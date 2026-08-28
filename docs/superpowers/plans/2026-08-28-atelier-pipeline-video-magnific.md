# Atelier → film : combler le pipeline script→plan→image-clé→vidéo (benchmark Magnific)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans.
> Steps use checkbox (`- [ ]`) syntax. Ce document est un plan de
> COMPARAISON et d'OPTIMISATION : rien n'est codé avant validation.

> Spécification de référence : `magnific_workflow_storyboard_video_spec.md`
> (Downloads, 26 818 octets, relue intégralement le 28/08). Magnific y sert
> de **benchmark produit** ; l'architecture reste agnostique fournisseur —
> ce plan ne propose AUCUN connecteur Magnific (§15 de la spec exige une
> vérification au portail développeur d'abord).

**Goal :** faire que la préproduction déjà construite dans l'Atelier
(manuscrit → bible → scénario → voice-over minuté → storyboard croquis)
débouche sur un **film** — plan par plan, image-clé validée avant animation,
score de cohérence, retake ciblé, timeline — au lieu de s'arrêter au croquis.

**Architecture :** aucune brique neuve massive. On **relie** ce qui existe
(bible verrouillable ↔ scènes ↔ plans ↔ registre `VIDEO_MODELS` ↔ pipeline
de rendu ↔ Studio) et on ajoute les trois pièces manquantes que la spec
désigne comme centrales : le **prompt structuré par champs** (§3.4),
l'**image-clé validée par plan** (§7), le **QC scoré + retake ciblé** (§5.2,
§11). Le versionnement des artefacts (§2.1) est un prérequis de socle.

**Coût API du plan lui-même : 0 $.** Chaque lot déclare sa dépense et sa
porte de validation humaine avant elle.

---

## 1. Inventaire MESURÉ de l'existant — « section Chapitres étendue »

Ce que le dépôt contient réellement au 28/08 (branche
`claude/audit-cleanup-2026-08`, identique à `origin/main`, `05696b0`,
APP_VERSION 2.6.0).

### 1.1 Les surfaces

| Surface | Fichiers | Taille mesurée |
|---|---|---|
| Page Atelier (hors bundle, servie par FastAPI sur `/atelier`) | `frontend/atelier/index.html`, `atelier.css`, `atelier.js`, `preview.html` | 255 / 347 / 1325 / 280 lignes |
| Routes Atelier | `backend/app/api/routes.py:4303-6340` | **34 endpoints** (48 dans la plage, moins les 14 de Vectorlab `5269-5551`) |
| Agent manuscrit | `backend/app/services/manuscript_agent.py` | 854 lignes |
| Épisodes (Roman → vidéo narrée) | `routes.py:1847-2027` | 3 endpoints (`extract-text`, `scenes`, `render`) |
| Registre vidéo | `backend/app/services/fal_service.py` `VIDEO_MODELS` | **11 modèles** (4 Seedance, 2 Kling, 1 PixVerse, 4 Veo) |
| Tarifs | `backend/app/services/pricing.py:52-59` | $/s par modèle × résolution |

### 1.2 Les tables (`backend/app/services/storage.py`)

| Table | Ligne | Ce qu'elle porte |
|---|---:|---|
| `bible_entities` | 146 | 6 `kind` (character/place/object/date/ambiance/decor), `description`, `ref_image`, `seed`, `prompt_recipe` (JSON = recette rejouable), `face_image`, `aliases`, `evidence`, `style_notes`, `voice_id/voice_name/voice_prev` |
| `chapters` | 242 | `script_text`, `spans` (JSON, zones↔entités), `series` |
| `shots` | 257 | `chapter_id`, `idx`, `source_text`, `action`, `entities` (JSON ids), `shot_type`, `camera_move`, `duration_s`, `sketch_image`, `sketch_seed`, `prompt`, `motion_recipe`, `energy` |
| `scenes` | 284 | `chapter_id`, `idx`, `slugline`, `int_ext`, `location_entity_id`, `time_of_day`, `fountain_text`, `lighting`, `camera_notes`, `mood`, `entities`, `duration_s`, `vo_audio` |
| `atelier_settings` | 312 | clé/valeur ; `global_style` = style de réalisation du projet |
| `jobs` | 17 | `status`, `progress`, `error`, `seed`, `video_model`, `cost_meta`, `batch_id` |

`_auto_migrate()` (`storage.py:437`) sait ajouter des colonnes à chaud —
**aucune nouvelle colonne de ce plan ne casse une base existante.**

### 1.3 Les services réutilisables (déjà écrits, déjà éprouvés)

- `board_service.py` — planches de référence composites : chaque vue générée
  **séparément**, identité garantie par **chaînage Kontext**, assemblage
  **par code (PIL)**. Chaque panneau garde son seed → recette rejouable.
- `proportion_qc.py` — **une boucle QC complète existe déjà** : `measure()`
  (LLM vision), `judge()` (verdict contre le canon), régénération corrective,
  `record_lesson()` (l'erreur est persistée par canon et ré-appliquée). C'est
  le patron exact à généraliser pour §5.2.
- `shotcraft_service.py` — catalogue de recettes motion (slug, catégorie,
  énergie 1-5) injecté dans le prompt de découpage.
- `pipeline.py` — rendu vidéo, slots `source_kind` (`seedance`, `heygen`,
  `job`, `upload`, `file`), extension ffmpeg au-delà de la durée native.
- `pricing.py` / `/api/cost/estimate` / `/api/cost/usage` — coût par modèle.

---

## 2. Écart point par point avec la spécification

Légende : **✅ existe** · **🟡 à adapter** (la brique est là, le contrat
diffère) · **❌ manque**.

### §1-2 — Résultat attendu et architecture

| Concept spec | État | Où / quoi |
|---|:--:|---|
| Script normalisé, découpé | ✅ | `POST /atelier/manuscript` (job, `segment_chapters`), `/episodes/extract-text` (txt/md/docx/pdf) |
| Bible visuelle (personnages, lieux, décors, accessoires, ambiance) | ✅ | `bible_entities` 6 kinds + planches `board_service` + `global_style` |
| Fiches d'entités avec référence visuelle | ✅ | `ref_image` + `face_image` + `seed` + `prompt_recipe` |
| Shot list exploitable | 🟡 | `shots` existe mais champs incomplets (voir §3.3 ci-dessous) |
| Storyboard par panneaux liés aux plans | ✅ | 1 croquis = 1 `shot` — **meilleur que la grille Magnific** pour le retake granulaire. Ne pas copier la grille. |
| Clips image-to-video **par plan** | ❌ | **le trou central** : aucun chemin `shot → vidéo`. `/generate` (Seedance) et `/episodes/render` (Ken Burns) existent mais ignorent les `shots`. |
| Timeline finale | 🟡 | Studio nodal + `montage_service` + `/episodes/render` savent assembler — rien ne les alimente depuis le storyboard |
| Séparer faits narratifs / décisions de réalisation | 🟡 | `scenes` (narratif) et `shots` (réalisation) coexistent mais **ne sont pas liés** : `shots` n'a pas de `scene_id` |
| Pipeline orienté artefacts, jamais d'écrasement silencieux | ❌ | `POST /chapters/{id}/storyboard/decoupe` **REMPLACE** tous les plans ; `PUT /shots/{id}` écrase ; régénérer une planche écrase `ref_image` |
| Interface `MediaProvider` interchangeable | 🟡 | `VIDEO_MODELS[*].provider` + `image_providers.py` + `google_video.py` font déjà le dispatch. **Recommandation : ne pas créer une couche d'abstraction neuve** — étendre le registre suffit et coûte 10× moins. |
| Jobs async idempotents, `providerJobId`, params complets, coût réel | 🟡 | `JobRecord` a `status/progress/error/video_model/cost_meta/seed` ; manquent `providerJobId`, les **paramètres complets** de l'appel, l'idempotency key, l'état `cancelled` |
| Gates human-in-the-loop par jalon | 🟡 | le croquis pré-production existe (bonne intuition, déjà en place) ; aucun **statut** ne matérialise l'approbation |
| Mode draft / final | 🟡 | croquis FLUX schnell vs planche = l'idée y est, pas formalisée |

### §3 — Modèle de données canonique

| Champ spec | État | Détail mesuré |
|---|:--:|---|
| `Project.target{aspectRatio,resolution,fps,durationTarget,language}` | ❌ | `atelier_settings` ne porte que `global_style` |
| `Project.globalStyle{genre,visualStyle,colorPalette,negativeConstraints}` | 🟡 | `global_style` = une chaîne libre ; ni palette ni contraintes négatives de projet |
| `Entity.immutableTraits` / `mutableTraits` | ❌ | tout est dans `description` en prose |
| `Entity.promptAnchor` / `negativePrompt` | ❌ | absents |
| `Entity.status` (`locked`) / `version` | ❌ | **absents du modèle** alors que la spec P1 (`2026-07-05-atelier-chapitre-design.md` §3) les prévoyait |
| `Scene.narrativePurpose`, `setDressing`, `continuity{wardrobe,weather,screenDirection}` | ❌ | `scenes` porte la grammaire filmique mais pas la continuité |
| `Shot.sceneId` | ❌ | `shots.chapter_id` seulement — **la hiérarchie scène→plans n'existe pas** |
| `Shot.camera{angle,framing,lensIntent,composition}` | 🟡 | un seul champ `camera_move` (chaîne) |
| `Shot.lighting{key,practical,contrast,atmosphere}` | ❌ | vit sur la scène, pas sur le plan |
| `Shot.sound[]`, `dialogue` | 🟡 | l'audio vit sur `scenes.vo_audio` (VO minuté), pas par plan |
| `Shot.imagePrompt` **vs** `motionPrompt` | ❌ | un seul `shot.prompt` |
| `Shot.references[]`, `inputKeyframe`, `acceptanceCriteria`, `status` | ❌ | absents |
| **§3.4 prompt structuré par champs** | ❌ | `shot.prompt` = **une chaîne unique** → ni audit, ni localisation, ni modification ciblée, ni comparaison entre générations |

### §4-5 — Analyse et cohérence

| Concept | État | Détail |
|---|:--:|---|
| Sortie JSON stricte validée par schéma | 🟡 | `_ai_shots` / `extract_chapter` parsent du JSON à la main (`_parse_json`), sans schéma |
| `unknown` / `ambiguities` / `recommendedQuestions` | ❌ | l'agent comble les trous en silence |
| Extraction imposée par scène (§4.2, 8 axes) | 🟡 | l'agent manuscrit extrait entités + `evidence` (citations verbatim — excellent) ; lumière/continuité/audio non systématisés |
| Heuristiques de découpage (§4.3) | ✅ | dans le prompt `_ai_shots` (`routes.py:4982`) + doctrine shotcraft injectée |
| Séquence de verrouillage (§5.1) | 🟡 | référence maître + seed + `prompt_recipe` = **ancrage rejouable, meilleur que le seed seul**. Manque : approbation explicite et versions. |
| **Scores de cohérence 0-100 (§5.2)** | 🟡 | `proportion_qc.py` prouve le mécanisme (vision → mesure → verdict → correction → leçon persistée) sur UN axe (proportions). Les 7 axes de la spec restent à écrire. |

### §6-8 — Storyboard, images-clés, modèles

| Concept | État | Détail |
|---|:--:|---|
| Storyboard = panneaux spécifiant le plan | ✅ | déjà par plan, avec croquis dédié |
| Panneau découpé et associé à un `shotId` | ✅ | par construction (1 croquis / 1 plan) |
| Shot list minimale (§6.3) | 🟡 | manquent `inputKeyframe`, `motionPrompt`, `acceptanceCriteria` |
| **§7 image-clé validée → image-to-video** | ❌ | **absent — c'est la règle centrale de la spec** |
| Prompt de mouvement (§7.2) | 🟡 | `shotcraft_service` + `prompt_engine` savent construire du mouvement ; pas de `motionPrompt` par plan |
| **Capability flags (§8)** | 🟡 | `VIDEO_MODELS` porte déjà `durations`, `ratios`, `resolutions`, `end_image`, `seed`, `audio_param` — **ce SONT des capability flags**, exposés par `GET /api/video-models` (`routes.py:4177`). Manquent : `imageToVideo`/`textToVideo`, `videoReference`, `multiShot`/`maxShots`, `motionControl`, `lipSync`, `maxReferenceImages`. |
| Routage modèle par besoin de plan | ❌ | sélection 100 % manuelle ; aucune justification ni résultat observé conservés |

### §9-12 — 3D, audio, QC, métriques

| Concept | État | Détail |
|---|:--:|---|
| Image → 3D (§9) | ✅ hors périmètre | `asset3d_service`, `meshy_service`, `print3d` livrés (GLB, STL/3MF). **Ne pas rouvrir dans ce chantier.** |
| Audio piste indépendante (§10) | ✅ | VO minuté par scène (`scenes.vo_audio` + `duration_s`), casting voix **par personnage** (`bible_entities.voice_id`), `sfx_service`, `music_service`, sous-titres. **Plus avancé que la spec sur le casting.** |
| Diagnostic d'échec typé + retake ciblé (§11) | ❌ | régénérer = relancer le même appel |
| Politique de retry en 4 paliers (§11.2) | ❌ | absente |
| Métriques (§12) | 🟡 | `/cost/usage` + `/cost/estimate` + `pricing.py` donnent le coût par modèle. Manquent : taux d'acceptation au premier rendu, retakes/plan, **coût par seconde approuvée**, écart durée prévue/montée |

### 2.1 Synthèse : les trois défauts structurants

1. **Le storyboard ne devient jamais un film.** Toute la chaîne
   manuscrit → bible → scénario → VO minuté → croquis fabrique de la
   préproduction qui n'a aucun débouché de rendu. Le moteur (pipeline,
   11 modèles, tarifs, Studio) existe et n'est pas branché.
2. **Rien n'est versionné.** `decoupe` remplace, `PUT` écrase, régénérer
   une planche perd la précédente. La spec §2.1 l'interdit explicitement.
   Plus on attend, plus la dette coûte.
3. **`scenes` et `shots` sont deux listes parallèles.** La spec impose
   scène → plans. Sans `scene_id`, le VO minuté par scène (déjà calculé !)
   ne peut pas caler les durées des plans — l'animatic est à portée et
   inatteignable.

---

## 3. Ordre d'implémentation par lots

Chaque lot : livrable seul, banc dédié via
`scripts\run-tests.ps1 -Filter <fichier>`, porte de validation humaine,
dépense API déclarée.

### Lot 0 — Socle : hiérarchie, verrou, versions · **0 $**

*Pourquoi d'abord : c'est de la dette de schéma. Chaque lot suivant écrit
dedans.*

- [ ] `shots.scene_id` (String(36), index, nullable) — via `_auto_migrate`.
      Rattachement rétroactif par recouvrement de `source_text` ; les plans
      non rattachés restent orphelins **et sont dits** (jamais devinés).
- [ ] `bible_entities.status` (`draft`|`locked`, défaut `draft`) +
      `version` (Integer, défaut 1). Verrouiller fige `prompt_recipe` ;
      modifier une entité verrouillée **crée une version** (snapshot JSON
      dans une table `entity_versions`) au lieu d'écraser.
- [ ] `shots.status` (`planned`|`keyframe_pending`|`keyframe_ok`|`rendered`|`approved`|`rejected`).
- [ ] `POST /chapters/{id}/storyboard/decoupe` cesse de REMPLACER : nouveau
      découpage = nouvelle **révision** ; l'ancienne reste consultable.
- [ ] Projet : clés `atelier_settings` `target_aspect`, `target_resolution`,
      `target_fps`, `color_palette`, `negative_constraints` (§3.1).
- **Banc** `test_atelier_socle.py` : migration à chaud sur base d'avant
  (colonnes créées, données intactes) ; verrouiller puis modifier → version 2
  créée, version 1 lisible ; re-découpage → révision 2, révision 1 intacte.
- **Porte :** l'utilisateur voit dans `/atelier` le badge 🔒 sur une entité
  verrouillée et l'historique des révisions du storyboard. Aucune dépense.

### Lot 1 — Prompt structuré par champs (§3.4) · **0 $**

*Pourquoi ici : sans lui, le retake ciblé du Lot 4 est impossible — on ne
peut pas « ne modifier que les champs liés au défaut » dans une chaîne.*

- [ ] `shots.prompt_fields` (Text JSON) : `{subject[], environment[], action,
      framing, cameraMotion, lighting, mood, style, technical, negative[]}`.
- [ ] Service pur neuf `backend/app/services/prompt_compose.py` :
      `compose_image(fields, entities, project) -> str` et
      `compose_motion(fields, entities) -> str`. **Déterministe** : mêmes
      entrées ⇒ même chaîne, octet pour octet. Les `promptAnchor` /
      `negativePrompt` des entités présentes y sont injectés.
- [ ] `bible_entities.prompt_anchor` + `negative_prompt` +
      `immutable_traits` / `mutable_traits` (JSON) — remplis par l'agent à
      l'ingestion, éditables à la main.
- [ ] `_ai_shots` rend désormais les **champs**, pas une phrase ;
      `shot.prompt` devient le **rendu dérivé** (override manuel possible,
      marqué comme tel).
- **Banc** `test_prompt_compose.py` : déterminisme (100 appels, 1 sortie) ;
  injection des ancres d'entités ; un `negative` de projet + un d'entité
  fusionnent sans doublon ; l'override manuel gagne.
- **Porte :** dans `/atelier`, la carte plan montre les champs éditables et
  le prompt composé en lecture seule. Aucune dépense.

### Lot 2 — Image-clé par plan (§7) · **dépense : images uniquement**

*Le pont manquant. La règle centrale de la spec : entités verrouillées →
image-clé contrôlée → image-to-video.*

- [ ] `shots.keyframe_image`, `keyframe_seed`, `keyframe_recipe` (JSON).
- [ ] `POST /shots/{id}/keyframe {seed?, model?}` — prompt composé (Lot 1)
      + **références des entités présentes** (`ref_image`/`face_image`),
      chaînage Kontext à la manière de `board_service` pour tenir l'identité ;
      dépôt Library avec provenance `atelier` (mécanisme `library_index`
      déjà livré le 28/08).
- [ ] UI carte plan : vignette image-clé à côté du croquis, 🎲 re-roll,
      🔒 valider (→ `status=keyframe_ok`).
- [ ] Estimation de coût affichée AVANT le tir (`/api/cost/estimate`).
- **Banc** `test_shot_keyframe.py` : fal stubbé → seed honoré et stocké,
  recette rejouable, refus si une entité présente est en `draft`
  (verrouillage exigé), les références des entités sont bien passées.
- **Porte :** l'utilisateur valide une image-clé par plan. **Aucune vidéo
  n'est générable tant que `status != keyframe_ok`** — c'est la gate qui
  protège la dépense vidéo (≈ 10× le coût d'une image).

### Lot 3 — Vidéo par plan + capability flags (§8) · **dépense : vidéo**

- [ ] `shots.motion_prompt` (dérivé de `compose_motion`), `shots.video_job_id`.
- [ ] `POST /shots/{id}/animate {model?}` — image-to-video depuis
      `keyframe_image`, durée clampée sur `shot.duration_s` via
      `clamp_duration`, réutilise `pipeline` et `JobRecord` (donc
      `/cost/usage` compte juste d'office).
- [ ] `VIDEO_MODELS` gagne les flags manquants de §8 : `image_to_video`,
      `text_to_video`, `video_reference`, `multi_shot` / `max_shots`,
      `motion_control`, `lip_sync`, `max_reference_images`.
      `GET /api/video-models` les expose (additif — les sélecteurs
      dynamiques `DzVideoModelSel` continuent de marcher sans retouche).
- [ ] Routeur de recommandation `shot → modèle` : table de correspondance
      (besoin de plan × capability flags × $/s), **justification stockée**
      sur le job. L'utilisateur garde la main.
- [ ] `JobRecord.provider_job_id` + `provider_params` (JSON) — la provenance
      intégrale exigée par §16.
- **Banc** `test_shot_animate.py` : flags exposés pour les 11 modèles ;
  refus si `status != keyframe_ok` ; clamp de durée ; recommandation
  déterministe et justifiée ; params complets persistés.
- **Porte :** confirmation explicite avec coût estimé avant chaque tir, et
  un plafond de dépense par chapitre.

### Lot 4 — QC scoré + retake ciblé (§5.2, §11) · **dépense : vision + retakes**

*Généralisation directe de `proportion_qc.py`, qui a déjà prouvé la boucle.*

- [ ] `backend/app/services/shot_qc.py` : `identity`, `location`, `prop`,
      `lighting`, `composition`, `artifact` sur l'image-clé ; `motion` sur
      première/dernière frame du clip. Seuils configurables (défauts de la
      spec §5.2). **Best-effort, jamais bloquant** (sans clé vision → None,
      comme `proportion_qc`).
- [ ] Scores + explication stockés sur le plan ; passage auto en `approved`
      seulement au-dessus des seuils.
- [ ] `FailureReason` typé (13 valeurs de §11.1) et moteur de retake qui ne
      touche **que** les champs `prompt_fields` liés au défaut — rendu
      possible par le Lot 1.
- [ ] Politique de retry en 4 paliers (§11.2) + escalade humaine au
      dépassement de budget ou de tentatives. Toutes les variantes conservées.
- **Banc** `test_shot_qc.py` : vision stubbée → seuils respectés ;
  `identity_drift` renforce les références et **ne touche pas** la caméra ;
  palier 4 bascule de modèle ; le budget dépassé escalade au lieu de tirer.
- **Porte :** l'utilisateur voit les scores et arbitre. Le retake ne part
  jamais tout seul.

### Lot 5 — Timeline et métriques (§10, §12) · **0 $**

- [ ] Assemblage des plans `approved` → graphe Studio auto-généré
      (Concatenate + audio + loudness), à la manière du P4 esquissé dans
      `2026-07-05-atelier-chapitre-design.md` §6.
- [ ] Calage sur le VO minuté déjà mesuré (`scenes.duration_s`) — possible
      seulement grâce au `scene_id` du Lot 0.
- [ ] `GET /api/atelier/metrics` : taux d'acceptation au premier rendu,
      retakes moyens par plan, **coût par seconde approuvée**, durée de
      génération, écart durée prévue / durée montée, taux de réutilisation
      des entités. Calculé depuis `jobs` + `shots.status` (rien de neuf à
      instrumenter).
- **Banc** `test_atelier_metrics.py` : formules de §12 sur un jeu de jobs
  figé ; assemblage produit un graphe Studio valide (ffmpeg réel).
- **Porte :** l'utilisateur relit le montage de travail avant tout upscale
  ou export final.

---

## 4. Décisions d'architecture (à valider avant de coder)

- **D1 — Pas d'interface `MediaProvider` neuve.** `VIDEO_MODELS` +
  `image_providers` + `google_video` font déjà le dispatch par `provider`.
  On étend le registre avec les capability flags manquants. Une couche
  d'abstraction supplémentaire coûterait une réécriture de `pipeline.py`
  pour un gain nul à 11 modèles.
- **D2 — Pas de connecteur Magnific.** §15 de la spec exige de vérifier
  API/MCP, scopes, quotas, coûts, droits commerciaux et rétention au portail
  développeur. Magnific reste **benchmark**, pas dépendance.
- **D3 — On garde 1 croquis = 1 plan**, on ne copie pas la grille storyboard
  multi-panneaux de Magnific : le découpage individuel permet le retake
  granulaire que §11 exige, et `board_service` a déjà mesuré que la
  diffusion est peu fiable sur les mises en page multi-panneaux.
- **D4 — La 3D reste hors chantier.** `asset3d`/`meshy`/`print3d` couvrent
  déjà §9 ; le rouvrir diluerait le lot vidéo.
- **D5 — Versionner par snapshot JSON**, pas par table par entité : une
  table `entity_versions` (`entity_id`, `version`, `payload` JSON,
  `created_at`) suffit et suit le patron `VectorDoc` (contenu hors table
  principale).
- **D6 — Les gates sont des `status`, pas des booléens.** Un plan traverse
  `planned → keyframe_ok → rendered → approved` ; chaque transition
  coûteuse exige la précédente. C'est ce qui rend la dépense impossible à
  déclencher par accident.

## 5. Ce que le dépôt fait DÉJÀ mieux que la spec

À conserver tel quel, ne pas régresser en appliquant la spec à la lettre :

- **Casting voix par personnage** (`bible_entities.voice_id` + suggestion
  par croisement fiche × labels du compte) — §10 n'en parle pas.
- **VO minuté d'abord, storyboard calé dessus** (méthode animatic) —
  §7 déduit les durées, l'Atelier les **mesure**.
- **`evidence`** : citations verbatim par chapitre sur chaque entité —
  la traçabilité que §4.1 réclame, déjà là.
- **`prompt_recipe`** : la recette complète (prompt + seed + taille) rejouée
  à l'identique — plus fort que le `referenceAssets` de §3.2.
- **Chaînage Kontext** pour l'identité inter-panneaux — §5.1 se contente de
  « vues cohérentes ».

## 6. Risques mesurés

| Risque | Mitigation |
|---|---|
| Le rattachement rétroactif `shot → scene` se trompe | recouvrement de `source_text` uniquement ; sous le seuil → orphelin **dit à l'UI**, jamais deviné |
| Le QC vision coûte à chaque plan | best-effort et **optionnel** (patron `proportion_qc`) ; seuils et activation par projet |
| L'image-to-video dérive malgré l'image-clé | c'est précisément pourquoi §7 impose l'image-clé : le prompt vidéo ne décrit que le **mouvement** ; le Lot 4 mesure la dérive au lieu de l'espérer |
| Les 34 endpoints Atelier deviennent illisibles | `routes.py` fait 7955 lignes — extraire les routes Atelier dans un module dédié est un candidat, **hors périmètre de ce plan** (à arbitrer séparément) |
| Dépense accidentelle | D6 : aucune vidéo sans `keyframe_ok` ; estimation avant chaque tir ; plafond par chapitre |
