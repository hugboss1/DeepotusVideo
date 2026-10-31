# Relevé des API 3D : génération, rigging, mouvement (t387)

**Date du relevé : 31/10/2026.** Recherche en LECTURE SEULE. Aucun appel payant, aucune connexion à un compte, aucune clé utilisée.

**Méthode.**
- Catalogue fal : API publique de recherche `https://api.fal.ai/v1/models?q=<mot>`, interrogée avec les mots tripo, rig, hunyuan, meshy, trellis, rodin, motion, seedream, gpt-image, kimodo et gvhmr.
- Schémas fal : pages `https://fal.ai/models/<id>/llms.txt`, version texte de la page `/api`.
- Documentation des fournisseurs : `developers.tripo3d.com` et `docs.meshy.ai` (versions `.md`).
- Code amont : fichiers bruts GitHub et paquet npm.

Chaque fait porte l'URL où il a été lu. Les prix sont ceux **affichés au 31/10/2026** et peuvent changer. « Non trouvé » veut dire que l'information n'apparaît nulle part dans les sources lues, pas qu'elle n'existe pas.

---

## 0. Catalogue 3D présent sur fal au 31/10/2026

Source : `https://api.fal.ai/v1/models?q=…`, aux dates et requêtes indiquées plus haut. **Gras** = endpoint que le backend appelle déjà.

| Famille | endpoint_id | Catégorie fal |
|---|---|---|
| Tripo | **tripo3d/tripo/v2.5/image-to-3d**, tripo3d/tripo/v2.5/multiview-to-3d | image-to-3d |
| Tripo | **tripo3d/h3.1/image-to-3d**, tripo3d/h3.1/multiview-to-3d, tripo3d/h3.1/text-to-3d | image/text-to-3d |
| Tripo | tripo3d/p1/image-to-3d, tripo3d/p1/text-to-3d | image/text-to-3d |
| Tripo | tripo3d/p2/image-to-3d, tripo3d/p2/text-to-3d | image/text-to-3d |
| Tripo | tripo3d/tripo/remesh, tripo3d/tripo/segment | 3d-to-3d |
| Tripo | tripo3d/triposplat | image-to-3d (Gaussian splat) |
| Hunyuan | fal-ai/hunyuan-3d/v3.1/pro/image-to-3d, …/v3.1/pro/text-to-3d | image/text-to-3d |
| Hunyuan | fal-ai/hunyuan-3d/v3.1/rapid/image-to-3d, …/v3.1/rapid/text-to-3d | image/text-to-3d |
| Hunyuan | fal-ai/hunyuan-3d/v3.1/smart-topology, fal-ai/hunyuan-3d/v3.1/part | 3d-to-3d |
| Hunyuan (anciens) | fal-ai/hunyuan3d-v3/{image,text,sketch}-to-3d, fal-ai/hunyuan3d-v21, **fal-ai/hunyuan3d/v2** (+ /turbo, /mini, /multi-view) | image-to-3d |
| Hunyuan mouvement | fal-ai/hunyuan-motion (« [1B] »), fal-ai/hunyuan-motion/fast (« [0.46B] ») | text-to-3d |
| TRELLIS | **fal-ai/trellis**, fal-ai/trellis/multi, fal-ai/trellis-2, fal-ai/trellis-2/retexture, fal-ai/trellis-2-lora | image-to-3d / 3d-to-3d |
| Rodin | **fal-ai/hyper3d/rodin**, fal-ai/hyper3d/rodin/v2, fal-ai/hyper3d/rodin/v2.5, …/v2.5/fast, …/v2.5/text-to-3d, …/v2.5/text-to-3d/fast | image/text-to-3d |
| Meshy | meshy/v7.1/{image,multi-image,text}-to-3d, meshy/v7/{image,multi-image,text}-to-3d, meshy/v7/retexture, meshy/v6/retexture, meshy/v6-lite/retexture | divers |
| Meshy | fal-ai/meshy/v6/{image,text}-to-3d, fal-ai/meshy/v6-preview/{image,text}-to-3d, fal-ai/meshy/v6/multi-image-to-3d (marqué **deprecated**) | divers |
| Meshy rigging | fal-ai/meshy/rigging, fal-ai/meshy/rigging/multi-animation | 3d-to-3d |
| Autres | fal-ai/sam-3/3d-objects, hitem3d/hi3d/texture, speridlabs/idol (splat), **fal-ai/triposr** | divers |

**Absents du catalogue fal** (recherche vide ou sans résultat pertinent) : aucun endpoint Tripo de rig, rig-check ou retarget (`https://fal.ai/models/tripo3d/rig/llms.txt` et `…/tripo3d/h3.1/rig/llms.txt` renvoient 404 ; `q=rig` ne remonte que Meshy), Kimodo (`q=kimodo` vide), GVHMR (`q=gvhmr` vide).

> **Contradiction relevée sur fal.** Les sorties Tripo (H3.1, P1, P2, remesh) contiennent un `task_id` décrit ainsi : « can be passed to rig or rig-check endpoints ». Aucun endpoint de ce nom n'est pourtant listé. Le rig Tripo ne passe donc, à ce jour, que par l'API directe de Tripo (§2.3).

---

## 1. Image → 3D / texte → 3D

### 1.1 Tripo sur fal

**tripo3d/h3.1/image-to-3d** (`https://fal.ai/models/tripo3d/h3.1/image-to-3d/llms.txt`)

| Paramètre | Type | Défaut | Valeurs |
|---|---|---|---|
| image_url | string (requis) | | |
| face_limit | int | adaptatif | 1000 à 2000000 |
| texture | bool | true | |
| pbr | bool | true | active aussi texture |
| model_seed, texture_seed | int | | |
| texture_quality | enum | standard | standard, detailed |
| geometry_quality | enum | standard | standard, detailed |
| texture_alignment | enum | original_image | original_image, geometry |
| auto_size | bool | false | échelle réelle en mètres |
| orientation | enum | default | default, align_image |
| quad | bool | false | sortie possiblement FBX |
| enable_safety_checker | bool | true | |

- **Sortie :** model_mesh (GLB ou FBX), model_urls, rendered_image, task_id.
- **Prix :** 0,20 $ sans texture, 0,30 $ texture standard, 0,40 $ texture HD. Géométrie détaillée +0,20 $, quad +0,05 $.

**tripo3d/h3.1/text-to-3d** (`…/tripo3d/h3.1/text-to-3d/llms.txt`)
- **Paramètres :** les mêmes, sans image_url, texture_alignment ni orientation, plus `prompt` (1024 car. max), `negative_prompt` et `image_seed`.
- **Prix :** 0,10 / 0,20 / 0,30 $, mêmes suppléments.

**tripo3d/h3.1/multiview-to-3d** (`…/tripo3d/h3.1/multiview-to-3d/llms.txt`)
- **Paramètres :** `image_urls`, 2 à 4 vues dans l'ordre front, left, back, right (front obligatoire). Le reste est identique à image-to-3d.
- **Prix :** identique à image-to-3d.

**tripo3d/p1/image-to-3d** (`…/tripo3d/p1/image-to-3d/llms.txt`), le modèle « Smart Mesh P1.0 » basse résolution
- **Paramètres :** `image_url` ; `face_limit` de 48 à 20000 (adaptatif si absent) ; `texture` (défaut true) ; `model_seed` ; `enable_safety_checker`. **Pas de pbr, de quad ni de texture_quality.**
- **Sortie :** model_mesh (GLB ou FBX), model_urls, rendered_image, task_id.
- **Prix :** 0,40 $ sans texture, 0,50 $ avec texture.
- **Version texte :** tripo3d/p1/text-to-3d existe (listing fal). Sa page n'a pas été relue en détail.

**tripo3d/p2/image-to-3d** (`…/tripo3d/p2/image-to-3d/llms.txt`), le modèle le plus récent de Tripo (topologie quad native)

| Paramètre | Type | Défaut | Valeurs |
|---|---|---|---|
| image_url | string (requis) | | |
| face_limit | int | adaptatif | 48 à 50000 ; quad 25000 max |
| texture | bool | true | |
| pbr | bool | true | |
| model_seed, texture_seed | int | | |
| texture_quality | enum | standard | fast, standard, detailed, extreme |
| texture_version | enum | non indiqué | v3.5-20260815, v3.0-20250812, v2.5-20250123 (fast exige v3.5) |
| delight | bool | true | retire l'éclairage cuit (v3.5) |
| auto_size | bool | false | |
| export_uv | bool | true | |
| export_orientation | enum | non indiqué | +x, -x, +y, -y |
| quad | bool | false | |
| enable_safety_checker | bool | true | |

- **Sortie :** comme H3.1.
- **Prix :** 1,00 $ sans texture, 1,10 $ en texture fast ou standard, 1,20 $ en detailed, 1,30 $ en extreme. Le quad est gratuit.

**tripo3d/p2/text-to-3d** (`…/tripo3d/p2/text-to-3d/llms.txt`)
- **Paramètres :** ceux de P2, plus `prompt` (1024 car.), `negative_prompt` et `image_seed`.
- **Prix :** identique (1,00 / 1,10 / 1,20 / 1,30 $).

**tripo3d/tripo/remesh** (`…/tripo3d/tripo/remesh/llms.txt`)
- **Paramètres :**
  - `mesh_url` : GLB, OBJ, FBX ou STL, 150 Mo max.
  - `quad` : défaut false. Force le FBX ; face_limit vaut alors 10000 par défaut.
  - `face_limit` : 500 à 20000 (500 à 10000 en quad).
  - `bake` : défaut true.
  - `part_names` : list.
- **Sortie :** model_mesh, model_urls, rendered_image, task_id.
- **Prix :** « $0.01 per units ». Le nombre d'unités par appel n'est pas trouvé.

**tripo3d/tripo/segment** (`…/tripo3d/tripo/segment/llms.txt`)
- **Paramètre :** `mesh_url`.
- **Sortie :** model_mesh, model_urls, `part_names` (à repasser au remesh), rendered_image.
- **Prix :** « $0.01 per units ».

### 1.2 Tripo en direct (openapi.tripo3d.com, API v3)

Ces faits servent de référence pour ce que fal n'expose pas.

**Image to model.** `POST https://openapi.tripo3d.com/v3/generation/image-to-model` (`https://developers.tripo3d.com/en/docs/generation-image-to-model`)
- **Modèles :** `model` vaut `v3.1-20260211` (défaut), `v3.0-20250812` ou `v2.5-20250123`.
- **Paramètres absents de fal :**
  - `enable_image_autofix`
  - `texture_quality` : fast, standard, detailed, extreme (8K)
  - `texture_version`
  - `delight`
  - `smart_low_poly` : triangles 500 à 20000, quads 500 à 10000
  - `generate_parts` : exige texture et pbr à false
  - `compress: geometry`
  - `export_orientation`
  - `export_uv`
- **face_limit maximal :** v3.1 = 1 500 000 en standard et 2 000 000 en ultra ; v3.0 = 1 000 000 et 2 000 000 ; v2.5 = 500 000 ; quad = 150 000.

**Série P.** `https://developers.tripo3d.com/en/models/p2`
- **P2 :** `P2-20260801`, release courante. `P1-20260311` est la release précédente, sans quad.
- **face_limit de P2 :** triangles 48 à 50 000, quads 48 à 25 000.
- **Paramètres non supportés par la série P :** smart_low_poly, generate_parts, geometry_quality.
- **Crédits P2 :** 100 sans texture, 110 standard, 120 detailed, 130 8K.
- **Concurrence :** 5 tâches série P en parallèle au plus.
- **Nommage :** la page liste `https://developers.tripo3d.com/en/models` montre « Tripo H3.1 » (slug v3-1, environ 40 s), « Tripo P2 », « Tripo Rigging » (environ 30 s), « Tripo Animation » (environ 5 s) et « Tripo Texture (V3.5) ».

**Grille de crédits générale.** `https://developers.tripo3d.com/en/pricing`
- **Base :** texte→3D 10 crédits sans texture, 20 avec ; image ou multivue 20 et 30.
- **Suppléments :** HD texture +10, 8K +20, géométrie HD +20, quad +5, smart low-poly +10, parts +20.
- **Animation :** rig check gratuit, auto rig 25, retarget 10 par animation.
- **Conversion monétaire :** « 1 credit = ¥0.07 CNY ». Aucun prix en USD n'a été trouvé sur cette page.

### 1.3 Hunyuan 3D v3.1 sur fal

**fal-ai/hunyuan-3d/v3.1/pro/image-to-3d** (`…/fal-ai/hunyuan-3d/v3.1/pro/image-to-3d/llms.txt`)

| Paramètre | Type | Défaut | Valeurs |
|---|---|---|---|
| input_image_url | string (requis) | | 128 à 5000 px, 8 Mo max, JPG, PNG ou WEBP |
| back_image_url, left_image_url, right_image_url | string | | vues optionnelles |
| top_image_url, bottom_image_url, left_front_image_url, right_front_image_url | string | | vues optionnelles, v3.1 seulement |
| generate_type | enum | Normal | Normal (texturé), Geometry (blanc) |
| enable_pbr | bool | false | ignoré en Geometry |
| face_count | int | 500000 | 40000 à 1500000 |

- **Sortie :** model_glb, thumbnail, model_urls (glb, obj), seed.
- **Prix :** 0,375 $. Suppléments de +0,15 $ chacun : PBR, multi-vues, face_count personnalisé.

**…/v3.1/pro/text-to-3d** (`…/pro/text-to-3d/llms.txt`)
- **Paramètres :** `prompt` (1024 car.), `generate_type`, `enable_pbr`, `face_count` (mêmes plages).
- **Restriction :** « LowPoly and Sketch types are not available in v3.1 ».
- **Sortie :** model_glb, thumbnail, model_urls (texture, mtl, obj, glb), seed.
- **Prix :** 0,375 $, mêmes suppléments.

**…/v3.1/rapid/image-to-3d** (`…/rapid/image-to-3d/llms.txt`)
- **Paramètres :** `input_image_url`, `enable_pbr` (défaut false), `enable_geometry` (défaut false : modèle blanc, sans OBJ).
- **Sortie :** model_glb, material_mtl, texture, thumbnail, model_urls.
- **Prix :** 0,225 $, PBR +0,15 $.
- **Version texte :** rapid/text-to-3d existe (listing). Sa page n'a pas été relue.

**…/v3.1/smart-topology** (`…/smart-topology/llms.txt`)
- **Paramètres :**
  - `input_file_url` : GLB ou OBJ, 200 Mo max.
  - `input_file_type` : glb ou obj.
  - `polygon_type` : triangle ou quadrilateral.
  - `face_level` : high, medium ou low (défaut medium).
- **Sortie :** model_glb et model_urls (glb, obj).
- **Prix :** 0,75 $.

**…/v3.1/part** (`…/part/llms.txt`)
- **Paramètre :** `input_file_url`, en FBX seulement, 100 Mo max et 30 000 faces max.
- **Sortie :** `result_files` (FBX par pièce).
- **Prix :** 0,45 $.

### 1.4 TRELLIS 2

**fal-ai/trellis-2** (`https://fal.ai/models/fal-ai/trellis-2/llms.txt`)
- **Paramètres principaux :**
  - `image_url` (requis) et `seed`.
  - `resolution` : 512, 1024 ou 1536 (défaut 1024).
  - `decimation_target` : 5000 à 2000000 (défaut 500000, **nombre de sommets visé**).
  - `texture_size` : 1024, 2048 ou 4096 (défaut 2048).
  - `remesh` : défaut true.
  - `remesh_band` : 0 à 4 (défaut 1) ; `remesh_project` : 0 à 1 (défaut 0).
- **Réglages avancés :** trois groupes de guidage, `ss_*`, `shape_slat_*` et `tex_slat_*`. Chacun a `guidance_strength` (0 à 10), `guidance_rescale`, `interval_start` et `interval_end`, `sampling_steps` (1 à 50, défaut 12) et `rescale_t` (1 à 6). S'y ajoutent les paramètres `uv_unwrap_*`.
- **Sortie :** `model_glb` seul.
- **Prix :** 0,25 $ en 512p, 0,30 $ en 1024p, 0,35 $ en 1536p.

**fal-ai/trellis-2/retexture** (`…/trellis-2/retexture/llms.txt`)
- **Paramètres :**
  - `image_url` et `mesh_url` (GLB, OBJ, PLY ou STL).
  - `resolution` : 512 ou 1024.
  - `tex_slat_*`.
  - `texture_size` : 1024, 2048 ou 4096.
- **Sortie :** model_glb.
- **Prix :** 0,20 $ en 512p, 0,24 $ en 1024p.

### 1.5 Rodin (Hyper3D)

**fal-ai/hyper3d/rodin/v2.5** (« Gen-2.5 », `…/fal-ai/hyper3d/rodin/v2.5/llms.txt`)

| Paramètre | Défaut | Valeurs |
|---|---|---|
| prompt | "" | auto-généré si vide en mode image |
| image_urls | | 5 max |
| tier | Gen-2.5-High | Gen-2.5-Minimum, -Extreme-Low, -Low, -Medium, -High, -Extreme-High (Minimum force 50K Triangle) |
| use_original_alpha | false | |
| seed | | 0 à 65535 |
| geometry_file_format | glb | glb, usdz, fbx, obj, stl |
| material | All | PBR, Shaded, All, None |
| quality_mesh_option | Auto | Auto, 4K/8K/18K/50K/100K/200K Quad, 2K/20K/50K/150K/500K/1M/2M Triangle (dépend du tier) |
| texture_mode | dépend du tier | legacy, extreme-low, low, medium, high |
| enable_creative_mode | false | |
| hd_texture | false | |
| texture_delight | false | |
| is_micro | false | Extreme-High seulement |
| TAPose | false | T-pose ou A-pose |
| bbox_condition | | objet, schéma non détaillé |
| addons | | HighPack |
| preview_render | false | |

- **Sortie :** model_mesh, model_meshes, seed, textures.
- **Prix :** 0,40 $, HighPack +0,80 $.

**…/rodin/v2.5/fast** (`…/v2.5/fast/llms.txt`)
- **tier :** Gen-2.5-Minimum, -Extreme-Low (défaut) ou -Low.
- **material :** Shaded par défaut.
- **quality_mesh_option :** Auto, 1K/4K/8K/18K/20K Quad, 2K/4K/8K/10K/20K Triangle (20K maximum).
- **Prix :** 0,10 $.

**…/rodin/v2.5/text-to-3d** (`…/v2.5/text-to-3d/llms.txt`)
- **Paramètres :** ceux de v2.5, sans image_urls ni use_original_alpha ni preview_render.
- **Prix :** 0,40 $, HighPack +0,80 $.
- **Variante rapide :** …/text-to-3d/fast existe (listing). Sa page n'a pas été relue.

**fal-ai/hyper3d/rodin/v2** (« Gen-2 », `…/rodin/v2/llms.txt`)
- **Paramètres :**
  - `input_image_urls` (5 max) et `prompt`.
  - `quality_mesh_option` : 4K/8K/18K/50K Quad ou 2K/20K/150K/500K Triangle (défaut 500K Triangle).
  - `material` : PBR, Shaded ou All.
  - `TAPose`.
  - `bbox_condition` [l, h, L].
  - `addons` : HighPack, textures 4K et triple facturation.
  - `preview_render`.
- **Valeur « Gen-2 » :** absente comme valeur de tier.
- **Prix :** 0,40 $.

### 1.6 Meshy

**API directe.** Sources : `https://docs.meshy.ai/en/api/image-to-3d`, `https://docs.meshy.ai/en/api/text-to-3d`, `https://docs.meshy.ai/api/pricing.md` et `https://docs.meshy.ai/llms.txt`.

**`ai_model`** (Image to 3D ; Text to 3D Preview)
- **Mode standard :** `latest` (= Meshy 7.1, défaut), `meshy-7.1`, `meshy-6`, `meshy-6-lite`, `meshy-7` (deprecated).
- **Mode smart-topology :** `meshy-t2` ou `meshy-t2.5` (défaut).
- **Retexture :** le modèle le plus récent est `meshy-7`, et `meshy-7.1` y est refusé (llms.txt).
- **Meshy 5 :** non listé.

**Paramètres d'Image to 3D**

| Paramètre | Défaut | Valeurs / règles |
|---|---|---|
| model_type | standard | standard, smart-topology |
| geometry_resolution | standard | standard, 2k (2048³), 4k (4096³) ; 2k exige 7.1, latest ou 7 ; 4k exige 7.1 ou latest (« Ultra ») |
| ultra_mode | false | deprecated, vaut geometry_resolution 2k |
| should_texture | true | |
| enable_pbr | false | exige should_texture |
| texture_resolution | 2k | 2k, 4k, 8k (pas de 4k ni 8k en 6-lite) |
| hd_texture | false | deprecated, vaut 4k |
| texture_prompt | | 800 car. max |
| texture_image_url | | |
| should_remesh | true en 6-lite, false sinon | |
| topology | triangle | quad, triangle (si remesh ; quad interdit en t2 et t2.5) |
| decimation_mode | | 1 ultra, 2 high, 3 medium, 4 low (prime sur target_polycount) |
| save_pre_remeshed_model | false | |
| target_polycount | 30000 | 100 à 300000 ; t2 : 100 à 15000 (déf. 4000) ; t2.5 : 100 à 30000 (déf. 15000) |
| symmetry_mode | auto | **deprecated, sans effet** |
| pose_mode | "" | a-pose, t-pose, "" |
| image_enhancement | true | meshy-6, 7.1 et latest seulement |
| remove_lighting | true | effectif en meshy-6 seulement ; 7.1 et latest l'ignorent |
| moderation | false | |
| target_formats | tous sauf 3mf | glb, obj, fbx, stl, usdz, 3mf |
| auto_size / origin_at | false / bottom | bottom, center |
| alpha_thumbnail, multi_view_thumbnails | false | |

**Text to 3D**
- **Preview :** `mode` = preview, `prompt` (800 car.), les mêmes paramètres de géométrie, `art_style` (deprecated et ignoré).
- **Refine :** `preview_task_id`, `enable_pbr`, `texture_resolution`, `texture_prompt` ou `texture_image_url`, `ai_model`, `remove_lighting`. `geometry_resolution` y est refusé (400).
- **Sortie :** model_urls (glb, fbx, obj, usdz, mtl, stl, 3mf, pre_remeshed_glb) ; texture_urls (base_color, metallic, normal, roughness, emission selon le modèle) ; thumbnail_url ; consumed_credits.

**Crédits de génération** (`https://docs.meshy.ai/api/pricing.md`)

| Configuration | 7.1 (latest) | 6 | 6-lite | t2 | t2.5 |
|---|---|---|---|---|---|
| Text to 3D Preview | 20 | 20 | 5 | 5 | 5 |
| Image to 3D, maillage seul | 20 | 20 | 5 | 5 | 5 |
| Image to 3D, textures 2K | 30 | 30 | 15 | 15 | 15 |
| Image to 3D, textures 4K | 30 | 30 | — | 15 | 15 |
| Image to 3D, textures 8K | 35 | 35 | — | 20 | 20 |

**Autres coûts en crédits** (même page)
- Ultra geometry : +5 (7.1 seulement).
- Text Refine et Retexture : 10 en 2K ou 4K, 15 en 8K.
- Remesh 5, UV Unwrap 5, Convert 1, Resize 1.
- **Prix du crédit en USD : non trouvé** sur cette page.

**Meshy sur fal**

**meshy/v7.1/image-to-3d** (`https://fal.ai/models/meshy/v7.1/image-to-3d/llms.txt`)
- **Paramètres :**
  - `image_url`
  - `model_type` : standard, lowpoly, smart-topology ou smart-topology-t2. fal expose une valeur `lowpoly` que la doc Meshy directe ne liste plus.
  - `topology` : quad ou triangle.
  - `target_polycount` : 100 à 300000, défaut 30000.
  - `symmetry_mode` : off, auto ou on.
  - `should_remesh` (true), `should_texture` (true), `enable_pbr` (false).
  - `pose_mode` : a-pose, t-pose ou "".
  - `texture_prompt`, `texture_image_url`.
  - `enable_rigging`, `rigging_height_meters` (1.7), `enable_animation`, `animation_action_id` (0 à 696, défaut 92).
  - `geometry_resolution` : standard, 2k ou 4k.
  - `enable_safety_checker`.
- **Paramètres absents de fal :** texture_resolution, image_enhancement, remove_lighting.
- **Sortie :** model_glb ; model_urls (glb, obj, fbx, usdz) ; thumbnail ; texture_urls ; seed. Avec rigging : rigged_character_glb/fbx, basic_animations, rig_task_id. Avec animation : animation_glb/fbx.
- **Prix :** 0,80 $ sans texture, 1,20 $ avec texture ; rig +0,20 $ ; animation +0,12 $ par appel. Soit 1,52 $ pour un modèle texturé, riggé et animé.

**meshy/v7.1/text-to-3d** (`…/meshy/v7.1/text-to-3d/llms.txt`)
- **Paramètres :** mêmes options, plus `mode` (preview ou full, défaut full), `prompt` (600 car.) et `enable_prompt_expansion`.
- **Prix :** identique.

**meshy/v7/retexture** (`…/meshy/v7/retexture/llms.txt`)
- **Paramètres :**
  - `model_url` : glb, gltf, obj, fbx ou stl.
  - `text_style_prompt` (600 car.) ou `image_style_url`.
  - `texture_resolution` : 2k, 4k ou 8k.
  - `enable_original_uv` : défaut true.
  - `enable_pbr`.
- **Prix :** 0,30 $ en 2K ou 4K, 0,45 $ en 8K.

**Autres endpoints Meshy listés mais non relus en détail :** meshy/v7.1/multi-image-to-3d, meshy/v7/*, fal-ai/meshy/v6/*, fal-ai/meshy/v6-preview/*, meshy/v6/retexture et meshy/v6-lite/retexture.

---

## 2. Rigging

### 2.1 Meshy en direct : `POST /openapi/v1/rigging`

Source : `https://docs.meshy.ai/api/rigging.md` et `https://docs.meshy.ai/en/api/rigging-and-animation`.

**Paramètres**
- `input_task_id` **ou** `model_url`. Le fichier doit être un GLB de 400 Mo max par URL, 100 Mo en data URI.
- `height_meters` : défaut 1.7, pas de valeur négative.
- `texture_image_url` : deprecated.

**Contraintes**
- Humanoïde **texturé**.
- **380 000 triangles maximum**, un quad comptant pour 2. Au-delà, la doc conseille un Remesh préalable à 300 000 ou moins (150 000 ou moins en quad).
- Le visage doit regarder vers **+Z**.
- Erreur 422 si l'estimation de pose échoue.
- Plan payant obligatoire (402 en plan gratuit).

**Sortie**
- `rigged_character_fbx_url` et `rigged_character_glb_url`.
- `basic_animations` : walking_glb, walking_fbx et walking_armature_glb, plus l'équivalent running.

**Crédits :** 5 par requête (pricing.md).

### 2.2 Meshy sur fal

**fal-ai/meshy/rigging** (`https://fal.ai/models/fal-ai/meshy/rigging/llms.txt`)
- **Paramètres :** `model_url` (GLB humanoïde), `height_meters` (1.7), `enable_animation` (false), `animation_action_id` (0 à 696, défaut 92), `enable_safety_checker`.
- **Sortie :** rigged_character_glb/fbx, basic_animations, animation_glb/fbx, rig_task_id.
- **Prix :** 0,20 $, ou 0,32 $ avec animation.

**fal-ai/meshy/rigging/multi-animation** (`…/rigging/multi-animation/llms.txt`)
- **Paramètres :** `model_url`, `height_meters`, `animation_action_ids` (liste requise : 1 à 10 identifiants distincts de 0 à 696, rendus dans l'ordre demandé).
- **Sortie :** `animations` (une liste d'AnimationClip dont les champs ne sont **pas documentés**), plus le reste de la sortie rigging.
- **Prix :** 0,20 $, plus 0,12 $ par clip.

### 2.3 Tripo en direct (absent de fal)

**`POST /v3/animations/rig-check`** (`https://developers.tripo3d.com/en/docs/animations-rig-check.md`)
- **Entrée :** `input`, au choix task_id, file_token ou URL. Formats GLB, FBX, OBJ ou STL, 150 Mo max.
- **Sortie :** `riggable` (bool) et `rig_type` : biped, quadruped, hexapod, octopod, avian, serpentine ou aquatic.
- **Coût :** gratuit (pricing).

**`POST /v3/animations/rig`** (`…/animations-rig.md`)

| Paramètre | Défaut | Valeurs |
|---|---|---|
| input | | task_id, file_token ou URL ; GLB, FBX, OBJ ou STL ; 150 Mo |
| model | v1.0-20240301 | v1.0-20240301, v2.5-20260210, v3.0-20260909 |
| rig_type | biped | biped, quadruped, hexapod, octopod, avian, serpentine, aquatic, others |
| spec | tripo | biped seulement : tripo, mixamo, actorcore, unity, unreal, vrm (actorcore, unity, unreal, vrm et others sous v3.0) |
| out_format | glb | glb, fbx |

- **Coût :** 25 crédits (pricing).

**`POST /v3/animations/retarget`** (`…/animations-retarget.md`)
- **Paramètres :**
  - `input` : task_id du modèle riggé.
  - `animation` (un seul) ou `animations` (5 au plus).
  - `out_format` : glb ou fbx.
  - `export_with_geometry` : défaut true.
  - `animate_in_place` : défaut false.
  - `bake_animation` : deprecated.
- **Presets des rigs v2.5 et v3.0 :** preset:idle, walk, run, dive, climb, jump, slash, shoot, hurt, fall, turn, preset:quadruped:walk, preset:hexapod:walk, preset:octopod:walk, preset:serpentine:march, preset:aquatic:march.
- **Presets du rig v1.0 (biped seulement) :** 101 presets `preset:biped:*` relevés (afraid, agree, angry_01…, dance_01 à 06, idle, run, walk, wave_goodbye_02…). La liste complète figure sur la page source.
- **Coût :** 10 crédits par animation.

### 2.4 Autres auto-rigs sur fal

**Non trouvé.** La recherche `q=rig` ne remonte que les deux endpoints Meshy.

---

## 3. Mouvement (motion)

### 3.1 fal-ai/hunyuan-motion et /fast

Sources : `https://fal.ai/models/fal-ai/hunyuan-motion/llms.txt` et `…/hunyuan-motion/fast/llms.txt`.

**Paramètres**

| Paramètre | Type | Défaut | Plage |
|---|---|---|---|
| prompt | string (requis) | | |
| seed | int | | |
| duration | float | 5 | 0.5 à 12 s |
| guidance_scale | float | 5 | 1 à 10 |
| output_format | enum | fbx | fbx, dict |

- **Sortie :** `fbx_file` (File), `motion_json` (File), `seed`.
- **Prix :** 0,08 $ pour le modèle 1B ; 0,06 $ pour /fast (0.46B).

**Structure exacte du JSON « dict » renvoyé par fal : non trouvée.** La page dit seulement « raw JSON » et « Generated motion data as JSON ».

**Ce que dit le code amont** (`https://github.com/Tencent-Hunyuan/HY-Motion-1.0`, branche `master`). On peut supposer, sans preuve, que fal sérialise cette sortie.
- `hymotion/utils/t2m_runtime.py` : avec `output_format == "dict"`, le runtime renvoie le `model_output` brut au lieu d'écrire un FBX.
- `hymotion/pipeline/motion_diffusion.py`, `decode_motion_from_latent` : il appelle `_decode_o6dp(..., num_joints=22)` et renvoie un dict contenant :
  - `latent_denorm` (B, L, 201)
  - `keypoints3d` (B, L, 22, 3) : positions des joints, recalées au sol (y min = 0)
  - `rot6d` (B, L, 22, 6) : **rotations en représentation 6D**, joint 0 = racine
  - `transl` (B, L, 3) : translation de la racine, lissée par Savitzky-Golay
  - `root_rotations_mat` (B, L, 3, 3)
  - `text`
- **Cadence :** `output_mesh_fps` vaut **30** par défaut, et la longueur vaut `round(duration × 30)` images.
- **Squelette :** 22 joints du corps, ordre SMPL-H ou SMPL (`scripts/gradio/static/assets/dump_wooden/joint_names.json`) : Pelvis, L_Hip, R_Hip, Spine1, L_Knee, R_Knee, Spine2, L_Ankle, R_Ankle, Spine3, L_Foot, R_Foot, Neck, L_Collar, R_Collar, Head, L_Shoulder, R_Shoulder, L_Elbow, R_Elbow, L_Wrist, R_Wrist. Le fichier liste ensuite 30 joints de doigts, soit 52 au total, mais le décodage est fait à 22.
- **Export FBX :** `hymotion/utils/smplh2woodfbx.py` (mapping SMPLH_JOINT2NUM) applique les rotations sur le mannequin `assets/wooden_models/boy_Rigging_smplx_tex.fbx`.

**Licence** (`License.txt`) : « Tencent HY-MOTION 1.0 Community License ».
- Elle porte la mention « THIS LICENSE AGREEMENT DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA ».
- Elle exige une licence spécifique au-delà de 1 M d'utilisateurs actifs mensuels.
- **Point à faire trancher** : nous sommes en France, même si l'appel passe par fal (relevé factuel, pas un avis juridique).

### 3.2 Meshy Text to Motion (API directe)

Source : `https://docs.meshy.ai/api/text-to-motion.md`. Cette API n'est pas dans la spec OpenAPI, selon llms.txt.

**`POST /openapi/v1/text-to-motion`**
- **Paramètres :**
  - `prompt` : 400 car. max.
  - `mode` : `prime` (FBX, 10 crédits, défaut) ou `swift` (BVH, 3 crédits).
  - `duration` : requis, de 2 à 10 s par pas de 0,5.
- **Sortie :** `motion_url`, `motion_format` (fbx ou bvh), `duration_ms`, `mode`. Les fichiers sont gardés 3 jours.
- **Application à un personnage :** `POST /openapi/v1/animations` avec `motion_task_id`. Le rig doit être biped ; un quadrupède est refusé.
- **Structure du squelette FBX ou BVH :** non trouvée.

### 3.3 Kimodo (NVIDIA)

**Ce que c'est.** Un modèle de diffusion cinématique texte → mouvement, avec contraintes (trajectoire, poses clés, mains et pieds). Il a été publié en mars 2026 (arXiv 2603.15546). Sources : `https://research.nvidia.com/labs/sil/projects/kimodo` et `https://github.com/nv-tlabs/kimodo`.

**Licences** (README GitHub)
- Code : Apache-2.0.
- Poids : « NVIDIA Open Model » license pour la plupart, « NVIDIA R&D Model » pour Kimodo-SMPLX-RP-v1.

**Squelettes et formats**
- Squelettes : SOMA (v1.1, v1.2), Unitree G1 et SMPL-X.
- Formats : NPZ maison ; CSV qpos MuJoCo pour G1 ; NPZ AMASS pour SMPL-X.
- **Cadence : non trouvée.**

**API hébergée**
- **Aucune chez NVIDIA ni sur fal.** La démo officielle est locale (`kimodo_demo`).
- **Déploiement communautaire non officiel :** `https://replicate.com/sprited/kimodo`. Entrées : prompt, duration (0.5 à 30 s par segment), samples (1 à 16), steps (10 à 500), model (SOMA ou G1), output_format (GLB, BVH, NPZ, FBX), constraints_json et custom_fbx (personnage riggé Mixamo pour le retarget). **Prix : non trouvé.**

### 3.4 GVHMR (vidéo → mouvement)

**API hébergée :** non trouvée sur fal (`q=gvhmr` vide) ni sur Replicate (recherche sans résultat pertinent). Il existe une démo HuggingFace Space `LittleFrog/GVHMR` et un Colab (`https://github.com/zju3dv/GVHMR`).

**Licence** (`https://raw.githubusercontent.com/zju3dv/GVHMR/main/LICENSE`) : « educational, research and non-profit purposes only », et « prohibited for commercial use ». **Usage commercial exclu.**

**Format de sortie et cadence :** non trouvés sur la page lue.

---

## 4. Bibliothèque d'animations Meshy

**Sources**
- Page `https://docs.meshy.ai/api/animation-library.md`.
- Liste JSON publique : `https://api.meshy.ai/web/public/animations/resources`, lue le 31/10/2026, **680 entrées**, action_id de −2 à 696 avec des trous.
- L'endpoint officiel équivalent, sans crédit mais authentifié, est `GET /openapi/v1/animations/library`, avec les filtres search, category, sub_category et action_ids (`https://docs.meshy.ai/api/animation.md`).

**Répartition par catégorie**

| Catégorie | Nombre | Sous-catégories (nombre) |
|---|---|---|
| WalkAndRun | 178 | Walking 88, Running 48, CrouchWalking 19, TurningAround 20, Swimming 3 |
| BodyMovements | 158 | Acting 68, HangingfromLedge 21, Climbing 18, Jumping 16, FallingFreely 14, PerformingStunt 11, VaultingOverObstacle 10 |
| DailyActions | 157 | Interacting 45, Transitioning 34, Idle 25, WorkingOut 14, PickingUpItem 12, LookingAround 11, Sleeping 10, Pushing 4, Drinking 2 |
| Fighting | 154 | AttackingwithWeapon 38, Punching 38, Transitioning 26, Blocking 18, CastingSpell 12, GettingHit 11, Dying 11 |
| Dancing | 33 | Dancing 33 |

**Remarques**
- Les identifiants −2 (Walking) et −1 (Running) sont marqués `isDefault: true`. Ce sont les `basic_animations` livrées avec le rig. fal n'accepte que 0 à 696.
- Le champ `isFree` vaut true pour 22 entrées.
- Le champ `rigType` vaut style_02 pour 671 entrées, style_03 pour 5, style_01 pour 2 et biped pour 2. Sa signification n'est pas trouvée.
- Exemples cités par la doc : 92 = « Double Combo Attack », 0 = « Idle ».

**Paramètres de l'endpoint `POST /openapi/v1/animations`**
- `rig_task_id`, plus **un seul** choix parmi : `action_id`, `action_ids` (1 à 10, rendus en un seul fichier avec un clip par action, dans l'ordre et sous le nom de la bibliothèque) ou `motion_task_id`.
- `post_process.operation_type` : `change_fps` (fps 24, 25, 30 ou 60, défaut 30), `fbx2usdz` ou `extract_armature`.

**Sortie :** animation_glb_url, animation_fbx_url, processed_usdz_url, processed_armature_fbx_url, processed_animation_fps_fbx_url.

**Coût :** 3 crédits par action.

La table complète se trouve en **annexe A**.

---

## 5. Modèles d'image pour les références de texture (fal)

| endpoint_id | Paramètres clés | Prix affiché | Source |
|---|---|---|---|
| fal-ai/nano-banana-2/edit | prompt ; image_urls (14 références au total, contexte compris) ; resolution 0.5K, 1K (déf.), 2K ou 4K ; aspect_ratio auto…8:1 ; num_images 1 à 4 ; output_format png, jpeg ou webp ; thinking_level minimal ou high | 0,08 $ par image ; 2K ×1,5 ; 4K ×2 ; 0.5K ×0,75 ; recherche web +0,015 $ | `https://fal.ai/models/fal-ai/nano-banana-2/edit/llms.txt` |
| fal-ai/nano-banana-pro/edit | idem ; resolution 1K, 2K ou 4K ; thinking « high » seulement | 0,15 $ par image ; 4K ×2 ; recherche web +0,015 $ | `…/fal-ai/nano-banana-pro/edit/llms.txt` |
| google/nano-banana-2.1/edit | resolution 1K, 2K ou 4K ; num_images 1 à 4 | tarif au jeton : texte 1,764 $ / 8,823 $ par M ; image 1,764 $ en entrée, 35,294 $ par M en sortie | `…/google/nano-banana-2.1/edit/llms.txt` |
| openai/gpt-image-2/edit | image_urls (16 max) ; quality auto, low, medium ou high (déf. high) ; background auto, transparent ou opaque ; mask_url ; num_images 1 à 10 | au jeton (image : 8 $ en entrée, 30 $ par M en sortie). Exemples par image en 1024×1024 : low 0,015 $, medium 0,061 $, high 0,219 $ | `…/openai/gpt-image-2/edit/llms.txt` et page `/models/openai/gpt-image-2/edit` |
| openai/gpt-image-2.5/flare/edit et …/sunburst/edit | image_urls (16) ; quality auto, low, medium, high, xhigh ou max ; background | même grille au jeton que gpt-image-2. **Différence entre flare et sunburst : non trouvée** | `…/gpt-image-2.5/flare/edit/llms.txt`, `…/sunburst/edit/llms.txt` |
| bytedance/seedream/v5/lite/edit | image_urls (10 max, les 10 derniers sont gardés) ; image_size (déf. auto_2K, de 2560×1440 à 4096×4096) ; num_images 1 à 6 ; max_images 1 à 15 ; output_format jpeg ou png | 0,035 $ par image | `…/bytedance/seedream/v5/lite/edit/llms.txt` |

**Autres modèles listés** (`q=seedream`) : seedream v5 pro/edit, v5 flash/edit et v5 pro/layerize.

---

## 6. ez-tree (github.com/dgreenheck/ez-tree)

### 6.1 Licences

**Code.** Le fichier `LICENSE` est sous licence **MIT**, « Copyright (c) 2024 Daniel Greenheck ». Le dépôt déclare spdx MIT. Sources : `https://raw.githubusercontent.com/dgreenheck/ez-tree/main/LICENSE` et `https://api.github.com/repos/dgreenheck/ez-tree`.

**Textures sur la branche `main`** (`src/app/public/textures/LICENSE.md`)
- **Écorces :** 11 jeux Bark001 à Bark015, en 1K JPG (Color, NormalGL, Roughness). Ils proviennent d'ambientcg.com, sous **CC0 1.0**.
- **Feuilles :** ash, aspen, oak et pine, en PNG. Le fichier précise « licensed under the project's own license (see repository LICENSE) », c'est-à-dire MIT.
- **Changement de version :** depuis la 2.0.0, la **bibliothèque n'embarque plus aucune texture**. L'appelant fournit ses `THREE.Texture` (CHANGELOG).

**Textures du paquet npm 1.1.0** (`https://registry.npmjs.org/@dgreenheck/ez-tree/-/ez-tree-1.1.0.tgz`)
- **Écorces embarquées :** birch, oak, pine et willow, avec les cartes ao, color, normal et roughness en 1k. Le fichier `src/lib/assets/bark/README.md` en indique les sources : texturecan.com/details/221 (birch), texturecan.com/details/588 (pine), polyhaven.com/a/bark_brown_02 (oak), polyhaven.com/a/bark_willow_02 (willow).
- **Licence de ces textures : non écrite dans le paquet.** Le seul fichier de licence est le MIT.
- **Feuilles embarquées :** ash, aspen, oak et pine, sans source indiquée.

### 6.2 Paquet npm

| Élément | Valeur |
|---|---|
| Nom | `@dgreenheck/ez-tree` |
| `dist-tags.latest` | **1.1.0**, publiée le 15/01/2026 (`https://registry.npmjs.org/@dgreenheck/ez-tree`) |
| Versions publiées | 0.1.2, 0.1.3, 0.1.4, 1.0.0, 1.0.1, 1.1.0 |
| Peer dependency | `three >=0.167` |
| Sorties du build | `build/ez-tree.es.js` et `build/ez-tree.umd.js` |

**Écart entre GitHub et npm.** Le `CHANGELOG.md` de `main` décrit une **2.0.0 du 16/07/2026**, alors que le `package.json` de `main` indique encore 1.1.0 et que la 2.0.0 **n'est pas publiée sur npm**. Pour avoir l'API 2.0 (LOD, `createGeometry`, textures fournies par l'appelant), il faut épingler un commit Git.

### 6.3 Presets intégrés

Ils sont identiques en 1.1.0 et sur `main` (`src/lib/presets/index.js`) : `Ash Small`, `Ash Medium`, `Ash Large`, `Aspen Small`, `Aspen Medium`, `Aspen Large`, `Bush 1`, `Bush 2`, `Bush 3`, `Oak Small`, `Oak Medium`, `Oak Large`, `Pine Small`, `Pine Medium`, `Pine Large`, `Trellis`.

### 6.4 API exportée

**Exports de `src/lib/index.js`**
- **npm 1.1.0 :** `Tree`, `Trellis`, `TreePreset`, `BarkType` (birch, oak, pine, willow), `Billboard` (single, double), `LeafType` (ash, aspen, pine, oak) et `TreeType` (deciduous, evergreen).
- **`main`, 2.0 :** `Tree`, `Trellis`, `TreePreset`, `Billboard` et `TreeType`. `BarkType` et `LeafType` ont été retirés, ce qui est un changement cassant.
- **`loadPreset`** est une fonction exportée par `presets/index.js` mais **pas réexportée** à la racine. On l'appelle par la méthode `tree.loadPreset(name)`.

**Classe `Tree extends THREE.Group`** (`src/lib/tree.js` sur main)
- `constructor(options = new TreeOptions())`
- `update(elapsedTime)` : animation du vent
- `loadPreset(name)`
- `loadFromJson(json)`
- `generate()`
- `generateLODs(levels = Tree.defaultLODLevels)`, depuis la 2.0
- `createGeometry(detail)`, depuis la 2.0, qui renvoie `{ branches, leaves }`

**Options `TreeOptions`** (`src/lib/options.js`)

| Groupe | Clés |
|---|---|
| général | `seed`, `type` |
| `bark` | `type`, `maps{color, ao, normal, roughness}`, `tint`, `flatShading`, `textured`, `textureScale{x, y}` |
| `branch` | `levels` ; `angle`, `children`, `gnarliness`, `length`, `radius`, `sections`, `segments`, `start`, `taper`, `twist` (indexés par niveau) ; `force{direction, strength}` |
| `leaves` | `type`, `map`, `billboard`, `angle`, `count`, `start`, `size`, `sizeVariance`, `tint`, `alphaTest`, `roundedNormals` |
| `trellis` | `enabled`, `position`, `width`, `height`, `spacing`, `force{strength, maxDistance, falloff}`, `cylinderRadius`, `visible`, `color` |

---

## 7. Réglages par moteur pour le registre ENGINES

Ce sont des **propositions**, au format de `backend/app/services/asset3d_service.py::ENGINES`. Les identifiants existants restent tels quels. Les nouveaux identifiants sont à valider.

| id proposé | endpoint(s) | Réglages à exposer (nom fournisseur → valeurs) | Drapeaux du registre |
|---|---|---|---|
| `tripo` (existant) | tripo3d/tripo/v2.5/image-to-3d + multiview | inchangé | inchangé |
| `tripo-h3.1` (existant) | tripo3d/h3.1/{image,multiview,text}-to-3d | texture, pbr, texture_quality standard/detailed, geometry_quality standard/detailed, face_limit 1000 à 2M, quad, texture_alignment, orientation, auto_size, model_seed, texture_seed ; **+ text-to-3d** (prompt, negative_prompt) | face_limit, quad et seed à True ; ajouter `text: True` |
| `tripo-p1` (nouveau) | tripo3d/p1/{image,text}-to-3d | texture (bool), face_limit 48 à 20000, model_seed | low-poly, pas de pbr ; draft True ; detailed False ; quad False |
| `tripo-p2` (nouveau) | tripo3d/p2/{image,text}-to-3d | texture, pbr, texture_quality fast/standard/detailed/extreme, texture_version, delight, face_limit 48 à 50000 (quad 25000), quad, export_uv, export_orientation, auto_size, seeds | face_limit, quad, seed et pbr à True ; detailed True (extreme) ; coût 1,00 à 1,30 $ |
| `tripo-remesh`, `tripo-segment` (outils) | tripo3d/tripo/remesh, …/segment | remesh : quad, face_limit 500 à 20000, bake, part_names ; segment : mesh_url seul | outils 3d-to-3d, hors génération |
| `hunyuan` (existant) | fal-ai/hunyuan3d/v2 | inchangé | inchangé |
| `hunyuan-3.1` (nouveau) | fal-ai/hunyuan-3d/v3.1/pro/{image,text}-to-3d | generate_type Normal/Geometry, enable_pbr, face_count 40000 à 1500000 ; vues back, left, right, top, bottom, left_front, right_front | multiview True (8 vues **nommées**, pas de liste ordonnée) ; max_images 8 ; pbr True ; face_limit True ; quad False ; formats glb, obj |
| `hunyuan-3.1-rapid` (nouveau) | …/v3.1/rapid/{image,text}-to-3d | enable_pbr, enable_geometry | draft True ; brouillon bon marché (0,225 $) |
| `hunyuan-topo` (outil) | fal-ai/hunyuan-3d/v3.1/smart-topology | polygon_type triangle/quadrilateral, face_level high/medium/low | outil de retopologie |
| `trellis` (existant) | fal-ai/trellis | inchangé | inchangé |
| `trellis-2` (nouveau) | fal-ai/trellis-2 | resolution 512/1024/1536, decimation_target 5000 à 2000000, texture_size 1024/2048/4096, remesh, seed ; les réglages ss/shape/tex_slat restent cachés (« avancé ») | face_limit True (en sommets) ; seed True ; formats glb |
| `rodin` (existant) | fal-ai/hyper3d/rodin | inchangé | inchangé |
| `rodin-2.5` (nouveau) | fal-ai/hyper3d/rodin/v2.5 (+ /text-to-3d) | tier Gen-2.5-*, quality_mesh_option (liste fermée Quad/Triangle), material PBR/Shaded/All/None, texture_mode, hd_texture, texture_delight, TAPose, geometry_file_format, seed, addons HighPack | tpose True ; quad True (via quality_mesh_option) ; pbr True ; formats glb, usdz, fbx, obj, stl |
| `rodin-2.5-fast` (nouveau) | …/v2.5/fast | tier Minimum/Extreme-Low/Low, quality_mesh_option ≤ 20K | draft True ; 0,10 $ |
| `meshy-7.1` (nouveau, voie fal) | meshy/v7.1/{image,text,multi-image}-to-3d | model_type standard/lowpoly/smart-topology/-t2, topology quad/triangle, target_polycount 100 à 300000, should_remesh, should_texture, enable_pbr, pose_mode a-pose/t-pose, geometry_resolution standard/2k/4k, texture_prompt, texture_image_url, enable_rigging, rigging_height_meters, animation_action_id | tpose True ; quad True ; face_limit True ; pbr True ; rig intégré |
| `meshy` (voie directe existante) | api.meshy.ai | ai_model latest/meshy-7.1/meshy-6/meshy-6-lite/meshy-t2/meshy-t2.5, texture_resolution 2k/4k/8k, image_enhancement, remove_lighting (meshy-6 seulement), decimation_mode 1 à 4, target_formats, auto_size et origin_at ; **retirer symmetry_mode (sans effet)** | |
| `triposr` (existant) | fal-ai/triposr | inchangé | inchangé |

**Rigging, registre à part (proposition `RIG_ENGINES`)**
- **`meshy-rig` (fal) :** fal-ai/meshy/rigging, avec height_meters, enable_animation et animation_action_id.
- **`meshy-rig-multi` (fal) :** …/rigging/multi-animation, avec animation_action_ids (1 à 10).
- **`meshy-rig-direct` :** /openapi/v1/rigging, puis /openapi/v1/animations avec action_ids et post_process.
- **`tripo-rig-direct` :** API Tripo v3 rig-check, puis rig (rig_type, spec mixamo/unity/unreal/vrm, model v3.0-20260909), puis retarget. **Hors fal, il faut une clé Tripo.**

**Mouvement (proposition `MOTION_ENGINES`)**
- **`hy-motion` (fal) :** fal-ai/hunyuan-motion, avec duration 0.5 à 12, guidance_scale 1 à 10, seed et output_format fbx/dict.
- **`hy-motion-fast` (fal) :** …/fast, mêmes réglages.
- **`meshy-motion` (direct) :** /openapi/v1/text-to-motion, avec mode prime/swift et duration 2 à 10 par pas de 0,5. On l'applique ensuite par motion_task_id.

**Références de texture (proposition `TEXREF_ENGINES`)**
- `nano-banana-2` : fal-ai/nano-banana-2/edit.
- `nano-banana-pro` : fal-ai/nano-banana-pro/edit.
- `gpt-image-2` : openai/gpt-image-2/edit.
- `seedream-5-lite` : bytedance/seedream/v5/lite/edit.

---

## 8. Inconnues restantes

1. **Rig Tripo via fal.** Les sorties fal mentionnent des endpoints « rig / rig-check », mais aucun n'est listé et les URL devinées renvoient 404. Il faut confirmer auprès de fal ou réessayer plus tard.
2. **Structure du JSON `motion_json` de fal-ai/hunyuan-motion** (`output_format: dict`) : non documentée. L'hypothèse tirée du code amont est rot6d (L, 22, 6), transl (L, 3) et keypoints3d (L, 22, 3), à 30 i/s. Un appel de test à 0,06 $ permettrait de la vérifier.
3. **Licence HY-Motion hors du territoire UE et Royaume-Uni.** L'effet d'un usage depuis la France via un service hébergé (fal) est à faire trancher ; ce n'est pas un avis juridique.
4. **Champs d'`AnimationClip` et de `BasicAnimations`** sur fal (Meshy multi-animation) : non documentés.
5. **Sens de `rigType` (style_01, 02 ou 03) dans la bibliothèque Meshy** : non documenté.
6. **Prix du crédit Meshy en USD et prix du crédit Tripo en USD** : non trouvés. Pour Tripo, seul « 1 credit = ¥0.07 CNY » a été trouvé.
7. **« $0.01 per units »** pour Tripo remesh et segment : le nombre d'unités par appel est inconnu.
8. **Différence entre gpt-image-2.5 flare et sunburst** : non trouvée.
9. **Kimodo** : cadence, prix Replicate et matériel inconnus. Le déploiement Replicate est communautaire et non officiel.
10. **GVHMR** : aucune API hébergée trouvée, et la licence interdit l'usage commercial. Le format de sortie et la cadence n'ont pas été relus.
11. **ez-tree** : la 2.0.0 n'est pas publiée sur npm, et la licence des textures d'écorce du paquet 1.1.0 (texturecan et polyhaven) n'est pas écrite dans le paquet.
12. **Pages listées mais non relues en détail** : tripo3d/p1/text-to-3d, hunyuan rapid/text-to-3d, rodin v2.5/text-to-3d/fast, meshy/v7.1/multi-image-to-3d, fal-ai/meshy/v6/*, fal-ai/hunyuan3d-v3/*, fal-ai/hunyuan3d-v21, tripo3d/triposplat et fal-ai/sam-3/3d-objects.
13. **Squelette des clips Meshy Text to Motion (FBX ou BVH)** : noms des joints non documentés.

---

## Annexe A : bibliothèque d'animations Meshy (680 entrées)

**Source :** `https://api.meshy.ai/web/public/animations/resources`, lue le 31/10/2026, liste publique référencée par `https://docs.meshy.ai/api/animation-library.md`. Les identifiants −2 et −1 sont les animations de base du rig et ne sont pas acceptés par fal (plage 0 à 696).

| action_id | key | nom | catégorie | sous-catégorie | rigType |
|---|---|---|---|---|---|
| -2 | Walking_man | Walking | WalkAndRun | Walking | biped |
| -1 | Running | Running | WalkAndRun | Running | biped |
| 0 | Idle | Idle | DailyActions | Idle | style_01 |
| 1 | Walking_Woman | Walking Woman | WalkAndRun | Walking | style_01 |
| 2 | Alert | Alert | DailyActions | LookingAround | style_02 |
| 3 | Arise | Arise | DailyActions | LookingAround | style_02 |
| 4 | Attack | Attack | Fighting | AttackingwithWeapon | style_02 |
| 5 | BackLeft_run | BackLeft Run | WalkAndRun | Running | style_02 |
| 6 | BackRight_Run | BackRight Run | WalkAndRun | Running | style_02 |
| 7 | BeHit_FlyUp | BeHit FlyUp | Fighting | GettingHit | style_02 |
| 8 | Dead | Dead | Fighting | Dying | style_02 |
| 9 | ForwardLeft_Run_Fight | ForwardLeft Run Fight | Fighting | Transitioning | style_02 |
| 10 | ForwardRight_Run_Fight | ForwardRight Run Fight | Fighting | Transitioning | style_02 |
| 11 | Idle_02 | Idle 1 | DailyActions | Idle | style_03 |
| 12 | Idle_03 | Idle 2 | DailyActions | Idle | style_03 |
| 13 | Jump_Run | Jump Run | WalkAndRun | Running | style_02 |
| 14 | Run_02 | Run 2 | WalkAndRun | Running | style_02 |
| 15 | Run_03 | Run 3 | WalkAndRun | Running | style_02 |
| 16 | RunFast | Run Fast | WalkAndRun | Running | style_02 |
| 17 | Skill_01 | Skill 1 | BodyMovements | Acting | style_03 |
| 18 | Skill_02 | Skill 2 | BodyMovements | Acting | style_03 |
| 19 | Skill_03 | Skill 3 | BodyMovements | Acting | style_03 |
| 20 | Walk_Fight_Back | Walk Fight Back | WalkAndRun | Walking | style_02 |
| 21 | Walk_Fight_Forward | Walk Fight Forward | WalkAndRun | Walking | style_02 |
| 22 | FunnyDancing_01 | Funny Dancing 1 | Dancing | Dancing | style_02 |
| 23 | FunnyDancing_02 | Funny Dancing 2 | Dancing | Dancing | style_02 |
| 24 | FunnyDancing_03 | Funny Dancing 3 | Dancing | Dancing | style_02 |
| 25 | Agree_Gesture | Agree Gesture | DailyActions | Interacting | style_02 |
| 26 | Angry_Stomp | Angry Stomp | DailyActions | Interacting | style_02 |
| 27 | Big_Heart_Gesture | Big Heart Gesture | BodyMovements | Acting | style_02 |
| 28 | Big_Wave_Hello | Big Wave Hello | DailyActions | Interacting | style_02 |
| 29 | Call_Gesture | Call Gesture | BodyMovements | Acting | style_02 |
| 30 | Casual_Walk | Casual Walk | WalkAndRun | Walking | style_02 |
| 31 | Catching_Breath | Catching Breath | BodyMovements | Acting | style_02 |
| 32 | Chair_Sit_Idle_F | Chair Sit Idle Female | DailyActions | Idle | style_02 |
| 33 | Chair_Sit_Idle_M | Chair Sit Idle Male | DailyActions | Idle | style_02 |
| 34 | Checkout_Gesture | Checkout Gesture | DailyActions | Interacting | style_02 |
| 35 | Clapping_Run | Clapping Run | BodyMovements | Acting | style_02 |
| 36 | Confused_Scratch | Confused Scratch | DailyActions | Idle | style_02 |
| 37 | Discuss_While_Moving | Discuss While Moving | DailyActions | Interacting | style_02 |
| 38 | Dozing_Elderly | Dozing Elderly | DailyActions | Idle | style_02 |
| 39 | Excited_Walk_F | Excited Walk Female | BodyMovements | Acting | style_02 |
| 40 | Excited_Walk_M | Excited Walk Male | BodyMovements | Acting | style_02 |
| 41 | Formal_Bow | Formal Bow | DailyActions | Interacting | style_02 |
| 42 | Gentlemans_Bow | Gentlemans Bow | DailyActions | Interacting | style_02 |
| 43 | Handbag_Walk | Handbag Walk | BodyMovements | Acting | style_02 |
| 44 | Happy_jump_f | Happy Jump Female | BodyMovements | Acting | style_02 |
| 45 | Indoor_Play | Indoor Play | BodyMovements | Acting | style_02 |
| 46 | Jump_Rope | Jump Rope | BodyMovements | Acting | style_02 |
| 47 | Listening_Gesture | Listening Gesture | DailyActions | Interacting | style_02 |
| 48 | Mirror_Viewing | Mirror Viewing | DailyActions | Idle | style_02 |
| 49 | Motivational_Cheer | Motivational Cheer | DailyActions | Interacting | style_02 |
| 50 | Phone_Call_Gesture | Phone Call Gesture | DailyActions | Interacting | style_02 |
| 51 | Shouting_Angrily | Shouting Angrily | BodyMovements | Acting | style_02 |
| 52 | Sit_to_Stand_Transition_F | Sit to Stand Transition Female | DailyActions | Transitioning | style_02 |
| 53 | Sit_to_Stand_Transition_M | Sit to Stand Transition Male | DailyActions | Transitioning | style_02 |
| 54 | Squat_Stance | Squat Stance | Dancing | Dancing | style_02 |
| 55 | Stage_Walk | Stage Walk | WalkAndRun | Walking | style_02 |
| 56 | Stand_and_Chat | Stand and Chat | DailyActions | Interacting | style_02 |
| 57 | Stand_to_Sit_Transition_M | Stand to Sit Transition Male | DailyActions | Transitioning | style_02 |
| 58 | Step_to_Sit_Transition | Step to Sit Transition | DailyActions | Transitioning | style_02 |
| 59 | Victory_Cheer | Victory Cheer | BodyMovements | Acting | style_02 |
| 60 | Walk_to_Sit | Walk to Sit | DailyActions | Transitioning | style_02 |
| 61 | happy_jump_m | Happy Jump Male | BodyMovements | Acting | style_02 |
| 62 | penguin_walk | Penguin Walk | BodyMovements | Acting | style_02 |
| 63 | Arm_Circle_Shuffle | Arm Circle Shuffle | Dancing | Dancing | style_02 |
| 64 | All_Night_Dance | All Night Dance | Dancing | Dancing | style_02 |
| 65 | Bass_Beats | Bass Beats | Dancing | Dancing | style_02 |
| 66 | Boom_Dance | Boom Dance | Dancing | Dancing | style_02 |
| 67 | Bubble_Dance | Bubble Dance | Dancing | Dancing | style_02 |
| 68 | Cherish_Pop_Dance | Cherish Pop Dance | Dancing | Dancing | style_02 |
| 69 | Crystal_Beads | Crystal Beads | Dancing | Dancing | style_02 |
| 70 | Cardio_Dance | Cardio Dance | Dancing | Dancing | style_02 |
| 71 | Denim_Pop_Dance | Denim Pop Dance | Dancing | Dancing | style_02 |
| 72 | Dont_You_Dare | Dont You Dare | Dancing | Dancing | style_02 |
| 73 | Fast_Lightning | Fast Lightning | Dancing | Dancing | style_02 |
| 74 | Gangnam_Groove | Gangnam Groove | Dancing | Dancing | style_02 |
| 75 | Indoor_Swing | Indoor Swing | Dancing | Dancing | style_02 |
| 76 | Love_You_Pop_Dance | Love You Pop Dance | Dancing | Dancing | style_02 |
| 77 | Magic_Genie | Magic Genie | Dancing | Dancing | style_02 |
| 78 | Not_Your_Mom | Rhythmic Dance | Dancing | Dancing | style_02 |
| 79 | OMG_Groove | OMG Groove | Dancing | Dancing | style_02 |
| 80 | Pop_Dance_LSA2 | Pop Dance LSA2 | Dancing | Dancing | style_02 |
| 81 | Pod_Baby_Groove | Pod Baby Groove | Dancing | Dancing | style_02 |
| 82 | Shake_It_Off_Dance | Shake It Off Dance | Dancing | Dancing | style_02 |
| 83 | Superlove_Pop_Dance | Superlove Pop Dance | Dancing | Dancing | style_02 |
| 84 | You_Groove | You Groove | Dancing | Dancing | style_02 |
| 85 | Axe_Stance | Axe Stance | Fighting | Transitioning | style_02 |
| 86 | Basic_Jump | Jump Attack | Fighting | AttackingwithWeapon | style_02 |
| 87 | Boxing_Practice | Boxing Practice | Fighting | Punching | style_02 |
| 88 | Chest_Pound_Taunt | Chest Pound Taunt | Fighting | Transitioning | style_02 |
| 89 | Combat_Stance | Combat Idel | Fighting | AttackingwithWeapon | style_02 |
| 90 | Counterstrike | Counterstrike | Fighting | Punching | style_02 |
| 91 | Double_Blade_Spin | Double Blade Spin | Fighting | AttackingwithWeapon | style_02 |
| 92 | Double_Combo_Attack | Double Combo Attack | Fighting | AttackingwithWeapon | style_02 |
| 93 | Dodge_and_Counter | Dodge and Counter | Fighting | Punching | style_02 |
| 94 | Flying_Fist_Kick | Flying Fist Kick | Fighting | Punching | style_02 |
| 95 | Gun_Hold_Left_Turn | Gun Hold Left Turn | Fighting | AttackingwithWeapon | style_02 |
| 96 | Kung_Fu_Punch | Kung Fu Punch | Fighting | Punching | style_02 |
| 97 | Left_Slash | Left Slash | Fighting | AttackingwithWeapon | style_02 |
| 98 | Run_and_Shoot | Run and Shoot | Fighting | AttackingwithWeapon | style_02 |
| 99 | Reaping_Swing | Reaping Swing | Fighting | Transitioning | style_02 |
| 100 | Rightward_Spin | Spin Down and Stand Up | Fighting | Transitioning | style_02 |
| 101 | Sword_Shout | Sword Shout | BodyMovements | Acting | style_02 |
| 102 | Sword_Judgment | Sword Judgment | Fighting | AttackingwithWeapon | style_02 |
| 103 | Simple_Kick | Simple Kick | Fighting | AttackingwithWeapon | style_02 |
| 104 | Side_Shot | Side Shot | Fighting | AttackingwithWeapon | style_02 |
| 105 | Triple_Combo_Attack | Triple Combo Attack | Fighting | AttackingwithWeapon | style_02 |
| 106 | Confident_Walk | Hot walk | WalkAndRun | Walking | style_02 |
| 107 | Confident_Strut | Confident Strut | WalkAndRun | Walking | style_02 |
| 108 | Flirty_Strut | Flirty Strut | WalkAndRun | Walking | style_02 |
| 109 | Groovy_Walk | Groovy Walk | BodyMovements | Acting | style_02 |
| 110 | Hello_Run | Hello Run | WalkAndRun | Running | style_02 |
| 111 | Injured_Walk | Injured Walk | WalkAndRun | Walking | style_02 |
| 112 | Monster_Walk | Frankenstein Walk | WalkAndRun | Walking | style_02 |
| 113 | Mummy_Stagger | Mummy Stagger | BodyMovements | Acting | style_02 |
| 114 | Proud_Strut | Proud Strut | WalkAndRun | Walking | style_02 |
| 115 | Quick_Walk | Quick Walk | WalkAndRun | Walking | style_02 |
| 116 | Run_to_Walk_Transition | Run to Walk Transition | WalkAndRun | Walking | style_02 |
| 117 | Red_Carpet_Walk | Red Carpet Walk | WalkAndRun | Walking | style_02 |
| 118 | Skip_Forward | Skip Forward | WalkAndRun | Walking | style_02 |
| 119 | Slow_Orc_Walk | Slow Orc Walk | WalkAndRun | Walking | style_02 |
| 120 | Touch_and_Run | Touch and Run | WalkAndRun | Running | style_02 |
| 121 | Thoughtful_Walk | Thoughtful Walk | WalkAndRun | Walking | style_02 |
| 122 | Texting_Walk | Texting Walk | WalkAndRun | Walking | style_02 |
| 123 | Unsteady_Walk | Unsteady Walk | WalkAndRun | Walking | style_02 |
| 124 | Walking_with_Phone | Walking with Phone | WalkAndRun | Walking | style_02 |
| 125 | Charged_Spell_Cast | Charged Spell Cast | Fighting | CastingSpell | style_02 |
| 126 | Charged_Spell_Cast_1 | Charged Spell Cast 1 | Fighting | CastingSpell | style_02 |
| 127 | Charged_Ground_Slam | Charged Ground Slam | Fighting | CastingSpell | style_02 |
| 128 | Heavy_Hammer_Swing | Heavy Hammer Swing | Fighting | AttackingwithWeapon | style_02 |
| 129 | mage_soell_cast | Mage Soell Cast | Fighting | CastingSpell | style_02 |
| 130 | mage_soell_cast_1 | Mage Soell Cast 1 | Fighting | CastingSpell | style_02 |
| 131 | mage_soell_cast_2 | Mage Soell Cast 2 | Fighting | CastingSpell | style_02 |
| 132 | mage_soell_cast_3 | Mage Soell Cast 3 | Fighting | CastingSpell | style_02 |
| 133 | mage_soell_cast_4 | Mage Soell Cast 4 | Fighting | CastingSpell | style_02 |
| 134 | mage_soell_cast_5 | Mage Soell Cast 5 | Fighting | CastingSpell | style_02 |
| 135 | mage_soell_cast_6 | Mage Soell Cast 6 | Fighting | CastingSpell | style_02 |
| 136 | mage_soell_cast_7 | Mage Soell Cast 7 | Fighting | CastingSpell | style_02 |
| 137 | mage_soell_cast_8 | Mage Soell Cast 8 | Fighting | CastingSpell | style_02 |
| 138 | Block1 | Block1 | Fighting | Blocking | style_02 |
| 139 | Block2 | Block2 | Fighting | Blocking | style_02 |
| 140 | Block3 | Block3 | Fighting | Blocking | style_02 |
| 141 | Block4 | Block4 | Fighting | Blocking | style_02 |
| 142 | Block5 | Block5 | Fighting | Blocking | style_02 |
| 143 | Block6 | Block6 | Fighting | Blocking | style_02 |
| 144 | Block8 | Block8 | Fighting | Blocking | style_02 |
| 145 | Block9 | Block9 | Fighting | Blocking | style_02 |
| 146 | Block10 | Block10 | Fighting | Blocking | style_02 |
| 147 | Sword_Parry | Sword Parry | Fighting | Blocking | style_02 |
| 148 | Sword_Parry_Backward | Sword Parry Backward | Fighting | Blocking | style_02 |
| 149 | Two_Handed_Parry | Two-handed Parry | Fighting | Blocking | style_02 |
| 150 | Hit_Reaction_with_Bow | Hit Reaction with Bow | Fighting | Blocking | style_02 |
| 151 | Sword_Parry_Backward_1 | Sword Parry Backward 1 | Fighting | Blocking | style_02 |
| 152 | Sword_Parry_Backward_2 | Sword Parry Backward 2 | Fighting | Blocking | style_02 |
| 153 | Sword_Parry_Backward_3 | Sword Parry Backward 3 | Fighting | Blocking | style_02 |
| 154 | Sword_Parry_Backward_4 | Sword Parry Backward 4 | Fighting | Blocking | style_02 |
| 155 | Sword_Parry_Backward_5 | Sword Parry Backward 5 | Fighting | Blocking | style_02 |
| 156 | Stand_Dodge | Stand Dodge | Fighting | Transitioning | style_02 |
| 157 | Stand_Dodge_1 | Stand Dodge 1 | Fighting | Transitioning | style_02 |
| 158 | Roll_Dodge | Roll Dodge | Fighting | Transitioning | style_02 |
| 159 | Roll_Dodge_1 | Roll Dodge 1 | Fighting | Transitioning | style_02 |
| 160 | Roll_Dodge_2 | Roll Dodge 2 | Fighting | Transitioning | style_02 |
| 161 | Roll_Dodge_3 | Roll Dodge 3 | Fighting | Transitioning | style_02 |
| 162 | Stand_Dodge_2 | Stand Dodge 2 | Fighting | Transitioning | style_02 |
| 163 | Roll_Dodge_4 | Roll Dodge 4 | Fighting | Transitioning | style_02 |
| 164 | Stand_Dodge_3 | Stand Dodge 3 | Fighting | Transitioning | style_02 |
| 165 | Kneeling_Reload | Kneeling Reload | Fighting | Transitioning | style_02 |
| 166 | Running_Reload | Running Reload | Fighting | Transitioning | style_02 |
| 167 | Slow_Walk_Reload | Slow Walk Reload | Fighting | Transitioning | style_02 |
| 168 | Prone_Reload | Prone Reload | Fighting | Transitioning | style_02 |
| 169 | Forward_Reload_Subtle | Forward Reload (subtle) | Fighting | Transitioning | style_02 |
| 170 | Standing_Reload | Standing Reload | Fighting | Transitioning | style_02 |
| 171 | Hit_Reaction_to_Waist | Hit Reaction to Waist | Fighting | Transitioning | style_02 |
| 172 | Electrocution_Reaction | Electrocution Reaction | Fighting | GettingHit | style_02 |
| 173 | Slap_Reaction | Slap Reaction | Fighting | GettingHit | style_02 |
| 174 | Face_Punch_Reaction | Face Punch Reaction | Fighting | GettingHit | style_02 |
| 175 | Face_Punch_Reaction_1 | Face Punch Reaction 1 | Fighting | GettingHit | style_02 |
| 176 | Face_Punch_Reaction_2 | Face Punch Reaction 2 | Fighting | GettingHit | style_02 |
| 177 | Gunshot_Reaction | Gunshot Reaction | Fighting | GettingHit | style_02 |
| 178 | Hit_Reaction | Hit Reaction | Fighting | GettingHit | style_02 |
| 179 | Hit_Reaction_1 | Hit Reaction 1 | Fighting | GettingHit | style_02 |
| 180 | Shot_in_the_Back_and_Fall | Shot in the Back and Fall | Fighting | GettingHit | style_02 |
| 181 | Electrocuted_Fall | Electrocuted Fall | Fighting | Dying | style_02 |
| 182 | Shot_and_Blown_Back | Shot and Blown Back | Fighting | Dying | style_02 |
| 183 | Shot_and_Fall_Backward | Shot and Fall Backward | Fighting | Dying | style_02 |
| 184 | Shot_and_Fall_Forward | Shot and Fall Forward | Fighting | Dying | style_02 |
| 185 | Shot_and_Slow_Fall_Backward | Shot and Slow Fall Backward | Fighting | Dying | style_02 |
| 186 | Strangled_and_Fall_Forward | Strangled and Fall Forward | Fighting | Dying | style_02 |
| 187 | Knock_Down | Knock Down | Fighting | Dying | style_02 |
| 188 | Fall_Dead_from_Abdominal_Injury | Fall Dead from Abdominal Injury | Fighting | Dying | style_02 |
| 189 | dying_backwards | Dying Backwards | Fighting | Dying | style_02 |
| 190 | Knock_Down_1 | Knock Down 1 | Fighting | Dying | style_02 |
| 191 | Left_Jab_from_Guard | Left Jab from Guard | Fighting | Punching | style_02 |
| 192 | Right_Jab_from_Guard | Right Jab from Guard | Fighting | Punching | style_02 |
| 193 | Left_Hook_from_Guard | Left Hook from Guard | Fighting | Punching | style_02 |
| 194 | Right_Uppercut_from_Guard | Right Uppercut from Guard | Fighting | Punching | style_02 |
| 195 | Right_Upper_Hook_from_Guard | Right Upper Hook from Guard | Fighting | Punching | style_02 |
| 196 | Left_Uppercut_from_Guard | Left Uppercut from Guard | Fighting | Punching | style_02 |
| 197 | Left_Short_Hook_from_Guard | Left Short Hook from Guard | Fighting | Punching | style_02 |
| 198 | Punch_Combo | Punch Combo | Fighting | Punching | style_02 |
| 199 | Weapon_Combo | Weapon Combo | Fighting | Punching | style_02 |
| 200 | Punch_Combo_1 | Punch Combo 1 | Fighting | Punching | style_02 |
| 201 | Punch_Combo_2 | Punch Combo 2 | Fighting | Punching | style_02 |
| 202 | Weapon_Combo_1 | Weapon Combo 1 | Fighting | Punching | style_02 |
| 203 | Punch_Combo_3 | Punch Combo 3 | Fighting | Punching | style_02 |
| 204 | Punch_Combo_4 | Punch Combo 4 | Fighting | Punching | style_02 |
| 205 | Punch_Combo_5 | Punch Combo 5 | Fighting | Punching | style_02 |
| 206 | Spartan_Kick | Spartan Kick | Fighting | Punching | style_02 |
| 207 | Roundhouse_Kick | Roundhouse Kick | Fighting | Punching | style_02 |
| 208 | Lunge_Roundhouse_Kick | Lunge Roundhouse Kick | Fighting | Punching | style_02 |
| 209 | Boxing_Guard_Right_Straight_Kick | Boxing Guard, Right Straight Kick | Fighting | Punching | style_02 |
| 210 | Boxing_Guard_Prep_Straight_Punch | Boxing Guard, Prep Straight Punch | Fighting | Punching | style_02 |
| 211 | Boxing_Guard_Step_Knee_Strike | Boxing Guard, Step Knee Strike | Fighting | Punching | style_02 |
| 212 | Elbow_Strike | Elbow Strike | Fighting | Punching | style_02 |
| 213 | Leg_Sweep | Leg Sweep | Fighting | Punching | style_02 |
| 214 | Punch_Forward_with_Both_Fists | Punch Forward with Both Fists | Fighting | Punching | style_02 |
| 215 | High_Kick | High Kick | Fighting | Punching | style_02 |
| 216 | Lunge_Spin_Kick | Lunge Spin Kick | Fighting | Punching | style_02 |
| 217 | Sweeping_Kick | Sweeping Kick | Fighting | Punching | style_02 |
| 218 | Step_in_High_Kick | Step-in High Kick | Fighting | Punching | style_02 |
| 219 | Right_Hand_Sword_Slash | Right-hand Sword Slash | Fighting | Punching | style_02 |
| 220 | Shield_Push_Left | Shield Push Left | Fighting | Punching | style_02 |
| 221 | Charged_Upward_Slash | Charged Upward Slash | Fighting | Punching | style_02 |
| 222 | Draw_and_Shoot_from_Back | Draw and Shoot from Back | Fighting | AttackingwithWeapon | style_02 |
| 223 | Draw_and_Shoot_from_Back_1 | Draw and Shoot from Back 1 | Fighting | AttackingwithWeapon | style_02 |
| 224 | Archery_Shot | Archery Shot | Fighting | AttackingwithWeapon | style_02 |
| 225 | Archery_Shot_1 | Archery Shot 1 | Fighting | AttackingwithWeapon | style_02 |
| 226 | Archery_Shot_2 | Archery Shot 2 | Fighting | AttackingwithWeapon | style_02 |
| 227 | Archery_Shot_3 | Archery Shot 3 | Fighting | AttackingwithWeapon | style_02 |
| 228 | Walk_Forward_with_Bow_Aimed | Walk Forward with Bow Aimed | Fighting | AttackingwithWeapon | style_02 |
| 229 | Draw_and_Shoot_from_Back_2 | Draw and Shoot from Back 2 | Fighting | AttackingwithWeapon | style_02 |
| 230 | Walk_Backward_with_Bow_Aimed | Walk Backward with Bow Aimed | Fighting | AttackingwithWeapon | style_02 |
| 231 | Archery_Aim_with_Lateral_Scan | Archery Aim with Lateral Scan | Fighting | AttackingwithWeapon | style_02 |
| 232 | Cowboy_Quick_Draw_Shooting | Cowboy Quick Draw Shooting | Fighting | AttackingwithWeapon | style_02 |
| 233 | Walk_Backward_While_Shooting | Walk Backward While Shooting | Fighting | AttackingwithWeapon | style_02 |
| 234 | Walk_Forward_While_Shooting | Walk Forward While Shooting | Fighting | AttackingwithWeapon | style_02 |
| 235 | Forward_Roll_and_Fire | Forward Roll and Fire | Fighting | AttackingwithWeapon | style_02 |
| 236 | Draw_and_Shoot_Left | Draw and Shoot Left | Fighting | AttackingwithWeapon | style_02 |
| 237 | Charged_Axe_Chop | Charged Axe Chop | Fighting | AttackingwithWeapon | style_02 |
| 238 | Axe_Spin_Attack | Axe Spin Attack | Fighting | AttackingwithWeapon | style_02 |
| 239 | Crouch_Pull_and_Throw | Crouch Pull and Throw | Fighting | AttackingwithWeapon | style_02 |
| 240 | Thrust_Slash | Thrust Slash | Fighting | AttackingwithWeapon | style_02 |
| 241 | Weapon_Combo_2 | Weapon Combo 2 | Fighting | AttackingwithWeapon | style_02 |
| 242 | Charged_Slash | Charged Slash | Fighting | AttackingwithWeapon | style_02 |
| 243 | Idle_3 | Idle 3 | DailyActions | Idle | style_02 |
| 244 | Idle_4 | Idle 4 | DailyActions | Idle | style_02 |
| 245 | Idle_5 | Idle 5 | DailyActions | Idle | style_02 |
| 246 | Idle_6 | Idle 6 | DailyActions | Idle | style_02 |
| 247 | Idle_7 | Idle 7 | DailyActions | Idle | style_02 |
| 248 | Idle_8 | Idle 8 | DailyActions | Idle | style_02 |
| 249 | Idle_9 | Idle 9 | DailyActions | Idle | style_02 |
| 250 | Idle_10 | Idle 10 | DailyActions | Idle | style_02 |
| 251 | Idle_11 | Idle 11 | DailyActions | Idle | style_02 |
| 252 | Idle_12 | Idle 12 | DailyActions | Idle | style_02 |
| 253 | Idle_13 | Idle 13 | DailyActions | Idle | style_02 |
| 254 | Idle_14 | Idle 14 | DailyActions | Idle | style_02 |
| 255 | Angry_Ground_Stomp | Angry Ground Stomp | DailyActions | Idle | style_02 |
| 256 | Angry_Ground_Stomp_1 | Angry Ground Stomp 1 | DailyActions | Idle | style_02 |
| 257 | Angry_Ground_Stomp_2 | Angry Ground Stomp 2 | DailyActions | Idle | style_02 |
| 258 | CrouchLookAroundBow | Crouchlookaroundbow | DailyActions | Idle | style_02 |
| 259 | Step_Forward_and_Push | Step Forward and Push | DailyActions | Pushing | style_02 |
| 260 | Push_Forward_and_Stop | Push Forward and Stop | DailyActions | Pushing | style_02 |
| 261 | Push_and_Walk_Forward | Push and Walk Forward | DailyActions | Pushing | style_02 |
| 262 | Crouch_and_Push_Forward | Crouch and Push Forward | DailyActions | Pushing | style_02 |
| 263 | Sleep_on_Desk | Sleep on Desk | DailyActions | Sleeping | style_02 |
| 264 | Cough_While_Sleeping | Cough While Sleeping | DailyActions | Sleeping | style_02 |
| 265 | Groan_Holding_Stomach_in_Sleep | Groan Holding Stomach in Sleep | DailyActions | Sleeping | style_02 |
| 266 | Lie_Down_Hands_Spread | Lie Down, Hands Spread | DailyActions | Sleeping | style_02 |
| 267 | Sleep_Normally | Sleep Normally | DailyActions | Sleeping | style_02 |
| 268 | Sit_and_Doze_Off | Sit and Doze Off | DailyActions | Sleeping | style_02 |
| 269 | sleep | Sleep | DailyActions | Sleeping | style_02 |
| 270 | Toss_and_Turn | Toss and Turn | DailyActions | Sleeping | style_02 |
| 271 | Wake_Up_and_Look_Up | Wake Up and Look Up | DailyActions | Sleeping | style_02 |
| 272 | Lie_on_Chair_Sunbathe_and_Sleep | Lie on Chair, Sunbathe and Sleep | DailyActions | Sleeping | style_02 |
| 273 | Male_Run_Forward_Pick_Up_Left | Male Run Forward Pick Up Left | DailyActions | PickingUpItem | style_02 |
| 274 | Female_Crouch_Pick_Up_Place_Side | Female Crouch Pick Up Place Side | DailyActions | PickingUpItem | style_02 |
| 275 | Female_Run_Forward_Pick_Up_Right | Female Run Forward Pick Up Right | DailyActions | PickingUpItem | style_02 |
| 276 | Male_Bend_Over_Pick_Up | Male Bend Over Pick Up | DailyActions | PickingUpItem | style_02 |
| 277 | Female_Crouch_Pick_Fruit_Basket_Stand | Female Crouch Pick Fruit Basket Stand | DailyActions | PickingUpItem | style_02 |
| 278 | Female_Stand_Pick_Fruit_Basket | Female Stand Pick Fruit Basket | DailyActions | PickingUpItem | style_02 |
| 279 | Female_Crouch_Pick_Gun_Point_Forward | Female Crouch Pick Gun Point Forward | DailyActions | PickingUpItem | style_02 |
| 280 | Female_Crouch_Pick_Throw_Forward | Female Crouch Pick Throw Forward | DailyActions | PickingUpItem | style_02 |
| 281 | Female_Bend_Over_Pick_Up_Inspect | Female Bend Over Pick Up Inspect | DailyActions | PickingUpItem | style_02 |
| 282 | Female_Walk_Pick_Put_In_Pocket | Female Walk Pick Put in Pocket | DailyActions | PickingUpItem | style_02 |
| 283 | Pull_Radish | Pull Radish | DailyActions | PickingUpItem | style_02 |
| 284 | Collect_Object | Collect Object | DailyActions | PickingUpItem | style_02 |
| 285 | open_door | Open Door | DailyActions | Interacting | style_02 |
| 286 | open_door_1 | Open Door 1 | DailyActions | Interacting | style_02 |
| 287 | open_door_2 | Open Door 2 | DailyActions | Interacting | style_02 |
| 288 | open_door_3 | Open Door 3 | DailyActions | Interacting | style_02 |
| 289 | open_door_4 | Open Door 4 | DailyActions | Interacting | style_02 |
| 290 | Wave_One_Hand | Wave One Hand | DailyActions | Interacting | style_02 |
| 291 | Wave_for_Help | Wave for Help | DailyActions | Interacting | style_02 |
| 292 | Gesture_with_Hand_on_Gun | Gesture with Hand on Gun | DailyActions | Interacting | style_02 |
| 293 | Wave_for_Help_1 | Wave for Help 1 | DailyActions | Interacting | style_02 |
| 294 | Wave_for_Help_2 | Wave for Help 2 | DailyActions | Interacting | style_02 |
| 295 | Wave_for_Help_3 | Wave for Help 3 | DailyActions | Interacting | style_02 |
| 296 | Wave_for_Help_4 | Wave for Help 4 | DailyActions | Interacting | style_02 |
| 297 | Personalized_Gesture | Personalized Gesture | DailyActions | Interacting | style_02 |
| 298 | Cheer_with_Both_Hands_Up | Cheer with Both Hands Up | DailyActions | Interacting | style_02 |
| 299 | Stand_Clap_and_Sit_Down | Stand Clap and Sit Down | DailyActions | Interacting | style_02 |
| 300 | Sit_Cheer_with_Left_Hand | Sit Cheer with Left Hand | DailyActions | Interacting | style_02 |
| 301 | Cheer_with_Both_Hands_1 | Cheer with Both Hands 1 | DailyActions | Interacting | style_02 |
| 302 | Stand_Wave_and_Sit_Down | Stand Wave and Sit Down | DailyActions | Interacting | style_02 |
| 303 | Cheer_with_Both_Hands | Cheer with Both Hands | DailyActions | Interacting | style_02 |
| 304 | Seated_Fist_Pump | Seated Fist Pump | DailyActions | Interacting | style_02 |
| 305 | Stand_Cheer_and_Sit_Down | Stand Cheer and Sit Down | DailyActions | Interacting | style_02 |
| 306 | Cheer_with_One_Hand_Up | Cheer with One Hand Up | DailyActions | Interacting | style_02 |
| 307 | Sitting_Answering_Questions | Sitting Answering Questions | DailyActions | Interacting | style_02 |
| 308 | Talk_Passionately | Talk Passionately | DailyActions | Interacting | style_02 |
| 309 | Talk_with_Left_Hand_on_Hip | Talk with Left Hand on Hip | DailyActions | Interacting | style_02 |
| 310 | Talk_with_Left_Hand_Raised | Talk with Left Hand Raised | DailyActions | Interacting | style_02 |
| 311 | Stand_Talking_Angry | Stand Talking Angry | DailyActions | Interacting | style_02 |
| 312 | Phone_Conversation | Phone Conversation | DailyActions | Interacting | style_02 |
| 313 | Talk_with_Hands_Open | Talk with Hands Open | DailyActions | Interacting | style_02 |
| 314 | Talk_with_Right_Hand_Open | Talk with Right Hand Open | DailyActions | Interacting | style_02 |
| 315 | Hand_on_Hip_Gesture | Hand on Hip Gesture | DailyActions | Interacting | style_02 |
| 316 | Headache_Relief | Headache Relief | DailyActions | Interacting | style_02 |
| 317 | Shrug | Shrug | DailyActions | Interacting | style_02 |
| 318 | Scheming_Hand_Rub | Scheming Hand Rub | DailyActions | Interacting | style_02 |
| 319 | air_squat | Air Squat | DailyActions | WorkingOut | style_02 |
| 320 | bicep_curl | Bicep Curl | DailyActions | WorkingOut | style_02 |
| 321 | bicycle_crunch | Bicycle Crunch | DailyActions | WorkingOut | style_02 |
| 322 | circle_crunch | Circle Crunch | DailyActions | WorkingOut | style_02 |
| 323 | golf_drive | Golf Drive | DailyActions | WorkingOut | style_02 |
| 324 | idle_to_push_up | Idle to Push Up | DailyActions | WorkingOut | style_02 |
| 325 | jump_push_up | Jump Push Up | DailyActions | WorkingOut | style_02 |
| 326 | jumping_jacks | Jumping Jacks | DailyActions | WorkingOut | style_02 |
| 327 | kettlebell_swing | Kettlebell Swing | DailyActions | WorkingOut | style_02 |
| 328 | push_up_to_idle | Push Up to Idle | DailyActions | WorkingOut | style_02 |
| 329 | push_up | Push Up | DailyActions | WorkingOut | style_02 |
| 330 | situps | Situps | DailyActions | WorkingOut | style_02 |
| 331 | Sumo_High_Pull | Sumo High Pull | DailyActions | WorkingOut | style_02 |
| 333 | Look_Around_Dumbfounded | Look Around Dumbfounded | DailyActions | LookingAround | style_02 |
| 334 | Lower_Weapon_Look_Raise | Lower Weapon, Look, Raise | DailyActions | LookingAround | style_02 |
| 335 | Axe_Breathe_and_Look_Around | Axe Breathe and Look Around | DailyActions | LookingAround | style_02 |
| 336 | Long_Breathe_and_Look_Around | Long Breathe and Look Around | DailyActions | LookingAround | style_02 |
| 337 | Torch_Look_Around | Torch Look Around | DailyActions | LookingAround | style_02 |
| 338 | Short_Breathe_and_Look_Around | Short Breathe and Look Around | DailyActions | LookingAround | style_02 |
| 339 | Walking_Scan_with_Sudden_Look_Back | Walking Scan with Sudden Look Back | DailyActions | LookingAround | style_02 |
| 340 | Crawl_and_Look_Back | Crawl and Look Back | DailyActions | LookingAround | style_02 |
| 341 | Walk_Slowly_and_Look_Around | Walk Slowly and Look Around | DailyActions | LookingAround | style_02 |
| 342 | Stand_and_Drink | Stand and Drink | DailyActions | Drinking | style_02 |
| 343 | Sit_and_Drink | Sit and Drink | DailyActions | Drinking | style_02 |
| 344 | Stand_Up1 | Stand Up 1 | DailyActions | Transitioning | style_02 |
| 345 | Stand_Up2 | Stand Up 2 | DailyActions | Transitioning | style_02 |
| 346 | Stand_Up3 | Stand Up 3 | DailyActions | Transitioning | style_02 |
| 347 | Stand_Up4 | Stand Up 4 | DailyActions | Transitioning | style_02 |
| 348 | Stand_Up5 | Stand Up 5 | DailyActions | Transitioning | style_02 |
| 349 | Stand_Up6 | Stand Up 6 | DailyActions | Transitioning | style_02 |
| 350 | Stand_Up7 | Stand Up 7 | DailyActions | Transitioning | style_02 |
| 351 | Stand_Up8 | Stand Up 8 | DailyActions | Transitioning | style_02 |
| 352 | Stand_Up9 | Stand Up 9 | DailyActions | Transitioning | style_02 |
| 353 | Stand_Up10 | Stand Up 10 | DailyActions | Transitioning | style_02 |
| 354 | Sitting_Clap | Sitting Clap | DailyActions | Transitioning | style_02 |
| 355 | Sit_Finger_Wag_No | Sit Finger Wag No | DailyActions | Transitioning | style_02 |
| 356 | Sit_Hands_on_Head_Lean_Back | Sit Hands on Head Lean Back | DailyActions | Transitioning | style_02 |
| 357 | Sit_Thumbs_Up_Right | Sit Thumbs Up Right | DailyActions | Transitioning | style_02 |
| 358 | Sit_Shout_Hands_on_Mouth | Sit Shout Hands on Mouth | DailyActions | Transitioning | style_02 |
| 359 | Look_Back_and_Sit | Look Back and Sit | DailyActions | Transitioning | style_02 |
| 360 | Sit_to_standTransition_Female_2 | Sit to Standtransition Female 2 | DailyActions | Transitioning | style_02 |
| 361 | Sit_Dodge | Sit Dodge | DailyActions | Transitioning | style_02 |
| 362 | Sit_Cross_Legged | Sit Cross-legged | DailyActions | Transitioning | style_02 |
| 363 | Sit_Cross_Legged_on_Floor | Sit Cross-legged on Floor | DailyActions | Transitioning | style_02 |
| 364 | Sit_on_Chair_Arms_Crossed | Sit on Chair Arms Crossed | DailyActions | Transitioning | style_02 |
| 365 | Kneel_on_One_Knee_and_Stand | Kneel on One Knee and Stand | DailyActions | Transitioning | style_02 |
| 366 | falling_down | Falling Down | DailyActions | Transitioning | style_02 |
| 367 | SideLying_Reach_Help | Sidelying Reach Help | DailyActions | Transitioning | style_02 |
| 368 | Angry_To_Tantrum_Sit | Angry to Tantrum Sit | DailyActions | Transitioning | style_02 |
| 369 | Lie_Back_Leg_Swing | Lie Back Leg Swing | DailyActions | Transitioning | style_02 |
| 370 | Stand_To_Side_Lying | Stand to Side Lying | DailyActions | Transitioning | style_02 |
| 371 | Sit_Lie_Bed | Sit Lie Bed | DailyActions | Transitioning | style_02 |
| 372 | Prone_Reach_Help | Prone Reach Help | DailyActions | Transitioning | style_02 |
| 375 | Handstand_Flip | Handstand Flip | BodyMovements | Acting | style_02 |
| 376 | Punch_Pose | Punch Pose | BodyMovements | Acting | style_02 |
| 377 | Relax_arms_then_strike_battle_pose | Relax Arms, Then Strike Battle Pose | BodyMovements | Acting | style_02 |
| 378 | Large_step_then_high_kick | Large Step, Then High Kick | BodyMovements | Acting | style_02 |
| 379 | Side_jumps_in_horse_stance | Side Jumps in Horse Stance. | BodyMovements | Acting | style_02 |
| 381 | Step_Right_for_Exercise | Step Right for Exercise | BodyMovements | Acting | style_02 |
| 382 | Jump_and_Slam_Back_Down | Jump and Slam Back Down | BodyMovements | Acting | style_02 |
| 384 | Quick_Step_and_Spin_Dodge | Quick Step and Spin Dodge | BodyMovements | Acting | style_02 |
| 385 | Boxing_Warmup | Boxing Warm-up | BodyMovements | Acting | style_02 |
| 386 | Zombie_Scream | Zombie Scream | BodyMovements | Acting | style_02 |
| 387 | Half_Squat_with_Thumb_Up | Half Squat with Thumb Up | BodyMovements | Acting | style_02 |
| 388 | Show_Both_Arm_Muscles | Show Both Arm Muscles | BodyMovements | Acting | style_02 |
| 389 | Grip_and_Throw_Down | Grip and Throw Down | BodyMovements | Acting | style_02 |
| 390 | Stand_on_Pole_and_Balance | Stand on Pole and Balance | BodyMovements | Acting | style_02 |
| 391 | Head_Hold_in_Pain | Head Hold in Pain | BodyMovements | Acting | style_02 |
| 392 | Ground_Flip_and_Sweep_Up | Ground Flip and Sweep Up | BodyMovements | Acting | style_02 |
| 393 | baseball_pitching | Baseball Pitching | BodyMovements | Acting | style_02 |
| 394 | Backflip_and_Hooks | Backflip and Hooks | BodyMovements | Acting | style_02 |
| 395 | Breakdance_1990 | Breakdance 1990 | BodyMovements | Acting | style_02 |
| 396 | Burpee_Exercise | Burpee Exercise | BodyMovements | Acting | style_02 |
| 397 | 360_Power_Spin_Jump | 360 Power Spin Jump | BodyMovements | Acting | style_02 |
| 398 | Crouch_Charge_and_Throw | Crouch Charge and Throw | BodyMovements | Acting | style_02 |
| 399 | Step_Step_Turn_Kick | Step Step Turn Kick | BodyMovements | Acting | style_02 |
| 401 | Sprint_Roll_and_Flip | Sprint, Roll, and Flip | BodyMovements | Acting | style_02 |
| 402 | Run_and_Leap | Run and Leap | BodyMovements | Acting | style_02 |
| 403 | Victory_Fist_Pump | Victory Fist Pump | BodyMovements | Acting | style_02 |
| 404 | Crouch_and_Step_Back | Crouch and Step Back | BodyMovements | Acting | style_02 |
| 405 | Joyful_Dance_with_Hand_Sway | Joyful Dance with Hand Sway | BodyMovements | Acting | style_02 |
| 406 | Thomas_Flair_to_Jump_Up | Thomas Flair to Jump Up | BodyMovements | Acting | style_02 |
| 407 | Wall_Push_Jump_and_Flip | Wall Push Jump and Flip | BodyMovements | Acting | style_02 |
| 408 | Jazz_Hands | Jazz Hands | BodyMovements | Acting | style_02 |
| 409 | Finger_Wag_No | Finger Wag No | BodyMovements | Acting | style_02 |
| 410 | Kick_a_Soccer_Ball | Kick a Soccer Ball | BodyMovements | Acting | style_02 |
| 411 | Neck_Slashing_Gesture | Neck Slashing Gesture | BodyMovements | Acting | style_02 |
| 412 | victory | Victory | BodyMovements | Acting | style_02 |
| 413 | Backflip_and_Rise | Backflip and Rise | BodyMovements | Acting | style_02 |
| 414 | Double_kick_forward | Double Kick Forward. | BodyMovements | Acting | style_02 |
| 415 | Happy_Sway_Standing | Happy Sway Standing | BodyMovements | Acting | style_02 |
| 416 | Hit_in_Back_While_Running | Hit in Back While Running | BodyMovements | Acting | style_02 |
| 417 | Hop_with_Arms_Raised | Hop with Arms Raised | BodyMovements | Acting | style_02 |
| 419 | Jump_to_Catch_and_Fall | Jump to Catch and Fall | BodyMovements | Acting | style_02 |
| 420 | Left_Hand_Bitten_Step_Back | Left Hand Bitten, Step Back | BodyMovements | Acting | style_02 |
| 421 | Over_Shoulder_Throw | Over Shoulder Throw | BodyMovements | Acting | style_02 |
| 422 | Rising_Flying_Kick | Rising Flying Kick | BodyMovements | Acting | style_02 |
| 425 | Vault_with_Rifle | Vault with Rifle | BodyMovements | VaultingOverObstacle | style_02 |
| 426 | Roll_Behind_Cover | Roll Behind Cover | BodyMovements | VaultingOverObstacle | style_02 |
| 427 | Vault_and_Land | Vault and Land | BodyMovements | VaultingOverObstacle | style_02 |
| 428 | Unarmed_Vault | Unarmed Vault | BodyMovements | VaultingOverObstacle | style_02 |
| 429 | Parkour_Vault | Parkour Vault | BodyMovements | VaultingOverObstacle | style_02 |
| 430 | Parkour_Vault_with_Roll | Parkour Vault with Roll | BodyMovements | VaultingOverObstacle | style_02 |
| 431 | Parkour_Vault_1 | Parkour Vault 1 | BodyMovements | VaultingOverObstacle | style_02 |
| 432 | Parkour_Vault_2 | Parkour Vault 2 | BodyMovements | VaultingOverObstacle | style_02 |
| 433 | Parkour_Vault_3 | Parkour Vault 3 | BodyMovements | VaultingOverObstacle | style_02 |
| 434 | Fast_Ladder_Climb | Fast Ladder Climb | BodyMovements | Climbing | style_02 |
| 435 | Ladder_Climb_Finish | Ladder Climb Finish | BodyMovements | Climbing | style_02 |
| 436 | Ladder_Mount_Start | Ladder Mount Start | BodyMovements | Climbing | style_02 |
| 437 | Slow_Ladder_Climb | Slow Ladder Climb | BodyMovements | Climbing | style_02 |
| 438 | Ladder_Climb_Loop | Ladder Climb Loop | BodyMovements | Climbing | style_02 |
| 439 | Climb_Left_with_Both_Limbs | Climb Left with Both Limbs | BodyMovements | Climbing | style_02 |
| 440 | Climb_Right_with_Both_Limbs | Climb Right with Both Limbs | BodyMovements | Climbing | style_02 |
| 441 | Climb_Stairs | Climb Stairs | BodyMovements | Climbing | style_02 |
| 442 | Fast_Stair_Climb | Fast Stair Climb | BodyMovements | Climbing | style_02 |
| 444 | climbing_up_wall | Climbing Up Wall | BodyMovements | Climbing | style_02 |
| 445 | diagonal_wall_run | Diagonal Wall Run | BodyMovements | Climbing | style_02 |
| 446 | Hang_and_Climb_Left | Hang and Climb Left | BodyMovements | Climbing | style_02 |
| 447 | Hang_and_Climb_Rght | Hang and Climb Rght | BodyMovements | Climbing | style_02 |
| 448 | Jump_and_Grab_Wall | Jump and Grab Wall | BodyMovements | Climbing | style_02 |
| 449 | Climb_Up_Rope | Climb Up Rope | BodyMovements | Climbing | style_02 |
| 450 | Wall_Flip | Wall Flip | BodyMovements | PerformingStunt | style_02 |
| 451 | One_Arm_Handstand | One-arm Handstand | BodyMovements | PerformingStunt | style_02 |
| 452 | Backflip | Backflip | BodyMovements | PerformingStunt | style_02 |
| 453 | Backflip_Sweep_Kick | Backflip Sweep Kick | BodyMovements | PerformingStunt | style_02 |
| 455 | Sweep_Kick | Sweep Kick | BodyMovements | PerformingStunt | style_02 |
| 456 | Jumping_Head_Scissor_Takedown | Jumping Head Scissor Takedown | BodyMovements | PerformingStunt | style_02 |
| 457 | Jumping_Punch | Jumping Punch | BodyMovements | PerformingStunt | style_02 |
| 458 | Unicycle_Jump_Dismount | Unicycle Jump Dismount | BodyMovements | PerformingStunt | style_02 |
| 459 | Run_Jump_and_Roll | Run, Jump, and Roll | BodyMovements | PerformingStunt | style_02 |
| 460 | Jump_with_Arms_Open | Jump with Arms Open | BodyMovements | Jumping | style_02 |
| 461 | Jump_with_Arms_and_Legs_Open | Jump with Arms and Legs Open | BodyMovements | Jumping | style_02 |
| 462 | Backflip_Jump | Backflip Jump | BodyMovements | Jumping | style_02 |
| 463 | Run_and_Jump | Run and Jump | BodyMovements | Jumping | style_02 |
| 464 | Leap_and_Punch | Leap and Punch | BodyMovements | Jumping | style_02 |
| 465 | Leap_Right_and_Catch | Leap Right and Catch | BodyMovements | Jumping | style_02 |
| 466 | Regular_Jump | Regular Jump | BodyMovements | Jumping | style_02 |
| 467 | Jump_Over_Obstacle_2 | Jump Over Obstacle 2 | BodyMovements | Jumping | style_02 |
| 468 | Back_Jump | Back Jump | BodyMovements | Jumping | style_02 |
| 470 | Jumping_Down | Jumping Down | BodyMovements | Jumping | style_02 |
| 471 | Jump_Over_Obstacle | Jump Over Obstacle | BodyMovements | Jumping | style_02 |
| 472 | Jump_Over_Obstacle_1 | Jump Over Obstacle 1 | BodyMovements | Jumping | style_02 |
| 473 | Quad_Jump_Left | Quad Jump Left | BodyMovements | HangingfromLedge | style_02 |
| 474 | Quad_Jump_Up | Quad Jump Up | BodyMovements | HangingfromLedge | style_02 |
| 475 | Quad_Climb_Right | Quad Climb Right | BodyMovements | HangingfromLedge | style_02 |
| 476 | Hang_and_Push_with_Foot | Hang and Push with Foot | BodyMovements | HangingfromLedge | style_02 |
| 477 | Rope_Hang_Idle | Rope Hang Idle | BodyMovements | HangingfromLedge | style_02 |
| 478 | Bar_Hang_Idle | Bar Hang Idle | BodyMovements | HangingfromLedge | style_02 |
| 479 | Upside_Down_Rope_Hang | Upside Down Rope Hang | BodyMovements | HangingfromLedge | style_02 |
| 480 | Upside_Down_Rope_Hang_1 | Upside Down Rope Hang 1 | BodyMovements | HangingfromLedge | style_02 |
| 481 | Upside_Down_Rope_Hang_2 | Upside Down Rope Hang 2 | BodyMovements | HangingfromLedge | style_02 |
| 482 | Grab_Wall_Midair_Idle | Grab Wall Midair Idle | BodyMovements | HangingfromLedge | style_02 |
| 483 | Slow_Bar_Hang_Left | Slow Bar Hang Left | BodyMovements | HangingfromLedge | style_02 |
| 484 | Slow_Bar_Hang_Right | Slow Bar Hang Right | BodyMovements | HangingfromLedge | style_02 |
| 485 | Jump_and_Hang_on_Bar | Jump and Hang on Bar | BodyMovements | HangingfromLedge | style_02 |
| 486 | Wall_Support_to_Step_Down | Wall Support to Step Down | BodyMovements | HangingfromLedge | style_02 |
| 487 | Climb_Attempt_and_Fall_3 | Climb Attempt and Fall 3 | BodyMovements | FallingFreely | style_02 |
| 488 | Climb_Attempt_and_Fall_4 | Climb Attempt and Fall 4 | BodyMovements | FallingFreely | style_02 |
| 489 | Climb_Attempt_and_Fall_5 | Climb Attempt and Fall 5 | BodyMovements | FallingFreely | style_02 |
| 490 | Fall_Down | Fall Down | BodyMovements | HangingfromLedge | style_02 |
| 491 | Fall_from_Bar | Fall from Bar | BodyMovements | HangingfromLedge | style_02 |
| 492 | Wall_Support_Jump_to_Ground | Wall Support, Jump to Ground | BodyMovements | HangingfromLedge | style_02 |
| 493 | Jump_Down_from_Wall | Jump Down from Wall | BodyMovements | HangingfromLedge | style_02 |
| 494 | Swing_on_Rope_to_Ground | Swing on Rope to Ground | BodyMovements | HangingfromLedge | style_02 |
| 495 | Grab_Bar_and_Swing_Forward | Grab Bar and Swing Forward | BodyMovements | HangingfromLedge | style_02 |
| 496 | Rope_Hang_Backflip_to_Crouch | Rope Hang Backflip to Crouch | BodyMovements | HangingfromLedge | style_02 |
| 497 | climbing_down_wall | Climbing Down Wall | BodyMovements | Climbing | style_02 |
| 498 | Climb_Attempt_and_Fall | Climb Attempt and Fall | BodyMovements | FallingFreely | style_02 |
| 499 | Climb_Attempt_and_Fall_1 | Climb Attempt and Fall 1 | BodyMovements | FallingFreely | style_02 |
| 500 | Climb_Attempt_and_Fall_2 | Climb Attempt and Fall 2 | BodyMovements | FallingFreely | style_02 |
| 501 | Leap_of_Faith | Leap of Faith | BodyMovements | FallingFreely | style_02 |
| 502 | Fall1 | Fall 1 | BodyMovements | FallingFreely | style_02 |
| 503 | Fall2 | Fall 2 | BodyMovements | FallingFreely | style_02 |
| 504 | Fall3 | Fall 3 | BodyMovements | FallingFreely | style_02 |
| 505 | Fall4 | Fall 4 | BodyMovements | FallingFreely | style_02 |
| 506 | Dive_Down_and_Land | Dive Down and Land | BodyMovements | FallingFreely | style_02 |
| 507 | Dive_Down_and_Land_1 | Dive Down and Land 1 | BodyMovements | FallingFreely | style_02 |
| 508 | Dive_Down_and_Land_2 | Dive Down and Land  | BodyMovements | FallingFreely | style_02 |
| 509 | Lean_Forward_Sprint | Lean Forward Sprint | WalkAndRun | Running | style_02 |
| 510 | Standard_Forward_Charge | Standard Forward Charge | WalkAndRun | Running | style_02 |
| 511 | Rifle_Charge | Rifle Charge | WalkAndRun | Running | style_02 |
| 512 | Male_Head_Down_Charge | Male Head-down Charge | WalkAndRun | Running | style_02 |
| 513 | Female_Head_Down_Charge | Female Head-down Charge | WalkAndRun | Running | style_02 |
| 514 | Female_Bow_Charge_Left_Hand | Female Bow Charge Left Hand | WalkAndRun | Running | style_02 |
| 515 | Female_Throwing_Stance_Charge | Female Throwing Stance Charge | WalkAndRun | Running | style_02 |
| 516 | slide_light | Slide Light | WalkAndRun | Running | style_02 |
| 517 | slide_right | Slide Right | WalkAndRun | Running | style_02 |
| 518 | sliding_rool | Sliding Rool | WalkAndRun | Running | style_02 |
| 519 | sliding_stumble | Sliding Stumble | WalkAndRun | Running | style_02 |
| 520 | Crouch_Walk_with_Torch | Crouch Walk with Torch | WalkAndRun | CrouchWalking | style_02 |
| 521 | Crouch_Walk_Left_with_Torch | Crouch Walk Left with Torch | WalkAndRun | CrouchWalking | style_02 |
| 522 | Crouch_Walk_Right_with_Torch | Crouch Walk Right with Torch | WalkAndRun | CrouchWalking | style_02 |
| 523 | Cautious_Crouch_Walk_Backward | Cautious Crouch Walk Backward | WalkAndRun | CrouchWalking | style_02 |
| 524 | Cautious_Crouch_Walk_Forward | Cautious Crouch Walk Forward | WalkAndRun | CrouchWalking | style_02 |
| 525 | Cautious_Crouch_Walk_Left | Cautious Crouch Walk Left | WalkAndRun | CrouchWalking | style_02 |
| 526 | Cautious_Crouch_Walk_Right | Cautious Crouch Walk Right | WalkAndRun | CrouchWalking | style_02 |
| 527 | Crouch_Walk_Left_with_Gun | Crouch Walk Left with Gun | WalkAndRun | CrouchWalking | style_02 |
| 528 | Walk_Left_with_Gun | Walk Left with Gun | WalkAndRun | CrouchWalking | style_02 |
| 529 | Walk_Backward_with_Gun | Walk Backward with Gun | WalkAndRun | CrouchWalking | style_02 |
| 530 | run_fast_3 | Run Fast 3 | WalkAndRun | Running | style_02 |
| 531 | Sprint_and_Sudden_Stop | Sprint and Sudden Stop | WalkAndRun | Running | style_02 |
| 532 | run_fast_4 | Run Fast 4 | WalkAndRun | Running | style_02 |
| 533 | run_fast_5 | Run Fast 5 | WalkAndRun | Running | style_02 |
| 534 | run_fast_6 | Run Fast 6 | WalkAndRun | Running | style_02 |
| 535 | run_fast_7 | Run Fast 7 | WalkAndRun | Running | style_02 |
| 536 | run_fast_8 | Run Fast 8 | WalkAndRun | Running | style_02 |
| 537 | run_fast_9 | Run Fast 9 | WalkAndRun | Running | style_02 |
| 538 | run_fast_10 | Run Fast 10 | WalkAndRun | Running | style_02 |
| 539 | run_fast_2 | Run Fast 2 | WalkAndRun | Running | style_02 |
| 540 | Injured_Walk_Backward | Injured Walk Backward | WalkAndRun | Walking | style_02 |
| 541 | Walk_Backward_with_Gun_1 | Walk Backward with Gun 1 | WalkAndRun | Walking | style_02 |
| 542 | Walk_Backward_with_Grenade | Walk Backward with Grenade | WalkAndRun | Walking | style_02 |
| 543 | Step_Back | Step Back | WalkAndRun | Walking | style_02 |
| 544 | Walk_Backward | Walk Backward | WalkAndRun | Walking | style_02 |
| 545 | Walk_Backward_with_Bow | Walk Backward with Bow | WalkAndRun | Walking | style_02 |
| 546 | Walk_Backward_with_Sword | Walk Backward with Sword | WalkAndRun | Walking | style_02 |
| 547 | Walk_Backward_with_Bow_1 | Walk Backward with Bow 1 | WalkAndRun | Walking | style_02 |
| 548 | Walk_Backward_with_Sword_Shield | Walk Backward with Sword & Shield | WalkAndRun | Walking | style_02 |
| 549 | Crawl_Backward | Crawl Backward | WalkAndRun | Walking | style_02 |
| 550 | Carry_Heavy_Cannon_Forward | Carry Heavy Cannon Forward | WalkAndRun | Walking | style_02 |
| 551 | Carry_Heavy_Object_Walk | Carry Heavy Object Walk | WalkAndRun | Walking | style_02 |
| 552 | Carry_Water_Bucket_Walk | Carry Water Bucket Walk | WalkAndRun | Walking | style_02 |
| 553 | Elderly_Shaky_Walk | Elderly Shaky Walk | WalkAndRun | Walking | style_02 |
| 554 | Funky_Walk | Funky Walk | WalkAndRun | Walking | style_02 |
| 555 | Limping_Walk_1 | Limping Walk 1 | WalkAndRun | Walking | style_02 |
| 556 | Limping_Walk_2 | Limping Walk 2 | WalkAndRun | Walking | style_02 |
| 557 | Limping_Walk_3 | Limping Walk 3 | WalkAndRun | Walking | style_02 |
| 558 | Limping_Walk | Limping Walk | WalkAndRun | Walking | style_02 |
| 559 | Sneaky_Walk | Sneaky Walk | WalkAndRun | Walking | style_02 |
| 560 | Spear_Walk | Spear Walk | WalkAndRun | Walking | style_02 |
| 561 | Step_Hip_Hop_Dance | Step Hip Hop Dance | WalkAndRun | Walking | style_02 |
| 562 | Stumble_Walk | Stumble Walk | WalkAndRun | Walking | style_02 |
| 563 | Stylish_Walk | Stylish Walk | WalkAndRun | Walking | style_02 |
| 564 | Tightrope_Walk | Tightrope Walk | WalkAndRun | Walking | style_02 |
| 565 | Walk_with_Umbrella | Walk with Umbrella | WalkAndRun | Walking | style_02 |
| 566 | walking_2 | Walking 2 | WalkAndRun | Walking | style_02 |
| 567 | Walk_with_Walker_Support | Walk with Walker Support | WalkAndRun | Walking | style_02 |
| 568 | Swim_Idle | Swim Idle | WalkAndRun | Swimming | style_02 |
| 569 | Swim_Forward | Swim Forward | WalkAndRun | Swimming | style_02 |
| 570 | swimming_to_edge | Swimming to Edge | WalkAndRun | Swimming | style_02 |
| 571 | Run_Turn_Left | Run Turn Left | WalkAndRun | TurningAround | style_02 |
| 572 | Walk_Turn_Left | Walk Turn Left | WalkAndRun | TurningAround | style_02 |
| 573 | Rifle_Turn_Left | Rifle Turn Left | WalkAndRun | TurningAround | style_02 |
| 574 | Walk_Turn_Left_with_Weapon | Walk Turn Left with Weapon | WalkAndRun | TurningAround | style_02 |
| 575 | Combat_Idle_Turn_Left | Combat Idle Turn Left | WalkAndRun | TurningAround | style_02 |
| 576 | Idle_Turn_Left | Idle Turn Left | WalkAndRun | TurningAround | style_02 |
| 577 | Idle_Step_Turn_Left | Idle Step Turn Left | WalkAndRun | TurningAround | style_02 |
| 578 | Idle_Torch_Turn_Left | Idle Torch Turn Left | WalkAndRun | TurningAround | style_02 |
| 579 | Depressed_Full_Turn_Left | Depressed Full Turn Left | WalkAndRun | TurningAround | style_02 |
| 580 | Sword_and_Shield_Alert_Turn_Left | Sword and Shield Alert Turn Left | WalkAndRun | TurningAround | style_02 |
| 581 | Run_Sharp_Turn_Right | Run Sharp Turn Right | WalkAndRun | TurningAround | style_02 |
| 582 | Run_Turn_Right | Run Turn Right | WalkAndRun | TurningAround | style_02 |
| 583 | Walk_Turn_Right | Walk Turn Right | WalkAndRun | TurningAround | style_02 |
| 584 | Walk_Turn_Right_Female | Walk Turn Right (female) | WalkAndRun | TurningAround | style_02 |
| 585 | Rifle_Aim_Turn_Right | Rifle Aim Turn Right | WalkAndRun | TurningAround | style_02 |
| 586 | Idle_Turn_Right | Idle Turn Right | WalkAndRun | TurningAround | style_02 |
| 587 | Walk_Turn_Right_Idle_Style | Walk Turn Right (idle Style) | WalkAndRun | TurningAround | style_02 |
| 588 | Frustrated_Turn_Right | Frustrated Turn Right | WalkAndRun | TurningAround | style_02 |
| 589 | Alert_Quick_Turn_Right | Alert Quick Turn Right | WalkAndRun | TurningAround | style_02 |
| 590 | Sword_and_Shield_Alert_Turn_Right | Sword and Shield Alert Turn Right | WalkAndRun | TurningAround | style_02 |
| 591 | Hip_Hop_Dance | Hip Hop Dance | Dancing | Dancing | style_02 |
| 592 | Hip_Hop_Dance_1 | Hip Hop Dance 1 | Dancing | Dancing | style_02 |
| 593 | Hip_Hop_Dance_2 | Hip Hop Dance 2 | Dancing | Dancing | style_02 |
| 594 | Hip_Hop_Dance_3 | Hip Hop Dance 3 | Dancing | Dancing | style_02 |
| 595 | jazz_danc | Jazz Danc | Dancing | Dancing | style_02 |
| 596 | ymca_dance | Ymca Dance | Dancing | Dancing | style_02 |
| 597 | Hip_Hop_Dance_4 | Hip Hop Dance  | Dancing | Dancing | style_02 |
| 598 | kettlebell_swing_1 | Kettlebell Swing 1 | DailyActions | WorkingOut | style_02 |
| 599 | Idle_15 | Idle 15 | DailyActions | Idle | style_02 |
| 601 | Backflip_inplace | Backflip | BodyMovements | PerformingStunt | style_02 |
| 604 | Backflip_Sweep_Kick_inplace | Backflip Sweep Kick | BodyMovements | PerformingStunt | style_02 |
| 605 | Back_Jump_inplace | Back Jump | BodyMovements | Jumping | style_02 |
| 606 | BackLeft_run_inplace | BackLeft Run | WalkAndRun | Running | style_02 |
| 607 | BackRight_Run_inplace | BackRight Run | WalkAndRun | Running | style_02 |
| 608 | BeHit_FlyUp_inplace | BeHit FlyUp | Fighting | GettingHit | style_02 |
| 609 | Boxing_Practice_inplace | Boxing Practice | Fighting | Punching | style_02 |
| 610 | Carry_Heavy_Cannon_Forward_inplace | Carry Heavy Cannon Forward | WalkAndRun | Walking | style_02 |
| 611 | Carry_Heavy_Object_Walk_inplace | Carry Heavy Object Walk | WalkAndRun | Walking | style_02 |
| 612 | Carry_Water_Bucket_Walk_inplace | Carry Water Bucket Walk | WalkAndRun | Walking | style_02 |
| 613 | Casual_Walk_inplace | Casual Walk | WalkAndRun | Walking | style_02 |
| 615 | Cautious_Crouch_Walk_Backward_inplace | Cautious Crouch Walk Backward | WalkAndRun | CrouchWalking | style_02 |
| 616 | Cautious_Crouch_Walk_Forward_inplace | Cautious Crouch Walk Forward | WalkAndRun | CrouchWalking | style_02 |
| 617 | Cautious_Crouch_Walk_Left_inplace | Cautious Crouch Walk Left | WalkAndRun | CrouchWalking | style_02 |
| 618 | Cautious_Crouch_Walk_Right_inplace | Cautious Crouch Walk Right | WalkAndRun | CrouchWalking | style_02 |
| 619 | Climb_Left_with_Both_Limbs_inplace | Climb Left with Both Limbs | BodyMovements | Climbing | style_02 |
| 620 | Climb_Right_with_Both_Limbs_inplace | Climb Right with Both Limbs | BodyMovements | Climbing | style_02 |
| 621 | Confident_Strut_inplace | Confident Strut | WalkAndRun | Walking | style_02 |
| 622 | Crawl_Backward_inplace | Crawl Backward | WalkAndRun | Walking | style_02 |
| 623 | Crouch_Walk_Left_with_Gun_inplace | Crouch Walk Left with Gun | WalkAndRun | CrouchWalking | style_02 |
| 624 | Crouch_Walk_Left_with_Torch_inplace | Crouch Walk Left with Torch | WalkAndRun | CrouchWalking | style_02 |
| 625 | Crouch_Walk_Right_with_Torch_inplace | Crouch Walk Right with Torch | WalkAndRun | CrouchWalking | style_02 |
| 626 | Elderly_Shaky_Walk_inplace | Elderly Shaky Walk | WalkAndRun | Walking | style_02 |
| 627 | Female_Bow_Charge_Left_Hand_inplace | Female Bow Charge Left Hand | WalkAndRun | Running | style_02 |
| 628 | Female_Throwing_Stance_Charge_inplace | Female Throwing Stance Charge | WalkAndRun | Running | style_02 |
| 629 | Flirty_Strut_inplace | Flirty Strut | WalkAndRun | Walking | style_02 |
| 630 | ForwardLeft_Run_Fight_inplace | ForwardLeft Run Fight | Fighting | Transitioning | style_02 |
| 631 | ForwardRight_Run_Fight_inplace | ForwardRight Run Fight | Fighting | Transitioning | style_02 |
| 632 | Funky_Walk_inplace | Funky Walk | WalkAndRun | Walking | style_02 |
| 635 | Handbag_Walk_inplace | Handbag Walk | BodyMovements | Acting | style_02 |
| 636 | Hello_Run_inplace | Hello Run | WalkAndRun | Running | style_02 |
| 637 | Injured_Walk_inplace | Injured Walk | WalkAndRun | Walking | style_02 |
| 638 | Injured_Walk_Backward_inplace | Injured Walk Backward | WalkAndRun | Walking | style_02 |
| 639 | Jazz_Hands_inplace | Jazz Hands | BodyMovements | Acting | style_02 |
| 640 | Jump_Over_Obstacle_inplace | Jump Over Obstacle | BodyMovements | Jumping | style_02 |
| 641 | Jump_Over_Obstacle_1_inplace | Jump Over Obstacle 1 | BodyMovements | Jumping | style_02 |
| 642 | Jump_Over_Obstacle_2_inplace | Jump Over Obstacle 2 | BodyMovements | Jumping | style_02 |
| 643 | Jump_Run_inplace | Jump Run | WalkAndRun | Running | style_02 |
| 644 | Lean_Forward_Sprint_inplace | Lean Forward Sprint | WalkAndRun | Running | style_02 |
| 645 | Limping_Walk_inplace | Limping Walk | WalkAndRun | Walking | style_02 |
| 646 | Limping_Walk_1_inplace | Limping Walk 1 | WalkAndRun | Walking | style_02 |
| 647 | Limping_Walk_2_inplace | Limping Walk 2 | WalkAndRun | Walking | style_02 |
| 648 | Limping_Walk_3_inplace | Limping Walk 3 | WalkAndRun | Walking | style_02 |
| 649 | Lunge_Roundhouse_Kick_inplace | Lunge Roundhouse Kick | Fighting | Punching | style_02 |
| 650 | Mummy_Stagger_inplace | Mummy Stagger | BodyMovements | Acting | style_02 |
| 651 | Parkour_Vault_with_Roll_inplace | Parkour Vault with Roll | BodyMovements | VaultingOverObstacle | style_02 |
| 652 | Proud_Strut_inplace | Proud Strut | WalkAndRun | Walking | style_02 |
| 653 | Red_Carpet_Walk_inplace | Red Carpet Walk | WalkAndRun | Walking | style_02 |
| 654 | Rifle_Charge_inplace | Rifle Charge | WalkAndRun | Running | style_02 |
| 656 | Run_and_Leap_inplace | Run and Leap | BodyMovements | Acting | style_02 |
| 657 | run_fast_10_inplace | Run Fast 10 | WalkAndRun | Running | style_02 |
| 658 | run_fast_2_inplace | Run Fast 2 | WalkAndRun | Running | style_02 |
| 659 | run_fast_3_inplace | Run Fast 3 | WalkAndRun | Running | style_02 |
| 660 | run_fast_4_inplace | Run Fast 4 | WalkAndRun | Running | style_02 |
| 661 | run_fast_5_inplace | Run Fast 5 | WalkAndRun | Running | style_02 |
| 662 | run_fast_6_inplace | Run Fast 6 | WalkAndRun | Running | style_02 |
| 663 | run_fast_7_inplace | Run Fast 7 | WalkAndRun | Running | style_02 |
| 664 | run_fast_8_inplace | Run Fast 8 | WalkAndRun | Running | style_02 |
| 665 | run_fast_9_inplace | Run Fast 9 | WalkAndRun | Running | style_02 |
| 666 | Running_Reload_inplace | Running Reload | Fighting | Transitioning | style_02 |
| 667 | Run_to_Walk_Transition_inplace | Run to Walk Transition | WalkAndRun | Walking | style_02 |
| 668 | Skip_Forward_inplace | Skip Forward | WalkAndRun | Walking | style_02 |
| 669 | Slow_Orc_Walk_inplace | Slow Orc Walk | WalkAndRun | Walking | style_02 |
| 670 | Slow_Walk_Reload_inplace | Slow Walk Reload | Fighting | Transitioning | style_02 |
| 671 | Sneaky_Walk_inplace | Sneaky Walk | WalkAndRun | Walking | style_02 |
| 672 | Spear_Walk_inplace | Spear Walk | WalkAndRun | Walking | style_02 |
| 673 | Standard_Forward_Charge_inplace | Standard Forward Charge | WalkAndRun | Running | style_02 |
| 674 | Stumble_Walk_inplace | Stumble Walk | WalkAndRun | Walking | style_02 |
| 675 | Stylish_Walk_inplace | Stylish Walk | WalkAndRun | Walking | style_02 |
| 676 | Texting_Walk_inplace | Texting Walk | WalkAndRun | Walking | style_02 |
| 677 | Tightrope_Walk_inplace | Tightrope Walk | WalkAndRun | Walking | style_02 |
| 678 | Unsteady_Walk_inplace | Unsteady Walk | WalkAndRun | Walking | style_02 |
| 679 | Walk_Backward_inplace | Walk Backward | WalkAndRun | Walking | style_02 |
| 680 | Walk_Backward_While_Shooting_inplace | Walk Backward While Shooting | Fighting | AttackingwithWeapon | style_02 |
| 681 | Walk_Backward_with_Bow_inplace | Walk Backward with Bow | WalkAndRun | Walking | style_02 |
| 682 | Walk_Backward_with_Bow_1_inplace | Walk Backward with Bow 1 | WalkAndRun | Walking | style_02 |
| 683 | Walk_Backward_with_Bow_Aimed_inplace | Walk Backward with Bow Aimed | Fighting | AttackingwithWeapon | style_02 |
| 684 | Walk_Backward_with_Grenade_inplace | Walk Backward with Grenade | WalkAndRun | Walking | style_02 |
| 685 | Walk_Backward_with_Gun_inplace | Walk Backward with Gun | WalkAndRun | CrouchWalking | style_02 |
| 686 | Walk_Backward_with_Gun_1_inplace | Walk Backward with Gun 1 | WalkAndRun | Walking | style_02 |
| 687 | Walk_Backward_with_Sword_inplace | Walk Backward with Sword | WalkAndRun | Walking | style_02 |
| 688 | Walk_Fight_Back_inplace | Walk Fight Back | WalkAndRun | Walking | style_02 |
| 689 | Walk_Fight_Forward_inplace | Walk Fight Forward | WalkAndRun | Walking | style_02 |
| 690 | Walk_Forward_While_Shooting_inplace | Walk Forward While Shooting | Fighting | AttackingwithWeapon | style_02 |
| 691 | Walk_Forward_with_Bow_Aimed_inplace | Walk Forward with Bow Aimed | Fighting | AttackingwithWeapon | style_02 |
| 692 | walking_2_inplace | Walking 2 | WalkAndRun | Walking | style_02 |
| 693 | Walking_with_Phone_inplace | Walking with Phone | WalkAndRun | Walking | style_02 |
| 694 | Walk_Left_with_Gun_inplace | Walk Left with Gun | WalkAndRun | CrouchWalking | style_02 |
| 695 | Walk_with_Umbrella_inplace | Walk with Umbrella | WalkAndRun | Walking | style_02 |
| 696 | Walk_with_Walker_Support_inplace | Walk with Walker Support | WalkAndRun | Walking | style_02 |
