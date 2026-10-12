/* ── Rack VFX — couche window.DzVfx (gauntlet VFX vs CapCut) ─────────────────
   Injecté dans frontend/dist/assets/index-*.js juste APRÈS le bloc sfxstudio,
   MÊME scope module : les alias du bundle (r.jsx / r.jsxs, x.useState…) sont
   accessibles directement. Volontairement SANS dépendance aux helpers sonvfx
   (svm*) : le rack est aussi monté dans le nœud Effects du Studio, hors
   `.dzsvm`. Styles : /shared/vfxrack.css (préfixe .vfx-, jeu de tokens à
   repli — .dzsvm ET application principale).

   Modèle d'interaction : celui du rack SFX maison (frontend/patches/sfxstudio.js)
   — onglets + compteurs réels, recherche « / », favoris ★ persistés, modules
   repliables avec résumé mono, un seul point d'écriture d'état.

   Exporte (contrat) :
     window.DzVfx = {ready, Panel, Stack, Bounds, Thumb, Alert,
                     catalog, previewUrl, defaultsFor, summary, EASES,
                     svc, retry}

   - Panel({open,onClose,clip,stack,onAdd,inline,onPick,title}) — panneau
     d'effets : catégories, recherche, favoris, VIGNETTE D'APERÇU par effet
     rendue sur le clip réellement sélectionné, pose par clic ET par glisser
     (mime « dz-vfx »). `inline:!0` = version encastrée (nœud Effects du Studio),
     `onPick(type)` au lieu de `onAdd(effet)`.
   - Stack({effects,onChange,clip,dur,title}) — pile d'effets du clip :
     réordonner, contourner (bypass, clé `off`, retirée du payload de rendu),
     supprimer, intensité + paramètres, bornes t0/t1 et rampe, bascule
     « avant / après » de toute la pile.
   - Bounds({eff,onChange,dur}) — bornes + rampe seules (nœud Effects Studio).

   ── Contrat backend attendu (écrit en parallèle) ──────────────────────────
   GET /api/effects/catalog
       → {"effects": {<type>: {label, params:[...], presets:[...]?,
                                category?, hint?}}}
       Repli 1 : GET /api/montage/effects (même forme, déjà en place).
       Repli 2 : catalogue local figé ci-dessous (VFX_STATIC).
   GET /api/effects/preview?type=<type>&w=<px>&t=<sec>&<params>&<source>
       → image/* (JPEG/PNG). `<params>` = intensity, preset, ratio, speed,
       c0, c1, angle, opacity, blend, file. `<source>` = les clés du `src` du
       clip aplaties (job_id / image / upload / audio…) PLUS `src=<json>`.
       Repli 1 : /effect-thumbs/<type>.jpg (et <type>_<preset>.jpg), le jeu
       statique déjà servi par main.py — image réelle de l'effet, mais sur un
       plan générique : la vignette porte alors la pastille « gén. ».
       Repli 2 : vignette grisée « aperçu — » (jamais d'image cassée, jamais
       de page en erreur).
   Le repli SPA de ce backend renvoie index.html en 200 : on ne se fie donc
   JAMAIS à res.ok seul, toujours au Content-Type.

   ── Backend absent : on le DIT, et on se répare ───────────────────────────
   Aucun repli n'est silencieux. Si les deux routes de catalogue se taisent,
   le rack N'A PAS L'AIR NORMAL : bandeau `vfx-alert` en tête du panneau ET
   de la pile, qui nomme la route muette, dit ce qui est amputé (liste locale,
   pas de vignette sur votre plan, pas de préréglages moteur) et affiche le
   compte à rebours de la reprise. Une sonde partagée (VFX_SVC) redemande
   /api/effects/catalog à intervalle croissant tant que le rack est monté ;
   au premier succès, catalogue et vignettes reviennent SEULS — sans rouvrir
   le panneau, sans recharger la page. Corollaire : un catalogue de secours
   n'est jamais mémorisé comme définitif. */

/* ── outils ───────────────────────────────────────────────────────────────── */
function vfxClamp(v,a,b){v=Number(v);if(!isFinite(v))v=a;return v<a?a:v>b?b:v}
function vfxN(v,d){var n=Number(v);return isFinite(n)?n:d}
function vfxRound(v,dec){var m=Math.pow(10,dec||0);return Math.round(v*m)/m}
/* mm:ss.d — les bornes sont des secondes locales au clip */
function vfxSec(s){
  s=Math.max(0,vfxN(s,0));
  var m=Math.floor(s/60),r=s-m*60;
  return m+":"+(r<10?"0":"")+vfxRound(r,1).toFixed(1)}
/* JSON strict : le repli SPA répond 200 + text/html, res.ok ne suffit pas */
function vfxJson(url){
  return fetch(url).then(function(res){
    var ct=(res.headers.get("content-type")||"").toLowerCase();
    if(!res.ok||ct.indexOf("json")<0)throw new Error(dzT("vfx.erreur.non_json"));
    return res.json()})}

/* T103 (D2b) : POST JSON, même garde que vfxJson (le repli SPA répond 200 +
   text/html) ; le `detail` du backend remonte tel quel dans l'erreur */
function vfxPost(url,body){
  return fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body||{})})
    .then(function(res){
      var ct=(res.headers.get("content-type")||"").toLowerCase();
      if(ct.indexOf("json")<0)throw new Error(dzT("vfx.erreur.non_json"));
      return res.json().then(function(d){if(!res.ok)throw new Error((d&&d.detail)||("HTTP "+res.status));return d})})}
/* T103 (D2b) : le détourage d'un plan — un seul à la fois, le modèle retenu
   d'un plan à l'autre ; les libellés sont ceux de matte_service.MATTE_MODELS */
var VFX_MATTE={busy:!1,model:"general",arm:null,models:null};
/* le registre vient du BACKEND (GET /api/matte-models) — jamais recopié ici */
function vfxMatteModels(){
  if(VFX_MATTE.models)return Promise.resolve(VFX_MATTE.models);
  return vfxJson("/api/matte-models").then(function(d){
    VFX_MATTE.models=(d&&d.models)||[];return VFX_MATTE.models})
    .catch(function(){return []})}

/* ── favoris — localStorage dz_fav_vfx (même patron que dz_fav_avatars) ───── */
function vfxFavsLoad(){
  try{
    var a=JSON.parse(localStorage.getItem("dz_fav_vfx")||"[]"),m={};
    if(Array.isArray(a))a.forEach(function(n){if(typeof n==="string")m[n]=1});
    return m}
  catch(_e){return {}}}
function vfxFavsSave(m){
  try{localStorage.setItem("dz_fav_vfx",JSON.stringify(Object.keys(m)))}catch(_e){}}

/* ── catalogue local figé — miroir de effects_engine.catalog() ─────────────
   Sert de repli quand aucune route ne répond : le panneau reste utilisable
   hors ligne, et les 21 effets du moteur restent posables. */
var VFX_STATIC={
  grade:{label:"LUT / Grade",params:["preset","file"],
    presets:["teal_orange","cyberpunk","deepsea","noir","warm","cold","vintage",
             "cross","matrix","faded"]},
  colorize:{label:dzT("vfx.effet.colorize"),params:["preset","intensity"],
    presets:["sepia","bw","duotone","matrix","redalert","gold"]},
  vhs:{label:"VHS",params:["intensity","speed"]},
  gradient:{label:dzT("vfx.effet.gradient"),params:["c0","c1","angle","opacity","blend"]},
  grain:{label:dzT("vfx.effet.grain"),params:["intensity"]},
  vignette:{label:"Vignette",params:["intensity"]},
  chroma:{label:dzT("vfx.effet.chroma"),params:["intensity"]},
  glitch:{label:"Glitch",params:["intensity"]},
  bloom:{label:"Bloom / Glow",params:["intensity"]},
  halation:{label:"Halation",params:["intensity"]},
  scanlines:{label:"Scanlines / CRT",params:["intensity"]},
  letterbox:{label:dzT("vfx.effet.letterbox"),params:["ratio"]},
  oldfilm:{label:"Old film",params:["intensity"]},
  sharpen:{label:dzT("vfx.effet.sharpen"),params:["intensity"]},
  blur:{label:dzT("vfx.effet.blur"),params:["intensity"]},
  dreamy:{label:"Soft / Dreamy",params:["intensity"]},
  pixelate:{label:"Pixelate",params:["intensity"]},
  shake:{label:"Camera shake",params:["intensity","speed"]},
  mirror:{label:dzT("vfx.effet.mirror"),params:[]},
  invert:{label:dzT("vfx.effet.invert"),params:[]}};

/* catégorie + phrase d'aide par effet — la catégorie du backend gagne si
   elle existe (clé `category`), sinon celle-ci ; inconnu → « autres ». */
var VFX_META={
  grade:{cat:"couleur",hint:dzT("vfx.aide.grade")},
  colorize:{cat:"couleur",hint:dzT("vfx.aide.colorize")},
  gradient:{cat:"couleur",hint:dzT("vfx.aide.gradient")},
  vhs:{cat:"retro",hint:dzT("vfx.aide.vhs")},
  oldfilm:{cat:"retro",hint:dzT("vfx.aide.oldfilm")},
  scanlines:{cat:"retro",hint:dzT("vfx.aide.scanlines")},
  grain:{cat:"retro",hint:dzT("vfx.aide.grain")},
  pixelate:{cat:"retro",hint:dzT("vfx.aide.pixelate")},
  bloom:{cat:"lumiere",hint:dzT("vfx.aide.bloom")},
  halation:{cat:"lumiere",hint:dzT("vfx.aide.halation")},
  vignette:{cat:"lumiere",hint:dzT("vfx.aide.vignette")},
  dreamy:{cat:"lumiere",hint:dzT("vfx.aide.dreamy")},
  chroma:{cat:"optique",hint:dzT("vfx.aide.chroma")},
  blur:{cat:"optique",hint:dzT("vfx.aide.blur")},
  sharpen:{cat:"optique",hint:dzT("vfx.aide.sharpen")},
  glitch:{cat:"optique",hint:dzT("vfx.aide.glitch")},
  shake:{cat:"mouvement",hint:dzT("vfx.aide.shake")},
  mirror:{cat:"mouvement",hint:dzT("vfx.aide.mirror")},
  invert:{cat:"mouvement",hint:dzT("vfx.aide.invert")},
  letterbox:{cat:"cadre",hint:dzT("vfx.aide.letterbox")}};

var VFX_BLENDS=["screen","overlay","multiply","softlight","addition","normal"];
/* courbes de rampe — noms EXACTS acceptés par animation_service.ease() */
var VFX_EASES=[["smooth",dzT("vfx.courbe.douce")],["linear",dzT("vfx.courbe.lineaire")],["easeIn",dzT("vfx.courbe.acceleree")],
  ["easeOut",dzT("vfx.courbe.freinee")],["easeInOut",dzT("vfx.courbe.douce_2_sens")],["easeInOutSine",dzT("vfx.courbe.sinus")],
  ["anticipate",dzT("vfx.courbe.anticipation")],["overshoot",dzT("vfx.courbe.depassement")],
  ["easeOutBack",dzT("vfx.courbe.retour")],["easeOutBounce",dzT("vfx.courbe.rebond")],
  /* t128 : la courbe dessinée à la main — la valeur stockée est « cubic-bezier(a,b,c,d) », que
     animation_service.ease() lit déjà ; « bezier » n'est que l'entrée du menu, jamais écrite */
  ["bezier",dzT("vfx.courbe.main")]];

/* ── t128 : éditeur de courbe de Bézier (deux poignées, aperçu SVG) ─────────────────────────────────
   Les poignées des presets Bézier du backend, à l'IDENTIQUE (animation_service._BEZIER, banc
   test_vfxrack_bezier) : choisir « courbe à la main » part de la forme du preset courant. */
var VFX_BEZ_PRESETS={smooth:[0.4,0,0.2,1],easeInOutSine:[0.45,0.05,0.55,0.95],
  anticipate:[0.36,0,0.66,-0.56],overshoot:[0.34,1.56,0.64,1],linear:[0,0,1,1]};
/* géométrie du dessin : un carré de c px pour [0,1]², une marge de m px autour — y visible de
   -m/c à 1+m/c (les dépassements « anticipation » / « rebond » restent sous le doigt) */
var VFX_BEZ_GEO={c:100,m:30};
function vfxBezNb(v){return Number((+v).toFixed(2))}
function vfxBezLire(v){
  var m=/^cubic-bezier\(([^,]+),([^,]+),([^,]+),([^,)]+)\)$/.exec(String(v==null?"":v).trim());
  if(!m)return null;
  var p=[m[1],m[2],m[3],m[4]].map(function(z){return z.trim()===""?NaN:Number(z)});
  if(p.some(function(z){return !isFinite(z)})||p[0]<0||p[0]>1||p[2]<0||p[2]>1)return null;
  return p}
function vfxBezEcrire(p){
  var q=[vfxClamp(p[0],0,1),vfxClamp(p[1],-1,2),vfxClamp(p[2],0,1),vfxClamp(p[3],-1,2)].map(vfxBezNb);
  return "cubic-bezier("+q.join(",")+")"}
function vfxBezDepart(nom){
  var p=vfxBezLire(nom)||VFX_BEZ_PRESETS[nom]||[0.42,0,0.58,1];
  return p.slice()}
/* point du SVG (px, dans le repère du dessin) -> point de la courbe, borné à la zone visible */
function vfxBezPoint(px,py){
  var G=VFX_BEZ_GEO;
  return [vfxBezNb(vfxClamp((px-G.m)/G.c,0,1)),vfxBezNb(vfxClamp(1-(py-G.m)/G.c,-G.m/G.c,1+G.m/G.c))]}
function vfxBezChemin(p){
  var G=VFX_BEZ_GEO,X=function(v){return vfxBezNb(G.m+v*G.c)},Y=function(v){return vfxBezNb(G.m+(1-v)*G.c)};
  return "M"+X(0)+" "+Y(0)+" C"+X(p[0])+" "+Y(p[1])+" "+X(p[2])+" "+Y(p[3])+" "+X(1)+" "+Y(1)}

/* l'éditeur : la courbe, ses deux poignées à glisser (capture du pointeur), quatre champs pour la
   précision. `value` = « cubic-bezier(…) », `onChange(nouvelle valeur)`. */
const VfxBezier=(props)=>{
  var p=vfxBezLire(props.value)||[0.42,0,0.58,1];
  var G=VFX_BEZ_GEO,T=G.c+2*G.m;
  /* la poignée tenue vit dans une RÉFÉRENCE : rien à redessiner quand on la saisit (chaque pas du glisser
     redessine déjà par onChange) — et pas d'état de plus dans le bundle, dont le compte est épinglé */
  var svgRef=x.useRef(null),prise=x.useRef(-1);
  function pose(i,pt){var q=p.slice();q[2*i]=pt[0];q[2*i+1]=pt[1];props.onChange(vfxBezEcrire(q))}
  function local(e){
    var b=svgRef.current.getBoundingClientRect();
    return vfxBezPoint((e.clientX-b.left)*T/b.width,(e.clientY-b.top)*T/b.height)}
  function poignee(i){
    var cx=vfxBezNb(G.m+p[2*i]*G.c),cy=vfxBezNb(G.m+(1-p[2*i+1])*G.c);
    return r.jsx("circle",{className:"vfx-bezh",cx:cx,cy:cy,r:6,
      "aria-label":dzT("vfx.bezier.poignee",{n:i+1}),
      onPointerDown:function(e){e.preventDefault();e.stopPropagation();
        try{e.currentTarget.setPointerCapture(e.pointerId)}catch(_e){}prise.current=i},
      onPointerMove:function(e){if(prise.current===i)pose(i,local(e))},
      onPointerUp:function(e){try{e.currentTarget.releasePointerCapture(e.pointerId)}catch(_e){}prise.current=-1},
      onPointerCancel:function(){prise.current=-1}})}
  function champ(k,lab){
    var bx=k%2===0;
    return r.jsx("input",{className:"vfx-num vfx-bezn",type:"number",step:.05,min:bx?0:-1,max:bx?1:2,
      value:p[k],"aria-label":lab,title:lab,
      onChange:function(e){var q=p.slice();q[k]=vfxN(e.target.value,p[k]);props.onChange(vfxBezEcrire(q))}})}
  var X=function(v){return vfxBezNb(G.m+v*G.c)},Y=function(v){return vfxBezNb(G.m+(1-v)*G.c)};
  return r.jsxs("div",{className:"vfx-bez",children:[
    r.jsxs("svg",{ref:svgRef,className:"vfx-bezsvg",viewBox:"0 0 "+T+" "+T,width:T,height:T,
      role:"img","aria-label":props.label||dzT("vfx.bezier.courbe"),children:[
      r.jsx("rect",{className:"vfx-bezcadre",x:G.m,y:G.m,width:G.c,height:G.c}),
      r.jsx("line",{className:"vfx-bezdiag",x1:X(0),y1:Y(0),x2:X(1),y2:Y(1)}),
      r.jsx("line",{className:"vfx-bezbras",x1:X(0),y1:Y(0),x2:X(p[0]),y2:Y(p[1])}),
      r.jsx("line",{className:"vfx-bezbras",x1:X(1),y1:Y(1),x2:X(p[2]),y2:Y(p[3])}),
      r.jsx("path",{className:"vfx-bezcourbe",d:vfxBezChemin(p)}),
      poignee(0),poignee(1)]}),
    r.jsxs("div",{className:"vfx-bezchamps",children:[
      champ(0,dzT("vfx.bezier.p1_temps")),champ(1,dzT("vfx.bezier.p1_intensite")),
      champ(2,dzT("vfx.bezier.p2_temps")),champ(3,dzT("vfx.bezier.p2_intensite"))]}),
    r.jsx("code",{className:"vfx-bezval",children:vfxBezEcrire(p)})]})};

/* catégories de repli — la liste FAIT AUTORITÉ côté backend dès que
   /api/effects/catalog répond (clé `categories`), celle-ci ne sert qu'au
   catalogue local et à /api/montage/effects. */
var VFX_CATS_FB=[["couleur",dzT("vfx.cat.couleur")],["retro",dzT("vfx.cat.retro")],["lumiere",dzT("vfx.cat.lumiere")],
  ["optique",dzT("vfx.cat.optique")],["mouvement",dzT("vfx.cat.mouvement")],["cadre",dzT("vfx.cat.cadre")]];

/* bornes de repli par paramètre — miroir de _PARAM_DEFAULTS (effects_engine) ;
   le backend renvoie `bounds` par effet et gagne toujours. */
var VFX_PBOUNDS={
  intensity:{type:"range",min:0,max:100,step:1,d:60,label:dzT("vfx.param.intensite"),unit:"%"},
  speed:{type:"range",min:0,max:100,step:1,d:50,label:dzT("vfx.param.vitesse"),unit:"%"},
  angle:{type:"range",min:0,max:360,step:1,d:45,label:"Angle",unit:"°"},
  opacity:{type:"range",min:0,max:100,step:1,d:40,label:dzT("vfx.param.opacite"),unit:"%"},
  cx:{type:"range",min:0,max:100,step:1,d:50,label:dzT("vfx.param.centre_x"),unit:"%"},
  cy:{type:"range",min:0,max:100,step:1,d:40,label:dzT("vfx.param.centre_y"),unit:"%"},
  c0:{type:"color",d:"#00e5ff",label:dzT("vfx.param.couleur_1")},
  c1:{type:"color",d:"#9945ff",label:dzT("vfx.param.couleur_2")},
  blend:{type:"choice",choices:VFX_BLENDS,d:"screen",label:dzT("vfx.param.fusion")},
  ratio:{type:"choice",choices:["2.39","2.35","1.85","1.33"],d:"2.35",
    label:"Format"},
  preset:{type:"choice",choices:[],d:"",label:dzT("vfx.commun.prereglage")},
  file:{type:"lut",d:"",label:"LUT .cube"}};
/* bornes effectives d'un paramètre : celles du backend, sinon le repli */
function vfxBounds(ce,p){
  var b=ce&&ce.bounds&&ce.bounds[p];
  var fb=VFX_PBOUNDS[p]||{type:"range",min:0,max:100,step:1,d:50,label:p};
  if(!b)return fb;
  return {type:b.type||fb.type,
    min:b.min!=null?b.min:fb.min,max:b.max!=null?b.max:fb.max,
    step:b.step!=null?b.step:fb.step,
    d:b["default"]!=null?b["default"]:fb.d,
    label:b.label||fb.label,unit:b.unit!=null?b.unit:fb.unit,
    choices:b.choices||fb.choices}}

/* ── catalogue (une seule requête par session, repli en cascade) ──────────── */
function vfxNormCat(raw,src){
  var eff=(raw&&(raw.effects||raw.catalog))||raw||{};
  /* la liste de catégories du backend fait autorité (id + libellé + ordre) */
  var cats=[],lbl={};
  if(raw&&Array.isArray(raw.categories))
    raw.categories.forEach(function(c){
      if(!c||!c.id)return;
      cats.push([String(c.id),String(c.label||c.id)]);
      lbl[String(c.id)]=String(c.label||c.id)});
  else VFX_CATS_FB.forEach(function(c){cats.push(c);lbl[c[0]]=c[1]});
  var by={},list=[],hasOther=!1;
  Object.keys(eff).forEach(function(t){
    var d=eff[t]||{},m=VFX_META[t]||{};
    var cat=String(d.cat||d.category||m.cat||"autres");
    if(!lbl[cat]){cat="autres";hasOther=!0}
    var e={type:t,label:d.label||t,
      params:Array.isArray(d.params)?d.params:[],
      presets:Array.isArray(d.presets)?d.presets:null,
      bounds:d.bounds&&typeof d.bounds==="object"?d.bounds:null,
      cat:cat,hint:d.hint||m.hint||""};
    by[t]=e;list.push(e)});
  if(hasOther){cats.push(["autres",dzT("vfx.commun.autres")]);lbl.autres=dzT("vfx.commun.autres")}
  /* « tous » et « ★ » ouvrent toujours la rangée d'onglets */
  return {src:src,by:by,list:list,
    cats:[["tous",dzT("vfx.commun.tous")],["fav",__dzGl("dz-action-favori")]].concat(cats)}}
/* ── santé du service d'effets — source unique, auto-réparation ───────────
   Le rack tient à deux routes : /api/effects/catalog (la liste, les bornes,
   les préréglages) et /api/effects/preview (les vignettes rendues sur VOTRE
   plan). Quand le backend tombe, le rack se rabattait en SILENCE sur le
   catalogue figé local et des vignettes grisées : à l'écran, ça ressemblait
   au vieux sélecteur, donc à une régression du logiciel. Deux règles ici :

   1. On le DIT. `st === "down"` → bandeau en tête du panneau, qui nomme la
      route muette et ce qui est amputé.
   2. On se répare. Une seule sonde partagée (jamais deux en vol) redemande
      /api/effects/catalog avec un intervalle croissant tant que le rack est
      à l'écran ; au premier succès le vrai catalogue reprend la main, `tick`
      est incrémenté et TOUTES les vignettes redemandent leur image — sans
      rouvrir le panneau ni recharger la page. La sonde s'arrête dès que plus
      rien n'est monté (0 requête de fond quand le rack est fermé).

   `st` : "ok" le service répond · "down" injoignable.
   Un échec de vignette isolé ne bascule JAMAIS le rack : il déclenche UNE
   sonde de diagnostic, et seul son échec (backend muet) fait tomber en
   "down". Service debout + une vignette qui rate = cette tuile seule
   se rabat (bug déjà corrigé, on ne le réintroduit pas). */
var VFX_SVC={cat:null,st:"ok",loading:!1,p:null,probing:!1,diag:!1,tries:0,
  next:0,timer:null,mounted:0,tick:0,fails:0,subs:[]};
/* intervalles de sonde (ms) — puis le dernier, indéfiniment */
var VFX_PROBE_MS=[1500,3000,5000,8000,12000,20000];

function vfxEmit(){
  VFX_SVC.subs.slice().forEach(function(f){try{f()}catch(_e){}})}
function vfxProbeStop(){
  if(VFX_SVC.timer){clearTimeout(VFX_SVC.timer);VFX_SVC.timer=null}}
function vfxUp(){
  var was=VFX_SVC.st;
  VFX_SVC.st="ok";VFX_SVC.tries=0;VFX_SVC.next=0;VFX_SVC.diag=!1;
  vfxProbeStop();
  /* revenir de "down" invalide tout ce qui a été rendu en mode dégradé :
     `tick` remonte, les vignettes repartent d'une URL neuve */
  if(was!=="ok"){VFX_SVC.tick++;VFX_SVC.fails=0}
  vfxEmit()}
function vfxDown(){
  VFX_SVC.st="down";
  vfxEmit();
  vfxProbeSchedule()}
function vfxProbeSchedule(){
  if(VFX_SVC.st!=="ok"&&!VFX_SVC.timer&&!VFX_SVC.probing&&VFX_SVC.mounted>0){
    var d=VFX_PROBE_MS[Math.min(VFX_SVC.tries,VFX_PROBE_MS.length-1)];
    VFX_SVC.next=Date.now()+d;
    VFX_SVC.timer=setTimeout(function(){
      VFX_SVC.timer=null;vfxProbe()},d)}}
/* une sonde = une vraie demande de catalogue : si elle passe, on a le
   catalogue ET la preuve que le backend est là. */
function vfxProbe(){
  if(VFX_SVC.probing)return;
  VFX_SVC.probing=!0;VFX_SVC.tries++;
  vfxEmit();
  vfxJson("/api/effects/catalog").then(function(d){
    VFX_SVC.probing=!1;
    VFX_SVC.cat=vfxNormCat(d,"catalog");
    vfxUp()},
  function(){
    VFX_SVC.probing=!1;
    VFX_SVC.diag=!1;
    if(VFX_SVC.st==="ok"){vfxDown();return}
    vfxEmit();vfxProbeSchedule()})}
/* « réessayer maintenant » du bandeau : on repart de l'intervalle le plus court */
function vfxRetryNow(){
  vfxProbeStop();VFX_SVC.tries=0;vfxProbe()}
/* une vignette a échoué : on ne condamne rien, on DIAGNOSTIQUE une fois */
function vfxPrvFail(){
  VFX_SVC.fails++;
  /* n'émettre qu'au PREMIER échec : sinon 20 tuiles qui ratent = 20 rendus */
  if(VFX_SVC.st!=="ok"||VFX_SVC.diag||VFX_SVC.probing){
    if(VFX_SVC.fails===1)vfxEmit();
    return}
  VFX_SVC.diag=!0;
  vfxProbe()}
/* une vignette a chargé : le backend rend des images, point final */
function vfxPrvOk(){if(VFX_SVC.st!=="ok")vfxUp()}

function vfxCatLoad(){
  if(VFX_SVC.loading)return VFX_SVC.p;
  VFX_SVC.loading=!0;
  VFX_SVC.p=vfxJson("/api/effects/catalog")
    .then(function(d){return vfxNormCat(d,"catalog")})
    .catch(function(){
      return vfxJson("/api/montage/effects")
        .then(function(d){return vfxNormCat(d,"montage")})})
    .then(function(c){
      VFX_SVC.loading=!1;VFX_SVC.cat=c;vfxUp();
      return c},
    function(){
      /* aucune route ne répond : catalogue de secours, et on le DIT */
      VFX_SVC.loading=!1;
      if(!VFX_SVC.cat)VFX_SVC.cat=vfxNormCat({effects:VFX_STATIC},"local");
      vfxDown();
      return VFX_SVC.cat});
  return VFX_SVC.p}
/* contrat exporté : promesse du catalogue courant. Un catalogue de secours
   n'est JAMAIS mémorisé comme définitif — on retente à chaque appel. */
function vfxCatalog(){
  if(VFX_SVC.cat&&VFX_SVC.st==="ok"&&VFX_SVC.cat.src!=="local")
    return Promise.resolve(VFX_SVC.cat);
  return vfxCatLoad()}

/* abonnement d'un composant du rack : re-rendu à chaque changement d'état,
   comptage des montages (la sonde ne tourne que si quelque chose est à
   l'écran), et nouvelle chance à chaque ouverture du panneau. */
function vfxSvcUse(){
  var s=x.useState(0),setT=s[1];
  x.useEffect(function(){
    var f=function(){setT(function(t){return t+1})};
    VFX_SVC.subs.push(f);
    VFX_SVC.mounted++;
    if(VFX_SVC.st!=="ok")vfxProbeSchedule();
    return function(){
      var i=VFX_SVC.subs.indexOf(f);
      if(i>=0)VFX_SVC.subs.splice(i,1);
      VFX_SVC.mounted--;
      if(VFX_SVC.mounted<1)vfxProbeStop()}},[]);
  return VFX_SVC}

/* retour du réseau ou de l'onglet au premier plan : on ne fait pas attendre
   l'utilisateur jusqu'au prochain intervalle. */
function vfxWake(){
  if(VFX_SVC.st!=="ok"&&VFX_SVC.mounted>0&&!VFX_SVC.probing)vfxRetryNow()}
try{
  window.addEventListener("online",vfxWake);
  window.addEventListener("focus",vfxWake);
  document.addEventListener("visibilitychange",function(){
    if(!document.hidden)vfxWake()})}
catch(_e){}

/* ── valeurs par défaut d'un effet posé — alignées sur effects_engine ─────── */
function vfxDefaultsFor(type,ce){
  var e={type:type},
      p=(ce&&ce.params)||(VFX_STATIC[type]&&VFX_STATIC[type].params)||[];
  p.forEach(function(k){
    if(k==="file")return;                    /* LUT utilisateur : jamais posée d'office */
    var b=vfxBounds(ce,k);
    if(k==="preset"){
      var pr=(ce&&ce.presets)||(b.choices&&b.choices.length?b.choices:null)||
        (VFX_STATIC[type]&&VFX_STATIC[type].presets)||null;
      var d=type==="grade"?"teal_orange":type==="colorize"?"duotone"
        :(pr&&pr[0])||null;
      if(d&&(!pr||pr.indexOf(d)>=0))e.preset=d;
      else if(pr&&pr.length)e.preset=pr[0];
      return}
    if(b.d!=null&&b.d!=="")e[k]=b.d});
  return e}

/* résumé mono d'un effet replié — valeurs clés, dérivées des paramètres réels */
function vfxSummary(eff,ce){
  if(!eff)return "";
  var pa=(ce&&ce.params)||
    (VFX_STATIC[eff.type]&&VFX_STATIC[eff.type].params)||[];
  var b=[];
  function has(k){return pa.indexOf(k)>=0}
  if(has("preset")&&eff.preset)b.push(String(eff.preset));
  if(has("file")&&eff.file)b.push(String(eff.file));
  if(has("intensity"))b.push(Math.round(vfxN(eff.intensity,60))+" %");
  if(has("speed"))b.push("v"+Math.round(vfxN(eff.speed,50)));
  if(has("ratio"))b.push(String(eff.ratio!=null?eff.ratio:"2.35"));
  if(has("blend"))b.push(String(eff.blend||"screen"));
  if(has("opacity")&&!has("intensity"))
    b.push(Math.round(vfxN(eff.opacity,40))+" %");
  return b.length?b.join(" · "):dzT("vfx.resume.sans_reglage")}

/* clés d'état d'un effet qui ne sont PAS des paramètres de rendu d'image */
var VFX_PRV_SKIP={type:1,off:1,label:1,t0:1,t1:1,fade_in:1,fade_out:1,
  ease_in:1,ease_out:1,behind:1};
/* source du plan, au format attendu par /api/effects/preview :
   « job:<id> », « image:<nom> », sinon rien (le backend rend sa mire). */
function vfxSourceOf(clip){
  var s=clip&&clip.src;
  if(!s||typeof s!=="object")return null;
  if(s.job_id)return "job:"+s.job_id;
  if(s.image)return "image:"+s.image;
  return null}
function vfxPreviewUrl(clip,eff,w){
  if(!eff||!eff.type)return null;
  var q=["type="+encodeURIComponent(eff.type),
         "w="+Math.round(vfxClamp(w||168,96,640))];
  Object.keys(eff).forEach(function(k){
    if(VFX_PRV_SKIP[k])return;
    var v=eff[k];
    if(v!=null&&v!=="")q.push(encodeURIComponent(k)+"="+encodeURIComponent(String(v)))});
  var so=vfxSourceOf(clip);
  if(so)q.push("source="+encodeURIComponent(so));
  /* T103 (D2b) : un effet « derrière » se prévisualise SOUS le sujet détouré,
     comme au rendu ; « devant » le couvre, la vignette d'avant suffit */
  if(clip&&clip.matte&&eff.behind!==!1)q.push("matte="+encodeURIComponent(clip.matte));
  /* 40 % du plan : ni le noir du début, ni la fin — une image représentative
     (le backend borne à 30 s, on n'envoie donc rien au-delà) */
  var len=clip&&clip.end>clip.start?clip.end-clip.start:0;
  q.push("t="+vfxRound(vfxClamp(vfxN(clip&&clip.srcIn,0)+len*0.4,0,30),2));
  return "/api/effects/preview?"+q.join("&")}

/* repli statique : jeu d'images déjà servi par main.py (/effect-thumbs).
   C'est une image RÉELLE de l'effet, mais sur un plan générique. */
function vfxStaticUrl(eff){
  if(!eff||!eff.type)return null;
  var t=String(eff.type);
  if(!/^[a-z0-9_]+$/.test(t))return null;
  if((t==="grade"||t==="colorize")&&eff.preset&&/^[a-z0-9_]+$/.test(String(eff.preset)))
    return "/effect-thumbs/"+t+"_"+eff.preset+".jpg";
  return "/effect-thumbs/"+t+".jpg"}

/* VfxThumb — vignette paresseuse (IntersectionObserver), repli grisé net.
   props : {url, h, alt, tick, debounce} — `tick` force un nouvel essai,
   `debounce` (ms) évite une requête par cran de curseur dans la pile. */
const VfxThumb=(props)=>{
  var svc=vfxSvcUse(),st=svc.st;
  var s1=x.useState(!1),seen=s1[0],setSeen=s1[1];
  var s2=x.useState(!1),err=s2[0],setErr=s2[1];
  var s3=x.useState(!1),okd=s3[0],setOkd=s3[1];
  var s4=x.useState(props.url),url=s4[0],setUrl=s4[1];
  var s5=x.useState(!1),fbErr=s5[0],setFbErr=s5[1];
  /* Ouvrir le panneau lance ~20 rendus d'un coup : une vignette peut échouer
     une fois (cache froid, ffmpeg saturé). Un échec isolé ne doit pas
     condamner la tuile — ni, via VFX_SVC, tout le rack. Un seul réessai. */
  var s6=x.useState(0),rty=s6[0],setRty=s6[1];
  var ref=x.useRef(null);
  x.useEffect(function(){
    var d=vfxN(props.debounce,0);
    if(!d){setUrl(props.url);return}
    var h=setTimeout(function(){setUrl(props.url)},d);
    return function(){clearTimeout(h)}},[props.url,props.debounce]);
  /* `svc.tick` : le service vient de revenir — tout ce qui a été rendu en
     mode dégradé (erreurs mémorisées comprises) est jeté, et la tuile
     redemande sa vraie image. C'est CE point qui empêche un échec au premier
     chargement de condamner la session. */
  x.useEffect(function(){setErr(!1);setOkd(!1);setFbErr(!1);setRty(0)},
    [url,props.tick,props.fallback,svc.tick]);
  x.useEffect(function(){
    if(seen)return;
    var el=ref.current;
    if(!el)return;
    if(typeof IntersectionObserver!=="function"){setSeen(!0);return}
    var io=new IntersectionObserver(function(es){
      for(var i=0;i<es.length;i++)if(es[i].isIntersecting){setSeen(!0);io.disconnect();return}},
      {rootMargin:"140px"});
    io.observe(el);
    return function(){io.disconnect()}},[seen]);
  /* chaîne de repli : aperçu sur le plan → vignette statique → grisé */
  var useFb=err||(st==="down"&&!okd);
  /* `_r` n'est pas un paramètre déclaré : le backend l'ignore (même clé de
     cache), le navigateur y voit une URL neuve et retente vraiment. */
  var rv=rty||svc.tick;
  var shownUrl=useFb?(props.fallback||null)
    :(url&&rv?url+(url.indexOf("?")>=0?"&":"?")+"_r="+rv:url);
  /* service à terre : /effect-thumbs sort du MÊME backend muet — inutile de
     lui envoyer 20 requêtes de plus pour afficher 20 images cassées. */
  var dead=(useFb&&(!props.fallback||st==="down"))||fbErr;
  return r.jsxs("span",{className:"vfx-thumb",ref:ref,
    style:props.h?{height:props.h}:void 0,children:[
    dead?null:(seen&&shownUrl?r.jsx("img",{className:"vfx-thumbimg",src:shownUrl,
      alt:props.alt||"",draggable:!1,decoding:"async",
      onLoad:function(){if(!useFb){setOkd(!0);vfxPrvOk()}},
      onError:function(){
        if(useFb){setFbErr(!0);vfxPrvFail();return}
        if(rty<1){setRty(rty+1);return}   /* un réessai avant de renoncer */
        setErr(!0);
        vfxPrvFail()}}):null),
    dead?r.jsx("span",{className:"vfx-thumboff",
      title:dzT("vfx.vignette.indisponible"),
      children:dzT("vfx.vignette.apercu_off")})
    :(useFb?r.jsx("span",{className:"vfx-thumbgen",
        title:dzT("vfx.vignette.generique"),
        children:dzT("vfx.vignette.gen")})
      :(okd?null:r.jsx("span",{className:"vfx-thumbskel","aria-hidden":!0})))]})};

/* ── note interne (aucune dépendance au module sonvfx) ───────────────────── */
function vfxUseNote(){
  var s=x.useState(""),note=s[0],setNote=s[1];
  var tRef=x.useRef(null);
  x.useEffect(function(){return function(){if(tRef.current)clearTimeout(tRef.current)}},[]);
  var fire=x.useCallback(function(m){
    setNote(String(m||""));
    if(tRef.current)clearTimeout(tRef.current);
    tRef.current=setTimeout(function(){setNote("")},4200)},[]);
  return [note,fire]}

/* ── bandeau de panne — À L'ENDROIT OÙ L'UTILISATEUR REGARDE ──────────────
   Quand le service d'effets ne répond pas, le rack ne se contente PAS d'un
   repli discret en pied de panneau : il nomme la cause, dit ce qui est
   amputé, et affiche le compte à rebours de la reprise automatique. Le
   bouton n'est qu'un raccourci — la réparation, elle, n'attend personne. */
const VfxAlert=(props)=>{
  var svc=vfxSvcUse();
  var s=x.useState(0),setT=s[1];
  var down=svc.st==="down";
  /* compte à rebours : un battement par seconde, uniquement en panne */
  x.useEffect(function(){
    if(!down)return;
    var h=setInterval(function(){setT(function(t){return t+1})},1000);
    return function(){clearInterval(h)}},[down]);
  if(!down)return null;
  var n=(svc.cat&&svc.cat.list&&svc.cat.list.length)||0;
  var loc=!svc.cat||svc.cat.src==="local";
  var left=Math.max(0,Math.ceil((svc.next-Date.now())/1000));
  var when=svc.probing?dzT("vfx.alerte.tentative")
    :dzT("vfx.alerte.reprise",{n:left});
  /* dire EXACTEMENT ce qui manque : catalogue jamais reçu, ou catalogue
     d'avant la panne encore en mémoire mais vignettes mortes. */
  var what=loc
    ?dzT("vfx.alerte.secours",{n:n})
    :dzT("vfx.alerte.avant_panne",{n:n});
  return r.jsxs("div",{className:"vfx-alert",role:"alert","aria-live":"assertive",
    children:[
    r.jsx("span",{className:"vfx-alerticon","aria-hidden":!0,children:"!"}),
    r.jsxs("div",{className:"vfx-alerttxt",children:[
      r.jsx("b",{className:"vfx-alerthead",
        children:dzT("vfx.alerte.titre")}),
      r.jsx("span",{className:"vfx-alertsub",children:
        dzT("vfx.alerte.detail",{quoi:what})}),
      r.jsx("span",{className:"vfx-alertwhen",children:when})]}),
    r.jsx("button",{className:"vfx-btn vfx-alertbtn",disabled:!!svc.probing,
      title:dzT("vfx.alerte.reessayer_aide"),
      onClick:vfxRetryNow,children:dzT("vfx.alerte.reessayer")})]})};

/* ═════════════════ Panneau d'effets (catégories · recherche · aperçus) ════ */
const VfxPanel=(props)=>{
  var inline=!!props.inline;
  /* le catalogue vit dans le magasin partagé, PAS dans un état local figé :
     quand la sonde ramène le vrai catalogue, ce panneau se remplit sans
     être rouvert. */
  var svc=vfxSvcUse(),cat=svc.cat;
  var s2=x.useState("tous"),tab=s2[0],setTab=s2[1];
  var s3=x.useState(""),query=s3[0],setQuery=s3[1];
  var s4=x.useState(vfxFavsLoad),favs=s4[0],setFavs=s4[1];
  var s5=x.useState(0),tick=s5[0],setTick=s5[1];
  var nt=vfxUseNote(),note=nt[0],fireNote=nt[1];
  var rootRef=x.useRef(null),searchRef=x.useRef(null),ghostRef=x.useRef(null);
  var open=inline||!!props.open;

  x.useEffect(function(){vfxCatalog()},[]);
  x.useEffect(function(){vfxFavsSave(favs)},[favs]);
  x.useEffect(function(){
    if(open&&!inline&&rootRef.current)
      try{rootRef.current.focus({preventScroll:!0})}catch(_e){}},[open,inline]);
  x.useEffect(function(){return function(){
    var g=ghostRef.current;
    if(g&&g.parentNode)g.parentNode.removeChild(g)}},[]);

  var clip=props.clip||null;
  var stack=props.stack||[];
  var used={};
  stack.forEach(function(f){if(f&&f.type)used[f.type]=(used[f.type]||0)+1});

  var qn=query.trim().toLowerCase();
  var all=(cat&&cat.list)||[];
  var searched=x.useMemo(function(){
    if(!qn)return all;
    return all.filter(function(e){
      return e.label.toLowerCase().indexOf(qn)>=0||
        e.type.toLowerCase().indexOf(qn)>=0||
        (e.hint&&e.hint.toLowerCase().indexOf(qn)>=0)})},[all,qn]);
  var tabs=(cat&&cat.cats)||[["tous",dzT("vfx.commun.tous")],["fav",__dzGl("dz-action-favori")]];
  var counts=x.useMemo(function(){
    var c={tous:searched.length,fav:0};
    tabs.forEach(function(k){if(k[0]!=="tous"&&k[0]!=="fav")c[k[0]]=0});
    searched.forEach(function(e){
      c[e.cat]=(c[e.cat]||0)+1;
      if(favs[e.type])c.fav++});
    return c},[searched,favs,cat]);
  var shown=x.useMemo(function(){
    var rows=tab==="tous"?searched.slice()
      :tab==="fav"?searched.filter(function(e){return !!favs[e.type]})
      :searched.filter(function(e){return e.cat===tab});
    /* favoris d'abord, puis ordre du catalogue — même règle que le rack SFX */
    rows.sort(function(a,b){return (favs[b.type]?1:0)-(favs[a.type]?1:0)});
    return rows},[searched,tab,favs]);

  function favToggle(t){
    setFavs(function(m){
      var nm=Object.assign({},m);
      if(nm[t])delete nm[t];else nm[t]=1;
      return nm})}

  function place(e){
    var eff=vfxDefaultsFor(e.type,e);
    if(inline){
      if(props.onPick)props.onPick(e.type,eff);
      return}
    if(props.onAdd)props.onAdd(eff,e);
    fireNote(dzT("vfx.panneau.pose",{nom:e.label}))}

  function dragStart(ev,e){
    var eff=vfxDefaultsFor(e.type,e);
    try{
      ev.dataTransfer.setData("dz-vfx",JSON.stringify(Object.assign({label:e.label},eff)));
      ev.dataTransfer.effectAllowed="copy";
      var g=document.createElement("div");
      __dzGlD(g,"dz-edit-effet","✦ "+e.label,"✦",12);
      g.setAttribute("style","position:fixed;top:-200px;left:-200px;z-index:9999;"+
        "padding:6px 10px;border-radius:8px;background:#1c1c21;color:#f2efe9;"+
        "border:1px solid #3d3b45;font:11px 'JetBrains Mono',Consolas,monospace;"+
        "box-shadow:0 8px 20px rgba(0,0,0,.5);max-width:240px;white-space:nowrap;"+
        "overflow:hidden;text-overflow:ellipsis;pointer-events:none");
      document.body.appendChild(g);ghostRef.current=g;
      ev.dataTransfer.setDragImage(g,14,14)}catch(_e){}}
  function dragEnd(){
    var g=ghostRef.current;
    if(g&&g.parentNode)g.parentNode.removeChild(g);
    ghostRef.current=null}

  function onKey(ev){
    var t=ev.target,tag=(t&&t.tagName||"").toLowerCase();
    var inField=tag==="input"||tag==="textarea"||tag==="select";
    if(ev.key==="Escape"){
      if(inField&&t===searchRef.current&&query){setQuery("");ev.preventDefault();return}
      if(!inline&&props.onClose){props.onClose();ev.preventDefault();ev.stopPropagation()}
      return}
    if(inField)return;
    if(ev.key==="/"){
      if(searchRef.current){searchRef.current.focus();ev.preventDefault();ev.stopPropagation()}}}

  function tile(e){
    var eff=vfxDefaultsFor(e.type,e);
    var n=used[e.type]||0;
    var on=!!favs[e.type];
    return r.jsxs("div",{className:"vfx-tile",tabIndex:0,role:"button",
      "data-used":n?"":void 0,draggable:!0,
      onDragStart:function(ev){dragStart(ev,e)},onDragEnd:dragEnd,
      onClick:function(){place(e)},
      onKeyDown:function(ev){
        if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();place(e)}
        else if(ev.key==="f"||ev.key==="F"){ev.preventDefault();favToggle(e.type)}},
      title:e.hint?(e.hint+dzT("vfx.tuile.aide_suite"))
        :dzT("vfx.tuile.aide"),
      "aria-label":e.label+(e.hint?" — "+e.hint:""),
      children:[
      r.jsx(VfxThumb,{url:vfxPreviewUrl(clip,eff,168),fallback:vfxStaticUrl(eff),
        h:74,alt:e.label,tick:tick}),
      r.jsxs("div",{className:"vfx-tilefoot",children:[
        r.jsx("span",{className:"vfx-tilename",children:e.label}),
        r.jsx("button",{className:"vfx-fav","data-on":on?"":void 0,tabIndex:-1,
          "aria-pressed":on,
          title:on?dzT("vfx.tuile.retirer_fav"):dzT("vfx.tuile.ajouter_fav"),
          "aria-label":(on?dzT("vfx.tuile.retirer_fav_nom"):dzT("vfx.tuile.ajouter_fav_nom"))+e.label,
          onClick:function(ev){ev.stopPropagation();favToggle(e.type)},
          children:on?__dzGl("dz-action-favori"):__dzGl("dz-action-favori")})]}),
      n?r.jsx("span",{className:"vfx-tilebadge",
        title:dzT("vfx.tuile.deja",{n:n}),children:"×"+n}):null]},e.type)}

  function body(){
    if(!cat)
      return r.jsx("div",{className:"vfx-grid",children:[0,1,2,3,4,5].map(function(i){
        return r.jsx("div",{className:"vfx-tile vfx-tileskel","aria-hidden":!0},"s"+i)})});
    if(!shown.length)
      return r.jsxs("div",{className:"vfx-empty",children:[
        r.jsx("div",{className:"vfx-emptytxt",children:qn
          ?dzT("vfx.panneau.aucun_pour",{q:qn})
          :tab==="fav"?dzT("vfx.panneau.aucun_favori")
          :dzT("vfx.panneau.aucun_categorie")}),
        qn?r.jsx("button",{className:"vfx-btn",onClick:function(){setQuery("")},
          children:dzT("vfx.panneau.effacer_recherche")})
        :tab==="fav"?r.jsx("div",{className:"vfx-emptyhint",
          children:__dzGlT("dz-action-favori",dzT("vfx.panneau.favori_aide"),"★")}):null]});
    return r.jsx("div",{className:"vfx-grid",children:shown.map(tile)})}

  if(!open)return null;
  var srcLbl=cat?(cat.src==="catalog"?dzT("vfx.panneau.src_moteur")
    :cat.src==="montage"?dzT("vfx.panneau.src_montage"):dzT("vfx.panneau.src_local")):"…";
  return r.jsxs("div",{className:inline?"vfx-rack vfx-inline":"vfx-rack vfx-float",
    ref:rootRef,tabIndex:inline?void 0:-1,onKeyDown:onKey,
    role:"group","aria-label":dzT("vfx.panneau.aria"),children:[
    r.jsxs("div",{className:"vfx-head",children:[
      r.jsx("span",{className:"vfx-title",children:props.title||dzT("vfx.panneau.titre")}),
      r.jsx("span",{className:"vfx-count",children:String((cat&&cat.list.length)||0)}),
      clip&&clip.label?r.jsx("span",{className:"vfx-on",
        title:dzT("vfx.panneau.sur_plan_aide"),
        children:dzT("vfx.panneau.sur_plan",{nom:clip.label})}):null,
      inline?null:r.jsx("button",{className:"vfx-iconbtn vfx-close",
        title:dzT("vfx.panneau.fermer"),"aria-label":dzT("vfx.panneau.fermer_aria"),
        onClick:function(){if(props.onClose)props.onClose()},children:__dzGl("dz-action-fermer")})]}),
    r.jsx(VfxAlert,{}),
    r.jsxs("div",{className:"vfx-searchrow",children:[
      r.jsx("input",{className:"vfx-search",ref:searchRef,type:"text",value:query,
        placeholder:dzT("vfx.panneau.rechercher"),"aria-label":dzT("vfx.panneau.rechercher_aria"),
        onChange:function(e){setQuery(e.target.value)}}),
      r.jsx("kbd",{className:"vfx-kbd","aria-hidden":!0,children:"/"})]}),
    r.jsx("div",{className:"vfx-tabs",role:"tablist",children:
      tabs.filter(function(c){
        return c[0]==="tous"||c[0]==="fav"||(counts[c[0]]||0)>0}).map(function(c){
        return r.jsxs("button",{className:"vfx-tab",role:"tab",
          "aria-selected":tab===c[0],"data-on":tab===c[0]?"":void 0,
          "aria-label":c[0]==="fav"?dzT("vfx.panneau.favoris_n",{n:counts.fav||0}):void 0,
          onClick:function(){setTab(c[0])},children:[
          c[1],
          r.jsx("span",{className:"vfx-tcount",children:String(counts[c[0]]||0)})]},c[0])})}),
    body(),
    note?r.jsx("div",{className:"vfx-note",role:"status","aria-live":"polite",
      children:note}):null,
    r.jsxs("div",{className:"vfx-foot",children:[
      r.jsxs("span",{className:"vfx-hints","aria-hidden":!0,children:[
        r.jsx("kbd",{children:dzT("vfx.pied.clic")}),inline?dzT("vfx.pied.choisir"):dzT("vfx.pied.poser"),
        inline?null:r.jsx("kbd",{children:dzT("vfx.pied.glisser")}),
        inline?null:dzT("vfx.pied.sur_clip"),
        r.jsx("kbd",{children:"F"}),dzT("vfx.pied.favori"),
        r.jsx("kbd",{children:"/"}),dzT("vfx.pied.recherche")]}),
      r.jsx("span",{className:"vfx-src",title:dzT("vfx.pied.origine"),
        children:srcLbl}),
      /* service debout mais des vignettes ont raté (ffmpeg saturé, cache
         froid…) : la panne globale est traitée par le bandeau, ceci ne
         couvre que les échecs isolés. */
      (svc.st==="ok"&&svc.fails)?r.jsx("button",{className:"vfx-btn",
        title:dzT("vfx.pied.reessayer_aide"),
        onClick:function(){
          VFX_SVC.fails=0;setTick(function(t){return t+1})},
        children:dzT("vfx.pied.reessayer")}):null]})]})};

/* ═════════════════ Bornes t0/t1 + rampe (déjà gérées par le moteur) ══════ */
const VfxBounds=(props)=>{
  var eff=props.eff||{};
  var dur=vfxN(props.dur,0)||60;
  var on=eff.t0!=null&&eff.t1!=null;
  var t0=vfxClamp(vfxN(eff.t0,0),0,dur),
      t1=vfxClamp(vfxN(eff.t1,dur),0,dur);
  var span=Math.max(0,t1-t0);
  var fi=vfxClamp(vfxN(eff.fade_in,0),0,span/2||0),
      fo=vfxClamp(vfxN(eff.fade_out,0),0,span/2||0);
  function set(patch){if(props.onChange)props.onChange(patch)}
  function toggle(){
    if(on)set({t0:void 0,t1:void 0,fade_in:void 0,fade_out:void 0,
      ease_in:void 0,ease_out:void 0});
    else set({t0:0,t1:vfxRound(dur,2)})}
  function num(p){
    return r.jsx("input",Object.assign({className:"vfx-num",type:"number"},p))}
  return r.jsxs("div",{className:"vfx-bounds",children:[
    r.jsxs("button",{className:"vfx-brow vfx-bhead",role:"switch","aria-checked":on,
      onClick:toggle,
      title:on?dzT("vfx.bornes.tout_plan_aide")
        :dzT("vfx.bornes.limiter_aide"),
      children:[
      r.jsx("span",{className:"vfx-sw","data-on":on?"":void 0,"aria-hidden":!0,
        children:r.jsx("i",{className:"vfx-swk"})}),
      r.jsx("span",{className:"vfx-blabel",children:dzT("vfx.bornes.titre")}),
      r.jsx("span",{className:"vfx-bsum",children:on
        ?vfxSec(t0)+" → "+vfxSec(t1):dzT("vfx.bornes.tout_plan")})]}),
    on?r.jsxs("div",{className:"vfx-bbody",children:[
      r.jsxs("div",{className:"vfx-prow",children:[
        r.jsx("span",{className:"vfx-plabel",children:dzT("vfx.bornes.debut")}),
        r.jsx("input",{className:"vfx-range",type:"range",min:0,max:vfxRound(dur,2),
          step:.05,value:t0,"aria-label":dzT("vfx.bornes.debut_aria"),
          onChange:function(e){
            var v=vfxClamp(vfxN(e.target.value,0),0,Math.max(0,t1-.05));
            set({t0:vfxRound(v,2)})}}),
        num({min:0,max:vfxRound(dur,2),step:.05,value:vfxRound(t0,2),
          "aria-label":dzT("vfx.bornes.debut_precis"),
          onChange:function(e){
            var v=vfxClamp(vfxN(e.target.value,t0),0,Math.max(0,t1-.05));
            set({t0:vfxRound(v,2)})}}),
        r.jsx("span",{className:"vfx-punit",children:"s"})]}),
      r.jsxs("div",{className:"vfx-prow",children:[
        r.jsx("span",{className:"vfx-plabel",children:dzT("vfx.bornes.fin")}),
        r.jsx("input",{className:"vfx-range",type:"range",min:0,max:vfxRound(dur,2),
          step:.05,value:t1,"aria-label":dzT("vfx.bornes.fin_aria"),
          onChange:function(e){
            var v=vfxClamp(vfxN(e.target.value,dur),Math.min(dur,t0+.05),dur);
            set({t1:vfxRound(v,2)})}}),
        num({min:0,max:vfxRound(dur,2),step:.05,value:vfxRound(t1,2),
          "aria-label":dzT("vfx.bornes.fin_precise"),
          onChange:function(e){
            var v=vfxClamp(vfxN(e.target.value,t1),Math.min(dur,t0+.05),dur);
            set({t1:vfxRound(v,2)})}}),
        r.jsx("span",{className:"vfx-punit",children:"s"})]}),
      r.jsxs("div",{className:"vfx-prow",children:[
        r.jsx("span",{className:"vfx-plabel",children:dzT("vfx.bornes.rampe_entree")}),
        num({min:0,max:vfxRound(span/2,2),step:.05,value:vfxRound(fi,2),
          "aria-label":dzT("vfx.bornes.rampe_entree_duree"),
          onChange:function(e){
            set({fade_in:vfxRound(vfxClamp(vfxN(e.target.value,0),0,span/2),2)})}}),
        r.jsx("span",{className:"vfx-punit",children:"s"}),
        r.jsx("select",{className:"vfx-sel",value:vfxBezLire(eff.ease_in)?"bezier":(eff.ease_in||"smooth"),
          "aria-label":dzT("vfx.bornes.courbe_entree"),disabled:!(fi>0),
          onChange:function(e){set({ease_in:e.target.value==="bezier"
            ?vfxBezEcrire(vfxBezDepart(eff.ease_in||"smooth")):e.target.value})},
          children:VFX_EASES.map(function(o){
            return r.jsx("option",{value:o[0],children:o[1]},o[0])})})]}),
      fi>0&&vfxBezLire(eff.ease_in)?r.jsx(VfxBezier,{value:eff.ease_in,label:dzT("vfx.bornes.courbe_entree"),
        onChange:function(v){set({ease_in:v})}}):null,
      r.jsxs("div",{className:"vfx-prow",children:[
        r.jsx("span",{className:"vfx-plabel",children:dzT("vfx.bornes.rampe_sortie")}),
        num({min:0,max:vfxRound(span/2,2),step:.05,value:vfxRound(fo,2),
          "aria-label":dzT("vfx.bornes.rampe_sortie_duree"),
          onChange:function(e){
            set({fade_out:vfxRound(vfxClamp(vfxN(e.target.value,0),0,span/2),2)})}}),
        r.jsx("span",{className:"vfx-punit",children:"s"}),
        r.jsx("select",{className:"vfx-sel",value:vfxBezLire(eff.ease_out)?"bezier":(eff.ease_out||"smooth"),
          "aria-label":dzT("vfx.bornes.courbe_sortie"),disabled:!(fo>0),
          onChange:function(e){set({ease_out:e.target.value==="bezier"
            ?vfxBezEcrire(vfxBezDepart(eff.ease_out||"smooth")):e.target.value})},
          children:VFX_EASES.map(function(o){
            return r.jsx("option",{value:o[0],children:o[1]},o[0])})})]}),
      fo>0&&vfxBezLire(eff.ease_out)?r.jsx(VfxBezier,{value:eff.ease_out,label:dzT("vfx.bornes.courbe_sortie"),
        onChange:function(v){set({ease_out:v})}}):null,
      /* t128 : le shake ne se fond pas (l'image secouée mélangée à l'image fixe se dédoublerait) — sa
         rampe module l'AMPLITUDE de la secousse ; la secousse + zoom garde une entrée et une sortie franches */
      eff.type==="shake"?r.jsx("div",{className:"vfx-bnote",
        children:dzT("vfx.bornes.note_shake")}):null,
      eff.type==="shakezoom"?r.jsx("div",{className:"vfx-bnote",
        children:dzT("vfx.bornes.note_shakezoom")}):null,
      r.jsx("div",{className:"vfx-bnote",
        children:dzT("vfx.bornes.note_hors")})]}):null]})};

/* ═════════════════ Pile d'effets du clip ════════════════════════════════ */
const VfxStack=(props)=>{
  var list=Array.isArray(props.effects)?props.effects:[];
  var s1=x.useState({}),exp=s1[0],setExp=s1[1];
  var s2=x.useState(0),tick=s2[0],setTick=s2[1];
  var nt=vfxUseNote(),note=nt[0],fireNote=nt[1];
  /* même magasin que le panneau : la pile récupère libellés, bornes et
     préréglages du moteur dès que le backend revient. */
  var svc=vfxSvcUse(),cat=svc.cat;
  x.useEffect(function(){vfxCatalog()},[]);

  var clip=props.clip||null;
  var dur=vfxN(props.dur,0)||(clip&&clip.end>clip.start?clip.end-clip.start:0);
  function ce(t){return (cat&&cat.by[t])||{type:t,label:t,
    params:(VFX_STATIC[t]&&VFX_STATIC[t].params)||[],
    presets:(VFX_STATIC[t]&&VFX_STATIC[t].presets)||null}}

  function emit(next,heavy){if(props.onChange)props.onChange(next,!!heavy)}
  function patchAt(i,patch,heavy){
    var next=list.slice();
    var o=Object.assign({},next[i],patch);
    Object.keys(patch).forEach(function(k){if(patch[k]===void 0)delete o[k]});
    next[i]=o;
    emit(next,heavy)}
  function removeAt(i){
    var next=list.slice(),f=next[i];
    next.splice(i,1);
    emit(next,!0);
    fireNote(dzT("vfx.pile.retire",{nom:ce(f&&f.type).label}))}
  function moveAt(i,d){
    var j=i+d;
    if(j<0||j>=list.length)return;
    var next=list.slice(),tmp=next[i];
    next[i]=next[j];next[j]=tmp;
    emit(next,!0)}
  function bypassAt(i){
    var f=list[i];
    patchAt(i,{off:f&&f.off?void 0:!0},!0)}
  var anyOn=list.some(function(f){return !f.off});
  function abToggle(){
    if(!list.length)return;
    var next=list.map(function(f){
      var o=Object.assign({},f);
      if(anyOn)o.off=!0;else delete o.off;
      return o});
    emit(next,!0);
    fireNote(anyOn?dzT("vfx.pile.avant_note")
      :dzT("vfx.pile.apres_note"))}
  function clearAll(){
    if(!list.length)return;
    emit([],!0);
    fireNote(dzT("vfx.pile.videe"))}

  /* préréglages : des VIGNETTES, pas des noms — c'est là que le choix se fait
     à l'œil (chaîne de repli identique à celle du panneau). */
  function presetRow(f,i,d){
    if((d.params||[]).indexOf("preset")<0)return null;
    var pr=d.presets||vfxBounds(d,"preset").choices||null;
    if(!pr||!pr.length)return null;
    var cur=f.preset||(f.type==="grade"?"teal_orange":f.type==="colorize"?"duotone":pr[0]);
    return r.jsxs("div",{className:"vfx-pgroup",children:[
      r.jsx("span",{className:"vfx-plabel",children:dzT("vfx.commun.prereglage")}),
      r.jsx("div",{className:"vfx-pgrid",children:pr.map(function(p){
        var pe=Object.assign({},f,{preset:p});
        return r.jsxs("button",{className:"vfx-ptile","data-on":p===cur?"":void 0,
          title:dzT("vfx.pile.prereglage_nom",{nom:p}),
          onClick:function(){patchAt(i,{preset:p})},children:[
          r.jsx(VfxThumb,{url:vfxPreviewUrl(clip,pe,120),fallback:vfxStaticUrl(pe),
            h:38,alt:p,tick:tick}),
          r.jsx("span",{className:"vfx-pname",children:p})]},p)})})]})}
  /* une rangée par paramètre, pilotée par les BORNES du catalogue : les
     effets ajoutés côté moteur apparaissent sans toucher au rack. */
  function paramRow(f,i,d,k){
    if(k==="preset")return null;                 /* rendu en vignettes */
    var b=vfxBounds(d,k);
    if(b.type==="lut"){
      return r.jsxs("div",{className:"vfx-prow",children:[
        r.jsx("span",{className:"vfx-plabel",children:b.label}),
        r.jsx("input",{className:"vfx-num",type:"text",style:{width:"auto",flex:1},
          value:f[k]||"",placeholder:"mon_look.cube",
          title:dzT("vfx.pile.lut_aide"),
          "aria-label":d.label+" — "+b.label,
          onChange:function(e){patchAt(i,vfxPatch1(k,e.target.value))}})]},k)}
    if(b.type==="color"){
      return r.jsxs("div",{className:"vfx-prow",children:[
        r.jsx("span",{className:"vfx-plabel",children:b.label}),
        r.jsx("input",{className:"vfx-color",type:"color",value:f[k]||b.d||"#ffffff",
          "aria-label":d.label+" — "+b.label,
          onChange:function(e){patchAt(i,vfxPatch1(k,e.target.value))}}),
        r.jsx("span",{className:"vfx-pval",children:String(f[k]||b.d||"")})]},k)}
    if(b.type==="choice"){
      var ch=b.choices||[];
      var cur=f[k]!=null?String(f[k]):String(b.d);
      /* peu de choix = pastilles (visibles d'un coup d'œil), sinon liste */
      if(ch.length&&ch.length<=6)
        return r.jsxs("div",{className:"vfx-prow vfx-prowwrap",children:[
          r.jsx("span",{className:"vfx-plabel",children:b.label}),
          r.jsx("div",{className:"vfx-chips",children:ch.map(function(o){
            return r.jsx("button",{className:"vfx-chip",
              "data-on":String(o)===cur?"":void 0,
              onClick:function(){patchAt(i,vfxPatch1(k,o))},
              children:String(o)},String(o))})})]},k);
      return r.jsxs("div",{className:"vfx-prow",children:[
        r.jsx("span",{className:"vfx-plabel",children:b.label}),
        r.jsx("select",{className:"vfx-sel",value:cur,
          "aria-label":d.label+" — "+b.label,
          onChange:function(e){patchAt(i,vfxPatch1(k,e.target.value))},
          children:ch.map(function(o){
            return r.jsx("option",{value:String(o),children:String(o)},String(o))})})]},k)}
    var v=vfxN(f[k],vfxN(b.d,0));
    var step=vfxN(b.step,1);
    return r.jsxs("div",{className:"vfx-prow",children:[
      r.jsx("span",{className:"vfx-plabel",children:b.label}),
      r.jsx("input",{className:"vfx-range",type:"range",
        min:vfxN(b.min,0),max:vfxN(b.max,100),step:step,value:v,
        "aria-label":d.label+" — "+b.label,
        onChange:function(e){
          patchAt(i,vfxPatch1(k,vfxRound(vfxN(e.target.value,v),step<1?2:0)))}}),
      r.jsx("span",{className:"vfx-pval",
        children:(step<1?vfxRound(v,2):Math.round(v))+(b.unit?" "+b.unit:"")})]},k)}

  /* ── T103 (D2b) + t186 (G4) : la rangée « Sujet » — détourer le plan ─────────────────────────────────────────────
     PAYANT : 1er clic = devis, 2e clic = tir ; le modèle vient du registre
     (vfxMatte*, fin de couche). Résultat au Montage par `dz-matte`. */
  var sM=x.useState(0),mtick=sM[1];
  x.useEffect(function(){vfxMatteModels().then(function(){mtick(function(n){return n+1})})},[]);
  function emitMatte(name){
    window.dispatchEvent(new CustomEvent("dz-matte",{detail:{id:clip&&clip.id,matte:name||null}}))}
  function matteGo(){
    if(VFX_MATTE.busy||!clip||!clip.src||!clip.src.job_id)return;if(vfxMatteSansSujet(fireNote))return;
    if(!VFX_MATTE.arm){
      fetch("/api/cost/estimate",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify(vfxMatteDevis(vfxN(clip.end,0)-vfxN(clip.start,0)))})
        .then(function(res){return res.ok?res.json():null})
        .then(function(e){VFX_MATTE.arm={id:clip.id,label:((e&&e.breakdown&&e.breakdown[0])||{}).label||dzT("vfx.matte.devis_indisponible"),
          usd:e&&typeof e.total_usd==="number"?e.total_usd:null};mtick(function(n){return n+1})})
        .catch(function(){VFX_MATTE.arm={id:clip.id,label:dzT("vfx.matte.devis_indisponible"),usd:null};mtick(function(n){return n+1})});
      return}
    VFX_MATTE.arm=null;VFX_MATTE.busy=!0;mtick(function(n){return n+1});
    var id=clip.id;
    vfxPost("/api/matte",vfxMatteCorps(clip.src.job_id)).then(function(d){
      (function poll(){vfxJson("/api/matte/"+d.matte_id).then(function(st){
        if(st.status==="done"){VFX_MATTE.busy=!1;mtick(function(n){return n+1});
          window.dispatchEvent(new CustomEvent("dz-matte",{detail:{id:id,matte:st.file}}));
          fireNote(dzT("vfx.matte.sujet_detoure")+st.file+" — "+(st.usd_note||""))}
        else if(st.status==="failed"){VFX_MATTE.busy=!1;mtick(function(n){return n+1});fireNote(dzT("vfx.matte.detourage_err")+st.error)}
        else setTimeout(poll,1200)}).catch(function(e){VFX_MATTE.busy=!1;mtick(function(n){return n+1});
          fireNote(dzT("vfx.matte.detourage_err")+e.message)})})()})
      .catch(function(e){VFX_MATTE.busy=!1;mtick(function(n){return n+1});fireNote(dzT("vfx.matte.detourage_err")+e.message)})}
  function matteRow(){
    if(!clip||!clip.src||!clip.src.job_id)return null;
    var arme=VFX_MATTE.arm&&VFX_MATTE.arm.id===clip.id?VFX_MATTE.arm:null;
    var mods=VFX_MATTE.models||[];
    return r.jsxs("div",{className:"vfx-matte",children:[
      r.jsx("span",{className:"vfx-mlbl",children:clip.matte?dzT("vfx.matte.sujet_detoure")+clip.matte:dzT("vfx.matte.sujet_non_detoure")}),
      mods.length?r.jsx("select",{className:"vfx-sel",value:VFX_MATTE.model,"aria-label":dzT("vfx.matte.modele"),
        onChange:function(e){vfxMatteChoix(e.target.value);VFX_MATTE.arm=null;mtick(function(n){return n+1})},
        children:mods.map(function(o){return r.jsx("option",{value:o.id,children:vfxMatteLbl(o)},o.id)})}):null,vfxMatteSujetRow(mtick),
      r.jsx("button",{className:"vfx-btn","data-off":VFX_MATTE.busy||!mods.length?"":void 0,
        title:dzT("vfx.matte.bouton_aide"),
        onClick:matteGo,
        children:VFX_MATTE.busy?dzT("vfx.matte.en_cours"):arme?dzT("vfx.matte.confirmer"):(clip.matte?dzT("vfx.matte.redetourer"):dzT("vfx.matte.detourer"))}),
      clip.matte?r.jsx("button",{className:"vfx-btn",onClick:function(){emitMatte(null)},children:dzT("vfx.matte.retirer")}):null,
      arme?r.jsx("div",{className:"vfx-mhint",children:dzT("vfx.matte.devis")+(arme.usd==null?"":"~$"+arme.usd.toFixed(2)+" — ")+arme.label
        +dzT("vfx.matte.second_clic")}):null]})}

  function row(f,i){
    var d=ce(f.type);
    var open=!!exp[i];
    var off=!!f.off;
    var bounded=f.t0!=null&&f.t1!=null;
    return r.jsxs("div",{className:"vfx-mod","data-off":off?"":void 0,children:[
      r.jsxs("div",{className:"vfx-mhead",children:[
        r.jsx(VfxThumb,{url:vfxPreviewUrl(clip,f,120),fallback:vfxStaticUrl(f),
          h:34,alt:d.label,tick:tick,debounce:360}),
        r.jsxs("button",{className:"vfx-mname",
          "aria-expanded":open,
          title:dzT("vfx.pile.deplier",{nom:d.label}),
          onClick:function(){setExp(function(m){
            var nm=Object.assign({},m);
            if(nm[i])delete nm[i];else nm[i]=1;
            return nm})},
          children:[
          /* deux lignes (nom, puis résumé ou intervalle) : l'inspecteur du
             Montage fait ~266 px, une seule ligne tronquerait le nom */
          r.jsxs("span",{className:"vfx-mtxt",children:[
            r.jsx("span",{className:"vfx-mn",children:d.label}),
            bounded?r.jsx("span",{className:"vfx-mbadge",
              title:dzT("vfx.pile.actif",{t0:vfxSec(f.t0),t1:vfxSec(f.t1),resume:vfxSummary(f,d)}),
              children:vfxSec(f.t0)+" → "+vfxSec(f.t1)})
            :r.jsx("span",{className:"vfx-msum",children:vfxSummary(f,d)})]}),
          r.jsx("span",{className:"vfx-mcaret","aria-hidden":!0,children:open?__dzGl("dz-action-deplier"):__dzGl("dz-action-deplier","1em",{transform:"rotate(-90deg)"})})]}),
        r.jsx("button",{className:"vfx-iconbtn",disabled:i===0,
          title:dzT("vfx.pile.monter"),"aria-label":dzT("vfx.pile.monter_nom",{nom:d.label}),
          onClick:function(){moveAt(i,-1)},children:__dzGl("dz-edit-monter")}),
        r.jsx("button",{className:"vfx-iconbtn",disabled:i===list.length-1,
          title:dzT("vfx.pile.descendre"),"aria-label":dzT("vfx.pile.descendre_nom",{nom:d.label}),
          onClick:function(){moveAt(i,1)},children:__dzGl("dz-edit-descendre")}),
        /* T103 (D2b) : sur un plan détouré, chaque effet passe derrière le
           sujet (défaut) ou devant lui */
        clip&&clip.matte?r.jsx("button",{className:"vfx-tog","data-on":f.behind!==!1?"":void 0,
          role:"switch","aria-checked":f.behind!==!1,
          title:f.behind!==!1?dzT("vfx.pile.derriere_aide"):dzT("vfx.pile.devant_aide"),
          "aria-label":(f.behind!==!1?dzT("vfx.pile.passer_devant"):dzT("vfx.pile.passer_derriere"))+d.label,
          onClick:function(){patchAt(i,{behind:f.behind!==!1?!1:void 0},!0)},
          children:f.behind!==!1?dzT("vfx.pile.derriere"):dzT("vfx.pile.devant")}):null,
        r.jsx("button",{className:"vfx-iconbtn vfx-bypass","data-on":off?"":void 0,
          role:"switch","aria-checked":off,
          title:off?dzT("vfx.pile.reactiver_aide")
            :dzT("vfx.pile.contourner_aide"),
          "aria-label":(off?dzT("vfx.pile.reactiver"):dzT("vfx.pile.contourner"))+d.label,
          onClick:function(){bypassAt(i)},children:off?__dzGl("dz-etat-contourne"):__dzGl("dz-etat-actif")}),
        r.jsx("button",{className:"vfx-iconbtn vfx-del",
          title:dzT("vfx.pile.retirer"),"aria-label":dzT("vfx.pile.retirer_nom",{nom:d.label}),
          onClick:function(){removeAt(i)},children:__dzGl("dz-action-retirer")})]}),
      open?r.jsxs("div",{className:"vfx-mbody",children:[
        d.hint?r.jsx("div",{className:"vfx-mhint",children:d.hint}):null,
        presetRow(f,i,d),
        (d.params||[]).map(function(k){return paramRow(f,i,d,k)}),
        (d.params||[]).length?null:r.jsx("div",{className:"vfx-mhint",
          children:dzT("vfx.pile.sans_reglage")}),
        r.jsx(VfxBounds,{eff:f,dur:dur,
          onChange:function(patch){patchAt(i,patch)}})]}):null]},f.type+"#"+i)}

  return r.jsxs("div",{className:"vfx-stack",children:[
    r.jsxs("div",{className:"vfx-shead",children:[
      r.jsx("span",{className:"vfx-title",children:props.title||dzT("vfx.pile.titre")}),
      r.jsx("span",{className:"vfx-count",
        children:list.length?String(list.length):dzT("vfx.pile.vide")}),
      r.jsxs("div",{className:"vfx-ab",role:"group",
        "aria-label":dzT("vfx.pile.ab_aria"),children:[
        r.jsx("button",{className:"vfx-abbtn","data-on":!anyOn?"":void 0,
          disabled:!list.length,
          title:dzT("vfx.pile.avant_aide"),
          onClick:function(){if(anyOn)abToggle()},children:dzT("vfx.pile.avant")}),
        r.jsx("button",{className:"vfx-abbtn","data-on":anyOn?"":void 0,
          disabled:!list.length,
          title:dzT("vfx.pile.apres_aide"),
          onClick:function(){if(!anyOn)abToggle()},children:dzT("vfx.pile.apres")})]}),
      r.jsx("button",{className:"vfx-btn",disabled:!list.length,
        title:dzT("vfx.pile.vider_aide"),
        onClick:clearAll,children:dzT("vfx.pile.vider")}),
      props.onOpenPanel?r.jsx("button",{className:"vfx-btn vfx-add",
        title:dzT("vfx.pile.ouvrir_panneau"),
        onClick:function(){props.onOpenPanel()},children:__dzGlT("dz-action-ajouter",dzT("vfx.pile.ajouter"),"+")}):null]}),
    r.jsx(VfxAlert,{}),
    matteRow(),r.jsx(VfxIaRack,{clip:clip,onNote:fireNote}),
    list.length?r.jsx("div",{className:"vfx-mods",children:list.map(row)})
    :r.jsxs("div",{className:"vfx-empty",children:[
      r.jsx("div",{className:"vfx-emptytxt",children:dzT("vfx.pile.aucun")}),
      r.jsx("div",{className:"vfx-emptyhint",
        children:dzT("vfx.pile.aucun_aide")})]}),
    note?r.jsx("div",{className:"vfx-note",role:"status","aria-live":"polite",
      children:note}):null]})};

/* ── t186 (G4) : le modèle du détourage d'un plan, pris dans le registre unique ──
   GET /api/matte-models sert en tête les trois anciennes clés (BiRefNet v2 vidéo :
   general, matting, portrait) puis les modèles vidéo du registre (Bria VRMBG 3.0, VEED
   rapide, Pixelcut vidéo, SAM 3.1), chacun avec usd, unite, prompt, dispo, cle. Le
   libellé porte le prix (règle unique prixUsd de DzModelesIA, sinon dzPrixUsd du maillon
   encartsia) et, sans clé, la mention « clé X à ajouter dans Réglages » : l'option reste
   CHOISISSABLE, POST /api/matte refuse en 503 avant toute dépense. SAM 3.1 exige le sujet
   à garder (champ sous le sélecteur, refus avant l'envoi s'il est vide). Le choix est
   mémorisé (localStorage dz_detour_vfx) ; défaut historique : general. Ces fonctions
   vivent ICI, après la dernière édition G1 de la couche : la table dzglyph_paires.json
   repère les éditions par position (les retouches plus haut sont à longueur égale). */
var VFX_DETOUR_LS="dz_detour_vfx";
try{VFX_MATTE.model=localStorage.getItem(VFX_DETOUR_LS)||VFX_MATTE.model}catch(_e){}
VFX_MATTE.sujet="";
function vfxMatteMod(id){var l=VFX_MATTE.models||[];for(var i=0;i<l.length;i++)if(l[i].id===id)return l[i];return null}
/* un modèle mémorisé que le serveur ne sert plus retombe sur la première option (general) */
function vfxMatteValide(){var l=VFX_MATTE.models||[];if(l.length&&!vfxMatteMod(VFX_MATTE.model))VFX_MATTE.model=l[0].id}
function vfxMattePrixUsd(usd,unite){
  var f=(window.DzModelesIA&&window.DzModelesIA.prixUsd)||(typeof dzPrixUsd==="function"?dzPrixUsd:null);
  return f?f(usd,unite):""}
function vfxMatteNom(o){var k="detour.modele."+String(o.id||"").replace(/-/g,"_");
  return window.DZ_I18N&&window.DZ_I18N[k]?dzT(k):o.label}
function vfxMatteLbl(o){var p=vfxMattePrixUsd(o.usd,o.unite);
  return vfxMatteNom(o)+" · "+(p||dzT("ia.prix.a_mesurer"))+(o.dispo===!1&&o.cle?" · "+dzT("ia.cle.a_ajouter",{cle:o.cle}):"")}
function vfxMatteChoix(v){VFX_MATTE.model=v;try{localStorage.setItem(VFX_DETOUR_LS,v)}catch(_e){}}
function vfxMatteSujetReq(){var m=vfxMatteMod(VFX_MATTE.model);return!!(m&&m.prompt)}
function vfxMatteSansSujet(note){vfxMatteValide();
  if(!vfxMatteSujetReq()||String(VFX_MATTE.sujet||"").trim())return!1;
  note(dzT("detour.champ.sujet_requis"));return!0}
/* le devis : BiRefNet (anciennes clés, birefnet-v2-video) garde le kind « matte » d'avant ; les autres : « detourage »
   — copie JS de la règle unique du serveur, matte_service.op_devis (/matte et décor Avatar) */
function vfxMatteDevis(dur){var m=vfxMatteMod(VFX_MATTE.model),reg=(m&&m.registre)||VFX_MATTE.model;
  return reg==="birefnet-v2-video"||reg==="general"||reg==="matting"||reg==="portrait"?{kind:"matte",duration_s:dur}:{kind:"detourage",modele:reg,secondes:dur}}
function vfxMatteCorps(job){var c={job_id:job,model:VFX_MATTE.model};
  if(vfxMatteSujetReq())c.sujet=String(VFX_MATTE.sujet||"").trim();return c}
function vfxMatteSujetRow(tick){
  vfxMatteValide();
  if(!vfxMatteSujetReq())return null;
  return r.jsx("input",{className:"vfx-sel vfx-msujet",type:"text",value:VFX_MATTE.sujet||"","data-dzdetsujet":"1",
    placeholder:dzT("detour.champ.sujet"),"aria-label":dzT("detour.champ.sujet"),
    onChange:function(e){VFX_MATTE.sujet=e.target.value;VFX_MATTE.arm=null;tick(function(n){return n+1})}})}

/* petit utilitaire : {clé: valeur} calculé (les objets littéraux du bundle
   n'acceptent pas de clé dynamique en syntaxe ES5) */
function vfxPatch1(k,v){var o={};o[k]=v;return o}

/* ── export contrat ──────────────────────────────────────────────────────────
   `hist` : horodatage partagé du dernier point d'historique posé par l'hôte
   (le Montage regroupe les rafales de curseur en une seule annulation). */
window.DzVfx={ready:!0,Panel:VfxPanel,Stack:VfxStack,Bounds:VfxBounds,
  Thumb:VfxThumb,Alert:VfxAlert,catalog:vfxCatalog,previewUrl:vfxPreviewUrl,
  defaultsFor:vfxDefaultsFor,summary:vfxSummary,EASES:VFX_EASES,hist:{t:0},
  /* santé du service — lisible et sondable depuis la console de l'app */
  svc:VFX_SVC,retry:vfxRetryNow};

/* ── t188 (G6) : VFX IA — une vidéo (ou une image) -> une vidéo retouchée, douze gestes ──────────────────────────
   Le catalogue vient du BACKEND (GET /api/vfx-ia/modeles = /api/ia/catalogue?nature=vfx) : prix, unités,
   options (choix, défauts, bornes), les 154 effets PixVerse (filtrables) — rien n'est recopié ici. Un geste sans FAL_KEY reste
   CHOISISSABLE, avec « clé FAL_KEY à ajouter dans Réglages » : POST /api/vfx-ia refuse en 503 au lancement,
   avant toute dépense. PAYANT, deux clics : le 1er demande le devis (devis:true, LE chiffre de la garde des
   plafonds), le 2e tire ; la réponse redit le même usd. Toute retouche de la saisie désarme le devis.
   La vidéo rendue devient un job fini (Bibliothèque → Rendus, provenance « vfx_ia »). Partagé avec le rail
   « VFX IA » de Son & VFX par window.DzVfx.ia. Ces fonctions vivent ICI, après la dernière édition G1 de la
   couche : la table dzglyph_paires.json repère les éditions par position. */
var VFX_IA={cat:null,prom:null};
function vfxIaCatalogue(){
  if(VFX_IA.cat)return Promise.resolve(VFX_IA.cat);
  if(!VFX_IA.prom)VFX_IA.prom=fetch("/api/vfx-ia/modeles").then(function(r2){return r2.ok?r2.json():null})
    .then(function(d){VFX_IA.cat=(d&&d.modeles)||[];return VFX_IA.cat})
    .catch(function(){VFX_IA.prom=null;return []});
  return VFX_IA.prom}
/* les images de la Bibliothèque (image de la lumière, référence, image à animer), les plus récentes d'abord */
function vfxIaImages(){
  return fetch("/api/images").then(function(r2){return r2.ok?r2.json():null})
    .then(function(d){return ((d&&d.images)||[]).slice().sort(function(a,b){return (b.mtime||0)-(a.mtime||0)})
      .slice(0,80).map(function(i){return i.filename})})
    .catch(function(){return []})}
/* titre et phrase de chaque geste (la phrase dit à l'utilisateur ce qu'il doit donner) */
function vfxIaTextes(){return {
  "relight-h3":[dzT("vfx.ia.relight_h3.titre"),dzT("vfx.ia.relight_h3.phrase")],
  "inserer-h3":[dzT("vfx.ia.inserer_h3.titre"),dzT("vfx.ia.inserer_h3.phrase")],
  "effacer-perso":[dzT("vfx.ia.effacer_perso.titre"),dzT("vfx.ia.effacer_perso.phrase")],
  "effacer-objet":[dzT("vfx.ia.effacer_objet.titre"),dzT("vfx.ia.effacer_objet.phrase")],
  "jour-nuit":[dzT("vfx.ia.jour_nuit.titre"),dzT("vfx.ia.jour_nuit.phrase")],
  "eau":[dzT("vfx.ia.eau.titre"),dzT("vfx.ia.eau.phrase")],
  "coloriser":[dzT("vfx.ia.coloriser.titre"),dzT("vfx.ia.coloriser.phrase")],
  "retoucher-kling":[dzT("vfx.ia.retoucher_kling.titre"),dzT("vfx.ia.retoucher_kling.phrase")],
  "retoucher-flux3":[dzT("vfx.ia.retoucher_flux3.titre"),dzT("vfx.ia.retoucher_flux3.phrase")],
  "recadrer":[dzT("vfx.ia.recadrer.titre"),dzT("vfx.ia.recadrer.phrase")],
  "agrandir":[dzT("vfx.ia.agrandir.titre"),dzT("vfx.ia.agrandir.phrase")],
  "effets-pixverse":[dzT("vfx.ia.effets_pixverse.titre"),dzT("vfx.ia.effets_pixverse.phrase")]}}
function vfxIaTitre(m){var t=vfxIaTextes()[m.id];return t?t[0]:m.label}
function vfxIaPhrase(m){var t=vfxIaTextes()[m.id];return t?t[1]:(m.phrase||"")}
function vfxIaOptLbl(k){return ({resolution:dzT("vfx.ia.opt.resolution"),aspect_ratio:dzT("vfx.ia.opt.format"),
  seed:dzT("vfx.ia.opt.graine"),start_time:dzT("vfx.ia.opt.debut"),resume_time:dzT("vfx.ia.opt.reprise"),
  duration:dzT("vfx.ia.opt.duree"),color_match:dzT("vfx.ia.opt.couleurs"),
  enable_prompt_expansion:dzT("vfx.ia.opt.enrichir"),mask_prompt:dzT("vfx.ia.opt.objet"),
  enable_pass2_refinement:dzT("vfx.ia.opt.passe2"),upscale_factor:dzT("vfx.ia.opt.facteur"),
  effect:dzT("vfx.ia.opt.effet")})[k]||k}
function vfxIaUnite(u){return ({s:dzT("vfx.ia.unite.s"),mp:dzT("vfx.ia.unite.mp"),video:dzT("vfx.ia.unite.video"),
  tranche10s:dzT("vfx.ia.unite.tranche10s"),effet:dzT("vfx.ia.unite.effet")})[u]||""}
/* « $ » + la valeur arrondie au millième, au moins deux décimales (règle prixUsd de DzModelesIA) ; sous 0,01 $
   (le mégapixel LTX : 0,0024075) cinq chiffres significatifs, sinon il s'afficherait « $0.002 » ; nul -> "" */
function vfxIaUsd(v){v=Number(v);if(!(v>0)||!isFinite(v))return "";
  var s=v<0.01?String(Number(v.toPrecision(5))):(Math.round(v*1000)/1000).toFixed(3);
  while(/\.\d{3,}$/.test(s)&&s.charAt(s.length-1)==="0")s=s.slice(0,-1);return "$"+s}
function vfxIaPrix(m){var p=vfxIaUsd(m.usd);
  return (p?p+vfxIaUnite(m.unite):dzT("ia.prix.a_mesurer"))+(m.dispo===!1&&m.cle?" · "+dzT("ia.cle.a_ajouter",{cle:m.cle}):"")}
function vfxIaVide(){return {prompt:"",image:"",opts:{},filtres:{}}}
/* le corps de POST /api/vfx-ia : la source (clip_id = le job du plan), le geste, ce que l'utilisateur a saisi */
function vfxIaCorps(m,st,job){var c={modele:m.id},o={},k;
  if(m.entree==="video"&&job)c.clip_id=job;
  if(m.prompt&&String(st.prompt||"").trim())c.prompt=String(st.prompt).trim();
  if(m.image&&st.image)c.image_filename=st.image;
  for(k in st.opts)if(st.opts[k]!==""&&st.opts[k]!=null&&(m.options||{})[k])o[k]=st.opts[k];
  c.options=o;return c}
/* ce qui manque AVANT d'appeler le serveur (le serveur refuse pareil, en 400) : null si tout y est */
function vfxIaManque(m,st,job){var o=m.options||{},k;
  if(m.entree==="video"&&!job)return dzT("vfx.ia.manque_video");
  if(m.image==="requis"&&!st.image)return m.entree==="image"?dzT("vfx.ia.manque_image_animer"):dzT("vfx.ia.manque_image_lumiere");
  if(m.prompt==="requis"&&!String(st.prompt||"").trim())return dzT("vfx.ia.manque_prompt");
  for(k in o)if(o[k].requis&&(st.opts[k]===""||st.opts[k]==null))return dzT("vfx.ia.manque_option",{nom:vfxIaOptLbl(k)});
  return null}
function vfxIaPost(corps){
  return fetch("/api/vfx-ia",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(corps)})
    .then(function(r2){return r2.json().catch(function(){return {}}).then(function(d){
      if(!r2.ok){var x2=d&&d.detail;throw new Error(typeof x2==="string"?x2:(x2&&x2.message)||("HTTP "+r2.status))}
      return d})})}
/* les deux clics : `arm` = le devis en attente ({sig, usd, detail}), valable pour CETTE saisie seulement */
function vfxIaClic(m,st,job,g){
  if(g.busy)return;var manque=vfxIaManque(m,st,job);if(manque){g.note(manque);return}
  var corps=vfxIaCorps(m,st,job),sig=JSON.stringify(corps);
  if(!g.arm||g.arm.sig!==sig){
    vfxIaPost(Object.assign({devis:!0},corps))
      .then(function(d){g.setArm({sig:sig,usd:d.usd,detail:d.detail||""})})
      .catch(function(e){g.setArm(null);g.note(dzT("vfx.ia.echec",{err:e.message}))});
    return}
  g.setArm(null);g.setBusy(!0);
  vfxIaPost(corps).then(function(d){g.setBusy(!1);
      g.note(dzT("vfx.ia.fait",{nom:d.filename,prix:vfxIaUsd(d.usd)||dzT("ia.prix.a_mesurer")}));
      if(g.done)g.done(d)})
    .catch(function(e){g.setBusy(!1);g.note(dzT("vfx.ia.echec",{err:e.message}))})}
function vfxIaDevisTxt(arm){
  return dzT("vfx.ia.devis",{prix:vfxIaUsd(arm.usd)||dzT("ia.prix.a_mesurer"),detail:arm.detail})}
/* les champs d'un geste, construits d'après le SCHÉMA servi (aucune liste recopiée) ; `k` = classes de l'hôte */
function VfxIaChamps(props){
  var m=props.m,st=props.st,k=props.k||{},o=m.options||{},out=[];
  function setOpt(n,v){var no=Object.assign({},st.opts);no[n]=v;props.set({opts:no})}
  if(m.prompt)out.push(r.jsx("textarea",{className:k.texte,rows:2,maxLength:1500,value:st.prompt,
    "aria-label":dzT("vfx.ia.prompt"),
    placeholder:m.prompt==="requis"?dzT("vfx.ia.prompt_requis"):dzT("vfx.ia.prompt_facultatif"),
    onChange:function(e){props.set({prompt:e.target.value})}},"p"));
  if(m.image)out.push(r.jsxs("select",{className:k.sel,value:st.image,"aria-label":dzT("vfx.ia.image"),
    onChange:function(e){props.set({image:e.target.value})},children:[
    r.jsx("option",{value:"",children:m.image==="requis"?(m.entree==="image"?dzT("vfx.ia.image_animer"):dzT("vfx.ia.image_lumiere"))
      :dzT("vfx.ia.image_reference")},""),
    (props.images||[]).map(function(f){return r.jsx("option",{value:f,children:f},f)})]},"i"));
  Object.keys(o).forEach(function(n){var s=o[n],v=st.opts[n],lbl=vfxIaOptLbl(n)+(s.requis?" *":"");
    /* une longue énumération (les 154 effets PixVerse) : un champ de filtre au-dessus du <select> ; le choix
       courant reste toujours dans la liste */
    if(s.choix&&s.choix.length>30){var fl=String((st.filtres||{})[n]||""),q=fl.trim().toLowerCase(),
        cur=v!=null?String(v):"",vus=s.choix.filter(function(c){return !q||c.toLowerCase().indexOf(q)>=0||c===cur});
      out.push(r.jsx("input",{className:k.sel,type:"search",value:fl,"aria-label":dzT("vfx.ia.filtrer"),
        placeholder:dzT("vfx.ia.filtrer_n",{n:s.choix.length}),
        onChange:function(e){var nf=Object.assign({},st.filtres||{});nf[n]=e.target.value;props.set({filtres:nf})}},n+"-f"));
      out.push(r.jsxs("label",{className:k.ligne,children:[r.jsx("span",{className:k.lbl,children:lbl}),
        r.jsxs("select",{className:k.sel,value:cur,"aria-label":lbl,
          onChange:function(e){setOpt(n,e.target.value)},children:[
          r.jsx("option",{value:"",children:dzT("vfx.ia.choisir_n",{n:vus.length})},""),
          vus.map(function(c){return r.jsx("option",{value:c,children:c},c)})]})]},n))}
    else if(s.choix)out.push(r.jsxs("label",{className:k.ligne,children:[r.jsx("span",{className:k.lbl,children:lbl}),
      r.jsxs("select",{className:k.sel,value:v!=null?String(v):(s.defaut!=null?String(s.defaut):""),"aria-label":lbl,
        onChange:function(e){setOpt(n,e.target.value)},children:[
        s.defaut==null?r.jsx("option",{value:"",children:dzT("vfx.ia.choisir")},""):null,
        s.choix.map(function(c){return r.jsx("option",{value:c,children:c},c)})]})]},n));
    else if(s.bool)out.push(r.jsxs("label",{className:k.ligne,children:[
      r.jsx("input",{type:"checkbox",checked:!!v,onChange:function(e){setOpt(n,e.target.checked)}}),
      r.jsx("span",{className:k.lbl,children:lbl})]},n));
    else if(s.num)out.push(r.jsxs("label",{className:k.ligne,children:[r.jsx("span",{className:k.lbl,children:lbl}),
      r.jsx("input",{className:k.num,type:"number",min:s.num[0],max:s.num[1],step:s.entier?1:.125,
        value:v!=null?v:(s.defaut!=null?s.defaut:""),"aria-label":lbl,placeholder:s.num[0]+" – "+s.num[1],
        onChange:function(e){var t=e.target.value;setOpt(n,t===""?"":Number(t))}})]},n));
    else out.push(r.jsxs("label",{className:k.ligne,children:[r.jsx("span",{className:k.lbl,children:lbl}),
      r.jsx("input",{className:k.sel,type:"text",value:v||"","aria-label":lbl,maxLength:300,
        onChange:function(e){setOpt(n,e.target.value)}})]},n))});
  return r.jsx("div",{className:k.bloc,style:{display:"flex",flexDirection:"column",gap:6,marginTop:8},children:out})}
/* la section « IA » du rack, sous « Détourer » : les gestes qui partent d'une VIDÉO, sur le plan sélectionné */
function VfxIaRack(props){
  var US=x.useState,EF=x.useEffect,clip=props.clip;
  var s1=US(VFX_IA.cat),cat=s1[0],setCat=s1[1];
  var s2=US(""),mid=s2[0],setMid=s2[1];
  var s3=US(vfxIaVide()),st=s3[0],setSt=s3[1];
  var s4=US(null),arm=s4[0],setArm=s4[1];
  var s5=US(!1),busy=s5[0],setBusy=s5[1];
  var s6=US([]),imgs=s6[0],setImgs=s6[1];
  EF(function(){var vivant=!0;vfxIaCatalogue().then(function(c){if(vivant)setCat(c)});
    vfxIaImages().then(function(l){if(vivant)setImgs(l)});return function(){vivant=!1}},[]);
  EF(function(){setArm(null)},[clip&&clip.id]);
  if(!clip||!clip.src||!clip.src.job_id)return null;
  var vids=(cat||[]).filter(function(v){return v.entree==="video"});
  var m=vids.filter(function(v){return v.id===mid})[0]||vids[0];
  var job=clip.src.job_id,g={busy:busy,arm:arm,setArm:setArm,setBusy:setBusy,note:props.onNote};
  return r.jsxs("div",{className:"vfx-matte vfx-ia","data-dzvfxia":"rack",children:[
    r.jsx("span",{className:"vfx-mlbl",children:dzT("vfx.ia.section")}),
    vids.length?r.jsx("select",{className:"vfx-sel",value:m?m.id:"","aria-label":dzT("vfx.ia.geste"),
      onChange:function(e){setMid(e.target.value);setSt(vfxIaVide());setArm(null)},
      children:vids.map(function(v){return r.jsx("option",{value:v.id,children:vfxIaTitre(v)+" · "+vfxIaPrix(v)},v.id)})})
      :r.jsx("div",{className:"vfx-mhint",children:dzT("vfx.ia.chargement")}),
    m?r.jsx("div",{className:"vfx-mhint vfx-iaphrase",children:vfxIaPhrase(m)}):null,
    m?r.jsx(VfxIaChamps,{m:m,st:st,images:imgs,k:{bloc:"vfx-iachamps",texte:"vfx-sel vfx-iatexte",sel:"vfx-sel",
      num:"vfx-sel vfx-ianum",ligne:"vfx-prow",lbl:"vfx-plabel"},
      set:function(p){setSt(Object.assign({},st,p));setArm(null)}}):null,
    m?r.jsx("button",{className:"vfx-btn","data-off":busy?"":void 0,title:dzT("vfx.ia.bouton_aide"),
      onClick:function(){vfxIaClic(m,st,job,g)},
      children:busy?dzT("vfx.ia.en_cours"):arm?dzT("vfx.ia.confirmer"):dzT("vfx.ia.lancer")}):null,
    arm?r.jsx("div",{className:"vfx-mhint",children:vfxIaDevisTxt(arm)}):null]})}
/* t188 : les aides des VFX IA, pour le rail « VFX IA » de Son & VFX */
window.DzVfx.ia={catalogue:vfxIaCatalogue,images:vfxIaImages,titre:vfxIaTitre,phrase:vfxIaPhrase,prix:vfxIaPrix,clic:vfxIaClic,devisTxt:vfxIaDevisTxt,Champs:VfxIaChamps,Rack:VfxIaRack};
