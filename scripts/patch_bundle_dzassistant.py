# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzassistant.py
"""Maillon de queue : « Créer l'espace » de Réglages › Espaces ouvre l'ASSISTANT de création en quatre temps
(t308 tâche 4, 26/10/2026, plan docs/superpowers/plans/2026-10-26-t308-assistant-espace.md, spec
docs/superpowers/specs/2026-10-25-boite-a-outils-design.md §5.3).

L'assistant vit dans frontend/shared/dz-espace-assistant.js (window.__dzEspaceAssistant, chargé par
frontend/dist/index.html). Ici, deux paires dans DzEspaces (posé par le maillon dzespace, HORS de tout bloc de couche
__DZ_*_BEGIN__ : mesuré le 26/10 à l'offset 1 138 023, avant SONVFX qui commence à 1 225 208) :
  P1 la soumission du formulaire `data-dz-espace-nouveau` ouvre l'assistant avec le nom et la couleur saisis ; au
     retour (un espace créé, terminé ou non), la liste se relit par `agir` (liste, cache du rail, deepotus:espace-refresh)
     et le nom saisi s'efface. SANS le script partagé, l'ancien formulaire rapide reste le repli (l'ancre est gardée
     entière derrière le crochet). Le formulaire reste : la scène du guide t211 surligne `[data-dz-espace-nouveau]` ;
  P2 le bouton « Créer l'espace » n'est plus grisé quand le nom est vide (l'assistant le demande à l'étape 1) — il
     l'est encore sans le script partagé — et porte `data-dz-espace-assistant-ouvrir` (localisateur de l'assistant F1).
Le reste de DzEspaces ne change pas. AUCUN `x.useState(` ajouté (731) ; v2.8.0 ×4, DzTracks 181, confirmations ×30
intouchés. Textes : clés espaces.assistant.* dans frontend/shared/i18n/espaces.json (FR/EN), lues par le script partagé.

Maillon de QUEUE, APRÈS dzagentplan (dont il sonde le marqueur) ; il garde un .js.bak_dzassistant le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzassistant` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzagentplan`. Lecture et écriture
en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer ses
paires (`defaire` relit les paires d'ici).
Banc : backend/tests/test_espace_assistant_ecran.py.
Run : python scripts/patch_bundle_dzassistant.py [--check]
"""
import pathlib
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzassistant")
TAG = "dzassistant"
MARKER = "/*__dzassistant*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzagentplan", "/*__dzagentplan*/", 1),
    ("dzespace", "function DzEspaces(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

_SOUMETTRE = 'onSubmit:function(ev){ev.preventDefault();'
_RAPIDE = 'if(!st.nom.trim())return;'
_BOUTON = 'disabled:st.busy||!st.nom.trim(),style:bt,children:dzT("espaces.nouveau.creer")'
PAIRES = [
    # P1 : la soumission ouvre l'assistant (nom et couleur saisis) ; l'ancien formulaire rapide reste le repli
    (_SOUMETTRE + _RAPIDE,
     _SOUMETTRE + 'if(' + MARKER + 'window.__dzEspaceAssistant){window.__dzEspaceAssistant.ouvrir({nom:st.nom.trim(),'
     'couleur:st.couleur}).then(function(id){id&&agir(Promise.resolve(),!0).then(function(){maj({nom:""})})});return}'
     + _RAPIDE),
    # P2 : « Créer l'espace » actif même nom vide (l'assistant le demande), localisateur de l'assistant
    (_BOUTON,
     'disabled:st.busy||!window.__dzEspaceAssistant&&!st.nom.trim(),"data-dz-espace-assistant-ouvrir":"1",style:bt,'
     'children:dzT("espaces.nouveau.creer")'),
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
    """L'inverse exact (lu par avant_dzassistant dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzassistant")
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
