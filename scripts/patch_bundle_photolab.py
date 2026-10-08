# -*- coding: utf-8 -*-
# scripts/patch_bundle_photolab.py
"""Patcher assert-gardé : l'entrée « Photolab » de la barre des applications (t137, plan
docs/superpowers/plans/2026-10-07-photolab-p2-ecran.md, Task D1 ; spec 2026-10-07-photolab-design.md).

BASELINE : bundle versionné de main après t134/t136 (73c9cfe2, fusion #263 ; dernier commit du bundle : 368f29ea) — la
plupart des maillons n'ont pas de .bak sur cette machine, le bundle commis fait foi. Maillon de QUEUE : il s'applique
sur le bundle courant. Backup dédié .js.bak_photolab au premier passage, SUPPRIMÉ après application réussie (aucun
.bak_* en trop : guard_downstream et repatch_all prennent tout .bak_* pour un maillon de la chaîne — un .bak_photolab
laissé ferait refuser `patch_bundle_version.py` par sa garde au prochain bump). Au prochain bump de version : archiver
.bak_version HORS de frontend/dist/assets puis relancer patch_bundle_version.py seul — `version` reste le DERNIER
maillon (il ne touche que les libellés « v2.8.0 », qu'aucune section d'ici ne déplace).

Ce que le patch pose (ancres uniques, mesurées le 07/10/2026) :
  * P1 l'icône `photolab` de la carte `Sh` (avant `gamegrid`) : un objectif photo, DESIGN.md §15-2 — grille 24,
    masses pleines `currentColor`, sujet à 1 : l'anneau (découpe evenodd) et un diaphragme à six lames séparées par
    un jour de .9 ; support à .32 : l'ouverture hexagonale. Lames calculées (disque r 6,9 ∩ demi-plans des côtés
    prolongés d'un hexagone r 2,7), arrondies au centième.
  * P2 l'entrée de rail `{id:"photolab",…}` juste APRÈS l'entrée Vectorlab (donc avant Settings).
  * P3 la vue : une iframe `/photolab/` (montage statique du backend, comme `/vectorlab/`), clé `pplab`.
  * P4 `photolab` entre dans la liste blanche des vues de `deepotus:navigate` (`Yu`) : `?view=photolab` et
    l'événement relais ouvrent l'écran comme les autres vues.

Lecture et écriture en OCTETS (le mode texte aplatit les CRLF — mémoire du 07/09/2026).

Run : python scripts/patch_bundle_photolab.py [--check] [--force-unchained]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_photolab")
TAG = "photolab"

MARKER = '{id:"photolab",'
MARKER_ATTENDU = 1

ANNEAU = "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20zM12 3.8a8.2 8.2 0 1 1 0 16.4a8.2 8.2 0 1 1 0-16.4z"
LAMES = ("M7.2 16.95A6.9 6.9 0 0 1 5.14 11.26L11.1 14.7z"
         "M5.31 10.32A6.9 6.9 0 0 1 9.21 5.69L9.21 12.57z"
         "M10.11 5.36A6.9 6.9 0 0 1 16.07 6.43L10.11 9.87z"
         "M18.86 12.74L12.9 9.3L16.8 7.05A6.9 6.9 0 0 1 18.86 12.74z"
         "M18.69 13.68A6.9 6.9 0 0 1 14.79 18.31L14.79 11.43z"
         "M13.89 18.64A6.9 6.9 0 0 1 7.93 17.57L13.89 14.13z")
OUVERTURE = "M14.34 13.35L12 14.7L9.66 13.35L9.66 10.65L12 9.3L14.34 10.65z"
ICONE = ('photolab:r.jsxs("g",{fill:"currentColor",children:['
         'r.jsx("path",{fillRule:"evenodd",d:"' + ANNEAU + '"}),'
         'r.jsx("path",{d:"' + LAMES + '"}),'
         'r.jsx("path",{d:"' + OUVERTURE + '",opacity:".32"})]}),')

ANCRE_ICONE = 'gamegrid:r.jsxs("g",{fill:"currentColor",children:['
ANCRE_RAIL = '{id:"vectorlab",label:"Vectorlab",icon:"vectorpen",desc:"Éditeur vectoriel & vitrail",new:!0},'
ENTREE = '{id:"photolab",label:"Photolab",icon:"photolab",desc:"Retouche d\'image & calques",new:!0},'
ANCRE_VUE = ('s==="vectorlab"&&r.jsx("iframe",{src:"/vectorlab/",title:"Vectorlab",style:{position:"absolute",inset:0,'
             'width:"100%",height:"100%",border:"0",background:"var(--bg-base)"}},"pvlab"),')
VUE = ('s==="photolab"&&r.jsx("iframe",{src:"/photolab/",title:"Photolab",style:{position:"absolute",inset:0,'
       'width:"100%",height:"100%",border:"0",background:"var(--bg-base)"}},"pplab"),')
# `,sg=Yu.includes(` rend l'ancre unique : `"settings","vectorlab"]` seul pourrait reparaître ailleurs
ANCRE_VUES = '"settings","vectorlab"],sg=Yu.includes('

PATCHES = [
    ("P1-icone", ANCRE_ICONE, ICONE + ANCRE_ICONE, 1),
    ("P2-rail", ANCRE_RAIL, ANCRE_RAIL + ENTREE, 1),
    ("P3-vue", ANCRE_VUE, ANCRE_VUE + VUE, 1),
    ("P4-vue-navigable", ANCRE_VUES, ANCRE_VUES.replace('"vectorlab"]', '"vectorlab","photolab"]'), 1),
]

SPEC_CHAR_DELTA = 881          # mesurés le 07/10/2026 (aucun caractère hors ASCII dans les sections)
SPEC_BYTE_DELTA = 881

# les voisins des ancres et les maillons de queue
SONDE_AMONT = [
    ("vectorlab", 'src:"/vectorlab/"', 1),
    ("vectorpen", 'vectorpen:r.jsxs("g",{fill:"currentColor",children:[', 1),
    ("assets2d", "function DzAssets2D(", 1),
    ("keepsaisie", "function __dzK(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
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
            raise SystemExit(f"[garde-chaine] backup aval detecte : {other.name} (plus recent que {bak.name}). "
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
            raise SystemExit(f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans {src.name} : double application "
                             "refusee.")
        sonder(s)
        for tag, a, _r, n in PATCHES:
            if s.count(a) != n:
                raise SystemExit(f"[{TAG}] --check : ancre {tag} x{s.count(a)} (attendu {n}).")
        print(f"[{TAG}] --check OK : {len(PATCHES)} ancres, delta {dc} car / {db} o.")
        return

    if s.count(MARKER):
        raise SystemExit(f"[{TAG}] marqueur deja present dans {src.name} : double application refusee.")
    sonder(s)
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    avant_c, avant_o = len(s), len(s.encode("utf-8"))
    for tag, a, r_, n in PATCHES:
        s = apply(s, a, r_, tag, n)
    if s.count(MARKER) != MARKER_ATTENDU:
        raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)} apres application (attendu {MARKER_ATTENDU}).")
    if (len(s) - avant_c, len(s.encode("utf-8")) - avant_o) != (dc, db):
        raise SystemExit(f"[{TAG}] delta mesure != delta spec.")
    ecrire(BUNDLE, s, bom)
    # maillon de queue : le .bak ne sert qu'à l'échec en cours de route ; laissé, il deviendrait un faux maillon de
    # la chaîne (repatch_all) et ferait refuser le maillon `version` par sa garde (« backup aval détecté »)
    BAK.unlink()
    print(f"[{TAG}] applique : {len(PATCHES)} sections, +{dc} car / +{db} o ; {BAK.name} supprime.")


if __name__ == "__main__":
    main()
