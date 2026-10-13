# -*- coding: utf-8 -*-
"""t208 (Espaces de marque E8, 13/10/2026) — les TEXTES DE MARQUE que le code écrivait en dur.

Spec docs/superpowers/specs/2026-10-13-espaces-de-marque.md (D10). Signatures (« From the deep. 🐙 »), échafaudages
des scripts d'avatar, accroches et signatures des scripts News, voix par défaut du polissage, prompt système du
classement des News et son brief par défaut, titre d'un lot News, thème par défaut des paroles, consignes du
storyboard : tout cela vient désormais de l'espace.
  - l'espace `deepotus` lit la graine livrée `app/espaces/deepotus_textes.json`, qui reprend MOT POUR MOT ce qui
    était codé en dur : ses sorties restent identiques à l'octet (tests/textes_espace_deepotus.json) ;
  - un autre espace reçoit des textes NEUTRES, remplis par son persona (nom, mission, audience, phrase fétiche de
    l'écran) : rien de Deepotus (ni « deep », ni « 🐙 ») n'y fuit.
Les mots « deepotus » ne restent que dans la graine. Le nom et le logo de l'APPLICATION ne sont pas concernés (ils ne
suivent jamais l'espace, décision du 13/10).
Gabarits : `{s}` (l'extrait de l'intention), `{s60}` (ses 60 premiers caractères), `{a}` (l'angle), `{langue}` ;
`remplir` ne touche qu'aux clés qu'on lui donne (les accolades d'un exemple JSON restent).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from loguru import logger

from app.services import espaces

GRAINE_DEEPOTUS = Path(__file__).resolve().parent.parent / "espaces" / "deepotus_textes.json"
_GABARIT = re.compile(r"\{([a-z0-9_]+)\}")

# Les textes d'un espace autre que Deepotus : {nom}, {signature}, {mission}, {audience} viennent de son persona.
NEUTRES = {
    "version": 1,
    "voix_off": {"EN": "{s}. That's why {nom}.", "FR": "{s}. Voila pourquoi {nom}."},
    "script_persona": "{nom} persona injected (brand cues + sign-off)",
    "script": {
        "EN": {
            "oracle": ["Listen carefully.", "{s}.", "Some things deserve a second look.", "{nom}."],
            "alpha": ["Cut the noise.", "{s}.", "You have a window. It's closing.", "{nom}. Now."],
            "zen": ["Breathe.", "{s}.", "One step at a time.", "{nom}. Patience."],
            "memer": ["POV: {s60}.", "You see it. I see it.", "Let's not pretend.", "{nom}."],
            "defaut": ["{s}.", "Here is what matters.", "{signature}"],
        },
        "FR": {
            "oracle": ["Ecoute attentivement.", "{s}.", "Certaines choses meritent un second regard.", "{nom}."],
            "alpha": ["Pas de blabla.", "{s}.", "Tu as une fenetre. Elle se ferme.", "{nom}. Maintenant."],
            "zen": ["Respire.", "{s}.", "Un pas apres l'autre.", "{nom}. Patience."],
            "memer": ["POV: {s60}.", "T'es la, je suis la.", "On va pas faire semblant.", "{nom}."],
            "defaut": ["{s}.", "Voici ce qui compte.", "{signature}"],
        },
    },
    "news": {
        "EN": {
            "accroches": {"oracle": "Here is what moved today.", "alpha": "Signal check. No noise.",
                          "zen": "Breathe. Then look.", "memer": "Okay, news dump, {nom} style.",
                          "prophet": "We have seen this script before. It rarely ends well."},
            "signatures": {"oracle": "Draw your own conclusions. {nom}.", "alpha": "Move accordingly. {nom}.",
                           "zen": "Stay steady. {nom}.", "memer": "That's the lore. {nom}.",
                           "prophet": "Stay sharp, stay skeptical. {nom}."},
            "liaisons": ["Apparently,", "Somehow,", "In today's circus,", "Predictably,", "Brace yourselves,"],
            "angle": "The {nom} read: {a}.",
        },
        "FR": {
            "accroches": {"oracle": "Voici ce qui a bouge aujourd'hui.", "alpha": "Point signal. Zero bruit.",
                          "zen": "Respire. Puis regarde.", "memer": "Bon, revue de presse, version {nom}.",
                          "prophet": "On a deja vu ce film. Ca finit rarement bien."},
            "signatures": {"oracle": "Tire tes conclusions. {nom}.", "alpha": "Agis en consequence. {nom}.",
                           "zen": "Reste stable. {nom}.", "memer": "Voila le lore. {nom}.",
                           "prophet": "Restez lucides, restez sceptiques. {nom}."},
            "liaisons": ["Apparemment,", "Comme par hasard,", "Au programme du cirque,", "Sans surprise,",
                         "Accrochez-vous,"],
            "angle": "Lecture {nom} : {a}.",
        },
    },
    "news_ton": "cynical/humorous commentator",
    "news_voix": "cynical, dry-witty commentator",
    "news_tri_systeme": ("You score news headlines for {marque}, which publishes one short vertical video per day."
                         "{public} Reply with JSON ONLY: a list of {\"id\": str, \"score\": int 0-100, \"pourquoi\": "
                         "str}, one entry per headline given, no preamble, no code fence."),
    "news_tri_brief": "{brief}",
    "news_titre": "News {nom}",
    "musique_theme": "{theme}",
    "storyboard_systeme": ("You are a storyboard director for {marque}. You split a narrated novel chapter into visual "
                           "scenes and write a vivid image prompt for each. Return ONLY valid JSON."),
    "storyboard_consigne": "\"illustration_prompt\" = a vivid cinematic image prompt in {langue} ({style})",
}


def remplir(gabarit, **vals):
    """Remplace `{cle}` par sa valeur pour les seules clés données ; une chaîne, une liste ou un dict de chaînes."""
    if isinstance(gabarit, str):
        return _GABARIT.sub(lambda m: str(vals[m.group(1)]) if m.group(1) in vals else m.group(0), gabarit)
    if isinstance(gabarit, list):
        return [remplir(x, **vals) for x in gabarit]
    if isinstance(gabarit, dict):
        return {k: remplir(v, **vals) for k, v in gabarit.items()}
    return gabarit


def _court(t, n: int) -> str:
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[:n].rstrip(" ,;:") + "…"


def valeurs(eid=None) -> dict:
    """Ce que le persona de l'espace dit de lui : nom, mission, audience, phrase fétiche, style."""
    eid = espaces.resoudre(eid)
    try:
        p = espaces.persona(eid)
    except Exception as e:  # noqa: BLE001 — un persona illisible ne casse pas une sortie
        logger.warning(f"textes_espace : persona de {eid} illisible ({e})")
        p = {}
    ident = p.get("identite") if isinstance(p.get("identite"), dict) else {}
    ecran = p.get("ecran") if isinstance(p.get("ecran"), dict) else {}
    aud = p.get("audience") if isinstance(p.get("audience"), dict) else {}
    vis = p.get("visuel") if isinstance(p.get("visuel"), dict) else {}
    nom = (str(ident.get("nom") or "").strip() or str(p.get("display_name") or "").split(" — ")[0].strip()
           or espaces.lire()["espaces"].get(eid, {}).get("nom") or eid)
    mission = _court(ident.get("mission"), 200)
    audience = _court(aud.get("qui"), 160)
    phrase = _court(ecran.get("catchphrase"), 120)
    style = _court(vis.get("style_ecrit"), 200) or ", ".join(str(k) for k in (p.get("vibe_keywords") or [])[:4]) \
        or "cinematic, atmospheric"
    return {"nom": nom, "mission": mission, "audience": audience, "signature": phrase or f"{nom}.",
            "marque": f"a brand called {nom}" + (f" ({mission.rstrip('.')})" if mission else ""),
            "public": f" Its audience: {audience.rstrip('.')}." if audience else "",
            "brief": ", ".join(x for x in (mission.rstrip("."), audience.rstrip(".")) if x) or nom,
            "theme": mission[:120] if mission else "the story so far", "style": style}


def textes(eid=None) -> dict:
    """Les textes de marque de l'espace (courant par défaut). Deepotus : la graine, à l'octet ; un autre : NEUTRES
    remplis par son persona. Les gabarits d'usage (`{s}`, `{a}`, `{langue}`) restent à remplir par l'appelant."""
    eid = espaces.resoudre(eid)
    if eid == "deepotus":
        try:
            return json.loads(GRAINE_DEEPOTUS.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            logger.warning(f"textes_espace : graine Deepotus illisible ({e}) : textes neutres")
    v = valeurs(eid)
    out = remplir(NEUTRES, **{k: v[k] for k in ("nom", "signature", "marque", "public", "brief", "theme", "style")})
    out["nom"] = v["nom"]
    out["signature"] = {"EN": v["signature"], "FR": v["signature"]}
    return out


def langue(lang) -> str:
    """« FR » ou « EN », depuis un Language, une chaîne ou rien."""
    return "FR" if str(getattr(lang, "value", lang) or "EN").upper().startswith("FR") else "EN"
