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

    BUNDLE.write_text(s, encoding="utf-8")
    print("patched OK")


if __name__ == "__main__":
    main()
