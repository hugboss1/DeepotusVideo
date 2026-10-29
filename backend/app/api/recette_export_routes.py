# -*- coding: utf-8 -*-
"""t346 (29/10/2026, D2 du lot Scenario) — /api/recettes : EXPORTER la recette d'un rendu, d'un plan ou d'un asset de
la Bibliothèque en skill (ZIP : SKILL.md + fabrication.pdf + recette.json + images réduites). Gratuit, aucune garde de
dépense (rien n'est appelé), local seulement (prompts et coûts de l'utilisateur). Service : services/recette_export.py.

  GET /api/recettes/export?type=job|plan|asset&id=…&lang=fr|en   -> application/zip (pièce jointe)
  GET /api/recettes/apercu?type=…&id=…&lang=…                    -> {type, id, titre, etapes, rates, couts, nom,
                                                                     skill_md, export}
400 type ou nom refusé, 404 introuvable (messages dans la langue de la requête, app/i18n/messages.json)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app import i18n
from app.api.routes import _require_localhost
from app.services import recette_export as RX

router = APIRouter()


async def _dossier(request: Request, type_: str, ident: str):
    _require_localhost(request)
    lang = i18n.langue_requete(request)
    try:
        return await RX.dossier(type_, ident)
    except RX.RecetteRefusee as e:
        raise HTTPException(400, i18n.msg("recette_export.refus", lang, detail=str(e)))
    except RX.RecetteIntrouvable:
        raise HTTPException(404, i18n.msg("recette_export.introuvable", lang, type=type_, id=str(ident)[:80]))


@router.get("/export")
async def exporter(request: Request, type: str = "", id: str = "", lang: str = ""):  # noqa: A002
    import asyncio
    d = await _dossier(request, type, id)
    nom, octets = await asyncio.to_thread(RX.archive, d, lang or i18n.langue_requete(request))
    return Response(content=octets, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"'})


@router.get("/apercu")
async def apercu(request: Request, type: str = "", id: str = "", lang: str = ""):  # noqa: A002
    d = await _dossier(request, type, id)
    return RX.apercu(d, lang or i18n.langue_requete(request))
