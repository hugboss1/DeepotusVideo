# -*- coding: utf-8 -*-
"""t356 (28/10/2026) — Veille & prospection P5, tâche 2 : l'ENVOI des étapes e-mail dues et la LECTURE des réponses.

`envoyer_dues(eid)` : seulement les étapes que `prospects_sequences.etapes_dues` rend (séquence VALIDÉE par l'utilisateur
puis planifiée, à l'heure, une relance comptée depuis l'envoi RÉEL de l'étape d'avant), dans les heures calmes, hors
pause, sous le plafond du jour, à une fiche toujours éligible (canal possible revérifié, adresse unique et valide), et
seulement si la lecture des réponses (IMAP) a réussi il y a moins de 15 min : on n'envoie pas sans lire les STOP.
Au plus une fois : une ligne « tentative » est écrite AVANT l'envoi ; une étape qui en porte déjà une passe pour envoyée.
Succès : étape envoyée (Message-ID), contact sortant, fiche Qualifiée → Contactée. Rebond (5xx du destinataire) :
séquence arrêtée. Passager (serveur injoignable, 4xx) : rien n'est arrêté, l'étape attend, l'erreur est dite.
Réglage refusé (identifiants, expéditeur, contenu) : rien ne part, l'erreur est gardée pour l'écran.
`lire_reponses(eid)` : l'IMAP de la boîte, en lecture seule (BODY.PEEK), à partir du dernier UID vu (au premier passage :
l'historique n'est pas relu). Réponse rattachée (In-Reply-To / References, sinon l'adresse d'une fiche) → contact
entrant, « A répondu », résumé gardé pour l'agent ; réponse automatique (absence) : ignorée ; STOP / désinscription →
opposition (fiche, ou registre pour un inconnu) ; avis de non-remise ou plainte : comptés seulement s'ils visent un de
NOS envois. Un message illisible est sauté (journalisé), jamais bloquant.
`boucle()` : toutes les 60 s l'envoi, toutes les 5 min la lecture. Les gestes qui peuvent écrire `espaces.json`
(opposition, changement de statut) passent sur la boucle d'événements (règle t353 I4), jamais depuis un thread.
"""
from __future__ import annotations

import asyncio
import html
import imaplib
import re
import ssl
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr

from loguru import logger

from app.services import email_canal as M, espaces as _es, prospects as _p, prospects_score as _sc, \
    prospects_sequences as _sq

MAX_LUS = 200
FRAICHEUR_IMAP = timedelta(minutes=15)
_PREFIXE = re.compile(r"^\s*((re|tr|fwd?|aw|wg)\s*:\s*)+", re.I)
_STOP_LIGNE = re.compile(r"^\s*(stop|arr[eê]t(e|ez|er)?)\b", re.I | re.M)
_STOP_PHRASE = re.compile(r"(d[ée]sinscri|d[ée]sabonn|unsubscrib|remove me|retirez[- ]moi|"
                          r"ne (plus|pas) (me )?(recevoir|contacter|[ée]crire|solliciter))", re.I)
_AUTO_SUJET = re.compile(r"(r[ée]ponse automatique|absence|absent|out of (the )?office|automatic reply|auto[- ]?reply|"
                         r"cong[ée]s?)", re.I)
_ID = re.compile(r"<[^<>\s]{1,300}>")
_ENVOYER = M.envoyer                   # coutures de banc
_IMAP = imaplib.IMAP4_SSL
_BOUCLE: asyncio.AbstractEventLoop | None = None


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


def _sur_boucle(fn, *a, **k):
    """t356 (relecture I11) : un geste qui peut écrire `espaces.json` s'exécute sur la boucle d'événements quand on est
    dans un thread de la boucle e-mail ; sinon (bancs, appel direct), sur place."""
    boucle = _BOUCLE
    if boucle is None or not boucle.is_running():
        return fn(*a, **k)
    try:
        if asyncio.get_running_loop() is boucle:
            return fn(*a, **k)
    except RuntimeError:
        pass

    async def geste():
        return fn(*a, **k)
    return asyncio.run_coroutine_threadsafe(geste(), boucle).result(timeout=60)


def _email_de(fiche: dict) -> str | None:
    for c in fiche.get("canaux") or []:
        if c.get("type") == "email" and c.get("valeur"):
            return str(c["valeur"]).strip()
    return None


def imap_sain(eid) -> bool:
    """La lecture des réponses a réussi il y a moins de 15 min (relecture I6)."""
    doc = M._doc(eid)
    lu = doc["imap_etat"].get("lu_le")
    if doc.get("erreur_imap") or not lu:
        return False
    return _maintenant() - datetime.fromisoformat(lu) < FRAICHEUR_IMAP


_IMAP_SAIN = imap_sain


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
    dues = _sq.etapes_dues(eid, "email")
    if dues and not _IMAP_SAIN(eid):
        out["etat"] = "imap"
        M.noter_erreur(eid, "les réponses ne sont pas lues (IMAP) : aucun e-mail ne part tant que la lecture échoue")
        return out
    reste = M.reste_du_jour(eid, now.astimezone(M._fuseau(eid)).date())
    for d in dues:
        deja = M.tentative(eid, d["sid"], d["rang"])
        if deja:                               # au plus une fois : une tentative écrite vaut envoi
            M.confirmer(eid, deja)
            _sq.noter_envoi(eid, d["sid"], d["rang"], deja)
            continue
        if reste <= 0:
            out["etat"] = "plafond"
            break
        try:
            fiche = _p.lire(eid, d["pid"])
        except _p.RefusProspect:
            _sq.arreter(eid, d["sid"], "effacee")
            continue
        adresse = _email_de(fiche)
        if fiche["statut"] not in _sq.STATUTS_FICHE or not adresse or not M._ADRESSE.fullmatch(adresse) \
                or "email" not in [c["canal"] for c in _sc.canaux_possibles(fiche)]:
            _sq.arreter(eid, d["sid"], "canal")
            continue
        doc = M._doc(eid)
        mid = M.nouvel_id(doc)
        msg = M.composer(doc, adresse, d["objet"], d["texte"], mid)
        if not _sq.encore_due(eid, d["sid"], d["rang"]):     # annulée pendant la passe (relecture M1)
            continue
        M.noter(eid, "tentative", adresse, mid, sid=d["sid"], rang=d["rang"], pid=d["pid"])
        try:
            _ENVOYER(eid, msg)
        except M.RefusEmail as e:
            if e.code == "rebond":
                M.requalifier(eid, mid, "rebond", e.message)
                _sq.arreter(eid, d["sid"], "rebond")
                out["rebonds"] += 1
                continue
            M.requalifier(eid, mid, "echec", e.message)
            M.noter_erreur(eid, e.message)
            out["etat"] = e.code
            out["reportes"] += 1 if e.code == "passager" else 0
            break                               # serveur en panne ou réglage refusé : l'étape attend, rien n'est arrêté
        M.confirmer(eid, mid)
        M.noter_erreur(eid, None)
        _sq.noter_envoi(eid, d["sid"], d["rang"], mid)
        try:
            _p.noter_contact(eid, d["pid"], "sortant", f"e-mail : message {d['rang'] + 1} envoyé", "systeme")
            if fiche["statut"] == "qualifie":
                _sur_boucle(_p.changer_statut, eid, d["pid"], "contacte", "1er e-mail envoyé", "systeme")
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
        t = re.sub(r"(?is)<(style|script|head)\b.*?</\1>", " ", t)
        t = re.sub(r"(?i)<\s*(br|/p|/div|/li|/tr|/h\d)\b[^>]*>", "\n", t)
        t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return str(t or "")


def _propre(texte: str) -> str:
    """La réponse sans la citation de notre message (« > », « Le … a écrit », en-têtes Outlook, message d'origine)."""
    lignes = []
    for l in texte.splitlines():
        if l.lstrip().startswith(">") or re.match(r"^\s*(le .{3,120} a écrit|on .{3,120} wrote)\s*:?\s*$", l, re.I) \
                or re.match(r"^\s*(-{3,}\s*(original message|message d'origine)|de\s*:\s|from\s*:\s)", l, re.I):
            break
        lignes.append(l)
    return "\n".join(lignes).strip()


def est_stop(sujet: str, corps: str) -> bool:
    s = _PREFIXE.sub("", sujet or "")
    debut = (corps or "")[:300]
    return bool(_STOP_LIGNE.search(s) or _STOP_PHRASE.search(s) or _STOP_LIGNE.search(debut) or _STOP_PHRASE.search(debut))


def _automatique(msg, sujet: str) -> bool:
    auto = str(msg.get("Auto-Submitted") or "").strip().lower()
    prec = str(msg.get("Precedence") or "").strip().lower()
    return (auto not in ("", "no") or bool(msg.get("X-Autoreply")) or bool(msg.get("X-Autorespond"))
            or prec in ("auto_reply", "bulk", "junk") or bool(_AUTO_SUJET.search(_PREFIXE.sub("", sujet))))


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


def _envoi_vers(journal: list, adresse: str) -> dict | None:
    return next((j for j in reversed(journal) if j["a"] == adresse and j["statut"] == "envoye"), None)


def _traiter(eid, msg, journal: list, out: dict) -> None:
    if msg.get_content_type() == "multipart/report":
        genre = str(msg.get_param("report-type") or "").lower()
        if genre == "delivery-status":
            rapport = _parties(msg, "message/delivery-status")
            if re.search(r"^\s*action\s*:\s*failed", rapport, re.I | re.M):
                for a in dict.fromkeys(_adresses_rapport(rapport, ("final-recipient", "original-recipient"))):
                    envoi = _envoi_vers(journal, a)
                    if envoi is None:            # relecture I10 : seulement un rebond de NOS envois
                        out["ignores"] += 1
                        continue
                    M.noter(eid, "rebond", a, envoi.get("message_id"), "avis de non-remise",
                            sid=envoi.get("sid"), rang=envoi.get("rang"), pid=envoi.get("pid"))
                    if envoi.get("sid"):
                        try:
                            _sq.arreter(eid, envoi["sid"], "rebond")
                        except _sq.RefusSequence:
                            pass
                    out["rebonds"] += 1
            return
        if genre == "feedback-report":
            rapport = _parties(msg, "message/feedback-report")
            for a in dict.fromkeys(_adresses_rapport(rapport, ("original-rcpt-to", "removal-recipient"))):
                envoi = _envoi_vers(journal, a)
                if envoi is None:
                    out["ignores"] += 1
                    continue
                M.noter(eid, "plainte", a, envoi.get("message_id"), "rapport de plainte", pid=envoi.get("pid"))
                _opposer(eid, envoi.get("pid") or _pid_par_adresse(eid, a), a)
                out["plaintes"] += 1
            return
    de = parseaddr(str(msg.get("From") or ""))[1].strip().lower()
    sujet = re.sub(r"[\r\n]+", " ", str(msg.get("Subject") or ""))[:200]
    refs = set(_ID.findall(" ".join(str(msg.get(h) or "") for h in ("In-Reply-To", "References"))))
    envoi = next((j for j in reversed(journal) if j.get("message_id") in refs and j["statut"] == "envoye"), None) if refs else None
    pid = (envoi or {}).get("pid") or _pid_par_adresse(eid, de)
    corps = _propre(_texte(msg))
    if est_stop(sujet, corps):
        _opposer(eid, pid, de)
        M.ajouter_reponse(eid, {"pid": pid, "de": de if pid else "", "sujet": sujet, "extrait": "", "stop": True,
                                "message_id": str(msg.get("Message-ID") or "")[:300]})
        out["stops"] += 1
        return
    if not pid or _automatique(msg, sujet):     # relecture I9 : une absence n'est pas une réponse
        out["ignores"] += 1
        return
    try:
        f = _p.noter_contact(eid, pid, "entrant", f"e-mail : {sujet[:80]}", "systeme")
        if f["statut"] == "contacte":
            _sur_boucle(_p.changer_statut, eid, pid, "repondu", "réponse par e-mail", "systeme")
    except _p.RefusProspect:
        out["ignores"] += 1
        return
    M.ajouter_reponse(eid, {"pid": pid, "de": de, "sujet": sujet, "extrait": corps[:500], "stop": False,
                            "message_id": str(msg.get("Message-ID") or "")[:300]})
    out["reponses"] += 1


class RegistreIndisponible(RuntimeError):
    """Le STOP n'a pas pu être inscrit : la lecture s'arrête AVANT ce message (il sera relu)."""


def _opposer(eid, pid, adresse: str) -> None:
    """STOP ou plainte : la fiche s'oppose (registre compris) ; un inconnu va au registre seul."""
    if pid:
        try:
            _sur_boucle(_p.opposer, eid, pid, qui="systeme")
            return
        except _p.RefusProspect as e:
            if e.code == "transition":         # déjà opposée
                return
            if e.code == "indisponible":
                raise RegistreIndisponible(e.message) from None
            logger.warning(f"opposition par e-mail de {pid} : {e.message}")
    if adresse:
        from app.services import oppositions as _op
        try:
            _op.inscrire([adresse], "email")
        except Exception as e:  # noqa: BLE001 — registre verrouillé : la prochaine lecture rejouera (curseur non avancé)
            raise RegistreIndisponible(f"registre des oppositions indisponible ({type(e).__name__})") from None


def lire_reponses(eid) -> dict:
    out = {"lus": 0, "reponses": 0, "stops": 0, "rebonds": 0, "plaintes": 0, "ignores": 0}
    doc = M._doc(eid)
    i = doc["imap"]
    mdp = M._secret(eid, "mdp", doc)
    if not (i["hote"] and i["utilisateur"] and mdp):
        M.noter_erreur_imap(eid, "lecture IMAP impossible : serveur, utilisateur ou mot de passe manquant (ou à reposer sur ce PC)")
        return out
    etat = dict(doc["imap_etat"])
    ok = False
    try:
        with _IMAP(i["hote"], i["port"], ssl_context=ssl.create_default_context(), timeout=M.DELAI) as c:
            c.login(i["utilisateur"], mdp)
            c.select("INBOX", readonly=True)
            _, st = c.status("INBOX", "(UIDVALIDITY)")
            m = re.search(rb"UIDVALIDITY (\d+)", st[0] if st else b"")
            validite = int(m.group(1)) if m else None
            neuf = etat.get("uidvalidity") != validite or not etat.get("initialise")
            crit = "ALL" if neuf else f"UID {int(etat.get('dernier') or 0) + 1}:*"
            _, d = c.uid("search", None, crit)
            uids = sorted(int(x) for x in (d[0] or b"").split() if x.isdigit())
            if neuf:                        # premier passage : l'historique n'est pas relu (relecture I8 : boîte vide comprise)
                etat.update({"uidvalidity": validite, "dernier": uids[-1] if uids else 0, "initialise": True})
                uids = []
            uids = [u for u in uids if u > int(etat.get("dernier") or 0)][:MAX_LUS]
            journal = doc["journal"]
            for u in uids:
                _, data = c.uid("fetch", str(u), "(BODY.PEEK[])")
                brut = next((x[1] for x in data or [] if isinstance(x, tuple) and len(x) > 1), None)
                if brut:
                    try:
                        _traiter(eid, BytesParser(policy=policy.default).parsebytes(bytes(brut)), journal, out)
                    except RegistreIndisponible:
                        raise
                    except Exception as e:  # noqa: BLE001 — relecture I7 : un message illisible est sauté, jamais bloquant
                        logger.warning(f"message IMAP {u} de {eid} illisible, sauté ({type(e).__name__})")
                        out["ignores"] += 1
                    out["lus"] += 1
                etat["dernier"] = u
            ok = True
    except (OSError, imaplib.IMAP4.error) as e:
        M.noter_erreur_imap(eid, f"lecture IMAP impossible ({type(e).__name__}) : vérifiez le serveur et le mot de passe")
        return out
    finally:
        M.poser_imap(eid, etat, lu=ok)
    if ok:
        M.noter_erreur_imap(eid, None)
    return out


# ---- boucle -----------------------------------------------------------------------------------------------------------

def _espaces_email() -> list:
    racine = _es.dossier()
    try:
        return sorted(d.name for d in racine.iterdir() if d.is_dir() and _es.id_valide(d.name) and (d / M.FICHIER).is_file())
    except OSError:
        return []


async def boucle(premier: float = 90, intervalle: float = 60) -> None:
    global _BOUCLE
    _BOUCLE = asyncio.get_running_loop()
    await asyncio.sleep(premier)
    n = 0
    while True:
        for eid in _espaces_email():
            for geste in (((lire_reponses,) if n % 5 == 0 else ()) + (envoyer_dues,)):
                try:
                    await asyncio.to_thread(geste, eid)
                except (M.RefusEmail, _sq.RefusSequence, RegistreIndisponible):
                    pass                     # espace archivé, réglages ou registre indisponibles : la passe suivante
                except Exception as e:  # noqa: BLE001 — une panne d'un espace n'arrête pas les autres
                    logger.warning(f"canal e-mail de {eid} : {type(e).__name__} : {e}")
        n += 1
        await asyncio.sleep(intervalle)
