# -*- coding: utf-8 -*-
# scripts/patch_bundle_materialforge.py
"""Patcher assert-gardé : sous-onglet « ✨ Matières » du hub Game Assets.

BASELINE : bundle POST-patch sfxstudio (dernier patch en date).
Backup dédié : .js.bak_materialforge (état juste avant CE patch).
Position dans la chaîne : EN QUEUE, après `sfxstudio`.

Le hub `DzGameAssetsHub` (3D | 3D Studio | Sprites 2D | Tuiles) gagne un
onglet de plus : « ✨ Matières » = iframe /materialforge/, page standalone
hors bundle (Material Forge Deepotus, cf. SPEC §7). Le relais
`deepotus:navigate` → `deepotus:assets-subtab` accepte déjà n'importe quel
`detail.subtab` : on étend seulement l'état accepté par le hub
(au montage via `window.__dzSubtab`, et par l'écouteur de l'événement).

Mécanique identique à patch_bundle_tilelab.py : restauration du .bak dédié
puis ré-application, chaque ancre devant apparaître EXACTEMENT une fois,
sinon abandon sans rien écrire.

Run :
    python scripts/patch_bundle_materialforge.py              # dépôt
    python scripts/patch_bundle_materialforge.py --root <dir> # app installée
    python scripts/patch_bundle_materialforge.py --check      # n'écrit rien

Compatible scripts/repatch_all.py : `--force-unchained` est accepté et ignoré.
"""
import pathlib
import shutil
import sys

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "materialforge"

# (nom de section, ancre, remplacement) — l'ancre doit être unique.
PATCHES = [
    # M-1 : état initial du hub — « materials » est un sous-onglet valide
    # (chemin window.__dzSubtab, posé par deepotus:navigate).
    ("M1-init-state",
     'return t==="sprites"||t==="tiles"||t==="studio3d"?t:"3d"}',
     'return t==="sprites"||t==="tiles"||t==="studio3d"||t==="materials"'
     '?t:"3d"}'),

    # M-2 : événement relais deepotus:assets-subtab — bascule aussi vers
    # « materials » quand le hub est déjà monté.
    ("M2-relay-event",
     'if(d.subtab==="sprites"||d.subtab==="3d"||d.subtab==="tiles"'
     '||d.subtab==="studio3d")setTab(d.subtab)',
     'if(d.subtab==="sprites"||d.subtab==="3d"||d.subtab==="tiles"'
     '||d.subtab==="studio3d"||d.subtab==="materials")setTab(d.subtab)'),

    # M-3 : la rangée d'onglets gagne « ✨ Matières », en dernière position.
    ("M3-tab-btn",
     'tb("tiles","\U0001f9f1 Tuiles")]},"tabs")',
     'tb("tiles","\U0001f9f1 Tuiles"),tb("materials","✨ Matières")]},'
     '"tabs")'),

    # M-4 : le panneau — nouvelle branche avant la branche par défaut
    # (3D Studio), pour ne pas déplacer le fallback existant.
    ("M4-materials-pane",
     ':r.jsx("iframe",{src:"/studio3d/",title:"3D Studio",',
     ':tab==="materials"?r.jsx("iframe",{src:"/materialforge/",'
     'title:"Material Forge",style:{flex:1,width:"100%",'
     'minHeight:"calc(100vh - 110px)",border:"0",marginTop:10,'
     'background:"var(--bg-base)"}},"pmf")'
     ':r.jsx("iframe",{src:"/studio3d/",title:"3D Studio",'),

    # M-5 : description de l'entrée de navigation du rail.
    ("M5-nav-desc",
     'desc:"3D studio, sprites & tuiles"',
     'desc:"3D studio, sprites, tuiles & matières"'),
]


def apply(s, anchor, replacement, tag):
    """Remplacement assert-gardé : l'ancre doit exister exactement une fois."""
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def main():
    args = sys.argv[1:]
    root = pathlib.Path(".")
    if "--root" in args:
        root = pathlib.Path(args[args.index("--root") + 1]).resolve()
    check = "--check" in args

    bundle = root / REL_BUNDLE
    if not bundle.is_file():
        raise SystemExit(f"[{TAG}] bundle introuvable : {bundle}")
    bak = bundle.with_name(bundle.name + ".bak_" + TAG)

    if check:
        # Contrôle à sec : on valide les ancres sur l'état PRÉ-patch
        # (le .bak s'il existe, sinon le bundle courant), sans rien écrire.
        src = bak if bak.exists() else bundle
        s = src.read_text(encoding="utf-8")
        for tag, anchor, _repl in PATCHES:
            n = s.count(anchor)
            if n != 1:
                raise SystemExit(
                    f"[{tag}] anchor count={n} (want 1) dans {src.name}. "
                    "Aborting.")
        print(f"[{TAG}] applicable sur {src} ({len(PATCHES)} ancres OK)")
        return

    if not bak.exists():
        shutil.copy2(bundle, bak)
        print("backup ->", bak)
    else:
        shutil.copy2(bak, bundle)

    s = bundle.read_text(encoding="utf-8")
    for tag, anchor, repl in PATCHES:
        s = apply(s, anchor, repl, tag)

    bundle.write_text(s, encoding="utf-8")
    print("OK — bundle patché (hub 3D|3D Studio|Sprites|Tuiles|Matières). "
          "Size:", bundle.stat().st_size)


if __name__ == "__main__":
    main()
