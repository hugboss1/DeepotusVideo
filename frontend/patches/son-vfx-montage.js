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
/* musique A2 réelle (bouclée au rendu) — même règle que le backend : PREMIÈRE
   occurrence a2 avec source dans l'ordre des clips ; son fade_out = fondu de
   fin de rendu */
function svmFirstA2Id(cs){for(var i=0;i<cs.length;i++){var c=cs[i];
  if(c.tr==="a2"&&c.src&&(c.src.audio||c.src.job_id))return c.id}
  return null}
function svmDbTxt(g){return g>0?"+"+g+" dB":g<0?"−"+Math.abs(g)+" dB":"0 dB"}
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
        var ch=ab.getChannelData(0),
            n=Math.max(90,Math.min(720,Math.round(ab.duration*12))),
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
  if(!c||(c.x==null&&c.y==null&&c.scale==null&&c.rotate==null))return null;
  function n(v,d){v=Number(v);return isFinite(v)?v:d}
  return {x:Math.min(1.2,Math.max(-.2,n(c.x,.5))),
          y:Math.min(1.2,Math.max(-.2,n(c.y,.5))),
          scale:Math.min(3,Math.max(.05,n(c.scale,1))),
          rotate:Math.min(180,Math.max(-180,n(c.rotate,0)))}}
/* application impérative sur une couche live — même géométrie que le rendu
   ffmpeg : largeur = scale·canvas, hauteur auto, centre posé en left/top %,
   rotation autour du centre ; tf null = retour au cover plein cadre */
function svmApplyTf(el,tf){
  if(tf){el.setAttribute("data-svmtf","");
    el.style.left=tf.x*100+"%";el.style.top=tf.y*100+"%";
    el.style.width=tf.scale*100+"%";
    el.style.transform="translate(-50%,-50%) rotate("+tf.rotate+"deg)"}
  else{el.removeAttribute("data-svmtf");
    el.style.left="";el.style.top="";el.style.width="";el.style.transform=""}}

/* ── panneau « Raccourcis clavier » (?) — données statiques. Honnêteté :
   raccourcis FIXES de l'éditeur, aucun remappage n'existe et le panneau ne le
   prétend pas. Chaque ligne : [touches (chips <kbd>), libellé]. */
var SVM_KEYS=[
 ["Lecture",[
  [["Espace"],"lecture / pause"],
  [["J","K","L"],"arrière · pause · avant (×1 ×2 ×4)"],
  [["←","→"],"reculer / avancer d'1 image"],
  [["Maj","←","→"],"±10 images"],
  [["↑","↓"],"coupe précédente / suivante"],
  [["Home","End"],"début / fin"],
  [["F"],"plein écran du cadre"],
  [["G"],"zones sûres (tiers, centre, marges)"]]],
 ["Montage",[
  [["Suppr"],"supprimer le clip sélectionné"],
  [["Alt","C"],"lame — couper à la tête"],
  [["Ctrl","Z"],"annuler"],
  [["Ctrl","Y"],"rétablir"],
  [["N"],"aimanter (bords, tête, 0)"],
  [["R"],"ripple — refermer les trous"],
  [["bord de clip"],"glisser : rogner / allonger"]]],
 ["Affichage",[
  [["Ctrl","molette"],"zoom continu sur le curseur"],
  [["Ctrl","+","−"],"crans de zoom"],
  [["Maj","Z"],"zoom 100 %"],
  [["T"],"panneau Narration (texte → voix)"],
  [["?"],"ouvrir / fermer ce panneau"]]]];

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
  var stVS=x.useState(null),prevSaved=stVS[0],setPrevSaved=stVS[1]; /* dernier aperçu 480p rendu — chip qualité source/480p */
  var stF=x.useState(null),fxCat=stF[0],setFxCat=stF[1]; /* catalogue Effects/Mask */
  var stFP=x.useState(!1),fxPick=stFP[0],setFxPick=stFP[1];
  var stFE=x.useState(null),fxEdit=stFE[0],setFxEdit=stFE[1]; /* {id,i} chip en édition */
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
  /* muet / verrou par piste — {trId:{pm:dB d'avant muet, l:verrou}} ; le
     muet lui-même se lit dans proj.mixDb (bus ≤ −40 dB), source de vérité */
  var stTS=x.useState({}),trackSt=stTS[0],setTrackSt=stTS[1];
  var trackStRef=x.useRef(trackSt);trackStRef.current=trackSt;
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
  var narrToggle=x.useCallback(function(){
    setNarrOn(function(v){var nv=!v;
      try{localStorage.setItem("dz_narr_open",nv?"1":"0")}catch(_e){}
      return nv})},[]);
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
  /* suppression d'un clip (id explicite : Suppr, inspecteur, blocs de
     narration) — ripple actif : les clips SUIVANTS de la même piste remontent
     de la longueur du trou (piste principale magnétique) */
  var delClipById=x.useCallback(function(id){
    var cs=clipsRef.current;
    var c=cs.find(function(k){return k.id===id});
    if(!c)return;
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){
      fireNote("Piste "+c.tr.toUpperCase()+" verrouillée — déverrouillez-la pour supprimer.");return}
    pushHistory();
    var len=c.end-c.start;
    var next=cs.filter(function(k){return k.id!==id});
    if(rippleRef.current)next=next.map(function(k){
      return k.tr===c.tr&&k.start>=c.end-.001?
        Object.assign({},k,{start:k.start-len,end:k.end-len}):k});
    setClips(next);setSelId("");setDirty(!0);
    fireNote("« "+c.label+" » supprimé"+(rippleRef.current?" — trou refermé (ripple)":""))},[fireNote,pushHistory]);
  var delClip=x.useCallback(function(){delClipById(selRef.current)},[delClipById]);

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
  var firstA2=svmFirstA2Id(clips); /* clip musique bouclée (fade_out = fin de rendu) */

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
      /* muet pendant le scrub — le son du plan en lecture ; muet aussi quand
         le bus dialogue (A1 = le son du plan au rendu) est coupé */
      var a1cut=Number(mixRef.current&&mixRef.current.dialogue!=null?mixRef.current.dialogue:0)<=-40;
      lv.muted=!run||a1cut;
      /* gain PAR CLIP du dialogue actif (clip A1 sous la tête) — approximation
         honnête du « son du plan » : volume = 10^(gain/20), borné 0..1 */
      var a1g=0;
      for(var i4=0;i4<cs.length;i4++){var kg=cs[i4];
        if(kg.tr==="a1"&&kg.src&&kg.gain&&kg.start<=t&&t<kg.end){a1g=kg.gain;break}}
      var vol=a1g?Math.min(1,Math.max(0,Math.pow(10,a1g/20))):1;
      if(lv.volume!==vol)lv.volume=vol;
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
        if(tfRoRef.current)tfRoRef.current.unobserve(ch);
        ov.removeChild(ch)}}
    Object.keys(act).forEach(function(id){
      var k=act[id],el=null;
      for(var i2=0;i2<ov.children.length;i2++){
        if(ov.children[i2]._svmId===id){el=ov.children[i2];break}}
      if(!el){var it2=livePoolGet(k.src,"o");el=it2.el;
        el._svmId=id;el._svmKey=livePoolKey(k.src,"o");ov.appendChild(el);
        if(tfRoRef.current)tfRoRef.current.observe(el)}
      el.style.opacity=k.opacity==null?"":String(k.opacity);
      /* sélection + manipulation directe : la couche est saisissable ; la
         transformation du clip (ou du geste en cours) est appliquée ici,
         garde de signature — aucune écriture DOM quand rien ne change */
      if(!el._svmTtl){el._svmTtl=1;
        el.title="Overlay — glisser : déplacer · poignées : échelle / rotation · double-clic : plein cadre"}
      el.onpointerdown=ovOvDown;el.ondblclick=ovOvDbl;
      var ktf=dragTfRef.current&&dragTfRef.current.id===id?dragTfRef.current:svmOvTfOf(k);
      var tsig=ktf?ktf.x+"|"+ktf.y+"|"+ktf.scale+"|"+ktf.rotate:"";
      if(el._svmTfSig!==tsig){el._svmTfSig=tsig;svmApplyTf(el,ktf)}
      if(el.tagName==="VIDEO"){
        el.muted=!0; /* un overlay ne porte jamais le son */
        var wt2=(k.srcIn||0)+(t-k.start);
        if(run){
          if(el.playbackRate!==s)el.playbackRate=s;
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
        o.el._svmVuSrc=null;o.el._svmVuAn=null;o.el._svmVuErr=1}});
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
      return an}
    catch(_e){el._svmVuErr=1;return null}}
  x.useEffect(function(){
    if(!playing)return;
    var cv=vuRef.current;if(!cv)return;
    var g;try{g=cv.getContext("2d")}catch(_e){g=null}
    if(!g)return;
    var dpr=Math.min(2,window.devicePixelRatio||1),
        W=Math.round(60*dpr),H=Math.round(10*dpr),bh=Math.round(4*dpr);
    if(cv.width!==W)cv.width=W;
    if(cv.height!==H)cv.height=H;
    var col=(getComputedStyle(cv).getPropertyValue("--green")||"").trim()||"#5ec8a0";
    var raf=0,buf=null,pk=0,pkAt=0;
    function lvlOf(v){ /* −42..0 dBFS → 0..1 */
      if(!(v>0))return 0;
      var db=20*Math.log(v)/Math.LN10;
      return Math.max(0,Math.min(1,(db+42)/42))}
    function step(now){
      raf=requestAnimationFrame(step);
      var el=previewRef.current?videoRef.current:liveVideoRef.current;
      var an=el&&!el.muted?svmVuWire(el):null,rms=0,mx2=0;
      if(an){
        if(!buf||buf.length!==an.fftSize)buf=new Uint8Array(an.fftSize);
        an.getByteTimeDomainData(buf);
        var s=0;
        for(var i=0;i<buf.length;i++){var v=(buf[i]-128)/128;s+=v*v;
          var a2=v<0?-v:v;if(a2>mx2)mx2=a2}
        rms=Math.sqrt(s/buf.length)}
      var lvl=lvlOf(rms),pv=lvlOf(mx2);
      if(pv>=pk||now-pkAt>900){pk=pv;pkAt=now} /* crête tenue 0,9 s */
      g.clearRect(0,0,W,H);
      g.fillStyle=col;
      g.globalAlpha=.22;g.fillRect(0,0,W,bh);g.fillRect(0,H-bh,W,bh); /* rails fantômes */
      var w=Math.round(lvl*W);
      if(w>0){g.globalAlpha=.9;g.fillRect(0,0,w,bh);g.fillRect(0,H-bh,w,bh)}
      if(pk>0){var px2=Math.min(W-1,Math.max(1,Math.round(pk*W)-1)),
          pw=Math.max(1,Math.round(dpr));
        g.globalAlpha=1;g.fillRect(px2,0,pw,bh);g.fillRect(px2,H-bh,pw,bh)}
      g.globalAlpha=1}
    raf=requestAnimationFrame(step);
    return function(){if(raf)cancelAnimationFrame(raf)}},[playing,previewUrl]);
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
    var tf=dragTfRef.current&&dragTfRef.current.id===id?dragTfRef.current:svmOvTfOf(k);
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
    var t0=svmOvTfOf(k)||{x:.5,y:.5,scale:1,rotate:0};
    var h0={clips:clipsRef.current,mixDb:mixRef.current};
    var x0=e.clientX,y0=e.clientY,moved=!1,fired=!1;
    var cur={id:k.id,x:t0.x,y:t0.y,scale:t0.scale,rotate:t0.rotate};
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
      if(el2){var tsig=cur.x+"|"+cur.y+"|"+cur.scale+"|"+cur.rotate;
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
      if(moved){setDirty(!0);pushHistory(h0);
        var p={x:Math.round(cur.x*1e4)/1e4,y:Math.round(cur.y*1e4)/1e4,
               scale:Math.round(cur.scale*1e4)/1e4,
               rotate:Math.round(cur.rotate*10)/10};
        setClips(clipsRef.current.map(function(c2){
          return c2.id===cur.id?Object.assign({},c2,p):c2}))}
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
    if(trackStRef.current.v2&&trackStRef.current.v2.l)return; /* verrou : sélection seule */
    if(e.button!==0)return;
    ovGesture("move",e,k)}
  function ovOvDbl(e){
    var id=e.currentTarget._svmId,cs=clipsRef.current,k=null,i;
    for(i=0;i<cs.length;i++){if(cs[i].id===id){k=cs[i];break}}
    /* overlay plein cadre : rien à réinitialiser, le double-clic du cadre
       (remise à zéro du zoom) garde la main */
    if(!k||!svmOvTfOf(k))return;
    if(trackStRef.current.v2&&trackStRef.current.v2.l)return;
    e.stopPropagation();e.preventDefault();
    svmOvTfReset(id)}
  function ovHandleDown(e,mode){
    var id=selRef.current,cs=clipsRef.current,k=null,i;
    for(i=0;i<cs.length;i++){if(cs[i].id===id){k=cs[i];break}}
    if(!k||k.tr!=="v2"||!k.src)return;
    if(trackStRef.current.v2&&trackStRef.current.v2.l)return;
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
    if(!k||!svmOvTfOf(k))return;
    pushHistory();
    setClips(cs.map(function(c2){
      if(c2.id!==id)return c2;
      var nk=Object.assign({},c2);
      delete nk.x;delete nk.y;delete nk.scale;delete nk.rotate;
      return nk}));
    setDirty(!0);
    fireNote("Overlay réinitialisé — plein cadre (cover).")}

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
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){
      fireNote("Piste "+c.tr.toUpperCase()+" verrouillée — la lame est bloquée.");return}
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
      /* panneau raccourcis : ? (Maj+/ sur AZERTY produit aussi "?") ; ouvert,
         il ne garde que Échap et ? — les autres raccourcis dorment sous le voile */
      if(k==="?"){e.preventDefault();setKbOn(function(v){return !v});return}
      if(kbRef.current){if(k==="Escape"){e.preventDefault();setKbOn(!1)}return}
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
      /* tête de lecture : ±1 image (1/30 s), Maj = ±10 images — arrondi
         image-exact : FF bouge d'exactement ±1/±10 dans le timecode */
      if(k==="ArrowLeft"||k==="ArrowRight"){e.preventDefault();
        var stp=(e.shiftKey?10:1)*(k==="ArrowLeft"?-1:1);
        seekTo(Math.min(durRef.current,Math.max(0,Math.round(phRef.current*30+stp)/30)));return}
      if(k==="ArrowUp"){e.preventDefault();jump(-1);return}
      if(k==="ArrowDown"){e.preventDefault();jump(1);return}
      if(k==="Home"){e.preventDefault();seekTo(0);return}
      if(k==="End"){e.preventDefault();seekTo(durRef.current);return}
      if(e.shiftKey&&(k==="z"||k==="Z")){e.preventDefault();zoomApply(100);return}
      if(!e.shiftKey&&!e.altKey&&(k==="n"||k==="N")){setSnap(function(s){return !s});return}
      if(!e.shiftKey&&!e.altKey&&(k==="r"||k==="R")){setRipple(function(v){return !v});return}
      /* T : tiroir Narration (blocs texte liés aux clips A1) */
      if(!e.shiftKey&&!e.altKey&&(k==="t"||k==="T")){narrToggle();return}
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
      /* F : plein écran du cadre (miroir du bouton de la barre du lecteur) */
      if(!e.shiftKey&&!e.altKey&&(k==="f"||k==="F")){e.preventDefault();svmFullscreen();return}
    }
    window.addEventListener("keydown",onKey);
    return function(){window.removeEventListener("keydown",onKey)}},[blade,delClip,undo,redo,jump,seekTo,zoomApply,narrToggle]);

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
    e.stopPropagation();setSelId(c.id);
    /* piste verrouillée : la sélection reste possible, tout geste est bloqué */
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l)return;
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
      return nk}));
    setDirty(!0)}
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
      fireNote(trId.toUpperCase()+" réactivée — bus "+bus+" à "+(back===0?"0 dB":"−"+Math.abs(Math.round(back))+" dB")+".")}
    else{
      setTrackSt(function(m){var nm=Object.assign({},m);
        nm[trId]=Object.assign({},nm[trId],{pm:cur});return nm});
      svmMixSet(bus,-40);
      fireNote(trId.toUpperCase()+" muette — bus "+bus+" à −40 dB dans le mixage.")}}
  function svmTrackLock(trId){
    var was=!!(trackSt[trId]&&trackSt[trId].l);
    setTrackSt(function(m){var nm=Object.assign({},m);
      nm[trId]=Object.assign({},nm[trId],{l:!was});return nm});
    fireNote("Piste "+trId.toUpperCase()+(was?" déverrouillée."
      :" verrouillée — déplacement, rognage, dépôt et suppression bloqués."))}

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

  /* ── ajout d'assets depuis la Bibliothèque, sur n'importe quelle piste ──
     ovPick vaut "" (fermé) ou l'identifiant de la piste visée. Les sources
     proposées suivent le type de la piste : une piste audio ne doit pas
     proposer d'images, une piste vidéo ne doit pas proposer de .mp3. */
  function trackKind(trId){return String(trId||"").charAt(0)==="a"?"audio":"video"}
  function openPicker(trId){
    if(proj.demo){fireNote("Ajout d'assets : disponible sur un projet réel — la démo reste une maquette.");return}
    if(trackSt[trId]&&trackSt[trId].l){
      fireNote("Piste "+trId.toUpperCase()+" verrouillée — déverrouillez-la pour ajouter.");return}
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
    if(trackStRef.current[tr2]&&trackStRef.current[tr2].l){
      fireNote("Piste "+tr2.toUpperCase()+" verrouillée — déverrouillez-la pour ajouter.");return}
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
        var o={tr:c.tr,src:c.src,start:c.start,end:c.end,srcIn:c.srcIn||0,
          transition:c.transition||"cut",transition_s:c.transition_s||0,
          effects:c.effects&&c.effects.length?c.effects:void 0,
          opacity:c.opacity};
        /* mixage par clip (pistes audio) — joint seulement si non nul :
           un projet sans réglage envoie exactement le payload d'avant */
        if(trackKind(c.tr)==="audio"){
          if(c.gain)o.gain=c.gain;
          if(c.fade_in)o.fade_in=c.fade_in;
          if(c.fade_out)o.fade_out=c.fade_out}
        /* transformation d'overlay (V2) — l'échelle matérialise l'état
           « transformé » (même à 100 %), x/y/rotate joints seulement hors
           défaut ; un overlay jamais touché envoie le payload d'avant */
        if(c.tr==="v2"){
          var tf=svmOvTfOf(c);
          if(tf){o.scale=tf.scale;
            if(Math.abs(tf.x-.5)>1e-4)o.x=tf.x;
            if(Math.abs(tf.y-.5)>1e-4)o.y=tf.y;
            if(Math.abs(tf.rotate)>=.05)o.rotate=tf.rotate}}
        return o})}}
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
            var pu="/api/jobs/"+job.id+"/video?t="+Date.now();
            setPreviewUrl(pu);setPrevSaved(pu); /* la chip qualité peut re-brancher ce rendu */
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

  /* inspecteur — « Overlay » (clip V2 sélectionné) : position / échelle /
     rotation / opacité. Même source de vérité que la manipulation directe
     dans le lecteur (champs du clip), une entrée d'historique par rafale de
     600 ms — cohérent avec la durée de transition et le mixage par clip. */
  function ovInspector(){
    if(!sel||sel.tr!=="v2"||!sel.src)return null;
    var tf=svmOvTfOf(sel);
    var t=tf||{x:.5,y:.5,scale:1,rotate:0};
    var vOp=Math.round((sel.opacity==null?1:sel.opacity)*100);
    function fieldNum(props){
      return r.jsx("input",Object.assign({className:"svm-transdur",type:"number"},props))}
    return r.jsxs("div",{className:"svm-transinsp",children:[
      r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:7},children:[
        r.jsx("div",{className:"svm-propk",style:{flex:"1 1 auto"},children:"Overlay"}),
        tf?r.jsx("button",{className:"svm-minibtn",
          title:"Revenir au plein cadre (équivaut au double-clic sur l'overlay dans le lecteur)",
          onClick:function(){svmOvTfReset(selRef.current)},children:"plein cadre"}):null]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:"Position"}),
        fieldNum({min:0,max:100,step:1,value:Math.round(t.x*100),
          title:"X du centre en % du canvas (50 = centré)","aria-label":"Position X (%)",
          onChange:function(e){var v=Number(e.target.value);
            if(isFinite(v))svmOvTfField({x:Math.min(1.2,Math.max(-.2,v/100))})}}),
        r.jsx("span",{className:"svm-fadesep","aria-hidden":!0,children:"x · y"}),
        fieldNum({min:0,max:100,step:1,value:Math.round(t.y*100),
          title:"Y du centre en % du canvas (50 = centré)","aria-label":"Position Y (%)",
          onChange:function(e){var v=Number(e.target.value);
            if(isFinite(v))svmOvTfField({y:Math.min(1.2,Math.max(-.2,v/100))})}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"%"})]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:"Échelle"}),
        fieldNum({min:5,max:300,step:1,value:Math.round(t.scale*100),
          title:"Largeur de l'overlay en % de celle du canvas (100 = pleine largeur)",
          "aria-label":"Échelle (%)",
          onChange:function(e){var v=Number(e.target.value);
            if(isFinite(v)&&v>0)svmOvTfField({scale:Math.min(3,Math.max(.05,v/100))})}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"%"})]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:"Rotation"}),
        fieldNum({min:-180,max:180,step:1,value:Math.round(t.rotate*10)/10,
          title:"Rotation en degrés (−180 à 180) — aimant 0 / ±45 / 90 dans le lecteur",
          "aria-label":"Rotation (degrés)",
          onChange:function(e){var v=Number(e.target.value);
            if(isFinite(v))svmOvTfField({rotate:Math.min(180,Math.max(-180,v))})}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"°"})]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:"Opacité"}),
        r.jsx("input",{className:"svm-range",type:"range",min:10,max:100,step:5,value:vOp,
          title:"Opacité de l'overlay ("+vOp+" %)","aria-label":"Opacité de l'overlay",
          onChange:function(e){var nv=Number(e.target.value)/100;var id=selRef.current;
            var now=Date.now();
            if(now-ovHistAt.current>600)pushHistory();
            ovHistAt.current=now;
            setClips(clipsRef.current.map(function(k){return k.id===id?Object.assign({},k,{opacity:nv>=1?void 0:nv}):k}));
            setDirty(!0)}}),
        r.jsx("span",{className:"svm-rangeval",children:vOp+" %"})]}),
      tf?null:r.jsx("div",{className:"svm-transnone",
        children:"plein cadre (cover) — saisissez l'overlay dans le lecteur pour le déplacer, le redimensionner ou le tourner"})]})}

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

  /* panneau « Raccourcis clavier » — modal centré (motif .svm-pop, z 20),
     voile léger, fermé par Échap, clic extérieur ou le bouton ; ouvert par ?
     ou le bouton « ? » discret en fin de transport */
  function kbPanel(){
    if(!kbOn)return null;
    return r.jsx("div",{className:"svm-kbscrim",onClick:function(){setKbOn(!1)},children:
      r.jsxs("div",{className:"svm-pop svm-kbpop",role:"dialog","aria-modal":!0,
        "aria-label":"Raccourcis clavier",
        onClick:function(e){e.stopPropagation()},children:[
        r.jsx("div",{className:"svm-poptitle",children:"Raccourcis clavier"}),
        r.jsx("div",{className:"svm-kbsub",children:"Raccourcis fixes de l'éditeur — Échap ou clic à l'extérieur pour fermer."}),
        r.jsx("div",{className:"svm-keys",children:SVM_KEYS.map(function(sec){
          return r.jsxs("div",{className:"svm-keysec",children:[
            r.jsx(SvmLabel,{children:sec[0]}),
            sec[1].map(function(row,i2){
              return r.jsxs("div",{className:"svm-keyrow",children:[
                r.jsx("span",{className:"svm-kbds",children:row[0].map(function(kk,i3){
                  return r.jsx("kbd",{children:kk},i3)})}),
                r.jsx("span",{className:"svm-keylbl",children:row[1]})]},i2)})]},sec[0])})}),
        r.jsx("div",{className:"svm-poprow",children:
          r.jsx("button",{className:"svm-secbtn",onClick:function(){setKbOn(!1)},children:"Fermer"})})]})})}

  /* mini-popover de jonction — règle la transition du clip de DROITE */
  function transPopover(){
    if(!transPop)return null;
    var jc=clips.find(function(k){return k.id===transPop.id});
    if(!jc||!svmLeftNeighbor(clips,jc))return null;
    var base=svmTransBase(jc.transition),isCut=base==="cut",s2=svmTransS(jc);
    return r.jsxs("div",{className:"svm-pop svm-transpop",style:{left:transPop.x},children:[
      r.jsx("div",{className:"svm-poptitle",children:"Transition de coupe"}),
      r.jsx("div",{className:"svm-transgrid",children:SVM_TRANS.map(function(o){
        return r.jsxs("button",{className:"svm-transtile","data-sel":base===o[0]?"":void 0,
          title:o[1]+" ("+o[0]+")",
          onClick:function(){svmSetTransType(jc.id,o[0])},children:[
          /* micro-scène A/B — aperçu animé du type ; la tuile sélectionnée est
             figée sur l'état final, reduced-motion la rend statique */
          r.jsxs("span",{className:"svm-tprev","data-tt":o[0],"aria-hidden":!0,children:[
            r.jsx("i",{className:"svm-ta"}),r.jsx("i",{className:"svm-tb"})]}),
          r.jsx("span",{className:"svm-ttl",children:o[1]})]},o[0])})}),
      r.jsxs("div",{className:"svm-fxedit",style:{marginTop:10},children:[
        r.jsx("span",{className:"svm-fxeditname",children:"Durée"}),
        r.jsx("span",{className:"svm-transbound","aria-hidden":!0,children:"0.1 s"}),
        r.jsx("input",{className:"svm-range",type:"range",min:.1,max:1,step:.05,
          value:isCut?.4:s2,disabled:isCut,"aria-label":"Durée de la transition",
          onChange:function(e){svmSetTransDur(jc.id,Number(e.target.value))}}),
        r.jsx("span",{className:"svm-transbound","aria-hidden":!0,children:"1.0 s"}),
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

  /* inspecteur — « Clip audio » : gain −24..+12 dB (multiplié au gain de bus
     par le rendu, jamais un remplacement) + fondus 0..3 s bornés à la moitié
     du clip ; la musique A2 bouclée garde sa note dédiée */
  function audioInspector(){
    if(!sel||trackKind(sel.tr)!=="audio"||!sel.src)return null;
    var g=Math.round(Number(sel.gain)||0);
    var len=Math.max(.2,sel.end-sel.start),fmax=Math.min(3,Math.floor(len*5)/10);
    var isMus=sel.id===firstA2;
    function setF(key,raw){
      var v=Number(raw);if(!isFinite(v))return;
      v=Math.max(0,Math.min(fmax,Math.round(v*10)/10));
      var patch={};patch[key]=v;
      svmSetClipAudio(sel.id,patch)}
    return r.jsxs("div",{className:"svm-transinsp",children:[
      r.jsx("div",{className:"svm-propk",children:"Clip audio"}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",children:"Gain"}),
        r.jsx("input",{className:"svm-range",type:"range",min:-24,max:12,step:1,value:g,
          title:"Gain du clip ("+svmDbTxt(g)+") — multiplié avec le bus "+(SVM_TRACK_BUS[sel.tr]||"")+" · flèches : ±1 dB",
          "aria-label":"Gain du clip audio (dB)",
          onChange:function(e){svmSetClipAudio(selRef.current,{gain:Math.round(Number(e.target.value))||0})}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:44},children:svmDbTxt(g)})]}),
      r.jsxs("div",{className:"svm-fadegain",children:[
        r.jsx("span",{className:"svm-fxeditname",children:"Fondus"}),
        r.jsx("input",{className:"svm-transdur",type:"number",min:0,max:fmax,step:.1,
          value:Number(sel.fade_in)||0,
          title:"Fondu d'entrée (0 à "+fmax+" s)","aria-label":"Fondu d'entrée (s)",
          onChange:function(e){setF("fade_in",e.target.value)}}),
        r.jsx("span",{className:"svm-fadesep","aria-hidden":!0,children:"in · out"}),
        r.jsx("input",{className:"svm-transdur",type:"number",min:0,max:fmax,step:.1,
          value:Number(sel.fade_out)||0,
          title:(isMus?"Fondu de fin de rendu":"Fondu de sortie")+" (0 à "+fmax+" s)",
          "aria-label":isMus?"Fondu de fin de rendu (s)":"Fondu de sortie (s)",
          onChange:function(e){setF("fade_out",e.target.value)}}),
        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"s"})]}),
      isMus?r.jsx("div",{className:"svm-transnone",children:"musique bouclée sur toute la durée — fondu de sortie calé sur la fin du rendu"}):null]})}

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
    narrStop();
    if(!c.src)return;
    if(playingRef.current)setPlaying(!1); /* jamais deux flux à la fois */
    var a=new Audio(svmSrcUrl(c.src));narrAudioRef.current=a;
    var s0=c.srcIn||0,s1=s0+Math.max(.1,c.end-c.start);
    try{a.currentTime=s0}catch(_e){}
    a.ontimeupdate=function(){if(a.currentTime>=s1-.02)narrStop()};
    a.onended=function(){narrStop()};
    setNarrPlayId(c.id);
    a.play().catch(function(){narrStop();
      fireNote("Lecture bloquée par le navigateur — cliquez d'abord dans la page.")})}
  /* texte d'un bloc — champ client posé sur le clip, une entrée d'historique
     par rafale de 600 ms (motif transition / mixage) ; ne touche pas à
     « NON ENREGISTRÉ » : rien ne part au rendu tant qu'on ne narre pas */
  function narrSetText(id,v){
    var now=Date.now();
    if(now-narrHistAt.current>600)pushHistory();
    narrHistAt.current=now;
    if(narrErr&&narrErr.id===id)setNarrErr(null);
    setClips(clipsRef.current.map(function(k){
      if(k.id!==id)return k;
      var nk=Object.assign({},k);
      if(v)nk.text=v;else delete nk.text;
      return nk}))}
  /* succès de synthèse : le clip reçoit src={audio}, sa fin suit la durée
     réelle mesurée — ripple actif : les clips A1 suivants sont décalés du
     delta ; sinon la fin est bornée au voisin A1 et au projet */
  function narrApply(id,fn,dsec){
    var cs=clipsRef.current,cur=null,i;
    for(i=0;i<cs.length;i++){if(cs[i].id===id){cur=cs[i];break}}
    if(!cur){fireNote("Bloc narré, mais son clip a disparu — « "+fn+" » reste dans la Bibliothèque (sons).");return}
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
    fireNote(known?"Bloc narré — "+svmShort(len)+(doRip?" · blocs suivants recalés (ripple)":"")
      :"Bloc narré — durée non mesurée, longueur du bloc conservée.")}
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
          throw new Error((o.d&&(o.d.detail||o.d.error))||"échec de la synthèse");
        var fn=o.d.filename;
        return svmAudioDur(o.d.url||("/api/audio/"+encodeURIComponent(fn)))
          .then(function(ds){narrApply(id,fn,ds);setNarrBusy("")})})
      .catch(function(e){setNarrBusy("");
        setNarrErr({id:id,msg:String(e&&e.message||e)})})}
  function narrClick(c){
    if(proj.demo){fireNote("Narration : disponible sur un projet réel — la démo reste une maquette.");return}
    if(trackStRef.current.a1&&trackStRef.current.a1.l){
      fireNote("Piste A1 verrouillée — déverrouillez-la pour narrer.");return}
    if(narrBusy)return;
    if(!(c.text&&c.text.trim()))return;
    if(!narrConfirmRef.current){setNarrArm(c.id);return}
    narrDo(c.id)}
  function narrAddBlock(){
    if(proj.demo){fireNote("Blocs de narration : disponibles sur un projet réel — la démo reste une maquette.");return}
    if(trackStRef.current.a1&&trackStRef.current.a1.l){
      fireNote("Piste A1 verrouillée — déverrouillez-la pour ajouter.");return}
    var d=durRef.current,cs=clipsRef.current,last=0;
    cs.forEach(function(k){if(k.tr==="a1"&&k.end>last)last=k.end});
    var st=Math.min(last,Math.max(0,d-.5)),en=Math.min(d,st+4);
    if(en-st<.5){fireNote("Plus de place sur A1 — libérez la fin de la piste dialogue.");return}
    ovSeq.current++;
    var id="a1n"+ovSeq.current+"_"+Math.round(st*10);
    pushHistory();
    setClips(cs.concat([{tr:"a1",id:id,label:"bloc narration",start:st,end:en,narr:!0}]));
    setSelId(id);setDirty(!0);
    fireNote("Bloc narration ajouté à "+svmShort(st)+" — écrivez son texte puis « Narrer ».")}
  function narrBlock(c,i){
    var isSel=selId===c.id,isAct=narrActive===c.id;
    var isPlan=!!(c.src&&c.src.job_id);
    var hasText=!!(c.text&&c.text.trim());
    var busy=narrBusy===c.id,arm=narrArm===c.id;
    var err=narrErr&&narrErr.id===c.id?narrErr.msg:null;
    var off=!hasText||!!narrBusy;
    var tt=busy?"synthèse en cours…":
      !hasText?"Écrivez d'abord le texte du bloc":
      isPlan?"Remplace le son du plan par une narration (~$0.08 — crédits ElevenLabs)":
      c.narrDone?"Re-synthétiser ce bloc (~$0.08 — crédits ElevenLabs)":
      c.src?"Remplace ce son par la narration (~$0.08 — crédits ElevenLabs)":
      "Synthétiser la voix de ce bloc (~$0.08 — crédits ElevenLabs)";
    return r.jsxs("div",{className:"svm-nb","data-nbid":c.id,
      "data-sel":isSel?"":void 0,"data-on":isAct?"":void 0,
      "data-ph":c.src?void 0:"",
      title:"Caler la tête de lecture au début du bloc",
      onClick:function(){setSelId(c.id);seekTo(c.start)},
      children:[
      r.jsxs("div",{className:"svm-nbhead",children:[
        r.jsx("span",{className:"svm-nbnum",children:svmPad2(i+1)}),
        r.jsx("span",{className:"svm-nbtc",title:"début du bloc (HH:MM:SS:image, 30 i/s)",children:svmTcFF(c.start)}),
        r.jsx("span",{className:"svm-nbdur",title:"durée du bloc",children:svmShort(c.end-c.start)})]}),
      r.jsxs("div",{className:"svm-nblabel",children:[c.label,
        c.src&&!hasText?r.jsx("span",{className:"svm-nbplanhint",
          children:isPlan?" (son du plan — pas de texte)":" (son importé — pas de texte)"}):null]}),
      r.jsx("textarea",{className:"svm-nbtext",rows:2,value:c.text||"",
        placeholder:"Écris la narration de ce plan…",
        "aria-label":"Texte de narration du bloc "+(i+1),
        title:c.src&&!hasText?"Écrire ici puis « Narrer » remplace ce son par la voix de synthèse":void 0,
        ref:narrTaGrow,
        onClick:function(e){e.stopPropagation()},
        onChange:function(e){narrSetText(c.id,e.target.value);narrTaGrow(e.target)}}),
      err?r.jsx("div",{className:"svm-note svm-nberr",children:"Échec : "+err}):null,
      arm?r.jsxs("div",{className:"svm-narrconfirm",onClick:function(e){e.stopPropagation()},children:[
        r.jsx("span",{children:"Générer la voix (~$0.08) ?"}),
        r.jsx("button",{className:"svm-nbgold",
          onClick:function(e){e.stopPropagation();narrConfirmRef.current=1;setNarrArm("");narrDo(c.id)},
          children:"Oui"}),
        r.jsx("button",{className:"svm-minibtn",
          onClick:function(e){e.stopPropagation();setNarrArm("")},children:"Non"})]}):
      r.jsxs("div",{className:"svm-nbrow",children:[
        r.jsx("button",{className:"svm-nbgold","data-off":off?"":void 0,title:tt,
          onClick:function(e){e.stopPropagation();if(!off)narrClick(c)},
          children:busy?"synthèse…":c.narrDone?"Re-narrer":"Narrer"}),
        r.jsx("button",{className:"svm-minibtn svm-nbplay",
          "data-on":narrPlayId===c.id?"":void 0,"data-off":c.src?void 0:"",
          title:c.src?(narrPlayId===c.id?"Pause":"Écouter l'audio du bloc"):"rien à écouter — bloc non narré",
          "aria-label":"Écouter le bloc "+(i+1),
          onClick:function(e){e.stopPropagation();if(c.src)narrListen(c)},
          children:narrPlayId===c.id?"▮▮":"▶"}),
        r.jsx("button",{className:"svm-minibtn svm-nbdel",
          title:"Supprimer le bloc et son clip A1 (ripple respecté)",
          "aria-label":"Supprimer le bloc "+(i+1),
          onClick:function(e){e.stopPropagation();
            if(narrPlayId===c.id)narrStop();
            delClipById(c.id)},
          children:"🗑︎"})]})]},c.id)}
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
        r.jsx(SvmLabel,{children:"Narration"}),
        r.jsx("span",{className:"svm-narrcount",children:blocks.length+" bloc"+(blocks.length>1?"s":"")})]}),
      r.jsxs("div",{className:"svm-narrvoice",children:[
        r.jsx("span",{className:"svm-nbvlbl",children:"Voix"}),
        narrVoices===null?
          r.jsx("span",{className:"svm-note",style:{marginTop:0,flex:"1 1 auto"},children:"chargement des voix…"}):
          r.jsxs("select",{className:"svm-secbtn svm-narrsel",value:narrVoice,
            title:"Voix de la narration (choix mémorisé) — voix clonées en tête",
            "aria-label":"Voix de narration",
            onChange:function(e){var v=e.target.value;setNarrVoice(v);
              try{localStorage.setItem("dz_narr_voice",v)}catch(_e){}},
            children:[
              cloned.length?r.jsx("optgroup",{label:"Voix clonées",children:cloned.map(opt)},"gcl"):null,
              others.length?r.jsx("optgroup",{label:narrVoices.enabled?"Catalogue":"Voix (démo)",
                children:others.map(opt)},"gcat"):null]})]}),
      narrVoices&&!narrVoices.enabled?r.jsx("div",{className:"svm-note",style:{marginTop:7},
        children:"voix de démonstration — connectez ElevenLabs (Réglages → Clés API) pour synthétiser"}):null,
      r.jsx("div",{className:"svm-narrlist",children:
        blocks.length?blocks.map(function(c,i){return narrBlock(c,i)}):
        r.jsx("div",{className:"svm-transnone",style:{marginTop:0},
          children:"aucun bloc — « + Ajouter un bloc » crée un plan de narration de 4 s sur A1"})}),
      r.jsx("button",{className:"svm-narradd",
        title:"Créer un clip A1 vide de 4 s en fin de piste — hachuré tant qu'il n'est pas narré",
        onClick:narrAddBlock,children:"+ Ajouter un bloc"}),
      r.jsx("div",{className:"svm-note",style:{marginTop:8},
        children:"le texte reste local — seul « Narrer » envoie le bloc à ElevenLabs"})]})}

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
        r.jsx("button",{className:"svm-themechip svm-narrchip","data-on":narrOn?"":void 0,
          "aria-pressed":narrOn,
          title:"Panneau Narration — écrire, synthétiser, caler la piste A1 (T)",
          onClick:narrToggle,children:"narration"}),
        r.jsx(SvmThemeChip,{theme:theme,setTheme:setTheme})]})]}),
    popover(),
    fxPicker(),
    ovPicker(),
    transPopover(),
    kbPanel(),
    /* tiroir narration + lecteur + inspecteur */
    r.jsxs("div",{className:"svm-mid",children:[
      narrPanel(),
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
          /* cadre de sélection des overlays : boîte + 8 poignées (échelle) +
             rotation, guides d'alignement et badge de geste — positionnés
             impérativement (tfSyncBox / ovGesture), hors échelle vzoom */
          liveOn?r.jsxs("div",{className:"svm-tf",children:[
            r.jsx("i",{className:"svm-tfguide","data-ax":"v",ref:tfGuideVRef}),
            r.jsx("i",{className:"svm-tfguide","data-ax":"h",ref:tfGuideHRef}),
            r.jsx("div",{className:"svm-tfbox",ref:tfBoxRef,children:
              ["nw","n","ne","e","se","s","sw","w"].map(function(hp){
                return r.jsx("i",{className:"svm-tfh","data-p":hp,
                  title:"Échelle — glisser (homothétique)",
                  onPointerDown:function(e2){ovHandleDown(e2,"scale")}},hp)})
              .concat([
                r.jsx("i",{className:"svm-tfstem","aria-hidden":!0},"stem"),
                r.jsx("i",{className:"svm-tfrot",
                  title:"Rotation — glisser (aimant 0 / ±45 / 90°)",
                  onPointerDown:function(e2){ovHandleDown(e2,"rotate")}},"rot")])}),
            r.jsx("div",{className:"svm-tfbadge",ref:tfBadgeRef})]}):null,
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
          r.jsx("div",{className:"svm-caption",children:
            r.jsx("div",{className:"svm-captiontext",children:proj.demo?"« La marée ne demande pas la permission. »":proj.name})}),
          /* timecode image-exact — coin haut droit, seul overlay UI permanent */
          r.jsx("div",{className:"svm-frametc svm-frametr",children:svmTcFF(ph)})]})}),
        /* barre du lecteur — TOUJOURS visible (plus de boutons au survol) :
           qualité source/480p, ratio du canvas, zones sûres, plein écran */
        r.jsxs("div",{className:"svm-playerbar",role:"group","aria-label":"Contrôles du lecteur",children:[
          r.jsx("button",{className:"svm-pchip","data-on":previewUrl?void 0:"",
            title:previewUrl?"revenir à l'aperçu direct des sources"
              :"aperçu direct des sources — transitions, effets et mixage visibles après une Preview 480p",
            onClick:function(){if(previewUrl)setPreviewUrl(null)},children:"source"}),
          r.jsx("button",{className:"svm-pchip","data-on":previewUrl?"":void 0,
            "data-off":!previewUrl&&!prevSaved?"":void 0,
            title:previewUrl?"aperçu rendu 480p branché dans le lecteur"
              :prevSaved?"rebrancher le dernier aperçu rendu 480p"
              :"lancer Preview 480p (gratuit)",
            onClick:function(){if(previewUrl)return;
              if(prevSaved)setPreviewUrl(prevSaved);
              else setPop(pop==="preview"?"":"preview")},children:"480p"}),
          r.jsx("i",{className:"svm-pdiv","aria-hidden":!0}),
          r.jsx("span",{className:"svm-pchip svm-pinfo",
            title:"ratio du canvas — se change dans la barre de titre",
            children:proj.ratio||"9:16"}),
          r.jsx("i",{className:"svm-pdiv","aria-hidden":!0}),
          r.jsx("button",{className:"svm-pchip","data-on":safeOn?"":void 0,
            "aria-pressed":safeOn,title:"tiers, centre et marges sur le cadre",
            onClick:function(){setSafeOn(!safeOn)},children:"zones sûres (G)"}),
          r.jsx("button",{className:"svm-pchip",title:"plein écran du cadre (Échap pour sortir)",
            onClick:svmFullscreen,children:"plein écran (F)"})]})]}),
      r.jsxs("aside",{className:"svm-insp",children:[
        r.jsx(SvmLabel,{children:"Clip sélectionné"}),
        r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:8,marginTop:9},children:[
          r.jsx("div",{className:"svm-clipname",style:{marginTop:0,flex:"1 1 auto",minWidth:0,
            whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"},children:sel?sel.label:"—"}),
          sel?r.jsx("button",{className:"svm-minibtn",title:"Supprimer le clip (Suppr)",
            "aria-label":"Supprimer "+sel.label,onClick:delClip,children:"🗑︎"}):null]}),
        r.jsx("div",{className:"svm-props",children:[
          {k:"In",v:sel?svmShort(sel.srcIn!=null?sel.srcIn:0):"—",t:sel?(sel.srcIn!=null?sel.srcIn:0):null},
          {k:"Out",v:sel?svmShort(sel.srcOut!=null?sel.srcOut:(sel.end-sel.start)):"—",t:sel?(sel.srcOut!=null?sel.srcOut:(sel.end-sel.start)):null},
          {k:"Vitesse",v:sel&&sel.speed?sel.speed:"100 %",t:null}
        ].map(function(p2){return r.jsxs("div",{className:"svm-prop",
          /* équivalent image-exact au survol — la valeur affichée reste une durée */
          title:p2.t==null?void 0:"= "+svmTcFF(p2.t)+" · "+Math.round(p2.t*30)+" images (30 i/s)",
          children:[
          r.jsx("div",{className:"svm-propk",children:p2.k}),
          r.jsx("div",{className:"svm-propv",children:p2.v})]},p2.k)})}),
        transInspector(),
        ovInspector(),
        audioInspector(),
        r.jsxs("div",{style:{display:"flex",alignItems:"center",margin:"20px 0 10px"},children:[
          r.jsx(SvmLabel,{children:"Mixage"}),
          /* vu-mètre live — seulement pendant la lecture d'un vrai flux */
          playing&&!proj.demo?r.jsx("canvas",{className:"svm-vu",ref:vuRef,role:"img",
            title:"niveau du flux en cours de lecture (mono, crête tenue 0,9 s)",
            "aria-label":"Vu-mètre de lecture"}):null]}),
        r.jsx("div",{className:"svm-mix",children:mixRows.map(function(m){
          return r.jsxs("div",{children:[
            r.jsxs("div",{className:"svm-mixhead",children:[
              r.jsx("span",{style:{color:"var("+m.c+")"},children:m.name}),
              r.jsx("span",{"data-off":m.dbNum<=-40?"":void 0,
                children:m.dbNum<=-40?"muet":m.db})]}),
            r.jsx("div",{className:"svm-mixrail",role:"slider",tabIndex:0,
              title:"Glisser pour régler le niveau "+m.name+" ("+m.db+")",
              "aria-label":"Niveau "+m.name,"aria-valuemin":-40,"aria-valuemax":0,
              "aria-valuenow":m.dbNum,"aria-valuetext":m.dbNum<=-40?"muet":m.db,
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
        r.jsxs("span",{className:"svm-tcmain",title:"position / durée totale — HH:MM:SS:image (30 i/s)",children:[
          svmTcFF(ph),r.jsx("span",{className:"svm-tctotal",children:" / "+svmTcFF(dur)})]}),
        playing&&spd!==1?r.jsx("span",{className:"svm-spdchip",
          title:"vitesse de lecture (J / L, K pour pause)",
          children:(spd<0?"◀ ×":"×")+Math.abs(spd)}):null,
        r.jsxs("div",{className:"svm-transbtns",children:[
          r.jsx("button",{className:"svm-tbtn",title:"Coupe précédente (↑)",onClick:function(){jump(-1)},children:"◀◀"}),
          r.jsx("button",{className:"svm-tbtn",title:"Image précédente (←)","aria-label":"Reculer d'une image",
            onClick:function(){seekTo(Math.max(0,Math.round(phRef.current*30-1)/30))},children:"|◀"}),
          r.jsx("button",{className:"svm-tbtn svm-gold",title:playing?"Pause (Espace · K)":"Lecture (Espace · L)",
            onClick:function(){setSpd(1);setPlaying(!playing)},children:playing?"▮▮":"▶"}),
          r.jsx("button",{className:"svm-tbtn",title:"Image suivante (→)","aria-label":"Avancer d'une image",
            onClick:function(){seekTo(Math.min(durRef.current,Math.round(phRef.current*30+1)/30))},children:"▶|"}),
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
          " "+Math.round(zoomPct)+" % · "+svmRuler(Math.round(dur))+" total"]}),
        /* bouton discret du panneau raccourcis — fin de transport */
        r.jsx("button",{className:"svm-tbtn",title:"Raccourcis (?)",
          "aria-label":"Raccourcis clavier","aria-haspopup":"dialog","aria-expanded":kbOn,
          onClick:function(){setKbOn(!kbOn)},children:"?"})]}),
      r.jsx("div",{className:"svm-scroll",ref:tlScrollRef,children:
        r.jsxs("div",{className:"svm-lanes",style:{width:zoomPct+"%"},children:[
          r.jsxs("div",{className:"svm-ruler",onPointerDown:rulerDown,
            onPointerMove:rulerHover,onPointerLeave:rulerLeave,children:[
            r.jsx("div",{className:"svm-gutter"}),
            ticks.map(function(t3){return r.jsx("div",{className:"svm-tick",children:svmRuler(t3)},t3)})]}),
          SVM_TRACKS.map(function(tr){
            var bus=SVM_TRACK_BUS[tr.id];
            var busDb=bus?Number(proj.mixDb&&proj.mixDb[bus]!=null?proj.mixDb[bus]:SVM_DEMO_MIX[bus]):0;
            var muted=!!bus&&busDb<=-40;
            var locked=!!(trackSt[tr.id]&&trackSt[tr.id].l);
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
                r.jsxs("div",{className:"svm-ttyperow",children:[
                  r.jsx("span",{className:"svm-ttype",title:tr.type,children:tr.type}),
                  bus?r.jsx("button",{className:"svm-minibtn svm-tkbtn",
                    "data-on":muted?"":void 0,"aria-pressed":muted,
                    title:muted?"Réactiver "+tr.name+" (bus "+bus+" — niveau d'avant restauré)"
                      :"Rendre "+tr.name+" muette (bus "+bus+" à −40 dB dans le mixage)",
                    onClick:function(){svmTrackMute(tr.id)},children:"M"}):null,
                  r.jsx("button",{className:"svm-minibtn svm-tkbtn",
                    "data-on":locked?"":void 0,"aria-pressed":locked,
                    title:locked?"Déverrouiller la piste "+tr.name
                      :"Verrouiller la piste "+tr.name+" (bloque déplacement, rognage, dépôt, suppression)",
                    onClick:function(){svmTrackLock(tr.id)},children:"🔒︎"})]})]}),
              r.jsxs("div",{className:"svm-lane",
                onDragOver:function(e){if(e.dataTransfer&&Array.prototype.indexOf.call(e.dataTransfer.types||[],DZ_MIME)>=0){e.preventDefault();e.dataTransfer.dropEffect="copy"}},
                onDrop:function(e){dropOnTrack(e,tr.id,e.currentTarget)},
                children:[
                tr.id==="v1"?svmV1Gaps(clips,dur):null,
                clips.filter(function(c){return c.tr===tr.id}).map(function(c){
                  var isSel=c.id===selId;
                  /* fond média : waveform (pistes audio), filmstrip / image (V1) —
                     pointer-events:none, la démo (sans src) reste inchangée */
                  var media=null;
                  if(c.src){
                    if(trackKind(tr.id)==="audio"&&(c.src.audio||c.src.job_id))
                      media=r.jsx(SvmWave,{src:c.src,k:svmSrcKey(c.src),srcIn:c.srcIn||0,
                        len:c.end-c.start,color:tr.c,theme:theme,zoom:zoomPct,dur:dur});
                    else if(tr.id==="v1"&&c.src.job_id)
                      media=r.jsx(SvmFilmstrip,{src:c.src,k:svmSrcKey(c.src),
                        srcIn:c.srcIn||0,len:c.end-c.start});
                    else if(tr.id==="v1"&&c.src.image)
                      media=r.jsx("div",{className:"svm-strip svm-stripbg","aria-hidden":!0,
                        style:{backgroundImage:"url('/api/images/"+encodeURIComponent(c.src.image)+"')"}})}
                  /* mixage par clip : rampes + poignées de fondu (clips audio
                     réels seulement) — masquées si la piste est verrouillée */
                  var aud=trackKind(tr.id)==="audio"&&c.src&&(c.src.audio||c.src.job_id);
                  var fIn=aud?Number(c.fade_in)||0:0,fOut=aud?Number(c.fade_out)||0:0;
                  var clen=Math.max(.01,c.end-c.start);
                  var fiP=Math.min(100,fIn/clen*100),foP=Math.min(100,fOut/clen*100);
                  var isMus=aud&&tr.id==="a2"&&c.id===firstA2;
                  /* bloc narration pas encore narré : hachures pointillées
                     (motif .svm-target), couleur de la piste */
                  var isPh=!!(c.narr&&!c.src);
                  return r.jsxs("div",{className:"svm-clip",
                    "data-locked":locked?"":void 0,
                    "data-narr":isPh?"":void 0,
                    "data-media":media&&tr.id==="v1"?"":void 0,
                    style:{left:c.start/dur*100+"%",width:(c.end-c.start)/dur*100+"%",
                      borderColor:isSel?"var(--accent)":isPh?"var(--stroke2)":"color-mix(in srgb, var("+tr.c+") 53%, transparent)",
                      background:isPh?"repeating-linear-gradient(-45deg,transparent 0 5px, color-mix(in srgb, var("+tr.c+") 26%, transparent) 5px 6px)":isSel?"color-mix(in srgb, var(--accent) 20%, transparent)":"color-mix(in srgb, var("+tr.c+") "+tr.mix+"%, transparent)"},
                    onPointerDown:function(e){clipDown(e,c,e.currentTarget.parentElement)},
                    /* curseur explicite : sans lui, rien n'indique que les
                       bords rognent au lieu de déplacer */
                    onPointerMove:function(e){
                      if(e.buttons)return;
                      var el=e.currentTarget;
                      if(locked){el.style.cursor="";return}
                      el.style.cursor=svmEdgeAt(e.clientX,el.getBoundingClientRect())==="m"?"grab":"col-resize"},
                    title:locked?c.label+" — piste verrouillée"
                      :c.label+" — bords : rogner / allonger · centre : déplacer",
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
                        r.jsx("line",{x1:0,y1:100,x2:100,y2:0,vectorEffect:"non-scaling-stroke"})}):null,
                      fOut>0?r.jsx("svg",{className:"svm-fadeline","aria-hidden":!0,
                        viewBox:"0 0 100 100",preserveAspectRatio:"none",
                        style:{right:0,width:foP+"%"},children:
                        r.jsx("line",{x1:0,y1:0,x2:100,y2:100,vectorEffect:"non-scaling-stroke"})}):null,
                      r.jsx("div",{className:"svm-cliplabel",children:c.label}),
                      /* poignées visibles sur le clip sélectionné */
                      isSel?r.jsx("div",{style:{position:"absolute",left:0,top:0,bottom:0,width:4,
                        background:"var(--accent)",borderRadius:"3px 0 0 3px",pointerEvents:"none"}}):null,
                      isSel?r.jsx("div",{style:{position:"absolute",right:0,top:0,bottom:0,width:4,
                        background:"var(--accent)",borderRadius:"0 3px 3px 0",pointerEvents:"none"}}):null,
                      /* poignées de fondu — coins supérieurs, drag vers
                         l'intérieur ; sur la musique A2 bouclée la droite
                         règle le fondu de FIN DE RENDU */
                      aud&&!locked?r.jsx("i",{className:"svm-fadeh",
                        title:"Fondu d'entrée : "+fIn.toFixed(1)+" s — glisser vers l'intérieur",
                        style:{left:"calc("+fiP+"% - 4px)"},
                        onPointerDown:function(e){fadeDown(e,c,"in",e.currentTarget.parentElement.parentElement)}}):null,
                      aud&&!locked?r.jsx("i",{className:"svm-fadeh",
                        title:(isMus?"Fondu de fin de rendu (musique bouclée sur toute la durée) : "
                          :"Fondu de sortie : ")+fOut.toFixed(1)+" s — glisser vers l'intérieur",
                        style:{right:"calc("+foP+"% - 4px)"},
                        onPointerDown:function(e){fadeDown(e,c,"out",e.currentTarget.parentElement.parentElement)}}):null]},c.id)}),
                /* jonctions V1 : étendue de la transition + losange de réglage */
                tr.id==="v1"?svmV1Junctions(clips).map(function(j2){
                  var on=svmTransBase(j2.right.transition)!=="cut";
                  var s2=on?svmTransS(j2.right):0;
                  return r.jsxs(r.Fragment,{children:[
                    /* bloc doré interactif : clic = réglage, poignées 4 px =
                       durée symétrique ; jamais de clipDown / scrub dessous */
                    on?r.jsxs("div",{className:"svm-transspan",
                      title:svmTransLabel(j2.right.transition)+" · "+s2.toFixed(2)+" s — poignées : durée · clic : régler",
                      style:{left:(j2.t-s2/2)/dur*100+"%",width:s2/dur*100+"%"},
                      onPointerDown:function(e){e.stopPropagation()},
                      onPointerEnter:function(){transHoverShow(j2.t,transHoverTxt(j2.right,on,s2))},
                      onPointerLeave:transHoverHide,
                      onClick:function(e){e.stopPropagation();openTransPop(j2.right.id,e)},
                      children:[
                      r.jsx("i",{className:"svm-transhandle","data-side":"l","aria-hidden":!0,
                        onClick:function(e){e.stopPropagation()},
                        onPointerDown:function(e){transSpanDown(e,j2.right,-1,j2.t)}}),
                      r.jsx("i",{className:"svm-transhandle","data-side":"r","aria-hidden":!0,
                        onClick:function(e){e.stopPropagation()},
                        onPointerDown:function(e){transSpanDown(e,j2.right,1,j2.t)}})]}):null,
                    r.jsx("button",{className:"svm-junc",
                      "data-on":on?"":void 0,
                      "data-sel":transPop&&transPop.id===j2.right.id?"":void 0,
                      style:{left:"calc("+j2.t/dur*100+"% - 5px)"},
                      title:"Transition : "+svmTransLabel(j2.right.transition)+(on?" · "+s2.toFixed(2)+" s":"")+" — cliquer pour régler",
                      "aria-label":"Transition entre "+j2.left.label+" et "+j2.right.label,
                      onPointerDown:function(e){e.stopPropagation()},
                      onPointerEnter:function(){transHoverShow(j2.t,transHoverTxt(j2.right,on,s2))},
                      onPointerLeave:transHoverHide,
                      onClick:function(e){e.stopPropagation();openTransPop(j2.right.id,e)}})]},"jx"+j2.right.id)}):null]})]},tr.id)}),
          snapT!=null?r.jsx("div",{className:"svm-snapline",style:{left:"calc(88px + (100% - 88px) * "+(snapT/dur)+")"}}):null,
          r.jsx("div",{className:"svm-phline",style:{left:"calc(88px + (100% - 88px) * "+phFrac+")"}}),
          r.jsx("div",{className:"svm-phtri",style:{left:"calc(88px + (100% - 88px) * "+phFrac+")"}}),
          r.jsx("div",{className:"svm-hovertc",ref:hoverTcRef}),
          r.jsx("div",{className:"svm-translabel",ref:transLabelRef})]})})]})]})}
