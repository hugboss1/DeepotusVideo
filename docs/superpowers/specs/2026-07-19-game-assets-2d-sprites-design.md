# Game Assets 2D — Sprite Lab (chantiers 9a→9d)

Date : 2026-07-19 · Statut : validé par Olivier (périmètre 9a→9d, hub + page standalone iframe, exports PNG+JSON générique + pack Unity, exécution 1 chantier = 1 session)

## 1. Contexte

La section **Game Assets** (vue `assets3d`, composant `DzGameAssets`, v1.15.8) couvre uniquement image → mesh 3D. Aucune capacité 2D (sprite, spritesheet, pixel art, tileset) n'existe dans le logiciel. Référence produit : la suite **sorceress.games** (Auto-Sprite v2, True Pixel, Quick Sprites, Sprite Analyzer) dont on transpose la chaîne 2D avec les briques déjà présentes :

- Seedance i2v (`fal_service.py`) = l'étape « Animate » d'Auto-Sprite ;
- `/api/images/process` (remove-bg fal/local, upscale, crop, edit Kontext, variations) ;
- ffmpeg embarqué (extraction de frames), Pillow (assemblage, quantize) ;
- système de jobs SQLite + pricing + Library + `atelier_settings` ;
- précédent `/atelier` (page riche hors bundle, iframe dans le SPA) ;
- recette patcher `patch_bundle_imagegen.py` (anchors count==1, backup `.bak_<tag>`).

Cas d'usage cible : sprites/VFX game-ready pour **DEEPOTUS: Rippled** (Unity, repo `D:\olivi\deepotus-rippled`).

Pipeline cible :

```
Image (Library / ImageGen) → Seedance fond uni (preset) → extraction frames (ffmpeg)
  → remove-BG par frame (fal rembg | local) → [option pixel-art PIL]
  → assemblage sheet (PIL) → préviz animée → exports PNG + ZIP + JSON + pack Unity
```

## 2. Non-goals v1

Rigging/animation 3D, Tileset Forge complet (grille éditable multi-outils), hitboxes façon Sprite Analyzer, voxel, tuiles seamless (chantier 9e reporté), câblage Meshy 6 (9f reporté).

## 3. Chantier 9a — Backend `sprite_service.py`

Calqué sur le gabarit `asset3d_service.py` (job en BackgroundTasks, `JobRecord provider="sprite2d"`, short id 8 hex, garde anti path-traversal, `cost_meta` JSON).

### Endpoints (routes.py)

- `POST /api/assets/sprite` — lance le job. Body :
  - `source` : `{kind: "job"|"upload"|"video", ...}` — un render existant (job_id), un upload utilisateur, ou un fichier vidéo déjà présent ;
  - `fps_sample` (défaut 8, 1–24) : fréquence d'échantillonnage des frames ;
  - `max_frames` (défaut 16, 4–64) ;
  - `remove_bg` : `"none" | "api" | "local"` (mêmes chemins que l'op remove-bg existante ; `local` exige la lib rembg, sinon 400 explicite) ;
  - `trim` : `"animation"` (canvas commun, position préservée) | `"tight"` (recadrage au contenu, bbox union) ;
  - `cell` : `{size: 128|256|512, align: "feet"|"center"}` — alignement vertical par le bas du contenu (« pieds ») ou centré ;
  - `pixel` (optionnel, dépend de 9b) : `{target_px, colors|palette, dither}` appliqué par frame ;
  - `columns` : `"auto"` (≈ carré) ou entier.
- `GET /api/assets/sprite/{job}/manifest` — grille, frames, fps, offsets, fichiers présents.
- `GET /api/assets/sprite/{job}/sheet` — `sheet.png` ; `GET .../preview` — `preview.gif`.
- `GET /api/assets/sprite/{job}/frame/{i}` — frame individuelle.
- `GET /api/assets/sprite/{job}/zip` — archive complète (sheet + frames + manifests + pack Unity).
- `POST /api/assets/sprite/{job}/save` — copie `sheet.png` dans la Library (`gen_*.png`) pour ré-usage Studio.

### Sorties (`DATA_ROOT/assets/outputs/sprites/{job}/`)

`sheet.png`, `frames/000.png…`, `preview.gif`, `manifest.json`, `sheet.unity.json`, `SpriteSheetImporter.cs`.

- `manifest.json` (générique) : `{version, source, grid: {cols, rows, cell_w, cell_h}, frames: [{index, file, rect: {x,y,w,h}, offset: {x,y}}], fps, created_at}`.
- **Pack Unity** : `sheet.unity.json` (slicing : name, rect, pivot par frame, pixelsPerUnit) + `SpriteSheetImporter.cs` (script Editor one-file, généré depuis un template backend, qui lit le JSON et découpe la texture en Sprites Multiple — évite de générer un `.meta` fragile).

### Étapes du job (progress via `current_step`)

1. résolution de la source (ffprobe durée) ; 2. extraction ffmpeg (`-vf fps=`) ; 3. remove-bg frame par frame (batch, tolère l'échec d'une frame → frame conservée non détourée + flag manifest) ; 4. pixel-art optionnel ; 5. trim/alignement (bbox union en mode tight, ancre pieds = bas de bbox) ; 6. assemblage PIL + `preview.gif` ; 7. écriture manifests + pricing.

### Pricing

`pricing.py` kind `"sprite2d"` : coût = remove-bg api × nb frames (réutilise le tarif rembg existant) ; extraction/assemblage/pixel = 0 (local). `POST /api/cost/estimate` doit couvrir le kind.

### Recette 9a

`backend/tests/test_sprite_service.py` (lancé avec le python embarqué de l'app installée) : grille/manifest cohérents sur une vidéo synthétique, rejet path-traversal, survie à l'échec d'une frame, mode tight vs animation, pack Unity présent dans le zip. **Preuve finale : un sheet réel généré depuis un render existant de la Library.**

## 4. Chantier 9b — Ops pixel-art & tile-preview (`/api/images/process`)

- op `"pixel"` : `{target_px 8–512 (côté long), colors 2–256 | palette: "pico8"|"gameboy"|"nes"|"sweetie16"|"onebit", dither: "none"|"ordered"|"floyd", scale 1–16}` — PIL pur : downscale LANCZOS → quantize (palette fixe ou adaptative) → upscale NEAREST. Palettes presets en constantes backend.
- op `"tile-preview"` : composite 2×2 (ou 3×3) d'une image de la Library + métrique de raccord (somme des diffs des bords opposés, normalisée 0–100) retournée dans la réponse — base du futur 9e.
- `sprite_service` réutilise l'op `pixel` par frame (import direct de la fonction, pas d'appel HTTP).

Recette 9b : tests golden — nombre de couleurs exact ≤ preset, dimensions attendues, déterminisme (même input → même output), métrique tile-preview basse sur une tuile unie et haute sur une photo.

## 5. Chantier 9c — UI « Sprite Lab » (page standalone + hub)

### Page `frontend/spritelab/` (hors bundle, modèle `/atelier`)

`index.html` + `spritelab.js` + `spritelab.css`, vanilla JS, en français, montée dans `main.py` sur `/spritelab` (StaticFiles no-cache, AVANT le catch-all SPA, redirect 307 `/spritelab` → `/spritelab/`).

Layout 3 zones (pattern Sorceress) :
1. **Source** (gauche) : choisir une image de la Library (grille + recherche) → bouton « Animer (Seedance, fond uni) » qui lance `POST /api/generate` avec un preset prompt fond uni/caméra fixe (suffixe : *static camera, character animation loop, plain solid green background, full body visible*) ; OU choisir un render existant / uploader une vidéo. Poll `/api/jobs/{id}`.
2. **Filmstrip + réglages** (centre) : frames extraites avec toggle on/off par frame (Shift-clic pour plage), réglages fps_sample/max_frames/remove-bg/trim/cell/alignement/pixel-art, bouton « Générer le sheet ».
3. **Préviz + exports** (droite) : préviz animée (slider FPS 1–24, loop, zoom, fonds damier/uni/couleurs), puis boutons Sheet PNG / ZIP frames / Pack Unity / Save to Library.

État persistant léger via `atelier_settings` (clés `spritelab_*` : derniers réglages).

### Intégration SPA (petit patcher `scripts/patch_bundle_spritelab.py`)

L'onglet **Game Assets devient un hub à sous-onglets « 3D | Sprites 2D »** : ~4 anchors —
1. entrée `Uu` : desc `"image → 3D model"` → `"image → 3D & sprites"` ;
2. wrapper `DzGameAssetsHub` : barre de sous-onglets, onglet 3D = `DzGameAssets` existant, onglet Sprites = iframe `/spritelab` (même pattern que `DzChapitres`/`/atelier`) ;
3. branche du switch `s==="assets3d"` → rend le hub ;
4. support d'un detail `subtab` dans l'event `deepotus:navigate` pour ouvrir directement le sous-onglet Sprites.

Convention : composants lisibles `Dz*`, backup `.bak_spritelab`, base = bundle courant post-imagegen.

### Recette 9c

Boucle QA Puppeteer (harnais du skill scroll-cinema-landing, `localStorage.dz_onboarded=1`) : parcours complet image Library → Animer → filmstrip → Générer → préviz ; screenshot du Sprite Lab avec sheet affiché + vérification disque des fichiers de sortie.

## 6. Chantier 9d — Library & hand-off « Send to »

- **Onglet « Sprites » dans la Library** (patcher `patch_bundle_libsprites.py`) : liste des jobs `sprite2d` — vignette = `preview.gif` animé au survol, download sheet/zip, favoris, rename, delete (mêmes patterns que l'onglet 3D ; DELETE `/api/jobs/{id}` supprime déjà les fichiers).
- **Hand-off façon Sorceress** : action « → Sprite Lab » sur les images ET les renders de la Library (`deepotus:navigate` avec `{view:"assets3d", subtab:"sprites", source:...}` relayé à l'iframe via postMessage) ; dans le Sprite Lab, bouton « → Studio » après Save to Library (le sheet devient un nœud Image ordinaire).

Recette 9d : QA Puppeteer — clic depuis la Library ouvre le Sprite Lab pré-rempli avec la bonne source ; l'onglet Sprites liste le job de la recette 9c.

## 7. Déploiement & garde-fous

- Aucune donnée réelle modifiée : uniquement de nouveaux dossiers `outputs/sprites/`, la Library existante n'est pas touchée ; chaque patcher garde son `.bak_<tag>` de rollback.
- Workflow habituel : dev dans le repo → tests python embarqué → copie repo → app installée → `stop.ps1` + `launch-silent.vbs` (vérifier `GET /api/jobs` vide avant restart).
- 1 chantier = 1 session ; commit « Chantier 9x : … (recette OK) » après preuve.
