# -*- coding: utf-8 -*-
"""t435 (lot M2 « Méthodes », 08/11/2026) — /api/agents-metier : les agents métier (service app.services.agent_metier).

  GET  /api/agents-metier?langue=                         les agents du catalogue, `disponible` pour les actifs
  POST /api/agents-metier/{agent}/conversations           {espace_id?, methode?} -> la conversation neuve
  GET  /api/agents-metier/{agent}/conversations/{cid}     la conversation (messages en texte, outils, coûts)
  POST /api/agents-metier/{agent}/conversations/{cid}/devis    {texte, langue?}   devis GRATUIT d'un message
  POST /api/agents-metier/{agent}/conversations/{cid}/message  {texte, langue?, confirme_cout, max_usd}   PAYANT

Ordre de refus du message, tout AVANT la dépense : agent ou conversation inconnus (404), texte vide (400), clé absente
(503), `confirme_cout` absent (409, devis joint), accord invalide (400), conversation occupée (409), plafond de la
catégorie de l'agent (402) au premier appel. La création et le message sont réservés à la machine locale.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.services import agent_metier as AM

router = APIRouter()


def _local(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _corps(body) -> dict:
    return body if isinstance(body, dict) else {}


def _agent(agent: str) -> None:
    if not AM.actif(agent):
        raise HTTPException(404, "Cet agent métier n'est pas encore disponible.")


def _conv(agent: str, cid: str) -> dict:
    _agent(agent)
    try:
        c = AM.lire(agent, cid)
    except ValueError:
        c = None
    if c is None:
        raise HTTPException(404, "Conversation inconnue.")
    return c


@router.get("")
async def agents_metier(langue: str = "fr"):
    return {"agents": AM.agents(langue)}


@router.post("/{agent}/conversations", dependencies=[Depends(_local)])
async def agent_metier_creer(agent: str, body: dict | None = None):
    _agent(agent)
    b = _corps(body)
    return AM.creer(agent, str(b.get("espace_id") or ""), str(b.get("methode") or ""))


@router.get("/{agent}/conversations/{cid}")
async def agent_metier_lire(agent: str, cid: str):
    return _conv(agent, cid)


@router.post("/{agent}/conversations/{cid}/devis")
async def agent_metier_devis(agent: str, cid: str, body: dict | None = None):
    _conv(agent, cid)
    b = _corps(body)
    return AM.devis_message(agent, cid, str(b.get("texte") or ""), str(b.get("langue") or "fr"))


@router.post("/{agent}/conversations/{cid}/message", dependencies=[Depends(_local)])
async def agent_metier_message(agent: str, cid: str, body: dict | None = None):
    _conv(agent, cid)
    b = _corps(body)
    texte = b.get("texte") if isinstance(b.get("texte"), str) else ""
    if not texte.strip():
        raise HTTPException(400, "Message vide.")
    langue = str(b.get("langue") or "fr")
    d = AM.devis_message(agent, cid, texte, langue)
    if not d["cle"]:
        raise HTTPException(503, "Le moteur Anthropic n'est pas configuré (Réglages › Clés d'API).")
    if b.get("confirme_cout") is not True:
        raise HTTPException(409, {"message": "Confirme le coût du message avant de l'envoyer.", "usd": d["usd"],
                                  "devis": d})
    try:
        return await AM.message(agent, cid, texte, max_usd=b.get("max_usd", d["usd"]), langue=langue)
    except AM.Occupee:
        raise HTTPException(409, "L'agent répond déjà dans cette conversation.")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        if str(e) == "sans_cle":
            raise HTTPException(503, "Le moteur Anthropic n'est pas configuré (Réglages › Clés d'API).")
        raise HTTPException(502, str(e)[:300])
