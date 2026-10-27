# -*- coding: utf-8 -*-
"""t311 (27/10/2026) — lecture BRUTE d'un espace : persona, mots interdits, archivage, sans `espaces.lire()`.

`espaces.persona()` passe par `espaces.lire()`, qui migre et écrit (piège t210) : une boucle de fond ou un outil d'agent
qui l'appelle peut migrer en parallèle d'une requête (WinError 32). Ici : lecture seule, aucune écriture, aucun mkdir,
aucun import-et-appel de `espaces.lire()` / `espaces.persona()`. L'id est validé par `espaces.id_valide`. Un fichier
absent ou illisible retombe sur le persona livré (espace `deepotus`) ou sur les défauts.
La formule des mots interdits est celle de `contenus_espace._interdits`.
"""
from __future__ import annotations

import json

from app import config
from app.services import espaces


def _brut(chemin):
    """Le JSON du fichier ; None s'il est absent ou illisible."""
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def persona(eid: str) -> dict:
    """Le persona de l'espace tel que sur disque, complété EN MÉMOIRE par `PERSONA_DEFAUTS`. KeyError : id invalide."""
    if not espaces.id_valide(eid):
        raise KeyError(f"espace inconnu : {str(eid)[:40]}")
    doc = _brut(config.DATA_ROOT / "espaces" / eid / "persona.json")
    if not isinstance(doc, dict):
        doc = _brut(espaces.PERSONA_LIVRE) if eid == "deepotus" else None
        if not isinstance(doc, dict):
            doc = {}
    out = json.loads(json.dumps(doc))
    for k, v in espaces.PERSONA_DEFAUTS.items():
        out.setdefault(k, json.loads(json.dumps(v)))
    out.setdefault("persona_id", eid)
    return out


def interdits(eid: str) -> list[str]:
    """Les mots interdits de l'espace (même formule que `contenus_espace._interdits`)."""
    p = persona(eid)
    vis, ec = p.get("visuel") or {}, p.get("ecran") or {}
    inter = vis.get("interdits") or {}
    mots = list(inter.get("sujets") or []) + list(ec.get("banned") or []) + list(inter.get("concurrents") or [])
    return [m.strip().lower() for m in mots if isinstance(m, str) and len(m.strip()) > 1]


def archive(eid: str) -> bool:
    """L'espace est-il archivé ? False s'il est inconnu ou si espaces.json est absent ou illisible."""
    if not espaces.id_valide(eid):
        return False
    doc = _brut(config.DATA_ROOT / "espaces" / "espaces.json")
    e = ((doc or {}).get("espaces") or {}).get(eid) if isinstance(doc, dict) else None
    return bool(isinstance(e, dict) and e.get("archive"))
