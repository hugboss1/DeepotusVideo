# -*- coding: utf-8 -*-
"""Assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md, 19/10/2026).

La connaissance vit dans docs/agent/ (AGENT.md écrit à la main, ancres.json) et docs/guide/src/ (chapitres.json,
jeveux.json). Ce module l'assemble en message système, appelle UN moteur de texte sous le plafond « aide », puis
transforme les balises de la réponse en actions pour l'écran. Il n'exécute RIEN de payant pour l'utilisateur.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
DOSSIER = RACINE / "docs" / "agent"
GUIDE = RACINE / "docs" / "guide" / "src"
# les vues du rail de la SPA, dans l'ordre du rail
VUES = ("quick", "studio", "episodes", "sonvfx", "montage", "scheduler", "templates", "news", "library", "assets3d",
        "vectorlab", "photolab", "avatarlive", "settings")
# les sections des Réglages que l'écran sait ouvrir (`dzReglagesEcoute` du bundle ; settings_routes._RUBRIQUES en a une
# de plus, « transfert », que l'écran n'ouvre pas par section)
SECTIONS_REGLAGES = ("diag", "coffre", "appareils", "keys", "accounts", "personas", "branding", "pack", "defaults",
                     "paths", "news", "appearance", "pricing", "espaces")


@lru_cache(maxsize=1)
def connaissance() -> dict:
    """Lue une fois par processus (les fichiers suivent l'installation, jamais l'utilisateur)."""
    ancres = json.loads((DOSSIER / "ancres.json").read_text(encoding="utf-8"))["ancres"]
    chap = json.loads((GUIDE / "chapitres.json").read_text(encoding="utf-8"))["chapitres"]
    jv = json.loads((GUIDE / "jeveux.json").read_text(encoding="utf-8"))["entrees"]
    return {"agent": (DOSSIER / "AGENT.md").read_text(encoding="utf-8"),
            "ancres": {a["id"]: a for a in ancres},
            "chapitres": {c["id"]: c for c in chap},
            "jeveux": jv}


def _ligne(v, n: int = 60) -> str:
    """Une valeur libre (nom d'espace, écran) réduite à UNE ligne bornée avant d'entrer dans le message système."""
    return " ".join(str(v or "").split())[:n]


def systeme(ecran: str, lang: str, espace: str = "") -> str:
    """AGENT.md + chapitres + « Je veux… » + ancres + vues, puis le contexte EN DERNIER : tout ce qui précède
    « ## Contexte » est identique d'une question à l'autre (cache du préfixe chez le fournisseur)."""
    ecran, espace = _ligne(ecran, 30), _ligne(espace)
    k = connaissance()
    en = lang == "en"
    cle = "en" if en else "fr"
    chap = "\n".join(f"- {c['id']} : {c[cle]}" for c in k["chapitres"].values())
    jv = "\n".join(f"- {e[cle]} → {e['cible']}" for e in k["jeveux"])
    anc = "\n".join(f"- {a['id']} ({a.get('ecran') or 'partout'}) : {a[cle]}" for a in k["ancres"].values())
    return (f"{k['agent']}\n\n## Chapitres (id : titre)\n{chap}\n\n## Je veux…\n{jv}\n\n"
            f"## Ancres (id (écran) : libellé)\n{anc}\n\n## Vues\n{', '.join(VUES)}\n\n"
            f"## Contexte\n- écran ouvert : {ecran or 'inconnu'}\n- espace de marque actif : {espace or 'inconnu'}\n"
            f"- langue : {'English' if en else 'français'}\n")
