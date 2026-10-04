# -*- coding: utf-8 -*-
"""Card Forge — pièce 04, sidecar « statistiques » (tâche #85 PR B, plan-cartes T9, 04/10/2026).

SIDECAR : aucun `router` (règle 8 — la route vit dans data.py). Python pur :
`numpy` est ABSENT du runtime embarqué.

LES QUANTITÉS SONT APPLIQUÉES, TOUJOURS, ET RIEN N'EST DÉPLIÉ. « 3 cartes à 7
d'attaque » pèse 3 : c'est l'histogramme du JEU qu'on regarde, pas celui du
fichier. Le plan dépliait chaque carte pour sa médiane — 999 copies × 20 000
lignes, c'est 20 millions d'éléments en mémoire. Ici tout se calcule sur des
couples (valeur, poids) triés : médiane pondérée, classes pondérées.

UNE COLONNE D'ENTIERS À PEU DE VALEURS (coût, attaque : la COURBE d'un jeu) a
une barre PAR VALEUR, de min à max — huit classes aux bornes fractionnaires y
cacheraient le trou à 3 de mana que l'auteur cherche.
"""
from __future__ import annotations

from typing import Any

from .data import BLANK, _num, read_qty

__all__ = ["CLASSES", "SEUIL_NUM", "MAX_VALEURS", "MAX_DISCRET", "colonne_stats", "stats_table"]

CLASSES = 8            # classes d'un histogramme de réels
MAX_DISCRET = 30       # entiers : une barre par valeur si l'étendue tient en 30 barres
SEUIL_NUM = 0.9        # au-dessous, la colonne est dite catégorielle
MAX_VALEURS = 40       # valeurs distinctes montrées d'une colonne catégorielle


def _clean(v: Any) -> str:
    return str(v if v is not None else "").replace(BLANK, "").strip()


def _mediane(paires: list[tuple[float, int]], n: int) -> float:
    """Médiane PONDÉRÉE sur des couples (valeur, poids) triés. Pour n pair, la
    moyenne de la n/2-ième et de la (n/2+1)-ième carte — comme une liste dépliée."""
    if not n:
        return 0.0

    def rang(k: int) -> float:                # la k-ième carte (1-indexée)
        cum = 0
        for x, q in paires:
            cum += q
            if cum >= k:
                return x
        return paires[-1][0]
    return rang(n // 2 + 1) if n % 2 else (rang(n // 2) + rang(n // 2 + 1)) / 2.0


def colonne_stats(nom: str, valeurs: list[tuple[str, int]]) -> dict:
    """Une colonne. `valeurs` = [(texte, poids en cartes)]."""
    vides = sum(q for v, q in valeurs if not v)
    pleins = [(v, q) for v, q in valeurs if v and q > 0]
    n = sum(q for _v, q in pleins)
    nums = [(_num(v), q) for v, q in pleins]
    nums = [(x, q) for x, q in nums if x is not None]
    n_num = sum(q for _x, q in nums)
    part = (n_num / n) if n else 0.0
    base = {"nom": nom, "n": n, "vides": vides, "note": ""}
    if n and part >= SEUIL_NUM:
        par: dict[float, int] = {}
        for x, q in nums:
            par[float(x)] = par.get(float(x), 0) + q
        paires = sorted(par.items())
        lo, hi = paires[0][0], paires[-1][0]
        discret = all(x == int(x) for x in par) and (hi - lo) < MAX_DISCRET
        if discret:
            classes = [{"de": int(v), "a": int(v), "n": par.get(float(v), 0)} for v in range(int(lo), int(hi) + 1)]
        else:
            larg = (hi - lo) / CLASSES if hi > lo else 1.0
            classes = [{"de": round(lo + k * larg, 4), "a": round(lo + (k + 1) * larg, 4), "n": 0} for k in range(CLASSES)]
            for x, q in paires:
                # DERNIÈRE CLASSE FERMÉE À DROITE : sans cela le maximum tombe hors de tout intervalle
                k = CLASSES - 1 if x >= hi else min(CLASSES - 1, int((x - lo) / larg))
                classes[k]["n"] += q
        base.update({
            "genre": "numerique", "discret": discret, "min": lo, "max": hi,
            "moyenne": sum(x * q for x, q in paires) / n_num, "mediane": _mediane(paires, n_num),
            "classes": classes, "distinctes": len(par),
        })
        base["n"] = n_num
        if n_num < n:
            base["note"] = ("%d valeur(s) sur %d ne sont pas des nombres et sont exclues du calcul"
                            % (n - n_num, n))
        return base
    par2: dict[str, int] = {}
    for v, q in pleins:
        par2[v] = par2.get(v, 0) + q
    tri = sorted(par2.items(), key=lambda kv: (-kv[1], kv[0]))
    base.update({
        "genre": "categoriel", "distinctes": len(par2),
        "valeurs": [{"valeur": v, "n": q} for v, q in tri[:MAX_VALEURS]],
        "tronque": max(0, len(tri) - MAX_VALEURS),
    })
    if n and 0 < part < SEUIL_NUM:
        base["note"] = ("%d valeur(s) sur %d sont numériques (%.0f %%) : sous %.0f %%, la colonne est traitée "
                        "en catégories" % (n_num, n, part * 100, SEUIL_NUM * 100))
    return base


def stats_table(columns: list, rows: list, qty_col: Any = None, skip: Any = None, off: Any = None) -> dict:
    """Le jeu, colonne par colonne. `qty_col` PONDÈRE et n'est pas décrite ; `skip`
    écarte des colonnes (images, identifiants) ; `off` écarte des LIGNES."""
    cols = [str(c) for c in (columns or ())]
    qc = str(qty_col) if qty_col and str(qty_col) in cols else ""
    iq = cols.index(qc) if qc else -1
    ecartees = {qc} | {str(s) for s in (skip or ())}
    off_set = set()
    for v in (off if isinstance(off, list) else ()):
        try:
            off_set.add(int(v))
        except (TypeError, ValueError):
            pass
    gardees = [r for i, r in enumerate(rows or ()) if i not in off_set and isinstance(r, list)]
    poids = [read_qty(r[iq]) if 0 <= iq < len(r) else 1 for r in gardees]
    out = []
    for i, c in enumerate(cols):
        if c in ecartees:
            continue
        out.append(colonne_stats(c, [(_clean(r[i]) if i < len(r) else "", poids[k]) for k, r in enumerate(gardees)]))
    return {"total_cartes": sum(poids), "lignes": len(gardees), "qty_col": qc, "colonnes": out}
