# -*- coding: utf-8 -*-
# scripts/patch_bundle_plenvoi.py
"""Patcher assert-gardé : « Envoyer vers » le Photolab, le Vectorlab et le Tile Lab, et depuis le Photolab (t139, plan
docs/superpowers/plans/2026-10-08-photolab-p4-bibliotheque.md, B2).

BASELINE : bundle versionné de main après t138 (85b93a00, fusion #265). Maillon de QUEUE, comme `photolab` : il
s'applique sur le bundle courant, garde un .js.bak_plenvoi le temps de l'écriture puis le SUPPRIME (un .bak_* laissé
serait pris pour un maillon par repatch_all et ferait refuser `patch_bundle_version.py` par sa garde). `version` reste
le DERNIER maillon (il ne touche que les libellés « v2.8.0 »).

Ce que le patch pose (ancres uniques, mesurées le 08/10/2026) :
  * E1 dans `__dzSendTo`, branche IMAGE, après « Sprite Lab — source » : trois cibles qui posent l'envoi
    (`__dzEnvoi`, contrat frontend/shared/dz-envoi.js) puis naviguent — Photolab (vue `photolab` ; absente quand le
    menu est ouvert DEPUIS le Photolab : `m.de==="photolab"`), Vectorlab (vue `vectorlab` : nouveau document avec
    l'image), Tile Lab (vue `assets3d`, sous-onglet `tiles` : l'image devient la source). Les autres cibles (Studio,
    Quick, Montage, Cardforge, Sprite Lab…) sont celles de libsend, inchangées.
  * E2 avant `function __dzToSpriteLab(` (même portée que `__dzSendTo`) : `__dzEnvoi(cible, nom)` et
    `window.__dzEnvoyerVers(nom, de)` — un lab en iframe (même origine) ouvre le MÊME menu pour l'image qu'il vient
    d'enregistrer dans la Bibliothèque. Ajoute une occurrence du jeton `__dzSendTo` (2 -> 3 : pins de
    test_library_sendto et test_quick_bundle réalignés).

Lecture et écriture en OCTETS (le mode texte aplatit les CRLF — mémoire du 07/09/2026).

Run : python scripts/patch_bundle_plenvoi.py [--check] [--force-unchained]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_plenvoi")
TAG = "plenvoi"

MARKER = "function __dzEnvoi("
MARKER_ATTENDU = 1

ANCRE_CIBLES = ('items.push({lbl:"🎮 Sprite Lab — source",fn:function(){onClose&&onClose();'
                '__dzToSpriteLab({kind:"image",filename:nom})}});')
CIBLES = ('if(m.de!=="photolab")items.push({lbl:"📷 Photolab — retoucher l\'image",fn:function(){onClose&&onClose();'
          '__dzEnvoi("photolab",nom);__dzSendNav("photolab")}});'
          'items.push({lbl:"✒ Vectorlab — nouveau document avec l\'image",fn:function(){onClose&&onClose();'
          '__dzEnvoi("vectorlab",nom);__dzSendNav("vectorlab")}});'
          'items.push({lbl:"🧱 Tile Lab — source de la tuile",fn:function(){onClose&&onClose();'
          '__dzEnvoi("tilelab",nom);__dzSendNav("assets3d",{subtab:"tiles"})}});')
ANCRE_AIDES = "function __dzToSpriteLab(src){"
AIDES = ('function __dzEnvoi(c,n){window.__dzEnvoiImg={cible:c,image:n,t:Date.now()}}'
         'window.__dzEnvoyerVers=function(nom,de){__dzSendTo({kind:"image",name:nom,de:de||""},null)};')

PATCHES = [
    ("E1-cibles", ANCRE_CIBLES, ANCRE_CIBLES + CIBLES, 1),
    ("E2-aides", ANCRE_AIDES, AIDES + ANCRE_AIDES, 1),
]

SPEC_CHAR_DELTA = 625           # mesurés le 08/10/2026 (emoji et tirets hors ASCII : caractères != octets)
SPEC_BYTE_DELTA = 639

# les voisins des ancres et les maillons de queue
SONDE_AMONT = [
    ("libsend", "function __dzSendTo(", 1),
    ("libsend-jeton", "__dzSendTo", 2),
    ("photolab", '{id:"photolab",', 1),
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
