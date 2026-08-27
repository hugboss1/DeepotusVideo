# -*- coding: utf-8 -*-
# scripts/patch_bundle_print3d.py
"""Patcher assert-garde : bouton « → Impression 3D » du panneau Game
Assets 3D (phase 2 du plan 2026-08-27-impression-3d-slicer).

BASELINE : bundle POST-patch vectorlab (dernier maillon en date).
Backup dedie : `.js.bak_print3d`. Position : EN QUEUE, apres vectorlab.

Deux sections :
  P1  le helper global `__dzPrint3d(sh)` — prompt de cible mm (vide =
      taille du fichier), POST /api/print3d/from-assets3d/{job}, puis
      proposition d'ouverture du .3mf dans le slicer. Injecte juste
      apres `var __dzManif3d={};` (avant le preambule dzdesign).
  P2  le bouton dans la rangee des formats du job (variante fontSize:11
      du panneau principal — la variante fontSize:10 des noeuds ne bouge
      pas).

DANGERS : identiques a cardforge/vectorlab — jamais `repatch_all.py
--from` sur cette chaine (mtimes menteurs vfxrack/subs), lancement SEUL,
newline='' partout (bundle CRLF), jamais d'ancre imprimee (console
cp1252).

Run :
    python scripts/patch_bundle_print3d.py              # depot
    python scripts/patch_bundle_print3d.py --check      # n'ecrit rien
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "print3d"
MARKER = "__dzPrint3d"

STABLE_PROBES = [
    ("screen-switch", 's==="assets3d"&&r.jsx(DzGameAssetsHub,{variant:e})', 1),
    ("cardforge-pane", 'src:"/cardforge/"', 1),
    ("vectorlab-pane", 'src:"/vectorlab/"', 1),
    ("navrail", "dz_nav_collapsed", 2),
    ("dzdesign", "__dzCatBar", 2),
]

SPEC_CHAR_DELTA = 1557
SPEC_BYTE_DELTA = 1567

HELPER = (
    "function __dzPrint3d(sh){try{"
    'var rep=window.prompt("Taille cible en mm ? (ex. 80 figurine, 250 '
    "plateau — la Centauri Carbon 2 imprime 256 mm ; vide = taille du "
    'fichier)","80");'
    "if(rep===null)return;"
    'var cible=rep.trim()===""?null:Number(rep.trim());'
    'if(cible!==null&&!(cible>0)){window.alert("taille en mm invalide");return}'
    'fetch("/api/print3d/from-assets3d/"+encodeURIComponent(sh),'
    '{method:"POST",headers:{"Content-Type":"application/json"},'
    "body:JSON.stringify(cible===null?{}:{cible_mm:cible})})"
    ".then(function(r){return r.json().then(function(d){return{ok:r.ok,d:d}})})"
    ".then(function(x){"
    'if(!x.ok)throw new Error((x.d&&x.d.detail)||"export impossible");'
    'if(window.confirm("Dossier d\'impression écrit : "+x.d.dossier+" ("'
    '+x.d.triangles+" triangles) — ouvrir le .3mf dans le slicer ?")){'
    'return fetch("/api/print3d/open",{method:"POST",'
    'headers:{"Content-Type":"application/json"},'
    "body:JSON.stringify({dossier:x.d.dossier})})"
    ".then(function(o){return o.json().then(function(od){"
    'if(!o.ok)throw new Error(od.detail||"ouverture impossible")})})}})'
    '.catch(function(e){window.alert("Impression 3D : "'
    "+String((e&&e.message)||e))})}catch(e){"
    'window.alert("Impression 3D : "+String((e&&e.message)||e))}}'
)

BOUTON = (
    'r.jsx("button",{onClick:function(){__dzPrint3d(sh)},'
    'style:{fontSize:11,padding:"4px 8px",borderRadius:6,cursor:"pointer",'
    'background:"var(--surface-2)",border:"1px solid var(--stroke)",'
    'color:"var(--ink)"},'
    'title:"Dossier d\'impression STL + 3MF aux mm réels '
    "(assets/print3d) puis ouverture du .3mf dans le slicer — "
    'ElegooSlicer/OrcaSlicer",children:"→ Impression 3D"},"p3d"),'
)

_A_HELPER = "var __dzManif3d={};"
_A_ROW = ('(mf.formats||[]).map(function(fm){return r.jsx("a",'
          '{href:"/api/assets/3d/"+sh+"/"+fm,download:!0,style:{fontSize:11')

PATCHES = [
    ("P1-helper", _A_HELPER, _A_HELPER + HELPER),
    ("P2-bouton", _A_ROW, BOUTON + _A_ROW),
]


def deltas():
    dc = sum(len(r) - len(a) for _t, a, r in PATCHES)
    db = sum(len(r.encode("utf-8")) - len(a.encode("utf-8"))
             for _t, a, r in PATCHES)
    return dc, db


def check_spec_parity():
    dc, db = deltas()
    if (dc, db) != (SPEC_CHAR_DELTA, SPEC_BYTE_DELTA):
        raise SystemExit(
            f"[{TAG}] parite spec rompue : delta calcule {dc} car / {db} o, "
            f"spec {SPEC_CHAR_DELTA} car / {SPEC_BYTE_DELTA} o. Aborting.")
    return dc, db


def guard_downstream(bak):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name}. "
                "print3d doit rester le DERNIER maillon ; jamais de "
                "repatch_all sur cette chaine.")


def ensure_tail_order(bak):
    stem = bak.name.rsplit(".bak_", 1)[0]
    others = [p.stat().st_mtime for p in bak.parent.glob(stem + ".bak_*")
              if p != bak]
    if not others:
        return False
    top = max(others)
    if bak.stat().st_mtime > top:
        return False
    t = max(time.time(), top + 1.0)
    os.utime(bak, (t, t))
    return True


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def read_src(p):
    return p.read_text(encoding="utf-8", newline="")


def eol_stats(data):
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf, data.count(b"\r") - crlf


def resolve_root(args):
    if "--root" in args:
        return pathlib.Path(args[args.index("--root") + 1]).resolve()
    here = pathlib.Path(".").resolve()
    if (here / REL_BUNDLE).is_file():
        return here
    return pathlib.Path(__file__).resolve().parent.parent


def main():
    args = sys.argv[1:]
    check = "--check" in args
    dc, db = check_spec_parity()
    root = resolve_root(args)
    bundle = root / REL_BUNDLE
    if not bundle.is_file():
        raise SystemExit(f"[{TAG}] bundle introuvable : {bundle}")
    bak = bundle.with_name(bundle.name + ".bak_" + TAG)
    if "--force-unchained" not in args:
        guard_downstream(bak)

    if check:
        src = bak if bak.exists() else bundle
        s = read_src(src)
        if s.count(MARKER):
            raise SystemExit(
                f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans "
                f"{src.name} — double application refusee. Si cette racine "
                "est l'APP INSTALLEE : on y COPIE le bundle patche du depot, "
                "on ne la repatche jamais.")
        for tag, anchor, _r in PATCHES:
            n = s.count(anchor)
            if n != 1:
                raise SystemExit(f"[{tag}] anchor count={n} (want 1). "
                                 "Aborting.")
        for name, probe, want in STABLE_PROBES:
            if s.count(probe) != want:
                raise SystemExit(f"[sonde {name}] count={s.count(probe)} "
                                 f"(want {want}). Aborting.")
        raw = src.read_bytes()
        crlf, lf, cr = eol_stats(raw)
        print(f"[{TAG}] applicable sur {src}")
        print(f"[{TAG}] 2 ancres OK, marqueur absent, "
              f"{len(STABLE_PROBES)} sondes aux comptes")
        print(f"[{TAG}] CRLF={crlf} LF-isole={lf} CR-isole={cr} ; "
              f"delta +{dc} car / +{db} o")
        return

    if not bak.exists():
        if MARKER in read_src(bundle):
            raise SystemExit(
                f"[{TAG}] marqueur present sans {bak.name} : etat ambigu, "
                "abandon sans rien ecrire.")
        shutil.copy2(bundle, bak)
        if ensure_tail_order(bak):
            print("mtime du backup pousse en queue de chaine")
        print("backup ->", bak.name)
    else:
        shutil.copy2(bak, bundle)
        print("restore <-", bak.name)

    before = bundle.read_bytes()
    crlf0, lf0, cr0 = eol_stats(before)
    if lf0 or cr0:
        raise SystemExit(f"[{TAG}] fins de ligne non homogenes. Aborting.")
    s = read_src(bundle)
    chars0 = len(s)
    if MARKER in s:
        raise SystemExit(f"[{TAG}] backup empoisonne (marqueur present "
                         "apres restore). Aborting.")
    for tag, anchor, repl in PATCHES:
        s = apply(s, anchor, repl, tag)
    with open(bundle, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)

    after = bundle.read_bytes()
    crlf1, lf1, cr1 = eol_stats(after)
    problems = []
    if (crlf1, lf1, cr1) != (crlf0, 0, 0):
        problems.append("fins de ligne changees")
    if len(after) != len(before) + db:
        problems.append(f"taille {len(after)} o, attendu {len(before) + db}")
    if len(s) != chars0 + dc:
        problems.append(f"caracteres {len(s)}, attendu {chars0 + dc}")
    if s.count(MARKER) != 2:      # la definition + l'appel du bouton
        problems.append(f"marqueur x{s.count(MARKER)} (want 2)")
    for tag, anchor in (("P1", _A_HELPER), ("P2", _A_ROW)):
        if s.count(anchor) != 1:
            problems.append(f"{tag} : ancre x{s.count(anchor)} (want 1)")
    for name, probe, want in STABLE_PROBES:
        if s.count(probe) != want:
            problems.append(f"sonde {name} x{s.count(probe)} (want {want})")
    if problems:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problems))
    print("OK - bundle patche (bouton -> Impression 3D du panneau Game "
          "Assets 3D).")
    print(f"   taille : {len(before)} -> {len(after)} o (+{db})")
    print("   suite  : copie .mjs + node --check, puis DEPLOYER le bundle")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
