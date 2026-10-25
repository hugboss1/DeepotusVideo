# -*- coding: utf-8 -*-
"""Catalogue de l'assistant (spec docs/superpowers/specs/2026-10-19-agent-catalogue-design.md § 2) — les scripts
PARTAGÉS en DOM nu (t287, 24/10/2026).

Les composants de frontend/shared/ ne passent ni par le bundle (React) ni par un lab : ils bâtissent leurs éléments par
el("balise", { attributs }, [enfants]). Trois formes, lues en clair :
- el("button" | "a" | "select" | "textarea" | "input", { texte: T("k") | title / "aria-label" / placeholder: T("k") }) ;
- nom = el("balise", …) puis nom.textContent = T(…) ou nom.setAttribute("placeholder" | "title" | "aria-label", T(…)) ;
- une fabrique de boutons (function bouton(texte, …) { … el("button", { texte: texte }) … } ou
  const onglet = (nom, cle) => el("button", { role: "tab", texte: T(cle) })) suivie à chacun de ses appels.
Un T(a ? "k1" : "k2") donne les deux clés : ce sont les deux états d'un même élément (Générer / Enregistrer).
Les div, p, span, option (états, erreurs, titres de carte, pastilles) ne sont pas des éléments : jamais lus.
Écran : celui de la clé (« campagnes », « agent » → « commun » : le tiroir F1 est partout), cadre : aucun.
"""
from __future__ import annotations

import pathlib
import re

from catalogue_bundle import _objet
from catalogue_commun import VIDE, _base, _texte, message

# fichier partagé → préfixes de clés retenus (None : tout le fichier). Du tiroir F1 (dz-agent.js), seuls les éléments de
# l'agent Campagnes (t285b) : le tiroir « Demander » d'avant (envoyer, moteur, dictée…) n'est pas au catalogue.
PARTAGES = {
    "frontend/shared/dz-campagnes.js": None,
    "frontend/shared/dz-agent.js": ("agent.onglet.", "agent.campagnes.", "agent.action.campagnes"),
    # t307 (25/10/2026) : la boîte des canaux d'un projet ; son « Annuler » (commun.action.annuler) n'est pas à elle
    "frontend/shared/dz-projet-canaux.js": ("projets.canaux.",),
}
TYPE_DE_BALISE = {"button": "bouton", "a": "bouton", "select": "champ", "textarea": "champ", "input": "champ"}
LIBELLE, INFOBULLE = "texte", ("title", "aria-label", "placeholder")

_ID = r"[A-Za-z_$][\w$]*"
RE_T = re.compile(r"(?<![\w$.])(?:T|dzT)\(")
RE_EL = re.compile(r'(?<![\w$.])el\(\s*"([a-z]+)"\s*,\s*\{')
RE_DECL = re.compile(r"\b(?:var|const|let)\s+(" + _ID + r')\s*=\s*el\(\s*"([a-z]+)"')
RE_AFFECT = re.compile(r"(?<![\w$.])(" + _ID + r')\.(?:textContent\s*=|setAttribute\(\s*"(placeholder|title|aria-label)"\s*,)\s*')
RE_CLE = re.compile(r'"([a-z0-9_]+(?:\.[a-z0-9_]+){2,})"')
RE_PROP = re.compile(r'\s*("[^"]+"|' + _ID + r")\s*:\s*")
RE_DEF = re.compile(r"\bfunction\s+(" + _ID + r")\s*\(([^()]*)\)\s*\{"
                    r"|\b(?:const|let|var)\s+(" + _ID + r")\s*=\s*\(([^()]*)\)\s*=>\s*")
RE_TAB = re.compile(r'\brole\s*:\s*"tab"')


def _cles_T(s: str, a: int, z: int, memo: dict) -> list:
    """Les clés des appels T(…) entre a et z : les littéraux du 1er argument (les deux branches d'un ternaire)."""
    out = []
    for m in RE_T.finditer(s, a, z):
        r = _objet(s, m.end() - 1, memo)
        if not r:
            continue
        fin = r[1][0] if r[1] else r[0]
        out += [c for c in RE_CLE.findall(s, m.end(), fin) if c not in out]
    return out


def _proprietes(s: str, i: int, memo: dict):
    """s[i] == '{' → (fin, [(nom, début, fin)]) des propriétés de 1er niveau de l'objet, ou None."""
    r = _objet(s, i, memo)
    if not r:
        return None
    bornes, props = [i] + r[1] + [r[0]], []
    for a, z in zip(bornes, bornes[1:]):
        m = RE_PROP.match(s, a + 1, z)
        if m:
            props.append((m.group(1).strip('"'), m.end(), z))
    return r[0], props


def _element(out: list, typ: str, lib: list, tip: list, rel: str) -> None:
    """Un élément lu : (clé, type, clé du libellé | None, clé de l'infobulle | None, fichier). Plusieurs libellés
    (ternaire) : une fiche par état ; sinon chaque infobulle distincte (placeholder d'un ternaire)."""
    if lib:
        out.extend((k, typ, k, tip[0] if tip and tip[0] != k else None, rel) for k in lib)
    else:
        out.extend((k, typ, None, k, rel) for k in tip)


def _directs(s: str, rel: str, memo: dict, out: list) -> None:
    for m in RE_EL.finditer(s):
        typ = TYPE_DE_BALISE.get(m.group(1))
        p = _proprietes(s, m.end() - 1, memo) if typ else None
        if not p:
            continue
        fin, props = p
        lib, tip = [], []
        for nom, a, z in props:
            if nom == LIBELLE:
                lib += [c for c in _cles_T(s, a, z, memo) if c not in lib]
            elif nom in INFOBULLE:
                tip += [c for c in _cles_T(s, a, z, memo) if c not in tip]
        if RE_TAB.search(s, m.end() - 1, fin):
            typ = "onglet"
        _element(out, typ, lib, tip, rel)


def _affectations(s: str, rel: str, memo: dict, out: list) -> None:
    balises = {n: b for n, b in RE_DECL.findall(s)}
    for m in RE_AFFECT.finditer(s):
        typ = TYPE_DE_BALISE.get(balises.get(m.group(1), ""))
        t = RE_T.match(s, m.end())
        r = _objet(s, t.end() - 1, memo) if typ and t else None
        if not r:
            continue
        cles = _cles_T(s, m.end(), r[0] + 1, memo)
        _element(out, typ, [] if m.group(2) else cles, cles if m.group(2) else [], rel)


def _corps(s: str, m: re.Match, memo: dict):
    """(début, fin) du corps d'une définition : le bloc { … } ou, pour une flèche, l'expression appel(…)."""
    i = m.end() - 1 if m.group(1) else m.end()
    if s[i] != "{":
        a = re.compile(_ID + r"\s*\(").match(s, i)
        if not a:
            return None
        i = a.end() - 1
    r = _objet(s, i, memo)
    return (m.start(), r[0] + 1) if r else None


def _fabriques(s: str, rel: str, memo: dict, out: list) -> None:
    for m in RE_DEF.finditer(s):
        nom, params = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        bornes = _corps(s, m, memo)
        if not bornes:
            continue
        corps = s[bornes[0]:bornes[1]]
        balise = re.search(r'(?<![\w$.])el\(\s*"(button|a)"', corps)
        if not balise:
            continue
        typ = "onglet" if RE_TAB.search(corps) else TYPE_DE_BALISE[balise.group(1)]
        sortes = {}
        for rang, p in enumerate(x.split("=", 1)[0].strip() for x in params.split(",")):
            if not re.fullmatch(_ID, p):
                continue
            e = re.escape(p)
            for attr in (LIBELLE, *INFOBULLE):
                a = r'(?:"' + attr + r'"|\b' + attr + r")\s*:\s*"
                if re.search(a + r"(?:T|dzT)\(\s*" + e + r"\s*[,)]", corps):
                    sortes[rang] = ("cle", attr)
                elif re.search(a + e + r"(?![\w$])", corps):
                    sortes[rang] = ("texte", attr)
        for c in re.finditer(r"(?<![\w$.])" + re.escape(nom) + r"\(", s):
            if bornes[0] <= c.start() < bornes[1]:
                continue
            r = _objet(s, c.end() - 1, memo)
            if not r:
                continue
            args = [c.end() - 1] + r[1] + [r[0]]
            for rang, (forme, attr) in sortes.items():
                if rang + 1 >= len(args):
                    continue
                a, z = args[rang] + 1, args[rang + 1]
                if forme == "cle":
                    k = re.fullmatch(r'\s*"([a-z0-9_]+(?:\.[a-z0-9_]+){2,})"\s*', s[a:z])
                    cles = [k.group(1)] if k else []
                else:
                    cles = _cles_T(s, a, z, memo)
                _element(out, typ, cles if attr == LIBELLE else [], [] if attr == LIBELLE else cles, rel)


def depuis_partages(racine: pathlib.Path, dico: dict) -> dict:
    """Les éléments des scripts partagés de PARTAGES (fichier absent : rien). Une clé lue deux fois : la 1re fiche."""
    out = {}
    for rel, prefixes in PARTAGES.items():
        f = racine / rel
        if not f.exists():
            continue
        s, memo, lus = f.read_text(encoding="utf-8"), {}, []
        _directs(s, rel, memo, lus)
        _affectations(s, rel, memo, lus)
        _fabriques(s, rel, memo, lus)
        for k, typ, lib, tip, _ in lus:
            if k in out or k not in dico or message(k) or (prefixes and not k.startswith(prefixes)):
                continue
            out[k] = {**_base(k, typ, dico), "libelle": _texte(dico, lib) if lib else dict(VIDE),
                      "infobulle": _texte(dico, tip) if tip else None, "sources": [rel]}
    return dict(sorted(out.items()))
