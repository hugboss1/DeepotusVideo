# scripts/patch_bundle_engine.py
"""Assert-guarded patcher: HeyGen rendering-engine choice (Avatar III/IV/V, API
v3) in Quick + the Studio HeyGen node + casting presets.

BASELINE: unlike the earlier patchers (which patched the pristine 1.15.8
bundle), this one patches the POST-#1/#2/#4 bundle from main (md5 c0aabe64…) —
several anchors below target strings those patches introduced. It therefore
keeps its own backup file (.js.bak_engine), separate from the historical
.js.bak (pristine).

"" / no engine selected => the legacy v2 pipeline, unchanged.

Run: python scripts/patch_bundle_engine.py
"""
import pathlib, shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_engine")

ENGINE_OPTS = ('[{value:"",label:"Auto (pipeline actuel)"},'
               '{value:"avatar_iii",label:"Avatar III"},'
               '{value:"avatar_iv",label:"Avatar IV \\u00b7 motion"},'
               '{value:"avatar_v",label:"Avatar V \\u00b7 max"}]')


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

    # E-1: Quick state — engine hook next to the other picker hooks.
    a = '[S,L]=x.useState(""),[vq,Vq]=x.useState(""),[pr,Pr]=x.useState([]),[pn,Pn]=x.useState(""),[J,de]=x.useState(!1)'
    r = '[S,L]=x.useState(""),[vq,Vq]=x.useState(""),[pr,Pr]=x.useState([]),[pn,Pn]=x.useState(""),[eng,Eng]=x.useState(""),[J,de]=x.useState(!1)'
    s = apply(s, a, r, "E1-quick-state")

    # E-2: Quick "Moteur" select right after the voice row (anchored on the
    # ▶ preview tail added by the presets patch — `_u` is unique to it).
    a = '"Preview voice",onClick:()=>{try{new Audio(_u).play().catch(()=>{})}catch(e){}}}):null})()]})})'
    r = a + (',r.jsx(O,{label:"Moteur HeyGen",hint:"Auto = pipeline actuel. III/IV/V = API v3 par requ\\u00eate.",'
             'children:r.jsx(re,{value:eng,onChange:Eng,options:' + ENGINE_OPTS + '})})')
    s = apply(s, a, r, "E2-quick-engine-select")

    # E-3: Quick direct HeyGen generation body.
    a = 'Z=await D.postJson("/generate/heygen",{avatar_id:C,voice_id:ee,script:R.trim(),avatar_type:(B==null?void 0:B.avatar_type)||"avatar",aspect_ratio:_,speed:1})'
    r = 'Z=await D.postJson("/generate/heygen",{avatar_id:C,voice_id:ee,script:R.trim(),avatar_type:(B==null?void 0:B.avatar_type)||"avatar",aspect_ratio:_,speed:1,engine:eng||void 0})'
    s = apply(s, a, r, "E3-quick-generate-body")

    # E-3b: Quick composition-mode HeyGen side.
    a = 'avatar_type:(B==null?void 0:B.avatar_type)||"avatar",aspect_ratio:_,speed:1},layout:We'
    r = 'avatar_type:(B==null?void 0:B.avatar_type)||"avatar",aspect_ratio:_,speed:1,engine:eng||void 0},layout:We'
    s = apply(s, a, r, "E3b-comp-heygen-body")

    # E-4: casting save body carries the engine.
    a = 'voice_prev:_v.preview_audio||"",voice_lang:_v.language||"",speed:1})'
    r = 'voice_prev:_v.preview_audio||"",voice_lang:_v.language||"",speed:1,engine:eng||""})'
    s = apply(s, a, r, "E4-casting-save-engine")

    # E-5: casting load applies the engine (Quick).
    a = 'if(P){Q(P.avatar_id);ne(P.voice_id);Vq("");'
    r = 'if(P){Q(P.avatar_id);ne(P.voice_id);Vq("");Eng(P.engine||"");'
    s = apply(s, a, r, "E5-casting-load-engine")

    # E-6: Studio node — "Moteur" select above Speed in DzAvatarPick.
    a = 'r.jsx(O,{label:"Speed",children:r.jsx(Oe,{value:p.speedX*100|0'
    r = ('r.jsx(O,{label:"Moteur",children:r.jsx(re,{value:p.engine||"",onChange:v=>set("engine",v),options:'
         + ENGINE_OPTS + '})}),' + a)
    s = apply(s, a, r, "E6-studio-engine-select")

    # E-7: Studio casting load applies the engine to the node.
    a = 'set("voiceLang",P.voice_lang||"");set("speedX",P.speed||1)'
    r = 'set("voiceLang",P.voice_lang||"");set("speedX",P.speed||1);set("engine",P.engine||"")'
    s = apply(s, a, r, "E7-studio-casting-engine")

    # E-8: Studio run compiler passes the node's engine.
    a = 'D.postJson("/generate/heygen",{avatar_id:aid,voice_id:vid,script:b.slice(0,4900),avatar_type:atype,aspect_ratio:n,speed:Number(s.props&&s.props.speedX)||1,source_graph:e})'
    r = 'D.postJson("/generate/heygen",{avatar_id:aid,voice_id:vid,script:b.slice(0,4900),avatar_type:atype,aspect_ratio:n,speed:Number(s.props&&s.props.speedX)||1,engine:(s.props&&s.props.engine)||void 0,source_graph:e})'
    s = apply(s, a, r, "E8-compiler-engine")

    BUNDLE.write_text(s, encoding="utf-8")
    print("patched OK")


if __name__ == "__main__":
    main()
