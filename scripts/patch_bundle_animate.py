# scripts/patch_bundle_animate.py
"""Assert-guarded patcher (feature D): animate a Library image + cinematic mode
on the Quick page's HeyGen generator.

BASELINE: the ENGINE-patched bundle (run scripts/patch_bundle_engine.py first —
several anchors below target strings it introduced). Own backup file
(.js.bak_animate).

Adds a "Source" toggle to Quick's HeyGen mode:
- Avatar HeyGen         -> existing flow (untouched)
- Image animée          -> Library image + motion prompt + expressivité,
                           POST /generate/heygen-image (v3 type=image)
- Cinématique           -> the Script box becomes the cinematic prompt; the
                           selected avatar is the look; optional reference
                           image; duration clamped 4–15 s,
                           POST /generate/heygen-cinematic
Castings support avatar_type "image" (saved/loaded from Quick; filtered out of
the Studio node's casting list, which can't render an image source yet).

Run: python scripts/patch_bundle_animate.py
"""
import pathlib, shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_animate")

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

    # D-1: Quick state — source kind + image + motion prompt + expressiveness.
    a = '[pn,Pn]=x.useState(""),[eng,Eng]=x.useState(""),[J,de]=x.useState(!1)'
    r = ('[pn,Pn]=x.useState(""),[eng,Eng]=x.useState(""),'
         '[hsrc,Hsrc]=x.useState("avatar"),[mimg,Mimg]=x.useState(""),'
         '[mp,Mp]=x.useState(""),[xp,Xp]=x.useState(""),[J,de]=x.useState(!1)')
    s = apply(s, a, r, "D1-quick-state")

    # D-2: "Source" toggle at the top of the Avatar section (heygen mode only).
    a = 'children:[r.jsx("input",{ref:et,type:"file"'
    r = ('children:[o==="heygen"&&r.jsx(O,{label:"Source",children:r.jsx(re,{value:hsrc,onChange:Hsrc,'
         'options:[{value:"avatar",label:"Avatar HeyGen"},'
         '{value:"image",label:"Image anim\\u00e9e (photo\\u2192vid\\u00e9o)"},'
         '{value:"cinematic",label:"Cin\\u00e9matique (le Script = prompt)"}]})}),'
         'r.jsx("input",{ref:et,type:"file"')
    s = apply(s, a, r, "D2-source-toggle")

    # D-3: image/cinematic panel after the "Moteur HeyGen" field.
    a = ('r.jsx(O,{label:"Moteur HeyGen",hint:"Auto = pipeline actuel. III/IV/V = API v3 par requ\\u00eate.",'
         'children:r.jsx(re,{value:eng,onChange:Eng,options:' + ENGINE_OPTS + '})})')
    r = a + (',(hsrc==="image"||hsrc==="cinematic")&&o==="heygen"&&r.jsxs(O,'
             '{label:hsrc==="image"?"Image \\u00e0 animer":"Image de r\\u00e9f\\u00e9rence (optionnel)",children:['
             'r.jsx(re,{value:mimg,options:[{value:"",label:"\\u2014 choisir dans la Library \\u2014"},'
             '...u.map(f2=>({value:f2,label:f2}))],onChange:Mimg}),'
             'mimg?r.jsx("img",{src:D.imageUrl(mimg),'
             'onLoad:e2=>{e2.currentTarget.style.opacity=1},onError:e2=>{e2.currentTarget.style.opacity=0},'
             'style:{marginTop:6,width:"100%",maxHeight:160,objectFit:"cover",borderRadius:8,border:"1px solid var(--stroke)"}}):null]}),'
             'hsrc==="image"&&o==="heygen"&&r.jsx(O,{label:"Motion prompt (gestes, expressions)",'
             'children:r.jsx("textarea",{value:mp,onChange:e2=>Mp(e2.target.value),rows:2,'
             'placeholder:"ex: sourit, hoche la t\\u00eate, gestes calmes de la main",'
             'style:{width:"100%",padding:8,background:"var(--bg-base)",border:"1px solid var(--stroke)",'
             'borderRadius:8,color:"var(--ink-strong)",fontFamily:"var(--f-ui)",fontSize:12,resize:"vertical"}})}),'
             'hsrc==="image"&&o==="heygen"&&r.jsx(O,{label:"Expressivit\\u00e9",'
             'children:r.jsx(re,{value:xp,onChange:Xp,options:[{value:"",label:"Auto"},'
             '{value:"low",label:"Low"},{value:"medium",label:"Medium"},{value:"high",label:"High"}]})})')
    s = apply(s, a, r, "D3-image-cinematic-panel")

    # D-4: submit branch — route by source kind.
    a = ('else if(o==="heygen"){if(!C||!ee){at({error:"Pick avatar + voice."});return}'
         'if(!R.trim()){at({error:"Empty script."});return}'
         'const B=U.find(fe=>fe.avatar_id===C),'
         'Z=await D.postJson("/generate/heygen",{avatar_id:C,voice_id:ee,script:R.trim(),'
         'avatar_type:(B==null?void 0:B.avatar_type)||"avatar",aspect_ratio:_,speed:1,engine:eng||void 0});'
         'at(Z.ok?{msg:"HeyGen queued."}:{error:Z.error})}')
    r = ('else if(o==="heygen"){'
         'if(hsrc==="image"){'
         'if(!mimg){at({error:"Choisis une image de la Library \\u00e0 animer."});return}'
         'if(!ee){at({error:"Pick a voice."});return}'
         'if(!R.trim()){at({error:"Empty script."});return}'
         'const Z2=await D.postJson("/generate/heygen-image",{image_filename:mimg,script:R.trim(),voice_id:ee,'
         'engine:eng==="avatar_v"?"avatar_v":"avatar_iv",motion_prompt:mp||void 0,'
         'expressiveness:xp||void 0,aspect_ratio:_});'
         'at(Z2.ok?{msg:"Image animation queued."}:{error:Z2.error})'
         '}else if(hsrc==="cinematic"){'
         'if(!C){at({error:"Choisis un avatar (look) pour le mode cin\\u00e9matique."});return}'
         'if(!R.trim()){at({error:"\\u00c9cris le prompt cin\\u00e9matique dans le champ Script."});return}'
         'const Z2=await D.postJson("/generate/heygen-cinematic",{prompt:R.trim(),look_ids:[C],'
         'reference_images:mimg?[mimg]:[],duration_s:Math.max(4,Math.min(15,h)),'
         'aspect_ratio:(_==="16:9"||_==="1:1")?_:"9:16"});'
         'at(Z2.ok?{msg:"Cinematic queued."}:{error:Z2.error})'
         '}else{'
         'if(!C||!ee){at({error:"Pick avatar + voice."});return}'
         'if(!R.trim()){at({error:"Empty script."});return}'
         'const B=U.find(fe=>fe.avatar_id===C),'
         'Z=await D.postJson("/generate/heygen",{avatar_id:C,voice_id:ee,script:R.trim(),'
         'avatar_type:(B==null?void 0:B.avatar_type)||"avatar",aspect_ratio:_,speed:1,engine:eng||void 0});'
         'at(Z.ok?{msg:"HeyGen queued."}:{error:Z.error})}}')
    s = apply(s, a, r, "D4-submit-branch")

    # D-5a: casting save — enabled with an image source too.
    a = 'disabled:!pn.trim()||!C||!ee,onClick:()=>{var nm=pn.trim();'
    r = 'disabled:!pn.trim()||!ee||(hsrc==="image"?!mimg:!C),onClick:()=>{var nm=pn.trim();'
    s = apply(s, a, r, "D5a-save-disabled")

    # D-5b: casting save body — image castings store the filename.
    a = ('body:JSON.stringify({name:nm,avatar_id:C,avatar_type:_a.avatar_type||"avatar",'
         'avatar_img:_a.preview_image_url||"",voice_id:ee,')
    r = ('body:JSON.stringify({name:nm,avatar_id:hsrc==="image"?mimg:C,'
         'avatar_type:hsrc==="image"?"image":(_a.avatar_type||"avatar"),'
         'avatar_img:hsrc==="image"?("/api/images/"+mimg):(_a.preview_image_url||""),voice_id:ee,')
    s = apply(s, a, r, "D5b-save-body")

    # D-6: casting load — image castings restore the image source mode.
    a = 'if(P){Q(P.avatar_id);ne(P.voice_id);Vq("");Eng(P.engine||"");'
    r = ('if(P){if(P.avatar_type==="image"){Hsrc("image");Mimg(P.avatar_id)}'
         'else{Hsrc("avatar");Q(P.avatar_id)}ne(P.voice_id);Vq("");Eng(P.engine||"");')
    s = apply(s, a, r, "D6-load-image-casting")

    # D-7: Studio node casting list — hide image castings (the node cannot
    # render an image source yet; Studio support is a follow-up).
    a = ('options:[{value:"",label:presets.length?"— load a casting —":"— no casting saved —"},'
         '...presets.map(P=>({value:P.id,label:P.name}))]')
    r = ('options:[{value:"",label:presets.length?"— load a casting —":"— no casting saved —"},'
         '...presets.filter(z2=>z2.avatar_type!=="image").map(P=>({value:P.id,label:P.name}))]')
    s = apply(s, a, r, "D7-studio-filter-image")

    BUNDLE.write_text(s, encoding="utf-8")
    print("patched OK")


if __name__ == "__main__":
    main()
