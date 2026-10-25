# -*- coding: utf-8 -*-
"""t305 (lot A0) — les BOÎTES À OUTILS de l'agent : les outils sont groupés par fonctionnalité ; chaque agent ne voit
que les boîtes qui le déclarent, et `agent_outils.executer` refuse un outil hors de la boîte de l'agent du tour.
A0 ne déclare que « campagnes » (les dix outils existants) ; les autres boîtes arrivent avec leur lot."""
from __future__ import annotations

from app.services import agent_outils as ao

NATURES = ("lecture", "ecriture", "carte")

BOITES: dict[str, dict] = {
    "campagnes": {
        "libelle": "agent.boites.campagnes",
        "outils": ["chercher_app", "lire_espace", "lire_bibliotheque", "lire_planificateur", "lire_document",
                   "ecrire_dossier", "proposer_porte", "deviser_generation", "creer_brouillons", "pointer"],
        "agents": ["campagnes"],
        "mobile": True,
    },
}


def boite_de(outil: str) -> str | None:
    """L'identifiant de la boîte qui contient l'outil (None si aucune)."""
    for bid, b in BOITES.items():
        if outil in b["outils"]:
            return bid
    return None


def outils_pour(agent: str) -> list[str]:
    """Les noms d'outils visibles de l'agent, dans l'ordre de `OUTILS`."""
    permis = {o for b in BOITES.values() if agent in b["agents"] for o in b["outils"]}
    return [n for n in ao.OUTILS if n in permis]


def _definitions(noms: list[str]) -> list[dict]:
    return [{"name": n, "description": ao.OUTILS[n]["description"], "input_schema": ao.OUTILS[n]["schema"]}
            for n in noms if n in ao.OUTILS]


def definitions_pour(agent: str) -> list[dict]:
    """La liste `tools` de l'API Anthropic pour cet agent (même format que `agent_outils.definitions()`)."""
    return _definitions(outils_pour(agent))


def paquet_mobile() -> list[dict]:
    """Les boîtes destinées au mobile : [{id, libelle, outils: définitions}]."""
    return [{"id": bid, "libelle": b["libelle"], "outils": _definitions([n for n in ao.OUTILS if n in b["outils"]])}
            for bid, b in BOITES.items() if b.get("mobile")]


def verifier() -> list[str]:
    """Les incohérences du registre (liste vide = sain)."""
    p: list[str] = []
    vus: dict[str, str] = {}
    for bid, b in BOITES.items():
        if not str(b.get("libelle", "")).startswith("agent.boites."):
            p.append(f"{bid} : libelle {b.get('libelle')!r} ne commence pas par agent.boites.")
        for o in b["outils"]:
            if o not in ao.OUTILS:
                p.append(f"{bid} : outil {o} absent de OUTILS")
                continue
            if o in vus:
                p.append(f"{o} : présent dans deux boîtes ({vus[o]} et {bid})")
            vus[o] = bid
            if ao.OUTILS[o].get("nature") not in NATURES:
                p.append(f"{o} : nature {ao.OUTILS[o].get('nature')!r} hors de NATURES")
    for o in ao.OUTILS:
        if o not in vus:
            p.append(f"{o} : outil sans boîte")
    return p
