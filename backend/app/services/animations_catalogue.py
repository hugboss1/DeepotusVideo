# -*- coding: utf-8 -*-
"""t398 (31/10/2026) — le CATALOGUE des animations Meshy, parcourable dans l'écran Animer du 3D Studio.

Hier, les identifiants de la bibliothèque Meshy se tapaient à la main et `meshy_service.ACTIONS_RIG` n'en nommait que
cinq. Le relevé des API (t387, annexe A de `docs/superpowers/specs/2026-10-31-api-3d-releve.md`) a lu la liste
publique entière : 680 entrées, de −2 à 696 avec des trous, en cinq catégories. Elle est figée dans
`meshy_animations.json` (à côté de ce module) : lire le catalogue ne coûte rien et ne touche pas le réseau.

Ce module ne fait que LIRE : chercher par texte (tous les mots, sans accents ni casse, sur le nom, la clé et la
sous-catégorie), filtrer par catégorie et sous-catégorie, paginer. Les favoris et les collections, qui sont des
ÉCRITURES de l'utilisateur, vivent dans `studio3d_animer`.

Les identifiants −2 (Walking) et −1 (Running) sont les animations de base livrées avec le rig : elles ne s'appliquent
pas (`applicable: False`) — Meshy et fal n'acceptent que 0 à 696.
"""
from __future__ import annotations

import json
import math
import unicodedata
from functools import lru_cache
from pathlib import Path

FICHIER = Path(__file__).resolve().parent / "meshy_animations.json"
PAR_PAGE = 48
PAR_PAGE_MAX = 200
ID_MIN, ID_MAX = 0, 696          # bornes acceptées par Meshy (`action_id`) et fal (`animation_action_id`)
# l'ordre d'affichage des catégories : du plus utile (marche, course) au plus rare (danse)
ORDRE = ("WalkAndRun", "BodyMovements", "DailyActions", "Fighting", "Dancing")


def _plat(s) -> str:
    """minuscules, sans accents ; les séparateurs de clé (`_`) deviennent des espaces"""
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    return s.lower().replace("_", " ")


@lru_cache(maxsize=1)
def charger() -> tuple[dict, ...]:
    """Les entrées du catalogue, chacune enrichie de `applicable` et d'un texte de recherche. Lu une fois."""
    doc = json.loads(FICHIER.read_text(encoding="utf-8"))
    out = []
    for a in doc["animations"]:
        e = dict(a)
        e["applicable"] = ID_MIN <= int(a["id"]) <= ID_MAX
        e["_texte"] = " ".join(_plat(x) for x in (a.get("nom"), a.get("cle"), a.get("sous_categorie"),
                                                  a.get("categorie")))
        out.append(e)
    return tuple(out)


def _public(e: dict) -> dict:
    return {k: v for k, v in e.items() if not k.startswith("_")}


def par_id(action_id) -> dict | None:
    try:
        i = int(action_id)
    except (TypeError, ValueError):
        return None
    return next((_public(e) for e in charger() if e["id"] == i), None)


def categories() -> list[dict]:
    """[{id, nombre, sous: [{id, nombre}]}] dans l'ordre d'affichage ; les sous-catégories de la plus fournie à la
    moins fournie (comme le tableau du relevé)."""
    cats: dict[str, dict[str, int]] = {}
    for e in charger():
        sous = cats.setdefault(e["categorie"], {})
        k = e.get("sous_categorie") or ""
        sous[k] = sous.get(k, 0) + 1
    rang = {c: i for i, c in enumerate(ORDRE)}
    out = []
    for c in sorted(cats, key=lambda c: (rang.get(c, len(ORDRE)), c)):
        s = sorted(((k, n) for k, n in cats[c].items() if k), key=lambda kn: (-kn[1], kn[0]))
        out.append({"id": c, "nombre": sum(cats[c].values()), "sous": [{"id": k, "nombre": n} for k, n in s]})
    return out


def chercher(q: str = "", categorie: str = "", sous_categorie: str = "", page: int = 1,
             par_page: int = PAR_PAGE, ids=None) -> dict:
    """Une page du catalogue filtré. `ids` (liste) restreint aux identifiants donnés, DANS LEUR ORDRE (favoris,
    collection). Une page hors bornes est ramenée à la dernière ; `par_page` est borné à [1, 200]."""
    mots = [m for m in _plat(q).split() if m]
    try:
        par_page = max(1, min(PAR_PAGE_MAX, int(par_page)))
    except (TypeError, ValueError):
        par_page = PAR_PAGE
    if ids is not None:
        rang = {}
        for i, x in enumerate(ids):
            try:
                rang.setdefault(int(x), i)
            except (TypeError, ValueError):
                continue
        base = sorted((e for e in charger() if e["id"] in rang), key=lambda e: rang[e["id"]])
    else:
        base = list(charger())
    res = [e for e in base
           if (not categorie or e["categorie"] == categorie)
           and (not sous_categorie or (e.get("sous_categorie") or "") == sous_categorie)
           and all(m in e["_texte"] for m in mots)]
    total = len(res)
    pages = max(1, math.ceil(total / par_page))
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    page = max(1, min(pages, page))
    debut = (page - 1) * par_page
    return {"total": total, "page": page, "pages": pages, "par_page": par_page,
            "entrees": [_public(e) for e in res[debut:debut + par_page]]}
