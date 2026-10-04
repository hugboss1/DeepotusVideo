# -*- coding: utf-8 -*-
"""Card Forge — pièce 11 « Édition » (tâche #84, plan-cartes T5, 04/10/2026).

CE QUI SE LIVRE AUTOUR DE LA CARTE : la table virtuelle (Tabletop Simulator,
Tabletopia) ; plus tard le livret de règles, le mockup, la fiche produit.

Elle ne dessine RIEN : aucun z ne lui est alloué (lint, Z_TABLE). Comme P7,
elle ASSEMBLE des cartes rendues par `CF.renderCard` et téléversées — le
navigateur voit et manipule, Python écrit. Règle 8 : elle n'importe le routeur
d'aucune voisine ; ce qu'il lui faut d'une autre pièce, elle le RECOPIE.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .contract import is_valid_did

router = APIRouter()

# Les cibles, dans l'ordre du panneau. Chacune dit ce qu'elle SAIT — relu sur
# la documentation de l'éditeur le 04/10/2026 —, pas ce qu'on aimerait.
CIBLES = [
    {"id": "tts", "label": "Tabletop Simulator — planches + objet sauvegardé",
     "livraison": "zip",
     "verifie": "04/10/2026 — kb.tabletopsimulator.com (custom-deck, asset-creation, save-file-format)",
     "note": "Planches de 10 x 7 cartes au plus (la grille est un réglage du "
             "Custom Deck, sans maximum publié), 4096 px de large au plus, PNG "
             "ou JPG en RVB, et un objet JSON (CustomDeck : FaceURL, BackURL, "
             "NumWidth, NumHeight) à poser dans Saved Objects."},
    {"id": "tabletopia", "label": "Tabletopia — une image par face",
     "livraison": "zip",
     "verifie": "04/10/2026 — help.tabletopia.com (how-to-prepare-graphics)",
     "note": "Recto et verso dans des FICHIERS SÉPARÉS, tous les composants "
             "d'un même type à la même taille, 2000 x 2000 px au plus par "
             "objet, 1 à 2 Mo visés (3 à 10 Mo au maximum). Aucune grille de "
             "collage : on ne lui en envoie pas."},
]


def _deck(did: str) -> dict:
    """Deck existant, ou l'erreur qui va bien (400 / 404) — jamais un 500.
    Import PARESSEUX du magasin, comme P7 : aucun cycle à l'import."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    from . import core as deck_store
    doc = deck_store.read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    return doc


@router.get("/cibles")
async def get_cibles(did: str):
    """Le catalogue des tables virtuelles servies, avec ce que chacune exige."""
    _deck(did)
    return {"cibles": CIBLES}
