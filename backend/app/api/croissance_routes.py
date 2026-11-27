# -*- coding: utf-8 -*-
"""t497 (G7, 26/11/2026) — /api/croissance : la NOTE avant publication d'un rendu (estimation en deux étages).

Boucle locale SEULEMENT ; la route payante a aussi `routes._require_local_depense`.
- `POST /note`          {job_id | post_id, mots?, soustitres?, zone_sure?} : étage 1, GRATUIT (ffmpeg) ; avec un post,
                        la note va dans `brief.note_rendu` (inspecteur du Planificateur).
- `GET  /note/devis`    `?job_id=|post_id=` : le devis GRATUIT de l'étage 2.
- `POST /note/affiner`  {job_id | post_id, max_usd, langue?, mots?} : étage 2, PAYANT (Claude sur quatre images clés).
Codes : 400 (corps), 404 (rendu ou post introuvable), 409 `cout`, 502/504, 503 (Claude non configuré), 402 (plafond).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api import inspiration_routes as IR
from app.services import note_rendu as NR

router = APIRouter()


def _cible(c: dict) -> dict:
    j, p = c.get("job_id"), c.get("post_id")
    if not (isinstance(j, str) and j) and not (isinstance(p, str) and p):
        raise HTTPException(400, "job_id ou post_id requis.")
    return {"job_id": j if isinstance(j, str) and j else None, "post_id": p if isinstance(p, str) and p else None}


def _http(e: Exception) -> HTTPException:
    if isinstance(e, NR.NoteImpossible):
        return HTTPException(404 if "introuvable" in str(e) else 400, str(e))
    return IR._http(e)


@router.post("/note", dependencies=[Depends(IR._local)])
async def note(request: Request):
    c = await IR._corps(request)
    try:
        return await NR.estimer(**_cible(c), mots=c.get("mots"), soustitres=c.get("soustitres"), zone_sure=c.get("zone_sure"))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None


@router.get("/note/devis", dependencies=[Depends(IR._local)])
async def devis(request: Request, job_id: str = "", post_id: str = "", langue: str = ""):
    try:
        d = await NR.devis_affiner(**_cible({"job_id": job_id, "post_id": post_id}),
                                   langue=IR._langue(request, {"langue": langue}))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    return {**d, "raison": IR._traduire(d.get("raison") or "", request)}


@router.post("/note/affiner", dependencies=[Depends(IR._local), Depends(IR._depense_locale)])
async def affiner(request: Request):
    c = await IR._corps(request)
    try:
        return await NR.affiner(**_cible(c), max_usd=c.get("max_usd"), langue=IR._langue(request, c), mots=c.get("mots"))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
