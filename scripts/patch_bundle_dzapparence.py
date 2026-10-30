# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzapparence.py
"""Maillon de queue : la PALETTE de Réglages › Apparence (t382, lot « Réglages : chemins & apparence », 30/10/2026,
plan docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md, décision D5).
Le panneau vit dans frontend/shared/dz-apparence.js (window.__dzApparence) ; le maillon ne pose qu'un hôte :
  P1 : dans Réglages › Apparence (`Cm`), après l'aide et AVANT la carte des animations, un <div
       data-dz-apparence-hote> dont la ref (fonction, aucun hook : x.useState( reste à 731) appelle
       window.__dzApparence.monter (idempotent : la ref est rappelée à chaque rendu).
Clés dzT : frontend/shared/i18n/apparence.json (FR/EN), assemblées par scripts/i18n_assembler.py.
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS dzfils (dont il sonde le marqueur) ; il garde un .js.bak_dzapparence le temps de l'écriture
puis le SUPPRIME. Son INVERSE est `avant_dzapparence` dans backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici),
appelé EN TÊTE de `avant_dzfils`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de
fin de ligne ; l'ancre est hors des couches __DZ_*_BEGIN__. DÉFAIRE le maillon AVANT de changer ses paires.
Banc : backend/tests/test_apparence_ecran.py.
Run : python scripts/patch_bundle_dzapparence.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzapparence")
TAG = "dzapparence"
MARKER = "/*dzapparence*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzfils", "/*dzfils*/", 1),
    ("apparence", "function Cm(){", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

HOTE = (MARKER + 'r.jsx("div",{"data-dz-apparence-hote":"1",ref:function(el){if(el&&window.__dzApparence)'
        'window.__dzApparence.monter(el)}}),')
_AIDE = 'children:dzT("reglages.apparence.aide")}),'
_CARTE = 'r.jsxs(jt,{style:{padding:14},children:['

PAIRES = [
    # P1 : l'hôte de la palette, entre l'aide de Réglages › Apparence et la carte des animations
    (_AIDE + _CARTE, _AIDE + HOTE + _CARTE),
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
            or neuf.count(CONFIRMER) != 30 or neuf.count("function Cm(){") != 1
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
