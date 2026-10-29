# -*- coding: utf-8 -*-
"""t345 (29/10/2026, D1 du lot Scenario) — /api/mcp : le serveur MCP local de DeepotusVideo (service :
services/mcp_pont.py ; processus stdio lancé par Claude Code : app/mcp_stdio.py). Local seulement, chaque route.

  GET  /api/mcp/etat                      -> {actif, commande, outils, en_attente}          (écran)
  PUT  /api/mcp/reglages {actif}          -> {actif}                                         (écran : Origin local exigé)
  GET  /api/mcp/journal?n=                -> {appels}
  GET  /api/mcp/demandes?etat=            -> {demandes}
  POST /api/mcp/demandes/{id}/commencer   -> {route, corps…}  l'utilisateur a cliqué « Lancer » (Origin local exigé)
  POST /api/mcp/demandes/{id}/refuser     -> la demande refusée                              (Origin local exigé)
  POST /api/mcp/demandes/{id}/resultat {ok, job_id?, fichier?, message?}                     (Origin local exigé)
  GET  /api/mcp/outils                    -> {outils}       le client MCP (403 si désactivé)
  POST /api/mcp/appel {outil, arguments}  -> {ok, resume, donnees}  le client MCP (en-tête X-Deepotus-MCP: 1 exigé)
Aucune de ces routes ne dépense : la génération est appelée par l'écran, au clic de l'utilisateur, sur sa route
habituelle (plafonds.verifier y est)."""
from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, HTTPException, Request

from app import i18n
from app.api.routes import _require_localhost
from app.services import mcp_pont as P

router = APIRouter()
_HOTES_ECRAN = {"127.0.0.1", "localhost", "::1"}


def _refus(request: Request, e: P.RefusPont) -> HTTPException:
    return HTTPException(e.statut, i18n.msg(e.cle, i18n.langue_requete(request), **e.valeurs))


def _ecran(request: Request) -> None:
    """Les gestes de l'UTILISATEUR viennent du navigateur de l'app : un Origin local est exigé (le client MCP, natif,
    n'en envoie pas ; la garde CSRF de main.py refuse déjà tout Origin étranger)."""
    from app.config import APP_HOSTNAME
    o = request.headers.get("origin") or ""
    try:
        h = (urllib.parse.urlparse(o).hostname or "").lower() if o else ""
    except ValueError:
        h = ""
    if not h or h not in (_HOTES_ECRAN | {APP_HOSTNAME}):
        raise HTTPException(403, i18n.msg("mcp.ecran_requis", i18n.langue_requete(request)))


@router.get("/etat")
async def etat(request: Request):
    _require_localhost(request)
    return {"actif": P.actif(), "commande": P.commande(),
            "outils": [{"nom": o["name"], "nature": o["nature"], "titre": o["annotations"]["title"]} for o in P.outils()],
            "en_attente": len(P.demandes("en_attente"))}


@router.put("/reglages")
async def reglages(request: Request, body: dict):
    _require_localhost(request)
    _ecran(request)
    v = (body or {}).get("actif")
    if not isinstance(v, bool):
        raise HTTPException(400, i18n.msg("mcp.actif_requis", i18n.langue_requete(request)))
    return {"actif": P.activer(v)}


@router.get("/journal")
async def journal(request: Request, n: int = 50):
    _require_localhost(request)
    return {"appels": P.journal(n)}


@router.get("/demandes")
async def demandes(request: Request, etat: str = ""):
    _require_localhost(request)
    return {"demandes": P.demandes(etat if etat in P.ETATS else None)}


@router.post("/demandes/{did}/commencer")
async def commencer(did: str, request: Request):
    _require_localhost(request)
    _ecran(request)
    try:
        return P.commencer(did)
    except P.RefusPont as e:
        raise _refus(request, e)


@router.post("/demandes/{did}/refuser")
async def refuser(did: str, request: Request):
    _require_localhost(request)
    _ecran(request)
    try:
        return P.refuser(did)
    except P.RefusPont as e:
        raise _refus(request, e)


@router.post("/demandes/{did}/resultat")
async def resultat(did: str, request: Request, body: dict):
    _require_localhost(request)
    _ecran(request)
    try:
        return P.noter(did, (body or {}).get("ok") is True, body if isinstance(body, dict) else {})
    except P.RefusPont as e:
        raise _refus(request, e)


@router.get("/outils")
async def outils(request: Request):
    _require_localhost(request)
    if not P.actif():
        raise HTTPException(403, i18n.msg("mcp.desactive", i18n.langue_requete(request)))
    return {"outils": [{k: o[k] for k in ("name", "description", "inputSchema", "annotations")} for o in P.outils()]}


@router.post("/appel")
async def appel(request: Request, body: dict):
    _require_localhost(request)
    if request.headers.get("x-deepotus-mcp") != "1":
        raise HTTPException(400, i18n.msg("mcp.entete", i18n.langue_requete(request)))
    lang = "en" if str((body or {}).get("lang") or "") == "en" else "fr"
    try:
        return await P.appeler((body or {}).get("outil"), (body or {}).get("arguments"), lang)
    except P.RefusPont as e:
        raise _refus(request, e)
