# DeepotusVideo « assets 2D » — inventaire de la Sprite Suite de sorceress.games (19/09/2026)

> Relevé fait en LECTURE SEULE dans le volet intégré du navigateur (site
> public, sans compte, viewport émulé 1400 × 900, bandeau cookies non
> apparu). Neuf outils du lanceur parcourus par leur URL ; le Sprite Editor
> a été ouvert en lui fournissant un PNG synthétique de 32 × 32 (fichier
> créé en mémoire, jamais téléversé sur un compte) ; le Tile Studio a été
> ouvert sur une tuile de démonstration. Aucune génération, aucun export,
> aucune connexion ; rien n'a été laissé sur le site (sessions locales
> vides). Rappel : cette suite était déjà la référence produit de la spec
> `2026-07-19-game-assets-2d-sprites-design.md` (Auto-Sprite v2, True
> Pixel, Quick Sprites, Sprite Analyzer) ; ce relevé mesure ce qui a
> CHANGÉ depuis et ce que nous n'avons pas transposé.

## 1. Structure du lanceur `/tools/sprite-suite`

| Zone | Cotes mesurées (px à 1400 de large) | Contenu |
|---|---|---|
| Barre de navigation | h ≈ 57, fond noir à 90 %, fixe | logo « SORCERESS », dix icônes d'outils (WizardGenie, Generate, Video, AutoSprite V3, 3D Studio, VoxelGen, Audio Suite, Tools Suite, Legacy Tools), boutons Marketplace · Play · In Dev · WizardGenie · Software, sept icônes (cours, blog, wiki, lexique de prompts, guide des outils, plans), « Get started » (pilule orange), « Sign in » |
| En-tête | H1 48 px blanc « Sprite Suite », sous-titre 16 px gris | « A compact launchpad for sprite creation, sheet inspection, pixel conversion, fast sprite generation, and 3D-to-2D asset workflows. » |
| Grille de cartes | 3 colonnes de 358 px, gouttière 54, cartes ≈ 340 px de haut, coins 8 px, fond translucide sombre | titre H3 18 px, icône dans un carré violet, paragraphe 14 px, vignette animée, pied : bouton « TUTORIAL » (contour) à gauche et bouton d'ouverture (plein, violet) à droite ; badge « NEW » sur quatre cartes |

Les neuf cartes, dans l'ordre : Auto Sprite (`/autosprite-v2`), Sprite Analyzer (`/spritesheet-analyzer`), Quick Sprites (`/quick-sprites`), True Pixel (`/pixel-art`), 3D to 2D (`/3d-to-2d`), Pixel Snap NEW (`/spritely`), Sprite Editor NEW (`/sprite-editor`), Tileset Forge V2 NEW (`/tileset-forge-v2`), Isometric Tileset Forge NEW (`/isometric-tileset-forge`).

## 2. Couleurs (lues au style calculé)

| Rôle | Valeur |
|---|---|
| fond de page | #000000 ; panneaux en noir translucide (oklab 0,14–0,21 à 70–80 %) |
| accent violet (boutons pleins, pastilles, bordures actives) | oklab(0,627 0,148 −0,220) ≈ #b04cff à 20–25 % pour les fonds, plein pour les boutons d'ouverture |
| accent orange « Get started » | lab(43 75 −87) ≈ #f08a2a |
| accent cyan (survol, tuile « déjà placée », bouton Analyzer) | oklab(0,715 −0,117 −0,082) ≈ #22c3d8 à 20 % |
| texte | #ffffff ; secondaire lab 65 ≈ #9a9a9a ; libellés de section en capitales 10–11 px |
| grille de l'Analyzer | cellules à liseré vert #3aa66b sur fond vert sombre, numéro de frame en haut à gauche, cellule cochée en vert plus clair |

## 3. Typographie

`ui-sans-serif, system-ui` ; corps 16 px ; H1 48, H2 20, H3 18 ; libellés de section en capitales 10–11 px espacées ; champs et boutons 12–14 px ; petites cotes 9 px.

## 4. Menus et navigation

Pas de barre de menus classique : la navigation est la barre du site (§1). Chaque outil est une page pleine à trois colonnes (gauche : sources / galerie ; centre : scène ; droite : réglages + export), sans onglets de document. Les raccourcis sont portés par les bulles des boutons (relevés ci-dessous).

## 5. Les neuf outils, entrée par entrée

### 5.1 Sprite Analyzer (`/spritesheet-analyzer`) — ouvert sans compte sur la démo « Wizard Walk » 512 × 512

| Zone | Contenu relevé |
|---|---|
| Colonne gauche | « Sign in to upload your own » ; onglets **Files (1)** / **Sprite Sets** (« No saved sprite sets ») ; fiche « Wizard Walk » cochée ; **SECTIONS** avec boutons « Copy tags as JSON » / « Download tags JSON » et l'aide : « Right-click selected frames to set Start · Middle · End, add a Custom section, or toggle loop / ping-pong / reverse. » |
| Onglets de scène | **Animation** · **Combat** · **Playground** |
| Barre de la scène (Animation) | « Auto-Detect » (bulle : *Try to automatically detect columns, rows, and used frames from the sheet*), **Grid** col × row (deux champs, « OK » = *Apply these columns and rows*), « 512×512 », compteur « 31/36 », **All** / **Clear selected**, **EVERY** 1 · 2nd · 3rd · 4th (*Every 2nd frame (0, 2, 4…)*), zoom − / + (*Ctrl + mouse scroll*), *Fit width*, **1:1** (*native pixel size*) ; phrase d'aide : « Drag paint over · Ctrl add/remove · Shift last→here · Right-click segment » |
| Scène | grille 6 × 6 de cellules vertes numérotées 0–35, 31 cochées (les 5 dernières vides) |
| Onglet Combat | « DRAW HITBOXES » / « SELECT FRAMES », aide « Drag to draw · click frame to select · Ctrl/⌘+C/V copy-paste », « 0 hit », bande de frames 0–30, « Hitbox inspector — Click frames to select paste targets (or use Select frames). Ctrl/⌘+C copies · Ctrl/⌘+V pastes onto selected frames. » |
| Onglet Playground | fonds : Checker grid · Solid dark · Sky · Outdoor · Cave · Dungeon · Sunset · Snow / ice ; PAUSE, vitesse « 2.0x », **Invert L/R**, **Grid**, « 31f », « 30 fps », touches W A S D ; aide « WASD or Arrow keys to move · Scroll to zoom · Middle-drag to pan · Space play/pause » |
| Colonne droite | **Preview** (bouton **HD** : *full-resolution preview. Click for faster playback with many frames*), **Playground** (*animation preview with WASD movement*), zoom −/+ (*scroll over preview to zoom toward cursor*), crosshair (*Toggle a center crosshair guide*), **AUTO ALIGN** (*line up selected frames to the first — great for AI sheets that wobble*) avec trois modes *Align both axes* / *left/right only* / *up/down (feet) only*, nudges ↑ ← ⟲ → ↓ 1 px (*Recenter this frame*), « Frame 0 · 31 selected », **FPS** (*Playback + export FPS*), **START** 0 / **END** 30 ; encart **Pixel Snap** « Sprite Fusion · true pixel grid on this sheet » → **FULL TOOL** (lien `/spritely`), **COLORS** curseur (16), **PIXEL SIZE** 1PX · 2PX · 3PX · 4PX · AUTO, **CONVERT TO PIXELS** ; **Export** : « PNG + .json config for your coding agent that tells your coding agent how to set up the sheet exactly as you have it here. » → « Sign in to Export » |

### 5.2 Sprite Editor (`/sprite-editor`) — NEW, ouvert sans compte

Écran d'accueil : « OPEN SOMETHING » — **Single image** (PNG/JPG/WebP, une frame), **Image sequence** (plusieurs fichiers → animation dans l'ordre des noms), **Sprite sheet** (feuille + grille à indiquer → chaque frame sur la ligne de temps) ; **SAVED SESSIONS** « Stored locally in this browser » (autosave ou Ctrl+S).

| Zone | Contenu relevé (après ouverture d'un PNG 32 × 32) |
|---|---|
| Barre haute | « SPRITE EDITOR · 32×32 · 1 frame », champ **Name — used for exported files**, **AUTO ✓** (*Autosave is on… Click for manual saving*), **SAVED** (*Save session (Ctrl+S) — stores every layer, frame and timing locally*), Undo (Ctrl+Z) / Redo (Ctrl+Shift+Z), menus **SPRITE · VIEW · PIXEL SNAP · EXPORT** (non déroulés, voir §10), *Keyboard shortcuts*, zoom − (−) / **Fit (F)** / + (+), « 1600% », *Close Sprite Editor* |
| Barre contextuelle du pinceau | **BRUSH** · **Size** curseur (1) · **ROUND** / **SQUARE** · **PIXEL-PERFECT** (*Keeps 1px strokes one pixel wide on diagonals*) · **MIRROR X** (*across the vertical center*) · **MIRROR Y** ; aide : « Drag to paint · right-click paints secondary · Shift+click lines from last point · Alt picks color » |
| Colonne d'outils (gauche) | Brush (B) · Eraser (E) · Eyedropper (I) · Fill (G) · Line (L) · Rectangle (R) · Ellipse (O) · Select box (M) · Select lasso (Q) · Select wand (W) · Move (V) · Pan (H) ; pastilles **primaire** (*click to edit · X swaps*) et **secondaire** (*right-click paints with it (transparent = erase)*), **Swap colors (X)** |
| Barre d'état | « Frame 1/1 · Layer 1 · Wheel zoom · Space pan · Right-click secondary » |
| Ligne de temps (bas) | Play / pause (Enter), **Loop playback**, *Hide current frame from playback*, **FPS** 12, **MS** 83, **Onion skin — ghost neighboring frames (red = previous, blue = next)**, tailles de vignettes **S · M · L**, **New layer — added above the active layer**, **Duplicate current frame**, **New empty frame**, **Delete current frame** ; grille calques × frames (« Layer 1 · frame 1 », *Hide layer*) |
| Colonne droite | **COLOR** : PRIMARY, A 100 %, champ hex `#eeeeee`, **PALETTE** From sprite · Classic 32 · Retro 16 · Arcade 16 · Handheld 4 · Grayscale 16, pastilles (*click: primary · right-click: secondary · Alt+click: remove*), *Add primary color to palette* ; **LAYERS** : New layer · Duplicate layer · Merge into the layer below · Delete layer · **Opacity** curseur 100 % · Hide · Lock · Move up · Move down |

### 5.3 Tileset Forge V2 (`/tileset-forge-v2`) — NEW, galerie de 15 démos, génération sur compte

| Zone | Contenu relevé |
|---|---|
| Colonne gauche « IMAGE MODELS » | 17 modèles avec coût en crédits (GPT Image 2.5 Flare/Sunburst VIP, GPT Image 2 8 cr, GPT Image 1.5 4 cr, Nano Banana 2 Lite/2/Pro/…, Grok Imagine, Seedream 5 Pro/Lite/4.5, Wan 2.7, Flux 2 Pro, Z-Image 3 cr), chacun avec **settings** et **Toggle** ; « Corridor Key inside » |
| Galerie | « Previewing demo creations. Sign in to generate and save your own tilesets. », **New Workspace**, **Upload**, filtre workspace « Everything · 15 », filtres **All · Keyed · Not keyed · Starred** ; carte = modèle, badge KEYED, JOB ID (*Copy Job ID for API agents*), View full size · Download · Reuse prompt · Delete · **Tile Studio** |
| Colonne droite « PROMPT » | zone de texte (*Describe the tile — surface, style, lighting, and how it should repeat…*), **Voice input**, *Resize prompt input*, bouton **JUNGLE TILESET STARTER** (*Load a complete example prompt…*), **ASPECT RATIO** auto · 16:9 · 1:1 · 9:16 · 21:9 · 9:21 · 4:3 · 3:4 · 3:2 · 2:3 · 2:1 · 1:2 · 3:1 · 1:3 · 5:4 · 4:5, **QUANTITY** 1–4, **REFERENCE IMAGES** (*Drop images here or click to upload · Drag from gallery*), **DESTINATION** (*SAME AS GALLERY*), **ESTIMATED 8 credits**, « SIGN IN TO GENERATE » |

**Tile Studio** (modale sur une tuile, « Demo preview — browsing only ») :

| Zone | Contenu relevé |
|---|---|
| Tête | JOB ID, **Rename**, **Saved**, **Use prompt** (*Load this tile's prompt back into the generator*), **Download this sheet**, **Close (Esc)** |
| **PIXEL TOOLS** « click a tool to paint » | Brush (B) · Eraser (E) · Eyedropper (I) · Fill (G) · Line (L) · Rectangle (R) · Ellipse (O) · Select box (M) · Select lasso (Q) · Select wand (W) · Move selection (V) · Clone stamp (S) ; primaire / secondaire / Swap (X) |
| **COLOR / PALETTE** | PRIMARY, A 100 %, hex, palettes From sheet · Classic 32 · Retro 16 · Arcade 16 · Handheld 4 · Grayscale 16, 32 pastilles extraites de la feuille, *Add primary color to palette* |
| **EXPORT** | taille de tuile 16 · 32 · 48 · 64 · 96 · 128 · 256 · 512 px, **PIXEL** (*Nearest-neighbor resampling (crisp pixel art) — click for smooth*), **PAD** (nombre), **Aligned sheet (.zip)** (*Every tile re-packed pixel-perfect into a uniform grid, plus a JSON manifest*), **Individual tiles (.zip)** (*One PNG per tile, named by the AI names when present*), **Tileset (PNG)** (*The painted tileset as one image*) |
| Vues | **Sheet** (*The full sheet, with detected-tile outlines*) · **Tileset** (*Paint tiles onto a grid to test how they connect*) · **Tile ×9** (*The selected tile repeated 3×3 — seam check*) ; **Outlines**, grille de pixels (*at 800%+ zoom*), Undo / Redo, zoom −/+, **Fit (0)**, **100% (1)** |
| Chaîne | **Prepare tileset** (*Runs the whole flow: remove the background, detect the tiles, open the tileset*) ; **BACKGROUND** « removed » (*click for keying, transform and resize options*), **Re-run removal 2 cr** (*Neural GPU matting — saves as this sheet's keyed variant*) ; **TILES** : *Detect tiles* (*Slice the sheet into individual tiles from the transparent gaps*), *Auto-fit all* (*snap connective tiles to the grid cell, stretch slopes…*), *Pixel Snap* (*Convert the sheet to clean pixel art*) |
| Aide | « Click a tile to paint it on the tileset. A cyan border means that tile is already placed. Clone makes an independent copy you can resize without changing the original. Shift/ctrl-click selects several — inspector edits then apply to all. Double-click for the 3×3 seam check. » |

### 5.4 Isometric Tileset Forge (`/isometric-tileset-forge`) — NEW, alpha

Bandeau « ALPHA VERSION — some features are still being worked on for isometric tilesets. The board is a 2:1 diamond grid. » (Dismiss). Même colonne de modèles, galerie vide (« No tiles yet · OPEN IMAGE MODELS · or · UPLOAD AN IMAGE »), prompt « Describe the isometric tileset — diamond ground, cubes, slopes, lighting, environment… », starter **ISOMETRIC JUNGLE STARTER**, mêmes ratios / quantité / références / destination, « ESTIMATED 5 credits ».

### 5.5 Pixel Snap (`/spritely`) — NEW

Colonne gauche : mêmes modèles ; **PIXEL SNAP GALLERY** « 0 LOADED SHEETS », FAVORITES, **UPLOAD SHEET**, **UPLOAD VIDEO**. Centre : « Turn character art into pixel sprite sheets. Generate sprites, remove backgrounds, snap to a clean pixel grid, align frames, and preview your animation before you export. » + vidéo. Droite : **PROMPT** avec deux gabarits **1 FRAME** (*One static character on a clean green-screen background. game sprite pixel art CHARACTER_DESCRIPTION*) et **6 WALK** (*Row of 6 frames showing a walk cycle. Replace KNIGHT with your character*), **REFERENCE IMAGE** (Add reference), **ASPECT** (16 ratios), **QUANTITY** 1–4, « ESTIMATED 8 credits », **GENERATE**.

### 5.6 True Pixel (`/pixel-art`) — « Pro Feature », réglages visibles sans compte

Gauche : **ENHANCEMENT** Edge Enhance · Outline / Dark Edges (cases) · Contrast · Brightness (nombres) ; **TARGET RESOLUTION** Lock, W × H (64 × 64), presets 16 · 32 · 48 · 64 · 96 · 128 · 256 ; **COLOR PALETTE** Auto Extract / Preset, **Max Colors** 256 avec 8 · 16 · 32 · 64 · 128 · 256 ; **PIXEL SCALE** « 4x → 256×256 » 1x · 2x · 4x · 8x · 16x ; **DITHERING** None · Ordered · Floyd-S ; **PROFILES**. Droite : **BACKGROUND REMOVAL** Chroma Key · CorridorKey · *Pick Chroma Key Color*. Centre : vidéo « Convert Any Image to True Pixel Art ».

### 5.7 Quick Sprites (`/quick-sprites`) — génération sur compte

**ANIMATION STYLES** : Four Angle Walking (48×48 only, « Consistent 4 direction, 4 frame walking animations of humanoid characters »), Small Sprites (32×32 only, « 4 direction walking, arm movement, looking, surprised, and laying down »), VFX Effects (24–96 px, 1:1) ; **SEED** ; galerie **GRID** curseur (4), All / Favorites, *Select multiple sprites to download, delete, or send to Sprite Analyzer*, par carte Download · Reuse · **Send to Sprite Analyzer** · Delete ; **PROMPT**, **OUTPUT FORMAT** Spritesheet (PNG) / Animated GIF, **REFERENCE IMAGE (OPTIONAL)**, « Simple Sprites Only — For fully custom sprites, use Auto-Sprite. New! Convert any art into pixel graphics with True Pixel. », « ESTIMATED 9 credits ».

### 5.8 AutoSprite V2 (`/autosprite-v2`) — LEGACY, aperçu gratuit

« Try AutoSprite free · Drop image or video here · Upload your own, or try this test video » (**Test AutoSprite with this video**), « Tools appear here after upload », **QUICK GUIDE** Upload → Extract frames → Remove background → Sprite sheet ; trois encarts « NOW AVAILABLE AutoSprite V3 — One prompt → game-ready animated sprites ».

### 5.9 3D to 2D (`/3d-to-2d`)

« Drop 3D model here · or click to browse · FBX, GLB, GLTF », onglets **3D Model · 2D Preview · Test Drive**, **EXPORT OPTIONS** (vide sans modèle), tutoriel.

## 6. Panneaux : le gabarit commun

Trois colonnes (gauche ≈ 300 : sources / modèles / galerie ; centre : scène ; droite ≈ 320 : réglages puis export), titres de section en capitales 10–11 px, groupes de boutons-radio en pilules (ratios, quantités, tailles), un bouton d'action plein violet en bas de la colonne droite avec le coût « ESTIMATED n credits », et le bouton devient « Sign in to … » sans compte.

## 7. Gestes relevés (phrases exactes des aides)

| Geste | Analyzer | Sprite Editor / Tile Studio |
|---|---|---|
| Sélection de frames / tuiles | « Drag paint over · Ctrl add/remove · Shift last→here · Right-click segment » | « Shift/ctrl-click selects several — inspector edits then apply to all » |
| Peinture | — | « Drag to paint · right-click paints secondary · Shift+click lines from last point · Alt picks color » |
| Palette | — | « click: primary · right-click: secondary · Alt+click: remove » |
| Vue | « Ctrl + mouse scroll » zoom, « scroll over preview to zoom toward cursor » | « Wheel zoom · Space pan · Right-click secondary » ; pixel grid à 800 %+ |
| Lecture | Space play/pause, WASD ou flèches (Playground), Middle-drag pan | Enter play/pause, Loop, onion skin rouge/bleu |
| Raccord | — | double-clic = seam check 3×3 |
| Copier-coller | hitboxes Ctrl/⌘+C/V entre frames | — |

## 8. Réglages et bornes

| Réglage | Bornes vues |
|---|---|
| Grille de feuille | colonnes × lignes (6 × 6 sur la démo), Auto-Detect |
| FPS | 30 (Analyzer), 12 = 83 ms (Editor) |
| Couleurs Pixel Snap | curseur 1–? (16 par défaut), pixel size 1–4 px ou Auto |
| True Pixel | résolution 16–256 (W × H libres, Lock), 8–256 couleurs, échelle 1×–16×, dither 3 modes |
| Tile Studio export | 16–512 px, PAD n px, nearest / smooth |
| Quantité de génération | 1–4 ; ratios 16 |

## 9. Comportements notés

- Tout se lance sans compte et le compte n'est demandé QU'AU moment de générer ou d'exporter (« Sign in to Export », « SIGN IN TO GENERATE ») : la démo est entièrement manipulable.
- Le coût en crédits est affiché AVANT le tir, par modèle et par lot (« ESTIMATED 8 credits »).
- Le Sprite Editor et le Tile Studio partagent les mêmes 11–12 outils raster, les mêmes six palettes nommées et la même sémantique primaire / secondaire (droit = secondaire, transparent = gomme).
- Les feuilles d'IA « qui tremblent » ont un correctif dédié : **Auto Align** (les deux axes, gauche/droite seulement, pieds seulement) et les nudges 1 px.
- L'export de l'Analyzer vise « your coding agent » : un JSON qui décrit la feuille (grille, sections nommées Start/Middle/End, boucle / ping-pong / inversé, hitboxes).
- Chaque création porte un **Job ID** copiable « for API agents ».
- Le Tileset Forge sépare **Keyed** (fond retiré) de **Not keyed**, et repasse le détourage par « Neural GPU matting » à 2 crédits.
- Sessions de l'éditeur stockées dans le navigateur (autosave), pas sur le serveur.

## 10. Non relevé

| Élément | Raison |
|---|---|
| Menus SPRITE · VIEW · PIXEL SNAP · EXPORT du Sprite Editor | non déroulés (relevé arrêté aux barres et panneaux visibles) |
| Résultat d'une génération, d'un « Convert to pixels », d'un export | exigent un compte et des crédits — aucune saisie |
| Outils d'AutoSprite V2 après téléversement, viewer 3D to 2D après import | exigent un fichier utilisateur (une vidéo de test existe mais n'a pas été lancée) |
| Menu contextuel « Start · Middle · End » de l'Analyzer | clic droit non simulé |
| Captures d'écran des pages d'outils | le volet caché ne dessine pas (captures en échec) ; le relevé vient du DOM |
