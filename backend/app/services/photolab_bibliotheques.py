# -*- coding: utf-8 -*-
"""t416 (Photolab N6, photocraft 0.21) — bibliothèques importées : styles .asl et formes .csh.

Le moteur `serve` ne garde rien d'un démarrage à l'autre : les fichiers importés vivent dans
`<données>/photolab/bibliotheques.json` et sont rejoués à chaque démarrage (SessionMoteur._poser_options). Ils arrivent en
`data` (base64), jamais par un chemin ; les commandes du moteur restent fermées à /executer. Supprimer un groupe du panneau
retire aussi son fichier de la réserve (SUPPRESSIONS)."""
import base64
import binascii
import json
import os
import tempfile
from pathlib import Path

GENRES = {"styles": "style.presets.importAsl", "formes": "shape.presets.importCsh"}
SUPPRESSIONS = {"style.presets.edit": "styles", "shape.presets.edit": "formes"}
MAX_OCTETS = 20_000_000
MAX_FICHIERS = 64
MAX_NOM = 64


def chemin() -> Path:
    from app.config import DATA_ROOT
    return Path(DATA_ROOT) / "photolab" / "bibliotheques.json"


def valider(genre, data, groupe) -> tuple:
    """-> (genre, data, groupe) ; sinon ValueError."""
    if genre not in GENRES:
        raise ValueError(f"bibliothèque : genre inconnu : {genre!r}")
    if not isinstance(groupe, str) or not groupe.strip() or len(groupe) > MAX_NOM:
        raise ValueError(f"bibliothèque : nom de groupe de 1 à {MAX_NOM} caractères")
    if not isinstance(data, str) or not data:
        raise ValueError("bibliothèque : contenu du fichier attendu")
    if len(data) > MAX_OCTETS * 4 // 3 + 4:
        raise ValueError("bibliothèque : fichier trop lourd")
    try:
        base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("bibliothèque : contenu illisible")
    return genre, data, groupe.strip()


def lire() -> list:
    try:
        l = json.loads(chemin().read_text(encoding="utf-8"))
        return [e for e in l if isinstance(e, dict) and e.get("genre") in GENRES and isinstance(e.get("data"), str)
                and isinstance(e.get("groupe"), str)] if isinstance(l, list) else []
    except (OSError, ValueError):
        return []


def _ecrire(liste: list):
    f = chemin()
    f.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=f.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as h:
        json.dump(liste, h, ensure_ascii=False)
    os.replace(tmp, f)


def ajouter(genre, data, groupe):
    """Un même groupe se remplace ; les plus anciens sortent au-delà de MAX_FICHIERS."""
    l = [e for e in lire() if not (e["genre"] == genre and e["groupe"] == groupe)]
    _ecrire((l + [{"genre": genre, "groupe": groupe, "data": data}])[-MAX_FICHIERS:])


def retirer(genre, groupe):
    l = lire()
    n = [e for e in l if not (e["genre"] == genre and e["groupe"] == groupe)]
    if len(n) != len(l):
        _ecrire(n)


def renommer(genre, groupe, nom):
    l = lire()
    for e in l:
        if e["genre"] == genre and e["groupe"] == groupe:
            e["groupe"] = nom
            _ecrire(l)
            return


def apres_edition(cid, params):
    """Le panneau a supprimé ou renommé un groupe : le prochain démarrage le rejoue tel quel."""
    genre = SUPPRESSIONS.get(cid)
    if not genre or not isinstance(params, dict) or not isinstance(params.get("group"), str):
        return
    if params.get("action") == "deleteGroup":
        retirer(genre, params["group"])
    elif params.get("action") == "renameGroup" and isinstance(params.get("name"), str):
        renommer(genre, params["group"], params["name"])


def etape(genre, data, groupe) -> dict:
    return {"command": GENRES[genre], "params": {"data": data, "group": groupe}}


def etapes() -> list:
    return [etape(e["genre"], e["data"], e["groupe"]) for e in lire()]
