# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzmethodes.py
"""Maillon de queue : l'écran « Méthodes » dans la barre des applications (t433, lot M0 « Méthodes », 08/11/2026 ;
conception docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md §5). La page est autonome
(frontend/methodes/, montée sur /methodes comme /whatsapp) ; la barre l'ouvre dans une iframe.

Ce qu'il pose (ancres uniques relevées le 08/11 sur le bundle de 2a1bfe6c, toutes HORS de tout bloc de couche
__DZ_*_BEGIN__, vérifié à l'écriture par `hors_couche`) :
  P1 l'entrée de rail `{id:"methodes",…}` juste après la Bibliothèque : libellé dzT("methodes.rail.titre"), icône
     Deepotus Glyph `dz-action-lancer-recette` (résolue par __dzGlyphe ; aucune icône neuve), description
     dzT("methodes.rail.desc") (frontend/shared/i18n/methodes.json). Le MARKER /*dzmethodes*/ ouvre cette entrée ;
  P2 la vue : une iframe `/methodes/`, clé `pmethodes`, après celle de WhatsApp ;
  P3 `methodes` entre dans la liste blanche des vues (`?view=` et « deepotus:navigate ») : poussé dans `Yu` avant sa
     première lecture, sans toucher la liste elle-même (elle appartient aux remplacements d'assets2d et whatsapppage) ;
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS dzcreer3d (t389, dont il sonde le marqueur) ; il garde un .js.bak_dzmethodes le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzmethodes` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzcreer3d`. Lecture et écriture en
OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer ses
paires (`defaire` relit les paires d'ici).
Banc : backend/tests/test_methodes_ecran.py.
Run : python scripts/patch_bundle_dzmethodes.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzmethodes")
TAG = "dzmethodes"
MARKER = "/*dzmethodes*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzcreer3d", "/*dzcreer3d*/", 1),
    ("whatsapppage", "/*whatsapppage*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

_RAIL_BI = ('{id:"library",label:dzT("coque.rail.bibliotheque"),icon:"dz-nav-bibliotheque",'
            'desc:dzT("coque.rail.bibliotheque_desc")},')
_RAIL_A3 = '{id:"assets3d",'
RAIL_ME = ('{id:"methodes",label:dzT("methodes.rail.titre"),icon:"dz-action-lancer-recette",'
           'desc:dzT("methodes.rail.desc"),new:!0},')
_STYLE = 'style:{position:"absolute",inset:0,width:"100%",height:"100%",border:"0",background:"var(--bg-base)"}'
_VUE_WA = 's==="whatsapp"&&r.jsx("iframe",{src:"/whatsapp/",title:dzT("whatsapp.page.titre"),' + _STYLE + '},"pwhatsapp"),'
VUE_ME = 's==="methodes"&&r.jsx("iframe",{src:"/methodes/",title:dzT("methodes.page.titre"),' + _STYLE + '},"pmethodes"),'
# P3 : la liste `Yu` et son début `sg=Yu.includes(` sont DANS les remplacements des maillons amont (assets2d,
# whatsapppage) : on ne les touche pas ; « methodes » est poussé dans `Yu` juste avant sa première lecture, dans
# l'argument de `Yu.includes(` (expression virgule), ce qui sert aussi `deepotus:navigate` qui lit la même liste.
_VUES = 'oa.get("view"))?oa.get("view"):null,ag=oa.get("nosplash")'
VUES_ME = '(Yu.push("methodes"),oa.get("view")))?oa.get("view"):null,ag=oa.get("nosplash")'

PAIRES = [
    # P1 : l'entrée de rail, juste après la Bibliothèque (le marqueur l'ouvre)
    (_RAIL_BI + _RAIL_A3, _RAIL_BI + MARKER + RAIL_ME + _RAIL_A3),
    # P2 : la vue, une iframe /methodes/ après celle de WhatsApp
    (_VUE_WA, _VUE_WA + VUE_ME),
    # P3 : la liste blanche des vues (?view= et deepotus:navigate)
    (_VUES, VUES_ME),
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
    """L'inverse exact (lu par avant_dzmethodes dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzmethodes")
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
