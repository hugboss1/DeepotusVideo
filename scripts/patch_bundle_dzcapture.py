# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzcapture.py
"""Maillon de queue : les ÉCRANS SECRETS de Réglages portent `data-dz-secret="ecran"` (t315, 28/10/2026, plan
docs/superpowers/plans/2026-10-28-t315-capture.md tâche 5, spec boîte à outils §8.2). Pendant une capture de l'app
(/shared/dz-capture.js), tout élément marqué data-dz-secret est flouté dans la page (CSS_MASQUE de
/shared/dz-capture-logique.js) ET caché par le compositeur (calque « caviardage ») : le rendu et le live ne montrent
jamais une clé, un jeton, le coffre, l'appairage ni la page Appareils.

Ce qu'il pose (ancre unique, relevée le 28/10 sur le bundle de 385e01a1, HORS de tout bloc de couche __DZ_*_BEGIN__,
vérifié à l'écriture par `hors_couche`) :
  P1 le panneau de droite de Réglages (`div.scroll`, celui qui affiche la section `s`) reçoit
     `"data-dz-secret": "ecran"` quand la section est l'une de SECRETS (coffre, appareils, keys, accounts,
     transfert), rien sinon. Le MARKER /*dzcapture*/ ouvre l'attribut.
Les champs `type="password"` n'ont pas besoin du maillon : le sélecteur SELECTEURS_SECRETS les couvre tous.
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS whatsapppage (t311, dont il sonde le marqueur) ; il garde un .js.bak_dzcapture le temps de
l'écriture puis le SUPPRIME. Son INVERSE est `avant_dzcapture` dans backend/tests/_i18n_l1_aide.py (lu sur les PAIRES
d'ici), appelé EN TÊTE de `avant_whatsapppage`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire ne
contient de fin de ligne. DÉFAIRE le maillon AVANT de changer ses paires (`defaire` relit les paires d'ici).
Banc : backend/tests/test_capture_secrets.py.
Run : python scripts/patch_bundle_dzcapture.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzcapture")
TAG = "dzcapture"
MARKER = "/*dzcapture*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("
# les sections de Réglages qui montrent un secret (clé, aperçu de clé, identifiant OAuth, QR d'appairage, coffre,
# mot de passe d'archive) ; liste figée par test_capture_secrets.py
SECRETS = ("coffre", "appareils", "keys", "accounts", "transfert")

SONDE_AMONT = [
    ("whatsapppage", "/*whatsapppage*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

_PANNEAU = 'r.jsxs("div",{className:"scroll",style:{overflowY:"auto",padding:24,maxWidth:880},children:[s==="accounts"&&r.jsx(Tm,{})'
ATTR = MARKER + '"data-dz-secret":' + "[" + ",".join('"%s"' % x for x in SECRETS) + '].indexOf(s)>=0?"ecran":void 0,'

PAIRES = [
    # P1 : le panneau de droite de Réglages, marqué secret pour les sections de SECRETS
    (_PANNEAU, _PANNEAU.replace('{className:"scroll",', '{' + ATTR + 'className:"scroll",', 1)),
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
    """L'inverse exact (lu par avant_dzcapture dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzcapture")
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
