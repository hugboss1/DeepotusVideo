# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzlogiciels3d.py
"""Maillon de queue : l'onglet « Moteurs et logiciels 3D » de Réglages (t521, 13/11/2026, lot 1 Blender et Godot ;
banc backend/tests/test_logiciels3d_t521.py). Le panneau vit dans frontend/shared/dz-logiciels3d.js
(window.__dzLogiciels3d.monter) ; le maillon ne pose que la porte d'entrée, comme dzmcp :
  La section s'appelle « moteurs » (lettres seules : test_agent_connaissance et test_reglages_diagnostic relisent la
  liste `ym` avec [a-z]+) ; ses textes gardent le préfixe logiciels3d.*.
  P1 : « moteurs » dans la liste blanche ?section= (`ym`), après « paths » (hors du remplacement de dzmcp) ;
  P2 : l'onglet, juste après « Chemins », libellé dzT("logiciels3d.reglages.onglet") ;
  P3 : le corps de l'onglet, avant la branche « personas » (hors du remplacement de dzmcp), ouvert par le MARKER : un
       <div data-dz-logiciels3d-hote> dont la ref (fonction, aucun hook : x.useState( reste à 731) appelle
       window.__dzLogiciels3d.monter ;
  P4 : la rubrique de la recherche des Réglages (dzRubriques), après « paths ».
  Aucune paire ne touche un remplacement de dzmcp : son --check reste « déjà appliqué ».
Clés dzT : frontend/shared/i18n/logiciels3d.json (FR/EN), assemblées par scripts/i18n_assembler.py.
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS dzclesguides (t520, dont il sonde le marqueur) ; il garde un .js.bak_dzlogiciels3d le temps de
l'écriture puis le SUPPRIME. Son INVERSE est `avant_dzlogiciels3d` dans backend/tests/_i18n_l1_aide.py (lu sur les
PAIRES d'ici), appelé EN TÊTE de `avant_dzclesguides`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de
ligne. DÉFAIRE le maillon AVANT de changer ses paires (`defaire` relit les paires d'ici).
Run : python scripts/patch_bundle_dzlogiciels3d.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzlogiciels3d")
TAG = "dzlogiciels3d"
MARKER = "/*dzlogiciels3d*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzclesguides", "/*dzclesguides*/", 4),
    ("dzmcp", "/*dzmcp*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

HOTE = ('s==="moteurs"&&r.jsx("div",{"data-dz-logiciels3d-hote":"1",ref:function(el){if(el&&window.__dzLogiciels3d)'
        'window.__dzLogiciels3d.monter(el)}}),')

PAIRES = [
    # P1 : la liste blanche ?section= (et dz-reglages-section), après « paths »
    ('"paths","news"', '"paths","moteurs","news"'),
    # P2 : l'onglet, juste après « Chemins »
    ('{k:"paths",l:dzT("reglages.onglet.chemins")},',
     '{k:"paths",l:dzT("reglages.onglet.chemins")},{k:"moteurs",l:dzT("logiciels3d.reglages.onglet")},'),
    # P3 : le corps, avant la branche « personas » ; le marqueur l'ouvre
    ('s==="personas"&&r.jsx(jm', MARKER + HOTE + 's==="personas"&&r.jsx(jm'),
    # P4 : la rubrique de la recherche des Réglages, après « paths »
    ('paths:dzT("reglages.onglet.chemins"),', 'paths:dzT("reglages.onglet.chemins"),moteurs:dzT("logiciels3d.reglages.onglet"),'),
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
    """L'inverse exact (lu par avant_dzlogiciels3d dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzlogiciels3d")
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
            or neuf.count(CONFIRMER) != 30 or neuf.count("\r\n") != crlf):
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
