/* ── Son & VFX (06) + Montage (07) — design handoff « son_vfx_montage » v2.1 ──
   Injecté dans frontend/dist/assets/index-*.js par scripts/patch_bundle_sonvfx.py
   juste avant `const oa=` (la région du shell applicatif). Symboles du bundle :
     r = react/jsx-runtime (r.jsx / r.jsxs / r.Fragment)
     x = React (hooks)
   Styles : /shared/son-vfx-montage.css (tokens Cinema scopés, .dzsvm).
   Chaînes en français — la langue de l'app installée (v2.x) et de la maquette.

   Câblage réel :
   - Son & VFX : /api/voices (clonées en tête), /api/audio (dernier asset →
     vrais pics WebAudio + lecture).
   - Montage : /api/montage/project (timeline initiale depuis la Bibliothèque),
     /api/montage/render (preview 480p gratuit / rendu final → JobRecord,
     poll /api/jobs/{id}), aperçu joué dans le lecteur 9:16 synchronisé à la
     timeline, « Rendre & publier » → rendu final + brouillon Scheduler.
   Sans asset réel, l'écran garde la démo du handoff (« teaser_abyss ») et les
   actions restent des cibles produit explicites. */

/* ── helpers partagés ── */
function svmPad2(n){n=Math.floor(n);return (n<10?"0":"")+n}
function svmClock(s){var c=Math.round(s*100),m=Math.floor(c/6000),r2=c%6000;return svmPad2(m)+":"+svmPad2(Math.floor(r2/100))+"."+svmPad2(r2%100)}
function svmTc(s){var ms=Math.round(s*1000),m=Math.floor(ms/60000),r2=ms%60000;return svmPad2(m)+":"+svmPad2(Math.floor(r2/1000))+"."+String(r2%1000).padStart(3,"0")}
function svmShort(s){var d=Math.round(s*10),m=Math.floor(d/600),r2=d%600;return svmPad2(m)+":"+svmPad2(Math.floor(r2/10))+"."+(r2%10)}
/* timecode broadcast HH:MM:SS:FF à 30 i/s — transport (position / durée),
   chip du cadre, survol de la règle ; svmTc / svmShort restent pour les durées */
function svmTcFF(s){var f=Math.max(0,Math.round(s*30)),ff=f%30,t=(f-ff)/30,m=Math.floor(t/60);
  return svmPad2(m/60)+":"+svmPad2(m%60)+":"+svmPad2(t%60)+":"+svmPad2(ff)}
function svmRuler(s){var m=Math.floor(s/60);return m+":"+svmPad2(s-m*60)}
/* heure locale HH:MM:SS — badge « enregistré · … » de l'autosave */
function svmClockHMS(ts){var d=new Date(ts);
  return svmPad2(d.getHours())+":"+svmPad2(d.getMinutes())+":"+svmPad2(d.getSeconds())}
/* montant $ compact du coût narration — 2/3/4 décimales selon l'ordre de
   grandeur ($0.12 / $0.012 / $0.0043) ; jamais un « $0.0000 » trompeur */
function svmUsd(v){
  if(!(v>0))return "$0.00";
  if(v<.00005)return "<$0.0001";
  return "$"+v.toFixed(v>=.095?2:v>=.0095?3:4)}
/* vitesse numérique d'un clip (facteur > 0 posé sur le clip, défaut ×1) */
/* t117 : horodatage de la dernière rafale de réglage d'un fondu J1 (une entrée d'historique par 600 ms) */
var SVM_AJ_FADE_T=0;
function svmSpeedOf(c){return c&&typeof c.speed==="number"&&c.speed>0?c.speed:1}
function svmGetTheme(){try{return localStorage.getItem("dz_svm_theme")==="light"?"light":"dark"}catch(e){return "dark"}}
function svmUseTheme(){var st=x.useState(svmGetTheme()),theme=st[0],setT=st[1];function set(t){setT(t);try{localStorage.setItem("dz_svm_theme",t)}catch(e){}}return [theme,set]}
/* tiroir Narration : ouvert par défaut (choix mémorisé dz_narr_open) */
function svmNarrInit(){try{return localStorage.getItem("dz_narr_open")!=="0"}catch(e){return !0}}
/* durée réelle d'un audio (narration fraîchement synthétisée) — metadata
   seule ; échec / timeout → 0, la longueur du bloc est alors conservée */
function svmAudioDur(url){return new Promise(function(res){
  var a=new Audio(),done=!1,to=setTimeout(function(){fin(0)},8000);
  function fin(v){if(done)return;done=!0;clearTimeout(to);
    a.onloadedmetadata=null;a.onerror=null;res(v)}
  a.onloadedmetadata=function(){fin(isFinite(a.duration)?a.duration:0)};
  a.onerror=function(){fin(0)};
  try{a.src=url}catch(_e){fin(0)}})}
function SvmThemeChip(props){return r.jsx("button",{className:"svm-themechip",title:dzT("son.theme.apercu_aide"),onClick:function(){props.setTheme(props.theme==="dark"?"light":"dark")},children:[__dzGl("dz-action-theme")," ",props.theme==="dark"?dzT("son.theme.clair"):dzT("son.theme.sombre")]})}
function svmBars(csv){return csv.split(",").map(Number)}
function SvmLabel(props){return r.jsx("div",{className:"svm-label",style:props.style,children:props.children})}
/* normalisation de recherche (cheatsheet) — minuscules sans accents */
function svmNorm(s){s=String(s||"").toLowerCase();
  try{s=s.normalize("NFD").replace(/[\u0300-\u036f]/g,"")}catch(_e){}
  return s}

/* ligne d'information transitoire (4,5 s) */
function svmUseNote(){var st=x.useState(""),note=st[0],setN=st[1],ref=x.useRef(null);
  var fire=x.useCallback(function(msg){setN(msg);if(ref.current)clearTimeout(ref.current);ref.current=setTimeout(function(){setN("")},4500)},[]);
  x.useEffect(function(){return function(){if(ref.current)clearTimeout(ref.current)}},[]);
  return [note,fire]}

/* ── couche SFX optionnelle (sfxstudio.js → window.DzSfx) — feature-detect
   STRICT : couche absente, chaque point d'intégration retombe sur l'UI
   d'avant, à l'octet près. Tout accès passe par ce helper, jamais en direct. */
function svmSfx(){var d=window.DzSfx;return d&&d.ready?d:null}
/* piste cible d'un item du tiroir Sons (voix→A1, musique→A2, sfx/import→A3) */
function svmSfxTrackOf(kind){return kind==="voix"?"a1":kind==="musique"?"a2":"a3"}
/* nom de fichier backend d'un item du tiroir (item.url = /api/audio/<fn>) */
function svmSfxFileOf(item){
  if(!item)return "";
  if(item.filename)return String(item.filename);
  var u=String(item.url||""),i=u.lastIndexOf("/");
  var fn=(i>=0?u.slice(i+1):u).split("?")[0];
  try{return decodeURIComponent(fn)}catch(_e){return fn}}
/* hôte du métering DzSfx.Meter (barre transport du Montage) — isole les mises
   à jour par frame : il relit la ref partagée (rms/peak/clip, écrits par la
   boucle vu-mètre existante) dans SA propre boucle rAF et ne re-rend que le
   Meter — jamais l'éditeur entier. */
function SvmMeterHost(props){
  var st=x.useState({rms:0,peak:0,clip:!1,lufsM:null}),lvl=st[0],setLvl=st[1];
  x.useEffect(function(){
    if(!props.engaged){setLvl({rms:0,peak:0,clip:!1,lufsM:null});return}
    var raf=0;
    var tick=function(){
      raf=requestAnimationFrame(tick);
      var v=props.srcRef.current;
      if(v)setLvl(function(o){
        var lm=v.lufsM==null?null:v.lufsM;
        return o.rms===v.rms&&o.peak===v.peak&&o.clip===v.clip&&o.lufsM===lm?o
          :{rms:v.rms,peak:v.peak,clip:v.clip,lufsM:lm}})};
    raf=requestAnimationFrame(tick);
    return function(){if(raf)cancelAnimationFrame(raf)}},[props.engaged]);
  var d=svmSfx();
  if(!d||!d.Meter)return null;
  /* lufsM : LUFS momentané K-weighted (fenêtre 400 ms) calculé par la boucle
     vu-mètre — null hors lecture, le Meter n'affiche alors rien */
  return r.jsx(d.Meter,{level:lvl,engaged:props.engaged,lufs:props.lufs,
    lufsM:lvl.lufsM,onMeasure:props.onMeasure,busy:props.busy})}

/* ── données de design (relevées dans le DOM de référence — projet « teaser_abyss ») ── */
var SVM_EDITOR_PEAKS=svmBars("18,43,62,70,66,53,37,23,21,20,25,36,45,45,36,19,42,63,77,79,69,50,27,28,40,42,36,25,20,23,19,32,50,65,72,68,52,28,33,54,66,66,56,41,26,19,19,25,36,46,49,42,26,33,56,73,80,74,57,36");
var SVM_SFX=[
 {id:"impact_grave",name:"impact_grave",dur:"0:01.2",bars:svmBars("58,36,80,88,54,40,82,86,50,44,84,85,47,48,85,83,43,52,87,82")},
 {id:"vague_lente",name:"vague_lente",dur:"0:03.4",bars:svmBars("90,69,22,72,90,66,26,74,89,62,30,77,89,59,35,79,88,56,38,81")},
 {id:"bulles",name:"bulles",dur:"0:02.1",bars:svmBars("40,55,88,80,36,58,89,78,32,61,89,75,28,65,90,73,23,68,90,70")},
 {id:"glitch_ui",name:"glitch_ui",dur:"0:00.4",bars:svmBars("49,46,85,84,45,49,86,83,41,53,87,81,37,57,88,79,33,60,89,76")},
 {id:"nappe_abysse",name:"nappe_abysse",dur:"0:08.0",bars:svmBars("58,36,80,88,54,40,82,86,50,44,84,85,47,48,85,83,43,52,87,82")}];
var SVM_VFX=[
 {id:"explosion",name:"Explosion",type:"sprite · 24 f",kind:"sprite"},
 {id:"smoke",name:dzT("son.demo_vfx.fumee"),type:dzT("son.demo_vfx.boucle"),kind:"sprite"},
 {id:"goldburst",name:dzT("son.demo_vfx.eclat"),type:"sprite · 12 f",kind:"sprite"},
 {id:"grain",name:dzT("son.demo_vfx.grain"),type:"post · overlay",kind:"post"},
 {id:"bloom",name:"Glow bloom",type:"post · shader",kind:"post"},
 {id:"glitchrgb",name:"Glitch RGB",type:"post · transition",kind:"post"}];
/* Le prix affiché est celui de CE QUE FAIT le bouton. « VFX particules » est
   passé de « $0.06 » à « gratuit » parce que la génération est désormais une
   simulation locale, et « SFX » à « gratuit » parce que 606 bruitages CC0 sont
   livrés : la facturation ElevenLabs ne concerne plus que la génération sur
   description. Un tarif qui survit au câblage est un mensonge d'interface. */
var SVM_GENS=[
 {id:"music",name:dzT("son.gen.musique"),desc:dzT("son.gen.musique_desc"),price:"~$0.10",c:"--c-audio"},
 {id:"sfx",name:"SFX",desc:dzT("son.gen.sfx_desc"),price:dzT("son.commun.gratuit"),c:"--c-audio"},
 {id:"voiceover",name:dzT("son.gen.voix_off"),desc:dzT("son.gen.voix_off_desc"),price:"$0.08",c:"--c-audio"},
 {id:"vfx",name:dzT("son.gen.vfx"),desc:dzT("son.gen.vfx_desc"),price:dzT("son.commun.gratuit"),c:"--c-3d"},
 {id:"post",name:dzT("son.gen.post"),desc:"Grain, glow, aberration, transitions",price:dzT("son.commun.gratuit"),c:"--c-3d"}];
/* onglet porté par chaque générateur : UNE sélection, deux affichages */
var SVM_GEN_TAB={music:"audio",sfx:"audio",voiceover:"audio",vfx:"vfx",post:"post"};
var SVM_DEMO_VOICES=[
 {id:"prophet",name:dzT("son.demo_voix.prophet"),meta:dzT("son.demo_voix.meta_prophet"),cloned:!0},
 {id:"tide",name:"Tide",meta:dzT("son.demo_voix.meta_tide")},
 {id:"narrator",name:dzT("son.demo_voix.narrateur"),meta:dzT("son.demo_voix.meta_narrateur")},
 {id:"abyss",name:"Abyss",meta:dzT("son.demo_voix.meta_abyss")}];
var SVM_DEMO_FILE={file:"voice_scene_03.wav",dur:14.32,pos:2.84,peaks:SVM_EDITOR_PEAKS,pill:dzT("son.demo_voix.pastille"),url:null};

/* ═══════════ Catalogue de démarrage CC0 (backend /api/starter) ═══════════
   80 textures de particules, 5 séquences animées et 606 bruitages livrés AVEC
   l'app, sous licence CC0. Ils existent pour une raison précise : sans clé
   ElevenLabs ni clé fal, cet écran ne proposait que de dépenser. Ici tout est
   jouable, assemblable et exportable sans une seule clé.

   L'index est chargé UNE fois par session (promesse mémoïsée) : il ne bouge
   jamais, il est produit au build. Catalogue absent (dépôt non construit) =
   `available:false`, et chaque surface le dit au lieu d'afficher du vide. */
var SVM_STARTER_IX=null,SVM_STARTER_LISTS={};
function svmStarterIndex(){
  if(!SVM_STARTER_IX)SVM_STARTER_IX=fetch("/api/starter/catalog")
    .then(function(r){return r.json()})
    .catch(function(){return {available:!1,sfx_families:[],particle_families:[],
      anims:[],sources:[],counts:{particles:0,sfx:0,anims:0}}});
  return SVM_STARTER_IX}
function svmStarterList(kind,family){
  var key=kind+"|"+(family||"");
  if(!SVM_STARTER_LISTS[key])SVM_STARTER_LISTS[key]=
    fetch("/api/starter/catalog?kind="+encodeURIComponent(kind)
      +(family?"&family="+encodeURIComponent(family):""))
      .then(function(r){return r.json()})
      .then(function(d){return d.items||[]})
      .catch(function(){return []});
  return SVM_STARTER_LISTS[key]}
/* recherche locale : la liste d'une famille tient en mémoire, inutile de
   repasser par le réseau à chaque frappe */
function svmStarterFilter(items,q){
  var t=svmNorm(q).trim();if(!t)return items;
  var terms=t.split(/\s+/);
  return items.filter(function(it){
    var hay=svmNorm([it.name,it.stem,it.id,it.family].join(" "));
    return terms.every(function(w){return hay.indexOf(w)>=0})})}

/* sondage d'un job sprite2d (particules / séquence) — même contrat que le
   Sprite Lab : /api/jobs/{id} jusqu'à done|failed */
function svmPollJob(jobId,onStep){
  return new Promise(function(res,rej){
    var tries=0;
    (function tick(){
      fetch("/api/jobs/"+jobId).then(function(r){return r.json()}).then(function(j){
        if(onStep)onStep(j.current_step||"",j.progress||0);
        if(j.status==="done")return res(j);
        if(j.status==="failed")return rej(new Error(j.error||dzT("son.job.echec_rendu")));
        if(++tries>300)return rej(new Error(dzT("son.job.delai_depasse")));
        setTimeout(tick,900)}).catch(function(e){rej(e)})})()})}

/* ── rail contextuel ──────────────────────────────────────────────────────
   Le défaut corrigé ici : le rail listait les VOIX quel que soit le
   générateur sélectionné. Choisir « VFX particules » et lire une liste de
   voix, c'est l'écran qui ment sur son propre état. Une seule sélection
   (selGen) pilote désormais le panneau du bas ET le contenu central. */
function SvmRailFamilies(props){
  return r.jsx("div",{className:"svm-voicelist",children:
    props.families.length?props.families.map(function(f){
      return r.jsxs("div",{className:"svm-voice",role:"button",tabIndex:0,
        "data-sel":props.sel===f.id?"":void 0,
        title:f.desc||"",
        onClick:function(){props.onPick(f.id)},
        onKeyDown:function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();props.onPick(f.id)}},
        children:[
        r.jsx("span",{className:"svm-sq7",style:{background:"var("+(props.color||"--c-audio")+")"}}),
        r.jsxs("div",{className:"svm-vbody",children:[
          r.jsx("div",{className:"svm-vname",children:f.name}),
          r.jsx("div",{className:"svm-vmeta",children:f.desc||""})]}),
        r.jsx("span",{className:"svm-dur",children:f.count})]},f.id)})
    :r.jsx("div",{className:"svm-note",children:dzT("son.rail.catalogue_indisponible")})})}

/* ── navigateur de bruitages (aucune clé requise) ───────────────────────── */
function SvmSfxBrowser(props){
  var s1=x.useState(null),items=s1[0],setItems=s1[1];
  var s2=x.useState(""),q=s2[0],setQ=s2[1];
  var s3=x.useState({}),added=s3[0],setAdded=s3[1];
  var s4=x.useState(""),busy=s4[0],setBusy=s4[1];
  x.useEffect(function(){var alive=!0;setItems(null);
    svmStarterList("sfx",props.family).then(function(l){if(alive)setItems(l)});
    return function(){alive=!1}},[props.family]);
  var shown=x.useMemo(function(){
    return items?svmStarterFilter(items,q).slice(0,240):[]},[items,q]);
  function add(it){
    if(busy)return;setBusy(it.id);
    fetch("/api/starter/import",{method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({kind:"sfx",ids:[it.id]})})
      .then(function(r2){if(!r2.ok)throw new Error(dzT("son.sfx.import_refuse"));return r2.json()})
      .then(function(d){setBusy("");
        setAdded(function(o){var n=Object.assign({},o);n[it.id]=d.items&&d.items[0];return n});
        props.onNote(dzT("son.sfx.importe",{nom:it.name}))})
      .catch(function(e){setBusy("");props.onNote(dzT("son.sfx.import_impossible",{e:e.message}))})}
  return r.jsxs("div",{className:"svm-card",children:[
    r.jsxs("div",{className:"svm-cardhead",children:[
      r.jsx(SvmLabel,{children:dzT("son.sfx.titre")}),
      r.jsx("input",{className:"svm-kbsearch",type:"search",value:q,
        placeholder:dzT("son.sfx.chercher_ph"),
        "aria-label":dzT("son.sfx.chercher"),
        onChange:function(e){setQ(e.target.value)}}),
      r.jsx("span",{className:"svm-genprice",title:dzT("son.sfx.gratuit_aide"),children:dzT("son.commun.gratuit")})]}),
    items===null?r.jsx("div",{className:"svm-note",children:dzT("son.sfx.chargement")}):
    !shown.length?r.jsx("div",{className:"svm-note",children:
      q?dzT("son.sfx.aucun_son",{q:q}):dzT("son.sfx.famille_vide")}):
    r.jsx("div",{className:"svm-sfxlist svm-scrolllist",children:shown.map(function(it){
      var url="/starter/"+it.file,on=props.playId===url;
      return r.jsxs("div",{className:"svm-sfx",children:[
        r.jsx("button",{className:"svm-playbtn","data-on":on?"":void 0,
          title:on?"Pause":dzT("son.commun.ecouter"),"aria-label":dzT("son.sfx.ecouter_nom",{nom:it.name}),
          onClick:function(){props.play(url)},children:on?__dzGl("dz-media-pause"):__dzGl("dz-media-lecture")}),
        r.jsx("span",{className:"svm-sfxname",children:it.name}),
        r.jsx("span",{className:"svm-dur",style:{marginLeft:"auto"},
          children:it.dur>0?svmShort(it.dur):"—"}),
        added[it.id]
          ?r.jsx("span",{className:"svm-savedchip",title:dzT("son.sfx.deja_aide"),children:dzT("son.sfx.ajoute")})
          :r.jsx("button",{className:"svm-minibtn",
            title:dzT("son.sfx.copier_aide"),
            "aria-label":dzT("son.sfx.ajouter_nom",{nom:it.name}),
            onClick:function(){add(it)},
            children:busy===it.id?"…":__dzGlT("dz-action-ajouter-bibliotheque",dzT("son.sfx.ajouter"),"+")})]},it.id)})}),
    r.jsx("div",{className:"svm-note",children:
      dzT("son.sfx.licence",{n:(items?items.length:0)})})]})}

/* ── VFX particules : presets, textures, génération LOCALE ──────────────── */
function SvmParticles(props){
  var s1=x.useState(null),data=s1[0],setData=s1[1];   /* presets + anims */
  var s2=x.useState("explosion"),sel=s2[0],setSel=s2[1];
  var s3=x.useState(null),tex=s3[0],setTex=s3[1];     /* textures de la famille */
  var s4=x.useState(""),busy=s4[0],setBusy=s4[1];
  var s5=x.useState(""),step=s5[0],setStep=s5[1];
  var s6=x.useState(null),out=s6[0],setOut=s6[1];
  var s7=x.useState(""),err=s7[0],setErr=s7[1];
  var s8=x.useState(512),cell=s8[0],setCell=s8[1];
  x.useEffect(function(){var alive=!0;
    fetch("/api/particles/presets").then(function(r2){return r2.json()})
      .then(function(d){if(alive)setData(d)})
      .catch(function(){if(alive)setData({available:!1,presets:[],anims:[]})});
    return function(){alive=!1}},[]);
  x.useEffect(function(){var alive=!0;setTex(null);
    if(props.family)svmStarterList("particle",props.family)
      .then(function(l){if(alive)setTex(l)});
    return function(){alive=!1}},[props.family]);

  function run(body,label){
    if(busy)return;setBusy(label);setErr("");setOut(null);setStep(dzT("son.vfx.envoi"));
    fetch(body.anim?"/api/assets/starter-anim":"/api/assets/particles",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify(body)})
      .then(function(r2){return r2.json().then(function(d){
        if(!r2.ok)throw new Error(d.detail||dzT("son.vfx.requete_refusee"));return d})})
      .then(function(d){return svmPollJob(d.job_id,function(st){setStep(st)})})
      .then(function(j){setBusy("");setStep("");
        var short=String(j.job_id||j.id||"").slice(0,8);
        setOut({short:short,title:j.title});
        props.onNote(dzT("son.vfx.sprite_pret"))})
      .catch(function(e){setBusy("");setStep("");setErr(e.message||String(e))})}

  var presets=(data&&data.presets)||[],anims=(data&&data.anims)||[];
  var cur=presets.filter(function(p){return p.id===sel})[0];

  return r.jsxs(r.Fragment,{children:[
    r.jsxs("div",{className:"svm-card",children:[
      r.jsxs("div",{className:"svm-cardhead",children:[
        r.jsx(SvmLabel,{children:dzT("son.vfx.titre")}),
        r.jsx("span",{className:"svm-genprice",
          title:dzT("son.vfx.gratuit_aide"),
          children:dzT("son.vfx.gratuit_local")})]}),
      data===null?r.jsx("div",{className:"svm-note",children:dzT("son.vfx.chargement")}):
      !presets.length?r.jsx("div",{className:"svm-note",children:
        dzT("son.vfx.catalogue_absent")}):
      r.jsx("div",{className:"svm-vfxgrid svm-wide",children:presets.map(function(p){
        return r.jsxs("button",{className:"svm-vfx","data-sel":sel===p.id?"":void 0,
          title:p.desc,onClick:function(){setSel(p.id)},children:[
          r.jsx("div",{className:"svm-vfxprev svm-vfxprev-img",
            style:p.thumb?{backgroundImage:"url("+p.thumb+")"}:null}),
          r.jsxs("div",{className:"svm-vfxfoot",children:[
            r.jsx("div",{className:"svm-vfxname",children:p.name}),
            r.jsx("div",{className:"svm-vfxtype",children:p.type})]})]},p.id)})}),
      cur?r.jsxs("div",{className:"svm-toolrow",style:{marginTop:12},children:[
        r.jsx("span",{className:"svm-note",style:{marginTop:0,flex:"1 1 auto"},
          children:dzT("son.vfx.preset_detail",{desc:cur.desc,texture:cur.texture,n:cur.frames,fps:cur.fps,fusion:cur.blend})}),
        r.jsx("button",{className:"svm-nbgold","data-off":busy?"":void 0,
          title:dzT("son.vfx.simuler_aide"),
          onClick:function(){run({preset:cur.id},"preset")},
          children:busy==="preset"?(step||dzT("son.commun.generation")):dzT("son.vfx.generer")})]}):null,
      err?r.jsx("div",{className:"svm-note",style:{color:"var(--red)"},children:dzT("son.commun.echec")+err}):null,
      out?r.jsxs("div",{className:"svm-toolrow",style:{marginTop:10},children:[
        r.jsx("img",{className:"svm-vfxresult",src:"/api/assets/sprite/"+out.short+"/preview",
          alt:dzT("son.vfx.apercu_alt")}),
        r.jsx("span",{className:"svm-note",style:{marginTop:0,flex:"1 1 auto"},
          children:dzT("son.vfx.pret")}),
        r.jsx("a",{className:"svm-secbtn",href:"/api/assets/sprite/"+out.short+"/zip",
          children:dzT("son.vfx.telecharger")}),
        r.jsx("button",{className:"svm-primarybtn",
          onClick:function(){props.go&&props.go("library")},
          children:__dzGlT("dz-nav-bibliotheque",dzT("son.vfx.ouvrir_biblio"),"→")})]}):null]}),

    r.jsxs("div",{className:"svm-card",children:[
      r.jsxs("div",{className:"svm-cardhead",children:[
        r.jsx(SvmLabel,{children:dzT("son.vfx.sequences")}),
        r.jsxs("select",{className:"svm-cellsel",value:cell,
          "aria-label":dzT("son.vfx.cellule"),
          onChange:function(e){setCell(Number(e.target.value))},
          children:[128,256,512].map(function(v){
            return r.jsx("option",{value:v,children:v+" px"},v)})})]}),
      r.jsx("div",{className:"svm-vfxgrid svm-wide",children:anims.map(function(a){
        return r.jsxs("button",{className:"svm-vfx",
          title:dzT("son.vfx.sequence_aide",{n:a.frames}),
          onClick:function(){run({anim:a.id,cell:cell},"anim:"+a.id)},children:[
          r.jsx("div",{className:"svm-vfxprev svm-vfxprev-img",
            style:{backgroundImage:"url("+a.thumb+")"}}),
          r.jsxs("div",{className:"svm-vfxfoot",children:[
            r.jsx("div",{className:"svm-vfxname",children:a.name}),
            r.jsx("div",{className:"svm-vfxtype",children:
              busy==="anim:"+a.id?(step||"…"):dzT("son.vfx.sequence_images",{n:a.frames})})]})]},a.id)})}),
      r.jsx("div",{className:"svm-note",children:
        dzT("son.vfx.sequences_note")})]}),

    r.jsxs("div",{className:"svm-card",children:[
      r.jsx(SvmLabel,{children:dzT("son.vfx.textures")}),
      tex===null?r.jsx("div",{className:"svm-note",children:dzT("son.vfx.choisir_famille")}):
      r.jsxs(r.Fragment,{children:[
        r.jsx("div",{className:"svm-texgrid",children:tex.map(function(t){
          return r.jsx("button",{className:"svm-tex",title:dzT("son.vfx.texture_aide",{nom:t.name,preset:(cur?cur.name:"—")}),
            "aria-label":dzT("son.vfx.texture_generer",{nom:t.name}),
            onClick:function(){if(cur)run({preset:cur.id,texture:t.id},"preset")},
            children:r.jsx("img",{src:"/starter/"+t.thumb,alt:t.name,loading:"lazy"})},t.id)})}),
        r.jsx("div",{className:"svm-note",children:
          dzT("son.vfx.texture_note",{preset:(cur?cur.name:"—")})})]})]})]})}

/* ── T102 (plan-son-vfx T6) : éditeur de paroles structurées ────────────────
   Sections [Verse]/[Chorus]/[Bridge] éditées une par une, sérialisées en texte
   balisé : le BACKEND normalise par modèle (ACE-Step : minuscules, MiniMax :
   capitalisées), l'écran n'écrit qu'une convention. Le thème du squelette se
   demande par le dialogue maison (jamais window.prompt). */
function svmLyricsParse(t){var out=[],cur=null;
  String(t||"").split(/\r?\n/).forEach(function(l){var mt=/^\[([^\]]+)\]\s*$/.exec(l.trim());
    if(mt){cur={tag:mt[1],text:""};out.push(cur)}
    else if(cur)cur.text+=(cur.text?"\n":"")+l;
    else if(l.trim()){cur={tag:"Verse",text:l};out.push(cur)}});
  return out}
function svmLyricsJoin(secs){return secs.map(function(s){return "["+s.tag+"]\n"+String(s.text||"").trim()}).join("\n\n")}
var SVM_LYR_ADD=[["Verse",dzT("son.paroles.couplet")],["Chorus",dzT("son.paroles.refrain")],["Bridge",dzT("son.paroles.pont")]];
function SvmLyricsEditor(props){
  var secs=svmLyricsParse(props.value);
  function set(next){props.onChange(svmLyricsJoin(next))}
  async function skeleton(){
    var th=window.__dzDialogue?await window.__dzDialogue.saisir(dzT("son.paroles.theme_invite"),
      {titre:dzT("son.paroles.squelette_titre"),ok:dzT("son.paroles.poser")}):"";
    if(th==null)return;
    fetch("/api/music/lyrics-skeleton?theme="+encodeURIComponent(th))
      .then(function(r2){return r2.json()}).then(function(d){if(d&&d.lyrics)props.onChange(d.lyrics)}).catch(function(){})}
  return r.jsxs("div",{className:"svm-lyrics",children:[
    r.jsxs("div",{className:"svm-toolrow",style:{flexWrap:"wrap"},children:[
      SVM_LYR_ADD.map(function(a){return r.jsx("button",{className:"svm-minibtn",
        onClick:function(){set(secs.concat([{tag:a[0],text:""}]))},children:a[1]},a[0])}),
      r.jsx("button",{className:"svm-minibtn",title:dzT("son.paroles.squelette_aide"),
        onClick:skeleton,children:dzT("son.paroles.squelette")}),
      props.required?r.jsx("span",{className:"svm-note",style:{marginTop:0},
        children:dzT("son.paroles.obligatoires")}):null]}),
    secs.length?null:r.jsx("div",{className:"svm-note",
      children:props.required?dzT("son.paroles.aucune_section"):(props.style==="ace"?dzT("son.paroles.vide_ace"):dzT("son.paroles.vide_auto"))}),
    secs.map(function(s,i){return r.jsxs("div",{className:"svm-lyrsec",children:[
      r.jsx("input",{className:"svm-lyrtag",value:s.tag,"aria-label":dzT("son.paroles.balise",{n:(i+1)}),
        onChange:function(e){var n=secs.slice();n[i]=Object.assign({},s,{tag:e.target.value.replace(/[\[\]\n]/g,"")||"Verse"});set(n)}}),
      r.jsx("textarea",{className:"svm-musicprompt",rows:2,value:s.text,"aria-label":dzT("son.paroles.texte",{n:(i+1)}),
        onChange:function(e){var n=secs.slice();n[i]=Object.assign({},s,{text:e.target.value});set(n)}}),
      r.jsx("button",{className:"svm-minibtn",title:dzT("son.paroles.retirer"),"aria-label":dzT("son.paroles.retirer_n",{n:(i+1)}),
        onClick:function(){set(secs.filter(function(_s,j){return j!==i}))},children:__dzGl("dz-action-supprimer")})]},i)})]})}
/* le prix affiché d'un modèle de musique : par génération, ou à la seconde (ACE-Step) sur la durée choisie */
function svmMusicPrice(v,dur){
  return v.usd_unit==="s"?"~$"+(v.usd*dur).toFixed(3)+" · "+dur+" s":"~$"+v.usd.toFixed(2)}

/* ── Musique : génération fal.ai sur la clé déjà configurée ─────────────── */
function SvmMusic(props){
  var s1=x.useState(null),cat=s1[0],setCat=s1[1];
  var s2=x.useState(""),model=s2[0],setModel=s2[1];
  var s3=x.useState(""),mood=s3[0],setMood=s3[1];
  var s4=x.useState(""),prompt=s4[0],setPrompt=s4[1];
  var s5=x.useState(60),dur=s5[0],setDur=s5[1];
  var s6=x.useState(!0),inst=s6[0],setInst=s6[1];
  var s7=x.useState(""),lyrics=s7[0],setLyrics=s7[1];
  var s8=x.useState(!1),busy=s8[0],setBusy=s8[1];
  var s9=x.useState(null),res=s9[0],setRes=s9[1];
  var sA=x.useState(""),err=sA[0],setErr=sA[1];
  var sB=x.useState(""),seed=sB[0],setSeed=sB[1];
  x.useEffect(function(){var alive=!0;
    fetch("/api/music-models").then(function(r2){return r2.json()})
      .then(function(d){if(!alive)return;setCat(d);setModel(d.default||"")})
      .catch(function(){if(alive)setCat({enabled:!1,models:[],moods:[]})});
    return function(){alive=!1}},[]);
  var m=cat&&cat.models.filter(function(v){return v.id===model})[0];
  /* T102 : les paroles se montrent quand le modèle les prend ET que la voix est
     demandée — ou TOUJOURS si le modèle n'a pas d'interrupteur instrumental
     (Music 2.0 : paroles obligatoires ; avant, l'état « instrumental » par
     défaut les cachait à jamais) */
  var showLyr=!!(m&&m.lyrics&&(!m.instrumental||!inst));
  var durNow=m&&m.duration?Math.min(m.duration[1],Math.max(m.duration[0],dur)):dur;
  function go(){
    if(busy||!m)return;
    if(!prompt.trim()&&!mood){setErr(dzT("son.musique.choisir"));return}
    /* les BALISES ne comptent pas (même règle que le serveur) : une section vide passait la borne à elle seule */
    if(m.lyrics_required&&lyrics.replace(/\[[^\[\]\n]{1,24}\]/g,"").trim().length<10){setErr(dzT("son.musique.paroles_exigees",{modele:m.label}));return}
    setBusy(!0);setErr("");setRes(null);
    fetch("/api/audio/music",{method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({model:model,prompt:prompt,mood:mood,
        duration_s:m.duration?durNow:null,instrumental:m.instrumental?inst:!1,
        lyrics:showLyr?lyrics:"",
        seed:m.seed&&String(seed).trim()!==""&&isFinite(Number(seed))?Math.round(Number(seed)):void 0})})
      .then(function(r2){return r2.json().then(function(d){
        if(!r2.ok)throw new Error(d.detail||dzT("son.musique.refusee"));return d})})
      .then(function(d){setBusy(!1);setRes(d);
        if(props.onGenerated&&d.item)props.onGenerated(d.item);
        props.onNote(dzT("son.musique.ajoutee"))})
      .catch(function(e){setBusy(!1);setErr(e.message||String(e))})}

  if(cat===null)return r.jsx("div",{className:"svm-card",
    children:r.jsx("div",{className:"svm-note",children:dzT("son.musique.chargement")})});
  if(!cat.enabled)return r.jsxs("div",{className:"svm-target",children:[
    r.jsx("span",{className:"svm-targettag",children:dzT("son.musique.cle_requise")}),
    r.jsx("div",{style:{color:"var(--ink2)",fontSize:12.5,fontWeight:600,marginBottom:6},
      children:dzT("son.musique.cle_titre")}),
    r.jsxs("div",{children:[dzT("son.musique.cablage",{n:cat.models.length}),
      dzT("son.musique.en_attendant")]})]});

  var resUrl=res&&res.item&&res.item.url,on=props.playId===resUrl;
  return r.jsxs(r.Fragment,{children:[
    r.jsxs("div",{className:"svm-card",children:[
      r.jsxs("div",{className:"svm-cardhead",children:[
        r.jsx(SvmLabel,{children:dzT("son.musique.ambiance")}),
        r.jsx("span",{className:"svm-note",style:{marginTop:0},
          children:dzT("son.musique.ambiance_note")})]}),
      r.jsx("div",{className:"svm-moodgrid",children:cat.moods.map(function(md){
        return r.jsx("button",{className:"svm-mood","data-sel":mood===md.id?"":void 0,
          title:md.prompt,
          onClick:function(){setMood(mood===md.id?"":md.id)},
          children:md.name},md.id)})}),
      r.jsx("textarea",{className:"svm-musicprompt",rows:2,maxLength:1200,
        value:prompt,"aria-label":dzT("son.musique.description"),
        placeholder:dzT("son.musique.description_ph"),
        onChange:function(e){setPrompt(e.target.value);if(err)setErr("")}})]}),

    r.jsxs("div",{className:"svm-card",children:[
      r.jsx(SvmLabel,{children:dzT("son.musique.modele")}),
      r.jsx("div",{className:"svm-modellist",children:cat.models.map(function(v){
        return r.jsxs("button",{className:"svm-model","data-sel":model===v.id?"":void 0,
          onClick:function(){setModel(v.id)},children:[
          r.jsxs("div",{className:"svm-genrow",children:[
            r.jsx("span",{className:"svm-genname",children:v.label}),
            r.jsx("span",{className:"svm-genprice",children:svmMusicPrice(v,v.duration?Math.min(v.duration[1],Math.max(v.duration[0],dur)):dur)})]}),
          r.jsx("div",{className:"svm-gendesc",children:v.desc}),
          r.jsxs("div",{className:"svm-modelcaps",children:[
            r.jsx("span",{className:"svm-cap","data-on":v.duration?"":void 0,
              children:v.duration?dzT("son.musique.duree_plage",{a:v.duration[0],b:v.duration[1]})
                :(v.fixed_duration?dzT("son.musique.duree_fixe",{s:v.fixed_duration}):dzT("son.musique.duree_imposee"))}),
            r.jsx("span",{className:"svm-cap","data-on":v.lyrics?"":void 0,children:dzT("son.musique.cap_paroles")}),
            r.jsx("span",{className:"svm-cap","data-on":v.instrumental?"":void 0,children:"instrumental"}),
            r.jsx("span",{className:"svm-cap","data-on":v.seed?"":void 0,children:dzT("son.musique.graine")})]})]},v.id)})}),
      m?r.jsxs("div",{className:"svm-toolrow",style:{marginTop:12,flexWrap:"wrap"},children:[
        m.duration?r.jsxs(r.Fragment,{children:[
          r.jsx("span",{className:"svm-dur",children:dzT("son.musique.duree")}),
          r.jsx("input",{className:"svm-range",type:"range",min:m.duration[0],
            max:m.duration[1],step:5,value:Math.min(m.duration[1],Math.max(m.duration[0],dur)),
            "aria-label":dzT("son.musique.duree_aide"),
            onChange:function(e){setDur(Number(e.target.value))}}),
          r.jsx("span",{className:"svm-rangeval",children:svmShort(Math.min(m.duration[1],Math.max(m.duration[0],dur)))})]}
        ):r.jsx("span",{className:"svm-note",style:{marginTop:0},
            children:m.fixed_duration?dzT("son.musique.produit",{modele:m.label,s:m.fixed_duration})
              :dzT("son.musique.choisit_duree",{modele:m.label})}),
        m.instrumental?r.jsxs("label",{className:"svm-switchrow",children:[
          r.jsx("input",{type:"checkbox",checked:inst,
            onChange:function(e){setInst(e.target.checked)}}),
          r.jsx("span",{children:"instrumental"})]}):null,
        m.seed?r.jsx("input",{className:"svm-transdur",type:"number",step:1,value:seed,placeholder:dzT("son.musique.graine"),
          title:dzT("son.musique.graine_aide"),
          "aria-label":dzT("son.musique.graine_label"),
          onChange:function(e){setSeed(e.target.value)}}):null,
        r.jsx("button",{className:"svm-nbgold","data-off":busy?"":void 0,
          title:dzT("son.musique.generer_aide"),
          onClick:go,children:busy?dzT("son.commun.generation"):dzT("son.musique.generer")})]}):null,
      showLyr?r.jsx(SvmLyricsEditor,{value:lyrics,onChange:function(v){setLyrics(v);if(err)setErr("")},
        required:!!m.lyrics_required,style:m.lyrics_style}):null,
      err?r.jsx("div",{className:"svm-note",style:{color:"var(--red)"},children:dzT("son.commun.echec")+err}):null]}),

    res?r.jsxs("div",{className:"svm-card",children:[
      r.jsx(SvmLabel,{children:dzT("son.musique.piste_generee")}),
      r.jsxs("div",{className:"svm-sfx",style:{marginTop:10},children:[
        r.jsx("button",{className:"svm-playbtn","data-on":on?"":void 0,
          title:on?"Pause":dzT("son.commun.ecouter"),"aria-label":dzT("son.musique.ecouter_piste"),
          onClick:function(){props.play(resUrl)},children:on?__dzGl("dz-media-pause"):__dzGl("dz-media-lecture")}),
        r.jsx("span",{className:"svm-sfxname",children:res.item.name}),
        r.jsx("span",{className:"svm-dur",style:{marginLeft:"auto"},
          children:res.item.dur>0?svmShort(res.item.dur):"—"}),
        r.jsx("span",{className:"svm-pill",children:res.model_label})]}),
      (res.notes||[]).length?r.jsx("div",{className:"svm-note",style:{color:"var(--amber)"},
        children:res.notes.join(" ")}):null,
      r.jsxs("div",{className:"svm-toolrow",style:{marginTop:10},children:[
        r.jsx("span",{className:"svm-note",style:{marginTop:0,flex:"1 1 auto"},
          children:dzT("son.musique.dans_biblio")}),
        r.jsx("button",{className:"svm-primarybtn",
          onClick:function(){props.go&&props.go("montage")},
          children:__dzGlT("dz-nav-montage",dzT("son.musique.ouvrir_montage"),"→")})]})]}):null]})}

/* T102 : le devis d'une action payante — LE chiffre du backend (le même que la
   garde des plafonds), jamais un tarif recopié ici. null = devis indisponible. */
function svmEstimate(op){
  return fetch("/api/cost/estimate",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify(op)})
    .then(function(r2){return r2.ok?r2.json():null})
    .then(function(d){return d&&typeof d.total_usd==="number"?d.total_usd:null})
    .catch(function(){return null})}
/* T102 (plan-son-vfx T7) : ce qui part au modèle — le MIROIR de
   voice_direction.apply_style : les balises du style en tête, sauf si le texte
   commence déjà par une balise (l'auteur a dirigé lui-même) */
var SVM_TAG_HEAD=/^\[[^\[\]\n]{1,40}\]/;
function svmVoText(tags,script){var t=String(script||"").trim();
  return !tags.length||SVM_TAG_HEAD.test(t)?t:(tags.join(" ")+" "+t)}
/* T102 (plan-son-vfx T8) : trois réglages de ducking nommés — paramètres de
   parse_ducking (bornés côté serveur), du plus discret au plus marqué */
var SVM_DUCK={leger:{label:dzT("son.ducking.leger"),ratio:3,threshold:.08},moyen:{label:dzT("son.ducking.moyen"),ratio:6,threshold:.05},
  fort:{label:dzT("son.ducking.fort"),ratio:12,threshold:.03}};

/* ═════════════════════ Écran 06 · Son & VFX ═════════════════════ */
function DzSonVfx(props){
  var th=svmUseTheme(),theme=th[0],setTheme=th[1];
  var st1=x.useState("voiceover"),selGen=st1[0],setSelGen=st1[1];
  var st2=x.useState("audio"),tab=st2[0],setTab=st2[1];
  var st3=x.useState(null),voices=st3[0],setVoices=st3[1]; /* null=chargement, {enabled,list} */
  var st4=x.useState(""),selVoice=st4[0],setSelVoice=st4[1];
  var st5=x.useState(SVM_DEMO_FILE),cur=st5[0],setCur=st5[1];
  var st6=x.useState(!1),playing=st6[0],setPlaying=st6[1];
  var st7=x.useState("goldburst"),selVfx=st7[0],setSelVfx=st7[1];
  var st8=x.useState(""),playingVoice=st8[0],setPlayingVoice=st8[1];
  /* génération SFX réelle (couche DzSfx → /api/audio/sfx) — couche absente,
     la carte démo du handoff reste exactement celle d'avant */
  var stG1=x.useState(""),sfxPrompt=stG1[0],setSfxPrompt=stG1[1];
  var stG2=x.useState(3),sfxDur=stG2[0],setSfxDur=stG2[1]; /* s · 0 = durée auto */
  var stG3=x.useState(!1),sfxBusy=stG3[0],setSfxBusy=stG3[1];
  var stG4=x.useState(null),sfxItems=stG4[0],setSfxItems=stG4[1];
  var stG5=x.useState(""),sfxErr=stG5[0],setSfxErr=stG5[1];
  var stG6=x.useState(""),sfxPlay=stG6[0],setSfxPlay=stG6[1]; /* url de l'item en écoute */
  /* dernière mesure loudness RÉELLE (Montage → Mesurer, dz_last_lufs) — elle
     remplace l'ancien libellé statique « −14 LUFS » qui ne mesurait rien */
  var stLm=x.useState(function(){
    try{return JSON.parse(localStorage.getItem("dz_last_lufs")||"null")}catch(_e){return null}}),
    lastLufs=stLm[0];
  /* catalogue de démarrage CC0 + familles sélectionnées dans le rail */
  var stIx=x.useState(null),ix=stIx[0],setIx=stIx[1];
  var stF1=x.useState("impacts"),sfxFam=stF1[0],setSfxFam=stF1[1];
  var stF2=x.useState("fire"),partFam=stF2[0],setPartFam=stF2[1];
  var stPl=x.useState(""),playId=stPl[0],setPlayId=stPl[1]; /* url en écoute */
  /* T102 (T7) : voix off dirigée — texte, balises v3 posées, palette servie, devis armé */
  var stV1=x.useState(""),voScript=stV1[0],setVoScript=stV1[1];
  var stV2=x.useState([]),voTags=stV2[0],setVoTags=stV2[1];
  var stV3=x.useState(null),tagCat=stV3[0],setTagCat=stV3[1];
  var stV4=x.useState(!1),voBusy=stV4[0],setVoBusy=stV4[1];
  var stV5=x.useState(null),voArm=stV5[0],setVoArm=stV5[1]; /* {usd} : devis lu, le 2e clic tire */
  /* T102 (T8) : mix voix + musique ducké, sans timeline */
  var stM1=x.useState(""),mixVoice=stM1[0],setMixVoice=stM1[1];
  var stM2=x.useState(""),mixMusic=stM2[0],setMixMusic=stM2[1];
  var stM3=x.useState("moyen"),mixPreset=stM3[0],setMixPreset=stM3[1];
  var stM4=x.useState(!1),mixBusy=stM4[0],setMixBusy=stM4[1];
  var stM5=x.useState(null),mixRes=stM5[0],setMixRes=stM5[1];
  var nt=svmUseNote(),note=nt[0],fireNote=nt[1];
  x.useEffect(function(){var alive=!0;
    fetch("/api/voice-tags").then(function(r2){return r2.json()})
      .then(function(d){if(alive)setTagCat(d&&d.groups?d:{groups:{},providers:{},experimental:[]})})
      .catch(function(){if(alive)setTagCat({groups:{},providers:{},experimental:[]})});
    return function(){alive=!1}},[]);
  var audioRef=x.useRef(null),rafRef=x.useRef(0),simRef=x.useRef(0);

  x.useEffect(function(){var alive=!0;
    svmStarterIndex().then(function(d){if(!alive)return;setIx(d);
      if(d.sfx_families&&d.sfx_families[0])setSfxFam(function(f){
        return d.sfx_families.some(function(x2){return x2.id===f})?f:d.sfx_families[0].id});
      if(d.particle_families&&d.particle_families[0])setPartFam(function(f){
        return d.particle_families.some(function(x2){return x2.id===f})?f:d.particle_families[0].id})});
    return function(){alive=!1}},[]);

  /* voix — vraie liste ElevenLabs quand la clé est configurée */
  x.useEffect(function(){var alive=!0;
    fetch("/api/voices").then(function(res){return res.json()}).then(function(d){
      if(!alive)return;
      var list=(d&&d.voices||[]).map(function(v){
        var lbl=v.labels||{};var bits=[v.language||lbl.language||lbl.accent,v.category].filter(Boolean);
        return {id:v.voice_id,name:v.name||v.voice_id,meta:bits.join(" · ")||"voix",cloned:v.category==="cloned",preview:v.preview_url||null}});
      if(d&&d.enabled&&list.length){
        list.sort(function(a,b){return (b.cloned?1:0)-(a.cloned?1:0)});
        setVoices({enabled:!0,list:list});
        var pref=list.find(function(v){return /prophet/i.test(v.name)})||list.find(function(v){return v.cloned})||list[0];
        setSelVoice(pref.id)}
      else{setVoices({enabled:!1,list:SVM_DEMO_VOICES});setSelVoice("prophet")}
    }).catch(function(){if(alive){setVoices({enabled:!1,list:SVM_DEMO_VOICES});setSelVoice("prophet")}});
    return function(){alive=!1}},[]);

  /* fichier courant — dernier audio de la Bibliothèque, vrais pics via WebAudio */
  x.useEffect(function(){var alive=!0;
    fetch("/api/audio").then(function(res){return res.json()}).then(function(d){
      var first=d&&d.audio&&d.audio[0];if(!alive||!first)return;
      fetch(first.url).then(function(res){return res.arrayBuffer()}).then(function(buf){
        var AC=window.AudioContext||window.webkitAudioContext;if(!AC)return;
        var ctx=new AC();return ctx.decodeAudioData(buf).then(function(ab){
          var ch=ab.getChannelData(0),n=60,bl=Math.floor(ch.length/n),peaks=[],max=0;
          for(var i=0;i<n;i++){var v=0;for(var j2=i*bl;j2<(i+1)*bl;j2+=64){var a=Math.abs(ch[j2]);if(a>v)v=a}peaks.push(v);if(v>max)max=v}
          peaks=peaks.map(function(v2){return Math.round(18+67*(max?v2/max:0))});
          if(alive)setCur({file:first.name,dur:ab.duration,pos:0,peaks:peaks,pill:dzT("son.editeur.pastille_biblio"),url:first.url});
          ctx.close&&ctx.close()})
      }).catch(function(){})
    }).catch(function(){});
    return function(){alive=!1}},[]);

  /* un seul flux à la fois — fichier de l'éditeur (url réelle ou progression simulée) */
  function stopAll(){setPlaying(!1);setPlayingVoice("");setSfxPlay("");setPlayId("");
    if(audioRef.current){audioRef.current.pause();audioRef.current=null}
    if(rafRef.current){cancelAnimationFrame(rafRef.current);rafRef.current=0}}
  /* écoute générique (catalogue de démarrage, piste générée) — même règle
     « un seul flux » que le reste de l'écran : rien ne se superpose */
  var playUrl=x.useCallback(function(url){
    if(!url)return;
    if(playId===url){stopAll();return}
    stopAll();
    var a=new Audio(url);audioRef.current=a;setPlayId(url);
    a.onended=function(){setPlayId("")};
    a.play().catch(function(){setPlayId("");
      fireNote(dzT("son.commun.lecture_bloquee"))})},
    [playId]);
  x.useEffect(function(){return stopAll},[]);
  function toggleEditor(){
    if(playing){stopAll();return}
    stopAll();setPlaying(!0);
    if(cur.url){var a=new Audio(cur.url);audioRef.current=a;a.currentTime=cur.pos>=cur.dur-.05?0:cur.pos;
      a.ontimeupdate=function(){setCur(function(c){return Object.assign({},c,{pos:a.currentTime})})};
      a.onended=function(){setPlaying(!1);setCur(function(c){return Object.assign({},c,{pos:0})})};
      a.play().catch(function(){setPlaying(!1);fireNote(dzT("son.commun.lecture_bloquee"))})}
    else{var last=performance.now();simRef.current=cur.pos>=cur.dur-.05?0:cur.pos;
      var step=function(now){var dt=(now-last)/1000;last=now;simRef.current+=dt;
        if(simRef.current>=cur.dur){setPlaying(!1);setCur(function(c){return Object.assign({},c,{pos:0})});rafRef.current=0;return}
        setCur(function(c){return Object.assign({},c,{pos:simRef.current})});rafRef.current=requestAnimationFrame(step)};
      rafRef.current=requestAnimationFrame(step)}}
  function seekWave(e){var el=e.currentTarget,rect=el.getBoundingClientRect();
    var f=Math.min(1,Math.max(0,(e.clientX-rect.left-10)/(rect.width-20)));
    var p=f*cur.dur;setCur(function(c){return Object.assign({},c,{pos:p})});
    if(audioRef.current)audioRef.current.currentTime=p;simRef.current=p}
  function playVoice(v,e){e.stopPropagation();
    if(playingVoice===v.id){stopAll();return}
    stopAll();
    if(v.preview){var a=new Audio(v.preview);audioRef.current=a;setPlayingVoice(v.id);
      a.onended=function(){setPlayingVoice("")};
      a.play().catch(function(){setPlayingVoice("");fireNote(dzT("son.voix.apercu_indispo"))})}
    else fireNote(dzT("son.voix.apercu_eleven"))}
  /* écoute d'un SFX généré — même règle « un seul flux » que tout l'écran */
  function playSfxItem(it){
    if(sfxPlay===it.url){stopAll();return}
    stopAll();
    var a=new Audio(it.url);audioRef.current=a;setSfxPlay(it.url);
    a.onended=function(){setSfxPlay("")};
    a.play().catch(function(){setSfxPlay("");
      fireNote(dzT("son.commun.lecture_bloquee"))})}
  /* génération : DzSfx.genSfx → POST /api/audio/sfx (2 variations) ; chaque
     fichier rejoint la Bibliothèque (sons) et donc le tiroir Sons du Montage */
  function genSfxGo(){
    var d=svmSfx();if(!d||!d.genSfx)return;
    var p=sfxPrompt.trim();
    if(!p){setSfxErr(dzT("son.sfx.decrire_dabord"));return}
    if(sfxBusy)return;
    setSfxBusy(!0);setSfxErr("");
    d.genSfx({prompt:p,duration_s:sfxDur>0?sfxDur:null,prompt_influence:.3,variations:2})
      .then(function(o){
        var items=(o&&o.items)||[];
        if(!items.length)throw new Error(dzT("son.sfx.aucun_son_retourne"));
        setSfxBusy(!1);setSfxItems(items)})
      .catch(function(e){setSfxBusy(!1);setSfxErr(String(e&&e.message||e))})}


  /* Une seule sélection pilote l'écran. Avant, le rail et les onglets étaient
     deux états indépendants : cliquer « VFX particules » laissait la liste des
     VOIX en dessous et l'onglet Audio actif. Désormais choisir un générateur
     déplace l'onglet, et choisir un onglet déplace le générateur. */
  function pickGen(id){setSelGen(id);setTab(SVM_GEN_TAB[id]||"audio")}
  function pickTab(t){setTab(t);
    if(t==="vfx")setSelGen("vfx");
    else if(t==="post")setSelGen("post");
    else if(SVM_GEN_TAB[selGen]!=="audio")setSelGen("voiceover")}

  /* panneau bas du rail — CONTEXTUEL au générateur sélectionné */
  var railBottom=
    selGen==="voiceover"?r.jsxs(r.Fragment,{children:[
      r.jsx(SvmLabel,{style:{margin:"22px 0 10px"},children:dzT("son.commun.voix")}),
      r.jsx("div",{className:"svm-voicelist",children:
        voices===null?r.jsx("div",{className:"svm-note",children:dzT("son.voix.chargement")}):
        voices.list.map(function(v){
          return r.jsxs("div",{className:"svm-voice",role:"button",tabIndex:0,
            "data-sel":selVoice===v.id?"":void 0,
            onClick:function(){setSelVoice(v.id)},
            onKeyDown:function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();setSelVoice(v.id)}},
            children:[
            r.jsx("span",{className:"svm-avatar"}),
            r.jsxs("div",{className:"svm-vbody",children:[
              r.jsx("div",{className:"svm-vname",children:v.name}),
              r.jsx("div",{className:"svm-vmeta",children:v.meta})]}),
            r.jsx("button",{className:"svm-playbtn","data-on":playingVoice===v.id?"":void 0,
              title:dzT("son.voix.ecouter"),"aria-label":dzT("son.sfx.ecouter_nom",{nom:v.name}),
              onClick:function(e){playVoice(v,e)},children:playingVoice===v.id?__dzGl("dz-media-pause"):__dzGl("dz-media-lecture")})]},v.id)})})]}):
    selGen==="sfx"?r.jsxs(r.Fragment,{children:[
      r.jsx(SvmLabel,{style:{margin:"22px 0 10px"},children:dzT("son.rail.familles_sons")}),
      r.jsx(SvmRailFamilies,{families:(ix&&ix.sfx_families)||[],sel:sfxFam,
        color:"--c-audio",onPick:setSfxFam})]}):
    selGen==="vfx"?r.jsxs(r.Fragment,{children:[
      r.jsx(SvmLabel,{style:{margin:"22px 0 10px"},children:dzT("son.rail.familles_textures")}),
      r.jsx(SvmRailFamilies,{families:(ix&&ix.particle_families)||[],sel:partFam,
        color:"--c-3d",onPick:setPartFam})]}):
    selGen==="music"?r.jsxs(r.Fragment,{children:[
      r.jsx(SvmLabel,{style:{margin:"22px 0 10px"},children:dzT("son.rail.sans_cle")}),
      r.jsx("div",{className:"svm-note",style:{marginTop:0},
        children:dzT("son.rail.jingles_note")}),
      r.jsx("button",{className:"svm-secbtn",style:{marginTop:10,width:"100%"},
        onClick:function(){setSfxFam("jingles");pickGen("sfx")},
        children:dzT("son.rail.ouvrir_jingles")})]}):
    r.jsxs(r.Fragment,{children:[
      r.jsx(SvmLabel,{style:{margin:"22px 0 10px"},children:dzT("son.rail.ou_applique")}),
      r.jsx("div",{className:"svm-note",style:{marginTop:0},
        children:dzT("son.rail.post_note")})]});

  /* rail gauche */
  var rail=r.jsxs("aside",{className:"svm-rail",children:[
    r.jsx(SvmLabel,{children:dzT("son.rail.generateurs")}),
    r.jsx("div",{className:"svm-genlist",children:SVM_GENS.map(function(g){
      return r.jsxs("button",{className:"svm-gen","data-sel":selGen===g.id?"":void 0,
        onClick:function(){pickGen(g.id)},children:[
        r.jsxs("div",{className:"svm-genrow",children:[
          r.jsx("span",{className:"svm-sq7",style:{background:"var("+g.c+")"}}),
          r.jsx("span",{className:"svm-genname",children:g.name}),
          r.jsx("span",{className:"svm-genprice",children:g.price})]}),
        r.jsx("div",{className:"svm-gendesc",children:g.desc})]},g.id)})}),
    railBottom]});

  /* carte éditeur de voix (le formulaire du générateur Voix off, tel que maquetté) */
  var editorCard=r.jsxs("div",{className:"svm-card",children:[
    r.jsxs("div",{className:"svm-cardhead",children:[
      r.jsx("span",{className:"svm-file",children:cur.file}),
      r.jsx("span",{className:"svm-pill",children:cur.pill}),
      r.jsx("span",{className:"svm-time",children:svmClock(cur.pos)+" / "+svmClock(cur.dur)})]}),
    r.jsxs("div",{className:"svm-wave",onClick:seekWave,title:dzT("son.editeur.se_deplacer"),children:[
      cur.peaks.map(function(h,i){return r.jsx("div",{className:"svm-bar",style:{height:h+"%"}},i)}),
      r.jsx("div",{className:"svm-wavehead",style:{left:(cur.dur?cur.pos/cur.dur*100:0)+"%"}})]}),
    r.jsxs("div",{className:"svm-toolrow",children:[
      r.jsx("button",{className:"svm-play30",onClick:toggleEditor,
        title:playing?"Pause":dzT("son.commun.lecture"),"aria-label":playing?"Pause":dzT("son.commun.lecture"),children:playing?__dzGl("dz-media-pause"):__dzGl("dz-media-lecture")}),
      [dzT("son.editeur.rogner"),dzT("son.editeur.fondu"),"Ducking",dzT("son.editeur.normaliser"),dzT("son.editeur.de_esser")].map(function(t){
        return r.jsx("button",{className:"svm-toolbtn",
          /* couche DzSfx chargée : ces outils EXISTENT, par clip dans le
             Montage — la note pointe le vrai chemin au lieu d'une promesse */
          onClick:function(){fireNote(svmSfx()
            ?dzT("son.editeur.outil_montage",{outil:t,touche:svmKeyLabelNow("sounds_drawer")})
            :dzT("son.editeur.outil_cible",{outil:t}))},
          children:t},t)}),
      r.jsx("button",{className:"svm-primarybtn",
        onClick:function(){props.go&&props.go("montage")},children:__dzGlT("dz-nav-montage",dzT("son.editeur.envoyer_montage"),"→")})]})]});

  /* ── T102 (T7) : la voix off DIRIGÉE — une vraie génération ──────────────
     Palette des balises Eleven v3 servie par /api/voice-tags (registre relu
     côté serveur) ; l'aperçu montre EXACTEMENT ce qui part ; payante, donc
     armée : 1er clic = devis du backend, 2e clic = tir. Sous Voicebox, pas de
     palette (les balises seraient retirées) et un seul clic (local, gratuit). */
  var voText=svmVoText(voTags,voScript);
  var voEleven=!!(tagCat&&tagCat.providers&&tagCat.providers.elevenlabs);
  function voFire(){setVoBusy(!0);setVoArm(null);
    fetch("/api/audio/voiceover",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({script:voScript,language:"fr",name:"sonvfx_vo",
        voice_id:voices&&voices.enabled?selVoice:void 0,
        model:voTags.length?"eleven_v3":void 0,style:{tags:voTags}})})
      .then(function(r2){return r2.json().then(function(d){if(!r2.ok)throw new Error(d.detail||dzT("son.commun.echec_mot"));return d})})
      .then(function(d){setVoBusy(!1);setMixVoice(d.filename);
        setCur({file:d.filename,dur:0,pos:0,peaks:cur.peaks,pill:dzT("son.editeur.pastille_generee"),url:d.url});
        fireNote(dzT("son.vo.generee",{nom:d.filename,notes:(d.notes||[]).length?" — "+d.notes.join(" · "):""}))})
      .catch(function(e){setVoBusy(!1);fireNote(dzT("son.vo.erreur",{e:String(e&&e.message||e)}))})}
  function voGo(){
    if(voBusy||!voScript.trim())return;
    if(!voEleven){voFire();return}
    if(voArm){voFire();return}
    svmEstimate({kind:"elevenlabs",chars:voText.length,model:voTags.length?"eleven_v3":void 0})
      .then(function(usd){setVoArm({usd:usd})})}
  var voCard=r.jsxs("div",{className:"svm-card svm-vodir",children:[
    r.jsxs("div",{className:"svm-cardhead",children:[
      r.jsx(SvmLabel,{children:dzT("son.vo.titre")}),
      r.jsx("span",{className:"svm-note",style:{marginTop:0},
        children:dzT("son.vo.balises_aide")})]}),
    r.jsx("textarea",{className:"svm-musicprompt",rows:3,value:voScript,maxLength:5000,
      "aria-label":dzT("son.vo.texte"),
      placeholder:dzT("son.vo.texte_exemple"),
      onChange:function(e){setVoScript(e.target.value);setVoArm(null)}}),
    tagCat===null?r.jsx("div",{className:"svm-note",children:dzT("son.vo.chargement_balises")}):
    voEleven?r.jsx("div",{className:"svm-tagpal",children:Object.keys(tagCat.groups).map(function(g){
      return r.jsxs("div",{className:"svm-taggrp",children:[
        r.jsx("span",{className:"svm-note",style:{marginTop:0,minWidth:64},children:g}),
        tagCat.groups[g].map(function(t){var on=voTags.indexOf(t)>=0;
          return r.jsx("button",{className:"svm-minibtn","data-on":on?"":void 0,"aria-pressed":on,
            title:(tagCat.experimental||[]).indexOf(t)>=0?dzT("son.vo.balise_speciale"):dzT("son.vo.balise_v3"),
            onClick:function(){setVoArm(null);
              setVoTags(on?voTags.filter(function(x2){return x2!==t}):voTags.concat([t]).slice(-(tagCat.max_tags||4)))},
            children:t},t)})]},g)})}):
    r.jsx("div",{className:"svm-note",children:tagCat.providers&&tagCat.providers.voicebox
      ?dzT("son.vo.voicebox_sans_balises")
      :dzT("son.vo.balises_cle")}),
    r.jsxs("div",{className:"svm-note",title:dzT("son.vo.apercu_aide"),children:[
      dzT("son.vo.apercu"),r.jsx("b",{className:"svm-voapercu",children:voText||"—"})]}),
    r.jsxs("div",{className:"svm-toolrow",style:{marginTop:8},children:[
      voArm?r.jsx("span",{className:"svm-note",style:{marginTop:0,flex:"1 1 auto"},
        children:voArm.usd==null?dzT("son.vo.devis_indispo")
          :dzT("son.vo.devis",{usd:voArm.usd.toFixed(3)})}):null,
      r.jsx("button",{className:"svm-nbgold","data-off":voBusy||!voScript.trim()?"":void 0,
        onClick:voGo,
        children:voBusy?dzT("son.vo.synthese"):voArm?dzT("son.vo.confirmer"):dzT("son.vo.generer")})]})]});

  /* ── T102 (T8) : le mix voix + musique ducké, SANS timeline ─────────────
     La dernière voix et la dernière musique générées ici ; POST /api/audio/duck
     (ffmpeg local, gratuit) rend un mix à la durée de la voix, posé en
     Bibliothèque. */
  function mixGo(){
    if(mixBusy||!mixVoice||!mixMusic)return;
    setMixBusy(!0);setMixRes(null);
    var pr=SVM_DUCK[mixPreset]||SVM_DUCK.moyen;
    fetch("/api/audio/duck",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({voice:mixVoice,music:mixMusic,ducking:{ratio:pr.ratio,threshold:pr.threshold}})})
      .then(function(r2){return r2.json().then(function(d){if(!r2.ok)throw new Error(d.detail||dzT("son.commun.echec_mot"));return d})})
      .then(function(d){setMixBusy(!1);setMixRes(d);playUrl(d.url);
        fireNote(dzT("son.mix.pose",{nom:d.filename}))})
      .catch(function(e){setMixBusy(!1);fireNote(dzT("son.mix.erreur",{e:String(e&&e.message||e)}))})}
  var mixCard=(mixVoice||mixMusic)?r.jsxs("div",{className:"svm-card svm-mix",children:[
    r.jsxs("div",{className:"svm-cardhead",children:[
      r.jsx(SvmLabel,{children:dzT("son.mix.titre")}),
      r.jsx("span",{className:"svm-genprice",title:dzT("son.mix.ffmpeg_local"),children:dzT("son.commun.gratuit")})]}),
    r.jsxs("div",{className:"svm-note",children:[dzT("son.mix.voix"),r.jsx("b",{children:mixVoice||dzT("son.mix.generer_voix")}),
      dzT("son.mix.musique"),r.jsx("b",{children:mixMusic||dzT("son.mix.generer_musique")})]}),
    r.jsxs("div",{className:"svm-toolrow",style:{marginTop:8,flexWrap:"wrap"},children:[
      r.jsx("span",{className:"svm-dur",children:"ducking"}),
      Object.keys(SVM_DUCK).map(function(k){return r.jsx("button",{className:"svm-minibtn",
        "data-on":mixPreset===k?"":void 0,"aria-pressed":mixPreset===k,
        title:dzT("son.mix.preset_aide",{ratio:SVM_DUCK[k].ratio,seuil:SVM_DUCK[k].threshold}),
        onClick:function(){setMixPreset(k)},children:SVM_DUCK[k].label},k)}),
      r.jsx("button",{className:"svm-nbgold","data-off":mixBusy||!mixVoice||!mixMusic?"":void 0,
        onClick:mixGo,children:mixBusy?dzT("son.mix.mixage"):dzT("son.mix.ecouter")})]}),
    mixRes?r.jsx("div",{className:"svm-note",children:dzT("son.mix.resultat",{nom:mixRes.filename})
      +(mixRes.dur?" · "+svmShort(mixRes.dur):"")}):null]}):null;

  /* panneau cible-produit pour les générateurs sans backend */
  function targetPanel(title,body){
    return r.jsxs("div",{className:"svm-target",children:[
      r.jsx("span",{className:"svm-targettag",children:dzT("son.cible.tag")}),
      r.jsx("div",{style:{color:"var(--ink2)",fontSize:12.5,fontWeight:600,marginBottom:6},children:title}),
      r.jsx("div",{children:body})]})}
  var postPanel=targetPanel(dzT("son.cible.post_titre"),dzT("son.cible.post_corps"));

  /* carte SFX — couche DzSfx chargée : VRAIE génération (prompt + durée +
     2 variations jouables, « Ouvrir le Montage ») ; absente : maquette d'avant */
  var sfxCard=svmSfx()?
    r.jsxs("div",{className:"svm-card",children:[
      r.jsxs("div",{className:"svm-cardhead",children:[
        r.jsx(SvmLabel,{children:dzT("son.sfx.titre_generer")}),
        r.jsx("span",{className:"svm-genprice",
          title:dzT("son.sfx.prix_aide"),children:"$0.03"})]}),
      r.jsxs("div",{className:"svm-sfxform",children:[
        r.jsx("input",{className:"svm-sfxprompt",type:"text",maxLength:450,value:sfxPrompt,
          placeholder:dzT("son.sfx.prompt_exemple"),
          "aria-label":dzT("son.sfx.prompt"),
          onChange:function(e){setSfxPrompt(e.target.value);if(sfxErr)setSfxErr("")},
          onKeyDown:function(e){if(e.key==="Enter")genSfxGo()}}),
        r.jsx("input",{className:"svm-transdur",type:"number",min:0,max:22,step:.5,value:sfxDur,
          title:dzT("son.sfx.duree_aide"),
          "aria-label":dzT("son.sfx.duree"),
          onChange:function(e){var v=Number(e.target.value);
            if(isFinite(v))setSfxDur(Math.max(0,Math.min(22,v)))}}),
        r.jsx("span",{className:"svm-dur",children:sfxDur>0?"s":"auto"}),
        r.jsx("button",{className:"svm-nbgold","data-off":sfxBusy||!sfxPrompt.trim()?"":void 0,
          title:dzT("son.sfx.generer_aide"),
          onClick:function(){if(!sfxBusy)genSfxGo()},
          children:sfxBusy?dzT("son.commun.generation"):dzT("son.commun.generer")})]}),
      sfxErr?r.jsx("div",{className:"svm-note",style:{color:"var(--red)"},children:dzT("son.commun.echec")+sfxErr}):null,
      sfxItems&&sfxItems.length?r.jsxs(r.Fragment,{children:[
        r.jsx("div",{className:"svm-sfxlist",children:sfxItems.map(function(it,i2){
          return r.jsxs("div",{className:"svm-sfx",children:[
            r.jsx("button",{className:"svm-playbtn","data-on":sfxPlay===it.url?"":void 0,
              title:sfxPlay===it.url?"Pause":dzT("son.commun.ecouter"),
              "aria-label":dzT("son.sfx.ecouter_nom",{nom:it.name||dzT("son.sfx.variation",{n:i2+1})}),
              onClick:function(){playSfxItem(it)},children:sfxPlay===it.url?__dzGl("dz-media-pause"):__dzGl("dz-media-lecture")}),
            r.jsx("span",{className:"svm-sfxname",children:it.name||(dzT("son.sfx.variation",{n:i2+1}))}),
            r.jsx("span",{className:"svm-dur",style:{marginLeft:"auto"},
              children:Number(it.dur)>0?svmShort(Number(it.dur)):"—"})]},it.url||i2)})}),
        r.jsxs("div",{className:"svm-toolrow",style:{marginTop:10},children:[
          r.jsx("span",{className:"svm-note",style:{marginTop:0,flex:"1 1 auto"},
            children:dzT("son.sfx.sauvegardes")}),
          r.jsx("button",{className:"svm-primarybtn",
            onClick:function(){stopAll();props.go&&props.go("montage")},
            children:__dzGlT("dz-nav-montage",dzT("son.sfx.ouvrir_montage"),"→")})]})]}):
      r.jsx("div",{className:"svm-note",
        children:dzT("son.sfx.note",{touche:svmKeyLabelNow("sounds_drawer")})})]}):
    r.jsxs("div",{className:"svm-card",children:[
      r.jsx(SvmLabel,{children:dzT("son.sfx.pack_titre")}),
      r.jsx("div",{className:"svm-sfxlist",children:SVM_SFX.map(function(s2){
        return r.jsxs("div",{className:"svm-sfx",children:[
          r.jsx("button",{className:"svm-playbtn",title:dzT("son.commun.ecouter"),"aria-label":dzT("son.sfx.ecouter_nom",{nom:s2.name}),
            onClick:function(){fireNote(dzT("son.sfx.sans_backend"))},children:__dzGl("dz-media-lecture")}),
          r.jsx("span",{className:"svm-sfxname",children:s2.name}),
          r.jsx("div",{className:"svm-miniwave",children:s2.bars.map(function(h,i){
            return r.jsx("div",{className:"svm-minibar",style:{height:h+"%"}},i)})}),
          r.jsx("span",{className:"svm-dur",children:s2.dur})]},s2.id)})})]});

  /* presets de post-traitement — ils n'ont jamais eu de génération à câbler,
     ils pointent vers le moteur Effects / Mask du nœud Render */
  var postCard=r.jsxs("div",{className:"svm-card",children:[
    r.jsx(SvmLabel,{children:dzT("son.post.titre")}),
    r.jsx("div",{className:"svm-vfxgrid svm-wide",children:
      SVM_VFX.filter(function(v){return v.kind==="post"}).map(function(v){
      return r.jsxs("button",{className:"svm-vfx","data-sel":selVfx===v.id?"":void 0,
        onClick:function(){setSelVfx(v.id)},children:[
        r.jsx("div",{className:"svm-vfxprev"}),
        r.jsxs("div",{className:"svm-vfxfoot",children:[
          r.jsx("div",{className:"svm-vfxname",children:v.name}),
          r.jsx("div",{className:"svm-vfxtype",children:v.type})]})]},v.id)})}),
    r.jsx("div",{className:"svm-note",children:dzT("son.post.note")})]});

  /* Contenu central — piloté par LE générateur sélectionné, comme le rail.
     Ordre volontaire côté SFX : le catalogue livré (gratuit, sans clé) passe
     AVANT la génération facturée. Un nouvel utilisateur doit pouvoir écouter
     et poser un son avant qu'on lui parle de crédits. */
  var center=
    selGen==="sfx"?r.jsxs(r.Fragment,{children:[
      r.jsx(SvmSfxBrowser,{family:sfxFam,onNote:fireNote,play:playUrl,playId:playId}),
      sfxCard]}):
    selGen==="music"?r.jsxs(r.Fragment,{children:[
      r.jsx(SvmMusic,{onNote:fireNote,play:playUrl,playId:playId,go:props.go,
        onGenerated:function(it){setMixMusic(it.filename)}}),
      mixCard]}):
    selGen==="vfx"?r.jsx(SvmParticles,{family:partFam,onNote:fireNote,go:props.go}):
    selGen==="post"?r.jsxs(r.Fragment,{children:[postPanel,postCard]}):
    r.jsxs(r.Fragment,{children:[voCard,mixCard,editorCard,
      r.jsxs("div",{className:"svm-grid2",children:[sfxCard,postCard]})]});

  return r.jsxs("div",{className:"dzsvm","data-svm-theme":theme==="light"?"light":void 0,children:[
    rail,
    r.jsxs("div",{className:"svm-main",children:[
      r.jsxs("div",{className:"svm-titlebar",children:[
        r.jsx("span",{className:"svm-title",children:dzT("son.ecran.titre")}),
        r.jsxs("div",{className:"svm-tabs",children:[
          r.jsx("button",{className:"svm-tab","data-on":tab==="audio"?"":void 0,onClick:function(){pickTab("audio")},children:"Audio"}),
          r.jsx("button",{className:"svm-tab","data-on":tab==="vfx"?"":void 0,onClick:function(){pickTab("vfx")},children:dzT("son.ecran.onglet_vfx")}),
          r.jsx("button",{className:"svm-tab","data-on":tab==="post"?"":void 0,onClick:function(){pickTab("post")},children:dzT("son.ecran.onglet_post")})]}),
        /* loudness : seulement une MESURE réelle (Montage → Mesurer) — plus
           jamais un chiffre décoratif ; sans mesure, l'emplacement reste vide
           (le span garde le margin-left:auto qui cale la chip de thème) */
        lastLufs&&isFinite(Number(lastLufs.i))?
          r.jsx("span",{className:"svm-meter",
            title:dzT("son.lufs.titre",{nom:lastLufs.name?" — "+lastLufs.name:""}),
            children:dzT("son.lufs.dernier_mix",{i:Math.round(Number(lastLufs.i)*10)/10})+
              (isFinite(Number(lastLufs.tp))?dzT("son.lufs.pic_vrai",{tp:Math.round(Number(lastLufs.tp)*10)/10}):"")}):
          r.jsx("span",{className:"svm-meter","aria-hidden":!0}),
        r.jsx(SvmThemeChip,{theme:theme,setTheme:setTheme})]}),
      r.jsxs("div",{className:"svm-content",children:[
        note?r.jsx("div",{className:"svm-note",style:{marginTop:0,marginBottom:10},children:note}):null,
        center]})]})]})}

/* ═════════════════════ Écran 07 · Montage ═════════════════════ */
var SVM_DEMO_DUR=64;
function svmDemoClips(){return [
 {tr:"v2",id:"v2c1",label:"titre_intro",start:3.84,end:14.08},
 {tr:"v2",id:"v2c2",label:"glow doré",start:24.32,end:32},
 {tr:"v2",id:"v2c3",label:"logo_outro",start:49.92,end:61.44},
 {tr:"v1",id:"v1c1",label:"plan_01",start:0,end:10.88},
 {tr:"v1",id:"v1c2",label:"plan_02",start:11.2,end:21.44},
 {tr:"v1",id:"v1c3",label:"plan_03",start:21.76,end:30.72},
 {tr:"v1",id:"v1c4",label:"plan_04 · travelling",start:30.72,end:43.84,srcIn:16,srcOut:21,speed:"100 %",transition:"fade",transition_s:0.4,fx:[{n:"glow doré",c:"c3d"},{n:"grain 8 %"}]},
 {tr:"v1",id:"v1c5",label:"plan_05",start:43.84,end:55.68},
 {tr:"v1",id:"v1c6",label:"plan_06",start:56,end:63.68},
 /* text : champ CLIENT du tiroir Narration — jamais envoyé au rendu */
 {tr:"a1",id:"a1c1",label:"voice_scene_01",start:1.28,end:29.44,
  text:"Sous la surface, quelque chose remue. La marée ne demande pas la permission — elle vient, et l'abysse s'ouvre."},
 {tr:"a1",id:"a1c2",label:"voice_scene_03",start:30.72,end:56.32,
  text:"Huit bras, une seule volonté. Le prophète des profondeurs a parlé : la houle porte déjà son nom."},
 {tr:"a2",id:"a2c1",label:"abyss_theme · ducking auto",start:0,end:63.36},
 {tr:"a3",id:"a3c1",label:"impact",start:7.68,end:10.88},
 {tr:"a3",id:"a3c2",label:"vague",start:22.4,end:27.52},
 {tr:"a3",id:"a3c3",label:"glitch",start:39.68,end:43.52}]}
var SVM_TRACKS=[
 {id:"v2",name:"V2",type:"overlay/VFX",h:40,c:"--c-3d",mix:13}, /* libellé compact : tient ENTIER dans l'en-tête 88 px */
 {id:"v1",name:"V1",type:"vidéo",h:54,c:"--c-video",mix:12},
 /* pistes audio réhaussées (R2/I3) : waveforms lisibles — .svm-tl suit (312px) */
 {id:"a1",name:"A1",type:"dialogue",h:52,c:"--c-audio",mix:13},
 {id:"a2",name:"A2",type:"musique",h:48,c:"--c-text",mix:8},
 {id:"a3",name:"A3",type:"sfx",h:48,c:"--c-3d",mix:13},
 /* S1 — sous-titres. Sous les pistes audio, comme dans toutes les stations :
    l'image en haut, le son au milieu, le texte en bas. Aucun bus de mixage
    (SVM_TRACK_BUS ne la connaît pas) : son en-tête n'a donc ni M, ni S, ni
    fader — seulement le nom, le type, le « + » et le verrou. */
 {id:"s1",name:"S1",type:"sous-titres",h:44,c:"--c-text",mix:11}];
var SVM_DEMO_MIX={dialogue:-12,musique:-22,sfx:-18};
var SVM_MIX_COLORS={dialogue:"--c-audio",musique:"--c-av",sfx:"--c-3d"};
var SVM_ZOOMW=[100,150,220,320];
/* Formats de sortie : doit rester aligné sur _CANVAS (montage_service.py).
   Exposer ici une valeur absente de _CANVAS ferait retomber le rendu en
   9:16 sans le dire — c'était le cas de 4:5 avant l'audit du 06/08. */
var SVM_RATIOS=[["9:16","9:16 · vertical"],["4:5","4:5 · feed"],
                ["1:1",dzT("son.format.carre")],["16:9",dzT("son.format.paysage")]];
/* échelle visuelle commune des faders de bus (maquette : w = 78 + 3,4·(dB+12)) —
   partagée entre la rangée MIXAGE de l'inspecteur et les mini-faders d'en-tête
   de piste (R2/I1) : mêmes nombres, les deux UIs restent synchrones */
function svmMixW(db){return Math.max(8,Math.min(100,Math.round(78+3.4*(db+12))))}
function svmBusDbTxt(db){return db===0?"0 dB":"−"+Math.abs(Math.round(db))+" dB"}
function svmMixRows(mixDb){return ["dialogue","musique","sfx"].map(function(k){
  var db=Number(mixDb&&mixDb[k]!=null?mixDb[k]:SVM_DEMO_MIX[k]);
  return {name:k,dbNum:db,db:db===0?"0 dB":"−"+Math.abs(db)+" dB",
    w:svmMixW(db),c:SVM_MIX_COLORS[k]}})}

/* trous V1 (> 0,1 s entre deux clips) — hachures discrètes ; le rendu y met du noir */
function svmV1Gaps(clips,dur){
  var vs=clips.filter(function(c){return c.tr==="v1"}).slice()
    .sort(function(a,b){return a.start-b.start});
  var out=[];
  for(var i=0;i<vs.length-1;i++){var g0=vs[i].end,g1=vs[i+1].start;
    if(g1-g0>.1)out.push(r.jsx("div",{className:"svm-gap",title:dzT("son.piste.trou"),
      style:{left:g0/dur*100+"%",width:(g1-g0)/dur*100+"%"}},"g"+i+"_"+Math.round(g0*100)))}
  return out}

/* ── transitions de coupe — 7 choix (libellés FR) mappés sur les noms backend.
   montage_service ne parse que le PREMIER mot : on stocke des noms nus
   ("fade", jamais "xfade 0.4"). La transition appartient au clip de DROITE
   d'une jonction ; premier clip et jonctions avec trou : ignorées au rendu. */
var SVM_TRANS=[["cut",dzT("son.transition.coupe_seche")],["fade",dzT("son.transition.fondu")],["dissolve",dzT("son.transition.dissolution")],
 ["fadeblack",dzT("son.transition.fondu_noir")],["glitch",dzT("son.transition.pixelise")],["slide",dzT("son.transition.glissement")],["flash",dzT("son.transition.fondu_blanc")]];
function svmTransBase(t){return String(t||"cut").split(/\s+/)[0]||"cut"}
function svmTransLabel(t){var b=svmTransBase(t);
  return DzTracks.transLabel(b,SVM_TRANS,window.__dzTransCat||null)}
function svmTransS(c){return Math.min(1,Math.max(.1,Number(c&&c.transition_s)||.4))}
/* jonctions d'une piste vidéo (V1 par défaut) : deux clips consécutifs dont l'écart ≤ 0,1 s (au-delà : trou).
   t117 (plusieurs séquences) : toute piste vidéo — plein cadre ou incrustation — a ses jonctions ; le rendu les fond
   par la même loi que V1 (montage_service._jonctions). */
function svmV1Junctions(cs,tid){
  tid=tid||"v1";
  var vs=cs.filter(function(c){return c.tr===tid}).slice()
    .sort(function(a,b){return a.start-b.start});
  var out=[];
  for(var i=0;i<vs.length-1;i++){
    if(Math.abs(vs[i+1].start-vs[i].end)<=.1)
      out.push({t:(vs[i].end+vs[i+1].start)/2,left:vs[i],right:vs[i+1]})}
  return out}
function svmLeftNeighbor(cs,c){
  var best=null;
  cs.forEach(function(k){
    if(k.tr!==c.tr||k.id===c.id||k.start>=c.start)return;   /* t117 : le voisin de gauche sur la MÊME piste */
    if(Math.abs(c.start-k.end)<=.1&&(!best||k.end>best.end))best=k});
  return best}
/* clip V1 réel (src vidéo ou image) actif sous t — fin exclusive, dernier départ gagne */
function svmActiveV1(cs,t){var best=null;
  for(var i=0;i<cs.length;i++){var c=cs[i];
    if(c.tr==="v1"&&c.src&&(c.src.job_id||c.src.image)&&c.start<=t&&t<c.end&&(!best||c.start>=best.start))best=c}
  return best}
/* musique A2 réelle (bouclée au rendu) — même règle que le backend : PREMIÈRE
   occurrence a2 avec source dans l'ordre des clips ; bouclée dans les bornes de son clip,
   son fade_out = fondu de fin du clip (retours L6, 26/09/2026) */
function svmFirstA2Id(cs){for(var i=0;i<cs.length;i++){var c=cs[i];
  if(c.tr==="a2"&&c.src&&(c.src.audio||c.src.job_id))return c.id}
  return null}
function svmDbTxt(g){return g>0?"+"+g+" dB":g<0?"−"+Math.abs(g)+" dB":"0 dB"}
/* ── courbes de fondu par clip audio (R2/I4) — vocabulaire partagé backend :
   lin (défaut, afade tri), douce (hsin), expo (exp), log (log). « lin » n'est
   JAMAIS écrit sur le clip ni envoyé : payload d'avant, octet pour octet. */
var SVM_FADE_CURVES=[["lin",dzT("son.courbe.lineaire")],["douce",dzT("son.courbe.douce")],["expo","expo"],["log","log"]];
var SVM_FADE_CURVE_TT={lin:dzT("son.courbe.lineaire_aide"),
  douce:dzT("son.courbe.douce_aide"),
  expo:dzT("son.courbe.expo_aide"),
  log:dzT("son.courbe.log_aide")};
/* tracé SVG de la rampe (viewBox 0..100, y=0 plein, y=100 silence) — le
   linéaire garde la <line> historique ; approximation visuelle, le rendu
   exact vit dans ffmpeg */
function svmFadePath(curve,isIn){
  if(curve==="douce")return isIn?"M0,100 C38,100 62,0 100,0":"M0,0 C38,0 62,100 100,100";
  if(curve==="expo") return isIn?"M0,100 C70,98 92,55 100,0":"M0,0 C8,55 30,98 100,100";
  if(curve==="log")  return isIn?"M0,100 C8,45 30,2 100,0":"M0,0 C70,2 92,45 100,100";
  return null}
/* ── automation de volume par clip audio (R4) — points {t, db} posés sur le
   clip (volume_points), TOUJOURS triés par t (invariant maintenu par chaque
   mutation). t = secondes locales au clip ; le rendu multiplie l'automation
   au gain de clip × bus (contrat backend : max 12 points, db −40..+12 ;
   musique A2 bouclée : le payload convertit t en temps GLOBAL du rendu).
   L'échelle verticale mappe −40..+12 dB sur la hauteur du clip. */
var SVM_VP_MIN=-40,SVM_VP_MAX=12,SVM_VP_CAP=12;
function svmVpOf(c){return c&&Array.isArray(c.volume_points)&&c.volume_points.length?c.volume_points:null}
function svmVpSort(pts){return pts.slice().sort(function(a,b){return a.t-b.t})}
/* dB à l'instant t — interpolation linéaire en dB, miroir exact de _vp_expr
   (constante avant le premier point / après le dernier) */
function svmVpDbAt(pts,t){
  if(!pts||!pts.length)return 0;
  if(t<=pts[0].t)return pts[0].db;
  var last=pts[pts.length-1];
  if(t>=last.t)return last.db;
  for(var i=1;i<pts.length;i++){var p0=pts[i-1],p1=pts[i];
    if(t<p1.t)return p0.db+(p1.db-p0.db)*(t-p0.t)/Math.max(.001,p1.t-p0.t)}
  return last.db}
function svmVpY(db){return (SVM_VP_MAX-db)/(SVM_VP_MAX-SVM_VP_MIN)*100}
function svmVpDbTxt(db){var v=Math.round(db*10)/10;
  return (v>0?"+":v<0?"−":"")+Math.abs(v).toFixed(1)+" dB"}
/* points de la polyline (viewBox 0..100) — sans points : ligne plate au
   niveau du gain du clip (l'automation n'existe pas encore) */
function svmVpPolyPts(pts,len,gain){
  var out=[];
  function push(x2,db){
    out.push((Math.round(x2*100)/100)+","+(Math.round(svmVpY(db)*100)/100))}
  if(!pts||!pts.length){var g=Math.max(SVM_VP_MIN,Math.min(SVM_VP_MAX,gain||0));
    push(0,g);push(100,g)}
  else{push(0,pts[0].db);
    for(var i=0;i<pts.length;i++)
      push(Math.min(100,Math.max(0,pts[i].t/len*100)),pts[i].db);
    push(100,pts[pts.length-1].db)}
  return out.join(" ")}
/* ratio largeur/hauteur numérique du canvas — sert au calcul CSS du cadre
   (--svm-arw) et au choix du côté de la barre du lecteur (portrait) */
function svmRatioW(rt){var p=String(rt||"9:16").split(":"),w=Number(p[0])||9,h=Number(p[1])||16;
  return Math.round(w/h*1e4)/1e4}

/* ── densité média : waveforms audio + vignettes vidéo dans les clips ──────
   Caches au niveau module (une source n'est jamais décodée deux fois, une
   frame jamais extraite deux fois), travaux SÉQUENTIELS lancés en idle
   (requestIdleCallback, repli setTimeout 0) : aucun fetch / décodage ne
   démarre pendant un drag. Échec de décodage (codec) : silencieux. */
var SVM_TRACK_BUS={a1:"dialogue",a2:"musique",a3:"sfx"}; /* bus de mixage backend */
function svmSrcKey(s){return s?(s.job_id?"j:"+s.job_id:s.audio?"a:"+s.audio:s.image?"i:"+s.image:""):""}
function svmSrcUrl(s){return s.job_id?"/api/jobs/"+s.job_id+"/video"
  :s.audio?"/api/audio/"+encodeURIComponent(s.audio)
  :s.image?"/api/images/"+encodeURIComponent(s.image):""}
var SVM_AC=null;
function svmSharedAC(){var AC=window.AudioContext||window.webkitAudioContext;
  if(!AC)return null;
  if(!SVM_AC){try{SVM_AC=new AC()}catch(_e){return null}}
  return SVM_AC}
/* file de travaux médias — un seul à la fois, démarré hors interaction */
var SVM_MQ=[],SVM_MQ_BUSY=!1;
function svmIdle(fn){if(window.requestIdleCallback)window.requestIdleCallback(fn,{timeout:800});
  else setTimeout(fn,0)}
function svmMqKick(){if(SVM_MQ_BUSY||!SVM_MQ.length)return;SVM_MQ_BUSY=!0;
  svmIdle(function(){var job=SVM_MQ.shift(),fired=!1;
    var done=function(){if(fired)return;fired=!0;SVM_MQ_BUSY=!1;svmMqKick()};
    if(!job){done();return}
    try{job(done)}catch(_e){done()}})}
function svmMqPush(job){SVM_MQ.push(job);svmMqKick()}
/* pics par source — clé → {st:"pend"|"ok"|"err", peaks 0..1, dur, subs[]} */
var SVM_WAVES=new Map();
function svmWavePeaks(src,cb){
  var key=svmSrcKey(src);if(!key)return null;
  var e=SVM_WAVES.get(key);
  if(e&&e.st==="ok")return e;
  if(e&&e.st==="err")return null;
  if(!e){e={st:"pend",subs:[]};SVM_WAVES.set(key,e);
    svmMqPush(function(done){
      var fin=function(ok){e.st=ok?"ok":"err";
        var s=e.subs;e.subs=[];s.forEach(function(f){try{f()}catch(_e){}});done()};
      fetch(svmSrcUrl(src)).then(function(res){
        if(!res.ok)throw 0;return res.arrayBuffer()})
      .then(function(buf){var ctx=svmSharedAC();if(!ctx)throw 0;
        return ctx.decodeAudioData(buf)})
      .then(function(ab){
        /* densité ×1,3 (R2/I3) : pistes plus hautes → waveform plus définie */
        var ch=ab.getChannelData(0),
            n=Math.max(90,Math.min(900,Math.round(ab.duration*15.6))),
            bl=Math.max(1,Math.floor(ch.length/n)),peaks=new Array(n),mx=0;
        for(var i=0;i<n;i++){var v=0;
          for(var j2=i*bl,jEnd=Math.min(ch.length,(i+1)*bl);j2<jEnd;j2+=32){
            var a=Math.abs(ch[j2]);if(a>v)v=a}
          peaks[i]=v;if(v>mx)mx=v}
        if(mx)for(var k=0;k<n;k++)peaks[k]=peaks[k]/mx;
        e.peaks=peaks;e.dur=ab.duration;fin(!0)})
      .catch(function(){fin(!1)})})}
  if(cb)e.subs.push(cb);
  return null}
/* vignettes vidéo — clé "source@seconde" → dataURL jpeg (ou "err") ;
   extracteur <video> offscreen partagé, une extraction à la fois */
var SVM_THUMBS=new Map(),SVM_THUMB_SUBS=new Map(),SVM_XTR=null;
var SVM_THUMB_W=78,SVM_THUMB_H=44;
function svmThumb(src,sec,cb){
  var key=svmSrcKey(src)+"@"+sec,hit=SVM_THUMBS.get(key);
  if(hit)return hit==="err"?null:hit;
  if(SVM_THUMB_SUBS.has(key)){if(cb)SVM_THUMB_SUBS.get(key).push(cb);return null}
  SVM_THUMB_SUBS.set(key,cb?[cb]:[]);
  svmMqPush(function(done){
    var fin=function(val){SVM_THUMBS.set(key,val||"err");
      var s=SVM_THUMB_SUBS.get(key)||[];SVM_THUMB_SUBS.delete(key);
      s.forEach(function(f){try{f()}catch(_e){}});done()};
    var v=SVM_XTR;
    if(!v){v=document.createElement("video");v.muted=!0;v.playsInline=!0;
      v.preload="auto";SVM_XTR=v}
    var url=svmSrcUrl(src);
    var to=setTimeout(function(){clean();fin(null)},8000);
    function clean(){v.onloadeddata=null;v.onseeked=null;v.onerror=null;clearTimeout(to)}
    function grab(){
      try{var c=document.createElement("canvas");
        c.width=SVM_THUMB_W;c.height=SVM_THUMB_H;
        var g=c.getContext("2d"),vw=v.videoWidth||1,vh=v.videoHeight||1,
            sc=Math.max(SVM_THUMB_W/vw,SVM_THUMB_H/vh),dw=vw*sc,dh=vh*sc;
        g.drawImage(v,(SVM_THUMB_W-dw)/2,(SVM_THUMB_H-dh)/2,dw,dh);
        clean();fin(c.toDataURL("image/jpeg",.6))}
      catch(_e){clean();fin(null)}}
    function ready(){
      var t=Math.min(Math.max(0,sec),Math.max(0,(v.duration||1)-.05));
      if(v.readyState>=2&&Math.abs(v.currentTime-t)<.02){grab();return}
      v.onseeked=grab;
      try{v.currentTime=t}catch(_e){clean();fin(null)}}
    v.onerror=function(){clean();fin(null)};
    if(v._svmUrl===url&&v.readyState>=2)ready();
    else{v._svmUrl=url;v.onloadeddata=ready;v.src=url;try{v.load()}catch(_e){}}})}
/* canvas waveform d'un clip audio — les pics affichés = fenêtre
   srcIn..srcIn+len de la source, à l'échelle du clip */
function SvmWave(props){
  var cv=x.useRef(null),st=x.useState(0),wtick=st[0],setWt=st[1];
  x.useEffect(function(){
    var alive=!0,c=cv.current;
    var e=svmWavePeaks(props.src,function(){if(alive)setWt(function(t){return t+1})});
    if(!c)return function(){alive=!1};
    var g=c.getContext("2d");
    if(!g)return function(){alive=!1};
    if(!e){if(c.width)g.clearRect(0,0,c.width,c.height);return function(){alive=!1}}
    var w=c.clientWidth,h=c.clientHeight;
    if(!w||!h)return function(){alive=!1};
    var dpr=Math.min(2,window.devicePixelRatio||1),
        W=Math.max(1,Math.round(w*dpr)),H=Math.max(1,Math.round(h*dpr));
    if(c.width!==W)c.width=W;
    if(c.height!==H)c.height=H;
    g.clearRect(0,0,W,H);
    var col=(getComputedStyle(c).getPropertyValue(props.color)||"").trim()||"#7fb069";
    g.fillStyle=col;g.globalAlpha=.55;
    var bw=Math.max(1,Math.round(1.5*dpr)),gap=Math.max(1,Math.round(dpr)),
        n=Math.max(1,Math.floor(W/(bw+gap))),
        sd=e.dur||1,pk=e.peaks,len=Math.max(.01,props.len),s0=props.srcIn||0;
    for(var i=0;i<n;i++){
      var t0=s0+i/n*len,t1=s0+(i+1)/n*len,
          p0=Math.max(0,Math.floor(t0/sd*pk.length)),
          p1=Math.min(pk.length,Math.max(p0+1,Math.ceil(t1/sd*pk.length))),v=0;
      for(var j2=p0;j2<p1;j2++){if(pk[j2]>v)v=pk[j2]}
      var bh=Math.max(dpr,v*H*.92);
      g.fillRect(i*(bw+gap),(H-bh)/2,bw,bh)}
    return function(){alive=!1}},
    [props.k,props.srcIn,props.len,props.color,props.theme,props.zoom,props.dur,wtick]);
  return r.jsx("canvas",{className:"svm-clipwave","aria-hidden":!0,ref:cv})}
/* filmstrip d'un clip V1 vidéo — une vignette ≈ toutes les 2,5 s de durée
   AFFICHÉE (cap 12), générées en asynchrone via la file idle */
function SvmFilmstrip(props){
  var st=x.useState(0),setFt=st[1];
  var len=Math.max(.1,props.len),
      n=Math.max(1,Math.min(12,Math.ceil(len/2.5))),
      secs=[],i;
  for(i=0;i<n;i++)secs.push(Math.max(0,Math.round((props.srcIn||0)+(i+.5)*len/n)));
  var sig=secs.join(",");
  x.useEffect(function(){
    var alive=!0;
    /* extraction différée : rien ne part pendant un drag (200 ms de stabilité) */
    var t=setTimeout(function(){if(!alive)return;
      secs.forEach(function(s2){
        svmThumb(props.src,s2,function(){if(alive)setFt(function(t2){return t2+1})})})},200);
    return function(){alive=!1;clearTimeout(t)}},[props.k,sig]);
  return r.jsx("div",{className:"svm-strip","aria-hidden":!0,children:
    secs.map(function(s2,i2){
      var d=SVM_THUMBS.get(svmSrcKey(props.src)+"@"+s2);
      return d&&d!=="err"?r.jsx("img",{className:"svm-stripimg",src:d,alt:"",draggable:!1},i2)
        :r.jsx("span",{className:"svm-stripimg"},i2)})})}

/* ── overlays transformables (V2) — x/y : centre en fraction du canvas,
   scale : largeur relative au canvas (hauteur auto, ratio source), rotate :
   degrés. AUCUN champ posé sur le clip → null : l'overlay reste plein cadre
   (cover), lecteur, payload et rendu strictement identiques à avant. */
function svmOvTfOf(c){
  /* L7 D-19 (24/09/2026) : un rayon > 0 ou une ombre matérialisent aussi l'état « transformé » — le rendu fait de même
     (plein cadre par défaut) ; la couche borne les deux (entier 0..200, 0|1) */
  var ex=DzTracks.ovExtra(c);
  if(!c||(c.x==null&&c.y==null&&c.scale==null&&c.rotate==null&&!ex.radius&&!ex.shadow))return null;
  function n(v,d){v=Number(v);return isFinite(v)?v:d}
  return {x:Math.min(1.2,Math.max(-.2,n(c.x,.5))),
          y:Math.min(1.2,Math.max(-.2,n(c.y,.5))),
          scale:Math.min(3,Math.max(.05,n(c.scale,1))),
          rotate:Math.min(180,Math.max(-180,n(c.rotate,0))),
          radius:ex.radius,shadow:ex.shadow}}
/* application impérative sur une couche live — même géométrie que le rendu
   ffmpeg : largeur = scale·canvas, hauteur auto, centre posé en left/top %,
   rotation autour du centre ; tf null = retour au cover plein cadre */
function svmApplyTf(el,tf){
  if(tf){el.setAttribute("data-svmtf","");
    el.style.left=tf.x*100+"%";el.style.top=tf.y*100+"%";
    el.style.width=tf.scale*100+"%";
    el.style.transform="translate(-50%,-50%) rotate("+tf.rotate+"deg)";
    /* L7 D-19 : coins et ombre de l'aperçu — le rayon (px d'un canvas de 1920 de large en paysage, 1080 sinon) est ramené
       à l'échelle affichée par la largeur du cadre ; cadre non mesurable (volet caché) : rayon brut, aperçu approximatif */
    var rad=tf.radius||0,pe=el.parentElement,pw=pe?pe.clientWidth:0,pk=pw>0?pw/(pw>pe.clientHeight?1920:1080):1;
    el.style.borderRadius=rad>0?Math.round(rad*pk*100)/100+"px":"";
    el.style.boxShadow=tf.shadow?"6px 6px 12px rgba(0,0,0,.55)":""}
  else{el.removeAttribute("data-svmtf");
    el.style.left="";el.style.top="";el.style.width="";el.style.transform="";
    el.style.borderRadius="";el.style.boxShadow=""}}
/* ── keyframes de position d'un overlay V2 (R4b) — points {t local 0..durée,
   x, y, rotate?} posés sur le clip (motion_points), TOUJOURS triés par t
   (invariant maintenu par chaque mutation). Contrat backend : max 8 points,
   x/y/rotate mêmes clamps que la transformation, interpolation LINÉAIRE par
   morceaux (avant premier = premier, après dernier = dernier) ; l'ÉCHELLE ne
   se keyframe pas (largeur figée — l'inspecteur le dit). ── */
var SVM_MP_CAP=8,SVM_MP_EPS=.15; /* cap backend · rayon « point le plus proche » (s) */
function svmMpOf(c){return c&&Array.isArray(c.motion_points)&&c.motion_points.length?c.motion_points:null}
function svmMpSort(pts){return pts.slice().sort(function(a,b){return a.t-b.t})}
/* valeur d'une clé (x / y / rotate) à t local — lerp sur le sous-ensemble des
   points qui la portent (miroir exact du backend : rotate peut manquer) ;
   aucun point ne la porte → null, l'appelant retombe sur le statique */
function svmMpLerp(pts,tl,key){
  var ps=[],i,v;
  for(i=0;i<pts.length;i++){v=Number(pts[i][key]);
    if(pts[i][key]!=null&&isFinite(v))ps.push({t:pts[i].t,v:v})}
  if(!ps.length)return null;
  if(tl<=ps[0].t)return ps[0].v;
  var last=ps[ps.length-1];
  if(tl>=last.t)return last.v;
  for(i=1;i<ps.length;i++){var p0=ps[i-1],p1=ps[i];
    if(tl<p1.t)return p0.v+(p1.v-p0.v)*(tl-p0.t)/Math.max(.001,p1.t-p0.t)}
  return last.v}
/* transformation EFFECTIVE d'un overlay à l'instant global t : sans point,
   la statique de svmOvTfOf (null compris — cover intact) ; avec des points,
   x/y/rotate interpolés à t−start, scale toujours statique. Source unique du
   lecteur (liveSync), du cadre de sélection et de l'inspecteur. */
function svmOvTfAt(c,t){
  var tf=svmOvTfOf(c),mp=svmMpOf(c);
  if(!mp)return tf;
  var base=tf||{x:.5,y:.5,scale:1,rotate:0};
  var tl=t-c.start;
  var mx=svmMpLerp(mp,tl,"x"),my=svmMpLerp(mp,tl,"y"),mr=svmMpLerp(mp,tl,"rotate");
  return {x:mx==null?base.x:Math.min(1.2,Math.max(-.2,mx)),
          y:my==null?base.y:Math.min(1.2,Math.max(-.2,my)),
          scale:DzTracks.mpLerp2(mp,tl,"scale",base.scale),
          rotate:mr==null?base.rotate:Math.min(180,Math.max(-180,mr)),
          /* L7 D-19 : coins et ombre restent la statique — jamais keyframés */
          radius:base.radius||0,shadow:base.shadow||0}}

/* ── raccourcis clavier — actions NOMMÉES et REMAPPABLES (R4c) ─────────────
   Chaque action : id stable, libellé FR, section, combo par défaut. La table
   couvre TOUT ce que le clavier de l'éditeur sait faire — un raccourci qui
   n'y figure pas n'existe pas. Sérialisation déterministe d'une combo :
   « Ctrl+Alt+Maj+Touche » (Meta compté comme Ctrl), lettres via e.key
   (AZERTY-fiable), repli e.code UNIQUEMENT quand Alt déforme la frappe
   (ç, touches mortes — la règle historique de la lame). Overrides persistés
   dans dz_svm_keymap (JSON {actionId: combo}), fusionnés aux défauts au
   chargement ; entrées invalides, réservées ou en conflit : ignorées. */
var SVM_ACTIONS=[
 {id:"play",sec:"Lecture",lbl:dzT("son.raccourci.play"),combo:"Espace"},
 {id:"jog_back",sec:"Lecture",lbl:dzT("son.raccourci.jog_back"),combo:"J"},
 {id:"jog_pause",sec:"Lecture",lbl:dzT("son.raccourci.jog_pause"),combo:"K"},
 {id:"jog_fwd",sec:"Lecture",lbl:dzT("son.raccourci.jog_fwd"),combo:"L"},
 {id:"step_back",sec:"Lecture",lbl:dzT("son.raccourci.step_back"),combo:"←"},
 {id:"step_fwd",sec:"Lecture",lbl:dzT("son.raccourci.step_fwd"),combo:"→"},
 {id:"cut_prev",sec:"Lecture",lbl:dzT("son.raccourci.cut_prev"),combo:"↑"},
 {id:"cut_next",sec:"Lecture",lbl:dzT("son.raccourci.cut_next"),combo:"↓"},
 {id:"home",sec:"Lecture",lbl:dzT("son.raccourci.home"),combo:"Home"},
 {id:"end",sec:"Lecture",lbl:dzT("son.raccourci.end"),combo:"End"},
 {id:"fullscreen",sec:"Lecture",lbl:dzT("son.raccourci.fullscreen"),combo:"F"},
 {id:"safezones",sec:"Lecture",lbl:dzT("son.raccourci.safezones"),combo:"G"},
 {id:"delete",sec:"Montage",lbl:dzT("son.raccourci.delete"),combo:"Suppr"},
 {id:"blade",sec:"Montage",lbl:dzT("son.raccourci.blade"),combo:"Alt+C"},
 {id:"undo",sec:"Montage",lbl:dzT("son.raccourci.undo"),combo:"Ctrl+Z"},
 {id:"redo",sec:"Montage",lbl:dzT("son.raccourci.redo"),combo:"Ctrl+Y"},
 {id:"snap",sec:"Montage",lbl:dzT("son.raccourci.snap"),combo:"N"},
 {id:"ripple",sec:"Montage",lbl:dzT("son.raccourci.ripple"),combo:"R"},
 {id:"range_in",sec:"Montage",lbl:dzT("son.raccourci.range_in"),combo:"I"},
 {id:"range_out",sec:"Montage",lbl:dzT("son.raccourci.range_out"),combo:"U"},
 {id:"range_clear",sec:"Montage",lbl:dzT("son.raccourci.range_clear"),combo:"X"},
 {id:"range_cut",sec:"Montage",lbl:dzT("son.raccourci.range_cut"),combo:"Maj+X"},
 {id:"marker_toggle",sec:"Montage",lbl:dzT("son.raccourci.marker_toggle"),combo:"Maj+M"},
 {id:"marker_prev",sec:"Montage",lbl:dzT("son.raccourci.marker_prev"),combo:"Ctrl+↑"},
 {id:"marker_next",sec:"Montage",lbl:dzT("son.raccourci.marker_next"),combo:"Ctrl+↓"},
 {id:"marker_index",sec:"Montage",lbl:dzT("son.raccourci.marker_index"),combo:"Ctrl+M"},
 {id:"swap_left",sec:"Montage",lbl:dzT("son.raccourci.swap_left"),combo:"Ctrl+←"},
 {id:"swap_right",sec:"Montage",lbl:dzT("son.raccourci.swap_right"),combo:"Ctrl+→"},
 {id:"title_add",sec:"Montage",lbl:dzT("son.raccourci.title_add"),combo:"Maj+T"},
 {id:"adjust_add",sec:"Montage",lbl:dzT("son.raccourci.adjust_add"),combo:"Maj+J"},
 {id:"trans_add",sec:"Montage",lbl:dzT("son.raccourci.trans_add"),combo:"Alt+T"},
 {id:"copy",sec:"Montage",lbl:dzT("son.raccourci.copy"),combo:"Ctrl+C"},
 {id:"paste",sec:"Montage",lbl:dzT("son.raccourci.paste"),combo:"Ctrl+V"},
 {id:"grade_copy",sec:"Montage",lbl:dzT("son.raccourci.grade_copy"),combo:"Ctrl+Alt+C"},
 {id:"grade_paste",sec:"Montage",lbl:dzT("son.raccourci.grade_paste"),combo:"Ctrl+Alt+V"},
 {id:"vo_record",sec:"Audio",lbl:dzT("son.raccourci.vo_record"),combo:"Alt+R"},
 {id:"zoom_in",sec:"Affichage",lbl:dzT("son.raccourci.zoom_in"),combo:"Ctrl+="},
 {id:"zoom_out",sec:"Affichage",lbl:dzT("son.raccourci.zoom_out"),combo:"Ctrl+-"},
 {id:"zoom100",sec:"Affichage",lbl:"zoom 100 %",combo:"Maj+Z"},
 {id:"narration",sec:"Affichage",lbl:dzT("son.raccourci.narration"),combo:"T"},
 {id:"toolbar",sec:"Affichage",lbl:dzT("son.raccourci.toolbar"),combo:"O"},
 {id:"keys_panel",sec:"Affichage",lbl:dzT("son.raccourci.keys_panel"),combo:"?"},
 /* la ligne « tiroir Sons » n'est AFFICHÉE par kbPanel que si la couche
    DzSfx est chargée (le panneau ne promet jamais un raccourci mort) — mais
    sa combo reste réservée dans la keymap : la couche peut se charger */
 {id:"sounds_drawer",sec:"Audio",lbl:dzT("son.raccourci.sounds_drawer"),combo:"B"},
 {id:"mute",sec:"Audio",lbl:dzT("son.raccourci.mute"),combo:"M"},
 {id:"solo",sec:"Audio",lbl:dzT("son.raccourci.solo"),combo:"S"},
 {id:"fade_in_cycle",sec:"Audio",lbl:dzT("son.raccourci.fade_in_cycle"),combo:"D"},
 {id:"fade_out_cycle",sec:"Audio",lbl:dzT("son.raccourci.fade_out_cycle"),combo:"Maj+D"},
 {id:"nudge_left",sec:"Audio",lbl:dzT("son.raccourci.nudge_left"),combo:"Alt+←"},
 {id:"nudge_right",sec:"Audio",lbl:dzT("son.raccourci.nudge_right"),combo:"Alt+→"},
 {id:"gain_up",sec:"Audio",lbl:dzT("son.raccourci.gain_up"),combo:"Alt+↑"},
 {id:"gain_down",sec:"Audio",lbl:dzT("son.raccourci.gain_down"),combo:"Alt+↓"}];
var SVM_ACTION_BY_ID={};
SVM_ACTIONS.forEach(function(a){SVM_ACTION_BY_ID[a.id]=a});
var SVM_KEY_SECTIONS=["Lecture","Montage","Affichage","Audio"];
/* rappels NON remappables du panneau — gestes souris et touche fixe, assumés
   tels ; acts : chips dynamiques (les combos VIVANTES des actions citées) */
var SVM_KEYS_INFO=[
 {sec:"Montage",keys:[dzT("son.raccourci.info_bord")],lbl:dzT("son.raccourci.info_rogner")},
 {sec:"Montage",acts:["step_back","step_fwd","cut_prev","cut_next"],
  lbl:dzT("son.raccourci.info_overlay")},
 {sec:"Affichage",keys:["Ctrl",dzT("son.raccourci.info_molette")],lbl:dzT("son.raccourci.info_zoom")},
 {sec:"Affichage",keys:["Échap"],lbl:dzT("son.raccourci.info_echap")}];
/* variantes Maj DÉRIVÉES : sans correspondance exacte, Maj+X retombe sur
   l'action de X pour ces ids (mag=vrai → ±10 images, nudge ×10, multi-solo,
   overlay ±2 %) — les autres restent stricts ; Ctrl+Maj+<annuler> = rétablir
   est traité à part (remappage suivi). */
var SVM_SHIFT_VARIANTS={play:1,step_back:1,step_fwd:1,cut_prev:1,cut_next:1,
  home:1,end:1,"delete":1,blade:1,solo:1,nudge_left:1,nudge_right:1,
  gain_up:1,gain_down:1};
/* touches nommées : e.key → nom canonique FR ; Maj n'est conservé dans la
   combo QUE pour les lettres et ces touches nommées — la ponctuation et les
   chiffres encodent déjà leur Maj dans le caractère (« ? » AZERTY). */
var SVM_EV_NAMES={" ":"Espace",Spacebar:"Espace",ArrowLeft:"←",ArrowRight:"→",
  ArrowUp:"↑",ArrowDown:"↓",Delete:"Suppr",Backspace:"Suppr",Home:"Home",
  End:"End",Enter:"Entrée",Escape:"Échap",Tab:"Tab"};
var SVM_EV_NAMED_SET={Espace:1,"←":1,"→":1,"↑":1,"↓":1,Suppr:1,Home:1,End:1,
  "Entrée":1,"Échap":1,Tab:1};
function svmComboOfEvent(e){
  var k=e.key,name="";
  if(k&&SVM_EV_NAMES[k])name=SVM_EV_NAMES[k];
  else if(e.code==="Space")name="Espace";
  else if(typeof k==="string"&&/^F\d{1,2}$/.test(k))name=k;
  else if(typeof k==="string"&&k.length===1){
    name=k.toUpperCase();
    if(name==="+")name="=";
    if(name==="_")name="-"}
  var isLet=name.length===1&&name>="A"&&name<="Z";
  /* Alt déforme la frappe (ç, ¬, touches mortes) : lettre PHYSIQUE du code
     — même repli que le raccourci lame historique (e.code==="KeyC") */
  if(e.altKey&&!isLet&&/^Key[A-Z]$/.test(e.code||"")){
    name=e.code.charAt(3);isLet=!0}
  if(!name)return "";
  var keepMaj=isLet||SVM_EV_NAMED_SET[name]||/^F\d{1,2}$/.test(name);
  return (e.ctrlKey||e.metaKey?"Ctrl+":"")+(e.altKey?"Alt+":"")+
         (e.shiftKey&&keepMaj?"Maj+":"")+name}
/* canonisation d'une combo STOCKÉE (dz_svm_keymap édité à la main compris) —
   insensible à la casse et aux accents, retourne "" si inconnue */
var SVM_COMBO_WORDS={espace:"Espace",space:"Espace",suppr:"Suppr",del:"Suppr",
  "delete":"Suppr",home:"Home",end:"End",entree:"Entrée",enter:"Entrée",
  echap:"Échap",escape:"Échap",tab:"Tab"};
function svmComboCanon(s){
  if(typeof s!=="string"||!s||s.length>40)return "";
  var parts=s.split("+"),ctrl=0,alt=0,maj=0,name="",i,p,pl;
  for(i=0;i<parts.length;i++){p=parts[i];pl=svmNorm(p);
    if(pl==="ctrl"||pl==="control"||pl==="cmd"||pl==="meta")ctrl=1;
    else if(pl==="alt"||pl==="option")alt=1;
    else if(pl==="maj"||pl==="shift")maj=1;
    else if(name)return "";
    else if(p.length===1)name=p.toUpperCase();
    else if(SVM_COMBO_WORDS[pl])name=SVM_COMBO_WORDS[pl];
    else if(/^f\d{1,2}$/.test(pl))name=p.toUpperCase();
    else return ""}
  if(!name)return "";
  if(name==="+")name="=";
  if(name==="_")name="-";
  var isLet=name.length===1&&name>="A"&&name<="Z";
  var keepMaj=isLet||SVM_EV_NAMED_SET[name]||/^F\d{1,2}$/.test(name);
  return (ctrl?"Ctrl+":"")+(alt?"Alt+":"")+(maj&&keepMaj?"Maj+":"")+name}
/* combos refusées à l'enregistrement — le navigateur les garde (raison
   affichée inline, jamais d'écrasement silencieux) */
var SVM_COMBO_RESERVED={"Ctrl+R":1,"Ctrl+Maj+R":1,"Ctrl+W":1,"Ctrl+Maj+W":1,
  "Ctrl+T":1,"Ctrl+Maj+T":1,"Ctrl+N":1,"Ctrl+Maj+N":1,"Ctrl+Tab":1,
  "Ctrl+Maj+Tab":1,"Ctrl+Maj+I":1,"Ctrl+Maj+J":1,"Ctrl+Maj+C":1,"Alt+F4":1};
function svmComboReserved(c){
  if(SVM_COMBO_RESERVED[c])return dzT("son.raccourci.reserve_navigateur");
  var kk=c.split("+").pop();
  if(/^F\d{1,2}$/.test(kk))return dzT("son.raccourci.reserve_touches_f");
  if(kk==="Échap")return dzT("son.raccourci.reserve_echap");
  if(kk==="Tab")return dzT("son.raccourci.reserve_tab");
  if(kk==="Entrée"&&c==="Entrée")return dzT("son.raccourci.reserve_entree");
  return ""}
/* overrides persistés — lecture assainie (id connu, combo canonisable, non
   réservée, différente du défaut) ; écriture : objet vide → clé retirée */
function svmKmLoad(){
  var out={};
  try{
    var raw=JSON.parse(localStorage.getItem("dz_svm_keymap")||"null");
    if(raw&&typeof raw==="object"&&!Array.isArray(raw))
      Object.keys(raw).forEach(function(id){
        if(!SVM_ACTION_BY_ID[id])return;
        var c=svmComboCanon(raw[id]);
        if(!c||svmComboReserved(c))return;
        if(c!==SVM_ACTION_BY_ID[id].combo)out[id]=c})}
  catch(_e){}
  return out}
function svmKmSave(ov){
  try{
    if(Object.keys(ov).length)localStorage.setItem("dz_svm_keymap",JSON.stringify(ov));
    else localStorage.removeItem("dz_svm_keymap")}
  catch(_e){}}
/* fusion défauts + overrides → {byId: action→combo, toAct: combo→action}.
   Une action remappée LIBÈRE son défaut avant le contrôle de collision — un
   échange légal fait dans l'UI (solo→X puis muet→S) survit au rechargement ;
   un override qui vole la touche d'une action NON remappée (données
   manipulées hors UI) est ignoré, ordre de table, déterministe. */
function svmKmMerge(ov){
  var byId={},used={},i,a,c;
  /* touches occupées par les défauts des actions SANS override */
  for(i=0;i<SVM_ACTIONS.length;i++){a=SVM_ACTIONS[i];
    if(!ov[a.id]&&!used[a.combo])used[a.combo]=a.id}
  /* overrides en ordre de table — collision : ignoré (retour au défaut) */
  for(i=0;i<SVM_ACTIONS.length;i++){a=SVM_ACTIONS[i];c=ov[a.id];
    if(c&&!used[c]){byId[a.id]=c;used[c]=a.id}}
  for(i=0;i<SVM_ACTIONS.length;i++){a=SVM_ACTIONS[i];
    if(!byId[a.id])byId[a.id]=a.combo}
  var toAct={};
  for(i=0;i<SVM_ACTIONS.length;i++){a=SVM_ACTIONS[i];
    if(toAct[byId[a.id]]==null)toAct[byId[a.id]]=a.id}
  return {byId:byId,toAct:toAct}}
/* libellé de combo HORS DzMontage (écran Son & VFX) — instantané relu au
   rendu depuis le stockage : les textes qui citent un raccourci du Montage
   suivent le remappage sans état partagé. Cache sur la chaîne brute : la
   fusion ne se recalcule qu'au changement réel (l'écran 06 re-rend par
   frame pendant une écoute — rien de coûteux ici). */
var SVM_KMNOW_CACHE={raw:void 0,byId:null};
function svmKeyLabelNow(id){
  var raw=null;
  try{raw=localStorage.getItem("dz_svm_keymap")}catch(_e){}
  if(SVM_KMNOW_CACHE.byId==null||SVM_KMNOW_CACHE.raw!==raw){
    SVM_KMNOW_CACHE.raw=raw;
    SVM_KMNOW_CACHE.byId=svmKmMerge(svmKmLoad()).byId}
  return SVM_KMNOW_CACHE.byId[id]||""}

function DzMontage(props){
  var th=svmUseTheme(),theme=th[0],setTheme=th[1];
  var st1=x.useState(svmDemoClips),clips=st1[0],setClips=st1[1];
  var st2=x.useState("v1c4"),selId=st2[0],setSelId=st2[1];
  var st3=x.useState(18.4),ph=st3[0],setPh=st3[1];
  var st4=x.useState(!1),playing=st4[0],setPlaying=st4[1];
  var st5=x.useState(SVM_ZOOMW[0]),zoomPct=st5[0],setZoomPct=st5[1]; /* zoom continu 100..800 % (SVM_ZOOMW = presets) */
  var st6=x.useState(!0),snap=st6[0],setSnap=st6[1];
  var st7=x.useState(!1),ripple=st7[0],setRipple=st7[1];
  var stSL=x.useState(null),snapT=stSL[0],setSnapT=stSL[1]; /* temps (s) où l'aimant accroche pendant un drag */
  var st8=x.useState(!0),dirty=st8[0],setDirty=st8[1];
  var st9=x.useState(!0),durMaster=st9[0],setDurMaster=st9[1];
  var stDk=x.useState(!0),ducking=stDk[0],setDucking=stDk[1];
  var stA=x.useState(""),pop=stA[0],setPop=stA[1];
  /* E-8 : l'inspecteur — ouvert ? largeur 260–480 (mémoire dz_svm_insp) */
  var stIn=x.useState(function(){try{var s=JSON.parse(localStorage.getItem("dz_svm_insp")||"{}")||{};return{on:s.on!==!1,w:DzTracks.inspW(s.w)}}catch(_e){return{on:!0,w:300}}}),inspSt=stIn[0],setInspSt=stIn[1],inspOn=inspSt.on,inspW=inspSt.w;
  function inspDown(e){if(e.button!==0)return;e.preventDefault();
    var sx=e.clientX,sw=inspW,w=window,last=sw;
    function mv(ev){last=DzTracks.inspW(sw+(sx-ev.clientX));setInspSt({on:!0,w:last})}
    function up(){w.removeEventListener("pointermove",mv);w.removeEventListener("pointerup",up);w.removeEventListener("pointercancel",up);
      try{localStorage.setItem("dz_svm_insp",JSON.stringify({on:!0,w:last}))}catch(_e){}}
    w.addEventListener("pointermove",mv);w.addEventListener("pointerup",up);w.addEventListener("pointercancel",up)}
  /* E-9 : la timeline — hauteur choisie (dz_svm_tlh, 30–70 % de .dzsvm) et durées sur les clips (dz_svm_showdur) */
  var stTl=x.useState(function(){try{var v=Number(localStorage.getItem("dz_svm_tlh"));return v>0?v:null}catch(_e){return null}}),tlH=stTl[0],setTlH=stTl[1];
  x.useEffect(function(){var el=document.querySelector(".dzsvm");if(el&&tlH!=null)setTlH(DzTracks.tlH(tlH,el.clientHeight))},[]);
  var stSd=x.useState(function(){try{return localStorage.getItem("dz_svm_showdur")==="1"}catch(_e){return !1}}),showDur=stSd[0],setShowDur=stSd[1];
  function tlDown(e){if(e.button!==0)return;e.preventDefault();
    var sy=e.clientY,el=document.querySelector(".dzsvm"),total=el?el.clientHeight:0,tl=e.currentTarget.nextElementSibling,sh=tlH||(tl?tl.offsetHeight:0),w=window,last=tlH;
    function mv(ev){last=DzTracks.tlH(sh+(sy-ev.clientY),total);setTlH(last)}
    function up(){w.removeEventListener("pointermove",mv);w.removeEventListener("pointerup",up);w.removeEventListener("pointercancel",up);
      try{if(last!=null)localStorage.setItem("dz_svm_tlh",String(last))}catch(_e){}}
    w.addEventListener("pointermove",mv);w.addEventListener("pointerup",up);w.addEventListener("pointercancel",up)}
  /* L7 D-8 (24/09/2026, tâche 3) : le boring detector — réglages {on,maxS,minFrames} (mémoire dz_svm_boring,
     défaut boringDef de la couche, éteint) et la carte id → "long"|"jump" de V1, mémoïsée sur [clips,bo], vide si éteint */
  var stBo=x.useState(function(){var d=Object.assign({on:!1},DzTracks.boringDef);try{return Object.assign(d,JSON.parse(localStorage.getItem("dz_svm_boring")||"{}")||{})}catch(_e){return d}}),bo=stBo[0],setBo=stBo[1];
  var boMap=x.useMemo(function(){return bo.on?DzTracks.boring(clips,bo):{}},[clips,bo]);
  /* L7 D-39 (24/09/2026, tâche 4) : la dernière comparaison {diff,nomA,nomB} — posée par « ⇄ » (Projets), montrée par pop==="diff" */
  var stDf=x.useState(null),diffSt=stDf[0],setDiffSt=stDf[1];
  /* L7 D-3b (24/09/2026, tâche 4-bis) : les vignettes A/B de la jonction en édition — {a,b : image ou null, k : clé « source@seconde|source@seconde »} */
  var stAb=x.useState({a:null,b:null,k:""}),abSt=stAb[0],setAbSt=stAb[1];
  var stP=x.useState({demo:!0,name:"teaser_abyss",version:"v4",ratio:"9:16",dur:SVM_DEMO_DUR,mixDb:SVM_DEMO_MIX}),proj=stP[0],setProj=stP[1];
  var stJ=x.useState(null),job=stJ[0],setJob=stJ[1]; /* {id,kind,status,progress,step,error} */
  var stV=x.useState(null),previewUrl=stV[0],setPreviewUrl=stV[1];
  var stVS=x.useState(null),prevSaved=stVS[0],setPrevSaved=stVS[1]; /* dernier aperçu 480p rendu — chip qualité source/480p */
  var stF=x.useState(null),fxCat=stF[0],setFxCat=stF[1]; /* catalogue Effects/Mask */
  var stFP=x.useState(!1),fxPick=stFP[0],setFxPick=stFP[1];
  var stFE=x.useState(null),fxEdit=stFE[0],setFxEdit=stFE[1]; /* {id,i} chip en édition */
  var stMed=x.useState(!1),medOn=stMed[0],setMedOn=stMed[1]; /* E-2 : tiroir Médias (rendus vidéo) ouvert */
  var stMT=x.useState(""),medTr=stMT[0],setMedTr=stMT[1]; /* "" = ouvert par la chip, sinon la piste vidéo dont le « + » a ouvert le tiroir */
  var stO=x.useState(""),ovPick=stO[0],setOvPick=stO[1]; /* "" = fermé, sinon l'id de la piste visée */
  var stS=x.useState(null),sources=stS[0],setSources=stS[1]; /* {images,videos} pour overlays */
  var stVZ=x.useState(1),vzoom=stVZ[0],setVzoom=stVZ[1]; /* zoom molette du viewport (≠ zoom timeline) */
  var ovSeq=x.useRef(0);
  var stTP=x.useState(null),transPop=stTP[0],setTransPop=stTP[1]; /* jonction en édition — {id: clip de DROITE, x: px du popover} */
  var stKb=x.useState(!1),kbOn=stKb[0],setKbOn=stKb[1]; /* panneau « Raccourcis clavier » (?) */
  var kbRef=x.useRef(kbOn);kbRef.current=kbOn;
  var vuRef=x.useRef(null); /* canvas du vu-mètre live (rangée MIXAGE) */
  var rootRef=x.useRef(null),transHistAt=x.useRef(0),audioHistAt=x.useRef(0);
  var nt=svmUseNote(),note=nt[0],fireNote=nt[1];
  var rafRef=x.useRef(0),phRef=x.useRef(ph);phRef.current=ph;
  var clipsRef=x.useRef(clips);clipsRef.current=clips;
  var selRef=x.useRef(selId);selRef.current=selId;
  var durRef=x.useRef(proj.dur);durRef.current=proj.dur;
  /* P9 — les PISTES du projet, relues à chaque rendu, pour que
     `addAsset` ne décide jamais sur un `proj` périmé (le greffon
     « Envoyer vers → Montage » l'appelle depuis la fermeture du
     premier rendu). Même motif que durRef, juste au-dessus. */
  var dzTracksRef=x.useRef(null);dzTracksRef.current=svmTracksOf(proj);
  var dzPlanHist=x.useRef(0);
  function dzPlanSet(patch,heavy){var tl=trackStRef.current.v1;if(tl&&tl.l)return;
    var id=selRef.current,now=Date.now();
    if(heavy||now-dzPlanHist.current>600)pushHistory();dzPlanHist.current=now;
    setClips(clipsRef.current.map(function(k){if(k.id!==id)return k;var nk=Object.assign({},k,patch);
      Object.keys(patch).forEach(function(q){if(patch[q]===void 0)delete nk[q]});return nk}));setDirty(!0)}
  var stDzStab=x.useState({}),dzStabJobs=stDzStab[0],setDzStabJobs=stDzStab[1];
  function dzStabStart(src){var key=DzTracks.srcKey(src);
    var put=function(v){if(dzAliveRef.current)setDzStabJobs(function(m){var n=Object.assign({},m);n[key]=v;return n})};
    var tick=function(id){fetch("/api/jobs/"+id).then(function(r3){return r3.json()}).then(function(j){
      var st=j&&j.status;if(!st)return put({status:"failed",error:(j&&j.detail)||dzT("montage.stab.job_introuvable")});
      var fin=st==="done"||st==="failed";put({status:fin?st:"running",progress:Number(j.progress)||0,error:j.error||null});
      if(!fin&&dzAliveRef.current)setTimeout(function(){tick(id)},1500)})
      .catch(function(e){put({status:"failed",error:String(e)})})};
    put({status:"running",progress:0});
    fetch("/api/montage/stab",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({src:src})})
      .then(function(r2){return r2.json().then(function(d){return {ok:r2.ok,d:d}})}).then(function(o){
        if(o.ok&&o.d&&o.d.ready)return put({status:"done"});
        if(!o.ok||!o.d||!o.d.job_id)return put({status:"failed",error:(o.d&&(o.d.detail||o.d.error))||"refus"});
        put({status:"running",progress:10});tick(o.d.job_id)})
      .catch(function(e){put({status:"failed",error:String(e)})})}
  var stDzFin=x.useState(null),dzFin=stDzFin[0],setDzFin=stDzFin[1];
  var stMn=x.useState(null),dzMenu=stMn[0],setDzMenu=stMn[1];
  var dzScrimRef=x.useRef(!1);dzScrimRef.current=!!(pop||dzFin||dzMenu);
  var stGap=x.useState(null),gapSel=stGap[0],setGapSel=stGap[1];
  var gapSelRef=x.useRef(null);gapSelRef.current=gapSel;
  var stLb=x.useState(!1),dzLb=stLb[0],setDzLb=stLb[1];
  var dzLbRef=x.useRef(!1);dzLbRef.current=dzLb;
  x.useEffect(function(){setGapSel(null)},[clips]);
  var stDzFS=x.useState(function(){try{return JSON.parse(localStorage.getItem("dz_montage_lastfin")||"{}")||{}}catch(_e){return {}}}),dzFinStore=stDzFS[0],setDzFinStore=stDzFS[1];
  var dzLast=DzTracks.finOf(dzFinStore,proj.project_id||"_");
  var dzVoRef=x.useRef(null);
  var stVw=x.useState("montage"),view=stVw[0],setVw=stVw[1];
  var stDzJ=x.useState([]),dzJobs=stDzJ[0],setDzJobs=stDzJ[1];
  x.useEffect(function(){if(view==="livraison"){var alive=!0;
    fetch("/api/jobs?providers=montage&limit=24&q="+encodeURIComponent(proj.name||"")).then(function(r2){return r2.json()})
      .then(function(j){if(alive&&dzAliveRef.current)setDzJobs(Array.isArray(j)?j:[])}).catch(function(){});
    return function(){alive=!1}}},[view,proj.name]);
  function dzSetView(v){if(v==="medias"){if(proj.demo){fireNote(dzT("montage.medias.demo"));return}setMedTr("");setMedOn(!0);setSfxOn(!1);setSubsOn(!1);setNarrOn(!1)}
    if(v==="livraison"){setMedOn(!1);setSfxOn(!1);setSubsOn(!1);setNarrOn(!1)}setVw(v)}
  var stDzDel=x.useState(function(){try{var v=JSON.parse(localStorage.getItem("dz_montage_deliver")||"null");if(!v||typeof v!=="object")return {};delete v.rangeOnly;return v}catch(_e){return {}}}),dzDel=stDzDel[0],setDzDel=stDzDel[1];
  var dzDelRef=x.useRef(null);dzDelRef.current=dzDel;
  var stDzApi=x.useState(null),dzApi=stDzApi[0],setDzApi=stDzApi[1];
  x.useEffect(function(){if(pop!=="render"&&dzApi)return;var alive=!0;
    fetch("/api/montage/deliver-presets").then(function(r2){return r2.json()}).then(function(j){if(alive&&dzAliveRef.current&&j&&typeof j==="object")setDzApi(j)}).catch(function(){});
    return function(){alive=!1}},[pop]);
  function dzDelSet(p){setDzDel(function(d){var n=Object.assign({},d,p);try{localStorage.setItem("dz_montage_deliver",JSON.stringify(Object.assign({},n,{rangeOnly:void 0})))}catch(_e){}return n})}
  async function dzSavePreset(){var lbl=await window.__dzDialogue.saisir(dzT("montage.preset.nom_invite"),{titre:dzT("montage.preset.maison"),ok:dzT("montage.commun.enregistrer")});if(!lbl)return;
    var id=String(lbl).toLowerCase().replace(/[^a-z0-9_]+/g,"_").replace(/^_+|_+$/g,"").slice(0,32)||"maison";
    var tous=dzApi&&Array.isArray(dzApi.presets)?dzApi.presets:[],bi=dzApi&&Array.isArray(dzApi.builtins)?dzApi.builtins:[];
    var base=dzDel.preset||(bi[0]&&bi[0].id)||null,m=tous.filter(function(p){return p&&p.id===base})[0];if(m)base=m.base;
    var f=Number(dzDel.fps),cur=tous.filter(function(p){return p&&p.id!==id});
    fetch("/api/montage/deliver-presets",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({presets:cur.concat([{id:id,label:String(lbl),base:base,fps:isFinite(f)&&f>0?f:null,crf:null}])})})
      .then(function(r2){return r2.json().catch(function(){return null}).then(function(j){return {ok:r2.ok,j:j}})})
      .then(function(o){if(!o.ok||!o.j){fireNote(dzT("montage.preset.refuse",{e:((o.j&&(o.j.detail||o.j.error))||dzT("montage.commun.echec"))}));return}
        if(dzAliveRef.current){setDzApi(function(a){return Object.assign({},a||{},{presets:Array.isArray(o.j.presets)?o.j.presets:[]})});dzDelSet({preset:id})}
        fireNote(dzT("montage.preset.enregistre",{nom:lbl,id:id}))})
      .catch(function(e){fireNote(dzT("montage.preset.non_enregistre",{e:String(e&&e.message||e)}))})}
  var stDzM=x.useState("ecraser"),dzMode=stDzM[0],setDzMode=stDzM[1];
  function dzTtAdd(){var t=DzTracks.titleNew({template:"tiers_inferieur",text:"Titre"},phRef.current,clipsRef.current,"t1");
    var ts=svmTracksOf(dzProjRef.current),ts2=DzTracks.titleTrack(ts);
    if(ts2!==ts)svmTracksSet(ts2);else pushHistory();
    setClips(clipsRef.current.concat([t]));setSelId(t.id);setDirty(!0);
    fireNote(dzT("montage.titre.pose",{t:t.start.toFixed(2)}))}
  function dzAjAdd(){var c=DzTracks.adjustNew(phRef.current,clipsRef.current,"j1");
    if(!c){fireNote(dzT("montage.ajustement.rien"));return}
    var ts=svmTracksOf(dzProjRef.current),ts2=DzTracks.adjustTrack(ts);
    if(ts2!==ts)svmTracksSet(ts2);else pushHistory();
    setClips(clipsRef.current.concat([c]));setSelId(c.id);setDirty(!0);
    fireNote(dzT("montage.ajustement.pose"))}
  var stDzMk=x.useState(!1),dzMkOn=stDzMk[0],setDzMkOn=stDzMk[1];
  var dzMkOnRef=x.useRef(!1);dzMkOnRef.current=dzMkOn;
  function dzMkToggle(v){var n=arguments.length?!!v:!dzMkOnRef.current;if(n)setOvPick("");setDzMkOn(n)}
  x.useEffect(function(){if(ovPick)setDzMkOn(!1)},[ovPick]);
  var dzModeRef=x.useRef(dzMode);dzModeRef.current=dzMode;
  var stDzCat=x.useState(null),dzTransCat=stDzCat[0],setDzTransCat=stDzCat[1];
  x.useEffect(function(){var al=!0;
    fetch("/api/montage/transitions")
      .then(function(rp){return rp.ok?rp.json():null})
      .then(function(d){if(al&&d&&Array.isArray(d.familles)){
        window.__dzTransCat=d;setDzTransCat(d)}})
      .catch(function(){});
    return function(){al=!1}},[]);
  var dzVeilRef=x.useRef(null);
  var dzTtHistAt=x.useRef(0);
  var stDzTtN=x.useState(0),dzTtNonce=stDzTtN[0],setDzTtNonce=stDzTtN[1];
  var dzTtHostRef=x.useRef(null);
  var stDzTt=x.useState(null),dzTitles=stDzTt[0],setDzTitles=stDzTt[1];
  x.useEffect(function(){var al=!0;
    fetch("/api/montage/titles")
      .then(function(rp){return rp.ok?rp.json():null})
      .then(function(d){if(al&&d&&Array.isArray(d.gabarits))setDzTitles(d)})
      .catch(function(){});
    return function(){al=!1}},[]);
  /* P9 — « le VRAI projet est-il arrivé ? ». Tant que
     `svmApplyProject` n'a pas remplacé la maquette, `proj` est la
     démo : sans `tracks`, donc svmTracksOf retombe sur les six
     pistes historiques — v2 COMPRISE. Un clip posé à cet
     instant-là repartirait sur une v2 que le projet réel n'a pas,
     et `setClips(cs)` de svmApplyProject l'effacerait de toute
     façon en écrasant la liste entière. */
  var dzReadyRef=x.useRef(!1);dzReadyRef.current=!proj.demo;
  /* P9 — L'ATTENTE DE LA TIMELINE RÉELLE, ET SON EXTINCTION.
     Elle vit ICI, dans le corps du composant, et non dans
     `addAsset` : c'est le seul endroit d'où elle peut être
     ANNULÉE. `DzMontage` est monté CONDITIONNELLEMENT
     (`s==="montage"&&r.jsx(DzMontage,…)`) — quitter l'onglet le
     DÉMONTE. Sans la garde ci-dessous, la chaîne continuait à se
     replanifier toute seule jusqu'au plafond, puis `fireNote`
     tapait dans un arbre démonté : no-op silencieux de React 18.
     MESURÉ le 04/09/2026 en rejouant le texte LIVRÉ sous node,
     horloge simulée, démontage à 300 ms : 167 reprogrammations,
     20 040 ms d'horloge, 1 note émise dans le vide, 0 clip posé.
     Ni le clip NI le message — exactement le silence que toute
     cette tâche supprime ailleurs, et dans la fenêtre où l'on est
     le plus tenté de partir puisque GET /project ffprobe chaque
     asset. La garde EST la correction ; `clearTimeout` n'est que
     la propreté (il épargne un dernier réveil de 120 ms).
     UNE SEULE chaîne peut être en vol : tant que `dzReadyRef` est
     faux, `proj.demo` est vrai, et les six autres appelants
     d'`addAsset` sont derrière une garde `proj.demo` — le greffon
     amont, lui, ne tire qu'une fois (son effet `[]` supprime
     `window.__dzMontageAdd` avant même le setTimeout). Une seule
     ref de minuteur suffit donc.
     Le remontage RÉARME : un effet `[]` est rejoué en double sous
     StrictMode, et sans cette ligne l'écran serait mort pour de
     bon après le premier aller-retour. */
  var dzAliveRef=x.useRef(!0),dzWaitRef=x.useRef(0);
  x.useEffect(function(){dzAliveRef.current=!0;
    return function(){dzAliveRef.current=!1;
      if(dzWaitRef.current){clearTimeout(dzWaitRef.current);
        dzWaitRef.current=0}}},[]);
  function dzAddWhenReady(a1,b1,c1,d1,e1,f1,until){
    dzWaitRef.current=0;
    if(!dzAliveRef.current)return;
    if(dzReadyRef.current){addAsset(a1,b1,c1,d1,e1,f1);return}
    if(Date.now()>=until){fireNote(dzT("montage.attente.non_pose",{nom:b1
      
      
      }));return}
    dzWaitRef.current=setTimeout(function(){
      dzAddWhenReady(a1,b1,c1,d1,e1,f1,until)},120)}
  var videoRef=x.useRef(null);
  var mixRef=x.useRef(proj.mixDb);mixRef.current=proj.mixDb;
  var rippleRef=x.useRef(ripple);rippleRef.current=ripple;
  var previewRef=x.useRef(previewUrl);previewRef.current=previewUrl;
  var zoomPctRef=x.useRef(zoomPct);zoomPctRef.current=zoomPct;
  var tlScrollRef=x.useRef(null),pendScrollRef=x.useRef(null);
  var histRef=x.useRef({u:[],r:[]}); /* piles annuler / rétablir */
  var dzProjRef=x.useRef(null);dzProjRef.current=proj;
  function dzmHistHost(){return DzTracks.histSnap({clips:clipsRef.current,mixDb:mixRef.current,proj:dzProjRef.current})}
  var dzStyleHistAt=x.useRef(0);
  var dzDurHistAt=x.useRef(0);
  var stHT=x.useState(0),setHistTick=stHT[1];
  /* lecteur vivant + molette J/K/L + zones sûres */
  var playingRef=x.useRef(playing);playingRef.current=playing;
  var stSp=x.useState(1),spd=stSp[0],setSpd=stSp[1]; /* vitesse signée ±1/2/4 */
  var spdRef=x.useRef(spd);spdRef.current=spd;
  var stSf=x.useState(!1),safeOn=stSf[0],setSafeOn=stSf[1];
  /* muet / verrou par piste — {trId:{pm:dB d'avant muet, l:verrou}} ; le
     muet lui-même se lit dans proj.mixDb (bus ≤ −40 dB), source de vérité */
  var stTS=x.useState({}),trackSt=stTS[0],setTrackSt=stTS[1];
  var trackStRef=x.useRef(trackSt);trackStRef.current=trackSt;
  /* ── solo d'ÉCOUTE par piste audio ({a1:!0,…}) — état d'interface pur : il
     coupe les autres bus pendant la lecture directe, ne touche JAMAIS le
     payload de rendu ni l'historique. Maj+clic / Maj+S : multi-solo. ── */
  var stSo=x.useState({}),solo=stSo[0],setSolo=stSo[1];
  var soloRef=x.useRef(solo);soloRef.current=solo;
  var soloTaughtRef=x.useRef(0); /* pédagogie « écoute seule » : une fois par session */
  /* ── tiroir « Sons » (B) — DzSfx.Drawer, exclusif du tiroir Narration :
     la fermeture croisée est SYNCHRONE (même lot de setState, zéro frame où
     les deux tiroirs cohabitent) et n'écrase pas le choix dz_narr_open ── */
  var stSx=x.useState(!1),sfxOn=stSx[0],setSfxOn=stSx[1];
  /* ── tiroir « Sous-titres » (S1) — exclusif des tiroirs Sons et Narration.
     Les SEGMENTS sont des clips de la piste s1 : ils vivent dans `clips`,
     donc ils se déplacent, se rognent, s'annulent et se sauvegardent comme
     tout le reste, sans second modèle parallèle. Le STYLE vit dans
     proj.subsStyle (et dans dz_subs_style : la sauvegarde serveur ne connaît
     pas encore la clé, on ne perd pas le réglage en attendant). ── */
  /* P3 — panneau « Texte » (monter en LISANT). Son état est À LUI :
     il ne vit pas dans la zone des tiroirs (Sons / Narration /
     Sous-titres, mutuellement exclusifs) mais dans la COLONNE
     D'INSPECTION, où il ne dispute sa place à personne. */
  var stDzTx=x.useState(!1),dzTextOn=stDzTx[0],setDzTextOn=stDzTx[1];
  /* étape 7 du handoff « Barre Outils Flottante » (§6) : la demande
     d'ouverture de la liste des projets (un COMPTEUR, pas un
     booléen — le popover se ferme seul sur le clic qui l'ouvre),
     et l'ajout des emoji, PARTAGÉ par le bouton du bandeau et la
     barre : `pushHistory()` puis l'ajout, donc « annuler » les
     retire d'un coup. */
  var stDzPj=x.useState(0),dzProjReq=stDzPj[0],setDzProjReq=stDzPj[1];
  function dzEmoAdd(cs){pushHistory();setClips(function(k){return (k||[]).concat(cs)});setDirty(!0)}
  /* étape 8 du handoff (§4.1) : LA DEMANDE DE BASCULE de la barre
     d'outils, un COMPTEUR pour la même raison que `dzProjReq` —
     l'état d'ouverture appartient au Dock, qui le persiste ; un
     booléen piloté d'ici en aurait fait une seconde source. C'est
     M20b, la branche du gestionnaire clavier, qui l'incrémente. */
  var stDzTb=x.useState(0),dzTbReq=stDzTb[0],setDzTbReq=stDzTb[1];
  /* L7-B D-41 (24/09/2026, tâche 6) : la demande d'ouverture d'un projet créé par
     les auto-clips du tiroir Médias — {n, id, name}, un COMPTEUR comme dzProjReq ;
     la liste des projets l'ouvre par le chemin de « ouvrir ». */
  var stDzAc=x.useState(null),dzAcOpen=stDzAc[0],setDzAcOpen=stDzAc[1];
  /* E-10 (lot E-C, tâche 4, 23/09/2026) : la barre d'outils ANCRÉE dans le
     bandeau — un booléen persisté (clé ci-dessous), passé en prop `docked`
     au Dock ; l'entrée ☰ › Affichage le bascule. */
  var stTbD=x.useState(function(){try{return localStorage.getItem("dz_svm_tb_dock")==="1"}catch(_e){return !1}}),dzTbDock=stTbD[0],setDzTbDock=stTbD[1];
  function dzTbDockToggle(){setDzTbDock(function(v){var n=!v;try{localStorage.setItem("dz_svm_tb_dock",n?"1":"0")}catch(_e){}return n})}
  var stSu=x.useState(!1),subsOn=stSu[0],setSubsOn=stSu[1];
  /* mémo du VERDICT — la timeline en demande un par segment à chaque rendu,
     donc on ne refait le calcul que si les clips, le style, la durée ou le
     contrôle du moteur ont bougé. Le contenu, lui, vient TOUJOURS de
     DzSubs.verdict : la timeline ne décide rien. */
  var subsWRef=x.useRef({k:null,s:null,d:null,t:-1,v:null});
  /* le moteur répond en différé : sans cet abonnement, la timeline garderait
     le calcul local pendant que le tiroir affiche celui du moteur — deux
     verdicts sur la même image, ce qui est précisément le défaut fermé ici. */
  var stVt=x.useState(0),setSubsVt=stVt[1];
  x.useEffect(function(){
    var d=window.DzSubs;
    if(!d||!d.ready||!d.onVerdict)return;
    return d.onVerdict(function(){setSubsVt(function(t){return t+1})})},[]);
  var sfxToggle=x.useCallback(function(){
    setSfxOn(function(v){return !v});
    setNarrOn(!1);setMedOn(!1)},[]);
  /* ── métering — niveaux partagés (boucle vu-mètre → DzSfx.Meter) + dernière
     mesure LUFS (/api/montage/measure) ; lufsM = LUFS momentané K-weighted
     (fenêtre 400 ms, R2/I7), null hors lecture ── */
  var vuLvlRef=x.useRef({rms:0,peak:0,clip:!1,lufsM:null});
  var stLu=x.useState(null),lufs=stLu[0],setLufs=stLu[1]; /* {i,tp,lra} */
  var stLb=x.useState(!1),lufsBusy=stLb[0],setLufsBusy=stLb[1];
  /* ── rangée de hints transport (R2/I5) — masquée une fois pour toutes par ×
     (dz_hints_off) ; recherche du cheatsheet (R2/I6) ── */
  var stHo=x.useState(function(){
    try{return localStorage.getItem("dz_hints_off")==="1"}catch(_e){return !1}}),
    hintsOff=stHo[0],setHintsOff=stHo[1];
  var stKq=x.useState(""),kbQuery=stKq[0],setKbQuery=stKq[1];
  /* ── keymap remappable (R4c) — overrides dz_svm_keymap fusionnés aux
     défauts (mémoïsé : rien à recalculer pendant la lecture) ; kmRef nourrit
     le handler clavier global sans élargir ses dépendances ; kbEdit = action
     dont la combo est en cours de capture (panneau ?), kbMsg = refus inline
     (conflit / touche navigateur), kbConfirm = « Réinitialiser tout » ── */
  var stKo=x.useState(svmKmLoad),kmOv=stKo[0],setKmOv=stKo[1];
  var km=x.useMemo(function(){return svmKmMerge(kmOv)},[kmOv]);
  var kmRef=x.useRef(km);kmRef.current=km;
  function svmKeyLabel(id){
    return String(km.byId[id]||(SVM_ACTION_BY_ID[id]?SVM_ACTION_BY_ID[id].combo:"")).replace(/Maj/g,dzT("montage.touches.maj")).replace(/Échap/g,dzT("montage.touches.echap")).replace(/Espace/g,dzT("montage.touches.espace")).replace(/Suppr/g,dzT("montage.touches.suppr")).replace(/Entrée/g,dzT("montage.touches.entree"))}
  var stKe=x.useState(""),kbEdit=stKe[0],setKbEdit=stKe[1];
  var kbEditRef=x.useRef("");kbEditRef.current=kbEdit;
  var stKg=x.useState(null),kbMsg=stKg[0],setKbMsg=stKg[1]; /* {id,msg} */
  var stKc=x.useState(!1),kbConfirm=stKc[0],setKbConfirm=stKc[1];
  var mixWheelAt=x.useRef(0); /* fenêtre 600 ms de la molette des faders d'en-tête */
  /* ── réglages ducking (presets + enveloppe) — proj.ducking reste ABSENT
     tant que rien n'est personnalisé : le payload garde le booléen d'avant ── */
  var stDkO=x.useState(!1),duckOpen=stDkO[0],setDuckOpen=stDkO[1];
  var nudgeHistAt=x.useRef(0); /* fenêtre 600 ms du nudge Alt+flèches */
  var kbAudioRef=x.useRef(null); /* actions clavier audio — closures fraîches par rendu */
  /* ── automation de volume (R4) — mode d'édition ◇ (les losanges du clip
     sélectionné deviennent posables / éditables) + losange sélectionné
     {id,i} (Suppr le retire au lieu du clip). Les points eux-mêmes vivent
     sur le clip (volume_points) : historique et payload les suivent. ── */
  var stAum=x.useState(!1),autoOn=stAum[0],setAutoOn=stAum[1];
  var stVpS=x.useState(null),vpSel=stVpS[0],setVpSel=stVpS[1];
  /* la sélection de losange suit le clip et le mode — jamais d'index orphelin */
  x.useEffect(function(){setVpSel(null)},[selId,autoOn]);
  var auditionRef=x.useRef(null); /* écoute rendue (blob /api/audio/audition) */
  /* ── tiroir « Narration » (T) — écriture texte-first pilotant la piste A1.
     L'inverse assumé de Descript : on ÉCRIT, la synthèse pose l'audio et cale
     le clip. clip.text est un champ CLIENT, jamais joint au payload de rendu. */
  var stNo=x.useState(svmNarrInit),narrOn=stNo[0],setNarrOn=stNo[1];
  var stNV=x.useState(null),narrVoices=stNV[0],setNarrVoices=stNV[1]; /* null = à charger */
  var stNvi=x.useState(""),narrVoice=stNvi[0],setNarrVoice=stNvi[1];
  var stNB=x.useState(""),narrBusy=stNB[0],setNarrBusy=stNB[1]; /* id du bloc en synthèse */
  var stNA=x.useState(""),narrArm=stNA[0],setNarrArm=stNA[1]; /* confirmation de coût inline */
  var stNE=x.useState(null),narrErr=stNE[0],setNarrErr=stNE[1]; /* {id,msg} détail backend */
  var stNP=x.useState(""),narrPlayId=stNP[0],setNarrPlayId=stNP[1]; /* écoute de bloc */
  var narrConfirmRef=x.useRef(0); /* coût accepté une fois par session */
  var narrHistAt=x.useRef(0),narrScrollAt=x.useRef(0);
  var narrRef=x.useRef(null),narrAudioRef=x.useRef(null);
  /* ── tarif narration (B) — $/caractère effectif chargé à la première
     ouverture du tiroir (null = pas encore chargé) + dépense de session
     {n blocs, usd} incrémentée à chaque synthèse réussie ── */
  var stNR=x.useState(null),narrRate=stNR[0],setNarrRate=stNR[1];
  var stNS=x.useState({n:0,usd:0}),narrSpent=stNS[0],setNarrSpent=stNS[1];
  /* ── sauvegarde de timeline (A) — autosave 1,5 s après la dernière
     édition ; saveInfo {ok, at} nourrit le badge « enregistré · HH:MM:SS » /
     « sauvegarde impossible » ; le compteur de séquence évite d'éteindre
     « NON ENREGISTRÉ » si une édition arrive pendant la requête ── */
  var stSv=x.useState(null),saveInfo=stSv[0],setSaveInfo=stSv[1];
  var saveSeqRef=x.useRef(0),saveAbortRef=x.useRef(null);
  var stLA=x.useState(!1),libArm=stLA[0],setLibArm=stLA[1]; /* confirmation « bibliothèque » */
  var narrToggle=x.useCallback(function(){
    setNarrOn(function(v){var nv=!v;
      try{localStorage.setItem("dz_narr_open",nv?"1":"0")}catch(_e){}
      return nv});
    /* tiroirs gauche exclusifs : ouvrir Narration ferme Sons (l'inverse vit
       dans sfxToggle) — fermer l'un ne rouvre jamais l'autre */
    setSfxOn(!1);setMedOn(!1)},[]);
  /* auto-grow des zones de texte — callback STABLE (un ref inline se
     ré-attacherait à chaque frame de lecture) + réappliqué à la frappe */
  var narrTaGrow=x.useCallback(function(el){
    if(!el)return;
    el.style.height="auto";
    el.style.height=Math.min(190,el.scrollHeight+2)+"px"},[]);
  var frameRef=x.useRef(null),hoverTcRef=x.useRef(null),transLabelRef=x.useRef(null);
  var liveHostRef=x.useRef(null),liveOvRef=x.useRef(null),liveVideoRef=x.useRef(null);
  var livePoolRef=x.useRef(null),liveSeqRef=x.useRef(0);
  var liveRafRef=x.useRef(0),livePendRef=x.useRef(null);
  /* overlays transformables : cadre de sélection + geste en cours (lecteur) */
  var vzRef=x.useRef(vzoom);vzRef.current=vzoom;
  var dragTfRef=x.useRef(null); /* {id,x,y,scale,rotate} pendant un geste — source de vérité du drag */
  var tfBoxRef=x.useRef(null),tfGuideVRef=x.useRef(null),tfGuideHRef=x.useRef(null);
  var tfBadgeRef=x.useRef(null),tfRoRef=x.useRef(null),tfSyncRef=x.useRef(null);
  var ovHistAt=x.useRef(0); /* fenêtre 600 ms de l'inspecteur Overlay */
  /* nudge clavier des overlays (R4b) — un V2 avec source sélectionné prend
     les flèches (déplacement ±0,5 %, Maj ±2 %) ; Échap les rend à la tête de
     lecture jusqu'à la prochaine (re)sélection — l'état vit dans une ref,
     remis à zéro par tout pointerdown de clip / couche */
  var ovKeysOffRef=x.useRef(!1);
  x.useEffect(function(){ovKeysOffRef.current=!1},[selId]);
  var dur=proj.dur;

  /* ── historique — instantanés {clips, mixDb}, cap 60 de chaque côté.
     pushHistory() lit les refs (état d'AVANT la mutation) ; un geste continu
     (drag, trim, mixage) capture son état au pointerdown et ne pousse qu'une
     entrée au relâchement. Les tableaux sont traités en immutable partout,
     stocker les références suffit. */
  var pushHistory=x.useCallback(function(prev){
    var h=histRef.current;
    h.u.push(prev||dzmHistHost());
    if(h.u.length>60)h.u.shift();
    h.r.length=0;
    setHistTick(function(t){return t+1})},[]);
  /* T103 (plan-son-vfx T10, D2b) : le rack VFX pose (ou retire) le SUJET
     DÉTOURÉ d'un plan par l'évènement `dz-matte` {id, matte} — un geste
     annulable comme les autres ; le rendu compose alors les effets derrière lui. */
  x.useEffect(function(){
    function onMatte(ev){var d=(ev&&ev.detail)||{};
      if(!d.id)return;
      pushHistory();
      setClips(clipsRef.current.map(function(k){return k.id===d.id?Object.assign({},k,{matte:d.matte||void 0}):k}));
      setDirty(!0);
      fireNote(d.matte?dzT("montage.matte.pose"):dzT("montage.matte.retire"))}
    window.addEventListener("dz-matte",onMatte);
    return function(){window.removeEventListener("dz-matte",onMatte)}},[]);
  var undo=x.useCallback(function(){
    var h=histRef.current;if(!h.u.length)return;
    var s=h.u.pop();
    h.r.push(dzmHistHost());
    if(h.r.length>60)h.r.shift();
    if("clips" in s)setClips(s.clips);
    /* D-0 — pistes, durée, style S1, plage, marqueurs reviennent avec
       le mixage ; SVM_TRACK_BUS suit les pistes restaurées. `histApply`
       ne touche PAS aux clips : c'est la ligne du dessus qui les rend.
       L'APPEL EST NU EXPRÈS : `s.tracks` vaut `undefined` quand le
       projet d'avant n'avait pas la clé, et `svmTrackBusSync` retombe
       alors sur DZM_DEFAULT_TRACKS — la table même que `svmTracksOf`
       rend sans `proj.tracks` (mesuré sous node le 21/09/2026 : les
       trois bus sont identiques). */
    if("tracks" in s)svmTrackBusSync(s.tracks);
    setProj(function(p){return DzTracks.histApply(p,s)});
    setDirty(!0);setHistTick(function(t){return t+1})},[]);
  var redo=x.useCallback(function(){
    var h=histRef.current;if(!h.r.length)return;
    var s=h.r.pop();
    h.u.push(dzmHistHost());
    if(h.u.length>60)h.u.shift();
    if("clips" in s)setClips(s.clips);
    /* D-0 — pistes, durée, style S1, plage, marqueurs reviennent avec
       le mixage ; SVM_TRACK_BUS suit les pistes restaurées. `histApply`
       ne touche PAS aux clips : c'est la ligne du dessus qui les rend.
       L'APPEL EST NU EXPRÈS : `s.tracks` vaut `undefined` quand le
       projet d'avant n'avait pas la clé, et `svmTrackBusSync` retombe
       alors sur DZM_DEFAULT_TRACKS — la table même que `svmTracksOf`
       rend sans `proj.tracks` (mesuré sous node le 21/09/2026 : les
       trois bus sont identiques). */
    if("tracks" in s)svmTrackBusSync(s.tracks);
    setProj(function(p){return DzTracks.histApply(p,s)});
    setDirty(!0);setHistTick(function(t){return t+1})},[]);
  /* suppression d'un clip (id explicite : Suppr, inspecteur, blocs de
     narration) — ripple actif : les clips SUIVANTS de la même piste remontent
     de la longueur du trou (piste principale magnétique) */
  var delClipById=x.useCallback(function(id){
    var cs=clipsRef.current;
    var c=cs.find(function(k){return k.id===id});
    if(!c)return;
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){
      fireNote(dzT("montage.piste.verrou_supprimer",{p:c.tr.toUpperCase()}));return}
    pushHistory();
    var len=c.end-c.start;
    var next=cs.filter(function(k){return k.id!==id});
    if(rippleRef.current)next=next.map(function(k){
      return k.tr===c.tr&&k.start>=c.end-.001?
        Object.assign({},k,{start:k.start-len,end:k.end-len}):k});
    setClips(next);setSelId("");setDirty(!0);
    fireNote(dzT("montage.clip.supprime",{nom:c.label})+(rippleRef.current?dzT("montage.clip.trou_referme"):""))},[fireNote,pushHistory]);
  var delClip=x.useCallback(function(){delClipById(selRef.current)},[delClipById]);
  /* ── E-6 (lot E-C, tâche 2, 23/09/2026) : LE MENU ☰ ET LES MENUS CONTEXTUELS ──
     dzFire(id) rejoue la combo VIVANTE d'une action (svmKeyLabel, repli table) par un
     KeyboardEvent synthétique sur window : onKey reste l'unique dispatch (il ne filtre
     que les champs de saisie). dzReplaceArm = le geste du bouton « remplacer » (R_M16),
     extrait : le bouton ET le menu du clip l'appellent. dzMenuProps(kind,o) construit les
     entrées À L'OUVERTURE (mémorisées dans dzMenu, jamais reconstruites au rendu) ; x,y
     ramenés au repère de .dzsvm (position:absolute;inset:0 — motif d'openTransPopAt). */
  function dzFire(id){var a=SVM_ACTION_BY_ID[id],k=DzTracks.comboToKey(km.byId[id]||(a&&a.combo)||"");
    if(k)window.dispatchEvent(new KeyboardEvent("keydown",Object.assign({bubbles:!0,cancelable:!0},k)))}
  function dzReplaceArm(sel){
    if(trackStRef.current[sel.tr]&&trackStRef.current[sel.tr].l){
      fireNote(dzT("montage.piste.verrou_remplacer",{p:sel.tr.toUpperCase()
        
        }));return}
    dzmReplaceRef.current={id:sel.id,tr:sel.tr,
      label:sel.label};
    setDzmArm({tr:sel.tr,label:sel.label});
    /* déjà ouvert sur cette piste : rouvrir le REFERMERAIT (le sélecteur bascule), et le
       mode resterait armé sur un panneau fermé. C'est `setDzmArm` — et non `openPicker` —
       qui re-rend dans ce cas-là, sans quoi le panneau resterait intitulé « Ajouter sur la
       piste V1 » pendant qu'il remplace. */
    if(ovPick!==sel.tr)openPicker(sel.tr)}
  function dzExportTl(fmt){var lib=fmt==="edl"?"EDL":"FCPXML",ext=fmt==="edl"?".edl":".fcpxml";
    if(proj.demo){fireNote(dzT("montage.export_tl.demo",{fmt:lib}));return}
    fireNote(dzT("montage.export_tl.en_cours",{fmt:lib}));
    fetch("/api/montage/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(svmSavePayload())})
      .then(function(res){if(!res.ok)throw new Error(dzT("montage.export_tl.sauvegarde_refusee",{code:res.status}));return fetch("/api/montage/export?format="+fmt)})
      .then(function(res){return res.text().then(function(t){
        if(!res.ok){var m="";try{m=(JSON.parse(t)||{}).detail||""}catch(_e){}throw new Error(m||("HTTP "+res.status))}
        var mm=/filename="([^"]+)"/.exec(res.headers.get("Content-Disposition")||"");return {nom:mm?mm[1]:"montage"+ext,t:t}})})
      .then(function(o){if(subsDownload(o.nom,o.t,fmt==="edl"?"text/plain":"application/xml"))fireNote(dzT("montage.export_tl.exporte",{fmt:lib,nom:o.nom}));else fireNote(dzT("montage.export_tl.navigateur"))})
      .catch(function(e){fireNote(dzT("montage.export_tl.refuse",{fmt:lib,e:((e&&e.message)||dzT("montage.commun.erreur_reseau"))}))})}
  function dzSceneCut(id){var c=clipsRef.current.find(function(k){return k.id===id});
    if(!c||!c.src||!c.src.job_id){fireNote(dzT("montage.scenes.reserve"));return}
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){fireNote(dzT("montage.piste.verrou_decouper",{p:c.tr.toUpperCase()}));return}
    var sp=typeof c.speed==="number"&&c.speed>0?c.speed:1,du=Math.round(Math.max(0,(c.end-c.start)*sp)*1e3)/1e3;
    function dzSg(k){return [Number(k.srcIn)||0,typeof k.speed==="number"&&k.speed>0?k.speed:1,Number(k.start)||0,Number(k.end)||0,svmSrcKey(k.src)].join("|")}
    var sg=dzSg(c);
    fireNote(dzT("montage.scenes.analyse"));
    fetch("/api/montage/scenes",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({src:c.src,srcIn:Number(c.srcIn)||0,dur:du})})
      .then(function(res){return res.json().catch(function(){return {}}).then(function(j){
        if(!res.ok)throw new Error((j&&typeof j.detail==="string"&&j.detail)||("HTTP "+res.status));return j})})
      .then(function(j){var k2=clipsRef.current.find(function(k){return k.id===id});
        if(k2&&dzSg(k2)!==sg){fireNote(dzT("montage.scenes.refus_change"));return}
        var r2=DzTracks.cutAt(clipsRef.current,id,j&&j.times,DzTracks.cutOpts(proj,trackStRef.current));
        if(r2.refus){fireNote(r2.note);return}
        pushHistory();setClips(r2.clips);setDirty(!0);fireNote(r2.note)})
      .catch(function(e){fireNote(dzT("montage.scenes.refuse",{e:((e&&e.message)||dzT("montage.commun.erreur_reseau"))}))})}
  function dzMenuProps(kind,o){
    var id=o.id,ph=phRef.current,cs=clipsRef.current,rr=rootRef.current?rootRef.current.getBoundingClientRect():{left:0,top:0,width:window.innerWidth};
    var base={kind:kind,id:id,x:Math.max(0,Math.min(o.x-rr.left,rr.width-270)),y:Math.max(0,o.y-rr.top)};
    if(kind==="main"){
      var rubs=DzTracks.menuModel(SVM_ACTIONS,svmKeyLabel).map(function(g){return {rub:g.rub,items:g.items.map(function(a){return {lbl:a.lbl,combo:a.combo,run:function(){dzFire(a.id)}}})}});
      rubs.unshift({rub:dzT("montage.menu.projet"),items:[
        {lbl:dzT("montage.menu.projets"),run:function(){setDzProjReq(function(n){return n+1})}},
        {lbl:"Preview 480p",run:function(){setPop("preview")}},
        {lbl:dzT("montage.menu.rendre"),run:function(){setPop("render")}},
        {lbl:dzT("montage.menu.publier"),off:!dzLast,run:function(){if(dzLast){setPop("");setDzFin(Object.assign({project_id:proj.project_id||""},dzLast))}}},
        {lbl:dzT("montage.menu.exporter_edl"),run:function(){dzExportTl("edl")}},
        {lbl:dzT("montage.menu.exporter_fcpxml"),run:function(){dzExportTl("fcpxml")}}]});
      var aff=rubs.filter(function(g){return g.rub==="Affichage"})[0];
      if(!aff){aff={rub:"Affichage",items:[]};rubs.splice(rubs.length-1,0,aff)}
      aff.items=aff.items.concat([
        {lbl:dzT("montage.menu.inspecteur"),combo:inspOn?"✓":"",run:function(){setInspSt(function(s){var n={on:!s.on,w:s.w};try{localStorage.setItem("dz_svm_insp",JSON.stringify(n))}catch(_e){}return n})}},
        {lbl:dzT("montage.menu.medias"),combo:medOn?"✓":"",run:function(){if(proj.demo){fireNote(dzT("montage.medias.demo"));return}setMedTr("");setMedOn(!medOn);setSfxOn(!1);setSubsOn(!1);setNarrOn(!1)}},
        {lbl:dzT("montage.menu.durees"),combo:showDur?"✓":"",run:function(){setShowDur(function(v){var n=!v;try{localStorage.setItem("dz_svm_showdur",n?"1":"0")}catch(_e){}return n})}},
        {lbl:dzT("montage.menu.plans_longs"),combo:bo.on?dzT("montage.commun.actif"):"",run:function(){setPop("boring")}},
        {lbl:dzT("montage.menu.lightbox"),run:function(){setDzLb(!0)}},
        {lbl:dzT("montage.menu.ancrer"),combo:dzTbDock?"✓":"",run:function(){dzTbDockToggle()}}]);
      return Object.assign(base,{rubs:rubs})}
    if(kind==="clip"){var c=cs.find(function(k){return k.id===id});if(!c)return null;
      var vid=trackKind(c.tr)==="video",sp=svmSpeedOf(c),g=DzTracks.voisins(cs,c).g;   /* t117 : toute piste vidéo */
      return Object.assign(base,{items:[
        {lbl:dzT("montage.menu.couper_tete"),combo:svmKeyLabel("blade"),off:!(ph>c.start+.05&&ph<c.end-.05),run:function(){dzFire("blade")}},
        {lbl:dzT("montage.menu.decouper_scenes"),off:!(c.src&&c.src.job_id)||trackKind(c.tr)!=="video",run:function(){dzSceneCut(id)}},
        {lbl:dzT("montage.commun.supprimer"),combo:svmKeyLabel("delete"),run:function(){delClipById(id)}},
        {lbl:dzT("montage.menu.remplacer_source"),off:!c.src,run:function(){dzReplaceArm(c)}},
        {lbl:dzT("montage.menu.effets"),off:trackKind(c.tr)==="audio",run:function(){setFxPick(!0)}},
        {lbl:dzT("montage.menu.copier_grade"),combo:svmKeyLabel("grade_copy"),off:!DzTracks.gradeTake(c),run:function(){dzGradeCopy(id)}},
        {lbl:dzT("montage.menu.coller_grade"),combo:svmKeyLabel("grade_paste"),off:!!proj.demo||trackKind(c.tr)!=="video"||!DzTracks.gradeRead(),run:function(){dzGradePaste(id)}},{sep:!0}]
        .concat([.25,.5,.75,1,1.5,2].map(function(v){return {lbl:dzT("montage.menu.vitesse",{n:Math.round(v*100)}),combo:Math.abs(sp-v)<1e-6?"✓":"",off:!vid||!c.src||!c.src.job_id,run:function(){svmSetV1Speed(id,v)}}}))
        .concat([{sep:!0},{lbl:"Transition…",off:!g,run:function(){openTransPopAt(id,o.x)}}])})}
    if(kind==="track"){var ts=svmTracksOf(proj),t=ts.find(function(k){return k.id===id});if(!t)return null;
      var bus=SVM_TRACK_BUS[id],lk=!!(trackSt[id]&&trackSt[id].l),bs=id==="v1"||id==="s1",n=cs.filter(function(k){return k.tr===id}).length;
      return Object.assign(base,{items:[
        {lbl:lk?dzT("montage.menu.deverrouiller"):dzT("montage.menu.verrouiller"),run:function(){svmTrackLock(id)}},
        {lbl:dzT("montage.menu.muet"),off:!bus,run:function(){svmTrackMute(id)}},
        {lbl:"Solo",off:!bus,run:function(){svmTrackSolo(id,!1)}},{sep:!0}]
        /* L7 D-22 (24/09/2026, tâche 6) : une piste de sous-titres — graver, exporter ses clips, nouvelle piste de langue */
        .concat(trackKind(id)==="subs"?(function(){var bid=DzTracks.subsBurnId(ts),segs=cs.filter(function(k){return k.tr===id});
          function dzSubsExp(fmt){var txt=fmt==="srt"?subsToSrt(segs,subsStyleNow()):fmt==="vtt"?subsToVtt(segs,subsStyleNow()):subsToTxt(segs);
            if(!txt.trim()){fireNote(dzT("montage.sous_titres.rien_a_exporter",{p:t.name||id}));return}
            var base=String(proj.name||"sous-titres").replace(/[^\w\-. ]+/g,"_")+"-"+id;
            fireNote(subsDownload(base+"."+fmt,txt,fmt==="vtt"?"text/vtt":fmt==="srt"?"application/x-subrip":"text/plain")?dzT("montage.sous_titres.fichier_ecrit",{nom:base+"."+fmt}):dzT("montage.sous_titres.telechargement_refuse"))}
          return [{lbl:bid===id?dzT("montage.menu.gravee_rendu"):dzT("montage.menu.graver_piste"),combo:bid===id?dzT("montage.menu.gravee"):"",off:bid===id,run:function(){svmTracksSet(DzTracks.subsBurn(ts,id));
              fireNote(dzT("montage.sous_titres.gravee",{p:t.name||id}))}},
            {lbl:dzT("montage.menu.exporter_srt"),off:!n,run:function(){dzSubsExp("srt")}},{lbl:dzT("montage.menu.exporter_vtt"),off:!n,run:function(){dzSubsExp("vtt")}},{lbl:dzT("montage.menu.exporter_txt"),off:!n,run:function(){dzSubsExp("txt")}},
            {lbl:dzT("montage.menu.nouvelle_langue"),run:async function(){var lg=await window.__dzDialogue.saisir(dzT("montage.sous_titres.langue_invite"),{titre:dzT("montage.sous_titres.nouvelle_langue_titre"),valeur:"en",ok:dzT("montage.commun.creer")});if(lg==null)return;
              var r2=DzTracks.subsNew(ts,lg);svmTracksSet(r2.tracks);
              fireNote(dzT("montage.sous_titres.piste_ajoutee",{p:r2.id.toUpperCase(),langue:(String(lg).trim()?" ("+String(lg).trim()+")":"")}))}},{sep:!0}]})():[])
        .concat([
        {lbl:dzT("montage.menu.supprimer_piste"),off:bs,run:function(){svmTracksSet(DzTracks.remove(ts,id));
          if(n)setClips(function(cs2){return (cs2||[]).filter(function(k){return k.tr!==id})});
          fireNote((n?(n>1?dzT("montage.piste.retiree_clips.plusieurs",{p:t.name||id,n:n}):dzT("montage.piste.retiree_clips.un",{p:t.name||id,n:n})):dzT("montage.piste.retiree",{p:t.name||id})))}}])})}
    return null}
  /* L5 D-31 D-32 : le choix d'un plan dans la lightbox et les gestes du grade (clavier + menu de clip) */
  function dzLbPick(id){var k=clipsRef.current.find(function(q){return q.id===id});setDzLb(!1);
    if(!k){fireNote(dzT("montage.lightbox.disparu"));return}
    setSelId(k.id);seekTo(k.start)}
  function dzGradeCopy(id){var c=clipsRef.current.find(function(k){return k.id===id});
    if(!c){fireNote(dzT("montage.grade.copier_selection"));return}
    fireNote(DzTracks.gradeCopyDo(c).note)}
  function dzGradePaste(id){
    if(dzProjRef.current&&dzProjRef.current.demo){fireNote(dzT("montage.grade.coller_demo"));return}
    var c=clipsRef.current.find(function(k){return k.id===id});
    if(!c){fireNote(dzT("montage.grade.coller_selection"));return}
    if(trackKind(c.tr)!=="video"){fireNote(dzT("montage.grade.coller_video"));return}
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){fireNote(dzT("montage.piste.verrou_grade",{p:c.tr.toUpperCase()}));return}
    var q=DzTracks.gradePasteDo(c);if(!q.clip){fireNote(q.note);return}
    pushHistory();setClips(clipsRef.current.map(function(k){return k.id===c.id?q.clip:k}));setDirty(!0);fireNote(q.note)}

  /* ── applique une réponse /api/montage/project — Bibliothèque OU
     sauvegarde (A). La sauvegarde porte le modèle CLIENT complet : chaque
     clip est repris TEL QUEL (texte de narration, gain/fondus/courbes,
     automation, transformation/trajectoire, vitesse, effets, opacité…),
     positions re-numérisées ; la Bibliothèque garde le mapping minimal
     historique. Vrai si une timeline a été posée. ── */
  /* P1 — TOUTE écriture de proj.tracks passe ici : historique poussé,
     SVM_TRACK_BUS resynchronisé, projet réécrit, « NON ENREGISTRÉ »
     allumé. Deux appelants (la barre d'outils et les en-têtes de
     piste) ; sans ce point unique, chacun aurait sa propre version de
     la séquence et l'un des deux finirait par en oublier un morceau.
     RESTE CONNU : l'historique ne mémorise que {clips, mixDb} — un
     annuler après un retrait de piste ramène les CLIPS, pas la piste.
     Ils redeviennent visibles dès qu'on rajoute une piste du même
     genre : l'identifiant repris est le plus petit libre, donc le
     leur. C'est dit dans la note du bouton, ce n'est pas silencieux. */
  /* P6 — L'ARMEMENT DU MODE REMPLACEMENT, et son DÉSARMEMENT.
     `{id, tr}` du plan dont on va échanger la source ; le prochain
     asset choisi remplacera au lieu d'ajouter. Une REF et non un
     état : le sélecteur d'assets appelle le poseur de clips depuis
     une fermeture, et un état re-rendu n'y serait pas lu.
     L'effet ci-dessous est la moitié qui manquait au plan : sans
     lui, une armement suivi d'un sélecteur FERMÉ sans choisir — ou
     rouvert sur une AUTRE piste — laissait le mode armé, et le clip
     suivant venait écraser la source d'un plan que l'utilisateur ne
     regardait plus. Le désarmement suit l'état du sélecteur
     lui-même (`ovPick`), pas une copie de ses règles.
     `dzmArm` est le MIROIR D'AFFICHAGE de cette ref, et rien de
     plus : la ref reste la seule autorité que lit `addAsset`.
     Il existe parce qu'une ref ne re-rend pas, et que le
     sélecteur doit DIRE qu'il est armé au moment où il l'est —
     y compris quand il était DÉJÀ ouvert sur la piste du plan et
     que M16src ne le rouvre donc pas (le rouvrir le refermerait).
     Un état SEUL ne suffirait pas : le rappel « version plus
     récente » arme puis appelle `addAsset` dans le MÊME
     gestionnaire, et un état posé là n'y serait pas relu. */
  var dzmReplaceRef=x.useRef(null);
  var stDZA=x.useState(null),dzmArm=stDZA[0],setDzmArm=stDZA[1];
  x.useEffect(function(){var rp=dzmReplaceRef.current;
    if(rp&&ovPick!==rp.tr){dzmReplaceRef.current=null;
      setDzmArm(null)}},[ovPick]);
  function svmTracksSet(ts){pushHistory();svmTrackBusSync(ts);setProj(function(p){return Object.assign({},p,{tracks:ts})});setDirty(!0)}
  function svmApplyProject(d){
    if(!d||!d.ok||!d.has_assets)return !1;
    var cs=(d.clips||[]).map(function(c,i){
      if(d.saved){
        var nk=Object.assign({},c);
        nk.id=c.id||("c"+i);nk.label=c.label||"clip";
        nk.start=Number(c.start)||0;nk.end=Number(c.end)||0;
        nk.srcIn=Number(c.srcIn)||0;
        if(String(c.tr||"").charAt(0)==="v"){nk.transition=c.transition||"cut";   /* t117 : toute piste vidéo */
          nk.transition_s=Number(c.transition_s)||0}
        return nk}
      return {tr:c.tr,id:c.id||("c"+i),label:c.label||"clip",start:Number(c.start)||0,
        end:Number(c.end)||0,src:c.src||null,srcIn:Number(c.srcIn)||0,
        transition:c.transition||(String(c.tr||"").charAt(0)==="v"?"cut":void 0),
        transition_s:Number(c.transition_s)||0}});
    /* P12 — DES IDENTIFIANTS UNIQUES. `ovSeq` repart de zéro à chaque
       chargement et la sauvegarde reprend `c.id` tel quel : deux clips
       du même id se suppriment ensemble (`c.id!==id`) et le second n'est
       jamais sélectionnable (`c.id===selId`). Le PREMIER garde le sien,
       les suivants sont renommés, c'est dit, `v1_non_video` — des
       IDENTIFIANTS, contrat du backend — suit le renommage (l'id neuf est
       AJOUTÉ : les deux exemplaires étaient marqués, ils le restent), et
       le compteur repart AU-DESSUS de tout ce que la sauvegarde porte. La
       réparation est PERSISTÉE par M22d (l'autosauvegarde) sur une
       sauvegarde, jamais sur une construction de Bibliothèque : la note
       le dit dans les deux cas. */
    var dzDd=DzTracks.dedupeIds(cs);cs=dzDd.clips;
    if(dzDd.renamed.length&&Array.isArray(d.v1_non_video))d.v1_non_video=
      d.v1_non_video.concat(dzDd.renamed.filter(function(k){
        return d.v1_non_video.indexOf(k.de)>=0&&d.v1_non_video.indexOf(k.en)<0})
      .map(function(k){return k.en}));
    if(dzDd.renamed.length)fireNote((dzDd.renamed.length>1?dzT("montage.ids.renommes.plusieurs",{n:dzDd.renamed.length,
      liste:dzDd.renamed.map(function(k){
        return k.de+" → "+k.en}).join(", "),
      suite:d.saved?dzT("montage.ids.suite_auto")
        :dzT("montage.ids.suite_biblio")})
      :dzT("montage.ids.renommes.un",{n:dzDd.renamed.length,
      liste:dzDd.renamed.map(function(k){return k.de+" → "+k.en}).join(", "),
      suite:d.saved?dzT("montage.ids.suite_auto")
        :dzT("montage.ids.suite_biblio")})));
    ovSeq.current=Math.max(ovSeq.current,DzTracks.seqMax(cs));
    var first=cs.find(function(c){return c.tr==="v1"});
    var maxEnd=1;
    cs.forEach(function(c){if(c.end>maxEnd)maxEnd=c.end});
    setClips(cs);setSelId(first?first.id:"");setPh(0);setDirty(!!(d.saved&&dzDd.renamed.length));
    /* P12 — LA RÉPARATION EST PERSISTÉE. `setDirty(!1)` désarmait ici
       l'autosauvegarde (l'effet gardé par `dirty`, 1,5 s) juste après le
       renommage de M22c, et AUCUN geste manuel n'enregistre le montage —
       `svmDoSave(` n'a que trois sites dans le bundle (sa définition,
       cet effet, la relance sur échec), « Enregistrer sous… » crée un
       projet NEUF (mesuré le 06/09/2026) : la note serait revenue à
       chaque chargement. Une SAUVEGARDE dont des ids ont été renommés est
       donc marquée modifiée, et l'autosauvegarde écrit les ids réparés.
       Une construction depuis la Bibliothèque (`saved` faux) ne l'est
       JAMAIS : l'enregistrer en ferait la source à la place de la
       Bibliothèque — et ses ids (`v1_<job>`, `a1_<job>`, `c<i>`) ne se
       répètent pas. La note de M22c le dit dans les deux cas. */
    histRef.current={u:[],r:[]};setHistTick(function(t){return t+1});
    var np={demo:!1,tracks:(function(){var _t=svmTracksFrom(d.tracks);return _t&&(d.clips||[]).some(function(c){return c&&c.kind==="title"})?DzTracks.titleTrack(_t):_t})(),project_id:d.project_id,v1NonVideo:Array.isArray(d.v1_non_video)?d.v1_non_video:null,range:DzTracks.rangeFrom(d.range),markers:DzTracks.markersFrom(d.markers),name:d.name||"montage",version:"v1",ratio:d.ratio||"9:16",vide:d.vide===!0,
      dur:Math.max(1,Number(d.duration)||maxEnd),mixDb:d.mix||SVM_DEMO_MIX};
    if(d.saved){
      /* restauration des commutateurs + réglages ducking sauvegardés */
      if(d.ducking_cfg&&typeof d.ducking_cfg==="object")np.ducking=d.ducking_cfg;
      setDurMaster(d.duration_master!==!1);
      setDucking(d.ducking===!1?!1:!0);
      var at=d.saved_at?Date.parse(d.saved_at):NaN;
      setSaveInfo(isFinite(at)?{ok:!0,at:at}:null);
      if(d.saved_pruned)fireNote(dzT("montage.sauvegarde.restauree",{
        n:d.pruned||1}))}
    /* style des sous-titres : la sauvegarde serveur d'abord si elle le porte,
       le réglage local (dz_subs_style) sinon — jamais le défaut par surprise */
    var _ss=d&&d.subs_style&&typeof d.subs_style==="object"?d.subs_style:null;
    if(!_ss)try{_ss=JSON.parse(localStorage.getItem("dz_subs_style")||"null")}
      catch(_e){_ss=null}
    if(_ss&&typeof _ss==="object")np.subsStyle=_ss;
    svmTrackBusSync(np.tracks);
    setProj(np);
    return !0}

  /* projet initial — la sauvegarde d'éditeur d'abord (saved:true), sinon
     les vrais assets de la Bibliothèque quand il y en a */
  x.useEffect(function(){var alive=!0;
    fetch("/api/montage/project").then(function(res){return res.json()}).then(function(d){
      if(alive)svmApplyProject(d)
    }).catch(function(){});
    return function(){alive=!1}},[]);

  /* ── autosave (A) — 1,5 s après la DERNIÈRE édition (chaque changement du
     modèle replanifie, le nettoyage d'effet fait le debounce), jamais en
     démo. Le POST part avec l'état du DERNIER rendu (l'effet se re-crée à
     chaque édition : la fermeture est toujours fraîche) ; le succès n'éteint
     « NON ENREGISTRÉ » que si aucune édition n'est arrivée entre-temps
     (compteur de séquence) — sinon la sauvegarde suivante est déjà armée. */
  function svmSavePayload(){
    /* le payload de SAVE n'est PAS celui du rendu : les clips partent TELS
       QUELS (modèle client complet — JSON.stringify ignore les undefined) ;
       seuls les états d'interface pure (sélection, tête, zoom, solo,
       verrous, historique) restent dehors */
    var o={name:proj.name,ratio:proj.ratio,duration:proj.dur,mix:proj.mixDb,
      duration_master:durMaster,ducking:ducking,clips:clips,
      /* sans cette clé, une piste ajoutée disparaissait au rechargement
         et les clips qu'elle portait retombaient sur une piste inconnue,
         donc hors du rendu — silencieusement. */
      tracks:svmTracksPayload(proj),
      vide:proj.vide===!0?!0:void 0,
      /* P5 — de quel projet NOMMÉ ce brouillon est le brouillon. Le
         backend n'écrit dans le projet QUE si cette clé désigne un
         fichier existant : sans elle (montage sans nom), rien ne
         change, pas un fichier n'est semé. */
      project_id:proj.project_id,
      range:DzTracks.rangeFrom(proj.range),
      markers:(proj.markers||[]),
      /* style des sous-titres : envoyé pour le jour où la sauvegarde serveur
         le connaîtra (les segments, eux, sont déjà dans `clips` et sont
         stockés tels quels) ; en attendant c'est dz_subs_style qui le retient */
      subs_style:proj.subsStyle||void 0};
    if(proj.ducking)o.ducking_cfg=proj.ducking;
    return o}
  function svmDoSave(seq){
    /* abortable : la réinitialisation « bibliothèque » annule tout POST en
       vol AVANT son DELETE — jamais de sauvegarde fantôme ressuscitée */
    var ac=null;
    try{ac=new AbortController()}catch(_e){}
    saveAbortRef.current=ac;
    fetch("/api/montage/save",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify(svmSavePayload()),signal:ac?ac.signal:void 0})
      .then(function(res){return res.json().catch(function(){return {}})
        .then(function(d2){return {ok:res.ok&&d2&&d2.ok,d:d2}})})
      .then(function(o){
        if(!o.ok)throw 0;
        if(saveSeqRef.current===seq)setDirty(!1);
        setSaveInfo({ok:!0,at:Date.now()})})
      .catch(function(err){
        if(err&&err.name==="AbortError")return; /* reset volontaire */
        setSaveInfo({ok:!1,at:Date.now()})})}
  x.useEffect(function(){
    if(proj.demo||!dirty)return;
    var seq=++saveSeqRef.current;
    var t=setTimeout(function(){svmDoSave(seq)},1500);
    return function(){clearTimeout(t)}},[clips,proj,durMaster,ducking,dirty]);

  /* bouton « bibliothèque » (confirmé) : DELETE de la sauvegarde puis
     rechargement du projet — la Bibliothèque redevient la source */
  function svmLibReset(){
    setLibArm(!1);
    /* un autosave encore en vol serait traité APRÈS le DELETE et
       ressusciterait la sauvegarde : on l'annule d'abord */
    if(saveAbortRef.current){try{saveAbortRef.current.abort()}catch(_e){}}
    fetch("/api/montage/save",{method:"DELETE"})
      .then(function(res){if(!res.ok)throw 0;
        return fetch("/api/montage/project")})
      .then(function(res){return res.json()})
      .then(function(d){
        saveSeqRef.current++; /* les autosaves en vol ne comptent plus */
        setSaveInfo(null);
        if(svmApplyProject(d))
          fireNote(dzT("montage.sauvegarde.reinitialisee"));
        else
          fireNote(dzT("montage.sauvegarde.effacee_vide"))})
      .catch(function(){fireNote(dzT("montage.sauvegarde.reinit_impossible"))})}

  /* catalogue du moteur Effects / Mask (sélecteur d'effets par clip) */
  x.useEffect(function(){var alive=!0;
    fetch("/api/montage/effects").then(function(res){return res.json()}).then(function(d){
      if(alive&&d&&d.effects)setFxCat(d.effects)}).catch(function(){});
    return function(){alive=!1}},[]);

  /* voix du tiroir Narration — même catalogue /api/voices que Son & VFX
     (clonées en tête), chargé à la première ouverture du tiroir ; choix
     mémorisé (dz_narr_voice). Clé absente : liste de démonstration, la
     synthèse renverra l'erreur backend honnête. */
  x.useEffect(function(){
    if(!narrOn||narrVoices!==null)return;
    var alive=!0;
    fetch("/api/voices").then(function(res){return res.json()}).then(function(d){
      if(!alive)return;
      var list=(d&&d.voices||[]).map(function(v){
        return {id:v.voice_id,name:v.name||v.voice_id,cloned:v.category==="cloned"}});
      if(d&&d.enabled&&list.length){
        list.sort(function(a,b){return (b.cloned?1:0)-(a.cloned?1:0)});
        setNarrVoices({enabled:!0,list:list});
        var saved=null;try{saved=localStorage.getItem("dz_narr_voice")}catch(_e){}
        var pref=list.find(function(v){return v.id===saved})||
          list.find(function(v){return /prophet/i.test(v.name)})||
          list.find(function(v){return v.cloned})||list[0];
        setNarrVoice(pref.id)}
      else{setNarrVoices({enabled:!1,list:SVM_DEMO_VOICES});setNarrVoice("prophet")}
    }).catch(function(){
      if(alive){setNarrVoices({enabled:!1,list:SVM_DEMO_VOICES});setNarrVoice("prophet")}});
    return function(){alive=!1}},[narrOn,narrVoices]);
  /* tarif narration (B) — chargé une fois à la première ouverture du
     tiroir : /api/voice-models donne le $/car EFFECTIF du modèle par défaut
     de l'app (base × multiplicateur, overrides pricing.json compris — c'est
     le modèle que POST /audio/voiceover utilisera) ; repli sur
     /api/cost/pricing (elevenlabs_usd_per_char × elevenlabs_model_mult
     scalaire éventuel) ; repli final silencieux : 0,00003 $/car. */
  x.useEffect(function(){
    if(!narrOn||narrRate!==null)return;
    var alive=!0;
    Promise.all([
      fetch("/api/voice-models").then(function(res){return res.json()}).catch(function(){return null}),
      fetch("/api/cost/pricing").then(function(res){return res.json()}).catch(function(){return null})
    ]).then(function(rr){
      if(!alive)return;
      var vm=rr[0],pr=rr[1],rate=0;
      if(vm&&vm.models&&vm.models.length){
        var def=vm.models.find(function(m){return m.id===vm["default"]})||vm.models[0];
        rate=Number(def&&def.usd_per_char)||0}
      if(!(rate>0)&&pr){
        var base=Number(pr.elevenlabs_usd_per_char),
            mm=pr.elevenlabs_model_mult,
            mult=typeof mm==="number"&&mm>0?mm:1;
        if(base>0)rate=base*mult}
      setNarrRate(rate>0?rate:3e-5)});
    return function(){alive=!1}},[narrOn,narrRate]);
  /* un seul flux audible — la lecture principale coupe l'écoute de bloc,
     fermer le tiroir l'arrête aussi */
  x.useEffect(function(){
    if(playing||!narrOn){
      var a=narrAudioRef.current;
      if(a){try{a.pause()}catch(_e){}narrAudioRef.current=null}
      setNarrPlayId(function(p){return p?"":p})}},[playing,narrOn]);
  x.useEffect(function(){return function(){var a=narrAudioRef.current;
    if(a){try{a.pause()}catch(_e){}}}},[]);

  var sel=clips.find(function(c){return c.id===selId})||null;
  var mixRows=svmMixRows(proj.mixDb);
  var firstA2=svmFirstA2Id(clips); /* clip musique bouclée dans les bornes de son clip (fade_out = fondu de fin du clip) */
  /* jumeaux A1 « son du plan » désynchronisés par une vitesse V1 (C) :
     job_id → % de vitesse du plan. La vitesse V1 ne ré-échantillonne JAMAIS
     l'audio A1 — le chip d'avertissement vit sur le clip ET sur son bloc de
     narration. */
  var v1SpeedJobs={};
  clips.forEach(function(c){
    if(trackKind(c.tr)==="video"&&c.src&&c.src.job_id&&typeof c.speed==="number"&&
       c.speed>0&&Math.abs(c.speed-1)>1e-6)
      v1SpeedJobs[c.src.job_id]=Math.round(c.speed*100)});   /* t117 : pistes hautes comme V1 */

  /* boucle de lecture — l'horloge suit le mode. Aperçu rendu (previewUrl) :
     le fichier composite reste maître. Projet réel sans aperçu : le <video>
     source du clip V1 courant fait l'horloge quand il joue (le son du plan
     est audible) ; trous, images et marche arrière = horloge murale. Démo :
     horloge murale. La vitesse J/K/L vit dans spdRef (±1/2/4), lue à chaque
     frame sans relancer l'effet ; l'arrière est un shuttle par seeks rAF. */
  x.useEffect(function(){
    if(!playing)return;
    var v=videoRef.current;
    if(v&&previewUrl&&spdRef.current>0){v.play().catch(function(){})}
    var last=performance.now();
    var step=function(now){var dt=(now-last)/1000;last=now;
      var s=spdRef.current,p=null,vd=videoRef.current;
      if(vd&&previewUrl){
        if(s>0){
          if(vd.playbackRate!==s)vd.playbackRate=s;
          if(vd.paused&&!vd.ended)vd.play().catch(function(){});
          if(vd.ended){setPlaying(!1);return}
          setPh(Math.min(durRef.current,vd.currentTime))}
        else{
          if(!vd.paused)vd.pause();
          p=phRef.current+dt*s;
          if(p<=0){try{vd.currentTime=0}catch(_e){}setPh(0);setSpd(1);setPlaying(!1);return}
          try{vd.currentTime=p}catch(_e){}
          setPh(p)}}
      else{
        if(s>0){
          var lv=liveVideoRef.current;
          if(lv&&!lv.paused&&!lv.ended&&!lv.seeking&&lv.readyState>=2){
            var cs=clipsRef.current,c=null;
            for(var i=0;i<cs.length;i++){if(cs[i].id===lv._svmClip){c=cs[i];break}}
            /* vitesse du clip (C) : le temps SOURCE défile ×s plus vite que
               la timeline — l'horloge divise pour rester en temps montage */
            if(c)p=Math.min(c.end,Math.max(c.start,
              c.start+(lv.currentTime-(c.srcIn||0))/svmSpeedOf(c)))}
          if(p==null)p=phRef.current+dt*s;
          if(p>=durRef.current){setPh(durRef.current);setSpd(1);setPlaying(!1);return}}
        else{
          p=phRef.current+dt*s;
          if(p<=0){setPh(0);setSpd(1);setPlaying(!1);return}}
        setPh(p)}
      rafRef.current=requestAnimationFrame(step)};
    rafRef.current=requestAnimationFrame(step);
    return function(){if(rafRef.current)cancelAnimationFrame(rafRef.current);
      var vd=videoRef.current;if(vd&&!vd.paused)vd.pause();
      livePoolPause()}},[playing,previewUrl]);

  var seekTo=x.useCallback(function(p){setPh(p);var v=videoRef.current;
    if(v&&previewRef.current){try{v.currentTime=Math.min(p,v.duration||p)}catch(_e){}}},[]);
  /* bascule source <-> 480p (chip qualité) : le <video> fraîchement monté
     est recalé sur la tête de lecture, la position ne saute pas */
  x.useEffect(function(){var v=videoRef.current;
    if(v&&previewUrl){try{v.currentTime=Math.min(phRef.current,v.duration||phRef.current)}catch(_e){}}},[previewUrl]);

  /* ── lecteur vivant — la vraie frame des SOURCES sous la tête, avant tout
     rendu. Pool d'éléments média par source (préfixe de rôle b:/o:, cap 6,
     éviction LRU des éléments détachés) : revenir sur un plan déjà vu est
     instantané. Tout ce qui est par-frame (currentTime, couches) est écrit
     impérativement dans deux hôtes (fond V1 / overlays V2) — aucun
     re-render ajouté par frame. ── */
  function livePoolKey(src,role){return role+(src.job_id?"j:"+src.job_id:"i:"+src.image)}
  function livePoolGet(src,role){
    var pool=livePoolRef.current||(livePoolRef.current=new Map());
    var key=livePoolKey(src,role),it=pool.get(key);
    if(!it){
      var el;
      if(src.job_id){el=document.createElement("video");
        el.src="/api/jobs/"+src.job_id+"/video";el.preload="auto";
        el.muted=!0;el.playsInline=!0}
      else{el=document.createElement("img");
        el.src="/api/images/"+encodeURIComponent(src.image);el.alt="";el.draggable=!1}
      el.className="svm-livemedia";
      it={el:el,video:!!src.job_id,at:0};pool.set(key,it);
      while(pool.size>6){
        var old=null,ok=null;
        pool.forEach(function(o,k2){if(o!==it&&!o.el.isConnected&&(!old||o.at<old.at)){old=o;ok=k2}});
        if(!old)break;
        if(old.video){try{old.el.pause();old.el.removeAttribute("src");old.el.load()}catch(_e){}}
        /* vu-mètre : libère les nœuds WebAudio d'un élément évincé (jamais réutilisé) */
        if(old.el._svmVuSrc){try{old.el._svmVuSrc.disconnect()}catch(_e){}
          try{old.el._svmVuAn.disconnect()}catch(_e){}
          old.el._svmVuSrc=null;old.el._svmVuAn=null;old.el._svmVuErr=1}
        if(old.el._svmVuKAn){try{old.el._svmVuKHp.disconnect()}catch(_e){}
          try{old.el._svmVuKHs.disconnect()}catch(_e){}
          try{old.el._svmVuKAn.disconnect()}catch(_e){}
          old.el._svmVuKHp=null;old.el._svmVuKHs=null;old.el._svmVuKAn=null}
        pool.delete(ok)}}
    it.at=++liveSeqRef.current;
    return it}
  function livePoolPause(){var pool=livePoolRef.current;
    if(pool)pool.forEach(function(o){if(o.video&&!o.el.paused){try{o.el.pause()}catch(_e){}}})}
  function livePlay(el){ /* un seul play() en vol par élément */
    if(el._svmPp)return;el._svmPp=1;
    var pr=el.play();
    if(pr&&pr.then)pr.then(function(){el._svmPp=0},function(){el._svmPp=0});
    else el._svmPp=0}
  /* écritures currentTime du scrub : throttle rAF — une écriture par frame
     et par élément, la dernière valeur gagne */
  function liveSeek(el,t2){
    var m=livePendRef.current||(livePendRef.current=new Map());
    m.set(el,t2);
    if(liveRafRef.current)return;
    liveRafRef.current=requestAnimationFrame(function(){
      liveRafRef.current=0;
      var mm=livePendRef.current;livePendRef.current=null;
      if(mm)mm.forEach(function(tt,el2){
        if(el2.isConnected&&Math.abs(el2.currentTime-tt)>.02){
          try{el2.currentTime=tt}catch(_e){}}})})}
  /* synchro des couches après CHAQUE rendu — idempotente et bon marché */
  function liveSync(){
    /* D-12 — LE VOILE DES TROIS FONDUS JOUABLES EN DIRECT. En TÊTE :
       `liveSync` sort tôt quand les hôtes ne sont pas montés, et le
       voile doit être remis à zéro même dans ce cas.
       LA TÊTE EST BORNÉE COMME CELLE DE L'IMAGE, pas brute : le clip
       montré est choisi sur `min(ph, dur-0.001)` (trois lignes plus
       bas) — voiler sur `ph` aurait fait, à la toute fin de la
       timeline, un voile qui ne correspond plus à l'image affichée.
       « dim » (le fondu simple) est voilé EN NOIR comme `fadeblack`,
       et c'est assumé : avec un hôte unique les deux se voient
       PAREIL à l'écran — seul le rendu ffmpeg les sépare (l'un
       croise deux images, l'autre passe par le noir). La couche
       garde le verdict distinct ; l'écran ne peut pas encore le
       montrer. L'hôte n'est jamais touché : il est noir, et rien
       n'est écrit sur un élément média partagé par le pool.
       LA SIGNATURE `_dzVeil` ÉVITE L'ÉCRITURE INUTILE : `liveSync`
       tourne à CHAQUE frame et le voile est nul presque tout le
       temps — sans elle, deux écritures de style par frame pour
       rien. Même parade que `_svmTfSig` et `_svmKey` plus bas. */
    var dzVe=dzVeilRef.current;
    if(dzVe){
      var dzVt=Math.min(phRef.current,Math.max(0,durRef.current-.001));
      var dzVv=DzTracks.veil(clipsRef.current,dzVt);
      var dzVk=dzVv.color+"|"+dzVv.alpha;
      if(dzVe._dzVeil!==dzVk){dzVe._dzVeil=dzVk;
        dzVe.style.background=(dzVv.color&&dzVv.color!=="dim")?dzVv.color:"#000";
        dzVe.style.opacity=String(dzVv.alpha||0)}}
    /* TT8 (D-21) — L'APERCU VIVANT DU CARTON, au meme endroit et
       pour les memes raisons que le voile : EN TETE, parce que
       `liveSync` sort tot quand les hotes ne sont pas montes et
       que l'apercu doit etre EFFACE meme dans ce cas -- sinon un
       titre survivrait a un passage en apercu 480p, ou l'image
       porte deja le titre GRAVE : on l'aurait vu en double.
       LA TETE EST BORNEE COMME CELLE DU VOILE (`dzVt`), pas brute :
       le clip montre est choisi sur `min(ph, dur-0.001)`, et un
       carton qui finit exactement a la fin de la timeline aurait
       disparu une frame avant l'image qu'il accompagne.
       LA SIGNATURE `_dzHtml` EVITE L'ECRITURE INUTILE : `liveSync`
       tourne a CHAQUE frame et la chaine est la meme pendant toute
       la duree du carton. Sans elle, un `innerHTML` par frame --
       donc un sous-arbre DETRUIT et RECONSTRUIT soixante fois par
       seconde, ce qui aurait relance l'animation CSS d'entree en
       boucle et rendu le titre illisible. Meme parade que
       `_dzVeil` ci-dessus, `_svmTfSig` et `_svmKey` plus bas.
       LA COUCHE ECHAPPE LE TEXTE (`ttEsc`) : il vient de
       l'utilisateur et il part en `innerHTML`. */
    var dzTtH=dzTtHostRef.current;
    if(dzTtH){
      var dzTtT=Math.min(phRef.current,Math.max(0,durRef.current-.001));
      var dzTtC=DzTracks.titleAt(clipsRef.current,dzTtT);
      var dzTtX=dzTtC?DzTracks.titleHtml(dzTtC,dzTtT):"";
      if(dzTtH._dzHtml!==dzTtX){dzTtH._dzHtml=dzTtX;dzTtH.innerHTML=dzTtX}}
    var host=liveHostRef.current,ov=liveOvRef.current;
    if(!host||!ov){liveVideoRef.current=null;livePoolPause();return}
    var t=Math.min(phRef.current,Math.max(0,durRef.current-.001));
    var cs=clipsRef.current,s=spdRef.current,run=playingRef.current&&s>0;
    /* fond : clip V1 actif — l'élément est réutilisé tant que la source ne
       change pas (une coupe à la lame se traverse sans seek ni re-fetch) */
    var c=svmActiveV1(cs,t),key=c?livePoolKey(c.src,"b"):null;
    if(host._svmKey!==key){
      while(host.firstChild){var rm=host.firstChild;
        if(rm.tagName==="VIDEO"&&!rm.paused){try{rm.pause()}catch(_e){}}
        host.removeChild(rm)}
      liveVideoRef.current=null;host._svmKey=key;
      if(key){var it=livePoolGet(c.src,"b");host.appendChild(it.el);
        if(it.video)liveVideoRef.current=it.el}}
    else if(key)livePoolGet(c.src,"b"); /* rafraîchit le LRU */
    var lv=liveVideoRef.current;
    if(lv&&c){
      lv._svmClip=c.id;
      /* D-13 : le zoom dynamique EN DIRECT -- meme geometrie que le zoompan
         du rendu, sur la <video> active ; ecrit seulement s'il change --
         l'origine 0 0 est posee par la feuille (.svm-live>.svm-livemedia) */
      var dzT=DzTracks.dzCss(c.dz,(t-c.start)/Math.max(.04,c.end-c.start));
      if(lv.style.transform!==dzT)lv.style.transform=dzT;
      /* vitesse du clip V1 (C) : la source défile à vitesse × la timeline —
         le mapping tête→temps source ET le playbackRate suivent, l'aperçu
         est fidèle au rendu (clamp 0.25..4 : la plage HTMLMediaElement) */
      var cspd=svmSpeedOf(c);
      var wt=(c.srcIn||0)+(t-c.start)*cspd;
      /* muet pendant le scrub — le son du plan en lecture ; muet aussi quand
         le bus dialogue (A1 = le son du plan au rendu) est coupé */
      var a1cut=Number(mixRef.current&&mixRef.current.dialogue!=null?mixRef.current.dialogue:0)<=-40;
      /* solo d'écoute : un solo actif ailleurs coupe A1 (le son du plan) —
         écoute locale seulement, le payload de rendu ne bouge jamais */
      var soloM=soloRef.current,anySoloLv=!1,skLv;
      for(skLv in soloM){if(soloM[skLv]){anySoloLv=!0;break}}
      lv.muted=!run||a1cut||(anySoloLv&&!soloM.a1);
      /* gain PAR CLIP + automation du dialogue actif (clip A1 sous la tête) —
         approximation honnête du « son du plan » : dB = gain + interpolation
         des losanges à la tête (≥ 2 points, la règle du payload), volume =
         10^(dB/20) borné 0..1, écrit seulement s'il change */
      var a1g=0,a1c=null;
      for(var i4=0;i4<cs.length;i4++){var kg=cs[i4];
        if(kg.tr==="a1"&&kg.src&&(kg.gain||svmVpOf(kg))&&kg.start<=t&&t<kg.end){
          a1c=kg;a1g=Number(kg.gain)||0;break}}
      var a1vp=a1c?svmVpOf(a1c):null;
      var a1db=a1vp&&a1vp.length>=2?a1g+svmVpDbAt(a1vp,t-a1c.start):a1g;
      var vol=a1db?Math.min(1,Math.max(0,Math.round(Math.pow(10,a1db/20)*1000)/1000)):1;
      if(lv.volume!==vol)lv.volume=vol;
      if(run){
        var prate=Math.min(4,Math.max(.25,s*cspd));
        if(lv.playbackRate!==prate)lv.playbackRate=prate;
        if(Math.abs(lv.currentTime-wt)>.35){try{lv.currentTime=wt}catch(_e){}}
        if(lv.paused&&!lv.ended)livePlay(lv)}
      else{
        if(!lv.paused)lv.pause();
        if(lv.playbackRate!==1)lv.playbackRate=1;
        liveSeek(lv,wt)}}
    /* L7-B D-40 : le cadrage EN DIRECT -- la fenetre du crop du rendu, a la tete en temps de source,
       sur la <video> active ou l'<img> du fond V1 */
    var rfEl=c?(lv||(host.firstChild&&host.firstChild.tagName==="IMG"?host.firstChild:null)):null;
    if(rfEl){var rfP=DzTracks.reframeCss(c,(t-c.start)*svmSpeedOf(c),rfEl.videoWidth||rfEl.naturalWidth,
      rfEl.videoHeight||rfEl.naturalHeight,rfEl.clientWidth,rfEl.clientHeight);
      if(rfEl.style.objectPosition!==rfP)rfEl.style.objectPosition=rfP}
    /* overlays V2 actifs à t, au-dessus du fond, opacité appliquée */
    var act={};
    cs.forEach(function(k){
      if(DzTracks.isOverlayTrack(k.tr,dzTracksRef.current)&&k.src&&(k.src.job_id||k.src.image)&&k.start<=t&&t<k.end)act[k.id]=k});
    /* P14 — l'ORDRE d'empilement suit l'ordre des pistes (la plus haute
       listée au-dessus, même loi que `layer` au rendu) : `dzOrd` est
       l'ordre d'ajout au DOM, le plus bas d'abord ; `dzReord` ne vaut
       vrai que si l'ensemble actif ou son ordre a changé — sinon aucune
       écriture DOM, comme la garde de signature de la transformation. */
    var dzOrd=DzTracks.overlayOrder(Object.keys(act),cs,dzTracksRef.current),
        dzOrdSig=dzOrd.join("|"),dzReord=ov._dzOrdSig!==dzOrdSig;
    ov._dzOrdSig=dzOrdSig;
    for(var i=ov.children.length-1;i>=0;i--){var ch=ov.children[i],kc=act[ch._svmId];
      if(!kc||livePoolKey(kc.src,"o")!==ch._svmKey){
        if(ch.tagName==="VIDEO"&&!ch.paused){try{ch.pause()}catch(_e){}}
        if(tfRoRef.current)tfRoRef.current.unobserve(ch);
        ov.removeChild(ch)}}
    dzOrd.forEach(function(id){
      var k=act[id],el=null;
      for(var i2=0;i2<ov.children.length;i2++){
        if(ov.children[i2]._svmId===id){el=ov.children[i2];break}}
      if(!el){var it2=livePoolGet(k.src,"o");el=it2.el;
        el._svmId=id;el._svmKey=livePoolKey(k.src,"o");ov.appendChild(el);
        if(tfRoRef.current)tfRoRef.current.observe(el);dzReord=!0}
      /* P14 — un enfant déjà là est REMIS EN QUEUE quand l'ordre a
         changé : appendChild déplace sans recréer ; rien n'est touché
         quand `dzReord` est faux. */
      else if(dzReord)ov.appendChild(el);
      /* D-14 : opacité interpolée sur les points porteurs (statique sinon) */
      var kOp=DzTracks.mpLerp2(svmMpOf(k)||[],t-k.start,"opacity",k.opacity==null?1:k.opacity);
      el.style.opacity=kOp>=1?"":String(Math.round(kOp*100)/100);
      /* sélection + manipulation directe : la couche est saisissable ; la
         transformation du clip (ou du geste en cours) est appliquée ici,
         garde de signature — aucune écriture DOM quand rien ne change */
      if(!el._svmTtl){el._svmTtl=1;
        el.title=dzT("montage.overlay.aide")}
      el.onpointerdown=ovOvDown;el.ondblclick=ovOvDbl;
      /* transformation effective à t : les keyframes de position (R4b)
         s'interpolent ici — le scrub et la lecture MONTRENT le mouvement ;
         sans point, svmOvTfAt rend la statique (ou null : cover intact) */
      var ktf=dragTfRef.current&&dragTfRef.current.id===id?dragTfRef.current:svmOvTfAt(k,t);
      /* L7 D-19 : coins et ombre entrent dans la signature — un rayon changé est ré-appliqué */
      var tsig=ktf?ktf.x+"|"+ktf.y+"|"+ktf.scale+"|"+ktf.rotate+"|"+(ktf.radius||0)+"|"+(ktf.shadow||0):"";
      if(el._svmTfSig!==tsig){el._svmTfSig=tsig;svmApplyTf(el,ktf)}
      if(el.tagName==="VIDEO"){
        el.muted=!0; /* un overlay ne porte jamais le son */
        var kSpd=svmSpeedOf(k);   /* t117 : la vitesse d'un plan haut, comme V1 */
        var wt2=(k.srcIn||0)+(t-k.start)*kSpd;
        if(run){
          if(el.playbackRate!==s*kSpd)el.playbackRate=s*kSpd;
          if(Math.abs(el.currentTime-wt2)>.35){try{el.currentTime=wt2}catch(_e){}}
          if(el.paused&&!el.ended)livePlay(el)}
        else{if(!el.paused)el.pause();liveSeek(el,wt2)}}});
    tfSyncBox()}
  x.useEffect(function(){liveSync()});
  /* préchauffe : les premières sources V1 (jusqu'au cap du pool) se chargent
     avant d'être atteintes — changement de plan instantané dès la 1re lecture */
  x.useEffect(function(){
    if(previewUrl||proj.demo)return;
    clips.slice().sort(function(a,b){return a.start-b.start}).forEach(function(c){
      if(c.tr!=="v1"||!c.src||!c.src.job_id)return;
      var pool=livePoolRef.current;
      if(pool&&pool.size>=6)return;
      livePoolGet(c.src,"b")})},[clips,previewUrl,proj.demo]);
  x.useEffect(function(){return function(){ /* démontage : libère le pool */
    if(liveRafRef.current)cancelAnimationFrame(liveRafRef.current);
    var pool=livePoolRef.current;
    if(pool){pool.forEach(function(o){
      if(o.video){try{o.el.pause();o.el.removeAttribute("src");o.el.load()}catch(_e){}}
      if(o.el._svmVuSrc){try{o.el._svmVuSrc.disconnect()}catch(_e){}
        try{o.el._svmVuAn.disconnect()}catch(_e){}
        o.el._svmVuSrc=null;o.el._svmVuAn=null;o.el._svmVuErr=1}
      if(o.el._svmVuKAn){try{o.el._svmVuKHp.disconnect()}catch(_e){}
        try{o.el._svmVuKHs.disconnect()}catch(_e){}
        try{o.el._svmVuKAn.disconnect()}catch(_e){}
        o.el._svmVuKHp=null;o.el._svmVuKHs=null;o.el._svmVuKAn=null}});
      pool.clear()}}},[]);
  /* ── vu-mètre live (rangée MIXAGE) — honnête : il mesure le flux réellement
     audible (aperçu 480p composite, ou le son du plan V1 / bus dialogue en
     lecture directe — musique et SFX ne jouent pas en live). WebAudio :
     UN SEUL createMediaElementSource PAR ÉLÉMENT à vie (marqué sur l'élément,
     jamais deux sources), branché analyser ET destination ; câblé uniquement
     quand l'AudioContext partagé tourne (sinon la re-route couperait le son) ;
     échec → dégradation silencieuse ; rAF SEULEMENT pendant la lecture. ── */
  function svmVuWire(el){
    if(!el)return null;
    if(el._svmVuAn)return el._svmVuAn;
    if(el._svmVuErr)return null;
    var ctx=svmSharedAC();
    if(!ctx){el._svmVuErr=1;return null}
    if(ctx.state!=="running"){ /* pas de re-route tant que le contexte dort */
      try{if(ctx.resume){var pr=ctx.resume();if(pr&&pr.catch)pr.catch(function(){})}}catch(_e){}
      return null}
    try{
      var src=ctx.createMediaElementSource(el);
      src.connect(ctx.destination); /* d'abord : le son continue de sortir */
      var an=ctx.createAnalyser();an.fftSize=512;an.smoothingTimeConstant=.5;
      src.connect(an);
      el._svmVuSrc=src;el._svmVuAn=an;
      /* chaîne K-weighting PARALLÈLE (R2/I7) : highpass 38 Hz (Q .5) →
         highshelf 1500 Hz +4 dB → analyser dédiée — jamais vers destination,
         le chemin audible ne change pas. Échec isolé : le vu classique vit,
         lufsM reste null (dégradation propre). */
      try{
        var khp=ctx.createBiquadFilter();khp.type="highpass";
        khp.frequency.value=38;khp.Q.value=.5;
        var khs=ctx.createBiquadFilter();khs.type="highshelf";
        khs.frequency.value=1500;khs.gain.value=4;
        var kan=ctx.createAnalyser();kan.fftSize=1024;
        src.connect(khp);khp.connect(khs);khs.connect(kan);
        el._svmVuKHp=khp;el._svmVuKHs=khs;el._svmVuKAn=kan}
      catch(_e2){}
      return an}
    catch(_e){el._svmVuErr=1;return null}}
  x.useEffect(function(){
    if(!playing){vuLvlRef.current={rms:0,peak:0,clip:!1,lufsM:null};return}
    /* canvas .svm-vu = repli sans DzSfx ; la boucle tourne même sans lui :
       elle alimente vuLvlRef, lu par SvmMeterHost (DzSfx.Meter, barre
       transport) — même analyser, deux affichages possibles */
    var cv=vuRef.current,g=null;
    if(cv){try{g=cv.getContext("2d")}catch(_e){g=null}}
    var dpr=Math.min(2,window.devicePixelRatio||1),
        W=Math.round(60*dpr),H=Math.round(10*dpr),bh=Math.round(4*dpr),
        col="",colRed="",colTick="",redX=W,tw=Math.max(1,Math.round(dpr)),TICKX=[];
    if(g){
      if(cv.width!==W)cv.width=W;
      if(cv.height!==H)cv.height=H;
      /* couleurs du thème lues à l'entrée en lecture (deps : theme) —
         vert = niveau, rouge = zone > −3 dBFS, ink4 = ticks */
      var cs9=getComputedStyle(cv);
      col=(cs9.getPropertyValue("--green")||"").trim()||"#5ec8a0";
      colRed=(cs9.getPropertyValue("--red")||"").trim()||"#e35d4a";
      colTick=(cs9.getPropertyValue("--ink4")||"").trim()||"#55514c";
      /* graduation fixe −30/−20/−10/−6/−3 dBFS sur l'échelle −42..0 de
         lvlOf ; la zone rouge démarre à −3 */
      TICKX=[-30,-20,-10,-6,-3].map(function(d2){return Math.round((d2+42)/42*W)});
      redX=Math.round(39/42*W)}
    var raf=0,buf=null,pk=0,pkAt=0,pkLast=0,kbuf=null,kwin=[],rmsSm=0,rmsAt=0;
    function lvlOf(v){ /* −42..0 dBFS → 0..1 */
      if(!(v>0))return 0;
      var db=20*Math.log(v)/Math.LN10;
      return Math.max(0,Math.min(1,(db+42)/42))}
    function step(now){
      raf=requestAnimationFrame(step);
      var el=previewRef.current?videoRef.current:liveVideoRef.current;
      var an=el&&!el.muted?svmVuWire(el):null,rms=0,mx2=0,lm=null;
      if(an){
        if(!buf||buf.length!==an.fftSize)buf=new Uint8Array(an.fftSize);
        an.getByteTimeDomainData(buf);
        var s=0;
        for(var i=0;i<buf.length;i++){var v=(buf[i]-128)/128;s+=v*v;
          var a2=v<0?-v:v;if(a2>mx2)mx2=a2}
        rms=Math.sqrt(s/buf.length)}
      /* LUFS momentané (R2/I7) — puissance moyenne K-weighted par frame,
         fenêtre glissante 400 ms : lufsM = −0.691 + 10·log10(moyenne)
         (approximation mono du BS.1770) ; silence / chaîne absente → null */
      var kan=an&&el?el._svmVuKAn:null;
      if(kan){
        if(!kbuf||kbuf.length!==kan.fftSize)kbuf=new Uint8Array(kan.fftSize);
        kan.getByteTimeDomainData(kbuf);
        var ks=0;
        for(var i2=0;i2<kbuf.length;i2++){var kv=(kbuf[i2]-128)/128;ks+=kv*kv}
        kwin.push({t:now,p:ks/kbuf.length});
        while(kwin.length&&kwin[0].t<now-400)kwin.shift();
        var pm=0;
        for(var i3=0;i3<kwin.length;i3++)pm+=kwin[i3].p;
        pm/=kwin.length||1;
        if(pm>0)lm=-.691+10*Math.log(pm)/Math.LN10}
      else if(kwin.length)kwin.length=0;
      /* RMS lissé (release ~250 ms) : aux frontières de clips / bascules du
         pool l'analyser rend 0 pendant quelques frames — sans lissage le
         readout flashe −∞ pendant que la crête tenue affiche encore une
         valeur (incohérence relevée en duel R2). Montée instantanée. */
      if(rms>=rmsSm)rmsSm=rms;
      else{var rdt=rmsAt?(now-rmsAt)/1000:0;rmsSm=Math.max(rms,rmsSm*Math.exp(-rdt/.25))}
      rmsAt=now;
      /* niveaux partagés (linéaire 0..1) — consommés par SvmMeterHost */
      vuLvlRef.current={rms:rmsSm,peak:mx2,clip:mx2>=.985,lufsM:lm};
      if(!g)return; /* pas de canvas : DzSfx.Meter affiche, rien à dessiner ici */
      var lvl=lvlOf(rmsSm),pv=lvlOf(mx2);
      /* crête : montée instantanée, tenue 600 ms puis RETOMBÉE lente
         (~14 dB/s sur l'échelle −42..0) — l'ancienne crête sautait d'un
         bloc à 0,9 s, jugée illisible */
      var pdt=pkLast?Math.min(.1,(now-pkLast)/1000):0;pkLast=now;
      if(pv>=pk){pk=pv;pkAt=now}
      else if(now-pkAt>600)pk=Math.max(pv,pk-pdt*(14/42));
      g.clearRect(0,0,W,H);
      g.fillStyle=col;
      g.globalAlpha=.22;g.fillRect(0,0,W,bh);g.fillRect(0,H-bh,W,bh); /* rails fantômes */
      /* zone rouge au-delà de −3 dBFS — surimpression discrète sur les rails */
      g.fillStyle=colRed;g.globalAlpha=.18;
      g.fillRect(redX,0,W-redX,bh);g.fillRect(redX,H-bh,W-redX,bh);
      /* ticks de graduation — traversent les deux rails, sous le niveau */
      g.fillStyle=colTick;g.globalAlpha=.55;
      for(var iT=0;iT<TICKX.length;iT++)g.fillRect(TICKX[iT],0,tw,H);
      var w=Math.round(lvl*W);
      if(w>0){g.globalAlpha=.9;
        var wg=Math.min(w,redX);
        g.fillStyle=col;g.fillRect(0,0,wg,bh);g.fillRect(0,H-bh,wg,bh);
        if(w>redX){g.fillStyle=colRed; /* la part au-delà de −3 vire au rouge */
          g.fillRect(redX,0,w-redX,bh);g.fillRect(redX,H-bh,w-redX,bh)}}
      if(pk>0){var px2=Math.min(W-1,Math.max(1,Math.round(pk*W)-1)),
          pw=Math.max(1,Math.round(dpr));
        g.globalAlpha=1;g.fillStyle=px2>=redX?colRed:col;
        g.fillRect(px2,0,pw,bh);g.fillRect(px2,H-bh,pw,bh)}
      g.globalAlpha=1}
    raf=requestAnimationFrame(step);
    return function(){if(raf)cancelAnimationFrame(raf);
      vuLvlRef.current={rms:0,peak:0,clip:!1,lufsM:null}}},[playing,previewUrl,theme]);
  function svmFullscreen(){
    var el=frameRef.current;if(!el)return;
    try{
      if(document.fullscreenElement){
        if(document.exitFullscreen){var pr2=document.exitFullscreen();if(pr2&&pr2.catch)pr2.catch(function(){})}}
      else if(el.requestFullscreen){var pr=el.requestFullscreen();if(pr&&pr.catch)pr.catch(function(){})}}
    catch(_e){}}

  /* ── overlays transformables : cadre de sélection + gestes du lecteur ─────
     La boîte (bordure --accent, 8 poignées d'échelle, poignée de rotation)
     est repositionnée impérativement : liveSync l'appelle après chaque rendu
     et chaque frame de lecture, les gestes la pilotent en direct — aucun
     re-render React par frame. Elle vit HORS de l'échelle vzoom : centre
     écran = 0.5 + (fraction − 0.5)·vzoom, les poignées gardent leur taille
     et suivent l'overlay transformé à tout niveau de zoom. ── */
  function tfSyncBox(){
    var box=tfBoxRef.current,ov=liveOvRef.current,fr2=frameRef.current;
    if(!box)return;
    var id=selRef.current,el=null,k=null,i;
    if(ov&&fr2&&id){
      for(i=0;i<ov.children.length;i++){
        if(ov.children[i]._svmId===id){el=ov.children[i];break}}
      if(el){var cs=clipsRef.current;
        for(i=0;i<cs.length;i++){if(cs[i].id===id){k=cs[i];break}}}}
    if(!el||!k){if(box._svmShown){box._svmShown=0;box.style.display="none"}return}
    var vz=vzRef.current,fw=fr2.clientWidth,fh=fr2.clientHeight;
    /* même transformation effective que liveSync : le cadre suit les
       keyframes de position pendant le scrub et la lecture */
    var tfT=Math.min(phRef.current,Math.max(0,durRef.current-.001));
    var tf=dragTfRef.current&&dragTfRef.current.id===id?dragTfRef.current:svmOvTfAt(k,tfT);
    var cx=fw/2+((tf?tf.x:.5)-.5)*fw*vz,cy=fh/2+((tf?tf.y:.5)-.5)*fh*vz;
    var bw=el.offsetWidth*vz,bh=el.offsetHeight*vz,rot=tf?tf.rotate:0;
    var sig=Math.round(cx*10)+"|"+Math.round(cy*10)+"|"+Math.round(bw*10)+"|"+
            Math.round(bh*10)+"|"+Math.round(rot*10);
    if(box._svmSig!==sig){box._svmSig=sig;
      box.style.left=cx+"px";box.style.top=cy+"px";
      box.style.width=bw+"px";box.style.height=bh+"px";
      box.style.transform="translate(-50%,-50%) rotate("+rot+"deg)"}
    if(!box._svmShown){box._svmShown=1;box.style.display="block"}}
  tfSyncRef.current=tfSyncBox;
  /* la boîte suit aussi ce qu'aucun rendu React ne voit : redimensionnement
     du cadre (fenêtre, plein écran) et médias qui finissent de charger */
  x.useEffect(function(){
    if(typeof ResizeObserver==="undefined")return;
    var ro=new ResizeObserver(function(){if(tfSyncRef.current)tfSyncRef.current()});
    tfRoRef.current=ro;
    if(frameRef.current)ro.observe(frameRef.current);
    var ov=liveOvRef.current;
    if(ov)for(var i=0;i<ov.children.length;i++)ro.observe(ov.children[i]);
    return function(){tfRoRef.current=null;ro.disconnect()}},[]);
  /* geste lecteur (déplacer / échelle / rotation) — écritures impératives
     par frame via dragTfRef (liveSync et la boîte lisent le geste, jamais un
     état périmé), setClips + pushHistory au relâchement UNIQUEMENT. La
     capture du pointeur vit sur le CADRE : si la tête de lecture sort du
     clip pendant le geste (couche retirée), le geste survit et se termine
     proprement (lostpointercapture compris). */
  function ovGesture(mode,e,k){
    e.preventDefault();e.stopPropagation();
    var fr2=frameRef.current;if(!fr2)return;
    try{fr2.setPointerCapture&&fr2.setPointerCapture(e.pointerId)}catch(_c){}
    var frect=fr2.getBoundingClientRect(),vz=vzRef.current;
    /* base du geste = transformation EFFECTIVE à la tête (keyframes
       interpolées comprises) : le drag part de ce qui est à l'écran */
    var tG0=Math.min(phRef.current,Math.max(0,durRef.current-.001));
    var t0=svmOvTfAt(k,tG0)||{x:.5,y:.5,scale:1,rotate:0};
    var h0={clips:clipsRef.current,mixDb:mixRef.current};
    var x0=e.clientX,y0=e.clientY,moved=!1,fired=!1;
    /* L7 D-19 : le geste garde coins et ombre à l'aperçu (jamais écrits par lui : p ne porte que x/y/scale/rotate) */
    var cur={id:k.id,x:t0.x,y:t0.y,scale:t0.scale,rotate:t0.rotate,radius:t0.radius||0,shadow:t0.shadow||0};
    var cpx=frect.left+frect.width/2+(t0.x-.5)*frect.width*vz,
        cpy=frect.top+frect.height/2+(t0.y-.5)*frect.height*vz;
    var d0=Math.max(8,Math.hypot(x0-cpx,y0-cpy)),a0=Math.atan2(y0-cpy,x0-cpx);
    var badge=tfBadgeRef.current,gv=tfGuideVRef.current,gh=tfGuideHRef.current;
    function guide(el2,val,ax){
      if(!el2)return;
      if(val==null){el2.style.display="none";return}
      el2.style[ax==="v"?"left":"top"]=50+(val-.5)*100*vz+"%";
      el2.style.display="block"}
    function showBadge(ev,txt){if(!badge)return;badge.textContent=txt;
      badge.style.left=ev.clientX-frect.left+"px";
      badge.style.top=ev.clientY-frect.top+"px";
      badge.style.display="block"}
    function apply(){
      dragTfRef.current=cur;
      var ov=liveOvRef.current,el2=null,i;
      if(ov)for(i=0;i<ov.children.length;i++){
        if(ov.children[i]._svmId===k.id){el2=ov.children[i];break}}
      if(el2){var tsig=cur.x+"|"+cur.y+"|"+cur.scale+"|"+cur.rotate+"|"+(cur.radius||0)+"|"+(cur.shadow||0);
        if(el2._svmTfSig!==tsig){el2._svmTfSig=tsig;svmApplyTf(el2,cur)}}
      tfSyncBox()}
    function mv(ev){
      if(!moved&&Math.abs(ev.clientX-x0)<3&&Math.abs(ev.clientY-y0)<3)return;
      moved=!0;
      var sv=null,sh=null;
      if(mode==="move"){
        /* aimants : lignes centrales (0.5) et bords (0 / 1) du canvas,
           seuil 2 % — la ligne guide flashe au point d'accroche */
        var nx=t0.x+(ev.clientX-x0)/Math.max(1,frect.width*vz),
            ny=t0.y+(ev.clientY-y0)/Math.max(1,frect.height*vz);
        [0,.5,1].forEach(function(g){
          if(Math.abs(nx-g)<.02){nx=g;sv=g}
          if(Math.abs(ny-g)<.02){ny=g;sh=g}});
        cur.x=Math.min(1.2,Math.max(-.2,nx));
        cur.y=Math.min(1.2,Math.max(-.2,ny))}
      else if(mode==="scale"){
        var d=Math.hypot(ev.clientX-cpx,ev.clientY-cpy);
        cur.scale=Math.min(3,Math.max(.05,t0.scale*d/d0));
        showBadge(ev,Math.round(cur.scale*100)+" %")}
      else{
        var na=Math.atan2(ev.clientY-cpy,ev.clientX-cpx);
        var nr=t0.rotate+(na-a0)*180/Math.PI;
        nr=((nr+180)%360+360)%360-180;
        var sn=Math.round(nr/45)*45; /* aimant 0 / ±45 / ±90 / ±135 / 180 (seuil 3°) */
        if(Math.abs(nr-sn)<3)nr=Math.min(180,Math.max(-180,sn));
        cur.rotate=nr;
        showBadge(ev,Math.round(nr)+"°")}
      guide(gv,sv,"v");guide(gh,sh,"h");
      apply()}
    function up(){
      if(fired)return;fired=!0;
      fr2.removeEventListener("pointermove",mv);
      fr2.removeEventListener("pointerup",up);
      fr2.removeEventListener("lostpointercapture",up);
      dragTfRef.current=null;
      if(badge)badge.style.display="none";
      guide(gv,null,"v");guide(gh,null,"h");
      if(moved){
        /* keyframes posées (R4b) + geste de position / rotation : le drag
           édite le point le PLUS PROCHE de la tête (≤ 0,15 s) ou en pose un
           — comportement CapCut ; l'échelle reste statique (pas de keyframe
           d'échelle), son geste écrit le clip comme avant */
        var kk=null,cs6=clipsRef.current,i6;
        for(i6=0;i6<cs6.length;i6++){if(cs6[i6].id===cur.id){kk=cs6[i6];break}}
        var mp6=kk?svmMpOf(kk):null;
        if(kk&&mp6&&mode!=="scale"){
          var tG6=Math.min(phRef.current,Math.max(0,durRef.current-.001));
          var tl6=Math.max(0,Math.min(Math.max(.01,kk.end-kk.start),tG6-kk.start));
          var res6=svmMpPlace(kk,{t:tl6,x:cur.x,y:cur.y,rotate:cur.rotate});
          if(res6){setDirty(!0);pushHistory(h0);svmMpApply(kk,res6);
            fireNote((res6.posed?dzT("montage.keyframe.posee",{t:svmShort(res6.at)}):dzT("montage.keyframe.editee",{t:
              svmShort(res6.at)})))}
          else{fireNote(dzT("montage.trajectoire.plafond_geste",{n:SVM_MP_CAP}));
            liveSync()}}
        else{setDirty(!0);pushHistory(h0);
          var p={x:Math.round(cur.x*1e4)/1e4,y:Math.round(cur.y*1e4)/1e4,
                 scale:Math.round(cur.scale*1e4)/1e4,
                 rotate:Math.round(cur.rotate*10)/10};
          setClips(clipsRef.current.map(function(c2){
            return c2.id===cur.id?Object.assign({},c2,p):c2}))}}
      else tfSyncBox()}
    fr2.addEventListener("pointermove",mv);
    fr2.addEventListener("pointerup",up);
    fr2.addEventListener("lostpointercapture",up)}
  /* pointerdown / double-clic posés par liveSync sur chaque couche overlay :
     clic = sélectionne le clip, drag = déplace, double-clic = plein cadre */
  function ovOvDown(e){
    var id=e.currentTarget._svmId,cs=clipsRef.current,k=null,i;
    for(i=0;i<cs.length;i++){if(cs[i].id===id){k=cs[i];break}}
    if(!k)return;
    e.stopPropagation();
    if(selRef.current!==id)setSelId(id);
    ovKeysOffRef.current=!1; /* resaisir l'overlay ré-arme les flèches (R4b) */
    if(trackStRef.current[k.tr]&&trackStRef.current[k.tr].l)return; /* verrou : sélection seule */
    if(e.button!==0)return;
    ovGesture("move",e,k)}
  function ovOvDbl(e){
    var id=e.currentTarget._svmId,cs=clipsRef.current,k=null,i;
    for(i=0;i<cs.length;i++){if(cs[i].id===id){k=cs[i];break}}
    /* overlay plein cadre : rien à réinitialiser, le double-clic du cadre
       (remise à zéro du zoom) garde la main */
    if(!k||(!svmOvTfOf(k)&&!svmMpOf(k)))return;
    if(trackStRef.current[k.tr]&&trackStRef.current[k.tr].l)return;
    e.stopPropagation();e.preventDefault();
    svmOvTfReset(id)}
  function ovHandleDown(e,mode){
    var id=selRef.current,cs=clipsRef.current,k=null,i;
    for(i=0;i<cs.length;i++){if(cs[i].id===id){k=cs[i];break}}
    if(!k||!DzTracks.isOverlayTrack(k.tr,dzTracksRef.current)||!k.src)return;
    if(trackStRef.current[k.tr]&&trackStRef.current[k.tr].l)return;
    if(e.button!==0)return;
    ovGesture(mode,e,k)}
  /* transformation — source de vérité UNIQUE du lecteur, de l'inspecteur et
     du payload : les quatre champs sont posés ensemble sur le clip (l'échelle
     est matérialisée même à 100 % — c'est elle qui distingue « transformé »
     de « plein cadre »). Réinitialiser retire les quatre champs : le clip
     redevient octet pour octet celui d'avant. */
  function svmOvTfField(patch){
    var id=selRef.current,now=Date.now();
    if(now-ovHistAt.current>600)pushHistory();
    ovHistAt.current=now;
    setClips(clipsRef.current.map(function(k){
      if(k.id!==id)return k;
      var t=svmOvTfOf(k)||{x:.5,y:.5,scale:1,rotate:0};
      return Object.assign({},k,{x:t.x,y:t.y,scale:t.scale,rotate:t.rotate},patch)}));
    setDirty(!0)}
  function svmOvTfReset(id){
    var cs=clipsRef.current,k=null,i;
    for(i=0;i<cs.length;i++){if(cs[i].id===id){k=cs[i];break}}
    if(!k||(!svmOvTfOf(k)&&!svmMpOf(k)))return;
    pushHistory();
    setClips(cs.map(function(c2){
      if(c2.id!==id)return c2;
      var nk=Object.assign({},c2);
      delete nk.x;delete nk.y;delete nk.scale;delete nk.rotate;
      delete nk.radius;delete nk.shadow; /* L7 D-19 : plein cadre = sans coins ni ombre (la chaîne cover du rendu les ignorerait) */
      delete nk.motion_points; /* plein cadre = trajectoire retirée aussi */
      return nk}));
    setDirty(!0);
    fireNote(dzT("montage.overlay.reinitialise")+
      (svmMpOf(k)?dzT("montage.overlay.trajectoire_retiree"):"."))}
  /* ── R4b : précision + keyframes de position (overlays V2) ──────────────
     ratio hauteur/largeur RÉEL du média — lu sur la couche live
     (videoWidth/videoHeight ou naturalWidth/naturalHeight), sinon sur
     l'élément du pool ; média pas encore chargé → null, l'appelant suppose
     un média carré et le pool est préchauffé pour le clic suivant */
  function svmOvMediaHW(c){
    function rd(el){if(!el)return null;
      var w2=el.videoWidth||el.naturalWidth||0,h2=el.videoHeight||el.naturalHeight||0;
      return w2>0&&h2>0?h2/w2:null}
    var ov=liveOvRef.current,i,v;
    if(ov)for(i=0;i<ov.children.length;i++){
      if(ov.children[i]._svmId===c.id){v=rd(ov.children[i]);if(v)return v}}
    var pool=livePoolRef.current;
    if(pool){var it=pool.get(livePoolKey(c.src,"o"));
      if(it){v=rd(it.el);if(v)return v}}
    if(c.src&&(c.src.job_id||c.src.image))livePoolGet(c.src,"o");
    return null}
  /* grille d'alignement 3×3 — colle le BORD RÉEL de l'overlay au bord du
     canvas avec une marge de 4 % : largeur_frac = scale, hauteur_frac =
     scale·(mediaH/mediaW)·(canvasW/canvasH). UNE entrée d'historique par
     clic ; des keyframes posées → le clic écrit le point le plus proche de
     la tête (≤ 0,15 s) ou en pose un (même règle que le drag du lecteur). */
  function svmOvAlign(gx,gy){
    var c=clipsRef.current.find(function(k){return k.id===selRef.current});
    if(!c||!DzTracks.isOverlayTrack(c.tr,dzTracksRef.current)||!c.src)return;
    var phc=Math.min(phRef.current,Math.max(0,durRef.current-.001));
    var eff=svmOvTfAt(c,phc)||{x:.5,y:.5,scale:1,rotate:0};
    var hw=svmOvMediaHW(c)||1; /* média inconnu : carré supposé, pool préchauffé */
    var wf=eff.scale,hf=eff.scale*hw*svmRatioW(proj.ratio);
    var nx=gx===0?.04+wf/2:gx===1?.96-wf/2:.5;
    var ny=gy===0?.04+hf/2:gy===1?.96-hf/2:.5;
    nx=Math.min(1.2,Math.max(-.2,Math.round(nx*1000)/1000));
    ny=Math.min(1.2,Math.max(-.2,Math.round(ny*1000)/1000));
    if(svmMpOf(c)){
      var tl=Math.max(0,Math.min(Math.max(.01,c.end-c.start),phc-c.start));
      var res=svmMpPlace(c,{t:tl,x:nx,y:ny,rotate:eff.rotate});
      if(!res){fireNote(dzT("montage.trajectoire.plafond",{n:SVM_MP_CAP}));return}
      pushHistory();
      svmMpApply(c,res);
      if(res.posed)fireNote(dzT("montage.keyframe.posee_bord",{t:svmShort(res.at)}))}
    else{
      pushHistory();
      var t=svmOvTfOf(c)||{x:.5,y:.5,scale:1,rotate:0};
      setClips(clipsRef.current.map(function(k){
        if(k.id!==c.id)return k;
        return Object.assign({},k,{x:nx,y:ny,scale:t.scale,rotate:t.rotate})}));
      setDirty(!0)}}
  /* ── mutations des keyframes de position — invariant : motion_points
     TOUJOURS trié par t ; liste vide → champ RETIRÉ (payload d'avant, octet
     pour octet). svmMpPlace est PUR (aucun setState ni historique) : chaque
     appelant pousse le sien (clic = une entrée, drag = h0 au relâchement,
     champs = rafale 600 ms). ── */
  function svmMpPlace(c,vals){
    var pts=svmMpSort(svmMpOf(c)||[]);
    var len=Math.max(.01,c.end-c.start);
    var t=Math.max(0,Math.min(len,Math.round(vals.t*100)/100));
    var bi=-1,bd=SVM_MP_EPS+1e-9,i,d2;
    for(i=0;i<pts.length;i++){d2=Math.abs(pts[i].t-t);
      if(d2<bd){bd=d2;bi=i}}
    if(bi<0&&pts.length>=SVM_MP_CAP)return null;
    var np={t:bi>=0?pts[bi].t:t,
      x:Math.min(1.2,Math.max(-.2,Math.round(vals.x*1000)/1000)),
      y:Math.min(1.2,Math.max(-.2,Math.round(vals.y*1000)/1000)),
      rotate:Math.min(180,Math.max(-180,Math.round((Number(vals.rotate)||0)*10)/10))};
    /* D-14 : scale/opacity du patch, sinon du point écrasé (bornes du backend) */
    DzTracks.mpKeep(np,vals,bi>=0?pts[bi]:null);
    var out=pts.slice();
    if(bi>=0)out[bi]=np;else out.push(np);
    return {pts:svmMpSort(out),posed:bi<0,at:np.t}}
  /* écrit les points + matérialise la transformation (l'échelle statique
     distingue « transformé » ; retirer tous les points rend l'overlay à sa
     position statique d'avant) — aucun pushHistory ici ; le clip est relu
     FRAIS dans le map (jamais un instantané de rendu périmé).
     INVARIANT d'honnêteté : un point UNIQUE ne part pas au rendu (règle des
     2 points du payload) — les statiques x/y/rotate sont donc alignés sur
     lui : lecteur, inspecteur et rendu montrent la même chose dans tous les
     états (aucun ressaut au relâchement, aucune divergence live/rendu). */
  function svmMpApply(c,res){
    setClips(clipsRef.current.map(function(k){
      if(k.id!==c.id)return k;
      var t=svmOvTfOf(k)||{x:.5,y:.5,scale:1,rotate:0};
      var one=res.pts.length===1?res.pts[0]:null;
      return Object.assign({},k,{
        x:one?one.x:t.x,y:one?one.y:t.y,scale:one&&one.scale!=null?one.scale:t.scale,
        opacity:one&&one.opacity!=null?(one.opacity>=1?void 0:one.opacity):k.opacity,
        rotate:one?one.rotate:t.rotate,
        motion_points:res.pts})}));
    setDirty(!0)}
  /* bouton « ◇ position ici » — pose (ou écrase à ≤ 0,15 s) un point
     {t = tête − start, x/y/rotation courants} ; tête hors du clip : refus
     expliqué. UNE entrée d'historique par clic. */
  function svmMpHere(){
    var c=clipsRef.current.find(function(k){return k.id===selRef.current});
    if(!c||!DzTracks.isOverlayTrack(c.tr,dzTracksRef.current)||!c.src)return;
    var phc=Math.min(phRef.current,Math.max(0,durRef.current-.001));
    if(phc<c.start-.001||phc>=c.end){
      fireNote(dzT("montage.position.tete_hors"));return}
    var eff=svmOvTfAt(c,phc)||{x:.5,y:.5,scale:1,rotate:0};
    var res=svmMpPlace(c,{t:phc-c.start,x:eff.x,y:eff.y,rotate:eff.rotate});
    if(!res){fireNote(dzT("montage.trajectoire.plafond",{n:SVM_MP_CAP}));return}
    pushHistory();
    svmMpApply(c,res);
    fireNote(res.posed?
      dzT("montage.position.pose",{t:svmShort(res.at)})+
        (res.pts.length===1?dzT("montage.position.second_point"):"")
      :dzT("montage.position.ecrase",{t:svmShort(res.at)}))}
  function svmMpRemove(id,i2){
    var c=clipsRef.current.find(function(k){return k.id===id});
    var pts=c?svmMpOf(c):null;
    if(!c||!pts||i2>=pts.length)return;
    pushHistory();
    var np=svmMpSort(pts);np.splice(i2,1);
    setClips(clipsRef.current.map(function(k){
      if(k.id!==id)return k;
      var nk=Object.assign({},k);
      if(np.length)nk.motion_points=np;
      else delete nk.motion_points;
      /* invariant : un point restant ne part pas au rendu — les statiques
         s'alignent sur lui (même image au lecteur et au rendu) */
      if(np.length===1){nk.x=np[0].x;nk.y=np[0].y;nk.rotate=np[0].rotate;if(np[0].scale!=null)nk.scale=np[0].scale;if(np[0].opacity!=null)nk.opacity=np[0].opacity>=1?void 0:np[0].opacity}
      return nk}));
    setDirty(!0);
    if(!np.length)fireNote(dzT("montage.trajectoire.retiree"))}
  /* champs X/Y/rotation (et flèches) AVEC des keyframes posées : le réglage
     écrit le point le plus proche de la tête (≤ 0,15 s) ou en pose un —
     même règle que le drag ; une entrée d'historique par rafale de 600 ms
     (motif svmOvTfField). Sans keyframe, svmOvTfField garde la main. */
  function svmMpField(c,patch){
    var phc=Math.min(phRef.current,Math.max(0,durRef.current-.001));
    var tl=Math.max(0,Math.min(Math.max(.01,c.end-c.start),phc-c.start));
    var eff=svmOvTfAt(c,phc)||{x:.5,y:.5,scale:1,rotate:0};
    var vals={t:tl,x:eff.x,y:eff.y,rotate:eff.rotate};
    Object.keys(patch).forEach(function(kk){vals[kk]=patch[kk]});
    var res=svmMpPlace(c,vals);
    if(!res){fireNote(dzT("montage.trajectoire.plafond",{n:SVM_MP_CAP}));return}
    var now=Date.now();
    if(now-ovHistAt.current>600)pushHistory();
    ovHistAt.current=now;
    svmMpApply(c,res);
    if(res.posed)fireNote(dzT("montage.keyframe.posee_reglage",{t:svmShort(res.at)}))}

  /* ── zoom continu 100..800 %, ancré sur un point (curseur ou centre du
     viewport) : le temps sous l'ancre reste sous l'ancre. L'axe temporel est
     décalé de la gouttière 88px ; le scrollLeft est recalé en layout effect
     une fois la nouvelle largeur rendue. ── */
  var zoomApply=x.useCallback(function(np,clientX){
    np=Math.min(800,Math.max(100,np));
    var el=tlScrollRef.current,oldP=zoomPctRef.current;
    if(np===oldP)return;
    if(el){var rect=el.getBoundingClientRect();
      var mx=clientX==null?rect.width/2:clientX-rect.left;
      var W=el.clientWidth*oldP/100,W2=el.clientWidth*np/100;
      var t=W-88>1?Math.max(0,(el.scrollLeft+mx-88)/(W-88)):0;
      pendScrollRef.current=Math.max(0,88+(W2-88)*t-mx)}
    zoomPctRef.current=np;setZoomPct(np)},[]);
  x.useLayoutEffect(function(){
    if(pendScrollRef.current!=null&&tlScrollRef.current){
      tlScrollRef.current.scrollLeft=pendScrollRef.current;pendScrollRef.current=null}},[zoomPct]);
  /* D-7 : la fenêtre visible de la mini-carte — [a,b] en fractions de la largeur défilable (gouttière 88 px déduite),
     recalculée au défilement de .svm-scroll (écouteur posé au montage, retiré au démontage) et à chaque zoom */
  var stMm=x.useState([0,1]),mmView=stMm[0],setMmView=stMm[1];
  var mmCalc=x.useCallback(function(){var el=tlScrollRef.current;if(!el)return;var w=el.scrollWidth-88;
    var a=w>0?Math.max(0,Math.min(1,el.scrollLeft/w)):0,b=w>0?Math.max(a,Math.min(1,(el.scrollLeft+el.clientWidth-88)/w)):1;
    setMmView(function(p){return p[0]===a&&p[1]===b?p:[a,b]})},[]);
  x.useEffect(function(){var el=tlScrollRef.current;if(!el)return;el.addEventListener("scroll",mmCalc);mmCalc();
    return function(){el.removeEventListener("scroll",mmCalc)}},[mmCalc]);
  x.useEffect(function(){mmCalc()},[zoomPct,mmCalc]);
  /* Ctrl+molette sur la timeline. Listener natif non passif : l'onWheel React
     est passif et ne bloquerait pas le zoom pleine page du navigateur. */
  x.useEffect(function(){var el=tlScrollRef.current;if(!el)return;
    function onW(e){if(!(e.ctrlKey||e.metaKey))return;e.preventDefault();
      zoomApply(zoomPctRef.current*Math.pow(1.0015,-e.deltaY),e.clientX)}
    el.addEventListener("wheel",onW,{passive:!1});
    return function(){el.removeEventListener("wheel",onW)}},[zoomApply]);
  /* molette sur un mini-fader d'en-tête (R2/I1) : ±1 dB — même listener natif
     non passif (délégué au scroller), disjoint du zoom (Ctrl y renvoie).
     Une entrée d'historique par rafale de 600 ms (motif nudge). */
  x.useEffect(function(){var el=tlScrollRef.current;if(!el)return;
    function onW(e){
      if(e.ctrlKey||e.metaKey)return;
      var t=e.target&&e.target.closest?e.target.closest(".svm-thmix"):null;
      if(!t)return;
      /* pan horizontal du trackpad : laisser défiler la timeline */
      if(Math.abs(e.deltaY)<=Math.abs(e.deltaX))return;
      e.preventDefault();
      var bus=t.getAttribute("data-bus");
      if(!bus||!(bus in SVM_DEMO_MIX))return;
      var cur=Number(mixRef.current&&mixRef.current[bus]!=null?mixRef.current[bus]:SVM_DEMO_MIX[bus]);
      var now=Date.now();
      if(now-mixWheelAt.current>600)pushHistory();
      mixWheelAt.current=now;
      svmMixSet(bus,cur+(e.deltaY<0?1:-1))}
    el.addEventListener("wheel",onW,{passive:!1});
    return function(){el.removeEventListener("wheel",onW)}},[pushHistory]);
  /* fermer le panneau raccourcis remet recherche, capture, message et
     confirmation à zéro (R2/I6 + R4c) */
  x.useEffect(function(){
    if(kbOn)return;
    setKbQuery("");setKbEdit("");setKbMsg(null);setKbConfirm(!1)},[kbOn]);
  /* ── capture d'une nouvelle combinaison (chip [data-editing] du panneau ?)
     — listener en PHASE DE CAPTURE : la frappe n'atteint ni le handler
     global ni le champ de recherche (toutes les actions court-circuitées).
     Échap annule ; touche réservée au navigateur ou combo déjà prise :
     refus expliqué inline, la capture reste armée. ── */
  x.useEffect(function(){
    if(!kbEdit)return;
    function cap(e){
      /* modificateur seul : la combinaison n'est pas finie */
      if(e.key==="Control"||e.key==="Shift"||e.key==="Alt"||e.key==="Meta"){
        e.preventDefault();e.stopPropagation();return}
      e.preventDefault();e.stopPropagation();
      if(e.stopImmediatePropagation)e.stopImmediatePropagation();
      if(e.key==="Escape"){setKbEdit("");setKbMsg(null);return}
      var combo=svmComboOfEvent(e);
      if(!combo){setKbMsg({id:kbEdit,msg:dzT("montage.raccourcis.non_reconnue")});return}
      var rsv=svmComboReserved(combo);
      if(rsv){setKbMsg({id:kbEdit,msg:dzT("montage.raccourcis.refusee",{combo:combo,raison:rsv})});return}
      var eff=kmRef.current.byId,taken="",id2;
      for(id2 in eff){if(id2!==kbEdit&&eff[id2]===combo){taken=id2;break}}
      if(taken){setKbMsg({id:kbEdit,
        msg:dzT("montage.raccourcis.deja_utilisee",{action:(SVM_ACTION_BY_ID[taken]?SVM_ACTION_BY_ID[taken].lbl:taken)})});
        return}
      var a=SVM_ACTION_BY_ID[kbEdit];
      setKmOv(function(o){var n=Object.assign({},o);
        if(a&&combo===a.combo)delete n[kbEdit];else n[kbEdit]=combo;
        svmKmSave(n);
        return n});
      setKbMsg(null);setKbEdit("")}
    window.addEventListener("keydown",cap,!0);
    return function(){window.removeEventListener("keydown",cap,!0)}},[kbEdit]);

  /* sauts transport — points de coupe V1 (aussi ↑ / ↓ au clavier) */
  var jump=x.useCallback(function(dir){var pts=[0,durRef.current];
    clipsRef.current.forEach(function(c){if(c.tr==="v1")pts.push(c.start,c.end)});
    pts.sort(function(a,b){return a-b});
    var p=phRef.current;
    if(dir<0){for(var i=pts.length-1;i>=0;i--){if(pts[i]<p-.05){seekTo(pts[i]);return}}seekTo(0)}
    else{for(var j2=0;j2<pts.length;j2++){if(pts[j2]>p+.05){seekTo(pts[j2]);return}}seekTo(durRef.current)}},[seekTo]);

  /* lame (bouton + raccourci « blade » de la keymap — Alt+C par défaut) */
  var blade=x.useCallback(function(){
    var p=phRef.current,cs=clipsRef.current,id=selRef.current;
    var c=cs.find(function(k){return k.id===id});
    if(!c||p<=c.start+.05||p>=c.end-.05){fireNote(dzT("montage.lame.hors_clip"));return}
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){
      fireNote(dzT("montage.piste.verrou_lame",{p:c.tr.toUpperCase()}));return}
    pushHistory();
    setClips(cs.map(function(k){return k===c?Object.assign({},c,{end:p}):k})
      /* la moitié droite démarre sur une jonction « cut » éditable (le losange) —
         sans quoi elle hériterait de la transition d'entrée du clip coupé */
      .concat([Object.assign({},c,{id:c.id+"_b"+Math.round(p*10),start:p,
        /* la source avance au rythme du clip : vitesse ×s consomme s fois plus */
        srcIn:(c.srcIn||0)+(p-c.start)*(typeof c.speed==="number"&&c.speed>0?c.speed:1),
        fx:c.fx,transition:"cut",transition_s:0})]));
    setDirty(!0);fireNote(dzT("montage.lame.coupe",{t:svmShort(p)}))},[fireNote,pushHistory]);
  x.useEffect(function(){
    function onKey(e){
      /* Un champ de saisie garde ses touches. L'écran contient des
         <input type="range"> (opacité, intensité) qui consomment déjà
         l'espace et les flèches : sans cette garde, espace basculerait la
         lecture EN PLUS de déplacer le curseur qui a le focus. */
      var el=e.target,tg=(el&&el.tagName||"").toLowerCase();
      if(tg==="input"||tg==="textarea"||tg==="select"||(el&&el.isContentEditable))return;
      /* capture d'une combo en cours (panneau ?) : le listener de capture a
         déjà tout consommé — ceinture et bretelles */
      if(kbEditRef.current)return;
      /* ── résolution combo → action via la keymap (défauts + overrides
         dz_svm_keymap, kmRef). Sans correspondance exacte, Maj+X retombe sur
         l'action de X quand sa variante Maj est définie (±10 images, nudge
         ×10, multi-solo…) ; Ctrl+Maj+<annuler> reste « rétablir », remappage
         suivi. « ? » : Maj+/ AZERTY sérialise déjà en « ? ». ── */
      var act=null,combo=svmComboOfEvent(e);
      if(combo){
        var m=kmRef.current.toAct;
        if(m[combo]!=null)act={id:m[combo],mag:!1};
        else{
          var mi=combo.indexOf("Maj+");
          if(mi>=0){
            var bid=m[combo.slice(0,mi)+combo.slice(mi+4)];
            if(bid==="undo")act={id:"redo",mag:!1};
            else if(bid&&SVM_SHIFT_VARIANTS[bid])act={id:bid,mag:!0}}}}
      /* panneau raccourcis ouvert : seules sa propre touche et Échap agissent
         — les autres raccourcis dorment sous le voile */
      if(kbRef.current){
        if(act&&act.id==="keys_panel"){e.preventDefault();setKbOn(!1)}
        else if(e.key==="Escape"){e.preventDefault();setKbOn(!1)}
        return}
      /* Échap : un overlay sélectionné tient les flèches (R4b) — les rendre
         à la tête de lecture ; sinon la touche reste sans effet ici */
      if(dzLbRef.current){if(e.key==="Escape"){e.preventDefault();setDzLb(!1)}return} /* D-32 : lightbox ouverte = modale au clavier, seul Échap agit (il la ferme) ; l'Échap de l'overlay décrit plus haut suit */
      if(e.key==="Escape"){
        if(dzMkOnRef.current){e.preventDefault();dzMkToggle(!1);return}
        if(gapSelRef.current){e.preventDefault();setGapSel(null);return}
        if(dzScrimRef.current){e.preventDefault();setPop("");setDzFin(null);setDzMenu(null);return}
        if(kbAudioRef.current&&kbAudioRef.current.ovEsc&&kbAudioRef.current.ovEsc())e.preventDefault();
        return}
      if(!act)return;
      var id=act.id,mag=act.mag;
      /* tiroir Sons : couche DzSfx absente, la touche reste morte (le
         panneau ne l'affiche pas non plus) */
      if(id==="sounds_drawer"){if(svmSfx()){e.preventDefault();sfxToggle()}return}
      if(id==="copy"&&window.getSelection&&String(window.getSelection())!=="")return;
      e.preventDefault();
      if(id==="keys_panel"){setKbOn(function(v){return !v});return}
      if(id==="play"){setSpd(1);setPlaying(function(p){return !p});return}
      /* molette de lecture — avant ×1/×2/×4, pause, arrière (shuttle par seeks) */
      if(id==="jog_fwd"){
        if(playingRef.current)setSpd(function(s2){return s2<0?1:Math.min(4,s2*2)});
        else{setSpd(1);setPlaying(!0)}
        return}
      if(id==="jog_back"){
        if(playingRef.current)setSpd(function(s2){return s2>0?-1:Math.max(-4,s2*2)});
        else{setSpd(-1);setPlaying(!0)}
        return}
      if(id==="jog_pause"){setSpd(1);setPlaying(!1);return}
      /* touches de navigation : un overlay V2 sélectionné les prend d'abord
         (R4b — ±0,5 %, mag ±2 %, la direction suit le remappage) ; sinon
         tête de lecture image-exacte (mag : ±10) et sauts de coupe */
      if(id==="step_back"||id==="step_fwd"||id==="cut_prev"||id==="cut_next"){
        var ark=id==="step_back"?"ArrowLeft":id==="step_fwd"?"ArrowRight":
                id==="cut_prev"?"ArrowUp":"ArrowDown";
        if(kbAudioRef.current&&kbAudioRef.current.ovArrow&&
           kbAudioRef.current.ovArrow(ark,mag))return;
        if(id==="cut_prev"){jump(-1);return}
        if(id==="cut_next"){jump(1);return}
        var stp=(mag?10:1)*(id==="step_back"?-1:1);
        seekTo(Math.min(durRef.current,Math.max(0,Math.round(phRef.current*30+stp)/30)));
        return}
      if(id==="home"){seekTo(0);return}
      if(id==="end"){seekTo(durRef.current);return}
      /* plein écran du cadre (miroir du bouton de la barre du lecteur) */
      if(id==="fullscreen"){svmFullscreen();return}
      if(id==="safezones"){setSafeOn(function(v){return !v});return}
      if(id==="delete"){
        /* E-14 : un trou sélectionné passe avant le losange et le clip */
        if(gapSelRef.current){var gs=gapSelRef.current;if(trackStRef.current[gs.tr]&&trackStRef.current[gs.tr].l){fireNote(dzT("montage.piste.verrou_trou",{p:gs.tr.toUpperCase()}));return}
          pushHistory();setClips(DzTracks.trouRipple(clipsRef.current,gs.tr,gs.a,gs.b));setDirty(!0);setGapSel(null);fireNote(dzT("montage.trou.referme",{d:svmShort(gs.b-gs.a),p:gs.tr.toUpperCase()}));return}
        /* mode automation : Suppr retire le losange sélectionné, pas le clip */
        if(kbAudioRef.current&&kbAudioRef.current.vpDel&&kbAudioRef.current.vpDel())return;
        delClip();return}
      if(id==="blade"){blade();return}
      if(id==="undo"){undo();return}
      if(id==="redo"){redo();return}
      if(id==="snap"){setSnap(function(s){return !s});return}
      if(id==="ripple"){setRipple(function(v){return !v});return}
      if(id==="range_in"||id==="range_out"||id==="range_clear"){var dzW=id.slice(6);var dzCur=(dzProjRef.current&&dzProjRef.current.range)||null;var dzNx=DzTracks.rangeSet(dzCur,dzW,phRef.current,dzProjRef.current&&dzProjRef.current.dur);if(dzNx===dzCur||(dzNx&&dzCur&&dzNx.in===dzCur.in&&dzNx.out===dzCur.out))return;pushHistory();setProj(function(p){return Object.assign({},p,{range:dzNx})});setDirty(!0);if(!dzNx&&dzModeRef.current==="remplir")setDzMode("ecraser");if(dzNx&&dzNx.in!=null&&dzNx.out==null)fireNote(dzT("montage.plage.entree",{t:dzNx.in.toFixed(2)}));else if(dzNx&&dzNx.out!=null&&dzNx.in==null)fireNote(dzT("montage.plage.sortie",{t:dzNx.out.toFixed(2)}));return}
      if(id==="range_cut"){var dzRg=DzTracks.rangeFrom(dzProjRef.current&&dzProjRef.current.range);if(!dzRg){fireNote(dzT("montage.plage.aucune"));return}var dzRc=DzTracks.rippleCut(clipsRef.current,dzRg.in,dzRg.out,DzTracks.cutOpts(dzProjRef.current,trackStRef.current));pushHistory();setClips(dzRc.clips);setProj(function(p){return Object.assign({},p,{range:null})});setDirty(!0);if(dzModeRef.current==="remplir")setDzMode("ecraser");fireNote(dzT("montage.plage.coupee",{a:dzRg.in.toFixed(2),b:dzRg.out.toFixed(2),d:dzRc.removed.toFixed(2)}));return}
      if(id==="marker_toggle"){var dzMkL=(dzProjRef.current&&dzProjRef.current.markers)||[];var dzMkT=Number(phRef.current)||0,dzMkN=DzTracks.markerAdd(dzMkL,dzMkT,{});if(dzMkN.length===dzMkL.length){fireNote(dzMkL.length>=200?dzT("montage.marqueur.plafond"):dzT("montage.marqueur.illisible"));return}pushHistory();setProj(function(p){return Object.assign({},p,{markers:dzMkN})});setDirty(!0);fireNote(dzMkN.length<dzMkL.length?(dzT("montage.marqueur.retire",{t:dzMkT.toFixed(2)})):(dzT("montage.marqueur.pose",{t:dzMkT.toFixed(2),touche:svmKeyLabel("marker_index")})));return}
      if(id==="marker_prev"||id==="marker_next"){var dzMkD=id==="marker_next"?1:-1;var dzMkG=DzTracks.markerNext(dzProjRef.current&&dzProjRef.current.markers,phRef.current,dzMkD);if(dzMkG!=null)seekTo(dzMkG);else fireNote((dzMkD>0?dzT("montage.marqueur.aucun_apres"):dzT("montage.marqueur.aucun_avant")));return}
      if(id==="marker_index"){dzMkToggle();return}
      if(id==="swap_left"||id==="swap_right"){var dzC=(clipsRef.current||[]).filter(function(k){return k&&k.id===selRef.current})[0];if(!dzC){fireNote(dzT("montage.echange.selection"));return}if(trackStRef.current[dzC.tr]&&trackStRef.current[dzC.tr].l){fireNote(dzT("montage.piste.verrouillee",{p:dzC.tr.toUpperCase()}));return}var dzSw=DzTracks.swap(clipsRef.current,dzC.id,id==="swap_left"?-1:1);if(dzSw.every(function(k,i){return k===clipsRef.current[i]})){fireNote(dzT("montage.echange.aucun_voisin"));return}pushHistory();setClips(dzSw);setDirty(!0);fireNote((id==="swap_left"?dzT("montage.echange.precedent",{nom:dzC.label||dzC.id}):dzT("montage.echange.suivant",{nom:dzC.label||dzC.id})));return}
      if(id==="title_add"){dzTtAdd();return}
      if(id==="adjust_add"){dzAjAdd();return}
      if(id==="trans_add"){var dzTc=(clipsRef.current||[]).filter(function(k){return k&&k.id===selRef.current&&trackKind(k.tr)==="video"})[0];if(!dzTc){fireNote(dzT("montage.transition.selection"));return}if(trackStRef.current[dzTc.tr]&&trackStRef.current[dzTc.tr].l){fireNote(dzT("montage.piste.verrouillee",{p:String(dzTc.tr).toUpperCase()}));return}if(!DzTracks.voisins(clipsRef.current,dzTc).g){fireNote(dzT("montage.transition.sans_coupe",{nom:dzTc.label||dzTc.id}));return}svmSetTransType(dzTc.id,"fade");fireNote(dzT("montage.transition.fondu_pose",{d:svmTransS(dzTc).toFixed(1),nom:dzTc.label||dzTc.id}));return}
      if(id==="copy"){var dzCp=(clipsRef.current||[]).filter(function(k){return k&&k.id===selRef.current})[0];if(!dzCp){fireNote(dzT("montage.copier.selection"));return}try{localStorage.setItem("dz_montage_clipboard",JSON.stringify({v:1,at:new Date().toISOString(),clip:DzTracks.clipCopy(dzCp)}))}catch(e){fireNote(dzT("montage.copier.indisponible"));return}fireNote(dzT("montage.copier.copie",{nom:dzCp.label||dzCp.id,touche:(svmKeyLabelNow("paste")||dzT("montage.commun.coller"))}));return}
      if(id==="paste"){if(dzProjRef.current&&dzProjRef.current.demo){fireNote(dzT("montage.coller.demo"));return}var dzPs=null;try{dzPs=JSON.parse(localStorage.getItem("dz_montage_clipboard")||"null")}catch(e){dzPs=null}var dzPq=ovSeq.current+1,dzPr=DzTracks.clipPaste(clipsRef.current||[],dzPs,{head:phRef.current,tracks:dzTracksRef.current||svmTracksOf(dzProjRef.current),mode:dzModeRef.current,seq:dzPq,range:dzProjRef.current&&dzProjRef.current.range,locked:(function(){var o={},k;for(k in trackStRef.current)if(trackStRef.current[k]&&trackStRef.current[k].l)o[k]=!0;return o})()});if(dzPr.id==null){fireNote(dzPr.note||dzT("montage.coller.rien"));return}ovSeq.current=dzPq;pushHistory();setClips(dzPr.clips);setSelId(dzPr.id);setDirty(!0);fireNote(dzT("montage.coller.colle",{nom:dzPs.clip.label||dzPr.id,p:String(dzPr.track).toUpperCase(),t:svmShort(Number(dzPr.start)||0),mode:(dzPr.mode!=="ecraser"?dzT("montage.coller.mode",{mode:DzTracks.modeLabel(dzPr.mode)}):""),note:(dzPr.note?" — "+dzPr.note:"")}));return}
      if(id==="grade_copy"){dzGradeCopy(selRef.current);return}
      if(id==="grade_paste"){dzGradePaste(selRef.current);return}
      if(id==="vo_record"){if(typeof dzVoRef.current==="function")dzVoRef.current();else fireNote(dzT("montage.voix_off.pas_prete"));return}
      if(id==="zoom_in"){zoomApply(zoomPctRef.current*1.25);return}
      if(id==="zoom_out"){zoomApply(zoomPctRef.current/1.25);return}
      if(id==="zoom100"){zoomApply(100);return}
      /* tiroir Narration (blocs texte liés aux clips A1) */
      if(id==="narration"){narrToggle();return}
      /* étape 8 du handoff « Barre Outils Flottante » (§4.1) :
         la barre d'outils de création. DEMANDE, pas ordre — le
         Dock tient l'état et le persiste. */
      if(id==="toolbar"){setDzTbReq(function(n){return n+1});return}
      /* ── audio — kbAudioRef porte des closures fraîches par rendu ── */
      if(id==="mute"){if(kbAudioRef.current)kbAudioRef.current.mute();return}
      if(id==="solo"){if(kbAudioRef.current)kbAudioRef.current.solo(mag);return}
      if(id==="fade_in_cycle"){if(kbAudioRef.current)kbAudioRef.current.fade("in");return}
      if(id==="fade_out_cycle"){if(kbAudioRef.current)kbAudioRef.current.fade("out");return}
      if(id==="nudge_left"||id==="nudge_right"){
        if(kbAudioRef.current)kbAudioRef.current.nudge((mag?10:1)*(id==="nudge_left"?-1:1));
        return}
      if(id==="gain_up"||id==="gain_down"){
        if(kbAudioRef.current)kbAudioRef.current.gain(id==="gain_up"?1:-1)}
    }
    window.addEventListener("keydown",onKey);
    return function(){window.removeEventListener("keydown",onKey)}},[blade,delClip,undo,redo,jump,seekTo,zoomApply,narrToggle,sfxToggle]);

  /* scrub sur la règle */
  function phFromEvent(e,el){var rect=el.getBoundingClientRect();
    var f=(e.clientX-rect.left-88)/(rect.width-88);
    return Math.min(durRef.current,Math.max(0,f*durRef.current))}
  function rulerDown(e){var el=e.currentTarget;
    rulerLeave();
    try{el.setPointerCapture&&el.setPointerCapture(e.pointerId)}catch(_c){}
    seekTo(phFromEvent(e,el));
    function mv(ev){seekTo(phFromEvent(ev,el))}
    function up(){el.removeEventListener("pointermove",mv);el.removeEventListener("pointerup",up)}
    el.addEventListener("pointermove",mv);el.addEventListener("pointerup",up)}
  /* survol de la règle SANS bouton : étiquette timecode qui suit la souris —
     la tête ne bouge pas (écritures impératives, aucun re-render) */
  function rulerHover(e){
    var el=hoverTcRef.current;if(!el)return;
    if(e.buttons){el.style.display="none";return}
    var rect=e.currentTarget.getBoundingClientRect();
    var fx=(e.clientX-rect.left-88)/Math.max(1,rect.width-88);
    if(fx<0||fx>1){el.style.display="none";return}
    el.textContent=svmTcFF(fx*durRef.current);
    el.style.left="calc(88px + (100% - 88px) * "+fx+")";
    el.style.display="block"}
  function rulerLeave(){var el=hoverTcRef.current;if(el)el.style.display="none"}

  /* déplacement / rognage de clip (zones de bord 6 px) — magnétisme bords + tête */
  /* Zone de préhension des bords. Elle valait 6 px sans aucun retour visuel :
     le rognage existait mais était introuvable à la souris. Élargie, et bornée
     au tiers du clip pour qu'un clip court garde une zone de déplacement. */
  function svmEdgeAt(clientX,cRect){
    var g=Math.min(10,Math.max(4,cRect.width/3));
    return clientX-cRect.left<g?"l":cRect.right-clientX<g?"r":"m";
  }
  function clipDown(e,c,laneEl){
    if(gapSelRef.current)setGapSel(null); /* E-14 : un clic sur un clip efface le trou sélectionné */
    e.stopPropagation();setSelId(c.id);
    ovKeysOffRef.current=!1; /* resélection : les flèches reviennent à l'overlay (R4b) */
    /* piste verrouillée : la sélection reste possible, tout geste est bloqué */
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l)return;
    var rect=laneEl.getBoundingClientRect(),pxPerS=rect.width/durRef.current;
    var cRect=e.currentTarget.getBoundingClientRect();
    var edge=svmEdgeAt(e.clientX,cRect);
    var x0=e.clientX,s0=c.start,e0=c.end,moved=!1,tgt=e.currentTarget;
    var dzSlip=!!e.altKey&&edge==="m",dzSlide=!!e.shiftKey&&!e.altKey&&edge==="m";
    var dzSd=Number(c.srcDur)||0;
    try{tgt.setPointerCapture&&tgt.setPointerCapture(e.pointerId)}catch(_c){}
    var h0=dzmHistHost(),snapAt=null;
    var edges=[0,durRef.current,phRef.current];
    clipsRef.current.forEach(function(k){if(k.id!==c.id){edges.push(k.start,k.end)}});
    /* ripple : rognage du bord droit d'un clip V1 — les clips suivants de la
       piste suivent le delta (positions d'origine capturées : pas de dérive) */
    /* P10 — la fin du dernier plan entraîné ne se calcule plus :
       elle ne servait qu'au plafond que M17d supprime. */
    var rip=ripple&&c.tr==="v1"&&edge==="r",orig={};
    if(rip)clipsRef.current.forEach(function(k){
      if(k.id!==c.id&&k.tr===c.tr&&k.start>=e0-.001){
        orig[k.id]={s:k.start,e:k.end}}});
    function doSnap(v){if(!snap)return v;var t=8/pxPerS,best=v;
      edges.forEach(function(g){if(Math.abs(g-v)<t){t=Math.abs(g-v);best=g}});
      if(best!==v)snapAt=best;
      return best}
    function mv(ev){var ds=(ev.clientX-x0)/pxPerS;
      if(Math.abs(ev.clientX-x0)>3)moved=!0;if(!moved)return;
      snapAt=null;
      if(dzSlip){setClips(DzTracks.slip(h0.clips,c.id,ds,{srcDur:dzSd}));return}
      if(dzSlide){var dzNs=doSnap(s0+ds);setClips(DzTracks.slide(h0.clips,c.id,dzNs-s0));setSnapT(snapAt);return}
      var w=0,delta=0;
      if(edge==="r"){
        /* P10 — plus de plafond ni de limite de ripple : c'est
           `up()` qui rallonge la timeline AU RELÂCHEMENT. */
        w=Math.max(s0+.3,doSnap(e0+ds));delta=w-e0}
      setClips(clipsRef.current.map(function(k){
        if(k.id!==c.id){
          if(rip&&orig[k.id])return Object.assign({},k,
            {start:orig[k.id].s+delta,end:orig[k.id].e+delta});
          return k}
        if(edge==="m"){var len=e0-s0,ns=doSnap(s0+ds);
          var nsEnd=doSnap(e0+ds);if(nsEnd!==e0+ds&&ns===s0+ds)ns=nsEnd-len;
          /* P10 — le clip va où on le tire ; `up()` étend. */
          ns=Math.max(0,ns);
          return Object.assign({},k,{start:ns,end:ns+len})}
        if(edge==="l"){var v=Math.min(e0-.3,Math.max(0,doSnap(s0+ds)));
          var upd={start:v};
          /* rognage gauche NLE : la source avance d'autant — ×vitesse pour
             un clip accéléré/ralenti (1 s de timeline = s s de source),
             même règle que la lame */
          if(k.src)upd.srcIn=Math.max(0,(c.srcIn||0)+(v-s0)*svmSpeedOf(c));
          return Object.assign({},k,upd)}
        return Object.assign({},k,{end:w})}));
      setSnapT(snapAt)}
    function up(){tgt.removeEventListener("pointermove",mv);tgt.removeEventListener("pointerup",up);
      setSnapT(null);
      if(moved){setDirty(!0);pushHistory(h0);
        /* P10 — la timeline rattrape ce que le geste a poussé dehors.
           TOUS les clips, pas seulement celui qu'on tient : en ripple,
           ce sont les plans ENTRAÎNÉS qui sortent du champ. */
        var dzUd=DzTracks.fitDur(clipsRef.current,durRef.current,0);
        if(dzUd>durRef.current){var dzU0=durRef.current;
          setProj(function(p){return Object.assign({},p,{dur:dzUd})});
          fireNote(dzT("montage.timeline.allongee_geste",{a:svmRuler(Math.round(dzU0)),
            b:svmRuler(Math.round(dzUd))
            
            }))}}}
    tgt.addEventListener("pointermove",mv);tgt.addEventListener("pointerup",up)}

  /* ── édition du mixage : glisser sur le rail = régler le dB du canal ──
     Échelle visuelle de la maquette (w = 78 + 3.4·(dB+12)), inversée et
     clampée à −40..0 dB ; les gains partent au rendu via mix → volume=. */
  function svmMixSet(name,db){
    db=Math.max(-40,Math.min(0,Math.round(db)));
    setProj(function(p){var m=Object.assign({},p.mixDb);m[name]=db;
      return Object.assign({},p,{mixDb:m})});
    setDirty(!0)}
  function mixDown(e,name){
    var el=e.currentTarget;
    var h0={clips:clipsRef.current,mixDb:mixRef.current}; /* une entrée d'historique par geste */
    try{el.setPointerCapture&&el.setPointerCapture(e.pointerId)}catch(_c){}
    function apply(ev){var rect=el.getBoundingClientRect();
      var w=(ev.clientX-rect.left)/Math.max(1,rect.width)*100;
      svmMixSet(name,(Math.max(8,Math.min(100,w))-78)/3.4-12)}
    apply(e);
    function mv(ev){apply(ev)}
    function up(){el.removeEventListener("pointermove",mv);el.removeEventListener("pointerup",up);
      pushHistory(h0)}
    el.addEventListener("pointermove",mv);el.addEventListener("pointerup",up)}

  /* ── mixage PAR CLIP (pistes audio) : gain dB + fondus — le rendu multiplie
     le gain du clip avec le gain de bus (jamais un remplacement). Glissière /
     champs de l'inspecteur : une entrée d'historique par geste (fenêtre
     600 ms, même logique que la durée de transition). 0 = neutre : le champ
     est retiré du clip, le payload reste celui d'avant. ── */
  function svmSetClipAudio(id,patch){
    var now=Date.now();
    if(now-audioHistAt.current>600)pushHistory();
    audioHistAt.current=now;
    setClips(clipsRef.current.map(function(k){
      if(k.id!==id)return k;
      var nk=Object.assign({},k,patch);
      if(!nk.gain)delete nk.gain;
      if(!nk.fade_in)delete nk.fade_in;
      if(!nk.fade_out)delete nk.fade_out;
      /* courbes de fondu (R2/I4) : « lin » (défaut) ou fondu absent → clé
         RETIRÉE — le payload redevient octet pour octet celui d'avant */
      if(!nk.fade_in||!nk.fade_in_curve||nk.fade_in_curve==="lin")delete nk.fade_in_curve;
      if(!nk.fade_out||!nk.fade_out_curve||nk.fade_out_curve==="lin")delete nk.fade_out_curve;
      /* rack SFX + vitesse : au défaut (liste vide / ×1) le champ est RETIRÉ
         du clip — le payload redevient octet pour octet celui d'avant */
      if(nk.fx&&!nk.fx.length)delete nk.fx;
      if(typeof nk.speed!=="number"||!(nk.speed>0)||Math.abs(nk.speed-1)<1e-6)delete nk.speed;
      /* automation (R4) : liste vide → champ retiré, même règle */
      if(nk.volume_points&&!nk.volume_points.length)delete nk.volume_points;
      return nk}));
    setDirty(!0)}
  /* ── vitesse d'un clip V1 réel (C) — facteur 0.25..4 posé sur le clip ;
     100 % RETIRE le champ (payload d'avant, octet pour octet). La durée
     TIMELINE ne bouge jamais (transitions, trous, offsets xfade intacts) :
     c'est la fenêtre SOURCE consommée qui devient durée × vitesse — rendu
     via setpts=PTS/vitesse, lecteur via playbackRate. UNE entrée
     d'historique par changement (le <select> est un geste discret). ── */
  function svmSetV1Speed(id,v){
    v=Number(v);
    if(!isFinite(v)||v<=0)return;
    v=Math.min(4,Math.max(.25,Math.round(v*100)/100));
    var c=clipsRef.current.find(function(k){return k.id===id});
    if(!c||trackKind(c.tr)!=="video"||!c.src||!c.src.job_id)return;   /* t117 : toute piste vidéo */
    var cur=svmSpeedOf(c);
    if(Math.abs(v-cur)<1e-6)return;
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){
      fireNote(dzT("montage.piste.verrou_vitesse",{p:String(c.tr).toUpperCase()}));return}
    pushHistory();
    setClips(clipsRef.current.map(function(k){
      if(k.id!==id)return k;
      var nk=Object.assign({},k);
      if(Math.abs(v-1)<1e-6)delete nk.speed;else nk.speed=v;
      return nk}));
    setDirty(!0);
    /* jumeau A1 « son du plan » : la désynchronisation est annoncée tout de
       suite, pas seulement par le chip */
    if(Math.abs(v-1)>1e-6&&clipsRef.current.some(function(k){
        return k.tr==="a1"&&k.src&&k.src.job_id===c.src.job_id}))
      fireNote(dzT("montage.vitesse.son_decale",{n:Math.round(v*100)}))}
  /* poignées de fondu : drag horizontal vers l'intérieur (0..3 s, clamp à la
     moitié du clip, pas 0,1), rampe redessinée en direct sur la waveform,
     étiquette flottante « 0.6 s » (motif .svm-hovertc via transHoverShow),
     une seule entrée d'historique au relâchement ; stopPropagation — jamais
     de clipDown sous une poignée */
  function fadeDown(e,c,which,laneEl){
    e.stopPropagation();e.preventDefault();
    setSelId(c.id);
    var tgt=e.currentTarget;
    try{tgt.setPointerCapture&&tgt.setPointerCapture(e.pointerId)}catch(_c){}
    var pxPerS=Math.max(1,laneEl.getBoundingClientRect().width)/durRef.current;
    var len=Math.max(.2,c.end-c.start),fmax=Math.min(3,Math.floor(len*5)/10);
    var isIn=which==="in",key=isIn?"fade_in":"fade_out";
    var f0=Number(c[key])||0,x0=e.clientX,last=f0,moved=!1;
    var h0={clips:clipsRef.current,mixDb:mixRef.current};
    function lbl(v){transHoverShow(isIn?c.start+v:c.end-v,v.toFixed(1)+" s")}
    lbl(f0);
    function mv(ev){
      if(Math.abs(ev.clientX-x0)>3)moved=!0;
      if(!moved)return;
      var v=f0+(isIn?1:-1)*(ev.clientX-x0)/pxPerS;
      v=Math.max(0,Math.min(fmax,Math.round(v*10)/10));
      lbl(v);
      if(v===last)return;
      last=v;
      setClips(clipsRef.current.map(function(k){
        if(k.id!==c.id)return k;
        var nk=Object.assign({},k);
        if(v)nk[key]=v;else delete nk[key];
        return nk}))}
    function up(){
      tgt.removeEventListener("pointermove",mv);tgt.removeEventListener("pointerup",up);
      transHoverHide();
      if(moved&&last!==f0){setDirty(!0);pushHistory(h0)}}
    tgt.addEventListener("pointermove",mv);tgt.addEventListener("pointerup",up)}

  /* ── automation de volume (R4) — mutations des points d'un clip. Invariant :
     volume_points TOUJOURS trié par t ; liste vide → champ RETIRÉ (payload
     d'avant, octet pour octet) ; UNE entrée d'historique par opération
     (pose, retrait, aplatir) ou par geste (drag de losange). ── */
  function svmVpWrite(id,pts){
    setClips(clipsRef.current.map(function(k){
      if(k.id!==id)return k;
      var nk=Object.assign({},k);
      if(pts&&pts.length)nk.volume_points=pts;
      else delete nk.volume_points;
      return nk}));
    setDirty(!0)}
  function svmVpAdd(c,t,db){
    var pts=svmVpOf(c)||[];
    if(pts.length>=SVM_VP_CAP){
      fireNote(dzT("montage.automation.plafond",{n:SVM_VP_CAP}));return}
    var len=Math.max(.01,c.end-c.start);
    t=Math.max(0,Math.min(len,Math.round(t*100)/100));
    db=Math.max(SVM_VP_MIN,Math.min(SVM_VP_MAX,Math.round(db*10)/10));
    pushHistory();
    var np=svmVpSort(pts.concat([{t:t,db:db}]));
    svmVpWrite(c.id,np);
    var ni=-1;
    for(var i=0;i<np.length;i++){if(np[i].t===t&&np[i].db===db){ni=i;break}}
    setVpSel({id:c.id,i:ni<0?0:ni});
    if(np.length===1)fireNote(dzT("montage.automation.premier"))}
  function svmVpRemove(id,i2){
    var c=clipsRef.current.find(function(k){return k.id===id});
    var pts=c?svmVpOf(c):null;
    if(!c||!pts||i2>=pts.length)return;
    pushHistory();
    var np=svmVpSort(pts);np.splice(i2,1);
    svmVpWrite(id,np);
    setVpSel(null)}
  function svmVpFlatten(id){
    var c=clipsRef.current.find(function(k){return k.id===id});
    if(!c||!svmVpOf(c))return;
    pushHistory();
    svmVpWrite(id,null);
    setVpSel(null);
    fireNote(dzT("montage.automation.aplatie"))}
  /* drag d'un losange : t horizontal (clampé entre voisins), dB vertical
     (−40..+12 sur la hauteur du clip), étiquette flottante « −12.5 dB »
     (motif .svm-hovertc via transHoverShow), UNE entrée d'historique au
     relâchement ; stopPropagation — jamais de clipDown sous un losange */
  function vpDown(e,c,i2){
    e.stopPropagation();e.preventDefault();
    setSelId(c.id);setVpSel({id:c.id,i:i2});
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l)return;
    if(e.button!==0)return;
    var tgt=e.currentTarget,clipEl=tgt.parentElement;
    if(!clipEl)return;
    try{tgt.setPointerCapture&&tgt.setPointerCapture(e.pointerId)}catch(_c){}
    var rect=clipEl.getBoundingClientRect();
    var len=Math.max(.01,c.end-c.start);
    var pts0=svmVpSort(svmVpOf(c)||[]),p0=pts0[i2];
    if(!p0)return;
    var lo=i2>0?pts0[i2-1].t+.01:0,
        hi=i2<pts0.length-1?pts0[i2+1].t-.01:len;
    if(hi<lo)hi=lo;
    var h0={clips:clipsRef.current,mixDb:mixRef.current};
    var x0=e.clientX,y0=e.clientY,moved=!1,lastT=p0.t,lastDb=p0.db;
    transHoverShow(c.start+p0.t,svmVpDbTxt(p0.db));
    function mv(ev){
      if(!moved&&Math.abs(ev.clientX-x0)<3&&Math.abs(ev.clientY-y0)<3)return;
      moved=!0;
      var t=(ev.clientX-rect.left)/Math.max(1,rect.width)*len;
      t=Math.max(lo,Math.min(hi,Math.round(t*100)/100));
      var db=SVM_VP_MAX-(ev.clientY-rect.top)/Math.max(1,rect.height)*(SVM_VP_MAX-SVM_VP_MIN);
      db=Math.max(SVM_VP_MIN,Math.min(SVM_VP_MAX,Math.round(db*10)/10));
      transHoverShow(c.start+t,svmVpDbTxt(db));
      if(t===lastT&&db===lastDb)return;
      lastT=t;lastDb=db;
      setClips(clipsRef.current.map(function(k){
        if(k.id!==c.id)return k;
        var np=svmVpSort(svmVpOf(k)||[]);
        if(i2>=np.length)return k;
        np[i2]={t:t,db:db};
        return Object.assign({},k,{volume_points:np})}))}
    function up(){
      tgt.removeEventListener("pointermove",mv);tgt.removeEventListener("pointerup",up);
      transHoverHide();
      if(moved&&(lastT!==p0.t||lastDb!==p0.db)){setDirty(!0);pushHistory(h0)}}
    tgt.addEventListener("pointermove",mv);tgt.addEventListener("pointerup",up)}
  /* double-clic (mode ◇, clip audio sélectionné) : pose un losange à
     l'endroit cliqué — t depuis x, dB depuis y */
  function vpDblClick(e,c){
    e.stopPropagation();
    var rect=e.currentTarget.getBoundingClientRect();
    var len=Math.max(.01,c.end-c.start);
    var t=(e.clientX-rect.left)/Math.max(1,rect.width)*len;
    var db=SVM_VP_MAX-(e.clientY-rect.top)/Math.max(1,rect.height)*(SVM_VP_MAX-SVM_VP_MIN);
    svmVpAdd(c,t,db)}

  /* ── muet / verrou de piste — honnêteté : le backend mixe par BUS
     (A1=dialogue, A2=musique, A3=sfx), pas par piste-fichier. Muet = le bus
     part à −40 dB dans payload.mix (visible dans la rangée de mixage) ;
     re-cliquer restaure le niveau d'avant. Pas de muet V1/V2 : le rendu ne
     le supporte pas. Le verrou est un état d'interface (aucun payload). */
  function svmTrackMute(trId){
    var bus=SVM_TRACK_BUS[trId];if(!bus)return;
    var cur=Number(mixRef.current&&mixRef.current[bus]!=null?mixRef.current[bus]:SVM_DEMO_MIX[bus]);
    pushHistory(); /* le mixage change : geste annulable */
    if(cur<=-40){
      var back=trackSt[trId]&&trackSt[trId].pm!=null?trackSt[trId].pm:SVM_DEMO_MIX[bus];
      if(back<=-40)back=SVM_DEMO_MIX[bus];
      svmMixSet(bus,back);
      fireNote(dzT("montage.mute.reactivee",{p:trId.toUpperCase(),bus:bus,db:(back===0?"0 dB":"−"+Math.abs(Math.round(back))+" dB")}))}
    else{
      setTrackSt(function(m){var nm=Object.assign({},m);
        nm[trId]=Object.assign({},nm[trId],{pm:cur});return nm});
      svmMixSet(bus,-40);
      fireNote(dzT("montage.mute.muette",{p:trId.toUpperCase(),bus:bus}))}}
  function svmTrackLock(trId){
    var was=!!(trackSt[trId]&&trackSt[trId].l);
    setTrackSt(function(m){var nm=Object.assign({},m);
      nm[trId]=Object.assign({},nm[trId],{l:!was});return nm});
    fireNote((was?dzT("montage.piste.deverrouillee",{p:trId.toUpperCase()})
      :dzT("montage.piste.verrouillee_tout",{p:trId.toUpperCase()})))}
  /* ── solo d'écoute — exclusif (clic / S) ou additif (Maj) ; état UI pur :
     ni payload, ni historique, ni « NON ENREGISTRÉ » ── */
  function svmTrackSolo(trId,additive){
    if(!SVM_TRACK_BUS[trId])return;
    var turnOn=!soloRef.current[trId];
    setSolo(function(cur){
      if(additive){var nm=Object.assign({},cur);
        if(nm[trId])delete nm[trId];else nm[trId]=!0;
        return nm}
      if(cur[trId]&&Object.keys(cur).length===1)return {};
      var one={};one[trId]=!0;return one});
    if(turnOn&&!soloTaughtRef.current){soloTaughtRef.current=1;
      fireNote(dzT("montage.solo.aide"))}}
  /* actions clavier audio (M / S / D / Alt+flèches) — kbAudioRef est réécrit à
     CHAQUE rendu avec des closures fraîches : le handler clavier global les
     appelle sans élargir ses dépendances ni capturer d'état périmé */
  function svmKbSelClip(){var id=selRef.current;
    return clipsRef.current.find(function(k){return k.id===id})||null}
  kbAudioRef.current={
    mute:function(){
      var c=svmKbSelClip();
      if(!c||!SVM_TRACK_BUS[c.tr]){fireNote(dzT("montage.audio.selection",{touche:svmKeyLabel("mute")}));return}
      svmTrackMute(c.tr)},
    solo:function(add){
      var c=svmKbSelClip();
      if(!c||!SVM_TRACK_BUS[c.tr]){fireNote(dzT("montage.audio.selection",{touche:svmKeyLabel("solo")}));return}
      svmTrackSolo(c.tr,!!add)},
    fade:function(which){
      var c=svmKbSelClip();
      if(!c||!SVM_TRACK_BUS[c.tr]||!c.src){fireNote(dzT("montage.audio.selection_reel",{touche:svmKeyLabel(which==="out"?"fade_out_cycle":"fade_in_cycle")}));return}
      if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){
        fireNote(dzT("montage.piste.verrou_fondu",{p:c.tr.toUpperCase()}));return}
      var key=which==="out"?"fade_out":"fade_in";
      var len=Math.max(.2,c.end-c.start),fmax=Math.min(3,Math.floor(len*5)/10);
      var steps=[0,.3,.6,1],cur=Number(c[key])||0,i=0;
      for(;i<steps.length;i++){if(cur<steps[i]-.001)break}
      var v=i>=steps.length?0:steps[i];
      if(v>fmax)v=0; /* clip trop court pour le cran suivant : retour à 0 */
      var patch={};patch[key]=v;
      svmSetClipAudio(c.id,patch);
      fireNote(dzT("montage.fondu.regle",{fondu:(which==="out"?dzT("montage.fondu.sortie"):dzT("montage.fondu.entree")),v:(v?v.toFixed(1)+" s":dzT("montage.commun.aucun")),nom:c.label}))},
    nudge:function(fr){
      var c=svmKbSelClip();
      if(!c){fireNote(dzT("montage.clip.selection_touche",{touche:svmKeyLabel("nudge_left")+" / "+svmKeyLabel("nudge_right")}));return}
      if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){
        fireNote(dzT("montage.piste.verrou_decalage",{p:c.tr.toUpperCase()}));return}
      var len=c.end-c.start,d=durRef.current;
      /* P10 — plus de plafond : le clip va où on le pousse, et la
         timeline le suit. La note ne parle QUE quand la durée change
         vraiment (une touche maintenue vaut 30 pas par seconde). */
      var ns=Math.max(0,c.start+fr/30);
      ns=Math.round(ns*3000)/3000; /* multiple exact d'1/30 s : zéro dérive */
      if(Math.abs(ns-c.start)<1e-6)return;
      var dzNd=DzTracks.fitDur([{end:ns+len}],d,0);
      var now=Date.now();
      if(now-nudgeHistAt.current>600)pushHistory();
      nudgeHistAt.current=now;
      setClips(clipsRef.current.map(function(k){
        return k.id===c.id?Object.assign({},k,{start:ns,end:ns+len}):k}));
      if(dzNd>d){setProj(function(p){return Object.assign({},p,{dur:dzNd})});
        fireNote(dzT("montage.timeline.allongee_clip",{t:svmRuler(Math.round(dzNd)),
          nom:(c.label||dzT("montage.clip.le_clip"))
          
          }))}
      setDirty(!0)},
    gain:function(dd){
      var c=svmKbSelClip();
      if(!c||!SVM_TRACK_BUS[c.tr]||!c.src){fireNote(dzT("montage.audio.selection_reel",{touche:svmKeyLabel("gain_up")+" / "+svmKeyLabel("gain_down")}));return}
      var g=Math.max(-24,Math.min(12,(Math.round(Number(c.gain)||0))+dd));
      svmSetClipAudio(c.id,{gain:g})},
    /* Suppr en mode automation : retire le losange sélectionné (pas le
       clip) — vrai si l'événement est consommé ; autoOn / vpSel capturés
       frais à chaque rendu (motif kbAudioRef) */
    vpDel:function(){
      if(!autoOn||!vpSel)return !1;
      var c=clipsRef.current.find(function(k){return k.id===vpSel.id});
      var pts=c?svmVpOf(c):null;
      if(!c||!pts||vpSel.i>=pts.length)return !1;
      if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l)return !1;
      svmVpRemove(c.id,vpSel.i);
      return !0},
    /* R4b — flèches sur un overlay V2 sélectionné (source posée) : déplacer
       de ±0,5 % (Maj ±2 %) au lieu de la tête ; keyframes posées → même
       règle que le drag (point le plus proche ≤ 0,15 s, sinon pose). Vrai
       si consommé ; piste verrouillée ou mode rendu à la tête (Échap) →
       faux, les flèches retombent sur la tête de lecture. */
    ovArrow:function(key,shift){
      var c=svmKbSelClip();
      if(!c||!DzTracks.isOverlayTrack(c.tr,dzTracksRef.current)||!c.src)return !1;
      if(ovKeysOffRef.current)return !1;
      if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l)return !1;
      var d=(shift?.02:.005)*(key==="ArrowLeft"||key==="ArrowUp"?-1:1);
      var phc=Math.min(phRef.current,Math.max(0,durRef.current-.001));
      var eff=svmOvTfAt(c,phc)||{x:.5,y:.5,scale:1,rotate:0};
      var horiz=key==="ArrowLeft"||key==="ArrowRight";
      var nv=Math.round(Math.min(1.2,Math.max(-.2,(horiz?eff.x:eff.y)+d))*1000)/1000;
      var patch=horiz?{x:nv}:{y:nv};
      if(svmMpOf(c))svmMpField(c,patch);
      else svmOvTfField(patch);
      return !0},
    /* Échap : rend les flèches à la tête de lecture (jusqu'à resélection) */
    ovEsc:function(){
      var c=svmKbSelClip();
      if(!c||!DzTracks.isOverlayTrack(c.tr,dzTracksRef.current)||!c.src||ovKeysOffRef.current)return !1;
      ovKeysOffRef.current=!0;
      fireNote(dzT("montage.overlay.fleches_rendues"));
      return !0}};

  /* ── édition des transitions de coupe (jonctions V1) ── */
  function svmSetTransType(id,t){
    pushHistory();
    setClips(clipsRef.current.map(function(k){
      if(k.id!==id)return k;
      return t==="cut"?Object.assign({},k,{transition:"cut",transition_s:0})
        :Object.assign({},k,{transition:t,transition_s:svmTransS(k)})}));
    setDirty(!0)}
  /* la glissière émet une rafale d'onChange : une entrée d'historique par
     geste (fenêtre 600 ms), même logique que les gestes pointeur */
  function svmSetTransDur(id,v){
    v=Math.min(1,Math.max(.1,Math.round(v*20)/20));
    var now=Date.now();
    if(now-transHistAt.current>600)pushHistory();
    transHistAt.current=now;
    setClips(clipsRef.current.map(function(k){
      return k.id===id?Object.assign({},k,{transition_s:v}):k}));
    setDirty(!0)}
  function svmApplyTransAll(t,s2){
    var ids={};svmV1Junctions(clipsRef.current).forEach(function(j2){ids[j2.right.id]=1});
    var n=Object.keys(ids).length;
    if(!n){fireNote(dzT("montage.transition.aucune_coupe"));return}
    pushHistory();
    setClips(clipsRef.current.map(function(k){
      return ids[k.id]?Object.assign({},k,{transition:t,transition_s:t==="cut"?0:s2}):k}));
    setDirty(!0);
    fireNote((n>1?dzT("montage.transition.appliquee.plusieurs",{nom:svmTransLabel(t),n:n}):dzT("montage.transition.appliquee.un",{nom:svmTransLabel(t),n:n})))}
  /* étiquette flottante des jonctions (survol du losange + drag de durée) —
     écritures impératives dans un seul élément (motif .svm-hovertc), rien de
     coûteux par frame côté React */
  function transHoverTxt(c,on,s2){
    return svmTransLabel(c.transition)+(on?" · "+(Math.round(s2*100)/100)+" s":"")}
  function transHoverShow(t,txt){var el=transLabelRef.current;if(!el)return;
    el.textContent=txt;
    el.style.left="calc(88px + (100% - 88px) * "+(t/durRef.current)+")";
    el.style.display="block"}
  function transHoverHide(){var el=transLabelRef.current;if(el)el.style.display="none"}
  /* poignées du bloc doré : drag = durée de la transition, SYMÉTRIQUE autour
     de la coupe (le bloc reste centré sur la jonction). Clamp 0,1..1 s, pas
     0,05 ; une seule entrée d'historique au relâchement ; clic sans mouvement
     = ouvrir le réglage (aux petits zooms le bloc couvre le losange). */
  function dzRollDown(e,j2){
    e.stopPropagation();e.preventDefault();
    var tgt=e.currentTarget;
    var lane=tgt.closest?tgt.closest(".svm-lane"):null;
    if(!lane)return;
    if(trackStRef.current[j2.right.tr]&&trackStRef.current[j2.right.tr].l)return;
    try{tgt.setPointerCapture&&tgt.setPointerCapture(e.pointerId)}catch(_c){}
    var pxPerS=Math.max(1,lane.getBoundingClientRect().width)/durRef.current;
    var x0=e.clientX,h0=dzmHistHost(),moved=!1;
    transHoverShow(j2.t,"roll");
    function mv(ev){var ds=(ev.clientX-x0)/pxPerS;
      if(Math.abs(ev.clientX-x0)>3)moved=!0;if(!moved)return;
      transHoverShow(j2.t,"roll "+(ds>=0?"+":"")+ds.toFixed(2)+" s");
      setClips(DzTracks.roll(h0.clips,j2.left.id,j2.right.id,ds))}
    function up(){tgt.removeEventListener("pointermove",mv);tgt.removeEventListener("pointerup",up);
      transHoverHide();if(moved){setDirty(!0);pushHistory(h0)}}
    tgt.addEventListener("pointermove",mv);tgt.addEventListener("pointerup",up)}
  function transSpanDown(e,jc,edge,t){
    e.stopPropagation();e.preventDefault();
    var tgt=e.currentTarget,span=tgt.parentElement,
        lane=span?span.parentElement:null;
    if(!lane)return;
    try{tgt.setPointerCapture&&tgt.setPointerCapture(e.pointerId)}catch(_c){}
    var pxPerS=Math.max(1,lane.getBoundingClientRect().width)/durRef.current;
    var sRect=span.getBoundingClientRect(),cx0=sRect.left+sRect.width/2;
    var s0=svmTransS(jc),x0=e.clientX,last=s0,moved=!1;
    var h0={clips:clipsRef.current,mixDb:mixRef.current};
    transHoverShow(t,s0.toFixed(2)+" s");
    function mv(ev){
      if(Math.abs(ev.clientX-x0)>3)moved=!0;
      if(!moved)return;
      var v=s0+edge*2*(ev.clientX-x0)/pxPerS;
      v=Math.min(1,Math.max(.1,Math.round(v*20)/20));
      transHoverShow(t,v.toFixed(2)+" s");
      if(v===last)return;
      last=v;
      setClips(clipsRef.current.map(function(k){
        return k.id===jc.id?Object.assign({},k,{transition_s:v}):k}))}
    function up(){
      tgt.removeEventListener("pointermove",mv);tgt.removeEventListener("pointerup",up);
      if(moved){setDirty(!0);pushHistory(h0);transHoverShow(t,transHoverTxt(jc,!0,last))}
      else{transHoverHide();openTransPopAt(jc.id,cx0)}}
    tgt.addEventListener("pointermove",mv);tgt.addEventListener("pointerup",up)}
  function openTransPopAt(id,cx0){
    if(transPop&&transPop.id===id){setTransPop(null);return}
    var rr=rootRef.current?rootRef.current.getBoundingClientRect():null;
    var cx=rr?cx0-rr.left:cx0;
    var w=rr?rr.width:window.innerWidth;
    setTransPop({id:id,x:Math.max(8,Math.min(w-284,cx-138))})}
  function openTransPop(id,e){
    var bx=e.currentTarget.getBoundingClientRect();
    openTransPopAt(id,bx.left+bx.width/2)}
  /* fermeture du popover de jonction : clic extérieur ou Échap */
  x.useEffect(function(){
    if(!transPop)return;
    function onDown(e){var el=e.target;
      while(el&&el!==document){
        if(el.classList&&(el.classList.contains("svm-transpop")||el.classList.contains("svm-junc")||el.classList.contains("svm-transspan")))return;
        el=el.parentElement}
      setTransPop(null)}
    function onEsc(e){if(e.key==="Escape")setTransPop(null)}
    window.addEventListener("pointerdown",onDown,!0);
    window.addEventListener("keydown",onEsc,!0);
    return function(){window.removeEventListener("pointerdown",onDown,!0);
      window.removeEventListener("keydown",onEsc,!0)}},[transPop]);
  /* L7 D-3b (24/09/2026, tâche 4-bis) : la jonction en édition — le clip de droite, son voisin de gauche (même mesure
     que le roll), les deux secondes de source (dernière image de A, première de B) et la clé qui date les vignettes */
  var dzAbJ=transPop?clips.filter(function(k){return k&&k.id===transPop.id})[0]||null:null,dzAbG=dzAbJ?DzTracks.voisins(clips,dzAbJ).g:null,
      dzAbS=DzTracks.abSecs(dzAbG,dzAbJ),dzAbK=dzAbS?svmSrcKey(dzAbG.src)+"@"+dzAbS.a+"|"+svmSrcKey(dzAbJ.src)+"@"+dzAbS.b:"",
      abOk=!!dzAbK,abA=abSt.k===dzAbK?abSt.a:null,abB=abSt.k===dzAbK?abSt.b:null;
  /* les deps sont la clé seule : elle encode source ET seconde des deux côtés, un roll ou un autre losange la changent */
  x.useEffect(function(){
    if(!dzAbK){setAbSt(function(s){return s.k?{a:null,b:null,k:""}:s});return}
    var alive=!0;
    /* revue 24/09 : le rappel n'est inscrit qu'au premier passage (reg) — relu depuis le cache à chaque arrivée, jamais empilé en double */
    function lire(reg){if(!alive)return;var cb=reg?lire:null,a=svmThumb(dzAbG.src,dzAbS.a,cb),b=svmThumb(dzAbJ.src,dzAbS.b,cb);setAbSt({a:a,b:b,k:dzAbK})}
    lire(!0);return function(){alive=!1}},[dzAbK]);
  /* le roll de n images (signé) à la jonction en édition : verrou dit, borne dite, historique avant l'écriture ;
     n/30 : 30 i/s en dur, la cadence du rendu et du juge des jump cuts (revue 24/09 : le roll borné est DIT, k images seulement) */
  function abRoll(n){
    if(!dzAbJ||!dzAbG)return;
    if(trackStRef.current[dzAbJ.tr]&&trackStRef.current[dzAbJ.tr].l){fireNote(dzT("montage.piste.verrouillee",{p:String(dzAbJ.tr).toUpperCase()}));return}
    var cs=clipsRef.current,r2=DzTracks.roll(cs,dzAbG.id,dzAbJ.id,n/30),q=r2.filter(function(k){return k&&k.id===dzAbJ.id})[0];
    var dit=DzTracks.abRollDit(dzAbJ.start,q?q.start:dzAbJ.start,n);
    if(!dit.k){fireNote(dzT("montage.jonction.borne"));return}
    pushHistory();setClips(r2);setDirty(!0);
    if(dit.partiel)fireNote((Math.abs(dit.k)>1?dzT("montage.jonction.partiel.plusieurs",{n:Math.abs(dit.k)}):dzT("montage.jonction.partiel.un",{n:Math.abs(dit.k)})))}

  /* ── ajout d'assets depuis la Bibliothèque, sur n'importe quelle piste ──
     ovPick vaut "" (fermé) ou l'identifiant de la piste visée. Les sources
     proposées suivent le type de la piste : une piste audio ne doit pas
     proposer d'images, une piste vidéo ne doit pas proposer de .mp3. */
  /* « subs » est un TROISIÈME genre de piste, ni vidéo ni audio. Le déclarer
     ici suffit à ce que tout le reste refuse déjà ce qu'il faut : svmDragOk
     (dépôt d'asset vidéo / de son / d'effet du rack VFX), addAsset, la pile
     d'effets, le mixage par clip — chacun teste un genre et ne trouve pas le
     sien sur S1. */
  function trackKind(trId){var k=String(trId||"").charAt(0);
    return k==="a"?"audio":k==="s"?"subs":k==="t"?"title":k==="j"?"adjust":"video"}

  /* ── couche sous-titres (frontend/patches/subs.js) — feature-detect : si
     elle est absente, tout ce qui suit rend `null` et le Montage retombe
     EXACTEMENT sur son comportement d'avant. ── */
  function subsLayer(){var d=window.DzSubs;return d&&d.ready?d:null}
  function subsSegsOf(cs){
    return (cs||[]).filter(function(c){return c.tr==="s1"})}
  function subsStyleNow(){
    var d=subsLayer();
    return Object.assign(d?d.defaultStyle():{},proj.subsStyle||{})}
  function subsStyleSet(patch){
    var dzN=Date.now();if(dzN-dzStyleHistAt.current>600)pushHistory();dzStyleHistAt.current=dzN;
    setProj(function(p){
      var d=subsLayer();
      var st=Object.assign(d?d.defaultStyle():{},p.subsStyle||{},patch||{});
      try{localStorage.setItem("dz_subs_style",JSON.stringify(st))}catch(_e){}
      return Object.assign({},p,{subsStyle:st})});
    setDirty(!0)}
  /* un seul point d'écriture des segments : les clips s1 sont REMPLACÉS par
     `next`, les autres pistes ne bougent pas. Même règle d'historique que la
     pile d'effets : une entrée par rafale de 600 ms (taper du texte ne remplit
     pas la pile d'annulation d'une entrée par lettre). */
  function subsCommit(next,heavy){
    if(trackStRef.current.s1&&trackStRef.current.s1.l){
      fireNote(dzT("montage.sous_titres.s1_verrouillee"));
      return}
    var now=Date.now(),d=subsLayer();
    if(heavy||now-((d&&d.hist.t)||0)>600)pushHistory();
    if(d)d.hist.t=now;
    setClips(clipsRef.current.filter(function(c){return c.tr!=="s1"})
      .concat((next||[]).map(function(s){
        return Object.assign({},s,{tr:"s1"})})));
    setDirty(!0)}
  function subsAddHere(){
    var d=subsLayer();
    if(!d){fireNote(dzT("montage.sous_titres.couche_absente"));return}
    var segs=subsSegsOf(clipsRef.current);
    /* la place libre à partir de la tête : le bouton ne fabrique jamais le
       chevauchement qu'il irait ensuite signaler comme une faute */
    var sl=d.freeSlot(segs,phRef.current,durRef.current);
    var s=d.make(sl.start,sl.end,"");
    subsCommit(segs.concat([s]),!0);
    setSelId(s.id);setSubsOn(!0);setSfxOn(!1);setNarrOn(!1);setMedOn(!1);
    fireNote(dzT("montage.sous_titres.ajoute",{t:d.tc(sl.start)}))}
  function subsToggle(){
    setSubsOn(function(v){return !v});setSfxOn(!1);setNarrOn(!1);setMedOn(!1)}
  /* ── LE VERDICT, lu au même endroit que le tiroir ──────────────────────────
     Sévérité par réplique et comptes affichés viennent d'UNE seule fonction
     (DzSubs.verdict). La timeline, la chip de la barre d'outils et
     l'inspecteur lisent CE résultat ; ils n'en calculent plus aucun.
     Avant : la timeline peignait sa pastille d'après le calcul LOCAL pendant
     que la liste du tiroir peignait la sienne d'après le MOTEUR — la même
     réplique était « bloquante » d'un côté, « à vérifier » de l'autre, dans
     la même image. On passe `clips` (la valeur du rendu en cours), jamais
     `clipsRef.current`, pour que les deux surfaces regardent la même piste. */
  function subsVd(){
    var d=subsLayer();
    if(!d||!d.verdict)return d&&d.verdictNil?d.verdictNil()
      :{list:[],bySeg:{},style:[],
        counts:{repliques:0,masquees:0,signalees:0,bloquantes:0,defauts:0,ecarts:0}};
    var st=proj.subsStyle||null,du=proj.dur,tk=d.chkTick?d.chkTick():0;
    var c0=subsWRef.current;
    if(c0.v&&c0.k===clips&&c0.s===st&&c0.d===du&&c0.t===tk)return c0.v;
    /* les PLANS entrent dans le verdict : la couverture du montage est un
       fait mesurable au même titre que la lisibilité, et elle ne peut pas se
       calculer sans savoir jusqu'où court le montage ni où sont ses plans. */
    var v=d.verdict(subsSegsOf(clips),subsStyleNow(),du,subsSrcClips(clips));
    subsWRef.current={k:clips,s:st,d:du,t:tk,v:v};
    return v}
  function subsSev(id){
    var d=subsLayer();
    return (d&&d.segState?d.segState(subsVd(),id):null)||{sev:null,n:0}}
  /* état de COUVERTURE d'un plan, pour la timeline : un plan que rien ne
     sous-titre doit se voir LÀ OÙ ON MONTE, pas seulement dans un panneau.
     « ignore » = marqué sans parole, dit et non alarmant. */
  function subsCovOf(id){
    var v=subsVd(),ps=(v&&v.cov&&v.cov.plans)||[];
    for(var i=0;i<ps.length;i++)if(ps[i].id===id)return ps[i].etat;
    return null}
  /* ce qui part au rendu : hors du tableau `clips` (un sous-titre n'est pas
     un média), masqués et lignes vides retirés. */
  function subsPayload(){
    var d=subsLayer();
    if(!d)return void 0;
    /* L7 D-22 (24/09/2026, tâche 6) : seule la piste de sous-titres marquée « gravée » part au rendu (s1 sans marque —
       subsBurnId de la couche) ; l'éditeur, le verdict, la couverture et les emojis restent sur s1 (subsSegsOf, inchangé) */
    var bid=DzTracks.subsBurnId(svmTracksOf(proj));
    var segs=d.sort((clipsRef.current||[]).filter(function(c){return c.tr===bid})).filter(function(s){
      return !s.hidden&&String(s.text||"").trim()});
    if(!segs.length)return void 0;
    return {style:subsStyleNow(),
      segments:segs.map(function(s){
        var o={start:Math.round(s.start*1e3)/1e3,end:Math.round(s.end*1e3)/1e3,
               text:String(s.text||"")};
        if(Array.isArray(s.words)&&s.words.length)o.words=s.words;
        return o})}}
  /* ce que la TRANSCRIPTION reçoit. Deux chemins côté backend, et le gratuit
     passe d'abord : si des clips de narration portent leur texte, il le CALE
     sur les silences réels (exact, hors ligne, 0 $) ; sinon il transcrit le
     média. On envoie donc la timeline réduite à ce qui sert, pas le modèle
     client entier. */
  function subsSrcClips(cs){
    /* P13 — la piste de dialogue du projet (bus « dialogue », sinon
       a1) fait partie de ce que la transcription reçoit, même sous
       un autre identifiant : c'est elle que la route vise. */
    var dzDial=DzTracks.dialogueTrack(svmTracksOf(proj));
    return ((cs||clipsRef.current)||[]).filter(function(c){
      return c.tr==="a1"||c.tr==="a3"||c.tr==="v1"||c.tr===dzDial})
      .map(function(c){
        var o={id:c.id,tr:c.tr,src:c.src||null,
               name:c.name||c.label||null,
               /* P13 — `srcIn` : la route décale de `start − srcIn`. */
               srcIn:Math.round(subsNum(c.srcIn)*1e3)/1e3,
               start:Math.round(subsNum(c.start)*1e3)/1e3,
               end:Math.round(subsNum(c.end)*1e3)/1e3};
        if(c.text)o.text=String(c.text);
        /* « sans parole » : l'aveu volontaire vit sur LE CLIP, donc il se
           sauvegarde et s'annule avec le reste du montage. Le ranger dans le
           style des sous-titres l'aurait fait voyager d'un projet à l'autre. */
        if(c.noSub)o.noSub=!0;
        /* t120 — la VITESSE du plan : la route pose les mots à
           start + (t − srcIn) / vitesse, avec la loi du rendu (V1 0,25..4,
           audio 0,5..2). Sans elle, un plan à ×2 voyait ses mots deux fois
           trop loin. Envoyée seulement quand le clip en porte une. */
        if(c.speed!=null&&isFinite(Number(c.speed))&&Number(c.speed)>0)o.speed=Number(c.speed);
        return o})}
  function subsNum(v){var n=Number(v);return isFinite(n)?n:0}
  /* marquer / démarquer un plan « sans parole » — une entrée d'historique,
     comme toute autre écriture sur un clip */
  function subsPlanFlag(id,on){
    pushHistory();
    setClips(clipsRef.current.map(function(c){
      if(c.id!==id)return c;
      var o=Object.assign({},c);
      if(on)o.noSub=!0;else delete o.noSub;
      return o}));
    setDirty(!0);
    fireNote(on?dzT("montage.sous_titres.sans_parole")
      :dzT("montage.sous_titres.remis"))}
  function subsSrcRef(){
    var cs=clipsRef.current||[],i;
    for(i=0;i<cs.length;i++)if(cs[i].tr==="a1"&&cs[i].src)return cs[i].src;
    for(i=0;i<cs.length;i++)if(cs[i].tr==="v1"&&cs[i].src)return cs[i].src;
    return null}
  function subsPanel(){
    var d=subsLayer();
    if(!d||!d.Drawer)return null;
    return r.jsx(d.Drawer,{open:subsOn,onClose:function(){setSubsOn(!1)},
      segments:subsSegsOf(clips),style:subsStyleNow(),
      onChange:subsCommit,onStyle:subsStyleSet,
      playhead:ph,dur:proj.dur,selId:selId,
      onSelect:function(id){setSelId(id)},
      onSeek:function(t){seekTo(Math.max(0,Math.min(durRef.current,t)))},
      onNote:fireNote,srcName:proj.name,
      srcRef:subsSrcRef(),srcClips:subsSrcClips(clips),
      onPlanFlag:subsPlanFlag,
      /* P13 — les pistes du projet, pour que le tiroir et la route
         visent la même piste de dialogue. */
      srcTracks:svmTracksOf(proj),
      /* L7 D-22 (24/09/2026) : la traduction « dans une nouvelle piste » — S<n> naît, ses répliques sont des clips neufs, S1 intacte */
      onNewTrack:function(lang,segs){var r2=DzTracks.subsNew(svmTracksOf(dzProjRef.current),lang);svmTracksSet(r2.tracks);
        setClips(function(cs){return DzTracks.subsCopy(cs,"s1",r2.id,segs)});setDirty(!0);
        fireNote(dzT("montage.sous_titres.traduite",{p:r2.id.toUpperCase(),langue:lang,n:(segs||[]).length}))}})}
  /* LE karaoké : le mot prononcé se surligne dans le lecteur, à l'échelle
     réelle du canevas de rendu (l'aperçu ne ment pas sur la taille).
     Le tiroir ouvert, le même bloc devient MANIPULABLE : cadre de sélection,
     prise au glisser, poignées de largeur, zones sûres. Ce que l'on déplace
     n'est pas une position libre en pixels — c'est l'ancrage, la marge et la
     largeur que le fichier ASS porte, donc ce que ffmpeg gravera. */
  function subsOverlay(){
    var d=subsLayer();
    if(!d||!d.Overlay)return null;
    /* L7 D-22 (revue T6, 24/09/2026) : l'aperçu montre la piste que le rendu grave (subsBurnId) — l'éditeur reste sur s1 */
    var dzBid=DzTracks.subsBurnId(svmTracksOf(proj));
    var segs=(clips||[]).filter(function(c){return c.tr===dzBid});
    if(!segs.length&&!subsOn)return null;
    return r.jsx(d.Overlay,{segments:segs,style:subsStyleNow(),t:ph,
      edit:subsOn,onStyle:subsStyleSet,
      canvasW:svmRatioW(proj.ratio)>1?1920:1080})}
  /* inspecteur : le sous-titre sélectionné, son texte, ses bornes, et ses
     avertissements — à côté du geste qui les répare, jamais dans un rapport. */
  function subsInspector(){
    var d=subsLayer();
    if(!d||!sel||sel.tr!=="s1")return null;
    var segs=subsSegsOf(clips);
    /* mêmes avertissements, même sévérité, même ordre que dans le tiroir et
       sur la timeline : ils sortent du verdict, pas d'un second calcul */
    var ws=subsSev(sel.id).warns||[];
    return r.jsxs(r.Fragment,{children:[
      r.jsx(SvmLabel,{style:{margin:"20px 0 10px"},children:dzT("montage.soustitre.titre")}),
      r.jsx("textarea",{className:"sub-text",value:sel.text||"",rows:3,
        placeholder:dzT("montage.soustitre.placeholder"),"aria-label":dzT("montage.soustitre.texte"),
        onChange:function(e){
          var id=selRef.current,v=e.target.value;
          subsCommit(segs.map(function(s){
            return s.id===id?Object.assign({},s,{text:v,label:d.labelOf(v)}):s}))}}),
      r.jsxs("div",{className:"sub-inspfoot",children:[
        r.jsx("span",{className:"sub-inspt",
          title:dzT("montage.soustitre.bornes_aide"),
          children:d.tc(sel.start)+" → "+d.tc(sel.end)},"t"),
        r.jsx("button",{className:"sub-minibtn",
          title:dzT("montage.soustitre.editeur_aide"),
          onClick:function(){setSubsOn(!0);setSfxOn(!1);setNarrOn(!1);setMedOn(!1)},
          children:dzT("montage.soustitre.editeur")},"ed")]}),
      ws.length?r.jsx("div",{className:"sub-warns",style:{marginTop:8},
        children:ws.map(function(w,k){
          return r.jsxs("div",{className:"sub-warn","data-sev":w.sev,children:[
            r.jsx("span",{className:"sub-warnicon","aria-hidden":!0,
              children:w.sev==="err"?"!":"·"},"i"),
            r.jsx("span",{className:"sub-warnmsg",children:w.msg},"m")]},"w"+k)})}):null]})}
  function openPicker(trId){
    if(proj.demo){fireNote(dzT("montage.selecteur.demo"));return}
    if(trackSt[trId]&&trackSt[trId].l){
      fireNote(dzT("montage.commun.piste_verrouillee_ajouter",{piste:trId.toUpperCase()}));return}
    if(ovPick===trId){setOvPick("");return}
    if(sources){setOvPick(trId);return}
    Promise.all([
      fetch("/api/images").then(function(res){return res.json()}).catch(function(){return {}}),
      fetch("/api/jobs").then(function(res){return res.json()}).catch(function(){return []}),
      fetch("/api/audio").then(function(res){return res.json()}).catch(function(){return {}}),
      /* P9 — LA règle du rendu, servie par le backend. Pas une copie. */
      fetch("/api/montage/media-rules").then(function(res){return res.json()}).catch(function(){return {}})
    ]).then(function(rr){
      var imgs=((rr[0]&&rr[0].images)||[]).slice(0,24).map(function(im){return {name:im.filename}});
      var xt=(rr[3]&&Array.isArray(rr[3].video_exts)&&rr[3].video_exts.length)
        ?rr[3].video_exts:null;
      var vids=(Array.isArray(rr[1])?rr[1]:[]).filter(function(j3){
        return DzTracks.isVideoJob(j3,xt)})
        .slice(0,12).map(function(j3){return {job_id:j3.job_id,title:j3.title||j3.job_id,
          dur:Number(j3.duration_real_s||j3.duration_s)||0}});
      var auds=((rr[2]&&rr[2].audio)||[]).slice(0,24).map(function(a3){
        return {name:a3.name,kb:a3.size_kb}});
      if(!xt)fireNote(dzT("montage.selecteur.regle_absente"
        
        
        ));
      setSources({images:imgs,videos:vids,audios:auds});setOvPick(trId)});
  }
  /* durée par défaut d'un asset posé : une image n'en a pas, une vidéo et un
     son sont bornés pour rester manipulables à la souris. */
  /* t119 (07/10/2026, E-3) : UN PLAN PAR SCÈNE. Un rendu reçu par la boîte
     aux lettres demande d'abord ses scènes (GET /api/montage/episode-scenes/ :
     [] pour tout ce qui n'est pas un épisode mesuré, ou en cas d'échec — la
     pose se fait alors comme avant). Deux scènes ou plus : `dzScenesRef`
     retient le numéro de pose courant (`ovSeq`, qu'`addAsset` n'avance que
     sur une pose ACCEPTÉE) ; l'effet qui suit attend la pose suivante, dans
     les 30 s, et découpe le clip qu'elle a sélectionné s'il lit CE job
     (`scenesPose` de la couche : le plan, son jumeau son, un marqueur par
     scène) en un SECOND pas d'historique — « Annuler » rend l'épisode en un
     seul plan, la seconde fois le retire. `addAsset` n'en sait rien (le banc
     bundle l'exécute seul sous node). Ce qui était déjà sur la timeline
     n'est jamais touché : seul le clip de la pose est découpé. */
  var dzScenesRef=x.useRef(null);
  x.useEffect(function(){var p=null;try{p=window.__dzMontageAdd;delete window.__dzMontageAdd}catch(_e){}if(!p)return;var dzT0=Date.now();function dzPose(){try{if(p.image)addAsset({image:p.image},p.image,"image",0,"v2");else if(p.job_id)addAsset({job_id:p.job_id},p.title||p.job_id,"video",p.dur||0,"v1")}catch(_e2){}}if(p.image||!p.job_id){setTimeout(dzPose,450);return}fetch("/api/montage/episode-scenes/"+encodeURIComponent(p.job_id)).then(function(rp){return rp.ok?rp.json():null}).catch(function(){return null}).then(function(d){var sc=(d&&Array.isArray(d.scenes))?d.scenes:[];if(sc.length>1)dzScenesRef.current={job_id:p.job_id,scenes:sc,seq:ovSeq.current,until:Date.now()+30000};setTimeout(dzPose,Math.max(0,450-(Date.now()-dzT0)))})},[]);
  x.useEffect(function(){var q=dzScenesRef.current;if(!q)return;
    if(Date.now()>q.until){dzScenesRef.current=null;return}
    if(ovSeq.current<=q.seq)return;dzScenesRef.current=null;
    var c=(clips||[]).find(function(k){return k&&k.id===selRef.current});
    if(!c||!c.src||c.src.job_id!==q.job_id)return;
    var lk={},k;for(k in trackStRef.current)if(trackStRef.current[k]&&trackStRef.current[k].l)lk[k]=!0;
    var rs=DzTracks.scenesPose(clips,c.id,q.scenes,(dzProjRef.current&&dzProjRef.current.markers)||[],{locked:lk});
    if(!rs.n){if(rs.note)fireNote(rs.note);return}
    pushHistory();setClips(rs.clips);setProj(function(pp){return Object.assign({},pp,{markers:rs.markers})});setDirty(!0);fireNote(rs.note)},[clips]);
  function defaultLen(kind,srcDur){
    /* P11 — plus de plafond : la longueur d'un clip est celle de
       sa source quand on la connaît. Les trois replis restent, et
       ils sont PASSÉS à la couche au lieu d'y être recopiés ; un
       clip posé sur un repli le DIT (champ `note`). */
    return DzTracks.clipLen(kind,srcDur,{image:4,audio:8,video:6});
  }
  function addAsset(src,label,kind,srcDur,trId,atTime){
    if(trackKind(trId||"v2")==="title"){
      fireNote(dzT("montage.ajout.piste_titres",{touche:svmKeyLabelNow("title_add")}));
      setOvPick("");return}
    /* P6 — MODE REMPLACEMENT, en court-circuit AVANT tout le reste :
       un remplacement ne choisit pas de piste, il garde celle du
       plan. Le mode est CONSOMMÉ dès l'entrée (une seule fois par
       armement), et les TROIS refus sortent AVANT pushHistory.

       CE COURT-CIRCUIT PREND TOUS LES APPELANTS D'`addAsset`, et
       c'est DÉCLARÉ ici parce que ce n'est pas anodin. Le
       sélecteur est un panneau de 300 px en haut à droite
       (`.svm-pop` : position:absolute, top:52px, right:18px,
       z-index:20 — MESURÉ dans shared/son-vfx-montage.css) et il
       n'a NI voile NI backdrop : tout le reste de l'écran reste
       cliquable pendant que le mode est armé, et le mode le reste
       tant qu'`ovPick` ne bouge pas. Deux chemins arrivent donc
       ici sans être des clics du sélecteur :
         · le GLISSER-DÉPOSER d'une vignette sur une bande (les
           vignettes sont `draggable:!0`). La piste visée et
           l'instant du dépôt sont alors JETÉS — un remplacement
           n'en veut pas — et le geste devient un remplacement.
           C'est ASSUMÉ : glisser une vignette, c'est choisir dans
           le sélecteur, et le titre du panneau dit que le
           prochain choix remplacera (section M15b). Fermer le
           panneau désarme.
         · `sfxInsert` (tiroir Sons, dont l'état `sfxOn` est
           INDÉPENDANT d'`ovPick` et rendu hors du panneau) :
           `addAsset({audio:fn},…,"audio",…)`. Celui-là n'est PAS
           assumable : MESURÉ sous node, `replaceSrc` accepte
           l'objet tel quel et le `src` d'un plan V1 devenait
           `{audio:"…"}` — avec ses bornes, ses effets et sa
           transition, et la fin ramenée à la durée du .wav.
           D'où le refus de GENRE ci-dessous, qui manquait.
       Le genre passe AVANT le verrou : déverrouiller la piste ne
       rendrait pas un son valide pour un plan vidéo, et envoyer
       l'utilisateur déverrouiller serait l'envoyer dans le mur. */
    if(dzmReplaceRef.current){
      var rc=dzmReplaceRef.current;dzmReplaceRef.current=null;
      setDzmArm(null);
      var rcs=clipsRef.current||[],rk=null,ri;
      for(ri=0;ri<rcs.length;ri++)if(rcs[ri].id===rc.id)rk=rcs[ri];
      setOvPick("");
      if(!rk){fireNote(dzT("montage.remplacer.plan_absent",
        
        {nom:label}
        
        ));return}
      var rkd=trackKind(rk.tr);
      var akd=(kind==="audio"||(src&&src.audio))?"audio":"video";
      if(rkd!==akd){
        fireNote(dzT("montage.remplacer.genre",{nom:label,
          genre:akd==="audio"?dzT("montage.remplacer.un_son"):
          dzT("montage.remplacer.une_image"),
          piste:rk.tr.toUpperCase(),
          type:rkd
          
          }));return}
      if(trackStRef.current[rk.tr]&&trackStRef.current[rk.tr].l){
        fireNote(dzT("montage.remplacer.piste_verrouillee",
          {piste:rk.tr.toUpperCase()}
          ));return}
      var rr=DzTracks.replaceSrc(rk,src,label,srcDur);
      pushHistory();
      setClips(rcs.map(function(k){return k.id===rc.id?rr.clip:k}));
      setSelId(rc.id);setDirty(!0);fireNote(rr.note);return}
    /* P9 — la piste RÉSOLUE, et l'attente de la timeline réelle (celle-
       ci vit dans le corps du composant, plus haut : c'est le seul
       endroit d'où le démontage de l'onglet peut l'éteindre). */
    var d=durRef.current;
    if(!dzReadyRef.current){dzAddWhenReady(src,label,kind,srcDur,trId,
      atTime,Date.now()+20000);return}
    var dzTs=dzTracksRef.current||svmTracksOf(proj);
    var dzWant=kind==="audio"?"audio":"video";
    var dzMot=dzWant==="audio"?"audio":dzT("montage.ajout.mot_video");
    var tr2=(trId&&dzTs.some(function(t){return t&&t.id===trId}))?trId
      :DzTracks.pickTrack(dzTs,dzWant);
    if(!tr2){fireNote(dzT("montage.ajout.aucune_piste",
      {nom:label,
      mot:dzMot}
      ));return}
    var dzMoved=(trId&&tr2!==trId)?String(trId).toUpperCase():"";
    /* « E4 » (D-2) — LE VERROU DE PISTE SE JUGE APRÈS LE MODE, dans
       `insere()` : le mode « au-dessus » CHANGE de piste, et
       refuser ici sur la piste visée refusait un geste qui n'allait
       pas s'y poser. Le refus, sa phrase d'origine comprise, vit
       désormais au seul endroit qui connaît la piste RÉELLE. */
    var st=atTime==null?phRef.current:atTime;
    /* P10 — LA TIMELINE S'ÉTEND, ELLE NE ROGNE PLUS. Le clip garde sa
       longueur naturelle ; c'est la durée du projet qui grandit. La
       garde des clips de moins d'une demi-seconde est celle d'avant :
       elle vise les SOURCES minuscules, pas le plafond disparu. */
    st=Math.max(0,st);
    /* P11 — LA LONGUEUR DE LA SOURCE, DÉCOUVERTE QUAND ELLE MANQUE.
       On sort ICI, avant `pushHistory` : rien n'est encore écrit, et le
       rappel repart du même point avec la mesure. La piste REDEMANDÉE
       est `trId`, pas la piste résolue — sinon l'explication « cette
       piste n'existe pas dans ce projet » se perdrait au retour ; `st`
       est repassé pour que le clip atterrisse là où la tête de lecture
       était AU CLIC, pas 85 ms plus tard. Mesure échouée : on repasse un
       nombre NÉGATIF, que `needDur` lit comme « déjà demandé » — c'est
       le verrou de récursion, et il est éprouvé sous node. */
    /* P12 — LE SON D'UN PLAN SUIT SA VIDÉO : le verdict « cette source
       a-t-elle du son ? » est demandé ICI, avant la durée et avant
       tout `pushHistory`, pour une vidéo posée sur une piste vidéo
       PLEIN CADRE (V1 : type « vidéo », jamais une incrustation). Le
       rappel repart des MÊMES arguments — c'est le CACHE du verdict,
       écrit par askAudio sur toute sortie, qui le rend non récursif
       (éprouvé sous node : un rappel sans cache redemande). La durée
       rendue en prime épargne le second aller-retour d'askDur. */
    var dzAuOn=DzTracks.wantsTwin(kind,dzTs,tr2);
    var dzAu=dzAuOn?DzTracks.audioOf(src):null;
    if(dzAuOn&&!dzAu){DzTracks.askAudio(src,{done:function(){
      addAsset(src,label,kind,srcDur,trId,st)}});return}
    srcDur=DzTracks.srcDurOr(kind,srcDur,dzAu);
    if(DzTracks.needDur(kind,srcDur)){
      DzTracks.askDur(src,{done:function(dzV){
        addAsset(src,label,kind,dzV>0?dzV:-1,trId,st)}});return}
    var dzCl=defaultLen(kind,srcDur);
    var en=st+dzCl.len;if(en-st<.5)st=Math.max(0,en-1);
    /* D-2 — LE MODE D'ÉDITION DÉCIDE DE L'ÉCRITURE. `dzModeRef` est
       l'état de la rangée de chips du sélecteur ; `insere()` rend la
       timeline ENTIÈRE, jumeau compris. Le numéro d'ordre n'est
       CONSOMMÉ qu'une fois l'insertion acceptée, et le refus sort AVANT
       `pushHistory()` : rien d'écrit, rien dans la pile d'annulation. */
    var dzSeq=ovSeq.current+1;
    /* P12 — l'identifiant est UNIQUE contre les clips existants (une
       sauvegarde rechargée peut en porter d'anciens du même rang), et
       le jumeau est décidé AVANT le seul pushHistory du geste : sa
       phrase rejoint la note de l'ajout — et une incrustation, exemptée
       de sonde, est DITE aussi (overlayNote), jamais tue. */
    var id=DzTracks.uniqueId(clipsRef.current||[],
      tr2+"u"+dzSeq+"_"+Math.round(st*10));
    var dzNeuf={tr:tr2,id:id,label:label,start:st,end:en,src:src,srcIn:0};
    var dzTw=dzAuOn?DzTracks.twinPlan(dzNeuf,dzTs,clipsRef.current||[],dzAu,
      function(t){return !!(trackStRef.current[t]&&trackStRef.current[t].l)}):null;
    var dzIns=DzTracks.insere(clipsRef.current||[],dzNeuf,dzModeRef.current,
      {tracks:dzTs,twin:dzTw&&dzTw.clip,head:phRef.current,
       srcDur:Number(srcDur)||0,
       range:dzProjRef.current&&dzProjRef.current.range,
       locked:(function(){var o={},k;for(k in trackStRef.current)
         if(trackStRef.current[k]&&trackStRef.current[k].l)o[k]=!0;
         return o})()});
    if(dzIns.refus==="verrou"){
      fireNote(dzIns.track===tr2
        ?(dzT("montage.commun.piste_verrouillee_ajouter",
          {piste:String(tr2).toUpperCase()}))
        :(dzT("montage.ajout.piste_verrouillee_mode",
          {piste:String(dzIns.track).toUpperCase()}
          )));return}
    ovSeq.current=dzSeq;
    /* LE CLIP RÉELLEMENT POSÉ : `dzmPose` RENOMME un identifiant déjà
       pris, et « en fin » / « remplir » le posent à d'autres bornes que
       [st,en[. On le relit par `dzIns.id` pour que la note dise la
       position VRAIE et que la sélection porte sur le bon clip. */
    var dzP=null,dzJ;
    for(dzJ=0;dzJ<dzIns.clips.length;dzJ++)
      if(dzIns.clips[dzJ]&&dzIns.clips[dzJ].id===dzIns.id)dzP=dzIns.clips[dzJ];
    var dzAv=DzTracks.fitDur(clipsRef.current||[],d,0);
    var dzFit=DzTracks.fitDur(dzIns.clips,d,0),dzGrew=dzFit>d?dzFit:0;
    var dzTail=dzCl.note+(dzGrew?(dzT("montage.ajout.allongee",{
      de:svmRuler(Math.round(d)),a:svmRuler(Math.round(dzGrew)),
      raison:dzAv>d?dzT("montage.ajout.allongee_tenir")
        :dzT("montage.ajout.allongee_garde")
          
      
      })):"");
    if(dzTw)dzTail+=dzTw.note;
    else dzTail+=DzTracks.overlayNote(kind,dzTs,tr2);
    /* D-2 — LE MODE APPLIQUÉ EST DIT, COURT. `dzIns.mode` est le mode
       EFFECTIF : « au-dessus » rend toujours "ecraser" sur une autre
       piste, c'est donc le changement de PISTE qui le trahit, et le
       repli « aucune piste libre » parle par `dzIns.note`. */
    if(dzIns.track&&dzIns.track!==tr2)dzTail+=dzT("montage.ajout.pose_au_dessus"
      );
    else if(dzIns.mode!=="ecraser")dzTail+=dzT("montage.ajout.mode",{mode:
      DzTracks.modeLabel(dzIns.mode)})+
      ((dzP&&Number(dzP.speed)>0&&Number(dzP.speed)!==1)?
        dzT("montage.ajout.vitesse",{v:String(dzP.speed).replace(".",",")}):"");
    if(dzModeRef.current==="remplir"&&dzIns.mode!=="remplir")
      dzTail+=dzT("montage.ajout.plage_effacee");
    /* Le JETON `dzIns.refus` n'est jamais affiché : la phrase française
       est `dzIns.note` (écrêtage de vitesse, aucune piste libre…), et
       elle est capitalisée parce qu'elle suit un point. */
    if(dzIns.note)dzTail+=" "+dzIns.note.charAt(0).toUpperCase()+
      dzIns.note.slice(1)+".";
    if(dzGrew)setProj(function(p){return Object.assign({},p,{dur:dzGrew})});
    /* LA NOTE ET LA SÉLECTION DISENT LE RÉEL : `id`, `tr2` et `st` sont
       RELUS sur le clip posé avant que la fin d'`addAsset` (setSelId,
       fireNote) ne les emploie — c'est la même variable, pas une
       seconde source de vérité. La phrase de la piste absente, le choix
       des pistes et `overlayNote` ont déjà lu `tr2` au-dessus : leur
       sens ne change pas. */
    id=dzIns.id||id;tr2=dzIns.track||tr2;if(dzP)st=Number(dzP.start)||0;
    pushHistory();
    setClips(dzIns.clips);
    setSelId(id);setDirty(!0);setOvPick("");
    fireNote(dzT("montage.ajout.ajoute",{nom:label,piste:tr2.toUpperCase(),
      t:svmShort(st)})+
      (dzMoved?dzT("montage.ajout.piste_absente",{piste:dzMoved,
        cible:tr2.toUpperCase(),
        suite:tr2==="v1"?dzT("montage.ajout.piste_absente_v1")
          :"",
        mot:dzMot
        
        
        }):"")+dzTail)}
  /* insertion depuis le tiroir Sons (DzSfx.Drawer) — à la tête de lecture,
     piste du type (voix→A1, musique→A2, sfx→A3 ; le tiroir peut imposer
     opts.track) ; même moteur addAsset : historique, sélection, note */
  function sfxInsert(item,opts){
    if(proj.demo){fireNote(dzT("montage.sons.insertion_demo"));return}
    var fn=svmSfxFileOf(item);
    if(!fn){fireNote(dzT("montage.sons.insertion_impossible"));return}
    var tr2=opts&&opts.track&&SVM_TRACK_BUS[opts.track]?opts.track:svmSfxTrackOf(item&&item.kind);
    addAsset({audio:fn},(item&&item.name)||fn,"audio",Number(item&&item.dur)||0,tr2,null)}

  /* ── glisser-déposer : le sélecteur est la source, les bandes et le
     viewport sont les cibles. Le viewport vise la piste vidéo principale. ── */
  /* ── rack VFX : pose d'un effet sur un clip vidéo (clic du panneau ou
     dépôt sur la bande). Même moteur que les autres mutations de clip :
     historique, sélection, note. ── */
  function vfxAddTo(id,eff){
    var cs=clipsRef.current,c=null;
    for(var i=0;i<cs.length;i++){if(cs[i].id===id){c=cs[i];break}}
    if(!c)return !1;
    if(c.kind!=="adjust"&&!c.src){fireNote(dzT("montage.effets.demo"));return !1}
    if(c.kind!=="adjust"&&trackKind(c.tr)!=="video"){fireNote(dzT("montage.effets.video_seulement"));return !1}
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){
      fireNote(dzT("montage.effets.piste_verrouillee",{piste:c.tr.toUpperCase()}));return !1}
    var e2={};
    Object.keys(eff||{}).forEach(function(k){if(k!=="label")e2[k]=eff[k]});
    pushHistory();
    setClips(clipsRef.current.map(function(k){
      return k.id===id?Object.assign({},k,{effects:(k.effects||[]).concat([e2])}):k}));
    setSelId(id);setDirty(!0);
    return !0}
  function vfxDropEffect(eff,trId,laneEl,e){
    if(proj.demo){fireNote(dzT("montage.effets.depot_demo"));return}
    var t=null;
    if(laneEl){var rc=laneEl.getBoundingClientRect();
      if(rc.width>0)t=Math.max(0,(e.clientX-rc.left)/rc.width*durRef.current)}
    var cs=clipsRef.current,hit=null;
    for(var i=0;i<cs.length;i++){var c=cs[i];
      if(c.tr!==trId||!c.src)continue;
      if(t==null||(t>=c.start-.001&&t<=c.end+.001)){hit=c;break}}
    if(!hit){fireNote(dzT("montage.effets.aucun_clip"));return}
    if(vfxAddTo(hit.id,eff))
      fireNote(dzT("montage.effets.pose_sur",{effet:eff.label||eff.type,clip:hit.label}))}
  var DZ_MIME="application/dz-asset";
  function dragPayload(e,src,label,kind,srcDur){
    try{e.dataTransfer.setData(DZ_MIME,JSON.stringify({src:src,label:label,kind:kind,dur:srcDur||0}));
        e.dataTransfer.effectAllowed="copy"}catch(_e){}}
  function readPayload(e){
    try{var raw=e.dataTransfer.getData(DZ_MIME);return raw?JSON.parse(raw):null}catch(_e){return null}}
  /* cibles de drop valides — DZ_MIME (sélecteur d'assets) partout, items
     « dz-audio » du tiroir Sons (DzSfx.Drawer) sur les pistes AUDIO seulement :
     ailleurs le survol reste refusé (curseur no-drop, aucun faux espoir) */
  function svmDragOk(e,trId){
    var ts=e.dataTransfer&&e.dataTransfer.types;
    if(!ts)return !1;
    if(Array.prototype.indexOf.call(ts,DZ_MIME)>=0)return !0;
    /* effet du rack VFX (mime « dz-vfx ») : pistes VIDÉO seulement — ailleurs
       le survol reste refusé (curseur no-drop, aucun faux espoir) */
    if(Array.prototype.indexOf.call(ts,"dz-vfx")>=0)
      return !!trId&&trackKind(trId)==="video";
    return Array.prototype.indexOf.call(ts,"dz-audio")>=0&&!!trId&&trackKind(trId)==="audio"}
  function dropOnTrack(e,trId,laneEl){
    /* effet du rack VFX déposé sur une bande vidéo → pile du clip visé */
    var _vfx=null;
    try{var _rv=e.dataTransfer.getData("dz-vfx");_vfx=_rv?JSON.parse(_rv):null}
    catch(_e){_vfx=null}
    if(_vfx&&_vfx.type){e.preventDefault();vfxDropEffect(_vfx,trId,laneEl,e);return}
    var p=readPayload(e);
    if(!p){
      /* item du tiroir Sons — même moteur addAsset que le sélecteur */
      var pa=null;
      try{var raw2=e.dataTransfer.getData("dz-audio");pa=raw2?JSON.parse(raw2):null}catch(_e){pa=null}
      if(!pa)return;
      e.preventDefault();
      if(trackKind(trId)!=="audio"){fireNote(dzT("montage.depot.son"));return}
      if(proj.demo){fireNote(dzT("montage.depot.demo"));return}
      var fn2=svmSfxFileOf(pa);if(!fn2)return;
      var t3=null;
      if(laneEl){var rect3=laneEl.getBoundingClientRect();
        if(rect3.width>0)t3=Math.max(0,(e.clientX-rect3.left)/rect3.width*durRef.current)}
      addAsset({audio:fn2},pa.name||fn2,"audio",Number(pa.dur)||0,trId,t3);
      return}
    e.preventDefault();
    /* un son ne se dépose pas sur une piste vidéo, et réciproquement */
    if(trackKind(trId)!==(p.kind==="audio"?"audio":"video")){
      fireNote(p.kind==="audio"?dzT("montage.depot.son"):dzT("montage.depot.video"));return}
    var t=null;
    if(laneEl){var rect=laneEl.getBoundingClientRect();
      if(rect.width>0)t=Math.max(0,(e.clientX-rect.left)/rect.width*durRef.current)}
    addAsset(p.src,p.label,p.kind,p.dur,trId,t);
  }

  /* ── rendu réel : POST /api/montage/render + poll /api/jobs/{id} ── */
  function renderPayload(preview,queue){
    var _b={name:proj.name,ratio:proj.ratio,preview:preview,
      /* piste S1 — HORS du tableau `clips` (ce ne sont pas des médias) :
         {style, segments:[{start,end,text,words?}]}. Absente quand la piste
         est vide ; un backend qui ne connaît pas encore la clé l'ignore et
         le rendu reste exactement celui d'avant. */
      subtitles:subsPayload(),
      duration_master:durMaster,
      /* ducking : booléen historique tant que rien n'est personnalisé,
         objet {enabled, ratio, attack_ms, release_ms, threshold} sinon */
      ducking:proj.ducking?Object.assign({enabled:ducking},proj.ducking):ducking,
      mix:proj.mixDb,
      /* P1 — l'ORDRE des pistes, du haut vers le bas : c'est lui que
         montage_service._tracks_meta traduit en rang de composition
         (`layer`) et en bus de mixage. Un backend qui ne connaît pas
         encore la clé l'ignore et rend exactement ce qu'il rendait. */
      tracks:svmTracksPayload(proj),
      clips:clips.filter(function(c){return c.src||c.kind==="title"||c.kind==="adjust"}).map(function(c){
        var o={tr:c.tr,src:c.src,start:c.start,end:c.end,srcIn:c.srcIn||0,kind:c.kind,title:c.title,
          transition:c.transition||"cut",transition_s:c.transition_s||0,
          /* contournés (bypass du rack VFX) : retirés du RENDU, gardés dans
             le projet — la clé `off` ne quitte jamais le client */
          effects:(function(){
            var _fx=(c.effects||[]).filter(function(_f){return !_f.off});
            return _fx.length?_fx:void 0})(),
          opacity:c.opacity};
        /* T103 (D2b) : le sujet détouré -- joint seulement s'il existe, sur un vrai plan V1 (payload d'avant sinon) */
        if(c.tr==="v1"&&c.matte&&c.src&&c.src.job_id)o.matte=c.matte;
        /* vitesse V1 (C) — jointe seulement hors 100 % et pour un VRAI plan
           vidéo (une image n'a pas de défilement) : payload d'avant sinon */
        if(trackKind(c.tr)==="video"&&c.src&&c.src.job_id&&typeof c.speed==="number"&&c.speed>0&&
           Math.abs(c.speed-1)>1e-6)o.speed=Math.round(c.speed*100)/100;   /* t117 : pistes hautes comme V1 */
        /* t117 : fondus d'un clip d'ajustement — joints seulement s'ils existent (payload d'avant sinon) */
        if(c.kind==="adjust"){if(c.fade_in)o.fade_in=c.fade_in;if(c.fade_out)o.fade_out=c.fade_out}
        /* D-13 : le zoom dynamique -- joint seulement s'il existe (payload d'avant sinon) */
        var dzD=c.tr==="v1"&&DzTracks.dzOf(c);if(dzD)o.dz=dzD;
        /* D-15 : l'interpolation du retime -- jointe seulement avec une vitesse */
        var rtD=o.speed&&DzTracks.retimeOf(c);if(rtD)o.retime=rtD;
        /* D-16 : la stabilisation -- jointe seulement si elle existe */
        var sbD=c.tr==="v1"&&DzTracks.stabOf(c);if(sbD)o.stab=sbD;
        /* L7-B D-40 : le cadrage -- joint seulement hors centre */
        var rfD=c.tr==="v1"&&DzTracks.reframePayload(c);if(rfD)o.reframe=rfD;
        /* L5 D-30 : le masque (V1 et overlays V2) -- joint seulement lisible et avec des effets actifs */
        var mkD=o.effects&&c.src&&trackKind(c.tr)==="video"&&DzTracks.maskOf(c.mask);if(mkD)o.mask=mkD;
        /* mixage par clip (pistes audio) — joint seulement si non nul :
           un projet sans réglage envoie exactement le payload d'avant */
        if(trackKind(c.tr)==="audio"){
          if(c.gain)o.gain=c.gain;
          if(c.fade_in)o.fade_in=c.fade_in;
          if(c.fade_out)o.fade_out=c.fade_out;
          /* courbes de fondu (R2/I4) — jointes seulement si un fondu existe
             ET que la courbe n'est pas « lin » : payload d'avant sinon */
          if(c.fade_in&&c.fade_in_curve&&c.fade_in_curve!=="lin")o.fade_in_curve=c.fade_in_curve;
          if(c.fade_out&&c.fade_out_curve&&c.fade_out_curve!=="lin")o.fade_out_curve=c.fade_out_curve;
          /* rack SFX + vitesse — joints seulement hors défaut : un projet
             jamais touché envoie exactement le payload d'avant */
          if(c.fx&&c.fx.length)o.fx=c.fx;
          if(typeof c.speed==="number"&&c.speed>0&&Math.abs(c.speed-1)>1e-6)o.speed=c.speed;
          /* automation de volume (R4) — jointe à 2 points ou plus (en deçà
             rien ne part : l'inspecteur le dit), t 0,01 / dB 0,1. Musique A2
             bouclée dans les bornes de son clip : le rendu lit son automation en temps
             GLOBAL (temps de la timeline, retours L6 26/09/2026) — on convertit t local → start + t pour que le
             losange s'entende exactement là où il est posé. */
          var vpp=svmVpOf(c);
          if(vpp&&vpp.length>=2){
            var vpMus=c.id===firstA2;
            o.volume_points=svmVpSort(vpp).map(function(p){
              return {t:Math.round((p.t+(vpMus?c.start:0))*100)/100,
                      db:Math.round(p.db*10)/10}})}}
        /* transformation d'overlay (V2) — l'échelle matérialise l'état
           « transformé » (même à 100 %), x/y/rotate joints seulement hors
           défaut ; un overlay jamais touché envoie le payload d'avant */
        if(DzTracks.isOverlayTrack(c.tr,dzTracksRef.current)){
          var tf=svmOvTfOf(c);
          if(tf){o.scale=tf.scale;
            if(Math.abs(tf.x-.5)>1e-4)o.x=tf.x;
            if(Math.abs(tf.y-.5)>1e-4)o.y=tf.y;
            if(Math.abs(tf.rotate)>=.05)o.rotate=tf.rotate;
            /* L7 D-19 : coins et ombre, joints seulement hors défaut (tf est non nul dès que l'un des deux est posé) */
            if(tf.radius>0)o.radius=tf.radius;if(tf.shadow)o.shadow=1}
          /* keyframes de position (R4b) — jointes à 2 points ou plus (en
             deçà rien ne part : l'inspecteur le dit), t 0,01 / x·y 0,001 /
             rotate 0,1 ; l'échelle reste la statique ci-dessus (pas de
             keyframe d'échelle — le rendu fige la largeur) */
          var mpp=svmMpOf(c);
          if(mpp&&mpp.length>=2){
            if(!tf)o.scale=1; /* défaut matérialisé — jamais le cas via l'UI */
            o.motion_points=svmMpSort(mpp).map(function(p){
              var q={t:Math.round(p.t*100)/100,
                     x:Math.round(p.x*1000)/1000,
                     y:Math.round(p.y*1000)/1000};
              if(p.rotate!=null&&isFinite(Number(p.rotate)))
                q.rotate=Math.round(Number(p.rotate)*10)/10;
              /* D-14 : échelle / opacité par point — jointes seulement si présentes */
              if(p.scale!=null&&isFinite(Number(p.scale)))q.scale=Math.round(Number(p.scale)*1000)/1000;
              if(p.opacity!=null&&isFinite(Number(p.opacity)))q.opacity=Math.round(Number(p.opacity)*100)/100;
              return q})}}
        return o})};
    /* L4 : hors apercu, les reglages de livraison (dzDelRef, frais) et la plage du projet entrent par la couche ; `queue` (D-36) vient de launchRender */
    return preview?_b:DzTracks.deliverPayload(_b,Object.assign({},dzDelRef.current,{range:proj.range,queue:queue===!0}))}
  function launchRender(preview,queue){
    if(proj.demo||(job&&job.status!=="failed"))return;setDzFin(null);
    if(!queue)setJob({id:null,kind:preview?"preview":"final",status:"queued",progress:0,step:dzT("montage.rendu.envoi"),error:null});
    fetch("/api/montage/render",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify(renderPayload(preview,queue))})
      .then(function(res){return res.json().then(function(d){return {ok:res.ok,d:d}})})
      .then(function(o){
        /* L4 (D-36) : en file, aucun `job` suivi (le badge de la vue Livraison suit GET /api/jobs) : note + fermeture, ou refus dit */
        if(queue){if(o.ok&&o.d&&o.d.queued){fireNote(o.d.message||dzT("montage.rendu.ajoute_file"));setPop("")}else fireNote(dzT("montage.rendu.file_refusee",{e:(o.d&&(o.d.detail||o.d.error))||dzT("montage.rendu.echec")}));return}
        if(!o.ok||!o.d.job_id){setJob({id:null,kind:preview?"preview":"final",status:"failed",progress:0,step:"",
          error:(o.d&&(o.d.detail||o.d.error))||dzT("montage.rendu.echec_lancement")});return}
        setJob({id:o.d.job_id,kind:preview?"preview":"final",status:"running",progress:10,step:dzT("montage.rendu.en_file"),error:null})})
      .catch(function(e){if(queue){fireNote(dzT("montage.rendu.file_erreur",{e:String(e)}));return}setJob({id:null,kind:preview?"preview":"final",status:"failed",progress:0,step:"",error:String(e)})})}
  x.useEffect(function(){
    if(!job||!job.id||job.status==="done"||job.status==="failed")return;
    var t=setInterval(function(){
      fetch("/api/jobs/"+job.id).then(function(res){return res.json()}).then(function(d){
        if(!d)return;
        if(d.status==="done"){
          clearInterval(t);
          if(job.kind==="preview"){
            var pu="/api/jobs/"+job.id+"/video?t="+Date.now();
            setPreviewUrl(pu);setPrevSaved(pu); /* la chip qualité peut re-brancher ce rendu */
            setJob(null);setPop("");seekTo(0);
            fireNote(dzT("montage.rendu.apercu_pret",{s:d.duration_real_s||d.duration_s||"?"}))}
          else{
            setJob(null);setPop("");setDirty(!1);
            setDzFin({job_id:job.id,name:proj.name,project_id:proj.project_id||""});
            setDzFinStore(function(s){var n=DzTracks.finStore(s,proj.project_id||"_",{job_id:job.id,name:proj.name,at:Date.now()});try{localStorage.setItem("dz_montage_lastfin",JSON.stringify(n))}catch(_e){}return n});
            fireNote(dzT("montage.rendu.final_termine"))}}
        else if(d.status==="failed"){clearInterval(t);
          setJob(function(j){return Object.assign({},j,{status:"failed",error:d.error||dzT("montage.rendu.echec_rendu")})})}
        else{setJob(function(j){return Object.assign({},j,{status:"running",
          progress:Number(d.progress)||0,step:d.current_step||""})})}
      }).catch(function(){})},1500);
    return function(){clearInterval(t)}},[job&&job.id,job&&job.kind,job&&job.status==="failed"]);

  var phFrac=dur?ph/dur:0;
  var liveOn=!previewUrl&&!proj.demo; /* lecteur vivant : sources sous la tête */
  var liveClip=liveOn?svmActiveV1(clips,Math.min(ph,Math.max(0,dur-.001))):null;
  /* bloc de narration « actif » : le clip A1 sous la tête — karaoké par bloc
     pendant la lecture, repère de position à l'arrêt */
  var narrActive=null;
  if(narrOn){for(var iN=0;iN<clips.length;iN++){var cN=clips[iN];
    if(cN.tr==="a1"&&cN.start<=ph&&ph<cN.end){narrActive=cN.id;break}}}
  /* auto-scroll du fil vers le bloc actif (lecture) ou sélectionné —
     scrollIntoView nearest, étranglé à 300 ms. Déclaré APRÈS le calcul de
     narrActive : déclaré avant, les deps liraient la valeur du rendu
     précédent (hoisting de var) et l'effet ne se déclencherait jamais. */
  x.useEffect(function(){
    if(!narrOn)return;
    var id=null;
    if(playing&&narrActive)id=narrActive;
    else{var sc=clipsRef.current.find(function(k){return k.id===selId});
      if(sc&&sc.tr==="a1")id=sc.id}
    if(!id)return;
    var now=Date.now();if(now-narrScrollAt.current<300)return;
    narrScrollAt.current=now;
    var host=narrRef.current,el=host&&host.querySelector('[data-nbid="'+id+'"]');
    if(el&&el.scrollIntoView)try{el.scrollIntoView({block:"nearest"})}catch(_e){}},
    [narrActive,playing,narrOn,selId]);
  var tickStep=[2,3,5,6,10,15,20,30,60].find(function(s){return dur/s<=11})||60;
  var ticks=[];for(var t2=0;t2<=Math.floor(dur/tickStep)*tickStep&&ticks.length<40;t2+=tickStep)ticks.push(t2);

  /* L7 D-8 (24/09/2026, tâche 3) : le popover « Plans trop longs / jump cuts » (☰ › Affichage) — la case
     allume la carte, les deux champs bornent le juge, chaque changement est persisté (dz_svm_boring) */
  function boringPopover(){
    function boSet(p){setBo(function(b){var n=Object.assign({},b,p);try{localStorage.setItem("dz_svm_boring",JSON.stringify({on:!!n.on,maxS:n.maxS,minFrames:n.minFrames}))}catch(_e){}return n})}
    function boNum(k,lo,hi,raw){var v=Math.round(Number(raw));if(!isFinite(v))return;var p={};p[k]=Math.min(hi,Math.max(lo,v));boSet(p)}
    var nb=Object.keys(boMap).length,nj=Object.keys(boMap).filter(function(k){return boMap[k]==="jump"}).length;
    return r.jsxs("div",{className:"svm-pop svm-boringpop",onClick:function(e){e.stopPropagation()},children:[
      r.jsx("div",{className:"svm-poptitle",children:dzT("montage.boring.titre")}),
      r.jsx("div",{className:"svm-popnote",children:dzT("montage.boring.note")}),
      r.jsxs("label",{className:"svm-delrange svm-boringon",title:dzT("montage.boring.activer_aide"),children:[
        r.jsx("input",{type:"checkbox",checked:!!bo.on,onChange:function(e){boSet({on:!!e.target.checked})}}),dzT("montage.boring.activer")]}),
      r.jsxs("div",{className:"svm-fadegain svm-boringrow",children:[
        r.jsx("span",{className:"svm-fxeditname",children:dzT("montage.boring.plus_long")}),
        r.jsx("input",{className:"svm-transdur",type:"number",min:2,max:60,step:1,value:bo.maxS,title:dzT("montage.boring.plus_long_aide"),onChange:function(e){boNum("maxS",2,60,e.target.value)}})]}),
      r.jsxs("div",{className:"svm-fadegain svm-boringrow",children:[
        r.jsx("span",{className:"svm-fxeditname",children:dzT("montage.boring.ecart")}),
        r.jsx("input",{className:"svm-transdur",type:"number",min:1,max:60,step:1,value:bo.minFrames,title:dzT("montage.boring.ecart_aide"),onChange:function(e){boNum("minFrames",1,60,e.target.value)}})]}),
      r.jsx("div",{className:"svm-popnote",children:bo.on?(nb?(function(j){return nb>1?dzT("montage.boring.marques_plusieurs",{n:nb,j:j}):dzT("montage.boring.marques_un",{n:nb,j:j})})(nj>1?dzT("montage.boring.jumps_plusieurs",{n:nj}):dzT("montage.boring.jumps_un",{n:nj})):dzT("montage.boring.aucun")):dzT("montage.boring.eteinte")}),
      r.jsx("div",{className:"svm-poprow",children:
        r.jsx("button",{className:"svm-secbtn",title:dzT("montage.commun.fermer_ce_panneau_echap"),onClick:function(){setPop("")},children:dzT("montage.commun.fermer")})})]})}
  /* popover de confirmation — coût affiché avant tout déclenchement (règle produit) */
  function popover(){
    if(!pop)return null;
    if(pop==="diff")return diffSt?r.jsx(DzTracks.DiffView,Object.assign({onClose:function(){setPop("")}},diffSt)):null;
    if(pop==="boring")return boringPopover();
    var isR=pop==="render";
    var busy=job&&job.kind===(isR?"final":"preview")&&job.status!=="failed";
    var failed=job&&job.status==="failed";
    return r.jsxs("div",{className:"svm-pop",onClick:function(e){e.stopPropagation()},children:[
      r.jsx("div",{className:"svm-poptitle",children:isR?dzT("montage.rendu.titre_rendre"):dzT("montage.rendu.titre_preview")}),
      r.jsxs("div",{className:"svm-popline",children:[r.jsx("span",{children:isR?dzT("montage.rendu.ligne_rendu",{d:svmRuler(Math.round(dur))}):dzT("montage.rendu.ligne_apercu",{d:svmRuler(Math.round(dur))})}),r.jsx("span",{className:"svm-cost",children:"$0.00"})]}),
      /* L4 (D-35/D-24/D-38) : preset, cadence, loudness + pastille, plage I/O, preset maison -- rendu final seulement */
      isR?r.jsx(DzTracks.DeliverRow,{opts:dzDel,api:dzApi,lufs:lufs,hasRange:!!DzTracks.rangeFrom(proj.range),onChange:dzDelSet,onSavePreset:dzSavePreset}):null,
      isR?r.jsxs("div",{className:"svm-popline",children:[r.jsx("span",{children:dzT("montage.rendu.publication")}),r.jsx("span",{className:"svm-cost",children:dzT("montage.rendu.gratuit")})]}):null,
      proj.demo?
        r.jsx("div",{className:"svm-popnote",children:dzT("montage.rendu.demo")}):
        busy?r.jsxs("div",{className:"svm-popnote",children:[dzT("montage.rendu.en_cours"),job.progress,"% · ",job.step||"…"]}):
        failed?r.jsxs("div",{className:"svm-popnote",style:{color:"var(--red)"},children:[dzT("montage.rendu.echec_prefixe"),job.error]}):
        r.jsx("div",{className:"svm-popnote",children:isR?
          dzT("montage.rendu.note_final"):
          dzT("montage.rendu.note_apercu")}),
      r.jsxs("div",{className:"svm-poprow",children:[
        r.jsx("button",{className:"svm-secbtn",title:dzT("montage.commun.fermer_ce_panneau_echap"),onClick:function(){setPop("");if(failed)setJob(null)},children:dzT("montage.commun.fermer")}),
          failed?r.jsx("button",{className:"svm-goldbtn",disabled:proj.demo,title:proj.demo?dzT("montage.rendu.indisponible_demo"):dzT("montage.rendu.relancer_aide"),onClick:function(){launchRender(!isR)},children:dzT("montage.commun.reessayer")}):
          r.jsx("button",{className:"svm-goldbtn",disabled:busy||proj.demo,style:(busy||proj.demo)?{opacity:.55,cursor:"default"}:null,title:proj.demo?dzT("montage.rendu.indisponible_demo"):(isR?dzT("montage.rendu.lancer_final_aide"):dzT("montage.rendu.lancer_apercu_aide")),
            onClick:function(){if(!busy)launchRender(!isR)},
            children:busy?(job.progress+"%"):(isR?dzT("montage.rendu.rendre"):dzT("montage.rendu.lancer_apercu"))}),
          r.jsx("button",{className:"svm-secbtn svm-queuebtn",disabled:!isR||busy||proj.demo,title:proj.demo?dzT("montage.rendu.indisponible_demo"):!isR?dzT("montage.rendu.file_finaux"):busy?dzT("montage.rendu.deja_en_cours"):dzT("montage.rendu.file_aide"),onClick:function(){if(isR&&!busy)launchRender(!1,!0)},children:dzT("montage.rendu.ajouter_file")})]})]})}

  /* couche rack VFX (frontend/patches/vfxrack.js) — feature-detect : absente,
     tout retombe sur le sélecteur historique, rien ne casse */
  function vfxLayer(){var d=window.DzVfx;return d&&d.ready?d:null}
  /* sélecteur d'effets — panneau du rack VFX (catégories, recherche, favoris,
     vignettes d'aperçu rendues sur CE plan, pose par clic ou par glisser) */
  function fxPicker(){
    if(!fxPick)return null;
    var d=vfxLayer();
    if(d&&d.Panel)
      return r.jsx(d.Panel,{open:!0,clip:sel,stack:(sel&&sel.effects)||[],
        onClose:function(){setFxPick(!1)},
        onAdd:function(eff,meta){
          var id=selRef.current;
          if(vfxAddTo(id,eff))
            fireNote(dzT("montage.effets.pose",{effet:(meta&&meta.label)||eff.type}))}});
    return fxPickerLegacy()}
  /* sélecteur historique — conservé mot pour mot comme repli */
  function fxPickerLegacy(){
    if(!fxPick||!fxCat)return null;
    return r.jsxs("div",{className:"svm-pop",style:{top:96},children:[
      r.jsx("div",{className:"svm-poptitle",children:dzT("montage.effets.ajouter_titre")}),
      r.jsx("div",{className:"svm-fxchips",style:{marginTop:10},children:
        Object.keys(fxCat).map(function(t3){
          return r.jsx("button",{className:"svm-fxchip",style:{cursor:"pointer"},
            onClick:function(){
              var id=selRef.current;
              pushHistory();
              setClips(clipsRef.current.map(function(k){
                if(k.id!==id)return k;
                return Object.assign({},k,{effects:(k.effects||[]).concat([{type:t3,intensity:60}])})}));
              setDirty(!0);setFxPick(!1);
              fireNote(dzT("montage.effets.ajoute",{effet:(fxCat[t3]&&fxCat[t3].label)||t3}))},
            children:(fxCat[t3]&&fxCat[t3].label)||t3},t3)})}),
      r.jsx("div",{className:"svm-poprow",children:
        r.jsx("button",{className:"svm-secbtn",title:dzT("montage.effets.fermer_selecteur"),onClick:function(){setFxPick(!1)},children:dzT("montage.commun.fermer")})})]})}

  /* inspecteur — « Overlay » (clip V2 sélectionné) : position / échelle /
     rotation / opacité. Même source de vérité que la manipulation directe
     dans le lecteur (champs du clip), une entrée d'historique par rafale de
     600 ms — cohérent avec la durée de transition et le mixage par clip. */
  function ovInspector(){
    if(!sel||!DzTracks.isOverlayTrack(sel.tr,dzTracksRef.current)||!sel.src)return null;
    var tf=svmOvTfOf(sel),mp=svmMpOf(sel);
    /* valeurs affichées = transformation EFFECTIVE à la tête de lecture :
       avec des keyframes, X/Y/rotation suivent l'interpolation pendant le
       scrub — la même source que le lecteur */
    var phc=Math.min(ph,Math.max(0,dur-.001));
    var t=(mp?svmOvTfAt(sel,phc):tf)||{x:.5,y:.5,scale:1,rotate:0};
    var vOp=Math.round((mp?DzTracks.mpLerp2(mp,phc-sel.start,"opacity",sel.opacity==null?1:sel.opacity):(sel.opacity==null?1:sel.opacity))*100);
    var kfTT=mp?dzT("montage.overlay.kf_aide"):"";
    function fieldNum(props){
      return r.jsx("input",Object.assign({className:"svm-transdur",type:"number"},props))}
    /* X/Y (et rotation) : sans keyframe le champ écrit le clip (même source
       que le drag) ; avec keyframes il écrit la trajectoire (règle du drag) */
    function posField(key,raw){
      var v=Number(raw);if(!isFinite(v))return;
      var patch={};patch[key]=Math.min(1.2,Math.max(-.2,v/100));
      if(mp)svmMpField(sel,patch);else svmOvTfField(patch)}
    return r.jsxs("div",{className:"svm-transinsp",children:[
      r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:7},children:[
        r.jsx("div",{className:"svm-propk",style:{flex:"1 1 auto"},children:"Overlay"}),
        tf||mp?r.jsx("button",{className:"svm-minibtn",
          title:dzT("montage.overlay.plein_cadre_aide")+(mp?dzT("montage.overlay.plein_cadre_trajectoire"):""),
          onClick:function(){svmOvTfReset(selRef.current)},children:dzT("montage.overlay.plein_cadre")}):null]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:"X"}),
        fieldNum({min:0,max:100,step:.5,value:Math.round(t.x*200)/2,
          title:dzT("montage.overlay.x_aide")+kfTT,
          "aria-label":dzT("montage.overlay.x"),
          onChange:function(e){posField("x",e.target.value)}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"%"})]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:"Y"}),
        fieldNum({min:0,max:100,step:.5,value:Math.round(t.y*200)/2,
          title:dzT("montage.overlay.y_aide")+kfTT,
          "aria-label":dzT("montage.overlay.y"),
          onChange:function(e){posField("y",e.target.value)}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"%"})]}),
      /* grille d'alignement 3×3 — coins / bords / centre : colle le BORD
         RÉEL de l'overlay (ratio du média mesuré) à 4 % du bord du canvas */
      r.jsxs("div",{className:"svm-fadegain",style:{alignItems:"flex-start"},children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50,marginTop:22},children:dzT("montage.overlay.aligner")}),
        r.jsx("div",{className:"svm-algrid",role:"group",
          "aria-label":dzT("montage.overlay.alignement"),children:
          [0,.5,1].map(function(gy){return [0,.5,1].map(function(gx){
            var lbl=(gy===0?dzT("montage.overlay.en_haut"):gy===1?dzT("montage.overlay.en_bas"):dzT("montage.overlay.au_centre"))+
              (gx===0?dzT("montage.overlay.a_gauche"):gx===1?dzT("montage.overlay.a_droite"):gy===.5?"":dzT("montage.overlay.au_centre_x"));
            return r.jsx("button",{className:"svm-albtn",
              title:dzT("montage.overlay.coller",{pos:lbl})+kfTT,
              "aria-label":dzT("montage.overlay.aligner_pos",{pos:lbl}),
              onClick:function(){svmOvAlign(gx,gy)},
              children:r.jsx("i",{style:{left:20+gx*60+"%",top:20+gy*60+"%"}})},gx+"_"+gy)})})})]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:dzT("montage.overlay.echelle")}),
        fieldNum({min:5,max:300,step:1,value:Math.round(t.scale*100),
          title:dzT("montage.overlay.echelle_aide")+kfTT,
          "aria-label":dzT("montage.overlay.echelle_pc"),
          onChange:function(e){var v=Number(e.target.value);
            if(!isFinite(v)||v<=0)return;v=Math.min(3,Math.max(.05,v/100));
            if(mp)svmMpField(sel,{scale:v});else svmOvTfField({scale:v})}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"%"})]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:"Rotation"}),
        fieldNum({min:-180,max:180,step:1,value:Math.round(t.rotate*10)/10,
          title:dzT("montage.overlay.rotation_aide")+kfTT,
          "aria-label":dzT("montage.overlay.rotation_degres"),
          onChange:function(e){var v=Number(e.target.value);
            if(!isFinite(v))return;
            v=Math.min(180,Math.max(-180,v));
            if(mp)svmMpField(sel,{rotate:v});else svmOvTfField({rotate:v})}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"°"})]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:dzT("montage.overlay.opacite")}),
        r.jsx("input",{className:"svm-range",type:"range",min:10,max:100,step:5,value:vOp,
          title:dzT("montage.overlay.opacite_val",{v:vOp})+kfTT,"aria-label":dzT("montage.overlay.opacite_overlay"),
          onChange:function(e){var nv=Number(e.target.value)/100;var id=selRef.current;
            if(mp){svmMpField(sel,{opacity:nv});return}
            var now=Date.now();
            if(now-ovHistAt.current>600)pushHistory();
            ovHistAt.current=now;
            setClips(clipsRef.current.map(function(k){return k.id===id?Object.assign({},k,{opacity:nv>=1?void 0:nv}):k}));
            setDirty(!0)}}),
        r.jsx("span",{className:"svm-rangeval",children:vOp+" %"})]}),
      /* L7 D-19 (24/09/2026, tâche 5) : coins arrondis (px du canvas, 0..200) et ombre portée — statiques même avec des
         keyframes (D-14) ; écrits par svmOvTfField (historique par rafale de 600 ms, comme l'opacité) */
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:dzT("montage.overlay.coins")}),
        fieldNum({min:0,max:200,step:5,value:t.radius||0,
          title:dzT("montage.overlay.coins_aide"),
          "aria-label":dzT("montage.overlay.coins_px"),
          onChange:function(e){var v=Number(e.target.value);
            if(!isFinite(v))return;svmOvTfField({radius:Math.max(0,Math.min(200,Math.round(v)))})}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"px"})]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:dzT("montage.overlay.ombre")}),
        r.jsxs("label",{className:"svm-delrange svm-ovshadow",title:dzT("montage.overlay.ombre_aide"),children:[
          r.jsx("input",{type:"checkbox",checked:!!t.shadow,"aria-label":dzT("montage.overlay.ombre_portee"),onChange:function(e){svmOvTfField({shadow:e.target.checked?1:0})}}),dzT("montage.overlay.portee")]})]}),
      /* ── trajectoire (keyframes de position, R4b) — ◇ pose/écrase à la
         tête, liste compacte (clic : caler la tête, poubelle : retirer),
         losanges sur le clip V2 de la timeline ; ≥ 2 points partent au
         rendu (interpolation linéaire), l'échelle ne se keyframe pas ── */
      r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:7,marginTop:12},children:[
        r.jsx("div",{className:"svm-propk",style:{flex:"1 1 auto"},children:dzT("montage.trajectoire.titre")}),
        mp?r.jsx("span",{className:"svm-kbcount",
          title:(mp.length>1?dzT("montage.trajectoire.points_plusieurs",{n:mp.length,max:SVM_MP_CAP}):dzT("montage.trajectoire.points_un",{n:mp.length,max:SVM_MP_CAP})),
          children:mp.length+"/"+SVM_MP_CAP}):null,
        r.jsx("button",{className:"svm-minibtn svm-vpbtn",
          title:dzT("montage.trajectoire.poser_aide"),
          onClick:svmMpHere,children:__dzGlT("dz-media-image-cle",dzT("montage.trajectoire.poser"),"◇")})]}),
      mp?r.jsxs("div",{className:"svm-vplist",children:[
        mp.map(function(p,pi){
          return r.jsxs("div",{className:"svm-vprow",style:{cursor:"pointer"},
            title:dzT("montage.trajectoire.caler")+
              (p.rotate?" · rotation "+Math.round(p.rotate*10)/10+"°":""),
            onClick:function(){seekTo(sel.start+p.t)},
            children:[
            r.jsx("span",{className:"svm-vpt",children:svmShort(p.t)}),
            r.jsx("span",{"aria-hidden":!0,children:"·"}),
            r.jsx("span",{className:"svm-vpdb",children:
              Math.round(p.x*1000)/10+" · "+Math.round(p.y*1000)/10+" %"}),
            r.jsx("button",{className:"svm-minibtn svm-vpdel",
              title:dzT("montage.trajectoire.retirer"),
              "aria-label":dzT("montage.trajectoire.retirer_a",{t:svmShort(p.t)}),
              onClick:function(e){e.stopPropagation();svmMpRemove(sel.id,pi)},
              children:__dzGl("dz-action-supprimer")})]},pi)}),
        r.jsx("div",{className:"svm-vprow",children:
          r.jsx("span",{className:"svm-transnone",style:{marginTop:0,flex:"1 1 auto"},
            children:mp.length<2?dzT("montage.trajectoire.un_seul")
              :(function(){var rs={},nR=0;
                mp.forEach(function(p){if(p.rotate!=null){var kR=String(Math.round(p.rotate*10));
                  if(!rs[kR]){rs[kR]=1;nR++}}});
                return (nR>1?dzT("montage.trajectoire.interp_pos_rot")
                  :dzT("montage.trajectoire.interp_pos"))})()})})]}):
      r.jsx("div",{className:"svm-transnone",
        children:dzT("montage.trajectoire.aucun")}),
      tf||mp?null:r.jsx("div",{className:"svm-transnone",
        children:dzT("montage.overlay.plein_cadre_note")})]})}

  /* réglage d'intensité / retrait du chip d'effet en cours d'édition,
     + presets paramétrés (grade / colorize) et ratios letterbox */
  var SVM_FX_DEFAULT_PRESET={grade:"teal_orange",colorize:"duotone"};
  var SVM_LB_RATIOS=[2.39,2.35,1.85,1.78,1.33,1];
  function svmSetFxParam(i2,patch){
    var id=selRef.current;
    pushHistory();
    setClips(clipsRef.current.map(function(k){
      if(k.id!==id)return k;
      var fx=(k.effects||[]).slice();fx[i2]=Object.assign({},fx[i2],patch);
      return Object.assign({},k,{effects:fx})}));
    setDirty(!0)}
  function fxParamRow(f){
    var meta=(fxCat&&fxCat[f.type])||{};
    if(meta.presets&&meta.presets.length){
      var cur2=f.preset||SVM_FX_DEFAULT_PRESET[f.type]||meta.presets[0];
      return r.jsx("div",{className:"svm-fxchips",style:{marginTop:8},children:
        meta.presets.map(function(p3){
          return r.jsx("button",{className:"svm-fxchip",
            style:{cursor:"pointer",borderColor:p3===cur2?"var(--accent)":void 0,
              color:p3===cur2?"var(--accent)":void 0},
            onClick:function(){svmSetFxParam(fxEdit.i,{preset:p3})},
            children:p3},p3)})})}
    if(f.type==="letterbox"){
      var curR=Number(f.ratio)||2.35;
      return r.jsx("div",{className:"svm-fxchips",style:{marginTop:8},children:
        SVM_LB_RATIOS.map(function(rt){
          return r.jsx("button",{className:"svm-fxchip",
            style:{cursor:"pointer",borderColor:rt===curR?"var(--accent)":void 0,
              color:rt===curR?"var(--accent)":void 0},
            onClick:function(){svmSetFxParam(fxEdit.i,{ratio:rt})},
            children:String(rt)},rt)})})}
    return null}
  /* ── section « Effets sur ce clip » de l'inspecteur ─────────────────────
     rack VFX (pile complète : ordre, contournement, paramètres, bornes t0/t1
     et rampe, bascule avant / après) sur un clip VIDÉO réel ; chips
     historiques partout ailleurs (démo, clips audio, couche absente). */
  function vfxStackSection(){
    var d=vfxLayer();
    if(d&&d.Stack&&sel&&((sel.src&&trackKind(sel.tr)==="video")||sel.kind==="adjust"))
      return r.jsxs(r.Fragment,{children:[sel.kind==="adjust"?r.jsx(SvmLabel,{style:{margin:"20px 0 10px"},children:dzT("montage.ajustement.titre")}):null,
      sel.kind==="adjust"?dzAjFadeRow(sel):null,
      r.jsx(d.Stack,{effects:sel.effects||[],clip:sel,
        dur:Math.max(.1,sel.end-sel.start),
        onOpenPanel:function(){setFxPick(!fxPick)},
        onChange:function(next,heavy){
          /* une entrée d'historique par rafale de 600 ms — même règle que
             l'opacité d'overlay et le mixage par clip */
          var id=selRef.current,now=Date.now();
          if(heavy||now-(d.hist.t||0)>600)pushHistory();
          d.hist.t=now;
          setClips(clipsRef.current.map(function(k){
            return k.id===id?Object.assign({},k,{effects:next}):k}));
          setDirty(!0)}})]});
    return vfxLegacySection()}
  /* t117 — FONDUS D'UN CLIP D'AJUSTEMENT (sa « transition ») : le fondu d'entrée fait monter les effets qui
     COMMENCENT avec le clip, celui de sortie fait descendre ceux qui FINISSENT avec lui (montage_service.
     _adjust_bounded ; le plus long gagne si un effet porte déjà le sien dans le rack). 0 = aucun : le champ est
     RETIRÉ (payload d'avant). Borné à la moitié du clip, comme l'enveloppe des effets. Une entrée d'historique par
     rafale de 600 ms, la règle du rack. */
  function dzAjFade(which,v){
    var id=selRef.current,c=clipsRef.current.find(function(k){return k.id===id});
    if(!c||c.kind!=="adjust")return;
    var half=Math.max(0,(c.end-c.start)/2);
    v=Math.round(Math.min(half,Math.max(0,Number(v)||0))*10)/10;
    var key=which==="out"?"fade_out":"fade_in";
    if((c[key]||0)===v)return;
    var now=Date.now();
    if(now-SVM_AJ_FADE_T>600)pushHistory();
    SVM_AJ_FADE_T=now;
    setClips(clipsRef.current.map(function(k){
      if(k.id!==id)return k;
      var nk=Object.assign({},k);
      if(v>0)nk[key]=v;else delete nk[key];
      return nk}));
    setDirty(!0)}
  function dzAjFadeRow(c){
    var half=Math.max(0,(c.end-c.start)/2);
    function champ(which,lbl){var key=which==="out"?"fade_out":"fade_in";
      return r.jsxs("div",{className:"svm-prop",children:[
        r.jsx("div",{className:"svm-propk",children:lbl}),
        r.jsx("input",{className:"svm-transdur",type:"number",min:0,max:Math.round(half*10)/10,step:.1,value:c[key]||0,
          "aria-label":dzT("montage.ajustement.champ_aria",{champ:lbl}),
          title:dzT("montage.ajustement.fondu_aide",{effet:which==="out"?dzT("montage.ajustement.eteignent"):dzT("montage.ajustement.allument"),
            max:Math.round(half*10)/10}),
          onChange:function(e){dzAjFade(which,e.target.value)}})]},key)}
    return r.jsx("div",{className:"svm-props",children:[champ("in",dzT("montage.ajustement.fondu_entree")),champ("out",dzT("montage.ajustement.fondu_sortie"))]})}
  function vfxLegacySection(){
    return r.jsxs(r.Fragment,{children:[
      r.jsx(SvmLabel,{style:{margin:"20px 0 10px"},children:dzT("montage.effets.sur_ce_clip")}),
      r.jsxs("div",{className:"svm-fxchips",children:[
        /* chips fx de la maquette (clips VIDÉO) — le rack AUDIO (clé fx du
           contrat) s'édite dans l'inspecteur « Clip audio », pas ici */
        (sel&&sel.fx&&trackKind(sel.tr)!=="audio"?sel.fx:[]).map(function(f){
          return r.jsx("span",{className:"svm-fxchip","data-c":f.c,children:f.n},f.n)}),
        (sel&&sel.effects?sel.effects:[]).map(function(f,fi){
          var lbl=(fxCat&&fxCat[f.type]&&fxCat[f.type].label)||f.type;
          var editing=fxEdit&&fxEdit.id===sel.id&&fxEdit.i===fi;
          return r.jsx("button",{className:"svm-fxchip","data-c":"c3d",
            title:dzT("montage.effets.regler_aide"),
            style:{cursor:"pointer",borderColor:editing?"var(--accent)":void 0},
            onClick:function(){setFxEdit(editing?null:{id:selRef.current,i:fi})},
            children:lbl},f.type+fi)}),
        r.jsx("button",{className:"svm-fxadd",
          onClick:function(){
            if(!sel||!sel.src){fireNote(dzT("montage.effets.demo"));return}
            if(!vfxLayer()&&!fxCat){fireNote(dzT("montage.effets.catalogue_absent"));return}
            setFxPick(!fxPick)},
          children:dzT("montage.effets.ajouter")})]}),
      fxEditRow()]})}
  function fxEditRow(){
    if(!fxEdit||!sel||fxEdit.id!==sel.id)return null;
    var f=(sel.effects||[])[fxEdit.i];if(!f)return null;
    var meta=(fxCat&&fxCat[f.type])||{};var lbl=meta.label||f.type;
    var hasInt=(meta.params||[]).indexOf("intensity")>=0;
    return r.jsxs(r.Fragment,{children:[r.jsxs("div",{className:"svm-fxedit",children:[
      r.jsx("span",{className:"svm-fxeditname",children:lbl}),
      hasInt?r.jsx("input",{className:"svm-range",type:"range",min:5,max:100,step:5,
        value:Math.round(f.intensity!=null?f.intensity:60),
        "aria-label":dzT("montage.effets.intensite",{effet:lbl}),
        onChange:function(e){var nv=Number(e.target.value);var id=selRef.current,i2=fxEdit.i;
          setClips(clipsRef.current.map(function(k){
            if(k.id!==id)return k;
            var fx=(k.effects||[]).slice();fx[i2]=Object.assign({},fx[i2],{intensity:nv});
            return Object.assign({},k,{effects:fx})}));
          setDirty(!0)}}):
        r.jsx("span",{className:"svm-note",style:{flex:1,marginTop:0},children:dzT("montage.effets.sans_intensite")}),
      hasInt?r.jsx("span",{className:"svm-rangeval",children:Math.round(f.intensity!=null?f.intensity:60)}):null,
      r.jsx("button",{className:"svm-minibtn",title:dzT("montage.effets.retirer_aide"),onClick:function(){
        var id=selRef.current,i2=fxEdit.i;
        pushHistory();
        setClips(clipsRef.current.map(function(k){
          if(k.id!==id)return k;
          var fx=(k.effects||[]).slice();fx.splice(i2,1);
          return Object.assign({},k,{effects:fx})}));
        setFxEdit(null);setDirty(!0)},children:dzT("montage.effets.retirer")})]}),
      fxParamRow(f)]})}

  /* sélecteur d'assets — contenu filtré selon le type de la piste visée */
  function ovPicker(){
    if(!ovPick||!sources)return null;
    var tr2=ovPick,audio=trackKind(tr2)==="audio";
    /* P6 — LE MODE REMPLACEMENT EST VISIBLE PENDANT QU'IL EST ARMÉ.
       `dzmArm` est le miroir d'affichage de `dzmReplaceRef` (voir
       M4b) : la ref reste ce que lit `addAsset`, l'état n'est là que
       pour que ce panneau se re-rende et change de discours.
       LA PISTE EST COMPARÉE, comme dans l'effet de désarmement : cet
       effet s'exécute APRÈS le rendu, donc un sélecteur rouvert sur
       une AUTRE piste aurait affiché « Remplacer… » le temps d'une
       image avant de se corriger. La condition d'affichage est la
       même que celle de l'armement, pas une seconde règle. */
    var dzmA=(dzmArm&&dzmArm.tr===tr2)?dzmArm:null;
    return r.jsxs("div",{className:"svm-pop",style:{top:96},children:[
      r.jsx("div",{className:"svm-poptitle",children:dzmA
        ?(dzT("montage.selecteur.remplacer_titre",{nom:dzmA.label||dzT("montage.selecteur.ce_plan")}))
        :(dzT("montage.selecteur.ajouter_titre",{piste:tr2.toUpperCase()}))}),
      dzmA?null:r.jsx(DzTracks.ModeBar,{mode:dzMode,onMode:setDzMode,
        range:proj.range}),
      r.jsx("div",{className:"svm-popnote",style:{marginTop:6},
        children:dzmA?(dzT("montage.selecteur.remplacer_note",{piste:dzmA.tr.toUpperCase()}))
               :audio?(dzT("montage.selecteur.note_audio",{t:svmShort(ph)}))
                      :(dzT("montage.selecteur.note_video",{t:svmShort(ph)}))}),
      audio?null:r.jsx(SvmLabel,{style:{marginTop:12},children:dzT("montage.selecteur.images")}),
      audio?null:(sources.images.length?
        r.jsx("div",{className:"svm-ovgrid",children:sources.images.map(function(im){
          return r.jsx("button",{className:"svm-ovimg",title:dzT("montage.selecteur.cliquer_glisser",{nom:im.name}),draggable:!0,
            onDragStart:function(e){dragPayload(e,{image:im.name},im.name,"image",0)},
            style:{backgroundImage:"url('/api/images/"+encodeURIComponent(im.name)+"')",backgroundSize:"cover",backgroundPosition:"center"},
            onClick:function(){addAsset({image:im.name},im.name,"image",0,tr2)}},im.name)})}):
        r.jsx("div",{className:"svm-note",children:dzT("montage.selecteur.aucune_image")})),
      audio?null:r.jsx(SvmLabel,{style:{marginTop:12},children:dzT("montage.selecteur.rendus_video")}),
      audio?null:(sources.videos.length?
        r.jsx("div",{className:"svm-ovlist",children:sources.videos.map(function(v3){
          return r.jsxs("button",{className:"svm-fxchip",style:{cursor:"pointer",textAlign:"left"},draggable:!0,
            title:dzT("montage.selecteur.cliquer_glisser",{nom:v3.title}),
            onDragStart:function(e){dragPayload(e,{job_id:v3.job_id},v3.title,"video",v3.dur)},
            onClick:function(){addAsset({job_id:v3.job_id},v3.title,"video",v3.dur,tr2)},
            children:[v3.title," · ",v3.dur?svmRuler(Math.round(v3.dur)):"—"]},v3.job_id)})}):
        r.jsx("div",{className:"svm-note",children:dzT("montage.overlay.aucun_rendu")})),
      audio?r.jsx(SvmLabel,{style:{marginTop:12},children:dzT("montage.overlay.sons_biblio")}):null,
      audio?((sources.audios&&sources.audios.length)?
        r.jsx("div",{className:"svm-ovlist",children:sources.audios.map(function(a3){
          return r.jsxs("button",{className:"svm-fxchip",style:{cursor:"pointer",textAlign:"left"},draggable:!0,
            title:a3.name+dzT("montage.overlay.cliquer_glisser"),
            onDragStart:function(e){dragPayload(e,{audio:a3.name},a3.name,"audio",0)},
            onClick:function(){addAsset({audio:a3.name},a3.name,"audio",0,tr2)},
            children:[a3.name,a3.kb?" · "+a3.kb+dzT("montage.unites.ko"):""]},a3.name)})}):
        r.jsx("div",{className:"svm-note",children:dzT("montage.overlay.aucun_son")})):null,
      r.jsx("div",{className:"svm-poprow",children:
        r.jsx("button",{className:"svm-secbtn",title:dzT("montage.overlay.fermer_aide"),onClick:function(){setOvPick("")},children:dzT("montage.commun.fermer")})})]})}

  /* panneau « Raccourcis clavier » — modal centré (motif .svm-pop, z 20),
     voile léger, fermé par Échap, clic extérieur ou le bouton ; ouvert par ?
     ou le bouton « ? » discret en fin de transport. R4c : chaque combo est
     un bouton — cliquer arme la capture ([data-editing], « appuyez sur une
     touche… »), la prochaine combinaison pressée est enregistrée
     (dz_svm_keymap) ; conflit ou touche navigateur : refus expliqué inline,
     jamais d'écrasement silencieux. */
  function kbPanel(){
    if(!kbOn)return null;
    var hasSfx=!!svmSfx();
    /* lignes = actions remappables (une combo VIVANTE chacune) + rappels de
       gestes souris (non remappables, assumés tels). Couche DzSfx absente :
       la ligne « tiroir Sons » disparaît — jamais un raccourci mort. */
    var rows=[];
    SVM_ACTIONS.forEach(function(a){
      if(a.id==="sounds_drawer"&&!hasSfx)return;
      rows.push({act:a})});
    SVM_KEYS_INFO.forEach(function(inf){rows.push({info:inf})});
    var total=rows.length;
    /* recherche — filtre vivant libellé + combo (remappée ET défaut), sans
       accents ; compteur « visibles/total » ; Échap : vide, puis ferme */
    var q=svmNorm(kbQuery.trim());
    function rowText(r2){
      return r2.act?r2.act.lbl+" "+km.byId[r2.act.id]+" "+r2.act.combo
        :r2.info.lbl+" "+(r2.info.keys||[]).join(" ")+" "+
         (r2.info.acts||[]).map(svmKeyLabel).join(" ")}
    var view=SVM_KEY_SECTIONS.map(function(sec){
      return {name:sec,list:rows.filter(function(r2){
        if((r2.act?r2.act.sec:r2.info.sec)!==sec)return !1;
        return !q||svmNorm(rowText(r2)).indexOf(q)>=0})}});
    var shown=0;view.forEach(function(s2){shown+=s2.list.length});
    var nOv=Object.keys(kmOv).length;
    function chips(parts,user){
      return r.jsx("span",{className:"svm-kbds","data-user":user?"":void 0,
        children:parts.map(function(kk,i3){
          return r.jsx("kbd",{children:String(kk).replace(/Maj/,dzT("montage.touches.maj")).replace(/Échap/,dzT("montage.touches.echap")).replace(/Espace/,dzT("montage.touches.espace"))},i3)})})}
    function actRow(a){
      var c=km.byId[a.id],isOv=!!kmOv[a.id],editing=kbEdit===a.id;
      var msg=kbMsg&&kbMsg.id===a.id?kbMsg.msg:null;
      return r.jsxs("div",{className:"svm-keyrow",children:[
        r.jsx("button",{className:"svm-kbdbtn","data-editing":editing?"":void 0,
          title:editing?dzT("montage.raccourcis.capture_aide")
            :dzT("montage.raccourcis.remapper_aide",{action:a.lbl})+
             (isOv?dzT("montage.raccourcis.defaut_suffixe")+a.combo:""),
          "aria-label":dzT("montage.raccourcis.remapper_aria",{action:a.lbl,combo:c}),
          onClick:function(){setKbMsg(null);setKbConfirm(!1);
            setKbEdit(editing?"":a.id)},
          children:editing
            ?r.jsx("span",{className:"svm-kbwait",children:dzT("montage.raccourcis.attente_touche")})
            :chips(c.split("+"),isOv)}),
        r.jsxs("span",{className:"svm-keylbl",children:[a.lbl,
          msg?r.jsx("span",{className:"svm-kbmsg",children:msg}):null]}),
        isOv&&!editing?r.jsx("button",{className:"svm-minibtn svm-kbreset","data-on":"",
          title:dzT("montage.raccourcis.revenir_defaut")+a.combo,
          "aria-label":dzT("montage.raccourcis.reinit_aria",{action:a.lbl,combo:a.combo}),
          onClick:function(){setKbMsg(null);
            setKmOv(function(o){var n=Object.assign({},o);delete n[a.id];
              svmKmSave(n);return n})},
          children:dzT("montage.raccourcis.reinitialiser")}):null]},a.id)}
    function infoRow(inf,i2){
      return r.jsxs("div",{className:"svm-keyrow svm-keyinfo",
        title:dzT("montage.raccourcis.fixe_aide"),children:[
        chips(inf.acts?inf.acts.map(svmKeyLabel):inf.keys,!1),
        r.jsx("span",{className:"svm-keylbl",children:inf.lbl})]},"i"+i2)}
    return r.jsx("div",{className:"svm-kbscrim",onClick:function(){setKbOn(!1)},children:
      r.jsxs("div",{className:"svm-pop svm-kbpop",role:"dialog","aria-modal":!0,
        "aria-label":dzT("montage.raccourcis.titre"),
        onClick:function(e){e.stopPropagation()},children:[
        r.jsx("div",{className:"svm-poptitle",children:dzT("montage.raccourcis.titre")}),
        r.jsx("div",{className:"svm-kbsub",children:dzT("montage.raccourcis.sous_titre")}),
        r.jsxs("div",{className:"svm-kbsearch",children:[
          r.jsx("input",{className:"svm-kbfind",type:"text",value:kbQuery,autoFocus:!0,
            placeholder:dzT("montage.raccourcis.recherche"),
            "aria-label":dzT("montage.raccourcis.recherche_aria"),
            onChange:function(e){setKbQuery(e.target.value)},
            onKeyDown:function(e){
              if(e.key!=="Escape")return;
              e.preventDefault();e.stopPropagation();
              if(kbQuery)setKbQuery("");else setKbOn(!1)}}),
          r.jsx("span",{className:"svm-kbcount",
            title:(shown>1?dzT("montage.raccourcis.compte.plusieurs",{n:shown,total:total}):dzT("montage.raccourcis.compte.un",{n:shown,total:total})),
            children:shown+"/"+total}),
          r.jsx("button",{className:"svm-secbtn svm-kbio",title:dzT("montage.raccourcis.resolve_aide"),
            onClick:function(){var pr=DzTracks.kmPreset("resolve");if(!pr){fireNote(dzT("montage.raccourcis.preset_introuvable"));return}setKmOv(pr);svmKmSave(pr);setKbEdit("");setKbMsg(null);
              fireNote(dzT("montage.raccourcis.resolve_applique"))},
            children:dzT("montage.raccourcis.resolve")}),
          r.jsx("button",{className:"svm-secbtn svm-kbio",title:dzT("montage.raccourcis.exporter_aide"),
            onClick:function(){if(!subsDownload("deepotus-raccourcis.json",DzTracks.kmExport(kmOv),"application/json")){fireNote(dzT("montage.raccourcis.export_impossible"));return}
              fireNote(nOv?(nOv>1?dzT("montage.raccourcis.exportes.plusieurs",{n:nOv}):dzT("montage.raccourcis.exportes.un",{n:nOv})):dzT("montage.raccourcis.export_vide"))},
            children:dzT("montage.commun.exporter_suite")}),
          r.jsx("button",{className:"svm-secbtn svm-kbio",title:dzT("montage.raccourcis.importer_aide"),
            onClick:function(){var inp=document.createElement("input");inp.type="file";inp.accept=".json,application/json";
              inp.onchange=function(){var f=inp.files&&inp.files[0];if(!f)return;var rd=new FileReader();
                rd.onload=function(){var rs=DzTracks.kmImport(String(rd.result||""),SVM_ACTIONS,svmComboCanon,svmComboReserved);
                  if(!rs.ok){fireNote(rs.raison==="json"?dzT("montage.raccourcis.pas_json"):dzT("montage.raccourcis.version_inconnue"));return}
                  setKmOv(rs.keymap);svmKmSave(rs.keymap);setKbEdit("");setKbMsg(null);var nk=Object.keys(rs.keymap).length,ni=rs.ignores.length;
                  fireNote((nk>1?dzT("montage.raccourcis.importes.plusieurs",{n:nk}):dzT("montage.raccourcis.importes.un",{n:nk}))+(ni?(ni>1?dzT("montage.raccourcis.ignores.plusieurs",{n:ni}):dzT("montage.raccourcis.ignores.un",{n:ni})):""))};
                rd.onerror=function(){fireNote(dzT("montage.raccourcis.fichier_illisible"))};rd.readAsText(f)};
              inp.click()},
            children:dzT("montage.commun.importer_suite")}),
          /* « Réinitialiser tout » — visible dès qu'un override existe,
             confirmation INLINE (le panneau ne s'empile pas de modales) */
          nOv?(kbConfirm?
            r.jsxs("span",{className:"svm-kbconfirm",children:[
              r.jsx("span",{children:(nOv>1?dzT("montage.raccourcis.revenir_defauts.plusieurs",{n:nOv}):dzT("montage.raccourcis.revenir_defauts.un",{n:nOv}))}),
              r.jsx("button",{className:"svm-minibtn",
                title:dzT("montage.raccourcis.confirmer_reinit"),
                onClick:function(){setKmOv({});svmKmSave({});
                  setKbConfirm(!1);setKbEdit("");setKbMsg(null)},
                children:dzT("montage.commun.oui_minuscule")}),
              r.jsx("button",{className:"svm-minibtn svm-kbno",
                title:dzT("montage.raccourcis.garder"),
                onClick:function(){setKbConfirm(!1)},children:dzT("montage.commun.non_minuscule")})]}):
            r.jsx("button",{className:"svm-secbtn svm-kbresetall",
              title:(nOv>1?dzT("montage.raccourcis.reinit_tout_aide.plusieurs",{n:nOv}):dzT("montage.raccourcis.reinit_tout_aide.un",{n:nOv})),
              onClick:function(){setKbConfirm(!0)},children:dzT("montage.raccourcis.reinit_tout")})):null]}),
        shown?r.jsx("div",{className:"svm-keys",children:view.map(function(sec){
          if(!sec.list.length)return null;
          return r.jsxs("div",{className:"svm-keysec",children:[
            r.jsx(SvmLabel,{children:({Lecture:dzT("montage.raccourcis.section_lecture"),Montage:dzT("montage.raccourcis.section_montage"),Affichage:dzT("montage.raccourcis.section_affichage")})[sec.name]||sec.name}),
            sec.list.map(function(r2,i2){
              return r2.act?actRow(r2.act):infoRow(r2.info,i2)})]},sec.name)})}):
        r.jsx("div",{className:"svm-transnone",style:{marginTop:14},
          children:dzT("montage.raccourcis.aucun")}),
        r.jsx("div",{className:"svm-poprow",children:
          r.jsx("button",{className:"svm-secbtn",title:dzT("montage.raccourcis.fermer_aide"),onClick:function(){setKbOn(!1)},children:dzT("montage.commun.fermer")})})]})})}

  /* mini-popover de jonction — règle la transition du clip de DROITE */
  function transPopover(){
    if(!transPop)return null;
    var jc=clips.find(function(k){return k.id===transPop.id});
    if(!jc||!svmLeftNeighbor(clips,jc))return null;
    var base=svmTransBase(jc.transition),isCut=base==="cut",s2=svmTransS(jc);
    return r.jsxs("div",{className:"svm-pop svm-transpop",style:{left:transPop.x},children:[
      r.jsx("div",{className:"svm-poptitle",children:dzT("montage.jonction.titre")}),
      /* D-20 — LA GALERIE. Les sept tuiles cèdent la place à
         TransGrid() de la couche : « coupe », puis les historiques du
         bundle qui ne sont pas au catalogue, puis les six
         familles servies. La couche garde `.svm-transtile`,
         `.svm-tprev` et `data-tt` — les règles du bundle
         continuent d'animer la moitié gauche, de mettre en
         pause hors survol et de figer la tuile choisie ;
         `data-fam` et `data-dir` n'ajoutent que l'animation de
         la moitié droite, dans montage.css. */
      r.jsx(DzTracks.TransGrid,{legacy:SVM_TRANS,cat:dzTransCat,cur:base,
        onPick:function(id){svmSetTransType(jc.id,id)}}),
      /* L7 D-3b (24/09/2026, tâche 4-bis) : A/B à la jonction — la dernière image du plan gauche, la première du plan
         droit (vignettes du navigateur, au 1/30 s près) et le roll d'une image (Maj : dix) ; rangée TOUJOURS rendue,
         grisée quand les deux plans ne sont pas des vidéos en contact */
      r.jsxs("div",{className:"svm-abrow",children:[
        r.jsx("img",{className:"svm-abthumb",src:abA||void 0,alt:"","data-ab":"a",draggable:!1,title:dzT("montage.jonction.vignette_a")}),
        r.jsx("button",{className:"svm-secbtn svm-abbtn",disabled:!abOk,"aria-disabled":!abOk,title:dzT("montage.jonction.reculer"),onClick:function(e){abRoll(e.shiftKey?-10:-1)},children:__dzGlT("dz-media-image-precedente","◀ −1","◀")}),
        r.jsx("button",{className:"svm-secbtn svm-abbtn",disabled:!abOk,"aria-disabled":!abOk,title:dzT("montage.jonction.avancer"),onClick:function(e){abRoll(e.shiftKey?10:1)},children:__dzGlT("dz-media-image-suivante","+1 ▶","▶")}),
        r.jsx("img",{className:"svm-abthumb",src:abB||void 0,alt:"","data-ab":"b",draggable:!1,title:dzT("montage.jonction.vignette_b")})]}),
      r.jsxs("div",{className:"svm-fxedit",style:{marginTop:10},children:[
        r.jsx("span",{className:"svm-fxeditname",children:dzT("montage.commun.duree")}),
        r.jsx("span",{className:"svm-transbound","aria-hidden":!0,children:"0.1 s"}),
        r.jsx("input",{className:"svm-range",type:"range",min:.1,max:1,step:.05,
          value:isCut?.4:s2,disabled:isCut,"aria-label":dzT("montage.jonction.duree_aria"),
          onChange:function(e){svmSetTransDur(jc.id,Number(e.target.value))}}),
        r.jsx("span",{className:"svm-transbound","aria-hidden":!0,children:"1.0 s"}),
        r.jsx("span",{className:"svm-rangeval",children:isCut?"—":s2.toFixed(2)+" s"})]}),
      r.jsx("div",{className:"svm-poprow",children:
        r.jsx("button",{className:"svm-secbtn",style:{width:"100%"},
          title:dzT("montage.jonction.copier_aide"),
          onClick:function(){svmApplyTransAll(base,isCut?0:s2)},
          children:dzT("montage.jonction.appliquer_tout")})})]})}

  /* inspecteur — transition d'entrée du clip V1 sélectionné ; le backend
     ignore celle du premier clip et des jonctions avec trou */
  function transInspector(){
    if(!sel||trackKind(sel.tr)!=="video")return null;   /* t117 : toute piste vidéo */
    var left=svmLeftNeighbor(clips,sel);
    var base=svmTransBase(sel.transition),isCut=base==="cut",s2=svmTransS(sel);
    var known=DzTracks.transList(SVM_TRANS,dzTransCat).some(function(f){
      return f.items.some(function(it){return it.id===base})});
    return r.jsxs("div",{className:"svm-transinsp",children:[
      r.jsx("div",{className:"svm-propk",children:dzT("montage.transition.titre")}),
      left?r.jsxs("div",{style:{display:"flex",gap:7,marginTop:6,alignItems:"center"},children:[
        r.jsx("select",{className:"svm-secbtn",style:{flex:"1 1 auto",minWidth:0,padding:"5px 8px"},
          value:base,title:dzT("montage.transition.type_aide"),"aria-label":dzT("montage.transition.type_aria"),
          onChange:function(e){svmSetTransType(sel.id,e.target.value)},
          children:(known?[]:[r.jsx("option",{value:base,children:base+dzT("montage.transition.herite")},"_leg")])
            .concat(DzTracks.transList(SVM_TRANS,dzTransCat)
              .reduce(function(a,f){return a.concat(f.items.map(function(it){
                return r.jsx("option",{value:it.id,
                  children:f.label+" · "+it.label},it.id)}))},[]))}),
        r.jsx("input",{className:"svm-transdur",type:"number",min:.1,max:1,step:.05,
          value:isCut?"":s2,disabled:isCut,
          title:dzT("montage.transition.duree_aide"),"aria-label":dzT("montage.transition.duree_aria"),
          onChange:function(e){var v=Number(e.target.value);
            if(isFinite(v)&&v>0)svmSetTransDur(sel.id,v)}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"s"})]}):
      r.jsx("div",{className:"svm-transnone",children:dzT("montage.transition.aucune")})]})}

  /* ── mesure loudness — /api/montage/measure : mix audio-only du payload
     COURANT (mêmes clips, mix, ducking que le rendu) passé dans ebur128 ;
     I/TP/LRA affichés par DzSfx.Meter et mémorisés (dz_last_lufs) pour
     l'écran Son & VFX ── */
  function doMeasure(){
    if(proj.demo){fireNote(dzT("montage.lufs.demo"));return}
    if(lufsBusy)return;
    setLufsBusy(!0);
    fetch("/api/montage/measure",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify(renderPayload(!0))})
      .then(function(res){return res.json().catch(function(){return {}})
        .then(function(d){return {ok:res.ok,d:d}})})
      .then(function(o){
        setLufsBusy(!1);
        if(!o.ok||!o.d||o.d.ok===!1||o.d.lufs_i==null)
          throw new Error((o.d&&(o.d.detail||o.d.error))||dzT("montage.lufs.impossible_min"));
        var m={i:Number(o.d.lufs_i),tp:Number(o.d.tp),lra:Number(o.d.lra)};
        setLufs(m);
        try{localStorage.setItem("dz_last_lufs",JSON.stringify(
          {i:m.i,tp:m.tp,lra:m.lra,at:Date.now(),name:proj.name}))}catch(_e){}
        fireNote(dzT("montage.lufs.resultat",{i:Math.round(m.i*10)/10,
          tp:Math.round(m.tp*10)/10,lra:Math.round(m.lra*10)/10}))})
      .catch(function(e){setLufsBusy(!1);
        fireNote(dzT("montage.lufs.impossible")+String(e&&e.message||e))})}
  /* ── écoute rendue d'un clip audio (rack d'effets) — /api/audio/audition
     renvoie un WAV traité par LA chaîne ffmpeg du rendu (parité deesser /
     denoise / normalize) ; un seul flux à la fois, URL blob révoquée après ── */
  function stopAudition(){
    var o=auditionRef.current;
    if(o){try{o.a.pause()}catch(_e){}
      if(o.url){try{URL.revokeObjectURL(o.url)}catch(_e){}}
      auditionRef.current=null}}
  x.useEffect(function(){if(playing)stopAudition()},[playing]);
  x.useEffect(function(){return stopAudition},[]);
  function sfxAudition(fx){
    var c=clipsRef.current.find(function(k){return k.id===selRef.current});
    if(!c||!c.src||!(c.src.audio||c.src.job_id)){
      fireNote(dzT("montage.audition.sans_source"));return}
    stopAudition();narrStop();
    if(playingRef.current)setPlaying(!1); /* jamais deux flux à la fois */
    /* L6 (25/09/2026) : le son d'un plan s'écoute rendu lui aussi (la route résout le job en son fichier rendu) */
    var body={src_in:c.srcIn||0,
      len:Math.min(12,Math.max(.2,c.end-c.start)),
      gain_db:Math.round(Number(c.gain)||0),
      speed:typeof c.speed==="number"&&c.speed>0?c.speed:1,
      fx:Array.isArray(fx)?fx:[]};
    if(c.src.job_id)body.job_id=String(c.src.job_id);else body.filename=c.src.audio;
    fetch("/api/audio/audition",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify(body)})
      .then(function(res){
        if(!res.ok)return res.json().catch(function(){return {}}).then(function(d){
          throw new Error((d&&(d.detail||d.error))||dzT("montage.audition.impossible"))});
        return res.blob()})
      .then(function(b){
        var url=URL.createObjectURL(b),a=new Audio(url);
        auditionRef.current={a:a,url:url};
        a.onended=stopAudition;a.onerror=stopAudition;
        a.play().catch(function(){stopAudition();
          fireNote(dzT("montage.commun.lecture_bloquee"))})})
      .catch(function(e){fireNote(dzT("montage.audition.erreur")+String(e&&e.message||e))})}
  /* ── réglages ducking — proj.ducking (contrat : ratio 2–20, attaque
     5–500 ms, retour 50–2000 ms, seuil 0.01–0.3) ; « défaut » retire l'objet
     et le payload redevient le booléen historique ── */
  function duckCfg(){var d2=proj.ducking||{};
    return {ratio:Number(d2.ratio)||6,attack_ms:Number(d2.attack_ms)||50,
      release_ms:Number(d2.release_ms)||400,threshold:Number(d2.threshold)||.05}}
  function setDuck(patch){
    setProj(function(p){
      var base=p.ducking||{ratio:6,attack_ms:50,release_ms:400,threshold:.05};
      return Object.assign({},p,{ducking:Object.assign({},base,patch)})});
    setDirty(!0)}
  function resetDuck(){
    setProj(function(p){var np=Object.assign({},p);delete np.ducking;return np});
    setDirty(!0);
    fireNote(dzT("montage.ducking.defaut"))}
  function duckPanel(){
    var dk=duckCfg();
    function dkRow(lbl,tt,min,max,step,val,txt,key){
      return r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:52},children:lbl}),
        r.jsx("input",{className:"svm-range",type:"range",min:min,max:max,step:step,value:val,
          title:tt,"aria-label":dzT("montage.ducking.aria",{param:lbl}),
          onChange:function(e){var v=Number(e.target.value);
            var patch={};patch[key]=v;setDuck(patch)}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:52},children:txt})]})}
    return r.jsxs("div",{className:"svm-duckpanel",children:[
      r.jsx("div",{className:"svm-fxchips",children:
        [[dzT("montage.ducking.leger"),3],[dzT("montage.ducking.moyen"),6],[dzT("montage.ducking.fort"),10]].map(function(p2){
          return r.jsx("button",{className:"svm-fxchip",
            style:{cursor:"pointer",borderColor:dk.ratio===p2[1]?"var(--accent)":void 0,
              color:dk.ratio===p2[1]?"var(--accent)":void 0},
            title:dzT("montage.ducking.rapport_aide",{r:p2[1]}),
            onClick:function(){setDuck({ratio:p2[1]})},
            children:p2[0]+" "+p2[1]+":1"},p2[0])})}),
      dkRow(dzT("montage.ducking.attaque"),dzT("montage.ducking.attaque_aide"),
        5,500,5,dk.attack_ms,Math.round(dk.attack_ms)+" ms","attack_ms"),
      dkRow(dzT("montage.ducking.retour"),dzT("montage.ducking.retour_aide"),
        50,2000,10,dk.release_ms,Math.round(dk.release_ms)+" ms","release_ms"),
      dkRow(dzT("montage.ducking.seuil"),dzT("montage.ducking.seuil_aide"),
        .01,.3,.01,dk.threshold,dk.threshold.toFixed(2),"threshold"),
      r.jsx("div",{className:"svm-transnone",style:{marginTop:8},
        children:dzT("montage.ducking.jamais_perso")})]})}

  /* inspecteur — « Clip audio » : gain −24..+12 dB (multiplié au gain de bus
     par le rendu, jamais un remplacement) + fondus 0..3 s bornés à la moitié
     du clip ; la musique A2 bouclée garde sa note dédiée */
  function audioInspector(){
    if(!sel||trackKind(sel.tr)!=="audio"||!sel.src)return null;
    var g=Math.round(Number(sel.gain)||0);
    var len=Math.max(.2,sel.end-sel.start),fmax=Math.min(3,Math.floor(len*5)/10);
    var isMus=sel.id===firstA2;
    var dzsfx=svmSfx();
    var spdv=typeof sel.speed==="number"&&sel.speed>0?sel.speed:1;
    function setF(key,raw){
      var v=Number(raw);if(!isFinite(v))return;
      v=Math.max(0,Math.min(fmax,Math.round(v*10)/10));
      var patch={};patch[key]=v;
      svmSetClipAudio(sel.id,patch)}
    var vp=svmVpOf(sel); /* automation (R4) — invariant : déjà trié par t */
    return r.jsxs("div",{className:"svm-transinsp",children:[
      r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:7},children:[
        r.jsx("div",{className:"svm-propk",style:{flex:"1 1 auto"},children:dzT("montage.audio.titre")}),
        /* mode automation ◇ — actif : ligne + losanges éditables sur le clip
           sélectionné (double-clic : poser, drag : t/dB, clic droit ou
           Suppr : retirer) ; les points existants restent toujours visibles
           et partent au rendu dès 2 points */
        r.jsx("button",{className:"svm-minibtn svm-vpbtn","data-on":autoOn?"":void 0,
          "aria-pressed":autoOn,
          title:dzT("montage.audio.automation_aide",{touche:svmKeyLabel("delete")})+
            (isMus?dzT("montage.audio.automation_musique"):""),
          onClick:function(){setAutoOn(!autoOn)},children:__dzGlT("dz-media-automation","◇ automation","◇")})]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",children:"Gain"}),
        r.jsx("input",{className:"svm-range",type:"range",min:-24,max:12,step:1,value:g,
          title:dzT("montage.audio.gain_aide",{db:svmDbTxt(g),bus:(SVM_TRACK_BUS[sel.tr]||"")}),
          "aria-label":dzT("montage.audio.gain_aria"),
          onChange:function(e){svmSetClipAudio(selRef.current,{gain:Math.round(Number(e.target.value))||0})}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:44},children:svmDbTxt(g)})]}),
      /* liste compacte des points d'automation — sous le gain ; poubelle par
         ligne, « aplatir » retire tout (le payload redevient celui d'avant) */
      vp?r.jsxs("div",{className:"svm-vplist",children:[
        vp.map(function(p,pi){
          return r.jsxs("div",{className:"svm-vprow",children:[
            r.jsx("span",{className:"svm-vpt",
              title:isMus?dzT("montage.audio.point_position_musique",{t:svmShort(sel.start)}):dzT("montage.audio.point_temps_local"),
              children:svmShort(p.t)}),
            r.jsx("span",{"aria-hidden":!0,children:"·"}),
            r.jsx("span",{className:"svm-vpdb",children:svmVpDbTxt(p.db)}),
            r.jsx("button",{className:"svm-minibtn svm-vpdel",
              title:dzT("montage.audio.point_retirer"),
              "aria-label":dzT("montage.audio.point_retirer_aria")+svmShort(p.t),
              onClick:function(){svmVpRemove(sel.id,pi)},children:__dzGl("dz-action-supprimer")})]},pi)}),
        r.jsxs("div",{className:"svm-vprow",children:[
          r.jsx("span",{className:"svm-transnone",style:{marginTop:0,flex:"1 1 auto"},
            children:vp.length<2?dzT("montage.audio.un_seul_point")
              :dzT("montage.audio.courbe_multiplie")+(isMus?dzT("montage.audio.t_rendu"):"")}),
          r.jsx("button",{className:"svm-minibtn",
            title:dzT("montage.audio.aplatir_aide"),
            onClick:function(){svmVpFlatten(sel.id)},children:dzT("montage.audio.aplatir")})]})]}):
      autoOn?r.jsx("div",{className:"svm-transnone",
        children:dzT("montage.audio.automation_mode")}):null,
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",children:dzT("montage.audio.fondus")}),
        r.jsx("input",{className:"svm-transdur",type:"number",min:0,max:fmax,step:.1,
          value:Number(sel.fade_in)||0,
          title:dzT("montage.audio.fondu_entree_aide",{max:fmax}),"aria-label":dzT("montage.audio.fondu_entree_aria"),
          onChange:function(e){setF("fade_in",e.target.value)}}),
        r.jsx("span",{className:"svm-fadesep","aria-hidden":!0,children:"in · out"}),
        r.jsx("input",{className:"svm-transdur",type:"number",min:0,max:fmax,step:.1,
          value:Number(sel.fade_out)||0,
          title:(isMus?dzT("montage.audio.fondu_fin_aide",{max:fmax}):dzT("montage.audio.fondu_sortie_aide",{max:fmax})),
          "aria-label":isMus?dzT("montage.audio.fondu_fin_aria"):dzT("montage.audio.fondu_sortie_aria"),
          onChange:function(e){setF("fade_out",e.target.value)}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"s"})]}),
      /* courbes de fondu (R2/I4) — 4 chips par côté ACTIF (fade > 0) ; l'or
         marque la courbe retenue, « lin » n'écrit rien sur le clip */
      [["in","fade_in"],["out","fade_out"]].map(function(sd){
        if(!(Number(sel[sd[1]])>0))return null;
        var ck=sd[1]+"_curve",curCv=sel[ck]||"lin";
        return r.jsxs("div",{className:"svm-curverow",children:[
          r.jsx("span",{className:"svm-curvelbl","aria-hidden":!0,children:sd[0]}),
          SVM_FADE_CURVES.map(function(o){
            var on=curCv===o[0];
            return r.jsx("button",{className:"svm-curvechip","data-on":on?"":void 0,
              "aria-pressed":on,
              title:(sd[0]==="in"?dzT("montage.audio.courbe_entree",{courbe:SVM_FADE_CURVE_TT[o[0]]}):dzT("montage.audio.courbe_sortie",{courbe:SVM_FADE_CURVE_TT[o[0]]})),
              onClick:function(){if(on)return;
                var patch={};patch[ck]=o[0];
                svmSetClipAudio(selRef.current,patch)},
              children:o[1]},o[0])})]},sd[0])}),
      isMus?r.jsx("div",{className:"svm-transnone",children:dzT("montage.audio.musique_bouclee")}):null,
      /* vitesse + rack d'effets — servis par la couche DzSfx (atempo + chaîne
         ffmpeg au rendu) ; couche absente : l'inspecteur reste celui d'avant */
      dzsfx?r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",children:dzT("montage.commun.vitesse")}),
        r.jsx("input",{className:"svm-range",type:"range",min:.5,max:2,step:.05,value:spdv,
          title:dzT("montage.audio.vitesse_aide",{v:spdv.toFixed(2)}),
          "aria-label":dzT("montage.audio.vitesse_aria"),
          onChange:function(e){
            svmSetClipAudio(selRef.current,{speed:Math.round(Number(e.target.value)*100)/100})}}),
        r.jsx("button",{className:"svm-minibtn svm-spdreset","data-off":spdv===1?"":void 0,
          title:spdv===1?dzT("montage.audio.vitesse_origine"):dzT("montage.audio.vitesse_revenir"),
          "aria-label":dzT("montage.audio.vitesse_un"),
          onClick:function(){if(spdv!==1)svmSetClipAudio(selRef.current,{speed:1})},
          children:[__dzGl("dz-action-reinitialiser")," ","×"+spdv.toFixed(2)]})]}):null,
      dzsfx&&dzsfx.Rack?r.jsxs(r.Fragment,{children:[
        r.jsx(SvmLabel,{style:{margin:"14px 0 0"},children:dzT("montage.commun.effets")}),
        r.jsx(dzsfx.Rack,{fx:sel.fx||[],
          onChange:function(nextFx){
            svmSetClipAudio(selRef.current,{fx:Array.isArray(nextFx)?nextFx:[]})},
          clip:{url:svmSrcUrl(sel.src),srcIn:sel.srcIn||0,len:len,
            gainDb:g,fadeIn:Number(sel.fade_in)||0,
            fadeOut:Number(sel.fade_out)||0,speed:spdv},
          onAudition:sfxAudition},sel.id),
        /* L6 D-25 : « Apprendre le bruit » / « Oublier » sous le rack — plage I/O du projet ; réponse appliquée au
           clip visé (par son id) sur sa liste d'effets courante, jetée si la sélection change pendant la mesure */
        r.jsx(DzTracks.NoiseLearn,{clip:sel,range:proj.range,demo:!!proj.demo,music:isMus,onNote:fireNote,
          onFx:function(id,f){var k=clipsRef.current.find(function(q){return q.id===id});
            if(k)svmSetClipAudio(id,{fx:f(Array.isArray(k.fx)?k.fx:[])})}},sel.id)]}):null]})}

  /* ── tiroir « Narration » — la narration s'écrit et se re-prend PAR LE
     TEXTE, un bloc par clip A1. Honnêteté : aucune transcription automatique
     n'existe — un clip « son du plan » l'affiche ; écrire puis Narrer
     REMPLACE son audio par la voix de synthèse (ElevenLabs, payant, coût
     affiché et confirmé inline à la première utilisation). ── */
  function narrStop(){
    var a=narrAudioRef.current;
    if(a){try{a.pause()}catch(_e){}a.ontimeupdate=null;a.onended=null;
      narrAudioRef.current=null}
    setNarrPlayId(function(p){return p?"":p})}
  function narrListen(c){
    if(narrPlayId===c.id){narrStop();return}
    narrStop();stopAudition(); /* l'écoute rendue du rack se tait aussi */
    if(!c.src)return;
    if(playingRef.current)setPlaying(!1); /* jamais deux flux à la fois */
    var a=new Audio(svmSrcUrl(c.src));narrAudioRef.current=a;
    var s0=c.srcIn||0,s1=s0+Math.max(.1,c.end-c.start);
    try{a.currentTime=s0}catch(_e){}
    a.ontimeupdate=function(){if(a.currentTime>=s1-.02)narrStop()};
    a.onended=function(){narrStop()};
    setNarrPlayId(c.id);
    a.play().catch(function(){narrStop();
      fireNote(dzT("montage.commun.lecture_bloquee"))})}
  /* texte d'un bloc — champ client posé sur le clip, une entrée d'historique
     par rafale de 600 ms (motif transition / mixage). Il ne part jamais au
     RENDU, mais il part à la SAUVEGARDE (A) : la frappe arme l'autosave
     (setDirty) — un texte écrit survit au rechargement. */
  function narrSetText(id,v){
    var now=Date.now();
    if(now-narrHistAt.current>600)pushHistory();
    narrHistAt.current=now;
    if(narrErr&&narrErr.id===id)setNarrErr(null);
    setClips(clipsRef.current.map(function(k){
      if(k.id!==id)return k;
      var nk=Object.assign({},k);
      if(v)nk.text=v;else delete nk.text;
      return nk}));
    setDirty(!0)}
  /* succès de synthèse : le clip reçoit src={audio}, sa fin suit la durée
     réelle mesurée — ripple actif : les clips A1 suivants sont décalés du
     delta ; sinon la fin est bornée au voisin A1 et au projet */
  function narrApply(id,fn,dsec){
    var cs=clipsRef.current,cur=null,i;
    for(i=0;i<cs.length;i++){if(cs[i].id===id){cur=cs[i];break}}
    if(!cur){fireNote(dzT("montage.narration.clip_disparu",{fichier:fn}));return}
    pushHistory();
    var d=durRef.current,oldEnd=cur.end,known=dsec>.05;
    var len=known?Math.max(.2,Math.round(dsec*100)/100):cur.end-cur.start;
    var newEnd=cur.start+len,delta=newEnd-oldEnd;
    var doRip=rippleRef.current&&known&&Math.abs(delta)>.01;
    if(!doRip){ /* clamp aux voisins : ni sur le clip A1 suivant, ni hors projet */
      var nb=null;
      cs.forEach(function(k){
        if(k.tr==="a1"&&k.id!==id&&k.start>=oldEnd-.001&&(nb==null||k.start<nb))nb=k.start});
      var lim=nb==null?d:Math.min(d,nb);
      if(newEnd>lim)newEnd=Math.max(cur.start+.2,lim)}
    setClips(cs.map(function(k){
      if(k.id===id){
        var nk=Object.assign({},k,{src:{audio:fn},srcIn:0,end:newEnd,narrDone:!0});
        if(nk.narr&&nk.label==="bloc narration")nk.label=fn.replace(/\.mp3$/,"");
        return nk}
      if(doRip&&k.tr==="a1"&&k.id!==id&&k.start>=oldEnd-.001){
        var ns=k.start+delta,ne=k.end+delta;
        if(ns<0){ne-=ns;ns=0}
        return Object.assign({},k,{start:ns,end:ne})}
      return k}));
    setSelId(id);setDirty(!0);
    fireNote(known?dzT("montage.narration.narre",{d:svmShort(len)})+(doRip?dzT("montage.narration.ripple"):"")
      :dzT("montage.narration.duree_non_mesuree"))}
  function narrDo(id){
    var cs=clipsRef.current,c=null,i;
    for(i=0;i<cs.length;i++){if(cs[i].id===id){c=cs[i];break}}
    if(!c)return;
    var txt=(c.text||"").trim();if(!txt)return;
    setNarrErr(null);setNarrBusy(id);
    var body={script:txt,language:"fr",name:(proj.name||"montage")+"_narr"};
    if(narrVoices&&narrVoices.enabled&&narrVoice)body.voice_id=narrVoice;
    fetch("/api/audio/voiceover",{method:"POST",
      headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
      .then(function(res){return res.json().catch(function(){return {}})
        .then(function(d){return {ok:res.ok,d:d}})})
      .then(function(o){
        if(!o.ok||!o.d||!o.d.filename)
          throw new Error((o.d&&(o.d.detail||o.d.error))||dzT("montage.narration.echec_synthese"));
        /* compteur de session (B) — incrémenté au SUCCÈS, au tarif affiché
           et pour les caractères réellement envoyés */
        setNarrSpent(function(s2){
          return {n:s2.n+1,usd:s2.usd+txt.length*(narrRate||3e-5)}});
        var fn=o.d.filename;
        return svmAudioDur(o.d.url||("/api/audio/"+encodeURIComponent(fn)))
          .then(function(ds){narrApply(id,fn,ds);setNarrBusy("")})})
      .catch(function(e){setNarrBusy("");
        setNarrErr({id:id,msg:String(e&&e.message||e)})})}
  function narrClick(c){
    if(proj.demo){fireNote(dzT("montage.narration.demo"));return}
    if(trackStRef.current.a1&&trackStRef.current.a1.l){
      fireNote(dzT("montage.narration.a1_verrou_narrer"));return}
    if(narrBusy)return;
    if(!(c.text&&c.text.trim()))return;
    if(!narrConfirmRef.current){setNarrArm(c.id);return}
    narrDo(c.id)}
  function narrAddBlock(){
    if(proj.demo){fireNote(dzT("montage.narration.blocs_demo"));return}
    if(trackStRef.current.a1&&trackStRef.current.a1.l){
      fireNote(dzT("montage.narration.a1_verrou_ajouter"));return}
    var d=durRef.current,cs=clipsRef.current,last=0;
    cs.forEach(function(k){if(k.tr==="a1"&&k.end>last)last=k.end});
    var st=Math.min(last,Math.max(0,d-.5)),en=Math.min(d,st+4);
    if(en-st<.5){fireNote(dzT("montage.narration.plus_de_place"));return}
    ovSeq.current++;
    var id="a1n"+ovSeq.current+"_"+Math.round(st*10);
    pushHistory();
    setClips(cs.concat([{tr:"a1",id:id,label:"bloc narration",start:st,end:en,narr:!0}]));
    setSelId(id);setDirty(!0);
    fireNote(dzT("montage.narration.bloc_ajoute",{t:svmShort(st)}))}
  function narrBlock(c,i){
    var isSel=selId===c.id,isAct=narrActive===c.id;
    var isPlan=!!(c.src&&c.src.job_id);
    var hasText=!!(c.text&&c.text.trim());
    var busy=narrBusy===c.id,arm=narrArm===c.id;
    var err=narrErr&&narrErr.id===c.id?narrErr.msg:null;
    var off=!hasText||!!narrBusy;
    /* coût AVANT génération (B) — caractères réellement facturés (le script
       part trimé) × tarif effectif ; le forfait « ~$0.08 » historique est
       mort : bouton, ligne et confirmation portent le montant du BLOC */
    var nChars=(c.text||"").trim().length;
    var nCost=nChars*(narrRate||3e-5);
    var costTxt="~"+svmUsd(nCost);
    var desyncN=c.src&&c.src.job_id?v1SpeedJobs[c.src.job_id]:void 0;
    var tt=busy?dzT("montage.narration.synthese_en_cours"):
      !hasText?dzT("montage.narration.ecrire_dabord"):
      isPlan?dzT("montage.narration.remplace_plan",{cout:costTxt}):
      c.narrDone?dzT("montage.narration.resynth",{cout:costTxt}):
      c.src?dzT("montage.narration.remplace_son",{cout:costTxt}):
      dzT("montage.narration.synth",{cout:costTxt});
    return r.jsxs("div",{className:"svm-nb","data-nbid":c.id,
      "data-sel":isSel?"":void 0,"data-on":isAct?"":void 0,
      "data-ph":c.src?void 0:"",
      title:dzT("montage.narration.caler_tete"),
      onClick:function(){setSelId(c.id);seekTo(c.start)},
      children:[
      r.jsxs("div",{className:"svm-nbhead",children:[
        r.jsx("span",{className:"svm-nbnum",children:svmPad2(i+1)}),
        r.jsx("span",{className:"svm-nbtc",title:dzT("montage.narration.debut_bloc"),children:svmTcFF(c.start)}),
        desyncN?r.jsx("span",{className:"svm-desync",
          title:dzT("montage.narration.desync_aide",{pct:desyncN}),
          children:dzT("montage.narration.desync")}):null,
        r.jsx("span",{className:"svm-nbdur",title:dzT("montage.narration.duree_bloc"),children:svmShort(c.end-c.start)})]}),
      r.jsxs("div",{className:"svm-nblabel",children:[c.label,
        c.src&&!hasText?r.jsx("span",{className:"svm-nbplanhint",
          children:isPlan?dzT("montage.narration.son_plan"):dzT("montage.narration.son_importe")}):null]}),
      r.jsx("textarea",{className:"svm-nbtext",rows:2,value:c.text||"",
        placeholder:dzT("montage.narration.texte_placeholder"),
        "aria-label":dzT("montage.narration.texte_aria")+(i+1),
        title:c.src&&!hasText?dzT("montage.narration.texte_aide"):void 0,
        ref:narrTaGrow,
        onClick:function(e){e.stopPropagation()},
        onChange:function(e){narrSetText(c.id,e.target.value);narrTaGrow(e.target)}}),
      /* ligne de coût (B) — mono discrète, recalculée au même rendu que la
         frappe (dérivée pure de c.text : aucun travail différé à throttler) */
      hasText?r.jsx("div",{className:"svm-nbcost",
        title:(nChars>1?dzT("montage.narration.estimation.plusieurs",{n:nChars,tarif:String(Math.round((narrRate||3e-5)*1e7)/1e7)}):
          dzT("montage.narration.estimation.un",{n:nChars,tarif:String(Math.round((narrRate||3e-5)*1e7)/1e7)}))+
          (narrRate===null?dzT("montage.narration.tarif_chargement"):""),
        children:dzT("montage.narration.cout_ligne",{n:nChars,cout:costTxt})}):null,
      err?r.jsx("div",{className:"svm-note svm-nberr",children:dzT("montage.commun.echec_deux_points")+err}):null,
      arm?r.jsxs("div",{className:"svm-narrconfirm",onClick:function(e){e.stopPropagation()},children:[
        r.jsx("span",{children:dzT("montage.narration.confirmer",{cout:costTxt})}),
        r.jsx("button",{className:"svm-nbgold",
          onClick:function(e){e.stopPropagation();narrConfirmRef.current=1;setNarrArm("");narrDo(c.id)},
          children:dzT("montage.commun.oui")}),
        r.jsx("button",{className:"svm-minibtn",
          title:dzT("montage.narration.annuler_aide"),
          onClick:function(e){e.stopPropagation();setNarrArm("")},children:dzT("montage.commun.non")})]}):
      r.jsxs("div",{className:"svm-nbrow",children:[
        r.jsx("button",{className:"svm-nbgold","data-off":off?"":void 0,title:tt,
          onClick:function(e){e.stopPropagation();if(!off)narrClick(c)},
          children:busy?dzT("montage.narration.synthese_courte"):c.narrDone?dzT("montage.narration.renarrer"):dzT("montage.narration.narrer")}),
        r.jsx("button",{className:"svm-minibtn svm-nbplay",
          "data-on":narrPlayId===c.id?"":void 0,"data-off":c.src?void 0:"",
          title:c.src?(narrPlayId===c.id?"Pause":dzT("montage.narration.ecouter_aide")):dzT("montage.narration.rien_a_ecouter"),
          "aria-label":dzT("montage.narration.ecouter_aria")+(i+1),
          onClick:function(e){e.stopPropagation();if(c.src)narrListen(c)},
          children:narrPlayId===c.id?__dzGl("dz-media-pause"):__dzGl("dz-media-lecture")}),
        r.jsx("button",{className:"svm-minibtn svm-nbdel",
          title:dzT("montage.narration.supprimer_aide"),
          "aria-label":dzT("montage.narration.supprimer_aria")+(i+1),
          onClick:function(e){e.stopPropagation();
            if(narrPlayId===c.id)narrStop();
            delClipById(c.id)},
          children:__dzGl("dz-action-supprimer")})]})]},c.id)}
  function narrPanel(){
    if(!narrOn)return null;
    var blocks=clips.filter(function(c){return c.tr==="a1"}).slice()
      .sort(function(a,b){return a.start-b.start});
    var vlist=(narrVoices&&narrVoices.list)||[];
    var cloned=vlist.filter(function(v){return v.cloned}),
        others=vlist.filter(function(v){return !v.cloned});
    function opt(v){return r.jsx("option",{value:v.id,children:v.name},v.id)}
    return r.jsxs("aside",{className:"svm-narr",ref:narrRef,children:[
      r.jsxs("div",{className:"svm-narrhead",children:[
        r.jsx(SvmLabel,{children:dzT("montage.narration.titre")}),
        /* dépense de session (B) — cumul des synthèses RÉUSSIES, au tarif
           affiché ; absent tant que rien n'a été généré */
        narrSpent.n?r.jsx("span",{className:"svm-narrspent",
          title:(narrSpent.n>1?
            dzT("montage.narration.depense_aide.plusieurs",{n:narrSpent.n}):
            dzT("montage.narration.depense_aide.un",{n:narrSpent.n})),
          children:(narrSpent.n>1?dzT("montage.narration.depense.plusieurs",{n:narrSpent.n,usd:svmUsd(narrSpent.usd)}):
            dzT("montage.narration.depense.un",{n:narrSpent.n,usd:svmUsd(narrSpent.usd)}))}):null,
        r.jsx("span",{className:"svm-narrcount",children:(blocks.length>1?dzT("montage.narration.compte.plusieurs",{n:blocks.length}):dzT("montage.narration.compte.un",{n:blocks.length}))})]}),
      r.jsxs("div",{className:"svm-narrvoice",children:[
        r.jsx("span",{className:"svm-nbvlbl",children:dzT("montage.commun.voix")}),
        narrVoices===null?
          r.jsx("span",{className:"svm-note",style:{marginTop:0,flex:"1 1 auto"},children:dzT("montage.narration.chargement_voix")}):
          r.jsxs("select",{className:"svm-secbtn svm-narrsel",value:narrVoice,
            title:dzT("montage.narration.voix_aide"),
            "aria-label":dzT("montage.narration.voix_aria"),
            onChange:function(e){var v=e.target.value;setNarrVoice(v);
              try{localStorage.setItem("dz_narr_voice",v)}catch(_e){}},
            children:[
              cloned.length?r.jsx("optgroup",{label:dzT("montage.narration.voix_clonees"),children:cloned.map(opt)},"gcl"):null,
              others.length?r.jsx("optgroup",{label:narrVoices.enabled?dzT("montage.narration.catalogue"):dzT("montage.narration.voix_demo"),
                children:others.map(opt)},"gcat"):null]})]}),
      narrVoices&&!narrVoices.enabled?r.jsx("div",{className:"svm-note",style:{marginTop:7},
        children:dzT("montage.narration.voix_demo_note")}):null,
      r.jsx("div",{className:"svm-narrlist",children:
        blocks.length?blocks.map(function(c,i){return narrBlock(c,i)}):
        r.jsx("div",{className:"svm-transnone",style:{marginTop:0},
          children:dzT("montage.narration.aucun_bloc")})}),
      r.jsx("button",{className:"svm-narradd",
        title:dzT("montage.narration.ajouter_aide"),
        onClick:narrAddBlock,children:dzT("montage.narration.ajouter")}),
      r.jsx("div",{className:"svm-note",style:{marginTop:8},
        children:dzT("montage.narration.texte_local")})]})}

  return r.jsxs("div",{className:"dzsvm svm-col",ref:rootRef,"data-view":view,"data-svm-theme":theme==="light"?"light":void 0,children:[
    /* barre de titre */
    r.jsxs("div",{className:"svm-titlebar",children:[
      r.jsx("button",{className:"svm-secbtn svm-menubtn",title:dzT("montage.titre.menu_aide"),"aria-haspopup":"menu","aria-expanded":!!(dzMenu&&dzMenu.kind==="main"),onClick:function(e){if(dzMenu&&dzMenu.kind==="main"){setDzMenu(null);return}var b=e.currentTarget.getBoundingClientRect();setDzMenu(dzMenuProps("main",{x:b.left,y:b.bottom+4}))},children:__dzGl("dz-action-menu")}),
      r.jsx("span",{className:"svm-title",children:"Montage"}),
      r.jsx("span",{className:"svm-projmeta",children:proj.name+" · "+proj.version+" · "+svmRuler(Math.round(dur))}),
      /* réinitialisation depuis la Bibliothèque (A) — confirmation INLINE :
         la sauvegarde est écrasée, jamais silencieusement */
      libArm?
        r.jsxs("span",{className:"svm-libconfirm",children:[
          r.jsx("span",{children:dzT("montage.titre.ecraser_confirm")}),
          r.jsx("button",{className:"svm-minibtn",title:dzT("montage.titre.ecraser_oui_aide"),onClick:svmLibReset,children:dzT("montage.commun.oui_minuscule")}),
          r.jsx("button",{className:"svm-minibtn svm-kbno",
            title:dzT("montage.titre.garder_sauvegarde"),
            onClick:function(){setLibArm(!1)},children:dzT("montage.commun.non_minuscule")})]}):
        r.jsx("button",{className:"svm-secbtn svm-libbtn",disabled:proj.demo,
          title:proj.demo?dzT("montage.titre.reinit_demo"):dzT("montage.titre.reinit_aide"),
          onClick:function(){setLibArm(!0)},children:dzT("montage.titre.bibliotheque")}),
      /* badge d'état de sauvegarde (A) — démo : l'historique « NON
         ENREGISTRÉ » permanent ; projet réel : édition en attente →
         autosave 1,5 s → « enregistré · HH:MM:SS », échec → rouge discret */
      proj.demo?(dirty?r.jsx("span",{className:"svm-unsaved",children:dzT("montage.titre.non_enregistre")}):null):
      saveInfo&&saveInfo.ok===!1?r.jsx("span",{className:"svm-unsaved svm-saveerr",
        title:dzT("montage.titre.sauvegarde_echec_aide"),
        children:dzT("montage.titre.sauvegarde_impossible")}):
      dirty?r.jsx("span",{className:"svm-unsaved",
        title:dzT("montage.titre.en_attente_aide"),
        children:dzT("montage.titre.non_enregistre")}):
      saveInfo&&saveInfo.ok?r.jsx("span",{className:"svm-savedchip",
        title:dzT("montage.titre.sauvegardee_aide"),
        children:dzT("montage.sauvegarde.enregistre",{heure:svmClockHMS(saveInfo.at)})}):null,
      r.jsxs("div",{style:{marginLeft:"auto",display:"flex",gap:8,alignItems:"center"},children:[
        /* Format : les 4 valeurs réellement rendues par _CANVAS côté backend.
           4:5 y a été ajouté — il était proposé ailleurs dans l'app mais
           retombait silencieusement en 9:16 au rendu. */
        r.jsx("select",{className:"svm-secbtn",value:proj.ratio||"9:16",
          title:dzT("montage.titre.format_sortie"),
          onChange:function(e){var v=e.target.value;
            setProj(function(p){return Object.assign({},p,{ratio:v})});
            setDirty(!0);fireNote(dzT("montage.titre.format_note",{v:v}))},
          children:SVM_RATIOS.map(function(rt){
            return r.jsx("option",{value:rt[0],children:rt[1]},rt[0])})}),
        r.jsx("button",{className:"svm-secbtn",title:dzT("montage.titre.preview_aide"),onClick:function(){setPop(pop==="preview"?"":"preview")},children:"Preview"}),
        r.jsx("button",{className:"svm-goldbtn",title:dzT("montage.titre.rendre_aide"),onClick:function(){setPop(pop==="render"?"":"render")},children:__dzGlT("dz-media-rendre",dzT("montage.titre.rendre"),"→")}),
        /* E-5 : « Publier » = le dernier rendu FINAL de ce projet (mémoire par projet), sinon grisé */
        r.jsx("button",{className:"svm-secbtn svm-pubbtn",disabled:!dzLast,title:dzLast?dzT("montage.titre.publier_aide"):dzT("montage.titre.publier_vide"),
          onClick:function(){if(dzLast){setPop("");setDzFin(Object.assign({project_id:proj.project_id||""},dzLast))}},children:dzT("montage.commun.publier")}),
        /* E-2 : tiroir Médias — les rendus vidéo terminés, paginés, avec chips de
           provenance ; quatrième tiroir de .svm-mid, exclusif avec les trois autres */
        r.jsx("button",{className:"svm-themechip svm-medchip","data-on":medOn?"":void 0,
          "aria-pressed":medOn,
          title:dzT("montage.titre.medias_aide"),
          onClick:function(){if(proj.demo){fireNote(dzT("montage.commun.ajout_demo"));return}setMedTr("");setMedOn(!medOn);setSfxOn(!1);setSubsOn(!1);setNarrOn(!1)},children:dzT("montage.titre.medias")}),
        /* E-8 : l'inspecteur a bascule — REPLI dans R_EB2 (l'ancre de « sons » est
           consommee par EB2) ; la poignee et la memoire vivent dans EB6a/EB6b */
        r.jsx("button",{className:"svm-themechip svm-inspchip","data-on":inspOn?"":void 0,
          "aria-pressed":inspOn,
          title:dzT("montage.titre.inspecteur_aide"),
          onClick:function(){setInspSt(function(s){var n={on:!s.on,w:s.w};try{localStorage.setItem("dz_svm_insp",JSON.stringify(n))}catch(_e){}return n})},children:dzT("montage.titre.inspecteur")}),
        /* E-9 : durées sur les clips — REPLI dans R_EB2 (même ancre consommée qu'E-8) */
        r.jsx("button",{className:"svm-themechip svm-durchip","data-on":showDur?"":void 0,
          "aria-pressed":showDur,
          title:dzT("montage.titre.durees_aide"),
          onClick:function(){setShowDur(function(v){var n=!v;try{localStorage.setItem("dz_svm_showdur",n?"1":"0")}catch(_e){}return n})},children:dzT("montage.titre.durees")}),
        /* tiroir Sons (DzSfx) — chip jumelle de « narration », les deux tiroirs
           sont exclusifs ; sans la couche DzSfx la chip n'existe pas */
        svmSfx()?r.jsx("button",{className:"svm-themechip svm-sfxchip","data-on":sfxOn?"":void 0,
          "aria-pressed":sfxOn,
          title:dzT("montage.titre.sons_aide",{k:svmKeyLabel("sounds_drawer")}),
          onClick:sfxToggle,children:dzT("montage.titre.sons")}):null,
        r.jsx("button",{className:"svm-themechip svm-narrchip","data-on":narrOn?"":void 0,
          "aria-pressed":narrOn,
          title:dzT("montage.titre.narration_aide",{k:svmKeyLabel("narration")}),
          onClick:narrToggle,children:"narration"}),
        /* L6 D-26 : la puce ● voix off — enregistre au micro pendant la lecture ; la prise est posée sur la piste de
           dialogue à l'instant où elle a commencé, en mode « écraser » forcé, puis la tête va à sa fin */
        r.jsx(DzTracks.VoiceRec,{demo:!!proj.demo,ctl:dzVoRef,combo:svmKeyLabel("vo_record"),onNote:fireNote,
          onStart:function(){var t=Math.max(0,Number(phRef.current)||0),p=dzProjRef.current;setSpd(1);setPlaying(!0);
            return {t0:t,pj:DzTracks.voIdent(p)}},
          onStop:function(){setPlaying(!1)},
          onDone:function(f,d,t0,pj){var pc=dzProjRef.current;
            if(!DzTracks.voMeme(pj,pc)){fireNote(dzT("montage.voix.prise_projet_change",{f:f}));return}
            var ts=dzTracksRef.current||svmTracksOf(proj),tr=DzTracks.dialogueTrack(ts);
            if(!tr){fireNote(dzT("montage.voix.prise_sans_dialogue",{f:f}));return}
            if(trackStRef.current[tr]&&trackStRef.current[tr].l){fireNote(dzT("montage.voix.prise_piste_verrou",{piste:tr.toUpperCase(),f:f}));return}
            var m0=dzModeRef.current,rp=dzmReplaceRef.current,q0=ovSeq.current;dzModeRef.current="ecraser";dzmReplaceRef.current=null;
            try{addAsset({audio:f},DzTracks.voLabel(DzTracks.voCount(clipsRef.current||[])),"audio",d,tr,t0)}
            finally{dzModeRef.current=m0;dzmReplaceRef.current=rp}
            if(ovSeq.current!==q0)seekTo(t0+d)}}),
        r.jsx(SvmThemeChip,{theme:theme,setTheme:setTheme})]})]}),
    popover(),
    dzFin?r.jsx(DzTracks.FinBandeau,{fin:dzFin,memo:(function(){try{return JSON.parse(localStorage.getItem("dz_montage_channels")||"null")}catch(_e){return null}})(),
      onSend:function(f){try{localStorage.setItem("dz_montage_channels",JSON.stringify(f.channels))}catch(_e){}
        return fetch("/api/montage/publish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(f)})
          .then(function(res){return res.ok?res.json():res.json().catch(function(){return null}).then(function(j){throw (j&&j.detail)||res.status})})
          .then(function(d){var id=d&&d.post&&d.post.id;if(id)window.dispatchEvent(new CustomEvent("deepotus:select-post",{detail:{id:id}}))})},
      onLib:function(){window.dispatchEvent(new CustomEvent("deepotus:navigate",{detail:{view:"library"}}))},
      onClose:function(){setDzFin(null)}}):null,
    fxPicker(),
    ovPicker(),
    dzMkOn?r.jsx(DzTracks.MarkerIndex,{markers:proj.markers,onSeek:seekTo,
      onClose:function(){setDzMkOn(!1)},
      onRemove:function(id){pushHistory();setProj(function(p){return Object.assign({},p,{markers:DzTracks.markerRemove(p.markers,id)})});setDirty(!0)},
      onChange:function(id,patch){pushHistory();setProj(function(p){return Object.assign({},p,{markers:DzTracks.markerUpdate(p.markers,id,patch)})});setDirty(!0)}}):null,
    transPopover(),
    (pop||dzFin||dzMenu)?r.jsx("div",{className:"svm-modescrim",onClick:function(){setPop("");setDzFin(null);setDzMenu(null)}}):null,
    dzMenu?r.jsx(DzTracks.CtxMenu,Object.assign({onClose:function(){setDzMenu(null)}},dzMenu)):null,
    dzLb?r.jsx(DzTracks.Lightbox,{clips:clips,onPick:function(c){dzLbPick(c.id)},onClose:function(){setDzLb(!1)}}):null,
    kbPanel(),
    /* tiroir sons + tiroir narration + lecteur + inspecteur */
    r.jsxs("div",{className:"svm-mid",children:[
      /* E-7 : le panneau Livraison (le composant Deliver de la couche) -- memes gestes que la barre de titre (Preview / Rendre / Publier = R_EA5D),
         historique dzJobs (EC6), « Voir dans la Bibliothèque » = le chemin du bandeau de fin */
      view==="livraison"?r.jsx(DzTracks.Deliver,{nom:proj.name,onPreview:function(){setPop("preview")},onRender:function(){setPop("render")},onPublish:function(){if(dzLast){setPop("");setDzFin(Object.assign({project_id:proj.project_id||""},dzLast))}},publishOn:!!dzLast,lastFin:dzLast,jobs:dzJobs,onOpenLib:function(){window.dispatchEvent(new CustomEvent("deepotus:navigate",{detail:{view:"library"}}))}}):null,
      /* tiroir Sons (DzSfx.Drawer) — même emplacement que Narration, les deux
         exclusifs ; l'insertion passe par addAsset (playhead / piste du type) */
      (function(){var d2=svmSfx();
        return d2&&d2.Drawer?r.jsx(d2.Drawer,{open:sfxOn,
          onClose:function(){setSfxOn(!1)},
          onInsert:sfxInsert,playheadSec:ph,defaultTab:"sfx"}):null})(),
      /* tiroir Sous-titres (DzSubs.Drawer) — même emplacement que Sons et
         Narration, les trois exclusifs */
      subsPanel(),
      narrPanel(),
      /* E-2 : tiroir Médias (rendus vidéo) — même emplacement, exclusif */
      r.jsx(DzTracks.MediaDrawer,{open:medOn,trId:medTr,exts:null,onClose:function(){setMedOn(!1)},dragPayload:dragPayload,
        onAdd:function(j){addAsset({job_id:j.job_id},j.title||j.job_id,"video",j.duration_s||0,medTr||"v1")},
        /* L7-B D-41 : le projet créé par les auto-clips est ouvert par la liste des projets (compteur) */
        onOpenProject:function(p){setDzAcOpen(function(v){return {n:((v&&v.n)||0)+1,id:p&&p.id,name:p&&p.name}})}}),
      r.jsxs("div",{className:"svm-playerzone",
        /* formats portrait : la barre du lecteur passe dans la zone latérale
           morte (colonne à droite), le cadre garde toute la hauteur */
        "data-side":svmRatioW(proj.ratio)<1?"":void 0,children:[
        note?r.jsx("div",{className:"svm-note",style:{position:"absolute",top:58,left:18,zIndex:5},children:note}):null,
        r.jsx("div",{className:"svm-stage",children:
        r.jsxs("div",{className:"svm-frame",ref:frameRef,
          /* le cadre suit le format du projet et remplit la hauteur disponible
             (plus de cap 420px) — --svm-arw sert au calcul CSS
             min(hauteur dispo, largeur dispo / ratio) */
          style:{aspectRatio:String(proj.ratio||"9:16").replace(":","/"),
                 "--svm-arw":String(svmRatioW(proj.ratio))},
          title:dzT("montage.lecteur.cadre_aide"),
          /* dépôt sur le viewport : vise la piste vidéo principale, à la
             tête de lecture (le viewport n'a pas d'axe temporel). */
          onDragOver:function(e){if(svmDragOk(e,"v1")){e.preventDefault();e.dataTransfer.dropEffect="copy"}},
          onDrop:function(e){dropOnTrack(e,"v1",null)},
          onWheel:function(e){
            e.preventDefault();
            setVzoom(function(z){
              var n=z*(e.deltaY<0?1.12:1/1.12);
              return n<1?1:n>6?6:n;   /* borné : en deçà de 1 le cadre se viderait */
            });
          },
          onDoubleClick:function(){setVzoom(1)},
          children:[
          previewUrl?r.jsx("video",{ref:videoRef,src:previewUrl,playsInline:!0,
            style:{position:"absolute",inset:0,width:"100%",height:"100%",objectFit:"cover",
                   transform:"scale("+vzoom+")",transformOrigin:"center center"},
            onEnded:function(){setPlaying(!1)}}):null,
          /* lecteur vivant : les sources elles-mêmes avant tout rendu —
             couches remplies impérativement par liveSync (pool par source) */
          liveOn?r.jsx("div",{className:"svm-live",ref:liveHostRef,
            style:{transform:"scale("+vzoom+")",transformOrigin:"center center"}}):null,
          /* retours L6 (26/09) : l'image etalonnee du plan V1 sous la tete, a l'arret -- sous les overlays V2 */
          liveOn?r.jsx(DzTracks.GradeLive,{clips:clips,head:ph,playing:playing,vzoom:vzoom,ratio:proj.ratio,dlv:dzDel,dapi:dzApi}):null,
          liveOn?r.jsx("div",{className:"svm-liveov",ref:liveOvRef,
            style:{transform:"scale("+vzoom+")",transformOrigin:"center center"}}):null,
          /* D-21 — L'APERÇU VIVANT DU CARTON. Vide, et écrit
             impérativement par `liveSync` à chaque frame. POSÉ
             AVANT LE VOILE : au rendu, les titres sont gravés
             APRÈS les `xfade`, donc un fondu passe par-dessus le
             titre — et pas par-dessus les sous-titres. */
          liveOn?r.jsx("div",{className:"svm-livetitle",ref:dzTtHostRef,"aria-hidden":!0}):null,
          /* D-12 — LE VOILE DES FONDUS EN DIRECT. Vide, transparent au
             repos, et écrit impérativement par `liveSync` (couleur +
             opacité) à chaque frame : le lecteur vivant n'a qu'un
             hôte, donc pas de crossfade A/B — un voile dit OÙ tombe
             la transition et COMBIEN elle dure. */
          liveOn?r.jsx("i",{className:"svm-xfveil",ref:dzVeilRef,"aria-hidden":!0}):null,
          liveOn&&!liveClip?r.jsx("div",{className:"svm-livegap",children:dzT("montage.lecteur.trou")}):null,
          /* cadre de sélection des overlays : boîte + 8 poignées (échelle) +
             rotation, guides d'alignement et badge de geste — positionnés
             impérativement (tfSyncBox / ovGesture), hors échelle vzoom */
          liveOn?r.jsxs("div",{className:"svm-tf",children:[
            r.jsx("i",{className:"svm-tfguide","data-ax":"v",ref:tfGuideVRef}),
            r.jsx("i",{className:"svm-tfguide","data-ax":"h",ref:tfGuideHRef}),
            r.jsx("div",{className:"svm-tfbox",ref:tfBoxRef,children:
              ["nw","n","ne","e","se","s","sw","w"].map(function(hp){
                return r.jsx("i",{className:"svm-tfh","data-p":hp,
                  title:dzT("montage.lecteur.echelle_aide"),
                  onPointerDown:function(e2){ovHandleDown(e2,"scale")}},hp)})
              .concat([
                r.jsx("i",{className:"svm-tfstem","aria-hidden":!0},"stem"),
                r.jsx("i",{className:"svm-tfrot",
                  title:dzT("montage.lecteur.rotation_aide"),
                  onPointerDown:function(e2){ovHandleDown(e2,"rotate")}},"rot")])}),
            r.jsx("div",{className:"svm-tfbadge",ref:tfBadgeRef}),
            /* L5 D-30 : le contour du masque du clip V1 selectionne (sous les rectangles du zoom) */
            sel&&sel.tr==="v1"&&sel.mask?r.jsx(DzTracks.MaskBox,{clip:sel}):null,
            /* D-13 : les deux fenetres du zoom dynamique du clip V1 selectionne */
            sel&&sel.tr==="v1"&&sel.dz?r.jsx(DzTracks.DzRects,{dz:sel.dz,
              onChange:function(nd){dzPlanSet({dz:nd})}}):null]}):null,
          /* zones sûres (G) : tiers + centre + marges verticales 9:16 */
          safeOn?r.jsxs("div",{className:"svm-safe","aria-hidden":!0,children:[
            r.jsx("div",{className:"svm-safe3v",style:{left:"33.333%"}}),
            r.jsx("div",{className:"svm-safe3v",style:{left:"66.667%"}}),
            r.jsx("div",{className:"svm-safe3h",style:{top:"33.333%"}}),
            r.jsx("div",{className:"svm-safe3h",style:{top:"66.667%"}}),
            r.jsx("div",{className:"svm-safectr"}),
            proj.ratio==="9:16"?r.jsx("div",{className:"svm-safebox"}):null]}):null,
          vzoom>1.01?r.jsx("div",{className:"svm-frametc",
            children:"×"+vzoom.toFixed(1)}):null,
          /* sous-titres du projet, mot actif surligné pendant la lecture */
          subsOverlay(),
          /* légende de la maquette : elle s'efface dès qu'une vraie piste S1
             existe, ou pendant le placement — deux textes empilés au même
             endroit ne veulent rien dire */
          subsSegsOf(clips).length||subsOn?null
          :r.jsx("div",{className:"svm-caption",children:
            r.jsx("div",{className:"svm-captiontext",children:proj.demo?dzT("montage.lecteur.legende_demo"):proj.name})}),
          /* timecode image-exact — coin haut droit, seul overlay UI permanent */
          r.jsx("div",{className:"svm-frametc svm-frametr",children:svmTcFF(ph)})]})}),
        /* barre du lecteur — TOUJOURS visible (plus de boutons au survol) :
           qualité source/480p, ratio du canvas, zones sûres, plein écran */
        r.jsxs("div",{className:"svm-playerbar",role:"group","aria-label":dzT("montage.lecteur.controles"),children:[
          r.jsx("button",{className:"svm-pchip","data-on":previewUrl?void 0:"",
            title:previewUrl?dzT("montage.lecteur.revenir_direct")
              :dzT("montage.lecteur.direct_aide"),
            onClick:function(){if(previewUrl)setPreviewUrl(null)},children:"source"}),
          r.jsx("button",{className:"svm-pchip","data-on":previewUrl?"":void 0,
            "data-off":!previewUrl&&!prevSaved?"":void 0,
            title:previewUrl?dzT("montage.lecteur.apercu_branche")
              :prevSaved?dzT("montage.lecteur.rebrancher")
              :dzT("montage.lecteur.lancer_preview"),
            onClick:function(){if(previewUrl)return;
              if(prevSaved)setPreviewUrl(prevSaved);
              else setPop(pop==="preview"?"":"preview")},children:"480p"}),
          r.jsx("i",{className:"svm-pdiv","aria-hidden":!0}),
          r.jsx("span",{className:"svm-pchip svm-pinfo",
            title:dzT("montage.lecteur.ratio_aide"),
            children:proj.ratio||"9:16"}),
          r.jsx("i",{className:"svm-pdiv","aria-hidden":!0}),
          r.jsx("button",{className:"svm-pchip","data-on":safeOn?"":void 0,
            "aria-pressed":safeOn,title:dzT("montage.lecteur.zones_aide"),
            onClick:function(){setSafeOn(!safeOn)},children:dzT("montage.lecteur.zones_sures",{k:svmKeyLabel("safezones")})}),
          r.jsx("button",{className:"svm-pchip",title:dzT("montage.lecteur.plein_ecran_aide"),
            onClick:svmFullscreen,children:dzT("montage.lecteur.plein_ecran",{k:svmKeyLabel("fullscreen")})}),
          /* L5 D-31 : la puce des scopes du plan V1 sous la tête (bascule mémorisée, encart dans le cadre) */
          r.jsx(DzTracks.Scopes,{clips:clips,head:ph,playing:playing,ratio:proj.ratio,dlv:dzDel,dapi:dzApi})]})]}),
      inspOn?r.jsxs("aside",{className:"svm-insp",style:{width:inspW},"data-w":inspW,children:[r.jsx("div",{className:"svm-insphandle",onPointerDown:inspDown,title:dzT("montage.inspecteur.poignee")}),
        r.jsx("div",{className:"svm-insphead",title:dzT("montage.inspecteur.tete_aide"),children:DzTracks.teteTxt(ph,sel,svmTcFF)}),
        r.jsx(SvmLabel,{children:dzT("montage.inspecteur.clip_selectionne")}),
        r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:8,marginTop:9},children:[
          r.jsx("div",{className:"svm-clipname",style:{marginTop:0,flex:"1 1 auto",minWidth:0,
            whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"},children:sel?sel.label:"—"}),
          sel?r.jsx("button",{className:"svm-minibtn",title:dzT("montage.inspecteur.supprimer_clip",{k:svmKeyLabel("delete")}),
            "aria-label":dzT("montage.inspecteur.supprimer_nom",{nom:sel.label}),onClick:delClip,children:__dzGl("dz-action-supprimer")}):null]}),
        (function(){
          /* Out affiché = durée de SOURCE consommée : à vitesse ×s (audio
             atempo comme V1) le clip lit s fois plus de source */
          var selSpd=sel?svmSpeedOf(sel):1;
          var outT=sel?(sel.srcOut!=null?sel.srcOut:(sel.end-sel.start)*selSpd):null;
          var rows=[
            {k:"In",v:sel?svmShort(sel.srcIn!=null?sel.srcIn:0):"—",t:sel?(sel.srcIn!=null?sel.srcIn:0):null},
            {k:"Out",v:sel?svmShort(outT):"—",t:outT}];
          /* vitesse ÉDITABLE (C) : clips V1 réels (rendu vidéo) seulement —
             partout ailleurs la valeur reste une lecture (facteur atempo des
             clips audio, chaîne de la maquette démo) */
          var v1spd=!!(sel&&trackKind(sel.tr)==="video"&&sel.src&&sel.src.job_id);   /* t117 : toute piste vidéo */
          if(!v1spd)rows.push({k:dzT("montage.commun.vitesse"),
            v:sel&&sel.speed?(typeof sel.speed==="number"?Math.round(sel.speed*100)+" %":sel.speed):"100 %",t:null});
          var kids=rows.map(function(p2){return r.jsxs("div",{className:"svm-prop",
            /* équivalent image-exact au survol — la valeur affichée reste une durée */
            title:p2.t==null?void 0:dzT("montage.inspecteur.equiv_images",{tc:svmTcFF(p2.t),n:Math.round(p2.t*30)}),
            children:[
            r.jsx("div",{className:"svm-propk",children:p2.k}),
            r.jsx("div",{className:"svm-propv",children:p2.v})]},p2.k)});
          if(v1spd){
            var pct=Math.round(selSpd*100);
            var opts=[25,50,75,100,150,200,300,400];
            if(opts.indexOf(pct)<0)opts=opts.concat([pct]).sort(function(a,b){return a-b});
            kids.push(r.jsxs("div",{className:"svm-prop",children:[
              r.jsx("div",{className:"svm-propk",children:dzT("montage.commun.vitesse")}),
              r.jsx("select",{className:"svm-vitsel",value:String(pct),
                title:dzT("montage.inspecteur.vitesse_aide"),
                "aria-label":dzT("montage.inspecteur.vitesse_label"),
                onChange:function(e){svmSetV1Speed(selRef.current,Number(e.target.value)/100)},
                children:opts.map(function(p3){
                  return r.jsx("option",{value:String(p3),children:p3+" %"},p3)})})]},"Vitesse"))}
          /* In / Out / Vitesse : une fenêtre de source, ça ne veut rien dire
             pour une ligne de texte — la section « Sous-titre » prend le relais */
          return sel&&(trackKind(sel.tr)==="subs"||trackKind(sel.tr)==="title")?null
            :r.jsx("div",{className:"svm-props",children:kids})})(),
        subsInspector(),
        /* P6 — le remplacement de source, posé ENTRE la fenêtre
           « In / Out » qu'il recale et l'inspecteur de transition
           qu'il conserve : les garanties du geste encadrent son
           bouton. Voir le commentaire d'ancre dans le patcher. */
        DzTracks.replaceBtn(sel,function(){dzReplaceArm(sel)}),
        DzTracks.revertBtn(sel,function(){
          /* LE MÊME VERROU QUE M15 : ce geste réécrit `src`,
             `label`, `srcIn` ET `end` — donc le bord droit du
             clip sur la timeline. Sans cette garde, « Revenir à
             la version précédente » était le SEUL des gestes
             destructifs de cet écran à passer outre une piste
             verrouillée, alors que M15 refuse de remplacer et
             M16src refuse même d'ARMER. */
          if(trackStRef.current[sel.tr]&&trackStRef.current[sel.tr].l){
            fireNote(dzT("montage.inspecteur.revert_verrou",{piste:sel.tr.toUpperCase()}));return}
          var rv=DzTracks.revertSrc(sel);if(!rv)return;
          pushHistory();
          setClips(clipsRef.current.map(function(k){
            return k.id===sel.id?rv.clip:k}));
          setDirty(!0);fireNote(rv.note)}),
        r.jsx(DzTracks.NewerHint,{jobId:sel&&sel.src&&sel.src.job_id,
          /* SECOND SITE D'ARMEMENT, écrit COMME LE PREMIER : la
             ref ET son miroir, avec le libellé. Il pourrait s'en
             passer AUJOURD'HUI — `addAsset` est appelé dans le
             MÊME gestionnaire, donc aucun rendu ne s'intercale et
             M15 éteint le miroir avant qu'il ne s'affiche ; les
             deux écritures d'état sont regroupées par React et
             n'aboutissent à rien. C'est écrit quand même parce que
             cette sûreté-là tient à UNE propriété du site appelant
             (sa synchronie), que rien n'oblige à durer : le jour où
             ce gestionnaire attendrait quoi que ce soit avant
             d'appeler `addAsset`, le mode serait armé et le
             sélecteur, rouvert, se dirait encore « Ajouter sur la
             piste V1 » — la faute exacte que M15b ferme. « La ref
             et son miroir s'arment ensemble » devient ainsi une
             règle STRUCTURELLE des deux sites, et le banc compte
             les deux ensemble (`les_deux_sites_arment_la_ref_ET_le
             _miroir`) : ils ne peuvent plus se désolidariser en
             silence. */
          onPick:function(c){dzmReplaceRef.current={id:sel.id,
            tr:sel.tr,label:sel.label};
            setDzmArm({tr:sel.tr,label:sel.label});
            addAsset({job_id:c.job_id},c.title||c.job_id,"video",
              Number(c.duration_s)||0,sel.tr)}},"dzmnew"),
        /* P12 — « Extraire le son → A1 » : le son d'un plan DÉJÀ posé,
           même moteur que l'ajout (sonde, cache, jumeau, refus DIT).
           Posé juste avant l'inspecteur de transition, pour tout clip
           vidéo porteur d'une source — V1, V2, V3. */
        DzTracks.extractBtn(sel,{tracks:dzTracksRef.current||svmTracksOf(proj),
          clips:function(){return clipsRef.current||[]},
          locked:function(t){return !!(trackStRef.current[t]&&trackStRef.current[t].l)},
          pushHistory:pushHistory,setClips:setClips,setDirty:setDirty,
          note:fireNote}),
        transInspector(),
        sel&&trackKind(sel.tr)==="title"?r.jsx(DzTracks.TitleInspector,{clip:sel,
          gabarits:dzTitles&&dzTitles.gabarits,
          fonts:dzTitles&&dzTitles.fonts,colors:dzTitles&&dzTitles.colors,nonce:dzTtNonce,
          onChange:function(id,p){
            var cs=DzTracks.titleUpdate(clipsRef.current,id,p);
            if(cs===clipsRef.current){
              if(p&&typeof p.text==="string"&&!p.text.trim()){
                fireNote(dzT("montage.carton.sans_texte"));
                setDzTtNonce(function(dzK){return dzK+1})}
              return}
            var dzTtN=Date.now();
            if(p.size==null){pushHistory();dzTtHistAt.current=0}
            else{if(dzTtN-dzTtHistAt.current>600)pushHistory();
              dzTtHistAt.current=dzTtN}
            setClips(cs);setDirty(!0)}}):null,
        /* P3 — les coupes sont appliquées de la FIN vers le DÉBUT :
           une coupe tardive ne décale pas les précédentes, donc les
           plages restent justes sans être recalculées entre deux. Un
           SEUL pushHistory pour le lot : « annuler » défait le geste,
           pas ses dix-sept morceaux. */
        r.jsx(DzTracks.TextDrawer,{open:dzTextOn,clips:clips,note:fireNote,
          onCut:function(rg,al){
            if(!rg||!rg.length)return;
            var rs=rg.slice().sort(function(u,v){return v[0]-u[0]});
            var dzO=DzTracks.cutOpts(proj,trackSt);
            pushHistory();
            /* les mots calés du tiroir, recollés sur LEUR clip : sans
               eux, fendre un bloc de narration laisserait la phrase
               entière sur les deux moitiés. */
            var cs=DzTracks.withWords(clipsRef.current||[],al),rm=0;
            rs.forEach(function(p){
              var res=DzTracks.rippleCut(cs,p[0],p[1],dzO);
              cs=res.clips;rm+=res.removed});
            rm=Math.round(rm*1000)/1000;
            /* les mots prêtés ne servaient qu'à répartir le texte :
               les garder gonflerait la sauvegarde d'une copie de
               toute la narration, que rien ne relit. */
            setClips(DzTracks.dropWords(cs,svmTracksOf(proj)
              .filter(function(t){return t.kind==="subs"})
              .map(function(t){return t.id})));
            setDirty(!0);
            var vk=Object.keys(dzO.locked);
            fireNote((rs.length>1?dzT("montage.texte.coupes_plusieurs",{n:rs.length,s:rm.toFixed(2)}):dzT("montage.texte.coupes_un",{n:rs.length,s:rm.toFixed(2)}))+(vk.length?dzT("montage.texte.pistes_verrouillees",{pistes:vk.join(", ").toUpperCase()}):""))}}),
        /* D-13 : les proprietes de plan (clip V1 reel seulement) */
        sel&&sel.tr==="v1"&&sel.src&&sel.src.job_id?r.jsx(DzTracks.PlanProps,{clip:sel,
          u:sel.end>sel.start?Math.max(0,Math.min(1,(ph-sel.start)/(sel.end-sel.start))):0,
          speed:svmSpeedOf(sel),head:ph,
          onRampe:function(t,sL,sR){var tl=trackStRef.current.v1;if(tl&&tl.l){fireNote(dzT("montage.plan.v1_verrou_division"));return}
            var res=DzTracks.rampe(clipsRef.current,selRef.current,t,sL,sR);
            if(res.refus){fireNote(res.refus==="bord"?dzT("montage.plan.trop_pres_bord"):dzT("montage.plan.division_impossible"));return}
            pushHistory();setClips(res.clips);setSelId(res.right);setDirty(!0)},
          stabJob:dzStabJobs[DzTracks.srcKey(sel.src)]||null,onStab:function(){dzStabStart(sel.src)},
          ratio:svmRatioW(proj.ratio),srcWH:(function(){var pl=livePoolRef.current,it=pl&&pl.get(livePoolKey(sel.src,"b"));
            return it?[it.el.videoWidth||it.el.naturalWidth||0,it.el.videoHeight||it.el.naturalHeight||0]:[0,0]})(),
          onReframe:function(){var id=sel.id,c=clipsRef.current.find(function(k){return k.id===id});
            if(!c||!c.src||!c.src.job_id){fireNote(dzT("montage.recadrage.reserve"));return Promise.resolve()}
            function dzRfSg(k){return [Number(k.srcIn)||0,svmSpeedOf(k),Number(k.start)||0,Number(k.end)||0,svmSrcKey(k.src),
              k.reframe&&typeof k.reframe==="object"?String(k.reframe.mode):""].join("|")}
            var sg=dzRfSg(c),du=Math.round(Math.max(0,(c.end-c.start)*svmSpeedOf(c))*1e3)/1e3;
            if(!(du>0)){fireNote(dzT("montage.recadrage.duree_nulle"));return Promise.resolve()}
            fireNote(dzT("montage.recadrage.en_cours"));
            return fetch("/api/montage/reframe",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({src:c.src,srcIn:Number(c.srcIn)||0,dur:du})})
              .then(function(res){return res.json().catch(function(){return {}}).then(function(j){
                if(!res.ok)throw new Error((j&&typeof j.detail==="string"&&j.detail)||("HTTP "+res.status));return j})})
              .then(function(j){var k2=clipsRef.current.find(function(k){return k.id===id});
                if(!k2){fireNote(dzT("montage.recadrage.disparu"));return}
                if(dzRfSg(k2)!==sg){fireNote(dzT("montage.recadrage.change"));return}
                var tl=trackStRef.current.v1;if(tl&&tl.l){fireNote(dzT("montage.recadrage.v1_verrou"));return}
                var si=Number(c.srcIn)||0,pts=(j&&j.mode==="suivi"&&Array.isArray(j.points)?j.points:[])
                  .map(function(q){return {t:Math.round((si+Number(q.t))*1e3)/1e3,x:q.x}});
                pushHistory();setClips(clipsRef.current.map(function(k){if(k.id!==id)return k;var nk=Object.assign({},k);
                  if(pts.length)nk.reframe={mode:"suivi",points:pts};else delete nk.reframe;return nk}));setDirty(!0);
                fireNote(pts.length?dzT("montage.recadrage.suivi",{n:pts.length}):dzT("montage.recadrage.peu"))})
              .catch(function(e){fireNote(dzT("montage.recadrage.refus",{raison:(e&&e.message)||dzT("montage.commun.erreur_reseau")}))})},
          onChange:dzPlanSet}):null,
        ovInspector(),
        /* L5 : le panneau Etalonnage (clip V1 reel seulement, meme garde que les proprietes de plan) */
        sel&&sel.tr==="v1"&&sel.src&&sel.src.job_id?r.jsx(DzTracks.GradePanel,{clip:sel,
          clips:clips,head:ph,playing:playing,locked:!!(trackStRef.current.v1&&trackStRef.current.v1.l),onNote:fireNote,onChange:dzPlanSet}):null,
        audioInspector(),
        r.jsxs("div",{style:{display:"flex",alignItems:"center",margin:"20px 0 10px"},children:[
          r.jsx(SvmLabel,{children:dzT("montage.commun.mixage")}),
          /* vu-mètre GRADUÉ de la rangée MIXAGE — pendant la lecture d'un
             vrai flux, TOUJOURS (le DzSfx.Meter transport garde les
             chiffres ; cette barre donne l'échelle au plus près des
             faders — verdict du juge mixage) : ticks −30/−20/−10/−6/−3
             dBFS, zone rouge > −3, crête à retombée lente */
          playing&&!proj.demo?r.jsx("canvas",{className:"svm-vu",ref:vuRef,role:"img",
            title:dzT("montage.mixage.vu_aide"),
            "aria-label":dzT("montage.mixage.vu_label")}):null]}),
        r.jsx("div",{className:"svm-mix",children:mixRows.map(function(m){
          return r.jsxs("div",{children:[
            r.jsxs("div",{className:"svm-mixhead",children:[
              r.jsx("span",{style:{color:"var("+m.c+")"},children:m.name}),
              r.jsx("span",{"data-off":m.dbNum<=-40?"":void 0,
                children:m.dbNum<=-40?dzT("montage.commun.muet"):m.db})]}),
            r.jsx("div",{className:"svm-mixrail",role:"slider",tabIndex:0,
              title:dzT("montage.mixage.rail_aide",{nom:m.name,db:m.db}),
              "aria-label":dzT("montage.mixage.rail_label",{nom:m.name}),"aria-valuemin":-40,"aria-valuemax":0,
              "aria-valuenow":m.dbNum,"aria-valuetext":m.dbNum<=-40?dzT("montage.commun.muet"):m.db,
              onPointerDown:function(e){mixDown(e,m.name)},
              onKeyDown:function(e){
                var d=e.key==="ArrowLeft"||e.key==="ArrowDown"?-1:
                      e.key==="ArrowRight"||e.key==="ArrowUp"?1:0;
                if(!d)return;e.preventDefault();pushHistory();svmMixSet(m.name,m.dbNum+d)},
              children:
              r.jsx("div",{className:"svm-mixfill",style:{width:m.w+"%",background:"var("+m.c+")"}})})]},m.name)})}),
        /* graduations du mixage — micro-labels alignés sur les ticks des rails
           (échelle visuelle de la maquette : −30/−20/−10 dB à 16,8/50,8/84,8 %) ;
           les extrémités physiques du rail ne valent PAS −40/0, les étiqueter
           ainsi mentirait */
        r.jsx("div",{className:"svm-mixscale","aria-hidden":!0,children:
          [[-30,16.8],[-20,50.8],[-10,84.8]].map(function(g2){
            return r.jsx("span",{style:{left:g2[1]+"%"},children:"−"+Math.abs(g2[0])},g2[0])})}),
        r.jsxs("button",{className:"svm-durmaster",style:{marginTop:12},
          onClick:function(){setDucking(!ducking);setDirty(!0)},
          role:"switch","aria-checked":ducking,children:[
          r.jsx("span",{className:"svm-switch","data-off":ducking?void 0:"",children:r.jsx("span",{className:"svm-knob"})}),
          r.jsxs("div",{children:[
            r.jsx("div",{className:"svm-dmtitle",children:dzT("montage.mixage.ducking")}),
            r.jsx("div",{className:"svm-dmhint",children:dzT("montage.mixage.ducking_aide")})]})]}),
        /* réglages du ducking — résumé toujours lisible + panneau presets /
           enveloppe ; « défaut » ne s'affiche que si un réglage est posé */
        r.jsxs("div",{className:"svm-duckrow",children:[
          r.jsx("span",{className:"svm-duckcur",
            title:proj.ducking?dzT("montage.mixage.duck_perso"):dzT("montage.mixage.duck_defaut"),
            children:(function(){var dk=duckCfg();
              return "ratio "+dk.ratio+":1 · "+Math.round(dk.attack_ms)+"/"+Math.round(dk.release_ms)+" ms"})()}),
          proj.ducking?r.jsx("button",{className:"svm-minibtn svm-duckbtn",
            title:dzT("montage.mixage.duck_revenir"),
            onClick:resetDuck,children:dzT("montage.mixage.defaut")}):null,
          r.jsx("button",{className:"svm-minibtn svm-duckbtn","data-on":duckOpen?"":void 0,
            "aria-expanded":duckOpen,
            title:dzT("montage.mixage.duck_regler"),
            onClick:function(){setDuckOpen(!duckOpen)},children:duckOpen?dzT("montage.mixage.fermer"):dzT("montage.mixage.reglages")})]}),
        duckOpen?duckPanel():null,
        r.jsxs("button",{className:"svm-durmaster",onClick:function(){setDurMaster(!durMaster);setDirty(!0)},
          role:"switch","aria-checked":durMaster,children:[
          r.jsx("span",{className:"svm-switch","data-off":durMaster?void 0:"",children:r.jsx("span",{className:"svm-knob"})}),
          r.jsxs("div",{children:[
            r.jsx("div",{className:"svm-dmtitle",children:dzT("montage.mixage.maitre_duree")}),
            r.jsx("div",{className:"svm-dmhint",children:dzT("montage.mixage.maitre_duree_aide")})]})]}),
        (sel&&(trackKind(sel.tr)==="subs"||trackKind(sel.tr)==="title")?null:vfxStackSection()),
        /* P4 — le geste GLOBAL de l'étalonnage : les quatre valeurs
           du plan sélectionné recopiées sur tous les autres plans
           réels de SA piste (pas « v1 » en dur : un plan V2 peut
           porter un grade_basic). RÉVERSIBLE : un seul pushHistory
           pour le lot ; « annuler » rend à chaque plan son
           étalonnage d'avant — déduit de trois faits mesurés, mais
           rien ne l'EXERCE (undo est un hook du composant). */
        DzTracks.gradeAllBtn(sel,clips,setClips,pushHistory,setDirty,fireNote)]}):null]}),
    /* timeline */
    r.jsx("div",{className:"svm-tlhandle",onPointerDown:tlDown,title:dzT("montage.timeline.hauteur_aide")}),
    r.jsxs("div",{className:"svm-tl","data-h":tlH||void 0,style:tlH?{height:tlH}:void 0,children:[
      r.jsxs("div",{className:"svm-trans",children:[
        /* étapes 4 à 7 du handoff « Barre Outils Flottante » :
           l'onglet OUTILS et la barre flottante, câblée sur les
           actions de l'écran. Les deux nœuds sont absolus, donc
           hors du flux flex de ce bandeau : rien n'y bouge. */
        r.jsx(DzTracks.ToolDock,{tracks:svmTracksOf(proj),onTracks:svmTracksSet,onPick:openPicker,wordAnim:(proj.subsStyle||{}).wordAnim||"couleur",onWordAnim:function(v){subsStyleSet({wordAnim:v})},textOn:dzTextOn,onText:function(){setDzTextOn(!dzTextOn)},emojiSegs:subsSegsOf(clips),note:fireNote,onEmojiAdd:dzEmoAdd,docked:dzTbDock,toggleReq:dzTbReq,keyLbl:svmKeyLabel("toolbar"),onProjets:function(){setDzProjReq(function(n){return n+1})}}),
        r.jsxs("span",{className:"svm-tcmain",title:dzT("montage.transport.tc_aide"),children:[
          svmTcFF(ph),r.jsx("span",{className:"svm-tctotal",children:" / "+svmTcFF(dur)})]}),
        playing&&spd!==1?r.jsx("span",{className:"svm-spdchip",
          title:dzT("montage.transport.vitesse_aide"),
          children:spd<0?[__dzGl("dz-media-vitesse")," ×"+Math.abs(spd)]:"×"+Math.abs(spd)}):null,
        /* badge SOLO — visible dès qu'un solo d'écoute est actif */
        (function(){var sks=Object.keys(solo).filter(function(kk){return solo[kk]});
          return sks.length?r.jsx("span",{className:"svm-solochip",
            title:dzT("montage.solo.badge_aide",{pistes:sks.map(function(s3){return s3.toUpperCase()}).join(" + ")})+(previewUrl?dzT("montage.solo.sans_effet_apercu"):""),
            children:"SOLO "+sks.map(function(s3){return s3.toUpperCase()}).join("+")}):null})(),
        r.jsxs("div",{className:"svm-transbtns",children:[
          r.jsx("button",{className:"svm-tbtn",title:dzT("montage.transport.coupe_prec",{k:svmKeyLabel("cut_prev")}),onClick:function(){jump(-1)},children:__dzGl("dz-media-precedent")}),
          r.jsx("button",{className:"svm-tbtn",title:dzT("montage.transport.image_prec",{k:svmKeyLabel("step_back")}),"aria-label":dzT("montage.transport.reculer"),
            onClick:function(){seekTo(Math.max(0,Math.round(phRef.current*30-1)/30))},children:__dzGl("dz-media-image-precedente")}),
          r.jsx("button",{className:"svm-tbtn svm-gold",
            title:playing?dzT("montage.transport.pause",{a:svmKeyLabel("play"),b:svmKeyLabel("jog_pause")})
              :dzT("montage.transport.lecture",{a:svmKeyLabel("play"),b:svmKeyLabel("jog_fwd")}),
            onClick:function(){setSpd(1);setPlaying(!playing)},children:playing?__dzGl("dz-media-pause"):__dzGl("dz-media-lecture")}),
          r.jsx("button",{className:"svm-tbtn",title:dzT("montage.transport.image_suiv",{k:svmKeyLabel("step_fwd")}),"aria-label":dzT("montage.transport.avancer"),
            onClick:function(){seekTo(Math.min(durRef.current,Math.round(phRef.current*30+1)/30))},children:__dzGl("dz-media-image-suivante")}),
          r.jsx("button",{className:"svm-tbtn",title:dzT("montage.transport.coupe_suiv",{k:svmKeyLabel("cut_next")}),onClick:function(){jump(1)},children:__dzGl("dz-media-suivant")})]}),
        r.jsxs("div",{className:"svm-transbtns",children:[
          r.jsx("button",{className:"svm-tbtn",title:dzT("montage.transport.annuler_aide",{k:svmKeyLabel("undo")}),"aria-label":dzT("montage.transport.annuler"),
            "data-off":histRef.current.u.length?void 0:"",onClick:undo,children:__dzGl("dz-action-annuler")}),
          r.jsx("button",{className:"svm-tbtn",title:dzT("montage.transport.retablir_aide",{k:svmKeyLabel("redo")}),"aria-label":dzT("montage.transport.retablir"),
            "data-off":histRef.current.r.length?void 0:"",onClick:redo,children:__dzGl("dz-action-retablir")})]}),
        r.jsxs("div",{className:"svm-toolchips",children:[
          /* étape 8 du handoff « Barre Outils Flottante » (§4.5) : les
             trois `aria-label`. Sous largeur réduite ces chips passent
             en glyphe seul (`font-size:0` + `::before`) ; sans nom
             explicite, leur nom accessible y porterait le caractère de
             dessin et dépendrait du moteur. Il reprend le texte
             visible, combo vivante comprise. */
          r.jsx("button",{className:"svm-toolchip","data-on":snap?"":void 0,
            "aria-label":dzT("montage.outils.aimanter"),
            title:dzT("montage.outils.aimanter_aide",{k:svmKeyLabel("snap")}),onClick:function(){setSnap(!snap)},children:dzT("montage.outils.aimanter")}),
          /* la chip AFFICHE la combo vivante — un remappage se lit ici aussi */
          r.jsx("button",{className:"svm-toolchip","aria-label":dzT("montage.outils.lame",{k:svmKeyLabel("blade")}),title:dzT("montage.outils.lame_aide",{k:svmKeyLabel("blade")}),onClick:blade,children:dzT("montage.outils.lame",{k:svmKeyLabel("blade")})}),
          r.jsx("button",{className:"svm-toolchip","data-on":ripple?"":void 0,
            "aria-label":"ripple",
            title:dzT("montage.outils.ripple_aide",{k:svmKeyLabel("ripple")}),onClick:function(){setRipple(!ripple)},children:"ripple"}),
          r.jsx("button",{className:"svm-toolchip","data-on":dzMkOn?"":void 0,
            "aria-label":dzT("montage.outils.marqueurs"),
            title:dzT("montage.outils.marqueurs_aide",{a:svmKeyLabel("marker_index"),b:svmKeyLabel("marker_toggle")}),onClick:function(){dzMkToggle()},children:__dzGlT("dz-media-marqueur",("◆ "+((proj.markers||[]).length)),"◆")}),
          r.jsx("button",{className:"svm-toolchip","aria-label":dzT("montage.outils.titre"),title:dzT("montage.outils.titre_aide",{k:svmKeyLabel("title_add")}),onClick:function(){dzTtAdd()},children:__dzGl("dz-media-titre")}),
          r.jsx("button",{className:"svm-toolchip","aria-label":dzT("montage.outils.ajustement"),title:dzT("montage.outils.ajustement_aide",{k:svmKeyLabel("adjust_add")}),onClick:function(){dzAjAdd()},children:__dzGl("dz-calque-reglage")}),
          /* sous-titres : la chip dit combien de lignes porte la piste et
             combien sont SIGNALÉES — les deux chiffres sortent du verdict,
             donc ils valent exactement ceux du badge d'onglet du tiroir et
             ceux des pastilles de la timeline. Le compteur comptait autrefois
             autre chose que le badge voisin : deux nombres pour la même
             notion, jamais d'accord. */
          (function(){
            if(!subsLayer())return null;
            var vd=subsVd(),C=vd.counts,cv=vd.cov||{connu:!1,complet:!0};
            var pl=function(n,u,p){return n+" "+(Math.abs(n)<2?u:(p||u+"s"))};
            /* même précision que le tiroir : les deux termes de la division
               doivent redonner le pourcentage affiché */
            var f1=function(v){
              return (Math.round(v*10)/10).toFixed(1).replace(".",",")};
            return r.jsxs("button",{className:"svm-toolchip","data-on":subsOn?"":void 0,
              "aria-pressed":subsOn,
              title:dzT("montage.sous_titres.chip_aide",{etat:C.repliques
                  ?dzT("montage.sous_titres.chip_compte",{repliques:pl(C.repliques,dzT("montage.sous_titres.replique"),dzT("montage.sous_titres.repliques")),signalees:pl(C.signalees,dzT("montage.sous_titres.signalee"),dzT("montage.sous_titres.signalees")),bloquantes:pl(C.bloquantes,dzT("montage.sous_titres.bloquante"),dzT("montage.sous_titres.bloquantes"))})+
                   (cv.connu
                     ?dzT("montage.sous_titres.chip_couverture",{pct:cv.pct})+
                      (C.plans_sans?dzT("montage.sous_titres.plans_sans",{plans:pl(C.plans_sans,dzT("montage.sous_titres.plan"),dzT("montage.sous_titres.plans"))}):"")
                     :"")
                  :dzT("montage.sous_titres.piste_vide")}),
              onClick:subsToggle,children:[
              dzT("montage.commun.sous_titres"),
              C.repliques?r.jsx("span",{className:"sub-chipn",
                title:dzT("montage.sous_titres.sur_piste",{repliques:pl(C.repliques,dzT("montage.sous_titres.replique"),dzT("montage.sous_titres.repliques"))}),
                children:String(C.repliques)},"n"):null,
              /* ambre, toujours : le rouge ne sert qu'à ce qui EST bloquant
                 (la pastille du segment fautif sur la piste, juste dessous) */
              C.signalees?r.jsx("span",{className:"sub-chipbad","data-sev":"warn",
                title:dzT("montage.sous_titres.signalees_dont",{repliques:pl(C.signalees,dzT("montage.sous_titres.replique"),dzT("montage.sous_titres.repliques")),bloquantes:pl(C.bloquantes,dzT("montage.sous_titres.bloquante"),dzT("montage.sous_titres.bloquantes"))}),
                children:String(C.signalees)},"b"):null,
              /* LA COUVERTURE, visible sans ouvrir le tiroir : un montage
                 sous-titré sur son premier cinquième ne doit pas pouvoir
                 partir au rendu sans qu'un seul écran l'ait dit. Le « % »
                 porte son unité ; le détail, plan par plan, est dans le
                 tiroir, et la piste S1 juste dessous le montre à l'œil. */
              cv.connu&&!cv.complet
                ?r.jsx("span",{className:"sub-chipcov","data-sev":"warn",
                  /* les DEUX termes de la division, à la précision affichée
                     dans le tiroir : « 14 s sur 69 s » ne redonnait pas
                     « 21 % », donc le chiffre de la chip semblait sorti de
                     nulle part dès qu'on tentait de le refaire. */
                  title:dzT("montage.sous_titres.couverture_aide",{couvert:f1(cv.couvert),attendu:f1(cv.attendu),pct:cv.pct})+
                    (C.plans_sans?dzT("montage.sous_titres.plans_sans_virgule",{plans:pl(C.plans_sans,dzT("montage.sous_titres.plan"),dzT("montage.sous_titres.plans"))}):""),
                  children:cv.pct+" %"},"c"):null]})})()]}),
        /* métering maître (DzSfx.Meter) — remplace le canvas .svm-vu ;
           SvmMeterHost isole les rafraîchissements par frame */
        svmSfx()?r.jsx("span",{className:"svm-meterslot",children:
          r.jsx(SvmMeterHost,{srcRef:vuLvlRef,engaged:playing&&!proj.demo,
            lufs:lufs,busy:lufsBusy,onMeasure:doMeasure})}):null,
        r.jsxs("span",{className:"svm-zoom",
          title:dzT("montage.zoom.aide",{plus:svmKeyLabel("zoom_in"),moins:svmKeyLabel("zoom_out"),cent:svmKeyLabel("zoom100")}),
          children:["zoom ",
          ["▁","▂","▃","▅"].map(function(g,i){
            return r.jsx("button",{className:"svm-zoomstep","data-on":Math.round(zoomPct)===SVM_ZOOMW[i]?"":void 0,
              title:dzT("montage.zoom.cran",{pct:SVM_ZOOMW[i]}),onClick:function(){zoomApply(SVM_ZOOMW[i])},children:g},i)}),
          " "+Math.round(zoomPct)+" %"]}),
        /* P10 — la durée du projet CESSE D'ÊTRE UN AFFICHAGE. Elle
           s'allonge et se raccourcit ici, d'une graduation de la
           règle à la fois ; raccourcir sous la fin du dernier clip
           est REFUSÉ, jamais fait en silence. Depuis D-0 (le
           21/09/2026, « H6 », replié ICI) le geste ENTRE dans
           l'historique, une entrée par rafale de 600 ms, et
           chaque note le dit. */
        DzTracks.durCtl({dur:dur,step:tickStep,clips:clips,
          /* D-0 — MÊME FENÊTRE QUE `nudgeHistAt` (M17b) : une
             rafale de clics sur « + » vaut UNE entrée, pas trente. */
          onSet:function(v){var dzN=Date.now();
            if(dzN-dzDurHistAt.current>600)pushHistory();
            dzDurHistAt.current=dzN;
            setProj(function(p){return Object.assign({},p,{dur:v})});setDirty(!0)},
          note:fireNote}),
        /* rappels permanents (R2/I5) — mono 10px discret, masquable par ×
           (dz_hints_off, définitif) ; « B sons » seulement si la couche vit */
        hintsOff?null:r.jsxs("span",{className:"svm-hints",children:[
          r.jsx("span",{className:"svm-hintstxt",children:
            dzT("montage.rappels.texte",{lecture:svmKeyLabel("play"),sons:svmSfx()?dzT("montage.rappels.sons",{k:svmKeyLabel("sounds_drawer")}):"",
            muet:svmKeyLabel("mute"),solo:svmKeyLabel("solo"),
            fondu:svmKeyLabel("fade_in_cycle"),tout:svmKeyLabel("keys_panel")})}),
          r.jsx("button",{className:"svm-hintsx",
            title:dzT("montage.rappels.masquer_aide"),
            "aria-label":dzT("montage.rappels.masquer"),
            onClick:function(){setHintsOff(!0);
              try{localStorage.setItem("dz_hints_off","1")}catch(_e){}},
            children:__dzGl("dz-action-fermer")})]}),
        /* bouton discret du panneau raccourcis — fin de transport */
        r.jsx(DzTracks.Projects,{name:proj.name,projectId:proj.project_id,note:fireNote,
          /* étape 6 (§5.1) : le BOUTON « projets » a quitté le
             bandeau ; la LISTE reste, parce que c’est elle que
             la barre d’outils demande. Montée NUE. */
          nu:!0,
          /* étape 7 : la barre d’outils ouvre CETTE liste-ci au
             lieu d’en monter une seconde — un compteur, pas un
             booléen. */
          openReq:dzProjReq,
          /* L7-B D-41 : ouvrir le projet créé par les auto-clips (compteur) */
          openProj:dzAcOpen,
          payload:function(){return svmSavePayload()},
          onBefore:function(){if(saveAbortRef.current){try{saveAbortRef.current.abort()}catch(_e){}}saveSeqRef.current++;setSaveInfo(null)},
          onFail:function(){if(dirty)svmDoSave(++saveSeqRef.current)},
          onOpen:function(d){return svmApplyProject(d)},
          /* L7 D-39 (24/09/2026, tâche 4) : « ⇄ » d'une ligne — lit l'autre projet, le compare à la timeline
             courante (le diff pur de la couche) et ouvre le popover « diff » ; rien n'est modifié */
          onDiff:function(p){fetch("/api/montage/projects/"+encodeURIComponent(p.id)).then(function(rp){if(!rp.ok)throw new Error("HTTP "+rp.status);return rp.json()}).then(function(d){setDiffSt({diff:DzTracks.diff(clipsRef.current,(d&&d.clips)||[]),nomA:(dzProjRef.current&&dzProjRef.current.name)||"",nomB:p.name||""});setPop("diff")}).catch(function(){fireNote(dzT("montage.projets.illisible"))})},
          onNamed:function(pid,nm){setProj(function(p){return Object.assign({},p,{project_id:pid,name:nm})})}}),
        /* bouton discret du panneau raccourcis — fin de transport */
        r.jsx("button",{className:"svm-tbtn",title:dzT("montage.raccourcis.aide",{k:svmKeyLabel("keys_panel")}),
          "aria-label":dzT("montage.raccourcis.label"),"aria-haspopup":"dialog","aria-expanded":kbOn,
          onClick:function(){setKbOn(!kbOn)},children:__dzGl("dz-action-raccourcis")})]}),
      /* D-7 : mini-carte HORS zoom — un rect par clip, la fenêtre visible ; clic = centrer .svm-scroll
         (la gouttière de 88 px est dans .svm-lanes donc dans scrollWidth : déduite, comme le zoom fait W-88) */
      r.jsx(DzTracks.Minimap,{clips:clips,tracks:svmTracksOf(proj),dur:dur,viewFrac:mmView,onSeek:function(f){var el=tlScrollRef.current;if(!el)return;var w=el.scrollWidth-88;el.scrollLeft=Math.max(0,f*w-(el.clientWidth-88)/2)}}),
      r.jsx("div",{className:"svm-scroll",ref:tlScrollRef,children:
        r.jsxs("div",{className:"svm-lanes",style:{width:zoomPct+"%"},children:[
          r.jsxs("div",{className:"svm-ruler",onPointerDown:rulerDown,
            onPointerMove:rulerHover,onPointerLeave:rulerLeave,children:[
            r.jsx("div",{className:"svm-gutter"}),r.jsx(DzTracks.RangeBar,{range:proj.range,dur:dur}),r.jsx(DzTracks.Markers,{markers:proj.markers,dur:dur,onSeek:seekTo}),
            ticks.map(function(t3){return r.jsx("div",{className:"svm-tick",children:svmRuler(t3)},t3)})]}),
          svmTracksOf(proj).map(function(tr){
            var bus=SVM_TRACK_BUS[tr.id];
            var busDb=bus?Number(proj.mixDb&&proj.mixDb[bus]!=null?proj.mixDb[bus]:SVM_DEMO_MIX[bus]):0;
            var muted=!!bus&&busDb<=-40;
            var locked=!!(trackSt[tr.id]&&trackSt[tr.id].l);
            /* solo d'écoute : piste audio hors du solo → bande atténuée */
            var anySolo=!1,skT;for(skT in solo){if(solo[skT]){anySolo=!0;break}}
            var soloOn=!!solo[tr.id],soloExcl=anySolo&&!!bus&&!soloOn;
            /* en-tête : éléments communs construits une fois — les pistes
               AUDIO (R2/I1+I2) passent en 3 rangées compactes : nom + type
               ENTIER, puis + / M / S / verrou, puis mini-fader de bus 46px
               (même état proj.mixDb que la rangée MIXAGE, drag via mixDown,
               molette ±1 dB via le listener natif du scroller) */
            var thAdd=r.jsx("button",{className:"svm-ovadd",
              title:trackKind(tr.id)==="subs"
                ?dzT("montage.piste.ajout_sous_titre")
                :trackKind(tr.id)==="audio"
                ?dzT("montage.piste.ajout_son")
                :trackKind(tr.id)==="adjust"
                ?dzT("montage.piste.ajout_ajustement")
                :trackKind(tr.id)==="title"
                ?dzT("montage.piste.ajout_carton",{k:svmKeyLabelNow("title_add")})
                :trackKind(tr.id)==="video"
                ?dzT("montage.piste.ajout_video")
                :dzT("montage.piste.ajout_image"),
              onClick:function(e){
                if(trackKind(tr.id)==="subs"){subsAddHere();return}
                if(trackKind(tr.id)==="adjust"){dzAjAdd();return}
                if(trackKind(tr.id)==="title"){dzTtAdd();return}
                if(trackKind(tr.id)==="video"&&!(e&&e.shiftKey)){if(proj.demo){fireNote(dzT("montage.commun.ajout_demo"));return}setMedTr(tr.id);setMedOn(!0);setSfxOn(!1);setSubsOn(!1);setNarrOn(!1);return}
                openPicker(tr.id)},children:__dzGl("dz-action-ajouter")},"add");
            var thType=r.jsx("span",{className:"svm-ttype",title:tr.type,children:tr.type},"type");
            var thM=bus?r.jsx("button",{className:"svm-minibtn svm-tkbtn",
              "data-on":muted?"":void 0,"aria-pressed":muted,
              title:muted?dzT("montage.piste.reactiver",{nom:tr.name,bus:bus})
                :dzT("montage.piste.rendre_muette",{nom:tr.name,bus:bus}),
              onClick:function(){svmTrackMute(tr.id)},children:__dzGl("dz-media-muet")},"m"):null;
            var thS=bus?r.jsx("button",{className:"svm-minibtn svm-tkbtn svm-tksolo",
              "data-on":soloOn?"":void 0,"aria-pressed":soloOn,
              title:soloOn?dzT("montage.piste.solo_retirer",{nom:tr.name,k:svmKeyLabel("solo")})
                :dzT("montage.piste.solo_poser",{nom:tr.name,k:svmKeyLabel("solo")}),
              onClick:function(e){svmTrackSolo(tr.id,e.shiftKey)},children:__dzGl("dz-media-solo")},"s"):null;
            var thLock=r.jsx("button",{className:"svm-minibtn svm-tkbtn",
              "data-on":locked?"":void 0,"aria-pressed":locked,
              title:locked?dzT("montage.piste.deverrouiller",{nom:tr.name})
                :dzT("montage.piste.verrouiller",{nom:tr.name}),
              onClick:function(){svmTrackLock(tr.id)},children:__dzGl("dz-etat-verrouille")},"lk");
            var thFader=bus?r.jsx("div",{className:"svm-thfader",children:
              r.jsx("div",{className:"svm-thmix","data-bus":bus,role:"slider",tabIndex:0,
                title:dzT("montage.piste.bus_aide",{bus:bus,niveau:muted?dzT("montage.commun.muet"):svmBusDbTxt(busDb)}),
                "aria-label":dzT("montage.piste.bus_label",{bus:bus}),
                "aria-orientation":"horizontal",
                "aria-valuemin":-40,"aria-valuemax":0,"aria-valuenow":busDb,
                "aria-valuetext":muted?dzT("montage.commun.muet"):svmBusDbTxt(busDb),
                onPointerDown:function(e){mixDown(e,bus)},
                onKeyDown:function(e){
                  var d3=e.key==="ArrowLeft"||e.key==="ArrowDown"?-1:
                        e.key==="ArrowRight"||e.key==="ArrowUp"?1:0;
                  if(!d3)return;e.preventDefault();e.stopPropagation();
                  pushHistory();svmMixSet(bus,busDb+d3)},
                children:r.jsx("div",{className:"svm-thmixfill",
                  style:{width:svmMixW(busDb)+"%",background:"var("+SVM_MIX_COLORS[bus]+")"}})})},"fd"):null;
            /* L7 D-22 (24/09/2026) : data-sub par genre (S2… aussi), data-burn sur la piste que le rendu grave (s1 sans marque) */
            return r.jsxs("div",{className:"svm-track","data-sub":trackKind(tr.id)==="subs"?"":void 0,"data-burn":trackKind(tr.id)==="subs"&&DzTracks.subsBurnId(svmTracksOf(proj))===tr.id?"":void 0,"data-soloexcl":soloExcl?"":void 0,style:{height:tr.h},children:[
              r.jsxs("div",{className:"svm-thead"+(bus?" svm-thead-a":""),onContextMenu:function(e){e.preventDefault();setDzMenu(dzMenuProps("track",{x:e.clientX,y:e.clientY,id:tr.id}))},children:
                bus?[
                  r.jsxs("div",{className:"svm-tnamerow",children:[
                    r.jsx("span",{className:"svm-sq6",style:{background:"var("+tr.c+")"}}),
                    r.jsx("span",{className:"svm-tname",children:tr.name}),
                    thType]},"nr"),
                  r.jsxs("div",{className:"svm-thbtns",children:[thAdd,thM,thS,thLock]},"br"),
                  DzTracks.headBtns(tr,svmTracksOf(proj),svmTracksSet,clips,setClips,fireNote),
                  thFader]
                :[
                  r.jsxs("div",{className:"svm-tnamerow",children:[
                    r.jsx("span",{className:"svm-sq6",style:{background:"var("+tr.c+")"}}),
                    r.jsx("span",{className:"svm-tname",children:tr.name})]},"nr"),
                  r.jsxs("div",{className:"svm-ttyperow",children:[thType,thLock,thAdd]},"tr"),
                  DzTracks.headBtns(tr,svmTracksOf(proj),svmTracksSet,clips,setClips,fireNote)]}),
              r.jsxs("div",{className:"svm-lane",
                onDragOver:function(e){if(svmDragOk(e,tr.id)){e.preventDefault();e.dataTransfer.dropEffect="copy"}},
                onDrop:function(e){dropOnTrack(e,tr.id,e.currentTarget)},
                onPointerDown:function(e){if(e.button!==0||e.target!==e.currentTarget||proj.demo)return;var rc=e.currentTarget.getBoundingClientRect();var t=(e.clientX-rc.left)/rc.width*durRef.current;var g=DzTracks.trou(clipsRef.current,tr.id,t);setGapSel(g?{tr:tr.id,a:g.a,b:g.b}:null)},
                children:[
                tr.id==="v1"?svmV1Gaps(clips,dur):null,
                gapSel&&gapSel.tr===tr.id?r.jsx("div",{className:"svm-gapsel",style:{left:(gapSel.a/dur*100)+"%",width:((gapSel.b-gapSel.a)/dur*100)+"%"},title:dzT("montage.timeline.trou_aide")}):null,
                clips.filter(function(c){return c.tr===tr.id}).map(function(c){
                  var isSel=c.id===selId;
                  /* fond média : waveform (pistes audio), filmstrip / image (V1) —
                     pointer-events:none, la démo (sans src) reste inchangée */
                  var media=null;
                  if(c.src){
                    if(trackKind(tr.id)==="audio"&&(c.src.audio||c.src.job_id))
                      media=r.jsx(SvmWave,{src:c.src,k:svmSrcKey(c.src),srcIn:c.srcIn||0,
                        /* vitesse ×s : la fenêtre source réellement consommée
                           est s fois plus longue — la waveform reste honnête */
                        len:(c.end-c.start)*(typeof c.speed==="number"&&c.speed>0?c.speed:1),
                        color:tr.c,theme:theme,zoom:zoomPct,dur:dur});
                    else if(tr.id==="v1"&&c.src.job_id)
                      media=r.jsx(SvmFilmstrip,{src:c.src,k:svmSrcKey(c.src),
                        /* vitesse ×s (C) : la fenêtre source AFFICHÉE suit
                           ce que le rendu consomme — durée × vitesse */
                        srcIn:c.srcIn||0,len:(c.end-c.start)*svmSpeedOf(c)});
                    else if(tr.id==="v1"&&c.src.image)
                      media=r.jsx("div",{className:"svm-strip svm-stripbg","aria-hidden":!0,
                        style:{backgroundImage:"url('/api/images/"+encodeURIComponent(c.src.image)+"')"}})}
                  /* mixage par clip : rampes + poignées de fondu (clips audio
                     réels seulement) — masquées si la piste est verrouillée */
                  var aud=trackKind(tr.id)==="audio"&&c.src&&(c.src.audio||c.src.job_id);
                  var fIn=aud?Number(c.fade_in)||0:0,fOut=aud?Number(c.fade_out)||0:0;
                  var clen=Math.max(.01,c.end-c.start);
                  var fiP=Math.min(100,fIn/clen*100),foP=Math.min(100,fOut/clen*100);
                  /* courbe de fondu (R2/I4) : path spécifique si ≠ lin, la
                     <line> historique sinon — clip jamais touché : identique */
                  var fiD=fIn>0?svmFadePath(c.fade_in_curve,!0):null,
                      foD=fOut>0?svmFadePath(c.fade_out_curve,!1):null;
                  var isMus=aud&&tr.id==="a2"&&c.id===firstA2;
                  /* bloc narration pas encore narré : hachures pointillées
                     (motif .svm-target), couleur de la piste */
                  var isPh=!!(c.narr&&!c.src);
                  /* jumeau A1 d'un plan V1 accéléré/ralenti (C) : chip ambre
                     — cet audio ne suivra plus l'image au rendu */
                  var desyncT=tr.id==="a1"&&c.src&&c.src.job_id?
                    v1SpeedJobs[c.src.job_id]:void 0;
                  /* automation de volume (R4) : la ligne reste visible dès
                     qu'un point existe (ce qui part au rendu se voit) ; les
                     losanges ne s'éditent qu'en mode ◇ sur le clip
                     sélectionné, piste déverrouillée */
                  var vpts=aud?svmVpOf(c):null;
                  var vpMode=aud&&autoOn&&isSel&&!locked;
                  return r.jsxs("div",{className:"svm-clip",
                    "data-locked":locked?"":void 0,
                    "data-narr":isPh?"":void 0,
                    "data-media":media&&tr.id==="v1"?"":void 0,
                    "data-kind":c.kind||void 0,
                    "data-boring":boMap[c.id]||void 0,
                    style:{left:c.start/dur*100+"%",width:(c.end-c.start)/dur*100+"%",
                      borderColor:isSel?"var(--accent)":isPh?"var(--stroke2)":"color-mix(in srgb, var("+tr.c+") 53%, transparent)",
                      background:isPh||c.kind==="adjust"?"repeating-linear-gradient(-45deg,transparent 0 5px, color-mix(in srgb, var("+tr.c+") 26%, transparent) 5px 6px)":isSel?"color-mix(in srgb, var(--accent) 20%, transparent)":"color-mix(in srgb, var("+tr.c+") "+tr.mix+"%, transparent)"},
                    /* le problème se voit SUR la timeline. La pastille porte
                       la SÉVÉRITÉ que le verdict a décidée — la même que la
                       pastille de la ligne dans le tiroir, réplique par
                       réplique. Elle ne connaissait que « rouge ou rien » et
                       la peignait d'après un calcul à elle : la piste appelait
                       « critiques » neuf segments que la liste d'à côté
                       rétrogradait en ambre. */
                    "data-cid":tr.id==="s1"?c.id:void 0,
                    "data-warn":tr.id==="s1"?(subsSev(c.id).sev||void 0):void 0,
                    "data-hidden":trackKind(tr.id)==="subs"&&c.hidden?"":void 0, /* L7 D-22 (revue T6) : masqué se voit sur toute piste subs */
                    /* couverture : le plan qui ne porte aucune réplique se
                       marque sur la timeline. « 16 s sous-titrées sur 1:09 »
                       était vrai et invisible — trois plans muets, et pas un
                       pixel pour le dire. */
                    "data-nosub":tr.id==="v1"?(subsCovOf(c.id)==="sans"?""
                      :subsCovOf(c.id)==="ignore"?"off":void 0):void 0,
                    onPointerDown:function(e){clipDown(e,c,e.currentTarget.parentElement)},
                    onContextMenu:function(e){e.preventDefault();e.stopPropagation();setSelId(c.id);setDzMenu(dzMenuProps("clip",{x:e.clientX,y:e.clientY,id:c.id}))},
                    onDoubleClick:vpMode?function(e){vpDblClick(e,c)}:void 0,
                    /* curseur explicite : sans lui, rien n'indique que les
                       bords rognent au lieu de déplacer */
                    onPointerMove:function(e){
                      if(e.buttons)return;
                      var el=e.currentTarget;
                      if(locked){el.style.cursor="";return}
                      el.style.cursor=svmEdgeAt(e.clientX,el.getBoundingClientRect())==="m"?"grab":"col-resize"},
                    title:locked?dzT("montage.clip.verrouille",{nom:c.label})
                      :dzT("montage.clip.aide",{nom:c.label})+
                        (vpMode?dzT("montage.clip.aide_losange"):""),
                    children:[
                      media,
                      /* rampes de fondu — triangles semi-transparents posés
                         PAR-DESSUS la waveform (couleur de piste, alpha .3) */
                      fIn>0?r.jsx("div",{className:"svm-fadeshade","aria-hidden":!0,
                        style:{background:"color-mix(in srgb, var("+tr.c+") 30%, transparent)",
                          clipPath:"polygon(0 0, "+fiP+"% 0, 0 100%)"}}):null,
                      fOut>0?r.jsx("div",{className:"svm-fadeshade","aria-hidden":!0,
                        style:{background:"color-mix(in srgb, var("+tr.c+") 30%, transparent)",
                          clipPath:"polygon("+(100-foP)+"% 0, 100% 0, 100% 100%)"}}):null,
                      /* trait de courbe du fondu — diagonale --accent 1,5 px
                         (épaisseur constante), lisible de loin comme la rampe
                         des NLE pros ; hors clip-path pour ne pas être rognée */
                      fIn>0?r.jsx("svg",{className:"svm-fadeline","aria-hidden":!0,
                        viewBox:"0 0 100 100",preserveAspectRatio:"none",
                        style:{left:0,width:fiP+"%"},children:
                        fiD?r.jsx("path",{d:fiD,vectorEffect:"non-scaling-stroke"})
                          :r.jsx("line",{x1:0,y1:100,x2:100,y2:0,vectorEffect:"non-scaling-stroke"})}):null,
                      fOut>0?r.jsx("svg",{className:"svm-fadeline","aria-hidden":!0,
                        viewBox:"0 0 100 100",preserveAspectRatio:"none",
                        style:{right:0,width:foP+"%"},children:
                        foD?r.jsx("path",{d:foD,vectorEffect:"non-scaling-stroke"})
                          :r.jsx("line",{x1:0,y1:0,x2:100,y2:100,vectorEffect:"non-scaling-stroke"})}):null,
                      /* ligne d'automation (R4) — −40..+12 dB sur la hauteur
                         du clip, couleur de piste pleine, par-dessus la
                         waveform et les rampes, sous le label ; sans points
                         (mode ◇) : plate au niveau du gain */
                      vpMode||vpts?r.jsx("svg",{className:"svm-vpline","aria-hidden":!0,
                        viewBox:"0 0 100 100",preserveAspectRatio:"none",children:
                        r.jsx("polyline",{
                          points:svmVpPolyPts(vpts,clen,Number(c.gain)||0),
                          vectorEffect:"non-scaling-stroke",
                          style:{stroke:"var("+tr.c+")"}})}):null,
                      /* losanges d'automation — mode ◇ seulement : drag t/dB
                         (étiquette flottante), clic droit / Suppr : retrait */
                      vpMode?(vpts||[]).map(function(p,pi){
                        var psel=vpSel&&vpSel.id===c.id&&vpSel.i===pi;
                        return r.jsx("i",{className:"svm-vph","data-sel":psel?"":void 0,
                          title:dzT("montage.clip.losange_aide",{t:svmShort(p.t),db:svmVpDbTxt(p.db),k:svmKeyLabel("delete")}),
                          style:{left:Math.min(100,Math.max(0,p.t/clen*100))+"%",
                            top:svmVpY(p.db)+"%"},
                          onPointerDown:function(ev){vpDown(ev,c,pi)},
                          onContextMenu:function(ev){ev.preventDefault();ev.stopPropagation();
                            svmVpRemove(c.id,pi)}},"vp"+pi)}):null,
                      r.jsx("div",{className:"svm-cliplabel",children:DzTracks.durLbl(c.label,c.start,c.end,showDur)}),
                      /* P9 — signalé AVANT le rendu, pas après son
                         400 : ce plan n'est pas une vidéo. */
                      (c.tr==="v1"&&(proj.v1NonVideo||[]).indexOf(c.id)>=0)?
                        DzTracks.badSrc(c,function(){openPicker(c.tr)}):null,
                      desyncT?r.jsx("span",{className:"svm-desync",
                        title:dzT("montage.clip.desync_aide",{pct:desyncT}),
                        children:dzT("montage.clip.desync")}):null,
                      /* poignées visibles sur le clip sélectionné */
                      isSel?r.jsx("div",{style:{position:"absolute",left:0,top:0,bottom:0,width:4,
                        background:"var(--accent)",borderRadius:"3px 0 0 3px",pointerEvents:"none"}}):null,
                      isSel?r.jsx("div",{style:{position:"absolute",right:0,top:0,bottom:0,width:4,
                        background:"var(--accent)",borderRadius:"0 3px 3px 0",pointerEvents:"none"}}):null,
                      /* poignées de fondu — coins supérieurs, drag vers
                         l'intérieur ; sur la musique A2 bouclée la droite
                         règle le fondu de FIN DE RENDU */
                      aud&&!locked?r.jsx("i",{className:"svm-fadeh",
                        title:dzT("montage.clip.fondu_entree",{s:fIn.toFixed(1)}),
                        style:{left:"calc("+fiP+"% - 4px)"},
                        onPointerDown:function(e){fadeDown(e,c,"in",e.currentTarget.parentElement.parentElement)}}):null,
                      aud&&!locked?r.jsx("i",{className:"svm-fadeh",
                        title:(isMus?dzT("montage.clip.fondu_fin_musique",{s:fOut.toFixed(1)}):dzT("montage.clip.fondu_sortie",{s:fOut.toFixed(1)})),
                        style:{right:"calc("+foP+"% - 4px)"},
                        onPointerDown:function(e){fadeDown(e,c,"out",e.currentTarget.parentElement.parentElement)}}):null,
                      /* losanges de trajectoire (R4b) — un losange --accent
                         par point de position d'un overlay V2 ; clic = caler
                         la tête dessus (l'édition vit dans le lecteur et
                         l'inspecteur) — visibles même piste verrouillée,
                         le seek reste permis */
                      DzTracks.isOverlayTrack(tr.id,dzTracksRef.current)?(svmMpOf(c)||[]).map(function(p,pi){
                        return r.jsx("i",{className:"svm-mph",
                          title:(p.rotate?dzT("montage.clip.point_rot",{t:svmShort(p.t),x:Math.round(p.x*1000)/10,y:Math.round(p.y*1000)/10,rot:Math.round(p.rotate*10)/10})
                            :dzT("montage.clip.point",{t:svmShort(p.t),x:Math.round(p.x*1000)/10,y:Math.round(p.y*1000)/10})),
                          style:{left:Math.min(100,Math.max(0,p.t/clen*100))+"%"},
                          onPointerDown:function(ev){ev.stopPropagation()},
                          onClick:function(ev){ev.stopPropagation();seekTo(c.start+p.t)}},"mp"+pi)}):null]},c.id)}),
                /* jonctions V1 : étendue de la transition + losange de réglage */
                trackKind(tr.id)==="video"?svmV1Junctions(clips,tr.id).map(function(j2){   /* t117 : toute piste vidéo */
                  var on=svmTransBase(j2.right.transition)!=="cut";
                  var s2=on?svmTransS(j2.right):0;
                  return r.jsxs(r.Fragment,{children:[
                    /* bloc doré interactif : clic = réglage, poignées 4 px =
                       durée symétrique ; jamais de clipDown / scrub dessous */
                    on?r.jsxs("div",{className:"svm-transspan",
                      title:dzT("montage.transition.span_aide",{nom:svmTransLabel(j2.right.transition),s:s2.toFixed(2)}),
                      style:{left:(j2.t-s2/2)/dur*100+"%",width:s2/dur*100+"%"},
                      onPointerDown:function(e){e.stopPropagation()},
                      onPointerEnter:function(){transHoverShow(j2.t,transHoverTxt(j2.right,on,s2))},
                      onPointerLeave:transHoverHide,
                      onClick:function(e){e.stopPropagation();openTransPop(j2.right.id,e)},
                      children:[
                      r.jsx("i",{className:"svm-transhandle","data-side":"l","aria-hidden":!0,
                        onClick:function(e){e.stopPropagation()},
                        onPointerDown:function(e){if(e.altKey){dzRollDown(e,j2);return}transSpanDown(e,j2.right,-1,j2.t)}}),
                      r.jsx("i",{className:"svm-transhandle","data-side":"r","aria-hidden":!0,
                        onClick:function(e){e.stopPropagation()},
                        onPointerDown:function(e){transSpanDown(e,j2.right,1,j2.t)}})]}):null,
                    r.jsx("button",{className:"svm-junc",
                      "data-on":on?"":void 0,
                      "data-sel":transPop&&transPop.id===j2.right.id?"":void 0,
                      style:{left:"calc("+j2.t/dur*100+"% - 5px)"},
                      title:(on?dzT("montage.transition.junc_aide_duree",{nom:svmTransLabel(j2.right.transition),s:s2.toFixed(2)}):dzT("montage.transition.junc_aide",{nom:svmTransLabel(j2.right.transition)})),
                      "aria-label":dzT("montage.transition.entre",{a:j2.left.label,b:j2.right.label}),
                      onPointerDown:function(e){if(e.altKey){dzRollDown(e,j2);return}e.stopPropagation()},
                      onPointerEnter:function(){transHoverShow(j2.t,transHoverTxt(j2.right,on,s2))},
                      onPointerLeave:transHoverHide,
                      onClick:function(e){e.stopPropagation();if(e.altKey)return;openTransPop(j2.right.id,e)}})]},"jx"+j2.right.id)}):null]})]},tr.id)}),
          snapT!=null?r.jsx("div",{className:"svm-snapline",style:{left:"calc(88px + (100% - 88px) * "+(snapT/dur)+")"}}):null,
          r.jsx("div",{className:"svm-phline",style:{left:"calc(88px + (100% - 88px) * "+phFrac+")"}}),
          r.jsx("div",{className:"svm-phtri",style:{left:"calc(88px + (100% - 88px) * "+phFrac+")"}}),
          r.jsx("div",{className:"svm-hovertc",ref:hoverTcRef}),
          r.jsx("div",{className:"svm-translabel",ref:transLabelRef})]})})]}),
    /* E-7 : la barre des vues, dernier enfant de .dzsvm (tablist ; data-on = la vue courante) */
    r.jsx("div",{className:"svm-views",role:"tablist",children:[["medias",dzT("montage.vues.medias")],["montage",dzT("montage.vues.montage")],["livraison",dzT("montage.vues.livraison")]].map(function(v){return r.jsx("button",{className:"svm-viewbtn",role:"tab","aria-selected":view===v[0],"data-on":view===v[0]?"":void 0,title:dzT("montage.vues.vue",{nom:v[1]}),onClick:function(){dzSetView(v[0])},children:v[1]},v[0])})})]})}
