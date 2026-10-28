# -*- coding: utf-8 -*-
"""t319 (28/10/2026) (lot D5) — /api/tutoriels : le brouillon de tutoriel d'une capture et les parcours partagés
(plan docs/superpowers/plans/2026-10-28-t319-tutoriels.md, tâche 4 ; spec boîte à outils §8.7).

Boucle locale SEULEMENT (`routes._require_localhost`), comme /api/capture.
- `GET  /captures/{id}`             {capture, brouillon, propose} : l'enregistré relu, sinon proposé.
- `PUT  /captures/{id}`             {brouillon} -> le brouillon validé par le serveur, enregistré.
- `POST /captures/{id}/proposer`    une proposition neuve (rien n'est écrit).
- `POST /captures/{id}/fabriquer`   {brouillon?} -> {scenes, fiches, exemples, dossier} ; brouillons dans
                                    `tutoriels/<id>/` (rien n'est publié) ; une fabrication à la fois par capture (409).
- `POST /captures/{id}/parcours`    {brouillon?} -> le fichier `.dzparcours` (téléchargement).
- `GET  /parcours`                  les parcours importés.
- `POST /parcours/importer`         corps BRUT = le `.dzparcours` (plafonné en lisant : 413) -> {id}.
- `GET  /parcours/{pid}`            le parcours, chaque étape avec son `action` construite depuis CETTE installation.
- `GET  /parcours/{pid}/video`      la vidéo du parcours.
- `DELETE /parcours/{pid}`          retire un parcours importé."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from loguru import logger

from app.services import capture as C
from app.services import capture_montage as M
from app.services import tutoriels as T

router = APIRouter()

MAX_CORPS = 2 * 1024 * 1024
_EN_COURS: set[str] = set()


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


async def _json(request: Request) -> dict:
    corps = await request.body()
    if len(corps) > MAX_CORPS:
        raise HTTPException(413, "Corps de requête trop lourd.")
    try:
        d = json.loads(corps or b"{}")
    except ValueError:
        raise HTTPException(400, "Corps JSON illisible.") from None
    if not isinstance(d, dict):
        raise HTTPException(400, "Corps JSON illisible.")
    return d


def _refus(e):
    return HTTPException(getattr(e, "statut", 400), str(e))


_REFUS = (C.RefusCapture, M.RefusMontage, T.RefusTutoriel)


@router.get("/captures/{cid}")
async def lire(cid: str, request: Request):
    _local(request)
    try:
        b, propose = await asyncio.to_thread(T.lire_brouillon, cid)
        r = await asyncio.to_thread(C.lire, cid)
    except _REFUS as e:
        raise _refus(e) from None
    return {"capture": {"id": cid, "duree_ms": T.duree(r), "cree_utc": r["session"].get("cree_utc")},
            "brouillon": b, "propose": propose}


@router.put("/captures/{cid}")
async def enregistrer(cid: str, request: Request):
    _local(request)
    d = await _json(request)
    try:
        b = await asyncio.to_thread(T.ecrire_brouillon, cid, d.get("brouillon"))
    except _REFUS as e:
        raise _refus(e) from None
    logger.info(f"tutoriel {cid} : brouillon enregistré ({len(b['etapes'])} étapes)")
    return {"ok": True, "brouillon": b}


@router.post("/captures/{cid}/proposer")
async def proposer(cid: str, request: Request):
    _local(request)
    try:
        return {"brouillon": await asyncio.to_thread(T.proposer_pour, cid)}
    except _REFUS as e:
        raise _refus(e) from None


@router.post("/captures/{cid}/fabriquer")
async def fabriquer(cid: str, request: Request):
    _local(request)
    d = await _json(request)
    if not C.ID.match(cid or ""):
        raise HTTPException(400, "Identifiant de capture invalide.")
    if cid in _EN_COURS:
        raise HTTPException(409, "Une fabrication de ce tutoriel est déjà en cours.")
    _EN_COURS.add(cid)
    try:
        r = await asyncio.to_thread(T.fabriquer, cid, d.get("brouillon"))
    except _REFUS as e:
        raise _refus(e) from None
    finally:
        _EN_COURS.discard(cid)
    logger.info(f"tutoriel {cid} : {r['scenes']} scènes, {r['fiches']} fiches, {r['exemples']} exemples")
    return dict(r, ok=True)


@router.post("/captures/{cid}/parcours")
async def exporter(cid: str, request: Request):
    _local(request)
    d = await _json(request)
    try:
        f = await asyncio.to_thread(T.exporter, cid, d.get("brouillon"))
    except _REFUS as e:
        raise _refus(e) from None
    logger.info(f"tutoriel {cid} : parcours exporté ({f.stat().st_size} octets)")
    return FileResponse(f, media_type="application/zip", filename=f.name)


@router.get("/parcours")
async def lister(request: Request):
    _local(request)
    return {"parcours": await asyncio.to_thread(T.liste_parcours)}


@router.post("/parcours/importer")
async def importer(request: Request):
    _local(request)
    base = T.racine_parcours()
    base.mkdir(parents=True, exist_ok=True)
    fd, nom = tempfile.mkstemp(prefix=".recu.", suffix=".dzparcours", dir=base)
    tmp = Path(nom)
    try:
        lu = 0
        with os.fdopen(fd, "wb") as f:
            async for morceau in request.stream():
                lu += len(morceau)
                if lu > T.MAX_ZIP:
                    raise HTTPException(413, "Parcours trop lourd.")
                f.write(morceau)
        if lu == 0:
            raise HTTPException(400, "Parcours illisible.")
        try:
            pid = await asyncio.to_thread(T.importer, tmp)
        except T.RefusTutoriel as e:
            raise _refus(e) from None
    finally:
        tmp.unlink(missing_ok=True)
    logger.info(f"parcours {pid} importé ({lu} octets)")
    return {"ok": True, "id": pid}


@router.get("/parcours/{pid}")
async def lire_parcours(pid: str, request: Request):
    _local(request)
    try:
        return await asyncio.to_thread(T.lire_parcours, pid)
    except T.RefusTutoriel as e:
        raise _refus(e) from None


@router.get("/parcours/{pid}/video")
async def video(pid: str, request: Request):
    _local(request)
    try:
        f = await asyncio.to_thread(T.video_parcours, pid)
    except T.RefusTutoriel as e:
        raise _refus(e) from None
    return FileResponse(f, media_type="video/mp4" if f.suffix == ".mp4" else "video/webm")


@router.delete("/parcours/{pid}")
async def retirer(pid: str, request: Request):
    _local(request)
    try:
        await asyncio.to_thread(T.retirer_parcours, pid)
    except T.RefusTutoriel as e:
        raise _refus(e) from None
    logger.info(f"parcours {pid} retiré")
    return {"ok": True}
