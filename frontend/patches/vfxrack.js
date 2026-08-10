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
    if(!res.ok||ct.indexOf("json")<0)throw new Error("réponse non JSON");
    return res.json()})}

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
  colorize:{label:"Colorisation",params:["preset","intensity"],
    presets:["sepia","bw","duotone","matrix","redalert","gold"]},
  vhs:{label:"VHS",params:["intensity","speed"]},
  gradient:{label:"Dégradé",params:["c0","c1","angle","opacity","blend"]},
  grain:{label:"Grain film",params:["intensity"]},
  vignette:{label:"Vignette",params:["intensity"]},
  chroma:{label:"Aberration chromatique",params:["intensity"]},
  glitch:{label:"Glitch",params:["intensity"]},
  bloom:{label:"Bloom / Glow",params:["intensity"]},
  halation:{label:"Halation",params:["intensity"]},
  scanlines:{label:"Scanlines / CRT",params:["intensity"]},
  letterbox:{label:"Letterbox ciné",params:["ratio"]},
  oldfilm:{label:"Old film",params:["intensity"]},
  sharpen:{label:"Netteté",params:["intensity"]},
  blur:{label:"Flou",params:["intensity"]},
  dreamy:{label:"Soft / Dreamy",params:["intensity"]},
  pixelate:{label:"Pixelate",params:["intensity"]},
  shake:{label:"Camera shake",params:["intensity","speed"]},
  mirror:{label:"Miroir",params:[]},
  invert:{label:"Négatif",params:[]}};

/* catégorie + phrase d'aide par effet — la catégorie du backend gagne si
   elle existe (clé `category`), sinon celle-ci ; inconnu → « autres ». */
var VFX_META={
  grade:{cat:"couleur",hint:"Étalonnage cinéma — 10 rendus, du teal & orange au noir contrasté."},
  colorize:{cat:"couleur",hint:"Teinte unique : sépia, N&B, duotone, alerte rouge, or."},
  gradient:{cat:"couleur",hint:"Dégradé de deux couleurs fusionné sur l'image."},
  vhs:{cat:"retro",hint:"Bande usée : lignes déplacées, bruit, chroma qui bave."},
  oldfilm:{cat:"retro",hint:"Pellicule fatiguée : poussières, sautes, vignettage."},
  scanlines:{cat:"retro",hint:"Lignes de balayage d'un tube cathodique."},
  grain:{cat:"retro",hint:"Grain argentique — de la texture sans salir l'image."},
  pixelate:{cat:"retro",hint:"Mosaïque — gros pixels, façon écran de 1998."},
  bloom:{cat:"lumiere",hint:"Les hautes lumières débordent et rayonnent."},
  halation:{cat:"lumiere",hint:"Halo chaud autour des sources vives, comme sur pellicule."},
  vignette:{cat:"lumiere",hint:"Bords assombris : le regard va au centre."},
  dreamy:{cat:"lumiere",hint:"Voile doux — portraits, souvenirs, rêve."},
  chroma:{cat:"optique",hint:"Franges colorées sur les bords, comme un objectif bon marché."},
  blur:{cat:"optique",hint:"Flou d'ensemble — arrière-plan ou transition."},
  sharpen:{cat:"optique",hint:"Accentue les contours — à doser, ça crie vite."},
  glitch:{cat:"optique",hint:"Décrochages numériques, blocs déplacés."},
  shake:{cat:"mouvement",hint:"Caméra à l'épaule — impact, panique, course."},
  mirror:{cat:"mouvement",hint:"Symétrie verticale de l'image."},
  invert:{cat:"mouvement",hint:"Négatif — inversion complète des valeurs."},
  letterbox:{cat:"cadre",hint:"Bandes noires : le format scope, tout de suite."}};

var VFX_BLENDS=["screen","overlay","multiply","softlight","addition","normal"];
/* courbes de rampe — noms EXACTS acceptés par animation_service.ease() */
var VFX_EASES=[["smooth","douce"],["linear","linéaire"],["easeIn","accélérée"],
  ["easeOut","freinée"],["easeInOut","douce (2 sens)"],["easeInOutSine","sinus"],
  ["anticipate","anticipation"],["overshoot","dépassement"],
  ["easeOutBack","retour"],["easeOutBounce","rebond"]];

/* catégories de repli — la liste FAIT AUTORITÉ côté backend dès que
   /api/effects/catalog répond (clé `categories`), celle-ci ne sert qu'au
   catalogue local et à /api/montage/effects. */
var VFX_CATS_FB=[["couleur","Couleur"],["retro","Rétro"],["lumiere","Lumière"],
  ["optique","Optique"],["mouvement","Mouvement"],["cadre","Cadre"]];

/* bornes de repli par paramètre — miroir de _PARAM_DEFAULTS (effects_engine) ;
   le backend renvoie `bounds` par effet et gagne toujours. */
var VFX_PBOUNDS={
  intensity:{type:"range",min:0,max:100,step:1,d:60,label:"Intensité",unit:"%"},
  speed:{type:"range",min:0,max:100,step:1,d:50,label:"Vitesse",unit:"%"},
  angle:{type:"range",min:0,max:360,step:1,d:45,label:"Angle",unit:"°"},
  opacity:{type:"range",min:0,max:100,step:1,d:40,label:"Opacité",unit:"%"},
  cx:{type:"range",min:0,max:100,step:1,d:50,label:"Centre X",unit:"%"},
  cy:{type:"range",min:0,max:100,step:1,d:40,label:"Centre Y",unit:"%"},
  c0:{type:"color",d:"#00e5ff",label:"Couleur 1"},
  c1:{type:"color",d:"#9945ff",label:"Couleur 2"},
  blend:{type:"choice",choices:VFX_BLENDS,d:"screen",label:"Fusion"},
  ratio:{type:"choice",choices:["2.39","2.35","1.85","1.33"],d:"2.35",
    label:"Format"},
  preset:{type:"choice",choices:[],d:"",label:"Préréglage"},
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
  if(hasOther){cats.push(["autres","Autres"]);lbl.autres="Autres"}
  /* « tous » et « ★ » ouvrent toujours la rangée d'onglets */
  return {src:src,by:by,list:list,
    cats:[["tous","Tous"],["fav","★"]].concat(cats)}}
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
  return b.length?b.join(" · "):"sans réglage"}

/* clés d'état d'un effet qui ne sont PAS des paramètres de rendu d'image */
var VFX_PRV_SKIP={type:1,off:1,label:1,t0:1,t1:1,fade_in:1,fade_out:1,
  ease_in:1,ease_out:1};
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
      title:"Aperçu indisponible — ni /api/effects/preview ni /effect-thumbs "+
        "ne rendent d'image pour cet effet.",
      children:"aperçu —"})
    :(useFb?r.jsx("span",{className:"vfx-thumbgen",
        title:"Aperçu générique — /api/effects/preview (rendu sur VOTRE plan) "+
          "n'est pas disponible ; ceci est la vignette de référence de l'effet.",
        children:"gén."})
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
  var when=svc.probing?"Nouvelle tentative en cours…"
    :"Reprise automatique — nouvelle tentative dans "+left+" s.";
  /* dire EXACTEMENT ce qui manque : catalogue jamais reçu, ou catalogue
     d'avant la panne encore en mémoire mais vignettes mortes. */
  var what=loc
    ?"Ceci n'est PAS le rack complet : liste de secours locale ("+n+" effets, "+
     "posables), sans vignette rendue sur votre plan, sans les préréglages "+
     "ni les bornes du moteur."
    :"Les "+n+" effets ci-dessous datent d'avant la panne et restent posables, "+
     "mais AUCUNE vignette ne peut plus être rendue sur votre plan.";
  return r.jsxs("div",{className:"vfx-alert",role:"alert","aria-live":"assertive",
    children:[
    r.jsx("span",{className:"vfx-alerticon","aria-hidden":!0,children:"!"}),
    r.jsxs("div",{className:"vfx-alerttxt",children:[
      r.jsx("b",{className:"vfx-alerthead",
        children:"Service d'effets injoignable — le backend ne répond pas."}),
      r.jsx("span",{className:"vfx-alertsub",children:
        "/api/effects/catalog et /api/effects/preview sont muets sur "+
        "127.0.0.1:8765. "+what+" Relancez DeepotusVideoGen ; le rack se "+
        "remplira tout seul, sans rouvrir ce panneau."}),
      r.jsx("span",{className:"vfx-alertwhen",children:when})]}),
    r.jsx("button",{className:"vfx-btn vfx-alertbtn",disabled:!!svc.probing,
      title:"Redemander /api/effects/catalog immédiatement",
      onClick:vfxRetryNow,children:"Réessayer maintenant"})]})};

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
  var tabs=(cat&&cat.cats)||[["tous","Tous"],["fav","★"]];
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
    fireNote("« "+e.label+" » posé sur le clip — réglez-le dans la pile.")}

  function dragStart(ev,e){
    var eff=vfxDefaultsFor(e.type,e);
    try{
      ev.dataTransfer.setData("dz-vfx",JSON.stringify(Object.assign({label:e.label},eff)));
      ev.dataTransfer.effectAllowed="copy";
      var g=document.createElement("div");
      g.textContent="✦ "+e.label;
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
      title:e.hint?(e.hint+"\n\nClic : poser · glisser sur un clip · F : favori")
        :"Clic : poser · glisser sur un clip · F : favori",
      "aria-label":e.label+(e.hint?" — "+e.hint:""),
      children:[
      r.jsx(VfxThumb,{url:vfxPreviewUrl(clip,eff,168),fallback:vfxStaticUrl(eff),
        h:74,alt:e.label,tick:tick}),
      r.jsxs("div",{className:"vfx-tilefoot",children:[
        r.jsx("span",{className:"vfx-tilename",children:e.label}),
        r.jsx("button",{className:"vfx-fav","data-on":on?"":void 0,tabIndex:-1,
          "aria-pressed":on,
          title:on?"Retirer des favoris (F)":"Ajouter aux favoris (F)",
          "aria-label":(on?"Retirer des favoris : ":"Ajouter aux favoris : ")+e.label,
          onClick:function(ev){ev.stopPropagation();favToggle(e.type)},
          children:on?"★":"☆"})]}),
      n?r.jsx("span",{className:"vfx-tilebadge",
        title:"Déjà dans la pile de ce clip ("+n+")",children:"×"+n}):null]},e.type)}

  function body(){
    if(!cat)
      return r.jsx("div",{className:"vfx-grid",children:[0,1,2,3,4,5].map(function(i){
        return r.jsx("div",{className:"vfx-tile vfx-tileskel","aria-hidden":!0},"s"+i)})});
    if(!shown.length)
      return r.jsxs("div",{className:"vfx-empty",children:[
        r.jsx("div",{className:"vfx-emptytxt",children:qn
          ?"Aucun effet pour « "+qn+" »."
          :tab==="fav"?"Aucun effet favori pour l'instant."
          :"Aucun effet dans cette catégorie."}),
        qn?r.jsx("button",{className:"vfx-btn",onClick:function(){setQuery("")},
          children:"Effacer la recherche"})
        :tab==="fav"?r.jsx("div",{className:"vfx-emptyhint",
          children:"Survolez un effet et cliquez ★ (ou touche F) pour l'épingler ici."}):null]});
    return r.jsx("div",{className:"vfx-grid",children:shown.map(tile)})}

  if(!open)return null;
  var srcLbl=cat?(cat.src==="catalog"?"catalogue moteur"
    :cat.src==="montage"?"catalogue Montage":"catalogue local (backend muet)"):"…";
  return r.jsxs("div",{className:inline?"vfx-rack vfx-inline":"vfx-rack vfx-float",
    ref:rootRef,tabIndex:inline?void 0:-1,onKeyDown:onKey,
    role:"group","aria-label":"Panneau d'effets vidéo",children:[
    r.jsxs("div",{className:"vfx-head",children:[
      r.jsx("span",{className:"vfx-title",children:props.title||"Effets"}),
      r.jsx("span",{className:"vfx-count",children:String((cat&&cat.list.length)||0)}),
      clip&&clip.label?r.jsx("span",{className:"vfx-on",
        title:"Les vignettes sont rendues sur CE plan",
        children:"sur « "+clip.label+" »"}):null,
      inline?null:r.jsx("button",{className:"vfx-iconbtn vfx-close",
        title:"Fermer (Échap)","aria-label":"Fermer le panneau d'effets",
        onClick:function(){if(props.onClose)props.onClose()},children:"✕"})]}),
    r.jsx(VfxAlert,{}),
    r.jsxs("div",{className:"vfx-searchrow",children:[
      r.jsx("input",{className:"vfx-search",ref:searchRef,type:"text",value:query,
        placeholder:"Rechercher un effet…","aria-label":"Rechercher un effet",
        onChange:function(e){setQuery(e.target.value)}}),
      r.jsx("kbd",{className:"vfx-kbd","aria-hidden":!0,children:"/"})]}),
    r.jsx("div",{className:"vfx-tabs",role:"tablist",children:
      tabs.filter(function(c){
        return c[0]==="tous"||c[0]==="fav"||(counts[c[0]]||0)>0}).map(function(c){
        return r.jsxs("button",{className:"vfx-tab",role:"tab",
          "aria-selected":tab===c[0],"data-on":tab===c[0]?"":void 0,
          "aria-label":c[0]==="fav"?"Favoris ("+(counts.fav||0)+")":void 0,
          onClick:function(){setTab(c[0])},children:[
          c[1],
          r.jsx("span",{className:"vfx-tcount",children:String(counts[c[0]]||0)})]},c[0])})}),
    body(),
    note?r.jsx("div",{className:"vfx-note",role:"status","aria-live":"polite",
      children:note}):null,
    r.jsxs("div",{className:"vfx-foot",children:[
      r.jsxs("span",{className:"vfx-hints","aria-hidden":!0,children:[
        r.jsx("kbd",{children:"clic"}),inline?" choisir · ":" poser · ",
        inline?null:r.jsx("kbd",{children:"glisser"}),
        inline?null:" sur un clip · ",
        r.jsx("kbd",{children:"F"})," favori · ",
        r.jsx("kbd",{children:"/"})," recherche"]}),
      r.jsx("span",{className:"vfx-src",title:"Origine du catalogue d'effets",
        children:srcLbl}),
      /* service debout mais des vignettes ont raté (ffmpeg saturé, cache
         froid…) : la panne globale est traitée par le bandeau, ceci ne
         couvre que les échecs isolés. */
      (svc.st==="ok"&&svc.fails)?r.jsx("button",{className:"vfx-btn",
        title:"Redemander les vignettes à /api/effects/preview",
        onClick:function(){
          VFX_SVC.fails=0;setTick(function(t){return t+1})},
        children:"Réessayer les aperçus"}):null]})]})};

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
      title:on?"Repasser l'effet sur tout le plan"
        :"Limiter l'effet à un intervalle du plan (t0 → t1), avec rampe",
      children:[
      r.jsx("span",{className:"vfx-sw","data-on":on?"":void 0,"aria-hidden":!0,
        children:r.jsx("i",{className:"vfx-swk"})}),
      r.jsx("span",{className:"vfx-blabel",children:"Bornes temporelles"}),
      r.jsx("span",{className:"vfx-bsum",children:on
        ?vfxSec(t0)+" → "+vfxSec(t1):"tout le plan"})]}),
    on?r.jsxs("div",{className:"vfx-bbody",children:[
      r.jsxs("div",{className:"vfx-prow",children:[
        r.jsx("span",{className:"vfx-plabel",children:"Début"}),
        r.jsx("input",{className:"vfx-range",type:"range",min:0,max:vfxRound(dur,2),
          step:.05,value:t0,"aria-label":"Début de l'effet (s)",
          onChange:function(e){
            var v=vfxClamp(vfxN(e.target.value,0),0,Math.max(0,t1-.05));
            set({t0:vfxRound(v,2)})}}),
        num({min:0,max:vfxRound(dur,2),step:.05,value:vfxRound(t0,2),
          "aria-label":"Début précis (s)",
          onChange:function(e){
            var v=vfxClamp(vfxN(e.target.value,t0),0,Math.max(0,t1-.05));
            set({t0:vfxRound(v,2)})}}),
        r.jsx("span",{className:"vfx-punit",children:"s"})]}),
      r.jsxs("div",{className:"vfx-prow",children:[
        r.jsx("span",{className:"vfx-plabel",children:"Fin"}),
        r.jsx("input",{className:"vfx-range",type:"range",min:0,max:vfxRound(dur,2),
          step:.05,value:t1,"aria-label":"Fin de l'effet (s)",
          onChange:function(e){
            var v=vfxClamp(vfxN(e.target.value,dur),Math.min(dur,t0+.05),dur);
            set({t1:vfxRound(v,2)})}}),
        num({min:0,max:vfxRound(dur,2),step:.05,value:vfxRound(t1,2),
          "aria-label":"Fin précise (s)",
          onChange:function(e){
            var v=vfxClamp(vfxN(e.target.value,t1),Math.min(dur,t0+.05),dur);
            set({t1:vfxRound(v,2)})}}),
        r.jsx("span",{className:"vfx-punit",children:"s"})]}),
      r.jsxs("div",{className:"vfx-prow",children:[
        r.jsx("span",{className:"vfx-plabel",children:"Rampe entrée"}),
        num({min:0,max:vfxRound(span/2,2),step:.05,value:vfxRound(fi,2),
          "aria-label":"Durée de la rampe d'entrée (s)",
          onChange:function(e){
            set({fade_in:vfxRound(vfxClamp(vfxN(e.target.value,0),0,span/2),2)})}}),
        r.jsx("span",{className:"vfx-punit",children:"s"}),
        r.jsx("select",{className:"vfx-sel",value:eff.ease_in||"smooth",
          "aria-label":"Courbe de la rampe d'entrée",disabled:!(fi>0),
          onChange:function(e){set({ease_in:e.target.value})},
          children:VFX_EASES.map(function(o){
            return r.jsx("option",{value:o[0],children:o[1]},o[0])})})]}),
      r.jsxs("div",{className:"vfx-prow",children:[
        r.jsx("span",{className:"vfx-plabel",children:"Rampe sortie"}),
        num({min:0,max:vfxRound(span/2,2),step:.05,value:vfxRound(fo,2),
          "aria-label":"Durée de la rampe de sortie (s)",
          onChange:function(e){
            set({fade_out:vfxRound(vfxClamp(vfxN(e.target.value,0),0,span/2),2)})}}),
        r.jsx("span",{className:"vfx-punit",children:"s"}),
        r.jsx("select",{className:"vfx-sel",value:eff.ease_out||"smooth",
          "aria-label":"Courbe de la rampe de sortie",disabled:!(fo>0),
          onChange:function(e){set({ease_out:e.target.value})},
          children:VFX_EASES.map(function(o){
            return r.jsx("option",{value:o[0],children:o[1]},o[0])})})]}),
      eff.type==="shake"?r.jsx("div",{className:"vfx-bnote",
        children:"Camera shake : entrée et sortie franches — mélanger une image "+
          "secouée avec l'image fixe la dédoublerait."}):null,
      r.jsx("div",{className:"vfx-bnote",
        children:"Hors de l'intervalle, le plan reste intact."})]}):null]})};

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
    fireNote("« "+ce(f&&f.type).label+" » retiré de la pile.")}
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
    fireNote(anyOn?"Avant : toute la pile est contournée (le rendu ignore ces effets)."
      :"Après : la pile est réactivée.")}
  function clearAll(){
    if(!list.length)return;
    emit([],!0);
    fireNote("Pile vidée.")}

  /* préréglages : des VIGNETTES, pas des noms — c'est là que le choix se fait
     à l'œil (chaîne de repli identique à celle du panneau). */
  function presetRow(f,i,d){
    if((d.params||[]).indexOf("preset")<0)return null;
    var pr=d.presets||vfxBounds(d,"preset").choices||null;
    if(!pr||!pr.length)return null;
    var cur=f.preset||(f.type==="grade"?"teal_orange":f.type==="colorize"?"duotone":pr[0]);
    return r.jsxs("div",{className:"vfx-pgroup",children:[
      r.jsx("span",{className:"vfx-plabel",children:"Préréglage"}),
      r.jsx("div",{className:"vfx-pgrid",children:pr.map(function(p){
        var pe=Object.assign({},f,{preset:p});
        return r.jsxs("button",{className:"vfx-ptile","data-on":p===cur?"":void 0,
          title:"Préréglage « "+p+" »",
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
          title:"Nom d'un fichier .cube déposé dans le dossier LUT",
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
          title:"Déplier les réglages de « "+d.label+" »",
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
              title:"Actif de "+vfxSec(f.t0)+" à "+vfxSec(f.t1)+" — "+vfxSummary(f,d),
              children:vfxSec(f.t0)+" → "+vfxSec(f.t1)})
            :r.jsx("span",{className:"vfx-msum",children:vfxSummary(f,d)})]}),
          r.jsx("span",{className:"vfx-mcaret","aria-hidden":!0,children:open?"▾":"▸"})]}),
        r.jsx("button",{className:"vfx-iconbtn",disabled:i===0,
          title:"Monter dans la pile","aria-label":"Monter « "+d.label+" »",
          onClick:function(){moveAt(i,-1)},children:"▲"}),
        r.jsx("button",{className:"vfx-iconbtn",disabled:i===list.length-1,
          title:"Descendre dans la pile","aria-label":"Descendre « "+d.label+" »",
          onClick:function(){moveAt(i,1)},children:"▼"}),
        r.jsx("button",{className:"vfx-iconbtn vfx-bypass","data-on":off?"":void 0,
          role:"switch","aria-checked":off,
          title:off?"Réactiver — l'effet repart au rendu"
            :"Contourner — l'effet reste dans la pile mais sort du rendu",
          "aria-label":(off?"Réactiver ":"Contourner ")+d.label,
          onClick:function(){bypassAt(i)},children:off?"◌":"◉"}),
        r.jsx("button",{className:"vfx-iconbtn vfx-del",
          title:"Retirer de la pile","aria-label":"Retirer « "+d.label+" »",
          onClick:function(){removeAt(i)},children:"✕"})]}),
      open?r.jsxs("div",{className:"vfx-mbody",children:[
        d.hint?r.jsx("div",{className:"vfx-mhint",children:d.hint}):null,
        presetRow(f,i,d),
        (d.params||[]).map(function(k){return paramRow(f,i,d,k)}),
        (d.params||[]).length?null:r.jsx("div",{className:"vfx-mhint",
          children:"Cet effet n'a aucun réglage — il s'applique tel quel."}),
        r.jsx(VfxBounds,{eff:f,dur:dur,
          onChange:function(patch){patchAt(i,patch)}})]}):null]},f.type+"#"+i)}

  return r.jsxs("div",{className:"vfx-stack",children:[
    r.jsxs("div",{className:"vfx-shead",children:[
      r.jsx("span",{className:"vfx-title",children:props.title||"Pile d'effets"}),
      r.jsx("span",{className:"vfx-count",
        children:list.length?String(list.length):"vide"}),
      r.jsxs("div",{className:"vfx-ab",role:"group",
        "aria-label":"Comparer avant / après",children:[
        r.jsx("button",{className:"vfx-abbtn","data-on":!anyOn?"":void 0,
          disabled:!list.length,
          title:"Avant — toute la pile est contournée",
          onClick:function(){if(anyOn)abToggle()},children:"avant"}),
        r.jsx("button",{className:"vfx-abbtn","data-on":anyOn?"":void 0,
          disabled:!list.length,
          title:"Après — la pile est appliquée",
          onClick:function(){if(!anyOn)abToggle()},children:"après"})]}),
      r.jsx("button",{className:"vfx-btn",disabled:!list.length,
        title:"Retirer tous les effets de ce clip (annulable)",
        onClick:clearAll,children:"Vider"}),
      props.onOpenPanel?r.jsx("button",{className:"vfx-btn vfx-add",
        title:"Ouvrir le panneau d'effets",
        onClick:function(){props.onOpenPanel()},children:"+ effet"}):null]}),
    r.jsx(VfxAlert,{}),
    list.length?r.jsx("div",{className:"vfx-mods",children:list.map(row)})
    :r.jsxs("div",{className:"vfx-empty",children:[
      r.jsx("div",{className:"vfx-emptytxt",children:"Aucun effet sur ce plan."}),
      r.jsx("div",{className:"vfx-emptyhint",
        children:"Ouvrez le panneau d'effets, ou glissez une vignette sur le clip."})]}),
    note?r.jsx("div",{className:"vfx-note",role:"status","aria-live":"polite",
      children:note}):null]})};

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
