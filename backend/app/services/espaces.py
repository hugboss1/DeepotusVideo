# -*- coding: utf-8 -*-
"""t200 (Espaces de marque E0, 13/10/2026) — PLUSIEURS espaces de marque sur une instance.

Un espace = une marque ou un projet (Deepotus, Rippled, un client) : un nom, une couleur, un kit de marque par
defaut, et un dossier `DATA_ROOT/espaces/<id>/` qui porte son `persona.json` (persona v2 en t201) et son
`contenus.json` (modeles de prompt Quick, categories, ingredients du generateur, vibes — t207). Les comptes de
diffusion (t203), les posts (t204) et les depenses (t209) s'y rattacheront par l'id.

Un espace ACTIF a la fois, comme le kit actif ; activer un espace active son kit.
Migration : au premier appel, l'existant devient l'espace `deepotus` A L'OCTET (persona livre, liste Quick actuelle
tiree de prompts.jsx par scripts/espaces/extraire_contenus_deepotus.mjs, kit `deepotus`). Un fichier deja present
n'est jamais ecrase. Un `espaces.json` ILLISIBLE est mis de cote (`espaces.json.illisible-<horodatage>`), jamais
ecrase en silence. Stockage hors du dossier d'installation : une mise a jour n'y touche pas.
"""
from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger

from app.config import DATA_ROOT
from app.services import brand_kits

MAX = 60
MAX_ESPACES = 50
FICHIERS = ("persona.json", "contenus.json")
_ICI = Path(__file__).resolve().parent.parent
PERSONA_LIVRE = _ICI / "personas" / "deepotus.json"
GRAINE_DEEPOTUS = _ICI / "espaces" / "deepotus_contenus.json"
CONTENUS_VIDES = {"version": 1, "prompt_templates": [], "prompt_cats": [], "ingredients": {}, "vibes": []}
_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def dossier() -> Path:
    p = DATA_ROOT / "espaces"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _fichier() -> Path:
    return dossier() / "espaces.json"


def id_valide(eid) -> bool:
    return isinstance(eid, str) and bool(_ID.match(eid))


def chemin(eid, nom: str) -> Path | None:
    """Le fichier `nom` de l'espace `eid`, ou None si l'id ou le nom sortent de la liste blanche (jamais de ../)."""
    if not id_valide(eid) or nom not in FICHIERS:
        return None
    return dossier() / eid / nom


def _ecrire_json(f: Path, doc) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _migrer() -> dict:
    d = dossier() / "deepotus"
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "persona.json").exists():
        shutil.copyfile(PERSONA_LIVRE, d / "persona.json")
    if not (d / "contenus.json").exists():
        shutil.copyfile(GRAINE_DEEPOTUS, d / "contenus.json")
    kits = brand_kits.lire()
    kit = "deepotus" if "deepotus" in kits["kits"] else kits["actif"]
    return {"actif": "deepotus", "espaces": {"deepotus": {
        "nom": "Deepotus", "couleur": "#ef4444", "kit_id": kit, "archive": False, "created_at": _maintenant()}}}


def _ecrire(doc: dict) -> None:
    _ecrire_json(_fichier(), doc)


def _sain(doc) -> bool:
    return (isinstance(doc, dict) and isinstance(doc.get("espaces"), dict) and doc["espaces"]
            and all(id_valide(k) and isinstance(v, dict) for k, v in doc["espaces"].items()))


def lire() -> dict:
    """{actif, espaces} — cree (migration) au premier appel. Un fichier illisible est MIS DE COTE, jamais ecrase."""
    f = _fichier()
    if f.is_file():
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            doc = None
        if _sain(doc):
            if doc.get("actif") not in doc["espaces"]:
                doc["actif"] = sorted(doc["espaces"])[0]
            return doc
        cote = f.with_name(f"espaces.json.illisible-{datetime.now():%Y%m%d-%H%M%S}")
        f.replace(cote)
        logger.warning(f"espaces.json illisible : mis de cote ({cote.name}), espaces repris de la migration")
    doc = _migrer()
    _ecrire(doc)
    return doc


def _vue(eid: str, e: dict, actif: str) -> dict:
    return {"id": eid, "nom": e.get("nom") or eid, "couleur": e.get("couleur") or "#ef4444",
            "kit_id": e.get("kit_id"), "archive": bool(e.get("archive")), "created_at": e.get("created_at"),
            "actif": eid == actif}


def actif() -> dict:
    doc = lire()
    return _vue(doc["actif"], doc["espaces"][doc["actif"]], doc["actif"])


def lister(archives: bool = False) -> list:
    doc = lire()
    vues = [_vue(k, v, doc["actif"]) for k, v in doc["espaces"].items()]
    vues = [v for v in vues if archives or not v["archive"]]
    return sorted(vues, key=lambda v: (not v["actif"], v["archive"], v["nom"].lower()))


def _nom(v) -> str:
    n = v.strip()[:MAX] if isinstance(v, str) else ""
    if not n:
        raise ValueError("un espace a besoin d'un nom")
    return n


def _couleur(v, defaut: str) -> str:
    if v in (None, ""):
        return defaut
    if not isinstance(v, str) or not _COULEUR.match(v.strip()):
        raise ValueError(f"couleur doit être #RRGGBB (reçu : {v})")
    return v.strip()


def creer(champs: dict) -> dict:
    """Un espace neuf, NON actif : persona squelette a son nom, contenus vides, et son propre kit (sauf kit_id
    existant donne). ValueError = entree fautive, dite."""
    doc = lire()
    if len(doc["espaces"]) >= MAX_ESPACES:
        raise ValueError(f"{MAX_ESPACES} espaces au plus : archivez-en ou supprimez-en un d'abord")
    nom = _nom(champs.get("nom"))
    couleur = _couleur(champs.get("couleur"), "#ef4444")
    kit = champs.get("kit_id")
    if kit not in (None, ""):
        if kit not in brand_kits.lire()["kits"]:
            raise ValueError(f"kit inconnu : {kit}")
    else:
        kit = brand_kits.enregistrer({"name": nom, "app_name": nom.upper(), "app_sub": "", "tagline_1": "", "tagline_2": ""})
    eid = "esp_" + uuid.uuid4().hex[:8]
    _ecrire_json(dossier() / eid / "persona.json", {
        "persona_id": eid, "display_name": nom, "version": 2, "vibe_keywords": [], "default_negative_prompt": "",
        "default_hashtags_pool": [], "templates": []})
    _ecrire_json(dossier() / eid / "contenus.json", CONTENUS_VIDES)
    doc["espaces"][eid] = {"nom": nom, "couleur": couleur, "kit_id": kit, "archive": False, "created_at": _maintenant()}
    _ecrire(doc)
    return _vue(eid, doc["espaces"][eid], doc["actif"])


def modifier(eid: str, champs: dict) -> dict:
    doc = lire()
    if eid not in doc["espaces"]:
        raise KeyError(eid)
    e = doc["espaces"][eid]
    if "nom" in champs:
        e["nom"] = _nom(champs.get("nom"))
    if "couleur" in champs:
        e["couleur"] = _couleur(champs.get("couleur"), e.get("couleur") or "#ef4444")
    if "kit_id" in champs:
        if champs["kit_id"] not in brand_kits.lire()["kits"]:
            raise ValueError(f"kit inconnu : {champs['kit_id']}")
        e["kit_id"] = champs["kit_id"]
    _ecrire(doc)
    return _vue(eid, e, doc["actif"])


def activer(eid: str) -> dict:
    """Rend l'espace actif et active son kit (s'il existe encore). KeyError = inconnu, ValueError = archive."""
    doc = lire()
    if eid not in doc["espaces"]:
        raise KeyError(eid)
    if doc["espaces"][eid].get("archive"):
        raise ValueError("cet espace est archivé : désarchivez-le d'abord")
    doc["actif"] = eid
    _ecrire(doc)
    kit = doc["espaces"][eid].get("kit_id")
    if kit in brand_kits.lire()["kits"]:
        brand_kits.activer(kit)
    return _vue(eid, doc["espaces"][eid], eid)


def archiver(eid: str, archive: bool = True) -> str:
    """"ok" | "absent" | "actif" (l'espace actif ne s'archive pas) | "seul" (le dernier non archive)."""
    doc = lire()
    if eid not in doc["espaces"]:
        return "absent"
    if archive:
        if doc["actif"] == eid:
            return "actif"
        if sum(1 for v in doc["espaces"].values() if not v.get("archive")) <= 1:
            return "seul"
    doc["espaces"][eid]["archive"] = bool(archive)
    _ecrire(doc)
    return "ok"


def contenus(eid: str) -> dict:
    """Le contenus.json de l'espace (contenus vides s'il manque ou est illisible). KeyError = espace inconnu."""
    if eid not in lire()["espaces"]:
        raise KeyError(eid)
    f = chemin(eid, "contenus.json")
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else dict(CONTENUS_VIDES)
    except (OSError, ValueError):
        return dict(CONTENUS_VIDES)
