# -*- coding: utf-8 -*-
"""t503 (lot G13, 26/11/2026) — /api/styles-reel : la bibliothèque de styles de reel nommés, en LECTURE.

  GET /api/styles-reel                       les styles (résumé) et les familles, dans la langue de la requête
  GET /api/styles-reel/{id}                  un style complet : gabarit et emplacements, pages motion, voix, musique,
                                             sous-titres, rythme, ce qu'il faut fournir
  GET /api/styles-reel/{id}/devis?duree_s=&moteur=
                                             le devis GRATUIT de la production (styles_reel.devis_style) : rien n'est
                                             lancé, aucun moteur n'est appelé

Boucle locale seulement. Aucune route payante ni d'écriture : lancer un reel passe par les écrans existants (Templates,
Rendu motion code, Voix, Musique), chacun sous sa garde de plafond. Service : app.services.styles_reel."""
from fastapi import APIRouter, HTTPException, Request

from app.i18n import langue_requete
from app.services import styles_reel as SR

router = APIRouter()

_HOTES_LOCAUX = ("127.0.0.1", "::1", "localhost", "testclient")


def _local(request: Request) -> None:
    host = (request.client.host if request.client else "") or ""
    if host not in _HOTES_LOCAUX:
        raise HTTPException(403, "Les styles de reel ne sont accessibles que depuis ce PC.")


def _lg(request: Request, langue: str) -> str:
    return langue if langue in SR.LANGUES else langue_requete(request)


@router.get("")
async def lister(request: Request, langue: str = ""):
    _local(request)
    lg = _lg(request, langue)
    return {"styles": SR.lister_styles(lg), "familles": SR.familles(lg)}


@router.get("/{sid}")
async def lire(sid: str, request: Request, langue: str = ""):
    _local(request)
    s = SR.style(sid[:60], _lg(request, langue))
    if s is None:
        raise HTTPException(404, "Style de reel inconnu.")
    return s


@router.get("/{sid}/devis")
async def devis(sid: str, request: Request, duree_s: float | None = None, moteur: str = "anthropic",
                langue: str = ""):
    _local(request)
    try:
        return SR.devis_style(sid[:60], duree_s, _lg(request, langue), moteur[:40])
    except LookupError as e:
        raise HTTPException(404, str(e)) from None
