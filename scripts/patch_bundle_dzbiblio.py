# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzbiblio.py
"""Maillon de queue : la Bibliothèque tient dans la fenêtre (10/10/2026).

Mesure (puppeteer, 1 440 × 900) : `<main>` faisait 1 389 px à partir de x=232, soit ~180 px au-delà du bord droit. La
coque est une grille `auto 1fr` ; sa piste `1fr` (= minmax(auto, 1fr)) ne descend pas sous le min-content de `<main>`,
et ce min-content était celui de la barre d'outils de la Bibliothèque (titre, onglets Images/Rendus/3D/Sprites/Audio/
Favoris/Établi, espaceur, « Rechercher des assets… », tri « Plus récents », « Importer une vidéo/un son/une image ») :
une rangée flex SANS retour à la ligne de 1 353 px. Tout ce qui partage `<main>` débordait avec elle : les pastilles
fal/heygen/voix/version de l'en-tête et, puce Audio, la ligne de filtres du tiroir Sons (« Récents », « Tous »).

Ce qu'il pose : la barre passe à la ligne (`flexWrap:"wrap"`, `rowGap:8`), marqueur `"data-dz-biblio-barre":"1"`.
Son min-content tombe à celui de son plus large enfant (le champ de recherche, 240 px) : `<main>` reprend la largeur
de la piste (1 208 px à 1 440, 1 134 à 1 366). La grille de la coque, partagée par tous les écrans, n'est pas touchée.

Maillon de QUEUE, APRÈS avatar (t168) et dzgbar (dont il sonde les marqueurs) ; comme lui, il garde un .js.bak_dzbiblio le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Lecture et écriture en OCTETS. Son inverse vit
dans backend/tests/_i18n_l1_aide.py (`avant_dzbiblio`, appelé en tête de `avant_avatar`).

Run : python scripts/patch_bundle_dzbiblio.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzbiblio")
TAG = "dzbiblio"
MARKER = '"data-dz-biblio-barre":"1"'

SONDE_AMONT = [
    ("avatar", '{id:"avatarlive",', 1),
    ("dzgbar", '"data-dz-gbar":"1"', 1),
    ("dzsched", '"data-dz-debord":"1"', 1),
    ("dzglyph", "function __dzGlyphe(", 1),
    ("i18nl2", 'dzT("biblio.vue.rechercher")', 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

PAIRES = [
    ('r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:12},children:[r.jsx("div",{className:"display",style:{fontSize:16,color:"var(--ink-strong)"},children:dzT("commun.objet.bibliotheque")})',
     'r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:12,flexWrap:"wrap",rowGap:8},"data-dz-biblio-barre":"1",children:[r.jsx("div",{className:"display",style:{fontSize:16,color:"var(--ink-strong)"},children:dzT("commun.objet.bibliotheque")})'),
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
