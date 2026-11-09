# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzigformat.py
"""Maillon de queue : le FORMAT Instagram d'un post dans l'éditeur de post du Planificateur (t494, lot G4 « boucle de
croissance », 09/11/2026, conception docs/superpowers/specs/2026-11-09-getripping-design.md).

Ce qu'il pose (UNE ancre unique, relevée le 09/11 sur le bundle de 9ccd9224, HORS de tout bloc de couche
__DZ_*_BEGIN__, vérifié à l'écriture par `hors_couche`) :
  P1 entre le champ « Canaux » et le champ de la légende de l'éditeur de post : quand le post vise le canal
     `instagram`, le point de montage `<div data-dz-igformat-hote={post.id}>` dont le ref appelle
     window.__dzIgFormat.monter(nœud, post.id, {statut}) (frontend/shared/dz-ig-format.js, chargé par
     frontend/dist/index.html ; `monter` est idempotent : le ref est rappelé à chaque rendu). Sa clé = le post :
     changer de post le remonte. Le MARKER /*dzigformat*/ ouvre ce point de montage.
L'ancre est le raccord entre deux champs : `},j.id)})})}),` (fin de la grille des canaux) puis `r.jsxs(ie,{label:`
(début du champ suivant). Le montage se glisse ENTRE les deux : aucun remplacement d'un maillon amont n'est coupé (le
libellé traduit du champ suivant commence après, DzPostComptes de dzespace finit avant), ce que le banc vérifie en
rejouant leurs `--check`.
Épingles intouchées : x.useState( 731 (aucun hook : l'état vit dans le module partagé), v2.8.0 x4, DzTracks 181,
`await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS dzmethodes (t433, dont il sonde le marqueur) ; il garde un .js.bak_dzigformat le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzigformat` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzmethodes`. Lecture et écriture en
OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne.
DÉFAIRE le maillon AVANT de changer ses paires (`defaire` relit les paires d'ici).
Banc : backend/tests/test_igformat_ecran.py.
Run : python scripts/patch_bundle_dzigformat.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzigformat")
TAG = "dzigformat"
MARKER = "/*dzigformat*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzmethodes", "/*dzmethodes*/", 1),
    ("dzdiffusion", "/*dzdiffusion*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

_FIN_CANAUX = '},j.id)})})}),'
_CHAMP_SUIVANT = 'r.jsxs(ie,{label:'
MONTER = "window.__dzIgFormat&&window.__dzIgFormat.monter(n,e.id,{statut:e.status})"
MONTAGE = (MARKER + 'e.channels.includes("instagram")&&r.jsx("div",{"data-dz-igformat-hote":e.id,'
           'ref:function(n){n&&' + MONTER + '}},"dzigf:"+e.id),')

PAIRES = [
    # P1 : entre « Canaux » et la légende, le point de montage du format Instagram (post qui vise instagram)
    (_FIN_CANAUX + _CHAMP_SUIVANT, _FIN_CANAUX + MONTAGE + _CHAMP_SUIVANT),
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
    """L'inverse exact (lu par avant_dzigformat dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzigformat")
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
