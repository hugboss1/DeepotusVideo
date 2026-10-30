# -*- coding: utf-8 -*-
"""t380 (30/10/2026) — /api/news/fils : les FILS SOCIAUX suivis de News (services/news_fils.py), local seulement.

- `GET    ""`                          les fils, les suggestions des agents, les plateformes, les fréquences, Apify prêt ou non
- `POST   ""`                          {plateforme, identifiant, nom?, frequence_h?} : ajout à la main (400, 409 déjà suivi)
- `PATCH  /{fid}`                      {pause?, frequence_h?, max?, nom?}
- `DELETE /{fid}`                      retire le fil et ses éléments du cache de News
- `GET    /{fid}/devis`                GRATUIT : le devis d'un relevé ({gratuit: true} pour un flux)
- `POST   /{fid}/accord`               {plafond_usd, confirme_cout: true} : 400, 503 sans clé, 409 sans confirme_cout (devis)
- `DELETE /{fid}/accord`               plus aucun relevé payant
- `POST   /{fid}/lire`                 un relevé maintenant : 409 sans accord ou devis au-delà du plafond du fil, 503 sans
                                       clé, 402 plafonds mensuels (`plafonds.verifier` « news » dans NF.relever), 502 échec
- `POST   /suggestions/{sid}/accepter` {frequence_h?} : le fil naît avec l'origine de la suggestion
- `POST   /suggestions/{sid}/ecarter`  jamais reproposée
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.services import news_fils as NF

router = APIRouter()


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _refus(e: NF.RefusFil) -> HTTPException:
    if e.statut in (400, 404) and not e.extra:
        return HTTPException(e.statut, str(e))
    return HTTPException(e.statut, {"code": e.code, "message": str(e), **e.extra})


def _inconnu(v, quoi: str = "fil"):
    if v is None and quoi == "fil":
        raise HTTPException(404, "fil inconnu")
    if v is None:
        raise HTTPException(404, "suggestion inconnue")
    return v


@router.get("", dependencies=[Depends(_local)])
async def lister():
    from app.services import apify as AP
    return dict(NF.lister(), plateformes={k: {"libelle": v["libelle"], "lecture": v["lecture"]}
                                          for k, v in NF.PLATEFORMES.items()},
                frequences_h=list(NF.FREQUENCES_H), frequence_defaut_h=NF.FREQUENCE_DEFAUT_H, apify=AP.etat())


@router.post("", dependencies=[Depends(_local)])
async def ajouter(body: dict):
    b = body or {}
    try:
        return {"fil": NF.ajouter(b.get("plateforme"), b.get("identifiant"), b.get("nom"), b.get("frequence_h"))}
    except NF.RefusFil as e:
        raise _refus(e) from None


@router.patch("/{fid}", dependencies=[Depends(_local)])
async def modifier(fid: str, body: dict):
    try:
        return {"fil": _inconnu(NF.modifier(fid, body or {}))}
    except NF.RefusFil as e:
        raise _refus(e) from None


@router.delete("/{fid}", dependencies=[Depends(_local)])
async def retirer(fid: str):
    if not NF.retirer(fid):
        raise HTTPException(404, "fil inconnu")
    return {"retire": fid}


@router.get("/{fid}/devis", dependencies=[Depends(_local)])
async def devis(fid: str):
    try:
        return _inconnu(await NF.devis(fid))
    except NF.RefusFil as e:
        raise _refus(e) from None


@router.post("/{fid}/accord", dependencies=[Depends(_local)])
async def accord(fid: str, body: dict):
    b = body or {}
    try:
        return {"fil": _inconnu(await NF.poser_accord(fid, b.get("plafond_usd"), b.get("confirme_cout")))}
    except NF.RefusFil as e:
        raise _refus(e) from None


@router.delete("/{fid}/accord", dependencies=[Depends(_local)])
async def retirer_accord(fid: str):
    return {"fil": _inconnu(NF.retirer_accord(fid))}


@router.post("/{fid}/lire", dependencies=[Depends(_local), Depends(_depense_locale)])
async def lire(fid: str):
    from app.services import apify as AP
    try:
        return _inconnu(await NF.relever(fid))
    except NF.RefusFil as e:
        raise _refus(e) from None
    except AP.SansCle as e:
        raise HTTPException(503, str(e)) from None
    except AP.ApifyRefus as e:
        raise HTTPException(e.code, str(e)) from None
    except AP.ApifyEchec as e:
        raise HTTPException(502, str(e)) from None


@router.post("/suggestions/{sid}/accepter", dependencies=[Depends(_local)])
async def accepter(sid: str, body: dict | None = None):
    try:
        return {"fil": _inconnu(NF.accepter(sid, (body or {}).get("frequence_h")), "suggestion")}
    except NF.RefusFil as e:
        raise _refus(e) from None


@router.post("/suggestions/{sid}/ecarter", dependencies=[Depends(_local)])
async def ecarter(sid: str):
    try:
        return {"suggestion": _inconnu(NF.ecarter(sid), "suggestion")}
    except NF.RefusFil as e:
        raise _refus(e) from None
