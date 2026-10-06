# -*- coding: utf-8 -*-
# scripts/patch_bundle_libsons.py
"""Patcher assert-gardé : la puce Audio de la Bibliothèque monte le tiroir Sons (T101, plan-son-vfx T5, 06/10/2026).

BASELINE : bundle versionné de main après T100 (31969216) — la queue réelle de la chaîne : la plupart des maillons
récents (srclbl, dzcout, libprov…) n'ont pas de .bak sur cette machine, le bundle commis fait foi.
Backup dédié : .js.bak_libsons (état juste avant CE patch), créé au premier passage.
Au prochain bump de version : archiver .bak_version HORS de frontend/dist/assets puis relancer
patch_bundle_version.py seul — `version` reste le DERNIER maillon (procédure de patch_bundle_version.py).

UNE ancre (mesurée unique le 06/10 : l'ouverture du bloc de l'onglet Audio, zone d'import + banques gratuites),
UNE insertion ADDITIVE en premier enfant de sa grille : le tiroir (window.DzSfx.Drawer, `inline`) dans un hôte `.dzsvm.dz-libsons`.
Feature-detect sur window.DzSfx.ready : couche absente → rien à l'écran, rien ne casse. Le reste de l'onglet
(import, banques, grille de la Bibliothèque) ne bouge pas.

Run : python scripts/patch_bundle_libsons.py [--check] [--force-unchained]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_libsons")
TAG = "libsons"

MARKER = "dz-libsons"
MARKER_ATTENDU = 1

ANCRE = 'o==="Audio"&&r.jsxs("div",{style:{marginBottom:14,display:"grid",gap:10},children:['
# l'insertion se fait DANS la grille de l'onglet (premier enfant) : la chaîne « DzMetaChips + ouverture du bloc
# Audio » est figée par le maillon montage (P9lib6, test_montage_bundle) et ne doit pas être coupée
INSERT = ('window.DzSfx&&window.DzSfx.ready&&r.jsx("div",{className:"dzsvm dz-libsons",'
          'children:r.jsx(window.DzSfx.Drawer,{open:!0,inline:!0,defaultTab:"tous"})}),')

# (tag, ancre, remplacement, occurrences attendues)
PATCHES = [
    ("A1-onglet-audio", ANCRE, ANCRE + INSERT, 1),
]

SPEC_CHAR_DELTA = 152
SPEC_BYTE_DELTA = 152

# les maillons voisins de l'ancre, et la couche que l'insertion appelle
SONDE_AMONT = [
    ("libprov", "__dzSrcChips", 2),
    ("metachips", "DzMetaChips", 2),
    ("projets", "DzProjetsBar", 2),
    ("srclbl", "Object.assign(__dzSrcLbl,", 2),
    ("sfxstudio", "window.DzSfx={ready:!0,Drawer:SvxDrawer", 1),
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


def deltas():
    dc = sum(len(rp) - len(a) for _t, a, rp, _n in PATCHES)
    db = sum(len(rp.encode("utf-8")) - len(a.encode("utf-8")) for _t, a, rp, _n in PATCHES)
    return dc, db


def apply(s, anchor, replacement, tag, n=1):
    c = s.count(anchor)
    if c != n:
        raise SystemExit(f"[{tag}] anchor count={c} (want {n}). Aborting.")
    return s.replace(anchor, replacement)


def guard_downstream(bak):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in sorted(bak.parent.glob(stem + ".bak_*")):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name} (plus recent que {bak.name}). "
                f"Utilise `python scripts/repatch_all.py --from {TAG}`.")


def sonder(s):
    for tag, jeton, n in SONDE_AMONT:
        c = s.count(jeton)
        if c != n:
            raise SystemExit(f"[sonde-amont] {tag} : x{c} (attendu {n}) - maillon amont absent ou rejoue. Aborting.")


def main():
    args = sys.argv[1:]
    dc, db = deltas()
    if (dc, db) != (SPEC_CHAR_DELTA, SPEC_BYTE_DELTA):
        raise SystemExit(f"[{TAG}] parite spec rompue : {dc} car / {db} o, spec {SPEC_CHAR_DELTA} / {SPEC_BYTE_DELTA}.")
    if "--force-unchained" not in args:
        guard_downstream(BAK)
    src = BAK if BAK.exists() else BUNDLE
    s, bom = lire(src)

    if "--check" in args:
        if s.count(MARKER):
            raise SystemExit(f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans {src.name} : double application refusee.")
        sonder(s)
        for tag, a, _, n in PATCHES:
            c = s.count(a)
            if c != n:
                raise SystemExit(f"[{tag}] anchor count={c} (want {n}) dans {src.name}.")
        print(f"[{TAG}] applicable sur {src.name} ({len(PATCHES)} ancre OK, {len(SONDE_AMONT)} sondes ; "
              f"delta +{dc} car / +{db} o)")
        return

    if not BAK.exists():
        if MARKER in s:
            raise SystemExit(f"[{TAG}] marqueur present sans {BAK.name} : etat ambigu, abandon sans rien ecrire.")
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK.name)
    else:
        shutil.copy2(BAK, BUNDLE)
        s, bom = lire(BUNDLE)
        print("restore <-", BAK.name)
    avant = BUNDLE.read_bytes()
    sonder(s)
    if MARKER in s:
        raise SystemExit(f"[{TAG}] backup empoisonne (marqueur present). Aborting.")
    for tag, a, rp, n in PATCHES:
        s = apply(s, a, rp, tag, n)
    ecrire(BUNDLE, s, bom)

    apres = BUNDLE.read_bytes()
    problemes = []
    if len(apres) != len(avant) + db:
        problemes.append(f"taille {len(apres)} o, attendu {len(avant) + db}")
    if apres.count(b"\r\n") != avant.count(b"\r\n") or apres.count(b"\n") != apres.count(b"\r\n"):
        problemes.append("fins de ligne changees")
    if s.count(MARKER) != MARKER_ATTENDU:
        problemes.append(f"marqueur x{s.count(MARKER)} (want {MARKER_ATTENDU})")
    if problemes:
        shutil.copy2(BAK, BUNDLE)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  " + "\n  ".join(problemes))
    print(f"OK - {TAG} applique ({len(avant)} -> {len(apres)} o, +{db}).")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
