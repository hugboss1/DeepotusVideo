# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzstudio.py
"""Maillon de queue : le STUDIO (menus Studio, t225-t229, 16/10/2026).

t225 — chaque lien atterrit au MILIEU du rond du port, à l'entrée comme à la sortie. Défaut relevé sur 02f8162c
(docs/superpowers/specs/2026-10-16-releve-menus-studio.md) : `qi` (géométrie des liens) et `ud` (rendu des ports)
calculaient chacun leur position. `qi` donnait x = 0 / bi et y = Ru+12+i·Mu (48+22i) ; le rond est rendu à x+1 / x+219
(bordure du nœud) et y = 1 + Ru + 10 + 8 (55+22i) ; un libellé long passait sur deux lignes (`alignItems:center`) et
le rond descendait encore de 7. Ce qu'il pose (ancres uniques, relevées le 16/10 sur 02f8162c) :
  - A0 : `dzPortGeo` = {b bordure, oy origine des lignes sous l'en-tête, p pas (Mu), lh hauteur de ligne, r rond},
    posé devant `qi` après les constantes du Studio : LA source unique de géométrie des ports ;
  - A1 : `qi` rend le centre du rond : x = b (entrée) / bi − b (sortie), y = b + Ru + oy + i·p + r/2 ;
  - A2 : `ud` pose la ligne à `oy + i·p`, de hauteur fixe `lh`, rond (`r`) ancré en HAUT (`alignItems:"flex-start"`),
    débordant de r/2 hors du nœud ;
  - A3 : l'étiquette tient sur UNE ligne (nowrap, ellipse, interligne lh) ; son `title` donne le libellé complet.
Le port `brand` absent (t226) et la hauteur du corps des ports (t227) ne sont PAS touchés ici : t226-t229 ajoutent
leurs familles de paires (B*, C*, D*, E*) à ce maillon.
Aucun useState ajouté (compte figé 731), aucun DzTracks, rien qui touche « v2.8.0 », aucun texte visible neuf (le
`title` réutilise le libellé et le type déjà affichés).

Maillon de QUEUE, APRÈS dzlogo (dont il sonde le marqueur) ; il garde un .js.bak_dzstudio le temps de l'écriture
puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzstudio` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzlogo`. Lecture et écriture
en OCTETS. Banc : backend/tests/test_studio_ancrage.py.
Run : python scripts/patch_bundle_dzstudio.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzstudio")
TAG = "dzstudio"
MARKER = "var dzPortGeo={"
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("dzlogo", "function DzLogoMarque(", 1),
    ("dzreglages", "function dzOuvrirReglages(", 1),
    ("spatialports", "function dzNodeInPorts(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

PAIRES = [
    ('Eh=30;function qi(',                                                                                  # A0
     'Eh=30;var dzPortGeo={b:1,oy:10,p:Mu,lh:16,r:16};function qi('),
    ('const l=t==="in"?0:bi,d=Ru+12+a*Mu;return{x:l,y:d}',                                                  # A1
     'const l=t==="in"?dzPortGeo.b:bi-dzPortGeo.b,d=dzPortGeo.b+Ru+dzPortGeo.oy+a*dzPortGeo.p+dzPortGeo.r/2;'
     'return{x:l,y:d}'),
    ('top:8+n*Mu+2,left:e==="in"?-8:"auto",right:e==="out"?-8:"auto",display:"flex",alignItems:"center",gap:6,'  # A2
     'flexDirection:e==="in"?"row":"row-reverse",width:130},children:[r.jsx("span",{"data-port-side":e,'
     '"data-port-id":t.id,onMouseDown:a=>{a.stopPropagation(),o(a)},onMouseUp:a=>{a.stopPropagation(),i(a)},'
     'style:{width:16,height:16,',
     'top:dzPortGeo.oy+n*dzPortGeo.p,left:e==="in"?-dzPortGeo.r/2:"auto",right:e==="out"?-dzPortGeo.r/2:"auto",'
     'display:"flex",alignItems:"flex-start",height:dzPortGeo.lh,gap:6,'
     'flexDirection:e==="in"?"row":"row-reverse",width:130},children:[r.jsx("span",{"data-port-side":e,'
     '"data-port-id":t.id,onMouseDown:a=>{a.stopPropagation(),o(a)},onMouseUp:a=>{a.stopPropagation(),i(a)},'
     'style:{width:dzPortGeo.r,height:dzPortGeo.r,'),
    ('r.jsxs("span",{style:{fontSize:10.5,color:"var(--ink-soft)",textAlign:e==="in"?"left":"right",'       # A3
     'padding:e==="in"?"0 0 0 4px":"0 4px 0 0"},children:[t.label||t.id,',
     'r.jsxs("span",{title:(t.label||t.id)+" · "+t.type,style:{fontSize:10.5,lineHeight:dzPortGeo.lh+"px",'
     'whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",minWidth:0,color:"var(--ink-soft)",'
     'textAlign:e==="in"?"left":"right",padding:e==="in"?"0 0 0 4px":"0 4px 0 0"},children:[t.label||t.id,'),
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
    """L'inverse exact (lu par avant_dzstudio dans _i18n_l1_aide)."""
    for ancre, remplace in reversed(PAIRES):
        if s.count(remplace) != 1:
            raise AssertionError(f"[{TAG}] remplacement x{s.count(remplace)} (attendu 1) : {remplace[:80]!r}")
        s = s.replace(remplace, ancre, 1)
    return s


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    crlf = s.count("\r\n")
    if crlf < 15000 or s.count("\n") != crlf:
        raise SystemExit(f"[{TAG}] fins de ligne inattendues ({crlf} CRLF / {s.count(chr(10))} LF)")
    neuf = appliquer(s)
    if neuf.count(MARKER) != MARKER_ATTENDU or defaire(neuf) != s:
        raise SystemExit(f"[{TAG}] aller-retour imparfait")
    if neuf.count("x.useState(") != 731 or neuf.count("v2.8.0") != 4 or neuf.count("DzTracks") != 181:
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
