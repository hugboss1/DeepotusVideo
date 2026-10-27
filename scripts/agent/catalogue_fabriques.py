# -*- coding: utf-8 -*-
"""Catalogue de l'assistant (spec docs/superpowers/specs/2026-10-19-agent-catalogue-design.md § 2) — les FABRIQUES des labs.

Le code d'un lab bâtit beaucoup de ses éléments par de petites fonctions (panneau Actions du Photolab, t261) : la clé
n'est pas dans l'élément mais à chaque appel. Cinq formes, lues en clair dans un fichier de lab :
- bouton(icone, cle, fn) dont le corps pose title = T(cle) : la clé est l'argument littéral ;
- caseAllumage(etat, aria, fn) dont le corps pose aria-label = aria : la clé est le T("…") de l'argument ;
- champ(c, libelleCle, element) qui étiquette un <label> par T(libelleCle) : un champ ;
- it(id, cle, …) qui rend un objet dont la clé est affichée par T(x.cle) dans un role="menuitem" : une entrée de menu ;
- el("button", classe, T(cle)) et les boutons d'un dialogue, boutons: [{ libelle: T(cle) }].
Rend des (clé, type, champ « libelle » | « infobulle », icône) ; le tri (dictionnaire, messages) est fait par l'appelant.
"""
from __future__ import annotations

import re

from catalogue_bundle import _objet

_T = r"(?:T|dzT|t|vlT)"
# function nom(params) {   |   const nom = (params) => {   ou   => ({ (jamais « => ( expression », comme T lui-même)
RE_DEF = re.compile(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(([^()]*)\)\s*\{"
                    r"|\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*\(([^()]*)\)\s*=>\s*(\{|\((?=\s*\{))")
RE_CLE_ARG = re.compile(r'\s*"([a-z0-9_]+(?:\.[a-z0-9_]+)+)"\s*$')
RE_T_CLE = re.compile(_T + r'\(\s*"([a-z0-9_.]+)"\s*[,)]')
RE_ICONE = re.compile(r'"(dz-[a-z0-9-]+)"')
RE_EL_BOUTON = re.compile(r'\b[A-Za-z_$][\w$]*\(\s*"button"\s*,[^,\n]*,\s*' + _T + r'\(\s*"([a-z0-9_.]+)"\s*[,)]')
RE_BOUTONS = re.compile(r"\bboutons\s*:\s*\[")
RE_LIBELLE_T = re.compile(r"\blibelle\s*:\s*" + _T + r'\(\s*"([a-z0-9_.]+)"\s*[,)]')
RE_MENUITEM = re.compile(r"""["']menuitem(?:checkbox)?["']""")
RE_T_PROP = re.compile(_T + r"\(\s*[A-Za-z_$][\w$]*\.([A-Za-z_$][\w$]*)\s*\)")
FENETRE_MENU = 600                                       # caractères autour d'un role="menuitem" où lire T(x.prop)
# t311 (restes) : T("prefixe." + o[0]) près d'un role "tab" — onglets dont la clé est composée à l'exécution
RE_T_CONCAT = re.compile(_T + r'\(\s*"([a-z0-9_]+(?:\.[a-z0-9_]+)*\.)"\s*\+')
RE_ROLE_TAB = re.compile(r"""\brole\s*:\s*["']tab["']""")
RE_LITTERAL = re.compile(r'"([a-z0-9_]+)"')
FENETRE_TAB = 400                                        # caractères autour de T("prefixe." + …) où chercher role "tab"


def _parametres(brut: str) -> list:
    """« icone, cle, fn, cls = "" » → ["icone", "cle", "fn", "cls"] ; une déstructuration compte pour un rang vide."""
    out = []
    for p in brut.split(","):
        p = p.split("=", 1)[0].strip()
        out.append(p if re.fullmatch(r"[A-Za-z_$][\w$]*", p) else "")
    return out


def _arguments(texte: str, i: int, memo: dict):
    """texte[i] == '(' → liste des (début, fin) des arguments, ou None."""
    r = _objet(texte, i, memo)
    if not r:
        return None
    bornes = [i] + r[1] + [r[0]]
    return [(a + 1, z) for a, z in zip(bornes, bornes[1:])]


def _definitions(texte: str, memo: dict):
    """(nom, paramètres, début de la définition, corps, rend_un_objet) des fonctions nommées du fichier."""
    for m in RE_DEF.finditer(texte):
        nom, params = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        ouvre = m.end() - 1
        r = _objet(texte, ouvre, memo)
        if r:
            yield nom, _parametres(params), m.start(), texte[ouvre:r[0] + 1], m.group(5) == "("   # => ({ … })


def _sorte(p: str, corps: str, menu_affiche: set, objet: bool):
    """Ce que le paramètre p devient dans le corps : (forme de l'argument « cle » | « texte », type, champ) ou None."""
    e = re.escape(p)
    if re.search(_T + r"\(\s*" + e + r"\s*\)", corps):
        if '"button"' in corps:
            return "cle", "bouton", "infobulle"
        if '"label"' in corps:
            return "cle", "champ", "libelle"
    if objet and p in menu_affiche and re.search(r"(?<![\w$.])" + e + r"(?![\w$])", corps):
        return "cle", "menu", "libelle"
    if '"button"' in corps and re.search(r'setAttribute\(\s*"aria-label"\s*,\s*' + e + r"\s*\)"
                                          r"|\.title\s*=\s*" + e + r"\s*[;,)]|\btitle\s*:\s*" + e + r"\s*[,}]", corps):
        return "texte", "bouton", "infobulle"
    # t311 (27/10/2026) : bouton(texte, p, glyphe) de la page WhatsApp — el("button", …) dont un enfant porte
    # el("span", { texte: texte }) : l'argument T("k") est le LIBELLÉ du bouton
    if '"button"' in corps and re.search(r"\btexte\s*:\s*" + e + r"\s*[,}]", corps):
        return "texte", "bouton", "libelle"
    return None


def _menu_affiche(texte: str) -> set:
    """Les propriétés affichées par T(x.prop) près d'un menuitem."""
    out = set()
    for m in RE_MENUITEM.finditer(texte):
        out |= set(RE_T_PROP.findall(texte, max(0, m.start() - FENETRE_MENU), m.end() + FENETRE_MENU))
    return out


def definitions(texte: str) -> dict:
    """t311 (restes) : {nom: sortes} des fabriques définies dans un fichier, pour les appels « X.nom( » des autres
    fichiers du même lab (whatsapp.js définit bouton(), onglets-*.js appellent W.bouton(…))."""
    memo, menu = {}, _menu_affiche(texte)
    out = {}
    for nom, params, _debut, corps, objet in _definitions(texte, memo):
        sortes = {r: s for r, p in enumerate(params) if p and (s := _sorte(p, corps, menu, objet))}
        if sortes:
            out[nom] = sortes
    return out


def _onglets(texte: str) -> list:
    """Les onglets à clé composée T("prefixe." + o[0]) sur un role "tab" : une clé par littéral du fichier (le
    tri par le dictionnaire est fait par l'appelant), avec l'icône du couple ["id", "dz-…"] s'il existe."""
    out, vus = [], set()
    for m in RE_T_CONCAT.finditer(texte):
        if not RE_ROLE_TAB.search(texte, max(0, m.start() - FENETRE_TAB), m.end() + FENETRE_TAB):
            continue
        for lit in RE_LITTERAL.findall(texte):
            k = m.group(1) + lit
            if k in vus:
                continue
            vus.add(k)
            ic = re.search(r'\[\s*"' + re.escape(lit) + r'"\s*,\s*"(dz-[a-z0-9-]+)"', texte)
            out.append((k, "onglet", "libelle", ic.group(1) if ic else None))
    return out


def fabriques(texte: str, partagees: dict = None) -> list:
    """Les éléments d'un fichier de lab bâtis par fabrique : [(clé, type, champ, icône)] dans l'ordre du texte.
    partagees : {nom: sortes} des fabriques d'autres fichiers du lab, lues seulement en appel préfixé « X.nom( »."""
    memo, out = {}, []
    menu_affiche = _menu_affiche(texte)
    appels = []                                          # (nom, sortes, motif d'appel, début de la définition)
    locales = set()
    for nom, params, debut, corps, objet in _definitions(texte, memo):
        sortes = {r: s for r, p in enumerate(params) if p and (s := _sorte(p, corps, menu_affiche, objet))}
        locales.add(nom)
        if sortes:
            appels.append((nom, sortes, r"(?<![\w$.])" + re.escape(nom) + r"\(", debut))
    for nom, sortes in (partagees or {}).items():
        if nom not in locales:
            appels.append((nom, sortes, r"(?<![\w$])[A-Za-z_$][\w$]*\." + re.escape(nom) + r"\(", -1))
    for nom, sortes, motif, debut in appels:
        for m in re.finditer(motif, texte):
            if m.start() == debut or texte[max(0, m.start() - 9):m.start()].rstrip().endswith("function"):
                continue
            args = _arguments(texte, m.end() - 1, memo)
            if not args:
                continue
            for r, (forme, typ, champ) in sortes.items():
                if r >= len(args):
                    continue
                a, z = args[r]
                if forme == "cle":
                    k = RE_CLE_ARG.match(texte[a:z])
                    cle = k.group(1) if k else None
                else:
                    cle = next((x.group(1) for x in RE_T_CLE.finditer(texte, a, z)
                                if not texte[a:x.start()].rstrip().endswith("?")), None)
                if cle:
                    ic = RE_ICONE.search(texte, args[0][0], args[-1][1])
                    out.append((cle, typ, champ, ic.group(1) if ic else None))
    for m in RE_EL_BOUTON.finditer(texte):
        out.append((m.group(1), "bouton", "libelle", None))
    for m in RE_BOUTONS.finditer(texte):
        r = _objet(texte, m.end() - 1, memo)
        if r:
            out.extend((k, "bouton", "libelle", None) for k in RE_LIBELLE_T.findall(texte, m.end(), r[0]))
    out.extend(_onglets(texte))
    return out
