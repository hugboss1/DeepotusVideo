# -*- coding: utf-8 -*-
"""Assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md, 19/10/2026).

La connaissance vit dans docs/agent/ (AGENT.md écrit à la main, ancres.json) et docs/guide/src/ (chapitres.json,
jeveux.json). Ce module l'assemble en message système, appelle UN moteur de texte sous le plafond « aide », puis
transforme les balises de la réponse en actions pour l'écran. Il n'exécute RIEN de payant pour l'utilisateur.
"""
from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
DOSSIER = RACINE / "docs" / "agent"
GUIDE = RACINE / "docs" / "guide" / "src"
# les vues du rail de la SPA (bundle : `Yu`), dans l'ordre du rail
VUES = ("quick", "studio", "episodes", "sonvfx", "montage", "scheduler", "templates", "news", "library", "assets3d",
        "vectorlab", "photolab", "avatarlive", "settings")
# les sections des Réglages (settings_routes._RUBRIQUES)
SECTIONS_REGLAGES = ("diag", "coffre", "appareils", "keys", "accounts", "personas", "branding", "pack", "defaults",
                     "paths", "news", "appearance", "pricing", "transfert", "espaces")
