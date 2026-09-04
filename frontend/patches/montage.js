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
     window.DzTracks = {ready, TrackAdd, headBtns, TextDrawer,
                         rippleCut, withWords,
                         gradeAllBtn, gradeAll, gradeOf,
                         Projects, projLine, projWhen,
                         tracksOf, from, payload, busSync,
                         pickTrack, isVideoJob, LibBtn, badSrc,
                         replaceSrc, revertSrc, replaceBtn, revertBtn,
                         newerLine, NewerHint,
                         move, moveTo, add, remove, group, DEFAULTS}

   - replaceSrc(clip, src, label, srcDur, now) — P6 : la SOURCE d'un plan
     échangée sans que rien d'autre bouge. PURE, rend {clip, warn, note} et
     ne mute pas l'entrée. Elle recale la fenêtre de source (srcIn / end)
     quand la nouvelle est trop courte, et le DIT.
   - revertSrc(clip) — l'autre voie de retour : dépile `src_history` et rend
     la source précédente AVEC les bornes d'alors. `null` sans historique.
   - replaceBtn(sel, onArm) / revertBtn(sel, onRevert) — les deux boutons de
     l'inspecteur, sans hook, donc exécutables sous node.
   - newerLine(c) — la ligne d'une proposition (PURE).
   - NewerHint({jobId, onPick}) — « une version plus récente existe » :
     interroge GET /api/montage/newer, dont le rapprochement est une
     HEURISTIQUE de titre, et le dit.

   - pickTrack(tracks, kind) — l'identifiant d'une piste QUI EXISTE, du genre
     demandé, la première dans l'ordre d'affichage ; "" si le projet n'en
     porte aucune. PURE. C'est elle qui répare « Envoyer vers → Montage » :
     le clip s'y posait sur « v2 » sans vérifier que v2 soit là.
   - isVideoJob(job, exts) — le critère du sélecteur « Rendus vidéo », appuyé
     sur la liste d'extensions SERVIE PAR LE BACKEND (_VIDEO_EXTS, via
     GET /api/montage/media-rules) : aucune extension n'est écrite ici.
     PURE. Sans liste, elle ne filtre pas — et le sélecteur le dit.
   - LibBtn({tracks,onPick,note}) — le bouton « Bibliothèque… » de la barre
     de transport : il ouvre le sélecteur d'assets sur la piste vidéo
     résolue. Il n'existait AUCUN bouton pour ajouter un clip ailleurs que
     dans l'en-tête d'une piste, au survol.
   - badSrc(clip, onFix) — la chip « pas une vidéo » posée sur un clip que
     GET /project a signalé dans `v1_non_video`. Cliquable : elle rouvre la
     Bibliothèque sur la piste du clip.

   - rippleCut(clips,t0,t1,opts) — coupe d'une PLAGE de temps sur toutes les
     pistes non verrouillées. PURE : c'est l'autre moitié du cœur exécuté
     sous node, par backend/tests/test_montage_texte.py.
   - withWords(clips, aligned) — recolle à chaque clip de narration les mots
     que le backend a calés pour lui, pour que la coupe sache répartir son
     texte. PURE elle aussi.
   - TextDrawer({open,clips,onCut,note}) — le panneau « Texte » : la
     narration mot par mot, les remplissages marqués, la sélection coupée.

   - gradeAll(clips, srcId, trackId) — recopie l'étalonnage de base d'un plan
     sur tous les plans réels d'une piste — CELLE du plan sélectionné, pas
     « v1 » en dur. PURE, testée sous node.
   - gradeAllBtn(sel, clips, setClips, pushHistory, setDirty, note) — le
     bouton qui le déclenche, posé sous la pile d'effets de l'inspecteur.

   - Projects({name,projectId,payload,onOpen,onNamed,onBefore,onFail,note})
     — le popover « projets » de la barre de transport : lister,
     « enregistrer sous… », ouvrir, dupliquer, renommer, supprimer. Les deux
     gestes destructifs (ouvrir, supprimer) ARMENT avant de frapper ; seul
     OUVRIR appelle `onBefore`, où l'éditeur annule son autosave en vol.
     SUPPRIMER ne l'appelle plus depuis le 04/09/2026 — le serveur ferme
     cette course-là tout seul, voir le commentaire de `doDel`.
   - projLine(p) / projWhen(iso) — la ligne de résumé d'un projet et sa date,
     PURES et sans fuseau : c'est la part de P5 que node exécute.

   - TrackAdd({tracks,onChange}) — les deux boutons « + piste vidéo » /
     « + piste audio » de la barre de transport. Ils disaient « + vidéo » et
     « + audio » jusqu'à P9 : ils ajoutent une PISTE, et le libellé le dit
     maintenant.
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

/* ── P9 : poser un clip sur une piste QUI EXISTE ────────────────────────────
   Rend l'identifiant de la PREMIÈRE piste du genre demandé, dans l'ordre
   d'affichage (haut → bas), ou "" si le projet n'en porte aucune.

   Pourquoi cette fonction existe : le dépôt posait ses clips sur « v2 » par
   défaut, sans jamais vérifier que v2 est là. MESURÉ dans la sauvegarde du
   04/09/2026, `tracks` vaut [v1, a2, a1, a3, s1] — pas de v2. Le clip
   entrait bien dans `clips`, il était sauvegardé, il serait parti au rendu
   en incrustation ; mais la timeline ne dessine QUE les pistes du projet :
   il était invisible et inselectionnable. « Rien n'est apparu » était exact,
   et le clip était pourtant là.

   Le genre se DÉDUIT de l'identifiant quand la piste ne le porte pas
   (dzmKindOf) : une liste restaurée d'une vieille sauvegarde n'a que des
   `id`, et exiger `kind` l'aurait fait rendre "" — c'est-à-dire un refus,
   sur un projet parfaitement valable. */
function dzmPickTrack(ts,kind){
  var want=kind==="audio"?"audio":kind==="subs"?"subs":"video";
  var list=(ts&&ts.length)?ts:[];
  for(var i=0;i<list.length;i++){
    var t=list[i];
    if(!t||!t.id)continue;
    if(dzmKindOf(t.id,t.kind)===want)return String(t.id)}
  return ""}

/* ── P9 : « ce rendu est-il une vidéo ? », posé une seule fois ─────────────
   `exts` est la liste servie par GET /api/montage/media-rules, c'est-à-dire
   `_VIDEO_EXTS` de montage_service.py — LA règle du rendu, pas une copie.
   Rien n'est réécrit ici : cette fonction ne connaît aucune extension.

   Sans `exts` (route injoignable), elle ne filtre PAS et rend vrai : c'est
   le seul repli honnête. Une liste vide en dur aurait affiché « aucun rendu
   vidéo terminé » sur une Bibliothèque pleine ; une liste d'extensions
   écrite ici aurait divergé du backend au premier format ajouté. Le
   sélecteur DIT à l'écran qu'il ne filtre pas.

   `final_video_path` PRIME sur `video_path`, dans cet ordre : c'est celui de
   `_resolve_src` côté serveur (`jr.final_video_path or jr.video_path`). Le
   critère d'avant testait `video_path || final_video_path` — sur un job dont
   le brut est une vidéo et le fini une image, les deux ne rendent pas la
   même chose, et c'est le serveur qui a raison.
   AUCUNE EXTENSION N'EST ÉCRITE DANS CE FICHIER, et le banc le vérifie
   (`M16c_la_couche_ne_recopie_aucune_extension`) : une seconde liste
   divergerait de `_VIDEO_EXTS` au premier format ajouté. */
function dzmVideoExt(fp){
  var nm=String(fp||"").replace(/\\/g,"/").split("/").pop();
  var k=nm.lastIndexOf(".");
  return k>0?nm.slice(k).toLowerCase():""}
function dzmIsVideoJob(j,exts){
  if(!j||j.status!=="done")return !1;
  /* la vignette d'une PRÉVISUALISATION de montage n'est pas un rendu à
     reposer — critère conservé tel quel du bundle. */
  if(j.provider==="montage"&&String(j.image_filename||"").indexOf("_preview")>=0)return !1;
  var fp=j.final_video_path||j.video_path;
  if(!fp)return !1;
  if(!exts||!exts.length)return !0;
  var sfx=dzmVideoExt(fp);
  if(!sfx)return !1;
  for(var i=0;i<exts.length;i++)if(String(exts[i]||"").toLowerCase()===sfx)return !0;
  return !1}

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

/* ── P3 : couper une PLAGE de temps, sur toutes les pistes à la fois ───────
   `rippleCut(clips, t0, t1, opts)` — PUR : aucune lecture d'état, aucune
   mutation de l'entrée (les clips inchangés sont rendus PAR RÉFÉRENCE, ce
   que React aime, et les clips modifiés sont des copies). C'est ce que le
   banc backend/tests/test_montage_texte.py exécute sous node.

   Le contrat tient dans UNE fonction de temps, appliquée partout :

       f(t) = t          si t ≤ t0
            = t0         si t0 < t < t1
            = t − (t1−t0) si t ≥ t1

   D'où, pour chaque clip : ce qui est dans [t0,t1[ disparaît, ce qui
   chevauche est FENDU (la moitié droite reprend en `srcIn` là où la source
   en était — VITESSE COMPRISE : à 2×, une seconde de timeline consomme deux
   secondes de source), et tout ce qui suit REMONTE. Les pistes en BOUCLE
   (la musique) ne se fendent pas : leurs deux bornes passent par f, donc
   elles RACCOURCISSENT — fendre une boucle en deux la ferait redémarrer au
   milieu, ce qui s'entend.

   ÉCART ASSUMÉ AVEC LE PLAN, mesuré : le plan raccourcissait TOUTE piste en
   boucle de (t1−t0), sans regarder où elle se trouve. Une musique de 0,2 s
   posée AVANT la coupe tombait alors à durée nulle, et une musique posée
   APRÈS gardait son point de départ pendant que tout le reste remontait.
   f(t) traite les trois positions du même geste (voir les trois lignes
   `boucle_*` du banc).

   ENTRÉES MOLLES, toutes mesurées : `t0 > t1` est remis à l'endroit (le
   glisser de sélection peut partir du dernier mot) ; une plage NULLE ne
   fend rien du tout et rend `removed:0` (le code du plan y coupait un clip
   en deux sans rien retirer) ; une plage hors de tous les clips les laisse
   intacts mais retire quand même le TEMPS DE TIMELINE ; une piste
   verrouillée n'est pas touchée ; `speed` absente, nulle ou illisible vaut
   1 (`speed: 0` est la valeur « non réglée » du modèle de clip).

   LE TEXTE SUIT LES MOTS : un clip fendu qui porte `text` ET `words` voit
   chaque moitié reprendre le texte de SES mots (voir dzmCutText). C'est ce
   qui empêche un bloc de narration fendu de garder sa phrase entière des
   deux côtés. Un clip qui n'a PAS de `words` garde son `text` tel quel —
   rien ne saurait dire quel morceau lui revient ; c'est `dzmWithWords` qui
   les lui pose, depuis le calage du backend, avant la coupe. */
function dzmR3(v){return Math.round(v*1000)/1000}
function dzmRipT(t,a,b,len){
  var v=Number(t)||0;
  return v<=a?dzmR3(v):(v<b?a:dzmR3(v-len))}
/* Mots d'un sous-titre fendu : on garde ceux du CÔTÉ demandé, et on les
   RECALE. Sans le recalage ils gardaient leur date d'avant la coupe et le
   karaoké s'allumait après la fin de sa propre ligne. Un mot à cheval sur
   une borne n'est gardé que par le côté où il COMMENCE : jamais deux fois. */
function dzmCutWords(ws,a,b,len,left){
  return (ws||[]).filter(function(w){
    var s=Number(w&&w.start)||0;
    return left?(s<a):(s>=b)}).map(function(w){
    var s=dzmRipT(w.start,a,b,len),e=dzmRipT(w.end,a,b,len);
    /* BORNAGE. Un mot À CHEVAL sur `a` (il commence avant, il finit après
       `b`) part à GAUCHE — c'est là qu'il commence — mais sa fin, elle,
       retombe au-delà de `a` : le mot finissait HORS de sa propre moitié.
       Chaque moitié borne donc ses mots à sa plage. */
    if(left)e=Math.min(e,a);else s=Math.max(s,a);
    return Object.assign({},w,{start:s,end:Math.max(s,e)})})}
/* Le TEXTE d'une moitié est celui de ses mots — même convention que
   `subsSplitAt` du bundle, qui découpe déjà un sous-titre ainsi
   (`.join(" ")`). Sans elle, fendre un bloc de narration laissait la phrase
   ENTIÈRE sur les deux moitiés : le tiroir Narration la montrait deux fois
   et « sous-titres depuis la narration » la calait deux fois. La ponctuation
   est portée par les mots eux-mêmes (le backend rend `raw`+`punct`) ; les
   retours à la ligne, eux, sont perdus — c'est le prix de la convention, et
   c'est déjà celui que paie le découpage de sous-titre du bundle. */
function dzmCutText(c,ws){
  return (c.text!=null&&Array.isArray(c.words)&&ws.length!==c.words.length)
    ?ws.map(function(w){return String((w&&w.w)||"")}).join(" ").trim()
    :null}
/* Recolle à chaque clip les mots qui LUI appartiennent (POST
   /api/subtitles/from-narration → `aligned`, dont chaque mot dit son `clip`).
   PUR. Un clip qui porte DÉJÀ ses mots (les sous-titres s1) n'est pas
   touché : sa liste fait foi. */
function dzmWithWords(clips,aligned){
  var by={},any=!1;
  (aligned||[]).forEach(function(w){
    if(!w||w.clip==null)return;
    any=!0;
    (by[w.clip]=by[w.clip]||[]).push({w:String(w.w||""),
      start:Number(w.start)||0,end:Number(w.end)||0})});
  if(!any)return (clips||[]).slice();
  return (clips||[]).map(function(c){
    return (c&&c.id!=null&&by[c.id]&&!Array.isArray(c.words))
      ?Object.assign({},c,{words:by[c.id]}):c})}
/* Les mots PRÊTÉS par `dzmWithWords` ne sont utiles qu'à la coupe : une fois
   le texte réparti, les garder gonflerait la sauvegarde du projet d'une copie
   de toute la narration, mot par mot, sans que rien ne la relise (mesuré :
   `words` sur un clip a1 est inerte au rendu). On les retire des pistes qui
   ne sont PAS des sous-titres — s1, lui, possède les siens et les garde. */
function dzmDropWords(clips,keepTracks){
  var keep={};
  (keepTracks||[]).forEach(function(t){if(t!=null)keep[String(t)]=1});
  return (clips||[]).map(function(c){
    if(!c||!c.words||keep[c.tr]===1)return c;
    var d=Object.assign({},c);delete d.words;return d})}
function dzmRippleCut(clips,t0,t1,opts){
  var loop=(opts&&opts.loopTracks)||[],locked=(opts&&opts.locked)||{};
  /* `a` borné à zéro : la timeline ne commence pas avant. Sans ce Math.max,
     couper [−1, 1[ posait un clip à `start: -1` — invisible, et le backend
     n'en veut pas. `len` se recalcule APRÈS le bornage, sinon on retirerait
     du temps qui n'existe pas. */
  var a=Math.max(0,dzmR3(Math.min(t0,t1))),b=dzmR3(Math.max(t0,t1));
  var len=dzmR3(b-a),out=[];
  /* `len` non strictement positif (plage nulle, ou t0/t1 illisibles) : il n'y
     a RIEN à retirer, donc rien à fendre. Le montage sort intact. */
  if(!(len>0))return {clips:(clips||[]).slice(),removed:0};
  /* IDENTIFIANTS DÉJÀ PRIS. `_r` seul ne suffit pas : deux plages coupées
     dans LE MÊME clip — le geste « retirer les N euh », qui est le cas
     NOMINAL — donnaient N clips nommés `x_r`. MESURÉ : un clip n1 [0,10]
     avec des « euh » en [1,2] et [5,6] rendait ["n1","n1_r","n1_r"]. Le
     bundle sélectionne par identifiant (clips.find(c=>c.id===selId)), écrit
     par identifiant (map(k=>k.id===id?…:k)) et clé ses rangées dessus : deux
     homonymes s'éditent ENSEMBLE et se disputent la rangée. */
  /* Table NUE (`Object.create(null)`) : un objet litteral hérite
     d'Object.prototype, et `taken["__proto__"]=1` n'y crée alors AUCUNE
     entrée — le nom passerait pour libre. Table nue, le problème n'existe
     pas, et la vérité simple suffit.
     HONNÊTETÉ SUR LA PORTÉE : aucun banc ne peut distinguer les deux formes.
     MESURÉ — Object.prototype porte constructor, __defineGetter__,
     __defineSetter__, hasOwnProperty, __lookupGetter__, __lookupSetter__,
     isPrototypeOf, propertyIsEnumerable, toString, valueOf, __proto__,
     toLocaleString : PAS UN ne finit par `_r` ni `_r<n>`, et tout candidat
     produit ici finit ainsi. C'est donc une précaution de construction, pas
     un correctif mesuré ; elle est écrite parce qu'elle coûte un mot. */
  var taken=Object.create(null);
  (clips||[]).forEach(function(c){if(c&&c.id!=null)taken[String(c.id)]=1});
  function newId(id){
    var base=String(id)+"_r",n=base,i=2;
    while(taken[n])n=base+(i++);
    taken[n]=1;return n}
  (clips||[]).forEach(function(c){
    if(!c)return;
    if(locked[c.tr]){out.push(c);return}
    /* COERCION UNE FOIS POUR TOUTES. `dzmRipT` coerce déjà ses entrées ; les
       branches, elles, comparaient les bornes BRUTES et la fenêtre de source
       les lisait brutes aussi — un `start` illisible sortait donc en
       `srcIn: NaN`, qui traverse le payload et le rendu sans un mot. */
    var c0=Number(c.start)||0,c1=Number(c.end)||0;
    var ns=dzmRipT(c0,a,b,len),ne=dzmRipT(c1,a,b,len);
    if(loop.indexOf(c.tr)>=0){
      if(ne<=ns)return;                       /* entièrement dans la plage */
      if(ns===c.start&&ne===c.end){out.push(c);return}
      out.push(Object.assign({},c,{start:ns,end:ne}));return}
    if(c1<=a){out.push(c);return}
    if(c0>=b){out.push(Object.assign({},c,{start:ns,end:ne}));return}
    var sp=(typeof c.speed==="number"&&c.speed>0)?c.speed:1;
    var fendu=c0<a;
    if(fendu){
      /* `start:c0` et pas le brut : la moitié gauche est un clip que NOUS
         écrivons, elle ne doit pas reconduire un `start` illisible. Les
         clips que la coupe ne touche pas, eux, ressortent tels quels —
         rippleCut coupe, elle ne réécrit pas ce qu'on ne lui demande pas. */
      var g=Object.assign({},c,{start:c0,end:a});
      if(Array.isArray(c.words)){
        g.words=dzmCutWords(c.words,a,b,len,!0);
        var gt=dzmCutText(c,g.words);
        if(gt!==null)g.text=gt}
      out.push(g)}
    if(c1>b){
      var k=Object.assign({},c,{id:(fendu&&c.id)?newId(c.id):c.id,
        start:a,end:dzmR3(c1-len)});
      /* pas de source, pas de fenêtre de source : inventer un `srcIn` sur un
         clip qui n'en a jamais eu ferait mentir l'inspecteur. */
      if(c.srcIn!=null||c.src)k.srcIn=dzmR3((Number(c.srcIn)||0)+(b-c0)*sp);
      if(Array.isArray(c.words)){
        k.words=dzmCutWords(c.words,a,b,len,!1);
        var kt=dzmCutText(c,k.words);
        if(kt!==null)k.text=kt}
      out.push(k)}});
  return {clips:out,removed:len}}

/* ── composants (r/x du bundle — jamais touchés au chargement) ───────────── */

/* Les deux boutons de la barre de transport.
   P9 — LIBELLÉS RECTIFIÉS. Ils disaient « + vidéo » / « + audio » et ils
   ajoutent une PISTE, pas un clip : l'utilisateur les a lus comme « ajouter
   une vidéo », a cliqué, et a obtenu une bande vide. Le libellé lui donnait
   raison. Ils disent maintenant ce qu'ils font ; le bouton qui ajoute
   VRAIMENT une vidéo est « Bibliothèque… », juste à côté. */
var DzmTrackAdd=function(props){
  var ts=(props&&props.tracks&&props.tracks.length)?props.tracks:DZM_DEFAULT_TRACKS;
  function add(k){if(props&&props.onChange)props.onChange(dzmAdd(ts,k))}
  return r.jsxs("span",{className:"dzm-add",children:[
    r.jsx("button",{className:"svm-tbtn dzm-addb",
      title:"Ajouter une PISTE vidéo d'overlay (une bande vide) — posée tout "+
        "en haut, donc composée AU-DESSUS des autres au rendu. Pour poser un "+
        "clip, c'est « Bibliothèque… ».",
      "aria-label":"Ajouter une piste vidéo d'overlay",
      onClick:function(){add("video")},children:"+ piste vidéo"},"v"),
    r.jsx("button",{className:"svm-tbtn dzm-addb",
      title:"Ajouter une PISTE audio (une bande vide) — posée sous les pistes "+
        "audio existantes, au-dessus des sous-titres. Bus BRUITAGES, sauf si "+
        "l'identifiant libre est celui d'une piste historique retirée (A1, "+
        "A2) : elle revient alors avec son bus d'origine et son habillage.",
      "aria-label":"Ajouter une piste audio",
      onClick:function(){add("audio")},children:"+ piste audio"},"a")]})};

/* ── P9 : le bouton « Bibliothèque… » de la barre de transport ─────────────
   MESURE qui le fonde : `openPicker` n'était appelé QU'À UN endroit du
   bundle — le petit « + » de l'en-tête d'une piste, 14 px, révélé au survol
   de cette piste-là. Rien, dans la barre de transport, ne proposait
   d'ajouter un clip. « il me faut aussi un bouton pour ajouter une video
   depuis la bibliotheque » : le voici, et il porte le mot de l'utilisateur.

   La piste visée est RÉSOLUE, jamais devinée : la première piste vidéo du
   projet dans l'ordre d'affichage. Sans piste vidéo, le bouton ne s'éteint
   pas — il DIT pourquoi il ne peut rien faire et nomme la sortie. Un bouton
   grisé sans explication oblige à deviner, et c'est le défaut que toute
   cette tâche répare. */
var DzmLibBtn=function(props){
  var ts=(props&&props.tracks&&props.tracks.length)?props.tracks:DZM_DEFAULT_TRACKS;
  var id=dzmPickTrack(ts,"video");
  return r.jsx("button",{className:"svm-tbtn dzm-libb",
    title:id?("Ouvrir la Bibliothèque et poser une vidéo, une image ou un "+
        "rendu sur la piste "+id.toUpperCase()+", à la tête de lecture — "+
        "c'est la piste vidéo la plus haute du projet.")
      :("Aucune piste vidéo dans ce projet : rien ne pourrait recevoir le "+
        "clip. « + piste vidéo » en crée une."),
    "aria-label":"Ouvrir la Bibliothèque pour ajouter un clip",
    onClick:function(){
      if(!id){if(props&&props.note)props.note("Aucune piste vidéo dans ce "+
        "projet — « + piste vidéo » en crée une, puis « Bibliothèque… » y "+
        "posera le clip.");return}
      if(props&&props.onPick)props.onPick(id)},
    children:"Bibliothèque…"},"lib")};

/* ── P9 : le marquage d'un clip V1 qui n'est pas une vidéo ─────────────────
   GET /api/montage/project rend `v1_non_video` — des identifiants de clips,
   joignables aux `clips` servis par la même réponse (contrat arrêté par P8).
   Sans lecteur, ce champ était un mensonge poli : le backend savait, l'écran
   se taisait, et POST /render refusait en 400 APRÈS le clic.

   La chip est un BOUTON, pas une étiquette : la voie de sortie est offerte
   sur place — elle rouvre la Bibliothèque sur la piste du clip — au lieu
   d'être devinée. `stopPropagation` sur pointerdown ET sur click : sans le
   premier, le clic amorcerait le déplacement du clip sous la chip.

   CE QUE LA CHIP DIT EST MESURÉ, ET LE BRIEF DE LA TÂCHE LE DISAIT TROP
   FORT. « POST /render refuse déjà ces clips en 400 en les nommant » n'est
   vrai que pour une PARTIE d'entre eux. Relu le 04/09/2026 dans
   montage_service.py : `v1_non_video` liste les clips V1 dont l'extension
   n'est pas dans `_VIDEO_EXTS` (6 extensions), tandis que le pré-vol de
   `POST /render` refuse ce que `_ffmpeg_ouvrira` rejette, c'est-à-dire hors
   de `_VIDEO_EXTS + _IMAGE_EXTS + _AUDIO_EXTS` — et `_IMAGE_EXTS` contient
   `.png` (l. 1488). Une planche de sprites PNG posée en V1 est donc SIGNALÉE
   ici et PASSE le pré-vol : elle se rend en carton fixe. Un maillage `.glb`,
   lui, est signalé ET refusé. La chip dit les deux cas ; promettre un refus
   qui n'arrive pas aurait été le même défaut, à l'envers. */
function dzmBadSrcChip(c,onFix){
  return r.jsx("button",{className:"dzm-badsrc",
    title:"Ce plan n'est pas une vidéo : son fichier ne porte pas "+
      "d'extension vidéo (planche de sprites, maillage 3D, archive…). Un "+
      "maillage ou une archive fera échouer le rendu, qui les nommera ; une "+
      "image passera le contrôle mais se rendra en carton fixe. Cliquez "+
      "pour rouvrir la Bibliothèque et poser un vrai rendu à sa place, puis "+
      "retirez celui-ci.",
    "aria-label":"Plan qui n'est pas une vidéo — ouvrir la Bibliothèque",
    onPointerDown:function(e){if(e&&e.stopPropagation)e.stopPropagation()},
    onClick:function(e){
      if(e&&e.stopPropagation)e.stopPropagation();
      if(onFix)onFix(c)},
    children:"pas une vidéo"},"badsrc")}

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

/* ── P3 : le tiroir « Texte » ──────────────────────────────────────────────
   Monter en lisant, pas en regardant des rectangles : la narration s'affiche
   MOT PAR MOT, les remplissages sont marqués, et couper des mots coupe le
   temps qu'ils occupent — sur toutes les pistes à la fois.

   OÙ IL VIT, et pourquoi ce n'est pas là où le plan l'imaginait : le plan
   visait une ancre de la zone des tiroirs qui, mesurée le 04/09/2026 sur le
   bundle livré, n'y apparaît PAS UNE FOIS. Son repli, dans la COLONNE
   D'INSPECTION, vaut exactement 1 : c'est celui-là. D'où la forme — un
   panneau empilé sous les inspecteurs, pas un tiroir pleine largeur. C'est
   plus étroit que ce que le plan décrivait ; c'est la place que le bundle
   offre sans toucher à un bloc amont.

   AUCUN de ces deux noms n'est écrit ici, et c'est délibéré : cette couche
   est INJECTÉE dans le bundle, donc un identifiant cité dans un de ses
   commentaires s'y compte une fois de plus. Mesuré deux fois — la première
   a fait abandonner le patcher (l'ancre retenue passait à 2), la seconde a
   remis dans le bundle un jeton qui n'y était pas. Les deux noms, eux, sont
   écrits en clair dans scripts/patch_bundle_montage.py (A_M12) et dans
   /shared/montage.css, qui ne sont pas injectés.

   LES MOTS viennent de POST /api/subtitles/from-narration (calage gratuit et
   hors ligne du texte déjà écrit), les remplissages de POST
   /api/subtitles/fillers. Rien n'est chargé tant que le panneau est fermé,
   et FERMER OUBLIE : les mots sont calés sur les clips d'A1, qu'un
   déplacement pendant la fermeture périmerait tous.

   LA COUPE EST RÉVERSIBLE : l'appelant pousse l'historique AVANT (voir M12).
   « Annuler » ramène les CLIPS et le mixage — c'est tout ce que
   `pushHistory` mémorise dans ce bundle. `proj.dur`, raccourci d'autant, ne
   revient PAS tout seul : c'est dit dans la note de chaque coupe. */
var DzmTextDrawer=function(props){
  var open=!!(props&&props.open);
  var sd=x.useState(null),data=sd[0],setData=sd[1];
  var sb=x.useState(0),busy=sb[0],setBusy=sb[1];
  var se=x.useState(""),err=se[0],setErr=se[1];
  var ss=x.useState(null),sel=ss[0],setSel=ss[1];
  var dragRef=x.useRef(!1),loadRef=x.useRef(0);
  var clipsRef=x.useRef(null);clipsRef.current=(props&&props.clips)||[];
  function note(m){if(props&&props.note)props.note(m)}

  x.useEffect(function(){
    if(open)return;
    loadRef.current=0;setData(null);setSel(null);setErr("")},[open]);

  /* le glisser peut se relâcher HORS des boutons (sur la marge, hors de la
     fenêtre) : sans cet écouteur, la sélection continuerait de suivre la
     souris au survol suivant, sans qu'aucun bouton ne soit enfoncé. */
  x.useEffect(function(){
    if(!open)return;
    function up(){dragRef.current=!1}
    window.addEventListener("mouseup",up);
    return function(){window.removeEventListener("mouseup",up)}},[open]);

  x.useEffect(function(){
    if(!open||loadRef.current)return;
    loadRef.current=1;
    var alive=!0;setBusy(1);setErr("");
    function post(u,b){
      return fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify(b)}).then(function(rp){
        return rp.json().then(function(d){
          if(!rp.ok)throw new Error((d&&d.detail)||("HTTP "+rp.status));
          return d})})}
    post("/api/subtitles/from-narration",{clips:clipsRef.current}).then(function(d){
      /* `aligned` (et pas `segments`) : c'est la seule forme qui dise de
         QUEL CLIP vient chaque mot — ce dont dzmWithWords a besoin pour que
         la coupe répartisse le texte d'un bloc fendu. `raw`+`punct` restitue
         le mot tel qu'il est écrit, accents et ponctuation compris. */
      var ws=((d&&d.aligned)||[]).map(function(w,i){
        return {i:i,w:String(w.raw||w.w||"")+String(w.punct||""),
          start:w.start,end:w.end,clip:w.clip}});
      if(!ws.length)throw new Error("Aucun mot calé sur la narration.");
      return post("/api/subtitles/fillers",{words:ws}).then(function(fd){
        if(!alive)return;
        setBusy(0);setData({words:ws,spans:(fd&&fd.spans)||[]})})})
      .catch(function(e){
        if(alive){setBusy(0);
          setErr((e&&e.message)||"échec de la requête")}});
    return function(){alive=!1}},[open,data]);

  function cut(ranges){
    var rg=(ranges||[]).filter(function(p){
      return p&&p[1]>p[0]});
    if(!rg.length){note("Rien à couper : la sélection est vide.");return}
    if(!props.onCut){note("Texte : rien pour recevoir la coupe.");return}
    /* les mots partent AVEC la coupe : c'est eux qui répartiront le texte
       d'un bloc de narration fendu entre ses deux moitiés. */
    props.onCut(rg,(data&&data.words)||[]);
    /* les temps de TOUS les mots suivants ont bougé : on relit plutôt que de
       les recaler ici — le calage est le métier du backend. */
    setSel(null);loadRef.current=0;setData(null)}

  if(!open)return null;
  var words=(data&&data.words)||[],spans=(data&&data.spans)||[];
  /* DEUX natures, et la distinction décide de ce qu'un bouton emporte SANS
     qu'on relise. « hesitation » : des non-mots (euh, hum, um, uh) — les
     retirer en bloc ne peut pas détruire une phrase. « tic » : des mots
     PLEINS qui servent de béquille (voilà, genre, well, right). MESURÉ le
     04/09/2026 sur une narration française SANS UNE SEULE hésitation : cinq
     plages de tic, six mots, dont « Voilà pourquoi… » et « quoi qu'on en
     dise » — quatre portent la phrase. Les tics sont donc MARQUÉS et ne se
     coupent qu'à la sélection ; seul le sac des hésitations part en bloc. */
  var hes=spans.filter(function(s){return s.kind==="hesitation"});
  var fill={};
  spans.forEach(function(s){(s.words||[]).forEach(function(i){
    fill[i]=s.kind||"tic"})});
  var i0=sel?Math.min(sel.a,sel.b):-1,i1=sel?Math.max(sel.a,sel.b):-2;
  var pick=words.slice(i0,i1+1).filter(function(w){
    return w.start!=null&&w.end!=null});
  var rgSel=pick.length?[Number(pick[0].start),
                         Number(pick[pick.length-1].end)]:null;
  /* les mots que le bouton en bloc emporte, NOMMÉS : « retirer les 3 euh »
     ne dit pas lesquels, et c'est précisément ce qu'il faut savoir avant de
     cliquer sur un geste qui coupe. */
  var hesMots=[];
  hes.forEach(function(s){(s.words||[]).forEach(function(i){
    var w=words[i];if(w&&w.w&&hesMots.indexOf(w.w)<0)hesMots.push(w.w)})});
  function selTo(i,ext){
    setSel(function(p){return (ext&&p)?{a:p.a,b:i}:{a:i,b:i}})}
  return r.jsxs("div",{className:"dzm-txt",children:[
    r.jsxs("div",{className:"dzm-txth",children:[
      r.jsx("span",{className:"dzm-txtt",children:"Texte"},"t"),
      r.jsx("span",{className:"dzm-txtn",children:
        busy?"…":(words.length?words.length+" mots":"")},"n")]},"h"),
    err?r.jsx("div",{className:"dzm-txterr",children:err},"e"):null,
    words.length?r.jsx("div",{className:"dzm-txtw",children:
      words.map(function(w,i){
        var on=i>=i0&&i<=i1;
        return r.jsx("button",{className:"dzm-txtb",
          "data-filler":fill[i]||void 0,"data-on":on?"":void 0,
          "aria-pressed":!!on,
          title:(fill[i]==="hesitation"?"Hésitation — ":
                 fill[i]==="tic"?"Mot béquille (mot plein : à couper à la "+
                   "main, jamais en bloc) — ":"")+
            (w.start!=null?Number(w.start).toFixed(2)+" s":"sans temps")+
            " · cliquer, Maj+clic ou glisser pour étendre la sélection",
          onMouseDown:function(e){dragRef.current=!0;selTo(i,e&&e.shiftKey)},
          onMouseEnter:function(){
            if(dragRef.current)setSel(function(p){
              return {a:p?p.a:i,b:i}})},
          onMouseUp:function(){dragRef.current=!1},
          /* CLAVIER. Un <button> activé à Entrée ou Espace émet un `click`,
             JAMAIS un `mousedown` : sans cette ligne, les boutons portaient
             `aria-pressed`, étaient tous dans l'ordre de tabulation, et ne
             faisaient rien. Sans risque pour le glisser — un `mousedown` et
             un `mouseup` sur DEUX boutons différents font remonter le
             `click` à leur ancêtre commun, pas au bouton. */
          onClick:function(e){selTo(i,e&&e.shiftKey)},
          children:w.w},String(i))})},"w"):null,
    r.jsxs("div",{className:"dzm-txta",children:[
      r.jsx("button",{className:"svm-tbtn dzm-txtbtn",disabled:!rgSel,
        title:rgSel
          ?("Couper de "+rgSel[0].toFixed(2)+" s à "+rgSel[1].toFixed(2)+
            " s sur toutes les pistes non verrouillées : ce qui suit remonte. "+
            "Annuler défait la coupe entièrement. La durée du projet ne bouge "+
            "pas : la fin de la timeline est maintenant vide, raccourcissez-la "+
            "si vous voulez.")
          :"Sélectionnez des mots (clic, Maj+clic, ou clic-glissé du premier "+
           "au dernier)",
        onClick:function(){cut([rgSel])},
        children:"couper la sélection"},"c"),
      r.jsx("button",{className:"svm-tbtn dzm-txtbtn",disabled:!hes.length,
        title:hes.length
          ?("Retirer "+hesMots.map(function(m){return "« "+m+" »"}).join(", ")+
            " — "+hes.length+" plage"+(hes.length>1?"s":"")+", de la fin vers "+
            "le début pour que les précédentes ne se décalent pas. Seules les "+
            "HÉSITATIONS partent ainsi ; les mots béquille soulignés se "+
            "coupent à la sélection, un par un. Annuler défait la coupe "+
            "entièrement. La durée du projet ne bouge pas : la fin de la "+
            "timeline est maintenant vide, raccourcissez-la si vous voulez.")
          :(spans.length
            ?"Aucune hésitation. Les "+spans.length+" mot"+
             (spans.length>1?"s":"")+" souligné"+(spans.length>1?"s":"")+
             " sont des mots PLEINS : à couper à la sélection, en les lisant."
            :"Aucun mot de remplissage repéré dans cette narration"),
        onClick:function(){cut(hes.map(function(s){
          return [s.start,s.end]}))},
        children:hes.length?("retirer les "+hes.length+" « euh »")
          :"aucun « euh »"},"f")]},"a")]})};

/* ── P4 : « appliquer cet étalonnage à tous les plans de la piste » ─────
   Les quatre curseurs (exposition, contraste, saturation, température) sont
   servis par le CATALOGUE du backend — effects_engine._CATALOG["grade_basic"]
   et ses bornes : le rack VFX dessine les curseurs et la vignette d'aperçu
   sans une ligne de plus ici. Ce qui manquait est le geste GLOBAL : un
   étalonnage réglé sur un plan, recopié sur tous les autres.

   dzmGradeAll est PURE — c'est la moitié du cœur exécutée sous node par
   backend/tests/test_montage_bundle.py.

   TROIS RÈGLES, et chacune répare un cas qui mordait :
   [a] les bornes de TEMPS ne se recopient pas (t0/t1 et leurs rampes). Elles
       sont en secondes LOCALES au clip : un étalonnage limité à [1 s ; 2 s]
       sur un plan de 8 s, recopié sur un plan de 1,2 s, y couvrirait presque
       tout. « Cet étalonnage » veut dire les quatre valeurs, sur le plan
       entier — et le bouton le DIT.
   [b] chaque plan reçoit sa PROPRE copie de l'effet. Partager un seul objet
       entre vingt clips ferait de tout réglage ultérieur sur l'un un réglage
       sur les vingt, sans que rien ne le montre.
   [c] un plan qui porte DÉJÀ exactement le même étalonnage n'est pas
       réécrit : il ne compte pas dans le lot, et sa ligne ne bouge pas.
   [d] la piste visée est CELLE DU PLAN SÉLECTIONNÉ, pas « v1 » en dur — voir
       le commentaire de dzmGradeAllBtn, qui porte la mesure.

   UN CAS DE BORD, MESURÉ ET ASSUMÉ : si un plan cible porte DEUX `grade_basic`
   empilés, seul le PREMIER est remplacé et le second survit — l'étalonnage
   « recopié » se compose alors avec un étalonnage étranger. Les retirer
   d'office serait détruire des effets posés à la main que ce bouton n'a
   jamais promis de toucher ; le geste ne remplace donc que la ligne que
   `dzmGradeOf` désigne, ici comme sur la source. Épinglé par
   `js_grade_ne_remplace_que_le_premier` de test_montage_bundle.py. */
var DZM_GRADE_TIMING=["t0","t1","fade_in","fade_out","ease_in","ease_out"];

/* le premier `grade_basic` de la pile d'un clip, ou null */
function dzmGradeOf(clip){
  var es=(clip&&clip.effects)||[];
  for(var i=0;i<es.length;i++)
    if(es[i]&&es[i].type==="grade_basic")return es[i];
  return null}

/* copie SANS les bornes de temps — voir [a] */
function dzmGradeCopy(eff){
  var o={};
  Object.keys(eff||{}).forEach(function(k){
    if(DZM_GRADE_TIMING.indexOf(k)<0)o[k]=eff[k]});
  o.type="grade_basic";
  return o}

/* empreinte stable d'un effet : clés triées, valeurs sérialisées. Sert à ne
   pas réécrire un plan déjà identique — voir [c]. Comparée SANS rien retirer,
   donc un étalonnage borné dans le temps DIFFÈRE de la copie pleine longueur
   et sera bien remplacé. */
function dzmEffKey(eff){
  var o=eff||{},s="";
  Object.keys(o).sort().forEach(function(k){
    s+=k+"="+JSON.stringify(o[k])+";"});
  return s}

/* PURE. Rend {clips, applied, replaced, targets} :
   `targets`  = plans de la piste visée, réels (avec `src`), hors la source ;
   `applied`  = ceux qui ont VRAIMENT changé ;
   `replaced` = ceux dont un `grade_basic` existant a été écrasé. */
function dzmGradeAll(clips,srcId,trackId){
  var cs=clips||[],tr=trackId||"v1",src=null;
  for(var i=0;i<cs.length;i++)
    if(cs[i]&&cs[i].id===srcId){src=cs[i];break}
  var g=src?dzmGradeOf(src):null;
  if(!g)return {clips:cs,applied:0,replaced:0,targets:0};
  var key=dzmEffKey(dzmGradeCopy(g)),applied=0,replaced=0,targets=0;
  var out=cs.map(function(c){
    if(!c||c.id===srcId||c.tr!==tr||!c.src)return c;
    targets++;
    var st=(c.effects||[]).slice(),at=-1;
    for(var j=0;j<st.length;j++)
      if(st[j]&&st[j].type==="grade_basic"){at=j;break}
    if(at>=0&&dzmEffKey(st[at])===key)return c;      /* [c] déjà à jour */
    var cp=dzmGradeCopy(g);                          /* [b] une copie par plan */
    if(at>=0){st[at]=cp;replaced++}else st.push(cp);
    applied++;
    return Object.assign({},c,{effects:st})});
  return {clips:out,applied:applied,replaced:replaced,targets:targets}}

/* Le bouton, posé sous la pile d'effets de l'inspecteur (section M13). Rend
   NULL tant que le plan sélectionné ne porte pas d'étalonnage : il n'y a rien
   à propager, et un bouton mort en permanence apprend moins qu'un bouton
   absent.

   LA PISTE VISÉE EST CELLE DU PLAN SÉLECTIONNÉ. Une première version codait
   « v1 » EN DUR aux deux appels. MESURÉ sous node, plan V2 étalonné
   sélectionné : le bouton s'affichait ACTIF, écrasait l'étalonnage des deux
   plans V1 ([cibles, appliqués, remplacés] = [2, 2, 2]) — une piste que
   l'utilisateur n'éditait pas — et ne touchait pas un seul clip de la piste
   où il travaillait. La pile d'effets est offerte à TOUTE piste de genre
   vidéo (le bundle : `trackKind(sel.tr)==="video"`), donc un clip V2 peut
   parfaitement porter un `grade_basic` : le cas n'a rien d'exotique.
   `dzmGradeAll` prenait déjà la piste en argument ; c'est l'appelant qui
   mentait. Épinglé par `js_grade_source_v2_ne_touche_pas_v1` et
   `js_bouton_suit_la_piste_du_plan`.

   POURQUOI PAS « V1 SEULEMENT, BOUTON CACHÉ AILLEURS » — l'autre voie, qui se
   défendait. MESURE, backend : `montage_service.py` n'appelle `build_chain`
   QU'UNE fois, dans la boucle des segments V1 ; le dictionnaire construit
   pour chaque overlay V2 ne porte même pas de clé `effects`. Un étalonnage
   posé sur V2 ne rend donc NULLE PART. Mais cette lacune est ANTÉRIEURE à ce
   bouton et vaut pour l'effet posé à la main comme pour celui qu'il recopie :
   la cacher derrière un bouton absent ne l'aurait pas réparée, elle l'aurait
   rendue muette, et le jour où le rendu emportera les effets des overlays il
   aurait fallu défaire ce choix. Le bouton suit donc la piste ET LE DIT : sur
   toute piste autre que V1, son titre et sa note portent l'avertissement.

   GESTE DESTRUCTIF, DONC RÉVERSIBLE : l'historique est poussé AVANT toute
   écriture, UNE
   seule fois pour tout le lot. « Annuler » restaure les clips (donc la pile
   d'effets de CHAQUE plan telle qu'elle était, y compris les étalonnages
   écrasés) et le mixage — c'est tout ce que l'historique de cet écran
   mémorise, et c'est tout ce que ce geste touche : ni la durée du projet, ni
   les pistes, ni les sous-titres.
   RÉSERVE, la même que P2 portait : « annuler rend à chaque plan son
   étalonnage d'avant » est une DÉDUCTION de trois faits mesurés (un seul
   `pushHistory`, poussé avant l'écriture, sur un état que le geste ne mute
   pas) — mais RIEN NE L'EXERCE. `pushHistory` et `undo` sont des hooks du
   composant du bundle, hors de portée du shim node qui mesure ce cœur : la
   restauration elle-même n'est jouée par aucun banc.

   ÉCART AU PLAN, déclaré : le plan passait cinq arguments
   (sel, clips, setClips, pushHistory, fireNote). Il en faut SIX — `setDirty`.
   MESURÉ dans le bundle : l'autosave sort tout de suite si le projet est une
   démo OU si rien n'est marqué modifié (le drapeau `dirty`), et il ne se
   replanifie que sur [clips, proj, durMaster, ducking, dirty]. Le littéral de
   cette garde n'est PAS recopié ici : la couche est injectée dans le bundle,
   et une ligne citée mot pour mot s'y compterait une fois de plus — c'est
   ainsi qu'une ancre de M12 avait fait abandonner le patcher au rejeu
   suivant. Sans `setDirty(!0)`, un lot appliqué juste après une
   sauvegarde réussie ne partait JAMAIS au serveur et « NON ENREGISTRÉ »
   restait éteint : le travail se perdait au rechargement, en silence. */
function dzmGradeAllBtn(sel,clips,setClips,pushHistory,setDirty,note){
  if(!dzmGradeOf(sel))return null;
  var tr=(sel&&sel.tr)||"v1",TR=String(tr).toUpperCase();
  var pv=dzmGradeAll(clips,sel&&sel.id,tr);
  var dead=!pv.applied;
  /* Hors V1 : mesuré côté backend, le rendu n'emporte pas les effets des
     overlays. Le dire dans le titre ET dans la note — un lot appliqué en
     silence sur vingt plans qui ne rendront rien est pire qu'un lot refusé. */
  var hors=tr==="v1"?"":(" ATTENTION — mesuré : le rendu n'emporte pas les "+
    "effets des pistes d'overlay. Sur "+TR+", cet étalonnage se verra dans "+
    "l'inspecteur et dans l'aperçu, pas dans la vidéo exportée.");
  var t=pv.targets
    ?(pv.applied
      ?("Recopier l'exposition, le contraste, la saturation et la "+
        "température de ce plan sur "+pv.applied+" autre"+
        (pv.applied>1?"s":"")+" plan"+(pv.applied>1?"s":"")+" "+TR+
        (pv.replaced?(", dont "+pv.replaced+" dont l'étalonnage actuel sera "+
                      "REMPLACÉ"):"")+". Les bornes de temps de l'effet ne "+
        "sont pas recopiées : l'étalonnage porte sur le plan entier. Annuler "+
        "restaure l'étalonnage de chaque plan tel qu'il était."+hors)
      :(pv.targets>1
        ?("Les "+pv.targets+" autres plans "+TR+" portent déjà exactement "+
          "cet étalonnage.")
        :("Le seul autre plan "+TR+" porte déjà exactement cet étalonnage.")))
    :("Aucun autre plan "+TR+" : rien à étalonner ailleurs.");
  var lbl="étalonnage → tous les plans "+TR;
  /* aria-label = le texte VISIBLE, puis l'état. Un aria-label FIGÉ masquait la
     seule phrase qui dit pourquoi le bouton est éteint : quand il existe, les
     lecteurs d'écran n'annoncent plus le `title`. Le libellé visible en reste
     le PRÉFIXE (WCAG « Label in Name ») : la commande vocale marche encore. */
  return r.jsx("button",{className:"svm-tbtn dzm-gall",disabled:dead,
    title:t,"aria-label":lbl+" — "+t,
    onClick:function(){
      if(dead)return;
      var res=dzmGradeAll(clips,sel&&sel.id,tr);
      if(!res.applied)return;
      if(pushHistory)pushHistory();
      if(setClips)setClips(res.clips);
      if(setDirty)setDirty(!0);
      if(note)note("Étalonnage appliqué à "+res.applied+" plan"+
        (res.applied>1?"s":"")+" "+TR+
        (res.replaced?(" (dont "+res.replaced+" dont l'étalonnage a été "+
                       "remplacé)"):"")+
        ". Les bornes de temps ne sont pas recopiées. Annuler restaure "+
        "l'étalonnage de chaque plan tel qu'il était."+hors)},
    children:lbl},"dzmgall")}

/* ── P5 : les PROJETS NOMMÉS ───────────────────────────────────────────────
   Jusqu'ici le Montage n'avait qu'UNE timeline sur le disque. Ouvrir un autre
   montage voulait dire écraser celle-là, et rien ne la rendait. Le popover
   « projets » nomme le courant, liste les autres, les ouvre, les duplique,
   les renomme et les supprime. TOUTES les écritures sont faites par le
   SERVEUR (routes /api/montage/projects*) : cette couche n'est que la main,
   elle ne décide de rien sur le disque.

   DEUX GESTES DESTRUCTIFS, et les deux ARMENT avant de frapper — un premier
   clic pose `data-arm` et change le libellé, le second seulement agit. Pas
   de modale : cet écran n'en a aucune, et une boîte système gèle la page
   entière (donc l'autosave) le temps qu'on lise.
     * OUVRIR remplace la timeline courante. Ce qu'elle portait n'est copié
       nulle part : si elle n'avait pas de nom, elle est PERDUE. « Annuler »
       ne la rend pas — l'historique de cet écran ne mémorise que
       {clips, mixDb}, et l'application d'un projet le remet à zéro.
     * SUPPRIMER retire le fichier du projet, définitivement. Rien ne le
       rejoue, ni ici ni côté serveur.
   OUVRIR appelle `onBefore` AVANT la requête, et c'est l'éditeur qui y annule
   son autosave en vol. Sans cela, une sauvegarde partie 1,4 s plus tôt
   arrivait APRÈS l'ouverture et réécrivait le courant avec le montage qu'on
   venait de quitter — la course exacte que le bouton « bibliothèque » du
   bundle désamorce déjà, de la même façon et pour la même raison. SUPPRIMER,
   lui, ne l'appelle PAS : le serveur ferme cette course-là à lui seul, et
   l'annulation était une perte sèche. Le détail est dans `doDel`.

   LA DATE EST AFFICHÉE TELLE QU'ELLE EST STOCKÉE (UTC), jamais convertie.
   `toLocaleString` rendrait une chaîne différente selon le fuseau de la
   machine : le cœur cesserait d'être mesurable sous node, et une mesure qui
   dépend de l'endroit où on la prend n'en est pas une. Le suffixe « UTC » le
   dit plutôt que de le taire. */

/* PURES toutes les deux — c'est la part de P5 que node exécute.
   `secs` (P6) : la SECONDE en plus, pour les seuls appelants qui doivent
   distinguer deux lignes homonymes. Un second analyseur d'ISO à côté de
   celui-ci aurait été une règle de plus à tenir en phase ; l'argument
   optionnel garde UN seul analyseur et laisse les appelants de P5
   inchangés, sortie comprise. */
function dzmProjWhen(iso,secs){
  var m=/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/
    .exec(String(iso||""));
  if(!m)return "";
  return m[3]+"/"+m[2]+" "+m[4]+":"+m[5]+((secs&&m[6])?(":"+m[6]):"")+" UTC"}

/* La ligne sous le nom d'un projet. Ce qui décide entre deux montages, c'est
   le NOMBRE de plans et la date — jamais l'identifiant, qui n'apprend rien. */
function dzmProjLine(p){
  var o=p||{},n=Number(o.clips)||0,out=[n+" clip"+(n>1?"s":"")];
  if(o.ratio)out.push(String(o.ratio));
  var d=Number(o.duration)||0;
  if(d>0)out.push(d.toFixed(1).replace(".",",")+" s");
  var w=dzmProjWhen(o.updated_at);
  if(w)out.push(w);
  return out.join(" · ")}

var DzmProjects=function(props){
  var so=x.useState(!1),op=so[0],setOp=so[1];
  var sl=x.useState(null),list=sl[0],setList=sl[1];
  var sb=x.useState(0),busy=sb[0],setBusy=sb[1];
  var se=x.useState(""),err=se[0],setErr=se[1];
  var sa=x.useState(""),arm=sa[0],setArm=sa[1];
  var sr=x.useState(null),ren=sr[0],setRen=sr[1];
  var sn=x.useState(""),nv=sn[0],setNv=sn[1];
  var box=x.useRef(null);
  var pid=(props&&props.projectId)||"";
  var nm=(props&&props.name)||"montage";
  function note(m){if(props&&props.note)props.note(m)}

  /* l'armement retombe tout seul au bout de quatre secondes : un bouton
     resté rouge finit par être cliqué pour autre chose. Même délai que le ×
     d'en-tête de piste, pour que les deux s'apprennent ensemble. */
  x.useEffect(function(){
    if(!arm)return;
    var h=setTimeout(function(){setArm("")},4000);
    return function(){clearTimeout(h)}},[arm]);

  /* Échap ferme, un clic dehors ferme. Un popover qu'on ne peut refermer
     qu'en retrouvant son bouton est un piège, et il masque la timeline. */
  x.useEffect(function(){
    if(!op)return;
    function key(e){if(e.key==="Escape"){setOp(!1);setArm("")}}
    function down(e){
      if(box.current&&!box.current.contains(e.target)){setOp(!1);setArm("")}}
    window.addEventListener("keydown",key);
    window.addEventListener("mousedown",down);
    return function(){window.removeEventListener("keydown",key);
      window.removeEventListener("mousedown",down)}},[op]);

  function req(url,opt){
    return fetch(url,opt||{}).then(function(rp){
      return rp.json().catch(function(){return {}}).then(function(d){
        if(!rp.ok)throw new Error((d&&d.detail)||("HTTP "+rp.status));
        return d})})}
  function send(url,method,body){
    return req(url,{method:method,headers:{"Content-Type":"application/json"},
      body:JSON.stringify(body||{})})}
  function url(p){return "/api/montage/projects/"+encodeURIComponent(p)}
  function fail(e){setBusy(0);setErr((e&&e.message)||"requête impossible")}

  function load(){
    setBusy(1);setErr("");
    return req("/api/montage/projects").then(function(d){
      setBusy(0);setList((d&&d.projects)||[])})
      .catch(function(e){setList([]);fail(e)})}

  function toggle(){
    var nx=!op;setOp(nx);setArm("");setRen(null);
    if(nx)load()}

  function saveAs(){
    if(busy)return;
    setBusy(1);setErr("");
    /* LA TIMELINE AFFICHEE PART AVEC LE NOM. Sans elle, le serveur ne
       connaissait que montage_saved.json, et DEUX etats courants n'en ont
       pas : une installation neuve (la Bibliotheque fournit la timeline,
       svmApplyProject pose setDirty(false), donc aucun autosave ne part) et
       l'instant qui suit le bouton « bibliotheque » (DELETE puis
       rechargement, exactement le meme etat). L'utilisateur regardait une
       timeline et ce popover lui repondait en rouge qu'il n'y en avait pas
       — HTTP 400, la porte d'entree de tout le lot fermee. Le reste du
       temps, le disque avait jusqu'a 1,5 s de retard sur l'ecran : MESURE,
       7 clips affiches, 1 clip ecrit, alors que le titre du bouton promet
       « le montage AFFICHE ». A defaut de cette prop, le serveur retombe sur
       le courant : la route se comporte exactement comme avant. */
    var tl=(props&&props.payload)?props.payload():null;
    send("/api/montage/projects","POST",
      {name:(nv||"").trim(),timeline:tl})
      .then(function(d){
        setBusy(0);setNv("");
        if(props.onNamed)props.onNamed(d.id,d.name);
        note("Montage enregistré sous « "+d.name+" ». Les modifications "+
          "suivantes y vont toutes seules, sans un geste de plus.");
        load()})
      .catch(fail)}

  function doOpen(p){
    if(busy)return;
    if(arm!=="o"+p.id){setArm("o"+p.id);return}
    setArm("");setBusy(1);setErr("");
    if(props.onBefore)props.onBefore();
    send(url(p.id)+"/open","POST")
      .then(function(){return req("/api/montage/project")})
      .then(function(d){
        setBusy(0);
        /* onNamed SEULEMENT si l'écran a vraiment appliqué. Rattacher le
           projet à une timeline restée l'ANCIENNE ferait écrire celle-ci
           dans le projet qu'on vient d'ouvrir, au premier autosave — le
           geste aurait détruit ce qu'il prétendait ouvrir. */
        if(props.onOpen&&props.onOpen(d)){
          if(props.onNamed)props.onNamed(p.id,p.name);
          setOp(!1);
          note("« "+p.name+" » ouvert. Le montage précédent a été remplacé : "+
            "s'il n'était pas enregistré sous un nom, il n'existe plus, et "+
            "« annuler » ne le rend pas.")}
        else
          /* le serveur refuse déjà d'ouvrir un projet sans plan vivant (409,
             et le courant reste intact) : il ne reste ici qu'une réponse que
             l'écran n'a pas su appliquer. Le taire ferait croire que rien ne
             s'est passé. */
          setErr("Réponse inattendue du serveur : rien n'a été appliqué. "+
            "Rechargez la page avant d'enregistrer.")})
      /* L'OUVERTURE A ECHOUE, et la liste est EXACTE : 409 « projet
         inouvrable », backend injoignable — les cas où la requête LÈVE. La
         timeline affichée n'a pas bougé et elle reste à enregistrer, or
         `onBefore` vient d'annuler l'autosave en vol et RIEN ne le
         replanifie (il ne touche que deux useRef et `setSaveInfo`, qui n'est
         pas dans les dépendances de l'effet). Le badge reste honnête, mais la
         sauvegarde que l'utilisateur croyait partie n'attendrait que sa
         prochaine édition. `onFail` la relance tout de suite.
         LA « RÉPONSE INAPPLICABLE » N'EST PAS ICI, et ce n'est pas un oubli :
         c'est le `else` du `.then` ci-dessus, il ne lève pas, donc ce `.catch`
         n'est jamais atteint et `onFail` n'est PAS appelé. Ce cas garde donc
         son autosave perdu — trou résiduel assumé, et le seul choix juste.
         Le serveur a DÉJÀ remplacé le courant par le projet ouvert ; seul
         l'écran n'a pas su appliquer la réponse. Relancer la sauvegarde y
         écrirait la timeline PÉRIMÉE par-dessus le courant tout neuf, et,
         `onNamed` n'ayant pas été appelé, elle la miroiterait dans l'ANCIEN
         projet — le geste défairait sur le disque l'ouverture qu'il vient de
         réussir, et il ferait exactement ce que le message affiché dit de ne
         pas faire (« Rechargez la page avant d'enregistrer »). Le trou est
         petit et il est dit à l'écran ; la réparation, elle, serait une
         corruption silencieuse.
         NON MESURE A L'ECRAN — dette navigateur, comme tout ce popover. */
      .catch(function(e){fail(e);if(props.onFail)props.onFail()})}

  function doDup(p){
    if(busy)return;
    setBusy(1);setErr("");
    send(url(p.id)+"/duplicate","POST").then(function(d){
      setBusy(0);
      note("Copie « "+d.name+" » créée. Le montage ouvert n'a pas changé.");
      load()})
      .catch(fail)}

  function doRen(p){
    if(busy)return;
    var v=(ren&&ren.id===p.id)?String(ren.v||""):"";
    setRen(null);setBusy(1);setErr("");
    send(url(p.id),"PATCH",{name:v}).then(function(d){
      setBusy(0);
      if(p.id===pid&&props.onNamed)props.onNamed(p.id,d.name);
      note(d.name===p.name
        ?("Nom inchangé : « "+d.name+" » — un champ vide garde l'ancien nom.")
        :("« "+p.name+" » renommé en « "+d.name+" »."));
      load()})
      .catch(fail)}

  function doDel(p){
    if(busy)return;
    if(arm!=="x"+p.id){setArm("x"+p.id);return}
    setArm("");setBusy(1);setErr("");
    /* PAS d'`onBefore` ICI, et c'est une correction du 04/09/2026 — mesurée,
       pas raisonnée. Le SERVEUR ferme cette course, à TROIS verrous, et c'est
       le TROISIÈME qui rend ce retrait légitime : POST /save ne retient
       `project_id` que s'il désigne un fichier qui EXISTE, il ne miroite que
       dans ce fichier-là — et, depuis le même commit, le triplet {test
       d'existence, écriture du courant, écriture du miroir} et la suppression
       passent sous un même verrou de module.
       LES DEUX PREMIERS NE SUFFISAIENT PAS, et c'est mesuré : entre le test
       d'existence et le miroir il y a deux sauts de thread, et un DELETE
       glissé là faisait REVENIR le fichier supprimé ET RESTER le lien du
       courant. Sans ce troisième verrou, retirer `onBefore` d'ici rouvrirait
       donc exactement « le courant reste lié à un projet supprimé ». La
       section [16] de test_montage_projets.py, qui joue l'entrelacement avec
       et sans le verrou, n'est donc pas une confirmation de ce retrait : elle
       en est la CONDITION. [10]
       (`supprime_l_autosave_ne_ressuscite_pas`) ne mesure, lui, que le cas
       SÉQUENTIEL — un autosave parti APRÈS que le DELETE a rendu la main.
       Annuler l'autosave ici était donc une PERTE SÈCHE : `onBefore` ne
       touche que deux useRef et `setSaveInfo(null)`, or `saveInfo` n'est pas
       dans les dépendances de l'effet d'autosave — supprimer un projet QUI
       N'EST PAS LE SIEN (`p.id!==pid`, donc pas d'`onNamed`, donc `proj`
       inchangé, donc aucune dépendance modifiée) annulait une sauvegarde en
       vol que plus rien ne replanifiait jusqu'à l'édition suivante.
       `svmDoSave` sort en silence sur AbortError : le badge reste honnête
       (`dirty` demeure vrai), mais l'utilisateur croyait sa sauvegarde
       partie. `doOpen`, lui, garde `onBefore` : là, le serveur NE PEUT PAS
       distinguer l'autosave du montage quitté de celui du montage ouvert. */
    req(url(p.id),{method:"DELETE"}).then(function(){
      setBusy(0);
      if(p.id===pid&&props.onNamed)props.onNamed("",nm);
      note("« "+p.name+" » supprimé — DÉFINITIVEMENT : le fichier est parti "+
        "du disque, ni « annuler » ni rien d'autre ne le rejoue."+
        (p.id===pid?" La timeline affichée, elle, reste : elle n'est simplement "+
          "plus rattachée à aucun projet.":""));
      load()})
      .catch(fail)}

  function row(p){
    var mine=p.id===pid,edit=!!(ren&&ren.id===p.id);
    var oArm=arm==="o"+p.id,xArm=arm==="x"+p.id;
    /* TOUS les boutons de la ligne s'éteignent pendant une requête. Tous les
       gestionnaires sortaient déjà sur `if(busy)return`, mais AUCUN bouton ne
       portait `disabled` (sauf « ouvrir », et seulement pour le projet déjà
       ouvert) : ils restaient cliquables et INERTES, sans le moindre retour.
       `load()` partant à chaque ouverture du popover, les tout premiers clics
       d'une ouverture tombaient précisément là. `.dzm-projbtn:disabled` (opacité
       .45, curseur normal) existe déjà dans la feuille depuis P5. */
    var off=!!busy;
    return r.jsxs("div",{className:"dzm-projrow","data-mine":mine?"":void 0,
      children:[
      r.jsxs("div",{className:"dzm-projid",children:[
        edit
          ?r.jsx("input",{className:"dzm-projin",value:ren.v,autoFocus:!0,
              "aria-label":"Nouveau nom du projet",
              onChange:function(e){setRen({id:p.id,v:e.target.value})},
              onKeyDown:function(e){
                if(e.key==="Enter")doRen(p);
                if(e.key==="Escape")setRen(null)}},"i")
          :r.jsx("span",{className:"dzm-projnm",title:p.name||"",
              children:(p.name||"sans nom")+(mine?" · ouvert":"")},"n"),
        r.jsx("span",{className:"dzm-projmeta",title:String(p.updated_at||""),
          children:dzmProjLine(p)},"m")]},"l"),
      r.jsxs("div",{className:"dzm-proja",children:[
        edit
          ?r.jsx("button",{className:"svm-tbtn dzm-projbtn",disabled:off,
              title:"Valider le nouveau nom (Entrée). Un champ vide garde "+
                "l'ancien nom.",
              onClick:function(){doRen(p)},children:"ok"},"ok")
          :r.jsx("button",{className:"svm-tbtn dzm-projbtn",disabled:off,
              title:"Renommer « "+(p.name||"")+" » — le montage lui-même "+
                "n'est pas touché",
              onClick:function(){setArm("");setRen({id:p.id,v:p.name||""})},
              children:"renommer"},"rn"),
        r.jsx("button",{className:"svm-tbtn dzm-projbtn",disabled:off,
          title:"Dupliquer « "+(p.name||"")+" » — une copie indépendante, "+
            "sous un nom suffixé « (copie) ». Rien d'autre ne bouge.",
          onClick:function(){doDup(p)},children:"dupliquer"},"dp"),
        r.jsx("button",{className:"svm-tbtn dzm-projbtn dzm-projop",
          "data-arm":oArm?"":void 0,disabled:mine||off,"aria-disabled":mine||off,
          title:mine
            ?"« "+(p.name||"")+" » est déjà le montage ouvert."
            :(oArm
              ?"Confirmer : OUVRIR « "+(p.name||"")+" » REMPLACE le montage "+
               "affiché. S'il n'est pas enregistré sous un nom, il est perdu "+
               "— « annuler » ne le rend pas."
              :"Ouvrir « "+(p.name||"")+" » — cela REMPLACE le montage "+
               "affiché (un second clic confirmera)"),
          onClick:function(){doOpen(p)},
          children:oArm?"remplacer ?":"ouvrir"},"op"),
        r.jsx("button",{className:"svm-tbtn dzm-projbtn dzm-projx",disabled:off,
          "data-arm":xArm?"":void 0,
          title:xArm
            ?"Confirmer : supprimer « "+(p.name||"")+" » DÉFINITIVEMENT. "+
             "Le fichier part du disque et rien ne le rejoue."
            :"Supprimer « "+(p.name||"")+" » du disque, définitivement "+
             "(un second clic confirmera)",
          "aria-label":"Supprimer "+(p.name||"ce projet"),
          onClick:function(){doDel(p)},
          children:xArm?"supprimer ?":"×"},"x")]},"a")]},p.id)}

  var rows=list||[];
  return r.jsxs("span",{className:"dzm-proj",ref:box,children:[
    r.jsx("button",{className:"svm-tbtn dzm-projb","data-on":op?"":void 0,
      "aria-expanded":op,"aria-haspopup":"dialog",
      title:pid
        ?("Projets — ce montage est enregistré sous « "+nm+" » et suit vos "+
          "modifications tout seul. La liste ouvre, duplique, renomme ou "+
          "supprime les autres.")
        :("Projets — ce montage n'a PAS de nom : il vit dans la timeline "+
          "courante, et le prochain projet ouvert l'écrasera sans retour. "+
          "« Enregistrer sous… » lui en donne un."),
      "aria-label":"Projets"+(pid?" — enregistré sous "+nm
                                 :" — ce montage n'a pas de nom"),
      onClick:toggle,children:"projets"},"b"),
    op?r.jsxs("div",{className:"dzm-projp",role:"dialog",
      "aria-label":"Projets de montage",children:[
      r.jsxs("div",{className:"dzm-projh",children:[
        r.jsx("span",{className:"dzm-projt",children:"Projets"},"t"),
        r.jsx("span",{className:"dzm-projn",children:
          busy?"…":(rows.length+" enregistré"+(rows.length>1?"s":""))},"n")]},"h"),
      r.jsxs("div",{className:"dzm-projsave",children:[
        r.jsx("input",{className:"dzm-projin",value:nv,
          placeholder:pid?nm:"nom du montage","aria-label":"Nom du projet",
          onChange:function(e){setNv(e.target.value)},
          onKeyDown:function(e){if(e.key==="Enter")saveAs()}},"i"),
        r.jsx("button",{className:"svm-tbtn dzm-projbtn",disabled:!!busy,
          title:"Enregistrer le montage AFFICHÉ comme un nouveau projet. "+
            "Rien n'est écrasé : c'est un fichier de plus, et c'est lui qui "+
            "recevra les modifications suivantes. Champ vide : le nom "+
            "courant est repris.",
          onClick:saveAs,children:"enregistrer sous…"},"s")]},"s"),
      err?r.jsx("div",{className:"dzm-projerr",children:err},"e"):null,
      rows.length
        ?r.jsx("div",{className:"dzm-projl",children:rows.map(row)},"l")
        :r.jsx("div",{className:"dzm-projvide",children:
          busy?"…":"Aucun projet enregistré. « Enregistrer sous… » crée le "+
            "premier ; jusque-là, le montage affiché est le seul, et ouvrir "+
            "un projet l'écraserait."},"v")]},"p"):null]})};

/* ── P6 : REMPLACER LA SOURCE D'UN PLAN, SANS PERDRE SON MONTAGE ───────────
   Le geste : l'utilisateur a régénéré un plan et veut échanger la SOURCE
   d'un clip. Tout le reste — début et fin sur la timeline, effets,
   transition, mixage, volume, texte — doit rester en place. C'est la
   différence entre « remplacer » et « supprimer puis reposer », qui perdait
   tout et que rien ne rendait.

   `dzmReplaceSrc` est PURE, et c'est ce que node exécute
   (backend/tests/test_montage_remplacer.py). Elle rend un clip NEUF :
   l'entrée n'est jamais mutée, sans quoi l'instantané que l'éditeur pousse
   dans son historique AVANT d'écrire serait déjà l'état d'après.

   LA FENÊTRE DE SOURCE, ET POURQUOI ELLE BOUGE. Un clip lit sa source de
   `srcIn` à `srcIn + (end - start) × vitesse` — c'est la formule que
   l'inspecteur affiche en « In / Out », et celle du rendu (à vitesse ×s le
   plan consomme s fois plus de source). Une source régénérée plus COURTE ne
   couvre plus cette fenêtre : trois cas, trois traitements, et chacun est
   DIT à l'écran.
     * elle couvre : rien ne bouge, aucun avertissement.
     * elle couvre la DURÉE mais pas depuis l'ancien point d'entrée : `srcIn`
       revient à 0. Le plan garde sa longueur, il ne montre plus le même
       morceau — c'est dit.
     * elle est plus courte que la durée consommée : `srcIn` revient à 0 ET
       la fin est ramenée. Le plan RACCOURCIT, la timeline garde un trou
       derrière lui (les clips suivants ne remontent pas : le ripple est un
       autre geste, et le faire ici sans le demander serait pire).
       CE QUE LE TROU DEVIENT AU RENDU dépend de la piste, et l'avertissement
       le dit piste par piste plutôt que d'en choisir une : sur V1, la piste
       de BASE, `_build_montage_command` pose un `color=c=black` de la durée
       du trou (montage_service.py, branche `s.get("gap")`) — noir à l'écran.
       Sur une piste d'overlay (V2 et au-delà), un clip est posé en
       `overlay … enable='between(t,st,en)'` : il s'arrête plus tôt, et c'est
       la piste du dessous qui réapparaît. « rendu en noir » y serait FAUX.
   DURÉE INCONNUE (0 ou absente) : on ne touche à RIEN et on le dit. Ce n'est
   pas un cas d'école — MESURE sur une copie de la base réelle (05/09/2026,
   lecture seule) : 53 des 97 jobs vidéo `done` non-montage ont `duration_s`
   NUL ou ≤ 0. Se taire laisserait un plan pointer dans le vide.
   CE CHIFFRE A ÉTÉ FAUX ICI AUSSI, et de la même façon qu'en base : il
   valait « 40 des 84 », mesuré sous `provider != 'montage'` — le défaut que
   la route corrige. Les 13 jobs `done` à `provider IS NULL` tombaient de la
   mesure comme de la requête : 84+13 = 97, 40+13 = 53.

   DEUX VOIES DE RETOUR, et il faut dire ce que chacune rend.
     1. « Annuler » (l'historique de l'écran) restaure {clips, mixDb} — donc
        le clip entier, source, bornes et effets compris. Il ne restaure NI
        la durée du projet NI les pistes : ce geste-ci n'y touche pas, mais
        la note le dit quand même, parce que c'est la limite de l'historique
        et qu'un utilisateur qui vient d'annuler autre chose la rencontrera.
     2. `src_history` — la source d'AVANT, empilée sur le clip, et rendue par
        « Revenir à la version précédente ». Elle porte AUSSI `srcIn` et
        `end` : sans eux, revenir en arrière aurait rendu l'ancienne source
        avec les bornes raccourcies et le point d'entrée perdu — un retour
        qui ne retourne pas. C'est un ÉCART assumé au plan, qui n'y mettait
        que {src, label, at}.
        Cette pile SURVIT à l'enregistrement : le serveur range les clips
        tels quels et la restauration les recopie de même — mesuré des deux
        côtés. Elle est plafonnée à 10 ; au-delà, les plus anciennes tombent.
   `srcOut` est RETIRÉ par le remplacement, et RENDU par le retour — les deux
   moitiés, parce que le champ est lu : `son-vfx-montage.js` affiche
   `sel.srcOut != null ? sel.srcOut : (sel.end - sel.start) × vitesse` dans
   la ligne « Out » de l'inspecteur. Le garder après un remplacement ferait
   donc mentir cette ligne (il décrit la fenêtre de l'ANCIENNE source) ; ne
   pas le rendre après un retour la ferait mentir dans l'AUTRE sens, en
   affichant une fin calculée là où l'utilisateur en avait posé une. Il est
   donc mémorisé dans `src_history` À CÔTÉ de `srcIn` et `end`, et seulement
   quand le clip le portait — une pile écrite par une version antérieure n'en
   a pas, et le retour n'invente rien. Le couple est ALORS un aller-retour
   exact, et le banc le mesure comme un TOUT (`ar_avant` / `ar_apres`) et non
   plus champ par champ : une clé ajoutée ou perdue par l'une des deux
   moitiés passait sous une liste de champs, elle ne passe pas sous une
   comparaison d'objets. Mesuré, un seul clip du dépôt porte `srcOut`
   aujourd'hui (la maquette de démonstration, qui n'a pas de source et sur
   laquelle le bouton n'apparaît donc jamais) ; la restauration d'une
   sauvegarde recopiant les clés inconnues, il pourrait revenir demain — et
   le backend, lui, ne le lit nulle part (mesuré : aucune occurrence dans
   backend/app). */
var DZM_HIST_MAX=10;
function dzmSrcLen(c){
  var o=c||{};
  return (Number(o.end)||0)-(Number(o.start)||0)}
function dzmSpeedNum(c){
  var s=c&&c.speed;
  return (typeof s==="number"&&s>0)?s:1}
function dzmReplaceSrc(c,src,label,srcDur,now){
  var o=c||{},len=dzmSrcLen(o),sp=dzmSpeedNum(o);
  var inn=Number(o.srcIn)||0,d=Number(srcDur)||0;
  var k=Object.assign({},o),warn="";
  var hi={src:o.src||null,label:o.label||null,srcIn:inn,
          end:Number(o.end)||0,at:now||Date.now()};
  /* la clé n'est ajoutée QUE si le clip la portait : sa seule présence dit
     au retour qu'il doit la rendre, son absence qu'il ne doit rien poser. */
  if("srcOut" in o)hi.srcOut=o.srcOut;
  k.src_history=((o.src_history&&o.src_history.length)?o.src_history:[])
    .concat([hi]).slice(-DZM_HIST_MAX);
  k.src=src;k.label=label||o.label;
  if("srcOut" in k)delete k.srcOut;
  if(d<=0){
    warn="Durée de la nouvelle source inconnue : les bornes du plan n'ont "+
      "pas pu être vérifiées — contrôlez sa fin."}
  else if(inn+len*sp>d+1e-3){
    k.srcIn=0;
    if(len*sp>d+1e-3){
      k.end=Math.round(((Number(o.start)||0)+d/sp)*1000)/1000;
      warn="La nouvelle source ne dure que "+d.toFixed(2)+" s : le plan a "+
        "été raccourci de "+len.toFixed(2)+" s à "+(d/sp).toFixed(2)+" s, "+
        "et la timeline garde un trou derrière lui"+
        (o.tr==="v1"
          ?", rendu en noir à l'export."
          :" — sur une piste d'overlay, c'est la piste du dessous qui "+
           "réapparaît.")}
    else warn="Point d'entrée ramené à 0 : la nouvelle source ("+
      d.toFixed(2)+" s) ne va pas assez loin pour l'ancien. Le plan garde "+
      "sa durée, il ne montre plus le même morceau."}
  return {clip:k,warn:warn,
    note:"Source de « "+(o.label||"ce plan")+" » remplacée par « "+
      (k.label||"")+" ». Bornes, effets, transition et mixage conservés."+
      (warn?" "+warn:"")+" Annuler restaure les clips et le mixage — pas la "+
      "durée du projet ni les pistes ; « Revenir à la version précédente » "+
      "rend aussi l'ancienne source."}}
function dzmRevertSrc(c){
  var o=c||{},h=(o.src_history&&o.src_history.length)?o.src_history:null;
  if(!h)return null;
  var last=h[h.length-1],k=Object.assign({},o),rest=h.slice(0,h.length-1);
  if(rest.length)k.src_history=rest;else delete k.src_history;
  k.src=last.src;k.label=last.label;
  /* les bornes d'ALORS, quand elles ont été mémorisées : une pile écrite par
     une version antérieure n'en porte pas, et inventer un 0 raccourcirait le
     plan au lieu de le rendre. */
  if(typeof last.srcIn==="number")k.srcIn=last.srcIn;
  if(typeof last.end==="number")k.end=last.end;
  /* `srcOut` : rendu SEULEMENT s'il a été mémorisé — le remplacement l'a
     retiré, et l'entrée dit s'il faut le remettre. Sans cette ligne
     l'aller-retour n'était pas l'identité, et la ligne « Out » de
     l'inspecteur changeait derrière un geste qui promet de tout rendre. */
  if("srcOut" in last)k.srcOut=last.srcOut;
  return {clip:k,
    note:"Source précédente rendue : « "+(last.label||"sans titre")+" », "+
      "avec son point d'entrée et sa fin d'alors."+
      (rest.length?(" "+rest.length+" version"+(rest.length>1?"s":"")+
        " plus ancienne"+(rest.length>1?"s":"")+" en mémoire."):
        " C'était la dernière en mémoire.")}}
/* Le bouton de l'inspecteur. Il n'apparaît QUE sur un clip qui A une source :
   la maquette de démonstration n'en pose aucune sur ses clips (mesuré), donc
   il est absent de la démo par construction — pas par une garde de plus. */
function dzmReplaceBtn(sel,onArm){
  if(!sel||!sel.src)return null;
  return r.jsx("button",{className:"svm-secbtn dzm-repl",
    title:"Échanger le fichier source de ce plan sans toucher au montage : "+
      "ses bornes sur la timeline, ses effets, sa transition et son mixage "+
      "restent en place. La Bibliothèque s'ouvre ; le clip que vous y "+
      "choisirez remplacera la source au lieu d'être ajouté.",
    "aria-label":"Remplacer la source de "+(sel.label||"ce plan"),
    onClick:function(){if(onArm)onArm()},
    children:"Remplacer la source…"},"dzmrepl")}
function dzmRevertBtn(sel,onRevert){
  var h=(sel&&sel.src_history&&sel.src_history.length)?sel.src_history:null;
  if(!h)return null;
  var last=h[h.length-1];
  return r.jsx("button",{className:"svm-secbtn dzm-revert",
    title:"Rendre à ce plan sa source précédente, « "+
      (last.label||"sans titre")+" », avec le point d'entrée et la fin "+
      "qu'il avait alors. "+h.length+" version"+(h.length>1?"s":"")+
      " en mémoire (10 au plus, les plus anciennes tombent).",
    "aria-label":"Revenir à la source précédente de "+(sel.label||"ce plan"),
    onClick:function(){if(onRevert)onRevert()},
    children:"Revenir à la version précédente"},"dzmrev")}
/* La ligne d'une proposition. PURE — c'est la part du rappel que node
   mesure ; le composant, lui, interroge le réseau.

   ELLE PORTE LA DATE ET LA DURÉE, et ce n'est pas de l'ornement : le TITRE
   est la clé même du rapprochement, donc tous les candidats le partagent PAR
   CONSTRUCTION. Une ligne réduite au titre rendait N boutons rigoureusement
   identiques — libellé et `aria-label` compris — et l'infobulle conseillait
   « vérifiez le titre », un conseil que la construction rendait impossible à
   suivre. MESURE sur une copie de la base réelle (05/09/2026) : trois
   groupes homonymes exploitables, « tweet_2026-05-20 » (7 jobs, plafond 5),
   « last launch 2 » (3), « backdoorpromo » (2) — soit jusqu'à cinq boutons
   jumeaux à l'écran.
   LA SECONDE EST AFFICHÉE. Toujours mesuré sur la même copie, deux jobs
   « backdoorpromo » sont terminés à 36 s d'intervalle (14:54:58 et
   14:55:34) : à la minute ils tombent encore dans deux minutes distinctes,
   mais rien ne le garantit — deux relances du même plan à vingt secondes
   d'écart auraient rendu la même chaîne. La seconde ferme ce cas ; deux
   rendus terminés dans la MÊME seconde resteraient indistinguables, et
   aucune ligne ne pourrait les distinguer.
   LA DURÉE est le second discriminant, et le seul qui dise à l'avance si le
   plan va être RACCOURCI. Elle est dite « inconnue » plutôt que tue quand
   elle manque : c'est le cas majoritaire en base (53 des 97), et c'est
   exactement l'avertissement que `replaceSrc` rendra. */
function dzmNewerLine(c){
  if(!c)return "";
  var o=c,bits=[],w=dzmProjWhen(o.completed_at,1),d=Number(o.duration_s)||0;
  if(w)bits.push(w);
  bits.push(d>0?(d.toFixed(1).replace(".",",")+" s"):"durée inconnue");
  return "Version plus récente : "+(o.title||o.job_id||"sans titre")+
    " · "+bits.join(" · ")+" — remplacer"}
/* Le rappel « une version plus récente existe ». Il interroge la route qui
   rapproche PAR LE TITRE, et le dit : c'est une heuristique, pas un lien
   établi en base. Deux rendus peuvent partager un titre sans rien avoir en
   commun — mesuré, un même titre couvre jusqu'à sept jobs dans la base
   réelle — donc la DATE et la DURÉE du candidat sont montrées AVANT qu'on
   remplace : le titre, lui, est le même pour tous par construction.
   Silencieux quand il n'y a rien : ni ligne vide, ni « aucune version ». */
var DzmNewerHint=function(props){
  var jid=(props&&props.jobId)||"";
  var sl=x.useState(null),list=sl[0],setList=sl[1];
  var se=x.useState(""),err=se[0],setErr=se[1];
  x.useEffect(function(){
    setList(null);setErr("");
    if(!jid)return;
    var on=!0;
    fetch("/api/montage/newer?job_id="+encodeURIComponent(jid))
      .then(function(res){return res.json()})
      .then(function(d){if(on)setList((d&&d.candidates)||[])})
      .catch(function(){if(on)setErr("Versions plus récentes : recherche "+
        "impossible (le service n'a pas répondu).")});
    return function(){on=!1}},[jid]);
  if(err)return r.jsx("div",{className:"dzm-newer dzm-newererr",children:err});
  if(!list||!list.length)return null;
  return r.jsx("div",{className:"dzm-newer",children:list.map(function(c){
    return r.jsx("button",{className:"dzm-newerb",
      title:"Rapprochement par le TITRE du rendu — une heuristique, pas un "+
        "lien enregistré : rien en base ne relie deux rendus du même plan. "+
        "Le titre étant la clé du rapprochement, TOUS les candidats le "+
        "partagent : ce qui les distingue, c'est la date et la durée "+
        "portées par la ligne. Vérifiez-les avant de remplacer."+
        (c.completed_at?(" Terminé le "+dzmProjWhen(c.completed_at,1)+"."):""),
      "aria-label":dzmNewerLine(c),
      onClick:function(){if(props&&props.onPick)props.onPick(c)},
      children:dzmNewerLine(c)},c.job_id)})})};

/* ── export contrat ───────────────────────────────────────────────────────── */
var DzTracks={ready:!0,TrackAdd:DzmTrackAdd,headBtns:dzmHeadBtns,
  WordAnimChip:DzmWordAnimChip,EmojiBtn:DzmEmojiBtn,
  TextDrawer:DzmTextDrawer,rippleCut:dzmRippleCut,withWords:dzmWithWords,
  dropWords:dzmDropWords,
  gradeAllBtn:dzmGradeAllBtn,gradeAll:dzmGradeAll,gradeOf:dzmGradeOf,
  Projects:DzmProjects,projLine:dzmProjLine,projWhen:dzmProjWhen,
  tracksOf:svmTracksOf,from:svmTracksFrom,payload:svmTracksPayload,
  busSync:svmTrackBusSync,skin:dzmSkin,
  pickTrack:dzmPickTrack,isVideoJob:dzmIsVideoJob,
  LibBtn:DzmLibBtn,badSrc:dzmBadSrcChip,
  replaceSrc:dzmReplaceSrc,revertSrc:dzmRevertSrc,
  replaceBtn:dzmReplaceBtn,revertBtn:dzmRevertBtn,
  newerLine:dzmNewerLine,NewerHint:DzmNewerHint,
  move:dzmMove,moveTo:dzmMoveTo,add:dzmAdd,remove:dzmRemove,group:dzmGroup,
  clipsOn:dzmClipsOn,emojiClips:dzmEmojiClips,WORD_ANIMS:DZM_WORD_ANIMS,
  DEFAULTS:DZM_DEFAULT_TRACKS};
window.DzTracks=DzTracks;
