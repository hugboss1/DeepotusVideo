"""Animations d'une feuille de sprites (plan sprites, tâche 2) — la LECTURE seule, posée par T109 pour les exports.

`spans` est le SEUL endroit qui décide du repli « une animation `default` qui couvre la feuille » : les quatre
exports (Godot, atlas, Aseprite, Paper2D) le partagent, sinon Godot nommerait `default` là où Aseprite ne nommerait
rien. Les tags eux-mêmes et la durée par image (`manifest["anim"]`, `frames[i]["duration_ms"]`) sont écrits par la
tâche 2 du plan (t110 du suivi : validation `normalize_anim`, appelée à la route puis dans `_assemble`) ; tant qu'ils
manquent, les exports écrivent une animation unique et la durée tirée du fps.

Pur stdlib : ce module ne connaît ni PIL, ni FastAPI, ni les réglages.
"""
from __future__ import annotations


def spans(anim: dict | None, n: int) -> list[tuple[str, int, int]]:
    """(nom, from, to) par animation. Sans tag : UNE animation « default » qui couvre la feuille."""
    tags = (anim or {}).get("tags") or []
    if not tags:
        return [("default", 0, max(0, n - 1))]
    return [(t["name"], int(t["from"]), int(t["to"])) for t in tags]


def duree_ms(frame: dict, fps) -> int:
    """La durée d'une image : la sienne (`duration_ms`, tâche 2) ou celle du fps de la feuille."""
    ms = frame.get("duration_ms")
    if ms:
        return int(ms)
    return int(round(1000 / max(1.0, float(fps or 8))))
