# -*- coding: utf-8 -*-
"""t476 (lot F1 « Fiches modèle », 09/11/2026) — /api/modeles : les fiches modèle, en LECTURE (gratuit, aucune
écriture). Service : app.services.modeles_fiches ; contrat : docs/agent/modeles/MODELES.md.

  GET /api/modeles/index?langue=           familles (description, natures, ids) + table id -> famille
  GET /api/modeles/fiche?cle=&langue=      une fiche (famille ou id d'un modèle) : corps, bloc « Membres », tronc commun
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services import modeles_fiches as MF

router = APIRouter()


@router.get("/index")
async def modeles_index(langue: str = "fr"):
    familles = MF.index(langue)
    return {"familles": familles, "ids": {i: f["famille"] for f in familles for i in f["ids"]}}


@router.get("/fiche")
async def modeles_fiche(cle: str = "", langue: str = "fr"):
    f = MF.fiche(cle[:120], langue)
    if f is None:
        raise HTTPException(404, "fiche modèle inconnue")
    return f
