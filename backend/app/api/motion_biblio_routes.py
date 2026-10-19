# -*- coding: utf-8 -*-
"""Bibliothèque motion (t233, 17/10/2026) — /api/motion/biblio et /api/motion/skills/installer.

Boucle locale SEULEMENT, en lecture comme en écriture : la bibliothèque est celle du PC (imports collés par
l'utilisateur, skills installés dans son dossier de données). Le service est app.services.motion_biblio.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.services import motion_biblio as MB

router = APIRouter()

_HOTES_LOCAUX = ("127.0.0.1", "::1", "localhost", "testclient")


def _local(request: Request) -> None:
    host = (request.client.host if request.client else "") or ""
    if host not in _HOTES_LOCAUX:
        raise HTTPException(403, "La bibliothèque motion n'est accessible que depuis ce PC.")


def _http(e: Exception) -> HTTPException:
    statut = 403 if isinstance(e, PermissionError) else 404 if isinstance(e, LookupError) else \
        502 if isinstance(e, RuntimeError) else 400
    return HTTPException(statut, str(e))


async def _corps(request: Request) -> dict:
    try:
        corps = await request.json()
    except ValueError:
        corps = None
    if not isinstance(corps, dict):
        raise HTTPException(400, "Corps JSON attendu.")
    return corps


@router.get("/biblio")
async def lister(request: Request, nature: str | None = None, theme: str | None = None):
    _local(request)
    entrees = MB.lister(nature, theme)
    return {"entrees": [{k: v for k, v in e.items() if k != "original"} for e in entrees],
            "themes": list(MB.THEMES), "presets": list(MB.PRESETS), "easings": list(MB.EASINGS),
            "formats": list(MB.FORMATS), "licences": list(MB.LICENCES)}


@router.get("/biblio/{eid}")
async def lire(eid: str, request: Request):
    _local(request)
    try:
        return MB.lire(eid)
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None


@router.post("/biblio")
async def importer(request: Request):
    _local(request)
    corps = await _corps(request)
    try:
        return MB.importer_prompt(corps)
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None


@router.patch("/biblio/{eid}")
async def modifier(eid: str, request: Request):
    _local(request)
    corps = await _corps(request)
    try:
        return MB.modifier(eid, corps)
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None


@router.post("/biblio/{eid}/revenir")
async def revenir(eid: str, request: Request):
    _local(request)
    try:
        return MB.revenir_original(eid)
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None


@router.delete("/biblio/{eid}")
async def supprimer(eid: str, request: Request):
    _local(request)
    try:
        return MB.supprimer(eid)
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None


@router.post("/skills/apercu")
async def apercu(request: Request):
    """t236 — lit SKILL.md et la licence d'un dépôt SANS rien installer : l'écran montre la licence AVANT que
    l'utilisateur confirme. Mêmes refus que l'installation (sans licence permissive → 400)."""
    _local(request)
    corps = await _corps(request)
    try:
        return await MB.apercu_skill(corps.get("source"))
    except (ValueError, LookupError, PermissionError, RuntimeError) as e:
        raise _http(e) from None


@router.post("/skills/installer")
async def installer(request: Request):
    """`licence` (facultatif) = l'identifiant montré par l'aperçu : une licence qui a changé entre-temps est refusée."""
    _local(request)
    corps = await _corps(request)
    lic = corps.get("licence")
    try:
        return await MB.installer_skill(corps.get("source"), lic if isinstance(lic, str) else None)
    except (ValueError, LookupError, PermissionError, RuntimeError) as e:
        raise _http(e) from None


@router.get("/personnalisation")
async def personnalisation(request: Request):
    """t240 — pour la rubrique « Personnaliser » de Direction motion : les curseurs (états, phrases ajoutées, effet de
    la finition), le bloc de précisions (libellés, aide, règle de priorité) et les bornes du tempo, en FR et EN."""
    _local(request)
    from app.services import motion_choregraphe as CH
    p = CH.personnalisation()
    return {"neutre": p["neutre"], "curseurs": p["curseurs"], "precisions": p["precisions"], "tempo": p["tempo"]}


@router.post("/choregraphier")
async def choregraphier(request: Request):
    """t234 — script + direction → éléments du nœud Animation (app.services.motion_choregraphe). Un moteur absent ou
    non configuré n'est pas une erreur : le repli déterministe répond. Un plafond dépassé remonte (402 dz_plafond)."""
    _local(request)
    corps = await _corps(request)
    from app.i18n import langue_requete
    from app.services import motion_choregraphe as CH
    try:
        return await CH.choregraphier(corps, langue_requete(request))
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None


@router.post("/code/ecrire")
async def code_ecrire(request: Request):
    """t238 — le moteur choisi écrit la page HTML / SVG / Canvas d'un nœud « Rendu motion code » (app.services.
    motion_code). Coût estimé et plafond vérifié AVANT l'appel (402 dz_plafond) ; une page refusée par le contrôle du
    bac à sable, une réponse illisible, un moteur absent : la page de repli. Rien n'est exécuté ici."""
    _local(request)
    corps = await _corps(request)
    from app.i18n import langue_requete
    from app.services import motion_code as MC
    try:
        r = await MC.ecrire(corps, langue_requete(request))
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None
    r["refus_texte"] = MC.details_refus(r.get("refus") or [], langue_requete(request))
    return r


@router.get("/code/{pid}")
async def code_lire(pid: str, request: Request):
    """La page enregistrée, en TEXTE dans du JSON (jamais servie comme document : elle ne s'exécute que dans le bac à
    sable), avec ses motifs de refus éventuels."""
    _local(request)
    from app.services import motion_code as MC
    try:
        html = MC.lire(pid)
    except LookupError as e:
        raise _http(e) from None
    return {"page_id": pid, "taille": len(html.encode("utf-8")), "refus": MC.controler(html), "html": html}


@router.post("/code/rendre")
async def code_rendre(request: Request, background_tasks: BackgroundTasks):
    """La page `page_id` rendue en MP4 dans le bac à sable, en tâche de fond : un job comme /api/animate (Job Dock,
    Bibliothèque, « Rouvrir dans le Studio »), sous le MÊME provider `animation` (rangé dans « Studio » par la couche
    Montage ; la liste des providers est figée par test_montage_eb_croise). GET /api/jobs/{job_id} ; un refus ou un
    arrêt du bac à sable = job en échec avec son message (FR / EN)."""
    _local(request)
    corps = await _corps(request)
    import asyncio
    import json
    from datetime import datetime
    from uuid import uuid4
    from loguru import logger
    from app.config import settings
    from app.i18n import langue_requete
    from app.models.schemas import JobStatus
    from app.services import motion_code as MC
    from app.services.storage import JobRecord, async_session_factory
    langue = langue_requete(request)
    pid = corps.get("page_id")
    try:
        MC.lire(pid)
    except LookupError as e:
        raise _http(e) from None
    aspect, _w, _h, fps, duree = MC.bornes(corps.get("aspect"), corps.get("fps"), corps.get("duree_s"))
    job_id = str(uuid4())
    sortie = settings.outputs_path / f"mcode_{job_id[:8]}.mp4"
    if corps.get("source_graph"):
        try:
            gdir = settings.outputs_path / "_graphs"
            gdir.mkdir(parents=True, exist_ok=True)
            (gdir / f"{job_id}.json").write_text(json.dumps(corps["source_graph"], ensure_ascii=False), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"source_graph save failed for motion code {job_id}: {e}")
    titre = corps.get("title") if isinstance(corps.get("title"), str) and corps.get("title").strip() else "Motion code"
    async with async_session_factory() as session:
        session.add(JobRecord(id=job_id, status=JobStatus.GENERATING_VIDEO.value, progress=10, title=titre[:200],
                              image_filename=sortie.name, aspect_ratio=aspect, provider="animation",
                              current_step="Rendering"))
        await session.commit()

    async def _run():
        try:
            r = await asyncio.to_thread(MC.rendre, pid, sortie, aspect=aspect, fps=fps, duree_s=duree, langue=langue)
            async with async_session_factory() as session:
                jr = await session.get(JobRecord, job_id)
                jr.status = JobStatus.DONE.value
                jr.progress = 100
                jr.final_video_path = jr.video_path = str(sortie)
                jr.duration_s = int(round(r["duree_s"]))
                jr.current_step = "Complete"
                jr.completed_at = datetime.utcnow()
                await session.commit()
        except Exception as e:  # noqa: BLE001 — refus, arrêt du bac à sable, encodage : le job le dit
            if not isinstance(e, MC.Arret):
                logger.exception(f"motion code job {job_id} failed: {e}")
            async with async_session_factory() as session:
                jr = await session.get(JobRecord, job_id)
                if jr is not None:
                    jr.status = JobStatus.FAILED.value
                    jr.error = str(e)
                    jr.current_step = "Failed"
                    await session.commit()

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "queued", "page_id": pid, "aspect": aspect, "fps": fps, "duree_s": duree}
