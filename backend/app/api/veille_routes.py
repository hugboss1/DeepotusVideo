# -*- coding: utf-8 -*-
"""t352 (27/10/2026) — /api/veille : la veille concurrentielle d'un espace (onglet « Veille » du tiroir F1).

- `GET  /{eid}`              {etat, rapport (le plus récent, ou null), veilles: [{date, classement, gardes}]}
- `GET  /{eid}/perimetre`    le dernier périmètre de l'espace, sinon celui par défaut (veille n°1)
- `POST /{eid}/collectes`    {perimetre?} : lance la collecte niveau 1 en fond (202) ; 409 si une tourne ; 422 périmètre
- `GET  /{eid}/verbatims`    ?date&theme&concurrent&limite : verbatims classés, sans auteur
- `POST /{eid}/importer`     {dossier} : importe le verbatims.jsonl d'une veille faite hors de l'app ; 413 au-delà de 20 Mo
Espace inconnu ou archivé : 404. Lecture seule sur le web, aucune dépense.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services import veille as V

router = APIRouter()


class CorpsCollecte(BaseModel):
    perimetre: dict | None = None


class CorpsImport(BaseModel):
    dossier: str


def _espace(eid: str) -> None:
    try:
        V._verifier(eid)
    except LookupError as e:
        raise HTTPException(404, str(e)) from None


@router.get("/{eid}")
async def lire(eid: str, date: str | None = None):
    _espace(eid)
    try:
        return {"etat": V.etat(eid), "rapport": V.dernier(eid, date), "veilles": V.lister(eid)}
    except ValueError as e:
        raise HTTPException(422, str(e)) from None


@router.get("/{eid}/perimetre")
async def lire_perimetre(eid: str):
    _espace(eid)
    return V.perimetre(eid)


@router.post("/{eid}/collectes")
async def collecter(eid: str, corps: CorpsCollecte | None = None):
    _espace(eid)
    try:
        r = await V.lancer(eid, (corps.perimetre if corps else None) or None)
    except V.ConflitCollecte as e:
        raise HTTPException(409, str(e)) from None
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    return JSONResponse(r, status_code=202)


@router.get("/{eid}/verbatims")
async def lire_verbatims(eid: str, date: str | None = None, theme: str | None = None, concurrent: str | None = None,
                         limite: int = 50):
    _espace(eid)
    try:
        return {"verbatims": V.verbatims(eid, date, theme, concurrent, limite)}
    except ValueError as e:
        raise HTTPException(422, str(e)) from None


@router.post("/{eid}/importer")
async def importer(eid: str, corps: CorpsImport):
    _espace(eid)
    try:
        return V.importer(eid, corps.dossier)
    except V.ImportTropGros as e:
        raise HTTPException(413, str(e)) from None
    except (ValueError, OSError) as e:
        raise HTTPException(422, str(e)) from None
