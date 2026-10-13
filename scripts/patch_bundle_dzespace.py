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
    'function dzEspSignal(){try{window.dispatchEvent(new Event("deepotus:espace-refresh"))}catch(_e){}Ji()}'
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
    'agir(dzEspEnvoyer(base(e.id),"POST",{kit_id:ev.target.value}),act)},style:champ,children:st.kits.map(function(k){'
    'return r.jsx("option",{value:k.id,"data-dz-brut":"1",children:k.name},k.id)})}),'
    'ed?r.jsxs(r.Fragment,{children:[r.jsx("button",{type:"button",disabled:st.busy||!st.editNom.trim(),style:bt,onClick:function(){'
    'agir(dzEspEnvoyer(base(e.id),"POST",{nom:st.editNom.trim()}),act).then(function(){maj({edit:""})})},'
    'children:dzT("espaces.action.enregistrer")}),r.jsx("button",{type:"button",style:bt,onClick:function(){maj({edit:""})},'
    'children:dzT("espaces.action.annuler")})]})'
    ':r.jsx("button",{type:"button",disabled:st.busy,style:bt,onClick:function(){maj({edit:e.id,editNom:e.nom})},'
    'children:dzT("espaces.action.renommer")}),'
    '!act&&!e.archive&&r.jsx("button",{type:"button","data-dz-espace-activer":e.id,disabled:st.busy,style:bt,onClick:function(){'
    'maj({busy:!0,err:""});dzEspActiver(e.id).then(function(){return charger()}).then(function(){maj({busy:!1})},'
    'function(x2){maj({busy:!1,err:String(x2&&x2.message||x2)})})},children:dzT("espaces.action.activer")}),'
    '!act&&r.jsx("button",{type:"button",disabled:st.busy,style:bt,onClick:function(){'
    'agir(dzEspEnvoyer(base(e.id)+"/archive","POST",{archive:!e.archive}))},'
    'children:dzT(e.archive?"espaces.action.desarchiver":"espaces.action.archiver")})]},e.id)})}),'
    'r.jsxs("label",{style:{fontSize:12,color:"var(--ink-soft)",display:"flex",gap:6,alignItems:"center"},children:['
    'r.jsx("input",{type:"checkbox",checked:st.arch,onChange:function(ev){maj({arch:ev.target.checked})}}),'
    'dzT("espaces.reglages.voir_archives")]}),'
    'st.actif&&r.jsx(DzComptesEspace,{espace:st.actif,nom:((st.liste||[]).find(function(e){return e.id===st.actif})||{}).nom||""},st.actif)]})}'
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
    (RAIL, AIDES + RAIL),                                                              # S1
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
