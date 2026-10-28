# -*- coding: utf-8 -*-
"""t315 (28/10/2026) (lot D1 « capture façon streaming ») — les SESSIONS DE CAPTURE de l'app : pistes brutes reçues
morceau par morceau, piste des clics relue et identifiée, clôture. Plan docs/superpowers/plans/2026-10-28-t315-capture.md,
spec 2026-10-25-boite-a-outils-design.md §8.1-8.3.

Une session vit dans `DATA_ROOT/captures/<id>/` :
- `session.json`       {id, cree_utc, debut_ms, fin_ms, etat (en_cours | terminee | abandonnee), options, pistes} ;
- `<piste>.<ext>`      les morceaux d'une MediaRecorder mis bout à bout DANS L'ORDRE (scene, ecran, camera, voix) ;
- `<id>.dzclics.json`  la piste des clics (écrite à la clôture, format au §« Contrat pour t316-t319 » du plan).

La piste des clics est une donnée du NAVIGATEUR : elle est relue champ par champ (liste blanche), jamais crue. Elle ne
contient ni touche, ni valeur saisie, ni chemin ou nom de fichier (spec §8.7, choix 11) : un champ inconnu est retiré,
un type inconnu (« touche »…) est retiré, un texte qui ressemble à un fichier est vidé. L'élément cliqué est
reconnu par le catalogue de « Demander » (`agent_aide.rapprocher`, côté serveur).
Aucun réseau, aucune dépense. Journaux : identifiants, tailles et nombres seulement."""
from __future__ import annotations

import json
import re
import secrets
import shutil
import threading
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from app.config import DATA_ROOT

PISTES = ("scene", "ecran", "camera", "voix")
# type MIME de base (avant « ; codecs= ») -> extension ; la voix est audio, les autres pistes sont vidéo
MIMES = {"video/webm": ".webm", "video/mp4": ".mp4", "audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".m4a"}
MAX_MORCEAU = 16 * 1024 * 1024          # une seconde de MediaRecorder pèse bien moins
MAX_PISTE = 4 * 1024 * 1024 * 1024      # 4 Go par piste
MAX_EVENEMENTS = 20000
MAX_LIBELLE = 40                         # comme le relevé de « Demander » (dz-agent-logique.js)
MAX_INFOBULLE = 80
MAX_ECRAN = 40
MODES = ("app", "onglet")
FORMES = ("cercle", "carre", "vif")
ID = re.compile(r"^[a-f0-9]{16}$")
ECRAN_SUR = re.compile(r"^[a-z0-9_-]{1,40}$")
# un nom de fichier ou un chemin (même motif que agent_aide.FICHIER, le relevé de « Demander »)
FICHIER = re.compile(r"(?i)\.(png|jpe?g|webp|gif|svg|mp4|mov|webm|mkv|wav|mp3|ogg|flac|psd|tiff?|bmp|pdf|json|glb|gltf"
                     r"|fbx|obj|stl|blend|zip|txt|docx?|xlsx?|csv)\b|[\\/][A-Za-z]|^[A-Za-z]:")
BALISES = re.compile(r"^[a-z][a-z0-9-]{0,20}$")
ROLES = re.compile(r"^[a-z]{1,20}$")

_VERROU = threading.Lock()


class RefusCapture(ValueError):
    """Une demande refusée : `statut` = le code HTTP (400, 404, 409, 413, 415). Levée avec un message littéral (L10)."""
    def __init__(self, message: str, statut: int):
        super().__init__(message)
        self.statut = statut


def racine() -> Path:
    return DATA_ROOT / "captures"


def _dossier(cid: str) -> Path:
    if not isinstance(cid, str) or not ID.match(cid):
        raise RefusCapture("Identifiant de capture invalide.", 400)
    return racine() / cid


def _maintenant_ms() -> int:
    return int(time.time() * 1000)


def _lire_session(cid: str) -> dict:
    f = _dossier(cid) / "session.json"
    if not f.is_file():
        raise RefusCapture("Capture introuvable.", 404)
    return json.loads(f.read_text("utf-8"))


def _ecrire_session(s: dict) -> None:
    d = _dossier(s["id"])
    tmp = d / "session.json.tmp"
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(d / "session.json")


def options_lues(o) -> dict:
    """Les options de la boîte de départ, relues : mode app | onglet, drapeaux booléens, forme de l'encart."""
    o = o if isinstance(o, dict) else {}
    b = lambda k, d=False: bool(o.get(k, d)) if isinstance(o.get(k, d), bool) else d   # noqa: E731
    return {
        "mode": o.get("mode") if o.get("mode") in MODES else "app",
        "voix": b("voix", True), "camera": b("camera"), "clics": b("clics", True), "halo": b("halo", True),
        "zoom": b("zoom"), "son_onglet": b("son_onglet"), "element_capture": b("element_capture"),
        "preuve": b("preuve"), "forme": o.get("forme") if o.get("forme") in FORMES else "cercle",
    }


def creer(options=None) -> dict:
    """Une session neuve : son dossier et son `session.json` (état en_cours)."""
    cid = secrets.token_hex(8)
    d = racine() / cid
    d.mkdir(parents=True, exist_ok=False)
    s = {"id": cid, "cree_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "debut_ms": _maintenant_ms(), "fin_ms": None, "etat": "en_cours", "options": options_lues(options),
         "pistes": {}}
    with _VERROU:
        _ecrire_session(s)
    return s


def _mime(mime: str, piste: str) -> str:
    base = str(mime or "").split(";", 1)[0].strip().lower()
    if base not in MIMES or (piste == "voix") != base.startswith("audio/"):
        raise RefusCapture("Format de piste refusé : vidéo WebM ou MP4, voix WebM, Ogg ou MP4.", 415)
    return base


def ajouter_morceau(cid: str, piste: str, n: int, octets: bytes, mime: str) -> dict:
    """Ajoute le morceau `n` (0, 1, 2… dans l'ordre) au bout de la piste. Un morceau hors ordre, trop lourd, d'un
    autre format que les précédents ou d'une session close est refusé sans rien écrire."""
    if piste not in PISTES:
        raise RefusCapture("Piste inconnue : scene, ecran, camera ou voix.", 400)
    if len(octets) > MAX_MORCEAU:
        raise RefusCapture("Morceau trop lourd : 16 Mo au plus.", 413)
    base = _mime(mime, piste)
    with _VERROU:
        s = _lire_session(cid)
        if s["etat"] != "en_cours":
            raise RefusCapture("Cette capture est close.", 409)
        p = s["pistes"].get(piste) or {"mime": base, "ext": MIMES[base], "morceaux": 0, "octets": 0}
        if p["mime"] != base:
            raise RefusCapture("Le format de la piste a changé en cours d'enregistrement.", 409)
        attendu = p["morceaux"]
        if n != attendu:
            raise RefusCapture(f"Morceau hors ordre : la piste attend le morceau {attendu}.", 409)
        if p["octets"] + len(octets) > MAX_PISTE:
            raise RefusCapture("Piste trop longue : 4 Go au plus.", 413)
        with open(_dossier(cid) / f"{piste}{p['ext']}", "ab") as f:
            f.write(octets)
        p["morceaux"] += 1
        p["octets"] += len(octets)
        s["pistes"][piste] = p
        _ecrire_session(s)
    return {"piste": piste, "recu": n, "octets": p["octets"]}


def chemin_piste(cid: str, piste: str) -> Path | None:
    if piste not in PISTES:
        raise RefusCapture("Piste inconnue : scene, ecran, camera ou voix.", 400)
    s = _lire_session(cid)
    p = s["pistes"].get(piste)
    f = _dossier(cid) / f"{piste}{p['ext']}" if p else None
    return f if f and f.is_file() else None


# ── la piste des clics ──

def _texte(v, n: int) -> str:
    """Un libellé affichable : sans contrôle ni format Unicode, espaces réduits, borné ; vidé s'il nomme un fichier."""
    if not isinstance(v, str):
        return ""
    v = "".join(c for c in v if not unicodedata.category(c).startswith("C"))
    v = " ".join(v.split())[:n]
    return "" if FICHIER.search(v) else v


def _nombre(v, lo: float, hi: float):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:      # NaN
        return None
    return max(lo, min(hi, float(v)))


def _ecran(v) -> str:
    return v if isinstance(v, str) and ECRAN_SUR.match(v) else ""


def nettoyer_clics(doc, duree_ms: int) -> list[dict]:
    """Les événements de la piste envoyée par le navigateur, relus par LISTE BLANCHE et triés par `t`. Types gardés :
    `clic` et `ecran` (les générations sont ajoutées par le serveur). Tout le reste est retiré."""
    evts = doc.get("evenements") if isinstance(doc, dict) else None
    if not isinstance(evts, list):
        return []
    fin = max(0, int(duree_ms or 0)) + 5000
    out = []
    for e in evts[:MAX_EVENEMENTS]:
        if not isinstance(e, dict):
            continue
        t = _nombre(e.get("t"), 0, fin)
        if t is None:
            continue
        if e.get("type") == "ecran":
            ec = _ecran(e.get("ecran"))
            if ec:
                out.append({"type": "ecran", "t": int(t), "ecran": ec})
        elif e.get("type") == "clic":
            x, y = _nombre(e.get("x"), 0, 1), _nombre(e.get("y"), 0, 1)
            if x is None or y is None:
                continue
            b = e.get("bouton")
            c = {"type": "clic", "t": int(t), "x": round(x, 4), "y": round(y, 4),
                 "bouton": b if b in (0, 1, 2) else 0, "ecran": _ecran(e.get("ecran"))}
            src = e.get("cible") if isinstance(e.get("cible"), dict) else {}
            balise = src.get("balise") if isinstance(src.get("balise"), str) else ""
            role = src.get("role") if isinstance(src.get("role"), str) else ""
            cible = {"balise": balise.lower() if BALISES.match(balise.lower()) else "",
                     "role": role.lower() if ROLES.match(role.lower()) else "", "t": "", "i": ""}
            if e.get("secret") is True:
                c["secret"] = True              # dans une zone masquée : ni libellé ni infobulle
            else:
                cible["t"], cible["i"] = _texte(src.get("t"), MAX_LIBELLE), _texte(src.get("i"), MAX_INFOBULLE)
            c["cible"] = cible
            out.append(c)
    out.sort(key=lambda x: x["t"])
    return out


def identifier(evts: list[dict]) -> list[dict]:
    """Pose `fiche` (id du catalogue de « Demander », ou None) sur chaque clic, d'après son libellé ou son infobulle et
    l'écran du clic (agent_aide.rapprocher : exact, gabarit, début des textes longs ; jamais une fiche d'un autre
    écran)."""
    from app.services import agent_aide
    for e in evts:
        if e["type"] != "clic":
            continue
        c = e["cible"]
        fiche = None
        if c["t"] or c["i"]:
            try:
                r = agent_aide.rapprocher([{"t": c["t"], "i": c["i"]}], e.get("ecran") or "")
                fiche = r["reconnus"][0]["id"] if r["reconnus"] else None
            except Exception:  # noqa: BLE001 — un catalogue illisible ne perd pas la capture
                fiche = None
        e["fiche"] = fiche
    return evts


def clore(cid: str, clics, duree_ms, cadre=None, generations=()) -> dict:
    """Clôt la session : piste des clics nettoyée, identifiée, complétée des générations, écrite dans
    `<id>.dzclics.json` ; état `terminee`. Rend {session, clics}. Une session déjà close est refusée (409)."""
    duree = int(_nombre(duree_ms, 0, 24 * 3600 * 1000) or 0)
    evts = identifier(nettoyer_clics(clics, duree))
    evts = sorted(evts + [g for g in generations if isinstance(g, dict)], key=lambda x: x["t"])
    cadre = cadre if isinstance(cadre, dict) else {}
    with _VERROU:
        s = _lire_session(cid)
        if s["etat"] != "en_cours":
            raise RefusCapture("Cette capture est close.", 409)
        doc = {"version": 1, "id": cid, "debut_utc": s["cree_utc"], "duree_ms": duree,
               "cadre": {"largeur": int(_nombre(cadre.get("largeur"), 0, 16384) or 0),
                         "hauteur": int(_nombre(cadre.get("hauteur"), 0, 16384) or 0),
                         "mode": s["options"]["mode"]},
               "evenements": evts}
        (_dossier(cid) / f"{cid}.dzclics.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")
        s["etat"], s["fin_ms"], s["duree_ms"] = "terminee", _maintenant_ms(), duree
        _ecrire_session(s)
    return {"session": s, "clics": doc}


def abandonner(cid: str) -> dict:
    """Une session en cours abandonnée (« Annuler », échec au départ) : ses pistes sont effacées, son état gardé."""
    with _VERROU:
        s = _lire_session(cid)
        if s["etat"] != "en_cours":
            raise RefusCapture("Cette capture est close.", 409)
        for f in _dossier(cid).iterdir():
            if f.name != "session.json":
                f.unlink(missing_ok=True)
        s["etat"], s["fin_ms"], s["pistes"] = "abandonnee", _maintenant_ms(), {}
        _ecrire_session(s)
    return s


def lire(cid: str) -> dict:
    """La session et sa piste des clics (None tant qu'elle n'est pas close)."""
    s = _lire_session(cid)
    f = _dossier(cid) / f"{cid}.dzclics.json"
    return {"session": s, "clics": json.loads(f.read_text("utf-8")) if f.is_file() else None}


def copier_scene(cid: str, dest_dossier: Path) -> Path:
    """Copie la piste « scene » vers la Bibliothèque : `capture_<AAAAMMJJ-HHMMSS>_<id>.<ext>` ; refus si vide."""
    src = chemin_piste(cid, "scene")
    if src is None or src.stat().st_size == 0:
        raise RefusCapture("La capture n'a reçu aucune image.", 409)
    dest_dossier.mkdir(parents=True, exist_ok=True)
    dest = dest_dossier / f"capture_{datetime.now().strftime('%Y%m%d-%H%M%S')}_{cid}{src.suffix}"
    shutil.copyfile(src, dest)
    return dest
