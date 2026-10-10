# -*- coding: utf-8 -*-
"""Avatar live G0 (t161, 10/10/2026) — /api/avatar-live : état du Direct, Personnages, sessions Decart.

Gardes :
  - lectures (état, Personnages, images) : boucle locale, ou appareil appairé (garde de jeton de main.py) ;
  - écritures sur les Personnages : boucle locale SEULEMENT (garde globale des écritures de main.py) ;
  - ouvrir / clore une session : boucle locale ou appareil appairé — les deux seules écritures ouvertes au réseau
    local (main._ECRITURES_OUVERTES). La garde du plafond mensuel est la MÊME pour les deux, et passe AVANT tout
    appel à Decart. Ce n'est pas `_require_local_depense` : le téléphone doit pouvoir lancer son Direct.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.services import avatar_live as AL
from app.services import plafonds as _PLAF

router = APIRouter()

_HOTES_LOCAUX = ("127.0.0.1", "::1", "localhost", "testclient")


async def _appareil(request: Request) -> str | None:
    """None = le PC (boucle locale) ; sinon l'id de l'appareil du JETON (jamais un champ du corps)."""
    host = (request.client.host if request.client else "") or ""
    if host in _HOTES_LOCAUX:
        return None
    from app.services import appairage
    entete = request.headers.get("authorization", "")
    jeton = entete[7:].strip() if entete[:7].lower() == "bearer " else ""
    a = await appairage.appareil_du_jeton(jeton)
    if not a:
        raise HTTPException(401, "Jeton d'appareil requis — appairez le téléphone depuis Réglages → Appareils.")
    return a["id"]


def _http(e: AL.Refus) -> HTTPException:
    return HTTPException(e.statut, e.message)


@router.get("/etat")
async def etat():
    return {"cle": AL.cle_presente(), "modele": AL.MODELE, "prix_usd_s": AL.prix_usd_s(False),
            "prix_rapide_usd_s": AL.prix_usd_s(True),
            "duree": {"min": AL.DUREE_MIN_S, "max": AL.DUREE_MAX_S, "defaut": AL.DUREE_DEFAUT_S},
            "consentement": AL.TEXTE_CONSENTEMENT, "images_max": AL.IMAGES_MAX, "cote_min_px": AL.COTE_MIN_PX}


@router.get("/personnages")
async def personnages():
    return {"personnages": AL.lister_personnages()}


@router.get("/personnages/{pid}")
async def personnage(pid: str):
    f = AL.lire_personnage(pid)
    if f is None:
        raise HTTPException(404, "Personnage inconnu.")
    return f


@router.get("/personnages/{pid}/image/{n}")
async def personnage_image(pid: str, n: int):
    p = AL.chemin_image(pid, n)
    if p is None:
        raise HTTPException(404, "Image inconnue.")
    return FileResponse(p, media_type="image/png")


@router.post("/personnages")
async def personnage_creer(body: dict | None = None):
    try:
        return AL.creer_personnage(body or {}, origine="pc")
    except AL.Refus as e:
        raise _http(e)


@router.delete("/personnages/{pid}")
async def personnage_supprimer(pid: str):
    if not AL.supprimer_personnage(pid):
        raise HTTPException(404, "Personnage inconnu.")
    return {"supprime": pid}


@router.post("/sessions")
async def session_ouvrir(request: Request, body: dict | None = None):
    appareil = await _appareil(request)
    b = body if isinstance(body, dict) else {}
    try:
        prep = AL.preparer_session(b.get("personnage_id"), b.get("duree_s"), bool(b.get("rapide")))
    except AL.Refus as e:
        raise _http(e)
    garde = await _PLAF.verifier(prep["op"], "direct", ref=f"decart:{prep['session_id']}")
    try:
        return await AL.ouvrir_session_direct(prep, garde["lignes"], appareil)
    except AL.Refus as e:
        raise _http(e)


@router.post("/sessions/fin")
async def session_fin(request: Request, body: dict | None = None):
    appareil = await _appareil(request)
    b = body if isinstance(body, dict) else {}
    try:
        return await AL.terminer_session(b.get("session_id"), b.get("secondes"), appareil)
    except AL.Refus as e:
        raise _http(e)
