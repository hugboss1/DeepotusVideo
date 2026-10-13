# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzespace.py
"""Maillon de queue : les ESPACES DE MARQUE à l'écran (t202, Espaces de marque E2, 13/10/2026).

Spec docs/superpowers/specs/2026-10-13-espaces-de-marque.md (D1, D2) ; le serveur est posé par t200/t201
(/api/espaces, /api/espaces/{id}/persona). Ce qu'il pose (ancres uniques, relevées le 13/10 sur e0d1ceff) :
  - S1 les aides de module, juste avant le rail (`function tg(`) : cache `dzEspCache` (GET /api/espaces) et ses
    abonnés, `dzEspActiver` (POST …/activate puis l'événement `deepotus:espace-refresh` ET `deepotus:brand-refresh`
    — le kit de l'espace devient le kit actif côté serveur, la carte de marque se relit), `dzEspPersona` /
    `dzEspPersonaEcrire` (le persona de l'ÉCRAN vit dans le persona v2 de l'espace actif, clé `ecran`) ;
    les composants `DzEspaceSel` (sélecteur du rail) et `DzEspaces` (Réglages › Espaces) ;
  - S2 la carte de marque du rail : le sélecteur d'espace sous la tagline (« Gérer les espaces… » ouvre l'onglet) ;
  - S3 le shell : `savePersona` enregistre aussi le persona dans l'espace actif ; `setActivePersonaId` passé aux
    Réglages et à l'Onboarding devient `dzJ` (choisir un persona l'enregistre dans l'espace) ; au démarrage et à chaque
    changement d'espace, le persona de l'espace est relu (`ecran`) — Deepotus sans `ecran` garde le préréglage
    « deepotus », un espace neuf reçoit un persona vierge à son nom. Fin de l'état volatil en mémoire ;
  - S4-S7 les Réglages : « espaces » dans la liste blanche ?section= (ym), l'onglet après Personas, son rendu, et sa
    rubrique dans dzRubrique (recherche des Réglages).
Aucun useState ajouté (x.useReducer : compte figé 731), aucun DzTracks, rien qui touche « v2.8.0 ».
Clés dzT « espaces.* » : frontend/shared/i18n/espaces.json (FR/EN), assemblées par scripts/i18n_assembler.py.

Maillon de QUEUE, APRÈS encartsia (dont il sonde le marqueur) ; comme lui, il garde un .js.bak_dzespace le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzespace` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_encartsia`.
Lecture et écriture en OCTETS.
t203 (13/10/2026) : `DzComptesEspace`, sous la liste des espaces, gère les comptes de diffusion de l'espace ACTIF
(GET/POST/DELETE /api/comptes, /api/channels/test avec `compte`, OAuth par compte) ; aucun secret relu.
t204 (13/10/2026) : le Planificateur — `DzPostComptes` dans l'éditeur de post (comptes de l'espace du post), mappeur
et enregistrement des posts (espace_id, comptes), liste rechargée au changement d'espace.
t205 (13/10/2026) : `DzOnboardingPersona`, l'assistant en 8 étapes (bouton « Définir le persona » de chaque espace).
t206 (13/10/2026) : `DzIdentite`, l'identité visuelle (bouton « Identité visuelle » de chaque espace ; /api/espaces/{id}/identite).
t208 (13/10/2026) : S11, l'exemple des notes de Quick devient neutre (plus de « $DEEPOTUS Pyth-feed »).
Run : python scripts/patch_bundle_dzespace.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzespace")
TAG = "dzespace"
MARKER = "function DzEspaceSel("
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("encartsia", "function dzImgOpts(", 1),
    ("encartsia", "function dzDetCorps(", 1),
    ("dzguide", 'g:"/guide/#cardforge"}', 1),
    ("i18nfix", 'dzT("scheduler.mode.assiste")', 1),
    ("dzbiblio", '"data-dz-biblio-barre":"1"', 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

# S1 — les aides et les deux composants (une ligne : le code injecté par les maillons est minifié à la main).
# Les écritures passent par dzEspEnvoyer : un refus du serveur (400/404/409) rend son `detail`, jamais une page muette.
AIDES = (
    'var dzEspCache=null,dzEspAbonnes=[];'
    'function dzEspAvertir(){dzEspAbonnes.slice().forEach(function(f){try{f()}catch(_e){}})}'
    'function dzEspCharger(){return fetch("/api/espaces").then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);'
    'return r.json()}).then(function(d){dzEspCache=d;dzEspAvertir();return d})}'
    'function dzEspEnvoyer(u,m,c){return fetch(u,{method:m,headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify(c||{})}).then(function(r){return r.json().catch(function(){return{}}).then(function(j){'
    'if(!r.ok)throw new Error(j&&j.detail?String(j.detail):"HTTP "+r.status);return j})})}'
    'function dzEspSignal(){try{window.dispatchEvent(new Event("deepotus:espace-refresh"))}catch(_e){}}'
    'function dzEspActiver(id){return dzEspEnvoyer("/api/espaces/"+encodeURIComponent(id)+"/activate","POST")'
    '.then(function(d){return dzEspCharger().then(function(){dzEspSignal();return d})})}'
    'function dzEspPersona(cb){fetch("/api/espaces/actif").then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);'
    'return r.json()}).then(function(e){return fetch("/api/espaces/"+encodeURIComponent(e.id)+"/persona")'
    '.then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);return r.json()}).then(function(p){cb(e,p)})})'
    '.catch(function(){})}'
    'function dzEspPersonaEcrire(f){if(!f||!f.id)return;dzEspPersona(function(e,p){'
    'dzEspEnvoyer("/api/espaces/"+encodeURIComponent(e.id)+"/persona","PUT",Object.assign({},p,{ecran:f}))'
    '.catch(function(){})})}'
    # le sélecteur du rail
    'function DzEspaceSel({setView:sv}){const[st,maj]=x.useReducer(function(o,n){return Object.assign({},o,n)},'
    '{busy:!1,err:""});x.useEffect(function(){var f=function(){maj({})};dzEspAbonnes.push(f);'
    'dzEspCache||dzEspCharger().catch(function(){maj({err:dzT("espaces.erreur.lecture")})});'
    'return function(){dzEspAbonnes=dzEspAbonnes.filter(function(g){return g!==f})}},[]);'
    'if(!dzEspCache)return st.err?r.jsx("div",{role:"alert",style:{fontSize:10.5,color:"var(--red)",marginTop:8},'
    'children:st.err}):null;'
    'return r.jsxs("div",{"data-dz-espace-sel":"1",style:{marginTop:8},children:[r.jsxs("select",{'
    'value:dzEspCache.actif,disabled:st.busy,"aria-label":dzT("espaces.sel.titre"),title:dzT("espaces.sel.titre"),'
    'onChange:function(ev){var v=ev.target.value;if(v==="__gerer"){try{var u=new URL(window.location.href);'
    'u.searchParams.set("section","espaces");window.history.replaceState(null,"",u)}catch(_e){}sv&&sv("settings");return}'
    'maj({busy:!0,err:""});dzEspActiver(v).then(function(){maj({busy:!1})},function(e){maj({busy:!1,err:String(e&&e.message||e)})})},'
    'style:{width:"100%",fontSize:11.5,padding:"4px 6px",background:"var(--bg-panel-2)",color:"var(--ink-strong)",'
    'border:"1px solid var(--stroke)",borderRadius:4},children:[(dzEspCache.espaces||[]).map(function(e){'
    'return r.jsx("option",{value:e.id,"data-dz-brut":"1",children:e.nom},e.id)}),'
    'r.jsx("option",{value:"__gerer",children:dzT("espaces.sel.gerer")},"__gerer")]}),'
    'st.err&&r.jsx("div",{role:"alert",style:{fontSize:10.5,color:"var(--red)",marginTop:4},children:st.err})]})}'
    # Réglages › Espaces
    'function DzEspaces(){const[st,maj]=x.useReducer(function(o,n){return Object.assign({},o,n)},'
    '{liste:null,actif:"",kits:[],arch:!1,nom:"",couleur:"#3b82f6",err:"",busy:!1,edit:"",editNom:""});'
    'function charger(){return Promise.all([fetch("/api/espaces?archives=true").then(function(r){return r.json()}),'
    'fetch("/api/brand-kits").then(function(r){return r.json()})]).then(function(v){maj({liste:v[0].espaces||[],'
    'actif:v[0].actif,kits:v[1].kits||[]})}).catch(function(){maj({err:dzT("espaces.erreur.lecture")})})}'
    'x.useEffect(function(){charger()},[]);'
    'function agir(p,signal){maj({busy:!0,err:""});return p.then(function(){return charger()}).then(function(){'
    'return dzEspCharger()}).then(function(){signal&&dzEspSignal();maj({busy:!1})},function(e){'
    'maj({busy:!1,err:String(e&&e.message||e)})})}'
    'function base(id){return"/api/espaces/"+encodeURIComponent(id)}'
    'var bt={fontSize:11.5,padding:"4px 10px",background:"var(--bg-panel-2)",color:"var(--ink-strong)",'
    'border:"1px solid var(--stroke)",borderRadius:4,cursor:"pointer"};'
    'var champ={fontSize:12,padding:"5px 8px",background:"var(--bg-panel-2)",color:"var(--ink-strong)",'
    'border:"1px solid var(--stroke)",borderRadius:4};'
    'var vues=(st.liste||[]).filter(function(e){return st.arch||!e.archive});'
    'return r.jsxs("div",{"data-dz-espaces":"1",style:{display:"flex",flexDirection:"column",gap:14},children:['
    'r.jsx("h2",{style:{margin:0,fontSize:16,color:"var(--ink-strong)"},children:dzT("espaces.reglages.titre")}),'
    'r.jsx("p",{style:{margin:0,fontSize:12.5,color:"var(--ink-soft)",maxWidth:640},children:dzT("espaces.reglages.aide")}),'
    'r.jsxs("form",{"data-dz-espace-nouveau":"1",onSubmit:function(ev){ev.preventDefault();if(!st.nom.trim())return;'
    'agir(dzEspEnvoyer("/api/espaces","POST",{nom:st.nom.trim(),couleur:st.couleur})).then(function(){maj({nom:""})})},'
    'style:{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"},children:['
    'r.jsx("input",{value:st.nom,maxLength:60,placeholder:dzT("espaces.nouveau.nom"),"aria-label":dzT("espaces.nouveau.nom"),'
    'onChange:function(ev){maj({nom:ev.target.value})},style:Object.assign({},champ,{minWidth:220})}),'
    'r.jsx("input",{type:"color",value:st.couleur,title:dzT("espaces.nouveau.couleur"),"aria-label":dzT("espaces.nouveau.couleur"),'
    'onChange:function(ev){maj({couleur:ev.target.value})},style:{width:36,height:28,padding:0,border:0,background:"none"}}),'
    'r.jsx("button",{type:"submit",disabled:st.busy||!st.nom.trim(),style:bt,children:dzT("espaces.nouveau.creer")})]}),'
    'st.err&&r.jsx("div",{role:"alert",style:{fontSize:12,color:"var(--red)"},children:st.err}),'
    'st.liste===null&&!st.err&&r.jsx("div",{style:{fontSize:12,color:"var(--ink-muted)"},children:dzT("espaces.etat.chargement")}),'
    'r.jsx("div",{style:{display:"flex",flexDirection:"column",gap:6},children:vues.map(function(e){'
    'var act=e.id===st.actif,ed=st.edit===e.id;'
    'return r.jsxs("div",{"data-dz-espace":e.id,style:{display:"flex",alignItems:"center",gap:10,flexWrap:"wrap",padding:"8px 10px",'
    'border:"1px solid "+(act?"var(--cyan)":"var(--stroke)"),borderRadius:6,background:"var(--bg-panel)",opacity:e.archive?.6:1},children:['
    'r.jsx("span",{style:{width:12,height:12,borderRadius:6,background:e.couleur,flex:"none"}}),'
    'ed?r.jsx("input",{value:st.editNom,maxLength:60,autoFocus:!0,"aria-label":dzT("espaces.action.renommer"),'
    'onChange:function(ev){maj({editNom:ev.target.value})},style:champ})'
    ':r.jsx("strong",{"data-dz-brut":"1",style:{fontSize:13,color:"var(--ink-strong)",minWidth:120},children:e.nom}),'
    'act&&r.jsx("span",{style:{fontSize:10.5,color:"var(--cyan)"},children:dzT("espaces.etat.actif")}),'
    'e.archive&&r.jsx("span",{style:{fontSize:10.5,color:"var(--ink-muted)"},children:dzT("espaces.etat.archive")}),'
    'r.jsx("label",{style:{fontSize:11,color:"var(--ink-soft)",marginLeft:"auto"},children:dzT("espaces.champ.kit")}),'
    'r.jsx("select",{value:e.kit_id||"",disabled:st.busy,"aria-label":dzT("espaces.champ.kit"),onChange:function(ev){'
    # 13/10 (après t205) : vide = l'espace SUIT le kit de Réglages › Branding ; un kit choisi ne sert qu'à ses contenus
    'agir(dzEspEnvoyer(base(e.id),"POST",{kit_id:ev.target.value}),act)},style:champ,children:[r.jsx("option",{value:"",'
    'children:dzT("espaces.champ.kit_branding")},"__branding")].concat(st.kits.map(function(k){'
    'return r.jsx("option",{value:k.id,"data-dz-brut":"1",children:k.name},k.id)}))}),'
    'ed?r.jsxs(r.Fragment,{children:[r.jsx("button",{type:"button",disabled:st.busy||!st.editNom.trim(),style:bt,onClick:function(){'
    'agir(dzEspEnvoyer(base(e.id),"POST",{nom:st.editNom.trim()}),act).then(function(){maj({edit:""})})},'
    'children:dzT("espaces.action.enregistrer")}),r.jsx("button",{type:"button",style:bt,onClick:function(){maj({edit:""})},'
    'children:dzT("espaces.action.annuler")})]})'
    ':r.jsx("button",{type:"button",disabled:st.busy,style:bt,onClick:function(){maj({edit:e.id,editNom:e.nom})},'
    'children:dzT("espaces.action.renommer")}),'
    '!e.archive&&r.jsx("button",{type:"button","data-dz-onb-ouvrir":e.id,style:bt,onClick:function(){maj({onb:e.id})},children:dzT("espaces.onb.ouvrir")}),'
    '!e.archive&&r.jsx("button",{type:"button","data-dz-idv-ouvrir":e.id,style:bt,onClick:function(){maj({idv:e.id})},children:dzT("espaces.idv.ouvrir")}),'
    '!act&&!e.archive&&r.jsx("button",{type:"button","data-dz-espace-activer":e.id,disabled:st.busy,style:bt,onClick:function(){'
    'maj({busy:!0,err:""});dzEspActiver(e.id).then(function(){return charger()}).then(function(){maj({busy:!1})},'
    'function(x2){maj({busy:!1,err:String(x2&&x2.message||x2)})})},children:dzT("espaces.action.activer")}),'
    '!act&&r.jsx("button",{type:"button",disabled:st.busy,style:bt,onClick:function(){'
    'agir(dzEspEnvoyer(base(e.id)+"/archive","POST",{archive:!e.archive}))},'
    'children:dzT(e.archive?"espaces.action.desarchiver":"espaces.action.archiver")})]},e.id)})}),'
    'r.jsxs("label",{style:{fontSize:12,color:"var(--ink-soft)",display:"flex",gap:6,alignItems:"center"},children:['
    'r.jsx("input",{type:"checkbox",checked:st.arch,onChange:function(ev){maj({arch:ev.target.checked})}}),'
    'dzT("espaces.reglages.voir_archives")]}),'
    'st.onb&&r.jsx(DzOnboardingPersona,{espace:st.onb,nom:((st.liste||[]).find(function(e){return e.id===st.onb})||{}).nom||"",'
    'fermer:function(){maj({onb:""})}},"onb:"+st.onb),'   # clé PRÉFIXÉE : voisin de DzComptesEspace (même id d'espace)
    'st.idv&&r.jsx(DzIdentite,{espace:st.idv,nom:((st.liste||[]).find(function(e){return e.id===st.idv})||{}).nom||"",'
    'fermer:function(){maj({idv:""})}},"idv:"+st.idv),'   # t206 : clé PRÉFIXÉE elle aussi
    'st.actif&&r.jsx(DzComptesEspace,{espace:st.actif,nom:((st.liste||[]).find(function(e){return e.id===st.actif})||{}).nom||""},"cpt:"+st.actif)]})}'
    # t203 — les comptes de diffusion de l'espace ACTIF (plusieurs X, Telegram… par espace). Aucun secret n'est jamais
    # relu : un champ secret dit « posé » ou non ; une saisie vide ne change rien. OAuth (YouTube, TikTok) PAR compte :
    # /api/oauth/<p>/start?compte=<id>, l'onglet ouvert AVANT l'appel (sinon le bloqueur de fenêtres le refuse), une
    # erreur du serveur (400/409) dite dans la ligne. Supprimer = deux clics (jamais de window.confirm).
    'function DzComptesEspace({espace:esp,nom:nomEsp}){const[st,maj]=x.useReducer(function(o,n){return Object.assign({},o,n)},'
    '{data:null,plat:"x",libelle:"",handle:"",err:"",busy:!1,ouvert:"",saisie:{},msg:{},suppr:""});'
    'function charger(){return fetch("/api/comptes?espace="+encodeURIComponent(esp)).then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);'
    'return r.json()}).then(function(d){maj({data:d})}).catch(function(){maj({err:dzT("espaces.erreur.lecture")})})}'
    'x.useEffect(function(){charger()},[esp]);'
    'function agir(p){maj({busy:!0,err:""});return p.then(function(){return charger()}).then(function(){maj({busy:!1})},'
    'function(e){maj({busy:!1,err:String(e&&e.message||e)})})}'
    'function dire(id,t){var m=Object.assign({},st.msg);m[id]=t;maj({msg:m})}'
    'function tester(c){dire(c.id,dzT("espaces.comptes.test_en_cours"));dzEspEnvoyer("/api/channels/test","POST",{channel:c.plateforme,'
    'compte:c.historique?void 0:c.id}).then(function(j){dire(c.id,(j.ok?"✓ ":"✗ ")+(j.detail||""))},function(e){dire(c.id,"✗ "+(e&&e.message||e))})}'
    'function connecter(c){var u="/api/oauth/"+c.plateforme+"/start"+(c.historique?"":"?compte="+encodeURIComponent(c.id)),w=null;'
    'try{w=window.open("","_blank")}catch(_e){}fetch(u,{redirect:"manual"}).then(function(r){if(r.type==="opaqueredirect"||r.status===302){'
    'w?w.location=u:window.open(u,"_blank");dire(c.id,dzT("espaces.comptes.connexion_ouverte"));return}w&&w.close();'
    'return r.json().then(function(j){dire(c.id,"✗ "+(j&&j.detail||"HTTP "+r.status))})}).catch(function(e){w&&w.close();dire(c.id,"✗ "+(e&&e.message||e))})}'
    'function enregistrer(c){var v={};Object.keys(st.saisie).forEach(function(k){var x2=st.saisie[k];if(x2!==""&&x2!=null)v[k]=x2});'
    'if(!Object.keys(v).length){maj({ouvert:""});return}'
    'agir(dzEspEnvoyer("/api/comptes/"+encodeURIComponent(c.id),"POST",{valeurs:v})).then(function(){maj({ouvert:"",saisie:{}})})}'
    'var pl=st.data&&st.data.plateformes||{},cs=st.data&&st.data.comptes||[];'
    'var bt={fontSize:11.5,padding:"4px 10px",background:"var(--bg-panel-2)",color:"var(--ink-strong)",border:"1px solid var(--stroke)",borderRadius:4,cursor:"pointer"};'
    'var champ={fontSize:12,padding:"5px 8px",background:"var(--bg-panel-2)",color:"var(--ink-strong)",border:"1px solid var(--stroke)",borderRadius:4};'
    'return r.jsxs("div",{"data-dz-comptes":esp,style:{display:"flex",flexDirection:"column",gap:10,marginTop:8,paddingTop:14,borderTop:"1px solid var(--stroke)"},children:['
    'r.jsx("h3",{style:{margin:0,fontSize:14,color:"var(--ink-strong)"},children:dzT("espaces.comptes.titre",{nom:nomEsp})}),'
    'r.jsx("p",{style:{margin:0,fontSize:12,color:"var(--ink-soft)",maxWidth:640},children:dzT("espaces.comptes.aide")}),'
    'st.err&&r.jsx("div",{role:"alert",style:{fontSize:12,color:"var(--red)"},children:st.err}),'
    'st.data&&!cs.length&&r.jsx("div",{style:{fontSize:12,color:"var(--ink-muted)"},children:dzT("espaces.comptes.aucun")}),'
    'cs.map(function(c){var ouv=st.ouvert===c.id;return r.jsxs("div",{"data-dz-compte":c.id,style:{display:"flex",flexDirection:"column",gap:6,padding:"8px 10px",'
    'border:"1px solid var(--stroke)",borderRadius:6,background:"var(--bg-panel)"},children:[r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:10,flexWrap:"wrap"},children:['
    'r.jsx("span",{style:{fontSize:10.5,fontFamily:"var(--f-mono)",color:"var(--ink-muted)",minWidth:64},children:(pl[c.plateforme]||{}).libelle||c.plateforme}),'
    'r.jsx("strong",{"data-dz-brut":"1",style:{fontSize:13,color:"var(--ink-strong)"},children:c.libelle}),'
    'c.handle&&r.jsx("span",{"data-dz-brut":"1",style:{fontSize:11.5,color:"var(--ink-soft)"},children:c.handle}),'
    'r.jsx("span",{style:{fontSize:10.5,color:c.disponible?"var(--green)":"var(--amber)"},children:dzT(c.disponible?"espaces.comptes.disponible":"espaces.comptes.incomplet")}),'
    'r.jsxs("span",{style:{marginLeft:"auto",display:"flex",gap:6,flexWrap:"wrap"},children:['
    '!c.historique&&r.jsx("button",{type:"button",style:bt,disabled:st.busy,onClick:function(){maj({ouvert:ouv?"":c.id,saisie:{}})},children:dzT("espaces.comptes.identifiants")}),'
    'c.oauth&&r.jsx("button",{type:"button",style:bt,onClick:function(){connecter(c)},children:dzT("espaces.comptes.connecter")}),'
    'r.jsx("button",{type:"button",style:bt,onClick:function(){tester(c)},children:dzT("espaces.comptes.tester")}),'
    '!c.historique&&(st.suppr===c.id?r.jsx("button",{type:"button","data-dz-compte-suppr":c.id,style:Object.assign({},bt,{color:"var(--red)",borderColor:"var(--red)"}),disabled:st.busy,'
    'onClick:function(){maj({suppr:""});agir(fetch("/api/comptes/"+encodeURIComponent(c.id),{method:"DELETE"}).then(function(r2){if(!r2.ok)return r2.json().catch(function(){return{}})'
    '.then(function(j){throw new Error(j&&j.detail||"HTTP "+r2.status)})}))},children:dzT("espaces.comptes.confirmer")})'
    ':r.jsx("button",{type:"button",style:bt,onClick:function(){maj({suppr:c.id})},children:dzT("espaces.comptes.supprimer")}))]})]}),'
    'c.historique&&r.jsx("div",{style:{fontSize:11,color:"var(--ink-muted)"},children:dzT("espaces.comptes.historique")}),'
    'st.msg[c.id]&&r.jsx("div",{"data-dz-compte-msg":c.id,style:{fontSize:11.5,color:"var(--ink-soft)"},children:st.msg[c.id]}),'
    'ouv&&r.jsxs("form",{onSubmit:function(ev){ev.preventDefault();enregistrer(c)},style:{display:"grid",gridTemplateColumns:"minmax(160px,auto) 1fr",gap:6,alignItems:"center"},children:['
    'c.champs.map(function(f){var val=st.saisie[f.nom];return[r.jsx("label",{style:{fontSize:11,fontFamily:"var(--f-mono)",color:"var(--ink-soft)"},children:f.nom},f.nom+"l"),'
    'f.nom==="TIKTOK_AUDITED"?r.jsx("input",{type:"checkbox","aria-label":f.nom,checked:val!=null?!!val:!!f.valeur,onChange:function(ev){var z=Object.assign({},st.saisie);'
    'z[f.nom]=ev.target.checked;maj({saisie:z})}},f.nom):r.jsx("input",{type:f.secret?"password":"text","aria-label":f.nom,autoComplete:"off",'
    'value:val!=null?val:f.secret?"":f.valeur||"",placeholder:f.secret&&f.pose?dzT("espaces.comptes.pose"):"",onChange:function(ev){var z=Object.assign({},st.saisie);'
    'z[f.nom]=ev.target.value;maj({saisie:z})},style:champ},f.nom)]}),'
    'r.jsx("span",{}),r.jsx("span",{children:r.jsx("button",{type:"submit",style:bt,disabled:st.busy,children:dzT("espaces.comptes.enregistrer")})})]})]},c.id)}),'
    'r.jsxs("form",{"data-dz-compte-nouveau":"1",onSubmit:function(ev){ev.preventDefault();agir(dzEspEnvoyer("/api/comptes","POST",{espace_id:esp,plateforme:st.plat,'
    'libelle:st.libelle.trim(),handle:st.handle.trim()})).then(function(){maj({libelle:"",handle:""})})},style:{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"},children:['
    'r.jsx("select",{value:st.plat,"aria-label":dzT("espaces.comptes.plateforme"),onChange:function(ev){maj({plat:ev.target.value})},style:champ,'
    'children:Object.keys(pl).map(function(k){return r.jsx("option",{value:k,children:pl[k].libelle},k)})}),'
    'r.jsx("input",{value:st.libelle,maxLength:80,placeholder:dzT("espaces.comptes.libelle"),"aria-label":dzT("espaces.comptes.libelle"),'
    'onChange:function(ev){maj({libelle:ev.target.value})},style:champ}),'
    'r.jsx("input",{value:st.handle,maxLength:80,placeholder:dzT("espaces.comptes.handle"),"aria-label":dzT("espaces.comptes.handle"),'
    'onChange:function(ev){maj({handle:ev.target.value})},style:champ}),'
    'r.jsx("button",{type:"submit",style:bt,disabled:st.busy||!st.data,children:dzT("espaces.comptes.ajouter")})]})]})}'
    # t204 — dans l'éditeur d'un post du Planificateur : les comptes de diffusion de SON espace (cache par espace).
    # Cocher un compte pose `comptes` ET les canaux qui en découlent (le serveur fait de même et garde l'espace :
    # 409 pour un compte d'un autre espace). Un post d'un autre espace que Deepotus sans compte est signalé : il ne
    # partira jamais par les comptes de Deepotus.
    'var dzPcCache={};'
    'function DzPostComptes({post:p,onChange:oc}){const[,maj]=x.useReducer(function(n){return n+1},0);'
    'var esp=p.espaceId||"deepotus",d=dzPcCache[esp];'
    'x.useEffect(function(){if(dzPcCache[esp])return;dzPcCache[esp]={chargement:!0};'
    'fetch("/api/comptes?espace="+encodeURIComponent(esp)).then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);return r.json()})'
    '.then(function(j){dzPcCache[esp]={liste:j.comptes||[],pl:j.plateformes||{}};maj()},function(){delete dzPcCache[esp];maj()})},[esp]);'
    'var choisis=p.comptes||[],liste=d&&d.liste||[];'
    'function basculer(c){var n=choisis.indexOf(c.id)>=0?choisis.filter(function(i){return i!==c.id}):choisis.concat([c.id]);'
    'if(!n.length){oc({comptes:[]});return}'
    'var ch=[];n.forEach(function(i){var v=liste.find(function(x2){return x2.id===i});v&&ch.indexOf(v.plateforme)<0&&ch.push(v.plateforme)});'
    'oc({comptes:n,channels:ch})}'
    'return r.jsxs("div",{"data-dz-post-comptes":p.id,style:{display:"flex",flexDirection:"column",gap:6,marginBottom:12},children:['
    'r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)",textTransform:"uppercase",letterSpacing:".04em"},children:dzT("espaces.post.titre")}),'
    '!d||d.chargement?r.jsx("div",{style:{fontSize:11.5,color:"var(--ink-muted)"},children:dzT("espaces.etat.chargement")})'
    ':!liste.length?r.jsx("div",{style:{fontSize:11.5,color:"var(--ink-muted)"},children:dzT("espaces.comptes.aucun")})'
    ':r.jsx("div",{style:{display:"flex",flexDirection:"column",gap:4},children:liste.map(function(c){var on=choisis.indexOf(c.id)>=0;'
    'return r.jsxs("label",{"data-dz-post-compte":c.id,style:{display:"flex",alignItems:"center",gap:8,fontSize:12,color:"var(--ink-strong)",cursor:"pointer"},children:['
    'r.jsx("input",{type:"checkbox",checked:on,onChange:function(){basculer(c)}}),'
    'r.jsx("span",{style:{fontFamily:"var(--f-mono)",fontSize:10.5,color:"var(--ink-muted)",minWidth:62},children:(d.pl[c.plateforme]||{}).libelle||c.plateforme}),'
    'r.jsx("span",{"data-dz-brut":"1",children:c.libelle+(c.handle?" "+c.handle:"")}),'
    '!c.disponible&&r.jsx("span",{style:{fontSize:10.5,color:"var(--amber)"},children:dzT("espaces.comptes.incomplet")})]},c.id)})}),'
    'esp!=="deepotus"&&!choisis.length&&r.jsx("div",{role:"alert","data-dz-post-sans-compte":"1",style:{fontSize:11.5,color:"var(--amber)"},'
    'children:dzT("espaces.post.sans_compte")})]})}'
    # t205 — l'ONBOARDING du persona : 8 étapes (spec D3). Chaque étape est enregistrée au passage (PUT, validée par le
    # serveur) ; « Lire la page » propose nom et pitch ; l'ambiance montre 4 directions, leurs vignettes sont DEVISÉES
    # avant le tir ; la synthèse est sans IA (gratuite) ou par l'IA (devis, sur demande) ; la proposition se corrige
    # puis se VALIDE — rien n'est écrit dans le persona avant. Aucun window.prompt/confirm.
    'var DZ_ONB_ETAPES=[["produit",[["nom","t"],["url","u"],["pitch","a"],["produits","l"]]],'
    '["audience",[["qui","t"],["ou","l"],["aime","l"],["rejette","l"]]],'
    '["personnage",[["type","c"],["nom","t"],["description","a"]]],'
    '["ton",[["serieux_meme","n"],["oracle_copain","n"],["sobre_exuberant","n"],["garder","l"],["rejeter","l"],["langues","l"],["catchphrase","t"],["handle","t"]]],'
    '["ambiance",[["notes","a"]]],["references",[["images","l"]]],'
    '["interdits",[["sujets","l"],["mots","l"],["couleurs","l"],["concurrents","l"],["legal","a"]]],["synthese",[]]];'
    'function DzOnboardingPersona({espace:esp,nom:nomEsp,fermer:fermer}){const[st,maj]=x.useReducer(function(o,n){return Object.assign({},o,n)},'
    '{i:0,d:null,f:{},prop:null,busy:!1,err:"",msg:""});'
    'var base="/api/espaces/"+encodeURIComponent(esp)+"/onboarding";'
    'function charger(i){return fetch(base).then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);return r.json()}).then(function(d){'
    'var k=DZ_ONB_ETAPES[i==null?st.i:i][0];maj({d:d,f:Object.assign({},d.etapes[k]||{}),prop:st.prop||d.proposition})})'
    '.catch(function(e){maj({err:String(e&&e.message||e)})})}'
    'x.useEffect(function(){charger(0)},[esp]);'
    'function faire(p,ok){maj({busy:!0,err:"",msg:""});return p.then(function(v){maj({busy:!1});ok&&ok(v);return v},function(e){maj({busy:!1,err:String(e&&e.message||e)})})}'
    'var et=DZ_ONB_ETAPES[st.i],k=et[0];'
    'function enregistrer(){if(k==="synthese")return Promise.resolve();var v={};et[1].forEach(function(c){if(c[0]in st.f)v[c[0]]=c[1]==="l"&&!Array.isArray(st.f[c[0]])?liste(st.f[c[0]]):st.f[c[0]]});'
    'if(k==="ambiance"){v.choisies=st.f.choisies||[];v.rejetees=st.f.rejetees||[]}'
    'return dzEspEnvoyer(base+"/"+k,"PUT",v)}'
    'function aller(j){faire(enregistrer().then(function(){return fetch(base).then(function(r){return r.json()})}),function(d){'
    'maj({i:j,d:d,f:Object.assign({},d.etapes[DZ_ONB_ETAPES[j][0]]||{})})})}'
    'function poser(c,v){var f=Object.assign({},st.f);f[c]=v;maj({f:f})}'
    'function liste(t){return String(t||"").split(",").map(function(x2){return x2.trim()}).filter(Boolean)}'
    'var champ={fontSize:12.5,padding:"6px 8px",background:"var(--bg-panel-2)",color:"var(--ink-strong)",border:"1px solid var(--stroke)",borderRadius:4,width:"100%",boxSizing:"border-box"};'
    'var bt={fontSize:12,padding:"6px 12px",background:"var(--bg-panel-2)",color:"var(--ink-strong)",border:"1px solid var(--stroke)",borderRadius:4,cursor:"pointer"};'
    'var btP=Object.assign({},bt,{background:"var(--brand)",borderColor:"var(--brand)",color:"#fff"});'
    'function usd(dv){var t=dv&&dv.total_usd;return t>0?(((window.DzModelesIA&&window.DzModelesIA.prixUsd)||dzPrixUsd)(t,"")):""}'
    'function rendreChamp(c){var n=c[0],g=c[1],v=st.f[n],lab=dzT("espaces.onb.champ."+k+"."+n);'
    'var ctl=g==="l"?r.jsx("input",{"aria-label":lab,value:Array.isArray(v)?v.join(", "):v||"",placeholder:dzT("espaces.onb.virgules"),'
    'onChange:function(ev){poser(n,ev.target.value)},style:champ})'
    ':g==="a"?r.jsx("textarea",{"aria-label":lab,rows:3,value:v||"",onChange:function(ev){poser(n,ev.target.value)},style:champ})'
    ':g==="n"?r.jsxs("div",{style:{display:"flex",gap:8,alignItems:"center"},children:[r.jsx("span",{style:{fontSize:11,color:"var(--ink-muted)",minWidth:90},children:dzT("espaces.onb.curseur."+n+".bas")}),'
    'r.jsx("input",{type:"range",min:0,max:100,"aria-label":lab,value:v==null?50:v,onChange:function(ev){poser(n,Number(ev.target.value))},style:{flex:1}}),'
    'r.jsx("span",{style:{fontSize:11,color:"var(--ink-muted)",minWidth:90,textAlign:"right"},children:dzT("espaces.onb.curseur."+n+".haut")})]})'
    ':g==="c"?r.jsx("select",{"aria-label":lab,value:v||"aucun",onChange:function(ev){poser(n,ev.target.value)},style:champ,children:["mascotte","humain","abstrait","aucun"].map(function(o){'
    'return r.jsx("option",{value:o,children:dzT("espaces.onb.personnage."+o)},o)})})'
    ':r.jsxs("div",{style:{display:"flex",gap:6},children:[r.jsx("input",{"aria-label":lab,value:v||"",onChange:function(ev){poser(n,ev.target.value)},style:champ}),'
    'g==="u"&&r.jsx("button",{type:"button",style:bt,disabled:st.busy||!v,onClick:function(){faire(dzEspEnvoyer(base+"/lire-url","POST",{url:v}),function(j){'
    'var f=Object.assign({},st.f);if(j.nom&&!f.nom)f.nom=j.nom;if(j.pitch&&!f.pitch)f.pitch=j.pitch;maj({f:f,msg:dzT("espaces.onb.page_lue")})})},children:dzT("espaces.onb.lire_page")})]});'
    'return r.jsxs("label",{style:{display:"flex",flexDirection:"column",gap:4},children:[r.jsx("span",{style:{fontSize:11.5,color:"var(--ink-soft)"},children:lab}),ctl]},n)}'
    'function ambiance(){var dirs=st.d&&st.d.directions||[],ch=st.f.choisies||[],rj=st.f.rejetees||[];'
    'function bascule(id,cle,autre){var a=(st.f[cle]||[]).slice(),b=(st.f[autre]||[]).filter(function(x2){return x2!==id});'
    'a.indexOf(id)>=0?a=a.filter(function(x2){return x2!==id}):a.push(id);var f=Object.assign({},st.f);f[cle]=a;f[autre]=b;maj({f:f})}'
    'var dv=st.d&&st.d.devis&&st.d.devis.vignettes;'
    'return r.jsxs("div",{style:{display:"flex",flexDirection:"column",gap:10},children:[r.jsx("p",{style:{margin:0,fontSize:12,color:"var(--ink-soft)"},children:dzT("espaces.onb.ambiance_aide")}),'
    'r.jsx("div",{style:{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(180px,1fr))",gap:10},children:dirs.map(function(x2){var on=ch.indexOf(x2.id)>=0,non=rj.indexOf(x2.id)>=0;'
    'return r.jsxs("div",{"data-dz-onb-direction":x2.id,style:{border:"1px solid "+(on?"var(--green)":non?"var(--red)":"var(--stroke)"),borderRadius:6,padding:8,display:"flex",flexDirection:"column",gap:6,background:"var(--bg-panel)"},children:['
    'x2.image?r.jsx("img",{src:"/api/images/"+encodeURIComponent(x2.image),alt:x2.titre,style:{width:"100%",aspectRatio:"1",objectFit:"cover",borderRadius:4}})'
    ':r.jsx("div",{style:{width:"100%",aspectRatio:"1",borderRadius:4,background:"var(--bg-panel-2)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:11,color:"var(--ink-muted)"},children:dzT("espaces.onb.sans_vignette")}),'
    'r.jsx("strong",{style:{fontSize:12.5,color:"var(--ink-strong)"},children:dzT("espaces.onb.direction."+x2.id)}),'
    'r.jsx("span",{style:{fontSize:11,color:"var(--ink-soft)"},children:x2.style}),'
    'r.jsxs("div",{style:{display:"flex",gap:6},children:[r.jsx("button",{type:"button",style:on?btP:bt,onClick:function(){bascule(x2.id,"choisies","rejetees")},children:dzT("espaces.onb.choisir")}),'
    'r.jsx("button",{type:"button",style:bt,onClick:function(){bascule(x2.id,"rejetees","choisies")},children:dzT(non?"espaces.onb.rejetee":"espaces.onb.rejeter")})]})]},x2.id)})}),'
    'r.jsx("div",{children:r.jsx("button",{type:"button","data-dz-onb-vignettes":"1",style:bt,disabled:st.busy||!(st.d&&st.d.voies&&st.d.voies.vignettes),'
    'title:st.d&&st.d.voies&&!st.d.voies.vignettes?dzT("ia.cle.a_ajouter",{cle:"FAL_KEY"}):"",onClick:function(){faire(enregistrer().then(function(){'
    'return dzEspEnvoyer(base+"/vignettes","POST",{})}),function(d){maj({d:Object.assign({},st.d,{directions:d.directions})})})},'
    'children:dzT("espaces.onb.generer_vignettes",{prix:st.d&&st.d.voies&&st.d.voies.vignettes?usd(dv)||dzT("ia.prix.a_mesurer"):dzT("ia.cle.a_ajouter",{cle:"FAL_KEY"})})})})]})}'
    'function references(){var im=st.f.images||[];return r.jsxs("div",{style:{display:"flex",flexDirection:"column",gap:8},children:['
    'r.jsx("p",{style:{margin:0,fontSize:12,color:"var(--ink-soft)"},children:dzT("espaces.onb.references_aide")}),'
    'r.jsx("div",{style:{display:"flex",gap:8,flexWrap:"wrap"},children:im.map(function(n){return r.jsxs("div",{style:{position:"relative"},children:['
    'r.jsx("img",{src:"/api/images/"+encodeURIComponent(n),alt:n,style:{width:84,height:84,objectFit:"cover",borderRadius:4,border:"1px solid var(--stroke)"}}),'
    'r.jsx("button",{type:"button","aria-label":dzT("espaces.onb.retirer"),title:dzT("espaces.onb.retirer"),style:Object.assign({},bt,{position:"absolute",top:2,right:2,padding:"0 6px"}),'
    'onClick:function(){poser("images",im.filter(function(x2){return x2!==n}))},children:"×"})]},n)})}),'
    'r.jsx("input",{type:"file",accept:"image/*",multiple:!0,"aria-label":dzT("espaces.onb.ajouter_images"),onChange:function(ev){var fs=[].slice.call(ev.target.files||[]);'
    'faire(Promise.all(fs.map(function(fi){var fd=new FormData();fd.append("file",fi);return fetch("/api/images/upload",{method:"POST",body:fd}).then(function(r2){'
    'if(!r2.ok)throw new Error("HTTP "+r2.status);return r2.json()})})),function(rs2){poser("images",im.concat(rs2.map(function(j){return j.filename}).filter(Boolean)))})}})]})}'
    'function synthese(){var pr=st.prop,dv=st.d&&st.d.devis&&st.d.devis.llm;'
    'function pp(chemin,v){var n=JSON.parse(JSON.stringify(pr));var o=n;for(var a=0;a<chemin.length-1;a++)o=o[chemin[a]]=o[chemin[a]]||{};o[chemin[chemin.length-1]]=v;maj({prop:n})}'
    'function get(chemin){var o=pr;for(var a=0;a<chemin.length&&o;a++)o=o[chemin[a]];return o}'
    'function propre(){var n=JSON.parse(JSON.stringify(pr));CH.forEach(function(c){if(c[1]!=="l")return;var ch=c[0].split("."),o=n;'
    'for(var a=0;a<ch.length-1;a++)o=o[ch[a]]=o[ch[a]]||{};var v=o[ch[ch.length-1]];if(typeof v==="string")o[ch[ch.length-1]]=liste(v)});return n}'
    'var CH=[["display_name","t"],["identite.mission","a"],["vibe_keywords","l"],["default_negative_prompt","a"],["default_hashtags_pool","l"],'
    '["ecran.name","t"],["ecran.handle","t"],["ecran.role","t"],["ecran.catchphrase","t"],["ecran.tone","l"],["ecran.preferred","l"],["ecran.banned","l"],["visuel.style_ecrit","a"]];'
    'return r.jsxs("div",{style:{display:"flex",flexDirection:"column",gap:10},children:[r.jsx("p",{style:{margin:0,fontSize:12,color:"var(--ink-soft)"},children:dzT("espaces.onb.synthese_aide")}),'
    'r.jsxs("div",{style:{display:"flex",gap:8,flexWrap:"wrap"},children:[r.jsx("button",{type:"button","data-dz-onb-synthese":"manuelle",style:bt,disabled:st.busy,'
    'onClick:function(){faire(dzEspEnvoyer(base+"/synthese","POST",{}),function(p2){maj({prop:p2})})},children:dzT("espaces.onb.synthese_manuelle")}),'
    'r.jsx("button",{type:"button","data-dz-onb-synthese":"llm",style:bt,disabled:st.busy||!(st.d&&st.d.voies&&st.d.voies.llm),'
    'onClick:function(){faire(dzEspEnvoyer(base+"/synthese","POST",{llm:!0}),function(p2){maj({prop:p2,msg:p2.note||""})})},children:dzT("espaces.onb.synthese_llm",{prix:st.d&&st.d.voies&&st.d.voies.llm?usd(dv)||dzT("ia.prix.a_mesurer"):dzT("espaces.onb.sans_llm")})})]}),'
    'pr&&r.jsxs("div",{"data-dz-onb-proposition":"1",style:{display:"flex",flexDirection:"column",gap:8},children:[CH.map(function(c){var ch=c[0].split("."),v=get(ch),lab=dzT("espaces.onb.prop."+c[0].replace(".","_"));'
    'return r.jsxs("label",{style:{display:"flex",flexDirection:"column",gap:4},children:[r.jsx("span",{style:{fontSize:11.5,color:"var(--ink-soft)"},children:lab}),'
    'c[1]==="l"?r.jsx("input",{"aria-label":lab,value:Array.isArray(v)?v.join(", "):v||"",onChange:function(ev){pp(ch,ev.target.value)},style:champ})'
    ':c[1]==="a"?r.jsx("textarea",{"aria-label":lab,rows:2,value:v||"",onChange:function(ev){pp(ch,ev.target.value)},style:champ})'
    ':r.jsx("input",{"aria-label":lab,value:v||"",onChange:function(ev){pp(ch,ev.target.value)},style:champ})]},c[0])}),'
    'r.jsx("div",{children:r.jsx("button",{type:"button","data-dz-onb-valider":"1",style:btP,disabled:st.busy,onClick:function(){faire(dzEspEnvoyer(base+"/valider","POST",{proposition:propre()}),'
    'function(){dzEspSignal();maj({msg:dzT("espaces.onb.valide")});fermer&&setTimeout(fermer,900)})},children:dzT("espaces.onb.valider")})})]})]})}'
    'return r.jsx("div",{role:"dialog","aria-modal":"true","aria-label":dzT("espaces.onb.titre",{nom:nomEsp}),"data-dz-onb":esp,'
    'style:{position:"fixed",inset:0,background:"rgba(0,0,0,.55)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:60},'
    'onKeyDown:function(ev){ev.key==="Escape"&&fermer&&fermer()},children:r.jsxs("div",{style:{width:"min(760px,94vw)",maxHeight:"90vh",overflow:"auto",background:"var(--bg-panel)",'
    'border:"1px solid var(--stroke)",borderRadius:8,padding:18,display:"flex",flexDirection:"column",gap:12},children:['
    'r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:10},children:[r.jsx("h2",{style:{margin:0,fontSize:16,color:"var(--ink-strong)",flex:1},'
    'children:dzT("espaces.onb.titre",{nom:nomEsp})}),r.jsx("button",{type:"button",style:bt,"aria-label":dzT("espaces.onb.fermer"),onClick:fermer,children:dzT("espaces.onb.fermer")})]}),'
    'r.jsx("ol",{style:{display:"flex",gap:4,listStyle:"none",padding:0,margin:0,flexWrap:"wrap"},children:DZ_ONB_ETAPES.map(function(e2,j){'
    'return r.jsx("li",{children:r.jsx("button",{type:"button","aria-current":j===st.i?"step":void 0,disabled:st.busy,onClick:function(){j!==st.i&&aller(j)},'
    'style:Object.assign({},bt,{fontSize:11,padding:"3px 8px"},j===st.i?{borderColor:"var(--cyan)",color:"var(--cyan)"}:{}),children:(j+1)+". "+dzT("espaces.onb.etape."+e2[0])})},e2[0])})}),'
    'r.jsx("h3",{style:{margin:0,fontSize:14,color:"var(--ink-strong)"},children:dzT("espaces.onb.etape."+k)}),'
    'r.jsx("p",{style:{margin:0,fontSize:12,color:"var(--ink-soft)"},children:dzT("espaces.onb.aide."+k)}),'
    'st.err&&r.jsx("div",{role:"alert",style:{fontSize:12,color:"var(--red)"},children:st.err}),'
    'st.msg&&r.jsx("div",{role:"status",style:{fontSize:12,color:"var(--green)"},children:st.msg}),'
    '!st.d?r.jsx("div",{style:{fontSize:12,color:"var(--ink-muted)"},children:dzT("espaces.etat.chargement")})'
    ':k==="ambiance"?r.jsxs(r.Fragment,{children:[ambiance(),et[1].map(rendreChamp)]}):k==="references"?references():k==="synthese"?synthese()'
    ':r.jsx("div",{style:{display:"flex",flexDirection:"column",gap:10},children:et[1].map(rendreChamp)}),'
    'r.jsxs("div",{style:{display:"flex",justifyContent:"space-between",marginTop:4},children:[r.jsx("button",{type:"button",style:bt,disabled:st.busy||st.i===0,'
    'onClick:function(){aller(st.i-1)},children:dzT("espaces.onb.precedent")}),'
    'st.i<DZ_ONB_ETAPES.length-1&&r.jsx("button",{type:"button","data-dz-onb-suivant":"1",style:btP,disabled:st.busy,onClick:function(){aller(st.i+1)},children:dzT("espaces.onb.suivant")})]})]})})}'
)

# t206 (Espaces de marque E6) : `DzIdentite`, l'identité visuelle d'un espace (logo, mascotte, produits, palette,
# typographies, style écrit sans nom d'artiste, ADN des prompts, planche composée puis validée). Le logo d'un persona
# sert à ses contenus : il n'habille jamais l'application.
AIDES_IDV = (
    'var DZ_IDV_ADN=[["touches_sujet","l"],["touches_decor","l"],["decor_defaut","t"],["reperes","v"],["eclairages","l"],["explication","t"]];'
    'function DzIdentite({espace:esp,nom:nomEsp,fermer:fermer}){const[st,maj]=x.useReducer(function(o,n){return Object.assign({},o,n)},'
    '{d:null,pal:[],typos:[],style:"",adn:{},busy:!1,err:"",msg:"",v:0});'
    'var base="/api/espaces/"+encodeURIComponent(esp)+"/identite";'
    'function remplir(d,tout){if(!tout){maj({d:d,v:Date.now()});return}var a=d.adn||{},t={};DZ_IDV_ADN.forEach(function(c){var v=a[c[0]];'
    't[c[0]]=v==null?"":Array.isArray(v)?v.join(c[1]==="v"?", ":"\\n"):String(v)});'
    'maj({d:d,v:Date.now(),pal:(d.palette||[]).map(function(c){return Object.assign({},c)}),typos:(d.typographies||[]).map(function(c){return Object.assign({},c)}),'
    'style:d.style_ecrit||"",adn:t})}'
    'function charger(){return fetch(base).then(function(r2){if(!r2.ok)throw new Error("HTTP "+r2.status);return r2.json()}).then(function(d){remplir(d,!0)})'
    '.catch(function(e){maj({err:String(e&&e.message||e)})})}'
    'x.useEffect(function(){charger()},[esp]);'
    'function faire(p,msg,tout){maj({busy:!0,err:"",msg:""});return p.then(function(j){var v=j&&j.identite||j;v&&v.palette&&remplir(v,tout);maj({busy:!1,msg:msg||""})},'
    'function(e){maj({busy:!1,err:String(e&&e.message||e)})})}'
    'function envoyer(g,fs){faire(fs.reduce(function(p,fi){return p.then(function(){var fd=new FormData();fd.append("file",fi);'
    'return fetch(base+"/images/"+g,{method:"POST",body:fd}).then(function(r2){return r2.json().catch(function(){return{}}).then(function(j){'
    'if(!r2.ok)throw new Error(j&&j.detail?String(j.detail):"HTTP "+r2.status);return j})})})},Promise.resolve(null)),"",!1)}'
    'function lignes(t){return String(t||"").split("\\n").map(function(s2){return s2.trim()}).filter(Boolean)}'
    'function virg(t){return String(t||"").split(",").map(function(s2){return s2.trim()}).filter(Boolean)}'
    'function enregistrer(){var a={};DZ_IDV_ADN.forEach(function(c){var v=String(st.adn[c[0]]||"");if(!v.trim())return;'
    'a[c[0]]=c[1]==="t"?v.trim():c[1]==="v"?virg(v):lignes(v)});'
    'faire(dzEspEnvoyer(base,"PUT",{palette:st.pal.filter(function(c){return c.hex}),typographies:st.typos.filter(function(t){return(t.nom||"").trim()}),'
    'style_ecrit:st.style,adn:a}),dzT("espaces.idv.enregistre"),!0)}'
    'function pal(i,o){maj({pal:st.pal.map(function(c,j){return j===i?Object.assign({},c,o):c})})}'
    'function tp(i,o){maj({typos:st.typos.map(function(c,j){return j===i?Object.assign({},c,o):c})})}'
    'var champ={fontSize:12.5,padding:"6px 8px",background:"var(--bg-panel-2)",color:"var(--ink-strong)",border:"1px solid var(--stroke)",borderRadius:4,width:"100%",boxSizing:"border-box"};'
    'var bt={fontSize:12,padding:"6px 12px",background:"var(--bg-panel-2)",color:"var(--ink-strong)",border:"1px solid var(--stroke)",borderRadius:4,cursor:"pointer"};'
    'var btP=Object.assign({},bt,{background:"var(--brand)",borderColor:"var(--brand)",color:"#fff"});'
    'var titre={fontSize:12.5,fontWeight:600,color:"var(--ink-strong)"},aide={margin:0,fontSize:11.5,color:"var(--ink-soft)"};'
    'var d=st.d;function img(n){return base+"/fichier/"+encodeURIComponent(n)+"?v="+st.v}'
    'function vignettes(g){var noms=g==="logo"?(d.logo?[d.logo]:[]):d[g]||[],max=(d.plafonds||{})[g]||1;'
    'return r.jsxs("div",{"data-dz-idv-genre":g,style:{display:"flex",flexDirection:"column",gap:6},children:['
    'r.jsx("div",{style:titre,children:dzT("espaces.idv.genre."+g)+" ("+noms.length+"/"+max+")"}),'
    'g==="logo"&&r.jsx("p",{style:aide,children:dzT("espaces.idv.logo_aide")}),'
    'r.jsxs("div",{style:{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"},children:[noms.map(function(n){return r.jsxs("div",{style:{position:"relative"},children:['
    'r.jsx("img",{src:img(n),alt:dzT("espaces.idv.genre."+g),style:{width:84,height:84,objectFit:"contain",background:"var(--bg-panel-2)",borderRadius:4,border:"1px solid var(--stroke)"}}),'
    'r.jsx("button",{type:"button","aria-label":dzT("espaces.onb.retirer"),title:dzT("espaces.onb.retirer"),disabled:st.busy,'
    'style:Object.assign({},bt,{position:"absolute",top:2,right:2,padding:"0 6px"}),onClick:function(){faire(dzEspEnvoyer(base+"/images/"+encodeURIComponent(n),"DELETE"),"",!1)},children:"×"})]},"im:"+n)}),'
    '(g==="logo"||noms.length<max)&&r.jsxs("label",{style:Object.assign({},bt,{display:"inline-flex",alignItems:"center",opacity:st.busy?.6:1}),children:['
    'dzT(g==="logo"&&noms.length?"espaces.idv.remplacer":"espaces.idv.ajouter"),'
    'r.jsx("input",{type:"file",accept:"image/png,image/jpeg,image/webp",multiple:g!=="logo","data-dz-idv-fichier":g,"aria-label":dzT("espaces.idv.genre."+g),'
    'style:{display:"none"},disabled:st.busy,onChange:function(ev){var fs=[].slice.call(ev.target.files||[]);ev.target.value="";fs.length&&envoyer(g,fs)}})]})]})]},"g:"+g)}'
    'function palette(){return r.jsxs("div",{"data-dz-idv-palette":"1",style:{display:"flex",flexDirection:"column",gap:6},children:['
    'r.jsx("div",{style:titre,children:dzT("espaces.idv.palette")}),'
    'st.pal.map(function(c,i){return r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center"},children:['
    'r.jsx("input",{type:"color",value:/^#[0-9a-fA-F]{6}$/.test(c.hex||"")?c.hex:"#000000","aria-label":dzT("espaces.idv.couleur"),'
    'onChange:function(ev){pal(i,{hex:ev.target.value.toUpperCase()})},style:{width:34,height:28,padding:0,border:"1px solid var(--stroke)",background:"none",flex:"0 0 auto"}}),'
    'r.jsx("input",{value:c.hex||"","aria-label":dzT("espaces.idv.hex"),onChange:function(ev){pal(i,{hex:ev.target.value})},style:Object.assign({},champ,{width:96,flex:"0 0 auto",fontFamily:"var(--f-mono)"})}),'
    'r.jsx("input",{value:c.role||"",placeholder:dzT("espaces.idv.role"),"aria-label":dzT("espaces.idv.role"),onChange:function(ev){pal(i,{role:ev.target.value})},style:champ}),'
    'r.jsx("button",{type:"button",style:bt,"aria-label":dzT("espaces.onb.retirer"),onClick:function(){maj({pal:st.pal.filter(function(_c,j){return j!==i})})},children:"×"})]},"pal:"+i)}),'
    'st.pal.length<12&&r.jsx("div",{children:r.jsx("button",{type:"button",style:bt,onClick:function(){maj({pal:st.pal.concat([{hex:"#3B82F6",role:""}])})},'
    'children:dzT("espaces.idv.palette_ajouter")})})]})}'
    'function typos(){return r.jsxs("div",{style:{display:"flex",flexDirection:"column",gap:6},children:['
    'r.jsx("div",{style:titre,children:dzT("espaces.idv.typos")}),'
    'st.typos.map(function(c,i){return r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center"},children:['
    'r.jsx("input",{value:c.nom||"",placeholder:dzT("espaces.idv.typo_nom"),"aria-label":dzT("espaces.idv.typo_nom"),onChange:function(ev){tp(i,{nom:ev.target.value})},style:champ}),'
    'r.jsx("input",{value:c.usage||"",placeholder:dzT("espaces.idv.typo_usage"),"aria-label":dzT("espaces.idv.typo_usage"),onChange:function(ev){tp(i,{usage:ev.target.value})},style:champ}),'
    'r.jsx("button",{type:"button",style:bt,"aria-label":dzT("espaces.onb.retirer"),onClick:function(){maj({typos:st.typos.filter(function(_c,j){return j!==i})})},children:"×"})]},"typo:"+i)}),'
    'st.typos.length<6&&r.jsx("div",{children:r.jsx("button",{type:"button",style:bt,onClick:function(){maj({typos:st.typos.concat([{nom:"",usage:""}])})},'
    'children:dzT("espaces.idv.typo_ajouter")})})]})}'
    'function adn(){var ef=d.adn_effectif||{};return r.jsxs("details",{"data-dz-idv-adn":"1",style:{display:"flex",flexDirection:"column",gap:6},children:['
    'r.jsx("summary",{style:Object.assign({},titre,{cursor:"pointer"}),children:dzT("espaces.idv.adn")}),'
    'r.jsx("p",{style:aide,children:dzT("espaces.idv.adn_aide")}),'
    'DZ_IDV_ADN.map(function(c){var e=ef[c[0]],ph=Array.isArray(e)?e.join(c[1]==="v"?", ":"\\n"):e||"",lab=dzT("espaces.idv.adn."+c[0]);'
    'return r.jsxs("label",{style:{display:"flex",flexDirection:"column",gap:3,fontSize:12,color:"var(--ink-soft)",marginTop:6},children:[lab,'
    'c[1]==="l"?r.jsx("textarea",{rows:3,value:st.adn[c[0]]||"",placeholder:ph,"aria-label":lab,onChange:function(ev){var a=Object.assign({},st.adn);a[c[0]]=ev.target.value;maj({adn:a})},style:champ})'
    ':r.jsx("input",{value:st.adn[c[0]]||"",placeholder:ph,"aria-label":lab,onChange:function(ev){var a=Object.assign({},st.adn);a[c[0]]=ev.target.value;maj({adn:a})},style:champ})]},"adn:"+c[0])})]})}'
    'function kit(){var k=d.kit||{},etat=k.depuis_identite?"identite":k.branding?"branding":"autre";'
    'return r.jsxs("div",{"data-dz-idv-kit":etat,style:{display:"flex",flexDirection:"column",gap:6},children:['
    'r.jsx("div",{style:titre,children:dzT("espaces.idv.kit")}),r.jsx("p",{style:aide,children:dzT("espaces.idv.kit_aide")}),'
    'r.jsxs("div",{style:{display:"flex",gap:8,alignItems:"center",fontSize:12,color:"var(--ink-soft)"},children:['
    'r.jsx("span",{"aria-hidden":"true",style:{width:14,height:14,borderRadius:3,background:k.brand_color,border:"1px solid var(--stroke)"}}),'
    'r.jsx("span",{"aria-hidden":"true",style:{width:14,height:14,borderRadius:3,background:k.accent_color,border:"1px solid var(--stroke)"}}),'
    'r.jsx("span",{children:dzT("espaces.idv.kit_etat."+etat,{nom:k.name||""})})]}),'
    'r.jsx("div",{children:r.jsx("button",{type:"button","data-dz-idv-kit-creer":"1",style:bt,disabled:st.busy,'
    'onClick:function(){faire(dzEspEnvoyer(base+"/kit","POST"),dzT("espaces.idv.kit_fait"),!1)},children:dzT(k.depuis_identite?"espaces.idv.kit_maj":"espaces.idv.kit_creer")})})]})}'
    'function planche(){var e=d.etat_planche||"absente",pl=d.planche||{};return r.jsxs("div",{"data-dz-idv-planche":e,style:{display:"flex",flexDirection:"column",gap:6},children:['
    'r.jsx("div",{style:titre,children:dzT("espaces.idv.planche")}),r.jsx("p",{style:aide,children:dzT("espaces.idv.planche_aide")}),'
    'r.jsx("div",{role:"status",style:{fontSize:12,color:e==="validee"?"var(--green)":e==="perimee"?"var(--red)":"var(--ink-soft)"},children:dzT("espaces.idv.planche_etat."+e)}),'
    'pl.fichier&&e!=="absente"&&r.jsx("img",{src:img(pl.fichier),alt:dzT("espaces.idv.planche"),style:{width:"100%",borderRadius:4,border:"1px solid var(--stroke)"}}),'
    'r.jsxs("div",{style:{display:"flex",gap:8},children:[r.jsx("button",{type:"button","data-dz-idv-composer":"1",style:bt,disabled:st.busy,'
    'onClick:function(){faire(dzEspEnvoyer(base+"/planche","POST"),"",!1)},children:dzT(e==="absente"?"espaces.idv.composer":"espaces.idv.recomposer")}),'
    'e==="a_valider"&&r.jsx("button",{type:"button","data-dz-idv-valider":"1",style:btP,disabled:st.busy,'
    'onClick:function(){faire(dzEspEnvoyer(base+"/planche/valider","POST"),dzT("espaces.idv.planche_validee"),!1)},children:dzT("espaces.idv.valider")})]})]})}'
    'return r.jsx("div",{role:"dialog","aria-modal":"true","aria-label":dzT("espaces.idv.titre",{nom:nomEsp}),"data-dz-idv":esp,'
    'style:{position:"fixed",inset:0,background:"rgba(0,0,0,.55)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:60},'
    'onKeyDown:function(ev){ev.key==="Escape"&&fermer&&fermer()},children:r.jsxs("div",{style:{width:"min(820px,94vw)",maxHeight:"90vh",overflow:"auto",background:"var(--bg-panel)",'
    'border:"1px solid var(--stroke)",borderRadius:8,padding:18,display:"flex",flexDirection:"column",gap:14},children:['
    'r.jsxs("div",{style:{display:"flex",justifyContent:"space-between",alignItems:"center",gap:8},children:['
    'r.jsx("h2",{style:{margin:0,fontSize:16,color:"var(--ink-strong)"},children:dzT("espaces.idv.titre",{nom:nomEsp})}),'
    'r.jsx("button",{type:"button",style:bt,"aria-label":dzT("espaces.onb.fermer"),onClick:fermer,children:dzT("espaces.onb.fermer")})]}),'
    'st.err&&r.jsx("div",{role:"alert",style:{fontSize:12,color:"var(--red)"},children:st.err}),'
    'st.msg&&r.jsx("div",{role:"status",style:{fontSize:12,color:"var(--green)"},children:st.msg}),'
    '!d?r.jsx("div",{style:{fontSize:12,color:"var(--ink-muted)"},children:dzT("espaces.etat.chargement")}):r.jsxs(r.Fragment,{children:['
    'vignettes("logo"),vignettes("mascotte"),vignettes("produits"),r.jsx("p",{style:aide,children:dzT("espaces.idv.references_aide")}),'
    'palette(),typos(),'
    'r.jsxs("label",{style:{display:"flex",flexDirection:"column",gap:4},children:[r.jsx("span",{style:titre,children:dzT("espaces.idv.style")}),'
    'r.jsx("textarea",{rows:3,value:st.style,"aria-label":dzT("espaces.idv.style"),placeholder:dzT("espaces.idv.style_exemple"),onChange:function(ev){maj({style:ev.target.value})},style:champ}),'
    'r.jsx("span",{style:aide,children:dzT("espaces.idv.style_aide")})]}),'
    'adn(),'
    'r.jsx("div",{children:r.jsx("button",{type:"button","data-dz-idv-enregistrer":"1",style:btP,disabled:st.busy,onClick:enregistrer,children:dzT("espaces.action.enregistrer")})}),'
    'kit(),planche()]})]})})}'
)

RAIL = 'function tg({view:e,setView:t,collapsed:n,setCollapsed:o}){const i=ji();'
CARTE = ('r.jsxs("div",{style:{marginTop:10,display:"flex",alignItems:"center",justifyContent:"space-between"},'
         'children:[r.jsx("span",{style:{fontFamily:"var(--f-mono)",fontSize:10,color:"var(--ink-muted)"},children:"v2.8.0"})')
SHELL = ('const[z,N]=x.useState(()=>(rm||[]).slice()),[P,j]=x.useState("deepotus");'
         'function E(F){N(I=>I.some(M=>M.id===F.id)?I.map(M=>M.id===F.id?{...M,...F}:M):[...I,F]),j(F.id)}')
SHELL_APRES = (
    'const[z,N]=x.useState(()=>(rm||[]).slice()),[P,j]=x.useState("deepotus");'
    'function E(F){N(I=>I.some(M=>M.id===F.id)?I.map(M=>M.id===F.id?{...M,...F}:M):[...I,F]),j(F.id),dzEspPersonaEcrire(F)}'
    'function dzJ(F){j(F);var f=z.find(function(M){return M.id===F});f&&dzEspPersonaEcrire(f)}'
    'x.useEffect(function(){var vivant=!0;function go(){dzEspPersona(function(e,p){if(!vivant)return;'
    'var f=p&&p.ecran&&p.ecran.id?p.ecran:e.id==="deepotus"?null:Object.assign(rs(),{id:e.id,name:p&&p.display_name||e.nom});'
    'if(!f){j("deepotus");return}'
    'N(function(I){return I.some(function(M){return M.id===f.id})?I.map(function(M){return M.id===f.id?Object.assign({},M,f):M})'
    ':I.concat([f])});j(f.id)})}go();function sur(){go();_()}window.addEventListener("deepotus:espace-refresh",sur);'
    'return function(){vivant=!1;window.removeEventListener("deepotus:espace-refresh",sur)}},[]);'
)

PAIRES = [
    (RAIL, AIDES + AIDES_IDV + RAIL),                                                  # S1
    (CARTE, 'r.jsx(DzEspaceSel,{setView:t}),' + CARTE),                                # S2
    (SHELL, SHELL_APRES),                                                              # S3
    ('const ym=["diag","coffre","appareils","keys","accounts","personas",',            # S4
     'const ym=["diag","coffre","appareils","keys","accounts","personas","espaces",'),
    ('{k:"personas",l:dzT("reglages.onglet.personas")},',                              # S5
     '{k:"personas",l:dzT("reglages.onglet.personas")},{k:"espaces",l:dzT("espaces.reglages.onglet")},'),
    ('s==="transfert"&&r.jsx(DzTransfert,{})]}),r.jsx(Au,{open:!!l,',                  # S6
     's==="transfert"&&r.jsx(DzTransfert,{}),s==="espaces"&&r.jsx(DzEspaces,{})]}),r.jsx(Au,{open:!!l,'),
    ('transfert:dzT("reglages.onglet.transfert")};return(e&&dzRubriques',              # S7
     'transfert:dzT("reglages.onglet.transfert"),espaces:dzT("espaces.reglages.onglet")};return(e&&dzRubriques'),
    # t204 — S8 le mappeur des posts garde l'espace et les comptes ; S9 l'enregistrement différé les envoie ;
    # S10 l'éditeur montre les comptes de l'espace du post, au-dessus des canaux
    ('delegueA:e.delegue_a||null}}',                                                    # S8
     'delegueA:e.delegue_a||null,espaceId:e.espace_id||"deepotus",comptes:e.comptes||[]}}'),
    ('"channels"in U&&(T.channels=U.channels),',                                        # S9
     '"channels"in U&&(T.channels=U.channels),"comptes"in U&&(T.comptes=U.comptes),'),
    ('r.jsx(ie,{label:dzT("scheduler.post.canaux"),',                                   # S10
     'r.jsx(DzPostComptes,{post:e,onChange:s}),r.jsx(ie,{label:dzT("scheduler.post.canaux"),'),
    # t208 — S11 l'exemple des notes du générateur Quick ne cite plus le jeton Deepotus ; il reste en ANGLAIS (décision
    # L2 : ce texte part au modèle, qui attend l'anglais)
    ('placeholder:"e.g. fits the $DEEPOTUS Pyth-feed announcement"',                    # S11
     'placeholder:"e.g. fits the next launch announcement"'),
]
# S3 bis : les DEUX passages de setActivePersonaId (Réglages, Onboarding) — même texte, remplacés ensemble
PERSO = ("setActivePersonaId:j,savePersona:E", "setActivePersonaId:dzJ,savePersona:E", 2)


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
    a, b, n = PERSO
    if s.count(a) != n:
        raise SystemExit(f"[{TAG}] ancre x{s.count(a)} (attendu {n}) : {a!r}")
    return s.replace(a, b)


def defaire(s: str) -> str:
    """L'inverse exact (lu par avant_dzespace dans _i18n_l1_aide)."""
    a, b, n = PERSO
    if s.count(b) != n:
        raise AssertionError(f"[{TAG}] remplacement x{s.count(b)} (attendu {n}) : {b!r}")
    s = s.replace(b, a)
    for ancre, remplace in reversed(PAIRES):
        if s.count(remplace) != 1:
            raise AssertionError(f"[{TAG}] remplacement x{s.count(remplace)} (attendu 1) : {remplace[:80]!r}")
        s = s.replace(remplace, ancre, 1)
    return s


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
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
    if neuf.count("x.useState(") != 731 or neuf.count("v2.8.0") != 4:
        raise SystemExit(f"[{TAG}] un compte figé a bougé")
    if check:
        print(f"[{TAG}] à appliquer ({len(PAIRES)} paires + {PERSO[2]} passages)")
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
