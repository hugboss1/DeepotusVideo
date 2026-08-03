# scripts/patch_bundle_asset3dopt.py
"""Assert-guarded patcher: Optimize 3D — budgets de triangles (chantier 10a).

BASELINE: bundle POST-patch libsprites (dernier patch en date).
Backup dédié: .js.bak_asset3dopt (état juste avant CE patch).

Ajoute :
- DzOptimize : zone « Optimize » dans chaque carte 3D terminée du hub —
  select de presets (Micro 500 → Ultra 100k, défaut Game Ready 10k),
  bouton Optimiser (POST /api/assets/3d/{sh}/optimize, gltfpack local),
  stats avant→après (tris, −%), download du GLB optimisé, comparateur
  Original | Optimisé (2 × model-viewer). Les stats persistées
  (optimize.json) sont rechargées au montage.
- DzOptGlbBtn : bouton « GLB optimisé » dans le modal 3D de la Library
  (probe HEAD /opt-glb, affiché seulement si le fichier existe).

NOTE EOL: la zone DzGameAssets du bundle contient des CRLF ; read_text
les normalise en \\n (anchors ci-dessous en \\n), write_text restitue
os.linesep — round-trip stable sous Windows.

Run: python scripts/patch_bundle_asset3dopt.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_asset3dopt")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


BTN = ('style:{fontSize:11,padding:"4px 8px",borderRadius:6,cursor:"pointer",'
       'background:"var(--surface-2)",border:"1px solid var(--stroke)",'
       'color:"var(--ink)"}')

DZ_OPTIMIZE = (
    'function DzOptFmt(n){return n>=1e6?(n/1e6).toFixed(2)+"M"'
    ':n>=1e3?(n/1e3).toFixed(1)+"k":String(n)}'
    'function DzOptimize({sh}){'
    'var IS=x.useState(null),info=IS[0],setInfo=IS[1],'
    'BS=x.useState(!1),busy=BS[0],setBusy=BS[1],'
    'CS=x.useState(!1),cmp=CS[0],setCmp=CS[1],'
    'PS=x.useState("game"),pre=PS[0],setPre=PS[1],'
    'ES=x.useState(""),err=ES[0],setErr=ES[1];'
    'x.useEffect(function(){var on=!0;'
    'fetch("/api/assets/3d/"+sh+"/optimize")'
    '.then(function(r2){return r2.ok?r2.json():null})'
    '.then(function(d){on&&d&&setInfo(d)}).catch(function(){});'
    'return function(){on=!1}},[sh]);'
    'function run(){if(busy)return;setBusy(!0);setErr("");'
    'fetch("/api/assets/3d/"+sh+"/optimize",{method:"POST",'
    'headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify({preset:pre})})'
    '.then(function(r2){return r2.json()'
    '.then(function(j){return{ok:r2.ok,j:j}})'
    '.catch(function(){return{ok:r2.ok,j:{}}})})'
    '.then(function(x2){setBusy(!1);'
    'if(!x2.ok){setErr(String((x2.j&&x2.j.detail)||"échec optimisation"));return}'
    'setInfo(x2.j);setCmp(!0)})'
    '.catch(function(e2){setBusy(!1);setErr(String(e2&&e2.message||e2))})}'
    'var opts=[["micro","Micro (500)"],["small","Small (1k)"],'
    '["prop","Prop (2.5k)"],["detailed","Detailed (5k)"],'
    '["game","Game Ready (10k)"],["balanced","Balanced (25k)"],'
    '["high","High (50k)"],["ultra","Ultra (100k)"]];'
    'var ts=info?encodeURIComponent(info.created_at||""):"";'
    'return r.jsxs("div",{style:{borderTop:"1px solid var(--stroke)",'
    'paddingTop:8,display:"flex",flexDirection:"column",gap:6},children:['
    'r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center",'
    'flexWrap:"wrap"},children:['
    'r.jsx("span",{style:{fontSize:11,color:"var(--ink-soft)"},'
    'children:"Optimize"},"lb"),'
    'r.jsx("select",{value:pre,'
    'onChange:function(ev){setPre(ev.target.value)},' + BTN + ','
    'children:opts.map(function(o){return r.jsx("option",'
    '{value:o[0],children:o[1]},o[0])})},"sel"),'
    'r.jsx("button",{onClick:run,disabled:busy,' + BTN + ','
    'children:busy?"Optimisation…":"⚙ Optimiser"},"go"),'
    'info?r.jsx("a",{href:"/api/assets/3d/"+sh+"/opt-glb",download:!0,'
    'style:{fontSize:11,padding:"4px 8px",borderRadius:6,'
    'textDecoration:"none",background:"var(--surface-2)",'
    'border:"1px solid var(--stroke)",color:"var(--cyan)"},'
    'children:"↓ GLB optimisé"},"dl"):null,'
    'info?r.jsx("button",{onClick:function(){setCmp(!cmp)},' + BTN + ','
    'children:cmp?"▣ Simple":"⇆ Comparer"},"cp"):null]},"row"),'
    'err?r.jsx("div",{style:{fontSize:11,color:"var(--red)"},'
    'children:err},"er"):null,'
    'info?r.jsxs("div",{style:{fontSize:11,fontFamily:"var(--f-mono)",'
    'color:"var(--ink-strong)"},children:['
    'DzOptFmt(info.before.tris)," → ",DzOptFmt(info.after.tris),'
    '" tris · −",String(info.reduction_pct),"%",'
    'info.preset?" · "+info.preset:""]},"st"):null,'
    'cmp&&info?r.jsxs("div",{style:{display:"grid",'
    'gridTemplateColumns:"1fr 1fr",gap:6},children:['
    'r.jsxs("div",{children:[r.jsx("div",{style:{fontSize:10,'
    'color:"var(--ink-soft)",marginBottom:2},'
    'children:"Original · "+DzOptFmt(info.before.tris)+" tris"}),'
    'r.jsx("model-viewer",{src:"/api/assets/3d/"+sh+"/glb",'
    '"camera-controls":!0,"auto-rotate":!0,'
    'style:{width:"100%",height:200,background:"#0b1016",borderRadius:8}})]},"o"),'
    'r.jsxs("div",{children:[r.jsx("div",{style:{fontSize:10,'
    'color:"var(--green)",marginBottom:2},'
    'children:"Optimisé · "+DzOptFmt(info.after.tris)+" tris"}),'
    'r.jsx("model-viewer",{src:"/api/assets/3d/"+sh+"/opt-glb?v="+ts,'
    '"camera-controls":!0,"auto-rotate":!0,'
    'style:{width:"100%",height:200,background:"#0b1016",borderRadius:8}})]},"p")'
    ']},"cmp"):null]})}'
)

DZ_OPTGLB_BTN = (
    'function DzOptGlbBtn({short}){'
    'var OS=x.useState(!1),ok=OS[0],setOk=OS[1];'
    'x.useEffect(function(){var on=!0;'
    'fetch("/api/assets/3d/"+short+"/opt-glb",{method:"HEAD"})'
    '.then(function(r2){on&&setOk(r2.ok)}).catch(function(){});'
    'return function(){on=!1}},[short]);'
    'if(!ok)return null;'
    'return r.jsx("a",{href:"/api/assets/3d/"+short+"/opt-glb",download:!0,'
    'style:{textDecoration:"none"},children:r.jsx(K,{variant:"outline",'
    'size:"sm",icon:"download",children:"GLB optimisé"})})}'
)


def main():
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")

    # P-1: composants module scope, juste avant DzGameAssets.
    a = 'function DzGameAssets({variant:e}){'
    r = DZ_OPTIMIZE + DZ_OPTGLB_BTN + a
    s = apply(s, a, r, "P1-components")

    # P-2: zone Optimize dans la carte 3D (entre formats et shots).
    a = ('children:"↓ "+fm.toUpperCase()},fm)})\n'
         '  ]}):null,\n'
         '  (done&&(mf.shots||[]).length)?')
    r = ('children:"↓ "+fm.toUpperCase()},fm)})\n'
         '  ]}):null,\n'
         '  done?r.jsx(DzOptimize,{sh:sh},"opt"+sh):null,\n'
         '  (done&&(mf.shots||[]).length)?')
    s = apply(s, a, r, "P2-card-zone")

    # P-3: modal 3D de la Library — download du GLB optimisé si présent.
    a = ('m.jobId&&(m.kind==="asset3d"||m.kind==="sprite2d")&&r.jsx(K,'
         '{variant:"ghost",size:"sm",'
         'onClick:()=>{var nn=window.prompt("Rename asset:",m.name);')
    r = ('m.kind==="asset3d"&&m.short&&r.jsx(DzOptGlbBtn,'
         '{short:m.short},"optglb"),'
         'm.jobId&&(m.kind==="asset3d"||m.kind==="sprite2d")&&r.jsx(K,'
         '{variant:"ghost",size:"sm",'
         'onClick:()=>{var nn=window.prompt("Rename asset:",m.name);')
    s = apply(s, a, r, "P3-library-optglb")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (Optimize 3D). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
