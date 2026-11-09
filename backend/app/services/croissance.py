# -*- coding: utf-8 -*-
"""t491 (lot G1 « boucle de croissance », 09/11/2026) — les fonctions PURES de la mesure d'un post contre l'habituel de
son compte (conception docs/superpowers/specs/2026-11-09-getripping-design.md, décision D1).

- l'HABITUEL d'un compte = la médiane des vues de ses N derniers posts du même format (N = 10) ; sous 5 posts il n'y a
  pas d'habituel, et on le dit plutôt que de comparer à trois valeurs ;
- le MULTIPLICATEUR « × habituel » = vues du post / habituel, à ÂGE ÉGAL : un post de 2 jours se compare aux vues
  qu'avaient les précédents à 1 jour, pas à leurs vues d'aujourd'hui ;
- les JALONS : 1, 3, 7 et 30 jours après la publication. La valeur d'un jalon est le premier instantané pris à cet âge
  ou après, dans une fenêtre bornée : un relevé trop tardif ne vaut pas pour le jalon ;
- un GAGNANT : au moins SEUIL_GAGNANT fois l'habituel.

Aucune lecture, aucune écriture, aucun appel : metrics_service fournit les instantanés.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median

JALONS = (1, 3, 7, 30)                # jours après la publication
FENETRE = 0.5                         # un jalon J accepte un relevé jusqu'à J × (1 + FENETRE) jours…
FENETRE_MIN = 1.5                     # …et au moins J + 1,5 jour (la passe de mesures est quotidienne)
N_HABITUEL = 10
MIN_HABITUEL = 5
SEUIL_GAGNANT = 3.0


def habituel(vues: list, n: int = N_HABITUEL, minimum: int = MIN_HABITUEL):
    """La médiane des `n` DERNIÈRES valeurs (l'ordre donné est chronologique, les None sont ignorés) ; None sous
    `minimum` valeurs."""
    v = [x for x in (vues or []) if isinstance(x, (int, float)) and not isinstance(x, bool)][-n:]
    if len(v) < minimum:
        return None
    return median(v)


def multiplicateur_habituel(vues, historique: list, n: int = N_HABITUEL, minimum: int = MIN_HABITUEL):
    """vues / habituel(historique), à une décimale ; None sans habituel ou si l'habituel est nul."""
    h = habituel(historique, n, minimum)
    if not h or not isinstance(vues, (int, float)) or isinstance(vues, bool):
        return None
    return round(vues / h, 1)


def gagnant(multiplicateur, seuil: float = SEUIL_GAGNANT) -> bool:
    return multiplicateur is not None and multiplicateur >= seuil


def jalon_courant(age_jours: float):
    """Le plus grand jalon déjà atteint à cet âge ; None avant le premier."""
    atteints = [j for j in JALONS if age_jours >= j]
    return atteints[-1] if atteints else None


def _borne(j: int) -> float:
    return max(j * (1 + FENETRE), j + FENETRE_MIN)


def jalons_mesures(posted_at: datetime | None, instantanes: list[dict]) -> dict:
    """{jalon: instantané | None}. Chaque instantané est un dict portant `fetched_at` ; celui retenu pour un jalon J
    est le PREMIER dont l'âge (fetched_at - posted_at) est dans [J, borne(J)] ; il est rendu avec `age_j`."""
    vide = {j: None for j in JALONS}
    if posted_at is None:
        return vide
    dates = sorted(((s["fetched_at"] - posted_at).total_seconds() / 86400.0, i)
                   for i, s in enumerate(instantanes or []) if s.get("fetched_at") is not None)
    for j in JALONS:
        for age, i in dates:
            if age < j:
                continue
            if age <= _borne(j):
                vide[j] = dict(instantanes[i], age_j=round(age, 2))
            break
    return vide


def regularite(dates: list, fin: datetime, jours: int, tz_min: int = 0) -> dict:
    """t492 : la régularité de publication sur les `jours` derniers jours LOCAUX (UTC + tz_min) finissant à `fin`.
    {jours, jours_avec_post, serie, semaine} ; la série compte les jours consécutifs avec un post en remontant depuis
    aujourd'hui, ou depuis hier si rien n'est encore sorti aujourd'hui (la journée n'est pas finie)."""
    jours = max(1, int(jours))
    dec = timedelta(minutes=int(tz_min or 0))
    auj = (fin + dec).date()
    debut = auj - timedelta(days=jours - 1)
    par_jour: dict = {}
    for d in dates or []:
        if d is None:
            continue
        j = (d + dec).date()
        if debut <= j <= auj:
            par_jour[j] = par_jour.get(j, 0) + 1
    serie, j = 0, auj if auj in par_jour else auj - timedelta(days=1)
    while j in par_jour:
        serie += 1
        j -= timedelta(days=1)
    semaine = [{"jour": (auj - timedelta(days=k)).isoformat(), "posts": par_jour.get(auj - timedelta(days=k), 0)}
               for k in range(min(7, jours) - 1, -1, -1)]
    return {"jours": jours, "jours_avec_post": len(par_jour), "serie": serie, "semaine": semaine}
