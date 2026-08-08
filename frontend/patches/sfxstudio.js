/* ── SFX Studio — couche window.DzSfx (gauntlet SFX R1) ─────────────────────
   Injecté dans frontend/dist/assets/index-*.js juste APRÈS le bloc sonvfx,
   MÊME scope module : les alias du bundle (r.jsx / r.jsxs, x.useState…) et
   les helpers sonvfx (svmSharedAC, svmWavePeaks, SVM_WAVES, svmSrcKey,
   svmShort, svmAudioDur, svmUseNote, SvmLabel) sont accessibles directement.
   Styles : /shared/sfxstudio.css (préfixe .svx-, scopé .dzsvm, thème clair
   via .dzsvm[data-svm-theme="light"]).

   Exporte (contrat gauntlet) :
     window.DzSfx = { ready, Drawer, Rack, Meter, genSfx, fxPresets }
   - Drawer({open,onClose,onInsert,playheadSec,defaultTab}) — tiroir Sons :
     bibliothèque (onglets par type + compteurs réels, favoris ★ persistés
     localStorage dz_sfx_favs + onglet ★ + tri favoris d'abord (R2/C1),
     recherche, tri, préécoute waveform, insertion playhead + drag "dz-audio",
     import, suppression confirmée inline) + onglet Générer (ElevenLabs SFX,
     téléchargement par carte + coût réel après génération — R2/C2).
   - Rack({fx,onChange,clip,onAudition}) — rack d'effets par clip audio,
     vocabulaire ffmpeg partagé, audition live Web Audio dans le composant.
   - Meter({level,engaged,lufs,lufsM,onMeasure,busy}) — métrologie maître
     graduée −48..0 dBFS, crête tenue, LED clip, LUFS mesurés + LUFS
     momentané « M » temps réel si fourni (R2/C3, tolérant null).
   Aucune écoute globale sans cleanup ; un seul flux audio à la fois
   (bus interne svxClaim, partagé préécoute / rack / cartes générées). */

/* ── helpers ─────────────────────────────────────────────────────────────── */
function svxClamp(v,a,b){v=Number(v);if(!isFinite(v))v=a;return v<a?a:v>b?b:v}
function svxN(v,d){var n=Number(v);return isFinite(n)?n:d}
function svxRound(v,dec){var m=Math.pow(10,dec||0);return Math.round(v*m)/m}
/* dB affiché : "−18.4" (signe moins typographique, ∞ sous −96) */
function svxDb1(db){
  if(db==null||!isFinite(db)||db<=-96)return "−∞";
  var v=svxRound(db,1),s=v<0?"−":v>0?"+":"";
  return s+Math.abs(v).toFixed(1)}
/* niveau reçu : linéaire 0..N (analyser) OU déjà en dBFS (négatif) */
function svxToDb(v){
  if(v==null)return -99;
  v=Number(v);if(!isFinite(v))return -99;
  if(v<0)return v;                       /* déjà des dBFS */
  if(v<=0.0000158)return -99;            /* < −96 dB */
  return 20*Math.log(v)/Math.LN10}
function svxKo(kb){kb=svxN(kb,0);return kb>=1024?(Math.round(kb/102.4)/10)+" Mo":kb+" Ko"}
function svxWaveEntry(src){
  var e=SVM_WAVES.get(svmSrcKey(src));
  return e&&e.st==="ok"?e:null}

/* catégories de la bibliothèque — couleur = type de média, jamais un état */
var SVX_KINDS={
  sfx:{tag:"SFX",label:"Effet sonore",c:"--c-3d",track:"a3"},
  voix:{tag:"VOIX",label:"Voix",c:"--c-audio",track:"a1"},
  musique:{tag:"MUS",label:"Musique",c:"--c-av",track:"a2"},
  import:{tag:"IMP",label:"Importé",c:"--c-text",track:"a3"}};
function svxKindOf(name,metaMap){
  var m=metaMap&&metaMap[name];
  if(m&&m.kind){var k=String(m.kind).toLowerCase();
    if(k==="sfx")return "sfx";
    if(k==="voix"||k==="voice"||k==="voiceover"||k==="vo")return "voix";
    if(k==="musique"||k==="music"||k==="bgm")return "musique";
    if(k==="import"||k==="imported")return "import"}
  var n=String(name||"").toLowerCase();
  if(/^sfx[_-]/.test(n))return "sfx";
  if(/^vo_|_narr-|^narration|voice|voix/.test(n))return "voix";
  if(/music|musique|bgm|theme|soundtrack|_loop/.test(n))return "musique";
  return "import"}
function svxTrackOf(kind){return (SVX_KINDS[kind]||SVX_KINDS.import).track}

/* ── favoris — localStorage dz_sfx_favs, tableau de filenames (R2/C1) ────── */
function svxFavsLoad(){
  try{
    var arr=JSON.parse(localStorage.getItem("dz_sfx_favs")||"[]"),m={};
    if(Array.isArray(arr))arr.forEach(function(n){if(typeof n==="string")m[n]=1});
    return m}
  catch(_e){return {}}}
function svxFavsSave(m){
  try{localStorage.setItem("dz_sfx_favs",JSON.stringify(Object.keys(m)))}catch(_e){}}

/* ── bus de lecture partagé : une seule source audible à la fois ─────────── */
var SVX_PLAY={cur:null};
function svxClaim(stop){
  if(SVX_PLAY.cur&&SVX_PLAY.cur!==stop){try{SVX_PLAY.cur()}catch(_e){}}
  SVX_PLAY.cur=stop}
function svxRelease(stop){if(SVX_PLAY.cur===stop)SVX_PLAY.cur=null}

/* ── cache AudioBuffer par URL (audition du rack) ────────────────────────── */
var SVX_BUFS=new Map();
function svxBuf(url,cb){
  var e=SVX_BUFS.get(url);
  if(!e){e={st:"pend",buf:null,subs:[]};SVX_BUFS.set(url,e);
    var fin=function(ok,b){e.st=ok?"ok":"err";e.buf=b||null;
      var s=e.subs;e.subs=[];s.forEach(function(f){try{f()}catch(_e){}})};
    fetch(url).then(function(res){if(!res.ok)throw 0;return res.arrayBuffer()})
      .then(function(ab){var ctx=svmSharedAC();if(!ctx)throw 0;
        return ctx.decodeAudioData(ab)})
      .then(function(b){fin(!0,b)})
      .catch(function(){fin(!1)})}
  if(cb&&e.st==="pend")e.subs.push(cb);
  return e}

/* ── vocabulaire FX (contrat backend/frontend — noms et bornes EXACTS) ────
   Ordre de chaîne fixe : filter → eq3 → denoise → deesser → compressor →
   distortion → echo → reverb → stereo → normalize. live:1 = audible dans
   l'audition Web Audio du rack ; live:0 = « Écouter (rendu) » (ffmpeg). */
var SVX_FX_DEFS=[
 {type:"filter",label:"Filtre",live:1,params:[
   {k:"mode",kind:"seg",opts:[["low","grave"],["high","aigu"],["band","bande"]],d:"low"},
   {k:"freq",label:"Fréq",min:20,max:20000,d:1000,step:1,unit:"Hz",log:1},
   {k:"q",label:"Q",min:0.1,max:10,d:1,step:0.1,unit:""}]},
 {type:"eq3",label:"Égaliseur",live:1,params:[
   {k:"bass_db",label:"Graves",min:-12,max:12,d:0,step:0.5,unit:"dB"},
   {k:"mid_db",label:"Médiums",min:-12,max:12,d:0,step:0.5,unit:"dB"},
   {k:"treble_db",label:"Aigus",min:-12,max:12,d:0,step:0.5,unit:"dB"}]},
 {type:"denoise",label:"Débruiteur",live:0,params:[
   {k:"amount",label:"Réduction",min:0,max:97,d:12,step:1,unit:"dB"}]},
 {type:"deesser",label:"Dé-esseur",live:0,params:[
   {k:"intensity",label:"Intensité",min:0,max:100,d:50,step:1,unit:"%"}]},
 {type:"compressor",label:"Compresseur",live:1,params:[
   {k:"threshold_db",label:"Seuil",min:-60,max:0,d:-20,step:1,unit:"dB"},
   {k:"ratio",label:"Ratio",min:1,max:20,d:4,step:0.5,unit:":1"},
   {k:"attack_ms",label:"Attaque",min:1,max:500,d:50,step:1,unit:"ms"},
   {k:"release_ms",label:"Relâche",min:10,max:2000,d:250,step:5,unit:"ms"}]},
 {type:"distortion",label:"Distorsion",live:1,params:[
   {k:"drive",label:"Drive",min:0,max:100,d:20,step:1,unit:"%"}]},
 {type:"echo",label:"Écho",live:1,params:[
   {k:"time_ms",label:"Temps",min:20,max:1500,d:300,step:5,unit:"ms"},
   {k:"feedback",label:"Répét.",min:0,max:90,d:30,step:1,unit:"%"},
   {k:"mix",label:"Mix",min:0,max:100,d:30,step:1,unit:"%"}]},
 {type:"reverb",label:"Réverbe",live:1,params:[
   {k:"mix",label:"Mix",min:0,max:100,d:30,step:1,unit:"%"},
   {k:"decay_s",label:"Décrois.",min:0.2,max:8,d:2,step:0.1,unit:"s"}]},
 {type:"stereo",label:"Stéréo",live:1,params:[
   {k:"pan",label:"Pan",min:-100,max:100,d:0,step:1,unit:""},
   {k:"width",label:"Largeur",min:0,max:200,d:100,step:1,unit:"%"}]},
 {type:"normalize",label:"Normaliser",live:0,params:[
   {k:"target_lufs",label:"Cible",min:-30,max:-10,d:-16,step:1,unit:"LUFS"}]}];
var SVX_FX_BY={};
SVX_FX_DEFS.forEach(function(d){SVX_FX_BY[d.type]=d});
function svxFxDefaults(type){
  var def=SVX_FX_BY[type],p={};
  if(!def)return p;
  def.params.forEach(function(pd){p[pd.k]=pd.d});
  return p}
/* params nettoyés, clés dans l'ordre du vocabulaire → JSON stable (égalité) */
function svxCleanParams(type,raw){
  var def=SVX_FX_BY[type],p={};
  if(!def)return p;
  raw=raw||{};
  def.params.forEach(function(pd){
    if(pd.kind==="seg"){
      var v=String(raw[pd.k]!=null?raw[pd.k]:pd.d),ok=!1;
      pd.opts.forEach(function(o){if(o[0]===v)ok=!0});
      p[pd.k]=ok?v:pd.d}
    else{
      var n=svxClamp(svxN(raw[pd.k],pd.d),pd.min,pd.max);
      p[pd.k]=svxRound(n,pd.step<1?1:0)}});
  return p}
function svxNormFx(list){
  var on={},unknown=[];
  (Array.isArray(list)?list:[]).forEach(function(en){
    if(!en||typeof en.type!=="string")return;
    if(SVX_FX_BY[en.type]){if(!on[en.type])on[en.type]=svxCleanParams(en.type,en.params)}
    else unknown.push(en)});
  return {on:on,unknown:unknown}}
function svxEmitFx(on,unknown){
  var out=[];
  SVX_FX_DEFS.forEach(function(d){
    if(on[d.type])out.push({type:d.type,params:Object.assign({},on[d.type])})});
  return unknown&&unknown.length?out.concat(unknown):out}
function svxFxSig(on){
  try{return JSON.stringify(svxEmitFx(on,[]))}catch(_e){return ""}}
/* résumé d'un module replié — mono, valeurs clés seulement */
function svxModSummary(def,p){
  if(!p)return "";
  switch(def.type){
    case "filter":{var mm={low:"grave",high:"aigu",band:"bande"};
      return (mm[p.mode]||p.mode)+" "+Math.round(p.freq)+" Hz"}
    case "eq3":return svxDb1(p.bass_db).replace(".0","")+" / "+svxDb1(p.mid_db).replace(".0","")+" / "+svxDb1(p.treble_db).replace(".0","");
    case "denoise":return p.amount+" dB";
    case "deesser":return p.intensity+" %";
    case "compressor":return svxDb1(p.threshold_db).replace(".0","")+" dB · "+p.ratio+":1";
    case "distortion":return p.drive+" %";
    case "echo":return p.time_ms+" ms · "+p.mix+" %";
    case "reverb":return p.mix+" % · "+p.decay_s+" s";
    case "stereo":return (p.pan===0?"centre":(p.pan>0?"D +":"G −")+Math.abs(p.pan))+" · "+p.width+" %";
    case "normalize":return p.target_lufs+" LUFS";
    default:return ""}}

/* ── presets français (contrat : ids exacts) — appliqués = remplacent la
   chaîne entière ; params dans l'ordre de chaîne ─────────────────────────── */
var svxFxPresets=[
 {id:"radio",label:"Radio",fx:[
   {type:"filter",params:{mode:"band",freq:1800,q:1.4}},
   {type:"compressor",params:{threshold_db:-24,ratio:6,attack_ms:5,release_ms:120}},
   {type:"distortion",params:{drive:14}}]},
 {id:"telephone",label:"Téléphone",fx:[
   {type:"filter",params:{mode:"band",freq:1700,q:2.2}},
   {type:"compressor",params:{threshold_db:-20,ratio:8,attack_ms:3,release_ms:90}},
   {type:"distortion",params:{drive:8}}]},
 {id:"caverne",label:"Caverne",fx:[
   {type:"eq3",params:{bass_db:2,mid_db:0,treble_db:-3}},
   {type:"echo",params:{time_ms:210,feedback:35,mix:22}},
   {type:"reverb",params:{mix:55,decay_s:3.5}}]},
 {id:"sous_leau",label:"Sous l'eau",fx:[
   {type:"filter",params:{mode:"low",freq:420,q:0.8}},
   {type:"eq3",params:{bass_db:3,mid_db:-2,treble_db:-9}},
   {type:"reverb",params:{mix:35,decay_s:2.6}}]},
 {id:"punchy",label:"Punchy",fx:[
   {type:"eq3",params:{bass_db:3,mid_db:0,treble_db:2}},
   {type:"compressor",params:{threshold_db:-18,ratio:8,attack_ms:8,release_ms:140}},
   {type:"distortion",params:{drive:10}}]},
 {id:"voix_nette",label:"Voix nette",fx:[
   {type:"filter",params:{mode:"high",freq:85,q:0.7}},
   {type:"eq3",params:{bass_db:0,mid_db:2,treble_db:1}},
   {type:"denoise",params:{amount:12}},
   {type:"deesser",params:{intensity:55}},
   {type:"compressor",params:{threshold_db:-22,ratio:3,attack_ms:15,release_ms:200}},
   {type:"normalize",params:{target_lufs:-16}}]}];

/* ── POST /api/audio/sfx — génération ElevenLabs ─────────────────────────── */
function svxGenSfx(o){
  o=o||{};
  var body={prompt:String(o.prompt||"").slice(0,450)};
  if(o.duration_s!=null)body.duration_s=svxClamp(o.duration_s,0.5,22);
  if(o.prompt_influence!=null)body.prompt_influence=svxClamp(o.prompt_influence,0,1);
  body.variations=Math.round(svxClamp(o.variations!=null?o.variations:1,1,4));
  return fetch("/api/audio/sfx",{method:"POST",
    headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
    .then(function(res){return res.json().catch(function(){return {}})
      .then(function(d){return {ok:res.ok,status:res.status,d:d}})})
    .then(function(o2){
      if(!o2.ok)throw new Error((o2.d&&(o2.d.detail||o2.d.error))||("génération refusée (HTTP "+o2.status+")"));
      var items=(o2.d&&o2.d.items||[]).map(function(it){
        var fn=it.filename||it.name||"";
        return {name:it.name||fn,filename:fn,
          url:it.url||("/api/audio/"+encodeURIComponent(fn)),
          dur:svxN(it.dur,0)}});
      return {items:items}})}

/* ── SvxWave — mini-waveform canvas (pics svmWavePeaks) + progression or ──
   prog 0..1 = portion jouée (barres repeintes --accent : la lecture est un
   ÉTAT) ; onReady est appelé quand les pics / la durée arrivent. */
const SvxWave=(props)=>{
  var cv=x.useRef(null),st=x.useState(0),tick=st[0],setTick=st[1];
  var onReady=props.onReady;
  x.useEffect(function(){
    var alive=!0,c=cv.current;
    var e=svmWavePeaks(props.src,function(){
      if(!alive)return;
      setTick(function(t){return t+1});
      if(onReady)try{onReady()}catch(_e){}});
    if(!c)return function(){alive=!1};
    var g=c.getContext("2d");
    if(!g)return function(){alive=!1};
    var w=c.clientWidth,h=c.clientHeight;
    if(!w||!h)return function(){alive=!1};
    var dpr=Math.min(2,window.devicePixelRatio||1),
        W=Math.max(1,Math.round(w*dpr)),H=Math.max(1,Math.round(h*dpr));
    if(c.width!==W)c.width=W;
    if(c.height!==H)c.height=H;
    g.clearRect(0,0,W,H);
    var cs=getComputedStyle(c),
        col=(cs.getPropertyValue(props.color||"--c-audio")||"").trim()||"#7fb069",
        acc=(cs.getPropertyValue("--accent")||"").trim()||"#f0b429";
    var bw=Math.max(1,Math.round(1.5*dpr)),gap=Math.max(1,Math.round(dpr)),
        n=Math.max(1,Math.floor(W/(bw+gap)));
    if(!e){ /* pics pas encore décodés : ligne médiane fantôme */
      g.fillStyle=col;g.globalAlpha=.25;
      g.fillRect(0,Math.round(H/2)-dpr,W,Math.max(1,Math.round(dpr*1.5)));
      g.globalAlpha=1;
      return function(){alive=!1}}
    var pk=e.peaks,pl=pk.length,
        played=props.prog!=null?Math.round(svxClamp(props.prog,0,1)*n):-1;
    for(var i=0;i<n;i++){
      var p0=Math.floor(i/n*pl),
          p1=Math.min(pl,Math.max(p0+1,Math.ceil((i+1)/n*pl))),v=0;
      for(var j2=p0;j2<p1;j2++){if(pk[j2]>v)v=pk[j2]}
      var bh=Math.max(dpr,v*H*.92);
      g.fillStyle=i<played?acc:col;
      g.globalAlpha=i<played?.95:.55;
      g.fillRect(i*(bw+gap),(H-bh)/2,bw,bh)}
    g.globalAlpha=1;
    return function(){alive=!1}},
    [props.k,props.color,props.prog,props.theme,tick]);
  return r.jsx("canvas",{className:"svx-wave","aria-hidden":!0,
    style:props.h?{height:props.h}:void 0,ref:cv})};

/* ── exemples de prompts SFX (cliquables, onglet Générer) ────────────────── */
var SVX_EXAMPLES=["verre brisé","vent dans une grotte","clic d'interface",
  "pas sur du gravier","porte qui grince au ralenti","explosion sourde et lointaine"];
var SVX_TABS=[["tous","Tous"],["fav","★"],["sfx","SFX"],["voix","Voix"],
  ["musique","Musique"],["import","Importés"]];

/* ═════════════════ Tiroir « Sons » — bibliothèque + Générer ═════════════ */
const SvxDrawer=(props)=>{
  var open=!!props.open;
  var s1=x.useState(null),lib=s1[0],setLib=s1[1];          /* null = chargement */
  var s2=x.useState(null),meta=s2[0],setMeta=s2[1];
  var s3=x.useState(null),tabSel=s3[0],setTabSel=s3[1];
  var s4=x.useState(""),query=s4[0],setQuery=s4[1];
  var s5=x.useState("recent"),sort=s5[0],setSort=s5[1];
  var s6=x.useState(null),prev=s6[0],setPrev=s6[1];        /* {name,pos,dur} */
  var s7=x.useState(null),confirmDel=s7[0],setConfirmDel=s7[1];
  var s8=x.useState(!1),upBusy=s8[0],setUpBusy=s8[1];
  var s9=x.useState(0),durTick=s9[0],setDurTick=s9[1];
  var s10=x.useState(!1),fileOver=s10[0],setFileOver=s10[1];
  var s11=x.useState(svxFavsLoad),favs=s11[0],setFavs=s11[1];  /* {filename:1} */
  /* onglet Générer — l'état vit ici : changer d'onglet ne perd rien */
  var g1=x.useState(""),gPrompt=g1[0],setGPrompt=g1[1];
  var g2=x.useState(!0),gAuto=g2[0],setGAuto=g2[1];
  var g3=x.useState(3),gDur=g3[0],setGDur=g3[1];
  var g4=x.useState(1),gVar=g4[0],setGVar=g4[1];
  var g5=x.useState(30),gInf=g5[0],setGInf=g5[1];
  var g6=x.useState(!1),gBusy=g6[0],setGBusy=g6[1];
  var g7=x.useState([]),gRes=g7[0],setGRes=g7[1];
  var g8=x.useState(null),renaming=g8[0],setRenaming=g8[1]; /* {name,val} */
  var g9=x.useState(null),gCost=g9[0],setGCost=g9[1];       /* coût réel dernière génération */
  var nt=svmUseNote(),note=nt[0],fireNote=nt[1];
  var rootRef=x.useRef(null),searchRef=x.useRef(null),fileRef=x.useRef(null),
      audRef=x.useRef(null),lastPrevRef=x.useRef(null),ghostRef=x.useRef(null),
      stopRef=x.useRef(null);
  if(!stopRef.current)stopRef.current=function(){
    var a=audRef.current;
    if(a){try{a.pause()}catch(_e){}a.ontimeupdate=null;a.onended=null;audRef.current=null}
    setPrev(null)};

  var tab=tabSel!=null?tabSel:
    (props.defaultTab==="generer"||props.defaultTab==="gen"?"gen":(props.defaultTab||"tous"));

  function refresh(){
    fetch("/api/audio").then(function(res){return res.json()})
      .then(function(d){setLib({items:d&&d.audio||[]})})
      .catch(function(){setLib(function(p){return p||{items:[],err:!0}})});
    fetch("/api/audio/meta").then(function(res){return res.ok?res.json():{}})
      .then(function(d){setMeta(d&&d.meta||{})})
      .catch(function(){setMeta(function(p){return p||{}})})}
  x.useEffect(function(){if(open)refresh()},[open]);
  x.useEffect(function(){if(open&&props.defaultTab)setTabSel(null)},[open]);
  x.useEffect(function(){
    if(open&&rootRef.current)try{rootRef.current.focus({preventScroll:!0})}catch(_e){}},[open]);
  x.useEffect(function(){if(!open){stopRef.current();svxRelease(stopRef.current)}},[open]);
  x.useEffect(function(){return function(){
    stopRef.current();svxRelease(stopRef.current);
    var g=ghostRef.current;
    if(g&&g.parentNode)g.parentNode.removeChild(g)}},[]);
  /* persistance des favoris — point d'écriture unique (updaters purs) */
  x.useEffect(function(){svxFavsSave(favs)},[favs]);

  var waveTick=x.useCallback(function(){setDurTick(function(t){return t+1})},[]);

  /* items classés — kind via meta sidecar puis heuristique de nommage */
  var all=x.useMemo(function(){
    return (lib&&lib.items||[]).map(function(a,i){
      var m=meta&&meta[a.name],e=svxWaveEntry({audio:a.name});
      return {name:a.name,url:a.url,kind:svxKindOf(a.name,meta),
        dur:e?e.dur:0,size_kb:a.size_kb,
        prompt:m&&m.prompt?String(m.prompt):void 0,
        created:m&&m.created?String(m.created):"",idx:i}})},
    [lib,meta,durTick]);
  var qn=query.trim().toLowerCase();
  var searched=x.useMemo(function(){
    if(!qn)return all;
    return all.filter(function(it){
      return it.name.toLowerCase().indexOf(qn)>=0||
        (it.prompt&&it.prompt.toLowerCase().indexOf(qn)>=0)})},[all,qn]);
  var counts=x.useMemo(function(){
    var c={tous:searched.length,fav:0,sfx:0,voix:0,musique:0,import:0};
    searched.forEach(function(it){c[it.kind]++;if(favs[it.name])c.fav++});
    return c},[searched,favs]);
  var shown=x.useMemo(function(){
    var rows=tab==="tous"||tab==="gen"?searched.slice()
      :tab==="fav"?searched.filter(function(it){return !!favs[it.name]})
      :searched.filter(function(it){return it.kind===tab});
    if(sort==="nom")rows.sort(function(a,b){return a.name.localeCompare(b.name,"fr")});
    else if(sort==="duree")rows.sort(function(a,b){
      return (a.dur||1e9)-(b.dur||1e9)||a.idx-b.idx});
    else if(sort==="fav")rows.sort(function(a,b){
      return (favs[b.name]?1:0)-(favs[a.name]?1:0)||a.idx-b.idx});
    return rows},[searched,tab,sort,favs]);
  var history=x.useMemo(function(){
    return all.filter(function(it){return it.kind==="sfx"&&it.prompt})
      .sort(function(a,b){return String(b.created).localeCompare(String(a.created))})
      .slice(0,6)},[all]);

  /* préécoute — un seul lecteur, progression sur la mini-waveform */
  function prevToggle(item){
    if(!item)return;
    if(prev&&prev.name===item.name){stopRef.current();svxRelease(stopRef.current);return}
    stopRef.current();
    svxClaim(stopRef.current);
    var a=new Audio(item.url);audRef.current=a;lastPrevRef.current=item;
    setPrev({name:item.name,pos:0,dur:item.dur||0});
    a.ontimeupdate=function(){
      setPrev(function(p){return p&&p.name===item.name
        ?{name:item.name,pos:a.currentTime,
          dur:isFinite(a.duration)&&a.duration>0?a.duration:p.dur}:p})};
    a.onended=function(){stopRef.current();svxRelease(stopRef.current)};
    a.play().catch(function(){stopRef.current();svxRelease(stopRef.current);
      fireNote("Lecture bloquée par le navigateur — cliquez d'abord dans la page.")})}

  function doInsert(item,mode){
    if(!props.onInsert||!item)return;
    props.onInsert({name:item.name,url:item.url,kind:item.kind,
      dur:item.dur||0,prompt:item.prompt},
      {track:svxTrackOf(item.kind),mode:mode||"playhead"})}

  /* favoris — toggle pur, l'effet [favs] persiste dans localStorage */
  function favToggle(name){
    setFavs(function(m){
      var nm=Object.assign({},m);
      if(nm[name])delete nm[name];else nm[name]=1;
      return nm})}
  /* étoile — révélée au survol/focus, TOUJOURS visible quand favori (état=or) */
  function favBtn(it){
    var on=!!favs[it.name];
    return r.jsx("button",{className:"svx-ifav","data-on":on?"":void 0,
      tabIndex:-1,"aria-pressed":on,
      title:on?"Retirer des favoris (F)":"Ajouter aux favoris (F)",
      "aria-label":(on?"Retirer des favoris : ":"Ajouter aux favoris : ")+it.name,
      onClick:function(e){e.stopPropagation();favToggle(it.name)},
      children:on?"★":"☆"})}

  function delGo(item){
    setConfirmDel(null);
    fetch("/api/audio/"+encodeURIComponent(item.name),{method:"DELETE"})
      .then(function(res){return res.json().catch(function(){return {}})
        .then(function(d){return {ok:res.ok,d:d}})})
      .then(function(o){
        if(!o.ok)throw new Error((o.d&&o.d.detail)||"suppression refusée");
        if(prev&&prev.name===item.name){stopRef.current();svxRelease(stopRef.current)}
        setGRes(function(rs){return rs.filter(function(g){return g.name!==item.name})});
        setFavs(function(m){
          if(!m[item.name])return m;
          var nm=Object.assign({},m);delete nm[item.name];return nm});
        refresh();fireNote("« "+item.name+" » supprimé.")})
      .catch(function(e){fireNote("Suppression : "+String(e&&e.message||e))})}

  function upFiles(files){
    var fs=Array.prototype.slice.call(files||[]).filter(function(f){return f&&f.name});
    if(!fs.length)return;
    setUpBusy(!0);
    var done=0,fail=[];
    (function next(i){
      if(i>=fs.length){
        setUpBusy(!1);refresh();
        fireNote(fail.length
          ?("Import : "+done+" ok · "+fail.length+" échec — "+fail[0])
          :(done+" fichier"+(done>1?"s":"")+" importé"+(done>1?"s":"")+"."));
        return}
      var fd=new FormData();fd.append("file",fs[i]);
      fetch("/api/audio/upload",{method:"POST",body:fd})
        .then(function(res){return res.json().catch(function(){return {}})
          .then(function(d){return {ok:res.ok,d:d}})})
        .then(function(o){if(o.ok)done++;else fail.push((o.d&&o.d.detail)||fs[i].name);next(i+1)})
        .catch(function(){fail.push(fs[i].name);next(i+1)})})(0)}

  /* drag natif — payload "dz-audio" du contrat + ghost lisible */
  function dragStart(e,item){
    try{
      e.dataTransfer.setData("dz-audio",JSON.stringify({name:item.name,url:item.url,
        kind:item.kind,dur:item.dur||0,prompt:item.prompt}));
      e.dataTransfer.effectAllowed="copy";
      var g=document.createElement("div");
      g.textContent="♪ "+item.name+(item.dur?" · "+svmShort(item.dur):"");
      g.setAttribute("style","position:fixed;top:-200px;left:-200px;z-index:9999;"+
        "padding:6px 10px;border-radius:8px;background:#1c1c21;color:#f2efe9;"+
        "border:1px solid #3d3b45;font:11px 'JetBrains Mono',Consolas,monospace;"+
        "box-shadow:0 8px 20px rgba(0,0,0,.5);max-width:240px;white-space:nowrap;"+
        "overflow:hidden;text-overflow:ellipsis;pointer-events:none");
      document.body.appendChild(g);ghostRef.current=g;
      e.dataTransfer.setDragImage(g,14,14)}catch(_e){}}
  function dragEnd(){
    var g=ghostRef.current;
    if(g&&g.parentNode)g.parentNode.removeChild(g);
    ghostRef.current=null}

  /* dépôt de fichiers OS → import direct */
  function isFileDrag(e){
    var ts=e.dataTransfer&&e.dataTransfer.types;
    return !!ts&&Array.prototype.indexOf.call(ts,"Files")>=0}

  function rowItem(el){
    var n=el&&el.closest?el.closest("[data-svx-item]"):null;
    if(!n)return null;
    var nm=n.getAttribute("data-svx-item");
    for(var i=0;i<shown.length;i++){if(shown[i].name===nm)return shown[i]}
    for(var j2=0;j2<gRes.length;j2++){if(gRes[j2].name===nm)return gRes[j2]}
    return null}

  /* clavier — TOUT passe par le tiroir (aucune écoute document) */
  function onKey(e){
    var t=e.target,tag=(t&&t.tagName||"").toLowerCase();
    var inField=tag==="input"||tag==="textarea"||tag==="select";
    if(e.key==="Escape"){
      if(confirmDel){setConfirmDel(null);e.preventDefault();return}
      if(renaming){setRenaming(null);e.preventDefault();return}
      if(inField&&t===searchRef.current&&query){setQuery("");e.preventDefault();return}
      if(props.onClose){props.onClose();e.preventDefault()}
      return}
    if(inField){
      if(t===searchRef.current&&e.key==="Enter"){
        var first=rootRef.current&&rootRef.current.querySelector("[data-svx-item]");
        if(first){first.focus();e.preventDefault()}}
      return}
    /* un vrai <button> focalisé garde son Espace / Entrée natifs */
    if(tag==="button"&&(e.key===" "||e.key==="Enter"))return;
    if(e.key==="/"){
      if(searchRef.current){searchRef.current.focus();e.preventDefault();e.stopPropagation()}
      return}
    if(e.key==="b"||e.key==="B"){
      if(props.onClose){props.onClose();e.preventDefault();e.stopPropagation()}
      return}
    if(e.key==="f"||e.key==="F"){
      /* même repli que Espace : rangée focalisée sinon dernier son préécouté.
         TOUJOURS consommé tiroir ouvert — sinon le F global (plein écran) se déclenche. */
      e.preventDefault();e.stopPropagation();
      var itf=rowItem(t)||lastPrevRef.current;
      if(itf)favToggle(itf.name);
      return}
    if(e.key===" "){
      e.preventDefault();e.stopPropagation();
      prevToggle(rowItem(t)||lastPrevRef.current);
      return}
    if(e.key==="Enter"){
      var it=rowItem(t);
      if(it){doInsert(it,"playhead");e.preventDefault();e.stopPropagation()}
      return}
    if(e.key==="Delete"||e.key==="Backspace"){
      var it3=rowItem(t);
      if(it3){setConfirmDel(it3.name);e.preventDefault();e.stopPropagation()}
      return}
    if(e.key==="ArrowDown"||e.key==="ArrowUp"){
      var rows=rootRef.current
        ?Array.prototype.slice.call(rootRef.current.querySelectorAll("[data-svx-item]")):[];
      if(!rows.length)return;
      var i=rows.indexOf(document.activeElement),ni;
      if(e.key==="ArrowDown")ni=i<0?0:Math.min(rows.length-1,i+1);
      else ni=i<0?rows.length-1:Math.max(0,i-1);
      rows[ni].focus();e.preventDefault();e.stopPropagation()}}

  /* génération SFX */
  function genGo(){
    var p=gPrompt.trim();
    if(!p||gBusy)return;
    setGBusy(!0);
    svxGenSfx({prompt:p,duration_s:gAuto?null:gDur,
      prompt_influence:gInf/100,variations:gVar})
      .then(function(d){
        setGBusy(!1);
        /* nom canonique = filename (les rangées et {audio:...} le réutilisent) */
        var its=(d.items||[]).map(function(it){
          return {name:it.filename||it.name,filename:it.filename,url:it.url,
            dur:it.dur,kind:"sfx",prompt:p}});
        setGRes(function(rs){return its.concat(rs).slice(0,24)});
        /* coût réel estimé : 40 crédits × durée générée, sommé sur les variations */
        var real=0;
        its.forEach(function(gi){real+=40*svxN(gi.dur,0)});
        setGCost(real>0?Math.round(real):null);
        refresh();
        fireNote(its.length+" variation"+(its.length>1?"s":"")+" générée"+
          (its.length>1?"s":"")+" — cartes ci-dessous, insérables ou déplaçables.")})
      .catch(function(e){setGBusy(!1);fireNote(String(e&&e.message||e))})}

  function renameGo(item){
    var ext=((item.name.match(/\.[a-z0-9]+$/i)||[".mp3"])[0]).toLowerCase();
    var nb=String(renaming&&renaming.val||"").trim()
      .replace(/[^\w.-]+/g,"_").replace(/^_+|_+$/g,"").slice(0,60);
    if(!nb){fireNote("Nom vide — renommage annulé.");setRenaming(null);return}
    var nn=nb.toLowerCase().slice(-ext.length)===ext?nb:nb+ext;
    if(nn===item.name){setRenaming(null);return}
    fetch(item.url).then(function(res){if(!res.ok)throw new Error("source introuvable");return res.blob()})
      .then(function(bl){
        var fd=new FormData();
        fd.append("file",new File([bl],nn,{type:bl.type||"audio/mpeg"}));
        return fetch("/api/audio/upload",{method:"POST",body:fd})})
      .then(function(res){
        if(!res.ok)return res.json().catch(function(){return {}})
          .then(function(d){throw new Error(d.detail||"import refusé")});
        return fetch("/api/audio/"+encodeURIComponent(item.name),{method:"DELETE"})})
      .then(function(){
        setGRes(function(rs){return rs.map(function(g){
          return g.name===item.name
            ?Object.assign({},g,{name:nn,filename:nn,url:"/api/audio/"+encodeURIComponent(nn)})
            :g})});
        /* le favori suit le renommage */
        setFavs(function(m){
          if(!m[item.name])return m;
          var nm=Object.assign({},m);delete nm[item.name];nm[nn]=1;return nm});
        setRenaming(null);refresh();fireNote("Renommé en « "+nn+" ».")})
      .catch(function(e){fireNote("Renommage : "+String(e&&e.message||e))})}

  /* ── rendus ── */
  function itemRow(it){
    var playing=prev&&prev.name===it.name;
    if(confirmDel===it.name)
      return r.jsxs("div",{className:"svx-item svx-confirm",role:"alert",children:[
        r.jsxs("span",{className:"svx-conftxt",children:[
          "Supprimer « ",r.jsx("b",{children:it.name})," » ?"]}),
        r.jsx("button",{className:"svx-abtn svx-dangerfill",
          onClick:function(){delGo(it)},children:"Supprimer"}),
        r.jsx("button",{className:"svx-abtn",autoFocus:!0,
          onClick:function(){setConfirmDel(null)},children:"Annuler"})]},it.name+"::c");
    return r.jsxs("div",{className:"svx-item",tabIndex:0,role:"button",
      "data-svx-item":it.name,"data-play":playing?"":void 0,
      draggable:!0,
      onDragStart:function(e){dragStart(e,it)},onDragEnd:dragEnd,
      onClick:function(e){if(!e.defaultPrevented)prevToggle(it)},
      title:"Clic / Espace : préécoute · glisser vers une piste A · Entrée : insérer",
      "aria-label":SVX_KINDS[it.kind].label+" "+it.name,
      children:[
      r.jsx("button",{className:"svm-playbtn svx-iplay",tabIndex:-1,
        "data-on":playing?"":void 0,
        "aria-label":(playing?"Arrêter ":"Écouter ")+it.name,
        onClick:function(e){e.stopPropagation();prevToggle(it)},
        children:playing?"▮▮":"▶"}),
      r.jsxs("div",{className:"svx-ibody",children:[
        r.jsxs("div",{className:"svx-irow1",children:[
          r.jsx("span",{className:"svx-iname",children:it.name}),
          favBtn(it),
          r.jsx("span",{className:"svx-ibadge","data-k":it.kind,
            title:SVX_KINDS[it.kind].label,children:SVX_KINDS[it.kind].tag}),
          r.jsx("span",{className:"svx-idur svm-mono",
            children:it.dur?svmShort(it.dur):svxKo(it.size_kb)})]}),
        r.jsx(SvxWave,{src:{audio:it.name},color:SVX_KINDS[it.kind].c,
          prog:playing&&prev.dur?prev.pos/prev.dur:null,onReady:waveTick,k:it.name}),
        it.prompt?r.jsx("div",{className:"svx-iprompt",title:it.prompt,
          children:it.prompt}):null]}),
      r.jsxs("div",{className:"svx-iact",children:[
        props.onInsert?r.jsx("button",{className:"svx-abtn",tabIndex:-1,
          title:"Insérer au playhead ("+svmShort(svxN(props.playheadSec,0))+
            ") — piste "+svxTrackOf(it.kind).toUpperCase(),
          onClick:function(e){e.stopPropagation();doInsert(it,"playhead")},
          children:"⤵"}):null,
        r.jsx("button",{className:"svx-abtn svx-danger",tabIndex:-1,
          title:"Supprimer de la bibliothèque",
          onClick:function(e){e.stopPropagation();setConfirmDel(it.name)},
          children:"✕"})]})]},it.name)}

  function emptyState(){
    if(lib===null)
      return r.jsxs("div",{className:"svx-skel",children:[
        r.jsx("div",{className:"svx-skelrow"}),
        r.jsx("div",{className:"svx-skelrow"}),
        r.jsx("div",{className:"svx-skelrow"})]});
    if(lib.err&&!(lib.items&&lib.items.length))
      return r.jsxs("div",{className:"svx-empty",children:[
        r.jsx("div",{className:"svx-emptytxt",
          children:"Bibliothèque injoignable — le backend ne répond pas."}),
        r.jsx("button",{className:"svm-secbtn",onClick:refresh,
          children:"Réessayer"})]});
    if(qn)
      return r.jsxs("div",{className:"svx-empty",children:[
        r.jsxs("div",{className:"svx-emptytxt",children:["Aucun résultat pour « ",qn," »."]}),
        r.jsx("button",{className:"svm-secbtn",onClick:function(){setQuery("")},
          children:"Effacer la recherche"})]});
    if(tab==="fav")
      return r.jsxs("div",{className:"svx-empty",children:[
        r.jsx("div",{className:"svx-emptytxt",children:"Aucun favori pour l'instant."}),
        r.jsx("div",{className:"svx-emptyhint",
          children:"Survolez un son et cliquez ★ (ou touche F) pour l'épingler ici."})]});
    var msg=tab==="voix"?"Aucune voix — narrez un bloc (tiroir Narration, T) ou importez une prise."
      :tab==="musique"?"Aucune musique — importez un fichier : il se posera sur la piste A2."
      :tab==="sfx"?"Aucun effet sonore pour l'instant."
      :"Votre bibliothèque de sons est vide.";
    return r.jsxs("div",{className:"svx-empty",children:[
      r.jsx("div",{className:"svx-emptytxt",children:msg}),
      r.jsxs("div",{className:"svx-emptyrow",children:[
        r.jsx("button",{className:"svm-secbtn",
          onClick:function(){if(fileRef.current)fileRef.current.click()},
          children:"Importer un son"}),
        r.jsx("button",{className:"svm-goldbtn",
          onClick:function(){setTabSel("gen")},children:"Générer un SFX"})]}),
      r.jsx("div",{className:"svx-emptyhint",
        children:"Vous pouvez aussi déposer des fichiers audio ici."})]})}

  function genCard(it){
    var playing=prev&&prev.name===it.name;
    var ren=renaming&&renaming.name===it.name;
    if(confirmDel===it.name)return itemRow(it);
    return r.jsxs("div",{className:"svx-gcard","data-svx-item":it.name,tabIndex:0,
      role:"button","data-play":playing?"":void 0,draggable:!0,
      onDragStart:function(e){dragStart(e,it)},onDragEnd:dragEnd,
      onClick:function(e){if(!e.defaultPrevented&&!ren)prevToggle(it)},
      title:"Clic / Espace : préécoute · glisser vers une piste A",
      children:[
      r.jsxs("div",{className:"svx-irow1",children:[
        r.jsx("button",{className:"svm-playbtn svx-iplay",tabIndex:-1,
          "data-on":playing?"":void 0,"aria-label":(playing?"Arrêter ":"Écouter ")+it.name,
          onClick:function(e){e.stopPropagation();prevToggle(it)},
          children:playing?"▮▮":"▶"}),
        ren?r.jsx("input",{className:"svx-rename svm-mono",autoFocus:!0,
          value:renaming.val,
          onClick:function(e){e.stopPropagation()},
          onChange:function(e){setRenaming({name:it.name,val:e.target.value})},
          onKeyDown:function(e){
            if(e.key==="Enter"){e.preventDefault();e.stopPropagation();renameGo(it)}
            else if(e.key==="Escape"){e.preventDefault();e.stopPropagation();setRenaming(null)}
            else e.stopPropagation()},
          "aria-label":"Nouveau nom"})
        :r.jsx("span",{className:"svx-iname",children:it.name}),
        ren?null:favBtn(it),
        r.jsx("span",{className:"svx-idur svm-mono",
          children:it.dur?svmShort(it.dur):""})]}),
      r.jsx(SvxWave,{src:{audio:it.name},color:"--c-3d",h:30,
        prog:playing&&prev.dur?prev.pos/prev.dur:null,onReady:waveTick,k:it.name}),
      r.jsxs("div",{className:"svx-gactions",children:[
        props.onInsert?r.jsx("button",{className:"svx-abtn",
          title:"Insérer au playhead — piste A3 (SFX)",
          onClick:function(e){e.stopPropagation();doInsert(it,"playhead")},
          children:"Insérer"}):null,
        r.jsx("a",{className:"svx-abtn svx-dl",href:it.url,download:it.name,
          draggable:!1,title:"Télécharger « "+it.name+" »",
          onClick:function(e){e.stopPropagation()},
          children:"Télécharger"}),
        ren?r.jsx("button",{className:"svx-abtn",
          onClick:function(e){e.stopPropagation();renameGo(it)},children:"Valider"})
        :r.jsx("button",{className:"svx-abtn",
          onClick:function(e){e.stopPropagation();
            setRenaming({name:it.name,val:it.name.replace(/\.[a-z0-9]+$/i,"")})},
          children:"Renommer"}),
        r.jsx("button",{className:"svx-abtn svx-danger",
          onClick:function(e){e.stopPropagation();setConfirmDel(it.name)},
          children:"Supprimer"})]})]},it.name)}

  function genPanel(){
    var cost=gAuto?null:Math.round(40*gDur)*gVar;
    return r.jsxs("div",{className:"svx-gen",children:[
      r.jsx(SvmLabel,{children:"Décrire le son"}),
      r.jsx("textarea",{className:"svx-gprompt",rows:3,value:gPrompt,
        placeholder:"« verre brisé sur du carrelage », « vent dans une grotte »…",
        maxLength:450,"aria-label":"Description du son à générer",
        onChange:function(e){setGPrompt(e.target.value)},
        onKeyDown:function(e){
          if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)){e.preventDefault();genGo()}}}),
      r.jsx("div",{className:"svx-gex",children:SVX_EXAMPLES.map(function(ex){
        return r.jsx("button",{className:"svx-gexchip",
          onClick:function(){setGPrompt(ex)},children:ex},ex)})}),
      r.jsxs("div",{className:"svx-grow",children:[
        r.jsx("span",{className:"svx-glabel",children:"Durée"}),
        r.jsx("button",{className:"svx-gsegbtn","data-on":gAuto?"":void 0,
          title:"ElevenLabs choisit la durée la plus naturelle",
          onClick:function(){setGAuto(!gAuto)},children:"auto"}),
        r.jsx("input",{className:"svx-gslider",type:"range",min:0.5,max:22,step:0.5,
          value:gDur,disabled:gAuto,"aria-label":"Durée (secondes)",
          onChange:function(e){setGDur(svxN(e.target.value,3));setGAuto(!1)}}),
        r.jsx("input",{className:"svx-gnum svm-mono",type:"number",min:0.5,max:22,
          step:0.1,value:gAuto?"":gDur,disabled:gAuto,placeholder:"—",
          "aria-label":"Durée précise (secondes)",
          onChange:function(e){
            var v=svxN(e.target.value,gDur);
            setGDur(svxClamp(v,0.5,22));setGAuto(!1)}}),
        r.jsx("span",{className:"svx-gunit",children:"s"})]}),
      r.jsxs("div",{className:"svx-grow",children:[
        r.jsx("span",{className:"svx-glabel",children:"Variations"}),
        r.jsx("div",{className:"svx-gseg",role:"radiogroup",
          "aria-label":"Nombre de variations",children:[1,2,3,4].map(function(n){
          return r.jsx("button",{className:"svx-gsegbtn",role:"radio",
            "aria-checked":gVar===n,"data-on":gVar===n?"":void 0,
            onClick:function(){setGVar(n)},children:String(n)},n)})})]}),
      r.jsxs("div",{className:"svx-grow",children:[
        r.jsx("span",{className:"svx-glabel",children:"Fidélité"}),
        r.jsx("input",{className:"svx-gslider",type:"range",min:0,max:100,step:5,
          value:gInf,"aria-label":"Fidélité au texte (prompt influence)",
          title:"Haut : colle au texte · bas : plus créatif (30 % par défaut)",
          onChange:function(e){setGInf(svxN(e.target.value,30))}}),
        r.jsx("span",{className:"svx-gval svm-mono",children:gInf+" %"})]}),
      r.jsxs("div",{className:"svx-gfoot",children:[
        r.jsx("span",{className:"svx-gcost svm-mono",
          title:"Estimation avant génération — ~40 crédits ElevenLabs par seconde et par variation",
          children:cost==null?"≈ 40 crédits/s · total selon durée générée":"≈ "+cost+" crédits"}),
        r.jsx("button",{className:"svm-goldbtn svx-gold","data-busy":gBusy?"":void 0,
          disabled:gBusy||!gPrompt.trim(),
          onClick:genGo,
          children:gBusy?r.jsxs(r.Fragment,{children:[
            r.jsx("span",{className:"svx-spin","aria-hidden":!0}),
            "Génération… (~10 s)"]}):"Générer"})]}),
      gRes.length?r.jsxs(r.Fragment,{children:[
        r.jsxs("div",{className:"svx-gresrow",children:[
          r.jsx(SvmLabel,{children:"Résultats"}),
          gCost!=null?r.jsx("span",{className:"svx-gcost svm-mono",
            title:"Coût réel estimé de la dernière génération — 40 crédits × durée générée × variations",
            children:"≈ "+gCost+" crédits utilisés"}):null]}),
        r.jsx("div",{className:"svx-gres",children:gRes.map(genCard)})]}):null,
      history.length?r.jsxs(r.Fragment,{children:[
        r.jsx(SvmLabel,{style:{margin:"16px 0 8px"},children:"Générations récentes"}),
        r.jsx("div",{className:"svx-ghist",children:history.map(function(h){
          return r.jsxs("button",{className:"svx-ghrow",
            title:"Reprendre ce prompt",
            onClick:function(){setGPrompt(h.prompt)},children:[
            r.jsx("span",{className:"svx-ghprompt",children:h.prompt}),
            r.jsx("span",{className:"svx-idur svm-mono",
              children:h.dur?svmShort(h.dur):""})]},h.name)})})]}):null]})}

  if(!open)return null;
  return r.jsxs("aside",{className:"svx-drawer",ref:rootRef,tabIndex:-1,
    onKeyDown:onKey,"aria-label":"Tiroir Sons",
    "data-fileover":fileOver?"":void 0,
    onDragOver:function(e){
      if(isFileDrag(e)){e.preventDefault();e.dataTransfer.dropEffect="copy";
        if(!fileOver)setFileOver(!0)}},
    onDragLeave:function(e){
      if(fileOver&&(!e.relatedTarget||!e.currentTarget.contains(e.relatedTarget)))
        setFileOver(!1)},
    onDrop:function(e){
      if(isFileDrag(e)){e.preventDefault();setFileOver(!1);
        upFiles(e.dataTransfer.files)}},
    children:[
    r.jsxs("div",{className:"svx-dhead",children:[
      r.jsx("span",{className:"svx-dtitle",children:"Sons"}),
      r.jsx("span",{className:"svx-dcount svm-mono",children:String(all.length)}),
      r.jsx("button",{className:"svx-iconbtn",title:"Rafraîchir la bibliothèque",
        "aria-label":"Rafraîchir",onClick:refresh,children:"⟳"}),
      r.jsx("button",{className:"svx-iconbtn","data-busy":upBusy?"":void 0,
        title:"Importer des fichiers audio (mp3, wav, m4a, ogg, flac…)",
        "aria-label":"Importer un son",
        onClick:function(){if(fileRef.current)fileRef.current.click()},
        children:upBusy?r.jsx("span",{className:"svx-spin","aria-hidden":!0}):"⤒"}),
      r.jsx("button",{className:"svx-iconbtn svx-dclose",title:"Fermer (B)",
        "aria-label":"Fermer le tiroir Sons",
        onClick:function(){if(props.onClose)props.onClose()},children:"✕"})]}),
    r.jsxs("div",{className:"svx-tabs",role:"tablist",children:[
      SVX_TABS.map(function(td){
        return r.jsxs("button",{className:"svx-tab",role:"tab",
          "aria-selected":tab===td[0],"data-on":tab===td[0]?"":void 0,
          title:td[0]==="fav"?"Favoris":void 0,
          "aria-label":td[0]==="fav"?"Favoris ("+counts.fav+")":void 0,
          onClick:function(){setTabSel(td[0])},children:[
          td[1],
          r.jsx("span",{className:"svx-tcount svm-mono",children:String(counts[td[0]])})]},td[0])}),
      r.jsx("span",{className:"svx-tsep","aria-hidden":!0}),
      r.jsx("button",{className:"svx-tab svx-tabgen",role:"tab",
        "aria-selected":tab==="gen","data-on":tab==="gen"?"":void 0,
        onClick:function(){setTabSel("gen")},children:"Générer"})]}),
    tab!=="gen"?r.jsxs("div",{className:"svx-filters",children:[
      r.jsxs("div",{className:"svx-search",children:[
        r.jsx("input",{className:"svx-searchin",ref:searchRef,type:"text",
          value:query,placeholder:"Rechercher (nom, prompt)…",
          "aria-label":"Rechercher un son",
          onChange:function(e){setQuery(e.target.value)}}),
        r.jsx("kbd",{className:"svx-kbd","aria-hidden":!0,children:"/"})]}),
      r.jsxs("select",{className:"svx-select",value:sort,
        "aria-label":"Trier la bibliothèque",title:"Tri",
        onChange:function(e){setSort(e.target.value)},children:[
        r.jsx("option",{value:"recent",children:"Récents"}),
        r.jsx("option",{value:"nom",children:"Nom"}),
        r.jsx("option",{value:"duree",children:"Durée"}),
        r.jsx("option",{value:"fav",children:"Favoris d'abord"})]})]}):null,
    r.jsx("div",{className:"svx-list",children:
      tab==="gen"?genPanel():(shown.length?shown.map(itemRow):emptyState())}),
    note?r.jsx("div",{className:"svx-note",role:"status","aria-live":"polite",
      children:note}):null,
    r.jsxs("div",{className:"svx-hints","aria-hidden":!0,children:[
      r.jsxs("span",{children:[r.jsx("kbd",{children:"Espace"})," préécoute"]}),
      r.jsxs("span",{children:[r.jsx("kbd",{children:"↑↓"})," naviguer"]}),
      r.jsxs("span",{children:[r.jsx("kbd",{children:"Entrée"})," insérer"]}),
      r.jsxs("span",{children:[r.jsx("kbd",{children:"F"})," favori"]}),
      r.jsxs("span",{children:[r.jsx("kbd",{children:"Suppr"})," supprimer"]}),
      r.jsxs("span",{children:[r.jsx("kbd",{children:"/"})," recherche"]}),
      r.jsxs("span",{children:[r.jsx("kbd",{children:"B"})," fermer"]})]}),
    r.jsx("input",{className:"svx-file",ref:fileRef,type:"file",
      accept:"audio/*,.mp3,.wav,.m4a,.aac,.ogg,.flac,.opus",multiple:!0,
      "aria-hidden":!0,tabIndex:-1,
      onChange:function(e){upFiles(e.target.files);e.target.value=""}})]})};

/* ═════════════════ Rack d'effets par clip (audition Web Audio) ══════════ */
function svxMakeIR(ctx,decay){
  var rate=ctx.sampleRate,secs=svxClamp(decay,0.2,8),
      n=Math.max(1,Math.floor(rate*secs)),
      buf=ctx.createBuffer(2,n,rate);
  for(var ch=0;ch<2;ch++){
    var d=buf.getChannelData(ch);
    for(var i=0;i<n;i++){d[i]=(Math.random()*2-1)*Math.pow(1-i/n,2.8)}}
  return buf}
function svxShaperCurve(drive){
  var k=1+svxClamp(drive,0,100)*0.32,n=1024,c=new Float32Array(n),
      den=Math.atan(k);
  for(var i=0;i<n;i++){var v=i/(n-1)*2-1;c[i]=Math.atan(k*v)/den}
  return c}

const SvxRack=(props)=>{
  var norm=svxNormFx(props.fx);
  var clip=props.clip||{};
  var e1=x.useState({}),expanded=e1[0],setExpanded=e1[1];
  var e2=x.useState(null),lastPreset=e2[0],setLastPreset=e2[1];
  var e3=x.useState(!1),playing=e3[0],setPlaying=e3[1];
  var e4=x.useState(!1),loading=e4[0],setLoading=e4[1];
  var e5=x.useState(!1),rBusy=e5[0],setRBusy=e5[1];
  var nt=svmUseNote(),note=nt[0],fireNote=nt[1];
  var engineRef=x.useRef(null),wantRef=x.useRef(!1),revSchedRef=x.useRef(null),
      lastParamsRef=x.useRef({}),fxRef=x.useRef(null),clipRef=x.useRef(null),
      stopImplRef=x.useRef(null),wrapRef=x.useRef(null);
  fxRef.current=norm.on;clipRef.current=clip;
  if(!wrapRef.current)wrapRef.current=function(){
    if(stopImplRef.current)stopImplRef.current()};

  var activeCount=0;
  SVX_FX_DEFS.forEach(function(d){if(norm.on[d.type])activeCount++});
  var nonLiveOn=SVX_FX_DEFS.filter(function(d){return !d.live&&norm.on[d.type]})
    .map(function(d){return d.label.toLowerCase()});
  var fxSig=svxFxSig(norm.on);
  var clipSig=[clip.url,clip.srcIn,clip.len,clip.gainDb,clip.speed].join("|");

  function emit(on){
    if(props.onChange)props.onChange(svxEmitFx(on,norm.unknown))}

  function setParam(type,k,v){
    var on=Object.assign({},fxRef.current),was=!!on[type];
    var p=Object.assign({},on[type]||lastParamsRef.current[type]||svxFxDefaults(type));
    p[k]=v;
    on[type]=svxCleanParams(type,p);
    emit(on);
    if(!was)setExpanded(function(m){var nm=Object.assign({},m);nm[type]=1;return nm});
    liveApply(on)}
  function toggleMod(type){
    var on=Object.assign({},fxRef.current);
    if(on[type]){lastParamsRef.current[type]=on[type];delete on[type]}
    else{on[type]=svxCleanParams(type,lastParamsRef.current[type]||svxFxDefaults(type));
      setExpanded(function(m){var nm=Object.assign({},m);nm[type]=1;return nm})}
    emit(on);
    liveApply(on)}
  function resetAll(){
    Object.keys(fxRef.current).forEach(function(t){
      lastParamsRef.current[t]=fxRef.current[t]});
    emit({});
    setLastPreset(null);
    liveApply({});
    fireNote("Chaîne d'effets réinitialisée.")}
  function applyPreset(p){
    var on={};
    p.fx.forEach(function(en){on[en.type]=svxCleanParams(en.type,en.params)});
    emit(on);
    setLastPreset(p.id);
    setExpanded(function(m){
      var nm=Object.assign({},m);
      p.fx.forEach(function(en){nm[en.type]=1});
      return nm});
    liveApply(on);
    fireNote("Preset « "+p.label+" » appliqué — la chaîne précédente est remplacée (annulable).")}
  function presetSig(p){
    var on={};
    p.fx.forEach(function(en){on[en.type]=svxCleanParams(en.type,en.params)});
    return svxFxSig(on)}

  /* ── moteur d'audition live ── */
  function engineStop(){
    var en=engineRef.current;
    if(en){
      try{en.src.stop()}catch(_e){}
      try{en.src.disconnect()}catch(_e){}
      en.nodes.forEach(function(n){try{n.disconnect()}catch(_e){}});
      engineRef.current=null}
    if(revSchedRef.current){clearTimeout(revSchedRef.current);revSchedRef.current=null}
    wantRef.current=!1;
    setLoading(!1);
    setPlaying(!1)}
  stopImplRef.current=engineStop;

  function segBounds(buf){
    var dur=buf.duration,s0=Math.max(0,svxN(clipRef.current.srcIn,0)),
        len=svxN(clipRef.current.len,0),
        s1=len>0?Math.min(dur,s0+len):dur;
    if(s1-s0<0.05){s0=0;s1=dur}
    return [s0,s1]}

  function liveApply(on){
    var en=engineRef.current;
    if(!en)return;
    var P=en.parts,ctx=en.ctx,t=ctx.currentTime,TC=0.02;
    function ramp(param,v){
      try{param.setTargetAtTime(v,t,TC)}
      catch(_e){try{param.value=v}catch(_e2){}}}
    var f=on.filter;
    if(f){
      var ft=f.mode==="high"?"highpass":f.mode==="band"?"bandpass":"lowpass";
      if(P.flt.type!==ft)P.flt.type=ft;
      ramp(P.flt.frequency,f.freq);ramp(P.flt.Q,f.q)}
    else{if(P.flt.type!=="peaking")P.flt.type="peaking";ramp(P.flt.gain,0)}
    var q3=on.eq3||{bass_db:0,mid_db:0,treble_db:0};
    ramp(P.bass.gain,q3.bass_db);ramp(P.mid.gain,q3.mid_db);ramp(P.treb.gain,q3.treble_db);
    var c=on.compressor;
    if(c){ramp(P.comp.threshold,c.threshold_db);ramp(P.comp.ratio,c.ratio);
      ramp(P.comp.knee,6);ramp(P.comp.attack,c.attack_ms/1000);
      ramp(P.comp.release,c.release_ms/1000)}
    else{ramp(P.comp.threshold,0);ramp(P.comp.ratio,1);ramp(P.comp.knee,0)}
    var dd=on.distortion;
    P.shp.curve=dd&&dd.drive>0?svxShaperCurve(dd.drive):null;
    var eo=on.echo;
    if(eo){ramp(P.dl.delayTime,eo.time_ms/1000);
      ramp(P.fb.gain,svxClamp(eo.feedback,0,90)/100);
      ramp(P.ewet.gain,eo.mix/100)}
    else{ramp(P.ewet.gain,0);ramp(P.fb.gain,0)}
    var rv=on.reverb;
    if(rv){
      ramp(P.rwet.gain,rv.mix/100);
      if(Math.abs((en.irDecay||0)-rv.decay_s)>0.03&&!revSchedRef.current){
        revSchedRef.current=setTimeout(function(){
          revSchedRef.current=null;
          var en2=engineRef.current,cur=fxRef.current.reverb;
          if(!en2||!cur)return;
          try{en2.parts.cv.buffer=svxMakeIR(en2.ctx,cur.decay_s);
            en2.irDecay=cur.decay_s}catch(_e){}},140)}}
    else ramp(P.rwet.gain,0);
    var sw=on.stereo,w=sw?svxClamp(sw.width,0,200)/100:1;
    ramp(P.sPos.gain,w);ramp(P.sNeg.gain,-w);
    if(P.pan)ramp(P.pan.pan,sw?svxClamp(sw.pan,-100,100)/100:0);
    ramp(P.out.gain,Math.pow(10,svxN(clipRef.current.gainDb,0)/20));
    ramp(en.src.playbackRate,svxClamp(svxN(clipRef.current.speed,1),0.5,2));
    try{
      var sb=segBounds(en.src.buffer);
      en.src.loopStart=sb[0];en.src.loopEnd=sb[1]}catch(_e){}}

  function startEngine(){
    wantRef.current=!1;
    setLoading(!1);
    var url=clipRef.current.url,e=url?SVX_BUFS.get(url):null;
    if(!e||e.st!=="ok"||!e.buf){
      fireNote("Décodage impossible (codec non lu par le navigateur).");return}
    engineStop();
    svxClaim(wrapRef.current);
    var ctx=svmSharedAC();
    if(!ctx)return;
    try{if(ctx.resume){var pr=ctx.resume();if(pr&&pr.catch)pr.catch(function(){})}}catch(_e){}
    var buf=e.buf,sb=segBounds(buf);
    var src=ctx.createBufferSource();
    src.buffer=buf;src.loop=!0;src.loopStart=sb[0];src.loopEnd=sb[1];
    var flt=ctx.createBiquadFilter();
    flt.type="peaking";flt.gain.value=0;flt.frequency.value=1000;
    try{flt.channelCount=2;flt.channelCountMode="explicit"}catch(_e){}
    var bass=ctx.createBiquadFilter();bass.type="lowshelf";bass.frequency.value=110;
    var mid=ctx.createBiquadFilter();mid.type="peaking";mid.frequency.value=1000;mid.Q.value=1;
    var treb=ctx.createBiquadFilter();treb.type="highshelf";treb.frequency.value=8000;
    var comp=ctx.createDynamicsCompressor();
    comp.threshold.value=0;comp.ratio.value=1;comp.knee.value=0;
    var shp=ctx.createWaveShaper();
    try{shp.oversample="2x"}catch(_e){}
    var dry=ctx.createGain();dry.gain.value=1;
    var sum=ctx.createGain();
    var dl=ctx.createDelay(2);var fb=ctx.createGain();fb.gain.value=0;
    var ewet=ctx.createGain();ewet.gain.value=0;
    var cv2=ctx.createConvolver();var rwet=ctx.createGain();rwet.gain.value=0;
    var spl=ctx.createChannelSplitter(2);
    var mg=ctx.createGain(),sg=ctx.createGain();
    var lm=ctx.createGain(),rm=ctx.createGain(),ls=ctx.createGain(),rs=ctx.createGain();
    lm.gain.value=0.5;rm.gain.value=0.5;ls.gain.value=0.5;rs.gain.value=-0.5;
    var sPos=ctx.createGain(),sNeg=ctx.createGain();
    sPos.gain.value=1;sNeg.gain.value=-1;
    var mrg=ctx.createChannelMerger(2);
    var pan=null;
    try{pan=ctx.createStereoPanner?ctx.createStereoPanner():null}catch(_e){}
    var out=ctx.createGain();
    src.connect(flt);flt.connect(bass);bass.connect(mid);mid.connect(treb);
    treb.connect(comp);comp.connect(shp);
    shp.connect(dry);dry.connect(sum);
    shp.connect(dl);dl.connect(fb);fb.connect(dl);dl.connect(ewet);ewet.connect(sum);
    shp.connect(cv2);cv2.connect(rwet);rwet.connect(sum);
    sum.connect(spl);
    spl.connect(lm,0);spl.connect(ls,0);
    spl.connect(rm,1);spl.connect(rs,1);
    lm.connect(mg);rm.connect(mg);ls.connect(sg);rs.connect(sg);
    mg.connect(mrg,0,0);mg.connect(mrg,0,1);
    sg.connect(sPos);sPos.connect(mrg,0,0);
    sg.connect(sNeg);sNeg.connect(mrg,0,1);
    if(pan){mrg.connect(pan);pan.connect(out)}else mrg.connect(out);
    out.connect(ctx.destination);
    engineRef.current={ctx:ctx,src:src,irDecay:0,
      parts:{flt:flt,bass:bass,mid:mid,treb:treb,comp:comp,shp:shp,dl:dl,fb:fb,
        ewet:ewet,cv:cv2,rwet:rwet,sPos:sPos,sNeg:sNeg,pan:pan,out:out},
      nodes:[flt,bass,mid,treb,comp,shp,dry,sum,dl,fb,ewet,cv2,rwet,spl,mg,sg,
        lm,rm,ls,rs,sPos,sNeg,mrg,pan,out].filter(Boolean)};
    var rv=fxRef.current.reverb;
    if(rv){try{cv2.buffer=svxMakeIR(ctx,rv.decay_s);
      engineRef.current.irDecay=rv.decay_s}catch(_e){}}
    liveApply(fxRef.current);
    try{src.start(0,sb[0])}catch(_e){engineStop();return}
    setPlaying(!0)}

  function listenToggle(){
    if(playing){engineStop();svxRelease(wrapRef.current);return}
    var url=clip.url;
    if(!url){fireNote("Pas de source audio sur ce clip.");return}
    if(!svmSharedAC()){fireNote("Web Audio indisponible dans ce navigateur.");return}
    var e=svxBuf(url,function(){if(wantRef.current)startEngine()});
    if(e.st==="ok"){wantRef.current=!0;startEngine()}
    else if(e.st==="err")fireNote("Décodage impossible (codec non lu par le navigateur).");
    else{wantRef.current=!0;setLoading(!0)}}

  function renderAudition(){
    if(!props.onAudition||rBusy)return;
    engineStop();svxRelease(wrapRef.current);
    var p=null;
    try{p=props.onAudition(svxEmitFx(fxRef.current,norm.unknown))}catch(_e){}
    if(p&&p.then){
      setRBusy(!0);
      p.then(function(){setRBusy(!1)},function(err){setRBusy(!1);
        if(err)fireNote(String(err&&err.message||err))})}}

  /* params mis à jour EN DIRECT pendant la lecture (graphe conservé) */
  x.useEffect(function(){if(engineRef.current)liveApply(fxRef.current)},[fxSig,clipSig]);
  /* source changée → on coupe (le prochain Écouter décode la nouvelle) */
  x.useEffect(function(){
    if(engineRef.current||wantRef.current){engineStop();svxRelease(wrapRef.current)}},
    [clip.url]);
  x.useEffect(function(){return function(){
    if(stopImplRef.current)stopImplRef.current();
    svxRelease(wrapRef.current)}},[]);

  function paramRow(def,pd,p,on){
    var v=p[pd.k];
    if(pd.kind==="seg")
      return r.jsxs("div",{className:"svx-prow",children:[
        r.jsx("span",{className:"svx-plabel",children:"Mode"}),
        r.jsx("div",{className:"svx-gseg",role:"radiogroup","aria-label":"Mode du filtre",
          children:pd.opts.map(function(o){
          return r.jsx("button",{className:"svx-gsegbtn",role:"radio",
            "aria-checked":v===o[0],"data-on":v===o[0]?"":void 0,
            onClick:function(){setParam(def.type,pd.k,o[0])},children:o[1]},o[0])})})]},pd.k);
    var sv,smin,smax,sstep;
    if(pd.log){smin=0;smax=1000;sstep=1;
      sv=Math.round(1000*Math.log(svxClamp(v,pd.min,pd.max)/pd.min)/Math.log(pd.max/pd.min))}
    else{smin=pd.min;smax=pd.max;sstep=pd.step;sv=v}
    var disp=pd.step<1?svxRound(v,1):Math.round(v);
    return r.jsxs("div",{className:"svx-prow","data-dim":on?void 0:"",children:[
      r.jsx("span",{className:"svx-plabel",children:pd.label}),
      r.jsx("input",{className:"svx-prange",type:"range",min:smin,max:smax,step:sstep,
        value:sv,"aria-label":def.label+" — "+pd.label,
        onChange:function(e){
          var nv=svxN(e.target.value,sv);
          if(pd.log)nv=pd.min*Math.pow(pd.max/pd.min,nv/1000);
          setParam(def.type,pd.k,svxClamp(nv,pd.min,pd.max))}}),
      r.jsx("input",{className:"svx-pval svm-mono",type:"number",
        min:pd.min,max:pd.max,step:pd.step,defaultValue:disp,
        "aria-label":def.label+" — "+pd.label+" (valeur)",
        onBlur:function(e){
          var nv=svxN(e.target.value,disp);
          if(nv!==disp)setParam(def.type,pd.k,svxClamp(nv,pd.min,pd.max))},
        onKeyDown:function(e){
          if(e.key==="Enter"){e.preventDefault();e.currentTarget.blur()}}},
        def.type+"."+pd.k+":"+disp),
      r.jsx("span",{className:"svx-punit",children:pd.unit})]},pd.k)}

  function moduleRow(def){
    var on=!!norm.on[def.type],exp=!!expanded[def.type],
        p=norm.on[def.type]||lastParamsRef.current[def.type]||svxFxDefaults(def.type);
    return r.jsxs("div",{className:"svx-mod","data-on":on?"":void 0,children:[
      r.jsxs("div",{className:"svx-mhead",role:"button",tabIndex:0,
        "aria-expanded":exp,
        onClick:function(){setExpanded(function(m){
          var nm=Object.assign({},m);
          if(nm[def.type])delete nm[def.type];else nm[def.type]=1;
          return nm})},
        onKeyDown:function(e){
          if(e.key==="Enter"||e.key===" "){e.preventDefault();e.currentTarget.click()}},
        children:[
        r.jsx("button",{className:"svx-sw",role:"switch","aria-checked":on,
          "data-on":on?"":void 0,
          title:(on?"Désactiver":"Activer")+" — "+def.label,
          "aria-label":(on?"Désactiver ":"Activer ")+def.label,
          onClick:function(e){e.stopPropagation();toggleMod(def.type)},
          children:r.jsx("i",{className:"svx-swk"})}),
        r.jsx("span",{className:"svx-mname",children:def.label}),
        r.jsx("span",{className:"svx-mtag","data-live":def.live?"":void 0,
          title:def.live?"Audible dans l'audition live Web Audio"
            :"Audible via « Écouter (rendu) » (ffmpeg) uniquement",
          children:def.live?"live":"rendu"}),
        on&&!exp?r.jsx("span",{className:"svx-msum svm-mono",
          children:svxModSummary(def,norm.on[def.type])}):null,
        r.jsx("span",{className:"svx-mcaret","aria-hidden":!0,children:exp?"▾":"▸"})]}),
      exp?r.jsx("div",{className:"svx-params",children:
        def.params.map(function(pd){return paramRow(def,pd,p,on)})}):null]},def.type)}

  return r.jsxs("div",{className:"svx-rack",children:[
    r.jsxs("div",{className:"svx-rhead",children:[
      r.jsx("span",{className:"svx-rcount svm-mono",
        children:activeCount?activeCount+" actif"+(activeCount>1?"s":""):"aucun effet"}),
      norm.unknown.length?r.jsx("span",{className:"svx-runk svm-mono",
        title:"Effets d'une version plus récente — conservés tels quels dans le rendu",
        children:"+"+norm.unknown.length+" inconnu"+(norm.unknown.length>1?"s":"")}):null,
      r.jsx("button",{className:"svx-rreset","data-off":activeCount?void 0:"",
        disabled:!activeCount,title:"Retirer tous les effets du clip (annulable)",
        onClick:resetAll,children:"Réinitialiser"})]}),
    r.jsx("div",{className:"svx-presets",children:svxFxPresets.map(function(p){
      var match=activeCount>0&&presetSig(p)===fxSig;
      var dirty=lastPreset===p.id&&!match&&activeCount>0;
      return r.jsxs("button",{className:"svx-preset","data-on":match?"":void 0,
        title:"Appliquer le preset « "+p.label+" » (remplace la chaîne)",
        onClick:function(){applyPreset(p)},children:[
        p.label,
        dirty?r.jsx("span",{className:"svx-dirty",title:"Preset modifié depuis l'application",
          children:"modifié"}):null]},p.id)})}),
    r.jsxs("div",{className:"svx-listenrow",children:[
      r.jsx("button",{className:"svx-listen","data-on":playing?"":void 0,
        title:playing?"Arrêter l'audition"
          :"Écouter le segment du clip en boucle, effets appliqués en direct (Web Audio) — fondus non simulés",
        onClick:listenToggle,
        children:loading?r.jsxs(r.Fragment,{children:[
            r.jsx("span",{className:"svx-spin","aria-hidden":!0}),"chargement…"]})
          :playing?"▮▮ Stop":"▶ Écouter"}),
      props.onAudition?r.jsx("button",{className:"svx-listen svx-listenr",
        "data-busy":rBusy?"":void 0,disabled:rBusy,
        title:"Rendu ffmpeg exact du segment avec la chaîne complète (débruiteur, dé-esseur, normalisation compris)",
        onClick:renderAudition,
        children:rBusy?r.jsxs(r.Fragment,{children:[
            r.jsx("span",{className:"svx-spin","aria-hidden":!0}),"rendu…"]})
          :"Écouter (rendu)"}):null,
      playing?r.jsx("span",{className:"svx-liveled","aria-hidden":!0}):null]}),
    nonLiveOn.length?r.jsx("div",{className:"svx-rnote",
      children:nonLiveOn.join(" · ")+" : au rendu uniquement — passez par « Écouter (rendu) »."}):null,
    r.jsx("div",{className:"svx-mods",children:SVX_FX_DEFS.map(moduleRow)}),
    note?r.jsx("div",{className:"svx-note",role:"status","aria-live":"polite",
      children:note}):null]})};

/* ═════════════════ Métrologie maître (barre −48..0 dBFS + LUFS) ═════════ */
var SVX_METER_MARKS=[-48,-36,-24,-18,-12,-6,0];
function svxMeterPct(db){return svxClamp((db+48)/48,0,1)*100}

const SvxMeter=(props)=>{
  var engaged=!!props.engaged;
  var m1=x.useState(!1),pin=m1[0],setPin=m1[1];
  var m2=x.useState(!1),hov=m2[0],setHov=m2[1];
  var m3=x.useState(!1),clipped=m3[0],setClipped=m3[1];
  var rootRef=x.useRef(null),holdRef=x.useRef({v:-99,at:0});
  var lv=props.level||{};
  var rdb=engaged?svxToDb(lv.rms):-99,
      pdb=engaged?svxToDb(lv.peak):-99;
  var now=Date.now();
  if(engaged){
    if(pdb>=holdRef.current.v||now-holdRef.current.at>1500)
      holdRef.current={v:pdb,at:now}}
  else holdRef.current={v:-99,at:0};
  var hold=holdRef.current.v;
  x.useEffect(function(){
    if(engaged&&(lv.clip||pdb>-0.05))setClipped(!0)},[engaged,lv.clip,pdb]);
  /* écoute document UNIQUEMENT quand le popover est figé — cleanup garanti */
  x.useEffect(function(){
    if(!pin)return;
    function onKeyD(e){if(e.key==="Escape")setPin(!1)}
    function onDoc(e){
      if(rootRef.current&&!rootRef.current.contains(e.target))setPin(!1)}
    document.addEventListener("keydown",onKeyD,!0);
    document.addEventListener("mousedown",onDoc,!0);
    return function(){
      document.removeEventListener("keydown",onKeyD,!0);
      document.removeEventListener("mousedown",onDoc,!0)}},[pin]);

  var zone=rdb>-3?"red":rdb>-12?"amber":"green";
  var open=pin||hov;
  var lufs=props.lufs&&isFinite(Number(props.lufs.i))?props.lufs:null;
  var dev=lufs?svxRound(Number(lufs.i)+14,1):null;
  /* LUFS momentané (R2/C3) — fourni par l'hôte (pondération K), null toléré */
  var lufsM=props.lufsM!=null&&isFinite(Number(props.lufsM))?Number(props.lufsM):null;

  function bar(big){
    return r.jsxs("div",{className:"svx-mbar","data-big":big?"":void 0,children:[
      r.jsx("div",{className:"svx-mzones","aria-hidden":!0}),
      SVX_METER_MARKS.map(function(mk){
        return r.jsx("i",{className:"svx-mtick",
          style:{left:svxMeterPct(mk)+"%"}},mk)}),
      r.jsx("i",{className:"svx-mtarget",style:{left:svxMeterPct(-14)+"%"},
        title:"Cible réseaux sociaux : −14 LUFS (mesurée via « Mesurer le mix »)"}),
      engaged?r.jsx("div",{className:"svx-mfill","data-z":zone,
        style:{width:svxMeterPct(rdb)+"%"}}):null,
      engaged&&hold>-96?r.jsx("i",{className:"svx-mpeak",
        style:{left:svxMeterPct(hold)+"%"}}):null]})}

  return r.jsxs("div",{className:"svx-meter",ref:rootRef,role:"group",
    "aria-label":"Niveau de sortie maître","data-idle":engaged?void 0:"",
    onMouseEnter:function(){setHov(!0)},onMouseLeave:function(){setHov(!1)},
    children:[
    r.jsx("button",{className:"svx-mled","data-on":clipped?"":void 0,
      title:clipped?"Saturation détectée (≥ 0 dBFS) — cliquer pour réinitialiser"
        :"Aucune saturation",
      "aria-label":clipped?"Saturation détectée — réinitialiser":"Aucune saturation",
      onClick:function(){setClipped(!1)}}),
    r.jsx("button",{className:"svx-mbarbtn","aria-expanded":open,
      title:engaged?"RMS "+svxDb1(rdb)+" · pic "+svxDb1(hold)+" dBFS — clic : détails"
        :"Au repos — lancez la lecture pour le niveau · clic : détails",
      onClick:function(){setPin(!pin)},
      children:bar(!1)}),
    r.jsxs("span",{className:"svx-mnums svm-mono","aria-live":"off",children:[
      r.jsx("span",{className:"svx-mnum",children:engaged?"RMS "+svxDb1(rdb):"RMS —"}),
      r.jsx("span",{className:"svx-mnum svx-mnump",children:engaged?"PIC "+svxDb1(hold):"PIC —"}),
      engaged&&lufsM!=null?r.jsx("span",{className:"svx-mnum svx-mnumm",
        title:"Loudness momentanée (fenêtre 400 ms, pondération K)",
        children:"M "+svxDb1(lufsM)+" LUFS"}):null]}),
    open?r.jsxs("div",{className:"svx-mpop",role:"dialog",
      "aria-label":"Détails du niveau de sortie",children:[
      r.jsxs("div",{className:"svx-mpophead",children:[
        r.jsx(SvmLabel,{children:"Sortie maître"}),
        pin?r.jsx("button",{className:"svx-iconbtn",title:"Fermer (Échap)",
          "aria-label":"Fermer les détails",
          onClick:function(){setPin(!1)},children:"✕"}):null]}),
      bar(!0),
      r.jsx("div",{className:"svx-mscale svm-mono","aria-hidden":!0,
        children:SVX_METER_MARKS.map(function(mk){
        return r.jsx("span",{style:{left:svxMeterPct(mk)+"%"},
          children:mk===0?"0":String(mk)},mk)})}),
      r.jsxs("div",{className:"svx-mreads svm-mono",children:[
        r.jsx("span",{children:engaged?"RMS "+svxDb1(rdb)+" dBFS":"RMS — (au repos)"}),
        r.jsx("span",{children:engaged?"PIC "+svxDb1(hold)+" dBFS":"PIC —"})]}),
      r.jsxs("div",{className:"svx-mlufs",children:[
        r.jsx(SvmLabel,{children:"Loudness du mix"}),
        lufsM!=null?r.jsxs("div",{className:"svx-lufsm svm-mono",
          title:"Loudness momentanée — temps réel pendant la lecture (fenêtre 400 ms, pondération K)",
          children:[
          r.jsx("span",{className:"svx-lufsmlbl",children:"momentané"}),
          r.jsx("span",{children:svxDb1(lufsM)+" LUFS"})]}):null,
        lufs?r.jsxs("div",{className:"svx-lufsrow svm-mono",children:[
          r.jsx("span",{title:"Loudness intégrée",children:"I "+svxDb1(Number(lufs.i))+" LUFS"}),
          r.jsx("span",{title:"Vrai pic",children:"TP "+svxDb1(Number(lufs.tp))+" dBTP"}),
          r.jsx("span",{title:"Plage de loudness",children:"LRA "+svxRound(Number(lufs.lra),1)}),
          r.jsx("span",{className:"svx-lufsdev","data-ok":Math.abs(dev)<=1?"":void 0,
            title:"Écart à la cible réseaux sociaux (−14 LUFS)",
            children:svxDb1(dev)+" dB vs cible"})]})
        :r.jsx("div",{className:"svx-lufsnone",
          children:"Pas encore mesuré — « Mesurer le mix » analyse le mix audio complet (ebur128, gratuit)."}),
        r.jsxs("div",{className:"svx-mpoprow",children:[
          r.jsx("span",{className:"svx-mtargetlbl svm-mono",children:"cible réseaux : −14 LUFS"}),
          props.onMeasure?r.jsx("button",{className:"svm-goldbtn svx-measure",
            disabled:!!props.busy,
            onClick:function(){props.onMeasure()},
            children:props.busy?r.jsxs(r.Fragment,{children:[
                r.jsx("span",{className:"svx-spin","aria-hidden":!0}),"mesure…"]})
              :"Mesurer le mix"}):null]})]}),
      r.jsx("div",{className:"svx-mhint",
        children:pin?"Échap ou clic dehors pour fermer":"clic sur la barre : figer le panneau"})]}):null]})};

/* ── export contrat ──────────────────────────────────────────────────────── */
window.DzSfx={ready:!0,Drawer:SvxDrawer,Rack:SvxRack,Meter:SvxMeter,
  genSfx:svxGenSfx,fxPresets:svxFxPresets};
