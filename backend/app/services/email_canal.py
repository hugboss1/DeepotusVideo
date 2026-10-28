# -*- coding: utf-8 -*-
"""t356 (28/10/2026) — Veille & prospection P5 : le CANAL E-MAIL d'un espace, `DATA_ROOT/espaces/<id>/email.json`.
Spec `2026-10-27-agent-veille-prospection-design.md` §3, §9.1, §9.3 ; plan `docs/superpowers/plans/2026-10-28-prospects-p5-t356.md`.

Une interface, deux façons d'envoyer (au choix par espace) : la boîte SMTP de l'utilisateur, ou Brevo (API). Les
réponses se lisent TOUJOURS dans l'IMAP de la boîte de l'expéditeur (`email_envoi`). Ici :
  - réglages : expéditeur, identité (raison sociale + adresse postale : obligatoires), SMTP / Brevo, IMAP, plafond ;
  - secrets (mot de passe de la boîte, clé Brevo) SCELLÉS par DPAPI pour la session Windows, jamais rendus ;
  - composition : pied d'identité, « répondez STOP », en-tête List-Unsubscribe (mailto : l'app est locale, aucun lien
    web ne la joint), Message-ID au domaine de l'expéditeur ; les en-têtes refusent tout retour à la ligne ;
  - plafond du jour 10 → 20 → 30 depuis le premier envoi, borné par le réglage de l'espace (30 au plus) ;
  - journal des envois, rebonds et plaintes ; pause automatique (rebonds > 5 % dès 10 envois sur 30 jours, ou 2 rebonds
    avant ; plainte = pause immédiate) ; « reprendre » est un geste de l'utilisateur.
Erreurs : `RefusEmail(message, code)` ; codes `champ`, `inconnu`, `incomplet`, `pause`, `rebond` (refus définitif du
destinataire), `passager` (réessayer), `config` (identifiants ou réglage refusés), `indisponible`.
"""
from __future__ import annotations

import base64
import json
import re
import smtplib
import ssl
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr, formatdate

from loguru import logger

from app.services import espaces as _es

FICHIER = "email.json"
MODES = ("smtp", "brevo")
SECURITES = ("ssl", "starttls")
SECRETS = ("mdp", "brevo")
ENTROPIE = b"DeepotusVideoGen/email/v1"
PLAFONDS = (10, 20, 30)
PLAFOND_MAX = 30
MAX_JOURNAL = 2000
FENETRE_REBONDS = timedelta(days=30)
SEUIL_REBONDS = 0.05
MIN_ENVOIS_TAUX = 10
DELAI = 30
STATUTS_JOURNAL = ("envoye", "rebond", "plainte", "echec")
PIED = ("\n\n-- \n{raison}\n{adresse}\n"
        "Vous recevez ce message à titre professionnel. Pour ne plus recevoir de message de notre part, "
        "répondez STOP.")
_HTTP = {"champ": 422, "inconnu": 404, "incomplet": 409, "pause": 409, "rebond": 409, "passager": 503,
         "config": 409, "indisponible": 503}
_ADRESSE = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,190}\.[A-Za-z]{2,24}$")
_HOTE = re.compile(r"^[A-Za-z0-9.\-]{1,253}$")
_verrou = threading.RLock()


class RefusEmail(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.message, self.code = message, code
        self.statut = _HTTP.get(code, 409)


def _maintenant() -> datetime:          # couture de banc
    return datetime.now(timezone.utc)


def _vierge() -> dict:
    return {"version": 1, "mode": "smtp", "expediteur": {"nom": "", "adresse": ""},
            "identite": {"raison_sociale": "", "adresse_postale": ""},
            "smtp": {"hote": "", "port": 465, "securite": "ssl", "utilisateur": ""},
            "imap": {"hote": "", "port": 993, "utilisateur": ""}, "plafond_jour": PLAFOND_MAX,
            "secrets": {}, "pause": {"active": False, "motif": "", "depuis": None}, "reprise_le": None,
            "premier_envoi": None, "erreur": None, "journal": [], "imap_etat": {"uidvalidity": None, "dernier": 0, "lu_le": None},
            "reponses": []}


# ---- fichier ----------------------------------------------------------------------------------------------------------

def _espace(eid) -> None:
    e = _es.lire()["espaces"].get(eid) if _es.id_valide(eid) else None
    if not isinstance(e, dict) or e.get("archive") or e.get("type") == "demonstration":
        raise RefusEmail("espace inconnu, archivé ou de démonstration", "inconnu")


def _doc(eid) -> dict:
    f = _es.chemin(eid, FICHIER)
    doc = _vierge()
    try:
        brut = f.read_bytes()
    except FileNotFoundError:
        return doc
    except OSError:
        raise RefusEmail("réglages e-mail momentanément illisibles : réessayez dans un instant", "indisponible") from None
    try:
        lu = json.loads(brut.decode("utf-8"))
        if not isinstance(lu, dict):
            raise ValueError("forme")
    except ValueError:
        cote = f.with_name(f"{f.name}.illisible-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        try:
            f.replace(cote)
            logger.warning(f"réglages e-mail illisibles mis de côté : {cote.name}")
        except OSError:
            raise RefusEmail("réglages e-mail momentanément illisibles : réessayez dans un instant", "indisponible") from None
        return doc
    for k, v in lu.items():
        if k in doc and (doc[k] is None or isinstance(v, type(doc[k]))):
            doc[k] = v
    for k in ("expediteur", "identite", "smtp", "imap", "pause", "imap_etat"):
        doc[k] = {**_vierge()[k], **(doc[k] if isinstance(doc[k], dict) else {})}
    return doc


def _poser(eid, doc: dict) -> None:
    del doc["journal"][:-MAX_JOURNAL]
    del doc["reponses"][:-500]
    _es._ecrire_json(_es.chemin(eid, FICHIER), doc)


# ---- réglages ---------------------------------------------------------------------------------------------------------

def _ligne(v, n: int, champ: str) -> str:
    s = str(v if v is not None else "").strip()
    if "\r" in s or "\n" in s or len(s) > n:
        raise RefusEmail(f"{champ} : une ligne de {n} caractères au plus", "champ")
    return s


def _adresse(v, champ: str = "adresse") -> str:
    s = _ligne(v, 254, champ)
    if s and not _ADRESSE.match(s):
        raise RefusEmail(f"{champ} : adresse e-mail illisible", "champ")
    return s


def _port(v) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 65535:
        raise RefusEmail("port : un entier de 1 à 65535", "champ")
    return v


def _hote(v) -> str:
    s = _ligne(v, 253, "serveur")
    if s and not _HOTE.match(s):
        raise RefusEmail("serveur : un nom d'hôte, sans https:// ni chemin", "champ")
    return s


def regler(eid, champs: dict) -> dict:
    _espace(eid)
    if not isinstance(champs, dict):
        raise RefusEmail("réglages illisibles", "champ")
    inconnus = set(champs) - {"mode", "expediteur", "identite", "smtp", "imap", "plafond_jour"}
    if inconnus:
        raise RefusEmail("réglage inconnu : " + ", ".join(sorted(map(str, inconnus)))[:100], "champ")
    with _verrou:
        doc = _doc(eid)
        if "mode" in champs:
            if champs["mode"] not in MODES:
                raise RefusEmail("mode d'envoi inconnu (smtp ou brevo)", "champ")
            doc["mode"] = champs["mode"]
        if "expediteur" in champs:
            x = champs["expediteur"] if isinstance(champs["expediteur"], dict) else {}
            doc["expediteur"] = {"nom": _ligne(x.get("nom"), 80, "nom de l'expéditeur"),
                                 "adresse": _adresse(x.get("adresse"), "adresse de l'expéditeur")}
        if "identite" in champs:
            x = champs["identite"] if isinstance(champs["identite"], dict) else {}
            postale = str(x.get("adresse_postale") or "").strip()
            if len(postale) > 300:
                raise RefusEmail("adresse postale : 300 caractères au plus", "champ")
            doc["identite"] = {"raison_sociale": _ligne(x.get("raison_sociale"), 120, "raison sociale"), "adresse_postale": postale}
        if "smtp" in champs:
            x = champs["smtp"] if isinstance(champs["smtp"], dict) else {}
            if x.get("securite", "ssl") not in SECURITES:
                raise RefusEmail("sécurité SMTP : ssl ou starttls", "champ")
            doc["smtp"] = {"hote": _hote(x.get("hote")), "port": _port(x.get("port", 465)),
                           "securite": x.get("securite", "ssl"), "utilisateur": _ligne(x.get("utilisateur"), 254, "utilisateur")}
        if "imap" in champs:
            x = champs["imap"] if isinstance(champs["imap"], dict) else {}
            doc["imap"] = {"hote": _hote(x.get("hote")), "port": _port(x.get("port", 993)),
                           "utilisateur": _ligne(x.get("utilisateur"), 254, "utilisateur")}
        if "plafond_jour" in champs:
            p = champs["plafond_jour"]
            if isinstance(p, bool) or not isinstance(p, int) or not 1 <= p <= PLAFOND_MAX:
                raise RefusEmail(f"plafond : de 1 à {PLAFOND_MAX} e-mails par jour", "champ")
            doc["plafond_jour"] = p
        _poser(eid, doc)
    return lire(eid)


def poser_secret(eid, quoi: str, valeur: str) -> dict:
    """Le mot de passe de la boîte (SMTP et IMAP) ou la clé Brevo, scellé DPAPI ; une valeur vide l'efface."""
    _espace(eid)
    if quoi not in SECRETS:
        raise RefusEmail("secret inconnu (mdp ou brevo)", "champ")
    v = str(valeur or "")
    if len(v) > 500 or "\n" in v or "\r" in v:
        raise RefusEmail("secret illisible", "champ")
    with _verrou:
        doc = _doc(eid)
        if v:
            from app.services import dpapi
            doc["secrets"][quoi] = base64.b64encode(dpapi.sceller(v.encode("utf-8"), ENTROPIE)).decode("ascii")
        else:
            doc["secrets"].pop(quoi, None)
        _poser(eid, doc)
    return lire(eid)


def _secret(eid, quoi: str, doc: dict | None = None) -> str | None:
    s = ((doc or _doc(eid)).get("secrets") or {}).get(quoi)
    if not s:
        return None
    from app.services import dpapi
    try:
        brut = dpapi.desceller(base64.b64decode(s), ENTROPIE)
    except ValueError:
        return None
    return brut.decode("utf-8") if brut else None


def manques(doc: dict) -> list:
    m = []
    if not (doc["expediteur"]["nom"] and doc["expediteur"]["adresse"]):
        m.append("expediteur")
    if not (doc["identite"]["raison_sociale"] and doc["identite"]["adresse_postale"]):
        m.append("identite")
    if doc["mode"] == "smtp" and not (doc["smtp"]["hote"] and doc["smtp"]["utilisateur"]):
        m.append("smtp")
    if not (doc["imap"]["hote"] and doc["imap"]["utilisateur"]):
        m.append("imap")
    if not doc["secrets"].get("mdp"):          # la boîte : envoi SMTP, et toujours la lecture IMAP (STOP, réponses)
        m.append("mdp")
    if doc["mode"] == "brevo" and not doc["secrets"].get("brevo"):
        m.append("brevo")
    return m


def lire(eid, maintenant: datetime | None = None) -> dict:
    """La vue de l'écran : réglages SANS secret, ce qui manque, l'état du jour (plafond, envoyés, taux, pause)."""
    _espace(eid)
    now = maintenant or _maintenant()
    with _verrou:
        doc = _doc(eid)
    jour = now.astimezone(_fuseau(eid)).date()
    m = manques(doc)
    return {"mode": doc["mode"], "expediteur": doc["expediteur"], "identite": doc["identite"], "smtp": doc["smtp"],
            "imap": doc["imap"], "plafond_jour": doc["plafond_jour"], "mdp_pose": bool(doc["secrets"].get("mdp")),
            "brevo_pose": bool(doc["secrets"].get("brevo")), "manques": m, "pret": not m, "pause": doc["pause"],
            "plafond_du_jour": _plafond(doc, jour), "envoyes_du_jour": _envoyes(doc, jour, _fuseau(eid)),
            "taux_rebond": _taux(doc, now)[0], "imap_lu_le": doc["imap_etat"].get("lu_le"), "erreur": doc.get("erreur")}


# ---- plafond, journal, pause --------------------------------------------------------------------------------------------

def _fuseau(eid):
    from zoneinfo import ZoneInfo
    from app.services import prospects_sequences as S
    return ZoneInfo(S._agent(eid)["horaires"]["fuseau"])


def _plafond(doc: dict, jour: date) -> int:
    depuis = date.fromisoformat(doc["premier_envoi"]) if doc.get("premier_envoi") else jour
    n = (jour - depuis).days
    rampe = PLAFONDS[0] if n < 7 else PLAFONDS[1] if n < 14 else PLAFONDS[2]
    return min(rampe, doc["plafond_jour"])


def _envoyes(doc: dict, jour: date, tz) -> int:
    return sum(1 for j in doc["journal"] if j.get("statut") == "envoye"
               and datetime.fromisoformat(j["quand"]).astimezone(tz).date() == jour)


def plafond_du_jour(eid, jour: date) -> int:
    return _plafond(_doc(eid), jour)


def reste_du_jour(eid, jour: date) -> int:
    doc = _doc(eid)
    return max(0, _plafond(doc, jour) - _envoyes(doc, jour, _fuseau(eid)))


def _taux(doc: dict, now: datetime) -> tuple:
    debut = now - FENETRE_REBONDS
    if doc.get("reprise_le"):
        debut = max(debut, datetime.fromisoformat(doc["reprise_le"]))
    j = [x for x in doc["journal"] if datetime.fromisoformat(x["quand"]) >= debut]
    envois = sum(1 for x in j if x["statut"] == "envoye")
    rebonds = sum(1 for x in j if x["statut"] == "rebond")
    return (rebonds / envois if envois else 0.0), envois, rebonds


def noter(eid, statut: str, adresse: str, message_id, detail: str = "", quand: datetime | None = None, sid=None, rang=None,
          pid=None) -> None:
    """Une ligne au journal ; un rebond ou une plainte peut mettre l'espace en pause."""
    if statut not in STATUTS_JOURNAL:
        raise ValueError("statut de journal inconnu")
    q = (quand or _maintenant()).astimezone(timezone.utc)
    with _verrou:
        doc = _doc(eid)
        doc["journal"].append({"quand": q.isoformat(), "statut": statut, "a": str(adresse or "")[:254].lower(),
                               "message_id": message_id, "detail": str(detail or "")[:200], "sid": sid, "rang": rang, "pid": pid})
        if statut == "envoye" and not doc.get("premier_envoi"):
            doc["premier_envoi"] = q.astimezone(_fuseau(eid)).date().isoformat()
        if not doc["pause"]["active"]:
            if statut == "plainte":
                doc["pause"] = {"active": True, "motif": "plainte", "depuis": q.isoformat()}
            elif statut == "rebond":
                taux, envois, rebonds = _taux(doc, q)
                if (envois >= MIN_ENVOIS_TAUX and taux > SEUIL_REBONDS) or (envois < MIN_ENVOIS_TAUX and rebonds >= 2):
                    doc["pause"] = {"active": True, "motif": "rebonds", "depuis": q.isoformat()}
        if doc["pause"]["active"] and doc["pause"]["depuis"] == q.isoformat():
            logger.warning(f"e-mail de l'espace {eid} mis en pause ({doc['pause']['motif']})")
        _poser(eid, doc)


def noter_erreur(eid, message) -> None:
    """La dernière erreur de réglage (identifiants, serveur) pour l'écran ; None l'efface."""
    with _verrou:
        doc = _doc(eid)
        nouveau = {"message": str(message)[:300], "le": _maintenant().isoformat()} if message else None
        if (doc.get("erreur") or {}).get("message") == (nouveau or {}).get("message"):
            return
        doc["erreur"] = nouveau
        _poser(eid, doc)


def ajouter_reponse(eid, r: dict) -> None:
    """Le résumé d'une réponse lue (pour l'agent, P7) : prospect, objet, 500 premiers caractères, STOP."""
    with _verrou:
        doc = _doc(eid)
        doc["reponses"].append(dict(r, quand=_maintenant().isoformat()))
        _poser(eid, doc)


def poser_imap(eid, etat: dict) -> None:
    with _verrou:
        doc = _doc(eid)
        doc["imap_etat"] = {"uidvalidity": etat.get("uidvalidity"), "dernier": int(etat.get("dernier") or 0),
                            "lu_le": _maintenant().isoformat()}
        _poser(eid, doc)


def reprendre(eid) -> dict:
    _espace(eid)
    with _verrou:
        doc = _doc(eid)
        doc["pause"] = {"active": False, "motif": "", "depuis": None}
        doc["reprise_le"] = _maintenant().isoformat()
        _poser(eid, doc)
    return lire(eid)


# ---- composition ------------------------------------------------------------------------------------------------------

def nouvel_id(doc: dict) -> str:
    dom = (doc["expediteur"]["adresse"].rsplit("@", 1) + ["deepotus.local"])[1] or "deepotus.local"
    return f"<{uuid.uuid4().hex}@{dom}>"


def _un_ligne(s: str) -> str:
    return re.sub(r"[\r\n]+", " ", str(s or "")).strip()


def composer(doc: dict, a: str, objet: str, texte: str, message_id: str) -> EmailMessage:
    ex, ident = doc["expediteur"], doc["identite"]
    m = EmailMessage()
    m["From"] = formataddr((_un_ligne(ex["nom"]), ex["adresse"]))
    m["To"] = _un_ligne(a)
    m["Subject"] = _un_ligne(objet)[:200]
    m["Date"] = formatdate(localtime=False)
    m["Message-ID"] = message_id
    m["List-Unsubscribe"] = f"<mailto:{ex['adresse']}?subject=STOP>"
    m.set_content(str(texte or "") + PIED.format(raison=ident["raison_sociale"], adresse=ident["adresse_postale"]))
    return m


# ---- adaptateurs ------------------------------------------------------------------------------------------------------

_SMTP_SSL = smtplib.SMTP_SSL           # coutures de banc
_SMTP = smtplib.SMTP


def _brevo(cle: str, corps: dict) -> tuple[int, dict]:
    import httpx
    r = httpx.post("https://api.brevo.com/v3/smtp/email", headers={"api-key": cle, "accept": "application/json"},
                   json=corps, timeout=DELAI)
    try:
        j = r.json()
    except ValueError:
        j = {}
    return r.status_code, j if isinstance(j, dict) else {}


_BREVO = _brevo


def _par_smtp(doc: dict, mdp: str, msg: EmailMessage) -> None:
    s = doc["smtp"]
    ctx = ssl.create_default_context()
    try:
        if s["securite"] == "ssl":
            serveur = _SMTP_SSL(s["hote"], s["port"], timeout=DELAI, context=ctx)
        else:
            serveur = _SMTP(s["hote"], s["port"], timeout=DELAI)
        with serveur:
            if s["securite"] == "starttls":
                serveur.starttls(context=ctx)
            serveur.login(s["utilisateur"], mdp)
            refuses = serveur.send_message(msg)
        if refuses:
            raise RefusEmail("destinataire refusé par le serveur", "rebond")
    except smtplib.SMTPRecipientsRefused:
        raise RefusEmail("destinataire refusé par le serveur", "rebond") from None
    except smtplib.SMTPAuthenticationError:
        raise RefusEmail("identifiants SMTP refusés : vérifiez l'utilisateur et le mot de passe", "config") from None
    except smtplib.SMTPResponseException as e:
        if 500 <= e.smtp_code < 600:
            raise RefusEmail(f"envoi refusé par le serveur (code {e.smtp_code})", "rebond") from None
        raise RefusEmail(f"serveur SMTP occupé (code {e.smtp_code}) : nouvel essai plus tard", "passager") from None
    except (OSError, smtplib.SMTPException) as e:
        raise RefusEmail(f"serveur SMTP injoignable ({type(e).__name__}) : nouvel essai plus tard", "passager") from None


def _par_brevo(doc: dict, cle: str, msg: EmailMessage) -> None:
    ex = doc["expediteur"]
    corps = {"sender": {"name": _un_ligne(ex["nom"]), "email": ex["adresse"]}, "to": [{"email": str(msg["To"])}],
             "subject": str(msg["Subject"]), "textContent": msg.get_body(preferencelist=("plain",)).get_content(),
             "headers": {"List-Unsubscribe": str(msg["List-Unsubscribe"]), "Message-Id": str(msg["Message-ID"])}}
    try:
        statut, _ = _BREVO(cle, corps)
    except Exception as e:  # noqa: BLE001 — réseau : passager, sans la clé
        raise RefusEmail(f"Brevo injoignable ({type(e).__name__}) : nouvel essai plus tard", "passager") from None
    if statut in (200, 201, 202):
        return
    if statut in (401, 403):
        raise RefusEmail("clé Brevo refusée : vérifiez-la dans l'onglet Prospects", "config")
    if statut == 400:
        raise RefusEmail("Brevo a refusé ce destinataire ou ce message", "rebond")
    raise RefusEmail(f"Brevo indisponible (HTTP {statut}) : nouvel essai plus tard", "passager")


def envoyer(eid, msg: EmailMessage) -> dict:
    """Envoie un message composé, par le mode de l'espace. Refus : pause, réglages incomplets, rebond, passager,
    config. Le journal est l'affaire de l'appelant (`noter`)."""
    _espace(eid)
    doc = _doc(eid)
    if doc["pause"]["active"]:
        raise RefusEmail(f"envoi en pause ({doc['pause']['motif']}) : reprenez-le dans l'onglet Prospects", "pause")
    m = manques(doc)
    if m:
        raise RefusEmail("réglages e-mail incomplets : " + ", ".join(m), "incomplet")
    if doc["mode"] == "brevo":
        _par_brevo(doc, _secret(eid, "brevo", doc) or "", msg)
    else:
        _par_smtp(doc, _secret(eid, "mdp", doc) or "", msg)
    return {"message_id": str(msg["Message-ID"])}
