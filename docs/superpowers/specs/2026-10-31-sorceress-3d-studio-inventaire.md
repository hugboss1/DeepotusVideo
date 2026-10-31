# Sorceress « 3D Character Studio » + TreeGen — relevé du 31/10/2026

> **Comment le relevé a été fait.** Volet de navigateur intégré, sans compte,
> fenêtre émulée 1600 × 1000. Textes lus dans le DOM (`innerText`, attributs
> `title` / `aria-label`), complétés par les dix captures fournies par
> l'utilisateur. Le relevé est en LECTURE SEULE : aucune génération, aucun
> envoi. Deux actions locales sans effet serveur : cases « Meshy 7 » et
> « Tripo v3.1 » cochées puis laissées (état de l'interface, sans compte) ; le
> clic sur une roue a ouvert le job de démonstration `a6fa3523…`.
>
> **Pages relevées :** `/3d-studio` (onglets Create, Uploads, Import, Texture,
> Rig, Refine, Animate, vue détail d'un job), `/tree-gen` (Trees, Shrubs &
> Ground). **Vu mais non relevé :** `/rigging-multileg` « Creature Rigging +
> Procedural Walk » (exige un modèle chargé), `/material-forge` (nous avons déjà
> Material Forge), `/voxelgen`. Les écrans qui exigent un compte (Uploads,
> AI auto-rig, génération) ne sont relevés que dans leur état « invité ».

## 0. Structure générale

- **Barre d'onglets centrée** en haut de l'écran, deux groupes séparés par un
  filet : `Create · Uploads · Import` | `Texture · Rig · Refine · Animate`. Le
  second groupe est grisé tant qu'aucun personnage n'est ouvert.
- **Bandeau « CURRENTLY OPEN »** sous les onglets : vignette, nom (« Rigged
  Character »), badge `RIGGED`, « 26 bones · 49 976 verts », « Unsaved
  changes in Rig » en orange, numéro de version à droite (`v798818`). Sans
  personnage : « No character open — generate, upload, or open one from
  Rigged Characters ».
- **Mise en page à trois colonnes** sur tous les onglets : panneau gauche
  (≈ 260 px), viewport 3D central, panneau droit (≈ 300 px) avec une action
  principale en bas (« Send to Refine → », « Send to Animate → »,
  « Generate · 3 credits »).
- **Chaînage** : chaque onglet finit par un bouton « Send to <onglet
  suivant> → ». Chaque carte de la galerie a « Edit Rig », « Refine »,
  « Animate » (liens `?job=<id>&tab=rig|refine|animate`).
- Couleur : fond noir, violet `#a855f7`-ish pour les actions, cyan pour
  l'onglet actif, ambre pour les avertissements (échantillonné sur capture).

## 1. Create (génération du modèle de base)

### Colonne gauche — « Select Models » (multi-sélection, total en crédits)

Cocher plusieurs modèles = un job par modèle (« Creates 2 separate 3D
generation jobs »). Chaque ligne : case, nom, badge fournisseur, badge
qualité (BEST, BEST BUDGET, AVERAGE, Low-poly, New), prix, roue de réglages
(accordéon, une seule ouverte).

| Modèle | Prix | Réglages (roue) |
|---|---|---|
| Meshy 7 (New) | 50 cr | Topology triangle/quad · Target Polycount (300 000) · Symmetry auto/on/off · Pose Mode None/a-pose/t-pose · Remesh (+15) · Generate Texture (+15) · Texture Resolution 2K/4K/8K (+10) · PBR Maps · Ultra Mode (+10) · Image Enhancement |
| Meshy 6 | 50 cr | idem sans Ultra, + Mesh Type standard/lowpoly · Remove Lighting |
| Tripo P2 (New) | 125 cr | Texture standard/HD (+10) · Quad Mesh · Face Limit · Auto Size · Texture Alignment original_image/geometry · Orientation default/align_image |
| Tripo v3.1 | 50 cr | Texture no/standard/HD · Quad Mesh (+5) · Geometry Quality standard/detailed · Face Limit · Auto Size · Texture Alignment · Orientation |
| Tripo Smart Mesh (Low-poly) | 65 cr | Texture no/standard/HD · Face Limit · Auto Size · Texture Alignment · Orientation |
| Hunyuan 3D 3.1 (BEST BUDGET) | 30 cr | (aucun réglage relevé) |
| Pixal3D (maison, VIP) | gratuit illimité | verrouillé |
| TRELLIS 2 (Microsoft) | 40 cr | Resolution 512/1024/1536 · Texture Size 1024/2048/4096 · Polycount Target · Remesh · Sampling Steps · Guidance Strength · Randomize Seed · Seed |
| Rodin 2.0 (Hyper3D) | 50 cr | Mesh Density high/medium/low/extra-low · Material PBR/Shaded/All/None · Mesh Mode Quad/Raw · Force T/A-Pose · Output Format glb/fbx/obj/usdz/stl |

Encart **RECOMMENDED POSE** : planche de référence A-pose (bras ≈ 45°, écart
membres/torse), phrase d'aide, bouton « Download pose reference image ».

### Centre — galerie

« N generations », filtres `ALL · STARRED · RIGGED · UNRIGGED` (compteurs),
curseur « GRID » (cartes par ligne, 3), recherche. Carte : bandeau
avant/après « Compare source vs 3D render » (poignée glissante entre l'image
source et le rendu 3D), badges `Done` / `Rigged`, nom du fichier + modèle,
« image to 3d · <modèle> », boutons Edit Rig / Refine / Animate.

### Droite — saisie

INPUT MODE `Image · Text · Multi-Img` ; « Drop multiple images to
batch-generate a separate 3D model for each one » ; QUANTITY 1-4 ;
ESTIMATED <total> credits ; bouton Generate.

### Vue détail d'un job (clic sur une carte)

« Back to gallery », nom, `Done`, fournisseur. Bascule `ORIGINAL · BOTH ·
OPTIMIZED` (deux viewports côte à côte, triangles affichés), curseur Rotate,
`SOURCE`. Droite : MODEL SPECS (Vertices, Triangles, Meshes, Materials),
RIGGING (« Model is rigged · 26 bones · 99 962 tris », Rig / Refine /
Animate, « Discard rig & revert to original »), RE-OPTIMIZE : préréglages
Micro Prop 500 · Small Prop 1k · Prop 2.5k · Detailed Prop 5k · Game Ready 10k
· Balanced 25k · High Detail 50k · Ultra 100k · Extreme 150k · Max Detail 200k,
curseur « Target triangles » 500 → max, « Re-Optimize » ; téléchargements
Original .glb / Optimized .glb.

## 2. Uploads

Téléverser ses propres modèles (fonction « Pro »), liste « N uploads ». Un
élément fourni : « Unreal Engine Mannequin — SMPL-fitted » (squelette SMPL
calé sur SK_Mannequin, à animer puis à recibler par l'IK Retargeter d'UE5).

## 3. Import

Gauche : UPLOAD FBX (dépôt .fbx Genesis 8/8.1) + dossier de textures
optionnel (« Daz stores hair, scalp & eyelash maps as external TIFFs »),
« Import character », « How to export from Daz Studio ». Centre : « Imported
characters — click one to send it to Animate ». Droite : IMPORT TYPE — Daz 3D
Genesis 8/8.1 (actif), Mixamo, Unreal Engine (mannequin / MetaHuman), VRM
(VRoid), Other glTF/GLB (tous « SOON »).

## 4. Texture (« TEXTURING IS IN ALPHA »)

- **Gauche « Image settings »** : REFERENCE PREVIEW ; IMAGE MODEL (★ Nano
  Banana 2 · 9 cr « best alignment », Nano Banana 2.1 · 9, Nano Banana · 6,
  GPT Image 2 · 5, Seedream 5 Lite · 6) ; RESOLUTION 1K/2K/4K ; ASPECT RATIO
  16:9, 1:1, 9:16, 21:9, 4:3, 3:2, 2:3.
- **Viewport** : cadre de capture (« snapshot · 1:1 · 1536×1536 ») ; rosace de
  vues FRONT/BACK/RIGHT/LEFT/TOP/BOTTOM + ¾ (F-R, F-L, B-R, B-L), orbite par
  pas 15/30/45/90° ; ÉCLAIRAGE Unlit (albédo pur), Flat, Soft, 3-pt, Bright +
  curseurs Bright / Ambient ; « Views (8) » ; rail de vignettes des
  références générées sous le viewport.
- **Barre d'outils verticale** (pinceau de texture) : Eraser (restaurer),
  Smudge/blend, Heal (fissures de couture), Fill from nearby (poches
  occluses), Fill all gaps, Denoise texture (IA, 2 cr), Undo/Redo, masquer la
  base, atlas UV à plat (« UV Atlas (flat unwrap) » Painted / Original GLB),
  fil de fer, propriété des vues, cadrer, revenir à la texture enregistrée,
  enregistrement de débogage, visualiseur de fissures (rouge/bleu/vert/magenta).
- **Droite** : « T-Pose arms for capture » ; GENERATE TEXTURE (prompt
  optionnel 0/1000, « Load default », Generate Texture · 9 cr, Generate with
  Progression · 9 cr) ; STYLE REFERENCE (téléverser une planche, « Generate
  from Shaded Mesh · 9 cr ») ; AUTO TEXTURE : 4 vues 36 cr, 6 vues 54, 8 vues
  72 (anneau), 10 vues 90, 12 « detail » 108 (4 côtés + zooms haut/bas),
  16 vues 144 (pas 22,5°), 18 « full sphere » 162 ; « From shaded mesh » ;
  « Run Auto Texture · 72 cr » (capture chaque angle, IA en parallèle,
  composite sur le modèle).

## 5. Rig

- **Gauche « BONES » (22)** : Pelvis, Spine Lower/Mid/Upper, Neck, Head,
  Clavicle/Upper Arm/Forearm/Hand L/R, Thigh/Shin/Foot/Toe L/R. Fiche de l'os
  sélectionné (parent, coordonnées).
- **Viewport** : squelette de référence SMPL (22 os) affiché à côté du modèle
  (« SMPL OFFSET » 155, « Hide SMPL Reference ») ; « CLICK A BONE TO ADJUST » ;
  en ajustement : gizmo de translation, bandeau « LOWERARM_L · SHIFT-CLICK TO
  ADD · ESC TO DESELECT », MIRROR, CHILDREN. SHADING Wire / Solid / Texture /
  Tex+Wire / Weights (carte de chaleur par os). CENTER (guide X = 0, nudge
  ±1/±5, Auto-center). ROTATE MODEL (Turn L/R, Tilt Fwd/Back, Fine rotate).
  CAMERA VIEW Front/Back/Left/Right/Top.
- **Droite** : SEMI-AUTOMATIC « FREE » — SKELETON 26 bones, ADJUST JOINTS /
  EXIT JOINT ADJUST, Start Over, BREAST BONES Off/On, WEIGHTS « Recompute » ;
  AI AUTO-RIG « AUTOMATIC » (« No markers to place… go straight to
  Animate »). Journal : « Restored skeleton + weights (in-memory): 26 bones,
  30 segments ». Send to Refine → / Send to Animate →.

## 6. Refine (peinture des poids)

- **Gauche « POSE TEST »** : jouer une animation enregistrée et peindre sur la
  pose déformée ; « Exit pose test (back to bind pose) ». Quatre étapes
  numérotées + un bouton global :
  - ONE-SHOT FIX « Fix everything » : reconstruit les poids d'épaule, puis
    batterie de poses d'amplitude (épaule, coude, genou, hanche, poignet,
    cheville, cou, torsions) et corrige itérativement étirement,
    compression, triangles effondrés, plis ; poids seulement, une annulation.
  - 1 ORPHAN DETECTION : îlots de poids déconnectés (Scan all / Scan bone).
  - 2 REACH CONTAINMENT : TRIM STRENGTH 70 %, Contain all limbs / this bone,
    Rebuild shoulder weights.
  - 3 SEAM SMOOTHING : COLLAR WIDTH 3 rings, « Deformed only (current pose) »,
    Soften all seams / this bone.
  - 4 DYNAMIC HEALING : joue l'animation, redistribue le poids des polygones
    trop étirés.
  - Bibliothèque d'animations (onglets 3D Studio / Voxel Studio), lecture,
    « Copy Anim for the API ».
- **Barre haute** : Undo / Redo ; vues Weights / Textured / Shaded / Wire ;
  outils Select Bone (1), Paint (2), Lasso (3, Alt = orbite), Pose (P, poignées
  IK ambre) ; Mirror Painting (M).
- **Droite « WEIGHTS »** : Bones (4) / Isolate (5) ; Select free polys
  (clic droit pour assigner) ; BRUSH SIZE 8.0 ; STRENGTH 15 % ; FALLOFF
  linear / smooth / constant ; WEIGHT TOOLS Set R · Add A · Subtract S · Smooth
  D · Blur F ; liste des os du rig (pelvis, spine_01…05, neck_01/02, head,
  clavicle, upperarm, lowerarm, hand, thigh, calf, foot, ball + *_tip) ;
  « Send to Animate → ».
- **Barre d'état** : « Model loaded — 49 976 verts, 30 bone segments… » ;
  raccourcis `[ / ]` taille, Ctrl+molette rayon, Maj+molette force, 1/2/3
  outil, Alt orbite, Ctrl+Z.

## 7. Animate

- **Gauche** : onglets Generated / Starred (8) ; COLLECTIONS (+ New,
  « All animations ») ; liste des clips (prompt, durée, images, rejouer).
- **Haut du viewport** : vues P/F/B/L/R/T, projection orthographique,
  Wire/Shaded/Textured/Tex+Wire/Weights ; **Drive Mode** (promener le
  personnage au clavier WASD, physique en direct) ; Jiggle, Hair, Cloth,
  Hands (grisés si le rig n'a pas les os / maillages).
- **Outils du viewport** : Bind Pose, IK Gun L/R, Hand L/R, Sword L/R ;
  affichage Char Bones, IK Markers, Lock Ends.
- **Droite « Generate »** : PROMPT text → animation ; MODELS (un ou
  plusieurs) HY-Motion (text → animation), Kimodo Soma 1.1 (text → animation,
  poses de début et de fin), GVHMR (vidéo → animation) ; DURATION 3 s ;
  INTENSITY 60 % ; « Generate · 3 credits ».
- **Droite « Export »** : FILE NAME ; ANIMATION COLLECTION (glisser des
  clips) ; GAME ENGINE (Unreal · Unity · Blender) : Skeletal Mesh Only .glb,
  Pose .glb, Animation .glb ; WEB / THREE.JS : Three.js Package .zip
  (personnage, clip, réglages physiques, manifeste, runtime contrôleur +
  physique + reciblage, AGENT_INSTRUCTIONS.md), Character + Animations .zip,
  Animation Clip .clip.json, Physics Config physics-config.json.

## 8. TreeGen (`/tree-gen`)

« Procedural trees · live in the browser · GLB + runtime export » (repose
sur **ez-tree**, cité dans l'infobulle « Cards »).

- **SPECIES** — Trees : Broadleaf (Oak, Ash, Aspen, Birch, Maple, Cherry
  blossom, Weeping willow), Conifer (Pine, Spruce, Fir), Tropical (Palm,
  Coconut palm), Exotic (Bare tree, Bonsai, Vine trellis). Shrubs & Ground :
  Shrub (Low shrub, Bush, Large shrub, Flowering bush, Dead shrub), Ground
  cover (Berry bush, Heather, Dune grass).
- SIZE Small/Medium/Large ; SHAPE Overall scale 1×, Branch levels 3
  (« calibrated to real-world metres »).
- FOLIAGE Real leaves (« SpeedTree look ») / Cards (« a few hundred
  triangles, for distant trees and forest LOD ») ; Leaves on/off ; LEAF SHAPE
  Auto, Oak, Ash, Aspen, Birch, Maple, Willow, Cherry, Ivy, Round, Needle,
  Grass ; SEASON Summer/Autumn/Winter ; Leaf density, Leaf size, Leaf droop ;
  Twigs.
- COLOR : BARK STYLE Auto/Oak/Birch/Pine/Willow ; Bark tint, Leaf tint
  (« baked into the leaf texture on export »).
- VARIATION : New variation, Seed (« same seed always grows the same tree »).
- Viewport : « 15.4 m · 168 342 tris · 15 016 leaves », Frame, orbite / zoom
  / pan, ciel et nuages.
- Droite : WIND (Wind sway on/off, Strength 0.7 m, Speed 1.1×, Direction 42°,
  Leaf flutter 5 cm, « Ships in the runtime ») ; STAGE (Sky & clouds) ; TREE
  (Height, Spread, Triangles, Leaves) ; EXPORT (asset name, DOWNLOAD BUNDLE
  .zip = GLB + recette JSON + runtime three.js vent / feuillage + README ; GLB
  only ; Recipe JSON) ; IMPORT RECIPE (déposer un `.treegen.json`).

## 9. Non relevé

- Comportement réel des générations, de l'auto-rig IA, des téléversements
  (compte requis, payant).
- `/rigging-multileg` (créature multipattes + marche procédurale) : écran de
  chargement seul.
- Le placement manuel de marqueurs du rig semi-automatique avant le premier
  calcul (le job de démonstration est déjà riggé).
