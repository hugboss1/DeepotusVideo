# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzglyph.py
"""Maillon de queue : icônes « Deepotus Glyph » dans la coque React (lot G1, docs/icones/PLAN-IMPLEMENTATION.md).

Ce qu'il pose (hors couches rafraîchissables) :
  - le socle : `__dzGlyphe(clé)` (la carte d'icônes `Sh` apprend toute clé `dz-…` de la suite, lue dans
    window.DZ_ICONS — /shared/icons/dz-icons.js, chargé par frontend/dist/index.html avant le bundle), `__dzGl`
    (une icône en élément React), `__dzGlT` (un texte traduit qui portait un glyphe : le glyphe devient l'icône),
    `__dzGlH` (le balisage HTML d'une icône pour le code qui écrit du HTML) ;
  - chaque site d'appel repointé vers sa clé finale (`X`, bouton `K` icon/iconRight, bouton-icône `se`, données des
    rails, catégories de nœuds, canaux, palette ⌘K…), les glyphes et emojis des écrans remplacés.

La TABLE est scripts/dzglyph_paires.json, produite par scripts/icones/g1_generer.py (saisie
scripts/icones/g1_saisie*.{py,json}, positions dans le bundle de la BASE G0). Les éditions DANS les couches
(montage, sonvfx, sfxstudio, vfxrack) ne passent pas par ici : le même générateur réécrit frontend/patches/*.js,
réinjectés par refresh_layer.py --layer <x> AVANT ce maillon.

Maillon de QUEUE, APRÈS i18n_l2 (dont il sonde le marqueur) : il s'applique sur le bundle courant, garde un
.js.bak_dzglyph le temps de l'écriture puis le SUPPRIME (un .bak_* laissé serait pris pour un maillon par
repatch_all et ferait refuser patch_bundle_version.py par sa garde). `version` reste le DERNIER maillon (il ne
touche que « v2.8.0 », sondé ici).

Lecture et écriture en OCTETS (le mode texte aplatit les CRLF — mémoire du 07/09/2026).

Run : python scripts/patch_bundle_dzglyph.py [--check] [--force-unchained]
"""
import json
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzglyph")
TABLE = pathlib.Path("scripts/dzglyph_paires.json")
TAG = "dzglyph"
MARKER = "function __dzGlyphe("

# les maillons voisins et les compteurs figés des maillons aval (ce maillon n'ajoute ni état ni DzTracks)
SONDE_AMONT = [
    ("i18nl2", 'dzT("studio.palette.titre")', 1),
    ("i18nl1", 'dzT("reglages.cadre.titre")', 1),
    ("plenvoi", "function __dzEnvoi(", 1),
    ("dzdesign", "__dzCatBar", 2),
    ("dznodecat", "__dzNodeCat", 2),
    ("dzrailmotion", "__dzNavMotion", 2),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]


def lire(p):
    """Le mode texte MENT sur les fins de ligne (mémoire du 07/09/2026) : on lit et on écrit en OCTETS."""
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig" if bom else "utf-8"), bom


def ecrire(p, text, bom):
    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    p.write_bytes(out)


def paires():
    return json.loads(TABLE.read_bytes().decode("utf-8"))["paires"]


def guard_downstream(bak):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in sorted(bak.parent.glob(stem + ".bak_*")):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(f"[garde-chaine] backup aval detecte : {other.name} (plus recent que {bak.name}).")


def sonder(s):
    for tag, jeton, n in SONDE_AMONT:
        c = s.count(jeton)
        if c != n:
            raise SystemExit(f"[sonde-amont] {tag} : x{c} (attendu {n}) - maillon amont absent ou rejoue. Aborting.")


def crlf_homogene(s):
    return s.count("\n") == s.count("\r\n")


def appliquer(s, P):
    for k, p in enumerate(P):
        c = s.count(p["ancre"])
        if c != 1:
            raise SystemExit(f"[{TAG}] paire {k} ({p['ids'][:1]}) : ancre x{c} (attendu 1) : {p['ancre'][:80]!r}. Aborting.")
        s = s.replace(p["ancre"], p["remplace"], 1)
    return s


def main():
    args = sys.argv[1:]
    P = paires()
    if "--force-unchained" not in args:
        guard_downstream(BAK)
    src = BAK if BAK.exists() else BUNDLE
    s, bom = lire(src)
    if s.count(MARKER):
        raise SystemExit(f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans {src.name} : double application refusee.")
    sonder(s)
    if not crlf_homogene(s):
        raise SystemExit(f"[{TAG}] fins de ligne heterogenes dans le bundle d'entree. Aborting.")
    if "--check" in args:
        appliquer(s, P)
        print(f"[{TAG}] --check OK : {len(P)} paires, chacune unique au moment de son application.")
        return
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    s2 = appliquer(s, P)
    if s2.count(MARKER) != 1:
        raise SystemExit(f"[{TAG}] marqueur x{s2.count(MARKER)} apres application (attendu 1).")
    sonder(s2)
    if not crlf_homogene(s2):
        raise SystemExit(f"[{TAG}] fins de ligne heterogenes apres application. Aborting.")
    ecrire(BUNDLE, s2, bom)
    BAK.unlink()
    print(f"[{TAG}] applique : {len(P)} paires, {len(s2) - len(s):+d} car ; {BAK.name} supprime.")


if __name__ == "__main__":
    main()
