# -*- coding: utf-8 -*-
"""t495 (lot G5, 26/11/2026) — /api/croissance : le fil des gagnants de la niche et « pourquoi ça marche »
(services/croissance_gagnants.py). Boucle locale SEULEMENT (`routes._require_localhost`) ; la route payante a aussi
`routes._require_local_depense`. `espace_id` absent = l'espace courant.
- `GET    /gagnants`                       ?espace_id=&jours=&seuil=&tous=0|1 : le fil (lecture seule, aucun relevé)
- `GET    /niche`                          ?espace_id= : tous les fils suivis, ceux de la niche marqués, et la niche
- `PUT    /niche`                          {espace_id?, fils: [id]} : pose la niche
- `GET    /enregistres`                    ?espace_id= : les gagnants enregistrés (métadonnées seulement)
- `POST   /enregistres`                    {espace_id?, item_id} : enregistre un gagnant
- `DELETE /enregistres/{item_id}`          ?espace_id= : le retire
- `POST   /gagnants/{item_id}/devis`       {espace_id?, transcription?, langue?} : le devis GRATUIT (aucun appel)
- `POST   /gagnants/{item_id}/analyse`     {espace_id?, max_usd, transcription?, langue?, nouvelle?} : PAYANTE (Claude,
                                           garde « campagnes » dans CG.analyser_gagnant)
Codes : 400 (forme, accord manquant, transcription trop longue), 404 (espace ou élément inconnu), 409 {message, code}
(`cout` + usd, `en_cours`, `trop`), 402 (plafond), 502/504 (appel peut-être facturé), 503 (Claude non configuré).
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from app.services import croissance_gagnants as CG
from app.services import inspiration as I

router = APIRouter()

MAX_CORPS = 64 * 1024


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _eid(v) -> str:
    from app.services import espaces
    return v.strip()[:40] if isinstance(v, str) and v.strip() else espaces.espace_courant()


def _langue(request: Request, v=None) -> str:
    if v in ("fr", "en"):
        return v
    from app.i18n import erreurs as _ERR
    return "en" if _ERR.langue(request) == "en" else "fr"


def _traduire(texte: str, request: Request) -> str:
    from app.i18n import erreurs as _ERR
    return _ERR.texte(texte, _ERR.langue(request)) if texte else texte


async def _corps(request: Request) -> dict:
    try:
        taille = int(request.headers.get("content-length") or 0)
    except ValueError:
        taille = 0
    if taille > MAX_CORPS:
        raise HTTPException(413, "Demande trop lourde.")
    brut = b""
    async for m in request.stream():
        brut += m
        if len(brut) > MAX_CORPS:
            raise HTTPException(413, "Demande trop lourde.")
    import json
    try:
        c = json.loads(brut or b"null")
    except ValueError:
        raise HTTPException(400, "Corps JSON attendu.") from None
    return c if isinstance(c, dict) else {}


def _http(e: Exception) -> HTTPException:
    if isinstance(e, CG.RefusGagnant):
        if e.statut == 409:
            return HTTPException(409, {"message": str(e), "code": e.code})
        return HTTPException(e.statut, str(e))
    if isinstance(e, I.CoutChange):
        return HTTPException(409, {"message": str(e), "code": "cout", "usd": e.usd})
    if isinstance(e, I.AppelEchoue):
        return HTTPException(e.statut, str(e))
    if isinstance(e, ValueError):
        return HTTPException(400, str(e))
    if isinstance(e, RuntimeError):
        return HTTPException(503 if str(e) in I.RAISONS.values() else 502, str(e))
    raise e


@router.get("/gagnants", dependencies=[Depends(_local)])
async def gagnants(espace_id: str = "", jours: int = CG.FENETRE_JOURS, seuil: float = CG.SEUIL_GAGNANT, tous: int = 0):
    try:
        return await asyncio.to_thread(CG.lire_gagnants, _eid(espace_id), jours, seuil, bool(tous))
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None


@router.get("/niche", dependencies=[Depends(_local)])
async def niche(espace_id: str = ""):
    from app.services import news_fils as NF
    try:
        eid = _eid(espace_id)
        n = CG.niche(eid)
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    dedans = {f["id"] for f in n}
    fils = [dict(CG._vue_fil(f), dans_niche=f["id"] in dedans) for f in NF.lister()["fils"]]
    return {"espace_id": eid, "niche": n, "fils": fils}


@router.put("/niche", dependencies=[Depends(_local)])
async def poser_niche(request: Request):
    c = await _corps(request)
    try:
        eid = _eid(c.get("espace_id"))
        return {"espace_id": eid, "niche": CG.regler_niche(eid, c.get("fils"))}
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None


@router.get("/enregistres", dependencies=[Depends(_local)])
async def enregistres(espace_id: str = ""):
    try:
        eid = _eid(espace_id)
        return {"espace_id": eid, "gagnants": CG.gagnants_enregistres(eid)}
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None


@router.post("/enregistres", dependencies=[Depends(_local)])
async def enregistrer(request: Request):
    c = await _corps(request)
    try:
        return await asyncio.to_thread(CG.enregistrer_gagnant, _eid(c.get("espace_id")), c.get("item_id"))
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None


@router.delete("/enregistres/{item_id}", dependencies=[Depends(_local)])
async def retirer(item_id: str, espace_id: str = ""):
    try:
        fait = CG.retirer_enregistre(_eid(espace_id), item_id)
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    if not fait:
        raise HTTPException(404, "Gagnant non enregistré.")
    return {"ok": True}


@router.post("/gagnants/{item_id}/devis", dependencies=[Depends(_local)])
async def devis_analyse(item_id: str, request: Request):
    c = await _corps(request)
    try:
        d = await CG.devis_analyse(_eid(c.get("espace_id")), item_id, c.get("transcription") or "",
                                   _langue(request, c.get("langue")))
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    return {**d, "raison": _traduire(d.get("raison") or "", request)}


@router.post("/gagnants/{item_id}/analyse", dependencies=[Depends(_local), Depends(_depense_locale)])
async def analyse(item_id: str, request: Request):
    c = await _corps(request)
    try:
        return await CG.analyser_gagnant(_eid(c.get("espace_id")), item_id, max_usd=c.get("max_usd"),
                                         transcription=c.get("transcription") or "",
                                         langue=_langue(request, c.get("langue")), nouvelle=c.get("nouvelle") is True)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning(f"croissance : analyse d'un gagnant refusée ou en échec ({type(e).__name__})")
        raise _http(e) from None
