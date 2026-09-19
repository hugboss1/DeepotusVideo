# DeepotusVideo « assets 2D » — conception depuis l'inventaire de la Sprite Suite (19/09/2026)

> Inventaire : `2026-09-19-sorceress-sprite-suite-inventaire.md`. Équivalents
> chez nous, ALLÉS VOIR : `frontend/spritelab/` (chaîne image → Seedance →
> frames → détourage → sheet, 665 lignes), `frontend/tilelab/` (seamless +
> pavage 3×3, 220 lignes), `backend/app/services/sprite_service.py`
> (extraction ffmpeg, rembg api/local, assemblage PIL, pack Unity, 644
> lignes), persona **Pixel** du Vectorlab (`mod-pixelui.js` : outils
> `px-crayon/pinceau/gomme/seau/ligne/rectpx/lasso/selrect/baguette/cloner/
> palette/raccord/grille/pelure`, cadres d'animation = images du calque
> « cadres », `mod-pixelart.js` pur : Bresenham, median cut, raccord 3×3,
> feuille, bande, pelure). Décisions à VALIDER par l'utilisateur avant tout
> plan. Aucune dépendance payante nouvelle : tout ce qui suit est local.

## Tableau d'écart

| Chez eux (Sprite Suite) | Aujourd'hui chez nous | Décision |
|---|---|---|
| **Lanceur** : une page « Choose a tool » à neuf cartes (titre, phrase, vignette animée, TUTORIAL + bouton d'ouverture, badge NEW) | Spritelab et Tilelab sont deux pages iframe séparées, entrées par le hub Game Assets ; le persona Pixel vit dans le Vectorlab | **À faire (léger)** : une carte-lanceur « Assets 2D » dans le hub avec Spritelab · Tilelab · Vectorlab Pixel · Cardforge, mêmes cartes ; pas de vidéos tutorielles (le guide PDF existe) |
| **Sprite Analyzer** : grille détectée (Auto-Detect, col × row), sélection de frames au glisser (Ctrl ajoute/retire, Maj de la dernière à ici, clic droit sur un segment), EVERY 1/2nd/3rd/4th, 31/36 compteur | Spritelab : filmstrip à cases à cocher après extraction (« ☑ Tout »), pas de grille sur une feuille existante, pas d'import de feuille | **À faire** : un onglet « Feuille existante » dans Spritelab — `grille_detecter(img)` pur (lignes/colonnes vides par projection alpha), sélection au glisser avec Ctrl/Maj, filtres « une sur n » |
| **Sections nommées** Start · Middle · End · Custom, loop / ping-pong / reverse, export « tags JSON » pour « your coding agent » | export PNG + JSON générique + pack Unity (frames, grille, fps) — pas de sections ni de boucles nommées | **À faire** : `sections` dans le manifest (nom, début, fin, mode loop/pingpong/reverse) + « Copier le JSON » ; c'est ce qui manque à Rippled pour lire une feuille sans code |
| **Combat** : hitboxes dessinées par frame, copier-coller Ctrl+C/V entre frames, inspecteur | rien | **À faire (lot séparé)** : calque « hitboxes » = rectangles par frame dans le manifest, dessin au glisser, C/V entre frames ; hors périmètre v1 de juillet, à rouvrir |
| **Playground** : fonds (damier, sombre, ciel, extérieur, cave, donjon, coucher, neige), vitesse, Invert L/R, grille, WASD pour déplacer le sprite, molette zoom, clic milieu pan | Spritelab : préviz ⏸, FPS, zoom 1–4×, fonds Damier / Noir / Blanc / Vert / Magenta | **Adapté** : ajouter deux fonds illustrés (extérieur, donjon, images libres du starter-catalog), Invert L/R et le déplacement WASD dans la préviz existante ; pas de moteur physique |
| **Auto Align** (les deux axes / gauche-droite / pieds) + nudges 1 px + crosshair — « for AI sheets that wobble » | `_fit_into_cell` avec ancrage Centré / Pieds (bas) côté backend, pas de nudge manuel | **À faire** : `aligner_frames(frames, mode)` pur côté client (centroïde ou bas de l'alpha) + nudges ↑←→↓ par frame avant assemblage ; les feuilles Seedance TREMBLENT aussi |
| **Pixel Snap** dans l'Analyzer : COLORS, PIXEL SIZE 1–4 / Auto, « Convert to pixels » | Spritelab : option pixel (taille cible, palettes PICO-8 / Game Boy / NES / Sweetie 16 / 1-bit, dither) au moment de générer ; `pixeliser` + `quantifier` purs dans mod-pixelart | **Conservé + exposé** : appliquer le pixel-art APRÈS coup sur une feuille déjà générée (bouton dans la préviz), avec « pixel size Auto » = détection du pas par autocorrélation (`pas_pixel_detecter` pur) |
| **Sprite Editor** : outils B/E/I/G/L/R/O/M/Q/W/V/H, pinceau rond/carré, pixel-perfect, miroir X/Y, primaire/secondaire (droit = secondaire, transparent = gomme), Shift = ligne depuis le dernier point, Alt = pipette | persona Pixel : crayon, pinceau, gomme, seau, ligne, rect, lasso, rect de sélection, baguette, cloner, palette, raccord, grille, pelure ; symétrie H/V (`symetrie`) ; pas de pinceau carré, pas de secondaire au clic droit, pas de Shift-ligne, pas d'Alt-pipette | **À faire** : couleur secondaire + clic droit, Maj = segment depuis le dernier point, Alt = pipette, pinceau carré, pixel-perfect (élaguer les coins en L) — tout dans `mod-pixelart` pur + `mod-pixelui` |
| **Ligne de temps** : frames × calques, play/pause Entrée, loop, frame cachée, FPS/MS, onion skin rouge/bleu, S/M/L, dupliquer / nouvelle / supprimer frame | cadres = images du calque « cadres » (ordre), `pelure` (précédent seulement, alpha 0,5), pas de grille frames × calques, lecture par « bande » | **À faire** : panneau « Ligne de temps » du persona Pixel — rangée de vignettes des cadres, lecture Entrée/loop, FPS, pelure rouge (précédent) ET bleue (suivant), dupliquer / vide / supprimer ; les calques restent ceux du document |
| **Palettes nommées** Classic 32 · Retro 16 · Arcade 16 · Handheld 4 · Grayscale 16 + « From sprite » + Alt-clic retire | PICO-8 · Game Boy · NES · Sweetie 16 · 1-bit + adaptative (Spritelab, Tilelab) ; palette du persona Pixel = extraite | **Conservé + unifié** : une seule liste de palettes partagée (module `palettes.js` : les cinq nôtres + Grayscale 16 + Handheld 4), utilisée par Spritelab, Tilelab et le persona Pixel ; pastilles cliquables droit = secondaire |
| **Sessions locales** autosave / Ctrl+S dans le navigateur | Spritelab : `savePrefs`/`restoreLast` (préférences + dernier résultat) ; Vectorlab : brouillon 30 s | **Conservé** |
| **Tileset Forge** : génération IA de feuilles de tuiles, Keyed / Not keyed, Corridor Key (matting GPU 2 cr), Job ID « for API agents » | Tilelab : une image de la Library → seamless (offset 50/50 + fondu, miroir 2×2) → pixel → score de raccord | **Écarté** pour la génération (dépendance payante ; nos générateurs existants suffisent) ; **Conservé** pour le seamless |
| **Tile Studio** : Detect tiles (découpe par les vides transparents), Auto-fit all (aimante les tuiles connectives à la cellule, étire les pentes), vues Sheet / Tileset / Tile ×9, tuile « déjà placée » en cyan, double-clic = seam check, export Aligned sheet .zip + JSON, Individual tiles .zip, Tileset PNG, PAD, nearest/smooth | Tilelab : une tuile à la fois, pavage 3×3 ; Vectorlab : `feuille_tuiles(tuiles, colonnes)` et `raccord_3x3` purs, grille hex/carrée/iso du lot C | **À faire (lot Tilelab 2)** : « Feuille de tuiles » — `tuiles_detecter(img)` pur (composantes connexes de l'alpha), grille de placement où l'on peint les tuiles pour tester les raccords, vue ×9 par double-clic, export feuille alignée + JSON + tuiles individuelles ; la découpe par vides existe déjà pour les frames (`_content_bbox`) |
| **Isometric Forge** : plateau 2:1 en diamant | Vectorlab : grille iso du lot C (`mod-grille`), tuiles hex du plateau | **Adapté** : la grille de placement du Tilelab 2 accepte carré et iso 2:1 en réutilisant `mod-grille` ; pas de génération |
| **True Pixel** : Edge Enhance, Outline / Dark Edges, Contrast, Brightness, résolution W × H avec Lock, Max Colors, échelle 1–16×, dither, Chroma Key / Corridor Key | `pixeliser`, `quantifier`, `niveaux`, `courbes`, `seuil`, `flou` dans mod-pixelart ; détourage chroma « fond uni, local » dans Spritelab | **Adapté** : ajouter « Contour sombre » (dilatation de l'alpha × noir) et « Accentuer les bords » (unsharp) purs ; échelle d'export 1–16× (nearest) ; pas de matting neural |
| **Quick Sprites** : styles 4 directions 48×48 / 32×32 / VFX, Send to Sprite Analyzer | Spritelab : durée, cadre, action ; starter-catalog | **Écarté** (génération payante) ; **Conservé** l'idée « Envoyer vers » déjà livrée le 28/08 (Spritelab ↔ Vectorlab) |
| **3D to 2D** : FBX/GLB/GLTF → clips + angles → feuille transparente | studio3d + `<model-viewer>` ; print3d lit le GLB ; pas de rendu de feuille | **À rouvrir plus tard** : rendu orthographique 4/8 angles d'un GLB animé vers une feuille (three.js vendorisé ? lourd) — hors lot |
| Coût « ESTIMATED n credits » avant tir | `updateCost()` de Spritelab affiche le coût avant Seedance | **Conservé** |

## Décisions tranchées (à valider)

**D1 — Une feuille existante entre dans Spritelab.** Aujourd'hui Spritelab
part d'une image ou d'une vidéo ; l'Analyzer montre que la moitié de la
valeur est dans l'INSPECTION d'une feuille déjà faite (grille, sélection,
sections, alignement). Un onglet « Feuille » avec `grille_detecter`,
sélection Ctrl/Maj, EVERY n, Auto Align + nudges, sections nommées et JSON
copiable. Modules purs bancables en node, aucune API.

**D2 — Le persona Pixel gagne la ligne de temps et les gestes du Sprite
Editor.** Secondaire au clic droit, Maj-ligne, Alt-pipette, pinceau carré,
pixel-perfect, pelure rouge/bleue, rangée de cadres avec lecture — le
Vectorlab devient l'éditeur de sprites, Spritelab reste la chaîne de
production. Contrats du relooking respectés (familles d'outils, onglets,
`VL.hints`, barre contextuelle).

**D3 — Tilelab 2 = feuille de tuiles.** Détection des tuiles par
l'alpha, grille de placement (carrée ou iso 2:1 via `mod-grille`) pour
peindre et tester les raccords, seam check ×9, export feuille alignée +
JSON + tuiles séparées. Aucune génération IA de tuiles (payant, écarté).

**D4 — Palettes unifiées.** Un module `palettes.js` partagé par les trois
surfaces, avec les six palettes nommées + adaptative ; c'est la dette la
plus visible entre Spritelab, Tilelab et le persona Pixel.

**D5 — Écartés** : génération IA de tuiles et de sprites rapides (crédits),
matting neural, 3D → 2D (lourd, à rouvrir en lot dédié).

## Répartition validée (19/09, utilisateur)

| Surface | Rôle | Ce qu'elle reçoit de la Suite |
|---|---|---|
| **Game Assets → Spritelab** | production (image → Seedance → frames → planche) et **inspection** d'une planche existante | Analyzer : grille, sélection, Auto Align, sections, JSON (lot 1) ; Playground adapté (lot 4) |
| **Game Assets → Tilelab** | tuile seamless et **feuille de tuiles** | Tile Studio : détection, grille de placement carrée / iso 2:1, seam check, exports (lot 3) |
| **Vectorlab → persona Pixel** | **édition** : retouche des sprites et des tuiles, y compris **iso** (grille `mod-grille` iso du lot C, cadres = images du calque « cadres »), et **rastérisation d'une image générée** (poser l'image de la Library → `pixeliser` / `quantifier` → calque raster éditable, journal `.pix<k>.png`) | Sprite Editor : ligne de temps, secondaire au clic droit, Maj-ligne, Alt-pipette, pinceau carré, pixel-perfect, pelure double (lot 2) |
| Library « Envoyer vers » | le pont entre les trois | conservé (28/08) |

Le lot 2 devra donc contenir, en plus des gestes du Sprite Editor : un mode
« tuile iso » du persona Pixel (cellule 2:1, symétrie sur la diagonale,
raccord ×9 en diamant) et une commande « Rastériser cette image »
(image générée → calque pixel à la taille cible, palette choisie).

## Lots proposés (ordre par valeur pour Rippled)

1. **Spritelab « Feuille »** (D1) — inspection, sections, JSON.
2. **Persona Pixel ligne de temps + gestes** (D2).
3. **Tilelab 2** (D3) + palettes unifiées (D4).
4. Playground et fonds illustrés, True Pixel « contour sombre » (adaptés).
