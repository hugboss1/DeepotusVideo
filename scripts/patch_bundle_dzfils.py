# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzfils.py
"""Maillon de queue : les FILS SOCIAUX SUIVIS dans News › Sources (t381, lot « News : fils suivis », 30/10/2026, plan
docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md, décision D4 ; serveur t380).
Le panneau vit dans frontend/shared/dz-fils.js (window.__dzFils) ; le maillon ne pose que :
  P1/P2 : dans la colonne des Sources de l'écran News (`pm`), la liste défilante reçoit, APRÈS les flux (ou « aucun
          flux »), un <div data-dz-fils-hote> dont la ref (fonction, aucun hook : x.useState( reste à 731) appelle
          window.__dzFils.monter — « Fils suivis » et « Suggérés par les agents » ;
  P3 : la liste des articles ne garde que ceux des flux actifs (`ena`) : un élément venu d'un fil (champ `plateforme`,
       posé par le serveur) y reste aussi ;
  P4 : `loadItems` recopie chaque article champ par champ : `plateforme` y est ajouté (sans lui, P3 ne voit rien).
Clés dzT : frontend/shared/i18n/fils.json (FR/EN), assemblées par scripts/i18n_assembler.py.
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS dzchemins (dont il sonde le marqueur) ; il garde un .js.bak_dzfils le temps de l'écriture
puis le SUPPRIME. Son INVERSE est `avant_dzfils` dans backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé
EN TÊTE de `avant_dzchemins`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin
de ligne ; les ancres sont hors des couches __DZ_*_BEGIN__. DÉFAIRE le maillon AVANT de changer ses paires.
Banc : backend/tests/test_fils_ecran.py.
Run : python scripts/patch_bundle_dzfils.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzfils")
TAG = "dzfils"
MARKER = "/*dzfils*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzchemins", "/*dzchemins*/", 1),
    ("sources", 'dzT("news.sources.vide")', 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

HOTE = (MARKER + 'r.jsx("div",{"data-dz-fils-hote":"1",ref:function(el){if(el&&window.__dzFils)'
        'window.__dzFils.monter(el)}})')
_PIED = 'r.jsxs("div",{style:{padding:12,borderTop:"1px solid var(--stroke)",display:"flex",gap:8},children:['

PAIRES = [
    # P1 : la liste défilante des Sources devient un tableau d'enfants…
    ('r.jsx("div",{className:"scroll",style:{flex:1,overflowY:"auto",padding:"6px 0"},children:srcs.length?',
     'r.jsx("div",{className:"scroll",style:{flex:1,overflowY:"auto",padding:"6px 0"},children:[srcs.length?'),
    # P2 : … dont le dernier est l'hôte des fils, après les flux (ou « aucun flux »), avant le pied des boutons
    ('children:dzT("news.sources.vide")})}),' + _PIED,
     'children:dzT("news.sources.vide")}),' + HOTE + ']}),' + _PIED),
    # P3 : un élément de fil (plateforme) reste dans la liste des articles
    ('var bySrc=srcs.length?items.filter(i=>ena.has(i.source_id)):items;',
     'var bySrc=srcs.length?items.filter(i=>ena.has(i.source_id)||!!i.plateforme):items;'),
    # P4 : l'écran recopie chaque article champ par champ (loadItems) : la plateforme d'un élément de fil est gardée
    ('doublons:z.doublons||[]})))}).catch(()=>{});x.useEffect(()=>{loadSrcs();loadItems()},[]);',
     'doublons:z.doublons||[],plateforme:z.plateforme||null})))}).catch(()=>{});x.useEffect(()=>{loadSrcs();loadItems()},[]);'),
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
    """L'inverse exact (lu par avant_dzfils dans _i18n_l1_aide)."""
    for ancre, remplace in reversed(PAIRES):
        if s.count(remplace) != 1:
            raise AssertionError(f"[{TAG}] remplacement x{s.count(remplace)} (attendu 1) : {remplace[:80]!r}")
        s = s.replace(remplace, ancre, 1)
    return s


def partiel(s: str) -> bool:
    if MARKER not in s:
        return False
    try:
        defaire(s)
    except AssertionError:
        return True
    return False


def hors_couche(s: str, jeton: str) -> bool:
    """Le jeton n'est dans aucun bloc /*__DZ_<NOM>_BEGIN__*/ … /*__DZ_<NOM>_END__*/."""
    i = s.index(jeton)
    for m in re.finditer(r"/\*__DZ_([A-Z0-9_]+?)_BEGIN__\*/", s):
        if m.start() <= i <= s.index("/*__DZ_%s_END__*/" % m.group(1)):
            return False
    return True


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
        if partiel(s):
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzfils")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    if any("\n" in a + z or "x.useState(" in z or CONFIRMER in z for a, z in PAIRES):
        raise SystemExit(f"[{TAG}] paire fautive (fin de ligne, x.useState( ou confirmation directe)")
    crlf = s.count("\r\n")
    if crlf < 15000 or s.count("\n") != crlf:
        raise SystemExit(f"[{TAG}] fins de ligne inattendues ({crlf} CRLF / {s.count(chr(10))} LF)")
    if not all(hors_couche(s, a) for a, _z in PAIRES):
        raise SystemExit(f"[{TAG}] une ancre est dans un bloc de couche __DZ_*_BEGIN__")
    neuf = appliquer(s)
    if not all(hors_couche(neuf, z) for _a, z in PAIRES):
        raise SystemExit(f"[{TAG}] une paire tombe dans un bloc de couche __DZ_*_BEGIN__")
    if neuf.count(MARKER) != MARKER_ATTENDU or defaire(neuf) != s:
        raise SystemExit(f"[{TAG}] aller-retour imparfait")
    if (neuf.count("x.useState(") != 731 or neuf.count("v2.8.0") != 4 or neuf.count("DzTracks") != 181
            or neuf.count(CONFIRMER) != 30 or neuf.count('dzT("news.sources.vide")') != 1
            or neuf.count("\r\n") != crlf):
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
