# -*- coding: utf-8 -*-
"""Card Forge — pièce 11 « Édition » (tâche #84, plan-cartes T5, 04/10/2026).

CE QUI SE LIVRE AUTOUR DE LA CARTE : la table virtuelle (Tabletop Simulator,
Tabletopia) ; plus tard le livret de règles, le mockup, la fiche produit.

Elle ne dessine RIEN : aucun z ne lui est alloué (lint, Z_TABLE). Comme P7,
elle ASSEMBLE des cartes rendues par `CF.renderCard` et téléversées — le
navigateur voit et manipule, Python écrit. Règle 8 : elle n'importe le routeur
d'aucune voisine ; ce qu'il lui faut d'une autre pièce, elle le RECOPIE.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from loguru import logger

from . import edition_vtt as VTT
from .contract import deck_dir, is_valid_did

router = APIRouter()

# Les cibles, dans l'ordre du panneau. Chacune dit ce qu'elle SAIT — relu sur
# la documentation de l'éditeur le 04/10/2026 —, pas ce qu'on aimerait.
CIBLES = [
    {"id": "tts", "label": "Tabletop Simulator — planches + objet sauvegardé",
     "livraison": "zip",
     "verifie": "04/10/2026 — kb.tabletopsimulator.com (custom-deck, asset-creation, save-file-format)",
     "note": "Planches de 10 x 7 cartes au plus (la grille est un réglage du "
             "Custom Deck, sans maximum publié), 4096 px de large au plus, PNG "
             "ou JPG en RVB, et un objet JSON (CustomDeck : FaceURL, BackURL, "
             "NumWidth, NumHeight) à poser dans Saved Objects."},
    {"id": "tabletopia", "label": "Tabletopia — une image par face",
     "livraison": "zip",
     "verifie": "04/10/2026 — help.tabletopia.com (how-to-prepare-graphics)",
     "note": "Recto et verso dans des FICHIERS SÉPARÉS, tous les composants "
             "d'un même type à la même taille, 2000 x 2000 px au plus par "
             "objet, 1 à 2 Mo visés (3 à 10 Mo au maximum). Aucune grille de "
             "collage : on ne lui en envoie pas."},
]


def _deck(did: str) -> dict:
    """Deck existant, ou l'erreur qui va bien (400 / 404) — jamais un 500.
    Import PARESSEUX du magasin, comme P7 : aucun cycle à l'import."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    from . import core as deck_store
    doc = deck_store.read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    return doc


@router.get("/cibles")
async def get_cibles(did: str):
    """Le catalogue des tables virtuelles servies, avec ce que chacune exige."""
    _deck(did)
    return {"cibles": CIBLES}


def _json_form(spec: str) -> dict:
    try:
        v = json.loads(spec or "{}")
    except Exception:
        raise HTTPException(400, "Le champ `spec` n'est pas du JSON")
    if not isinstance(v, dict):
        raise HTTPException(400, "Le champ `spec` doit être un objet JSON")
    return v


def _geom(doc: dict):
    from . import core as deck_store
    return deck_store.geom_of(doc)


def _dossier_tts(did: str) -> Path:
    return deck_dir(did) / "edition" / "tts"


@router.post("/tts")
async def post_tts(did: str, spec: str = Form("{}"),
                   fronts: list[UploadFile] = File(default=[]),
                   backs: list[UploadFile] = File(default=[])):
    """TABLETOP SIMULATOR (tâche #84 PR B) : les planches 10 x 7 à la coupe,
    l'objet sauvegardé qui pointe vers elles (chemins locaux), un ZIP de tout.
    Les fichiers restent dans le dossier du jeu : l'objet les retrouve."""
    doc = _deck(did)
    body = _json_form(spec)
    if not fronts:
        raise HTTPException(400, "Aucune carte reçue : le navigateur doit rendre les cartes avant l'export")
    noms = body.get("noms") if isinstance(body.get("noms"), list) else []
    rectos = [await f.read() for f in fronts]
    versos = [await f.read() for f in (backs or [])]
    g = _geom(doc)

    def work():
        return VTT.construire(str(doc.get("name") or "Jeu"), g, rectos, versos, noms, _dossier_tts(did))
    try:
        out, res = await asyncio.to_thread(work)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("cards/edition: export TTS impossible")
        raise HTTPException(500, f"Export Tabletop Simulator impossible: {e}")
    return Response(content=out, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="{res["jeu"]}_tts.zip"',
        "X-CF-Cartes": str(res["cartes"]), "X-CF-Planches": str(res["planches"]),
        "X-CF-Cellule": "%dx%d" % tuple(res["cellule"]),
        "X-CF-Planche-Px": "%dx%d" % tuple(res["planche_px"]),
        "X-CF-Unique-Back": "1" if res["unique_back"] else "0",
    })


@router.post("/tabletopia")
async def post_tabletopia(did: str, spec: str = Form("{}"),
                          fronts: list[UploadFile] = File(default=[]),
                          backs: list[UploadFile] = File(default=[])):
    """TABLETOPIA (tâche #84 PR C) : un fichier par face, à la coupe, 2000 px au
    plus sur le côté long, et le manifeste — en ZIP. Rien n'est écrit sur le PC
    hors du téléchargement : Tabletopia se charge par son éditeur en ligne."""
    doc = _deck(did)
    body = _json_form(spec)
    if not fronts:
        raise HTTPException(400, "Aucune carte reçue : le navigateur doit rendre les cartes avant l'export")
    noms = body.get("noms") if isinstance(body.get("noms"), list) else []
    rectos = [await f.read() for f in fronts]
    versos = [await f.read() for f in (backs or [])]
    g = _geom(doc)

    def work():
        return VTT.tabletopia(str(doc.get("name") or "Jeu"), g, rectos, versos, noms)
    try:
        out, res = await asyncio.to_thread(work)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("cards/edition: export Tabletopia impossible")
        raise HTTPException(500, f"Export Tabletopia impossible: {e}")
    return Response(content=out, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="{res["jeu"]}_tabletopia.zip"',
        "X-CF-Cartes": str(res["cartes"]), "X-CF-Fichiers": str(res["fichiers"]),
        "X-CF-Px": "%dx%d" % tuple(res["px"]),
    })


def _saved_objects() -> Path:
    r"""Le dossier « Saved Objects » de Tabletop Simulator : Documents\My Games\
    Tabletop Simulator\Saves\Saved Objects. « Documents » est lu par le
    dossier connu de Windows (il peut être redirigé, OneDrive par exemple).
    DEEPOTUS_TTS_DIR le remplace (bancs)."""
    env = os.environ.get("DEEPOTUS_TTS_DIR", "").strip()
    if env:
        return Path(env)
    docs = None
    try:
        import ctypes
        from ctypes import wintypes
        import uuid
        guid = uuid.UUID("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}")       # FOLDERID_Documents

        class GUID(ctypes.Structure):
            _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD), ("d3", wintypes.WORD), ("d4", ctypes.c_ubyte * 8)]
        g = GUID(guid.fields[0], guid.fields[1], guid.fields[2],
                 (ctypes.c_ubyte * 8)(*guid.bytes[8:]))
        p = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(p)) == 0:
            docs = Path(p.value)
            ctypes.windll.ole32.CoTaskMemFree(p)
    except Exception:
        docs = None
    docs = docs or Path.home() / "Documents"
    return docs / "My Games" / "Tabletop Simulator" / "Saves" / "Saved Objects"


@router.post("/tts/poser")
async def post_tts_poser(did: str):
    """Copie le dernier objet exporté (JSON + vignette) dans les Saved Objects
    de Tabletop Simulator, sous-dossier « Deepotus » : il apparaît dans le jeu,
    Objects > Saved Objects. Écrit HORS des données de l'appli — décision de
    l'utilisateur (04/10), et seulement quand on le demande."""
    doc = _deck(did)
    s = VTT.slug(str(doc.get("name") or "Jeu"))
    src = _dossier_tts(did)
    js, th = src / f"{s}.json", src / f"{s}.png"
    if not js.is_file():
        raise HTTPException(409, "Exportez d'abord pour Tabletop Simulator : aucun objet à poser.")
    cible = _saved_objects()
    racine_tts = cible.parent.parent                 # « My Games/Tabletop Simulator »
    if not racine_tts.is_dir():
        raise HTTPException(409, f"Tabletop Simulator introuvable sur ce PC ({racine_tts}) : lancez-le une "
                                 "fois, ou déposez le JSON du ZIP dans ses Saved Objects.")
    dest = cible / "Deepotus"
    try:
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(js, dest / js.name)
        if th.is_file():
            shutil.copyfile(th, dest / th.name)
    except OSError as e:
        raise HTTPException(500, f"Copie dans Tabletop Simulator impossible : {e}")
    return {"chemin": str(dest / js.name), "dossier": str(dest)}
