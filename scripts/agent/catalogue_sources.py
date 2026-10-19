# -*- coding: utf-8 -*-
"""Catalogue de l'assistant (spec docs/superpowers/specs/2026-10-19-agent-catalogue-design.md § 2) — les SOURCES.

Lit le CODE du dépôt (jamais l'application en marche) et rend des éléments bruts :
{id, ecran, cadre, type, libelle{fr,en}, infobulle{fr,en}|None, icone, sources[], (reglages, fiche)}.
Aucune rédaction ici : le rôle et les synonymes viennent du skill connaissance-agent (fusion : catalogue.py).
Lancé avec le python embarqué, sans importer l'application.
"""
from __future__ import annotations

import ast
import bisect
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
# préfixe « zone.objet » rattaché à un autre écran que sa zone (consulté AVANT ECRAN_DE_ZONE)
ECRAN_DE_PREFIXE = {"avatar.noeud": "studio"}            # titres des nœuds avatar du graphe du Studio
# zone → lab affiché dans un cadre intégré (les iframes que monte la SPA)
CADRE_DE_ZONE = {"vectorlab": "/vectorlab/", "photolab": "/photolab/", "sprites": "/spritelab/",
                 "tuiles": "/tilelab/", "cartes": "/cardforge/", "matiere": "/materialforge/",
                 "studio3d": "/studio3d/"}
# rôle d'une clé qui désigne un MESSAGE (état, erreur), pas un élément : le dernier segment, ou son dernier morceau
# après « _ » (montage.projets.montage_vide). « titre » et « aide » n'y sont PAS : ce sont souvent de vraies infobulles.
ROLES_MESSAGES = {"echec", "erreur", "err", "vide", "aucun", "aucune", "chargement", "en_cours", "illisible",
                  "refuse", "fait", "enregistre", "pose", "plusieurs", "un", "redaction", "lecture", "generation",
                  "manquant", "manquante", "manque", "attente", "pret"}
# labs servis en cadre intégré dont le code est lu en clair : dossier de frontend/ → (écran, cadre)
LABS = {"vectorlab": ("vectorlab", "/vectorlab/"), "photolab": ("photolab", "/photolab/"),
        "avatar": ("avatarlive", "/avatar/")}
LAB_DE_DOSSIER = {"vectorlab": ("vectorlab", "/vectorlab/"), "photolab": ("photolab", "/photolab/"),
                  "spritelab": ("assets3d", "/spritelab/"), "tilelab": ("assets3d", "/tilelab/")}

# un élément React minifié : r.jsx(X,{…}) / r.jsxs(X,{…}) ; X = balise ("button") ou composant (identifiant nu,
# renommé à chaque build : jamais codé en dur)
RE_ELEMENT = re.compile(r'\.jsxs?\(\s*("[a-zA-Z][a-zA-Z0-9-]*"|[A-Za-z_$][\w$.]*)\s*,\s*\{')
RE_CLE = re.compile(r'dzT\("([a-z0-9_.]+)"\s*[,)]')              # dzT("cle") ou dzT("cle",{params})
RE_ICONE_LIT = re.compile(r'"(dz-[a-z0-9-]+)"')
RE_ICONE = re.compile(r'icone?:"(dz-[a-z0-9-]+)"')
# infobulle d'un lab : title: T("k"), b.title = T("k"), et la forme gabarit title="${T("k")}" ; T, dzT, t ou vlT
RE_T_LAB = re.compile(r'(title|titre|"aria-label"|aria-label|tip)\s*[:=]\s*(?:"\$\{\s*)?(?:T|dzT|t|vlT)\("([a-z0-9_.]+)"\)')
RE_BALISE = re.compile(r"<([A-Za-z][\w-]*)")
# une ligne de lab qui ouvre un dialogue : son « titre: T(…) » est le titre de la boîte, pas un élément
RE_DIALOGUE = re.compile(r"saisir\(|confirmer\(|valider:|dialogue", re.I)
EXCLUS = ("docs", "agent", "catalogue", "_exclus.json")   # faux éléments écartés par le skill connaissance-agent
RE_LETTRE = re.compile(r"[A-Za-zÀ-ÿ]")
CHAMPS = {"input", "select", "textarea"}
LITTERAL_MAX = 200
VIDE = {"fr": "", "en": ""}
# lecture d'un objet de props : les caractères qui comptent hors chaîne, les chaînes, l'intérieur d'un gabarit
_RE_SPECIAL = re.compile(r"[{}()\[\]\"'`,]|/\*|//")      # « / » seul (division, regex) : rien
_RE_TETE = re.compile(r"(?:\s+|/\*[\s\S]*?\*/|//[^\n]*)*")      # blancs et commentaires devant un attribut
_RE_CHAINE = {'"': re.compile(r'"(?:[^"\\\n]|\\.)*"'), "'": re.compile(r"'(?:[^'\\\n]|\\.)*'")}
_RE_GABARIT = re.compile(r"\\[\s\S]|`|\$\{")
_RE_ATTR = re.compile(r'\s*("[^"]+"|[A-Za-z_$][\w$]*)\s*:')
_RE_METHODE = re.compile(r"\s*([A-Za-z_$][\w$]*)\s*\(")
_RE_NU = re.compile(r"\s*([A-Za-z_$][\w$]*)\s*$")


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


def ecran(cle: str) -> str:
    prefixe = ".".join(cle.split(".", 2)[:2])
    return ECRAN_DE_PREFIXE.get(prefixe) or ECRAN_DE_ZONE.get(zone(cle), "commun")


def message(cle: str) -> bool:
    dernier = cle.rsplit(".", 1)[-1]                   # « code_en_cours » : un rôle de plusieurs morceaux compte aussi
    return dernier in ROLES_MESSAGES or any(dernier.endswith("_" + r) for r in ROLES_MESSAGES)


def _texte(dico: dict, cle: str) -> dict:
    v = dico.get(cle) or {}
    return {"fr": v.get("fr", ""), "en": v.get("en", "")}


def _base(cle: str, typ: str, dico: dict) -> dict:
    return {"id": cle, "ecran": ecran(cle), "cadre": CADRE_DE_ZONE.get(zone(cle)), "type": typ,
            "libelle": _texte(dico, cle), "infobulle": None, "icone": None, "sources": [f"i18n:{cle}"]}


def _sha8(t: str) -> str:
    return hashlib.sha1(t.encode("utf-8")).hexdigest()[:8]


def _bundle(racine: pathlib.Path) -> str:
    fichiers = sorted((racine / "frontend" / "dist" / "assets").glob("index-*.js"))
    return fichiers[0].read_text(encoding="utf-8") if fichiers else ""


# ── lecture d'un objet de props par accolades équilibrées ─────────────────────────────────────────────────────────

def _objet(s: str, i: int, memo: dict):
    """s[i] == '{' → (position de la '}' fermante, virgules de 1er niveau), ou None si l'objet ne se referme pas.
    Saute les chaînes "…" '…', les gabarits `…${…}…` (échappements compris) et les commentaires /* … */, // …. `memo` garde les objets déjà
    bornés : un objet imbriqué déjà lu est enjambé d'un coup (d'où la lecture des éléments de la fin vers le début).
    Limite connue : un littéral d'expression régulière contenant un guillemet ou une accolade fausse la lecture."""
    pile, virgules, j = [], [], i
    while True:
        if pile and pile[-1] == "`":
            m = _RE_GABARIT.search(s, j)
            if not m:
                return None
            j = m.end()
            if m.group() == "`":
                pile.pop()
            elif m.group() == "${":
                pile.append("{")
            continue
        m = _RE_SPECIAL.search(s, j)
        if not m:
            return None
        j, c = m.start(), m.group()
        if c == "/*":                                    # une apostrophe de commentaire n'ouvre pas de chaîne
            k = s.find("*/", j + 2)
            if k < 0:
                return None
            j = k + 2
        elif c == "//":
            k = s.find("\n", j)
            j = k if k >= 0 else len(s)
        elif c in _RE_CHAINE:
            m = _RE_CHAINE[c].match(s, j)
            if not m:
                return None
            j = m.end()
        elif c == "`":
            pile.append("`")
            j += 1
        elif c in "{([":
            if pile and j in memo:
                j = memo[j][0] + 1
            else:
                pile.append(c)
                j += 1
        elif c in "})]":
            if not pile:
                return None
            pile.pop()
            if not pile:
                memo[i] = (j, virgules)
                return memo[i]
            j += 1
        else:                                            # « , »
            if len(pile) == 1:
                virgules.append(j)
            j += 1


def _attributs(s: str, i: int, fin: int, virgules: list) -> dict:
    """attributs de PREMIER niveau de l'objet s[i..fin] : nom (sans guillemets) → (début, fin) de la valeur."""
    out, bornes = {}, [i] + virgules + [fin]
    for a, b in zip(bornes, bornes[1:]):
        a += _RE_TETE.match(s, a + 1).end() - (a + 1)  # sauter blancs et commentaires de tête
        seg = s[a + 1:b]
        m = _RE_ATTR.match(seg)
        if m:
            out.setdefault(m.group(1).strip('"'), (a + 1 + m.end(), b))
            continue
        m = _RE_METHODE.match(seg) or _RE_NU.match(seg)   # onClick(){…} ou {onClick}
        if m:
            out.setdefault(m.group(1), (a + 1 + m.start(1), b))
    return out


# ── extraction ────────────────────────────────────────────────────────────────────────────────────────────────────

def _elements(b: str) -> list:
    """Tous les éléments jsx/jsxs du bundle, dans l'ordre du texte : (début, balise, attributs)."""
    memo, out = {}, []
    for m in reversed(list(RE_ELEMENT.finditer(b))):      # les imbriqués d'abord : l'objet parent les enjambe
        i = m.end() - 1
        r = _objet(b, i, memo)
        if r:
            out.append((m.start(), m.group(1), _attributs(b, i, r[0], r[1])))
    out.reverse()
    return out


def _etat_de_ternaire(avant: str, texte: dict) -> bool:
    """1re branche d'un ternaire (« cond ? dzT(A) : … ») dont le texte FR finit par « … » : un état passager."""
    fr = (texte.get("fr") or "").rstrip() if isinstance(texte, dict) else ""
    return avant.rstrip().endswith("?") and fr.endswith(("…", "..."))


def _retenu(balise: str, attrs: dict):
    """type de l'élément s'il est cliquable ou saisissable, sinon None."""
    if balise.startswith('"'):
        nom = balise.strip('"')
        if nom in CHAMPS:
            return "champ"
        return "bouton" if nom == "button" or "onClick" in attrs else None
    if "placeholder" in attrs:                           # composant de saisie maison (champ de recherche…)
        return "champ"
    return "bouton" if ("onClick" in attrs or "title" in attrs or "aria-label" in attrs) else None


def depuis_bundle(racine: pathlib.Path, dico: dict, inv: dict) -> dict:
    """Une fiche par élément cliquable (bouton natif, composant à onClick, composant à infobulle) ou champ.
    Libellé = 1re clé dzT de children/label (coupé au 1er élément imbriqué) ; infobulle = 1re clé de title,
    aria-label (placeholder pour un champ). Même clé sur deux éléments : la 1re fiche gagne, la source s'ajoute."""
    b, out = _bundle(racine), {}
    elements = _elements(b)
    debuts = [e[0] for e in elements]
    cles_pos = [(m.start(), m.group(1)) for m in RE_CLE.finditer(b) if m.group(1) in dico]
    pos_cles = [p for p, _ in cles_pos]

    def premiere_cle(attrs, noms, coupe):
        for n in noms:
            if n not in attrs:
                continue
            a, z = attrs[n]
            if coupe:                                    # jamais la clé d'un élément imbriqué
                k = bisect.bisect_left(debuts, a)
                if k < len(debuts) and debuts[k] < z:
                    z = debuts[k]
            for m in RE_CLE.finditer(b, a, z):
                k = m.group(1)
                if k not in dico or message(k):
                    continue
                if coupe and _etat_de_ternaire(b[a:m.start()], dico[k]):
                    continue                             # busy?dzT("…envoi…"):dzT("envoyer") → la branche au repos
                return k
        return None

    def icone(attrs):
        for n in ("icon", "icone"):
            if n in attrs:
                noms = RE_ICONE_LIT.findall(b, *attrs[n])
                if len(noms) >= 2 and noms[0].startswith("dz-etat-"):
                    return noms[1]                       # icon:j?"dz-etat-attente":"dz-B" → l'icône au repos
                if noms:
                    return noms[0]
        if "children" in attrs:                          # glyphe dans le contenu propre (__dzGlT, composant icône)
            a, z = attrs["children"]
            k = bisect.bisect_right(debuts, a)
            while k < len(debuts) and debuts[k] < z:       # s'arrêter au 1er élément imbriqué RETENU
                if _retenu(elements[k][1], elements[k][2]):
                    z = debuts[k]
                    break
                k += 1
            m = RE_ICONE_LIT.search(b, a, z)
            if m:
                return m.group(1)
        return None

    def ecran_proche(pos):
        k = bisect.bisect_left(pos_cles, pos)
        voisins = [cles_pos[j] for j in (k - 1, k) if 0 <= j < len(cles_pos)]
        return ecran(min(voisins, key=lambda v: abs(v[0] - pos))[1]) if voisins else "commun"

    for debut, balise, attrs in elements:
        typ = _retenu(balise, attrs)
        if not typ:
            continue
        lib = premiere_cle(attrs, ("children", "label"), True)
        tips = ("title", "aria-label", "placeholder") if typ == "champ" else ("title", "aria-label")
        tip = premiere_cle(attrs, tips, False)
        sources = [f"i18n:{k}" for k in (lib, tip) if k]
        if lib or tip:
            i = lib or tip
            if i in out:
                out[i]["sources"] = sorted(set(out[i]["sources"]) | set(sources))
                continue
            e = out[i] = _base(i, typ, dico)
            e["libelle"] = _texte(dico, lib) if lib else dict(VIDE)
            e["infobulle"] = _texte(dico, tip) if tip else None
            e["icone"], e["sources"] = icone(attrs), sorted(sources)
            continue
        if "title" not in attrs:
            continue
        brut = b[slice(*attrs["title"])].strip()
        if not (len(brut) >= 2 and brut[0] == brut[-1] == '"'):
            continue
        try:
            fr = json.loads(brut)
        except ValueError:
            fr = brut[1:-1]
        if not (fr and len(fr) <= LITTERAL_MAX and RE_LETTRE.search(fr)):
            continue
        ec = ecran_proche(debut)
        i = f"lit.{_sha8(ec + fr)}"
        if i in out:
            continue
        out[i] = {"id": i, "ecran": ec, "cadre": None, "type": typ, "libelle": dict(VIDE),
                  "infobulle": {"fr": fr, "en": inv.get(fr, "")}, "icone": icone(attrs), "sources": ["bundle:title"]}
    return out


def _slug(t: str) -> str:
    import unicodedata
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
    """(clé, position) des infobulles d'un fichier de lab, hors lignes de dialogue (la ligne OU la précédente :
    « ouvrirDialogue(PL, { » puis « titre: T(…) »)."""
    debut, avant = 0, ""
    for ligne in texte.splitlines(keepends=True):
        if not (RE_DIALOGUE.search(ligne) or RE_DIALOGUE.search(avant)):
            for m in RE_T_LAB.finditer(ligne):
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
    for dossier_lab, (ec, cadre) in LABS.items():
        dossier = racine / "frontend" / dossier_lab
        fichiers = [dossier / "index.html", *sorted(dossier.glob("*.js")), *sorted((dossier / "js").glob("*.js"))]
        for f in fichiers:
            if not f.exists():
                continue
            rel = f.relative_to(racine).as_posix()
            texte = f.read_text(encoding="utf-8", errors="replace")
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
            if k in out:                                  # outil aussi lu en infobulle : une fiche, sources fusionnées
                e["sources"] = sorted(set(e["sources"]) | set(out[k]["sources"]))
            out[k] = e
    return out


def depuis_reglages(racine: pathlib.Path, inv: dict) -> dict:
    """Les rubriques de la recherche des Réglages (_INDEX_FIXE de settings_routes.py)."""
    f = racine / "backend" / "app" / "api" / "settings_routes.py"
    if not f.exists():
        return {}
    valeur = []
    for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "_INDEX_FIXE" for t in n.targets):
            valeur = ast.literal_eval(n.value)
    out = {}
    for section, libelle, _mots in valeur:
        i = f"reglages.{section}.{_slug(libelle)}"
        if i in out:
            continue
        out[i] = {"id": i, "ecran": "settings", "cadre": None, "type": "reglage",
                  "libelle": {"fr": libelle, "en": inv.get(libelle, libelle)}, "infobulle": None, "icone": None,
                  "sources": ["backend/app/api/settings_routes.py#_INDEX_FIXE"], "reglages": section}
    return out


def depuis_fiches(racine: pathlib.Path) -> dict:
    """Les fiches didactiques des labs (frontend/<lab>/aide/index.json)."""
    out = {}
    for f in sorted((racine / "frontend").glob("*/aide/index.json")):
        dossier = f.parent.parent.name
        ec, cadre = LAB_DE_DOSSIER.get(dossier, ("commun", None))
        for x in json.loads(f.read_text(encoding="utf-8")):
            i = f"{dossier}.fiche.{x['id']}"
            out[i] = {"id": i, "ecran": ec, "cadre": cadre, "type": "outil",
                      "libelle": {"fr": x["titre"], "en": x.get("titre_en") or x["titre"]},
                      "infobulle": {"fr": x["phrase"], "en": x.get("phrase_en") or x["phrase"]}, "icone": None,
                      "sources": [f.relative_to(racine).as_posix()], "fiche": x["id"]}
    return out


def extraire(racine) -> dict:
    """Tous les éléments bruts du dépôt, par id. Une clé vue par plusieurs sources : une seule fiche (la 1re)."""
    racine = pathlib.Path(racine)
    dico = dictionnaire(racine)
    inv = inverse(dico)
    out = {}
    out.update(depuis_bundle(racine, dico, inv))
    _ajouter(out, depuis_labs(racine, dico))
    _ajouter(out, depuis_reglages(racine, inv))
    _ajouter(out, depuis_fiches(racine))
    f = racine.joinpath(*EXCLUS)
    if f.exists():                                       # ids exacts et préfixes que le skill a écartés
        x = json.loads(f.read_text(encoding="utf-8"))
        ids, prefixes = set(x.get("ids") or []), tuple(x.get("prefixes") or [])
        out = {k: v for k, v in out.items() if k not in ids and not (prefixes and k.startswith(prefixes))}
    return out
