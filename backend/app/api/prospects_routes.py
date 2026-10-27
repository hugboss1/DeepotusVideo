# -*- coding: utf-8 -*-
"""t353 (27/10/2026) — /api/prospects : la fiche Prospects d'un espace (onglet « Prospects » du tiroir F1). Local seulement
(lectures comprises : des données personnelles ; le compagnon arrive en P8). Aucun envoi, aucune dépense.

- `GET    /{eid}?statut=`                        {prospects, compte_par_statut, oppositions: n}
- `POST   /{eid}`                                crée (201) ; refus {code, message[, pid]} en 404 / 409 / 422
- `GET`·`PATCH`·`DELETE /{eid}/{pid}`             lit, modifie, efface (`?inscrire_opposition=0` : saisie erronée)
- `POST   /{eid}/{pid}/statut`                   {statut, detail} -> {prospect, note}
- `POST   /{eid}/{pid}/consentements[/revoquer]` {canal, base_legale, moyen, date?} / {canal}
- `POST   /{eid}/{pid}/contacts`                 {sens: entrant|sortant, detail}
- `POST   /{eid}/{pid}/opposer`                  anonymise et inscrit au registre
- `GET    /{eid}/{pid}/export`                   la fiche en pièce jointe `prospect-<pid>.json` (droit d'accès)
- `POST   /oppositions`                          {identifiant} saisi à la main -> {inscrit: bool} (rien en clair)
Les messages passent par L10 (le gestionnaire traduit le champ `message` d'un detail dict).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.api.routes import _require_localhost
from app.services import oppositions as O, prospects as P

router = APIRouter()


def _faire(request: Request, geste):
    _require_localhost(request)
    try:
        return geste()
    except P.RefusProspect as e:
        d = {"code": e.code, "message": e.message}
        if e.pid:
            d["pid"] = e.pid
        raise HTTPException(e.statut, d) from None


def _corps(body) -> dict:
    return body if isinstance(body, dict) else {}


@router.post("/oppositions")
def post_opposition(request: Request, body: dict):
    _require_localhost(request)
    ident = _corps(body).get("identifiant")
    if O.normaliser(ident) is None:
        raise HTTPException(422, "identifiant illisible : une adresse e-mail, un numéro ou un profil est attendu")
    return {"inscrit": O.inscrire([ident], "saisie") > 0}


@router.get("/{eid}")
def get_prospects(request: Request, eid: str, statut: str | None = None):
    def geste():
        tous = P.lister(eid)
        compte = {}
        for f in tous:
            compte[f["statut"]] = compte.get(f["statut"], 0) + 1
        return {"prospects": [f for f in tous if not statut or f["statut"] == statut],
                "compte_par_statut": compte, "oppositions": O.compte()}
    return _faire(request, geste)


@router.post("/{eid}", status_code=201)
def post_prospect(request: Request, eid: str, body: dict):
    return _faire(request, lambda: P.creer(eid, _corps(body)))


@router.get("/{eid}/{pid}")
def get_prospect(request: Request, eid: str, pid: str):
    return _faire(request, lambda: P.lire(eid, pid))


@router.patch("/{eid}/{pid}")
def patch_prospect(request: Request, eid: str, pid: str, body: dict):
    return _faire(request, lambda: P.modifier(eid, pid, _corps(body)))


@router.delete("/{eid}/{pid}")
def delete_prospect(request: Request, eid: str, pid: str, inscrire_opposition: int = 1):
    _faire(request, lambda: P.effacer(eid, pid, inscrire_opposition=bool(inscrire_opposition)))
    return {"efface": pid}


@router.post("/{eid}/{pid}/statut")
def post_statut(request: Request, eid: str, pid: str, body: dict):
    b = _corps(body)
    return _faire(request, lambda: P.changer_statut(eid, pid, b.get("statut"), str(b.get("detail") or "")))


@router.post("/{eid}/{pid}/consentements")
def post_consentement(request: Request, eid: str, pid: str, body: dict):
    b = _corps(body)
    return _faire(request, lambda: P.ajouter_consentement(eid, pid, b.get("canal"), b.get("base_legale"), b.get("moyen"),
                                                          b.get("date")))


@router.post("/{eid}/{pid}/consentements/revoquer")
def post_revoquer(request: Request, eid: str, pid: str, body: dict):
    return _faire(request, lambda: P.revoquer_consentement(eid, pid, _corps(body).get("canal")))


@router.post("/{eid}/{pid}/contacts")
def post_contact(request: Request, eid: str, pid: str, body: dict):
    b = _corps(body)
    return _faire(request, lambda: P.noter_contact(eid, pid, b.get("sens"), str(b.get("detail") or "")))


@router.post("/{eid}/{pid}/opposer")
def post_opposer(request: Request, eid: str, pid: str):
    return _faire(request, lambda: P.opposer(eid, pid))


@router.get("/{eid}/{pid}/export")
def get_export(request: Request, eid: str, pid: str):
    doc = _faire(request, lambda: P.exporter(eid, pid))
    return Response(json.dumps(doc, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="prospect-{doc["id"]}.json"'})
