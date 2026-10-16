# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzreglages.py
"""Maillon de queue : l'OPTIMISATION DU MENU RÉGLAGES (lot « Menus : Réglages », t219-t224, 15/10/2026).

Plan docs/superpowers/plans/2026-10-15-optimisation-menus-reglages.md. Ce qu'il pose (ancres uniques, relevées le
15/10 sur 7a104ba2) :
  t219 — les pastilles de l'en-tête ouvraient Réglages › Comptes connectés. Elles faisaient `i&&i("settings")` et
  Réglages (`xm`) ne lisait sa rubrique qu'au montage (`vn("section")`, sinon « accounts ») : un Réglages déjà ouvert
  ne bougeait pas non plus.
  - R0 : `dzOuvrirReglages(section, aller)` écrit `?section=` (history.replaceState), émet `dz-reglages-section`
    {section}, puis appelle aller("settings") ; `dzReglagesEcoute(a)` écoute cet évènement (rubriques de `ym`
    seulement). Les deux sont posées devant `xm`, qui monte l'écoute dans un useEffect sans dépendance : Réglages
    déjà ouvert change de rubrique, un Réglages qui s'ouvre lit l'URL ;
  - R1 : la pastille des dépenses ouvre « pricing » (Tarifs et budget) ; R2 : les pastilles des clés (fal / HeyGen /
    voix) ouvrent « keys » (Clés d'API), comme leur bulle l'annonce ;
  - R3-R4 : la palette de commandes : « Réglages — comptes » → accounts, « Réglages — clés » → keys (l'aide est
    appelée APRÈS `n("settings")`, laissé intact : la paire G1 du maillon dzglyph le contient) ;
  - R5 : la bulle des dépenses annonce « Clic → Réglages → Tarifs et budget. ».
  t220 (16/10, relevé sur e9e47154) — Fournisseurs par défaut : les rôles proposaient des NOMS DE CLÉS et restaient
  dans le localStorage (« Enregistré localement ») ; aucun écran ne réglait ANTHROPIC_MODEL / OPENAI_MODEL ; le
  GEMINI_MODEL de Clés d'API était un champ de clé (chez l'utilisateur, il contient sa clé AIza…).
  - F0 : DzFournDefauts / DzFournModele / DzCleVersDefauts (+ aides dzFd*) devant `Em` ;
  - F1 : l'aide de la rubrique (fin du « Enregistré localement ») ; F2 : les lignes de rôle locales → DzFournDefauts
    (l'état `n` et la liste `s` d'Em restent, morts : retirer leur useState changerait le compte figé) ;
  - F3 : Diagnostic, l'alerte « contient une clé, pas un nom de modèle » à la place de l'aperçu ;
  - F4 : Clés d'API, la ligne GEMINI_MODEL renvoie vers Fournisseurs par défaut.
  t221 (16/10, relevé sur c784c6e8) — Diagnostic : chaque ligne porte « Régler » vers la rubrique où la clé se règle
  (champ `rubrique` du serveur) ; les orphelines reçoivent un champ (D0-D2, C0-C1, N1 : détail plus bas).
  t222 (16/10, relevé sur 1ad154a5) — Clés d'API › « Fournisseurs libres (compatibles OpenAI) » : ajouter, lire la
  liste des modèles, tester, supprimer en deux clics (L0-L1 : détail plus bas).
  t223 (16/10, relevé sur e544888a) — Clés d'API › LLM local : plusieurs serveurs (Ollama natif ou compatible
  OpenAI), la première ligne étant le couple OLLAMA_URL / OLLAMA_MODEL (S0-S1 : détail plus bas).
  Aucune paire ne doit recopier un remplacement de scripts/dzglyph_paires.json (vu : `size:"sm",icon:
  "dz-action-enregistrer",onClick` en est un — l'ordre des props de nos boutons l'évite).
Aucun useState ajouté (compte figé 731), aucun DzTracks, rien qui touche « v2.8.0 ».
Clés dzT « reglages.pastille.* » (zone.objet.role : pas de « _ » dans la zone) : frontend/shared/i18n/menus.json (FR/EN), assemblées par scripts/i18n_assembler.py.

Maillon de QUEUE, APRÈS dzquick (dont il sonde le marqueur) ; il garde un .js.bak_dzreglages le temps de l'écriture
puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzreglages` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzquick`.
Les tâches suivantes du lot (t220-t223) AJOUTENT leurs paires ici : défaire d'abord avec le patcher de HEAD, éditer
PAIRES, puis réappliquer. Lecture et écriture en OCTETS.
Run : python scripts/patch_bundle_dzreglages.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzreglages")
TAG = "dzreglages"
MARKER = "function dzOuvrirReglages("
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("dzquick", "class DzQuickGarde ", 1),
    ("dzespace", "function DzEspaceSel(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

# R0 — les deux aides, posées devant Réglages (une ligne : le code injecté par les maillons est minifié à la main)
AIDES = (
    'function dzOuvrirReglages(section,aller){try{var u=new URL(window.location.href);u.searchParams.set("section",'
    'section);window.history.replaceState(null,"",u)}catch(_e){}try{window.dispatchEvent(new CustomEvent('
    '"dz-reglages-section",{detail:{section:section}}))}catch(_e){}if(typeof aller==="function")aller("settings")}'
    'function dzReglagesEcoute(aller){function h(ev){var k=ev&&ev.detail&&ev.detail.section;if(ym.includes(k))'
    'aller(k)}window.addEventListener("dz-reglages-section",h);return function(){'
    'window.removeEventListener("dz-reglages-section",h)}}'
)

XM = ('function xm({variant:e,personas:t=[],activePersonaId:n,setActivePersonaId:o,savePersona:i}){const[s,a]='
      'x.useState(()=>{const u=vn("section");return ym.includes(u)?u:"accounts"}),[l,d]=x.useState(null);')

PAIRES = [
    (XM,                                                                                                    # R0
     AIDES + XM + 'x.useEffect(function(){return dzReglagesEcoute(a)},[]);'),
    ('r.jsxs("div",{title:__dzCoutBlanc(Cu).titre,onClick:()=>i&&i("settings"),',                           # R1
     'r.jsxs("div",{title:__dzCoutBlanc(Cu).titre,onClick:()=>dzOuvrirReglages("pricing",i),'),
    ('title:dzT("coque.entete.ouvrir_cles"),onClick:()=>i&&i("settings"),',                                  # R2
     'title:dzT("coque.entete.ouvrir_cles"),onClick:()=>dzOuvrirReglages("keys",i),'),
    # R3-R4 : `n("settings")` reste tel quel (la paire G1 du maillon dzglyph le contient) ; l'aide vient APRÈS lui,
    # dans le même gestionnaire : l'URL est écrite avant que Réglages ne se monte (le rendu suit le gestionnaire)
    ('ings"),t()}},{l:dzT("coque.palette.reglages_cles")',                                                   # R3
     'ings"),t(),dzOuvrirReglages("accounts")}},{l:dzT("coque.palette.reglages_cles")'),
    ('ings"),t()}}].filter(l=>!i||',                                                                         # R4
     'ings"),t(),dzOuvrirReglages("keys")}}].filter(l=>!i||'),
    ('titre:t+dzT("reglages.depenses.clic_reglages")',                                                      # R5
     'titre:t+dzT("reglages.pastille.clic_tarifs")'),
]

# ── t220 : Fournisseurs par défaut branchés sur le serveur, modèles de texte réglables ─────────────────────────────
# F0 — les composants, posés devant `Em` (Réglages › Fournisseurs par défaut). Aucun useState (useReducer seulement).
#   DzFournDefauts : les lignes Image → vidéo / Avatar / Voix off en LECTURE SEULE (la clé servie et son état, lus sur
#   la santé du shell comme avant), les rôles Résumé News / Planificateur (un MOTEUR, liste du serveur, "" = auto,
#   POST /api/settings/provider-defaults puis relecture), une ligne DzFournModele par moteur configuré (ou fautif).
#   DzFournModele : la liste du fournisseur (GET …/modeles) + une saisie libre liées à la même valeur, Tester (POST
#   …/tester, ne dépense rien) et Enregistrer. Un modèle fautif (clé collée) n'est JAMAIS montré : champ vide, bord
#   rouge, alerte « contient une clé, pas un nom de modèle » ; Enregistrer reste actif (vide = défaut du code).
#   DzCleVersDefauts : la ligne « Gemini — modèle » de Clés d'API renvoie vers cette rubrique.
COMPOSANTS_F = (
    'function dzFdJson(R){return R.json().catch(function(){return{}}).then(function(d){if(!R.ok)throw new Error('
    'String(d&&d.detail||("HTTP "+R.status)));return d})}'
    'function dzFdPoster(corps){return fetch("/api/settings/provider-defaults",{method:"POST",headers:{"Content-Type":'
    '"application/json"},body:JSON.stringify(corps)}).then(dzFdJson)}'
    'function dzFdNom(d,id){var m=((d&&d.moteurs)||[]).find(function(x){return x.moteur===id});return m?m.nom:id}'
    'function dzFdTete(titre,aide){return r.jsxs("div",{children:[r.jsx("div",{style:{fontSize:12.5,color:'
    '"var(--ink-strong)"},children:titre}),r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)"},children:aide})]})}'
    'var dzFdLigne={display:"grid",gridTemplateColumns:"260px 1fr auto",gap:14,alignItems:"center",padding:"14px 18px",'
    'borderTop:"1px solid var(--stroke)"};'
    'function DzFournModele({m:m,relire:relire}){'
    'var rs=x.useReducer(function(o,n){return Object.assign({},o,n)},{v:m.modele||"",liste:null,lisible:!1,msg:"",ton:"",busy:!1}),'
    'st=rs[0],maj=rs[1];'
    'x.useEffect(function(){var on=!0;fetch("/api/settings/provider-defaults/modeles?moteur="+encodeURIComponent(m.moteur))'
    '.then(dzFdJson).then(function(d){on&&maj({liste:d.modeles||[],lisible:!!d.lisible})}).catch(function(){on&&maj({liste:[],'
    'lisible:!1})});'
    'return function(){on=!1}},[m.moteur]);x.useEffect(function(){maj({v:m.modele||""})},[m.modele,m.fautif]);'
    'function fini(msg,ton){maj({busy:!1,msg:msg,ton:ton})}'
    'function enregistrer(){var c={};c[m.moteur]=st.v.trim();maj({busy:!0,msg:""});dzFdPoster({modeles:c}).then(function(){'
    'fini(dzT("commun.etat.enregistre"),"green");relire()}).catch(function(e){fini(String(e&&e.message||e),"red")})}'
    'function tester(){maj({busy:!0,msg:""});fetch("/api/settings/provider-defaults/tester",{method:"POST",headers:'
    '{"Content-Type":"application/json"},body:JSON.stringify({moteur:m.moteur,modele:st.v.trim()})}).then(dzFdJson)'
    '.then(function(d){fini({connu:dzT("reglages.fournisseurs.test_connu"),inconnu:dzT("reglages.fournisseurs.test_inconnu"),'
    'non_verifiable:dzT("reglages.fournisseurs.test_non_verifiable")}[d.etat]||String(d.etat),d.ok===!0?"green":'
    'd.ok===!1?"red":"amber")})'
    '.catch(function(e){fini(String(e&&e.message||e),"red")})}'
    'var liste=st.liste||[],opts=liste.map(function(n){return{value:n,label:n}});'
    'if(st.v&&liste.indexOf(st.v)<0)opts=[{value:st.v,label:st.v}].concat(opts);'
    'if(!opts.length)opts=[{value:"",label:st.liste===null?dzT("reglages.commun.chargement"):"—"}];'
    'var change=st.v.trim()!==(m.modele||"")||m.fautif;'
    'return r.jsxs("div",{"data-dzfourn":"modele-"+m.moteur,style:Object.assign({},dzFdLigne,{gridTemplateColumns:'
    '"260px 1fr"}),children:['
    'dzFdTete(dzT("reglages.fournisseurs.modele_de",{moteur:m.nom}),r.jsxs("span",{children:[r.jsx("span",{className:'
    '"mono",children:m.cle_modele}),m.fautif?r.jsx("span",{"data-dzfourn":"alerte",style:{color:"var(--red)"},children:'
    '" · "+dzT("reglages.fournisseurs.cle_dans_modele")}):null]})),'
    'r.jsxs("div",{style:{minWidth:0},children:[r.jsxs("div",{style:{display:"flex",gap:8,alignItems:"center",minWidth:0},children:['
    'r.jsx("div",{style:{flex:"1 1 0",minWidth:0},children:r.jsx(re,{value:st.v,options:opts,onChange:function(v){'
    'maj({v:v||"",msg:""})}})}),'
    'r.jsx("input",{"data-dzfourn":"saisie",value:st.v,placeholder:dzT("reglages.fournisseurs.saisir_nom"),'
    'onChange:function(e){maj({v:e.target.value,msg:""})},style:{flex:"1 1 0",minWidth:110,boxSizing:"border-box",'
    'background:"var(--bg-base)",border:"1px solid "+(m.fautif?"var(--red)":"var(--stroke)"),borderRadius:"var(--r-sm)",'
    'padding:"6px 10px",color:"var(--ink-strong)",fontFamily:"var(--f-mono)",fontSize:12}}),'
    'r.jsx(K,{variant:"outline",size:"sm",onClick:tester,disabled:st.busy||!st.v.trim(),children:dzT("reglages.diag.tester")}),'
    'r.jsx(K,{variant:"primary",icon:"dz-action-enregistrer",size:"sm",onClick:enregistrer,disabled:st.busy||!change,'
    'children:dzT("reglages.commun.enregistrer")})]}),'
    'r.jsx("div",{"data-dzfourn":"etat",style:{fontSize:10.5,marginTop:6,color:st.ton==="red"?"var(--red)":'
    'st.ton==="green"?"var(--green)":st.ton==="amber"?"var(--amber)":"var(--ink-muted)"},children:st.msg||(st.liste===null'
    '?"…":st.lisible?dzT("reglages.fournisseurs.n_modeles",{n:liste.length}):dzT("reglages.fournisseurs.liste_illisible"))})]})]})}'
    'function DzFournDefauts({cles:t}){'
    'var rs=x.useReducer(function(o,n){return Object.assign({},o,n)},{d:null,msg:"",err:!1}),st=rs[0],maj=rs[1];'
    'function charger(){return fetch("/api/settings/provider-defaults").then(dzFdJson).then(function(d){maj({d:d})})'
    '.catch(function(e){maj({msg:String(e&&e.message||e),err:!0})})}'
    'x.useEffect(function(){charger()},[]);'
    'function role(id,v){var c={};c[id]=v;maj({msg:""});dzFdPoster(c).then(function(){maj({msg:dzT("commun.etat.enregistre"),'
    'err:!1});charger()}).catch(function(e){maj({msg:String(e&&e.message||e),err:!0})})}'
    'var d=st.d,SV=[["video","reglages.defauts.video","reglages.defauts.video_aide","FAL_KEY"],["avatar",'
    '"reglages.defauts.avatar","reglages.defauts.avatar_aide","HEYGEN_API_KEY"],["voice","reglages.defauts.voix_off",'
    '"reglages.defauts.voix_off_aide","ELEVENLABS_API_KEY"]],RO=[["summarizer","reglages.defauts.resume",'
    '"reglages.defauts.resume_aide"],["planner","reglages.defauts.planif","reglages.defauts.planif_aide"]];'
    'return r.jsxs(r.Fragment,{children:['
    '...SV.map(function(s){var pose=(t||[]).includes(s[3]);return r.jsxs("div",{"data-dzfourn":"service-"+s[0],'
    'style:dzFdLigne,children:[dzFdTete(dzT(s[1]),dzT(s[2])),r.jsx("span",{className:"mono",style:{fontSize:11.5,'
    'color:"var(--ink-soft)"},children:s[3]}),r.jsx(te,{tone:pose?"green":"red",dot:!0,children:pose?'
    'dzT("reglages.defauts.pret"):dzT("reglages.defauts.manquant")})]},"s-"+s[0])}),'
    '...RO.map(function(ro){var R=(d&&d.roles&&d.roles[ro[0]])||{},dispo=R.available||[],pref=R.preference||"",'
    'opts=[{value:"",label:dzT("reglages.fournisseurs.auto",{moteur:R.active?dzFdNom(d,R.active):"—"})}].concat('
    'dispo.map(function(id){return{value:id,label:dzFdNom(d,id)}}));'
    'if(pref&&dispo.indexOf(pref)<0)opts.push({value:pref,label:dzFdNom(d,pref)+dzT("reglages.defauts.indisponible")});'
    'return r.jsxs("div",{"data-dzfourn":"role-"+ro[0],style:dzFdLigne,children:[dzFdTete(dzT(ro[1]),dzT(ro[2])),'
    '!d?r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)"},children:dzT("reglages.commun.chargement")}):'
    'dispo.length===0&&!pref?r.jsx("div",{style:{fontSize:11,color:"var(--red)"},children:dzT("reglages.defauts.aucune_cle")}):'
    'r.jsx(re,{value:pref,options:opts,onChange:function(v){role(ro[0],v)}}),'
    'r.jsx(te,{tone:R.active?"green":"red",dot:!0,children:R.active?dzFdNom(d,R.active):dzT("reglages.defauts.manquant")})]},'
    '"r-"+ro[0])}),'
    '...((d&&d.moteurs)||[]).filter(function(m){return m.configure||m.fautif}).map(function(m){'
    'return r.jsx(DzFournModele,{m:m,relire:charger},"m-"+m.moteur)}),'
    'st.msg?r.jsx("div",{"data-dzfourn":"msg",style:{padding:"8px 18px",borderTop:"1px solid var(--stroke)",fontSize:11.5,'
    'color:st.err?"var(--red)":"var(--green)"},children:st.msg},"msg"):null]})}'
    'function DzCleVersDefauts({k:k,c:c}){return r.jsxs("div",{"data-dzfourn":"vers-defauts",style:{display:"grid",'
    'gridTemplateColumns:"180px minmax(0,1fr) auto",gap:14,alignItems:"center",padding:"14px 18px",borderTop:c?'
    '"1px solid var(--stroke)":"none"},children:[r.jsxs("div",{children:[r.jsx("div",{style:{fontSize:12.5,color:'
    '"var(--ink-strong)"},children:k.label}),r.jsx("div",{className:"mono",style:{fontSize:10.5,color:"var(--ink-muted)"},'
    'children:k.k})]}),r.jsx("div",{style:{fontSize:11.5,color:"var(--ink-soft)"},children:'
    'dzT("reglages.fournisseurs.se_regle_ailleurs")}),r.jsx(K,{variant:"outline",size:"sm",onClick:function(){'
    'dzOuvrirReglages("defaults")},children:dzT("commun.action.ouvrir")})]})}'
)

EM = 'function Em(){const e=bt(),t=Fu.filter('
LIGNES_ROLES = (
    '...s.map((a,l)=>{const d=a.options.filter(f=>t.includes(f)),u=n[a.id]||d[0]||"";return r.jsxs("div",{style:'
    '{display:"grid",gridTemplateColumns:"260px 1fr auto",gap:14,alignItems:"center",padding:"14px 18px",borderTop:'
    '"1px solid var(--stroke)"},children:[r.jsxs("div",{children:[r.jsx("div",{style:{fontSize:12.5,color:'
    '"var(--ink-strong)"},children:a.label}),r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)"},children:a.hint})]'
    '}),d.length===0?r.jsx("div",{style:{fontSize:11,color:"var(--red)"},children:dzT("reglages.defauts.aucune_cle")}):'
    'r.jsx(re,{value:u,options:d.map(f=>({value:f,label:f})),onChange:f=>i(a.id,f)}),r.jsx(te,{tone:d.length?"green":"red",'
    'dot:!0,children:d.length?dzT("reglages.defauts.pret"):dzT("reglages.defauts.manquant")})]},a.id)})'
)
DIAG_APERCU = ("'var(--ink-muted)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'},title:t?"
               "String(t.message||''):c.apercu,children:t?String(t.message||''):(c.apercu||'')})")
CLES_LIGNE = 'children:Fu.map((k,c)=>{const p=!!(e!=null&&e[k.health]),h=g[k.k];'

PAIRES += [
    (EM, COMPOSANTS_F + EM),                                                                                # F0
    ('dzT("reglages.defauts.aide_1"),r.jsx("span",{className:"mono",children:"backend/.env"}),'              # F1
     'dzT("reglages.defauts.aide_2")',
     'dzT("reglages.fournisseurs.aide")'),
    (LIGNES_ROLES, 'r.jsx(DzFournDefauts,{cles:t},"dzfourn")'),                                             # F2
    (DIAG_APERCU,                                                                                           # F3
     "(c.alerte?'var(--red)':'var(--ink-muted)'),overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'},"
     "title:t?String(t.message||''):c.apercu,children:t?String(t.message||''):(c.alerte?"
     "dzT(\"reglages.fournisseurs.cle_dans_modele\"):(c.apercu||''))})"),
    (CLES_LIGNE,                                                                                            # F4
     CLES_LIGNE + 'if(k.k==="GEMINI_MODEL")return r.jsx(DzCleVersDefauts,{k:k,c:c},k.k);'),
]

# ── t221 : Diagnostic, chaque clé a son endroit (16/10, relevé sur c784c6e8) ──────────────────────────────────────────
# Le Diagnostic listait les clés de l'allowlist sans dire où les régler ; DECART_API_KEY (hors de l'écran Avatar live),
# ARTICLE_READER_FALLBACK et ELEVENLABS_VOICE_ID_FR / _EN ne se réglaient nulle part. Le serveur dit désormais la
# rubrique de chaque ligne (`rubrique`, table RUBRIQUE_DE_CLE de settings_routes, tirée de l'allowlist).
#   D0 : dzFuNeuves (les lignes de C0), dzRgCle (POST /api/settings/keys d'UNE valeur, l'erreur du serveur dite), DzDiagRegler (le bouton « Régler » :
#        dzOuvrirReglages(rubrique) SANS `aller`, Réglages est déjà ouvert et son écoute change de rubrique),
#        DzCleTexte (un réglage texte de Clés d'API qui n'est pas un secret : champ clair, Enregistrer) et
#        DzNewsLecteur (la bascule du lecteur public, lue sur /api/health), posés devant DzDiag ;
#   D1-D2 : la ligne du Diagnostic gagne une colonne et le bouton ;
#   C0 : Clés d'API, trois lignes neuves (Decart, voix FR, voix EN — ces deux-là `texte:!0`), rendues par
#        `Fu.concat(dzFuNeuves())` : le littéral `Fu` reste intact (test_p1_figma_token : Figma en dernier) ;
#   C1 : une ligne `texte` est rendue par DzCleTexte ; N1 : Réglages › News montre la bascule sous son aide.
COMPOSANTS_D = (
    'function dzRgCle(nom,val){return fetch("/api/settings/keys",{method:"POST",headers:{"Content-Type":'
    '"application/json"},body:JSON.stringify({name:nom,value:val})}).then(function(R){return R.json().catch(function(){'
    'return{}}).then(function(d){if(!R.ok||d.ok===!1)throw new Error(String(d&&(d.detail||d.error)||("HTTP "+R.status)));'
    'return d})})}'
    'function DzDiagRegler({c:c}){if(!c.rubrique)return r.jsx("div",{});return r.jsx(K,{variant:"ghost",size:"sm",'
    '"data-dzdiag-regler":c.rubrique,title:dzT("reglages.diag.regler_aide"),onClick:function(){dzOuvrirReglages(c.rubrique)},'
    'children:dzT("reglages.diag.regler")})}'
    'function DzCleTexte({k:k,c:c,h:h,relire:relire}){'
    'var rs=x.useReducer(function(o,n){return Object.assign({},o,n)},{v:"",msg:"",err:!1,busy:!1}),st=rs[0],maj=rs[1];'
    'function enregistrer(){var v=st.v.trim();if(!v)return;maj({busy:!0,msg:""});dzRgCle(k.k,v).then(function(){'
    'maj({busy:!1,v:"",msg:dzT("commun.etat.enregistre"),err:!1});relire&&relire()}).catch(function(e){'
    'maj({busy:!1,msg:String(e&&e.message||e),err:!0})})}'
    'return r.jsxs("div",{"data-dzcle-texte":k.k,style:{display:"grid",gridTemplateColumns:"180px minmax(0,1fr) auto",'
    'gap:14,alignItems:"center",padding:"14px 18px",borderTop:c?"1px solid var(--stroke)":"none"},children:['
    'r.jsxs("div",{children:[r.jsx("div",{style:{fontSize:12.5,color:"var(--ink-strong)"},children:k.label}),'
    'r.jsxs("div",{className:"mono",title:k.k+" · "+k.why,style:{fontSize:10.5,color:"var(--ink-muted)",overflow:"hidden",'
    'textOverflow:"ellipsis",whiteSpace:"nowrap"},children:[k.k," · ",k.why]}),h&&h.preview?r.jsxs("div",{className:"mono",'
    'style:{fontSize:10,color:"var(--ink-soft)",marginTop:2},children:[dzT("reglages.cles.actuelle"),h.preview]}):null]}),'
    'r.jsxs("div",{style:{minWidth:0},children:[r.jsx("input",{type:"text","data-dzcle-saisie":k.k,value:st.v,'
    'placeholder:dzT("avatar.perso.voix_id"),onChange:function(e){maj({v:e.target.value,msg:""})},style:{minWidth:0,'
    'width:"100%",boxSizing:"border-box",background:"var(--bg-base)",border:"1px solid var(--stroke)",borderRadius:'
    '"var(--r-sm)",padding:"6px 10px",color:"var(--ink-strong)",fontFamily:"var(--f-mono)",fontSize:12}}),'
    'st.msg?r.jsx("div",{"data-dzcle-msg":st.err?"erreur":"ok",style:{fontSize:10.5,marginTop:4,color:st.err?"var(--red)":'
    '"var(--green)"},children:st.msg}):null]}),'
    'r.jsx(K,{variant:"primary",icon:"dz-action-enregistrer",size:"sm",onClick:enregistrer,disabled:st.busy||!st.v.trim(),'
    'children:st.busy?"…":dzT("reglages.commun.enregistrer")})]})}'
    'function DzNewsLecteur(){'
    'var rs=x.useReducer(function(o,n){return Object.assign({},o,n)},{on:null,msg:"",err:!1}),st=rs[0],maj=rs[1];'
    'x.useEffect(function(){var vif=!0;fetch("/api/health").then(function(R){return R.json()}).then(function(d){'
    'vif&&typeof(d&&d.article_reader_fallback)==="boolean"&&maj({on:d.article_reader_fallback})}).catch(function(){});'
    'return function(){vif=!1}},[]);'
    'function basculer(v){maj({msg:""});dzRgCle("ARTICLE_READER_FALLBACK",v?"true":"false").then(function(){'
    'maj({on:v,msg:dzT("commun.etat.enregistre"),err:!1})}).catch(function(e){maj({msg:String(e&&e.message||e),err:!0})})}'
    'return r.jsxs(jt,{"data-dzlecteur":st.on===null?"inconnu":st.on?"actif":"coupe",style:{padding:"12px 14px",'
    'marginBottom:14},children:[r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"minmax(0,1fr) auto",gap:12,'
    'alignItems:"center"},children:[r.jsxs("div",{children:[r.jsx("div",{style:{fontSize:12.5,color:"var(--ink-strong)"},'
    'children:dzT("reglages.news.lecteur")}),r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)",marginTop:2},'
    'children:dzT("reglages.news.lecteur_aide")}),r.jsx("div",{className:"mono",style:{fontSize:10,color:"var(--ink-muted)",'
    'marginTop:2},children:"ARTICLE_READER_FALLBACK"})]}),st.on===null?r.jsx("span",{style:{color:"var(--ink-muted)"},'
    'children:"…"}):r.jsx(Ze,{checked:st.on,onChange:basculer})]}),st.msg?r.jsx("div",{"data-dzlecteur-msg":st.err?'
    '"erreur":"ok",style:{fontSize:10.5,marginTop:6,color:st.err?"var(--red)":"var(--green)"},children:st.msg}):null]})}'
)
DIAG = "function DzDiag(){"
DIAG_GRILLE = "'data-dzdiag-cle':c.cle,style:{display:'grid',gridTemplateColumns:'210px 90px 1fr auto',gap:10,"
DIAG_FIN = "onClick:()=>tester(c.cle),children:dzT(\"reglages.diag.tester\")}):r.jsx('div',{})]},c.cle)"
FU_MAP = 'children:Fu.map((k,c)=>{const p='
FU_NEUVES = (
    'function dzFuNeuves(){return[{k:"DECART_API_KEY",label:dzT("reglages.cles.decart"),why:dzT('
    '"reglages.cles.decart_pourquoi"),health:"decart_configured"},{k:"ELEVENLABS_VOICE_ID_FR",label:dzT('
    '"reglages.cles.voix_fr"),why:dzT("reglages.cles.voix_pourquoi"),health:"voiceover_enabled",texte:!0},'
    '{k:"ELEVENLABS_VOICE_ID_EN",label:dzT("reglages.cles.voix_en"),why:dzT("reglages.cles.voix_pourquoi"),'
    'health:"voiceover_enabled",texte:!0}]}'
)
VERS_DEFAUTS = 'if(k.k==="GEMINI_MODEL")return r.jsx(DzCleVersDefauts,{k:k,c:c},k.k);'
NEWS_AIDE = 'children:dzT("reglages.news.aide")}),'

PAIRES += [
    (DIAG, FU_NEUVES + COMPOSANTS_D + DIAG),                                                                # D0
    (DIAG_GRILLE, DIAG_GRILLE.replace("1fr auto'", "1fr auto auto'")),                                       # D1
    (DIAG_FIN, DIAG_FIN.replace("r.jsx('div',{})]},c.cle)",                                                 # D2
                                "r.jsx('div',{}),r.jsx(DzDiagRegler,{c:c})]},c.cle)")),
    (FU_MAP, 'children:Fu.concat(dzFuNeuves()).map((k,c)=>{const p='),                                      # C0
    (VERS_DEFAUTS,                                                                                          # C1
     VERS_DEFAUTS + 'if(k.texte)return r.jsx(DzCleTexte,{k:k,c:c,h:h,relire:function(){m(),No()}},k.k);'),
    (NEWS_AIDE, NEWS_AIDE + 'r.jsx(DzNewsLecteur,{}),'),                                                    # N1
]


# ── t222 : les fournisseurs libres compatibles OpenAI (16/10, relevé sur 1ad154a5) ───────────────────────────────────
# Clés d'API n'avait qu'un encart « LLM local » : aucun moyen d'ajouter DeepSeek, OpenRouter, Mistral, Groq… Le serveur
# (services/fournisseurs_llm.py, routes /api/reglages/fournisseurs-libres) garde la description sans secret et la clé
# au coffre ou au .env (DZF_<ID>_API_KEY), jamais relue ; chaque fournisseur devient le moteur de texte `fl:<id>`.
#   L0 : DzFournLibres (+ aides dzFl*) devant `wm` (l'encart « LLM local ») : la liste (nom, base, moteur, clé posée,
#        modèle par défaut, « prix à mesurer »), par ligne Remplacer la clé / Lire la liste / Tester / Supprimer (DEUX
#        clics : le premier arme « Confirmer la suppression »), et « + Ajouter un fournisseur » : préréglage, nom, URL de
#        base, clé, « Lire la liste » (GET {base}/models par le serveur), modèles en saisie libre, modèle par défaut.
#        Aucun useState (useReducer, mises à jour fonctionnelles pour les réponses tardives) ; un champ neuf n'a pas
#        l'ordre de style compté par test_p2_cles_ecran 2.2 ; le bouton Enregistrer a l'ordre de props de t220 ;
#   L1 : l'encart se pose dans Clés d'API, juste avant « LLM local ».
COMPOSANTS_L = (
    'var dzFlVide={nom:"",base:"",cle:"",modeles:"",defaut:"",pre:""},dzFlRacine="/api/reglages/fournisseurs-libres";'
    'function dzFlAppel(url,methode,corps){return fetch(url,{method:methode||"GET",headers:{"Content-Type":'
    '"application/json"},body:corps?JSON.stringify(corps):void 0}).then(dzFdJson)}'
    'function dzFlTon(t){return t==="red"?"var(--red)":t==="green"?"var(--green)":"var(--ink-muted)"}'
    'function dzFlChamp(lib,el){return r.jsxs("label",{style:{display:"flex",flexDirection:"column",gap:4,minWidth:0,'
    'fontSize:11,color:"var(--ink-soft)"},children:[lib,el]})}'
    'function dzFlSaisie(attr,v,ph,surv,type){return r.jsx("input",{"data-dzfl":attr,type:type||"text",value:v,'
    'placeholder:ph,autoComplete:"off",spellCheck:!1,onChange:function(e){surv(e.target.value)},style:{minWidth:0,'
    'boxSizing:"border-box",width:"100%",background:"var(--bg-base)",border:"1px solid var(--stroke)",borderRadius:'
    '"var(--r-sm)",padding:"6px 10px",color:"var(--ink-strong)",fontFamily:"var(--f-mono)",fontSize:12}})}'
    'function DzFournLibres({onSaved:onSaved}){'
    'var rs=x.useReducer(function(o,n){return Object.assign({},o,typeof n==="function"?n(o):n)},{l:null,pre:[],err:"",'
    'ouvert:!1,f:dzFlVide,lus:null,msg:"",ton:"",busy:!1,conf:"",rm:{},cles:{}}),st=rs[0],maj=rs[1];'
    'function charger(){return dzFlAppel(dzFlRacine).then(function(d){maj({l:d.fournisseurs||[],pre:d.prereglages||[],'
    'err:""})}).catch(function(e){maj({l:[],err:String(e&&e.message||e)})})}'
    'x.useEffect(function(){charger()},[]);'
    'function prevenir(){charger();onSaved&&onSaved()}'
    'function champ(k,v){maj(function(o){var f=Object.assign({},o.f);f[k]=v;return{f:f,msg:""}})}'
    'function prereglage(id){maj(function(o){var p=o.pre.find(function(q){return q.id===id});return{f:Object.assign({},'
    'o.f,{pre:id},p?{nom:p.nom,base:p.base}:{}),msg:""}})}'
    'function fini(msg,ton,plus){maj(Object.assign({busy:!1,msg:msg,ton:ton},plus||{}))}'
    'function lireForm(){maj({busy:!0,msg:""});dzFlAppel(dzFlRacine+"/lire-modeles","POST",{base:st.f.base,cle:st.f.cle})'
    '.then(function(d){var m=d.modeles||[];maj(function(o){return{busy:!1,ton:"green",lus:m,msg:dzT('
    '"reglages.libres.n_lus",{n:m.length}),f:Object.assign({},o.f,{modeles:m.join(", "),defaut:o.f.defaut||m[0]||""})}})})'
    '.catch(function(e){fini(String(e&&e.message||e),"red")})}'
    'function creer(){var f=st.f;maj({busy:!0,msg:""});dzFlAppel(dzFlRacine,"POST",{nom:f.nom,base:f.base,cle:f.cle,'
    'modeles:f.modeles,defaut:f.defaut}).then(function(){fini(dzT("commun.etat.enregistre"),"green",{ouvert:!1,f:dzFlVide,'
    'lus:null});prevenir()}).catch(function(e){fini(String(e&&e.message||e),"red")})}'
    'function dire(id,t,ton){maj(function(o){var rm=Object.assign({},o.rm);rm[id]={t:t,ton:ton};return{rm:rm}})}'
    'function modifier(id,corps,ok){return dzFlAppel(dzFlRacine+"/"+id,"POST",corps).then(function(){dire(id,ok||'
    'dzT("commun.etat.enregistre"),"green");prevenir();return!0}).catch(function(e){dire(id,String(e&&e.message||e),'
    '"red");return!1})}'
    'function lireLigne(p){dire(p.id,"…","");dzFlAppel(dzFlRacine+"/lire-modeles","POST",{id:p.id}).then(function(d){'
    'var m=d.modeles||[];return modifier(p.id,{modeles:m},dzT("reglages.libres.n_lus",{n:m.length}))}).catch(function(e){'
    'dire(p.id,String(e&&e.message||e),"red")})}'
    'function tester(p){dire(p.id,"…","");dzFlAppel(dzFlRacine+"/"+p.id+"/tester","POST",{}).then(function(d){'
    'dire(p.id,d.etat==="ok"?dzT("reglages.libres.test_ok",{n:d.n}):d.etat==="sans_cle"?dzT("reglages.libres.sans_cle"):'
    'String(d.cause||d.etat),d.etat==="ok"?"green":"red")}).catch(function(e){dire(p.id,String(e&&e.message||e),"red")})}'
    'function supprimer(p){if(st.conf!==p.id){maj({conf:p.id});return}maj({conf:""});dzFlAppel(dzFlRacine+"/"+p.id,'
    '"DELETE").then(function(){maj({msg:dzT("reglages.libres.supprime"),ton:"green",err:""});prevenir()}).catch('
    'function(e){dire(p.id,String(e&&e.message||e),"red")})}'
    'function cle(id,v){maj(function(o){var c=Object.assign({},o.cles);c[id]=v;return{cles:c}})}'
    'function remplacer(p){var v=(st.cles[p.id]||"").trim();if(!v)return;modifier(p.id,{cle:v}).then(function(ok){'
    'ok&&cle(p.id,"")})}'
    'var l=st.l,f=st.f,pret=!!(f.nom.trim()&&f.base.trim()),opts=[{value:"",label:dzT("reglages.libres.autre")}].concat('
    'st.pre.map(function(p){return{value:p.id,label:p.nom}}));'
    'return r.jsxs("div",{"data-dzfl":"encart",style:{marginTop:22},children:['
    'r.jsx("div",{className:"display",style:{fontSize:15,color:"var(--ink-strong)",marginBottom:4},children:'
    'dzT("reglages.libres.titre")}),'
    'r.jsx("div",{style:{fontSize:11.5,color:"var(--ink-soft)",marginBottom:12,maxWidth:640},children:'
    'dzT("reglages.libres.aide")}),'
    'r.jsxs(jt,{style:{padding:0},children:['
    'l===null?r.jsx("div",{style:{padding:"14px 18px",fontSize:11.5,color:"var(--ink-soft)"},children:'
    'dzT("reglages.commun.chargement")},"ch"):l.length===0?r.jsx("div",{"data-dzfl":"vide",style:{padding:"14px 18px",'
    'fontSize:11.5,color:"var(--ink-soft)"},children:dzT("reglages.libres.aucun")},"vide"):null,'
    '...(l||[]).map(function(p,i){var m=st.rm[p.id],mods=(p.defaut&&p.modeles.indexOf(p.defaut)<0?[p.defaut]:[]).concat('
    'p.modeles),arme=st.conf===p.id;'
    'return r.jsxs("div",{"data-dzfl":"ligne-"+p.id,style:{padding:"14px 18px",borderTop:i?"1px solid var(--stroke)":'
    '"none"},children:['
    'r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"200px minmax(0,1fr) auto",gap:14,alignItems:"center"},'
    'children:['
    'r.jsxs("div",{style:{minWidth:0},children:[r.jsx("div",{style:{fontSize:12.5,color:"var(--ink-strong)"},children:'
    'p.nom}),r.jsx("div",{className:"mono",title:p.base,style:{fontSize:10.5,color:"var(--ink-muted)",overflow:"hidden",'
    'textOverflow:"ellipsis",whiteSpace:"nowrap"},children:p.base}),r.jsx("div",{className:"mono",style:{fontSize:10,'
    'color:"var(--ink-soft)",marginTop:2},children:p.moteur+" · "+p.cle})]}),'
    'r.jsxs("div",{style:{display:"flex",gap:8,alignItems:"center",minWidth:0,flexWrap:"wrap"},children:['
    'r.jsx("div",{"data-dzfl":"defaut-"+p.id,style:{flex:"1 1 180px",minWidth:0},children:r.jsx(re,{value:p.defaut,'
    'options:mods.length?mods.map(function(n){return{value:n,label:n}}):[{value:"",label:"—"}],onChange:function(v){'
    'v&&v!==p.defaut&&modifier(p.id,{defaut:v})}})}),'
    'r.jsx("span",{style:{fontSize:10.5,color:"var(--ink-soft)"},children:dzT("reglages.libres.n_modeles",'
    '{n:p.modeles.length})+" · "+dzT("ia.prix.a_mesurer")})]}),'
    'r.jsx(te,{tone:p.cle_posee?"green":"red",dot:!0,children:p.cle_posee?dzT("reglages.cles.posee"):'
    'dzT("reglages.cles.manquante")})]}),'
    'r.jsxs("div",{style:{display:"flex",gap:8,alignItems:"center",marginTop:10,flexWrap:"wrap"},children:['
    'r.jsx("div",{style:{flex:"1 1 220px",minWidth:0},children:dzFlSaisie("cle-"+p.id,st.cles[p.id]||"",p.cle_posee?'
    'dzT("reglages.cles.coller_nouvelle"):dzT("reglages.cles.coller"),function(v){cle(p.id,v)},"password")}),'
    'r.jsx(K,{variant:"outline",size:"sm","data-dzfl":"remplacer-"+p.id,onClick:function(){remplacer(p)},'
    'disabled:!(st.cles[p.id]||"").trim(),children:dzT("reglages.libres.remplacer")}),'
    'r.jsx(K,{variant:"outline",size:"sm","data-dzfl":"lire-"+p.id,onClick:function(){lireLigne(p)},disabled:'
    '!p.cle_posee,children:dzT("reglages.libres.lire")}),'
    'r.jsx(K,{variant:"outline",size:"sm","data-dzfl":"tester-"+p.id,onClick:function(){tester(p)},children:'
    'dzT("reglages.diag.tester")}),'
    'r.jsx(K,{variant:arme?"danger":"ghost",size:"sm","data-dzfl":"suppr-"+p.id,onClick:function(){supprimer(p)},'
    'children:arme?dzT("espaces.comptes.confirmer"):dzT("commun.action.supprimer")})]}),'
    'm?r.jsx("div",{"data-dzfl":"msg-"+p.id,style:{fontSize:10.5,marginTop:6,color:dzFlTon(m.ton)},children:m.t}):null]},'
    '"fl-"+p.id)})]}),'
    'st.ouvert?r.jsxs(jt,{"data-dzfl":"form",style:{padding:14,marginTop:12},children:['
    'r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"minmax(0,1fr) minmax(0,1fr) minmax(0,2fr)",gap:12,'
    'alignItems:"end"},children:['
    'dzFlChamp(dzT("vfx.commun.prereglage"),r.jsx(re,{value:f.pre,options:opts,onChange:prereglage})),'
    'dzFlChamp(dzT("reglages.personas.nom"),dzFlSaisie("nom",f.nom,"DeepSeek",function(v){champ("nom",v)})),'
    'dzFlChamp(dzT("reglages.libres.base"),dzFlSaisie("base",f.base,"https://api.example.com/v1",function(v){'
    'champ("base",v)}))]}),'
    'r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"minmax(0,1fr) auto",gap:12,alignItems:"end",marginTop:10},'
    'children:[dzFlChamp(dzT("reglages.comptes.champ.api_key"),dzFlSaisie("cle",f.cle,dzT("reglages.cles.coller"),'
    'function(v){champ("cle",v)},"password")),'
    'r.jsx(K,{variant:"outline",size:"sm","data-dzfl":"lire-form",onClick:lireForm,disabled:st.busy||!f.base.trim()||'
    '!f.cle.trim(),children:dzT("reglages.libres.lire")})]}),'
    'r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"minmax(0,2fr) minmax(0,1fr)",gap:12,alignItems:"end",'
    'marginTop:10},children:['
    'dzFlChamp(dzT("reglages.libres.modeles"),dzFlSaisie("modeles",f.modeles,dzT("reglages.libres.modeles_aide"),'
    'function(v){champ("modeles",v)})),'
    'dzFlChamp(dzT("reglages.libres.defaut"),st.lus&&st.lus.length?r.jsx(re,{value:f.defaut,options:st.lus.map('
    'function(n){return{value:n,label:n}}),onChange:function(v){champ("defaut",v)}}):dzFlSaisie("defaut",f.defaut,'
    'dzT("reglages.libres.defaut_aide"),function(v){champ("defaut",v)}))]}),'
    'r.jsxs("div",{style:{display:"flex",gap:8,marginTop:12,alignItems:"center"},children:['
    'r.jsx(K,{variant:"primary",icon:"dz-action-enregistrer",size:"sm","data-dzfl":"creer",onClick:creer,disabled:'
    'st.busy||!pret,children:dzT("reglages.commun.enregistrer")}),'
    'r.jsx(K,{variant:"ghost",size:"sm",onClick:function(){maj({ouvert:!1,f:dzFlVide,lus:null,msg:""})},children:'
    'dzT("commun.action.annuler")})]})]}):'
    'r.jsx("div",{style:{marginTop:12},children:r.jsx(K,{variant:"outline",size:"sm","data-dzfl":"ajouter",onClick:'
    'function(){maj({ouvert:!0,msg:"",conf:""})},children:dzT("reglages.libres.ajouter")})}),'
    'st.msg||st.err?r.jsx("div",{"data-dzfl":"msg",style:{fontSize:11,marginTop:8,color:st.err?"var(--red)":'
    'dzFlTon(st.ton)},children:st.msg||st.err}):null]})}'
)
WM = "function wm({serverKeys:e,onSaved:t}){"
WM_APPEL = "r.jsx(wm,{serverKeys:g,onSaved:()=>{m(),No()}})"

PAIRES += [
    (WM, COMPOSANTS_L + WM),                                                                                # L0
    (WM_APPEL, 'r.jsx(DzFournLibres,{onSaved:()=>{m(),No()}}),' + WM_APPEL),                                # L1
]


# ── t223 : LLM local, plusieurs serveurs (16/10, relevé sur e544888a) ─────────────────────────────────────────────────
# L'encart « LLM local (Ollama) » (`wm`) ne réglait qu'un couple OLLAMA_URL / OLLAMA_MODEL, en API Ollama native. Le
# serveur (services/serveurs_locaux.py, routes /api/reglages/serveurs-locaux) décrit désormais une LISTE : la première
# ligne est ce couple, lu tel quel (moteur `ollama`, réglé par `wm` resté intact : ses useState comptent dans les 731),
# puis les serveurs ajoutés (Ollama natif ou compatible OpenAI : LM Studio, llama.cpp, vLLM), moteur `local:<id>`.
#   S0 : DzServeursLocaux (+ aides dzSl*) devant `var dzFlVide=` (hors des tranches que lit le banc de t222) : la liste
#        (nom, URL, moteur · type, modèle par défaut, « n modèles · gratuit », prêt / sans modèle), par ligne Lire les
#        modèles / Tester (la première ligne aussi) / Supprimer en DEUX clics (pas la première), Remplacer la clé pour un
#        serveur compatible OpenAI ; « + Ajouter un serveur » : préréglage (Ollama, LM Studio, llama.cpp, vLLM), type,
#        nom, URL, clé facultative (OpenAI seulement), Lire les modèles (par le serveur), modèles, défaut. Réemploie
#        dzFlAppel / dzFlTon / dzFlChamp de L0 ; aucun useState ; ordre de style de champ hors du compte 2.2 ; bouton
#        Enregistrer à l'ordre de props de t220-t222 ;
#   S1 : la liste se pose juste APRÈS `wm` dans Clés d'API ; elle se relit quand les clés se relisent (`cles:g`).
COMPOSANTS_S = (
    'var dzSlVide={nom:"",url:"",type:"ollama",cle:"",modeles:"",defaut:"",pre:""},dzSlRacine="/api/reglages/serveurs'
    '-locaux";function dzSlSaisie(attr,v,ph,surv,type){return r.jsx("input",{"data-dzsl":attr,type:type||"text",value'
    ':v,placeholder:ph,autoComplete:"off",spellCheck:!1,onChange:function(e){surv(e.target.value)},style:{minWidth:0,'
    'boxSizing:"border-box",width:"100%",background:"var(--bg-base)",border:"1px solid var(--stroke)",borderRadius:"v'
    'ar(--r-sm)",padding:"6px 10px",color:"var(--ink-strong)",fontFamily:"var(--f-mono)",fontSize:12}})}function dzSl'
    'Type(t){return t==="openai"?dzT("reglages.locaux.type_openai"):dzT("reglages.locaux.type_ollama")}function DzSer'
    'veursLocaux({cles:cles,onSaved:onSaved}){var rs=x.useReducer(function(o,n){return Object.assign({},o,typeof n==='
    '"function"?n(o):n)},{l:null,pre:[],err:"",ouvert:!1,f:dzSlVide,lus:null,msg:"",ton:"",busy:!1,conf:"",rm:{},cles'
    ':{}}),st=rs[0],maj=rs[1];function charger(){return dzFlAppel(dzSlRacine).then(function(d){maj({l:d.serveurs||[],'
    'pre:d.prereglages||[],err:""})}).catch(function(e){maj({l:[],err:String(e&&e.message||e)})})}x.useEffect(functio'
    'n(){charger()},[cles]);function prevenir(){charger();onSaved&&onSaved()}function champ(k,v){maj(function(o){var '
    'f=Object.assign({},o.f);f[k]=v;if(k==="type"&&v!=="openai")f.cle="";return{f:f,msg:""}})}function prereglage(id)'
    '{maj(function(o){var p=o.pre.find(function(q){return q.id===id});return{f:Object.assign({},o.f,{pre:id},p?{nom:p'
    '.nom,url:p.url,type:p.type}:{}),msg:""}})}function fini(msg,ton,plus){maj(Object.assign({busy:!1,msg:msg,ton:ton'
    '},plus||{}))}function lireForm(){var f=st.f;maj({busy:!0,msg:""});dzFlAppel(dzSlRacine+"/lire-modeles","POST",{u'
    'rl:f.url,type:f.type,cle:f.type==="openai"?f.cle:""}).then(function(d){var m=d.modeles||[];maj(function(o){retur'
    'n{busy:!1,ton:"green",lus:m,msg:dzT("reglages.locaux.n_lus",{n:m.length}),f:Object.assign({},o.f,{modeles:m.join'
    '(", "),defaut:o.f.defaut||m[0]||""})}})}).catch(function(e){fini(String(e&&e.message||e),"red")})}function creer'
    '(){var f=st.f;maj({busy:!0,msg:""});dzFlAppel(dzSlRacine,"POST",{nom:f.nom,url:f.url,type:f.type,cle:f.type==="o'
    'penai"?f.cle:"",modeles:f.modeles,defaut:f.defaut}).then(function(){fini(dzT("commun.etat.enregistre"),"green",{'
    'ouvert:!1,f:dzSlVide,lus:null});prevenir()}).catch(function(e){fini(String(e&&e.message||e),"red")})}function di'
    're(id,t,ton){maj(function(o){var rm=Object.assign({},o.rm);rm[id]={t:t,ton:ton};return{rm:rm}})}function modifie'
    'r(id,corps,ok){return dzFlAppel(dzSlRacine+"/"+id,"POST",corps).then(function(){dire(id,ok||dzT("commun.etat.enr'
    'egistre"),"green");prevenir();return!0}).catch(function(e){dire(id,String(e&&e.message||e),"red");return!1})}fun'
    'ction lireLigne(p){dire(p.id,"…","");dzFlAppel(dzSlRacine+"/lire-modeles","POST",{id:p.id}).then(function(d){var'
    ' m=d.modeles||[],t=dzT("reglages.locaux.n_lus",{n:m.length});if(p.integre){dire(p.id,t+(m.length?" : "+m.slice(0'
    ',6).join(", ")+(m.length>6?"…":""):""),"green");return}return modifier(p.id,{modeles:m},t)}).catch(function(e){d'
    'ire(p.id,String(e&&e.message||e),"red")})}function tester(p){dire(p.id,"…","");dzFlAppel(dzSlRacine+"/"+p.id+"/t'
    'ester","POST",{}).then(function(d){dire(p.id,d.etat==="ok"?dzT("reglages.locaux.test_ok",{n:d.n}):String(d.cause'
    '||d.etat),d.etat==="ok"?"green":"red")}).catch(function(e){dire(p.id,String(e&&e.message||e),"red")})}function s'
    'upprimer(p){if(st.conf!==p.id){maj({conf:p.id});return}maj({conf:""});dzFlAppel(dzSlRacine+"/"+p.id,"DELETE").th'
    'en(function(){maj({msg:dzT("reglages.locaux.supprime"),ton:"green",err:""});prevenir()}).catch(function(e){dire('
    'p.id,String(e&&e.message||e),"red")})}function cle(id,v){maj(function(o){var c=Object.assign({},o.cles);c[id]=v;'
    'return{cles:c}})}function remplacer(p){var v=(st.cles[p.id]||"").trim();if(!v)return;modifier(p.id,{cle:v}).then'
    '(function(ok){ok&&cle(p.id,"")})}var l=st.l,f=st.f,pret=!!f.url.trim(),opts=[{value:"",label:dzT("reglages.locau'
    'x.autre")}].concat(st.pre.map(function(p){return{value:p.id,label:p.nom}})),types=[{value:"ollama",label:dzT("re'
    'glages.locaux.type_ollama")},{value:"openai",label:dzT("reglages.locaux.type_openai")}];return r.jsxs("div",{"da'
    'ta-dzsl":"encart",style:{marginTop:16},children:[r.jsx("div",{className:"display",style:{fontSize:13.5,color:"va'
    'r(--ink-strong)",marginBottom:4},children:dzT("reglages.locaux.titre")}),r.jsx("div",{style:{fontSize:11.5,color'
    ':"var(--ink-soft)",marginBottom:10,maxWidth:640},children:dzT("reglages.locaux.aide")}),r.jsxs(jt,{style:{paddin'
    'g:0},children:[l===null?r.jsx("div",{style:{padding:"14px 18px",fontSize:11.5,color:"var(--ink-soft)"},children:'
    'dzT("reglages.commun.chargement")},"ch"):null,...(l||[]).map(function(p,i){var m=st.rm[p.id],mods=(p.defaut&&p.m'
    'odeles.indexOf(p.defaut)<0?[p.defaut]:[]).concat(p.modeles),arme=st.conf===p.id,prete=!!(p.defaut||p.modeles.len'
    'gth),ouv=p.type==="openai"&&!p.integre;return r.jsxs("div",{"data-dzsl":"ligne-"+p.id,style:{padding:"12px 18px"'
    ',borderTop:i?"1px solid var(--stroke)":"none"},children:[r.jsxs("div",{style:{display:"grid",gridTemplateColumns'
    ':"minmax(0,200px) minmax(0,1fr) auto",gap:14,alignItems:"center"},children:[r.jsxs("div",{style:{minWidth:0},chi'
    'ldren:[r.jsx("div",{style:{fontSize:12.5,color:"var(--ink-strong)"},children:p.nom}),r.jsx("div",{className:"mon'
    'o",title:p.url,style:{fontSize:10.5,color:"var(--ink-muted)",overflow:"hidden",textOverflow:"ellipsis",whiteSpac'
    'e:"nowrap"},children:p.url}),r.jsx("div",{className:"mono",style:{fontSize:10,color:"var(--ink-soft)",marginTop:'
    '2},children:p.moteur+" · "+dzSlType(p.type)+(p.cle_posee?" · "+dzT("reglages.cles.posee"):"")})]}),r.jsxs("div",'
    '{style:{display:"flex",gap:8,alignItems:"center",minWidth:0,flexWrap:"wrap"},children:[p.integre?r.jsx("span",{c'
    'lassName:"mono","data-dzsl":"defaut-"+p.id,style:{fontSize:11.5,color:"var(--ink-strong)"},children:p.defaut||"—'
    '"}):r.jsx("div",{"data-dzsl":"defaut-"+p.id,style:{flex:"1 1 180px",minWidth:0},children:r.jsx(re,{value:p.defau'
    't,options:mods.length?mods.map(function(n){return{value:n,label:n}}):[{value:"",label:"—"}],onChange:function(v)'
    '{v&&v!==p.defaut&&modifier(p.id,{defaut:v})}})}),r.jsx("span",{style:{fontSize:10.5,color:"var(--ink-soft)"},chi'
    'ldren:(p.integre?dzT("reglages.locaux.integre"):dzT("reglages.libres.n_modeles",{n:p.modeles.length}))+" · "+dzT'
    '("son.commun.gratuit")})]}),r.jsx(te,{tone:prete?"green":"neutral",dot:!0,children:prete?dzT("reglages.defauts.p'
    'ret"):dzT("reglages.locaux.sans_modele")})]}),r.jsxs("div",{style:{display:"flex",gap:8,alignItems:"center",marg'
    'inTop:10,flexWrap:"wrap"},children:[ouv?r.jsx("div",{style:{flex:"1 1 200px",minWidth:0},children:dzSlSaisie("cl'
    'e-"+p.id,st.cles[p.id]||"",p.cle_posee?dzT("reglages.cles.coller_nouvelle"):dzT("reglages.locaux.cle"),function('
    'v){cle(p.id,v)},"password")}):null,ouv?r.jsx(K,{variant:"outline",size:"sm","data-dzsl":"remplacer-"+p.id,onClic'
    'k:function(){remplacer(p)},disabled:!(st.cles[p.id]||"").trim(),children:dzT("reglages.libres.remplacer")}):null'
    ',r.jsx(K,{variant:"outline",size:"sm","data-dzsl":"lire-"+p.id,onClick:function(){lireLigne(p)},children:dzT("re'
    'glages.locaux.lire")}),r.jsx(K,{variant:"outline",size:"sm","data-dzsl":"tester-"+p.id,onClick:function(){tester'
    '(p)},children:dzT("reglages.diag.tester")}),p.integre?null:r.jsx(K,{variant:arme?"danger":"ghost",size:"sm","dat'
    'a-dzsl":"suppr-"+p.id,onClick:function(){supprimer(p)},children:arme?dzT("espaces.comptes.confirmer"):dzT("commu'
    'n.action.supprimer")})]}),m?r.jsx("div",{"data-dzsl":"msg-"+p.id,style:{fontSize:10.5,marginTop:6,color:dzFlTon('
    'm.ton),overflowWrap:"anywhere"},children:m.t}):null]},"sl-"+p.id)})]}),st.ouvert?r.jsxs(jt,{"data-dzsl":"form",s'
    'tyle:{padding:14,marginTop:12},children:[r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"minmax(0,1fr) '
    'minmax(0,1fr) minmax(0,1fr)",gap:12,alignItems:"end"},children:[dzFlChamp(dzT("vfx.commun.prereglage"),r.jsx(re,'
    '{value:f.pre,options:opts,onChange:prereglage})),dzFlChamp(dzT("photolab.param.type"),r.jsx(re,{value:f.type,opt'
    'ions:types,onChange:function(v){champ("type",v)}})),dzFlChamp(dzT("reglages.personas.nom"),dzSlSaisie("nom",f.no'
    'm,"LM Studio",function(v){champ("nom",v)}))]}),r.jsxs("div",{style:{display:"grid",gridTemplateColumns:f.type==='
    '"openai"?"minmax(0,2fr) minmax(0,1fr) auto":"minmax(0,1fr) auto",gap:12,alignItems:"end",marginTop:10},children:'
    '[dzFlChamp(dzT("reglages.cles.ollama_url"),dzSlSaisie("url",f.url,f.type==="openai"?"http://127.0.0.1:1234/v1":"'
    'http://127.0.0.1:11434",function(v){champ("url",v)})),f.type==="openai"?dzFlChamp(dzT("reglages.locaux.cle"),dzS'
    'lSaisie("cle",f.cle,dzT("reglages.cles.coller"),function(v){champ("cle",v)},"password")):null,r.jsx(K,{variant:"'
    'outline",size:"sm","data-dzsl":"lire-form",onClick:lireForm,disabled:st.busy||!f.url.trim(),children:dzT("reglag'
    'es.locaux.lire")})]}),r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"minmax(0,2fr) minmax(0,1fr)",gap:'
    '12,alignItems:"end",marginTop:10},children:[dzFlChamp(dzT("reglages.libres.modeles"),dzSlSaisie("modeles",f.mode'
    'les,dzT("reglages.locaux.modeles_aide"),function(v){champ("modeles",v)})),dzFlChamp(dzT("reglages.locaux.defaut"'
    '),st.lus&&st.lus.length?r.jsx(re,{value:f.defaut,options:st.lus.map(function(n){return{value:n,label:n}}),onChan'
    'ge:function(v){champ("defaut",v)}}):dzSlSaisie("defaut",f.defaut,dzT("reglages.libres.defaut_aide"),function(v){'
    'champ("defaut",v)}))]}),r.jsxs("div",{style:{display:"flex",gap:8,marginTop:12,alignItems:"center"},children:[r.'
    'jsx(K,{variant:"primary",icon:"dz-action-enregistrer",size:"sm","data-dzsl":"creer",onClick:creer,disabled:st.bu'
    'sy||!pret,children:dzT("reglages.commun.enregistrer")}),r.jsx(K,{variant:"ghost",size:"sm","data-dzsl":"annuler"'
    ',onClick:function(){maj({ouvert:!1,f:dzSlVide,lus:null,msg:""})},children:dzT("commun.action.annuler")})]})]}):r'
    '.jsx("div",{style:{marginTop:12},children:r.jsx(K,{variant:"outline",size:"sm","data-dzsl":"ajouter",onClick:fun'
    'ction(){maj({ouvert:!0,msg:"",conf:""})},children:dzT("reglages.locaux.ajouter")})}),st.msg||st.err?r.jsx("div",'
    '{"data-dzsl":"msg",style:{fontSize:11,marginTop:8,color:st.err?"var(--red)":dzFlTon(st.ton)},children:st.msg||st'
    '.err}):null]})}'
)
FL_VIDE = 'var dzFlVide={nom:"",base:"",cle:"",modeles:"",defaut:"",pre:""},dzFlRacine='

PAIRES += [
    (FL_VIDE, COMPOSANTS_S + FL_VIDE),                                                                     # S0
    (WM_APPEL, WM_APPEL + ',r.jsx(DzServeursLocaux,{cles:g,onSaved:()=>{m(),No()}})'),                      # S1
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
    """L'inverse exact (lu par avant_dzreglages dans _i18n_l1_aide)."""
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
    if neuf.count("x.useState(") != 731 or neuf.count("v2.8.0") != 4 or neuf.count("DzTracks") != 181:
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
