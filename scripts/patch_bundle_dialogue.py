# -*- coding: utf-8 -*-
# scripts/patch_bundle_dialogue.py
"""Patcher assert-gardé : dialogues maison dans le bundle (finitions UI, 20/09/2026).

BASELINE : bundle POST-patch version 2.8.0 (queue de chaîne au 20/09/2026).
Backup dédié : .js.bak_dialogue (état juste avant CE patch).
Au prochain bump de version : archiver .bak_version HORS de
frontend/dist/assets puis relancer patch_bundle_version.py seul — `version`
reste le DERNIER maillon (procédure de patch_bundle_version.py).

Le « 127.0.0.1:8765 indique » des captures de l'utilisateur est le titre du
dialogue NATIF du navigateur. Le bundle porte 11 sites `confirm(` et 33
`alert(` :
  G1  injection de la couche `frontend/patches/dialogue.js` après le bloc
      Transfert (fin de module) : `window.__dzDialogue` + `window.alert`
      remplacé (les 33 alert passent par là sans réécriture) ;
  G2..G12  les 11 sites `confirm(` réécrits en
      `await window.__dzDialogue.confirmer(` ; les fonctions qui ne l'étaient
      pas deviennent async (le `onClick:f=>{…}` du job, la `function(){}` du
      rendu 3D, le `.then(function(x){…})` de l'impression 3D).

Sonde de maillon amont : `__DZ_TRANSFERT_END__` doit être présent UNE fois
(c'est l'ancre d'injection). La couche ne cite aucune ancre : le banc
`backend/tests/test_dialogue_bundle.py` le vérifie.

Run : python scripts/patch_bundle_dialogue.py [--check] [--force-unchained]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
COUCHE = pathlib.Path("frontend/patches/dialogue.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dialogue")
TAG = "dialogue"

BEGIN = "/*__DZ_DIALOGUE_BEGIN__*/"
END = "/*__DZ_DIALOGUE_END__*/"
ANCHOR_INJECT = "/*__DZ_TRANSFERT_END__*/"

D = "await window.__dzDialogue.confirmer("

# (tag, ancre, remplacement, occurrences attendues)
PATCHES = [
    ("G2-son",
     'onClick:async()=>{confirm("Delete ce son ?")&&',
     'onClick:async()=>{' + D + '"Delete ce son ?")&&', 1),
    ("G3-image",
     'onClick:async()=>{confirm("Delete cette image ?")&&',
     'onClick:async()=>{' + D + '"Delete cette image ?")&&', 1),
    ("G4-render",
     'onClick:async()=>{confirm("Delete this render and its files?")&&',
     'onClick:async()=>{' + D + '"Delete this render and its files?")&&', 1),
    ("G5-job",
     'onClick:f=>{var m;(m=f==null?void 0:f.stopPropagation)==null||m.call(f),'
     'confirm("Delete this job and its files?")&&(o==null||o())}',
     'onClick:async f=>{var m;(m=f==null?void 0:f.stopPropagation)==null||m.call(f),('
     + D + '"Delete this job and its files?"))&&(o==null||o())}', 1),
    ("G6-feed-del",
     'async function del(id){if(!confirm("Remove this feed?"))return;',
     'async function del(id){if(!' + D + '"Remove this feed?"))return;', 1),
    ("G7-feed-f",
     'async function f(v){if(confirm("Remove this feed?")){',
     'async function f(v){if(' + D + '"Remove this feed?")){', 1),
    ("G8-rendu3d",
     'onClick:function(){if(window.confirm("Supprimer définitivement ce rendu 3D ?")){',
     'onClick:async function(){if(' + D + '"Supprimer définitivement ce rendu 3D ?")){', 1),
    ("G9-layout",
     "async function dzDelTemplate(id,nm,refresh,selId,setSel){if(!confirm('Delete le layout \"'",
     "async function dzDelTemplate(id,nm,refresh,selId,setSel){if(!" + D + "'Delete le layout \"'", 1),
    ("G10-captions",
     'async function y(){if(!confirm("Reset the caption pack to the deepotus defaults?',
     'async function y(){if(!' + D + '"Reset the caption pack to the deepotus defaults?', 1),
    ("G11-brand",
     'async function v(){if(!confirm("Reset name, taglines, colors and logo to the deepotus defaults?',
     'async function v(){if(!' + D + '"Reset name, taglines, colors and logo to the deepotus defaults?', 1),
    ("G12-print3d",
     '.then(function(x){if(!x.ok)throw new Error((x.d&&x.d.detail)||"export impossible");'
     'if(window.confirm("Dossier d\'impression écrit : "',
     '.then(async function(x){if(!x.ok)throw new Error((x.d&&x.d.detail)||"export impossible");'
     'if(' + D + '"Dossier d\'impression écrit : "', 1),
]

SONDE_AMONT = [("transfert", "__DZ_TRANSFERT_END__", 1)]


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


def nl(text, crlf):
    return text.replace("\n", "\r\n") if crlf else text


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
            raise SystemExit(f"[sonde-amont] {tag} : {jeton} ×{c} (attendu {n}) "
                             f"— maillon amont absent ou rejoué. Aborting.")


def main():
    args = sys.argv[1:]
    if "--force-unchained" not in args:
        guard_downstream(BAK)
    src = BAK if BAK.exists() else BUNDLE
    s, bom = lire(src)
    crlf = "\r\n" in s
    couche = COUCHE.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")

    if "--check" in args:
        sonder(s)
        for tag, a, _, n in PATCHES:
            c = s.count(nl(a, crlf))
            if c != n:
                raise SystemExit(f"[{tag}] anchor count={c} (want {n}) dans {src.name}.")
        if s.count(nl(ANCHOR_INJECT, crlf)) != 1:
            raise SystemExit("[G1] ancre d'injection absente ou multiple.")
        print(f"[{TAG}] applicable sur {src.name} ({len(PATCHES) + 1} ancres OK)")
        return

    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK.name)
    else:
        shutil.copy2(BAK, BUNDLE)
        s, bom = lire(BUNDLE)
        crlf = "\r\n" in s
    sonder(s)
    injection = nl("\n" + couche.strip() + "\n", crlf)
    s = apply(s, nl(ANCHOR_INJECT, crlf), nl(ANCHOR_INJECT, crlf) + injection, "G1-inject")
    for tag, a, rp, n in PATCHES:
        s = apply(s, nl(a, crlf), nl(rp, crlf), tag, n)
    ecrire(BUNDLE, s, bom)
    print(f"OK — {TAG} applique ({BUNDLE.stat().st_size} o).")


if __name__ == "__main__":
    main()
