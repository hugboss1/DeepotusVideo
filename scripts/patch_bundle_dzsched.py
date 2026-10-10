# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzsched.py
"""Maillon de queue : le Planificateur ne déborde plus (10/10/2026).

Mesure à 1 600 × 1 000 : la zone principale de la coque (<main>, rail de 232 px déduit = 1 368 px disponibles)
s'étendait à 1 645 px et poussait l'en-tête et le panneau de droite hors de l'écran. Cause : la grille de l'écran
`gridTemplateColumns:"1fr 420px"` — une piste `1fr` ne descend jamais sous la largeur min-content de son contenu,
ici la barre d'outils `Dm` (titre, Semaine/Mois, dates, Générer un plan, Nouveau post, Comptes, Valider la semaine,
Créneaux, Analytics, Campagne) qui ne passait jamais à la ligne : 1 225 px.

Ce qu'il pose :
  - la piste de gauche en `minmax(0,1fr)` (elle peut être plus étroite que son contenu), marqueur
    `"data-dz-debord":"1"` sur la grille ;
  - `minWidth:0` sur la colonne de gauche (élément flex en colonne) ;
  - la barre d'outils `Dm` passe à la ligne (`flexWrap:"wrap"`, `rowGap:8`) au lieu d'imposer sa largeur.

Maillon de QUEUE, APRÈS dzglyph (dont il sonde le marqueur) ; comme dzglyph, il garde un .js.bak_dzsched le temps
de l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Lecture et écriture en OCTETS.

Run : python scripts/patch_bundle_dzsched.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzsched")
TAG = "dzsched"
MARKER = '"data-dz-debord":"1"'

SONDE_AMONT = [
    ("dzglyph", "function __dzGlyphe(", 1),
    ("i18nl2", 'dzT("studio.palette.titre")', 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

PAIRES = [
    ('style:{display:"grid",gridTemplateColumns:"1fr 420px",height:"100%",minHeight:0,background:"var(--bg-base)"}',
     '"data-dz-debord":"1",style:{display:"grid",gridTemplateColumns:"minmax(0,1fr) 420px",height:"100%",minHeight:0,background:"var(--bg-base)"}'),
    ('children:[r.jsxs("div",{style:{display:"flex",flexDirection:"column",minHeight:0},children:[r.jsx(Dm,',
     'children:[r.jsxs("div",{style:{display:"flex",flexDirection:"column",minHeight:0,minWidth:0},children:[r.jsx(Dm,'),
    ('function Dm({view:e,setView:t,count:n,range:o,onPrev:i,onNext:s,onToday:a,onNew:l,onPlan:d}){return r.jsxs("div",{style:{padding:"12px 18px",borderBottom:"1px solid var(--stroke)",background:"var(--bg-panel)",display:"flex",alignItems:"center",gap:12}',
     'function Dm({view:e,setView:t,count:n,range:o,onPrev:i,onNext:s,onToday:a,onNew:l,onPlan:d}){return r.jsxs("div",{style:{padding:"12px 18px",borderBottom:"1px solid var(--stroke)",background:"var(--bg-panel)",display:"flex",alignItems:"center",gap:12,flexWrap:"wrap",rowGap:8}'),
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
