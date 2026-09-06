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
                         fitDur, durCtl, secs, DUR_MIN,
                         clipLen, needDur, askDur, CLIP_DEFAUTS, DUR_DELAI,
                         dialogueTrack, trackPlein, wantsTwin,
                         audioOf, audioSet, audioForget, askAudio, srcDurOr,
                         srcKey, uniqueId, dedupeIds, seqMax,
                         twinClip, twinPlan, extract, extractBtn,
                         subsSources, subsLabel,
                         isOverlayTrack, overlayOrder, addDit,
                         tbTraces, tbIcons, tbParse, tbSerial,
                         TbIcon, ToolBtn, TB_GROUPES, TB_PX, TB_PX_GRIP,
                         move, moveTo, add, remove, group, DEFAULTS}

   - bdRetire() / bdPlan(dispo, blocs) — étape 6 du handoff « Barre Outils
     Flottante » (§5). La première RECALCULE ce que le retrait des neuf
     contrôles rend au bandeau (697 px nominaux ; le protocole de mesure est
     écrit sur place, avec sa réserve). La seconde décide, largeur
     disponible en entrée, CE QUI SE DÉGRADE — PURE, donc jouée sous node :
     c'est la seule façon de mesurer « jamais deux lignes, jamais de
     défilement horizontal » sans navigateur. `bdMesure` / `bdPose` /
     `bdTour` sont l'hôte : ils mesurent et posent, ils ne décident rien.
   - isOverlayTrack(trId, tracks) / overlayOrder(ids, clips, tracks) — P14 :
     « piste de genre vidéo autre que v1 » (ce que le rendu compose en
     incrustation : montage_service._tracks_meta, `layer`) et l'ordre dans
     lequel l'aperçu doit EMPILER ses overlays actifs — le plus bas d'abord,
     la piste listée le plus haut au-dessus, même loi que `layer`. PURES.
     Les neuf portes du bundle qui codaient « v2 » en dur (aperçu, payload,
     inspecteur, losanges, alignement, point de position, poignées, flèches,
     Échap) lisent la première ; l'aperçu lit la seconde.
   - addDit(ts, kind) — P14 : `add` plus la phrase qui dit ce qui vient
     d'être créé (identifiant, nature). `add(ts,"video")` crée une piste
     vidéo PLEIN CADRE (type « vidéo »), `add(ts,"overlay")` une piste
     d'incrustation (type « overlay » — V2, quand elle est libre, revient
     avec son habillage historique « overlay/VFX », rien ne la renomme).
   - clipLen(kind, srcDur, defauts) — P11 : la longueur à donner au clip
     qu'on pose. PURE, rend {len, origine, note} — la longueur ENTIÈRE de la
     source quand elle est connue, le repli du bundle sinon, et dans ce cas
     seulement une note qui DIT que le chiffre n'est pas celui de la source.
   - dialogueTrack(ts) / trackPlein(ts,id) / wantsTwin(kind,ts,id) — P12 :
     la piste qui reçoit le son d'un plan (bus « dialogue », sinon a1,
     jamais une piste bouclée), et « cette piste vidéo est-elle plein
     cadre ? » (une incrustation ne reçoit pas de jumeau). PURES.
   - askAudio(src, {done, fetch, timer, delai}) / audioOf / audioSet /
     audioForget — P12 : la sonde GET /api/montage/has-audio sur le motif
     d'askDur, et son CACHE par source, qui est le verrou de récursion de
     l'ajout. srcDurOr(kind, srcDur, verdict) prend la durée rendue en
     prime quand on ne la connaît pas encore.
   - uniqueId(clips, base) / dedupeIds(clips) / seqMax(clips) — P12 : des
     identifiants de clips UNIQUES, y compris après rechargement d'une
     sauvegarde qui en porte en double (mesuré).
   - twinClip(clip, trId, clips) / twinPlan(neuf, ts, clips, verdict,
     locked) — P12 : le clip jumeau « … · son du plan » et la décision de
     le poser, chaque sortie DITE. extract(sel, o) / extractBtn(sel, o) —
     le bouton « Extraire le son → A1 » de l'inspecteur, même moteur.
   - needDur(kind, srcDur) / askDur(src, {done, fetch, timer, delai}) — P11 :
     faut-il aller mesurer la durée, et la mesure elle-même
     (GET /api/montage/duration). `askDur` prend ses deux dépendances impures
     en argument, donc elle se joue sous node comme le reste du cœur.

   - fitDur(clips, dur, tail) — P10 : la durée que le projet DOIT avoir,
     c'est-à-dire le maximum entre la durée demandée et la fin du dernier
     clip (plus `tail`), arrondie à la seconde SUPÉRIEURE — l'unité de la
     règle et du total affiché. PURE, et elle ne raccourcit JAMAIS.
   - durCtl({dur, step, clips, onSet, note}) — P10 : le réglage explicite de
     la durée dans la barre de transport, là où ne s'affichait qu'un nombre.
     Allonge, raccourcit, et REFUSE de descendre sous la fin du dernier
     clip. Sans hook, donc exécutable sous node.
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
   la restauration : les deux chemins ne peuvent pas diverger.
   P14 — LE TYPE DEMANDÉ (troisième argument) n'est honoré que pour une piste
   vidéo HORS de la table, et seul « vidéo » compte : une piste vidéo neuve
   est plein cadre si on l'a demandée ainsi, une incrustation sinon — c'est
   le défaut d'avant P14, et c'est ce que redevient une sauvegarde qui ne
   porte pas le type. Une piste plein cadre prend l'habillage de V1
   (hauteur, teinte) : à l'écran, la nature se lit sans ouvrir un titre. */
function dzmSkin(id,kind,type){
  var d=DZM_DEFAULT_TRACKS.filter(function(k){return k.id===id})[0];
  /* une COPIE : rendre l'objet de la table exposerait les défauts partagés à
     la mutation du premier appelant venu. Latent, mais d'un mot. */
  if(d)return Object.assign({},d);
  if(kind==="audio")return {id:id,name:String(id).toUpperCase(),type:"sfx",
    h:48,c:"--c-3d",mix:13,kind:"audio",bus:"sfx"};
  if(kind==="subs")return {id:id,name:String(id).toUpperCase(),type:"sous-titres",
    h:44,c:"--c-text",mix:11,kind:"subs"};
  if(type==="vidéo")return {id:id,name:String(id).toUpperCase(),type:"vidéo",
    h:54,c:"--c-video",mix:13,kind:"video"};
  return {id:id,name:String(id).toUpperCase(),type:"overlay",h:40,c:"--c-3d",
    mix:13,kind:"video"}}

function dzmKindOf(id,kind){
  if(kind)return kind;
  var k=String(id||"").charAt(0);
  return k==="a"?"audio":k==="s"?"subs":"video"}

/* LE REPLI DES PISTES, ÉCRIT UNE FOIS. « Une liste vide vaut les six pistes
   de base » était écrit à deux endroits ; l'étape 4 de la barre en voulait un
   TROISIÈME. Trois copies de la même condition divergent à la première
   retouche, alors les trois appellent celle-ci. C'est un contrôle à deux
   faces : la retirer casse `svmTracksOf`, `DzmTrackAdd` ET le câblage de la
   barre, et trois lignes du banc le disent séparément. */
function dzmTsOr(ts){return (ts&&ts.length)?ts:DZM_DEFAULT_TRACKS}

function svmTracksOf(proj){
  return dzmTsOr(proj&&proj.tracks)}

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
    /* P14 — le type du payload est passé à l'habillage : une piste vidéo
       plein cadre restaurée reprend l'habillage de V1, comme à sa création,
       au lieu de revenir en bande d'incrustation typée « vidéo ». */
    out.push(Object.assign({},dzmSkin(id,kind,t.type),t,{id:id,kind:kind}))});
  return out.some(function(t){return t.id==="v1"})?out:null}

/* Ce qui part au backend (rendu ET autosave) : le strict nécessaire à
   montage_service._tracks_meta. L'habillage reste au client (dzmSkin le
   reconstruit au retour).
   P14 — PLUS LE TYPE « vidéo » d'une piste vidéo autre que v1 : c'est le
   SEUL choix que l'habillage ne sait pas reconstruire (v1 est toujours plein
   cadre, toute autre piste vidéo est une incrustation par défaut). Sans
   cette clé, une piste créée « vidéo » revenait « overlay » au rechargement
   et le jumeau sonore (wantsTwin) changeait d'avis avec elle. Le backend
   range `tracks` tel quel (POST /save : `data["tracks"] = body["tracks"]`)
   et `_tracks_meta` ignore la clé — mesuré. */
function svmTracksPayload(proj){return svmTracksOf(proj).map(function(t){
  var o={id:t.id,kind:t.kind};if(t.bus)o.bus=t.bus;if(t.loop)o.loop=!0;
  if(t.kind==="video"&&t.id!=="v1"&&t.type==="vidéo")o.type="vidéo";return o})}

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
   d'une suppression annulée retrouvent donc leur piste.
   P14 — DEUX SORTES DE PISTES VIDÉO. `kind` vaut « video » (plein cadre,
   type « vidéo »), « overlay » (incrustation, type « overlay ») ou
   « audio » ; les deux premiers fabriquent un identifiant v<n>. Un « vidéo »
   SAUTE un identifiant libre dont l'habillage historique est une
   incrustation (v2 : « overlay/VFX », que rien ne renomme) : sur les pistes
   du 04/09 [v1, a2, a1, a3, s1], « vidéo » aurait sinon créé V2 en
   incrustation — le contraire de ce que le bouton annonce. Le plus petit
   libre reste la règle pour tout le reste, et la note de `dzmAddDit` nomme
   l'identifiant obtenu. */
function dzmAdd(ts,kind){
  var genre=kind==="audio"?"audio":"video";
  var type=kind==="video"?"vidéo":void 0;
  var n=1,ids=ts.map(function(t){return t.id}),t;
  /* BORNÉE (faute n°6 : un banc qui ne finit pas ne rougit jamais) : si
     l'habillage cessait de rendre « vidéo » hors de la table, la boucle
     accepterait le 99e identifiant plutôt que de tourner sans fin. */
  for(;;n++){
    var id=genre.charAt(0)+n;
    if(ids.indexOf(id)>=0)continue;
    t=dzmSkin(id,genre,type);
    if(type!=="vidéo"||t.type==="vidéo"||n>=99)break}
  var at=genre==="video"?0:dzmSubsAt(ts);
  var out=ts.slice();out.splice(at<0?ts.length:at,0,t);return out}
/* LA PISTE, ET LA PHRASE QUI LA DIT (P14). Rend {tracks, id, type, note} :
   la liste neuve, l'identifiant créé, son type d'habillage et la note que
   la barre affiche (fireNote) — la nature de la piste en une phrase, avec
   ce que « vidéo » implique (recouvrement de V1, son extrait) ou ce
   qu'« incrustation » implique (réglable, muette). PURE. */
function dzmAddDit(ts,kind){
  var avant=(ts||[]).map(function(t){return t&&t.id}),out=dzmAdd(ts||[],kind);
  var neuf=null,i;
  for(i=0;i<out.length;i++)if(avant.indexOf(out[i].id)<0){neuf=out[i];break}
  if(!neuf)return {tracks:out,id:"",type:"",note:""};
  var nom=String(neuf.id).toUpperCase(),ty=String(neuf.type||""),note;
  if(neuf.kind==="audio")note="Piste "+nom+" ajoutée — audio, bus "+
    String(neuf.bus||"sfx")+(neuf.loop?", bouclée":"")+" : une bande vide, "+
    "sous les pistes audio existantes.";
  else if(ty==="vidéo")note="Piste "+nom+" ajoutée — vidéo plein cadre : "+
    "ses plans recouvrent V1 pendant leur durée et leur son est extrait sur "+
    "la piste de dialogue ; V1 reste la séquence maîtresse (durée, "+
    "transitions, vitesse, effets).";
  else note="Piste "+nom+" ajoutée — incrustation"+
    (ty==="overlay/VFX"?" (overlay/VFX, la piste historique)":"")+
    " : image dans l'image, réglable (position, échelle, rotation, "+
    "opacité), muette.";
  return {tracks:out,id:neuf.id,type:ty,note:note}}
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
  var ts=dzmTsOr(props&&props.tracks);
  function add(k){if(props&&props.onChange)props.onChange(dzmAdd(ts,k))}
  return r.jsxs("span",{className:"dzm-add",children:[
    r.jsx("button",{className:"svm-tbtn dzm-addb",
      title:"Ajouter une PISTE vidéo plein cadre (une bande vide) — posée "+
        "tout en haut ; ses plans recouvrent V1 pendant leur durée. Pour "+
        "poser un clip, c'est « Bibliothèque… ».",
      "aria-label":"Ajouter une piste vidéo plein cadre",
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
  var ts=dzmTsOr(props&&props.tracks);
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

/* ── L'ACTION « emoji », SORTIE DU BOUTON QUI LA PORTAIT ──────────────
   ÉTAPE 7 DU HANDOFF, §6 : « la barre est un nouveau point d'entrée, pas une
   nouvelle implémentation ». Tant que cette action vivait DANS `DzmEmojiBtn`,
   la barre n'avait rien à appeler — c'est la mesure qui l'avait laissée
   éteinte à l'étape 4. Elle est ici, au premier niveau : le bouton du bandeau
   et le bouton de la barre l'appellent tous les deux, et il n'y a qu'un code.

   L'ATTENTE RESTE À L'APPELANT (`busy` / `setBusy`) : c'est un état React, et
   cette fonction n'a pas de hook. Chaque porte tient la sienne — deux
   portes, deux attentes, et l'étape 6 en refermera une. RESTE ASSUMÉ, dit
   ici plutôt que découvert : d'ici là, deux clics simultanés partent en deux
   requêtes. Elles ne se détruisent pas — chacune pousse l'historique avant
   d'ajouter, et `dzmEmojiClips` numérote ses identifiants sur `Date.now()`.

   `fetch` EST APPELÉE SUR SON OBJET quand elle vient de la fenêtre, jamais
   détachée dans une variable : même leçon que `dzmTbFrame` à l'étape 4
   (« Illegal invocation » sous Blink et WebKit). Et elle est INJECTABLE,
   sans quoi cette fonction ne serait pas jouable sous node — la seule raison
   pour laquelle l'étape 4 ne pouvait rien mesurer d'elle.

   DEUX SORTES DE SORTIE, et le banc lit les deux : un JETON quand elle
   REFUSE (quatre refus, quatre mots distincts — un `return` nu les aurait
   rendus indiscernables), la PROMESSE quand elle part.

   CE QUE FAIT CETTE ACTION ET CE QUE LE §6 DÉCRIT NE SE RECOUVRENT PAS, et
   l'écart est DIT à l'utilisateur dans le titre du bouton de la barre : le
   §6 veut un sélecteur d'emoji dont le choix pose UN clip de 2 s à la tête de
   lecture ; cette base pose, sans sélecteur, UN clip de 0,8 s PAR MOT-CLÉ
   reconnu dans les sous-titres, à la date de ce mot. C'est l'action qui
   existe, et le §6 demande de réutiliser l'action qui existe. */
function dzmEmojiGo(p){
  p=p||{};
  function note(m){if(typeof p.note==="function")p.note(m)}
  function busy(v){if(typeof p.setBusy==="function")p.setBusy(v)}
  if(p.busy)return "occupe";
  var segs=p.segments||[];
  if(!segs.length){
    note("Aucun sous-titre : les emoji se posent sur les MOTS d'une "+
      "réplique. Écrivez la piste S1 d'abord.");return "sans-soustitre"}
  if(typeof p.onAdd!=="function"){
    note("Emoji : rien pour recevoir les clips.");return "sans-hote"}
  var f=(typeof p.fetch==="function")?p.fetch:null;
  if(!f&&typeof window!=="undefined"&&typeof window.fetch==="function")
    f=function(u,o){return window.fetch(u,o)};
  if(!f){note("Emoji : ce navigateur ne sait pas interroger le serveur.");
    return "sans-reseau"}
  busy(1);
  return f("/api/subtitles/emoji-hints",{method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({segments:segs})})
    .then(function(rp){return rp.json()})
    .then(function(d){
      busy(0);
      var hs=(d&&d.hints)||[];
      if(!hs.length){note("Aucun mot-clé reconnu — les mots suivis sont "+
        "feu, lune, vague, poulpe, or, fusée.");return}
      var cs=dzmEmojiClips(hs,p.tracks,Date.now());
      if(!cs.length){note("Aucune piste vidéo d'overlay pour les poser : "+
        "ajoutez-en une par « + vidéo ».");return}
      p.onAdd(cs);
      note(cs.length+" emoji posé"+(cs.length>1?"s":"")+" sur "+cs[0].tr+
        " — annuler les retire tous.")})
    .catch(function(e){busy(0);
      note("Emoji : "+((e&&e.message)||"échec de la requête"))})}
/* Le bouton « emoji » du bandeau : il ne porte plus QUE son attente.
   RÉVERSIBLE — l'appelant pousse l'historique AVANT d'ajouter, donc
   « annuler » les retire d'un coup ; et ce sont des clips ordinaires, qui se
   déplacent et se suppriment comme les autres. */
var DZM_EMO_TITRE="Poser un emoji sur les mots-clés des sous-titres (feu, "+
  "lune, vague, poulpe, or, fusée) — un clip par mot, sur la piste "+
  "d'overlay la plus haute. Annuler les retire.";
var DzmEmojiBtn=function(props){
  var sb=x.useState(0),busy=sb[0],setBusy=sb[1];
  return r.jsx("button",{className:"svm-tbtn dzm-emo",disabled:!!busy,
    title:DZM_EMO_TITRE,
    "aria-label":"Poser les emoji des mots-clés",
    onClick:function(){dzmEmojiGo({segments:props&&props.segments,
      tracks:props&&props.tracks,note:props&&props.note,
      onAdd:props&&props.onAdd,busy:busy,setBusy:setBusy})},
    children:busy?"…":"emoji"})};

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
  /* ÉTAPE 6 (§5.1) — MONTÉ NU. Le §5.1 retire `projets` du bandeau, mais ce
     composant est DEUX choses : le bouton ET la liste qu'il ouvre. Retirer
     les deux aurait rendu MORT le bouton `projets` de la barre flottante,
     qui n'ouvre pas une liste à lui — il DEMANDE l'ouverture de celle-ci
     (`openReq`, un compteur, cf. l'étape 7). `nu` retire donc le bouton et
     garde la liste : un seul contrôle, une seule liste, aucun doublon.
     C'est le seul des neuf dans ce cas — les huit autres n'ont pas de
     panneau attaché à leur bouton. */
  var nu=!!(props&&props.nu);
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

  /* ÉTAPE 7 — LE SECOND POINT D'ENTRÉE (§6 : « la barre est un nouveau point
     d'entrée, pas une nouvelle implémentation »). Le §6 dit OUVRE, pas
     BASCULE : la barre incrémente un compteur, l'ouverture est donc
     IDEMPOTENTE et le même geste ne referme jamais la liste par accident.
     POURQUOI UN COMPTEUR ET NON UN BOOLÉEN PARTAGÉ, et c'est mesuré : ce
     popover se ferme sur un `mousedown` HORS de sa boîte, et le bouton de la
     barre est hors de cette boîte. Un booléen piloté depuis la barre serait
     donc remis à faux par ce `mousedown` juste avant que le `click` le
     ramène à vrai — deux écritures pour un geste, dont l'ordre décide. Le
     compteur, lui, ne décrit pas un ÉTAT mais une DEMANDE : quel que soit
     l'ordre des deux événements, la dernière chose faite est d'ouvrir.
     `oreq<=0` GARDE LE MONTAGE : l'effet part une première fois à zéro, et
     sans cette ligne la liste s'ouvrirait toute seule au chargement.
     RIEN D'AUTRE N'EST TOUCHÉ : ni la timeline, ni la tête de lecture, ni
     l'historique. C'est `doOpen`, plus bas, qui remplace le montage — et il
     demande confirmation avant, ce que le §6 exige et que la base faisait
     déjà. */
  var oreq=Number(props&&props.openReq)||0;
  x.useEffect(function(){
    if(oreq<=0)return;
    setOp(!0);setArm("");setRen(null);load()},[oreq]);

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
  return r.jsxs("span",{className:"dzm-proj",ref:box,
    "data-nu":nu?"":void 0,children:[
    nu?null:r.jsx("button",{className:"svm-tbtn dzm-projb","data-on":op?"":void 0,
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
/* CE QUE LE TROU DEVIENT AU RENDU — TROIS CAS, pas deux. Une première
   version disait « rendu en noir » partout ; la deuxième basculait sur
   `tr==="v1"` et appelait donc PISTE D'OVERLAY tout ce qui n'est pas V1 —
   les pistes SON comprises, où il n'y a aucune piste du dessous à faire
   réapparaître. Le bouton « Remplacer la source… » n'est gardé que sur
   `sel.src` et le refus de genre PERMET audio→audio : le cas est atteint,
   pas théorique. MESURÉ dans la sauvegarde de l'utilisateur (17 clips) :
   8 portent une source, dont un A1 et un A2 — soit deux des huit boutons.

   Ce que le rendu fait de chaque cas (backend/app/services/montage_service.py) :
     · V1, piste de BASE : les trous partent en `color=c=black` (branche
       `s.get("gap")`) — l'image devient noire ;
     · piste vidéo d'INCRUSTATION : le clip est posé en
       `overlay … enable='between(t,st,en)'`, l'incrustation s'arrête plus
       tôt et c'est la piste du dessous qui redevient visible ;
     · piste SON : le clip est `atrim` puis `adelay` à sa place, mixé en
       `amix` — rien ne remplit le trou, cette piste se tait. RÉSERVE
       MESURÉE : le PREMIER clip d'une piste BOUCLÉE (a2 par défaut, `loop`
       venu du payload) ne devient pas un clip du tout mais l'entrée
       `music`, prise en `-stream_loop -1` et coupée par `-t total` ; ses
       `start`/`end`/`srcIn` ne sont JAMAIS lus, et il n'entre pas non plus
       dans `audio_end`. Le raccourcir ne change donc rien au rendu — et
       c'est le cas de l'unique clip A2 de la sauvegarde mesurée. La phrase
       le dit au lieu de promettre un silence qui ne viendra pas.
   Le genre est lu par `dzmKindOf`, la fonction que cette couche emploie
   déjà (même règle que `trackKind` du bundle : l'initiale de la piste) —
   pas une seconde règle. Une piste de SOUS-TITRES (« subs ») ne reçoit
   AUCUNE des trois phrases : ses clips n'ont pas de source (mesuré : les
   9 clips `s1` de la sauvegarde, aucun avec `src`), le bouton ne s'y montre
   donc jamais, et affirmer quoi que ce soit d'un cas qu'on n'a pas mesuré
   est exactement la faute que ces trois cas corrigent. */
function dzmGapFate(tr){
  var kd=dzmKindOf(tr);
  if(kd==="audio")
    return " — sur une piste son, aucune piste ne réapparaît en dessous : "+
      "ce trou-là s'entend. Sauf sur une piste BOUCLÉE (A2 par défaut), "+
      "dont le rendu ignore les bornes de son premier clip et joue la "+
      "source d'un bout à l'autre du film.";
  if(kd!=="video")return ".";
  return tr==="v1"
    ?", rendu en noir à l'export."
    :" — sur une piste d'incrustation, c'est la piste du dessous qui "+
     "réapparaît.";}
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
        "et la timeline garde un trou derrière lui"+dzmGapFate(o.tr)}
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
   exactement l'avertissement que `replaceSrc` rendra.

   L'ORDRE EST LE CORRECTIF, et il vient d'une mesure de LARGEUR. Une
   première version écrivait « Version plus récente : TITRE · date · durée
   — remplacer », c'est-à-dire les discriminants DERRIÈRE un préfixe que
   tous les candidats partagent — dans un bouton
   `white-space:nowrap; overflow:hidden; text-overflow:ellipsis`. La
   troncature retire la fin : elle mangeait exactement ce que la ligne
   venait de gagner.
   LA MESURE (shared/son-vfx-montage.css, `box-sizing:border-box` global
   ligne 56) : `.svm-insp` fait 300 px, bordure gauche 1 px et 16 px de
   marge intérieure de chaque côté, déclarée UNE fois et sans media-query
   qui la reprenne (le fichier n'en porte qu'une, `prefers-reduced-motion`).
   Reste 267 px ; moins ~16 px de barre de défilement (`overflow:auto`,
   0 avec des barres en surimpression), moins la bordure du bouton (2 px)
   et sa marge intérieure (`padding:4px 8px`, 16 px) : de 233 à 249 px
   utiles. À 9 px avec `letter-spacing:.02em`, l'avance par caractère va de
   ~5,13 px (Consolas, 0,55 em) à ~5,58 px (JetBrains Mono, 0,6 em) : de
   42 à 48 CARACTÈRES visibles. C'est une BORNE, pas un nombre — la coupe
   dépend de la fonte réellement résolue et de la barre de défilement, et
   rien ici ne rend une page.
   OR, dans l'ancien ordre, les secondes tombaient au caractère 48 à 54 et
   la durée plus loin encore (mesuré sur les groupes homonymes de la base :
   préfixe partagé de 39 à 49 caractères). Sur « tweet_2026-05-20 » (7 jobs)
   comme sur les deux « backdoorpromo » à 36 s d'écart — la paire même qui
   justifiait d'afficher la seconde — les boutons redevenaient visuellement
   identiques. L'`aria-label` portant la ligne entière, seul l'utilisateur
   VOYANT y perdait.
   D'OÙ : les deux discriminants D'ABORD, le titre ENSUITE, le verbe en
   queue. Ce qui est tronqué est alors ce que la construction rend
   redondant — le titre est la clé du rapprochement, il est le MÊME pour
   tous — et jamais ce qui distingue. Dans le pire cas mesuré (42
   caractères, « durée inconnue »), la date à la seconde ET la durée
   tiennent entières.
   ET LE SENS PARTAGÉ SORT DES BOUTONS : « Version plus récente » n'est plus
   répété N fois dans N libellés tronqués, il est dit UNE fois par l'en-tête
   `.dzm-newerh` du bloc, qui ne porte NI `nowrap` NI ellipse et ne peut
   donc pas être coupé. Contrairement à ce que suggérait la revue, le
   panneau ne le disait PAS déjà : mesuré dans le bundle livré, le rappel
   est rendu entre `revertBtn` et `transInspector()`, sans aucun libellé
   visible au-dessus — laisser tomber le préfixe sans rien mettre à sa
   place aurait rendu une rangée d'horodatages nus. L'`aria-label`, lui,
   reprend l'en-tête ET la ligne : un lecteur d'écran qui tabule droit sur
   le bouton entend les deux. */
var DZM_NEWER_H="Rendus plus récents portant ce titre";
function dzmNewerLine(c){
  if(!c)return "";
  var o=c,bits=[],w=dzmProjWhen(o.completed_at,1),d=Number(o.duration_s)||0;
  if(w)bits.push(w);
  bits.push(d>0?(d.toFixed(1).replace(".",",")+" s"):"durée inconnue");
  bits.push(o.title||o.job_id||"sans titre");
  return bits.join(" · ")+" — remplacer"}
/* Le rappel « une version plus récente existe ». Il interroge la route qui
   rapproche PAR LE TITRE, et le dit : c'est une heuristique, pas un lien
   établi en base. Deux rendus peuvent partager un titre sans rien avoir en
   commun — mesuré, un même titre couvre jusqu'à sept jobs dans la base
   réelle — donc la DATE et la DURÉE du candidat sont montrées AVANT qu'on
   remplace : le titre, lui, est le même pour tous par construction.
   Silencieux quand il n'y a rien : ni ligne vide, ni « aucune version ».
   L'EN-TÊTE porte le sens que les N boutons partageaient — voir la mesure
   de largeur au-dessus de `dzmNewerLine`. Il est rendu UNE fois, il ne
   peut pas être tronqué, et l'`aria-label` de chaque bouton le reprend. */
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
  return r.jsxs("div",{className:"dzm-newer",children:[
    r.jsx("div",{className:"dzm-newerh",children:DZM_NEWER_H},"dzmnewh"),
    list.map(function(c){
    return r.jsx("button",{className:"dzm-newerb",
      title:"Rapprochement par le TITRE du rendu — une heuristique, pas un "+
        "lien enregistré : rien en base ne relie deux rendus du même plan. "+
        "Le titre étant la clé du rapprochement, TOUS les candidats le "+
        "partagent : ce qui les distingue, c'est la date et la durée "+
        "portées par la ligne. Vérifiez-les avant de remplacer."+
        (c.completed_at?(" Terminé le "+dzmProjWhen(c.completed_at,1)+"."):""),
      "aria-label":DZM_NEWER_H+" : "+dzmNewerLine(c),
      onClick:function(){if(props&&props.onPick)props.onPick(c)},
      children:dzmNewerLine(c)},c.job_id)})]})};

/* ── P10 : LA TIMELINE S'ÉTEND AU LIEU DE ROGNER ────────────────────────────
   LE DÉFAUT, rapporté par l'utilisateur : « j'ai voulu ajouter trois vidéos
   depuis la bibliothèque, or la timeline est fixe, je suis obligé de
   raccourcir des pistes vidéo pour les faire rentrer ». MESURÉ dans le
   bundle : `proj.dur` n'était écrit qu'UNE fois, au chargement — aucun
   contrôle de l'écran ne le touchait — et trois gestes rognaient contre lui
   EN SILENCE (l'ajout, le décalage clavier, le glisser à la souris).

   ÉTENDRE EST SANS RISQUE POUR LE RENDU, et c'est mesuré des deux côtés :
   `renderPayload()` du bundle n'emporte AUCUNE clé `duration`, et
   `_build_montage_command` (montage_service.py) recalcule `total` depuis
   `seg_durs`. La seule route qui lit la durée postée est POST /save, qui la
   RANGE. `proj.dur` est donc une BORNE D'ÉDITION, pas une propriété du film.

   RÉSERVE CENTRALE, portée par chaque note de cette tâche : `proj.dur`
   N'ENTRE PAS DANS L'HISTORIQUE. `pushHistory` ne mémorise que
   {clips, mixDb} — étendre puis annuler rend les clips, PAS la durée. C'est
   exactement le piège que P3 avait choisi d'éviter en ne touchant pas à
   `dur` ; on y touche ici DÉLIBÉRÉMENT, et le retour existe : c'est le
   contrôle de durée de la barre de transport (`dzmDurCtl`), qui raccourcit
   aussi bien qu'il allonge. Faire entrer `dur` dans l'historique demanderait
   de réécrire `pushHistory`, `undo` et `redo` — trois fermetures du bundle
   dont aucune n'offre d'ancre unique : c'est une tâche à part, et rien ici
   ne fait semblant de l'avoir faite. */

/* LE PLANCHER, repris de `svmApplyProject` : `dur:Math.max(1,…)`. Une durée
   nulle ou négative rend `c.start/dur*100+"%"` non fini — toute la timeline
   perd sa géométrie. */
var DZM_DUR_MIN=1;

/* LA DURÉE QUE LE PROJET DOIT AVOIR. PURE.
   `dur` est un PLANCHER, jamais un plafond : cette fonction ne raccourcit
   JAMAIS rien — c'est le contrôle explicite de la barre de transport qui
   raccourcit, et lui seul. Elle rend donc le maximum entre la durée demandée
   et la fin du dernier clip augmentée de `tail`.

   L'ARRONDI EST AU PLAFOND, ET IL EST MESURÉ, PAS CHOISI. La barre de
   transport affiche `svmRuler(Math.round(dur))` et la règle du bundle est
   graduée en SECONDES ENTIÈRES (`tickStep` vaut 2, 3, 5, 6, 10, 15, 20, 30
   ou 60). Une durée de 20,37 s s'afficherait « 0:20 » alors qu'un clip finit
   à 20,37 : le seul arrondi qui ne fasse pas mentir le total affiché est
   celui qui monte. La « marge de queue » gratuite qui en découle vaut donc
   moins d'une seconde, et elle n'est inventée nulle part.

   Les valeurs illisibles sont IGNORÉES, jamais propagées : un `end` à NaN ou
   à l'infini rendrait `Math.max` non fini, et la timeline entière avec lui. */
function dzmFitDur(clips,dur,tail){
  var d=Number(dur);if(!isFinite(d))d=0;
  var t=Number(tail);if(!isFinite(t)||t<0)t=0;
  var m=0,i,e;
  if(clips&&clips.length)for(i=0;i<clips.length;i++){
    e=clips[i]?Number(clips[i].end):NaN;
    if(isFinite(e)&&e>m)m=e}
  /* `tail` s'ajoute à la fin d'un CLIP : sans clip, il n'y a pas de queue à
     laisser, et une timeline vide ne doit pas s'allonger toute seule. */
  var need=m>0?Math.ceil(m+t):0;
  return Math.max(DZM_DUR_MIN,d,need)}

/* « 2 s », « 0,5 s » — la virgule décimale du français, comme `dzmNewerLine`. */
function dzmSecs(v){
  var n=Math.round(Number(v)*10)/10;
  if(!isFinite(n))n=0;
  return (n===Math.round(n)?String(Math.round(n))
                           :n.toFixed(1).replace(".",","))+" s"}

/* `svmRuler` / `svmPad2` sont les fonctions DU BUNDLE (même portée module :
   cette couche est injectée dans le bloc `sonvfx`, comme `SVM_TRACK_BUS`
   qu'elle mute déjà). On ne recopie pas leur règle : une seconde version du
   format m:ss divergerait de la première au premier changement. Le banc les
   EXTRAIT du bundle pour les jouer sous node, et vérifie des deux côtés que
   la couche les appelle et que le bundle les déclare. */
function dzmDurTxt(v){return svmRuler(Math.round(v))}

var DZM_DUR_UNDO=" « Annuler » ne rend pas la durée du projet : l'historique "+
  "de cet écran ne mémorise que les clips et le mixage. C'est ce réglage-ci "+
  "qui la reprend, dans les deux sens.";

function dzmDurBtn(cls,lbl,ttl,aria,fn,key){
  return r.jsx("button",{className:"svm-zoomstep dzm-durb "+cls,
    title:ttl,"aria-label":aria,onClick:fn,children:lbl},key)}

/* LE CONTRÔLE EXPLICITE DE LA DURÉE, dans la barre de transport, à la place
   du simple affichage « 1:04 total » qui s'y trouvait. Il paie aussi la
   dette laissée par P3, dont la note disait « la fin de la timeline est
   maintenant vide, raccourcissez-la si vous voulez » alors que RIEN ne
   permettait de la raccourcir.

   LE PAS EST MESURÉ, PAS INVENTÉ : c'est `tickStep`, la graduation que la
   règle DESSINE déjà (`[2,3,5,6,10,15,20,30,60].find(dur/s<=11)||60`). Un
   clic vaut donc exactement une graduation, à toutes les échelles — 2 s sur
   un montage de 16 s, 30 s sur un montage de 5 min. Un pas fixe aurait été
   un chiffre de plus sorti de nulle part, et illisible à l'une des deux
   extrémités.

   LES BORNES SONT MESURÉES ELLES AUSSI :
     · en bas, la fin du dernier clip (`dzmFitDur(clips, 1)`), et le plancher
       de 1 s de `svmApplyProject` en deçà. RACCOURCIR SOUS CETTE BORNE EST
       REFUSÉ, jamais fait en silence : les clips ne seraient pas supprimés,
       mais ils sortiraient du champ — `left:c.start/dur*100+"%"` les
       pousserait hors de la bande, et le seul moyen de les revoir serait de
       rallonger. Le refus NOMME l'instant qui bloque et dit quoi faire.
       Un « − » qui tomberait SOUS la borne n'est pas refusé pour autant : il
       s'ARRÊTE dessus, et le dit.
     · en haut, aucune. La seule limite mesurée est celle de la RÈGLE, qui
       cesse de graduer au-delà de 40 traits (`ticks.length<40`, pas maximal
       60 s → 40 min) ; elle ne casse rien et ne justifie pas un refus. Elle
       est consignée dans le banc comme dette d'écran.

   AUCUN `pushHistory` ICI, ET C'EST DÉLIBÉRÉ : l'historique ne mémorise que
   {clips, mixDb}. Pousser une entrée pour un geste qui ne change NI l'un NI
   l'autre donnerait un « annuler » qui restaure des clips identiques et
   laisse la durée où elle est — un retour qui ne retourne rien. Le retour de
   ce geste, c'est ce contrôle lui-même, et chaque note le dit. */
function dzmDurCtl(o){
  o=o||{};
  var set=o.onSet,note=o.note;
  var d=Number(o.dur);if(!isFinite(d)||d<DZM_DUR_MIN)d=DZM_DUR_MIN;
  var stp=Number(o.step);if(!isFinite(stp)||stp<=0)stp=1;
  var fit=dzmFitDur(o.clips,DZM_DUR_MIN,0);
  var vide=Math.round((d-fit)*1000)/1000;
  function put(nv,msg){if(set)set(nv);if(note)note(msg+DZM_DUR_UNDO)}
  function moins(){
    if(d<=fit){if(note)note("La timeline fait déjà la longueur de son "+
      "contenu ("+dzmDurTxt(fit)+", fin du dernier clip) : la raccourcir "+
      "ferait sortir des clips du champ — ils ne seraient pas supprimés, "+
      "mais plus rien ne les montrerait. Déplacez ou retirez d'abord le "+
      "dernier clip.");return}
    var vise=Math.round((d-stp)*1000)/1000,nv=Math.max(fit,vise);
    put(nv,"Timeline raccourcie de "+dzmDurTxt(d)+" à "+dzmDurTxt(nv)+
      (nv>vise?(" — le pas de "+dzmSecs(stp)+" s'est arrêté sur la fin du "+
        "dernier clip : aucun clip ne sort du champ."):"")+
      " Aucun clip n'a bougé.")}
  function plus(){
    var nv=Math.round((d+stp)*1000)/1000;
    put(nv,"Timeline allongée de "+dzmDurTxt(d)+" à "+dzmDurTxt(nv)+
      " (+"+dzmSecs(stp)+"). Aucun clip n'a bougé.")}
  function ajuste(){
    put(fit,"Timeline ajustée à son contenu : "+dzmDurTxt(d)+" → "+
      dzmDurTxt(fit)+", soit "+dzmSecs(vide)+" de queue vide retirés. "+
      "Aucun clip n'a bougé.")}
  var kids=[
    dzmDurBtn("dzm-durm","−",
      "Raccourcir la timeline d'une graduation ("+dzmSecs(stp)+"). Le "+
      "raccourcissement s'arrête sur la fin du dernier clip : aucun clip ne "+
      "peut sortir du champ."+DZM_DUR_UNDO,
      "Raccourcir la timeline de "+dzmSecs(stp),moins,"m"),
    r.jsx("span",{className:"dzm-durv",
      title:"Durée de la timeline — une BORNE D'ÉDITION, pas une propriété "+
        "du film : le rendu recalcule sa durée depuis les plans, cette "+
        "valeur ne lui est jamais envoyée. Les boutons − et + la règlent "+
        "d'une graduation de la règle ("+dzmSecs(stp)+")."+DZM_DUR_UNDO,
      children:dzmDurTxt(d)+" total"},"v"),
    dzmDurBtn("dzm-durp","+",
      "Allonger la timeline d'une graduation ("+dzmSecs(stp)+")."+
      DZM_DUR_UNDO,
      "Allonger la timeline de "+dzmSecs(stp),plus,"p")];
  /* « ajuster » n'apparaît QUE s'il y a une queue vide à retirer : un bouton
     toujours là mais sans effet neuf fois sur dix serait un piège de plus. */
  if(vide>0)kids.push(dzmDurBtn("dzm-durf","ajuster",
    "Ramener la fin de la timeline sur le dernier clip : "+dzmSecs(vide)+
    " de vide à retirer. Aucun clip ne bouge ni ne disparaît."+DZM_DUR_UNDO,
    "Ajuster la timeline à son contenu",ajuste,"f"));
  return r.jsx("span",{className:"dzm-durctl",children:kids},"dzmdur")}

/* ══ P11 — UN CLIP ENTRE À LA LONGUEUR DE SA SOURCE ═══════════════════════
   P10 a rendu la timeline extensible ; il restait un SECOND plafond, dans le
   bundle, qui bornait la longueur d'un clip AU MOMENT OÙ ON LE POSE. Une
   vidéo entrait à six secondes quelle que soit sa longueur réelle, un son à
   huit : même avec une timeline infinie, les sources entraient tronquées.

   LEVER LE PLAFOND NE SUFFIT PAS, et c'est le cœur de la tâche. MESURÉ le
   05/09/2026 sur un instantané COHÉRENT de la base de l'utilisateur
   (`sqlite3.connect('file:…?mode=ro', uri=True).backup(dst)`, qui fusionne
   le WAL — une copie d'octets du seul `.db` comptait 106 jobs contre 120) :
   sur ses trois vidéos, `duration_s` vaut 16 pour l'une et NULL pour les
   deux autres. Pour celles-là, l'application n'a RIEN à lever : elle ignore
   la durée. Il faut donc aussi la DÉCOUVRIR — c'est `askDur`, et la route
   `GET /api/montage/duration` qui la sert.

   TROIS FONCTIONS, ET LA FRONTIÈRE ENTRE ELLES EST NETTE :
     · `clipLen` DÉCIDE — pure, sans réseau, sans horloge, jouée en entier
       sous node par test_montage_bundle.py ;
     · `needDur` dit S'IL FAUT DEMANDER — pure elle aussi ;
     · `askDur` DEMANDE — c'est la seule à toucher au réseau, et ses deux
       dépendances (`fetch`, `setTimeout`) sont INJECTABLES, donc elle se
       joue sous node comme les autres au lieu de rester une dette de
       navigateur.

   POURQUOI UNE ROUTE, ET PAS LA DURÉE LUE À L'ÉCRAN NI JOINTE À LA LISTE.
   Trois voies étaient ouvertes ; celle-ci est prise pour des raisons
   mesurées, écrites ici pour qu'on puisse les contester avec un chiffre.
     · JOINDRE LA DURÉE À LA LISTE DU SÉLECTEUR aurait sondé DOUZE assets à
       chaque ouverture (la liste est tranchée à douze), soit 0,7 à 1,0 s de
       ffprobe pour une liste dont l'utilisateur ne pose qu'une ligne — et
       n'aurait RIEN fait pour « Envoyer vers → Montage », qui n'ouvre aucune
       liste et envoie une durée nulle par construction.
     · LA LIRE À L'ÉCRAN (`loadedmetadata`) aurait demandé une URL jouable
       par source ; le vocabulaire de source du Montage ({job_id}, {audio},
       {image}, {file_path}) n'en a pas, et lui en donner une était une
       tâche à soi seule.
     · LA ROUTE, elle, parle EXACTEMENT ce vocabulaire (elle réutilise
       `_resolve_src`), coûte UN ffprobe — MESURÉ : médiane 56 à 85 ms sur
       les cinq vidéos réelles de l'utilisateur, 12 appels après 3 de
       chauffe, ffprobe 8.1.1-essentials_build, Windows 11 / AMD64 — et ne
       coûte RIEN au chargement de l'écran : elle n'est appelée QUE lorsqu'un
       clip est posé, et seulement si la durée manque.

   L'ÉCRAN RESTE VIVANT PENDANT : l'appel ne bloque rien (une promesse), et
   il porte un DÉLAI. Passé ce délai, le clip est posé quand même — à sa
   longueur par défaut, en le disant. Le pire cas mesurable côté serveur est
   le délai d'attente de `_probe_duration` (30 s sur un fichier tronqué) ;
   sans ce garde-fou, l'utilisateur aurait cliqué et rien n'aurait bougé
   pendant une demi-minute. */

/* LES TROIS REPLIS NE SONT PAS ÉCRITS ICI, ILS SONT REÇUS. C'est le bundle
   qui les porte depuis toujours (une image cadrée à 4 s, un son à 8, une
   vidéo à 6) et il les PASSE en troisième argument : la couche ne devient
   pas une seconde autorité pour trois chiffres qui ne sont pas les siens.
   Cette table-ci n'est que le repli du repli — elle sert quand l'appelant
   n'en passe pas, ou en passe un illisible. */
var DZM_CLIP_DEFAUTS={image:4,audio:8,video:6};

/* LA LONGUEUR À DONNER AU CLIP. PURE.
   Rend {len, origine, note} :
     · origine "source" — la durée de la source est lisible et exploitable :
       c'est ELLE, entière, sans plafond d'aucune sorte ;
     · origine "repli"  — la durée est inconnue (nulle, négative, illisible,
       absente) : le clip prend la longueur par défaut, ET LE DIT. Un clip
       posé à 6 s parce que l'application ignore la vraie longueur ne doit
       pas se faire passer pour une source de 6 s ;
     · origine "image"  — une image n'a PAS de longueur naturelle. Ses 4 s ne
       sont donc pas une ignorance mais un cadrage, et il n'y a rien à
       confesser : la note est vide. La durée passée est ignorée pour ce
       genre-là, comme elle l'a toujours été.

   AUCUN PLAFOND HAUT, ET C'EST UN CHOIX MESURÉ. Une source de 21 s entre à
   21 s, une de dix minutes à dix minutes. La seule borne haute connue du
   dépôt est celle de la RÈGLE, qui cesse de graduer au-delà de 40 traits
   (soit 40 min) — elle est consignée en dette d'écran depuis P10, elle ne
   casse rien, et elle ne justifie pas de rogner une source. Ce qui est
   refusé n'est donc pas « trop long » mais « pas un nombre utilisable » :
   NaN, l'infini, zéro, le négatif, une chaîne.

   LA GARDE DES CLIPS MINUSCULES N'EST PAS ICI, et c'est délibéré : une
   source de 0,2 s donne bien un clip de 0,2 s. C'est l'appelant qui décale
   le point de départ pour qu'un tel clip reste saisissable à la souris —
   cette règle-là lui appartient depuis P10, et deux autorités pour une même
   borne divergeraient au premier changement. */
function dzmClipLen(kind,srcDur,defauts){
  var D=defauts&&typeof defauts==="object"?defauts:{};
  function repli(k){
    var v=Number(D[k]);
    return isFinite(v)&&v>0?v:DZM_CLIP_DEFAUTS[k]}
  if(kind==="image")return {len:repli("image"),origine:"image",note:""};
  var k=kind==="audio"?"audio":"video";
  var v=Number(srcDur);
  if(isFinite(v)&&v>0)return {len:Math.round(v*1000)/1000,origine:"source",
    note:" Le clip fait "+dzmSecs(v)+", la longueur ENTIÈRE de la source."};
  var r=repli(k);
  return {len:r,origine:"repli",
    /* L'ACCORD EST PORTÉ PAR LA BRANCHE, pas par un suffixe commun :
       « Cette vidéo a été posé » était la phrase livrée, et elle est
       LUE par l'utilisateur à chaque source non mesurable. Le son
       était juste par accident (masculin), la vidéo fausse. */
    note:" "+(k==="audio"?"Ce son a été posé":"Cette vidéo a été posée")
      +" à "+dzmSecs(r)+" — une longueur PAR DÉFAUT, pas la sienne : "+
      "l'application n'a pas pu mesurer la durée de cette source. Rognez le "+
      "bord droit du clip pour lui donner sa vraie longueur."}}

/* FAUT-IL ALLER DEMANDER LA DURÉE ? PURE.
   Non pour une image (elle n'en a pas). Non quand on la connaît déjà. Non
   quand elle est NÉGATIVE — et cette troisième réponse est le verrou de
   récursion de l'appelant : celui-ci se rappelle avec la mesure quand elle
   est bonne, et avec un nombre négatif quand elle a échoué. Sans ce
   troisième cas, une source que la mesure ne sait pas dater relancerait la
   mesure indéfiniment. Une valeur illisible (NaN, une chaîne) fait bien
   demander : c'est exactement le cas où l'on ne sait rien. */
function dzmNeedDur(kind,srcDur){
  if(kind==="image")return !1;
  var v=Number(srcDur);
  return !(isFinite(v)&&v!==0)}

/* LE DÉLAI AU-DELÀ DUQUEL ON POSE LE CLIP SANS ATTENDRE LA MESURE.
   1,5 s, soit près de vingt fois la mesure médiane observée (56 à 85 ms) :
   le chemin normal ne le rencontre jamais. Il n'existe que pour le chemin
   pathologique — une source tronquée sur laquelle ffprobe tient ses 30 s
   d'attente — où le seul défaut inacceptable serait un clic sans effet. */
var DZM_DUR_DELAI=1500;

/* LA DURÉE D'UNE SOURCE, DEMANDÉE AU BACKEND.
   `done(dur, pourquoi)` est appelée UNE SEULE FOIS, toujours, quoi qu'il
   arrive : `dur` vaut 0 dès que la mesure n'a pas abouti, et `pourquoi`
   nomme la sortie prise. Les deux dépendances impures sont injectables
   (`o.fetch`, `o.timer`) — c'est ce qui rend cette fonction jouable sous
   node, au lieu de laisser tout le chemin réseau en dette de navigateur.

   `rendu` EST LE POINT : le délai et la réponse courent l'un contre
   l'autre. Le premier arrivé gagne, le second ne fait rien — sans ce
   verrou, une réponse tardive poserait un SECOND clip.

   ABSENT ET NUL NE SE VALENT PAS, et ce n'est pas un raffinement de style :
   `o.fetch` ABSENT veut dire « prends celui de l'hôte », `o.fetch` NUL veut
   dire « il n'y en a pas ». Un simple `o.fetch||…` confondait les deux, et
   la branche « sans réseau » devenait alors INATTEIGNABLE au banc — node 18
   et les suivants portent un `fetch` global, qui reprenait la main sur le
   nul injecté et partait pour de vrai sur une URL relative. Une branche
   qu'aucun test ne peut atteindre est une branche qu'on croit tenue.

   LES DEUX GLOBALES SONT ENVELOPPÉES, JAMAIS PRISES NUES : `var t=setTimeout;
   t(fn,ms)` et `var f=fetch; f(u)` perdent leur récepteur, et plusieurs
   moteurs répondent « Illegal invocation ». C'est le seul chemin de cette
   fonction qu'aucun banc ne joue — node injecte les siens — donc il est écrit
   pour être juste sans mesure, pas mesuré. Dette déclarée. */
function dzmAskDur(src,o){
  o=o||{};
  var fin=typeof o.done==="function"?o.done:function(){};
  var f=o.fetch===void 0
    ?(typeof fetch==="function"?function(u){return fetch(u)}:null):o.fetch;
  var tm=o.timer===void 0
    ?(typeof setTimeout==="function"
        ?function(fn,ms){return setTimeout(fn,ms)}:null):o.timer;
  var ms=Number(o.delai);if(!isFinite(ms)||ms<=0)ms=DZM_DUR_DELAI;
  var rendu=!1;
  function rend(v,pq){if(rendu)return;rendu=!0;fin(v,pq)}
  var u;
  try{u="/api/montage/duration?src="+
    encodeURIComponent(JSON.stringify(src||{}))}
  catch(e){rend(0,"src-illisible");return}
  if(!f){rend(0,"sans-reseau");return}
  if(tm)tm(function(){rend(0,"delai")},ms);
  try{
    f(u).then(function(rp){return rp&&rp.ok?rp.json():null})
        .then(function(j){var v=j?Number(j.dur):0;
          rend(isFinite(v)&&v>0?v:0,j?"mesure":"refus")})
        .catch(function(){rend(0,"erreur")})}
  catch(e2){rend(0,"erreur")}}

/* ══════════════════════════════════════════════════════════════════════════
   P12 — LE SON D'UN PLAN SUIT SA VIDÉO.
   Le rendu n'entre JAMAIS l'audio embarqué d'un clip vidéo dans le graphe
   ffmpeg (`[idx:v]` seul, montage_service._run) : sans clip jumeau sur la
   piste de dialogue, un plan parlant sort muet. La construction automatique
   pose ce jumeau (« … · son du plan ») ; les SEPT portes d'`addAsset`
   posaient un clip vidéo et rien d'autre. Ce bloc est le CŒUR PUR de la
   correction — chaque fonction se joue sous node, comme le reste :
     · dialogueTrack(ts) — la piste qui reçoit le son, JAMAIS une piste
       bouclée ; « a1 » par identifiant si aucun bus ne le dit ;
     · trackPlein(ts,id) / wantsTwin(kind,ts,id) — une vidéo posée sur une
       piste vidéo PLEIN CADRE reçoit un jumeau ; une incrustation (type
       « overlay » / « overlay/VFX »), non ;
     · overlayNote(kind,ts,id) — l'incrustation, DITE : la phrase de l'ajout
       quand aucun jumeau ne parle (rien d'extrait, le bouton) ;
     · audioOf / audioSet / audioForget — le CACHE des verdicts, par source ;
       c'est lui qui rend le rappel d'`addAsset` non récursif ;
     · askAudio(src,{done,fetch,timer,delai}) — la sonde (GET /has-audio),
       sur le motif EXACT d'askDur, cache compris ;
     · srcDurOr(kind,srcDur,verdict) — la durée que la sonde a rendue en
       prime, prise quand on ne la connaît pas encore ;
     · uniqueId / dedupeIds / seqMax — les identifiants de clips, UNIQUES ;
     · twinClip / twinPlan — le jumeau lui-même et la décision de le poser,
       avec sa note ;
     · extract / extractBtn — le bouton de l'inspecteur pour les plans DÉJÀ
       posés, même moteur. */

/* LA PISTE DE DIALOGUE. `pickTrack(ts,"audio")` n'est PAS la bonne réponse :
   c'est la première piste audio de l'ordre d'affichage — MESURÉ sur la
   sauvegarde du 04/09/2026 ([v1, a2, a1, a3, s1]) elle rend `a2`, la
   MUSIQUE, seule entrée bouclée et duckée du rendu. La cible est la piste de
   `bus:"dialogue"` (les pistes audio le portent), sinon `a1` par
   identifiant, sinon "" — et JAMAIS une piste `loop` : le rendu ignore les
   bornes du premier clip d'une piste bouclée et la joue d'un bout à l'autre
   du film (mesuré, voir dzmGapFate). Le genre se déduit de l'identifiant
   quand la piste ne le porte pas, comme pickTrack. */
function dzmDialogueTrack(ts){
  var list=Array.isArray(ts)?ts:[],i,t;
  for(i=0;i<list.length;i++){t=list[i];
    if(!t||!t.id||t.loop)continue;
    if(dzmKindOf(t.id,t.kind)==="audio"&&t.bus==="dialogue")return String(t.id)}
  for(i=0;i<list.length;i++){t=list[i];
    if(!t||String(t.id)!=="a1"||t.loop)continue;
    if(dzmKindOf(t.id,t.kind)==="audio")return "a1"}
  return ""}

/* P13 — CE QUE LA TRANSCRIPTION VA DÉPENSER, ET SUR QUOI. Le geste
   « Transcrire l'audio » envoie `src:null` : la route choisit elle-même les
   clips de la piste de dialogue (même loi que le rendu : bus « dialogue »,
   sinon a1, jamais une piste bouclée) porteurs d'une source, les transcrit
   un par un et décale leurs mots de `start − srcIn`. La pastille de coût
   doit annoncer CETTE dépense — la somme des `end − start` de ces clips —
   et non la durée du projet, qui compte aussi les images, la musique et
   les trous. PURE, jouée sous node. Rend {track, list, total, repli, step,
   dit} : `list` triée par `start` ({id, tr, label, start, dur}), `total`
   en secondes (millième), `repli` vrai quand aucun clip de dialogue ne
   porte de source et que la PREMIÈRE V1 porteuse en tient lieu (la route
   fait de même), `step` la ligne d'attente du tiroir, `dit` la phrase de
   l'infobulle — "" quand rien n'est à envoyer : l'appelant retombe alors
   sur la durée du projet, comme avant. Les clips sont ceux que le tiroir
   reçoit (`subsSrcClips` : {id, tr, src, name, start, end, srcIn?}) ;
   `name` est le libellé de la timeline, sinon la source est nommée par
   son champ. Sans pistes (`ts` absent ou vide) : les pistes par défaut,
   donc a1 — une liste PRÉSENTE sans piste de dialogue rend le repli V1.
   TOUR 1 (revue du 06/09) — LA DÉPENSE EST PAR FICHIER DISTINCT : la route
   ne transcrit qu'UNE fois un même fichier porté par deux clips (la lame
   coupe un clip en deux de même `src`), et le moteur reçoit le fichier
   ENTIER. Ce que le client en sait : la RÉUNION des fenêtres
   [srcIn, srcIn + dur] que ses clips lisent — deux moitiés font le tout,
   le même fichier posé deux fois compte une fois, un clip rogné reste une
   borne BASSE (la phrase le dit) ; `files` compte les fichiers distincts. */
function dzmSubsNum(v){var n=Number(v);return isFinite(n)?n:0}
function dzmSubsKey(s){return (s&&typeof s==="object")?dzmSrcKey(s):String(s)}
function dzmUnionLen(iv){
  var l=iv.slice().sort(function(p,q){return p[0]-q[0]}),t=0,a=0,b=0,open=!1,i;
  for(i=0;i<l.length;i++){
    if(!open||l[i][0]>b){if(open&&b>a)t+=b-a;a=l[i][0];b=l[i][1];open=!0}
    else if(l[i][1]>b)b=l[i][1]}
  if(open&&b>a)t+=b-a;
  return t}
function dzmSubsLabel(c){
  var s=c&&c.src;
  if(c&&(c.name||c.label))return String(c.name||c.label);
  if(s&&typeof s==="object")
    return String(s.audio||s.image||s.name||s.filename||s.file_path||s.job_id||"source");
  return s?String(s):"source"}
function dzmSubsSources(clips,ts){
  var cs=Array.isArray(clips)?clips:[],
      dial=dzmDialogueTrack(Array.isArray(ts)&&ts.length?ts:DZM_DEFAULT_TRACKS),
      list=[],v1=[],repli=!1,total=0,i,c,d;
  for(i=0;i<cs.length;i++){c=cs[i];
    if(!c||!c.src)continue;
    d=dzmSubsNum(c.end)-dzmSubsNum(c.start);
    if(!(d>0))continue;
    var row={id:c.id,tr:String(c.tr),label:dzmSubsLabel(c),
             start:dzmSubsNum(c.start),dur:Math.round(d*1000)/1000,
             key:dzmSubsKey(c.src),srcIn:Math.max(0,dzmSubsNum(c.srcIn))};
    if(dial&&row.tr===dial)list.push(row);
    else if(row.tr==="v1")v1.push(row)}
  var parStart=function(p,q){return p.start-q.start};
  list.sort(parStart);
  if(!list.length&&v1.length){v1.sort(parStart);list=[v1[0]];repli=!0}
  var parKey={},keys=[],k;
  for(i=0;i<list.length;i++){k=list[i].key;
    if(!parKey[k]){parKey[k]=[];keys.push(k)}
    parKey[k].push([list[i].srcIn,list[i].srcIn+list[i].dur])}
  for(i=0;i<keys.length;i++)total+=dzmUnionLen(parKey[keys[i]]);
  total=Math.round(total*1000)/1000;
  var piste=(repli?"v1":dial).toUpperCase(),n=list.length,
      noms=list.map(function(l){return l.label+" ("+dzmSecs(l.dur)+")"});
  return {track:dial,list:list,total:total,repli:repli,files:keys.length,
    step:!n?"envoi…":n===1?"envoi de "+list[0].label+"…"
        :"envoi de "+n+" clips de "+piste+"…",
    dit:!n?"":repli
      ?"Aucun clip de la piste "+(dial||"de dialogue").toUpperCase()+
       " ne porte de son : la vidéo "+noms[0]+" de V1 est envoyée entière, "+
       "ses répliques posées à son instant."
      :"Envoyé : "+n+" clip"+(n>1?"s":"")+
       (keys.length<n?" ("+keys.length+" fichier"+(keys.length>1?"s":"")+")":"")+
       " de la piste "+piste+" — "+noms.join(", ")+" — "+dzmSecs(total)+
       " de son, chaque réplique posée à l'instant de son clip. Chaque fichier "+
       "part entier chez le moteur : un clip rogné coûte la durée de son fichier."}}

/* PLEIN CADRE OU INCRUSTATION. Le `type` est celui de dzmSkin : « vidéo »
   pour V1, « overlay/VFX » pour la V2 historique, « overlay » pour toute
   piste vidéo neuve. Une piste sans `type` compte comme plein cadre — donc
   une liste NUE rend vrai pour TOUTE piste vidéo, v2 et v3 compris : le
   payload d'une sauvegarde les nomme SANS type (celle de l'utilisateur,
   06/09/2026, tracks [v3, v2, v1, …]). Ce n'est JAMAIS elle qui arrive
   ici : svmTracksFrom habille chaque piste par dzmSkin à l'apply (v2 →
   « overlay/VFX », v3 → « overlay », mesuré sous node) et le composant lit
   sa ref des pistes, posée par svmTracksOf(proj) à chaque rendu — habillée
   aussi. C'est cet
   habillage, pas cette fonction, qui tient l'exemption des incrustations ;
   le banc mesure les deux côte à côte (nue → vrai, habillée → faux). Une
   piste absente, ou d'un autre genre, rend faux. */
function dzmTrackPlein(ts,id){
  var list=Array.isArray(ts)?ts:[],t=null,i;
  for(i=0;i<list.length;i++)if(list[i]&&String(list[i].id)===String(id)){t=list[i];break}
  if(!t||dzmKindOf(t.id,t.kind)!=="video")return !1;
  var ty=String(t.type||"");
  return ty!=="overlay"&&ty!=="overlay/VFX"}
function dzmWantsTwin(kind,ts,id){return kind==="video"&&dzmTrackPlein(ts,id)}

/* L'INCRUSTATION, DITE. Une vidéo posée sur une piste d'incrustation n'est
   pas sondée (wantsTwin) — et l'ajout ne doit pas se taire pour autant. La
   porte « Envoyer vers → Montage » de la Bibliothèque vise « v2 » EN DUR
   (greffon libsend du bundle, `addAsset({job_id},…,"video",p.dur||0,"v2")`,
   1 occurrence, mesuré le 06/09/2026) ; sur la sauvegarde de l'utilisateur
   v2 EXISTE, habillée « overlay/VFX » : un kapwing_sample envoyé de là
   arrivait sur V2 sans son et sans un mot — sa remontée exacte. Rend la
   phrase que l'ajout concatène à sa note, ou "" quand il n'y a rien à dire :
   pas une vidéo (un son, une image), piste plein cadre (le jumeau parle
   alors, par twinPlan), piste absente ou d'un autre genre. Elle nomme la
   piste, dit que rien n'a été extrait et renvoie au bouton de
   l'inspecteur, avec sa cible quand le projet en a une. */
function dzmOverlayNote(kind,ts,id){
  if(kind!=="video")return "";
  var list=Array.isArray(ts)?ts:[],t=null,i;
  for(i=0;i<list.length;i++)if(list[i]&&String(list[i].id)===String(id)){t=list[i];break}
  if(!t||dzmKindOf(t.id,t.kind)!=="video"||dzmTrackPlein(ts,id))return "";
  var tr=dzmDialogueTrack(ts);
  return " Posé sur "+String(id).toUpperCase()+" (incrustation) : le son de "+
    "ce plan n'a PAS été extrait — sélectionnez-le puis « Extraire le son"+
    (tr?" → "+tr.toUpperCase():"")+" » dans l'inspecteur."}

/* ── P14 : « PISTE DE GENRE VIDÉO AUTRE QUE V1 » ──────────────────────────
   Le bundle codait « v2 » EN DUR à NEUF endroits (mesuré le 06/09/2026 en
   octets, « v2 » entre guillemets dans le code de l'écran, hors démo et
   table historique :
   aperçu, payload x/y/scale/rotate/motion_points, inspecteur Overlay,
   losanges de trajectoire, alignement 3×3, « position ici », poignées du
   lecteur, flèches et Échap du clavier) et le verrou de piste à QUATRE
   (l'état de la piste « .v2 » lu en dur). Dès que V2 existait, « vidéo »
   créait v3, et
   un clip posé dessus était un FANTÔME : invisible dans l'aperçu, sans
   inspecteur, sans poignée — et parti cover plein cadre au rendu, qui, lui,
   traite TOUTE piste vidéo ≠ v1 en incrustation (montage_service
   `_tracks_meta`, `kind == "video" and tid != "v1"`). La sauvegarde de
   l'utilisateur porte tracks [v3, v2, v1, …] : c'est exactement cette piste.
   Cette fonction est la règle du rendu, écrite une fois pour les treize
   portes. Le genre vient de la piste quand la liste la porte, de l'initiale
   de l'identifiant sinon (même loi que `trackKind` du bundle et que
   dzmKindOf) — une liste ABSENTE retombe donc sur l'initiale, et une piste
   absente de la liste aussi : un clip « v2 » d'un projet sans V2 reste
   visible dans l'aperçu, comme avant. `null`, "" et v1 rendent faux. */
function dzmIsOverlayTrack(trId,tracks){
  if(trId==null)return !1;
  var id=String(trId);
  if(!id||id==="v1")return !1;
  var list=Array.isArray(tracks)?tracks:[],t=null,i;
  for(i=0;i<list.length;i++)if(list[i]&&String(list[i].id)===id){t=list[i];break}
  return dzmKindOf(id,t?t.kind:void 0)==="video"}

/* L'ORDRE D'EMPILEMENT DE L'APERÇU (P14). Mesuré dans le bundle : la couche
   `ov` du lecteur ajoute chaque overlay actif par `appendChild` dans l'ordre
   de `Object.keys(act)` — l'ordre des CLIPS, jamais celui des pistes — et ne
   déplace jamais un enfant déjà là. Deux pistes d'incrustation se
   superposaient donc au hasard de la liste des clips, quand le rendu, lui,
   compose la piste listée le plus haut AU-DESSUS (`layer` : `reversed(ov)`).
   Cette fonction rend l'ordre d'AJOUT AU DOM — le plus bas d'abord, donc
   la piste la plus haute de la liste en dernier — pour les identifiants de
   clips donnés : rang de piste décroissant, puis l'ordre reçu (stable, sans
   compter sur le tri natif). Une piste absente de la liste passe SOUS
   toutes les autres ; une liste absente vaut les six pistes historiques ;
   un identifiant sans clip garde sa place. PURE. */
function dzmOverlayOrder(ids,clips,tracks){
  var list=(Array.isArray(tracks)&&tracks.length)?tracks:DZM_DEFAULT_TRACKS;
  var rang=Object.create(null),byId=Object.create(null),i;
  for(i=0;i<list.length;i++)
    if(list[i]&&list[i].id!=null&&!(String(list[i].id) in rang))rang[String(list[i].id)]=i;
  (Array.isArray(clips)?clips:[]).forEach(function(c){
    if(c&&c.id!=null&&!(String(c.id) in byId))byId[String(c.id)]=c});
  var dec=(Array.isArray(ids)?ids:[]).map(function(id,pos){
    var c=byId[String(id)],tr=(c&&c.tr!=null)?String(c.tr):"";
    return {id:id,r:(tr in rang)?rang[tr]:Infinity,pos:pos}});
  dec.sort(function(a,b){
    if(a.r===b.r)return a.pos-b.pos;
    return a.r>b.r?-1:1});
  return dec.map(function(e){return e.id})}

/* LE CACHE DES VERDICTS, par source. La clé est `JSON.stringify(src)` ; une
   source que JSON refuse (cycle) n'a pas de clé, et son verdict est connu
   d'avance : « illisible », donc pas de son — sans jamais rien demander.
   C'est ce qui ferme la récursion d'`addAsset` de ce côté-là aussi.
   Le verdict est {has_audio, dur, pourquoi} : `pourquoi` est la sortie de
   la sonde qui l'a produit (« mesure » quand le serveur a répondu, sinon
   « refus » / « delai » / « erreur » / « sans-reseau »), parce qu'un « pas
   de son » MESURÉ et un « pas de son » faute de réponse ne se disent pas
   avec les mêmes mots à l'écran. Les copies rendues sont fraîches : muter
   ce qu'on lit ne touche pas la mémoire. */
var DZM_AUDIO_CACHE=Object.create(null);
function dzmAudioKey(src){
  try{return JSON.stringify(src||{})}catch(e){return ""}}
function dzmAudioNorm(v){
  var o=v||{},d=Number(o.dur);
  return {has_audio:!!o.has_audio,dur:(isFinite(d)&&d>0)?Math.round(d*1000)/1000:0,
    pourquoi:String(o.pourquoi||"")}}
function dzmAudioOf(src){
  var k=dzmAudioKey(src);
  if(k==="")return {has_audio:!1,dur:0,pourquoi:"src-illisible"};
  var c=DZM_AUDIO_CACHE[k];
  return c?dzmAudioNorm(c):null}
function dzmAudioSet(src,v){
  var k=dzmAudioKey(src);
  if(k==="")return null;
  DZM_AUDIO_CACHE[k]=dzmAudioNorm(v);
  return dzmAudioNorm(DZM_AUDIO_CACHE[k])}
function dzmAudioForget(src){
  var k=dzmAudioKey(src);
  if(k!==""&&DZM_AUDIO_CACHE[k]){delete DZM_AUDIO_CACHE[k];return !0}
  return !1}

/* LA RAISON, EN FRANÇAIS. Les sorties de la sonde (« delai », « refus »,
   « erreur », « sans-reseau », « src-illisible ») sont des NOMS DE CODE —
   ce que le cache mémorise et ce que le banc épingle — pas des phrases ;
   les notes montrent ceci. Un jeton inconnu passe tel quel, jamais une
   chaîne vide. */
function dzmAudioPourquoi(pq){
  var p=String(pq||"");
  return p==="delai"?"délai dépassé":p==="refus"?"le serveur a refusé"
    :p==="erreur"?"erreur réseau":p==="sans-reseau"?"hors ligne"
    :p==="src-illisible"?"source illisible":(p||"sans réponse")}

/* LA SONDE. Motif EXACT d'askDur — `done(verdict, pourquoi)` appelée UNE
   SEULE FOIS quoi qu'il arrive, `fetch` et `timer` injectables (absent =
   celui de l'hôte, nul = « il n'y en a pas »), le délai et la réponse en
   course, `rendu` pour que le second arrivé ne fasse rien. Deux différences,
   et elles sont le point :
     · LE CACHE EST ÉCRIT AVANT `done`, sur TOUTE sortie — c'est le verrou :
       le rappel d'`addAsset` lit `audioOf(src)` non nul et ne redemande pas.
       Sans cette écriture, une sortie « delai » relancerait la sonde à
       chaque rappel, indéfiniment (le mode de panne que le banc [3-bis]
       reproduit pour askDur, et qu'il joue ici en supprimant l'écriture) ;
     · UNE SOURCE DÉJÀ SONDÉE RÉPOND SUR PLACE, sortie « cache », sans
       appel : un même fichier posé deux fois n'est sondé qu'une fois.
   Le verdict porte `dur` en prime (`/has-audio` la rend) : l'appelant s'en
   sert quand il ne connaît pas encore la longueur de la source, et
   s'épargne le second aller-retour d'askDur. */
function dzmAskAudio(src,o){
  o=o||{};
  var fin=typeof o.done==="function"?o.done:function(){};
  var f=o.fetch===void 0
    ?(typeof fetch==="function"?function(u){return fetch(u)}:null):o.fetch;
  var tm=o.timer===void 0
    ?(typeof setTimeout==="function"
        ?function(fn,ms){return setTimeout(fn,ms)}:null):o.timer;
  var ms=Number(o.delai);if(!isFinite(ms)||ms<=0)ms=DZM_DUR_DELAI;
  var k=dzmAudioKey(src);
  if(k===""){fin(dzmAudioOf(src),"src-illisible");return}
  var deja=dzmAudioOf(src);
  if(deja){fin(deja,"cache");return}
  var rendu=!1;
  function rend(v,pq){if(rendu)return;rendu=!0;
    fin(dzmAudioSet(src,{has_audio:v.has_audio,dur:v.dur,pourquoi:pq}),pq)}
  var u="/api/montage/has-audio?src="+encodeURIComponent(k);
  if(!f){rend({has_audio:!1,dur:0},"sans-reseau");return}
  if(tm)tm(function(){rend({has_audio:!1,dur:0},"delai")},ms);
  try{
    f(u).then(function(rp){return rp&&rp.ok?rp.json():null})
        .then(function(j){
          if(j&&typeof j.has_audio==="boolean")
            rend({has_audio:j.has_audio,dur:Number(j.dur)},"mesure");
          else rend({has_audio:!1,dur:0},"refus")})
        .catch(function(){rend({has_audio:!1,dur:0},"erreur")})}
  catch(e2){rend({has_audio:!1,dur:0},"erreur")}}

/* LA DURÉE RENDUE EN PRIME, prise SEULEMENT quand on ne la connaît pas
   encore — la règle « connaît-on la durée ? » reste celle de needDur, pas
   une seconde copie ; un verdict sans durée (0) laisse l'appelant aller la
   demander comme avant. */
function dzmSrcDurOr(kind,srcDur,v){
  if(!dzmNeedDur(kind,srcDur))return srcDur;
  var d=v?Number(v.dur):0;
  return (isFinite(d)&&d>0)?d:srcDur}

/* LES IDENTIFIANTS. `ovSeq` repart de zéro à chaque chargement et
   svmApplyProject reprend `c.id` tel quel : MESURÉ sur la sauvegarde de
   l'utilisateur (lecture seule, 06/09/2026), `v1u1_0` est porté par DEUX
   clips et `v1u2_0` par deux autres — supprimer l'un supprime l'autre
   (`c.id!==id`), et le second n'est jamais sélectionnable (`c.id===selId`).
     · uniqueId(clips, base) — `base` s'il est libre, sinon `base_2`,
       `base_3`… (le plus petit n libre, à partir de 2) ;
     · dedupeIds(clips) — le PREMIER porteur garde son id, les suivants sont
       renommés PAR uniqueId (le même, pas une seconde boucle de suffixe)
       contre TOUS les ids du tableau, ceux d'après compris, ET ceux que le
       renommage vient d'attribuer ; rend {clips, renamed:[{de, en}]},
       l'entrée n'est pas mutée ;
     · seqMax(clips) — le plus grand `u<n>` rencontré, pour re-semer ovSeq
       au-dessus de tout ce que la sauvegarde porte. */
function dzmUniqueId(clips,base){
  var b=String(base==null?"":base),taken=Object.create(null),i;
  var cs=Array.isArray(clips)?clips:[];
  for(i=0;i<cs.length;i++)if(cs[i]&&cs[i].id!=null)taken[String(cs[i].id)]=1;
  if(!taken[b])return b;
  var n=2;
  while(taken[b+"_"+n])n++;
  return b+"_"+n}
function dzmDedupeIds(clips){
  var cs=Array.isArray(clips)?clips:[],seen=Object.create(null),out=[],ren=[];
  /* `pool` est ce contre quoi uniqueId tranche : les clips d'entrée (ceux
     d'après compris), plus chaque id que le renommage attribue. */
  var pool=cs.slice(),i,c,id,nid;
  for(i=0;i<cs.length;i++){c=cs[i];
    if(!c||c.id==null){out.push(c);continue}
    id=String(c.id);
    if(!seen[id]){seen[id]=1;out.push(c);continue}
    nid=dzmUniqueId(pool,id);
    pool.push({id:nid});seen[nid]=1;
    ren.push({de:id,en:nid});
    out.push(Object.assign({},c,{id:nid}))}
  return {clips:out,renamed:ren}}
function dzmSeqMax(clips){
  var cs=Array.isArray(clips)?clips:[],mx=0,i,m;
  for(i=0;i<cs.length;i++){
    if(!cs[i]||cs[i].id==null)continue;
    m=/u(\d+)/.exec(String(cs[i].id));
    if(m&&Number(m[1])>mx)mx=Number(m[1])}
  return mx}

/* LE JUMEAU. Même source, mêmes bornes, même point d'entrée, sur la piste
   de dialogue ; libellé « … · son du plan », celui de la construction
   automatique. `null` s'il existe DÉJÀ sur cette piste un clip de même
   source (comparée par JSON des clés triées : {job_id} et {job_id} se
   valent quel que soit l'ordre d'écriture) qui CHEVAUCHE [start, end] —
   c'est le refus du doublon, et il vaut pour le bouton comme pour l'ajout.
   L'identifiant reprend celui du plan en changeant la piste (v1u3_0 →
   a1u3_0), puis passe par uniqueId contre les clips existants. */
function dzmSrcKey(src){
  var o=(src&&typeof src==="object")?src:{},ks=Object.keys(o).sort(),r={},i;
  for(i=0;i<ks.length;i++)r[ks[i]]=o[ks[i]];
  try{return JSON.stringify(r)}catch(e){return ""}}
function dzmTwinClip(clip,trId,clips){
  var c=clip||{},tr=String(trId||"");
  if(!tr||!c.src)return null;
  var st=Number(c.start)||0,en=Number(c.end)||0,k=dzmSrcKey(c.src);
  var cs=Array.isArray(clips)?clips:[],i,o;
  for(i=0;i<cs.length;i++){o=cs[i];
    if(!o||o.tr!==tr||!o.src||dzmSrcKey(o.src)!==k)continue;
    if((Number(o.start)||0)<en&&st<(Number(o.end)||0))return null}
  var id=String(c.id==null?"":c.id),base;
  if(!id)base=tr+"_son";
  else if(c.tr&&id.indexOf(String(c.tr))===0)base=tr+id.slice(String(c.tr).length);
  else base=tr+"_"+id;
  return {tr:tr,id:dzmUniqueId(cs,base),
    label:(c.label||"plan")+" · son du plan",
    start:st,end:en,src:c.src,srcIn:Number(c.srcIn)||0}}

/* LA DÉCISION, ET SA PHRASE. Rend {clip, tr, motif, note} : `clip` est le
   jumeau à poser (ou null), `motif` nomme la sortie, `note` est la phrase
   que l'appelant CONCATÈNE à la sienne — chaque sortie est DITE, jamais
   tue : le verdict « muet », « pas de piste de dialogue », « déjà là »,
   « verrouillée », « non sondée », et la pose elle-même, qui dit la piste et
   qu'« Annuler » retire les deux clips d'un coup (un seul pushHistory, un
   seul concat : l'appelant s'y engage, le banc [3-bis] le mesure). */
function dzmTwinPlan(neuf,ts,clips,v,locked){
  var c=neuf||{},L=c.label||"ce plan",tr=dzmDialogueTrack(ts),TR=tr.toUpperCase();
  function out(clip,motif,note){return {clip:clip,tr:tr,motif:motif,note:note}}
  if(!v)return out(null,"non-sonde"," Son du plan : la source n'a pas été "+
    "sondée — rien n'a été extrait. « Extraire le son » dans l'inspecteur "+
    "réessaie.");
  if(!v.has_audio){
    if(v.pourquoi==="mesure"){
      /* MESURÉ sans flux ET sans durée : ffprobe n'a rien pu lire — la
         source est vide ou illisible (le « demo complete videogen brute »
         de la sauvegarde de l'utilisateur fait 0 octet, mesuré le
         06/09/2026). Ce n'est PAS un plan muet, et le dire muet serait un
         mensonge : `dur` est le témoin qui sépare les deux. Une image rend
         0 aussi, mais une image n'est jamais sondée (wantsTwin exige le
         genre « video », extractBtn refuse `src.image`). */
      if(!(Number(v.dur)>0))return out(null,"non-sondable"," Son du plan : "+
        "la source n'a pas pu être sondée (aucune durée mesurable : fichier "+
        "vide ou illisible) — rien n'a été extrait. Vérifiez le fichier, ou "+
        "remplacez la source.");
      return out(null,"muet"," Cette vidéo n'a pas de piste audio : rien "+
        "n'a été extrait.")}
    return out(null,"non-sonde"," Son du plan : la sonde n'a pas abouti ("+
      dzmAudioPourquoi(v.pourquoi)+") — rien n'a été extrait, et le rendu "+
      "n'emporte JAMAIS l'audio embarqué d'un plan. « Extraire le son » dans "+
      "l'inspecteur réessaie.")}
  if(!tr)return out(null,"sans-piste"," Cette vidéo a du son, mais ce projet "+
    "n'a pas de piste de dialogue : le rendu la jouera MUETTE. Ajoutez une "+
    "piste avec « + piste audio », puis « Extraire le son » dans "+
    "l'inspecteur.");
  if(typeof locked==="function"&&locked(tr))return out(null,"verrou"," Piste "+
    TR+" verrouillée : le son de « "+L+" » n'a PAS été extrait — "+
    "déverrouillez-la, puis « Extraire le son » dans l'inspecteur.");
  var j=dzmTwinClip(c,tr,clips);
  if(!j)return out(null,"doublon"," Son du plan : déjà présent sur "+TR+
    " (même source, même plage) — pas de second exemplaire.");
  return out(j,"pose"," Son du plan extrait sur "+TR+" (« "+j.label+" », "+
    "mêmes bornes, même source) : « Annuler » (Ctrl+Z) retire les DEUX clips "+
    "d'un coup.")}

/* LE BOUTON DES PLANS DÉJÀ POSÉS — même moteur : la sonde (cache compris),
   twinClip, refus DIT. `o` est l'hôte : {tracks, clips (un THUNK : les clips
   au moment de la réponse, pas ceux du clic), locked(trId), pushHistory,
   setClips, setDirty, note, ask}. `ask` est injectable pour le banc ; l'hôte
   n'en passe pas et c'est askAudio qui sonde. Un verdict en cache qui n'est
   PAS une mesure (délai, erreur…) est OUBLIÉ avant de redemander : un clic
   est un geste, il a droit à une vraie seconde sonde — là où le rappel
   automatique d'addAsset, lui, ne doit jamais reboucler.
   ÉCART AU PLAN, DÉCLARÉ : le plan écrivait extractBtn(sel, ts, clips,
   onClick) « sur le motif de replaceBtn/revertBtn », qui reçoivent
   (sel, rappel). Ici c'est (sel, hôte), parce que le bouton a besoin des
   PISTES pour nommer sa cible dans son libellé, et des CLIPS AU MOMENT DE
   LA RÉPONSE (le thunk) et non de ceux du clic — replaceBtn n'a besoin ni
   de l'un ni de l'autre. Le clip visé est RELU dans ces clips frais :
   déplacé entre le clic et la réponse, le jumeau prend ses bornes du
   moment, pas celles du clic. Une image posée sur une piste vidéo
   (`src.image`, deux portes du bundle le font) n'a rien à extraire : refus
   avant toute sonde, et le bouton ne se montre pas. */
function dzmExtract(sel,o){
  o=o||{};
  var note=typeof o.note==="function"?o.note:function(){};
  var c=sel||{},L=c.label||"ce plan";
  if(!c.src){note("Aucun plan à source n'est sélectionné : rien à extraire.");
    return !1}
  if(c.src.image){note("« "+L+" » est une image : elle n'a pas de son à "+
    "extraire.");return !1}
  var ts=dzmTsOr(o.tracks),tr=dzmDialogueTrack(ts),TR=tr.toUpperCase();
  if(!tr){note("Ce projet n'a pas de piste de dialogue : le son de « "+L+
    " » n'a pas été extrait. Ajoutez une piste avec « + piste audio », puis "+
    "recommencez.");return !1}
  if(typeof o.locked==="function"&&o.locked(tr)){note("Piste "+TR+
    " verrouillée — déverrouillez-la pour y extraire le son de « "+L+" ».");
    return !1}
  var v0=dzmAudioOf(c.src);
  if(v0&&v0.pourquoi!=="mesure"&&v0.pourquoi!=="src-illisible")dzmAudioForget(c.src);
  var ask=typeof o.ask==="function"?o.ask:dzmAskAudio;
  ask(c.src,{done:function(v,pq){
    if(!v||!v.has_audio){
      note(!v||v.pourquoi!=="mesure"
        ?"La sonde audio de « "+L+" » n'a pas abouti ("+
          dzmAudioPourquoi((v&&v.pourquoi)||pq)+") : rien n'a été posé. "+
          "Réessayez dans un instant."
        :!(Number(v.dur)>0)
        ?"« "+L+" » n'a pas pu être sondé (aucune durée mesurable : fichier "+
          "vide ou illisible) : rien à extraire. Vérifiez le fichier, ou "+
          "remplacez la source."
        :"« "+L+" » n'a pas de piste audio : rien à extraire.");return}
    var cs=(typeof o.clips==="function"?o.clips():o.clips)||[],i,la=null;
    for(i=0;i<cs.length;i++)if(cs[i]&&cs[i].id===c.id){la=cs[i];break}
    if(!la){note("« "+L+" » n'est plus dans la timeline : rien n'a été "+
      "posé.");return}
    /* `la`, le clip FRAIS — ses bornes du moment, pas celles du clic */
    var j=dzmTwinClip(la,tr,cs);
    if(!j){note("Le son de « "+L+" » est déjà sur "+TR+" (même source, "+
      "même plage) : rien n'a été ajouté.");return}
    if(typeof o.pushHistory==="function")o.pushHistory();
    if(typeof o.setClips==="function")o.setClips(cs.concat([j]));
    if(typeof o.setDirty==="function")o.setDirty(!0);
    note("Son de « "+L+" » extrait sur "+TR+" : « "+j.label+" », "+
      dzmSecs(j.end-j.start)+", mêmes bornes et même source que le plan. "+
      "« Annuler » (Ctrl+Z) le retire.")}});
  return !0}
/* Visible pour TOUT clip vidéo porteur d'une source — V1, V2, V3… — parce que
   c'est le seul chemin qui rend son son à un plan DÉJÀ posé (celui de
   l'utilisateur, posé sur V1 avant que l'ajout ne sache extraire). Le
   libellé nomme la piste visée ; sans piste de dialogue il le dit, et le
   clic explique. */
function dzmExtractBtn(sel,o){
  if(!sel||!sel.src||sel.src.image||dzmKindOf(sel.tr)!=="video")return null;
  var tr=dzmDialogueTrack(dzmTsOr(o&&o.tracks)),TR=tr.toUpperCase();
  var L=sel.label||"ce plan";
  return r.jsx("button",{className:"svm-secbtn dzm-extract",
    title:(tr
      ?"Poser sur "+TR+" (piste de dialogue) un clip « "+L+" · son du plan » : "+
       "même source, mêmes bornes, même point d'entrée. Le rendu n'emporte "+
       "JAMAIS l'audio embarqué d'un plan vidéo — sans ce clip, ce plan "+
       "sort muet. Refusé si la source n'a pas de piste audio ou si ce son "+
       "est déjà sur "+TR+" à cette plage. « Annuler » (Ctrl+Z) le retire."
      :"Ce projet n'a pas de piste de dialogue : ajoutez une piste avec "+
       "« + piste audio » pour pouvoir extraire le son de ce plan."),
    "aria-label":"Extraire le son de "+L+(tr?" vers "+TR:""),
    onClick:function(){dzmExtract(sel,o)},
    children:tr?"Extraire le son → "+TR:"Extraire le son (aucune piste de dialogue)"},
    "dzmextr")}

/* ══════════════════════════════════════════════════════════════════════════
   BARRE D'OUTILS DÉPORTABLE DE LA TIMELINE — étapes 1, 2 et 3 du §9 du
   handoff « Barre Outils Flottante » (« Design d'icônes applicatives/
   design_handoff_barre_outils/design.md »). Étape 1 : les tokens, dans les
   TROIS feuilles. Étape 2 : les dix tracés du §3. Étape 3 : le bouton
   d'action du §2.3, celui qui se répète neuf fois.

   RIEN DE CE BLOC N'EST MONTÉ À L'ÉCRAN. Les étapes 4 à 8 — la barre, son
   onglet, le déport, le retrait des neuf contrôles du bandeau fixe, le
   câblage — ne sont PAS ici. Ce qui suit est appelable et rien d'autre :
   aucun pixel de l'application ne bouge tant qu'une section du patcher n'en
   appelle une fonction, et aucune ne le fait aujourd'hui.

   ÉCART DE LIVRAISON, DÉCLARÉ PLUTÔT QUE TU. Le handoff dit « Livraison :
   src/icons/toolbar/*, un composant par icône ». C'est IMPOSSIBLE ici, et
   c'est mesuré : frontend/src ne porte AUCUNE classe svm-*, l'écran Montage
   n'y existe pas — il vit dans le bundle construit et dans les patchs. Une
   reconstruction Vite rendrait un bundle SANS l'écran Montage et effacerait
   la chaîne. Le design ne change pas ; son véhicule si.

   LES TRACÉS SONT GARDÉS TELS QUELS, EN CHAÎNE, et non retranscrits en
   appels `r.jsx`. Le handoff dit « Les tracés SVG sont donnés intégralement
   et doivent être repris tels quels » : la chaîne EST le texte du §3, au
   caractère près, et c'est ELLE qui fait foi. `dzmTbParse` la traduit une
   fois au chargement — pure, donc jouable sous node — et `dzmTbSerial` fait
   le chemin inverse et doit rendre la chaîne de départ. C'est le contrôle À
   DEUX FACES qui interdit qu'une retranscription silencieuse s'installe :
   une virgule perdue dans un `d=` cesserait d'être invisible.

   AUCUNE COULEUR N'EST ÉCRITE ICI. La teinte du groupe arrive par la classe
   `dzm-g-<groupe>`, que montage.css traduit en `--grp` ; le JS ne fabrique
   donc jamais un nom de variable CSS à partir d'une entrée. C'est aussi ce
   qui rend un groupe inconnu inoffensif : pas de classe, pas de teinte, et
   la ligne du banc le dit. */
var DZM_TB_TRACES={
  "piste-video":
    '<rect x="2.6" y="4.2" width="18.8" height="5.6" opacity=".34"/><rect x="2.6" y="11.6" width="10.4" height="5.6"/><path d="M17 12.6h1.9V15h2.4v1.9h-2.4v2.4H17v-2.4h-2.4V15H17z"/>',
  "piste-audio":
    '<rect x="2.6" y="10.2" width="2.2" height="3.6" opacity=".45"/><rect x="6.2" y="6.6" width="2.2" height="10.8"/><rect x="9.8" y="8.8" width="2.2" height="6.4"/><rect x="13.4" y="4.6" width="2.2" height="15" opacity=".45"/><path d="M17.6 12.6h1.9V15h2.4v1.9h-2.4v2.4h-1.9v-2.4h-2.4V15h2.4z"/>',
  "bibliotheque":
    '<path d="M12 2.8 21 7.2 12 11.6 3 7.2z"/><path d="M12 13.6 4.6 10l-1.6.8L12 15.2l9-4.4-1.6-.8zM12 18.2 4.6 14.6l-1.6.8L12 19.8l9-4.4-1.6-.8z" opacity=".42"/>',
  "couleur":
    '<rect x="2.8" y="7.4" width="18.4" height="6.2" opacity=".34"/><rect x="2.8" y="7.4" width="8.8" height="6.2"/><rect x="2.8" y="16.4" width="4.8" height="3.6"/><rect x="9.6" y="16.4" width="4.8" height="3.6" opacity=".5"/><rect x="16.4" y="16.4" width="4.8" height="3.6" opacity=".34"/>',
  "rebond":
    '<rect x="2.8" y="16.8" width="18.4" height="4.2" opacity=".34"/><rect x="3.2" y="8.6" width="4.6" height="4.6"/><rect x="9.7" y="3.4" width="4.6" height="4.6"/><rect x="16.2" y="8.6" width="4.6" height="4.6" opacity=".55"/>',
  "glow":
    '<rect x="6.6" y="9.4" width="10.8" height="5.2"/><rect x="11.2" y="2.2" width="1.6" height="4.2" opacity=".45"/><rect x="11.2" y="17.6" width="1.6" height="4.2" opacity=".45"/><rect x="2.2" y="11.2" width="4.2" height="1.6" opacity=".45"/><rect x="17.6" y="11.2" width="4.2" height="1.6" opacity=".45"/>',
  "emoji":
    '<rect x="3" y="3" width="18" height="18" opacity=".3"/><rect x="7.4" y="7.6" width="2.8" height="3.6"/><rect x="13.8" y="7.6" width="2.8" height="3.6"/><rect x="7.4" y="14.2" width="9.2" height="2.6"/>',
  "texte":
    '<rect x="3.4" y="3.8" width="17.2" height="3.4"/><rect x="10.3" y="7.2" width="3.4" height="11.6"/><rect x="5.2" y="20.2" width="13.6" height="1.8" opacity=".34"/>',
  "projets":
    '<rect x="6" y="3" width="15.4" height="11.6" opacity=".3"/><path d="M2.6 6.2h6.2l1.7 2.1h11.1v12.5H2.6z"/>',
  "poignee":
    '<rect x="8" y="4" width="2.6" height="2.6"/><rect x="13.4" y="4" width="2.6" height="2.6"/><rect x="8" y="10.7" width="2.6" height="2.6"/><rect x="13.4" y="10.7" width="2.6" height="2.6"/><rect x="8" y="17.4" width="2.6" height="2.6"/><rect x="13.4" y="17.4" width="2.6" height="2.6"/>',
  /* P14 (06/09/2026) — la dixième icône, déclarée dans le §3 du handoff
     sous son écart daté, et APRÈS la poignée parce que c'est l'ordre du §3
     (le banc rapproche les deux listes dans l'ordre) : le cadre en opacité
     de support, le cadre intérieur plein décalé en bas à droite, et la
     croix d'ajout de « piste vidéo », reprise telle quelle. */
  "piste-incrust":
    '<rect x="2.6" y="4.2" width="13.6" height="10.4" opacity=".34"/><rect x="8.4" y="8.4" width="6" height="4.2"/><path d="M17 12.6h1.9V15h2.4v1.9h-2.4v2.4H17v-2.4h-2.4V15H17z"/>',
};
/* Les cinq groupes du §2.4, dans l'ordre du §2.4. Le rouge n'y est pas :
   il est réservé au destructif, qui reste dans le bandeau fixe. */
var DZM_TB_GROUPES=["pistes","biblio","mot","ajouts","projets"];
/* Grille 24 × 24, rendu 18 px (§3). Le grip fait 14 px (§2.2a) : il est
   passé en `size`, il n'a pas sa propre constante. */
var DZM_TB_PX=18;
var DZM_TB_PX_GRIP=14;
function dzmTbCamel(n){return String(n).replace(/-([a-z])/g,
  function(m,c){return c.toUpperCase()})}
function dzmTbKebab(n){return String(n).replace(/[A-Z]/g,
  function(c){return "-"+c.toLowerCase()})}
/* Le tracé du §3 → une liste [balise, propriétés]. Les noms d'attributs
   passent en camelCase parce que c'est ce que React attend : aucun des dix
   tracés n'en porte de composé aujourd'hui (x, y, width, height, opacity,
   d), mais un `fill-rule` posé demain serait muet sans cette ligne — React
   ignore une propriété qu'il ne reconnaît pas sur un élément SVG. */
function dzmTbParse(t){
  var out=[],re=/<([a-zA-Z]+)((?:\s+[a-zA-Z-]+="[^"]*")*)\s*\/>/g,m,ra,a,p;
  while((m=re.exec(String(t||"")))!==null){
    p={};ra=/([a-zA-Z-]+)="([^"]*)"/g;
    while((a=ra.exec(m[2]))!==null)p[dzmTbCamel(a[1])]=a[2];
    out.push([m[1],p]);}
  return out}
/* L'AUTRE FACE. Elle rend le tracé d'origine, caractère pour caractère —
   l'ordre des clés d'un objet JS suit l'insertion tant qu'aucune n'est un
   entier, et aucune ne l'est ici. Le banc compare les dix allers-retours au
   texte du §3 lu DANS design.md : ni la couche ni le banc ne recopient les
   tracés, ils les lisent au même endroit. */
function dzmTbSerial(ns){
  return (ns||[]).map(function(e){
    var s="<"+e[0],k;
    for(k in e[1])if(Object.prototype.hasOwnProperty.call(e[1],k))
      s+=" "+dzmTbKebab(k)+'="'+e[1][k]+'"';
    return s+"/>"}).join("")}
var DZM_TB_ICONS=(function(){
  var o={},k;
  for(k in DZM_TB_TRACES)
    if(Object.prototype.hasOwnProperty.call(DZM_TB_TRACES,k))
      o[k]=dzmTbParse(DZM_TB_TRACES[k]);
  return o})();
/* L'icône. `fill="currentColor"` et RIEN d'autre : la couleur vient du
   bouton, jamais de l'icône (§3). `aria-hidden` parce que le sens est porté
   par le libellé et l'`aria-label` du bouton — une icône annoncée en plus
   ferait dire deux fois la même chose au lecteur d'écran. */
function DzmTbIcon(o){
  o=o||{};
  var n=DZM_TB_ICONS[o.name];
  if(!n)return null;
  var px=Number(o.size);if(!isFinite(px)||px<=0)px=DZM_TB_PX;
  return r.jsx("svg",{className:"dzm-tbi",viewBox:"0 0 24 24",
    fill:"currentColor",width:px,height:px,"aria-hidden":!0,
    focusable:"false",
    children:n.map(function(e,i){return r.jsx(e[0],e[1],"t"+i)})},
    o.k||("tbi-"+o.name))}
/* ── LE BOUTON D'ACTION (§2.3) — l'unité qui se répète neuf fois ───────────
   UN SEUL COMPOSANT, deux propriétés qui décident de tout : `group` (la
   famille, donc la teinte) et `toggle` (bascule ou action simple).

   `active` n'est LU que si `toggle` : une action simple n'a pas d'état, et
   un appelant qui lui en passerait un par erreur ne doit pas peindre un
   bouton allumé qui ne s'éteindrait jamais. Trois valeurs : `true` (allumé),
   `"mixed"` (sélection hétérogène — bordure teintée, fond transparent,
   §4.3), tout le reste = éteint.

   `aria-pressed` n'est posé QUE sur les bascules, et il porte "mixed" tel
   quel : c'est la valeur ARIA de l'état indéterminé, et sans elle une
   sélection hétérogène s'annoncerait « non pressé », c'est-à-dire faux.

   LE LIBELLÉ EST TOUJOURS DANS LE DOM, même masqué : le §2.3 dit
   « masquables, pas supprimables ». C'est montage.css qui le cache
   (`--lbl:none`), et `title` comme `aria-label` retombent sur lui — d'où
   l'interdiction du §2.3 (« Ne pas livrer un mode compact sans infobulles »)
   tenue par construction, sans que l'appelant ait à y penser.

   L'ÉTAT ÉTEINT (`disabled`) et l'état indéterminé sont RENDUS ici ; QUAND
   les poser est le câblage du §6 et de l'étape 7, qui n'est pas de ce lot.
   Ils sont là parce que le §2.3 dit « la faire juste une fois » : livrer une
   bascule qui ne sait pas se peindre éteinte obligerait à rouvrir le seul
   composant que le handoff demande de ne pas rouvrir. */
function DzmToolBtn(o){
  o=o||{};
  var g=DZM_TB_GROUPES.indexOf(o.group)>=0?o.group:"";
  var tog=o.toggle===!0;
  var etat=tog?o.active:!1;
  var on=etat===!0,mix=etat==="mixed";
  var dis=o.disabled===!0;
  var lbl=o.label||"";
  var cls="dzm-tbb";
  if(g)cls+=" dzm-g-"+g;
  if(o.solo===!0)cls+=" dzm-solo";
  if(on)cls+=" dzm-on";
  if(mix)cls+=" dzm-mix";
  var p={type:"button",className:cls,
    title:o.title||lbl,"aria-label":o.aria||lbl,disabled:dis,
    onClick:function(){if(!dis&&typeof o.onAct==="function")o.onAct()},
    children:[DzmTbIcon({name:o.icon,k:"i"}),
      r.jsx("span",{className:"dzm-tbl",children:lbl},"l")]};
  if(g)p["data-grp"]=g;
  if(tog)p["aria-pressed"]=mix?"mixed":(on?"true":"false");
  /* ÉTAPE 8 — LE `tabindex` ROVING (§4.5), EN TROIS ÉTATS ET PAS DEUX :
     `true` = le point d'entrée (0), `false` = dans le groupe mais hors du
     parcours (−1), ABSENT = aucun attribut, donc le comportement natif du
     `<button>`. Le troisième état existe parce que ce composant est public
     et testé : un appelant qui monte un bouton HORS d'une barre roving ne
     doit pas hériter d'un `-1` qui le sortirait du parcours sans raison. */
  if(o.tab===!0)p.tabIndex=0;
  else if(o.tab===!1)p.tabIndex=-1;
  return r.jsx("button",p,o.k||("tbb-"+(o.icon||g||"x")))}
/* ── ÉTAPES 4, 5, 7 ET 8 DU §9 : LA BARRE, SON ONGLET, SON DÉPORT, SON
   CÂBLAGE, SON CLAVIER ────────────────────────────────────────────────────
   Géométrie (§2.1, §2.2), contenu verbatim (§2.4), ouverture et repli (§4.1),
   le déport (§4.2), de §4.4 LES DEUX CLÉS `open` et `offset`, le câblage
   du §6 EN ENTIER, et depuis l'étape 8 le §4.5 : `role="toolbar"`, le
   `tabindex` roving, Échap, le raccourci et le focus à l'ouverture. Le
   retrait des neuf contrôles du bandeau (§5) est l'étape 6.
   L'ORDRE DES ÉTAPES 6 ET 7 EST INVERSÉ PAR RAPPORT AU §9, et c'est une
   décision, pas un oubli : `emoji` et `projets` étaient ÉTEINTS dans la
   barre à l'étape 4. Retirer d'abord leurs contrôles du bandeau les aurait
   rendus inatteignables PARTOUT — exactement ce que le §9 s'interdit
   (« ne pas laisser l'application dans un état où les actions ne sont
   accessibles nulle part »).

   ── LA DUPLICATION EST TRANSITOIRE, ET C'EST DIT ICI ──
   Les neuf actions existent AUX DEUX ENDROITS tant que l'étape 6 n'a pas
   retiré celles du bandeau fixe. Le §5.1 l'interdit à terme (« deux sources
   de vérité pour l'état des bascules ») ; le §9 l'impose transitoirement.
   C'est un reste ASSUMÉ, et l'étape 6 le solde. AUCUN ÉTAT N'EST DOUBLÉ
   pour autant : `wordAnim` vit dans `proj.subsStyle` et l’état du panneau
   « Texte » dans l'écran — la chip, le bouton du bandeau et la barre les
   LISENT tous les trois, sans en garder de copie. La seule chose réellement
   doublée est l'ÉTAT D'ATTENTE de la requête emoji, un booléen par porte :
   deux clics simultanés partent en deux requêtes, qui ne se détruisent pas
   mais posent deux fois les mêmes clips. L'étape 6 referme une des portes.

   ── AUCUN BOUTON VIVANT QUI NE FAIT RIEN ──
   LES NEUF BOUTONS SONT CÂBLÉS sur une action qui EXISTAIT — la barre est un
   nouveau point d'entrée, pas une nouvelle implémentation (§6). Les deux qui
   avaient résisté à l'étape 4 tenaient chacun à un état enfermé dans son
   composant, et l'étape 7 a ouvert la porte SANS déplacer l'état :
     • `emoji` — son `fetch` est sorti du bouton (`dzmEmojiGo`, au premier
       niveau) ; l'attente, elle, reste à chaque appelant, parce qu'un hook
       ne se partage pas.
     • `projets` — le popover garde son ouverture chez lui et reçoit une
       DEMANDE (`openReq`, un compteur) ; c'est le seul moyen d'ouvrir sans
       lutter contre son propre « clic dehors », qui se déclenche justement
       sur le bouton de la barre.
   Un bouton reste ÉTEINT quand l'écran ne lui a pas donné de quoi agir, ou
   pendant l'attente d'`emoji` — et son `title` dit alors laquelle des deux
   situations est en cours. */

/* LA CLÉ DE PERSISTANCE — ÉCART DÉCLARÉ, DANS LES DEUX SENS.
   Le §4.4 demande `deepotus.toolbar.open`. LA MAISON dit autre chose, et
   c'est mesuré le 05/09/2026 sur le bundle et les couches : VINGT-CINQ clés
   `dz_*` distinctes, dont les quatre de cet écran (`dz_svm_theme`,
   `dz_svm_keymap`, `dz_narr_open`, `dz_hints_off`) — et TROIS clés
   `deepotus.*` seulement (`deepotus.motion.reduced`, `deepotus.motion.halo`,
   `deepotus.provider_defaults`), qui vivent toutes les trois dans
   frontend/src, hors de portée de cette chaîne de patchs.
   ON SUIT LA MAISON, et le §4.4 lui-même le demande : « dans le même espace
   de nommage que les panneaux existants ». L'espace des panneaux existants
   de cet écran est `dz_*`. `deepotus.toolbar.open` aurait fabriqué la
   quatrième clé d'un espace que la chaîne n'emploie nulle part.
   La FORME suit `dz_narr_open` au caractère près : "1" / "0", lecture et
   écriture sous try/catch (localStorage lève en navigation privée et sous
   une politique de site restrictive).
   LE DÉFAUT EST « OUVERTE » DEPUIS L'ÉTAPE 6, et c'est un RENVERSEMENT
   ASSUMÉ : l'étape 4 avait posé « repliée », mais elle en avait écrit la
   raison — « tant que l'étape 6 n'a pas retiré les neuf contrôles, ouvrir
   par défaut montrerait une barre qui double une rangée déjà là ». Cette
   étape-ci retire les neuf. La raison a disparu, et son contraire est
   arrivé : replié par défaut, un utilisateur qui n'a jamais vu l'onglet
   n'aurait AUCUN moyen d'ajouter une piste, de lier la Bibliothèque ni
   d'ouvrir ses projets — le §9 s'interdit précisément cet état (« ne pas
   laisser l'application dans un état où les actions ne sont accessibles
   nulle part »). Le prix est de 74 px posés sur la règle au premier
   chargement, que le `×` de la barre reprend en un clic, et ce clic est
   MÉMORISÉ.
   LA MÉMOIRE EST PRÉSERVÉE DANS LES DEUX SENS : la clé garde "1"/"0", donc
   qui a déjà replié reste replié (valeur "0") et qui a ouvert reste ouvert.
   Seule l'ABSENCE de clé change de sens. Et un magasin en panne (navigation
   privée, politique de site) rend désormais « ouverte » plutôt que
   « repliée » : sans mémoire, mieux vaut montrer les neuf actions que les
   cacher pour toujours. */
var DZM_TB_CLE_OPEN="dz_svm_tb_open";
var DZM_TB_ID="dzm-toolbar";
/* Le magasin est PARAMÉTRABLE pour que le banc puisse en fournir un faux :
   sous node il n'y a pas de localStorage, et une fonction qu'on ne peut pas
   jouer n'est pas mesurée. Sans argument, c'est celui du navigateur. */
function dzmTbStore(){
  try{return (typeof window!=="undefined"&&window.localStorage)||null}
  catch(e){return null}}
function dzmTbOpenGet(st){
  var s=st||dzmTbStore();
  try{return !s||s.getItem(DZM_TB_CLE_OPEN)!=="0"}catch(e){return !0}}
/* REND CE QU'ELLE A ÉCRIT : l'appelant pose l'état React avec la valeur que
   cette fonction rend, donc un magasin en panne ne désynchronise pas
   l'écran de lui-même — il perd la mémoire, pas la bascule. */
function dzmTbOpenSet(v,st){
  var s=st||dzmTbStore();
  try{if(s)s.setItem(DZM_TB_CLE_OPEN,v?"1":"0")}catch(e){}
  return !!v}

/* LE CONTENU DU §2.4, VERBATIM. Cinq groupes dans l'ordre du tableau, les
   en-têtes tels qu'écrits (§2.2b : « Libellés verbatim »), le suffixe
   « — sélection » de MOT, et les neuf libellés de bouton. Le banc compare
   cette table au §2.4 lu DANS design.md : ni la couche ni le banc ne
   recopient le tableau deux fois, ils le lisent au même endroit — même
   protocole que les dix tracés du §3.
   Les clés d'icône sont celles du §3 ; le banc vérifie que les neuf y sont,
   une fois chacune, et que la dixième (`poignee`) n'est PAS un bouton. */
var DZM_TB_PLAN=[
  /* P14 (06/09/2026) — TROIS boutons dans PISTES, écart déclaré dans le
     handoff (§2.4, §3 « piste incrustation ») : « vidéo » crée une piste
     plein cadre, « incrust. » une piste d'incrustation. Mesuré : au rendu
     toute piste vidéo ≠ V1 est une incrustation, et l'utilisateur doit
     pouvoir choisir. */
  {g:"pistes",t:"PISTES",type:"action",
   btns:[{i:"piste-video",l:"vidéo"},{i:"piste-incrust",l:"incrust."},
         {i:"piste-audio",l:"audio"}]},
  {g:"biblio",t:"BIBLIOTHÈQUE",type:"ouvre un panneau",
   btns:[{i:"bibliotheque",l:"lier"}]},
  {g:"mot",t:"MOT",suf:"— sélection",type:"bascules",
   btns:[{i:"couleur",l:"couleur"},{i:"rebond",l:"rebond"},{i:"glow",l:"glow"}]},
  {g:"ajouts",t:"AJOUTS",type:"outils de placement",
   btns:[{i:"emoji",l:"emoji"},{i:"texte",l:"texte"}]},
  {g:"projets",t:"PROJETS",type:"ouvre un panneau",
   btns:[{i:"projets",l:"projets"}]}];

/* `dzmTbEtape7` VIVAIT ICI — la phrase des deux boutons qui n'étaient pas
   câblés. L'étape 7 a câblé les neuf : plus personne ne l'appelait, et une
   fonction morte injectée dans le bundle est une fonction morte de plus.
   Retirée, pas commentée. Ce qu'elle disait est mesuré à l'envers désormais :
   le banc exige qu'AUCUN titre de la barre ne nomme encore une étape à
   venir. */
var DZM_TB_SANS_HOTE="Action non fournie à la barre par l'écran qui la "+
  "monte — il n'y a rien à déclencher.";
/* LA POIGNÉE PARLE DES TROIS GESTES qu'elle accepte, et de la seule règle
   que l'utilisateur peut constater : la barre ne sort pas. */
var DZM_TB_T_GRIP="Poignée — glisser pour déplacer la barre d'outils ; "+
  "flèches pour la déplacer de 8 px, Maj + flèches de 1 px. Elle reste "+
  "entièrement dans la timeline et la prévisualisation, à 8 px des bords, "+
  "et s'aimante aux bords et à la tête de lecture au relâchement.";
var DZM_TB_A_GRIP="Déplacer la barre d'outils";
/* DEUX PHRASES, PAS UN BOUTON ÉTEINT (§4.2 : « il ne doit jamais être
   masqué »). Il reste CLIQUABLE même quand il n'a rien à recentrer : c'est
   le filet de sécurité du déport, et un filet qui se désarme tout seul dès
   que l'état le croit inutile n'en est plus un. Son titre dit laquelle des
   deux situations est en cours. */
var DZM_TB_T_RECENTRER="Recentrer la barre d'outils — la ramène sous le "+
  "bandeau de transport, à sa place d'origine.";
var DZM_TB_T_RECENTREE="Recentrer la barre d'outils — elle est déjà à sa "+
  "place d'origine.";
var DZM_TB_T_REPLIER="Replier la barre d'outils sur son onglet.";
var DZM_TB_T_TEXTE="Ouvrir ou fermer le panneau « Texte » — la narration "+
  "mot par mot dans la colonne de droite.";
/* L'ÉCART DU GROUPE MOT, DIT À L'UTILISATEUR ET PAS SEULEMENT EN COMMENTAIRE.
   Le §4.3 veut trois bascules INDÉPENDANTES et CUMULABLES, calculées depuis
   la sélection de mots des sous-titres. Cette base n'a NI sélection de mot NI
   champ `words[].fx` : elle a UN champ `proj.subsStyle.wordAnim` à trois
   valeurs exclusives, qui vaut pour toute la piste S1 — mesuré, c'est ce que
   la chip du bandeau écrit et ce que le rendu ASS lit. Câbler les trois
   boutons sur ce champ donne trois boutons VIVANTS qui font ce que la base
   sait faire ; les laisser éteints aurait rendu l'effet inatteignable dès
   que l'étape 6 retire la chip. Le comportement du §4.3 est l'étape 7. */
var DZM_TB_MOT_ECART=" — Cette base porte UNE animation à la fois pour "+
  "toute la piste de sous-titres, pas trois effets cumulables sur une "+
  "sélection de mots : choisir celle-ci remplace la précédente.";
/* LES DEUX AUTRES ÉCARTS DU §6, DITS À L'UTILISATEUR ET PAS SEULEMENT ICI.
   Ils décrivent CE QUE LA BASE FAIT ; ils ne citent pas le handoff, que
   personne devant l'écran n'a sous les yeux. Le rapport, lui, les nomme.
     • §6 « emoji » : un sélecteur d'emoji dont le choix pose UN clip de 2 s
       à la tête de lecture. Ici : aucun sélecteur, UN clip de 0,8 s PAR
       mot-clé reconnu, à la date de ce mot (voir `dzmEmojiGo`).
     • §6 « texte » : un clip de texte posé à la tête de lecture, en édition
       immédiate. Ici : le panneau de narration — c'est LE bouton « texte »
       que le §5.1 retire du bandeau, donc celui dont la barre doit devenir
       le point d'entrée. Le geste que le §6 décrit existe ailleurs
       (`subsAddHere`, le « + » de l'en-tête S1) et le titre y renvoie. */
var DZM_TB_EMO_ECART=" Cette base n'a pas de sélecteur d'emoji : elle pose "+
  "d'elle-même un clip par mot reconnu, là où ce mot est dit, et non un "+
  "emoji choisi à la tête de lecture.";
var DZM_TB_TXT_ECART=" Ce bouton ouvre un panneau, il ne pose pas de clip : "+
  "pour écrire un sous-titre à la tête de lecture, le « + » de l'en-tête de "+
  "la piste S1.";
var DZM_TB_T_EMOJI="Poser les emoji des mots-clés des sous-titres (feu, "+
  "lune, vague, poulpe, or, fusée) — un clip de 0,8 s par mot reconnu, sur "+
  "la piste vidéo d'overlay la plus haute.";
var DZM_TB_T_EMOJI_OCC="Emoji — la demande précédente est encore en cours ; "+
  "le bouton se rallume à la réponse du serveur.";
var DZM_TB_T_PROJETS="Ouvrir la liste des projets de montage — enregistrer "+
  "sous un nom, ouvrir, dupliquer, renommer, supprimer.";

/* ── EXIGENCE 1 DU §6 : « TOUTES LES ACTIONS PASSENT PAR LE MÊME HISTORIQUE »
   ── ET CE QUE CET HISTORIQUE-CI SAIT FAIRE ────────────────────────────
   MESURE, sur ce bundle : `pushHistory` n'empile QUE `{clips, mixDb}` et
   `undo` ne repose que ces deux-là. Ni les pistes, ni `proj.dur`, ni
   `proj.subsStyle`, ni le projet ouvert n'y entrent. Les neuf actions
   passent donc bien par le MÊME historique — il n'y en a qu'un, et la barre
   n'en crée pas un second — mais ce que `Ctrl+Z` REND diffère de l'une à
   l'autre, et le taire aurait laissé l'utilisateur découvrir seul qu'une
   annulation « ne fait rien ».
   LE CAS LE PLUS TRAÎTRE EST LA PISTE : `svmTracksSet` APPELLE `pushHistory`
   avant d'écrire `proj.tracks`. Une entrée est donc bien empilée — mais
   elle ne contient que des clips inchangés : `Ctrl+Z` la consomme et ne
   défait RIEN de visible. C'est un pas d'historique muet, pas un refus.
   RÉPARER L'HISTORIQUE N'EST PAS DE CETTE ÉTAPE : `pushHistory`, `undo` et
   `redo` sont trois hooks du bundle, hors de la surface que cette chaîne de
   patchs ouvre, et l'élargir toucherait TOUS les gestes de l'écran. On DIT
   la limite à chaque bouton, et le retour qui existe vraiment. */
var DZM_TB_H_CLIPS=" « Annuler » (Ctrl+Z) retire d'un coup ce qui vient "+
  "d'être posé : l'historique de cet écran mémorise les clips et le mixage.";
var DZM_TB_H_PISTE=" « Annuler » (Ctrl+Z) NE retire PAS la piste : "+
  "l'historique de cet écran ne mémorise que les clips et le mixage, et le "+
  "pas qu'il consomme après ce geste ne défait donc rien de visible. Le "+
  "« × » de l'en-tête de la piste la retire.";
var DZM_TB_H_STYLE=" « Annuler » (Ctrl+Z) ne revient pas dessus : ce "+
  "réglage n'entre pas dans l'historique, une annulation défera le geste "+
  "d'AVANT. Le retour, c'est de rechoisir.";
var DZM_TB_H_PANNEAU=" Ouvrir ou fermer ce panneau n'entre pas dans "+
  "l'historique et ne déplace pas la tête de lecture.";
var DZM_TB_H_PROJET=" Ouvrir la liste n'entre pas dans l'historique et ne "+
  "déplace pas la tête de lecture. Ouvrir un PROJET, en revanche, remplace "+
  "le montage affiché, VIDE l'historique et ramène la tête à zéro : la liste "+
  "demande confirmation avant.";
/* LA TABLE, ET À QUOI ELLE SERT. Elle porte pour chacune des neuf clés
   d'icône du §2.4 la réponse aux DEUX premières exigences transversales :
   `h` = ce que `Ctrl+Z` rend, `tete` = si l'action déplace la tête de
   lecture (aucune ne le fait, et le banc le JOUE au lieu de le croire).
   `via` DIT QUI FAIT LE GESTE : « direct » quand le clic écrit lui-même,
   « panneau » quand il ouvre une porte et que l'écriture vient d'après
   (« lier » ouvre la Bibliothèque, « projets » ouvre la liste). Sans ce
   champ, la phrase d'annulation de « lier » — qui parle du clip à venir —
   aurait paru démentie par un clic qui, lui, ne pose rien.
   ELLE N'EST PAS UNE DÉCLARATION D'INTENTION : c'est elle qui écrit la
   phrase de chaque titre (`dzmTbUndo`), et le banc rejoue les neuf actions
   sur un faux écran pour vérifier que le comportement observé est bien
   celui qu'elle annonce. Une table qui mentirait rougirait. */
var DZM_TB_EFFETS={
  "piste-video":{h:"piste",via:"direct",tete:!1},
  "piste-incrust":{h:"piste",via:"direct",tete:!1},
  "piste-audio":{h:"piste",via:"direct",tete:!1},
  "bibliotheque":{h:"clips",via:"panneau",tete:!1},
  "couleur":{h:"style",via:"direct",tete:!1},
  "rebond":{h:"style",via:"direct",tete:!1},
  "glow":{h:"style",via:"direct",tete:!1},
  "emoji":{h:"clips",via:"direct",tete:!1},
  "texte":{h:"panneau",via:"direct",tete:!1},
  "projets":{h:"projet",via:"panneau",tete:!1}};
var DZM_TB_H_TXT={piste:DZM_TB_H_PISTE,clips:DZM_TB_H_CLIPS,
  style:DZM_TB_H_STYLE,panneau:DZM_TB_H_PANNEAU,projet:DZM_TB_H_PROJET};
/* Un genre inconnu rend la chaîne VIDE plutôt qu'« undefined » dans une
   infobulle : le titre reste lisible, et la ligne du banc qui exige une
   phrase par bouton câblé rougit. */
function dzmTbUndo(k){
  var e=DZM_TB_EFFETS[k];
  return (e&&DZM_TB_H_TXT[e.h])||""}

/* ── EXIGENCE 3 DU §6 : « LES INSERTIONS À LA TÊTE DE LECTURE RESPECTENT
   AIMANTER » — CE QUE CETTE BASE EN FAIT, MESURÉ ────────────────────
   « aimanter » est un état de l'écran (`snap`), et il n'est LU qu'à UN
   endroit du bundle : `doSnap`, dans le glissement d'un clip, qui colle les
   BORDS aux bords voisins, à la tête et à zéro. AUCUNE insertion ne le
   consulte — ni `addAsset` (le sélecteur), ni `subsAddHere`, ni les emoji.
   LA BARRE NE CALCULE DONC AUCUNE POSITION, et c'est délibéré : le seul de
   ses neuf boutons qui mène à une insertion à la tête de lecture est
   « lier », et il délègue ENTIÈREMENT le placement à `openPicker`. Poser ici
   une seconde règle d'aimantation aurait fait diverger la barre du « + »
   d'en-tête de piste, qui ouvre le même sélecteur. Le banc le mesure : aucune
   des neuf actions ne LIT la tête de lecture. Aligner la base sur le §6
   voudrait dire aimanter `addAsset` lui-même, pour TOUTES ses portes — un
   autre chantier, consigné plutôt qu'improvisé ici. */

/* ── LE CÂBLAGE, PUR ──────────────────────────────────────────
   Une fonction, aucun hook, aucun accès au DOM : le banc la joue sous node
   et lit ce que chaque bouton reçoit. Elle rend une entrée par clé d'icône —
   `act` (rien si le bouton est éteint), `disabled`, `title`, `toggle`,
   `active`. C'est ICI que se décide « câblé » ou « éteint-et-dit », et nulle
   part ailleurs : la barre, elle, ne fait que peindre ce qu'on lui donne.
   ÉTAPE 7 : LES NEUF SONT CÂBLÉS. Chaque `act` appelle une action qui
   EXISTAIT déjà — aucune n'est réécrite ici — et chaque titre dit ce que
   « annuler » rend, par `dzmTbUndo`. */
function dzmTbCablage(p){
  p=p||{};
  var ts=dzmTsOr(p.tracks);
  var vid=dzmPickTrack(ts,"video");
  var m={};
  var poseTr=typeof p.onTracks==="function";
  /* PISTES — MÊME APPEL que « + piste vidéo » du bandeau : `dzmAdd` puis le
     setter du projet, qui pousse l'historique et marque le projet modifié.
     Rien de neuf n'est écrit ici, c'est une autre porte sur la même action.
     P14 — DEUX SORTES DE PISTES VIDÉO, et la note qui redit la nature de la
     piste créée (`p.note`, le fireNote de l'écran, comme les emoji). Le
     titre de « vidéo » dit l'ÉCART ASSUMÉ : une piste vidéo plein cadre n'a
     ni fondu enchaîné, ni vitesse, ni effets — V1 seule les porte, et les
     fournir est le chantier « plusieurs séquences », non entrepris. */
  function poseTrack(k){
    var r=dzmAddDit(ts,k);
    p.onTracks(r.tracks);
    if(typeof p.note==="function"&&r.note)p.note(r.note)}
  m["piste-video"]={disabled:!poseTr,
    act:poseTr?function(){poseTrack("video")}:null,
    title:poseTr?("Ajouter une piste vidéo plein cadre — ses plans "+
      "RECOUVRENT V1 pendant leur durée et leur son est extrait sur la "+
      "piste de dialogue ; V1 reste la séquence maîtresse (durée, "+
      "transitions, vitesse, effets)."+
      dzmTbUndo("piste-video")):DZM_TB_SANS_HOTE};
  m["piste-incrust"]={disabled:!poseTr,
    act:poseTr?function(){poseTrack("overlay")}:null,
    title:poseTr?("Ajouter une piste d'incrustation — image dans l'image, "+
      "réglable (position, échelle, rotation, opacité), muette."+
      dzmTbUndo("piste-incrust")):DZM_TB_SANS_HOTE};
  m["piste-audio"]={disabled:!poseTr,
    act:poseTr?function(){poseTrack("audio")}:null,
    title:poseTr?("Ajouter une piste audio — posée sous les pistes audio "+
      "existantes, au-dessus des sous-titres."+
      dzmTbUndo("piste-audio")):DZM_TB_SANS_HOTE};
  /* BIBLIOTHÈQUE — `onPick` est le `openPicker` de l'écran, qui porte DÉJÀ
     ses propres refus (projet de démonstration, piste verrouillée). La piste
     visée est RÉSOLUE, jamais devinée : la première piste vidéo dans l'ordre
     d'affichage. Sans piste vidéo il n'y a rien à ouvrir — bouton éteint,
     et le titre nomme la sortie au lieu de laisser deviner.
     LE PLACEMENT EST DÉLÉGUÉ EN ENTIER : cette action ne transmet QUE la
     piste, jamais un temps. C'est ce qui la fait suivre la même règle que le
     « + » d'en-tête de piste, « aimanter » compris (exigence 3 du §6). */
  var pick=typeof p.onPick==="function";
  m["bibliotheque"]={disabled:!(pick&&vid),
    act:(pick&&vid)?function(){p.onPick(vid)}:null,
    title:!pick?DZM_TB_SANS_HOTE
      :vid?("Ouvrir la Bibliothèque et poser une vidéo, une image ou un "+
        "rendu sur la piste "+String(vid).toUpperCase()+", à la tête de "+
        "lecture — c'est la piste vidéo la plus haute du projet."+
        dzmTbUndo("bibliotheque"))
      :("Aucune piste vidéo dans ce projet : rien ne pourrait recevoir le "+
        "clip. « vidéo » du groupe PISTES en crée une.")};
  /* MOT — les trois valeurs viennent de DZM_WORD_ANIMS, la table qui sert
     déjà la chip du bandeau : leur `v` EST la clé d'icône du §3, et leur `t`
     la phrase qui décrit l'effet. Une seconde liste aurait divergé. */
  var wa=String(p.wordAnim||"couleur");
  var poseWa=typeof p.onWordAnim==="function";
  DZM_WORD_ANIMS.forEach(function(a){
    m[a.v]={toggle:!0,active:wa===a.v,disabled:!poseWa,
      act:poseWa?function(){p.onWordAnim(a.v)}:null,
      title:poseWa?(a.t+DZM_TB_MOT_ECART+dzmTbUndo(a.v)):DZM_TB_SANS_HOTE}});
  /* AJOUTS — `emoji` ÉTAIT ÉTEINT À L'ÉTAPE 4 parce que son `fetch` et son
     état d'attente vivaient DANS `DzmEmojiBtn` : il n'y avait rien à
     appeler. L'étape 7 a sorti l'action du bouton (`dzmEmojiGo`) — elle est
     maintenant appelée par les deux portes, et il n'y a toujours qu'un code.
     L'ATTENTE ÉTEINT LE BOUTON, et son titre le DIT au lieu de le laisser
     deviner : une seconde requête partie pendant la première ne détruirait
     rien, mais elle poserait deux fois les mêmes emoji. */
  var poseEmo=typeof p.onEmoji==="function";
  var emoOcc=p.emojiBusy===!0;
  m["emoji"]={disabled:!poseEmo||emoOcc,
    act:(poseEmo&&!emoOcc)?function(){p.onEmoji()}:null,
    title:!poseEmo?DZM_TB_SANS_HOTE
      :emoOcc?DZM_TB_T_EMOJI_OCC
      :(DZM_TB_T_EMOJI+DZM_TB_EMO_ECART+dzmTbUndo("emoji"))};
  var poseTx=typeof p.onText==="function";
  m["texte"]={toggle:!0,active:p.textOn===!0,disabled:!poseTx,
    act:poseTx?function(){p.onText()}:null,
    title:poseTx?(DZM_TB_T_TEXTE+DZM_TB_TXT_ECART+dzmTbUndo("texte"))
      :DZM_TB_SANS_HOTE};
  /* PROJETS — le sélecteur ÉTAIT ÉTEINT À L'ÉTAPE 4 parce qu'il portait son
     état d'ouverture dans son composant : rien ne l'ouvrait de l'extérieur.
     L'étape 7 lui a donné une DEMANDE d'ouverture (`openReq`), et c'est tout
     ce que ce bouton fait — il n'ouvre AUCUN projet, ne touche ni la
     timeline, ni la tête de lecture, ni l'historique. */
  var posePj=typeof p.onProjets==="function";
  m["projets"]={disabled:!posePj,
    act:posePj?function(){p.onProjets()}:null,
    title:posePj?(DZM_TB_T_PROJETS+dzmTbUndo("projets")):DZM_TB_SANS_HOTE};
  return m}

/* LA FRAME SUIVANTE, ISOLÉE POUR ÊTRE JOUABLE. Elle sert au §4.4 :
   « poser l'état final, réactiver les transitions à la frame suivante ».
   `requestAnimationFrame` EST APPELÉE SUR SON OBJET, jamais détachée — une
   référence gardée puis appelée nue (`var raf=w.requestAnimationFrame;
   raf(fn)`) lève « Illegal invocation » sous Blink et WebKit. C'est la forme
   qui était écrite ici, et RIEN NE L'AURAIT VUE : ce chemin ne s'exécute
   qu'au montage du composant à hooks, hors de portée du banc. D'où
   l'extraction : ces six lignes-là, elles, se jouent sous node.
   `cancelAnimationFrame` est exigée AUSSI : sans elle, l'annulateur ne
   pourrait rien annuler, et un moteur qui n'aurait que la moitié de la
   paire vaut mieux servi par un minuteur, qui s'annule vraiment. */
function dzmTbFrame(w,fn){
  var ok=!!(w&&typeof w.requestAnimationFrame==="function"
            &&typeof w.cancelAnimationFrame==="function");
  if(ok){
    var id=w.requestAnimationFrame(fn);
    return function(){w.cancelAnimationFrame(id)}}
  var t=setTimeout(fn,0);
  return function(){clearTimeout(t)}}

/* ── ÉTAPE 5 DU §9 : LE DÉPORT ─────────────────────────────────────────────
   Le §4.2 en entier, et de §4.4 la seule clé `offset`. Le retrait des neuf
   contrôles du bandeau (§5) est l'étape 6, le câblage complet (§6)
   l'étape 7 ; le §4.5 — clavier, `role="toolbar"`, mouvement réduit — est
   l'étape 8, et le CLAVIER DE LA POIGNÉE ci-dessous en est le seul morceau
   arrivé ici en avance : il est la contrepartie du geste souris de ce lot.

   ── L'AVERTISSEMENT DU §9, PRIS AU MOT ──
   « Tester d'abord le bornage : c'est là que se logent les régressions. »
   « Une barre à moitié sortie de l'écran n'est pas récupérable. »
   D'où la forme de ce lot : le CŒUR est `dzmTbBorne`, une fonction PURE qui
   prend la position courante, le déplacement, le rectangle du conteneur,
   celui de la barre et l'abscisse de la tête de lecture, et rend le décalage
   BORNÉ puis AIMANTÉ. Pure = jouable sous node, et c'est la seule façon de
   mesurer le bornage sans écran. Tout le reste — écouteurs, curseur,
   persistance, mesure des rectangles — s'appuie dessus et n'en refait rien.

   ── LE CONTENEUR DU BORNAGE, MESURÉ LE 05/09/2026 ──
   Le §4.2 dit « la zone timeline + zone de prévisualisation ». Dans cette
   base, ce sont DEUX nœuds, frères et empilés, tous deux enfants directs de
   la racine `.dzsvm.svm-col` : `.svm-mid` (lecteur + inspecteur) puis
   `.svm-tl` (la timeline, dont `.svm-trans` — l'ancrage de la barre — est le
   premier enfant). Le RECTANGLE retenu est leur UNION, c'est-à-dire tout
   l'écran SOUS la barre de titre. Trois raisons, chacune mesurée :
   1. c'est le plus petit rectangle qui contienne les deux zones que le §4.2
      nomme ; « zone de prévisualisation » seule (`.svm-playerzone`) est plus
      étroite que la timeline — l'inspecteur occupe la droite de `.svm-mid` —
      et l'union des deux ne serait alors PAS un rectangle, quand le §4.2
      parle d'« un conteneur » au singulier avec une marge unique ;
   2. le seul nœud exclu est `.svm-titlebar`, et c'est le bon : il porte le
      nom du projet, le badge d'enregistrement, le format et le bouton de
      rendu — des commandes qui doivent rester cliquables ;
   3. TOUT le rectangle est à l'intérieur de `.dzsvm`, qui déclare
      `overflow:hidden` (son-vfx-montage.css l.50) et qui est le SEUL
      ancêtre rogneur de la chaîne — `.svm-mid` (l.210) et `.svm-tl` (l.303,
      montage.css l.18, subs.css l.30) n'en déclarent aucun. Borner là-dedans
      garantit donc qu'aucun pixel de la barre n'est coupé : elle reste
      récupérable, ce que le §4.2 exige.
   Borner contre `.svm-tl` SEULE aurait interdit ce que le §4.2 autorise
   explicitement (monter dans la prévisualisation) ; borner contre la racine
   entière aurait laissé la barre couvrir la barre de titre.

   ── L'AXE DE LA TÊTE DE LECTURE ──
   `.svm-phline` — un seul nœud dans le bundle, rendu SANS condition dans
   `.svm-lanes`, large d'1 px (son-vfx-montage.css l.358), positionné en
   `left:calc(88px + (100% - 88px) * phFrac)`. Son abscisse est donc lisible
   à tout instant par `getBoundingClientRect()`, relâchement compris. Mais
   `.svm-lanes` vit dans `.svm-scroll` (`overflow:auto`, l.331) et s'élargit
   avec le zoom : la tête PEUT être hors du conteneur. C'est réglé sans
   second pinçage — voir `dzmTbAimant`.

   ── LE PRÉCÉDENT DU DÉPÔT, ET POURQUOI ON EN DIVERGE ──
   `clipDown` du bundle glisse déjà dans cet écran. MESURÉ : il capture sa
   géométrie au `pointerdown` (`rect`, `pxPerS`, `s0`, `e0`, la liste des
   bords d'aimantation) — on fait pareil, c'est la discipline de la maison —
   mais il pose `pointermove` / `pointerup` sur `e.currentTarget` et s'en
   tire par `setPointerCapture`, qui redirige les événements vers l'élément
   capturant. ICI, C'EST LA FENÊTRE, comme le §4.2 l'écrit, et ce n'est pas
   par obéissance : le décalage est un état React, donc la barre se redessine
   à chaque déplacement, et un écouteur posé sur un nœud que React
   remplacerait mourrait avec lui — le nœud de `clipDown`, lui, survit à ses
   propres rendus. `pointercancel` est écouté EN PLUS des deux du §4.2 : sans
   lui, un geste repris par le système laisserait `grabbing` collé sur tout
   le document, et ce serait un geste destructif sans retour.

   ── LA CLÉ, MÊME ÉCART DÉCLARÉ QUE `dz_svm_tb_open` ──
   Le §4.4 demande `deepotus.toolbar.offset` ; la maison dit `dz_*` (VINGT-SIX
   clés `dz_*` distinctes dans le bundle livré aujourd'hui — les vingt-cinq
   mesurées à l'étape 4, plus `dz_svm_tb_open` qu'elle a elle-même ajoutée —
   contre trois `deepotus.*`, toutes trois hors de portée de cette chaîne).
   Le §4.4 tranche lui-même : « dans le même espace de nommage que les
   panneaux existants ». La FORME est du JSON, comme `dz_svm_keymap`, la
   seule clé `dz_*` de cette base qui stocke autre chose qu'une chaîne plate.
   ON STOCKE UN DÉCALAGE, JAMAIS DES COORDONNÉES : le §4.2 l'exige pour que
   la barre garde sa place relative au redimensionnement de la fenêtre.

   ── LE CLAVIER DE LA POIGNÉE : LIVRÉ ICI, PAS À L'ÉTAPE 8 ──
   Le §4.5 le range dans l'accessibilité, mais il écrit aussi « Un objet
   déplaçable à la souris seule n'est pas accessible ». Les deux autres
   options étaient pires : livrer un déport souris-seule ferait vivre cette
   régression jusqu'à l'étape 8, et rendre la poignée focusable sans lui
   donner les flèches livrerait un bouton focusable qui ne fait rien. Le
   cœur pur rend le clavier presque gratuit — un déplacement de ±8 px (±1
   avec `Maj`) passe par le MÊME `dzmTbBorne` que la souris. RESTE POUR
   L'ÉTAPE 8, ET C'EST DIT : la navigation aux flèches ENTRE LES BOUTONS
   (`tabindex` roving) devra exclure la poignée de son groupe, sinon les
   flèches auraient deux sens sur le même objet. */

/* Les deux distances du §4.2, une fois chacune ; le banc les lit DANS le
   handoff — ni la couche ni lui ne les retapent deux fois. */
var DZM_TB_MARGE=8;
var DZM_TB_AIMANT=12;
/* Les deux pas du §4.5. */
var DZM_TB_PAS=8;
var DZM_TB_PAS_FIN=1;
var DZM_TB_CLE_OFF="dz_svm_tb_off";
/* La classe posée sur `document.body` pendant le geste (§4.2 : « cursor:
   grabbing sur document.body — pas seulement sur la poignée »). */
var DZM_TB_CL_DRAG="dzm-tbdrag";

function dzmTbFini(v){return typeof v==="number"&&isFinite(v)}
function dzmTbNb(v){return dzmTbFini(v)?v:0}

/* UN RECTANGLE LISIBLE, OU RIEN — et « rien » n'est pas « zéro ».
   `getBoundingClientRect()` d'un nœud jamais posé rend six zéros, et un nœud
   détaché peut rendre des `NaN`. Les DEUX doivent être REFUSÉS, pas
   normalisés : un rectangle nul pincerait la barre contre un coin qui
   n'existe pas, et c'est le chemin de la RESTAURATION qui en mourrait — le
   décalage d'un utilisateur, borné contre une mise en page pas encore
   calculée, serait écrasé en silence. Refusé, le bornage est simplement
   SAUTÉ et le décalage passe tel quel. */
function dzmTbRect(q){
  if(!q)return null;
  var l=q.left,t=q.top,w=q.width,h=q.height;
  if(!dzmTbFini(l)||!dzmTbFini(t)||!dzmTbFini(w)||!dzmTbFini(h))return null;
  if(w<=0||h<=0)return null;
  return {l:l,t:t,r:l+w,b:t+h,w:w,h:h}}

/* L'UNION DES DEUX RECTANGLES — « la zone timeline + zone de prévisualisation ».
   Pure : le banc la joue sans DOM. Un seul des deux lisible : c'est lui, et
   le bornage se RESSERRE au lieu de disparaître. Rend la forme d'un
   `DOMRect` (left/top/width/height), celle que tout le reste consomme. */
function dzmTbBoite(p,q){
  var a=dzmTbRect(p),b=dzmTbRect(q);
  if(!a&&!b)return null;
  if(!a)a=b;
  else if(b){
    var l=Math.min(a.l,b.l),t=Math.min(a.t,b.t);
    a={l:l,t:t,w:Math.max(a.r,b.r)-l,h:Math.max(a.b,b.b)-t}}
  return {left:a.l,top:a.t,width:a.w,height:a.h}}

/* LA PINCE. Quand la barre NE TIENT PAS dans le conteneur, `mn` dépasse `mx`
   et aucune position n'est licite : on rend `mn`, le bord d'ORIGINE (gauche,
   haut). C'est délibéré et c'est le bord de la POIGNÉE — sans elle plus rien
   ne se déplace, alors que `⌖` n'aurait de toute façon rien à réparer (à
   décalage nul la barre déborderait pareil) et que l'onglet OUTILS, lui, ne
   bouge jamais et replie la barre quoi qu'il arrive. Un
   `Math.min(mx,Math.max(mn,v))` naïf aurait rendu `mx` : la poignée dehors,
   à gauche. */
function dzmTbPince(v,mn,mx){
  if(mn>mx)return mn;
  return v<mn?mn:(v>mx?mx:v)}

/* LE PLUS PROCHE CANDIDAT À MOINS DE 12 px, ET QUI RESTE DANS LES BORNES.
   Un candidat hors bornes n'en est PAS un — il est écarté, pas ramené.
   CE QUE CET ÉCART FAIT VRAIMENT, MESURÉ PAR MUTATION ET PAS SUPPOSÉ : la
   tête de lecture sortie du conteneur est réglée par le PINÇAGE, pas par
   lui — `res.dx` étant déjà pincé, un candidat au-delà d'une borne est
   forcément PLUS LOIN d'elle que la borne elle-même, donc il ne pouvait pas
   gagner. Le seul cas où l'écart change la sortie est celui d'une barre trop
   grande pour le conteneur, où AUCUNE borne n'est atteignable : sans lui,
   `xmn` et `xmx` — qui se croisent — deviendraient des cibles et la barre
   sauterait hors du conteneur au relâchement. C'est ce cas-là que le banc
   exerce. (Ne pas re-pincer APRÈS l'aimantation reste, lui, un choix de
   forme : re-pincer aurait collé la barre au bord au lieu de la laisser où
   le doigt l'a lâchée, mais rien ne peut aujourd'hui le mettre en défaut.)
   `<` strict : « à MOINS de 12 px » (§4.2). Le premier candidat gagne une
   égalité — l'ordre de la liste est donc l'ordre de priorité. */
function dzmTbAimant(v,cands,mn,mx){
  var best=null,d=DZM_TB_AIMANT,i,e;
  for(i=0;i<cands.length;i++){
    if(cands[i][0]<mn||cands[i][0]>mx)continue;
    e=Math.abs(cands[i][0]-v);
    if(e<d){d=e;best=cands[i]}}
  return best}

/* ── LE CŒUR, PUR (§4.2) ───────────────────────────────────────────────────
   `bar` est le rectangle de la barre TEL QU'IL EST AUJOURD'HUI, c'est-à-dire
   décalé de (`dx`,`dy`) : on en déduit l'ancrage à décalage nul, et les
   bornes s'expriment donc en DÉCALAGE, jamais en coordonnées.
   `mx`/`my` : le déplacement depuis la saisie. `ph` : l'abscisse de l'axe de
   la tête, ou rien. `aim` : vrai au seul relâchement (§4.2 — l'aimantation
   est « au relâchement », pas pendant le geste, sinon la barre collerait aux
   bords en cours de route).
   AUCUNE SORTIE N'EST `NaN` : tout ce qui entre passe par `dzmTbNb`. Un
   `NaN` écrit dans une translation CSS ne lève pas, il ANNULE la règle — la
   barre sauterait à son ancrage sans un mot. */
function dzmTbBorne(o){
  o=o||{};
  var dx=dzmTbNb(o.dx),dy=dzmTbNb(o.dy);
  var res={dx:dx+dzmTbNb(o.mx),dy:dy+dzmTbNb(o.my),ax:"",ay:"",borne:!1};
  var b=dzmTbRect(o.bar),c=dzmTbRect(o.cont);
  if(!b||!c)return res;
  res.borne=!0;
  var x0=b.l-dx,y0=b.t-dy;
  var xmn=c.l+DZM_TB_MARGE-x0,xmx=c.r-DZM_TB_MARGE-b.w-x0;
  var ymn=c.t+DZM_TB_MARGE-y0,ymx=c.b-DZM_TB_MARGE-b.h-y0;
  res.dx=dzmTbPince(res.dx,xmn,xmx);
  res.dy=dzmTbPince(res.dy,ymn,ymx);
  if(o.aim!==!0)return res;
  /* LES QUATRE BORDS DU CONTENEUR sont représentés par les DEUX bornes de
     chaque axe : bornées à 8 px, les positions « bord gauche » et « bord
     gauche du conteneur » sont la même. Aimanter au bord NU aurait violé la
     marge que la ligne du dessus vient de poser. */
  var cx=[[xmn,"g"],[xmx,"d"]];
  /* L'AXE DE LA TÊTE prend les DEUX bords verticaux de la barre : le §4.2
     dit « un bord de la barre », pas « le bord gauche ». */
  if(dzmTbFini(o.ph)){cx.push([o.ph-x0,"tg"],[o.ph-b.w-x0,"td"])}
  var a=dzmTbAimant(res.dx,cx,xmn,xmx);
  if(a){res.dx=a[0];res.ax=a[1]}
  /* PAS D'AXE HORIZONTAL POUR LA TÊTE : `.svm-phline` est une VERTICALE
     (`top:0; bottom:0; width:1px`). Deux bords seulement en ordonnée. */
  var y=dzmTbAimant(res.dy,[[ymn,"h"],[ymx,"b"]],ymn,ymx);
  if(y){res.dy=y[0];res.ay=y[1]}
  return res}

/* ── LA PERSISTANCE DU DÉCALAGE (§4.4) ─────────────────────────────────────
   Même magasin injectable que `dz_svm_tb_open` : sous node il n'y a pas de
   `localStorage`, et une fonction qu'on ne peut pas jouer n'est pas mesurée.
   TOUTE VALEUR QUI N'EST PAS UN COUPLE DE NOMBRES RETOMBE SUR L'ORIGINE, et
   c'est le filet de sécurité de la clé : un `dz_svm_tb_off` corrompu à la
   main ne peut pas envoyer la barre hors de l'écran, il la ramène chez elle. */
function dzmTbOffGet(st){
  var s=st||dzmTbStore(),v=null;
  try{v=s?s.getItem(DZM_TB_CLE_OFF):null}catch(e){return {dx:0,dy:0}}
  if(typeof v!=="string")return {dx:0,dy:0};
  try{v=JSON.parse(v)}catch(e){return {dx:0,dy:0}}
  if(!v||typeof v!=="object")return {dx:0,dy:0};
  return {dx:dzmTbNb(v.dx),dy:dzmTbNb(v.dy)}}
/* REND CE QU'ELLE A ÉCRIT, comme `dzmTbOpenSet` : un magasin en panne fait
   perdre la MÉMOIRE, jamais le déplacement en cours. */
function dzmTbOffSet(o,st){
  var s=st||dzmTbStore();
  var v={dx:dzmTbNb(o&&o.dx),dy:dzmTbNb(o&&o.dy)};
  try{if(s)s.setItem(DZM_TB_CLE_OFF,JSON.stringify(v))}catch(e){}
  return v}

/* ── LE GESTE (§4.2) ───────────────────────────────────────────────────────
   `w` est un OBJET-FENÊTRE et `corps` un ÉLÉMENT-CORPS, tous deux reçus en
   argument : c'est ce qui rend ces trente lignes jouables sous node avec des
   faux, et c'est là que se mesure ce qu'aucune lecture de source ne dirait —
   SUR QUOI les écouteurs sont posés, et qu'ils sont bien tous retirés.
   Rend un ANNULATEUR, appelé aussi bien au relâchement qu'au démontage du
   composant : sans lui, une barre démontée en plein geste laisserait le
   curseur `grabbing` sur tout le document et trois écouteurs vivants.
   LA DERNIÈRE POSITION CONNUE EST GARDÉE : un `pointerup` sans coordonnées
   lisibles (cela arrive sur `pointercancel`) ne doit pas valoir « déplacement
   nul » — la barre sauterait à sa position d'avant le geste. */
function dzmTbSaisie(w,corps,geo,pose){
  var vif=!0,lmx=0,lmy=0;
  if(!w||typeof w.addEventListener!=="function"
     ||typeof w.removeEventListener!=="function"
     ||typeof pose!=="function"||!geo)return function(){};
  function dep(ev){
    var cx=ev?ev.clientX:void 0,cy=ev?ev.clientY:void 0;
    if(dzmTbFini(cx)&&dzmTbFini(cy)){lmx=cx-geo.px;lmy=cy-geo.py}
    return [lmx,lmy]}
  function calc(ev,aim){
    var m=dep(ev);
    return dzmTbBorne({bar:geo.bar,cont:geo.cont,ph:geo.ph,
      dx:geo.dx,dy:geo.dy,mx:m[0],my:m[1],aim:aim})}
  function mv(ev){if(vif)pose(calc(ev,!1),!1)}
  /* `pointercancel` TERMINE COMME UN RELÂCHEMENT — le §4.2 ne le nomme pas.
     Rendre la barre à sa position d'avant le geste aurait été l'autre choix :
     on garde ce que l'utilisateur a fait, c'est le plus indulgent des deux et
     `⌖` reste là pour tout défaire. */
  function up(ev){if(!vif)return;var res=calc(ev,!0);fin();pose(res,!0)}
  function fin(){
    if(!vif)return;
    vif=!1;
    try{w.removeEventListener("pointermove",mv);
        w.removeEventListener("pointerup",up);
        w.removeEventListener("pointercancel",up)}catch(e){}
    try{if(corps&&corps.classList)corps.classList.remove(DZM_TB_CL_DRAG)}
    catch(e){}}
  w.addEventListener("pointermove",mv);
  w.addEventListener("pointerup",up);
  w.addEventListener("pointercancel",up);
  try{if(corps&&corps.classList)corps.classList.add(DZM_TB_CL_DRAG)}catch(e){}
  return fin}

/* ── LA MESURE DES RECTANGLES, DEPUIS LA BARRE ELLE-MÊME ───────────────────
   Aucune propriété neuve n'est demandée à l'écran, donc AUCUNE section de
   patch neuve : on remonte de la barre à `.svm-tl` (le parent du bandeau),
   puis on prend `.svm-mid` chez le même parent. Le `while` est BORNÉ — une
   remontée d'arbre sans plafond est une boucle infinie en puissance. */
var DZM_TB_REMONTEE=40;
function dzmTbAncetre(el,cls){
  var n=el,i=0;
  while(n&&i<DZM_TB_REMONTEE){
    if(n.classList&&typeof n.classList.contains==="function"
       &&n.classList.contains(cls))return n;
    n=n.parentNode;i++}
  return null}
function dzmTbLire(el){
  if(!el||typeof el.getBoundingClientRect!=="function")return null;
  var q;
  try{q=el.getBoundingClientRect()}catch(e){return null}
  return dzmTbRect(q)?q:null}
function dzmTbConteneur(el){
  var tl=dzmTbAncetre(el,"svm-tl");
  if(!tl)return null;
  var par=tl.parentNode;
  var mid=(par&&typeof par.querySelector==="function")
    ?par.querySelector(".svm-mid"):null;
  return dzmTbBoite(dzmTbLire(tl),dzmTbLire(mid))}
/* L'AXE, PAS LE BORD : `.svm-phline` fait 1 px, mais c'est son MILIEU que
   l'œil lit comme la tête de lecture. */
function dzmTbTete(el){
  var tl=dzmTbAncetre(el,"svm-tl");
  var ph=(tl&&typeof tl.querySelector==="function")
    ?tl.querySelector(".svm-phline"):null;
  var q=dzmTbRect(dzmTbLire(ph));
  return q?q.l+q.w/2:null}
/* TOUTE LA GÉOMÉTRIE EN UNE FOIS, AU `pointerdown` — la discipline de
   `clipDown`, qui fige `rect`, `pxPerS` et les bords d'aimantation à la
   saisie. Mesurer à chaque déplacement aurait fait bouger les bornes sous le
   geste : la timeline se redessine pendant la lecture. */
function dzmTbGeo(el,off,ev){
  var bar=dzmTbLire(el);
  if(!bar)return null;
  return {bar:bar,cont:dzmTbConteneur(el),ph:dzmTbTete(el),
    dx:dzmTbNb(off&&off.dx),dy:dzmTbNb(off&&off.dy),
    px:dzmTbNb(ev&&ev.clientX),py:dzmTbNb(ev&&ev.clientY)}}

/* ── LE RECADRAGE : LA BARRE RENTRE QUAND LA FENÊTRE RÉTRÉCIT ─────────────
   LE TROU QUE CECI BOUCHE, ET IL EST RÉEL. Le décalage est stocké en
   RELATIF (§4.2), donc la barre garde sa place quand la fenêtre change de
   taille — mais « sa place » peut sortir du conteneur quand celui-ci
   rétrécit, et le §4.2 dit qu'une barre à moitié sortie n'est pas
   récupérable. L'onglet OUTILS, lui, ne bouge jamais et sait la replier ;
   mais `⌖`, qui est LE filet de sécurité du déport, voyage AVEC la barre et
   deviendrait injoignable. On recadre donc : au montage — ce qui règle le
   cas courant, rétrécir puis recharger — et à chaque `resize`.
   SANS AIMANTATION : le recadrage répare, il ne redécide pas d'une position
   que l'utilisateur a choisie.
   `null` VEUT DIRE « RIEN À FAIRE », et c'est distinct de `{dx:0,dy:0}` :
   un conteneur non mesurable (écran caché, mise en page pas encore calculée)
   NE DOIT PAS ramener la barre à l'origine — c'est exactement la régression
   que `dzmTbRect` refuse déjà plus haut, et elle se rejouerait ici. */
function dzmTbRecadre(el,off){
  var geo=dzmTbGeo(el,off,null);
  if(!geo)return null;
  var res=dzmTbBorne({bar:geo.bar,cont:geo.cont,dx:geo.dx,dy:geo.dy,aim:!1});
  /* UNE SEULE GARDE SUFFIT, ET C'EST MESURE : un conteneur non mesurable
     fait rendre à `dzmTbBorne` le décalage INCHANGÉ, donc l'égalité
     ci-dessous l'attrape déjà. Une seconde garde sur `res.borne` était
     inatteignable — la campagne de mutation l'a montrée verte quel qu'en
     soit le sens, et elle est partie. */
  if(res.dx===geo.dx&&res.dy===geo.dy)return null;
  return {dx:res.dx,dy:res.dy}}
/* L'ÉCOUTE DU REDIMENSIONNEMENT, ISOLÉE POUR ÊTRE JOUABLE — même parade que
   `dzmTbFrame` et `dzmTbSaisie` : la fenêtre est un ARGUMENT, donc le banc
   la remplace par une fausse et mesure ce qui est posé et ce qui est rendu. */
function dzmTbVeille(w,fn){
  if(!w||typeof w.addEventListener!=="function"
     ||typeof w.removeEventListener!=="function"
     ||typeof fn!=="function")return function(){};
  w.addEventListener("resize",fn);
  return function(){w.removeEventListener("resize",fn)}}

/* ── LE CLAVIER DE LA POIGNÉE (§4.5) ───────────────────────────────────────
   `hasOwnProperty` PLUTÔT QU'UN ACCÈS NU : `DZM_TB_TOUCHES["constructor"]`
   rendrait une fonction héritée, donc « vraie », et `v[0]` serait `undefined`
   — un pas `NaN` sur une touche que personne n'a mappée. */
var DZM_TB_TOUCHES={ArrowLeft:[-1,0],ArrowRight:[1,0],
  ArrowUp:[0,-1],ArrowDown:[0,1]};
function dzmTbTouche(k,maj){
  var n=String(k);
  if(!Object.prototype.hasOwnProperty.call(DZM_TB_TOUCHES,n))return null;
  var v=DZM_TB_TOUCHES[n],p=maj===!0?DZM_TB_PAS_FIN:DZM_TB_PAS;
  return {mx:v[0]*p,my:v[1]*p}}

/* ══ ÉTAPE 8 DU §9 — CLAVIER, `role="toolbar"`, MOUVEMENT RÉDUIT (§4.5) ════

   ── LA POIGNÉE EST HORS DU GROUPE ROVING, ET C'EST LA CONSIGNE DE L'ÉTAPE 5
   Ses flèches déplacent la barre de 8 px (1 px avec Maj) ; celles du groupe
   déplacent le FOCUS. Le même geste ne peut pas faire les deux sur le même
   objet. `dzmTbTouche` ci-dessus et `dzmTbRoveDir` ci-dessous sont donc deux
   tables séparées, et le sélecteur du groupe ne nomme pas `.dzm-tbgrip`.
   CE QUE CELA COÛTE, ET C'EST UN ÉCART DÉCLARÉ : la barre a DEUX arrêts de
   tabulation, la poignée puis le groupe — pas un. Le §4.5 demande « un seul
   point d'entrée dans l'ordre de tabulation » ET « la poignée est un bouton
   focusable » dans le même paragraphe ; sortir la poignée du parcours aurait
   rendu son clavier inatteignable, c'est-à-dire annulé la phrase suivante du
   même §4.5 (« un objet déplaçable à la souris seule n'est pas accessible »).
   Le roving vaut donc pour les ONZE boutons — les neuf actions puis `⌖` et
   `×` — et la poignée garde le sien.

   ── LES DEUX CONTRÔLES DE FENÊTRE SONT DANS LE GROUPE ──
   `⌖` « ne doit jamais être masqué » (§4.2) : c'est le filet de sécurité du
   déport. Le laisser hors du roving lui aurait donné un troisième arrêt de
   tabulation, ou aucun. */
var DZM_TB_SEL_ROVE=".dzm-tbb,.dzm-tbwb";
var DZM_TB_A_BARRE="Outils de création";
/* HORIZONTALE : seules les flèches gauche/droite naviguent (§4.5, et
   `aria-orientation="horizontal"` le promet). Haut/bas restent à l'écran —
   ce sont ses sauts de coupe, et les voler ici serait un raccourci de plus
   qui ne dit pas son nom. */
var DZM_TB_ROVE_DIRS={ArrowLeft:-1,ArrowRight:1};
function dzmTbRoveDir(k){
  var n=String(k);
  if(!Object.prototype.hasOwnProperty.call(DZM_TB_ROVE_DIRS,n))return 0;
  return DZM_TB_ROVE_DIRS[n]}

/* LE NOMBRE DE BOUTONS D'ACTION, DÉRIVÉ DU PLAN — jamais écrit en dur : le
   jour où un groupe gagne un bouton, l'ordre plat et les deux index des
   contrôles de fenêtre suivent tout seuls. */
function dzmTbNbAct(plan){
  var l=(plan&&plan.length)?plan:DZM_TB_PLAN,n=0,i;
  for(i=0;i<l.length;i++)n+=((l[i]&&l[i].btns)||[]).length;
  return n}

/* L'ORDRE PLAT DU GROUPE, ET CE QUI Y EST ATTEIGNABLE. Il suit l'ordre du
   DOM par CONSTRUCTION : les groupes du plan, dans l'ordre, puis `⌖` et `×`.
   `DzmToolBar` peint dans ce même ordre et `dzmTbBoutons` le relit du DOM ;
   le gestionnaire refuse de naviguer si les deux longueurs diffèrent — une
   liste plus courte ferait viser à côté, en silence.
   LES DEUX CONTRÔLES DE FENÊTRE SONT TOUJOURS ATTEIGNABLES : le §4.2
   l'exige pour `⌖`, et `×` est la seule façon de replier au clavier depuis
   la souris. Ils ne portent pas d'état `disabled` dans `DzmToolBar`.
   UNE ENTRÉE ABSENTE COMPTE POUR ÉTEINTE, et c'est la MÊME règle que la
   barre applique en peignant (`items[b.i]||{disabled:!0}`). La version
   naïve — « absent donc rien à éteindre » — les aurait comptés ACTIFS, et
   le point d'entrée du parcours serait tombé sur un bouton `disabled`,
   c'est-à-dire nulle part. Le banc compare les deux côtés bouton par
   bouton, sur un câblage plein, un câblage sans hôte et aucun câblage. */
function dzmTbActifs(items){
  var it=items||{},l=DZM_TB_PLAN,a=[],i,j,b,e;
  for(i=0;i<l.length;i++){
    b=(l[i]&&l[i].btns)||[];
    for(j=0;j<b.length;j++){
      e=it[b[j].i];
      a.push(!!e&&e.disabled!==!0)}}
  a.push(!0);a.push(!0);
  return a}

/* ── LE CŒUR : index courant + direction + boutons actifs → index suivant ──
   PUR, donc joué sous node : c'est la seule façon de mesurer la traversée
   des groupes sans navigateur.
   IL BOUCLE (le dernier → le premier), comme une barre d'outils ARIA : sans
   cela, le dernier bouton serait un cul-de-sac au clavier alors qu'il ne
   l'est pas à la souris.
   IL SAUTE LES ÉTEINTS : un bouton `disabled` ne prend pas le focus, et
   poser `tabindex="0"` dessus retirerait la barre entière du parcours.
   HORS BORNES — index négatif, trop grand, `NaN`, non entier, absent : on
   repart du bord AMONT du sens de marche (avant le premier pour `+1`, après
   le dernier pour `−1`), donc le premier appel `dzmTbRove(-1,1,a)` rend le
   PREMIER actif. C'est la même fonction qui sert « aller au bouton suivant »
   et « aller au premier bouton » (§4.1, le focus à l'ouverture).
   LISTE VIDE OU TOUTE ÉTEINTE : `-1`. L'appelant ne pose alors AUCUN
   `tabindex="0"` — une barre sans rien d'atteignable se saute, elle ne
   piège pas le focus sur un bouton mort.
   LA BOUCLE VISITE EXACTEMENT `n` CANDIDATS, chacun une fois : le pas vaut
   ±1, donc elle termine toujours et ne peut pas manquer un actif. */
function dzmTbRove(cour,dir,actifs){
  var l=actifs||[],n=l.length;
  if(!n)return -1;
  var d=(Number(dir)<0)?-1:1;
  var c=Number(cour);
  if(!isFinite(c)||Math.floor(c)!==c||c<0||c>=n)c=(d>0)?-1:n;
  var i,j;
  for(i=1;i<=n;i++){
    j=((c+d*i)%n+n)%n;
    if(l[j])return j}
  return -1}

/* L'INDEX QUI PORTE `tabindex="0"`, ASSAINI À CHAQUE RENDU. Le point
   d'entrée doit rester ATTEIGNABLE : si le bouton mémorisé vient d'être
   éteint (la sélection a changé, une requête emoji est partie), le parcours
   de tabulation retombe sur le PREMIER actif, jamais sur le suivant — c'est
   un point d'entrée, pas une navigation. */
function dzmTbRoveSain(cour,actifs){
  var l=actifs||[],n=l.length;
  var c=Number(cour);
  if(isFinite(c)&&Math.floor(c)===c&&c>=0&&c<n&&l[c])return c;
  return dzmTbRove(-1,1,l)}

/* ── LES TROIS AIDES DE DOM, MINCES EXPRÈS ────────────────────────────────
   Seule `dzmTbBoutons` appelle le DOM (`querySelectorAll`) ; les deux autres
   travaillent sur le TABLEAU qu'elle rend, donc le banc les joue sur un faux
   arbre — la même méthode que `dzmTbGeo` et `dzmTbSaisie` à l'étape 5. */
function dzmTbBoutons(bar){
  if(!bar||typeof bar.querySelectorAll!=="function")return [];
  try{return Array.prototype.slice.call(bar.querySelectorAll(DZM_TB_SEL_ROVE))}
  catch(e){return []}}
function dzmTbIdx(l,el){
  var a=l||[],i;
  if(!el)return -1;
  for(i=0;i<a.length;i++)if(a[i]===el)return i;
  return -1}
function dzmTbFocus(l,i){
  var a=l||[],el=(typeof i==="number"&&i>=0&&i<a.length)?a[i]:null;
  if(el&&typeof el.focus==="function"){el.focus();return !0}
  return !1}
/* « ÉCHAP […] REND LE FOCUS À L'ONGLET » (§4.5) — et RENDRE suppose qu'on
   l'avait. Le raccourci, lui, replie depuis N'IMPORTE OÙ : la timeline, un
   en-tête de piste, l'inspecteur. Y déplacer le focus ne serait pas le
   rendre, ce serait le VOLER — et le voler coûte cher ici, parce qu'un
   `<button>` qui a le focus consomme la barre d'espace, c'est-à-dire la
   lecture. D'où cette garde, posée sur les DEUX chemins de repli. */
function dzmTbDedans(bar,el){
  if(!bar||!el)return !1;
  if(bar===el)return !0;
  if(typeof bar.contains!=="function")return !1;
  try{return !!bar.contains(el)}catch(e){return !1}}

/* LE RACCOURCI, DIT SUR L'ONGLET ET RELU À CHAQUE RENDU. La combo n'est pas
   écrite ici : elle vient de `svmKeyLabel("toolbar")`, donc de la keymap
   VIVANTE — un remappage se lit sur l'onglet comme il se lit déjà sur la
   chip « lame ». Sans combo (hôte muet, action retirée de la table) : rien
   n'est ajouté, jamais une parenthèse vide. */
function dzmTbCombo(c){
  var s=(typeof c==="string")?c.trim():"";
  return s?(" Raccourci : "+s+"."):""}

/* ── L'ONGLET D'APPEL (§2.1) ───────────────────────────────────────────────
   Cinq pastilles aux cinq teintes — l'aperçu du contenu, on voit les
   familles avant d'ouvrir — puis OUTILS, puis le chevron. `aria-expanded` et
   `aria-controls` sont OBLIGATOIRES au §4.1 : sans eux l'onglet s'annonce
   comme un bouton quelconque et rien ne dit ce qu'il ouvre.
   LA TEINTE DES PASTILLES PASSE PAR LA CLASSE `dzm-g-<groupe>`, comme celle
   des boutons : aucun nom de variable CSS n'est fabriqué en JS. */
function DzmToolTab(o){
  o=o||{};
  var open=o.open===!0;
  return r.jsx("button",{type:"button",className:"dzm-tbtab",ref:o.tabRef,
    "aria-expanded":open?"true":"false","aria-controls":DZM_TB_ID,
    title:(open?DZM_TB_T_REPLIER:"Ouvrir la barre d'outils de création.")
      +dzmTbCombo(o.keyLbl),
    onClick:function(){if(typeof o.onToggle==="function")o.onToggle()},
    children:[
      r.jsx("span",{className:"dzm-tbdots","aria-hidden":!0,
        children:DZM_TB_GROUPES.map(function(g){
          return r.jsx("span",{className:"dzm-tbdot dzm-g-"+g},g)})},"d"),
      r.jsx("span",{className:"dzm-tblbl",children:"OUTILS"},"l"),
      r.jsx("span",{className:"dzm-tbchev","aria-hidden":!0,
        children:open?"▾":"▴"},"c")]},"tbtab")}

/* ── LA BARRE (§2.2) ───────────────────────────────────────────────────────
   Trois zones : poignée, groupes, contrôles de fenêtre.
   ELLE RESTE DANS LE DOM QUAND ELLE EST REPLIÉE, et c'est ce qui permet
   d'animer le repli (§4.1 : « Repli : l'inverse »). `visibility:hidden`,
   posé par la feuille à la FIN de la transition, la retire du parcours de
   tabulation et de l'arbre d'accessibilité — un `display:none` aurait coupé
   l'animation, un simple `opacity:0` aurait laissé neuf boutons focusables
   sous une barre invisible.
   `data-noanim` : à la restauration, l'état final est posé SANS transition
   (§4.4), réactivée à la frame suivante par le Dock. */
function DzmToolBar(o){
  o=o||{};
  var open=o.open===!0;
  var items=o.items||{};
  /* LE DÉCALAGE EST NORMALISÉ ICI, une fois : la barre ne peint jamais un
     `NaN` même si l'appelant lui en passe un. */
  var off={dx:dzmTbNb(o.off&&o.off.dx),dy:dzmTbNb(o.off&&o.off.dy)};
  var deporte=off.dx!==0||off.dy!==0;
  /* ÉTAPE 8 — L'INDEX QUI PORTE LE POINT D'ENTRÉE. Il est ASSAINI ICI et
     pas seulement chez l'appelant : la barre est un composant public, et un
     index périmé (un bouton qui vient de s'éteindre) sortirait la barre
     entière du parcours de tabulation. `-1` = rien d'atteignable, donc
     aucun `tabindex="0"` posé — ce qui n'arrive pas dans l'application,
     `⌖` et `×` n'étant jamais éteints. */
  var actifs=dzmTbActifs(items);
  var rove=dzmTbRoveSain(o.rove,actifs);
  var nAct=dzmTbNbAct();
  var ri=0;
  var kids=[];
  /* a. LA POIGNÉE (§2.2a, §4.2, §4.5) — UN BOUTON, plus un décor.
     Elle porte le geste souris ET le clavier, elle n'est donc plus
     `aria-hidden` : un nœud focusable caché des technologies d'assistance
     est une faute, pas une précaution. Le glyphe, lui, le reste — c'est
     `DzmTbIcon` qui le pose, et l'`aria-label` porte le sens. */
  kids.push(r.jsx("button",{type:"button",className:"dzm-tbgrip",
    title:DZM_TB_T_GRIP,"aria-label":DZM_TB_A_GRIP,
    onPointerDown:o.onGrab,onKeyDown:o.onGripKey,
    children:DzmTbIcon({name:"poignee",size:DZM_TB_PX_GRIP,k:"g"})},"grip"));
  /* b. LES GROUPES — une colonne chacun, filet droit sauf le dernier. */
  kids.push(r.jsx("span",{className:"dzm-tbzone",
    children:DZM_TB_PLAN.map(function(gr,gi){
      var tete=[r.jsx("span",{className:"dzm-tbht",children:gr.t},"t")];
      if(gr.suf)tete.push(r.jsx("span",{className:"dzm-tbsuf",
        children:" "+gr.suf},"s"));
      /* ÉTAPE 8, §4.5 : « LA COULEUR N'EST JAMAIS LE SEUL PORTEUR
         D'INFORMATION : chaque groupe a son en-tête en clair. » Il l'avait À
         L'ŒIL et à l'œil seulement — un `<span>` posé au-dessus d'une rangée
         de boutons n'est RATTACHÉ à rien. Le nom accessible de « vidéo »
         était donc « vidéo », et rien ne disait de quoi. `role="group"`
         avec le libellé VERBATIM du §2.2 (suffixe « — sélection » compris)
         rend le rattachement programmatique : le groupe est annoncé à
         l'entrée, comme la teinte le donne à l'œil.
         L'EN-TÊTE N'EST PAS MASQUÉ POUR AUTANT : un moteur qui n'annoncerait
         pas les groupes le lit encore en mode exploration. Une redite vaut
         mieux qu'un silence. */
      return r.jsx("span",{className:"dzm-tbgrp dzm-g-"+gr.g,
        role:"group","aria-label":gr.t+(gr.suf?" "+gr.suf:""),
        "data-last":gi===DZM_TB_PLAN.length-1?"":void 0,
        children:[
          r.jsx("span",{className:"dzm-tbhead",children:tete},"h"),
          r.jsx("span",{className:"dzm-tbrow",
            children:gr.btns.map(function(b){
              /* UNE ENTRÉE MANQUANTE ÉTEINT LE BOUTON. Le repli n'est pas
                 l'objet vide : `{}` aurait rendu un bouton d'apparence
                 vivante sans action derrière — exactement le piège que ce
                 lot refuse. Il n'arrive pas dans l'application (le câblage
                 rend toujours les neuf entrées) ; il arriverait le jour où
                 un bouton s'ajoute au plan sans passer par le câblage. */
              var it=items[b.i]||{disabled:!0,title:DZM_TB_SANS_HOTE};
              /* L'INDEX PLAT AVANCE DANS L'ORDRE DE PEINTURE — c'est ce qui
                 fait que l'ordre du DOM et celui de `dzmTbActifs` sont le
                 MÊME, sans qu'aucun des deux ne recopie l'autre. */
              var ti=ri++;
              return DzmToolBtn({group:gr.g,icon:b.i,label:b.l,
                solo:gr.btns.length===1,toggle:it.toggle===!0,
                active:it.active,disabled:it.disabled===!0,
                tab:ti===rove,
                title:it.title,aria:b.l,onAct:it.act,k:"b-"+b.i})})},"r")]},
        gr.g)})},"zone"));
  /* c. LES CONTRÔLES DE FENÊTRE — les deux vivants. */
  kids.push(r.jsx("span",{className:"dzm-tbwin",children:[
    r.jsx("button",{type:"button",className:"dzm-tbwb dzm-tbrc",
      title:deporte?DZM_TB_T_RECENTRER:DZM_TB_T_RECENTREE,
      "aria-label":"Recentrer la barre d'outils",
      tabIndex:rove===nAct?0:-1,
      onClick:function(){if(typeof o.onRecentrer==="function")o.onRecentrer()},
      children:"⌖"},"rc"),
    r.jsx("button",{type:"button",className:"dzm-tbwb dzm-tbcl",
      title:DZM_TB_T_REPLIER,"aria-label":"Replier la barre d'outils",
      tabIndex:rove===nAct+1?0:-1,
      onClick:function(){if(typeof o.onClose==="function")o.onClose()},
      children:"×"},"cl")]},"win"));
  /* LA TRANSLATION PASSE PAR DEUX PROPRIÉTÉS PERSONNALISÉES FIXES, jamais
     par une transformation écrite en JS : `transform` est déjà employée par
     le repli (§4.1 — `translateY(6px)`) et les deux se seraient écrasées.
     La feuille lit `--tbx`/`--tby` dans la propriété `translate`, qui est
     indépendante de `transform` et se transitionne toute seule sur
     `--dur-bar-snap` : l'aimantation du §4.2 s'anime sans un minuteur.
     Les deux noms sont des LITTÉRAUX — rien n'est fabriqué par
     concaténation, la règle de l'étape 3 tient.
     `data-drag` coupe la transition pendant le geste : sans lui la barre
     suivrait le pointeur avec 180 ms de retard. */
  /* ÉTAPE 8 — `role="toolbar"` (§4.5), AU MOT, sur le nœud qui porte les
     onze boutons ET la poignée. `aria-orientation="horizontal"` promet que
     seules les flèches gauche/droite naviguent, et c'est exactement ce que
     `dzmTbRoveDir` accepte ; `aria-label` nomme la barre — l'onglet dit
     « OUTILS », mais un lecteur d'écran qui entre par Tab n'a pas lu
     l'onglet.
     LE CLAVIER EST SUR LE CONTENEUR, PAS SUR `window`, et c'est la réponse à
     « comment ne pas voler Échap » : l'écouteur ne peut se déclencher que si
     le focus est DANS la barre. Les autres panneaux qui écoutent Échap
     (popover de jonction, popover de projets, panneau des raccourcis) le
     font depuis `window` et gardent leur touche partout ailleurs. */
  return r.jsx("div",{id:DZM_TB_ID,className:"dzm-tbar",ref:o.barRef,
    role:"toolbar","aria-orientation":"horizontal",
    "aria-label":DZM_TB_A_BARRE,onKeyDown:o.onBarKey,
    style:{"--tbx":off.dx+"px","--tby":off.dy+"px"},
    "data-off":open?void 0:"","data-noanim":o.anim===!0?void 0:"",
    "data-drag":o.drag===!0?"":void 0,
    children:kids},"tbar")}

/* ── CE QUE LE DOCK AJOUTE AUX PROPRIÉTÉS DE L'ÉCRAN ─────────────────
   ISOLÉE POUR ÊTRE JOUÉE, comme `dzmTbFrame` à l'étape 4 et pour la même
   raison : cette décision-là — « le bouton emoji est-il vivant ? » — vivait
   sinon dans le seul morceau à hooks du lot, donc hors de portée du banc.
   DEUX PROPRIÉTÉS DE PLUS, ET RIEN D'AUTRE N'EST TOUCHÉ : l'objet de l'écran
   est COPIÉ, jamais muté — il appartient au bundle, qui le reconstruit à
   chaque rendu, et le muter ferait fuir l'état d'attente d'un rendu au
   suivant.
   `onEmoji` N'EST POSÉ QUE SI L'ÉCRAN A FOURNI DE QUOI RECEVOIR LES CLIPS :
   sans `onEmojiAdd`, `dzmEmojiGo` ne saurait qu'écrire une note d'excuse, et
   le bouton aurait l'air vivant en ne faisant rien — exactement ce que
   l'étape 4 refusait déjà. Éteint, et `dzmTbCablage` le dit. */
function dzmTbHote(o,emoji,occupe){
  var h={},k;
  o=o||{};
  for(k in o)if(Object.prototype.hasOwnProperty.call(o,k))h[k]=o[k];
  h.onEmoji=(typeof o.onEmojiAdd==="function"&&typeof emoji==="function")
    ?emoji:null;
  h.emojiBusy=occupe===!0;
  return h}

/* ── CE QUI EST MONTÉ DANS LE BANDEAU (§4.1, §4.4) ─────────────────────────
   Le seul morceau à hooks du lot, et il est mince exprès : il tient l'état
   `open`, le restaure sans animation, et passe le câblage à la barre. Tout
   ce qui se mesure — le câblage, l'onglet, la barre — est pur et se joue
   sous node ; ce composant-ci se lit dans la source et dans le bundle.
   L'ONGLET ET LA BARRE SONT DEUX FRÈRES, pas un nid : l'onglet doit rester
   accroché au bord du bandeau quand la barre partira en déport (étape 5). */
function DzmToolDock(o){
  o=o||{};
  var st=x.useState(dzmTbOpenGet),open=st[0],setOpen=st[1];
  /* LE DÉCALAGE EST RESTAURÉ AU PREMIER RENDU, donc posé AVANT la première
     peinture, et `data-noanim` (déjà là depuis l'étape 4) coupe la
     transition jusqu'à la frame suivante : c'est le « poser l'état final,
     réactiver les transitions à la frame suivante » du §4.4, et la même
     `dzmTbFrame` sert aux deux. Sans cela, une barre restaurée déportée
     glisserait de son ancrage jusqu'à sa place à chaque chargement. */
  var so=x.useState(dzmTbOffGet),off=so[0],setOff=so[1];
  var sg=x.useState(!1),drag=sg[0],setDrag=sg[1];
  var sa=x.useState(!1),anim=sa[0],setAnim=sa[1];
  var bar=x.useRef(null),fin=x.useRef(null);
  /* L'ATTENTE DE LA REQUÊTE EMOJI, ET POURQUOI ELLE EST ICI. `dzmEmojiGo`
     n'a pas de hook : chaque porte tient la sienne. Celle du bandeau vit
     dans `DzmEmojiBtn`, celle-ci dans le Dock — duplication TRANSITOIRE que
     l'étape 6 solde en retirant l'autre porte. */
  var sm=x.useState(0),emo=sm[0],setEmo=sm[1];
  /* ── ÉTAPE 8 — LE POINT D'ENTRÉE DU ROVING, L'ONGLET, ET DEUX MIROIRS ───
     `rove` est un INDEX DE SOUHAIT : la barre l'assainit à chaque rendu, il
     n'a donc jamais besoin d'être remis en cause quand un bouton s'éteint.
     `onglet` reçoit le focus qu'Échap et `×` rendent (§4.5).
     `openRef` : le raccourci bascule depuis un effet qui ne dépend QUE de
     son compteur — sans cette référence il lirait pour toujours l'état du
     premier rendu, la forme de la maison (`clipsRef.current=props.clips`).
     `vuOpen` : l'ouverture RESTAURÉE au montage ne prend PAS le focus. Le
     §4.1 le donne « à l'ouverture », c'est-à-dire au geste ; la barre étant
     ouverte par défaut depuis l'étape 6, le donner au montage volerait le
     focus à chaque chargement de l'écran. `null` = premier passage. */
  var srv=x.useState(0),rove=srv[0],setRove=srv[1];
  var onglet=x.useRef(null);
  var openRef=x.useRef(open);openRef.current=open;
  var vuOpen=x.useRef(null);
  /* LE DÉCALAGE COURANT DANS UNE RÉFÉRENCE, tenue à jour à chaque rendu —
     la forme de la maison (`clipsRef.current=props.clips` dans le bundle).
     L'écouteur de redimensionnement est posé UNE FOIS, au montage ; sans
     cette référence il lirait pour toujours le décalage du premier rendu. */
  var offRef=x.useRef(off);offRef.current=off;
  /* LA MÉMOIRE DES LARGEURS (§5.3) : un bloc déjà sacrifié mesure zéro, et
     sans elle l'échelle ne remonterait jamais quand la fenêtre s'élargit. */
  var bdMem=x.useRef({});
  x.useEffect(function(){
    return dzmTbFrame((typeof window!=="undefined")?window:null,
      function(){setAnim(!0)})},[]);
  /* ── §5.3, L'HÔTE. Il MESURE le bandeau et POSE ce que `dzmBdPlan` a
     décidé ; il ne décide rien lui-même. Il tourne au montage, à chaque
     changement de taille du bandeau (`ResizeObserver` quand le moteur en a
     un, `resize` de la fenêtre sinon — les deux existent rarement en même
     temps, l'un suffit) et à chaque bascule de la barre.
     PAS DE BOUCLE : sacrifier un bloc le passe en `display:none`, ce qui
     change le CONTENU du bandeau, jamais sa BOÎTE — l'observateur ne se
     réveille donc pas sur son propre effet. Mesuré au raisonnement, pas à
     l'exécution : c'est de la dette navigateur, elle est dite.
     RESTE ASSUMÉ : un changement de contenu SANS changement de taille (la
     croix des rappels, un compteur de sous-titres qui gagne un chiffre)
     n'est repris qu'au prochain redimensionnement. Le niveau est alors
     périmé d'un cran, jamais faux dans le sens dangereux — il en cache un
     peu trop, il n'en montre jamais trop. */
  x.useEffect(function(){
    var bd=dzmTbAncetre(bar.current,"svm-trans");
    if(!bd)return;
    function tour(){dzmBdTour(bd,bdMem.current)}
    tour();
    var w=(typeof window!=="undefined")?window:null;
    var ro=null;
    try{
      if(w&&typeof w.ResizeObserver==="function"){
        ro=new w.ResizeObserver(tour);ro.observe(bd)}}
    catch(e){ro=null}
    if(ro)return function(){try{ro.disconnect()}catch(e){}};
    return dzmTbVeille(w,tour)},[open]);
  /* LE RETOUR DU GESTE : si la barre se démonte au milieu d'un glissement,
     l'annulateur retire les trois écouteurs ET la classe `grabbing` restée
     sur le corps. Sans lui, tout le document garderait ce curseur, et rien
     dans l'application ne saurait le lui reprendre. */
  x.useEffect(function(){return function(){
    if(fin.current){fin.current();fin.current=null}}},[]);
  /* LE RECADRAGE, AU MONTAGE ET À CHAQUE REDIMENSIONNEMENT. `recadrer` rend
     `null` quand il n'y a rien à faire : ni écriture inutile dans le
     magasin, ni rendu de plus. */
  x.useEffect(function(){
    function recadrer(){
      var v=dzmTbRecadre(bar.current,offRef.current);
      if(v)setOff(dzmTbOffSet(v))}
    recadrer();
    return dzmTbVeille((typeof window!=="undefined")?window:null,
      recadrer)},[]);
  function bascule(){setOpen(function(v){return dzmTbOpenSet(!v)})}
  /* ── ÉTAPE 8 — LE CÂBLAGE DU CLAVIER (§4.1, §4.5) ────────────────────────
     `items` est HISSÉ hors du rendu : il servait déjà à peindre la barre, il
     sert maintenant AUSSI à savoir quels boutons sont atteignables. Une
     seconde table aurait divergé de la première au premier bouton éteint. */
  var items=dzmTbCablage(dzmTbHote(o,emoji,!!emo));
  function focusOnglet(){
    var t=onglet.current;
    if(t&&typeof t.focus==="function")t.focus()}
  /* REPLIER REND TOUJOURS LE FOCUS À L'ONGLET, et pas seulement sur Échap.
     `×` vit DANS la barre : sans cette ligne, le replier au clavier laissait
     le focus sur un bouton passé en `visibility:hidden`, c'est-à-dire nulle
     part — le navigateur le rend alors au `<body>` et la tabulation repart
     du haut de l'écran. Mesuré au raisonnement sur la règle
     `.dzm-tbar[data-off]{visibility:hidden}` de la feuille, pas à
     l'exécution : c'est de la dette navigateur, elle est dite. */
  /* LE FOCUS N'EST RENDU QUE S'IL ÉTAIT DANS LA BARRE (voir `dzmTbDedans`).
     Les deux chemins de repli passent par ici, et le raccourci en a besoin :
     il replie depuis n'importe où. */
  function rendreFocus(){
    var doc=(typeof document!=="undefined")?document:null;
    if(dzmTbDedans(bar.current,doc&&doc.activeElement))focusOnglet()}
  function replier(){setOpen(dzmTbOpenSet(!1));rendreFocus()}
  /* LE FOCUS AU PREMIER BOUTON (§4.1), SUR LE GESTE SEULEMENT. Il passe par
     le MÊME cœur pur que les flèches : « le premier actif » est
     `dzmTbRove(-1, +1, …)`, pas une seconde règle. */
  x.useEffect(function(){
    if(vuOpen.current===null){vuOpen.current=open;return}
    if(open&&!vuOpen.current){
      var k=dzmTbRove(-1,1,dzmTbActifs(items));
      if(k>=0){setRove(k);dzmTbFocus(dzmTbBoutons(bar.current),k)}}
    vuOpen.current=open},[open]);
  /* LE RACCOURCI (§4.1), REÇU COMME UNE DEMANDE. L'écran ne bascule pas la
     barre : il COMPTE les demandes, exactement comme `openReq` pour la liste
     des projets. La raison est la même — l'état d'ouverture appartient à ce
     composant — et le compteur n'a pas d'ordre à respecter.
     `treq<=0` GARDE LE MONTAGE : l'effet part une première fois à zéro, et
     sans cette ligne la barre basculerait toute seule au chargement.
     LA TOUCHE ELLE-MÊME N'EST PAS ICI : elle est déclarée dans SVM_ACTIONS
     (patcher, section M20a), donc remappable et listée dans le panneau
     « ? » comme les trente-deux autres. */
  var treq=Number(o.toggleReq)||0;
  x.useEffect(function(){
    if(treq<=0)return;
    var v=!openRef.current;
    setOpen(dzmTbOpenSet(v));
    if(!v)rendreFocus()},[treq]);
  /* ÉCHAP ET LES FLÈCHES, SUR LA BARRE (§4.5) — ET LES DEUX NE TRAITENT PAS
     LA PROPAGATION DE LA MÊME FAÇON. L'asymétrie est le cœur de ce bloc.

     ── ÉCHAP : IL REPLIE ET REND LE FOCUS À L'ONGLET, ET IL LAISSE MONTER ──
     L'écouteur est sur LA BARRE, pas sur `window` : il ne peut se déclencher
     que si le focus est DANS la barre. C'est déjà ce qui empêche de voler la
     touche aux autres panneaux partout ailleurs.
     IL NE L'ARRÊTE PAS POUR AUTANT, et c'est une MESURE qui a corrigé la
     première version de ce bloc : le bouton `projets` de la barre ouvre le
     popover des projets SANS déplacer le focus, qui reste donc sur ce
     bouton — dans la barre. Le popover ferme sur `Échap` par un écouteur
     `window` de PHASE MONTANTE (montage.js, effet `[op]`), donc sous nous.
     `stopPropagation` ici l'aurait étouffé : une frappe repliait la barre et
     laissait le popover ouvert derrière, sans clavier pour le fermer.
     C'EST AUSSI LA RÈGLE DE LA MAISON : `SVM_KEYS_INFO` décrit `Échap` comme
     « fermer / annuler — touche fixe (panneaux, capture, flèches d'overlay) ».
     Une touche fixe qui ferme PLUSIEURS choses ne s'accapare pas.
     Reste assumé, dit ici : quand rien d'autre n'est ouvert, la frappe rend
     aussi les flèches d'un overlay sélectionné à la tête de lecture. C'est
     ce que « fermer / annuler » promet, pas un effet de bord.

     ── LES FLÈCHES : ELLES, ON LES ARRÊTE ──
     Sans quoi elles déplaceraient AUSSI la tête de lecture (`step_back` /
     `step_fwd`) : deux gestes pour une frappe, et celui-là n'est pas un
     « annuler » partagé, c'est une navigation qui appartient à la barre.
     React pose son écouteur sur le conteneur racine, donc sous `window` :
     arrêter là empêche bien l'événement natif d'y monter — c'est la mesure
     de l'étape 5, reprise telle quelle.
     Gauche/droite seulement, et seulement quand le focus est sur l'un des
     onze boutons du groupe. La poignée n'y est pas — elle consomme déjà les
     quatre flèches dans son propre `onKeyDown` et arrête leur propagation,
     ce qui est exactement ce qui empêche un même geste d'avoir deux sens.
     LES DEUX LONGUEURS DOIVENT S'ACCORDER : si le DOM ne rend pas autant de
     boutons que le plan en décrit, on ne navigue pas — viser à côté au
     clavier est pire que ne rien faire. */
  function barKey(e){
    if(!e)return;
    if(e.key==="Escape"){
      if(typeof e.preventDefault==="function")e.preventDefault();
      replier();return}
    var d=dzmTbRoveDir(e.key);
    if(!d)return;
    var l=dzmTbBoutons(bar.current),a=dzmTbActifs(items);
    if(l.length!==a.length)return;
    var doc=(typeof document!=="undefined")?document:null;
    var i=dzmTbIdx(l,doc&&doc.activeElement);
    if(i<0)return;
    if(typeof e.preventDefault==="function")e.preventDefault();
    if(typeof e.stopPropagation==="function")e.stopPropagation();
    var j=dzmTbRove(i,d,a);
    if(j<0)return;
    setRove(j);dzmTbFocus(l,j)}
  /* L'ACTION « emoji », RÉUTILISÉE : c'est `dzmEmojiGo`, la même fonction que
     le bouton du bandeau appelle. La barre lui passe les trois ingrédients
     que l'écran fournit (`emojiSegs`, `tracks`, `onEmojiAdd`) et son propre
     couple d'attente. Elle ne calcule AUCUN temps : le placement des clips
     appartient à `dzmEmojiClips`, comme avant. */
  function emoji(){
    dzmEmojiGo({segments:o.emojiSegs,tracks:o.tracks,note:o.note,
      onAdd:o.onEmojiAdd,busy:emo,setBusy:setEmo})}
  /* Le décalage n'est écrit dans le magasin qu'au RELÂCHEMENT : un
     `setItem` par `pointermove` aurait écrit des centaines de fois par
     geste, pour une seule position qui compte. */
  function pose(res,fini){
    setOff({dx:res.dx,dy:res.dy});
    if(fini){setDrag(!1);dzmTbOffSet(res);fin.current=null}}
  /* PAS DE `preventDefault` ICI, et c'est mesuré : sur `pointerdown` il
     supprime les événements souris de compatibilité, donc le focus que ce
     bouton doit recevoir. La sélection de texte que le §4.2 veut empêcher est
     déjà coupée par `user-select:none` sur le corps — le remède que le §4.2
     prescrit lui-même — et `touch-action:none` sur la poignée empêche le
     défilement tactile. Bouton gauche seulement : un clic droit ouvre un
     menu contextuel, il ne saisit pas. */
  function saisir(e){
    if(e&&e.button!=null&&e.button!==0)return;
    var w=(typeof window!=="undefined")?window:null;
    var doc=(typeof document!=="undefined")?document:null;
    var geo=dzmTbGeo(bar.current,off,e);
    if(!w||!geo)return;
    if(fin.current)fin.current();
    setDrag(!0);
    fin.current=dzmTbSaisie(w,doc&&doc.body,geo,pose)}
  /* LES FLÈCHES N'AIMANTENT PAS : le pas de 1 px du §4.5 n'aurait plus aucun
     sens si un seuil de 12 px reprenait la main derrière lui.
     `stopPropagation` EST NÉCESSAIRE, et c'est mesuré : l'écran écoute
     `keydown` sur `window` et ne rend la main qu'aux `input`, `textarea`,
     `select` et aux nœuds éditables — pas aux boutons. Sans elle, les flèches
     déplaceraient la barre ET la tête de lecture. React pose son écouteur sur
     le conteneur racine, donc sous `window` : arrêter la propagation là
     empêche bien l'événement natif d'y monter. */
  function clavier(e){
    var p=dzmTbTouche(e&&e.key,e&&e.shiftKey===!0);
    if(!p)return;
    if(typeof e.preventDefault==="function")e.preventDefault();
    if(typeof e.stopPropagation==="function")e.stopPropagation();
    var geo=dzmTbGeo(bar.current,off,null);
    var res=dzmTbBorne({bar:geo&&geo.bar,cont:geo&&geo.cont,
      dx:off.dx,dy:off.dy,mx:p.mx,my:p.my,aim:!1});
    setOff({dx:res.dx,dy:res.dy});dzmTbOffSet(res)}
  /* `⌖` REMET `dx = dy = 0`, SANS PINCER (§4.2, au mot). C'est le filet de
     sécurité : sa sortie doit être la même à tous les coups, quelle que soit
     la mise en page du moment. L'ancrage est par construction dans la
     timeline — il est posé par la feuille sous le bandeau. */
  function recentrer(){setOff(dzmTbOffSet({dx:0,dy:0}))}
  return r.jsx(r.Fragment,{children:[
    DzmToolTab({open:open,onToggle:bascule,tabRef:onglet,keyLbl:o.keyLbl}),
    DzmToolBar({open:open,anim:anim,off:off,drag:drag,barRef:bar,
      items:items,rove:rove,onBarKey:barKey,
      onGrab:saisir,onGripKey:clavier,
      onRecentrer:recentrer,
      onClose:replier})]})}


/* ══ ÉTAPE 6 DU HANDOFF « BARRE OUTILS FLOTTANTE » — §5 ═══════════════════
   LE BANDEAU REDISTRIBUÉ : ce qui l'a quitté (§5.1), et ce qui se dégrade
   quand il n'a plus la largeur (§5.3).

   AUCUN DES NEUF NE DISPARAÎT DE L'ÉCRAN. Ils sont câblés dans la barre
   flottante depuis l'étape 7 — `dzmTbCablage` rend les neuf avec un `act`
   non nul dès que l'écran fournit ses fonctions — et le défaut de la barre
   passe à « ouverte » DANS CETTE MÊME ÉTAPE, pour qu'un utilisateur qui n'a
   jamais touché l'onglet les ait sous les yeux au premier chargement.

   ── LA PLACE RENDUE, ET SON PROTOCOLE. Sans navigateur on ne mesure pas
   des pixels, on les DÉRIVE — le protocole est donc écrit, pas sous-entendu:
   • chaque contrôle retiré est un bouton mono à 10 px ; l'avance de
     JetBrains Mono (`--f-mono`) vaut 600/1000 d'em, soit 6,0 px par
     caractère à 10 px. C'est une métrique de la fonte, pas une estimation ;
   • la boîte est `border-box` (deepotus.tokens.css l.88 ET
     son-vfx-montage.css l.56, les deux) : largeur = caractères
     + rembourrage horizontal + les deux filets de 1 px ;
   • l'intervalle que le nœud rendait est compté AVEC lui : 12 px pour un
     enfant direct du bandeau (`gap:12px`, son-vfx-montage.css l.306), la
     valeur du groupe pour les autres — 5 px dans `.dzm-add`, 4 px puis
     2 px dans `.dzm-wa` (montage.css l.32, l.89, l.93).
   RÉSERVE DITE : c'est une largeur NOMINALE. Une fonte de repli (Consolas,
   0,55 em) en rendrait moins, une fonte système un peu plus. L'ordre de
   grandeur ne dépend pas de la fonte — c'est plus de la moitié d'un bandeau
   de 1 280 px — mais le chiffre exact, lui, en dépend, et il est écrit ici
   pour pouvoir être contredit par une mesure. */
var DZM_BD_PX_CAR=6;
var DZM_BD_PX_BRD=2;
function dzmBdPx(e){
  var o=e||{};
  if(typeof o.px==="number"&&isFinite(o.px))return o.px;
  return String(o.lbl||"").length*DZM_BD_PX_CAR
    +(Number(o.pad)||0)+DZM_BD_PX_BRD}

/* LES DIX NŒUDS QUI ONT QUITTÉ LE BANDEAU (§5.1) : les neuf contrôles
   (`ctl`) plus l'étiquette `mot`, que le §5.1 nomme elle aussi
   (« l'étiquette MOT et ses trois options »). `lbl` est le libellé RÉEL du
   bouton, celui que le composant écrit ; le banc les rapproche des deux
   côtés, sans quoi cette table dériverait en silence de ce qu'elle décrit.
   L'étiquette `mot` est le seul `px` en dur : 9 px avec `letter-spacing`
   .06em sur trois caractères = 3 × (5,4 + 0,54) = 17,8, arrondi à 18. */
var DZM_BD_RETIRES=[
  {id:"piste-video",  ctl:!0, lbl:"+ piste vidéo", pad:16, gap:12},
  {id:"piste-audio",  ctl:!0, lbl:"+ piste audio", pad:16, gap:5},
  {id:"bibliotheque", ctl:!0, lbl:"Bibliothèque…", pad:16, gap:12},
  {id:"mot",                  lbl:"mot",   px:18,          gap:12},
  {id:"couleur",      ctl:!0, lbl:"couleur",       pad:14, gap:4},
  {id:"rebond",       ctl:!0, lbl:"rebond",        pad:14, gap:2},
  {id:"glow",         ctl:!0, lbl:"glow",          pad:14, gap:2},
  {id:"emoji",        ctl:!0, lbl:"emoji",         pad:16, gap:12},
  {id:"texte",        ctl:!0, lbl:"texte",         pad:16, gap:12},
  {id:"projets",      ctl:!0, lbl:"projets",       pad:16, gap:12}];
/* PURE, et c'est ce qui rend le chiffre rejouable : le banc le RECALCULE au
   lieu de le recopier. `n` compte les CONTRÔLES — il doit valoir neuf, et le
   banc l'exige : une table amputée d'une ligne rendrait un total plus petit
   sans que rien ne le dise. */
function dzmBdRetire(t){
  var l=(t&&t.length)?t:DZM_BD_RETIRES,px=0,n=0,i,e;
  for(i=0;i<l.length;i++){e=l[i];
    px+=dzmBdPx(e)+(Number(e.gap)||0);
    if(e.ctl===!0)n++}
  return {px:px,n:n,nb:l.length}}

/* ── §5.3 : LA DÉGRADATION EN LARGEUR RÉDUITE ─────────────────────────────
   « Le bandeau ne doit JAMAIS passer sur deux lignes ni provoquer de
   défilement horizontal. » Les deux moitiés ne coûtent pas la même chose :
   • DEUX LIGNES — le bandeau est un conteneur flex sans `flex-wrap`, donc
     `nowrap` par défaut ; la feuille l'écrit quand même, en VERROU, comme
     elle écrit déjà `overflow:visible` pour l'onglet ;
   • DÉFILEMENT — le bandeau ne défile pas non plus : il est en
     `overflow:visible`, et `.dzsvm` rogne au bord de la fenêtre. Ce qui
     dépasse n'est donc pas défilable, il est INVISIBLE. C'est le vrai mode
     de panne de cet écran-ci, et c'est celui que l'échelle réduit.

   L'ORDRE DE SACRIFICE DU §5.3, ADAPTÉ À CE QUI EXISTE — l'adaptation est
   dite rang par rang, et chaque rang garde le PRINCIPE de celui du §5.3 :
   1. §5.3 : « le contrôle de mix inline se réduit à son bouton panneau son ».
      N'existe pas — ni mix inline ni panneau son, mesurés à zéro dans le
      bundle. Le principe est « ce qui n'est là que par commodité, et dont la
      version complète vit ailleurs, part le premier ». Dans ce bandeau c'est
      la bande de RAPPELS de raccourcis : purement informative, déjà
      refermable à la main par sa croix, et le panneau « ? » juste à côté en
      dit plus qu'elle.
   2. §5.3 : « les libellés des outils de coupe passent en icônes seules avec
      infobulles ». Applicable AU MOT PRÈS : `aimanter`, `lame · <combo>` et
      `ripple` portent déjà chacun un `title` en clair — l'exigence « ne pas
      livrer un mode compact sans infobulles » (§2.3) est donc remplie sans
      rien ajouter. La chip des sous-titres, quatrième de la même rangée,
      NE SUIT PAS : le §5.3 la protège, et ses deux compteurs seraient
      illisibles en glyphe.
   3. §5.3 : « le bloc d'édition se replie dans un menu ⋯ ». Ce bloc n'existe
      pas (`couper`, `coller`, `scinder`, `supprimer` : zéro dans le bundle,
      et le §5.2 les demande NEUFS — hors de cette étape). Le principe est
      « un bloc dont la version complète est un panneau se replie » : c'est
      ici le métering maître, dont la rangée MIXAGE est le panneau.
   4. §5.3 : « le timecode perd sa durée totale ». Applicable au mot : la
      durée totale est un nœud à elle, dans le timecode.
   NE SE DÉGRADENT JAMAIS (rang 0, §5.3 au mot) : le transport, les
   sous-titres, le zoom et l'onglet OUTILS. L'annulation / rétablissement non
   plus — c'est du transport pour la main qui la cherche.

   LE CŒUR EST PUR, et c'est la seule façon de mesurer « jamais deux lignes »
   sans navigateur : largeur disponible + largeurs des blocs → ce qui tombe.
   L'hôte, plus bas, ne fait que MESURER et POSER ; il ne décide rien. */
var DZM_BD_GAP=12;
var DZM_BD_PX_SEP=13;
var DZM_BD_PX_PAD=28;
var DZM_BD_RANGS=[
  {id:"hints",   rang:1, sel:".svm-hints",     esp:12},
  {id:"coupe",   rang:2, sel:".svm-toolchips", esp:0, serre:!0},
  {id:"metre",   rang:3, sel:".svm-meterslot", esp:25},
  {id:"tctotal", rang:4, sel:".svm-tctotal",   esp:0}];
/* La largeur d'un outil de coupe en ICÔNE SEULE, fixée PAR LA FEUILLE et non
   devinée ici : 4 + 11 + 4 de rembourrage et de glyphe, plus les deux
   filets. Le banc exige que /shared/montage.css porte bien ces trois
   nombres — sans quoi cette constante mentirait sur ce que le navigateur
   dessine, et la dégradation viserait à côté. */
var DZM_BD_PX_ICONE=21;
var DZM_BD_ATTR="data-bdoff";

/* dzmBdPlan(dispo, blocs) → {niveau, off, besoin, ok}
   `blocs` : [{id, px, rang}] — `px` mesuré par l'hôte, `rang` 0 pour ce qui
   ne se sacrifie jamais. Le retour dit CE QUI TOMBE (`off`, dans l'ordre du
   sacrifice), ce qu'il reste à porter (`besoin`) et si ça tient (`ok`).
   `ok:!1` N'EST PAS UNE ERREUR MAIS UN AVEU : quand même le dernier rang ne
   suffit pas, la fonction rend le plan le plus serré qu'elle sache ET dit
   qu'il déborde. Une fonction qui aurait tu ce cas aurait promis une
   garantie qu'elle ne tient pas.
   ELLE NE MUTE RIEN : `cand` est un tableau NEUF, sans quoi le tri
   réordonnerait la table de l'appelant — et l'ordre du §5.3 avec elle.
   LE TRI EST TOTAL (rang, puis rang d'apparition) : deux blocs de même rang
   tomberaient sinon dans un ordre que le moteur choisit. */
function dzmBdPlan(dispo,blocs){
  var l=(blocs&&blocs.length)?blocs:[];
  var d=(typeof dispo==="number"&&isFinite(dispo))?dispo:0;
  var cand=[],besoin=0,i,b,r,w;
  for(i=0;i<l.length;i++){
    b=l[i];
    w=Math.max(0,Number(b&&b.px)||0);
    besoin+=w;
    r=Number(b&&b.rang)||0;
    if(r>0)cand.push({id:b.id,rang:r,px:w,i:i})}
  cand.sort(function(a,c){return a.rang===c.rang?a.i-c.i:a.rang-c.rang});
  var off=[],niveau=0;
  for(i=0;i<cand.length&&besoin>d;i++){
    off.push(cand[i].id);
    besoin-=cand[i].px;
    niveau=cand[i].rang}
  return {niveau:niveau,off:off,besoin:besoin,ok:besoin<=d}}

/* ── L'HÔTE : MESURER, PUIS POSER ─────────────────────────────────────────
   Tout ce qui suit touche le DOM et ne se joue pas sous node — c'est assumé,
   et c'est pour cela que la DÉCISION n'y est pas. Il mesure des largeurs
   NATURELLES (`scrollWidth` quand le nœud est déjà comprimé par
   `text-overflow`), garde en mémoire celle d'un bloc déjà sacrifié — sinon
   elle vaudrait zéro et l'échelle ne remonterait jamais quand la fenêtre
   s'élargit — et écrit UNE chaîne sur le bandeau, que la feuille lit par
   `~=`. Le bandeau appartient au bundle : on n'y ajoute aucun nœud, et
   l'attribut posé n'est géré par React nulle part, donc rien ne l'efface. */
function dzmBdLarg(el){
  if(!el)return 0;
  var a=Number(el.offsetWidth)||0,b=Number(el.scrollWidth)||0;
  return Math.max(a,b)}
/* Les nœuds HORS FLUX du bandeau — l'onglet, la barre, et la liste des
   projets montée nue — ne prennent ni largeur ni intervalle. */
var DZM_BD_HORS=".dzm-tbtab,.dzm-tbar,.dzm-proj";
/* LES BLOCS QUI PORTENT UN FILET (§5.2) — la feuille leur donne 13 px de
   marge en plus du `gap`, et ces 13 px comptent dans la largeur.
   `.svm-hints` N'Y EST PAS : il est en `overflow:hidden`, un filet en
   pseudo-élément y serait rogné, la feuille ne le lui dessine donc pas et
   il n'a pas la marge. `.svm-zoom` non plus : son `margin-left:auto` EST
   l'intercalaire du §5.2, le filet s'y pose sans marge. */
var DZM_BD_SEP=".svm-transbtns,.svm-toolchips,.svm-meterslot";
function dzmBdEst(el,sel){
  if(!el||typeof el.matches!=="function")return !1;
  try{return el.matches(sel)}catch(e){return !1}}
function dzmBdOff(bd){
  var v="";
  try{v=(bd&&typeof bd.getAttribute==="function"
    &&bd.getAttribute(DZM_BD_ATTR))||""}catch(e){v=""}
  return " "+v+" "}
function dzmBdSomme(l){
  var t=0,i;
  for(i=0;i<(l||[]).length;i++)t+=Math.max(0,Number(l[i].px)||0);
  return t}
function dzmBdMesure(bd,mem){
  if(!bd||typeof bd.querySelector!=="function")return null;
  var m=mem||{},dej=dzmBdOff(bd);
  var kids=bd.children||[],cour=0,nv=0,i,el,w;
  for(i=0;i<kids.length;i++){
    el=kids[i];
    if(dzmBdEst(el,DZM_BD_HORS))continue;
    w=dzmBdLarg(el);
    if(w<=0)continue;
    nv++;cour+=w;
    if(dzmBdEst(el,DZM_BD_SEP))cour+=DZM_BD_PX_SEP}
  cour+=Math.max(0,nv-1)*DZM_BD_GAP;
  var blocs=[],plein=cour,j,rg,cible,g;
  for(j=0;j<DZM_BD_RANGS.length;j++){
    rg=DZM_BD_RANGS[j];
    if(dej.indexOf(" "+rg.id+" ")>=0){
      g=Math.max(0,Number(m[rg.id])||0);
      plein+=g}
    else{
      cible=bd.querySelector(rg.sel);
      w=dzmBdLarg(cible);
      g=rg.serre?Math.max(0,w-3*DZM_BD_PX_ICONE):(w>0?w+rg.esp:0);
      if(g>0)m[rg.id]=g}
    blocs.push({id:rg.id,rang:rg.rang,px:g})}
  blocs.push({id:"reste",rang:0,
    px:Math.max(0,plein-dzmBdSomme(blocs))});
  return {dispo:Math.max(0,(Number(bd.clientWidth)||0)-DZM_BD_PX_PAD),
    plein:plein,blocs:blocs,mem:m}}
function dzmBdPose(bd,plan){
  if(!bd||!plan||typeof bd.setAttribute!=="function")return null;
  var v=(plan.off||[]).join(" ");
  try{
    if(bd.getAttribute(DZM_BD_ATTR)===v)return v;
    if(v)bd.setAttribute(DZM_BD_ATTR,v);
    else bd.removeAttribute(DZM_BD_ATTR)}
  catch(e){return null}
  return v}
/* Le tour complet, pour que le Dock n'ait qu'une ligne à appeler. */
function dzmBdTour(bd,mem){
  var q=dzmBdMesure(bd,mem);
  if(!q)return null;
  var plan=dzmBdPlan(q.dispo,q.blocs);
  dzmBdPose(bd,plan);
  return {plan:plan,mesure:q}}

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
  clipsOn:dzmClipsOn,emojiClips:dzmEmojiClips,emojiGo:dzmEmojiGo,
  EMO_TITRE:DZM_EMO_TITRE,WORD_ANIMS:DZM_WORD_ANIMS,
  fitDur:dzmFitDur,durCtl:dzmDurCtl,secs:dzmSecs,DUR_MIN:DZM_DUR_MIN,
  clipLen:dzmClipLen,needDur:dzmNeedDur,askDur:dzmAskDur,
  dialogueTrack:dzmDialogueTrack,trackPlein:dzmTrackPlein,wantsTwin:dzmWantsTwin,
  audioOf:dzmAudioOf,audioSet:dzmAudioSet,audioForget:dzmAudioForget,
  askAudio:dzmAskAudio,srcDurOr:dzmSrcDurOr,srcKey:dzmSrcKey,
  uniqueId:dzmUniqueId,dedupeIds:dzmDedupeIds,seqMax:dzmSeqMax,
  twinClip:dzmTwinClip,twinPlan:dzmTwinPlan,extract:dzmExtract,
  extractBtn:dzmExtractBtn,overlayNote:dzmOverlayNote,
  subsSources:dzmSubsSources,subsLabel:dzmSubsLabel,
  isOverlayTrack:dzmIsOverlayTrack,overlayOrder:dzmOverlayOrder,
  addDit:dzmAddDit,
  CLIP_DEFAUTS:DZM_CLIP_DEFAUTS,DUR_DELAI:DZM_DUR_DELAI,
  tbTraces:DZM_TB_TRACES,tbIcons:DZM_TB_ICONS,tbParse:dzmTbParse,
  tbSerial:dzmTbSerial,TbIcon:DzmTbIcon,ToolBtn:DzmToolBtn,
  TB_GROUPES:DZM_TB_GROUPES,TB_PX:DZM_TB_PX,TB_PX_GRIP:DZM_TB_PX_GRIP,
  TB_PLAN:DZM_TB_PLAN,TB_CLE_OPEN:DZM_TB_CLE_OPEN,TB_ID:DZM_TB_ID,
  tbOpenGet:dzmTbOpenGet,tbOpenSet:dzmTbOpenSet,tbCablage:dzmTbCablage,tbFrame:dzmTbFrame,
  tbHote:dzmTbHote,tbUndo:dzmTbUndo,TB_EFFETS:DZM_TB_EFFETS,
  TB_H_TXT:DZM_TB_H_TXT,
  tbBorne:dzmTbBorne,tbBoite:dzmTbBoite,tbPince:dzmTbPince,
  tbSaisie:dzmTbSaisie,tbTouche:dzmTbTouche,tbGeo:dzmTbGeo,
  tbRecadre:dzmTbRecadre,tbVeille:dzmTbVeille,
  tbRove:dzmTbRove,tbRoveSain:dzmTbRoveSain,tbRoveDir:dzmTbRoveDir,
  tbActifs:dzmTbActifs,tbNbAct:dzmTbNbAct,tbIdx:dzmTbIdx,tbFocus:dzmTbFocus,
  tbDedans:dzmTbDedans,
  tbBoutons:dzmTbBoutons,tbCombo:dzmTbCombo,
  TB_SEL_ROVE:DZM_TB_SEL_ROVE,TB_A_BARRE:DZM_TB_A_BARRE,
  TB_ROVE_DIRS:DZM_TB_ROVE_DIRS,
  tbConteneur:dzmTbConteneur,tbTete:dzmTbTete,tbAncetre:dzmTbAncetre,
  tbOffGet:dzmTbOffGet,tbOffSet:dzmTbOffSet,TB_CLE_OFF:DZM_TB_CLE_OFF,
  TB_MARGE:DZM_TB_MARGE,TB_AIMANT:DZM_TB_AIMANT,TB_PAS:DZM_TB_PAS,
  TB_PAS_FIN:DZM_TB_PAS_FIN,TB_CL_DRAG:DZM_TB_CL_DRAG,
  ToolTab:DzmToolTab,ToolBar:DzmToolBar,ToolDock:DzmToolDock,tsOr:dzmTsOr,
  bdRetires:DZM_BD_RETIRES,bdRetire:dzmBdRetire,bdPx:dzmBdPx,
  bdPlan:dzmBdPlan,BD_RANGS:DZM_BD_RANGS,BD_PX_ICONE:DZM_BD_PX_ICONE,
  BD_ATTR:DZM_BD_ATTR,BD_PX_CAR:DZM_BD_PX_CAR,BD_PX_SEP:DZM_BD_PX_SEP,
  BD_GAP:DZM_BD_GAP,BD_SEP:DZM_BD_SEP,BD_HORS:DZM_BD_HORS,
  bdMesure:dzmBdMesure,bdPose:dzmBdPose,bdTour:dzmBdTour,bdLarg:dzmBdLarg,
  DEFAULTS:DZM_DEFAULT_TRACKS};
window.DzTracks=DzTracks;
