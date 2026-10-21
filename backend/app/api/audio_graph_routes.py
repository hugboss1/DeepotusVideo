"""Atelier sonore — routes du moteur de graphe audio (t270, 21/10/2026), montées sous /api/audio/graph.

  GET  /noeuds   le catalogue des nœuds (types, entrées, bornes ; effets = vocabulaire FX partagé)
  POST /valider  body = le graphe → {ok, sources, ignores, ordre} ; 400 avec le message sinon
  POST /apercu   body {graphe, depuis?} → audio/mpeg de 10 s au plus, jamais rangé dans la Bibliothèque
  POST /rendre   body {graphe, nom?} → atelier_<nom>.mp3 dans la Bibliothèque (relation « atelier », mère = la
                 première source) ; gratuit (ffmpeg local), aucun plafond.
Les écritures hors de la boucle locale sont refusées par la garde de main.py (_garde_ecritures_locales).
"""
import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.services import audio_graph as AG
from app.services import library_index as LI

router = APIRouter()


async def _corps(request: Request) -> dict:
    try:
        d = await request.json()
    except Exception:
        d = None
    return d if isinstance(d, dict) else {}


@router.get("/noeuds")
async def noeuds():
    return AG.catalogue()


@router.post("/valider")
async def valider(request: Request):
    g = await _corps(request)
    try:
        v = AG.valider(g)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "sources": v["sources"], "ignores": v["ignores"], "ordre": v["ordre"]}


@router.post("/apercu")
async def apercu(request: Request):
    b = await _corps(request)
    try:
        p = await asyncio.get_running_loop().run_in_executor(None, AG.apercu, b.get("graphe"), b.get("depuis", 0))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    return FileResponse(p, media_type="audio/mpeg", background=BackgroundTask(p.unlink, missing_ok=True))


@router.post("/rendre")
async def rendre(request: Request):
    b = await _corps(request)
    try:
        r = await asyncio.get_running_loop().run_in_executor(None, AG.rendre, b.get("graphe"), str(b.get("nom") or ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    await LI.noter([r["filename"]], "sonvfx", kind="audio", parent=r["parent"], relation=r["relation"])
    return r
