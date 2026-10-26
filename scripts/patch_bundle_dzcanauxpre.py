# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzcanauxpre.py
"""Maillon de queue : les écrans de création de brouillon n'envoient plus le canal X par défaut, le serveur reprend les
comptes du projet actif (t325 tâche 1, 26/10/2026, plan docs/superpowers/plans/2026-10-26-t325-canaux-preremplis.md,
spec docs/superpowers/specs/2026-10-25-boite-a-outils-design.md §5.4). L'héritage serveur est celui de t307
(`POST /api/schedule` sans `channels` ni `comptes`, repli ["x"] s'il n'y a aucun canal).
Deux paires, toutes deux HORS de tout bloc de couche __DZ_*_BEGIN__ (mesuré le 26/10/2026 sur le bundle de t308 : la
première à l'offset 692 531, la seconde à 1 018 799, avant SONVFX qui commence à 1 226 464 ; chaque ancre est unique) :
  P1 `__dzSendSched` (Bibliothèque › Envoyer vers › Planificateur, sortie du maillon libsend) : `post.channels||["x"]`
     devient « sans canaux (absents OU tableau vide), on retire la clé » ; des canaux explicites passent tels quels.
     Le MARKER /*dzcanauxpre*/ est collé à la fin de cette sortie (sans fin de ligne) ;
  P2 Planificateur › Nouveau post (composant d'origine, fonction A) : l'objet de createScheduledPost n'a plus
     `channels:["x"]`.
Rien d'autre ne change : AUCUN `x.useState(` ajouté (731) ; v2.8.0 x4, DzTracks 181, confirmations x30 intouchés. Le
serveur ne change pas.

Maillon de QUEUE, APRÈS dzassistant (t308, dont il sonde le marqueur) ; il garde un .js.bak_dzcanauxpre le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzcanauxpre` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzassistant`. Lecture et écriture en
OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer ses paires
(`defaire` relit les paires d'ici).
Banc : backend/tests/test_canaux_preremplis.py.
Run : python scripts/patch_bundle_dzcanauxpre.py [--check]
"""
import pathlib
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzcanauxpre")
TAG = "dzcanauxpre"
MARKER = "/*dzcanauxpre*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzassistant", "/*__dzassistant*/", 1),
    ("sendsched", "function __dzSendSched(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

PAIRES = [
    # P1 : __dzSendSched sans canaux (absents ou tableau vide) -> pas de clé, le serveur hérite ; explicites gardés
    ('post.channels=post.channels||["x"];post.status="draft";',
     'if(!(post.channels&&post.channels.length))delete post.channels;post.status="draft";' + MARKER),
    # P2 : Planificateur › Nouveau post n'envoie plus channels:["x"]
    ('title:"Untitled post",caption:"",channels:["x"],run_at:U.toISOString()',
     'title:"Untitled post",caption:"",run_at:U.toISOString()'),
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
    """L'inverse exact (lu par avant_dzcanauxpre dans _i18n_l1_aide)."""
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


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
        if partiel(s):
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzcanauxpre")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    if any("\n" in a + z or "x.useState(" in z for a, z in PAIRES):
        raise SystemExit(f"[{TAG}] paire fautive (fin de ligne ou x.useState( direct)")
    crlf = s.count("\r\n")
    if crlf < 15000 or s.count("\n") != crlf:
        raise SystemExit(f"[{TAG}] fins de ligne inattendues ({crlf} CRLF / {s.count(chr(10))} LF)")
    neuf = appliquer(s)
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
        shutil.copyfile(BAK, BUNDLE)
        raise
    finally:
        BAK.unlink(missing_ok=True)
    print(f"[{TAG}] appliqué")


if __name__ == "__main__":
    main()
