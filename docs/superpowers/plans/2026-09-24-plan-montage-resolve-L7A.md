# Lot L7-A du Montage — confort — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** livrer la moitié « client, gratuite, pure » du lot L7 de `docs/superpowers/specs/2026-09-21-montage-vs-resolve-design.md` (l.178) : D-10 preset clavier Resolve + export/import du mappage (l.52), D-6 presse-papiers de clips entre projets (l.47), D-8 boring detector (l.49), D-39 comparaison de deux projets (l.126), D-3b trim A/B ±1 image à la jonction (l.43), D-19 coins arrondis et ombre sur un overlay (l.67), D-22 pistes de sous-titres par langue, une seule gravée (l.75). Le reste du L7 (D-37 EDL/FCPXML, D-40 recadrage, D-41 auto-clips, D-42 scdet, D-34 notes ★ Bibliothèque) forme le lot **L7-B**, à planifier après.

**Architecture :** tout ce qui est décidable est une fonction PURE de la couche `frontend/patches/montage.js` (bancée sous node par `test_montage_edition.py`), câblée dans le bundle par des sections du patcher `scripts/patch_bundle_montage.py` (préfixe **`L7`**) ; le backend ne change que pour D-19 (deux champs d'overlay dans `_build_montage_command`) et D-22 (rien : la gravure reste un seul objet `subtitles`, le client n'envoie que la piste marquée gravée).

**Tech :** bundle patché en octets, couche JS plate, FastAPI/ffmpeg 8.1.1 pour D-19, bancs python embarqué, Playwright pour les preuves.

---

## Conventions valables pour tout le plan

```powershell
$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"
Set-Location backend
& $PY tests\test_montage_l7.py             # NEUF (T5 D-19 backend)
& $PY tests\test_montage_edition.py        # 294/0 au départ
& $PY tests\test_montage_bundle.py         # 2092/0
& $PY tests\test_montage_ergonomie.py      # 36/0
& $PY tests\test_montage_l4.py             # 120/0
& $PY tests\test_montage_l3.py             # 86/0
& $PY tests\test_montage_l2.py             # 78/0
& $PY tests\test_subtitles_burn.py ; & $PY tests\test_subs_traduction.py ; & $PY tests\test_montage_pistes_dyn.py
& $PY tests\test_hygiene_imports.py
Set-Location ..
& $PY scripts\patch_bundle_montage.py --check --force-unchained   # 171 ancres au départ
& $PY scripts\repatch_all.py --from montage ; & $PY scripts\repatch_all.py --list
node --check frontend\dist\assets\index-BEOJX8L5.js ; node --check frontend\patches\montage.js
```

- Un banc = un processus, jamais `pytest`. `check(label, cond, detail)`, `=== N passed, M failed ===`, code de sortie. Règle des assertions négatives (témoin positif dans la même expression), état vide construit (shim sur fichier vide : les clés de section listées dans `vide_cles`, `test_montage_edition.py:1109`), faute n°6 (aucune lecture nue, détail évalué avant le court-circuit).
- Ancres comptées sur `.bak_montage` (1/0/1 : une fois dans `.bak`, zéro fois dans le patcher hors section, une fois dans le bundle) ; ancre consommée → repli dans le remplacement hôte ; sections en queue après `L4d4`. `.bak_dzcout` plus récent ⇒ toujours `repatch_all --from montage`. Bundle en OCTETS (CRLF, mesuré : 20 447 lignes) ; après rejeu : `--list`, `node --check`, CRLF == LF, `git hash-object`, sonde `("montage","DzTracks",135)` de `scripts/patch_bundle_dzcout.py` remesurée et justifiée ligne à ligne. `localStorage` clés `dz_*` en try/catch. Composants de la couche lisent `r`/`x` à l'APPEL, jamais au chargement (cœur pur sans `r.jsx`, `x.use`, `localStorage`, `window`, `document`, `fetch(` : vérifié par `_corps()`).
- Commits `--only`, première ligne sans accent `montage : D-xx - <quoi>`, trailer EXACT `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`, push de `chantier/montage-l7`. Pas de heredoc bash pour du code (le Bash de la session désescape `\n`) : Write/Edit. Jamais `git checkout --`/`stash`. Chaque agent CONTESTE le plan si la mesure le contredit (écart daté dans la conception à la clôture).
- Preuves à l'écran par le contrôleur (backend du worktree sur 8799 via `.claude/launch.json` recréé par `mk_launch.py`, projet « preuve e3 », Playwright + Chrome).

## Faits mesurés le 24/09/2026 (relevé lecture seule, état af413ed)

**Keymap** (bundle B) : `var SVM_ACTIONS=[…]` B:1522-1570, 45 entrées `{id,sec,lbl,combo}` ; `SVM_ACTION_BY_ID`, `SVM_KEY_SECTIONS=["Lecture","Montage","Affichage","Audio"]` B:1571-1573 ; `svmComboOfEvent` B:1597, `svmComboCanon` B:1620, `SVM_COMBO_RESERVED`/`svmComboReserved` B:1640-1650 ; stockage `dz_svm_keymap` = JSON `{actionId: combo}` des seuls overrides (`svmKmLoad` B:1653 filtre id connu, combo canonisable, non réservée, ≠ défaut ; `svmKmSave(ov)` B:1665, objet vide ⇒ `removeItem`) ; `svmKmMerge(ov)` B:1675 → `{byId,toAct}`, collision ⇒ retour au défaut ; état hôte `kmOv/setKmOv` B:1992-2001 ; `onKey` B:3369 ; panneau `kbPanel()` B:5090 avec « Réinitialiser tout » B:5165-5180. **Aucun import/export, aucun preset.** Défauts utiles : `jog_back J`, `jog_pause K`, `jog_fwd L`, `range_in I`, `range_out U`, `range_clear X`, `blade Alt+C`, `undo Ctrl+Z`, `redo Ctrl+Y`, `delete Suppr`, `nudge_left/right Alt+←/→`. Le menu ☰ rejoue une action par `dzFire(id)` B:2147 (KeyboardEvent synthétique via `DzTracks.comboToKey`), modèle `dzmMenuModel(SVM_ACTIONS, svmKeyLabel)` M:6792, rubriques `DZM_MENU_RUB` M:6775-6784.
**Sélection/historique** : UN clip (`selId` B:1707, `sel` B:2467, pas de multi-sélection) ; `pushHistory()` AVANT `setClips(next)` (B:2082, `delClipById` B:2123-2138 en modèle) ; `histRef={u,r}`, `DZM_HIST_CLES=["tracks","dur","subsStyle","range","markers"]` M:4776. Ajout : `addAsset(src,label,kind,srcDur,trId,atTime)` B:4281, id `DzTracks.uniqueId(clips, tr+"u"+seq+"_"+round(st*10))` B:4406-4431, `ovSeq.current` ; `dzmInsere(clips,clip,mode,opts)` M:5033 → `{clips,track,mode,refus,note,id}`, `DZM_MODES` M:4936 ; `dzmUniqueId` M:2848, `dzmDedupeIds` M:2856, `dzmSeqMax` M:2870. Clip : `{id,tr,label,start,end,srcIn,src:{job_id|image|audio},transition,transition_s,gain,fade_*,volume_points,x,y,scale,rotate,opacity,motion_points,effects,dz,speed,retime,stab,text,narr,hidden,kind,srcOut,src_history}`.
**Projets** : `GET /api/montage/projects` → `{ok,projects:[{id,name,updated_at,clips,ratio,duration}]}` (MS:2301) ; `GET /projects/{pid}` MS:2378 rend le record `{name,ratio,duration,mix,clips,tracks?,range?,markers?,…}` ; `DzmProjects` M:1370-1740 (`load()` M:1471, `ouvrir()` M:1559), monté B:6307 ; `svmApplyProject` B:2241 ; autosave `svmDoSave` B:2362.
**Timeline** : `.svm-clip` B:6463 avec `data-cid`, `data-warn` (`"warn"|"err"`), `data-hidden`, `data-nosub`, `data-kind`, `data-locked`, `data-narr` ; sélection par style en ligne (pas de `data-sel`) ; CSS `frontend/dist/shared/son-vfx-montage.css:352,615,620,791` (INTOUCHABLE : on n'écrit que dans `montage.css`). Popovers = `div.svm-pop` pilotés par `pop/setPop`, voile `svm-modescrim` B:5791, Échap B:3405 ; panneau dépliable modèle `duckOpen?duckPanel():null` B:6135-6139 ; chips `svm-themechip` B:5752-5770 (`dz_svm_showdur`).
**Jonction** : losange `.svm-junc` B:6602 → `openTransPop(rightId,e)` ; `transPopover()` B:5193-5223 (`svm-pop svm-transpop`, `DzTracks.TransGrid`, curseur 0.1-1 s, « Appliquer à toutes les coupes ») ; `dzmRoll(clips,leftId,rightId,ds)` M:5193 (borne `-(lenL-.3)..lenR-.3`), `dzmVoisins` M:5149 ; vignettes client `svmThumb(src,sec,cb)` B:1364-1398 (`<video>` hors écran → dataURL JPEG 78×44, clé `"source@seconde"`) ; `nudge_left/right` B:3863-3880 DÉPLACE le clip (`Math.round(ns*3000)/3000`, 30 i/s en dur) ; **aucune route `/frame`**, `/strip` (MS:4575) = n vignettes uniformes sans temps.
**Overlays** : `_ov_transform(c)` MS:962-990 (`x/y −0.5..1.5, scale 0.05..3, rotate ±180`) ; chaîne avec transformation MS:2967 `och=f"scale={ow2}:-2,setsar=1,fps={fps},format=rgba"` puis opacité (`colorchannelmixer=aa=`) MS:2968-2979, rotation MS:2991-3008, `setpts` MS:3009, `overlay=…eof_action=pass:enable='between(t,st,en)'` MS:3010-3024 ; chaîne « cover » sans transformation MS:2914-2921 (`yuva420p`) ; échelle animée MS:2963-2983 (`pad`+`zoompan`). Payload MS:3961-3970 `"opacity","tf","mp","layer"`. Inspecteur `ovInspector()` B:4801-4900 (`fieldNum`, `svmOvTfField(patch)` B:3090, `svmOvTfOf` B:1458, `svmApplyTf` B:1469) ; `renderPayload` B:4644-4667 n'émet `x/y/scale/rotate` que si non triviaux. Bancs D-14 dans `test_montage_l3.py:630-822`.
**Sous-titres** : piste `{id:"s1",kind:"subs"}` M:168-185 (`_CLIENT_DEFAULT_TRACKS` MS:554-559), genre par initiale `dzmKindOf` M:234-237 (`"s"→"subs"`) et `trackKind` (section TT1) ; segments = CLIPS `{id:"s1c…",tr:"s1",start,end,label,text,words?,hidden?}` (`frontend/patches/subs.js:99-111`, inliné dans le bundle : on ne le modifie que par sections) ; **`"s1"` en dur** dans `subsSegsOf` B:4053, `subsCommit` B:4070-4080 (verrou `trackStRef.current.s1.l`), `subsAddHere` B:4081, `subsPayload()` B:4129-4140 → `{style,segments}` ou `void 0`, `data-sub:tr.id==="s1"` B:6396, `dzmRemove` M:397-400 (s1 non supprimable), `DzmTrackBtns` M:807, `dzmSubsAt` M:393 (première piste subs). Traduction `dzTraduire()` (section M26a) → `POST /subtitles/translate` `{segments,target,source?}` → `{segments}` mêmes temps, puis `subsTrApply` + `onChange(dzNext,!0)` ⇒ **écrase S1**. Export local `subsToSrt/Vtt/Txt` (subs.js:1133-1147) + `subsDownload`. Gravure : `_subs_ass(body["subtitles"],(w,h),stem)` MS:3360 → UN chemin, dernier maillon de `_deliver_tail`. Tête de piste B:6340-6412 : `thLock` pour toutes, rangée `svm-ttyperow [thType,thLock,thAdd]` B:6410 (88 px, serrée), `DzTracks.headBtns` ; `svmTracksPayload` M:283-285 n'émet que `id,kind,bus,loop,type`. Menu contextuel de piste = section EC5.

### Décisions prises sur les démentis

1. **Preset Resolve** (D-10) = un dictionnaire d'overrides `{range_out:"O", blade:"Ctrl+B", trans_add:"Ctrl+T", delete:"Backspace"…}` appliqué par `setKmOv` (même chemin que le panneau ; JKL et I sont déjà les défauts). **Ctrl+T transition** exige une action NEUVE `trans_add` (section Montage, défaut « Ctrl+T », libellé « Transition par défaut à la coupe ») : pose `fade` 0.4 s sur le clip sélectionné de V1 (son bord gauche) via `svmSetTransType(sel.id,"fade")` existant. Export/import = fichier JSON `{version:1, keymap:{id:combo}}` validé par `dzmKmImport(json, actions, canon, reserved)` pur (ids inconnus / combos réservées / non canonisables ignorés, compte rendu) ; export = `dzmKmExport(ov)`.
2. **Presse-papiers** (D-6) : un seul clip (la sélection est simple — écart daté : pas de multi-copie) ; `Ctrl+C` = action `copy` → `localStorage dz_montage_clipboard` = `{v:1, at:<iso>, clip:dzmClipCopy(clip)}` (copie sans `id`, sans `transition`, sans `src_history`, `srcOut` conservé) ; `Ctrl+V` = action `paste` → `dzmClipPaste(clips, payload, {head, tracks, mode:"inserer"|dzModeRef, srcDur, range, locked, seq})` pur qui choisit la piste : même `tr` si elle existe et de même genre, sinon la première piste de ce genre, id par `dzmUniqueId(clips, tr+"u"+seq+"_"+round(head*10))`, insertion par `dzmInsere` en mode courant ; refus dits par `DZM_REFUS`. Le presse-papiers survit au changement de projet (localStorage) ; les combos `Ctrl+C`/`Ctrl+V` ne sont pas réservées (à MESURER dans `SVM_COMBO_RESERVED` — si réservées, écart : `Ctrl+Maj+C/V`).
3. **Boring detector** (D-8) : `dzmBoring(clips, opts={maxS:8, minFrames:12, fps:30})` pur → `{ [id]: "long"|"jump" }` sur V1 : `long` si `end-start > maxS` ; `jump` si deux clips V1 en CONTACT (tolérance `dzmVoisins`) ont la même source (`src.job_id`/`image`) et `|srcIn_droit − (srcIn_gauche + len_gauche)| < minFrames/fps` (jump cut : même plan repris presque au même point). Rendu : `data-boring="long"|"jump"` sur `.svm-clip` (V1 seulement) + règles dans `montage.css` (liseré gris pointillé / rouge) ; réglages `{on,maxS,minFrames}` dans `localStorage dz_svm_boring`, popover « Plans trop longs / jump cuts » ouvert depuis ☰ › Affichage (entrée neuve `boring`, modèle « Durées sur les clips »), champs `fieldNum`.
4. **Diff de projets** (D-39) : `dzmDiff(a, b)` pur sur deux tableaux de clips → `{added:[…], removed:[…], moved:[{id,de,en}], trimmed:[{id,de,en}], changed:[{id,cles:[…]}]}` ; identité = `id` ; `moved` = même `tr`/durée, `start` différent ; `trimmed` = `start`/`end`/`srcIn` changés avec durée différente ; `changed` = autres clés (`gain,opacity,x,y,scale,rotate,effects,dz,speed,retime,stab,text,transition,transition_s`) comparées par `JSON.stringify` ; `DzmDiffView({diff, nomA, nomB, onClose})` liste lisible. Entrée : bouton « ⇄ comparer » sur chaque ligne de `DzmProjects` (autre que le courant) → `GET /api/montage/projects/{pid}` → `dzmDiff(courant.clips, autre.clips)` → panneau `svm-pop dzm-diff`. Aucune route neuve.
5. **Trim A/B** (D-3b) : le popover de jonction gagne une rangée `svm-abrow` : vignette A = `svmThumb(srcGauche, srcIn_g + len_g − 1/30)` (dernière image), vignette B = `svmThumb(srcDroit, srcIn_d)` (première image), compteur « A −1 ◀ ▶ +1 » qui appelle `DzTracks.roll(clips, leftId, rightId, ±1/30)` (pushHistory avant, `setClips`, `setDirty`) — les vignettes se recalculent (clé `source@seconde` arrondie au 1/30) ; Maj = ±10 images. `svmThumb` est client : pas de route `/frame` (écart daté : vignettes au 1/30 s près, dépend du décodeur du navigateur). Les deux clips doivent être des vidéos (`src.job_id`) ; sinon rangée absente.
6. **PIP** (D-19) : deux champs d'overlay `radius` (px, 0..200, entier) et `shadow` (0|1) validés dans `_ov_transform` (clé `"radius"`/`"shadow"` dans `spec`, défaut 0) ; dans la chaîne AVEC transformation seulement, entre l'opacité et la rotation (MS:2979→2991) : coins = `geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*(1-gt(hypot(max(abs(X-W/2)-(W/2-{R}),0),max(abs(Y-H/2)-(H/2-{R}),0)),{R}))'` (R borné à `min(R, w/2, h/2)` sur la taille RÉELLE `ow2` : la hauteur est inconnue avant `scale=-2` → utiliser `min(R,W/2,H/2)` DANS l'expression) ; ombre = `split[o][s];[s]colorchannelmixer=rr=0:gg=0:bb=0:aa=0.5,boxblur=8[sb];[sb][o]overlay=x=-8:y=-8` — NON : l'ombre doit être SOUS l'image et décalée : `[o]pad=iw+16:ih+16:8:8:color=black@0[op];[s]colorchannelmixer=rr=0:gg=0:bb=0:aa=0.55,boxblur=6,pad=iw+16:ih+16:14:14:color=black@0[sp];[sp][op]overlay=0:0`. La chaîne est ajoutée comme labels intermédiaires dans `parts` (le maillon `[idx:v]{och}[ov{j}]` devient trois maillons quand `shadow`). Écart daté : ni `radius` ni `shadow` sur la chaîne « cover » ni sur l'échelle animée (D-14) — ignorés avec warning. Client : deux champs dans `ovInspector` (« Coins » 0-200, case « Ombre »), lus par `svmOvTfOf`, écrits par `svmOvTfField`, émis par `renderPayload` (`o.radius` si > 0, `o.shadow` si 1), aperçu vivant : `border-radius` et `box-shadow` sur l'élément d'overlay dans `svmApplyTf`.
7. **Pistes de sous-titres par langue** (D-22), périmètre minimal et daté : une piste S2… est une COPIE TRADUITE de S1 (créée par « Traduire vers → nouvelle piste ») ou une copie vide ; ses segments sont des clips `tr:"s2"` ; l'ÉDITEUR (DzSubs.Drawer) reste sur S1 (écart daté : S2 s'édite par retraduction/import, pas dans le tiroir) ; la piste `subs` marquée `burn:true` (une seule, bascule « œil » dans le menu contextuel de piste EC5 : « Graver cette piste (langue) », et `data-burn` sur `.svm-track`) est celle que `subsPayload()` envoie ; export .srt/.vtt/.txt de CHAQUE piste subs par le même menu (fonctions locales `subsToSrt` etc. appliquées aux clips `tr===piste`). Cœur pur : `dzmSubsTracks(tracks)`, `dzmSubsBurn(tracks, id)` (une seule gravée, s1 par défaut), `dzmSubsNew(tracks, lang)` (id `s<n>`, `name:"S<n> "+lang`, `kind:"subs"`, `lang`), `dzmSubsCopy(clips, deTr, versTr, segments?)` (clips `tr` retagués, ids `s<n>c…` uniques). Backend : `_tracks_meta` accepte déjà tout `kind` ; `svmTracksPayload` émet aussi `lang` et `burn`. Sections à paramétrer : `subsPayload()` (filtre `c.tr===burnId`), `data-sub` (`trackKind(tr.id)==="subs"`), `dzmRemove`/`DzmTrackBtns` (s1 seule protégée, s2… supprimables), M26a (`dzTraduire` gagne une cible « nouvelle piste »).

## Fichiers

- Modifier `frontend/patches/montage.js` : blocs L7 (D-10 `dzmKmPreset/Export/Import`, D-6 `dzmClipCopy/Paste`, D-8 `dzmBoring`, D-39 `dzmDiff` + `DzmDiffView`, D-22 `dzmSubsTracks/Burn/New/Copy`), exports `kmPreset, kmExport, kmImport, clipCopy, clipPaste, boring, diff, DiffView, subsTracks, subsBurn, subsNew, subsCopy`.
- Modifier `scripts/patch_bundle_montage.py` : sections `L7a…` (une par tâche, ancres 1/0/1 ou replis).
- Modifier `frontend/dist/shared/montage.css` : `[data-boring]`, `.svm-abrow`, `.dzm-diff`, `[data-burn]`.
- Modifier `backend/app/services/montage_service.py` : D-19 (`_ov_transform`, chaîne overlay).
- Créer `backend/tests/test_montage_l7.py` (D-19 backend + rendu réel), sections `[25]…[30]` dans `test_montage_edition.py`, `[L7]` dans `test_montage_bundle.py`.
- Clôture : `backend/tests/mutations_montage_l7.py`, `test_montage_l7_croise.py`, conception datée.

---

## Tâche 1 — D-10 preset Resolve, export/import du mappage, action `trans_add`

**Fichiers :** `frontend/patches/montage.js` (bloc `/* ── L7 D-10 ── */` avant `var DzTracks=`), `scripts/patch_bundle_montage.py` (sections `L7a1` action neuve dans `SVM_ACTIONS`, `L7a2` dispatch de `trans_add` dans `onKey`, `L7a3` trois boutons dans `kbPanel`), `backend/tests/test_montage_edition.py` section `[25]`, `backend/tests/test_montage_bundle.py` section `[L7] D-10`.

- [ ] **Étape 1 — banc rouge (édition [25])** : dans `PROBE`, après la section [24] :

```js
/* ── [25] L7 D-10 : preset Resolve, export/import du mappage ── */
out.kp_resolve=T.kmPreset("resolve");
out.kp_inconnu=T.kmPreset("avid");
out.kx=T.kmExport({blade:"Ctrl+B"});
out.ki_ok=T.kmImport('{"version":1,"keymap":{"blade":"Ctrl+B","zzz":"Q","undo":"Espace"}}',
  [{id:"blade",combo:"Alt+C"},{id:"undo",combo:"Ctrl+Z"}], function(s){return s==="Q"?null:s;}, function(s){return s==="Espace";});
out.ki_casse=T.kmImport("{pas du json", [], function(s){return s;}, function(){return false;});
out.ki_v2=T.kmImport('{"version":2,"keymap":{}}', [], function(s){return s;}, function(){return false;});
```

Section Python `[25]` : `kp_resolve` est un objet avec EXACTEMENT `{range_out:"O", blade:"Ctrl+B", trans_add:"Ctrl+T", delete:"Backspace"}` (et rien d'autre : `Object.keys` == 4) ; `kp_inconnu` est `null` ; `kx` est une chaîne JSON dont le parse rend `{version:1, keymap:{blade:"Ctrl+B"}}` ; `ki_ok` = `{ok:true, keymap:{blade:"Ctrl+B"}, ignores:[{id:"zzz",raison:"inconnu"},{id:"undo",raison:"reservee"}]}` (l'ordre des ignorés suit l'ordre du fichier) ; `ki_casse` = `{ok:false, raison:"json"}` ; `ki_v2` = `{ok:false, raison:"version"}`. Ajouter les six clés à `vide_cles`. Lancer : `=== … 6 failed ===` (les six clés absentes).

- [ ] **Étape 2 — cœur pur** dans `montage.js` :

```js
/* ── L7 D-10 : preset clavier Resolve, export/import du mappage (pur) ── */
var DZM_KM_PRESETS={resolve:{range_out:"O",blade:"Ctrl+B",trans_add:"Ctrl+T","delete":"Backspace"}};
function dzmKmPreset(nom){var p=DZM_KM_PRESETS[nom];return p?Object.assign({},p):null}
function dzmKmExport(ov){return JSON.stringify({version:1,keymap:Object.assign({},ov||{})})}
function dzmKmImport(txt,actions,canon,reserved){
  var d;try{d=JSON.parse(String(txt))}catch(e){return {ok:false,raison:"json"}}
  if(!d||d.version!==1||!d.keymap||typeof d.keymap!=="object")return {ok:false,raison:"version"};
  var ids={};(actions||[]).forEach(function(a){ids[a.id]=a.combo});
  var km={},ign=[];
  Object.keys(d.keymap).forEach(function(id){
    var c=canon(String(d.keymap[id]||""));
    if(!(id in ids))ign.push({id:id,raison:"inconnu"});
    else if(!c)ign.push({id:id,raison:"combo"});
    else if(reserved(c))ign.push({id:id,raison:"reservee"});
    else if(c!==ids[id])km[id]=c});
  return {ok:true,keymap:km,ignores:ign}}
```

Exports : `kmPreset:dzmKmPreset,kmExport:dzmKmExport,kmImport:dzmKmImport,`. Banc : `=== … 0 failed ===`, `_corps("dzmKmImport")` pur, exports ×1 dans `_DT`.

- [ ] **Étape 3 — bundle** (`patch_bundle_montage.py`, après `L4d4`) :
  - `L7a1` : ancre = la ligne EXACTE de l'entrée `adjust_add` de `SVM_ACTIONS` (mesurer B:~1553, 1/0/1) → même ligne + `{id:"trans_add",sec:"Montage",lbl:"Transition par défaut à la coupe",combo:"Ctrl+T"},` (vérifier d'abord que « Ctrl+T » n'est pas dans `SVM_COMBO_RESERVED`, sinon « Ctrl+Maj+T » et écart daté).
  - `L7a2` : dans `onKey`, ancre = la branche `adjust_add` (mesurer) → ajouter `if(act==="trans_add"){var sc=clipsRef.current.find(function(c){return c.id===selRef.current&&c.tr==="v1"});if(sc){svmSetTransType(sc.id,"fade")}e.preventDefault();return}` (utiliser les noms RÉELS de `onKey` : mesurer la variable d'action et le style des autres branches ; `svmSetTransType(id,type)` existe B:~5200, mesurer sa signature).
  - `L7a3` : dans `kbPanel()`, ancre = le bouton « Réinitialiser tout » (B:5165-5180, 1/0/1) → trois boutons `svm-secbtn` AVANT : « Preset Resolve » (`setKmOv(DzTracks.kmPreset("resolve"))` + `svmKmSave` ; message `kbMsg` « Preset Resolve appliqué : O, Ctrl+B, Ctrl+T, Retour arrière »), « Exporter… » (blob `application/json` téléchargé `deepotus-raccourcis.json` via un `<a download>` créé/révoqué à 2 s), « Importer… » (`<input type=file accept=.json>` caché ; `FileReader` → `DzTracks.kmImport(txt,SVM_ACTIONS,svmComboCanon,svmComboReserved)` ; ok → `setKmOv(r.keymap)` + `svmKmSave(r.keymap)` + message « n raccourcis importés, m ignorés » ; sinon message « Fichier illisible » / « Version inconnue »). Tous avec `title` (E-12).
  - Banc bundle `[L7] D-10` : noms neufs ×0 dans `.bak`/≥1 dans `s`, ancres/remplacements 1/0/1, `s.count('id:"trans_add"')==1`, `SVM_ACTIONS` compte 46 entrées (mesurer par regex sur le littéral), les trois boutons portent `title`, ergonomie 36/0 → 39/0 (mesurer).
- [ ] **Étape 4** : rejeu `repatch_all --from montage`, `--list`, `node --check`, bancs (édition, bundle, ergonomie), `--check --force-unchained` (ancres +3), sonde dzcout remesurée. Commit `montage : D-10 - preset Resolve, export import du mappage, action trans_add`, push.

## Tâche 2 — D-6 presse-papiers de clips entre projets

**Fichiers :** `montage.js` (bloc D-6), patcher (sections `L7b1` actions `copy`/`paste` dans `SVM_ACTIONS`, `L7b2` dispatch dans `onKey`, `L7b3` entrées Édition du menu ☰ automatiques via `dzmMenuRub` — vérifier que `DZM_MENU_RUB` range `copy`/`paste` en « Édition », sinon les ajouter à `DZM_MENU_RUB`), édition `[26]`, bundle `[L7] D-6`.

- [ ] **Étape 1 — banc rouge [26]** : `out.cc=T.clipCopy({id:"v1c4",tr:"v1",label:"x",start:2,end:5,srcIn:1,srcOut:4,src:{job_id:"j"},transition:"fade",transition_s:.4,src_history:[1],gain:-3})` → objet SANS `id`, `transition`, `transition_s`, `src_history`, AVEC `tr,label,start,end,srcIn,srcOut,src,gain` (start/end conservés : la durée est `end-start`) ; `out.cp_meme_piste=T.clipPaste(CLIPS, {v:1,clip:cc}, {head:10, tracks:TRACKS, mode:"inserer", seq:7})` → `{clips, id:"v1u7_100", track:"v1", refus:null}` avec un clip de 3 s à 10..13 ; `out.cp_piste_absente` (payload `tr:"v9"`, genre video) → piste `v1` (première du genre) ; `out.cp_genre_absent` (tr `"a1"` mais aucune piste audio dans `tracks`) → `{refus:"piste", note:"Aucune piste audio pour coller"}` ; `out.cp_vide=T.clipPaste(CLIPS,null,{})` → `{refus:"vide"}` ; `out.cp_v0=T.clipPaste(CLIPS,{v:2,clip:cc},{})` → `{refus:"version"}`. `dzmInsere` étant déjà bancé, on vérifie seulement que le collage passe par lui (`mode` rendu = `"inserer"`). Clés dans `vide_cles`.
- [ ] **Étape 2 — cœur pur** :

```js
/* ── L7 D-6 : presse-papiers de clips entre projets (pur) ── */
var DZM_CLIP_NOCOPY=["id","transition","transition_s","src_history"];
function dzmClipCopy(c){if(!c)return null;var o={};Object.keys(c).forEach(function(k){if(DZM_CLIP_NOCOPY.indexOf(k)<0)o[k]=JSON.parse(JSON.stringify(c[k]))});return o}
function dzmClipPaste(clips,payload,opts){
  opts=opts||{};if(!payload||!payload.clip)return {refus:"vide",note:"Presse-papiers vide"};
  if(payload.v!==1)return {refus:"version",note:"Presse-papiers d'une autre version"};
  var c=dzmClipCopy(payload.clip),tracks=opts.tracks||[],genre=dzmKindOf(c.tr);
  var tr=tracks.find(function(t){return t.id===c.tr})||tracks.find(function(t){return dzmKindOf(t.id)===genre});
  if(!tr)return {refus:"piste",note:"Aucune piste "+genre+" pour coller"};
  var head=Math.max(0,+opts.head||0),len=Math.max(.1,(+c.end||0)-(+c.start||0));
  c.tr=tr.id;c.start=head;c.end=head+len;
  c.id=dzmUniqueId(clips,tr.id+"u"+(opts.seq|0)+"_"+Math.round(head*10));
  var r=dzmInsere(clips,c,opts.mode||"inserer",{tracks:tracks,head:head,srcDur:opts.srcDur,range:opts.range,locked:opts.locked,twin:opts.twin});
  return {clips:r.clips,id:r.refus?null:c.id,track:tr.id,mode:r.mode,refus:r.refus||null,note:r.note||null}}
```

(Mesurer la signature réelle de `dzmInsere`/`dzmKindOf` avant d'écrire : `kind` d'une piste vient de `t.kind||dzmKindOf(t.id)` si la couche l'utilise ainsi.) Exports `clipCopy:dzmClipCopy,clipPaste:dzmClipPaste,`.

- [ ] **Étape 3 — bundle** : `L7b1` deux actions `{id:"copy",sec:"Montage",lbl:"Copier le clip",combo:"Ctrl+C"},{id:"paste",sec:"Montage",lbl:"Coller à la tête",combo:"Ctrl+V"}` (vérifier `SVM_COMBO_RESERVED` ; si réservées → `Ctrl+Maj+C/V`, écart daté) ; `L7b2` dans `onKey` : `copy` → `var sc=sel clip; if(sc){try{localStorage.setItem("dz_montage_clipboard",JSON.stringify({v:1,at:new Date().toISOString(),clip:DzTracks.clipCopy(sc)}))}catch(e){} fireNote("Clip copié — Ctrl+V pour coller à la tête")}` ; `paste` → lire/parse le localStorage en try/catch, `var r=DzTracks.clipPaste(clipsRef.current,payload,{head:headRef.current,tracks:proj.tracks,mode:dzModeRef.current,seq:ovSeq.current+1,range:proj.range,locked:…})` ; refus → `fireNote(r.note)` ; sinon `pushHistory();setClips(r.clips);setSelId(r.id);ovSeq.current+=1;setDirty(!0)` (utiliser les refs RÉELLES : mesurer `headRef`, `dzModeRef`, `fireNote`, et comment `addAsset` lit `locked`/`twin` pour `dzmInsere`, B:4406-4431). Banc bundle : actions ×1, `dz_montage_clipboard` ×2 dans `s` (set + get), `pushHistory();` précède `setClips(r.clips)` dans la branche (position par `find`).
- [ ] **Étape 4** : rejeu complet, bancs, commit `montage : D-6 - presse-papiers de clips entre projets`, push.

## Tâche 3 — D-8 boring detector

**Fichiers :** `montage.js` (D-8), patcher (`L7c1` état `boring` + `data-boring` sur `.svm-clip`, `L7c2` entrée ☰ Affichage « Plans trop longs / jump cuts… » → `setPop("boring")`, `L7c3` popover `boringPopover()`), `montage.css`, édition `[27]`, bundle `[L7] D-8`.

- [ ] **Étape 1 — banc rouge [27]** : `CLB=[{id:"a",tr:"v1",start:0,end:10,srcIn:0,src:{job_id:"j1"}},{id:"b",tr:"v1",start:10,end:12,srcIn:10.2,src:{job_id:"j1"}},{id:"c",tr:"v1",start:12,end:15,srcIn:0,src:{job_id:"j2"}},{id:"d",tr:"a1",start:0,end:30,src:{audio:"x"}}]` ; `out.bo=T.boring(CLB,{maxS:8,minFrames:12,fps:30})` → `{a:"long", b:"jump"}` (b reprend j1 à 10.2 alors que a s'arrête à 10.0 : écart 0.2 s < 12/30=0.4 → jump ; c change de source → rien ; d hors V1) ; `out.bo_defaut=T.boring(CLB)` = même résultat avec les défauts `{maxS:8,minFrames:12,fps:30}` ; `out.bo_loin=T.boring(CLB,{maxS:8,minFrames:3})` → `{a:"long"}` (0.2 ≥ 0.1) ; `out.bo_vide=T.boring([])` → `{}` ; `out.bo_long_et_jump` : un clip long ET jump rend `"jump"` (priorité au défaut visible). Clés dans `vide_cles`.
- [ ] **Étape 2 — cœur pur** :

```js
/* ── L7 D-8 : boring detector (pur) — plans trop longs et jump cuts sur V1 ── */
var DZM_BORING_DEF={maxS:8,minFrames:12,fps:30};
function dzmSrcKey(c){var s=c&&c.src||{};return s.job_id?"j:"+s.job_id:s.image?"i:"+s.image:s.audio?"a:"+s.audio:""}
function dzmBoring(clips,opts){
  var o=Object.assign({},DZM_BORING_DEF,opts||{}),out={};
  var v=(clips||[]).filter(function(c){return c.tr==="v1"}).slice().sort(function(a,b){return a.start-b.start});
  v.forEach(function(c,i){
    if((+c.end)-(+c.start)>o.maxS)out[c.id]="long";
    if(i>0){var g=v[i-1],k=dzmSrcKey(c);
      if(k&&k===dzmSrcKey(g)&&Math.abs(c.start-g.end)<=.1+1e-9){
        var fin=(+g.srcIn||0)+((+g.end)-(+g.start)),ecart=Math.abs((+c.srcIn||0)-fin);
        if(ecart<o.minFrames/o.fps)out[c.id]="jump"}}});
  return out}
```

Export `boring:dzmBoring,`.

- [ ] **Étape 3 — bundle + CSS** : `L7c1` : état `var stBo=x.useState(function(){try{return Object.assign({on:!1},DzTracks.boringDef,JSON.parse(localStorage.getItem("dz_svm_boring")||"{}"))}catch(e){return {on:!1}}})` (exporter aussi `boringDef:DZM_BORING_DEF`), `boMap=x.useMemo(function(){return bo.on?DzTracks.boring(clips,bo):{}},[clips,bo])`, et sur `.svm-clip` (ancre `"data-kind":c.kind||void 0,` 1/0/1 — mesurer) → `"data-boring":boMap[c.id]||void 0,` ; `L7c2` entrée Affichage dans `dzMenuProps` (modèle « Durées sur les clips », mesurer B:2162-2180) `{id:"boring",lbl:"Plans trop longs / jump cuts…",run:function(){setPop("boring")}}` ; `L7c3` `boringPopover()` = `div.svm-pop` titre « Plans trop longs / jump cuts », case « Activer », `fieldNum` « Plus long que (s) » 2..60, `fieldNum` « Jump cut si écart < (images) » 1..60, écriture `localStorage dz_svm_boring` en try/catch, bouton « Fermer » ; rendu `pop==="boring"?boringPopover():null` à côté des autres popovers (mesurer où `pop==="render"` est rendu). CSS `montage.css` : `.dzsvm .svm-clip[data-boring="long"]{outline:1px dashed #9a9a9a;outline-offset:-1px}` `.dzsvm .svm-clip[data-boring="jump"]{outline:2px solid #e0443e;outline-offset:-2px}`. Banc bundle : ancres, `data-boring` ×1, règles CSS ×1 et ×0 dans `src`, popover porte `title` sur ses boutons.
- [ ] **Étape 4** : rejeu, bancs, commit `montage : D-8 - boring detector, plans trop longs et jump cuts`, push.

## Tâche 4 — D-39 comparaison de deux projets

**Fichiers :** `montage.js` (D-39 `dzmDiff` + `DzmDiffView` + bouton dans `DzmProjects`), patcher (`L7d1` : `DzmProjects` reçoit `courant:{name,clips}` et `onDiff` → l'hôte ouvre `pop==="diff"`), `montage.css` (`.dzm-diff`), édition `[28]`, bundle `[L7] D-39`.

- [ ] **Étape 1 — banc rouge [28]** : `A=[{id:"1",tr:"v1",start:0,end:5,srcIn:0},{id:"2",tr:"v1",start:5,end:8,srcIn:0,gain:0},{id:"3",tr:"a1",start:0,end:8}]`, `B=[{id:"1",tr:"v1",start:2,end:7,srcIn:0},{id:"2",tr:"v1",start:5,end:9,srcIn:0,gain:-3},{id:"4",tr:"v1",start:9,end:12}]` ; `out.df=T.diff(A,B)` → `{added:["4"],removed:["3"],moved:[{id:"1",de:0,en:2}],trimmed:[{id:"2",de:[5,8],en:[5,9]}],changed:[{id:"2",cles:["gain"]}]}` (un clip peut être à la fois trimmed et changed ; moved exclut trimmed) ; `out.df_id=T.diff(A,A)` → tout vide ; `out.df_vide=T.diff([],[])` ; `out.df_vue` = rendu de `DzmDiffView({diff:out.df,nomA:"a",nomB:"b"})` avec le jsx factice : contient les cinq rubriques et « 1 ajouté · 1 supprimé · 1 déplacé · 1 rogné · 1 modifié ». Clés dans `vide_cles`.
- [ ] **Étape 2 — cœur pur** : `DZM_DIFF_CLES=["gain","opacity","x","y","scale","rotate","effects","dz","speed","retime","stab","text","transition","transition_s","fade_in","fade_out","label","tr"]` ; `dzmDiff(a,b)` par index `id` ; `DzmDiffView(o)` lit `r` à l'appel et rend `div.svm-pop.dzm-diff` avec résumé + listes (`label||id`, temps `mm:ss`). Exports `diff:dzmDiff,DiffView:DzmDiffView,`.
- [ ] **Étape 3 — bundle** : `L7d1` : dans `DzmProjects` (couche, pas bundle) chaque ligne autre que le courant gagne un bouton « ⇄ » `title="Comparer à la timeline courante"` → `props.onDiff(p)` ; l'hôte (ancre `r.jsx(DzTracks.Projects,{` B:6307, 1/0/1) passe `onDiff:function(p){fetch("/api/montage/projects/"+p.id).then(r=>r.json()).then(d=>{setDiff({diff:DzTracks.diff(clipsRef.current,d.clips||[]),nomA:proj.name,nomB:p.name});setPop("diff")})}` et rend `pop==="diff"&&diffSt?r.jsx(DzTracks.DiffView,Object.assign({onClose:function(){setPop("")}},diffSt)):null`. Banc bundle + ergonomie.
- [ ] **Étape 4** : rejeu, bancs, commit `montage : D-39 - comparaison de deux projets`, push.

## Tâche 5 — D-19 coins arrondis et ombre sur un overlay (backend + inspecteur)

**Fichiers :** `backend/app/services/montage_service.py` (`_ov_transform`, chaîne overlay MS:2967-3024), `backend/tests/test_montage_l7.py` (NEUF), patcher (`L7e1` deux champs dans `ovInspector`, `L7e2` `svmOvTfOf` lit `radius`/`shadow`, `L7e3` `renderPayload` les émet, `L7e4` `svmApplyTf` aperçu), bundle `[L7] D-19`.

- [ ] **Étape 1 — banc rouge `test_montage_l7.py`** (modèle `test_montage_l4.py` : `BUILD`, `V1SPEC`, TMP, ffmpeg réel en [M]) : `_ov_transform({"x":.5,"y":.5,"scale":1,"radius":40,"shadow":1})` → `tf["radius"]==40 and tf["shadow"]==1` ; `radius` 999 → 200, `-1` → 0, `"abc"` → 0 avec warning ; `shadow` `True`/`"1"`/2 → 1, `0`/None → 0 ; chaîne : un overlay `tf` avec `radius=40` porte `geq=` UNE fois avec `min(40,W/2,H/2)` littéral, placé après `colorchannelmixer`/`format=rgba` et AVANT `rotate=` ; `shadow=1` → `split[o5][s5]`, `boxblur=6`, `pad=`, l'`overlay=0:0` intermédiaire et le label `[ov5]` final inchangé ; sans les deux champs → chaîne octet pour octet identique à L3 (témoin) ; sur la chaîne « cover » (sans tf) `radius` ignoré + warning ; avec `motion_points` d'échelle → ignoré + warning. [M] : rendu réel 2 s d'un overlay `radius=60, shadow=1` sur `testsrc2` 480×270 → rc 0, fichier > 0, et un pixel du COIN de l'overlay (`ffmpeg -vf crop=1:1:x:y -f rawvideo`) est celui du fond, le pixel au centre du bord est celui de l'overlay (mesure de deux pixels par `ffmpeg … -frames:v 1 -f rawvideo -pix_fmt rgb24 -`). `=== N failed ===`.
- [ ] **Étape 2 — backend** : `spec` de `_ov_transform` gagne `"radius": (0, 200, 0)` (entier, `int(round())`) et `"shadow": (0, 1, 0)` (→ `1 if truthy numérique ≥ 0.5 else 0`) — mais ces deux clés NE rendent PAS `tf` non-None à elles seules si x/y/scale/rotate sont absents ? DÉCISION : si `radius` ou `shadow` est posé sans transformation, `tf` devient `{x:.5,y:.5,scale:1,rotate:0,radius,shadow}` (la chaîne avec transformation est nécessaire, c'est le prix ; daté). Dans la chaîne : après l'opacité (MS:2979) :

```python
            rad = int(tf.get("radius") or 0) if tf else 0
            if rad > 0 and not zp:
                och += (f",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                        f"a='alpha(X,Y)*(1-gt(hypot(max(abs(X-W/2)-(W/2-min({rad},W/2,H/2)),0),"
                        f"max(abs(Y-H/2)-(H/2-min({rad},W/2,H/2)),0)),min({rad},W/2,H/2)))'")
            elif rad > 0:
                logger.warning(f"montage: overlay radius ignoré (échelle animée) — {lbl}")
```

et pour l'ombre, à l'émission (MS:3009-3011), quand `tf.get("shadow")` et pas `zp` :

```python
            if tf and tf.get("shadow") and not zp:
                parts.append(f"[{idx}:v]{och}[oa{j}]")
                parts.append(f"[oa{j}]split[oo{j}][os{j}]")
                parts.append(f"[oo{j}]pad=iw+16:ih+16:8:8:color=black@0[op{j}]")
                parts.append(f"[os{j}]colorchannelmixer=rr=0:gg=0:bb=0:aa=0.55,boxblur=6,"
                             f"pad=iw+16:ih+16:14:14:color=black@0[osp{j}]")
                parts.append(f"[osp{j}][op{j}]overlay=0:0[ov{j}]")
            else:
                parts.append(f"[{idx}:v]{och}[ov{j}]")
```

(`och` contient déjà `setpts` : VÉRIFIER l'ordre réel — `setpts` doit rester sur le flux final `[ov{j}]` ; si `setpts` est dans `och`, le split hérite du même PTS, acceptable ; mesurer que `overlay=0:0` entre deux flux de même PTS ne décale rien : rendu [M].) Position : `x={cx}-w/2` reste juste (w/h = taille paddée : l'ombre déborde de 8 px, daté).
- [ ] **Étape 3 — client** : `L7e1` deux champs dans `ovInspector` après « Opacité » (`fieldNum` « Coins (px) » 0..200 step 5 → `svmOvTfField({radius:v})` ; case « Ombre portée » → `svmOvTfField({shadow:ch?1:0})`) ; `L7e2` `svmOvTfOf` borne `radius` 0..200 et `shadow` 0|1 ; `L7e3` `renderPayload` : `if(tf.radius>0)o.radius=tf.radius;if(tf.shadow)o.shadow=1;` ; `L7e4` `svmApplyTf` : `el.style.borderRadius=(tf.radius||0)+"px";el.style.boxShadow=tf.shadow?"6px 6px 12px rgba(0,0,0,.55)":""` (mesurer l'élément et l'échelle px de l'aperçu — le rayon en px du canvas 1080 doit être ramené à la taille affichée : `rad*el.offsetWidth/ow2` si disponible, sinon écart daté « aperçu approximatif »). Banc bundle + ergonomie (`title` sur la case).
- [ ] **Étape 4** : bancs l7 (0 failed), l3 86/0, l2 78/0, bundle, édition ; commit `montage : D-19 - coins arrondis et ombre portee sur un overlay`, push.

## Tâche 6 — D-22 pistes de sous-titres par langue, une seule gravée

**Fichiers :** `montage.js` (D-22 cœur pur + `dzmRemove`/`DzmTrackBtns`/`svmTracksPayload`), patcher (`L7f1` `subsPayload()` lit la piste gravée, `L7f2` `data-sub` par genre + `data-burn`, `L7f3` menu contextuel de piste EC5 : « Graver cette piste », « Exporter .srt/.vtt/.txt », « Nouvelle piste de langue… », `L7f4` M26a : cible « nouvelle piste »), `montage.css` (`[data-burn]` œil), édition `[29]`, bundle `[L7] D-22`, `test_subs_traduction.py`/`test_montage_pistes_dyn.py` relancés.

- [ ] **Étape 1 — banc rouge [29]** : `TR=[{id:"v1",kind:"video"},{id:"s1",kind:"subs"},{id:"a1",kind:"audio"}]` ; `out.st=T.subsTracks(TR)` → `["s1"]` ; `out.sn=T.subsNew(TR,"en")` → `{tracks:[…,{id:"s2",name:"S2 en",kind:"subs",lang:"en",type:"sous-titres",…}], id:"s2"}` (habillage `dzmSkin`) ; `out.sn2=T.subsNew(out.sn.tracks,"de").id==="s3"` ; `out.sb=T.subsBurn(out.sn.tracks,"s2")` → s2 `burn:true`, s1 `burn:false` (une seule) ; `out.sb_defaut=T.subsBurn(TR,null)` → s1 gravée ; `out.sc=T.subsCopy(CL,"s1","s2",[{start:0,end:1,text:"Hi"}])` → clips `tr:"s2"` avec ids `s2c…` uniques, `label`==`text`, autres clips intacts ; `out.rm=T.remove(out.sn.tracks,"s2")` retire s2 ; `out.rm_s1=T.remove(TR,"s1")` ne retire PAS s1 ; `out.tp=T.tracksPayload(out.sb.tracks)` porte `lang` et `burn`. Clés dans `vide_cles`.
- [ ] **Étape 2 — cœur pur** : `dzmSubsTracks`, `dzmSubsNew` (id = `"s"+(max n+1)`, `dzmSkin` pour l'habillage), `dzmSubsBurn` (retourne un NOUVEAU tableau), `dzmSubsCopy(clips,deTr,versTr,segments)` (segments donnés → clips neufs `{id,tr:versTr,start,end,text,label:text}` ; segments absents → copie des clips de `deTr`), `dzmRemove` : `id==="v1"||id==="s1"` inchangé (s2… supprimables), `DzmTrackBtns` : `base` inchangé, `svmTracksPayload` : `+ lang, burn`. Exports `subsTracks,subsNew,subsBurn,subsCopy`.
- [ ] **Étape 3 — bundle** : `L7f1` `subsPayload()` : ancre `return (cs||[]).filter(function(c){return c.tr==="s1"})` de `subsSegsOf` (B:4053, mesurer 1/0/1) → `var bid=(proj.tracks||[]).filter(function(t){return t.burn&&trackKind(t.id)==="subs"}).map(function(t){return t.id})[0]||"s1";return (cs||[]).filter(function(c){return c.tr===bid})` (ATTENTION : `subsSegsOf` sert aussi à l'éditeur S1 (`emojiSegs`, tiroir) — si oui, ne changer QUE `subsPayload` : mesurer les appelants ; l'éditeur reste sur s1) ; `L7f2` `"data-sub":tr.id==="s1"?"":void 0` → `"data-sub":trackKind(tr.id)==="subs"?"":void 0,"data-burn":tr.burn?"":void 0` ; `L7f3` menu de piste (section EC5, entrées `dzTrackMenu`) : pour une piste subs, `{lbl:"Graver cette piste au rendu",run:…setProj(p=>({...p,tracks:DzTracks.subsBurn(p.tracks,tr.id)}))}`, `{lbl:"Exporter .srt",run:…subsDownload(subsToSrt(clips.filter(c=>c.tr===tr.id)))}` (+ .vtt/.txt ; mesurer les noms RÉELS de `subsToSrt`/`subsDownload` inlinés — s'ils sont hors de portée du scope de DzMontage, exposer par `window.DzSubs` déjà exporté : `DzSubs.toSrt` existe-t-il ? mesurer ; sinon réimplémenter `dzmSrt(segs)` pur dans la couche, 10 lignes), `{lbl:"Nouvelle piste de langue…",run:…prompt("Langue (en, de…)")→subsNew+subsCopy(vide)}` ; l'historique D-0 couvre `tracks` (DZM_HIST_CLES) : `pushHistory()` avant ; `L7f4` M26a : le sélecteur « vers » gagne une case « dans une nouvelle piste » : si cochée, `dzTraduire` ne fait pas `onChange(dzNext,!0)` mais `subsNew(tracks,target)` + `subsCopy(clips,"s1",id,segsTraduits)` + `setClips`/`setProj` (nécessite que M26a ait accès à `setClips`/`setProj` : mesurer ; sinon passer un callback `onNewTrack` par les props du tiroir). Banc bundle : ancres, `data-burn` ×1, `subsPayload` lit `burn` ×1, menu entrées ×1 chacune.
- [ ] **Étape 4** : bancs (édition, bundle, pistes_dyn, subs_traduction, subtitles_burn), rejeu ; commit `montage : D-22 - pistes de sous-titres par langue, une seule gravee`, push.

## Tâche 7 — clôture L7-A

- [ ] `backend/tests/mutations_montage_l7.py` (modèle `mutations_montage_l4.py`, ≥ 12) : `dzmKmImport` acceptant version 2 ; preset Resolve sans `trans_add` ; `dzmClipCopy` gardant `id` ; `dzmClipPaste` sans repli de piste ; `dzmBoring` jump sans test de source ; `dzmBoring` `long` avec `>=` ; `dzmDiff` moved incluant trimmed ; `_ov_transform` radius non borné ; `geq` sans `min(…)` ; ombre sans `boxblur` ; `dzmSubsBurn` laissant deux gravées ; `dzmRemove` supprimant s1 ; bundle : `data-boring` retiré ; `subsPayload` lisant `"s1"` en dur ; `trans_add` retiré de `SVM_ACTIONS`.
- [ ] `test_montage_l7_croise.py` : combos du preset Resolve toutes canonisables et non réservées (rejouer `svmComboCanon`/`svmComboReserved` extraits du bundle sous node) ; ids d'actions du preset ⊂ `SVM_ACTIONS` ; `DZM_DIFF_CLES` ⊂ clés réellement émises par `renderPayload` ∪ clés client ; `radius/shadow` du payload client == clés lues par `_ov_transform` ; `svmTracksPayload` émet `burn` et `_tracks_meta` la conserve (ou daté : le backend l'ignore).
- [ ] Comptes, `--check`, `--list`, `node --check`, sonde ; conception `2026-09-21-montage-vs-resolve-design.md` l.43/47/49/52/67/75/126/178 datées « exécuté <date> … écarts : … » (sélection simple → un clip copié ; vignettes A/B côté navigateur au 1/30 ; `trans_add` neuve ; radius/shadow hors cover et hors échelle animée, ombre déborde 8 px ; S2 non éditable dans le tiroir ; presse-papiers un seul clip ; boring = V1 seulement, jump = même source en contact) ; mémoire par le contrôleur ; L7-B listé comme reste.

## Relecture du plan
- Couverture : D-10 (T1), D-6 (T2), D-8 (T3), D-39 (T4), D-3b (dans T5 ? NON — **D-3b est absent des tâches** : l'ajouter en **T4-bis**).

### Tâche 4-bis — D-3b vignettes A/B et ±1 image à la jonction

**Fichiers :** patcher (`L7g1` rangée `svm-abrow` dans `transPopover()` B:5193-5223), `montage.css` (`.svm-abrow`, `.svm-abthumb`), bundle `[L7] D-3b`, preuve écran.

- [ ] **Étape 1 — banc rouge bundle** : `svm-abrow` ×0 dans `.bak`, ×1 dans `s` ; la rangée appelle `svmThumb(` deux fois et `DzTracks.roll(` une fois ; `pushHistory();` précède `setClips(` dans le gestionnaire ; boutons `title` (ergonomie).
- [ ] **Étape 2 — section `L7g1`** : ancre = le curseur de durée de `transPopover` (mesurer 1/0/1) → AVANT lui, si `jl&&jr` sont deux clips vidéo (`src.job_id`) en contact : `var ta=(+jl.srcIn||0)+(jl.end-jl.start)-1/30,tb=+jr.srcIn||0;` deux `<img className="svm-abthumb">` alimentées par `svmThumb(src,sec,cb)` (état local `abA/abB` par `x.useState` + `x.useEffect` sur `[jl.id,jr.id,ta,tb]` — dans un composant fonction du bundle, `x.useState` est disponible : mesurer que `transPopover` est appelée DANS le rendu de DzMontage, donc les hooks doivent vivre au niveau de DzMontage, pas dans `transPopover()` : déclarer `abSt` près de `stBo` et le remplir par un `useEffect` gardé par `pop==="trans"`), et une rangée « A ◀ −1 · +1 ▶ B » : `function abRoll(n){var r=DzTracks.roll(clipsRef.current,jl.id,jr.id,n/30);if(!r||r===clipsRef.current)return;pushHistory();setClips(r);setDirty(!0)}` (mesurer la valeur de retour de `dzmRoll` : tableau neuf ou `{clips}`), Maj = ×10 (`e.shiftKey`). CSS : `.dzsvm .svm-abrow{display:flex;gap:6px;align-items:center}.dzsvm .svm-abthumb{width:78px;height:44px;object-fit:cover;background:#111;border-radius:3px}`.
- [ ] **Étape 3** : rejeu, bancs, commit `montage : D-3b - vignettes A B et roll d une image a la jonction`, push.

- Noms : `kmPreset/kmExport/kmImport`, `clipCopy/clipPaste`, `boring/boringDef`, `diff/DiffView`, `subsTracks/subsNew/subsBurn/subsCopy`, actions `trans_add/copy/paste`, clés `dz_svm_boring`, `dz_montage_clipboard`, champs `radius/shadow`, `burn/lang` sur les pistes, `data-boring/data-burn`, sections `L7a1..L7g1`.
- Ordre d'exécution : T1 → T2 → T3 → T4 → T4-bis → T5 → T6 → T7.
