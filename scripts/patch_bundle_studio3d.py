# scripts/patch_bundle_studio3d.py
"""Assert-guarded patcher: sous-onglet « 3D Studio » du hub Game Assets (v2.1).

BASELINE: bundle POST-patch node-style-cinema (dernier patch en date, v2.0.0).
Backup dédié: .js.bak_studio3d (état juste avant CE patch).

Le hub « 3D | Sprites 2D | Tuiles » (patchs spritelab + tilelab) gagne un
quatrième sous-onglet « 🐙 3D Studio » = iframe /studio3d (page standalone
hors bundle — écran 1 du design « DeepOtus Studio », pipeline Meshy réel :
prompt/réf → maillage → texture → remesh → rig → animations → export).
Placé juste après « 🧊 3D » : le flux fal une-passe reste l'onglet par
défaut, intact (contrainte du chantier).

`deepotus:navigate` accepte déjà n'importe quel detail.subtab (S4 spritelab) ;
on étend l'état du hub ("studio3d" accepté au montage + par l'event relais
deepotus:assets-subtab — c'est ce que dispatch la page /studio3d elle-même
pour « ouvrir Game Assets 3D (fal) » et « 04 · Sprite Sheet → »).

Run: python scripts/patch_bundle_studio3d.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_studio3d")


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

    # S3-1: état initial du hub — "studio3d" est un sous-onglet valide.
    a = 'return t==="sprites"||t==="tiles"?t:"3d"}'
    r = 'return t==="sprites"||t==="tiles"||t==="studio3d"?t:"3d"}'
    s = apply(s, a, r, "S3D1-init-state")

    # S3-2: event relais — bascule aussi vers "studio3d".
    a = 'if(d.subtab==="sprites"||d.subtab==="3d"||d.subtab==="tiles")setTab(d.subtab)'
    r = ('if(d.subtab==="sprites"||d.subtab==="3d"||d.subtab==="tiles"'
         '||d.subtab==="studio3d")setTab(d.subtab)')
    s = apply(s, a, r, "S3D2-relay-event")

    # S3-3: la rangée d'onglets gagne « 3D Studio », juste après « 3D ».
    a = 'children:[tb("3d","🧊 3D"),tb("sprites","🧩 Sprites 2D"),tb("tiles","🧱 Tuiles")]},"tabs")'
    r = ('children:[tb("3d","🧊 3D"),tb("studio3d","🐙 3D Studio"),'
         'tb("sprites","🧩 Sprites 2D"),tb("tiles","🧱 Tuiles")]},"tabs")')
    s = apply(s, a, r, "S3D3-tab-btn")

    # S3-4: le panneau — ternaire à 4 branches (3d / sprites / tiles / studio3d).
    a = ':r.jsx("iframe",{src:"/tilelab/",title:"Tile Lab",'
    r = ':tab==="tiles"?r.jsx("iframe",{src:"/tilelab/",title:"Tile Lab",'
    s = apply(s, a, r, "S3D4a-ternary")

    a = 'marginTop:10,background:"var(--bg-base)"}},"ptl")]})}'
    r = ('marginTop:10,background:"var(--bg-base)"}},"ptl")'
         ':r.jsx("iframe",{src:"/studio3d/",title:"3D Studio",'
         'style:{flex:1,width:"100%",minHeight:"calc(100vh - 110px)",'
         'border:"0",marginTop:10,background:"var(--bg-base)"}},"ps3")]})}')
    s = apply(s, a, r, "S3D4b-studio3d-pane")

    # S3-5: description de l'entrée de navigation.
    a = 'desc:"image → 3D, sprites & tuiles"'
    r = 'desc:"3D studio, sprites & tuiles"'
    s = apply(s, a, r, "S3D5-nav-desc")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (hub 3D|3D Studio|Sprites|Tuiles). Size:",
          BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
