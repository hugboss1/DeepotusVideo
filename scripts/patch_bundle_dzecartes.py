# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzecartes.py
"""Maillon de queue : la puce « N écartés ce jour » de l'écran News ne déroule plus une bulle géante (t375, lot B
« News », plan docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md).
Avant : le `title` du span porteur de la puce listait TOUS les articles écartés, un par ligne (« titre — motif ») :
des centaines de lignes dès que la fenêtre de fraîcheur est courte.
  P1 : `dzNewsEcartesResume(l)`, posée JUSTE AVANT l'écran (`pm`) : le total, un compte par motif (du plus fréquent au
       plus rare, les motifs arrivent déjà traduits du serveur), puis l'indication « Tout afficher ».
  P2 : la bulle de la puce devient ce résumé ; la liste complète passe dans un déroulé natif <details> qui suit la
       puce (« Tout afficher ») : panneau en surimpression, borné à 50vh et défilant, titre et motif par ligne, aux
       jetons de la charte (aucun rayon, aucune couleur en dur). Aucun état React neuf : le déroulé s'ouvre seul.
       Le MARKER /*dzecartes*/ précède la puce.
Clés dzT neuves (frontend/shared/i18n/news_survol.json : news.json est GÉNÉRÉ par la saisie L2) : news.liste.ecartes_resume, news.liste.ecartes_tout,
news.liste.ecartes_tout_aide.

Maillon de QUEUE, APRÈS dzcurseur (dont il sonde le marqueur) ; il garde un .js.bak_dzecartes le temps de l'écriture
puis le SUPPRIME. Son INVERSE est `avant_dzecartes` dans backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici),
appelé EN TÊTE de `avant_dzcurseur`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire ne contient
de fin de ligne ; les ancres sont hors des couches __DZ_*_BEGIN__. DÉFAIRE le maillon AVANT de changer ses paires.
Banc : backend/tests/test_news_ecartes_ecran.py.
Run : python scripts/patch_bundle_dzecartes.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzecartes")
TAG = "dzecartes"
MARKER = "/*dzecartes*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzcurseur", "/*dzcurseur*/", 1),
    ("ecran", "function pm({variant:e,go:Go}){", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

ECRAN = "function pm({variant:e,go:Go}){"
RESUME = ('function dzNewsEcartesResume(l){var m={},o=[];(l||[]).forEach(function(z){var k=z.motif||"?";'
          'if(!(k in m)){m[k]=0;o.push(k)}m[k]++});'
          'o.sort(function(a,b){return m[b]-m[a]});'
          'return[dzT("news.liste.ecartes_resume",{n:(l||[]).length})].concat(o.map(function(k){'
          'return m[k]+" · "+k})).concat([dzT("news.liste.ecartes_tout_aide")]).join("\\n")}')

PUCE = ('r.jsx("span",{title:ranked.ecartes.map(function(z){return z.title+" — "+z.motif}).join("\\n"),'
        'children:r.jsx(te,{tone:"amber",style:{whiteSpace:"nowrap"},'
        'children:dzT("news.liste.ecartes",{n:ranked.ecartes.length})})})')
PUCE_NEUVE = (MARKER + 'r.jsxs(r.Fragment,{children:['
              'r.jsx("span",{title:dzNewsEcartesResume(ranked.ecartes),'
              'children:r.jsx(te,{tone:"amber",style:{whiteSpace:"nowrap"},'
              'children:dzT("news.liste.ecartes",{n:ranked.ecartes.length})})}),'
              'r.jsxs("details",{className:"dz-news-ecartes",style:{position:"relative"},children:['
              'r.jsx("summary",{style:{cursor:"pointer",listStyle:"none",whiteSpace:"nowrap",fontSize:12,'
              'color:"var(--ink-soft)",padding:"2px 8px",border:"1px solid var(--stroke)"},'
              'children:dzT("news.liste.ecartes_tout")}),'
              'r.jsx("div",{role:"list",style:{position:"absolute",top:"calc(100% + 4px)",left:0,zIndex:40,'
              'width:"min(560px, 80vw)",maxHeight:"50vh",overflow:"auto",background:"var(--bg-panel)",'
              'border:"1px solid var(--stroke-strong)",boxShadow:"0 8px 24px var(--bg-base)",padding:"4px 0"},'
              'children:ranked.ecartes.map(function(z){return r.jsxs("div",{role:"listitem",'
              'style:{display:"flex",gap:10,padding:"4px 12px",fontSize:12,borderBottom:"1px solid var(--stroke)"},'
              'children:['
              'r.jsx("span",{style:{flex:1,minWidth:0,color:"var(--ink)",overflow:"hidden",textOverflow:"ellipsis",'
              'whiteSpace:"nowrap"},children:z.title}),'
              'r.jsx("span",{style:{color:"var(--ink-muted)",whiteSpace:"nowrap"},children:z.motif})]},z.id)})})]})]})')

PAIRES = [
    # P1 : le résumé du survol, défini avant l'écran
    (ECRAN, RESUME + ECRAN),
    # P2 : la puce au résumé + « Tout afficher » (déroulé natif)
    (PUCE, PUCE_NEUVE),
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
    """L'inverse exact (lu par avant_dzecartes dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzecartes")
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
            or neuf.count(CONFIRMER) != 30 or neuf.count(ECRAN) != 1 or neuf.count("\r\n") != crlf):
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
