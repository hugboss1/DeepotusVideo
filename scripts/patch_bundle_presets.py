# scripts/patch_bundle_presets.py
"""Idempotent, assert-guarded patcher for the HeyGen Quick/Studio picker.
Run: python scripts/patch_bundle_presets.py
Creates a .bak once (the pristine bundle), then on every run restores from it so
all patches compose from a clean base. Each patch asserts its anchor occurs
exactly once. The file is written only after ALL patches succeed."""
import pathlib, shutil

from _patch_guard import assert_not_retired

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def main():
    assert_not_retired("patch_bundle_presets", "shared untagged .js.bak; anchors consumed long ago")
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

    # ---- PATCH LOADER: fetch presets on mount into pr + voice matcher ----
    # dzVMatch: substring match first; if nothing matches, fall back to a
    # SUBSEQUENCE match (letters in order) so a near-miss like "xdno" still
    # finds " xdynoMoney - Voice 1" instead of showing an empty dropdown.
    anchor_load = ',[Ce,at]=x.useState(null);'
    add_load = (',[Ce,at]=x.useState(null);'
                'x.useEffect(()=>{let on=!0;fetch("/api/heygen/presets").then(R=>R.ok?R.json():{presets:[]}).then(d=>{if(on)Pr((d&&d.presets)||[])}).catch(()=>{});return()=>{on=!1}},[]);'
                'var dzVMatch=function(q){q=(q||"").trim().toLowerCase();if(!q)return Y;'
                'var K=function(B){return((B.name||"")+" "+(B.language||"")+" "+(B.voice_id||"")).toLowerCase()};'
                'var f=Y.filter(function(B){return K(B).indexOf(q)>=0});if(f.length)return f;'
                'return Y.filter(function(B){var t=K(B),i=0;for(var ci=0;ci<t.length&&i<q.length;ci++){if(t[ci]===q[i])i++}return i>=q.length})};')
    s = apply(s, anchor_load, add_load, "LOADER-quick-presets")

    # ---- PATCH A1: "Search voices" field after "Search avatars" ----
    # Typing AUTO-SELECTS the first match (so the voice name + the play button
    # appear immediately — the search "validates" itself, no extra click).
    anchor_a1 = 'r.jsx(O,{label:"Search avatars",children:r.jsx(le,{icon:"search",value:S,onChange:L,placeholder:`Search ${U.length} avatars…`})}),'
    add_a1 = anchor_a1 + ('r.jsx(O,{label:"Search voices",children:r.jsx(le,{icon:"search",value:vq,'
                          'onChange:function(v){Vq(v);if((v||"").trim()){var f=dzVMatch(v);'
                          'if(f.length&&!f.some(function(z){return z.voice_id===ee}))ne(f[0].voice_id)}},'
                          'placeholder:`Search ${Y.length} voices…`})}),')
    s = apply(s, anchor_a1, add_a1, "A1-voice-search-field")

    # ---- PATCH A3: voice dropdown filtered via dzVMatch + ▶ preview ----
    # The SELECTED voice is always present in the options (prepended with a ✓
    # when the filter/200-cap would hide it) so the closed dropdown never shows
    # "—" for a valid selection. Empty result -> an explanatory option.
    anchor_a3 = 'r.jsx(O,{label:"Voice",children:r.jsx(re,{value:ee,options:Y.slice(0,200).map(B=>({value:B.voice_id,label:`${B.name||B.voice_id} ${B.language?`· ${B.language}`:""}`})),onChange:ne})})'
    add_a3 = ('r.jsx(O,{label:"Voice",children:r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center"},children:['
              'r.jsx("div",{style:{flex:1,minWidth:0},children:r.jsx(re,{value:ee,'
              'options:(function(){var f=dzVMatch(vq).slice(0,200).map(function(B){return{value:B.voice_id,label:((B.name||B.voice_id)+"").trim()+(B.language?" · "+B.language:"")}});'
              'if(ee&&!f.some(function(z){return z.value===ee})){var sv=Y.find(function(B){return B.voice_id===ee});'
              'if(sv)f=[{value:sv.voice_id,label:"✓ "+((sv.name||sv.voice_id)+"").trim()+(sv.language?" · "+sv.language:"")}].concat(f)}'
              'if(!f.length)f=[{value:ee||"",label:(vq||"").trim()?"Aucune voix ne correspond — modifie la recherche":(Y.length?"—":"Loading voices…")}];'
              'return f})(),onChange:ne})}),'
              '(()=>{const _v=Y.find(B=>B.voice_id===ee);const _u=_v&&_v.preview_audio;'
              'return _u?r.jsx(K,{variant:"outline",size:"sm",icon:"play",title:"Preview voice",onClick:()=>{try{new Audio(_u).play().catch(()=>{})}catch(e){}}}):null})()]})})')
    s = apply(s, anchor_a3, add_a3, "A3-voice-filter-preview")

    # ---- PATCH E1 (Quick): casting dropdown + name field + Save/Delete ----
    anchor_e1 = 'r.jsx("input",{ref:et,type:"file",accept:"image/png,image/jpeg,image/webp",style:{display:"none"},onChange:B=>{var Z;dn((Z=B.target.files)==null?void 0:Z[0]),B.target.value=""}}),'
    # Loading a casting clears the voice search (so the loaded voice is visible,
    # not hidden by a stale filter) and confirms via the status line (Ee).
    # Saving confirms too — silent success read as "nothing happened".
    cast_e1 = anchor_e1 + ('r.jsx(O,{label:`Casting (${pr.length})`,children:r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center"},children:['
                           'r.jsx("div",{style:{flex:1,minWidth:0},children:r.jsx(re,{value:"",'
                           'options:[{value:"",label:pr.length?"— load a casting —":"— no casting saved —"},...pr.map(P=>({value:P.id,label:P.name}))],'
                           'onChange:v=>{const P=pr.find(z=>z.id===v);if(P){Q(P.avatar_id);ne(P.voice_id);Vq("");'
                           'Ee("Casting \\u00ab "+P.name+" \\u00bb charg\\u00e9 \\u2713 \\u2014 voix : "+((P.voice_name||"?")+"").trim())}}})}),'
                           'r.jsx(K,{variant:"ghost",size:"sm",icon:"trash",title:"Delete newest casting",disabled:!pr.length,'
                           'onClick:()=>{const P=pr[0];if(P)fetch("/api/heygen/presets/"+P.id,{method:"DELETE"}).then(()=>fetch("/api/heygen/presets").then(R=>R.json()).then(d=>Pr((d&&d.presets)||[])))}})]})}),'
                           'r.jsx(O,{label:"Save current as casting",children:r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center"},children:['
                           'r.jsx("div",{style:{flex:1,minWidth:0},children:r.jsx(le,{value:pn,onChange:Pn,placeholder:"Casting name (e.g. News Reel)"})}),'
                           'r.jsx(K,{variant:"outline",size:"sm",icon:"save",title:"Save casting",disabled:!pn.trim()||!C||!ee,'
                           'onClick:()=>{var nm=pn.trim();const _a=U.find(z=>z.avatar_id===C)||{};const _v=Y.find(z=>z.voice_id===ee)||{};'
                           'fetch("/api/heygen/presets",{method:"POST",headers:{"Content-Type":"application/json"},'
                           'body:JSON.stringify({name:nm,avatar_id:C,avatar_type:_a.avatar_type||"avatar",avatar_img:_a.preview_image_url||"",voice_id:ee,voice_name:(_v.name||"").trim(),voice_prev:_v.preview_audio||"",voice_lang:_v.language||"",speed:1})})'
                           '.then(R=>R.ok?R.json():null).then(function(d){'
                           'Ee(d?("Casting \\u00ab "+nm+" \\u00bb sauvegard\\u00e9 \\u2713 \\u2014 voix : "+(((_v.name||"?")+"").trim())):"Failed to save casting");'
                           'if(d)Pn("");return fetch("/api/heygen/presets").then(R=>R.json()).then(d2=>Pr((d2&&d2.presets)||[]))})}})]})}),')
    s = apply(s, anchor_e1, cast_e1, "E1-quick-casting")

    # ---- PATCH E2a (Studio): load presets in DzAvatarPick ----
    anchor_e2a = 'const[list,setList]=x.useState(null),[voices,setVoices]=x.useState(null);'
    add_e2a = 'const[list,setList]=x.useState(null),[voices,setVoices]=x.useState(null),[presets,setPresets]=x.useState([]);x.useEffect(()=>{let on=!0;fetch("/api/heygen/presets").then(R=>R.ok?R.json():{presets:[]}).then(d=>{if(on)setPresets((d&&d.presets)||[])}).catch(()=>{});return()=>{on=!1}},[]);'
    s = apply(s, anchor_e2a, add_e2a, "E2a-studio-presets-load")

    # ---- PATCH E2b (Studio): casting dropdown wired to set() ----
    anchor_e2b = 'return r.jsxs(ie,{label:"Avatar",children:[r.jsx(O,{label:"Find avatar",'
    add_e2b = 'return r.jsxs(ie,{label:"Avatar",children:[r.jsx(O,{label:`Casting (${presets.length})`,children:r.jsx(re,{value:"",options:[{value:"",label:presets.length?"— load a casting —":"— no casting saved —"},...presets.map(P=>({value:P.id,label:P.name}))],onChange:v=>{const P=presets.find(z=>z.id===v);if(!P)return;set("avatarId",P.avatar_id);set("avatarType",P.avatar_type||"avatar");set("avatarImg",P.avatar_img||"");const _a=(list||[]).find(z=>z.avatar_id===P.avatar_id);if(_a)set("avatar",_a.avatar_name);set("voiceId",P.voice_id);set("voice",P.voice_name||"");set("voicePrev",P.voice_prev||"");set("voiceLang",P.voice_lang||"");set("speedX",P.speed||1)}})}),r.jsx(O,{label:"Find avatar",'
    s = apply(s, anchor_e2b, add_e2b, "E2b-studio-casting")

    BUNDLE.write_text(s, encoding="utf-8")
    print("patched OK")


if __name__ == "__main__":
    main()
