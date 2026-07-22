# -*- coding: utf-8 -*-
# scripts/patch_bundle_voicenode.py
"""Assert-guarded patcher : chantier V-b — nœud Studio « Voiceover » réanimé.

BASELINE : bundle POST-patch version (v1.17.0 — chaîne quickvoice → version).
Backup dédié : .js.bak_voicenode (état juste avant CE patch).
Spec : docs/superpowers/specs/2026-07-22-voiceover-quick-studio-design.md (§6).

Sections :
- S1 props    : registre du nœud — props legacy (voice/stability, jamais
                câblées) remplacées par provider/voice_id/voice_name/language/
                filename/chars.
- S2 carte    : sous-titre de la carte nœud = voice_name (au lieu du
                « Adam » du prop legacy).
- S3 coût     : Qh — « $0.04 » en dur → chars × 0.00024 $ (MÊME constante
                que backend/app/services/pricing.py, elevenlabs_usd_per_char ;
                à changer LÀ-BAS d'abord si le tarif bouge, puis ici).
- S4 injection: helper dzGraphVoiceover(graph) (marche du port audio du
                Render — miroir de la marche de dzCompose, ports in/a/src/
                text — qui CAPTURE le filename du nœud Voiceover) +
                composant DzVoiceNodePanel, insérés avant um (même point
                d'injection éprouvé que quickvoice ; les déclarations de
                fonctions sont hoistées, l'ordre textuel est indifférent).
- S5 panneau  : branche d'inspecteur Voiceover dans Yh, à l'anchor « fin du
                panneau MusicTrack » (spec §4). Reçoit set (clé unique) ET
                upd (=t, merge multi-clés atomique pour voice_id+voice_name).
- S6 façade   : renderLayoutTemplate envoie voiceover:{file} — UNE seule
                surface pour TOUTES les branches template (UGC, montage,
                spatial) ; le backend post-merge la VO sur le composite.
- S7/S8 solo  : payloads directs Studio /generate et /generate/heygen —
                voiceover:{file} aux côtés de source_graph.
- S9 finition : hint « You're about to call fal.ai » de la colonne droite de
                Quick masqué en mode voice (reliquat tracé au chantier V-a).

Réutilise les identifiants module-scope vérifiés au chantier V-a : r/x
(React), D (façade API : createVoiceover, audioUrl), Ge (GET+fallback), Te
(base API), ie/O/re/K (section, champ, select custom, bouton), DzVoicePicker
(V-a), Wt (résolution d'arête amont).

Castings : atelier_settings.voice_castings, valeur = CHAÎNE JSON — partagés
avec Quick (V-a). Préécoute : celle de DzVoicePicker (aucune génération).

Run : python scripts/patch_bundle_voicenode.py
Rejouer la chaîne : python scripts/repatch_all.py --from voicenode
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_voicenode")

MARKER = "DzVoiceNodePanel"


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
function dzGraphVoiceover(g){
if(!g||!g.nodes||!g.edges)return null;
var rn=(g.nodes||[]).find(function(n2){return n2.type==="Render"});
if(!rn)return null;
var cur=Wt(g,rn.id,"audio"),k=0,vo=null;
while(cur&&k++<8){
if(cur.type==="Voiceover"){if(cur.props&&cur.props.filename&&!vo)vo={file:cur.props.filename};cur=Wt(g,cur.id,"text")}
else if(cur.type==="Loudness")cur=Wt(g,cur.id,"in");
else if(cur.type==="AudioMix")cur=Wt(g,cur.id,"a");
else if(cur.type==="MusicTrack")cur=Wt(g,cur.id,"src");
else break}
return vo}
function DzVoiceNodePanel({node:nd,p:np,set:st,upd:up2,graph:gr}){
const w1=x.useState(void 0),prov=w1[0],setProv=w1[1],
w2=x.useState(!1),busy=w2[0],setBusy=w2[1],
w3=x.useState(null),res=w3[0],setRes=w3[1],
w4=x.useState([]),casts=w4[0],setCasts=w4[1],
w5=x.useState(""),castSel=w5[0],setCastSel=w5[1],
w6=x.useState(!1),nmOpen=w6[0],setNmOpen=w6[1],
w7=x.useState(""),castNm=w7[0],setCastNm=w7[1],
w8=x.useState(!1),saving=w8[0],setSaving=w8[1];
x.useEffect(function(){var on=!0;
Ge("/voice/providers",null).then(function(v){on&&setProv(v||{resolved:null})});
Ge("/atelier/settings",null).then(function(d){if(!on)return;var raw=d&&d.settings&&d.settings.voice_castings;if(!raw)return;try{var j=JSON.parse(raw);Array.isArray(j)&&setCasts(j)}catch(_e){}});
return function(){on=!1}},[]);
var upn=Wt(gr,nd.id,"text");
var txt=String((upn&&upn.props&&upn.props.value)||"").trim();
var hasTxt=!!txt;
var resolved=prov===void 0?"loading":(prov&&prov.resolved)||null;
var okProv=resolved==="elevenlabs";
var lang=np.language==="en"?"en":"fr";
var cost=txt.length*0.00024;
async function gen(){if(!hasTxt||busy||!okProv)return;setBusy(!0);setRes(null);
try{var d=await D.createVoiceover({script:txt,language:lang,voice_id:np.voice_id||void 0,name:"studio_vo"});setBusy(!1);
if(d&&d.ok){up2({filename:d.filename,chars:txt.length});setRes({filename:d.filename,url:d.url,kb:d.size_kb})}
else setRes({error:(d&&d.error)||"Échec de la génération."})}
catch(err){setBusy(!1);setRes({error:String((err&&err.message)||err)})}}
async function putCasts(next){setSaving(!0);var ok=!1;
try{var rp=await fetch(Te+"/atelier/settings",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({voice_castings:JSON.stringify(next)})});ok=!!(rp&&rp.ok)}catch(_e){}
setSaving(!1);if(ok)setCasts(next);return ok}
async function saveCast(){var nm=castNm.trim();if(!nm)return;
var it={name:nm,provider:"elevenlabs",voice_id:np.voice_id||"",voice_name:np.voice_name||"Voix par défaut de l'app",language:lang};
var ok=await putCasts(casts.filter(function(c2){return c2&&c2.name!==nm}).concat([it]));
if(ok){setCastSel(nm);setNmOpen(!1);setCastNm("")}}
async function delCast(){if(!castSel)return;var ok=await putCasts(casts.filter(function(c2){return!(c2&&c2.name===castSel)}));if(ok)setCastSel("")}
function applyCast(nm){setCastSel(nm);if(!nm)return;var c2=casts.find(function(z2){return z2&&z2.name===nm});if(!c2)return;
var o2={voice_id:c2.voice_id||"",voice_name:c2.voice_name||"Voix par défaut de l'app"};
if(c2.language==="fr"||c2.language==="en")o2.language=c2.language;
up2(o2)}
var guard=resolved==="loading"||okProv?null:resolved==="voicebox"?r.jsx("div",{"data-dzvnprov":"voicebox",style:{padding:8,background:"var(--amber-soft)",border:"1px solid var(--amber)",borderRadius:"var(--r-sm)",fontSize:11,color:"var(--ink)"},children:"v1 gère ElevenLabs seul — change le Fournisseur de voix dans Réglages."}):r.jsx("div",{"data-dzvnprov":"none",style:{padding:8,background:"var(--red-soft)",border:"1px solid var(--red)",borderRadius:"var(--r-sm)",fontSize:11,color:"var(--ink)"},children:"Clé ElevenLabs manquante — ajoute-la dans Réglages → Clés."});
var fileShown=(res&&res.filename)||np.filename||"";
var fileUrl=res&&res.url?res.url:(np.filename?D.audioUrl(np.filename):"");
return r.jsxs(ie,{label:"Voice over",children:[
r.jsx(O,{label:"Texte amont",children:
hasTxt?r.jsxs("div",{"data-dzvntext":"1",style:{fontSize:11.5,color:"var(--ink)",background:"var(--bg-base)",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",padding:8,lineHeight:1.45},children:[
txt.slice(0,80),txt.length>80?"…":"",
r.jsxs("span",{style:{color:"var(--ink-muted)",fontSize:10.5},children:[" · ",txt.length," chars · ~$",cost.toFixed(4)]})]}):
r.jsx("div",{"data-dzvntext":"0",style:{fontSize:11,color:"var(--ink)",background:"var(--amber-soft)",border:"1px solid var(--amber)",borderRadius:"var(--r-sm)",padding:8},children:"Relie un nœud Text/Prompt à l'entrée text."})}),
guard?r.jsx(O,{children:guard}):null,
r.jsx(O,{label:"Langue",children:r.jsx(re,{value:lang,onChange:function(v2){st("language",v2)},options:[{value:"fr",label:"Français"},{value:"en",label:"Anglais"}]})}),
r.jsx(O,{label:"Voix",children:r.jsx(DzVoicePicker,{value:np.voice_id||"",onChange:function(v2,n3){up2({voice_id:v2,voice_name:n3})}})}),
r.jsxs("div",{"data-dzvncastrow":"1",style:{display:"flex",gap:6,alignItems:"center",marginTop:2},children:[
r.jsx("div",{style:{flex:1,minWidth:0},children:r.jsx(re,{value:castSel,onChange:applyCast,options:[{value:"",label:"Casting…"}].concat(casts.map(function(c2){return{value:c2.name,label:c2.name}}))})}),
r.jsx(K,{variant:"ghost",size:"sm",disabled:saving,"data-dzvncastsave":"1",onClick:function(){setNmOpen(!nmOpen);setCastNm(castSel||"")},children:"★ Sauver"}),
r.jsx(K,{variant:"ghost",size:"sm",disabled:!castSel||saving,"data-dzvncastdel":"1",onClick:delCast,children:"✕"})]}),
nmOpen?r.jsxs("div",{style:{display:"flex",gap:6,marginTop:6},children:[
r.jsx("input",{value:castNm,onChange:function(ev){setCastNm(ev.target.value)},placeholder:"Nom du casting (existant = écrasé)","data-dzvncastname":"1",style:{flex:1,height:26,padding:"0 8px",background:"var(--bg-base)",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",color:"var(--ink)",fontSize:11.5,outline:"none"}}),
r.jsx(K,{variant:"primary",size:"sm",disabled:!castNm.trim()||saving,"data-dzvncastok":"1",onClick:saveCast,children:saving?"…":"OK"})]}):null,
r.jsx(K,{variant:"primary",size:"md",icon:busy?"sparkle":"wave",style:{width:"100%",marginTop:8},"data-dzvngen":"1",disabled:busy||!hasTxt||!okProv,onClick:gen,children:busy?"Génération…":"Générer la voix"}),
res&&res.error?r.jsxs("div",{"data-dzvnres":"err",style:{marginTop:8,padding:8,background:"var(--red-soft)",border:"1px solid var(--red)",borderRadius:"var(--r-sm)",fontSize:11,color:"var(--ink)"},children:[
r.jsx("strong",{style:{color:"var(--red)"},children:"Échec : "}),
String(res.error).slice(0,300)]}):null,
fileShown?r.jsxs("div",{"data-dzvnres":"ok",style:{marginTop:8},children:[
fileUrl?r.jsx("audio",{src:fileUrl,controls:!0,style:{width:"100%"}}):null,
r.jsxs("div",{style:{marginTop:4,fontSize:10.5,color:"var(--ink-soft)"},children:[
r.jsx("span",{className:"mono","data-dzvnfile":fileShown,children:fileShown}),
" · mixée au Render (sortie → port audio) · Library → Audio"]})]}):null]})}
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

    # S1 — props du registre : legacy voice/stability -> props V-b.
    a = ('Voiceover:{cat:"audio",title:"Voiceover",desc:"ElevenLabs TTS",'
         'inPorts:[{id:"text",type:"text"}],outPorts:[{id:"out",type:"audio"}],'
         'props:{voice:"Adam · oracular",stability:.6}}')
    r = ('Voiceover:{cat:"audio",title:"Voiceover",desc:"ElevenLabs TTS",'
         'inPorts:[{id:"text",type:"text"}],outPorts:[{id:"out",type:"audio"}],'
         'props:{provider:"elevenlabs",voice_id:"",voice_name:"",language:"fr",'
         'filename:"",chars:0}}')
    s = apply(s, a, r, "S1-props")

    # S2 — sous-titre de carte : voice_name (le prop legacy `voice` a disparu).
    a = ('e.type==="Voiceover"?(a=(s=t.voice)==null?void 0:'
         's.split("·")[0])==null?void 0:a.trim():')
    r = 'e.type==="Voiceover"?(t.voice_name||"Voix par défaut"):'
    s = apply(s, a, r, "S2-carte")

    # S3 — coût de carte dynamique (chars × 0.00024, cf. pricing.py).
    a = 'e.type==="Voiceover"?"$0.04":'
    r = 'e.type==="Voiceover"?"$"+((((e.props||{}).chars)||0)*.00024).toFixed(4):'
    s = apply(s, a, r, "S3-cout")

    # S4 — injection helper + panneau avant um (déclarations hoistées).
    a = 'function um({variant:e,activePersona:t}){'
    s = apply(s, a, js_inject() + a, "S4-inject")

    # S5 — branche d'inspecteur à la fin du panneau MusicTrack (spec §4).
    a = ('label:"Loop to render duration"})})]}):'
         'e.type==="Seedance"?r.jsxs(ie,{label:"Generator"')
    r = ('label:"Loop to render duration"})})]}):'
         'e.type==="Voiceover"?r.jsx(DzVoiceNodePanel,'
         '{node:e,p:n,set:o,upd:t,graph:g},"dzvn"):'
         'e.type==="Seedance"?r.jsxs(ie,{label:"Generator"')
    s = apply(s, a, r, "S5-panneau")

    # S6 — façade renderLayoutTemplate : voiceover:{file} pour TOUTES les
    # branches template (le backend post-merge sur le composite).
    a = 'source_graph:g||null,preview:'
    r = 'source_graph:g||null,voiceover:dzGraphVoiceover(g)||null,preview:'
    s = apply(s, a, r, "S6-facade")

    # S7 — payload direct Studio -> /generate (Seedance solo).
    a = 'voiceover_enabled:!1,source_graph:e})'
    r = 'voiceover_enabled:!1,voiceover:dzGraphVoiceover(e)||void 0,source_graph:e})'
    s = apply(s, a, r, "S7-seedance")

    # S8 — payload direct Studio -> /generate/heygen (avatar solo).
    a = 'engine:(s.props&&s.props.engine)||void 0,source_graph:e})'
    r = ('engine:(s.props&&s.props.engine)||void 0,'
         'voiceover:dzGraphVoiceover(e)||void 0,source_graph:e})')
    s = apply(s, a, r, "S8-heygen")

    # S9 — finition V-a : hint fal.ai de la colonne droite masqué en voice.
    a = ('r.jsxs("div",{style:{position:"absolute",bottom:24,left:24,right:24,'
         'display:"flex",alignItems:"center",gap:12,fontSize:11,'
         'color:"var(--ink-soft)"},children:[r.jsx(X,{name:"warn",size:13,'
         'style:{color:"var(--amber)"}}),"You\'re about to call ",'
         'r.jsx("span",{className:"mono strong",children:"fal.ai"})')
    r = 'o!=="voice"&&' + a
    s = apply(s, a, r, "S9-falhint")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (voicenode V-b). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
