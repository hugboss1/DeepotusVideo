# -*- coding: utf-8 -*-
"""Assistant « Demander à Deepotus » (spec 2026-10-19-agent-aide-design.md, 19/10/2026) — /api/agent.

Boucle locale SEULEMENT, comme les Réglages : la question part vers le moteur de texte de l'utilisateur, sous le
plafond « aide » (le 402 `dz_plafond` remonte tel quel jusqu'au dialogue de /shared/dz-plafonds.js).
A5 : `/estimer` donne le devis GRATUIT d'un appel avec capture ; `/demander` porte alors `image` et `max_usd` (409 si
le coût recalculé dépasse le montant accepté).
"""
import asyncio
import json

from fastapi import APIRouter, HTTPException, Request

from app.services import agent_aide as A

router = APIRouter()

_HOTES_LOCAUX = ("127.0.0.1", "::1", "localhost", "testclient")
MAX_CORPS = 8_000_000           # une capture JPEG de 1 280 px tient très en dessous


def _local(request: Request) -> None:
    host = (request.client.host if request.client else "") or ""
    if host not in _HOTES_LOCAUX:
        raise HTTPException(403, "L'assistant n'est accessible que depuis ce PC.")


async def _corps(request: Request):
    try:
        taille = int(request.headers.get("content-length") or 0)
    except ValueError:
        taille = 0
    if taille > MAX_CORPS:
        raise HTTPException(413, "Demande trop lourde.")        # refus AVANT de lire
    morceaux, total = [], 0
    async for morceau in request.stream():                       # lecture en flux, coupée à MAX_CORPS + 1 octets
        total += len(morceau)
        if total > MAX_CORPS:
            raise HTTPException(413, "Demande trop lourde.")
        morceaux.append(morceau)
    brut = b"".join(morceaux)
    try:
        return json.loads(brut or b"null")
    except ValueError:
        raise HTTPException(400, "Corps JSON attendu.") from None


@router.get("/etat")
async def etat(request: Request):
    _local(request)
    return await asyncio.to_thread(A.etat)      # la vision d'Ollama et la voix interrogent des serveurs locaux


@router.post("/estimer")
async def estimer(request: Request):
    _local(request)
    corps = await _corps(request)
    from app.i18n import langue_requete
    try:
        return await asyncio.to_thread(A.estimer_vue, corps, langue_requete(request))
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.post("/demander")
async def demander(request: Request):
    _local(request)
    corps = await _corps(request)
    from app.i18n import langue_requete
    try:
        return await A.demander(corps, langue_requete(request))
    except A.CoutChange:
        raise HTTPException(409, "Le coût a changé depuis ton accord : rien n'a été envoyé. Redemande.") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from None
