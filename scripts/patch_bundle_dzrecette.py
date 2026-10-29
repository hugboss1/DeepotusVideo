# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzrecette.py
"""Maillon de queue : la RECETTE de génération suit le rendu — Bibliothèque → Quick / Studio (t283, 23/10/2026).

Trois paires, toutes HORS des blocs de couche (MONTAGE, SONVFX… ne sont jamais touchés) :
  R1 les aides de frontend/patches/recette.js, APLATIES en une ligne, devant `function __dzRelancer(j,ev){` :
     __dzRecetteLire / __dzRecetteQuick / __dzRecetteStudio / DzRecetteRendu (voir l'en-tête de la source) ;
  R2 « Envoyer vers » d'un rendu : « Quick — reprendre la recette » et « Studio — refaire la génération », après
     « Studio — nouveau graphe » (qui garde son rôle : re-rendre le clip) ;
  R3 la fiche modale de la Bibliothèque : le panneau DzRecetteRendu après les images semblables, avant le média ;
     t346 (29/10/2026) : suivi du bouton DzRecetteExport (« Exporter la recette » : skill ZIP + PDF de fabrication).
Le serveur donne la recette (GET /api/jobs/{id}/recette, services/recette_rendu.py) ; aucun coût n'est repris.
AUCUN `x.useState(` ajouté (hooks par alias : 731 inchangé) ; v2.8.0 ×4, DzTracks 181, confirmations ×30 intouchés.
Textes : clés dzT `recette.*` dans frontend/shared/i18n/recette.json (FR/EN).

Maillon de QUEUE, APRÈS dzsonvfx (dont il sonde le marqueur) ; il garde un .js.bak_dzrecette le temps de l'écriture
puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzrecette` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzsonvfx`. Lecture et écriture en
OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne.
Banc : backend/tests/test_recette_rendu.py.
Run : python scripts/patch_bundle_dzrecette.py [--check]
"""
import pathlib
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzrecette")
SOURCE = RACINE / "frontend" / "patches" / "recette.js"
TAG = "dzrecette"
MARKER = "/*__dzrecette*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzsonvfx", "function DzSonVfxHub(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]


def aplatir(src: str) -> str:
    """Même règle que patch_bundle_dzsonvfx.aplatir : commentaires « /* » de lignes entières retirés, lignes rognées,
    jointes par une espace."""
    out, dans = [], False
    for ligne in src.splitlines():
        t = ligne.strip()
        if dans:
            dans = not t.endswith("*/")
            continue
        if t.startswith("/*"):
            dans = not t.endswith("*/")
            continue
        if t.startswith(("//", "(", "[")):
            raise SystemExit(f"[{TAG}] ligne interdite dans la source : {t[:60]!r}")
        if t:
            out.append(t)
    return " ".join(out)


AIDES = aplatir(SOURCE.read_bytes().decode("utf-8"))

_ENVOI = 'items.push(dzSendStudioRendu(m,nom,onClose));'
PAIRES = [
    # R1 : les aides
    ("function __dzRelancer(j,ev){", AIDES + "function __dzRelancer(j,ev){"),
    # R2 : Envoyer vers d'un rendu
    (_ENVOI, _ENVOI
     + 'items.push({ic:"dz-action-rouvrir-quick",g:"⚡",lbl:dzT("recette.envoyer.quick"),'
       'fn:function(){onClose&&onClose();__dzRecetteQuick(m.jobId,!1)}});'
     + 'items.push({ic:"dz-nav-studio",g:"🎬",lbl:dzT("recette.envoyer.studio"),'
       'fn:function(){onClose&&onClose();__dzRecetteStudio(m.jobId,!1)}});'),
    # R3 : le panneau de la fiche, après les « images semblables » et avant le média (l'enchaînement DzLignee →
    # DzFiche → DzCommentaires → DzSemblables est épinglé par les bancs test_library_*_ecran)
    ('r.jsx(DzSemblables,{m:m,liste:l,ouvrir:y}),m.kind==="sprite2d"',
     'r.jsx(DzSemblables,{m:m,liste:l,ouvrir:y}),r.jsx(DzRecetteRendu,{m:m,fermer:()=>y(null)}),'
     'r.jsx(DzRecetteExport,{m:m}),m.kind==="sprite2d"'),
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
    """L'inverse exact (lu par avant_dzrecette dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzrecette")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    if "\n" in AIDES or MARKER not in AIDES or "x.useState(" in AIDES:
        raise SystemExit(f"[{TAG}] source mal aplatie (fin de ligne, marqueur absent ou x.useState( direct)")
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
