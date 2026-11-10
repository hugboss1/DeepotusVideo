# -*- coding: utf-8 -*-
"""t476 (lot F1 « Fiches modèle », 09/11/2026) — /api/modeles : les fiches modèle, en LECTURE (gratuit, aucune
écriture). Service : app.services.modeles_fiches ; contrat : docs/agent/modeles/MODELES.md.

  GET /api/modeles/index?langue=           familles (description, natures, ids) + table id -> famille
  GET /api/modeles/fiche?cle=&langue=      une fiche (famille ou id d'un modèle) : corps, bloc « Membres », tronc commun
  POST /api/modeles/recommander            t492 : {nature, consigne, contraintes, langue} -> premier, alternative,
                                           brouillon, classement, écartés (modeles_conseil.recommander, sans LLM)
  POST /api/modeles/verifier               t492 : {modele, prompt} -> constats (modeles_conseil.verifier_prompt)
"""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from app.services import modeles_conseil as MC, modeles_fiches as MF

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


@router.post("/recommander")
async def modeles_recommander(corps: dict = Body(default_factory=dict)):
    c = corps.get("contraintes") if isinstance(corps.get("contraintes"), dict) else {}
    try:
        return MC.recommander(str(corps.get("nature") or ""), str(corps.get("consigne") or "")[:500], c,
                              str(corps.get("langue") or "fr"))
    except KeyError:
        raise HTTPException(400, "nature d'appel inconnue")
    except ValueError:
        raise HTTPException(400, "contrainte illisible")


@router.post("/verifier")
async def modeles_verifier(corps: dict = Body(default_factory=dict)):
    try:
        return MC.verifier_prompt(str(corps.get("modele") or "")[:120], str(corps.get("prompt") or "")[:20000])
    except KeyError:
        raise HTTPException(404, "modèle d'IA inconnu")
