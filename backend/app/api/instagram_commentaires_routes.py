# -*- coding: utf-8 -*-
"""t501 (lot G11, 26/11/2026) — /api/instagram/commentaires : commentaires au mot-clé et brouillons de réponse
PUBLIQUE (service `services/instagram_commentaires.py`). Boucle locale seulement ; les deux routes qui dépensent
(Claude, l'envoi qui consomme le quota de l'application Meta) passent aussi `_require_local_depense`.

- `GET  /etat`                                       {scope, disponible, reponse_privee: false, reponses_jour, plafond_jour}
- `GET  /file?espace_id=`                            les posts Instagram publiés, mot-clé, compteur, brouillons (lecture)
- `GET  /posts/{post_id}`                            l'état d'un post (lecture locale)
- `PUT  /posts/{post_id}/mot-cle`                    {mot_cle} -> brief.mot_cle
- `POST /posts/{post_id}/relever`                    lit les commentaires (Meta, lecture) et compte ceux au mot-clé
- `POST /posts/{post_id}/brouillons/gabarit`         {langue?, gabarit?} : brouillons GRATUITS
- `GET  /posts/{post_id}/brouillons/devis?langue=`   devis GRATUIT de la rédaction par Claude
- `POST /posts/{post_id}/brouillons/claude`          {max_usd, langue?} : PAYANTE (Claude, catégorie « campagnes »)
- `POST /posts/{post_id}/brouillons/{bid}/valider`   {texte} : la porte humaine, UN brouillon
- `POST /posts/{post_id}/brouillons/{bid}/rejeter`
- `POST /posts/{post_id}/brouillons/{bid}/envoyer`   {texte, confirme: true} : UNE réponse publique, brouillon validé
Aucune route de message privé, aucune route d'envoi en masse (décision du 26/11). Refus : {code, message} traduit.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import i18n as _i
from app.services import instagram_commentaires as IC

router = APIRouter()


class CorpsMot(BaseModel):
    mot_cle: str | None = None


class CorpsGabarit(BaseModel):
    langue: str | None = None
    gabarit: str | None = None


class CorpsClaude(BaseModel):
    max_usd: float | None = None
    langue: str | None = None


class CorpsTexte(BaseModel):
    texte: str | None = None


class CorpsEnvoi(BaseModel):
    texte: str | None = None
    confirme: bool | None = None


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _langue(request: Request, v: str | None) -> str:
    if v in ("fr", "en"):
        return v
    return "en" if _i.langue_requete(request) == "en" else "fr"


def _http(e: IC.RefusCommentaire, request: Request) -> HTTPException:
    return HTTPException(e.statut, {"code": e.code, "message": _i.texte(e, _i.langue_requete(request)),
                                    **({"usd": e.message.vars.get("usd")} if e.code == "cout" else {})})


@router.get("/etat")
async def etat(request: Request):
    _local(request)
    return IC.etat()


@router.get("/file")
async def file(request: Request, espace_id: str | None = None):
    _local(request)
    return await IC.file((espace_id or "").strip()[:40] or None)


@router.get("/posts/{post_id}")
async def lire_post(request: Request, post_id: str):
    _local(request)
    try:
        return IC.vue(IC.lire(post_id))
    except IC.RefusCommentaire as e:
        raise _http(e, request) from None


@router.put("/posts/{post_id}/mot-cle")
async def poser_mot_cle(request: Request, post_id: str, corps: CorpsMot):
    _local(request)
    try:
        return await IC.poser_mot_cle(post_id, corps.mot_cle)
    except IC.RefusCommentaire as e:
        raise _http(e, request) from None


@router.post("/posts/{post_id}/relever")
async def relever(request: Request, post_id: str):
    _local(request)
    try:
        return await IC.relever(post_id)
    except IC.RefusCommentaire as e:
        raise _http(e, request) from None


@router.post("/posts/{post_id}/brouillons/gabarit")
async def brouillons_gabarit(request: Request, post_id: str, corps: CorpsGabarit | None = None):
    _local(request)
    try:
        return await IC.rediger_gabarit(post_id, _langue(request, corps.langue if corps else None),
                                        corps.gabarit if corps else None)
    except IC.RefusCommentaire as e:
        raise _http(e, request) from None


@router.get("/posts/{post_id}/brouillons/devis")
async def brouillons_devis(request: Request, post_id: str, langue: str | None = None):
    _local(request)
    try:
        return await IC.devis_claude(post_id, _langue(request, langue))
    except IC.RefusCommentaire as e:
        raise _http(e, request) from None


@router.post("/posts/{post_id}/brouillons/claude")
async def brouillons_claude(request: Request, post_id: str, corps: CorpsClaude):
    """PAYANTE : la garde (accord, puis plafonds par `tirer_garde`) vit dans IC.rediger_claude."""
    _local(request)
    _depense_locale(request)
    try:
        return await IC.rediger_claude(post_id, max_usd=corps.max_usd, langue=_langue(request, corps.langue))
    except IC.RefusCommentaire as e:
        raise _http(e, request) from None


@router.post("/posts/{post_id}/brouillons/{bid}/valider")
async def valider(request: Request, post_id: str, bid: str, corps: CorpsTexte):
    _local(request)
    try:
        return await IC.valider(post_id, bid, corps.texte)
    except IC.RefusCommentaire as e:
        raise _http(e, request) from None


@router.post("/posts/{post_id}/brouillons/{bid}/rejeter")
async def rejeter(request: Request, post_id: str, bid: str):
    _local(request)
    try:
        return IC.rejeter(post_id, bid)
    except IC.RefusCommentaire as e:
        raise _http(e, request) from None


@router.post("/posts/{post_id}/brouillons/{bid}/envoyer")
async def envoyer(request: Request, post_id: str, bid: str, corps: CorpsEnvoi):
    """UNE réponse publique : la garde (validation, confirmation, texte validé, garde-fou du jour) vit dans IC.envoyer."""
    _local(request)
    _depense_locale(request)
    try:
        return await IC.envoyer(post_id, bid, texte=corps.texte, confirme=corps.confirme)
    except IC.RefusCommentaire as e:
        raise _http(e, request) from None
