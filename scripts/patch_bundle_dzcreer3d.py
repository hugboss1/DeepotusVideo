# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzcreer3d.py
"""Maillon de queue : l'onglet 3D de Game Assets devient « CRÉER » (t389, chantier « 3D Studio à écrans », 31/10/2026,
plan docs/superpowers/plans/2026-10-31-studio3d-ecrans.md, décision D1). L'écran vit dans frontend/shared/dz-creer3d.js
(window.__dzCreer3d) ; le maillon ne pose qu'un hôte et range l'ancien formulaire :
  P1 : dans `DzGameAssetsHub`, l'onglet « 3d » rend un <div data-dz-creer3d-hote> dont la ref (fonction, aucun hook :
       x.useState( reste à 731) appelle window.__dzCreer3d.monter (idempotent), PUIS l'ancien `DzGameAssets` dans un
       <div data-dz-creer3d-ancien> que l'écran replie (bouton « Afficher l'ancien formulaire 3D »).
Clés dzT : frontend/shared/i18n/creer3d.json (FR/EN), assemblées par scripts/i18n_assembler.py.
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS dzapparence (dont il sonde le marqueur) ; il garde un .js.bak_dzcreer3d le temps de l'écriture
puis le SUPPRIME. Son INVERSE est `avant_dzcreer3d` dans backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici),
appelé EN TÊTE de `avant_dzapparence`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire ne contient
de fin de ligne ; l'ancre est hors des couches __DZ_*_BEGIN__. DÉFAIRE le maillon AVANT de changer ses paires.
Banc : backend/tests/test_creer3d.py.
Run : python scripts/patch_bundle_dzcreer3d.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzcreer3d")
TAG = "dzcreer3d"
MARKER = "/*dzcreer3d*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzapparence", "/*dzapparence*/", 1),
    ("hub", "function DzGameAssetsHub({variant:e}){", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

_ANCRE = 'children:r.jsx(DzGameAssets,{variant:e})},"p3d")'
_HOTE = (MARKER + 'r.jsx("div",{"data-dz-creer3d-hote":"1",ref:function(el){if(el&&window.__dzCreer3d)'
         'window.__dzCreer3d.monter(el)}},"c3d"),')
_ANCIEN = 'r.jsx("div",{"data-dz-creer3d-ancien":"1",children:r.jsx(DzGameAssets,{variant:e})},"a3d")'

PAIRES = [
    # P1 : l'hôte de l'écran Créer en tête de l'onglet 3D, l'ancien formulaire rangé dessous
    (_ANCRE, 'children:[' + _HOTE + _ANCIEN + ']},"p3d")'),
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
    """L'inverse exact (lu par avant_dzapparence dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzapparence")
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
            or neuf.count(CONFIRMER) != 30 or neuf.count("function DzGameAssetsHub({variant:e}){") != 1
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
