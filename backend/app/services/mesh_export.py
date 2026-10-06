# -*- coding: utf-8 -*-
"""Emmener la pièce dans un moteur (tâche T093, plan etabli-p4-p5 tâches 4 à 6).

Ce ne sont pas des cibles réseau : ce sont des formats et des conventions d'import. Le défaut est le glTF standard
(.glb, Y en haut, 1 unité = 1 mètre) pour les quatre : leurs importeurs convertissent eux-mêmes vers leur repère,
et pré-cuire la conversion produirait un modèle tourné deux fois. Ce que ce module apporte : le bon format, une
échelle déclarée, la FICHE qui dit ce que le moteur fera, le geste « ouvrir » qui existe vraiment pour chaque
éditeur, et le dépôt dans le projet.

LE CHEMIN EST CELUI DU SERVEUR, JAMAIS CELUI DE LA PAGE. Le plan prenait un `chemin` dans le corps des routes
« ouvrir » et « déposer » : le premier le collait dans du Python exécuté par Blender (`--python-expr`), le second
copiait n'importe quel fichier dans un projet. Ici, (job, version, cible) suffisent : le chemin est recalculé
(`chemin_export`), il vit sous `exports/` du job, et il passe par repr() avant d'entrer dans du Python.

Le FBX n'est jamais ÉCRIT ici : format fermé d'Autodesk. Il n'est signalé que là où un fournisseur l'a livré.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

CIBLES: dict[str, dict] = {
    "blender": {
        "nom": "Blender 4", "format": "glb", "axe_haut": "Y", "echelle": 1.0,
        "note": "Import natif (Fichier › Importer › glTF 2.0) : l'importeur convertit toujours lui-même le Y-up de "
                "glTF vers le Z-up de Blender, et 1 unité = 1 mètre tant que l'échelle d'unité de la scène vaut 1. "
                "Le fichier est donc livré en glTF standard, sans rotation pré-cuite.",
    },
    "godot": {
        "nom": "Godot 4", "format": "glb", "axe_haut": "Y", "echelle": 1.0,
        "note": "Godot est Y-up et compte en mètres, comme glTF : rien à convertir. Un .glb posé dans le dossier du "
                "projet est importé automatiquement par l'éditeur, au prochain balayage (quand il reprend la main).",
    },
    "unreal": {
        "nom": "Unreal Engine 5", "format": "glb", "axe_haut": "Y", "echelle": 1.0,
        "note": "Unreal importe glTF nativement (Interchange, sans greffon à activer depuis la 5.2) : glisser le "
                "fichier dans le Content Browser, ou Fichier › Importer. Le simple dépôt dans Content/ ne crée un "
                "asset que si l'import automatique (Préférences › Chargement et enregistrement › Auto Reimport) est "
                "réglé pour. Livré en glTF standard (Y en haut, mètres) : si l'objet arrive couché ou à la mauvaise "
                "taille, les options Offset Rotation / Uniform Scale de l'import le règlent.",
    },
    "unity": {
        "nom": "Unity 6", "format": "glb", "axe_haut": "Y", "echelle": 1.0,
        "note": "Unity n'importe pas glTF seul : installer le paquet glTFast (Package Manager › + › Add package by "
                "name › com.unity.cloud.gltfast), qui devient l'importeur des .glb d'Assets/ et convertit le repère "
                "lui-même. Sans lui, le fichier déposé reste inerte.",
    },
}

# Les chemins vivent dans l'environnement (.env), comme SLICER_PATH de print3d : c'est le patron du dépôt pour un
# exécutable local que tout le monde n'a pas. LE DOSSIER DE PROJET est la RACINE du projet (celle qui contient
# Assets/, project.godot ou le .uproject) : le sous-dossier de dépôt s'en déduit, et l'ouverture aussi.
EXE_ENV = {"blender": "BLENDER_PATH", "unity": "UNITY_PATH", "unreal": "UNREAL_PATH", "godot": "GODOT_PATH"}
PROJET_ENV = {"blender": "BLENDER_PROJECT_DIR", "unity": "UNITY_PROJECT_DIR",
              "unreal": "UNREAL_PROJECT_DIR", "godot": "GODOT_PROJECT_DIR"}
# Où déposer dans le projet — un sous-dossier À NOUS, jamais la racine d'Assets/ ou de Content/.
DEPOT = {"blender": (), "unity": ("Assets", "Deepotus"), "unreal": ("Content", "Deepotus"), "godot": ("deepotus",)}
AXES = ("X", "Y", "Z")


def _cible(cible: str) -> dict:
    if cible not in CIBLES:
        raise ValueError(f"cible inconnue : {cible} (attendu {', '.join(sorted(CIBLES))})")
    return CIBLES[cible]


def _job_dir(job: str) -> Path:
    from app.services import mesh_report
    return mesh_report.job_dir(Path(str(job)).name)


def dossier_exports(job: str) -> Path:
    return _job_dir(job) / "exports"


def chemin_export(job: str, version: int, cible: str) -> Path:
    """Le chemin du fichier exporté pour (job, version, cible) — calculé ICI, jamais reçu."""
    c = _cible(cible)
    nom = Path(str(job)).name
    return dossier_exports(job) / f"{nom}_v{int(version)}_{cible}.{c['format']}"


def _fiche_de(chemin: Path) -> Path:
    return chemin.with_name(chemin.stem + ".import.md")


def fbx_disponible(job: str) -> bool:
    """Un FBX n'existe que si un fournisseur (Meshy, Tripo, Rodin) en a livré un."""
    return (_job_dir(job) / "model.fbx").is_file()


def _source(job: str, version: int) -> bytes:
    nom = "model.glb" if int(version) <= 1 else f"model.v{int(version)}.glb"
    p = _job_dir(job) / nom
    if not p.is_file():
        raise FileNotFoundError(f"{Path(str(job)).name}/{nom} introuvable")
    return p.read_bytes()


def _fiche(cible: str, fichier: str, axe: str, echelle: float) -> str:
    c = CIBLES[cible]
    surcharge = ""
    if axe != c["axe_haut"] or float(echelle) != float(c["echelle"]):
        surcharge = (f"\n> **Surcharge explicite appliquée** : axe haut {axe}, échelle ×{echelle:g}. Le défaut de cette "
                     f"cible est {c['axe_haut']}-up à l'échelle 1 : vérifie que l'importeur ne refait pas la "
                     "conversion.\n")
    return (f"# Importer dans {c['nom']}\n\n**Fichier :** `{fichier}`  \n**Format :** {c['format']}  \n"
            f"**Axe haut écrit :** {axe}  \n**Échelle :** ×{echelle:g} (1 unité = 1 mètre)\n\n{c['note']}\n{surcharge}")


def exporter(job: str, version: int, cible: str, *, axe_haut: str | None = None,
             echelle: float | None = None) -> dict:
    """Écrit la pièce prête pour un moteur, et SA fiche (une par cible : la seconde n'écrase pas la première). Les
    surcharges d'axe et d'échelle passent par `mesh_edit.reparer` — aucune seconde arithmétique de matrice."""
    from app.services import mesh_edit
    c = _cible(cible)
    axe = str(axe_haut or c["axe_haut"]).upper()
    if axe not in AXES:
        raise ValueError(f"axe haut « {axe_haut} » — X, Y ou Z")
    ech = float(c["echelle"] if echelle is None else echelle)
    if not ech > 0 or ech != ech or ech == float("inf"):
        raise ValueError(f"échelle « {echelle} » — un nombre fini > 0")
    data = _source(job, version)
    if axe != "Y" or ech != 1.0:
        data = mesh_edit.reparer(data, axe_haut=axe, echelle=ech)
    sortie = chemin_export(job, version, cible)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_bytes(data)
    fiche = _fiche_de(sortie)
    fiche.write_text(_fiche(cible, sortie.name, axe, ech), encoding="utf-8")
    return {"cible": cible, "chemin": str(sortie), "fichier": sortie.name, "bytes": len(data), "axe_haut": axe,
            "echelle": ech, "fiche": str(fiche),
            "url": f"/api/assets/3d/{Path(str(job)).name}/export/{sortie.name}",
            "fbx_disponible": fbx_disponible(job)}


def geste_ouvrir(cible: str) -> str:
    """Ce que « ouvrir » veut dire pour cette cible : Blender ouvre un FICHIER (il l'importe au lancement) ; Unity,
    Unreal et Godot ouvrent leur PROJET, et importent ce qu'on dépose dedans."""
    _cible(cible)
    return "fichier" if cible == "blender" else "projet"


def _lancer(argv: list) -> None:      # pragma: no cover — remplacé au banc
    import subprocess
    subprocess.Popen([str(a) for a in argv])


def _racine_projet(cible: str) -> Path:
    """La racine du projet, prise dans l'environnement et VÉRIFIÉE : un dossier qui n'est pas un projet de ce
    moteur est refusé en le disant (un dépôt dans le mauvais dossier ne se voit que trop tard)."""
    cle = PROJET_ENV[cible]
    brut = os.environ.get(cle, "").strip()
    if not brut:
        raise RuntimeError(f"{cle} n'est pas renseigné — indique dans le .env la racine du projet "
                           f"{CIBLES[cible]['nom']} (aucune valeur par défaut : l'application n'écrit pas hors de ses "
                           "sorties sans qu'on le lui demande).")
    d = Path(brut)
    if not d.is_dir():
        raise RuntimeError(f"{cle} pointe vers un dossier inexistant : {d}")
    if cible == "unity" and not (d / "Assets").is_dir():
        raise RuntimeError(f"{cle} : {d} n'a pas de dossier Assets/ — ce n'est pas la racine d'un projet Unity")
    if cible == "godot" and not (d / "project.godot").is_file():
        raise RuntimeError(f"{cle} : {d} n'a pas de project.godot — ce n'est pas la racine d'un projet Godot")
    if cible == "unreal" and not sorted(d.glob("*.uproject")):
        raise RuntimeError(f"{cle} : {d} n'a pas de fichier .uproject — ce n'est pas la racine d'un projet Unreal")
    return d


def ouvrir(job: str, version: int, cible: str) -> dict:
    _cible(cible)
    cle = EXE_ENV[cible]
    exe = os.environ.get(cle, "").strip()
    if not exe:
        raise RuntimeError(f"{cle} n'est pas renseigné — pose le chemin de l'exécutable dans le .env pour ouvrir "
                           f"{CIBLES[cible]['nom']} d'ici.")
    if cible == "blender":
        fichier = chemin_export(job, version, cible)
        if not fichier.is_file():
            raise RuntimeError("rien d'exporté pour Blender sur cette version — « Préparer » d'abord")
        # repr() : le chemin entre dans du PYTHON ; une apostrophe ne peut pas en sortir
        expr = f"import bpy; bpy.ops.import_scene.gltf(filepath={str(fichier)!r})"
        _lancer([exe, "--python-expr", expr])
        return {"geste": "fichier", "exe": exe, "fichier": fichier.name}
    racine = _racine_projet(cible)
    if cible == "unity":
        argv = [exe, "-projectPath", str(racine)]
    elif cible == "godot":
        argv = [exe, "--editor", "--path", str(racine)]
    else:
        argv = [exe, str(sorted(racine.glob("*.uproject"))[0])]
    _lancer(argv)
    return {"geste": "projet", "exe": exe, "projet": str(racine)}


def _sonder(dossier) -> bool:         # pragma: no cover — remplacé au banc
    from app.services import fs_guard
    return fs_guard.probe_write_visibility(Path(dossier))


def deposer(job: str, version: int, cible: str) -> dict:
    """Copie l'export (et sa fiche) dans le projet du moteur, sous un sous-dossier à nous. SEULE écriture hors de
    `outputs/` du chantier, donc la seule qui a besoin d'une sonde : l'incident MSIX a montré qu'une écriture peut
    sembler réussir en partant dans un overlay invisible."""
    _cible(cible)
    src = chemin_export(job, version, cible)
    racine = _racine_projet(cible)
    if not src.is_file():
        raise RuntimeError(f"rien d'exporté pour {CIBLES[cible]['nom']} sur cette version — « Préparer » d'abord")
    dest = racine.joinpath(*DEPOT[cible])
    dest.mkdir(parents=True, exist_ok=True)
    if not _sonder(dest):
        raise RuntimeError(f"écriture invisible dans {dest} — le processus est virtualisé (MSIX) et le fichier "
                           "n'apparaîtrait pas pour le moteur. Relance l'application hors du conteneur.")
    shutil.copy2(src, dest / src.name)
    fiche = _fiche_de(src)
    if fiche.is_file():
        shutil.copy2(fiche, dest / fiche.name)
    avertissement = None
    if cible == "unity":
        # Unity 6 n'importe PAS un .glb sans glTFast (vérifié le 06/10, manuel Unity « 3D formats ») : sans le
        # paquet, le dépôt réussit et le fichier reste inerte — on le dit au lieu de laisser chercher pourquoi.
        manifeste = racine / "Packages" / "manifest.json"
        if not (manifeste.is_file() and "com.unity.cloud.gltfast" in manifeste.read_text("utf-8", errors="replace")):
            avertissement = ("glTFast n'est pas dans Packages/manifest.json : Unity n'importera pas ce .glb tant que "
                             "le paquet com.unity.cloud.gltfast n'est pas installé")
    return {"chemin": str(dest / src.name), "dossier": str(dest), "visible": True, "avertissement": avertissement}
