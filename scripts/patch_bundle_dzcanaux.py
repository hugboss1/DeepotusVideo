# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzcanaux.py
"""Maillon de queue : les CANAUX d'un projet dans la barre « Projet » de la Bibliothèque (t307 tâche 4, 25/10/2026,
plan docs/superpowers/plans/2026-10-25-t307-projets-canaux.md).

DzProjetsBar et dzProjCharger viennent du maillon libsons (bloc « Bibliothèque #78 PR B ») : on NE modifie PAS ce
maillon, on réécrit sa sortie dans le bundle final. Six paires, toutes DANS le bloc #78 (le banc
test_library_projets_ecran exécute ce bloc sous node : le composant des glyphes doit y vivre), HORS de toute fin de
ligne, et qui n'AJOUTENT que du texte (l'ancre d'origine reste entière dans son remplacement) :
  P1 les aides de frontend/patches/projet-canaux.js (DzProjetCanauxIcones), APLATIES en une ligne, devant
     `function DzProjetsBar({f,setF}){` ;
  P2 dzProjCharger garde `espace_id` et `canaux` de la vue du projet (GET /api/library/projets/{id}) ;
  P3 / P4 la barre écoute aussi « dz-projet-canaux » (émis par frontend/shared/dz-projet-canaux.js après
     l'enregistrement) et relit la liste des projets et le projet regardé ; on retire l'écoute au démontage ;
  P5 les glyphes des canaux du projet regardé, juste après la liste des projets (titre au survol : les comptes) ;
  P6 le bouton « Canaux » (glyphe dz-action-publier + dzT("projets.canaux.bouton"), écrit en clair au style du `bouton`
     de la barre, pour que l'extracteur du catalogue de l'assistant le lise) avant « État », qui appelle
     window.__dzProjetCanaux.ouvrir(f).
AUCUN `x.useState(` ajouté (hooks par alias : 731 inchangé) ; v2.8.0 ×4, DzTracks 181, confirmations ×30 intouchés ;
aucun jeton compté par un banc voisin dans la barre n'est touché (r.jsx(DzProjetsBar,…) ×1, `function DzProjetsBar(` ×1).
Textes : clés dzT `projets.canaux.*` dans frontend/shared/i18n/projets.json (FR/EN).

Maillon de QUEUE, APRÈS dzagentplan (dont il sonde le marqueur) ; il garde un .js.bak_dzcanaux le temps de l'écriture
puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzcanaux` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzagentplan`. Lecture et écriture en
OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer sa
source (`defaire` relit la source).
Banc : backend/tests/test_projets_canaux_ecran.py.
Run : python scripts/patch_bundle_dzcanaux.py [--check]
"""
import pathlib
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzcanaux")
SOURCE = RACINE / "frontend" / "patches" / "projet-canaux.js"
TAG = "dzcanaux"
MARKER = "/*__dzcanaux*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzagentplan", "/*__dzagentplan*/", 1),
    ("dzrecette", "/*__dzrecette*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
    ("libsons", "function DzProjetsBar(", 1),
]


def aplatir(src: str) -> str:
    """Même règle que patch_bundle_dzagentplan.aplatir : commentaires « /* » de lignes entières retirés, lignes rognées,
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

_BARRE = "function DzProjetsBar({f,setF}){"
_CHARGE = "return{id:d.id,nom:d.nom,epingle:!!d.epingle,"
_ECOUTE = 'window.addEventListener("dz-projets",h);'
_RETIRE = 'return function(){window.removeEventListener("dz-projets",h)}},[f&&f.id]);'
_AUTO = 'ch.push(bouton(ici?__dzGlT("dz-action-rangement-auto"'
_ETAT = 'ch.push(bouton(__dzGlT("dz-etat-information",dzT("biblio.projets.etat_bouton"),"▦")'
PAIRES = [
    # P1 : les aides (le composant des glyphes), devant la barre, DANS le bloc #78
    (_BARRE, AIDES + _BARRE),
    # P2 : le projet chargé garde son espace et ses canaux
    (_CHARGE, _CHARGE + "espace_id:d.espace_id,canaux:d.canaux||[],"),
    # P3 : la barre relit les projets après l'enregistrement des canaux
    (_ECOUTE, _ECOUTE + 'window.addEventListener("dz-projet-canaux",h);'),
    # P4 : et retire cette écoute au démontage
    (_RETIRE, 'return function(){window.removeEventListener("dz-projets",h);window.removeEventListener("dz-projet-canaux",h)}},[f&&f.id]);'),
    # P5 : les glyphes des canaux, juste après la liste des projets
    (_AUTO, 'ch.push(r.jsx(DzProjetCanauxIcones,{projet:f},"dzcanaux-ic"));' + _AUTO),
    # P6 : le bouton « Canaux », avant « État »
    #     (bouton écrit EN CLAIR, au style du `bouton` de la barre : l'extracteur du catalogue de l'assistant lit ses
    #     clés dzT, ce qu'il ne fait pas à travers la fabrique `bouton(lbl,titre,…)`)
    (_ETAT, 'ch.push(r.jsx("button",{type:"button","data-dz-projet-canaux-ouvrir":f.id,title:dzT("projets.canaux.aide"),'
            'onClick:function(){var P=window.__dzProjetCanaux;if(P&&typeof P.ouvrir==="function")P.ouvrir(f)},'
            'style:{height:24,padding:"0 9px",fontSize:11,borderRadius:12,cursor:"pointer",border:"1px solid var(--stroke)",'
            'background:"transparent",color:"var(--ink-soft)"},'
            'children:[__dzGl("dz-action-publier")," ",dzT("projets.canaux.bouton")]},"dzcanaux-bouton"));' + _ETAT),
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
    """L'inverse exact (lu par avant_dzcanaux dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzcanaux")
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
