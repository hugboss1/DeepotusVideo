# Lot L7-B du Montage — export, plans, cadrage, auto-clips, notes — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** livrer le reste du lot L7 de `docs/superpowers/specs/2026-09-21-montage-vs-resolve-design.md` (l.178) : D-37 export EDL CMX 3600 + FCPXML (l.119, = D5 du plan du 03/09), D-42 découper aux changements de plan par `scdet` (l.130), D-40 recadrage par énergie de mouvement PIL (l.129, = D2), D-41 auto-clips 15–60 s avec score LLM et repli heuristique (l.129, = D3), D-34 note ★ « Good Take » sur les rendus (l.111).

**Architecture :** chaque décision = un service backend PUR et bancé (`edl_export.py`, `scenes.py`, `reframe.py`, `autoclips.py`) + une route dans `montage_service.py` + une entrée client (couche `frontend/patches/montage.js` + sections `L7B*` du patcher `scripts/patch_bundle_montage.py`). Aucune dépense sans confirmation : la transcription payante de D-41 passe par une estimation puis `confirm:true` ; le LLM est optionnel (repli heuristique).

**Tech :** FastAPI, ffmpeg 8.1.1 essentials (`scdet` mesuré : coupe détectée à 2,0 s sur deux plans concaténés), PIL 12.3.0 (numpy, cv2, scipy ABSENTS du python embarqué — mesuré), `summarizer._chat_dispatch`, `transcribe_service`, bundle patché en octets, bancs python embarqué, Playwright pour les preuves.

---

## Liste de contrôle du lot (cochée par le contrôleur à chaque tâche close = revue conforme + revue qualité + bancs verts)

- [x] T1 — D-37 export EDL + FCPXML (`5d5eadc`, revue `562a048`, `140c3d5` ; FCPXML 1.9, FROM CLIP NAME = fichier, poignées dites)
- [x] T2 — D-42 découper aux changements de plan (`4c48d45`, revue `8517a25` ; réponse obsolète refusée, écart minimal entre coupes)
- [x] T3 — D-40 recadrage : backend (tracker PIL, crop à x animé) (`d70989c`, revue `e09552b` ; `-/filter_complex <fichier>` au-delà de 30 000 car., arbre `_rf_lerp_expr` car la chaîne échoue au-delà de 93 points ; restes mineurs pour T8)
- [x] T4 — D-40 recadrage : client (inspecteur « Cadrage ») (`871d5de`, revue `637bf41` ; source et mode dans l'empreinte d'obsolescence, aussi pour D-42 ; modes gelés pendant l'analyse ; plans image)
- [x] T5 — D-41 auto-clips : backend (`9c55f40`, revue `031dd6a` ; toute la source examinée, 60 candidats par tranches, mots transcrits en cache, clips disjoints, `llm:false` ; reste : `windows` hors `to_thread`, pour T8)
- [ ] T6 — D-41 auto-clips : client
- [x] T7 — D-34 note ★ des rendus (base + tiroir Médias) (`0285290`, `2c66209`, revue `84814da` ; offset qui suit le compte serveur, PUT en file ; restes pour T8 : recharge sous filtre qui devance un PUT, mémoires `noteConf/noteFile/noteSeq` jamais vidées)
- [ ] T8 — clôture (mutations, banc croisé, conception datée, revue finale, PR)

Règle de non-blocage : une tâche n'attend jamais la preuve écran d'une autre ; le contrôleur joue les preuves écran par paquets sur 8799 pendant que la tâche suivante avance, et une retouche issue d'une preuve devient un commit de revue de la tâche concernée.

## Conventions valables pour tout le plan

```powershell
$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"
Set-Location backend
& $PY tests\test_montage_l7b.py            # NEUF (T1) — un banc pour les services backend du lot
& $PY tests\test_montage_edition.py        # 400/0 au départ
& $PY tests\test_montage_bundle.py         # 2191/0
& $PY tests\test_montage_ergonomie.py      # 52/0
& $PY tests\test_montage_l7.py             # 33/0
& $PY tests\test_montage_l4.py ; & $PY tests\test_montage_l3.py ; & $PY tests\test_montage_l2.py
& $PY tests\test_montage_projets.py ; & $PY tests\test_montage_eb.py ; & $PY tests\test_hygiene_imports.py
Set-Location ..
& $PY scripts\patch_bundle_montage.py --check --force-unchained   # 191 ancres au départ
& $PY scripts\repatch_all.py --from montage ; & $PY scripts\repatch_all.py --list
node --check frontend\dist\assets\index-BEOJX8L5.js ; node --check frontend\patches\montage.js
```

- Un banc = un processus, jamais `pytest`. `check(label, cond, detail)`, `=== N passed, M failed ===`, code de sortie. Règle des assertions négatives (témoin positif dans la même expression), état vide construit, faute n°6 (aucune lecture nue, détail évalué avant le court-circuit). Sections neuves de `test_montage_edition.py` : [32]… (clés dans `vide_cles`).
- Ancres comptées sur `.bak_montage` (1/0/1) ; ancre consommée → repli dans le remplacement hôte ; sections en queue, préfixe **`L7B`**. `.bak_dzcout` plus récent ⇒ `repatch_all --from montage`. Bundle en OCTETS (CRLF) ; la couche `montage.js` est en LF (mesuré le 24/09). Sonde `("montage","DzTracks",159)` remesurée et justifiée. Aucun nom d'API navigateur dans les commentaires de la couche (piège `_corps`). `localStorage` en try/catch.
- Backend : `montage_service.py` en CRLF, travailler en octets (Write/Edit ; le Bash de la session désescape `\n` : pas de heredoc pour du code). Tout service neuf est pur (pas d'état global hors cache borné), importé par `montage_service.py`.
- Commits `--only`, première ligne sans accent `montage : D-xx - <quoi>`, trailer EXACT `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, push `chantier/montage-l7b`. Jamais `git checkout --`/`stash`. Aucun serveur relancé (8765 = production de l'utilisateur ; 8799 = preuves du contrôleur). Chaque agent CONTESTE le plan par la mesure (écart daté).
- AUCUNE dépense réelle dans les bancs ni les preuves : LLM factice injecté, transcription jamais confirmée (on prouve l'estimation et le refus sans `confirm`), texte connu via `align_known_text`.

## Faits mesurés le 24/09/2026 (relevé lecture seule, état a284485)

- **Rien de D2/D3/D5 n'existe** ; `scdet` non utilisé ; aucune route `/export`, `/reframe`, `/autoclips`, `/scenes`.
- **Résolution de source** : `_resolve_src(src)` (MS:2529-2553) `{job_id}` → `final_video_path or video_path` ; `_media_source(request, src, *, video)` (MS:4422) localhost, 404/415 ; `_load_saved()` (MS:1324) = timeline courante. Champs de rendu V1 (MS:4010-4022) : `src_in`, `start`, `end`, `transition`, `transition_s`, `speed` (`_v1_speed`, 0.0 = ×1, bornes 0,25–4). Source consommée = `(end−start)×speed`.
- **Recadrage aujourd'hui** : V1 toujours « cover » centré `scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps},format=yuv420p` (MS:2733 ; variantes vitesse/zoom MS:2761-2767) ; `dz` (D-13) est un `zoompan` APRÈS `fps` (sur image déjà coupée) ; commentaire MS:1170 : `crop=w='…t…'` échoue (−22) — un `x` animé n'a JAMAIS été mesuré. `_CANVAS` MS:223. `_mp_lerp_expr(pts, var="t")` MS:1096.
- **LLM** : `summarizer._chat_dispatch(prompt, system, max_tokens) -> (str|None, fournisseur)` (summarizer.py:156), Anthropic/OpenAI/Gemini, ne lève pas ; `available()` vrai avec Ollama seul alors que Ollama n'est jamais appelé → repli heuristique obligatoire. Motif JSON : routes.py:5787-5830.
- **Transcription** : gratuite `align_known_text` (transcribe_service:459), `align_to_audio` (:548), `group_words` (:646) ; payante `estimate_transcription` (:941, `ok:false` sans clé), `transcribe(audio_path, provider, language)` (:1007) ; ElevenLabs 0,0067 $/min, OpenAI whisper 25 Mo max.
- **Épisodes/chapitres** : `JobRecord` (storage.py:17-54) sans `chapter_id` ; `Chapter.script_text` (storage.py:257) ; le texte des scènes d'un épisode n'est pas conservé sur le job. Vidéo externe : `POST /videos/upload` → job `provider="ugc"`.
- **Lame** : `useCallback` du bundle (son-vfx-montage.js:2530-2544) : marge 0,05 s, piste verrouillée refusée, `pushHistory()`, moitié droite `{id:c.id+"_b"+round(p*10), start:p, srcIn:srcIn+(p−start)×speed, transition:"cut", transition_s:0}` — id non unique pour deux coupes à < 0,1 s. `dzmRippleCut` (M:631-705) a un générateur d'ids sans collision.
- **Téléchargement client** : `subsDownload(name,text,mime)` (bundle, même portée module que DzMontage, réutilisé par D-10 et D-22). Modèle serveur : `POST /api/subtitles/export` (routes.py:8941) `Content-Disposition: attachment`.
- **Notes** : pas de route `/api/library` ; l'écran Bibliothèque (`vm`, bundle l.285-286) vit dans les maillons `libprov`/`libsend` INTOUCHABLES, dont les `.bak` sont absents de ce worktree ; les rendus n'ont pas de ligne `library_assets` (décision du 28/08) ; favoris actuels en localStorage (`dz_fav_renders`). Migration de colonne : liste de paires + boucle `_auto_migrate` (storage.py:442-530, `ALTER TABLE … ADD COLUMN`). `_job_to_dict` routes.py:3331 ; `Pipeline.list_jobs(limit, offset, providers, q, video_exts)` pipeline.py:1283 (filtres AVANT le `limit`). Tiroir `DzmMediaDrawer` M:6606 (`/api/jobs?limit=24&offset=…&video=1&q=…`). Pin suspect : `test_library_sendto.py` exige `__dzMontageAdd` ×5, le bundle en compte 7 — à mesurer en T7.

### Décisions prises sur les démentis

1. **D-37** : service `edl_export.py` pur : `to_edl(rec, resolve, fps=30) -> str` (CMX 3600 : `TITLE:`, `FCM: NON-DROP FRAME`, événements V1 puis audio A1/A3, bobine `AX`, `hh:mm:ss:ff`, `* FROM CLIP NAME:`, `* SOURCE FILE:`, transitions V1 `fade`/`dissolve` → événement `D` de la durée en images, autres transitions → `C` + commentaire `* TRANSITION: <nom> (non exportée)`, titres/ajustements/sous-titres/overlays sans source → `* SKIPPED: <genre> <label>`) et `to_fcpxml(rec, resolve, fps=30, size=(w,h)) -> str` (version FCPXML LUE sur la documentation Apple par WebFetch à l'étape 1 et datée ; `format` 1/30s ; `asset` par source avec `src` = `Path.resolve().as_uri()` ; `spine` d'`asset-clip` V1 avec `offset`/`start`/`duration` en `n/30s` ; audio A1 en `asset-clip lane="-1"` ; vitesse ≠ 1 → `timeMap` si la version le permet, sinon commentaire daté). Vitesse en EDL : durée source = `(end−start)×speed`, commentaire `* SPEED: <x>` (M2 motion effect non émis, daté). Route `GET /api/montage/export?format=edl|fcpxml` : `_load_saved()` + `_resolve_src`, `Response` texte avec `Content-Disposition: attachment; filename="<nom nettoyé>.edl|.fcpxml"`, 400 sans timeline, 400 format inconnu. Client : ☰ › Projet « Exporter EDL… » / « Exporter FCPXML… » → `fetch` puis `subsDownload` (même chemin que D-10). Preuve finale : import dans DaVinci Resolve par l'UTILISATEUR (hors session, daté).
2. **D-42** : service `scenes.py` : `detect(path, src_in, dur, threshold=10.0) -> [t…]` via `ffmpeg -ss src_in -t dur -i path -vf "scdet=threshold=T,metadata=print:file=-" -f null -` (temps RELATIFS au début lu, triés, dédoublonnés à 1/30 s, bornés à 200), cache par (chemin, mtime, srcIn, dur, T) dans `outputs/montage_cache`, timeout proportionnel. Route `POST /api/montage/scenes {src, srcIn, dur, threshold?}` → `{ok, times}`. Cœur pur `dzmCutAt(clips, id, times, opts)` : times en secondes du CLIP (0..len), convertis `start + t/speed` sur la timeline, coupes à moins de 0,05 s d'un bord ignorées, piste verrouillée → refus, `srcIn` recalé par `×speed`, moitiés droites `transition:"cut"`, ids uniques par le générateur de `dzmRippleCut` (ou `dzmUniqueId`), rend `{clips, n, refus, note}`. Client : clic droit sur un clip vidéo « Découper aux changements de plan » (menu contextuel E-6) → route → `pushHistory()` + `setClips`, note « n coupes ».
3. **D-40** : service `reframe.py` : `motion_track(path, src_in, dur, fps=4, width=96, noise=12) -> {mode:"suivi"|"centre", points:[{t,x}], fps}` (frames ffmpeg `fps=4,scale=96:-2,format=gray` en PNG temporaires, `ImageChops.difference` + `resize((w,1), BOX)`, barycentre des colonnes au-dessus de `noise`, EMA 0,5, plus de 20 % des paires sans mouvement → `centre`) ; banc : carré de 60 px qui traverse un fond 480×270 → erreur ≤ 8 % de la largeur sur t ∈ [0,5 ; 3,5] ; statique → `centre`, x = 0,5. Champ V1 `reframe: {mode:"centre"|"suivi"|"manuel", x?, points?}` nettoyé par `_reframe_of(c)` (≤ 240 points, t en secondes de SOURCE depuis srcIn — le crop précède setpts=PTS/speed ; ÉCART DATÉ du 24/09/2026, mesuré en T3 (`d70989c`) : le plan disait « secondes du CLIP », le client convertit la tête par (tête − start) × vitesse). Rendu : le `crop={w}:{h}` du cover devient `crop={w}:{h}:x='clip(iw*(EXPR)-{w}/2,0,iw-{w})':y=(ih-{h})/2` avec `EXPR = _mp_lerp_expr(points)` en temps du clip — MESURER d'abord qu'un `x` animé de `crop` passe dans ffmpeg 8.1.1 (D-13 a mesuré l'échec d'un `w` animé) et que `t` y vaut le temps du flux APRÈS `trim/setpts` (sinon passer par `sendcmd` comme D-14, daté) ; sans champ → commande octet pour octet identique. `mode:"manuel"` = `x` constant. Route `POST /api/montage/reframe {src, srcIn, dur}` → résultat du tracker. Client (T4) : section « Cadrage » de l'inspecteur d'un clip V1 : Centré / Suivre le mouvement (analyse, bouton) / Manuel (curseur x 0–100 %), aperçu vivant par `object-position` sur l'élément du lecteur vivant, payload `reframe` dans `renderPayload`. Réglages visibles seulement si le ratio source ≠ ratio projet ? NON (E-12) : toujours rendus, grisés avec infobulle quand la source remplit déjà le cadre.
4. **D-41** : service `autoclips.py` : `windows(words, min_s=15, max_s=60, step_s=5)`, `heuristic(win, persona)` (formule du plan du 03/09 : 40 + 15·`?` + 10·chiffre + 5·mots-clés persona − pénalité > 45 s, borné 0..100, déterministe), `score(wins, llm=None, n=4, persona=None)` (`llm` = `_chat_dispatch` par défaut, JSON strict `[{i,score,title,hook}]`, `max_tokens=800`, toute erreur/`None` → heuristique ; rend `{clips:[{start,end,score,title,hook,segments}], source:"llm:<f>"|"heuristique"}`, `segments = group_words(words, max_chars=30)`). Routes `POST /api/montage/autoclips {src, text?, chapter_id?, lang, n, persona?, confirm?}` (texte fourni ou `Chapter.script_text` → `align_to_audio` gratuit ; sinon `estimate_transcription` et `{ok:false, estimate}` tant que `confirm` n'est pas vrai, puis `transcribe`) et `POST /api/montage/autoclips/create {src, clip, name?}` → projet neuf nommé (V1 `{src, srcIn:start, start:0, end:dur}`, A1 son du plan si la source a de l'audio, S1 = segments décalés de −start) → `{project_id}` via le mécanisme de création de projet existant (`POST /projects` / `_save_record`). Client (T6) : clic droit sur une ligne du tiroir Médias (ou bouton « Auto-clips… » sur la ligne) → popover : source, texte connu (zone de texte optionnelle ou chapitre), n, bouton « Estimer » → affiche coût/refus ; « Lancer » (avec `confirm` seulement si l'utilisateur l'a demandé explicitement dans le popover) → liste des clips (score, titre, accroche, durée) → « Créer le projet » → ouvre le projet (mécanisme E-1 « ouvrir »). ÉCART DATÉ du 24/09/2026 (T6) : bouton « ✂ auto-clips » sur la ligne (pas de clic droit) ; section [35] de l'édition ([34] prise par D-40) ; aucune section `L7Bac` — trois replis (R_M11 état `dzAcOpen`, R_EB3 `onOpenProject`, R_M14 `openProj`) : la liste des projets ouvre par `surete` → `ouvrir` sur un compteur `{n,id,name}`, le second clic (« Créer et ouvrir ? ») est dans le popover ; `confirm:true` exige case cochée + estimation `ok` vue pour la même source + aucun texte connu, et la case se décoche à chaque envoi confirmé.
5. **D-34** : note 0–5 sur les RENDUS (jobs), en base : colonne `jobs.rating INTEGER` par la migration existante (liste de paires + `_auto_migrate`), `PUT /api/jobs/{job_id}/rating {rating:0..5}` (0 = sans note), `_job_to_dict` rend `rating`, `list_jobs(min_rating=0)` filtre AVANT le `limit`, `GET /api/jobs?min_rating=` ; transfert entre machines : colonne tolérée (mesurer `transfert.py:355`). Client : dans chaque ligne du tiroir Médias, cinq étoiles cliquables (`stopPropagation`, le glisser de la ligne reste intact), chip de filtre « ★ 3+ » (et « ★ 5 » = Good Take) qui passe `min_rating` au serveur. Écart daté : l'écran Bibliothèque et les images (`library_assets`) n'ont pas encore d'étoiles — plan Bibliothèque du 03/09 (P1 `libmeta`), la colonne est prête à y être lue ; les favoris localStorage `dz_fav_renders` ne sont pas migrés. Mesurer le pin `__dzMontageAdd` ×5/×7 de `test_library_sendto.py` et le réaligner s'il est rouge sur main (écart daté, pas dû à ce lot).

## Tâche 1 — D-37 export EDL + FCPXML

**Fichiers :** créer `backend/app/services/edl_export.py`, `backend/tests/test_montage_l7b.py` (section [1]) ; modifier `montage_service.py` (route), `montage.js` + patcher (entrées de menu, section `L7Ba…` ou repli dans la construction du menu ☰ `dzMenuProps`), bancs édition/bundle/ergonomie.

- [ ] Étape 1 : WebFetch de la documentation FCPXML d'Apple (developer.apple.com, « FCPXML Reference ») → version courante et forme minimale d'un `asset-clip`, `format`, `timeMap` ; dater dans le docstring du service.
- [ ] Étape 2 : banc rouge [1] : projet de test (deux plans V1 de sources vidéo testsrc2 générées en TMP, srcIn 1,0 et 0,0, le second en `fade` 0,4 ; une voix A1 ; un titre t1 ; une vitesse ×2 sur un plan) → lignes EDL exactes (timecodes à la main, commentaires), FCPXML parsable par `xml.etree` (références résolues, durées `^\d+/30s$|^0s$`, `src` `file:///`), route (espion `_load_saved`) 200 + `Content-Disposition`, 400 sans timeline et format inconnu.
- [ ] Étape 3 : service + route ; banc vert ; bancs voisins.
- [ ] Étape 4 : client (deux entrées ☰ › Projet avec `title`, `fetch` → `subsDownload(nom+".edl"|".fcpxml", texte, mime)`, refus dit par `fireNote`) ; édition/bundle/ergonomie ; rejeu chaîne ; commit `montage : D-37 - export EDL et FCPXML`.

## Tâche 2 — D-42 découper aux changements de plan

**Fichiers :** créer `backend/app/services/scenes.py` ; `test_montage_l7b.py` [2] ; route ; `montage.js` (`dzmCutAt`, export `cutAt`) ; patcher (entrée du menu contextuel de clip E-6) ; édition [32], bundle, ergonomie.

- [ ] Banc rouge [2] : deux sources testsrc2/testsrc de 2 s concaténées en TMP → `detect` rend une coupe à 2,0 ± 1/30 s (relatif au début lu), avec `srcIn=0.5` → 1,5 ; source uniforme → `[]` ; cache (deuxième appel sans ffmpeg : espion) ; route 404 source inconnue.
- [ ] Banc [32] de `dzmCutAt` : trois coupes → quatre clips, `srcIn` recalés ×speed, ids uniques même à < 0,1 s, bords 0,05 ignorés, verrou → refus, clip absent → refus, pur.
- [ ] Service, route, cœur, entrée de menu (clip vidéo seulement, grisée sinon, `title`), note « n coupes » ; commit `montage : D-42 - decouper aux changements de plan`.

## Tâche 3 — D-40 recadrage : backend

**Fichiers :** créer `backend/app/services/reframe.py` ; `test_montage_l7b.py` [3] ; `montage_service.py` (`_reframe_of`, chaîne cover V1, route).

- [ ] Étape 1 : MESURE ffmpeg d'un `crop=…:x='…t…'` sur la chaîne cover réelle (avec et sans vitesse/trim) ; consigner le résultat dans le docstring ; si refus, repli `sendcmd` (modèle D-14) et écart daté.
- [ ] Banc rouge [3] : tracker (carré qui traverse → `suivi`, erreur ≤ 8 % ; statique → `centre`) ; `_reframe_of` (bornes, 240 points, modes) ; commande : sans champ octet pour octet, `manuel` → `x` constant, `suivi` → expression ; rendu réel 9:16 d'une source 16:9 où le carré reste dans le cadre à trois instants (pixel mesuré) ; route.
- [ ] Service, champ, route ; bancs l7b, l7, l4, l3, l2 ; commit `montage : D-40 - recadrage par energie de mouvement (backend)`.

## Tâche 4 — D-40 recadrage : client

**Fichiers :** `montage.js` (`dzmReframeOf` pur, export), patcher (section « Cadrage » dans l'inspecteur de clip V1, `renderPayload`, aperçu vivant), `montage.css`, édition [33], bundle, ergonomie.

- [ ] Cœur `dzmReframeOf(c)` (bornes identiques au backend), banc [33].
- [ ] Inspecteur : trois boutons de mode + curseur x + « Analyser le mouvement » (`POST /reframe`, note pendant l'analyse, refus dit) ; historique par rafale comme les autres champs ; `renderPayload` émet `reframe` seulement s'il n'est pas `centre` sans x ; aperçu vivant (`object-position` en %, points interpolés à la tête) ; titles (E-12) ; commit `montage : D-40 - cadrage dans l inspecteur (client)`.

## Tâche 5 — D-41 auto-clips : backend

**Fichiers :** créer `backend/app/services/autoclips.py` ; `test_montage_l7b.py` [4] ; routes.

- [ ] Banc rouge [4] (sans réseau) : `windows` (durées 15–60, fin sur ponctuation forte) ; LLM factice → scores et `source=="llm:fake"` ; JSON cassé / `None` → heuristique déterministe, n clips ; segments dans la fenêtre ; route `autoclips` avec `text` (align gratuit, espion : `transcribe` jamais appelé) ; sans texte et sans `confirm` → `{ok:false, estimate}` et `transcribe` jamais appelé ; `create` → projet lisible par `GET /projects/{pid}` avec V1/S1 décalés.
- [ ] Service + routes ; bancs projets, l7b ; commit `montage : D-41 - auto-clips, fenetres, score LLM et repli heuristique (backend)`.

## Tâche 6 — D-41 auto-clips : client

**Fichiers :** `montage.js` (`DzmAutoclips` composant, lit `r`/`x` à l'appel), patcher (accès depuis le tiroir Médias et/ou ☰), `montage.css`, édition [34], bundle, ergonomie.

- [ ] Popover : source (ligne choisie), texte connu optionnel, n (1–8), persona optionnelle ; « Estimer / Lancer » (sans case « payer » cochée, jamais `confirm`) ; liste des clips ; « Créer le projet » → ouverture ; refus et coûts dits ; commit `montage : D-41 - auto-clips dans le tiroir Medias (client)`.

## Tâche 7 — D-34 note ★ des rendus

**Fichiers :** `backend/app/services/storage.py` (colonne), `pipeline.py` (`list_jobs(min_rating)`), `backend/app/api/routes.py` (`PUT /jobs/{id}/rating`, `_job_to_dict`, `GET /jobs?min_rating=`), `test_montage_l7b.py` [5], `montage.js` (étoiles + chip dans `DzmMediaDrawer`), bundle/édition/ergonomie, `test_library_sendto.py` (mesure du pin).

- [ ] Banc rouge [5] : migration sur une base TMP ancienne (colonne ajoutée, lignes intactes) ; PUT bornes (6 → 400, −1 → 400, « 3 » → 3 ?) ; `min_rating` filtre avant `limit` (pagination juste) ; `_job_to_dict` porte `rating` ; transfert tolère la colonne.
- [ ] Client : étoiles (5 boutons `title`, `stopPropagation`), chip ★ 3+ / ★ 5, rechargement de page ; commit `montage : D-34 - note etoile des rendus, filtre du tiroir Medias`.

## Tâche 8 — clôture L7-B

- [ ] `backend/tests/mutations_montage_l7b.py` (modèle `mutations_montage_l7.py`, ≥ 12, campagne entière, table des comptes dans le docstring) ; `test_montage_l7b_croise.py` (champs de clip lus par l'EDL == champs émis par `renderPayload` ; bornes `reframe` client == backend ; `min_rating` client == route ; menu : chaque entrée neuve a une action) ; conception datée l.111/119/129/130/178 + écarts ; plan coché ; revue finale ; PR ; mémoire par le contrôleur.
