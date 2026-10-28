# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzinspiration.py
"""Maillon de queue : le bouton « Depuis une inspiration » du Planificateur (t313, 28/10/2026, plan
docs/superpowers/plans/2026-10-28-t313-inspiration.md, Décision 10 ; spec boîte à outils §7.4).

Ce qu'il pose (ancre unique, relevée le 28/10 sur le bundle de 385e01a1, HORS de tout bloc de couche __DZ_*_BEGIN__,
vérifié à l'écriture par `hors_couche`) :
  P1 dans la barre du calendrier du Planificateur (Dm), juste après le bouton « Nouveau post », un bouton
     dzT("inspiration.planif.bouton") (icône Deepotus Glyph `dz-media-image`, aucune icône neuve ; aide
     dzT("inspiration.planif.aide")) qui appelle window.__dzInspiration.ouvrir() (frontend/shared/dz-inspiration.js,
     chargé par frontend/dist/index.html). Le MARKER /*dzinspiration*/ ouvre ce bouton. Le brouillon créé recharge le
     Planificateur par « deepotus:schedule-recharger » (écouté depuis t309, maillon dzgardeclient) : rien d'autre à
     toucher dans le bundle.
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30 (les
confirmations de dépense vivent dans le module partagé, pas dans le bundle).

Maillon de QUEUE, APRÈS whatsapppage (t311, dont il sonde le marqueur) ; il garde un .js.bak_dzinspiration le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzinspiration` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzcapture` (fusion t320 :
rejoué APRÈS dzcapture, t315, qui défait d'abord ce maillon puis le sien). Lecture et écriture
en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer ses
paires (`defaire` relit les paires d'ici).
Banc : backend/tests/test_inspiration_ecran.py.
Run : python scripts/patch_bundle_dzinspiration.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzinspiration")
TAG = "dzinspiration"
MARKER = "/*dzinspiration*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("whatsapppage", "/*whatsapppage*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

_NOUVEAU = ('r.jsx(K,{variant:"primary",size:"sm",icon:"dz-action-ajouter",glow:!0,onClick:l,'
            'children:dzT("scheduler.calendrier.nouveau_post")}),')
OUVRIR = "window.__dzInspiration&&window.__dzInspiration.ouvrir()"
BOUTON = ('r.jsx(K,{variant:"outline",size:"sm",icon:"dz-media-image",title:dzT("inspiration.planif.aide"),'
          'onClick:function(){' + OUVRIR + '},children:dzT("inspiration.planif.bouton")}),')

PAIRES = [
    # P1 : « Depuis une inspiration » après « Nouveau post » (le marqueur l'ouvre)
    (_NOUVEAU, _NOUVEAU + MARKER + BOUTON),
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
    """L'inverse exact (lu par avant_dzinspiration dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzinspiration")
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
        print(f"[{TAG}] à appliquer ({len(PAIRES)} paire)")
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
