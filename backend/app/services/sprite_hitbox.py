# -*- coding: utf-8 -*-
"""Hitboxes par frame — T112 (spec sorceress-sprite-suite, lot « Combat » : « calque hitboxes = rectangles par frame
dans le manifest, dessin au glisser, C/V entre frames »).

Une hitbox est un rectangle en pixels DE CELLULE (origine en haut à gauche de la case, pas de la feuille) :
{x, y, w, h, type}. `type` vaut « hit » (la zone qui frappe) ou « hurt » (la zone qui peut être touchée) — les deux
mots que les moteurs de combat 2D emploient ; « hit » par défaut. Un rectangle qui déborde est ROGNÉ à la cellule, un
rectangle entièrement dehors est écarté : la case est la seule vérité géométrique d'une frame.

Elles vivent dans `manifest.json`, clé `hitboxes` de chaque frame — absente quand la frame n'en a pas, pour qu'une
feuille sans hitbox garde ses exports à l'octet près. `ecrire()` ne touche QUE ce champ, puis réécrit les exports du
disque (ceux du ZIP) ; les téléchargements à la volée relisent le manifeste. Pur stdlib, comme `sprite_anim`.
"""
from __future__ import annotations

import json
from pathlib import Path

TYPES = ("hit", "hurt")
MAX_PAR_FRAME = 16


def _entier(v, champ: str) -> int:
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        raise ValueError(f"hitbox : {champ} doit être un nombre (reçu {v!r})")


def normaliser_frame(rects, cell_w: int, cell_h: int) -> list[dict]:
    """Les rectangles d'UNE frame, entiers, typés, rognés à la cellule (dehors : écartés)."""
    if rects in (None, ""):
        return []
    if not isinstance(rects, list):
        raise ValueError("hitbox : une liste de rectangles par frame")
    if len(rects) > MAX_PAR_FRAME:
        raise ValueError(f"hitbox : {len(rects)} rectangles sur une frame — {MAX_PAR_FRAME} au plus")
    out = []
    for r in rects:
        if not isinstance(r, dict):
            raise ValueError(f"hitbox : un rectangle {{x, y, w, h, type}} attendu (reçu {r!r})")
        x, y, w, h = (_entier(r.get(k), k) for k in ("x", "y", "w", "h"))
        if w <= 0 or h <= 0:
            raise ValueError(f"hitbox : rectangle vide ({w}x{h})")
        t = str(r.get("type") or "hit").lower()
        if t not in TYPES:
            raise ValueError(f"hitbox : type {t!r} inconnu (attendu : {', '.join(TYPES)})")
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(int(cell_w), x + w), min(int(cell_h), y + h)
        if x1 <= x0 or y1 <= y0:
            continue                                  # entièrement hors de la case
        out.append({"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0, "type": t})
    return out


def normaliser(hitboxes, n_frames: int, cell_w: int, cell_h: int) -> list[list[dict]]:
    """Une liste PAR frame, dans l'ordre des frames de la feuille."""
    if not isinstance(hitboxes, list):
        raise ValueError("hitboxes : une liste de listes, une par frame")
    if len(hitboxes) != n_frames:
        raise ValueError(f"hitboxes : {len(hitboxes)} liste(s) pour {n_frames} frames — une par frame")
    return [normaliser_frame(r, cell_w, cell_h) for r in hitboxes]


def poser(manifest: dict, hitboxes: list[list[dict]]) -> dict:
    """Pose les hitboxes NORMALISÉES sur les frames du manifeste (clé absente quand la liste est vide)."""
    for f, rects in zip(manifest["frames"], hitboxes):
        if rects:
            f["hitboxes"] = rects
        else:
            f.pop("hitboxes", None)
    return manifest


def reecrire_exports(manifest: dict, out_dir: Path) -> None:
    """Les exports du DISQUE (ceux que le ZIP emporte) relus depuis le manifeste."""
    from PIL import Image
    from app.services import sprite_export as SE
    with Image.open(out_dir / "sheet.png") as sh:
        w, h = sh.size
    SE.write_all(manifest, out_dir, w, h)


def ecrire(out_dir: Path, hitboxes) -> dict:
    """Valide, pose, écrit le manifeste (lui seul change) puis réécrit les exports du disque. ValueError /
    FileNotFoundError parlants."""
    mf = Path(out_dir) / "manifest.json"
    if not mf.is_file():
        raise FileNotFoundError("aucune feuille pour ce job")
    m = json.loads(mf.read_text(encoding="utf-8"))
    g = m.get("grid") or {}
    norm = normaliser(hitboxes, len(m.get("frames") or []), int(g.get("cell_w") or 0), int(g.get("cell_h") or 0))
    poser(m, norm)
    tmp = mf.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, indent=2), encoding="utf-8")
    tmp.replace(mf)
    reecrire_exports(m, Path(out_dir))
    return {"frames": len(norm), "rectangles": sum(len(r) for r in norm),
            "par_frame": [len(r) for r in norm]}
