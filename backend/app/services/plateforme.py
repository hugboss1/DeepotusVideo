"""t535 (20/11/2026) — couche hébergée, pièce ⑥ : les outils réservés à Windows, grisés ailleurs.

Plan docs/superpowers/plans/2026-11-20-couche-hebergee-vps.md. Sur le VPS (Linux), certains outils n'ont pas de
binaire ou pas de sens : leur état les dit indisponibles (l'écran les grise) et leurs gestes lèvent `ReserveWindows`,
un `Refus` traduit que main.py rend en 501 dans la langue de la requête — jamais un 500, jamais un processus lancé.

  photolab  photocraft-cli / photocraft.exe : build Windows seulement (sauf PHOTOCRAFT_CLI désigné)
  clip      l'installeur télécharge des roues win_amd64 figées
  slicer    os.startfile, et un slicer lancé sur un SERVEUR n'ouvre rien chez l'utilisateur
  tts       les Saved Objects de Tabletop Simulator vivent dans les Documents de Windows

Hors liste : le scan OCR se dégrade seul (503 + secours Claude), Blender MCP et les logiciels 3D se disent « absent ».
"""
import os

from app import i18n

OUTILS = ("photolab", "clip", "slicer", "tts")


def windows() -> bool:
    return os.name == "nt"


def _exempte(outil: str) -> bool:
    """Un outil rendu possible sous Linux par un réglage explicite (un photocraft-cli Linux désigné)."""
    return outil == "photolab" and bool(os.environ.get("PHOTOCRAFT_CLI", "").strip())


def disponible(outil: str) -> bool:
    return windows() or _exempte(outil)


def message(outil: str) -> i18n.Message:
    return i18n.Message("plateforme.windows_seul", outil=i18n.Message(f"plateforme.outil.{outil}"))


class ReserveWindows(i18n.Refus):
    """Un geste d'un outil réservé à Windows, demandé ailleurs : 501 traduit (gestionnaire de main.py)."""

    def __init__(self, outil: str):
        self.outil = outil
        super().__init__("plateforme.windows_seul", outil=i18n.Message(f"plateforme.outil.{outil}"))


def exiger(outil: str) -> None:
    if not disponible(outil):
        raise ReserveWindows(outil)


def etat(lang: str | None = None) -> dict:
    return {"windows": windows(),
            "indisponibles": {o: message(o).dans(lang) for o in OUTILS if not disponible(o)}}
