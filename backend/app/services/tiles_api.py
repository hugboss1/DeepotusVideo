# -*- coding: utf-8 -*-
"""Le routeur des tuiles — UNE porte pour toutes les routes de `/api/tiles`
(plan 2026-09-03-plan-tuiles, tâche t113). Monté par `main.py` sous
`/api/tiles` (bloc `__DZ_TILES_ROUTER_*`, patron des autres routeurs).

Tout est LOCAL (PIL pur, aucun fournisseur payant). Le calcul — assemblage,
atlas, et le raccord mesuré sur TOUTES les paires légales — part dans un
exécuteur : à 512 px et 5 variantes il pèse plusieurs secondes, et la boucle
d'évènements de l'application ne doit pas s'arrêter pour lui.
"""
from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.services import library_index as LI
from app.services import tile_ops as TO
from app.services import tile_store as TS

router = APIRouter()


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _charger_matiere(spec, quoi: str) -> Image.Image:
    """Une matière = une image de la Bibliothèque, désignée par son NOM (un
    chemin est refusé). La T10 du plan ajoutera la clé `materiau`."""
    if not isinstance(spec, dict):
        raise HTTPException(400, f"{quoi}: objet attendu")
    nom = str(spec.get("image") or "").strip()
    if not nom:
        raise HTTPException(400, f"{quoi}: cle 'image' attendue")
    p = settings.images_path / nom
    if p.name != nom or "\\" in nom or not p.is_file():
        raise HTTPException(400, f"{quoi}: image introuvable: {nom}")
    try:
        with Image.open(p) as im:
            return im.convert("RGB").copy()
    except (UnidentifiedImageError, OSError) as e:
        raise HTTPException(400, f"{quoi}: image illisible: {nom} ({e})")


def _fabriquer(a, b, jeu_nom, cote, variantes, graine):
    """Bloquant : le jeu, son atlas, et le pire raccord des paires légales."""
    from app.services import tile_metrics as TM
    jeu = TO.assembler_jeu(a, b, jeu_nom, cote, variantes, graine)
    img, colonnes, rangees = TO.atlas(jeu)
    return jeu, img, colonnes, rangees, TM.raccord_jeu(jeu)


@router.post("/jeu")
async def creer_jeu(body: dict):
    """Fabrique un jeu de tuiles depuis DEUX matières et le range.
    Body: {matiere_a:{image}, matiere_b:{image}, jeu, cote, variantes, graine, nom}.
    → la méta du jeu, dont `raccord` = le PIRE raccord des paires légales."""
    body = body if isinstance(body, dict) else {}
    jeu_nom = str(body.get("jeu") or "blob47")
    if jeu_nom not in TO.JEUX:
        raise HTTPException(400, f"jeu inconnu: {jeu_nom} (attendu {', '.join(TO.JEUX)})")
    try:
        cote = int(body.get("cote") or 64)
        variantes = int(body.get("variantes") or 1)
        graine = int(body.get("graine") or 1)
    except (TypeError, ValueError):
        raise HTTPException(400, "cote, variantes et graine sont des entiers")
    if not 16 <= cote <= 512:
        raise HTTPException(400, "cote doit tenir entre 16 et 512")
    if not 1 <= variantes <= 5:
        raise HTTPException(400, "variantes doit tenir entre 1 et 5")
    a = _charger_matiere(body.get("matiere_a") or {}, "matiere_a")
    b = _charger_matiere(body.get("matiere_b") or {}, "matiere_b")

    jeu, img, colonnes, rangees, raccord = await asyncio.get_running_loop().run_in_executor(
        None, _fabriquer, a, b, jeu_nom, cote, variantes, graine)

    tid = TS.new_tid()
    d = TS.tileset_dir(tid, create=True)
    img.save(d / "atlas.png", format="PNG")
    meta = {"tid": tid, "nom": str(body.get("nom") or "jeu de tuiles")[:80],
            "jeu": jeu_nom, "cles": jeu["cles"], "cote": cote,
            "variantes": variantes, "graine": graine,
            "tuiles": len(jeu["tuiles"]), "vide": jeu["vide"],
            "colonnes": colonnes, "rangees": rangees,
            "source_a": {"image": (body.get("matiere_a") or {}).get("image")},
            "source_b": {"image": (body.get("matiere_b") or {}).get("image")},
            "raccord": raccord, "cree_le": _maintenant()}
    TS.write_meta(tid, meta)
    # LA PROVENANCE : l'atlas est COPIÉ dans la Bibliothèque sous `tile_<id>_atlas.png` (préfixe → source
    # « tuiles »), puis indexé. Indexer le seul NOM (comme le plan le dessinait) aurait posé dans l'index une
    # ligne vers un fichier qui n'existe pas dans le dossier des images.
    copie = settings.images_path / f"{tid}_atlas.png"
    try:
        shutil.copyfile(d / "atlas.png", copie)
        await LI.noter([copie.name], "tuiles")
    except Exception as e:  # noqa: BLE001 — la provenance n'empêche jamais le jeu
        logger.warning(f"tuiles : copie / index de l'atlas ignorés ({e})")
    logger.info(f"tuiles/jeu {jeu_nom} {len(jeu['tuiles'])} tuiles cote={cote} x{variantes} "
                f"raccord={raccord} -> {tid}")
    return meta


@router.get("")
async def lister():
    return {"tilesets": TS.list_tilesets()}


@router.get("/{tid}")
async def lire(tid: str):
    meta = TS.read_meta(tid)
    if meta is None:
        raise HTTPException(404, f"jeu de tuiles inconnu: {tid}")
    meta["tid"] = tid
    return meta


@router.get("/{tid}/fichier/{nom}")
async def fichier(tid: str, nom: str):
    try:
        p = TS.chemin_fichier(tid, nom)
    except ValueError as e:
        raise HTTPException(404, str(e))
    if not p.is_file():
        raise HTTPException(404, f"fichier absent: {nom}")
    return FileResponse(str(p))
