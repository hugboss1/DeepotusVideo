# -*- coding: utf-8 -*-
# scripts/patch_bundle_avatar.py
"""Maillon de queue : l'entrée « Avatar live » de la barre des applications (t168, 10/10/2026 ; spec
docs/superpowers/specs/2026-10-10-higgsfield-genjutsu-inventaire.md). L'écran est une page à part (frontend/avatar/,
montée sur /avatar comme /photolab) ; la barre l'ouvre dans une iframe, comme le Photolab et le Vectorlab.

Ce qu'il pose (ancres uniques, relevées le 10/10 sur le bundle de main e7fb1ac1 + dzglyph + dzsched) :
  - P1 l'entrée de rail `{id:"avatarlive",…}` juste APRÈS celle du Photolab : icône Deepotus Glyph `dz-media-avatar`
    (résolue par __dzGlyphe, maillon dzglyph), description par dzT("avatar.rail.desc") (dictionnaire avatar.json) ;
  - P2 la vue : une iframe `/avatar/`, clé `pavlive`, après celle du Photolab ; `allow` donne caméra et micro à la
    page (le Direct en a besoin : une iframe ne les reçoit PAS par défaut) ;
  - P3 `avatarlive` entre dans la liste blanche des vues de `deepotus:navigate` : `?view=avatarlive` ouvre l'écran.
Maillon de QUEUE, APRÈS dzsched (dont il sonde le marqueur) ; comme lui, il garde un .js.bak_avatar le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_avatar` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici : une seule source). Lecture et écriture en OCTETS.
Run : python scripts/patch_bundle_avatar.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_avatar")
TAG = "avatar"
MARKER = '{id:"avatarlive",'

SONDE_AMONT = [
    ("dzsched", '"data-dz-debord":"1"', 1),
    ("dzglyph", "function __dzGlyphe(", 1),
    ("photolab", '{id:"photolab",', 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

_RAIL_PL = '{id:"photolab",label:"Photolab",icon:"dz-nav-photolab",desc:dzT("coque.rail.photolab_desc"),new:!0},'
_VUE_PL = ('s==="photolab"&&r.jsx("iframe",{src:"/photolab/",title:"Photolab",style:{position:"absolute",inset:0,'
           'width:"100%",height:"100%",border:"0",background:"var(--bg-base)"}},"pplab"),')
_VUES = '"settings","vectorlab","photolab"],sg=Yu.includes('

PAIRES = [
    (_RAIL_PL, _RAIL_PL + '{id:"avatarlive",label:"Avatar live",icon:"dz-media-avatar",desc:dzT("avatar.rail.desc"),new:!0},'),
    (_VUE_PL, _VUE_PL + ('s==="avatarlive"&&r.jsx("iframe",{src:"/avatar/",title:"Avatar live",allow:"camera; microphone; autoplay",'
                         'style:{position:"absolute",inset:0,width:"100%",height:"100%",border:"0",background:"var(--bg-base)"}},"pavlive"),')),
    (_VUES, _VUES.replace('"photolab"]', '"photolab","avatarlive"]')),
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
