# -*- coding: utf-8 -*-
"""Catalogue de l'assistant (spec docs/superpowers/specs/2026-10-19-agent-catalogue-design.md § 2) — les écrans bâtis en
GABARITS HTML (t404, 31/10/2026).

L'onglet 3D « Créer » (frontend/shared/dz-creer3d.js) et les écrans du 3D Studio (frontend/studio3d/ecrans/*.js) bâtissent
leurs éléments par chaînes HTML (innerHTML) où les messages, les options et les vrais boutons se mêlent : aucune forme
lisible ne les sépare. Les éléments retenus sont donc DÉSIGNÉS, clé par clé, dans scripts/agent/gabarits_html.json
(le skill connaissance-agent les choisit en lisant le code) :

  {"groupes": [{"fichiers": ["frontend/studio3d/ecrans/coque.js", …],
                "cles": {"studio3decrans.onglet.texture": ["onglet", "studio3decrans.aide.texture"],
                         "creer3d.saisie.generer": "bouton"}}]}

Une clé n'entre que si elle est au dictionnaire ET encore employée par le code du groupe : en clair ("aff.tout" ou
"studio3decrans.aff.tout" — les écrans du 3D Studio passent par un T qui préfixe leur zone), ou composée
(T("onglet." + e.id) : le préfixe "onglet. et l'id "texture" figurent tous deux dans les fichiers du groupe). Une clé
que le code n'emploie plus disparaît, et sa fiche passe « retire ». Écran et cadre : ceux de la zone (catalogue_commun).
"""
from __future__ import annotations

import json
import pathlib
import re

from catalogue_commun import _base, _texte

TABLE = ("scripts", "agent", "gabarits_html.json")
TYPES = {"bouton", "champ", "onglet", "outil", "panneau"}


def _cite(mot: str, texte: str) -> bool:
    """mot écrit en littéral (casse ignorée : curseur("ventForce") donne T("decor." + nom.toLowerCase())), ou en clé
    d'objet ({ arbres: […], sol: […] } parcouru par Object.keys)."""
    return re.search(r"[\"'`]" + re.escape(mot) + r"[\"'`]|[{,]\s*" + re.escape(mot) + r"\s*:", texte, re.I) is not None


def _employee(cle: str, texte: str) -> bool:
    """La clé est employée en clair, ou composée : un littéral qui S'ARRÊTE après un préfixe de la clé coupé à « . » ou
    « _ » ("anim.onglet_" + v, `aff.${cle}_${x}`), et le reste écrit ailleurs en littéral, entier ou morceau par morceau."""
    relatives = [cle, cle.split(".", 1)[1]] if cle.count(".") >= 2 else [cle]
    for r in relatives:
        if _cite(r, texte):
            return True
        for i, c in enumerate(r):
            if c not in "._" or i == len(r) - 1:
                continue
            prefixe, reste = r[:i + 1], r[i + 1:]
            if not re.search(r"[\"'`]" + re.escape(prefixe) + r"(?:[\"'`]|\$\{)", texte):
                continue
            if _cite(reste, texte) or all(_cite(m, texte) for m in reste.split("_") if m):
                return True
    return False


def _table(racine: pathlib.Path) -> list:
    """Les groupes de la table ; fichier absent : aucun. Mal formé → RuntimeError (une erreur muette viderait l'écran)."""
    f = racine.joinpath(*TABLE)
    if not f.exists():
        return []
    nom = "/".join(TABLE)
    try:
        x = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise RuntimeError(f"{nom} illisible : {err}") from None
    groupes = x.get("groupes") if isinstance(x, dict) else None
    if not isinstance(groupes, list):
        raise RuntimeError(f"{nom} illisible : « groupes » doit être une liste")
    for g in groupes:
        if not (isinstance(g, dict) and isinstance(g.get("fichiers"), list) and isinstance(g.get("cles"), dict)):
            raise RuntimeError(f"{nom} illisible : un groupe veut « fichiers » (liste) et « cles » (objet) : {g!r}")
        for k, v in g["cles"].items():
            typ = v[0] if isinstance(v, list) and v else v
            if typ not in TYPES or (isinstance(v, list) and len(v) > 2):
                raise RuntimeError(f"{nom} illisible : {k} → {v!r} (type parmi {sorted(TYPES)}, puis la clé d'infobulle)")
    return groupes


def depuis_gabarits(racine: pathlib.Path, dico: dict) -> dict:
    out = {}
    for g in _table(racine):
        presents = [p for p in g["fichiers"] if (racine / p).exists()]
        texte = "\n".join((racine / p).read_text(encoding="utf-8") for p in presents)
        for k, v in g["cles"].items():
            typ, info = (v[0], v[1] if len(v) > 1 else None) if isinstance(v, list) else (v, None)
            if k not in dico or not _employee(k, texte):
                continue
            e = {**_base(k, typ, dico), "sources": sorted(presents)}
            if info and info in dico:
                e["infobulle"] = _texte(dico, info)
            out[k] = e
    return out
