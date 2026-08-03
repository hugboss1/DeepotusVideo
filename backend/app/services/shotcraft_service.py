"""v1.22 (W-d) — pont vers le skill Claude « video-shotcraft ».

Le skill installé (~/.claude/skills/video-shotcraft) est une bibliothèque de
106 fiches de plans motion-design (slugs anglais, énergie, résumés) plus une
doctrine de réalisation. Ce service la met au service de l'agent interne de
découpage storyboard :

- découverte du skill installé (env SHOTCRAFT_SKILL_DIR, réglage homonyme,
  sinon ~/.claude/skills/video-shotcraft) et parse de son catalogue
  gallery/api/library.json — les fiches ajoutées par une mise à jour du
  skill deviennent immédiatement valides ;
- repli : catalogue embarqué backend/app/knowledge/shotcraft_catalog.json
  (mêmes slugs + gloses anglaises éditoriales, régénéré par
  scripts/gen_shotcraft_catalog.py) — la fonctionnalité marche donc aussi
  sur une machine sans le skill ;
- doctrine distillée (SHOTCRAFT_DOCTRINE) + catalogue compact à injecter
  dans le prompt du découpage (_ai_shots) ;
- validation des slugs `motion_recipe` et gloses pour le prompt croquis.

Contrat fail-safe du projet : ne lève jamais — au pire, catalogue vide et
prompt_block() == "" (le découpage retombe sur son comportement pré-W-d).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from loguru import logger

from app.config import settings

_BUNDLED = Path(__file__).parent.parent / "knowledge" / "shotcraft_catalog.json"
_DEFAULT_SKILL_DIR = Path.home() / ".claude" / "skills" / "video-shotcraft"

# Distillation anglaise des principes du SKILL.md (§3-5) et de la fiche
# tension-camera-moves — la grammaire transposable au découpage narratif.
SHOTCRAFT_DOCTRINE = (
    "SHOTCRAFT DOCTRINE (video-shotcraft craft rules):\n"
    "- One motion idea per shot: each shot stars exactly ONE technique, and "
    "a given technique stars at most once per chapter (repeats read as "
    "filler).\n"
    "- Breathe after key beats: when a key image or line lands, hold on it "
    "about a second inside the shot's duration; err slow, never rushed.\n"
    "- Design the energy arc of the whole sequence (calm opening, build, "
    "peak, quiet close). Adjacent shots usually move one energy step; a "
    "jump of two or more is a deliberate punch, never an accident.\n"
    "- The camera is motivated by emotion, not decoration: slow push-in = "
    "mounting tension; pull-back = isolation or finality; freeze + orbit = "
    "this moment matters; held dutch angle rolled level = wrongness "
    "resolved; crash zoom = shock; whip pan = urgent relocation.\n"
    "- Cinematic feel comes from camera, light and rhythm working together, "
    "never from effect spam; groups of elements enter through motion, not "
    "per-element glow.")

_CAT_ORDER = {"camera": 0, "transition": 1, "rhythm": 2, "impact": 3,
              "light": 4, "material": 5, "particle": 6, "title": 7,
              "outro": 8}

_cache: dict = {"key": None, "data": None}


def _energy_class(zh: str) -> str:
    """Classe d'énergie à partir du champ (chinois) de library.json."""
    s = (zh or "").strip()
    if not s or s.lower().startswith("n/a"):
        return "n/a"
    if "极高" in s or "峰值" in s:
        return "peak"
    if "/" in s:
        return "varies"
    if "中高" in s:
        return "mid-high"
    if "中低" in s or "低中" in s:
        return "mid-low"
    if "高" in s:
        return "high"
    if "低" in s:
        return "low"
    if "中" in s:
        return "mid"
    return "varies"


def _skill_dir() -> Path | None:
    """Dossier du skill installé, ou None s'il est absent."""
    cand = (os.environ.get("SHOTCRAFT_SKILL_DIR")
            or getattr(settings, "SHOTCRAFT_SKILL_DIR", "") or "").strip()
    p = Path(cand) if cand else _DEFAULT_SKILL_DIR
    try:
        return p if (p / "SKILL.md").exists() else None
    except OSError:
        return None


def _load_bundled() -> dict[str, dict]:
    try:
        data = json.loads(_BUNDLED.read_text(encoding="utf-8-sig"))
        return {c["slug"]: dict(c) for c in data.get("cards", [])
                if c.get("slug")}
    except Exception as e:                                # noqa: BLE001
        logger.warning(f"shotcraft: catalogue embarqué illisible: {e}")
        return {}


def _load() -> dict:
    """Catalogue fusionné {source, path, cards} (cache par mtime)."""
    sd = _skill_dir()
    lib = (sd / "gallery" / "api" / "library.json") if sd else None
    try:
        lib_mtime = lib.stat().st_mtime if lib and lib.exists() else None
    except OSError:
        lib_mtime = None
    try:
        bundled_mtime = _BUNDLED.stat().st_mtime if _BUNDLED.exists() else None
    except OSError:
        bundled_mtime = None
    key = (str(sd) if sd else "", lib_mtime, bundled_mtime)
    if _cache["key"] == key and _cache["data"] is not None:
        return _cache["data"]

    cards = _load_bundled()
    source = "bundled"
    if lib and lib_mtime is not None:
        try:
            data = json.loads(lib.read_text(encoding="utf-8-sig"))
            n = 0
            for it in data.get("cards", []):
                slug = str(it.get("name") or "").strip()
                if not slug:
                    continue
                card = cards.get(slug) or {
                    # fiche ajoutée par une mise à jour du skill, pas encore
                    # curée : valide pour la sélection manuelle, hors prompt.
                    "slug": slug, "cat": "extra", "anim": False,
                    "gloss": slug.replace("-", " "),
                }
                card["energy"] = _energy_class(str(it.get("energy") or ""))
                cards[slug] = card
                n += 1
            if n:
                source = "installed"
        except Exception as e:                            # noqa: BLE001
            logger.warning(f"shotcraft: library.json illisible ({e}) — "
                           f"catalogue embarqué utilisé")
    data = {"source": source,
            "path": str(sd) if (sd and source == "installed") else None,
            "cards": cards}
    _cache["key"], _cache["data"] = key, data
    return data


def catalog() -> dict:
    return _load()


def valid_slugs() -> set[str]:
    return set(_load()["cards"])


def gloss(slug: str | None) -> str:
    c = _load()["cards"].get((slug or "").strip())
    return (c or {}).get("gloss") or (slug or "").replace("-", " ")


def status() -> dict:
    d = _load()
    return {"source": d["source"],
            "installed": d["source"] == "installed",
            "path": d["path"],
            "cards": len(d["cards"]),
            "anim_cards": sum(1 for c in d["cards"].values()
                              if c.get("anim"))}


def prompt_block(max_cards: int = 64) -> str:
    """Doctrine + catalogue compact des fiches « animation/récit » pour le
    prompt du découpage. Chaîne vide si aucun catalogue n'est disponible."""
    d = _load()
    anim = [c for c in d["cards"].values() if c.get("anim")]
    if not anim:
        return ""
    anim.sort(key=lambda c: (_CAT_ORDER.get(c.get("cat"), 99), c["slug"]))
    lines = [f"- {c['slug']} [{c.get('cat', '?')}, energy "
             f"{c.get('energy', '?')}]: {c.get('gloss', '')}"
             for c in anim[:max_cards]]
    return (SHOTCRAFT_DOCTRINE
            + "\nMOTION RECIPE CATALOG (video-shotcraft cards — per shot, "
              "pick the one whose motion best serves the story beat):\n"
            + "\n".join(lines))
