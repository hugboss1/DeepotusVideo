# -*- coding: utf-8 -*-
# scripts/patch_bundle_srclbl.py
"""Patcher assert-gardé : libellés de provenance servis par le BACKEND (02/10/2026).

BASELINE : bundle POST-patch dzcout (queue de chaîne au 02/10/2026).
Backup dédié : .js.bak_srclbl (état juste avant CE patch).
Au prochain bump de version : archiver .bak_version HORS de
frontend/dist/assets puis relancer patch_bundle_version.py seul — `version`
reste le DERNIER maillon (procédure de patch_bundle_version.py).

Défaut corrigé : les chips de provenance (écran Library, onglet Images, et
sélecteur __dzLibPicker) lisaient la table JS figée `__dzSrcLbl` posée par
libprov ; le catalogue réel `library_index.SOURCES` a gagné « mobile »
(tâche #58) et la chip affichait le slug brut « mobile (1) ».
GET /api/images sert désormais `sources` (slug → libellé) ; deux greffes
ADDITIVES le versent dans `__dzSrcLbl` dès que la liste arrive :
  L1  vm (écran Library), dans le chargement async, avant la construction
      des items : `ne&&ne.sources&&Object.assign(__dzSrcLbl,ne.sources);`
  L2  __dzLibPicker, au retour du fetch : même versement, gardé par
      `typeof` comme le reste du corps du picker.
La table de libprov reste le REPLI (backend sans `sources`) ; le banc
test_library_provenance épingle sa parité avec SOURCES.

Rien de libprov n'est réécrit : ses sondes et celles du picker tiennent
(__dzSrcChips ×2, dzlp-chips ×4, __dzLibPicker ×10).

Run : python scripts/patch_bundle_srclbl.py [--check] [--force-unchained]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_srclbl")
TAG = "srclbl"

MARKER = "Object.assign(__dzSrcLbl,"
MARKER_ATTENDU = 2

# (tag, ancre, remplacement, occurrences attendues)
PATCHES = [
    ("L1-vm",
     "if(!C)return;const W=((ne==null?void 0:ne.images)||[])",
     "if(!C)return;ne&&ne.sources&&Object.assign(__dzSrcLbl,ne.sources);"
     "const W=((ne==null?void 0:ne.images)||[])", 1),
    ("L2-picker",
     'fetch("/api/images").then(function(r){return r.json()})'
     ".then(function(d){tout=",
     'fetch("/api/images").then(function(r){return r.json()})'
     '.then(function(d){d&&d.sources&&typeof __dzSrcLbl!=="undefined"'
     "&&Object.assign(__dzSrcLbl,d.sources);tout=", 1),
]

SPEC_CHAR_DELTA = 136
SPEC_BYTE_DELTA = 136

SONDE_AMONT = [
    ("libprov", "__dzSrcChips", 2),
    ("libprov-table", "var __dzSrcLbl={", 1),
    ("libprov-picker", "dzlp-chips", 4),
    ("libpicker", "__dzLibPicker", 10),
    ("dzcout", "__dzCoutBlanc", 7),
]


def lire(p):
    """Le mode texte MENT sur les fins de ligne (mémoire du 07/09/2026) :
    on lit et on écrit en OCTETS."""
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
    db = sum(len(rp.encode("utf-8")) - len(a.encode("utf-8"))
             for _t, a, rp, _n in PATCHES)
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
                f"[garde-chaine] backup aval detecte : {other.name} (plus "
                f"recent que {bak.name}). Utilise "
                f"`python scripts/repatch_all.py --from {TAG}`.")


def sonder(s):
    for tag, jeton, n in SONDE_AMONT:
        c = s.count(jeton)
        if c != n:
            raise SystemExit(f"[sonde-amont] {tag} : x{c} (attendu {n}) "
                             "- maillon amont absent ou rejoue. Aborting.")


def main():
    args = sys.argv[1:]
    dc, db = deltas()
    if (dc, db) != (SPEC_CHAR_DELTA, SPEC_BYTE_DELTA):
        raise SystemExit(f"[{TAG}] parite spec rompue : {dc} car / {db} o, "
                         f"spec {SPEC_CHAR_DELTA} / {SPEC_BYTE_DELTA}.")
    if "--force-unchained" not in args:
        guard_downstream(BAK)
    src = BAK if BAK.exists() else BUNDLE
    s, bom = lire(src)

    if "--check" in args:
        if s.count(MARKER):
            raise SystemExit(f"[{TAG}] marqueur deja present x{s.count(MARKER)}"
                             f" dans {src.name} : double application refusee.")
        sonder(s)
        for tag, a, _, n in PATCHES:
            c = s.count(a)
            if c != n:
                raise SystemExit(f"[{tag}] anchor count={c} (want {n}) "
                                 f"dans {src.name}.")
        print(f"[{TAG}] applicable sur {src.name} ({len(PATCHES)} ancres OK, "
              f"{len(SONDE_AMONT)} sondes ; delta +{dc} car / +{db} o)")
        return

    if not BAK.exists():
        if MARKER in s:
            raise SystemExit(f"[{TAG}] marqueur present sans {BAK.name} : "
                             "etat ambigu, abandon sans rien ecrire.")
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK.name)
    else:
        shutil.copy2(BAK, BUNDLE)
        s, bom = lire(BUNDLE)
        print("restore <-", BAK.name)
    avant = BUNDLE.read_bytes()
    sonder(s)
    if MARKER in s:
        raise SystemExit(f"[{TAG}] backup empoisonne (marqueur present). "
                         "Aborting.")
    for tag, a, rp, n in PATCHES:
        s = apply(s, a, rp, tag, n)
    ecrire(BUNDLE, s, bom)

    apres = BUNDLE.read_bytes()
    problemes = []
    if len(apres) != len(avant) + db:
        problemes.append(f"taille {len(apres)} o, attendu {len(avant) + db}")
    if apres.count(b"\r\n") != avant.count(b"\r\n") or \
            apres.count(b"\n") != apres.count(b"\r\n"):
        problemes.append("fins de ligne changees")
    if s.count(MARKER) != MARKER_ATTENDU:
        problemes.append(f"marqueur x{s.count(MARKER)} "
                         f"(want {MARKER_ATTENDU})")
    if problemes:
        shutil.copy2(BAK, BUNDLE)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problemes))
    print(f"OK - {TAG} applique ({len(avant)} -> {len(apres)} o, +{db}).")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
