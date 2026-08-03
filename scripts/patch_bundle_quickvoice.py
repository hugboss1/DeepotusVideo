# -*- coding: utf-8 -*-
# scripts/patch_bundle_quickvoice.py
"""Assert-guarded patcher : chantier V-a — onglet Quick « Voice Over ».

BASELINE : bundle POST-patch version (release v1.16.0, chantier 11 complet).
Backup dédié : .js.bak_quickvoice (état juste avant CE patch).
Spec : docs/superpowers/specs/2026-07-22-voiceover-quick-studio-design.md (§5).

Sections :
- S1 deep-link : "voice" accepté par l'init du mode (?mode=voice).
- S2 onglet    : tuple ["voice","Voice Over","wave",!1] dans la rangée
                 d'onglets Quick (jamais désactivé : la garde fournisseur
                 est DANS le panneau, pas sur l'onglet).
- S3 bascule   : le conteneur scrollable du formulaire rend DzQuickVoice
                 seul quand o==="voice" (aucun early-return dans um :
                 l'ordre des hooks est intact).
- S5 footer    : le footer natif (Est. cost + Generate + warnings), SIBLING
                 du conteneur scroll (constat smoke 22/07), est masqué en
                 mode voice — le panneau a son propre Générer sticky.
- S4 injection : composants top-level DzVoicePicker + DzQuickVoice insérés
                 avant function um. Identifiants module-scope réutilisés
                 (vérifiés uniques le 22/07) : r/x (React), D (façade API :
                 listVoices, createVoiceover), Ge (GET+fallback), Te (base
                 API), ie/O/re/K (sections, champ, select, bouton — K
                 propage ...rest vers le DOM, d'où les data-dz* de QA).

Coût affiché : chars × 0.00024 $ — MÊME constante que
backend/app/services/pricing.py (elevenlabs_usd_per_char) ; à changer LÀ-BAS
d'abord si le tarif bouge, puis ici.

Préécoute : new Audio(preview_url) singleton module (DzVoAudio) — jouer une
voix stoppe la précédente ; AUCUN appel de génération.
Castings : atelier_settings.voice_castings, valeur = CHAÎNE JSON
(PUT stringifie str(v) côté serveur — jamais envoyer un objet).

Run : python scripts/patch_bundle_quickvoice.py
Rejouer la chaîne : python scripts/repatch_all.py --from quickvoice
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_quickvoice")

MARKER = "DzQuickVoice"


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
    """Composants injectés — lignes coupées uniquement après ; , {{ }} ( ) :
    la jointure sans espace est donc sûre (aucune fusion de mots)."""
    block = r"""
var DzVoicesCache=null,DzVoAudio=null,DzVoAudioKey=null;
function DzVoStopPreview(){if(DzVoAudio){try{DzVoAudio.pause()}catch(_e){}}DzVoAudio=null;DzVoAudioKey=null}
function DzVoicePicker({value:vSel,onChange:onPick}){
const sv1=x.useState(DzVoicesCache),vcs=sv1[0],setVcs=sv1[1],
sv2=x.useState(""),vq=sv2[0],setVq=sv2[1],
sv3=x.useState(null),vpl=sv3[0],setVpl=sv3[1],
sv4=x.useState(!DzVoicesCache),vld=sv4[0],setVld=sv4[1];
function vload(){setVld(!0);D.listVoices().then(function(d){var v=(d&&d.voices)||[];DzVoicesCache=v;setVcs(v);setVld(!1)})}
x.useEffect(function(){DzVoicesCache?setVcs(DzVoicesCache):vload();return function(){DzVoStopPreview()}},[]);
function vtoggle(vk,pv){if(DzVoAudioKey===vk){DzVoStopPreview();setVpl(null);return}DzVoStopPreview();setVpl(null);if(!pv)return;var a=new Audio(pv);DzVoAudio=a;DzVoAudioKey=vk;setVpl(vk);a.onended=function(){if(DzVoAudioKey===vk){DzVoStopPreview();setVpl(null)}};a.play().catch(function(){if(DzVoAudioKey===vk){DzVoStopPreview();setVpl(null)}})}
var vlist=(vcs||[]).filter(function(v){var s2=(vq||"").trim().toLowerCase();if(!s2)return!0;var lb=v.labels||{};var hay=(v.name||"")+" "+Object.keys(lb).map(function(k2){return String(lb[k2]||"")}).join(" ");return hay.toLowerCase().indexOf(s2)>=0});
function vcard(sel,nm,sub,pv,vk,onSel){return r.jsxs("div",{onClick:onSel,"data-dzvoice":vk||"default","data-dzsel":sel?"1":"0",style:{display:"flex",alignItems:"center",gap:8,padding:"7px 9px",background:sel?"var(--bg-panel-2)":"var(--bg-base)",border:sel?"1px solid var(--brand)":"1px solid var(--stroke)",borderRadius:"var(--r-sm)",cursor:"pointer",flex:"0 0 auto"},children:[
r.jsxs("div",{style:{flex:1,minWidth:0},children:[
r.jsx("div",{style:{fontSize:12,color:"var(--ink-strong)",fontWeight:sel?600:400,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},children:nm}),
sub?r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},children:sub}):null]}),
vk?r.jsx("button",{title:pv?"Préécouter":"Pas d'échantillon",disabled:!pv,"data-dzplay":vk,onClick:function(ev){ev.stopPropagation();vtoggle(vk,pv)},style:{width:26,height:26,flex:"0 0 auto",background:"var(--bg-base)",border:"1px solid var(--stroke-strong)",borderRadius:"var(--r-sm)",color:pv?"var(--ink-soft)":"var(--ink-muted)",cursor:pv?"pointer":"not-allowed",fontSize:10,lineHeight:"1"},children:vpl===vk?"■":"▶"}):null]},vk||"default")}
return r.jsxs("div",{children:[
r.jsxs("div",{style:{display:"flex",gap:6,marginBottom:6},children:[
r.jsx("input",{value:vq,onChange:function(ev){setVq(ev.target.value)},placeholder:"Filtrer les voix…","data-dzvoicefilter":"1",style:{flex:1,height:26,padding:"0 8px",background:"var(--bg-base)",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",color:"var(--ink)",fontSize:11.5,outline:"none"}}),
r.jsx("button",{title:"Recharger le catalogue",onClick:vload,"data-dzvoicereload":"1",style:{width:26,height:26,background:"var(--bg-base)",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",color:"var(--ink-soft)",cursor:"pointer",fontSize:12,lineHeight:"1"},children:"↻"})]}),
r.jsxs("div",{className:"scroll","data-dzvoicelist":"1",style:{maxHeight:240,overflowY:"auto",display:"flex",flexDirection:"column",gap:6},children:[
vcard(!vSel,"Voix par défaut de l'app","ELEVENLABS_VOICE_ID du .env selon la langue",null,"",function(){onPick("","Voix par défaut de l'app")}),
vld?r.jsx("div",{style:{fontSize:11,color:"var(--ink-muted)",padding:6},children:"Chargement des voix…"}):null,
!vld&&!vlist.length?r.jsx("div",{style:{fontSize:11,color:"var(--ink-muted)",padding:6},children:vcs&&vcs.length?"Aucune voix ne correspond au filtre.":"Aucune voix — vérifie la clé ElevenLabs (Réglages)."}):null,
vlist.map(function(v){var lb=v.labels||{};var sub=[lb.gender,lb.accent,lb.age,lb.description||lb.use_case].filter(Boolean).join(" · ");return vcard(vSel===v.voice_id,v.name||v.voice_id,sub,v.preview_url,v.voice_id,function(){onPick(v.voice_id,v.name||v.voice_id)})})]})]})}
function DzQuickVoice(){
const q1=x.useState(void 0),prov=q1[0],setProv=q1[1],
q2=x.useState(""),txt=q2[0],setTxt=q2[1],
q3=x.useState("fr"),lang=q3[0],setLang=q3[1],
q4=x.useState(""),vid=q4[0],setVid=q4[1],
q5=x.useState("Voix par défaut de l'app"),vnm=q5[0],setVnm=q5[1],
q6=x.useState(!1),busy=q6[0],setBusy=q6[1],
q7=x.useState(null),res=q7[0],setRes=q7[1],
q8=x.useState([]),casts=q8[0],setCasts=q8[1],
q9=x.useState(""),castSel=q9[0],setCastSel=q9[1],
qa=x.useState(!1),nmOpen=qa[0],setNmOpen=qa[1],
qb=x.useState(""),castNm=qb[0],setCastNm=qb[1],
qc=x.useState(!1),saving=qc[0],setSaving=qc[1];
x.useEffect(function(){var on=!0;
Ge("/voice/providers",null).then(function(v){on&&setProv(v||{resolved:null})});
Ge("/atelier/settings",null).then(function(d){if(!on)return;var raw=d&&d.settings&&d.settings.voice_castings;if(!raw)return;try{var j=JSON.parse(raw);Array.isArray(j)&&setCasts(j)}catch(_e){}});
return function(){on=!1}},[]);
var resolved=prov===void 0?"loading":(prov&&prov.resolved)||null;
var okProv=resolved==="elevenlabs";
var chars=txt.length;
var cost=chars*0.00024;
async function gen(){if(!txt.trim()||busy)return;setBusy(!0);setRes(null);try{var d=await D.createVoiceover({script:txt.trim(),language:lang,voice_id:vid||void 0,name:"quick_vo"});setBusy(!1);d&&d.ok?setRes({filename:d.filename,url:d.url,kb:d.size_kb}):setRes({error:(d&&d.error)||"Échec de la génération."})}catch(err){setBusy(!1);setRes({error:String((err&&err.message)||err)})}}
async function putCasts(next){setSaving(!0);var ok=!1;try{var rp=await fetch(Te+"/atelier/settings",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({voice_castings:JSON.stringify(next)})});ok=!!(rp&&rp.ok)}catch(_e){}setSaving(!1);if(ok)setCasts(next);return ok}
async function saveCast(){var nm=castNm.trim();if(!nm)return;var it={name:nm,provider:"elevenlabs",voice_id:vid,voice_name:vnm,language:lang};var ok=await putCasts(casts.filter(function(c2){return c2&&c2.name!==nm}).concat([it]));if(ok){setCastSel(nm);setNmOpen(!1);setCastNm("")}}
async function delCast(){if(!castSel)return;var ok=await putCasts(casts.filter(function(c2){return!(c2&&c2.name===castSel)}));if(ok)setCastSel("")}
function applyCast(nm){setCastSel(nm);if(!nm)return;var c2=casts.find(function(z){return z&&z.name===nm});if(!c2)return;setVid(c2.voice_id||"");setVnm(c2.voice_name||"Voix par défaut de l'app");if(c2.language==="fr"||c2.language==="en")setLang(c2.language)}
var guard=resolved==="loading"?r.jsx("div",{style:{fontSize:11,color:"var(--ink-muted)"},children:"Fournisseur de voix…"}):okProv?r.jsxs("div",{"data-dzprov":"elevenlabs",style:{display:"inline-flex",alignItems:"center",gap:6,padding:"3px 9px",background:"var(--bg-panel-2)",border:"1px solid var(--stroke)",borderRadius:999,fontSize:10.5,color:"var(--ink-soft)"},children:[
r.jsx("span",{style:{width:7,height:7,borderRadius:99,background:"var(--green)",display:"inline-block"}}),
"ElevenLabs"]}):resolved==="voicebox"?r.jsxs("div",{"data-dzprov":"voicebox",style:{padding:8,background:"var(--amber-soft)",border:"1px solid var(--amber)",borderRadius:"var(--r-sm)",fontSize:11,color:"var(--ink)"},children:[
r.jsx("strong",{style:{color:"var(--amber)"},children:"v1 gère ElevenLabs seul"}),
" — change le Fournisseur de voix dans Réglages pour générer ici."]}):r.jsxs("div",{"data-dzprov":"none",style:{padding:8,background:"var(--red-soft)",border:"1px solid var(--red)",borderRadius:"var(--r-sm)",fontSize:11,color:"var(--ink)"},children:[
r.jsx("strong",{style:{color:"var(--red)"},children:"Clé ElevenLabs manquante"}),
" — ajoute-la dans Réglages → Clés."]});
var dis=prov!==void 0&&!okProv&&resolved!=="voicebox";
return r.jsxs("div",{"data-dzquickvoice":"1",children:[
r.jsx("div",{style:{padding:"10px 14px 8px"},children:guard}),
r.jsxs("div",{style:dis?{opacity:.55,pointerEvents:"none"}:void 0,children:[
r.jsxs(ie,{label:"Script",children:[
r.jsx("textarea",{value:txt,maxLength:2500,onChange:function(ev){setTxt(ev.target.value)},placeholder:"Texte bref à dire — max 2500 caractères (narrations longues : flux Chapitres).","data-dztext":"1",style:{width:"100%",minHeight:110,background:"var(--bg-base)",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",color:"var(--ink)",padding:8,fontSize:12.5,resize:"vertical",outline:"none",boxSizing:"border-box"}}),
r.jsxs("div",{style:{display:"flex",justifyContent:"space-between",marginTop:4,fontSize:10.5,color:"var(--ink-muted)"},children:[
r.jsx("span",{"data-dzchars":"1",children:chars+"/2500"}),
r.jsx("span",{"data-dzcost":"1",title:"chars × $0.00024 — aligné sur pricing.py (elevenlabs_usd_per_char)",children:"~$"+cost.toFixed(4)})]})]}),
r.jsxs(ie,{label:"Voix",children:[
r.jsx(O,{label:"Langue",children:r.jsx(re,{value:lang,onChange:setLang,options:[{value:"fr",label:"Français"},{value:"en",label:"Anglais"}]})}),
r.jsx(DzVoicePicker,{value:vid,onChange:function(v2,n2){setVid(v2);setVnm(n2)}}),
r.jsxs("div",{"data-dzcastrow":"1",style:{display:"flex",gap:6,alignItems:"center",marginTop:8},children:[
r.jsx("div",{style:{flex:1,minWidth:0},children:r.jsx(re,{value:castSel,onChange:applyCast,options:[{value:"",label:"Casting…"}].concat(casts.map(function(c2){return{value:c2.name,label:c2.name}}))})}),
r.jsx(K,{variant:"ghost",size:"sm",disabled:saving,"data-dzcastsave":"1",onClick:function(){setNmOpen(!nmOpen);setCastNm(castSel||"")},children:"★ Sauver"}),
r.jsx(K,{variant:"ghost",size:"sm",disabled:!castSel||saving,"data-dzcastdel":"1",onClick:delCast,children:"✕"})]}),
nmOpen?r.jsxs("div",{style:{display:"flex",gap:6,marginTop:6},children:[
r.jsx("input",{value:castNm,onChange:function(ev){setCastNm(ev.target.value)},placeholder:"Nom du casting (existant = écrasé)","data-dzcastname":"1",style:{flex:1,height:26,padding:"0 8px",background:"var(--bg-base)",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",color:"var(--ink)",fontSize:11.5,outline:"none"}}),
r.jsx(K,{variant:"primary",size:"sm",disabled:!castNm.trim()||saving,"data-dzcastok":"1",onClick:saveCast,children:saving?"…":"OK"})]}):null]}),
r.jsxs("div",{style:{padding:14,borderTop:"1px solid var(--stroke)",background:"var(--bg-panel-2)",position:"sticky",bottom:0},children:[
r.jsx(K,{variant:"primary",size:"lg",icon:busy?"sparkle":"wave",glow:!0,style:{width:"100%"},"data-dzvogen":"1",disabled:busy||!txt.trim()||!okProv,onClick:gen,children:busy?"Génération…":"Générer la voix"}),
res&&res.error?r.jsxs("div",{"data-dzvores":"err",style:{marginTop:8,padding:8,background:"var(--red-soft)",border:"1px solid var(--red)",borderRadius:"var(--r-sm)",fontSize:11,color:"var(--ink)"},children:[
r.jsx("strong",{style:{color:"var(--red)"},children:"Échec : "}),
String(res.error).slice(0,300)]}):null,
res&&res.filename?r.jsxs("div",{"data-dzvores":"ok",style:{marginTop:8},children:[
r.jsx("audio",{src:res.url,controls:!0,style:{width:"100%"}}),
r.jsxs("div",{style:{marginTop:4,fontSize:10.5,color:"var(--ink-soft)"},children:[
r.jsx("span",{className:"mono",children:res.filename}),
" · ",res.kb," KB · disponible dans Library → Audio"]})]}):null]})]})]})}
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

    # S1 — deep-link : ?mode=voice accepté par l'init du mode.
    a = '["seedance","heygen","comp"].includes(B)?B:"seedance"'
    r = '["seedance","heygen","comp","voice"].includes(B)?B:"seedance"'
    s = apply(s, a, r, "S1-deeplink")

    # S2 — tuple d'onglet Voice Over (icône wave, jamais disabled).
    a = ',["comp","Composition","layers",Za||_n]].map('
    r = ',["comp","Composition","layers",Za||_n],["voice","Voice Over","wave",!1]].map('
    s = apply(s, a, r, "S2-onglet")

    # S3 — bascule du conteneur scrollable : panneau voice OU form existant.
    a = ('className:"scroll",style:{flex:1,overflowY:"auto"},'
         'children:[o!=="heygen"&&r.jsxs(ie,{label:"Source (Seedance)"')
    r = ('className:"scroll",style:{flex:1,overflowY:"auto"},'
         'children:o==="voice"?[r.jsx(DzQuickVoice,{},"dzqv")]:'
         '[o!=="heygen"&&r.jsxs(ie,{label:"Source (Seedance)"')
    s = apply(s, a, r, "S3-bascule")

    # S5 — footer natif du form (Est. cost + Generate + warnings fal/heygen),
    # sibling du conteneur scroll : masqué en mode voice (le panneau a son
    # propre bloc Générer, sticky en bas du scroll).
    a = ('r.jsxs("div",{style:{padding:14,borderTop:"1px solid var(--stroke)",'
         'background:"var(--bg-panel-2)"},children:[r.jsxs("div",{style:{display:"flex",'
         'alignItems:"center",justifyContent:"space-between",marginBottom:8,fontSize:11.5},'
         'children:[r.jsx("span",{className:"soft",children:"Est. cost"})')
    r = 'o!=="voice"&&' + a
    s = apply(s, a, r, "S5-footer")

    # S4 — injection des composants top-level avant um.
    a = 'function um({variant:e,activePersona:t}){'
    s = apply(s, a, js_inject() + a, "S4-inject")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (quickvoice V-a). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
