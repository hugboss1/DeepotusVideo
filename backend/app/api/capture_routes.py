# -*- coding: utf-8 -*-
"""t315 (28/10/2026) (lot D1) — /api/capture : les sessions de capture de l'app (plan
docs/superpowers/plans/2026-10-28-t315-capture.md, tâche 2 ; spec boîte à outils §8.1-8.3).

Boucle locale SEULEMENT (`routes._require_localhost`) : la capture filme l'app et ses pistes restent sur le PC.
- `POST   /sessions`                        {options} -> {id, options} : une session neuve (état en_cours).
- `PUT    /sessions/{id}/pistes/{piste}/{n}` corps brut (Content-Type = type MIME de la MediaRecorder) : le morceau n
                                            (0, 1, 2… dans l'ordre) de la piste scene | ecran | camera | voix.
- `POST   /sessions/{id}/terminer`          {clics, duree_ms, cadre:{largeur, hauteur}, titre?} : piste des clics
                                            nettoyée et identifiée, générations ajoutées (jobs créés ou finis pendant
                                            la capture), scène copiée dans la Bibliothèque (job `capture`, index
                                            `capture`) -> {id, job_id, fichier, clics: {evenements, clics, reconnus}}.
- `DELETE /sessions/{id}`                   abandon d'une session en cours (pistes effacées).
- `GET    /sessions/{id}`                   {session, clics} (la piste, une fois close).
- `GET    /sessions/{id}/pistes/{piste}`    la piste brute (pour le montage après coup, t317).
Aucun réseau, aucune dépense. Journaux : identifiant, tailles et nombres seulement."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from loguru import logger

from app.services import capture as C

router = APIRouter()

MAX_CORPS_TERMINER = 8 * 1024 * 1024        # 20 000 événements de quelques dizaines d'octets


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _refus(e: C.RefusCapture):
    return HTTPException(e.statut, str(e))


async def _json(request: Request, maximum: int) -> dict:
    corps = await request.body()
    if len(corps) > maximum:
        raise HTTPException(413, "Corps de requête trop lourd.")
    import json
    try:
        d = json.loads(corps or b"{}")
    except ValueError:
        raise HTTPException(400, "Corps JSON illisible.") from None
    if not isinstance(d, dict):
        raise HTTPException(400, "Corps JSON illisible.")
    return d


@router.post("/sessions")
async def creer_session(request: Request):
    _local(request)
    d = await _json(request, 64 * 1024)
    s = await asyncio.to_thread(C.creer, d.get("options"))
    logger.info(f"capture {s['id']} : session ouverte ({s['options']['mode']})")
    return {"id": s["id"], "options": s["options"]}


@router.put("/sessions/{cid}/pistes/{piste}/{n}")
async def deposer_morceau(cid: str, piste: str, n: int, request: Request):
    _local(request)
    if n < 0:
        raise HTTPException(400, "Numéro de morceau invalide.")
    octets = bytearray()
    async for bout in request.stream():
        octets += bout
        if len(octets) > C.MAX_MORCEAU:
            raise HTTPException(413, "Morceau trop lourd : 16 Mo au plus.")
    try:
        return await asyncio.to_thread(C.ajouter_morceau, cid, piste, n, bytes(octets),
                                       request.headers.get("content-type", ""))
    except C.RefusCapture as e:
        raise _refus(e) from None


async def _generations(debut_ms: int, fin_ms: int) -> list[dict]:
    """Les débuts et fins de génération pendant la capture, d'après les jobs (créés ou finis dans la fenêtre)."""
    from sqlalchemy import or_, select
    from app.services.storage import JobRecord, async_session_factory
    # les dates des jobs sont en UTC sans fuseau (datetime.utcnow)
    d0 = datetime.fromtimestamp(debut_ms / 1000, timezone.utc).replace(tzinfo=None)
    d1 = datetime.fromtimestamp(fin_ms / 1000, timezone.utc).replace(tzinfo=None) + timedelta(seconds=2)
    out = []
    try:
        async with async_session_factory() as s:
            q = select(JobRecord).where(or_(JobRecord.created_at.between(d0, d1),
                                            JobRecord.completed_at.between(d0, d1)))
            for j in (await s.execute(q)).scalars():
                if (j.provider or "") == "capture":
                    continue
                if j.created_at and d0 <= j.created_at <= d1:
                    out.append({"type": "generation_debut", "t": int((j.created_at - d0).total_seconds() * 1000),
                                "job_id": j.id, "provider": (j.provider or "")[:20]})
                if j.completed_at and d0 <= j.completed_at <= d1:
                    out.append({"type": "generation_fin", "t": int((j.completed_at - d0).total_seconds() * 1000),
                                "job_id": j.id, "provider": (j.provider or "")[:20], "statut": (j.status or "")[:40]})
    except Exception as e:  # noqa: BLE001 — les générations sont un à-côté de la piste
        logger.warning(f"capture : générations non lues ({type(e).__name__})")
    return out


@router.post("/sessions/{cid}/terminer")
async def terminer(cid: str, request: Request):
    _local(request)
    d = await _json(request, MAX_CORPS_TERMINER)
    from app.api import routes as R
    from app.config import settings
    from app.services import library_index as LI
    try:
        # revue finale t315 (I1) : la clôture est RÉSERVÉE sous verrou avant toute copie ; une seconde clôture concurrente
        # reçoit 409 sans toucher au fichier de la première
        s = await asyncio.to_thread(C.reserver, cid)
    except C.RefusCapture as e:
        raise _refus(e) from None
    try:
        gens = await _generations(s["debut_ms"], C._maintenant_ms())
        dest = await asyncio.to_thread(C.copier_scene, cid, settings.outputs_path / "captures")
    except BaseException as e:
        await asyncio.to_thread(C.liberer, cid)
        if isinstance(e, C.RefusCapture):
            raise _refus(e) from None
        raise
    try:
        r = await asyncio.to_thread(C.clore, cid, d.get("clics"), d.get("duree_ms"), d.get("cadre"), gens)
    except C.RefusCapture as e:
        dest.unlink(missing_ok=True)
        raise _refus(e) from None
    titre = C._texte(d.get("titre"), 120) or f"Capture {datetime.now().strftime('%d/%m %H:%M')}"
    job_id = await R._sfx_video_job(dest, titre, provider="capture", etape="Capture")
    evts = r["clics"]["evenements"]
    clics = [e for e in evts if e["type"] == "clic"]
    await LI.noter([dest.name], "capture", kind="video", job_id=job_id,
                   recette={"capture_id": cid, "mode": r["session"]["options"]["mode"],
                            "pistes": sorted(r["session"]["pistes"]), "clics": len(clics)})
    logger.info(f"capture {cid} : close, {len(evts)} événements, pistes {sorted(r['session']['pistes'])}")
    return {"id": cid, "job_id": job_id, "fichier": dest.name,
            "clics": {"evenements": len(evts), "clics": len(clics),
                      "reconnus": sum(1 for e in clics if e.get("fiche"))}}


@router.delete("/sessions/{cid}")
async def abandonner(cid: str, request: Request):
    _local(request)
    try:
        s = await asyncio.to_thread(C.abandonner, cid)
    except C.RefusCapture as e:
        raise _refus(e) from None
    return {"id": s["id"], "etat": s["etat"]}


@router.get("/sessions/{cid}")
async def lire(cid: str, request: Request):
    _local(request)
    try:
        return await asyncio.to_thread(C.lire, cid)
    except C.RefusCapture as e:
        raise _refus(e) from None


@router.get("/sessions/{cid}/pistes/{piste}")
async def lire_piste(cid: str, piste: str, request: Request):
    _local(request)
    try:
        f = await asyncio.to_thread(C.chemin_piste, cid, piste)
        s = (await asyncio.to_thread(C.lire, cid))["session"]
    except C.RefusCapture as e:
        raise _refus(e) from None
    if f is None:
        raise HTTPException(404, "Piste absente de cette capture.")
    return FileResponse(str(f), media_type=s["pistes"][piste]["mime"])
