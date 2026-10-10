# -*- coding: utf-8 -*-
"""Les formes de reel News et leur cout AVANT tir (plan 2026-09-03 T11, tache #35 du suivi, 30/09/2026).

Ce module ne GENERE rien : il catalogue, chiffre et refuse. Chaque forme delegue a un producteur deja eprouve :

  cartes             -> POST /api/news/illustration (cartes de marque rendues par ffmpeg : LOCAL, GRATUIT)
  illustration_ia    -> POST /api/images/generate (une image par titre)
  plans_seedance     -> POST /api/generate (un plan par sujet)
  avatar             -> le chemin HeyGen existant
  voix_sous_titres   -> ElevenLabs + subtitle_service, sans avatar (R5 P2)

Ecarts dates (30/09) : (1) la forme `cartes` s'ajoute aux quatre de R8 — c'est le reel que la chaine du lot pose sur
chaque post (decision de l'utilisateur : le media du lot est gratuit ; les formes payantes sont chiffrees ici et
lancees a la main) ; (2) `disponible()` regarde la cle du fournisseur, pas seulement l'existence de l'identifiant.
Le cout passe par `pricing.estimate` : un second bareme divergerait au premier changement de tarif.
"""
from app.config import settings
from app.services import pricing

_CATALOGUE = [
    {"id": "cartes", "label": "Cartes animées (gratuit)",
     "description": "les titres en cartes de marque, rendues localement par ffmpeg ; aucun fournisseur",
     "producteur": "/api/news/illustration", "depend_de": "", "payant": False},
    {"id": "illustration_ia", "label": "Illustration IA par titre",
     "description": "une image de marque générée par titre, animée en cartes",
     "producteur": "/api/images/generate", "depend_de": "", "payant": True},
    {"id": "plans_seedance", "label": "Plans vidéo par sujet",
     "description": "un plan généré par sujet, monté bout à bout",
     "producteur": "/api/generate", "depend_de": "R1", "payant": True},
    {"id": "avatar", "label": "Avatar présentateur",
     "description": "l'avatar HeyGen lit le script, compose avec les cartes",
     "producteur": "pipeline:heygen", "depend_de": "", "payant": True},
    {"id": "voix_sous_titres", "label": "Voix off et sous-titres",
     "description": "pas d'avatar : voix ElevenLabs sur les cartes, sous-titres calés sur le texte connu",
     "producteur": "subtitle_service:burn", "depend_de": "R5 P2", "payant": True},
]

IDS = [f["id"] for f in _CATALOGUE]


def catalogue() -> list[dict]:
    return [dict(f) for f in _CATALOGUE]


def disponible(forme: str) -> bool:
    """Vrai si la forme peut etre tiree ICI : le fournisseur a sa cle (FAL pour les images et Seedance, HeyGen pour
    l'avatar, ElevenLabs pour la voix off). Les cartes ne dependent de rien."""
    if forme == "cartes":
        return True
    if forme in ("illustration_ia", "plans_seedance"):
        return bool((settings.FAL_KEY or "").strip())
    if forme == "avatar":
        return bool(settings.has_heygen)
    if forme == "voix_sous_titres":
        try:
            from app.services import subtitle_service  # noqa: F401
        except ImportError:
            return False
        return bool(settings.has_voiceover)
    return False


def _refus_forme(forme: str) -> None:
    if forme not in IDS:
        raise ValueError(f"forme de reel inconnue : {forme!r} — les formes sont " + ", ".join(IDS))


def _nombre(v, defaut: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return defaut
    return x if x == x and 0 <= x < 1e7 else defaut


def estimer(forme: str, items: list[dict], options: dict | None = None) -> dict:
    """Rend {forme, breakdown, total_usd, credits, detail}. Leve ValueError sur une forme inconnue ou une liste
    vide : un devis a zero article afficherait « 0,00 $ » et laisserait croire que le tir est gratuit."""
    _refus_forme(forme)
    if not items:
        raise ValueError("aucun article selectionne : rien a chiffrer")
    o = dict(options or {})
    n = len(items)
    if forme == "cartes":
        return {"forme": forme, "breakdown": [], "total_usd": 0.0, "credits": {},
                "detail": {"cartes": n, "rendu": "local (ffmpeg), gratuit"}}
    if forme == "illustration_ia":
        op = {"kind": "image", "n": n, "model": o.get("model") or "flux"}
        detail = {"images": n}
    elif forme == "plans_seedance":
        duree = _nombre(o.get("duration_s"), 5.0) or 5.0
        op = {"kind": "seedance", "n": n, "duration_s": duree, "model": o.get("model") or "seedance-2-fast",
              "resolution": o.get("resolution") or "1080p"}
        detail = {"secondes": int(round(duree * n))}
    elif forme == "avatar":
        chars = _nombre(o.get("chars"), 0.0)
        op = {"kind": "heygen", "chars": chars}
        detail = {"caracteres": int(chars)}
    else:  # voix_sous_titres
        chars = _nombre(o.get("chars"), 0.0)
        op = {"kind": "elevenlabs", "chars": chars, "model": o.get("voice_model") or ""}
        detail = {"caracteres": int(chars), "sous_titres": "calage du texte connu (local, gratuit)"}
    devis = pricing.estimate(op)
    devis["forme"] = forme
    devis["detail"] = detail
    return devis
