# -*- coding: utf-8 -*-
"""Routes du banc comparatif des moteurs image → 3D — t344 (lot Scenario B9, 29/10/2026). Préfixe /api/comparatif3d.

Tout est gratuit SAUF `POST /api/comparatif3d` (N tirs en un clic). Son ordre de refus, tout AVANT la dépense :
moteurs / image (400) → clé fal ou service local (503, la clé nommée) → `confirme_cout` absent (409, avec le devis
total) → plafonds sur le TOTAL (402 `dz_plafond`) → une garde par tir (référence `asset3d:<job>`) → les N jobs en
parallèle (même image, même réglage de texture, une seule image : pas de vues complémentaires, c'est la même
entrée pour tous). Le service : `app.services.comparatif3d`.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger

from app.config import settings

router = APIRouter()


@router.get("/moteurs")
async def comparatif_moteurs(textures: bool = True):
    """Chaque moteur, son prix pour CE réglage de texture, et la clé (ou le service) qu'il demande. Un moteur sans clé
    reste choisissable : `cle_ok` le dit, le refus n'arrive qu'au lancement."""
    from app.services import comparatif3d as C3, local3d_service
    from app.services.asset3d_service import ENGINES
    local_ok = await asyncio.to_thread(local3d_service.joignable) if any(
        e.get("local") for e in ENGINES.values()) else None
    return C3.devis(list(ENGINES), textures, local_ok=local_ok)


@router.get("/modeles")
async def comparatif_modeles():
    """Les modèles 3D déjà générés (mode « comparer des modèles existants », gratuit)."""
    from app.services import comparatif3d as C3
    return {"modeles": await asyncio.to_thread(C3.modeles)}


@router.get("")
async def comparatif_liste():
    from app.services import comparatif3d as C3
    return {"comparatifs": await asyncio.to_thread(C3.lister)}


@router.post("/devis")
async def comparatif_devis(body: dict = None):
    """Le devis de N tirs, gratuit : rien n'est écrit, rien n'est réservé."""
    from app.services import comparatif3d as C3
    body = body or {}
    try:
        moteurs = C3.valider_moteurs(body.get("moteurs"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return C3.devis(moteurs, bool(body.get("textures", True)))


@router.post("")
async def comparatif_lancer(body: dict, background_tasks: BackgroundTasks):
    """N moteurs sur la même image, en UN clic. Payant (catégorie « moteurs3d »)."""
    from app.api import routes as _R
    from app.services import comparatif3d as C3, local3d_service, plafonds as _PLAF
    from app.services.asset3d_service import ENGINES, generate_asset3d
    from app.models.schemas import JobStatus
    from app.services.storage import JobRecord, async_session_factory
    body = body or {}
    try:
        moteurs = C3.valider_moteurs(body.get("moteurs"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    fn = Path(str(body.get("image_filename") or "")).name
    if not fn or not (settings.images_path / fn).is_file():
        raise HTTPException(400, f"Image introuvable dans la Bibliothèque : {fn or '—'}")
    textures = bool(body.get("textures", True))
    if any(not ENGINES[m].get("local") for m in moteurs) and not (settings.FAL_KEY or "").strip():
        raise HTTPException(503, "Clé fal absente — ajoute-la dans les Réglages (Clés d'API) : les moteurs 3D "
                                 "choisis passent par fal.")
    if any(ENGINES[m].get("local") for m in moteurs) and not await asyncio.to_thread(local3d_service.joignable):
        raise HTTPException(503, local3d_service.message_absent())
    d = C3.devis(moteurs, textures)
    if body.get("confirme_cout") is not True:
        raise HTTPException(409, {"message": "Comparatif payant : confirme le coût total avant de lancer.",
                                  "devis": d})
    # le TOTAL d'abord : le dialogue du plafond montre ce que coûtent les N tirs, et rien n'est écrit s'il refuse
    await _PLAF.juger({"kind": "campaign", "ops": [C3.op(m, textures) for m in moteurs]}, "moteurs3d")
    lignes = []
    for m, l in zip(moteurs, d["lignes"]):
        job_id = str(uuid4())
        short = job_id[:8]
        await _R._plafond(C3.op(m, textures), "moteurs3d", ref=f"asset3d:{short}")
        lignes.append({"moteur": m, "job": short, "job_id": job_id, "version": 1, "usd_estime": l["usd"]})
    cmp = C3.creer("tir", lignes, image_filename=fn, textures=textures, titre=str(body.get("titre") or fn))
    async with async_session_factory() as s:
        for l in lignes:
            s.add(JobRecord(id=l["job_id"], status=JobStatus.GENERATING_VIDEO.value, progress=5,
                            title=f"Comparatif 3D · {ENGINES[l['moteur']]['label']}",
                            image_filename=f"asset3d_{l['job']}", provider="asset3d",
                            current_step="Generating 3D"))
        await s.commit()

    async def _un(l):
        job_id, short = l["job_id"], l["job"]

        async def on_step(label, pct):
            async with async_session_factory() as s2:
                jr2 = await s2.get(JobRecord, job_id)
                if jr2 is not None:
                    jr2.current_step, jr2.progress = label, int(pct)
                    await s2.commit()

        C3.noter(cmp["id"], short, debut=datetime.utcnow().isoformat(timespec="seconds"))
        try:
            r = await generate_asset3d({"engine": l["moteur"], "image_filename": fn, "textures": textures,
                                        "formats": ["glb"], "multiview": False}, short, on_step=on_step)
            C3.noter(cmp["id"], short, fin=datetime.utcnow().isoformat(timespec="seconds"))
            async with async_session_factory() as s:
                jr = await s.get(JobRecord, job_id)
                if jr is not None:
                    jr.status, jr.progress, jr.current_step = JobStatus.DONE.value, 100, "Complete"
                    jr.final_video_path = r.get("glb")
                    if r.get("preview"):
                        jr.image_filename = "preview.png"
                    jr.completed_at = datetime.utcnow()
                    jr.cost_meta = json.dumps({"engine": r["engine"], "files": r["files"], "shots": r["shots"],
                                               "job": short, "skipped_formats": r.get("skipped_formats") or [],
                                               "comparatif": cmp["id"]})
                    await s.commit()
        except Exception as e:                          # noqa: BLE001 — un moteur raté n'arrête pas les autres
            logger.exception(f"comparatif3d {cmp['id']} {l['moteur']} échoué : {e}")
            C3.noter(cmp["id"], short, fin=datetime.utcnow().isoformat(timespec="seconds"), erreur=str(e)[:400])
            async with async_session_factory() as s:
                jr = await s.get(JobRecord, job_id)
                if jr is not None:
                    jr.status, jr.error, jr.current_step = JobStatus.FAILED.value, str(e), "Failed"
                    await s.commit()

    async def _tous():
        await asyncio.gather(*(_un(l) for l in lignes))

    background_tasks.add_task(_tous)
    return {"id": cmp["id"], "lignes": [{k: l[k] for k in ("moteur", "job", "usd_estime")} for l in lignes],
            "total_usd": d["total_usd"]}


@router.post("/existants")
async def comparatif_existants(body: dict = None):
    """Des GLB déjà générés, côte à côte. Gratuit : lit (et calcule au besoin) leurs fiches de maillage."""
    from app.services import comparatif3d as C3
    body = body or {}
    try:
        lignes = await asyncio.to_thread(C3.preparer_existants, body.get("modeles"))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    c = C3.creer("existants", lignes, titre=str(body.get("titre") or ""))
    return await C3.tableau(c["id"])


@router.get("/{cid}")
async def comparatif_lire(cid: str):
    from app.services import comparatif3d as C3
    try:
        return await C3.tableau(cid)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/{cid}/garder")
async def comparatif_garder(cid: str, body: dict = None):
    """« Garder celui-ci » : la vue capturée du gagnant entre dans la Bibliothèque avec sa provenance. Gratuit."""
    from app.services import comparatif3d as C3
    body = body or {}
    job = str(body.get("job") or "")
    if not C3.job_valide(job):
        raise HTTPException(400, "job refusé : le nom du dossier du job 3D est attendu")
    try:
        poster = C3.lire_poster(body.get("poster"))
        return await C3.garder(cid, job, poster)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
