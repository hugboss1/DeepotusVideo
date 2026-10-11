# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzguide.py
"""Maillon de queue : les boutons « Guide » de l'onglet Assets 2D du hub Game Assets mènent au chapitre du guide v3,
dans la langue de l'application (t181, 11/10/2026).

Avant : seul Card Forge avait un lien, en dur vers le FRANÇAIS (`/guide/fr.html#c18`), même interface en anglais ; les
trois autres boutons étaient grisés (« Pas encore »), faute de chapitre. Le guide v3 a désormais un chapitre par outil.
Les liens visent `/guide/#<chapitre>` : la page d'entrée du guide (docs/guide/index.html, t169) lit `dz_lang` puis la
langue du navigateur et ouvre fr.html ou en.html EN GARDANT l'ancre. Les ancres sont les identifiants stables du
sommaire (docs/guide/src/chapitres.json) : spritelab, tilelab, vectorlab-pixel, cardforge.

Ce qu'il pose (ancres uniques, relevées le 11/10 sur le bundle de main a7dc5d77) : quatre paires sur le tableau `C`
de DzAssets2D (maillon assets2d, t125), une par carte. Rien d'autre ne change : le rendu du bouton (`c.g ? lien :
bouton grisé`) est celui du maillon assets2d.

Maillon de QUEUE, APRÈS i18nfix (dont il sonde le marqueur) ; comme lui, il garde un .js.bak_dzguide le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzguide` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici : une seule source), appelé EN TÊTE de `avant_i18nfix`.
Lecture et écriture en OCTETS.
Run : python scripts/patch_bundle_dzguide.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzguide")
TAG = "dzguide"
MARKER = 'g:"/guide/#cardforge"}'

SONDE_AMONT = [
    ("i18nfix", 'dzT("scheduler.mode.assiste")', 1),
    ("dzbiblio", '"data-dz-biblio-barre":"1"', 1),
    ("avnoeuds", "function dzAvCompile(", 1),
    ("avatar", '{id:"avatarlive",', 1),
    ("assets2d", "function DzAssets2D(", 1),
    ("dzglyph", "function __dzGlyphe(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

PAIRES = [
    ('o:function(){go("sprites")},g:""}', 'o:function(){go("sprites")},g:"/guide/#spritelab"}'),
    ('o:function(){go("tiles")},g:""}', 'o:function(){go("tiles")},g:"/guide/#tilelab"}'),
    ('o:vl,g:""}', 'o:vl,g:"/guide/#vectorlab-pixel"}'),
    ('g:"/guide/fr.html#c18"}', MARKER),
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
