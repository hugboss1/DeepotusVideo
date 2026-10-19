# -*- coding: utf-8 -*-
"""Assistant « Demander à Deepotus » (spec 2026-10-19-agent-aide-design.md, 19/10/2026) — /api/agent.

Boucle locale SEULEMENT, comme les Réglages : la question part vers le moteur de texte de l'utilisateur, sous le
plafond « aide » (le 402 `dz_plafond` remonte tel quel jusqu'au dialogue de /shared/dz-plafonds.js).
"""
from fastapi import APIRouter, HTTPException, Request

from app.services import agent_aide as A

router = APIRouter()

_HOTES_LOCAUX = ("127.0.0.1", "::1", "localhost", "testclient")


def _local(request: Request) -> None:
    host = (request.client.host if request.client else "") or ""
    if host not in _HOTES_LOCAUX:
        raise HTTPException(403, "L'assistant n'est accessible que depuis ce PC.")


@router.get("/etat")
async def etat(request: Request):
    _local(request)
    return A.etat()


@router.post("/demander")
async def demander(request: Request):
    _local(request)
    try:
        corps = await request.json()
    except ValueError:
        raise HTTPException(400, "Corps JSON attendu.") from None
    from app.i18n import langue_requete
    try:
        return await A.demander(corps, langue_requete(request))
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from None
