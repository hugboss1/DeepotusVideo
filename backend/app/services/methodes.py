# -*- coding: utf-8 -*-
"""t433 (lot M0 « Méthodes », 08/11/2026) — le CATALOGUE des méthodes : 94 fiches bilingues (étapes, contrôles,
pièges, exemples de demandes) rangées par famille et portées chacune par un agent métier (§3 de la conception
docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md).

Lecture seule et gratuite. Les données vivent dans app/knowledge/methodes.json, CONSTRUIT par
scripts/methodes_construire.py (jamais édité à la main). Lu une fois puis gardé en mémoire.
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

FICHIER = Path(__file__).resolve().parent.parent / "knowledge" / "methodes.json"
LANGUES = ("fr", "en")


@lru_cache(maxsize=1)
def catalogue() -> dict:
    return json.loads(FICHIER.read_text(encoding="utf-8"))


def _plat(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return s.lower()


def _langue(langue: str) -> str:
    return langue if langue in LANGUES else "fr"


def _texte_cherche(m: dict) -> str:
    morceaux = [m["slug"]]
    for cle in ("titre", "resume", "etapes", "exemples"):
        for lg in LANGUES:
            v = m[cle][lg]
            morceaux.extend(v if isinstance(v, list) else [v])
    morceaux.extend(m["modeles"])
    return _plat(" ".join(morceaux))


def resume(m: dict, langue: str = "fr") -> dict:
    """La carte d'une méthode dans la galerie (sans les étapes)."""
    lg = _langue(langue)
    c = catalogue()
    a = c["agents"][m["agent"]]
    return {"slug": m["slug"], "titre": m["titre"][lg], "resume": m["resume"][lg], "famille": m["famille"],
            "famille_libelle": c["familles"][m["famille"]][lg], "agent": m["agent"], "agent_libelle": a[lg],
            "agent_lot": a["lot"], "ecrans": m["ecrans"], "filtre": m["filtre"], "valeur": m["valeur"],
            "effort": m["effort"], "licence_skill": m["licence_skill"]}


def lister(*, famille: str = "", agent: str = "", ecran: str = "", q: str = "", langue: str = "fr") -> list[dict]:
    """Les méthodes filtrées (tous les filtres se cumulent), de la plus utile à la moins utile."""
    mots = [w for w in _plat(q).split() if w]
    sortie = []
    for m in catalogue()["methodes"]:
        if famille and m["famille"] != famille:
            continue
        if agent and m["agent"] != agent:
            continue
        if ecran and ecran not in m["ecrans"]:
            continue
        if mots:
            t = _texte_cherche(m)
            if not all(w in t for w in mots):
                continue
        sortie.append(resume(m, langue))
    return sortie


def fiche(slug: str, langue: str = "fr") -> dict | None:
    """La fiche complète d'une méthode dans une langue (None si le slug est inconnu)."""
    lg = _langue(langue)
    c = catalogue()
    m = next((x for x in c["methodes"] if x["slug"] == slug), None)
    if m is None:
        return None
    a = c["agents"][m["agent"]]
    return dict(resume(m, lg), etapes=m["etapes"][lg], controles=m["controles"][lg], pieges=m["pieges"][lg],
                exemples=m["exemples"][lg], illustration=m["illustration"][lg], modeles=m["modeles"],
                equivalents=m["equivalents"], source=m["source"], agent_role=a["role_" + lg],
                agent_outil=a["outil"], agent_tache=a["tache"],
                ecrans_libelles=[c["ecrans"][e][lg] for e in m["ecrans"]])


def reperes(langue: str = "fr") -> dict:
    """Ce qu'il faut pour bâtir les filtres : familles, agents, écrans (avec leur nombre de méthodes), la source."""
    lg = _langue(langue)
    c = catalogue()
    ms = c["methodes"]
    return {
        "total": len(ms),
        "familles": [{"id": k, "libelle": v[lg], "nb": sum(1 for m in ms if m["famille"] == k)}
                     for k, v in c["familles"].items()],
        "agents": [{"id": k, "libelle": v[lg], "role": v["role_" + lg], "lot": v["lot"], "outil": v["outil"],
                    "nb": v["nb"]} for k, v in c["agents"].items()],
        "ecrans": [{"id": k, "libelle": v[lg], "vue": v["vue"], "nb": sum(1 for m in ms if k in m["ecrans"])}
                   for k, v in c["ecrans"].items()],
        "source": {"nom": c["source"]["nom"], "url": c["source"]["url"], "note": c["source"]["note_" + lg]},
    }
