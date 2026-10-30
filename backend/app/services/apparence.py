# -*- coding: utf-8 -*-
"""Réglages › Apparence : la PALETTE de l'application (t382, lot « Réglages : chemins & apparence », 30/10/2026, plan
docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md, décision D5 : globale à l'app,
préréglages + palette libre).

L'état vit dans DATA_ROOT/apparence.json. Le serveur fait foi : l'app s'ouvre sur 127.0.0.1 ou sur deepotus.localhost,
deux origines qui n'ont pas le même localStorage. L'écran (frontend/shared/dz-apparence.js) garde un cache local pour
peindre avant le premier rendu, puis relit ici.

Un état : {"preset": "sombre" | "clair" | "contraste" | "deeplab"} ou {"preset": "libre", "couleurs": {six jetons
"#rrggbb"}, "fort": true facultatif}. Les couleurs des préréglages et tout ce qui s'en dérive (encres, bordures,
surfaces, contrôles de contraste) vivent dans l'écran : le serveur ne garde que le choix.
"""
from __future__ import annotations

import json
import os
import re
import tempfile

from app.config import DATA_ROOT

PRESETS = ("sombre", "clair", "contraste", "deeplab")
JETONS = ("fond", "panneau", "texte", "accent", "succes", "erreur")
DEFAUT = {"preset": "sombre"}
_HEX = re.compile(r"^#[0-9a-f]{6}$")


def _fichier():
    return DATA_ROOT / "apparence.json"


def normaliser(corps) -> dict:
    """L'état gardé, ou ValueError. Rien d'inconnu ne passe."""
    if not isinstance(corps, dict):
        raise ValueError("Palette illisible : un objet {preset, couleurs} est attendu")
    preset = corps.get("preset")
    if preset in PRESETS:
        return {"preset": preset}
    if preset != "libre":
        raise ValueError(f"Préréglage inconnu : {preset}")
    couleurs = corps.get("couleurs")
    if not isinstance(couleurs, dict):
        raise ValueError("Palette libre : les six couleurs sont attendues")
    trop = sorted(set(couleurs) - set(JETONS))
    if trop:
        raise ValueError(f"Couleur inconnue : {', '.join(map(str, trop))}")
    propres = {}
    for j in JETONS:
        v = couleurs.get(j)
        if not isinstance(v, str) or not _HEX.match(v.lower()):
            raise ValueError(f"Couleur manquante ou illisible : {j} (#rrggbb attendu)")
        propres[j] = v.lower()
    fort = corps.get("fort", False)
    if not isinstance(fort, bool) and fort not in (0, 1):
        raise ValueError("« fort » doit valoir vrai ou faux")
    etat = {"preset": "libre", "couleurs": propres}
    if fort is True:
        etat["fort"] = True
    return etat


def lire() -> dict:
    """L'état gardé ; absent, illisible ou invalide : Deepotus sombre."""
    try:
        return normaliser(json.loads(_fichier().read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return dict(DEFAUT)


def ecrire(corps) -> dict:
    etat = normaliser(corps)
    f = _fichier()
    f.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".apparence-", suffix=".json", dir=str(f.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as h:
            json.dump(etat, h, ensure_ascii=False)
        os.replace(tmp, f)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return etat
