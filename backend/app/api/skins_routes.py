# -*- coding: utf-8 -*-
"""t316 (28/10/2026) (lot D2) — /api/skins : les skins qui habillent la scène de la capture (plan
docs/superpowers/plans/2026-10-28-t316-skins.md, tâche 2 ; spec boîte à outils §8.5).

Boucle locale SEULEMENT (`routes._require_localhost`). L'espace est celui de la requête (en-tête X-Dz-Espace, sinon
l'espace actif : `espaces.espace_courant()`).
- `GET    /`                          {espace, espace_nom, choisi, skins (de l'espace), livres}
- `GET    /actif`                     {skin | null, contexte} : le skin de l'espace (défaut livre-deepotus)
- `PUT    /choix`                     {skin_id | ""} -> {choisi}
- `POST   /`                          {base?, nom?} -> skin neuf de l'espace (copie d'un livré ou d'un skin)
- `POST   /import`                    corps = le .zip -> skin neuf de l'espace {…, ignores}
- `GET    /{id}`                      {skin, contexte}
- `PUT    /{id}`                      skin -> skin (livré : 409)
- `DELETE /{id}`                      -> {supprime}
- `GET|PUT|DELETE /{id}/images/{logo|fond}`  l'image du skin (PUT : corps brut, relu par Pillow)
- `GET    /{id}/export`               le .zip (skin.json + images)
Aucun réseau, aucune dépense. Journaux : identifiants et tailles seulement."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from loguru import logger

from app.services import skins as K

router = APIRouter()


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _espace() -> str:
    from app.services import espaces
    return espaces.espace_courant()


def _refus(e: K.RefusSkin):
    return HTTPException(e.statut, str(e))


async def _corps(request: Request, maximum: int) -> bytes:
    octets = bytearray()
    async for bout in request.stream():
        octets += bout
        if len(octets) > maximum:
            raise HTTPException(413, "Corps de requête trop lourd.")
    return bytes(octets)


async def _json(request: Request, maximum: int = 256 * 1024) -> dict:
    corps = await _corps(request, maximum)
    try:
        d = json.loads(corps or b"{}")
    except ValueError:
        raise HTTPException(400, "Corps JSON illisible.") from None
    if not isinstance(d, dict):
        raise HTTPException(400, "Corps JSON illisible.")
    return d


async def _faire(f, *args):
    try:
        return await asyncio.to_thread(f, *args)
    except K.RefusSkin as e:
        raise _refus(e) from None


@router.get("")
@router.get("/")
async def lister(request: Request):
    _local(request)
    eid = _espace()
    cx = await _faire(K.contexte, eid)
    return {"espace": eid, "espace_nom": cx["espace"]["nom"], "choisi": await _faire(K.choisi, eid),
            "skins": await _faire(K.lister, eid), "livres": await _faire(K.livres)}


@router.get("/actif")
async def actif(request: Request):
    _local(request)
    eid = _espace()
    return {"skin": await _faire(K.actif, eid), "contexte": await _faire(K.contexte, eid)}


@router.put("/choix")
async def choisir(request: Request):
    _local(request)
    d = await _json(request)
    eid = _espace()
    sid = await _faire(K.choisir, eid, d.get("skin_id"))
    logger.info(f"skins : espace {eid} -> {sid or 'sans habillage'}")
    return {"choisi": sid}


@router.post("")
@router.post("/")
async def creer(request: Request):
    _local(request)
    d = await _json(request)
    base = d.get("base")
    if base is not None and not isinstance(base, str):
        raise HTTPException(400, "Identifiant de skin invalide.")
    v = await _faire(K.creer, base or None, d.get("nom"), _espace())
    logger.info(f"skins : {v['id']} créé (base {base or '-'})")
    return v


@router.post("/import")
async def importer(request: Request):
    _local(request)
    octets = await _corps(request, K.MAX_ZIP)
    v = await _faire(K.importer, octets, _espace())
    logger.info(f"skins : {v['id']} importé ({len(octets)} octets, {len(v['ignores'])} entrées ignorées)")
    return v


@router.get("/{sid}")
async def lire(sid: str, request: Request):
    _local(request)
    v = await _faire(K.du_meme_espace, sid, _espace())
    return {"skin": v, "contexte": await _faire(K.contexte, v["espace_id"] or _espace())}


@router.put("/{sid}")
async def enregistrer(sid: str, request: Request):
    _local(request)
    d = await _json(request)
    await _faire(K.du_meme_espace, sid, _espace())
    return await _faire(K.enregistrer, sid, d)


@router.delete("/{sid}")
async def supprimer(sid: str, request: Request):
    _local(request)
    await _faire(K.du_meme_espace, sid, _espace())
    await _faire(K.supprimer, sid)
    logger.info(f"skins : {sid} supprimé")
    return {"supprime": sid}


@router.get("/{sid}/images/{nom}")
async def image(sid: str, nom: str, request: Request):
    _local(request)
    await _faire(K.du_meme_espace, sid, _espace())
    p = await _faire(K.chemin_image, sid, nom)
    return FileResponse(str(p), media_type="image/png", headers={"Cache-Control": "no-cache"})


@router.put("/{sid}/images/{nom}")
async def poser_image(sid: str, nom: str, request: Request):
    _local(request)
    octets = await _corps(request, K.MAX_IMAGE + 1)
    await _faire(K.du_meme_espace, sid, _espace())
    return await _faire(K.poser_image, sid, nom, octets)


@router.delete("/{sid}/images/{nom}")
async def retirer_image(sid: str, nom: str, request: Request):
    _local(request)
    await _faire(K.du_meme_espace, sid, _espace())
    return await _faire(K.retirer_image, sid, nom)


@router.get("/{sid}/export")
async def exporter(sid: str, request: Request):
    _local(request)
    await _faire(K.du_meme_espace, sid, _espace())
    nom, octets = await _faire(K.exporter, sid)
    return Response(octets, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"', "Cache-Control": "no-store"})
