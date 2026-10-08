# -*- coding: utf-8 -*-
# scripts/patch_bundle_i18n_l1.py
"""Maillon de queue : traduction L1 (t141, plan docs/superpowers/plans/2026-10-08-traduction-l1-coque-reglages-
bibliotheque.md) — la coque, la navigation, les Réglages et la vue Bibliothèque passent par dzT(clé).

La TABLE est scripts/i18n_l1_paires.json, produite par scripts/i18n_l1_generer.py à partir de la saisie
scripts/i18n_l1/*.py (positions dans le bundle de BASE 92bec8ed, une ancre minimale unique par substitution, dans
l'ordre où elles s'appliquent). Les textes de la COUCHE frontend/patches/montage.js ne passent pas par ici : ils sont
changés dans la couche elle-même (même générateur), réinjectée par refresh_layer.py --layer montage AVANT ce maillon.

Maillon de QUEUE, comme photolab et plenvoi : il s'applique sur le bundle courant, garde un .js.bak_i18nl1 le temps
de l'écriture puis le SUPPRIME (un .bak_* laissé serait pris pour un maillon par repatch_all et ferait refuser
patch_bundle_version.py par sa garde). `version` reste le DERNIER maillon (il ne touche que « v2.8.0 », gardé ici).

Lecture et écriture en OCTETS (le mode texte aplatit les CRLF — mémoire du 07/09/2026).

Run : python scripts/patch_bundle_i18n_l1.py [--check] [--force-unchained]
"""
import json
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_i18nl1")
TABLE = pathlib.Path("scripts/i18n_l1_paires.json")
TAG = "i18nl1"
MARKER = 'dzT("reglages.cadre.titre")'

# les maillons voisins et les compteurs figés des maillons aval
SONDE_AMONT = [
    ("plenvoi", "function __dzEnvoi(", 1),
    ("photolab", '{id:"photolab",', 1),
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
    t = json.loads(TABLE.read_bytes().decode("utf-8"))
    return t["paires"]


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


def appliquer(s, P):
    for k, p in enumerate(P):
        c = s.count(p["ancre"])
        if c != 1:
            raise SystemExit(f"[{TAG}] paire {k} ({p['groupe']}) : ancre x{c} (attendu 1) : {p['ancre'][:80]!r}. Aborting.")
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
    sonder(s2)                                     # dzT est une fonction globale : aucun hook, aucun compteur ne bouge
    ecrire(BUNDLE, s2, bom)
    BAK.unlink()
    print(f"[{TAG}] applique : {len(P)} paires, {len(s2) - len(s):+d} car ; {BAK.name} supprime.")


if __name__ == "__main__":
    main()
