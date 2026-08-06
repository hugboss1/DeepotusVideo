# scripts/patch_bundle_concat.py
"""Assert-guarded patcher: let a Studio Concatenate node accept non-Seedance
video sources (Existing render / Upload), not only Seedance.

Root cause of the bug: the graph compiler pushed only type==="Seedance" nodes
into the montage, so a Concatenate fed by "Existing render" clips errored with
"needs at least 2 Seedance clips" even when 3 were wired. The backend montage
renderer already supports source_kind job/upload/file, so this is frontend-only.

Run: python scripts/patch_bundle_concat.py
Creates a .bak once (pristine bundle); on re-run restores from it so patches
compose from a clean base. Writes the file only after all patches succeed."""
import pathlib, shutil

from _patch_guard import assert_not_retired

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def main():
    assert_not_retired("patch_bundle_concat", "shared untagged .js.bak; anchors consumed long ago")
    bak = BUNDLE.with_suffix(".js.bak")
    if not bak.exists():
        shutil.copy2(BUNDLE, bak)
        print("backup ->", bak)
    else:
        shutil.copy2(bak, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")

    # CONCAT-1: broaden the source-type filter + error message.
    anchor_c1 = 'for(const j of["a","b","c","d","e","f"]){const E=Wt(e,a.id,j);E&&E.type==="Seedance"&&h.push(E)}if(h.length<2)return{ok:!1,error:"Concatenate needs at least 2 Seedance clips connected."};'
    add_c1 = 'for(const j of["a","b","c","d","e","f"]){const E=Wt(e,a.id,j);E&&["Seedance","ExistingRender","Upload"].includes(E.type)&&h.push(E)}if(h.length<2)return{ok:!1,error:"Concatenate needs at least 2 video sources connected (Seedance, Existing render or Upload)."};'
    s = apply(s, anchor_c1, add_c1, "CONCAT-1-source-filter")

    # CONCAT-2: build slot payload per source type (seedance vs job/upload).
    # Existing render / Upload play their full real duration (length_mode source)
    # with their own audio preserved (audio_volume:1).
    anchor_c2 = 'const[b,_]=pd(n),z={},N=h.map((j,E)=>{var V,M,U,T,Y,q;const H=Wt(e,j.id,"image");if(!H||(H.type!=="Image"&&H.type!=="NewsIllustration")||!((V=H.props)!=null&&V.filename))throw new Error(`Seedance #${E+1} needs an Image node connected.`);const F=Wt(e,j.id,"prompt"),I="clip"+E,A=Number((M=j.props)==null?void 0:M.durationS)||5;return z[I]={source_kind:"seedance",seedance:{image_filename:H.props.filename,custom_prompt:((U=F==null?void 0:F.props)==null?void 0:U.value)||"cinematic motion, deep-sea bioluminescence",duration_s:A,extend_mode:((T=j.props)==null?void 0:T.extendMode)||"loop",voiceover_enabled:!1}},{id:"r"+E,type:"video_slot",act:E,x:0,y:0,width:b,height:_,slot_name:I,length_s:A,length_mode:"fixed",transition:E?{type:((Y=a.props)==null?void 0:Y.transition)||"crossfade",duration_s:Number((q=a.props)==null?void 0:q.durationS)||.4}:{type:"cut"}}}),'
    add_c2 = 'const[b,_]=pd(n),z={},N=h.map((j,E)=>{const I="clip"+E;const tr=E?{type:(a.props&&a.props.transition)||"crossfade",duration_s:Number(a.props&&a.props.durationS)||.4}:{type:"cut"};if(j.type==="Seedance"){const H=Wt(e,j.id,"image");if(!H||(H.type!=="Image"&&H.type!=="NewsIllustration")||!(H.props&&H.props.filename))throw new Error(`Seedance #${E+1} needs an Image node connected.`);const F=Wt(e,j.id,"prompt"),A=Number(j.props&&j.props.durationS)||5;z[I]={source_kind:"seedance",seedance:{image_filename:H.props.filename,custom_prompt:(F&&F.props&&F.props.value)||"cinematic motion, deep-sea bioluminescence",duration_s:A,extend_mode:(j.props&&j.props.extendMode)||"loop",voiceover_enabled:!1}};return{id:"r"+E,type:"video_slot",act:E,x:0,y:0,width:b,height:_,slot_name:I,length_s:A,length_mode:"fixed",transition:tr}}const jid=j.props&&j.props.jobId,fn=j.props&&j.props.filename;if(jid)z[I]={source_kind:"job",job_id:jid};else if(fn)z[I]={source_kind:"upload",upload_filename:fn};else throw new Error(`Source #${E+1} (${j.type}) is empty — pick a render/file in its inspector.`);return{id:"r"+E,type:"video_slot",act:E,x:0,y:0,width:b,height:_,slot_name:I,length_s:0,length_mode:"source",audio_volume:1,transition:tr}}),'
    s = apply(s, anchor_c2, add_c2, "CONCAT-2-slot-payload")

    BUNDLE.write_text(s, encoding="utf-8")
    print("patched OK")


if __name__ == "__main__":
    main()
