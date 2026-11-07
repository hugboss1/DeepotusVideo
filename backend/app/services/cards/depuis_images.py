# -*- coding: utf-8 -*-
"""Card Forge — t421 : créer un deck « carte pleine » depuis des images.

`POST /api/cards/decks/depuis-images` : N images de la Bibliothèque deviennent
N cartes d'un deck NEUF, sans cadre ni texte (le visuel EST la carte),
rectangulaire ou hexagonal. Les images ne sont jamais ouvertes en écriture ni
copiées : le deck ne garde que leurs NOMS, dans la colonne `art` (et `dos`).

Le deck est ensemencé comme `models.instancier` : `core.create_deck` puis
`core.patch_deck` — le même chemin que l'autosave de l'écran. Tout est
VALIDÉ avant `create_deck` : un refus ne laisse aucun deck derrière lui.

Ce routeur est inclus AVANT `core` (cf. `__init__`) : `/decks/depuis-images`
doit être apparié avant le joker `/{did}` de core.

Aucune dépense IA, aucune écriture dans `images/`.
"""
from __future__ import annotations

import asyncio
import os
import re

from fastapi import APIRouter, HTTPException
from loguru import logger

from . import core
from .contract import FORMATS

__all__ = ["router"]

router = APIRouter()

# Même plafond que le traitement par lots de la Bibliothèque.
IMAGES_MAX = 500

# Même motif que le Photolab (`_NOM_IMAGE`, photolab_routes.py) : lettres
# accentuées admises (forme composée ou décomposée), jamais de séparateur de
# dossier, de « : » ni de retour à la ligne. Recopié, pas importé : `app.api`
# importe les services, l'inverse ferait un cycle.
_NOM_IMAGE = re.compile(
    r"[\w\u0300-\u036f]([\w\u0300-\u036f. -]{0,179}[\w\u0300-\u036f-])?")

# Le deck « carte pleine » : aucun habillage, aucune zone de texte.
_CADRE_NU = {"family": "none", "gem": False, "banner": False,
             "corner": "none", "line_mm": 0, "double": False, "metal": False}


def _images_dir():
    from app.config import settings
    return settings.images_path


def _nom_valide(nom, champ: str) -> str:
    if not isinstance(nom, str) or not _NOM_IMAGE.fullmatch(nom):
        raise HTTPException(400, f"{champ} : nom d'image refusé : {nom!r}")
    return nom


def _verifie_presente(nom: str) -> None:
    """404 nommant le fichier ; 400 s'il sort de la Bibliothèque (lien)."""
    racine = _images_dir().resolve()
    src = (_images_dir() / nom).resolve()
    if racine not in src.parents:
        raise HTTPException(400, f"image hors de la Bibliothèque : {nom}")
    if not src.is_file():
        raise HTTPException(404, f"image introuvable dans la Bibliothèque : {nom}")


def _titre(nom: str) -> str:
    """Le nom de la carte : le fichier sans extension, `_` -> espace."""
    return os.path.splitext(nom)[0].replace("_", " ").strip() or nom


def preparer(body) -> dict:
    """Valide TOUT le corps et rend `{name, format, rows}`. Lève HTTPException.
    Aucun effet de bord : appelée avant `create_deck`."""
    if not isinstance(body, dict):
        raise HTTPException(400, "Corps JSON attendu")
    images = body.get("images")
    if not isinstance(images, list) or not images:
        raise HTTPException(400, "images : une liste non vide de noms attendue")
    if len(images) > IMAGES_MAX:
        raise HTTPException(
            400, f"images : {IMAGES_MAX} au plus ({len(images)} reçues)")
    fmt_in = body.get("format")
    if isinstance(fmt_in, str):
        fmt_in = {"fmt": fmt_in}
    if not isinstance(fmt_in, dict):
        raise HTTPException(400, "format : un objet {fmt, …} attendu")
    fmt_id = str(fmt_in.get("fmt") or "").strip().lower()
    if fmt_id not in FORMATS:
        raise HTTPException(400, f"format inconnu : {fmt_id!r}")
    fond_perdu = body.get("fond_perdu", True)
    if not isinstance(fond_perdu, bool):
        raise HTTPException(400, "fond_perdu : booléen attendu")
    versos = body.get("versos")
    commun = body.get("verso_commun")
    if versos is not None and commun is not None:
        raise HTTPException(400, "versos et verso_commun s'excluent")
    if versos is not None:
        if not isinstance(versos, list) or len(versos) != len(images):
            raise HTTPException(
                400, "versos : une liste de la longueur de images attendue")
    noms = [_nom_valide(n, "images") for n in images]
    if commun is not None:
        _nom_valide(commun, "verso_commun")
    dos = ([v if v not in (None, "") else "" for v in versos]
           if versos is not None else [commun or ""] * len(noms))
    for v in dos:
        if v:
            _nom_valide(v, "versos")
    for n in dict.fromkeys(noms + [v for v in dos if v]):
        _verifie_presente(n)
    fmt = dict(fmt_in)
    fmt["fmt"] = fmt_id
    if fond_perdu:
        fmt.pop("bleed_mm", None)       # le fond perdu natif du format
    else:
        fmt["bleed_mm"] = 0             # `safe_mm` reste celui du corps / natif
    return {"name": core.clean_name(body.get("name"), "Mes images"),
            "format": fmt,
            "rows": [[_titre(n), n, v] for n, v in zip(noms, dos)]}


def creer(prep: dict) -> dict:
    """Crée le deck et l'ensemence par `core.patch_deck`."""
    doc = core.create_deck(prep["name"])
    out = core.patch_deck(doc["id"], {
        "format": prep["format"],
        "frame": dict(_CADRE_NU),
        "type": {"slots": [], "seeded": True, "sel": ""},
        "face": {"seeded": True, "fit": "cover", "src": None,
                 "default_art": None},
        "data": {"columns": ["nom", "art", "dos"], "rows": prep["rows"],
                 "map": {"art": "art", "dos": "back"}},
    })
    if out is None:
        raise OSError("deck disparu après sa création")
    return out


@router.post("/decks/depuis-images")
async def post_depuis_images(body: dict | None = None):
    prep = await asyncio.to_thread(preparer, body)
    try:
        doc = await asyncio.to_thread(creer, prep)
    except OSError as e:
        logger.exception("cards: création depuis images impossible")
        raise HTTPException(500, "Création du deck impossible : écriture "
                                 f"refusée ({e.strerror or 'E/S'})")
    return {"deck": doc}
