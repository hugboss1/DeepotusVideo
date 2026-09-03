/* ── Montage, couche window.DzTracks — injectée après le bloc subs, même scope
   module. Le CŒUR (tracks*, dzm*) est pur : aucune référence à `r` (jsx) ni à
   `x` (React) au CHARGEMENT, donc il tourne tel quel sous node — c'est ce que
   fait backend/tests/test_montage_bundle.py, qui le charge dans un shim et
   vérifie l'ordre rendu par move/add/remove. Les composants, eux, n'appellent
   `r`/`x` que dans leur corps : jamais évalués sous node.
   Styles : /shared/montage.css (préfixe .dzm-).

   CE QUE CETTE COUCHE AJOUTE : les pistes de la timeline cessent d'être une
   table figée (SVM_TRACKS) pour devenir un ÉTAT du projet (proj.tracks),
   ordonnable, extensible, sauvegardé et envoyé au rendu. L'ordre à l'écran,
   du HAUT vers le BAS, est CELUI que le backend lit dans `tracks` : la piste
   listée le plus haut est composée en dernier, donc au-dessus de tout
   (montage_service._tracks_meta, champ `layer`).

   Exporte (contrat) :
     window.DzTracks = {ready, TrackAdd, headBtns,
                         tracksOf, from, payload, busSync,
                         move, moveTo, add, remove, group, DEFAULTS}

   - TrackAdd({tracks,onChange}) — les deux boutons « + vidéo » / « + audio »
     de la barre de transport.
   - headBtns(tr, tracks, set, clips, setClips, note) — le groupe ▲ ▼ × de
     l'en-tête d'une piste, plus la poignée de glisser-déposer. Rend un
     ÉLÉMENT (avec sa clé) : il s'insère tel quel dans les tableaux `children`
     du bundle.
   - tracksOf(proj) / from(raw) / payload(proj) — lecture, restauration depuis
     la sauvegarde serveur, et le petit objet {id,kind,bus?,loop?} envoyé au
     backend.
   - busSync(tracks) — voir plus bas : SVM_TRACK_BUS muté EN PLACE. */
"use strict";

/* Les six pistes historiques, à l'octet près de SVM_TRACKS (nom, type,
   hauteur, couleur, rang de mixage), plus les trois champs que le backend
   lit : `kind`, `bus`, `loop`. Un projet sans `tracks` retombe ici et
   l'écran ne bouge pas d'un pixel. */
var DZM_DEFAULT_TRACKS=[
 {id:"v2",name:"V2",type:"overlay/VFX",h:40,c:"--c-3d",mix:13,kind:"video"},
 {id:"v1",name:"V1",type:"vidéo",h:54,c:"--c-video",mix:12,kind:"video"},
 {id:"a1",name:"A1",type:"dialogue",h:52,c:"--c-audio",mix:13,kind:"audio",bus:"dialogue"},
 {id:"a2",name:"A2",type:"musique",h:48,c:"--c-text",mix:8,kind:"audio",bus:"musique",loop:!0},
 {id:"a3",name:"A3",type:"sfx",h:48,c:"--c-3d",mix:13,kind:"audio",bus:"sfx"},
 {id:"s1",name:"S1",type:"sous-titres",h:44,c:"--c-text",mix:11,kind:"subs"}];

/* HABILLAGE d'une piste NEUVE (ou restaurée). Le payload serveur ne porte que
   {id,kind,bus,loop} : sans ce repli, une piste v3 ajoutée puis rechargée
   revenait sans nom, sans type et surtout sans HAUTEUR — une bande de 0 px,
   invisible, portant pourtant des clips. Même fonction pour l'ajout et pour
   la restauration : les deux chemins ne peuvent pas diverger. */
function dzmSkin(id,kind){
  var d=DZM_DEFAULT_TRACKS.filter(function(k){return k.id===id})[0];
  /* une COPIE : rendre l'objet de la table exposerait les défauts partagés à
     la mutation du premier appelant venu. Latent, mais d'un mot. */
  if(d)return Object.assign({},d);
  if(kind==="audio")return {id:id,name:String(id).toUpperCase(),type:"sfx",
    h:48,c:"--c-3d",mix:13,kind:"audio",bus:"sfx"};
  if(kind==="subs")return {id:id,name:String(id).toUpperCase(),type:"sous-titres",
    h:44,c:"--c-text",mix:11,kind:"subs"};
  return {id:id,name:String(id).toUpperCase(),type:"overlay",h:40,c:"--c-3d",
    mix:13,kind:"video"}}

function dzmKindOf(id,kind){
  if(kind)return kind;
  var k=String(id||"").charAt(0);
  return k==="a"?"audio":k==="s"?"subs":"video"}

function svmTracksOf(proj){
  return (proj&&proj.tracks&&proj.tracks.length)?proj.tracks:DZM_DEFAULT_TRACKS}

/* Restauration depuis GET /api/montage/project. `null` = « rien de valable,
   garde les défauts » : c'est le cas d'une sauvegarde d'avant P1, et celui
   d'une liste qui aurait perdu v1 (la piste de BASE — sans elle le rendu
   n'a plus de fond et le backend refuse la timeline). */
function svmTracksFrom(raw){
  if(!Array.isArray(raw)||!raw.length)return null;
  var seen={},out=[];
  raw.forEach(function(t){
    if(!t||!t.id)return;
    var id=String(t.id);
    if(seen[id])return;
    seen[id]=1;
    var kind=dzmKindOf(id,t.kind);
    out.push(Object.assign({},dzmSkin(id,kind),t,{id:id,kind:kind}))});
  return out.some(function(t){return t.id==="v1"})?out:null}

/* Ce qui part au backend (rendu ET autosave) : le strict nécessaire à
   montage_service._tracks_meta. L'habillage reste au client (dzmSkin le
   reconstruit au retour). */
function svmTracksPayload(proj){return svmTracksOf(proj).map(function(t){
  var o={id:t.id,kind:t.kind};if(t.bus)o.bus=t.bus;if(t.loop)o.loop=!0;return o})}

/* SVM_TRACK_BUS est un objet module-level du bloc sonvfx, LU à neuf endroits
   (mesuré : svmTrackMute, svmTrackSolo, quatre gardes de raccourci, le dépôt
   de son, le titre du gain de clip, l'en-tête de piste). On le MUTE en place
   plutôt que de poser neuf ancres — la référence ne change jamais, tous les
   lecteurs voient la nouvelle table sans qu'aucun d'eux soit réécrit.
   RESTE CONNU : les messages de ces gardes disent encore « A1, A2 ou A3 »
   en dur ; sur un projet à pistes personnalisées ils nomment mal les pistes
   éligibles. Le mécanisme, lui, est juste. */
function svmTrackBusSync(ts){
  Object.keys(SVM_TRACK_BUS).forEach(function(k){delete SVM_TRACK_BUS[k]});
  (ts||DZM_DEFAULT_TRACKS).forEach(function(t){
    if(t&&t.kind==="audio"&&t.bus)SVM_TRACK_BUS[t.id]=t.bus})}

/* Règle d'ordre : overlays au-dessus de V1 (V1 = dernière piste vidéo),
   audio au milieu, sous-titres en bas. Un déplacement ne sort JAMAIS de son
   groupe — c'est ce qui garantit que V1 reste la piste de base du rendu et
   que le backend n'a jamais à arbitrer une timeline incohérente. */
function dzmGroup(t){
  var k=t&&t.kind;
  return k==="video"?(t.id==="v1"?1:0):k==="audio"?2:3}
function dzmIndex(ts,id){
  for(var i=0;i<ts.length;i++)if(ts[i].id===id)return i;
  return -1}
function dzmMove(ts,id,dir){
  var i=dzmIndex(ts,id),j=i+dir;
  if(i<0||j<0||j>=ts.length||dzmGroup(ts[i])!==dzmGroup(ts[j]))return ts;
  var n=ts.slice();n[i]=ts[j];n[j]=ts[i];return n}
/* Glisser-déposer : on ne saute pas, on RÉPÈTE dzmMove — la frontière de
   groupe reste donc infranchissable, et la boucle s'arrête d'elle-même
   dès qu'un pas est refusé (dzmMove rend le MÊME tableau). */
function dzmMoveTo(ts,id,overId,after){
  var i=dzmIndex(ts,id),j=dzmIndex(ts,overId);
  if(i<0||j<0||i===j)return ts;
  var want=j+(after?1:0);
  if(want>i)want--;
  var out=ts,guard=0;
  while(dzmIndex(out,id)!==want&&guard++<64){
    var nx=dzmMove(out,id,dzmIndex(out,id)<want?1:-1);
    if(nx===out)break;
    out=nx}
  return out}
/* Une piste vidéo naît EN HAUT (donc au-dessus de tout au rendu), une piste
   audio juste au-dessus des sous-titres. L'identifiant est le plus petit
   libre : retirer v3 puis rajouter une vidéo redonne v3 — les clips orphelins
   d'une suppression annulée retrouvent donc leur piste. */
function dzmAdd(ts,kind){
  var n=1,ids=ts.map(function(t){return t.id});
  while(ids.indexOf(kind.charAt(0)+n)>=0)n++;
  var t=dzmSkin(kind.charAt(0)+n,kind==="audio"?"audio":"video");
  var at=kind==="video"?0:dzmSubsAt(ts);
  var out=ts.slice();out.splice(at<0?ts.length:at,0,t);return out}
function dzmSubsAt(ts){
  for(var i=0;i<ts.length;i++)if(ts[i].kind==="subs")return i;
  return -1}
/* v1 ET s1 sont des pistes de BASE. v1 porte le fond du rendu. s1 est la
   SEULE piste de sous-titres et rien ne sait la recréer : dzmAdd ne fabrique
   que des identifiants v… et a…, il n'y a pas de bouton « + sous-titres ».
   La retirer emportait ses clips (les sous-titres SONT des clips tr:"s1")
   et l'autosave figeait la perte au rechargement — un aller sans retour en
   un clic. On la refuse ici ; le × est désactivé pour elle (var `base`). */
function dzmRemove(ts,id){
  return (id==="v1"||id==="s1")?ts:ts.filter(function(t){return t.id!==id})}
function dzmClipsOn(clips,id){
  var n=0;
  (clips||[]).forEach(function(c){if(c&&c.tr===id)n++});
  return n}

/* ── P2 : animation des sous-titres MOT PAR MOT ────────────────────────────
   Trois valeurs seulement, parce que trois seulement se gravent (mesuré à
   l'image, backend/tests/test_subs_animes.py) :
     couleur — le karaoké `\k` : le mot actif change de couleur. Rien n'est
               déplacé, donc une réplique sur plusieurs lignes en profite
               aussi. C'est le comportement HISTORIQUE, et la valeur par
               défaut : la chip ne change rien tant qu'on n'y touche pas.
     rebond  — un événement ASS par mot, posé en \pos, qui entre en
               grossissant. MESURÉ : 222 px éclairés à 130 ms contre 191 une
               fois posé, soit ×1,16 (270×480, Anton 52, un mot seul).
     glow    — même mécanique, le contour pousse puis retombe.
   Le rebond et le glow ne savent poser qu'UNE ligne : une réplique plus
   longue que `maxChars` retombe sur la couleur, et le backend le DIT
   (info.word_anim_skipped). Aucune de ces valeurs ne détruit quoi que ce
   soit — c'est un champ de style, on revient en arrière en le rechangeant. */
var DZM_WORD_ANIMS=[
 {v:"couleur",l:"couleur",t:"Le mot actif change de couleur (karaoké). "+
   "Rien n'est déplacé : les répliques sur plusieurs lignes en profitent aussi."},
 {v:"rebond",l:"rebond",t:"Chaque mot entre en grossissant, puis se pose. "+
   "Mesuré à l'image : 222 pixels éclairés à 130 ms contre 191 une fois posé "+
   "(×1,16). Réservé aux répliques qui tiennent sur UNE ligne — les autres "+
   "gardent la couleur."},
 {v:"glow",l:"glow",t:"Chaque mot pousse son contour puis le laisse "+
   "retomber. Mêmes limites que le rebond : une seule ligne."}];

/* Les suggestions de POST /api/subtitles/emoji-hints en clips d'overlay.
   PUR : c'est ce que le banc exécute sous node. La piste visée est la
   première piste vidéo qui n'est pas V1 — donc la plus haute, celle qui est
   composée au-dessus de tout (P1). `seq` rend les identifiants uniques d'un
   appel à l'autre : deux passes sur la même piste ne se marchent pas dessus.

   LES QUATRE NOMBRES CI-DESSOUS SONT DES DÉFAUTS, PAS DES MESURES. 0,8 s à
   l'écran, 18 % de la largeur, centré en x, à 62 % de la hauteur (donc
   au-dessus de la bande de sous-titres, qui vit vers 80 %) : ce sont des
   points de départ choisis pour être visibles, rien d'autre ne les fonde.
   Le clip qui en sort est un clip ORDINAIRE — il se déplace, se retaille,
   se supprime, et l'annulation le retire comme n'importe quel autre. */
function dzmEmojiClips(hints,tracks,seq){
  var ov=(tracks&&tracks.length?tracks:DZM_DEFAULT_TRACKS).filter(function(t){
    return t&&t.kind==="video"&&t.id!=="v1"});
  if(!ov.length)return [];
  var tr=ov[0].id,n=Number(seq)||0;
  return (hints||[]).filter(function(h){return h&&h.png}).map(function(h,i){
    var t0=Number(h.t)||0;
    /* pas de `is_image` : le backend dérive le genre du SUFFIXE du fichier
       (_resolve_src puis la sonde) et le frontend ne lit jamais ce champ —
       le poser ne ferait qu'inventer une source de vérité de plus. */
    return {id:"emo"+(n+i).toString(36)+"_"+String(h.file||i),tr:tr,
      label:(h.emoji||"emoji")+" "+(h.word||""),
      src:{file_path:h.png},
      start:Math.round(t0*1e3)/1e3,end:Math.round((t0+0.8)*1e3)/1e3,
      scale:.18,x:.5,y:.62,rotate:0}})}

/* ── composants (r/x du bundle — jamais touchés au chargement) ───────────── */

/* Les deux boutons de la barre de transport. */
var DzmTrackAdd=function(props){
  var ts=(props&&props.tracks&&props.tracks.length)?props.tracks:DZM_DEFAULT_TRACKS;
  function add(k){if(props&&props.onChange)props.onChange(dzmAdd(ts,k))}
  return r.jsxs("span",{className:"dzm-add",children:[
    r.jsx("button",{className:"svm-tbtn dzm-addb",
      title:"Ajouter une piste vidéo d'overlay — posée tout en haut, donc "+
        "composée AU-DESSUS des autres au rendu",
      "aria-label":"Ajouter une piste vidéo d'overlay",
      onClick:function(){add("video")},children:"+ vidéo"},"v"),
    r.jsx("button",{className:"svm-tbtn dzm-addb",
      title:"Ajouter une piste audio — posée sous les pistes audio "+
        "existantes, au-dessus des sous-titres. Bus BRUITAGES, sauf si "+
        "l'identifiant libre est celui d'une piste historique retirée (A1, "+
        "A2) : elle revient alors avec son bus d'origine et son habillage.",
      "aria-label":"Ajouter une piste audio",
      onClick:function(){add("audio")},children:"+ audio"},"a")]})};

/* ▲ ▼ × d'un en-tête de piste, et la poignée de glisser-déposer.
   Le × ARME avant de frapper quand la piste porte des clips : un clic pose
   `data-arm` et remplace le glyphe par le compte, le second clic seulement
   supprime. */
var DzmTrackBtns=function(props){
  var tr=props.tr;
  var ts=(props.tracks&&props.tracks.length)?props.tracks:DZM_DEFAULT_TRACKS;
  var sa=x.useState(0),arm=sa[0],setArm=sa[1];
  x.useEffect(function(){
    if(!arm)return;
    var h=setTimeout(function(){setArm(0)},4000);
    return function(){clearTimeout(h)}},[arm]);
  var n=dzmClipsOn(props.clips,tr.id);
  var base=tr.id==="v1"||tr.id==="s1";
  var upOk=dzmMove(ts,tr.id,-1)!==ts,dnOk=dzmMove(ts,tr.id,1)!==ts;
  function note(m){if(props.note)props.note(m)}
  function set(nx){if(props.onSet&&nx!==ts)props.onSet(nx)}
  function mv(d){
    var nx=dzmMove(ts,tr.id,d);
    if(nx===ts){note("« "+(tr.name||tr.id)+" » ne peut pas aller plus "+
      (d<0?"haut":"bas")+" — les overlays restent au-dessus de V1, l'audio "+
      "au milieu, les sous-titres en bas.");return}
    set(nx)}
  function del(){
    if(base){note(tr.id==="s1"
      ?"S1 est la seule piste de sous-titres et rien ne sait la recréer : "+
       "elle ne peut pas être retirée."
      :"V1 est la piste de base du montage : elle ne peut pas être "+
       "retirée.");return}
    if(n&&!arm){setArm(1);return}
    setArm(0);
    set(dzmRemove(ts,tr.id));
    if(n&&props.setClips)props.setClips(function(cs){
      return (cs||[]).filter(function(c){return c.tr!==tr.id})});
    note("Piste "+(tr.name||tr.id)+" retirée"+
      (n?" avec "+n+" clip"+(n>1?"s":""):"")+
      (n?" — annuler ramène les clips ; la piste, elle, se rajoute par "+
         "« + "+(tr.kind==="audio"?"audio":"vidéo")+" » (même identifiant).":"."))}
  return r.jsxs("div",{className:"dzm-hb",draggable:!0,
    title:"Glisser pour réordonner la piste (ou ▲ ▼)",
    onDragStart:function(e){
      try{e.dataTransfer.setData("dz-track",tr.id);
        e.dataTransfer.effectAllowed="move"}catch(_e){}},
    onDragOver:function(e){
      var ty=e.dataTransfer&&e.dataTransfer.types;
      if(!ty||Array.prototype.indexOf.call(ty,"dz-track")<0)return;
      e.preventDefault();e.stopPropagation();
      try{e.dataTransfer.dropEffect="move"}catch(_e){}},
    onDrop:function(e){
      var src="";
      try{src=e.dataTransfer.getData("dz-track")||""}catch(_e){src=""}
      if(!src||src===tr.id)return;
      e.preventDefault();e.stopPropagation();
      var box=e.currentTarget.getBoundingClientRect();
      var after=box.height>0&&(e.clientY-box.top)>box.height/2;
      set(dzmMoveTo(ts,src,tr.id,after))},
    children:[
    r.jsx("span",{className:"dzm-grip","aria-hidden":!0,children:"⋮"},"g"),
    r.jsx("button",{className:"dzm-hbtn",disabled:!upOk,"aria-disabled":!upOk,
      title:"Monter "+(tr.name||tr.id)+" d'un rang — une piste plus haute est "+
        "composée AU-DESSUS au rendu",
      "aria-label":"Monter la piste "+(tr.name||tr.id),
      onClick:function(){mv(-1)},children:"▲"},"u"),
    r.jsx("button",{className:"dzm-hbtn",disabled:!dnOk,"aria-disabled":!dnOk,
      title:"Descendre "+(tr.name||tr.id)+" d'un rang",
      "aria-label":"Descendre la piste "+(tr.name||tr.id),
      onClick:function(){mv(1)},children:"▼"},"d"),
    r.jsx("button",{className:"dzm-hbtn dzm-hbx",disabled:base,"aria-disabled":base,
      "data-arm":arm?"":void 0,
      title:base?(tr.id==="s1"
          ?"S1 est la seule piste de sous-titres — elle ne se retire pas"
          :"V1 est la piste de base du montage — elle ne se retire pas")
        :n?(arm?"Confirmer : retirer "+(tr.name||tr.id)+" ET ses "+n+" clip"+
              (n>1?"s":"")+" — annuler ramène les clips"
             :"Retirer la piste "+(tr.name||tr.id)+" ("+n+" clip"+(n>1?"s":"")+
              " — un second clic confirmera)")
        :"Retirer la piste "+(tr.name||tr.id)+" (vide)",
      "aria-label":"Retirer la piste "+(tr.name||tr.id),
      onClick:function(){del()},children:arm?String(n):"×"},"x")]})};

function dzmHeadBtns(tr,ts,set,clips,setClips,note){
  return r.jsx(DzmTrackBtns,{tr:tr,tracks:ts,onSet:set,clips:clips,
    setClips:setClips,note:note},"dzmhb")}

/* La chip « mot : couleur / rebond / glow » de la barre de transport. Le
   panneau de style vit dans un TIROIR qu'on ne peut pas patcher (le bloc
   correspondant du bundle porte vingt sections que la copie source de
   son-vfx-montage.js ne sait pas rejouer) : le réglage est donc posé ici,
   là où il est visible sans ouvrir quoi que ce soit. */
var DzmWordAnimChip=function(props){
  var v=String((props&&props.value)||"couleur");
  function set(nv){if(props&&props.onChange&&nv!==v)props.onChange(nv)}
  return r.jsxs("span",{className:"dzm-wa",role:"group",
    "aria-label":"Animation des sous-titres, mot par mot",children:[
    r.jsx("span",{className:"dzm-walbl","aria-hidden":!0,children:"mot"},"l"),
    r.jsx("span",{className:"dzm-wab",children:DZM_WORD_ANIMS.map(function(o){
      return r.jsx("button",{className:"svm-tbtn dzm-wabtn",
        "data-on":v===o.v?"":void 0,"aria-pressed":v===o.v,
        title:o.t,onClick:function(){set(o.v)},children:o.l},o.v)})},"b")]})};

/* Le bouton « emoji » : demande les suggestions au backend, les pose en
   clips d'overlay. RÉVERSIBLE — l'appelant pousse l'historique AVANT
   d'ajouter, donc « annuler » les retire d'un coup ; et ce sont des clips
   ordinaires, qui se déplacent et se suppriment comme les autres. */
var DzmEmojiBtn=function(props){
  var sb=x.useState(0),busy=sb[0],setBusy=sb[1];
  function note(m){if(props&&props.note)props.note(m)}
  function go(){
    if(busy)return;
    var segs=(props&&props.segments)||[];
    if(!segs.length){
      note("Aucun sous-titre : les emoji se posent sur les MOTS d'une "+
        "réplique. Écrivez la piste S1 d'abord.");return}
    if(!props.onAdd){note("Emoji : rien pour recevoir les clips.");return}
    setBusy(1);
    fetch("/api/subtitles/emoji-hints",{method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({segments:segs})})
      .then(function(rp){return rp.json()})
      .then(function(d){
        setBusy(0);
        var hs=(d&&d.hints)||[];
        if(!hs.length){note("Aucun mot-clé reconnu — les mots suivis sont "+
          "feu, lune, vague, poulpe, or, fusée.");return}
        var cs=dzmEmojiClips(hs,props.tracks,Date.now());
        if(!cs.length){note("Aucune piste vidéo d'overlay pour les poser : "+
          "ajoutez-en une par « + vidéo ».");return}
        props.onAdd(cs);
        note(cs.length+" emoji posé"+(cs.length>1?"s":"")+" sur "+cs[0].tr+
          " — annuler les retire tous.")})
      .catch(function(e){setBusy(0);
        note("Emoji : "+((e&&e.message)||"échec de la requête"))})}
  return r.jsx("button",{className:"svm-tbtn dzm-emo",disabled:!!busy,
    title:"Poser un emoji sur les mots-clés des sous-titres (feu, lune, "+
      "vague, poulpe, or, fusée) — un clip par mot, sur la piste d'overlay "+
      "la plus haute. Annuler les retire.",
    "aria-label":"Poser les emoji des mots-clés",
    onClick:go,children:busy?"…":"emoji"})};

/* ── export contrat ───────────────────────────────────────────────────────── */
var DzTracks={ready:!0,TrackAdd:DzmTrackAdd,headBtns:dzmHeadBtns,
  WordAnimChip:DzmWordAnimChip,EmojiBtn:DzmEmojiBtn,
  tracksOf:svmTracksOf,from:svmTracksFrom,payload:svmTracksPayload,
  busSync:svmTrackBusSync,skin:dzmSkin,
  move:dzmMove,moveTo:dzmMoveTo,add:dzmAdd,remove:dzmRemove,group:dzmGroup,
  clipsOn:dzmClipsOn,emojiClips:dzmEmojiClips,WORD_ANIMS:DZM_WORD_ANIMS,
  DEFAULTS:DZM_DEFAULT_TRACKS};
window.DzTracks=DzTracks;
