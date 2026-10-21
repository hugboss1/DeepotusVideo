"""Atelier sonore — routes du moteur de graphe audio (t270, 21/10/2026), montées sous /api/audio/graph.

  GET  /noeuds   le catalogue des nœuds (types, entrées, bornes ; effets = vocabulaire FX partagé)
  POST /valider  body = le graphe → {ok, sources, ignores, ordre} ; 400 avec le message sinon
  POST /apercu   body {graphe, depuis?} → audio/mpeg de 10 s au plus, jamais rangé dans la Bibliothèque
  POST /rendre   body {graphe, nom?} → atelier_<nom>.mp3 dans la Bibliothèque (relation « atelier », mère = la
                 première source) ; gratuit (ffmpeg local), aucun plafond.
  POST /devis    t272 : body {graphe} → {usd, a_generer, deja} : ce que l'aperçu ou le rendu ferait payer (gratuit).
t272 (21/10/2026) : un graphe qui porte un nœud IA dont le segment n'est pas encore rangé PAYE avant /apercu et
/rendre (`_generer_avant`) — dans cet ordre : graphe valide (400), clé FAL_KEY (503 qui la nomme, rien d'écrit),
confirmation `generer: true` (409 sinon : le premier clic de l'écran arme, le second envoie), entrées rendues et
plages vérifiées (400, gratuit), garde des plafonds « son », génération (`AG.generer_ia`), lignée des segments
(relation « atelier_ia », notée ICI, jamais depuis un thread). Un segment déjà rangé ne se paie plus.
Les écritures hors de la boucle locale sont refusées par la garde de main.py (_garde_ecritures_locales).
"""
import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.config import settings
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


@router.post("/devis")
async def devis(request: Request):
    g = await _corps(request)
    try:
        return AG.devis(g.get("graphe"))
    except ValueError as e:
        raise HTTPException(400, str(e))


async def _generer_avant(b: dict, request: Request) -> dict:
    """t272 : les segments IA manquants, générés et PAYÉS avant l'aperçu ou le rendu → {ia [noms], usd}."""
    from app.api import routes as R
    from app.services import pricing
    try:
        v = AG.valider(b.get("graphe"))
        plan = AG.plan_ia(v)
    except ValueError as e:
        raise HTTPException(400, str(e))
    manquants = [x for x in plan if not x["existe"]]
    if not manquants:
        return {"ia": [], "usd": 0.0}
    if not (settings.FAL_KEY or "").strip():
        raise R._refus_cle("FAL_KEY", manquants[0]["label"], request)
    ops = [x["cout"] for x in manquants]
    usd = round(pricing.estimate({"kind": "campaign", "ops": ops})["total_usd"], 6)
    if b.get("generer") is not True:
        n = len(manquants)
        raise HTTPException(409, f"génération payante à confirmer : {n} nœud(s) IA, {usd} $")
    loop = asyncio.get_running_loop()
    try:
        prets = await loop.run_in_executor(None, AG.preparer_entrees, v, plan)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    try:
        await R._plafond(ops, "son", v["sources"][0])
        faits = await AG.generer_ia(v, plan, prets)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    finally:
        AG.nettoyer(prets)
    await LI.noter(faits, "sonvfx", kind="audio", parent=v["sources"][0], relation="atelier_ia")
    return {"ia": faits, "usd": usd}


@router.post("/apercu")
async def apercu(request: Request):
    b = await _corps(request)
    ia = await _generer_avant(b, request)
    try:
        p = await asyncio.get_running_loop().run_in_executor(None, AG.apercu, b.get("graphe"), b.get("depuis", 0))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    return FileResponse(p, media_type="audio/mpeg", background=BackgroundTask(p.unlink, missing_ok=True),
                        headers={"X-DZ-IA-Usd": str(ia["usd"])})


@router.post("/rendre")
async def rendre(request: Request):
    b = await _corps(request)
    ia = await _generer_avant(b, request)
    try:
        r = await asyncio.get_running_loop().run_in_executor(None, AG.rendre, b.get("graphe"), str(b.get("nom") or ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    await LI.noter([r["filename"]], "sonvfx", kind="audio", parent=r["parent"], relation=r["relation"])
    return dict(r, usd=ia["usd"], ia=ia["ia"])
