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

t236 (18/10/2026, plan § t236, spec 2026-10-17 § B3 et 2026-10-18 § 3) — même maillon, mêmes paires, M5 élargi par la
constante BIBLIO (posée devant DzMotionDirection) et l'appel `dzMotionBiblio(e,o,P,f)` dans l'inspecteur, avant
« Personnaliser » : rubrique « Bibliothèque motion » (repliée) —
  - importer un prompt : titre / texte / URL d'attribution (obligatoire) / auteur / thèmes (noms des fiches maison),
    attribution montrée en direct, aperçu du bloc de précisions (titre, règle, les 5 précisions de
    GET /api/motion/personnalisation) ; POST /api/motion/biblio ;
  - installer un skill `owner/repo[:chemin]` : « Lire la licence » → POST /api/motion/skills/apercu (route neuve de
    t236, rien d'écrit), licence montrée (identifiant, fichier, texte) AVANT « Installer sous licence X » →
    POST /api/motion/skills/installer {source, licence} (refus si la licence a changé entre-temps) ;
  - liste des prompts et skills filtrable par thème, attribution (lien vers la fiche / le dépôt, auteur, licence),
    « Utiliser » (pose la source), « Supprimer » après confirmation (DELETE, source vidée si c'était elle) ;
  - après chaque import / installation / suppression : dzMoCharger(true) → la liste Source se rafraîchit.
  Rien ne part sur le réseau sans un clic. La saisie vit dans le magasin module `dzMoBib` (par nœud) et se redessine
  par l'état de rafraîchissement existant : AUCUN hook neuf (dzMoUS 2, dzMoUE 3). Confirmations hors couche 24 → 25.
  Banc : backend/tests/test_studio_motion_biblio.py (et test_motion_skill_apercu.py pour la route).

t238 (19/10/2026, plan § t238, option B « Motion code » validée par l'utilisateur) — même maillon, famille C :
  - M1 : le nœud neuf `MotionCode` (« Rendu motion code », catégorie motion) : entrées `direction` et `script`, sortie
    `out` de type av, propriétés script / durationS / fps / pageId ; M2 le range dans « Animations », M3 son encart
    (page écrite ou non), M4 son inspecteur `DzMotionCode` ;
  - M5 : la constante CODE (posée devant DzAnimation) : `dzMotionCodePayload` = le corps de t234 compilé par
    `dzMotionPayload` (direction reliée, script relié ou champ, format, durée) + la cadence ; « Écrire la page » →
    POST /api/motion/code/ecrire (le moteur de Direction motion écrit la page ; coût estimé et plafond AVANT l'appel,
    côté serveur), bilan (moteur, taille, coût, ou repli et sa raison), page en LECTURE SEULE (texte d'une zone de
    saisie, jamais un document : elle ne s'exécute que dans le bac à sable du serveur) ;
  - M8 : la base de l'Animation reliée à un MotionCode = {source_kind:"motion_code", page_id, aspect, fps, duree_s} de
    l'Animation (le serveur rend la page au rendu) ; M9 : sans page écrite, la compilation le dit au lieu d'un fond
    uni ; M10 : un MotionCode relié à l'entrée `in` du Rendu (sans Animation) → POST /api/motion/code/rendre (job).
  UN hook neuf (l'état de DzMotionCode) : dzMoUS 2 → 3 ; aucun dzMoUE ni confirmation neufs.
  Banc : backend/tests/test_studio_motion_code.py (et test_motion_code.py pour le serveur et le bac à sable).

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
HOOKS = 3                       # appels à l'alias dzMoUS (voir l'en-tête ; t238 : + l'état de DzMotionCode)

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

BIBLIO = (
    'function dzMoBibEtat(id){return dzMoBib[id]||(dzMoBib[id]={ti:"",tx:"",u:"",au:"",th:[],sk:"",ap:null,fl:"",msg:"",'
    'err:!1,busy:""})}'
    'function dzMoEnvoyer(u,m,b){return fetch(u,{method:m,headers:{"Content-Type":"application/json"},'
    'body:b==null?void 0:JSON.stringify(b)}).then(function(r_){return r_.json().catch(function(){return null})'
    '.then(function(j){return{ok:r_.ok,j:j}})}).catch(function(){return{ok:!1,j:null}})}'
    'function dzMoThemes(){return(dzMoCache.lst||[]).filter(function(z){return z.nature==="style"}).map(function(z){'
    'return{id:String((z.themes||[])[0]||z.id),titre:dzMoTitre(z)}})}'
    'function dzMotionBiblio(e,o,P,f){var B=dzMoBibEtat(e.id),C=dzMoCache,pe=C.perso,TH=dzMoThemes(),busy=!!B.busy,'
    'u=String(B.u||"").trim(),au=String(B.au||"").trim(),pret=!!(String(B.ti).trim()&&String(B.tx).trim()&&u),'
    'lst=(C.lst||[]).filter(function(z){return(z.nature==="prompt"||z.nature==="skill")&&(!B.fl||(z.themes||[]).indexOf(B.fl)>=0)}),'
    'k_=[],a=B.ap;'
    'function m(k,v){B[k]=v;f()}'
    'function dit(t,err){B.msg=t;B.err=!!err;B.busy="";f()}'
    'function nomTh(t){var z=TH.find(function(q){return q.id===t});return z?z.titre:t}'
    'async function importer(){if(!pret){dit(dzT("studio.motion.bib_import_manque"),!0);return}B.busy="import";B.msg="";f();'
    'var R_=await dzMoEnvoyer("/api/motion/biblio","POST",{titre:B.ti,texte:B.tx,url:u,auteur:B.au,themes:B.th.slice()});'
    'if(!R_.ok||!R_.j||!R_.j.id){dit(dzMotionErreur(R_.j),!0);return}B.ti="";B.tx="";B.u="";B.au="";B.th=[];'
    'await dzMoCharger(!0);dit(dzT("studio.motion.bib_import_fait",{titre:R_.j.titre}))}'
    'async function lire(){var s_=String(B.sk||"").trim();if(!s_)return;B.busy="lire";B.ap=null;B.msg="";f();'
    'var R_=await dzMoEnvoyer("/api/motion/skills/apercu","POST",{source:s_});'
    'if(!R_.ok||!R_.j||!R_.j.licence){dit(dzMotionErreur(R_.j),!0);return}B.ap=Object.assign({},R_.j,{sk:s_});dit("")}'
    'async function installer(){var a_=B.ap;if(!a_)return;B.busy="installer";B.msg="";f();'
    'var R_=await dzMoEnvoyer("/api/motion/skills/installer","POST",{source:a_.sk,licence:a_.licence});B.ap=null;'
    'if(!R_.ok||!R_.j||!R_.j.id){dit(dzMotionErreur(R_.j),!0);return}B.sk="";await dzMoCharger(!0);'
    'dit(dzT("studio.motion.bib_skill_fait",{titre:dzMoTitre(R_.j),licence:R_.j.licence}))}'
    'async function supprimer(z){if(!(await window.__dzDialogue.confirmer(dzT("studio.motion.bib_supprimer_q",{titre:dzMoTitre(z)}),'
    '{titre:dzT("studio.motion.bib_titre"),ok:dzT("studio.motion.bib_supprimer")})))return;B.busy="suppr";B.msg="";f();'
    'var R_=await dzMoEnvoyer("/api/motion/biblio/"+encodeURIComponent(z.id),"DELETE");if(!R_.ok){dit(dzMotionErreur(R_.j),!0);return}'
    'String(P.source||"")===z.id&&(o("source",""),o("consigne",""));delete C.fiches[z.id];await dzMoCharger(!0);'
    'dit(dzT("studio.motion.bib_supprime",{titre:dzMoTitre(z)}))}'
    'B.msg&&k_.push(r.jsx("div",{"data-dz-motion":"bib-message",role:"status",style:{fontSize:11,margin:"0 0 8px",'
    'color:B.err?"var(--red)":"var(--ink-soft)"},children:B.msg},"bm"));'
    # ── importer un prompt ──
    'k_.push(dzMoSous(dzT("studio.motion.bib_importer")),r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-muted)",'
    'marginBottom:8,lineHeight:1.35},children:dzT("studio.motion.bib_import_aide")},"ia"),'
    'r.jsx(O,{label:dzT("studio.motion.bib_champ_titre"),children:r.jsx(le,{"data-dz-motion":"bib-titre",value:B.ti,maxLength:200,'
    'onChange:function(w){m("ti",w)}})},"bt"),'
    'r.jsx(O,{label:dzT("studio.motion.bib_champ_texte"),children:r.jsx("textarea",{"data-dz-motion":"bib-texte",value:B.tx,'
    'maxLength:20000,rows:5,onChange:function(ev){m("tx",ev.target.value)},style:dzMoTA})},"bx"),'
    'r.jsx(O,{label:dzT("studio.motion.bib_champ_url"),hint:dzT("studio.motion.bib_champ_url_aide"),children:r.jsx(le,'
    '{"data-dz-motion":"bib-url",value:B.u,maxLength:2048,placeholder:"https://",onChange:function(w){m("u",w)}})},"bu"),'
    'r.jsx(O,{label:dzT("studio.motion.bib_champ_auteur"),children:r.jsx(le,{"data-dz-motion":"bib-auteur",value:B.au,maxLength:120,'
    'onChange:function(w){m("au",w)}})},"ba"),'
    'r.jsx(O,{label:dzT("studio.motion.bib_champ_themes"),children:r.jsx("div",{style:{display:"flex",flexWrap:"wrap",gap:4},'
    'children:TH.map(function(t){var on=B.th.indexOf(t.id)>=0;return r.jsx("button",{"data-dz-motion":"bib-theme-"+t.id,'
    '"aria-pressed":on,onClick:function(){m("th",on?B.th.filter(function(q){return q!==t.id}):B.th.concat([t.id]))},'
    'style:Object.assign({},dzMoBTN,on?{background:"var(--nd-motion)",color:"#04121c",borderColor:"var(--nd-motion)"}:{}),'
    'children:t.titre},t.id)})})},"bth"),'
    'r.jsx("div",{"data-dz-motion":"bib-attribution",style:{fontSize:11,color:u?"var(--ink-soft)":"var(--amber)",marginBottom:6,'
    'wordBreak:"break-all"},children:u?au?dzT("studio.motion.bib_attribution",{auteur:au,url:u}):'
    'dzT("studio.motion.bib_attribution_url",{url:u}):dzT("studio.motion.bib_attribution_vide")},"bat"),'
    'pe&&pe.precisions?r.jsxs("div",{"data-dz-motion":"bib-apercu",style:{fontSize:11,lineHeight:1.4,padding:"6px 8px",'
    'borderRadius:6,border:"1px dashed var(--stroke-strong)",background:"var(--bg-base)",color:"var(--ink-soft)",marginBottom:6},'
    'children:[r.jsx("div",{style:{color:"var(--ink-muted)",marginBottom:2},children:dzT("studio.motion.bib_apercu_aide")},"q0"),'
    'r.jsx("div",{style:{color:"var(--ink)"},children:dzT("studio.motion.apercu_regle",{titre:dzMoLoc(pe.precisions.titre),'
    'regle:dzMoLoc(pe.precisions.regle)})},"q1")].concat((pe.precisions.champs||[]).map(function(c){return r.jsx("div",'
    '{children:dzT("studio.motion.bib_apercu_champ",{libelle:dzMoLoc(c.libelle)})},"q-"+c.id)}))},"bap"):null,'
    'r.jsx("button",{"data-dz-motion":"bib-importer",disabled:busy||!pret,title:pret?void 0:dzT("studio.motion.bib_import_manque"),'
    'onClick:importer,style:Object.assign({},dzMoBTN,{marginBottom:6,cursor:busy||!pret?"default":"pointer",opacity:busy||!pret?.5:1}),'
    'children:B.busy==="import"?dzT("studio.motion.en_cours"):dzT("studio.motion.bib_importer_ok")},"bi"));'
    # ── installer un skill ──
    'k_.push(dzMoSous(dzT("studio.motion.bib_skill")),r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-muted)",marginBottom:8,'
    'lineHeight:1.35},children:dzT("studio.motion.bib_skill_aide")},"sa"),'
    'r.jsx(O,{label:dzT("studio.motion.bib_skill_source"),children:r.jsx(le,{"data-dz-motion":"bib-skill",value:B.sk,maxLength:400,'
    'placeholder:dzT("studio.motion.bib_skill_exemple"),onChange:function(w){B.ap=null;m("sk",w)}})},"bs"),'
    'a?r.jsxs("div",{"data-dz-motion":"bib-licence",style:{padding:8,borderRadius:8,border:"1px solid var(--stroke-strong)",'
    'background:"var(--surface-2)",marginBottom:6},children:[r.jsx("div",{style:{fontSize:12,fontWeight:600,color:"var(--ink-strong)"},'
    'children:dzT("studio.motion.bib_skill_de",{titre:dzMoTitre(a),depot:(a.source&&a.source.depot)||""})},"l0"),'
    'a.description?r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)",margin:"2px 0 4px"},children:a.description},"l1"):null,'
    'r.jsx("div",{"data-dz-motion":"bib-licence-id",style:{fontSize:11,color:"var(--ink)",margin:"4px 0"},'
    'children:dzT("studio.motion.bib_skill_licence",{licence:a.licence,fichier:a.fichier_licence||""})},"l2"),'
    'r.jsx("textarea",{readOnly:!0,"data-dz-motion":"bib-licence-texte",value:String(a.licence_texte||""),rows:6,style:dzMoTA},"l3"),'
    'r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-muted)",margin:"4px 0 6px"},children:dzT("studio.motion.bib_skill_confirmer_aide")},"l4"),'
    'r.jsxs("div",{style:{display:"flex",gap:6},children:[r.jsx("button",{"data-dz-motion":"bib-installer",disabled:busy,'
    'onClick:installer,style:Object.assign({},dzMoBTN,{fontWeight:600}),children:B.busy==="installer"?dzT("studio.motion.en_cours"):'
    'dzT("studio.motion.bib_skill_installer",{licence:a.licence})},"l5"),r.jsx("button",{"data-dz-motion":"bib-annuler",disabled:busy,'
    'onClick:function(){m("ap",null)},style:dzMoBTN,children:dzT("studio.motion.bib_annuler")},"l6")]},"l7")]},"bl"):'
    'r.jsx("button",{"data-dz-motion":"bib-lire",disabled:busy||!String(B.sk||"").trim(),onClick:lire,'
    'style:Object.assign({},dzMoBTN,{marginBottom:6,opacity:busy||!String(B.sk||"").trim()?.5:1}),'
    'children:B.busy==="lire"?dzT("studio.motion.bib_skill_lecture"):dzT("studio.motion.bib_skill_lire")},"bl"));'
    # ── la liste ──
    'k_.push(dzMoSous(dzT("studio.motion.bib_liste")),r.jsx(O,{label:dzT("studio.motion.bib_filtre"),children:r.jsx(re,'
    '{value:B.fl,options:[{value:"",label:dzT("studio.motion.bib_filtre_tous")}].concat(TH.map(function(t){'
    'return{value:t.id,label:t.titre}})),onChange:function(w){m("fl",w)}})},"bf"),'
    'lst.length?r.jsx("div",{"data-dz-motion":"bib-liste",children:lst.map(function(z){var sk_=z.nature==="skill",'
    'url=sk_?z.source&&z.source.url:z.url,on=String(P.source||"")===z.id,'
    'inf=[sk_?dzT("studio.motion.bib_nature_skill",{licence:z.licence||""}):dzT("studio.motion.bib_nature_prompt")]'
    '.concat(z.auteur?[dzT("studio.motion.bib_par",{auteur:z.auteur})]:[]).concat(sk_&&z.source&&z.source.depot?[z.source.depot]:[])'
    '.concat((z.themes||[]).map(nomTh));'
    'return r.jsxs("div",{"data-dz-motion":"bib-"+z.id,style:{padding:"6px 8px",borderRadius:6,border:"1px solid var(--stroke)",'
    'background:"var(--bg-base)",marginBottom:6},children:[r.jsx("div",{title:dzMoTitre(z),style:{fontSize:12,fontWeight:600,'
    'color:"var(--ink-strong)",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},children:dzMoTitre(z)},"t"),'
    'r.jsx("div",{"data-dz-motion":"bib-info",style:{fontSize:10.5,color:"var(--ink-muted)",margin:"2px 0 4px"},'
    'children:inf.join(" · ")},"i"),r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:6},children:['
    'url?r.jsx("a",{href:url,target:"_blank",rel:"noopener noreferrer","data-dz-motion":"bib-lien",style:{flex:1,fontSize:11,'
    'color:"var(--cyan)"},children:sk_?dzT("studio.motion.bib_depot"):dzT("studio.motion.bib_fiche")},"a"):'
    'r.jsx("span",{style:{flex:1}},"a"),r.jsx("button",{"data-dz-motion":"bib-utiliser",disabled:on,onClick:function(){'
    'o("source",z.id);o("consigne","")},style:Object.assign({},dzMoBTN,{opacity:on?.5:1}),'
    'children:on?dzT("studio.motion.bib_utilisee"):dzT("studio.motion.bib_utiliser")},"u"),'
    'r.jsx("button",{"data-dz-motion":"bib-supprimer",disabled:busy,onClick:function(){return supprimer(z)},style:dzMoBTN,'
    'children:dzT("studio.motion.bib_supprimer")},"s")]},"b")]},z.id)})},"bli"):'
    'r.jsx("div",{"data-dz-motion":"bib-vide",style:{fontSize:11,color:"var(--ink-soft)",marginBottom:6},'
    'children:dzT("studio.motion.bib_vide")},"bv"));'
    'return r.jsx(ie,{label:dzT("studio.motion.bib_titre"),defaultOpen:!1,children:r.jsx("div",{"data-dz-motion":"biblio",'
    'style:{padding:"0 0 6px"},children:k_})})}'
)

FONCTIONS = (
    'var dzMoUS=x.useState,dzMoUE=x.useEffect,dzMoMAX=8000,dzMoCache={lst:null,mot:null,mods:{},effs:{},fiches:{},perso:null,'
    'p:null,pm:null,pp:null},dzMoPile={},dzMoBib={},dzMoTA=' + TA + ',dzMoBTN=' + BTN + ','
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
    'c==="modele_fautif"?dzT("studio.motion.raison_modele_fautif"):c==="sortie_invalide"?dzT("studio.motion.raison_sortie_invalide"):'
    'c==="delai"?dzT("studio.motion.raison_delai"):c==="erreur_moteur"?dzT("studio.motion.raison_erreur_moteur"):""}'
    'function dzMotionCout(c){var n=c&&c.nature;return n==="gratuit"?dzT("studio.motion.cout_bilan_gratuit"):'
    'n==="a_mesurer"?dzT("studio.motion.cout_bilan_a_mesurer"):'
    'dzT("studio.motion.cout_bilan_payant",{usd:Number((c&&c.estime_usd)||0).toFixed(4)})}'
    'function dzMotionBilan(j){var n=(j.elements||[]).length;return j.repli?'
    'dzT("studio.motion.bilan_repli",{n:n,raison:dzMotionRaison(j.raison)}):'
    'dzT("studio.motion.bilan",{n:n,moteur:j.moteur+(j.modele?" · "+j.modele:""),cout:dzMotionCout(j.cout)})}'
    'function dzMotionErreur(j,k){var d=j&&j.detail;return typeof d==="string"&&d?d:d&&typeof d.message==="string"&&d.message?'
    'd.message:dzT(k||"studio.motion.echec")}'
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
    + BIBLIO +
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
    'dzMotionBiblio(e,o,P,f),dzMotionPerso(P,o,g,e,nat),'
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

CODE = (
    'var dzMoCode={};'
    'function dzMoKo(n){return dzT("studio.motion.code_ko",{n:(Math.max(0,Number(n)||0)/1024).toFixed(1)})}'
    'function dzMotionCodePayload(g,a){var c=dzMotionPayload(g,a),P=dzMoProps(a);delete c.images;'
    'c.fps=Math.min(60,Math.max(12,Math.round(Number(P.fps)||30)));return c}'
    'function dzMotionCodeBase(b3,anim,n){var P=dzMoProps(b3);return P.pageId?{source_kind:"motion_code",'
    'page_id:String(P.pageId),aspect:n,fps:Number(anim.props&&anim.props.fps)||30,'
    'duree_s:Number(anim.props&&anim.props.durationS)||8}:null}'
    'function dzMotionCodeRendu(g,mc,n,o){var P=dzMoProps(mc);if(!P.pageId)return{ok:!1,error:dzT("studio.motion.code_sans_page")};'
    'var corps={page_id:String(P.pageId),aspect:n,fps:Number(P.fps)||30,duree_s:Number(P.durationS)||8,title:o,source_graph:g};'
    'return{ok:!0,summary:dzT("studio.motion.code_resume",{id:String(P.pageId)}),run:function(){'
    'return fetch("/api/motion/code/rendre",{method:"POST",headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify(corps)}).then(function(r3){return r3.ok?r3.json():{ok:!1,error:dzT("studio.motion.code_rendre_echec")}})}}}'
    'function dzMotionCodeBilan(j){var t=dzMoKo(j.taille);return j.repli?dzT("studio.motion.code_bilan_repli",{taille:t,'
    'raison:j.raison==="page_refusee"?dzT("studio.motion.code_raison_refusee",{motifs:String(j.refus_texte||"")}):'
    'dzMotionRaison(j.raison)}):dzT("studio.motion.code_bilan",{moteur:j.moteur+(j.modele?" · "+j.modele:""),taille:t,'
    'cout:dzMotionCout(j.cout)})}'
    'function dzMotionCodeEncart(P){var id=String(P.pageId||""),s=id?dzT("studio.motion.code_encart",{id:id}):'
    'dzT("studio.motion.code_encart_vide");return r.jsxs("div",{title:s,"data-dz-motion":"code-encart",style:{width:"100%",'
    'height:"100%",display:"flex",alignItems:"center",gap:6,padding:"0 10px",boxSizing:"border-box",background:"#0b1016",'
    'color:"var(--nd-motion)",fontSize:11},children:[r.jsx(X,{name:"dz-cat-animation",size:12}),'
    'r.jsx("span",{style:{minWidth:0,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},children:s})]})}'
    'function DzMotionCode({node:e,graph:g,set:o}){var st_=dzMoUS(null),et=st_[0],setEt=st_[1],P=dzMoProps(e),'
    'pid=String(P.pageId||""),dn=dzMotionDirection(g,e),sn=Wt(g,e.id,"script"),busy=!!(et&&et.busy),cd=pid?dzMoCode[pid]:null;'
    'function vu(){setEt(function(z){return Object.assign({},z||{})})}'
    'if(!dzMoCache.lst&&!dzMoCache.p)dzMoCharger().then(vu);'
    'if(pid&&cd===void 0){dzMoCode[pid]=null;dzMoJson("/api/motion/code/"+encodeURIComponent(pid)).then(function(j){'
    'dzMoCode[pid]=j&&typeof j.html==="string"?j:!1;vu()})}'
    'async function ecrire(){var c=dzMotionCodePayload(g,e);if(!c.script.trim()){'
    'setEt({err:!0,msg:dzT("studio.motion.script_vide")});return}setEt({busy:!0,msg:dzT("studio.motion.code_en_cours_aide")});'
    'try{var rq=await fetch("/api/motion/code/ecrire",{method:"POST",headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify(c)}),j=await rq.json().catch(function(){return null});'
    'if(!rq.ok||!j||!j.page_id){setEt({err:!0,msg:dzMotionErreur(j,"studio.motion.code_echec")});return}'
    'delete dzMoCode[j.page_id];o("pageId",j.page_id);setEt({msg:dzMotionCodeBilan(j)})}'
    'catch(_e){setEt({err:!0,msg:dzT("studio.motion.code_echec")})}}'
    'var dl=dn?dzT("studio.motion.direction_reliee",{resume:dzMotionResume(dzMoProps(dn))}):dzT("studio.motion.direction_absente");'
    'return r.jsxs(ie,{label:dzT("studio.motion.code_titre"),children:['
    'r.jsx("div",{"data-dz-motion":"code-direction",title:dl,style:{fontSize:11,color:"var(--ink-soft)",marginBottom:6,'
    'overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},children:dl}),'
    'sn?r.jsx("div",{"data-dz-motion":"code-script-relie",style:{fontSize:11,color:"var(--ink-soft)",marginBottom:6},'
    'children:dzT("studio.motion.script_relie",{titre:(Me[sn.type]&&Me[sn.type].title)||sn.type})}):'
    'r.jsx(O,{label:dzT("studio.motion.script"),children:r.jsx("textarea",{"data-dz-motion":"code-script",'
    'value:String(P.script||""),onChange:function(ev){o("script",ev.target.value)},rows:4,'
    'placeholder:dzT("studio.motion.script_aide"),style:dzMoTA})}),'
    'r.jsx(O,{label:dzT("studio.motion.duree"),children:r.jsx(le,{"data-dz-motion":"code-duree",type:"number",min:1,max:60,'
    'value:String(P.durationS==null?"":P.durationS),onChange:function(w){o("durationS",w===""?"":Number(w))}})}),'
    'r.jsx(O,{label:dzT("studio.motion.code_fps"),children:r.jsx(le,{"data-dz-motion":"code-fps",type:"number",min:12,max:60,'
    'value:String(P.fps==null?"":P.fps),onChange:function(w){o("fps",w===""?"":Number(w))}})}),'
    'r.jsx("button",{"data-dz-motion":"code-ecrire",onClick:ecrire,disabled:busy,style:{width:"100%",fontSize:12,'
    'fontWeight:600,padding:"7px",borderRadius:7,border:"none",background:"var(--nd-motion)",color:"#04121c",'
    'cursor:busy?"default":"pointer"},children:busy?dzT("studio.motion.code_en_cours"):pid?dzT("studio.motion.code_reecrire"):'
    'dzT("studio.motion.code_ecrire")}),'
    'et&&et.msg?r.jsx("div",{"data-dz-motion":"code-message",role:"status",style:{fontSize:11,marginTop:6,'
    'color:et.err?"var(--red)":"var(--ink-soft)"},children:et.msg}):null,'
    'r.jsx("div",{"data-dz-motion":"code-page",style:{fontSize:11,marginTop:6,color:pid?"var(--ink)":"var(--amber)"},'
    'children:pid?dzT("studio.motion.code_page",{id:pid,taille:cd&&cd.taille!=null?dzMoKo(cd.taille):"—"}):'
    'dzT("studio.motion.code_sans_page")}),'
    'r.jsx("div",{"data-dz-motion":"code-bac",style:{fontSize:10.5,marginTop:4,color:"var(--ink-muted)",lineHeight:1.4},'
    'children:dzT("studio.motion.code_bac")}),'
    'pid?r.jsx(ie,{label:dzT("studio.motion.code_lecture"),defaultOpen:!1,children:r.jsx("textarea",{readOnly:!0,'
    '"data-dz-motion":"code-html",value:cd&&cd.html?cd.html:"",rows:10,spellCheck:!1,style:Object.assign({},dzMoTA,'
    '{fontFamily:"var(--font-mono, monospace)",fontSize:11})})}):null]})}'
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
     'outPorts:[{id:"direction",type:"direction"}],props:{style:"style-kinetic-type",source:"",consigne:"",moteur:"",modele:""}},'
     'MotionCode:{cat:"motion",title:dzT("studio.motion.code_titre"),desc:dzT("studio.motion.code_desc"),'
     'inPorts:[{id:"direction",type:"direction"},{id:"script",type:"text"}],outPorts:[{id:"out",type:"av"}],'
     'props:{script:"",durationS:8,fps:30,pageId:""}},'),
    ('{cat:"motion",types:["Animation"]}',                                                                      # M2
     '{cat:"motion",types:["Animation","MotionDirection","MotionCode"]}'),
    ('):n==="Animation"?r.jsxs(',                                                                               # M3
     '):n==="MotionCode"?dzMotionCodeEncart(o):n==="MotionDirection"?dzMotionEncart(o):n==="Animation"?r.jsxs('),
    ('e.type==="Animation"?r.jsx(DzAnimation,{node:e,graph:g,set:o}):',                                         # M4
     'e.type==="MotionCode"?r.jsx(DzMotionCode,{node:e,graph:g,set:o}):'
     'e.type==="MotionDirection"?r.jsx(DzMotionDirection,{node:e,graph:g,set:o}):'
     'e.type==="Animation"?r.jsx(DzAnimation,{node:e,graph:g,set:o}):'),
    ('function DzAnimation({node:e,graph:g,set:o}){',                                                          # M5
     FONCTIONS + CODE + 'function DzAnimation({node:e,graph:g,set:o}){'),
    ('var ms=x.useState("from"),mode=ms[0],setMode=ms[1];',                                                    # M6
     HOOKS_ANIM + 'var ms=x.useState("from"),mode=ms[0],setMode=ms[1];'),
    ('children:"+ Image"})]}),els.length?',                                                                     # M7
     'children:"+ Image"})]}),moBloc(),els.length?'),
    ('if(dzIsImgNode(b3))return b3.props&&b3.props.filename?{source_kind:"upload",upload_filename:b3.props.filename}:null;'  # M8
     'return null};',
     'if(b3.type==="MotionCode")return dzMotionCodeBase(b3,anim,n);'
     'if(dzIsImgNode(b3))return b3.props&&b3.props.filename?{source_kind:"upload",upload_filename:b3.props.filename}:null;'
     'return null};'),
    ('var bn=Wt(e,anim.id,"base"),aEls=(anim.props&&anim.props.elements)||[];',                                   # M9
     'var bn=Wt(e,anim.id,"base"),aEls=(anim.props&&anim.props.elements)||[];'
     'if(bn&&bn.type==="MotionCode"&&!(bn.props&&bn.props.pageId))return{ok:!1,error:dzT("studio.motion.code_sans_page")};'),
    ('return{ok:!1,error:dzT("studio.compil.impossible")}}const Zi={',                                           # M10
     'var mcN=Wt(e,t.id,"in");if(mcN&&mcN.type==="MotionCode")return dzMotionCodeRendu(e,mcN,n,o);'
     'return{ok:!1,error:dzT("studio.compil.impossible")}}const Zi={'),
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
