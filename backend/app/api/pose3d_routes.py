# -*- coding: utf-8 -*-
"""t376 (29/10/2026) — /api/assets3d/pose : le choix Aucune / T-pose / A-pose de la génération 3D (pose3d).

- `GET  ""`         GRATUIT : l'état du choix pour l'écran {actif, sujet, texte, vision, mode, raison,
                    avertissement, vision_proposee} d'après ?engine, ?multiview, ?subject, ?image_filename.
- `GET  /devis`     GRATUIT : le devis d'une classification vision {usd, moteur, nom, disponible, raison}.
- `POST /classer`   {image_filename, confirme_cout: true, max_usd} : la classification vision PAYANTE, UNE fois par
                    image (déjà classée : rendue sans appel ni dépense). Sans `confirme_cout` : 409 {code:
                    "confirme_cout", devis} et rien n'est envoyé ; coût hors accord : 409 {message, usd} ; Claude
                    non configuré ou sans vision : 503 ; plafond « moteurs3d » : 402 (tirer_garde).
Toutes en boucle locale ; la route payante exige aussi la dépense locale (`_require_local_depense`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.services import pose3d as P

router = APIRouter()


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


@router.get("", dependencies=[Depends(_local)])
async def etat(engine: str = "tripo", multiview: bool = False, subject: str = "", image_filename: str = ""):
    return P.etat(engine, multiview, subject, image_filename)


@router.get("/devis", dependencies=[Depends(_local)])
async def devis():
    return P.devis()


@router.post("/classer", dependencies=[Depends(_local), Depends(_depense_locale)])
async def classer(body: dict):
    image = str((body or {}).get("image_filename") or "")
    if P.classe_vision(image) is None and (body or {}).get("confirme_cout") is not True:
        raise HTTPException(409, {"code": "confirme_cout", "devis": P.devis()})
    try:
        r = await P.classer_image(image, max_usd=(body or {}).get("max_usd"))
    except P.CoutChange as e:
        raise HTTPException(409, {"message": str(e), "usd": e.usd}) from None
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from None
    return {**r, "etat": P.etat(str(body.get("engine") or "tripo"), bool(body.get("multiview")),
                                str(body.get("subject") or ""), image)}
