# -*- coding: utf-8 -*-
# scripts/patch_bundle_dziglogin.py
"""Maillon de queue : « Relier par Instagram » dans le bloc Instagram de Réglages › Comptes connectés (t493, 26/11/2026,
lot G3 ; banc backend/tests/test_instagram_oauth_t493.py). Le panneau vit dans frontend/shared/dz-ig-relier.js
(window.__dzIgRelier.monter) ; le maillon ne pose que deux choses :
  P1 : les champs de l'application Instagram (IG_APP_ID, IG_APP_SECRET, IG_OAUTH_REDIRECT) APRÈS IG_BUSINESS_ID dans la
       liste `fields` du bloc Instagram : ils s'enregistrent comme les autres champs (POST /api/settings/keys, secret au
       coffre) ; le premier champ reste IG_ACCESS_TOKEN (le lien « Guide » de dzclesguides lit `k.fields[0].k`) ;
  P2 : un <span data-dz-ig-relier-hote> pour le seul bloc Instagram, AVANT le lien « Guide » posé par dzclesguides (sa
       pose reste un sous-texte intact : son --check reste « déjà appliqué ») ; sa ref (fonction, aucun hook :
       x.useState( reste à 731) appelle window.__dzIgRelier.monter.
Clés dzT : frontend/shared/i18n/igrelier.json (FR/EN), assemblées par scripts/i18n_assembler.py.
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS dzlogiciels3d (t521, dont il sonde le marqueur) ; il garde un .js.bak_dziglogin le temps de
l'écriture puis le SUPPRIME. Son INVERSE est `avant_dziglogin` dans backend/tests/_i18n_l1_aide.py (lu sur les PAIRES
d'ici), appelé EN TÊTE de `avant_dzlogiciels3d`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire
ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer ses paires (`defaire` relit les paires d'ici).
Run : python scripts/patch_bundle_dziglogin.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dziglogin")
TAG = "dziglogin"
MARKER = "/*dziglogin*/"
MARKER_ATTENDU = 2
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzlogiciels3d", "/*dzlogiciels3d*/", 1),
    ("dzclesguides", "/*dzclesguides*/", 4),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

_ID_COMPTE = '{k:"IG_BUSINESS_ID",label:dzT("reglages.comptes.champ.business_id")}]'
_CHAMPS = ('{k:"IG_APP_ID",label:dzT("igrelier.champ.app_id")},{k:"IG_APP_SECRET",label:dzT("igrelier.champ.app_secret")},'
           '{k:"IG_OAUTH_REDIRECT",label:dzT("igrelier.champ.redirect")}')
_GUIDE = "/*dzclesguides*/r.jsx(DzGuideCompte,{ck:k.fields[0].k}),"
HOTE = ('k.k==="instagram"&&r.jsx("span",{"data-dz-ig-relier-hote":"1",ref:function(el){if(el&&window.__dzIgRelier)'
        'window.__dzIgRelier.monter(el)}}),')

PAIRES = [
    # P1 : les champs de l'application Instagram, après l'ID du compte (le premier champ ne change pas)
    (_ID_COMPTE, _ID_COMPTE[:-1] + "," + MARKER + _CHAMPS + "]"),
    # P2 : le bouton « Relier par Instagram », avant le lien « Guide » de dzclesguides
    (_GUIDE, MARKER + HOTE + _GUIDE),
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
    """L'inverse exact (lu par avant_dziglogin dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dziglogin")
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
            or neuf.count(CONFIRMER) != 30 or neuf.count("\r\n") != crlf or neuf.count(_GUIDE) != 1):
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
