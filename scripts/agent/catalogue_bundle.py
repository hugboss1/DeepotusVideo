# -*- coding: utf-8 -*-
"""Catalogue de l'assistant (spec docs/superpowers/specs/2026-10-19-agent-catalogue-design.md § 2) — le BUNDLE.

Lit le bundle minifié de la SPA (frontend/dist/assets/index-*.js) : chaque élément React r.jsx(X,{…}) cliquable ou
saisissable devient une fiche brute (libellé et infobulle dzT, icône, ou infobulle littérale).
"""
from __future__ import annotations

import bisect
import json
import pathlib
import re

from catalogue_commun import CHAMPS, VIDE, _base, _sha8, _texte, ecran, message

# un élément React minifié : r.jsx(X,{…}) / r.jsxs(X,{…}) ; X = balise ("button") ou composant (identifiant nu,
# renommé à chaque build : jamais codé en dur)
RE_ELEMENT = re.compile(r'\.jsxs?\(\s*("[a-zA-Z][a-zA-Z0-9-]*"|[A-Za-z_$][\w$.]*)\s*,\s*\{')
RE_CLE = re.compile(r'dzT\("([a-z0-9_.]+)"\s*[,)]')              # dzT("cle") ou dzT("cle",{params})
RE_ICONE_LIT = re.compile(r'"(dz-[a-z0-9-]+)"')
RE_LETTRE = re.compile(r"[A-Za-zÀ-ÿ]")
LITTERAL_MAX = 200
# lecture d'un objet de props : les caractères qui comptent hors chaîne, les chaînes, l'intérieur d'un gabarit
_RE_SPECIAL = re.compile(r"[{}()\[\]\"'`,]|/\*|//")      # « / » seul (division, regex) : rien
_RE_TETE = re.compile(r"(?:\s+|/\*[\s\S]*?\*/|//[^\n]*)*")      # blancs et commentaires devant un attribut
_RE_CHAINE = {'"': re.compile(r'"(?:[^"\\\n]|\\.)*"'), "'": re.compile(r"'(?:[^'\\\n]|\\.)*'")}
_RE_GABARIT = re.compile(r"\\[\s\S]|`|\$\{")
_RE_ATTR = re.compile(r'\s*("[^"]+"|[A-Za-z_$][\w$]*)\s*:')
_RE_METHODE = re.compile(r"\s*([A-Za-z_$][\w$]*)\s*\(")
_RE_NU = re.compile(r"\s*([A-Za-z_$][\w$]*)\s*$")


def _bundle(racine: pathlib.Path) -> str:
    """Le bundle de la SPA ; aucun → "" ; plusieurs → erreur (un reste d'ancien build fausserait le catalogue)."""
    fichiers = sorted((racine / "frontend" / "dist" / "assets").glob("index-*.js"))
    if len(fichiers) > 1:
        raise RuntimeError("frontend/dist/assets : le bundle doit être unique, trouvés "
                           + ", ".join(f.name for f in fichiers))
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

