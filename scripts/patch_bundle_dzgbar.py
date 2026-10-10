# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzgbar.py
"""Maillon de queue : la barre du graphe du Studio ne passe plus sous l'inspecteur (10/10/2026).

Mesure (puppeteer, inspecteur déplié) : la colonne centrale de la grille `260px 1fr 340px` fait 608 px à 1 440 et
848 px à 1 680, mais sa barre du graphe (Nouveau, Enregistrer, Recette, Importer, ouvrir un graphe, 9:16, Aperçu,
≈ $, Exécuter, Enregistrer le layout, Exporter) est une rangée flex de hauteur fixe 48 px qui ne passe jamais à la
ligne : ~1 300 px de contenu. À 1 440, Aperçu x=1320 et Exécuter x=1472 alors que l'inspecteur commence à x=1100 —
elementFromPoint au centre de ces boutons rend l'inspecteur : invisibles et non cliquables.

Ce qu'il pose :
  - la barre passe à la ligne (`flexWrap:"wrap"`, `rowGap:6`), en `minHeight:48` au lieu de `height:48` (padding
    vertical 6 px, `boxSizing:"border-box"`), marqueur `"data-dz-gbar":"1"` ;
  - `ref:__dzGbarRef` : un ResizeObserver écrit la hauteur réelle de la barre dans `--dz-gbar-h` sur la colonne ;
  - le bandeau d'état (jadis `top:56`, soit 48 + 8) se place à `calc(var(--dz-gbar-h, 48px) + 8px)`, donc sous la
    barre quelle que soit sa hauteur.

Maillon de QUEUE, APRÈS dzsched (dont il sonde le marqueur) ; comme lui, il garde un .js.bak_dzgbar le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Lecture et écriture en OCTETS. Son inverse vit
dans backend/tests/_i18n_l1_aide.py (`avant_dzgbar`, appelé en tête de `avant_dzsched`).

Run : python scripts/patch_bundle_dzgbar.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzgbar")
TAG = "dzgbar"
MARKER = '"data-dz-gbar":"1"'

SONDE_AMONT = [
    ("dzsched", '"data-dz-debord":"1"', 1),
    ("dzglyph", "function __dzGlyphe(", 1),
    ("i18nl2", 'dzT("studio.palette.titre")', 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

REF = ('function __dzGbarRef(el){if(!el||el.__dzGbarRo)return;var p=el.parentNode;function f(){p&&p.style.setProperty('
       '"--dz-gbar-h",Math.ceil(el.getBoundingClientRect().height)+"px")}f();try{el.__dzGbarRo=new ResizeObserver(f);'
       'el.__dzGbarRo.observe(el)}catch(_e){}}')

PAIRES = [
    ('r.jsxs("div",{style:{position:"absolute",top:0,left:0,right:0,zIndex:5,height:48,padding:"0 16px",background:"linear-gradient(180deg, #0a1422ee 0%, #0a142299 100%)",backdropFilter:"blur(8px)",borderBottom:"1px solid var(--stroke)",display:"flex",alignItems:"center",gap:10},children:[r.jsx(X,{name:"dz-nav-studio"',
     'r.jsxs("div",{style:{position:"absolute",top:0,left:0,right:0,zIndex:5,minHeight:48,boxSizing:"border-box",padding:"6px 16px",background:"linear-gradient(180deg, #0a1422ee 0%, #0a142299 100%)",backdropFilter:"blur(8px)",borderBottom:"1px solid var(--stroke)",display:"flex",alignItems:"center",gap:10,flexWrap:"wrap",rowGap:6},ref:__dzGbarRef,"data-dz-gbar":"1",children:[r.jsx(X,{name:"dz-nav-studio"'),
    ('c&&r.jsxs("div",{style:{position:"absolute",top:56,left:16,right:16,zIndex:5,padding:"8px 12px",',
     'c&&r.jsxs("div",{style:{position:"absolute",top:"calc(var(--dz-gbar-h, 48px) + 8px)",left:16,right:16,zIndex:5,padding:"8px 12px",'),
    ('function Fh({graph:e,onRename:t,onUpdateNode:U}){',
     REF + 'function Fh({graph:e,onRename:t,onUpdateNode:U}){'),
]


def lire(p):
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig" if bom else "utf-8"), bom


def ecrire(p, text, bom):
    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    p.write_bytes(out)


def sonder(s):
    for tag, jeton, n in SONDE_AMONT:
        c = s.count(jeton)
        if c != n:
            raise SystemExit(f"[sonde-amont] {tag} : x{c} (attendu {n}) - maillon amont absent ou rejoue. Aborting.")


def crlf_homogene(s):
    return s.count("\n") == s.count("\r\n")


def appliquer(s):
    for k, (a, b) in enumerate(PAIRES):
        c = s.count(a)
        if c != 1:
            raise SystemExit(f"[{TAG}] paire {k} : ancre x{c} (attendu 1) : {a[:80]!r}. Aborting.")
        s = s.replace(a, b, 1)
    return s


def main():
    args = sys.argv[1:]
    src = BAK if BAK.exists() else BUNDLE
    s, bom = lire(src)
    if s.count(MARKER):
        raise SystemExit(f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans {src.name} : double application refusee.")
    sonder(s)
    if not crlf_homogene(s):
        raise SystemExit(f"[{TAG}] fins de ligne heterogenes dans le bundle d'entree. Aborting.")
    if "--check" in args:
        appliquer(s)
        print(f"[{TAG}] --check OK : {len(PAIRES)} paires uniques.")
        return
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
    s2 = appliquer(s)
    if s2.count(MARKER) != 1:
        raise SystemExit(f"[{TAG}] marqueur x{s2.count(MARKER)} apres application (attendu 1).")
    sonder(s2)
    if not crlf_homogene(s2):
        raise SystemExit(f"[{TAG}] fins de ligne heterogenes apres application. Aborting.")
    ecrire(BUNDLE, s2, bom)
    BAK.unlink()
    print(f"[{TAG}] applique : {len(PAIRES)} paires, {len(s2) - len(s):+d} car ; {BAK.name} supprime.")


if __name__ == "__main__":
    main()
