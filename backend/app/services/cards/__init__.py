# -*- coding: utf-8 -*-
"""Card Forge — le domaine « cartes », monté sous `/api/cards`.

CE FICHIER APPARTIENT À CORE et ne bouge plus : il assemble, il n'implémente
rien. Les neuf pièces remplissent leur propre `<id>.py` et n'en sortent pas.

Le domaine vit HORS de `app/api/routes.py` — ce fichier passe déjà 6 500
lignes, et huit builders qui l'éditent en parallèle, c'est huit conflits.
Chaque pièce a son fichier ; ici on ne fait que les brancher.

Assemblage (règle 8 de la spec) :

    /api/cards/models             CORE   (models.py) modèles d'usine + perso
    /api/cards/formats            CORE   (core.py)
    /api/cards/decks              CORE   création, instanciation, duplication
    /api/cards/{did}              CORE   document, autosave, suppression
    /api/cards/{did}/geom         CORE   géométrie
    /api/cards/{did}/face/…       P1     face.py
    /api/cards/{did}/frame/…      P2     frame.py
    /api/cards/{did}/type/…       P3     type.py
    /api/cards/{did}/data/…       P4     data.py
    /api/cards/{did}/solid/…      P5     solid.py
    /api/cards/{did}/texture/…    P6     texture.py
    /api/cards/{did}/print/…      P7     print.py
    /api/cards/{did}/gltf/…       P8     gltf.py
    /api/cards/{did}/forge3d/…    P9     forge3d.py

Chaque sous-module déclare `router = APIRouter()` avec des chemins RELATIFS
et n'importe le routeur d'aucun autre : le préfixe `{did}` est posé ici, une
seule fois. `core` est inclus EN PREMIER pour que `/formats` et `/decks`
soient appariés avant le joker `/{did}` — Starlette apparie dans l'ordre.

`type` et `print` sont des noms de fonctions natives Python : ils sont
importés sous alias pour ne pas les masquer dans ce module.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from . import core
from . import face, frame, data, solid, texture, gltf, forge3d
from . import models
from . import type as type_mod
from . import print as print_mod

__all__ = ["router"]

router = APIRouter()

# LES MODÈLES AVANT CORE. `/models` est UN SEGMENT : inclus après `core`, il
# tomberait dans le joker `/{did}` de core.py — Starlette apparie dans l'ordre
# de déclaration — et GET /api/cards/models répondrait « identifiant de deck
# invalide ». L'inverse est sans risque : `models.py` ne déclare que /models,
# il ne peut masquer ni /formats, ni /decks, ni un did.
router.include_router(models.router, tags=["cards:models"])

# CORE ensuite : /formats et /decks avant le joker /{did}.
router.include_router(core.router, tags=["cards"])

router.include_router(face.router, prefix="/{did}/face", tags=["cards:face"])
router.include_router(frame.router, prefix="/{did}/frame", tags=["cards:frame"])
router.include_router(type_mod.router, prefix="/{did}/type", tags=["cards:type"])
router.include_router(data.router, prefix="/{did}/data", tags=["cards:data"])
router.include_router(solid.router, prefix="/{did}/solid", tags=["cards:solid"])
router.include_router(texture.router, prefix="/{did}/texture",
                      tags=["cards:texture"])
router.include_router(print_mod.router, prefix="/{did}/print",
                      tags=["cards:print"])
router.include_router(gltf.router, prefix="/{did}/gltf", tags=["cards:gltf"])
router.include_router(forge3d.router, prefix="/{did}/forge3d",
                      tags=["cards:forge3d"])


# ── le filet, EN DERNIER ────────────────────────────────────────────────────
# Une route inconnue sous /api/cards ne doit JAMAIS retomber sur le catch-all
# de la SPA : celui-ci répond 200 + du HTML (piège n°7 de la spec), et un
# client hors CF le lit comme un succès. Mesuré : un `did` contenant des
# séparateurs percent-encodés (`/api/cards/..%2f..%2fetc/geom`) sortait du
# domaine avant d'atteindre le garde-fou 400 de `_deck_or_404` et rendait
# 200 text/html. Aucune traversée n'était possible (le double garde-fou de
# `deck_dir` n'était même pas sollicité), mais une API qui répond du HTML est
# un piège. Déclaré APRÈS les neuf sous-routeurs : Starlette apparie dans
# l'ordre, il ne peut donc rien masquer.
@router.api_route("/{rest:path}",
                  methods=["GET", "POST", "PATCH", "PUT", "DELETE", "HEAD"],
                  include_in_schema=False)
async def cards_not_found(rest: str):
    raise HTTPException(404, "Route inconnue dans le domaine /api/cards")
