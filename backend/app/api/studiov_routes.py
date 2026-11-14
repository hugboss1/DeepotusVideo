# -*- coding: utf-8 -*-
"""SV1 (14/11/2026) — /api/studiov : le studio virtuel 3D de la capture et du live (conception
docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md).

Boucle locale SEULEMENT (`routes._require_localhost`). L'espace est celui de la requête (X-Dz-Espace, sinon l'actif).
- `GET    /`               {espace, espace_nom, choisi, decors (de l'espace), livres, catalogue}
- `GET    /actif`          {decor | null, contexte} : le décor de l'espace ("" par défaut : pas de studio)
- `PUT    /choix`          {decor_id | ""} -> {choisi}
- `POST   /`               {base?, nom?} -> décor neuf de l'espace (copie d'un livré ou d'un décor de l'espace)
- `GET    /{id}`           {decor, contexte}
- `PUT    /{id}`           recette -> décor (livré : 409)
- `DELETE /{id}`           -> {supprime}
- `GET    /{id}/fabrique`  le GLB fabriqué par Blender, s'il existe (404 sinon)
Aucun réseau, aucune dépense. Journaux : identifiants seulement."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from loguru import logger

from app.services import studiov as S

router = APIRouter()


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _espace() -> str:
    from app.services import espaces
    return espaces.espace_courant()


async def _json(request: Request, maximum: int = 512 * 1024) -> dict:
    octets = bytearray()
    async for bout in request.stream():
        octets += bout
        if len(octets) > maximum:
            raise HTTPException(413, "Corps de requête trop lourd.")
    try:
        d = json.loads(bytes(octets) or b"{}")
    except ValueError:
        raise HTTPException(400, "Corps JSON illisible.") from None
    if not isinstance(d, dict):
        raise HTTPException(400, "Corps JSON illisible.")
    return d


async def _faire(f, *args):
    try:
        return await asyncio.to_thread(f, *args)
    except S.RefusStudio as e:
        raise HTTPException(e.statut, str(e)) from None


@router.get("")
@router.get("/")
async def lister(request: Request):
    _local(request)
    eid = _espace()
    cx = await _faire(S.contexte, eid)
    return {"espace": eid, "espace_nom": cx["espace"]["nom"], "choisi": await _faire(S.choisi, eid),
            "decors": await _faire(S.lister, eid), "livres": await _faire(S.livres), "catalogue": S.catalogue()}


@router.get("/actif")
async def actif(request: Request):
    _local(request)
    eid = _espace()
    sid = await _faire(S.choisi, eid)
    return {"decor": await _faire(S.lire, sid) if sid else None, "contexte": await _faire(S.contexte, eid)}


@router.put("/choix")
async def choisir(request: Request):
    _local(request)
    d = await _json(request)
    return {"choisi": await _faire(S.choisir, _espace(), d.get("decor_id"))}


@router.post("")
@router.post("/")
async def creer(request: Request):
    _local(request)
    d = await _json(request)
    v = await _faire(S.creer, d.get("base") or None, d.get("nom"), _espace())
    logger.info("studiov: décor créé {} (base {})", v["id"], v["base"])
    return v


@router.get("/{sid}")
async def lire(sid: str, request: Request):
    _local(request)
    eid = _espace()
    return {"decor": await _faire(S.du_meme_espace, sid, eid), "contexte": await _faire(S.contexte, eid)}


@router.put("/{sid}")
async def enregistrer(sid: str, request: Request):
    _local(request)
    d = await _json(request)
    if not S.ID_LIVRE.match(sid):
        await _faire(S.du_meme_espace, sid, _espace())
    return await _faire(S.enregistrer, sid, d)


@router.delete("/{sid}")
async def supprimer(sid: str, request: Request):
    _local(request)
    if not S.ID_LIVRE.match(sid):
        await _faire(S.du_meme_espace, sid, _espace())
    await _faire(S.supprimer, sid)
    logger.info("studiov: décor supprimé {}", sid)
    return {"supprime": sid}


@router.get("/{sid}/fabrique")
async def fabrique(sid: str, request: Request):
    _local(request)
    await _faire(S.du_meme_espace, sid, _espace())
    f = S.chemin_fabrique(sid)
    if f is None:
        raise HTTPException(404, "Décor non fabriqué.")
    return FileResponse(f, media_type="model/gltf-binary", headers={"Cache-Control": "no-cache"})
