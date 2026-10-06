"""Animations d'une feuille de sprites (plan sprites, tâche 2) — tags d'animation et durée par image.

UN SEUL PROPRIÉTAIRE DE LA VALIDATION, APPELÉ DEUX FOIS. `normalize_anim` tourne une première fois dans
`sprite_service.normalize_opts` pour le refus rapide de la route — le nombre d'images n'y est PAS connu (le filmstrip
peut encore en retirer), donc `n=None` et les bornes de tag sont testées contre MAX_FRAMES ; puis une seconde fois
dans `_assemble`, où `n` est enfin le vrai. Sans le second appel un tag qui déborde la sélection passerait, et Godot
lirait une animation vide.

`spans` est le SEUL endroit qui décide du repli « une animation `default` qui couvre la feuille » : les quatre
exports (Godot, atlas, Aseprite, Paper2D) le partagent, sinon Godot nommerait `default` là où Aseprite ne nommerait
rien. Une feuille produite avant T110 n'a ni `manifest["anim"]` ni `frames[i]["duration_ms"]` : les exports y
écrivent une animation unique et la durée tirée du fps.

Pur stdlib : ce module ne connaît ni PIL, ni FastAPI, ni les réglages.
"""
from __future__ import annotations

import re

# le nom d'un tag devient un identifiant Godot (`&"idle"`) et une STRING Aseprite : on interdit ce qui casserait l'un
# des deux plutôt que d'échapper différemment dans quatre exports
_NOM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,31}$")
DIRECTIONS = ("forward", "reverse", "pingpong", "pingpong_reverse")
MAX_TAGS = 16
MAX_FRAMES = 64          # même plafond que normalize_opts.max_frames
DUREE_MIN, DUREE_MAX = 10, 10000


def normalize_anim(spec, n: int | None, fps: int = 8) -> dict:
    """{tags, durations} normalisé. `n` = nombre d'images de la feuille, ou None quand il n'est pas encore connu.
    ValueError lisible sinon (la route la transforme en 400)."""
    if spec in (None, ""):
        spec = {}
    if not isinstance(spec, dict):
        raise ValueError("anim must be an object {tags, durations}")
    borne = MAX_FRAMES if n is None else n

    brut = spec.get("tags") or []
    if not isinstance(brut, (list, tuple)):
        raise ValueError("anim.tags must be a list of {name, from, to}")
    if len(brut) > MAX_TAGS:
        raise ValueError(f"anim.tags: {MAX_TAGS} tags at most")
    tags, vus = [], set()
    for t in brut:
        if not isinstance(t, dict):
            raise ValueError("anim.tags: each tag is an object {name, from, to, direction, repeat}")
        nom = str(t.get("name") or "")
        if not _NOM.match(nom):
            raise ValueError(f"anim tag name {nom!r}: 1-32 characters, letters, digits, space, _ or -, "
                             "starting with a letter or a digit")
        if nom in vus:
            raise ValueError(f"anim tag name {nom!r} appears twice")
        vus.add(nom)
        try:
            a, b = int(t.get("from")), int(t.get("to"))
        except (TypeError, ValueError):
            raise ValueError(f"anim tag {nom!r}: from/to must be integers")
        if not 0 <= a <= b < borne:
            raise ValueError(f"anim tag {nom!r}: 0 <= from <= to < {borne} (got from={a}, to={b})")
        sens = str(t.get("direction") or "forward").lower()
        if sens not in DIRECTIONS:
            raise ValueError(f"anim tag {nom!r}: direction must be one of {', '.join(DIRECTIONS)}")
        try:
            rep = int(t.get("repeat") or 0)
        except (TypeError, ValueError):
            raise ValueError(f"anim tag {nom!r}: repeat must be an integer")
        if not 0 <= rep <= 65535:
            raise ValueError(f"anim tag {nom!r}: repeat must be 0-65535 (0 = forever)")
        tags.append({"name": nom, "from": a, "to": b, "direction": sens, "repeat": rep})

    dur = spec.get("durations")
    if dur in (None, ""):
        defaut = max(DUREE_MIN, int(round(1000 / max(1, int(fps)))))
        durations = None if n is None else [defaut] * n
    else:
        if not isinstance(dur, (list, tuple)):
            raise ValueError("anim.durations must be a list of milliseconds")
        if len(dur) > MAX_FRAMES:
            raise ValueError(f"anim.durations: {MAX_FRAMES} values at most")
        if n is not None and len(dur) != n:
            raise ValueError(f"anim.durations: {len(dur)} values for {n} frames — give exactly one per frame")
        durations = []
        for v in dur:
            try:
                ms = int(v)
            except (TypeError, ValueError):
                raise ValueError("anim.durations: milliseconds are integers")
            if not DUREE_MIN <= ms <= DUREE_MAX:
                raise ValueError(f"anim.durations: {ms} ms is out of range ({DUREE_MIN}-{DUREE_MAX})")
            durations.append(ms)
    return {"tags": tags, "durations": durations}


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
