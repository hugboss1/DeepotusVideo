# -*- coding: utf-8 -*-
"""t514 (RV4, 26/11/2026) — FICHE D'OFFRE d'un espace de marque (décision R5 du 13/11).

Spec 2026-11-13-reel-reference-design.md § 3.4 point 1 : produit ou service, pour qui, promesse, deux ou trois preuves
VRAIES, frein levé (essai, garantie), appel(s) à l'action autorisé(s), chiffres publiables (valeur, libellé, source).
Sans fiche, la réécriture d'une recette s'arrête et la demande. Les chiffres publiables sont la seule source des
nombres qu'un script peut écrire sans la mention « valeur d'illustration » (R8, `script_court.controler_verite`).

Fichier `DATA_ROOT/espaces/<id>/offre.json` (liste blanche `espaces.FICHIERS`). Écriture locale seulement.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from app.services import espaces

MAX = {"produit": 200, "pour_qui": 300, "promesse": 400, "frein_leve": 300}
MAX_PREUVES = 5
MAX_APPELS = 5
MAX_CHIFFRES = 12
APPELS_PERMIS = ("lien", "commentaire", "abonnement", "message", "achat")
VIDE = {"produit": "", "pour_qui": "", "promesse": "", "preuves": [], "frein_leve": "", "appels": ["lien"],
        "chiffres": [], "maj": ""}


def _t(v, n: int) -> str:
    return " ".join(str(v if v is not None else "").split())[:n]


def normaliser(champs: dict) -> dict:
    """Une fiche saisie -> la fiche gardée (bornes, appels permis seulement ; un chiffre sans source est refusé)."""
    c = champs if isinstance(champs, dict) else {}
    preuves = [_t(x, 300) for x in (c.get("preuves") if isinstance(c.get("preuves"), list) else []) if _t(x, 300)]
    appels = [a for a in (c.get("appels") if isinstance(c.get("appels"), list) else []) if a in APPELS_PERMIS]
    chiffres = []
    for x in (c.get("chiffres") if isinstance(c.get("chiffres"), list) else [])[:MAX_CHIFFRES]:
        if not isinstance(x, dict):
            continue
        v, lib, src = _t(x.get("valeur"), 40), _t(x.get("libelle"), 160), _t(x.get("source"), 300)
        if not v:
            continue
        if not src:
            raise ValueError("Chaque chiffre publiable a besoin de sa source (où le vérifier).")
        chiffres.append({"valeur": v, "libelle": lib, "source": src})
    return {**{k: _t(c.get(k), n) for k, n in MAX.items()}, "preuves": preuves[:MAX_PREUVES],
            "appels": list(dict.fromkeys(appels))[:MAX_APPELS] or ["lien"], "chiffres": chiffres}


def complete(fiche: dict) -> bool:
    """Assez pour écrire un script : produit, promesse et au moins une preuve."""
    return bool(fiche.get("produit") and fiche.get("promesse") and fiche.get("preuves"))


def lire(eid: str) -> dict:
    f = espaces.chemin(eid, "offre.json")
    if f is None or eid not in espaces.lire()["espaces"]:
        raise KeyError(eid)
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(VIDE)
    return {**VIDE, **d} if isinstance(d, dict) else dict(VIDE)


def ecrire(eid: str, champs: dict) -> dict:
    f = espaces.chemin(eid, "offre.json")
    if f is None or eid not in espaces.lire()["espaces"]:
        raise KeyError(eid)
    fiche = {**normaliser(champs), "maj": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(fiche, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, f)
    return fiche
