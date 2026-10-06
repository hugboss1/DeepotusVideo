# -*- coding: utf-8 -*-
"""T102 (plan-son-vfx T7, P5) — direction d'interprétation par balises Eleven v3.

Registre RELU le 06/10/2026 sur elevenlabs.io/docs/best-practices/prompting/eleven-v3.
Deux écarts au plan du 03/09, mesurés sur la page :
  · `[sad]` et `[pause]` n'y figurent pas — la page dit de régler les pauses par
    la ponctuation (points de suspension), et « v3 ne prend pas les balises
    SSML break ». Elles ne sont donc ni proposées ni tenues pour connues : une
    balise que la doc ne promet pas est signalée, pas garantie ;
  · `[fart]` et `[strong X accent]` y sont (« unique and special »).

Voicebox n'interprète aucune balise, les modèles v2/flash non plus : on les
RETIRE et on le DIT (notes), plutôt que de laisser prononcer « crochet excited
crochet »."""
from __future__ import annotations

import re

V3_TAGS = {
    "emotion": ["[excited]", "[curious]", "[sarcastic]", "[mischievously]",
                "[crying]"],
    "voix": ["[whispers]", "[sighs]", "[exhales]", "[laughs]",
             "[laughs harder]", "[starts laughing]", "[wheezing]", "[snorts]"],
    "sons": ["[applause]", "[clapping]", "[explosion]", "[gunshot]",
             "[swallows]", "[gulps]"],
    # « unique and special » de la page : à manier en connaissance de cause
    "special": ["[sings]", "[woo]"],
}
EXPERIMENTAL = {"[sings]", "[woo]"}
# connues mais pas proposées dans la palette (hors ton de marque)
_HORS_PALETTE = {"[fart]"}
KNOWN = {t for g in V3_TAGS.values() for t in g} | EXPERIMENTAL | _HORS_PALETTE
# `[strong X accent]` : un gabarit, pas une liste (X = l'accent voulu)
_ACCENT_RX = re.compile(r"^\[strong [A-Za-zÀ-ÿ' -]{2,30} accent\]$")
_TAG_RX = re.compile(r"\[[^\[\]\n]{1,40}\]")
MAX_TAGS = 4


def is_known(tag: str) -> bool:
    return tag in KNOWN or bool(_ACCENT_RX.match(tag or ""))


def find_tags(text: str) -> list[str]:
    return _TAG_RX.findall(text or "")


def unknown_tags(text: str) -> list[str]:
    return [t for t in find_tags(text) if not is_known(t)]


def strip_tags(text: str) -> str:
    return " ".join(_TAG_RX.sub(" ", text or "").split())


def clamp_style(raw) -> dict:
    """{tags, stability} : balises connues seulement, au plus MAX_TAGS (au-delà
    le modèle les lit comme du texte qui traîne), stabilité snappée sur les
    trois valeurs que v3 accepte (0 / 0,5 / 1 — `clamp_voice_settings`)."""
    raw = raw if isinstance(raw, dict) else {}
    tags = [t for t in (raw.get("tags") or [])
            if isinstance(t, str) and is_known(t)][:MAX_TAGS]
    try:
        s = float(raw.get("stability", 0.5))
    except (TypeError, ValueError):
        s = 0.5
    return {"tags": tags,
            "stability": min((0.0, 0.5, 1.0), key=lambda v: abs(v - s))}


def apply_style(text: str, style: dict | None) -> str:
    """Préfixe les balises du style — sauf si le texte commence déjà par une :
    l'auteur a dirigé lui-même, on n'empile pas une seconde direction."""
    t = (text or "").strip()
    st = clamp_style(style)
    if not st["tags"] or _TAG_RX.match(t):
        return t
    return " ".join(st["tags"]) + " " + t
