# -*- coding: utf-8 -*-
"""Catalogue de démarrage des MATIÈRES — face runtime (R10c P4).

Fabriqué par `scripts/build_materials_catalog.py` dans
`backend/app/assets/materials/` : trente matières CC0 de Poly Haven, trois
cartes chacune (couleur, normale mesurée, rugosité), 1024², JPEG. Ce module
lit `catalog.json` UNE fois, le sert à l'écran, et sait recopier une matière
dans les matières de l'utilisateur.

POURQUOI LA RECOPIE PLUTÔT QU'UNE LECTURE DIRECTE — même raison que
`starter_catalog.py` pour les sons : tout l'aval (inspecteur, dérivation
re-réglable, export, GLB, Forge 3D des cartes, print3d) lit une matière
`mat_xxxxxxxx` sur disque. Une matière de catalogue qui resterait « à part »
serait un cas particulier à porter dans chaque écran, pour toujours. Recopiée
à la première utilisation, elle devient une matière ordinaire et l'aval n'a
rien à savoir de son origine — sauf son CRÉDIT, qui la suit.

CINQ CARTES SUR HUIT SONT DÉRIVÉES ICI, gratuitement et hors ligne
(`pbr_service.derive_maps`) : occlusion, hauteur, métal, émissif et ORM. C'est
exactement l'argument du produit, appliqué à son propre catalogue — et la
fiche de la matière importée le dit.

Catalogue absent (dépôt sans build) = catalogue VIDE et l'écran le dit,
jamais une exception.
"""
from __future__ import annotations

import json
import threading
import unicodedata
from pathlib import Path

from loguru import logger

STARTER_DIR = Path(__file__).resolve().parent.parent / "assets" / "materials"
CATALOG_FILE = STARTER_DIR / "catalog.json"

_lock = threading.Lock()
_cache: dict | None = None
_EMPTY: dict = {"version": 0, "source": {}, "families": [], "materials": [],
                "available": False}


class StarterError(Exception):
    """Erreur à traduire en HTTPException(status, message) par la route."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    with _lock:
        if _cache is not None:
            return _cache
        if not CATALOG_FILE.is_file():
            logger.warning(
                "matières : catalog.json absent ({}) — le catalogue de "
                "démarrage est vide. Lancer : python "
                "scripts/build_materials_catalog.py --fetch", CATALOG_FILE)
            _cache = dict(_EMPTY)
            return _cache
        try:
            d = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
            d["available"] = True
            _cache = d
        except (OSError, ValueError) as e:
            logger.error("matières : catalog.json illisible ({}) — {}",
                         CATALOG_FILE, e)
            _cache = dict(_EMPTY)
        return _cache


def reset_cache() -> None:
    global _cache
    with _lock:
        _cache = None


def _index() -> dict:
    return {m["id"]: m for m in load().get("materials", [])}


def get(item_id: str) -> dict:
    it = _index().get(str(item_id))
    if it is None:
        raise StarterError(404, f"matière « {item_id} » absente du catalogue "
                                f"de démarrage")
    return it


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def browse(family: str = "", query: str = "") -> list[dict]:
    """La recherche porte sur le nom FR, le nom Poly Haven, l'identifiant et
    les mots-clés : « brique », « brick » et « brick_wall_001 » trouvent la
    même matière, parce qu'on ne sait pas dans quelle langue on cherche."""
    items = list(_index().values())
    if family:
        items = [i for i in items if i.get("family") == family]
    q = _norm(query).strip()
    if q:
        def foin(i):
            return _norm(" ".join([str(i.get("name", "")),
                                   str(i.get("polyhaven_name", "")),
                                   str(i.get("id", "")),
                                   " ".join(i.get("tags") or [])]))
        items = [i for i in items if all(t in foin(i) for t in q.split())]
    return items


def carte_path(item_id: str, carte: str) -> Path:
    """Chemin d'une carte, CONFINÉ à STARTER_DIR.

    Le catalogue est généré, donc sain en principe — mais il est lu depuis le
    disque, et un chemin qui s'en échapperait serait servi tel quel. On
    vérifie le confinement au lieu de le supposer (même garde que
    `starter_catalog.asset_path`)."""
    it = get(item_id)
    rel = (it.get("maps") or {}).get(str(carte))
    if not rel:
        raise StarterError(404, f"carte « {carte} » absente de « {item_id} »")
    p = (STARTER_DIR / rel).resolve()
    if not p.is_relative_to(STARTER_DIR.resolve()):
        raise StarterError(400, "chemin de carte hors du catalogue")
    if not p.is_file():
        raise StarterError(404, f"fichier absent : {rel}")
    return p


def importer(ids) -> list[dict]:
    """Recopie des matières du catalogue dans les matières de l'utilisateur.

    Les trois cartes MESURÉES sont reprises telles quelles ; les cinq autres
    sont dérivées localement. Les niveaux de départ sont ceux que les cartes
    PORTENT (`natural_levels`), pas des 0/1 de principe."""
    from PIL import Image
    from app.services import material_store as MS
    from app.services import pbr_service as PBR

    faits = []
    for brut in (ids or []):
        it = get(brut)
        base_p = carte_path(it["id"], "basecolor")
        with Image.open(base_p) as im:
            base = im.convert("RGB")
        res = base.size[0]
        auteurs = ", ".join((it.get("authors") or {}).keys()) or "Poly Haven"
        mat = MS.create_material(
            name=it["name"], prompt="", full_prompt="", res=res,
            seamless=True, seam={"before": None, "after": None},
            source={"kind": "catalog", "model": None,
                    "filename": it["id"], "prep": None})
        mid = mat["id"]
        maps = PBR.derive_maps(base, mat["derive"],
                               list(MS.SECONDARY_MAPS))
        maps["basecolor"] = base
        # les DEUX cartes mesurées écrasent leur dérivée : elles portent une
        # information qu'aucune estimation depuis l'albédo ne peut inventer
        for carte, kind in (("normal", "normal"), ("roughness", "roughness")):
            try:
                p = carte_path(it["id"], carte)
            except StarterError:
                continue
            with Image.open(p) as im:
                maps[kind] = (im.convert("RGB") if kind == "normal"
                              else im.convert("L")).resize((res, res))
        maps["orm"] = Image.merge("RGB", (maps["ao"].convert("L"),
                                          maps["roughness"].convert("L"),
                                          maps["metallic"].convert("L")))
        MS.save_maps(mid, maps)
        MS.write_source(mid, base)
        mat = MS.read_material(mid)
        mat["props"] = MS.merge_props(mat["props"], MS.natural_levels(maps))
        mat["credit"] = {
            "source": (load().get("source") or {}).get("name", "Poly Haven"),
            "author": auteurs, "license": "CC0-1.0",
            "url": it.get("url", "")}
        mat = MS.refresh_report(mat, maps)
        MS.write_material(mat)
        faits.append(MS.read_material(mid))
    return faits
