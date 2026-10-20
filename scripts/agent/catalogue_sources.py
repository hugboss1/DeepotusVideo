# -*- coding: utf-8 -*-
"""Catalogue de l'assistant (spec docs/superpowers/specs/2026-10-19-agent-catalogue-design.md § 2) — les SOURCES.

Lit le CODE du dépôt (jamais l'application en marche) et rend des éléments bruts :
{id, ecran, cadre, type, libelle{fr,en}, infobulle{fr,en}|None, icone, sources[], (reglages, fiche)}.
Aucune rédaction ici : le rôle et les synonymes viennent du skill connaissance-agent (fusion : catalogue.py).
Lancé avec le python embarqué, sans importer l'application.
"""
from __future__ import annotations

import ast
import html
import json
import pathlib
import re
import shutil
import subprocess
import sys
import unicodedata

# tables et aides communes, et le parseur du bundle : réexportés ici (catalogue.py et le banc lisent S.…)
from catalogue_commun import (CADRE_DE_ZONE, CHAMPS, ECRAN_DE_PREFIXE, ECRAN_DE_ZONE, ROLES_MESSAGES,  # noqa: F401
                              VIDE, _base, _sha8, _texte, ecran, message, zone)
from catalogue_bundle import _bundle, depuis_bundle                                                # noqa: F401
from catalogue_fabriques import fabriques

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


RE_LIBELLE_VOISIN = re.compile(r'\blibelle\s*:\s*(?:(?:T|dzT|t|vlT)\("([a-z0-9_.]+)"\)|"([^"\\]+)")')


def _libelle_voisin(ligne: str, i: int):
    """Le libellé posé dans le MÊME objet littéral que l'infobulle en ligne[i] — { id: "pixel", libelle: "Pixel",
    titre: T("…") } : ("cle", k) ou ("lit", texte), sinon None. L'objet s'arrête à la 1re accolade de part et d'autre."""
    a = max(ligne.rfind("{", 0, i), ligne.rfind("}", 0, i)) + 1
    z = min((j for j in (ligne.find("{", i), ligne.find("}", i)) if j >= 0), default=len(ligne))
    m = RE_LIBELLE_VOISIN.search(ligne[a:z])
    return None if not m else ("cle", m.group(1)) if m.group(1) else ("lit", m.group(2))


def _infobulles_lab(texte: str):
    """(clé, position, libellé voisin) des infobulles d'un fichier de lab. Seul l'attribut « titre » d'une ligne de dialogue est écarté
    (la ligne OU la précédente : « ouvrirDialogue(PL, { » puis « titre: T(…) ») ; title et aria-label restent."""
    debut, avant = 0, ""
    for ligne in texte.splitlines(keepends=True):
        dialogue = bool(RE_DIALOGUE.search(ligne) or RE_DIALOGUE.search(avant))
        for m in RE_T_LAB.finditer(ligne):
            if not (dialogue and m.group(1) == "titre"):
                yield m.group(2), debut + m.start(), _libelle_voisin(ligne, m.start())
        debut, avant = debut + len(ligne), ligne


def _type_lab(texte: str, pos: int) -> str:
    """« champ » si l'attribut est dans la balise ouvrante d'un <input>/<select>/<textarea> (gabarit HTML), sinon
    « bouton »."""
    lt = texte.rfind("<", 0, pos)
    if lt < 0 or ">" in texte[lt:pos].replace("=>", ""):   # hors balise (b.title = T(…)) ; « => » n'en ferme pas
        return "bouton"
    m = RE_BALISE.match(texte, lt)
    return "champ" if m and m.group(1).lower() in CHAMPS else "bouton"


def depuis_labs(racine: pathlib.Path, dico: dict, inv: dict = None) -> dict:
    """Les infobulles T("cle") des labs en cadre intégré (index.html, *.js, js/*.js), avec le libellé posé à côté dans
    le même objet, plus le registre des outils du Photolab (photolab.outil.<id>)."""
    inv = inv or {}
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
            for k, pos, lib in _infobulles_lab(texte):
                if k not in dico or message(k):
                    continue
                e = out.get(k) or {**_base(k, _type_lab(texte, pos), dico), "ecran": ec, "cadre": cadre,
                                   "libelle": dict(VIDE), "infobulle": _texte(dico, k), "sources": []}
                if lib and not e["libelle"]["fr"]:
                    if lib[0] == "cle" and lib[1] in dico:
                        e["libelle"] = _texte(dico, lib[1])
                    elif lib[0] == "lit":
                        e["libelle"] = {"fr": lib[1], "en": inv.get(lib[1], "")}
                e["sources"] = sorted(set(e["sources"]) | {rel})
                out[k] = e
            for k, typ, champ, icone in fabriques(texte):   # éléments bâtis par une fabrique du lab (t261)
                if k not in dico or message(k) or k.startswith("commun."):
                    continue
                e = out.get(k)
                if e is None:
                    e = out[k] = {**_base(k, typ, dico), "ecran": ec, "cadre": cadre, "libelle": dict(VIDE),
                                  "infobulle": None, "icone": icone, "sources": []}
                    e[champ] = _texte(dico, k)
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


# balise ouvrante d'un bouton ou d'un champ, écrite en clair dans la page d'un lab, et son infobulle littérale
RE_BALISE_PAGE = re.compile(r"<(button|input|select|textarea)\b[^>]*>", re.I)
RE_TITLE_PAGE = re.compile(r'\btitle="([^"$]+)"')


def depuis_pages(racine: pathlib.Path, dico: dict, deja: dict) -> dict:
    """Les boutons et champs de la page d'un lab (index.html) dont l'infobulle est un texte FR en clair — la barre
    d'outils du Vectorlab : <button data-outil="plume" title="Plume Bézier — …">. La page est traduite au
    chargement par recouvrement exact ; sa clé est celle du dictionnaire de la page (<lab>.page.*) qui porte ce texte.
    Un texte déjà porté par une fiche connue (même bouton lu ailleurs) n'en crée pas d'autre ; sans clé : rien."""
    out = {}
    for dossier_lab in LABS_LUS:
        ec, cadre = LABS[dossier_lab]
        f = racine / "frontend" / dossier_lab / "index.html"
        if not f.exists():
            continue
        rel, prefixe = f.relative_to(racine).as_posix(), f"{dossier_lab}.page."
        par_texte = {}
        for k, v in dico.items():
            if isinstance(v, dict) and v.get("fr"):
                par_texte.setdefault(v["fr"], []).append(k)
        for m in RE_BALISE_PAGE.finditer(f.read_text(encoding="utf-8")):
            t = RE_TITLE_PAGE.search(m.group())
            if not t:
                continue
            cles = par_texte.get(html.unescape(t.group(1)), [])
            page = sorted(k for k in cles if k.startswith(prefixe))
            if not page or any(k in deja or k in out for k in cles if k.startswith(dossier_lab + ".")):
                continue
            k = page[0]
            typ = "champ" if m.group(1).lower() in CHAMPS else "bouton"
            out[k] = {**_base(k, typ, dico), "ecran": ec, "cadre": cadre, "libelle": dict(VIDE),
                      "infobulle": _texte(dico, k), "sources": [rel]}
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


MENUS_PHOTOLAB = ("frontend", "photolab", "js", "mod-menus.js")
CATALOGUE_MENUS = "frontend/photolab/donnees/menus.json"
ETATS_MENU = ("actif", "inactif")    # « inactif » : grisée faute de document, l'entrée existe ; « bientot » : non


def _registre_photolab(racine: pathlib.Path) -> list:
    """Le registre capturé du moteur épinglé (backend/tests/photocraft_commandes_<version de vendor/photocraft.json>),
    chaque commande avec ses `champs` (photolab_registre.structurer, comme GET /api/photolab/commandes)."""
    version = json.loads((racine / "vendor" / "photocraft.json").read_text(encoding="utf-8"))["version"]
    f = racine / "backend" / "tests" / f"photocraft_commandes_{version}.json"
    if not f.exists():
        raise RuntimeError(f"{f.relative_to(racine).as_posix()} absent : python scripts/photocraft_commandes.py")
    brut = json.loads(f.read_text(encoding="utf-8"))
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backend"))
    from app.services import photolab_registre as PR                 # module pur (json, re) : sans l'application
    reg = PR.structurer(brut)
    return [{**c, "champs": reg.get(c.get("id"), {}).get("champs", [])} for c in brut]


def depuis_menus_photolab(racine: pathlib.Path, dico: dict) -> dict:
    """Les entrées de la barre de menus du Photolab qui ne sont PAS « bientôt » : la vraie construireMenus
    (scripts/agent/photolab_menus.mjs, node) sur le registre capturé. Id photolab.menu.<commande> ; le chemin de
    sous-menus et le raccourci affichés, par langue. Pas de mod-menus.js : rien ; node ou registre absent : RuntimeError
    (un catalogue vidé en silence passerait toutes les fiches « retire »)."""
    if not racine.joinpath(*MENUS_PHOTOLAB).exists():
        return {}
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node introuvable : il construit les menus du Photolab (scripts/agent/photolab_menus.mjs)")
    entree = json.dumps({"registre": _registre_photolab(racine), "dico": dico}, ensure_ascii=False)
    p = subprocess.run([node, str(pathlib.Path(__file__).resolve().parent / "photolab_menus.mjs"), str(racine)],
                       input=entree, capture_output=True, text=True, encoding="utf-8", timeout=120)
    if p.returncode:
        raise RuntimeError(f"menus du Photolab : {p.stderr.strip()[-400:]}")
    langues = json.loads(p.stdout)
    du_catalogue = {e.get("id") for e in json.loads((racine / CATALOGUE_MENUS).read_text(encoding="utf-8"))["entrees"]}
    en = {}
    for x in langues["en"]:
        en.setdefault(x["id"], x)
    out = {}
    for x in langues["fr"]:
        i = f"photolab.menu.{x['id']}"
        if x["etat"] not in ETATS_MENU or i in out:              # une commande placée deux fois : la 1re place
            continue
        y = en.get(x["id"], {})
        e = {"id": i, "ecran": "photolab", "cadre": "/photolab/", "type": "menu",
             "libelle": {"fr": x["libelle"], "en": y.get("libelle", "")}, "infobulle": None, "icone": None,
             "chemin": {"fr": " › ".join(x["chemin"]), "en": " › ".join(y.get("chemin", []))},
             "sources": [CATALOGUE_MENUS if x["id"] in du_catalogue else "/".join(MENUS_PHOTOLAB)]}
        if x["raccourci"]:
            e["raccourci"] = {"fr": x["raccourci"], "en": y.get("raccourci", "")}
        out[i] = e
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
    _ajouter(out, depuis_labs(racine, dico, inv))
    _ajouter(out, depuis_pages(racine, dico, out))
    _ajouter(out, depuis_reglages(racine, inv))
    _ajouter(out, depuis_fiches(racine))
    _ajouter(out, depuis_menus_photolab(racine, dico))
    return {k: v for k, v in out.items() if k not in ids and not (prefixes and k.startswith(prefixes))}
