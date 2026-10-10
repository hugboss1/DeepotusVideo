# -*- coding: utf-8 -*-
"""Avatar live G0 (t161, 10/10/2026) — le socle du Direct : Personnages (images de référence + voix + consentement)
et sessions Decart Lucy 2.5 bornées. Spec : docs/superpowers/specs/2026-10-10-higgsfield-genjutsu-inventaire.md.

Relevé le 10/10 dans @decartai/sdk 0.2.8 et la doc Decart :
  - le flux vidéo va du navigateur (ou du téléphone) à Decart EN DIRECT, par WebRTC : le backend ne voit jamais une
    image ; il ne fait que frapper un jeton client (POST /v1/client/tokens, en-tête X-API-KEY) ;
  - un jeton expiré n'arrête PAS une session déjà ouverte — seul `constraints.realtime.maxSessionDuration` la borne.
    C'est donc lui qui porte le plafond : la garde réserve le devis de la durée ENTIÈRE, Decart coupe à la borne ;
  - Lucy 2.5 : 0,02 $/s, 0,04 $/s en mode rapide, à la seconde de génération active. La fin de session note le réel
    (secondes rapportées, bornées) à la place du devis.

Les Personnages vivent dans DATA_ROOT/personnages/<id>/ : fiche.json + ref_<n>.png (ré-encodés par Pillow : aucun
octet reçu n'est écrit tel quel). Les sessions vivent EN MÉMOIRE (une session dure au plus 30 minutes ; un
redémarrage les oublie et laisse le devis, sens sûr pour un plafond)."""
import base64
import io
import json
import re
import secrets as _secrets
import shutil
import time
from datetime import datetime

import httpx
from loguru import logger

from app.config import DATA_ROOT, SSL_VERIFY, settings

BASE_URL = "https://api.decart.ai"
MODELE = "lucy-2.5"
DUREE_MIN_S = 10            # minimum de maxSessionDuration chez Decart
DUREE_MAX_S = 1800          # 30 minutes : au-delà, on rouvre une session (et la garde repasse)
DUREE_DEFAUT_S = 300
TTL_JETON_S = 60            # le temps de se connecter ; n'arrête pas la session
IMAGES_MAX = 8
COTE_MIN_PX = 256           # Decart recommande 512 ; sous 256 le visage est illisible
COTE_MAX_PX = 2048          # ré-échantillonné au-delà
TEXTE_CONSENTEMENT = ("J'ai le droit d'utiliser ce visage et cette voix : ce sont les miens, ou la personne m'a donné "
                      "son accord pour les cloner.")

_RACINE = DATA_ROOT / "personnages"
_ID = re.compile(r"^[a-f0-9]{16}$")

#: session_id -> {personnage_id, duree_s, prix_usd_s, ref, appareil (id ou None pour le PC), ouverte}
_SESSIONS: dict[str, dict] = {}


class Refus(Exception):
    """Refus métier : (statut HTTP, message)."""

    def __init__(self, statut: int, message: str):
        super().__init__(message)
        self.statut = statut
        self.message = message


def prix_usd_s(rapide: bool = False) -> float:
    from app.services import pricing as _pricing
    p = _pricing.load()
    base = float(p.get("decart_realtime_usd_per_s", 0.02))
    return base * (2 if rapide else 1)


def borner_duree(v) -> int:
    """Durée demandée -> secondes entières dans [10, 1800] ; illisible -> 300."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return DUREE_DEFAUT_S
    if f != f or f in (float("inf"), float("-inf")):
        return DUREE_DEFAUT_S
    return int(max(DUREE_MIN_S, min(DUREE_MAX_S, round(f))))


def cle_presente() -> bool:
    return bool((getattr(settings, "DECART_API_KEY", "") or "").strip())


# ── Personnages ─────────────────────────────────────────────────────────────────────────────────────────────────────

def _dossier(pid: str):
    if not isinstance(pid, str) or not _ID.match(pid):
        return None
    d = _RACINE / pid
    return d if (d / "fiche.json").is_file() else None


def _image_png(b64: str) -> bytes:
    from PIL import Image, UnidentifiedImageError
    try:
        brut = base64.b64decode(b64 or "", validate=False)
    except (ValueError, TypeError):
        raise Refus(415, "Image illisible (base64 invalide).")
    try:
        im = Image.open(io.BytesIO(brut))
        im.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise Refus(415, "Ces octets ne sont pas une image (PNG, JPEG ou WebP).")
    w, h = im.size
    if min(w, h) < COTE_MIN_PX:
        raise Refus(400, f"Image trop petite ({w}×{h}) : {COTE_MIN_PX} px au moins sur le petit côté (512 conseillés).")
    im = im.convert("RGB")
    if max(w, h) > COTE_MAX_PX:
        im.thumbnail((COTE_MAX_PX, COTE_MAX_PX))
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def _publique(f: dict) -> dict:
    return {"id": f["id"], "nom": f["nom"], "images": f["images"], "voix": f.get("voix") or {},
            "consentement": f["consentement"], "cree": f["cree"]}


def creer_personnage(corps: dict, origine: str = "pc") -> dict:
    corps = corps if isinstance(corps, dict) else {}
    if corps.get("consentement") is not True:
        raise Refus(400, "Consentement requis : cochez « " + TEXTE_CONSENTEMENT + " »")
    nom = re.sub(r"\s+", " ", str(corps.get("nom") or "")).strip()[:60] or "Personnage"
    images = corps.get("images")
    if not isinstance(images, list) or not images:
        raise Refus(400, "Au moins une image de référence (visage de face, bien éclairé).")
    if len(images) > IMAGES_MAX:
        raise Refus(400, f"{IMAGES_MAX} images au plus.")
    pngs = [_image_png(b) for b in images]          # tout est vérifié AVANT d'écrire quoi que ce soit
    voix = corps.get("voix") if isinstance(corps.get("voix"), dict) else {}
    voix = {k: str(voix.get(k))[:80] for k in ("fournisseur", "voice_id") if voix.get(k)}
    pid = _secrets.token_hex(8)
    d = _RACINE / pid
    d.mkdir(parents=True, exist_ok=False)
    for i, b in enumerate(pngs):
        (d / f"ref_{i}.png").write_bytes(b)
    fiche = {"id": pid, "nom": nom, "images": len(pngs), "voix": voix, "cree": datetime.now().isoformat(timespec="seconds"),
             "consentement": {"texte": TEXTE_CONSENTEMENT, "le": datetime.now().isoformat(timespec="seconds"),
                              "origine": origine}}
    (d / "fiche.json").write_text(json.dumps(fiche, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"avatar_live: Personnage {pid} « {nom} » ({len(pngs)} images, consentement {origine})")
    return _publique(fiche)


def lire_personnage(pid: str) -> dict | None:
    d = _dossier(pid)
    if d is None:
        return None
    try:
        return _publique(json.loads((d / "fiche.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError):
        return None


def lister_personnages() -> list[dict]:
    if not _RACINE.is_dir():
        return []
    out = [lire_personnage(p.name) for p in _RACINE.iterdir() if p.is_dir()]
    return sorted([f for f in out if f], key=lambda f: f["cree"])


def chemin_image(pid: str, n) -> str | None:
    f = lire_personnage(pid)
    try:
        n = int(n)
    except (TypeError, ValueError):
        return None
    if f is None or not 0 <= n < f["images"]:
        return None
    p = _RACINE / pid / f"ref_{n}.png"
    return str(p) if p.is_file() else None


def poser_voix(pid: str, voix: dict) -> dict:
    """G2 (t163) : rattache une voix (clonée ou choisie) au Personnage, en réécrivant fiche.json."""
    d = _dossier(pid)
    if d is None:
        raise Refus(404, "Personnage inconnu.")
    f = json.loads((d / "fiche.json").read_text(encoding="utf-8"))
    f["voix"] = {k: v for k, v in (voix or {}).items() if k in ("fournisseur", "voice_id", "clonee", "le", "verification")}
    tmp = d / "fiche.json.tmp"
    tmp.write_text(json.dumps(f, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(d / "fiche.json")
    return _publique(f)


def supprimer_personnage(pid: str) -> bool:
    d = _dossier(pid)
    if d is None:
        return False
    shutil.rmtree(d)
    return True


# ── Sessions ────────────────────────────────────────────────────────────────────────────────────────────────────────

async def _poster(url: str, entetes: dict, corps: dict) -> tuple[int, dict]:
    """Le SEUL appel réseau du module (remplacé par les bancs)."""
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=20) as c:
        r = await c.post(url, headers=entetes, json=corps)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"detail": r.text[:200]}


def preparer_session(personnage_id: str, duree_s, rapide: bool = False) -> dict:
    """Vérifie tout ce qui ne coûte rien (clé, Personnage) et rend l'op d'estimation : la route passe la garde du
    plafond ENTRE ce contrôle et `ouvrir_session_direct`."""
    if not cle_presente():
        raise Refus(409, "Clé Decart absente (DECART_API_KEY) : l'écran Direct la demande à sa première "
                         "ouverture (console : platform.decart.ai) — rien n'a été lancé.")
    f = lire_personnage(personnage_id)
    if f is None:
        raise Refus(404, "Personnage inconnu.")
    duree = borner_duree(duree_s)
    return {"personnage": f, "duree_s": duree, "rapide": bool(rapide),
            "op": {"kind": "direct", "seconds": duree, "rapide": bool(rapide)},
            "session_id": _secrets.token_hex(12)}


async def ouvrir_session_direct(prep: dict, lignes: list, appareil: str | None) -> dict:
    """Frappe le jeton client chez Decart, borné à la durée réservée. Un refus de Decart remet la réservation à
    0 $ réel (rien n'a été consommé) et lève 502."""
    from app.services import plafonds as _plaf
    sid = prep["session_id"]
    ref = f"decart:{sid}"
    await _plaf.rattacher(lignes, ref)
    corps = {"expiresIn": TTL_JETON_S, "allowedModels": [MODELE],
             "constraints": {"realtime": {"maxSessionDuration": prep["duree_s"]}}}
    try:
        statut, rep = await _poster(f"{BASE_URL}/v1/client/tokens",
                                    {"X-API-KEY": settings.DECART_API_KEY.strip(), "content-type": "application/json"},
                                    corps)
    except httpx.HTTPError as e:
        statut, rep = 0, {"detail": type(e).__name__}
    jeton = rep.get("apiKey") if isinstance(rep, dict) else None
    if statut != 200 or not isinstance(jeton, str) or not jeton:
        await _plaf.noter_reel(ref, 0.0, 0.0)
        # relevé le 10/10 sur le vrai Decart : une clé refusée rend 401 {"error": "Invalid or expired API key"}
        detail = ((rep.get("detail") or rep.get("error")) if isinstance(rep, dict) else "") or ""
        raise Refus(502, f"Decart a refusé le jeton (HTTP {statut}) : {str(detail)[:120]} — rien n'a été facturé.")
    prix = prix_usd_s(prep["rapide"])
    _SESSIONS[sid] = {"personnage_id": prep["personnage"]["id"], "duree_s": prep["duree_s"], "prix_usd_s": prix,
                      "ref": ref, "appareil": appareil, "ouverte": time.time()}
    pid = prep["personnage"]["id"]
    return {"session_id": sid, "jeton": jeton, "expire": rep.get("expiresAt"), "modele": MODELE,
            "duree_max_s": prep["duree_s"], "prix_usd_s": prix, "devis_usd": round(prix * prep["duree_s"], 6),
            "rapide": prep["rapide"], "personnage": prep["personnage"],
            "image_url": f"/api/avatar-live/personnages/{pid}/image/0"}


async def terminer_session(session_id: str, secondes, appareil: str | None) -> dict:
    """Le réel d'une session : secondes rapportées, bornées à [0, durée réservée]. Le PC clôt toute session ; un
    téléphone ne clôt que les siennes. Une session close disparaît (pas de double compte)."""
    from app.services import plafonds as _plaf
    s = _SESSIONS.get(session_id if isinstance(session_id, str) else "")
    if s is None or (appareil is not None and s["appareil"] != appareil):
        raise Refus(404, "Session inconnue ou déjà close.")
    try:
        sec = float(secondes)
        if sec != sec:
            raise ValueError
    except (TypeError, ValueError):
        sec = float(s["duree_s"])           # illisible : la durée entière (sens sûr)
    sec = max(0.0, min(float(s["duree_s"]), sec))
    _SESSIONS.pop(session_id, None)
    reel = round(sec * s["prix_usd_s"], 6)
    await _plaf.noter_reel(s["ref"], reel, sec)
    return {"session_id": session_id, "secondes": sec, "reel_usd": reel}
