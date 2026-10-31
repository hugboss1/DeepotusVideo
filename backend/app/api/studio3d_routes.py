# -*- coding: utf-8 -*-
"""Routes du 3D Studio à écrans — t388 (31/10/2026). Préfixe /api/studio3d.

Lecture et gratuit, SAUF `POST /creer` (t389, l'écran Créer de l'onglet 3D : payant, gardé). Lecture : la galerie
de l'écran Ouvrir, la fiche du modèle ouvert (bandeau commun à tous les écrans) et les préréglages de Préparer. Les écritures passent par les routes déjà gardées : optimisation
(`/api/assets/3d/{job}/optimize`), versions de l'Établi (`/api/etabli/*`). Le service : `app.services.studio3d_ouvert`.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

router = APIRouter()


@router.get("/modeles")
async def studio3d_modeles():
    """La galerie de l'écran Ouvrir, du plus récent au plus ancien (E/S disque : hors de la boucle d'événements)."""
    from app.services import studio3d_ouvert as SO
    return {"modeles": await asyncio.to_thread(SO.modeles)}


@router.get("/ouvert/{job}")
async def studio3d_ouvert(job: str, version: int | None = None):
    """La fiche du modèle ouvert : nom, moteur, versions, comptes, rig. 404 job ou version absents, 400 GLB illisible."""
    from app.services import studio3d_ouvert as SO
    try:
        return await asyncio.to_thread(SO.fiche, job, version)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/preparer/cibles")
async def studio3d_preparer_cibles():
    """Les préréglages de l'écran Préparer, du plus léger au plus lourd, avec leur budget en triangles."""
    from app.services import studio3d_ouvert as SO
    return {"cibles": SO.preparer_cibles()}


# ── t389 : l'onglet 3D = « Créer » ───────────────────────────────────────────────────────────────────────────────
# Plusieurs modèles × images × exemplaires en UN clic. Ordre des refus, tout AVANT la dépense : demande (400) → clé fal
# ou service local (503) → `confirme_cout` absent (409, avec le devis TOTAL) → plafonds sur le total (402) → une garde
# par tir (référence `asset3d:<job>`) → les tirs en parallèle, chacun son JobRecord (suivi par GET /api/jobs/{id}).

@router.post("/creer/devis")
async def studio3d_creer_devis(body: dict = None):
    """Le devis d'une demande de l'écran Créer — gratuit, rien n'est écrit."""
    from app.config import settings
    from app.services import studio3d_creer as SC
    try:
        d = SC.valider(body or {}, settings.images_path)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return SC.devis(d)


@router.post("/creer")
async def studio3d_creer(body: dict, background_tasks: BackgroundTasks):
    """Lance les tirs de l'écran Créer. Payant (catégorie « moteurs3d »)."""
    import json as _json
    from datetime import datetime
    from uuid import uuid4
    from loguru import logger
    from app.api import routes as _R
    from app.config import settings
    from app.models.schemas import JobStatus
    from app.services import local3d_service, plafonds as _PLAF, studio3d_creer as SC
    from app.services.asset3d_service import ENGINES, generate_asset3d
    from app.services.storage import JobRecord, async_session_factory
    try:
        d = SC.valider(body or {}, settings.images_path)
    except ValueError as e:
        raise HTTPException(400, str(e))
    for m in d["moteurs"]:                        # t376 : une pose que l'écran aurait grisée est refusée ici
        _R._pose_ou_400({"pose": d["pose"], "multiview": False, "subject": d["prompt"],
                         "image_filename": d["images"][0]}, m)
    if any(not ENGINES[m].get("local") for m in d["moteurs"]) and not (settings.FAL_KEY or "").strip():
        raise HTTPException(503, "Clé fal absente — ajoute-la dans les Réglages (Clés d'API) : les modèles 3D "
                                 "choisis passent par fal.")
    if any(ENGINES[m].get("local") for m in d["moteurs"]) and not await asyncio.to_thread(local3d_service.joignable):
        raise HTTPException(503, local3d_service.message_absent())
    dv = SC.devis(d)
    if (body or {}).get("confirme_cout") is not True:
        raise HTTPException(409, {"message": "Génération payante : confirme le coût total avant de lancer.",
                                  "devis": dv})
    tirs = SC.tirs(d)
    await _PLAF.juger({"kind": "campaign", "ops": [SC.op(t) for t in tirs]}, "moteurs3d")
    lignes = []
    for t in tirs:
        job_id = str(uuid4())
        short = job_id[:8]
        await _R._plafond(SC.op(t), "moteurs3d", ref=f"asset3d:{short}")
        lignes.append({**t, "job": short, "job_id": job_id})
    async with async_session_factory() as s:
        for l in lignes:
            s.add(JobRecord(id=l["job_id"], status=JobStatus.GENERATING_VIDEO.value, progress=5,
                            title=(d["titre"] or f"3D · {ENGINES[l['engine']]['label']}"),
                            image_filename=f"asset3d_{l['job']}", provider="asset3d", current_step="Generating 3D"))
        await s.commit()

    async def _un(l):
        job_id, short = l["job_id"], l["job"]

        async def on_step(label, pct):
            async with async_session_factory() as s2:
                jr2 = await s2.get(JobRecord, job_id)
                if jr2 is not None:
                    jr2.current_step, jr2.progress = label, int(pct)
                    await s2.commit()

        payload = {k: v for k, v in l.items() if k not in ("job", "job_id", "exemplaire")}
        try:
            r = await generate_asset3d(payload, short, on_step=on_step)
            async with async_session_factory() as s:
                jr = await s.get(JobRecord, job_id)
                if jr is not None:
                    jr.status, jr.progress, jr.current_step = JobStatus.DONE.value, 100, "Complete"
                    jr.final_video_path = r.get("glb")
                    if r.get("preview"):
                        jr.image_filename = "preview.png"
                    jr.completed_at = datetime.utcnow()
                    jr.cost_meta = _json.dumps({"engine": r["engine"], "files": r["files"], "shots": r["shots"],
                                                "job": short, "skipped_formats": r.get("skipped_formats") or [],
                                                "creer": True})
                    await s.commit()
        except Exception as e:                          # noqa: BLE001 — un tir raté n'arrête pas les autres
            logger.exception(f"studio3d/creer {short} ({l['engine']}) échoué : {e}")
            async with async_session_factory() as s:
                jr = await s.get(JobRecord, job_id)
                if jr is not None:
                    jr.status, jr.error, jr.current_step = JobStatus.FAILED.value, str(e), "Failed"
                    await s.commit()

    async def _tous():
        await asyncio.gather(*(_un(l) for l in lignes))

    background_tasks.add_task(_tous)
    return {"tirs": [{"moteur": l["engine"], "job": l["job"], "job_id": l["job_id"],
                      "image": l.get("image_filename") or "", "exemplaire": l["exemplaire"]} for l in lignes],
            "total_usd": dv["total_usd"]}


# ── t391 : l'écran Importer — GLB, glTF, OBJ, STL, et désormais FBX (par Blender) et VRM ─────────────────────────────

@router.post("/importer")
async def studio3d_importer(file: UploadFile = File(...)):
    """Un modèle venu d'ailleurs devient un job du 3D Studio. Local et gratuit. 400 format / fichier refusé, 503 Blender
    absent (FBX seulement)."""
    from app.services import mesh_optimize, studio3d_export as SE, studio3d_import as SI
    from app.config import settings
    data = await file.read()
    try:
        r = await asyncio.to_thread(SI.importer, data, file.filename or "modele")
    except SE.BlenderIndisponible as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    st = mesh_optimize.glb_stats(settings.outputs_path / "assets3d" / r["job"] / "model.glb")
    return {**r, "triangles": st["tris"]}
