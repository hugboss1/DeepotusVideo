# -*- coding: utf-8 -*-
"""Catalogue de l'assistant (spec docs/superpowers/specs/2026-10-19-agent-catalogue-design.md § 2) — le COMMUN.

Tables et aides partagées par les lecteurs de sources (catalogue_bundle : la SPA ; catalogue_sources : labs,
Réglages, fiches) : à quel écran et à quel cadre appartient une clé i18n, quelles clés sont des messages, la forme
de base d'une fiche.
"""
from __future__ import annotations

import hashlib

# zone d'une clé i18n (1er segment) → écran de l'app (agent_aide.VUES) ; tout le reste : « commun »
ECRAN_DE_ZONE = {
    "quick": "quick", "studio": "studio", "motion": "studio", "episodes": "episodes", "atelier": "episodes",
    "son": "sonvfx", "sfx": "sonvfx", "vfx": "sonvfx", "montage": "montage", "montage_svm": "montage",
    "subs": "montage", "scheduler": "scheduler", "planif_news": "scheduler", "templates": "templates",
    "news": "news", "biblio": "library", "lib3d": "assets3d", "sprites": "assets3d", "tuiles": "assets3d",
    "cartes": "assets3d", "matiere": "assets3d", "studio3d": "assets3d", "etabli": "assets3d",
    "plateau": "assets3d", "avatar": "avatarlive", "vectorlab": "vectorlab", "photolab": "photolab",
    "reglages": "settings", "espaces": "settings", "transfert": "settings",
    "projets": "library",                # t307 (25/10/2026) : les canaux d'un projet de la Bibliothèque
    "whatsapp": "whatsapp",              # t311 (27/10/2026) : la page WhatsApp (cadre /whatsapp/, voir catalogue_sources.LABS)
    "pose3d": "assets3d",                # t376 (29/10/2026) : le choix de pose de Game Assets 3D (/shared/dz-pose3d.js)
    "ga3d": "assets3d",                  # t376 : l'écran Game Assets 3D traduit (maillon dzga3d)
    "a2d": "assets3d",                   # t377 (30/10/2026) : les cartes de l'onglet Assets 2D (maillon dza2d)
    "chemins": "settings",               # t378 (30/10/2026) : les emplacements de Réglages › Chemins (dz-chemins.js)
    "fils": "news",                      # t381 (30/10/2026) : les fils suivis de News › Sources (dz-fils.js)
    "apparence": "settings",             # t382 (30/10/2026) : la palette de Réglages › Apparence (dz-apparence.js)
}
# préfixe « zone.objet » rattaché à un autre écran que sa zone (consulté AVANT ECRAN_DE_ZONE)
ECRAN_DE_PREFIXE = {"avatar.noeud": "studio",           # titres des nœuds avatar du graphe du Studio
                    "whatsapp.espace": "settings"}      # t311 : le panneau « Agent WhatsApp » de Réglages › Espaces
# zone → lab affiché dans un cadre intégré (les iframes que monte la SPA)
CADRE_DE_ZONE = {"vectorlab": "/vectorlab/", "photolab": "/photolab/", "sprites": "/spritelab/",
                 "tuiles": "/tilelab/", "cartes": "/cardforge/", "matiere": "/materialforge/",
                 "studio3d": "/studio3d/"}
# rôle d'une clé qui désigne un MESSAGE (état, erreur), pas un élément : le dernier segment, ou son dernier morceau
# après « _ » (montage.projets.montage_vide). « titre » et « aide » n'y sont PAS : ce sont souvent de vraies infobulles.
ROLES_MESSAGES = {"echec", "erreur", "err", "vide", "aucun", "aucune", "chargement", "en_cours", "illisible",
                  "refuse", "fait", "enregistre", "pose", "plusieurs", "un", "redaction", "lecture", "generation",
                  "manquant", "manquante", "manque", "attente", "pret"}
CHAMPS = {"input", "select", "textarea"}
VIDE = {"fr": "", "en": ""}


def zone(cle: str) -> str:
    return cle.split(".", 1)[0]


def ecran(cle: str) -> str:
    prefixe = ".".join(cle.split(".", 2)[:2])
    return ECRAN_DE_PREFIXE.get(prefixe) or ECRAN_DE_ZONE.get(zone(cle), "commun")


def message(cle: str) -> bool:
    dernier = cle.rsplit(".", 1)[-1]                   # « code_en_cours » : un rôle de plusieurs morceaux compte aussi
    return dernier in ROLES_MESSAGES or any(dernier.endswith("_" + r) for r in ROLES_MESSAGES)


def _texte(dico: dict, cle: str) -> dict:
    v = dico.get(cle) or {}
    return {"fr": v.get("fr", ""), "en": v.get("en", "")}


def _base(cle: str, typ: str, dico: dict) -> dict:
    return {"id": cle, "ecran": ecran(cle), "cadre": CADRE_DE_ZONE.get(zone(cle)), "type": typ,
            "libelle": _texte(dico, cle), "infobulle": None, "icone": None, "sources": [f"i18n:{cle}"]}


def _sha8(t: str) -> str:
    return hashlib.sha1(t.encode("utf-8")).hexdigest()[:8]

