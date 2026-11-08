# -*- coding: utf-8 -*-
"""t433 (lot M0 « Méthodes », 08/11/2026) — /api/methodes : le catalogue des méthodes, en LECTURE (gratuit, aucune
écriture). Service : app.services.methodes.

  GET /api/methodes?famille=&agent=&ecran=&q=&langue=   la galerie filtrée
  GET /api/methodes/reperes?langue=                     familles, agents, écrans (avec leurs nombres), source
  GET /api/methodes/{slug}?langue=                      une fiche complète
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services import methodes as M

router = APIRouter()


@router.get("")
async def methodes_lister(famille: str = "", agent: str = "", ecran: str = "", q: str = "", langue: str = "fr"):
    ms = M.lister(famille=famille, agent=agent, ecran=ecran, q=q[:200], langue=langue)
    return {"total": len(ms), "methodes": ms}


@router.get("/reperes")
async def methodes_reperes(langue: str = "fr"):
    return M.reperes(langue)


@router.get("/{slug}")
async def methodes_fiche(slug: str, langue: str = "fr"):
    f = M.fiche(slug, langue)
    if f is None:
        raise HTTPException(404, "méthode inconnue")
    return f
