# -*- coding: utf-8 -*-
"""t318 (28/10/2026) (lot D4) — /api/live : le direct multi-destinations (plan docs/superpowers/plans/2026-10-28-t318-live.md,
spec boîte à outils §8.6).

Boucle locale SEULEMENT. L'espace est celui de la requête (en-tête X-Dz-Espace, sinon l'actif).
- `POST   /sessions`                 {comptes: [id…], titre} -> la vue publique (destinations SANS URL ni clé).
- `GET    /sessions/{id}`            la vue + la santé du flux.
- `WS     /sessions/{id}/flux`       binaire : les morceaux de la MediaRecorder, poussés dans ffmpeg (lancé à
                                     l'ouverture) ; texte en retour, chaque seconde : {type: "etat", …}. Client local
                                     ET en-tête Origin absent ou de même hôte (une page d'ailleurs ne s'y branche pas).
                                     Fermeture = ffmpeg arrêté.
- `POST   /sessions/{id}/marqueurs`  {t, libelle} : un marqueur de chapitre (ms depuis le début de la capture).
- `POST   /sessions/{id}/annonce`    {compte, texte} : le message Discord par webhook -> {ok, statut} (jamais l'URL).
- `POST   /sessions/{id}/terminer`   {capture_id?} : ffmpeg arrêté, <capture>.dzlive.json écrit -> {live, fichier}.
- `DELETE /sessions/{id}`            abandon (ffmpeg arrêté).
Journaux : identifiants, plateformes et nombres seulement ; jamais une URL de destination ni une clé."""
from __future__ import annotations

import asyncio
import json
import re
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from loguru import logger

from app.services import live as L

router = APIRouter()

MAX_MORCEAU = 8 * 1024 * 1024


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _espace() -> str:
    from app.services import espaces
    return espaces.espace_courant()


def _refus(e: L.RefusLive):
    return HTTPException(e.statut, str(e))


async def _json(request: Request) -> dict:
    corps = await request.body()
    if len(corps) > 64 * 1024:
        raise HTTPException(413, "Corps de requête trop lourd.")
    try:
        d = json.loads(corps or b"{}")
    except ValueError:
        raise HTTPException(400, "Corps JSON illisible.") from None
    if not isinstance(d, dict):
        raise HTTPException(400, "Corps JSON illisible.")
    return d


@router.post("/sessions")
async def ouvrir(request: Request):
    _local(request)
    d = await _json(request)
    try:
        v = await asyncio.to_thread(L.ouvrir, _espace(), d.get("comptes"), d.get("titre") or "")
    except L.RefusLive as e:
        raise _refus(e) from None
    logger.info(f"live {v['id']} : prêt ({', '.join(x['plateforme'] for x in v['destinations'])})")
    return v


@router.get("/sessions/{lid}")
async def lire(lid: str, request: Request):
    _local(request)
    try:
        return L.vue(lid)
    except L.RefusLive as e:
        raise _refus(e) from None


_HOTE_LOCAL = re.compile(r"^(127\.0\.0\.1|localhost|\[::1\])(:\d{1,5})?$")


def _origine_sure(ws: WebSocket) -> bool:
    """Client local, en-tête Host local (revue finale M1 : un rebond DNS garde un Host étranger) et Origin absente ou
    identique à Host."""
    from app.api.routes import _HOTES_LOCAUX
    hote = (ws.client.host if ws.client else "") or ""
    entete = (ws.headers.get("host") or "").lower()
    if hote not in _HOTES_LOCAUX or not _HOTE_LOCAL.match(entete):
        return False
    origine = ws.headers.get("origin")
    if not origine:
        return True
    return urlsplit(origine).netloc.lower() == entete


@router.websocket("/sessions/{lid}/flux")
async def flux(ws: WebSocket, lid: str):
    if not _origine_sure(ws):
        await ws.close(code=1008)
        return
    try:
        d = await asyncio.to_thread(L.brancher, lid)
    except L.RefusLive:
        await ws.close(code=1008)
        return
    await ws.accept()
    logger.info(f"live {lid} : flux branché")

    async def etats():
        while True:
            await asyncio.sleep(1)
            await ws.send_text(json.dumps({"type": "etat", **d.etat()}, ensure_ascii=False))

    tache = asyncio.create_task(etats())
    try:
        while True:
            m = await ws.receive()
            if m.get("type") == "websocket.disconnect":
                break
            octets = m.get("bytes")
            if octets:
                if len(octets) > MAX_MORCEAU or not await asyncio.to_thread(d.ecrire, octets):
                    break
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        tache.cancel()
        await asyncio.to_thread(L.debrancher, lid)
        try:
            await ws.close()
        except RuntimeError:
            pass
        logger.info(f"live {lid} : flux débranché")


@router.post("/sessions/{lid}/marqueurs")
async def marquer(lid: str, request: Request):
    _local(request)
    d = await _json(request)
    try:
        return L.marquer(lid, d.get("t"), d.get("libelle") or "")
    except L.RefusLive as e:
        raise _refus(e) from None


@router.post("/sessions/{lid}/annonce")
async def annoncer(lid: str, request: Request):
    _local(request)
    d = await _json(request)
    try:
        r = await L.annoncer(lid, d.get("compte"), d.get("texte") or "")
    except L.RefusLive as e:
        raise _refus(e) from None
    logger.info(f"live {lid} : annonce Discord {'envoyée' if r['ok'] else 'refusée'} ({r['statut']})")
    return r


@router.post("/sessions/{lid}/terminer")
async def terminer(lid: str, request: Request):
    _local(request)
    d = await _json(request)
    try:
        r = await asyncio.to_thread(L.terminer, lid, d.get("capture_id"))
    except L.RefusLive as e:
        raise _refus(e) from None
    logger.info(f"live {lid} : terminé ({len(r['live']['marqueurs'])} marqueur(s))")
    return r


@router.delete("/sessions/{lid}")
async def abandonner(lid: str, request: Request):
    _local(request)
    try:
        await asyncio.to_thread(L.abandonner, lid)
    except L.RefusLive as e:
        raise _refus(e) from None
    return {"ok": True}
