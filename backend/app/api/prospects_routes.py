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
- `POST   /oppositions/retirer`                  {identifiant} : saisie erronée retirée, journalisée -> {retire: bool} ;
                                                 409 pour une opposition de la personne (t353 suite, M6)
- la liste porte aussi `espaces_demo` {id: nom} (t353 suite, M8)
- `GET    /{eid}/sequences?pid=`                 t355 : {sequences} (étapes « due », lien « ouvrir » d'un canal manuel)
- `POST   /{eid}/sequences/{sid}/valider|planifier|annuler` ({debut?} pour planifier) ; `…/etapes/{rang}/envoye` (manuel)
Les messages passent par L10 (le gestionnaire traduit le champ `message` d'un detail dict). Relecture I4 : routes ASYNC,
sur la boucle comme les autres écrivains d'espaces.json (le geste démonstration y écrit) : jamais depuis un thread.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.api.routes import _require_localhost
from app.services import espaces as _es, oppositions as O, prospects as P, prospects_sequences as SQ

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
async def post_opposition(request: Request, body: dict):
    _require_localhost(request)
    ident = _corps(body).get("identifiant")
    if O.normaliser(ident) is None:
        raise HTTPException(422, "identifiant illisible : une adresse e-mail, un numéro ou un profil est attendu")
    try:
        return {"inscrit": O.inscrire([ident], "saisie") > 0}
    except O.RegistreIndisponible as e:
        raise HTTPException(503, str(e)) from None


@router.post("/oppositions/retirer")
async def post_retrait(request: Request, body: dict):
    """t353 suite (M6) : retire une saisie erronée (origine saisie ou effacement), journalisé ; une opposition de la
    personne (fiche, STOP) ne se retire pas ici : 409. {retire: bool}."""
    _require_localhost(request)
    ident = _corps(body).get("identifiant")
    if O.normaliser(ident) is None:
        raise HTTPException(422, "identifiant illisible : une adresse e-mail, un numéro ou un profil est attendu")
    try:
        r = O.retirer([ident], "saisie_erronee")
    except O.RegistreIndisponible as e:
        raise HTTPException(503, str(e)) from None
    if r["refuse"] and not r["retire"]:
        raise HTTPException(409, "cette personne s'est opposée elle-même : seul son réabonnement la retire du registre")
    return {"retire": r["retire"] > 0}


@router.get("/recherche")
async def get_recherche(request: Request):
    """t354 : le fournisseur de recherche web choisi, et pour chacun : configuré (clé posée) et prix. Jamais une clé."""
    _require_localhost(request)
    from app.services import recherche_web as RW
    return RW.etat()


@router.post("/recherche/fournisseur")
async def post_recherche_fournisseur(request: Request, body: dict):
    _require_localhost(request)
    from app.services import recherche_web as RW
    try:
        RW.choisir(_corps(body).get("fournisseur"))
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    return RW.etat()


@router.post("/recherche/cle")
async def post_recherche_cle(request: Request, body: dict):
    """t354 : pose la clé d'un fournisseur de recherche (Tavily, Exa, Serper) là où vivent les clés (coffre ouvert, sinon
    .env ; coffre fermé : en mémoire), appliquée à chaud. La clé Anthropic se règle dans Réglages › Clés d'API."""
    _require_localhost(request)
    from app.services import coffre as CF, recherche_web as RW
    b = _corps(body)
    f, v = b.get("fournisseur"), str(b.get("valeur") or "").strip()
    if f not in RW.FOURNISSEURS or f == "anthropic":
        raise HTTPException(422, "fournisseur à clé inconnu : tavily, exa ou serper")
    if not v or len(v) > 300 or any(ch.isspace() for ch in v):
        raise HTTPException(422, "clé illisible : une seule chaîne, sans espace")
    ou = CF.enregistrer_cle(RW.CLES[f], v)
    return dict(RW.etat(), ou=ou)


@router.get("/{eid}")
async def get_prospects(request: Request, eid: str, statut: str | None = None):
    def geste():
        tous = P.lister(eid)
        compte = {}
        for f in tous:
            compte[f["statut"]] = compte.get(f["statut"], 0) + 1
        espaces = _es.lire()["espaces"]          # t353 suite (M8) : l'écran nomme l'espace démo, jamais son id brut
        return {"prospects": [f for f in tous if not statut or f["statut"] == statut],
                "compte_par_statut": compte, "oppositions": P._reg(O.compte),
                "registre_mis_de_cote": O.mis_de_cote(),
                "espaces_demo": {f["espace_demo"]: espaces[f["espace_demo"]].get("nom") or f["espace_demo"]
                                 for f in tous if f["espace_demo"] and isinstance(espaces.get(f["espace_demo"]), dict)}}
    return _faire(request, geste)


@router.post("/{eid}", status_code=201)
async def post_prospect(request: Request, eid: str, body: dict):
    return _faire(request, lambda: P.creer(eid, _corps(body)))


def _seq(request: Request, geste):
    """t355 : les gestes sur les séquences ; refus {code, message} comme les fiches."""
    _require_localhost(request)
    try:
        return geste()
    except SQ.RefusSequence as e:
        raise HTTPException(e.statut, {"code": e.code, "message": e.message}) from None


@router.get("/{eid}/sequences")
async def get_sequences(request: Request, eid: str, pid: str | None = None):
    return _seq(request, lambda: {"sequences": SQ.lister(eid, pid)})


@router.post("/{eid}/sequences/{sid}/valider")
async def post_sequence_valider(request: Request, eid: str, sid: str):
    return _seq(request, lambda: SQ.valider(eid, sid, "utilisateur"))


@router.post("/{eid}/sequences/{sid}/planifier")
async def post_sequence_planifier(request: Request, eid: str, sid: str, body: dict | None = None):
    return _seq(request, lambda: SQ.planifier(eid, sid, _corps(body).get("debut"), "utilisateur"))


@router.post("/{eid}/sequences/{sid}/annuler")
async def post_sequence_annuler(request: Request, eid: str, sid: str):
    return _seq(request, lambda: SQ.annuler(eid, sid, "utilisateur"))


@router.post("/{eid}/sequences/{sid}/etapes/{rang}/envoye")
async def post_sequence_envoye(request: Request, eid: str, sid: str, rang: int):
    return _seq(request, lambda: SQ.marquer_envoye(eid, sid, rang, "utilisateur"))


@router.get("/{eid}/{pid}")
async def get_prospect(request: Request, eid: str, pid: str):
    return _faire(request, lambda: P.lire(eid, pid))


@router.patch("/{eid}/{pid}")
async def patch_prospect(request: Request, eid: str, pid: str, body: dict):
    return _faire(request, lambda: P.modifier(eid, pid, _corps(body)))


@router.delete("/{eid}/{pid}")
async def delete_prospect(request: Request, eid: str, pid: str, inscrire_opposition: int = 1):
    _faire(request, lambda: P.effacer(eid, pid, inscrire_opposition=bool(inscrire_opposition)))
    return {"efface": pid}


@router.post("/{eid}/{pid}/statut")
async def post_statut(request: Request, eid: str, pid: str, body: dict):
    b = _corps(body)
    return _faire(request, lambda: P.changer_statut(eid, pid, b.get("statut"), str(b.get("detail") or "")))


@router.post("/{eid}/{pid}/qualifier")
async def post_qualifier(request: Request, eid: str, pid: str, body: dict):
    """t354 : {offre, ajustement?, raison?} -> la fiche, score recalculé (barème + ajustement borné)."""
    b = _corps(body)
    return _faire(request, lambda: P.qualifier(eid, pid, b.get("offre"), b.get("ajustement", 0) if b.get("ajustement") is not None else 0,
                                               str(b.get("raison") or "")))


@router.post("/{eid}/{pid}/consentements")
async def post_consentement(request: Request, eid: str, pid: str, body: dict):
    b = _corps(body)
    return _faire(request, lambda: P.ajouter_consentement(eid, pid, b.get("canal"), b.get("base_legale"), b.get("moyen"),
                                                          b.get("date")))


@router.post("/{eid}/{pid}/consentements/revoquer")
async def post_revoquer(request: Request, eid: str, pid: str, body: dict):
    return _faire(request, lambda: P.revoquer_consentement(eid, pid, _corps(body).get("canal")))


@router.post("/{eid}/{pid}/contacts")
async def post_contact(request: Request, eid: str, pid: str, body: dict):
    b = _corps(body)
    return _faire(request, lambda: P.noter_contact(eid, pid, b.get("sens"), str(b.get("detail") or "")))


@router.post("/{eid}/{pid}/opposer")
async def post_opposer(request: Request, eid: str, pid: str):
    return _faire(request, lambda: P.opposer(eid, pid))


@router.get("/{eid}/{pid}/export")
async def get_export(request: Request, eid: str, pid: str):
    doc = _faire(request, lambda: P.exporter(eid, pid))
    return Response(json.dumps(doc, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="prospect-{doc["id"]}.json"'})
