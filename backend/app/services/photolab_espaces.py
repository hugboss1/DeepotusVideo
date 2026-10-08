"""Espaces de travail du Photolab (t151, parité L1) : l'état que l'écran garde entre deux sessions.

Un fichier `<données>/photolab/espaces.json` : l'espace actif, le verrou, les dispositions modifiées par espace, les
espaces enregistrés par l'utilisateur. Rien n'y désigne un fichier ni une commande du moteur : ce n'est qu'une
disposition d'écran. La validation est une liste blanche STRICTE (clés, groupes, onglets, bornes) et la copie
JavaScript de ces listes (frontend/photolab/js/mod-espaces.js) est comparée par le banc test_photolab_espaces.
"""
import json
import os
import re
import tempfile
from pathlib import Path

# Groupes de panneaux de l'écran -> leurs onglets (index.html : #grpCouleur, #grpProprietes, #grpPinceaux, #grpCalques,
# #grpInfos — t153).
GROUPES = {
    "couleur": ("couleur", "nuancier", "degrades", "motifs", "formes"),
    "proprietes": ("proprietes", "ajustements", "styles", "compositions"),
    "pinceaux": ("pinceaux", "parametres", "source", "predefinis"),
    "calques": ("calques", "couches", "traces", "historique", "navigateur"),
    "infos": ("histogramme", "infos"),                   # t153 : #grpInfos
    "texte": ("caractere", "paragraphe", "glyphes", "stylesCar", "stylesPar"),       # t156 : #grpTexte
}
# Espaces fournis, dans l'ordre du menu (décision Q1 du 08/10/2026).
FOURNIS = ("essentiel", "base", "graphisme", "mouvement", "peinture", "photo", "pixel")
# Leurs noms, pour refuser un espace personnel qui en porterait un (comparés sans casse ; fr et en).
NOMS_FOURNIS = {"essentiel", "essentials", "base", "basics", "graphisme et web", "graphic and web", "mouvement", "motion",
                "peinture", "painting", "photo", "photography", "pixel art"}
ETATS_GROUPE = ("ouvert", "replie", "masque")
MAX_PERSO = 20
MAX_NOM = 64
_ID_PERSO = re.compile(r"perso-[0-9a-z]{1,12}")
_CLES_ETAT = {"version", "actif", "verrouille", "modifs", "perso"}
_CLES_DISPO = {"colonnes", "outils", "options", "barreOutils", "groupes"}
_CLES_GROUPE = {"id", "etat", "onglet"}
_CLES_PERSO = {"id", "nom", "disposition"}


def etat_defaut() -> dict:
    return {"version": 1, "actif": "essentiel", "verrouille": False, "modifs": {}, "perso": []}


def chemin() -> Path:
    from app.config import DATA_ROOT
    return Path(DATA_ROOT) / "photolab" / "espaces.json"


def _objet(v, cles, ou):
    if not isinstance(v, dict):
        raise ValueError(f"{ou} : objet attendu")
    inconnues = set(v) - cles
    if inconnues:
        raise ValueError(f"{ou} : clé(s) inconnue(s) : {', '.join(sorted(map(str, inconnues)))}")
    manquantes = cles - set(v)
    if manquantes:
        raise ValueError(f"{ou} : clé(s) manquante(s) : {', '.join(sorted(manquantes))}")


def _booleen(v, ou):
    if not isinstance(v, bool):
        raise ValueError(f"{ou} : booléen attendu")


def _disposition(d, ou) -> dict:
    _objet(d, _CLES_DISPO, ou)
    if d["colonnes"] not in (1, 2) or isinstance(d["colonnes"], bool):
        raise ValueError(f"{ou}.colonnes : 1 ou 2")
    if d["outils"] not in ("tous", "base"):
        raise ValueError(f"{ou}.outils : « tous » ou « base »")
    _booleen(d["options"], f"{ou}.options")
    _booleen(d["barreOutils"], f"{ou}.barreOutils")
    if not isinstance(d["groupes"], list):
        raise ValueError(f"{ou}.groupes : liste attendue")
    vus = set()
    for i, g in enumerate(d["groupes"]):
        o = f"{ou}.groupes[{i}]"
        _objet(g, _CLES_GROUPE, o)
        if g["id"] not in GROUPES:
            raise ValueError(f"{o}.id : groupe inconnu : {g['id']!r}")
        if g["id"] in vus:
            raise ValueError(f"{o}.id : groupe en double : {g['id']}")
        vus.add(g["id"])
        if g["etat"] not in ETATS_GROUPE:
            raise ValueError(f"{o}.etat : {'|'.join(ETATS_GROUPE)}")
        if g["onglet"] not in GROUPES[g["id"]]:
            raise ValueError(f"{o}.onglet : {g['onglet']!r} n'est pas un onglet du groupe {g['id']}")
    return d


def valider(obj) -> dict:
    """L'état tel quel (noms rendus sans espaces autour) s'il est admis ; sinon ValueError (message français)."""
    _objet(obj, _CLES_ETAT, "état")
    if obj["version"] != 1 or isinstance(obj["version"], bool):
        raise ValueError("état.version : 1 attendu")
    _booleen(obj["verrouille"], "état.verrouille")
    if not isinstance(obj["perso"], list):
        raise ValueError("état.perso : liste attendue")
    if len(obj["perso"]) > MAX_PERSO:
        raise ValueError(f"état.perso : {MAX_PERSO} espaces personnels au plus")
    ids, noms = set(), set()
    for i, p in enumerate(obj["perso"]):
        o = f"état.perso[{i}]"
        _objet(p, _CLES_PERSO, o)
        if not isinstance(p["id"], str) or not _ID_PERSO.fullmatch(p["id"]):
            raise ValueError(f"{o}.id : mal formé")
        if p["id"] in ids:
            raise ValueError(f"{o}.id : en double")
        ids.add(p["id"])
        if not isinstance(p["nom"], str):
            raise ValueError(f"{o}.nom : texte attendu")
        nom = p["nom"].strip()
        if not nom or len(nom) > MAX_NOM or any(ord(c) < 32 for c in nom):
            raise ValueError(f"{o}.nom : 1 à {MAX_NOM} caractères, sur une ligne")
        if nom.casefold() in NOMS_FOURNIS or nom.casefold() in noms:
            raise ValueError(f"{o}.nom : déjà pris : {nom}")
        noms.add(nom.casefold())
        p["nom"] = nom
        _disposition(p["disposition"], f"{o}.disposition")
    connus = set(FOURNIS) | ids
    if obj["actif"] not in connus:
        raise ValueError(f"état.actif : espace inconnu : {obj['actif']!r}")
    if not isinstance(obj["modifs"], dict):
        raise ValueError("état.modifs : objet attendu")
    for k, d in obj["modifs"].items():
        if k not in connus:
            raise ValueError(f"état.modifs : espace inconnu : {k!r}")
        _disposition(d, f"état.modifs.{k}")
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
    fd, tmp = tempfile.mkstemp(prefix="espaces-", suffix=".tmp", dir=f.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as h:
            json.dump(etat, h, ensure_ascii=False, indent=1)
        os.replace(tmp, f)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return etat
