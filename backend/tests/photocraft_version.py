# -*- coding: utf-8 -*-
"""t250 (Photolab M1) — la version ÉPINGLÉE du moteur, lue dans vendor/photocraft.json, et le registre de ses commandes
capturé du vrai binaire (tests/photocraft_commandes_<version>.json). Les bancs passent par ici au lieu d'écrire
« 0.3.0 » en dur : une montée de version ne change que le manifeste et ajoute le registre capturé."""
import json, pathlib

BACKEND = pathlib.Path(__file__).resolve().parent.parent
RACINE = BACKEND.parent
MANIFESTE = json.loads((RACINE / "vendor" / "photocraft.json").read_text(encoding="utf-8"))
VERSION = MANIFESTE["version"]


def fichier_commandes(version: str = VERSION) -> pathlib.Path:
    return BACKEND / "tests" / f"photocraft_commandes_{version}.json"


def commandes(version: str = VERSION) -> list:
    return json.loads(fichier_commandes(version).read_text(encoding="utf-8"))
