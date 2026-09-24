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
                         subsTrDefaut, subsTrBody, subsTrEnabled,
                         subsTrLabel, subsTrTitle, subsTrNote,
                         subsTrApply,
                         isOverlayTrack, overlayOrder, addDit,
                         tbTraces, tbIcons, tbParse, tbSerial,
                         TbIcon, ToolBtn, TB_GROUPES, TB_PX, TB_PX_GRIP,
                         move, moveTo, add, remove, group,
                         jobsTri, Deliver,
                         teteTxt, trou, trouRipple, DEFAULTS}

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
 /* D-21 (21/09/2026) — LA PISTE DES TITRES, TOUT EN HAUT. Un carton se lit
    PAR-DESSUS tout le reste au rendu (la gravure ASS est le dernier maillon
    vidéo, après les incrustations), et l'écran doit le dire : t1 est donc la
    PREMIÈRE ligne de la timeline, au-dessus même de V2.
    `kind:"title"` est un QUATRIÈME genre, ni vidéo ni audio ni sous-titres :
    le bloc sonvfx teste partout une égalité (`trackKind(x)==="video"`,
    « ==="audio" », « ==="subs" ») et ne trouve donc JAMAIS le sien sur t1 —
    dépôt d'asset, pile d'effets, mixage par clip et bouton « + » de l'en-tête
    la refusent tous, exactement comme ils refusent S1. C'est la recette
    écrite au-dessus de `trackKind` dans le bundle, suivie à la lettre.
    `mix:11` et `--c-text` : l'habillage de S1, l'autre piste de texte. */
 {id:"t1",name:"T1",type:"titres",h:40,c:"--c-text",mix:11,kind:"title"},
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
  /* D-21 — une piste de titres HORS table (t2, si un jour il en naissait une)
     prend le même habillage que t1. Rien ne fabrique d'identifiant t<n>
     aujourd'hui (`dzmAdd` ne rend que des v… et des a…) : cette branche sert
     la RESTAURATION d'une sauvegarde qui en porterait une, jamais une
     création. Sans elle, une telle piste revenait en bande « overlay » de
     0 px de nom, portant pourtant ses cartons. */
  if(kind==="title")return {id:id,name:String(id).toUpperCase(),type:"titres",
    h:40,c:"--c-text",mix:11,kind:"title"};
  /* D-9 — la piste d'AJUSTEMENT (j1) : ses clips n'ont pas de source, ils
     portent des effets qui s'appliquent à tout ce qui est dessous au rendu.
     Habillage d'incrustation (teinte --c-3d) : c'est le groupe qu'elle
     rejoint (dzmGroup). */
  if(kind==="adjust")return {id:id,name:String(id).toUpperCase(),type:"ajustement",
    h:40,c:"--c-3d",mix:13,kind:"adjust"};
  if(type==="vidéo")return {id:id,name:String(id).toUpperCase(),type:"vidéo",
    h:54,c:"--c-video",mix:13,kind:"video"};
  return {id:id,name:String(id).toUpperCase(),type:"overlay",h:40,c:"--c-3d",
    mix:13,kind:"video"}}

/* D-21 — « t » EST LE QUATRIÈME GENRE. La table est celle de `trackKind` du
   bundle (section TT1 du patcher), à l'initiale près : les deux lisent la
   MÊME lettre et rendent le MÊME mot, sinon la couche et l'écran auraient
   divergé sur t1. MESURE du 21/09/2026 : dans `.bak_montage`, AUCUN
   identifiant de piste ne commence par « t » (les 18 occurrences de `id:"t`
   sont des ports de nœuds, des gabarits `tpl_…`, des canaux et des voix —
   relevées une à une), donc la lettre était libre. */
function dzmKindOf(id,kind){
  if(kind)return kind;
  var k=String(id||"").charAt(0);
  return k==="a"?"audio":k==="s"?"subs":k==="t"?"title":k==="j"?"adjust":"video"}
/* D-9 — « j » EST LE CINQUIÈME GENRE (même table que TT1/AJ1 du patcher).
   MESURE du 22/09/2026 : `id:"j` vaut 8 dans .bak_montage, tous des
   `job_…`/`jog_…` — aucun identifiant de PISTE. La lettre était libre. */

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
/* D-21 — LE TITRE EST DANS LE GROUPE DU HAUT, celui des incrustations : un
   carton se lit par-dessus l'image, jamais dessous, et le déplacement ▲ ▼ ne
   doit pas pouvoir le faire passer sous V1. Il partage donc le groupe 0 avec
   V2 — les deux s'échangent librement entre eux, et c'est sans conséquence :
   la gravure ASS passe APRÈS toutes les incrustations au rendu, quel que soit
   l'ordre des bandes. `dzmTitleTrack` l'insère EN TÊTE, donc au-dessus de V2
   à sa naissance. */
function dzmGroup(t){
  var k=t&&t.kind;
  return k==="title"||k==="adjust"?0:k==="video"?(t.id==="v1"?1:0):k==="audio"?2:3}
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
  /* D-21 — « EN HAUT » VEUT DIRE SOUS LES TITRES. La piste t1 est la
     PREMIÈRE bande de la timeline ; sans cette borne, une piste vidéo neuve
     naissait AU-DESSUS d'elle, c'est-à-dire hors de son groupe (dzmGroup
     range t1 avec les incrustations, groupe 0), et les ▲ ▼ ne pouvaient
     plus l'en faire redescendre — une piste coincée au premier coup. */
  var at=genre==="video"?dzmTitresAt(ts):dzmSubsAt(ts);
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
/* Le rang de la PREMIÈRE piste qui n'est pas une piste de titres, c'est-à-
   dire le haut du groupe des incrustations. `0` quand il n'y a aucun titre :
   le comportement d'avant D-21, à l'octet près. */
function dzmTitresAt(ts){
  for(var i=0;i<ts.length;i++)if(dzmKindOf(ts[i]&&ts[i].id,ts[i]&&ts[i].kind)!=="title")return i;
  return ts.length}
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
  var want=kind==="audio"?"audio":kind==="subs"?"subs":
    kind==="title"?"title":"video";
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
    /* CE QUE LA NOTE PROMET DOIT EXISTER (correctif du 22/09/2026, revue
       de la tâche 6). La phrase renvoyait à « + audio » ou « + vidéo » et
       la piste des TITRES retombait sur « + vidéo » : or aucun bouton de ce
       nom ne repose T1 — la bande revient par le raccourci « poser un
       titre », qui recrée la piste EN TÊTE avant d'y poser le carton
       (`titleTrack`, mesuré). Le genre est DÉDUIT (`dzmKindOf`) et non lu
       tel quel : une piste restaurée d'une vieille sauvegarde n'a que son
       `id`, et `tr.kind` y vaut `undefined`. La combo vient de la keymap
       VIVANTE : un remappage aurait rendu « Maj+T » faux.
       LE GENRE EST DÉDUIT UNE FOIS, POUR LES DEUX BRANCHES (correctif du
       22/09/2026) : la branche audio lisait encore `tr.kind` NU, et une
       piste a1 restaurée sans `kind` s'y voyait offrir « + vidéo ». Deux
       lectures du même genre par deux chemins différents, c'est une
       divergence qui attend son tour. */
    var kd=dzmKindOf(tr.id,tr.kind);
    note("Piste "+(tr.name||tr.id)+" retirée"+
      (n?" avec "+n+" clip"+(n>1?"s":""):"")+
      (n?" — annuler ramène les clips ; la piste, elle, "+
         (kd==="title"
          ?"revient avec "+dzmCombo("title_add","Maj+T")+
           ", qui repose un carton (même identifiant)."
          /* D-9 (revue 23/09/2026) : MÊME DÉFAUT QUE T1 — aucun « + vidéo »
             ne repose j1 (dzmAdd ne fabrique que v…/a…) ; elle revient par
             Maj+J / « J+ », qui la recrée sous t1 (`adjustTrack`). */
          :kd==="adjust"
          ?"revient avec "+dzmCombo("adjust_add","Maj+J")+
           ", qui repose un clip d'ajustement (même identifiant)."
          :"se rajoute par « + "+(kd==="audio"?"audio":"vidéo")+
           " » (même identifiant)."):"."))}
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
    surete().then(function(s){if(s)ouvrir(p,s.nom)})}

  /* E-1 (22/09/2026) — LA COPIE DE SÛRETÉ. Un montage courant SANS nom
     (pas de `pid`) qui porte des clips est enregistré sous un nom daté
     AVANT que « ouvrir » ou « nouveau » ne le remplace : la note d'ouverture
     promettait jusque-là « il n'existe plus », E-1 le fait cesser. Elle
     part AVANT `onBefore` : si elle échoue, l'autosave en vol n'a pas été
     annulé et rien n'a bougé. Rend {nom} (nom vide = rien à sauver), ou
     null quand la copie a échoué — l'ouverture est alors ANNULÉE, et le
     motif est dit (le 400 « plus de 2 Mo » n'est pas un « impossible »).
     LA COPIE EST RATTACHÉE À L'ÉCRAN DÈS QU'ELLE EXISTE (`onNamed`) : sans
     cela, `pid` restait vide après un échec de l'étape suivante (création
     400, open 409, réseau) et chaque nouvel essai recréait une copie
     « (non nommé) … ». Ainsi l'autosave relancé par `onFail` miroite dans
     la copie, et l'ouverture réussie reprend la main par `onNamed(p.id)`. */
  function surete(){
    var tl=(!pid&&props&&props.payload)?props.payload():null;
    if(!(tl&&tl.clips&&tl.clips.length))return Promise.resolve({nom:""});
    var n=dzmInstantaneNom(nm,new Date());
    return send("/api/montage/projects","POST",{name:n,timeline:tl})
      .then(function(d){if(props.onNamed)props.onNamed(d.id,d.name);
          return {nom:d.name}},
        function(e){setBusy(0);
          note("Copie de sûreté impossible ("+((e&&e.message)||"requête impossible")+
            ") — ouverture annulée");return null})}

  /* l'ouverture proprement dite, factorisée : « remplacer ? » et
     « nouveau » y passent tous deux. `sauve` = nom de la copie de sûreté. */
  function ouvrir(p,sauve){
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
          note("« "+p.name+" » ouvert. Le montage précédent a été remplacé"+
            (sauve?" — il est à l'abri sous « "+sauve+" »"
              :" : s'il n'était pas enregistré sous un nom, il n'existe plus")+
            ", et « annuler » ne le rend pas.")}
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

  /* E-1 : « nouveau » — un projet VIDE (`dzmProjetNeuf`, le nom du champ ou
     « montage neuf ») créé puis ouvert par `ouvrir`, la copie de sûreté du
     montage affiché d'abord. Le nom du champ est consommé comme par
     « enregistrer sous… ». ARMÉ comme « ouvrir » (« nouveau ? » au second
     clic) : il REMPLACE le montage affiché, et pour un montage NOMMÉ la
     sûreté ne fait rien alors qu'`onBefore` avorte l'autosave en vol. */
  function doNew(){
    if(busy)return;
    if(arm!=="n"){setArm("n");return}
    setArm("");setBusy(1);setErr("");
    surete().then(function(s){if(!s)return;
      return send("/api/montage/projects","POST",dzmProjetNeuf(nv))
        .then(function(d){setNv("");ouvrir({id:d.id,name:d.name},s.nom)})
        .catch(fail)})}

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
        p.vide?r.jsx("span",{className:"dzm-projvide-chip",title:"montage vide",
          children:"\u2205"},"vd"):null,
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
        /* L7 D-39 (24/09/2026) : « ⇄ » compare CE projet à la timeline courante
           — TOUJOURS rendu, grisé sur le courant (comme « ouvrir » : un bouton
           conditionnel est une forme de plus à dater dans l'audit E-12). Rien
           n'est modifié : l'hôte lit le projet, calcule et montre. */
        r.jsx("button",{className:"svm-tbtn dzm-projbtn dzm-projdiff",disabled:mine||off,"aria-disabled":mine||off,
          title:mine
            ?"« "+(p.name||"")+" » est le montage ouvert — rien à comparer"
            :"Comparer « "+(p.name||"")+" » à la timeline courante (rien n'est modifié)",
          onClick:function(){if(props&&props.onDiff)props.onDiff(p)},children:"⇄"},"df"),
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
        r.jsx("button",{className:"svm-minibtn dzm-projnew",disabled:!!busy,
          title:arm==="n"
            ?"Confirmer : créer un montage vide REMPLACE le montage affiché "+
             "(enregistré d'abord s'il n'a pas de nom)"
            :"Créer un montage vide et l'ouvrir (le montage affiché est "+
             "d'abord enregistré s'il n'a pas de nom ; un second clic confirmera)",
          onClick:doNew,children:arm==="n"?"nouveau ?":"nouveau"},"nw"),
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

var DZM_DUR_UNDO=" « Annuler » (Ctrl+Z) rend aussi la durée du projet : elle "+
  "entre dans l'historique depuis le 21/09/2026, avec les pistes, le style "+
  "des sous-titres, la plage et les marqueurs.";

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

/* ── P16 : TRADUIRE LES RÉPLIQUES — le cœur calculable ────────────────────
   La rangée « Répliques » du tiroir de sous-titres gagne une langue cible
   (état local `dz_subs_to`) et un bouton « Traduire vers … » (sections
   M26a/M26b du patcher). TOUT ce qui se décide se décide ICI, en fonctions
   PURES jouées sous node par le banc bundle : le corps de la requête
   (subsTrBody), le droit de partir et sa raison (subsTrEnabled), le défaut
   de la cible (subsTrDefaut — « en » quand on transcrit du français, sinon
   « fr »), le libellé (subsTrLabel), l'infobulle (subsTrTitle — elle dit
   MOT POUR MOT ce que le clic fait, et ce qu'« Annuler » fait : MESURÉ,
   l'application passe par props.onChange(…, heavy) → le point d'écriture
   unique des répliques de l'hôte, qui pousse UNE entrée d'historique avant
   d'écrire et REFUSE en le disant quand la piste S1 est verrouillée), la
   note de fin (subsTrNote) et la fusion du résultat (subsTrApply — temps
   et identifiants des répliques CONSERVÉS, texte et libellé remplacés,
   les mots karaoké d'avant JETÉS : ils épelaient l'ancien texte). */
function dzmSubsTrDefaut(lang){return String(lang||"")==="fr"?"en":"fr"}
function dzmSubsTrLangLab(code,langs){
  var l=Array.isArray(langs)?langs:[],i;
  for(i=0;i<l.length;i++)if(l[i]&&l[i][0]===code)return String(l[i][1]);
  return String(code||"?")}
function dzmSubsTrLabel(target,langs){
  return "Traduire vers "+dzmSubsTrLangLab(target,langs)}
function dzmSubsTrBody(segs,target,source){
  var cs=Array.isArray(segs)?segs:[],t=String(target||"");
  if(!cs.length||!t)return null;
  return {segments:cs.map(function(s){
      return {start:dzmSubsNum(s&&s.start),end:dzmSubsNum(s&&s.end),
              text:String((s&&s.text)||"")}}),
    target:t,
    /* « auto » est une consigne de DÉTECTION, pas une langue : la route
       reçoit alors source:null et laisse le modèle lire la langue. */
    source:(source&&source!=="auto")?String(source):null}}
function dzmSubsTrEnabled(n,est,busy){
  if(busy)return {on:!1,pourquoi:"Un travail est déjà en cours — attendez sa fin."};
  if(!(n>0))return {on:!1,pourquoi:"Aucune réplique à traduire : la piste S1 est vide."};
  if(!est||!est.ok)return {on:!1,pourquoi:String((est&&est.reason)||
    "Aucune clé LLM configurée (Réglages) — le coût ne peut pas être "+
    "annoncé, donc rien n'est lancé.")};
  return {on:!0,pourquoi:""}}
function dzmSubsTrTitle(n){
  if(!(n>1))return "REMPLACE le texte de la réplique de S1 par sa "+
    "traduction ; son temps est conservé. « Annuler » de la timeline "+
    "restaure le texte d'avant (le remplacement pousse une entrée "+
    "d'historique avant d'écrire). Piste S1 verrouillée : rien n'est "+
    "écrit, et l'écran le dit.";
  return "REMPLACE le texte des "+n+" répliques de S1 par leur traduction ; "+
    "leurs temps sont conservés. « Annuler » de la timeline restaure le "+
    "texte d'avant (le remplacement pousse une entrée d'historique avant "+
    "d'écrire). Piste S1 verrouillée : rien n'est écrit, et l'écran le dit."}
function dzmSubsTrNote(n,target,langs){
  return n+" réplique"+(n>1?"s":"")+" traduite"+(n>1?"s":"")+" vers "+
    dzmSubsTrLangLab(target,langs)+" — relisez, la machine se trompe."}
function dzmSubsTrApply(segs,rendus,labelOf){
  var cs=Array.isArray(segs)?segs:[],rs=Array.isArray(rendus)?rendus:[];
  if(!cs.length||cs.length!==rs.length)return null;
  return cs.map(function(s,i){
    var t=String((rs[i]&&rs[i].text)||""),out={},k;
    for(k in s)if(Object.prototype.hasOwnProperty.call(s,k))out[k]=s[k];
    out.text=t;
    out.label=(typeof labelOf==="function")?labelOf(t):t;
    out.words=null;
    return out})}


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
   1 occurrence, mesuré le 06/09/2026 — 22/09/2026 : remplacée en aval par la
   section EA1 du patcher montage, vidéo → v1, l'image reste v2) ; sur la sauvegarde de l'utilisateur
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
  "d'être posé : l'historique de cet écran mémorise tout l'état du montage.";
var DZM_TB_H_PISTE=" « Annuler » (Ctrl+Z) retire la piste : l'historique de "+
  "cet écran mémorise les pistes depuis le 21/09/2026. Le « × » de l'en-tête "+
  "de la piste la retire aussi.";
var DZM_TB_H_STYLE=" « Annuler » (Ctrl+Z) revient dessus : ce réglage entre "+
  "dans l'historique (une entrée par rafale de 600 ms).";
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
    /* E-10 (lot E-C, tâche 4, 23/09/2026) : ANCRÉE dans le bandeau de
       transport. La prop vient de l'hôte (persistée par lui) ; la feuille
       fait tout le reste (position:static, en flux, compacte). `data-off`
       garde son sens : l'onglet replie la barre ancrée à zéro largeur. */
    "data-docked":o.docked===!0?"":void 0,
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
    /* E-10 (revue 23/09/2026) : ANCRÉE, LA POIGNÉE EST INERTE — la barre est
       en flux (`translate:none`), un déport saisi ici ne se verrait pas mais
       serait persisté et reparaîtrait au désancrage. Même garde au clavier. */
    if(o.docked===!0)return;
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
    if(o.docked===!0)return;
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
    DzmToolBar({open:open,docked:o.docked,anim:anim,off:off,drag:drag,barRef:bar,
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

/* ── D-0 (21/09/2026) : L'HISTORIQUE COMPLET ─────────────────────────────
   MESURÉ sur le bundle : `pushHistory` n'empilait que {clips, mixDb} ; les
   pistes, la durée, le style S1, la plage et les marqueurs restaient hors
   d'atteinte de Ctrl+Z, et six titres de l'écran le disaient. Un instantané
   porte désormais SEPT clés, toutes des RÉFÉRENCES (les tableaux sont
   traités en immutable partout : stocker la référence suffit, comme avant).
   `histApply` ne touche QUE les clés que l'instantané PORTE : un h0
   historique {clips, mixDb} capturé par un geste amont reste valable.

   ABSENT EST UN ÉTAT, ET IL EST RESTAURÉ COMME TEL. MESURÉ À L'ÉCRAN le
   21/09/2026 sur le projet de démonstration, qui n'a PAS de clé
   `proj.tracks` (`svmTracksOf` retombe alors sur DZM_DEFAULT_TRACKS) :
   ajouter une piste « audio » puis allonger la timeline, Ctrl+Z rendait la
   durée mais LAISSAIT la piste A4. La cause : l'instantané d'avant ne
   portait pas `tracks` — la clé n'existait pas — donc `histApply` n'avait
   rien à remettre. Les CINQ clés sont donc copiées SANS condition dès que
   `proj` est un objet : `s[k]=p[k]` vaut `undefined` quand la clé manque,
   `k in s` reste vrai, et `histApply` réécrit l'absence. Même trou, même
   correctif, pour `range`, `markers` et `subsStyle`. */
var DZM_HIST_CLES=["tracks","dur","subsStyle","range","markers"];
function dzmHistSnap(o){
  if(!o||typeof o!=="object")return {};
  var s={},p=o.proj,i,k;
  if("clips" in o)s.clips=o.clips;
  if("mixDb" in o)s.mixDb=o.mixDb;
  if(p&&typeof p==="object")for(i=0;i<DZM_HIST_CLES.length;i++){
    k=DZM_HIST_CLES[i];s[k]=p[k]}
  return s}
function dzmHistApply(p,s){
  if(!s||typeof s!=="object")return p;
  var base=(p&&typeof p==="object")?p:{},n=Object.assign({},base),i,k;
  if("mixDb" in s)n.mixDb=s.mixDb;
  for(i=0;i<DZM_HIST_CLES.length;i++){k=DZM_HIST_CLES[i];if(k in s)n[k]=s[k]}
  return n}

/* options de rippleCut depuis l'état des pistes : pistes en boucle (elles
   ne rippent pas) et pistes verrouillées (elles ne bougent pas). PURE.
   UN SEUL endroit : la coupe par plage (R2, « Maj+X ») et le tiroir Texte
   (M12) construisaient la MÊME paire à deux endroits ; deux copies d'une
   même condition divergent à la première retouche. */
function dzmCutOpts(proj,trackSt){
  var lk={},st=trackSt&&typeof trackSt==="object"?trackSt:{};
  Object.keys(st).forEach(function(k){if(st[k]&&st[k].l)lk[k]=!0});
  var lt=svmTracksOf(proj).filter(function(t){return t.loop}).map(function(t){return t.id});
  return {loopTracks:lt,locked:lk}}

/* ── D-11 (21/09/2026) : LA PLAGE D'ENTRÉE / SORTIE ───────────────────────
   `proj.range` = {in, out} (secondes, null si non posé) ou null. Pure :
   `dzmRangeSet(range, which, t, dur)` rend la plage suivante ; "in" après
   "out" pousse "out" à dur (jamais une plage inversée) ; "clear" rend null.
   Persistée par POST /save (`range`), restaurée par `dzmRangeFrom`. */
function dzmRangeNum(v,dur){
  var n=Number(v);if(!isFinite(n))return null;
  var d=Number(dur);if(!isFinite(d)||d<0)d=0;
  return Math.max(0,Math.min(d,dzmR3(n)))}
function dzmRangeSet(range,which,t,dur){
  var r=range&&typeof range==="object"?{in:range.in,out:range.out}:{in:null,out:null};
  if(which==="clear")return null;
  var v=dzmRangeNum(t,dur);
  if(v==null)return range||null;
  if(which==="in"){r.in=v;if(r.out!=null&&r.out<=v)r.out=dzmRangeNum(dur,dur)}
  else if(which==="out"){r.out=v;if(r.in!=null&&r.in>=v)r.in=0}
  else return range||null;
  if(r.in==null)r.in=null;if(r.out==null)r.out=null;
  return r}
function dzmRangeFrom(v){
  if(!v||typeof v!=="object")return null;
  var a=Number(v.in),b=Number(v.out);
  if(!isFinite(a)||!isFinite(b)||a<0||b<=a)return null;
  return {in:dzmR3(a),out:dzmR3(b)}}
function dzmRangeLen(r){
  if(!r||typeof r!=="object")return 0;
  var a=Number(r.in),b=Number(r.out);
  return (isFinite(a)&&isFinite(b)&&b>a)?dzmR3(b-a):0}
/* la barre sur la règle : deux poignées et la bande entre elles.
   `dzmRangeFrom` fait ici office de garde : sans plage COMPLÈTE et valide
   (une entrée seule, une plage inversée, rien du tout), le composant rend
   `null` et la règle est exactement celle d'avant — c'est ce qui rend la
   section R3 inoffensive tant que I / U n'ont pas été frappés.
   Les 88 px retranchés sont la GOUTTIÈRE (`.svm-gutter`, 88 px collants) :
   la même soustraction que `phFromEvent` du bundle, qui lit la tête de
   lecture à `(clientX - left - 88) / (width - 88)`. */
function DzmRangeBar(o){
  var rg=dzmRangeFrom(o&&o.range),d=Number(o&&o.dur)||1;
  if(!rg)return null;
  /* BORNÉ À LA RÈGLE (21/09/2026). Une plage est PERSISTÉE : elle survit à un
     raccourcissement de la durée, et `rg.out` peut alors dépasser `dur` —
     `dzmRangeFrom`, qui garde ce composant, ne connaît pas la durée et ne peut
     donc pas borner à sa place. Sans ces deux Math.min, `left` passait 100 % et
     la bande débordait la règle à droite. `100-l` pour la largeur : une entrée
     déjà hors champ laisse une bande de zéro, pas une bande à l'envers. */
  var l=Math.min(100,rg.in/d*100),w=Math.min(100-l,(rg.out-rg.in)/d*100);
  return r.jsx("div",{className:"dzm-range",
    title:"Plage "+rg.in.toFixed(2)+" s → "+rg.out.toFixed(2)+" s — I : entrée, "+
      "U : sortie, X : effacer, Maj+X : couper la plage (toutes pistes, ripple)",
    style:{left:"calc(88px + (100% - 88px) * "+(l/100)+")",width:"calc((100% - 88px) * "+(w/100)+")"}})}

/* ── D-2 (21/09/2026) : LES MODES D'ÉDITION ─────────────────────────────
   Chez Resolve : insert, overwrite, replace, fit to fill, place on top,
   append at end, ripple overwrite. Ici SIX modes sur `dzmInsere(clips,clip,
   mode,opts)` (replace = « Remplacer la source… », P6, existe déjà) :
     ecraser         pose et rogne/fend ce qui est dessous (même piste) ;
     inserer         fend au point d'entrée et POUSSE la suite de la piste ;
     fin             pose après le dernier clip de la piste, tête ignorée ;
     dessus          pose sur la piste LIBRE la plus proche au-dessus, du
                     MÊME genre que la piste visée (une image ne va pas
                     atterrir sur A2, un son ne va pas atterrir sur V3) ;
     ripple_ecraser  retire le clip sous la tête, pose À SA PLACE (depuis
                     le DÉBUT du clip remplacé), recale la suite ;
     remplir         (fit to fill) bornes = plage I/O, vitesse = source/plage,
                     ÉCRÊTÉE à [0,25 ; 4] — et `srcIn` REMIS À 0 : la plage
                     décide des bornes de timeline, la vitesse absorbe tout
                     le reste de la source, donc on repart de son début.

   CE QUE FAIT LE JUMEAU, EXACTEMENT (`opts.twin`, le son du plan de P12) —
   réécrit le 21/09/2026 après mesure, l'ancienne phrase (« la piste jumelle
   est poussée comme l'est la piste visée ») décrivait une intention, pas le
   code :
     · `ecraser`, `inserer`, `dessus` (qui retombe en `ecraser`) : le jumeau
       est posé SUR SA PISTE, au MÊME mode, aux bornes DEMANDÉES du clip
       vidéo (`clip.start`/`clip.end`) — `inserer` ripple donc aussi la piste
       jumelle, sinon le son posé perdrait la synchro que la vidéo vient de
       gagner ;
     · `ripple_ecraser` : même mode sur la piste jumelle, avec `opts.head`
       RELAYÉE TELLE QUELLE (mesuré : la réécrire à `clip.start` décalait le
       son de 4 s sur head 2 / clip [6,9[). La tête est une position de
       TIMELINE, commune aux deux pistes ;
     · `fin` et `remplir` : le jumeau est posé en `ecraser` aux bornes RÉELLES
       du clip vidéo posé — pour `fin` parce que la fin de la piste jumelle
       n'est pas celle de la piste visée (mesuré : x [4,7[ sur v1, mais [20,23[
       sur a1 si on relançait `fin` là-bas), pour `remplir` parce que les
       bornes sont celles de la plage. `remplir` propage en plus au jumeau la
       `speed` calculée (sinon v1 ×2 et a1 ×1 : désynchronisé d'entrée) ;
     · piste jumelle VERROUILLÉE : rien n'est posé pour le son (la vidéo, elle,
       est posée), `refus` vaut `"verrou_jumeau"` — même refus que celui que
       `dzmTwinPlan` prononce déjà, et la `note` le dit.

   RIPPLE ET LES AUTRES PISTES — CHOIX ASSUMÉ : `ripple_ecraser` ne recale QUE
   la piste visée (et, quand il y a un jumeau, la piste jumelle, par le même
   appel sur elle). C'est l'inverse de `dzmRippleCut` (l. ~567), qui recale
   TOUTES les pistes non verrouillées : un ripple overwrite de Resolve est
   LOCAL à la piste, et c'est le jumeau — pas un recalage global — qui porte
   la synchro du son avec sa vidéo.

   FENTE : `dzmCarve` NE réutilise PAS `dzmRippleCut` — mesuré : `dzmRippleCut`
   retire du TEMPS et RIPPLE toutes les pistes non verrouillées / non bouclées,
   ce qu'`ecraser`/`inserer`/`remplir` ne doivent PAS faire (ils ne touchent QUE
   la piste visée). `dzmCarve` a donc son propre fondu, mais son schéma de
   nommage est ALIGNÉ, mesuré sur `newId` de `dzmRippleCut` : même suffixe `_r`,
   même compteur collé sans séparateur (`_r`, puis `_r2`, `_r3`…), même table
   nue anti-`__proto__` — et `dzmPose` utilise EXACTEMENT le même mécanisme
   quand l'identifiant du clip posé est DÉJÀ PRIS sur le montage (mesuré : sans
   ça, poser un clip `p2` sur une piste qui a déjà `p2` rendait les identifiants
   ["p1","p2","p2"], et le bundle sélectionne/édite PAR identifiant).

   SOURCE ET `srcIn` : la doctrine de `dzmRippleCut` vaut ici aussi — « pas de
   source, pas de fenêtre de source ». `dzmCarve` n'écrit `srcIn` sur un morceau,
   et `dzmPose` n'en force un à 0, QUE si le clip en portait un ou porte un
   `src`. Un clip de TITRE (`{text:"…"}`, sans `src`) ne gagne donc aucun
   `srcIn` qui ferait mentir l'inspecteur.

   PARTAGE D'OBJETS : le montage rendu n'est PAS un clone profond. Les clips
   que l'opération ne touche pas sont les MÊMES objets que dans `clips` (seuls
   les clips rognés / fendus / décalés et le clip posé sont recopiés, à plat,
   par `Object.assign`). Les fonctions sont pures au sens où elles ne MUTENT
   rien : l'appelant peut comparer par identité pour savoir ce qui a bougé,
   mais ne doit pas muter un clip du résultat en croyant travailler sur une
   copie.

   ORDRE DES PISTES POUR « dessus » : mesuré sur `dzmOverlayOrder` (l. ~2587,
   commentaire « compose la piste listée le plus haut AU-DESSUS ») — dans
   une liste de pistes, l'INDEX LE PLUS PETIT est la piste la PLUS HAUTE à
   l'écran. `dzmInsere` cherche donc, à partir de la piste visée, vers les
   index DÉCROISSANTS (0 en tête) : c'est la même loi que `layer`. Quand rien
   n'est libre au-dessus (ou que la piste visée n'est même pas dans
   `opts.tracks`), il n'y a PAS de sortie anticipée : le mode retombe en
   `ecraser` sur la piste visée et le chemin NORMAL reprend — la garde de
   verrou et la pose du jumeau s'appliquent donc aussi à ce repli (mesuré :
   l'ancien `return` écrivait sur une piste verrouillée et perdait le son). */
var DZM_MODES=Object.freeze([["ecraser","écraser"],["inserer","insérer"],
  ["fin","en fin"],["dessus","au-dessus"],["ripple_ecraser","écraser en ripple"],
  ["remplir","remplir la plage"]].map(function(p){return Object.freeze(p)}));
/* Les refus sont des JETONS STABLES, jamais une phrase : la phrase française
   vit dans `note` (que l'appelant concatène à la sienne), le jeton vit dans
   `refus` (que l'appelant teste). */
var DZM_REFUS=Object.freeze(["clips","clip","verrou","verrou_jumeau","aucune_piste"]);
function dzmModeOk(m){return DZM_MODES.some(function(o){return o[0]===m})?m:"ecraser"}
function dzmNoteJoin(a,b){return a?(b?a+" ; "+b:a):(b||"")}
function dzmTrackEnd(clips,tr){
  var m=0;(clips||[]).forEach(function(c){if(c&&c.tr===tr&&Number(c.end)>m)m=Number(c.end)});
  return dzmR3(m)}
function dzmOverlap(clips,tr,a,b,skip){
  return (clips||[]).some(function(c){return c&&c.tr===tr&&c.id!==skip&&
    Number(c.start)<b-1e-6&&Number(c.end)>a+1e-6})}
function dzmTaken(clips){
  var t=Object.create(null);
  (clips||[]).forEach(function(c){if(c&&c.id!=null)t[String(c.id)]=1});return t}
function dzmFreeId(taken,id){
  var base=String(id)+"_r",n=base,i=2;while(taken[n])n=base+(i++);taken[n]=1;return n}
/* fend/rogne ce qui est sous [a,b[ sur UNE piste, sans rien décaler */
function dzmCarve(clips,tr,a,b){
  var out=[],taken=dzmTaken(clips);
  (clips||[]).forEach(function(c){
    if(!c||c.tr!==tr){out.push(c);return}
    var s=Number(c.start)||0,e=Number(c.end)||0,sp=dzmSpeedNum(c),si=Number(c.srcIn)||0,q;
    if(e<=a||s>=b){out.push(c);return}
    if(s<a)out.push(Object.assign({},c,{end:dzmR3(a)}));
    if(e>b){q=Object.assign({},c,{id:s<a?dzmFreeId(taken,c.id):c.id,start:dzmR3(b)});
      if(c.srcIn!=null||c.src)q.srcIn=dzmR3(si+(b-s)*sp);
      out.push(q)}});
  return out}
/* Rend {clips, clip} : `clip` est le clip POSÉ, avec son identifiant DÉFINITIF
   (renommé s'il était pris) — c'est lui que la branche jumelle relit. */
function dzmPose(clips,tr,clip,st,en,extra){
  var cs=clips||[],c=clip||{},taken=dzmTaken(cs);
  var k=Object.assign({},c,{tr:tr,start:dzmR3(st),end:dzmR3(en)},extra||{});
  /* `srcDur` EST UNE MESURE DE LA SOURCE, PAS UNE PROPRIÉTÉ DU CLIP. Seul le
     mode « remplir » le lit, pour calculer la vitesse ; le laisser ici le
     faisait entrer dans la sauvegarde et dans le payload de rendu (huit
     clés au lieu de sept, mesuré le 21/09/2026). Même doctrine que `srcIn`
     ci-dessous : pas de source, pas de fenêtre de source. */
  if("srcDur" in k)delete k.srcDur;
  if(c.id!=null&&taken[String(c.id)])k.id=dzmFreeId(taken,c.id);
  if(c.srcIn!=null||c.src){if(k.srcIn==null)k.srcIn=0}
  else if("srcIn" in k)delete k.srcIn;
  return {clips:cs.concat([k]),clip:k}}
function dzmInsereUn(clips,clip,mode,opts,tr){
  var st=Number(clip.start)||0,len=dzmR3((Number(clip.end)||0)-st),o=opts||{},p;
  if(!(len>0))len=dzmR3(Number(DZM_CLIP_DEFAUTS.video)||6);
  if(mode==="fin"){st=dzmTrackEnd(clips,tr);p=dzmPose(clips,tr,clip,st,st+len);
    return {clips:p.clips,pose:p.clip,mode:mode,note:""}}
  if(mode==="inserer"){
    var cut=dzmCarve(clips,tr,st,st);            /* fend à st sans rien retirer */
    cut=cut.map(function(c){return (c&&c.tr===tr&&Number(c.start)>=st-1e-6)?
      Object.assign({},c,{start:dzmR3(Number(c.start)+len),end:dzmR3(Number(c.end)+len)}):c});
    p=dzmPose(cut,tr,clip,st,st+len);
    return {clips:p.clips,pose:p.clip,mode:mode,note:""}}
  if(mode==="ripple_ecraser"){
    var h=Number(o.head);if(!isFinite(h))h=st;
    var under=(clips||[]).filter(function(c){return c&&c.tr===tr&&Number(c.start)<=h+1e-6&&Number(c.end)>h+1e-6})[0];
    if(!under)return dzmInsereUn(clips,clip,"ecraser",o,tr);
    var s0=Number(under.start),d=dzmR3(len-(Number(under.end)-s0));
    var rest=(clips||[]).filter(function(c){return c!==under}).map(function(c){
      return (c&&c.tr===tr&&Number(c.start)>=Number(under.end)-1e-6)?
        Object.assign({},c,{start:dzmR3(Number(c.start)+d),end:dzmR3(Number(c.end)+d)}):c});
    p=dzmPose(rest,tr,clip,s0,s0+len);
    return {clips:p.clips,pose:p.clip,mode:mode,note:""}}
  if(mode==="remplir"){
    var rg=dzmRangeFrom(o.range);
    if(!rg)return dzmInsereUn(clips,clip,"ecraser",o,tr);
    /* LA LONGUEUR DE LA SOURCE vient d'`opts` (ce que le câblage passe) ou,
       à défaut, du clip lui-même (ce que le banc édition passe). `dzmPose`
       retire la clé de la copie posée dans les deux cas. */
    var plage=dzmR3(rg.out-rg.in);
    var sd=Number(o.srcDur)||Number(clip.srcDur)||0,brut=sd>0?dzmR3(sd/plage):1;
    var sp=Math.max(.25,Math.min(4,brut)),nt="";
    /* L'ÉCRÊTAGE EST DIT. Une source de 100 s dans une plage de 3 s demande
       ×33,3 : on écrête à ×4, et le clip posé ne montrera donc PAS toute la
       source. Se taire ferait croire à un « remplir » exact. */
    if(sp!==brut)nt=sp>=4?"vitesse écrêtée à ×4 (source trop longue pour la plage)":
      "vitesse écrêtée à ×0,25 (source trop courte pour la plage)";
    p=dzmPose(dzmCarve(clips,tr,rg.in,rg.out),tr,clip,rg.in,rg.out,{speed:sp,srcIn:0});
    return {clips:p.clips,pose:p.clip,mode:mode,note:nt}}
  p=dzmPose(dzmCarve(clips,tr,st,st+len),tr,clip,st,st+len);
  return {clips:p.clips,pose:p.clip,mode:"ecraser",note:""}}
/* GARDE : un `clips` qui n'est même pas une liste est une ENTRÉE MOLLE, pas
   un projet vide légitime. MESURÉ au banc (T.insere(null,N,"ecraser",{})) :
   sans cette garde, `cs` retombait sur `[]` et le clip s'y posait quand même
   (1 clip rendu) — la même faiblesse que la garde `!clip` juste en dessous
   traite déjà côté clip, mais qui manquait côté `clips`. Avec la garde, les
   DEUX entrées molles rendent la même chose : rien n'est posé.
   REND {clips, track, mode, refus, note, id} : `refus` est un jeton de
   DZM_REFUS (`""` si rien à dire), `note` la phrase française à afficher
   (`""` sinon), `id` l'identifiant DÉFINITIF du clip posé (`null` si rien
   n'a été posé) — l'appelant en a besoin puisque `dzmPose` renomme un
   identifiant déjà pris. */
function dzmInsere(clips,clip,mode,opts){
  var o=opts||{},m=dzmModeOk(mode),lk=(o&&o.locked)||{},refus="",note="";
  if(!Array.isArray(clips))return {clips:[],track:null,mode:m,refus:"clips",note:"",id:null};
  var cs=clips;
  if(!clip||typeof clip!=="object")return {clips:cs.slice(),track:null,mode:m,refus:"clip",note:"",id:null};
  var tr=clip.tr;
  if(m==="dessus"){
    var ts=Array.isArray(o.tracks)?o.tracks:[],i,t,st=Number(clip.start)||0,en=Number(clip.end)||0,ix=-1;
    for(i=0;i<ts.length;i++)if(ts[i]&&ts[i].id===tr){ix=i;break}
    /* MÊME GENRE que la piste visée : filtrer sur `kind==="video"` seul
       envoyait un clip AUDIO de A1 sur V3 (mesuré). Piste visée absente de
       `opts.tracks` : `ix` reste −1, aucune candidate, on retombe en
       `ecraser` — le repli normal. */
    var kind=(ix>=0&&ts[ix])?ts[ix].kind:null,found=null;
    for(i=ix-1;i>=0;i--){t=ts[i];if(t&&t.kind===kind&&!dzmOverlap(cs,t.id,st,en)){found=t.id;break}}
    if(found==null){m="ecraser";refus="aucune_piste";
      note="aucune piste libre au-dessus : posé sur "+String(tr==null?"":tr).toUpperCase()}
    else{tr=found;m="ecraser"}}
  if(lk[tr])return {clips:cs.slice(),track:tr,mode:m,refus:"verrou",note:"",id:null};
  var res=dzmInsereUn(cs,clip,m,o,tr),pose=res.pose||null;
  note=dzmNoteJoin(note,res.note);
  if(o.twin&&typeof o.twin==="object"&&o.twin.tr){
    var tw=o.twin;
    if(lk[tw.tr]){
      /* Le jumeau est refusé, la vidéo est posée : `refus` prend le jeton du
         jumeau (l'appelant apprend ce qui MANQUE), `note` garde les deux
         phrases. */
      refus="verrou_jumeau";
      note=dzmNoteJoin(note,"piste "+String(tw.tr).toUpperCase()+
        " verrouillée : le son n'a pas été posé")}
    else{
      var tm=res.mode,tc;
      if(tm==="fin"||tm==="remplir"){
        tc=Object.assign({},tw,pose?{start:pose.start,end:pose.end}:
          {start:clip.start,end:clip.end});
        if(tm==="remplir"){tc.speed=dzmSpeedNum(pose);
          if(tw.srcIn!=null||tw.src)tc.srcIn=0}
        tm="ecraser"}
      else tc=Object.assign({},tw,{start:clip.start,end:clip.end});
      /* `o` est relayé TEL QUEL : `o.head` est une position de TIMELINE,
         commune aux deux pistes (la réécrire à `clip.start` désynchronisait
         le son de 4 s en `ripple_ecraser`, mesuré). */
      res.clips=dzmInsereUn(res.clips,tc,tm,o,tc.tr).clips}}
  return {clips:res.clips,track:tr,mode:res.mode,refus:refus,note:note,
    id:pose?pose.id:null}}

/* ── D-2 (21/09/2026) : LA RANGÉE DES MODES, dans le sélecteur d'assets ────
   Six chips EXCLUSIVES (role="radiogroup" / "radio"), une seule allumée :
   `data-on` est le marqueur d'état des chips voisines du bundle
   (`.svm-toolchip[data-on]`, son-vfx-montage.css l.323 — MESURÉ, la règle de
   base n'est PAS scopée au bandeau de transport, seules les surcharges de
   taille le sont), et `svm-toolchip` leur classe. Le composant ne décide de
   RIEN : il rend le mode courant et rappelle `onMode`. `dzmModeOk` le borne,
   donc une valeur inconnue allume « écraser » plutôt que rien.
   « remplir » EST ÉTEINT SANS PLAGE : `dzmInsere` retomberait en silence sur
   « écraser » (dzmInsereUn, branche "remplir" : `if(!rg)return … "ecraser"`),
   et un mode qui ment est pire qu'un mode grisé — le `title` dit quoi faire. */
var DZM_MODE_T={
  ecraser:"Écraser : le clip se pose à la tête et rogne ou fend ce qui est dessous.",
  inserer:"Insérer : fend à la tête et pousse la suite de la piste (ripple).",
  fin:"En fin : après le dernier clip de la piste, la tête est ignorée.",
  dessus:"Au-dessus : sur la piste vidéo libre la plus proche au-dessus (titres, PIP).",
  ripple_ecraser:"Écraser en ripple : remplace le clip sous la tête, la suite se recale à la nouvelle durée.",
  remplir:"Remplir la plage : bornes = plage I/O, vitesse calculée pour la remplir (V1)."};
function DzmModeBar(o){
  var cur=dzmModeOk(o&&o.mode),on=typeof (o&&o.onMode)==="function"?o.onMode:function(){};
  return r.jsx("div",{className:"dzm-modebar",role:"radiogroup",
    "aria-label":"Mode d'édition",
    children:DZM_MODES.map(function(m){
      var dis=m[0]==="remplir"&&!dzmRangeFrom(o&&o.range);
      return r.jsx("button",{className:"svm-toolchip dzm-modechip",role:"radio",
        "aria-checked":cur===m[0]?"true":"false","data-on":cur===m[0]?"":void 0,
        disabled:dis||void 0,
        title:DZM_MODE_T[m[0]]+(dis?" — posez d'abord une plage (I / U).":""),
        onClick:function(){on(m[0])},children:m[1]},m[0])})})}
/* Le LIBELLÉ français d'un mode, lu dans DZM_MODES (table gelée, source
   unique) : la note d'ajout d'`addAsset` le dit quand le mode appliqué n'est
   pas « écraser ». Un mode inconnu rend celui d'« écraser », comme dzmModeOk. */
function dzmModeLabel(m){
  var k=dzmModeOk(m),i;
  for(i=0;i<DZM_MODES.length;i++)if(DZM_MODES[i][0]===k)return DZM_MODES[i][1];
  return DZM_MODES[0][1]}

/* ── D-3 (21/09/2026) : ROLL, SLIP, SLIDE (Resolve : trim contextuel) ────
   Tout est PUR et relatif à l'ÉTAT DU POINTERDOWN (h0.clips) : le geste
   rejoue `ds` depuis l'origine, jamais depuis l'état précédent (dérive).
   slip  : Alt + glisser le centre — bornes fixes, srcIn -= ds × vitesse ;
   slide : Maj + glisser le centre — le clip bouge, le voisin gauche s'allonge,
           le voisin droit se raccourcit (min 0,3 s) et son srcIn avance ;
   roll  : Alt + glisser la jonction — fin du gauche = début du droit =
           jonction + ds (min 0,3 s de chaque côté), srcIn du droit suit ;
           la jonction doit être une VRAIE jonction (même piste, contact).
   BORNE DE TÊTE DE SOURCE (I1, revue du 21/09/2026) : reculer une jonction
   ou un clip recule le `srcIn` du voisin DROIT. Le déplacement `d` est donc
   borné par `-srcIn / vitesse` de ce voisin — borner la seule VALEUR écrite
   (`Math.max(0, …)`) laissait le clip commencer plus tôt avec un srcIn à 0,
   c'est-à-dire du média INVENTÉ avant la tête de sa source.
   `dzmSrcLen` rend la longueur TIMELINE (end-start) : la longueur SOURCE
   consommée vaut donc `dzmSrcLen(c)*vitesse` — c'est elle qui borne le slip.
   Doctrine mesurée dans `dzmRippleCut`/`dzmCarve` : on n'INVENTE jamais un
   `srcIn` sur un clip qui n'a ni `srcIn` ni `src` (un titre n'a pas de
   fenêtre de source). */
/* Voisins de CONTACT, sur la MEME piste, a un dixieme de seconde pres.
   DEPARTAGE, revue du 21/09/2026 : ce n'est PAS « le plus proche » — a
   gauche c'est la borne la plus AVANCEE (max end), a droite la plus
   RECULEE (min start). Les deux regles different des qu'un candidat
   chevauche legerement : end = start-0,02 et end = start+0,05 sont tous
   deux en contact, « max end » prend le second, « le plus proche » le
   premier. La regle retenue est celle des bornes, parce que c'est elle qui
   rend le voisin que le trim va DEPLACER.
   TOLERANCE : `<= .1+1e-9` et non `<= .1` — un contact de 0,1 s EXACTE se
   mesure 0,10000000000000009 en flottant (4 - 3,9) et tombait dehors.
   RESTES CONNUS, NON TRAITES ICI (revue du 21/09/2026) : la fonction est en
   O(n) par appel et le `mv` d'un geste la rappelle a chaque frame ; elle
   ignore les clips de longueur nulle ; et elle ne dit pas lequel de deux
   voisins EXACTEMENT a egalite l'emporte (le premier rencontre gagne). */
function dzmVoisins(cs,c){
  var g=null,d=null,tol=.1+1e-9;
  if(!Array.isArray(cs)||!c)return {g:g,d:d};
  cs.forEach(function(k){if(!k||k.tr!==c.tr||k.id===c.id)return;
    if(Math.abs(Number(k.end)-Number(c.start))<=tol&&(!g||Number(k.end)>Number(g.end)))g=k;
    if(Math.abs(Number(k.start)-Number(c.end))<=tol&&(!d||Number(k.start)<Number(d.start)))d=k});
  return {g:g,d:d}}
function dzmSlip(clips,id,ds,opts){
  var cs=Array.isArray(clips)?clips:[],d=Number(ds);if(!isFinite(d))d=0;
  var sd=Number(opts&&opts.srcDur)||0;
  var c=cs.filter(function(k){return k&&k.id===id})[0];
  /* pas de source, pas de fenêtre à faire glisser : geste sans objet */
  if(!c||(c.srcIn==null&&!c.src))return cs.slice();
  return cs.map(function(k){
    if(!k||k.id!==id)return k;
    var sp=dzmSpeedNum(k),len=dzmSrcLen(k)*sp,si=(Number(k.srcIn)||0)-d*sp;
    if(si<0)si=0;
    if(sd>0&&si>sd-len)si=Math.max(0,sd-len);
    return Object.assign({},k,{srcIn:dzmR3(si)})})}
function dzmSlide(clips,id,ds){
  var cs=Array.isArray(clips)?clips:[],d=Number(ds);if(!isFinite(d))d=0;
  var c=cs.filter(function(k){return k&&k.id===id})[0];
  if(!c||!d)return cs.slice();
  var v=dzmVoisins(cs,c);
  if(!v.d)return cs.slice();                     /* sans voisin droit : pas un slide */
  var dmax=(Number(v.d.end)-Number(v.d.start))-.3,
      dmin=v.g?-((Number(v.g.end)-Number(v.g.start))-.3):-Number(c.start);
  /* I1 (revue du 21/09/2026) : reculer le clip fait RECULER le srcIn du
     voisin droit, et `Math.max(0,...)` ne bornait que la VALEUR ECRITE —
     le voisin gardait alors sa nouvelle borne de gauche avec un srcIn 0,
     c'est-a-dire du media INVENTE avant la tete de sa source. C'est `d`
     qu'il faut borner, pas le srcIn. */
  if(v.d.srcIn!=null||v.d.src)
    dmin=Math.max(dmin,-(Number(v.d.srcIn)||0)/dzmSpeedNum(v.d));
  d=Math.max(dmin,Math.min(dmax,d));
  return cs.map(function(k){
    if(!k)return k;
    if(k.id===c.id)return Object.assign({},k,
      {start:dzmR3(Number(k.start)+d),end:dzmR3(Number(k.end)+d)});
    if(v.g&&k.id===v.g.id)return Object.assign({},k,{end:dzmR3(Number(k.end)+d)});
    if(k.id===v.d.id){var q=Object.assign({},k,{start:dzmR3(Number(k.start)+d)});
      if(k.srcIn!=null||k.src)q.srcIn=dzmR3(Math.max(0,(Number(k.srcIn)||0)+d*dzmSpeedNum(k)));
      return q}
    return k})}
function dzmRoll(clips,leftId,rightId,ds){
  var cs=Array.isArray(clips)?clips:[],d=Number(ds);if(!isFinite(d))d=0;
  var L=cs.filter(function(k){return k&&k.id===leftId})[0],
      R=cs.filter(function(k){return k&&k.id===rightId})[0];
  if(!L||!R||!d)return cs.slice();
  /* I2 (revue du 21/09/2026) : un roll n'a de sens que sur une JONCTION —
     meme piste, bornes en contact. Sans cette garde, `roll(cs,"a","z")` sur
     deux clips etrangers rallongeait l'un et deplacait l'autre, chacun dans
     son coin : deux clips mutiles et aucune jonction deplacee. */
  if(L.tr!==R.tr||Math.abs(Number(R.start)-Number(L.end))>.1+1e-9)return cs.slice();
  var dmin=-((Number(L.end)-Number(L.start))-.3),dmax=(Number(R.end)-Number(R.start))-.3;
  /* I1 : meme mesure que dans le slide — reculer la jonction recule le
     srcIn du clip DROIT ; on borne `d`, pas la valeur ecrite. */
  if(R.srcIn!=null||R.src)dmin=Math.max(dmin,-(Number(R.srcIn)||0)/dzmSpeedNum(R));
  d=Math.max(dmin,Math.min(dmax,d));
  return cs.map(function(k){
    if(!k)return k;
    if(k.id===L.id)return Object.assign({},k,{end:dzmR3(Number(k.end)+d)});
    if(k.id===R.id){var q=Object.assign({},k,{start:dzmR3(Number(k.start)+d)});
      if(k.srcIn!=null||k.src)q.srcIn=dzmR3(Math.max(0,(Number(k.srcIn)||0)+d*dzmSpeedNum(k)));
      return q}
    return k})}

/* ── D-5 (21/09/2026) : LES MARQUEURS ──────────────────────────────────────
   Un marqueur est {id, t, color, title, note} : un repère posé sur la RÈGLE,
   à la tête de lecture, que l'on retrouve d'un raccourci et que l'index
   (Ctrl+M) liste, renomme, recolore et retire.
   TROIS règles qui ne se devinent pas :
     · POSER SUR UN MARQUEUR LE RETIRE (bascule à ±DZM_MARKER_EPS). C'est le
       geste de Resolve : la même touche pose et dépose. `{force:true}` passe
       outre — l'index, lui, doit pouvoir doubler un repère si on le lui
       demande ;
     · `dzmMarkerNext` IGNORE le marqueur SOUS LA TÊTE (même EPS). « Aller au
       suivant » depuis un marqueur doit aller au SUIVANT, pas rester sur
       place. Un `>v+1e-6` nu rendait 2,004 pour une tête à 2,000 — mesuré ;
     · la liste est TRIÉE PAR t, toujours : la règle et l'index lisent la
       même chronologie, et `markerNext` peut s'arrêter au premier trouvé. */
var DZM_MARKER_COLORS=Object.freeze([["or","#f0b429"],["rouge","#e5484d"],
  ["vert","#46a758"],["bleu","#3e8be2"],["violet","#8e4ec6"],
  ["cyan","#12a594"]].map(function(p){return Object.freeze(p)}));
var DZM_MARKER_EPS=.15;
var DZM_MARKER_MAX=200;            /* même plafond que le backend */
var DZM_MARKER_TITRE_MAX=200,DZM_MARKER_NOTE_MAX=1e3;
function dzmMarkerColor(c){
  return DZM_MARKER_COLORS.some(function(o){return o[0]===c})?c:"or"}
function dzmMarkerHex(c){
  var o=DZM_MARKER_COLORS.filter(function(x){return x[0]===c})[0];
  return (o||DZM_MARKER_COLORS[0])[1]}
/* LE MEME `t` DES DEUX COTES (revue du 21/09/2026 ; l'etiquette « I-6 »
   qu'avait ce bloc etait FAUSSE — I-6 nommait les `.index()` nus du banc).
   `Number("")` vaut ZERO en JavaScript, quand `float("")` LEVE en Python :
   un marqueur `{t:""}` etait accepte a 0 s par le client et jete par le
   serveur, donc il disparaissait au rechargement sans un mot.
   R-3 (seconde revue) : LE TYPE EST REFUSE AVANT LA VALEUR. `Number(true)`
   vaut 1 et `Number([])` vaut 0 : un booleen devenait un marqueur a 1 s et
   un tableau vide un marqueur a 0 s — exactement ce que `_save_record`
   refuse depuis son test `isinstance(t, bool)`. Seuls un NOMBRE et une
   CHAINE sont des temps. */
function dzmMarkerT(v){
  if(typeof v!=="number"&&typeof v!=="string")return null;
  if(typeof v==="string"&&!v.replace(/\s/g,""))return null;
  var n=Number(v);
  return (isFinite(n)&&n>=0)?n:null}
function dzmMarkerTexte(v,max){
  var s=v==null?"":String(v);return s.length>max?s.slice(0,max):s}
function dzmMarkerId(ms){
  var n=1,id;
  do{id="m"+n++}while((ms||[]).some(function(m){return m&&m.id===id}));
  return id}
function dzmMarkersSort(ms){
  return ms.slice().sort(function(a,b){return a.t-b.t})}
function dzmMarkerAdd(ms,t,o){
  var l=Array.isArray(ms)?ms.filter(Boolean):[],v=dzmMarkerT(t);
  if(v==null)return l.slice();
  /* I-1 (revue du 21/09/2026) : LE PLUS PROCHE, PAS LE PREMIER. Le filtre
     rendait le premier marqueur DE LA LISTE dans la tolerance ; avec A a
     1,00 et B a 1,10, une tete a 1,09 retirait A. Mesure du 21/09/2026.
     La liste est triee, mais deux marqueurs peuvent etre a moins de 2 EPS
     l'un de l'autre et encadrer la tete : c'est la DISTANCE qui tranche. */
  var near=null,dmin=DZM_MARKER_EPS;
  l.forEach(function(m){
    var d=Math.abs(Number(m.t)-v);
    if(d<=dmin+1e-9&&(near===null||d<dmin)){near=m;dmin=d}});
  if(near&&!(o&&o.force))return l.filter(function(m){return m!==near});
  if(l.length>=DZM_MARKER_MAX)return l.slice();
  var m={id:dzmMarkerId(l),t:dzmR3(v),color:dzmMarkerColor(o&&o.color),
    title:dzmMarkerTexte(o&&o.title,DZM_MARKER_TITRE_MAX),
    note:dzmMarkerTexte(o&&o.note,DZM_MARKER_NOTE_MAX)};
  return dzmMarkersSort(l.concat([m]))}
function dzmMarkerRemove(ms,id){
  return (Array.isArray(ms)?ms:[]).filter(function(m){
    return !!m&&m.id!==id})}
/* PATCH PARTIEL, jamais un remplacement : seules les clés PRÉSENTES dans
   `patch` bougent, et chacune repasse par l'assainissement — l'index envoie
   ce que l'utilisateur tape, pas ce que la couche voudrait. Un id inconnu
   rend la liste telle quelle. */
function dzmMarkerUpdate(ms,id,patch){
  var p=patch&&typeof patch==="object"?patch:{};
  return (Array.isArray(ms)?ms:[]).filter(Boolean).map(function(m){
    if(m.id!==id)return m;
    var q=Object.assign({},m);
    if("color" in p)q.color=dzmMarkerColor(p.color);
    if("title" in p)q.title=dzmMarkerTexte(p.title,DZM_MARKER_TITRE_MAX);
    if("note" in p)q.note=dzmMarkerTexte(p.note,DZM_MARKER_NOTE_MAX);
    return q})}
function dzmMarkerNext(ms,t,dir){
  var l=dzmMarkersSort((Array.isArray(ms)?ms:[]).filter(Boolean)),
      v=Number(t)||0,i;
  if(dir>=0){for(i=0;i<l.length;i++)if(l[i].t>v+DZM_MARKER_EPS)return l[i].t}
  else{for(i=l.length-1;i>=0;i--)if(l[i].t<v-DZM_MARKER_EPS)return l[i].t}
  return null}
/* RESTAURATION. TROIS regles, et la deuxieme est celle qui manquait :
     · les identifiants sont REGENERES (m1..mN), jamais relus du disque —
       deux marqueurs d'un vieux fichier pouvaient porter le meme, et
       `markerRemove` en aurait retire deux ;
     · L'INVARIANT D'ESPACEMENT (>= DZM_MARKER_EPS) est tenu ICI AUSSI.
       I-2, revue du 21/09/2026 : `markerAdd` etait le seul a le tenir, donc
       un fichier (ou un autre client) pouvait poser 1,00 et 1,12 — et le
       second etait INJOIGNABLE par Ctrl+haut / Ctrl+bas, qui sautent tout ce
       qui est a moins d'un EPS. Le tri PRECEDE le filtre : c'est toujours le
       PREMIER de deux voisins qui reste, et les doublons exacts tombent par
       la meme regle (distance nulle) ;
     · R-1 (seconde revue du 21/09/2026) : LA BORNE EST LARGE (`<=`), PAS
       STRICTE. `markerNext` saute tout ce qui n'est pas `t > v + EPS` :
       un couple a EXACTEMENT 0,150 s passait un filtre strict et restait
       injoignable DANS LES DEUX SENS (mesure : 697 couples au millieme
       entre 0 et 10 s). `markerAdd` traitait deja « exactement EPS »
       comme trop proche (`d <= dmin + 1e-9`) : les trois bornes disent
       desormais la meme chose ;
     · le plafond s'applique APRES le filtre — 200 marqueurs UTILES, pas 200
       entrees dont la moitie serait jetee. Meme ordre que `_save_record`. */
function dzmMarkersFrom(v){
  var brut=[];
  (Array.isArray(v)?v:[]).forEach(function(m){
    if(!m||typeof m!=="object")return;
    var t=dzmMarkerT(m.t);if(t==null)return;
    brut.push({t:dzmR3(t),color:dzmMarkerColor(m.color),
      title:dzmMarkerTexte(m.title,DZM_MARKER_TITRE_MAX),
      note:dzmMarkerTexte(m.note,DZM_MARKER_NOTE_MAX)})});
  var out=[];
  dzmMarkersSort(brut).forEach(function(m){
    if(out.length>=DZM_MARKER_MAX)return;
    if(out.length&&m.t-out[out.length-1].t<=DZM_MARKER_EPS+1e-9)return;
    m.id="m"+(out.length+1);out.push(m)});
  return out}
/* LES LOSANGES SUR LA RÈGLE. Même gouttière de 88 px que `DzmRangeBar`, et
   même borne : un marqueur PERSISTÉ survit à un raccourcissement de la durée
   et `t` peut alors dépasser `dur` — sans le Math.min, `left` passait 100 %.
   `svmTcFF` (le timecode du bloc sonvfx) est résolu À L'APPEL et jamais au
   chargement : sous node, la couche est seule et le symbole n'existe pas. */
/* I-5 : LA COMBO N'EST PAS ECRITE EN DUR. Les quatre actions du lot sont
   REMAPPABLES (panneau « ? »), et une infobulle qui dit « Maj+M » apres un
   remappage MENT. `svmKeyLabelNow` est la lecture de la keymap vivante au
   NIVEAU MODULE du bundle (celle que le tiroir Sons emploie deja, 3
   occurrences) — `svmKeyLabel`, lui, vit DANS le composant et lit son `km`
   de closure : la couche ne peut pas l'atteindre. Resolu A L'APPEL, comme
   `svmTcFF`, et avec le meme repli : sous node le symbole n'existe pas, et
   `svmKeyLabelNow` rend "" sur une action inconnue. */
/* LA RÉSOLUTION EST ÉCRITE UNE SEULE FOIS (22/09/2026) : D-21 a un SECOND
   texte à faire parler la keymap (la note de retrait de la piste T1), et
   recopier la ligne `typeof svmKeyLabelNow` aurait fait DEUX résolutions du
   même symbole — c'est exactement ce que la ligne
   `D5_I5_les_trois_textes_lisent_la_keymap_vivante` compte à UN. Le repli
   reste un ARGUMENT : chaque appelant nomme le sien, aucun défaut caché. */
function dzmCombo(id,repli){
  var f=typeof svmKeyLabelNow==="function"?svmKeyLabelNow:null;
  return (f&&f(id))||repli}
function dzmMarkerCombo(){return dzmCombo("marker_toggle","Maj+M")}
function DzmMarkers(o){
  var ms=Array.isArray(o&&o.markers)?o.markers.filter(Boolean):[],
      d=Number(o&&o.dur)||1,go=o&&o.onSeek;
  var dzTc=typeof svmTcFF==="function"?svmTcFF:dzmSecs;
  return ms.map(function(m){
    var l=Math.min(100,Math.max(0,(Number(m.t)||0)/d*100));
    return r.jsx("button",{className:"dzm-mk",
      "aria-label":"Marqueur "+dzTc(m.t)+(m.title?" — "+m.title:""),
      title:(m.title||"marqueur")+" · "+dzTc(m.t)+(m.note?"\n"+m.note:"")+
        "\nclic : aller · "+dzmMarkerCombo()+" à la tête : retirer",
      style:{left:"calc(88px + (100% - 88px) * "+(l/100)+")",
        background:dzmMarkerHex(m.color)},
      /* C-1 (revue du 21/09/2026) : SANS CECI LE CLIC NE VA NULLE PART. Le
         parent `.svm-ruler` porte `onPointerDown:rulerDown`, qui prend la
         capture du pointeur et fait `seekTo(phFromEvent(e, el))` : la tete
         partait SOUS LE CURSEUR avant que le `click` du bouton n'arrive, et
         le losange semblait mort a deux pixels pres. Meme parade que
         `vpDown` du bundle (`e.stopPropagation(); e.preventDefault()`), et
         c'est le POINTERDOWN qu'il faut avaler : le `click`, lui, arrive
         trop tard. */
      onPointerDown:function(e){
        if(e&&e.stopPropagation)e.stopPropagation();
        if(e&&e.preventDefault)e.preventDefault()},
      onClick:function(){if(go)go(m.t)}},m.id)})}
/* L'INDEX. Le titre part sur `onBlur` (et sur Entrée), PAS sur chaque
   frappe : `onChange` poussait un instantané d'historique par caractère et
   « Annuler » remontait lettre à lettre. La couleur, elle, part tout de
   suite — un <select> ne se frappe pas en rafale. */
function DzmMarkerIndex(o){
  var ms=Array.isArray(o&&o.markers)?o.markers.filter(Boolean):[];
  var dzTc=typeof svmTcFF==="function"?svmTcFF:dzmSecs;
  function titre(m,e){
    var v=e&&e.target?e.target.value:"";
    if(v===m.title)return;
    if(o.onChange)o.onChange(m.id,{title:v})}
  return r.jsxs("div",{className:"svm-pop dzm-mkidx",style:{top:96},children:[
    r.jsx("div",{className:"svm-poptitle",children:"Marqueurs — "+ms.length}),
    ms.length?ms.map(function(m){
      return r.jsxs("div",{className:"dzm-mkrow",children:[
        r.jsx("button",{className:"svm-fxchip",title:"aller à ce marqueur",
          onClick:function(){if(o.onSeek)o.onSeek(m.t)},children:dzTc(m.t)}),
        r.jsx("select",{className:"dzm-mkcol",value:m.color,
          "aria-label":"Couleur du marqueur "+dzTc(m.t),
          onChange:function(e){
            if(o.onChange)o.onChange(m.id,{color:e.target.value})},
          children:DZM_MARKER_COLORS.map(function(c){
            return r.jsx("option",{value:c[0],children:c[0]},c[0])})}),
        /* I-3 (revue du 21/09/2026) : LA CLE PORTE LE TITRE. Le champ est
           NON CONTROLE (`defaultValue`) — c'est ce qui l'empeche de remonter
           a chaque frappe — mais React IGNORE `defaultValue` a la mise a
           jour : apres Ctrl+Z, le projet rendait l'ancien titre pendant que
           l'input gardait le neuf. Une cle qui porte la VALEUR force le
           remontage des que l'amont change, et le champ repart de la bonne
           chaine. CE QUE CELA COUTE, ET C'EST ASSUME : valider par Entree
           remonte le titre, donc change la cle, donc remonte l'input — le
           focus est perdu. Un etat local resynchronise par `useEffect` le
           garderait, mais c'est LUI qu'on ne veut pas : la raison de la cle
           porteuse est precisement qu'AUCUN etat local ne doit doubler le
           projet, sinon Ctrl+Z repeint l'hote et pas le champ. (Correctif
           du 22/09/2026 : ce commentaire donnait une raison FAUSSE — « ce
           n'est pas un composant a hooks » — alors que l'hote le monte par
           un `r.jsx` sur `MarkerIndex`, donc comme un vrai composant,
           ou un hook serait parfaitement legal. Le choix est delibere, pas
           impose.) */
        r.jsx("input",{className:"dzm-mktitre",defaultValue:m.title,
          placeholder:"titre","aria-label":"Titre du marqueur "+dzTc(m.t),
          onBlur:function(e){titre(m,e)},
          onKeyDown:function(e){if(e.key==="Enter")titre(m,e)}},
          m.id+"|"+m.title),
        r.jsx("button",{className:"svm-minibtn",title:"Retirer ce marqueur",
          "aria-label":"Retirer le marqueur "+dzTc(m.t),
          onClick:function(){if(o.onRemove)o.onRemove(m.id)},
          children:"\u2716"})]},m.id)}):
      r.jsx("div",{className:"svm-note",
        children:"Aucun marqueur — "+dzmMarkerCombo()+
          " en pose un à la tête de lecture."}),
    r.jsx("div",{className:"svm-poprow",children:
      r.jsx("button",{className:"svm-secbtn",title:"Fermer l'index des marqueurs",onClick:o&&o.onClose,
        children:"Fermer"})})]})}

/* ── D-4 : ÉCHANGER un plan avec son voisin de gauche (dir −1) ou de droite ─
   `dzmSwap(clips,id,dir)` échange le clip `id` avec son voisin de contact
   (≤0,1s, `dzmVoisins`) côté `dir`. Les DEUX clips gardent leur durée et
   leurs autres champs (srcIn compris) : seules `start`/`end` bougent, pour
   que l'échange se lise par les BORNES et non par l'index dans le tableau
   rendu.
   LES DEUX BORNES EXTÉRIEURES DU COUPLE SONT ANCRÉES, PAS UNE SEULE
   (correctif du 21/09/2026, revue) : `s=a.start` ET `e=b.end` sont lus
   AVANT tout calcul, et les deux clips sont reposés À L'INTÉRIEUR de
   `[s,e]` — `b` en tête (`{start:s,end:s+lb}`), `a` en queue
   (`{start:e-la,end:e}`). Ancrer `s` seul (comme la première version)
   RECALCULAIT la borne droite de `a` depuis `s+lb+la` : un écart entre
   les deux clips (le trou ou le chevauchement toléré par `dzmVoisins`,
   jusqu'à 0,1 s) se retrouvait ABSORBÉ — un trou de 0,05 s TÉLÉPORTAIT
   `a` au raccord suivant (mesuré : p1[0,4] p2[4.05,8] p3[8,10] →
   `swap(p2,-1)` rendait p2[0,3.95] p1[3.95,7.95] p3[8,10], p1 collé à p3
   au lieu de laisser 0,05 s) et un chevauchement de 0,05 s faisait MORDRE
   `a` sur son voisin suivant. Avec les deux bornes ancrées, l'écart ne
   disparaît ni ne se déplace vers l'extérieur : il RESTE AU RACCORD
   INTÉRIEUR, maintenant entre les deux clips échangés (p2[0,3.95]
   p1[4,8] p3[8,10] — le même trou de 0,05 s, simplement de l'autre
   côté). Deux clips JOINTIFS (écart nul) rendent donc exactement le
   résultat d'avant : ancrer une borne ou les deux ne change rien quand
   il n'y a rien à préserver.
   TRANSITION D'ENTRÉE, ÉCART ASSUMÉ ET DATÉ (21/09/2026) : `transition`/
   `transition_s` est portée par le clip mais c'est une propriété du BORD
   ENTRANT — `montage_service` applique le fondu du segment k au raccord
   k-1|k, et le segment 0 (premier de la piste) n'en consomme aucun.
   `dzmSwap` ne touche qu'à `start`/`end` : la transition reste attachée
   au CLIP qui la porte, donc échanger déplace le fondu vers la nouvelle
   place de ce clip — et le fait DISPARAÎTRE s'il devient le premier de
   la piste (plus de raccord k-1|k à son entrée). Non couvert par ce lot,
   à reporter dans la conception de la tâche 10 (les jonctions/transitions
   de D-4/D-11 suivantes). */
function dzmSwap(clips,id,dir){
  var cs=Array.isArray(clips)?clips:[],c=cs.filter(function(k){return k&&k.id===id})[0];
  if(!c||!(dir===1||dir===-1))return cs.slice();
  var v=dzmVoisins(cs,c),n=dir<0?v.g:v.d;
  if(!n)return cs.slice();
  var a=dir<0?n:c,b=dir<0?c:n;                   /* a précède b */
  var la=Number(a.end)-Number(a.start),lb=Number(b.end)-Number(b.start);
  var s=Number(a.start),e=Number(b.end);         /* bornes extérieures ancrées */
  return cs.map(function(k){
    if(k===b)return Object.assign({},k,{start:dzmR3(s),end:dzmR3(s+lb)});
    if(k===a)return Object.assign({},k,{start:dzmR3(e-la),end:dzmR3(e)});
    return k})}

/* ── D-20 (21/09/2026) : LA GALERIE DES TRANSITIONS ────────────────────────
   Le backend sert le catalogue (GET /api/montage/transitions : six familles,
   58 transitions, leurs libellés et un drapeau `live`). Ici : la FORME de la
   galerie — « coupe » en tête, puis les historiques du bundle QUI NE SONT PAS
   au catalogue (« historiques »), puis les familles du serveur.
   POURQUOI UNE COPIE DES FAMILLES CÔTÉ CLIENT (`DZM_TRANS_FAM`) ALORS QUE LE
   SERVEUR LES SERT : ce n'est pas la même question. Le catalogue dit CE QUI
   EXISTE (les libellés, le direct) et il arrive par le réseau, donc en retard
   ou jamais ; `DZM_TRANS_FAM` dit À QUOI RESSEMBLE une transition, et c'est
   ce que la micro-scène CSS doit savoir AU PREMIER RENDU pour animer la
   tuile. La table est donc une table de STYLE, pas une autorité : elle ne
   décide d'aucun rendu, elle choisit une animation. Le repli sur le
   catalogue (la boucle `fs` ci-dessous) couvre le jour où le serveur
   ajouterait une famille que cette copie ne connaît pas encore : la tuile
   portera son `data-fam`, sans animation dédiée, plutôt que rien.
   La correspondance des deux tables est tenue par un banc croisé. */
var DZM_TRANS_FAM={
  fondus:["fade","fadeblack","fadewhite","fadegrays","fadefast","fadeslow","dissolve","distance"],
  glissements:["slideleft","slideright","slideup","slidedown","coverleft","coverright","coverup","coverdown","revealleft","revealright","revealup","revealdown"],
  volets:["wipeleft","wiperight","wipeup","wipedown","wipetl","wipetr","wipebl","wipebr","smoothleft","smoothright","smoothup","smoothdown","diagtl","diagtr","diagbl","diagbr"],
  formes:["circlecrop","rectcrop","circleopen","circleclose","vertopen","vertclose","horzopen","horzclose","radial"],
  zooms:["zoomin","squeezeh","squeezev"],
  pixels:["pixelize","hblur","hlslice","hrslice","vuslice","vdslice","hlwind","hrwind","vuwind","vdwind"]};
/* la DIRECTION du geste, posée en data-dir : une seule animation par famille
   suffit alors pour les quatre sens. Les « slice » et les « wind » vont à
   l'envers de leur nom (hl = moitié gauche qui part, donc l'entrant vient de
   la droite) — c'est mesuré sur ffmpeg, pas deviné du nom. */
var DZM_TRANS_DIR={left:["slideleft","coverleft","revealleft","wipeleft","smoothleft","hrslice","hrwind"],
  right:["slideright","coverright","revealright","wiperight","smoothright","hlslice","hlwind"],
  up:["slideup","coverup","revealup","wipeup","smoothup","vuslice","vuwind"],
  down:["slidedown","coverdown","revealdown","wipedown","smoothdown","vdslice","vdwind"]};
/* les familles du catalogue, ASSAINIES une fois pour toutes : le JSON vient
   du reseau, une entree nulle ou sans `items` y est possible, et les quatre
   lecteurs ci-dessous la traversaient (mesure : `{familles:[null,…]}` tuait
   le shim sur `fs[i].items` — rougir, pas mourir). */
function dzmTransFams(cat){
  var fs=cat&&Array.isArray(cat.familles)?cat.familles:[];
  return fs.filter(function(f){return f&&f.id!=null}).map(function(f){
    return {id:f.id,label:f.label,items:(Array.isArray(f.items)?f.items:[]).filter(function(it){return it&&it.id!=null})}})}
/* LES DEUX TABLES SONT GELEES EN PROFONDEUR : `Object.freeze` est
   SUPERFICIEL -- il scelle l'objet, pas les tableaux qu'il porte, et
   `TRANS_FAM.fondus.push("zzz")` passait donc en silence. Les tableaux
   sont scelles AVANT l'objet ; l'export ne fait que les repasser. */
(function(){var k;
  for(k in DZM_TRANS_FAM)Object.freeze(DZM_TRANS_FAM[k]);
  for(k in DZM_TRANS_DIR)Object.freeze(DZM_TRANS_DIR[k]);
  Object.freeze(DZM_TRANS_FAM);Object.freeze(DZM_TRANS_DIR)})();
/* LES DEUX QUE LE BUNDLE ANIME DEJA AUTREMENT. `son-vfx-montage.css`
   (intouchable) porte sept regles `.svm-tprev[data-tt="…"] .svm-tb`.
   Cinq visent des noms HORS catalogue (cut, glitch, slide, flash, fade
   mis a part) ; DEUX visent des noms QUI SONT au catalogue et demandent
   une animation DIFFERENTE de celle de leur famille : `dissolve`
   (svmtDiss) et `fadeblack` (svmtCutMid + le voile ::after). Ces deux-la
   ne recoivent PAS de `data-fam` : ils gardent les regles du bundle, et
   nos six regles de famille restent toutes a la MEME specificite
   (0,4,0) -- c'est ce qui permet a la pause au repos, ecrite apres et a
   la meme specificite, de les couvrir TOUTES. Un `:not()` dans la regle
   `fondus` aurait pese (0,6,0) et laisse SIX tuiles (fade, fadewhite,
   fadegrays, fadefast, fadeslow, distance) s'agiter en permanence : la
   liste est une decision de CASCADE, pas de style. `fade` en est absent
   a dessein -- sa regle du bundle et la notre demandent la MEME svmtFade,
   et la notre lui rend un delai de famille. */
var DZM_TRANS_TT=Object.freeze(["dissolve","fadeblack"]);
function dzmTransFamily(id,cat){
  if(id==="cut")return "coupe";
  var k;for(k in DZM_TRANS_FAM)if(DZM_TRANS_FAM[k].indexOf(id)>=0)return k;
  var fs=dzmTransFams(cat),i,j;
  for(i=0;i<fs.length;i++)for(j=0;j<fs[i].items.length;j++)if(fs[i].items[j].id===id)return String(fs[i].id);
  return ""}
function dzmTransDir(id){var k;for(k in DZM_TRANS_DIR)if(DZM_TRANS_DIR[k].indexOf(id)>=0)return k;return ""}
/* `live` est dit par le SERVEUR et par lui seul (D-12 joue ces fondus-là dans
   le lecteur vivant) : pas de copie cliente. Sans catalogue, seule la coupe
   franche est « en direct » — elle ne demande aucun voile. */
function dzmTransLive(id,cat){
  var fs=dzmTransFams(cat),i,j;
  for(i=0;i<fs.length;i++)for(j=0;j<fs[i].items.length;j++){var it=fs[i].items[j];if(it.id===id)return !!it.live}
  return id==="cut"}
function dzmTransLabel(id,legacy,cat){
  var fs=dzmTransFams(cat),i,j;
  for(i=0;i<fs.length;i++)for(j=0;j<fs[i].items.length;j++){var it=fs[i].items[j];if(it.id===id&&it.label)return String(it.label)}
  var lg=(Array.isArray(legacy)?legacy:[]).filter(function(o){return o&&o[0]===id})[0];
  return lg?String(lg[1]):String(id)}
/* LE PREMIER GAGNE, DES DEUX COTES. `dzmTransLabel` rend le libelle de la
   PREMIERE famille du catalogue qui porte l'id, et `dzmTransFamily` la
   PREMIERE famille de la copie cliente : un nom servi dans deux familles
   se range dans celle du haut. La grille, elle, ne cherche RIEN : chaque
   tuile lit `it.label` DE SA FAMILLE, celui que `dzmTransList` y a
   depose -- une tuile ne peut donc pas porter le libelle d'une autre
   famille. Le banc croise mesure quaucun des 58 noms du service n est
   dans deux familles : ce commentaire dit ce qui arriverait, il ne decrit
   pas un defaut vivant. */
function dzmTransList(legacy,cat){
  var lg=Array.isArray(legacy)?legacy:[],fs=dzmTransFams(cat);
  var inCat={},out=[{id:"coupe",label:"coupe",items:[{id:"cut",label:dzmTransLabel("cut",lg,cat),live:!0}]}];
  fs.forEach(function(f){f.items.forEach(function(it){inCat[it.id]=1})});
  /* DEDOUBLONNE PAR ID : `SVM_TRANS` est une liste de paires, rien n'y
     interdit deux entrees de meme nom, et la galerie aurait rendu deux
     tuiles de MEME CLE React -- un avertissement en console et une tuile
     qui ne se met pas a jour. Le PREMIER gagne, comme partout ici. */
  var vus={},hist=lg.filter(function(o){
    if(!o||o[0]==="cut"||inCat[o[0]]||vus[o[0]])return !1;
    vus[o[0]]=1;return !0}).map(function(o){return {id:String(o[0]),label:String(o[1]),live:dzmTransLive(o[0],cat)}});
  if(hist.length)out.push({id:"historiques",label:"historiques",items:hist});
  fs.forEach(function(f){out.push({id:String(f.id),label:String(f.label||f.id),
    items:f.items.map(function(it){return {id:String(it.id),label:String(it.label||it.id),live:!!it.live}})})});
  return out}
/* la grille : une rangée de titre par famille, les tuiles reprennent la
   classe `.svm-transtile` et la micro-scène `.svm-tprev` du bundle ; la
   famille et la direction sont posées en data-* pour l'animation CSS de
   montage.css (une règle par famille, la direction en variable).
   `data-tt` EST GARDÉ sur toutes les tuiles, y compris les 58 neuves :
   c'est LUI qui porte, dans son-vfx-montage.css (intouchable), l'animation
   de la moitié GAUCHE et le voile des fondus au noir/blanc. La pause au
   repos, le survol et le figement de la tuile choisie sont REPOSÉS sur
   `data-fam` dans montage.css : nos règles de famille écrivent le
   raccourci `animation:`, qui remet `animation-play-state` à `running`. */
function DzmTransGrid(o){
  var lst=dzmTransList(o&&o.legacy,o&&o.cat),cur=o&&o.cur,on=typeof (o&&o.onPick)==="function"?o.onPick:function(){};
  /* LE CATALOGUE EST-IL ARRIVE ? Sans lui, `live` est FAUX pour tout sauf
     la coupe -- et ecrire « visible apres Preview » sur les six
     historiques serait une affirmation que rien ne soutient : le direct
     est dit par le SERVEUR (D-12), pas par nous. Tant qu il n a pas
     repondu, l'infobulle se tait sur ce point. */
  var dit=!!(o&&o.cat&&Array.isArray(o.cat.familles)&&o.cat.familles.length);
  return lst.map(function(f){
    return r.jsxs("div",{className:"dzm-transfam",role:"group",
      "aria-label":"Transitions — "+f.label,children:[
      r.jsx("div",{className:"dzm-transfam-t",children:f.label}),
      r.jsx("div",{className:"svm-transgrid dzm-transgrid",children:f.items.map(function(it){
        /* `data-fam` est OMIS (pas vide) pour les deux que le bundle anime
           deja : `[data-fam]` matche un attribut PRESENT, fut-il vide. */
        var fam=DZM_TRANS_TT.indexOf(it.id)>=0?"":dzmTransFamily(it.id,o&&o.cat);
        var dir=dzmTransDir(it.id);
        return r.jsxs("button",{className:"svm-transtile","data-sel":cur===it.id?"":void 0,
          "aria-pressed":cur===it.id,
          title:it.label+" ("+it.id+")"+(dit&&!it.live?" — visible après Preview":""),
          onClick:function(){on(it.id)},children:[
          r.jsxs("span",{className:"svm-tprev","data-tt":it.id,"data-fam":fam||void 0,"data-dir":dir||void 0,"aria-hidden":!0,
            children:[r.jsx("i",{className:"svm-ta"}),r.jsx("i",{className:"svm-tb"})]}),
          r.jsx("span",{className:"svm-ttl",children:it.label})]},it.id)})})]},f.id)})}

/* ── D-12 (21/09/2026) : LES FONDUS SIMPLES JOUES EN DIRECT, PAR UN VOILE ──
   Le lecteur vivant n'a qu'UN clip visible a la fois (`svmActiveV1` en rend
   un seul) : un vrai crossfade A/B demanderait deux hotes et deux elements
   media. Un VOILE suffit pour les trois fondus que Resolve montre en
   lecture -- noir, blanc, et le fondu simple. Le rendu ffmpeg fait foi pour
   les 55 autres, qui ne sont visibles qu'apres Preview (c'est ce que dit
   l'infobulle « visible apres Preview » de la galerie, et c'est le drapeau
   `live` du catalogue qui les separe : la table ci-dessous et la liste
   `_XFADE_LIVE` du service sont tenues ensemble par le banc croise
   `D12_les_trois_fondus_de_la_couche_sont_ceux_du_service` de
   test_montage_bundle.py, qui EXTRAIT les deux listes de leur fichier).
   LA JONCTION EST CELLE DU CLIP DE DROITE, comme au rendu : c'est `c` qui
   porte `transition` et `transition_s`, et la jonction est `c.start`. Le
   voile est TRIANGULAIRE sur [t0-s/2, t0+s/2] -- il monte de 0 a 1 au
   raccord puis redescend. Ce n'est pas la courbe de `xfade` (qui croise
   deux images sans passer par le noir, sauf `fadeblack`) : c'est la seule
   courbe qu'un hote unique puisse jouer, et elle dit au monteur OU tombe la
   transition et COMBIEN elle dure. Le mensonge serait de ne rien montrer.
   LE VOISIN GAUCHE EST EXIGE. Sans clip a gauche EN CONTACT (<= 0,1 s,
   `dzmVoisins`), il n'y a pas de jonction : un premier clip, ou un clip
   apres un trou, porte peut-etre un nom de transition -- le rendu ne la
   jouera pas davantage (`xfade` a besoin de deux segments), et un ecran
   qui s'assombrirait au demarrage serait un defaut, pas un aperçu.
   `hasOwnProperty` PLUTOT QUE `DZM_VEIL[k]` : `String(c.transition)` vient
   du projet, et « constructor » ou « toString » auraient rendu une valeur
   HERITEE, donc vraie -- le voile aurait pris une fonction pour une
   couleur. Mesure sous node, ligne `vl_heritage` du banc.
   « dim » N'EST PAS UNE COULEUR, c'est un MECANISME : le fondu simple n'a
   pas de couche a poser, il baisse l'image. La fonction le NOMME pour que
   l'appelant choisisse -- elle ne decide d'aucun style. */
var DZM_VEIL={fadeblack:"#000",fadewhite:"#fff",fade:"dim"};
function dzmVeil(clips,t){
  var cs=Array.isArray(clips)?clips:[],v=Number(t),i,c,k,best=null;
  if(!isFinite(v))return {color:null,alpha:0};
  for(i=0;i<cs.length;i++){c=cs[i];if(!c||c.tr!=="v1"||!c.src)continue;
    k=String(c.transition||"cut").split(/\s+/)[0];
    if(!Object.prototype.hasOwnProperty.call(DZM_VEIL,k))continue;
    /* LES MEMES BORNES QUE `svmTransS` DU BUNDLE (0,1 - 1 s, defaut 0,4) :
       recopiees parce que la couche ne peut pas appeler une fonction du
       bundle, et CROISEES par le banc
       `D12_les_bornes_de_duree_sont_celles_du_bundle`, qui extrait le
       triplet des DEUX sources et les compare. */
    var s=Math.min(1,Math.max(.1,Number(c.transition_s)||.4)),t0=Number(c.start)||0;
    if(Math.abs(v-t0)>s/2)continue;
    var g=dzmVoisins(cs,c).g;if(!g)continue;
    var a=dzmR3(1-Math.abs(v-t0)/(s/2));
    /* ALPHA NUL = PAS DE VOILE, ET PAS « UN VOILE NOIR INVISIBLE ». Au BORD
       EXACT de la fenetre (v-t0 = s/2) la formule rend 0 : sans cette
       ligne, la fonction rendait {color:"#000",alpha:0}, une couleur pour
       un voile qui ne se voit pas -- l'appelant n'a pas a demeler ca. */
    if(!(a>0))continue;
    /* DEUX JONCTIONS DANS LA MEME FENETRE : deux clips tres courts (moins
       d'une seconde) mettent leurs deux triangles l'un sur l'autre. Le
       MAXIMUM l'emporte -- deux voiles ne s'additionnent pas a l'ecran, et
       c'est la transition la plus proche qui compte.
       A EGALITE D'ALPHA, C'EST L'ORDRE DU TABLEAU QUI TRANCHE : `>` et non
       `>=`, donc le PREMIER rencontre garde la main. Meme regle que
       `dzmVoisins` et `dzmTransList` -- et c'est la COULEUR qui le rend
       visible, pas l'alpha (banc `vl_egalite`). */
    if(!best||a>best.alpha)best={color:DZM_VEIL[k],alpha:a}}
  return best||{color:null,alpha:0}}

/* ── D-21 (21/09/2026) : LES CARTONS DE TITRE, CÔTÉ COEUR ──────────────────
   Un titre est un CLIP SANS `src` sur la piste t1. Tout est déjà là pour
   qu'il vive : la persistance range `clips` tel quel (POST /save n'exige
   aucune clé), `GET /project` le resservait déjà, et le backend grave
   `montage_service._titles_ass` à partir de `c.title` pour tout clip dont la
   PISTE porte `kind:"title"` (mesuré, tâches 4 et 5).

   AUCUNE DE CES QUATRE FONCTIONS NE RECOPIE LA TABLE DES HUIT GABARITS. Le
   nom du gabarit est une CHAÎNE qui traverse : `titleNew` l'assainit aux
   caractères d'un identifiant, `titleHtml` en fait une classe CSS, et c'est
   `titles.TEMPLATES` (backend) qui décide seul de la police, de la taille,
   de la couleur, du placement et de l'animation. Un gabarit inconnu retombe
   donc sur le défaut DU BACKEND, jamais sur un second défaut écrit ici —
   même règle que `dzmVideoExt`, qui n'écrit aucune extension, et que
   `dzmTransLabel`, qui ne nomme aucune transition. */

/* LE NOM DE GABARIT, ASSAINI AUX CARACTÈRES D'UN IDENTIFIANT — et rendu
   MINUSCULE AVANT (correctif du 22/09/2026, revue de la tâche 6). Les huit
   clés de `titles.TEMPLATES` sont en minuscules ; le filtre `[^a-z0-9_]`
   MANGEAIT donc les capitales au lieu de les ramener : « CTA » devenait ""
   (aucune classe, aucun gabarit envoyé) et « Plein_Cadre » devenait
   « lein_adre », un nom qui n'existe pas et que le backend remplace en
   silence par son défaut. `toLowerCase()` d'abord, et les deux cas rendent
   le gabarit attendu. Un nom hostile reste assaini : la classe ne peut pas
   sortir de l'attribut.
   TROIS APPELANTS, UNE SEULE RÈGLE : `titleNew`, `titleHtml` et
   `titleUpdate` — trois copies auraient divergé à la première retouche. */
function dzmTtTpl(v){
  return (typeof v==="string"?v:"").toLowerCase().replace(/[^a-z0-9_]/g,"")}

/* L'ÉCHAPPEMENT, PARCE QUE L'APERÇU VIVANT EST ÉCRIT EN `innerHTML`. Le
   texte vient de l'utilisateur : « <b> » doit s'AFFICHER, pas gras. Les
   CINQ caractères sont ceux qui comptent dans un corps d'élément et dans
   une valeur d'attribut ; `&` passe EN PREMIER, sinon les entités posées
   par les suivants seraient ré-échappées.
   L'APOSTROPHE EST DU LOT (revue du 22/09/2026). Elle ne sert à rien tant
   que CETTE fonction n'écrit que des corps d'élément — mais elle est la
   moitié manquante d'un échappeur d'attribut, et le jour où l'aperçu vivant
   porterait un `title='…'` la fuite serait silencieuse. Cinq caractères
   coûtent une ligne ; un échappeur à moitié juste coûte une faille. */
function dzmTtEsc(v){return String(v==null?"":v)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;").replace(/'/g,"&#39;")}

/* La piste t1 si elle manque, EN TÊTE. Rend le MÊME tableau quand elle est
   déjà là : l'appelant compare l'identité pour savoir s'il doit écrire
   (`svmTracksSet` pousse l'historique, on ne le paie pas pour rien).
   Le genre se DÉDUIT quand la piste ne le porte pas (dzmKindOf) : une liste
   restaurée d'une vieille sauvegarde n'a que des `id`, et exiger `kind`
   aurait fait poser une SECONDE piste t1 par-dessus la première. */
function dzmTitleTrack(ts){
  var list=(ts&&ts.length)?ts:[],i,t;
  for(i=0;i<list.length;i++){t=list[i];
    if(t&&t.id&&dzmKindOf(t.id,t.kind)==="title")return ts}
  var out=list.slice();out.unshift(dzmSkin("t1","title"));return out}

/* LE CARTON NEUF, ou `null`. PURE.
   `null` SANS TEXTE, et c'est la même règle que `titles.title_spec` côté
   serveur (« un carton sans texte n'est pas un carton ») : la poser AUSSI
   ici évite d'empiler un instantané d'historique et d'allumer « NON
   ENREGISTRÉ » pour un clip que le rendu ignorerait ensuite en silence.
   QUATRE CLÉS SONT OMISES QUAND L'APPELANT N'EN DIT RIEN (`template`,
   `sub`, `color`, `font`, `size`) : les défauts des huit gabarits vivent
   dans `titles.TEMPLATES`, et une valeur écrite ici — un `size:0`, une
   couleur vide — serait une SECONDE autorité que le backend devrait ensuite
   démêler (`title_spec` borne `size` à 24 au minimum : un zéro parti d'ici
   aurait donné 24 px au lieu des 64 du gabarit).
   DURÉE : celle d'une IMAGE (`DZM_CLIP_DEFAUTS.image`, 4 s) — un carton n'a
   pas plus de longueur naturelle qu'une image cadrée. */
function dzmTitleNew(title,t,clips,tr){
  var o=title&&typeof title==="object"?title:{};
  var txt=(typeof o.text==="string"?o.text:"").trim();
  if(!txt)return null;
  var piste=String(tr||"t1");
  var v=Number(t);if(!isFinite(v)||v<0)v=0;
  var t0=dzmR3(v),len=dzmR3(Number(DZM_CLIP_DEFAUTS.image)||4);
  /* le rang du carton sur la piste, pour que l'identifiant se lise (t1u1,
     t1u2…) ; `uniqueId` tranche ensuite contre TOUS les clips du projet. */
  var n=1;
  (Array.isArray(clips)?clips:[]).forEach(function(c){if(c&&c.kind==="title")n++});
  var ti={text:txt};
  var tpl=dzmTtTpl(o.template);
  if(tpl)ti.template=tpl;
  var sub=(typeof o.sub==="string"?o.sub:"").trim();
  if(sub)ti.sub=sub;
  if(typeof o.color==="string"&&o.color)ti.color=o.color;
  if(typeof o.font==="string"&&o.font)ti.font=o.font;
  var sz=Number(o.size);if(isFinite(sz)&&sz>0)ti.size=Math.round(sz);
  return {tr:piste,kind:"title",id:dzmUniqueId(clips,piste+"u"+n),
    label:txt.slice(0,24),start:t0,end:dzmR3(t0+len),title:ti}}

/* D-9 — LA PISTE D'AJUSTEMENT, POSÉE UNE FOIS. Même contrat que
   `dzmTitleTrack` (le MÊME tableau si une piste `adjust` existe déjà, le
   genre DÉDUIT quand la piste ne le porte pas), mais insérée SOUS les
   titres (`dzmTitresAt`) : la gravure ASS passe après tout au rendu, et
   l'ajustement doit rester au-dessus des incrustations qu'il traite. Sur
   une liste vide : `["j1"]`. PURE. */
function dzmAdjustTrack(ts){
  var list=(ts&&ts.length)?ts:[],i,t;
  for(i=0;i<list.length;i++){t=list[i];
    if(t&&t.id&&dzmKindOf(t.id,t.kind)==="adjust")return ts}
  var out=list.slice();out.splice(dzmTitresAt(list),0,dzmSkin("j1","adjust"));return out}

/* LE CLIP D'AJUSTEMENT NEUF, ou `null`. PURE. SANS clé `src` (le payload le
   laisse passer par son genre, comme un carton), `effects:[]` — c'est le
   rack VFX qui les lui donne. TROIS SECONDES bornées par la fin de la
   timeline (`max(end)` des clips) ; `null` sous une tête négative ou sur un
   projet vide : rien à ajuster, aucun instantané d'historique pour rien. */
function dzmAdjustNew(t,clips,tr){
  var cs=Array.isArray(clips)?clips:[],v=Number(t);
  if(!cs.length||!isFinite(v)||v<0)return null;
  var piste=String(tr||"j1"),fin=0,n=1;
  cs.forEach(function(c){if(c){if(c.end>fin)fin=c.end;if(c.kind==="adjust")n++}});
  var t0=dzmR3(v),t1=dzmR3(Math.min(t0+3,fin));
  if(t1<=t0)return null;
  return {tr:piste,kind:"adjust",id:dzmUniqueId(cs,piste+"u"+n),
    label:"Ajustement",start:t0,end:t1,effects:[]}}

/* LE CARTON SOUS LA TÊTE, ou `null`. FIN EXCLUE et DERNIER DÉPART GAGNANT :
   les deux règles de `svmActiveV1` du bundle, reprises telles quelles — un
   carton qui finit à 4 s a cédé la place à 4 s exactement, et deux cartons
   qui se recouvrent montrent le plus RÉCEMMENT commencé. À égalité de
   départ, le DERNIER du tableau l'emporte (`>=`) : c'est le dernier posé,
   donc celui que l'utilisateur vient d'écrire. */
function dzmTitleAt(clips,t){
  var cs=Array.isArray(clips)?clips:[],v=Number(t),i,c,s,e,best=null;
  if(!isFinite(v))return null;
  for(i=0;i<cs.length;i++){c=cs[i];
    if(!c||c.kind!=="title")continue;
    s=Number(c.start);e=Number(c.end);
    if(!isFinite(s)||!isFinite(e))continue;
    if(v<s||v>=e)continue;
    if(!best||s>=Number(best.start))best=c}
  return best}

/* L'APERÇU VIVANT, EN HTML. Chaîne VIDE quand il n'y a rien à montrer (pas
   un carton, pas de texte, tête hors de la plage) : l'appelant écrit cette
   chaîne telle quelle dans `innerHTML`, et « vide » y vaut « efface ».
   LA CLASSE PORTE LE GABARIT (`dzm-tt-<gabarit>`) et c'est la FEUILLE qui
   place, colore et anime — pas une seconde table de styles ici. Un gabarit
   inconnu ne rend QUE `dzm-tt` : la règle de base l'affiche au lieu de le
   faire disparaître, et le 480p fait foi de toute façon.
   LE 480p FAIT FOI, ET C'EST ÉCRIT : cet aperçu est une APPROXIMATION (pas
   de police embarquée, pas d'animation d'entrée, pas de boîte au pixel) —
   la gravure ASS est la seule vérité. */
function dzmTitleHtml(clip,t){
  var c=clip&&typeof clip==="object"?clip:null;
  if(!c||c.kind!=="title")return "";
  var o=c.title&&typeof c.title==="object"?c.title:{};
  var txt=(typeof o.text==="string"?o.text:"").trim();
  if(!txt)return "";
  var v=Number(t);
  if(isFinite(v)){var s=Number(c.start),e=Number(c.end);
    if(isFinite(s)&&isFinite(e)&&(v<s||v>=e))return ""}
  var tpl=dzmTtTpl(o.template);
  var sub=(typeof o.sub==="string"?o.sub:"").trim();
  return '<div class="dzm-tt'+(tpl?" dzm-tt-"+tpl:"")+'">'+
    "<b>"+dzmTtEsc(txt)+"</b>"+(sub?"<i>"+dzmTtEsc(sub)+"</i>":"")+"</div>"}

/* ── D-21 (22/09/2026) : RÉGLER UN CARTON, ET L'INSPECTEUR QUI LE RÈGLE ────
   `dzmTitleUpdate(clips, id, patch)` est PURE et rend la liste entière. Elle
   ne rend un TABLEAU NEUF que lorsqu'il y a eu un changement RÉEL ; sinon
   elle rend LE MÊME TABLEAU, et l'identité EST le signal — exactement comme
   `titleTrack` et `dzmMove`. C'est ce qui permet à l'hôte de ne payer un
   `pushHistory` que pour un vrai changement : un patch refusé (texte vide,
   gabarit qui ne survit pas à l'assainissement, valeur identique) n'allume
   ni « NON ENREGISTRÉ » ni une entrée d'historique qui ne défait rien.
   CE QUE LA COUCHE NE SAIT PAS, ELLE NE LE JUGE PAS — et c'est un ÉCART
   MESURÉ contre la lettre du plan, qui demandait « gabarit inconnu →
   inchangé » et une couleur « hors BRAND → inchangée » :
     . les huit noms de gabarits vivent dans `titles.TEMPLATES` et la ligne
       `D21_la_couche_ne_recopie_aucun_gabarit` du banc bundle INTERDIT d'en
       écrire un seul ici. Le seul « inconnu » que la couche puisse trancher
       est le nom qui ne survit PAS à l'assainissement (`dzmTtTpl` rend "")
       — celui-là est refusé ; les autres traversent, et `title_spec`
       retombe sur son défaut. L'inspecteur, lui, ne propose QUE les huit du
       serveur : l'utilisateur ne peut pas en frapper un douzième ;
     . `BRAND` et `FONT_FILES` sont dans le même cas. La couche accepte
       toute chaîne non vide et le BACKEND assainit (`color not in BRAND`
       → couleur du gabarit). Écrire ici une seconde table de cinq couleurs
       et de seize polices aurait été une seconde autorité à démêler.
   LA CHAÎNE VIDE EFFACE LA CLÉ (`sub`, `color`, `font`) : c'est le choix
   « (du gabarit) » de l'inspecteur, et il doit RETIRER le réglage, pas
   écrire un `color:""` que `title_spec` devrait ensuite ignorer.
   UN TEXTE VIDE EST REFUSÉ, exactement comme dans `titleNew` et dans
   `title_spec` (« un carton sans texte n'est pas un carton ») : vider le
   champ ne fabrique pas un clip que le rendu jetterait en silence — l'input
   repart de l'ancien texte au remontage (sa clé porte la valeur).
   LE LIBELLÉ DE LA BANDE SUIT LE TEXTE : la timeline dessine `c.label`, et
   sans cette ligne le carton aurait gardé le nom de son premier jet.
   LES BORNES 120/160 SONT CELLES DU BACKEND (`MAX_TEXT`, `MAX_SUB`), et
   elles sont ici pour que le champ ne PARAISSE pas accepter ce qui sera
   coupé — le serveur reste l'autorité, la couche n'est qu'une politesse. */
var DZM_TT_MAX_TEXT=120,DZM_TT_MAX_SUB=160;
function dzmTitleUpdate(clips,id,patch){
  var cs=Array.isArray(clips)?clips:[];
  var p=patch&&typeof patch==="object"?patch:null;
  var cible=null,i;
  if(p){for(i=0;i<cs.length;i++){
    if(cs[i]&&cs[i].id===id&&cs[i].kind==="title"){cible=cs[i];break}}}
  if(!cible)return cs;
  var t0=cible.title&&typeof cible.title==="object"?cible.title:{};
  var t=Object.assign({},t0),bouge=!1;
  var tpl=dzmTtTpl(p.template);
  if(tpl&&tpl!==t.template){t.template=tpl;bouge=!0}
  if(typeof p.text==="string"){
    var tx=p.text.replace(/\r\n/g,"\n").slice(0,DZM_TT_MAX_TEXT);
    if(tx.trim()&&tx!==t.text){t.text=tx;bouge=!0}}
  if(typeof p.sub==="string"){
    var sb=p.sub.replace(/\r\n/g,"\n").slice(0,DZM_TT_MAX_SUB);
    if(!sb.trim()){if("sub" in t){delete t.sub;bouge=!0}}
    else if(sb!==t.sub){t.sub=sb;bouge=!0}}
  ["color","font"].forEach(function(k){
    if(typeof p[k]!=="string")return;
    var v=p[k].trim();
    if(!v){if(k in t){delete t[k];bouge=!0}}
    else if(v!==t[k]){t[k]=v;bouge=!0}});
  /* LA TAILLE EST BORNÉE 24..200 ICI AUSSI (22/09/2026) : la réglette ne
     peut pas en sortir, mais `titleUpdate` est PUBLIQUE — un appel venu
     d'ailleurs aurait écrit un `size:5000` que la sauvegarde aurait gardé
     et que seul le rendu aurait ramené à 200, sans le dire. Les mêmes
     bornes que `title_spec` (`max(24, min(200, …))`) et que l'`<input
     type=range>` : trois fois la même règle, et jamais trois règles. */
  if(p.size!=null){var nz=Math.round(Number(p.size));
    if(isFinite(nz)&&nz>0){nz=Math.max(24,Math.min(200,nz));
      if(nz!==t.size){t.size=nz;bouge=!0}}}
  if(!bouge)return cs;
  var lab=typeof t.text==="string"?t.text.slice(0,24):cible.label;
  return cs.map(function(c){
    return c===cible?Object.assign({},c,{title:t,label:lab}):c})}

/* LA LARGEUR DES VIGNETTES. 180 px : la colonne d'inspection fait 300 px de
   large et la galerie est à DEUX colonnes — 180 dans une case de ~140
   laisse la marge d'un écran à 2× sans repasser par le serveur. La route
   borne `w` à 96..640 et PAIR ; 180 traverse tel quel. Une largeur par
   vignette aurait multiplié les entrées du cache serveur par autant. */
var DZM_TT_CARD_W=180;
/* L'INSPECTEUR DU CARTON. AUCUN ÉTAT LOCAL, AUCUN HOOK — et c'est un CHOIX,
   pas une contrainte : TT6 le monte par un `r.jsx` sur `TitleInspector`,
   donc comme un vrai composant, où un `useState` serait parfaitement légal.
   (Correctif du 22/09/2026 : ce commentaire disait « appelé comme une
   fonction, donc sans hook » — c'était faux.) La vraie raison est que TOUT
   l'état vit dans le clip : un état local le doublerait, et après un Ctrl+Z
   l'hôte repeindrait l'ancien texte pendant que le champ garderait le neuf.
   D'où les champs NON CONTRÔLÉS et la clé qui porte la valeur (React ignore
   `defaultValue` à la mise à jour).
   CE QUE CELA COÛTE, ET C'EST ASSUMÉ : valider par Entrée remonte le texte,
   donc change la clé, donc REMONTE l'input — le focus est perdu et le
   curseur revient en fin de champ. C'est le même prix que l'index des
   marqueurs paie déjà (I-3 de D-5), et la contrepartie est qu'un Ctrl+Z ne
   laisse JAMAIS le champ mentir sur le projet.
   LES HUIT VIGNETTES SONT DES PNG DU SERVEUR, gravés par le MÊME ASS que le
   rendu (`GET /title-preview`) : une maquette CSS aurait menti sur la
   police, la boîte et le placement, c'est-à-dire sur tout ce qui distingue
   les huit gabarits. `loading="lazy"` — le panneau peut être hors champ.
   L'URL NE PORTE QUE `template`, `text`, `sub` ET `w`. La couleur, la
   police et le CORPS en sont VOLONTAIREMENT absents : ils changent
   l'image sans changer le GABARIT, et les y mettre aurait fait regraver
   HUIT PNG à chaque cran de la réglette de taille. Le cadre 9:16 du
   serveur fait foi pour la vignette ; l'aperçu vivant, lui, porte les
   réglages.
   ET SEULE LA CARTE CHOISIE PORTE LE TEXTE RÉEL (22/09/2026) : les sept
   autres montrent le mot « Titre », sans sous-texte. Sans cela, CHAQUE
   édition de texte gravait HUIT PNG neufs — huit ffmpeg d'environ 0,3 s,
   huit entrées de cache de plus, à chaque blur. Avec, une édition n'en
   grave qu'UN, et les sept autres sont les mêmes vignettes pour tous les
   projets de la machine : le cache les sert une fois pour toutes. Ce que
   la galerie doit montrer, c'est le GABARIT ; le texte de l'utilisateur,
   c'est la carte choisie et l'aperçu vivant qui le disent.
   UN PUSH PAR CHANGEMENT RÉEL : le texte et le sous-texte partent au BLUR
   et sur Entrée (un `onChange` par frappe poussait un instantané
   d'historique par caractère, défaut déjà corrigé pour les marqueurs) ; le
   gabarit part au CLIC ; couleur et police au `change` d'un `<select>`, qui
   ne se frappe pas en rafale ; la TAILLE part au relâchement
   (`onPointerUp`/`onKeyUp`/`onBlur`) et JAMAIS pendant le glissé — React
   câble `onChange` d'un `<input type=range>` sur l'événement `input`, qui
   tire à chaque pixel : cinquante instantanés pour un geste.
   CE QUE CELA COÛTE, ET C'EST ASSUMÉ : le nombre affiché à côté de la
   réglette ne bouge qu'au relâchement (pas d'état local pour le suivre).
   Le curseur, lui, glisse normalement — c'est le navigateur qui le tient. */
function DzmTitleInspector(o){
  var c=o&&o.clip&&typeof o.clip==="object"?o.clip:null;
  if(!c||c.kind!=="title")return null;
  var gs=Array.isArray(o&&o.gabarits)?o.gabarits.filter(Boolean):[];
  var fonts=Array.isArray(o&&o.fonts)?o.fonts.filter(Boolean):[];
  var cols=Array.isArray(o&&o.colors)?o.colors.filter(Boolean):[];
  var on=typeof (o&&o.onChange)==="function"?o.onChange:function(){};
  var ti=c.title&&typeof c.title==="object"?c.title:{};
  var txt=typeof ti.text==="string"?ti.text:"";
  var sub=typeof ti.sub==="string"?ti.sub:"";
  var cur=dzmTtTpl(ti.template);
  /* LE JETON DE REMONTAGE. L'hôte l'incrémente quand il REFUSE un patch
     (vider le champ Texte) : le clip ne change pas, donc la clé porteuse de
     valeur ne changerait pas, donc React garderait à l'écran l'input vidé
     alors que le carton a gardé son texte — un champ qui ment. Le jeton
     entre dans les deux clés et force le remontage : le champ se recolle
     sur la valeur du projet. Il vaut 0 quand l'hôte n'en dit rien. */
  var nz=Number(o&&o.nonce)||0;
  /* le gabarit COURANT du catalogue : c'est lui qui nomme les défauts
     affichés dans les deux `<select>` et sous la réglette. Absent (le
     catalogue n'est pas arrivé, ou le carton porte un nom inconnu), les
     champs disent « (du gabarit) » sans prétendre savoir lequel. */
  var gab=null,gi;
  for(gi=0;gi<gs.length;gi++){if(String(gs[gi].id)===cur){gab=gs[gi];break}}
  var taille=Number(ti.size)||Number(gab&&gab.size)||64;
  function maj(p){on(c.id,p)}
  /* REMONTE SEULEMENT SI ÇA A CHANGÉ — la moitié qui empêche un instantané
     d'historique sur un blur qui n'a rien touché. */
  function pousse(cle,avant,e){
    var v=e&&e.target?String(e.target.value):"";
    if(v===String(avant==null?"":avant))return;
    var p={};p[cle]=v;maj(p)}
  function pousseNb(avant,e){
    var n=Math.round(Number(e&&e.target?e.target.value:NaN));
    if(!isFinite(n)||n===Number(avant))return;maj({size:n})}
  var vignette=txt.trim()||"Titre";
  return r.jsxs("div",{className:"dzm-ttinsp",children:[
    r.jsx("div",{className:"svm-poptitle",children:"Titre — gabarit"}),
    /* SANS CATALOGUE, UNE PHRASE PLUTÔT QU'UNE GRILLE VIDE. Le `fetch` de
       `/titles` échoue en silence (même parti pris que le catalogue des
       transitions) : une grille de zéro case laisserait l'utilisateur
       devant un trou sans nom. La phrase dit ce qui manque ET ce qui
       marche encore — le texte, le sous-texte et le corps restent
       réglables, et le rendu garde les défauts du gabarit. */
    gs.length?r.jsx("div",{className:"dzm-ttcards",role:"group",
      "aria-label":"Gabarits de titre",
      children:gs.map(function(g){
        var gid=String(g.id||""),lab=String(g.label||gid),ici=cur===gid;
        return r.jsxs("button",{className:"dzm-ttcard",
          "data-sel":ici?"":void 0,"aria-pressed":ici,
          title:lab+" ("+gid+")",
          onClick:function(){if(gid&&gid!==cur)maj({template:gid})},children:[
          r.jsx("img",{className:"dzm-ttimg",loading:"lazy",alt:"",
            src:"/api/montage/title-preview?template="+encodeURIComponent(gid)+
              "&text="+encodeURIComponent(ici?vignette:"Titre")+
              (ici&&sub?"&sub="+encodeURIComponent(sub):"")+
              "&w="+DZM_TT_CARD_W}),
          r.jsx("span",{className:"dzm-ttname",children:lab})]},gid)})}):
      r.jsx("div",{className:"svm-note",
        children:"Gabarits indisponibles — le texte reste réglable."}),
    r.jsxs("label",{className:"dzm-ttrow",children:[
      r.jsx("span",{className:"dzm-ttlab",children:"Texte"}),
      r.jsx("input",{className:"dzm-ttxt",defaultValue:txt,
        maxLength:DZM_TT_MAX_TEXT,placeholder:"Titre",
        "aria-label":"Texte du carton",
        onBlur:function(e){pousse("text",txt,e)},
        onKeyDown:function(e){if(e.key==="Enter")pousse("text",txt,e)}},
        c.id+"|"+nz+"|"+txt)]}),
    r.jsxs("label",{className:"dzm-ttrow",children:[
      r.jsx("span",{className:"dzm-ttlab",children:"Sous-texte"}),
      r.jsx("input",{className:"dzm-ttxt",defaultValue:sub,
        maxLength:DZM_TT_MAX_SUB,placeholder:"(aucun)",
        "aria-label":"Sous-texte du carton",
        onBlur:function(e){pousse("sub",sub,e)},
        onKeyDown:function(e){if(e.key==="Enter")pousse("sub",sub,e)}},
        c.id+"|s|"+nz+"|"+sub)]}),
    r.jsxs("label",{className:"dzm-ttrow",children:[
      r.jsx("span",{className:"dzm-ttlab",children:"Couleur"}),
      r.jsx("select",{className:"dzm-ttsel",
        value:typeof ti.color==="string"?ti.color:"",
        "aria-label":"Couleur du carton",
        onChange:function(e){pousse("color",ti.color,e)},
        children:[r.jsx("option",{value:"",
          children:"(du gabarit"+(gab&&gab.color?" — "+gab.color:"")+")"},"")]
          .concat(cols.map(function(k){
            return r.jsx("option",{value:String(k),children:String(k)},
              String(k))}))})]}),
    r.jsxs("label",{className:"dzm-ttrow",children:[
      r.jsx("span",{className:"dzm-ttlab",children:"Police"}),
      r.jsx("select",{className:"dzm-ttsel",
        value:typeof ti.font==="string"?ti.font:"",
        "aria-label":"Police du carton",
        onChange:function(e){pousse("font",ti.font,e)},
        children:[r.jsx("option",{value:"",
          children:"(du gabarit"+(gab&&gab.font?" — "+gab.font:"")+")"},"")]
          .concat(fonts.map(function(f){
            return r.jsx("option",{value:String(f),children:String(f)},
              String(f))}))})]}),
    r.jsxs("label",{className:"dzm-ttrow",children:[
      r.jsx("span",{className:"dzm-ttlab",children:"Taille"}),
      r.jsx("input",{className:"dzm-ttsize",type:"range",min:24,max:200,step:1,
        defaultValue:String(taille),
        "aria-label":"Corps du titre à 1080 p, en pixels",
        onPointerUp:function(e){pousseNb(taille,e)},
        onKeyUp:function(e){pousseNb(taille,e)},
        onBlur:function(e){pousseNb(taille,e)}},c.id+"|z|"+taille),
      r.jsx("span",{className:"dzm-ttnb",children:taille+" px"})]}),
    r.jsx("div",{className:"svm-note",
      children:"Le placement et l'animation viennent du gabarit. "+
        "L'aperçu du lecteur est approché : Preview 480p fait foi."})]})}

/* ── E-1 (22/09/2026) : UN MONTAGE NEUF. Le corps de POST /projects pour un
   projet VIDE : nom nettoyé (« montage neuf » à défaut), `vide:true`, et les
   pistes par défaut du CLIENT écrites explicitement (une seule vérité pour
   l'écran et le rendu) — des COPIES, la constante ne sort jamais.
   `dzmInstantaneNom` nomme la copie de sûreté prise AVANT d'ouvrir un autre
   projet par-dessus un montage non nommé ; « montage » est le nom par défaut
   de l'écran, pas un nom. */
function dzmProjetNeuf(nom){
  var n=String(nom||"").trim()||"montage neuf";
  return {name:n,vide:!0,tracks:DZM_DEFAULT_TRACKS.map(function(t){return Object.assign({},t)})}}
function dzmInstantaneNom(nom,now){
  var n=String(nom||"").trim();
  if(n&&n!=="montage")return n;
  var d=now instanceof Date&&!isNaN(now)?now:new Date(),p=function(v){return (v<10?"0":"")+v};
  return "(non nommé) "+p(d.getDate())+"/"+p(d.getMonth()+1)+" "+p(d.getHours())+":"+p(d.getMinutes())}

/* ── export contrat ───────────────────────────────────────────────────────── */
/* ── E-4 (22/09/2026) : PUBLIER, À LA DEMANDE. Le rendu ne crée plus rien
   dans le Scheduler ; le bandeau de fin propose l'envoi. Défauts partagés
   avec la Bibliothèque (+2 h, arrondi au quart d'heure suivant, canal « x »),
   canaux mémorisés (dz_montage_channels), liste blanche = celle du backend
   (montage_service). `publishIso` convertit l'heure LOCALE du champ
   datetime-local en UTC « Z » : le backend la ramène en naïf UTC. */
var DZM_CHANNELS=[["x","X"],["telegram","Telegram"],["youtube","YouTube"],["instagram","Instagram"]];
function dzmChannelsNorm(list){
  var ok=DZM_CHANNELS.map(function(c){return c[0]}),out=[];
  (Array.isArray(list)?list:[]).forEach(function(c){if(ok.indexOf(c)>=0&&out.indexOf(c)<0)out.push(c)});
  return out.length?out:["x"]}
function dzmPublishLocal(now){
  var d=new Date(now.getTime()+2*3600*1000),q=15*60*1000;d=new Date(Math.ceil(d.getTime()/q)*q);
  var p=function(v){return (v<10?"0":"")+v};
  return d.getFullYear()+"-"+p(d.getMonth()+1)+"-"+p(d.getDate())+"T"+p(d.getHours())+":"+p(d.getMinutes())}
function dzmPublishIso(local){var d=new Date(String(local||""));return isNaN(d)?"":d.toISOString()}
function dzmPublishDefaults(nom,now,memo){
  return {channels:dzmChannelsNorm(memo),run_at:dzmPublishLocal(now),caption:String(nom||"").trim()||"Montage"}}
/* LE BANDEAU DE FIN DE RENDU. props : {fin:{job_id,name,project_id}, memo,
   onSend(form)→Promise, onLib(), onClose()}. Un double clic ne crée pas deux
   brouillons : le bouton se désarme pendant « … » et après succès. */
var DZM_FIN_OK="Brouillon ajouté au Scheduler";
function DzmFinBandeau(o){
  var fin=o&&o.fin;if(!fin)return null;
  var d0=dzmPublishDefaults(fin.name,new Date(),o.memo);
  var s1=x.useState(d0.channels),ch=s1[0],setCh=s1[1];
  var s2=x.useState(d0.run_at),when=s2[0],setWhen=s2[1];
  var s3=x.useState(d0.caption),cap=s3[0],setCap=s3[1];
  var s4=x.useState(""),st=s4[0],setSt=s4[1];
  var tog=function(id){setCh(function(c){return c.indexOf(id)>=0?c.filter(function(k){return k!==id}):c.concat([id])})};
  /* E-11 (23/09/2026) : le voile du bundle (EB5a) ferme au clic ;
     la racine arrête le clic comme le popover (EB5b) et kbPanel */
  return r.jsxs("div",{className:"svm-pop dzm-fin",onClick:function(e){e.stopPropagation()},children:[
    r.jsx("div",{className:"svm-poptitle",children:"Rendu terminé"}),
    r.jsx("div",{className:"dzm-fin-row",children:DZM_CHANNELS.map(function(c){return r.jsxs("label",{className:"dzm-fin-ch",children:[
      r.jsx("input",{type:"checkbox",checked:ch.indexOf(c[0])>=0,onChange:function(){tog(c[0])}})," "+c[1]]},c[0])})}),
    r.jsxs("div",{className:"dzm-fin-row",children:[r.jsx("input",{type:"datetime-local",value:when,onChange:function(e){setWhen(e.target.value)}}),
      r.jsx("input",{type:"text",value:cap,placeholder:"légende",onChange:function(e){setCap(e.target.value)}})]}),
    st?r.jsx("div",{className:"dzm-fin-st",children:st}):null,
    r.jsxs("div",{className:"dzm-fin-row",children:[
      r.jsx("button",{className:"svm-goldbtn",disabled:st==="…"||st===DZM_FIN_OK,
        title:"Envoyer ce rendu au Scheduler (brouillon, rien n'est publié sans validation)",onClick:function(){setSt("…");
        Promise.resolve(o.onSend({job_id:fin.job_id,project_id:fin.project_id||void 0,channels:dzmChannelsNorm(ch),run_at:dzmPublishIso(when)||void 0,caption:cap}))
          .then(function(){setSt(DZM_FIN_OK)}).catch(function(e){setSt("Envoi impossible : "+String(e))})},children:"Envoyer vers le Scheduler"}),
      r.jsx("button",{className:"svm-secbtn",title:"Ouvrir la Bibliothèque sur ce rendu",onClick:function(){o.onLib&&o.onLib()},children:"Voir dans la Bibliothèque"}),
      r.jsx("button",{className:"svm-secbtn",title:"Fermer le bandeau (Échap)",onClick:function(){o.onClose&&o.onClose()},children:"Fermer"})]})]})}
/* ── E-7 (lot E-C, tâche 3, 23/09/2026) : LA VUE « LIVRAISON » ─────────────
   dzmJobsTri(jobs, nom) — pure : les jobs `provider==="montage"` dont le
   titre COMMENCE par `nom` (nom vide : tous), séparés en {finals, previews}
   par le suffixe « (aperçu 480p) » que montage_service pose sur le titre
   d'un aperçu (`name[:60]` + suffixe, montage_service.py:3222) — aucun
   project_id en base : l'historique d'un projet est PAR TITRE (écart daté).
   Ordre reçu conservé (GET /api/jobs rend le plus récent d'abord) ; entrées
   non-objets ignorées ; `jobs` non-tableau → deux listes vides.
   DzmDeliver(o) — {nom, onPreview, onRender, onPublish, publishOn, lastFin,
   jobs, onOpenLib} → div.svm-deliver. AUCUN hook : le fetch est dans l'hôte
   (EC6, effet [view]). Les trois boutons reprennent les handlers de la barre
   de titre (setPop preview/render, Publier = R_EA5D, grisé sans rendu final
   ET gardé dans le clic ; libellés « Rendre… » / « Publier ce rendu » : les
   jetons « Rendre → » et « Publier » nu sont ceux de la BARRE, pinnés ×1) ; « Voir dans la Bibliothèque » = le chemin EXACT
   du bandeau de fin (deepotus:navigate → library, passé par l'hôte). La
   durée passe par dzmDurTxt (svmRuler du bundle, E-9), jamais recopiée. */
var DZM_DEL_APERCU="(aperçu 480p)";
function dzmJobsTri(jobs,nom){
  var n=String(nom==null?"":nom),fin=[],prev=[];
  (Array.isArray(jobs)?jobs:[]).forEach(function(j){
    if(!j||typeof j!=="object"||j.provider!=="montage")return;
    var t=String(j.title==null?"":j.title);
    if(n&&t.indexOf(n)!==0)return;
    (t.indexOf(DZM_DEL_APERCU)>=0?prev:fin).push(j)});
  return {finals:fin,previews:prev}}
function dzmDelDate(v){if(!v)return "";var d=new Date(v);return isNaN(d)?"":d.toLocaleString()}
function DzmDeliver(o){
  o=o||{};var tri=dzmJobsTri(o.jobs,o.nom),lf=o.lastFin,n=tri.finals.length+tri.previews.length;
  var row=function(j,kind){return r.jsxs("div",{className:"svm-delrow","data-kind":kind,children:[
    r.jsx("span",{className:"svm-deltitle",children:String(j.title||j.job_id||"")}),
    r.jsx("span",{className:"svm-deldate",children:dzmDelDate(j.created_at)}),
    r.jsx("span",{className:"svm-deldur",children:j.duration_s>0?dzmDurTxt(Number(j.duration_s)):""}),
    r.jsx("span",{className:"svm-delbadge",children:kind==="preview"?"aperçu":"final"}),
    /* L4 (D-36) : le statut brut du job (queued / generating_video / done / failed) en badge, texte par dzmDelStatut */
    (function(){var st=dzmDelStatut(j);return r.jsx("span",{className:"svm-delbadge svm-delst","data-st":st.st,children:st.txt})})()]},String(j.job_id||"")+kind)};
  return r.jsxs("div",{className:"svm-deliver",children:[
    r.jsx("h2",{className:"svm-delh",children:"Livraison"}),
    r.jsxs("div",{className:"svm-delbtns",children:[
      r.jsx("button",{className:"svm-secbtn",title:"Aperçu 480p — rapide, pour vérifier le montage",onClick:function(){o.onPreview&&o.onPreview()},children:"Preview 480p"}),
      r.jsx("button",{className:"svm-goldbtn",title:"Rendu final (master 1080), aucun crédit consommé",onClick:function(){o.onRender&&o.onRender()},children:"Rendre…"}),
      r.jsx("button",{className:"svm-secbtn",disabled:!o.publishOn,title:o.publishOn?"Envoyer le dernier rendu final au Scheduler":"Aucun rendu final pour ce projet",onClick:function(){if(o.publishOn&&o.onPublish)o.onPublish()},children:"Publier ce rendu"})]}),
    r.jsx("div",{className:"svm-dellast",children:lf?"Dernier rendu final : "+String(lf.name||"")+" · "+dzmDelDate(lf.at):"Dernier rendu final : aucun"}),
    r.jsx("div",{className:"svm-dellist",children:n?tri.finals.map(function(j){return row(j,"final")}).concat(tri.previews.map(function(j){return row(j,"preview")})):r.jsx("div",{className:"svm-delempty",children:"Aucun rendu pour ce projet."})}),
    r.jsx("button",{className:"svm-secbtn",title:"Ouvrir la Bibliothèque sur les rendus vidéo",onClick:function(){o.onOpenLib&&o.onOpenLib()},children:"Voir dans la Bibliothèque"})]})}
/* ── E-13 / E-14 (lot E-C, tâche 5, 23/09/2026) : LA TÊTE DANS L'INSPECTEUR,
   LE TROU SÉLECTIONNÉ ──────────────────────────────────────────────────────
   dzmTeteTxt(ph, sel, fmt) — pure : « tête à <fmt(ph)> », puis « · +<fmt(ph−start)>
   dans le plan » quand un clip est sélectionné et start ≤ ph < end (intervalle
   FERMÉ-OUVERT : à ph == end la tête est « hors du plan »), sinon « · hors du
   plan » ; sans sel, rien de plus. Le formateur est PASSÉ par l'hôte (svmTcFF,
   HH:MM:SS:FF à 30 i/s, celui de .svm-tcmain — décision 7 : pas de « ·ii »,
   rien de recopié) ; absent, le nombre est arrondi au centième. ph non fini → "".
   dzmTrou(clips, tr, t) — pure : {a,b} = fin du dernier clip de `tr` finissant
   ≤ t (0 si aucun) et début du premier clip commençant > t ; null si t est DANS
   un clip, sans clip suivant (la queue de piste n'est pas un trou — décision 8),
   ou si le trou fait moins de 0,05 s (seuil FLOTTANT : 6,05−6 < 0,05 en
   IEEE, un tel trou est refusé — assumé, daté 23/09). Entrées non-objets
   ignorées. Les MARQUEURS (D-5) ne suivent pas le ripple du trou (écart
   daté, comme le jumeau A1). Dans l'hôte, le trou s'efface dès que `clips`
   change (effet [clips], revue T5) : jamais de bornes périmées.
   dzmTrouRipple(clips, tr, a, b) — pure : nouveau tableau ; les clips de `tr`
   dont start ≥ b (−1e-6) reculent de b−a (start/end seuls, les autres champs
   et l'ordre intacts, les clips immobiles sont LES MÊMES objets) ; les autres
   pistes ne bougent pas (écart daté : le jumeau A1 ne suit pas, comme D-4).
   Bornes invalides (b ≤ a, NaN) → copie identique ; clips non-tableau → []. */
function dzmTeteTxt(ph,sel,fmt){
  var p=Number(ph);if(!isFinite(p))return "";
  var f=typeof fmt==="function"?fmt:function(v){return String(Math.round(v*100)/100)};
  var s="tête à "+f(p);
  if(sel&&typeof sel==="object"&&isFinite(Number(sel.start))&&isFinite(Number(sel.end)))
    s+=(Number(sel.start)<=p&&p<Number(sel.end))?" · +"+f(p-Number(sel.start))+" dans le plan":" · hors du plan";
  return s}
function dzmTrou(clips,tr,t){
  var p=Number(t);if(!Array.isArray(clips)||!isFinite(p))return null;
  var a=0,b=null,i,c,s0,e0;
  for(i=0;i<clips.length;i++){c=clips[i];if(!c||typeof c!=="object"||c.tr!==tr)continue;
    s0=Number(c.start);e0=Number(c.end);if(!isFinite(s0)||!isFinite(e0))continue;
    if(s0<=p&&p<e0)return null;
    if(e0<=p&&e0>a)a=e0;
    if(s0>p&&(b===null||s0<b))b=s0}
  if(b===null||b-a<.05)return null;
  return {a:a,b:b}}
function dzmTrouRipple(clips,tr,a,b){
  if(!Array.isArray(clips))return [];
  var d=Number(b)-Number(a);
  if(!isFinite(d)||d<=0)return clips.slice();
  return clips.map(function(c){
    if(!c||typeof c!=="object"||c.tr!==tr||!(Number(c.start)>=Number(b)-1e-6))return c;
    return Object.assign({},c,{start:c.start-d,end:c.end-d})})}
/* ── L4 (23/09/2026) : LES RÉGLAGES DE LIVRAISON (D-35, D-24, D-36, D-38) ──
   Décisions 5-8 du plan L4. Le client n'a AUCUNE liste de presets en dur :
   builtins ET presets maison viennent de GET /api/montage/deliver-presets
   ({builtins:[{id,label}], fps:[…], presets:[{id,label,base,fps,crf}]}) ;
   sans réglage, aucun `preset` n'est posté et le backend retombe sur master.
   Les cadences (DZM_DEL_FPS) et les cibles de loudness (DZM_DEL_LOUD) sont
   les listes du backend (_DELIVER_FPS, _LOUD_TARGETS — banc croisé T5).
   dzmLoudPastille(i, cible) — pure : "gris" (cible absente ou mesure non
   finie), "vert" |Δ| ≤ 1 dB, "jaune" ≤ 3, "rouge" au-delà.
   dzmDeliverOpts(api) — pure : [{id,label,groupe:"Standard"|"Maison"}],
   builtins puis maison, ids uniques (le premier gagne), entrées non-objets
   ou sans id ignorées, api null → [].
   dzmDeliverPayload(base, opts) — pure : copie de `base` + `preset` (chaîne
   non vide), `fps` (∈ DZM_DEL_FPS, sinon OMIS), `loudness` (NOMBRE ∈
   DZM_DEL_LOUD — "-14" chaîne omise, le backend refuse les chaînes),
   `range:[in,out]` seulement si `opts.rangeOnly` ET `dzmRangeFrom(opts.range)`
   valide, `queue:true` si `opts.queue`. Aucun champ absent n'est posé.
   dzmDelStatut(j) — pure : {st, txt} du badge de statut d'un job de la vue
   Livraison ("queued" → « en file », "generating_video" → « en cours n % »,
   "done" → « terminé », "failed" → « échec », autre → txt "").
   DzmDeliverRow(o) — {opts, api, onChange(patch), lufs, hasRange, onSavePreset}
   → div.svm-delopts (grille libellé/contrôle) : select preset (optgroup
   Standard / Maison), select cadence (« projet (30) » = rien de posté), select
   loudness (« aucune » / −14 / −16 / −23) + pastille span.svm-loudpill
   [data-etat] titrée (« mesure −16,2 LUFS · cible −14 » / « mesurez
   d'abord »), case « Rendre la plage I/O seulement » SEULEMENT si hasRange,
   bouton « Enregistrer ce réglage… » → onSavePreset(). AUCUN hook : l'état
   et le fetch vivent dans l'hôte (L4a). Le nom du preset maison est demandé
   par l'hôte (prompt natif — écart daté : le Montage n'a pas de dialogue
   maison, VL.dialogue est celui du Vectorlab). */
var DZM_DEL_FPS=[24,25,30,60];
var DZM_DEL_LOUD=[[-14,"−14 YouTube · TikTok"],[-16,"−16 podcast"],[-23,"−23 EBU"]];
function dzmLoudTxt(v){return String(Math.round(Number(v)*10)/10).replace("-","−").replace(".",",")}
function dzmLoudPastille(i,cible){
  var c=Number(cible),m=Number(i);
  if(cible==null||!isFinite(c)||i==null||!isFinite(m))return "gris";
  var d=Math.abs(m-c);
  return d<=1?"vert":d<=3?"jaune":"rouge"}
function dzmDeliverOpts(api){
  var out=[],vus={};
  if(!api||typeof api!=="object")return out;
  var pousse=function(lst,grp){(Array.isArray(lst)?lst:[]).forEach(function(p){
    if(!p||typeof p!=="object")return;
    var id=String(p.id==null?"":p.id);if(!id||vus[id])return;vus[id]=1;
    out.push({id:id,label:String(p.label==null||p.label===""?id:p.label),groupe:grp})})};
  pousse(api.builtins,"Standard");pousse(api.presets,"Maison");
  return out}
function dzmDeliverPayload(base,opts){
  var out=Object.assign({},base||{}),o=opts&&typeof opts==="object"?opts:{};
  if(typeof o.preset==="string"&&o.preset)out.preset=o.preset;
  var f=Number(o.fps);if(DZM_DEL_FPS.indexOf(f)>=0)out.fps=f;
  if(typeof o.loudness==="number"&&DZM_DEL_LOUD.some(function(l){return l[0]===o.loudness}))out.loudness=o.loudness;
  var rg=o.rangeOnly?dzmRangeFrom(o.range):null;if(rg)out.range=[rg.in,rg.out];
  if(o.queue)out.queue=!0;
  return out}
function dzmDelStatut(j){
  var st=String(j&&j.status||""),p=Math.max(0,Math.min(100,Math.round(Number(j&&j.progress)||0)));
  var txt=st==="queued"?"en file":st==="generating_video"?"en cours "+p+" %":st==="done"?"terminé":st==="failed"?"échec":"";
  return {st:st,txt:txt}}
function DzmDeliverRow(o){
  o=o||{};var opts=o.opts&&typeof o.opts==="object"?o.opts:{},lst=dzmDeliverOpts(o.api);
  var ch=function(p){if(o.onChange)o.onChange(p)};
  var grp=function(g){var it=lst.filter(function(p){return p.groupe===g});
    return it.length?r.jsx("optgroup",{label:g,children:it.map(function(p){return r.jsx("option",{value:p.id,children:p.label},p.id)})},g):null};
  var pv=typeof opts.preset==="string"&&opts.preset?opts.preset:(lst[0]?lst[0].id:"");
  /* revue T4 : un preset persiste qui n'est plus servi (maison supprime, api en panne) est DIT, jamais remplace en silence */
  var absent=pv&&!lst.some(function(p){return p.id===pv})?r.jsx("option",{value:pv,children:pv+" (absent)"},pv):null;
  var lz=opts.loudness,li=o.lufs&&isFinite(Number(o.lufs.i))?Number(o.lufs.i):null;
  var etat=dzmLoudPastille(li,lz);
  var ptitre=li==null?"mesurez d'abord (bouton « mesurer » du bandeau Son)":"mesure "+dzmLoudTxt(li)+" LUFS · cible "+(lz==null?"aucune":dzmLoudTxt(lz));
  var plein={gridColumn:"1 / -1"};
  return r.jsxs("div",{className:"svm-delopts",children:[
    r.jsx("span",{children:"preset"}),
    r.jsxs("select",{title:"Preset de sortie (codec, taille, conteneur) — les presets maison suivent les standards",value:pv,onChange:function(e){ch({preset:e.target.value})},children:[absent,grp("Standard"),grp("Maison")]}),
    r.jsx("span",{children:"cadence"}),
    r.jsx("select",{title:"Cadence d'images du rendu final — « projet » laisse celle du preset",value:opts.fps==null||opts.fps===""?"":String(opts.fps),onChange:function(e){var v=e.target.value;ch({fps:v?Number(v):null})},
      children:[r.jsx("option",{value:"",children:"projet (30)"},"")].concat(DZM_DEL_FPS.map(function(f){return r.jsx("option",{value:String(f),children:String(f)},String(f))}))}),
    r.jsx("span",{children:"loudness"}),
    r.jsxs("span",{className:"svm-delloud",children:[
      r.jsx("select",{title:"Normalisation de loudness en deux passes (ffmpeg loudnorm) — « aucune » laisse le mix tel quel",value:lz==null?"":String(lz),onChange:function(e){var v=e.target.value;ch({loudness:v?Number(v):null})},
        children:[r.jsx("option",{value:"",children:"aucune"},"")].concat(DZM_DEL_LOUD.map(function(l){return r.jsx("option",{value:String(l[0]),children:l[1]},String(l[0]))}))}),
      r.jsx("span",{className:"svm-loudpill","data-etat":etat,title:ptitre})]}),
    o.hasRange?r.jsxs("label",{className:"svm-delrange",style:plein,title:"Ne rendre que la plage I/O de la timeline (coupe de sortie — sous-titres et titres gardent l'horloge globale)",children:[
      r.jsx("input",{type:"checkbox",checked:!!opts.rangeOnly,title:"Rendre la plage I/O seulement",onChange:function(e){ch({rangeOnly:!!e.target.checked})}}),
      " Rendre la plage I/O seulement"]}):null,
    r.jsx("button",{className:"svm-secbtn svm-delsave",style:plein,title:"Enregistrer preset + cadence comme preset maison (un nom est demandé)",onClick:function(){if(o.onSavePreset)o.onSavePreset()},children:"Enregistrer ce réglage…"})]})}
/* ── D-13 (22/09/2026) : LE ZOOM DYNAMIQUE ───────────────────────────────
   `dz` = {x0,y0,w0,x1,y1,w1,ease} en FRACTIONS du cadre — MÊMES bornes que
   `montage_service._dz_spec` (w ∈ [0.1,1], x/y ∈ [0,1−w], plein cadre aux
   deux bouts = null). Le rendu est un zoompan (backend) ; en direct, le
   lecteur applique `dzmDzCss` à la <video> active (translate puis scale,
   origine 0 0) — même géométrie, pas le même moteur. */
function dzmDzR(v){return Math.round(v*1e6)/1e6}
function dzmDzNorm(raw){
  if(!raw||typeof raw!=="object")return null;
  var ks=["x0","y0","w0","x1","y1","w1"],o={},i,v;
  for(i=0;i<ks.length;i++){v=Number(raw[ks[i]]);if(!isFinite(v))return null;o[ks[i]]=v}
  ["0","1"].forEach(function(s){
    o["w"+s]=Math.max(.1,Math.min(1,o["w"+s]));
    o["x"+s]=dzmDzR(Math.max(0,Math.min(1-o["w"+s],o["x"+s])));
    o["y"+s]=dzmDzR(Math.max(0,Math.min(1-o["w"+s],o["y"+s])));
    o["w"+s]=dzmDzR(o["w"+s])});
  if(o.x0===0&&o.y0===0&&o.x1===0&&o.y1===0&&o.w0>=1&&o.w1>=1)return null;
  o.ease=raw.ease==="lin"?"lin":"doux";
  return o}
function dzmDzOf(c){return c&&c.dz?dzmDzNorm(c.dz):null}
/* interpolation sur un `d` DEJA normalise (partagee par dzmDzAt et dzmDzCss) */
function dzmDzAtN(d,u){
  u=Math.max(0,Math.min(1,Number(u)||0));
  if(d.ease!=="lin")u=u*u*(3-2*u);
  return {x:dzmDzR(d.x0+(d.x1-d.x0)*u),y:dzmDzR(d.y0+(d.y1-d.y0)*u),w:dzmDzR(d.w0+(d.w1-d.w0)*u)}}
function dzmDzAt(dz,u){var d=dzmDzNorm(dz);return d?dzmDzAtN(d,u):{x:0,y:0,w:1}}
function dzmDzPreset(name){
  if(name==="in")return dzmDzNorm({x0:0,y0:0,w0:1,x1:.2,y1:.2,w1:.6});
  if(name==="out")return dzmDzNorm({x0:.2,y0:.2,w0:.6,x1:0,y1:0,w1:1});
  return null}
/* k = 0 (début) | 1 (fin) ; dx/dy en fraction du cadre — le rectangle reste
   dans le cadre, la largeur ne bouge pas */
function dzmDzMove(dz,k,dx,dy){
  var d=dzmDzNorm(dz);if(!d)return null;var s=k?"1":"0",o=Object.assign({},d);
  o["x"+s]=o["x"+s]+(Number(dx)||0);o["y"+s]=o["y"+s]+(Number(dy)||0);
  return dzmDzNorm(o)||d}
/* dw en fraction : la largeur change AUTOUR DU CENTRE du rectangle, bornée
   [0.1, 1] et ramenée dans le cadre par la normalisation */
function dzmDzScale(dz,k,dw){
  var d=dzmDzNorm(dz);if(!d)return null;var s=k?"1":"0",o=Object.assign({},d);
  var w0=o["w"+s],w1=Math.max(.1,Math.min(1,w0+(Number(dw)||0))),cx=o["x"+s]+w0/2,cy=o["y"+s]+w0/2;
  o["w"+s]=w1;o["x"+s]=cx-w1/2;o["y"+s]=cy-w1/2;
  return dzmDzNorm(o)||d}
/* la transformation CSS de la <video> pour la fenêtre à u : scale = 1/w,
   puis translation de −x·s / −y·s (en % de la boîte de l'élément), origine
   0 0 — posée par la FEUILLE (`.svm-live>.svm-livemedia{transform-origin:0 0}`),
   pas par l'appelant. "" quand il n'y a pas de zoom (dz absent ou invalide).
   UN SEUL arrondi (1e4) pour les trois nombres. */
function dzmDzCss(dz,u){
  var d=dzmDzNorm(dz);if(!d)return "";
  var r=dzmDzAtN(d,u),s=1/r.w,f=function(v){return String(Math.round(v*1e4)/1e4)};
  return "translate("+f(-r.x*s*100)+"%, "+f(-r.y*s*100)+"%) scale("+f(s)+")"}
/* ── D-15 (22/09/2026) : INTERPOLATION ET RAMPE ───────────────────────────
   `retime` = "blend" | "flow" (nearest = absent, l'historique) ; le backend
   ne le lit qu'avec une vitesse ≠ 1. La RAMPE de Resolve devient « diviser
   à t puis deux vitesses » : MÊME règle que dzmCarve pour la partie droite
   (srcIn + (t − start) · ancienne vitesse, identifiant libre par dzmFreeId),
   la droite perd sa transition d'entrée (elle est au milieu du plan). Bornes
   0,3 s aux deux bords. Rend {clips, left, right, refus:""|"clip"|"hors"|"bord"}. */
function dzmRetimeOf(c){var v=c&&c.retime;return v==="blend"||v==="flow"?v:null}
function dzmRampe(clips,id,t,spdL,spdR){
  var cs=Array.isArray(clips)?clips:[],c=cs.filter(function(k){return k&&k.id===id})[0],ko=function(m){return {clips:cs,left:null,right:null,refus:m}};
  if(!c)return ko("clip");
  t=Number(t);var s=Number(c.start)||0,e=Number(c.end)||0;
  if(!(t>s&&t<e))return ko("hors");
  if(t-s<.3||e-t<.3)return ko("bord");
  /* SANS arrondi : « remplir » pose des vitesses à trois décimales (1,333) ;
     une gauche réécrite à 1,33 consommerait moins de source que R.srcIn ne
     le suppose (trou ≈ t·0,003 s au raccord). Le select fournit déjà deux décimales. */
  var cl=function(v){v=Number(v);return v>0?Math.max(.25,Math.min(4,v)):1},sp=dzmSpeedNum(c);
  var L=Object.assign({},c,{end:dzmR3(t)}),R=Object.assign({},c,{id:dzmFreeId(dzmTaken(cs),c.id),start:dzmR3(t)});
  if(c.srcIn!=null||c.src)R.srcIn=dzmR3((Number(c.srcIn)||0)+(t-s)*sp);
  /* continuité du zoom au raccord : la fenêtre à t devient la fin de la gauche
     et le début de la droite — la LAME du bundle, elle, hérite `dz` tel quel
     (reste daté pour la clôture) */
  var d=dzmDzOf(c);if(d){var m=dzmDzAtN(d,(t-s)/(e-s));L.dz=Object.assign({},d,{x1:m.x,y1:m.y,w1:m.w});R.dz=Object.assign({},d,{x0:m.x,y0:m.y,w0:m.w})}
  if(cl(spdL)===1)delete L.speed;else L.speed=cl(spdL);
  if(cl(spdR)===1)delete R.speed;else R.speed=cl(spdR);
  delete R.transition;delete R.transition_s;
  var out=[];cs.forEach(function(k){out.push(k===c?L:k);if(k===c)out.push(R)});
  return {clips:out,left:L.id,right:R.id,refus:""}}
/* ── D-16 (22/09/2026) : STABILISATION ───────────────────────────────────
   `stab` = {on, smooth 1..100, crop keep|black, zoom −30..30} — mêmes bornes
   que `_v1_stab` du backend (null hors `on` : la clé est alors retirée du
   clip). L'analyse (.trf) vit chez le backend, PAR SOURCE : le client la
   DEMANDE (POST /api/montage/stab, contrat de /proxy) et la suit par
   GET /api/jobs/{id} — premier consommateur client d'un job « par source ».
   stabState phrase l'état d'un job {status,progress,error}|null. */
function dzmStabNorm(raw){
  if(!raw||typeof raw!=="object"||!raw.on)return null;
  var n=function(v,lo,hi,dv){v=Number(v);return isFinite(v)?Math.round(Math.max(lo,Math.min(hi,v))):dv};
  return {on:!0,smooth:n(raw.smooth,1,100,15),crop:raw.crop==="black"?"black":"keep",zoom:n(raw.zoom,-30,30,0)}}
function dzmStabOf(c){return c&&c.stab?dzmStabNorm(c.stab):null}
function dzmStabState(job){
  if(!job)return "à analyser";
  if(job.status==="done")return "analysée";
  if(job.status==="failed")return "échec : "+String(job.error||"?");
  return "analyse "+Math.round(Number(job.progress)||0)+" %"}
/* ── D-14 (22/09/2026) : KEYFRAMES D'ÉCHELLE ET D'OPACITÉ SUR LES OVERLAYS ──
   Contrat du rendu (T7a) : un point sans `scale` (ou `opacity`) ne participe
   pas à CETTE animation ; sans point porteur, la statique du clip reste.
   dzmMpLerp2 = svmMpLerp du bundle (lerp sur le SOUS-ENSEMBLE porteur,
   constante hors bornes) avec un défaut `dv`, et sans supposer les points
   triés. dzmMpKeep : mesuré, svmMpPlace construit un point NEUF
   {t,x,y,rotate} — il perdait scale/opacity du patch ET du point écrasé ;
   ceci les reporte (le patch `vals` gagne, sinon le point `prev`), bornées
   comme le backend (.05..3 au millième, 0..1 au centième), jamais de clé
   sans valeur finie. */
function dzmMpLerp2(pts,tl,key,dv){
  var ps=[],i,v;
  for(i=0;i<(pts||[]).length;i++){v=Number(pts[i]&&pts[i][key]);
    if(pts[i]&&pts[i][key]!=null&&isFinite(v))ps.push({t:Number(pts[i].t)||0,v:v})}
  if(!ps.length)return dv;
  ps.sort(function(a,b){return a.t-b.t});tl=Number(tl)||0;
  if(tl<=ps[0].t)return ps[0].v;
  var last=ps[ps.length-1];
  if(tl>=last.t)return last.v;
  for(i=1;i<ps.length;i++){var p0=ps[i-1],p1=ps[i];
    if(tl<p1.t)return p0.v+(p1.v-p0.v)*(tl-p0.t)/Math.max(.001,p1.t-p0.t)}
  return last.v}
var DZM_MP_EXTRA={scale:[.05,3,1000],opacity:[0,1,100]};
function dzmMpKeep(np,vals,prev){
  Object.keys(DZM_MP_EXTRA).forEach(function(k){
    var b=DZM_MP_EXTRA[k],v=Number(vals&&vals[k]!=null?vals[k]:prev?prev[k]:null);
    if((vals&&vals[k]!=null)||(prev&&prev[k]!=null))
      if(isFinite(v))np[k]=Math.min(b[1],Math.max(b[0],Math.round(v*b[2])/b[2]))});
  return np}
/* L'HÔTE DES PROPRIÉTÉS DE PLAN (D-13, puis D-15 et D-16) : UNE section de
   l'inspecteur, montée UNE fois (DZ1) sur un clip V1 réel. props : {clip,
   u (avancement 0..1 de la tête dans le clip), speed (vitesse du clip),
   head (tête de lecture, s), onChange(patch, heavy), onRampe(t, spdL, spdR)}
   — `onChange` reçoit un patch de clip ({dz:…} ou {dz:void 0}) et l'appelant
   écrit l'historique. `r` n'est lu qu'à l'appel, comme DzmTitleInspector.
   Le useState de la rampe vient APRÈS la garde `!c` : l'hôte n'est monté
   qu'avec un clip (DZ1), l'ordre des hooks est donc stable — et sans clip
   le composant rend null sans toucher `x` (banc). */
function DzmPlanProps(o){
  var c=o&&o.clip,on=typeof (o&&o.onChange)==="function"?o.onChange:function(){};
  if(!c)return null;
  var st=x.useState(2),rampSpd=st[0],setRampSpd=st[1];
  var dz=dzmDzOf(c),spd=Number(o.speed)||1,rt=dzmRetimeOf(c),head=Number(o.head);
  var inClip=isFinite(head)&&head-c.start>=.3&&c.end-head>=.3;
  var row=function(label,kids,key){return r.jsxs("div",{className:"svm-prop dzm-plan-row",children:[
    r.jsx("div",{className:"svm-propk",children:label}),r.jsx("div",{className:"svm-propv",children:kids})]},key)};
  var sel=function(cur,opts,cb,title){return r.jsx("select",{className:"svm-vitsel",value:cur,title:title,
    onChange:function(e){cb(e.target.value)},children:opts.map(function(p){return r.jsx("option",{value:p[0],children:p[1]},p[0])})})};
  var kids=[row("Zoom dyn.",sel(dz?(dz.w1<dz.w0?"in":dz.w1>dz.w0?"out":"custom"):"off",
    [["off","aucun"],["in","zoom avant"],["out","zoom arrière"],["custom","personnalisé"]],
    function(v){if(v==="custom"&&dz)return;on({dz:v==="off"?void 0:v==="custom"?(dz||dzmDzPreset("in")):dzmDzPreset(v)},!0)},
    "Zoom dynamique : deux fenêtres, début (vert) et fin (rouge) du plan — glisser les rectangles dans le lecteur, le rendu interpole"),"dz")];
  if(dz){
    kids.push(row("Courbe",sel(dz.ease,[["doux","douce"],["lin","linéaire"]],function(v){on({dz:Object.assign({},dz,{ease:v})},!0)},"Interpolation du zoom"),"dz-ease"));
    kids.push(row("Fenêtres",r.jsx("span",{className:"dzm-plan-hint",
      children:"début "+Math.round(dz.w0*100)+" % · fin "+Math.round(dz.w1*100)+" %"}),"dz-w"))}
  /* D-15 : l'interpolation du retime (sans effet à 100 %, le backend ne la lit qu'avec une vitesse) */
  kids.push(row("Interpolation",sel(rt||"nearest",[["nearest","image voisine"],["blend","fondu d'images"],["flow","flux optique (lent)"]],
    function(v){on({retime:v==="nearest"?void 0:v},!0)},
    spd===1?"Sans effet à 100 % — change d'abord la vitesse":"Qualité du retime (D-15) : fondu = flou de mouvement, flux optique = images intermédiaires calculées"),"rt"));
  /* D-15 : la rampe = diviser à la tête, la partie droite à la vitesse choisie */
  kids.push(row("Rampe",r.jsxs("span",{className:"dzm-plan-hint",children:[
    r.jsx("button",{className:"svm-minibtn",disabled:!inClip,
      title:inClip?"Diviser le plan à la tête : la partie gauche garde sa vitesse, la droite passe à la vitesse choisie":"Placer la tête à 0,3 s au moins des deux bords du plan",
      onClick:function(){if(typeof o.onRampe==="function")o.onRampe(head,spd,rampSpd)},children:"Diviser à la tête →"}),
    sel(String(rampSpd),[["0.5","50 %"],["0.75","75 %"],["1","100 %"],["1.5","150 %"],["2","200 %"],["3","300 %"]],
      function(v){setRampSpd(Number(v))},"Vitesse de la partie droite")]}),"rampe"));
  /* D-16 : la stabilisation — case (lourd), « Analyser » (désactivé pendant
     l'analyse), chip d'état ; puis, si active, deux curseurs (léger : le
     range tire onChange à chaque cran, la rafale de 600 ms fait UNE entrée)
     et le sort des bords (lourd). props : stabJob = état du job de CETTE
     source ({status,progress,error}|null), onStab() = demander l'analyse. */
  /* revue : « Analyser » n'est réarmé que sur un échec — après « analysée »
     un second clic ne ferait qu'un POST inoffensif (le cache n'est jamais purgé) */
  var sb=dzmStabOf(c),sj=o.stabJob||null,sjBloque=!!sj&&sj.status!=="failed";
  kids.push(row("Stabilis.",r.jsxs("span",{className:"dzm-plan-hint dzm-stab",children:[
    r.jsx("input",{type:"checkbox",checked:!!sb,title:"Stabiliser le plan (vidstab, deux passes au rendu)",
      onChange:function(e){on({stab:e.target.checked?dzmStabNorm({on:!0}):void 0},!0)}}),
    r.jsx("button",{className:"svm-minibtn",disabled:!sb||sjBloque,
      title:"Analyser la source maintenant (sinon le rendu le fera, plus long)",
      onClick:function(){if(typeof o.onStab==="function")o.onStab()},children:"Analyser"}),
    r.jsx("span",{className:"dzm-stab-st","data-st":sj?sj.status:"",children:sb?dzmStabState(sj):""})]}),"stab"));
  if(sb){
    var rng=function(key,lo,hi,label,title){return row(label,r.jsxs("span",{className:"dzm-plan-hint dzm-stab",children:[
      r.jsx("input",{type:"range",min:lo,max:hi,value:sb[key],title:title,
        onChange:function(e){var p={};p[key]=Number(e.target.value);on({stab:dzmStabNorm(Object.assign({},sb,p))},!1)}}),
      " "+sb[key]]}),"stab-"+key)};
    kids.push(rng("smooth",1,100,"Lissage","Fenêtre de lissage (images) — 15 par défaut"));
    kids.push(rng("zoom",-30,30,"Zoom","Zoom fixe en % pour cacher les bords (0 = optzoom)"));
    kids.push(row("Bords",sel(sb.crop,[["keep","garder"],["black","noir"]],
      function(v){on({stab:dzmStabNorm(Object.assign({},sb,{crop:v}))},!0)},"Que faire des bords découverts"),"stab-crop"))}
  return r.jsxs("div",{className:"dzm-plan",children:[r.jsx("div",{className:"dzm-plan-t",children:"Propriétés du plan"}),
    r.jsx("div",{className:"svm-props",children:kids})]})}
/* LES DEUX RECTANGLES (vert = début, rouge = fin) dans le cadre du lecteur,
   en % du cadre — glisser le corps = déplacer, glisser le coin = échelle.
   props : {dz, onChange(dz)} ; le cadre est MESURÉ au pointerdown (la boîte
   du wrap = le cadre, hors vzoom) ; le geste écoute la FENÊTRE (la forme de
   la maison, comme la barre d'outils §4.2 — jamais de capture sur l'élément),
   filtre son pointerId, coalesce par rAF (un setClips par image, pas par
   événement) et rejoue l'état du pointerdown par les pures. */
function DzmDzRects(o){
  var dz=dzmDzNorm(o&&o.dz),on=typeof (o&&o.onChange)==="function"?o.onChange:function(){};
  if(!dz)return null;
  var mk=function(k){
    var s=k?"1":"0",x=dz["x"+s],y=dz["y"+s],w=dz["w"+s];
    var down=function(mode){return function(e){
      if(e.button)return;
      var wrap=e.currentTarget.closest(".dzm-dzwrap"),bx=wrap?wrap.getBoundingClientRect():null;
      if(!bx||bx.width<2)return;
      var w=window,sx=e.clientX,sy=e.clientY,base=dz,pid=e.pointerId,last=null,raf=0;
      e.preventDefault();e.stopPropagation();
      var mv=function(e2){if(e2.pointerId!==pid)return;last=e2;
        if(!raf)raf=requestAnimationFrame(function(){raf=0;var dx=(last.clientX-sx)/bx.width,dy=(last.clientY-sy)/bx.height;
          on(mode==="move"?dzmDzMove(base,k,dx,dy):dzmDzScale(base,k,dx))})};
      var up=function(e2){if(e2.pointerId!==pid)return;if(raf)cancelAnimationFrame(raf);raf=0;
        w.removeEventListener("pointermove",mv);w.removeEventListener("pointerup",up);w.removeEventListener("pointercancel",up)};
      w.addEventListener("pointermove",mv);w.addEventListener("pointerup",up);w.addEventListener("pointercancel",up)}};
    return r.jsxs("div",{className:"dzm-dzrect","data-k":k?"fin":"debut",
      style:{left:(x*100)+"%",top:(y*100)+"%",width:(w*100)+"%",height:(w*100)+"%"},
      title:(k?"Fin":"Début")+" du zoom — glisser : déplacer · coin : échelle",
      onPointerDown:down("move"),children:[
        r.jsx("span",{className:"dzm-dzlab",children:k?"fin":"début"}),
        r.jsx("i",{className:"dzm-dzh",onPointerDown:down("scale")})]},k)};
  return r.jsxs("div",{className:"dzm-dzwrap",children:[mk(0),mk(1)]})}
/* ── E-2 (23/09/2026) : LE TIROIR MÉDIAS — provenance, filtre, liste paginée ──
   Le tiroir sert les RENDUS VIDÉO (exigence n°1 de E-2) ; images et sons
   restent au popover « lier » (`ovPicker`) : « le sélecteur devient un
   tiroir » n'est vrai que pour les vidéos, pour ne pas dupliquer trois
   fetchs ni rouvrir R_M16C (écart daté 23/09/2026).

   PROVENANCE : aucun provider ne s'appelle « Studio » ni « Chapitres » —
   les providers mesurés sont seedance, heygen, composition, template, news,
   episode, ugc, montage, animation, asset3d, sprite2d, card3d (+ NULL, lu
   « seedance » par le backend). Le groupe affiché est DÉRIVÉ du provider
   par cette table (comme les chips de la Bibliothèque, patch_bundle_libprov)
   et les chips sont dérivées des jobs REÇUS, jamais une liste figée. Un
   provider inconnu s'affiche tel quel : on ne cache pas un nom sous
   « Autres ». */
var DZM_PROV_LBL={seedance:"Studio",heygen:"Studio",composition:"Studio",animation:"Studio",
  episode:"Chapitres",news:"News",template:"Templates",ugc:"Importés",montage:"Montages"};
function dzmProvGroupe(p){var k=(p==null||p==="")?"seedance":String(p);return DZM_PROV_LBL[k]||k}
/* « Tout » en tête, puis les groupes dans l'ORDRE D'APPARITION, uniques */
function dzmProvChips(jobs){var out=["Tout"],seen={};(jobs||[]).forEach(function(j){
  var g=dzmProvGroupe(j&&j.provider);if(!seen[g]){seen[g]=1;out.push(g)}});return out}
/* filtre LOCAL sur les pages déjà chargées : groupe dérivé + `q` sur le titre
   (ou le job_id quand le titre manque), insensible à la casse. Un job null
   est ignoré. L'entrée n'est pas mutée. */
function dzmMediaFiltre(jobs,f){var g=(f&&f.groupe)||"Tout",q=String((f&&f.q)||"").trim().toLowerCase();
  return (jobs||[]).filter(function(j){if(!j)return !1;if(g!=="Tout"&&dzmProvGroupe(j.provider)!==g)return !1;
    return !q||String(j.title||j.job_id||"").toLowerCase().indexOf(q)>=0})}
/* LE COMPOSANT. props : {open, trId, exts, onAdd(job), onClose(), dragPayload(e,src,label,kind,dur)}.
   Il lit `r`/`x` À L'APPEL (comme DzmFinBandeau) et ses hooks tournent
   ferme comme ouvert — l'hôte le monte en permanence et bascule `open`,
   la règle des hooks interdit un `return null` avant les useState.
   Une seule vérité : le serveur. `GET /api/jobs?limit=24&offset=&video=1`
   (juge vidéo côté backend, T1) ; la recherche `q` est locale sur la page
   chargée ET, dès 2 caractères, re-demandée au serveur (`&q=`, 250 ms de
   repos, un compteur écarte la réponse d'une frappe dépassée) ; le filtre
   `groupe` reste LOCAL aux pages chargées (les groupes sont dérivés — « Plus »
   continue de paginer sans filtre serveur ; choix daté 23/09/2026).
   DEUX JUGES COMPLÉMENTAIRES (revue 23/09/2026) : le serveur juge
   l'EXTENSION (`video=1`), la couche juge le STATUT — `dzmIsVideoJob` est
   appliqué TOUJOURS (status done, pas d'aperçu `_preview`, chemin posé),
   `exts` restant facultatif (null = pas de second tamis par extension,
   mesuré : la garde `!exts` de dzmIsVideoJob vient après celle du statut).
   Sans lui, un job en cours ou en erreur dont `video_path` est déjà posé
   entrerait dans le tiroir. Après une erreur HTTP, « Plus » reste actif
   et rejoue depuis le même offset : accepté, daté 23/09/2026 (la page
   manquée n'a pas été comptée, l'offset n'a pas avancé). Vignette : la première
   image de la bande (`/api/montage/strip … n=1`). Durée : `dzmDurTxt`,
   le formateur déjà partagé avec le transport (pas de second m:ss). */
var DZM_MED_PAGE=24,DZM_MED_REPOS=250;
function DzmMediaDrawer(o){
  o=o||{};
  var s1=x.useState([]),jobs=s1[0],setJobs=s1[1];
  var s2=x.useState(0),offset=s2[0],setOffset=s2[1];
  var s3=x.useState(!1),fin=s3[0],setFin=s3[1];
  var s4=x.useState("Tout"),groupe=s4[0],setGroupe=s4[1];
  var s5=x.useState(""),q=s5[0],setQ=s5[1];
  var s6=x.useState(""),st=s6[0],setSt=s6[1];
  var seq=x.useRef(0),vivant=x.useRef(!0);
  x.useEffect(function(){vivant.current=!0;return function(){vivant.current=!1}},[]);
  var qServ=q.trim().length>=2?q.trim():"";
  var charge=function(off,qq,remplace){
    var n=++seq.current;setSt("…");
    var u="/api/jobs?limit="+DZM_MED_PAGE+"&offset="+off+"&video=1"+(qq?"&q="+encodeURIComponent(qq):"");
    return fetch(u).then(function(res){if(!res.ok)throw new Error("HTTP "+res.status);return res.json()})
      .then(function(d){if(!vivant.current||n!==seq.current)return;
        var page=Array.isArray(d)?d:[];
        setJobs(function(prev){var base=remplace?[]:prev,vu={};base.forEach(function(j){if(j&&j.job_id)vu[j.job_id]=1});
          return base.concat(page.filter(function(j){if(!j||!j.job_id||vu[j.job_id])return !1;vu[j.job_id]=1;return !0}))});
        setOffset(off+page.length);setFin(page.length<DZM_MED_PAGE);setSt("")})
      .catch(function(e){if(vivant.current&&n===seq.current)setSt("Rendus : chargement impossible ("+String((e&&e.message)||e)+")")})};
  /* ouverture ou nouvelle recherche serveur : repartir de zéro (250 ms de repos sur la frappe) */
  x.useEffect(function(){
    if(!o.open)return;
    var t=setTimeout(function(){charge(0,qServ,!0)},qServ?DZM_MED_REPOS:0);
    return function(){clearTimeout(t)}},[o.open?1:0,qServ]);
  if(!o.open)return null;
  var vus=jobs.filter(function(j){return dzmIsVideoJob(j,o.exts)});
  var chips=dzmProvChips(vus),g=chips.indexOf(groupe)>=0?groupe:"Tout";
  var liste=dzmMediaFiltre(vus,{groupe:g,q:q});
  var row=function(j){var jid=String(j.job_id||""),lbl=j.title||jid;
    var src=encodeURIComponent(JSON.stringify({job_id:jid}));
    return r.jsxs("div",{className:"svm-medrow",draggable:!0,
      title:lbl+" — Glisser vers une bande, ou cliquer pour poser sur "+(o.trId||"la piste vidéo"),
      onDragStart:function(e){if(o.dragPayload)o.dragPayload(e,{job_id:jid},lbl,"video",j.duration_s||0)},
      onClick:function(){if(o.onAdd)o.onAdd(j)},
      children:[
        r.jsx("img",{src:"/api/montage/strip?src="+src+"&n=1&w=96&h=54",loading:"lazy",alt:"",draggable:!1,
          onError:function(e){e.target.style.visibility="hidden"}}),
        r.jsxs("div",{className:"svm-medmeta",children:[
          r.jsx("div",{className:"svm-medtitle",children:lbl}),
          r.jsxs("div",{className:"svm-medsub",children:[
            r.jsx("span",{children:j.duration_s>0?dzmDurTxt(j.duration_s):"—"}),
            r.jsx("span",{className:"svm-themechip svm-medgrp",children:dzmProvGroupe(j.provider)})]})]})]},jid||lbl)};
  return r.jsxs("div",{className:"svm-meddrawer",children:[
    r.jsxs("div",{className:"svm-medhead",children:[
      r.jsx("div",{className:"svm-poptitle",children:"Médias — rendus vidéo"+(o.trId?" → "+o.trId:"")}),
      r.jsx("button",{className:"svm-secbtn",title:"Fermer le tiroir Médias",onClick:function(){if(o.onClose)o.onClose()},children:"Fermer"})]}),
    r.jsx("input",{type:"search",className:"svm-medq",value:q,placeholder:"Rechercher un titre…",
      onChange:function(e){setQ(e.target.value)}}),
    r.jsx("div",{className:"svm-medchips",children:chips.map(function(c){
      return r.jsx("button",{className:"svm-themechip","data-on":c===g?"":void 0,
        onClick:function(){setGroupe(c)},children:c},c)})}),
    r.jsx("div",{className:"svm-medlist",children:liste.map(row)}),
    st?r.jsx("div",{className:"svm-medst",children:st}):null,
    !st&&!liste.length?r.jsx("div",{className:"svm-medst",children:vus.length?"Aucun rendu dans ce groupe.":"Aucun rendu vidéo terminé."}):null,
    !fin?r.jsx("button",{className:"svm-secbtn svm-medplus",disabled:st==="…",
      title:"Charger les rendus suivants",
      onClick:function(){charge(offset,qServ,!1)},children:"Plus"}):null]})}
/* E-5 (lot E-B, tache 4, 23/09/2026) — LE DERNIER RENDU FINAL PAR PROJET.
   Aucun JobRecord ne porte de project_id (mesure routes.py:3330, _job_to_dict) :
   la memoire est COTE CLIENT, un store {project_id:{job_id,name,at}} que l'hote
   lit au montage et ecrit apres chaque rendu FINAL dans la cle localStorage
   du dernier rendu (jamais la preview). Ici deux fonctions
   PURES : finStore rend un objet NEUF (pose, ou retrait quand fin est null) et
   finOf lit l'entree du projet ou null. Un project_id vide (projet pas encore
   nomme) se range sous la cle "_". Deux etats distincts dans l'hote : dzFin
   (le bandeau est visible) et ce store (il y a eu un rendu). */
function dzmFinKey(pid){var k=String(pid==null?"":pid).trim();return k||"_"}
function dzmFinStore(store,pid,fin){
  var out={},k=dzmFinKey(pid),s=(store&&typeof store==="object")?store:{};
  Object.keys(s).forEach(function(q){out[q]=s[q]});
  if(fin==null)delete out[k];
  else out[k]={job_id:String(fin.job_id||""),name:String(fin.name||""),at:Number(fin.at)||0};
  return out}
function dzmFinOf(store,pid){
  var s=(store&&typeof store==="object")?store:{},v=s[dzmFinKey(pid)];
  return (v&&typeof v==="object"&&v.job_id)?v:null}
/* E-8 (lot E-B, tache 6, 23/09/2026) — LA LARGEUR DE L'INSPECTEUR. L'hote
   (EB6b) lit la cle dz_svm_insp du stockage local au montage et la poignee (EB6a) pose
   startW+(startX-clientX) a chaque pointermove : les deux passent ICI, une
   seule ecriture des bornes 260..480 et du defaut 300 (.svm-insp{width:300px},
   son-vfx-montage.css:233). dzmClamp est la forme generale : null / "" /
   undefined / booleen / NaN / ±Infinity / objet -> def, jamais 0 puis la
   borne basse (une cle JSON corrompue rendrait l'inspecteur a 260 sans un
   mot) ; une chaine numerique est lue (le stockage local rend des chaines). */
function dzmClamp(v,lo,hi,def){
  if(v==null||v===""||typeof v==="boolean")return def;
  var n=typeof v==="number"?v:Number(typeof v==="string"?v.trim():NaN);
  if(n!==n||n===Infinity||n===-Infinity)return def;
  return Math.min(hi,Math.max(lo,n))}
function dzmInspW(raw){return Math.round(dzmClamp(raw,260,480,300))}
/* E-9 (lot E-B, tache 7, 23/09/2026) — LA HAUTEUR DE LA TIMELINE ET LA DUREE
   SUR LES CLIPS. L'hote (EB7a, repli R_EB6B) lit la cle dz_svm_tlh au montage
   puis, dans un effet, la borne sur la hauteur MESUREE de .dzsvm ; la poignee
   (EB7b, AU-DESSUS de la timeline : tirer vers le haut agrandit) pose
   startH+(startY-clientY) a chaque pointermove : tout passe ICI. Bornes 30..70 %
   du total (conception E-9) ; `null` = « aucun choix » : l'hote ne pose ni
   data-h ni height, et le plafond historique (.dzsvm .svm-tl{max-height:48vh},
   montage.css:18) reste — la conception (30–70 %) et ce plafond sont
   incompatibles, le plan tranche par `[data-h]` (affirmation demente n°5).
   Total inconnu (<= 0, non fini) -> null aussi : au montage, .dzsvm n'est pas
   encore mesuree. dzmDurLbl : `label · m:ss` par dzmDurTxt (svmRuler du
   bundle, JAMAIS un second formateur) quand la chip « durées » est allumee ;
   label seul sinon ou si end <= start ; label vide -> la duree seule. */
function dzmTlH(raw,total){
  var t=typeof total==="number"?total:Number(total);
  if(!(t>0)||t===Infinity)return null;
  var n=dzmClamp(raw,.3*t,.7*t,NaN);
  return n!==n?null:Math.round(n)}
function dzmDurLbl(label,start,end,on){
  var l=label==null?"":String(label),d=Number(end)-Number(start);
  if(!on||!(d>0))return l;
  var txt=dzmDurTxt(d);
  return l?l+" · "+txt:txt}
/* D-7 (lot E-B, tache 8, 23/09/2026) — LA MINI-CARTE DE LA TIMELINE. La
   conception la voulait « au-dessus de la regle » ; dans .svm-lanes elle
   suivrait le zoom (width:zoomPct%). L'hote (EB8a) la pose dans .svm-tl
   AVANT .svm-scroll, HORS zoom (affirmation dementie n°6 du plan), et garde
   pour lui le « clic = centrer » : il est seul a tenir tlScrollRef. Ici, la
   GEOMETRIE seule : dzmMinimap rend des lignes (une par piste, dans l'ordre
   recu, genre par dzmKindOf — la table existante) et des rectangles en
   FRACTIONS [0,1] de la duree (start/dur, end/dur bornes). Le champ piste d'un
   clip est `tr` (mesure : 58 `c.tr` dans .bak_montage, aucun `c.track`).
   Ignores : clips hors [0,dur], a duree <= 0, sans piste connue, null ; une
   piste dupliquee ne fait qu'une ligne. dur <= 0, non fini, ou entrees qui ne
   sont pas des tableaux -> {rows:[],rects:[]} : la mini-carte se tait, elle
   ne devine rien. Rien n'est mute. */
function dzmMinimap(clips,tracks,dur){
  var d=typeof dur==="number"?dur:Number(dur),rows=[],rects=[],idx={};
  if(!Array.isArray(clips)||!Array.isArray(tracks)||!(d>0)||d===Infinity)return{rows:rows,rects:rects};
  tracks.forEach(function(t){if(!t||t.id==null)return;var id=String(t.id);if(idx[id]!=null)return;
    idx[id]=rows.length;rows.push({id:id,kind:dzmKindOf(id,t.kind)})});
  clips.forEach(function(c){if(!c)return;var tr=String(c.tr==null?"":c.tr),row=idx[tr];if(row==null)return;
    var s=Number(c.start),e=Number(c.end);if(!(e>s)||e<=0||s>=d)return;
    rects.push({tr:tr,row:row,x0:Math.max(0,s/d),x1:Math.min(1,e/d),kind:rows[row].kind})});
  return{rows:rows,rects:rects}}
/* Le composant lit `r` a l'appel (comme DzmFinBandeau). Props : clips, tracks,
   dur, viewFrac [a,b] (la fenetre visible, calculee par l'hote sur scroll et
   zoom), onSeek(frac). Une div.svm-mmrow par ligne, hauteur 100/N % des 30 px
   (feuille montage.css) ; les rectangles en % ; la fenetre .svm-mmview est
   pointer-events:none par la feuille : le clic tombe toujours sur la carte,
   borne 0..1 sur sa largeur mesuree. Aucun hook : la carte est un pur rendu. */
function DzmMinimap(o){
  o=o||{};
  var m=dzmMinimap(o.clips,o.tracks,o.dur),n=m.rows.length,vf=Array.isArray(o.viewFrac)?o.viewFrac:[0,1];
  var a=dzmClamp(vf[0],0,1,0),b=dzmClamp(vf[1],0,1,1);if(b<a)b=a;
  function clic(e){if(typeof o.onSeek!=="function")return;var rc=e.currentTarget.getBoundingClientRect();
    if(!(rc.width>0))return;o.onSeek(Math.max(0,Math.min(1,(e.clientX-rc.left)/rc.width)))}
  return r.jsxs("div",{className:"svm-minimap",title:"Mini-carte — cliquer pour centrer la timeline",onClick:clic,children:[
    m.rows.map(function(row,i){return r.jsx("div",{className:"svm-mmrow",style:{height:(100/n)+"%"},
      children:m.rects.filter(function(q){return q.row===i}).map(function(q,k){
        return r.jsx("div",{className:"svm-mmrect","data-kind":q.kind,
          style:{left:(q.x0*100)+"%",width:((q.x1-q.x0)*100)+"%"}},k)})},row.id)}),
    r.jsx("div",{className:"svm-mmview",style:{left:(a*100)+"%",width:((b-a)*100)+"%"}})]})}
/* ── E-6 (lot E-C, tâche 1, 23/09/2026) : LE MENU — combo → touche, modèle, composant ──
   Décision 1 du plan : PAS de dispatch(id) dans l'hôte — une entrée de menu à
   raccourci REJOUE sa combo par window.dispatchEvent(new KeyboardEvent("keydown",
   dzmComboToKey(combo))) ; onKey reste l'unique dispatch. Jetons MESURÉS dans la
   table SVM_ACTIONS du bundle patché (45 combos) : Ctrl, Maj, Alt, Suppr, Espace,
   Home, End, ?, =, -, lettres, ← → ↑ ↓ ; Échap / Entrée acceptés par avance (revue
   23/09 : pas de jeton Cmd — svmComboCanon sérialise metaKey en « Ctrl+ » ; les
   graphies sans accent sont mortes, la keymap est canonisée par svmComboCanon).
   Clé finale : lettre → minuscule (KeyboardEvent.key sans Maj), jeton nommé par
   la table, autre jeton tel quel. Vide, non-chaîne, modificateur seul → null. */
var DZM_KEY_TOK={"suppr":"Delete","échap":"Escape","espace":" ","entrée":"Enter",
  "←":"ArrowLeft","→":"ArrowRight","↑":"ArrowUp","↓":"ArrowDown","home":"Home","end":"End","tab":"Tab"};
function dzmComboToKey(combo){
  if(typeof combo!=="string")return null;
  var parts=combo.split("+").map(function(s){return s.trim()}).filter(function(s){return s!==""});
  if(!parts.length)return null;
  var k={key:"",ctrlKey:!1,shiftKey:!1,altKey:!1,metaKey:!1},i,t,l;
  for(i=0;i<parts.length;i++){t=parts[i];l=t.toLowerCase();
    if(l==="ctrl")k.ctrlKey=!0;
    else if(l==="maj"||l==="shift")k.shiftKey=!0;
    else if(l==="alt")k.altKey=!0;
    else if(i===parts.length-1)k.key=DZM_KEY_TOK[l]||(t.length===1?t.toLowerCase():t);
    else return null}
  return k.key?k:null}
/* Décision 2 : six rubriques ≠ les quatre `sec` de SVM_KEY_SECTIONS. Table id →
   rubrique pour les ids connus (tous mesurés dans SVM_ACTIONS du bundle patché,
   banc croisé [20]) ; repli par `sec` : Audio → Édition, Affichage → Affichage,
   Lecture / Montage / inconnu → Timeline. « Projet » n'a aucune action à
   raccourci : l'hôte (T2) y pose ses entrées sans combo. keys_panel (« ? »)
   va dans Aide pour que T2 n'y double pas « Raccourcis ». */
var DZM_MENU_ORDRE=["Projet","Édition","Timeline","Marqueurs","Affichage","Aide"];
var DZM_MENU_RUB={undo:"Édition",redo:"Édition",delete:"Édition",ripple:"Édition",
  range_in:"Édition",range_out:"Édition",range_clear:"Édition",range_cut:"Édition",
  swap_left:"Édition",swap_right:"Édition",nudge_left:"Édition",nudge_right:"Édition",
  gain_up:"Édition",gain_down:"Édition",fade_in_cycle:"Édition",fade_out_cycle:"Édition",mute:"Édition",solo:"Édition",
  snap:"Édition",/* revue 23/09 : bascule sœur de ripple, même rubrique */
  copy:"Édition",paste:"Édition",/* L7 D-6 (24/09/2026) : le presse-papiers est une édition, pas une action de timeline */
  marker_toggle:"Marqueurs",marker_prev:"Marqueurs",marker_next:"Marqueurs",marker_index:"Marqueurs",
  zoom_in:"Affichage",zoom_out:"Affichage",zoom100:"Affichage",toolbar:"Affichage",narration:"Affichage",
  sounds_drawer:"Affichage",fullscreen:"Affichage",safezones:"Affichage",
  keys_panel:"Aide"};
function dzmMenuRub(a){
  var s=a&&DZM_MENU_RUB[a.id];if(s)return s;
  return a.sec==="Audio"?"Édition":a.sec==="Affichage"?"Affichage":"Timeline"}
/* dzmMenuModel(actions, keyLabel) → [{rub, items:[{id,lbl,combo}]}] dans l'ordre
   fixe, rubriques vides omises ; la combo affichée vient de keyLabel(id) (la
   keymap VIVANTE — svmKeyLabel du bundle rend "" sans surcharge) sinon de la
   table ; entrées non-objets ignorées ; l'entrée n'est pas mutée. */
function dzmMenuModel(actions,keyLabel){
  var par={},i,a,rub,cb;
  if(!Array.isArray(actions))return [];
  for(i=0;i<actions.length;i++){a=actions[i];if(!a||typeof a!=="object")continue;
    rub=dzmMenuRub(a);cb=(typeof keyLabel==="function"&&keyLabel(a.id))||a.combo||"";
    (par[rub]=par[rub]||[]).push({id:a.id,lbl:a.lbl==null?"":String(a.lbl),combo:String(cb)})}
  return DZM_MENU_ORDRE.filter(function(n){return par[n]&&par[n].length})
    .map(function(n){return {rub:n,items:par[n]}})}
/* Décision 3 : UN composant sert ☰ (ancré sous le bouton : o.rubs) et les deux
   menus contextuels (au pointeur : o.items à plat). Item {lbl, combo?, run,
   off?, sep?}. AUCUN hook — l'hôte tient l'état {kind,x,y,id}. La fenêtre est
   lue À L'APPEL (gardée par typeof : le shim du banc n'a qu'un objet vide → repli),
   position bornée : left ≤ innerWidth−270 (ÉCART daté 23/09 : le plan disait
   260 = la largeur CSS seule ; 270 garde 10 px de marge droite), top ≤
   innerHeight−40·n. Pas de `o.anchor` (écart 23/09) : T2 calcule x,y depuis
   getBoundingClientRect() du bouton ☰ (left, bottom+4) — une seule entrée.
   `.svm-menugrp` enveloppe chaque rubrique (en-tête + rangées) : T2 le style
   dans montage.css avec svm-menurub / svm-menusep / svm-menuitem / svm-menukey.
   La racine arrête le clic comme le popover (EB5b) et le bandeau E-11 : le
   voile du bundle ferme au clic dehors, Échap dans R_K7. Le clic ferme TOUJOURS
   (finally) : un run qui lève ne laisse pas le menu bloqué sous le voile.
   Écarts datés 23/09 : un menu plus haut que la fenêtre déborde (CSS T2 :
   max-height + overflow) ; pas de navigation clavier dans le menu (souris,
   Échap) ; « Projet » reste vide tant que T2 n'y pose pas ses entrées. */
function DzmCtxMenu(o){
  o=o||{};
  var rubs=Array.isArray(o.rubs)?o.rubs:[{rub:"",items:Array.isArray(o.items)?o.items:[]}];
  var n=rubs.reduce(function(s,g){return s+((g&&Array.isArray(g.items))?g.items.length:0)},0);
  var W=(typeof window!=="undefined"&&window.innerWidth)||1e9,H=(typeof window!=="undefined"&&window.innerHeight)||1e9;
  var px=Number(o.x)||0,py=Number(o.y)||0;
  function row(it,k){
    if(!it||typeof it!=="object")return null;
    if(it.sep)return r.jsx("div",{className:"svm-menusep"},"s"+k);
    return r.jsxs("button",{className:"svm-menuitem",role:"menuitem",disabled:!!it.off,title:it.lbl,
      onClick:function(){try{it.run&&it.run()}finally{o.onClose&&o.onClose()}},
      children:[r.jsx("span",{children:it.lbl}),r.jsx("span",{className:"svm-menukey",children:it.combo||""})]},k)}
  return r.jsx("div",{className:"svm-pop svm-menu",role:"menu",onClick:function(e){e.stopPropagation()},
    style:{left:Math.max(0,Math.min(px,W-270)),top:Math.max(0,Math.min(py,H-40*n))},
    children:rubs.map(function(g,gi){var its=(g&&Array.isArray(g.items))?g.items:[];
      return r.jsxs("div",{className:"svm-menugrp",children:[
        g&&g.rub?r.jsx("div",{className:"svm-menurub",children:g.rub}):null,its.map(row)]},gi)})})}
/* ── L7 D-10 (24/09/2026) : preset clavier Resolve, export / import du mappage (pur) ──
   Le preset est un dictionnaire d'OVERRIDES {actionId: combo} que l'hôte applique par
   setKmOv (le chemin du panneau « ? »). MESURÉ sur le bundle : « Ctrl+T » et « Ctrl+Maj+T »
   sont réservées au navigateur (SVM_COMBO_RESERVED) — l'action neuve trans_add a pour défaut
   « Alt+T », qui n'a donc rien à faire ici ; Retour arrière est déjà « Suppr » (SVM_EV_NAMES) ;
   « O » est le défaut de toolbar et svmKmMerge ignore un override qui vole la touche d'une
   action NON remappée — le preset déplace donc toolbar sur « Alt+O ». JKL, I : déjà les défauts.
   Le fichier d'échange est {version:1, keymap:{id:combo}} ; l'import est validé ici, avec les
   juges du bundle passés en paramètres (canon, reserved) : jamais recopiés. */
var DZM_KM_PRESETS={resolve:{range_out:"O",toolbar:"Alt+O",blade:"Ctrl+B"}};
function dzmKmPreset(nom){
  if(typeof nom!=="string"||!Object.prototype.hasOwnProperty.call(DZM_KM_PRESETS,nom))return null;
  return Object.assign({},DZM_KM_PRESETS[nom])}
function dzmKmExport(ov){
  var km={};if(ov&&typeof ov==="object"&&!Array.isArray(ov))Object.keys(ov).forEach(function(k){km[k]=ov[k]});
  return JSON.stringify({version:1,keymap:km})}
function dzmKmImport(txt,actions,canon,reserved){
  var d;try{d=JSON.parse(String(txt))}catch(e){return {ok:!1,raison:"json"}}
  if(!d||typeof d!=="object"||d.version!==1||!d.keymap||typeof d.keymap!=="object"||Array.isArray(d.keymap))return {ok:!1,raison:"version"};
  var acts=Array.isArray(actions)?actions:[],ids={};acts.forEach(function(a){if(a&&a.id)ids[a.id]=a.combo});
  var km0={},ign=[];
  Object.keys(d.keymap).forEach(function(id){
    var v=d.keymap[id],c=typeof v==="string"?canon(v):"";
    if(!Object.prototype.hasOwnProperty.call(ids,id))ign.push({id:id,raison:"inconnu"});
    else if(!c)ign.push({id:id,raison:"combo"});
    else if(reserved(c))ign.push({id:id,raison:"reservee"});
    else if(c!==ids[id])km0[id]=c});
  /* revue D-10 : les COLLISIONS, jugées comme svmKmMerge le fera (même ordre : les défauts des
     actions sans override occupent leur touche, puis les overrides en ordre de TABLE) — une ligne
     du fichier qui vole la touche d'une action non remappée, ou la touche d'une ligne déjà
     retenue, est dite {raison:"collision", avec:<id qui garde la touche>} au lieu de retomber
     au défaut en silence. Object.keys(keymap) est exactement ce que la fusion retiendra. */
  var used={},km={};
  acts.forEach(function(a){if(a&&a.id&&!km0[a.id]&&!used[a.combo])used[a.combo]=a.id});
  acts.forEach(function(a){if(!a||!a.id||!km0[a.id])return;var c=km0[a.id];
    if(used[c])ign.push({id:a.id,raison:"collision",avec:used[c]});else{km[a.id]=c;used[c]=a.id}});
  return {ok:!0,keymap:km,ignores:ign}}
/* ── L7 D-6 (24/09/2026) : presse-papiers de clips entre projets (pur) ──
   UN clip : la sélection est simple (selId, B:1707) — écart daté, pas de
   multi-copie. L'hôte range {v:1, at, clip:dzmClipCopy(c)} dans le stockage
   local du navigateur (clé dz_montage_clipboard : survit au changement de
   projet et d'onglet) et colle par dzmClipPaste à la tête, en mode d'édition
   courant. (Aucun nom d'API du navigateur dans ce commentaire, à dessein :
   _corps() du banc lit jusqu'au prochain `var`, et juge la pureté du bloc
   D-10 qui précède.)
   La copie est PROFONDE et sans `id` (l'identifiant est tranché au collage),
   sans `transition`/`transition_s` (une transition appartient à la coupe,
   pas au clip qu'on emporte), sans `src_history` (le journal de remplacement
   reste au projet d'origine) ; `srcOut` suit le clip (fenêtre de source).
   LA PISTE CIBLE : celle du clip si elle existe, sinon la piste du même
   genre au PLUS PETIT rang (v1, a1, t1…). MESURÉ : les pistes arrivent dans
   l'ordre de l'ÉCRAN (DZM_DEFAULT_TRACKS : t1, v3, v2, v1, a1…) — « la
   première du genre » serait V3, une incrustation, pour une vidéo de V9.
   Le genre d'une piste est `kind` s'il est dit, sinon son initiale
   (dzmKindOf) ; le genre du clip vient de son `tr`.
   `srcDur` (durée de la SOURCE) n'est pas connue du presse-papiers —
   addAsset la tient de /duration — : seul « remplir » la lit (vitesse ×1
   à défaut, dzmInsereUn), et l'appelant peut la passer dans `opts`. Les
   refus de dzmInsere (verrou, clips mous) sont RELAYÉS tels quels, la
   phrase française posée ici quand dzmInsere n'en donne pas. */
var DZM_CLIP_NOCOPY=["id","transition","transition_s","src_history"];
function dzmClipCopy(c){
  if(!c||typeof c!=="object"||Array.isArray(c))return null;
  var o={};
  Object.keys(c).forEach(function(k){
    if(DZM_CLIP_NOCOPY.indexOf(k)>=0||c[k]===void 0)return;
    try{o[k]=JSON.parse(JSON.stringify(c[k]))}catch(e){}});
  return o}
function dzmClipPisteCible(tracks,tr){
  var ts=Array.isArray(tracks)?tracks:[],genre=dzmKindOf(tr),i,t,best=null,n;
  /* revue M-2 : la piste homonyme n'est prise que si elle est DU GENRE du
     clip (un « v1 » déclaré kind:"audio" par un projet exotique ne reçoit
     pas une vidéo) — sinon la piste du genre au plus petit rang */
  for(i=0;i<ts.length;i++){t=ts[i];if(t&&t.id!=null&&String(t.id)===String(tr)&&dzmKindOf(t.id,t.kind)===genre)return t.id}
  for(i=0;i<ts.length;i++){t=ts[i];if(!t||t.id==null||dzmKindOf(t.id,t.kind)!==genre)continue;
    n=parseInt(String(t.id).replace(/^\D+/,""),10);if(!isFinite(n))n=1e9;
    if(!best||n<best.n)best={id:t.id,n:n}}
  return best?best.id:null}
function dzmClipPaste(clips,payload,opts){
  var o=opts||{},base=Array.isArray(clips)?clips.slice():[];
  if(!payload||typeof payload!=="object"||!payload.clip||typeof payload.clip!=="object")
    return {clips:base,track:null,mode:null,refus:"vide",note:"Presse-papiers vide — copiez d'abord un clip",id:null,start:null};
  if(payload.v!==1)return {clips:base,track:null,mode:null,refus:"version",note:"Presse-papiers d'une autre version",id:null,start:null};
  /* revue M-3 : la RECOPIE est voulue — le payload (lu du stockage, ou
     tenu par l'appelant) n'est jamais muté : tr/start/end/id sont écrits
     sur la copie, et le presse-papiers reste collable une seconde fois */
  var c=dzmClipCopy(payload.clip),tracks=Array.isArray(o.tracks)?o.tracks:[],genre=dzmKindOf(c.tr);
  /* revue I-2 : un clip SANS source (copié depuis la démo, dont les clips
     n'ont pas de src) ne serait jamais rendu — renderPayload filtre
     `c.src || kind title/adjust` ; on le refuse ici, pas au rendu */
  if(!c.src&&c.kind!=="title"&&c.kind!=="adjust")
    return {clips:base,track:null,mode:null,refus:"source",note:"Ce clip n'a pas de source (copié depuis la démo ?) — rien n'a été collé",id:null,start:null};
  var tr=dzmClipPisteCible(tracks,c.tr);
  if(tr==null)return {clips:base,track:null,mode:null,refus:"piste",note:"Aucune piste "+genre+" pour coller",id:null,start:null};
  var head=Number(o.head);if(!isFinite(head)||head<0)head=0;head=dzmR3(head);
  var len=dzmR3((Number(c.end)||0)-(Number(c.start)||0));
  if(!(len>0))len=dzmR3(Number(DZM_CLIP_DEFAUTS.video)||6);
  c.tr=tr;c.start=head;c.end=dzmR3(head+len);
  c.id=dzmUniqueId(clips,String(tr)+"u"+(o.seq|0)+"_"+Math.round(head*10));
  var r=dzmInsere(clips,c,o.mode||"inserer",{tracks:tracks,head:head,srcDur:o.srcDur,range:o.range,locked:o.locked,twin:o.twin});
  var note=r.note||"";
  if(r.id==null&&!note)note=r.refus==="verrou"?"Piste "+String(r.track||tr).toUpperCase()+" verrouillée — rien n'a été collé":"Rien n'a été collé";
  /* revue M-1 : `start` est la position RÉELLE du clip posé (« en fin »,
     « ripple », « remplir » le posent ailleurs qu'à la tête) — l'hôte la dit */
  var pose=null;if(r.id!=null)for(var q=0;q<r.clips.length;q++)if(r.clips[q]&&r.clips[q].id===r.id){pose=r.clips[q];break}
  return {clips:r.clips,track:r.track||tr,mode:r.mode,refus:r.refus||null,note:note||null,id:r.id,start:pose?Number(pose.start):null}}
/* ── L7 D-8 (24/09/2026) : boring detector (pur) — plans trop longs et jump
   cuts sur V1 ──
   dzmBoring(clips, opts) → { id : "long" | "jump" } sur les clips de V1
   SEULEMENT (les incrustations et l'audio ne sont pas des « plans »).
   `long` : durée > maxS (strict). `jump` : le plan est en CONTACT avec son
   voisin de gauche (la tolérance de dzmVoisins, 0,1 s — réutilisée, pas
   une seconde règle), de la MÊME source, et reprend cette source à moins
   de minFrames images de là où le voisin l'a laissée :
     | srcIn_droit − (srcIn_gauche + len_gauche × vitesse_gauche) | × fps
       < minFrames
   — le même plan repris presque au même point : la coupe « saute ». Le
   jump PRIME sur le long (un seul attribut par clip, le défaut visible
   d'abord). Précisions mesurées : la comparaison se fait EN IMAGES avec un
   epsilon (2.4 − 2 vaut 0.3999… en flottant : AU seuil, ce n'est pas un
   jump) ; la vitesse du plan gauche compte (à ×2, 5 s de timeline
   consomment 10 s de source) ; une IMAGE n'a pas de position de source :
   deux images identiques en contact sont un jump quel que soit srcIn ;
   les options illisibles, nulles ou négatives retombent sur le défaut, et
   DZM_BORING_DEF n'est jamais muté (copie) ; l'ordre d'arrivée des clips
   est indifférent, les clips ne sont pas mutés. L'hôte tient les réglages
   {on, maxS, minFrames} dans le stockage local du navigateur (clé
   dz_svm_boring) et pose data-boring sur .svm-clip ; montage.css dessine
   le liseré (gris pointillé / rouge). (Aucun nom d'API du navigateur dans
   ce commentaire, à dessein : _corps() du banc lit jusqu'au prochain
   `var` et juge la pureté du bloc D-6 qui précède.) */
var DZM_BORING_DEF={maxS:8,minFrames:12,fps:30};
function dzmBoringOpts(opts){
  var o=Object.assign({},DZM_BORING_DEF),k,v;
  if(opts&&typeof opts==="object")for(k in DZM_BORING_DEF){v=Number(opts[k]);if(isFinite(v)&&v>0)o[k]=v}
  return o}
/* la « même source » est celle du jumeau (dzmSrcKey, la clé JSON canonique
   de `src`, déjà exportée `srcKey`) — le plan la redéfinissait, MESURÉ :
   elle existait ; une source vide ({} ou absente) n'a pas de clé */
function dzmBoringKey(c){
  var s=c&&c.src;
  return (s&&typeof s==="object"&&Object.keys(s).length)?dzmSrcKey(s):""}
function dzmBoring(clips,opts){
  var o=dzmBoringOpts(opts),out={};
  if(!Array.isArray(clips))return out;
  var v=clips.filter(function(c){return c&&typeof c==="object"&&c.tr==="v1"&&c.id!=null})
    .sort(function(a,b){return (Number(a.start)||0)-(Number(b.start)||0)});
  v.forEach(function(c){
    var len=(Number(c.end)||0)-(Number(c.start)||0);
    if(len>o.maxS)out[c.id]="long";
    var g=dzmVoisins(v,c).g,k=dzmBoringKey(c);
    if(!g||!k||k!==dzmBoringKey(g))return;
    if(c.src.image&&!c.src.job_id){out[c.id]="jump";return}
    var sp=Number(g.speed);if(!(sp>0))sp=1;
    var fin=(Number(g.srcIn)||0)+((Number(g.end)||0)-(Number(g.start)||0))*sp;
    var ecart=Math.abs((Number(c.srcIn)||0)-fin);
    if(ecart*o.fps<o.minFrames-1e-6)out[c.id]="jump"});
  return out}
/* ── L7 D-39 (24/09/2026) : comparaison de deux projets (pur) ──
   dzmDiff(a, b) sur deux tableaux de clips → {added, removed, moved,
   trimmed, changed, noms}. Identité par `id` (des chaînes). `moved` :
   même durée ET même srcIn, start différent. `trimmed` : durée OU srcIn
   différents — un slip (srcIn seul) est un rognage de la FENÊTRE de
   source, pas un déplacement (la lettre du plan le laissait sans
   rubrique) ; `src:[inA,inB]` s'ajoute quand srcIn a bougé. `changed` :
   les clés de DZM_DIFF_CLES qui diffèrent par leur forme JSON (absent,
   null et undefined se valent ; 0 n'est pas absent) — un clip peut être
   rogné ET modifié, déplacé d'une piste = déplacé ET modifié (tr),
   moved exclut trimmed. `noms` = {id: libellé} (B prime, sinon A, rien
   sans libellé) : la vue n'a pas les clips sous la main — sixième clé,
   écart mesuré au plan (cinq rubriques). Rien n'est muté. Les temps de
   la vue : le m:ss du bundle (svmRuler, réutilisé) + un dixième à la
   virgule quand il y en a un. L'hôte lit l'autre projet, appelle diff
   sur la timeline courante et monte DiffView dans son popover. */
var DZM_DIFF_CLES=["gain","opacity","x","y","scale","rotate","effects","dz","speed","retime","stab","text","transition","transition_s","fade_in","fade_out","label","tr"];
function dzmDiffIndex(clips){
  var m={},ord=[];
  (Array.isArray(clips)?clips:[]).forEach(function(c){
    if(c&&typeof c==="object"&&c.id!=null){var k=String(c.id);if(!(k in m))ord.push(k);m[k]=c}});
  return {m:m,ord:ord}}
function dzmDiff(a,b){
  var ia=dzmDiffIndex(a),ib=dzmDiffIndex(b),out={added:[],removed:[],moved:[],trimmed:[],changed:[],noms:{}};
  function json(v){return JSON.stringify(v===void 0?null:v)}
  ib.ord.forEach(function(id){var c=ib.m[id];if(c.label)out.noms[id]=String(c.label);if(!(id in ia.m))out.added.push(id)});
  ia.ord.forEach(function(id){
    var ca=ia.m[id],cb=ib.m[id];
    if(ca.label&&!out.noms[id])out.noms[id]=String(ca.label);
    if(!cb){out.removed.push(id);return}
    var sa=Number(ca.start)||0,ea=Number(ca.end)||0,sb=Number(cb.start)||0,eb=Number(cb.end)||0;
    var na=Number(ca.srcIn)||0,nb=Number(cb.srcIn)||0,la=ea-sa,lb=eb-sb;
    if(Math.abs(la-lb)>1e-6||na!==nb){
      var t={id:id,de:[sa,ea],en:[sb,eb]};if(na!==nb)t.src=[na,nb];out.trimmed.push(t)}
    else if(sa!==sb)out.moved.push({id:id,de:sa,en:sb});
    var cles=DZM_DIFF_CLES.filter(function(k){return json(ca[k])!==json(cb[k])});
    if(cles.length)out.changed.push({id:id,cles:cles})});
  return out}
function dzmDiffTemps(v){
  v=Number(v);if(!(v>0))v=0;
  var s=Math.floor(v),d=Math.round((v-s)*10);if(d>=10){s+=1;d=0}
  return svmRuler(s)+(d?","+d:"")}
var DZM_DIFF_RUB=[["added","Ajouté","Ajoutés"],["removed","Supprimé","Supprimés"],["moved","Déplacé","Déplacés"],
  ["trimmed","Rogné","Rognés"],["changed","Modifié","Modifiés"]];
/* la vue : un svm-pop (le voile et Échap sont ceux de l'hôte), un résumé, cinq rubriques data-rub, « Fermer » */
function DzmDiffView(o){
  o=o||{};var d=o.diff||{},noms=d.noms||{};
  function nom(id){return noms[id]||String(id)}
  function n(k){return Array.isArray(d[k])?d[k].length:0}
  function ligne(k,e){
    if(k==="moved")return nom(e.id)+" : "+dzmDiffTemps(e.de)+" → "+dzmDiffTemps(e.en);
    if(k==="trimmed")return nom(e.id)+" : "+dzmDiffTemps(e.de[0])+"–"+dzmDiffTemps(e.de[1])+" → "+dzmDiffTemps(e.en[0])+"–"+dzmDiffTemps(e.en[1])+(e.src?" (source "+dzmDiffTemps(e.src[0])+" → "+dzmDiffTemps(e.src[1])+")":"");
    if(k==="changed")return nom(e.id)+" : "+(e.cles||[]).join(", ");
    return nom(e)}
  var res=DZM_DIFF_RUB.map(function(rb){var c=n(rb[0]);return c+" "+(c>1?rb[2]:rb[1]).toLowerCase()}).join(" · ");
  return r.jsxs("div",{className:"svm-pop dzm-diff",onClick:function(e){e.stopPropagation()},children:[
    r.jsx("div",{className:"svm-poptitle",children:"Comparer : « "+(o.nomA||"montage courant")+" » → « "+(o.nomB||"autre projet")+" »"}),
    r.jsx("div",{className:"svm-popnote dzm-diffres",children:res})].concat(DZM_DIFF_RUB.map(function(rb){
      var k=rb[0],items=Array.isArray(d[k])?d[k]:[];
      return r.jsxs("div",{className:"dzm-diffrub","data-rub":k,children:[
        r.jsx("div",{className:"dzm-diffh",children:rb[2]+" ("+items.length+")"}),
        r.jsx("ul",{className:"dzm-difflist",children:items.length
          ?items.map(function(e,i){return r.jsx("li",{children:ligne(k,e)},k+i)})
          :[r.jsx("li",{className:"dzm-diffnone",children:"—"},"none")]})]},k)}),[
    r.jsx("div",{className:"svm-poprow",children:
      r.jsx("button",{className:"svm-secbtn",title:"Fermer la comparaison (Échap)",onClick:function(){if(o.onClose)o.onClose()},children:"Fermer"})},"fin")])})}
var DzTracks={ready:!0,TrackAdd:DzmTrackAdd,headBtns:dzmHeadBtns,
  WordAnimChip:DzmWordAnimChip,EmojiBtn:DzmEmojiBtn,
  TextDrawer:DzmTextDrawer,rippleCut:dzmRippleCut,cutOpts:dzmCutOpts,withWords:dzmWithWords,
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
  subsTrDefaut:dzmSubsTrDefaut,subsTrBody:dzmSubsTrBody,
  subsTrEnabled:dzmSubsTrEnabled,subsTrLabel:dzmSubsTrLabel,
  subsTrTitle:dzmSubsTrTitle,subsTrNote:dzmSubsTrNote,
  subsTrApply:dzmSubsTrApply,
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
  histSnap:dzmHistSnap,histApply:dzmHistApply,HIST_CLES:DZM_HIST_CLES,
  rangeSet:dzmRangeSet,rangeFrom:dzmRangeFrom,rangeLen:dzmRangeLen,
  RangeBar:DzmRangeBar,
  markerAdd:dzmMarkerAdd,markerRemove:dzmMarkerRemove,
  markerUpdate:dzmMarkerUpdate,markerNext:dzmMarkerNext,
  markersFrom:dzmMarkersFrom,MARKER_COLORS:DZM_MARKER_COLORS,
  Markers:DzmMarkers,MarkerIndex:DzmMarkerIndex,
  veil:dzmVeil,VEIL:Object.freeze(DZM_VEIL),
  /* D-21 — `group`, `pickTrack` et `remove` sont DÉJÀ au contrat (P9, P14) :
     rien n'est ré-exporté sous un second nom, une clé de plus aurait été une
     seconde porte sur la même fonction. */
  titleTrack:dzmTitleTrack,titleNew:dzmTitleNew,
  /* D-9 — `kindOf` entre au contrat : c'est la table des genres elle-même
     (aucune autre porte n'y menait, le banc [18] la lit). */
  kindOf:dzmKindOf,adjustTrack:dzmAdjustTrack,adjustNew:dzmAdjustNew,
  titleAt:dzmTitleAt,titleHtml:dzmTitleHtml,ttEsc:dzmTtEsc,
  titleUpdate:dzmTitleUpdate,TitleInspector:DzmTitleInspector,
  transList:dzmTransList,transLabel:dzmTransLabel,transFamily:dzmTransFamily,
  transLive:dzmTransLive,transDir:dzmTransDir,TransGrid:DzmTransGrid,
  TRANS_FAM:DZM_TRANS_FAM,TRANS_DIR:DZM_TRANS_DIR,TRANS_TT:DZM_TRANS_TT,
  insere:dzmInsere,MODES:DZM_MODES,REFUS:DZM_REFUS,carve:dzmCarve,
  slip:dzmSlip,slide:dzmSlide,roll:dzmRoll,voisins:dzmVoisins,swap:dzmSwap,
  ModeBar:DzmModeBar,MODE_T:DZM_MODE_T,modeLabel:dzmModeLabel,
  projetNeuf:dzmProjetNeuf,instantaneNom:dzmInstantaneNom,
  channelsNorm:dzmChannelsNorm,publishLocal:dzmPublishLocal,publishIso:dzmPublishIso,
  publishDefaults:dzmPublishDefaults,FinBandeau:DzmFinBandeau,CHANNELS:DZM_CHANNELS,
  dzNorm:dzmDzNorm,dzOf:dzmDzOf,dzAt:dzmDzAt,dzPreset:dzmDzPreset,dzMove:dzmDzMove,
  dzScale:dzmDzScale,dzCss:dzmDzCss,PlanProps:DzmPlanProps,DzRects:DzmDzRects,
  retimeOf:dzmRetimeOf,rampe:dzmRampe,
  stabNorm:dzmStabNorm,stabOf:dzmStabOf,stabState:dzmStabState,
  mpLerp2:dzmMpLerp2,mpKeep:dzmMpKeep,
  /* E-2 (lot E-B, 23/09/2026) : provenance, filtre et tiroir Medias */
  provGroupe:dzmProvGroupe,provChips:dzmProvChips,mediaFiltre:dzmMediaFiltre,MediaDrawer:DzmMediaDrawer,
  /* E-5 (lot E-B, tache 4) : le dernier rendu final par projet */
  finStore:dzmFinStore,finOf:dzmFinOf,
  /* E-8 (lot E-B, tache 6) : la largeur de l'inspecteur bornee */
  clamp:dzmClamp,inspW:dzmInspW,
  /* E-9 (lot E-B, tache 7) : la hauteur de la timeline bornee, la duree sur le label */
  tlH:dzmTlH,durLbl:dzmDurLbl,
  /* D-7 (lot E-B, tache 8) : la mini-carte -- geometrie pure et composant */
  minimap:dzmMinimap,Minimap:DzmMinimap,
  /* E-6 (lot E-C, tache 1) : combo -> touche, modele de menu, composant de menu */
  comboToKey:dzmComboToKey,menuModel:dzmMenuModel,CtxMenu:DzmCtxMenu,
  /* E-7 (lot E-C, tache 3) : le tri des rendus par titre et la vue Livraison */
  jobsTri:dzmJobsTri,Deliver:DzmDeliver,
  /* L4 (23/09/2026) : reglages de livraison -- pastille, options, payload, statut, rangee */
  loudPastille:dzmLoudPastille,deliverOpts:dzmDeliverOpts,deliverPayload:dzmDeliverPayload,delStatut:dzmDelStatut,DeliverRow:DzmDeliverRow,
  kmPreset:dzmKmPreset,kmExport:dzmKmExport,kmImport:dzmKmImport,
  clipCopy:dzmClipCopy,clipPaste:dzmClipPaste,
  boring:dzmBoring,boringDef:DZM_BORING_DEF,
  diff:dzmDiff,DiffView:DzmDiffView,diffTemps:dzmDiffTemps,
  /* E-13 / E-14 (lot E-C, tache 5) : la tete dans l'inspecteur, le trou selectionne et son ripple */
  teteTxt:dzmTeteTxt,trou:dzmTrou,trouRipple:dzmTrouRipple,
  DEFAULTS:DZM_DEFAULT_TRACKS};
window.DzTracks=DzTracks;
