# Retours du 26/09, Seedance 2.5, GPT Image 2.5, champs IA et dictée — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** corriger l'horloge du rendu (A), compléter l'aperçu étalonné à l'arrêt (B), montrer les scopes en plein écran (C), afficher le message du serveur à l'upload refusé (D), faire de Seedance 2.5 le modèle vidéo par défaut avec une garde de coût (F), ajouter GPT Image 2.5 Flare et Sunburst aux générations d'image (I), habiller les champs de saisie IA (G) et y permettre la dictée (H).

**Architecture :** le backend est modifié par fichiers disjoints : `montage_service`/`grading` pour A et B, `fal_service`/`pricing`/`routes` pour F, `image_providers`/`pricing`/`routes`/`material_store` pour I, et un service neuf pour la dictée. Le client passe par la couche `montage.js`/`montage.css` et par des sections du maillon `montage` (B, C, D, F5). G et H forment une couche globale neuve, `/shared/dz-champ-ia.js`, chargée par balise sans patcher le bundle.

**Tech :** FastAPI, ffmpeg 9.0.1 (app) et 8.1.1 (PATH), bundle Vite patché en octets (chaîne montage → dzcout), bancs sous python embarqué, Node pour les bancs JS, Playwright et Chrome sur 8799.

Conception : `docs/superpowers/specs/2026-09-26-retours-ia-design.md` (`ad6ad50`), plus la section I ajoutée le 27/09 (voir plus bas).

---

## Liste de contrôle

Le contrôleur coche une tâche après : revue de conformité, revue qualité, corrections, re-revue et bancs verts.

- [x] T1 — A : horloge du rendu (`fps` avec `start_time=0`, amorce après une coupe franche), bancs dorés réécrits (`3e01fbe`, revue `b536118` trou en tête + overlays V2 `start_time`, banc `554c71c` ; horloge 64/0 sous 9.0.1 ET 8.1.1)
- [x] T2 — B serveur : grade-frame avec retime blend/flow, stabilisation (`.trf` en cache, plafond 20 s), piste J1 (`_adjust_bounded` partagé) (`a4bbc5f`, `c6b4071`, revue `70ecf06` : recalage stab+retime, marge en images SOURCE, `format=yuv420p:color_ranges=tv`, `-threads 1` ; plafond stab = SOURCE ≤ 20 s (coût = `optzoom=1`) ; retours_grade 87/0)
- [x] T3 — B client et C : porte `dzmGlBody`, champs `cadre` neufs, pastille ; scopes portés dans l'élément plein écran (`a319ef5`, revue `6c4a353` porte J1 en miroir de la post-passe ; édition 660/0)
- [x] T4 — D et F5 : sections du maillon montage (`uploadVideo` lit `detail` ; défaut du nœud `seedance-2.5` et repli `dzVmCost`) (`437fba6` R7up1 + R7vm1..3 ; clôture `4462cf7` plafond 10 s de la vignette ; bundle 2383/0, r7 43/0)
- [x] T5 — F backend : `DEFAULT_VIDEO_MODEL` 2.5, estimation sans le repli 0,04, garde 402 (`max_usd` et plafond), durée générée plafonnée (`dc38d0d`, revue `8228e0e` : soumission fal unique, HeyGen dans la garde, non finis ; plafond 10 $ confirmé par l'utilisateur ; seedance_garde 96/0)
- [x] T6 — I backend : GPT Image 2.5 Flare et Sunburst, en direct et via fal ; routage des `-fal` avant le préfixe ; prix ; `MS.MODELS` ; coût du Materialforge (`fc2d7ad`, revue `8fc4a3b` : défaut figé, 502 fournisseur, fond transparent sunburst via fal ; gpt_image_25 145/0)
- [ ] T7 — H serveur : `/api/dictation/estimate` et `/api/dictation` (espion, 402, aucune transcription réelle)
- [x] T8 — G couche : `dz-champ-ia.js` (marquage par table, habillage variante B, reduced-motion), chargement SPA et pages à part, inventaire écran (`42927ea`, revue `5bc0c08` : défaire au détachement, repeinture au thème ; liseré peint par le champ, jamais de re-parentage)
- [x] T9 — G pastille de modèle, miroir du sélecteur de la vue (adaptateurs, clés absentes grisées) (`074b740`, revue `21f7cec` + `75e9659`)
- [x] T10 — H client : micro, voie 1 SpeechRecognition, voie 2 enregistrement puis estimation, dialogue et transcription (`339273b`, revue `8df4b4d` : Entrée = Non via `danger:true`, abandon caché/retiré/pagehide ; clôture `afdf017` ; champ_ia 252/0)
- [ ] T11 — clôture : mutations, banc croisé, bancs complets, preuves écran, conception et mémoire datées, revue finale, PR

## Ordonnancement

Fichiers partagés en série, fichiers disjoints en parallèle. Les revues tournent en arrière-plan sur le SHA figé (worktree temporaire et `.bak_*` copiés datés).

| Vague | Tâches | Fichiers |
|---|---|---|
| 1 | **T1** | `montage_service.py` : chaîne V1 et bancs dorés |
| 1 | **T5** | `fal_service`, `pricing`, `routes` (`/generate*` et layout), `schemas`, `pipeline` |
| 1 | **T7** | service neuf, `main.py` |
| 1 | **T8** | `frontend/shared/dz-champ-ia.js` et `index.html` |
| 1 | **T3** | couche `montage.js`/`montage.css` ; code écrit contre le contrat T2 ci-dessous |
| 2 | **T2** | après T1 : même `montage_service.py`, plus `grading.py` |
| 2 | **T6** | après T5 : `pricing.py` et `routes.py` partagés |
| 2 | **T4** | après T3 : patcher et bundle |
| 2 | **T9** | après T8 : même couche ; lit `/api/image-models` dynamique, donc indépendante de T6 |
| 3 | **T10** | après T9 et T7 |
| 4 | **T11** | en dernier |

Deux tâches ne peuvent pas éditer `routes.py` en même temps : T5, puis T6. T7 met ses routes dans un fichier neuf.

## Faits mesurés (26–27/09)

Relevés en lecture seule ; les scripts sont dans le scratchpad de la session (`avance/`, `inventaire/`).

**A. Avance d'une image.** Résultats identiques sous 9.0.1 et 8.1.1.
- Première cause : la chaîne `fps={fps}` (l.3589, 3622, 3626) démarre sur une image dont le pts vaut plus de 0. `trim` garde alors 29 images sur 30, et `setpts=PTS-STARTPTS` recule tout d'une image.
- Seconde cause : `_XFADE["cut"]=("fade",0.04)` (l.160) chevauche deux plans jointifs sans compensation. L'effet est cumulatif : 3 plans à 25 i/s donnent 31 images sur 90.
- Correctif essayé sur copie (`scratchpad/avance/correctif_AB2.diff`) : il rend 30/30, 60/60 et 90/90, et les ASS s'affichent des images 30 à 59.
- Les 18 bancs de référence sont verts sur `e0ab545`. Avec le correctif, 26 lignes dorées virent au rouge : l3 (11), l5_masque (6), l6 (4), retours_musique (4) et retours_grade r5 (1).

**B. Aperçu étalonné.**
- `dzmGlBody` (montage.js l.8420-8429) renvoie `null` sans effet actif.
- `t` porte déjà la vitesse (`dzmSrcTimeAt` l.7940).
- `_cadre_pre` (montage_service l.5950-5972) : « sans vitesse ni retime ni stabilisation ».
- Retime : `_RETIME` (l.1577). Stabilisation : `_v1_stab` et `_v1_stab_trf` (l.1592, 1608), cache `MM.stab_path` (montage_media l.379).
- Ajustement : post-passe l.4329-4362.
- La route grade-frame est aux l.6069-6094, et `grading.graded_frame` aux l.367-403.
- D-14 porte seulement sur les overlays V2, que le lecteur anime déjà (KF1, KF5).

**C. Plein écran.**
- `DzmScopes` (montage.js l.8825-8902) fait un portail vers `closest(".dzsvm")`.
- `svmFullscreen` met `.svm-frame` en plein écran (son-vfx-montage.js l.2094) ; le bundle n'a aucun écouteur `fullscreenchange`.
- La règle CSS `.dzsvm>.dzm-scwin` (montage.css l.1635) vise un enfant direct.

**D. uploadVideo.** La chaîne minifiée est unique dans le bundle et dans `.bak_montage` :

```
uploadVideo:async e=>{try{const t=new FormData;t.append("file",e);const n=await fetch(`${Te}/videos/upload`,{method:"POST",body:t});return n.ok?await n.json():{ok:!1,error:`HTTP ${n.status}`}}
```

Le motif court `return n.ok?await n.json():{ok:!1,error:`HTTP ${n.status}`}` apparaît deux fois : ne jamais l'utiliser seul. Deux appelants : le nœud UGC du Studio et la Library.

**F. Seedance.**
- `seedance-2.5` est au registre (`fal_service.py:94`), tarifé 480p 0,2205 et 720p 0,473 (`pricing.py:59`). Le défaut reste `seedance-v1-pro` (`fal_service.py:63`, épinglé par `test_video_models.py:41`).
- `pricing.estimate` retombe sur 0,04 $/s si le modèle est vide (l.242-254, 283, 381).
- Aucune garde sur `/generate` (routes l.2962), `/generate/batch` (3002), `/generate/composition` (3248), ni sur le rendu de layout (157).
- La prop par défaut V1 du nœud vaut `"seedance-v1-pro"` (bundle vers l'octet 179221, patcher `videomodel`) ; `dzVmCost` a un repli, `dzVmRates` est en dur.
- `@retry(stop_after_attempt(3))` sur `generate_video` (l.328) comporte un risque de refacturation.
- La doc fal lue le 26/09 : durée `auto` ou 4–30 s, pas de seed en entrée, `generate_audio` sans effet sur le prix.

**I. GPT Image 2.5.** Doc lue le 27/09 :
- Modèles OpenAI `gpt-image-2.5-flare` et `gpt-image-2.5-sunburst` (instantanés `-2026-09-08`), sur `v1/images/generations` et `v1/images/edits`.
- Qualités low, medium, high, xhigh, max et auto ; tarif token identique à GPT Image 2.
- Endpoints fal : `openai/gpt-image-2.5/{flare|sunburst}/{text-to-image|edit}`.
- Prix fal par image, en 1024² : medium 0,01317, **high 0,05268 (défaut fal)**, max 0,21072. En 1024×1536 high : 0,04116.
- Flare accepte le fond transparent.

État du dépôt :
- `image_providers.PROVIDERS` (l.23-39) contient `gpt-image-2` et `gpt-image-2-fal`.
- La façade route `gpt-image-2-fal` AVANT le préfixe `gpt-image` (l.199-217).
- **`/images/generate` (routes l.4807) et `/materials/generate` (l.8031) testent `startswith("gpt-image")`** et partent chez OpenAI : c'est pourquoi `gpt-image-2-fal` n'est pas dans `/image-models`.
- `nano-banana-pro` retombe sur FLUX dans `/images/generate` (l.4846) et sur Kontext dans l'édition de `/images/process` (l.5068), sans rien dire.
- `material_store.MODELS` (l.155) est en dur, et `clean_model` ramène un id inconnu à `flux`.
- `pricing._IMAGE_MODELS` (l.103-115) : un id absent est estimé au prix FLUX sans rien dire.
- `materialforge.js` (l.131-138) a `MODEL_COST`/`MODEL_SEC` en dur.
- Tous les sélecteurs lisent `/api/image-models` ou `/api/atelier/providers` : Studio, Réglages, Cardforge, Materialforge, Atelier.
- **Sprites, pixel-art et tuiles ne génèrent aucune image** : ils partent d'une image de la Library, produite par le générateur global. Ils sont donc couverts par le registre.
- Les bancs qui touchent la liste : `test_cards_face.py:2978-3075` (signature de `build_fal_gpt_request` à préserver), `test_style_da.py:56-69`, `test_images_process.py:145-204`, `test_image_model_default.py:97-116`, et `test_cards_frame.py:6504-6547` (aucun id en dur dans `frame.py`).

**G/H.**
- 36 champs IA relevés ; le périmètre validé couvre les générations média, soit environ 24 champs (conception §G).
- Le Studio vit sous `.dz-studio-grid`.
- Les pages à part chargent `/shared/dialogue.js`, sauf le Vectorlab (`mod-dialogue.js` via `core.js`).
- Aucun `SpeechRecognition` dans le dépôt.
- `transcribe_service.transcribe(audio_path, provider, language, timeout)` (l.1007) et `estimate_transcription` (l.941) : Scribe 0,0067 $/min, whisper-1 0,006 $/min.
- L'enregistreur D-26 est dans montage.js (l.8740-8760).

**Chaîne des patchers.**
- `.bak_montage` (21/09) et `.bak_dzcout` (26/09) ont été copiés avec `cp -p` depuis epic-fermi après un `cmp` nul du bundle (`c45244ef`).
- `repatch_all.py --list` affiche montage OK et dzcout OK.

## Décisions ajoutées le 27/09 (section I, validée par l'utilisateur)

- **Quatre entrées :**

  | Id | Voie | Clé |
  |---|---|---|
  | `gpt-image-2.5-flare` | OpenAI | OPENAI_API_KEY |
  | `gpt-image-2.5-sunburst` | OpenAI | OPENAI_API_KEY |
  | `gpt-image-2.5-flare-fal` | fal | FAL_KEY |
  | `gpt-image-2.5-sunburst-fal` | fal | FAL_KEY |

  Libellés : « GPT Image 2.5 Flare » et « GPT Image 2.5 Sunburst », suivis de « (OpenAI) » ou « (via fal) ».
- **Qualité et prix.** La qualité reste `high` sur les deux voies, comme le défaut fal, pour un prix fixe par image de 0,053 $ (1024², high).
  - Clés `gpt_image_25_flare_usd`, `gpt_image_25_sunburst_usd`, `gpt_image_25_flare_fal_usd` et `gpt_image_25_sunburst_fal_usd`, toutes à 0,053.
  - Écart daté : pas de tarification par qualité ni par taille, et pas de contrôle de qualité à l'écran.
- **Transparence.** Le paramètre `background` est accepté par `image_providers` (flare seulement, avec `output_format` png) et par `/images/generate`, mais aucun contrôle n'est ajouté à l'écran dans ce lot (écart daté). Sprites et pixel-art passent déjà par rembg.
- **Routage.** Tout id dont `PROVIDERS[id]["needs"] == "FAL_KEY"` passe par `IP.generate` AVANT le test de préfixe, dans `/images/generate`, `/materials/generate` et `/images/process`. `gpt-image-2-fal` entre alors aussi dans `/image-models`. Les défauts voisins sont corrigés au passage parce qu'ils sont sur les mêmes lignes : `nano-banana-pro` routé vers son fournisseur, `MS.MODELS` complété.
- **Hors lot, daté :**
  - l'éditeur de tarifs des Réglages du bundle ne gagne pas les nouvelles clés (il ne connaît déjà ni les prix fal ni Nano Banana) ;
  - la série Cardforge ne gagne pas de marche 2.5 (décision de l'utilisateur).

## Conventions

Ce sont celles des plans L6 et des retours L6.
- **Bancs.**
  - Un banc par processus depuis `backend/`, sous python embarqué `C:\Users\olivi\AppData\Local\DeepotusVideoGen\runtime\python\python.exe`.
  - Lecture par le code de sortie et par la ligne `=== N passed, M failed ===`.
  - `check(label, cond, detail)`, assertions négatives avec témoin positif, état vide, faute n°6 (le détail est évalué avant `cond` : parade `_attendu`).
- **Patchers.**
  - Ancres comptées sur `.bak_montage` (1/0/1) ; une ancre consommée se replie dans le remplacement hôte.
  - Sections neuves préfixées **`R7`**, en groupe posé en queue après `R6`, avec les pins de queue réalignés EN LE DISANT (`_PQ`, `_DZ_TAGS`, `len(PATCHES)`).
  - `--check --force-unchained`, `node --check`, sonde dzcout remesurée.
- **Couche et interface.**
  - Couche `montage.js` en LF.
  - Règle E-12 : tout bouton a un `title` ; on grise, on n'échange jamais deux boutons par ternaire.
- **Édition et commits.**
  - `montage_service.py` s'édite seulement avec Edit ou Write (jamais `sed -i`), et jamais par heredoc pour du code.
  - Commits par `git commit --only <chemins>`, première ligne sans accent, trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, push.
  - Jamais `git checkout --`, `git stash` ni `git add -A`.
- **Interdits.**
  - Aucun serveur 8765.
  - Aucune dépense : espions sur `FalSeedanceClient`, `IP._openai_generate`, `IP._fal_gpt_generate` et `transcribe`. Jamais `/api/audio/voiceover` ni `/api/audio/sfx` dans un banc.
  - Ne pas toucher aux fichiers de `chantier/motion-design`.
- **Contester le plan.** Chaque agent conteste le plan par la mesure : un démenti mesuré prime, et il est dit dans le rapport.

---

## Tâche 1 — A : horloge du rendu

**Fichiers :** `backend/app/services/montage_service.py`. Bancs réécrits : `test_montage_l3.py`, `test_montage_l5_masque.py`, `test_montage_l6.py`, `test_retours_musique.py`, `test_retours_grade.py` (r5). Banc neuf : `backend/tests/test_retours_horloge.py`.

- [ ] **Étape 1 — banc neuf rouge.** `test_retours_horloge.py` rend sous les deux ffmpeg une source de synthèse numérotée (luminance par image, 64×32), sans aucun appel réseau, en appelant `_build_montage_command` comme les bancs l3 et l7. Il compare le nombre d'images, l'index de la première image de chaque plan et le numéro de la première image source.
  - **Cas :** 1 plan à `in` 0 (témoin vert avant ET après) ; 1 plan à `in` 0,5 avec source à 25 i/s ; 1 plan de 2 s à `in` 0,37 ; canevas 25 i/s ; vitesse ×0,5 flow, puis blend ; zoom dz ; 2 plans en coupe ; 3 plans en coupe à 30 et à 29,97 i/s ; 3 plans à 25 i/s avec `in` 0,5 / 2,3 / 4,1 ; 2 plans avec un trou (inchangé) ; ASS de 1,00 à 2,00 s, présent sur les images 30 à 59.
  - **Contrôles :** n = attendu ; j0 = `start·fps` ; img0 = image `in` ; écart médian 0.
  - **Témoin :** la chaîne de `e0ab545` (lue par `git show e0ab545:backend/app/services/montage_service.py` et importée dans un module temporaire) donne +1 sur les cas désalignés et 31/90 sur le pire cas.
  - Lancer : rouge attendu.
- [ ] **Étape 2 — correctif.**
  - `fps={fps}` devient `fps={fps}:start_time=0` aux trois poses de la chaîne V1 : préfixe `sf`, variante vitesse et variante recadrage/zoom. Remesurer les numéros de ligne.
  - Sur tout plan V1 qui suit DIRECTEMENT un autre plan par une coupe (`cut`, τ = 0,04), après ses effets et son masque : `[n{k}l]tpad=start_mode=clone:start_duration=0.04[n{k}]` et `seg_durs[k] += 0.04`, pour que l'offset du xfade tombe sur `start`.
  - Les trous et les vraies transitions ne changent pas.
  - Mesurer que `total` égale la timeline (`/render` et `/measure`).
- [ ] **Étape 3 — banc vert, sous 9.0.1 ET 8.1.1** : PATH préfixé par `%LOCALAPPDATA%\DeepotusVideoGen\bin`, puis sans.
- [ ] **Étape 4 — réécrire les 26 lignes dorées.** Les chaînes `"fps=25,"` deviennent `"fps=25:start_time=0,"`. Les commandes dorées de 81bfde3, 62f0c75 et L6-T1 sont reconstruites en appliquant le correctif à l'ancienne commande : une transformation écrite dans le banc, pas une nouvelle constante recopiée.
  - r5 de retours_grade passe à `|k| ≤ 1` en 1/150 s, avec un témoin qui prouve que l'ancienne chaîne donnait `k ≥ 5`.
  - Aucune borne ne s'assouplit ailleurs.
- [ ] **Étape 5 — bancs l2, l3, l3_croise, l4, l4_croise, l5, l5_masque, l6, l7, l7b, pistes_rendu, pistes_dyn, remplacer, retours_grade, retours_musique, retours_croise, subs_animes, subtitles_burn** : tous à 0 échec. Référence sur `e0ab545` : l2 78, l3 86, l3_croise 25, l4 120, l4_croise 20, l5 109, l5_masque 60, l6 110, l7 33, l7b 163, pistes_rendu 33, pistes_dyn 20, remplacer 99, retours_grade 47, retours_musique 31, retours_croise 21, subs_animes 65.
- [ ] **Étape 6 — commit** : `montage : horloge du rendu - fps depuis 0 et coupe franche compensee`.
- **Écarts à dater dans le rapport :** un vrai fondu (τ > 0,04) avance encore les plans suivants de τ ; un trou suivi d'un plan en coupe avale la première image du plan.

## Tâche 2 — B serveur : grade-frame avec retime, stabilisation et J1

**Fichiers :** `backend/app/services/montage_service.py` (route grade-frame, `_cadre_of`, `_cadre_pre`, extraction de `_adjust_bounded` des l.4341-4357), `backend/app/services/grading.py`. Bancs : `backend/tests/test_retours_grade.py` étendu (sections [6] et suivantes), `test_montage_l3.py` et `test_montage_l3_croise.py` (identité de la commande de rendu).

**Contrat, lu par T3 :**
```
POST /api/montage/grade-frame  {src, t, effects?, mask?, w?, cadre?}
  cadre += {speed?: float (défaut 1), retime?: "none"|"blend"|"flow", fps?: int (défaut 30),
            stab?: <objet stab du clip, tel que le rendu le lit>,
            adjust?: [{start: float, end: float, effects: [...]}], t_global?: float}
  réponse : image/jpeg ; en-tête X-Dz-Grade-Note (facultatif, virgules) ∈ {stab-non-analysee, stab-trop-loin}
```

- [ ] **Étape 1 — contrôles rouges** dans `test_retours_grade.py`.
  - [6] speed 0,5 + blend : l'image est celle du rendu Preview réel au même instant (écart moyen ≤ 6/255), et le témoin sans retime s'en écarte de plus de 6.
  - [7] Même chose en flow.
  - [8] Mire secouée, avec `.trf` précalculé par `MM.stab_detect` (local, gratuit) : l'image est proche du rendu stabilisé, et le témoin non stabilisé s'en écarte.
  - [9] Sans `.trf` : la note vaut `stab-non-analysee`, et un espion sur `stab_detect` prouve ZÉRO appel.
  - [10] `t_src` > 20 s : note `stab-trop-loin`, aucun décodage depuis 0 (espion sur `_run`, durée).
  - [11] Clip J1 couvrant la tête (négatif) : pixel inversé, alors qu'un J1 hors tête ne change rien. Il est appliqué APRÈS le masque V1 : masque ellipse, avec un coin affecté par J1 mais pas par la pile V1.
  - [12] Sans les champs neufs : l'image est octet pour octet celle d'aujourd'hui, et le mtime du `.trf` entre dans la clé de cache.
- [ ] **Étape 2 — implémenter.**
  - `_adjust_bounded(aj, total)` est extrait et la post-passe de rendu l'utilise : la commande de rendu est identique octet pour octet, ce que prouvent l3 et l3_croise.
  - Retime : fenêtre alignée `tw = floor((t_local − m/F)·F)/F` (m = 2 pour blend, 4 pour flow), `-ss (srcIn + tw·spd)`, puis `setpts=PTS/spd`, minterpolate de `_RETIME` si flow, `fps=F:start_time=0`, tblend de `_RETIME` si blend, puis `setpts=PTS-STARTPTS+tw/TB`, `select=gte(t,t_local-1/(2F))`, `-frames:v 1`.
  - Stabilisation : seulement si `MM.stab_path(p).exists()` et `t_src ≤ 20`. `-i src` sans `-ss`, puis `vidstabtransform` avec les paramètres de `_v1_stab`, `trim=start=t_src`, `setpts`, puis `_cadre_pre`.
  - J1 : effets présents à `t_global`, `_pile`, chaînés après `[gout]`.
  - Mesurer le temps de flow à 720 px et le dire.
- [ ] **Étape 3 — bancs retours_grade, l3, l3_croise, l5 et retours_croise verts, sous les deux ffmpeg.**
- [ ] **Étape 4 — commit** : `montage : apercu a l arret - retime, stabilisation en cache et piste d ajustement`.

## Tâche 3 — B client et C : porte d'aperçu, champs du cadre, scopes en plein écran

**Fichiers :** `frontend/patches/montage.js` (LF), `frontend/dist/shared/montage.css`, rejeu `scripts/repatch_all.py --from montage` (montage.js est injecté par M1). Bancs : `backend/tests/test_montage_edition.py` (`r6_*`, `r6s_*`), `test_montage_bundle.py`, `test_montage_ergonomie.py`.

- [ ] **Étape 1 — contrôles rouges.**
  - **Édition, B0.** Un plan avec seulement `retime` (vitesse ≠ 1), seulement `stab.on`, ou seulement un clip J1 dont l'effet est actif à la tête, produit une requête. Un plan sans rien n'en produit AUCUNE (témoin de l'état vide). Le corps porte exactement `cadre.speed`, `cadre.retime`, `cadre.fps`, `cadre.stab`, `cadre.adjust` et `cadre.t_global`. J1 se repère par `dzmKindOf(c.tr, c.kind) === "adjust"`.
  - La pastille affiche ce qu'elle applique (étalonné, vitesse, stabilisation, ajustement), plus la note serveur lue dans `X-Dz-Grade-Note` (« stabilisation non analysée », « stabilisation : trop loin dans la source »).
  - L'anti-rebond passe à 600 ms quand `stab` est posé, 250 ms sinon.
  - La largeur mesurée entre dans l'empreinte, par paliers de 160 px, pour que le plein écran ne garde pas une image de 720 px étirée.
  - **Édition, C.** Faux `document.fullscreenElement` et faux `add/removeEventListener("fullscreenchange")`. Le portail passe dans l'élément plein écran quand `.dzsvm` le contient, et revient à la racine en sortie. La géométrie est recadrée aux dimensions de la cible sans rien écrire dans `dz_montage_scopes_geo`. Un geste en cours est abandonné. L'écouteur est retiré au démontage. Un plein écran d'un autre élément, hors `.dzsvm`, ne change rien.
  - **Bundle.** Règle CSS `.dzsvm>.dzm-scwin,.dzsvm .svm-frame>.dzm-scwin{` comptée exactement 1. Compteurs `x.useState(` (578 → mesurer) et `DzTracks` (178), réalignés EN LE DISANT.
- [ ] **Étape 2 — implémenter** dans `dzmGlBody`, `DzmGradeLive` et `DzmScopes` (ref `cibleR`, `saisir` et `dzmTbVeille` lisent `cibleR.current`), plus la CSS.
- [ ] **Étape 3 — rejouer la chaîne et vérifier.** `python scripts/repatch_all.py --from montage`, puis `--list` (montage OK, dzcout OK), `node --check`, puis les bancs édition, bundle et ergonomie verts.
- [ ] **Étape 4 — commit** (montage.js, montage.css, bundle, bancs) : `montage : apercu a l arret sans effet requis et scopes en plein ecran`.

## Tâche 4 — D et F5 : sections du maillon montage

**Fichiers :** `scripts/patch_bundle_montage.py` (groupe `R7`), bundle rejoué. Bancs : `test_montage_bundle.py`, plus un banc neuf `backend/tests/test_retours_bundle_r7.py`.

- [ ] **Étape 1 — contrôles rouges.**
  - **R7up1.** L'ancre D complète vaut 1 dans `.bak_montage` et 0 après remplacement. Le remplacement est :
    ```
    uploadVideo:async e=>{try{const t=new FormData;t.append("file",e);const n=await fetch(`${Te}/videos/upload`,{method:"POST",body:t});if(n.ok)return await n.json();let d="";try{const j=await n.json();d=typeof(j&&j.detail)=="string"?j.detail:""}catch(x){}return{ok:!1,error:d||`HTTP ${n.status}`}}
    ```
    Le banc exécute la fonction extraite sous Node avec un faux `fetch` : 415 `{detail:"Fichier vide ou illisible : a.mp4 (vide)"}` → `error` = ce texte ; 500 sans JSON → `HTTP 500` ; 200 → le JSON. Le témoin : l'ancienne fonction rend `HTTP 415`.
  - **R7vm1.** La prop par défaut du nœud Seedance, `"seedance-v1-pro"`, devient `"seedance-2.5"`. Mesurer le jeton exact et son compte sur `.bak_montage` ; s'il n'est pas unique, élargir l'ancre. Même traitement pour le repli de `dzVmCost` (tarif 2.5 à 720p, 0,473) et le libellé « Défaut (… ». Les graphes enregistrés ne changent pas : le défaut ne s'applique qu'aux props absentes, à vérifier sous Node.
- [ ] **Étape 2 — sections en queue, groupe `R7` après `R6`**, avec `_PQ`, `_DZ_TAGS` et `len(PATCHES)` réalignés EN LE DISANT. Puis `--check --force-unchained`, rejeu `--from montage`, `--list` OK, `node --check`, et sonde dzcout remesurée.
- [ ] **Étape 3 — bancs bundle, R7, édition et ergonomie verts.**
- [ ] **Étape 4 — commit** : `montage : upload refuse lisible et seedance 2.5 par defaut dans le studio`.

## Tâche 5 — F backend : Seedance 2.5 par défaut et garde de coût

**Fichiers :** `backend/app/services/fal_service.py`, `backend/app/services/pricing.py`, `backend/app/api/routes.py` (`/generate`, `/generate/batch`, `/generate/composition`, `/layout-templates/{id}/render`), `backend/app/models/schemas.py`, `backend/app/services/pipeline.py`. Bancs : `backend/tests/test_video_models.py` réécrit, plus un banc neuf `backend/tests/test_seedance_garde.py`.

- [ ] **Étape 1 — contrôles rouges.**
  - `DEFAULT_VIDEO_MODEL == "seedance-2.5"`.
  - `pricing.estimate` avec un modèle vide ou absent donne le tarif 2.5 à la résolution demandée (720p → 0,473 $/s), jamais 0,04. Même chose pour l'estimation épisodes et pour le plan marketing (l.283, l.381 : mesurer ce qu'ils estiment).
  - **Garde.** `POST /generate` avec `max_usd` inférieur à l'estimation serveur → 402, avec un `detail` qui nomme le montant (« Estimation 4,73 $ > plafond 1,00 $ »). Sans `max_usd`, le plafond `pricing.json` `video_max_usd_per_request` (défaut 10) s'applique. `/generate/batch` estime la somme des variations. `/generate/composition` et le rendu de layout suivent la même règle.
  - Espion sur `FalSeedanceClient.generate_video` : **zéro appel** en cas de refus ; un appel, espionné et sans réseau, en cas d'accord.
  - La durée envoyée à fal est plafonnée à `video_max_gen_s` (défaut 10). Le reste est prolongé par ffmpeg comme aujourd'hui : mesurer le chemin `clamp_duration`.
  - L'ancien défaut `seedance-v1-pro` reste choisissable.
  - État vide : un `pricing.json` absent donne les défauts.
- [ ] **Étape 2 — implémenter.**
  - Le commentaire « audio-off pricing column » est retiré pour 2.5.
  - Le retry après soumission est mesuré et dit. S'il resoumet une génération déjà acceptée, le limiter à une erreur AVANT soumission, avec un test.
- [ ] **Étape 3 — bancs.** `test_video_models`, `test_seedance_garde`, et tout banc qui importe `pricing` (`grep -l pricing backend/tests`) verts.
- [ ] **Étape 4 — commit** : `video : seedance 2.5 par defaut, estimation juste et garde de cout serveur`.

## Tâche 6 — I backend : GPT Image 2.5 Flare et Sunburst

**Fichiers :** `backend/app/services/image_providers.py`, `backend/app/services/pricing.py`, `backend/app/api/routes.py` (`/image-models` l.~5225, `/images/generate` l.~4807, `/images/process` l.~5068, `/materials/generate` l.~8031), `backend/app/services/material_store.py`, `frontend/materialforge/materialforge.js` (`MODEL_COST`/`MODEL_SEC`). Banc neuf : `backend/tests/test_gpt_image_25.py`. Bancs existants gardés verts : `test_cards_face.py`, `test_style_da.py`, `test_images_process.py`, `test_image_model_default.py`, `test_cards_frame.py`.

- [ ] **Étape 1 — contrôles rouges.**
  - Les quatre ids sont dans `PROVIDERS` avec `needs` (OPENAI_API_KEY ou FAL_KEY), dans `pricing._IMAGE_MODELS` (0,053) et dans `MS.MODELS`. `clean_model` garde chacun des quatre, avec un témoin : un id inconnu donne `flux`.
  - `/image-models` : les deux directs apparaissent avec OPENAI_API_KEY, les deux `-fal` (plus `gpt-image-2-fal`) avec FAL_KEY, et aucun sans sa clé. Les clés sont simulées dans `settings`, jamais lues.
  - `build_fal_gpt_request` garde sa signature actuelle (épinglée par `test_cards_face`). Une variante renvoie `openai/gpt-image-2.5/flare/text-to-image`, ou `/edit` avec une image. `quality` vaut `high`. `background="transparent"` passe pour flare, est ignoré pour sunburst, et impose `output_format` png.
  - `build_openai_request("gpt-image-2.5-flare", …)` renvoie `model` = `gpt-image-2.5-flare`, `quality` = `high`, et `background` si demandé.
  - **Routage.** `/images/generate` avec `gpt-image-2.5-flare-fal` appelle `IP._fal_gpt_generate` (espion) et JAMAIS le chemin OpenAI ; sans OPENAI_API_KEY, ce n'est pas refusé. `/materials/generate` et `/images/process` suivent la même règle. `nano-banana-pro` part vers son fournisseur, pas vers FLUX ni Kontext : mesurer d'abord, et dater si le démenti tient.
  - `materialforge.js` : `MODEL_COST` et `MODEL_SEC` ont les quatre ids. Contrôle statique, plus un `node --check`.
  - Espions sur `_openai_generate` et `_fal_gpt_generate` : aucun appel réel.
- [ ] **Étape 2 — implémenter.** La façade route tout `needs == "FAL_KEY"` des familles gpt avant le préfixe, et les trois routes délèguent à `IP.generate` pour ces ids.
- [ ] **Étape 3 — banc neuf et les cinq bancs existants verts.**
- [ ] **Étape 4 — commit** : `images : gpt image 2.5 flare et sunburst, en direct et via fal`.

## Tâche 7 — H serveur : routes de dictée

**Fichiers :** service neuf `backend/app/services/dictation_service.py` (router FastAPI), `backend/app/main.py` (inclusion ; mesurer comment les autres routers sont montés). Banc neuf : `backend/tests/test_dictation.py`.

**Contrat, lu par T10 :**
```
POST /api/dictation/estimate   multipart {file}          -> {duration_s, provider, usd, available: bool, reason?}
POST /api/dictation            multipart {file, max_usd, language?} -> {text, usd, provider}
  402 si usd recalculé > max_usd ; 415 prise vide ou illisible ; 503 {detail} si aucune clé (ELEVENLABS_API_KEY, puis OPENAI_API_KEY)
```

- [ ] **Étape 1 — contrôles rouges.**
  - La prise webm/ogg d'un bruit de synthèse (ffmpeg lavfi) est transcodée en WAV 16 k mono (patron `/audio/recording`). La durée est mesurée, et `usd` vient de `transcribe_service.estimate_transcription`.
  - 402 si `max_usd` < usd ; espion sur `transcribe_service.transcribe` avec ZÉRO appel en 402, 415 et 503.
  - En accord : un appel espionné qui rend le texte simulé.
  - Prise vide → 415. Aucune clé → 503 avec `detail`. Taille maximale de 25 Mo, sinon 413.
  - Le fichier temporaire est supprimé dans tous les cas.
  - `_require_localhost`, si les routes voisines l'utilisent : mesurer.
- [ ] **Étape 2 — implémenter.**
- [ ] **Étape 3 — banc vert**, avec `test_hygiene_imports.py` et `security_guards`.
- [ ] **Étape 4 — commit** : `dictee : routes d estimation et de transcription avec plafond`.
- Nouvelle route : l'utilisateur relancera le backend.

## Tâche 8 — G : couche des champs IA

**Fichiers :**
- Créer `frontend/shared/dz-champ-ia.js` et sa copie à l'octet près `frontend/dist/shared/dz-champ-ia.js` (modèle : `frontend/shared/dialogue.js` et `test_dialogue_bundle.py`).
- Modifier `frontend/dist/index.html`, ainsi que les `index.html` de `frontend/atelier/`, `frontend/cardforge/`, `frontend/materialforge/`, `frontend/spritelab/` et `frontend/vectorlab/`. Mesurer la ligne de `/shared/dialogue.js` et poser une ligne jumelle. Le Vectorlab n'a pas `dialogue.js` : on y ajoute une balise.

Banc neuf : `backend/tests/test_champ_ia.py`. Il lance Node sur un DOM minimal simulé : faux `document`, `MutationObserver`, `matchMedia`. Mesurer si le dépôt a déjà un shim DOM (bancs Vectorlab ou dialogue) et le réutiliser.

- [ ] **Étape 1 — contrôles rouges.**
  - `window.DzChampIA` expose `regles`, `marquer(racine)` et `version`.
  - La table des règles couvre le périmètre de la conception §G. Chaque règle porte `{id, vue, sel | libelle, genre: "video"|"image"|"anim"|"sfx"|"musique"|"3d"}`.
  - `marquer` pose `data-dz-ia=<genre>` sur les champs visés et habille un conteneur (`.dzia-hab`) sans déplacer le champ.
  - Il ignore tout ce qui est sous `.dz-studio-grid` : le témoin est un textarea « Prompt » du Studio, jamais marqué, alors que le Prompt du Quick l'est.
  - Il ignore les champs exclus : Voice Over, Narration, brief du Scheduler, Persona, `#script` de l'Atelier. Chacun a un témoin qui n'est jamais marqué.
  - Il est idempotent (deux passes, un seul habillage) et observe les ajouts.
  - `data-dz-ia` posé à la main est honoré.
  - Le `<style>` est injecté une seule fois. Il contient `@property --dzia-ang`, un `conic-gradient` avec #8b5cf6, #3b82f6 et #f97316, l'animation au `:focus-within` seulement, et `@media (prefers-reduced-motion:reduce)` qui coupe toute animation.
  - Les deux copies sont identiques à l'octet (non-dérive), et une ligne `<script src="/shared/dz-champ-ia.js">` figure dans chaque `index.html` visé.
- [ ] **Étape 2 — implémenter.**
  - Le repli par libellé cible le Prompt et le Script (HeyGen) du Quick : `parent.parent.firstElementChild` vaut « Prompt », ou le texte commence par « Script ( ».
  - L'habillage enveloppe par un conteneur posé autour du champ, ou par des pseudo-éléments d'un parent existant quand il est unique. Mesurer pour chaque règle que la mise en page hôte ne bouge pas : mêmes `offsetWidth`/`offsetHeight` du champ à ±1 px à l'écran.
  - Le texte garde son contraste.
- [ ] **Étape 3 — inventaire à l'écran** sur 8799 (Playwright et Chrome, `DEEPOTUS_DATA_DIR` dans le scratchpad), vue par vue.
  - Pour chaque vue : liste des champs marqués, capture au repos, capture au focus.
  - Mesurer l'absence de décalage de mise en page.
  - Un champ du périmètre absent ou un faux positif corrige la table.
  - Les captures vont dans le scratchpad.
- [ ] **Étape 4 — banc vert**, avec `test_dialogue_bundle.py` resté vert.
- [ ] **Étape 5 — commit** : `champs ia : liseré degrade et holographique au focus, table des champs`.

## Tâche 9 — G : pastille de modèle, miroir du sélecteur de la vue

**Fichiers :** `frontend/shared/dz-champ-ia.js` et sa copie `dist`. Banc : `test_champ_ia.py` étendu.

- [ ] **Étape 1 — contrôles rouges.**
  - La barre du champ contient un badge « IA », une pastille de modèle (bouton titré) et une place pour le micro (T10).
  - Chaque règle porte un adaptateur `modele: {liste: "video"|"image"|null, lire(champ) → id, ecrire(champ, id), fixe?: "libellé"}`.
    - La liste vient de `/api/video-models` ou de `/api/image-models`.
    - Un modèle `available:false` est grisé (`aria-disabled`), avec le `title` « clé FAL_KEY absente », « clé OPENAI_API_KEY absente » ou « clé GEMINI_API_KEY absente ».
    - Le prix est affiché comme dans la vue (`usd_per_s` en vidéo, prix par image via `/api/cost/estimate`) : mesurer ce que la vue affiche déjà.
  - **Synchronisation dans les deux sens.** Changer la pastille écrit dans le sélecteur natif de la vue : `localStorage.dz_video_model` pour le Quick, ou le select natif avec un événement `change` natif (setter du prototype pour React). Le sélecteur natif changé met la pastille à jour, par observation.
  - **Vues sans choix** (SFX, musique, 3D, Spritelab, Scheduler) : pastille grisée, libellé du modèle réellement utilisé (Seedance 2.5 par défaut après T5, ElevenLabs, Meshy…) et `title` « choisi par la vue ».
  - **E-12.** Tout bouton a un `title`. On grise, jamais d'échange de deux boutons par ternaire.
- [ ] **Étape 2 — implémenter. Mesurer d'abord, à l'écran, le sélecteur natif de chaque vue** : les selects du bundle sont custom, pas des `<select>` natifs, et un piège mémorisé impose de mesurer le texte du champ. Une vue dont le sélecteur ne peut pas être piloté sans patcher le bundle a une pastille en lecture seule, datée.
- [ ] **Étape 3 — banc vert et captures d'écran** : pastille, liste ouverte, modèle grisé sans clé (data8799 sans clé).
- [ ] **Étape 4 — commit** : `champs ia : pastille de modele synchronisee avec le choix de la vue`.

## Tâche 10 — H client : dictée

**Fichiers :** `frontend/shared/dz-champ-ia.js` et sa copie `dist`. Banc : `test_champ_ia.py` étendu.

- [ ] **Étape 1 — contrôles rouges.**
  - **Bouton micro**, `title` « Dicter — reconnaissance vocale du navigateur (l'audio part au service du navigateur) ».
  - **Voie 1**, si `SpeechRecognition || webkitSpeechRecognition` existe : `lang` = `document.documentElement.lang || "fr-FR"`, `interimResults` à vrai, `continuous` à vrai.
    - Le texte final est inséré AU CURSEUR (`selectionStart`/`selectionEnd`), avec un espace de séparation si besoin. La valeur passe par le setter du prototype (`HTMLTextAreaElement` ou `HTMLInputElement`), puis un événement `input` qui bulle, pour que React la voie.
    - Pendant l'écoute : classe `.dzia-ecoute`, texte « À l'écoute… (clic ou Échap pour arrêter) », et le bouton devient « ■ » titré « Arrêter la dictée ». C'est le même bouton : on change son état, sans ternaire de deux boutons.
    - Échap et clic arrêtent l'écoute.
  - **Voie 2**, si la voie 1 est absente, ou sur l'erreur `network` ou `service-not-allowed` :
    - `MediaRecorder` (patron D-26), puis `POST /api/dictation/estimate`.
    - Dialogue maison, avec `window.DzDialogue` s'il existe (mesurer l'API de `dialogue.js`) : « Transcrire 12 s par ElevenLabs Scribe ≈ 0,0013 $ ? ». Oui ou Non.
    - Sur Oui : `POST /api/dictation` avec `max_usd` = le montant affiché, puis insertion au curseur. Sur Non : RIEN n'est envoyé (espion `fetch`).
    - Si `available:false` : micro grisé en voie 2, avec le `title` de la raison.
    - Si `getUserMedia` est refusé : note lisible, pas d'exception.
  - Tout est testé sous faux `SpeechRecognition`, faux `MediaRecorder` et faux `fetch`. Aucune transcription réelle.
- [ ] **Étape 2 — implémenter.**
- [ ] **Étape 3 — mesurer la voie 1** dans Chrome sur `deepotus.localhost:8799` et sur `127.0.0.1:8799`, avec `--use-fake-device-for-media-stream` et `--use-fake-ui-for-media-stream` : présence du constructeur, et erreur éventuelle (`network` hors ligne, etc.).
  - Prouver la voie 2 jusqu'au dialogue, puis cliquer Non : zéro requête `/api/dictation`.
  - Une transcription réelle (≈ 0,001 $) N'EST faite QU'avec l'accord explicite de l'utilisateur, demandé par le contrôleur.
- [ ] **Étape 4 — commit** : `champs ia : dictee par le navigateur et repli transcrit avec accord`.

## Tâche 11 — clôture

- [ ] **Mutations.** `backend/tests/mutations_retours_ia.py`, sur le modèle de `mutations_retours_l6.py` avec `--pre-vol`, au moins 16 mutations en octets :
  - A : `start_time` retiré ; amorce omise ;
  - B : `.trf` fabriqué à la volée ; blend avant `fps` ; J1 avant le masque ;
  - C : pas de retour à la racine ; écouteur non retiré ;
  - D : `detail` ignoré ;
  - F : défaut v1-pro ; garde contournée ; 0,04 rétabli ;
  - I : `-fal` routé par le préfixe ; id absent de `MS.MODELS` ;
  - H : transcription sans `max_usd` ;
  - G : `.dz-studio-grid` non exclu ; reduced-motion retiré.
  - Toutes rouges ; patcher, bundle et `.bak_*` restaurés au sha256.
- [ ] **Banc croisé** `backend/tests/test_retours_ia_croise.py` :
  - champs `cadre` envoyés = champs lus ;
  - corps de dictée client = contrat serveur ;
  - ids de la pastille = ids de `/api/*-models` ;
  - tarif 2.5 du bundle = `pricing`.
- [ ] **Tous les bancs Montage et ceux touchés**, un par processus. Ceux de l'horloge et de grade sous les deux ffmpeg.
- [ ] **Preuves écran sur 8799 :**
  - rendu de 3 plans en coupe sans avance (images numérotées) ;
  - aperçu retime et J1 à l'arrêt ;
  - scopes visibles en plein écran ;
  - message 415 lisible dans le Studio et la Library ;
  - champs IA au repos et au focus ;
  - pastille grisée ;
  - dictée jusqu'au dialogue.
- [ ] **Documentation.** Conception datée (écarts), mémoire (`montage-vs-resolve-inventaire.md` et la ligne de `MEMORY.md`), revue finale (non-régression mesurée contre `main`), PR vers `main`.
- Fusion et déploiement SEULEMENT sur demande explicite de l'utilisateur.
