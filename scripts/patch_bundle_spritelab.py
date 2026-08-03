# scripts/patch_bundle_spritelab.py
"""Assert-guarded patcher: hub Game Assets « 3D | Sprites 2D » (chantier 9c).

BASELINE: bundle POST-patch imagegen (dernier patch en date).
Backup dédié: .js.bak_spritelab (état juste avant CE patch).

L'onglet Game Assets devient un hub à sous-onglets :
- « 🧊 3D »        = DzGameAssets existant (image → mesh, inchangé) ;
- « 🧩 Sprites 2D » = iframe /spritelab (page standalone hors bundle,
                      même pattern que DzChapitres → /atelier).

L'event `deepotus:navigate` accepte un detail.subtab ("sprites"|"3d") pour
ouvrir directement le bon sous-onglet (utilisé par le hand-off 9d) :
window.__dzSubtab est lu par le hub à son montage, et l'event relais
`deepotus:assets-subtab` bascule un hub déjà monté.

Run: python scripts/patch_bundle_spritelab.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_spritelab")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


# ── le hub (module scope, hoisté comme DzGameAssets/DzChapitres) ─────────────
HUB = (
    'function DzGameAssetsHub({variant:e}){'
    'var ts=x.useState(function(){var t=null;'
    'try{t=window.__dzSubtab;delete window.__dzSubtab}catch(err){}'
    'return t==="sprites"?"sprites":"3d"}),tab=ts[0],setTab=ts[1];'
    'x.useEffect(function(){function h(ev){var d=(ev&&ev.detail)||{};'
    'if(d.subtab==="sprites"||d.subtab==="3d")setTab(d.subtab)}'
    'window.addEventListener("deepotus:assets-subtab",h);'
    'return function(){window.removeEventListener("deepotus:assets-subtab",h)}},[]);'
    'function tb(id,lbl){var on=tab===id;'
    'return r.jsx("button",{onClick:function(){setTab(id)},'
    'style:{fontSize:12,padding:"6px 14px",borderRadius:7,'
    'border:"1px solid "+(on?"var(--cyan)":"var(--stroke)"),'
    'background:on?"rgba(77,216,230,.12)":"var(--bg-panel)",'
    'color:on?"var(--cyan)":"var(--ink-soft)",cursor:"pointer"},'
    'children:lbl},id)}'
    'return r.jsxs("div",{style:{display:"flex",flexDirection:"column",'
    'height:"100%",minHeight:0},children:['
    'r.jsxs("div",{style:{display:"flex",gap:8,padding:"14px 24px 0",'
    'flex:"0 0 auto"},children:[tb("3d","🧊 3D"),tb("sprites","🧩 Sprites 2D")]},"tabs"),'
    'tab==="3d"?r.jsx("div",{style:{flex:1,minHeight:0,overflow:"auto"},'
    'children:r.jsx(DzGameAssets,{variant:e})},"p3d")'
    ':r.jsx("iframe",{src:"/spritelab/",title:"Sprite Lab",'
    'style:{flex:1,width:"100%",minHeight:"calc(100vh - 110px)",border:"0",'
    'marginTop:10,background:"var(--bg-base)"}},"p2d")]})}'
)


def main():
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")

    # S-1: entrée de navigation — la description annonce le 2D.
    a = 'desc:"image → 3D model"'
    r = 'desc:"image → 3D & sprites"'
    s = apply(s, a, r, "S1-nav-desc")

    # S-2: définition du hub, hoistée juste avant DzGameAssets (même scope).
    a = 'var __dzManif3d={};function DzGameAssets({variant:e}){'
    r = 'var __dzManif3d={};' + HUB + 'function DzGameAssets({variant:e}){'
    s = apply(s, a, r, "S2-hub-def")

    # S-3: la branche du switch rend le hub (le composant 3D vit dedans).
    a = 's==="assets3d"&&r.jsx(DzGameAssets,{variant:e})'
    r = 's==="assets3d"&&r.jsx(DzGameAssetsHub,{variant:e})'
    s = apply(s, a, r, "S3-switch-hub")

    # S-4: deepotus:navigate — detail.subtab ouvre le bon sous-onglet
    # (mémorisé pour un hub pas encore monté + event pour un hub monté).
    a = ('try{var Tp=I&&I.detail&&I.detail.templateId;if(Tp)window.__dzTpl=Tp}'
         'catch(Z){}A&&Yu.includes(A)&&a(A)')
    r = ('try{var Tp=I&&I.detail&&I.detail.templateId;if(Tp)window.__dzTpl=Tp}'
         'catch(Z){}'
         'try{var Sb=I&&I.detail&&I.detail.subtab;'
         'if(Sb){window.__dzSubtab=Sb;'
         'setTimeout(function(){window.dispatchEvent('
         'new CustomEvent("deepotus:assets-subtab",{detail:{subtab:Sb}}))},80)}}'
         'catch(Z9){}'
         'A&&Yu.includes(A)&&a(A)')
    s = apply(s, a, r, "S4-navigate-subtab")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (Game Assets hub 3D|Sprites). Size:",
          BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
