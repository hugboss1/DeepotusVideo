/* ── Piste de sous-titres — couche window.DzSubs ─────────────────────────────
   Injecté dans frontend/dist/assets/index-*.js juste APRÈS le bloc vfxrack,
   MÊME scope module : les alias du bundle (r.jsx / r.jsxs, x.useState…) sont
   accessibles directement. Aucune dépendance aux helpers sonvfx (svm*) ni au
   rack VFX : la couche est autonome, et le Montage retombe proprement sur son
   comportement d'avant si elle est absente (`window.DzSubs && ready`).
   Styles : /shared/subs.css (préfixe .sub-, jeu de tokens à repli).

   Modèle d'interaction : celui des racks maison (sfxstudio, vfxrack) —
   tiroir latéral, onglets à compteurs réels, recherche « / », modules
   repliables, un seul point d'écriture d'état.

   Exporte (contrat) :
     window.DzSubs = {ready, Drawer, Overlay, Style, Segments, Alert,
                      defaultStyle, PRESETS, FONTS, ANIMS,
                      words, warnings, reflow, splitAt, mergeAt,
                      parse, toSrt, toVtt, toTxt, tc, parseTc,
                      svc, retry}

   - Drawer({open,onClose,segments,onChange,style,onStyle,playhead,onSeek,
             dur,selId,onSelect,onNote,srcName}) — le tiroir complet :
     onglet « Segments » (liste éditable, début/fin 00:00.000 avec « caler sur
     la tête », ajout / fusion / découpe / suppression, recherche, œil de
     visibilité, caractères par sous-titre, import / export) et onglet
     « Style » (préréglages, police, fond, contour, ombre, karaoké, animation).
   - Overlay({segments,style,t,frame}) — le rendu des sous-titres DANS le
     lecteur, avec surlignage KARAOKÉ du mot actif.
   - warnings(segments,style) — vitesse de lecture, segments trop courts /
     trop longs, chevauchements, lignes trop larges. Rendus à côté du segment
     fautif, avec le bouton qui corrige.

   ── Contrat backend attendu (écrit en parallèle) ──────────────────────────
   GET  /api/subtitles/presets
        → {"presets":[{id,label,style}]}                (repli : PRESETS local)
   GET  /api/subtitles/fonts
        → {"fonts":[{id,label,file?,url?}]}             (repli : FONTS local)
        `url` sert une @font-face : l'aperçu dessine alors avec la fonte
        EMBARQUÉE que ffmpeg gravera, pas avec une fonte système voisine.
   POST /api/subtitles/transcribe  {src, clips, lang, cps}
        → {"job_id": "..."}                             (AUCUN repli local)
        `clips` permet le chemin GRATUIT : la narration déjà écrite est calée
        sur les silences réels au lieu d'être re-devinée contre paiement.
   GET  /api/subtitles/jobs/{id}
        → {status:"pending|running|done|failed", pct, step, segments?, error?}
   POST /api/subtitles/check  {segments, style}
        → {"warnings":[{i,kind,msg,sev,fix?,fixLabel?,need?}]}
                                                        (repli : calcul local)
   POST /api/subtitles/export {format, segments, style}
        → texte                                         (repli : fabriqué ici)
        Le format `ass` n'a PAS de repli : il porte le style et le karaoké,
        c'est le fichier même que ffmpeg grave au rendu.

   Le repli SPA de ce backend renvoie index.html en 200 : on ne se fie donc
   JAMAIS à res.ok seul, toujours au Content-Type (gotcha déjà payé par le
   rack VFX).

   ── Backend absent : on le DIT, et on ne ment pas sur l'étendue ───────────
   Tout ce qui compte ici est LOCAL : écrire, découper, styler, voir le
   karaoké, exporter .srt / .vtt / .txt — rien de tout cela ne touche au
   réseau. Seule la transcription automatique a besoin du backend. Le bandeau
   `sub-alert` nomme donc la route muette ET dit ce qui marche quand même,
   au lieu de laisser croire que le panneau est cassé. Une sonde partagée
   redemande /api/subtitles/presets à intervalle croissant tant que le tiroir
   est monté ; au premier succès, préréglages et polices du moteur reviennent
   seuls, sans rouvrir le tiroir. */

/* ── outils ───────────────────────────────────────────────────────────────── */
function subsClamp(v,a,b){v=Number(v);if(!isFinite(v))v=a;return v<a?a:v>b?b:v}
function subsN(v,d){var n=Number(v);return isFinite(n)?n:d}
function subsRound(v,dec){var m=Math.pow(10,dec||0);return Math.round(v*m)/m}
function subsPad(n,w){var s=String(Math.floor(Math.abs(n)));
  while(s.length<w)s="0"+s;return s}
/* accord en nombre — « 1 répliques » se lit comme une machine */
function subsPl(n,un,plur){return n+" "+(Math.abs(n)<2?un:(plur||un+"s"))}
/* 00:00.000 — le format EXACT des champs de la barre */
function subsTc(s){
  s=Math.max(0,subsN(s,0));
  var ms=Math.round(s*1000),m=Math.floor(ms/60000),r2=ms%60000;
  return subsPad(m,2)+":"+subsPad(Math.floor(r2/1000),2)+"."+subsPad(r2%1000,3)}
/* accepte 00:00.000, 0:00.0, 00:00:00,000 (SRT) et les secondes nues */
function subsParseTc(txt,fb){
  var s=String(txt==null?"":txt).trim().replace(",",".");
  if(!s)return fb;
  var p=s.split(":"),v=null;
  if(p.length===1)v=Number(p[0]);
  else if(p.length===2)v=Number(p[0])*60+Number(p[1]);
  else if(p.length===3)v=Number(p[0])*3600+Number(p[1])*60+Number(p[2]);
  return isFinite(v)&&v>=0?v:fb}
/* JSON strict : le repli SPA répond 200 + text/html, res.ok ne suffit pas */
function subsJson(url,opt){
  return fetch(url,opt).then(function(res){
    var ct=(res.headers.get("content-type")||"").toLowerCase();
    if(!res.ok||ct.indexOf("json")<0)throw new Error("réponse non JSON");
    return res.json()})}
function subsPost(url,body){
  return subsJson(url,{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify(body||{})})}

/* ── modèle ───────────────────────────────────────────────────────────────────
   Un sous-titre est un CLIP de la piste s1 du Montage : {id,tr:"s1",start,end,
   label,text,words?,hidden?}. `label` n'existe que pour la timeline (elle
   affiche c.label) — le texte fait foi et `label` le suit toujours. */
function subsLabelOf(txt){
  var t=String(txt==null?"":txt).replace(/\s+/g," ").trim();
  if(!t)return "(vide)";
  return t.length>46?t.slice(0,45)+"…":t}
var SUBS_SEQ=0;
function subsNewId(){SUBS_SEQ++;return "s1c"+Date.now().toString(36)+SUBS_SEQ}
function subsMake(start,end,text){
  return {id:subsNewId(),tr:"s1",start:subsRound(start,3),end:subsRound(end,3),
    text:String(text||""),label:subsLabelOf(text)}}
function subsSort(list){
  return (list||[]).slice().sort(function(a,b){return a.start-b.start})}
/* place libre à partir de la tête de lecture : si un sous-titre couvre déjà
   `t`, on se pose APRÈS lui, et on s'arrête avant le suivant. Un bouton
   « ajouter » ne doit jamais fabriquer lui-même le chevauchement qu'il ira
   ensuite signaler comme une faute. */
function subsFreeSlot(segs,t,dur){
  var list=subsSort(segs),d=Math.max(1,subsN(dur,60));
  var s0=subsClamp(t,0,Math.max(0,d-.4));
  list.forEach(function(s){
    if(s0>=s.start-1e-6&&s0<s.end)s0=s.end+.04});
  s0=subsClamp(s0,0,Math.max(0,d-.4));
  var s1=Math.min(d,s0+2);
  list.forEach(function(s){if(s.start>s0&&s.start<s1)s1=s.start-.02});
  if(s1-s0<.4)s1=s0+.4;
  return {start:subsRound(s0,3),end:subsRound(s1,3)}}
/* toute écriture d'un segment passe ici : le label reste synchrone du texte */
function subsWith(seg,patch){
  var o=Object.assign({},seg,patch);
  if(patch&&patch.text!=null)o.label=subsLabelOf(patch.text);
  o.start=subsRound(subsN(o.start,0),3);
  o.end=subsRound(Math.max(subsN(o.start,0)+.05,subsN(o.end,0)),3);
  return o}

/* ── découpage en mots + timings (le karaoké) ──────────────────────────────
   Si le backend a fourni des timings par mot (`words`), ils font autorité et
   sont seulement recalés dans [start,end]. Sinon on répartit au prorata du
   nombre de caractères — c'est ce que fait la barre pour son surlignage, et
   à l'œil le résultat est le même. La provenance est affichée (« aligné » vs
   « réparti ») : on n'annonce jamais un alignement qu'on n'a pas. */
function subsWords(seg){
  if(!seg)return [];
  var t0=subsN(seg.start,0),t1=Math.max(t0+.05,subsN(seg.end,t0+1));
  var raw=Array.isArray(seg.words)?seg.words:null;
  if(raw&&raw.length){
    var out=[],n=raw.length;
    for(var i=0;i<n;i++){
      var w=raw[i]||{};
      var a=subsClamp(subsN(w.t0!=null?w.t0:w.start,t0),t0,t1),
          b=subsClamp(subsN(w.t1!=null?w.t1:w.end,a+.15),a+.02,t1);
      out.push({w:String(w.w!=null?w.w:w.word||""),t0:a,t1:b,src:"align"})}
    return out}
  var parts=String(seg.text||"").split(/(\s+)/).filter(function(s){return s.trim()!==""});
  if(!parts.length)return [];
  var tot=0,ws=parts.map(function(p){var c=p.length+1;tot+=c;return c});
  var acc=t0,span=t1-t0,res=[];
  for(var j=0;j<parts.length;j++){
    var d=span*(ws[j]/tot);
    res.push({w:parts[j],t0:acc,t1:j===parts.length-1?t1:acc+d,src:"split"});
    acc+=d}
  return res}
/* index du mot actif à l'instant t (-1 si aucun) */
function subsActiveWord(ws,t){
  for(var i=0;i<ws.length;i++)if(t>=ws[i].t0&&t<ws[i].t1)return i;
  if(ws.length&&t>=ws[ws.length-1].t1)return ws.length-1;
  return -1}
function subsAt(segs,t){
  var list=segs||[];
  for(var i=0;i<list.length;i++){
    var s=list[i];
    if(s.hidden)continue;
    if(t>=s.start&&t<s.end)return s}
  return null}

/* ── césure : le texte tel qu'il apparaîtra (lignes) ───────────────────────── */
function subsLines(text,maxc){
  var t=String(text||"");
  if(t.indexOf("\n")>=0)return t.split("\n");
  var mc=Math.max(8,subsN(maxc,42));
  var words=t.split(/\s+/).filter(Boolean),lines=[],cur="";
  for(var i=0;i<words.length;i++){
    var w=words[i];
    if(!cur){cur=w;continue}
    if((cur+" "+w).length<=mc)cur+=" "+w;else{lines.push(cur);cur=w}}
  if(cur)lines.push(cur);
  return lines.length?lines:[""]}

/* ── recomposition « caractères par sous-titre » ───────────────────────────
   On ne redécoupe pas segment par segment (ça produirait des micro-lignes) :
   on regroupe les segments qui se suivent (trou < 0,4 s), on remet leurs mots
   bout à bout AVEC leurs timings, puis on repack en lignes ≤ `maxc` en
   coupant aux frontières de mots. Chaque nouveau segment prend le t0 de son
   premier mot et le t1 du dernier : le calage ne dérive jamais. */
function subsReflow(segs,maxc){
  var list=subsSort(segs),mc=Math.max(10,subsN(maxc,42)),out=[];
  var i=0;
  while(i<list.length){
    var grp=[list[i]],j=i+1;
    while(j<list.length&&list[j].start-grp[grp.length-1].end<.4&&
          !list[j].hidden&&!grp[0].hidden){grp.push(list[j]);j++}
    var ws=[];
    grp.forEach(function(s){ws=ws.concat(subsWords(s))});
    if(!ws.length){out.push(grp[0]);i=j;continue}
    var cur=[],curLen=0;
    function flush(){
      if(!cur.length)return;
      var txt=cur.map(function(w){return w.w}).join(" ");
      var seg=subsMake(cur[0].t0,cur[cur.length-1].t1,txt);
      if(cur[0].src==="align")
        seg.words=cur.map(function(w){return {w:w.w,t0:w.t0,t1:w.t1}});
      if(grp[0].hidden)seg.hidden=!0;
      out.push(seg);cur=[];curLen=0}
    for(var k=0;k<ws.length;k++){
      var w=ws[k],add=(curLen?1:0)+w.w.length;
      if(curLen&&curLen+add>mc)flush();
      cur.push(w);curLen+=(curLen?1:0)+w.w.length}
    flush();
    i=j}
  return out}

/* découpe d'un segment à l'instant t — les mots partent du bon côté */
function subsSplitAt(segs,id,t){
  var list=subsSort(segs),out=[],done=!1;
  list.forEach(function(s){
    if(s.id!==id||t<=s.start+.05||t>=s.end-.05){out.push(s);return}
    var ws=subsWords(s),a=[],b=[];
    ws.forEach(function(w){if(w.t1<=t||w.t0<t&&(t-w.t0)>(w.t1-t))a.push(w);else b.push(w)});
    /* jamais de côté vide : on rééquilibre d'un mot plutôt que de produire
       un segment sans texte */
    if(!a.length&&b.length>1)a.push(b.shift());
    if(!b.length&&a.length>1)b.unshift(a.pop());
    var s1=subsWith(s,{end:t,text:a.map(function(w){return w.w}).join(" ")});
    var s2=subsMake(t,s.end,b.map(function(w){return w.w}).join(" "));
    if(s.hidden){s1.hidden=!0;s2.hidden=!0}
    delete s1.words;
    out.push(s1);out.push(s2);done=!0});
  return done?out:null}
/* fusion avec le suivant */
function subsMergeAt(segs,id){
  var list=subsSort(segs),i=-1;
  for(var k=0;k<list.length;k++)if(list[k].id===id){i=k;break}
  if(i<0||i>=list.length-1)return null;
  var a=list[i],b=list[i+1];
  var out=list.slice();
  var m=subsWith(a,{end:Math.max(a.end,b.end),
    text:(String(a.text||"").trim()+" "+String(b.text||"").trim()).trim()});
  if(Array.isArray(a.words)&&Array.isArray(b.words))m.words=a.words.concat(b.words);
  else delete m.words;
  out.splice(i,2,m);
  return out}

/* ── avertissements de qualité et correctifs NÉGOCIÉS ──────────────────────
   Calculés ici, et affichés DANS la ligne fautive (jamais dans un rapport
   séparé). Le backend peut renvoyer sa propre liste (POST /api/subtitles/check,
   qui mesure en PIXELS avec la vraie fonte) ; elle gagne. Hors ligne, le
   calcul local applique EXACTEMENT les mêmes règles — sinon le panneau
   mentirait dès que le backend tousse.

   ── Ce qu'un correctif n'a PAS le droit de faire ───────────────────────────
   La piste est un système sous contraintes : chaque segment est borné par ses
   voisins. « Étirer à 1,35 s » poussait la fin du n°1 à 01.609 alors que le
   n°2 commence à 01.419 : 190 ms de chevauchement fabriqués par le bouton
   censé réparer, pendant que la carte du dessous avertissait déjà que la
   frontière était trop serrée. Le bouton mentait, et personne ne le voyait.

   Un correctif est donc un PLAN, et un plan :
     * ne prend que le silence RÉELLEMENT libre (jamais un écart déjà serré) ;
     * dit dans `effect`, AVANT le clic, ce qu'il fait — y compris aux voisins ;
     * annonce la valeur qu'il atteint VRAIMENT (`granted`), pas celle visée ;
     * quand rien ne passe, n'affiche AUCUN bouton et explique (`blocked`),
       en proposant la renégociation (`alt`) quand elle existe.
   Les invariants sont verrouillés côté moteur par
   `backend/tests/test_subtitle_fixes.py`. */
var SUBS_CPS_MAX=20;    /* caractères/seconde lisibles (norme sous-titrage FR) */
var SUBS_MIN_S=1;       /* en deçà, l'œil n'a pas le temps de se poser */
var SUBS_MAX_S=7;       /* au-delà, le sous-titre traîne */
var SUBS_MIN_GAP=.08;   /* deux images à 25 i/s entre deux sous-titres */

function subsFr(v,d){
  var m=Math.pow(10,d==null?2:d),s=(Math.round(v*m)/m).toFixed(d==null?2:d);
  if(s.indexOf(".")>=0)s=s.replace(/0+$/,"").replace(/\.$/,"");
  return s.replace(".",",")}
function subsFrMs(v){return Math.round(v*1000)+" ms"}
function subsRank(i){return "n°"+(i+1)}

/* place libre APRÈS le segment i : si l'écart avec le suivant est déjà sous
   le seuil, elle vaut 0 — c'est ce zéro qui empêche un correctif de grignoter
   une frontière déjà trop serrée. */
function subsRoomAfter(list,i,dur){
  if(i+1<list.length)return Math.max(0,list[i+1].start-SUBS_MIN_GAP-list[i].end);
  return dur>0?Math.max(0,dur-list[i].end):Infinity}
function subsRoomBefore(list,i){
  if(i>0)return Math.max(0,list[i].start-SUBS_MIN_GAP-list[i-1].end);
  return Math.max(0,list[i].start)}

function subsPlan(action,ok,label,effect,ops,extra){
  var p={action:action,ok:!!ok,label:label||"",effect:effect||"",
    ops:ops||[],touches:[],alt:null};
  if(extra)Object.keys(extra).forEach(function(k){p[k]=extra[k]});
  return p}
function subsBlockedPlan(action,why,extra){
  return subsPlan(action,!1,"","",[],Object.assign({blocked:why},extra||{}))}
function subsSetOp(s,f){return Object.assign({op:"set",id:s.id},f)}

function subsPlanStretch(list,i,target,dur){
  var s=list[i],len=s.end-s.start;
  var want=Math.max(len,target),need=want-len;
  if(need<=1e-6)return subsBlockedPlan("etirer","Le segment dure déjà assez longtemps.");
  var after=subsRoomAfter(list,i,dur),before=subsRoomBefore(list,i);
  var ta=Math.min(need,after),tb=Math.min(need-ta,before);
  var got=len+ta+tb,deficit=Math.max(0,want-got);
  var alt=null;
  if(deficit>.001&&i+1<list.length){
    var lastEnd=list[list.length-1].end+deficit;
    if(dur>0&&lastEnd>dur+1e-6)
      alt=subsBlockedPlan("etirer","Décaler les suivants sortirait le dernier "+
        "sous-titre de la vidéo ("+subsFrMs(lastEnd-dur)+" de trop).");
    else{
      var ops=[subsSetOp(s,{start:subsRound(s.start-tb,3),
        end:subsRound(s.end+ta+deficit,3)})],touches=[];
      for(var j=i+1;j<list.length;j++){
        ops.push(subsSetOp(list[j],{start:subsRound(list[j].start+deficit,3),
          end:subsRound(list[j].end+deficit,3)}));
        touches.push(j)}
      alt=subsPlan("etirer",!0,"Étirer à "+subsFr(want)+" s en décalant la suite",
        "Décale les "+(list.length-i-1)+" sous-titres suivants de "+
        subsFrMs(deficit)+". Leur texte ne suivra plus la voix — à ne faire "+
        "que si le montage suit.",ops,
        {touches:touches,granted:subsRound(want,3),requested:subsRound(want,3)})}}
  if(got<=len+1e-6){
    var why=i+1<list.length
      ?"le "+subsRank(i+1)+" commence "+subsFrMs(Math.max(0,list[i+1].start-s.end))+
       " après la fin de celui-ci (plancher "+subsFrMs(SUBS_MIN_GAP)+")"
      :"le segment finit déjà avec la vidéo";
    return subsBlockedPlan("etirer","Aucun silence disponible : "+why+
      ". Raccourcissez le texte, ou fusionnez avec le voisin.",{alt:alt})}
  var bits=[];
  if(ta>.001)bits.push("prend "+subsFrMs(ta)+" de silence après");
  if(tb>.001)bits.push(subsFrMs(tb)+" de silence avant");
  var eff=bits.length?"Le segment "+bits.join(" et ")+". Aucun voisin ne bouge."
    :"Aucun voisin ne bouge.";
  if(got<want-.005)
    eff+=" Il faudrait "+subsFr(want)+" s : le voisin ne laisse pas plus. "+
      "Le problème sera réduit, pas effacé.";
  return subsPlan("etirer",!0,"Étirer à "+subsFr(got)+" s",eff,
    [subsSetOp(s,{start:subsRound(s.start-tb,3),end:subsRound(s.end+ta,3)})],
    {granted:subsRound(got,3),requested:subsRound(want,3),alt:alt})}

function subsPlanBoundary(list,i){
  if(i<1)return subsBlockedPlan("separer","Pas de voisin avant ce segment.");
  var p=list[i-1],c=list[i],gap=c.start-p.end,need=SUBS_MIN_GAP-gap;
  if(need<=1e-6)return subsBlockedPlan("separer","La frontière est déjà assez large.");
  var dp=p.end-p.start,dc=c.end-c.start;
  var gp=Math.max(0,dp-SUBS_MIN_S),gc=Math.max(0,dc-SUBS_MIN_S),tot=gp+gc;
  if(tot>=need-1e-6){
    var tp=tot>0?need*(gp/tot):0,tc=need-tp;
    if(tc>gc){tc=gc;tp=need-gc}
    return subsPlan("separer",!0,"Séparer de "+subsFrMs(SUBS_MIN_GAP),
      "Le "+subsRank(i-1)+" perd "+subsFrMs(tp)+" à la fin, le "+subsRank(i)+
      " "+subsFrMs(tc)+" au début. Écart final "+subsFrMs(SUBS_MIN_GAP)+
      ", et les deux restent au-dessus de "+subsFr(SUBS_MIN_S)+" s.",
      [subsSetOp(p,{end:subsRound(p.end-tp,3)}),
       subsSetOp(c,{start:subsRound(c.start+tc,3)})],{touches:[i-1]})}
  var fus=null,md=c.end-p.start;
  if(md<=SUBS_MAX_S+1e-6)
    fus=subsPlan("fusionner",!0,"Fusionner les deux",
      "Le "+subsRank(i-1)+" et le "+subsRank(i)+" deviennent un seul "+
      "sous-titre de "+subsFr(md)+" s. Le texte est mis bout à bout, le "+
      "calage par mot est refait.",
      [subsSetOp(p,{end:subsRound(c.end,3),
        text:(String(p.text||"").trim()+" "+String(c.text||"").trim()).trim(),
        words:null}),{op:"remove",id:c.id}],{touches:[i]});
  return subsBlockedPlan("separer",
    "Impossible sans passer sous "+subsFr(SUBS_MIN_S)+" s : le "+subsRank(i-1)+
    " dure "+subsFr(dp)+" s, le "+subsRank(i)+" "+subsFr(dc)+" s, et il manque "+
    subsFrMs(need-tot)+". Fusionnez-les, ou raccourcissez un texte.",{alt:fus})}

/* découpe : les mots se touchent, donc une coupe brute collerait les deux
   moitiés et fabriquerait l'avertissement suivant. On ouvre la respiration. */
function subsPlanSplit(list,i,maxc,maxLines){
  var s=list[i];
  var parts=subsReflow([s],Math.max(10,maxc*Math.max(1,maxLines)));
  if(parts.length<2)
    return subsBlockedPlan("decouper","Le texte tient en un seul bloc de "+
      maxc+" caractères : rien à découper.");
  for(var k=0;k<parts.length-1;k++)
    if(parts[k+1].start-parts[k].end<SUBS_MIN_GAP-1e-6)
      parts[k].end=subsRound(Math.max(parts[k].start+.12,
        parts[k+1].start-SUBS_MIN_GAP),3);
  var durs=parts.map(function(p){return subsFr(p.end-p.start)+" s"}).join(" + ");
  return subsPlan("decouper",!0,"Découper en "+parts.length+" sous-titres",
    "Le segment devient "+parts.length+" sous-titres ("+durs+"), coupés sur "+
    "les mots avec "+subsFrMs(SUBS_MIN_GAP)+" de respiration entre eux. Les "+
    "voisins ne bougent pas.",
    [{op:"replace",id:s.id,"with":parts.map(function(p){
      return {start:p.start,end:p.end,text:subsLines(p.text,maxc).join("\n"),
        words:p.words||null}})}],{granted:parts.length})}

function subsPlanRewrap(list,i,maxc,maxLines){
  var s=list[i],flat=String(s.text||"").replace(/\s+/g," ").trim();
  var ln=subsLines(flat,maxc);
  if(ln.length<=maxLines){
    var nt=ln.join("\n");
    if(nt===s.text)
      return subsBlockedPlan("replier","Le texte est déjà replié au mieux "+
        "pour "+maxc+" caractères par ligne.");
    return subsPlan("replier",!0,"Replier en "+ln.length+" lignes",
      "Le texte est replié à "+maxc+" caractères par ligne ("+
      ln.map(function(x){return x.length}).join(" / ")+"). Le début, la fin "+
      "et le calage par mot ne bougent pas.",
      [subsSetOp(s,{text:nt})],{granted:ln.length})}
  var p=subsPlanSplit(list,i,maxc,maxLines);
  if(p.ok)p.effect="Le texte fait "+ln.length+" lignes à "+maxc+
    " caractères : il ne tient pas en "+maxLines+". "+p.effect;
  return p}

/* application d'un plan — les `ops` sont des DONNÉES ({op,id,start,end,text}),
   les mêmes que celles du moteur. Trois verbes, pas un de plus. */
function subsApplyPlan(list,plan){
  if(!plan||!plan.ok||!plan.ops||!plan.ops.length)return list;
  var by={};plan.ops.forEach(function(o){if(o&&o.id!=null)by[o.id]=o});
  var out=[];
  subsSort(list).forEach(function(s){
    var o=by[s.id];
    if(!o){out.push(s);return}
    if(o.op==="remove")return;
    if(o.op==="replace"){
      (o["with"]||[]).forEach(function(n){
        var m=subsMake(subsN(n.start,s.start),subsN(n.end,s.end),String(n.text||""));
        if(n.words&&n.words.length)m.words=n.words;
        if(s.hidden)m.hidden=!0;
        out.push(m)});
      return}
    var pt={};
    if(o.start!=null)pt.start=subsN(o.start,s.start);
    if(o.end!=null)pt.end=subsN(o.end,s.end);
    if(o.text!=null)pt.text=String(o.text);
    var ns=subsWith(s,pt);
    /* bornes déplacées : le calage par mot hérité devient faux. On le laisse
       se refaire au prorata plutôt que de laisser le karaoké dériver. */
    if(Object.prototype.hasOwnProperty.call(o,"words")){
      if(o.words==null)delete ns.words;else ns.words=o.words}
    else if(o.start!=null||o.end!=null)delete ns.words;
    out.push(ns)});
  return subsSort(out)}

function subsWarnings(segs,style,dur){
  var list=subsSort(segs),out=[],mc=Math.max(10,subsN(style&&style.maxChars,42));
  var maxLines=Math.max(1,subsN(style&&style.maxLines,2));
  var d=subsN(dur,0);
  function push(s,i,kind,sev,msg,plan,about){
    out.push({id:s.id,i:i,kind:kind,sev:sev,msg:msg,plan:plan||null,
      about:about||[i]})}
  list.forEach(function(s,i){
    /* la FRONTIÈRE d'abord : elle ne dépend que des bornes, et un segment
       encore vide ne doit pas masquer le chevauchement qu'il cause.
       ANCRAGE : sur le segment qui COMMENCE trop tôt (le second), et le
       message nomme l'autre par son rang — c'est le défaut « 60 ms depuis le
       précédent affiché sur la mauvaise carte » qui est fermé ici. */
    if(i){
      var gap=s.start-list[i-1].end;
      if(gap<-1e-6)
        push(s,i,"chevauche","err","Commence "+subsFrMs(-gap)+" AVANT la fin "+
          "du "+subsRank(i-1)+" : les deux s'afficheront ensemble.",
          subsPlanBoundary(list,i),[i-1,i]);
      else if(gap<SUBS_MIN_GAP)
        push(s,i,"intervalle","warn","Commence "+subsFrMs(gap)+" après la fin "+
          "du "+subsRank(i-1)+" : sous "+subsFrMs(SUBS_MIN_GAP)+" le "+
          "changement se verra comme un clignotement.",
          subsPlanBoundary(list,i),[i-1,i])}
    var len=Math.max(.001,s.end-s.start);
    var chars=String(s.text||"").replace(/\s+/g," ").trim().length;
    if(!chars){
      push(s,i,"vide","err","Segment sans texte : rien ne s'affichera, et il "+
        "sortira de l'export.");return}
    var cps=chars/len;
    if(cps>SUBS_CPS_MAX+1e-6){
      var pl=subsPlanStretch(list,i,chars/SUBS_CPS_MAX,d);
      if(!pl.ok&&!(pl.alt&&pl.alt.ok)&&chars>mc)
        pl=subsPlanSplit(list,i,mc,maxLines);
      push(s,i,"vitesse","err",subsFr(cps,1)+" caractères/seconde : au-delà de "+
        SUBS_CPS_MAX+", la lecture décroche.",pl)}
    if(len<SUBS_MIN_S-1e-4)
      push(s,i,"court","warn",subsFr(len)+" s : sous "+subsFr(SUBS_MIN_S)+
        " s l'œil n'a pas le temps de se poser.",
        subsPlanStretch(list,i,SUBS_MIN_S,d));
    if(len>SUBS_MAX_S+1e-4)
      push(s,i,"long","info",subsFr(len,1)+" s à l'écran : au-delà de "+
        SUBS_MAX_S+" s, découpez.",subsPlanSplit(list,i,mc,maxLines));
    var ln=subsLines(s.text,mc);
    if(ln.length>maxLines)
      push(s,i,"lignes","warn",ln.length+" lignes affichées (maximum "+
        maxLines+").",subsPlanRewrap(list,i,mc,maxLines))});
  return out}
/* ═══════════════════ LE VERDICT — la SEULE fonction qui décide ═══════════════
   La sévérité de chaque réplique ET tous les comptes affichés sont calculés
   ICI, une fois, pour une piste donnée. La timeline, la liste, les pastilles
   de ligne, les badges d'onglet, la chip de la barre d'outils et l'inspecteur
   LISENT ce résultat ; aucune surface ne refait le sien.

   Pourquoi : quatre endroits calculaient leur propre verdict et se
   contredisaient DANS LA MÊME IMAGE — la timeline peignait 9 pastilles
   « critiques » (calcul local) pendant que la liste, juste à côté, en peignait
   8 en ambre et une seule en rouge (calcul du moteur), et le badge d'onglet
   annonçait un troisième chiffre (des AVERTISSEMENTS, pas des répliques) que
   rien à l'écran ne désignait. Un panneau qui se contredit ne vaut rien.

   ── Ce que compte chaque nombre affiché, nommé une fois pour toutes ─────────
     repliques  — lignes posées sur la piste S1 (masquées comprises)
     masquees   — lignes hors rendu et hors export
     signalees  — lignes portant AU MOINS un défaut, quelle qu'en soit la gravité
     bloquantes — lignes portant au moins un défaut BLOQUANT (sous-ensemble)
     defauts    — défauts au total (une ligne peut en porter plusieurs)
     ecarts     — écarts entre l'aperçu et la GRAVURE : ils portent sur le
                  STYLE, pas sur une réplique, et ne sont jamais additionnés
                  aux quatre précédents.
   Deux nombres différents à l'écran ne désignent donc jamais la même chose,
   et chacun porte son unité en toutes lettres. */
var SUBS_SEVN={info:1,warn:2,err:3};
var SUBS_SEVLAB={err:"bloquant",warn:"à vérifier",info:"remarque"};
function subsSevMax(a,b){
  if(!a)return b||null;
  if(!b)return a;
  return (SUBS_SEVN[b]||0)>(SUBS_SEVN[a]||0)?b:a}
/* Signature de CONTENU : deux surfaces qui passent la même piste obtiennent le
   même verdict, quelle que soit l'identité des objets. Elle sert aussi de clé
   au contrôle backend — un résultat du moteur ne s'applique QU'À la piste pour
   laquelle il a été calculé. Sans ce verrou, la liste affichait le verdict
   d'une version précédente pendant que la timeline affichait celui d'aujourd'hui. */
function subsKeyOf(segs,style,dur){
  return JSON.stringify([subsSort(segs).map(function(s){
      return [s.id,subsRound(subsN(s.start,0),3),subsRound(subsN(s.end,0),3),
        String(s.text||""),s.hidden?1:0]}),
    style||null,subsRound(subsN(dur,0),3)])}
/* Résultat de POST /api/subtitles/check, rangé AVEC la clé de la piste qu'il
   mesure. Module-level : le tiroir n'en est plus le propriétaire — sinon la
   timeline lirait le calcul local pendant que la liste lit le moteur, ce qui
   est exactement le défaut que ce bloc ferme. */
var SUBS_CHK={key:null,warns:null,style:null,unsupported:null,tick:0,subs:[]};
function subsChkEmit(){
  SUBS_CHK.subs.slice().forEach(function(f){try{f()}catch(_e){}})}
function subsChkPut(key,d){
  SUBS_CHK.key=key||null;
  SUBS_CHK.warns=d&&Array.isArray(d.warnings)?d.warnings:null;
  SUBS_CHK.style=d&&Array.isArray(d.style_warnings)?d.style_warnings:null;
  SUBS_CHK.unsupported=d&&d.unsupported&&typeof d.unsupported==="object"
    ?d.unsupported:null;
  SUBS_CHK.tick++;subsChkEmit()}
function subsChkClear(){
  if(SUBS_CHK.key===null&&!SUBS_CHK.warns&&!SUBS_CHK.style&&!SUBS_CHK.unsupported)
    return;
  subsChkPut(null,null)}
function subsChkSub(f){
  SUBS_CHK.subs.push(f);
  return function(){
    var i=SUBS_CHK.subs.indexOf(f);
    if(i>=0)SUBS_CHK.subs.splice(i,1)}}

/* ── zone sûre : le repère TRACÉ dans l'aperçu et les réglages doivent dire la
   même chose ───────────────────────────────────────────────────────────────
   L'aperçu dessinait une zone sûre à 10 % et posait simultanément le texte à
   9 % de marge : le bas du sous-titre livré par défaut passait SOUS la ligne,
   sans un mot. La ligne pleine « zone sûre 10 % » fait foi. Un réglage qui la
   franchit devient un écart annoncé COMME LES AUTRES, avec le geste qui le
   ferme — et le défaut d'usine se tient au-dessus des DEUX repères que
   l'aperçu trace (10 % zone sûre, 13 % bande d'UI des réseaux en 9:16), parce
   qu'un défaut d'usine qui déclenche son propre avertissement n'en est pas un. */
function subsSafeIssues(style){
  var st=Object.assign(subsDefaultStyle(),style||{}),out=[];
  var side=subsRound((100-subsClamp(subsN(st.width,80),20,100))/2,1);
  var mv=subsRound(subsN(st.marginV,SUBS_MARGIN_DEF),1);
  var wSafe=100-2*SUBS_SAFE_TITLE;
  if(side<SUBS_SAFE_TITLE-.05)
    out.push({msg:"Largeur du bloc "+Math.round(subsN(st.width,80))+" % : ses "+
      "bords tombent à "+subsFr(side,1)+" % de l'image et sortent donc de la "+
      "zone sûre "+SUBS_SAFE_TITLE+" % que l'aperçu trace.",
      sev:"warn",about:[],cle:"safe_width",
      fix:{champ:"width",valeur:wSafe,
        label:"Rentrer dans la zone sûre",
        effect:"La largeur passe à "+wSafe+" % : les deux marges latérales "+
          "tombent exactement sur la ligne "+SUBS_SAFE_TITLE+" %."}});
  if(String(st.valign)!=="middle"&&mv<SUBS_SAFE_TITLE-.05)
    out.push({msg:"Marge du bord "+subsFr(mv,1)+" % : le bord du texte passe "+
      "SOUS la ligne de zone sûre "+SUBS_SAFE_TITLE+" % que l'aperçu trace.",
      sev:"warn",about:[],cle:"safe_margin",
      fix:{champ:"marginV",valeur:SUBS_SAFE_TITLE,
        label:"Remonter à "+SUBS_SAFE_TITLE+" %",
        effect:"La marge du bord passe à "+SUBS_SAFE_TITLE+" % : le texte se "+
          "pose exactement sur la ligne de zone sûre."}});
  return out}
/* le même test, en booléen, pour l'aperçu : le bandeau de placement doit le
   dire AU MOMENT du geste, pas seulement dans l'onglet Style */
function subsOutOfSafe(style){return subsSafeIssues(style).length>0}

var SUBS_VD={k:null,v:null};
function subsVerdict(segs,style,dur){
  var list=subsSort(segs||[]),st=Object.assign(subsDefaultStyle(),style||{});
  var key=subsKeyOf(list,st,dur);
  var ck=key+"#"+SUBS_CHK.tick;
  if(SUBS_VD.k===ck)return SUBS_VD.v;
  /* Le calcul local tourne TOUJOURS : hors ligne il fait foi, en ligne il sert
     de repli tant que le moteur n'a pas répondu POUR CETTE piste. Le moteur
     gagne quand il a répondu pour la MÊME clé — jamais pour une autre. */
  var warns=subsWarnings(list,st,dur),src="local";
  if(SUBS_CHK.key===key&&SUBS_CHK.warns){
    var byId={};list.forEach(function(s){byId[s.id]=s});
    warns=SUBS_CHK.warns.map(function(w){
      var s=(w&&w.id!=null&&byId[w.id])||list[subsN(w&&w.i,-1)];
      if(!s)return null;
      return {id:s.id,i:subsN(w.i,-1),kind:String(w.kind||"regle"),
        sev:SUBS_SEVN[String(w.sev)]?String(w.sev):"warn",
        msg:String(w.msg||""),
        about:Array.isArray(w.about)?w.about:[subsN(w.i,-1)],
        plan:w.plan||null}}).filter(Boolean);
    src="moteur"}
  var bySeg={},nSig=0,nBlk=0;
  list.forEach(function(s){bySeg[s.id]={sev:null,n:0,nErr:0,warns:[]}});
  warns.forEach(function(w){
    var e=bySeg[w.id];
    if(!e)return;
    e.warns.push(w);e.n++;
    if(w.sev==="err")e.nErr++;
    e.sev=subsSevMax(e.sev,w.sev)});
  list.forEach(function(s){
    var e=bySeg[s.id];
    if(e.n)nSig++;
    if(e.nErr)nBlk++});
  /* écarts aperçu/gravure : zone sûre d'abord (c'est nous qui la traçons),
     puis ceux du moteur. Même liste, même dédoublonnage, un seul compte. */
  var sty=subsStyleIssues({
    style:(SUBS_CHK.key===key?SUBS_CHK.style:null),
    unsupported:(SUBS_CHK.key===key?SUBS_CHK.unsupported:null),
    safe:subsSafeIssues(st)});
  var v={key:key,source:src,list:warns,bySeg:bySeg,style:sty,
    counts:{repliques:list.length,
      masquees:list.filter(function(s){return !!s.hidden}).length,
      signalees:nSig,bloquantes:nBlk,defauts:warns.length,ecarts:sty.length}};
  SUBS_VD={k:ck,v:v};
  return v}
/* verdict VIDE — la forme exacte du plein, pour que l'hôte n'ait jamais à
   tester `null` avant de lire un compte */
function subsVerdictNil(){
  return {key:"",source:"local",list:[],bySeg:{},style:[],
    counts:{repliques:0,masquees:0,signalees:0,bloquantes:0,defauts:0,ecarts:0}}}
function subsSegState(v,id){
  return (v&&v.bySeg&&v.bySeg[id])||{sev:null,n:0,nErr:0,warns:[]}}

/* ── formats de fichier — TOUT est fabriqué ici, hors ligne ────────────────
   C'est exactement là où la barre nous laisse la place : Kapwing met le
   téléchargement .srt/.vtt derrière un compte, Canva ne sait pas exporter de
   fichier de sous-titres du tout (« exportez en MP4 »). Chez nous : local,
   gratuit, sans filigrane, sans plafond. */
function subsSrtTc(s){
  s=Math.max(0,subsN(s,0));
  var ms=Math.round(s*1000),h=Math.floor(ms/3600000),r2=ms%3600000;
  return subsPad(h,2)+":"+subsPad(Math.floor(r2/60000),2)+":"+
    subsPad(Math.floor(r2%60000/1000),2)+","+subsPad(r2%1000,3)}
function subsVttTc(s){return subsSrtTc(s).replace(",",".")}
function subsToSrt(segs,style){
  var list=subsSort(segs).filter(function(s){return !s.hidden&&String(s.text||"").trim()});
  var mc=Math.max(10,subsN(style&&style.maxChars,42));
  return list.map(function(s,i){
    return (i+1)+"\n"+subsSrtTc(s.start)+" --> "+subsSrtTc(s.end)+"\n"+
      subsLines(s.text,mc).join("\n")+"\n"}).join("\n")}
function subsToVtt(segs,style){
  var list=subsSort(segs).filter(function(s){return !s.hidden&&String(s.text||"").trim()});
  var mc=Math.max(10,subsN(style&&style.maxChars,42));
  return "WEBVTT\n\n"+list.map(function(s){
    return subsVttTc(s.start)+" --> "+subsVttTc(s.end)+"\n"+
      subsLines(s.text,mc).join("\n")+"\n"}).join("\n")}
function subsToTxt(segs){
  return subsSort(segs).filter(function(s){return !s.hidden})
    .map(function(s){return String(s.text||"").replace(/\s+/g," ").trim()})
    .filter(Boolean).join("\n")}
/* import .srt / .vtt — même analyseur, les deux formats ne diffèrent que par
   l'en-tête et le séparateur de millisecondes. */
function subsParse(txt){
  var raw=String(txt||"").replace(/\r/g,"");
  var blocks=raw.split(/\n{2,}/),out=[];
  blocks.forEach(function(b){
    var lines=b.split("\n").filter(function(l){return l.trim()!==""});
    if(!lines.length)return;
    if(/^WEBVTT/i.test(lines[0]))lines.shift();
    if(!lines.length)return;
    var ti=-1;
    for(var i=0;i<lines.length;i++)if(lines[i].indexOf("-->")>=0){ti=i;break}
    if(ti<0)return;
    var p=lines[ti].split("-->");
    var t0=subsParseTc(p[0],null),t1=subsParseTc((p[1]||"").split(/\s+/)[1]||p[1],null);
    if(t0==null||t1==null)return;
    var body=lines.slice(ti+1).join("\n").trim();
    if(!body)return;
    out.push(subsMake(t0,Math.max(t0+.1,t1),body))});
  return out}
function subsDownload(name,text,mime){
  try{
    var b=new Blob([text],{type:(mime||"text/plain")+";charset=utf-8"});
    var u=URL.createObjectURL(b),a=document.createElement("a");
    a.href=u;a.download=name;document.body.appendChild(a);a.click();
    setTimeout(function(){document.body.removeChild(a);URL.revokeObjectURL(u)},400);
    return !0}
  catch(_e){return !1}}

/* ── style ────────────────────────────────────────────────────────────────── */
var SUBS_FONTS_FB=[
  ["Inter","Inter · interface"],["Segoe UI","Segoe UI"],["Arial","Arial"],
  ["Impact","Impact · massif"],["Bahnschrift","Bahnschrift · condensé"],
  ["Franklin Gothic Medium","Franklin Gothic"],["Georgia","Georgia · sérif"],
  ["Trebuchet MS","Trebuchet MS"],["Verdana","Verdana"],["Tahoma","Tahoma"],
  ["Courier New","Courier New · mono"],["Comic Sans MS","Comic Sans MS"]];
/* Animations : SEULES celles que la gravure sait reproduire. « montée » et
   « machine à écrire » ont été retirées — l'ASS n'a rien pour les rendre, et
   un réglage qui n'agit pas sur la vidéo livrée n'a rien à faire ici.
   « fondu » sort en ad, « pop » en 	 sur l'échelle : vérifiés à l'image
   sur une vraie gravure ffmpeg (sonde libass). */
var SUBS_ANIMS=[["none","aucune"],["fade","fondu"],["pop","pop"]];
/* Karaoké : « échelle » (le mot grossit) retiré pour la même raison — l'ASS
   ne sait que basculer une couleur. Restent le remplissage (\k) et la boîte
   (\ko, qui colore la boîte du mot quand un fond est actif). */
var SUBS_KMODES=[["fill","remplissage"],["box","boîte"]];
var SUBS_ALIGN=[["left","gauche","⭰"],["center","centré","≡"],["right","droite","⭲"]];
var SUBS_VALIGN=[["top","haut","⤒"],["middle","milieu","⇔"],["bottom","bas","⤓"]];

function subsDefaultStyle(){
  return {preset:"defaut",font:"Inter",size:42,weight:700,italic:!1,underline:!1,
    upper:!1,tracking:0,align:"center",valign:"bottom",placed:!1,
    /* marge et largeur d'usine = les repères que l'aperçu trace (voir
       SUBS_MARGIN_DEF / SUBS_WIDTH_DEF) : le sous-titre livré sans réglage
       est DANS la zone sûre, pas sous sa ligne. */
    color:"#ffffff",maxChars:42,maxLines:2,
    width:SUBS_WIDTH_DEF,marginV:SUBS_MARGIN_DEF,
    bgOn:!0,bgColor:"#000000",bgOpacity:64,bgPad:12,
    outOn:!0,outColor:"#000000",outW:3,
    shOn:!1,shColor:"#000000",shOff:3,
    karOn:!0,karColor:"#f0b429",karMode:"fill",karBox:"#f0b429",
    anim:"pop"}}
/* préréglages nommés — mêmes intentions que la barre (Default, Pop Art,
   Highlighter, Butter, Dark Outline, Prime), en français, plus trois maison. */
var SUBS_PRESETS=[
  {id:"defaut",label:"Défaut",style:{}},
  {id:"popart",label:"Pop Art",style:{font:"Impact",size:52,weight:900,upper:!0,
    tracking:1,color:"#ffffff",bgOn:!1,outOn:!0,outColor:"#1b1b1f",outW:6,
    shOn:!0,shColor:"#00000099",shOff:5,
    karOn:!0,karColor:"#ffd23f",karMode:"fill",anim:"pop"}},
  {id:"surligneur",label:"Surligneur",style:{font:"Inter",size:44,weight:800,
    upper:!1,color:"#111114",bgOn:!0,bgColor:"#f0b429",
    bgOpacity:100,bgPad:10,outOn:!1,shOn:!1,
    karOn:!0,karMode:"box",karBox:"#ffffff",karColor:"#111114",anim:"fade"}},
  {id:"beurre",label:"Beurre",style:{font:"Georgia",size:44,weight:700,
    color:"#ffe9a8",bgOn:!1,outOn:!0,outColor:"#3a2a06",outW:4,
    shOn:!0,shColor:"#00000066",shOff:2,
    karOn:!0,karColor:"#ffffff",karMode:"fill",anim:"fade"}},
  {id:"contour",label:"Contour sombre",style:{font:"Inter",size:42,weight:700,
    color:"#ffffff",bgOn:!1,outOn:!0,outColor:"#000000",outW:5,
    shOn:!0,shColor:"#000000aa",shOff:2,
    karOn:!0,karColor:"#f0b429",karMode:"fill",anim:"none"}},
  {id:"prime",label:"Prime",style:{font:"Bahnschrift",size:48,weight:800,
    upper:!0,tracking:2,color:"#ffffff",bgOn:!0,bgColor:"#101014",
    bgOpacity:82,bgPad:14,outOn:!1,shOn:!1,
    karOn:!0,karColor:"#4ad4ff",karMode:"fill",anim:"pop"}},
  {id:"abysse",label:"Abysse",style:{font:"Inter",size:44,weight:800,
    color:"#e8f6ff",bgOn:!0,bgColor:"#04121c",bgOpacity:70,
    bgPad:16,outOn:!1,shOn:!1,
    karOn:!0,karColor:"#00e5ff",karMode:"fill",anim:"fade"}},
  {id:"machine",label:"Machine",style:{font:"Courier New",size:36,weight:700,
    upper:!0,tracking:1,color:"#c9ffd0",bgOn:!0,bgColor:"#000000",
    bgOpacity:88,bgPad:8,outOn:!1,shOn:!1,
    karOn:!0,karColor:"#ffffff",karMode:"box",karBox:"#1f7a3a",anim:"none"}},
  {id:"nu",label:"Nu",style:{font:"Inter",size:38,weight:600,color:"#ffffff",
    bgOn:!1,outOn:!1,shOn:!0,shColor:"#00000088",shOff:2,
    karOn:!1,anim:"none"}}];
/* ── nommer un préréglage par ce qu'il FAIT ────────────────────────────────
   « Beurre » et « Prime » ne disent rien : ni la couleur, ni le fond, ni le
   contour. On garde l'identifiant du moteur (il voyage jusqu'à l'ASS) et le
   nom d'origine en infobulle, mais la tuile affiche l'effet. Un préréglage
   inconnu de cette table retombe sur son libellé moteur — et sa fiche
   technique, dérivée du style lui-même, le distingue quand même. */
var SUBS_PLABEL={
  standard:"Blanc, contour fin",       defaut:"Blanc, contour fin",
  pop:"Capitales jaunes",              popart:"Capitales, gros contour",
  surligneur:"Fond plein surligneur",
  beurre:"Capitales crème, contour brun",
  contour_sombre:"Blanc, contour épais", contour:"Blanc, contour épais",
  prime:"Bandeau noir léger",
  neon:"Cyan lumineux",
  marqueur:"Feutre manuscrit",
  sobre:"Bandeau noir dense",
  abysse:"Bandeau bleu nuit",
  machine:"Mono vert sur noir",
  nu:"Blanc sans décor"};
function subsPresetName(p){
  return SUBS_PLABEL[String(p&&p.id)]||String((p&&p.label)||p&&p.id||"préréglage")}
/* fiche technique en une ligne : ce qui sépare deux tuiles voisines quand
   deux glyphes ne suffisent pas (police, casse, fond OU contour) */
function subsPresetSpec(ps){
  var a=[String(ps.font||"Inter")];
  if(ps.upper)a.push("capitales");
  if(ps.bgOn)a.push("fond "+Math.round(subsClamp(subsN(ps.bgOpacity,100),0,100))+" %");
  else if(ps.outOn&&subsN(ps.outW,0)>0){
    var rel=subsN(ps.outW,0)/Math.max(1,subsN(ps.size,42));
    a.push("contour "+(rel<.06?"fin":rel<.1?"moyen":"épais"))}
  else a.push("sans fond ni contour");
  return a.join(" · ")}
/* clés que le cadre de placement possède : un préréglage ne les reprend plus
   dès que l'utilisateur a placé le bloc lui-même */
var SUBS_POSKEYS=["align","valign","marginV","width"];
function subsPresetStyle(id){
  var base=subsDefaultStyle();
  for(var i=0;i<SUBS_PRESETS.length;i++)
    if(SUBS_PRESETS[i].id===id)
      return Object.assign(base,SUBS_PRESETS[i].style,{preset:id});
  return base}
function subsHex8(hex,opa){
  var h=String(hex||"#000000");
  if(/^#[0-9a-f]{8}$/i.test(h))return h;
  if(!/^#[0-9a-f]{6}$/i.test(h))h="#000000";
  var a=Math.round(subsClamp(subsN(opa,100),0,100)*255/100).toString(16);
  return h+(a.length<2?"0"+a:a)}
/* couleur nue (sans alpha) — les <input type=color> refusent le #RRGGBBAA */
function subsHex6(hex){
  var h=String(hex||"#000000");
  if(/^#[0-9a-f]{8}$/i.test(h))return h.slice(0,7);
  return /^#[0-9a-f]{6}$/i.test(h)?h:"#000000"}

/* ── santé du service — source unique, auto-réparation (patron du rack VFX) ─
   Ici la panne n'ampute PAS le cœur du travail : seule la transcription
   automatique est réseau. La sonde sert à récupérer préréglages et polices
   du moteur, et à dire la vérité sur ce qui manque. */
var SUBS_SVC={st:"ok",presets:null,fonts:null,loading:!1,probing:!1,tries:0,
  next:0,timer:null,mounted:0,tick:0,subs:[]};
/* Les fontes du MOTEUR sont embarquées dans le backend (templates/_fonts), pas
   installées sur le poste : sans @font-face, l'aperçu dessinerait « Anton » en
   Arial pendant que ffmpeg le grave en Anton. On déclare donc une face par
   famille servie, pointée sur la route qui rend le .ttf. Idempotent. */
var SUBS_FF_DONE={};
function subsFontFaces(list){
  var css="";
  (list||[]).forEach(function(o){
    var fam=String(o.id||o.name||""),u=String(o.url||"");
    if(!fam||!u||SUBS_FF_DONE[fam])return;
    SUBS_FF_DONE[fam]=!0;
    css+="@font-face{font-family:'"+fam.replace(/'/g,"")+"';src:url('"+u+
      "') format('truetype');font-display:swap}\n"});
  if(!css)return;
  var el=document.getElementById("dz-subs-fonts");
  if(!el){el=document.createElement("style");el.id="dz-subs-fonts";
    document.head.appendChild(el)}
  el.appendChild(document.createTextNode(css))}
/* Hauteur de ligne RÉELLE de chaque famille, en multiples du corps : c'est
   aussi le facteur qui sépare le corps écrit dans le fichier ASS de l'em que
   libass dessine. Le moteur la sert dans `/api/subtitles/fonts` (`lh`) ; la
   table ci-dessous n'est qu'un filet pour le premier rendu, avant la réponse,
   et pour les familles système du repli. Valeurs mesurées à l'image. */
var SUBS_LH_FB={"inter":1.4302,"anton":1.7334,"bebas neue":1.3,"staatliches":1.312,
  "bungee":2.574,"press start 2p":1.374,"ibm plex sans":1.395,"pacifico":1.935};
var SUBS_LH={};
function subsFontLh(fam){
  var k=String(fam||"Inter").trim().toLowerCase();
  if(SUBS_LH[k]!=null)return SUBS_LH[k];
  if(SUBS_LH_FB[k]!=null)return SUBS_LH_FB[k];
  return 1.2}
var SUBS_PROBE_MS=[1500,3000,5000,8000,12000,20000];
function subsEmit(){SUBS_SVC.subs.slice().forEach(function(f){try{f()}catch(_e){}})}
function subsProbeStop(){if(SUBS_SVC.timer){clearTimeout(SUBS_SVC.timer);SUBS_SVC.timer=null}}
function subsUp(){
  var was=SUBS_SVC.st;
  SUBS_SVC.st="ok";SUBS_SVC.tries=0;SUBS_SVC.next=0;subsProbeStop();
  if(was!=="ok")SUBS_SVC.tick++;
  subsEmit()}
function subsDown(){SUBS_SVC.st="down";subsEmit();subsProbeSchedule()}
function subsProbeSchedule(){
  if(SUBS_SVC.st!=="ok"&&!SUBS_SVC.timer&&!SUBS_SVC.probing&&SUBS_SVC.mounted>0){
    var d=SUBS_PROBE_MS[Math.min(SUBS_SVC.tries,SUBS_PROBE_MS.length-1)];
    SUBS_SVC.next=Date.now()+d;
    SUBS_SVC.timer=setTimeout(function(){SUBS_SVC.timer=null;subsProbe()},d)}}
function subsProbe(){
  if(SUBS_SVC.probing)return;
  SUBS_SVC.probing=!0;SUBS_SVC.tries++;subsEmit();
  subsJson("/api/subtitles/presets").then(function(d){
    SUBS_SVC.probing=!1;
    var ps=d&&Array.isArray(d.presets)?d.presets:null;
    if(ps&&ps.length)SUBS_SVC.presets=ps.map(function(p){
      return {id:String(p.id),label:String(p.label||p.id),style:p.style||{}}});
    subsJson("/api/subtitles/fonts").then(function(f){
      if(f&&Array.isArray(f.fonts)&&f.fonts.length){
        SUBS_SVC.fonts=f.fonts.map(function(o){
          return [String(o.id||o.name),String(o.label||o.id||o.name)]});
        f.fonts.forEach(function(o){
          var v=parseFloat(o.lh);
          if(isFinite(v)&&v>0.5&&v<4)
            SUBS_LH[String(o.id||o.name).trim().toLowerCase()]=v});
        subsFontFaces(f.fonts)}
      subsEmit()},function(){});
    subsUp()},
  function(){
    SUBS_SVC.probing=!1;
    if(SUBS_SVC.st==="ok"){subsDown();return}
    subsEmit();subsProbeSchedule()})}
function subsRetryNow(){subsProbeStop();SUBS_SVC.tries=0;subsProbe()}
function subsSvcUse(){
  var s=x.useState(0),setT=s[1];
  x.useEffect(function(){
    var f=function(){setT(function(t){return t+1})};
    SUBS_SVC.subs.push(f);SUBS_SVC.mounted++;
    if(SUBS_SVC.st!=="ok")subsProbeSchedule();
    return function(){
      var i=SUBS_SVC.subs.indexOf(f);
      if(i>=0)SUBS_SVC.subs.splice(i,1);
      SUBS_SVC.mounted--;
      if(SUBS_SVC.mounted<1)subsProbeStop()}},[]);
  return SUBS_SVC}
function subsPresets(){return SUBS_SVC.presets||SUBS_PRESETS}
function subsFonts(){return SUBS_SVC.fonts||SUBS_FONTS_FB}

/* ── note interne ─────────────────────────────────────────────────────────── */
function subsUseNote(){
  var s=x.useState(""),note=s[0],setNote=s[1];
  var tRef=x.useRef(null);
  x.useEffect(function(){return function(){if(tRef.current)clearTimeout(tRef.current)}},[]);
  var fire=x.useCallback(function(m){
    setNote(String(m||""));
    if(tRef.current)clearTimeout(tRef.current);
    tRef.current=setTimeout(function(){setNote("")},4200)},[]);
  return [note,fire]}

/* ── bandeau de panne — honnête sur l'étendue réelle du dégât ─────────────── */
const SubsAlert=(props)=>{
  var svc=subsSvcUse();
  var s=x.useState(0),setT=s[1];
  var down=svc.st==="down";
  x.useEffect(function(){
    if(!down)return;
    var h=setInterval(function(){setT(function(t){return t+1})},1000);
    return function(){clearInterval(h)}},[down]);
  if(!down)return null;
  var left=Math.max(0,Math.ceil((svc.next-Date.now())/1000));
  return r.jsxs("div",{className:"sub-alert",role:"alert","aria-live":"polite",children:[
    r.jsx("span",{className:"sub-alerticon","aria-hidden":!0,children:"!"}),
    r.jsxs("div",{className:"sub-alerttxt",children:[
      r.jsx("b",{className:"sub-alerthead",
        children:"Service de sous-titres injoignable — le backend ne répond pas."}),
      /* dire vite ce qui est amputé : ici, presque rien. Tout le cœur du
         travail est local — inutile d'alarmer sur six lignes. */
      r.jsx("span",{className:"sub-alertsub",
        title:"/api/subtitles/presets et /api/subtitles/transcribe sont muets "+
          "sur 127.0.0.1:8765. Relancez DeepotusVideoGen : le panneau se "+
          "remplira seul, sans être rouvert.",
        children:"Seule la transcription automatique en dépend. Écrire, "+
          "découper, caler, styler, le karaoké et l'export .SRT / .VTT / .TXT "+
          "marchent hors ligne ; préréglages et polices = liste locale."}),
      r.jsx("span",{className:"sub-alertwhen",children:svc.probing
        ?"Nouvelle tentative en cours…"
        :"Reprise automatique — nouvelle tentative dans "+left+" s."})]}),
    r.jsx("button",{className:"sub-btn sub-alertbtn",disabled:!!svc.probing,
      title:"Redemander /api/subtitles/presets immédiatement",
      onClick:subsRetryNow,children:"Réessayer"})]})};

/* ── placement : ce que le MOTEUR sait porter, et rien d'autre ─────────────
   Un sous-titre gravé n'a pas de position libre en pixels. Le fichier ASS
   n'écrit que quatre choses : l'ancrage horizontal (\an gauche/centre/droite),
   l'ancrage vertical (bas/milieu/haut), la marge du bord (MarginV) et les
   marges latérales (MarginL/R, que le panneau exprime en « largeur du bloc »).
   Le cadre de sélection ne déplace donc RIEN d'autre : ce qu'on attrape à
   l'écran, c'est exactement ce que ffmpeg gravera. Une position libre au
   pixel — ou une rotation — s'afficherait ici et disparaîtrait au rendu ;
   on ne l'offre pas plutôt que de la mentir.

   Repères d'ancrage possibles pour le bloc de texte, à largeur donnée :
     gauche  → bord gauche du bloc     (ASS \an1/4/7, MarginL)
     centré  → milieu du bloc          (ASS \an2/5/8)
     droite  → bord droit du bloc      (ASS \an3/6/9, MarginR)
   et en vertical : haut+marge, milieu (marge ignorée par libass), bas+marge. */
var SUBS_SAFE_ACTION=5;   /* % — zone d'action : tout écran la garde */
var SUBS_SAFE_TITLE=10;   /* % — zone de titre : rien d'important au-delà */
var SUBS_SOCIAL_BOT=13;   /* % — bande basse mangée par l'UI des réseaux (9:16) */
/* Marge du bord PAR DÉFAUT : au-dessus des DEUX repères que l'aperçu trace
   (zone sûre 10 %, bande d'UI des réseaux 13 %). Elle valait 9 % — le texte
   d'usine passait donc sous la ligne pleine que le même écran dessinait.
   Largeur par défaut : 80 % = marges latérales de 10 %, soit exactement la
   zone sûre sur l'autre axe. Le défaut d'usine ne déclenche plus le
   contrôle qu'il est censé respecter. */
var SUBS_MARGIN_DEF=SUBS_SOCIAL_BOT;
var SUBS_WIDTH_DEF=100-2*SUBS_SAFE_TITLE;
function subsNearestSeg(segs,t){
  var best=null,bd=1/0;
  (segs||[]).forEach(function(s){
    if(!String(s.text||"").trim())return;
    var d=t<s.start?s.start-t:t>=s.end?t-s.end:0;
    if(d<bd){bd=d;best=s}});
  return best}
/* marge : demi-points, aimantée sur les deux zones sûres */
function subsSnapMv(v){
  v=subsClamp(v,0,45);
  var snap=[SUBS_SAFE_ACTION,SUBS_SAFE_TITLE,SUBS_SOCIAL_BOT];
  for(var i=0;i<snap.length;i++)
    if(Math.abs(v-snap[i])<.9)return snap[i];
  return Math.round(v*2)/2}
var SUBS_VLAB={top:"haut",middle:"milieu",bottom:"bas"};
var SUBS_HLAB={left:"gauche",center:"centré",right:"droite"};

/* ═════════════════ Overlay du lecteur — KARAOKÉ + PLACEMENT ═════════════════
   Rendu du sous-titre actif dans le cadre, mot actif surligné. Trois modes de
   surlignage : remplissage (la couleur du mot change), boîte (fond derrière le
   mot), échelle (le mot grossit). C'est la signature visuelle de la barre.
   `edit` ajoute le cadre de sélection : prise au glisser, poignées de largeur,
   zones sûres, et la lecture en clair des valeurs du moteur. */
const SubsOverlay=(props)=>{
  var style=Object.assign(subsDefaultStyle(),props.style||{});
  var t=subsN(props.t,0);
  var edit=!!props.edit&&typeof props.onStyle==="function";
  /* la taille de police est exprimée en pixels du CANEVAS DE RENDU (1080 de
     large en 9:16). Le cadre du lecteur fait ce qu'il peut : on mesure sa
     largeur réelle et on met l'aperçu à la même échelle — sinon un « 42 px »
     annoncé ne voudrait rien dire une fois rendu. */
  var seg=subsAt(props.segments,t),ghost=!1;
  if(!seg&&edit){
    /* rien à l'instant t : on montre quand même le bloc à déplacer, avec le
       texte du sous-titre le plus proche (ou un témoin si la piste est vide).
       Placer le cadre ne doit pas exiger de trouver d'abord une réplique. */
    seg=subsNearestSeg(props.segments,t)
      ||{id:"__fantome",start:t,end:t+1,text:"Sous-titre"};
    ghost=!0}
  var live=!!(seg&&String(seg.text||"").trim());
  var mr=x.useRef(null);
  var sw=x.useState({w:0,h:0}),fr=sw[0],setFr=sw[1];
  var dgR=x.useRef(null);
  var sd=x.useState(""),drag=sd[0],setDrag=sd[1];
  x.useEffect(function(){
    var el=mr.current&&mr.current.parentElement;
    if(!el)return;
    var read=function(){
      var w=el.clientWidth||0,h=el.clientHeight||0;
      setFr(function(p){return p.w===w&&p.h===h?p:{w:w,h:h}})};
    read();
    if(typeof ResizeObserver!=="function")return;
    var ro=new ResizeObserver(read);ro.observe(el);
    return function(){ro.disconnect()}},[live,edit]);
  var fw=fr.w;

  /* ── le geste ────────────────────────────────────────────────────────────
     Tout est calculé en fraction du CADRE, jamais en pixels d'écran : le
     résultat est le même à n'importe quelle taille de fenêtre. On mesure le
     bloc (largeur %) pour le vertical, et l'emprise réelle du texte pour
     l'horizontal — c'est le texte qu'on voit bouger, pas la boîte. */
  function subsFrameEl(){return mr.current&&mr.current.parentElement}
  function subsRectIn(el,hr){
    var a=el.getBoundingClientRect();
    return {left:a.left-hr.left,top:a.top-hr.top,width:a.width,height:a.height,
      right:a.right-hr.left,bottom:a.bottom-hr.top}}
  /* `placed` marque un placement POSÉ À LA MAIN : les préréglages cessent
     alors de le réécrire dans le dos de celui qui vient de le poser. */
  function subsPut(patch){
    if(props.onStyle)props.onStyle(Object.assign({placed:!0},patch))}
  function subsDown(e,mode){
    var host=subsFrameEl();
    if(!host||!edit)return;
    e.preventDefault();e.stopPropagation();
    var hr=host.getBoundingClientRect(),wr=subsRectIn(mr.current,hr);
    var ln=mr.current.querySelectorAll(".sub-line"),tl=null;
    for(var i=0;i<ln.length;i++){
      var q=subsRectIn(ln[i],hr);
      tl=tl?{left:Math.min(tl.left,q.left),right:Math.max(tl.right,q.right)}
        :{left:q.left,right:q.right}}
    if(!tl)tl={left:wr.left,right:wr.right};
    dgR.current={mode:mode,x:e.clientX,y:e.clientY,
      W:hr.width||1,H:hr.height||1,wr:wr,tl:tl.left,tw:tl.right-tl.left,
      st:{align:String(style.align||"center"),
          valign:String(style.valign||"bottom"),
          marginV:subsN(style.marginV,9),width:subsN(style.width,84)},
      last:""};
    try{e.currentTarget.setPointerCapture(e.pointerId)}catch(_e){}
    setDrag(mode)}
  function subsMove(e){
    var g=dgR.current;
    if(!g)return;
    e.preventDefault();
    var dx=e.clientX-g.x,dy=e.clientY-g.y;
    if(g.mode==="w"||g.mode==="e"){
      /* les marges latérales du moteur sont SYMÉTRIQUES (MarginL = MarginR) :
         tirer un bord écarte les deux. Le montrer ainsi évite de promettre un
         cadrage décentré que l'ASS ne saurait pas graver. */
      var wpc=Math.round(subsClamp(g.st.width+(g.mode==="e"?1:-1)*dx*200/g.W,20,100));
      if(String(wpc)!==g.last){g.last=String(wpc);subsPut({width:wpc})}
      return}
    var patch={};
    /* horizontal : trois ancrages possibles, on prend le plus proche */
    var pl=g.tl+dx;
    var bl=g.wr.left,br=g.wr.right;
    var cand=[["left",bl],["center",bl+(br-bl-g.tw)/2],["right",br-g.tw]];
    var bi=0,bd=1/0;
    cand.forEach(function(c,i){var d=Math.abs(pl-c[1]);if(d<bd){bd=d;bi=i}});
    patch.align=cand[bi][0];
    /* vertical : haut+marge / milieu / bas+marge, la marge recalculée depuis
       la position ABSOLUE du bloc — le bloc reste donc sous le doigt même au
       moment où l'ancrage bascule */
    var top=g.wr.top+dy,bot=top+g.wr.height,cy=top+g.wr.height/2;
    if(Math.abs(cy-g.H/2)<=g.H*.03)patch.valign="middle";
    else if(cy<g.H/2){patch.valign="top";patch.marginV=subsSnapMv(top/g.H*100)}
    else{patch.valign="bottom";patch.marginV=subsSnapMv((g.H-bot)/g.H*100)}
    var sig=patch.align+"|"+patch.valign+"|"+(patch.marginV==null?"-":patch.marginV);
    if(sig===g.last)return;
    g.last=sig;subsPut(patch)}
  function subsUp(e){
    if(!dgR.current)return;
    try{e.currentTarget.releasePointerCapture(e.pointerId)}catch(_e){}
    dgR.current=null;setDrag("")}
  function subsKey(e){
    if(!edit)return;
    var k=e.key,st=style,p=null;
    var step=e.shiftKey?2:.5;
    if(k==="ArrowUp"||k==="ArrowDown"){
      var up=k==="ArrowUp";
      if(st.valign==="middle")p={valign:up?"top":"bottom",marginV:45};
      else{
        var d=(st.valign==="bottom")===up?step:-step;
        p={marginV:subsClamp(subsRound(subsN(st.marginV,9)+d,1),0,45)}}}
    else if(k==="ArrowLeft"||k==="ArrowRight"){
      var order=["left","center","right"],i=order.indexOf(String(st.align));
      if(i<0)i=1;
      i=subsClamp(i+(k==="ArrowRight"?1:-1),0,2);
      p={align:order[i]}}
    else if(k==="Escape"){try{e.currentTarget.blur()}catch(_e){}return}
    else return;
    e.preventDefault();e.stopPropagation();subsPut(p)}

  if(!live)return r.jsx("i",{ref:mr,className:"sub-ovprobe","aria-hidden":!0});
  var ws=subsWords(seg),act=style.karOn&&!ghost?subsActiveWord(ws,t):-1;
  var mc=Math.max(10,subsN(style.maxChars,42));
  var lines=subsLines(seg.text,mc);
  /* la césure regroupe les mots : on redistribue les index de mots par ligne
     pour que le surlignage tombe sur LE bon mot, pas sur son homonyme */
  var idx=0,byLine=lines.map(function(l){
    var n=l.split(/\s+/).filter(Boolean).length,a=[];
    for(var i=0;i<n;i++){a.push(idx);idx++}
    return a});
  var scale=(fw||360)/Math.max(120,subsN(props.canvasW,1080));
  var fs=subsClamp(style.size,8,200)*scale;
  var shadow=[];
  if(style.outOn&&style.outW>0){
    var w=subsClamp(style.outW,0,20)*scale,c=subsHex6(style.outColor);
    /* contour par 8 ombres — le seul moyen fidèle en CSS pur, et il rend
       exactement comme le borderw d'ASS côté ffmpeg */
    [[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]].forEach(function(d){
      shadow.push((d[0]*w).toFixed(2)+"px "+(d[1]*w).toFixed(2)+"px 0 "+c)})}
  /* l'ombre ASS est UNE copie décalée en bas à droite, d'une seule
     profondeur : ni X/Y séparés, ni flou. L'aperçu fait pareil, sinon il
     promet une ombre que la vidéo ne contiendra pas. */
  if(style.shOn){
    var so=subsClamp(subsN(style.shOff,subsN(style.shY,3)),0,20)*scale;
    shadow.push(so.toFixed(2)+"px "+so.toFixed(2)+"px 0 "+subsHex6(style.shColor))}
  var wrapSty={
    position:"absolute",left:"50%",transform:"translateX(-50%)",
    width:subsClamp(style.width,20,100)+"%",
    display:"flex",flexDirection:"column",
    pointerEvents:edit?"auto":"none",
    alignItems:style.align==="left"?"flex-start":style.align==="right"?"flex-end":"center",
    textAlign:style.align,
    gap:0};
  var mv=subsClamp(style.marginV,0,45)+"%";
  if(style.valign==="top")wrapSty.top=mv;
  else if(style.valign==="middle"){wrapSty.top="50%";
    wrapSty.transform="translate(-50%,-50%)"}
  else wrapSty.bottom=mv;
  var txtSty={
    fontFamily:"'"+String(style.font||"Inter")+"', sans-serif",
    fontSize:fs.toFixed(1)+"px",fontWeight:subsClamp(style.weight,100,900),
    fontStyle:style.italic?"italic":"normal",
    textDecoration:style.underline?"underline":"none",
    letterSpacing:subsN(style.tracking,0)*scale+"px",
    /* interligne : libass avance d'exactement UN `Fontsize` par ligne (mesuré
       à l'image sur Inter, Anton et Bebas, à deux tailles) — et depuis la
       correction d'échelle, `Fontsize` vaut `em × hauteur de ligne de la
       fonte`. L'aperçu se cale donc sur CE rapport, servi par
       `/api/subtitles/fonts` (`lh`), et non sur 1. Le réglage a disparu du
       panneau puisqu'il ne pouvait rien changer au fichier livré. */
    lineHeight:subsFontLh(style.font),
    color:subsHex6(style.color),
    textShadow:shadow.length?shadow.join(", "):"none",
    padding:style.bgOn?(subsClamp(style.bgPad,0,60)*scale*.5).toFixed(1)+"px "+
      (subsClamp(style.bgPad,0,60)*scale).toFixed(1)+"px":0,
    /* pas d'arrondi : la boîte ASS (BorderStyle 3) est à angles droits */
    borderRadius:0,
    background:style.bgOn?subsHex8(style.bgColor,style.bgOpacity):"transparent",
    textTransform:style.upper?"uppercase":"none",
    boxDecorationBreak:"clone",WebkitBoxDecorationBreak:"clone",
    maxWidth:"100%",
    /* JAMAIS de coupure DANS un mot : libass n'en fait pas (le fichier est
       écrit en WrapStyle 2, et `ui_wrap` côté moteur ne tronçonne aucun mot).
       Avec `break-word`, l'aperçu remplissait joliment la largeur pendant que
       la gravure débordait — mesuré : 16 points de % d'écart sur le bord
       droit. Un mot trop long doit donc déborder ICI AUSSI, pour qu'on le
       voie avant le rendu. */
    wordBreak:"normal",overflowWrap:"normal"};
  /* le fond « pleine largeur » n'existe plus : BorderStyle 4 rend
     exactement comme le 3 chez libass (mesuré : 258 px contre 260 sur 640).
     Une seule étendue, donc, celle qui se grave — la boîte ajustée. */
  var fill=!1,blockSty=null;
  /* karaoké : en ASS le surlignage est CUMULATIF (\k fait basculer chaque
     mot et il le reste jusqu'à la fin de la réplique). L'aperçu n'allumait
     que le mot courant — il montrait autre chose que la vidéo. */
  function word(gi,w){
    var on=act>=0&&gi<=act,cur=gi===act;
    var st={};
    if(on&&style.karMode==="fill")st.color=subsHex6(style.karColor);
    if(on&&style.karMode==="box"){st.background=subsHex6(style.karBox);
      st.color=subsHex6(style.karColor);st.borderRadius=0;
      st.padding="0 "+(4*scale)+"px";st.boxDecorationBreak="clone"}
    return r.jsxs("span",{className:"sub-w","data-on":on?"":void 0,
      "data-cur":cur?"":void 0,style:st,
      children:[w," "]},"w"+gi)}
  var body=byLine.map(function(ids,li){
    var lw=lines[li].split(/\s+/).filter(Boolean);
    return r.jsx("span",{className:"sub-line",style:fill?void 0:txtSty,
      children:lw.map(function(w,k){return word(ids[k],w)})},"l"+li)});
  var inner=fill?r.jsx("span",{className:"sub-fill",style:blockSty,children:body}):body;
  /* court : le bandeau tient sur une ligne, y compris sur un cadre 9:16
     etroit — l'infobulle du bandeau dit le pourquoi en toutes lettres */
  var mvTxt=style.valign==="middle"?"marge sans objet"
    :"marge "+subsRound(subsN(style.marginV,9),1)+" %";
  /* UNE seule lecture des valeurs, dans le bandeau : une étiquette « placement »
     collée au bloc en plus n'aurait fait que se cogner aux repères de zone sûre */
  /* UNE seule lecture des valeurs, dans le bandeau : une étiquette « placement »
     collée au bloc en plus n'aurait fait que se cogner aux repères de zone sûre.
     Le bandeau n'existe QUE pendant le placement — inutile de le renommer. */
  /* HORS ZONE SÛRE, dit AU MOMENT où ça arrive : le repère à 10 % est tracé
     juste à côté ; un réglage qui le franchit doit s'annoncer là, pas
     seulement dans l'onglet Style. Même règle, même chiffre — subsSafeIssues. */
  var safeBad=subsSafeIssues(style);
  var readout=(ghost?"aucune réplique ici — ":"")+
    SUBS_VLAB[style.valign]+" · "+SUBS_HLAB[style.align]+" · "+
    mvTxt+" · largeur "+Math.round(subsN(style.width,SUBS_WIDTH_DEF))+" %"+
    (safeBad.length?"  ⚠ hors zone sûre "+SUBS_SAFE_TITLE+" %":"");
  var block=r.jsxs("div",{className:"sub-ov",
    "data-anim":edit?"none":(style.anim||"none"),
    "data-seg":seg.id,"data-edit":edit?"":void 0,
    "data-ghost":ghost?"":void 0,"data-drag":drag||void 0,
    style:wrapSty,ref:mr,
    tabIndex:edit?0:void 0,
    role:edit?"group":void 0,
    "aria-label":edit?"Placement du sous-titre — "+readout+
      " (flèches : déplacer, Maj+flèches : par pas de 2 %)":void 0,
    title:edit?"Glisser pour placer le bloc · poignées latérales pour la "+
      "largeur · flèches du clavier pour affiner":void 0,
    onPointerDown:edit?function(e){subsDown(e,"move")}:void 0,
    onPointerMove:edit?subsMove:void 0,
    onPointerUp:edit?subsUp:void 0,
    onPointerCancel:edit?subsUp:void 0,
    onKeyDown:edit?subsKey:void 0,
    children:[
    inner,
    /* ── cadre de sélection : le contour, les quatre coins, les deux poignées
       de largeur. Pas de rotation ni de poignée de coin « échelle » : ni
       l'une ni l'autre ne survivrait à la gravure, et le corps se règle au
       chiffre (« Taille ») dans l'onglet Style. ── */
    edit?r.jsxs("i",{className:"sub-fr","aria-hidden":!0,children:[
      r.jsx("i",{className:"sub-frc","data-p":"nw"},"nw"),
      r.jsx("i",{className:"sub-frc","data-p":"ne"},"ne"),
      r.jsx("i",{className:"sub-frc","data-p":"sw"},"sw"),
      r.jsx("i",{className:"sub-frc","data-p":"se"},"se")]},"fr"):null,
    edit?r.jsx("i",{className:"sub-frh","data-p":"w",
      title:"Largeur du bloc — les deux marges bougent ensemble",
      onPointerDown:function(e){subsDown(e,"w")},
      onPointerMove:subsMove,onPointerUp:subsUp,onPointerCancel:subsUp},"hw"):null,
    edit?r.jsx("i",{className:"sub-frh","data-p":"e",
      title:"Largeur du bloc — les deux marges bougent ensemble",
      onPointerDown:function(e){subsDown(e,"e")},
      onPointerMove:subsMove,onPointerUp:subsUp,onPointerCancel:subsUp},"he"):null,
    null]});
  if(!edit)return block;
  /* zones sûres — seulement en placement, sinon c'est du bruit sur l'aperçu */
  var portrait=fr.h>fr.w;
  return r.jsxs(r.Fragment,{children:[
    r.jsxs("div",{className:"sub-safe","aria-hidden":!0,"data-drag":drag||void 0,
      "data-out":safeBad.length?"":void 0,children:[
      r.jsx("i",{className:"sub-safebox","data-k":"action",
        style:{inset:SUBS_SAFE_ACTION+"%"}},"a"),
      r.jsx("i",{className:"sub-safebox","data-k":"title",
        style:{inset:SUBS_SAFE_TITLE+"%"}},"t"),
      portrait?r.jsx("i",{className:"sub-safesoc",
        style:{height:SUBS_SOCIAL_BOT+"%"}},"s"):null,
      r.jsx("i",{className:"sub-safelab","data-k":"title",
        style:{top:"calc("+SUBS_SAFE_TITLE+"% + 3px)"},
        children:"zone sûre 10 %"},"lt"),
      portrait?r.jsx("i",{className:"sub-safelab","data-k":"soc",
        style:{bottom:"calc("+SUBS_SOCIAL_BOT+"% - 12px)"},
        children:"UI réseaux"},"ls"):null]},"safe"),
    r.jsx("div",{className:"sub-hud","data-drag":drag||void 0,
      "data-out":safeBad.length?"":void 0,
      role:"status","aria-live":"off",
      title:(safeBad.length?safeBad.map(function(w){return w.msg}).join(" ")+" ":"")+
        "Ce que le moteur gravera : ancrage, marge du bord et largeur du "+
        "bloc. Ancré au milieu, la marge du bord n'a pas d'effet — libass "+
        "l'ignore, l'aperçu aussi.",
      children:readout},"hud"),
    block]})};

/* ═════════════════ Onglet Style ═════════════════════════════════════════════ */
const SubsStyle=(props)=>{
  var svc=subsSvcUse();
  var st=Object.assign(subsDefaultStyle(),props.style||{});
  /* modules repliés au départ : ce qui sert le plus est désormais À PLAT en
     haut (bloc « Réglages »), les modules ne portent que le détail */
  var s1=x.useState({}),exp=s1[0],setExp=s1[1];
  function set(patch,heavy){if(props.onChange)props.onChange(patch,!!heavy)}
  function fold(id,label,sum,kids){
    var open=!!exp[id];
    return r.jsxs("div",{className:"sub-mod",children:[
      r.jsxs("button",{className:"sub-mhead","aria-expanded":open,
        onClick:function(){setExp(function(m){
          var n=Object.assign({},m);if(n[id])delete n[id];else n[id]=1;return n})},
        children:[
        r.jsx("span",{className:"sub-mname",children:label}),
        r.jsx("span",{className:"sub-msum",children:sum}),
        r.jsx("span",{className:"sub-mcaret","aria-hidden":!0,children:open?"▾":"▸"})]}),
      open?r.jsx("div",{className:"sub-mbody",children:kids}):null]},id)}
  function row(label,kids,key){
    return r.jsxs("div",{className:"sub-prow",children:[
      r.jsx("span",{className:"sub-plabel",children:label}),kids]},key||label)}
  function rng(k,min,max,step,unit,label){
    var v=subsN(st[k],min);
    return row(label,[
      r.jsx("input",{className:"sub-range",type:"range",min:min,max:max,step:step,
        value:v,"aria-label":label,
        onChange:function(e){var o={};o[k]=subsN(e.target.value,v);set(o)}},"r"),
      r.jsx("span",{className:"sub-pval",
        children:(step<1?subsRound(v,2):Math.round(v))+(unit||"")},"v")],k)}
  function col(k,label){
    return row(label,[
      r.jsx("input",{className:"sub-color",type:"color",value:subsHex6(st[k]),
        "aria-label":label,
        onChange:function(e){var o={};o[k]=e.target.value;set(o,!0)}},"c"),
      r.jsx("span",{className:"sub-pval",children:subsHex6(st[k])},"v")],k)}
  function sw(k,label,title){
    var on=!!st[k];
    return r.jsxs("button",{className:"sub-swrow",role:"switch","aria-checked":on,
      title:title||label,
      onClick:function(){var o={};o[k]=!on;set(o,!0)},children:[
      r.jsx("span",{className:"sub-sw","data-on":on?"":void 0,"aria-hidden":!0,
        children:r.jsx("i",{className:"sub-swk"})}),
      r.jsx("span",{className:"sub-blabel",children:label})]},k)}
  function chips(k,opts,label){
    var cur=String(st[k]);
    return row(label,[r.jsx("div",{className:"sub-chips",children:opts.map(function(o){
      return r.jsx("button",{className:"sub-chip","data-on":String(o[0])===cur?"":void 0,
        title:o[1],onClick:function(){var p={};p[k]=o[0];set(p,!0)},
        children:o[2]||o[1]},String(o[0]))})},"c")],k)}

  var presets=subsPresets();
  /* échelle des vignettes : mesurée, pas devinée — la tuile représente le
     cadre du rendu, donc un préréglage « gros » doit y paraître gros. */
  var gref=x.useRef(null);
  var gs=x.useState(168),gw=gs[0],setGw=gs[1];
  x.useEffect(function(){
    var el=gref.current;
    if(!el)return;
    var read=function(){
      var w=Math.max(60,(el.clientWidth-6)/2-14);
      setGw(function(p){return Math.abs(p-w)<1?p:w})};
    read();
    if(typeof ResizeObserver!=="function")return;
    var ro=new ResizeObserver(read);ro.observe(el);
    return function(){ro.disconnect()}},[]);
  var placed=!!st.placed;
  function applyPreset(p){
    var ps=Object.assign({},p.style||{},{preset:p.id});
    /* le placement appartient à qui l'a posé : une fois le bloc déplacé dans
       le lecteur, changer d'habillage ne le fait plus sauter. */
    if(placed)SUBS_POSKEYS.forEach(function(k){delete ps[k]});
    set(ps,!0)}
  function ptile(p){
    var ps=Object.assign(subsDefaultStyle(),p.style||{});
    var on=st.preset===p.id;
    var sc=gw/1080;                       /* px de tuile par px de canevas */
    var fs=Math.max(7,subsClamp(ps.size,8,400)*sc);
    var shadow=[];
    if(ps.outOn&&subsN(ps.outW,0)>0){
      var ow=Math.max(.5,subsN(ps.outW,0)*sc),oc=subsHex6(ps.outColor);
      [[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]].forEach(function(d){
        shadow.push((d[0]*ow).toFixed(2)+"px "+(d[1]*ow).toFixed(2)+"px 0 "+oc)})}
    if(ps.shOn){
      var pso=(subsClamp(subsN(ps.shOff,subsN(ps.shY,3)),0,20)*sc).toFixed(1);
      shadow.push(pso+"px "+pso+"px 0 "+subsHex6(ps.shColor))}
    var wsty={fontFamily:"'"+String(ps.font||"Inter")+"', sans-serif",
      fontSize:fs.toFixed(1)+"px",fontWeight:subsClamp(ps.weight,100,900),
      fontStyle:ps.italic?"italic":"normal",
      letterSpacing:(subsN(ps.tracking,0)*sc).toFixed(2)+"px",
      textTransform:ps.upper?"uppercase":"none",
      color:subsHex6(ps.color),
      textShadow:shadow.length?shadow.join(", "):"none",
      background:ps.bgOn?subsHex8(ps.bgColor,ps.bgOpacity):"transparent",
      padding:ps.bgOn?(subsN(ps.bgPad,10)*sc*.45).toFixed(1)+"px "+
        (subsN(ps.bgPad,10)*sc).toFixed(1)+"px":0,
      borderRadius:0,
      boxDecorationBreak:"clone",WebkitBoxDecorationBreak:"clone"};
    var ksty={};
    if(ps.karOn&&ps.karMode==="box"){ksty.background=subsHex6(ps.karBox);
      ksty.color=subsHex6(ps.karColor);ksty.borderRadius=0;
      ksty.padding="0 "+(3*sc*10).toFixed(1)+"px"}
    else if(ps.karOn)ksty.color=subsHex6(ps.karColor);
    return r.jsxs("button",{className:"sub-ptile","data-on":on?"":void 0,
      title:"Préréglage « "+String(p.label||p.id)+" » ("+p.id+") — "+
        subsPresetSpec(ps)+". Le texte et le calage ne bougent pas"+
        (placed?", et le placement que vous avez posé est conservé":"")+".",
      onClick:function(){applyPreset(p)},
      children:[
      /* vignette = un vrai bout de cadre : fond d'image simulé, corps à
         l'échelle du rendu, contour et fond réels, et le MOT ACTIF dans sa
         couleur de karaoké — c'est là que deux préréglages voisins se séparent */
      r.jsx("span",{className:"sub-pfr","aria-hidden":!0,children:
        r.jsxs("span",{className:"sub-pw",style:wsty,children:[
          "mot ",r.jsx("span",{style:ksty,children:"actif"},"k")]})}),
      r.jsx("span",{className:"sub-pname",children:subsPresetName(p)}),
      r.jsx("span",{className:"sub-pspec",children:subsPresetSpec(ps)})]},p.id)}

  /* écarts entre l'aperçu et la GRAVURE — zone sûre comprise. Ils sortent du
     VERDICT, comme tout le reste : le badge de l'onglet et cette liste ne
     peuvent donc plus annoncer deux chiffres différents. */
  var issues=(props.verdict||subsVerdictNil()).style;

  /* ── CE QUE LA GRAVURE FERA D'AUTRE QUE L'APERÇU ─────────────────────────
     Ces écarts (zone sûre franchie, `style_warnings` et `unsupported` du
     moteur) sont EXACTEMENT ce que compte le badge de cet onglet. Ils vivaient
     sous la galerie : le badge annonçait « 2 » et rien à l'écran ne les
     désignait tant qu'on n'avait pas déroulé. Ils passent donc EN TÊTE de
     l'onglet — un badge doit toujours pouvoir se pointer du doigt. */
  var ecarts=issues.length
    ?r.jsxs("div",{className:"sub-stywarns",children:[
      r.jsxs("div",{className:"sub-sec",children:[
        r.jsx("span",{className:"sub-seclabel",
          children:"Aperçu et gravure : les écarts"},"l"),
        r.jsx("span",{className:"sub-secnote",
          title:"Le badge de cet onglet compte exactement ces écarts",
          children:issues.length+(issues.length>1?" écarts":" écart")},"n")]},"h"),
      issues.map(function(w,k){
        var fx=w.fix;
        return r.jsxs("div",{className:"sub-warn","data-sev":w.sev,children:[
          r.jsx("span",{className:"sub-warnicon","aria-hidden":!0,
            children:"·"},"i"),
          r.jsx("span",{className:"sub-warnmsg",
            children:w.msg+(w.about&&w.about.length
              ?" (" + w.about.length + " réplique" +
                (w.about.length>1?"s":"") + " concernée" +
                (w.about.length>1?"s":"") + ")":"")},"m"),
          /* la conséquence du geste vit dans l'infobulle du bouton, pas sur une
             ligne de plus : ici le MESSAGE dit déjà quoi faire (« passez
             l'opacité à 100 %, ou coupez le karaoké »), et deux fois la même
             phrase pousserait les préréglages hors de l'écran */
          fx?r.jsx("button",{className:"sub-minibtn sub-fix",
            title:fx.effect||"",
            onClick:function(){var o={};o[fx.champ]=fx.valeur;set(o,!0)},
            children:fx.label||"Corriger"},"f"):null]},"sw"+k)})]},"ec")
    :null;

  return r.jsxs("div",{className:"sub-style",children:[
    r.jsx(SubsAlert,{}),

    /* ── LES RÉGLAGES D'ABORD, LA GALERIE ENSUITE ──────────────────────────
       Tout ce qui était au-dessus de la ligne de flottaison était une galerie
       de huit préréglages : pas de taille, pas de couleur, pas d'épaisseur de
       contour, pas de marge — on prenait une combinaison toute faite, ou on
       déroulait vers l'inconnu. Un monteur qui ajuste une taille ne doit pas
       chercher. Les cinq réglages qui servent le plus sont donc ici, à plat,
       en haut ; la galerie garde sa place de RACCOURCI, juste dessous ; et le
       détail (graisse, casse, fond, ombre, karaoké, animation, césure) vit
       dans les modules repliables. Aucun réglage n'apparaît deux fois. */
    r.jsxs("div",{className:"sub-sec",children:[
      r.jsx("span",{className:"sub-seclabel",children:"Réglages"}),
      r.jsx("span",{className:"sub-secnote",
        title:"Le détail (graisse, casse, fond, ombre, karaoké, animation) est "+
          "dans les modules, sous la galerie",
        children:"les plus utilisés"})]}),
    r.jsxs("div",{className:"sub-quick",children:[
      row("Police",[r.jsx("select",{className:"sub-sel",value:st.font,
        "aria-label":"Police des sous-titres",
        onChange:function(e){set({font:e.target.value},!0)},
        children:subsFonts().map(function(f){
          return r.jsx("option",{value:f[0],children:f[1]},f[0])})},"s")],"font"),
      rng("size",12,200,1," px","Taille"),
      col("color","Couleur du texte"),
      /* épaisseur 0 = pas de contour : un curseur au lieu d'un interrupteur
         PLUS un curseur, et le même réglage ne vit qu'à un seul endroit */
      row("Contour",[
        r.jsx("input",{className:"sub-range",type:"range",min:0,max:14,step:.5,
          value:subsN(st.outW,0),"aria-label":"Épaisseur du contour",
          title:"0 = aucun contour. La couleur du contour est dans le module "+
            "« Contour et ombre ».",
          onChange:function(e){
            var v=subsN(e.target.value,0);
            set({outW:v,outOn:v>0})}},"r"),
        r.jsx("span",{className:"sub-pval",
          children:st.outOn&&subsN(st.outW,0)>0
            ?subsRound(subsN(st.outW,0),1)+" px":"aucun"},"v")],"outW"),
      st.valign==="middle"
        ?r.jsx("div",{className:"sub-mhint",
          children:"Ancré au milieu, la marge du bord n'a pas d'effet — c'est "+
            "aussi vrai dans le fichier ASS que dans l'aperçu."},"mvh")
        :rng("marginV",0,45,.5," %","Marge du bord")]}),

    /* les écarts que compte le badge de cet onglet : juste sous les réglages
       qu'ils concernent, et AVANT la galerie — le badge doit toujours pouvoir
       se pointer du doigt sans qu'on déroule */
    ecarts,

    r.jsxs("div",{className:"sub-sec",children:[
      r.jsx("span",{className:"sub-seclabel",children:"Préréglages"}),
      r.jsx("span",{className:"sub-secnote",
        title:"Raccourci : un préréglage écrit d'un coup police, corps, "+
          "couleur, fond, contour et karaoké. Origine de la liste : "+
          (SUBS_SVC.presets?"le moteur":"la table locale")+".",
        children:"raccourcis · "+(SUBS_SVC.presets?"moteur":"local")})]}),
    r.jsx("div",{className:"sub-pgrid",ref:gref,children:presets.map(ptile)}),

    /* ── PLACEMENT — le même modèle que le cadre du lecteur ─────────────────
       Ces quatre réglages SONT ce que le moteur grave. Ils se règlent au
       chiffre ici, ou à la main dans l'aperçu ; les deux écrivent la même
       chose. */
    fold("place","Placement",
      SUBS_VLAB[st.valign]+" · "+SUBS_HLAB[st.align]+" · marge "+
      subsFr(subsN(st.marginV,SUBS_MARGIN_DEF),1)+" % · largeur "+
      Math.round(subsN(st.width,SUBS_WIDTH_DEF))+" %",[
      r.jsx("div",{className:"sub-mhint",
        children:"Le tiroir ouvert, le bloc s'attrape directement dans le "+
          "lecteur : glisser pour placer, poignées latérales pour la largeur, "+
          "flèches du clavier pour affiner. Les zones sûres s'affichent pendant "+
          "le geste."},"ph"),
      chips("align",SUBS_ALIGN,"Ancrage horizontal"),
      chips("valign",SUBS_VALIGN,"Ancrage vertical"),
      rng("width",20,100,1," %","Largeur du bloc"),
      r.jsx("div",{className:"sub-mhint",
        children:"Les marges latérales du moteur sont symétriques : la largeur "+
          "se réduit des deux côtés à la fois."},"wh"),
      placed?r.jsx("button",{className:"sub-btn",
        title:"Reprendre le placement prévu par le préréglage courant",
        onClick:function(){
          var p=null;
          presets.forEach(function(q){if(q.id===st.preset)p=q});
          var o={placed:!1};
          SUBS_POSKEYS.forEach(function(k){
            var v=p&&p.style?p.style[k]:void 0;
            o[k]=v!=null?v:subsDefaultStyle()[k]});
          set(o,!0)},
        children:"Reprendre le placement du préréglage"},"rp"):null]),

    /* police, corps et couleur sont remontés dans « Réglages » : ce module ne
       garde que ce qui sert moins souvent — aucun réglage en double */
    fold("police","Texte",
      (Number(st.weight)>=900?"noir":Number(st.weight)>=700?"gras"
        :Number(st.weight)>=600?"demi":"maigre")+
      (st.upper?" · capitales":"")+(st.italic?" · italique":"")+
      (subsN(st.tracking,0)?" · "+subsFr(subsN(st.tracking,0),1)+" px":""),[
      row("Graisse",[r.jsx("div",{className:"sub-chips",children:
        [[400,"maigre"],[600,"demi"],[700,"gras"],[900,"noir"]].map(function(o){
          return r.jsx("button",{className:"sub-chip",
            "data-on":Number(st.weight)===o[0]?"":void 0,
            onClick:function(){set({weight:o[0]},!0)},children:o[1]},String(o[0]))})},"c")],"w"),
      row("Effets",[r.jsxs("div",{className:"sub-chips",children:[
        r.jsx("button",{className:"sub-chip","data-on":st.italic?"":void 0,
          title:"Italique",onClick:function(){set({italic:!st.italic},!0)},
          children:r.jsx("i",{children:"I"})},"i"),
        r.jsx("button",{className:"sub-chip","data-on":st.underline?"":void 0,
          title:"Souligné",onClick:function(){set({underline:!st.underline},!0)},
          children:r.jsx("u",{children:"U"})},"u"),
        r.jsx("button",{className:"sub-chip","data-on":st.upper?"":void 0,
          title:"Tout en majuscules",onClick:function(){set({upper:!st.upper},!0)},
          children:"AA"},"c")]},"c")],"fx"),
      /* pas de réglage d'interligne : libass fixe l'écart des lignes à
         1,000 x le corps de la fonte (mesuré à l'image). Le curseur qui
         existait ici ne changeait que l'aperçu. */
      rng("tracking",-2,12,.5," px","Interlettrage")]),

    /* Fond : ni « étendue », ni « arrondi ». libass ne dessine qu'une boîte
       ajustée au texte, à angles droits (BorderStyle 3) ; BorderStyle 4 rend
       exactement pareil, mesuré. Les deux réglages ne pouvaient rien changer
       à la vidéo livrée : ils sont partis plutôt que de mentir. */
    fold("fond","Fond",st.bgOn?"ajusté · "+Math.round(st.bgOpacity)+" %":"aucun",[
      sw("bgOn","Fond derrière le texte",
         "Boîte colorée ajustée au texte, angles droits — comme à la gravure"),
      st.bgOn?col("bgColor","Couleur du fond"):null,
      st.bgOn?rng("bgOpacity",0,100,1," %","Opacité"):null,
      st.bgOn?rng("bgPad",0,48,1," px","Marge intérieure"):null]),

    /* l'ÉPAISSEUR du contour est remontée dans « Réglages » (0 px = aucun
       contour, l'interrupteur d'avant n'avait plus de raison d'être) : ce
       module garde la couleur et toute l'ombre */
    fold("bord","Contour et ombre",
      (st.outOn&&subsN(st.outW,0)>0
        ?"contour "+subsFr(subsN(st.outW,0),1)+" px":"sans contour")+
      (st.shOn?" · ombre":""),[
      st.outOn&&subsN(st.outW,0)>0?col("outColor","Couleur du contour")
        :r.jsx("div",{className:"sub-mhint",
          children:"Aucun contour : réglez l'épaisseur au-dessus, dans "+
            "« Réglages », pour qu'il apparaisse."},"oh"),
      /* L'ombre ASS est UNE copie décalée en bas à droite : un seul
         décalage, et aucun flou. D'où un seul curseur, au lieu des trois
         d'avant dont deux ne sortaient pas dans la vidéo. */
      sw("shOn","Ombre portée",
         "Copie du texte décalée en bas à droite — exactement ce que grave l'ASS"),
      st.shOn?col("shColor","Couleur de l'ombre"):null,
      st.shOn?rng("shOff",0,20,1," px","Décalage"):null]),

    fold("kar","Karaoké",st.karOn?"cumulatif · "+
      (SUBS_KMODES.filter(function(m){return m[0]===st.karMode})[0]||["","—"])[1]
      :"désactivé",[
      sw("karOn","Surligner les mots prononcés",
        "Chaque mot bascule à son tour et le reste jusqu'à la fin de la "+
        "réplique — c'est ce que grave l'ASS, et l'aperçu le montre pareil"),
      st.karOn?chips("karMode",SUBS_KMODES,"Mode"):null,
      st.karOn?col("karColor","Couleur du mot"):null,
      st.karOn&&st.karMode==="box"?col("karBox","Couleur de la boîte"):null,
      st.karOn&&st.karMode==="box"&&!st.bgOn?r.jsx("div",{className:"sub-mhint",
        "data-warn":"",
        children:"Mode « boîte » sans fond : au rendu, la couleur ira sur le "+
          "CONTOUR du mot, pas dans une boîte — la boîte du karaoké est celle "+
          "du fond. Activez le fond, ou passez en « remplissage »."},"kw"):null,
      st.karOn?r.jsx("div",{className:"sub-mhint",
        children:"Sans timings par mot venus de la transcription, la répartition "+
          "est proportionnelle au nombre de caractères — chaque segment le dit."},
        "kh"):null]),

    fold("anim","Animation",(SUBS_ANIMS.filter(function(a){return a[0]===st.anim})[0]||["","aucune"])[1],[
      chips("anim",SUBS_ANIMS,"Apparition"),
      r.jsx("div",{className:"sub-mhint",
        children:"Fondu et pop sont gravés dans la vidéo (\fad et \t de "+
          "l'ASS). Les apparitions qui n'avaient aucun équivalent gravable "+
          "— montée, machine à écrire — ont été retirées."},"ah"),
      row("Césure",[
        r.jsx("input",{className:"sub-num",type:"number",min:10,max:120,step:1,
          value:Math.round(subsN(st.maxChars,42)),
          "aria-label":"Caractères par ligne",
          onChange:function(e){set({maxChars:subsClamp(subsN(e.target.value,42),10,120)},!0)}},"n"),
        r.jsx("span",{className:"sub-punit",children:"car./ligne"},"u")],"mc"),
      row("Lignes max",[
        r.jsx("input",{className:"sub-num",type:"number",min:1,max:4,step:1,
          value:Math.round(subsN(st.maxLines,2)),
          "aria-label":"Nombre maximum de lignes",
          onChange:function(e){set({maxLines:subsClamp(subsN(e.target.value,2),1,4)},!0)}},"n"),
        r.jsx("span",{className:"sub-punit",children:"lignes"},"u")],"ml")]),

    r.jsx("button",{className:"sub-btn sub-reset",
      title:"Revenir au style par défaut (le texte et le calage ne bougent pas)",
      onClick:function(){set(subsDefaultStyle(),!0)},
      children:"Réinitialiser le style"})]})};

/* ═════════════════ Onglet Segments ══════════════════════════════════════════ */
const SubsSegments=(props)=>{
  var svc=subsSvcUse();
  var segs=subsSort(props.segments||[]);
  var style=Object.assign(subsDefaultStyle(),props.style||{});
  var s1=x.useState(""),query=s1[0],setQuery=s1[1];
  var s2=x.useState(null),reflowN=s2[0],setReflowN=s2[1];
  /* pli des lignes : 1 = ouverte de force, 0 = fermée de force, absente = elle
     suit la sélection. Trois états parce que deux ne suffisent pas : la ligne
     sélectionnée doit s'ouvrir seule SANS empêcher de la refermer. */
  var s4=x.useState({}),openMap=s4[0],setOpenMap=s4[1];
  var s5=x.useState(!1),onlyBad=s5[0],setOnlyBad=s5[1];
  /* la recomposition n'occupe la place que quand on s'en sert : ailleurs, un
     curseur permanent vole 55 px de liste à chaque ouverture du tiroir */
  var s6=x.useState(!1),cpsOn=s6[0],setCpsOn=s6[1];
  var searchRef=x.useRef(null),rowsRef=x.useRef(null);
  var ph=subsN(props.playhead,0);
  /* le repli à 60 s sert à PLACER un nouveau sous-titre quand la durée du
     montage est inconnue ; il ne sert jamais de plafond aux correctifs (le
     verdict, lui, reçoit la durée réelle), sinon on refuserait d'étirer la
     dernière réplique d'un montage de 3 minutes. */
  var dur=subsN(props.dur,0)||60;

  /* la touche « / » que le badge annonce — un raccourci affiché doit exister */
  x.useEffect(function(){
    var h=function(e){
      if(e.key!=="/"||e.ctrlKey||e.altKey||e.metaKey)return;
      var t=e.target,tag=t&&t.tagName;
      if(tag==="INPUT"||tag==="TEXTAREA"||tag==="SELECT"||(t&&t.isContentEditable))return;
      if(!searchRef.current)return;
      e.preventDefault();e.stopPropagation();
      try{searchRef.current.focus();searchRef.current.select()}catch(_e){}};
    document.addEventListener("keydown",h,!0);
    return function(){document.removeEventListener("keydown",h,!0)}},[]);

  function emit(next,heavy){if(props.onChange)props.onChange(subsSort(next),!!heavy)}
  function note(m){if(props.onNote)props.onNote(m)}
  function patch(id,p,heavy){
    emit(segs.map(function(s){return s.id===id?subsWith(s,p):s}),heavy)}

  /* AUCUN calcul d'avertissement ici : la liste LIT le verdict unique que le
     tiroir lui passe (subsVerdict). C'est ce qui interdit qu'une réplique soit
     « bloquante » sur la timeline et « à vérifier » dans la liste juste à
     côté — les deux surfaces lisent le MÊME objet, réplique par réplique. */
  var vd=props.verdict||subsVerdictNil();

  var qn=query.trim().toLowerCase();
  var shown=x.useMemo(function(){
    var l=segs;
    if(qn)l=l.filter(function(s){
      return String(s.text||"").toLowerCase().indexOf(qn)>=0});
    /* « signalées » : le filtre qui remplace le déroulement d'une liste
       entière pour retrouver les lignes fautives */
    if(onlyBad)l=l.filter(function(s){return subsSegState(vd,s.id).n>0});
    return l},[segs,qn,onlyBad,vd]);

  function addAt(){
    var sl=subsFreeSlot(segs,ph,dur);
    var s=subsMake(sl.start,sl.end,"");
    emit(segs.concat([s]),!0);
    if(props.onSelect)props.onSelect(s.id);
    note("Sous-titre ajouté à "+subsTc(sl.start)+" — tapez le texte.")}
  function delAt(id){
    emit(segs.filter(function(s){return s.id!==id}),!0);
    note("Sous-titre supprimé.")}
  function splitHere(id){
    var next=subsSplitAt(segs,id,ph);
    if(!next){note("Placez la tête de lecture À L'INTÉRIEUR du segment pour le découper.");return}
    emit(next,!0);note("Segment découpé à "+subsTc(ph)+".")}
  function mergeNext(id){
    var next=subsMergeAt(segs,id);
    if(!next){note("Aucun segment après celui-ci — rien à fusionner.");return}
    emit(next,!0);note("Segments fusionnés.")}
  function setHere(id,which){
    var s=null;
    segs.forEach(function(k){if(k.id===id)s=k});
    if(!s)return;
    if(which==="start"){
      if(ph>=s.end-.05){note("La tête est après la fin du segment — déplacez-la d'abord.");return}
      patch(id,{start:ph},!0)}
    else{
      if(ph<=s.start+.05){note("La tête est avant le début du segment — déplacez-la d'abord.");return}
      patch(id,{end:ph},!0)}}
  /* un correctif = appliquer un PLAN, tel qu'il a été annoncé. Le panneau ne
     recalcule rien : il exécute les `ops` que la carte affichait déjà, donc
     ce qui se passe est EXACTEMENT ce qui était écrit sous le bouton. */
  function applyPlan(plan){
    if(!plan||!plan.ok)return;
    var next=subsApplyPlan(segs,plan);
    emit(next,!0);
    note(plan.label+" — "+plan.effect)}
  function doReflow(n){
    setReflowN(n);
    emit(subsReflow(segs,n),!0)}

  /* import / export — 100 % local, aucun compte, aucun filigrane */
  function doExport(fmt){
    var txt=fmt==="srt"?subsToSrt(segs,style)
      :fmt==="vtt"?subsToVtt(segs,style):subsToTxt(segs);
    if(!txt.trim()){note("Rien à exporter — la piste est vide.");return}
    var base=String(props.srcName||"sous-titres").replace(/[^\w\-. ]+/g,"_");
    var ok=subsDownload(base+"."+fmt,txt,
      fmt==="vtt"?"text/vtt":fmt==="srt"?"application/x-subrip":"text/plain");
    note(ok?"Fichier ."+fmt.toUpperCase()+" écrit ("+
      subsSort(segs).filter(function(s){return !s.hidden}).length+
      " lignes) — local, sans compte, sans filigrane."
      :"Téléchargement refusé par le navigateur.")}
  var fileRef=x.useRef(null);
  function doImport(f){
    if(!f)return;
    var rd=new FileReader();
    rd.onload=function(){
      var got=subsParse(String(rd.result||""));
      if(!got.length){note("Aucun sous-titre lisible dans ce fichier (.srt ou .vtt attendu).");return}
      emit(got,!0);
      note(subsPl(got.length,"sous-titre")+" importé"+(got.length>1?"s":"")+
        " depuis « "+f.name+" ».")};
    rd.onerror=function(){note("Lecture du fichier impossible.")};
    rd.readAsText(f,"utf-8")}

  function tcField(s,which){
    var val=which==="start"?s.start:s.end;
    /* champ non contrôlé + clé dérivée de la valeur : taper « 00:0 » ne se
       fait pas réécrire sous les doigts, mais un calage venu d'ailleurs
       (bouton ⏱, glissement du clip sur la timeline) remonte bien */
    return r.jsxs("span",{className:"sub-tcwrap",children:[
      r.jsx("input",{className:"sub-tc",type:"text",defaultValue:subsTc(val),
        "aria-label":(which==="start"?"Début":"Fin")+" du sous-titre (00:00.000)",
        title:(which==="start"?"Début":"Fin")+" — format 00:00.000",
        onBlur:function(e){
          var v=subsParseTc(e.target.value,val);
          var p={};p[which]=v;
          if(which==="start"&&v>=s.end-.05)p[which]=s.end-.05;
          if(which==="end"&&v<=s.start+.05)p[which]=s.start+.05;
          patch(s.id,p,!0)},
        onKeyDown:function(e){if(e.key==="Enter")e.target.blur()}},
        s.id+which+String(val)),
      r.jsx("button",{className:"sub-tcnow",
        title:"Caler sur la tête de lecture ("+subsTc(ph)+")",
        "aria-label":"Caler le "+(which==="start"?"début":"fin")+" sur la tête de lecture",
        onClick:function(){setHere(s.id,which)},children:"⏱"},"now")]},which)}

  /* ── une ligne par réplique ───────────────────────────────────────────────
     Le pli par défaut : numéro, début, texte, et les défauts SIGNALÉS SUR LA
     LIGNE (pastille rouge/ambre avec le compte). On lit la piste entière d'un
     coup d'œil, et on ne déplie que celle qu'on va corriger. La ligne
     sélectionnée s'ouvre d'elle-même — cliquer un segment sur la timeline
     ouvre donc son éditeur, sans second geste. */
  function isOpen(id){
    var v=openMap[id];
    return v===1?!0:v===0?!1:props.selId===id}
  function toggleOpen(id){
    setOpenMap(function(m){
      var n=Object.assign({},m);n[id]=isOpen(id)?0:1;return n})}
  function pickRow(id){
    if(props.onSelect)props.onSelect(id);
    setOpenMap(function(m){
      if(m[id]==null)return m;
      var n=Object.assign({},m);delete n[id];return n})}

  function segRow(s,i){
    var sel=props.selId===s.id;
    var live=ph>=s.start&&ph<s.end;
    var ws=subsWords(s);
    var aligned=ws.length&&ws[0].src==="align";
    var chars=String(s.text||"").replace(/\s+/g," ").trim().length;
    var len=Math.max(.001,s.end-s.start);
    var cps=chars/len;
    /* la pastille de la ligne SORT DU VERDICT : même sévérité, même compte et
       même couleur que la pastille du segment sur la timeline */
    var est=subsSegState(vd,s.id),lw=est.warns;
    var open=isOpen(s.id);
    var txt=String(s.text||"").replace(/\s+/g," ").trim();
    var head=r.jsxs("div",{className:"sub-r1",role:"button",tabIndex:0,
      "aria-expanded":open,
      onClick:function(){pickRow(s.id)},
      onKeyDown:function(e){
        if(e.key==="Enter"||e.key===" "){e.preventDefault();pickRow(s.id)}
        else if(e.key==="ArrowRight"&&!open)toggleOpen(s.id)
        else if(e.key==="ArrowLeft"&&open)toggleOpen(s.id)},
      onDoubleClick:function(){if(props.onSeek)props.onSeek(s.start)},
      children:[
      r.jsx("span",{className:"sub-rown",children:String(i+1)},"n"),
      r.jsx("button",{className:"sub-rtc",
        title:"Caler la tête de lecture ici ("+subsTc(s.start)+" → "+
          subsTc(s.end)+", "+subsRound(len,2)+" s, "+Math.round(cps)+" car./s)",
        onClick:function(e){e.stopPropagation();if(props.onSeek)props.onSeek(s.start)},
        children:subsTc(s.start)},"tc"),
      r.jsx("span",{className:"sub-rtxt","data-empty":txt?void 0:"",
        title:txt||"Segment sans texte",
        children:txt||"(vide)"},"t"),
      s.hidden?r.jsx("span",{className:"sub-rbadge","data-k":"off",
        title:"Masqué — hors rendu et hors export",children:"masqué"},"h"):null,
      /* UNE pastille par réplique, colorée par sa sévérité la PLUS forte, et
         dont le nombre compte les DÉFAUTS DE CETTE RÉPLIQUE — l'infobulle le
         dit en toutes lettres, pour qu'aucun chiffre de l'écran ne puisse être
         confondu avec un autre. */
      est.sev?r.jsx("span",{className:"sub-rbadge","data-k":est.sev,
        title:subsPl(est.n,"défaut")+" sur cette réplique ("+
          (SUBS_SEVLAB[est.sev]||est.sev)+" au plus fort) : "+
          lw.map(function(w){return w.msg}).join(" · "),
        children:(est.sev==="err"?"!":"·")+(est.n>1?est.n:"")},"b"):null,
      r.jsx("button",{className:"sub-rcar","aria-expanded":open,
        title:open?"Replier cette réplique":"Déplier — bornes, texte, correctifs",
        "aria-label":(open?"Replier":"Déplier")+" le sous-titre "+(i+1),
        onClick:function(e){e.stopPropagation();toggleOpen(s.id)},
        children:open?"▾":"▸"},"c")]},"r1");
    if(!open)
      return r.jsx("div",{className:"sub-row","data-sel":sel?"":void 0,
        "data-live":live?"":void 0,"data-off":s.hidden?"":void 0,
        children:head},s.id);
    return r.jsxs("div",{className:"sub-row","data-sel":sel?"":void 0,
      "data-open":"","data-live":live?"":void 0,"data-off":s.hidden?"":void 0,
      children:[
      head,
      r.jsxs("div",{className:"sub-rowhead",children:[
        tcField(s,"start"),
        r.jsx("span",{className:"sub-arrow","aria-hidden":!0,children:"→"},"ar"),
        tcField(s,"end"),
        r.jsx("span",{className:"sub-rowlen","data-hot":cps>SUBS_CPS_MAX?"":void 0,
          title:chars+" caractères en "+subsRound(len,2)+" s = "+Math.round(cps)+
            " car./s (seuil "+SUBS_CPS_MAX+")",
          children:subsRound(len,2)+" s · "+Math.round(cps)+" c/s"},"len"),
        r.jsx("button",{className:"sub-iconbtn","data-on":s.hidden?"":void 0,
          role:"switch","aria-checked":!s.hidden,
          title:s.hidden?"Réafficher — ce sous-titre repart au rendu"
            :"Masquer — il reste dans la liste mais sort du rendu et de l'export",
          onClick:function(){patch(s.id,{hidden:s.hidden?void 0:!0},!0)},
          children:s.hidden?"🚫":"👁"},"eye"),
        r.jsx("button",{className:"sub-iconbtn sub-del",title:"Supprimer ce sous-titre",
          "aria-label":"Supprimer le sous-titre "+(i+1),
          onClick:function(){delAt(s.id)},children:"✕"},"del")]},"head"),
      r.jsx("textarea",{className:"sub-text",value:s.text||"",rows:2,
        placeholder:"Texte du sous-titre…",
        "aria-label":"Texte du sous-titre "+(i+1),
        onFocus:function(){if(props.onSelect)props.onSelect(s.id)},
        onChange:function(e){patch(s.id,{text:e.target.value})}},"txt"),
      r.jsxs("div",{className:"sub-rowfoot",children:[
        r.jsx("button",{className:"sub-minibtn",
          title:"Découper à la tête de lecture ("+subsTc(ph)+")",
          onClick:function(){splitHere(s.id)},children:"découper"},"sp"),
        r.jsx("button",{className:"sub-minibtn",disabled:i>=segs.length-1,
          title:"Fusionner avec le sous-titre suivant",
          onClick:function(){mergeNext(s.id)},children:"fusionner"},"mg"),
        r.jsx("span",{className:"sub-rowsrc",
          title:aligned?"Timings par mot fournis par la transcription — le karaoké est aligné sur la voix."
            :"Aucun timing par mot : la répartition du karaoké est proportionnelle au nombre de caractères.",
          children:aligned?"mots alignés":"mots répartis"},"src")]},"foot"),
      lw.length?r.jsx("div",{className:"sub-warns",children:lw.map(function(w,k){
        /* un bouton de correction dit CE QU'IL FAIT avant le clic : son
           libellé nomme l'action et son résultat (« Découper en 2 sous-titres »,
           « Étirer à 1,2 s »), et la ligne dessous annonce la conséquence, y
           compris sur les voisins. Pas de plan applicable = pas de bouton,
           mais l'explication reste. */
        var p=w.plan||null,alt=p&&p.alt&&p.alt.ok?p.alt:null;
        return r.jsxs("div",{className:"sub-warn","data-sev":w.sev,children:[
          r.jsx("span",{className:"sub-warnicon","aria-hidden":!0,
            children:w.sev==="err"?"!":"·"},"i"),
          r.jsx("span",{className:"sub-warnmsg",children:w.msg},"m"),
          p&&p.ok?r.jsx("button",{className:"sub-minibtn sub-fix",
            title:p.effect,onClick:function(){applyPlan(p)},
            children:p.label},"f"):null,
          p&&p.ok?r.jsx("span",{className:"sub-warnwhat",children:p.effect},"e")
            :null,
          p&&!p.ok&&p.blocked
            ?r.jsx("span",{className:"sub-warnwhat","data-blocked":"",
              children:p.blocked},"b"):null,
          alt?r.jsx("button",{className:"sub-minibtn sub-fixalt",
            title:alt.effect,onClick:function(){applyPlan(alt)},
            children:alt.label},"fa"):null,
          alt?r.jsx("span",{className:"sub-warnwhat",children:alt.effect},"ae")
            :null]},"w"+k)})},"warns"):null]},s.id)}

  /* tous les comptes viennent du verdict : aucun n'est refait ici */
  var nOff=vd.counts.masquees,nBad=vd.counts.signalees,nBlk=vd.counts.bloquantes;
  /* signalées que le filtre ou la recherche cachent en ce moment : un badge
     qui annonce des défauts pendant que rien à l'écran ne les désigne, c'est
     le défaut qu'on ferme ici. */
  var hiddenBad=nBad-shown.filter(function(s){
    return subsSegState(vd,s.id).n>0}).length;
  var empty=!segs.length;
  /* le champ de fichier vit hors des deux états : il sert au bouton
     « importer » du plein comme du vide */
  var fileInput=r.jsx("input",{className:"sub-file",type:"file",ref:fileRef,
    accept:".srt,.vtt,.txt",style:{display:"none"},"aria-hidden":!0,
    onChange:function(e){doImport(e.target.files&&e.target.files[0]);
      e.target.value=""}},"file");
  var btnAdd=r.jsx("button",{className:"sub-btn sub-add",
    title:"Ajouter un sous-titre à la tête de lecture ("+subsTc(ph)+")",
    onClick:addAt,children:empty?"+ première réplique":"+ sous-titre"},"add");
  var btnImport=r.jsx("button",{className:"sub-btn",
    title:"Importer un .srt ou un .vtt déjà écrit ailleurs",
    onClick:function(){if(fileRef.current)fileRef.current.click()},
    children:"importer .srt / .vtt"},"imp");

  /* ── PISTE VIDE ────────────────────────────────────────────────────────────
     L'absence se dit UNE fois, à l'endroit où on peut la lever, avec les
     gestes qui la lèvent. Recherche, découpe automatique, compteurs, filtres
     et export ne sont pas grisés : ils ne sont pas là — une commande qui ne
     peut rien faire sur un ensemble vide n'a rien à occuper de la place. */
  if(empty)
    return r.jsxs("div",{className:"sub-segs",children:[
      r.jsx(SubsAlert,{}),
      fileInput,
      r.jsxs("div",{className:"sub-empty",children:[
        r.jsx("div",{className:"sub-emptytxt",children:"Aucun sous-titre sur la piste S1."}),
        r.jsx("div",{className:"sub-emptyhint",
          children:"Écrivez la première réplique à la tête de lecture ("+
            subsTc(ph)+"), reprenez un fichier existant, ou lancez la "+
            "transcription automatique ci-dessus."}),
        r.jsxs("div",{className:"sub-emptyact",children:[btnAdd,btnImport]})]})]});

  var anyOpen=segs.some(function(s){return isOpen(s.id)});
  return r.jsxs("div",{className:"sub-segs",children:[
    r.jsx(SubsAlert,{}),
    fileInput,
    r.jsxs("div",{className:"sub-toolrow",children:[
      btnAdd,
      btnImport,
      r.jsx("button",{className:"sub-btn","data-on":cpsOn?"":void 0,
        "aria-expanded":cpsOn,
        title:"Redécouper TOUTE la piste : les répliques voisines sont remises "+
          "bout à bout puis recoupées à la longueur choisie. Le nombre de "+
          "sous-titres change ; le calage suit les mots.",
        onClick:function(){setCpsOn(function(v){return !v})},
        children:"redécouper toute la piste "+(cpsOn?"▾":"▸")},"rf")]}),
    cpsOn?r.jsxs("div",{className:"sub-cpsrow",children:[
      r.jsx("span",{className:"sub-plabel",children:"Caractères par sous-titre"}),
      r.jsx("input",{className:"sub-range",type:"range",min:12,max:96,step:1,
        value:Math.round(subsN(reflowN!=null?reflowN:style.maxChars,42)),
        "aria-label":"Caractères par sous-titre",
        title:"Recompose la découpe en direct — les mots ne sont jamais coupés",
        onChange:function(e){doReflow(subsN(e.target.value,42))}}),
      r.jsx("span",{className:"sub-pval",
        children:Math.round(subsN(reflowN!=null?reflowN:style.maxChars,42))}),
      /* l'effet AVANT le geste : combien de sous-titres ce réglage produit */
      r.jsx("span",{className:"sub-cpsout",
        title:"Nombre de sous-titres que cette longueur produit sur la piste",
        children:"→ "+subsReflow(segs,subsN(reflowN!=null?reflowN:style.maxChars,42))
          .length+" sous-titres"})]}):null,
    /* recherche et filtres sur UNE ligne : le compte total est déjà dans
       l'en-tête du tiroir, il n'a pas à être redit ici */
    r.jsxs("div",{className:"sub-searchrow",children:[
      r.jsx("input",{className:"sub-search",ref:searchRef,type:"text",value:query,
        placeholder:"Rechercher…",
        "aria-label":"Rechercher dans les sous-titres",
        onChange:function(e){setQuery(e.target.value)}},"q"),
      r.jsx("kbd",{className:"sub-kbd",title:"Touche / — aller à la recherche",
        children:"/"},"k"),
      nOff?r.jsx("span",{className:"sub-statoff",
        title:subsPl(nOff,"réplique")+" masquée(s) : hors rendu et hors export",
        children:subsPl(nOff,"masquée")},"o"):null,
      nBad?r.jsx("button",{className:"sub-statfilt",
        "data-on":onlyBad?"":void 0,"data-sev":"warn",
        "aria-pressed":onlyBad,
        title:(onlyBad?"Revoir toute la piste. ":"N'afficher que ces répliques. ")+
          subsPl(nBad,"réplique")+" signalée"+(nBad>1?"s":"")+" sur "+
          vd.counts.repliques+", dont "+subsPl(nBlk,"bloquante")+
          " — chacune porte son correctif",
        onClick:function(){setOnlyBad(function(v){return !v})},
        children:subsPl(nBad,"signalée")},"b"):null,
      r.jsx("button",{className:"sub-statfilt",
        title:anyOpen?"Tout replier":"Tout déplier — bornes et correctifs",
        onClick:function(){
          var m={};segs.forEach(function(s){m[s.id]=anyOpen?0:1});
          setOpenMap(m)},
        children:anyOpen?"replier":"déplier"},"x")]}),
    /* le badge de l'onglet compte TOUTE la piste ; la liste, elle, peut être
       filtrée. Quand les deux ne montrent pas la même chose, on le dit et on
       offre le geste — un badge sans rien à l'écran qui le désigne, c'est
       exactement le défaut qu'on ferme. */
    hiddenBad>0?r.jsxs("div",{className:"sub-hidbad",role:"status",children:[
      r.jsx("span",{className:"sub-hidbadtxt",
        children:hiddenBad>1
          ?hiddenBad+" répliques signalées ne sont pas affichées : "+
            (qn?"la recherche":"le filtre")+" les masque."
          :"1 réplique signalée n'est pas affichée : "+
            (qn?"la recherche":"le filtre")+" la masque."},"t"),
      r.jsx("button",{className:"sub-minibtn",
        title:"Effacer la recherche et le filtre pour voir toutes les répliques signalées",
        onClick:function(){setQuery("");setOnlyBad(!1)},
        children:"tout afficher"},"a")]},"hb"):null,
    shown.length
      ?r.jsx("div",{className:"sub-rows",ref:rowsRef,children:shown.map(segRow)})
      :r.jsxs("div",{className:"sub-empty",children:[
        r.jsx("div",{className:"sub-emptytxt",children:onlyBad
          ?"Aucune réplique signalée."
          :"Aucun sous-titre contenant « "+qn+" »."}),
        r.jsx("div",{className:"sub-emptyhint",children:onlyBad
          ?"La piste passe le contrôle de lisibilité."
          :"Effacez la recherche pour revoir toute la piste."})]}),
    r.jsxs("div",{className:"sub-exportrow",children:[
      r.jsx("span",{className:"sub-plabel",title:
        "Écrit localement par l'application : pas de compte, pas de filigrane, "+
        "pas de plafond mensuel.",children:"Télécharger"},"l"),
      ["srt","vtt","txt"].map(function(f){
        return r.jsx("button",{className:"sub-btn",
          title:"Exporter en ."+f.toUpperCase()+" — fichier écrit ici, hors ligne",
          onClick:function(){doExport(f)},children:"."+f.toUpperCase()},f)})]})]})};

/* ── le contrôle qualité du backend, une fois pour tout le tiroir ──────────
   `POST /api/subtitles/check` rend TROIS choses : les avertissements par
   réplique, ceux du STYLE (sans index de segment, parce qu'ils portent sur
   le style entier) et les écarts nommés entre l'aperçu et la gravure.
   Le POST vivait dans l'onglet Répliques : les deux derniers ne se
   rafraîchissaient donc jamais pendant qu'on réglait le style — c'est-à-dire
   exactement au moment où ils servent. Il vit maintenant dans le tiroir. */
/* `style_warnings` et `unsupported` se recouvrent : le fond translucide sous
   karaoké est à la fois une règle de qualité et un écart aperçu/gravure. Une
   liste unique, dédoublonnée sur le texte, avec le geste quand il existe —
   sinon le panneau afficherait deux fois le même problème et compterait 2. */
function subsStyleIssues(chk){
  var out=[],vus={};
  function add(o){
    var m=String(o&&o.msg||"");
    if(!m||vus[m])return;vus[m]=1;out.push(o)}
  /* La zone sûre d'abord : c'est NOTRE repère, tracé par NOTRE aperçu, et il
     se répare d'un clic. */
  ((chk&&chk.safe)||[]).forEach(add);
  ((chk&&chk.style)||[]).forEach(function(w){
    add({msg:String(w.msg||""),fix:w.fix||null,about:w.about||[],
      sev:w.sev||"warn"})});
  var u=(chk&&chk.unsupported)||{};
  Object.keys(u).forEach(function(k){
    add({msg:String(u[k]||""),fix:null,about:[],sev:"info",cle:k})});
  return out}

/* Le POST ne rend plus rien à un appelant : il RANGE son résultat dans le
   magasin partagé, avec la clé de la piste mesurée. Toute surface qui demande
   le verdict de CETTE piste le verra ; aucune ne peut en avoir un autre. */
function subsUseCheck(segs,style,dur,svc){
  var key=x.useMemo(function(){
    return subsKeyOf(segs,style,dur)},[segs,style,dur]);
  x.useEffect(function(){
    /* backend connu injoignable : on n'envoie RIEN. Un POST toutes les 450 ms
       vers une route absente remplit la console d'erreurs sans rien apporter
       — le calcul local, lui, tourne déjà. */
    if(svc.st!=="ok"){subsChkClear();return}
    var body={segments:subsSort(segs).map(function(s){
      return {id:s.id,start:s.start,end:s.end,text:s.text}}),
      style:style,dur:dur};
    var dead=!1;
    var h=setTimeout(function(){
      subsPost("/api/subtitles/check",body).then(function(d){
        if(dead)return;
        if(d&&Array.isArray(d.warnings))subsChkPut(key,d);else subsChkClear()},
        function(){if(!dead)subsChkClear()})},450);
    return function(){dead=!0;clearTimeout(h)}},[key,svc.st,svc.tick])}

/* Abonnement au magasin : une surface React qui lit le verdict doit se
   redessiner quand le moteur répond, sinon elle affiche encore le calcul local
   pendant que sa voisine affiche celui du moteur — la divergence par le retard. */
function subsUseVerdict(segs,style,dur){
  var s=x.useState(0),setT=s[1];
  x.useEffect(function(){
    return subsChkSub(function(){setT(function(t){return t+1})})},[]);
  return subsVerdict(segs,style,dur)}

/* ═════════════════ Tiroir — Segments · Style ════════════════════════════════ */
const SubsDrawer=(props)=>{
  var svc=subsSvcUse();
  var s1=x.useState("segments"),tab=s1[0],setTab=s1[1];
  var s2=x.useState(null),trJob=s2[0],setTrJob=s2[1];
  /* Les avertissements de STYLE et les écarts aperçu/gravure viennent du même
     POST /api/subtitles/check que ceux des répliques. Le panneau les jetait
     faute d'index de segment : ils n'ont pas d'index PARCE QU'ils portent sur
     le style entier. On les remonte donc ici, pour les poser dans l'onglet
     où l'on peut agir dessus — Style. */
  var nt=subsUseNote(),note=nt[0],fireNote=nt[1];
  var rootRef=x.useRef(null);
  var open=!!props.open;
  var segs=subsSort(props.segments||[]);
  var style=Object.assign(subsDefaultStyle(),props.style||{});
  /* le POST range son résultat dans le magasin partagé ; le VERDICT est lu
     une seule fois ici et descend tel quel dans les deux onglets. Le tiroir
     ne calcule plus rien : c'est ce qui rend impossible qu'un badge d'onglet
     annonce un chiffre que la liste ne montre pas. */
  subsUseCheck(segs,style,props.dur,svc);
  var vd=subsUseVerdict(segs,style,props.dur);

  x.useEffect(function(){if(open)subsProbe()},[open]);
  x.useEffect(function(){
    if(open&&rootRef.current)
      try{rootRef.current.focus({preventScroll:!0})}catch(_e){}},[open]);
  function note2(m){fireNote(m);if(props.onNote)props.onNote(m)}

  /* transcription automatique — la SEULE fonction qui a besoin du backend.
     Absente : on le dit sans détour, et on rappelle l'issue locale. */
  function transcribe(){
    if(trJob&&trJob.busy)return;
    setTrJob({busy:!0,step:"envoi…",pct:0});
    /* `clips` porte la timeline : le backend y trouve la NARRATION (texte déjà
       écrit) et cale dessus — gratuit, hors ligne, et orthographe exacte, là
       où une transcription payante écrit « Dipotus » pour « Deepotus ». Sans
       texte, il retombe sur la transcription du média `src`. */
    subsPost("/api/subtitles/transcribe",
      {src:props.srcRef||null,clips:props.srcClips||null,
       lang:"fr",cps:subsN(style.maxChars,42)})
      .then(function(d){
        var id=d&&d.job_id;
        if(!id)throw new Error("pas de job_id");
        var tick=function(){
          subsJson("/api/subtitles/jobs/"+encodeURIComponent(id)).then(function(j){
            var stt=String(j&&j.status||"");
            if(stt==="done"){
              var got=(j.segments||[]).map(function(o){
                var s=subsMake(subsN(o.start,0),subsN(o.end,1),String(o.text||""));
                if(Array.isArray(o.words))s.words=o.words;
                return s});
              setTrJob(null);
              if(!got.length){note2("Transcription terminée : aucune parole détectée.");return}
              if(props.onChange)props.onChange(subsSort(got),!0);
              note2(got.length+" sous-titres transcrits — relisez, la machine se trompe.")}
            else if(stt==="failed"){
              setTrJob(null);
              note2("Transcription échouée : "+String(j&&j.error||"raison non fournie"))}
            else{
              setTrJob({busy:!0,step:String(j&&j.step||"transcription…"),
                pct:subsN(j&&j.pct,0)});
              setTimeout(tick,900)}},
          function(){setTrJob(null);
            note2("Suivi de la transcription perdu — le backend ne répond plus.")})};
        setTimeout(tick,700)},
      function(){
        setTrJob(null);
        note2("Transcription automatique indisponible : POST /api/subtitles/transcribe "+
          "ne répond pas. Tout le reste marche hors ligne — écrivez, importez "+
          "un .srt, ou relancez DeepotusVideoGen.")})}

  if(!open)return null;
  var C=vd.counts;
  return r.jsxs("aside",{className:"sub-drawer",ref:rootRef,tabIndex:-1,
    role:"group","aria-label":"Sous-titres",
    onKeyDown:function(e){
      if(e.key==="Escape"&&props.onClose){props.onClose();e.stopPropagation()}},
    children:[
    /* en-tête et onglets ne répètent PAS le compte quand il n'y a rien :
       « Sous-titres 0 » + « Segments 0 » + « 0 sous-titres » + la prose, c'est
       quatre fois la même absence. Les compteurs n'apparaissent que lorsqu'ils
       comptent quelque chose. */
    r.jsxs("div",{className:"sub-head",children:[
      r.jsx("span",{className:"sub-title",children:"Sous-titres"}),
      C.repliques?r.jsx("span",{className:"sub-count",
        title:"Lignes posées sur la piste S1, masquées comprises",
        children:subsPl(C.repliques,"réplique")}):null,
      r.jsx("button",{className:"sub-iconbtn sub-close",title:"Fermer (Échap)",
        "aria-label":"Fermer le panneau de sous-titres",
        onClick:function(){if(props.onClose)props.onClose()},children:"✕"})]}),
    /* ── ce que chaque nombre COMPTE, écrit à côté du nombre ────────────────
       Les badges d'onglet et la chip de la barre d'outils comptent tous des
       RÉPLIQUES ; les défauts, eux, sont nommés « défauts ». Deux nombres
       différents à l'écran ne peuvent donc plus désigner la même chose, et
       aucun ne se lit sans son unité. Tous sortent du même verdict. */
    C.repliques?r.jsxs("div",{className:"sub-tally",role:"status",
      title:"Signalées = répliques portant au moins un défaut. Bloquantes = "+
        "sous-ensemble des signalées, celles qui portent un défaut bloquant. "+
        "Défauts = total des défauts (une réplique peut en porter plusieurs). "+
        "Tous ces chiffres sortent du même contrôle ("+
        (vd.source==="moteur"?"moteur":"calcul local")+").",children:[
      r.jsxs("span",{className:"sub-tal","data-k":"repliques",
        children:[r.jsx("b",{children:String(C.repliques)}),
          C.repliques<2?"réplique":"répliques"]},"r"),
      r.jsxs("span",{className:"sub-tal","data-k":"signalees",
        "data-sev":C.signalees?"warn":void 0,
        children:[r.jsx("b",{children:String(C.signalees)}),
          C.signalees<2?"signalée":"signalées"]},"s"),
      r.jsxs("span",{className:"sub-tal","data-k":"bloquantes",
        "data-sev":C.bloquantes?"err":void 0,
        children:[r.jsx("b",{children:String(C.bloquantes)}),
          C.bloquantes<2?"bloquante":"bloquantes"]},"b"),
      r.jsxs("span",{className:"sub-tal","data-k":"defauts",
        children:[r.jsx("b",{children:String(C.defauts)}),
          C.defauts<2?"défaut":"défauts"]},"d"),
      C.masquees?r.jsxs("span",{className:"sub-tal","data-k":"masquees",
        children:[r.jsx("b",{children:String(C.masquees)}),
          C.masquees<2?"masquée":"masquées"]},"m"):null,
      r.jsx("span",{className:"sub-talsrc",
        children:vd.source==="moteur"?"moteur":"local"},"o")]}):null,
    r.jsxs("div",{className:"sub-tabs",role:"tablist",children:[
      r.jsxs("button",{className:"sub-tab",role:"tab","aria-selected":tab==="segments",
        "data-on":tab==="segments"?"":void 0,
        onClick:function(){setTab("segments")},children:[
        "Répliques",
        /* Le badge compte des RÉPLIQUES SIGNALÉES — le même nombre que la chip
           de la barre d'outils et que le compte de la ligne du dessus. Il
           comptait autrefois des avertissements : trois surfaces, trois
           chiffres, aucun ne désignait ce que la liste montrait.
           COULEUR : ambre, toujours. Le rouge est réservé à ce qui EST
           bloquant — une réplique en rouge sur la piste, une pastille rouge
           sur sa ligne, et le compte « n bloquantes » ci-dessus. Peindre en
           rouge un total de 12 dont une seule est bloquante remettrait la
           timeline et la liste en désaccord, autrement. */
        C.signalees?r.jsx("span",{className:"sub-tbad","data-sev":"warn",
          title:subsPl(C.signalees,"réplique")+" signalée"+
            (C.signalees>1?"s":"")+", dont "+subsPl(C.bloquantes,"bloquante")+
            " (le détail est sur chaque ligne)",
          children:String(C.signalees)}):null]},"segments"),
      r.jsxs("button",{className:"sub-tab",role:"tab","aria-selected":tab==="style",
        "data-on":tab==="style"?"":void 0,
        onClick:function(){setTab("style")},children:[
        "Style et placement",
        C.ecarts?r.jsx("span",{className:"sub-tbad","data-soft":"",
          title:C.ecarts+" écart(s) entre l'aperçu et la gravure — ils portent "+
            "sur le STYLE, pas sur une réplique ; le détail est dans l'onglet",
          children:String(C.ecarts)}):null]},"style")]}),
    r.jsxs("div",{className:"sub-trrow",children:[
      r.jsx("button",{className:"sub-btn sub-tr",disabled:!!(trJob&&trJob.busy),
        title:"Transcrire la bande son du montage (backend requis) — "+
          "tout le reste du panneau marche hors ligne",
        onClick:transcribe,
        children:trJob&&trJob.busy?"Transcription…":"Transcrire l'audio"}),
      trJob&&trJob.busy
        ?r.jsx("span",{className:"sub-trstep",
          children:trJob.step+(trJob.pct?" · "+Math.round(trJob.pct)+" %":"")})
        :r.jsx("span",{className:"sub-trhint",
          children:"ou écrivez à la main — c'est gratuit et hors ligne"})]}),
    r.jsx("div",{className:"sub-body",children:
      tab==="segments"
        ?r.jsx(SubsSegments,{segments:segs,style:style,onChange:props.onChange,
          playhead:props.playhead,dur:props.dur,selId:props.selId,
          /* note INTERNE seulement : l'hôte affiche la sienne en surimpression
             du lecteur, juste au-dessus de ce tiroir — deux fois le même
             message au même endroit, c'est du bruit */
          onSelect:props.onSelect,onSeek:props.onSeek,onNote:fireNote,
          verdict:vd,srcName:props.srcName})
        :r.jsx(SubsStyle,{style:style,onChange:props.onStyle,verdict:vd})}),
    note?r.jsx("div",{className:"sub-note",role:"status","aria-live":"polite",
      children:note}):null]})};

/* ── export contrat ───────────────────────────────────────────────────────── */
window.DzSubs={ready:!0,Drawer:SubsDrawer,Overlay:SubsOverlay,Style:SubsStyle,
  Segments:SubsSegments,Alert:SubsAlert,
  defaultStyle:subsDefaultStyle,PRESETS:SUBS_PRESETS,FONTS:SUBS_FONTS_FB,
  ANIMS:SUBS_ANIMS,words:subsWords,warnings:subsWarnings,reflow:subsReflow,
  /* ── LE point d'accès au verdict unique ────────────────────────────────
     `verdict(segments, style, dur)` rend {list, bySeg, style, counts, source}.
     TOUTE surface — timeline du Montage, chip de la barre d'outils, liste du
     tiroir, badges d'onglet, inspecteur — lit CE résultat. Aucune ne
     recalcule le sien : c'est l'invariant que verrouille
     `backend/tests/test_subs_single_source.py` et que mesure à l'écran
     `scripts/qa/subs-consistency.js`. */
  verdict:subsVerdict,verdictNil:subsVerdictNil,segState:subsSegState,
  keyOf:subsKeyOf,sevLabels:SUBS_SEVLAB,
  chkTick:function(){return SUBS_CHK.tick},onVerdict:subsChkSub,
  safeIssues:subsSafeIssues,outOfSafe:subsOutOfSafe,
  SAFE:{action:SUBS_SAFE_ACTION,title:SUBS_SAFE_TITLE,social:SUBS_SOCIAL_BOT,
    marginDefault:SUBS_MARGIN_DEF,widthDefault:SUBS_WIDTH_DEF},
  splitAt:subsSplitAt,mergeAt:subsMergeAt,make:subsMake,sort:subsSort,
  freeSlot:subsFreeSlot,
  labelOf:subsLabelOf,at:subsAt,
  parse:subsParse,toSrt:subsToSrt,toVtt:subsToVtt,toTxt:subsToTxt,
  tc:subsTc,parseTc:subsParseTc,hist:{t:0},
  svc:SUBS_SVC,retry:subsRetryNow};
