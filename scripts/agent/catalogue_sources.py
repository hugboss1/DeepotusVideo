# -*- coding: utf-8 -*-
"""Catalogue de l'assistant (spec docs/superpowers/specs/2026-10-19-agent-catalogue-design.md § 2) — les SOURCES.

Lit le CODE du dépôt (jamais l'application en marche) et rend des éléments bruts :
{id, ecran, cadre, type, libelle{fr,en}, infobulle{fr,en}|None, icone, sources[], (reglages, fiche)}.
Aucune rédaction ici : le rôle et les synonymes viennent du skill connaissance-agent (fusion : catalogue.py).
Lancé avec le python embarqué, sans importer l'application.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import sys
import unicodedata

# tables et aides communes, et le parseur du bundle : réexportés ici (catalogue.py et le banc lisent S.…)
from catalogue_commun import (CADRE_DE_ZONE, CHAMPS, ECRAN_DE_PREFIXE, ECRAN_DE_ZONE, ROLES_MESSAGES,  # noqa: F401
                              VIDE, _base, _sha8, _texte, ecran, message, zone)
from catalogue_bundle import _bundle, depuis_bundle                                                # noqa: F401

# labs servis en cadre intégré : dossier de frontend/ → (écran, cadre). Une seule table pour les deux lectures :
# le code des labs de LABS_LUS est lu en clair (infobulles T(…)), les fiches didactiques de tous (aide/index.json).
LABS = {"vectorlab": ("vectorlab", "/vectorlab/"), "photolab": ("photolab", "/photolab/"),
        "avatar": ("avatarlive", "/avatar/"), "spritelab": ("assets3d", "/spritelab/"),
        "tilelab": ("assets3d", "/tilelab/")}
LABS_LUS = ("vectorlab", "photolab", "avatar")

# infobulle d'un lab : title: T("k"), b.title = T("k"), et la forme gabarit title="${T("k")}" ; T, dzT, t ou vlT
RE_T_LAB = re.compile(r'(title|titre|"aria-label"|aria-label|tip)\s*[:=]\s*(?:"\$\{\s*)?(?:T|dzT|t|vlT)\("([a-z0-9_.]+)"\)')
RE_BALISE = re.compile(r"<([A-Za-z][\w-]*)")
# une ligne de lab qui ouvre un dialogue : son attribut « titre: T(…) » (et lui seul : jamais title/aria-label) est le
# titre de la boîte, pas un élément. coquilleReglage( ouvre les boîtes de réglage du Photolab, dialogueXxx( ses
# boîtes dédiées (dialogueExport) ; « dialogue » seul couvre VL.dialogue.… (mais pas « dialogues »).
RE_DIALOGUE = re.compile(r"\bsaisir\(|\bconfirmer\(|\bouvrirDialogue\(|\bvalider:|\bcoquilleReglage\(|\bdialogue\b"
                         r"|\bdialogue[A-Z]\w*\(")
EXCLUS = ("docs", "agent", "catalogue", "_exclus.json")   # faux éléments écartés par le skill connaissance-agent


def dictionnaire(racine: pathlib.Path) -> dict:
    d = {}
    for f in sorted((racine / "frontend" / "shared" / "i18n").glob("*.json")):
        d.update(json.loads(f.read_text(encoding="utf-8")))
    return d


def inverse(dico: dict) -> dict:
    """texte FR → texte EN (le bundle garde des libellés FR en clair, traduits par recouvrement exact)."""
    return {v["fr"]: v["en"] for v in dico.values() if isinstance(v, dict) and v.get("fr") and v.get("en")}


def _slug(t: str) -> str:
    s = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or _sha8(t)


def _ajouter(out: dict, nouveaux: dict) -> None:
    """Une clé déjà vue (bundle, autre lab) garde sa 1re fiche ; seules les sources s'ajoutent."""
    for k, e in nouveaux.items():
        if k in out:
            out[k]["sources"] = sorted(set(out[k]["sources"]) | set(e["sources"]))
        else:
            out[k] = e


def _infobulles_lab(texte: str):
    """(clé, position) des infobulles d'un fichier de lab. Seul l'attribut « titre » d'une ligne de dialogue est écarté
    (la ligne OU la précédente : « ouvrirDialogue(PL, { » puis « titre: T(…) ») ; title et aria-label restent."""
    debut, avant = 0, ""
    for ligne in texte.splitlines(keepends=True):
        dialogue = bool(RE_DIALOGUE.search(ligne) or RE_DIALOGUE.search(avant))
        for m in RE_T_LAB.finditer(ligne):
            if not (dialogue and m.group(1) == "titre"):
                yield m.group(2), debut + m.start()
        debut, avant = debut + len(ligne), ligne


def _type_lab(texte: str, pos: int) -> str:
    """« champ » si l'attribut est dans la balise ouvrante d'un <input>/<select>/<textarea> (gabarit HTML), sinon
    « bouton »."""
    lt = texte.rfind("<", 0, pos)
    if lt < 0 or ">" in texte[lt:pos].replace("=>", ""):   # hors balise (b.title = T(…)) ; « => » n'en ferme pas
        return "bouton"
    m = RE_BALISE.match(texte, lt)
    return "champ" if m and m.group(1).lower() in CHAMPS else "bouton"


def depuis_labs(racine: pathlib.Path, dico: dict) -> dict:
    """Les infobulles T("cle") des labs en cadre intégré (index.html, *.js, js/*.js), plus le registre des outils du
    Photolab (photolab.outil.<id>)."""
    out = {}
    for dossier_lab in LABS_LUS:
        ec, cadre = LABS[dossier_lab]
        dossier = racine / "frontend" / dossier_lab
        fichiers = [dossier / "index.html", *sorted(dossier.glob("*.js")), *sorted((dossier / "js").glob("*.js"))]
        for f in fichiers:
            if not f.exists():
                continue
            rel = f.relative_to(racine).as_posix()
            texte = f.read_text(encoding="utf-8")
            for k, pos in _infobulles_lab(texte):
                if k not in dico or message(k):
                    continue
                e = out.get(k) or {**_base(k, _type_lab(texte, pos), dico), "ecran": ec, "cadre": cadre,
                                   "libelle": dict(VIDE), "infobulle": _texte(dico, k), "sources": []}
                e["sources"] = sorted(set(e["sources"]) | {rel})
                out[k] = e
    for k in dico:
        if k.startswith("photolab.outil.") and not message(k):
            e = {**_base(k, "outil", dico), "ecran": "photolab", "cadre": "/photolab/"}
            if k in out:                                  # outil déjà lu en infobulle : on garde cette fiche (et son
                e = out[k]                                # infobulle), la source i18n s'ajoute
                e["sources"] = sorted(set(e["sources"]) | {f"i18n:{k}"})
            out[k] = e
    return out


def _index_fixe(f: pathlib.Path) -> list:
    """La valeur littérale de _INDEX_FIXE (affectation simple ou annotée) : une liste de triplets
    (section, libellé, mots). Introuvable, non littérale ou mal formée → RuntimeError."""
    nom = f"{f.name} : _INDEX_FIXE"
    valeur = None
    for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "_INDEX_FIXE" for t in n.targets):
            valeur = n.value
        elif isinstance(n, ast.AnnAssign) and getattr(n.target, "id", None) == "_INDEX_FIXE" and n.value is not None:
            valeur = n.value
    if valeur is None:
        raise RuntimeError(f"{nom} introuvable (affectation attendue)")
    try:
        liste = ast.literal_eval(valeur)
    except ValueError as x:
        raise RuntimeError(f"{nom} n'est pas une valeur littérale ({x})") from None
    if not isinstance(liste, (list, tuple)):
        raise RuntimeError(f"{nom} : liste attendue, trouvé {type(liste).__name__}")
    for t in liste:
        if not (isinstance(t, (list, tuple)) and len(t) == 3 and all(isinstance(v, str) for v in t)):
            raise RuntimeError(f"{nom} : triplet (section, libellé, mots) attendu, trouvé {t!r}")
    return list(liste)


def depuis_reglages(racine: pathlib.Path, inv: dict) -> dict:
    """Les rubriques de la recherche des Réglages (_INDEX_FIXE de settings_routes.py ; fichier absent : aucune)."""
    f = racine / "backend" / "app" / "api" / "settings_routes.py"
    if not f.exists():
        return {}
    out = {}
    for section, libelle, _mots in _index_fixe(f):
        i = f"reglages.{section}.{_slug(libelle)}"
        if i in out:
            continue
        out[i] = {"id": i, "ecran": "settings", "cadre": None, "type": "reglage",
                  "libelle": {"fr": libelle, "en": inv.get(libelle, "")}, "infobulle": None, "icone": None,
                  "sources": ["backend/app/api/settings_routes.py#_INDEX_FIXE"], "reglages": section}
    return out


IGNOREES: list = []          # fiches didactiques sans id/titre/phrase écartées par la dernière extraction (« chemin#id »)


def depuis_fiches(racine: pathlib.Path) -> dict:
    """Les fiches didactiques des labs (frontend/<lab>/aide/index.json). Fichier illisible ou racine non liste →
    RuntimeError ; fiche sans id/titre/phrase → ignorée, notée dans IGNOREES et sur stderr."""
    out = {}
    for f in sorted((racine / "frontend").glob("*/aide/index.json")):
        dossier = f.parent.parent.name
        rel = f.relative_to(racine).as_posix()
        ec, cadre = LABS.get(dossier, ("commun", None))
        try:
            liste = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError) as x:
            raise RuntimeError(f"{rel} illisible : {x}") from None
        if not isinstance(liste, list):
            raise RuntimeError(f"{rel} illisible : liste de fiches attendue, trouvé {type(liste).__name__}")
        for n, x in enumerate(liste):
            complete = isinstance(x, dict) and all(isinstance(x.get(c), str) and x[c] for c in ("id", "titre", "phrase"))
            if not complete:
                nom = x["id"] if isinstance(x, dict) and isinstance(x.get("id"), str) and x["id"] else n
                IGNOREES.append(f"{rel}#{nom}")
                print(f"catalogue : fiche ignorée (id, titre ou phrase manquant) {rel}#{nom}", file=sys.stderr)
                continue
            i = f"{dossier}.fiche.{x['id']}"
            out[i] = {"id": i, "ecran": ec, "cadre": cadre, "type": "outil",
                      "libelle": {"fr": x["titre"], "en": x.get("titre_en") or ""},
                      "infobulle": {"fr": x["phrase"], "en": x.get("phrase_en") or ""}, "icone": None,
                      "sources": [rel], "fiche": x["id"]}
    return out


def _exclusions(racine: pathlib.Path) -> tuple:
    """(ids exacts, préfixes) que le skill connaissance-agent a écartés ; fichier absent : aucune exclusion.
    Mal formé → RuntimeError (une chaîne en guise de liste deviendrait un tuple de lettres et effacerait en silence)."""
    f = racine.joinpath(*EXCLUS)
    if not f.exists():
        return set(), ()
    nom = "/".join(EXCLUS)
    try:
        x = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise RuntimeError(f"{nom} illisible : {err}") from None
    if not isinstance(x, dict):
        raise RuntimeError(f"{nom} illisible : objet attendu, trouvé {type(x).__name__}")
    listes = {}
    for champ in ("ids", "prefixes"):
        v = x.get(champ, [])
        if not isinstance(v, list) or not all(isinstance(e, str) for e in v):
            raise RuntimeError(f"{nom} illisible : « {champ} » doit être une liste de chaînes, trouvé {v!r}")
        listes[champ] = v
    return set(listes["ids"]), tuple(listes["prefixes"])


def extraire(racine) -> dict:
    """Tous les éléments bruts du dépôt, par id. Une clé vue par plusieurs sources : une seule fiche (la 1re)."""
    racine = pathlib.Path(racine)
    IGNOREES.clear()
    ids, prefixes = _exclusions(racine)                  # lu d'abord : un fichier mal formé arrête tout
    dico = dictionnaire(racine)
    inv = inverse(dico)
    out = {}
    out.update(depuis_bundle(racine, dico, inv))
    _ajouter(out, depuis_labs(racine, dico))
    _ajouter(out, depuis_reglages(racine, inv))
    _ajouter(out, depuis_fiches(racine))
    return {k: v for k, v in out.items() if k not in ids and not (prefixes and k.startswith(prefixes))}
