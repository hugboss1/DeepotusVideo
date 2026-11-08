# -*- coding: utf-8 -*-
"""t434 (lot M1 « Méthodes », 08/11/2026) — /api/briques : les briques transverses des agents métier.
Services : app.services.briques (B1 mesures + avis, B3 conformer/comparer), app.services.ancres (B2),
app.services.registre_taches (B7).

  POST   /api/briques/mesurer          {chemin, reference?}              B1, local, gratuit
  POST   /api/briques/comparer         {a, b}                            B3, dérive image par image, gratuit
  POST   /api/briques/conformer        {chemin, source}                  B3, ffmpeg local, gratuit
  POST   /api/briques/avis/devis       {chemins, criteres, contexte?}    B1, devis GRATUIT de l'avis
  POST   /api/briques/avis             {…, confirme_cout, max_usd, categorie, tache?}   B1, PAYANT (Claude vision)
  GET    /api/briques/ancres           ?espace=&nature=                  B2
  POST   /api/briques/ancres           {nom, nature, chemin, espace_id?, note?}
  DELETE /api/briques/ancres/{id}
  POST   /api/briques/ancres/{id}/verifier  {chemin}
  GET    /api/briques/registre         ?tache=                           B7

Ordre de refus de l'avis, tout AVANT la dépense : entrée (400) → clé (503) / modèle aveugle (400) → `confirme_cout`
absent (409, devis joint) → coût hors accord (409) → plafond de la catégorie (402, par tirer_garde).
"""
from __future__ import annotations

import asyncio
import subprocess

from fastapi import APIRouter, Depends, HTTPException, Request

from app.services import ancres as AN
from app.services import briques as BR
from app.services import registre_taches as RT

router = APIRouter()


def _local(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _corps(body) -> dict:
    return body if isinstance(body, dict) else {}


async def _fil(fn, *args):
    try:
        return await asyncio.to_thread(fn, *args)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
        raise HTTPException(500, str(e)[:300])


@router.post("/mesurer")
async def briques_mesurer(body: dict | None = None):
    b = _corps(body)
    return await _fil(BR.mesurer, b.get("chemin"), b.get("reference") or "")


@router.post("/comparer")
async def briques_comparer(body: dict | None = None):
    b = _corps(body)
    return await _fil(BR.comparer, b.get("a"), b.get("b"))


@router.post("/conformer", dependencies=[Depends(_local)])
async def briques_conformer(body: dict | None = None):
    b = _corps(body)
    return await _fil(BR.conformer, b.get("chemin"), b.get("source"))


@router.post("/avis/devis")
async def briques_avis_devis(body: dict | None = None):
    b = _corps(body)
    chemins = b.get("chemins") if isinstance(b.get("chemins"), list) else []
    for c in chemins[:BR.MAX_IMAGES]:
        await _fil(BR.confiner, c)
    try:
        return BR.devis_avis(len(chemins), b.get("criteres"), b.get("contexte") or "", b.get("langue") or "fr")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/avis", dependencies=[Depends(_local)])
async def briques_avis(body: dict | None = None):
    from app.services.scan_vision import CoutChange
    b = _corps(body)
    chemins = b.get("chemins") if isinstance(b.get("chemins"), list) else []
    try:
        d = BR.devis_avis(len(chemins), b.get("criteres"), b.get("contexte") or "", b.get("langue") or "fr")
    except ValueError as e:
        raise HTTPException(400, str(e))
    if d["raison"] == "cle":
        raise HTTPException(503, "Le moteur Anthropic n'est pas configuré (Réglages › Clés d'API).")
    if d["raison"] == "vision":
        raise HTTPException(400, "Le modèle Anthropic réglé ne lit pas les images : choisis-en un qui les voit (Réglages › Modèles).")
    if b.get("confirme_cout") is not True:
        raise HTTPException(409, {"message": "Confirme le coût de l'avis avant de le lancer.", "usd": d["usd"], "devis": d})
    tache = b.get("tache") if isinstance(b.get("tache"), str) and b.get("tache").strip() else ""
    eid = await RT.ouvrir(tache, "avis", d["usd"]) if tache else None
    try:
        r = await BR.avis(chemins, b.get("criteres"), max_usd=b.get("max_usd", d["usd"]),
                          categorie=str(b.get("categorie") or ""), contexte=b.get("contexte") or "",
                          langue=b.get("langue") or "fr", ref=(f"briques:{tache}"[:64] if tache else None))
    except CoutChange as e:
        if eid:
            await RT.fermer(eid, "annule")
        raise HTTPException(409, {"message": str(e), "usd": e.usd, "devis": d | {"usd": e.usd}})
    except ValueError as e:
        if eid:
            await RT.fermer(eid, "annule")
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        if eid:
            await RT.fermer(eid, "echec")
        raise HTTPException(502, str(e)[:300])
    if eid:
        r["registre"] = await RT.fermer(eid, "fait")
    return r


@router.get("/ancres")
async def briques_ancres(espace: str = "", nature: str = ""):
    return {"ancres": AN.lister(espace, nature), "natures": list(AN.NATURES)}


@router.post("/ancres", dependencies=[Depends(_local)])
async def briques_ancre_creer(body: dict | None = None):
    b = _corps(body)
    return await _fil(AN.creer, b.get("nom") or "", b.get("nature") or "", b.get("chemin"),
                      b.get("espace_id") or "", b.get("note") or "")


@router.delete("/ancres/{ancre_id}", dependencies=[Depends(_local)])
async def briques_ancre_supprimer(ancre_id: str):
    if not await asyncio.to_thread(AN.supprimer, ancre_id):
        raise HTTPException(404, "Ancre inconnue.")
    return {"ok": True}


@router.post("/ancres/{ancre_id}/verifier")
async def briques_ancre_verifier(ancre_id: str, body: dict | None = None):
    return await _fil(AN.verifier, ancre_id, _corps(body).get("chemin"))


@router.get("/registre")
async def briques_registre(tache: str = ""):
    try:
        return await RT.lire(tache)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── t435b (lot M2) : B4, la chaîne d'éditions vidéo → vidéo (services/chaine_video.py) ─────────────────────────────
#   GET  /api/briques/chaines                  les chaînes (les plus récentes d'abord)
#   POST /api/briques/chaines                  {source, nom?}          une chaîne neuve sur une vidéo approuvée
#   GET  /api/briques/chaines/{id}             la chaîne et ses étapes
#   POST /api/briques/chaines/{id}/devis       {consigne, ancres?, resolution?}   devis GRATUIT de la prochaine étape
#   POST /api/briques/chaines/{id}/etapes      {…, confirme_cout, max_usd}        PAYANT, tir en tâche de fond
# Ordre de refus du tir, tout AVANT la dépense : chaîne / entrée (404/400) → clé fal (503) → refus du clip ou étape en
# cours (409) → confirmation (409, devis joint) → coût hors accord (409) → plafond « montage » (402).

from fastapi import BackgroundTasks  # noqa: E402

from app.services import chaine_video as CV  # noqa: E402


def _chaine(cid: str) -> dict:
    ch = CV.lire(cid)
    if ch is None:
        raise HTTPException(404, "Chaîne inconnue.")
    return ch


@router.get("/chaines")
async def briques_chaines():
    return {"chaines": await asyncio.to_thread(CV.lister)}


@router.post("/chaines", dependencies=[Depends(_local)])
async def briques_chaine_creer(body: dict | None = None):
    b = _corps(body)
    return await _fil(CV.creer, b.get("source"), b.get("nom") or "")


@router.get("/chaines/{cid}")
async def briques_chaine(cid: str):
    return _chaine(cid)


async def _devis_chaine(cid: str, b: dict) -> dict:
    _chaine(cid)
    ancres = b.get("ancres") if isinstance(b.get("ancres"), list) else []
    return await _fil(CV.devis_etape, cid, b.get("consigne") or "", [str(a) for a in ancres],
                      str(b.get("resolution") or "720p"))


@router.post("/chaines/{cid}/devis")
async def briques_chaine_devis(cid: str, body: dict | None = None):
    d = await _devis_chaine(cid, _corps(body))
    d.pop("op", None)
    return d


@router.post("/chaines/{cid}/etapes", dependencies=[Depends(_local)])
async def briques_chaine_etape(cid: str, background_tasks: BackgroundTasks, body: dict | None = None):
    from app.config import settings
    from app.services import plafonds as PL
    from app.services.scan_vision import _accord
    b = _corps(body)
    d = await _devis_chaine(cid, b)
    if not settings.FAL_KEY:
        raise HTTPException(503, "Ajoute une clé fal.ai (Réglages › Clés d'API) pour lancer une édition vidéo.")
    if d["refus"]:
        raise HTTPException(409, d["refus"])
    pub = {k: v for k, v in d.items() if k != "op"}
    if b.get("confirme_cout") is not True:
        raise HTTPException(409, {"message": "Confirme le coût de l'étape avant de la lancer.", "usd": d["usd"],
                                  "devis": pub})
    try:
        mx = _accord(b.get("max_usd", d["usd"]))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if d["usd"] > mx + 1e-4:
        raise HTTPException(409, {"message": "Le coût a changé : il dépasse le montant accepté.", "usd": d["usd"],
                                  "devis": pub})
    try:
        n = CV.reserver(cid, d)
    except ValueError as e:
        raise HTTPException(409, str(e))
    try:
        garde = await PL.verifier(d["op"], "montage", ref=f"{cid}:{n}")
    except BaseException:
        CV.terminer(cid, n, statut="annule")
        raise
    etape = await RT.ouvrir(cid, f"étape {n}", d["usd"], (garde or {}).get("lignes") or [])

    async def _run():
        e = await CV.tirer(cid, n, d)
        await RT.fermer(etape, "fait" if e.get("statut") == "fait" else "echec")

    background_tasks.add_task(_run)
    return {"chaine": cid, "n": n, "usd": d["usd"], "statut": "en_cours"}
