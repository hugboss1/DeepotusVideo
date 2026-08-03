# scripts/patch_bundle_tilelab.py
"""Assert-guarded patcher: sous-onglet « Tuiles » du hub Game Assets (9e).

BASELINE: bundle POST-patch asset3dopt (dernier patch en date).
Backup dédié: .js.bak_tilelab (état juste avant CE patch).

Le hub « 3D | Sprites 2D » (injecté par patch_bundle_spritelab) gagne un
troisième sous-onglet « 🧱 Tuiles » = iframe /tilelab (page standalone hors
bundle, chantier 9e). `deepotus:navigate` accepte déjà n'importe quel
detail.subtab (S4 du patch spritelab) : on étend seulement l'état du hub
("tiles" accepté au montage + par l'event relais deepotus:assets-subtab).

Run: python scripts/patch_bundle_tilelab.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_tilelab")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def main():
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")

    # T-1: état initial du hub — "tiles" est un sous-onglet valide.
    a = 'return t==="sprites"?"sprites":"3d"}'
    r = 'return t==="sprites"||t==="tiles"?t:"3d"}'
    s = apply(s, a, r, "T1-init-state")

    # T-2: event relais — bascule aussi vers "tiles".
    a = 'if(d.subtab==="sprites"||d.subtab==="3d")setTab(d.subtab)'
    r = ('if(d.subtab==="sprites"||d.subtab==="3d"||d.subtab==="tiles")'
         'setTab(d.subtab)')
    s = apply(s, a, r, "T2-relay-event")

    # T-3: la rangée d'onglets gagne « Tuiles ».
    a = 'children:[tb("3d","🧊 3D"),tb("sprites","🧩 Sprites 2D")]},"tabs")'
    r = ('children:[tb("3d","🧊 3D"),tb("sprites","🧩 Sprites 2D"),'
         'tb("tiles","🧱 Tuiles")]},"tabs")')
    s = apply(s, a, r, "T3-tab-btn")

    # T-4: le panneau — ternaire à 3 branches (3d / sprites / tiles).
    a = ':r.jsx("iframe",{src:"/spritelab/",title:"Sprite Lab",'
    r = ':tab==="sprites"?r.jsx("iframe",{src:"/spritelab/",title:"Sprite Lab",'
    s = apply(s, a, r, "T4a-ternary")

    a = ('marginTop:10,background:"var(--bg-base)"}},"p2d")]})}')
    r = ('marginTop:10,background:"var(--bg-base)"}},"p2d")'
         ':r.jsx("iframe",{src:"/tilelab/",title:"Tile Lab",'
         'style:{flex:1,width:"100%",minHeight:"calc(100vh - 110px)",'
         'border:"0",marginTop:10,background:"var(--bg-base)"}},"ptl")]})}')
    s = apply(s, a, r, "T4b-tiles-pane")

    # T-5: description de l'entrée de navigation.
    a = 'desc:"image → 3D & sprites"'
    r = 'desc:"image → 3D, sprites & tuiles"'
    s = apply(s, a, r, "T5-nav-desc")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (hub 3D|Sprites|Tuiles). Size:",
          BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
