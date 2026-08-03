# -*- coding: utf-8 -*-
"""Détection de la virtualisation filesystem (MSIX / AppContainer).

Incident de référence (14/06 → 20/07/2026) : le backend relancé depuis le
shell d'une session Claude (application empaquetée MSIX) hérite du conteneur.
Windows dévie alors ses écritures AppData vers un overlay
``Packages\\<pkg>\\LocalCache\\Local`` **invisible de l'énumération du vrai
dossier** : chaque image générée, render ou écriture DB forke silencieusement
(~1,3 Go d'assets + deepotus.db divergés). Symptôme utilisateur : « l'image
générée n'est pas sauvegardée dans la Librairie ».

Le garde écrit un canari dans le dossier images, vérifie qu'il apparaît dans
l'énumération du même dossier, puis le supprime. Si le canari n'apparaît pas,
le processus est virtualisé : ses écritures ne sont pas dans le monde réel.

Appelé une fois au démarrage (main.py) ; le résultat est exposé par
GET /api/health sous ``fs_virtualized`` et vérifié par la sonde de
déploiement (scripts/dz_postdeploy_probe.ps1).
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

logger = logging.getLogger("deepotus.fs_guard")

# None = pas encore sondé ; sinon résultat du check de démarrage.
_VIRTUALIZED: bool | None = None


def probe_write_visibility(folder: Path) -> bool:
    """True si un fichier écrit dans `folder` apparaît dans son énumération.

    Un échec d'écriture (dossier absent, permission) est traité comme
    « visible » : le garde cible spécifiquement la redirection MSIX, pas les
    erreurs disque génériques (qui, elles, remontent ailleurs).
    """
    try:
        folder.mkdir(parents=True, exist_ok=True)
        canary = folder / f".dz_fsguard_{uuid.uuid4().hex[:12]}.tmp"
        canary.write_text("canary", encoding="utf-8")
        try:
            seen = canary.name in {p.name for p in folder.iterdir()}
        finally:
            try:
                canary.unlink()
            except OSError:
                pass
        return seen
    except OSError as e:
        logger.warning(f"fs_guard probe skipped (write failed): {e}")
        return True


def startup_check(folder: Path) -> bool:
    """Sonde `folder`, mémorise et journalise. Retourne True si virtualisé."""
    global _VIRTUALIZED
    _VIRTUALIZED = not probe_write_visibility(folder)
    if _VIRTUALIZED:
        logger.error(
            "=" * 60 + "\n"
            "FS VIRTUALISÉ : ce backend tourne dans un conteneur (MSIX). Ses "
            "écritures partent dans un overlay LocalCache invisible — images "
            "et renders sembleront « non sauvegardés ». Fermer ce processus "
            "et relancer via scripts\\launch-silent.vbs HORS conteneur "
            "(double-clic Explorer, pas depuis un shell d'agent).\n" + "=" * 60
        )
    return _VIRTUALIZED


def is_virtualized() -> bool:
    """Résultat du check de démarrage (False si jamais sondé)."""
    return bool(_VIRTUALIZED)
