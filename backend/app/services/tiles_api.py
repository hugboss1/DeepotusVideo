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


@router.post("/{tid}/export")
async def exporter(tid: str, body: dict):
    """Body: {format: 'tiled'|'ldtk'|'godot'} (t114, plan T3-T5). Écrit `tileset.tsx`, `projet.ldtk` ou
    `tileset.tres` dans le dossier du jeu, à côté de son `atlas.png`, et rend son nom — le fichier fait foi, et la
    route de fichier le sert (les trois noms sont dans la liste blanche de `tile_store`)."""
    from app.services import tile_export as TE
    meta = TS.read_meta(tid)
    if meta is None:
        raise HTTPException(404, f"jeu de tuiles inconnu: {tid}")
    fmt = str((body or {}).get("format") or "").strip().lower()
    if fmt not in TE.FORMATS:
        raise HTTPException(400, f"format inconnu: {fmt or '(vide)'} (attendu {', '.join(sorted(TE.FORMATS))})")
    p = await asyncio.to_thread(TE.FORMATS[fmt], TS.tileset_dir(tid), meta)
    logger.info(f"tuiles/export {fmt}: {tid} -> {p.name} ({p.stat().st_size} o)")
    return {"tid": tid, "format": fmt, "fichier": p.name, "octets": p.stat().st_size,
            "url": f"/api/tiles/{tid}/fichier/{p.name}"}


# ── aperçu auto-tuilé (P3, tâche t115) ───────────────────────────────────────────────────────────────────────────────
#: côté maximal de l'aperçu, en PIXELS : 16 cases de 512 px feraient 8192 px de côté, soit ≈ 200 Mo en RGB pour une
#: image qu'on ne regarde qu'en vignette ; à 4096, un jeu de 512 px garde ses 8 x 8 cases
APERCU_PX_MAX = 4096


def _refaire_jeu(meta: dict) -> dict:
    """Refabrique le jeu à l'identique depuis son meta — mêmes sources, même graine, donc mêmes octets. Le jeu n'est
    pas gardé en mémoire : c'est la recette qui fait foi, pas un cache. Bloquant (PIL) : à appeler hors de la boucle
    d'évènements."""
    a = _charger_matiere(meta.get("source_a") or {}, "matiere_a")
    b = _charger_matiere(meta.get("source_b") or {}, "matiere_b")
    return TO.assembler_jeu(a, b, meta["jeu"], int(meta["cote"]),
                            int(meta["variantes"]), int(meta["graine"]))


def _bornes_apercu(body: dict, cote: int) -> tuple[int, float, int]:
    """(cases, densite, graine) validés. UNE seule porte pour l'aperçu (P3) et pour les mesures (P4), qui tirent la
    même carte. `densite: 0` est une valeur (carte vide), pas un oubli."""
    body = body if isinstance(body, dict) else {}
    try:
        cases = int(body.get("cases") or 8)
        graine = int(body.get("graine") or 1)
        densite = float(body["densite"]) if body.get("densite") is not None else 0.55
    except (TypeError, ValueError):
        raise HTTPException(400, "cases et graine entiers, densite reelle")
    if not 4 <= cases <= 16:
        raise HTTPException(400, "cases doit tenir entre 4 et 16")
    if not 0.0 <= densite <= 1.0:
        raise HTTPException(400, "densite doit tenir entre 0 et 1")
    if cases * cote > APERCU_PX_MAX:
        raise HTTPException(400, f"{cases} cases de {cote} px depassent {APERCU_PX_MAX} px de cote : "
                                 f"{APERCU_PX_MAX // cote} cases au plus pour ce jeu")
    return cases, densite, graine


def _lire_meta(tid: str) -> dict:
    meta = TS.read_meta(tid)
    if meta is None:
        raise HTTPException(404, f"jeu de tuiles inconnu: {tid}")
    return meta


@router.post("/{tid}/apercu")
async def apercu(tid: str, body: dict):
    """Aperçu auto-tuilé : une grille de terrain tirée au hasard (rejouable), chaque case reçoit la tuile de son
    voisinage et une variante tirée. Écrit `apercu.png` dans le dossier du jeu.
    Body: {cases 4..16, densite 0..1, graine}."""
    meta = _lire_meta(tid)
    cases, densite, graine = _bornes_apercu(body, int(meta["cote"]))

    def _faire():
        jeu = _refaire_jeu(meta)
        grille = TO.carte_aleatoire(cases, densite, graine)
        img, plan = TO.composer_carte(grille, jeu, graine=graine, boucle=True)
        img.save(TS.tileset_dir(tid, create=True) / "apercu.png", format="PNG")
        return grille, plan

    grille, plan = await asyncio.get_running_loop().run_in_executor(None, _faire)
    logger.info(f"tuiles/apercu {cases}x{cases} d={densite} g={graine}: {tid}")
    return {"tid": tid, "cases": cases, "densite": densite, "graine": graine,
            "plan": plan, "grille": grille,
            "url": f"/api/tiles/{tid}/fichier/apercu.png"}


@router.get("/{tid}/fichier/{nom}")
async def fichier(tid: str, nom: str):
    try:
        p = TS.chemin_fichier(tid, nom)
    except ValueError as e:
        raise HTTPException(404, str(e))
    if not p.is_file():
        raise HTTPException(404, f"fichier absent: {nom}")
    return FileResponse(str(p))
