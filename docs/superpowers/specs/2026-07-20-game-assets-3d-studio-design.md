# Game Assets 3D — Rig Studio (chantiers 10a→10d)

Date : 2026-07-20 · Statut : **PROPOSITION — à valider par Olivier** (issue de
l'exploration de sorceress.games : 5 captures du 3D Studio + site public).

## 1. Contexte

L'onglet **Game Assets** est aujourd'hui un hub « 🧊 3D | 🧩 Sprites 2D » (9c/9d).
Côté 3D on a déjà : image → mesh texturé via 5 engines fal
(`asset3d_service.ENGINES` : tripo 2.5, hunyuan v2, trellis, rodin, triposr),
formats multiples (glb/fbx/obj/stl/usdz selon engine), shots, poster,
`model-viewer` dans le SPA, onglet 3D de la Library. **Il manque tout le
post-génération** : optimisation (budget de triangles), rigging, animation,
et le pont 3D → sprites 2D.

Référence produit : le **3D Studio de sorceress.games** — « Type an idea, get a
fully rigged, fully animated, game-ready 3D character » : image gen → image-to-3D
→ auto-rig humanoïde + weight-paint → text-to-animation → export FBX/GLB/GLTF.

Cas d'usage cible : personnages/props game-ready pour **DEEPOTUS: Rippled**
(Unity), et sprites 8 directions générés depuis les assets 3D (leur module
« 3D to 2D » le confirme comme produit à part entière).

## 2. Cartographie sorceress (captures du 20/07/2026 + site)

1. **Create** : multi-modèles au choix avec coût en crédits — Tripo v3.1 (40cr,
   BEST), Meshy 6 (35cr, BEST), Hunyuan 3D 3.1 (30cr, BEST BUDGET), Pixal3D
   (VIP uncensored), TRELLIS 2 (40cr), Rodin 2.0 (50cr) ; input Image / Text /
   Multi-Img ; quantité 1–4 ; batch « drop multiple images » ; galerie avec
   filtres ALL/STARRED/RIGGED/UNRIGGED + recherche ; actions par carte :
   Edit Rig / Refine / Animate.
2. **Viewer / Optimize** : vue côte à côte **Original vs Optimized** (specs :
   vertices/triangles/meshes/materials), re-optimize par presets : Micro Prop
   500 · Small Prop 1k · Prop 2.5k · Detailed Prop 5k · **Game Ready 10k** ·
   Balanced 25k · High Detail 50k · Ultra 100k · Extreme 150k · Max Detail 200k
   + slider « target triangles » ; téléchargement .glb original et optimisé
   (ex. observé : 1 499 810 tris → 99 962, « 93% reduction »).
3. **Guidance A-Pose** : pose de référence recommandée (bras ~45°, espace entre
   les membres) avec image téléchargeable — améliore le rig auto.
4. **Rig** : auto-rig humanoïde (26 bones · référence SMPL 22 bones affichée
   côte à côte), Adjust Joints, Breast bones on/off, Recompute weights,
   SMPL offset, shading Wire/Solid/Texture/Tex+Wire/Weights, Send to
   Refine/Animate.
5. **Refine** : weight painting complet (brush size/strength, falloff
   linear/smooth/constant, Set/Add/Subtract/Smooth/Blur, mirror painting,
   isolate par bone, lasso, select free polys), **Seam smoothing** (collar
   width en rings, soften all seams / this bone), **Dynamic healing** (stretch
   tolerance, heal spread, auto-rig heal), **Pose test** : jouer une animation
   (bibliothèque en langage naturel : « A person dances happily with rhythm »,
   « throws a right-hand punch », « sits down on a chair »…) et peindre sur la
   pose déformée.
6. **Animate / Drive Mode** : slots de locomotion (Idle/Walk/Run/Walk
   Backwards/Strafe L-R/Jump…) avec vitesse par slot et profils sauvegardés,
   pilotage WASD temps réel avec blend weights affichés, In-place, physiques
   Jiggle/Hair/Cloth, Record → JSON, **Export → Godot**.
7. Modules sœurs pertinents : **3D to 2D** (« any 3D character, object, or
   animation → pixel-perfect 2D sprite sheet from any camera angle »),
   Material Forge (image → PBR), Procedural Walk (rig multi-jambes + IK).

## 3. Briques dont on dispose déjà

- **fal** : les 5 engines image→3D en place ; clés déjà configurées.
- **Meshy API** (chantier 9f déjà prévu au plan 9) : image/text→3D **mais
  aussi auto-rigging et bibliothèque d'animations retargetées + retexture** —
  c'est la brique « rig + animate » sans ML local. Tripo (API directe) a un
  équivalent rig/retarget. À trancher au 10b (voir §6).
- **Binaire embarqué** (pattern ffmpeg) : **gltfpack** (meshoptimizer) — exe
  autonome qui fait simplification/quantization de GLB. Idéal pour le
  re-optimize par presets, 100 % local et gratuit.
- **Page standalone hors bundle** (pattern `/atelier`, `/spritelab`) : une page
  `/rigstudio` avec **three.js embarqué en local** (GLTFLoader +
  SkeletonHelper + AnimationMixer) pour prévisualiser rig et animations —
  `model-viewer` ne montre ni squelette ni blending.
- **sprite_service (9a)** : l'assemblage sheet + pack Unity resservira tel quel
  pour le pont 3D→2D.
- Conventions : patchers à anchors (count==1, backup), jobs SQLite + pricing,
  hand-off « Send to » (9d), recettes pytest + QA Puppeteer.

## 4. Non-goals v1

Weight painting interactif complet, seam smoothing/dynamic healing, drive mode
WASD + physiques (jiggle/hair/cloth), voxel, rig procédural multi-jambes,
Material Forge PBR, retexture. (Réévaluables après 10d.)

## 5. Chantiers proposés (1 chantier = 1 session, commit après recette)

### 10a — Optimize : budgets de triangles (local, gratuit)

- Embarquer `gltfpack.exe` dans `bin/` (comme ffmpeg) ; service
  `mesh_optimize` : `POST /api/assets/3d/{job}/optimize`
  `{target_tris | preset}` → `model.opt.glb` + stats {tris/verts avant/après,
  ratio} persistées dans le manifest du job.
- Presets calqués sorceress : micro 500 / small 1k / prop 2.5k / detailed 5k /
  **game-ready 10k (défaut)** / balanced 25k / high 50k / ultra 100k.
- UI (patcher `patch_bundle_asset3dopt.py`) : dans le panneau 3D existant,
  comparateur Original|Optimized (2 × model-viewer), specs, boutons presets,
  download des deux .glb ; l'onglet 3D de la Library propose le .glb optimisé.
- Recette : sur un asset réel de la Library, réduction ≥ 90 % vers 10k ±10 %
  tris (stats vérifiées en parsant le GLB), QA Puppeteer du comparateur.

### 10b — Rig auto par API + badge Rigged

- `POST /api/assets/3d/{job}/rig` via **Meshy rigging** (ou Tripo — décision
  §6) sur le glb (optimisé de préférence) → `rigged.glb` (+ fbx si offert) ;
  job enrichi (`cost_meta.rigged`), badge « Rigged » sur les cartes 3D
  (Library + galerie du hub), pricing kind `rig3d`.
- Guidance A-Pose : preset de prompt ImageGen « character reference sheet,
  A-pose, arms at 45°, clear gap between limbs » + encart d'aide dans l'UI
  Create (statique, pas d'analyse de pose v1).
- Recette : pytest de parsing GLTF (le rigged.glb contient skins/joints > 0,
  hiérarchie humanoïde plausible) + un asset réel riggé de bout en bout.

### 10c — Page `/rigstudio` (three.js) : préviz rig + animations par preset

- Page standalone hors bundle (three.js local) montée dans `main.py` ;
  sous-onglet « 🦴 Rig Studio » ajouté au hub (iframe, pattern 9c).
- Viewer : modèle riggé, squelette en overlay, heatmap de weights simple
  (par bone sélectionné), turntable.
- Animations : presets retargetés via l'API d'animation Meshy (idle, walk,
  run, punch, jump…) → `anims/{name}.glb` téléchargés et rejoués par
  AnimationMixer ; export **.glb animé** + pack **Unity** (script Editor à la
  9a : Humanoid/Generic import) et notice Godot.
- Hand-off (pattern 9d) : « → Rig Studio » depuis les cartes 3D de la Library
  et de la galerie du hub (postMessage source) ; « → Library » après export.
- Recette : QA Puppeteer — mixer.time avance, changement d'anim par preset,
  export rechargé dans le viewer sans erreur ; hand-off pré-rempli.

### 10d — Pont 3D → 2D : sprites 8 directions (le lien avec Rippled)

- Dans `/rigstudio` : « → Sprite Lab » — capture offscreen (three.js,
  renderer alpha) de N angles (1/4/8 directions) × M frames de l'animation
  choisie, fond transparent → `POST /api/assets/sprite` (nouvelle source
  `{kind:"frames"}` : PNG déjà détourés, pipeline 9a réutilisé pour
  l'assemblage sheet/manifest/pack Unity + preview.gif).
- Un sheet par direction ou grille direction × frame (option), presets 2D du
  Sprite Lab applicables (pixel-art 9b compris).
- Recette : depuis un perso riggé + anim walk, un sheet 8 directions arrive
  dans l'onglet Sprites de la Library et se rejoue dans le Sprite Lab ;
  QA bout-en-bout + preuve visuelle.

## 6. Questions à trancher avant 10a (réponses d'Olivier)

1. **Rig/animate : Meshy ou Tripo ?** Meshy = rig + grosse bibliothèque
   d'anims + retexture (mais nouveau compte/clé et crédits) ; Tripo = déjà
   utilisé via fal pour la géométrie, mais rig via API directe Tripo
   (clé dédiée aussi). Proposition : **Meshy** (couvre 9f + 10b + 10c d'un
   coup), Tripo en fallback.
2. **gltfpack embarqué** : ok pour ajouter le binaire (~1 Mo) dans `bin/` de
   l'app installée + repo ?
3. **Place UI** : 3e sous-onglet « Rig Studio » dans le hub (proposé), ou tout
   intégrer dans l'onglet 3D existant ?
4. Ordre : 10a→10d proposé (valeur immédiate : l'optimize sert Rippled dès
   10a). Le 9e (tuiles seamless) reste prioritaire si tu préfères finir le 2D.

## 7. Déploiement & garde-fous

Workflow habituel : dev repo → tests python embarqué → copie vers l'app
installée → stop/launch (file vide d'abord) ; nouveaux binaires dans `bin/`
avec PATH préfixé comme ffmpeg ; aucun asset existant modifié (les sorties
optimize/rig s'ajoutent dans `outputs/assets3d/{short}/`) ; patchers avec
backup `.bak_<tag>` ; 1 chantier = 1 session, commit « Chantier 10x : …
(recette OK) » après preuve.
