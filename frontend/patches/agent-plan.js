/* t285 T9 (24/10/2026) — le mode « Agent Campagnes » du dialogue « Generate a marketing plan » du Planificateur
   (spec docs/superpowers/specs/2026-10-23-agent-interne-design.md §6). Source du maillon de queue
   scripts/patch_bundle_dzagentplan.py, injectée APLATIE (une ligne) devant la fonction du dialogue (Um). Règles
   d'écriture : chaque instruction finit par « ; » ou « } », aucune ligne ne commence par « ( » « [ » ou « // »,
   commentaires « /* » sur des lignes entières seulement.
   - __dzAgentPlanMode() : l'état du sélecteur, « rapide » par défaut (le code d'origine du dialogue, inchangé) ;
   - DzAgentPlanBascule : Rapide / Agent Campagnes, dans l'en-tête du dialogue ;
   - __dzAgentPlanBrief(brief, debut, jours, depot) : le PREMIER message, posé dans le champ du composant (l'envoi
     reste à l'utilisateur, après le devis) : le brief, la période en clair, le nom du document déposé ;
   - __dzAgentPlanDeposer(espace, fichier) : la conversation naît (POST /api/agent/campagnes/), puis le document va
     en dépôt (POST /{cid}/depot, multipart « fichier ») ; l'agent le lit avec lire_document ;
   - __dzAgentPlanMonter(hote, o) : window.DzCampagnes.monter (frontend/shared/dz-campagnes.js) ; null s'il manque ;
   - DzAgentPlan : le panneau. L'espace se choisit ICI, avant le montage (espaces non archivés, l'actif par défaut),
     puis il est figé : le composant l'affiche sans pouvoir le changer. Démonté au changement de mode et à la
     fermeture du dialogue.
   Les brouillons au calendrier : le Planificateur écoute déjà « deepotus:schedule-reload » (reloadPosts). Le lien de
   la carte « brouillons » émet « dz-campagnes-brouillons » : on recharge le calendrier et, SI l'espace des brouillons
   est l'espace actif (relu à ce moment), on ferme le dialogue ; sinon le dialogue reste ouvert avec une ligne qui le
   dit (GET /api/schedule ne rend que l'espace actif). Au démontage d'une conversation ouverte, on recharge aussi.
   Correctifs de relecture (24/10) : une ligne sous le sélecteur quand l'espace choisi n'est pas l'actif ; bouton
   désactivé tant que la liste des espaces n'est pas là ; window.__dzEspActiver = l'activation de la coque
   (dzEspActiver : POST /activate, cache des espaces relu, « deepotus:espace-refresh ») pour la carte « brouillons »
   de dz-campagnes.js, qui active l'espace sur un clic de l'utilisateur.
   Hooks par alias (compte figé des bancs). Textes : clés dzT campagnes.plan.* (frontend/shared/i18n/campagnes.json). */
function __dzAgentPlanMode(){/*__dzagentplan*/var US=x.useState;return US("rapide");}
try{if(typeof dzEspActiver==="function")window.__dzEspActiver=dzEspActiver;}catch(e){}
function __dzAgentPlanActif(){return fetch("/api/espaces").then(function(R){return R.ok?R.json():null;}).then(function(d){return d&&d.actif||null;}).catch(function(){return null;});}
function __dzAgentPlanRecharger(){try{window.dispatchEvent(new CustomEvent("deepotus:schedule-reload"));}catch(e){}}
function __dzAgentPlanBrief(brief,debut,jours,depot){
  var t=String(brief||"").trim(),plus=[];
  if(debut&&jours)plus.push(dzT("campagnes.plan.periode_message",{debut:debut,n:jours}));
  else if(debut)plus.push(dzT("campagnes.plan.debut_message",{debut:debut}));
  if(depot)plus.push(dzT("campagnes.plan.document_message",{nom:depot}));
  return plus.length?(t?t+"\n\n":"")+plus.join("\n"):t;}
function __dzAgentPlanErreur(R){
  return R.json().catch(function(){return{};}).then(function(j){
    if(!R.ok)throw new Error(j&&j.detail?String(j.detail):dzT("campagnes.erreur.http",{code:R.status}));
    return j;});}
function __dzAgentPlanDeposer(espace,fichier){
  var corps={role:"campagnes"};
  if(espace)corps.espace_id=espace;
  return fetch("/api/agent/campagnes/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(corps)}).then(__dzAgentPlanErreur).then(function(c){
    var fd=new FormData();
    fd.append("fichier",fichier,fichier.name||"document");
    return fetch("/api/agent/campagnes/"+encodeURIComponent(c.id)+"/depot",{method:"POST",body:fd}).then(__dzAgentPlanErreur).then(function(j){
      return{cid:c.id,depot:j.depot||fichier.name};});});}
function __dzAgentPlanDispo(){var C=window.DzCampagnes;return !!(C&&typeof C.monter==="function");}
function __dzAgentPlanMonter(hote,o){
  var C=window.DzCampagnes;
  if(!hote||!C||typeof C.monter!=="function")return null;
  var opts={role:"campagnes",espace_id:o.espace_id||void 0,brief:o.brief||"",contexte:"planificateur"};
  if(o.cid)opts.cid=o.cid;
  if(o.surCid)opts.surCid=o.surCid;
  try{return C.monter(hote,opts);}catch(e){return null;}}
function DzAgentPlanBascule(p){
  var m=p.mode;
  function b(v,k){return r.jsx("button",{type:"button","data-dzagentplan-mode":v,"aria-pressed":m===v?"true":"false",onClick:function(){if(m!==v)p.choisir(v);},style:{height:26,padding:"0 12px",background:m===v?"var(--bg-panel)":"transparent",border:0,borderRadius:4,cursor:"pointer",color:m===v?"var(--ink-strong)":"var(--ink-soft)",fontSize:11.5,fontWeight:500},children:dzT(k)},v);}
  return r.jsx("div",{role:"group","aria-label":dzT("campagnes.plan.mode"),"data-dzagentplan":"bascule",style:{display:"flex",gap:2,padding:3,background:"var(--bg-base)",borderRadius:"var(--r-sm)",border:"1px solid var(--stroke)"},children:[b("rapide","campagnes.plan.rapide"),b("agent","campagnes.plan.agent")]});}
function DzAgentPlan(p){
  var US=x.useState,UE=x.useEffect,UR=x.useRef;
  var s1=US(null),esp=s1[0],setEsp=s1[1];
  var s2=US(""),choix=s2[0],setChoix=s2[1];
  var s3=US(null),doc=s3[0],setDoc=s3[1];
  var s4=US(null),conv=s4[0],setConv=s4[1];
  var s5=US(""),err=s5[0],setErr=s5[1];
  var s6=US(!1),occ=s6[0],setOcc=s6[1];
  var s7=US(null),actif=s7[0],setActif=s7[1];
  var hote=UR(null),cidRef=UR(null),fileRef=UR(null),fermer=UR(p.fermer);
  fermer.current=p.fermer;
  UE(function(){var on=!0;
    fetch("/api/espaces").then(function(R){return R.ok?R.json():null;}).then(function(d){
      if(!on)return;
      var l=(d&&Array.isArray(d.espaces)?d.espaces:[]).filter(function(z){return z&&z.id&&!z.archive;});
      var a=d&&d.actif;
      setEsp(l);
      setActif(a||null);
      setChoix(l.some(function(z){return z.id===a;})?a:(l[0]?l[0].id:""));}).catch(function(){if(on)setEsp([]);});
    function surBrouillons(ev){
      __dzAgentPlanRecharger();
      var e=ev&&ev.detail&&ev.detail.espace_id||null;
      __dzAgentPlanActif().then(function(a){
        if(!on)return;
        if(a)setActif(a);
        if(!e||a===e){var f=fermer.current;if(f)f();}
        else setErr(dzT("campagnes.plan.brouillons_inactif"));});}
    window.addEventListener("dz-campagnes-brouillons",surBrouillons);
    return function(){on=!1;window.removeEventListener("dz-campagnes-brouillons",surBrouillons);};},[]);
  UE(function(){
    if(!conv)return;
    cidRef.current=conv.cid||null;
    var h=__dzAgentPlanMonter(hote.current,{cid:conv.cid,espace_id:conv.espace,brief:conv.brief,surCid:function(c){cidRef.current=c;}});
    if(!h){setErr(dzT("campagnes.plan.absent"));return;}
    return function(){try{h.demonter();}catch(e){}if(cidRef.current)__dzAgentPlanRecharger();};},[conv]);
  var dispo=__dzAgentPlanDispo();
  function demarrer(){
    if(occ||esp===null)return;
    if(!__dzAgentPlanDispo()){setErr(dzT("campagnes.plan.absent"));return;}
    setErr("");
    var brief=p.brief,espace=choix;
    if(!doc){setConv({cid:null,espace:espace,brief:__dzAgentPlanBrief(brief,p.debut,p.jours,null)});return;}
    setOcc(!0);
    __dzAgentPlanDeposer(espace,doc).then(function(o){setOcc(!1);setConv({cid:o.cid,espace:espace,brief:__dzAgentPlanBrief(brief,p.debut,p.jours,o.depot)});}).catch(function(e){setOcc(!1);setErr(dzT("campagnes.plan.echec_depot",{msg:String(e&&e.message||e)}));});}
  var alerte=err?r.jsx("div",{role:"alert","data-dzagentplan-erreur":"",style:{padding:10,background:"var(--red-soft)",border:"1px solid var(--red)",borderRadius:"var(--r-sm)",fontSize:11.5,color:"var(--ink)"},children:err}):null;
  if(conv)return r.jsxs("div",{"data-dzagentplan":"conversation",style:{flex:1,minHeight:0,display:"flex",flexDirection:"column",gap:8,padding:12},children:[alerte,
    r.jsx("div",{ref:hote,"data-dzagentplan-hote":"",style:{flex:"0 0 auto",minHeight:360,height:"min(62vh,560px)",display:"flex",flexDirection:"column",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",overflow:"hidden"}})]});
  var champ={width:"100%",height:30,padding:"0 8px",background:"var(--bg-base)",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",color:"var(--ink-strong)",fontFamily:"var(--f-ui)",fontSize:12};
  var mut={fontSize:10.5,color:"var(--ink-soft)",lineHeight:1.45};
  var nomChoix=(esp||[]).filter(function(z){return z.id===choix;}).map(function(z){return String(z.nom||z.id);})[0]||"";
  var inactif=!!(choix&&actif&&choix!==actif);
  var choixEspace=esp===null?r.jsx("div",{style:mut,children:dzT("espaces.etat.chargement")}):esp.length?r.jsx(re,{value:choix,onChange:function(v){setChoix(v);},options:esp.map(function(z){return{value:z.id,label:String(z.nom||z.id)};})}):r.jsx("div",{style:mut,children:dzT("campagnes.entete.aucun_espace")});
  return r.jsxs("div",{className:"scroll","data-dzagentplan":"panneau",style:{flex:1,overflowY:"auto",padding:18,display:"flex",flexDirection:"column",gap:14},children:[
    r.jsx("div",{style:mut,children:dzT("campagnes.plan.intro")}),
    r.jsx(O,{label:dzT("campagnes.plan.espace"),children:r.jsxs("div",{children:[choixEspace,r.jsx("div",{style:Object.assign({marginTop:4},mut),children:dzT("campagnes.plan.espace_fige")}),inactif?r.jsx("div",{"data-dzagentplan-inactif":"",style:Object.assign({marginTop:4},mut,{color:"var(--amber)"}),children:dzT("campagnes.plan.espace_inactif",{nom:nomChoix})}):null]})}),
    r.jsx(O,{label:dzT("scheduler.plan.brief"),children:r.jsx("textarea",{value:p.brief,"data-dzagentplan-brief":"",onChange:function(ev){p.setBrief(ev.target.value);},rows:3,style:{width:"100%",padding:10,background:"var(--bg-base)",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",color:"var(--ink-strong)",fontFamily:"var(--f-ui)",fontSize:12.5,resize:"vertical"},placeholder:dzT("scheduler.plan.brief_exemple")})}),
    r.jsxs("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10},children:[
      r.jsx(O,{label:dzT("scheduler.plan.date_debut"),children:r.jsx("input",{type:"date",value:p.debut,"data-dzagentplan-debut":"",onChange:function(ev){p.setDebut(ev.target.value);},style:Object.assign({},champ,{fontFamily:"var(--f-mono)",colorScheme:"dark"})})}),
      r.jsx(O,{label:dzT("scheduler.plan.jours"),children:r.jsx(re,{value:String(p.jours),onChange:function(v){p.setJours(Number(v));},options:["3","5","7","14"].map(function(v){return{value:v,label:dzT("scheduler.plan.n_jours",{n:v})};})})})]}),
    r.jsx(O,{label:dzT("campagnes.plan.document"),children:r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"},children:[
      r.jsx("input",{ref:fileRef,type:"file",accept:".md,.markdown,.txt,.docx,.pdf",style:{display:"none"},onChange:function(ev){var f=ev.target.files&&ev.target.files[0];setDoc(f||null);ev.target.value="";}}),
      r.jsx(K,{variant:"outline",size:"sm",icon:"dz-action-importer","data-dzagentplan-joindre":"",onClick:function(){var i=fileRef.current;if(i)i.click();},children:dzT("campagnes.plan.joindre")}),
      doc?r.jsx("span",{className:"mono","data-dzagentplan-doc":"",style:{fontSize:11,color:"var(--ink-strong)"},children:doc.name}):null,
      doc?r.jsx(K,{variant:"outline",size:"sm",icon:"dz-action-fermer",onClick:function(){setDoc(null);},children:dzT("commun.action.retirer")}):null,
      r.jsx("div",{style:Object.assign({width:"100%"},mut),children:dzT("campagnes.plan.document_aide")})]})}),
    alerte,
    dispo?null:r.jsx("div",{style:mut,children:dzT("campagnes.plan.absent")}),
    r.jsx("div",{style:{display:"flex",justifyContent:"flex-end"},children:r.jsx(K,{variant:"primary",size:"md",icon:"dz-action-generer",glow:!0,"data-dzagentplan-demarrer":"",onClick:demarrer,disabled:occ||!dispo||esp===null,children:occ?dzT("campagnes.plan.depot_en_cours"):dzT("campagnes.plan.demarrer")})})]});}
