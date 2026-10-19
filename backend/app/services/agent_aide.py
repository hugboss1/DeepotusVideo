# -*- coding: utf-8 -*-
"""Assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md, 19/10/2026).

La connaissance vit dans docs/agent/ (AGENT.md écrit à la main, ancres.json) et docs/guide/src/ (chapitres.json,
jeveux.json). Ce module l'assemble en message système, appelle UN moteur de texte sous le plafond « aide », puis
transforme les balises de la réponse en actions pour l'écran. Il n'exécute RIEN de payant pour l'utilisateur.
"""
from __future__ import annotations

import json
import re
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


# toute balise MAJUSCULE entre crochets, avec ou sans cible : les connues deviennent des actions, les autres sont
# retirées (comptées) — l'écran ne voit jamais une balise
BALISE = re.compile(r"\[([A-Z]{2,8})(?::([^\[\]\n]{1,80}))?\]")
MAX_ACTIONS = 6


def _action(typ: str, cible: str) -> dict | None:
    k = connaissance()
    if typ == "POINT" and cible in k["ancres"]:
        a = k["ancres"][cible]
        return {"type": "point", "cible": cible, "ecran": a.get("ecran"), "selecteur": a.get("selecteur"),
                "texte": a.get("texte"), "cadre": a.get("cadre"), "reglages": a.get("reglages"),
                "fr": a["fr"], "en": a["en"]}
    if typ == "ALLER" and cible in VUES:
        return {"type": "aller", "cible": cible}
    if typ == "GUIDE" and cible in k["chapitres"]:
        c = k["chapitres"][cible]
        return {"type": "guide", "cible": cible, "fr": c["fr"], "en": c["en"]}
    return None


def analyser(texte) -> tuple[str, list, int]:
    """(texte sans balises ni indentation, actions dédoublonnées ≤ MAX_ACTIONS, nombre de balises rejetées)."""
    actions, vus, rejets = [], set(), 0

    def remplacer(m):
        nonlocal rejets
        a = _action(m.group(1), (m.group(2) or "").strip())
        if a is None:
            rejets += 1
        elif (a["type"], a["cible"]) not in vus and len(actions) < MAX_ACTIONS:
            vus.add((a["type"], a["cible"]))
            actions.append(a)
        return ""

    propre = BALISE.sub(remplacer, str(texte or ""))
    # linéaire (« [ \t]+\n » en re.sub est quadratique) ; retire aussi l'indentation qu'un modèle recopie, et les \r
    propre = "\n".join(l.strip() for l in propre.split("\n"))
    propre = re.sub(r"\n{3,}", "\n\n", propre).strip()
    return propre, actions, rejets
