# scripts/patch_bundle_presets.py
"""Idempotent, assert-guarded patcher for the HeyGen Quick/Studio picker.
Run: python scripts/patch_bundle_presets.py
Creates a .bak once (the pristine bundle), then on every run restores from it so
all patches compose from a clean base. Each patch asserts its anchor occurs
exactly once. The file is written only after ALL patches succeed."""
import pathlib, shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def main():
    bak = BUNDLE.with_suffix(".js.bak")
    if not bak.exists():
        shutil.copy2(BUNDLE, bak)
        print("backup ->", bak)
    else:
        shutil.copy2(bak, BUNDLE)  # restore clean base so all patches compose
    s = BUNDLE.read_text(encoding="utf-8")

    # ---- PATCH B: Quick avatar preview image after the "Avatar" select ----
    anchor_b = 'r.jsx(O,{label:"Avatar",children:r.jsx(re,{value:C,options:U.filter(B=>{const Z=S.trim().toLowerCase();return Z?`${B.name||""} ${B.avatar_id||""} ${B.avatar_type||""}`.toLowerCase().includes(Z):!0}).slice(0,200).map(B=>({value:B.avatar_id,label:`${B._kind==="talking_photo"?"📷 ":""}${B.name||B.avatar_id} ${B.gender?`· ${B.gender}`:""}`})),onChange:Q})})'
    preview_b = anchor_b + ',(()=>{const _a=U.find(B=>B.avatar_id===C);const _u=_a&&_a.preview_image_url;return r.jsx("div",{style:{marginTop:4,aspectRatio:"9 / 16",maxHeight:200,background:"#02060d",border:"1px solid var(--stroke)",borderRadius:8,overflow:"hidden",display:"flex",alignItems:"center",justifyContent:"center"},children:_u?r.jsx("img",{src:_u,alt:"avatar",onLoad:e=>{e.currentTarget.style.opacity=1},onError:e=>{e.currentTarget.style.opacity=0},style:{width:"100%",height:"100%",objectFit:"cover"}}):r.jsx("span",{style:{fontSize:10.5,color:"var(--ink-soft)",padding:8,textAlign:"center"},children:"Pick an avatar to preview"})})})()'
    s = apply(s, anchor_b, preview_b, "B-avatar-preview")

    # ---- PATCH STATE: voice-search (vq) + preset (pr,pn) hooks in Quick (um) ----
    anchor_state = '[S,L]=x.useState(""),[J,de]=x.useState(!1)'
    add_state = '[S,L]=x.useState(""),[vq,Vq]=x.useState(""),[pr,Pr]=x.useState([]),[pn,Pn]=x.useState(""),[J,de]=x.useState(!1)'
    s = apply(s, anchor_state, add_state, "STATE-quick-hooks")

    # ---- PATCH LOADER: fetch presets on mount into pr ----
    anchor_load = ',[Ce,at]=x.useState(null);'
    add_load = ',[Ce,at]=x.useState(null);x.useEffect(()=>{let on=!0;fetch("/api/heygen/presets").then(R=>R.ok?R.json():{presets:[]}).then(d=>{if(on)Pr((d&&d.presets)||[])}).catch(()=>{});return()=>{on=!1}},[]);'
    s = apply(s, anchor_load, add_load, "LOADER-quick-presets")

    # ---- PATCH A1: "Search voices" field after "Search avatars" ----
    anchor_a1 = 'r.jsx(O,{label:"Search avatars",children:r.jsx(le,{icon:"search",value:S,onChange:L,placeholder:`Search ${U.length} avatars…`})}),'
    add_a1 = anchor_a1 + 'r.jsx(O,{label:"Search voices",children:r.jsx(le,{icon:"search",value:vq,onChange:Vq,placeholder:`Search ${Y.length} voices…`})}),'
    s = apply(s, anchor_a1, add_a1, "A1-voice-search-field")

    # ---- PATCH A3: voice dropdown filtered by vq + ▶ preview ----
    anchor_a3 = 'r.jsx(O,{label:"Voice",children:r.jsx(re,{value:ee,options:Y.slice(0,200).map(B=>({value:B.voice_id,label:`${B.name||B.voice_id} ${B.language?`· ${B.language}`:""}`})),onChange:ne})})'
    add_a3 = 'r.jsx(O,{label:"Voice",children:r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center"},children:[r.jsx("div",{style:{flex:1,minWidth:0},children:r.jsx(re,{value:ee,options:Y.filter(B=>{const Z=(vq||"").trim().toLowerCase();return Z?`${B.name||""} ${B.language||""} ${B.voice_id||""}`.toLowerCase().includes(Z):!0}).slice(0,200).map(B=>({value:B.voice_id,label:`${(B.name||B.voice_id).trim()} ${B.language?`· ${B.language}`:""}`})),onChange:ne})}),(()=>{const _v=Y.find(B=>B.voice_id===ee);const _u=_v&&_v.preview_audio;return _u?r.jsx(K,{variant:"outline",size:"sm",icon:"play",title:"Preview voice",onClick:()=>{try{new Audio(_u).play().catch(()=>{})}catch(e){}}}):null})()]})})'
    s = apply(s, anchor_a3, add_a3, "A3-voice-filter-preview")

    BUNDLE.write_text(s, encoding="utf-8")
    print("patched OK")


if __name__ == "__main__":
    main()
