# Scenario Explorations — relevé (27/10/2026)

## Préambule : comment le relevé a été fait

- Cible : https://www.scenario.com/explorations (83 explorations au 27/10, filtres
  Play 15 · Watch 20 · Explore 28 · Create 20, tri « newest first », recherche `/`).
- Outil : `playwright-cli` 0.1.5 (session `scn`, Chromium Playwright), en LECTURE SEULE.
  Page d'index puis les 83 pages, `document.title + document.body.innerText` de chacune
  enregistré dans le scratchpad de session (`scn/pages/<slug>.txt`, 360 Ko au total),
  deux captures (index, Previs to Picture). Synthèse page par page en trois lots
  relus par sous-agents, pages Blender relues directement.
- État laissé : bandeau cookies NON accepté (ni « Accept » ni « Reject » cliqué),
  aucun compte, aucun formulaire, navigateur fermé.
- Non relevé : 14 pages surtout interactives (jeux, configurateurs, zoom infini)
  ne livrent que leurs commandes en texte : apex-livery-studio, continuity-heist (en
  partie), crimson-tower, fan-cam, kumo-ramen, lamplighter, last-repair-shop,
  little-lights, little-paper-voyage, mirror-keeper, park-atlas, rover-foundry,
  saint-seiya, the-drifting-afternoon, wish-you-were-here ; material-worlds,
  paper-city, the-room-remembers en grande partie. Les PDF « making-of » et les ZIP
  de skills n'ont PAS été téléchargés (règle : pas de téléchargement sans accord).
- L'existant DeepotusVideo a été relu sur `origin/main` (le `main` local a 893
  commits de retard).

## 1. Ce qu'est la page

Une vitrine de cas d'usage. Chaque exploration = un livrable fini (film, jeu jouable
dans le navigateur, configurateur, visionneuse 3D) + son « how it was made » :

- barre commune : `Scenario / Explorations` · How it was made · PDF · Skill · Make yours ↗ ;
- sections numérotées `01 / 02…`, film d'abord, puis la chaîne, les assets
  (carte = modèle + coût CU + lien PROMPT), la facture, les ratés, « Make yours » ;
- comparateurs à curseur (wipe) avec raccourcis : **O** maintenu = original,
  **C** = comparer, **F** = « peler le code », flèches / Espace, pas image par image ;
- pied commun : « Create with Scenario MCP / Scenario Skills » (ou « Astra ») ;
- presque toujours : **skill d'agent ZIP** (`~/.claude/skills/` ou `~/.codex/skills/`),
  **making-of PDF illustré**, film narré, prompts complets.

Le message produit : *un agent (Claude Code / Opus 5.5, parfois Codex) + le Scenario
MCP + un skill = un pipeline reproductible en une session, souvent un seul prompt.*

## 2. Les briques de Scenario citées dans les pages

| Famille | Briques relevées |
|---|---|
| MCP | boucle `search → recommend → model_schema_get → model_run` ; asset analysis / caption / describe ; detect depth ; **Quality Gate** (/100) ; « art director » noté /10 ; Prompt Spark ; Scenario LLM |
| Plugin Blender (open source, Blender 5.0+) | panneau latéral ; **Render Video** depuis la caméra de scène ; **asset slots** (le proxy gris est remplacé par l'asset, révisions) ; `apply_world` ; `apply_pbr_maps` ; tâches en arrière-plan, liste des générations ; « Scenario Blender skills » (relumage, remplacement de figurants) |
| Workflows 2D | **Pixelate** (grille exacte) ; **Pixel Lock** (sprite + porte d'approbation) ; **Pose Keyframe** (nouvelle pose, même grille) ; **Animate Loop** (2 poses + 1 phrase → boucle) ; Video to Frames ; Grid Maker ; Frames to GIF ; Resize ; Layerize (Seedream 5.0 Pro) |
| 3D / monde | Skybox GPT (360°, 3840×1920), HDRI Skybox (EXR), PATINA Material (PBR), Scenario Texture, Tripo Segmentation v2 (pièces), Uthana rig 52 os, Video/Text to Motion (Uthana, Cartwheel), Meshy Animation |
| Vidéo | Video Studio (composite), video-to-video, édition « change only X » avec `@video1 @image1`, 3D Color LUT, motion control |
| Roblox | Roblox Studio MCP + 14 skills `scenario-roblox-*` (Graveyard Waves) |

Modèles les plus cités : GPT Image 2 / 2.5 Sunburst / Flare, Seedance 2.5 (partout en
vidéo), MiniMax H3, Kling V3 Pro, Hunyuan 3D 3.1 Pro, Tripo 3.1 / P2, Hitem3D 3.0,
Meshy 7.1, Rodin Gen-2.5, GPT-6 Astra 3D, Claude Opus 5.5 3D, ElevenLabs Music v2.5 /
SFX 2 / v4, Lyria 3.5, Gemini 3.5 Transcribe, SAM 3.1, Sync-3, P-Video.

## 3. Explorations par famille (83)

### 3.1 Blender → image finale (previs, layout, mise en scène) — cœur « Chapitres »

| Slug | Mécanique relevée |
|---|---|
| previs-to-picture | Previs Blender **colorée, jamais grise**, code couleur publié (jaune = ajoncs, cônes verts = cyprès…) ; les prompts nomment chaque forme. Voiture : concept → Hunyuan → Tripo Segmentation 33 pièces (roues à la bonne vitesse). Skybox tourné pour placer le couchant. 2 style frames peintes sur stills de previs (GPT Image 2, Quality Gate 96). Seedance 2.5 **video-to-video** previs 720p → 1080p (~6 min). Contrôles : dérive ≤ 1 image (corrélation de bords), depth check frame 340, fidélité 9–9,5/10. Faisceau du phare retiré avant envoi (sinon objet solide). Shoot-out Seedance 2.0 (4/10) vs 2.5 (8/10). Son : 5 stems, niveau moteur lié à la distance caméra-voiture, −16,5 LUFS. 52 min, 30 appels, 4 198 CU. Skill `scenario-previs-to-picture` (5 scripts : export réf., drift, conform, paires, mix distance). |
| grease-pencil-to-final-frame | 5 animatics Grease Pencil → plugin capture caméra → Seedance 2.5 / MiniMax H3 avec un « look » (monde, lumière, matière, **pas le mouvement**). Durée mini des modèles (4 s / 5 s) : 3 routes — étirer puis ré-accélérer, compléter au noir puis couper, assez long. Décalage mesuré par image (Seedance moy. ≤ 2,4 ; MiniMax jusqu'à 31). Option « traits du crayon par-dessus ». |
| the-last-lantern | Film 2 min, 40 cuts. Grey-box Blender 289 objets (audit 0 chevauchement), 14 plans previs/animatic avant tout crédit. Modèles remplacent les blocs (cachés, pas supprimés). 40 cuts planifiés caméra principale + couverture (audit ray-cast). **Chaque cut en 4 versions : clay Workbench, look EEVEE, still, film.** Feuilles de référence par élément récurrent (lanterne, porte, visage) données aux stills. Seedance `@video1` (clay) + `@image1` (still). Skill « Blockout to Film ». |
| one-take-many-angles | Une scène Blender = référence spatiale ; 3 mondes (Gemini 3.0 Pro) ; une performance continue (Seedance 2.5) **recoupée en 13 angles** avec focale par angle (28 mm plan large…). |
| impossible-rides | Trajectoires caméra impossibles dirigées dans Blender, master du véhicule + 9 vues de référence, Seedance interprète ; comparateur Realistic / Stylized. |
| hold-on | Stop-motion feutrine 2:08, 25 plans : turnaround + 4 expressions par personnage en référence à chaque keyframe ; layout de la crique en proxys colorés (couleur = personnage/matière) ; 1re/dernière image par beat ; contrôle image par image ; musique 11 sections calées sur le montage. |
| sleeping-giant | 3 assets 3D pour fixer échelle/caméra (guide seulement) ; storyboard par beats ; réparations de continuité par édition d'image avant la vidéo ; contre-champ ajouté. |
| twenty-minutes | Personnage construit à l'écran (dessin → maillage → rig Uthana → 5 vêtements → Text to Motion → monde) ; playblast EEVEE 30 s fini par Seedance avec 7 keyframes ; Quality Gate 65 WARN → 78 PASS. |
| pavilion / hadal / last-order / paper-harbor / lamplight-deep / neon-drift | Agent seul dans Blender 5.2 en 55 à 125 min sur un prompt : blocage gris → assets dans les slots → PATINA → Skybox/HDRI → **boucle de revue** (rendus test → analyse → correction nommée) → rendu EEVEE/Cycles ; son calé sur les frames. Pavilion compare 3 captures de mouvement (dérive du pied en cm/s). |
| blender-2d-animation | Side-scroller : 10 images par look (concept = référence de tout, héros sur **magenta**), cartes alpha en parallaxe (0,97 / 0,85 / 0,6 / −0,45), caméra ortho, rigid bodies tracés sur le contour ; nouveau thème = `build_scene.py --set assets_snow`. |
| two-rulers | Reconstruction fidèle d'un concept dans Blender : caméra résolue, `LAYOUT.json` en mm, 4 gates notés en IoU de silhouette. |

### 3.2 Game assets

| Slug | Mécanique relevée |
|---|---|
| scroll-courier | 5 routes pixel comparées et mesurées (taille de bloc, couleurs, pixels parasites) ; la grille vient d'un OUTIL (Pixelate, gardé, contre Pixel Snapper) ; Pixel Lock → Pose Keyframe → Animate Loop (Seedance 1re/dernière image même pose, 4 s, 1:1) → 24 images re-pixelisées → feuille 4×6 + GIF. **Ne jamais miroiter** (objet dans la mauvaise main). Cycles : garder 1 image sur 2-3, pas 1 sur 4. Parallaxe : peinture 3072×1024 découpée en 5 calques (Layerize). |
| iso-cycles | 5 héros × 8 directions × 4 cycles × 8 images ; 5 colonnes dessinées, SW/W/NW en miroir ; 96/80/64 px ; boucle extraite des images 20–67, couture 0,50× ; 20 feuilles PNG + données. |
| pit-tactics | 2 angles par unité sur magenta, zombies = éditions des humains, i2v (idle/walk/attack/death), clé magenta, pixélisation palette fixe, miroir des directions manquantes, effets en feuilles de 16 images, props intacts/détruits appariés. |
| pixel-vfx-forge | ~40 VFX pixel en **recettes JSON** copiables ; teinte, palette (PICO-8, Sweetie 16, Endesga 32, Game Boy, 1-bit), contour, tramage, images, fps, boucle, graine. |
| hibana | Combat 3D navigateur en 3 jours : planche → 3D 40 k tris → rig 52 os → mouvements en vidéo Kling → Video to Motion → retimage 60 i/s (startup/active/recovery) → hitboxes sur os ; voix en 5 langues. |
| graveyard-waves | Roblox : budget de triangles par rôle (700–6 000), rig + 38 clips, VFX flipbook, HUD depuis planche 2×2, SFX choisis par loudness/attaque/transcription, musique en boucles de phrases ; Roblox Studio MCP, playtest à chaque vague. |
| quarantine-07 | 7 kits, 66 designs, 198 GLB en **3 densités natives** (50 k / 8 k / 2 k), pièces mobiles séparées. |
| small-worlds-real-craft | Concept → Meshy → reconstruction bas-poly par Opus 5.5 3D (834 978 → 4 990 tris, détail cuit), pièces mobiles, caisse en 26 morceaux, village Unity 6. |
| image-to-3d-benchmark | 12 modèles × 6 images, vues Textured/Clay/Wireframe, tableau tris / arêtes ouvertes / shape match / temps ; test bas-poly 4 k / 10 k. |
| full-circle | Orbite 360° par pas de 22,5°, hauteurs Top/High/Eye/Low, « on location » / sans fond, bascule 3D. |
| nine-models-one-brief | 9 modèles image × 18 tests (icônes d'inventaire, texture seamless, turnaround, feuille d'expressions…) avec CU et temps, tableau triable. |
| sketch-to-asset / mech-bay / rover-foundry / build-a-reef / island-builder / theme-swap / full-self-flying / material-worlds | Croquis → carte → 3D ; pièces interchangeables ; jeu three.js avec décor réduit < 1 Mo en Blender headless ; fenêtres détectées par clé de couleur et allumées la nuit ; re-thème d'un jeu entier par édition en place ; 6 mondes de matières sur un même asset. |

### 3.3 Vidéo, personnages, voix

alter (11 changements d'une prise, « target frame », brouillon 480p puis final des
seuls validés, 7 mesures), change-only-x / -fashion / -product (édition chaînée, une
étape = entrée de la suivante), a-cast-of-one (un acteur au téléphone joue 4 rôles),
same-moves-new-actor (motion control sur 8 acteurs), one-more-take (12 langues,
13 directions de jeu), dotties-voice (prompt « chorégraphie » seconde par seconde,
réparation d'un plan à bornes verrouillées), green-screen-to-any-scene (FLUX.3 Edit
Video gagne et coûte le moins), give-each-picture-a-job (un rôle par référence +
« ne pas prendre »), babel-tavern (8 langues, voix verrouillée redonnée, lèvres =
95 % du coût, contre-vérif par transcription), the-picture-book (texte typographié,
jamais dessiné ; « nommer ce qui se compte »), game-to-trailer, tap-to-install,
eight-ways-to-edit (8 skills de montage), auto-edit, every-scenario (code par-dessus
la vidéo, matte personne), video-color-grade (LUT 33³ en code), motion-loops.

### 3.4 Marketing / produit / lieux

same-product-every-variation, one-sole, bottled, maison-vespree,
impossible-fitting-room (calculateur de coût), one-logo-42-worlds, mirage-house,
open-house (.spz), the-room-remembers, the-stones-remember, inside-a-heartbeat,
celestial-orrery, park-atlas, apex-livery-studio.

## 4. Motifs transverses

1. **Un pipeline = un skill téléchargeable + un PDF + des prompts publiés.**
2. **Blender guide, le modèle vidéo peint** : Blender fige géographie, échelle,
   caméra, timing ; la vidéo/édition « repeint ». Proxys **colorés et nommés**.
3. **Boucle de revue chiffrée** : Quality Gate, notes /10, dérive en images,
   profondeur, IoU de silhouette, dérive de pied, transcription. Le site dit lui-même
   que le Quality Gate est « far more lenient » qu'une revue d'art.
4. **Facture visible** : CU par asset, total, durée de session, échecs comptés.
5. **Ratés montrés** avec la correction (faisceau retiré, rochers carrés, manches
   trouées, dragon à l'œil fermé).
6. **Cohérence** : feuilles personnage/élément en référence des STILLS (pas de la
   vidéo), accessoire canonique, rôle unique par référence.
7. **Texte composé en code**, jamais demandé au modèle.
