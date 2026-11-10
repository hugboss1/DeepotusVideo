# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzplanifaff.py
"""Maillon de queue : deux défauts d'AFFICHAGE du Planificateur (10/11/2026).

Ce qu'il pose (TROIS ancres uniques, relevées le 10/11 sur le bundle de 68f475cc, HORS de tout bloc de couche
__DZ_*_BEGIN__, vérifié à l'écriture par `hors_couche`) :
  P1 le graphe d'acheminement (composant Fm) ne disait « auto possible » que pour Telegram et X : la condition
     codée en dur `I==="telegram"&&…||I==="x"&&…` ignorait YouTube et Instagram, que le serveur publie pourtant
     seul (marketing.auto_channels()). Le maillon AJOUTE après elle, derrière le MARKER /*dzplanifaff*/ :
     `||!!(o&&(Array.isArray(o.auto_channels)?o.auto_channels.indexOf(I)>=0:o[I+"_enabled"]))` — la liste
     `auto_channels` que /api/health expose désormais, à défaut le drapeau `<canal>_enabled` (ancien serveur).
     Le `I==="whatsapp"||` de dzdiffusion, posé plus haut, est intact.
  P2 le titre du calendrier « Scheduler » passe par dzT("scheduler.calendrier.titre") (FR « Planificateur »).
  P3 le bouton « Analytics » du calendrier passe par dzT("scheduler.calendrier.analytics") (FR « Statistiques »).
Les deux clés vivent dans frontend/shared/i18n/planif_news.json (écrit à la main, assemblé par
scripts/i18n_assembler.py).
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS dzigformat (dont il sonde le marqueur) ; il garde un .js.bak_dzplanifaff le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzplanifaff` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzigformat`. Lecture et écriture
en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne.
DÉFAIRE le maillon AVANT de changer ses paires (`defaire` relit les paires d'ici).
Banc : backend/tests/test_planif_affichage.py.
Run : python scripts/patch_bundle_dzplanifaff.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzplanifaff")
TAG = "dzplanifaff"
MARKER = "/*dzplanifaff*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzigformat", "/*dzigformat*/", 1),
    ("dzdiffusion", "/*dzdiffusion*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

_X_AUTO = 'I==="x"&&!!(o!=null&&o.x_enabled)'
_SUITE_GRAPHE = ';return r.jsxs(ss,{pos:i[`ch:${I}`]'
AUTO_SERVEUR = ('||!!(o&&(Array.isArray(o.auto_channels)?o.auto_channels.indexOf(I)>=0'
                ':o[I+"_enabled"]))')
_ANALYTICS = 'onClick:function(){__dzSchedAnalytics()},children:'

PAIRES = [
    # P1 : « auto possible » d'après la liste du serveur (YouTube, Instagram…), pas seulement Telegram et X
    (_X_AUTO + _SUITE_GRAPHE, _X_AUTO + MARKER + AUTO_SERVEUR + _SUITE_GRAPHE),
    # P2 : le titre du calendrier
    ('children:"Scheduler"})', 'children:dzT("scheduler.calendrier.titre")})'),
    # P3 : le bouton des statistiques du calendrier
    (_ANALYTICS + '"Analytics"})', _ANALYTICS + 'dzT("scheduler.calendrier.analytics")})'),
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
    """L'inverse exact (lu par avant_dzplanifaff dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzplanifaff")
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
