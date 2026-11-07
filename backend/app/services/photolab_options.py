# -*- coding: utf-8 -*-
"""t415 (Photolab N5, photocraft 0.21) — options d'historique et de lecture des actions.

Le moteur `serve` ne garde pas ces réglages d'un démarrage à l'autre : ils vivent dans
`<données>/photolab/options_moteur.json`, sont vérifiés clé par clé, et rejoués à chaque démarrage du moteur
(SessionMoteur._preparer). `allowNonLinearHistory` reste fermée : le panneau Historique saute par annulations
successives, ce qu'un historique non linéaire contredirait."""
import json
import os
import tempfile
from pathlib import Path

DEFAUTS = {"premierInstantane": True, "instantaneEnregistrement": False, "visibiliteAnnulable": True,
           "dialogueInstantane": False, "actionUnEtat": True}
VERS_MOTEUR = {"premierInstantane": "automaticallyCreateFirstSnapshot", "instantaneEnregistrement": "automaticallyCreateNewSnapshotWhenSaving",
               "visibiliteAnnulable": "makeLayerVisibilityChangesUndoable", "dialogueInstantane": "showNewSnapshotDialogByDefault"}


def chemin() -> Path:
    from app.config import DATA_ROOT
    return Path(DATA_ROOT) / "photolab" / "options_moteur.json"


def valider(corps) -> dict:
    """Les clés connues, en booléens ; sinon ValueError."""
    if not isinstance(corps, dict):
        raise ValueError("options : objet attendu")
    for k, v in corps.items():
        if k not in DEFAUTS:
            raise ValueError(f"options : clé inconnue : {k}")
        if not isinstance(v, bool):
            raise ValueError(f"options : {k} : booléen attendu")
    return dict(corps)


def lire() -> dict:
    """Le fichier, complété par les défauts ; illisible ou abîmé : les défauts."""
    try:
        return {**DEFAUTS, **valider(json.loads(chemin().read_text(encoding="utf-8")))}
    except (OSError, ValueError):
        return dict(DEFAUTS)


def ecrire(options: dict) -> dict:
    o = {**DEFAUTS, **valider(options)}
    f = chemin()
    f.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=f.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as h:
        json.dump(o, h, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, f)
    return o


def etapes(options: dict) -> list:
    """Les étapes `batch` qui posent ces options dans le moteur."""
    return [{"command": "history.options", "params": {VERS_MOTEUR[k]: options[k] for k in VERS_MOTEUR}},
            {"command": "actions.setHistory", "params": {"singleState": options["actionUnEtat"]}}]


def en_place() -> bool:
    """Vrai si l'utilisateur a réglé quelque chose : sans fichier, le moteur démarre tel quel."""
    return chemin().is_file()
