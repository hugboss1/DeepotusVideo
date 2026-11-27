# -*- coding: utf-8 -*-
"""t498 (lot G8, 26/11/2026) — /api/recyclage : recycler un GAGNANT (carrousel, accroches, fil X, branche).

Boucle locale SEULEMENT (`routes._require_localhost`) ; la route payante a aussi `routes._require_local_depense`.
- `GET  /{post_id}/proposition`   `?gabarit=&langue=` : la proposition et ses cartes de devis (gratuit).
- `POST /{post_id}/redaction`     {element, max_usd, langue?, nouvelle?} : PAYANTE (Claude, garde « campagnes »).
- `POST /{post_id}/brouillons`    {elements?, gabarit?} : les brouillons au Planificateur (jamais en mode automatique).
Codes : 400 élément ou accord fautif, 404 post inconnu, 409 {message, code, …} (`sous_seuil` + seuil et mesure,
`cout` + usd, `en_cours`, `a_rediger`, `interdits`, `sans_gabarit`, `sans_plans`, `espace`), 402 (plafond),
502/504 (appel peut-être facturé), 503 (Claude non configuré). Messages fixes : L10.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from app.services import recyclage as RC

router = APIRouter()

MAX_CORPS = 16 * 1024
CODES_400 = ("element",)


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _langue(request: Request, v=None) -> str:
    if v in ("fr", "en"):
        return v
    from app.i18n import erreurs as _ERR
    return "en" if _ERR.langue(request) == "en" else "fr"


async def _corps(request: Request) -> dict:
    brut = b""
    async for m in request.stream():
        brut += m
        if len(brut) > MAX_CORPS:
            raise HTTPException(413, "Demande trop lourde.")
    import json
    try:
        c = json.loads(brut or b"null")
    except ValueError:
        raise HTTPException(400, "Corps JSON attendu.") from None
    return c if isinstance(c, dict) else {}


def _http(e: Exception) -> HTTPException:
    from app.services import inspiration as I
    if isinstance(e, HTTPException):
        return e
    if isinstance(e, RC.Inconnu):
        return HTTPException(404, RC.M_INCONNU)
    if isinstance(e, RC.CoutChange):
        return HTTPException(409, {"message": str(e), "code": "cout", "usd": e.usd})
    if isinstance(e, RC.EnCours):
        return HTTPException(409, {"message": str(e), "code": "en_cours"})
    if isinstance(e, RC.Refus):
        d = {"message": str(e), "code": e.code, **e.details}
        return HTTPException(400 if e.code in CODES_400 else 409, d)
    if isinstance(e, RC.AppelEchoue):
        return HTTPException(e.statut, str(e))
    if isinstance(e, ValueError):
        return HTTPException(400, str(e))
    if isinstance(e, RuntimeError):
        return HTTPException(503 if str(e) in I.RAISONS.values() else 502, str(e))
    raise e


@router.get("/{post_id}/proposition", dependencies=[Depends(_local)])
async def proposition(post_id: str, request: Request, gabarit: str = "", langue: str = ""):
    try:
        return await RC.proposer_recyclage(post_id, _langue(request, langue), gabarit.strip()[:120] or None)
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None


@router.post("/{post_id}/redaction", dependencies=[Depends(_local), Depends(_depense_locale)])
async def redaction(post_id: str, request: Request):
    c = await _corps(request)
    try:
        return await RC.rediger(post_id, c.get("element"), max_usd=c.get("max_usd"), langue=_langue(request, c.get("langue")),
                                nouvelle=c.get("nouvelle") is True)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"recyclage : rédaction refusée ou en échec ({type(e).__name__})")
        raise _http(e) from None


@router.post("/{post_id}/brouillons", dependencies=[Depends(_local)])
async def brouillons(post_id: str, request: Request):
    c = await _corps(request)
    g = c.get("gabarit")
    try:
        return await RC.creer_brouillons(post_id, c.get("elements"), gabarit_id=g.strip()[:120] if isinstance(g, str) and g.strip() else None)
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
