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
function svmRuler(s){var m=Math.floor(s/60);return m+":"+svmPad2(s-m*60)}
function svmGetTheme(){try{return localStorage.getItem("dz_svm_theme")==="light"?"light":"dark"}catch(e){return "dark"}}
function svmUseTheme(){var st=x.useState(svmGetTheme()),theme=st[0],setT=st[1];function set(t){setT(t);try{localStorage.setItem("dz_svm_theme",t)}catch(e){}}return [theme,set]}
function SvmThemeChip(props){return r.jsx("button",{className:"svm-themechip",title:"Prévisualiser l'autre thème (clair et sombre sont livrés ensemble)",onClick:function(){props.setTheme(props.theme==="dark"?"light":"dark")},children:props.theme==="dark"?"clair":"sombre"})}
function svmBars(csv){return csv.split(",").map(Number)}
function SvmLabel(props){return r.jsx("div",{className:"svm-label",style:props.style,children:props.children})}

/* ligne d'information transitoire (4,5 s) */
function svmUseNote(){var st=x.useState(""),note=st[0],setN=st[1],ref=x.useRef(null);
  var fire=x.useCallback(function(msg){setN(msg);if(ref.current)clearTimeout(ref.current);ref.current=setTimeout(function(){setN("")},4500)},[]);
  x.useEffect(function(){return function(){if(ref.current)clearTimeout(ref.current)}},[]);
  return [note,fire]}

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
 {id:"smoke",name:"Fumée douce",type:"alpha · boucle",kind:"sprite"},
 {id:"goldburst",name:"Éclat doré",type:"sprite · 12 f",kind:"sprite"},
 {id:"grain",name:"Grain 16 mm",type:"post · overlay",kind:"post"},
 {id:"bloom",name:"Glow bloom",type:"post · shader",kind:"post"},
 {id:"glitchrgb",name:"Glitch RGB",type:"post · transition",kind:"post"}];
var SVM_GENS=[
 {id:"music",name:"Musique",desc:"Piste complète, instrumentale ou chantée",price:"$0.14",c:"--c-audio",target:!0},
 {id:"sfx",name:"SFX",desc:"Pack d'effets depuis une description",price:"$0.03",c:"--c-audio",target:!0},
 {id:"voiceover",name:"Voix off",desc:"Voix IA ou clonage d'une voix humaine",price:"$0.08",c:"--c-audio"},
 {id:"vfx",name:"VFX particules",desc:"Explosions, fumée, éclats — sprite ou alpha",price:"$0.06",c:"--c-3d",target:!0},
 {id:"post",name:"Post-traitement",desc:"Grain, glow, aberration, transitions",price:"gratuit",c:"--c-3d"}];
var SVM_DEMO_VOICES=[
 {id:"prophet",name:"Prophet (clonée)",meta:"fr · grave · 44.1 kHz",cloned:!0},
 {id:"tide",name:"Tide",meta:"en · neutre"},
 {id:"narrator",name:"Narrateur humain",meta:"importée · 12 prises"},
 {id:"abyss",name:"Abyss",meta:"fr · chuchotée"}];
var SVM_DEMO_FILE={file:"voice_scene_03.wav",dur:14.32,pos:2.84,peaks:SVM_EDITOR_PEAKS,pill:"clonée · Prophet",url:null};

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
  var nt=svmUseNote(),note=nt[0],fireNote=nt[1];
  var audioRef=x.useRef(null),rafRef=x.useRef(0),simRef=x.useRef(0);

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
          if(alive)setCur({file:first.name,dur:ab.duration,pos:0,peaks:peaks,pill:"bibliothèque",url:first.url});
          ctx.close&&ctx.close()})
      }).catch(function(){})
    }).catch(function(){});
    return function(){alive=!1}},[]);

  /* un seul flux à la fois — fichier de l'éditeur (url réelle ou progression simulée) */
  function stopAll(){setPlaying(!1);setPlayingVoice("");
    if(audioRef.current){audioRef.current.pause();audioRef.current=null}
    if(rafRef.current){cancelAnimationFrame(rafRef.current);rafRef.current=0}}
  x.useEffect(function(){return stopAll},[]);
  function toggleEditor(){
    if(playing){stopAll();return}
    stopAll();setPlaying(!0);
    if(cur.url){var a=new Audio(cur.url);audioRef.current=a;a.currentTime=cur.pos>=cur.dur-.05?0:cur.pos;
      a.ontimeupdate=function(){setCur(function(c){return Object.assign({},c,{pos:a.currentTime})})};
      a.onended=function(){setPlaying(!1);setCur(function(c){return Object.assign({},c,{pos:0})})};
      a.play().catch(function(){setPlaying(!1);fireNote("Lecture bloquée par le navigateur — cliquez d'abord dans la page.")})}
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
      a.play().catch(function(){setPlayingVoice("");fireNote("Aperçu de voix indisponible.")})}
    else fireNote("Les aperçus de voix arrivent avec ElevenLabs connecté (Réglages → clés API).")}

  var vfxTiles=tab==="vfx"?SVM_VFX.filter(function(v){return v.kind==="sprite"}):tab==="post"?SVM_VFX.filter(function(v){return v.kind==="post"}):SVM_VFX;

  /* rail gauche */
  var rail=r.jsxs("aside",{className:"svm-rail",children:[
    r.jsx(SvmLabel,{children:"Générateurs"}),
    r.jsx("div",{className:"svm-genlist",children:SVM_GENS.map(function(g){
      return r.jsxs("button",{className:"svm-gen","data-sel":selGen===g.id?"":void 0,
        onClick:function(){setSelGen(g.id)},children:[
        r.jsxs("div",{className:"svm-genrow",children:[
          r.jsx("span",{className:"svm-sq7",style:{background:"var("+g.c+")"}}),
          r.jsx("span",{className:"svm-genname",children:g.name}),
          r.jsx("span",{className:"svm-genprice",children:g.price})]}),
        r.jsx("div",{className:"svm-gendesc",children:g.desc})]},g.id)})}),
    r.jsx(SvmLabel,{style:{margin:"22px 0 10px"},children:"Voix"}),
    r.jsx("div",{className:"svm-voicelist",children:
      voices===null?r.jsx("div",{className:"svm-note",children:"chargement des voix…"}):
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
            title:"Écouter la voix","aria-label":"Écouter "+v.name,
            onClick:function(e){playVoice(v,e)},children:playingVoice===v.id?"▮▮":"▶"})]},v.id)})})]});

  /* carte éditeur de voix (le formulaire du générateur Voix off, tel que maquetté) */
  var editorCard=r.jsxs("div",{className:"svm-card",children:[
    r.jsxs("div",{className:"svm-cardhead",children:[
      r.jsx("span",{className:"svm-file",children:cur.file}),
      r.jsx("span",{className:"svm-pill",children:cur.pill}),
      r.jsx("span",{className:"svm-time",children:svmClock(cur.pos)+" / "+svmClock(cur.dur)})]}),
    r.jsxs("div",{className:"svm-wave",onClick:seekWave,title:"Se déplacer",children:[
      cur.peaks.map(function(h,i){return r.jsx("div",{className:"svm-bar",style:{height:h+"%"}},i)}),
      r.jsx("div",{className:"svm-wavehead",style:{left:(cur.dur?cur.pos/cur.dur*100:0)+"%"}})]}),
    r.jsxs("div",{className:"svm-toolrow",children:[
      r.jsx("button",{className:"svm-play30",onClick:toggleEditor,
        title:playing?"Pause":"Lecture","aria-label":playing?"Pause":"Lecture",children:playing?"▮▮":"▶"}),
      ["Rogner","Fondu","Ducking","Normaliser","Dé-esser"].map(function(t){
        return r.jsx("button",{className:"svm-toolbtn",
          onClick:function(){fireNote("« "+t+" » arrive avec le backend d'édition audio — cible produit, rien n'est facturé.")},
          children:t},t)}),
      r.jsx("button",{className:"svm-primarybtn",
        onClick:function(){props.go&&props.go("montage")},children:"Envoyer au montage →"})]})]});

  /* panneau cible-produit pour les générateurs sans backend */
  function targetPanel(title,body){
    return r.jsxs("div",{className:"svm-target",children:[
      r.jsx("span",{className:"svm-targettag",children:"Cible produit"}),
      r.jsx("div",{style:{color:"var(--ink2)",fontSize:12.5,fontWeight:600,marginBottom:6},children:title}),
      r.jsx("div",{children:body})]})}
  var centerTop=
    selGen==="voiceover"?editorCard:
    selGen==="music"?targetPanel("La génération de musique n'est pas encore câblée","Aucun backend n'existe aujourd'hui pour la piste complète. La carte du rail montre l'estimation unitaire cible ($0.14 par piste) ; rien ne peut être déclenché ni facturé d'ici."):
    selGen==="sfx"?targetPanel("La génération de packs SFX n'est pas encore câblée","Aucun backend n'existe aujourd'hui pour les packs d'effets. Estimation unitaire cible : $0.03 par pack ; rien ne peut être déclenché ni facturé d'ici."):
    selGen==="vfx"?targetPanel("La génération de sprites de particules n'est pas encore câblée","effects_engine couvre uniquement le post-traitement — les sprites/alpha de particules sont une cible produit. Estimation unitaire : $0.06 par élément."):
    targetPanel("Le post-traitement s'applique au rendu","Grain, glow, aberration et transitions passent par le moteur Effects / Mask existant sur le nœud Render (gratuit, ffmpeg local). À configurer dans Studio → Render.");

  var sfxCard=r.jsxs("div",{className:"svm-card",children:[
    r.jsx(SvmLabel,{children:"Pack SFX généré"}),
    r.jsx("div",{className:"svm-sfxlist",children:SVM_SFX.map(function(s2){
      return r.jsxs("div",{className:"svm-sfx",children:[
        r.jsx("button",{className:"svm-playbtn",title:"Écouter","aria-label":"Écouter "+s2.name,
          onClick:function(){fireNote("La génération de SFX n'a pas encore de backend — ces lignes sont la cible produit.")},children:"▶"}),
        r.jsx("span",{className:"svm-sfxname",children:s2.name}),
        r.jsx("div",{className:"svm-miniwave",children:s2.bars.map(function(h,i){
          return r.jsx("div",{className:"svm-minibar",style:{height:h+"%"}},i)})}),
        r.jsx("span",{className:"svm-dur",children:s2.dur})]},s2.id)})})]});

  var vfxCard=r.jsxs("div",{className:"svm-card",children:[
    r.jsx(SvmLabel,{children:"VFX · particules & post"}),
    r.jsx("div",{className:"svm-vfxgrid"+(tab!=="audio"?" svm-wide":""),children:vfxTiles.map(function(v){
      return r.jsxs("button",{className:"svm-vfx","data-sel":selVfx===v.id?"":void 0,
        onClick:function(){setSelVfx(v.id)},children:[
        r.jsx("div",{className:"svm-vfxprev"}),
        r.jsxs("div",{className:"svm-vfxfoot",children:[
          r.jsx("div",{className:"svm-vfxname",children:v.name}),
          r.jsx("div",{className:"svm-vfxtype",children:v.type})]})]},v.id)})}),
    tab==="vfx"?r.jsx("div",{className:"svm-note",children:"La génération de sprites de particules est une cible produit — les vignettes sont des emplacements média."}):null,
    tab==="post"?r.jsx("div",{className:"svm-note",children:"Les presets post passent par le moteur Effects / Mask existant au rendu (gratuit)."}):null]});

  return r.jsxs("div",{className:"dzsvm","data-svm-theme":theme==="light"?"light":void 0,children:[
    rail,
    r.jsxs("div",{className:"svm-main",children:[
      r.jsxs("div",{className:"svm-titlebar",children:[
        r.jsx("span",{className:"svm-title",children:"Son & VFX"}),
        r.jsxs("div",{className:"svm-tabs",children:[
          r.jsx("button",{className:"svm-tab","data-on":tab==="audio"?"":void 0,onClick:function(){setTab("audio")},children:"Audio"}),
          r.jsx("button",{className:"svm-tab","data-on":tab==="vfx"?"":void 0,onClick:function(){setTab("vfx")},children:"VFX particules"}),
          r.jsx("button",{className:"svm-tab","data-on":tab==="post"?"":void 0,onClick:function(){setTab("post")},children:"Post-traitement"})]}),
        r.jsx("span",{className:"svm-meter",children:"master −14 LUFS · vrai pic −1.2 dB"}),
        r.jsx(SvmThemeChip,{theme:theme,setTheme:setTheme})]}),
      r.jsxs("div",{className:"svm-content",children:[
        note?r.jsx("div",{className:"svm-note",style:{marginTop:0,marginBottom:10},children:note}):null,
        tab==="audio"?r.jsxs(r.Fragment,{children:[centerTop,
          r.jsxs("div",{className:"svm-grid2",children:[sfxCard,vfxCard]})]}):vfxCard]})]})]})}

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
 {tr:"a1",id:"a1c1",label:"voice_scene_01",start:1.28,end:29.44},
 {tr:"a1",id:"a1c2",label:"voice_scene_03",start:30.72,end:56.32},
 {tr:"a2",id:"a2c1",label:"abyss_theme · ducking auto",start:0,end:63.36},
 {tr:"a3",id:"a3c1",label:"impact",start:7.68,end:10.88},
 {tr:"a3",id:"a3c2",label:"vague",start:22.4,end:27.52},
 {tr:"a3",id:"a3c3",label:"glitch",start:39.68,end:43.52}]}
var SVM_TRACKS=[
 {id:"v2",name:"V2",type:"overlay / VFX",h:40,c:"--c-3d",mix:13},
 {id:"v1",name:"V1",type:"vidéo",h:54,c:"--c-video",mix:12},
 {id:"a1",name:"A1",type:"dialogue",h:40,c:"--c-audio",mix:13},
 {id:"a2",name:"A2",type:"musique",h:36,c:"--c-text",mix:8},
 {id:"a3",name:"A3",type:"sfx",h:36,c:"--c-3d",mix:13}];
var SVM_DEMO_MIX={dialogue:-12,musique:-22,sfx:-18};
var SVM_MIX_COLORS={dialogue:"--c-audio",musique:"--c-av",sfx:"--c-3d"};
var SVM_ZOOMW=[100,150,220,320];
/* Formats de sortie : doit rester aligné sur _CANVAS (montage_service.py).
   Exposer ici une valeur absente de _CANVAS ferait retomber le rendu en
   9:16 sans le dire — c'était le cas de 4:5 avant l'audit du 06/08. */
var SVM_RATIOS=[["9:16","9:16 · vertical"],["4:5","4:5 · feed"],
                ["1:1","1:1 · carré"],["16:9","16:9 · paysage"]];
function svmMixRows(mixDb){return ["dialogue","musique","sfx"].map(function(k){
  var db=Number(mixDb&&mixDb[k]!=null?mixDb[k]:SVM_DEMO_MIX[k]);
  return {name:k,dbNum:db,db:db===0?"0 dB":"−"+Math.abs(db)+" dB",
    w:Math.max(8,Math.min(100,Math.round(78+3.4*(db+12)))),c:SVM_MIX_COLORS[k]}})}

/* trous V1 (> 0,1 s entre deux clips) — hachures discrètes ; le rendu y met du noir */
function svmV1Gaps(clips,dur){
  var vs=clips.filter(function(c){return c.tr==="v1"}).slice()
    .sort(function(a,b){return a.start-b.start});
  var out=[];
  for(var i=0;i<vs.length-1;i++){var g0=vs[i].end,g1=vs[i+1].start;
    if(g1-g0>.1)out.push(r.jsx("div",{className:"svm-gap",title:"trou — rendu en noir",
      style:{left:g0/dur*100+"%",width:(g1-g0)/dur*100+"%"}},"g"+i+"_"+Math.round(g0*100)))}
  return out}

/* ── transitions de coupe — 7 choix (libellés FR) mappés sur les noms backend.
   montage_service ne parse que le PREMIER mot : on stocke des noms nus
   ("fade", jamais "xfade 0.4"). La transition appartient au clip de DROITE
   d'une jonction ; premier clip et jonctions avec trou : ignorées au rendu. */
var SVM_TRANS=[["cut","coupe sèche"],["fade","fondu"],["dissolve","dissolution"],
 ["fadeblack","fondu noir"],["glitch","pixélisé"],["slide","glissement"],["flash","fondu blanc"]];
function svmTransBase(t){return String(t||"cut").split(/\s+/)[0]||"cut"}
function svmTransLabel(t){var b=svmTransBase(t);
  var f=SVM_TRANS.find(function(o){return o[0]===b});return f?f[1]:b}
function svmTransS(c){return Math.min(1,Math.max(.1,Number(c&&c.transition_s)||.4))}
/* jonctions V1 : deux clips consécutifs dont l'écart ≤ 0,1 s (au-delà : trou) */
function svmV1Junctions(cs){
  var vs=cs.filter(function(c){return c.tr==="v1"}).slice()
    .sort(function(a,b){return a.start-b.start});
  var out=[];
  for(var i=0;i<vs.length-1;i++){
    if(Math.abs(vs[i+1].start-vs[i].end)<=.1)
      out.push({t:(vs[i].end+vs[i+1].start)/2,left:vs[i],right:vs[i+1]})}
  return out}
function svmLeftNeighbor(cs,c){
  var best=null;
  cs.forEach(function(k){
    if(k.tr!=="v1"||k.id===c.id||k.start>=c.start)return;
    if(Math.abs(c.start-k.end)<=.1&&(!best||k.end>best.end))best=k});
  return best}
/* clip V1 réel (src vidéo ou image) actif sous t — fin exclusive, dernier départ gagne */
function svmActiveV1(cs,t){var best=null;
  for(var i=0;i<cs.length;i++){var c=cs[i];
    if(c.tr==="v1"&&c.src&&(c.src.job_id||c.src.image)&&c.start<=t&&t<c.end&&(!best||c.start>=best.start))best=c}
  return best}

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
  var stP=x.useState({demo:!0,name:"teaser_abyss",version:"v4",ratio:"9:16",dur:SVM_DEMO_DUR,mixDb:SVM_DEMO_MIX}),proj=stP[0],setProj=stP[1];
  var stJ=x.useState(null),job=stJ[0],setJob=stJ[1]; /* {id,kind,status,progress,step,error} */
  var stV=x.useState(null),previewUrl=stV[0],setPreviewUrl=stV[1];
  var stF=x.useState(null),fxCat=stF[0],setFxCat=stF[1]; /* catalogue Effects/Mask */
  var stFP=x.useState(!1),fxPick=stFP[0],setFxPick=stFP[1];
  var stFE=x.useState(null),fxEdit=stFE[0],setFxEdit=stFE[1]; /* {id,i} chip en édition */
  var stO=x.useState(""),ovPick=stO[0],setOvPick=stO[1]; /* "" = fermé, sinon l'id de la piste visée */
  var stS=x.useState(null),sources=stS[0],setSources=stS[1]; /* {images,videos} pour overlays */
  var stVZ=x.useState(1),vzoom=stVZ[0],setVzoom=stVZ[1]; /* zoom molette du viewport (≠ zoom timeline) */
  var ovSeq=x.useRef(0);
  var stTP=x.useState(null),transPop=stTP[0],setTransPop=stTP[1]; /* jonction en édition — {id: clip de DROITE, x: px du popover} */
  var rootRef=x.useRef(null),transHistAt=x.useRef(0);
  var nt=svmUseNote(),note=nt[0],fireNote=nt[1];
  var rafRef=x.useRef(0),phRef=x.useRef(ph);phRef.current=ph;
  var clipsRef=x.useRef(clips);clipsRef.current=clips;
  var selRef=x.useRef(selId);selRef.current=selId;
  var durRef=x.useRef(proj.dur);durRef.current=proj.dur;
  var videoRef=x.useRef(null);
  var mixRef=x.useRef(proj.mixDb);mixRef.current=proj.mixDb;
  var rippleRef=x.useRef(ripple);rippleRef.current=ripple;
  var previewRef=x.useRef(previewUrl);previewRef.current=previewUrl;
  var zoomPctRef=x.useRef(zoomPct);zoomPctRef.current=zoomPct;
  var tlScrollRef=x.useRef(null),pendScrollRef=x.useRef(null);
  var histRef=x.useRef({u:[],r:[]}); /* piles annuler / rétablir */
  var stHT=x.useState(0),setHistTick=stHT[1];
  /* lecteur vivant + molette J/K/L + zones sûres */
  var playingRef=x.useRef(playing);playingRef.current=playing;
  var stSp=x.useState(1),spd=stSp[0],setSpd=stSp[1]; /* vitesse signée ±1/2/4 */
  var spdRef=x.useRef(spd);spdRef.current=spd;
  var stSf=x.useState(!1),safeOn=stSf[0],setSafeOn=stSf[1];
  var frameRef=x.useRef(null),hoverTcRef=x.useRef(null);
  var liveHostRef=x.useRef(null),liveOvRef=x.useRef(null),liveVideoRef=x.useRef(null);
  var livePoolRef=x.useRef(null),liveSeqRef=x.useRef(0);
  var liveRafRef=x.useRef(0),livePendRef=x.useRef(null);
  var dur=proj.dur;

  /* ── historique — instantanés {clips, mixDb}, cap 60 de chaque côté.
     pushHistory() lit les refs (état d'AVANT la mutation) ; un geste continu
     (drag, trim, mixage) capture son état au pointerdown et ne pousse qu'une
     entrée au relâchement. Les tableaux sont traités en immutable partout,
     stocker les références suffit. */
  var pushHistory=x.useCallback(function(prev){
    var h=histRef.current;
    h.u.push(prev||{clips:clipsRef.current,mixDb:mixRef.current});
    if(h.u.length>60)h.u.shift();
    h.r.length=0;
    setHistTick(function(t){return t+1})},[]);
  var undo=x.useCallback(function(){
    var h=histRef.current;if(!h.u.length)return;
    var s=h.u.pop();
    h.r.push({clips:clipsRef.current,mixDb:mixRef.current});
    if(h.r.length>60)h.r.shift();
    setClips(s.clips);
    setProj(function(p){return Object.assign({},p,{mixDb:s.mixDb})});
    setDirty(!0);setHistTick(function(t){return t+1})},[]);
  var redo=x.useCallback(function(){
    var h=histRef.current;if(!h.r.length)return;
    var s=h.r.pop();
    h.u.push({clips:clipsRef.current,mixDb:mixRef.current});
    if(h.u.length>60)h.u.shift();
    setClips(s.clips);
    setProj(function(p){return Object.assign({},p,{mixDb:s.mixDb})});
    setDirty(!0);setHistTick(function(t){return t+1})},[]);
  /* suppression du clip sélectionné — ripple actif : les clips SUIVANTS de la
     même piste remontent de la longueur du trou (piste principale magnétique) */
  var delClip=x.useCallback(function(){
    var id=selRef.current,cs=clipsRef.current;
    var c=cs.find(function(k){return k.id===id});
    if(!c)return;
    pushHistory();
    var len=c.end-c.start;
    var next=cs.filter(function(k){return k.id!==id});
    if(rippleRef.current)next=next.map(function(k){
      return k.tr===c.tr&&k.start>=c.end-.001?
        Object.assign({},k,{start:k.start-len,end:k.end-len}):k});
    setClips(next);setSelId("");setDirty(!0);
    fireNote("« "+c.label+" » supprimé"+(rippleRef.current?" — trou refermé (ripple)":""))},[fireNote,pushHistory]);

  /* projet initial — vrais assets de la Bibliothèque quand il y en a */
  x.useEffect(function(){var alive=!0;
    fetch("/api/montage/project").then(function(res){return res.json()}).then(function(d){
      if(!alive||!d||!d.ok||!d.has_assets)return;
      var cs=(d.clips||[]).map(function(c,i){
        return {tr:c.tr,id:c.id||("c"+i),label:c.label||"clip",start:Number(c.start)||0,
          end:Number(c.end)||0,src:c.src||null,srcIn:Number(c.srcIn)||0,
          transition:c.transition||(c.tr==="v1"?"cut":void 0),
          transition_s:Number(c.transition_s)||0}});
      var first=cs.find(function(c){return c.tr==="v1"});
      setClips(cs);setSelId(first?first.id:"");setPh(0);setDirty(!1);
      histRef.current={u:[],r:[]};setHistTick(function(t){return t+1});
      setProj({demo:!1,name:d.name||"montage",version:"v1",ratio:d.ratio||"9:16",
        dur:Math.max(1,Number(d.duration)||1),mixDb:d.mix||SVM_DEMO_MIX});
    }).catch(function(){});
    return function(){alive=!1}},[]);

  /* catalogue du moteur Effects / Mask (sélecteur d'effets par clip) */
  x.useEffect(function(){var alive=!0;
    fetch("/api/montage/effects").then(function(res){return res.json()}).then(function(d){
      if(alive&&d&&d.effects)setFxCat(d.effects)}).catch(function(){});
    return function(){alive=!1}},[]);

  var sel=clips.find(function(c){return c.id===selId})||null;
  var mixRows=svmMixRows(proj.mixDb);

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
            if(c)p=Math.min(c.end,Math.max(c.start,c.start+(lv.currentTime-(c.srcIn||0))))}
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
      var wt=(c.srcIn||0)+(t-c.start);
      lv.muted=!run; /* muet pendant le scrub — le son du plan en lecture */
      if(run){
        if(lv.playbackRate!==s)lv.playbackRate=s;
        if(Math.abs(lv.currentTime-wt)>.35){try{lv.currentTime=wt}catch(_e){}}
        if(lv.paused&&!lv.ended)livePlay(lv)}
      else{
        if(!lv.paused)lv.pause();
        if(lv.playbackRate!==1)lv.playbackRate=1;
        liveSeek(lv,wt)}}
    /* overlays V2 actifs à t, au-dessus du fond, opacité appliquée */
    var act={};
    cs.forEach(function(k){
      if(k.tr==="v2"&&k.src&&(k.src.job_id||k.src.image)&&k.start<=t&&t<k.end)act[k.id]=k});
    for(var i=ov.children.length-1;i>=0;i--){var ch=ov.children[i],kc=act[ch._svmId];
      if(!kc||livePoolKey(kc.src,"o")!==ch._svmKey){
        if(ch.tagName==="VIDEO"&&!ch.paused){try{ch.pause()}catch(_e){}}
        ov.removeChild(ch)}}
    Object.keys(act).forEach(function(id){
      var k=act[id],el=null;
      for(var i2=0;i2<ov.children.length;i2++){
        if(ov.children[i2]._svmId===id){el=ov.children[i2];break}}
      if(!el){var it2=livePoolGet(k.src,"o");el=it2.el;
        el._svmId=id;el._svmKey=livePoolKey(k.src,"o");ov.appendChild(el)}
      el.style.opacity=k.opacity==null?"":String(k.opacity);
      if(el.tagName==="VIDEO"){
        el.muted=!0; /* un overlay ne porte jamais le son */
        var wt2=(k.srcIn||0)+(t-k.start);
        if(run){
          if(el.playbackRate!==s)el.playbackRate=s;
          if(Math.abs(el.currentTime-wt2)>.35){try{el.currentTime=wt2}catch(_e){}}
          if(el.paused&&!el.ended)livePlay(el)}
        else{if(!el.paused)el.pause();liveSeek(el,wt2)}}})}
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
      if(o.video){try{o.el.pause();o.el.removeAttribute("src");o.el.load()}catch(_e){}}});
      pool.clear()}}},[]);
  function svmFullscreen(){
    var el=frameRef.current;if(!el)return;
    try{
      if(document.fullscreenElement){
        if(document.exitFullscreen){var pr2=document.exitFullscreen();if(pr2&&pr2.catch)pr2.catch(function(){})}}
      else if(el.requestFullscreen){var pr=el.requestFullscreen();if(pr&&pr.catch)pr.catch(function(){})}}
    catch(_e){}}

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
  /* Ctrl+molette sur la timeline. Listener natif non passif : l'onWheel React
     est passif et ne bloquerait pas le zoom pleine page du navigateur. */
  x.useEffect(function(){var el=tlScrollRef.current;if(!el)return;
    function onW(e){if(!(e.ctrlKey||e.metaKey))return;e.preventDefault();
      zoomApply(zoomPctRef.current*Math.pow(1.0015,-e.deltaY),e.clientX)}
    el.addEventListener("wheel",onW,{passive:!1});
    return function(){el.removeEventListener("wheel",onW)}},[zoomApply]);

  /* sauts transport — points de coupe V1 (aussi ↑ / ↓ au clavier) */
  var jump=x.useCallback(function(dir){var pts=[0,durRef.current];
    clipsRef.current.forEach(function(c){if(c.tr==="v1")pts.push(c.start,c.end)});
    pts.sort(function(a,b){return a-b});
    var p=phRef.current;
    if(dir<0){for(var i=pts.length-1;i>=0;i--){if(pts[i]<p-.05){seekTo(pts[i]);return}}seekTo(0)}
    else{for(var j2=0;j2<pts.length;j2++){if(pts[j2]>p+.05){seekTo(pts[j2]);return}}seekTo(durRef.current)}},[seekTo]);

  /* lame (bouton + ⌥C) */
  var blade=x.useCallback(function(){
    var p=phRef.current,cs=clipsRef.current,id=selRef.current;
    var c=cs.find(function(k){return k.id===id});
    if(!c||p<=c.start+.05||p>=c.end-.05){fireNote("Lame : placez la tête de lecture dans le clip sélectionné.");return}
    pushHistory();
    setClips(cs.map(function(k){return k===c?Object.assign({},c,{end:p}):k})
      /* la moitié droite démarre sur une jonction « cut » éditable (le losange) —
         sans quoi elle hériterait de la transition d'entrée du clip coupé */
      .concat([Object.assign({},c,{id:c.id+"_b"+Math.round(p*10),start:p,srcIn:(c.srcIn||0)+(p-c.start),fx:c.fx,transition:"cut",transition_s:0})]));
    setDirty(!0);fireNote("Clip coupé à "+svmShort(p))},[fireNote,pushHistory]);
  x.useEffect(function(){
    function onKey(e){
      /* Un champ de saisie garde ses touches. L'écran contient des
         <input type="range"> (opacité, intensité) qui consomment déjà
         l'espace et les flèches : sans cette garde, espace basculerait la
         lecture EN PLUS de déplacer le curseur qui a le focus. */
      var el=e.target,tg=(el&&el.tagName||"").toLowerCase();
      if(tg==="input"||tg==="textarea"||tg==="select"||(el&&el.isContentEditable))return;
      var k=e.key;
      if(e.ctrlKey||e.metaKey){
        if(k==="z"||k==="Z"){e.preventDefault();if(e.shiftKey)redo();else undo();return}
        if(k==="y"||k==="Y"){e.preventDefault();redo();return}
        if(k==="="||k==="+"){e.preventDefault();zoomApply(zoomPctRef.current*1.25);return}
        if(k==="-"||k==="_"){e.preventDefault();zoomApply(zoomPctRef.current/1.25);return}
        return}
      if(e.altKey&&(k==="c"||k==="C"||e.code==="KeyC")){e.preventDefault();blade();return}
      /* espace = lecture/pause ; preventDefault sinon la page défile */
      if(e.code==="Space"||k===" "){e.preventDefault();setSpd(1);setPlaying(function(p){return !p});return}
      if(k==="Delete"||k==="Backspace"){e.preventDefault();delClip();return}
      /* tête de lecture : ±1 image (1/30 s), Maj = ±10 images */
      if(k==="ArrowLeft"||k==="ArrowRight"){e.preventDefault();
        var st=(e.shiftKey?10:1)/30*(k==="ArrowLeft"?-1:1);
        seekTo(Math.min(durRef.current,Math.max(0,phRef.current+st)));return}
      if(k==="ArrowUp"){e.preventDefault();jump(-1);return}
      if(k==="ArrowDown"){e.preventDefault();jump(1);return}
      if(k==="Home"){e.preventDefault();seekTo(0);return}
      if(k==="End"){e.preventDefault();seekTo(durRef.current);return}
      if(e.shiftKey&&(k==="z"||k==="Z")){e.preventDefault();zoomApply(100);return}
      if(!e.shiftKey&&!e.altKey&&(k==="n"||k==="N")){setSnap(function(s){return !s});return}
      if(!e.shiftKey&&!e.altKey&&(k==="r"||k==="R")){setRipple(function(v){return !v});return}
      /* J/K/L : molette de lecture — L avant ×1/×2/×4, K pause, J arrière
         (shuttle par seeks) ; G : zones sûres sur le cadre */
      if(!e.shiftKey&&!e.altKey&&(k==="l"||k==="L")){e.preventDefault();
        if(playingRef.current)setSpd(function(s2){return s2<0?1:Math.min(4,s2*2)});
        else{setSpd(1);setPlaying(!0)}
        return}
      if(!e.shiftKey&&!e.altKey&&(k==="j"||k==="J")){e.preventDefault();
        if(playingRef.current)setSpd(function(s2){return s2>0?-1:Math.max(-4,s2*2)});
        else{setSpd(-1);setPlaying(!0)}
        return}
      if(!e.shiftKey&&!e.altKey&&(k==="k"||k==="K")){e.preventDefault();setSpd(1);setPlaying(!1);return}
      if(!e.shiftKey&&!e.altKey&&(k==="g"||k==="G")){setSafeOn(function(v){return !v});return}
    }
    window.addEventListener("keydown",onKey);
    return function(){window.removeEventListener("keydown",onKey)}},[blade,delClip,undo,redo,jump,seekTo,zoomApply]);

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
    el.textContent=svmShort(fx*durRef.current);
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
    e.stopPropagation();setSelId(c.id);
    var rect=laneEl.getBoundingClientRect(),pxPerS=rect.width/durRef.current;
    var cRect=e.currentTarget.getBoundingClientRect();
    var edge=svmEdgeAt(e.clientX,cRect);
    var x0=e.clientX,s0=c.start,e0=c.end,moved=!1,tgt=e.currentTarget;
    try{tgt.setPointerCapture&&tgt.setPointerCapture(e.pointerId)}catch(_c){}
    var h0={clips:clipsRef.current,mixDb:mixRef.current},snapAt=null;
    var edges=[0,durRef.current,phRef.current];
    clipsRef.current.forEach(function(k){if(k.id!==c.id){edges.push(k.start,k.end)}});
    /* ripple : rognage du bord droit d'un clip V1 — les clips suivants de la
       piste suivent le delta (positions d'origine capturées : pas de dérive) */
    var rip=ripple&&c.tr==="v1"&&edge==="r",orig={},ripMax=0;
    if(rip)clipsRef.current.forEach(function(k){
      if(k.id!==c.id&&k.tr===c.tr&&k.start>=e0-.001){
        orig[k.id]={s:k.start,e:k.end};if(k.end>ripMax)ripMax=k.end}});
    function doSnap(v){if(!snap)return v;var t=8/pxPerS,best=v;
      edges.forEach(function(g){if(Math.abs(g-v)<t){t=Math.abs(g-v);best=g}});
      if(best!==v)snapAt=best;
      return best}
    function mv(ev){var ds=(ev.clientX-x0)/pxPerS;
      if(Math.abs(ev.clientX-x0)>3)moved=!0;if(!moved)return;
      snapAt=null;
      var w=0,delta=0;
      if(edge==="r"){
        var lim=durRef.current;
        if(rip&&ripMax>0)lim=Math.min(lim,e0+(durRef.current-ripMax));
        w=Math.max(s0+.3,Math.min(lim,doSnap(e0+ds)));delta=w-e0}
      setClips(clipsRef.current.map(function(k){
        if(k.id!==c.id){
          if(rip&&orig[k.id])return Object.assign({},k,
            {start:orig[k.id].s+delta,end:orig[k.id].e+delta});
          return k}
        if(edge==="m"){var len=e0-s0,ns=doSnap(s0+ds);
          var nsEnd=doSnap(e0+ds);if(nsEnd!==e0+ds&&ns===s0+ds)ns=nsEnd-len;
          ns=Math.min(durRef.current-len,Math.max(0,ns));
          return Object.assign({},k,{start:ns,end:ns+len})}
        if(edge==="l"){var v=Math.min(e0-.3,Math.max(0,doSnap(s0+ds)));
          var upd={start:v};
          /* rognage gauche NLE : la source avance d'autant (clips réels) */
          if(k.src)upd.srcIn=Math.max(0,(c.srcIn||0)+(v-s0));
          return Object.assign({},k,upd)}
        return Object.assign({},k,{end:w})}));
      setSnapT(snapAt)}
    function up(){tgt.removeEventListener("pointermove",mv);tgt.removeEventListener("pointerup",up);
      setSnapT(null);
      if(moved){setDirty(!0);pushHistory(h0)}}
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
    if(!n){fireNote("Aucune coupe V1 adjacente.");return}
    pushHistory();
    setClips(clipsRef.current.map(function(k){
      return ids[k.id]?Object.assign({},k,{transition:t,transition_s:t==="cut"?0:s2}):k}));
    setDirty(!0);
    fireNote("Transition « "+svmTransLabel(t)+" » appliquée à "+n+" coupe"+(n>1?"s":""))}
  function openTransPop(id,e){
    if(transPop&&transPop.id===id){setTransPop(null);return}
    var rr=rootRef.current?rootRef.current.getBoundingClientRect():null;
    var bx=e.currentTarget.getBoundingClientRect();
    var cx=rr?bx.left+bx.width/2-rr.left:bx.left;
    var w=rr?rr.width:window.innerWidth;
    setTransPop({id:id,x:Math.max(8,Math.min(w-256,cx-124))})}
  /* fermeture du popover de jonction : clic extérieur ou Échap */
  x.useEffect(function(){
    if(!transPop)return;
    function onDown(e){var el=e.target;
      while(el&&el!==document){
        if(el.classList&&(el.classList.contains("svm-transpop")||el.classList.contains("svm-junc")))return;
        el=el.parentElement}
      setTransPop(null)}
    function onEsc(e){if(e.key==="Escape")setTransPop(null)}
    window.addEventListener("pointerdown",onDown,!0);
    window.addEventListener("keydown",onEsc,!0);
    return function(){window.removeEventListener("pointerdown",onDown,!0);
      window.removeEventListener("keydown",onEsc,!0)}},[transPop]);

  /* ── ajout d'assets depuis la Bibliothèque, sur n'importe quelle piste ──
     ovPick vaut "" (fermé) ou l'identifiant de la piste visée. Les sources
     proposées suivent le type de la piste : une piste audio ne doit pas
     proposer d'images, une piste vidéo ne doit pas proposer de .mp3. */
  function trackKind(trId){return String(trId||"").charAt(0)==="a"?"audio":"video"}
  function openPicker(trId){
    if(proj.demo){fireNote("Ajout d'assets : disponible sur un projet réel — la démo reste une maquette.");return}
    if(ovPick===trId){setOvPick("");return}
    if(sources){setOvPick(trId);return}
    Promise.all([
      fetch("/api/images").then(function(res){return res.json()}).catch(function(){return {}}),
      fetch("/api/jobs").then(function(res){return res.json()}).catch(function(){return []}),
      fetch("/api/audio").then(function(res){return res.json()}).catch(function(){return {}})
    ]).then(function(rr){
      var imgs=((rr[0]&&rr[0].images)||[]).slice(0,24).map(function(im){return {name:im.filename}});
      var vids=(Array.isArray(rr[1])?rr[1]:[]).filter(function(j3){
        return j3.status==="done"&&(j3.video_path||j3.final_video_path)&&
          !(j3.provider==="montage"&&String(j3.image_filename||"").indexOf("_preview")>=0)})
        .slice(0,12).map(function(j3){return {job_id:j3.job_id,title:j3.title||j3.job_id,
          dur:Number(j3.duration_real_s||j3.duration_s)||0}});
      var auds=((rr[2]&&rr[2].audio)||[]).slice(0,24).map(function(a3){
        return {name:a3.name,kb:a3.size_kb}});
      setSources({images:imgs,videos:vids,audios:auds});setOvPick(trId)});
  }
  /* durée par défaut d'un asset posé : une image n'en a pas, une vidéo et un
     son sont bornés pour rester manipulables à la souris. */
  function defaultLen(kind,srcDur){
    if(kind==="image")return 4;
    if(kind==="audio")return Math.min(8,srcDur||8);
    return Math.min(6,srcDur||6);
  }
  function addAsset(src,label,kind,srcDur,trId,atTime){
    var tr2=trId||"v2",d=durRef.current;
    var st=atTime==null?phRef.current:atTime;
    st=Math.min(Math.max(0,st),Math.max(0,d-1));
    var en=Math.min(d,st+defaultLen(kind,srcDur));if(en-st<.5)st=Math.max(0,en-1);
    ovSeq.current++;
    var id=tr2+"u"+ovSeq.current+"_"+Math.round(st*10);
    pushHistory();
    setClips(clipsRef.current.concat([{tr:tr2,id:id,label:label,start:st,end:en,src:src,srcIn:0}]));
    setSelId(id);setDirty(!0);setOvPick("");
    fireNote("« "+label+" » ajouté sur "+tr2.toUpperCase()+" à "+svmShort(st)+" — glissez / rognez sur la piste.")}

  /* ── glisser-déposer : le sélecteur est la source, les bandes et le
     viewport sont les cibles. Le viewport vise la piste vidéo principale. ── */
  var DZ_MIME="application/dz-asset";
  function dragPayload(e,src,label,kind,srcDur){
    try{e.dataTransfer.setData(DZ_MIME,JSON.stringify({src:src,label:label,kind:kind,dur:srcDur||0}));
        e.dataTransfer.effectAllowed="copy"}catch(_e){}}
  function readPayload(e){
    try{var raw=e.dataTransfer.getData(DZ_MIME);return raw?JSON.parse(raw):null}catch(_e){return null}}
  function dropOnTrack(e,trId,laneEl){
    var p=readPayload(e);if(!p)return;
    e.preventDefault();
    /* un son ne se dépose pas sur une piste vidéo, et réciproquement */
    if(trackKind(trId)!==(p.kind==="audio"?"audio":"video")){
      fireNote(p.kind==="audio"?"Un son se dépose sur A1, A2 ou A3.":"Cet asset se dépose sur V1 ou V2.");return}
    var t=null;
    if(laneEl){var rect=laneEl.getBoundingClientRect();
      if(rect.width>0)t=Math.max(0,(e.clientX-rect.left)/rect.width*durRef.current)}
    addAsset(p.src,p.label,p.kind,p.dur,trId,t);
  }

  /* ── rendu réel : POST /api/montage/render + poll /api/jobs/{id} ── */
  function renderPayload(preview){
    return {name:proj.name,ratio:proj.ratio,preview:preview,
      duration_master:durMaster,ducking:ducking,mix:proj.mixDb,
      clips:clips.filter(function(c){return c.src}).map(function(c){
        return {tr:c.tr,src:c.src,start:c.start,end:c.end,srcIn:c.srcIn||0,
          transition:c.transition||"cut",transition_s:c.transition_s||0,
          effects:c.effects&&c.effects.length?c.effects:void 0,
          opacity:c.opacity}})}}
  function launchRender(preview){
    if(proj.demo||(job&&job.status!=="failed"))return;
    setJob({id:null,kind:preview?"preview":"final",status:"queued",progress:0,step:"Envoi…",error:null});
    fetch("/api/montage/render",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify(renderPayload(preview))})
      .then(function(res){return res.json().then(function(d){return {ok:res.ok,d:d}})})
      .then(function(o){
        if(!o.ok||!o.d.job_id){setJob({id:null,kind:preview?"preview":"final",status:"failed",progress:0,step:"",
          error:(o.d&&(o.d.detail||o.d.error))||"échec du lancement"});return}
        setJob({id:o.d.job_id,kind:preview?"preview":"final",status:"running",progress:10,step:"En file",error:null})})
      .catch(function(e){setJob({id:null,kind:preview?"preview":"final",status:"failed",progress:0,step:"",error:String(e)})})}
  x.useEffect(function(){
    if(!job||!job.id||job.status==="done"||job.status==="failed")return;
    var t=setInterval(function(){
      fetch("/api/jobs/"+job.id).then(function(res){return res.json()}).then(function(d){
        if(!d)return;
        if(d.status==="done"){
          clearInterval(t);
          if(job.kind==="preview"){
            setPreviewUrl("/api/jobs/"+job.id+"/video?t="+Date.now());
            setJob(null);setPop("");seekTo(0);
            fireNote("Aperçu 480p prêt — branché dans le lecteur ("+(d.duration_real_s||d.duration_s||"?")+" s).")}
          else{
            var run=new Date();run.setDate(run.getDate()+1);run.setHours(9,0,0,0);
            fetch("/api/schedule",{method:"POST",headers:{"Content-Type":"application/json"},
              body:JSON.stringify({title:proj.name,caption:proj.name+" 🐙",channels:["x","telegram"],
                run_at:run.toISOString(),status:"draft",mode:"assisted",job_id:job.id})})
              .then(function(res){return res.json()}).then(function(p2){
                setJob(null);setPop("");setDirty(!1);
                fireNote("Rendu final terminé — brouillon ajouté au Scheduler.");
                if(p2&&p2.id){setTimeout(function(){
                  window.dispatchEvent(new CustomEvent("deepotus:select-post",{detail:{id:p2.id}}))},400)}
                props.go&&setTimeout(function(){props.go("scheduler")},900)})
              .catch(function(){setJob(null);setPop("");
                fireNote("Rendu terminé (Bibliothèque) — création du brouillon Scheduler impossible.")})}}
        else if(d.status==="failed"){clearInterval(t);
          setJob(function(j){return Object.assign({},j,{status:"failed",error:d.error||"échec du rendu"})})}
        else{setJob(function(j){return Object.assign({},j,{status:"running",
          progress:Number(d.progress)||0,step:d.current_step||""})})}
      }).catch(function(){})},1500);
    return function(){clearInterval(t)}},[job&&job.id,job&&job.kind,job&&job.status==="failed"]);

  var phFrac=dur?ph/dur:0;
  var liveOn=!previewUrl&&!proj.demo; /* lecteur vivant : sources sous la tête */
  var liveClip=liveOn?svmActiveV1(clips,Math.min(ph,Math.max(0,dur-.001))):null;
  var tickStep=[2,3,5,6,10,15,20,30,60].find(function(s){return dur/s<=11})||60;
  var ticks=[];for(var t2=0;t2<=Math.floor(dur/tickStep)*tickStep&&ticks.length<40;t2+=tickStep)ticks.push(t2);

  /* popover de confirmation — coût affiché avant tout déclenchement (règle produit) */
  function popover(){
    if(!pop)return null;
    var isR=pop==="render";
    var busy=job&&job.kind===(isR?"final":"preview")&&job.status!=="failed";
    var failed=job&&job.status==="failed";
    return r.jsxs("div",{className:"svm-pop",children:[
      r.jsx("div",{className:"svm-poptitle",children:isR?"Rendre & publier":"Preview 480p"}),
      r.jsxs("div",{className:"svm-popline",children:[r.jsx("span",{children:isR?"rendu ffmpeg (local) · "+svmRuler(Math.round(dur)):"aperçu ffmpeg 480p (local) · "+svmRuler(Math.round(dur))}),r.jsx("span",{className:"svm-cost",children:"$0.00"})]}),
      isR?r.jsxs("div",{className:"svm-popline",children:[r.jsx("span",{children:"publication · brouillon Scheduler"}),r.jsx("span",{className:"svm-cost",children:"gratuit"})]}):null,
      proj.demo?
        r.jsx("div",{className:"svm-popnote",children:"Timeline de démonstration — aucune source réelle à rendre. Génère ou importe d'abord une vidéo (Studio, Quick, Épisodes ou upload) : la timeline se remplira depuis la Bibliothèque."}):
        busy?r.jsxs("div",{className:"svm-popnote",children:["Rendu en cours — ",job.progress,"% · ",job.step||"…"]}):
        failed?r.jsxs("div",{className:"svm-popnote",style:{color:"var(--red)"},children:["Échec : ",job.error]}):
        r.jsx("div",{className:"svm-popnote",children:isR?
          "Rendu local 1080 (aucun crédit consommé), puis brouillon dans le Scheduler — rien n'est publié sans ta validation.":
          "L'aperçu basse résolution est gratuit et local — il ne consomme jamais de crédits. Le résultat se branche dans le lecteur."}),
      r.jsxs("div",{className:"svm-poprow",children:[
        r.jsx("button",{className:"svm-secbtn",onClick:function(){setPop("");if(failed)setJob(null)},children:"Fermer"}),
        proj.demo?null:
          failed?r.jsx("button",{className:"svm-goldbtn",onClick:function(){launchRender(!isR)},children:"Réessayer"}):
          r.jsx("button",{className:"svm-goldbtn",disabled:busy,style:busy?{opacity:.55,cursor:"default"}:null,
            onClick:function(){if(!busy)launchRender(!isR)},
            children:busy?(job.progress+"%"):(isR?"Rendre & publier":"Lancer l'aperçu")})]})]})}

  /* sélecteur d'effets — catalogue réel du moteur Effects / Mask */
  function fxPicker(){
    if(!fxPick||!fxCat)return null;
    return r.jsxs("div",{className:"svm-pop",style:{top:96},children:[
      r.jsx("div",{className:"svm-poptitle",children:"Ajouter un effet — moteur Effects / Mask"}),
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
              fireNote("Effet « "+((fxCat[t3]&&fxCat[t3].label)||t3)+" » ajouté — appliqué au rendu du clip.")},
            children:(fxCat[t3]&&fxCat[t3].label)||t3},t3)})}),
      r.jsx("div",{className:"svm-poprow",children:
        r.jsx("button",{className:"svm-secbtn",onClick:function(){setFxPick(!1)},children:"Fermer"})})]})}

  /* réglage d'opacité (overlay V2 sélectionné) */
  function opacityRow(){
    var v=Math.round((sel.opacity==null?1:sel.opacity)*100);
    return r.jsxs("div",{className:"svm-fxedit",children:[
      r.jsx("span",{className:"svm-fxeditname",children:"Opacité"}),
      r.jsx("input",{className:"svm-range",type:"range",min:10,max:100,step:5,value:v,
        "aria-label":"Opacité de l'overlay",
        onChange:function(e){var nv=Number(e.target.value)/100;var id=selRef.current;
          setClips(clipsRef.current.map(function(k){return k.id===id?Object.assign({},k,{opacity:nv>=1?void 0:nv}):k}));
          setDirty(!0)}}),
      r.jsx("span",{className:"svm-rangeval",children:v+" %"})]})}

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
  function fxEditRow(){
    if(!fxEdit||!sel||fxEdit.id!==sel.id)return null;
    var f=(sel.effects||[])[fxEdit.i];if(!f)return null;
    var meta=(fxCat&&fxCat[f.type])||{};var lbl=meta.label||f.type;
    var hasInt=(meta.params||[]).indexOf("intensity")>=0;
    return r.jsxs(r.Fragment,{children:[r.jsxs("div",{className:"svm-fxedit",children:[
      r.jsx("span",{className:"svm-fxeditname",children:lbl}),
      hasInt?r.jsx("input",{className:"svm-range",type:"range",min:5,max:100,step:5,
        value:Math.round(f.intensity!=null?f.intensity:60),
        "aria-label":"Intensité de l'effet "+lbl,
        onChange:function(e){var nv=Number(e.target.value);var id=selRef.current,i2=fxEdit.i;
          setClips(clipsRef.current.map(function(k){
            if(k.id!==id)return k;
            var fx=(k.effects||[]).slice();fx[i2]=Object.assign({},fx[i2],{intensity:nv});
            return Object.assign({},k,{effects:fx})}));
          setDirty(!0)}}):
        r.jsx("span",{className:"svm-note",style:{flex:1,marginTop:0},children:"sans réglage d'intensité"}),
      hasInt?r.jsx("span",{className:"svm-rangeval",children:Math.round(f.intensity!=null?f.intensity:60)}):null,
      r.jsx("button",{className:"svm-minibtn",onClick:function(){
        var id=selRef.current,i2=fxEdit.i;
        pushHistory();
        setClips(clipsRef.current.map(function(k){
          if(k.id!==id)return k;
          var fx=(k.effects||[]).slice();fx.splice(i2,1);
          return Object.assign({},k,{effects:fx})}));
        setFxEdit(null);setDirty(!0)},children:"retirer"})]}),
      fxParamRow(f)]})}

  /* sélecteur d'assets — contenu filtré selon le type de la piste visée */
  function ovPicker(){
    if(!ovPick||!sources)return null;
    var tr2=ovPick,audio=trackKind(tr2)==="audio";
    return r.jsxs("div",{className:"svm-pop",style:{top:96},children:[
      r.jsx("div",{className:"svm-poptitle",children:"Ajouter sur la piste "+tr2.toUpperCase()}),
      r.jsx("div",{className:"svm-popnote",style:{marginTop:6},
        children:audio?("Posé à la tête de lecture ("+svmShort(ph)+"). A1 = dialogue, A2 = musique (ducking auto), A3 = SFX.")
                      :("Posé à la tête de lecture ("+svmShort(ph)+") — ou déposez directement sur une bande ou le viewport. Les PNG gardent leur transparence.")}),
      audio?null:r.jsx(SvmLabel,{style:{marginTop:12},children:"Images (Bibliothèque)"}),
      audio?null:(sources.images.length?
        r.jsx("div",{className:"svm-ovgrid",children:sources.images.map(function(im){
          return r.jsx("button",{className:"svm-ovimg",title:im.name+" — cliquer ou glisser",draggable:!0,
            onDragStart:function(e){dragPayload(e,{image:im.name},im.name,"image",0)},
            style:{backgroundImage:"url('/api/images/"+encodeURIComponent(im.name)+"')",backgroundSize:"cover",backgroundPosition:"center"},
            onClick:function(){addAsset({image:im.name},im.name,"image",0,tr2)}},im.name)})}):
        r.jsx("div",{className:"svm-note",children:"aucune image dans la Bibliothèque"})),
      audio?null:r.jsx(SvmLabel,{style:{marginTop:12},children:"Rendus vidéo"}),
      audio?null:(sources.videos.length?
        r.jsx("div",{className:"svm-ovlist",children:sources.videos.map(function(v3){
          return r.jsxs("button",{className:"svm-fxchip",style:{cursor:"pointer",textAlign:"left"},draggable:!0,
            title:v3.title+" — cliquer ou glisser",
            onDragStart:function(e){dragPayload(e,{job_id:v3.job_id},v3.title,"video",v3.dur)},
            onClick:function(){addAsset({job_id:v3.job_id},v3.title,"video",v3.dur,tr2)},
            children:[v3.title," · ",v3.dur?svmRuler(Math.round(v3.dur)):"—"]},v3.job_id)})}):
        r.jsx("div",{className:"svm-note",children:"aucun rendu vidéo terminé"})),
      audio?r.jsx(SvmLabel,{style:{marginTop:12},children:"Sons (Bibliothèque)"}):null,
      audio?((sources.audios&&sources.audios.length)?
        r.jsx("div",{className:"svm-ovlist",children:sources.audios.map(function(a3){
          return r.jsxs("button",{className:"svm-fxchip",style:{cursor:"pointer",textAlign:"left"},draggable:!0,
            title:a3.name+" — cliquer ou glisser",
            onDragStart:function(e){dragPayload(e,{audio:a3.name},a3.name,"audio",0)},
            onClick:function(){addAsset({audio:a3.name},a3.name,"audio",0,tr2)},
            children:[a3.name,a3.kb?" · "+a3.kb+" ko":""]},a3.name)})}):
        r.jsx("div",{className:"svm-note",children:"aucun son — importez-en un depuis la Bibliothèque"})):null,
      r.jsx("div",{className:"svm-poprow",children:
        r.jsx("button",{className:"svm-secbtn",onClick:function(){setOvPick("")},children:"Fermer"})})]})}

  /* mini-popover de jonction — règle la transition du clip de DROITE */
  function transPopover(){
    if(!transPop)return null;
    var jc=clips.find(function(k){return k.id===transPop.id});
    if(!jc||!svmLeftNeighbor(clips,jc))return null;
    var base=svmTransBase(jc.transition),isCut=base==="cut",s2=svmTransS(jc);
    return r.jsxs("div",{className:"svm-pop svm-transpop",style:{left:transPop.x},children:[
      r.jsx("div",{className:"svm-poptitle",children:"Transition de coupe"}),
      r.jsx("div",{className:"svm-transgrid",children:SVM_TRANS.map(function(o){
        return r.jsx("button",{className:"svm-transtile","data-sel":base===o[0]?"":void 0,
          title:o[1]+" ("+o[0]+")",
          onClick:function(){svmSetTransType(jc.id,o[0])},children:o[1]},o[0])})}),
      r.jsxs("div",{className:"svm-fxedit",style:{marginTop:10},children:[
        r.jsx("span",{className:"svm-fxeditname",children:"Durée"}),
        r.jsx("input",{className:"svm-range",type:"range",min:.1,max:1,step:.05,
          value:isCut?.4:s2,disabled:isCut,"aria-label":"Durée de la transition",
          onChange:function(e){svmSetTransDur(jc.id,Number(e.target.value))}}),
        r.jsx("span",{className:"svm-rangeval",children:isCut?"—":s2.toFixed(2)+" s"})]}),
      r.jsx("div",{className:"svm-poprow",children:
        r.jsx("button",{className:"svm-secbtn",style:{width:"100%"},
          title:"Copier ce réglage sur toutes les jonctions V1 (Échap ou clic extérieur pour fermer)",
          onClick:function(){svmApplyTransAll(base,isCut?0:s2)},
          children:"Appliquer à toutes les coupes"})})]})}

  /* inspecteur — transition d'entrée du clip V1 sélectionné ; le backend
     ignore celle du premier clip et des jonctions avec trou */
  function transInspector(){
    if(!sel||sel.tr!=="v1")return null;
    var left=svmLeftNeighbor(clips,sel);
    var base=svmTransBase(sel.transition),isCut=base==="cut",s2=svmTransS(sel);
    var known=SVM_TRANS.some(function(o){return o[0]===base});
    return r.jsxs("div",{className:"svm-transinsp",children:[
      r.jsx("div",{className:"svm-propk",children:"Transition"}),
      left?r.jsxs("div",{style:{display:"flex",gap:7,marginTop:6,alignItems:"center"},children:[
        r.jsx("select",{className:"svm-secbtn",style:{flex:"1 1 auto",minWidth:0,padding:"5px 8px"},
          value:base,title:"Transition avec le plan précédent","aria-label":"Type de transition",
          onChange:function(e){svmSetTransType(sel.id,e.target.value)},
          children:(known?[]:[r.jsx("option",{value:base,children:base+" (hérité)"},"_leg")])
            .concat(SVM_TRANS.map(function(o){
              return r.jsx("option",{value:o[0],children:o[1]},o[0])}))}),
        r.jsx("input",{className:"svm-transdur",type:"number",min:.1,max:1,step:.05,
          value:isCut?"":s2,disabled:isCut,
          title:"Durée de la transition (0,1 à 1 s)","aria-label":"Durée de la transition (s)",
          onChange:function(e){var v=Number(e.target.value);
            if(isFinite(v)&&v>0)svmSetTransDur(sel.id,v)}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"s"})]}):
      r.jsx("div",{className:"svm-transnone",children:"première coupe / trou — pas de transition"})]})}

  return r.jsxs("div",{className:"dzsvm svm-col",ref:rootRef,"data-svm-theme":theme==="light"?"light":void 0,children:[
    /* barre de titre */
    r.jsxs("div",{className:"svm-titlebar",children:[
      r.jsx("span",{className:"svm-title",children:"Montage"}),
      r.jsx("span",{className:"svm-projmeta",children:proj.name+" · "+proj.version+" · "+svmRuler(Math.round(dur))}),
      dirty?r.jsx("span",{className:"svm-unsaved",children:"NON ENREGISTRÉ"}):null,
      r.jsxs("div",{style:{marginLeft:"auto",display:"flex",gap:8,alignItems:"center"},children:[
        /* Format : les 4 valeurs réellement rendues par _CANVAS côté backend.
           4:5 y a été ajouté — il était proposé ailleurs dans l'app mais
           retombait silencieusement en 9:16 au rendu. */
        r.jsx("select",{className:"svm-secbtn",value:proj.ratio||"9:16",
          title:"Format de sortie",
          onChange:function(e){var v=e.target.value;
            setProj(function(p){return Object.assign({},p,{ratio:v})});
            setDirty(!0);fireNote("Format : "+v)},
          children:SVM_RATIOS.map(function(rt){
            return r.jsx("option",{value:rt[0],children:rt[1]},rt[0])})}),
        r.jsx("button",{className:"svm-secbtn",onClick:function(){setPop(pop==="preview"?"":"preview")},children:"Preview 480p (gratuit)"}),
        r.jsx("button",{className:"svm-goldbtn",onClick:function(){setPop(pop==="render"?"":"render")},children:"Rendre & publier →"}),
        r.jsx(SvmThemeChip,{theme:theme,setTheme:setTheme})]})]}),
    popover(),
    fxPicker(),
    ovPicker(),
    transPopover(),
    /* lecteur + inspecteur */
    r.jsxs("div",{className:"svm-mid",children:[
      r.jsxs("div",{className:"svm-playerzone",children:[
        note?r.jsx("div",{className:"svm-note",style:{position:"absolute",top:58,left:18,zIndex:5},children:note}):null,
        r.jsxs("div",{className:"svm-frame",ref:frameRef,
          /* le cadre suivait un aspect-ratio 9/16 figé en CSS : il suit
             désormais le format du projet */
          style:{aspectRatio:String(proj.ratio||"9:16").replace(":","/")},
          title:"Molette : zoom · double-clic : réinitialiser · déposez un asset pour l'ajouter",
          /* dépôt sur le viewport : vise la piste vidéo principale, à la
             tête de lecture (le viewport n'a pas d'axe temporel). */
          onDragOver:function(e){if(e.dataTransfer&&Array.prototype.indexOf.call(e.dataTransfer.types||[],DZ_MIME)>=0){e.preventDefault();e.dataTransfer.dropEffect="copy"}},
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
          liveOn?r.jsx("div",{className:"svm-liveov",ref:liveOvRef,
            style:{transform:"scale("+vzoom+")",transformOrigin:"center center"}}):null,
          liveOn&&!liveClip?r.jsx("div",{className:"svm-livegap",children:"trou"}):null,
          /* zones sûres (G) : tiers + centre + marges verticales 9:16 */
          safeOn?r.jsxs("div",{className:"svm-safe","aria-hidden":!0,children:[
            r.jsx("div",{className:"svm-safe3v",style:{left:"33.333%"}}),
            r.jsx("div",{className:"svm-safe3v",style:{left:"66.667%"}}),
            r.jsx("div",{className:"svm-safe3h",style:{top:"33.333%"}}),
            r.jsx("div",{className:"svm-safe3h",style:{top:"66.667%"}}),
            r.jsx("div",{className:"svm-safectr"}),
            proj.ratio==="9:16"?r.jsx("div",{className:"svm-safebox"}):null]}):null,
          vzoom>1.01?r.jsx("div",{className:"svm-frametc",style:{top:34},
            children:"×"+vzoom.toFixed(1)}):null,
          r.jsx("div",{className:"svm-caption",children:
            r.jsx("div",{className:"svm-captiontext",children:proj.demo?"« La marée ne demande pas la permission. »":proj.name})}),
          /* badge d'état du lecteur — coin opposé au timecode ; rien en démo */
          proj.demo?null:r.jsx("div",{className:"svm-frametc svm-frametr",
            title:previewUrl?"aperçu rendu 480p branché dans le lecteur"
              :"aperçu direct des sources — transitions, effets et mixage visibles après une Preview 480p",
            children:previewUrl?"aperçu 480p":"aperçu source"}),
          r.jsxs("div",{className:"svm-framebtns",children:[
            r.jsx("button",{className:"svm-framebtn",title:"plein écran (Échap pour sortir)",
              "aria-label":"Plein écran",onClick:svmFullscreen,children:"⛶"}),
            r.jsx("button",{className:"svm-framebtn","data-on":safeOn?"":void 0,
              title:"zones sûres (G)","aria-label":"Zones sûres",
              onClick:function(){setSafeOn(!safeOn)},children:"▦"})]}),
          r.jsx("div",{className:"svm-frametc",children:svmShort(ph)})]})]}),
      r.jsxs("aside",{className:"svm-insp",children:[
        r.jsx(SvmLabel,{children:"Clip sélectionné"}),
        r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:8,marginTop:9},children:[
          r.jsx("div",{className:"svm-clipname",style:{marginTop:0,flex:"1 1 auto",minWidth:0,
            whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"},children:sel?sel.label:"—"}),
          sel?r.jsx("button",{className:"svm-minibtn",title:"Supprimer le clip (Suppr)",
            "aria-label":"Supprimer "+sel.label,onClick:delClip,children:"🗑︎"}):null]}),
        r.jsx("div",{className:"svm-props",children:[
          {k:"In",v:sel?svmShort(sel.srcIn!=null?sel.srcIn:0):"—"},
          {k:"Out",v:sel?svmShort(sel.srcOut!=null?sel.srcOut:(sel.end-sel.start)):"—"},
          {k:"Vitesse",v:sel&&sel.speed?sel.speed:"100 %"}
        ].map(function(p2){return r.jsxs("div",{className:"svm-prop",children:[
          r.jsx("div",{className:"svm-propk",children:p2.k}),
          r.jsx("div",{className:"svm-propv",children:p2.v})]},p2.k)})}),
        transInspector(),
        sel&&sel.tr==="v2"&&sel.src?opacityRow():null,
        r.jsx(SvmLabel,{style:{margin:"20px 0 10px"},children:"Mixage"}),
        r.jsx("div",{className:"svm-mix",children:mixRows.map(function(m){
          return r.jsxs("div",{children:[
            r.jsxs("div",{className:"svm-mixhead",children:[
              r.jsx("span",{style:{color:"var("+m.c+")"},children:m.name}),
              r.jsx("span",{children:m.db})]}),
            r.jsx("div",{className:"svm-mixrail",role:"slider",tabIndex:0,
              title:"Glisser pour régler le niveau "+m.name+" ("+m.db+")",
              "aria-label":"Niveau "+m.name,"aria-valuemin":-40,"aria-valuemax":0,
              "aria-valuenow":m.dbNum,"aria-valuetext":m.db,
              onPointerDown:function(e){mixDown(e,m.name)},
              onKeyDown:function(e){
                var d=e.key==="ArrowLeft"||e.key==="ArrowDown"?-1:
                      e.key==="ArrowRight"||e.key==="ArrowUp"?1:0;
                if(!d)return;e.preventDefault();pushHistory();svmMixSet(m.name,m.dbNum+d)},
              children:
              r.jsx("div",{className:"svm-mixfill",style:{width:m.w+"%",background:"var("+m.c+")"}})})]},m.name)})}),
        r.jsxs("button",{className:"svm-durmaster",style:{marginTop:12},
          onClick:function(){setDucking(!ducking);setDirty(!0)},
          role:"switch","aria-checked":ducking,children:[
          r.jsx("span",{className:"svm-switch","data-off":ducking?void 0:"",children:r.jsx("span",{className:"svm-knob"})}),
          r.jsxs("div",{children:[
            r.jsx("div",{className:"svm-dmtitle",children:"Ducking auto"}),
            r.jsx("div",{className:"svm-dmhint",children:"La musique s'abaisse sous le dialogue"})]})]}),
        r.jsxs("button",{className:"svm-durmaster",onClick:function(){setDurMaster(!durMaster);setDirty(!0)},
          role:"switch","aria-checked":durMaster,children:[
          r.jsx("span",{className:"svm-switch","data-off":durMaster?void 0:"",children:r.jsx("span",{className:"svm-knob"})}),
          r.jsxs("div",{children:[
            r.jsx("div",{className:"svm-dmtitle",children:"Maître de durée"}),
            r.jsx("div",{className:"svm-dmhint",children:"La voix off ne sera jamais coupée"})]})]}),
        r.jsx(SvmLabel,{style:{margin:"20px 0 10px"},children:"Effets sur ce clip"}),
        r.jsxs("div",{className:"svm-fxchips",children:[
          (sel&&sel.fx?sel.fx:[]).map(function(f){
            return r.jsx("span",{className:"svm-fxchip","data-c":f.c,children:f.n},f.n)}),
          (sel&&sel.effects?sel.effects:[]).map(function(f,fi){
            var lbl=(fxCat&&fxCat[f.type]&&fxCat[f.type].label)||f.type;
            var editing=fxEdit&&fxEdit.id===sel.id&&fxEdit.i===fi;
            return r.jsx("button",{className:"svm-fxchip","data-c":"c3d",
              title:"Régler / retirer l'effet",
              style:{cursor:"pointer",borderColor:editing?"var(--accent)":void 0},
              onClick:function(){
                setFxEdit(editing?null:{id:selRef.current,i:fi})},
              children:lbl},f.type+fi)}),
          r.jsx("button",{className:"svm-fxadd",
            onClick:function(){
              if(!sel||!sel.src){fireNote("Effets par clip : disponibles sur les clips réels (Bibliothèque) — la démo reste une maquette.");return}
              if(!fxCat){fireNote("Catalogue d'effets indisponible — backend à relancer ?");return}
              setFxPick(!fxPick)},
            children:"+ effet"})]}),
        fxEditRow()]})]}),
    /* timeline */
    r.jsxs("div",{className:"svm-tl",children:[
      r.jsxs("div",{className:"svm-trans",children:[
        r.jsx("span",{className:"svm-tcmain",children:svmTc(ph)}),
        playing&&spd!==1?r.jsx("span",{className:"svm-spdchip",
          title:"vitesse de lecture (J / L, K pour pause)",
          children:(spd<0?"◀ ×":"×")+Math.abs(spd)}):null,
        r.jsxs("div",{className:"svm-transbtns",children:[
          r.jsx("button",{className:"svm-tbtn",title:"Coupe précédente (↑)",onClick:function(){jump(-1)},children:"◀◀"}),
          r.jsx("button",{className:"svm-tbtn",title:"Image précédente (←)","aria-label":"Reculer d'une image",
            onClick:function(){seekTo(Math.max(0,phRef.current-1/30))},children:"|◀"}),
          r.jsx("button",{className:"svm-tbtn svm-gold",title:playing?"Pause (Espace · K)":"Lecture (Espace · L)",
            onClick:function(){setSpd(1);setPlaying(!playing)},children:playing?"▮▮":"▶"}),
          r.jsx("button",{className:"svm-tbtn",title:"Image suivante (→)","aria-label":"Avancer d'une image",
            onClick:function(){seekTo(Math.min(durRef.current,phRef.current+1/30))},children:"▶|"}),
          r.jsx("button",{className:"svm-tbtn",title:"Coupe suivante (↓)",onClick:function(){jump(1)},children:"▶▶"})]}),
        r.jsxs("div",{className:"svm-transbtns",children:[
          r.jsx("button",{className:"svm-tbtn",title:"Annuler (Ctrl+Z)","aria-label":"Annuler",
            "data-off":histRef.current.u.length?void 0:"",onClick:undo,children:"↶"}),
          r.jsx("button",{className:"svm-tbtn",title:"Rétablir (Ctrl+Y)","aria-label":"Rétablir",
            "data-off":histRef.current.r.length?void 0:"",onClick:redo,children:"↷"})]}),
        r.jsxs("div",{className:"svm-toolchips",children:[
          r.jsx("button",{className:"svm-toolchip","data-on":snap?"":void 0,
            title:"aimanter les bords, la tête et 0 (N)",onClick:function(){setSnap(!snap)},children:"aimanter"}),
          r.jsx("button",{className:"svm-toolchip",title:"couper le clip sélectionné à la tête (Alt+C)",onClick:blade,children:"lame ⌥C"}),
          r.jsx("button",{className:"svm-toolchip","data-on":ripple?"":void 0,
            title:"refermer les trous — suppression et rognage droit sur V1 (R)",onClick:function(){setRipple(!ripple)},children:"ripple"})]}),
        r.jsxs("span",{className:"svm-zoom",
          title:"Ctrl+molette : zoom continu centré sur le curseur · Ctrl+= / Ctrl+- : crans · Shift+Z : 100 %",
          children:["zoom ",
          ["▁","▂","▃","▅"].map(function(g,i){
            return r.jsx("button",{className:"svm-zoomstep","data-on":Math.round(zoomPct)===SVM_ZOOMW[i]?"":void 0,
              title:"zoom "+SVM_ZOOMW[i]+" % (Ctrl+molette : continu)",onClick:function(){zoomApply(SVM_ZOOMW[i])},children:g},i)}),
          " "+Math.round(zoomPct)+" % · "+svmRuler(Math.round(dur))+" total"]})]}),
      r.jsx("div",{className:"svm-scroll",ref:tlScrollRef,children:
        r.jsxs("div",{className:"svm-lanes",style:{width:zoomPct+"%"},children:[
          r.jsxs("div",{className:"svm-ruler",onPointerDown:rulerDown,
            onPointerMove:rulerHover,onPointerLeave:rulerLeave,children:[
            r.jsx("div",{className:"svm-gutter"}),
            ticks.map(function(t3){return r.jsx("div",{className:"svm-tick",children:svmRuler(t3)},t3)})]}),
          SVM_TRACKS.map(function(tr){
            return r.jsxs("div",{className:"svm-track",style:{height:tr.h},children:[
              r.jsxs("div",{className:"svm-thead",children:[
                r.jsxs("div",{className:"svm-tnamerow",children:[
                  r.jsx("span",{className:"svm-sq6",style:{background:"var("+tr.c+")"}}),
                  r.jsx("span",{className:"svm-tname",children:tr.name}),
                  r.jsx("button",{className:"svm-ovadd",
                    title:trackKind(tr.id)==="audio"
                      ?"Ajouter un son de la Bibliothèque à la tête de lecture"
                      :"Ajouter une image ou un rendu à la tête de lecture",
                    onClick:function(){openPicker(tr.id)},children:"+"})]}),
                r.jsx("div",{className:"svm-ttype",children:tr.type})]}),
              r.jsxs("div",{className:"svm-lane",
                onDragOver:function(e){if(e.dataTransfer&&Array.prototype.indexOf.call(e.dataTransfer.types||[],DZ_MIME)>=0){e.preventDefault();e.dataTransfer.dropEffect="copy"}},
                onDrop:function(e){dropOnTrack(e,tr.id,e.currentTarget)},
                children:[
                tr.id==="v1"?svmV1Gaps(clips,dur):null,
                clips.filter(function(c){return c.tr===tr.id}).map(function(c){
                  var isSel=c.id===selId;
                  return r.jsxs("div",{className:"svm-clip",
                    style:{left:c.start/dur*100+"%",width:(c.end-c.start)/dur*100+"%",
                      borderColor:isSel?"var(--accent)":"color-mix(in srgb, var("+tr.c+") 53%, transparent)",
                      background:isSel?"color-mix(in srgb, var(--accent) 20%, transparent)":"color-mix(in srgb, var("+tr.c+") "+tr.mix+"%, transparent)"},
                    onPointerDown:function(e){clipDown(e,c,e.currentTarget.parentElement)},
                    /* curseur explicite : sans lui, rien n'indique que les
                       bords rognent au lieu de déplacer */
                    onPointerMove:function(e){
                      if(e.buttons)return;
                      var el=e.currentTarget;
                      el.style.cursor=svmEdgeAt(e.clientX,el.getBoundingClientRect())==="m"?"grab":"col-resize"},
                    title:c.label+" — bords : rogner / allonger · centre : déplacer",
                    children:[
                      r.jsx("div",{className:"svm-cliplabel",children:c.label}),
                      /* poignées visibles sur le clip sélectionné */
                      isSel?r.jsx("div",{style:{position:"absolute",left:0,top:0,bottom:0,width:4,
                        background:"var(--accent)",borderRadius:"3px 0 0 3px",pointerEvents:"none"}}):null,
                      isSel?r.jsx("div",{style:{position:"absolute",right:0,top:0,bottom:0,width:4,
                        background:"var(--accent)",borderRadius:"0 3px 3px 0",pointerEvents:"none"}}):null]},c.id)}),
                /* jonctions V1 : étendue de la transition + losange de réglage */
                tr.id==="v1"?svmV1Junctions(clips).map(function(j2){
                  var on=svmTransBase(j2.right.transition)!=="cut";
                  var s2=on?svmTransS(j2.right):0;
                  return r.jsxs(r.Fragment,{children:[
                    on?r.jsx("div",{className:"svm-transspan",
                      style:{left:(j2.t-s2/2)/dur*100+"%",width:s2/dur*100+"%"}}):null,
                    r.jsx("button",{className:"svm-junc",
                      "data-on":on?"":void 0,
                      "data-sel":transPop&&transPop.id===j2.right.id?"":void 0,
                      style:{left:"calc("+j2.t/dur*100+"% - 5px)"},
                      title:"Transition : "+svmTransLabel(j2.right.transition)+(on?" · "+s2.toFixed(2)+" s":"")+" — cliquer pour régler",
                      "aria-label":"Transition entre "+j2.left.label+" et "+j2.right.label,
                      onPointerDown:function(e){e.stopPropagation()},
                      onClick:function(e){e.stopPropagation();openTransPop(j2.right.id,e)}})]},"jx"+j2.right.id)}):null]})]},tr.id)}),
          snapT!=null?r.jsx("div",{className:"svm-snapline",style:{left:"calc(88px + (100% - 88px) * "+(snapT/dur)+")"}}):null,
          r.jsx("div",{className:"svm-phline",style:{left:"calc(88px + (100% - 88px) * "+phFrac+")"}}),
          r.jsx("div",{className:"svm-phtri",style:{left:"calc(88px + (100% - 88px) * "+phFrac+")"}}),
          r.jsx("div",{className:"svm-hovertc",ref:hoverTcRef})]})})]})]})}
