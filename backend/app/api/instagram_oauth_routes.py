# -*- coding: utf-8 -*-
"""t493 (lot G3, 26/11/2026) — /api/oauth/instagram : « Relier par Instagram » (Instagram Login), service
`services/instagram_oauth.py`. Boucle locale seulement (comme les Réglages) ; inerte sans IG_APP_ID / IG_APP_SECRET.

- `GET  /etat`      {configure, redirect_uri, scopes, coffre_ouvert, choix, comptes} — jamais un secret
- `POST /demarrer`  {compte?} -> {url} : l'adresse d'autorisation Instagram (state à usage unique) ; rien ne part
- `GET  /callback`  ?code&state | ?error… : le retour direct (boucle locale acceptée par Meta, ou VPS) -> page HTML
- `POST /retour`    {adresse} : l'adresse collée où Instagram a renvoyé le navigateur (https://localhost/…)
Les refus sont des `RefusIG` (messages ig.oauth.*), rendus dans la langue de la requête.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import i18n as _i
from app.services import instagram_oauth as IO

router = APIRouter()


class CorpsDemarrer(BaseModel):
    compte: str | None = None


class CorpsRetour(BaseModel):
    adresse: str = ""


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _http(e: IO.RefusIG, request: Request) -> HTTPException:
    return HTTPException(e.statut, _i.texte(e, _i.langue_requete(request)))


@router.get("/etat")
async def etat(request: Request):
    _local(request)
    return IO.etat()


@router.post("/demarrer")
async def demarrer(request: Request, corps: CorpsDemarrer | None = None):
    _local(request)
    try:
        return {"url": IO.demarrer((corps.compte if corps else None) or None)}
    except IO.RefusIG as e:
        raise _http(e, request) from None


@router.get("/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = "", error_reason: str = ""):
    _local(request)
    from app.api.routes import _oauth_page
    lang = _i.langue_requete(request)
    try:
        res = await IO.terminer(code, state, error_reason or error)
    except IO.RefusIG as e:
        return _oauth_page(_i.msg("ig.oauth.titre_refus", lang), _i.texte(e, lang), 400 if e.statut < 500 else 502)
    return _oauth_page(_i.msg("ig.oauth.titre_relie", lang),
                       _i.msg("ig.oauth.relie", lang, nom=res["username"], date=res["expire"]))


@router.post("/retour")
async def retour(request: Request, corps: CorpsRetour):
    _local(request)
    code, state, erreur = IO.lire_retour(corps.adresse)
    try:
        if not erreur and not code:
            raise IO.RefusIG(400, "ig.oauth.code_absent")
        res = await IO.terminer(code, state, erreur)
    except IO.RefusIG as e:
        raise _http(e, request) from None
    return dict(res, message=_i.msg("ig.oauth.relie", _i.langue_requete(request), nom=res["username"], date=res["expire"]))
