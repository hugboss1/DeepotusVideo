# -*- coding: utf-8 -*-
# scripts/patch_bundle_voicemodel.py
"""Assert-guarded patcher : chantier W-b — modèles + précision ElevenLabs.

BASELINE : bundle POST-patch version v1.19.0 (chaîne … → quickvoice →
voicenode → videomodel → version, cf. mémoire chantier W-a).
Backup dédié : .js.bak_voicemodel (état juste avant CE patch).
Plan : docs/superpowers/plans/2026-07-22-modeles-generation-onthefly.md (§2).

Sections :
- M1  props    : registre du nœud Voiceover — props W-b `model:""` (vide =
                 défaut app ELEVENLABS_MODEL) + `tune:null` (curseurs).
- M2  injection: dzVoMult/dzVoMeta (miroir de pricing.py
                 DEFAULTS["elevenlabs_model_mult"] et
                 elevenlabs_service.ELEVEN_MODELS — à changer LÀ-BAS d'abord,
                 puis ici) + dzVoRate/dzVoCardCost + composants DzVoModelSel
                 (fetch /api/voice-models via Ge, pattern DzVideoModelSel) et
                 DzVoTuning (curseurs Oe par modèle, ↺ = défauts serveur),
                 insérés avant um (point d'injection éprouvé).
- M3  coût     : carte nœud — chars × 0.00024 → chars × tarif du modèle.
- M4  quick    : states dzM/dzT persistés localStorage dz_voice_model /
                 dz_voice_tune (pattern dz_video_model).
- M5-M9 quick  : maxlength par modèle (textarea + compteur + placeholder) et
                 coût estimé × multiplicateur (+ title honnête).
- M10 quick UI : rangée « Modèle » + curseurs sous la rangée Langue.
- M11 quick    : payload /audio/voiceover → model + settings.
- M12-M14 node : mêmes ajouts dans DzVoiceNodePanel (coût, UI, payload) —
                 model/tune vivent dans les props du nœud (persistés graphe).
- M15 picker   : DzVoicePicker — badge [library]/[cloned]… devant le
                 sous-titre pour distinguer les voix non-premade (W-Q4).

Identifiants module-scope réutilisés (V-a/V-b/W-a, vérifiés 22/07) : r/x
(React), Ge (GET+fallback), ie/O/re/K (section, champ, select, bouton), Oe
(slider, props float OK), DzVoicePicker/DzQuickVoice/DzVoiceNodePanel (V-a/
V-b), um (Quick). Réglages non envoyés quand tune vide → défauts persona/app
serveur (clamp + filtre par modèle côté backend, elevenlabs_service).

Run : python scripts/patch_bundle_voicemodel.py
Rejouer la chaîne : python scripts/repatch_all.py --from voicemodel
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_voicemodel")

MARKER = "DzVoModelSel"


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


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def js_inject():
    """Code injecté — lignes coupées uniquement après ; , {{ }} ( ) :
    la jointure sans espace est donc sûre (aucune fusion de mots)."""
    block = r"""
var dzVoMult={"eleven_multilingual_v2":1,"eleven_v3":1,"eleven_flash_v2_5":.5};
var dzVoMeta={"eleven_multilingual_v2":{max:1e4,set:["stability","similarity_boost","style","speed"]},
"eleven_v3":{max:5e3,set:["stability"]},
"eleven_flash_v2_5":{max:4e4,set:["stability","similarity_boost","style","speed"]}};
var DzVoDefModel="eleven_multilingual_v2",DzVoModelsCache=null;
function dzVoM(m){return dzVoMeta[m]||dzVoMeta[DzVoDefModel]}
function dzVoRate(m){return 2.4e-4*(dzVoMult[m]!=null?dzVoMult[m]:1)}
function dzVoCardCost(e){var p2=e.props||{};
return"$"+((p2.chars||0)*dzVoRate(p2.model)).toFixed(4)}
function DzVoModelSel({value:vv,onChange:oc}){
var ms=x.useState(DzVoModelsCache),mm=ms[0],setMM=ms[1];
x.useEffect(function(){var on=!0;
if(DzVoModelsCache){setMM(DzVoModelsCache);
return function(){on=!1}}
Ge("/voice-models",null).then(function(d2){if(!on)return;
DzVoModelsCache=d2||{models:[]};
setMM(DzVoModelsCache)});
return function(){on=!1}},[]);
if(!mm)return null;
function lbl(m2){var px=m2.usd_per_char!=null?" · $"+(Number(m2.usd_per_char)*1e3).toFixed(2)+"/1k":"";
return m2.label+px+(m2.available?"":" · clé manquante")}
var opts=[{value:"",label:"Défaut ("+(mm.default||DzVoDefModel)+")"}].concat((mm.models||[]).map(function(m2){return{value:m2.id,label:lbl(m2)}}));
return r.jsx("div",{"data-dzvomsel":"1",children:r.jsx(re,{value:vv||"",onChange:oc,options:opts})})}
function DzVoTuning({model:md,value:tv,onChange:oc}){
var mt=dzVoM(md),t2=tv||{},v3=mt.set.length===1;
function set2(k2,v2){var n2={};
Object.keys(t2).forEach(function(z){n2[z]=t2[z]});
n2[k2]=Number(v2);
oc(n2)}
function row(k2,lb2,mn,mx,st2,df){if(mt.set.indexOf(k2)<0)return null;
var cur=t2[k2]!=null?Number(t2[k2]):df;
return r.jsx("div",{"data-dzvotune":k2,children:r.jsx(Oe,{label:lb2,value:cur,min:mn,max:mx,step:st2,unit:"",onChange:function(v2){set2(k2,v2)}})},k2)}
var hasT=Object.keys(t2).length>0;
return r.jsxs("div",{"data-dzvotunebox":hasT?"custom":"defaults",style:{display:"flex",flexDirection:"column",gap:6},children:[
row("stability","Stabilité",0,1,v3?.5:.05,v3?.5:.55),
row("similarity_boost","Similarité",0,1,.05,.75),
row("style","Style",0,1,.05,0),
row("speed","Vitesse",.7,1.2,.05,1),
hasT?r.jsx("div",{style:{display:"flex",justifyContent:"flex-end"},children:r.jsx(K,{variant:"ghost",size:"sm","data-dzvotunereset":"1",onClick:function(){oc({})},children:"↺ Défauts"})}):null]})}
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

    # M1 — props du registre : model (vide = défaut app) + tune (curseurs).
    a = ('props:{provider:"elevenlabs",voice_id:"",voice_name:"",'
         'language:"fr",filename:"",chars:0}}')
    r = ('props:{provider:"elevenlabs",voice_id:"",voice_name:"",'
         'language:"fr",filename:"",chars:0,model:"",tune:null}}')
    s = apply(s, a, r, "M1-props")

    # M2 — injection helpers + composants avant um (déclarations hoistées).
    a = 'function um({variant:e,activePersona:t}){'
    s = apply(s, a, js_inject() + a, "M2-inject")

    # M3 — coût de carte du nœud : tarif × multiplicateur du modèle.
    a = 'e.type==="Voiceover"?"$"+((((e.props||{}).chars)||0)*.00024).toFixed(4):'
    r = 'e.type==="Voiceover"?dzVoCardCost(e):'
    s = apply(s, a, r, "M3-carte")

    # M4 — Quick : states modèle + réglages, persistés localStorage.
    a = 'function DzQuickVoice(){'
    r = ('function DzQuickVoice(){'
         'var dzmS=x.useState(function(){try{return localStorage.getItem('
         '"dz_voice_model")||""}catch(_e){return""}}),dzM=dzmS[0],dzSetM=dzmS[1],'
         'dztS=x.useState(function(){try{return JSON.parse(localStorage.getItem('
         '"dz_voice_tune")||"{}")||{}}catch(_e){return{}}}),'
         'dzT=dztS[0],dzSetT=dztS[1];')
    s = apply(s, a, r, "M4-quick-state")

    # M5 — Quick : maxlength du textarea suit le modèle.
    a = 'r.jsx("textarea",{value:txt,maxLength:2500,'
    r = 'r.jsx("textarea",{value:txt,maxLength:dzVoM(dzM).max,'
    s = apply(s, a, r, "M5-maxlen")

    # M6 — Quick : compteur de caractères au plafond du modèle.
    a = 'children:chars+"/2500"'
    r = 'children:chars+"/"+dzVoM(dzM).max'
    s = apply(s, a, r, "M6-compteur")

    # M7 — Quick : coût estimé × multiplicateur du modèle.
    a = 'var cost=chars*0.00024;'
    r = 'var cost=chars*dzVoRate(dzM);'
    s = apply(s, a, r, "M7-cout")

    # M8 — Quick : title du coût aligné sur la nouvelle formule.
    a = 'title:"chars × $0.00024 — aligné sur pricing.py (elevenlabs_usd_per_char)"'
    r = ('title:"chars × tarif du modèle — aligné sur pricing.py '
         '(elevenlabs_usd_per_char × elevenlabs_model_mult)"')
    s = apply(s, a, r, "M8-title")

    # M9 — Quick : placeholder sans le « 2500 » en dur.
    a = ('placeholder:"Texte bref à dire — max 2500 caractères '
         '(narrations longues : flux Chapitres)."')
    r = ('placeholder:"Texte bref à dire — la limite suit le modèle choisi '
         '(narrations longues : flux Chapitres)."')
    s = apply(s, a, r, "M9-placeholder")

    # M10 — Quick : rangée Modèle + curseurs précision sous la rangée Langue.
    a = ('r.jsx(O,{label:"Langue",children:r.jsx(re,{value:lang,'
         'onChange:setLang,options:[{value:"fr",label:"Français"},'
         '{value:"en",label:"Anglais"}]})}),')
    r = (a
         + 'r.jsx(O,{label:"Modèle",children:r.jsx(DzVoModelSel,{value:dzM,'
           'onChange:function(v2){dzSetM(v2);try{localStorage.setItem('
           '"dz_voice_model",v2)}catch(_e){}}})}),'
           'r.jsx(DzVoTuning,{model:dzM,value:dzT,onChange:function(t2){'
           'dzSetT(t2);try{localStorage.setItem("dz_voice_tune",'
           'JSON.stringify(t2))}catch(_e){}}}),')
    s = apply(s, a, r, "M10-quick-ui")

    # M11 — Quick : payload → model + settings (vide = défauts serveur).
    a = ('var d=await D.createVoiceover({script:txt.trim(),language:lang,'
         'voice_id:vid||void 0,name:"quick_vo"});')
    r = ('var d=await D.createVoiceover({script:txt.trim(),language:lang,'
         'voice_id:vid||void 0,model:dzM||void 0,'
         'settings:dzT&&Object.keys(dzT).length?dzT:void 0,'
         'name:"quick_vo"});')
    s = apply(s, a, r, "M11-quick-payload")

    # M12 — nœud : coût estimé × multiplicateur du modèle du nœud.
    a = 'var cost=txt.length*0.00024;'
    r = 'var cost=txt.length*dzVoRate(np.model);'
    s = apply(s, a, r, "M12-node-cout")

    # M13 — nœud : rangée Modèle + curseurs sous la rangée Langue (props).
    a = ('r.jsx(O,{label:"Langue",children:r.jsx(re,{value:lang,'
         'onChange:function(v2){st("language",v2)},'
         'options:[{value:"fr",label:"Français"},'
         '{value:"en",label:"Anglais"}]})}),')
    r = (a
         + 'r.jsx(O,{label:"Modèle",children:r.jsx(DzVoModelSel,'
           '{value:np.model||"",onChange:function(v2){st("model",v2)}})}),'
           'r.jsx(DzVoTuning,{model:np.model||"",value:np.tune||{},'
           'onChange:function(t2){st("tune",t2)}}),')
    s = apply(s, a, r, "M13-node-ui")

    # M14 — nœud : payload → model + settings des props.
    a = ('var d=await D.createVoiceover({script:txt,language:lang,'
         'voice_id:np.voice_id||void 0,name:"studio_vo"});')
    r = ('var d=await D.createVoiceover({script:txt,language:lang,'
         'voice_id:np.voice_id||void 0,model:np.model||void 0,'
         'settings:np.tune&&Object.keys(np.tune).length?np.tune:void 0,'
         'name:"studio_vo"});')
    s = apply(s, a, r, "M14-node-payload")

    # M15 — picker : badge de catégorie devant le sous-titre des voix
    # non-premade (library/community/cloned rouvertes, W-Q4).
    a = ('var sub=[lb.gender,lb.accent,lb.age,lb.description||lb.use_case]'
         '.filter(Boolean).join(" · ");')
    r = ('var sub=[v.category&&v.category!=="premade"?"["+v.category+"]":null,'
         'lb.gender,lb.accent,lb.age,lb.description||lb.use_case]'
         '.filter(Boolean).join(" · ");')
    s = apply(s, a, r, "M15-picker-badge")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (voicemodel W-b). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
