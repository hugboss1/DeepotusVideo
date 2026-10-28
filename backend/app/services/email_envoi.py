# -*- coding: utf-8 -*-
"""t356 (28/10/2026) — Veille & prospection P5, tâche 2 : l'ENVOI des étapes e-mail dues et la LECTURE des réponses.

`envoyer_dues(eid)` : seulement les étapes que `prospects_sequences.etapes_dues` rend (séquence VALIDÉE par l'utilisateur
puis planifiée, à l'heure), dans les heures calmes, hors pause, sous le plafond du jour, à une fiche toujours éligible
(canal possible revérifié : consentement, base légale, registre). Succès : étape envoyée (Message-ID), contact sortant,
fiche Qualifiée → Contactée. Rebond : séquence arrêtée (journal → pause éventuelle). Passager : 3 essais, puis arrêt
« echec ». Réglage refusé (identifiants) : rien ne part, l'erreur est gardée pour l'écran.
`lire_reponses(eid)` : l'IMAP de la boîte, en lecture seule (BODY.PEEK, rien n'est marqué lu), à partir du dernier UID
vu (au premier passage : l'historique n'est pas relu). Réponse rattachée (In-Reply-To / References, sinon l'adresse
d'une fiche) → contact entrant, « A répondu », résumé gardé pour l'agent ; STOP / désinscription → opposition (fiche, ou
registre pour un inconnu) ; avis de non-remise → rebond ; rapport de plainte → pause + opposition.
`boucle()` : toutes les 60 s l'envoi, toutes les 5 min la lecture, pour chaque espace dont le canal est prêt.
"""
from __future__ import annotations

import asyncio
import imaplib
import re
import ssl
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr

from loguru import logger

from app.services import email_canal as M, espaces as _es, prospects as _p, prospects_score as _sc, \
    prospects_sequences as _sq

MAX_ESSAIS = 3
MAX_LUS = 200
_STOP = re.compile(r"^\s*(stop|arr[eê]t|d[ée]sinscri|desabonn|d[ée]sabonn|unsubscribe|remove me)\b", re.I | re.M)
_ID = re.compile(r"<[^<>\s]{1,300}>")
_ENVOYER = M.envoyer                   # coutures de banc
_IMAP = imaplib.IMAP4_SSL


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


def _email_de(fiche: dict) -> str | None:
    for c in fiche.get("canaux") or []:
        if c.get("type") == "email" and c.get("valeur"):
            return str(c["valeur"]).strip()
    return None


# ---- envoi ------------------------------------------------------------------------------------------------------------

def envoyer_dues(eid) -> dict:
    out = {"envoyes": 0, "rebonds": 0, "reportes": 0, "etat": "ok"}
    v = M.lire(eid)
    if v["pause"]["active"]:
        out["etat"] = "pause"
        return out
    if not v["pret"]:
        out["etat"] = "incomplet"
        return out
    from app.services import whatsapp as _wa
    now = _maintenant()
    if not _wa.dans_horaires(_sq._agent(eid), now):
        out["etat"] = "hors_horaires"
        return out
    reste = M.reste_du_jour(eid, now.astimezone(M._fuseau(eid)).date())
    for d in _sq.etapes_dues(eid, "email"):
        if reste <= 0:
            out["etat"] = "plafond"
            break
        try:
            fiche = _p.lire(eid, d["pid"])
        except _p.RefusProspect:
            _sq.arreter(eid, d["sid"], "effacee")
            continue
        adresse = _email_de(fiche)
        if fiche["statut"] not in _sq.STATUTS_FICHE or not adresse \
                or "email" not in [c["canal"] for c in _sc.canaux_possibles(fiche)]:
            _sq.arreter(eid, d["sid"], "canal")
            continue
        doc = M._doc(eid)
        mid = M.nouvel_id(doc)
        msg = M.composer(doc, adresse, d["objet"], d["texte"], mid)
        try:
            _ENVOYER(eid, msg)
        except M.RefusEmail as e:
            if e.code == "rebond":
                M.noter(eid, "rebond", adresse, mid, e.message, sid=d["sid"], rang=d["rang"], pid=d["pid"])
                _sq.arreter(eid, d["sid"], "rebond")
                out["rebonds"] += 1
                continue
            if e.code == "passager":
                if _sq.noter_essai(eid, d["sid"], d["rang"]) >= MAX_ESSAIS:
                    M.noter(eid, "echec", adresse, mid, e.message, sid=d["sid"], rang=d["rang"], pid=d["pid"])
                    _sq.arreter(eid, d["sid"], "echec")
                out["reportes"] += 1
                break                          # le serveur est en panne : les autres attendront la passe suivante
            M.noter_erreur(eid, e.message)     # config, incomplet, pause : rien ne part tant que l'utilisateur n'a pas réglé
            out["etat"] = e.code
            break
        M.noter(eid, "envoye", adresse, mid, sid=d["sid"], rang=d["rang"], pid=d["pid"])
        M.noter_erreur(eid, None)
        _sq.noter_envoi(eid, d["sid"], d["rang"], mid)
        try:
            _p.noter_contact(eid, d["pid"], "sortant", f"e-mail : message {d['rang'] + 1} envoyé", "systeme")
            if fiche["statut"] == "qualifie":
                _p.changer_statut(eid, d["pid"], "contacte", "1er e-mail envoyé", "systeme")
        except _p.RefusProspect as e:
            logger.warning(f"e-mail envoyé mais fiche {d['pid']} non mise à jour : {e.message}")
        out["envoyes"] += 1
        reste -= 1
    return out


# ---- lecture ----------------------------------------------------------------------------------------------------------

def _texte(msg) -> str:
    b = None
    try:
        b = msg.get_body(preferencelist=("plain", "html"))
        t = b.get_content() if b is not None else ""
    except (KeyError, LookupError, ValueError):
        t = ""
    if b is not None and b.get_content_type() == "text/html":
        t = re.sub(r"<[^>]+>", " ", t)
    return str(t or "")


def _propre(texte: str) -> str:
    """La réponse sans la citation de notre message (lignes « > » et ce qui suit « Le … a écrit »)."""
    lignes = []
    for l in texte.splitlines():
        if l.lstrip().startswith(">") or re.match(r"^\s*(le .{3,80} a écrit|on .{3,80} wrote)\s*:?\s*$", l, re.I):
            break
        lignes.append(l)
    return "\n".join(lignes).strip()


def _parties(msg, genre: str) -> str:
    out = []
    for p in msg.walk():
        if p.get_content_type() == genre:
            pl = p.get_payload()
            if isinstance(pl, list):
                out.extend(str(x) for x in pl)
            else:
                out.append(pl if isinstance(pl, str) else str(p.get_payload(decode=True) or b"", "utf-8", "replace"))
    return "\n".join(out)


def _adresses_rapport(texte: str, champs: tuple) -> list:
    out = []
    for l in texte.splitlines():
        k, _, v = l.partition(":")
        if k.strip().lower() in champs:
            a = v.split(";")[-1].strip().strip("<>").lower()
            if "@" in a:
                out.append(a)
    return out


def _pid_par_adresse(eid, adresse: str) -> str | None:
    try:
        for f in _p.lister(eid):
            if any(c.get("type") == "email" and str(c.get("valeur") or "").strip().lower() == adresse for c in f.get("canaux") or []):
                return f["id"]
    except _p.RefusProspect:
        return None
    return None


def _traiter(eid, msg, journal: list, out: dict) -> None:
    if msg.get_content_type() == "multipart/report":
        genre = str(msg.get_param("report-type") or "").lower()
        if genre == "delivery-status":
            rapport = _parties(msg, "message/delivery-status")
            echecs = [a for a in _adresses_rapport(rapport, ("final-recipient", "original-recipient"))]
            if re.search(r"^\s*action\s*:\s*failed", rapport, re.I | re.M):
                for a in dict.fromkeys(echecs):
                    envoi = next((j for j in reversed(journal) if j["a"] == a and j["statut"] == "envoye"), None)
                    M.noter(eid, "rebond", a, envoi and envoi.get("message_id"), "avis de non-remise",
                            sid=envoi and envoi.get("sid"), rang=envoi and envoi.get("rang"), pid=envoi and envoi.get("pid"))
                    if envoi and envoi.get("sid"):
                        try:
                            _sq.arreter(eid, envoi["sid"], "rebond")
                        except _sq.RefusSequence:
                            pass
                    out["rebonds"] += 1
            return
        if genre == "feedback-report":
            rapport = _parties(msg, "message/feedback-report")
            for a in dict.fromkeys(_adresses_rapport(rapport, ("original-rcpt-to", "removal-recipient"))):
                M.noter(eid, "plainte", a, None, "rapport de plainte")
                pid = _pid_par_adresse(eid, a)
                _opposer(eid, pid, a)
            out["plaintes"] += 1
            return
    de = parseaddr(str(msg.get("From") or ""))[1].strip().lower()
    sujet = re.sub(r"[\r\n]+", " ", str(msg.get("Subject") or ""))[:200]
    refs = set(_ID.findall(" ".join(str(msg.get(h) or "") for h in ("In-Reply-To", "References"))))
    envoi = next((j for j in reversed(journal) if j.get("message_id") in refs), None) if refs else None
    pid = (envoi or {}).get("pid") or _pid_par_adresse(eid, de)
    corps = _propre(_texte(msg))
    if _STOP.search(sujet) or _STOP.search(corps[:300]):
        _opposer(eid, pid, de)
        M.ajouter_reponse(eid, {"pid": pid, "de": de if pid else "", "sujet": sujet, "extrait": "", "stop": True,
                                "message_id": str(msg.get("Message-ID") or "")[:300]})
        out["stops"] += 1
        return
    if not pid:
        out["ignores"] += 1
        return
    try:
        f = _p.noter_contact(eid, pid, "entrant", f"e-mail : {sujet[:80]}", "systeme")
        if f["statut"] == "contacte":
            _p.changer_statut(eid, pid, "repondu", "réponse par e-mail", "systeme")
    except _p.RefusProspect:
        out["ignores"] += 1
        return
    M.ajouter_reponse(eid, {"pid": pid, "de": de, "sujet": sujet, "extrait": corps[:500], "stop": False,
                            "message_id": str(msg.get("Message-ID") or "")[:300]})
    out["reponses"] += 1


def _opposer(eid, pid, adresse: str) -> None:
    """STOP ou plainte : la fiche s'oppose (registre compris) ; un inconnu va au registre seul."""
    if pid:
        try:
            _p.opposer(eid, pid, qui="systeme")
            return
        except _p.RefusProspect as e:
            if e.code != "transition":     # déjà opposée : rien à faire ; sinon, le registre au moins
                logger.warning(f"opposition par e-mail de {pid} : {e.message}")
            else:
                return
    if adresse:
        from app.services import oppositions as _op
        try:
            _op.inscrire([adresse], "email")
        except Exception as e:  # noqa: BLE001 — registre verrouillé : la prochaine lecture rejouera (curseur non avancé)
            raise RuntimeError(f"registre des oppositions indisponible ({type(e).__name__})") from None


def lire_reponses(eid) -> dict:
    out = {"lus": 0, "reponses": 0, "stops": 0, "rebonds": 0, "plaintes": 0, "ignores": 0}
    doc = M._doc(eid)
    i = doc["imap"]
    mdp = M._secret(eid, "mdp", doc)
    if not (i["hote"] and i["utilisateur"] and mdp):
        return out
    etat = dict(doc["imap_etat"])
    try:
        with _IMAP(i["hote"], i["port"], ssl_context=ssl.create_default_context(), timeout=M.DELAI) as c:
            c.login(i["utilisateur"], mdp)
            c.select("INBOX", readonly=True)
            _, st = c.status("INBOX", "(UIDVALIDITY)")
            m = re.search(rb"UIDVALIDITY (\d+)", st[0] if st else b"")
            validite = int(m.group(1)) if m else None
            neuf = etat.get("uidvalidity") != validite or not etat.get("dernier")
            crit = "ALL" if neuf else f"UID {int(etat['dernier']) + 1}:*"
            _, d = c.uid("search", None, crit)
            uids = sorted(int(x) for x in (d[0] or b"").split() if x.isdigit())
            if neuf:                        # premier passage : l'historique n'est pas relu
                etat.update({"uidvalidity": validite, "dernier": uids[-1] if uids else 0})
                uids = []
            uids = [u for u in uids if u > int(etat.get("dernier") or 0)][:MAX_LUS]
            journal = doc["journal"]
            for u in uids:
                _, data = c.uid("fetch", str(u), "(BODY.PEEK[])")
                brut = next((x[1] for x in data or [] if isinstance(x, tuple) and len(x) > 1), None)
                if brut:
                    _traiter(eid, BytesParser(policy=policy.default).parsebytes(bytes(brut)), journal, out)
                    out["lus"] += 1
                etat["dernier"] = u
    except (OSError, imaplib.IMAP4.error) as e:
        M.noter_erreur(eid, f"lecture IMAP impossible ({type(e).__name__}) : vérifiez le serveur et le mot de passe")
        return out
    finally:
        M.poser_imap(eid, etat)
    return out


# ---- boucle -----------------------------------------------------------------------------------------------------------

def _espaces_email() -> list:
    racine = _es.dossier()
    try:
        return sorted(d.name for d in racine.iterdir() if d.is_dir() and _es.id_valide(d.name) and (d / M.FICHIER).is_file())
    except OSError:
        return []


async def boucle(premier: float = 90, intervalle: float = 60) -> None:
    await asyncio.sleep(premier)
    n = 0
    while True:
        for eid in _espaces_email():
            for geste in ((envoyer_dues,) + ((lire_reponses,) if n % 5 == 0 else ())):
                try:
                    await asyncio.to_thread(geste, eid)
                except (M.RefusEmail, _sq.RefusSequence):
                    pass                     # espace archivé, réglages ou registre indisponibles : la passe suivante
                except Exception as e:  # noqa: BLE001 — une panne d'un espace n'arrête pas les autres
                    logger.warning(f"canal e-mail de {eid} : {type(e).__name__} : {e}")
        n += 1
        await asyncio.sleep(intervalle)
