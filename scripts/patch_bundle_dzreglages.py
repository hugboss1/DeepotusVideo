# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzreglages.py
"""Maillon de queue : l'OPTIMISATION DU MENU RÉGLAGES (lot « Menus : Réglages », t219-t224, 15/10/2026).

Plan docs/superpowers/plans/2026-10-15-optimisation-menus-reglages.md. Ce qu'il pose (ancres uniques, relevées le
15/10 sur 7a104ba2) :
  t219 — les pastilles de l'en-tête ouvraient Réglages › Comptes connectés. Elles faisaient `i&&i("settings")` et
  Réglages (`xm`) ne lisait sa rubrique qu'au montage (`vn("section")`, sinon « accounts ») : un Réglages déjà ouvert
  ne bougeait pas non plus.
  - R0 : `dzOuvrirReglages(section, aller)` écrit `?section=` (history.replaceState), émet `dz-reglages-section`
    {section}, puis appelle aller("settings") ; `dzReglagesEcoute(a)` écoute cet évènement (rubriques de `ym`
    seulement). Les deux sont posées devant `xm`, qui monte l'écoute dans un useEffect sans dépendance : Réglages
    déjà ouvert change de rubrique, un Réglages qui s'ouvre lit l'URL ;
  - R1 : la pastille des dépenses ouvre « pricing » (Tarifs et budget) ; R2 : les pastilles des clés (fal / HeyGen /
    voix) ouvrent « keys » (Clés d'API), comme leur bulle l'annonce ;
  - R3-R4 : la palette de commandes : « Réglages — comptes » → accounts, « Réglages — clés » → keys (l'aide est
    appelée APRÈS `n("settings")`, laissé intact : la paire G1 du maillon dzglyph le contient) ;
  - R5 : la bulle des dépenses annonce « Clic → Réglages → Tarifs et budget. ».
Aucun useState ajouté (compte figé 731), aucun DzTracks, rien qui touche « v2.8.0 ».
Clés dzT « reglages.pastille.* » (zone.objet.role : pas de « _ » dans la zone) : frontend/shared/i18n/menus.json (FR/EN), assemblées par scripts/i18n_assembler.py.

Maillon de QUEUE, APRÈS dzquick (dont il sonde le marqueur) ; il garde un .js.bak_dzreglages le temps de l'écriture
puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzreglages` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzquick`.
Les tâches suivantes du lot (t220-t223) AJOUTENT leurs paires ici : défaire d'abord avec le patcher de HEAD, éditer
PAIRES, puis réappliquer. Lecture et écriture en OCTETS.
Run : python scripts/patch_bundle_dzreglages.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzreglages")
TAG = "dzreglages"
MARKER = "function dzOuvrirReglages("
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("dzquick", "class DzQuickGarde ", 1),
    ("dzespace", "function DzEspaceSel(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

# R0 — les deux aides, posées devant Réglages (une ligne : le code injecté par les maillons est minifié à la main)
AIDES = (
    'function dzOuvrirReglages(section,aller){try{var u=new URL(window.location.href);u.searchParams.set("section",'
    'section);window.history.replaceState(null,"",u)}catch(_e){}try{window.dispatchEvent(new CustomEvent('
    '"dz-reglages-section",{detail:{section:section}}))}catch(_e){}if(typeof aller==="function")aller("settings")}'
    'function dzReglagesEcoute(aller){function h(ev){var k=ev&&ev.detail&&ev.detail.section;if(ym.includes(k))'
    'aller(k)}window.addEventListener("dz-reglages-section",h);return function(){'
    'window.removeEventListener("dz-reglages-section",h)}}'
)

XM = ('function xm({variant:e,personas:t=[],activePersonaId:n,setActivePersonaId:o,savePersona:i}){const[s,a]='
      'x.useState(()=>{const u=vn("section");return ym.includes(u)?u:"accounts"}),[l,d]=x.useState(null);')

PAIRES = [
    (XM,                                                                                                    # R0
     AIDES + XM + 'x.useEffect(function(){return dzReglagesEcoute(a)},[]);'),
    ('r.jsxs("div",{title:__dzCoutBlanc(Cu).titre,onClick:()=>i&&i("settings"),',                           # R1
     'r.jsxs("div",{title:__dzCoutBlanc(Cu).titre,onClick:()=>dzOuvrirReglages("pricing",i),'),
    ('title:dzT("coque.entete.ouvrir_cles"),onClick:()=>i&&i("settings"),',                                  # R2
     'title:dzT("coque.entete.ouvrir_cles"),onClick:()=>dzOuvrirReglages("keys",i),'),
    # R3-R4 : `n("settings")` reste tel quel (la paire G1 du maillon dzglyph le contient) ; l'aide vient APRÈS lui,
    # dans le même gestionnaire : l'URL est écrite avant que Réglages ne se monte (le rendu suit le gestionnaire)
    ('ings"),t()}},{l:dzT("coque.palette.reglages_cles")',                                                   # R3
     'ings"),t(),dzOuvrirReglages("accounts")}},{l:dzT("coque.palette.reglages_cles")'),
    ('ings"),t()}}].filter(l=>!i||',                                                                         # R4
     'ings"),t(),dzOuvrirReglages("keys")}}].filter(l=>!i||'),
    ('titre:t+dzT("reglages.depenses.clic_reglages")',                                                      # R5
     'titre:t+dzT("reglages.pastille.clic_tarifs")'),
]


def lire(p):
    b = p.read_bytes()
    bom = b.startswith(b"\xef\xbb\xbf")
    return b.decode("utf-8-sig" if bom else "utf-8"), bom


def ecrire(p, texte, bom):
    p.write_bytes((("﻿" if bom else "") + texte).encode("utf-8"))


def appliquer(s: str) -> str:
    for ancre, remplace in PAIRES:
        n = s.count(ancre)
        if n != 1:
            raise SystemExit(f"[{TAG}] ancre x{n} (attendu 1) : {ancre[:80]!r}")
        s = s.replace(ancre, remplace, 1)
    return s


def defaire(s: str) -> str:
    """L'inverse exact (lu par avant_dzreglages dans _i18n_l1_aide)."""
    for ancre, remplace in reversed(PAIRES):
        if s.count(remplace) != 1:
            raise AssertionError(f"[{TAG}] remplacement x{s.count(remplace)} (attendu 1) : {remplace[:80]!r}")
        s = s.replace(remplace, ancre, 1)
    return s


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    crlf = s.count("\r\n")
    if crlf < 15000 or s.count("\n") != crlf:
        raise SystemExit(f"[{TAG}] fins de ligne inattendues ({crlf} CRLF / {s.count(chr(10))} LF)")
    neuf = appliquer(s)
    if neuf.count(MARKER) != MARKER_ATTENDU or defaire(neuf) != s:
        raise SystemExit(f"[{TAG}] aller-retour imparfait")
    if neuf.count("x.useState(") != 731 or neuf.count("v2.8.0") != 4 or neuf.count("DzTracks") != 181:
        raise SystemExit(f"[{TAG}] un compte figé a bougé")
    if check:
        print(f"[{TAG}] à appliquer ({len(PAIRES)} paires)")
        return
    shutil.copyfile(BUNDLE, BAK)
    try:
        ecrire(BUNDLE, neuf, bom)
    except BaseException:
        shutil.copyfile(BAK, BUNDLE)                    # jamais un bundle à moitié écrit
        raise
    finally:
        BAK.unlink(missing_ok=True)
    print(f"[{TAG}] appliqué")


if __name__ == "__main__":
    main()
