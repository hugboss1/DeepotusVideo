/* t283 (23/10/2026) — la RECETTE de génération suit le rendu : Bibliothèque → Quick / Studio.
   Source du maillon de queue scripts/patch_bundle_dzrecette.py, injectée APLATIE (une ligne) devant
   `function __dzRelancer(j,ev){`. Règles d'écriture : chaque instruction finit par « ; » ou « } », aucune ligne ne
   commence par « ( » « [ » ou « // », commentaires « /* » sur des lignes entières seulement.
   - __dzRecetteLire(id) : GET /api/jobs/{id}/recette (recette Quick, sinon colonnes du job, sinon recette d'import) ;
   - __dzRecetteQuick(id, garder) : le formulaire Quick pré-rempli ; prompt EXACT (ambiance sans mots-clés ajoutés :
     « hybrid » si le style l'est, « cinematic » sinon) ; graine NEUVE sauf si `garder` (décision du 23/10) ;
   - __dzRecetteStudio(id, garder) : le graphe Image (+ fin) → Seedance ← Prompt (positif et négatif) → Render ;
   - DzRecetteRendu : le panneau « Recette » de la fiche d'un rendu (source, prompt, négatif replié, réglages,
     recette d'import et prompts de ses clips), case « Reprendre la graine d'origine », boutons Quick et Studio ;
   - t346 (29/10/2026) DzRecetteExport : « Exporter la recette » de la fiche (un rendu par son job, tout autre fichier
     par son nom : la lignée remontée) -> GET /api/recettes/export (ZIP : SKILL.md + fabrication.pdf), gratuit, local.
   Le coût n'est jamais repris : Quick et Studio réestiment au tarif du jour. Hooks par alias (compte figé des bancs). */
function __dzGraineNeuve(){/*__dzrecette*/return Math.floor(Math.random()*1e4);}
function __dzRecetteLire(id){
  return fetch("/api/jobs/"+encodeURIComponent(id)+"/recette").then(function(R){return R.ok?R.json():null;}).catch(function(){return null;});}
function __dzRecetteGraine(rc,garder){var g=garder?rc.seed:__dzGraineNeuve();return g==null?"":String(g);}
function __dzRecetteVersQuick(rc,garder){
  var g=__dzRecetteGraine(rc,garder);
  if(rc.quick&&rc.quick.tab){var q=JSON.parse(JSON.stringify(rc.quick));q.seedance=q.seedance||{};q.seedance.seed=g;return q;}
  return{v:1,tab:"seedance",seedance:{image:rc.image||"",end:rc.image_end||"",prompt:rc.prompt||"",
    vibe:rc.style==="hybrid"?"hybrid":"cinematic",model:rc.model||"",duration:rc.duration_s||10,
    aspect:rc.aspect_ratio||"9:16",seed:g,template:rc.template_id||""}};}
function __dzRecetteRefaisable(rc){return !!rc&&(rc.source==="quick"||rc.source==="job")&&!!(rc.prompt||rc.prompt_envoye);}
function __dzRecetteQuick(id,garder){
  __dzRecetteLire(id).then(function(rc){
    if(!rc){__dzToast(dzT("recette.toast.introuvable"));return;}
    if(!__dzRecetteRefaisable(rc)){__dzToast(dzT("recette.toast.rien_a_refaire"));return;}
    if(!rc.quick&&rc.provider==="heygen"){__dzReopenQuick(id);return;}
    var rec=__dzRecetteVersQuick(rc,garder);
    window.__dzQuickRecipe=rec;__dzSendNav("quick");
    setTimeout(function(){window.dispatchEvent(new CustomEvent("deepotus:quick-recipe",{detail:rec}));},60);
    __dzToast(dzT(garder?"recette.toast.quick_ok_graine":"recette.toast.quick_ok",{id:String(id).slice(0,8)}));});}
function __dzRecetteGraphe(rc,garder,nom){
  var g=Number(__dzRecetteGraine(rc,garder))||__dzGraineNeuve();
  var nodes=[],edges=[];
  if(rc.image){nodes.push({id:"im1",type:"Image",x:60,y:120,props:{filename:rc.image}});
    edges.push({id:"e1",from:"im1",fromPort:"out",to:"sd1",toPort:"image"});}
  if(rc.image_end){nodes.push({id:"im2",type:"Image",x:60,y:320,props:{filename:rc.image_end}});
    edges.push({id:"e2",from:"im2",fromPort:"out",to:"sd1",toPort:"end"});}
  nodes.push({id:"pr1",type:"Prompt",x:60,y:520,props:{value:rc.prompt_envoye||rc.prompt||"",negative:rc.negative||""}});
  edges.push({id:"e3",from:"pr1",fromPort:"out",to:"sd1",toPort:"prompt"});
  nodes.push({id:"sd1",type:"Seedance",x:400,y:280,props:{model:rc.model||"seedance-2.5",style:rc.style||"cinematic",
    durationS:rc.duration_s||10,aspect:rc.aspect_ratio||"9:16",seed:g,extendMode:"loop"}});
  nodes.push({id:"rn1",type:"Render",x:740,y:280,props:{}});
  edges.push({id:"e4",from:"sd1",fromPort:"out",to:"rn1",toPort:"in"});
  return{name:(nom||"recette")+".graph",nodes:nodes,edges:edges};}
function __dzRecetteStudio(id,garder){
  __dzRecetteLire(id).then(function(rc){
    if(!rc){__dzToast(dzT("recette.toast.introuvable"));return;}
    if(!__dzRecetteRefaisable(rc)){__dzToast(dzT("recette.toast.rien_a_refaire"));return;}
    window.__dzRenderGraph=__dzRecetteGraphe(rc,garder,"recette_"+String(id).slice(0,8));__dzSendNav("studio");
    __dzToast(dzT("recette.toast.studio_ok",{id:String(id).slice(0,8)}));});}
function DzRecetteRendu(p){
  var US=x.useState,UE=x.useEffect,m=p.m;
  var s1=US(null),rc=s1[0],setRc=s1[1];
  var s2=US(!1),garder=s2[0],setGarder=s2[1];
  var s3=US(!1),neg=s3[0],setNeg=s3[1];
  var jid=m&&m.kind==="render"?m.jobId:null;
  UE(function(){var on=!0;setRc(null);setNeg(!1);
    if(jid)__dzRecetteLire(jid).then(function(r2){if(on)setRc(r2||!1);});
    return function(){on=!1;};},[jid]);
  if(!jid||!rc)return null;
  var mut={fontSize:11,color:"var(--muted,#8a96a3)"};
  var bloc={fontSize:12,lineHeight:1.45,color:"var(--ink,#cfd6dd)",background:"var(--bg-input,#0c0f12)",border:"1px solid var(--stroke,#20262d)",padding:"8px 10px",marginTop:6,whiteSpace:"pre-wrap",wordBreak:"break-word",maxHeight:140,overflow:"auto"};
  var lignes=[];
  function L(k,v){if(v!=null&&v!=="")lignes.push(r.jsxs("div",{style:{display:"flex",gap:8,fontSize:12,marginTop:3},children:[r.jsx("span",{style:Object.assign({minWidth:120},mut),children:dzT(k)}),r.jsx("span",{style:{color:"var(--ink,#cfd6dd)",wordBreak:"break-all"},children:String(v)})]},k));}
  L("recette.champ.source",dzT("recette.source."+rc.source));
  L("recette.champ.modele",rc.model);
  L("recette.champ.duree",rc.duration_s?rc.duration_s+" s":null);
  L("recette.champ.format",rc.aspect_ratio);
  L("recette.champ.graine",rc.seed);
  L("recette.champ.image",rc.image);
  L("recette.champ.image_fin",rc.image_end);
  L("recette.champ.gabarit",rc.template_id);
  var imp=rc.import&&typeof rc.import==="object"?rc.import:null;
  if(imp){L("recette.champ.import_source",imp.source);L("recette.champ.composition",imp.composition);
    if(imp.variables&&typeof imp.variables==="object")L("recette.champ.variables",Object.keys(imp.variables).map(function(k){return k+" = "+imp.variables[k];}).join(", "));
    if(imp.prompt)L("recette.champ.prompt_import",imp.prompt);}
  var clips=imp&&Array.isArray(imp.clips)?imp.clips:[];
  var ok=__dzRecetteRefaisable(rc);
  var btn={background:"transparent",border:"1px solid var(--stroke,#20262d)",color:"var(--ink,#cfd6dd)",padding:"5px 10px",fontSize:12,cursor:"pointer"};
  return r.jsxs("div",{"data-dzrecette":rc.source,style:{marginTop:12,paddingTop:10,borderTop:"1px solid var(--stroke,#20262d)"},children:[
    r.jsx("div",{style:{fontSize:11,letterSpacing:".08em",textTransform:"uppercase",color:"var(--muted,#8a96a3)"},children:dzT("recette.panneau.titre")}),
    rc.prompt?r.jsx("div",{"data-dzrecette-prompt":"",style:bloc,children:rc.prompt}):r.jsx("div",{style:Object.assign({marginTop:6},mut),children:dzT(imp?"recette.panneau.import_note":"recette.panneau.aucune")}),
    rc.negative?r.jsx("button",{type:"button",style:{background:"none",border:0,padding:0,marginTop:6,cursor:"pointer",fontSize:11,color:"var(--muted,#8a96a3)",textDecoration:"underline"},onClick:function(){setNeg(!neg);},children:dzT(neg?"recette.panneau.negatif_masquer":"recette.panneau.negatif_voir")}):null,
    rc.negative&&neg?r.jsx("div",{style:bloc,children:rc.negative}):null,
    r.jsx("div",{style:{marginTop:6},children:lignes}),
    clips.length?r.jsxs("div",{style:{marginTop:8},children:[r.jsx("div",{style:mut,children:dzT("recette.panneau.clips",{n:clips.length})}),
      clips.map(function(c,i){return r.jsx("div",{style:Object.assign({},bloc,{maxHeight:60,marginTop:4}),children:(c&&c.job_id?String(c.job_id).slice(0,8)+" · ":"")+String(c&&c.prompt||"")},i);})]}):null,
    ok?r.jsxs("div",{style:{display:"flex",flexWrap:"wrap",alignItems:"center",gap:10,marginTop:10},children:[
      r.jsxs("label",{title:dzT("recette.panneau.graine_aide"),style:{display:"flex",alignItems:"center",gap:6,fontSize:12,color:"var(--ink,#cfd6dd)",cursor:"pointer"},children:[
        r.jsx("input",{type:"checkbox","data-dzrecette-graine":"",checked:garder,onChange:function(e){setGarder(!!e.target.checked);}}),dzT("recette.panneau.graine_origine")]}),
      r.jsx("button",{type:"button","data-dzrecette-quick":"",style:btn,title:dzT("recette.panneau.quick_aide"),onClick:function(){p.fermer&&p.fermer();__dzRecetteQuick(jid,garder);},children:dzT("recette.panneau.ouvrir_quick")}),
      r.jsx("button",{type:"button","data-dzrecette-studio":"",style:btn,title:dzT("recette.panneau.studio_aide"),onClick:function(){p.fermer&&p.fermer();__dzRecetteStudio(jid,garder);},children:dzT("recette.panneau.ouvrir_studio")}),
      r.jsx("span",{style:mut,children:dzT("recette.panneau.cout_reestime")})]}):null]});}
function __dzRecetteExportUrl(m){
  var lg=(window.dzLang&&window.dzLang())||"fr";
  if(m&&m.kind==="render"&&m.jobId)return "/api/recettes/export?type=job&id="+encodeURIComponent(m.jobId)+"&lang="+lg;
  if(m&&m.name)return "/api/recettes/export?type=asset&id="+encodeURIComponent(m.name)+"&lang="+lg;
  return null;}
function __dzRecetteTelecharger(u){var a=document.createElement("a");a.href=u;a.download="";document.body.appendChild(a);a.click();a.remove();__dzToast(dzT("recette.export.toast"));}
function DzRecetteExport(p){
  var u=__dzRecetteExportUrl(p.m);if(!u)return null;
  return r.jsxs("div",{"data-dzrecette-export":"",style:{display:"flex",flexWrap:"wrap",alignItems:"center",gap:10,marginTop:10},children:[
    r.jsx("button",{type:"button","data-dzrecette-exporter":"",title:dzT("recette.export.aide"),style:{background:"transparent",border:"1px solid var(--accent,#f0b429)",color:"var(--accent,#f0b429)",padding:"5px 10px",fontSize:12,cursor:"pointer"},onClick:function(){__dzRecetteTelecharger(u);},children:dzT("recette.export.bouton")}),
    r.jsx("span",{style:{fontSize:11,color:"var(--muted,#8a96a3)"},children:dzT("recette.export.note")})]});}
