# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzmotion.py
"""Maillon de queue : MOTION (lot « Studio : Animation », t235, 17/10/2026).

Option A + (iii) validées par l'utilisateur (spec docs/superpowers/specs/2026-10-17-studio-animation-releve.md § B5) :
un moteur de texte chorégraphie le nœud Animation (POST /api/motion/choregraphier, t234), guidé par un nœud
« Direction motion » qui porte le style, la source et le moteur.
  - M0 : un type de port neuf `direction` (couleur de la catégorie Animations) — seule la sortie de Direction motion se
    relie à l'entrée `direction` de l'Animation (les liens exigent le même type) ;
  - M1 : le catalogue : l'Animation gagne les entrées `direction` et `script` (type text : Texte, Prompt, Script News)
    et la propriété `script` (le champ du nœud) ; le nœud neuf `MotionDirection`, catégorie motion, sortie
    `direction`, propriétés style / source / consigne / moteur / modele ;
  - M2 : la palette range Direction motion dans « Animations », après l'Animation ;
  - M3 : l'encart du nœud dit style · source · moteur en une ligne (ellipse, `title` = le texte complet) ;
  - M4 : l'inspecteur de Direction motion = `DzMotionDirection` ;
  - M5 : les fonctions du maillon, posées devant `DzAnimation` :
      * `dzMotionPayload(g, anim)` compile le graphe en corps de t234 : script = `value` du nœud relié à `script`
        (sinon le champ du nœud), direction = style / source / consigne du nœud relié à `direction` (la consigne ne
        part que pour un skill : celle d'un prompt est en lecture seule), moteur, modèle, aspect = format du Rendu,
        duree_s = durée de l'Animation, images = fichiers des éléments image déjà posés ;
      * `dzMotionRaison` / `dzMotionCout` / `dzMotionBilan` traduisent la réponse (codes `raison` de t234) ;
      * `DzMotionDirection` : Style (fiches maison), Source (Aucune / prompt en lecture seule + lien vers sa fiche /
        skill dont la consigne s'édite dans le nœud : zone repliable, « Revenir à l'original », compteur), Moteur
        (moteur + modèle + bulle de coût, comme mod-ia.js : GET /api/motion/moteurs puis
        /api/settings/provider-defaults/modeles au choix d'un moteur) ;
  - M6 : `DzAnimation` gagne un état (le bilan de la chorégraphie) et l'écoute de Ctrl+Z ;
  - M7 : son inspecteur gagne le bloc « Chorégraphier » : direction reliée, champ « Script » quand l'entrée `script`
    n'est pas reliée, bouton. Il appelle t234 et remplace les éléments, après confirmation s'il y en a ; l'état
    d'avant est empilé (`dzMoPile`) et Ctrl+Z (hors champ de saisie) le rend.

t241 (18/10/2026, spec docs/superpowers/specs/2026-10-18-studio-animation-personnalisation.md § P1-P5, P7, P8) — même
maillon, mêmes paires, M5 élargi :
  - rubrique « Personnaliser » (`dzMotionPerso`) : champs générés depuis les `champs` de la fiche (libellé, aide, défaut en
    texte d'exemple, liste avec « par défaut ») ; pour un prompt ou un skill, cinq précisions (libellés et aides de
    GET /api/motion/personnalisation), l'aperçu de la règle « mes précisions priment » et « Reprendre mes précisions »
    (copie celles du dernier autre nœud Direction motion du graphe) ; trois curseurs à 5 crans (état et phrase ajoutée,
    ou effet pour la Finition, lus sur la même route) ; Tempo (BPM 40-220) ; remplacements du format, de la durée, de
    la police et de la palette (vides = graphe et kit de marque) ;
  - Effort à côté du modèle : « Auto (défaut du modèle : …) » puis les niveaux de CE moteur et CE modèle (`efforts` de
    GET /api/motion/moteurs et de /api/settings/provider-defaults/modeles, t239), Auto seul sinon ; la bulle le dit ;
  - `dzMotionPayload` envoie direction.champs (vides retirés = défaut), direction.precisions (source seulement),
    direction.curseurs, tempo_bpm, effort (« auto » si le modèle connu ne l'accepte pas) et les remplacements
    (aspect, duree_s, marque {couleur, marque, police}). Ports, ancrage et hooks inchangés.
  Banc : backend/tests/test_studio_motion_personnaliser.py.

Comptes figés : `x.useState(` reste à 731 (une cinquantaine de bancs le sondent sur le livré) ; les hooks du maillon
passent par l'alias `dzMoUS` (comme `dzAvUS` des nœuds Avatar) : DEUX appels, chiffrés dans le banc — l'état de
rafraîchissement de DzMotionDirection et le bilan de DzAnimation. v2.8.0 ×4, DzTracks 181, dzglyph_paires.json et le
littéral Fu intouchés. Textes : une phrase = une clé dzT `studio.motion.*` (frontend/shared/i18n/motion.json).

Maillon de QUEUE, APRÈS dzstudio (dont il sonde le marqueur) ; il garde un .js.bak_dzmotion le temps de l'écriture
puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzmotion` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzstudio`. Lecture et écriture
en OCTETS. Banc : backend/tests/test_studio_motion_direction.py.
Run : python scripts/patch_bundle_dzmotion.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzmotion")
TAG = "dzmotion"
MARKER = "function DzMotionDirection("
MARKER_ATTENDU = 1
HOOKS = 2                       # appels à l'alias dzMoUS (voir l'en-tête)

SONDE_AMONT = [
    ("dzstudio", "var dzPortGeo={", 1),
    ("dzstudio_g", "function dzPresetDe(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

TA = ('{width:"100%",resize:"vertical",fontSize:12,lineHeight:1.4,padding:"8px",borderRadius:6,'
      'border:"1px solid var(--stroke-strong)",background:"var(--bg-base)",color:"var(--ink-strong)",'
      'fontFamily:"inherit",boxSizing:"border-box"}')
BTN = ('{fontSize:11,padding:"4px 8px",borderRadius:6,cursor:"pointer",background:"var(--bg-base)",'
       'border:"1px solid var(--stroke)",color:"var(--ink)"}')

FONCTIONS = (
    'var dzMoUS=x.useState,dzMoUE=x.useEffect,dzMoMAX=8000,dzMoCache={lst:null,mot:null,mods:{},effs:{},fiches:{},perso:null,'
    'p:null,pm:null,pp:null},dzMoPile={},dzMoTA=' + TA + ',dzMoBTN=' + BTN + ','
    'dzMoCURS=["creativite","rythme","finition"],dzMoFORMATS=["16:9","9:16","1:1","4:5"],dzMoHEX=/^#[0-9a-fA-F]{6}$/;'
    'function dzMoProps(n){return Object.assign({},(n&&Me[n.type]&&Me[n.type].props)||{},(n&&n.props)||{})}'
    'function dzMoNature(id){id=String(id||"");return id.indexOf("skill-")===0?"skill":id.indexOf("prompt-")===0?"prompt":""}'
    'function dzMoLangue(){return typeof window!=="undefined"&&window.dzLang&&window.dzLang()==="en"?"en":"fr"}'
    'function dzMoTitre(z){var t=z&&z.titre;return t&&typeof t==="object"?String(t[dzMoLangue()]||t.fr||""):String(t||(z&&z.id)||"")}'
    'function dzMoJson(u){return fetch(u).then(function(r_){return r_.ok?r_.json():null}).catch(function(){return null})}'
    'function dzMoCharger(force){var C=dzMoCache;if(C.p)return C.p;if(C.lst&&!force)return Promise.resolve(C.lst);'
    'C.p=dzMoJson("/api/motion/biblio").then(function(j){C.lst=j&&Array.isArray(j.entrees)?j.entrees:(C.lst||[]);C.p=null;'
    'return C.lst});return C.p}'
    'function dzMoMoteurs(force){var C=dzMoCache;if(C.pm)return C.pm;if(C.mot&&!force)return Promise.resolve(C.mot);'
    'C.pm=dzMoJson("/api/motion/moteurs").then(function(j){C.mot=j&&Array.isArray(j.moteurs)?j.moteurs:(C.mot||[]);C.pm=null;'
    'return C.mot});return C.pm}'
    'function dzMoModeles(m){return dzMoJson("/api/settings/provider-defaults/modeles?moteur="+encodeURIComponent(m))'
    '.then(function(j){dzMoCache.mods[m]=j&&Array.isArray(j.modeles)?j.modeles:[];'
    'dzMoCache.effs[m]=j&&j.efforts&&typeof j.efforts==="object"?j.efforts:{};return dzMoCache.mods[m]})}'
    'function dzMoPerso(force){var C=dzMoCache;if(C.pp)return C.pp;if(C.perso&&!force)return Promise.resolve(C.perso);'
    'C.pp=dzMoJson("/api/motion/personnalisation").then(function(j){C.perso=j&&j.curseurs&&j.precisions?j:(C.perso||null);'
    'C.pp=null;return C.perso});return C.pp}'
    'function dzMoLoc(v){return v&&typeof v==="object"&&!Array.isArray(v)?String(v[dzMoLangue()]||v.fr||""):String(v==null?"":v)}'
    'function dzMoNonVides(v){var o={};v&&typeof v==="object"&&Object.keys(v).forEach(function(k){var s=v[k];'
    'if(typeof s==="number"&&isFinite(s))o[k]=s;else if(s!=null&&typeof s!=="object"&&String(s).trim())o[k]=String(s)});return o}'
    'function dzMoCurseurs(D){var c=D&&D.curseurs||{},o={};dzMoCURS.forEach(function(k){var n=Number(c[k]);'
    'o[k]=Number.isInteger(n)&&n>=0&&n<=4?n:2});return o}'
    'function dzMoNombre(v){var t=Number(String(v==null?"":v).replace(",","."));return isFinite(t)&&t>0?t:0}'
    'function dzMoTempo(D){var t=dzMoNombre(D&&D.tempo);return t?Math.min(220,Math.max(40,Math.round(t))):null}'
    'function dzMoDuree(D){var t=dzMoNombre(D&&D.duree);return t?Math.min(120,Math.max(1,t)):null}'
    'function dzMoMarque(D){var m={};D=D||{};dzMoHEX.test(String(D.couleur||""))&&(m.couleur=String(D.couleur));'
    'dzMoHEX.test(String(D.couleur_marque||""))&&(m.marque=String(D.couleur_marque));D.police&&(m.police=String(D.police));'
    'return Object.keys(m).length?m:null}'
    'function dzMoEfforts(moteur,modele){var C=dzMoCache,E=C.effs[moteur],m0=(C.mot||[]).find(function(z){return z.moteur===moteur}),'
    'f=m0&&m0.efforts;if(E&&modele&&E[modele])return E[modele];if(f&&(!modele||f.modele===modele))return f;return null}'
    'function dzMoEffort(D){var e=String(D&&D.effort||"auto"),mt=String(D&&D.moteur||"");if(!mt||e==="auto")return"auto";'
    'var m0=(dzMoCache.mot||[]).find(function(z){return z.moteur===mt}),f=dzMoEfforts(mt,String(D.modele||(m0&&m0.modele)||""));'
    'return f&&(f.niveaux||[]).indexOf(e)<0?"auto":e}'
    'function dzMoFiche(id){return dzMoJson("/api/motion/biblio/"+encodeURIComponent(id)).then(function(j){'
    'if(j&&j.id===id)dzMoCache.fiches[id]=j;return j})}'
    'function dzMotionScript(g,a){var s=Wt(g,a.id,"script");if(s){var P=dzMoProps(s);return String(P.value==null?"":P.value)}'
    'return String((a.props&&a.props.script)||"")}'
    'function dzMotionDirection(g,a){var d=Wt(g,a.id,"direction");return d&&d.type==="MotionDirection"?d:null}'
    'function dzMotionPayload(g,a){var d=dzMotionDirection(g,a),D=d?dzMoProps(d):{},P=dzMoProps(a),src=String(D.source||""),'
    'nat=dzMoNature(src),R=(g.nodes||[]).find(function(n){return n.type==="Render"}),ims=[];(P.elements||[]).forEach(function(el){'
    'el&&el.type!=="text"&&el.filename&&ims.indexOf(el.filename)<0&&ims.push(el.filename)});'
    'var dir={style:String(D.style||""),source:src||null,consigne:nat==="skill"?String(D.consigne||""):"",'
    'champs:dzMoNonVides(D.champs),curseurs:dzMoCurseurs(D)};nat&&(dir.precisions=dzMoNonVides(D.precisions));'
    'var c={script:dzMotionScript(g,a),direction:dir,moteur:String(D.moteur||""),modele:String(D.modele||""),effort:dzMoEffort(D),'
    'aspect:dzMoFORMATS.indexOf(D.aspect)>=0?D.aspect:(R&&R.props&&R.props.format)||"9:16",'
    'duree_s:dzMoDuree(D)||Number(P.durationS)||8,images:ims},t=dzMoTempo(D),m=dzMoMarque(D);t&&(c.tempo_bpm=t);m&&(c.marque=m);'
    'return c}'
    'function dzMotionResume(P){var L=dzMoCache.lst||[];function f(id){var z=L.find(function(q){return q.id===id});'
    'return z?dzMoTitre(z):String(id||"").replace(/^(style|prompt|skill)-/,"")}'
    'return[P.style?f(P.style):"—",P.source?f(P.source):dzT("studio.motion.source_aucune"),'
    'P.moteur?P.moteur+(P.modele?" · "+P.modele:""):dzT("studio.motion.encart_maison")].join(" · ")}'
    'function dzMotionEncart(P){if(!dzMoCache.lst&&!dzMoCache.p)dzMoCharger();var s=dzMotionResume(P);'
    'return r.jsxs("div",{title:s,"data-dz-motion":"encart",style:{width:"100%",height:"100%",display:"flex",'
    'alignItems:"center",gap:6,padding:"0 10px",boxSizing:"border-box",background:"#0b1016",color:"var(--nd-motion)",'
    'fontSize:11},children:[r.jsx(X,{name:"dz-cat-animation",size:12}),'
    'r.jsx("span",{style:{minWidth:0,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},children:s})]})}'
    'function dzMotionRaison(c){return c==="sans_moteur"?dzT("studio.motion.raison_sans_moteur"):'
    'c==="moteur_inconnu"?dzT("studio.motion.raison_moteur_inconnu"):c==="non_configure"?dzT("studio.motion.raison_non_configure"):'
    'c==="modele_fautif"?dzT("studio.motion.raison_modele_fautif"):c==="sortie_invalide"?dzT("studio.motion.raison_sortie_invalide"):""}'
    'function dzMotionCout(c){var n=c&&c.nature;return n==="gratuit"?dzT("studio.motion.cout_bilan_gratuit"):'
    'n==="a_mesurer"?dzT("studio.motion.cout_bilan_a_mesurer"):'
    'dzT("studio.motion.cout_bilan_payant",{usd:Number((c&&c.estime_usd)||0).toFixed(4)})}'
    'function dzMotionBilan(j){var n=(j.elements||[]).length;return j.repli?'
    'dzT("studio.motion.bilan_repli",{n:n,raison:dzMotionRaison(j.raison)}):'
    'dzT("studio.motion.bilan",{n:n,moteur:j.moteur+(j.modele?" · "+j.modele:""),cout:dzMotionCout(j.cout)})}'
    'function dzMotionErreur(j){var d=j&&j.detail;return typeof d==="string"&&d?d:d&&typeof d.message==="string"&&d.message?'
    'd.message:dzT("studio.motion.echec")}'
    'function dzMotionBulle(m0,moteur,modele,f,eff){if(!moteur)return dzT("studio.motion.cout_aucun");'
    'var v={moteur:moteur+(modele?" · "+modele:"")},c=m0&&m0.cout||(moteur==="ollama"||moteur.indexOf("local:")===0?"gratuit":'
    'moteur.indexOf("fl:")===0?"a_mesurer":"payant"),n=f&&f.niveaux||[];return(c==="gratuit"?dzT("studio.motion.cout_gratuit",v):'
    'c==="a_mesurer"?dzT("studio.motion.cout_a_mesurer",v):dzT("studio.motion.cout_payant",v))+" · "+(!n.length?'
    'dzT("studio.motion.effort_bulle_seul"):eff&&eff!=="auto"&&n.indexOf(eff)>=0?dzT("studio.motion.effort_bulle",{effort:eff}):'
    'f.defaut?dzT("studio.motion.effort_bulle_auto",{defaut:f.defaut}):dzT("studio.motion.effort_bulle_auto_nu"))}'
    'function dzMoSous(t){return r.jsx("div",{style:{fontSize:10.5,fontWeight:600,letterSpacing:".04em",textTransform:"uppercase",'
    'color:"var(--ink-muted)",margin:"6px 0 6px"},children:t})}'
    'function dzMoCouleur(lab,k,P,o){var v=String(P[k]||""),ok=dzMoHEX.test(v);return r.jsx(O,{label:lab,children:r.jsxs("div",'
    '{style:{display:"flex",alignItems:"center",gap:6},children:[r.jsx("input",{type:"color","data-dz-motion":k,'
    'value:ok?v:"#808080","aria-label":lab,onChange:function(ev){o(k,ev.target.value)},style:{width:30,height:22,padding:0,'
    'border:"1px solid var(--stroke)",borderRadius:4,background:"none",cursor:"pointer"}}),r.jsx("span",{style:{flex:1,fontSize:11,'
    'color:"var(--ink-soft)"},children:ok?v:dzT("studio.motion.kit")}),ok?r.jsx("button",{"data-dz-motion":k+"-kit",'
    'onClick:function(){o(k,"")},style:dzMoBTN,children:dzT("studio.motion.kit_revenir")}):null]})},k)}'
    'function dzMotionPerso(P,o,g,e,nat){var C=dzMoCache,pe=C.perso,lg=dzMoLangue(),'
    'fi=(C.lst||[]).find(function(z){return z.id===P.style}),ch=fi&&Array.isArray(fi.champs)?fi.champs:[],V=P.champs||{},'
    'Q=P.precisions||{},K=dzMoCurseurs(P),R=(g.nodes||[]).find(function(n){return n.type==="Render"}),'
    'fmt=(R&&R.props&&R.props.format)||"9:16",fonts=typeof DZ_FONTS!=="undefined"&&Array.isArray(DZ_FONTS)?DZ_FONTS:[],k_=[];'
    'function pc(id,v){var z=Object.assign({},V);z[id]=v;o("champs",z)}'
    'function pq(id,v){var z=Object.assign({},Q);z[id]=v;o("precisions",z)}'
    'ch.length&&k_.push(dzMoSous(dzT("studio.motion.perso_fiche",{titre:dzMoTitre(fi)})));'
    'ch.forEach(function(c){var lib=dzMoLoc(c.libelle),ai=dzMoLoc(c.aide),v=V[c.id]==null?"":String(V[c.id]);'
    'if(c.type==="liste"){var od=(c.options||[]).find(function(q){return q.valeur===c.defaut});'
    'k_.push(r.jsx(O,{label:lib,hint:ai,children:r.jsx(re,{value:v,options:[{value:"",label:dzT("studio.motion.champ_defaut",'
    '{valeur:od?dzMoLoc(od.libelle):String(c.defaut==null?"":c.defaut)})}].concat((c.options||[]).map(function(q){'
    'return{value:String(q.valeur),label:dzMoLoc(q.libelle)}})),onChange:function(w){pc(c.id,w)}})},"c-"+c.id));return}'
    'var nb=c.type==="nombre";k_.push(r.jsx(O,{label:lib,hint:ai,children:r.jsx(le,{"data-dz-motion":"champ-"+c.id,value:v,'
    'type:nb?"number":"text",min:nb?c.min:void 0,max:nb?c.max:void 0,maxLength:nb?void 0:c.max,'
    'placeholder:nb?String(c.defaut==null?"":c.defaut):dzMoLoc(c.defaut),onChange:function(w){pc(c.id,w)}})},"c-"+c.id))});'
    'if(nat&&pe){var pr=pe.precisions,pch=pr.champs||[],pl=pch.filter(function(c){return String(Q[c.id]==null?"":Q[c.id]).trim()}),'
    'au=(g.nodes||[]).filter(function(n){return n.type==="MotionDirection"&&n.id!==e.id'
    '&&Object.keys(dzMoNonVides(n.props&&n.props.precisions)).length}).pop();'
    'k_.push(r.jsxs("div",{"data-dz-motion":"precisions",style:{marginBottom:8},children:[dzMoSous(dzMoLoc(pr.titre))].concat('
    'pch.map(function(c){return r.jsx(O,{label:dzMoLoc(c.libelle),children:r.jsx(le,{"data-dz-motion":"precision-"+c.id,'
    'value:Q[c.id]==null?"":String(Q[c.id]),maxLength:300,placeholder:dzMoLoc(c.aide),onChange:function(w){pq(c.id,w)}})},"p-"+c.id)}),'
    '[r.jsxs("div",{"data-dz-motion":"apercu",style:{fontSize:11,lineHeight:1.4,padding:"6px 8px",borderRadius:6,'
    'border:"1px dashed var(--stroke-strong)",background:"var(--bg-base)",color:"var(--ink-soft)"},children:['
    'r.jsx("div",{style:{color:"var(--ink)"},children:dzT("studio.motion.apercu_regle",{titre:dzMoLoc(pr.titre),regle:dzMoLoc(pr.regle)})})]'
    '.concat(pl.length?pl.map(function(c){return r.jsx("div",{children:dzT("studio.motion.apercu_ligne",{libelle:dzMoLoc(c.libelle),'
    'valeur:String(Q[c.id]).trim()})},"a-"+c.id)}):[r.jsx("div",{children:dzT("studio.motion.precisions_vides")},"a-0")])}),'
    'r.jsx("button",{"data-dz-motion":"reprendre",disabled:!au,title:dzT("studio.motion.reprendre_aide"),onClick:function(){'
    'au&&o("precisions",dzMoNonVides(au.props.precisions))},style:Object.assign({},dzMoBTN,{marginTop:6,cursor:au?"pointer":"default",'
    'opacity:au?1:.5}),children:dzT("studio.motion.reprendre")})])},"prec"))}'
    'k_.push(dzMoSous(dzT("studio.motion.perso_curseurs")));'
    'pe?dzMoCURS.forEach(function(k){var cu=pe.curseurs&&pe.curseurs[k];if(!cu)return;var n=K[k],cr=(cu.crans||[])[n]||{},'
    'po=cu.poles&&(cu.poles[lg]||cu.poles.fr)||["",""],ph=k==="finition"?dzMoLoc(cr.effet):cr.phrase?'
    'dzT("studio.motion.curseur_phrase",{phrase:dzMoLoc(cr.phrase)}):dzT("studio.motion.curseur_neutre");'
    'k_.push(r.jsxs("div",{"data-dz-motion":"curseur-"+k,style:{marginBottom:10},children:[r.jsxs("div",{style:{display:"flex",'
    'justifyContent:"space-between",gap:6,fontSize:11,color:"var(--ink-soft)"},children:[r.jsx("span",{children:dzMoLoc(cu.libelle)}),'
    'r.jsx("span",{"data-dz-motion":"etat-"+k,style:{color:"var(--ink-strong)",fontWeight:600},children:dzMoLoc(cr.etat)})]}),'
    'r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:6},children:[r.jsx("span",{style:{fontSize:10.5,'
    'color:"var(--ink-muted)"},children:po[0]}),r.jsx("input",{type:"range",min:0,max:4,step:1,value:n,"aria-label":dzMoLoc(cu.libelle),'
    '"data-dz-motion":"cran-"+k,onChange:function(ev){var z=dzMoCurseurs(P);z[k]=Number(ev.target.value);o("curseurs",z)},'
    'style:{flex:1,accentColor:"var(--nd-motion)",cursor:"pointer"}}),r.jsx("span",{style:{fontSize:10.5,color:"var(--ink-muted)"},'
    'children:po[1]})]}),r.jsx("div",{"data-dz-motion":"phrase-"+k,style:{fontSize:10.5,color:"var(--ink-muted)",lineHeight:1.35},'
    'children:ph})]},"k-"+k))}):k_.push(r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)",marginBottom:6},'
    'children:dzT("studio.motion.perso_chargement")},"k-0"));'
    'k_.push(dzMoSous(dzT("studio.motion.perso_remplacements")),'
    'r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-muted)",marginBottom:8},children:dzT("studio.motion.remplacements_aide")},"ra"),'
    'r.jsx(O,{label:dzT("studio.motion.tempo"),hint:dzT("studio.motion.tempo_aide"),children:r.jsx(le,{"data-dz-motion":"tempo",'
    'type:"number",min:40,max:220,value:P.tempo==null?"":String(P.tempo),placeholder:dzT("studio.motion.tempo_aucun"),'
    'onChange:function(w){o("tempo",w)}})},"tempo"),'
    'r.jsx(O,{label:dzT("studio.motion.format"),children:r.jsx(re,{value:dzMoFORMATS.indexOf(P.aspect)>=0?P.aspect:"",'
    'options:[{value:"",label:dzT("studio.motion.format_graphe",{format:fmt})}].concat(dzMoFORMATS.map(function(z){'
    'return{value:z,label:z}})),onChange:function(w){o("aspect",w)}})},"format"),'
    'r.jsx(O,{label:dzT("studio.motion.duree"),children:r.jsx(le,{"data-dz-motion":"duree",type:"number",min:1,max:120,'
    'value:P.duree==null?"":String(P.duree),placeholder:dzT("studio.motion.duree_graphe"),onChange:function(w){o("duree",w)}})},"duree"),'
    'r.jsx(O,{label:dzT("studio.motion.police"),children:r.jsx(re,{value:String(P.police||""),options:[{value:"",'
    'label:dzT("studio.motion.kit")}].concat(fonts.map(function(z){return{value:z,label:z}})),onChange:function(w){o("police",w)}})},"police"),'
    'dzMoCouleur(dzT("studio.motion.couleur"),"couleur",P,o),dzMoCouleur(dzT("studio.motion.couleur_marque"),"couleur_marque",P,o));'
    'return r.jsx(ie,{label:dzT("studio.motion.personnaliser"),defaultOpen:!0,children:r.jsx("div",{"data-dz-motion":"perso",'
    'style:{padding:"0 0 6px"},children:k_})})}'
    'function DzMotionDirection({node:e,graph:g,set:o}){var st_=dzMoUS(0),bump=st_[1],C=dzMoCache,P=dzMoProps(e),'
    'src=String(P.source||""),nat=dzMoNature(src),moteur=String(P.moteur||"");'
    'function f(){bump(function(z){return z+1})}'
    'dzMoUE(function(){var on=!0;function f2(){on&&f()}dzMoCharger(!0).then(f2);dzMoMoteurs(!0).then(f2);dzMoPerso().then(f2);'
    'return function(){on=!1}},[]);'
    'dzMoUE(function(){var on=!0;function f2(){on&&f()}moteur&&!C.mods[moteur]&&dzMoModeles(moteur).then(f2);'
    'src&&!C.fiches[src]&&dzMoFiche(src).then(f2);return function(){on=!1}},[moteur,src]);'
    'var L=C.lst,styles=(L||[]).filter(function(z){return z.nature==="style"}),'
    'sources=(L||[]).filter(function(z){return z.nature==="prompt"||z.nature==="skill"}),fi=C.fiches[src]||null,'
    'orig=fi&&nat==="skill"?String(fi.original!=null?fi.original:fi.consigne||""):"",'
    'cons=nat==="skill"?(P.consigne!=null&&P.consigne!==""?String(P.consigne):String((fi&&fi.consigne)||"")):"",'
    'modif=!!orig&&cons!==orig,mot=C.mot||[],m0=mot.find(function(z){return z.moteur===moteur})||null,'
    'ml=(moteur&&C.mods[moteur])||[],md=String(P.modele||(m0&&m0.modele)||"");'
    'ml=ml.length?ml.slice():md?[md]:[];md&&ml.indexOf(md)<0&&ml.unshift(md);'
    'var ef=dzMoEfforts(moteur,md)||{niveaux:[],defaut:""},nv=ef.niveaux||[],eff=nv.indexOf(String(P.effort||""))>=0?String(P.effort):"auto",'
    'bulle=dzMotionBulle(m0,moteur,String(P.modele||(m0&&m0.modele)||""),ef,eff);'
    'return r.jsxs(ie,{label:dzT("studio.motion.titre"),children:['
    'L?null:r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)",marginBottom:6},children:dzT("studio.motion.chargement")}),'
    'r.jsx(O,{label:dzT("studio.motion.style"),children:r.jsx(re,{value:String(P.style||""),'
    'options:styles.map(function(z){return{value:z.id,label:dzMoTitre(z)}}),onChange:function(v){o("style",v);o("champs",{})}})}),'
    'r.jsx(O,{label:dzT("studio.motion.source"),children:r.jsx(re,{value:src,'
    'options:[{value:"",label:dzT("studio.motion.source_aucune")}].concat(sources.map(function(z){return{value:z.id,'
    'label:z.nature==="skill"?dzT("studio.motion.source_skill",{titre:dzMoTitre(z)}):'
    'dzT("studio.motion.source_prompt",{titre:dzMoTitre(z)})}})),onChange:function(v){o("source",v);o("consigne","")}})}),'
    'nat==="prompt"?r.jsxs("div",{"data-dz-motion":"prompt",style:{marginBottom:8},children:['
    'r.jsx(O,{label:dzT("studio.motion.prompt_lecture"),children:r.jsx("textarea",{readOnly:!0,"data-dz-motion":"prompt-texte",'
    'value:String((fi&&fi.texte)||""),rows:5,style:dzMoTA})}),'
    'fi&&fi.url?r.jsx("a",{href:fi.url,target:"_blank",rel:"noopener noreferrer","data-dz-motion":"fiche",'
    'style:{fontSize:11,color:"var(--cyan)"},children:dzT("studio.motion.prompt_fiche")}):null,'
    'fi&&fi.auteur?r.jsx("span",{style:{fontSize:11,color:"var(--ink-soft)",marginLeft:8},'
    'children:dzT("studio.motion.prompt_auteur",{auteur:fi.auteur})}):null]}):null,'
    'nat==="skill"?r.jsx(ie,{label:dzT("studio.motion.consigne_skill"),defaultOpen:!0,children:r.jsxs("div",'
    '{"data-dz-motion":"skill",children:[r.jsx("textarea",{"data-dz-motion":"consigne",value:cons,maxLength:dzMoMAX,rows:8,'
    'onChange:function(ev){o("consigne",ev.target.value)},style:dzMoTA}),r.jsxs("div",{style:{display:"flex",'
    'alignItems:"center",gap:6,marginTop:4},children:[r.jsx("span",{"data-dz-motion":"compteur",style:{flex:1,fontSize:11,'
    'color:modif?"var(--amber)":"var(--ink-soft)"},children:modif?dzT("studio.motion.compteur_modifie",{n:cons.length,max:dzMoMAX}):'
    'dzT("studio.motion.compteur",{n:cons.length,max:dzMoMAX})}),r.jsx("button",{"data-dz-motion":"revenir",disabled:!modif,'
    'onClick:function(){o("consigne",orig)},style:dzMoBTN,children:dzT("studio.motion.revenir")})]})]})}):null,'
    'dzMotionPerso(P,o,g,e,nat),'
    'r.jsx(O,{label:dzT("studio.motion.moteur"),children:r.jsx(re,{value:moteur,'
    'options:[{value:"",label:dzT("studio.motion.moteur_aucun")}].concat(mot.map(function(z){return{value:z.moteur,'
    'label:z.configure?z.moteur:dzT("studio.motion.moteur_non_configure",{moteur:z.moteur})}})),'
    'onChange:function(v){o("moteur",v);o("modele","")}})}),'
    'moteur?r.jsx(O,{label:dzT("studio.motion.modele"),children:r.jsx(re,{value:md,'
    'options:ml.length?ml.map(function(z){return{value:z,label:z}}):[{value:"",label:"—"}],onChange:function(v){o("modele",v)}})}):null,'
    'moteur?r.jsx(O,{label:dzT("studio.motion.effort"),hint:nv.length?null:dzT("studio.motion.effort_seul"),children:r.jsx(re,'
    '{value:eff,options:[{value:"auto",label:ef.defaut?dzT("studio.motion.effort_auto_defaut",{defaut:ef.defaut}):'
    'dzT("studio.motion.effort_auto")}].concat(nv.map(function(z){return{value:String(z),label:String(z)}})),'
    'onChange:function(v){o("effort",v)}})}):null,'
    'r.jsx("div",{"data-dz-motion":"bulle",title:bulle,style:{fontSize:11,color:"var(--ink-soft)",lineHeight:1.4,'
    'margin:"2px 0 4px"},children:bulle})]})}'
)

HOOKS_ANIM = (
    'var moS=dzMoUS(null),moEt=moS[0],setMoEt=moS[1];'
    'dzMoUE(function(){function k(ev){if(!(ev.ctrlKey||ev.metaKey)||ev.shiftKey||ev.altKey||String(ev.key||"").toLowerCase()!=="z")return;'
    'var t1=ev.target,tg=(t1&&t1.tagName||"").toLowerCase();if(tg==="input"||tg==="textarea"||tg==="select"||(t1&&t1.isContentEditable))return;'
    'var pl=dzMoPile[e.id];if(!pl||!pl.length)return;ev.preventDefault();var v=pl.pop();o("elements",v.elements);'
    'o("selected",v.selected);setMoEt({msg:dzT("studio.motion.annule")})}'
    'window.addEventListener("keydown",k);return function(){window.removeEventListener("keydown",k)}});'
    'async function choregraphier(){var corps=dzMotionPayload(g,e);if(!corps.script.trim()){'
    'setMoEt({err:!0,msg:dzT("studio.motion.script_vide")});return}'
    'if(els.length&&!(await window.__dzDialogue.confirmer(dzT("studio.motion.remplacer",{n:els.length}),'
    '{titre:dzT("studio.motion.choregraphier"),ok:dzT("studio.motion.remplacer_ok")})))return;'
    'setMoEt({busy:!0,msg:dzT("studio.motion.en_cours")});'
    'try{var rq=await fetch("/api/motion/choregraphier",{method:"POST",headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify(corps)}),j=await rq.json().catch(function(){return null});'
    'if(!rq.ok||!j||!Array.isArray(j.elements)){setMoEt({err:!0,msg:dzMotionErreur(j)});return}'
    '(dzMoPile[e.id]=dzMoPile[e.id]||[]).push({elements:els,selected:sel});o("elements",j.elements);o("selected",0);'
    'setMoEt({msg:dzMotionBilan(j)})}catch(_e){setMoEt({err:!0,msg:dzT("studio.motion.echec")})}}'
    'function moBloc(){var sn=Wt(g,e.id,"script"),dn=dzMotionDirection(g,e),busy=!!(moEt&&moEt.busy),'
    'dl=dn?dzT("studio.motion.direction_reliee",{resume:dzMotionResume(dzMoProps(dn))}):dzT("studio.motion.direction_absente");'
    'return r.jsxs("div",{"data-dz-motion":"bloc",style:{marginBottom:8,padding:8,borderRadius:8,border:"1px solid var(--stroke)",'
    'background:"var(--surface-2)"},children:[r.jsx("div",{"data-dz-motion":"direction",title:dl,style:{fontSize:11,'
    'color:"var(--ink-soft)",marginBottom:6,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},children:dl}),'
    'sn?r.jsx("div",{"data-dz-motion":"script-relie",style:{fontSize:11,color:"var(--ink-soft)",marginBottom:6},'
    'children:dzT("studio.motion.script_relie",{titre:(Me[sn.type]&&Me[sn.type].title)||sn.type})}):'
    'r.jsx(O,{label:dzT("studio.motion.script"),children:r.jsx("textarea",{"data-dz-motion":"script",'
    'value:String(P.script||""),onChange:function(ev){o("script",ev.target.value)},rows:4,'
    'placeholder:dzT("studio.motion.script_aide"),style:dzMoTA})}),'
    'r.jsx("button",{"data-dz-motion":"choregraphier",onClick:choregraphier,disabled:busy,style:{width:"100%",fontSize:12,'
    'fontWeight:600,padding:"7px",borderRadius:7,border:"none",background:"var(--nd-motion)",color:"#04121c",'
    'cursor:busy?"default":"pointer"},children:busy?dzT("studio.motion.en_cours"):dzT("studio.motion.choregraphier")}),'
    'moEt&&moEt.msg?r.jsx("div",{"data-dz-motion":"message",role:"status",style:{fontSize:11,marginTop:6,'
    'color:moEt.err?"var(--red)":"var(--ink-soft)"},children:moEt.msg}):null]})}'
)

PAIRES = [
    ('text:{color:"var(--node-text)",label:"text"},data:{color:"var(--node-data)",label:"data"}},Qr={',          # M0
     'text:{color:"var(--node-text)",label:"text"},data:{color:"var(--node-data)",label:"data"},'
     'direction:{color:"var(--nd-motion)",label:"direction"}},Qr={'),
    ('Animation:{cat:"motion",title:"Animation",desc:dzT("studio.catalogue.animation_desc"),'                    # M1
     'inPorts:[{id:"base",type:"av"}],outPorts:[{id:"out",type:"av"}],props:{durationS:8,fps:30,elements:[],selected:0}},',
     'Animation:{cat:"motion",title:"Animation",desc:dzT("studio.catalogue.animation_desc"),'
     'inPorts:[{id:"base",type:"av"},{id:"direction",type:"direction"},{id:"script",type:"text"}],'
     'outPorts:[{id:"out",type:"av"}],props:{durationS:8,fps:30,elements:[],selected:0,script:""}},'
     'MotionDirection:{cat:"motion",title:dzT("studio.motion.titre"),desc:dzT("studio.motion.desc"),inPorts:[],'
     'outPorts:[{id:"direction",type:"direction"}],props:{style:"style-kinetic-type",source:"",consigne:"",moteur:"",modele:""}},'),
    ('{cat:"motion",types:["Animation"]}',                                                                      # M2
     '{cat:"motion",types:["Animation","MotionDirection"]}'),
    ('):n==="Animation"?r.jsxs(',                                                                               # M3
     '):n==="MotionDirection"?dzMotionEncart(o):n==="Animation"?r.jsxs('),
    ('e.type==="Animation"?r.jsx(DzAnimation,{node:e,graph:g,set:o}):',                                         # M4
     'e.type==="MotionDirection"?r.jsx(DzMotionDirection,{node:e,graph:g,set:o}):'
     'e.type==="Animation"?r.jsx(DzAnimation,{node:e,graph:g,set:o}):'),
    ('function DzAnimation({node:e,graph:g,set:o}){',                                                          # M5
     FONCTIONS + 'function DzAnimation({node:e,graph:g,set:o}){'),
    ('var ms=x.useState("from"),mode=ms[0],setMode=ms[1];',                                                    # M6
     HOOKS_ANIM + 'var ms=x.useState("from"),mode=ms[0],setMode=ms[1];'),
    ('children:"+ Image"})]}),els.length?',                                                                     # M7
     'children:"+ Image"})]}),moBloc(),els.length?'),
]


def lire(p):
    b = p.read_bytes()
    bom = b.startswith(b"\xef\xbb\xbf")
    return b.decode("utf-8-sig" if bom else "utf-8"), bom


def ecrire(p, texte, bom):
    p.write_bytes((("﻿" if bom else "") + texte).encode("utf-8"))


def appliquer(s: str) -> str:
    for ancre, remplace in PAIRES:
        n = s.count(ancre)
        if n != 1:
            raise SystemExit(f"[{TAG}] ancre x{n} (attendu 1) : {ancre[:80]!r}")
        s = s.replace(ancre, remplace, 1)
    return s


def defaire(s: str) -> str:
    """L'inverse exact (lu par avant_dzmotion dans _i18n_l1_aide)."""
    for ancre, remplace in reversed(PAIRES):
        if s.count(remplace) != 1:
            raise AssertionError(f"[{TAG}] remplacement x{s.count(remplace)} (attendu 1) : {remplace[:80]!r}")
        s = s.replace(remplace, ancre, 1)
    return s


def partiel(s: str) -> bool:
    """Marqueur présent mais le défaire complet échoue : une paire manque."""
    if MARKER not in s:
        return False
    try:
        defaire(s)
    except AssertionError:
        return True
    return False


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
        if partiel(s):
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzmotion "
                             f"(défaire avec le maillon d'avant l'ajout, puis appliquer)")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    crlf = s.count("\r\n")
    if crlf < 15000 or s.count("\n") != crlf:
        raise SystemExit(f"[{TAG}] fins de ligne inattendues ({crlf} CRLF / {s.count(chr(10))} LF)")
    neuf = appliquer(s)
    if neuf.count(MARKER) != MARKER_ATTENDU or defaire(neuf) != s:
        raise SystemExit(f"[{TAG}] aller-retour imparfait")
    if (neuf.count("x.useState(") != 731 or neuf.count("dzMoUS(") != HOOKS or neuf.count("v2.8.0") != 4
            or neuf.count("DzTracks") != 181):
        raise SystemExit(f"[{TAG}] un compte figé a bougé")
    if check:
        print(f"[{TAG}] à appliquer ({len(PAIRES)} paires)")
        return
    shutil.copyfile(BUNDLE, BAK)
    try:
        ecrire(BUNDLE, neuf, bom)
    except BaseException:
        shutil.copyfile(BAK, BUNDLE)                    # jamais un bundle à moitié écrit
        raise
    finally:
        BAK.unlink(missing_ok=True)
    print(f"[{TAG}] appliqué")


if __name__ == "__main__":
    main()
