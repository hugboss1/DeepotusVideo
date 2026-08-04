# -*- coding: utf-8 -*-
# scripts/patch_bundle_videomodel.py
"""Assert-guarded patcher : chantier W-a — nœud vidéo multi-modèles.

BASELINE : bundle POST-patch version v1.18.0 (chaîne … → quickvoice →
voicenode → version, cf. mémoire chantier V-b).
Backup dédié : .js.bak_videomodel (état juste avant CE patch).
Plan : docs/superpowers/plans/2026-07-22-modeles-generation-onthefly.md (§1).

Sections :
- V1  props    : registre du nœud Seedance — prop model:"seedance-v1-pro"
                 (défaut inchangé = comportement historique).
- V2  injection: dzVmRates (miroir $/s 1080p + max natif de
                 pricing.py DEFAULTS["video_usd_per_s"] / fal_service
                 VIDEO_MODELS — à changer LÀ-BAS d'abord, puis ici) +
                 dzVmCost(e) + composant DzVideoModelSel (fetch
                 /api/video-models, pattern DzImgModelSel), insérés avant um
                 (point d'injection éprouvé quickvoice/voicenode).
- V3  coût     : Qh — « $0.18 » en dur → durée native clampée × taux modèle.
- V4  panneau  : select « Modèle » en tête du panneau Generator (Studio).
- V5  solo     : payload direct Studio /generate → video_model.
- V6  spatial  : slot seedance (SpatialCompose) → video_model.
- V7  ugc      : slot seedance (branche UGC r_anim) → video_model.
- V8  montage  : slots seedance (branche montage/acts) → video_model.
- V9  quick    : state VMQ (persisté localStorage dz_video_model).
- V10 quick UI : select « Modèle » au-dessus de Duration.
- V11 quick    : payload /generate (solo) → video_model.
- V12 quick    : payload /generate/composition (slot seedance) → video_model.
- V13 topbar   : DzStudioEst — ops seedance + signature re-render au modèle.
- V14-17 pill  : DzQuickEst — prop vm (signature, ops ×2, deps, call site).

Identifiants module-scope vérifiés (V-a/V-b) : r/x (React), re (select
custom), O (champ), Oe (slider), ie (section), Wt (arête amont), Me
(registre nœuds), Qh (coût carte), um (composant Quick).

Run : python scripts/patch_bundle_videomodel.py
Rejouer la chaîne : python scripts/repatch_all.py --from videomodel
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_videomodel")

MARKER = "DzVideoModelSel"


def guard_downstream(bak):
    """Refuse de tourner si un patcher AVAL est déjà passé — voir repatch_all.py."""
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval détecté : {other.name} (plus récent que "
                f"{bak.name}). Utiliser : python scripts/repatch_all.py --from "
                f"{bak.name.rsplit('.bak_', 1)[1]}")


def apply(s, anchor, replacement, tag, want=1):
    n = s.count(anchor)
    if n != want:
        raise SystemExit(f"[{tag}] anchor count={n} (want {want}). Aborting.")
    return s.replace(anchor, replacement)


def js_inject():
    """Code injecté — lignes coupées uniquement après ; , {{ }} ( ) :
    la jointure sans espace est donc sûre (aucune fusion de mots)."""
    block = r"""
var dzVmRates={"seedance-v1-pro":[.124,10],"seedance-2":[.682,15],"seedance-2-fast":[.2419,15],"kling-v3-pro":[.112,15],"kling-v3-standard":[.084,15],"pixverse-v6":[.09,8],"veo-3.1-fast-fal":[.1,8],"veo-3.1-google":[.4,8],"veo-3.1-fast-google":[.15,8],"veo-3.1-lite-google":[.1,8]};
function dzVmCost(e){
var p2=e.props||{},en=dzVmRates[p2.model||"seedance-v1-pro"]||[.04,60],
d2=Math.min(Number(p2.durationS)||10,en[1]);
return"$"+(d2*en[0]).toFixed(2)}
function DzVideoModelSel({value,onChange}){
var ms=x.useState(null),mm=ms[0],setMM=ms[1];
x.useEffect(function(){var on=!0;
fetch("/api/video-models").then(function(r2){return r2.ok?r2.json():null}).then(function(d2){on&&setMM(d2||{models:[]})}).catch(function(){setMM({models:[]})});
return function(){on=!1}},[]);
if(!mm)return null;
function lbl(m2){
var rr=m2.usd_per_s||{},v2=rr["1080p"]!=null?rr["1080p"]:rr["*"],
px=v2!=null?" · $"+(Number(v2)>=.1?Number(v2).toFixed(2):Number(v2).toFixed(3))+"/s":"";
return m2.label+px+(m2.available?"":" · clé manquante")}
var opts=[{value:"",label:"Défaut ("+(mm.default||"seedance-v1-pro")+")"}].concat((mm.models||[]).map(function(m2){return{value:m2.id,label:lbl(m2)}}));
return r.jsx("div",{"data-dzvmsel":"1",children:r.jsx(re,{value:value||"",onChange:onChange,options:opts})})}
"""
    return "".join(line.strip() for line in block.splitlines())


def main():
    if "--force-unchained" not in sys.argv:
        guard_downstream(BAK)
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
        print("restore <-", BAK.name)
    s = BUNDLE.read_text(encoding="utf-8")
    if MARKER in s:
        raise SystemExit(f"[sanity] marqueur {MARKER} déjà présent après restore. Aborting.")

    # V1 — prop model sur le nœud Seedance (défaut = comportement historique).
    a = ('Seedance:{cat:"gen",title:"Seedance",desc:"image → cinematic clip",'
         'inPorts:[{id:"image",type:"image"},{id:"end",type:"image"},'
         '{id:"prompt",type:"text"}],outPorts:[{id:"out",type:"video"}],'
         'props:{style:"cinematic",durationS:10,aspect:"9:16",seed:4421,'
         'extendMode:"loop"}}')
    r = ('Seedance:{cat:"gen",title:"Seedance",desc:"image → cinematic clip",'
         'inPorts:[{id:"image",type:"image"},{id:"end",type:"image"},'
         '{id:"prompt",type:"text"}],outPorts:[{id:"out",type:"video"}],'
         'props:{model:"seedance-v1-pro",style:"cinematic",durationS:10,'
         'aspect:"9:16",seed:4421,extendMode:"loop"}}')
    s = apply(s, a, r, "V1-props")

    # V2 — injection helpers + select avant um (déclarations hoistées).
    a = 'function um({variant:e,activePersona:t}){'
    s = apply(s, a, js_inject() + a, "V2-inject")

    # V3 — coût de carte par modèle (durée native clampée × taux 1080p).
    a = 'e.type==="Seedance"?"$0.18":'
    r = 'e.type==="Seedance"?dzVmCost(e):'
    s = apply(s, a, r, "V3-cout")

    # V4 — select « Modèle » en tête du panneau Generator.
    a = ('e.type==="Seedance"?r.jsxs(ie,{label:"Generator",children:['
         'r.jsx(O,{label:"Style"')
    r = ('e.type==="Seedance"?r.jsxs(ie,{label:"Generator",children:['
         'r.jsx(O,{label:"Modèle",children:r.jsx(DzVideoModelSel,'
         '{value:n.model,onChange:i=>o("model",i)})}),'
         'r.jsx(O,{label:"Style"')
    s = apply(s, a, r, "V4-panel")

    # V5 — payload direct Studio -> /generate (branche solo, nœud h).
    a = 'return D.postJson("/generate",{image_filename:b.props.filename,'
    r = ('return D.postJson("/generate",{video_model:'
         '(h.props&&h.props.model)||void 0,image_filename:b.props.filename,')
    s = apply(s, a, r, "V5-solo")

    # V6 — slot seedance de la composition spatiale (nœud g).
    a = 'return{source_kind:"seedance",seedance:{image_filename:img.props.filename,'
    r = ('return{source_kind:"seedance",seedance:{video_model:'
         '(g.props&&g.props.model)||void 0,image_filename:img.props.filename,')
    s = apply(s, a, r, "V6-spatial")

    # V7 — slot seedance de la branche UGC (r_anim, nœud j).
    a = 'N.anim={source_kind:"seedance",seedance:{image_filename:H.props.filename,'
    r = ('N.anim={source_kind:"seedance",seedance:{video_model:'
         '(j.props&&j.props.model)||void 0,image_filename:H.props.filename,')
    s = apply(s, a, r, "V7-ugc")

    # V8 — slots seedance de la branche montage (acts, nœud j).
    a = 'z[I]={source_kind:"seedance",seedance:{image_filename:H.props.filename,'
    r = ('z[I]={source_kind:"seedance",seedance:{video_model:'
         '(j.props&&j.props.model)||void 0,image_filename:H.props.filename,')
    s = apply(s, a, r, "V8-montage")

    # V9 — Quick : state VMQ, persisté (pattern dz_image_model). Anchor long
    # (la séquence courte `const n=bt(),[o,i]=` existe aussi ailleurs).
    a = ('function um({variant:e,activePersona:t}){var el;'
         'const n=bt(),[o,i]=x.useState')
    r = ('function um({variant:e,activePersona:t}){var el;'
         'const n=bt(),dzvmS=x.useState(function(){try{return '
         'localStorage.getItem("dz_video_model")||""}catch(_e){return""}}),'
         'VMQ=dzvmS[0],dzSetVMQ=dzvmS[1],[o,i]=x.useState')
    s = apply(s, a, r, "V9-quick-state")

    # V10 — Quick : select « Modèle » au-dessus du slider Duration.
    a = ('r.jsx(O,{children:r.jsx(Oe,{label:"Duration",value:h,min:5,max:60,'
         'step:5,unit:"s",onChange:b})}),')
    r = ('r.jsx(O,{label:"Modèle",children:r.jsx(DzVideoModelSel,{value:VMQ,'
         'onChange:function(v2){dzSetVMQ(v2);try{localStorage.setItem('
         '"dz_video_model",v2)}catch(_e){}}})}),' + a)
    s = apply(s, a, r, "V10-quick-ui")

    # V11 — Quick : payload /generate (solo seedance).
    a = 'je={image_filename:w,image_filename_end:g||null,'
    r = 'je={video_model:VMQ||void 0,image_filename:w,image_filename_end:g||null,'
    s = apply(s, a, r, "V11-quick-solo")

    # V12 — Quick : payload /generate/composition (slot seedance).
    a = 'D.postJson("/generate/composition",{seedance:{image_filename:w,custom_prompt:je,'
    r = ('D.postJson("/generate/composition",{seedance:{video_model:'
         'VMQ||void 0,image_filename:w,custom_prompt:je,')
    s = apply(s, a, r, "V12-quick-comp")

    # V13 — topbar Studio (DzStudioEst) : le modèle entre dans l'estimate
    # ET dans la signature (sinon pas de re-render au changement de modèle).
    a = ('else if(T==="Seedance")ops.push({kind:"seedance",'
         'duration_s:Number(n.props&&n.props.durationS)||10});')
    r = ('else if(T==="Seedance")ops.push({kind:"seedance",'
         'duration_s:Number(n.props&&n.props.durationS)||10,'
         'model:(n.props&&n.props.model)||void 0});')
    s = apply(s, a, r, "V13-est-ops")
    a = 'const sig=nodes.map(n=>n.type+":"+((n.props&&n.props.durationS)||"")).join(",");'
    r = ('const sig=nodes.map(n=>n.type+":"+((n.props&&n.props.durationS)||"")'
         '+":"+((n.props&&n.props.model)||"")).join(",");')
    s = apply(s, a, r, "V13-est-sig")

    # V14 — pill Quick (DzQuickEst) : prop vm.
    a = 'function DzQuickEst({mode,dur}){'
    r = 'function DzQuickEst({mode,dur,vm}){'
    s = apply(s, a, r, "V14-quickest-sig")

    # V15 — les DEUX ops seedance du ternaire (comp + solo) portent le modèle.
    a = '{kind:"seedance",duration_s:dur}'
    r = '{kind:"seedance",duration_s:dur,model:vm||void 0}'
    s = apply(s, a, r, "V15-quickest-ops", want=2)

    # V16 — deps du useEffect : re-estimer quand le modèle change.
    a = '},[mode,dur]);const hint='
    r = '},[mode,dur,vm]);const hint='
    s = apply(s, a, r, "V16-quickest-deps")

    # V17 — call site du pill.
    a = 'r.jsx(DzQuickEst,{mode:o,dur:h})'
    r = 'r.jsx(DzQuickEst,{mode:o,dur:h,vm:VMQ})'
    s = apply(s, a, r, "V17-quickest-call")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (videomodel W-a). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
