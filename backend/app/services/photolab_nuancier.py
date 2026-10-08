"""Nuancier du Photolab (t153, parité L3) : les groupes de nuances que l'écran garde entre deux sessions.

Le moteur n'a aucune commande de nuancier (l'amont garde ses 40 nuances en dur dans l'interface) : la liste est une
donnée Deepotus, dans `<données>/photolab/nuancier.json`. Une nuance n'est qu'une couleur `#rrggbb` et un nom
facultatif ; choisir une nuance passe par `tools.setColors` (route /executer), jamais par ce fichier. Validation en
liste blanche STRICTE ; la copie JavaScript du défaut (frontend/photolab/js/mod-nuancier.js) est comparée par le banc
test_photolab_panneaux3.
"""
import json
import os
import re
import tempfile
from pathlib import Path

# Les 40 nuances de l'amont (photocraft ui-egui panels.rs, SWATCHES : 4 rangées de 10), en quatre groupes.
DEFAUT_GROUPES = (
    ("gris", ("#000000", "#1a1a1a", "#333333", "#4d4d4d", "#666666", "#808080", "#999999", "#b3b3b3", "#cccccc", "#ffffff")),
    ("pastels", ("#ec8080", "#f4b084", "#fae080", "#d6f080", "#96e896", "#80e8c8", "#80dcf0", "#80b0f4", "#a890f4", "#e890e8")),
    ("vives", ("#e62828", "#f5781e", "#fad21e", "#a0dc28", "#28c850", "#1ec8aa", "#1eaae6", "#2864e6", "#7846dc", "#d232b4")),
    ("foncees", ("#781414", "#823c0a", "#826e0a", "#507814", "#146428", "#0a645a", "#0a5078", "#143278", "#3c1e6e", "#6e145a")),
)
MAX_GROUPES = 40
MAX_NUANCES = 400            # par groupe
MAX_RECENTES = 12
MAX_NOM = 64
_HEX = re.compile(r"#[0-9a-f]{6}")
_ID_GROUPE = re.compile(r"(gris|pastels|vives|foncees|g-[0-9a-z]{1,12})")
_CLES_ETAT = {"version", "groupes", "recentes"}
_CLES_GROUPE = {"id", "nom", "couleurs"}
_CLES_NUANCE = {"hex", "nom"}


def etat_defaut() -> dict:
    """Groupes fournis : `nom` vide = nom traduit par l'écran (photolab.nuancier.groupe_<id>)."""
    return {"version": 1, "recentes": [],
            "groupes": [{"id": i, "nom": "", "couleurs": [{"hex": h, "nom": ""} for h in c]} for i, c in DEFAUT_GROUPES]}


def chemin() -> Path:
    from app.config import DATA_ROOT
    return Path(DATA_ROOT) / "photolab" / "nuancier.json"


def _objet(v, cles, ou):
    if not isinstance(v, dict):
        raise ValueError(f"{ou} : objet attendu")
    inconnues = set(v) - cles
    if inconnues:
        raise ValueError(f"{ou} : clé(s) inconnue(s) : {', '.join(sorted(map(str, inconnues)))}")
    manquantes = cles - set(v)
    if manquantes:
        raise ValueError(f"{ou} : clé(s) manquante(s) : {', '.join(sorted(manquantes))}")


def _hex(v, ou):
    if not isinstance(v, str) or not _HEX.fullmatch(v):
        raise ValueError(f"{ou} : couleur « #rrggbb » (minuscules) attendue")


def _nom(v, ou, vide_admis):
    if not isinstance(v, str):
        raise ValueError(f"{ou} : texte attendu")
    n = v.strip()
    if (not n and not vide_admis) or len(n) > MAX_NOM or any(ord(c) < 32 for c in n):
        raise ValueError(f"{ou} : {0 if vide_admis else 1} à {MAX_NOM} caractères, sur une ligne")
    return n


def valider(obj) -> dict:
    """L'état tel quel (noms rendus sans espaces autour) s'il est admis ; sinon ValueError (message français)."""
    _objet(obj, _CLES_ETAT, "nuancier")
    if obj["version"] != 1 or isinstance(obj["version"], bool):
        raise ValueError("nuancier.version : 1 attendu")
    if not isinstance(obj["recentes"], list) or len(obj["recentes"]) > MAX_RECENTES:
        raise ValueError(f"nuancier.recentes : liste de {MAX_RECENTES} couleurs au plus")
    for i, h in enumerate(obj["recentes"]):
        _hex(h, f"nuancier.recentes[{i}]")
    if not isinstance(obj["groupes"], list) or len(obj["groupes"]) > MAX_GROUPES:
        raise ValueError(f"nuancier.groupes : liste de {MAX_GROUPES} groupes au plus")
    ids = set()
    for i, g in enumerate(obj["groupes"]):
        o = f"nuancier.groupes[{i}]"
        _objet(g, _CLES_GROUPE, o)
        if not isinstance(g["id"], str) or not _ID_GROUPE.fullmatch(g["id"]):
            raise ValueError(f"{o}.id : mal formé")
        if g["id"] in ids:
            raise ValueError(f"{o}.id : en double")
        ids.add(g["id"])
        # Un groupe fourni peut garder un nom vide (traduit par l'écran) ; un groupe créé porte un nom.
        g["nom"] = _nom(g["nom"], f"{o}.nom", vide_admis=not g["id"].startswith("g-"))
        if not isinstance(g["couleurs"], list) or len(g["couleurs"]) > MAX_NUANCES:
            raise ValueError(f"{o}.couleurs : liste de {MAX_NUANCES} nuances au plus")
        for j, n in enumerate(g["couleurs"]):
            on = f"{o}.couleurs[{j}]"
            _objet(n, _CLES_NUANCE, on)
            _hex(n["hex"], f"{on}.hex")
            n["nom"] = _nom(n["nom"], f"{on}.nom", vide_admis=True)
    return obj


def lire() -> dict:
    """L'état enregistré ; le défaut si le fichier manque, est illisible ou refusé (jamais d'exception)."""
    try:
        return valider(json.loads(chemin().read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, AttributeError):
        return etat_defaut()


def ecrire(obj) -> dict:
    """Valide puis écrit d'un seul tenant (fichier temporaire du même dossier puis os.replace)."""
    etat = valider(obj)
    f = chemin()
    f.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="nuancier-", suffix=".tmp", dir=f.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as h:
            json.dump(etat, h, ensure_ascii=False, indent=1)
        os.replace(tmp, f)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return etat
