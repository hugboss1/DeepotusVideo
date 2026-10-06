# -*- coding: utf-8 -*-
"""Rangement des jeux de tuiles : un dossier par jeu sous
`outputs/tilesets/<tid>` (plan 2026-09-03-plan-tuiles, P1 — tâche t113).

Patron de `material_store` : un `tid` hors motif est refusé PUIS le chemin est
confiné — ceinture et bretelles. Motif `^tile_[0-9a-f]{8}$`. La route de
fichier ne sert qu'une LISTE BLANCHE de noms : aucun composant de chemin ne
franchit cette porte.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

TID_RE = re.compile(r"^tile_[0-9a-f]{8}$")
#: les seuls noms de fichier servis par la route de fichier
FICHIERS = ("atlas.png", "apercu.png", "carte.png", "carte.json",
            "tileset.tsx", "projet.ldtk", "tileset.tres", "meta.json")


def tilesets_root() -> Path:
    from app.config import settings
    p = Path(settings.outputs_path) / "tilesets"
    p.mkdir(parents=True, exist_ok=True)
    return p


def is_valid_tid(tid) -> bool:
    return isinstance(tid, str) and bool(TID_RE.match(tid))


def new_tid() -> str:
    root = tilesets_root()
    for _ in range(64):
        tid = "tile_" + uuid4().hex[:8]
        if not (root / tid).exists():
            return tid
    raise RuntimeError("Impossible d'allouer un identifiant de jeu de tuiles")


def tileset_dir(tid: str, create: bool = False) -> Path:
    """Dossier d'un jeu. Refuse tout `tid` hors motif, puis confine."""
    if not is_valid_tid(tid):
        raise ValueError(f"Identifiant de jeu de tuiles invalide: {tid!r}")
    root = tilesets_root().resolve()
    p = (root / tid).resolve()
    if p.parent != root:
        raise ValueError(f"Chemin hors du dossier des tuiles: {tid!r}")
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def chemin_fichier(tid: str, nom: str) -> Path:
    """Chemin d'un fichier SERVI. `nom` est comparé à une liste blanche."""
    if nom not in FICHIERS:
        raise ValueError(f"Fichier inconnu: {nom!r}")
    return tileset_dir(tid) / nom


def write_meta(tid: str, meta: dict) -> dict:
    d = tileset_dir(tid, create=True)
    tmp = d / "meta.json.tmp"
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(d / "meta.json")
    return meta


def read_meta(tid: str) -> dict | None:
    try:
        f = tileset_dir(tid) / "meta.json"
    except ValueError:
        return None
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def list_tilesets() -> list[dict]:
    """Les jeux rangés, du plus récent au plus ancien."""
    out = []
    for d in tilesets_root().iterdir():
        if not d.is_dir() or not is_valid_tid(d.name):
            continue
        meta = read_meta(d.name)
        if meta is None:
            continue
        meta["tid"] = d.name
        meta["fichiers"] = sorted(p.name for p in d.iterdir() if p.name in FICHIERS)
        out.append(meta)
    out.sort(key=lambda m: m.get("cree_le", ""), reverse=True)
    return out
