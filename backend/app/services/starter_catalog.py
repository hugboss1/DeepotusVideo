# -*- coding: utf-8 -*-
"""Catalogue de démarrage — index CC0 embarqué (Son & VFX).

Fabriqué par scripts/build_starter_catalog.py dans
backend/app/assets/starter/ : 80 textures de particules, 5 séquences animées,
606 bruitages, tous en CC0 (kenney.nl). Ce module est la face runtime : il lit
catalog.json UNE fois, le sert aux écrans, et sait recopier un élément dans la
Bibliothèque de l'utilisateur.

Pourquoi la recopie plutôt qu'une lecture directe : tout l'aval de l'app
(tiroir Sons du Montage, nœuds Studio, mixage, rendu) lit la Bibliothèque. Un
son de démarrage qui resterait « à part » serait un cas particulier à traiter
dans chaque écran, pour toujours. Recopié à la première utilisation, il devient
un asset utilisateur ordinaire et l'aval n'a rien à savoir de son origine.

Aucun accès réseau, aucun sous-processus : les durées et les vignettes ont été
calculées au build. Catalogue absent (dépôt sans build) = catalogue vide et
l'UI le dit, jamais une exception.
"""
from __future__ import annotations

import json
import re
import shutil
import threading
import unicodedata
from datetime import datetime
from pathlib import Path

from loguru import logger

STARTER_DIR = Path(__file__).resolve().parent.parent / "assets" / "starter"
CATALOG_FILE = STARTER_DIR / "catalog.json"

_lock = threading.Lock()
_cache: dict | None = None

_EMPTY: dict = {"version": 0, "sources": [], "sfx_families": [],
                "particle_families": [], "particles": [], "anims": [],
                "sfx": [], "available": False}


class StarterError(Exception):
    """Erreur à traduire en HTTPException(status, message) par la route."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def load() -> dict:
    """catalog.json, mémoïsé. Absent ou illisible -> catalogue vide."""
    global _cache
    if _cache is not None:
        return _cache
    with _lock:
        if _cache is not None:
            return _cache
        if not CATALOG_FILE.is_file():
            logger.warning(
                "starter: catalog.json absent ({}) — le catalogue de démarrage "
                "est vide. Lancer: python scripts/build_starter_catalog.py "
                "--fetch", CATALOG_FILE)
            _cache = dict(_EMPTY)
            return _cache
        try:
            data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
            data["available"] = True
            _cache = data
        except (OSError, ValueError) as e:
            logger.error("starter: catalog.json illisible ({}) — {}",
                         CATALOG_FILE, e)
            _cache = dict(_EMPTY)
        return _cache


def reset_cache() -> None:
    """Vide la mémoïsation (tests, rebuild à chaud)."""
    global _cache
    with _lock:
        _cache = None


# ── index par identifiant ───────────────────────────────────────────────────
def _index(kind: str) -> dict[str, dict]:
    cat = load()
    key = {"sfx": "sfx", "particle": "particles", "anim": "anims"}.get(kind)
    if key is None:
        raise StarterError(400, f"kind inconnu : {kind!r} "
                                f"(sfx, particle ou anim attendu)")
    return {it["id"]: it for it in cat.get(key, [])}


def get(kind: str, item_id: str) -> dict:
    it = _index(kind).get(str(item_id))
    if it is None:
        raise StarterError(404, f"{kind} « {item_id} » absent du catalogue "
                                f"de démarrage")
    return it


def asset_path(kind: str, item_id: str) -> Path:
    """Chemin disque d'un élément, confiné à STARTER_DIR.

    Le catalogue est généré, donc en principe sain — mais il est lu depuis le
    disque et un chemin qui s'échappe du dossier serait servi tel quel. Le
    confinement est vérifié ici plutôt que supposé.
    """
    it = get(kind, item_id)
    rel = it.get("file") or it.get("dir") or ""
    p = (STARTER_DIR / rel).resolve()
    if not p.is_relative_to(STARTER_DIR.resolve()):
        raise StarterError(400, "chemin d'asset hors du catalogue")
    if not p.exists():
        raise StarterError(404, f"fichier absent : {rel}")
    return p


def anim_frames(item_id: str) -> list[Path]:
    """Frames d'une séquence animée, dans l'ordre."""
    d = asset_path("anim", item_id)
    frames = sorted(d.glob("[0-9][0-9][0-9].png"))
    if not frames:
        raise StarterError(404, f"séquence « {item_id} » sans frame")
    return frames


# ── recherche / filtrage (rail + champ de recherche de l'écran) ─────────────
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def browse(kind: str, family: str = "", query: str = "",
           limit: int = 0) -> list[dict]:
    """Éléments d'un type, filtrés par famille et/ou recherche libre.

    La recherche porte sur le libellé FR, le radical d'origine (anglais) et
    l'identifiant : « verre », « glass » et « impactGlass » trouvent le même
    son, parce qu'on ne sait pas dans quelle langue l'utilisateur cherche.
    """
    items = list(_index(kind).values())
    if family:
        items = [it for it in items if it.get("family") == family]
    q = _norm(query).strip()
    if q:
        terms = q.split()
        def hay(it):
            return _norm(" ".join(str(it.get(k, ""))
                                  for k in ("name", "stem", "id", "family")))
        items = [it for it in items if all(t in hay(it) for t in terms)]
    return items[:limit] if limit and limit > 0 else items


# ── import dans la Bibliothèque ─────────────────────────────────────────────
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(label: str, ext: str) -> str:
    base = _SAFE.sub("_", unicodedata.normalize("NFKD", label)
                     .encode("ascii", "ignore").decode()).strip("._-")
    return f"{base or 'starter'}{ext}"


def _unique(folder: Path, name: str) -> Path:
    dest = folder / name
    if not dest.exists():
        return dest
    stem, ext = Path(name).stem, Path(name).suffix
    for i in range(2, 500):
        cand = folder / f"{stem}_{i}{ext}"
        if not cand.exists():
            return cand
    raise StarterError(409, f"trop de copies de « {name} » dans la Bibliothèque")


def import_sfx(ids: list[str]) -> list[dict]:
    """Copie des bruitages du catalogue dans le dossier audio de la
    Bibliothèque, avec le sidecar de tags (kind « sfx ») que lit le tiroir
    Sons du Montage. Retourne les items importés, format /api/audio."""
    from app.config import settings
    from app.services import sfx_service

    folder = settings.images_path.parent / "audio"
    folder.mkdir(parents=True, exist_ok=True)

    out = []
    for raw in ids:
        it = get("sfx", raw)
        src = asset_path("sfx", raw)
        dest = _unique(folder, _safe_name(it["name"], src.suffix))
        shutil.copy2(src, dest)
        sfx_service.record_meta(dest.name, {
            "kind": "sfx",
            "prompt": f"{it['name']} — catalogue de démarrage (CC0, Kenney)",
            "starter_id": it["id"],
            "created": datetime.now().isoformat(timespec="seconds")})
        out.append({"filename": dest.name, "url": f"/api/audio/{dest.name}",
                    "name": it["name"], "dur": it.get("dur", 0),
                    "size_kb": dest.stat().st_size // 1024})
    return out


def import_particle(ids: list[str]) -> list[dict]:
    """Copie des textures de particules dans les images de la Bibliothèque
    (réutilisables comme n'importe quelle image : nœud Studio, overlay…)."""
    from app.config import settings

    folder = settings.images_path
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for raw in ids:
        it = get("particle", raw)
        src = asset_path("particle", raw)
        dest = _unique(folder, f"particule_{it['id']}{src.suffix}")
        shutil.copy2(src, dest)
        out.append({"filename": dest.name, "url": f"/api/images/{dest.name}",
                    "name": it["name"]})
    return out
