# -*- coding: utf-8 -*-
"""t305 (25/10/2026) (lot A0) — les BOÎTES À OUTILS de l'agent : les outils sont groupés par fonctionnalité ; chaque agent ne voit
que les boîtes qui le déclarent, et `agent_outils.executer` refuse un outil hors de la boîte de l'agent du tour.
A0 ne déclare que « campagnes » (les dix outils existants) ; les autres boîtes arrivent avec leur lot.

t345 (29/10/2026, D1 du lot Scenario) : l'agent « mcp » = Claude Code (ou tout client MCP) branché sur le serveur MCP
local de l'app (services/mcp_pont.py). Il déclare les boîtes utiles à la production (campagnes, veille, recette, scan,
capture, chapitres, assets3d), mais `FILTRES` ne lui laisse que la LECTURE et le seul devis `deviser_generation` :
aucune écriture, aucune carte qui suppose une conversation. Campagnes reste figé à l'octet (fixture), le mobile aussi."""
from __future__ import annotations

from app.services import agent_outils as ao

NATURES = ("lecture", "ecriture", "carte")

BOITES: dict[str, dict] = {
    "campagnes": {
        "libelle": "agent.boites.campagnes",
        "outils": ["chercher_app", "lire_espace", "lire_bibliotheque", "lire_planificateur", "lire_document",
                   "ecrire_dossier", "proposer_porte", "deviser_generation", "creer_brouillons", "pointer"],
        "agents": ["campagnes", "mcp"],
        "mobile": True,
    },
    # t352 (27/10/2026) : la veille concurrentielle (niveau 1, lecture seule) ; le compagnon l'aura en P8
    "veille": {
        "libelle": "agent.boites.veille",
        "outils": ["veille_collecter", "veille_lire", "veille_sources", "veille_apify",   # t366 : sources Apify
                   "concurrents_pages", "concurrents_pubs", "concurrents_serp"],             # t368 : concurrents
        "agents": ["campagnes", "mcp"],
        "mobile": False,
    },
    # t354 (28/10/2026) : la recherche et la qualification des prospects ; le compagnon l'aura en P8
    "prospects": {
        "libelle": "agent.boites.prospects",
        "outils": ["prospects_chercher", "prospects_qualifier", "entreprises_registre", "entreprises_rechercher",
                   "entreprises_carte",                                   # t365 : leads Google Maps (Apify)
                   "signaux_reddit",                                      # t367 : signaux de besoin Reddit (Apify)
                   "sequence_proposer", "sequence_planifier", "whatsapp_modeles",
                   "reponses_lire", "relance_proposer"],
        "agents": ["campagnes"],
        "mobile": False,
    },
    # t311 : l'agent WhatsApp d'un espace ; jamais sur le téléphone (mobile False : boites.json inchangé)
    "whatsapp": {
        "libelle": "agent.boites.whatsapp",
        "outils": ["lire_conversation", "rediger_reponse", "choisir_modele", "proposer_creneaux",
                   "remettre_a_l_humain"],
        "agents": ["whatsapp"],
        "mobile": False,
    },
    # t346 : lire la recette exportable d'un rendu, d'un plan ou d'un asset (lecture, gratuite)
    "recette": {
        "libelle": "agent.boites.recette",
        "outils": ["lire_recette"],
        "agents": ["campagnes", "mcp"],
        "mobile": False,
    },
    # t312 : lire le texte d'une image de la Bibliothèque ; aucun agent ne la déclare encore (§11 bis)
    # t313 : + l'inspiration vers un contenu neuf (angles_inspiration en lecture, deviser_contenu_neuf en carte)
    # t314 : + calques_illustration (carte : schéma -> calques nommés du Vectorlab, devis du détourage)
    "scan": {
        "libelle": "agent.boites.scan",
        "outils": ["lire_texte_image", "angles_inspiration", "deviser_contenu_neuf", "calques_illustration"],
        "agents": ["mcp"],   # t345 : lecture seulement pour mcp (FILTRES)
        "mobile": False,
    },
    # t317 : lire la piste des clics d'une capture ; aucun agent ne la déclare encore (§11 bis : le Tutoriel est « Demander ») ;
    # t319 : + les cartes proposer_decoupe et proposer_chapitres_tuto (spec §4)
    "capture": {
        "libelle": "agent.boites.capture",
        "outils": ["lire_piste_clics", "proposer_decoupe", "proposer_chapitres_tuto"],
        "agents": ["mcp"],   # t345 : lecture seulement pour mcp (FILTRES)
        "mobile": False,
    },
    # t337 (29/10/2026) : lire la revue chiffrée d'un plan du storyboard ; t345 : + la bible et les plans, déclarée par
    # l'agent « mcp » (Claude Code) ; pas par Campagnes, dont la fixture est figée et le métier est la diffusion
    "chapitres": {
        "libelle": "agent.boites.chapitres",
        "outils": ["lire_revue_plan", "lire_bible", "lire_plans", "lire_passes_plan"],   # t334 : + les passes Blender du plan
        "agents": ["mcp"],
        "mobile": False,
    },
    # t333 + t338 (29/10/2026) : la previs colorée et la couverture d'un plan (lecture, proposition) ; aucun agent ne
    # la déclare encore (§11 bis)
    "plateau": {
        "libelle": "agent.boites.plateau",
        "outils": ["plateau_previs"],
        "agents": [],
        "mobile": False,
    },
    # t342 : pièces mobiles et budgets de triangles (lecture seule) ; aucun agent ne la déclare encore (comme « scan »)
    "assets3d": {
        "libelle": "agent.boites.assets3d",
        "outils": ["pieces_analyser", "budgets_triangles", "comparatif3d_lire",   # t344 : + le tableau d'un comparatif
                   "mouvement_lire"],   # t343 : + le mouvement sur le rig (lecture)
        "agents": ["mcp"],   # t345 : Claude Code lit pièces, budgets et comparatifs (lecture)
        "mobile": False,
    },
}


# t345 : ce qu'un agent garde des boîtes qu'il déclare. « mcp » : la LECTURE (hors outils d'une conversation WhatsApp,
# hors `pointer` qui vise l'écran de l'app, hors `lire_document` qui lit les dépôts d'une conversation de campagne) et
# le devis `deviser_generation` (une carte que le serveur MCP transforme en jeton ; jamais une dépense).
def _permis_mcp(nom: str) -> bool:
    o = ao.OUTILS.get(nom) or {}
    if nom == "deviser_generation":
        return True
    return o.get("nature") == "lecture" and not o.get("contact") and nom not in ("pointer", "lire_document")


FILTRES = {"mcp": _permis_mcp}


def boite_de(outil: str) -> str | None:
    """L'identifiant de la boîte qui contient l'outil (None si aucune)."""
    for bid, b in BOITES.items():
        if outil in b["outils"]:
            return bid
    return None


def outils_pour(agent: str) -> list[str]:
    """Les noms d'outils visibles de l'agent, dans l'ordre de `OUTILS`."""
    permis = {o for b in BOITES.values() if agent in b["agents"] for o in b["outils"]}
    garde = FILTRES.get(agent)
    return [n for n in ao.OUTILS if n in permis and (garde is None or garde(n))]


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
