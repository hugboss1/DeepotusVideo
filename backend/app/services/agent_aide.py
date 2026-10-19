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

from loguru import logger

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

MAX_QUESTION = 2000
MAX_HISTORIQUE = 10
MAX_TOUR = 1000
MAX_TOKENS = 2000   # les moteurs qui raisonnent comptent la réflexion dans la sortie
REPONSE_VIDE = {"fr": "Voici où regarder :", "en": "Here is where to look:"}
SANS_REPONSE = {"fr": "Je n'ai pas de réponse utile ; le guide peut aider.",
                "en": "I have no useful answer; the guide can help."}
PREFERENCE = ("anthropic", "openai", "gemini")
SANS_CLE = {
    "fr": "Aucun moteur de texte n'est branché : l'assistant a besoin d'une clé (Anthropic, OpenAI, Gemini) ou d'un "
          "serveur local. Ouvre les Réglages › Clés d'API, colle ta clé, puis repose ta question.",
    "en": "No text engine is connected: the assistant needs an API key (Anthropic, OpenAI, Gemini) or a local "
          "server. Open Settings › API keys, paste your key, then ask again.",
}


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
    anc = "\n".join(f"- {a['id']} ({'partout' if a.get('partout') or not a.get('ecran') else a['ecran']}) : {a[cle]}" for a in k["ancres"].values())
    return (f"{k['agent']}\n\n## Chapitres (id : titre)\n{chap}\n\n## Je veux…\n{jv}\n\n"
            f"## Ancres (id (écran) : libellé)\n{anc}\n\n## Vues\n{', '.join(VUES)}\n\n"
            f"## Contexte\n- écran ouvert : {ecran or 'inconnu'}\n- espace de marque actif : {espace or 'inconnu'}\n"
            f"- langue : {'English' if en else 'français'}\n")


# toute balise MAJUSCULE entre crochets, avec ou sans cible : les connues deviennent des actions, les autres sont
# retirées (comptées) — l'écran ne voit jamais une balise
BALISE = re.compile(r"\[([A-Z]{2,8})(?::([^\[\]\n]{1,80}))?\]")
MAX_ACTIONS = 6
# A5 : coordonnées rendues par un moteur qui a VU une capture (pixels de la capture), libellé facultatif
XY = re.compile(r"^(\d{1,5})\s*,\s*(\d{1,5})\s*(?::(.*))?$")


def _action(typ: str, cible: str, image: dict | None = None) -> dict | None:
    """image : {largeur, hauteur} de la capture jointe à l'appel (A5) — seule une réponse à une capture peut rendre des
    coordonnées, et jamais une nouvelle demande de capture."""
    k = connaissance()
    if typ == "POINT" and cible in k["ancres"]:
        a = k["ancres"][cible]
        return {"type": "point", "cible": cible, "ecran": a.get("ecran"), "selecteur": a.get("selecteur"),
                "texte": a.get("texte"), "cadre": a.get("cadre"), "reglages": a.get("reglages"),
                "partout": bool(a.get("partout")), "libelle": a.get("libelle"),
                "fr": a["fr"], "en": a["en"]}
    if typ == "POINT" and image:
        m = XY.match(cible)
        if m:
            x, y = int(m.group(1)), int(m.group(2))
            if x <= image["largeur"] and y <= image["hauteur"]:
                return {"type": "point_xy", "cible": f"{x},{y}", "x": x, "y": y, "largeur": image["largeur"],
                        "hauteur": image["hauteur"], "libelle": _ligne(m.group(3) or "", 60)}
        return None
    if typ == "VOIR" and not cible and not image:
        return {"type": "voir", "cible": "ecran"}
    if typ == "ALLER" and cible in VUES:
        return {"type": "aller", "cible": cible}
    if typ == "GUIDE" and cible in k["chapitres"]:
        c = k["chapitres"][cible]
        return {"type": "guide", "cible": cible, "fr": c["fr"], "en": c["en"]}
    return None


def analyser(texte, image: dict | None = None) -> tuple[str, list, int]:
    """(texte sans balises ni indentation, actions dédoublonnées ≤ MAX_ACTIONS, nombre de balises rejetées).
    image : {largeur, hauteur} quand la réponse vient d'un appel avec capture (A5)."""
    actions, vus, rejets = [], set(), 0

    def remplacer(m):
        nonlocal rejets
        a = _action(m.group(1), (m.group(2) or "").strip(), image)
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


def choisir_moteur(demande: str = "") -> str:
    """Le moteur demandé s'il est connu ET configuré ; sans demande, le premier configuré dans PREFERENCE, puis le
    premier configuré tout court ; "" si aucun. Jamais de repli d'un moteur demandé vers un autre."""
    from app.services import moteurs_texte as MT
    if demande:
        return demande if MT.connu(demande) and MT.configure(demande) and not MT.modele_fautif(demande) else ""
    lignes = [l["moteur"] for l in MT.etat() if l["configure"] and not l.get("fautif")]
    for p in PREFERENCE:
        if p in lignes:
            return p
    return lignes[0] if lignes else ""


def _espace() -> str:
    try:
        from app.services import espaces as ES
        return str(ES.actif().get("nom") or "")
    except Exception:  # noqa: BLE001 — l'espace n'est qu'un contexte : son absence ne bloque pas l'aide
        return ""


def _historique(h) -> str:
    if not isinstance(h, list):
        return ""
    lignes = []
    for t in h[-MAX_HISTORIQUE:]:
        if isinstance(t, dict) and t.get("role") in ("user", "assistant") and isinstance(t.get("texte"), str):
            qui = "Utilisateur" if t["role"] == "user" else "Assistant"
            lignes.append(f"{qui} : {t['texte'].strip()[:MAX_TOUR]}")
    return ("Échange précédent :\n" + "\n".join(lignes) + "\n\nNouvelle question : ") if lignes \
        else "Nouvelle question : "


async def demander(corps, lang: str = "fr") -> dict:
    """{texte, actions, moteur, nom, rejets, sans_cle}. ValueError : corps ou question invalides. RuntimeError :
    le moteur a échoué. HTTPException 402 : plafond « aide » (remonte tel quel jusqu'au dialogue de l'écran)."""
    from app.services import moteurs_texte as MT
    if not isinstance(corps, dict):
        raise ValueError("Corps JSON attendu.")
    q = corps.get("question")
    q = q.strip()[:MAX_QUESTION] if isinstance(q, str) else ""
    if not q:
        raise ValueError("La question est vide.")
    lang = "en" if (corps.get("lang") or lang) == "en" else "fr"
    ecran = corps.get("ecran") if corps.get("ecran") in VUES else ""
    demande = corps.get("moteur").strip() if isinstance(corps.get("moteur"), str) else ""
    moteur = choisir_moteur(demande)
    if not moteur:
        _, actions, _ = analyser("[POINT:reglages.cles] [GUIDE:cles]")
        return {"texte": SANS_CLE[lang], "actions": actions, "moteur": "", "nom": "", "rejets": 0, "sans_cle": True}
    sortie = await MT.tirer_garde(moteur, "", _historique(corps.get("historique")) + q,
                                  systeme(ecran, lang, _espace()), MAX_TOKENS, categorie="aide", effort="low")
    texte, actions, rejets = analyser(sortie)
    if not texte:
        if actions:
            texte = REPONSE_VIDE[lang]
        else:
            texte = SANS_REPONSE[lang]
            actions = analyser("[GUIDE:tour]")[1]
    if rejets:
        logger.info(f"agent_aide : {rejets} balise(s) inconnue(s) retirée(s) ({moteur})")
    return {"texte": texte, "actions": actions, "moteur": moteur, "nom": MT.nom(moteur), "rejets": rejets,
            "sans_cle": False}


def etat() -> dict:
    from app.services import moteurs_texte as MT
    k = connaissance()
    moteurs = [{"moteur": l["moteur"], "nom": l["nom"], "cout": MT.nature_cout(l["moteur"])}
               for l in MT.etat() if l["configure"] and not l.get("fautif")]
    return {"moteur": choisir_moteur(), "moteurs": moteurs, "ancres": len(k["ancres"]),
            "chapitres": len(k["chapitres"])}
