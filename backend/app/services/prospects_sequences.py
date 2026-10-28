# -*- coding: utf-8 -*-
"""t355 (28/10/2026) — Veille & prospection P4 : les SÉQUENCES d'un prospect, `DATA_ROOT/espaces/<id>/sequences.json` =
{"version": 1, "email_depuis": "AAAA-MM-JJ" | None, "sequences": [...]}. Spec `2026-10-27-agent-veille-prospection-design.md`
§2, §3, §5 ; plan `docs/superpowers/plans/2026-10-28-prospects-p4-t355.md`.

Une séquence = 1 à 3 étapes (1er message + 2 relances) sur UN canal que `prospects_score.canaux_possibles` autorise :
  proposee (l'agent ou l'utilisateur la rédige) → validee (PORTE HUMAINE : l'utilisateur seul) → planifiee (consentement
  revérifié, heures calmes, plafond e-mail) → terminee ; annulee à tout moment, et d'office quand la fiche répond, prend
  rendez-vous, signe, est perdue ou s'oppose (« motif » : fiche:<statut>, effacee, remplacee, annulee).
Rien n'est ENVOYÉ ici : l'e-mail (P5) et WhatsApp (P6) liront les étapes dues de leur canal ; X, Instagram et LinkedIn
restent manuels (« Copier et ouvrir », puis « Marquer envoyé », qui note le contact sur la fiche).
Les envois ne vont pas dans la table du Planificateur : sa boucle publierait ou passerait « prête » des messages privés.
Écrivain unique sous verrou ; un fichier illisible est mis de côté, jamais écrasé.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from loguru import logger

from app.services import espaces as _es, prospects as _p, prospects_score as _sc

FICHIER = "sequences.json"
STATUTS = ("proposee", "validee", "planifiee", "terminee", "annulee")
EN_COURS = ("proposee", "validee", "planifiee")
CANAUX_AUTO = ("email", "whatsapp")            # envoyés par P5 / P6
CANAUX_MANUELS = ("x", "instagram", "linkedin")
STATUTS_FICHE = ("qualifie", "contacte")       # une fiche « proposé » se qualifie d'abord
ARRET = ("repondu", "rdv", "client", "perdu", "oppose")
MAX_ETAPES = 3
DELAI_MIN, DELAI_MAX = 2, 30
LONGUEURS = {"email": 5000, "whatsapp": 4096, "x": 2000, "instagram": 2000, "linkedin": 2000}
MAX_OBJET = 150
MAX_SEQUENCES = 2000
PLAFONDS_EMAIL = (10, 20, 30)                  # 1re semaine, 2e, ensuite (décision P0 §9.3)
JOURS_REPORT = 30
PAS = timedelta(minutes=15)
_ID = re.compile(r"^sq_[0-9a-f]{8}$")
_X = re.compile(r"^@?([A-Za-z0-9_]{1,15})$")
_INSTA = re.compile(r"^@?([A-Za-z0-9._]{1,30})$")
_LINKEDIN = re.compile(r"^https://([a-z]{2,3}\.|www\.)?linkedin\.com/[A-Za-z0-9_\-/%.]+$")
_HTTP = {"champ": 422, "interdit": 422, "inconnu": 404, "etat": 409, "canal": 409, "plafond": 409, "indisponible": 503}
_verrou = threading.RLock()


class RefusSequence(Exception):
    """Un geste refusé : `message` (texte de l'utilisateur, traduit par L10), `code`, `statut` HTTP."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.message, self.code = message, code
        self.statut = _HTTP.get(code, 409)


def _maintenant() -> datetime:          # couture de banc (UTC, avec fuseau)
    return datetime.now(timezone.utc)


def _txt(v, n: int) -> str:
    return str(v or "").strip()[:n]


# ---- fichier ----------------------------------------------------------------------------------------------------------

def _fichier(eid):
    return _es.chemin(eid, FICHIER)


def _lire(eid) -> dict:
    f = _fichier(eid)
    vide = {"version": 1, "email_depuis": None, "sequences": []}
    try:
        brut = f.read_bytes()
    except FileNotFoundError:
        return vide
    except OSError:
        raise RefusSequence("séquences momentanément illisibles : réessayez dans un instant", "indisponible") from None
    try:
        doc = json.loads(brut.decode("utf-8"))
        if not isinstance(doc, dict) or not isinstance(doc.get("sequences"), list):
            raise ValueError("forme inattendue")
    except ValueError:
        cote = f.with_name(f"{f.name}.illisible-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        try:
            f.replace(cote)
            logger.warning(f"séquences illisibles mises de côté : {cote.name}")
        except OSError:
            raise RefusSequence("séquences momentanément illisibles : réessayez dans un instant", "indisponible") from None
        return vide
    doc["sequences"] = [s for s in doc["sequences"] if isinstance(s, dict) and _ID.match(str(s.get("id") or ""))]
    return doc


def _poser(eid, doc: dict) -> None:
    fin = [s for s in doc["sequences"] if s.get("statut") in EN_COURS]
    reste = [s for s in doc["sequences"] if s.get("statut") not in EN_COURS]
    doc["sequences"] = reste[-max(0, MAX_SEQUENCES - len(fin)):] + fin if len(doc["sequences"]) > MAX_SEQUENCES else doc["sequences"]
    _es._ecrire_json(_fichier(eid), doc)


def _espace(eid) -> None:
    try:
        _p._espace(eid)
    except _p.RefusProspect as e:
        raise RefusSequence(e.message, "inconnu") from None


def _fiche(eid, pid) -> dict:
    try:
        return _p.lire(eid, pid)
    except _p.RefusProspect as e:
        raise RefusSequence(e.message, e.code if e.code in _HTTP else "inconnu") from None


def _trouver(doc: dict, sid) -> dict:
    for s in doc["sequences"]:
        if s["id"] == sid:
            return s
    raise RefusSequence("séquence inconnue", "inconnu")


def _noter(s: dict, quoi: str, qui: str) -> None:
    s.setdefault("historique", []).append({"quand": _es._maintenant(), "quoi": quoi, "qui": qui})
    del s["historique"][:-50]


def _stopper(s: dict, motif: str, effacer: bool = False) -> None:
    """Arrête une séquence (étapes non envoyées annulées) ; `effacer` (RGPD) vide aussi les textes et objets."""
    if s.get("statut") in EN_COURS:
        s["statut"], s["motif"] = "annulee", motif
        for e in s["etapes"]:
            if e["statut"] != "envoyee":
                e["statut"] = "annulee"
        _noter(s, "arret:" + motif, "systeme")
    if effacer:
        for e in s["etapes"]:
            e["texte"], e["objet"] = "", ""


def _fiches(eid) -> dict:
    """Les fiches de l'espace ; t355 (relecture I2) : registre ou fiche illisible = refus 503, jamais « rien à arrêter »."""
    try:
        return {f["id"]: f for f in _p.lister(eid)}
    except _p.RefusProspect as e:
        raise RefusSequence(e.message, "indisponible" if e.code == "indisponible" else "inconnu") from None


def _arreter(eid, doc: dict) -> bool:
    """Arrêt automatique : la fiche a répondu, est passée plus loin, a disparu, ou son canal n'est plus possible
    (consentement retiré, base légale changée : relecture I3). Fiche effacée ou opposée : textes vidés (I1)."""
    if not doc["sequences"]:
        return False
    fiches = _fiches(eid)
    change = False
    for s in doc["sequences"]:
        f = fiches.get(s.get("pid"))
        st = f["statut"] if f else None
        a_vider = (f is None or st == "oppose") and any(e.get("texte") or e.get("objet") for e in s["etapes"])
        if s.get("statut") not in EN_COURS and not a_vider:
            continue
        if f is None or st in ARRET:
            _stopper(s, f"fiche:{st}" if st else "effacee", effacer=(f is None or st == "oppose"))
        elif s["canal"] not in [c["canal"] for c in _sc.canaux_possibles(f)]:
            _stopper(s, "canal")
        else:
            continue
        change = True
    return change


def pour_export(eid, pid) -> list:
    """Les séquences d'une fiche, telles quelles (droit d'accès ; espace archivé compris) : lecture seule."""
    with _verrou:
        try:
            return [json.loads(json.dumps(s)) for s in _lire(eid)["sequences"] if s.get("pid") == pid]
        except RefusSequence:
            return []


def oublier(eid, pid) -> None:
    """RGPD (relecture I1) : la fiche est effacée, opposée ou purgée — ses séquences s'arrêtent et perdent leurs textes
    TOUT DE SUITE. Appelé par `prospects` hors de son verrou ; n'appelle jamais `prospects`."""
    with _verrou:
        try:
            doc = _lire(eid)
        except RefusSequence:
            logger.warning(f"séquences de {eid} illisibles : textes de {pid} non vidés (le seront à la lecture)")
            return
        touchees = [s for s in doc["sequences"] if s.get("pid") == pid]
        for s in touchees:
            _stopper(s, "effacee", effacer=True)
        if touchees:
            _poser(eid, doc)


def _charger(eid) -> dict:
    doc = _lire(eid)
    if _arreter(eid, doc):
        _poser(eid, doc)
    return doc


# ---- contrôles --------------------------------------------------------------------------------------------------------

def _canal_possible(fiche: dict, canal: str) -> None:
    if fiche.get("statut") not in STATUTS_FICHE:
        raise RefusSequence(f"prospect au statut « {fiche.get('statut')} » : seule une fiche qualifiée ou contactée "
                            "reçoit une séquence", "etat")
    if canal not in [c["canal"] for c in _sc.canaux_possibles(fiche)]:
        raise RefusSequence(f"canal impossible pour ce prospect : {_txt(canal, 20)} (consentement ou base légale)", "canal")


def _interdits(textes: list, interdits) -> list:
    motifs = [(m, re.compile(r"(?<!\w)" + re.escape(m) + r"(?!\w)", re.IGNORECASE))
              for m in (str(x).strip() for x in interdits or []) if m]
    return sorted({m for m, pat in motifs for t in textes if pat.search(t)})


def _etapes(canal: str, etapes, interdits) -> list:
    if not isinstance(etapes, list) or not 1 <= len(etapes) <= MAX_ETAPES:
        raise RefusSequence(f"une séquence a de 1 à {MAX_ETAPES} étapes (1er message et 2 relances au plus)", "champ")
    out, textes = [], []
    for i, e in enumerate(etapes):
        if not isinstance(e, dict):
            raise RefusSequence("étape illisible", "champ")
        texte, objet = str(e.get("texte") or "").strip(), str(e.get("objet") or "").strip()
        d = e.get("delai_jours", 0)
        if isinstance(d, bool) or not isinstance(d, int):
            raise RefusSequence("délai en jours entiers", "champ")
        if not texte:
            raise RefusSequence(f"étape {i + 1} : texte vide", "champ")
        if len(texte) > LONGUEURS[canal]:
            raise RefusSequence(f"étape {i + 1} : texte trop long ({LONGUEURS[canal]} caractères au plus)", "champ")
        if canal == "email" and (not objet or len(objet) > MAX_OBJET):
            raise RefusSequence(f"étape {i + 1} : objet de l'e-mail requis ({MAX_OBJET} caractères au plus)", "champ")
        if i == 0 and d != 0:
            raise RefusSequence("le 1er message part sans délai (0 jour)", "champ")
        if i > 0 and not DELAI_MIN <= d <= DELAI_MAX:
            raise RefusSequence(f"une relance attend de {DELAI_MIN} à {DELAI_MAX} jours", "champ")
        textes += [texte, objet]
        out.append({"rang": i, "objet": objet if canal == "email" else "", "texte": texte, "delai_jours": d,
                    "quand": None, "statut": "brouillon", "envoye_le": None})
    fautifs = _interdits(textes, interdits)
    if fautifs:
        raise RefusSequence("mots interdits de l'espace : " + ", ".join(fautifs) + " — réécris ces textes sans eux", "interdit")
    return out


# ---- heures calmes, plafond -------------------------------------------------------------------------------------------

def _agent(eid) -> dict:
    from app.services import whatsapp as _wa
    try:
        return _wa.reglages(eid)["agent"]
    except Exception:  # noqa: BLE001 — réglages illisibles : les horaires par défaut (lun-ven 9 h-18 h)
        return _wa._agent_complet(None)


def prochain_calme(agent: dict, t: datetime) -> datetime:
    """Le premier instant >= t dans les horaires de l'agent de l'espace (pas de 15 min, 8 jours au plus). Hors horaires,
    l'instant est d'abord arrondi au quart d'heure suivant : l'étape tombe à l'ouverture pile (9 h 00), pas à 9 h 01 min 36."""
    from app.services import whatsapp as _wa
    if _wa.dans_horaires(agent, t):
        return t
    t = t.replace(second=0, microsecond=0)
    t = t + timedelta(minutes=(-t.minute) % 15)
    fin = t + timedelta(days=8)
    while t < fin:
        if _wa.dans_horaires(agent, t):
            return t
        t = t + PAS
    raise RefusSequence("aucun créneau dans les horaires de l'espace (réglages de l'agent WhatsApp)", "plafond")


def plafond_email(depuis: date, jour: date) -> int:
    n = (jour - depuis).days
    return PLAFONDS_EMAIL[0] if n < 7 else PLAFONDS_EMAIL[1] if n < 14 else PLAFONDS_EMAIL[2]


def _quand_depart(debut) -> datetime:
    now = _maintenant()
    if debut in (None, ""):
        return now
    try:
        t = datetime.fromisoformat(str(debut).strip().replace("Z", "+00:00"))
    except ValueError:
        raise RefusSequence("date de départ illisible (ISO 8601)", "champ") from None
    t = t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)
    return max(t, now)


# ---- gestes -----------------------------------------------------------------------------------------------------------

def lien(fiche: dict, canal: str) -> str | None:
    """L'adresse à ouvrir pour un envoi manuel (profil X / Instagram, URL LinkedIn de la fiche), sinon None."""
    for c in fiche.get("canaux") or []:
        if c.get("type") != canal:
            continue
        v = str(c.get("valeur") or "").strip()
        if canal == "x" and _X.match(v):
            return "https://x.com/" + _X.match(v).group(1)
        if canal == "instagram" and _INSTA.match(v):
            return "https://www.instagram.com/" + _INSTA.match(v).group(1) + "/"
        if canal == "linkedin" and _LINKEDIN.match(v):
            return v
    return None


def lister(eid, pid=None) -> list:
    """Les séquences (plus récentes d'abord) ; chaque étape porte `due` (planifiée et à l'heure) ; `ouvrir` pour un canal
    manuel."""
    _espace(eid)
    with _verrou:
        doc = _charger(eid)
    seqs = [s for s in doc["sequences"] if pid in (None, "") or s.get("pid") == pid]
    fiches = _fiches(eid) if any(s.get("canal") in CANAUX_MANUELS for s in seqs) else {}
    now = _maintenant()
    out = []
    for s in sorted(seqs, key=lambda x: x.get("cree_le") or "", reverse=True):
        s = json.loads(json.dumps(s))
        for e in s["etapes"]:
            e["due"] = bool(e["statut"] == "planifiee" and e.get("quand") and datetime.fromisoformat(e["quand"]) <= now)
        s["ouvrir"] = lien(fiches.get(s["pid"]) or {}, s["canal"]) if s["canal"] in CANAUX_MANUELS else None
        out.append(s)
    return out


def proposer(eid, pid, canal, etapes, interdits=(), qui: str = "agent") -> dict:
    _espace(eid)
    if canal not in LONGUEURS:
        raise RefusSequence(f"canal inconnu : {_txt(canal, 20)}", "champ")
    propres = _etapes(canal, etapes, interdits)
    with _verrou:
        fiche = _fiche(eid, pid)
        _canal_possible(fiche, canal)
        doc = _charger(eid)
        for s in doc["sequences"]:
            if s["pid"] == pid and s["canal"] == canal and s["statut"] in ("validee", "planifiee"):
                raise RefusSequence("une séquence est déjà validée sur ce canal pour ce prospect : annulez-la d'abord", "etat")
        for s in doc["sequences"]:
            if s["pid"] == pid and s["canal"] == canal and s["statut"] == "proposee":
                s["statut"], s["motif"] = "annulee", "remplacee"
                for e in s["etapes"]:
                    e["statut"] = "annulee"
                _noter(s, "remplacee", qui)
        s = {"id": "sq_" + uuid.uuid4().hex[:8], "pid": pid, "canal": canal, "statut": "proposee", "etapes": propres,
             "cree_le": _es._maintenant(), "cree_par": qui if qui in _p.QUI else "agent", "valide_le": None,
             "planifie_le": None, "motif": None, "historique": []}
        _noter(s, "proposee", s["cree_par"])
        doc["sequences"].append(s)
        _poser(eid, doc)
    return s


def valider(eid, sid, qui: str = "utilisateur") -> dict:
    """La porte humaine : l'utilisateur seul."""
    if qui != "utilisateur":
        raise RefusSequence("seul l'utilisateur valide une séquence", "etat")
    _espace(eid)
    with _verrou:
        doc = _charger(eid)
        s = _trouver(doc, sid)
        if s["statut"] != "proposee":
            raise RefusSequence(f"séquence « {s['statut']} » : rien à valider", "etat")
        _canal_possible(_fiche(eid, s["pid"]), s["canal"])
        s["statut"], s["valide_le"] = "validee", _es._maintenant()
        for e in s["etapes"]:
            e["statut"] = "validee"
        _noter(s, "validee", qui)
        _poser(eid, doc)
    return s


def annuler(eid, sid, qui: str = "utilisateur") -> dict:
    _espace(eid)
    with _verrou:
        doc = _charger(eid)
        s = _trouver(doc, sid)
        if s["statut"] not in EN_COURS:
            raise RefusSequence(f"séquence « {s['statut']} » : rien à annuler", "etat")
        s["statut"], s["motif"] = "annulee", "annulee"
        for e in s["etapes"]:
            if e["statut"] != "envoyee":
                e["statut"] = "annulee"
        _noter(s, "annulee", qui if qui in _p.QUI else "utilisateur")
        _poser(eid, doc)
    return s


def _emails_du_jour(doc: dict, tz, jour: date, sauf: str) -> int:
    n = 0
    for s in doc["sequences"]:
        if s["canal"] != "email" or s["id"] == sauf:
            continue
        for e in s["etapes"]:
            if e["statut"] in ("planifiee", "envoyee") and e.get("quand") \
                    and datetime.fromisoformat(e["quand"]).astimezone(tz).date() == jour:
                n += 1
    return n


def planifier(eid, sid, debut=None, qui: str = "utilisateur") -> dict:
    """Une séquence VALIDÉE : canal revérifié, chaque étape posée dans les heures calmes de l'espace, e-mail sous le
    plafond du jour (un jour plein repousse au suivant)."""
    _espace(eid)
    t = _quand_depart(debut)
    agent = _agent(eid)
    tz = ZoneInfo(agent["horaires"]["fuseau"])
    with _verrou:
        doc = _charger(eid)
        s = _trouver(doc, sid)
        if s["statut"] != "validee":
            raise RefusSequence("seule une séquence validée par l'utilisateur se planifie", "etat")
        _canal_possible(_fiche(eid, s["pid"]), s["canal"])
        pris: dict = {}
        depuis = date.fromisoformat(doc["email_depuis"]) if doc.get("email_depuis") else None
        quand = []
        for e in s["etapes"]:
            base = t if e["rang"] == 0 else quand[-1] + timedelta(days=e["delai_jours"])
            q = prochain_calme(agent, base)
            if s["canal"] == "email":
                for _ in range(JOURS_REPORT):
                    jour = q.astimezone(tz).date()
                    d0 = depuis or jour
                    if _emails_du_jour(doc, tz, jour, sid) + pris.get(jour, 0) < plafond_email(d0, jour):
                        break
                    lendemain = datetime.combine(jour + timedelta(days=1), datetime.min.time(), tz).astimezone(timezone.utc)
                    q = prochain_calme(agent, lendemain)
                else:
                    raise RefusSequence(f"plafond e-mail atteint pour les {JOURS_REPORT} prochains jours", "plafond")
                jour = q.astimezone(tz).date()
                pris[jour] = pris.get(jour, 0) + 1
                depuis = depuis or jour
            quand.append(q)
        for e, q in zip(s["etapes"], quand):
            e["quand"], e["statut"] = q.astimezone(timezone.utc).isoformat(), "planifiee"
        if s["canal"] == "email" and not doc.get("email_depuis"):
            doc["email_depuis"] = depuis.isoformat()
        s["statut"], s["planifie_le"] = "planifiee", _es._maintenant()
        _noter(s, "planifiee", qui if qui in _p.QUI else "utilisateur")
        _poser(eid, doc)
    return s


# ---- t356 : ce que lisent les envois automatiques (e-mail P5, WhatsApp P6) --------------------------------------------

def etapes_dues(eid, canal: str) -> list:
    """Les étapes à envoyer maintenant sur `canal` : séquence planifiée, étape planifiée à l'heure, les précédentes
    envoyées. L'arrêt automatique (fiche, canal, registre) s'applique d'abord ; registre indisponible : 503."""
    _espace(eid)
    now = _maintenant()
    with _verrou:
        doc = _charger(eid)
    out = []
    for s in doc["sequences"]:
        if s["canal"] != canal or s["statut"] != "planifiee":
            continue
        for e in s["etapes"]:
            if e["statut"] == "envoyee":
                continue
            avant = s["etapes"][e["rang"] - 1] if e["rang"] > 0 else None
            # relecture t356 (I4) : une relance se compte depuis l'envoi RÉEL de l'étape d'avant (jamais en rafale)
            reel = avant and avant.get("envoye_utc") and \
                datetime.fromisoformat(avant["envoye_utc"]) + timedelta(days=e["delai_jours"]) > now
            if e["statut"] == "planifiee" and e.get("quand") and datetime.fromisoformat(e["quand"]) <= now and not reel:
                out.append({"sid": s["id"], "rang": e["rang"], "pid": s["pid"], "objet": e["objet"], "texte": e["texte"]})
            break
    return out


def _etape(doc: dict, sid, rang) -> tuple:
    s = _trouver(doc, sid)
    if not isinstance(rang, int) or not 0 <= rang < len(s["etapes"]):
        raise RefusSequence("étape inconnue", "inconnu")
    return s, s["etapes"][rang]


def encore_due(eid, sid, rang) -> bool:
    """Juste avant l'envoi (relecture t356 M1) : la séquence est toujours planifiée et l'étape aussi."""
    with _verrou:
        try:
            s, e = _etape(_lire(eid), sid, rang)
        except RefusSequence:
            return False
    return s["statut"] == "planifiee" and e["statut"] == "planifiee"


def noter_envoi(eid, sid, rang, message_id: str) -> dict:
    """Un envoi automatique réussi : l'étape passe « envoyée » avec son Message-ID ; la dernière termine la séquence
    (une séquence arrêtée entre-temps le reste)."""
    with _verrou:
        doc = _lire(eid)
        s, e = _etape(doc, sid, rang)
        e["statut"], e["envoye_le"], e["message_id"] = "envoyee", _es._maintenant(), str(message_id or "")[:300]
        e["envoye_utc"] = _maintenant().isoformat()
        if s["statut"] == "planifiee" and all(x["statut"] == "envoyee" for x in s["etapes"]):
            s["statut"] = "terminee"
        _noter(s, f"envoyee:{rang}", "systeme")
        _poser(eid, doc)
    return s


def noter_essai(eid, sid, rang) -> int:
    """Un échec passager : rend le nombre d'essais de l'étape."""
    with _verrou:
        doc = _lire(eid)
        s, e = _etape(doc, sid, rang)
        e["essais"] = int(e.get("essais") or 0) + 1
        _poser(eid, doc)
    return e["essais"]


def arreter(eid, sid, motif: str) -> None:
    """Arrêt par le canal (rebond, échec répété) : étapes non envoyées annulées."""
    with _verrou:
        doc = _lire(eid)
        _stopper(_trouver(doc, sid), motif)
        _poser(eid, doc)


def marquer_envoye(eid, sid, rang, qui: str = "utilisateur") -> dict:
    """Un envoi MANUEL fait par l'utilisateur (X, Instagram, LinkedIn) : l'étape passe « envoyée », la fiche note un
    contact sortant et passe « contacté » si elle était « qualifié »."""
    _espace(eid)
    with _verrou:
        doc = _charger(eid)
        s = _trouver(doc, sid)
        if s["canal"] not in CANAUX_MANUELS:
            raise RefusSequence("cette étape part par l'envoi automatique du canal, pas à la main", "canal")
        if s["statut"] != "planifiee":
            raise RefusSequence(f"séquence « {s['statut']} » : rien à envoyer", "etat")
        if isinstance(rang, bool) or not isinstance(rang, int) or not 0 <= rang < len(s["etapes"]):
            raise RefusSequence("étape inconnue", "inconnu")
        e = s["etapes"][rang]
        if e["statut"] != "planifiee" or any(x["statut"] != "envoyee" for x in s["etapes"][:rang]):
            raise RefusSequence("étape déjà envoyée, annulée, ou une étape précédente n'est pas envoyée", "etat")
        fiche = _fiche(eid, s["pid"])
        try:
            _p.noter_contact(eid, s["pid"], "sortant", f"{s['canal']} : message {rang + 1} envoyé à la main", qui)
            if fiche["statut"] == "qualifie":
                _p.changer_statut(eid, s["pid"], "contacte", "1er message envoyé", qui)
        except _p.RefusProspect as x:
            raise RefusSequence(x.message, x.code if x.code in _HTTP else "etat") from None
        e["statut"], e["envoye_le"], e["envoye_utc"] = "envoyee", _es._maintenant(), _maintenant().isoformat()
        if all(x["statut"] == "envoyee" for x in s["etapes"]):
            s["statut"] = "terminee"
        _noter(s, f"envoyee:{rang}", qui)
        _poser(eid, doc)
    return s
