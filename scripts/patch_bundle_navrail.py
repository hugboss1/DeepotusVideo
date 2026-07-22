# -*- coding: utf-8 -*-
# scripts/patch_bundle_navrail.py
"""Assert-guarded patcher : persistance du rail de navigation (sidebar).

BASELINE : bundle POST-patch nodedock (dernier patch en date).
Backup dédié : .js.bak_navrail (état juste avant CE patch).

La sidebar tg sait déjà se replier en rail d'icônes 64 px (bouton « Collapse »
caret, tooltips par title, bouton « Expand » caretR en bas) — mais l'état
n'était PAS persisté : useState(initialSidebar=false) à chaque lancement.

Ce patch :
- initialise collapsed depuis localStorage dz_nav_collapsed ("1" replié,
  absent/"0" déplié — le défaut initialSidebar reste le fallback) ;
- persiste chaque toggle en interceptant setCollapsed au point de montage
  unique de tg.

Run : python scripts/patch_bundle_navrail.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_navrail")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def main():
    s = BUNDLE.read_text(encoding="utf-8")
    if "dz_nav_collapsed" in s:
        raise SystemExit("Bundle déjà patché (dz_nav_collapsed présent). Aborting.")
    if not BAK.exists():
        shutil.copyfile(BUNDLE, BAK)
        print("backup ->", BAK.name)

    # S1 : init de collapsed depuis localStorage (lazy initializer useState).
    a = ('initialSidebar:n=!1,initialDock:o=!1,motionOn:i=!0}){'
         'const[s,a]=x.useState(sg||t),[l,d]=x.useState(n),')
    r = ('initialSidebar:n=!1,initialDock:o=!1,motionOn:i=!0}){'
         'const[s,a]=x.useState(sg||t),[l,d]=x.useState(function(){'
         'try{var v1=localStorage.getItem("dz_nav_collapsed");'
         'return v1===null?n:v1==="1"}catch(_e){return n}}),')
    s = apply(s, a, r, "S1-init")

    # S2 : persistance au toggle (interception de setCollapsed au montage).
    a = 'r.jsx(tg,{view:s,setView:a,collapsed:l,setCollapsed:d})'
    r = ('r.jsx(tg,{view:s,setView:a,collapsed:l,'
         'setCollapsed:function(v1){try{localStorage.setItem("dz_nav_collapsed",v1?"1":"0")}'
         'catch(_e){}d(v1)}})')
    s = apply(s, a, r, "S2-persist")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (navrail persistance). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
