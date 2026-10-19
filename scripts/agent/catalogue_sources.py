# -*- coding: utf-8 -*-
"""Catalogue de l'assistant (spec docs/superpowers/specs/2026-10-19-agent-catalogue-design.md § 2) — les SOURCES.

Lit le CODE du dépôt (jamais l'application en marche) et rend des éléments bruts :
{id, ecran, cadre, type, libelle{fr,en}, infobulle{fr,en}|None, icone, sources[], (reglages, fiche)}.
Aucune rédaction ici : le rôle et les synonymes viennent du skill connaissance-agent (fusion : catalogue.py).
Lancé avec le python embarqué, sans importer l'application.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import re

# zone d'une clé i18n (1er segment) → écran de l'app (agent_aide.VUES) ; tout le reste : « commun »
ECRAN_DE_ZONE = {
    "quick": "quick", "studio": "studio", "motion": "studio", "episodes": "episodes", "atelier": "episodes",
    "son": "sonvfx", "sfx": "sonvfx", "vfx": "sonvfx", "montage": "montage", "montage_svm": "montage",
    "subs": "montage", "scheduler": "scheduler", "planif_news": "scheduler", "templates": "templates",
    "news": "news", "biblio": "library", "lib3d": "assets3d", "sprites": "assets3d", "tuiles": "assets3d",
    "cartes": "assets3d", "matiere": "assets3d", "studio3d": "assets3d", "etabli": "assets3d",
    "plateau": "assets3d", "avatar": "avatarlive", "vectorlab": "vectorlab", "photolab": "photolab",
    "reglages": "settings", "espaces": "settings", "transfert": "settings",
}
# zone → lab affiché dans un cadre intégré (les iframes que monte la SPA)
CADRE_DE_ZONE = {"vectorlab": "/vectorlab/", "photolab": "/photolab/", "sprites": "/spritelab/",
                 "tuiles": "/tilelab/", "cartes": "/cardforge/", "matiere": "/materialforge/",
                 "studio3d": "/studio3d/"}
# dernier segment d'une clé qui désigne un MESSAGE (état, erreur), pas un élément cliquable
ROLES_MESSAGES = {"echec", "erreur", "err", "vide", "aucun", "aucune", "chargement", "en_cours", "illisible",
                  "refuse", "fait", "enregistre", "pose", "plusieurs", "un"}
LABS = {"vectorlab": "/vectorlab/", "photolab": "/photolab/"}
LAB_DE_DOSSIER = {"vectorlab": ("vectorlab", "/vectorlab/"), "photolab": ("photolab", "/photolab/"),
                  "spritelab": ("assets3d", "/spritelab/"), "tilelab": ("assets3d", "/tilelab/")}

FENETRE = 600
RE_BOUTON = re.compile(r'"button",\{')
RE_DZT = re.compile(r'(title|children|"aria-label"|label)\s*:\s*dzT\("([a-z0-9_.]+)"\)')
RE_TITRE_LIT = re.compile(r'title:"([^"\\]{3,80})"')
RE_ICONE = re.compile(r'icone?:"(dz-[a-z0-9-]+)"')
RE_T_LAB = re.compile(r'(title|titre|"aria-label"|tip)\s*[:=]\s*(?:T|dzT|t)\("([a-z0-9_.]+)"\)')
VIDE = {"fr": "", "en": ""}


def dictionnaire(racine: pathlib.Path) -> dict:
    d = {}
    for f in sorted((racine / "frontend" / "shared" / "i18n").glob("*.json")):
        d.update(json.loads(f.read_text(encoding="utf-8")))
    return d


def inverse(dico: dict) -> dict:
    """texte FR → texte EN (le bundle garde des libellés FR en clair, traduits par recouvrement exact)."""
    return {v["fr"]: v["en"] for v in dico.values() if isinstance(v, dict) and v.get("fr") and v.get("en")}


def zone(cle: str) -> str:
    return cle.split(".", 1)[0]


def message(cle: str) -> bool:
    return cle.rsplit(".", 1)[-1] in ROLES_MESSAGES


def _texte(dico: dict, cle: str) -> dict:
    v = dico.get(cle) or {}
    return {"fr": v.get("fr", ""), "en": v.get("en", "")}


def _base(cle: str, typ: str, dico: dict) -> dict:
    z = zone(cle)
    return {"id": cle, "ecran": ECRAN_DE_ZONE.get(z, "commun"), "cadre": CADRE_DE_ZONE.get(z), "type": typ,
            "libelle": _texte(dico, cle), "infobulle": None, "icone": None, "sources": [f"i18n:{cle}"]}


def _sha8(t: str) -> str:
    return hashlib.sha1(t.encode("utf-8")).hexdigest()[:8]


def _bundle(racine: pathlib.Path) -> str:
    fichiers = sorted((racine / "frontend" / "dist" / "assets").glob("index-*.js"))
    return fichiers[0].read_text(encoding="utf-8") if fichiers else ""


def depuis_bundle(racine: pathlib.Path, dico: dict, inv: dict) -> dict:
    b, out, titres_vus = _bundle(racine), {}, set()
    for m in RE_BOUTON.finditer(b):
        f = b[m.end(): m.end() + FENETRE]
        n = f.find('"button",{')
        f = f if n < 0 else f[:n]
        cles = RE_DZT.findall(f)
        lib = next((k for a, k in cles if a in ("children", "label") and k in dico and not message(k)), None)
        tip = next((k for a, k in cles if a in ("title", '"aria-label"') and k in dico and not message(k)), None)
        ic = RE_ICONE.search(f)
        if lib or tip:
            e = out.setdefault(lib or tip, _base(lib or tip, "bouton", dico))
            e["libelle"] = _texte(dico, lib) if lib else dict(VIDE)
            if tip:
                e["infobulle"] = _texte(dico, tip)
                titres_vus.add(tip)
            if ic:
                e["icone"] = ic.group(1)
            e["sources"] = sorted({f"i18n:{k}" for k in (lib, tip) if k})
            continue
        lit = RE_TITRE_LIT.search(f)
        if lit and re.search(r"[A-Za-zÀ-ÿ]", lit.group(1)):
            fr = lit.group(1)
            i = f"lit.{_sha8(fr)}"
            out[i] = {"id": i, "ecran": "commun", "cadre": None, "type": "bouton", "libelle": dict(VIDE),
                      "infobulle": {"fr": fr, "en": inv.get(fr, fr)}, "icone": ic.group(1) if ic else None,
                      "sources": ["bundle:title"]}
    for a, k in RE_DZT.findall(b):                      # infobulles hors d'un bouton natif (composants à icône)
        if a in ("title", '"aria-label"') and k in dico and not message(k) and k not in titres_vus and k not in out:
            e = _base(k, "bouton", dico)
            e["libelle"], e["infobulle"] = dict(VIDE), _texte(dico, k)
            out[k] = e
    return out


def extraire(racine) -> dict:
    """Tous les éléments bruts du dépôt, par id."""
    racine = pathlib.Path(racine)
    dico = dictionnaire(racine)
    inv = inverse(dico)
    out = {}
    out.update(depuis_bundle(racine, dico, inv))
    return out
