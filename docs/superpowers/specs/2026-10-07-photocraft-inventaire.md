# Photolab « reproduire photocraft » — inventaire de photocraft v0.3.0 (07/10/2026)

> Relevé fait en LECTURE SEULE, t135 (skill `inventaire-site`), en deux volets :
>
> - **À l'écran** : la version web officielle `photocraft-web-0.3.0.zip` (release GitHub storytold/photocraft v0.3.0,
>   11 119 388 o, sha256 `1825b2be…3f93d06` vérifié contre `SHA256SUMS.txt` de la release ; téléchargement autorisé
>   par l'utilisateur le 07/10), servie en local sur 127.0.0.1:8805 et ouverte dans le **Chrome de l'utilisateur**
>   (fenêtre 1600 × 1000, vue 1524 × 784, zoom 100 %). Le volet intégré de l'app (418 px de large) tassait
>   l'interface egui : il n'a servi qu'à vérifier le démarrage. Aucun compte, aucune donnée de l'utilisateur.
>   Document de travail : « Untitled-1 », préréglage HDTV 1080p, un calque de réglage Courbes ajouté.
> - **Dans le code** : les sources v0.3.0 (tarball de la release, lues sans compiler — pas de `cargo` ici) ; les
>   listes « entrée par entrée » (653 entrées de menus, 45 outils, 19 onglets, 16 réglages, 75 filtres, 27 modes,
>   raccourcis, gestes, formats, thèmes) viennent du code avec leur `fichier:ligne`, partie B ci-dessous.
>
> Touché et remis : le thème a été basculé trois fois (bouton soleil) pour relever les variantes, puis remis sur
> « Pro (Medium Gray) » ; un tracé au pinceau synthétique (glisser sans étapes intermédiaires) n'a RIEN peint —
> le geste de peinture n'est donc pas relevé à l'écran (voir B §8 pour sa description dans le code). Le document
> n'a pas été enregistré ; les préférences de photocraft vivent dans le localStorage de 127.0.0.1:8805 seulement.
> État final : identique au départ, onglet Chrome fermé, serveur local arrêté.
>
> Captures : `2026-10-07-photocraft-captures/` (11 images, 01 à 11, citées ci-dessous).

# Partie A — relevé à l'écran

## A1. Structure des zones (thème par défaut « Pro (Medium Gray) », vue 1524 × 784)

| Zone | Mesure (px écran) | Contenu relevé |
|---|---|---|
| Barre de menus / titre | ≈ 30 de haut (code : 32) | File Edit Image Layer Type Select Filter View Window Help à gauche ; titre du document centré (« PhotoCraft » sans document, « Untitled-1 • » modifié) ; à droite : Discord, bouton thème (soleil), loupe (recherche ⌘K), sélecteur d'espace de travail « Essentials ». Capture 01 |
| Barre d'options | ≈ 35 (code : 36) | Maison ; outil courant + flèche (préréglages) ; pour le Pinceau : pastille de taille (20), réglages pinceau, Mode Normal, Opacity 100 %, pression→opacité, Flow 100 %, aérographe, Smoothing 10 %, réglages de lissage, symétrie / pression→taille. Capture 01 |
| Onglets de document | ≈ 25 | « × Untitled-1 @ 59.7% (RGB/8) » ; le titre suit le calque actif : « (Curves 1, RGB/8)* ». Captures 03, 08 |
| Barre d'outils (gauche) | ≈ 68 de large, 2 colonnes de 32 (code : 40 en une colonne repliable « » ») | 20 emplacements groupés en 5 sections (séparateurs), petit triangle en bas à droite = flyout ; pastilles premier plan / arrière-plan ; inverser / défaut ; masque rapide ; mode d'écran. Capture 03 |
| Rail d'icônes (droite) | ≈ 34 de large | 5 icônes (réglages, navigateur, couleur, calques, historique) qui ouvrent des panneaux repliés. Capture 03 |
| Colonne de panneaux | ≈ 278 de large | 3 groupes empilés : Color │ Swatches │ Gradients │ Patterns — Properties │ Adjustments — Layers │ Channels │ Paths ; menu « ≡ » par groupe. Capture 03 |
| Canevas | le reste | fond #282828 (code), document centré, ombre nulle |
| Barre d'état | ≈ 22 (code : 24) | champ zoom « 59.7 % », « 1920 px x 1080 px (72 ppi) », chevron d'infos. Capture 03 |

## A2. Écran d'accueil (sans document) — capture 01

« PhotoCraft open source » ; « Create a new document or open an existing file. » ; boutons pilule « New document…
Ctrl+N » (plein, bleu) et « Open… Ctrl+O » (contour) ; « Drop an image or PSD anywhere to open it. » ; « Join us on
Discord » ; liens « PhotoCraft website · GitHub · ArtCraft ». Panneaux à vide : « No properties », « No document ».

## A3. Dialogue New Document — capture 02

Onglets Recent │ Photo │ Print │ Art & Illustration │ Web │ Mobile │ Film & Video (souligné = actif). « BLANK DOCUMENT
PRESETS (2) » en cartes (icône de format, nom, sous-titre « 7 x 5 in @ 300 ppi ») — Recent montre « Default Photoshop
Size » et « HDTV 1080p ». Colonne « PRESET DETAILS » : nom (Untitled-1), Width 1920 + unité (Pixels), Height 1080,
Orientation (portrait/paysage, paysage actif), Resolution 72 + Pixels/Inch, Color Mode RGB Color + 8 bit,
Background Contents White. Boutons « Close » (contour) / « Create » (plein bleu). Les 33 préréglages des 7 catégories
sont en B §5.

## A4. Espace de travail avec document — captures 03, 08

- **Properties** (document) : « Document », section repliable « Canvas » : W 1920 px, H 1080 px, X 0 px, Y 0 px,
  lien de proportion, orientation.
- **Layers** : filtre « Kind » + 5 filtres d'icône (pixel, réglage, texte, forme, objet dynamique) ; mode « Normal »,
  Opacity 100 %, « Lock: » 5 verrous (pixels transparents, pixels, position, plan de travail, tout), Fill 100 % ;
  ligne : œil, vignette (cadre de sélection aux coins), nom, cadenas pour Background ; pied de 7 boutons : lier, fx,
  masque, réglage/remplissage, groupe, nouveau calque, corbeille.
- **Adjustments** (capture 07) : « Add an adjustment », grille 8 × 2 de 16 icônes.
- Calque de réglage ajouté (capture 08) : ligne « Curves 1 » avec vignette de réglage ; Properties devient
  « Curves 1 — Curves », Channel RGB, graphe de courbe avec dégradé d'entrée.

## A5. Menus — captures 04, 05

Menus déroulants gris (≈ #5a5a5a), libellé à gauche, raccourci aligné à droite en gris clair (« Ctrl+N »,
« Ctrl+Alt+Shift+O »), entrées indisponibles grisées (New from Clipboard, Open As…, Save a Copy…, Revert, Place…,
Package…), sous-menus marqués « ▸ », séparateurs fins ; menus longs à défilement (flèches ▲ ▼ en haut et en bas du
menu File). Survol = bande bleue pleine (Blur ▸). Sous-menu Blur : Average, Blur, Blur More, Box Blur…, Gaussian
Blur…, Lens Blur…, Motion Blur…, Radial Blur…, Shape Blur…, Smart Blur…, Surface Blur…. Toutes les entrées : B §1.

## A6. Dialogue de filtre — capture 06

« Gaussian Blur » : titre en gras, Radius (champ numérique « 1 px » + curseur), case « Preview » (cochée, bleue),
« Cancel » (contour) / « OK » (plein bleu). Fenêtre modale sans voile, ombre portée, coins ≈ 6 px.

## A7. Flyout d'outil — capture 09

Clic droit (ou appui long > 0,35 s) sur un emplacement : liste « ▪ Rectangular Marquee Tool   M » / « Elliptical
Marquee Tool   M » — puce sur l'outil actif, icône, nom, lettre à droite.

## A8. Thèmes — captures 10, 11

Le bouton soleil fait défiler les thèmes (code : 5 thèmes, B §7). Relevés à l'écran :
1. **Pro (Medium Gray)** — défaut, gris moyen, accent bleu #378EF0 (code), interface dense.
2. **Sombre à accent violet** — fond noir bleuté, panneau Properties FLOTTANT au-dessus du canevas, interrupteurs
   (« Pressure for Size », « Adjustment visible », « Clip to layer below »), barre d'état enrichie (« RGB Color · 8 bit
   · 1920 × 1080 px · 2 layers · Fit »), nuancier en grille. Capture 10.
3. **Clair** — fond gris clair chaud, accent bleu marine, mêmes dispositions aérées que 2 : barre d'outils une
   colonne plus large, boutons carrés, champs à bord fin. Capture 11.

Le thème change aussi la DISPOSITION (Properties flottant, barre d'options plus riche) : ce n'est pas qu'une palette.

## A9. Non relevé à l'écran (et pourquoi)

- Peinture, sélections, transformation, texte au canevas : les glisser synthétiques de l'outil de pilotage n'ont
  pas d'étapes intermédiaires (rien n'a été peint) — décrits dans le code, B §8.
- Couleurs exactes : le canevas egui est en WebGPU, pas de lecture de pixels par le DOM ; valeurs hex prises dans
  `theme.rs` (B §7).
- Les 653 entrées de menus, 45 outils et 75 filtres n'ont pas été ouverts un par un : la liste du code est
  exhaustive et plus sûre (B §1-§4).

# Partie B — inventaire tiré du code de photocraft v0.3.0 (Rust, egui)

Relevé factuel extrait du **code source** (`scratchpad/photocraft`, version `0.3.0` d'après `Cargo.toml:7`), le 07/10/2026, en lecture seule. Aucune compilation possible (pas de `cargo`) : tout est lu ; les décomptes globaux viennent d'une extraction statique par script ; « (déduit) » marque une conclusion qui n'est pas un littéral du code. Chaque section cite ses sources `fichier:ligne` (chemins relatifs à `crates/ui-egui/src/` sauf mention).

## Résumé (10 lignes)
1. **Menus** : 10 menus (File…Help), **653 entrées** et 140 séparateurs, dont File 54, Edit 75, Image 61, Layer 168, Type 45, Select 25, Filter 76, View 74, Window 68, Help 7 ; arbre tiré de `menu_catalog.rs` (ordre Photoshop) (765 lignes dont séparateurs) + 50 commandes `UI_COMMANDS` + ajouts du registre.
2. **Outils** : 45 outils en 20 emplacements (5 sections), 19 touches à une lettre (Blur/Sharpen/Smudge sans touche), 112 icônes SVG Lucide ; barre d'options propre à ~30 cas d'outil.
3. **Panneaux** : dock de 6 groupes / 19 onglets (Color, Swatches, Gradients, Patterns │ Properties, Adjustments │ Character, Paragraph │ Navigator, Histogram, Info │ History, Actions, Layer Comps │ Layers, Channels, Paths) + Brush Settings flottant (13 sections) + rail de 5 icônes.
4. **Réglages** : 16 calques de réglage (×2 commandes : calque + destructif) + 6 réglages destructifs seuls (Desaturate, Equalize, Shadows/Highlights, Replace Color, Match Color, HDR Toning).
5. **Filtres** : 75 commandes `filter.*` (+ `plugin.install`) dans le menu Filter, en 11 sous-menus + racine (Blur 11, Blur Gallery 5, Distort 9, Noise 5, Pixelate 7, Render 8, Sharpen 5, Stylize 9, Video 2, Other 6, Plug-ins 1, racine 8).
6. **Fusion / styles** : 27 modes de fusion (+ Pass Through pour les groupes), liste à plat sans séparateurs ; 10 styles de calque + Blending Options.
7. **Dialogues** : New Document (7 catégories, 33 préréglages), Image/Canvas Size (7 unités, 5 rééchantillonnages, 9 ancres), Export As (5 formats), Save for Web (5 formats, 12 préréglages), Préférences (18 sections, ~60 réglages masqués).
8. **Thème** : 5 thèmes, défaut **Pro (Medium Gray)** (chrome #535353, canevas #282828, accent #378EF0) ; Inter + JetBrains Mono ; barres 32/36/24 px en Pro.
9. **Registre** : **684 ids extraits statiquement** (README : « 500+ ») — layer.* en tête ; liste exacte par `photocraft-cli commands --json`.
10. **Localisation** : 10 langues (fr.tsv : 2465 entrées), clés = texte anglais + `@id` par commande + `@plural` ; toutes les entrées de menu ont une traduction française.

## Sommaire
1. Menus de la barre · 2. Outils · 3. Panneaux · 4. Réglages, filtres, modes de fusion, styles · 5. Dialogues · 6. Formats lus/écrits · 7. Thème et design · 8. Gestes, modificateurs, barre d'état · 9. Registre des commandes · 10. Localisation

## 1. Menus de la barre

Sources : `menus.rs` (barre, `TOP_MENUS` l.9, `UI_COMMANDS` l.12-63, `menu_items` l.617-722, rendu l.739-900) et `menu_catalog.rs:6-772` (arbre Photoshop complet : chemin, libellé ou « --- », raccourci, id). Construction (lu, `menus.rs:617-722`) :
1. le catalogue dans l'ordre (sous-menu placé à la position de son premier enfant, `menus.rs:837-890`) ;
2. puis, pour chaque commande de `UI_COMMANDS` puis du registre moteur ayant un `menu`, si ni l'id ni (chemin + libellé sans « … ») n'existent déjà : insertion après le dernier élément du même menu de premier niveau (`file.newFromClipboard` après `file.new`, `PLACE_AFTER` l.615) ;
3. extensions WebAssembly installées (Filter › Plug-ins) ; File › Open Recent dynamique après « Open As… » ; séparateur avant System Info / About dans Help ;
4. préférences : raccourcis personnalisés, éléments masqués et couleurs (Edit › Menus).

Rendu : séparateurs en tête/fin ou doublés supprimés (l.842-848) ; coche « ✔ » pour les éléments à état (l.851-853) ; infobulles « Integer » / « Floating point » sur Image › Mode › 8/16/32 bits (l.865-868) ; ⌥-clic sur Merge Down/Merge Layers/Merge Visible → Stamp (l.902-907) ; largeur min 220 ; menus qui défilent si trop hauts (`menu_nav.rs`) ; menu « (coming soon) » si vide. Raccourcis en notation `Cmd` (= Ctrl sous Windows/Linux, affichage par `shortcuts::pretty`). La colonne « Où l'id est implémenté » est une lecture statique : `moteur` (registre), `UI_COMMANDS`, `shell (alias)` (window.panel.*, window.workspace.*, view.proofSetup.*), `shell UI` (id cité dans un gestionnaire de `crates/ui-egui`). La traduction FR vient de `fr.tsv` (entrée `@id` sinon libellé).

Le tableau émule `menu_items` (script) ; ordre exact pour le catalogue ; pour les ~20 ajouts hors catalogue, l'ordre suit l'ordre reconstitué du registre (déduit). Les noms de sous-menus sont suivis de leur traduction.

### 1.1 File — « Fichier » (54 entrées, 19 séparateurs)

| # | Chemin (sous-menu) | Libellé EN | Libellé FR (fr.tsv) | Raccourci | id de commande | Où l'id est implémenté (lecture statique) | Source |
|---|---|---|---|---|---|---|---|
| 1 | — | New… | Nouveau… | Cmd+N | `file.new` | moteur | menu_catalog.rs:7 |
| 2 | — | New from Clipboard | Créer depuis le presse-papiers |  | `file.newFromClipboard` | moteur | edit_cmds.rs:488 |
| 3 | — | Open… | Ouvrir… | Cmd+O | `file.open` | UI_COMMANDS | menu_catalog.rs:8 |
| 4 | — | Open As… | Ouvrir en tant que… | Cmd+Alt+Shift+O | `file.openAs` | moteur | menu_catalog.rs:9 |
| 5 | Open Recent (Ouvrir un fichier récent) | (fichiers récents, dynamiques) |  |  | `file.openRecent.N` | shell (dynamique) | menus.rs:672-694 |
| | Open Recent | ——— séparateur ——— | | | | | menus.rs:683 |
| 6 | Open Recent (Ouvrir un fichier récent) | Clear Recent Files | Effacer la liste des fichiers récents |  | `file.clearRecent` | shell (dynamique) | menus.rs:685-693 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:10 |
| 7 | — | Close | Fermer | Cmd+W | `file.close` | moteur | menu_catalog.rs:11 |
| 8 | — | Close All | Tout fermer | Cmd+Alt+W | `file.closeAll` | moteur | menu_catalog.rs:12 |
| 9 | — | Close Others | Fermer les autres | Cmd+Alt+P | `file.closeOthers` | moteur | menu_catalog.rs:13 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:14 |
| 10 | — | Save | Enregistrer | Cmd+S | `file.save` | UI_COMMANDS | menu_catalog.rs:15 |
| 11 | — | Save As… | Enregistrer sous… | Cmd+Shift+S | `file.saveAs` | UI_COMMANDS | menu_catalog.rs:16 |
| 12 | — | Save a Copy… | Enregistrer une copie… | Cmd+Alt+S | `file.saveACopy` | moteur | menu_catalog.rs:17 |
| 13 | — | Revert | Revenir à la version enregistrée | F12 | `file.revert` | moteur | menu_catalog.rs:18 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:19 |
| 14 | Export (Exporter) | Quick Export as PNG | Exportation rapide au format PNG |  | `file.export.quickExportAsPng` | UI_COMMANDS | menu_catalog.rs:20 |
| 15 | Export (Exporter) | Export As… | Exporter sous… | Cmd+Alt+Shift+W | `file.export.exportAs` | UI_COMMANDS | menu_catalog.rs:21 |
| 16 | Export (Exporter) | Export Preferences… | Préférences d'exportation… |  | `file.export.exportPreferences` | moteur | menu_catalog.rs:22 |
| | Export | ——— séparateur ——— | | | | | menu_catalog.rs:23 |
| 17 | Export (Exporter) | Save for Web (Legacy)… | Enregistrer pour le Web (ancien)… | Cmd+Alt+Shift+S | `file.export.saveForWebLegacy` | moteur | menu_catalog.rs:24 |
| | Export | ——— séparateur ——— | | | | | menu_catalog.rs:25 |
| 18 | Export (Exporter) | Artboards to Files… | Plans de travail en fichiers… |  | `file.export.artboardsToFiles` | moteur | menu_catalog.rs:26 |
| 19 | Export (Exporter) | Artboards to PDF… | Plans de travail en PDF… |  | `file.export.artboardsToPdf` | moteur | menu_catalog.rs:27 |
| 20 | Export (Exporter) | Layers to Files… | Calques en fichiers… |  | `file.export.layersToFiles` | moteur | menu_catalog.rs:28 |
| 21 | Export (Exporter) | Layer Comps to Files… | Compositions de calques en fichiers… |  | `file.export.layerCompsToFiles` | moteur | menu_catalog.rs:29 |
| | Export | ——— séparateur ——— | | | | | menu_catalog.rs:30 |
| 22 | Export (Exporter) | Color Lookup Tables… | Tables de correspondance des couleurs… |  | `file.export.colorLookupTables` | moteur | menu_catalog.rs:31 |
| 23 | Export (Exporter) | Data Sets as Files… | Jeux de données en fichiers… |  | `file.export.dataSetsAsFiles` | moteur | menu_catalog.rs:32 |
| 24 | Export (Exporter) | Paths to Illustrator… | Tracés vers Illustrator… |  | `file.export.pathsToIllustrator` | moteur | menu_catalog.rs:33 |
| 25 | Export (Exporter) | Render Video… | Rendu vidéo… |  | `file.export.renderVideo` | moteur | menu_catalog.rs:34 |
| 26 | Generate (Générer) | Image Assets | Ressources d'image |  | `file.generate.imageAssets` | moteur | menu_catalog.rs:35 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:36 |
| 27 | — | Place Embedded… | Placer incorporé… |  | `file.placeEmbedded` | moteur | menu_catalog.rs:37 |
| 28 | — | Place Linked… | Placer lié… |  | `file.placeLinked` | moteur | menu_catalog.rs:38 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:39 |
| 29 | — | Package… | Rassembler… |  | `file.package` | moteur | menu_catalog.rs:40 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:41 |
| 30 | Automate (Automatisation) | Batch… | Traitement par lots… |  | `file.automate.batch` | moteur | menu_catalog.rs:42 |
| 31 | Automate (Automatisation) | Create Droplet… | Créer un droplet… |  | `file.automate.createDroplet` | moteur | menu_catalog.rs:43 |
| | Automate | ——— séparateur ——— | | | | | menu_catalog.rs:44 |
| 32 | Automate (Automatisation) | Crop and Straighten Photos | Recadrer et redresser les photos |  | `file.automate.cropAndStraightenPhotos` | moteur | menu_catalog.rs:45 |
| 33 | Automate (Automatisation) | Contact Sheet II… | Planche contact II… |  | `file.automate.contactSheetII` | moteur | menu_catalog.rs:46 |
| 34 | Automate (Automatisation) | Conditional Mode Change… | Changement de mode conditionnel… |  | `file.automate.conditionalModeChange` | moteur | menu_catalog.rs:47 |
| 35 | Automate (Automatisation) | Fit Image… | Adapter l'image… |  | `file.automate.fitImage` | moteur | menu_catalog.rs:48 |
| 36 | Automate (Automatisation) | Lens Correction… | Correction de l'objectif… |  | `file.automate.lensCorrection` | moteur | menu_catalog.rs:49 |
| | Automate | ——— séparateur ——— | | | | | menu_catalog.rs:50 |
| 37 | Automate (Automatisation) | Merge to HDR Pro… | Fusionner en HDR Pro… |  | `file.automate.mergeToHdrPro` | moteur | menu_catalog.rs:51 |
| 38 | Automate (Automatisation) | Photomerge… | Photomerge… |  | `file.automate.photomerge` | moteur | menu_catalog.rs:52 |
| 39 | Scripts | Image Processor… | Processeur d'images… |  | `file.scripts.imageProcessor` | moteur | menu_catalog.rs:53 |
| | Scripts | ——— séparateur ——— | | | | | menu_catalog.rs:54 |
| 40 | Scripts | Delete All Empty Layers | Supprimer tous les calques vides |  | `file.scripts.deleteAllEmptyLayers` | moteur | menu_catalog.rs:55 |
| 41 | Scripts | Flatten All Layer Effects | Aplatir tous les effets de calque |  | `file.scripts.flattenAllLayerEffects` | moteur | menu_catalog.rs:56 |
| 42 | Scripts | Flatten All Masks | Aplatir tous les masques |  | `file.scripts.flattenAllMasks` | moteur | menu_catalog.rs:57 |
| | Scripts | ——— séparateur ——— | | | | | menu_catalog.rs:58 |
| 43 | Scripts | Script Events Manager… | Gestionnaire d'événements de script… |  | `file.scripts.scriptEventsManager` | moteur | menu_catalog.rs:59 |
| | Scripts | ——— séparateur ——— | | | | | menu_catalog.rs:60 |
| 44 | Scripts | Load Files into Stack… | Charger des fichiers dans une pile… |  | `file.scripts.loadFilesIntoStack` | moteur | menu_catalog.rs:61 |
| 45 | Scripts | Statistics… | Statistiques… |  | `file.scripts.statistics` | moteur | menu_catalog.rs:62 |
| | Scripts | ——— séparateur ——— | | | | | menu_catalog.rs:63 |
| 46 | Scripts | Browse… | Parcourir… |  | `file.scripts.browse` | moteur | menu_catalog.rs:64 |
| 47 | Import (Importer) | Variable Data Sets… | Jeux de données variables… |  | `file.import.variableDataSets` | moteur | menu_catalog.rs:65 |
| 48 | Import (Importer) | Video Frames to Layers… | Images vidéo dans des calques… |  | `file.import.videoFramesToLayers` | moteur | menu_catalog.rs:66 |
| 49 | Import (Importer) | Notes… | Notes… |  | `file.import.notes` | moteur | menu_catalog.rs:67 |
| 50 | Import (Importer) | WIA Support… | Prise en charge de WIA… |  | `file.import.wiaSupport` | moteur | menu_catalog.rs:68 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:69 |
| 51 | — | File Info… | Informations sur le fichier… | Cmd+Alt+Shift+I | `file.fileInfo` | moteur | menu_catalog.rs:70 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:71 |
| 52 | — | Print… | Imprimer… | Cmd+P | `file.print` | moteur | menu_catalog.rs:72 |
| 53 | — | Print One Copy | Imprimer un exemplaire | Cmd+Alt+Shift+P | `file.printOneCopy` | moteur | menu_catalog.rs:73 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:74 |
| 54 | — | Exit | Quitter | Cmd+Q | `file.exit` | UI_COMMANDS | menu_catalog.rs:75 |

### 1.2 Edit — « Édition » (75 entrées, 17 séparateurs)

| # | Chemin (sous-menu) | Libellé EN | Libellé FR (fr.tsv) | Raccourci | id de commande | Où l'id est implémenté (lecture statique) | Source |
|---|---|---|---|---|---|---|---|
| 1 | — | Undo | Annuler |  | `edit.undo` | moteur | menu_catalog.rs:76 |
| 2 | — | Redo | Rétablir |  | `edit.redo` | moteur | menu_catalog.rs:77 |
| 3 | — | Toggle Last State | Basculer sur le dernier état | Cmd+Alt+Z | `edit.toggleLastState` | moteur | menu_catalog.rs:78 |
| 4 | — | Fade… | Estomper… | Cmd+Shift+F | `edit.fade` | moteur | menu_catalog.rs:79 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:80 |
| 5 | — | Cut | Couper |  | `edit.cut` | moteur | menu_catalog.rs:81 |
| 6 | — | Copy | Copier |  | `edit.copy` | moteur | menu_catalog.rs:82 |
| 7 | — | Copy Merged | Copier les calques fusionnés | Cmd+Shift+C | `edit.copyMerged` | moteur | menu_catalog.rs:83 |
| 8 | — | Paste | Coller |  | `edit.paste` | moteur | menu_catalog.rs:84 |
| 9 | Paste Special (Collage spécial) | Paste in Place | Coller sur place | Cmd+Shift+V | `edit.pasteSpecial.pasteInPlace` | moteur | menu_catalog.rs:85 |
| 10 | Paste Special (Collage spécial) | Paste Into | Coller dans la sélection | Cmd+Alt+Shift+V | `edit.pasteSpecial.pasteInto` | moteur | menu_catalog.rs:86 |
| 11 | Paste Special (Collage spécial) | Paste Outside | Coller hors de la sélection |  | `edit.pasteSpecial.pasteOutside` | moteur | menu_catalog.rs:87 |
| 12 | — | Clear | Effacer |  | `edit.clear` | moteur | menu_catalog.rs:88 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:89 |
| 13 | — | Search… | Rechercher… | Cmd+K | `edit.search` | UI_COMMANDS | menu_catalog.rs:90 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:91 |
| 14 | — | Check Spelling… | Vérifier l'orthographe… |  | `edit.checkSpelling` | moteur | menu_catalog.rs:92 |
| 15 | — | Find and Replace Text… | Rechercher et remplacer du texte… |  | `edit.findAndReplaceText` | moteur | menu_catalog.rs:93 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:94 |
| 16 | — | Fill… | Remplir… | Shift+F5 | `edit.fill` | moteur | menu_catalog.rs:95 |
| 17 | — | Stroke… | Contourner… |  | `edit.stroke` | moteur | menu_catalog.rs:96 |
| 18 | — | Content-Aware Fill… | Remplissage d'après le contenu… |  | `edit.contentAwareFill` | moteur | menu_catalog.rs:97 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:98 |
| 19 | — | Content-Aware Scale | Mise à l'échelle d'après le contenu | Cmd+Alt+Shift+C | `edit.contentAwareScale` | moteur | menu_catalog.rs:99 |
| 20 | — | Puppet Warp | Déformation par épingles |  | `edit.puppetWarp` | moteur | menu_catalog.rs:100 |
| 21 | — | Perspective Warp | Déformation de la perspective |  | `edit.perspectiveWarp` | moteur | menu_catalog.rs:101 |
| 22 | — | Free Transform | Transformation libre | Cmd+T | `edit.freeTransform` | UI_COMMANDS | menu_catalog.rs:102 |
| 23 | Transform (Transformation) | Again | Répéter | Cmd+Shift+T | `edit.transform.again` | moteur | menu_catalog.rs:103 |
| | Transform | ——— séparateur ——— | | | | | menu_catalog.rs:104 |
| 24 | Transform (Transformation) | Scale | Mise à l'échelle |  | `edit.transform.scale` | UI_COMMANDS | menu_catalog.rs:105 |
| 25 | Transform (Transformation) | Rotate | Rotation |  | `edit.transform.rotate` | UI_COMMANDS | menu_catalog.rs:106 |
| 26 | Transform (Transformation) | Skew | Inclinaison |  | `edit.transform.skew` | UI_COMMANDS | menu_catalog.rs:107 |
| 27 | Transform (Transformation) | Distort | Déformation |  | `edit.transform.distort` | UI_COMMANDS | menu_catalog.rs:108 |
| 28 | Transform (Transformation) | Perspective | Perspective |  | `edit.transform.perspective` | UI_COMMANDS | menu_catalog.rs:109 |
| 29 | Transform (Transformation) | Warp | Déformer |  | `edit.transform.warp` | moteur | menu_catalog.rs:110 |
| | Transform | ——— séparateur ——— | | | | | menu_catalog.rs:111 |
| 30 | Transform (Transformation) | Split Warp Horizontally | Diviser la déformation horizontalement |  | `edit.transform.splitWarpHorizontally` | moteur | menu_catalog.rs:112 |
| 31 | Transform (Transformation) | Split Warp Vertically | Diviser la déformation verticalement |  | `edit.transform.splitWarpVertically` | moteur | menu_catalog.rs:113 |
| 32 | Transform (Transformation) | Split Warp Crosswise | Diviser la déformation en croix |  | `edit.transform.splitWarpCrosswise` | moteur | menu_catalog.rs:114 |
| 33 | Transform (Transformation) | Remove Warp Split | Supprimer la division de la déformation |  | `edit.transform.removeWarpSplit` | moteur | menu_catalog.rs:115 |
| | Transform | ——— séparateur ——— | | | | | menu_catalog.rs:116 |
| 34 | Transform (Transformation) | Rotate 180° | Rotation de 180° |  | `edit.transform.rotate180` | moteur | menu_catalog.rs:117 |
| 35 | Transform (Transformation) | Rotate 90° Clockwise | Rotation de 90° horaire |  | `edit.transform.rotate90Cw` | moteur | menu_catalog.rs:118 |
| 36 | Transform (Transformation) | Rotate 90° Counter Clockwise | Rotation de 90° antihoraire |  | `edit.transform.rotate90Ccw` | moteur | menu_catalog.rs:119 |
| | Transform | ——— séparateur ——— | | | | | menu_catalog.rs:120 |
| 37 | Transform (Transformation) | Flip Horizontal | Symétrie horizontale |  | `edit.transform.flipHorizontal` | moteur | menu_catalog.rs:121 |
| 38 | Transform (Transformation) | Flip Vertical | Symétrie verticale |  | `edit.transform.flipVertical` | moteur | menu_catalog.rs:122 |
| 39 | — | Auto-Align Layers… | Alignement automatique des calques… |  | `edit.autoAlignLayers` | moteur | menu_catalog.rs:123 |
| 40 | — | Auto-Blend Layers… | Fusion automatique des calques… |  | `edit.autoBlendLayers` | moteur | menu_catalog.rs:124 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:125 |
| 41 | — | Define Brush Preset… | Définir un préréglage de pinceau… |  | `edit.defineBrushPreset` | moteur | menu_catalog.rs:126 |
| 42 | — | Define Pattern… | Définir un motif… |  | `edit.definePattern` | moteur | menu_catalog.rs:127 |
| 43 | — | Define Custom Shape… | Définir une forme personnalisée… |  | `edit.defineCustomShape` | moteur | menu_catalog.rs:128 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:129 |
| 44 | Purge (Purger) | Undo | Historique d'annulation |  | `edit.purge.undo` | moteur | menu_catalog.rs:130 |
| 45 | Purge (Purger) | Clipboard | Presse-papiers |  | `edit.purge.clipboard` | moteur | menu_catalog.rs:131 |
| 46 | Purge (Purger) | Histories | Historiques |  | `edit.purge.histories` | moteur | menu_catalog.rs:132 |
| 47 | Purge (Purger) | Video Cache | Cache vidéo |  | `edit.purge.videoCache` | moteur | menu_catalog.rs:133 |
| | Purge | ——— séparateur ——— | | | | | menu_catalog.rs:134 |
| 48 | Purge (Purger) | All | Tout |  | `edit.purge.all` | moteur | menu_catalog.rs:135 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:136 |
| 49 | Presets (Préréglages) | Preset Manager… | Gestionnaire de préréglages… |  | `edit.presets.presetManager` | moteur | menu_catalog.rs:137 |
| | Presets | ——— séparateur ——— | | | | | menu_catalog.rs:138 |
| 50 | Presets (Préréglages) | Migrate Presets | Migrer les préréglages |  | `edit.presets.migratePresets` | moteur | menu_catalog.rs:139 |
| 51 | Presets (Préréglages) | Export/Import Presets… | Exporter/importer des préréglages… |  | `edit.presets.exportImportPresets` | moteur | menu_catalog.rs:140 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:141 |
| 52 | — | Color Settings… | Paramètres de couleur… | Cmd+Shift+K | `edit.colorSettings` | moteur | menu_catalog.rs:142 |
| 53 | — | Assign Profile… | Attribuer un profil… |  | `edit.assignProfile` | moteur | menu_catalog.rs:143 |
| 54 | — | Convert to Profile… | Convertir en profil… |  | `edit.convertToProfile` | moteur | menu_catalog.rs:144 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:145 |
| 55 | — | Keyboard Shortcuts… | Raccourcis clavier… | Cmd+Alt+Shift+K | `edit.keyboardShortcuts` | moteur | menu_catalog.rs:146 |
| 56 | — | Menus… | Menus… | Cmd+Alt+Shift+M | `edit.menus` | moteur | menu_catalog.rs:147 |
| 57 | — | Toolbar… | Barre d'outils… |  | `edit.toolbar` | moteur | menu_catalog.rs:148 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:149 |
| 58 | Preferences (Préférences) | Settings… | Paramètres… |  | `edit.preferences.general` | moteur | menu_catalog.rs:150 |
| 59 | Preferences (Préférences) | AI Integrations… | Intégrations d'IA… |  | `edit.preferences.integrations` | moteur | menu_catalog.rs:151 |
| 60 | Preferences (Préférences) | Interface… | Interface… |  | `edit.preferences.interface` | moteur | menu_catalog.rs:152 |
| 61 | Preferences (Préférences) | Workspace… | Espace de travail… |  | `edit.preferences.workspace` | moteur | menu_catalog.rs:153 |
| 62 | Preferences (Préférences) | Tools… | Outils… |  | `edit.preferences.tools` | moteur | menu_catalog.rs:154 |
| 63 | Preferences (Préférences) | History Log… | Journal de l'historique… |  | `edit.preferences.historyLog` | moteur | menu_catalog.rs:155 |
| 64 | Preferences (Préférences) | File Handling… | Gestion des fichiers… |  | `edit.preferences.fileHandling` | moteur | menu_catalog.rs:156 |
| 65 | Preferences (Préférences) | Export… | Exportation… |  | `edit.preferences.export` | moteur | menu_catalog.rs:157 |
| 66 | Preferences (Préférences) | Performance… | Performances… |  | `edit.preferences.performance` | moteur | menu_catalog.rs:158 |
| 67 | Preferences (Préférences) | Scratch Disks… | Disques de travail… |  | `edit.preferences.scratchDisks` | moteur | menu_catalog.rs:159 |
| 68 | Preferences (Préférences) | Cursors… | Curseurs… |  | `edit.preferences.cursors` | moteur | menu_catalog.rs:160 |
| 69 | Preferences (Préférences) | Transparency & Gamut… | Transparence et gamut… |  | `edit.preferences.transparencyAndGamut` | moteur | menu_catalog.rs:161 |
| 70 | Preferences (Préférences) | Units & Rulers… | Unités et règles… |  | `edit.preferences.unitsAndRulers` | moteur | menu_catalog.rs:162 |
| 71 | Preferences (Préférences) | Guides, Grid & Slices… | Repères, grille et tranches… |  | `edit.preferences.guidesGridAndSlices` | moteur | menu_catalog.rs:163 |
| 72 | Preferences (Préférences) | Plug-ins… | Extensions… |  | `edit.preferences.plugIns` | moteur | menu_catalog.rs:164 |
| 73 | Preferences (Préférences) | Type… | Texte… |  | `edit.preferences.type` | moteur | menu_catalog.rs:165 |
| 74 | Preferences (Préférences) | Enhanced Controls… | Commandes avancées… |  | `edit.preferences.enhancedControls` | moteur | menu_catalog.rs:166 |
| 75 | Preferences (Préférences) | Raw Defaults… | Valeurs Raw par défaut… |  | `edit.preferences.rawDefaults` | moteur | menu_catalog.rs:167 |

### 1.3 Image — « Image » (61 entrées, 16 séparateurs)

| # | Chemin (sous-menu) | Libellé EN | Libellé FR (fr.tsv) | Raccourci | id de commande | Où l'id est implémenté (lecture statique) | Source |
|---|---|---|---|---|---|---|---|
| 1 | Mode | Bitmap | Bitmap |  | `image.mode.bitmap` | moteur | menu_catalog.rs:168 |
| 2 | Mode | Grayscale | Niveaux de gris |  | `image.mode.grayscale` | moteur | menu_catalog.rs:169 |
| 3 | Mode | Duotone | Duotone |  | `image.mode.duotone` | moteur | menu_catalog.rs:170 |
| 4 | Mode | Indexed Color | Couleurs indexées |  | `image.mode.indexedColor` | moteur | menu_catalog.rs:171 |
| 5 | Mode | RGB Color | Couleurs RVB |  | `image.mode.rgb` | moteur | menu_catalog.rs:172 |
| 6 | Mode | CMYK Color | Couleurs CMJN |  | `image.mode.cmyk` | moteur | menu_catalog.rs:173 |
| 7 | Mode | Lab Color | Couleurs Lab |  | `image.mode.lab` | moteur | menu_catalog.rs:174 |
| 8 | Mode | Multichannel | Multicanal |  | `image.mode.multichannel` | moteur | menu_catalog.rs:175 |
| | Mode | ——— séparateur ——— | | | | | menu_catalog.rs:176 |
| 9 | Mode | 8 Bits/Channel | 8 bits/canal |  | `image.mode.bits8` | moteur | menu_catalog.rs:177 |
| 10 | Mode | 16 Bits/Channel | 16 bits/canal |  | `image.mode.bits16` | moteur | menu_catalog.rs:178 |
| 11 | Mode | 32 Bits/Channel | 32 bits/canal |  | `image.mode.bits32` | moteur | menu_catalog.rs:179 |
| | Mode | ——— séparateur ——— | | | | | menu_catalog.rs:180 |
| 12 | Mode | Color Table… | Table des couleurs… |  | `image.mode.colorTable` | moteur | menu_catalog.rs:181 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:182 |
| 13 | Adjustments (Ajustements) | Brightness/Contrast… | Luminosité/Contraste… |  | `image.adjustments.brightnessContrast` | moteur | menu_catalog.rs:183 |
| 14 | Adjustments (Ajustements) | Levels… | Niveaux… | Cmd+L | `image.adjustments.levels` | moteur | menu_catalog.rs:184 |
| 15 | Adjustments (Ajustements) | Curves… | Courbes… | Cmd+M | `image.adjustments.curves` | moteur | menu_catalog.rs:185 |
| 16 | Adjustments (Ajustements) | Exposure… | Exposition… |  | `image.adjustments.exposure` | moteur | menu_catalog.rs:186 |
| 17 | Adjustments (Ajustements) | Vibrance… | Vibrance… |  | `image.adjustments.vibrance` | moteur | menu_catalog.rs:187 |
| 18 | Adjustments (Ajustements) | Hue/Saturation… | Teinte/Saturation… | Cmd+U | `image.adjustments.hueSaturation` | moteur | menu_catalog.rs:188 |
| 19 | Adjustments (Ajustements) | Color Balance… | Balance des couleurs… | Cmd+B | `image.adjustments.colorBalance` | moteur | menu_catalog.rs:189 |
| 20 | Adjustments (Ajustements) | Black & White… | Noir et blanc… | Cmd+Alt+Shift+B | `image.adjustments.blackWhite` | moteur | menu_catalog.rs:190 |
| 21 | Adjustments (Ajustements) | Photo Filter… | Filtre photo… |  | `image.adjustments.photoFilter` | moteur | menu_catalog.rs:191 |
| 22 | Adjustments (Ajustements) | Channel Mixer… | Mélangeur de canaux… |  | `image.adjustments.channelMixer` | moteur | menu_catalog.rs:192 |
| 23 | Adjustments (Ajustements) | Color Lookup… | Table de correspondance des couleurs… |  | `image.adjustments.colorLookup` | moteur | menu_catalog.rs:193 |
| | Adjustments | ——— séparateur ——— | | | | | menu_catalog.rs:194 |
| 24 | Adjustments (Ajustements) | Invert | Inverser | Cmd+I | `image.adjustments.invert` | moteur | menu_catalog.rs:195 |
| 25 | Adjustments (Ajustements) | Posterize… | Postériser… |  | `image.adjustments.posterize` | moteur | menu_catalog.rs:196 |
| 26 | Adjustments (Ajustements) | Threshold… | Seuil… |  | `image.adjustments.threshold` | moteur | menu_catalog.rs:197 |
| 27 | Adjustments (Ajustements) | Gradient Map… | Mappage de dégradé… |  | `image.adjustments.gradientMap` | moteur | menu_catalog.rs:198 |
| 28 | Adjustments (Ajustements) | Selective Color… | Couleur sélective… |  | `image.adjustments.selectiveColor` | moteur | menu_catalog.rs:199 |
| | Adjustments | ——— séparateur ——— | | | | | menu_catalog.rs:200 |
| 29 | Adjustments (Ajustements) | Shadows/Highlights… | Ombres/Hautes lumières… |  | `image.adjustments.shadowsHighlights` | moteur | menu_catalog.rs:201 |
| 30 | Adjustments (Ajustements) | HDR Toning… | Tonalité HDR… |  | `image.adjustments.hdrToning` | moteur | menu_catalog.rs:202 |
| | Adjustments | ——— séparateur ——— | | | | | menu_catalog.rs:203 |
| 31 | Adjustments (Ajustements) | Desaturate | Désaturer | Cmd+Shift+U | `image.adjustments.desaturate` | moteur | menu_catalog.rs:204 |
| 32 | Adjustments (Ajustements) | Match Color… | Faire correspondre la couleur… |  | `image.adjustments.matchColor` | moteur | menu_catalog.rs:205 |
| 33 | Adjustments (Ajustements) | Replace Color… | Remplacer la couleur… |  | `image.adjustments.replaceColor` | moteur | menu_catalog.rs:206 |
| 34 | Adjustments (Ajustements) | Equalize | Égaliser |  | `image.adjustments.equalize` | moteur | menu_catalog.rs:207 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:208 |
| 35 | — | Auto Tone | Tonalité automatique | Cmd+Shift+L | `image.autoTone` | moteur | menu_catalog.rs:209 |
| 36 | — | Auto Contrast | Contraste automatique | Cmd+Alt+Shift+L | `image.autoContrast` | moteur | menu_catalog.rs:210 |
| 37 | — | Auto Color | Couleur automatique | Cmd+Shift+B | `image.autoColor` | moteur | menu_catalog.rs:211 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:212 |
| 38 | — | Image Size… | Taille de l'image… | Cmd+Alt+I | `image.imageSize` | moteur | menu_catalog.rs:213 |
| 39 | — | Canvas Size… | Taille du canevas… | Cmd+Alt+C | `image.canvasSize` | moteur | menu_catalog.rs:214 |
| 40 | Image Rotation (Rotation de l'image) | 180° | 180° |  | `image.imageRotation.180` | moteur | menu_catalog.rs:215 |
| 41 | Image Rotation (Rotation de l'image) | 90° Clockwise | 90° horaire |  | `image.imageRotation.90cw` | moteur | menu_catalog.rs:216 |
| 42 | Image Rotation (Rotation de l'image) | 90° Counter Clockwise | 90° antihoraire |  | `image.imageRotation.90ccw` | moteur | menu_catalog.rs:217 |
| 43 | Image Rotation (Rotation de l'image) | Arbitrary… | Angle personnalisé… |  | `image.rotation.arbitrary` | moteur | menu_catalog.rs:218 |
| | Image Rotation | ——— séparateur ——— | | | | | menu_catalog.rs:219 |
| 44 | Image Rotation (Rotation de l'image) | Flip Canvas Horizontal | Retourner le canevas horizontalement |  | `image.imageRotation.flipCanvasHorizontal` | moteur | menu_catalog.rs:220 |
| 45 | Image Rotation (Rotation de l'image) | Flip Canvas Vertical | Retourner le canevas verticalement |  | `image.imageRotation.flipCanvasVertical` | moteur | menu_catalog.rs:221 |
| 46 | — | Crop | Recadrer |  | `image.crop` | moteur | menu_catalog.rs:222 |
| 47 | — | Trim… | Rogner les bords… |  | `image.trim` | moteur | menu_catalog.rs:223 |
| 48 | — | Reveal All | Tout afficher |  | `image.revealAll` | moteur | menu_catalog.rs:224 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:225 |
| 49 | — | Duplicate… | Dupliquer… |  | `image.duplicate` | moteur | menu_catalog.rs:226 |
| 50 | — | Apply Image… | Appliquer une image… |  | `image.applyImage` | shell UI (id cité dans ui-egui) | menu_catalog.rs:227 |
| 51 | — | Calculations… | Calculs… |  | `image.calculations` | shell UI (id cité dans ui-egui) | menu_catalog.rs:228 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:229 |
| 52 | Variables | Define… | Définir… |  | `image.variables.define` | moteur | menu_catalog.rs:230 |
| 53 | Variables | Data Sets… | Jeux de données… |  | `image.variables.dataSets` | moteur | menu_catalog.rs:231 |
| 54 | — | Apply Data Set… | Appliquer un jeu de données… |  | `image.applyDataSet` | moteur | menu_catalog.rs:232 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:233 |
| 55 | — | Trap… | Recouvrement… |  | `image.trap` | moteur | menu_catalog.rs:234 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:235 |
| 56 | Analysis (Analyse) | Set Measurement Scale… | Définir l'échelle de mesure… |  | `image.analysis.setMeasurementScale` | moteur | menu_catalog.rs:236 |
| 57 | Analysis (Analyse) | Select Data Points… | Sélectionner les points de données… |  | `image.analysis.selectDataPoints` | moteur | menu_catalog.rs:237 |
| | Analysis | ——— séparateur ——— | | | | | menu_catalog.rs:238 |
| 58 | Analysis (Analyse) | Record Measurements | Enregistrer les mesures |  | `image.analysis.recordMeasurements` | moteur | menu_catalog.rs:239 |
| | Analysis | ——— séparateur ——— | | | | | menu_catalog.rs:240 |
| 59 | Analysis (Analyse) | Ruler Tool | Outil Règle |  | `image.analysis.rulerTool` | moteur | menu_catalog.rs:241 |
| 60 | Analysis (Analyse) | Count Tool | Outil Compteur |  | `image.analysis.countTool` | moteur | menu_catalog.rs:242 |
| | Analysis | ——— séparateur ——— | | | | | menu_catalog.rs:243 |
| 61 | Analysis (Analyse) | Place Scale Marker… | Placer un repère d'échelle… |  | `image.analysis.placeScaleMarker` | moteur | menu_catalog.rs:244 |

### 1.4 Layer — « Calque » (168 entrées, 42 séparateurs)

| # | Chemin (sous-menu) | Libellé EN | Libellé FR (fr.tsv) | Raccourci | id de commande | Où l'id est implémenté (lecture statique) | Source |
|---|---|---|---|---|---|---|---|
| 1 | New (Nouveau) | Layer… | Calque… | Cmd+Shift+N | `layer.new.layer` | moteur | menu_catalog.rs:245 |
| 2 | New (Nouveau) | Layer from Background… | Calque d'après l'arrière-plan… |  | `layer.new.layerFromBackground` | moteur | menu_catalog.rs:246 |
| 3 | New (Nouveau) | Group… | Groupe… |  | `layer.new.group` | moteur | menu_catalog.rs:247 |
| 4 | New (Nouveau) | Group from Layers… | Groupe d'après des calques… |  | `layer.new.groupFromLayers` | moteur | menu_catalog.rs:248 |
| | New | ——— séparateur ——— | | | | | menu_catalog.rs:249 |
| 5 | New (Nouveau) | Artboard… | Plan de travail… |  | `layer.new.artboard` | moteur | menu_catalog.rs:250 |
| 6 | New (Nouveau) | Artboard from Group… | Plan de travail d'après un groupe… |  | `layer.new.artboardFromGroup` | moteur | menu_catalog.rs:251 |
| 7 | New (Nouveau) | Artboard from Layers… | Plan de travail d'après des calques… |  | `layer.new.artboardFromLayers` | moteur | menu_catalog.rs:252 |
| 8 | New (Nouveau) | Frame from Layers | Image d'après les calques |  | `layer.new.frameFromLayers` | moteur | menu_catalog.rs:253 |
| | New | ——— séparateur ——— | | | | | menu_catalog.rs:254 |
| 9 | New (Nouveau) | Layer via Copy | Calque par copie | Cmd+J | `layer.new.layerViaCopy` | moteur | menu_catalog.rs:255 |
| 10 | New (Nouveau) | Layer via Cut | Calque par coupe | Cmd+Shift+J | `layer.new.layerViaCut` | moteur | menu_catalog.rs:256 |
| 11 | — | Duplicate Layer… | Dupliquer le calque… |  | `layer.duplicate` | moteur | menu_catalog.rs:257 |
| 12 | Delete (Supprimer) | Layer | Calque |  | `layer.delete` | moteur | menu_catalog.rs:258 |
| 13 | Delete (Supprimer) | Hidden Layers | Calques masqués |  | `layer.delete.hiddenLayers` | moteur | menu_catalog.rs:259 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:260 |
| 14 | — | Quick Export as PNG | Exportation rapide au format PNG | Cmd+Shift+' | `layer.quickExportAsPng` | moteur | menu_catalog.rs:261 |
| 15 | — | Export As… | Exporter sous… | Cmd+Alt+Shift+' | `layer.exportAs` | moteur | menu_catalog.rs:262 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:263 |
| 16 | — | Rename Layer | Renommer le calque |  | `layer.renameLayer` | moteur | menu_catalog.rs:264 |
| 17 | Layer Style (Style de calque) | Blending Options… | Options de fusion… |  | `layer.layerStyle.blendingOptions` | moteur | menu_catalog.rs:265 |
| 18 | Layer Style (Style de calque) | Bevel & Emboss… | Biseau et relief… |  | `layer.layerStyle.bevelEmboss` | moteur | menu_catalog.rs:266 |
| 19 | Layer Style (Style de calque) | Stroke… | Contourner… |  | `layer.layerStyle.stroke` | moteur | menu_catalog.rs:267 |
| 20 | Layer Style (Style de calque) | Inner Shadow… | Ombre intérieure… |  | `layer.layerStyle.innerShadow` | moteur | menu_catalog.rs:268 |
| 21 | Layer Style (Style de calque) | Inner Glow… | Lueur intérieure… |  | `layer.layerStyle.innerGlow` | moteur | menu_catalog.rs:269 |
| 22 | Layer Style (Style de calque) | Satin… | Satin… |  | `layer.layerStyle.satin` | moteur | menu_catalog.rs:270 |
| 23 | Layer Style (Style de calque) | Color Overlay… | Superposition de couleur… |  | `layer.layerStyle.colorOverlay` | moteur | menu_catalog.rs:271 |
| 24 | Layer Style (Style de calque) | Gradient Overlay… | Superposition de dégradé… |  | `layer.layerStyle.gradientOverlay` | moteur | menu_catalog.rs:272 |
| 25 | Layer Style (Style de calque) | Pattern Overlay… | Superposition de motif… |  | `layer.layerStyle.patternOverlay` | moteur | menu_catalog.rs:273 |
| 26 | Layer Style (Style de calque) | Outer Glow… | Lueur extérieure… |  | `layer.layerStyle.outerGlow` | moteur | menu_catalog.rs:274 |
| 27 | Layer Style (Style de calque) | Drop Shadow… | Ombre portée… |  | `layer.layerStyle.dropShadow` | moteur | menu_catalog.rs:275 |
| | Layer Style | ——— séparateur ——— | | | | | menu_catalog.rs:276 |
| 28 | Layer Style (Style de calque) | Copy Layer Style | Copier le style de calque |  | `layer.layerStyle.copyLayerStyle` | moteur | menu_catalog.rs:277 |
| 29 | Layer Style (Style de calque) | Paste Layer Style | Coller le style de calque |  | `layer.layerStyle.pasteLayerStyle` | moteur | menu_catalog.rs:278 |
| 30 | Layer Style (Style de calque) | Clear Layer Style | Effacer le style de calque |  | `layer.layerStyle.clear` | moteur | menu_catalog.rs:279 |
| | Layer Style | ——— séparateur ——— | | | | | menu_catalog.rs:280 |
| 31 | Layer Style (Style de calque) | Global Light… | Lumière globale… |  | `layer.layerStyle.globalLight` | moteur | menu_catalog.rs:281 |
| 32 | Layer Style (Style de calque) | Create Layer | Créer un calque |  | `layer.layerStyle.createLayer` | moteur | menu_catalog.rs:282 |
| 33 | Layer Style (Style de calque) | Hide All Effects | Masquer tous les effets |  | `layer.layerStyle.hideAllEffects` | moteur | menu_catalog.rs:283 |
| 34 | Layer Style (Style de calque) | Scale Effects… | Mettre les effets à l'échelle… |  | `layer.layerStyle.scaleEffects` | moteur | menu_catalog.rs:284 |
| 35 | Smart Filter (Filtre intelligent) | Disable Smart Filters | Désactiver les filtres intelligents |  | `layer.smartFilter.disableSmartFilters` | moteur | menu_catalog.rs:285 |
| | Smart Filter | ——— séparateur ——— | | | | | menu_catalog.rs:286 |
| 36 | Smart Filter (Filtre intelligent) | Delete Filter Mask | Supprimer le masque de filtre |  | `layer.smartFilter.deleteFilterMask` | moteur | menu_catalog.rs:287 |
| 37 | Smart Filter (Filtre intelligent) | Disable Filter Mask | Désactiver le masque de filtre |  | `layer.smartFilter.disableFilterMask` | moteur | menu_catalog.rs:288 |
| 38 | Smart Filter (Filtre intelligent) | Blending Options… | Options de fusion… |  | `layer.smartFilter.blendingOptions` | moteur | menu_catalog.rs:289 |
| | Smart Filter | ——— séparateur ——— | | | | | menu_catalog.rs:290 |
| 39 | Smart Filter (Filtre intelligent) | Clear Smart Filters | Effacer les filtres intelligents |  | `layer.smartFilter.clearSmartFilters` | moteur | menu_catalog.rs:291 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:292 |
| 40 | New Fill Layer (Nouveau calque de remplissage) | Solid Color… | Couleur unie… |  | `layer.newFillLayer.solidColor` | moteur | menu_catalog.rs:293 |
| 41 | New Fill Layer (Nouveau calque de remplissage) | Gradient… | Dégradé… |  | `layer.newFillLayer.gradient` | moteur | menu_catalog.rs:294 |
| 42 | New Fill Layer (Nouveau calque de remplissage) | Pattern… | Motif… |  | `layer.newFillLayer.pattern` | moteur | menu_catalog.rs:295 |
| 43 | New Adjustment Layer (Nouveau calque de réglage) | Brightness/Contrast… | Luminosité/Contraste… |  | `layer.newAdjustmentLayer.brightnessContrast` | moteur | menu_catalog.rs:296 |
| 44 | New Adjustment Layer (Nouveau calque de réglage) | Levels… | Niveaux… |  | `layer.newAdjustmentLayer.levels` | moteur | menu_catalog.rs:297 |
| 45 | New Adjustment Layer (Nouveau calque de réglage) | Curves… | Courbes… |  | `layer.newAdjustmentLayer.curves` | moteur | menu_catalog.rs:298 |
| 46 | New Adjustment Layer (Nouveau calque de réglage) | Exposure… | Exposition… |  | `layer.newAdjustmentLayer.exposure` | moteur | menu_catalog.rs:299 |
| 47 | New Adjustment Layer (Nouveau calque de réglage) | Vibrance… | Vibrance… |  | `layer.newAdjustmentLayer.vibrance` | moteur | menu_catalog.rs:300 |
| 48 | New Adjustment Layer (Nouveau calque de réglage) | Hue/Saturation… | Teinte/Saturation… |  | `layer.newAdjustmentLayer.hueSaturation` | moteur | menu_catalog.rs:301 |
| 49 | New Adjustment Layer (Nouveau calque de réglage) | Color Balance… | Balance des couleurs… |  | `layer.newAdjustmentLayer.colorBalance` | moteur | menu_catalog.rs:302 |
| 50 | New Adjustment Layer (Nouveau calque de réglage) | Black & White… | Noir et blanc… |  | `layer.newAdjustmentLayer.blackWhite` | moteur | menu_catalog.rs:303 |
| 51 | New Adjustment Layer (Nouveau calque de réglage) | Photo Filter… | Filtre photo… |  | `layer.newAdjustmentLayer.photoFilter` | moteur | menu_catalog.rs:304 |
| 52 | New Adjustment Layer (Nouveau calque de réglage) | Channel Mixer… | Mélangeur de canaux… |  | `layer.newAdjustmentLayer.channelMixer` | moteur | menu_catalog.rs:305 |
| 53 | New Adjustment Layer (Nouveau calque de réglage) | Color Lookup… | Table de correspondance des couleurs… |  | `layer.newAdjustmentLayer.colorLookup` | moteur | menu_catalog.rs:306 |
| | New Adjustment Layer | ——— séparateur ——— | | | | | menu_catalog.rs:307 |
| 54 | New Adjustment Layer (Nouveau calque de réglage) | Invert… | Inverser… |  | `layer.newAdjustmentLayer.invert` | moteur | menu_catalog.rs:308 |
| 55 | New Adjustment Layer (Nouveau calque de réglage) | Posterize… | Postériser… |  | `layer.newAdjustmentLayer.posterize` | moteur | menu_catalog.rs:309 |
| 56 | New Adjustment Layer (Nouveau calque de réglage) | Threshold… | Seuil… |  | `layer.newAdjustmentLayer.threshold` | moteur | menu_catalog.rs:310 |
| 57 | New Adjustment Layer (Nouveau calque de réglage) | Gradient Map… | Mappage de dégradé… |  | `layer.newAdjustmentLayer.gradientMap` | moteur | menu_catalog.rs:311 |
| 58 | New Adjustment Layer (Nouveau calque de réglage) | Selective Color… | Couleur sélective… |  | `layer.newAdjustmentLayer.selectiveColor` | moteur | menu_catalog.rs:312 |
| 59 | — | Layer Content Options… | Options de contenu du calque… |  | `layer.layerContentOptions` | moteur | menu_catalog.rs:313 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:314 |
| 60 | Layer Mask (Masque de calque) | Reveal All | Tout afficher |  | `layer.layerMask.revealAll` | moteur | menu_catalog.rs:315 |
| 61 | Layer Mask (Masque de calque) | Hide All | Tout masquer |  | `layer.layerMask.hideAll` | moteur | menu_catalog.rs:316 |
| | Layer Mask | ——— séparateur ——— | | | | | menu_catalog.rs:317 |
| 62 | Layer Mask (Masque de calque) | Reveal Selection | Afficher la sélection |  | `layer.layerMask.revealSelection` | moteur | menu_catalog.rs:318 |
| 63 | Layer Mask (Masque de calque) | Hide Selection | Masquer la sélection |  | `layer.layerMask.hideSelection` | moteur | menu_catalog.rs:319 |
| 64 | Layer Mask (Masque de calque) | From Transparency | D'après la transparence |  | `layer.layerMask.fromTransparency` | moteur | menu_catalog.rs:320 |
| | Layer Mask | ——— séparateur ——— | | | | | menu_catalog.rs:321 |
| 65 | Layer Mask (Masque de calque) | Delete | Supprimer |  | `layer.layerMask.delete` | moteur | menu_catalog.rs:322 |
| 66 | Layer Mask (Masque de calque) | Apply | Appliquer |  | `layer.layerMask.apply` | moteur | menu_catalog.rs:323 |
| | Layer Mask | ——— séparateur ——— | | | | | menu_catalog.rs:324 |
| 67 | Layer Mask (Masque de calque) | Enable Layer Mask | Activer le masque de calque |  | `layer.layerMask.enabled` | moteur | menu_catalog.rs:325 |
| 68 | Layer Mask (Masque de calque) | Link Layer Mask | Lier le masque de calque |  | `layer.layerMask.linked` | moteur | menu_catalog.rs:326 |
| 69 | — | Mask All Objects | Masquer tous les objets |  | `layer.maskAllObjects` | moteur | menu_catalog.rs:327 |
| 70 | Vector Mask (Masque vectoriel) | Reveal All | Tout afficher |  | `layer.vectorMask.revealAll` | moteur | menu_catalog.rs:328 |
| 71 | Vector Mask (Masque vectoriel) | Hide All | Tout masquer |  | `layer.vectorMask.hideAll` | moteur | menu_catalog.rs:329 |
| 72 | Vector Mask (Masque vectoriel) | Current Path | Tracé actif |  | `layer.vectorMask.currentPath` | moteur | menu_catalog.rs:330 |
| | Vector Mask | ——— séparateur ——— | | | | | menu_catalog.rs:331 |
| 73 | Vector Mask (Masque vectoriel) | Delete | Supprimer |  | `layer.vectorMask.delete` | moteur | menu_catalog.rs:332 |
| | Vector Mask | ——— séparateur ——— | | | | | menu_catalog.rs:333 |
| 74 | Vector Mask (Masque vectoriel) | Enable Vector Mask | Activer le masque vectoriel |  | `layer.vectorMask.enabled` | moteur | menu_catalog.rs:334 |
| 75 | Vector Mask (Masque vectoriel) | Link Vector Mask | Lier le masque vectoriel |  | `layer.vectorMask.linked` | moteur | menu_catalog.rs:335 |
| 76 | — | Create Clipping Mask | Créer un masque de découpe | Cmd+Alt+G | `layer.createClippingMask` | moteur | menu_catalog.rs:336 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:337 |
| 77 | Smart Objects (Objets intelligents) | Convert to Smart Object | Convertir en objet intelligent |  | `layer.smartObjects.convertToSmartObject` | moteur | menu_catalog.rs:338 |
| 78 | Smart Objects (Objets intelligents) | New Smart Object via Copy | Nouvel objet intelligent par copie |  | `layer.smartObjects.newSmartObjectViaCopy` | moteur | menu_catalog.rs:339 |
| | Smart Objects | ——— séparateur ——— | | | | | menu_catalog.rs:340 |
| 79 | Smart Objects (Objets intelligents) | Reveal in Finder | Afficher dans le Finder |  | `layer.smartObjects.revealInFinder` | moteur | menu_catalog.rs:341 |
| | Smart Objects | ——— séparateur ——— | | | | | menu_catalog.rs:342 |
| 80 | Smart Objects (Objets intelligents) | Update Modified Content | Mettre à jour le contenu modifié |  | `layer.smartObjects.updateModifiedContent` | moteur | menu_catalog.rs:343 |
| 81 | Smart Objects (Objets intelligents) | Update All Modified Content | Mettre à jour tout le contenu modifié |  | `layer.smartObjects.updateAllModifiedContent` | moteur | menu_catalog.rs:344 |
| | Smart Objects | ——— séparateur ——— | | | | | menu_catalog.rs:345 |
| 82 | Smart Objects (Objets intelligents) | Edit Contents | Modifier le contenu |  | `layer.smartObjects.editContents` | moteur | menu_catalog.rs:346 |
| 83 | Smart Objects (Objets intelligents) | Relink to File… | Lier de nouveau au fichier… |  | `layer.smartObjects.relinkToFile` | moteur | menu_catalog.rs:347 |
| 84 | Smart Objects (Objets intelligents) | Replace Contents… | Remplacer le contenu… |  | `layer.smartObjects.replaceContents` | moteur | menu_catalog.rs:348 |
| 85 | Smart Objects (Objets intelligents) | Export Contents… | Exporter le contenu… |  | `layer.smartObjects.exportContents` | moteur | menu_catalog.rs:349 |
| | Smart Objects | ——— séparateur ——— | | | | | menu_catalog.rs:350 |
| 86 | Smart Objects (Objets intelligents) | Convert to Linked… | Convertir en objet lié… |  | `layer.smartObjects.convertToLinked` | moteur | menu_catalog.rs:351 |
| 87 | Smart Objects (Objets intelligents) | Convert to Embedded | Convertir en objet incorporé |  | `layer.smartObjects.convertToEmbedded` | moteur | menu_catalog.rs:352 |
| | Smart Objects | ——— séparateur ——— | | | | | menu_catalog.rs:353 |
| 88 | Smart Objects › Stack Mode (Objets intelligents › Mode de pile) | Entropy | Entropie |  | `layer.smartObjects.stackMode.entropy` | shell UI (id cité dans ui-egui) | menu_catalog.rs:354 |
| 89 | Smart Objects › Stack Mode (Objets intelligents › Mode de pile) | Kurtosis | Kurtosis |  | `layer.smartObjects.stackMode.kurtosis` | shell UI (id cité dans ui-egui) | menu_catalog.rs:355 |
| 90 | Smart Objects › Stack Mode (Objets intelligents › Mode de pile) | Maximum | Maximum |  | `layer.smartObjects.stackMode.maximum` | shell UI (id cité dans ui-egui) | menu_catalog.rs:356 |
| 91 | Smart Objects › Stack Mode (Objets intelligents › Mode de pile) | Mean | Moyenne |  | `layer.smartObjects.stackMode.mean` | shell UI (id cité dans ui-egui) | menu_catalog.rs:357 |
| 92 | Smart Objects › Stack Mode (Objets intelligents › Mode de pile) | Median | Médiane |  | `layer.smartObjects.stackMode.median` | shell UI (id cité dans ui-egui) | menu_catalog.rs:358 |
| 93 | Smart Objects › Stack Mode (Objets intelligents › Mode de pile) | Minimum | Minimum |  | `layer.smartObjects.stackMode.minimum` | shell UI (id cité dans ui-egui) | menu_catalog.rs:359 |
| 94 | Smart Objects › Stack Mode (Objets intelligents › Mode de pile) | Range | Plage |  | `layer.smartObjects.stackMode.range` | shell UI (id cité dans ui-egui) | menu_catalog.rs:360 |
| 95 | Smart Objects › Stack Mode (Objets intelligents › Mode de pile) | Skewness | Asymétrie |  | `layer.smartObjects.stackMode.skewness` | shell UI (id cité dans ui-egui) | menu_catalog.rs:361 |
| 96 | Smart Objects › Stack Mode (Objets intelligents › Mode de pile) | Standard Deviation | Écart type |  | `layer.smartObjects.stackMode.standardDeviation` | shell UI (id cité dans ui-egui) | menu_catalog.rs:362 |
| 97 | Smart Objects › Stack Mode (Objets intelligents › Mode de pile) | Summation | Somme |  | `layer.smartObjects.stackMode.summation` | shell UI (id cité dans ui-egui) | menu_catalog.rs:363 |
| 98 | Smart Objects › Stack Mode (Objets intelligents › Mode de pile) | Variance | Variance |  | `layer.smartObjects.stackMode.variance` | shell UI (id cité dans ui-egui) | menu_catalog.rs:364 |
| | Smart Objects | ——— séparateur ——— | | | | | menu_catalog.rs:365 |
| 99 | Smart Objects (Objets intelligents) | Rasterize | Rastériser |  | `layer.smartObjects.rasterize` | moteur | menu_catalog.rs:366 |
| | Smart Objects | ——— séparateur ——— | | | | | menu_catalog.rs:367 |
| 100 | Smart Objects (Objets intelligents) | Warp | Déformer |  | `layer.smartObjects.warp` | moteur | menu_catalog.rs:368 |
| 101 | Smart Objects (Objets intelligents) | Perspective Warp | Déformation de la perspective |  | `layer.smartObjects.perspectiveWarp` | moteur | menu_catalog.rs:369 |
| 102 | Smart Objects (Objets intelligents) | Puppet Warp | Déformation par épingles |  | `layer.smartObjects.puppetWarp` | moteur | menu_catalog.rs:370 |
| 103 | Video Layers (Calques vidéo) | New Blank Video Layer | Nouveau calque vidéo vide |  | `layer.videoLayers.newBlankVideoLayer` | moteur | menu_catalog.rs:371 |
| 104 | Video Layers (Calques vidéo) | New Video Layer from File… | Nouveau calque vidéo à partir d'un fichier… |  | `layer.videoLayers.newVideoLayerFromFile` | moteur | menu_catalog.rs:372 |
| | Video Layers | ——— séparateur ——— | | | | | menu_catalog.rs:373 |
| 105 | Video Layers (Calques vidéo) | Insert Blank Frame | Insérer une image vide |  | `layer.videoLayers.insertBlankFrame` | moteur | menu_catalog.rs:374 |
| 106 | Video Layers (Calques vidéo) | Duplicate Frame | Dupliquer l'image |  | `layer.videoLayers.duplicateFrame` | moteur | menu_catalog.rs:375 |
| 107 | Video Layers (Calques vidéo) | Delete Frame | Supprimer l'image |  | `layer.videoLayers.deleteFrame` | moteur | menu_catalog.rs:376 |
| | Video Layers | ——— séparateur ——— | | | | | menu_catalog.rs:377 |
| 108 | Video Layers (Calques vidéo) | Replace Footage… | Remplacer le métrage… |  | `layer.videoLayers.replaceFootage` | moteur | menu_catalog.rs:378 |
| 109 | Video Layers (Calques vidéo) | Interpret Footage… | Interpréter le métrage… |  | `layer.videoLayers.interpretFootage` | moteur | menu_catalog.rs:379 |
| | Video Layers | ——— séparateur ——— | | | | | menu_catalog.rs:380 |
| 110 | Video Layers (Calques vidéo) | Show Altered Video | Afficher la vidéo modifiée |  | `layer.videoLayers.showAlteredVideo` | moteur | menu_catalog.rs:381 |
| | Video Layers | ——— séparateur ——— | | | | | menu_catalog.rs:382 |
| 111 | Video Layers (Calques vidéo) | Restore Frame | Restaurer l'image |  | `layer.videoLayers.restoreFrame` | moteur | menu_catalog.rs:383 |
| 112 | Video Layers (Calques vidéo) | Restore All Frames | Restaurer toutes les images |  | `layer.videoLayers.restoreAllFrames` | moteur | menu_catalog.rs:384 |
| 113 | Video Layers (Calques vidéo) | Reload Frame | Recharger l'image |  | `layer.videoLayers.reloadFrame` | moteur | menu_catalog.rs:385 |
| | Video Layers | ——— séparateur ——— | | | | | menu_catalog.rs:386 |
| 114 | Video Layers (Calques vidéo) | Rasterize | Rastériser |  | `layer.videoLayers.rasterize` | moteur | menu_catalog.rs:387 |
| 115 | Rasterize (Rastériser) | Type | Texte |  | `layer.rasterize.type` | moteur | menu_catalog.rs:388 |
| 116 | Rasterize (Rastériser) | Shape | Forme |  | `layer.rasterize.shape` | moteur | menu_catalog.rs:389 |
| 117 | Rasterize (Rastériser) | Fill Content | Contenu du remplissage |  | `layer.rasterize.fillContent` | moteur | menu_catalog.rs:390 |
| 118 | Rasterize (Rastériser) | Vector Mask | Masque vectoriel |  | `layer.rasterize.vectorMask` | moteur | menu_catalog.rs:391 |
| 119 | Rasterize (Rastériser) | Smart Object | Objet intelligent |  | `layer.rasterize.smartObject` | moteur | menu_catalog.rs:392 |
| 120 | Rasterize (Rastériser) | Video | Vidéo |  | `layer.rasterize.video` | moteur | menu_catalog.rs:393 |
| | Rasterize | ——— séparateur ——— | | | | | menu_catalog.rs:394 |
| 121 | Rasterize (Rastériser) | Layer | Calque |  | `layer.rasterize.layer` | moteur | menu_catalog.rs:395 |
| 122 | Rasterize (Rastériser) | All Layers | Tous les calques |  | `layer.rasterize.allLayers` | moteur | menu_catalog.rs:396 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:397 |
| 123 | — | New Layer Based Slice | Nouvelle tranche d'après un calque |  | `layer.newLayerBasedSlice` | moteur | menu_catalog.rs:398 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:399 |
| 124 | — | Group Layers | Grouper les calques |  | `layer.groupLayers` | moteur | menu_catalog.rs:400 |
| 125 | — | Ungroup Layers | Dissocier les calques |  | `layer.ungroupLayers` | moteur | menu_catalog.rs:401 |
| 126 | — | Hide Layers | Masquer les calques |  | `layer.hideLayers` | moteur | menu_catalog.rs:402 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:403 |
| 127 | Arrange (Organiser) | Bring to Front | Mettre au premier plan | Cmd+Shift+] | `layer.arrange.bringToFront` | moteur | menu_catalog.rs:404 |
| 128 | Arrange (Organiser) | Bring Forward | Avancer d'un niveau | Cmd+] | `layer.arrange.bringForward` | moteur | menu_catalog.rs:405 |
| 129 | Arrange (Organiser) | Send Backward | Reculer d'un niveau | Cmd+[ | `layer.arrange.sendBackward` | moteur | menu_catalog.rs:406 |
| 130 | Arrange (Organiser) | Send to Back | Mettre à l'arrière-plan | Cmd+Shift+[ | `layer.arrange.sendToBack` | moteur | menu_catalog.rs:407 |
| | Arrange | ——— séparateur ——— | | | | | menu_catalog.rs:408 |
| 131 | Arrange (Organiser) | Reverse | Inverser l'ordre |  | `layer.arrange.reverse` | moteur | menu_catalog.rs:409 |
| 132 | Combine Shapes (Combiner les formes) | Unite Shapes | Réunir les formes |  | `layer.combineShapes.unite` | moteur | menu_catalog.rs:410 |
| 133 | Combine Shapes (Combiner les formes) | Subtract Front Shape | Soustraire la forme de premier plan |  | `layer.combineShapes.subtractFrontShape` | moteur | menu_catalog.rs:411 |
| 134 | Combine Shapes (Combiner les formes) | Intersect Shape Areas | Intersection des zones de formes |  | `layer.combineShapes.intersectShapeAreas` | moteur | menu_catalog.rs:412 |
| 135 | Combine Shapes (Combiner les formes) | Exclude Overlapping Shapes | Exclure les formes superposées |  | `layer.combineShapes.excludeOverlappingShapes` | moteur | menu_catalog.rs:413 |
| | Combine Shapes | ——— séparateur ——— | | | | | menu_catalog.rs:414 |
| 136 | Combine Shapes (Combiner les formes) | Merge Shape Components | Fusionner les composants de forme |  | `layer.combineShapes.mergeShapeComponents` | moteur | menu_catalog.rs:415 |
| 137 | Align (Aligner) | Top Edges | Bords supérieurs |  | `layer.align.topEdges` | moteur | menu_catalog.rs:416 |
| 138 | Align (Aligner) | Vertical Centers | Centres verticaux |  | `layer.align.verticalCenters` | moteur | menu_catalog.rs:417 |
| 139 | Align (Aligner) | Bottom Edges | Bords inférieurs |  | `layer.align.bottomEdges` | moteur | menu_catalog.rs:418 |
| | Align | ——— séparateur ——— | | | | | menu_catalog.rs:419 |
| 140 | Align (Aligner) | Left Edges | Bords gauches |  | `layer.align.leftEdges` | moteur | menu_catalog.rs:420 |
| 141 | Align (Aligner) | Horizontal Centers | Centres horizontaux |  | `layer.align.horizontalCenters` | moteur | menu_catalog.rs:421 |
| 142 | Align (Aligner) | Right Edges | Bords droits |  | `layer.align.rightEdges` | moteur | menu_catalog.rs:422 |
| 143 | Distribute (Répartir) | Top Edges | Bords supérieurs |  | `layer.distribute.topEdges` | moteur | menu_catalog.rs:423 |
| 144 | Distribute (Répartir) | Vertical Centers | Centres verticaux |  | `layer.distribute.verticalCenters` | moteur | menu_catalog.rs:424 |
| 145 | Distribute (Répartir) | Bottom Edges | Bords inférieurs |  | `layer.distribute.bottomEdges` | moteur | menu_catalog.rs:425 |
| | Distribute | ——— séparateur ——— | | | | | menu_catalog.rs:426 |
| 146 | Distribute (Répartir) | Left Edges | Bords gauches |  | `layer.distribute.leftEdges` | moteur | menu_catalog.rs:427 |
| 147 | Distribute (Répartir) | Horizontal Centers | Centres horizontaux |  | `layer.distribute.horizontalCenters` | moteur | menu_catalog.rs:428 |
| 148 | Distribute (Répartir) | Right Edges | Bords droits |  | `layer.distribute.rightEdges` | moteur | menu_catalog.rs:429 |
| | Distribute | ——— séparateur ——— | | | | | menu_catalog.rs:430 |
| 149 | Distribute (Répartir) | Horizontally | Horizontalement |  | `layer.distribute.horizontally` | moteur | menu_catalog.rs:431 |
| 150 | Distribute (Répartir) | Vertically | Verticalement |  | `layer.distribute.vertically` | moteur | menu_catalog.rs:432 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:433 |
| 151 | — | Lock Layers… | Verrouiller les calques… |  | `layer.lockLayers` | moteur | menu_catalog.rs:434 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:435 |
| 152 | — | Link Layers | Lier les calques |  | `layer.linkLayers` | moteur | menu_catalog.rs:436 |
| 153 | — | Select Linked Layers | Sélectionner les calques liés |  | `layer.selectLinkedLayers` | moteur | menu_catalog.rs:437 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:438 |
| 154 | — | Merge Layers | Fusionner les calques | Cmd+E | `layer.mergeLayers` | moteur | menu_catalog.rs:439 |
| 155 | — | Merge Visible | Fusionner les calques visibles | Cmd+Shift+E | `layer.mergeVisible` | moteur | menu_catalog.rs:440 |
| 156 | — | Flatten Image | Aplatir l'image |  | `layer.flattenImage` | moteur | menu_catalog.rs:441 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:442 |
| 157 | Matting (Détourage) | Color Decontaminate… | Décontaminer les couleurs… |  | `layer.matting.colorDecontaminate` | moteur | menu_catalog.rs:443 |
| 158 | Matting (Détourage) | Defringe… | Supprimer les franges… |  | `layer.matting.defringe` | moteur | menu_catalog.rs:444 |
| 159 | Matting (Détourage) | Remove Black Matte | Supprimer le fond noir |  | `layer.matting.removeBlackMatte` | moteur | menu_catalog.rs:445 |
| 160 | Matting (Détourage) | Remove White Matte | Supprimer le fond blanc |  | `layer.matting.removeWhiteMatte` | moteur | menu_catalog.rs:446 |
| 161 | — | Release Clipping Mask | Libérer le masque de découpe |  | `layer.releaseClippingMask` | moteur | commands.rs:539 |
| 162 | — | Merge Down | Fusionner avec le calque inférieur |  | `layer.mergeDown` | moteur | commands.rs:570 |
| 163 | New (Nouveau) | New Type Layer | Nouveau calque de texte |  | `type.create` | moteur | type_cmds.rs:486 |
| 164 | Rasterize (Rastériser) | Rasterize Type | Rastériser le texte |  | `type.rasterize` | moteur | type_cmds.rs:681 |
| 165 | New (Nouveau) | New Shape Layer | Nouveau calque de forme |  | `shape.create` | moteur | vector_cmds.rs:1243 |
| 166 | Rasterize (Rastériser) | Rasterize Shape | Rastériser la forme |  | `shape.rasterize` | moteur | vector_cmds.rs:1275 |
| 167 | Vector Mask (Masque vectoriel) | Add Vector Mask | Ajouter un masque vectoriel |  | `layer.vectorMask.add` | moteur | vector_cmds.rs:1376 |
| 168 | Vector Mask (Masque vectoriel) | Vector Mask from Current Path | Masque vectoriel d'après le tracé actif |  | `layer.vectorMask.fromPath` | moteur | vector_cmds.rs:1384 |

### 1.5 Type — « Texte » (45 entrées, 10 séparateurs)

| # | Chemin (sous-menu) | Libellé EN | Libellé FR (fr.tsv) | Raccourci | id de commande | Où l'id est implémenté (lecture statique) | Source |
|---|---|---|---|---|---|---|---|
| 1 | Panels (Panneaux) | Character Panel | Panneau Caractère |  | `type.panels.character` | shell UI (id cité dans ui-egui) | menu_catalog.rs:447 |
| 2 | Panels (Panneaux) | Paragraph Panel | Panneau Paragraphe |  | `type.panels.paragraph` | shell UI (id cité dans ui-egui) | menu_catalog.rs:448 |
| 3 | Panels (Panneaux) | Glyphs Panel | Panneau Glyphes |  | `type.panels.glyphs` | shell UI (id cité dans ui-egui) | menu_catalog.rs:449 |
| 4 | Panels (Panneaux) | Character Styles Panel | Panneau Styles de caractère |  | `type.panels.characterStyles` | shell UI (id cité dans ui-egui) | menu_catalog.rs:450 |
| 5 | Panels (Panneaux) | Paragraph Styles Panel | Panneau Styles de paragraphe |  | `type.panels.paragraphStyles` | shell UI (id cité dans ui-egui) | menu_catalog.rs:451 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:452 |
| 6 | Anti-Alias (Lissage) | Sharp | Net |  | `type.antiAlias.sharp` | moteur | menu_catalog.rs:453 |
| 7 | Anti-Alias (Lissage) | Crisp | Vif |  | `type.antiAlias.crisp` | moteur | menu_catalog.rs:454 |
| 8 | Anti-Alias (Lissage) | Strong | Fort |  | `type.antiAlias.strong` | moteur | menu_catalog.rs:455 |
| 9 | Anti-Alias (Lissage) | Smooth | Doux |  | `type.antiAlias.smooth` | moteur | menu_catalog.rs:456 |
| | Anti-Alias | ——— séparateur ——— | | | | | menu_catalog.rs:457 |
| 10 | Anti-Alias (Lissage) | Windows LCD | LCD Windows |  | `type.antiAlias.windowsLcd` | moteur | menu_catalog.rs:458 |
| 11 | Anti-Alias (Lissage) | Windows | Windows |  | `type.antiAlias.windows` | moteur | menu_catalog.rs:459 |
| 12 | Orientation | Horizontal | Horizontal |  | `type.orientation.horizontal` | moteur | menu_catalog.rs:460 |
| 13 | Orientation | Vertical | Vertical |  | `type.orientation.vertical` | moteur | menu_catalog.rs:461 |
| 14 | OpenType | Standard Ligatures | Ligatures standard |  | `type.openType.standardLigatures` | moteur | menu_catalog.rs:462 |
| 15 | OpenType | Contextual Alternates | Variantes contextuelles |  | `type.openType.contextualAlternates` | moteur | menu_catalog.rs:463 |
| 16 | OpenType | Discretionary Ligatures | Ligatures conditionnelles |  | `type.openType.discretionaryLigatures` | moteur | menu_catalog.rs:464 |
| 17 | OpenType | Swash | Lettres ornées |  | `type.openType.swash` | moteur | menu_catalog.rs:465 |
| 18 | OpenType | Oldstyle | Chiffres anciens |  | `type.openType.oldstyle` | moteur | menu_catalog.rs:466 |
| 19 | OpenType | Stylistic Alternates | Variantes stylistiques |  | `type.openType.stylisticAlternates` | moteur | menu_catalog.rs:467 |
| 20 | OpenType | Titling Alternates | Variantes de titrage |  | `type.openType.titlingAlternates` | moteur | menu_catalog.rs:468 |
| 21 | OpenType | Ornaments | Ornements |  | `type.openType.ornaments` | moteur | menu_catalog.rs:469 |
| 22 | OpenType | Ordinals | Ordinaux |  | `type.openType.ordinals` | moteur | menu_catalog.rs:470 |
| 23 | OpenType | Fractions | Fractions |  | `type.openType.fractions` | moteur | menu_catalog.rs:471 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:472 |
| 24 | — | Create Work Path | Créer un tracé de travail |  | `type.createWorkPath` | moteur | menu_catalog.rs:473 |
| 25 | — | Convert to Shape | Convertir en forme |  | `type.convertToShape` | moteur | menu_catalog.rs:474 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:475 |
| 26 | — | Rasterize Type Layer | Rastériser le calque de texte |  | `type.rasterizeTypeLayer` | moteur | menu_catalog.rs:476 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:477 |
| 27 | — | Convert to Paragraph Text | Convertir en texte de paragraphe |  | `type.convertToParagraphText` | moteur | menu_catalog.rs:478 |
| 28 | — | Convert to Point Text | Convertir en texte de point |  | `type.convertToPointText` | moteur | menu_catalog.rs:479 |
| 29 | — | Warp Text… | Déformer le texte… |  | `type.warpText` | moteur | menu_catalog.rs:480 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:481 |
| 30 | Font Preview Size (Taille de l'aperçu des polices) | Small | Petite |  | `type.fontPreviewSize.small` | shell UI (id cité dans ui-egui) | menu_catalog.rs:482 |
| 31 | Font Preview Size (Taille de l'aperçu des polices) | Medium | Moyenne |  | `type.fontPreviewSize.medium` | shell UI (id cité dans ui-egui) | menu_catalog.rs:483 |
| 32 | Font Preview Size (Taille de l'aperçu des polices) | Large | Grande |  | `type.fontPreviewSize.large` | shell UI (id cité dans ui-egui) | menu_catalog.rs:484 |
| 33 | Font Preview Size (Taille de l'aperçu des polices) | Extra Large | Très grande |  | `type.fontPreviewSize.extraLarge` | shell UI (id cité dans ui-egui) | menu_catalog.rs:485 |
| 34 | Font Preview Size (Taille de l'aperçu des polices) | Huge | Énorme |  | `type.fontPreviewSize.huge` | shell UI (id cité dans ui-egui) | menu_catalog.rs:486 |
| 35 | Language Options (Options de langue) | Default Features | Fonctionnalités par défaut |  | `type.languageOptions.defaultFeatures` | shell UI (id cité dans ui-egui) | menu_catalog.rs:487 |
| 36 | Language Options (Options de langue) | East Asian Features | Fonctionnalités d'Asie orientale |  | `type.languageOptions.eastAsianFeatures` | shell UI (id cité dans ui-egui) | menu_catalog.rs:488 |
| 37 | Language Options (Options de langue) | Middle Eastern Features | Fonctionnalités du Moyen-Orient |  | `type.languageOptions.middleEasternFeatures` | shell UI (id cité dans ui-egui) | menu_catalog.rs:489 |
| | Language Options | ——— séparateur ——— | | | | | menu_catalog.rs:490 |
| 38 | Language Options (Options de langue) | Middle Eastern & South Asian Composer | Composeur pour le Moyen-Orient et l'Asie du Sud |  | `type.languageOptions.middleEasternAndSouthAsianComposer` | shell UI (id cité dans ui-egui) | menu_catalog.rs:491 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:492 |
| 39 | — | Update All Text Layers | Mettre à jour tous les calques de texte |  | `type.updateAllTextLayers` | moteur | menu_catalog.rs:493 |
| 40 | — | Replace All Missing Fonts | Remplacer toutes les polices manquantes |  | `type.replaceAllMissingFonts` | moteur | menu_catalog.rs:494 |
| 41 | — | Resolve Missing Fonts… | Résoudre les polices manquantes… |  | `type.resolveMissingFonts` | moteur | menu_catalog.rs:495 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:496 |
| 42 | — | Paste Lorem Ipsum | Coller du Lorem Ipsum |  | `type.pasteLoremIpsum` | moteur | menu_catalog.rs:497 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:498 |
| 43 | — | Load Default Type Styles | Charger les styles de texte par défaut |  | `type.loadDefaultTypeStyles` | moteur | menu_catalog.rs:499 |
| 44 | — | Save Default Type Styles | Enregistrer les styles de texte par défaut |  | `type.saveDefaultTypeStyles` | moteur | menu_catalog.rs:500 |
| 45 | Anti-Alias (Lissage) | None | Aucun |  | `type.antiAlias.none` | moteur | type_extra_cmds.rs:519 |

### 1.6 Select — « Sélection » (25 entrées, 7 séparateurs)

| # | Chemin (sous-menu) | Libellé EN | Libellé FR (fr.tsv) | Raccourci | id de commande | Où l'id est implémenté (lecture statique) | Source |
|---|---|---|---|---|---|---|---|
| 1 | — | All | Tout sélectionner | Cmd+A | `select.all` | moteur | menu_catalog.rs:501 |
| 2 | — | Deselect | Désélectionner | Cmd+D | `select.deselect` | moteur | menu_catalog.rs:502 |
| 3 | — | Reselect | Resélectionner | Cmd+Shift+D | `select.reselect` | moteur | menu_catalog.rs:503 |
| 4 | — | Inverse Selection | Inverser la sélection |  | `select.inverse` | moteur | menu_catalog.rs:504 |
| 5 | — | Convert to Shape | Convertir en forme |  | `select.convertToShape` | moteur | menu_catalog.rs:505 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:506 |
| 6 | — | All Layers | Tous les calques | Cmd+Alt+A | `select.allLayers` | moteur | menu_catalog.rs:507 |
| 7 | — | Deselect Layers | Désélectionner les calques |  | `select.deselectLayers` | moteur | menu_catalog.rs:508 |
| 8 | — | Find Layers | Rechercher des calques | Cmd+Alt+Shift+F | `select.findLayers` | moteur | menu_catalog.rs:509 |
| 9 | — | Isolate Layers | Isoler les calques |  | `select.isolateLayers` | moteur | menu_catalog.rs:510 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:511 |
| 10 | — | Color Range… | Plage de couleurs… |  | `select.colorRange` | moteur | menu_catalog.rs:512 |
| 11 | — | Focus Area… | Zone de mise au point… |  | `select.focusArea` | moteur | menu_catalog.rs:513 |
| 12 | — | Subject | Sujet |  | `select.subject` | moteur | menu_catalog.rs:514 |
| 13 | — | Sky | Ciel |  | `select.sky` | moteur | menu_catalog.rs:515 |
| 14 | — | Select and Mask… | Sélectionner et masquer… |  | `select.selectAndMask` | UI_COMMANDS | menu_catalog.rs:516 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:517 |
| 15 | Modify (Modifier) | Border… | Bordure… |  | `select.modify.border` | moteur | menu_catalog.rs:518 |
| 16 | Modify (Modifier) | Smooth… | Lisser… |  | `select.modify.smooth` | moteur | menu_catalog.rs:519 |
| 17 | Modify (Modifier) | Expand… | Étendre… |  | `select.modify.expand` | moteur | menu_catalog.rs:520 |
| 18 | Modify (Modifier) | Contract… | Contracter… |  | `select.modify.contract` | moteur | menu_catalog.rs:521 |
| 19 | Modify (Modifier) | Feather… | Adoucir… | Shift+F6 | `select.modify.feather` | moteur | menu_catalog.rs:522 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:523 |
| 20 | — | Grow | Agrandir |  | `select.grow` | moteur | menu_catalog.rs:524 |
| 21 | — | Similar | Similaire |  | `select.similar` | moteur | menu_catalog.rs:525 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:526 |
| 22 | — | Transform Selection | Transformer la sélection |  | `select.transformSelection` | moteur | menu_catalog.rs:527 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:528 |
| 23 | — | Edit in Quick Mask Mode | Modifier en mode masque rapide | Q | `select.editInQuickMaskMode` | shell UI (id cité dans ui-egui) | menu_catalog.rs:529 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:530 |
| 24 | — | Load Selection… | Charger la sélection… |  | `select.loadSelection` | shell UI (id cité dans ui-egui) | menu_catalog.rs:531 |
| 25 | — | Save Selection… | Enregistrer la sélection… |  | `select.saveSelection` | shell UI (id cité dans ui-egui) | menu_catalog.rs:532 |

### 1.7 Filter — « Filtre » (76 entrées, 4 séparateurs)

| # | Chemin (sous-menu) | Libellé EN | Libellé FR (fr.tsv) | Raccourci | id de commande | Où l'id est implémenté (lecture statique) | Source |
|---|---|---|---|---|---|---|---|
| 1 | — | Last Filter | Dernier filtre | Cmd+Alt+F | `filter.lastFilter` | moteur | menu_catalog.rs:533 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:534 |
| 2 | — | Convert for Smart Filters | Convertir pour les filtres intelligents |  | `filter.convertForSmartFilters` | moteur | menu_catalog.rs:535 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:536 |
| 3 | — | Filter Gallery… | Galerie de filtres… |  | `filter.filterGallery` | moteur | menu_catalog.rs:537 |
| 4 | — | Camera Raw Filter… | Filtre Camera Raw… | Cmd+Shift+A | `filter.cameraRaw` | moteur | menu_catalog.rs:538 |
| 5 | — | Adaptive Wide Angle… | Grand angle adaptatif… | Cmd+Alt+Shift+A | `filter.adaptiveWideAngle` | moteur | menu_catalog.rs:539 |
| 6 | — | Lens Correction… | Correction de l'objectif… | Cmd+Shift+R | `filter.lensCorrection` | moteur | menu_catalog.rs:540 |
| 7 | — | Liquify… | Liquéfier… | Cmd+Shift+X | `filter.liquify` | moteur | menu_catalog.rs:541 |
| 8 | — | Vanishing Point… | Point de fuite… | Cmd+Alt+V | `filter.vanishingPoint` | moteur | menu_catalog.rs:542 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:543 |
| 9 | Blur (Flou) | Average | Moyenne |  | `filter.blur.average` | moteur | menu_catalog.rs:544 |
| 10 | Blur (Flou) | Blur | Flou |  | `filter.blur.blur` | moteur | menu_catalog.rs:545 |
| 11 | Blur (Flou) | Blur More | Flou accentué |  | `filter.blur.blurMore` | moteur | menu_catalog.rs:546 |
| 12 | Blur (Flou) | Box Blur… | Flou par boîte… |  | `filter.blur.boxBlur` | moteur | menu_catalog.rs:547 |
| 13 | Blur (Flou) | Gaussian Blur… | Flou gaussien… |  | `filter.blur.gaussianBlur` | moteur | menu_catalog.rs:548 |
| 14 | Blur (Flou) | Lens Blur… | Flou d'objectif… |  | `filter.blur.lensBlur` | moteur | menu_catalog.rs:549 |
| 15 | Blur (Flou) | Motion Blur… | Flou de mouvement… |  | `filter.blur.motionBlur` | moteur | menu_catalog.rs:550 |
| 16 | Blur (Flou) | Radial Blur… | Flou radial… |  | `filter.blur.radialBlur` | moteur | menu_catalog.rs:551 |
| 17 | Blur (Flou) | Shape Blur… | Flou selon une forme… |  | `filter.blur.shapeBlur` | moteur | menu_catalog.rs:552 |
| 18 | Blur (Flou) | Smart Blur… | Flou intelligent… |  | `filter.blur.smartBlur` | moteur | menu_catalog.rs:553 |
| 19 | Blur (Flou) | Surface Blur… | Flou de surface… |  | `filter.blur.surfaceBlur` | moteur | menu_catalog.rs:554 |
| 20 | Blur Gallery (Galerie de flous) | Field Blur… | Flou de champ… |  | `filter.blurGallery.fieldBlur` | moteur | menu_catalog.rs:555 |
| 21 | Blur Gallery (Galerie de flous) | Iris Blur… | Flou d'iris… |  | `filter.blurGallery.irisBlur` | moteur | menu_catalog.rs:556 |
| 22 | Blur Gallery (Galerie de flous) | Tilt-Shift… | Inclinaison-décalage… |  | `filter.blurGallery.tiltShift` | moteur | menu_catalog.rs:557 |
| 23 | Blur Gallery (Galerie de flous) | Path Blur… | Flou de tracé… |  | `filter.blurGallery.pathBlur` | moteur | menu_catalog.rs:558 |
| 24 | Blur Gallery (Galerie de flous) | Spin Blur… | Flou de rotation… |  | `filter.blurGallery.spinBlur` | moteur | menu_catalog.rs:559 |
| 25 | Distort (Déformation) | Displace… | Déplacement… |  | `filter.distort.displace` | moteur | menu_catalog.rs:560 |
| 26 | Distort (Déformation) | Pinch… | Pincement… |  | `filter.distort.pinch` | moteur | menu_catalog.rs:561 |
| 27 | Distort (Déformation) | Polar Coordinates… | Coordonnées polaires… |  | `filter.distort.polarCoordinates` | moteur | menu_catalog.rs:562 |
| 28 | Distort (Déformation) | Ripple… | Ondulation… |  | `filter.distort.ripple` | moteur | menu_catalog.rs:563 |
| 29 | Distort (Déformation) | Shear… | Cisaillement… |  | `filter.distort.shear` | moteur | menu_catalog.rs:564 |
| 30 | Distort (Déformation) | Spherize… | Sphérisation… |  | `filter.distort.spherize` | moteur | menu_catalog.rs:565 |
| 31 | Distort (Déformation) | Twirl… | Tourbillon… |  | `filter.distort.twirl` | moteur | menu_catalog.rs:566 |
| 32 | Distort (Déformation) | Wave… | Onde… |  | `filter.distort.wave` | moteur | menu_catalog.rs:567 |
| 33 | Distort (Déformation) | ZigZag… | Zigzag… |  | `filter.distort.zigZag` | moteur | menu_catalog.rs:568 |
| 34 | Noise (Bruit) | Add Noise… | Ajout de bruit… |  | `filter.noise.addNoise` | moteur | menu_catalog.rs:569 |
| 35 | Noise (Bruit) | Despeckle | Supprimer les mouchetures |  | `filter.noise.despeckle` | moteur | menu_catalog.rs:570 |
| 36 | Noise (Bruit) | Dust & Scratches… | Poussière et rayures… |  | `filter.noise.dustAndScratches` | moteur | menu_catalog.rs:571 |
| 37 | Noise (Bruit) | Median… | Médiane… |  | `filter.noise.median` | moteur | menu_catalog.rs:572 |
| 38 | Noise (Bruit) | Reduce Noise… | Réduction du bruit… |  | `filter.noise.reduceNoise` | moteur | menu_catalog.rs:573 |
| 39 | Pixelate (Pixeliser) | Color Halftone… | Trame de demi-teintes couleur… |  | `filter.pixelate.colorHalftone` | moteur | menu_catalog.rs:574 |
| 40 | Pixelate (Pixeliser) | Crystallize… | Cristallisation… |  | `filter.pixelate.crystallize` | moteur | menu_catalog.rs:575 |
| 41 | Pixelate (Pixeliser) | Facet | Facettes |  | `filter.pixelate.facet` | moteur | menu_catalog.rs:576 |
| 42 | Pixelate (Pixeliser) | Fragment | Fragmentation |  | `filter.pixelate.fragment` | moteur | menu_catalog.rs:577 |
| 43 | Pixelate (Pixeliser) | Mezzotint… | Manière noire… |  | `filter.pixelate.mezzotint` | moteur | menu_catalog.rs:578 |
| 44 | Pixelate (Pixeliser) | Mosaic… | Mosaïque… |  | `filter.pixelate.mosaic` | moteur | menu_catalog.rs:579 |
| 45 | Pixelate (Pixeliser) | Pointillize… | Pointillisme… |  | `filter.pixelate.pointillize` | moteur | menu_catalog.rs:580 |
| 46 | Render (Rendu) | Flame… | Flamme… |  | `filter.render.flame` | moteur | menu_catalog.rs:581 |
| 47 | Render (Rendu) | Picture Frame… | Cadre d'image… |  | `filter.render.pictureFrame` | moteur | menu_catalog.rs:582 |
| 48 | Render (Rendu) | Tree… | Arbre… |  | `filter.render.tree` | moteur | menu_catalog.rs:583 |
| | Render | ——— séparateur ——— | | | | | menu_catalog.rs:584 |
| 49 | Render (Rendu) | Clouds | Nuages |  | `filter.render.clouds` | moteur | menu_catalog.rs:585 |
| 50 | Render (Rendu) | Difference Clouds | Nuages par différence |  | `filter.render.differenceClouds` | moteur | menu_catalog.rs:586 |
| 51 | Render (Rendu) | Fibers… | Fibres… |  | `filter.render.fibers` | moteur | menu_catalog.rs:587 |
| 52 | Render (Rendu) | Lens Flare… | Reflet d'objectif… |  | `filter.render.lensFlare` | moteur | menu_catalog.rs:588 |
| 53 | Render (Rendu) | Lighting Effects… | Effets d'éclairage… |  | `filter.render.lightingEffects` | moteur | menu_catalog.rs:589 |
| 54 | Sharpen (Netteté) | Sharpen | Netteté |  | `filter.sharpen.sharpen` | moteur | menu_catalog.rs:590 |
| 55 | Sharpen (Netteté) | Sharpen Edges | Netteté des contours |  | `filter.sharpen.sharpenEdges` | moteur | menu_catalog.rs:591 |
| 56 | Sharpen (Netteté) | Sharpen More | Netteté accentuée |  | `filter.sharpen.sharpenMore` | moteur | menu_catalog.rs:592 |
| 57 | Sharpen (Netteté) | Smart Sharpen… | Netteté intelligente… |  | `filter.sharpen.smartSharpen` | moteur | menu_catalog.rs:593 |
| 58 | Sharpen (Netteté) | Unsharp Mask… | Masque flou… |  | `filter.sharpen.unsharpMask` | moteur | menu_catalog.rs:594 |
| 59 | Stylize (Styliser) | Diffuse… | Diffuser… |  | `filter.stylize.diffuse` | moteur | menu_catalog.rs:595 |
| 60 | Stylize (Styliser) | Emboss… | Relief… |  | `filter.stylize.emboss` | moteur | menu_catalog.rs:596 |
| 61 | Stylize (Styliser) | Extrude… | Extruder… |  | `filter.stylize.extrude` | moteur | menu_catalog.rs:597 |
| 62 | Stylize (Styliser) | Find Edges | Détecter les contours |  | `filter.stylize.findEdges` | moteur | menu_catalog.rs:598 |
| 63 | Stylize (Styliser) | Oil Paint… | Peinture à l'huile… |  | `filter.stylize.oilPaint` | moteur | menu_catalog.rs:599 |
| 64 | Stylize (Styliser) | Solarize | Solariser |  | `filter.stylize.solarize` | moteur | menu_catalog.rs:600 |
| 65 | Stylize (Styliser) | Tiles… | Carreaux… |  | `filter.stylize.tiles` | moteur | menu_catalog.rs:601 |
| 66 | Stylize (Styliser) | Trace Contour… | Tracer les contours… |  | `filter.stylize.traceContour` | moteur | menu_catalog.rs:602 |
| 67 | Stylize (Styliser) | Wind… | Vent… |  | `filter.stylize.wind` | moteur | menu_catalog.rs:603 |
| 68 | Video (Vidéo) | De-Interlace… | Désentrelacer… |  | `filter.video.deInterlace` | moteur | menu_catalog.rs:604 |
| 69 | Video (Vidéo) | NTSC Colors | Couleurs NTSC |  | `filter.video.ntscColors` | moteur | menu_catalog.rs:605 |
| 70 | Other… (Autre…) | Custom… | Personnalisé… |  | `filter.other.custom` | moteur | menu_catalog.rs:606 |
| 71 | Other… (Autre…) | HSB/HSL | TSL/TSI |  | `filter.other.hsbHsl` | moteur | menu_catalog.rs:607 |
| 72 | Other… (Autre…) | High Pass… | Passe-haut… |  | `filter.other.highPass` | moteur | menu_catalog.rs:608 |
| 73 | Other… (Autre…) | Maximum… | Maximum… |  | `filter.other.maximum` | moteur | menu_catalog.rs:609 |
| 74 | Other… (Autre…) | Minimum… | Minimum… |  | `filter.other.minimum` | moteur | menu_catalog.rs:610 |
| 75 | Other… (Autre…) | Offset… | Décalage… |  | `filter.other.offset` | moteur | menu_catalog.rs:611 |
| 76 | Plug-ins (Extensions) | Install Plug-in… | Installer une extension… |  | `plugin.install` | moteur | plugin_cmds.rs:239 |

### 1.8 View — « Affichage » (74 entrées, 16 séparateurs)

| # | Chemin (sous-menu) | Libellé EN | Libellé FR (fr.tsv) | Raccourci | id de commande | Où l'id est implémenté (lecture statique) | Source |
|---|---|---|---|---|---|---|---|
| 1 | Proof Setup (Configuration d'épreuve) | Custom… | Personnalisé… |  | `view.proofSetup.custom` | shell (alias) | menu_catalog.rs:612 |
| | Proof Setup | ——— séparateur ——— | | | | | menu_catalog.rs:613 |
| 2 | Proof Setup (Configuration d'épreuve) | Working CMYK | CMJN de travail |  | `view.proofSetup.workingCmyk` | shell (alias) | menu_catalog.rs:614 |
| 3 | Proof Setup (Configuration d'épreuve) | Working Cyan Plate | Plaque cyan de travail |  | `view.proofSetup.workingCyanPlate` | moteur | menu_catalog.rs:615 |
| 4 | Proof Setup (Configuration d'épreuve) | Working Magenta Plate | Plaque magenta de travail |  | `view.proofSetup.workingMagentaPlate` | moteur | menu_catalog.rs:616 |
| 5 | Proof Setup (Configuration d'épreuve) | Working Yellow Plate | Plaque jaune de travail |  | `view.proofSetup.workingYellowPlate` | moteur | menu_catalog.rs:617 |
| 6 | Proof Setup (Configuration d'épreuve) | Working Black Plate | Plaque noire de travail |  | `view.proofSetup.workingBlackPlate` | moteur | menu_catalog.rs:618 |
| 7 | Proof Setup (Configuration d'épreuve) | Working CMY Plate | Plaque CMJ de travail |  | `view.proofSetup.workingCmyPlate` | moteur | menu_catalog.rs:619 |
| | Proof Setup | ——— séparateur ——— | | | | | menu_catalog.rs:620 |
| 8 | Proof Setup (Configuration d'épreuve) | Legacy Macintosh RGB | RVB Macintosh (ancien) |  | `view.proofSetup.legacyMacintoshRgb` | moteur | menu_catalog.rs:621 |
| 9 | Proof Setup (Configuration d'épreuve) | Internet Standard RGB | RVB standard d'Internet |  | `view.proofSetup.internetStandardRgb` | shell (alias) | menu_catalog.rs:622 |
| 10 | Proof Setup (Configuration d'épreuve) | Monitor RGB | RVB du moniteur |  | `view.proofSetup.monitorRgb` | shell (alias) | menu_catalog.rs:623 |
| | Proof Setup | ——— séparateur ——— | | | | | menu_catalog.rs:624 |
| 11 | Proof Setup (Configuration d'épreuve) | Color Blindness — Protanopia-type | Daltonisme — type protanopie |  | `view.proofSetup.colorBlindnessProtanopia` | moteur | menu_catalog.rs:625 |
| 12 | Proof Setup (Configuration d'épreuve) | Color Blindness — Deuteranopia-type | Daltonisme — type deutéranopie |  | `view.proofSetup.colorBlindnessDeuteranopia` | moteur | menu_catalog.rs:626 |
| 13 | — | Proof Colors | Couleurs d'épreuve | Cmd+Y | `view.proofColors` | moteur | menu_catalog.rs:627 |
| 14 | — | Gamut Warning | Alerte de gamut | Cmd+Shift+Y | `view.gamutWarning` | moteur | menu_catalog.rs:628 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:629 |
| 15 | Pixel Aspect Ratio (Format des pixels) | Custom Pixel Aspect Ratio… | Format des pixels personnalisé… |  | `view.pixelAspectRatio.custom` | shell UI (id cité dans ui-egui) | menu_catalog.rs:630 |
| | Pixel Aspect Ratio | ——— séparateur ——— | | | | | menu_catalog.rs:631 |
| 16 | Pixel Aspect Ratio (Format des pixels) | Square | Carré |  | `view.pixelAspectRatio.square` | shell UI (id cité dans ui-egui) | menu_catalog.rs:632 |
| 17 | Pixel Aspect Ratio (Format des pixels) | D1/DV NTSC (0.91) | D1/DV NTSC (0,91) |  | `view.pixelAspectRatio.d1DvNtsc` | shell UI (id cité dans ui-egui) | menu_catalog.rs:633 |
| 18 | Pixel Aspect Ratio (Format des pixels) | D1/DV PAL (1.09) | D1/DV PAL (1,09) |  | `view.pixelAspectRatio.d1DvPal` | shell UI (id cité dans ui-egui) | menu_catalog.rs:634 |
| 19 | Pixel Aspect Ratio (Format des pixels) | D1/DV NTSC Widescreen (1.21) | D1/DV NTSC grand écran (1,21) |  | `view.pixelAspectRatio.d1DvNtscWidescreen` | shell UI (id cité dans ui-egui) | menu_catalog.rs:635 |
| 20 | Pixel Aspect Ratio (Format des pixels) | HDV 1080/DVCPRO HD 720 (1.33) | HDV 1080/DVCPRO HD 720 (1,33) |  | `view.pixelAspectRatio.hdv1080` | shell UI (id cité dans ui-egui) | menu_catalog.rs:636 |
| 21 | Pixel Aspect Ratio (Format des pixels) | D1/DV PAL Widescreen (1.46) | D1/DV PAL grand écran (1,46) |  | `view.pixelAspectRatio.d1DvPalWidescreen` | shell UI (id cité dans ui-egui) | menu_catalog.rs:637 |
| 22 | Pixel Aspect Ratio (Format des pixels) | DVCPRO HD 1080/HDV 1080 (1.5) | DVCPRO HD 1080/HDV 1080 (1,5) |  | `view.pixelAspectRatio.dvcproHd1080` | shell UI (id cité dans ui-egui) | menu_catalog.rs:638 |
| 23 | Pixel Aspect Ratio (Format des pixels) | Anamorphic 2:1 (2) | Anamorphique 2:1 (2) |  | `view.pixelAspectRatio.anamorphic2To1` | shell UI (id cité dans ui-egui) | menu_catalog.rs:639 |
| 24 | — | Pixel Aspect Ratio Correction | Correction du format des pixels |  | `view.pixelAspectRatioCorrection` | shell UI (id cité dans ui-egui) | menu_catalog.rs:640 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:641 |
| 25 | — | 32-bit Preview Options… | Options d'aperçu 32 bits… |  | `view.thirtyTwoBitPreviewOptions` | moteur | menu_catalog.rs:642 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:643 |
| 26 | — | Zoom In | Zoom avant | Cmd+= | `view.zoomIn` | UI_COMMANDS | menu_catalog.rs:644 |
| 27 | — | Zoom Out | Zoom arrière | Cmd+- | `view.zoomOut` | UI_COMMANDS | menu_catalog.rs:645 |
| 28 | — | Fit on Screen | Adapter à l'écran |  | `view.fitOnScreen` | UI_COMMANDS | menu_catalog.rs:646 |
| 29 | — | Fit Layer(s) on Screen | Adapter le(s) calque(s) à l'écran |  | `view.fitLayersOnScreen` | shell UI (id cité dans ui-egui) | menu_catalog.rs:647 |
| 30 | — | Fit Artboard on Screen | Adapter le plan de travail à l'écran |  | `view.fitArtboardOnScreen` | shell UI (id cité dans ui-egui) | menu_catalog.rs:648 |
| 31 | — | 100% | 100 % | Cmd+1 | `view.actualPixels` | UI_COMMANDS | menu_catalog.rs:649 |
| 32 | — | 200% | 200 % |  | `view.twoHundredPercent` | shell UI (id cité dans ui-egui) | menu_catalog.rs:650 |
| 33 | — | Print Size | Taille d'impression |  | `view.printSize` | shell UI (id cité dans ui-egui) | menu_catalog.rs:651 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:652 |
| 34 | — | Flip Horizontal | Symétrie horizontale |  | `view.flipHorizontal` | shell UI (id cité dans ui-egui) | menu_catalog.rs:653 |
| 35 | Screen Mode (Mode d'écran) | Standard Screen Mode | Mode d'écran standard |  | `view.screenMode.standard` | shell UI (id cité dans ui-egui) | menu_catalog.rs:654 |
| 36 | Screen Mode (Mode d'écran) | Full Screen Mode With Menu Bar | Mode plein écran avec barre de menus |  | `view.screenMode.fullScreenWithMenuBar` | shell UI (id cité dans ui-egui) | menu_catalog.rs:655 |
| 37 | Screen Mode (Mode d'écran) | Full Screen Mode | Mode plein écran |  | `view.screenMode.fullScreen` | shell UI (id cité dans ui-egui) | menu_catalog.rs:656 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:657 |
| 38 | — | Extras | Extras | Cmd+H | `view.extras` | UI_COMMANDS | menu_catalog.rs:658 |
| 39 | Show (Afficher) | Layer Edges | Contours du calque |  | `view.show.layerEdges` | shell UI (id cité dans ui-egui) | menu_catalog.rs:659 |
| 40 | Show (Afficher) | Selection Edges | Contours de la sélection |  | `view.show.selectionEdges` | shell UI (id cité dans ui-egui) | menu_catalog.rs:660 |
| 41 | Show (Afficher) | Target Path | Tracé cible | Cmd+Shift+H | `view.show.targetPath` | UI_COMMANDS | menu_catalog.rs:661 |
| 42 | Show (Afficher) | Grid | Grille | Cmd+' | `view.show.grid` | UI_COMMANDS | menu_catalog.rs:662 |
| 43 | Show (Afficher) | Guides | Repères | Cmd+; | `view.show.guides` | UI_COMMANDS | menu_catalog.rs:663 |
| 44 | Show (Afficher) | Canvas Guides | Repères du canevas |  | `view.show.canvasGuides` | shell UI (id cité dans ui-egui) | menu_catalog.rs:664 |
| 45 | Show (Afficher) | Artboard Guides | Repères du plan de travail |  | `view.show.artboardGuides` | shell UI (id cité dans ui-egui) | menu_catalog.rs:665 |
| 46 | Show (Afficher) | Count | Compteur |  | `view.show.count` | shell UI (id cité dans ui-egui) | menu_catalog.rs:666 |
| 47 | Show (Afficher) | Smart Guides | Repères intelligents |  | `view.show.smartGuides` | shell UI (id cité dans ui-egui) | menu_catalog.rs:667 |
| 48 | Show (Afficher) | Slices | Tranches |  | `view.show.slices` | shell UI (id cité dans ui-egui) | menu_catalog.rs:668 |
| 49 | Show (Afficher) | Notes | Notes |  | `view.show.notes` | shell UI (id cité dans ui-egui) | menu_catalog.rs:669 |
| 50 | Show (Afficher) | Pixel Grid | Grille de pixels |  | `view.show.pixelGrid` | shell UI (id cité dans ui-egui) | menu_catalog.rs:670 |
| 51 | Show (Afficher) | Brush Preview | Aperçu du pinceau |  | `view.show.brushPreview` | shell UI (id cité dans ui-egui) | menu_catalog.rs:671 |
| 52 | Show (Afficher) | Mesh | Maillage |  | `view.show.mesh` | shell UI (id cité dans ui-egui) | menu_catalog.rs:672 |
| 53 | Show (Afficher) | Edit Pins | Modifier les épingles |  | `view.show.editPins` | shell UI (id cité dans ui-egui) | menu_catalog.rs:673 |
| | Show | ——— séparateur ——— | | | | | menu_catalog.rs:674 |
| 54 | Show (Afficher) | All | Tout |  | `view.show.all` | shell UI (id cité dans ui-egui) | menu_catalog.rs:675 |
| 55 | Show (Afficher) | Show Extras Options… | Options d'affichage des extras… |  | `view.show.showExtrasOptions` | shell UI (id cité dans ui-egui) | menu_catalog.rs:676 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:677 |
| 56 | — | Rulers | Règles | Cmd+R | `view.rulers` | UI_COMMANDS | menu_catalog.rs:678 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:679 |
| 57 | — | Snap | Aimanter | Cmd+Shift+; | `view.snap` | UI_COMMANDS | menu_catalog.rs:680 |
| 58 | Snap To (Aimanter à) | Guides | Repères |  | `view.snapTo.guides` | shell UI (id cité dans ui-egui) | menu_catalog.rs:681 |
| 59 | Snap To (Aimanter à) | Grid | Grille |  | `view.snapTo.grid` | shell UI (id cité dans ui-egui) | menu_catalog.rs:682 |
| 60 | Snap To (Aimanter à) | Layers | Calques |  | `view.snapTo.layers` | shell UI (id cité dans ui-egui) | menu_catalog.rs:683 |
| 61 | Snap To (Aimanter à) | Slices | Tranches |  | `view.snapTo.slices` | shell UI (id cité dans ui-egui) | menu_catalog.rs:684 |
| 62 | Snap To (Aimanter à) | Document Bounds | Limites du document |  | `view.snapTo.documentBounds` | shell UI (id cité dans ui-egui) | menu_catalog.rs:685 |
| | Snap To | ——— séparateur ——— | | | | | menu_catalog.rs:686 |
| 63 | Snap To (Aimanter à) | All | Tout |  | `view.snapTo.all` | shell UI (id cité dans ui-egui) | menu_catalog.rs:687 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:688 |
| 64 | — | Lock Guides | Verrouiller les repères | Cmd+Alt+; | `view.lockGuides` | UI_COMMANDS | menu_catalog.rs:689 |
| 65 | — | Clear Guides | Effacer les repères |  | `view.clearGuides` | moteur | menu_catalog.rs:690 |
| 66 | — | Clear Selected Artboard Guides | Effacer les repères du plan de travail sélectionné |  | `view.clearSelectedArtboardGuides` | moteur | menu_catalog.rs:691 |
| 67 | — | Clear Canvas Guides | Effacer les repères du canevas |  | `view.clearCanvasGuides` | moteur | menu_catalog.rs:692 |
| 68 | — | New Guide… | Nouveau repère… |  | `view.newGuide` | moteur | menu_catalog.rs:693 |
| 69 | — | New Guide Layout… | Nouvelle disposition de repères… |  | `view.newGuideLayout` | moteur | menu_catalog.rs:694 |
| 70 | — | New Guides From Shape | Nouveaux repères d'après la forme |  | `view.newGuidesFromShape` | moteur | menu_catalog.rs:695 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:696 |
| 71 | — | Lock Slices | Verrouiller les tranches |  | `view.lockSlices` | moteur | menu_catalog.rs:697 |
| 72 | — | Clear Slices | Effacer les tranches |  | `view.clearSlices` | moteur | menu_catalog.rs:698 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:699 |
| 73 | — | Pattern Preview | Aperçu du motif |  | `view.patternPreview` | shell UI (id cité dans ui-egui) | menu_catalog.rs:700 |
| 74 | — | Pixel Art Preview | Aperçu pixel art |  | `view.pixelArtPreview` | shell UI (id cité dans ui-egui) | menu_catalog.rs:701 |

### 1.9 Window — « Fenêtre » (68 entrées, 8 séparateurs)

| # | Chemin (sous-menu) | Libellé EN | Libellé FR (fr.tsv) | Raccourci | id de commande | Où l'id est implémenté (lecture statique) | Source |
|---|---|---|---|---|---|---|---|
| 1 | Arrange (Organiser) | Tile All Vertically | Tout en mosaïque verticale |  | `window.arrange.tileAllVertically` | shell UI (id cité dans ui-egui) | menu_catalog.rs:702 |
| 2 | Arrange (Organiser) | Tile All Horizontally | Tout en mosaïque horizontale |  | `window.arrange.tileAllHorizontally` | shell UI (id cité dans ui-egui) | menu_catalog.rs:703 |
| 3 | Arrange (Organiser) | 2-up Vertical | 2 vignettes verticales |  | `window.arrange.twoUpVertical` | shell UI (id cité dans ui-egui) | menu_catalog.rs:704 |
| 4 | Arrange (Organiser) | 2-up Horizontal | 2 vignettes horizontales |  | `window.arrange.twoUpHorizontal` | shell UI (id cité dans ui-egui) | menu_catalog.rs:705 |
| 5 | Arrange (Organiser) | 3-up Vertical | 3 vignettes verticales |  | `window.arrange.threeUpVertical` | shell UI (id cité dans ui-egui) | menu_catalog.rs:706 |
| 6 | Arrange (Organiser) | 3-up Horizontal | 3 vignettes horizontales |  | `window.arrange.threeUpHorizontal` | shell UI (id cité dans ui-egui) | menu_catalog.rs:707 |
| 7 | Arrange (Organiser) | 3-up Stacked | 3 vignettes empilées |  | `window.arrange.threeUpStacked` | shell UI (id cité dans ui-egui) | menu_catalog.rs:708 |
| 8 | Arrange (Organiser) | 4-up | 4 vignettes |  | `window.arrange.fourUp` | shell UI (id cité dans ui-egui) | menu_catalog.rs:709 |
| 9 | Arrange (Organiser) | 6-up | 6 vignettes |  | `window.arrange.sixUp` | shell UI (id cité dans ui-egui) | menu_catalog.rs:710 |
| | Arrange | ——— séparateur ——— | | | | | menu_catalog.rs:711 |
| 10 | Arrange (Organiser) | Consolidate All to Tabs | Tout regrouper dans des onglets |  | `window.arrange.consolidateAllToTabs` | shell UI (id cité dans ui-egui) | menu_catalog.rs:712 |
| 11 | Arrange (Organiser) | Cascade | Cascade |  | `window.arrange.cascade` | shell UI (id cité dans ui-egui) | menu_catalog.rs:713 |
| 12 | Arrange (Organiser) | Tile | Mosaïque |  | `window.arrange.tile` | shell UI (id cité dans ui-egui) | menu_catalog.rs:714 |
| | Arrange | ——— séparateur ——— | | | | | menu_catalog.rs:715 |
| 13 | Arrange (Organiser) | Float in Window | Flottante dans une fenêtre |  | `window.arrange.floatInWindow` | shell UI (id cité dans ui-egui) | menu_catalog.rs:716 |
| 14 | Arrange (Organiser) | Float All in Windows | Toutes flottantes dans des fenêtres |  | `window.arrange.floatAllInWindows` | shell UI (id cité dans ui-egui) | menu_catalog.rs:717 |
| | Arrange | ——— séparateur ——— | | | | | menu_catalog.rs:718 |
| 15 | Arrange (Organiser) | New Window for Document | Nouvelle fenêtre pour le document |  | `window.arrange.newWindowForDocument` | shell UI (id cité dans ui-egui) | menu_catalog.rs:719 |
| | Arrange | ——— séparateur ——— | | | | | menu_catalog.rs:720 |
| 16 | Arrange (Organiser) | Match Zoom | Faire correspondre le zoom |  | `window.arrange.matchZoom` | shell UI (id cité dans ui-egui) | menu_catalog.rs:721 |
| 17 | Arrange (Organiser) | Match Location | Faire correspondre la position |  | `window.arrange.matchLocation` | shell UI (id cité dans ui-egui) | menu_catalog.rs:722 |
| 18 | Arrange (Organiser) | Match Rotation | Faire correspondre la rotation |  | `window.arrange.matchRotation` | shell UI (id cité dans ui-egui) | menu_catalog.rs:723 |
| 19 | Arrange (Organiser) | Match All | Tout faire correspondre |  | `window.arrange.matchAll` | shell UI (id cité dans ui-egui) | menu_catalog.rs:724 |
| 20 | Workspace (Espace de travail) | Essentials | Essentiel |  | `window.workspace.essentials` | shell (alias) | menu_catalog.rs:725 |
| 21 | Workspace (Espace de travail) | Photography | Photographie |  | `window.workspace.photography` | shell (alias) | menu_catalog.rs:726 |
| 22 | Workspace (Espace de travail) | Painting | Peinture |  | `window.workspace.painting` | shell (alias) | menu_catalog.rs:727 |
| 23 | Workspace (Espace de travail) | Pixel Art | Pixel art |  | `window.workspace.pixelArt` | shell (alias) | menu_catalog.rs:728 |
| 24 | Workspace (Espace de travail) | Graphic and Web | Graphisme et Web |  | `window.workspace.graphicAndWeb` | shell (alias) | menu_catalog.rs:729 |
| 25 | Workspace (Espace de travail) | Motion | Mouvement |  | `window.workspace.motion` | shell (alias) | menu_catalog.rs:730 |
| | Workspace | ——— séparateur ——— | | | | | menu_catalog.rs:731 |
| 26 | Workspace (Espace de travail) | Reset Workspace | Réinitialiser l'espace de travail |  | `window.workspace.resetWorkspace` | shell (alias) | menu_catalog.rs:732 |
| 27 | Workspace (Espace de travail) | New Workspace… | Nouvel espace de travail… |  | `window.workspace.newWorkspace` | shell (alias) | menu_catalog.rs:733 |
| 28 | Workspace (Espace de travail) | Delete Workspace… | Supprimer l'espace de travail… |  | `window.workspace.deleteWorkspace` | shell (alias) | menu_catalog.rs:734 |
| | Workspace | ——— séparateur ——— | | | | | menu_catalog.rs:735 |
| 29 | Workspace (Espace de travail) | Keyboard Shortcuts… | Raccourcis clavier… | Cmd+Alt+Shift+K | `edit.keyboardShortcuts` | moteur | menu_catalog.rs:736 |
| 30 | Workspace (Espace de travail) | Lock Workspace | Verrouiller l'espace de travail |  | `window.workspace.lockWorkspace` | shell (alias) | menu_catalog.rs:737 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:738 |
| 31 | — | Actions | Actions | Alt+F9 | `window.panel.actions` | shell (alias) | menu_catalog.rs:739 |
| 32 | — | Adjustments | Ajustements |  | `window.panel.adjustments` | shell (alias) | menu_catalog.rs:740 |
| 33 | — | Brush Settings | Paramètres du pinceau | F5 | `window.panel.brushSettings` | shell (alias) | menu_catalog.rs:741 |
| 34 | — | Brushes | Pinceaux |  | `window.panel.brushes` | shell (alias) | menu_catalog.rs:742 |
| 35 | — | Channels | Canaux |  | `window.panel.channels` | shell (alias) | menu_catalog.rs:743 |
| 36 | — | Character | Caractère |  | `window.panel.character` | shell (alias) | menu_catalog.rs:744 |
| 37 | — | Character Styles | Styles de caractère |  | `window.panel.characterStyles` | shell (alias) | menu_catalog.rs:745 |
| 38 | — | Clone Source | Source de clonage |  | `window.panel.cloneSource` | shell (alias) | menu_catalog.rs:746 |
| 39 | — | Color | Couleur | F6 | `window.panel.color` | shell (alias) | menu_catalog.rs:747 |
| 40 | — | Glyphs | Glyphes |  | `window.panel.glyphs` | shell (alias) | menu_catalog.rs:748 |
| 41 | — | Gradients | Dégradés |  | `window.panel.gradients` | shell (alias) | menu_catalog.rs:749 |
| 42 | — | Histogram | Histogramme |  | `window.panel.histogram` | shell (alias) | menu_catalog.rs:750 |
| 43 | — | History | Historique |  | `window.panel.history` | shell (alias) | menu_catalog.rs:751 |
| 44 | — | Info | Infos | F8 | `window.panel.info` | shell (alias) | menu_catalog.rs:752 |
| 45 | — | Layer Comps | Compositions de calques |  | `window.panel.layerComps` | shell (alias) | menu_catalog.rs:753 |
| 46 | — | Layers | Calques | F7 | `window.panel.layers` | shell (alias) | menu_catalog.rs:754 |
| 47 | — | Measurement Log | Journal des mesures |  | `window.panel.measurementLog` | shell (alias) | menu_catalog.rs:755 |
| 48 | — | Modifier Keys | Touches de modification |  | `window.panel.modifierKeys` | shell (alias) | menu_catalog.rs:756 |
| 49 | — | Navigator | Navigation |  | `window.panel.navigator` | shell (alias) | menu_catalog.rs:757 |
| 50 | — | Notes | Notes |  | `window.panel.notes` | shell (alias) | menu_catalog.rs:758 |
| 51 | — | Paragraph | Paragraphe |  | `window.panel.paragraph` | shell (alias) | menu_catalog.rs:759 |
| 52 | — | Paragraph Styles | Styles de paragraphe |  | `window.panel.paragraphStyles` | shell (alias) | menu_catalog.rs:760 |
| 53 | — | Paths | Tracés |  | `window.panel.paths` | shell (alias) | menu_catalog.rs:761 |
| 54 | — | Patterns | Motifs |  | `window.panel.patterns` | shell (alias) | menu_catalog.rs:762 |
| 55 | — | Properties | Propriétés |  | `window.panel.properties` | shell (alias) | menu_catalog.rs:763 |
| 56 | — | Shapes | Formes |  | `window.panel.shapes` | shell (alias) | menu_catalog.rs:764 |
| 57 | — | Styles | Styles |  | `window.panel.styles` | shell (alias) | menu_catalog.rs:765 |
| 58 | — | Swatches | Nuancier |  | `window.panel.swatches` | shell (alias) | menu_catalog.rs:766 |
| 59 | — | Timeline | Montage |  | `window.panel.timeline` | shell (alias) | menu_catalog.rs:767 |
| 60 | — | Tool Presets | Préréglages d'outils |  | `window.panel.toolPresets` | shell (alias) | menu_catalog.rs:768 |
| | — | ——— séparateur ——— | | | | | menu_catalog.rs:769 |
| 61 | — | Options | Options |  | `window.panel.options` | shell (alias) | menu_catalog.rs:770 |
| 62 | — | Tools | Outils |  | `window.panel.tools` | shell (alias) | menu_catalog.rs:771 |
| 63 | — | Next Theme | Thème suivant |  | `window.theme.toggle` | UI_COMMANDS | menus.rs:49 |
| 64 | Theme (Thème) | Pro Theme | Thème Pro |  | `window.theme.pro` | UI_COMMANDS | menus.rs:50 |
| 65 | Theme (Thème) | Pro Medium Gray Theme | Thème Pro gris moyen |  | `window.theme.proMedium` | UI_COMMANDS | menus.rs:51 |
| 66 | Theme (Thème) | Studio Theme | Thème Studio |  | `window.theme.studio` | UI_COMMANDS | menus.rs:52 |
| 67 | Theme (Thème) | Studio Light Theme | Thème Studio clair |  | `window.theme.studioLight` | UI_COMMANDS | menus.rs:53 |
| 68 | Theme (Thème) | Classic Theme | Thème Classique |  | `window.theme.classic` | UI_COMMANDS | menus.rs:54 |

### 1.10 Help — « Aide » (7 entrées, 1 séparateurs)

| # | Chemin (sous-menu) | Libellé EN | Libellé FR (fr.tsv) | Raccourci | id de commande | Où l'id est implémenté (lecture statique) | Source |
|---|---|---|---|---|---|---|---|
| 1 | — | Join the ArtCraft Discord… | Rejoindre le Discord d'ArtCraft… |  | `help.discord` | UI_COMMANDS | menus.rs:56 |
| 2 | — | PhotoCraft Website | Site web de PhotoCraft |  | `help.website` | UI_COMMANDS | menus.rs:57 |
| 3 | — | ArtCraft Website | Site web d'ArtCraft |  | `help.artcraftWebsite` | UI_COMMANDS | menus.rs:58 |
| 4 | — | PhotoCraft on GitHub | PhotoCraft sur GitHub |  | `help.github` | UI_COMMANDS | menus.rs:59 |
| 5 | — | Report an Issue… | Signaler un problème… |  | `help.reportIssue` | UI_COMMANDS | menus.rs:60 |
| | — | ——— séparateur ——— | | | | | menus.rs:697-703 |
| 6 | — | System Info… | Informations système… |  | `help.systemInfo` | UI_COMMANDS | menus.rs:61 |
| 7 | — | About PhotoCraft | À propos de PhotoCraft |  | `help.about` | UI_COMMANDS | menus.rs:62 |

## 2. Outils de la barre d'outils

Source : `crates/ui-egui/src/state.rs:48-94` (enum `Tool`, 45 outils), `state.rs:97-143` (`Tool::ALL`), `state.rs:145-191` (libellés), `state.rs:213-237` (touches), `crates/ui-egui/src/icons.rs:60-107` (icône), `crates/ui-egui/src/panels.rs:17-44` (sections et emplacements), `panels.rs:54-233` (rendu). Les icônes sont des SVG Lucide (licence ISC) dans `assets/icons/<nom>.svg`, 112 fichiers, embarqués par `crates/ui-egui/src/icon_data.rs` (112 `include_bytes!`), recolorés en blanc puis teintés, trait ramené de 2 à 1,75 (`icons.rs:16-27`).

### 2.1 Disposition (lu)
- Une colonne ; elle passe à deux colonnes seulement si la hauteur ne suffit pas (`toolbar_needs_double`, `panels.rs:237-246`).
- Largeur : 40 px (Pro) / 50 px (Studio, Classic) ; bouton d'outil 30 px (Pro) / 36 px ; marge horizontale 5 / 7 px (`panels.rs:56`). En double colonne : `w1 + bx + 2`.
- En Pro : en-tête « chevrons-right » (11 px) en haut, aucun séparateur entre sections (« Photoshop 2026 draws one uninterrupted column », `panels.rs:91-97`) ; en Studio/Classic un trait entre sections.
- Triangle de coin (6 px) sur tout emplacement contenant plusieurs outils (`panels.rs:108-112`).
- Clic droit ou appui long > 0,35 s : menu déroulant (« flyout ») listant icône 14 px, libellé (12,5 px), touche à droite, puce carrée devant l'outil courant ; largeur ≥ 180 px, rangée 26 px (`panels.rs:116-186`). L'emplacement affiche le dernier outil utilisé du groupe (`slot_tool`, `panels.rs:46-52`).
- Infobulle : « {libellé}  ({touche}) » (`panels.rs:106`).
- Sous les outils (Pro) : bouton « … » `ellipsis` → `edit.toolbar` « Edit Toolbar… » (`panels.rs:191-193`) ; pastilles premier plan / arrière-plan 21×21 décalées de 11 px, rayon 5 (`panels.rs:252-282`) ; bouton Masque rapide `square-dashed` « Edit in Quick Mask Mode  (Q) » → `select.editInQuickMaskMode` ; bouton Mode d'écran `app-window` « Change Screen Mode  (F) » → `view.screenMode.cycle`, clic droit : Standard Screen Mode / Full Screen Mode With Menu Bar / Full Screen Mode (`panels.rs:196-230`).

### 2.2 Les 45 outils, par section et emplacement (ordre `TOOL_SECTIONS`, `panels.rs:17-44`)

| Section | Emplacement (flyout) | Outil (`Tool::`) | Libellé EN | Libellé FR (fr.tsv) | Touche | Icône (`assets/icons/…svg`) |
|---|---|---|---|---|---|---|
| 1 | 1 | Move | Move Tool | Outil Déplacement | V | move |
| 2 | 2 | RectMarquee | Rectangular Marquee Tool | Outil Sélection rectangulaire | M | square-dashed |
| 2 | 2 | EllipseMarquee | Elliptical Marquee Tool | Outil Sélection elliptique | M | circle-dashed |
| 2 | 3 | Lasso | Lasso Tool | Outil Lasso | L | lasso |
| 2 | 3 | PolygonLasso | Polygonal Lasso Tool | Outil Lasso polygonal | L | pentagon |
| 2 | 4 | ObjectSelection | Object Selection Tool | Outil Sélection d'objet | W | square-dashed-mouse-pointer |
| 2 | 4 | QuickSelection | Quick Selection Tool | Outil Sélection rapide | W | circle-dashed |
| 2 | 4 | MagicWand | Magic Wand Tool | Outil Baguette magique | W | wand-sparkles |
| 2 | 5 | Crop | Crop Tool | Outil Recadrage | C | crop |
| 2 | 5 | Slice | Slice Tool | Outil Tranche | C | slice-knife |
| 2 | 5 | SliceSelect | Slice Select Tool | Outil Sélection de tranche | C | square-dashed-mouse-pointer |
| 2 | 6 | Eyedropper | Eyedropper Tool | Outil Pipette | I | pipette |
| 2 | 6 | Ruler | Ruler Tool | Outil Règle | I | ruler |
| 2 | 6 | Note | Note Tool | Outil Note | I | message-square |
| 2 | 6 | Count | Count Tool | Outil Compteur | I | circle-dot |
| 3 | 7 | SpotHealing | Spot Healing Brush Tool | Outil Correcteur localisé | J | bandage |
| 3 | 7 | Healing | Healing Brush Tool | Outil Pinceau correcteur | J | bandage |
| 3 | 7 | Patch | Patch Tool | Outil Pièce | J | lasso-select |
| 3 | 8 | Brush | Brush Tool | Outil Pinceau | B | brush |
| 3 | 8 | Pencil | Pencil Tool | Outil Crayon | B | pencil |
| 3 | 8 | MixerBrush | Mixer Brush Tool | Outil Pinceau mélangeur | B | palette |
| 3 | 9 | CloneStamp | Clone Stamp Tool | Outil Tampon de clonage | S | stamp |
| 3 | 10 | HistoryBrush | History Brush Tool | Outil Pinceau d'historique | Y | clock |
| 3 | 11 | Eraser | Eraser Tool | Outil Gomme | E | eraser |
| 3 | 11 | BackgroundEraser | Background Eraser Tool | Outil Gomme d'arrière-plan | E | eraser-background |
| 3 | 11 | MagicEraser | Magic Eraser Tool | Outil Gomme magique | E | eraser-magic |
| 3 | 12 | Gradient | Gradient Tool | Outil Dégradé | G | blend |
| 3 | 12 | PaintBucket | Paint Bucket Tool | Outil Pot de peinture | G | paint-bucket |
| 3 | 13 | Blur | Blur Tool | Outil Flou | (aucune, `'\0'`) | droplet |
| 3 | 13 | Sharpen | Sharpen Tool | Outil Netteté | (aucune) | triangle |
| 3 | 13 | Smudge | Smudge Tool | Outil Doigt | (aucune) | pointer |
| 3 | 14 | Dodge | Dodge Tool | Outil Éclaircir | O | lollipop |
| 3 | 14 | Burn | Burn Tool | Outil Assombrir | O | flame |
| 3 | 14 | Sponge | Sponge Tool | Outil Éponge | O | cloud |
| 4 | 15 | Pen | Pen Tool | Outil Plume | P | pen-tool |
| 4 | 16 | Type | Horizontal Type Tool | Outil Texte horizontal | T | type |
| 4 | 17 | PathSelection | Path Selection Tool | Outil Sélection de tracé | A | mouse-pointer-2 |
| 4 | 18 | Rectangle | Rectangle Tool | Outil Rectangle | U | rectangle-horizontal |
| 4 | 18 | EllipseShape | Ellipse Tool | Outil Ellipse | U | circle |
| 4 | 18 | Triangle | Triangle Tool | Outil Triangle | U | triangle |
| 4 | 18 | Polygon | Polygon Tool | Outil Polygone | U | pentagon |
| 4 | 18 | Line | Line Tool | Outil Trait | U | slash |
| 4 | 18 | CustomShape | Custom Shape Tool | Outil Forme personnalisée | U | cloud |
| 5 | 19 | Hand | Hand Tool | Outil Main | H | hand |
| 5 | 20 | Zoom | Zoom Tool | Outil Zoom | Z | zoom-in |

Les libellés FR de cette table sont lus dans `crates/ui-egui/src/i18n/fr.tsv` (entrée sans contexte dont la source est le libellé EN) et vérifiés par script. Un champ `glyph()` hérité (`state.rs:239-257`) n'est plus utilisé pour le rendu (icônes vectorielles).

Valeurs par défaut des options (struct `ToolOptions`, `state.rs:330-475`, `Default` `state.rs:476-528`) : tolerance 32 ; contiguous oui ; anti_alias oui ; sample_all_layers non ; feather 0 ; gradient_style "linear" ; gradient_reverse non ; gradient_dither oui ; gradient_classic non (mode « Gradient » = calque de remplissage dégradé dynamique) ; gradient_blend_mode Normal ; fill_opacity 100 ; bucket_fill_pattern non ; type_font "Inter", type_style "Regular", type_size 48 pt, type_aa "sharp", type_align "left" ; clone_aligned oui ; clone_sample "current" ; spot_type "contentAware" ; patch_mode "source" ; tone_range "midtones" ; exposure 50 ; protect_tones oui ; sponge_mode "desaturate" ; vibrance oui ; strength 50 ; protect_detail oui ; finger_painting non ; enhance_edge non ; vector_mode "path" ; shape_fill oui ; stroke_width 0 ; corner_radius 0 ; polygon_sides 5 ; line_weight 3 ; marquee_style "normal", marquee_width/height 1 ; move_auto_select oui ; move_target "layer" ; move_show_transform non ; crop_ratio "" ; crop_delete oui ; magic_eraser_opacity 100 ; bg_sampling "continuous" ; bg_limits "contiguous" ; bg_tolerance 50 ; bg_protect_fg non ; zoom_scrubby oui ; pencil_auto_erase non.

### 2.3 Barre d'options (barre contextuelle)

Conteneur : `panels.rs:397-813`. Hauteur 36 px (Pro) / 42 px ; marge horizontale 10 ; traits haut/bas couleur `separator`. En Pro, tête de barre : bouton Accueil `house` 26 px « Home » (`chrome_ui.rs:163-172`), trait vertical, icône de l'outil 26 px + chevron 10 px, trait (`panels.rs:407-416`). Les libellés en Pro reçoivent un « : » final (`opt_label`, `panels.rs:827-831`). Champs numériques = `widgets::value_field` (hauteur 24) ; listes = `widgets::dropdown` ; séparateurs = `vline` (22 px).

Priorités : transformation en cours → barre de transformation (`transform_tool.rs:1194`) ; Puppet/Perspective Warp → `puppet_ui`/`perspective_ui` (`distort_ui.rs:196-206`) ; outils de retouche (sauf Brush/Pencil/Mixer/Eraser) et Quick Selection : sélecteur de forme (« brush preset chip ») + bascule Brush Settings (`panels.rs:426-434`) ; puis `eraser_ui`, `retouch_ui`, `vector_ui`, `analysis_ui`, `slice_ui` (`panels.rs:435-442`).

| Outil | Champs (dans l'ordre), plage, unité, défaut | Source |
|---|---|---|
| Brush, Eraser (Pro) | puce de forme + Brush Settings │ Mode (27 modes, liste 96 px) ; Opacity 0–100 % ; bouton `circle-dot` « Always use pressure for opacity » ; Flow 1–100 % ; bouton `sparkles` « Enable airbrush-style build-up effects » ; Smoothing (champ 58 px) ; bouton `settings` « Set additional smoothing options » │ bouton `circle-dot` « Always use pressure for size » ; bouton `arrow-left-right` « Set painting symmetry options » | panels.rs:449-473 |
| Brush, Eraser (Studio/Classic) | puce │ Size 1–2500 px │ Hardness 0–100 % ; Opacity 0–100 % ; Flow 1–100 % ; Smoothing │ bascules « Pressure for Size », « Pressure for Opacity » | panels.rs:496-511 |
| Pencil | puce │ (hors Pro : Size 1–5000 px) │ Mode ; Opacity 0–100 % ; Smoothing │ case « Auto Erase » | panels.rs:475-495 |
| Mixer Brush | puce │ Wet, Load, Mix, Flow (0–100 % chacun) │ « Sample All Layers » | panels.rs:512-526 |
| Rect./Elliptical Marquee (Pro) | 4 modes (icônes `square` New selection, `plus` Add (Shift), `minus` Subtract (Alt), `squares-subtract` Intersect (Shift+Alt)) │ Feather 0–1000 px ; Anti-alias (grisé pour le rectangle) │ Style : Normal / Fixed Ratio / Fixed Size ; Width, bouton `arrow-left-right` « Swaps height and width », Height (Fixed Size : 1–300 000 px, défaut 64×64 ; Fixed Ratio : 0,001–999, défaut 1:1) │ bouton « Select and Mask… » | panels.rs:527-577 |
| Lasso, Polygonal Lasso (Pro) | 4 modes │ Feather 0–1000 px ; Anti-alias │ « Select and Mask… » ; en cours de polygone : « Click the first point or press {Enter} to close · Esc cancels » | panels.rs:578-597 |
| Magic Wand | 4 modes │ Tolerance 0–255 ; Anti-alias ; Contiguous ; Sample All Layers │ « Select Subject » ; « Select and Mask… » | panels.rs:598-613 |
| Quick Selection | puce de forme │ Sample All Layers ; Enhance Edge ; « {Alt} to subtract » │ « Select Subject » | retouch_ui.rs:263-271 |
| Object Selection | Sample All Layers ; « Drag a rectangle around the object » │ « Select Subject » | retouch_ui.rs:272-279 |
| Paint Bucket (Pro) | Fill : Foreground / Pattern ; Opacity 1–100 % ; Tolerance 0–255 ; Anti-alias ; Contiguous ; All Layers | panels.rs:614-627 |
| Gradient (Pro) | liste « Gradient » / « Classic gradient » ; aperçu du dégradé │ 5 styles (icônes `blend` Linear, `circle` Radial, `rotate-cw` Angle, `arrow-left-right` Reflected, `diamond` Diamond) │ Mode (27) ; Opacity 1–100 % ; Reverse ; Dither | panels.rs:628-665 |
| Crop (Pro) | Ratio : Ratio, Original Ratio, 1 : 1 (Square), 4 : 5 (8 : 10), 5 : 7, 2 : 3 (4 : 6), 16 : 9 (`chrome_ui.rs:195-203`) ; deux champs 0–99 999 + bouton d'échange │ « Clear » ; bouton `grid-3x3` « Overlay: Rule of Thirds » ; « Delete Cropped Pixels » (défaut oui) ; à droite `check` « Commit current crop operation  ({Enter}) », `ban` « Cancel current crop operation  (Esc) » | panels.rs:666-703 |
| Type (Pro) | `text-cursor` « Toggle text orientation » ; police (170 px) ; style (110 px) ; icône `type` + taille 1–1296 pt ; anticrénelage None/Sharp/Crisp/Strong/Smooth │ alignement `align-left`/`align-center`/`align-right` │ nuancier couleur « Set the text color » ; pendant l'édition : `check` « Commit any current edits ({Cmd+Enter}) », `ban` « Cancel any current edits (Esc) » | type_tool.rs:794-907 |
| Move (Pro) | « Auto-Select: » (défaut oui) + Layer/Group │ « Show Transform Controls » │ `panels-top-left` Align left edges, `app-window` Align horizontal centers, `panel-right` Align right edges ; `ellipsis` « Align and distribute » (menu Align = `layer.align.*`, Distribute = `layer.distribute.*`) | panels.rs:705-746 |
| Zoom | « Scrubby Zoom » (défaut oui) ; indication ; boutons « Fit Screen », « 100% » | panels.rs:764-783 |
| Eyedropper / Hand / (hors Pro) Marquee, Move, Lasso, Crop, Gradient, Bucket, Type | indications textuelles seulement (voir §8) | panels.rs:747-805 |
| Magic Eraser | Tolerance 0–255 ; Anti-alias ; Contiguous ; Sample All Layers │ Opacity 1–100 % | eraser_ui.rs:65-74 |
| Background Eraser | Sampling : `pipette` Continuous, `circle-dot` Once, `square` Background Swatch │ Limits : Discontiguous / Contiguous / Find Edges ; Tolerance 0–100 % ; Protect Foreground Color | eraser_ui.rs:75-97 |
| Spot Healing | Type : Content-Aware / Create Texture / Proximity Match │ Sample All Layers | retouch_ui.rs:190-200 |
| Patch | Patch : Source / Destination │ « Lasso around an area, then drag the selection » | retouch_ui.rs:201-211 |
| Healing, Clone Stamp | Aligned ; Sample : Current Layer / Current & Below / All Layers ; sans source : « {Alt}-click to set the source » | retouch_ui.rs:212-225 |
| Dodge, Burn | Range : Shadows / Midtones / Highlights ; Exposure % ; Protect Tones | retouch_ui.rs:226-232 |
| Sponge | Mode : Desaturate / Saturate ; Vibrance | retouch_ui.rs:233-238 |
| Blur, Sharpen, Smudge | Strength % ; Sample All Layers ; (Sharpen) Protect Detail ; (Smudge) Finger Painting | retouch_ui.rs:239-248 |
| History Brush | « Paints from the document's opening state » | retouch_ui.rs:249 |
| Pen | Path / Shape │ « Click: corner · Drag: smooth · Click first point: close · {Enter} finish · Esc cancel » | vector_ui.rs:389-401 |
| Path Selection | « Drag to move the active shape's path or the Work Path » (ou « Drag to move the targeted vector mask ») | vector_ui.rs:385-388 |
| Rectangle, Ellipse, Triangle, Polygon, Line, Custom Shape | liste « Shape » │ Fill: case + nuancier premier plan ; Stroke: 0–288 px │ (Rectangle) Radius: 0–10 000 px ; (Polygon) Sides: 3–100 ; (Line) Weight: 1–1000 px ; (Custom Shape) sélecteur de forme `preset_panels::shape_picker` | vector_ui.rs:402-438 |
| Ruler | X:, Y:, W:, H:, A:, L1:, L2: (lecture) │ Use Measurement Scale ; « Straighten Layer » ; « Clear » | analysis_ui.rs:417-438 |
| Count | « Count: {n} » │ groupe (liste 140 px), `eye`/`eye-off` visibilité, couleur, `trash` supprimer le groupe ; `folder-plus` nouveau groupe ; « Clear » │ Marker Size 1–10 ; Label Size 8–72 | analysis_ui.rs:439-480 |
| Note | Author: (texte 120 px) ; Color: ; « Clear All » ; `message-square` Notes panel | analysis_ui.rs:481-495 |
| Slice | « Style: Normal » │ « Slices From Guides » | slice_ui.rs:251-257 |
| Slice Select | « Promote », « Divide… », « Delete » │ Hide Auto Slices │ « Slice Options… » ; si verrouillé : « Slices are locked (View › Lock Slices) » | slice_ui.rs:258-283 |
| Transformation libre (Cmd+T) | X:, Y: −30 000…30 000 px (point de référence) │ W:, H: −10 000…10 000 % + lien `link`/`unlink` « Maintain aspect ratio » (défaut lié) │ `rotate-cw` angle −180…180° │ Interpolation: Bicubic / Bilinear / Nearest Neighbor ; zone d'actions 140 px à droite | transform_tool.rs:1194-1268 |
| Déformation (Warp) | Warp: None, Custom, Arc, Arc Lower, Arc Upper, Arch, Bulge, Shell Lower, Shell Upper, Flag, Wave, Fish, Rise, Fisheye, Inflate, Squeeze, Twist (`geom/src/warp.rs:114-132`) ; préréglage : Vertical, Bend: / H: / V: −100…100 % ; Custom : Split: (Crosswise / Vertically / Horizontally), Grid: Custom / Default / 3 x 3 / 4 x 4 / 5 x 5 | transform_tool.rs:1270-1350 |



## 3. Panneaux

Chemins relatifs à `crates/ui-egui/src/`.

### 3.1 Dock de droite et rail (lu)
- **Groupes et onglets** (`dock.rs:24-112`), ordre Essentials de haut en bas :

| Groupe (`Group::`) | Onglets (thème Pro) | Onglets (Studio/Classic) | Hauteur par défaut | Hauteur compacte | Hauteur min |
|---|---|---|---|---|---|
| Color | Color, Swatches, Gradients, Patterns | Swatches, Color, Gradients, Patterns | 190 | 130 | 80 |
| Properties | Properties, Adjustments | idem | 250 | 160 | 80 |
| Character (hors Essentials, #150) | Character, Paragraph | idem | 270 | 160 | 80 |
| Navigator | Navigator, Histogram, Info | idem | 210 | 140 | 80 |
| History | History, Actions, Layer Comps | idem | 200 | 130 | 80 |
| Layers | Layers, Channels, Paths | idem | 320 (remplit le reste ; demande 500) | 200 | 140 |

- Dispatch des onglets vers le code : `panels.rs:984-1007`.
- Le dernier groupe déplié (Layers) remplit la hauteur ; glisser l'intervalle entre deux groupes les redimensionne ; double-clic sur un onglet ou menu de panneau : replier ; glisser la barre d'onglets : déplacer le groupe (sauf Window › Workspace › Lock Workspace) (`dock.rs:1-11`).
- **Menu de panneau** (bouton à droite de la barre d'onglets 20×18, `widgets.rs:89`) : si l'onglet est Layers → « Collapse All Groups » (`layer_row_ui.rs:197-206`, `layer.setExpanded {"all":true,"expanded":false}`), séparateur ; puis « Collapse Panel Group » / « Expand Panel Group », « Move Group Up », « Move Group Down », séparateur, « Close Tab Group » (`dock.rs:410-434`).
- Barre d'onglets Pro : hauteur 26, fond `tab_strip`, police 11,5 (`widgets.rs:84`, `tab_strip.rs:165-197`) ; onglets en pilule (Studio) : police medium 12,5, hauteur 24 (`widgets.rs:112-131`, `tab_strip.rs:198-207`). Chevron des onglets débordants (`tab_strip.rs:139`).
- Largeur du dock : défaut 290 (Pro) / 300, plage 250–520, redimensionnable (`panels.rs:943, 973`) ; marge interne 2 (Pro) / 8.
- **Rail d'icônes** à l'extrême droite (toujours visible) : largeur 36 (Pro) / 44, boutons 28 / 32 (`panels.rs:911-934`) : `sliders-horizontal` Properties, `navigation` Navigator, `palette` Color & Swatches, `layers` Layers, `clock` History. En Studio, Properties flotte au-dessus du canevas (carte 320 px, `panels.rs:1893-1976`).
- Préréglages d'espace de travail (`menus.rs:910-933`) : Essentials / Photography / Painting / Graphic and Web — visibilité (navigator, color, layers, history, properties) : Photography (oui, non, oui, oui, oui), Painting (non, oui, oui, non, non), Graphic and Web (non, oui, oui, non, oui), Essentials et autres (non, oui, oui, non, oui) ; Character toujours fermé. Panneaux par défaut (`state.rs:279-293`) : layers, properties, color, toolbar, options_bar, status_bar ouverts ; history, navigator, brush_settings, character fermés.

### 3.2 Layers (`panels.rs:1269-1529`, rangée `panels.rs:1567-1759`)
- **Filtre (Pro, en tête)** : champ « Kind » (64×22, icône `search`) puis 5 boutons 22 px : `image` « Filter for pixel layers », `contrast` « Filter for adjustment layers », `type` « Filter for type layers », `square` « Filter for shape layers », `app-window` « Filter for smart objects » (`panels.rs:1284-1311`).
- **Ligne 1** : liste de mode de fusion (27 modes ; + Pass Through pour un groupe, `panels.rs:1265-1267`), largeur = reste ; « Opacity: » + champ 0–100 % (66 px) ; grisé pour le calque Background (`panels.rs:1312-1334`).
- **Ligne 2** : « Lock: » puis 5 icônes 20 px (Pro) : `grid-3x3` « Lock transparent pixels », `brush` « Lock image pixels », `move` « Lock position », `scan` « Prevent auto-nesting in and out of Artboards and Frames », `lock` « Lock all » ; en Studio/Classic une seule icône `lock`/`lock-open` « Lock layer » (bascule tout/rien ; sur Background → `layer.new.layerFromBackground`) ; à droite « Fill: » 0–100 % (66 px) (`panels.rs:1337-1378`). Le libellé « Lock: » disparaît si la place manque.
- **Rangée de calque** : hauteur 32 (Pro) / 46 ; fond `row_selected` si sélectionnée ; séparateur vertical à x+30 et trait bas (Pro) (`panels.rs:1580-1606`). De gauche à droite :
  1. œil `eye`/`eye-off` 22×22 (icône 15) → `layer.setProps {visible}` ;
  2. indentation de groupe + triangle de dépliage (`layer_tree_ui::disclosure`) ;
  3. « ↳ » si écrêté (clipping) ;
  4. vignette 24 px (Pro) / 34 : damier + pixels ; groupe `folder`, réglage `contrast` sur fond `field` ; texte = carré clair avec `type` ; remplissage dégradé = le dégradé, uni = la couleur ; contour 1 px gris 20 (Pro) ; badge d'objet dynamique (`panels.rs:1761-1802`) ;
  5. chaînes de lien et vignettes de masque de pixels / masque vectoriel (`mask_thumbs_ui::paint`) ; la cible active (pixels, masque ou masque vectoriel) est encadrée de coins (`paint_brackets`) ;
  6. nom (police 12 Pro / 13), tronqué « … » ; en Studio sous-libellé du type (ex. nom du réglage, « Group · {n} layers ») ; nom grisé si invisible ;
  7. indicateurs à droite (`layer_row_ui.rs` `indicators`, l.~106-170) : « fx » + triangle de dépliage des effets (infobulles « Hide the layer's effects  ({key}-click: all layers) » / « Show the layer's effects … »), nom du mode de fusion si différent, `lock`, `link`.
- **Clics** : simple = `layer.select` (Cmd-clic : toggle, Maj-clic : plage) ; clic sur vignette de masque → cible le masque ; Cmd-clic sur une vignette → `select.loadSelection` (transparence / masque / tracé ; Maj ajoute, Alt soustrait, Maj+Alt intersecte) ; Maj-clic sur masque → désactiver ; Alt-clic sur masque → afficher le masque (`panels.rs:1674-1716`). Double-clic : Background → calque normal ; nom → renommage en place (Entrée/Tab/clic ailleurs valide, Échap annule, `layer_row_ui.rs:228-277`) ; vignette réglage/remplissage → `layer.layerContentOptions` ; vignette d'objet dynamique → `layer.smartObjects.editContents` ; vignette texte → `type.editText` ; ailleurs → `layer.layerStyle.blendingOptions` (`panels.rs:1722-1744`). Clic droit : menu contextuel (`layer_menu_ui::show`, voir §8). Glisser-déposer pour réordonner (`layer_drag_and_drop`, `panels.rs:2268`).
- Sous-rangées : effets (`effect_rows`, `panels.rs:2320`) et filtres dynamiques (`smart_ui::filter_rows`).
- **Pied de panneau** (hauteur ≈38, icônes 26 px, de droite à gauche) : `trash` « Delete layer » (`layer.delete`) ; `square-plus` « Create a new layer » (`layer.new.layer`) ; `folder` « Create a new group » (`layer.new.group`) ; `contrast` « Create new fill or adjustment layer » (menu : les 16 `layer.newAdjustmentLayer.*`, séparateur, « Solid Color… », « Gradient… ») ; `square-dot` « Add a mask  (from the selection; {Alt} inverts) » ; « fx » italique 15 px « Add a layer style » (menu : « Blending Options… », séparateur, puis les 10 styles dans l'ordre de `KINDS`) ; `link` « Link layers » (actif à ≥ 2 calques) (`panels.rs:1442-1506`). Ordre visuel de gauche à droite (déduit, mise en page droite-à-gauche) : link, fx, mask, adjustment, folder, new, trash.

### 3.3 Properties (`panels.rs:2027-2070`, `layer_props_ui.rs`, `doc_props_ui.rs`, `props_layout.rs`)
- Rien ou Background sélectionné → **Document** (`doc_props_ui.rs:117+`) : section Canvas (W, H avec lien `link`/`unlink`, X et Y grisés « 0 px », boutons `rectangle-vertical` Portrait / `rectangle-horizontal` Landscape, « Resolution: {dpi} pixels/inch », Mode (liste 150), profondeur (liste à infobulles Integer / Floating point), Fill « Background Color ») ; section Rulers & Grids (`ruler` Rulers, `grid-3x3` Grid, `grid-2x2` Pixel Grid, unité (96 px)) ; section Guides (`eye` Show Guides, `lock` Lock Guides, « New Guide… », « Clear »).
- En-tête de calque (`props_layout.rs`) : icône par type (Adjustment `sliders-horizontal`, Group `folder`, Fill `paint-bucket`, Text `type`, Shape `pentagon`, Smart `app-window`, Raster `image`) + nom + type (« {Kind} Layer », « Artboard », nom du réglage). Constantes : SECTION_H 24, LABEL_W 22, LABEL_GAP 4, COL_GAP 8 (`props_layout.rs:8-11`).
- Calque (Pro, `layer_props_ui.rs:97-180`) : section **Transform** (W, lien « Link width and height », H ; X, Y) ; dégradé si calque de remplissage dégradé ; section **Align and Distribute** (6 glyphes 24 px : leftEdges, horizontalCenters, rightEdges, topEdges, verticalCenters, bottomEdges, infobulle « Align {what} ») ; sections Type ou Shape ; section **Quick Actions** (`props_layout.rs:105-121`) : Raster → Remove Background, Select Subject ; Text → Convert to Shape, Convert to Paragraph Text, Convert to Point Text, Create Warped Text, Rasterize Type ; Shape → Rasterize Shape, Convert to Smart Object ; Smart → Edit Contents, Rasterize Smart Object ; Group → Ungroup Layers, Convert to Smart Object ; Fill → Rasterize Fill Content ; Adjustment → aucune.
- Réglage : éditeur `adjust_editors::layer_editor` + bascules « Adjustment visible », « Clip to layer below » + bouton « Reset to defaults » (`panels.rs:1978-1999`).
- Studio : X/Y/W/H en lecture, curseurs Opacity et Fill 0–100 % (`panels.rs:2001-2024`).
- Type (`type_tool.rs:1093-1300`) — section **Character** : police (pleine largeur), style ; « tT » Font size 0,1–1296 pt ; « A↕ » Leading 0,1–5000 pt ; Kerning (Metrics, Optical ou valeur 1/1000 em) ; « VA » Tracking −1000…10 000 ; « ↕T » Vertical scale 0–1000 % ; « ↔T » Horizontal scale 0–1000 % ; « Aª » Baseline shift −1296…1296 pt ; Color (nuancier « Text color ») ; 6 bascules : Faux Bold, Faux Italic, All Caps, Small Caps, Underline, Strikethrough. Section **Paragraph** : 7 alignements (Left align text, Center text, Right align text, Justify last left, Justify last centered, Justify last right, Justify all) ; « →| » Indent left margin, « |← » Indent right margin, « ¶→ » Indent first line (−1296…1296 pt) ; « ↑¶ » Add space before paragraph, « ¶↓ » Add space after paragraph (0–1296 pt) ; Hyphenate. Sans calque texte : « Select a type layer to edit its character and paragraph settings. »

### 3.4 Adjustments (`panels.rs:2073-2108`)
« Add an adjustment » puis grille de 16 boutons 30 px (crée `layer.newAdjustmentLayer.<kind>` et bascule sur Properties) :

| kind | Icône | Infobulle |
|---|---|---|
| brightnessContrast | sun | Brightness/Contrast |
| levels | gauge | Levels |
| curves | pen-tool | Curves |
| exposure | scan | Exposure |
| vibrance | sparkles | Vibrance |
| hueSaturation | droplet | Hue/Saturation |
| colorBalance | blend | Color Balance |
| blackWhite | contrast | Black & White |
| photoFilter | circle-dot | Photo Filter |
| channelMixer | sliders-horizontal | Channel Mixer |
| invert | squares-subtract | Invert |
| posterize | layers | Posterize |
| threshold | square | Threshold |
| gradientMap | palette | Gradient Map |
| selectiveColor | swatch-book | Selective Color |
| colorLookup | grid-3x3 | Color Lookup |

### 3.5 Color, Swatches, Gradients, Patterns
- **Color (Pro)** (`panels.rs:2111-2203`) : pastilles premier plan / arrière-plan 22×22 à gauche ; champ saturation/luminosité (maillage 16×16, hauteur 120) ; bande de teinte verticale 14 px ; repère cercle blanc ; ligne « #RRGGBB » (mono 12) + « R … G … B … » (mono 11).
- **Color (Studio)** (`panels.rs:1213-1246`) : curseurs Hue 0–360°, Saturation 0–100 %, Brightness 0–100 % (dégradés) ; pastille 26 px, « #RRGGBB », « RGB r g b ».
- **Swatches** (`panels.rs:1141-1211`) : 40 couleurs fixes, 10 colonnes, écart 4, coins 4 ; rangées : 10 gris (0,26,51,77,102,128,153,179,204,255) ; 10 pastels ; 10 saturées ; 10 sombres (valeurs RVB en `panels.rs:1141-1182`) ; clic = premier plan, clic droit = arrière-plan ; aide « Click sets foreground · right-click sets background ».
- **Gradients** (`preset_panels.rs:482-521`) : préréglages groupés ; bouton « Create new gradient » ; clic → `gradient.presets.select`, double action → `gradient.presets.apply`.
- **Patterns** (`preset_panels.rs:522-600`) : idem, « Create new pattern from the selection », `pattern.presets.select` / `pattern.presets.apply`.

### 3.6 Navigator, Histogram, Info
- **Navigator** (`panels.rs:1078-1132`) : vignette dans un cadre de 150 px de haut sur damier ; rectangle visible rouge (255,84,84) ; clic/glisser recentre ; « Zoom » + pilules « Fit », « 100% », « 200% » ; curseur log2 du zoom de −6,64 à 5 (≈1 % à 3200 %).
- **Histogram** (`tone.rs:223-330`) : « Channel: » ; statistiques Mean, Std Dev, Median, Pixels, Cache Level ; triangle d'alerte quand le cache est en retard.
- **Info** (`panels.rs:1010-1076`) : colonnes R:, G:, B: | C:, M:, Y:, K: (CMJN naïf en %) ; X:, Y: | W:, H: (unité des règles) ; « Doc: {w} × {h} px ».

### 3.7 History, Actions, Layer Comps
- **History** (`panels.rs:1808-1888`) : rangée d'instantané 38 px (vignette 28 + nom du document) ; rangées 24 px avec icône déduite du libellé (brush, layers, square-dashed, paint-bucket, image, sliders-horizontal), état courant en `row_selected`, états rétablissables grisés ; clic = annuler/rétablir jusqu'à l'état. Pied (Pro) : `file-plus` « Create new document from current state », `scan` « Create new snapshot », `trash` « Delete current state » (boutons sans action branchée, `let _ =`).
- **Actions** (`actions.rs:66-200`) : aide « Record ● a sequence of edits, then play ▶ it on any document. » ; boutons `square` « Stop playing/recording », enregistrement « Begin recording », `play` « Play selection », `plus` « Create new action », `trash` « Delete ».
- **Layer Comps** (`comps_ui.rs:28-140`) : rangée « Last Document State » ; aide « Capture the visibility, position and style of every layer with + below, then switch between versions. » ; par comp : bascules `eye` Visibility, `move` Position, `sparkles` Appearance (Layer Style) ; alerte `triangle-alert` « {n} layer(s) recorded by this comp were deleted… ».

### 3.8 Channels et Paths
- **Channels** (`channels_panel.rs`) : rangées par canal avec visibilité (« Toggle visibility »), masque en surimpression (« Show the layer mask as an overlay ») ; pied : `circle-dashed` « Load channel as selection », `square-dashed` « Save selection as channel », `trash` « Delete current channel », `plus` « Create new channel » (l.279-289) ; options de surimpression : Overlay Color (Red, Green, Blue, Cyan, Magenta, Yellow) et Overlay Opacity (l.346-361).
- **Paths** (`vector_ui.rs:723-860`) : sans tracé « Draw with the Pen tool (P) or make a work path from a selection. » ; double-clic sur Work Path = enregistrer (« Path {n} ») ; menu contextuel d'un tracé (`path_context_actions`, l.680-722) : Make Selection, Fill Path, Stroke Path ; puis Save Path (tracé de travail) ; Duplicate Path (« {nom} copy {n} ») et Delete Path (tracés enregistrés) ; Delete Vector Mask (masque vectoriel) ; pied (7 icônes 24 px) : `paint-bucket` « Fill path with foreground color », `circle` « Stroke path with brush », `square-dashed` « Load path as a selection », `spline` « Make work path from selection » (tolérance 2), `square` « Add vector mask », `square-plus` « Create new path », `trash` « Delete path » (ou « Delete vector mask »).

### 3.9 Brush Settings (fenêtre flottante, F5 ; `brush_panel.rs:32-46`, `brush_sections.rs`)
Sections (case d'activation sauf 1re et Smoothing) : Brush Tip Shape (Size jusqu'à 5000 + « Restore original size », Flip X, Flip Y, Angle/Roundness par widget ellipse, Hardness, Spacing 1–1000 % avec case) ; Shape Dynamics (Size Jitter, Minimum Diameter, Tilt Scale, Angle Jitter, Roundness Jitter + Minimum Roundness, Flip X/Y Jitter, Brush Projection ; « Control: » + Fade steps 1–9999) ; Scattering (Scatter 0–1000 %, Both Axes, Count 1–16, Count Jitter) ; Texture (motif, Invert, Pattern Size 16–1024 px, Scale, Brightness −150…150, Contrast −50…100, Texture Each Tip, Mode, Depth, Minimum Depth, Depth Jitter) ; Dual Brush (Mode, Flip, Size ≤ 2500, Spacing, Scatter, Both Axes, Count 1–16) ; Color Dynamics (Apply Per Tip, Foreground/Background Jitter, Hue Jitter, Saturation Jitter, Brightness Jitter, Purity −100…100 %) ; Transfer (Opacity/Flow/Wetness/Mix Jitter + Minimum ; bloc Mixer Brush : Wet, Load, Mix, Flow) ; Brush Pose (Tilt X, Tilt Y, Override Tilt, Rotation 0–360°, Override Rotation, Pressure, Override Pressure) ; Noise ; Wet Edges ; Build-up (Rate 1–200 /s) ; Smoothing (Smoothing %, Pulled String Mode, Stroke Catch-up, Catch-up on Stroke End, Adjust for Zoom) ; Protect Texture. Onglet préréglages = Window › Brushes (`menus.rs:157-162`).


## 4. Réglages, filtres, modes de fusion, styles

### 4.1 Calques de réglage : 16 (lu, `crates/engine/src/commands.rs:844-933`)
Une seule table `ADJ` génère, pour chaque type, **deux** commandes : `layer.newAdjustmentLayer.<kind>` (menu Layer › New Adjustment Layer, nécessite un document) et `image.adjustments.<kind>` (menu Image › Adjustments, destructif, nécessite un calque de pixels ou un canal), avec la même chaîne de paramètres. Raccourcis côté Image › Adjustments : levels Cmd+L, curves Cmd+M, hueSaturation Cmd+U, colorBalance Cmd+B, invert Cmd+I, blackWhite Cmd+Alt+Shift+B (`commands.rs:912-920`). Les clés de canal de Levels/Curves suivent le mode (red/green/blue, gray, cyan/magenta/yellow/black, lightness/a/b ; `adjust_params`).

| # | kind | Libellé | Paramètres (plage = défaut) |
|---|---|---|---|
| 1 | brightnessContrast | Brightness/Contrast… | brightness −150..150 = 0 ; contrast −50..100 = 0 ; legacy bool = false |
| 2 | levels | Levels… | inBlack 0..253 = 0 ; gamma 0.01..9.99 = 1 ; inWhite 2..255 = 255 ; outBlack 0..255 = 0 ; outWhite 0..255 = 255 ; red/green/blue json (par canal mêmes 5 clés) |
| 3 | curves | Curves… | points json [[in,out],…] 0..255, 2 à 19 points (composite) ; red/green/blue json par canal |
| 4 | exposure | Exposure… | exposure −20..20 = 0 ; offset −0.5..0.5 = 0 ; gamma 0.01..9.99 = 1 |
| 5 | vibrance | Vibrance… | vibrance −100..100 = 0 ; saturation −100..100 = 0 |
| 6 | hueSaturation | Hue/Saturation… | hue −180..180 = 0 ; saturation −100..100 = 0 ; lightness −100..100 = 0 ; colorize bool = false (colorize : hue 0..360, saturation 0..100) ; reds/yellows/greens/cyans/blues/magentas json {hue, saturation, lightness, range:[4 degrés]} |
| 7 | colorBalance | Color Balance… | shadows/midtones/highlights json [cyan-red, magenta-green, yellow-blue] −100..100 ; preserveLuminosity bool = true |
| 8 | blackWhite | Black & White… | reds −200..300 = 40 ; yellows = 60 ; greens = 40 ; cyans = 60 ; blues = 20 ; magentas = 80 ; tint bool = false ; tintColor #rrggbb |
| 9 | photoFilter | Photo Filter… | filter : warming85, warmingLBA, warming81, cooling80, coolingLBB, cooling82, red, orange, yellow, green, cyan, blue, violet, magenta, sepia, deepRed, deepBlue, deepEmerald, deepYellow, underwater ; color #rrggbb ; density 0..100 = 25 ; preserveLuminosity bool = true |
| 10 | channelMixer | Channel Mixer… | red/green/blue/gray json [rouge %, vert %, bleu %, constante %] −200..200 ; monochrome bool = false |
| 11 | invert | Invert | (aucun) |
| 12 | posterize | Posterize… | levels 2..255 = 4 |
| 13 | threshold | Threshold… | level 1..255 = 128 |
| 14 | gradientMap | Gradient Map… | stops json [[position 0..1, "#rrggbb"],…] 2 à 64 ; reverse bool = false ; dither bool = false |
| 15 | selectiveColor | Selective Color… | method relative/absolute = relative ; colors reds/yellows/greens/cyans/blues/magentas/whites/neutrals/blacks = reds ; cyan, magenta, yellow, black −100..100 = 0 ; tableaux [c,m,y,k] par gamme |
| 16 | colorLookup | Color Lookup… | lut none/warm/cool/tealOrange/bleachBypass/fadedFilm/dayForNight/monoContrast/crossProcess = none ; file (.cube/.3dl/.look) ; interpolation trilinear/tetrahedral = trilinear ; dither bool = false ; data json |

Autres entrées d'Image › Adjustments (destructives seulement, pas de calque de réglage) — table générée ci-dessous ; notamment Desaturate (Cmd+Shift+U, `commands.rs:721-735`), Equalize (`extra_cmds.rs`), Shadows/Highlights, Replace Color, Match Color, HDR Toning (`crates/engine/src/adjust_cmds.rs:350-394`).

Éditeurs interactifs (Properties et dialogue) : 13 types ont un éditeur dédié (`crates/ui-egui/src/adjust_editors.rs:25-39` : brightnessContrast, levels, curves, exposure, vibrance, hueSaturation, colorBalance, blackWhite, photoFilter, channelMixer, posterize, threshold, gradientMap) ; selectiveColor et colorLookup passent par le dialogue schéma (`filter_dialog.rs:131-145`), invert n'a pas de paramètre.

| id | Libellé | Raccourci | Paramètres | Source |
|---|---|---|---|---|
| `image.adjustments.shadowsHighlights` | Shadows/Highlights… |  | {"shadowAmount":0..100=35,"shadowTone":0..100=50,"shadowRadius":0..2500=30,"highlightAmount":0..100=0,"highlightTone":0..100=50,"highlightRadius":0..2500=30,"color":-100..100=20,"midtone":-100..100=0,"blackClip":0..50=0.01,"whiteClip":0..50=0.01} | adjust_cmds.rs:353 |
| `image.adjustments.replaceColor` | Replace Color… |  | {"color":json,"fuzziness":0..200=40,"hue":-180..180=0,"saturation":-100..100=0,"lightness":-100..100=0} (color: "#rrggbb", default the foreground colour) | adjust_cmds.rs:361 |
| `image.adjustments.matchColor` | Match Color… |  | {"source":doc,"sourceLayer":json,"luminance":1..200=100,"intensity":1..200=100,"fade":0..100=0,"neutralize":bool=false,"useSelectionInSource":bool=false,"useSelectionInTarget":bool=false} (source: document index; sourceLayer: layer id, default the merged image) | adjust_cmds.rs:369 |
| `image.adjustments.hdrToning` | HDR Toning… |  | {"radius":1..500=30,"strength":0.1..4=0.5,"gamma":0.1..2=1,"exposure":-5..5=0,"detail":-100..300=30,"shadow":-100..100=0,"highlight":-100..100=0,"vibrance":-100..100=0,"saturation":-100..100=20,"curve":[[in,out],…] 0..255} (flattens the image) | adjust_cmds.rs:377 |
| `image.adjustments.colorLookup.list` | List Color Lookup Looks |  | {} | adjust_cmds.rs:385 |
| `image.adjustments.desaturate` | Desaturate | Cmd+Shift+U | {} | commands.rs:722 |
| `image.adjustments.equalize` | Equalize |  | {} | extra_cmds.rs:592 |
| `image.adjustments.brightnessContrast` | Brightness/Contrast… |  | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.levels` | Levels… | Cmd+L | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.curves` | Curves… | Cmd+M | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.exposure` | Exposure… |  | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.vibrance` | Vibrance… |  | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.hueSaturation` | Hue/Saturation… | Cmd+U | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.colorBalance` | Color Balance… | Cmd+B | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.blackWhite` | Black & White… | Cmd+Alt+Shift+B | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.photoFilter` | Photo Filter… |  | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.channelMixer` | Channel Mixer… |  | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.invert` | Invert | Cmd+I | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.posterize` | Posterize… |  | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.threshold` | Threshold… |  | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.gradientMap` | Gradient Map… |  | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.selectiveColor` | Selective Color… |  | (voir boucle ADJ) | commands.rs:868-933 (généré) |
| `image.adjustments.colorLookup` | Color Lookup… |  | (voir boucle ADJ) | commands.rs:868-933 (généré) |

### 4.2 Filtres (lu, par sous-menu du catalogue)
Source des paramètres : chaîne `params` de chaque `CommandSpec` (`crates/engine/src/filters.rs`, `filters_ext.rs`, `extra_cmds.rs`, `lens_cmds.rs`, `distort_cmds.rs`, `vp_cmds.rs`, `smart_cmds.rs`, `gallery_cmds.rs`, `plugin_cmds.rs`). Grammaire : `"clé":min..max=défaut`, `"a|b"` = choix, `bool`, `json`, `px`, `u32`. Ordre = ordre du catalogue de menus (`menu_catalog.rs`). Le sous-menu Filter › Plug-ins liste aussi dynamiquement les extensions WebAssembly installées (`plugin_ui::insert_menu_items`, `menus.rs:670`). Dialogue généré : voir §5.5.


**(racine Filter)** (8)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `filter.lastFilter` | Last Filter | Dernier filtre | {} | filters.rs:334 |
| `filter.convertForSmartFilters` | Convert for Smart Filters | Convertir pour les filtres intelligents | {"layer":id?} | smart_cmds.rs:878 |
| `filter.filterGallery` | Filter Gallery… | Galerie de filtres… | {"effects":json,"foreground":json,"background":json,"list":bool} | gallery_cmds.rs:138 |
| `filter.cameraRaw` | Camera Raw Filter… | Filtre Camera Raw… | {"temperature":-100..100=0,"tint":-100..100=0,"exposure":-5..5=0,"contrast":-100..100=0,"highlights":-100..100=0,"shadows":-100..100=0,"whites":-100..100=0,"blacks":-100..100=0,"texture":-100..100=0,"clarity":-100..100=0,"dehaze":-100..100=0,"vibrance":-100..100=0,"saturation":-100..100=0,"curveHighlights":-100..100=0,"curveLights":-100..100=0,"curveDarks":-100..100=0,"curveShadows":-100..100=0,"curveSplits":[25,50,75],"pointCurve":[[in,out]],"pointCurveRed":[[in,out]],"pointCurveGreen":[[in,out]],"pointCurveBlue":[[in,out]],"hslHue":[8],"hslSat":[8],"hslLum":[8],"gradeShadows":{"hue":deg,"sat":0..100,"lum":-100..100},"gradeMidtones":{},"gradeHighlights":{},"gradeGlobal":{},"gradeBlending":0..100=50,"gradeBalance":-100..100=0,"sharpenAmount":0..150=0,"sharpenRadius":0.5..3=1,"sharpenDetail":0..100=25,"sharpenMasking":0..100=0,"noiseLuminance":0..100=0,"noiseLuminanceDetail":0..100=50,"noiseColor":0..100=0,"noiseColorDetail":0..100=50,"grainAmount":0..100=0,"grainSize":0..100=25,"grainRoughness":0..100=50,"vignetteAmount":-100..100=0,"vignetteMidpoint":0..100=50,"vignetteRoundness":-100..100=0,"vignetteFeather":0..100=50,"vignetteHighlights":0..100=0,"vignetteStyle":"highlightPriority\|colorPriority\|paintOverlay","seed":u32=0} | lens_cmds.rs:403 |
| `filter.adaptiveWideAngle` | Adaptive Wide Angle… | Grand angle adaptatif… | {"model":"auto\|fisheye\|perspective\|fullSpherical","focalLength":0..200=0,"cropFactor":0.1..10=1,"scale":50..150=100,"constraints":[{"a":[x,y],"b":[x,y],"orientation":"free\|horizontal\|vertical"}]} | lens_cmds.rs:393 |
| `filter.lensCorrection` | Lens Correction… | Correction de l'objectif… | {"profile":"none\|auto\|generic","focalLength":mm=0,"correctDistortion":bool=true,"correctVignette":bool=true,"correctCA":bool=true,"autoScale":bool=false,"distortion":-100..100=0,"redCyan":-100..100=0,"blueYellow":-100..100=0,"vignetteAmount":-100..100=0,"vignetteMidpoint":0..100=50,"vertical":-100..100=0,"horizontal":-100..100=0,"angle":-180..180=0,"scale":50..150=100,"edge":"transparency\|edgeExtension\|black\|white","straighten":[[x,y],[x,y]]?} | lens_cmds.rs:383 |
| `filter.liquify` | Liquify… | Liquéfier… | {"strokes":[{"tool":"forwardWarp\|reconstruct\|smooth\|twirlCw\|twirlCcw\|pucker\|bloat\|pushLeft\|freeze\|thaw\|lassoMask\|reconstructAll","size":px=100,"density":0-100=50,"pressure":0-100=100,"rate":0-100=80,"points":[[x,y,pressure?]…],"amount":%? (reconstructAll; lassoMask: 1 freezes the polygon in points, 0 thaws it)}…],"meshSize":px? (field resolution, px per node; default 2, or 4 above 4 MP),"layer":id?} — strokes replay in order on a fresh field; a selection limits the effect; on a smart object it becomes a smart filter | distort_cmds.rs:371 |
| `filter.vanishingPoint` | Vanishing Point… | Point de fuite… | {"planes":[{"corners":[[x,y]×4]} \| {"from":plane,"edge":"top\|right\|bottom\|left","angle":deg=90,"depth":1}],"focalLength":px=0,"paste":[{"plane":0,"layer":id? (else the clipboard),"at":[u,v]=[0.25,0.25],"width":0..1=0.5}],"clone":[{"source":[x,y],"points":[[x,y]],"size":px=40,"hardness":0..100=50,"opacity":0..100=100}],"newLayer":bool=false} | vp_cmds.rs:199 |

**Blur** (11)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `filter.blur.average` | Average | Moyenne | {} | extra_cmds.rs:688 |
| `filter.blur.blur` | Blur | Flou | {} | filters.rs:274 |
| `filter.blur.blurMore` | Blur More | Flou accentué | {} | filters.rs:275 |
| `filter.blur.boxBlur` | Box Blur… | Flou par boîte… | {"radius":1..2000=1} | filters.rs:280 |
| `filter.blur.gaussianBlur` | Gaussian Blur… | Flou gaussien… | {"radius":0.1..1000=1} | filters.rs:273 |
| `filter.blur.lensBlur` | Lens Blur… | Flou d'objectif… | {"radius":0..100=15,"shape":"hexagon\|triangle\|square\|pentagon\|heptagon\|octagon","bladeCurvature":0..100=0,"rotation":0..360=0,"depthMap":"none\|transparency\|layerMask","focalDistance":0..255=0,"invert":bool,"brightness":0..100=0,"threshold":0..255=255,"noise":0..100=0,"distribution":"uniform\|gaussian","monochromatic":bool,"seed":u32=0} | filters_ext.rs:544 |
| `filter.blur.motionBlur` | Motion Blur… | Flou de mouvement… | {"angle":-360..360=0,"distance":1..2000=10} | filters.rs:281 |
| `filter.blur.radialBlur` | Radial Blur… | Flou radial… | {"amount":1..100=10,"method":"spin\|zoom","centerX":0..1=0.5,"centerY":0..1=0.5} | filters.rs:283 |
| `filter.blur.shapeBlur` | Shape Blur… | Flou selon une forme… | {"radius":5..1000=10,"shape":"circle\|ring\|square\|diamond\|triangle\|hexagon\|star\|heart\|cross"} | filters_ext.rs:550 |
| `filter.blur.smartBlur` | Smart Blur… | Flou intelligent… | {"radius":0.1..100=3,"threshold":0.1..100=25,"quality":"high\|medium\|low","mode":"normal\|edgeOnly\|overlayEdge"} | filters_ext.rs:538 |
| `filter.blur.surfaceBlur` | Surface Blur… | Flou de surface… | {"radius":1..100=5,"threshold":2..255=15} | filters.rs:288 |

**Blur Gallery** (5)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `filter.blurGallery.fieldBlur` | Field Blur… | Flou de champ… | {"blur":0..500=15,"centerX":0..1=0.5,"centerY":0..1=0.5,"pins":json} | filters_ext.rs:569 |
| `filter.blurGallery.irisBlur` | Iris Blur… | Flou d'iris… | {"blur":0..500=15,"centerX":0..1=0.5,"centerY":0..1=0.5,"radiusX":0.01..1=0.35,"radiusY":0.01..1=0.25,"angle":-180..180=0,"roundness":0..100=0,"feather":0..0.99=0.5,"pins":json} | filters_ext.rs:563 |
| `filter.blurGallery.tiltShift` | Tilt-Shift… | Inclinaison-décalage… | {"blur":0..500=15,"centerX":0..1=0.5,"centerY":0..1=0.5,"angle":-90..90=0,"focus":0..1=0.1,"transition":0.01..1=0.15} | filters_ext.rs:557 |
| `filter.blurGallery.pathBlur` | Path Blur… | Flou de tracé… | {"speed":0..500=50,"taper":0..100=0,"startX":0..1=0.2,"startY":0..1=0.5,"endX":0..1=0.8,"endY":0..1=0.5,"paths":json} | filters_ext.rs:581 |
| `filter.blurGallery.spinBlur` | Spin Blur… | Flou de rotation… | {"blurAngle":0..360=15,"centerX":0..1=0.5,"centerY":0..1=0.5,"radiusX":0.01..1=0.3,"radiusY":0.01..1=0.3,"angle":-180..180=0,"pins":json} | filters_ext.rs:575 |

**Distort** (9)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `filter.distort.displace` | Displace… | Déplacement… | {"horizontal":-999..999=10,"vertical":-999..999=10,"fit":"stretch\|tile","undefinedAreas":"repeat\|wrap","mapDocument":doc,"mapPath":text,"mapLayer":json} | filters_ext.rs:498 |
| `filter.distort.pinch` | Pinch… | Pincement… | {"amount":-100..100=50} | filters.rs:314 |
| `filter.distort.polarCoordinates` | Polar Coordinates… | Coordonnées polaires… | {"mode":"rectangularToPolar\|polarToRectangular"} | filters.rs:323 |
| `filter.distort.ripple` | Ripple… | Ondulation… | {"amount":-999..999=100,"size":"small\|medium\|large"} | filters.rs:322 |
| `filter.distort.shear` | Shear… | Cisaillement… | {"amount":-100..100=0,"undefinedAreas":"wrap\|repeat","points":json} | filters_ext.rs:503 |
| `filter.distort.spherize` | Spherize… | Sphérisation… | {"amount":-100..100=100,"mode":"normal\|horizontalOnly\|verticalOnly"} | filters.rs:315 |
| `filter.distort.twirl` | Twirl… | Tourbillon… | {"angle":-999..999=50} | filters.rs:313 |
| `filter.distort.wave` | Wave… | Onde… | {"generators":1..999=5,"wavelengthMin":1..998=10,"wavelengthMax":2..999=120,"amplitudeMin":1..998=5,"amplitudeMax":1..999=35,"type":"sine\|triangle\|square","undefinedAreas":"wrap\|repeat","seed":u32=0} | filters.rs:317 |
| `filter.distort.zigZag` | ZigZag… | Zigzag… | {"amount":-100..100=10,"ridges":0..20=5,"style":"pondRipples\|outFromCenter\|aroundCenter"} | filters_ext.rs:505 |

**Noise** (5)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `filter.noise.addNoise` | Add Noise… | Ajout de bruit… | {"amount":0.1..400=12.5,"distribution":"uniform\|gaussian","monochromatic":bool,"seed":u32=0} | filters.rs:302 |
| `filter.noise.despeckle` | Despeckle | Supprimer les mouchetures | {} | filters.rs:279 |
| `filter.noise.dustAndScratches` | Dust & Scratches… | Poussière et rayures… | {"radius":1..500=1,"threshold":0..255=0} | filters.rs:308 |
| `filter.noise.median` | Median… | Médiane… | {"radius":1..500=1} | filters.rs:307 |
| `filter.noise.reduceNoise` | Reduce Noise… | Réduction du bruit… | {"strength":0..10=6,"preserveDetails":0..100=60,"reduceColorNoise":0..100=45,"sharpenDetails":0..100=25,"removeJpegArtifact":bool} | filters_ext.rs:531 |

**Pixelate** (7)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `filter.pixelate.colorHalftone` | Color Halftone… | Trame de demi-teintes couleur… | {"maxRadius":4..127=8,"channel1":-360..360=108,"channel2":-360..360=162,"channel3":-360..360=90,"channel4":-360..360=45} | filters_ext.rs:459 |
| `filter.pixelate.crystallize` | Crystallize… | Cristallisation… | {"cellSize":3..300=10,"seed":u32=0} | filters_ext.rs:464 |
| `filter.pixelate.facet` | Facet | Facettes | {} | filters_ext.rs:465 |
| `filter.pixelate.fragment` | Fragment | Fragmentation | {} | filters_ext.rs:466 |
| `filter.pixelate.mezzotint` | Mezzotint… | Manière noire… | {"type":"fineDots\|mediumDots\|grainyDots\|coarseDots\|shortLines\|mediumLines\|longLines\|shortStrokes\|mediumStrokes\|longStrokes","seed":u32=0} | filters_ext.rs:468 |
| `filter.pixelate.mosaic` | Mosaic… | Mosaïque… | {"cellSize":2..200=10} | filters.rs:309 |
| `filter.pixelate.pointillize` | Pointillize… | Pointillisme… | {"cellSize":3..300=5,"seed":u32=0,"background":json} | filters_ext.rs:473 |

**Render** (8)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `filter.render.flame` | Flame… | Flamme… | {"flameType":"oneFlameAlongPath\|multipleFlamesAlongPath\|multipleFlamesPathDirections\|multipleFlamesVariousLength\|candleLight\|multipleFlamesOneDirection","length":1..1000=150,"randomizeLength":bool,"width":1..1000=40,"angle":-180..180=0,"interval":1..1000=60,"adjustIntervalForLoops":bool=true,"useCustomColor":bool,"color":color,"turbulent":0..100=25,"jag":0..100=25,"opacity":0..100=75,"flameLines":1..100=20,"flameBottomAlignment":0..100=20,"flameStyle":"normal\|violent\|flat","flameShape":"parallel\|toCenter\|spread\|oval\|pointed","randomizeShapes":bool,"seed":u32=0,"quality":"draft\|low\|medium\|high\|fine","path":text,"newLayer":bool} → {layer,newLayer,bounds,primitives,usedPath} | render_cmds.rs:188 |
| `filter.render.pictureFrame` | Picture Frame… | Cadre d'image… | {"frame":"vineWithFlowers\|vineWithLeaves\|ivy\|roses\|daisies\|berries\|bamboo\|waves\|zigzag\|dots\|rope\|scallops\|doubleLine\|snowflakes\|stars\|hearts","margin":0..30=4,"size":1..100=50,"arrangement":1..100=50,"lines":1..5=1,"thickness":1..100=30,"fade":0..100=0,"vineColor":color,"flowerColor":color,"leafColor":color,"seed":u32=0,"newLayer":bool} → {layer,newLayer,bounds,primitives,frame} | render_cmds.rs:198 |
| `filter.render.tree` | Tree… | Arbre… | {"baseTreeType":1..34=1,"lightDirection":1..5=3,"leavesAmount":0..100=50,"leavesSize":0..200=100,"branchesHeight":50..300=100,"branchesThickness":50..200=100,"defaultLeaves":bool=true,"leavesColor":color,"customBranchColor":bool,"branchesColor":color,"flatShading":bool,"seed":u32=0,"x":0..1=0.5,"y":0..1=0.95,"size":0.05..2=0.8,"newLayer":bool} → {layer,newLayer,bounds,primitives,treeType} | render_cmds.rs:208 |
| `filter.render.clouds` | Clouds | Nuages | {"seed":u32=0} | extra_cmds.rs:689 |
| `filter.render.differenceClouds` | Difference Clouds | Nuages par différence | {"seed":u32=0} | extra_cmds.rs:690 |
| `filter.render.fibers` | Fibers… | Fibres… | {"variance":1..64=16,"strength":1..64=4,"seed":u32=0,"foreground":json,"background":json} | filters_ext.rs:512 |
| `filter.render.lensFlare` | Lens Flare… | Reflet d'objectif… | {"brightness":10..300=100,"centerX":0..1=0.5,"centerY":0..1=0.5,"lens":"zoom\|prime35\|prime105\|moviePrime"} | filters_ext.rs:518 |
| `filter.render.lightingEffects` | Lighting Effects… | Effets d'éclairage… | {"lightType":"spot\|point\|infinite","intensity":-100..100=75,"lightX":0..1=0.25,"lightY":0..1=0.2,"lightZ":0..2=0.6,"targetX":0..1=0.5,"targetY":0..1=0.55,"cone":1..89=45,"hotspot":0..100=50,"angle":-180..180=135,"elevation":0..90=45,"gloss":-100..100=0,"metallic":-100..100=0,"exposure":-100..100=0,"ambience":-100..100=8,"texture":"none\|red\|green\|blue\|alpha\|luminance","height":0..100=50,"whiteIsHigh":bool=true,"lights":json} | filters_ext.rs:524 |

**Sharpen** (5)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `filter.sharpen.sharpen` | Sharpen | Netteté | {} | filters.rs:276 |
| `filter.sharpen.sharpenEdges` | Sharpen Edges | Netteté des contours | {} | filters.rs:278 |
| `filter.sharpen.sharpenMore` | Sharpen More | Netteté accentuée | {} | filters.rs:277 |
| `filter.sharpen.smartSharpen` | Smart Sharpen… | Netteté intelligente… | {"amount":1..500=100,"radius":0.1..64=1,"reduceNoise":0..100=10} | filters.rs:296 |
| `filter.sharpen.unsharpMask` | Unsharp Mask… | Masque flou… | {"amount":1..500=50,"radius":0.1..1000=1,"threshold":0..255=0} | filters.rs:290 |

**Stylize** (9)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `filter.stylize.diffuse` | Diffuse… | Diffuser… | {"mode":"normal\|darkenOnly\|lightenOnly\|anisotropic","seed":u32=0} | filters_ext.rs:475 |
| `filter.stylize.emboss` | Emboss… | Relief… | {"angle":-180..180=135,"height":1..100=3,"amount":1..500=100} | filters.rs:310 |
| `filter.stylize.extrude` | Extrude… | Extruder… | {"type":"blocks\|pyramids","size":2..255=30,"depth":1..255=30,"depthMode":"random\|levelBased","solidFrontFaces":bool,"maskIncompleteBlocks":bool,"seed":u32=0} | filters_ext.rs:477 |
| `filter.stylize.findEdges` | Find Edges | Détecter les contours | {} | filters.rs:311 |
| `filter.stylize.oilPaint` | Oil Paint… | Peinture à l'huile… | {"stylization":0.1..10=4,"cleanliness":0..10=5,"scale":0.1..10=1,"bristleDetail":0..10=5,"lighting":bool=true,"angle":-180..180=-60,"shine":0..10=1} | filters_ext.rs:483 |
| `filter.stylize.solarize` | Solarize | Solariser | {} | filters.rs:312 |
| `filter.stylize.tiles` | Tiles… | Carreaux… | {"count":1..99=10,"maxOffset":1..99=10,"fill":"background\|foreground\|inverse\|unaltered","seed":u32=0,"foreground":json,"background":json} | filters_ext.rs:489 |
| `filter.stylize.traceContour` | Trace Contour… | Tracer les contours… | {"level":0..255=128,"edge":"lower\|upper"} | filters_ext.rs:494 |
| `filter.stylize.wind` | Wind… | Vent… | {"method":"wind\|blast\|stagger","direction":"fromRight\|fromLeft","seed":u32=0} | filters_ext.rs:495 |

**Video** (2)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `filter.video.deInterlace` | De-Interlace… | Désentrelacer… | {"eliminate":"oddFields\|evenFields","createBy":"interpolation\|duplication"} | filters_ext.rs:591 |
| `filter.video.ntscColors` | NTSC Colors | Couleurs NTSC | {} | filters_ext.rs:596 |

**Other** (6)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `filter.other.custom` | Custom… | Personnalisé… | {"kernel":int[25],"scale":1..9999=1,"offset":-9999..9999=0} | filters_ext.rs:587 |
| `filter.other.hsbHsl` | HSB/HSL | TSL/TSI | {"inputMode":"rgb\|hsb\|hsl","rowOrder":"hsb\|hsl\|rgb"} | filters_ext.rs:588 |
| `filter.other.highPass` | High Pass… | Passe-haut… | {"radius":0.1..1000=10} | filters.rs:324 |
| `filter.other.maximum` | Maximum… | Maximum… | {"radius":0.2..500=1,"preserve":"squareness\|roundness"} | filters.rs:326 |
| `filter.other.minimum` | Minimum… | Minimum… | {"radius":0.2..500=1,"preserve":"squareness\|roundness"} | filters.rs:325 |
| `filter.other.offset` | Offset… | Décalage… | {"horizontal":px=0,"vertical":px=0,"undefinedAreas":"wrap\|repeat\|transparent"} | filters.rs:328 |

**Plug-ins** (1)

| id | Libellé EN | Libellé FR | Paramètres (chaîne `params` du registre) | Source |
|---|---|---|---|---|
| `plugin.install` | Install Plug-in… | Installer une extension… | {"path":text,"data":json,"replace":bool=true} (path: a .wasm file, native only; data: the module as base64) | plugin_cmds.rs:239 |

### 4.3 Modes de fusion : 27 (+ Pass Through pour les groupes) (lu, `crates/color/src/blend.rs:11-140`)
Ordre du menu = `BlendMode::LAYER_MODES` (« All modes except PassThrough, in Photoshop menu order », l.44-72). Les listes déroulantes (`widgets::dropdown`) n'insèrent **aucun séparateur** entre familles (lu : `panels.rs:455, 486, 657, 1265-1267` construisent la liste à plat). Pass Through n'apparaît en tête que pour un groupe (`blend_options(groups)`, `panels.rs:1265-1267`).

| # | Mode | Libellé FR (fr.tsv) | Clé PSD | Séparable |
|---|---|---|---|---|
| 0 | Pass Through (groupes) | Transfert | pass | — |
| 1 | Normal | Normal | norm | oui |
| 2 | Dissolve | Fondu | diss | oui |
| 3 | Darken | Obscurcir | dark | oui |
| 4 | Multiply | Produit | mul  | oui |
| 5 | Color Burn | Densité couleur + | idiv | oui |
| 6 | Linear Burn | Densité linéaire + | lbrn | oui |
| 7 | Darker Color | Couleur plus foncée | dkCl | non |
| 8 | Lighten | Éclaircir | lite | oui |
| 9 | Screen | Écran | scrn | oui |
| 10 | Color Dodge | Densité couleur − | div  | oui |
| 11 | Linear Dodge (Add) | Densité linéaire − (Addition) | lddg | oui |
| 12 | Lighter Color | Couleur plus claire | lgCl | non |
| 13 | Overlay | Incrustation | over | oui |
| 14 | Soft Light | Lumière douce | sLit | oui |
| 15 | Hard Light | Lumière crue | hLit | oui |
| 16 | Vivid Light | Lumière vive | vLit | oui |
| 17 | Linear Light | Lumière linéaire | lLit | oui |
| 18 | Pin Light | Lumière ponctuelle | pLit | oui |
| 19 | Hard Mix | Mélange maximal | hMix | oui |
| 20 | Difference | Différence | diff | oui |
| 21 | Exclusion | Exclusion | smud | oui |
| 22 | Subtract | Soustraction | fsub | oui |
| 23 | Divide | Division | fdiv | oui |
| 24 | Hue | Teinte | hue  | non |
| 25 | Saturation | Saturation | sat  | non |
| 26 | Color | Couleur | colr | non |
| 27 | Luminosity | Luminosité | lum  | non |

(« Séparable » = `is_separable`, `blend.rs:146-148`. Libellés : `blend.rs:75-106` ; clés : `blend.rs:109-140`.)

### 4.4 Styles de calque : 10 (+ Blending Options) (lu)
Ordre de la liste du dialogue Layer Style (`crates/ui-egui/src/layer_style.rs:27-38`, `KINDS`) : Bevel & Emboss, Stroke, Inner Shadow, Inner Glow, Satin, Color Overlay, Gradient Overlay, Pattern Overlay, Outer Glow, Drop Shadow. Champs du dialogue (`layer_style.rs:40-140`, type Slider(min,max,unité) / Color / Blend / Choice / Check / Pattern) et défauts (`layer_style.rs:142-166`) ; commandes moteur `layer.layerStyle.<kind>` et leurs chaînes `params` (`crates/engine/src/layer_style.rs:220-263`, menu Layer › Layer Style).

| Style (commande) | Champs du dialogue (ordre) | Défauts dialogue | Paramètres moteur (en plus) |
|---|---|---|---|
| Drop Shadow (`dropShadow`) | Blend Mode ; Color ; Opacity 0–100 % ; Angle −180–180° ; Use Global Light ; Distance 0–300 px ; Spread 0–100 % ; Size 0–250 px ; Layer Knocks Out Drop Shadow | Multiply, #000000, 75, 120, oui, 5, 0, 5, oui | opacity=75, blend=multiply, angle=120, distance=5, size=5, add, layer |
| Inner Shadow (`innerShadow`) | Blend Mode ; Color ; Opacity ; Angle ; Use Global Light ; Distance 0–300 ; Choke 0–100 % ; Size 0–250 | Multiply, #000000, 75, 120, oui, 5, 0, 5 | opacity=75, add |
| Outer Glow (`outerGlow`) | Blend Mode ; Opacity ; Color ; Spread 0–100 % ; Size 0–250 px ; Range 1–100 % | Screen, 75, #ffffbe, 0, 5, 50 | technique softer/precise, blend=screen |
| Inner Glow (`innerGlow`) | Blend Mode ; Opacity ; Color ; Source Edge/Center ; Choke ; Size | Screen, 75, #ffffbe, edge, 0, 5 | technique softer/precise |
| Stroke (`stroke`) | Size 1–250 px ; Position Outside/Inside/Center ; Blend Mode ; Opacity ; Color | 3, outside, Normal, 100, #000000 | from/to (dégradé), style, angle |
| Color Overlay (`colorOverlay`) | Blend Mode ; Color ; Opacity | Normal, #ff0000, 100 | — |
| Gradient Overlay (`gradientOverlay`) | Blend Mode ; Opacity ; From ; To ; Reverse ; Style Linear/Radial/Angle/Reflected/Diamond ; Angle −180–180° ; Scale 10–150 % | Normal, 100, #000000, #ffffff, non, linear, 90, 100 | angle=90, scale 10..150=100 |
| Pattern Overlay (`patternOverlay`) | Blend Mode ; Opacity ; Pattern ; Angle ; Scale 1–1000 % ; Link with Layer | Normal, 100, (1er motif), 0, 100, oui | phaseX, phaseY |
| Bevel & Emboss (`bevelEmboss`) | Style Inner Bevel/Outer Bevel/Emboss/Pillow Emboss ; Depth 1–1000 % ; Direction Up/Down ; Size 0–250 px ; Soften 0–16 px ; Angle ; Use Global Light ; Altitude 0–90° | inner, 100, up, 5, 0, 120, oui, 30 | style « stroke » en plus ; technique smooth/chiselHard/chiselSoft ; contour, contourRange 1..100=50 ; texture, textureScale 1..1000=100, textureDepth −1000..1000=100, textureInvert, textureLink=true |
| Satin (`satin`) | Blend Mode ; Color ; Opacity ; Angle ; Distance 0–250 px ; Size 0–250 px ; Invert | Multiply, #000000, 50, 19, 11, 14, oui | — |
| Blending Options (`blendingOptions`) | Blend Mode ; Opacity 0–100 % ; Fill Opacity 0–100 % | — | `layer.layerStyle.blendingOptions` : blend, opacity, fillOpacity, blendIf {channel gray/red/green/blue/cyan/…, thisLayer, underlying [noir,blanc] ou 4 valeurs 0..255} (`crates/engine/src/layer_menu_cmds.rs:765`) |

Autres commandes Layer › Layer Style : Copy Layer Style, Paste Layer Style, Clear Layer Style, Global Light… (angle −180..180=120, altitude 0..90=30), Create Layer, Hide All Effects / Show All Effects, Scale Effects… (scale 1..1000=100) (`layer_menu_cmds.rs:765-781`, `extra_cmds.rs:604-635`, `layer_style.rs:265` du moteur ; voir §9).


## 5. Dialogues

Chemins relatifs à `crates/ui-egui/src/` sauf mention. Relevé par lecture (sous-agent dédié, puis relu en partie) ; « (déduit) » marque une conclusion.

### 5.0 Mécanique commune (`dialogs.rs`)
- `egui::Modal`, fond non assombri (`dialogs.rs:91`) ; déplaçable par la barre de titre puis position épinglée (l.112-114, 199-206) ; Échap annule, un clic dehors ne ferme pas (l.207-214).
- Largeurs (l.93-111) : min 380 ; New Document 800 fixe ; Layer Style, `__export`, pipette : max 600 ; autres max 440 ; Preferences 780, Shortcuts 720, autres `prefs_ui` 460 (`prefs_ui.rs:666-672`) ; Save for Web 900, Print 720 (`file_ui.rs:135-143`).
- Aiguillage du corps selon les clés `__` (l.118-165) : NewDocument → `new_doc_ui::body` ; puis `fill_ui`, `rasterize_prompt`, `variables_ui`, `file_ui` (`__web`/`__print`), `color_picker_ui`, `color_range_ui`, `prefs_ui` (`__prefsui`), `__export` → `export_dialog`, `__sizing` → `sizing`, `__adjust` → `adjust_dialog`, `__filter` → `filter_dialog`, `__form` → `view_cmds::form_body`.
- Boutons alignés à droite (l.169-194) : principal « Create » (New Document) / « Export » / « Save… » (Web) / « Print » / « OK » ; Entrée valide (l.183) ; « Apply » seulement pour Preferences, actif s'il y a des changements (l.186-189) ; secondaire « Close » (New Document) sinon « Cancel » (l.190). About et Error : « OK » seul.
- Titre (l.237-259) : New Document, About PhotoCraft, System Info, Layer Style, Error ; pour une commande : `__label` sans « … ».
- Ouverture générique `open_command_dialog` (l.294-310) : Color Range → `adjust_dialog::open` → `filter_dialog::open` si `has_dialog` → sinon confirmation nue (titre + OK/Cancel, OK = `app.run(__command, {})`, l.160, 280-285, 306-309). Routage menu (`menus.rs:399-407`) : `image.imageSize`/`image.canvasSize` → `sizing::open` avant tout.
- Validation (`confirm`, l.262-289) : New Document → `file.new` ; commande → `__command` avec `filter_dialog::params_of` ; `smart_ui::confirm_command` redirige vers `layer.smartFilter.setParams` si `__smartFilter` (`smart_ui.rs:116-121`).

### 5.1 New Document (`new_doc_ui.rs`, `state.rs:814-817`)
- Ouvert par `file.new` sans paramètres (`menus.rs:217-220`), l'écran d'accueil (`canvas.rs:1257`) ou le canal de contrôle (`control.rs:343`).
- Champs initiaux (`state.rs:815`) : name « Untitled-1 », width 1920, height 1080, mode rgb, depth 8, background white ; `resolution` absente → 72 à l'affichage (l.221) et au moteur. Clés d'interface : `__category` (défaut « Recent », l.141), `__preset`, `__unit` (« px », l.222), `__resUnit` (« in », l.255).
- Disposition (l.143-209) : onglets texte soulignés ; en-tête « BLANK DOCUMENT PRESETS ({n}) » ; grille de 3 cartes 164×112 avec vignette à la proportion ; carte « W x H in @ ppi » si ppi ≥ 300, sinon « W x H px @ ppi » (l.111, 190-200). Clic → `apply_preset` (l.105-112).

Préréglages (`CATEGORIES`, l.16-74 ; type `(nom, L px, H px, ppi)`, l.13). Pouces déduits par division par 300.

| Catégorie | Préréglage | L px | H px | ppi |
|---|---|---|---|---|
| Recent (l.17, liste statique — déduit) | Default Photoshop Size | 2100 | 1500 | 300 |
| Recent | HDTV 1080p | 1920 | 1080 | 72 |
| Photo (l.18-28) | Landscape, 6 x 4 | 1800 | 1200 | 300 |
| Photo | Landscape, 7 x 5 | 2100 | 1500 | 300 |
| Photo | Landscape, 10 x 8 | 3000 | 2400 | 300 |
| Photo | Portrait, 4 x 6 | 1200 | 1800 | 300 |
| Photo | Portrait, 5 x 7 | 1500 | 2100 | 300 |
| Photo | Square, 5 x 5 | 1500 | 1500 | 300 |
| Print (l.29-39) | Letter | 2550 | 3300 | 300 |
| Print | Legal | 2550 | 4200 | 300 |
| Print | Tabloid | 3300 | 5100 | 300 |
| Print | A4 | 2480 | 3508 | 300 |
| Print | A3 | 3508 | 4961 | 300 |
| Print | A5 | 1748 | 2480 | 300 |
| Art & Illustration (l.40-43) | Poster | 5400 | 7200 | 300 |
| Art & Illustration | Postcard | 1800 | 1200 | 300 |
| Art & Illustration | Comic Book | 1988 | 3075 | 300 |
| Art & Illustration | Square, 12 x 12 | 3600 | 3600 | 300 |
| Web (l.44-53) | Web Most Common | 1366 | 768 | 72 |
| Web | Web Minimum | 1024 | 768 | 72 |
| Web | Web Large | 1920 | 1080 | 72 |
| Web | MacBook Pro 16" | 3456 | 2234 | 72 |
| Web | iMac 24" | 4480 | 2520 | 72 |
| Mobile (l.54-63) | iPhone 16 | 1179 | 2556 | 72 |
| Mobile | iPhone 16 Pro Max | 1320 | 2868 | 72 |
| Mobile | iPad Pro 13" | 2064 | 2752 | 72 |
| Mobile | Android 1080p | 1080 | 1920 | 72 |
| Mobile | Apple Watch 45mm | 396 | 484 | 72 |
| Film & Video (l.64-73) | HDTV 1080p | 1920 | 1080 | 72 |
| Film & Video | HDTV 720p | 1280 | 720 | 72 |
| Film & Video | UHD 4K | 3840 | 2160 | 72 |
| Film & Video | DCI 4K | 4096 | 2160 | 72 |
| Film & Video | UHD 8K | 7680 | 4320 | 72 |

Panneau « PRESET DETAILS » (colonne droite 260 px, l.212-302) :

| Champ | Widget | Valeurs / plage | Défaut | Réf. |
|---|---|---|---|---|
| Nom | TextEdit 250 px, police 15 | libre | Untitled-1 | l.216-219 |
| Width | value_field 110 px, 0,01–300 000 dans l'unité | converti en px entiers 1–300 000 (l.100-102) ; efface `__preset` | 1920 px | l.223-229 |
| Unité L/H | dropdown 120 px | Pixels, Inches, Centimeters, Millimeters, Points, Picas (`UNITS` l.79-80 ; par pouce : –/1/2,54/25,4/72/6) | px | l.230-233 |
| Height | idem | idem | 1080 px | l.235-241 |
| Orientation | icônes 24 px `rectangle-vertical` « Portrait », `rectangle-horizontal` « Landscape » | échange L/H | selon h>w | l.243-250 |
| Resolution | value_field 110 px, 1–30 000 | stockée en ppi (×2,54 si /cm) | 72 | l.253-259 |
| Unité de résolution | dropdown 120 px | Pixels/Inch, Pixels/Centimeter | in | l.260-264 |
| Color Mode | dropdown 110 px | Grayscale (`gray`), RGB Color, CMYK Color, Lab Color | rgb | l.267-283 |
| Profondeur | dropdown à infobulles 120 px | 8 bit (Integer), 16 bit (Integer), 32 bit (float) (Floating point) (`DEPTH_OPTIONS` l.76) | 8 | l.284-288 |
| Background Contents | dropdown 240 px | White, Black, Background Color, Transparent | White | l.291-301 |

Absents : profil colorimétrique, pixel aspect ratio, Advanced Options, enregistrement de préréglage, plans de travail. Moteur `file.new` (`crates/engine/src/commands.rs:212-261`) : `{"width":u32=1920,"height":u32=1080,"mode":"rgb|gray|cmyk|lab"="rgb","depth":8|16|32=8,"background":"white|black|backgroundColor|transparent|#rrggbb"="white","resolution":ppi=72,"name":str}` ; tailles 1–300 000 ; résolution 1–30 000 ; nom moteur par défaut « Untitled » ; `transparent` crée un calque « Layer 1 » sans fond ; `#rrggbb` accepté mais pas proposé.

### 5.2 Image Size et Canvas Size (`sizing.rs`, `crates/engine/src/image_cmds.rs`)
- Clés communes (`sizing.rs:47-74`) : `__command`, `__label`, `__sizing`, `__origW`, `__origH`, `__origRes`, `__unit`, `__bytesPerPixel` (défaut 4), `width`, `height`. Unité initiale = préférence Units & Rulers › Rulers (`pref_unit`, l.17-28).
- Unités (`UNITS`, l.13-14) : Pixels, Percent, Inches, Centimeters, Millimeters, Points, Picas ; percent relatif à l'origine ; pt = 72/in, pica = 6/in (déduit : indépendant du réglage PostScript/Traditional). Une liste d'unité par ligne, clé `__unit` partagée (l.154-160). Champ dimension : value_field 90 px, ±300 000 px ou ±30 000 autres unités (l.138-152).
- **Image Size** (l.162-259) : « Image Size: » « X (was Y) » (octets K/M/G, l.105-113) ; « Dimensions: » « W px × H px » ; Width:/Height: ; accolade `link`/`unlink` « Constrain proportions » (défaut oui, active seulement avec rééchantillonnage, l.193-219) ; Resolution: 1–30 000 « Pixels/Inch » (pas d'autre unité, l.220-233) ; case Resample (cochée si `resample` ≠ none, l.235-244) ; liste (200 px, l.245-257) : Preserve Details (`preserveDetails`), Bicubic (smooth gradients), Lanczos (sharp), Bilinear, Nearest Neighbor (hard edges). Défaut tiré de Préférences › General › Image interpolation (`pref_resample` l.31-40 : Nearest→nearest, Bilinear→bilinear, BicubicSharper→lanczos, PreserveDetails→preserveDetails, autres→bicubic).
- Moteur `image.imageSize` (`image_cmds.rs:367-374`) : `{"width":px,"height":px,"resolution":ppi,"resample":"bicubic|bilinear|nearest|lanczos|preserveDetails|none"="bicubic"}` ; alias `nearestNeighbor` (l.92-101) ; dimension manquante → proportions gardées ; résolution bornée 1–10 000 côté moteur (l'interface permet 30 000) ; masques, canaux, sélection en bilinéaire ; effets mis à l'échelle ; vecteurs transformés (l.104-146).
- **Canvas Size** (l.261-322) : « Current Size » (Size:, Width:, Height:) ; « New Size » (octets) ; Width:/Height: (négatifs permis en relatif) ; case Relative (défaut non) ; Anchor: grille 3×3 de cases 24 px, défaut center (`anchor_grid` l.325-376 ; ancres `topLeft, top, topRight, left, center, right, bottomLeft, bottom, bottomRight` l.41) ; « Canvas extension color: » (140 px) Foreground / Background (défaut) / White / Black / Transparent.
- Moteur `image.canvasSize` (`image_cmds.rs:375-382`) : `{"width":px,"height":px,"relative":bool=false,"anchor":…="center","extensionColor":"background|foreground|white|black|transparent|#rrggbb"="background"}` ; la couleur d'extension ne remplit que le calque « Background » (l.209-240).

### 5.3 Export As / Save As / Quick Export / Save for Web / Print

**Export As…** (`export_dialog.rs`) — `file.export.exportAs` (Cmd+Alt+Shift+W) et `layer.exportAs` (titre « Export As: <calque> », l.31-42).
- Champs initiaux (l.16-28) : format png, quality 85, transparency oui, scale 100.
- Formats (`FORMATS`, l.14) : PNG (`png`), JPG (`jpg`), WebP (lossless) (`webp`), TIFF (`tif`), TGA (`tga`).
- Colonne « File Settings » 220 px (l.118-150) : Format (130 px) ; si JPG : Quality curseur 1–100 % (défaut 85) ; sinon case Transparency (oui) ; « Image Size » : Scale 1–1000 % + « W × H px ».
- Colonne droite (l.153-181) : aperçu 300×300 sur damier ; estimation « PNG ≈ 1.2M » (encodage proxy ≤ 512 px, l.103-111).
- Export (l.72-91) : `image.imageSize` bicubique ; `layer.flattenImage` si pas de transparence ou JPG. Seule la qualité JPEG est transmise (`ExportSettings { jpeg_quality }`, `lib.rs:147-150`). Absents : métadonnées, conversion sRGB, rééchantillonnage, taille en px, compression PNG/TIFF.
- Sélecteur natif `SAVE_FILTERS` (`apps/photocraft/src/services.rs:24-32`) : Photoshop (psd, psb), PhotoCraft (pcraft), PNG, JPEG (jpg), TIFF (tif), Targa (tga), OpenEXR (exr) — pas de filtre webp (déduit : incohérence).

**Save / Save As** (`menus.rs:14-15, 229-237, 260`, `lib.rs:726-758`) : aucun dialogue d'options ; sélecteur natif, nom suggéré = chemin existant ou `<stem>.psd`, filtre de l'extension en tête (`services.rs:35-44`) ; qualité JPEG par défaut du codec 90 (`crates/codecs/src/options.rs:131`). File › Save écrit en place seulement psd/psb/pcraft (`crates/engine/src/file_cmds.rs:134-136`). Moteur `file.saveACopy` : `{"path":str,"quality":0..12? (JPEG),"layers":bool=true}` (`file_cmds.rs:1049-1053`).

**Open** : filtre « All Formats » (`OPEN_EXTS`, `services.rs:16-19`) = pcraft, psd, psb, png, jpg, jpeg, tif, tiff, webp, gif, bmp, tga, ico, qoi, exr, hdr, pbm, pgm, ppm, pam, pfm, dng, cr2, cr3, nef, nrw, arw, pef, orf, rw2, raf, abr, grd ; plus « PhotoCraft » (pcraft).

**Quick Export as PNG** (`export_dialog.rs:206-229`, `crates/engine/src/web_cmds.rs:822-880`) : suit Export Preferences (format png/jpg/gif/webp, emplacement ask/sameFolder) ; moteur `file.export.quickExport {"path":str?}` (`web_cmds.rs:1184-1191`) ; jpg → qualité `jpegQuality` ; gif → réglages web par défaut ; webp → conversion sRGB optionnelle ; sinon png24 ; métadonnées all/none/copyright. Layer › Quick Export as PNG : toujours PNG 100 % (`export_dialog.rs:45-52`). Export Preferences… ouvre Préférences › Export (`file_ui.rs:62`) ; moteur `{"quickExportFormat":"png|jpg|gif|webp"?,"quickExportLocation":"ask|sameFolder"?,"jpegQuality":1..100?,"metadata":"none|copyright|all"?,"convertToSrgb":bool?}` (`web_cmds.rs:1175-1182`).

**Save for Web (Legacy)…** (`file_ui.rs:181-519`, `web_cmds.rs`) — Cmd+Alt+Shift+S (`web_cmds.rs:1166-1174`).
- Défauts d'ouverture (`open_web` l.185-220, reprend `last_web`) : jpeg, quality 60, palette selective, colors 128, dither diffusion, ditherAmount 88, transparency oui, matte #ffffff, interlaced non, progressive non, optimized oui, embedIcc non, convertToSrgb oui, metadata copyright, percent 100, webSnap 0, vue 2-Up. (Défauts moteur différents : png24, 256 couleurs, `web_cmds.rs:101-121`.)
- Vues : Original, Optimized, 2-Up, 4-Up (l.348-356) ; aperçu 600×470 ; 4-Up = original, courant, deux variantes (l.223-239) ; légende « FORMAT taille » et « N sec @ 56.6 Kbps · N colors » (l.304-317).
- Colonne 250 px (l.390-495) : Preset « [Unnamed] » + GIF 128 Dithered, GIF 128 No Dither, GIF 32 Dithered, GIF 32 No Dither, GIF 64 Dithered, GIF 64 No Dither, GIF Restrictive, JPEG High (q60), JPEG Low (q10), JPEG Medium (q30), PNG-24, PNG-8 128 Dithered (`PRESETS` `web_cmds.rs:241-254` ; « JPEG Maximum » q100 et « JPEG Very High » q80 acceptés mais absents du menu, l.256-285) ; Format GIF / PNG-8 / PNG-24 / JPEG / WBMP (l.183).
  - GIF / PNG-8 (l.407-435) : Palette Perceptual / Selective / Adaptive / Restrictive (Web) / Exact (systemMac, systemWindows, uniform acceptés par le moteur, non proposés) ; Colors 2–256 (128) ; Dither No Dither / Diffusion / Pattern / Noise ; quantité 0–100 % (88) ; Transparency ; Interlaced ; Web Snap 0–100 % (0).
  - JPEG (l.436-441) : Quality 0–100 (60) ; Progressive ; Optimized ; Embed Color Profile.
  - WBMP (l.442-451) : Dither none / diffusion / pattern. PNG-24 (l.452-455) : Transparency, Interlaced.
  - Matte (hex, masqué pour PNG-24 transparent, l.457-465) ; Convert to sRGB (l.467) ; Metadata None / Copyright / Copyright and Contact Info / All (l.468-478) ; « Image Size » Percent 1–1000 % (l.480-487) ; avec tranches : « N slices », Save HTML and Images, All Slices / All User Slices (l.488-494).
- Le moteur accepte aussi `width`, `height`, `resample` (bicubic|bilinear|nearest), `path`, `dir`, `html`, `numbers` (spec l.1171).

**Print** (`file_ui.rs:521-725`) : Printer Setup (Printer, Copies 1–999, Paper `print_cmds::PAPERS`, Portrait/Landscape) ; Color Management (Printer Manages Colors / PhotoCraft Manages Colors / No Color Management ; profil Coated CMYK, sRGB IEC61966-2.1, Adobe RGB (1998) compatible, Display P3, Gray Gamma 2.2 ; intention Perceptual / Relative Colorimetric / Saturation / Absolute Colorimetric ; Black Point Compensation) ; Position and Size (Center, Top/Left 0–100 in, Scale to Fit Media, Scale 1–1000 %) ; Printing Marks (Corner Crop Marks, Center Crop Marks, Registration Marks, Description, Labels) ; Save as PDF. Autres formulaires `__form` (l.63-116) : Contact Sheet II, Create Droplet, Image Statistics, Script Events Manager, Package, Export Paths to File.

### 5.4 Preferences (`prefs_ui.rs`, `crates/engine/src/prefs.rs`)
- Ouverture `edit.preferences.<section>` (`prefs_ui.rs:541-543, 675-680`) ; liste des sections à gauche (170 px), titre + grille 2 colonnes à droite (540 px, défilement max 390) ; « Reset Section » (110 px) ; section sans réglage visible : « These settings aren't available in PhotoCraft yet. » (nom grisé) (l.797-866). Boutons OK / Apply / Cancel (OK = `prefs.set {"path":"","value":…}`, l.1313-1318).
- Widgets générés (`section_fields`, l.927-1030) : booléen → case ; `interface.language` → liste spéciale ; chaîne à `choices()` → liste 220 px ; couleur → bouton couleur + hex ; autre chaîne → TextEdit 260 px ; entier → DragValue dans `range()` ; flottant → DragValue pas 0,1 ; tableau → « N items » + « Clear ».
- Libellés : `humanize(clé)` (l.758-771) + remplacements Psd→PSD, Gpu→GPU, Ui→UI, Mb→(MB), Exif→EXIF, Hud→HUD (déduit : ne s'applique qu'en début, d'où « Memory usage mb », confirmé `i18n/fr.tsv:1766`). Choix : `choice_label` (l.773-790). Réglages masqués : `HIDDEN_UNTIL_IMPLEMENTED` (`prefs.rs:799-863`).
- Sections dans l'ordre (`SECTIONS`, `prefs.rs:772-791`) et contrôles visibles (* = défaut) :
  1. **General** (`prefs.rs:165-197`) : Image interpolation (Bicubic automatic*, Nearest neighbor, Bilinear, Bicubic, Bicubic smoother, Bicubic sharper, Preserve details) ; Zoom with scroll wheel (non) ; Auto show home screen (oui). Masqués : colorPicker, beepWhenDone, exportClipboard, resizeImageDuringPlace, alwaysCreateSmartObjectsWhenPlacing, animatedZoom, zoomResizesWindows, useLegacyFreeTransform.
  2. **Interface** (`prefs.rs:201-241`) : Theme (Pro, Pro medium*, Studio, Studio light, Classic) ; Canvas color (Default*, Black, Dark gray, Medium gray, Light gray, Custom) ; Canvas custom color (#282828) ; Canvas border (Drop shadow*, Line, None) ; UI scale (Auto*, 100 %, 200 %) ; Language (Auto*, English, 日本語, 简体中文, 繁體中文, Español, Русский, Čeština, Français, Bahasa Indonesia, 한국어 ; `prefs_ui.rs:952-959`) ; Show menu colors (oui) ; Show tooltips (oui) ; Show bounding box when dragging layer (non). Masqués : uiFontSize, showChannelsInColor, dynamicColorSliders.
  3. **Workspace** (`prefs.rs:245-267`) : Remember workspace changes (oui) ; 6 masqués.
  4. **Tools** (`prefs.rs:271-305`) : Show tooltips (oui) ; Use shift key for tool switch (non) ; Snap vector tools and transforms to pixel grid (oui) ; Overscroll (oui) ; Right click with painting tools (Brush picker*, Erase) ; Use tablet pressure (oui). Masqués : zoomClickedPointToCenter, enableFlickPanning, varyRoundBrushHardnessOnHud, showTransformationValues, doubleClickLayerMaskLaunchesSelectAndMask.
  5. **History Log** (`prefs.rs:309-321`) : Enabled (non) ; Destination (Metadata*, Text file, Both) ; File path ; Detail (Sessions only, Concise*, Detailed).
  6. **File Handling** (`prefs.rs:325-359`) : Autosave (oui) ; Autosave minutes 1–240 (10) ; Recover on launch (oui) ; Recent file count 0–100 (20) ; Recent files (liste + Clear). Masqués : imagePreviews, lowercaseExtension, saveInBackground, ignoreExifProfileTag, askBeforeSavingLayeredTiff, maximizePsdCompatibility.
  7. **Export** (`prefs.rs:363-381`) : Quick export format (Png*, Jpg, Gif, Webp) ; Quick export location (Ask*, Same folder) ; Jpeg quality 1–100 (85) ; Metadata (None, Copyright*, All) ; Convert to srgb (oui).
  8. **Performance** (`prefs.rs:385-433`, `prefs_ui.rs:870-918`) : Rendering Mode (Automatic (recommended)*, GPU, CPU / Compatibility) + note « Automatic uses GPU acceleration when available and falls back to CPU rendering on errors. » ; Memory usage mb 256–1 048 576 (8192) ; History states 1–1000 (50) ; Cache tile size 256–16 384 (8192) ; bloc « Graphics » (infos GPU, « Applies at next launch. ») ; repli « Advanced » : GPU Backend (Auto*, Vulkan, DirectX 12, Metal, OpenGL, CPU (no GPU acceleration)). Masqués : cacheLevels (1–8, 4), effectCacheMb (16–65 536, 768), legacyCompositing.
  9. **Scratch Disks** (`prefs.rs:437-453`) : `disks` masqué → section vide (code de liste + « Add disk » présent, `prefs_ui.rs:999-1017`) ; défaut [(system temp), activé].
  10. **Cursors** (`prefs.rs:457-476`) : Painting (Standard, Precise, Normal tip*, Full size tip) ; Show crosshair in brush tip (non) ; Show only crosshair while painting (non) ; Other (Standard*, Precise). Masqué : brushPreviewColor (#ff0000).
  11. **Transparency & Gamut** (`prefs.rs:480-502`) : Grid size (None, Small, Medium*, Large ; 4/8/16, l.506-513) ; Grid colors (Light*, Medium, Dark, Red, Orange, Green, Blue, Purple, Custom) ; Custom light #ffffff ; Custom dark #cccccc ; Gamut warning color #808080 ; Gamut warning opacity 1–100 (100).
  12. **Units & Rulers** (`prefs.rs:532-554`) : Rulers (Pixels*, Inches, Centimeters, Millimeters, Points, Picas, Percent) ; Point size (PostScript (72 points/inch)*, Traditional (72.27 points/inch)). Masqués : typeUnits, columnWidth 180, gutter 12, printResolution 300, screenResolution 72.
  13. **Guides, Grid & Slices** (`prefs.rs:566-595`) : Guide color #4affff ; Guide style (Lines*, Dashed lines, Dots) ; Smart guide color #ff00ff ; Grid color #8c8c8c ; Grid style (Lines*) ; Gridline every 0,001–10 000 (1,0) ; Grid unit (Inches*) ; Subdivisions 1–100 (4) ; Slice color #38b5ff ; Show slice numbers (oui).
  14. **Plug-ins** (`prefs.rs:606-625`) : Use additional plugins folder (non) ; Additional plugins folder. Masqués : showExtensionPanels, allowScriptsToConnect, generatorEnabled.
  15. **Type** (`prefs.rs:629-653`) : tout masqué (smartQuotes, missingGlyphProtection, showFontNamesInEnglish, useEscToCommit, textEngine worldReady, fontPreview medium, fillNewTypeLayersWithPlaceholder, recentFonts 10).
  16. **Enhanced Controls** (`prefs.rs:657-668`) : tout masqué (scrubbySliderAcceleration, touchGestures, zoomWithTrackpadPinch, rotateViewWithTrackpad).
  17. **Camera Raw Defaults** (`prefs.rs:672-692`, menu « Camera Raw… ») : tout masqué (colorSpace adobeRgb, bitDepth 16, resolution 300, sharpenFor none, openAsSmartObject, applyAutoTone).
  18. **Integrations** (`prefs.rs:696-707`) : tout masqué (allowAgentControl oui, controlPort 0).
- **Keyboard Shortcuts and Menus** (un seul dialogue, `prefs_ui.rs:701-715, 1034-1220`) : onglets pilule Keyboard Shortcuts (`edit.keyboardShortcuts`, Cmd+Alt+Shift+K), Menus (`edit.menus`, Cmd+Alt+Shift+M), Toolbar (`edit.toolbar`). Recherche « command or shortcut » ; grille groupée par menu (y compris outils temporaires Hand Tool (hold) Space, Zoom In Cmd+Space, Zoom Out Cmd+Alt+Space, `prefs.rs:1174-1178`) ; capture « Press keys… », Échap annule, ⌫/Suppr retire ; conflit « X is already in use by … and will be removed from it when you click OK. » ; Use Default, Delete Shortcut, Reset All to Defaults. Menus : Visible + couleur (none, red, orange, yellow, green, blue, violet, gray) + Show All Menu Items. Toolbar : cases par outil + Restore Defaults (pas de réordonnancement dans l'interface).
- Autres : Preset Manager (Brushes / Custom Shapes / Patterns ; Rename, Delete, Load… .abr), Export/Import Presets (`Presets.pcpresets`), Embedded Profile Mismatch (`prefs_ui.rs:1222-1308`).

### 5.5 Dialogues de paramètres génériques
- **Schéma** (`filter_dialog.rs`) — `has_dialog` (l.147-167) : tous les `filter.*` (sauf Filter Gallery), `select.modify.*`, la liste `PREVIEWED` (l.131-145 : image.adjustments.selectiveColor, colorLookup, shadowsHighlights, replaceColor, matchColor, hdrToning ; image.rotation.arbitrary ; image.mode.indexedColor, bitmap, duotone ; layer.matting.defringe, colorDecontaminate ; layer.layerStyle.scaleEffects), plus image.trim, view.newGuide, select.refineEdge, edit.assignProfile, edit.convertToProfile, view.proofSetup, layer.layerStyle.globalLight, image.mode.colorTable — si la chaîne `params` n'est pas vide. Commandes `edit.*` aussi via `prefs_ui.rs:549-608`.
- Grammaire (`parse_spec`, l.44-107), dans l'ordre : `"a|b|c"` → liste ; `bool[=x]` → case ; `text` → champ texte ; `doc` → document ouvert ; `json`, `[`…, `{`… → non affiché ; `int[N]` → grille N ; `lo..hi[=d]` → plage (défaut = min si absent) ; autre → entier (nombre après `=`, sinon 0). La clé `layer` est ignorée. (Déduit : un défaut `="x"` de liste est ignoré, la première option l'emporte, l.181 ; `str` est rendu comme entier.)
- Widgets (`body`, l.251-374) : plage → unité « px » pour radius, distance, cellSize, horizontal, vertical, height, wavelengthMin/Max, amplitudeMin/Max, maxRadius, size, blur, speed (l.110-128), « ° » pour angle, « % » pour amount si max ≤ 500 ; si min > 0 et max/min > 500 : champ + curseur logarithmique (l.246-288), sinon `slider_row` ; liste 170 px (libellés camelCase → « Camel Case ») ; case ; texte 200 px ; document (« None » + docs) ; grille de value_field −999…999 ; entier −30 000…30 000 (80 px) ; note `__note` ; case « Preview ».
- Aperçu (`canvas.rs:777-809`) : la vraie commande sur un proxy ; facteur k = 1 si ≤ 5 Mpx, sinon ⌈√(px/2,5 M)⌉ (min 2) (`proxy.rs:8-17`) ; paramètres en px divisés par k (`filter_dialog.rs:384-405`) ; cache par hachage.
- **Ajustements** (`adjust_dialog.rs`) : pour brightnessContrast, levels, curves, exposure, vibrance, hueSaturation, colorBalance, blackWhite, photoFilter, channelMixer, posterize, threshold, gradientMap (`adjust_editors.rs:25-39`) : même éditeur que Properties + « Preview » (l.47-70) ; aperçu par calque d'ajustement temporaire sur GPU, sinon proxy ; OK = une étape d'historique.
- **Formulaires `__form`** (`view_cmds.rs:695-756`) : booléen → case ; chaîne avec `__choices` → liste 200 px ; chaîne → texte 260 px ; entier → DragValue ; flottant → DragValue pas 0,5 ; pas d'aperçu.

### 5.6 Écarts relevés (déduits)
1. New Document : ni profil, ni pixel aspect, ni options avancées ; « Recent » statique.
2. Image Size : résolution 30 000 dans l'interface, 10 000 dans le moteur.
3. Export As : WebP sans perte seulement, pas de métadonnées ni de sRGB, pas de filtre webp dans le sélecteur.
4. Save for Web : défauts interface ≠ moteur ; 2 préréglages et 3 palettes du moteur non proposés.
5. Quick Export as PNG suit en réalité le format des Export Preferences.
6. Préférences : env. 60 réglages masqués, 5 sections vides.


## 6. Formats lus et écrits

Chemins relatifs à la racine du dépôt photocraft. Relevé par lecture (sous-agent dédié) ; « (déduit) » = conclusion.

### 6.1 Pile commune
- Tout passe par `photocraft_io::import` / `export` : `.pcraft` natif ; PSD/PSB reconnus par la signature `8BPS` ; raws reconnus par leurs octets ; le reste par `photocraft-codecs` (`crates/io/src/lib.rs:128-145, 157-176`).
- Formats plats : les calques ne sont jamais gardés (« N layer(s) flattened; layers, masks and blend modes are not kept », `crates/io/src/flat.rs:157-158`) ; un document à un seul calque normal, opaque, sans masque est écrit en natif (profondeur et CMJN gardés) (`flat.rs:83-102, 130-155`).
- **`.pcraft`** (L/É) : ZIP (entrées STORE) ou dossier ; `manifest.json`, tuiles 256×256 zstd `tiles/<blake3>.zst`, `blobs` (ICC, EXIF, blocs PSD, objets dynamiques), `thumb.png`, `composite/preview.png` (`crates/format/src/lib.rs:1-19, 47, 104-114`) ; vignette 256 et aperçu 1024 à l'export (`io/src/lib.rs:159-165`) ; dépendances `ruzstd 0.9`, `blake3`, `flate2` ; seule l'image courante des calques vidéo est gardée (`engine/src/video_cmds.rs:3-4`).
- Limites de décodage : 2^18 px de côté, 2^30 pixels, 8 Gio (2 Gio en 32 bits) (`codecs/src/options.rs:19-25`) ; raws 2^28 px et 2 Gio (`raw/src/lib.rs:122-126`).
- Avertissements de décodage `MoreFrames`, `MorePages`, `Truncated` : seule la 1re image/page est importée (`codecs/src/image.rs:137-142`). Orientation EXIF appliquée à la lecture puis remise à 1 (`codecs/src/lib.rs:69-83`).
- Conversions à l'export plat : sans alpha → aplati sur blanc ; CMJN vers format sans CMJN → sRGB géré ; EXR et HDR en sRGB linéaire ; format sans ICC → perceptuel vers sRGB ; Lab via le composite ; CMJN/Lab multicalques en RVB sRGB ; Indexé + PNG → PNG-8 ; Bichromie → RVB (`flat.rs:20-25, 129-130, 161-166, 265-285, 350-402`).
- Contrôle de fidélité (`codecs/src/fidelity.rs:13-55`) : DepthReduced, RangeClipped, AlphaDiscarded, AlphaBinarized, CmykConverted, ColorToGray, PaletteQuantized, LossyCompression, IccDropped, ExifDropped, XmpDropped, DpiDropped, TextDropped, DimensionsExceeded ; fatals : WriteUnsupported, DimensionsExceeded.

### 6.2 Raster plats (`crates/codecs`, `Format` 13 entrées, `format.rs:7-24`, capacités `format.rs:162-194`)
Options par défaut (`options.rs:107-141`) : jpeg_quality 90 (1..100, sert aussi à AVIF) ; jpeg_chroma_subsampling oui (4:2:0) ; png_compression Default (None/Fast/Default/Best) ; png_interlaced non ; webp_lossless oui ; tiff_compression Deflate (None/Lzw/Deflate/PackBits) ; exr_compression Zip16 (None/Rle/Zip1/Zip16/Piz) ; embed_icc oui ; embed_metadata oui.

| Format | Extensions (`format.rs:114-130`) | L/É | Profondeurs | Modes | Métadonnées | Bibliothèque |
|---|---|---|---|---|---|---|
| PNG | png, apng | L/É | 8, 16 | Gray, GrayA, Rgb, Rgba | ICC, EXIF, XMP, DPI, texte | `png 0.18` |
| JPEG | jpg, jpeg, jpe, jfif | L/É | 8 | Gray, Rgb, Cmyk | ICC, EXIF, XMP, DPI | `zune-jpeg 0.5` (L), `jpeg-encoder 0.6` (É) |
| TIFF | tif, tiff | L/É | 8, 16, 32f | Gray(A), Rgb(A), Cmyk(A) | ICC, XMP, DPI, texte | `tiff 0.11` |
| WebP | webp | L/É (sans perte seulement) | 8 | Rgb, Rgba | ICC, EXIF, XMP | `image-webp 0.2` |
| GIF | gif | L/É | 8 | Rgba | — | `image` |
| BMP | bmp, dib | L/É | 8 | Rgb, Rgba | — | `image` |
| TGA | tga, icb, vda, vst | L/É | 8 | Gray(A), Rgb(A) | — | `image` |
| ICO | ico | L/É (≤ 256×256) | 8 | Rgba | — | `image` |
| Netpbm | pnm, pbm, pgm, ppm, pam, pfm | L/É | 8, 16, 32f | 6 dispositions | — | maison |
| QOI | qoi | L/É | 8 | Rgb, Rgba | — | `image` |
| OpenEXR | exr | L/É | 16f, 32f | Gray(A), Rgb(A) | — | `exr 1.73` + `half 2` |
| Radiance HDR | hdr | L/É | 32f | Rgb | — | `image` |
| AVIF | avif | É seule, feature `avif` désactivée par défaut | 8 | Rgb, Rgba | — | ravif via `image` |

Détails : PNG — palettes et < 8 bits étendus, iCCP/eXIf/tEXt/zTXt/iTXt, XMP `XML:com.adobe.xmp`, pHYs → DPI, APNG : 1re image + avertissement, IDAT parallèle > 4 Mo, PNG-8 indexé 1–256 couleurs + tRNS (`codecs/codecs/png.rs:13-414`). JPEG — gris, YCbCr, CMJN Adobe inversé, YCCK ; scanner de marqueurs APP0/APP1/APP2/APP14 ; CMJN toujours 4:4:4 ; max 65535² (`jpeg.rs:1-267`, `format.rs:151-158`). TIFF — 1er IFD seulement (`MorePages`), 1/2/4 bits → 8, U32 → U16, F16 lu, F64 → F32, WhiteIsZero inversé, balises texte ImageDescription/Make/Model/Software/DateTime/Artist/Copyright ; raws TIFF renvoyés vers `photocraft-raw` ; écriture LZW/Deflate/PackBits avec prédicteur, alpha non associé, ICC (34675), XMP (700) (`tiff.rs:1-451`). WebP — lecture avec/sans perte ; écriture avec perte refusée « lossy WebP encoding needs libwebp (C) » ; max 16384² (`webp.rs:33-42`). GIF/BMP/TGA/ICO/QOI/HDR via `image` 0.25 (`via_image.rs`) : ICC/EXIF lus mais pas réécrits ; GIF 1re image ; HDR marqué avec perte. AVIF : lecture non prise en charge (« needs dav1d (C) », `format.rs:54-58`). Netpbm : P1–P7, PFM ; écrit PFM/P5/P6/P7 (jamais P1–P4, déduit) (`pnm.rs`). EXR : 1re couche pleine résolution, lignes, compressions sans perte (`exr.rs`). Formats « web » (`codecs/src/web.rs`) : GIF89a indexé (LZW maison), GIF animé (boucle NETSCAPE2.0), WBMP 1 bit L/É, JPEG RVB progressif pour Save for Web (4:2:0 si qualité < 90 ; Huffman optimisé désactivé en baseline 4:2:0 à cause d'un défaut de `jpeg-encoder 0.6`, l.308-313).

### 6.3 Raws d'appareil (`crates/raw`, lecture seule, sans dépendance)
- Extensions reconnues : dng, cr2, cr3, nef, nrw, arw, srf, sr2, pef, orf, rw2, raf (`raw/src/lib.rs:108`).
- Décodés : DNG non compressé et lossless-JPEG, bandes et tuiles, CFA et LinearRaw (refusés : X-Trans/non-Bayer, Deflate flottant, avec perte, JPEG XL ; opcode GainMap seul) ; CR2 lossless (sRAW/mRAW refusés) ; TIFF/EP non compressé (NEF, ARW, PEF…, NEF/PEF compressés refusés) ; ARW compressé Sony (cRAW, largeur multiple de 32) ; RW2 RawFormat 5 ; ORF non compressé (`dng.rs`, `cr2.rs`, `tiffep.rs`, `sony.rs`, `rw2.rs`, `orf.rs`, `sensor.rs:198-214`).
- Non décodés : CR3, RAF (`lib.rs:207-208`) → aperçu JPEG embarqué 8 bits avec avertissement (`io/src/raw.rs:63-77`).
- Développement : RVB 16 bits ProPhoto (D50, gamma 1,8), dématriçage AHD par défaut (Bilinear, MHC dispo) ; profil ProPhotoCompat (`lib.rs:13-16, 64`, `demosaic.rs:22-31`, `io/src/raw.rs:42-61`).

### 6.4 PSD / PSB (`crates/psd` + `crates/io`)
- Lecture/écriture « byte-stable » v1 et v2 ; compressions Raw, RLE, ZIP, ZIP+prédiction dans les deux sens (`psd/src/lib.rs:1-22`, `compression.rs:20-31`) ; 300 000 px, 1–56 canaux, 1/8/16/32 bits (`header.rs:7-9, 152-166`) ; modes Bitmap, Grayscale, Indexed, RGB, CMYK, Multichannel, Duotone, Lab ; dépendance `flate2` seule.
- **Import** (`io/src/psd_import.rs`) : Gris/RVB/CMJN/Lab 8-16-32 en calques ; Bitmap, Indexed (table gardée), Duotone (encres gardées brutes, affichage gris) aplatis en 8 bits avec avertissement ; Multichannel = canaux d'encre. Calques raster, masques utilisateur et « real mask » (densité, feather), visibilité, opacité, fond, écrêtage, verrous `lspf`, couleur `lclr`, Blend If, `brst`, ids ; groupes ouverts/fermés ; calques liés (1026) ; 27 modes + Pass Through (clé inconnue → Normal + avertissement). Réglages : 16 clés `levl curv hue2 brit nvrt thrs post expA vibA blnc mixr grdm phfl selc blwh clrL` (`adjust_map.rs:18-19` ; dégradés de bruit, LUT par profil, mixeur CMJN, versions inconnues conservés tels quels). Remplissages `SoCo`, `GdFl`, `PtFl` ; formes `vsms`/`vmsk`, `vstk`, `vscg`, `vogk` ; masques vectoriels ; texte `TySh` + EngineData + `Txt2`, styles de caractère/paragraphe ; objets dynamiques `SoLd`, `PlLd`, `SoLE` (transformation, perspective, warp), filtres dynamiques `filterFX` (non implémentés → `psd.unsupportedFilter` conservé), masque de filtre `FEid`/`FXid`, fichiers liés `lnk2`/`lnk3`/`lnkD` ; effets `lfx2`, `lfxs`, `lmfx` (DrSh, IrSh, OrGl, IrGl, FrFX, SoFi, GrFl, patternFill, ChFX, ebbl ; ancien `lrFX` partiel) ; plans de travail `artb`/`artd`/`abdd` ; ressources : résolution, ICC, XMP, EXIF, repères (1032), lumière globale, tracés (2000–2997, 1025, 2999), couches alpha et ton direct (1045, 1077, 1007), Masque rapide (1022), compositions (1065, `cmls`), tranches (1050 v6–8), notes `Anno`, mesure (1074), comptage (1080), motifs `Patt`/`Pat2`/`Pat3` ; tout bloc non modélisé est conservé.
- **Export** (`io/src/psd_export.rs`) : PSB si demandé, extension `.psb`, côté > 30 000 px ou > 2 Go ; Gris/CMJN/Lab tels quels, le reste en RVB (Indexed → RVB, Bitmap/Duotone → gris, avertissement) ; Multichannel dédié ; RLE (ZIP+prédiction en 32 bits) ; `Lr16`/`Lr32` ; `hdrt`/`hdra` en 32 bits ; blocs réécrits à l'identique s'ils décodent encore, sinon régénérés ; texte : TySh généré sinon pixels ; effets `write_lfx2` ; objets liés embarqués (« PSD export keeps no external links »), `.pcraft` imbriqué en PSB (8 niveaux) ; ≤ 56 canaux ; Masque rapide 1022 ; ≤ 998 tracés ; compositions et tranches régénérées (tranches v6) ; apparence des compositions non écrite ; pas de `lnkE`.

### 6.5 Fichiers de préréglages

| Fichier | Lecture | Écriture | Références |
|---|---|---|---|
| .abr (pinceaux) | v1/v2 et v6–v10 | non dans l'application (`write_v12`/`write_v6` pour tests) | `psd/src/abr.rs:1-39, 353-367` ; `io/src/abr_map.rs` ; `brush.presets.importAbr` |
| .grd (dégradés) | v5 seulement (v3 refusée ; bruit ignoré) | non | `psd/src/grd.rs` ; `preset_import_cmds.rs:180-223` |
| .pat (motifs) | oui (`8BPT`) | oui | `psd/src/patterns.rs` ; `pattern.import` / `pattern.export` |
| .cube | oui (1D étendues en 33³, bord ≤ 129) | oui (`file.export.colorLookupTables`, taille 2..256 = 33) | `cms/src/lutfile.rs:20, 85-207` ; `engine/src/file_cmds.rs:891-916` |
| .3dl | oui | non | `lutfile.rs:145-175` |
| .look (SpeedGrade XML) | oui | non | `lutfile.rs:177-194` |
| .icc / .icm | oui (v2/v4) | encodeur v4.3 interne (pas de commande d'export, déduit) | `cms/src/lib.rs`, `write.rs` |
| préréglages JSON `photocraft-presets` (`.pcpresets`) | oui | oui | `engine/src/edit_menu_cmds.rs:859-905` |
| .pcdroplet / actions JSON | oui | oui | `automate_cmds.rs:289, 536` |
| .aco .ase .asl .csh .tpl .atn .acv .ahu .alv | non | non | aucune occurrence (déduit) |

8 « looks » intégrés procéduraux (`lutfile.rs:219-228`).

### 6.6 Polices (`crates/text`)
`parley 0.11` (complex-scripts), `skrifa 0.44` ; Inter (Regular, Medium, SemiBold) et JetBrains Mono embarqués (`text/src/fonts.rs:21-31`) ; dossiers système scannés pour ttf, otf, ttc, otc (8 niveaux, `fonts.rs:335-350`) ; WOFF/WOFF2/Type 1 absents (déduit).

### 6.7 CLI `photocraft-cli convert`
`convert <in> <out> [--format <ext>] [--quality <1-100>]` (`apps/photocraft-cli/src/lib.rs:17-18, 62, 168-175`) ; seule la qualité JPEG/AVIF est exposée ; `batch` : entrées pcraft, psd, psb et formats codecs (pas les raws), sortie par défaut = extension d'entrée sinon png (`lib.rs:284-313`).

### 6.8 PDF, SVG, GIF animé, vidéo, HTML
- PDF : écriture seule — `file.print` (PDF 1.4, XObject Flate Gris/RVB/CMJN, ICC, repères, `print_cmds.rs:1-203`) et `file.export.artboardsToPdf` (une page JPEG par plan de travail, qualité 0..12 = 10, `artboard_cmds.rs:359-494`) ; PDF placés embarqués sans décodage.
- Illustrator : `file.export.pathsToIllustrator` (PostScript AI3, `print_cmds.rs:10-12, 578`).
- SVG : ni import ni export (déduit).
- HTML : tableau de tranches par Save for Web (`web_cmds.rs:4-6, 792`).
- GIF animé : `file.export.renderVideo` (palette adaptative 256 par image, délai 100/fps cs, boucle infinie, `video_cmds.rs:309-331`) ; à l'import, 1re image seulement.
- Vidéo : aucun codec (« Clean-room; no proprietary codec », `video_cmds.rs:294-295`) ; import d'une image ou d'un dossier de séquence (png, jpg, jpeg, tif, tiff, webp, bmp, gif, tga, exr, pcraft, psd ; 30 i/s par défaut) ; export en séquence `{dir}/{stem}_NNNN.{format}` (png par défaut) ou GIF.
- Génération d'assets : png, png8, png24, png32, gif, webp, jpg (`web_cmds.rs:985-1001`). Qualité « Photoshop » 0..12 → 1..100 par `q/12*99+1` (`file_cmds.rs:167-174`). `file.package` : pcraft, psd, psb.

### 6.9 Filtres des sélecteurs de fichiers
- Ouvrir (natif et web) : pcraft psd psb png jpg jpeg tif tiff webp gif bmp tga ico qoi exr hdr pbm pgm ppm pam pfm dng cr2 cr3 nef nrw arw pef orf rw2 raf abr grd + filtre « PhotoCraft » (`apps/photocraft/src/services.rs:14-19`, `apps/photocraft-web/src/web.rs:14-19`). Lisibles mais absents du filtre : jpe, jfif, dib, icb, vda, vst, pnm, apng, srf, sr2.
- Enregistrer sous : Photoshop (psd, psb), PhotoCraft (pcraft), PNG, JPEG (jpg), TIFF (tif), Targa (tga), OpenEXR (exr) (`services.rs:21-43`).
- Formulaires : Droplet, Image Processor, Batch → same/png/jpg/psd/tiff ; Layers/Comps/Artboards to Files → png jpg psd tiff webp bmp (`file_ui.rs:83`, `view_cmds.rs:846-911`).
- Dossiers des commandes batch du moteur : psd psb pcraft png jpg jpeg tif tiff webp gif bmp tga exr hdr qoi ico pnm ppm pgm dng cr2 nef nrw arw pef (`engine/src/file_cmds.rs:117-121`).


## 7. Thème et design (lu, `crates/ui-egui/src/theme.rs` sauf mention)

### 7.1 Thèmes
Cinq thèmes (`ThemeKind`, l.15-26 ; `ALL` l.29) ; **défaut = Pro (Medium Gray)** (`#[default]` l.20 et `state.rs:768`) — la doc `docs/ui-design.md` dit encore « Pro (default) », le code fait foi.

| id (`window.theme.<id>`) | Libellé | Sombre | Grammaire Photoshop (`pro`) |
|---|---|---|---|
| pro | Pro (Dark) | oui | oui |
| proMedium | Pro (Medium Gray) — **défaut** | oui | oui |
| studio | Studio (Dark) | oui | non |
| studioLight | Studio (Light) | non | non |
| classic | Classic (Windows 2000, biseaux) | non | non |

Bascule : bouton soleil/lune 28 px dans la barre de titre (`sun` en thème sombre, `moon` en clair, infobulle « Switch theme »), cycle `next()` dans l'ordre ci-dessus (`panels.rs:326-330`, `theme.rs:49-52`), juste à gauche du bouton Discord (`message-square` 14 px + « Discord », 12 px, infobulle « Join the ArtCraft Discord (…) », `panels.rs:331-339`). Menu Window › Theme (5 entrées) et Window › Next Theme (`menus.rs:49-54`). `ui.set {"theme":…}` accepte aussi « dark », « medium », « light », « win2000 »… (`from_name`, l.53-62).

### 7.2 Jetons de couleur (hex) par thème (`Tokens::for_kind`, l.111-262)
ProMedium hérite de Pro pour les champs non listés (l.113-131).

| Jeton | Pro | ProMedium | Studio | Studio Light | Classic |
|---|---|---|---|---|---|
| chrome (barres, titre, outils) | #323232 | #535353 | #141415 | #F6F6F8 | #D4D0C8 |
| canvas (fond du canevas) | #282828 | #282828 (hérité) | #0E0E0F | #E2E2E6 | #808080 |
| canvas_dot | #282828 | #282828 | #2E2E32 | #C8C8CE | #808080 |
| dock | #1E1E1E | #424242 | #111112 | #F0F0F3 | #D4D0C8 |
| card (panneaux) | #323232 | #535353 | #1A1A1C | #FCFCFD | #D4D0C8 |
| card_border | #1E1E1E | #424242 | #28282C | #DEDEE4 | #808080 |
| field (champs) | #242424 | #454545 | #232326 | #F2F2F5 | #FFFFFF |
| field_border | #4A4A4A | #686868 | #343439 | #D6D6DC | #808080 |
| hover | #424242 | #626262 | #2C2C30 | #E8E8ED | #E2DED6 |
| pressed | #4E4E4E | #707070 | #38383E | #DCDCE2 | #BEBAB2 |
| text | #DEDEDE | #EEEEEE | #ECECF0 | #18181C | #000000 |
| text_dim | #B2B2B2 | #D4D4D4 | #96969E | #60606A | #404040 |
| text_faint | #808080 | #A0A0A0 | #606068 | #9696A0 | #808080 |
| icon | #C8C8C8 | #E2E2E2 | #C4C4CC | #3C3C44 | #000000 |
| accent | **#378EF0** | #378EF0 | #8B7CF6 | #6C5CE7 | #0A246A |
| accent_soft | #4E4E4E | #6E6E6E | #8B7CF6 α46 | #6C5CE7 α36 | #0A246A |
| accent_border | #378EF0 | #378EF0 | #A094FF α110 | #6C5CE7 α120 | #0A246A |
| accent_text | #FFFFFF | #FFFFFF | #D6D0FF | #5040C8 | #FFFFFF |
| separator | #1E1E1E | #3E3E3E | #26262A | #E2E2E8 | #808080 |
| shadow | noir α150 | noir α150 | noir α140 | noir α50 | noir α0 |
| primary_bg | #378EF0 | #378EF0 | #F6F6F8 | #141418 | #D4D0C8 |
| primary_text | #FFFFFF | #FFFFFF | #0C0C0E | #FAFAFC | #000000 |
| danger | #EC5B62 | #EC5B62 | #F06060 | #D23C3C | #A00000 |
| warning | #E8B046 | #E8B046 | #F0BE5A | #BE8214 | #806000 |
| tab_strip | #262626 | #4A4A4A | transparent | transparent | #D4D0C8 |
| row_selected | #525252 | #6B6B6B | transparent | transparent | #0A246A |
| histogram_bg | #282828 | #282828 | #0E0E0F | #282828 | #282828 |
| histogram_level | 225 | 225 | 225 | 240 | 240 |

Rayons (`radius_sm` / `radius` / `radius_lg`) : Pro et ProMedium 3 / 4 / 6 ; Studio et Studio Light 6 / 8 / 12 ; Classic 0 / 0 / 0 (biseaux `bevel: true`). Couleurs de menu (Edit › Menus) : red #BE3C3C, orange #C87828, yellow #BEAA28, green #3C9646, blue #326EC8, violet #8250BE, gray #787878, appliquées à 55 % (`menus.rs:725-737, 864`). Le surlignage des menus en Pro est la couleur `accent` avec texte blanc, rayon 3, padding 10×4 (`menus.rs:827-835`). Rectangle visible du Navigator #FF5454 (`panels.rs:1111`).

### 7.3 Style egui global (`apply`, l.311-372)
- Visuals : `panel_fill` = chrome ; `window_fill` = card ; bordure fenêtre 1 px card_border ; `extreme_bg_color` = field ; rayon fenêtre = radius_lg, rayon menu = radius ; ombre fenêtre (0,10) flou 32, ombre popup (0,6) flou 20 ; sélection = accent (Pro et Classic) sinon accent_soft ; poignées rondes ; widgets inactifs/survol/actifs/ouverts : fond field/hover/pressed/hover, bordure field_border (accent_border à l'appui), rayon radius_sm, pas d'expansion.
- Typographie : Small 10,5 ; Body 12 (Pro) / 12,5 ; Button 12 / 12,5 ; Heading semibold 15 ; Monospace 12 (l.346-353).
- Espacements : item_spacing 8×6 ; button_padding 10×4 ; interact_size 24×24 ; slider_width 150 ; combo_width 120 ; menu_margin 6 ; window_margin 16 ; icon_width 14 ; tooltip_width 280 ; barres de défilement fines (pleines en Classic) (l.354-367). Délai d'infobulle 0,35 s (`TOOLTIP_DELAY`, l.373) ; écart entre rangées de panneau `ROW_GAP` 4 (l.376-378).
- Polices (`install_fonts_with`, l.274-299) : **Inter** Regular / Medium / SemiBold (UI, familles nommées `medium`, `semibold`) et **JetBrains Mono** Regular (chiffres) — fichiers `assets/fonts/Inter-Regular.ttf`, `Inter-Medium.ttf`, `Inter-SemiBold.ttf`, `JetBrainsMono-Regular.ttf` (OFL) ; polices CJK système en repli chargées à la demande (`cjk_fonts.rs`).

### 7.4 Dimensions de la chrome (lu)

| Élément | Pro | Studio / Classic | Source |
|---|---|---|---|
| Barre de titre + menus (même rangée) | 32 px | 38 px | panels.rs:287-289 |
| Barre d'options | 36 px | 42 px | panels.rs:399-401 |
| Barre d'onglets de document | 26 px, police 11,5, onglet = texte + 42, croix `x` 10 px | idem | canvas.rs:1093-1160 |
| Barre d'état | 24 px | 30 px | panels.rs:850-851 |
| Barre d'outils (largeur / bouton / marge) | 40 / 30 / 5 | 50 / 36 / 7 | panels.rs:56 |
| Icône dans un bouton | 52 % de la boîte (`box*0.52`) | idem | icons.rs:131-135 |
| Rail de droite (largeur / bouton) | 36 / 28 | 44 / 32 | panels.rs:911 |
| Dock (défaut, plage) | 290, 250–520 | 300, 250–520 | panels.rs:943, 973 |
| Rangée de calque / vignette | 32 / 24 | 46 / 34 | panels.rs:1580, 1621 |
| Rangée d'historique | 24 | 24 | panels.rs:1839 |
| Champ numérique (`value_field`) | hauteur 24 | 24 | widgets.rs:132-134 |
| Bouton primaire/secondaire | hauteur 28, pilule (rayon h/2+2), texte medium 13, padding 28 | hauteur 30, rayon radius_sm+2 | widgets.rs:294-330 |
| Curseur (`slider`) | hauteur 18, bouton 10×16 | idem | widgets.rs:173-221 |
| Interrupteur (`toggle`) | 30×17 | idem | widgets.rs:255-262 |
| Case à cocher | 14×14 | idem | widgets.rs:464-469 |
| Séparateur vertical `vline` | 9 de large | idem | widgets.rs:369-371 |
| Liste déroulante | hauteur popup max 420, chevron dessiné | idem | widgets.rs:387-400 |
| Menu déroulant (largeur min) | 220 | 220 | menus.rs:766 |
| Barre de menus : padding bouton | 6×3, sans espacement | idem | menus.rs:760-761 |
| Barre de titre : liste d'espace de travail | 130 px (Essentials, Photography, Painting, Graphic and Web) ; bouton recherche `search` 28 px « Search commands » (Cmd+K) | idem | panels.rs:309-325 |

Titre de fenêtre centré entre les menus et les contrôles (écart min 16, `TITLE_GAP`, police medium 13), « nom  • » si modifié (`panels.rs:300, 344-375`). Lavis violet en bas de la barre d'outils en Studio sombre (RGBA 90,70,190,34 sur 260 px, `panels.rs:74-89`).

### 7.5 Icônes et marque
112 SVG Lucide (`assets/icons/`, licence `LICENSE-lucide.txt`), dont 3 propres (`eraser-background`, `eraser-magic`, `slice-knife` — déduit : absents de Lucide). Icône d'application `assets/app-icon/` (photocraft.svg, photocraft-small.svg, .ico, .icns, 1024 png, hicolor) ; marque ArtCraft `docs/brand/`. Surcharges de jetons à chaud en debug : `PHOTOCRAFT_THEME_FILE=tokens.json` (`theme.rs:470-599`).


## 8. Gestes, modificateurs, barre d'état et infobulles

Chemins relatifs à `crates/ui-egui/src/` sauf mention. Notation : ⌘ = Cmd sur macOS, Ctrl ailleurs ; ⌥ = Alt ; ⇧ = Shift. Relevé par lecture (sous-agent dédié).

### 8.A Gestes, modificateurs, raccourcis hors menu

**Notation et aiguillage** (`shortcuts.rs`)
- `parse` lit « Cmd+Shift+N » (Cmd = COMMAND, Shift, Alt, Ctrl ; symboles = - [ ; ' ]) (l.10-34). `pretty` : macOS ⌘ ⇧ ⌥ ↩ ⌫ concaténés ; ailleurs Cmd → **Ctrl**, joint par « + » (l.39-53). `key_matches` : modificateurs exacts, `=` accepte `+`, Delete = Backspace, ponctuation décalée acceptée (l.93-127). ⌘+ ⌘- ⌘0 ⌘1 restent actifs sous un dialogue (l.140-156). Presse-papiers : Copy/Cut/Paste → ⌘C/⌘X/⌘V ; Windows ⇧Delete = Remplir ; Linux Ctrl+Insert / Shift+Insert (l.165-228).
- Priorités (`handle`, l.230-372) : Camera Raw ouvert (aucun) → menu ouvert → Liquify → dialogue (zoom seul) → champ texte (⌘ et F seulement) → déformations (↩/Esc) → transformation libre (↩ valide, Esc annule) → flèches de décalage → tracé Plume (↩ termine, Esc abandonne) → texte en ligne → table des raccourcis → lasso polygonal / recadrage (↩ valide, Esc annule) → touches d'outils (la touche du groupe courant fait tourner le groupe ; avec la préférence « Use shift key for tool switch », seul ⇧+touche fait tourner) → ⇧[ / ⇧] dureté ±25 % (outils de type brosse) → [ / ] taille ÷1,25 / ×1,25 (1–2500) → chiffres.
- `shortcut_dispatch.rs` : table fusionnée UI_COMMANDS → moteur → catalogue → surcharges → secondaires, triée par nombre de modificateurs (l.51-85) ; `edit.fill` a aussi ⇧Backspace (l.44) ; commande désactivée → « X is not available: raison » (l.222-227).

**Raccourcis par défaut hors menu**

| Touche | Effet | Source |
|---|---|---|
| V M L W C I J B S Y E G O P T A U H Z | outils (voir §2.2 ; W : Magic Wand → Quick Selection → Object Selection) | `state.rs:218-238` |
| Space (tenu) | Main temporaire | `crates/engine/src/prefs.rs:1175`, `hold_keys.rs` |
| ⌘Space (tenu) | Zoom avant temporaire (glisser = continu) | `prefs.rs:1176` |
| ⌘⌥Space (tenu) | Zoom arrière temporaire | `prefs.rs:1177` |
| F | cycle des modes d'écran | `menus.rs:33` |
| ⌘⌥T | Free Transform a Copy | `menus.rs:34` |
| X / D | permuter / couleurs par défaut | `engine/src/commands.rs:751, 755` |
| ⌥⌫ / ⌘⌫ | remplir premier plan / arrière-plan | `engine/src/fill_key_cmds.rs:48, 58` |
| ⌥⇧⌫ / ⌘⇧⌫ | idem en préservant la transparence | `fill_key_cmds.rs:68, 78` |
| ⇧Backspace | Remplir… (second raccourci) | `shortcut_dispatch.rs:44` |
| ⌘2 … ⌘9 | cibler composite / canaux 3–9 | `engine/src/channel_cmds.rs:1586-1593` |
| ⌥] / ⌥[ | calque au-dessus / en dessous | `engine/src/layer_nav_cmds.rs:97-98` |
| ⌥. / ⌥, | calque du haut / du bas | `layer_nav_cmds.rs:99-100` |
| ⌥⇧] / ⌥⇧[ | ajouter le calque au-dessus / en dessous à la sélection | `layer_nav_cmds.rs:101-102` |
| ⌘⌥⇧E / ⌘⌥E | Stamp Visible / Stamp Down | `engine/src/stamp_cmds.rs:149, 159` |
| ⌘↩ | tracé → sélection | `engine/src/vector_cmds.rs:1352` |
| 0–9 / ⇧0–9 | opacité / flux ou fond (voir ci-dessous) | `opacity_keys.rs` |
| [ ] / ⇧[ ⇧] | taille / dureté de la brosse | `shortcuts.rs:343-369` |
| flèches (⇧, ⌥) | décalage 1 px / 10 px / duplication | `move_mods.rs:158-174` |

Q (Masque rapide) est un item de menu (`menu_catalog.rs:529`). **Absents** (déduit, recherche négative) : Tab pour masquer les panneaux, H tenu (vue aérienne), R (rotation de la vue), double-clic sur Main/Zoom.

**Touches chiffrées** (`opacity_keys.rs`) : 1 = 10 % … 9 = 90 %, 0 = 100 % ; deux chiffres en moins de 800 ms = valeur exacte (4 puis 5 = 45 %) ; ignoré avec ⌘/Ctrl/⌥ ; Brush/Eraser : opacité (⇧ = flux) ; Pencil : opacité ; Gradient/Paint Bucket : opacité de remplissage ; autres outils : opacité du calque (⇧ = fond), Background ignoré (l.14, 33-120).

**Molette et zoom** : défilement = panoramique, ⇧ = horizontal, pincement ou ⌘+molette = zoom autour du pointeur, ⌥+molette = 5 % par cran, préférence « Zoom with scroll wheel » (`wheel_nav.rs:1-87`) ; outil Zoom : Scrubby (glisser droite/gauche, 100 points = ×2, 1 %–6400 %), sinon rectangle ; clic = cran avant, ⌥-clic = arrière (`zoom_tool.rs`, `canvas.rs:1755-1757`) ; bouton du milieu = Main (`canvas.rs:1616-1621`).

**Sélections** : ⇧ ajoute, ⌥ soustrait, ⇧⌥ intersecte (`tool_feedback.rs:61-70`) ; Rect./Ellipse : ⇧ carré/cercle, ⌥ depuis le centre ; un modificateur tenu à l'appui choisit le mode, il ne contraint qu'après relâché/repressé (`canvas.rs:83-104`, #188) ; Space déplace pendant le tracé ; < 2 px = désélection ; Fixed Ratio/Size l'emportent sur ⇧ (`chrome_ui.rs:176-192`). Lasso : < 3 points = désélection. Polygonal : clic = sommet, clic à < 8 points du premier (≥ 3 sommets) ou double-clic ferme, ↩ ferme, Esc annule (`canvas.rs:2533-2547, 1761-1764`).

**Recadrage** (`crop_ui.rs`) : hors du cadre = nouveau cadre (⇧ carré, ⌥ centre, Space déplace) ; dedans = déplacer ; bords/coins (8 points) = redimensionner (⇧ rapport, ⌥ centre) ; ↩ valide, Esc annule ; pas de rotation.

**Déplacement** (`move_mods.rs`) : ⇧ verrouille l'axe dominant (hystérésis 8°) ; ⌥ à l'appui duplique (une étape « Duplicate + Move ») ; flèches 1 px, ⇧ 10 px, ⌥ duplique ; aussi pendant la transformation ; ⌘-clic sélectionne le calque sous le pointeur (inverse l'Auto-Select), ⇧ ajoute (`canvas.rs:2303-2308`) ; repères déplaçables, supprimés si sortis du canevas. *(Déduit, non compilé : `arrow_keys` consomme d'abord `Modifiers::NONE` et egui ignore ⇧ dans `consume_key` (`shortcuts.rs:341-342`) — ⇧/⌥+flèche risquent de donner 1 px sans duplication.)*

**Peinture** : ⇧ en glissant = ligne droite 0/45/90° (verrouillée après 3 points) ; ⇧-clic = ligne depuis la fin du trait précédent ; Dégradé : ⇧ cale par 45° (`stroke_constraint.rs`) ; ⌥ = pipette pour Brush, Pencil, Gradient, Paint Bucket (`canvas.rs:2172-2194`) ; Pipette : ⌥-clic = arrière-plan ; Clone/Healing : ⌥-clic = source ; ⌥+clic droit glissé (Win/Linux) ou Ctrl+⌥ glissé : horizontal = diamètre, vertical = dureté (200 points = 0→100 %), 1–5000 (`brush_resize.rs`) ; clic droit avec outil de peinture = sélecteur de brosse, ou gomme si la préférence « Erase » ; ⌘+clic droit = liste des calques (`paint_mouse.rs`).

**Transformation libre** (`transform_tool.rs`) : coin = échelle proportionnelle, ⇧ libère ; bord = un axe ; ⌥ = autour du point de référence ; ⌘+coin = déformation ; ⌘⌥⇧+coin = perspective ; ⌘+bord = inclinaison ; hors de la boîte = rotation, ⇧ = 15° ; dedans = déplacer ; ⌥-clic place le point de référence ; Warp : ⌥-clic = découpe rapide ; ↩ ou double-clic valide, Esc annule ; flèches déplacent ; ⌘⌥T sur une copie (l.1-9, 636-914).

**Texte** (`type_tool.rs:201-571`) : clic = texte ponctuel, glisser ≥ 4 points = paragraphe ; ⇧-clic étend ; double-clic = mot ; Backspace/Delete (⌥ = mot, ⌘Backspace = début de ligne) ; ⌥←/→ = crénage ±20 (±100 avec ⌘) ; flèches (⌘/⌥ = mot, ⇧ étend) ; ⌘↑/↓ début/fin ; Home/End ; **⌘↩ ou Esc valide**, ↩ = saut de ligne ; ⌘A tout.

**Plume et formes** (`vector_ui.rs`) : clic = coin, glisser = lisse ; clic sur le 1er sommet (6 points) ferme ; ↩ termine ouvert, Esc abandonne ; formes : ⇧ proportions, ⌥ centre, Ligne ⇧ = 45°.

**Panneau Calques** : voir §3.2 (clics ⌘/⇧, ⌘-clic vignette = sélection, ⇧-clic masque = désactiver, ⌥-clic masque = afficher en gris, ⌥⇧-clic = superposition, double-clics, ⌥-clic sur triangle = tous les groupes/effets, glisser-déposer `layer.moveTo` zone centrale 30–70 % = dans le groupe ; `mask_thumbs_ui.rs:111-205`, `layer_tree_ui.rs:61-62`, `panels.rs:2268-2317`).

**Menu contextuel d'une rangée de calque** (`layer_menu_ui.rs:23-118`) : Blending Options… │ Duplicate Layer(s)…, Delete Layer(s), Group from Layers… │ Quick Export As PNG, Export As… │ Artboard from Layers…, Frame from Layers… │ Convert to Smart Object, puis selon le contenu Rasterize Type / Rasterize Layer / Edit Contents │ masque : Disable/Apply/Delete Layer Mask ou Add Layer Mask ; Create/Release Clipping Mask │ Link Layers, Select Linked Layers │ Copy / Paste / Clear Layer Style │ Merge Layers ou Merge Down, Merge Visible, Flatten Image │ Rename Layer… (commandes absentes masquées).

**Panneau Couches** (`channels_panel.rs:142-369`) : clic = cibler ; ⌘-clic = charger (⇧/⌥/⇧⌥) ; œil ; double-clic sur alpha = renommer ; menu contextuel : Duplicate Channel, Delete Channel, Rename Channel…, (ton direct) Merge Spot Channel, Convert to Alpha Channel, Color Indicates Masked/Selected Areas, Overlay Color › Red/Green/Blue/Cyan/Magenta/Yellow, Overlay Opacity › 25/50/75/100 % ; Quick Mask : Exit Quick Mask ; masque de calque : Disable/Enable, Delete ; communs : New Channel…, New Spot Channel…, Split Channels, Merge Channels….

**Menus clic droit du canevas** (`canvas_tool_menu.rs`, `layer_pick_ui.rs`) : Move ou ⌘+clic droit (tout outil) = liste des calques sous le pointeur ; outils de sélection : Deselect, Inverse Selection, Feather…, Select and Mask…, Transform Selection (ou Reselect sans sélection) (l.61-73) ; Plume (`PEN_MENU`, l.23-53) : Create Vector Mask, Delete Path │ Define Custom Shape… │ Make Selection…, New Guides From Shape, Fill Path…, Stroke Path… │ Clipping Path… │ Free Transform Path │ Unite Shapes, Subtract Front Shape, Unite Shapes at Overlap, Subtract Shapes at Overlap │ Copy Fill, Copy Complete Stroke │ Paste Fill, Paste Complete Stroke │ Isolate Layers │ Make Symmetry Path, Disable Symmetry Path. (`docs/context-menu-inventory.md:20` dit encore que la Plume n'a pas de menu : périmé.)

**Divers** : flyout d'outils par clic droit ou appui > 0,35 s ; Esc quitte le plein écran (`lib.rs:927-931`) ; double-clic sur la barre de titre = maximiser ; double-clic sur un onglet du dock = replier ; onglet de document (clic droit) : Close, Close Others, Close All (`canvas.rs:1054-1060`) ; Liquify : ⌘Z/⌘⇧Z, ⌘H, ⌘I, ⌘D, [ ] ×0,9/×1,1, outils W R E C S B O F D L (`liquify_ui.rs:482-524`) ; Window › Modifier Keys = touches collantes (`canvas.rs:2257-2258`).


### 8.B Barre d'état, retours sur le canevas, infobulles (lu ; chemins relatifs à `crates/ui-egui/src/`)

**Barre d'état — conteneur** (`panels.rs:848-900`) : panneau bas 24 px (Pro) / 30 px, trait en haut. Pro → `chrome_ui::status_bar_pro` puis, à droite, progression des tâches (`jobs_ui::status_progress`). Studio : champ zoom 1–3200 % (78 px) │ « {mode} Color · {bits} bit » │ « {w} × {h} px » │ « {n} layer » / « {n} layers » ; sans document « No document » ; message d'état (couleur `warning` si erreur ou s'il commence par « Couldn ») ; à droite bouton « Fit » et progression.

**Barre d'état Pro** (`chrome_ui.rs:123-159`) : « No document » sans document ; champ zoom 1–3200 % (64 px) ; texte d'information (défaut `dimensions`, l.32) ; chevron `chevron-right` « Show » ouvrant le menu exclusif `STATUS_INFO` (l.37-46) :

| Clé | Entrée du menu | Texte affiché (l.77-101) |
|---|---|---|
| sizes | Document Sizes | « Doc: {aplati}/{calques} » (octets K/M/G, ex. « Doc: 10.3M/13.7M ») |
| profile | Document Profile | « {profil} ({bits}bpc) », ex. « sRGB IEC61966-2.1 (8bpc) » |
| dimensions | Document Dimensions | « {w} px x {h} px ({ppi} ppi) » |
| measurementScale | Measurement Scale | « 1 pixel = 1.0000 pixels » (fixe) |
| scratch | Scratch Sizes | « Scratch: {taille} » |
| efficiency | Efficiency | « Efficiency: 100% » (fixe) |
| tool | Current Tool | libellé de l'outil |
| layers | Layer Count | « {n} Layer » / « {n} Layers » |

Nom de profil (`profile_name`, l.103-120) : « Untagged {mode} », « Invalid {mode} profile », « Unnamed {mode} profile », sinon la description (≤ 128 car.). Libellés de mode (`canvas.rs:1215-1226`) : RGB, Gray, CMYK, Lab, Indexed, Bitmap, Duotone, Multichannel.

**Tâches de fond** (`jobs_ui.rs:245-290`) : de droite à gauche bouton × « Cancel (Esc) », pourcentage (vide = indéterminé), barre 120×6 (Pro) / 140×6, libellé « (+N) » ; fenêtre modale après un délai : titre + message ou « Working… », Échap annule.

**Indications de la barre d'options** (texte `text_faint`, `panels.rs:841-844` ; `{…}` = touche via `shortcuts::pretty`) :
- Marquee (hors Pro, non traduit) : « Drag to select  ·  {Shift} add  ·  {Alt} subtract  ·  {Shift+Alt} intersect  ·  click to deselect » (l.747-755)
- Move (hors Pro) : « Drag to move the active layer » (l.756)
- Eyedropper : « Click to sample the foreground colour  ·  {Alt}-click for background » (l.757-763)
- Zoom : « Click to zoom in  ·  {Alt}-click to zoom out  ·  drag right/left to zoom in/out » (l.764-783)
- Hand : « Drag to pan  ·  hold Space with any tool » (l.784)
- Lasso (hors Pro) : « Drag (lasso) or click points (polygonal) · {Shift} add · {Alt} subtract » (l.785-791)
- Polygonal Lasso en cours (Pro) : « Click the first point or press {Enter} to close · Esc cancels » (l.588-596)
- Crop (hors Pro) : « Drag a crop box · drag inside to move · edges resize ({Shift} ratio, {Alt} centre) · Space moves while drawing · {Enter} commits · Esc cancels » (l.792-802)
- Gradient : « Drag to draw a gradient » ; Paint Bucket : « Click to fill similar colours » ; Type : « Click to add text » (l.803-805)
- Transformation : « Commit transform ({Enter}) » / « Commit warp ({Enter}) », « Cancel transform (Esc) » / « Cancel warp (Esc) », « Switch between free transform and warp modes » (`transform_tool.rs:1413-1429`)

**Retours sur le canevas** (`tool_feedback.rs`, `canvas.rs`, `brush_resize.rs`) :
- Badge du mode de sélection près du curseur : « + » ajout, « − » soustraction, « × » intersection (aucun pour Nouveau), blanc sur halo sombre, à +30,+11 (ou au centre du cercle pour Quick Selection) ; outils : Rect./Elliptical Marquee, Lasso, Polygonal Lasso, Magic Wand, Quick Selection, Object Selection (`tool_feedback.rs:14-106`).
- Mode effectif (`selection_mode`, l.41-73) : Maj+Alt intersecte, Maj ajoute, Alt soustrait, sinon mode de la barre ; Quick Selection : toujours ajout, Alt soustrait ; Object Selection : Alt soustrait, Maj ajoute, sinon remplace.
- Fourmis : tirets noirs 4 px sur trait blanc, animés toutes les 100 ms (l.109-155) ; aperçu de forme : trait couleur sur halo noir 3 px (l.171-174).
- Bulles de mesure (`canvas.rs:123-145`, à +16,+18 du pointeur) : marquee « W: / H: » en px ; redimensionnement de brosse « Diameter: {n} px » / « Hardness: {n}% » avec aperçu de pointe rouge (`brush_resize.rs:123-141`).
- Curseurs (`canvas.rs:1805-1895`) : sur repère avec Move → redimensionnement ; brosse masquée pendant le redimensionnement ; Alt sur un outil de peinture → réticule pipette ; outils de type brosse selon Préférences › Cursors (Standard = flèche, Precise = réticule, Normal tip / Full size tip = contour, « crosshair only while painting ») ; Pencil = carré de pixels ; Other Cursors Precise → réticule pour Move, Type, Eyedropper ; Move = Move ; Hand = Grab / Grabbing ; Zoom = ZoomIn / ZoomOut (Alt) ; Type = Text ; autres = Crosshair.

**Onglets et accueil** (`canvas.rs`) : titre d'onglet « {nom} @ {zoom}% ({calque}, {mode | Layer Mask}/{bits}){*} » (l.1105-1112) ; « Opening… » + % et « Cancel opening » (l.1032, 1140, 1156) ; écran d'accueil : « PhotoCraft » / « open source », « Create a new document or open an existing file. », boutons « New document… » et « Open… » suivis du raccourci, « Drop an image or PSD anywhere to open it. » (ou sous Wayland « Use File › Open to open an image. »), liste « Recent » (6 max) (l.1236-1300).

**Infobulles de la barre d'outils** (`panels.rs:54-233`) : « {libellé}  ({touche}) » ; pastilles « Set foreground color », « Set background color », « Swap colours (X) », « Default colours (D) » (l.266-276) ; « Edit Toolbar… » ; « Edit in Quick Mask Mode  (Q) » / « Edit in Standard Mode  (Q) » ; « Change Screen Mode  (F) ». Format générique `tip_label` = « {libellé}  ({raccourci}) » avec le raccourci personnalisé s'il existe (`shortcuts.rs:63-78`).


## 9. Registre des commandes (lu + extraction statique)

- Structure `CommandSpec { id, label, menu, shortcut, params, enabled, run, journal }` (`crates/engine/src/commands.rs:14-27`) ; le registre est construit une fois par `build()` (`commands.rs:209-1003`) : la liste littérale de `commands.rs`, la boucle `ADJ` (16 × 2 commandes, l.844-933), puis `v.extend(<module>::specs())` pour 69 modules (l.935-1003, dans cet ordre : layer_style, filters, filters_ext, gallery_cmds, gradient_fill_cmds, type_cmds, transform_cmds, vector_cmds, smartselect_cmds, symmetry_cmds, edit_cmds, color_cmds, brush_cmds, brush_preset_cmds, eraser_cmds, preset_import_cmds, retouch_cmds, image_cmds, selection_cmds, select_extra_cmds, paint_cmds, extra_cmds, file_cmds, type_extra_cmds, type_styles_cmds, type_spell_cmds, smart_cmds, layer_multi_cmds, prefs, edit_menu_cmds, fill_key_cmds, stamp_cmds, align_cmds, photo_cmds, lens_cmds, vp_cmds, channel_cmds, adjust_cmds, layer_menu_cmds, mode_cmds, multichannel_cmds, pattern_cmds, warp_cmds, comps_cmds, artboard_cmds, distort_cmds, analysis_cmds, notes_cmds, proof_sim, presets (gradients, patterns, styles, shapes, tools, clone_source), render_cmds, slice_cmds, web_cmds, automate_cmds, print_cmds, pick_cmds, layer_nav_cmds, frame_cmds, migrate_cmds, trap_cmds, timeline_cmds, video_cmds, jobs, wia_cmds, variables_cmds, plugin_cmds, group_view_cmds, fx_view_cmds, mask_view_cmds).
- Les menus de l'interface ne sont **pas** construits à la main : `menu_catalog.rs` fixe l'arbre Photoshop (ordre, séparateurs, raccourcis, ids) ; un id du catalogue est actif s'il existe dans le registre moteur, dans `UI_COMMANDS` (`menus.rs:12-63`) ou dans un gestionnaire de la coque (`is_live`, `menus.rs:599-614`) ; les commandes du registre qui ont un `menu` mais manquent au catalogue sont ajoutées en fin de leur menu (`menus.rs:617-669`).
- **Obtenir la liste exacte** : `photocraft-cli commands --json` (sortie = tableau `{id, label, menu, shortcut, params, enabled}` produit par la commande moteur `command.list`, `apps/photocraft-cli/src/lib.rs:365-386`, `commands.rs:798-818`) ; filtre `--filter <texte>` sur id + libellé ; sans `--json` : colonnes id / libellé / menu. Aussi via MCP (`photocraft-cli mcp`), le serveur JSON (`photocraft-cli serve`) ou le canal de contrôle (`docs/control-protocol.md`). Le README annonce « 500+ commands » (`README.md:222`). Aucune compilation n'étant possible ici (pas de cargo), **le décompte ci-dessous est une extraction statique** (expressions régulières sur les littéraux des fonctions `specs()`/`build()`, hors tests, + 32 ids générés + 29 ids définis par constantes) : il peut manquer des ids construits dynamiquement ; l'ordre est reconstitué (fichier puis ligne, dans l'ordre des `extend`).

Total d'identifiants extraits statiquement : **684** (dont 32 générés par la boucle ADJ ; 84 dont seul l'id a été extrait).
Commandes avec un chemin de menu : 439 ; sans menu (requêtes, outils, automatisation) : 192.

| Espace de noms | Nombre |
|---|---|
| `layer.*` | 179 |
| `edit.*` | 76 |
| `filter.*` | 75 |
| `image.*` | 62 |
| `file.*` | 48 |
| `type.*` | 38 |
| `select.*` | 28 |
| `view.*` | 23 |
| `paint.*` | 21 |
| `path.*` | 15 |
| `layerComp.*` | 13 |
| `brush.*` | 12 |
| `gradient.*` | 11 |
| `pattern.*` | 10 |
| `shape.*` | 9 |
| `count.*` | 7 |
| `slice.*` | 7 |
| `timeline.*` | 7 |
| `plugin.*` | 5 |
| `cloneSource.*` | 5 |
| `style.*` | 5 |
| `tool.*` | 5 |
| `tools.*` | 4 |
| `notes.*` | 4 |
| `measurementLog.*` | 3 |
| `document.*` | 3 |
| `prefs.*` | 3 |
| `jobs.*` | 2 |
| `color.*` | 1 |
| `session.*` | 1 |
| `command.*` | 1 |
| `variables.*` | 1 |

#### Sous-espaces (deux premiers segments)

| Préfixe | Nombre |
|---|---|
| `image.adjustments` | 23 |
| `layer.layerStyle` | 19 |
| `edit.preferences` | 18 |
| `layer.newAdjustmentLayer` | 16 |
| `layer.smartObjects` | 16 |
| `edit.transform` | 14 |
| `image.mode` | 12 |
| `layer.videoLayers` | 12 |
| `file.export` | 11 |
| `filter.blur` | 11 |
| `file.automate` | 10 |
| `layer.new` | 10 |
| `layer.vectorMask` | 10 |
| `type.openType` | 10 |
| `brush.presets` | 9 |
| `filter.distort` | 9 |
| `filter.stylize` | 9 |
| `layer.layerMask` | 9 |
| `layer.smartFilter` | 9 |
| `view.proofSetup` | 9 |
| `file.scripts` | 8 |
| `filter.render` | 8 |
| `image.analysis` | 8 |
| `layer.distribute` | 8 |
| `layer.rasterize` | 8 |
| `filter.pixelate` | 7 |
| `gradient.presets` | 7 |
| `type.antiAlias` | 7 |
| `filter.other` | 6 |
| `layer.align` | 6 |
| `edit.purge` | 5 |
| `filter.blurGallery` | 5 |
| `filter.noise` | 5 |
| `filter.sharpen` | 5 |
| `image.imageRotation` | 5 |
| `layer.arrange` | 5 |
| `layer.combineShapes` | 5 |
| `pattern.presets` | 5 |
| `select.modify` | 5 |
| `shape.presets` | 5 |
| `style.presets` | 5 |
| `tool.presets` | 5 |
| `file.import` | 4 |
| `gradient.fill` | 4 |
| `layer.matting` | 4 |
| `path.style` | 4 |
| `edit.pasteSpecial` | 3 |
| `edit.presets` | 3 |
| `layer.newFillLayer` | 3 |
| `filter.video` | 2 |
| `image.variables` | 2 |
| `layer.delete` | 2 |
| `path.clippingPath` | 2 |
| `type.orientation` | 2 |
| `brush.defineFromSelection` | 1 |
| `brush.get` | 1 |
| `brush.texturePattern` | 1 |
| `cloneSource.list` | 1 |
| `cloneSource.overlay` | 1 |
| `cloneSource.resetTransform` | 1 |
| `cloneSource.select` | 1 |
| `cloneSource.set` | 1 |
| `color.profileMismatch` | 1 |
| `command.list` | 1 |
| `count.add` | 1 |
| `count.clear` | 1 |
| `count.deleteGroup` | 1 |
| `count.move` | 1 |
| `count.newGroup` | 1 |
| `count.remove` | 1 |
| `count.setGroup` | 1 |
| `document.activate` | 1 |
| `document.inspect` | 1 |
| `document.pixel` | 1 |
| `edit.assignProfile` | 1 |
| `edit.autoAlignLayers` | 1 |
| `edit.autoBlendLayers` | 1 |
| `edit.checkSpelling` | 1 |
| `edit.clear` | 1 |
| `edit.colorSettings` | 1 |
| `edit.contentAwareFill` | 1 |
| `edit.contentAwareScale` | 1 |
| `edit.convertToProfile` | 1 |
| `edit.copy` | 1 |
| `edit.copyMerged` | 1 |
| `edit.cut` | 1 |
| `edit.defineBrushPreset` | 1 |
| `edit.defineCustomShape` | 1 |
| `edit.definePattern` | 1 |
| `edit.fade` | 1 |
| `edit.fill` | 1 |
| `edit.fillBackground` | 1 |
| `edit.fillBackgroundPreserve` | 1 |
| `edit.fillForeground` | 1 |
| `edit.fillForegroundPreserve` | 1 |
| `edit.findAndReplaceText` | 1 |
| `edit.keyboardShortcuts` | 1 |
| `edit.menus` | 1 |
| `edit.paste` | 1 |
| `edit.perspectiveWarp` | 1 |
| `edit.profileInfo` | 1 |
| `edit.puppetWarp` | 1 |
| `edit.redo` | 1 |
| `edit.stroke` | 1 |
| `edit.toggleLastState` | 1 |
| `edit.toolbar` | 1 |
| `edit.undo` | 1 |
| `file.close` | 1 |
| `file.closeAll` | 1 |
| `file.closeOthers` | 1 |
| `file.fileInfo` | 1 |
| `file.generate` | 1 |
| `file.new` | 1 |
| `file.newFromClipboard` | 1 |
| `file.openAs` | 1 |
| `file.package` | 1 |
| `file.placeEmbedded` | 1 |
| `file.placeLinked` | 1 |
| `file.print` | 1 |
| `file.printOneCopy` | 1 |
| `file.revert` | 1 |
| `file.saveACopy` | 1 |
| `filter.adaptiveWideAngle` | 1 |
| `filter.cameraRaw` | 1 |
| `filter.convertForSmartFilters` | 1 |
| `filter.filterGallery` | 1 |
| `filter.lastFilter` | 1 |
| `filter.lensCorrection` | 1 |
| `filter.liquify` | 1 |
| `filter.vanishingPoint` | 1 |
| `image.applyDataSet` | 1 |
| `image.autoColor` | 1 |
| `image.autoContrast` | 1 |
| `image.autoTone` | 1 |
| `image.canvasSize` | 1 |
| `image.crop` | 1 |
| `image.duplicate` | 1 |
| `image.imageSize` | 1 |
| `image.revealAll` | 1 |
| `image.rotation` | 1 |
| `image.trap` | 1 |
| `image.trim` | 1 |
| `jobs.cancel` | 1 |
| `jobs.list` | 1 |
| `layer.addAboveToSelection` | 1 |
| `layer.addBelowToSelection` | 1 |
| `layer.artboard` | 1 |
| `layer.createClippingMask` | 1 |
| `layer.duplicate` | 1 |
| `layer.exportAs` | 1 |
| `layer.flattenImage` | 1 |
| `layer.groupLayers` | 1 |
| `layer.hideLayers` | 1 |
| `layer.layerContentOptions` | 1 |
| `layer.linkLayers` | 1 |
| `layer.lockLayers` | 1 |
| `layer.maskAllObjects` | 1 |
| `layer.mergeDown` | 1 |
| `layer.mergeLayers` | 1 |
| `layer.mergeVisible` | 1 |
| `layer.moveTo` | 1 |
| `layer.newLayerBasedSlice` | 1 |
| `layer.pickAt` | 1 |
| `layer.quickExportAsPng` | 1 |
| `layer.releaseClippingMask` | 1 |
| `layer.renameLayer` | 1 |
| `layer.select` | 1 |
| `layer.selectAbove` | 1 |
| `layer.selectBelow` | 1 |
| `layer.selectBottom` | 1 |
| `layer.selectLinkedLayers` | 1 |
| `layer.selectTop` | 1 |
| `layer.setAdjustment` | 1 |
| `layer.setEffectsExpanded` | 1 |
| `layer.setExpanded` | 1 |
| `layer.setProps` | 1 |
| `layer.showLayers` | 1 |
| `layer.stampDown` | 1 |
| `layer.stampVisible` | 1 |
| `layer.translate` | 1 |
| `layer.ungroupLayers` | 1 |
| `layerComp.apply` | 1 |
| `layerComp.delete` | 1 |
| `layerComp.duplicate` | 1 |
| `layerComp.list` | 1 |
| `layerComp.new` | 1 |
| `layerComp.next` | 1 |
| `layerComp.previous` | 1 |
| `layerComp.rename` | 1 |
| `layerComp.restoreLastDocumentState` | 1 |
| `layerComp.setComment` | 1 |
| `layerComp.setOptions` | 1 |
| `layerComp.update` | 1 |
| `layerComp.updateWarnings` | 1 |
| `measurementLog.delete` | 1 |
| `measurementLog.export` | 1 |
| `measurementLog.list` | 1 |
| `notes.add` | 1 |
| `notes.delete` | 1 |
| `notes.list` | 1 |
| `notes.set` | 1 |
| `paint.backgroundEraser` | 1 |
| `paint.blur` | 1 |
| `paint.bucket` | 1 |
| `paint.burn` | 1 |
| `paint.cloneStamp` | 1 |
| `paint.colorReplacement` | 1 |
| `paint.dodge` | 1 |
| `paint.gradient` | 1 |
| `paint.healingBrush` | 1 |
| `paint.historyBrush` | 1 |
| `paint.magicEraser` | 1 |
| `paint.mixerBrush` | 1 |
| `paint.patch` | 1 |
| `paint.pencil` | 1 |
| `paint.sharpen` | 1 |
| `paint.smudge` | 1 |
| `paint.sponge` | 1 |
| `paint.spotHealing` | 1 |
| `paint.stroke` | 1 |
| `paint.symmetryDisable` | 1 |
| `paint.symmetryFromPath` | 1 |
| `path.delete` | 1 |
| `path.fill` | 1 |
| `path.info` | 1 |
| `path.list` | 1 |
| `path.rename` | 1 |
| `path.set` | 1 |
| `path.stroke` | 1 |
| `path.toSelection` | 1 |
| `path.transform` | 1 |
| `pattern.delete` | 1 |
| `pattern.export` | 1 |
| `pattern.import` | 1 |
| `pattern.list` | 1 |
| `pattern.rename` | 1 |
| `plugin.install` | 1 |
| `plugin.list` | 1 |
| `plugin.reload` | 1 |
| `plugin.remove` | 1 |
| `plugin.run` | 1 |
| `prefs.get` | 1 |
| `prefs.reset` | 1 |
| `prefs.set` | 1 |
| `select.all` | 1 |
| `select.allLayers` | 1 |
| `select.colorRange` | 1 |
| `select.convertToShape` | 1 |
| `select.deselect` | 1 |
| `select.deselectLayers` | 1 |
| `select.findLayers` | 1 |
| `select.focusArea` | 1 |
| `select.grow` | 1 |
| `select.inverse` | 1 |
| `select.isolateLayers` | 1 |
| `select.lasso` | 1 |
| `select.magicWand` | 1 |
| `select.object` | 1 |
| `select.quick` | 1 |
| `select.rect` | 1 |
| `select.refineEdge` | 1 |
| `select.reselect` | 1 |
| `select.similar` | 1 |
| `select.sky` | 1 |
| `select.subject` | 1 |
| `select.toWorkPath` | 1 |
| `select.transformSelection` | 1 |
| `session.inspect` | 1 |
| `shape.create` | 1 |
| `shape.edit` | 1 |
| `shape.info` | 1 |
| `shape.rasterize` | 1 |
| `slice.delete` | 1 |
| `slice.divide` | 1 |
| `slice.fromGuides` | 1 |
| `slice.list` | 1 |
| `slice.new` | 1 |
| `slice.promote` | 1 |
| `slice.set` | 1 |
| `timeline.create` | 1 |
| `timeline.delete` | 1 |
| `timeline.info` | 1 |
| `timeline.nextFrame` | 1 |
| `timeline.previousFrame` | 1 |
| `timeline.setFrame` | 1 |
| `timeline.setProps` | 1 |
| `tools.defaultColors` | 1 |
| `tools.setBrush` | 1 |
| `tools.setColors` | 1 |
| `tools.swapColors` | 1 |
| `type.convertToParagraphText` | 1 |
| `type.convertToPointText` | 1 |
| `type.convertToShape` | 1 |
| `type.create` | 1 |
| `type.createWorkPath` | 1 |
| `type.edit` | 1 |
| `type.fonts` | 1 |
| `type.info` | 1 |
| `type.insertText` | 1 |
| `type.loadDefaultTypeStyles` | 1 |
| `type.pasteLoremIpsum` | 1 |
| `type.rasterize` | 1 |
| `type.rasterizeTypeLayer` | 1 |
| `type.replaceAllMissingFonts` | 1 |
| `type.resolveMissingFonts` | 1 |
| `type.saveDefaultTypeStyles` | 1 |
| `type.setStyle` | 1 |
| `type.updateAllTextLayers` | 1 |
| `type.warpText` | 1 |
| `variables.list` | 1 |
| `view.clearCanvasGuides` | 1 |
| `view.clearGuides` | 1 |
| `view.clearSelectedArtboardGuides` | 1 |
| `view.clearSlices` | 1 |
| `view.deleteGuide` | 1 |
| `view.gamutWarning` | 1 |
| `view.layerMask` | 1 |
| `view.lockSlices` | 1 |
| `view.moveGuide` | 1 |
| `view.newGuide` | 1 |
| `view.newGuideLayout` | 1 |
| `view.newGuidesFromShape` | 1 |
| `view.proofColors` | 1 |
| `view.thirtyTwoBitPreviewOptions` | 1 |

#### Liste complète des identifiants (ordre reconstitué du registre)

| id | Libellé | Menu | Raccourci | Source |
|---|---|---|---|---|
| `file.new` | New… | File | Cmd+N | commands.rs:213 |
| `file.close` | Close | File | Cmd+W | commands.rs:262 |
| `edit.undo` | Undo | Edit | Cmd+Z | commands.rs:268 |
| `edit.redo` | Redo | Edit | Cmd+Shift+Z | commands.rs:269 |
| `edit.fill` | Fill… | Edit | Shift+F5 | commands.rs:271 |
| `edit.clear` | Clear | Edit | Delete | commands.rs:279 |
| `select.all` | All | Select | Cmd+A | commands.rs:290 |
| `select.deselect` | Deselect | Select | Cmd+D | commands.rs:299 |
| `select.inverse` | Inverse | Select | Cmd+Shift+I | commands.rs:306 |
| `select.rect` | Rectangular Selection | — |  | commands.rs:320 |
| `layer.new.layer` | Layer… | Layer › New | Cmd+Shift+N | commands.rs:388 |
| `layer.new.group` | Group… | Layer › New |  | commands.rs:397 |
| `layer.groupLayers` | Group Layers | Layer | Cmd+G | commands.rs:407 |
| `layer.duplicate` | Duplicate Layer… | Layer |  | commands.rs:415 |
| `layer.delete` | Delete Layer | Layer › Delete |  | commands.rs:435 |
| `layer.select` | Select Layer | — |  | commands.rs:450 |
| `layer.setProps` | Layer Properties | — |  | commands.rs:459 |
| `layer.arrange.bringForward` | Bring Forward | Layer › Arrange | Cmd+] | commands.rs:519 |
| `layer.arrange.sendBackward` | Send Backward | Layer › Arrange | Cmd+[ | commands.rs:520 |
| `layer.arrange.bringToFront` | Bring to Front | Layer › Arrange | Cmd+Shift+] | commands.rs:521 |
| `layer.arrange.sendToBack` | Send to Back | Layer › Arrange | Cmd+Shift+[ | commands.rs:526 |
| `layer.createClippingMask` | Create Clipping Mask | Layer | Cmd+Alt+G | commands.rs:531 |
| `layer.releaseClippingMask` | Release Clipping Mask | Layer |  | commands.rs:539 |
| `layer.layerMask.revealAll` | Reveal All | Layer › Layer Mask |  | commands.rs:547 |
| `layer.layerMask.hideAll` | Hide All | Layer › Layer Mask |  | commands.rs:553 |
| `layer.layerMask.revealSelection` | Reveal Selection | Layer › Layer Mask |  | commands.rs:559 |
| `layer.layerMask.delete` | Delete | Layer › Layer Mask |  | commands.rs:564 |
| `layer.mergeDown` | Merge Down | Layer |  | commands.rs:570 |
| `layer.flattenImage` | Flatten Image | Layer |  | commands.rs:590 |
| `layer.newFillLayer.solidColor` | Solid Color… | Layer › New Fill Layer |  | commands.rs:602 |
| `layer.newFillLayer.gradient` | Gradient… | Layer › New Fill Layer |  | commands.rs:613 |
| `layer.setAdjustment` | Adjustment Properties | — |  | commands.rs:640 |
| `layer.moveTo` | Reorder Layer | — |  | commands.rs:660 |
| `layer.translate` | Move Layer | — |  | commands.rs:698 |
| `image.imageRotation.flipCanvasHorizontal` | Flip Canvas Horizontal | Image › Image Rotation |  | commands.rs:707 |
| `image.imageRotation.flipCanvasVertical` | Flip Canvas Vertical | Image › Image Rotation |  | commands.rs:710 |
| `image.imageRotation.180` | 180° | Image › Image Rotation |  | commands.rs:713 |
| `image.imageRotation.90cw` | 90° Clockwise | Image › Image Rotation |  | commands.rs:716 |
| `image.imageRotation.90ccw` | 90° Counter Clockwise | Image › Image Rotation |  | commands.rs:719 |
| `image.adjustments.desaturate` | Desaturate | Image › Adjustments | Cmd+Shift+U | commands.rs:722 |
| `paint.stroke` | Brush Stroke | — |  | commands.rs:738 |
| `tools.setColors` | Set Colors | — |  | commands.rs:746 |
| `tools.swapColors` | Switch Foreground and Background Colors | — | X | commands.rs:751 |
| `tools.defaultColors` | Default Foreground and Background Colors | — | D | commands.rs:755 |
| `session.inspect` | Inspect Session | — |  | commands.rs:762 |
| `document.inspect` | Inspect Document | — |  | commands.rs:772 |
| `document.activate` | Activate Document | — |  | commands.rs:786 |
| `command.list` | List Commands | — |  | commands.rs:799 |
| `document.pixel` | Read Composite Pixel | — |  | commands.rs:820 |
| `layer.newAdjustmentLayer.brightnessContrast` | Brightness/Contrast… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.brightnessContrast` | Brightness/Contrast… | Image › Adjustments |  | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.levels` | Levels… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.levels` | Levels… | Image › Adjustments | Cmd+L | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.curves` | Curves… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.curves` | Curves… | Image › Adjustments | Cmd+M | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.exposure` | Exposure… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.exposure` | Exposure… | Image › Adjustments |  | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.vibrance` | Vibrance… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.vibrance` | Vibrance… | Image › Adjustments |  | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.hueSaturation` | Hue/Saturation… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.hueSaturation` | Hue/Saturation… | Image › Adjustments | Cmd+U | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.colorBalance` | Color Balance… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.colorBalance` | Color Balance… | Image › Adjustments | Cmd+B | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.blackWhite` | Black & White… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.blackWhite` | Black & White… | Image › Adjustments | Cmd+Alt+Shift+B | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.photoFilter` | Photo Filter… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.photoFilter` | Photo Filter… | Image › Adjustments |  | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.channelMixer` | Channel Mixer… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.channelMixer` | Channel Mixer… | Image › Adjustments |  | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.invert` | Invert | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.invert` | Invert | Image › Adjustments | Cmd+I | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.posterize` | Posterize… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.posterize` | Posterize… | Image › Adjustments |  | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.threshold` | Threshold… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.threshold` | Threshold… | Image › Adjustments |  | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.gradientMap` | Gradient Map… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.gradientMap` | Gradient Map… | Image › Adjustments |  | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.selectiveColor` | Selective Color… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.selectiveColor` | Selective Color… | Image › Adjustments |  | commands.rs:868-933 (généré) |
| `layer.newAdjustmentLayer.colorLookup` | Color Lookup… | Layer › New Adjustment Layer |  | commands.rs:868-933 (généré) |
| `image.adjustments.colorLookup` | Color Lookup… | Image › Adjustments |  | commands.rs:868-933 (généré) |
| `layer.layerStyle.dropShadow` | Drop Shadow… | Layer › Layer Style |  | layer_style.rs:222 |
| `layer.layerStyle.innerShadow` | Inner Shadow… | Layer › Layer Style |  | layer_style.rs:227 |
| `layer.layerStyle.outerGlow` | Outer Glow… | Layer › Layer Style |  | layer_style.rs:232 |
| `layer.layerStyle.innerGlow` | Inner Glow… | Layer › Layer Style |  | layer_style.rs:237 |
| `layer.layerStyle.stroke` | Stroke… | Layer › Layer Style |  | layer_style.rs:242 |
| `layer.layerStyle.colorOverlay` | Color Overlay… | Layer › Layer Style |  | layer_style.rs:247 |
| `layer.layerStyle.gradientOverlay` | Gradient Overlay… | Layer › Layer Style |  | layer_style.rs:248 |
| `layer.layerStyle.patternOverlay` | Pattern Overlay… | Layer › Layer Style |  | layer_style.rs:253 |
| `layer.layerStyle.bevelEmboss` | Bevel & Emboss… | Layer › Layer Style |  | layer_style.rs:258 |
| `layer.layerStyle.satin` | Satin… | Layer › Layer Style |  | layer_style.rs:263 |
| `layer.layerStyle.clear` | Clear Layer Style | Layer › Layer Style |  | layer_style.rs:265 |
| `filter.blur.gaussianBlur` | Gaussian Blur… | Filter › Blur |  | filters.rs:273 |
| `filter.blur.blur` | Blur | Filter › Blur |  | filters.rs:274 |
| `filter.blur.blurMore` | Blur More | Filter › Blur |  | filters.rs:275 |
| `filter.sharpen.sharpen` | Sharpen | Filter › Sharpen |  | filters.rs:276 |
| `filter.sharpen.sharpenMore` | Sharpen More | Filter › Sharpen |  | filters.rs:277 |
| `filter.sharpen.sharpenEdges` | Sharpen Edges | Filter › Sharpen |  | filters.rs:278 |
| `filter.noise.despeckle` | Despeckle | Filter › Noise |  | filters.rs:279 |
| `filter.blur.boxBlur` | Box Blur… | Filter › Blur |  | filters.rs:280 |
| `filter.blur.motionBlur` | Motion Blur… | Filter › Blur |  | filters.rs:281 |
| `filter.blur.radialBlur` | Radial Blur… | Filter › Blur |  | filters.rs:283 |
| `filter.blur.surfaceBlur` | Surface Blur… | Filter › Blur |  | filters.rs:288 |
| `filter.sharpen.unsharpMask` | Unsharp Mask… | Filter › Sharpen |  | filters.rs:290 |
| `filter.sharpen.smartSharpen` | Smart Sharpen… | Filter › Sharpen |  | filters.rs:296 |
| `filter.noise.addNoise` | Add Noise… | Filter › Noise |  | filters.rs:302 |
| `filter.noise.median` | Median… | Filter › Noise |  | filters.rs:307 |
| `filter.noise.dustAndScratches` | Dust & Scratches… | Filter › Noise |  | filters.rs:308 |
| `filter.pixelate.mosaic` | Mosaic… | Filter › Pixelate |  | filters.rs:309 |
| `filter.stylize.emboss` | Emboss… | Filter › Stylize |  | filters.rs:310 |
| `filter.stylize.findEdges` | Find Edges | Filter › Stylize |  | filters.rs:311 |
| `filter.stylize.solarize` | Solarize | Filter › Stylize |  | filters.rs:312 |
| `filter.distort.twirl` | Twirl… | Filter › Distort |  | filters.rs:313 |
| `filter.distort.pinch` | Pinch… | Filter › Distort |  | filters.rs:314 |
| `filter.distort.spherize` | Spherize… | Filter › Distort |  | filters.rs:315 |
| `filter.distort.wave` | Wave… | Filter › Distort |  | filters.rs:317 |
| `filter.distort.ripple` | Ripple… | Filter › Distort |  | filters.rs:322 |
| `filter.distort.polarCoordinates` | Polar Coordinates… | Filter › Distort |  | filters.rs:323 |
| `filter.other.highPass` | High Pass… | Filter › Other |  | filters.rs:324 |
| `filter.other.minimum` | Minimum… | Filter › Other |  | filters.rs:325 |
| `filter.other.maximum` | Maximum… | Filter › Other |  | filters.rs:326 |
| `filter.other.offset` | Offset… | Filter › Other |  | filters.rs:328 |
| `filter.lastFilter` | Last Filter | Filter | Cmd+Alt+F | filters.rs:334 |
| `filter.pixelate.colorHalftone` | Color Halftone… | Filter › Pixelate |  | filters_ext.rs:459 |
| `filter.pixelate.crystallize` | Crystallize… | Filter › Pixelate |  | filters_ext.rs:464 |
| `filter.pixelate.facet` | Facet | Filter › Pixelate |  | filters_ext.rs:465 |
| `filter.pixelate.fragment` | Fragment | Filter › Pixelate |  | filters_ext.rs:466 |
| `filter.pixelate.mezzotint` | Mezzotint… | Filter › Pixelate |  | filters_ext.rs:468 |
| `filter.pixelate.pointillize` | Pointillize… | Filter › Pixelate |  | filters_ext.rs:473 |
| `filter.stylize.diffuse` | Diffuse… | Filter › Stylize |  | filters_ext.rs:475 |
| `filter.stylize.extrude` | Extrude… | Filter › Stylize |  | filters_ext.rs:477 |
| `filter.stylize.oilPaint` | Oil Paint… | Filter › Stylize |  | filters_ext.rs:483 |
| `filter.stylize.tiles` | Tiles… | Filter › Stylize |  | filters_ext.rs:489 |
| `filter.stylize.traceContour` | Trace Contour… | Filter › Stylize |  | filters_ext.rs:494 |
| `filter.stylize.wind` | Wind… | Filter › Stylize |  | filters_ext.rs:495 |
| `filter.distort.displace` | Displace… | Filter › Distort |  | filters_ext.rs:498 |
| `filter.distort.shear` | Shear… | Filter › Distort |  | filters_ext.rs:503 |
| `filter.distort.zigZag` | ZigZag… | Filter › Distort |  | filters_ext.rs:505 |
| `filter.render.fibers` | Fibers… | Filter › Render |  | filters_ext.rs:512 |
| `filter.render.lensFlare` | Lens Flare… | Filter › Render |  | filters_ext.rs:518 |
| `filter.render.lightingEffects` | Lighting Effects… | Filter › Render |  | filters_ext.rs:524 |
| `filter.noise.reduceNoise` | Reduce Noise… | Filter › Noise |  | filters_ext.rs:531 |
| `filter.blur.smartBlur` | Smart Blur… | Filter › Blur |  | filters_ext.rs:538 |
| `filter.blur.lensBlur` | Lens Blur… | Filter › Blur |  | filters_ext.rs:544 |
| `filter.blur.shapeBlur` | Shape Blur… | Filter › Blur |  | filters_ext.rs:550 |
| `filter.blurGallery.tiltShift` | Tilt-Shift… | Filter › Blur Gallery |  | filters_ext.rs:557 |
| `filter.blurGallery.irisBlur` | Iris Blur… | Filter › Blur Gallery |  | filters_ext.rs:563 |
| `filter.blurGallery.fieldBlur` | Field Blur… | Filter › Blur Gallery |  | filters_ext.rs:569 |
| `filter.blurGallery.spinBlur` | Spin Blur… | Filter › Blur Gallery |  | filters_ext.rs:575 |
| `filter.blurGallery.pathBlur` | Path Blur… | Filter › Blur Gallery |  | filters_ext.rs:581 |
| `filter.other.custom` | Custom… | Filter › Other |  | filters_ext.rs:587 |
| `filter.other.hsbHsl` | HSB/HSL | Filter › Other |  | filters_ext.rs:588 |
| `filter.video.deInterlace` | De-Interlace… | Filter › Video |  | filters_ext.rs:591 |
| `filter.video.ntscColors` | NTSC Colors | Filter › Video |  | filters_ext.rs:596 |
| `filter.filterGallery` | Filter Gallery… | Filter |  | gallery_cmds.rs:138 |
| `gradient.fill.create` | Gradient (Live) | — |  | gradient_fill_cmds.rs:532 |
| `gradient.fill.set` | Edit Gradient Fill | — |  | gradient_fill_cmds.rs:542 |
| `gradient.fill.stop` | Edit Gradient Stop | — |  | gradient_fill_cmds.rs:552 |
| `gradient.fill.get` | Gradient Fill Settings | — |  | gradient_fill_cmds.rs:562 |
| `type.create` | New Type Layer | Layer › New |  | type_cmds.rs:486 |
| `type.edit` | Edit Type | — |  | type_cmds.rs:533 |
| `type.setStyle` | Set Type Style | — |  | type_cmds.rs:648 |
| `type.rasterize` | Rasterize Type | Layer › Rasterize |  | type_cmds.rs:681 |
| `type.info` | Type Layer Info | — |  | type_cmds.rs:709 |
| `type.fonts` | List Fonts | — |  | type_cmds.rs:719 |
| `edit.transform` | Free Transform | — |  | transform_cmds.rs:404 |
| `shape.create` | New Shape Layer | Layer › New |  | vector_cmds.rs:1243 |
| `shape.edit` | Edit Shape | — |  | vector_cmds.rs:1253 |
| `shape.info` | Shape Layer Info | — |  | vector_cmds.rs:1263 |
| `shape.rasterize` | Rasterize Shape | Layer › Rasterize |  | vector_cmds.rs:1275 |
| `path.list` | List Paths | — |  | vector_cmds.rs:1277 |
| `path.info` | Path Info | — |  | vector_cmds.rs:1287 |
| `path.set` | Set Path | — |  | vector_cmds.rs:1301 |
| `path.delete` | Delete Path | — |  | vector_cmds.rs:1310 |
| `path.transform` | Free Transform Path | — |  | vector_cmds.rs:1312 |
| `path.clippingPath.set` | Clipping Path | — |  | vector_cmds.rs:1320 |
| `path.clippingPath.clear` | Clear Clipping Path | — |  | vector_cmds.rs:1327 |
| `path.style.copyFill` | Copy Fill | — |  | vector_cmds.rs:1328 |
| `path.style.copyStroke` | Copy Complete Stroke | — |  | vector_cmds.rs:1329 |
| `path.style.pasteFill` | Paste Fill | — |  | vector_cmds.rs:1331 |
| `path.style.pasteStroke` | Paste Complete Stroke | — |  | vector_cmds.rs:1339 |
| `path.rename` | Rename Path | — |  | vector_cmds.rs:1346 |
| `path.toSelection` | Make Selection from Path | — | Cmd+Enter | vector_cmds.rs:1349 |
| `select.toWorkPath` | Make Work Path | — |  | vector_cmds.rs:1358 |
| `path.fill` | Fill Path | — |  | vector_cmds.rs:1360 |
| `path.stroke` | Stroke Path | — |  | vector_cmds.rs:1368 |
| `layer.vectorMask.add` | Add Vector Mask | Layer › Vector Mask |  | vector_cmds.rs:1376 |
| `layer.vectorMask.fromPath` | Vector Mask from Current Path | Layer › Vector Mask |  | vector_cmds.rs:1384 |
| `layer.vectorMask.edit` | Edit Vector Mask | — |  | vector_cmds.rs:1392 |
| `layer.vectorMask.delete` | Delete Vector Mask | Layer › Vector Mask |  | vector_cmds.rs:1399 |
| `layer.rasterize.vectorMask` | Rasterize Vector Mask | — |  | vector_cmds.rs:1401 |
| `layer.vectorMask.revealAll` | Vector Mask: Reveal All | — |  | vector_cmds.rs:1409 |
| `layer.vectorMask.hideAll` | Vector Mask: Hide All | — |  | vector_cmds.rs:1414 |
| `layer.vectorMask.currentPath` | Vector Mask: Current Path | — |  | vector_cmds.rs:1419 |
| `layer.vectorMask.enabled` | Enable Vector Mask | — |  | vector_cmds.rs:1422 |
| `layer.vectorMask.linked` | Link Vector Mask | — |  | vector_cmds.rs:1425 |
| `layer.rasterize.shape` | Rasterize Shape | — |  | vector_cmds.rs:1428 |
| `layer.combineShapes.unite` | Unite Shapes | — |  | vector_cmds.rs:1430 |
| `layer.combineShapes.subtractFrontShape` | Subtract Front Shape | — |  | vector_cmds.rs:1437 |
| `layer.combineShapes.intersectShapeAreas` | Intersect Shape Areas | — |  | vector_cmds.rs:1441 |
| `layer.combineShapes.excludeOverlappingShapes` | Exclude Overlapping Shapes | — |  | vector_cmds.rs:1445 |
| `layer.combineShapes.mergeShapeComponents` | Merge Shape Components | — |  | vector_cmds.rs:1449 |
| `select.convertToShape` | Convert Selection to Shape | — |  | vector_cmds.rs:1457 |
| `layer.vectorMask.info` | Vector Mask Info | — |  | vector_cmds.rs:1465 |
| `select.quick` | Quick Selection | — |  | smartselect_cmds.rs:226 |
| `select.object` | Object Selection | — |  | smartselect_cmds.rs:234 |
| `select.subject` | Subject | Select |  | smartselect_cmds.rs:242 |
| `select.refineEdge` | Refine Edge | — |  | smartselect_cmds.rs:250 |
| `select.focusArea` | Focus Area… | Select |  | smartselect_cmds.rs:258 |
| `paint.symmetryFromPath` | Make Symmetry Path | — |  | symmetry_cmds.rs:125 |
| `paint.symmetryDisable` | Disable Symmetry Path | — |  | symmetry_cmds.rs:135 |
| `edit.cut` | Cut | Edit | Cmd+X | edit_cmds.rs:469 |
| `edit.copy` | Copy | Edit | Cmd+C | edit_cmds.rs:476 |
| `edit.copyMerged` | Copy Merged | Edit | Cmd+Shift+C | edit_cmds.rs:477 |
| `edit.paste` | Paste | Edit | Cmd+V | edit_cmds.rs:479 |
| `file.newFromClipboard` | New from Clipboard | File |  | edit_cmds.rs:488 |
| `edit.pasteSpecial.pasteInPlace` | Paste in Place | Edit › Paste Special | Cmd+Shift+V | edit_cmds.rs:496 |
| `layer.new.layerViaCopy` | Layer via Copy | Layer › New | Cmd+J | edit_cmds.rs:497 |
| `layer.new.layerViaCut` | Layer via Cut | Layer › New | Cmd+Shift+J | edit_cmds.rs:498 |
| `layer.mergeVisible` | Merge Visible | Layer | Cmd+Shift+E | edit_cmds.rs:499 |
| `image.autoTone` | Auto Tone | Image | Cmd+Shift+L | edit_cmds.rs:500 |
| `image.autoContrast` | Auto Contrast | Image | Cmd+Alt+Shift+L | edit_cmds.rs:501 |
| `image.autoColor` | Auto Color | Image | Cmd+Shift+B | edit_cmds.rs:502 |
| `edit.toggleLastState` | Toggle Last State | Edit | Cmd+Alt+Z | edit_cmds.rs:503 |
| `edit.transform.again` | Again | Edit › Transform | Cmd+Shift+T | edit_cmds.rs:504 |
| `edit.transform.againCopy` | Transform Again on a Copy | — | Cmd+Alt+Shift+T | edit_cmds.rs:506 |
| `view.newGuide` | New Guide… | View |  | edit_cmds.rs:514 |
| `view.moveGuide` | Move Guide | — |  | edit_cmds.rs:517 |
| `view.deleteGuide` | Delete Guide | — |  | edit_cmds.rs:520 |
| `view.clearGuides` | Clear Guides | View |  | edit_cmds.rs:521 |
| `edit.assignProfile` | Assign Profile… | Edit |  | color_cmds.rs:955 |
| `edit.convertToProfile` | Convert to Profile… | Edit |  | color_cmds.rs:964 |
| `edit.colorSettings` | Color Settings… | Edit |  | color_cmds.rs:973 |
| `color.profileMismatch` | Embedded Profile Mismatch | — |  | color_cmds.rs:983 |
| `edit.profileInfo` | Profile Info | — |  | color_cmds.rs:991 |
| `view.proofSetup` | Proof Setup… | — |  | color_cmds.rs:993 |
| `view.proofColors` | Proof Colors | View |  | color_cmds.rs:1001 |
| `view.gamutWarning` | Gamut Warning | View |  | color_cmds.rs:1003 |
| `paint.pencil` | ? | ? |  | brush_cmds.rs:720 |
| `paint.mixerBrush` | ? | ? |  | brush_cmds.rs:728 |
| `paint.colorReplacement` | ? | ? |  | brush_cmds.rs:736 |
| `brush.presets.list` | ? | ? |  | brush_cmds.rs:744 |
| `brush.presets.save` | ? | ? |  | brush_cmds.rs:745 |
| `brush.presets.delete` | ? | ? |  | brush_cmds.rs:746 |
| `brush.defineFromSelection` | ? | ? |  | brush_cmds.rs:747 |
| `brush.get` | ? | ? |  | brush_cmds.rs:748 |
| `tools.setBrush` | ? | ? |  | brush_cmds.rs:749 |
| `brush.presets.rename` | ? | ? |  | brush_preset_cmds.rs:208 |
| `brush.presets.move` | ? | ? |  | brush_preset_cmds.rs:209 |
| `brush.presets.moveGroup` | ? | ? |  | brush_preset_cmds.rs:215 |
| `brush.presets.renameGroup` | ? | ? |  | brush_preset_cmds.rs:221 |
| `brush.presets.deleteGroup` | ? | ? |  | brush_preset_cmds.rs:222 |
| `paint.magicEraser` | Magic Eraser | — |  | eraser_cmds.rs:169 |
| `paint.backgroundEraser` | Background Eraser | — |  | eraser_cmds.rs:179 |
| `brush.presets.importAbr` | Import Brushes… | — |  | preset_import_cmds.rs:114 |
| `gradient.presets.importGrd` | Import Gradients… | — |  | preset_import_cmds.rs:124 |
| `paint.cloneStamp` | Clone Stamp | — |  | retouch_cmds.rs:656 |
| `paint.healingBrush` | Healing Brush | — |  | retouch_cmds.rs:668 |
| `paint.spotHealing` | Spot Healing Brush | — |  | retouch_cmds.rs:680 |
| `paint.patch` | Patch | — |  | retouch_cmds.rs:690 |
| `paint.dodge` | Dodge | — |  | retouch_cmds.rs:700 |
| `paint.burn` | Burn | — |  | retouch_cmds.rs:710 |
| `paint.sponge` | Sponge | — |  | retouch_cmds.rs:720 |
| `paint.blur` | Blur | — |  | retouch_cmds.rs:730 |
| `paint.sharpen` | Sharpen | — |  | retouch_cmds.rs:740 |
| `paint.smudge` | Smudge | — |  | retouch_cmds.rs:750 |
| `paint.historyBrush` | History Brush | — |  | retouch_cmds.rs:760 |
| `image.imageSize` | Image Size… | Image |  | image_cmds.rs:368 |
| `image.canvasSize` | Canvas Size… | Image |  | image_cmds.rs:376 |
| `image.crop` | Crop | Image |  | image_cmds.rs:383 |
| `image.trim` | Trim… | Image |  | image_cmds.rs:385 |
| `image.mode.rgb` | RGB Color | Image › Mode |  | image_cmds.rs:393 |
| `image.mode.grayscale` | Grayscale | Image › Mode |  | image_cmds.rs:401 |
| `image.mode.cmyk` | CMYK Color | Image › Mode |  | image_cmds.rs:409 |
| `image.mode.lab` | Lab Color | Image › Mode |  | image_cmds.rs:417 |
| `image.mode.bits8` | 8 Bits/Channel | Image › Mode |  | image_cmds.rs:424 |
| `image.mode.bits16` | 16 Bits/Channel | Image › Mode |  | image_cmds.rs:425 |
| `image.mode.bits32` | 32 Bits/Channel | Image › Mode |  | image_cmds.rs:426 |
| `image.duplicate` | Duplicate… | Image |  | image_cmds.rs:427 |
| `select.magicWand` | Magic Wand | — |  | selection_cmds.rs:328 |
| `select.colorRange` | Color Range… | Select |  | selection_cmds.rs:336 |
| `select.modify.border` | Border… | Select › Modify |  | selection_cmds.rs:343 |
| `select.modify.smooth` | Smooth… | Select › Modify |  | selection_cmds.rs:344 |
| `select.modify.expand` | Expand… | Select › Modify |  | selection_cmds.rs:345 |
| `select.modify.contract` | Contract… | Select › Modify |  | selection_cmds.rs:346 |
| `select.modify.feather` | Feather… | Select › Modify |  | selection_cmds.rs:347 |
| `select.grow` | Grow | Select |  | selection_cmds.rs:348 |
| `select.similar` | Similar | Select |  | selection_cmds.rs:349 |
| `select.lasso` | Lasso | — |  | selection_cmds.rs:353 |
| `select.sky` | Sky | Select |  | select_extra_cmds.rs:215 |
| `select.isolateLayers` | Isolate Layers | Select |  | select_extra_cmds.rs:225 |
| `select.transformSelection` | Transform Selection | Select |  | select_extra_cmds.rs:235 |
| `paint.bucket` | Paint Bucket | — |  | paint_cmds.rs:116 |
| `paint.gradient` | Gradient | — |  | paint_cmds.rs:126 |
| `edit.stroke` | Stroke… | Edit |  | extra_cmds.rs:556 |
| `edit.transform.rotate180` | Rotate 180° | Edit › Transform |  | extra_cmds.rs:564 |
| `edit.transform.rotate90Cw` | Rotate 90° Clockwise | Edit › Transform |  | extra_cmds.rs:565 |
| `edit.transform.rotate90Ccw` | Rotate 90° Counter Clockwise | Edit › Transform |  | extra_cmds.rs:566 |
| `edit.transform.flipHorizontal` | Flip Horizontal | Edit › Transform |  | extra_cmds.rs:570 |
| `edit.transform.flipVertical` | Flip Vertical | Edit › Transform |  | extra_cmds.rs:571 |
| `edit.pasteSpecial.pasteInto` | Paste Into | Edit › Paste Special | Cmd+Alt+Shift+V | extra_cmds.rs:573 |
| `edit.pasteSpecial.pasteOutside` | Paste Outside | Edit › Paste Special |  | extra_cmds.rs:581 |
| `select.reselect` | Reselect | Select | Cmd+Shift+D | extra_cmds.rs:584 |
| `image.adjustments.equalize` | Equalize | Image › Adjustments |  | extra_cmds.rs:592 |
| `image.revealAll` | Reveal All | Image |  | extra_cmds.rs:593 |
| `layer.new.layerFromBackground` | Layer From Background… | Layer › New |  | extra_cmds.rs:603 |
| `layer.layerStyle.copyLayerStyle` | Copy Layer Style | Layer › Layer Style |  | extra_cmds.rs:604 |
| `layer.layerStyle.pasteLayerStyle` | Paste Layer Style | Layer › Layer Style |  | extra_cmds.rs:612 |
| `layer.layerStyle.hideAllEffects` | Hide All Effects | Layer › Layer Style |  | extra_cmds.rs:634 |
| `layer.layerStyle.showAllEffects` | Show All Effects | — |  | extra_cmds.rs:635 |
| `layer.layerMask.enabled` | Disable Layer Mask | Layer › Layer Mask |  | extra_cmds.rs:637 |
| `layer.layerMask.linked` | Unlink Layer Mask | Layer › Layer Mask |  | extra_cmds.rs:646 |
| `layer.rasterize.layer` | Layer | Layer › Rasterize |  | extra_cmds.rs:654 |
| `layer.rasterize.allLayers` | All Layers | Layer › Rasterize |  | extra_cmds.rs:655 |
| `layer.rasterize.type` | Type | Layer › Rasterize |  | extra_cmds.rs:656 |
| `layer.rasterize.fillContent` | Fill Content | Layer › Rasterize |  | extra_cmds.rs:657 |
| `layer.rasterize.smartObject` | Smart Object | Layer › Rasterize |  | extra_cmds.rs:662 |
| `layer.delete.hiddenLayers` | Hidden Layers | Layer › Delete |  | extra_cmds.rs:667 |
| `file.scripts.deleteAllEmptyLayers` | Delete All Empty Layers | File › Scripts |  | extra_cmds.rs:669 |
| `layer.ungroupLayers` | Ungroup Layers | Layer | Cmd+Shift+G | extra_cmds.rs:675 |
| `layer.hideLayers` | Hide Layers | Layer | Cmd+, | extra_cmds.rs:686 |
| `layer.showLayers` | Show Layers | — |  | extra_cmds.rs:687 |
| `filter.blur.average` | Average | Filter › Blur |  | extra_cmds.rs:688 |
| `filter.render.clouds` | Clouds | Filter › Render |  | extra_cmds.rs:689 |
| `filter.render.differenceClouds` | Difference Clouds | Filter › Render |  | extra_cmds.rs:690 |
| `file.closeAll` | Close All | File | Cmd+Alt+W | file_cmds.rs:1037 |
| `file.closeOthers` | Close Others | File | Cmd+Alt+P | file_cmds.rs:1039 |
| `file.revert` | Revert | File | F12 | file_cmds.rs:1047 |
| `file.saveACopy` | Save a Copy… | File | Cmd+Alt+S | file_cmds.rs:1049 |
| `file.openAs` | Open As… | File | Cmd+Alt+Shift+O | file_cmds.rs:1058 |
| `file.placeEmbedded` | Place Embedded… | File |  | file_cmds.rs:1067 |
| `file.placeLinked` | Place Linked… | File |  | file_cmds.rs:1075 |
| `file.fileInfo` | File Info… | File | Cmd+Alt+Shift+I | file_cmds.rs:1079 |
| `file.automate.fitImage` | Fit Image… | File › Automate |  | file_cmds.rs:1088 |
| `file.automate.conditionalModeChange` | Conditional Mode Change… | File › Automate |  | file_cmds.rs:1097 |
| `file.automate.batch` | Batch… | File › Automate |  | file_cmds.rs:1106 |
| `file.scripts.imageProcessor` | Image Processor… | File › Scripts |  | file_cmds.rs:1115 |
| `file.scripts.loadFilesIntoStack` | Load Files into Stack… | File › Scripts |  | file_cmds.rs:1124 |
| `file.scripts.flattenAllLayerEffects` | Flatten All Layer Effects | File › Scripts |  | file_cmds.rs:1132 |
| `file.scripts.flattenAllMasks` | Flatten All Masks | File › Scripts |  | file_cmds.rs:1134 |
| `file.export.layersToFiles` | Layers to Files… | File › Export |  | file_cmds.rs:1143 |
| `file.export.colorLookupTables` | Color Lookup Tables… | File › Export |  | file_cmds.rs:1152 |
| `view.newGuideLayout` | New Guide Layout… | View |  | file_cmds.rs:1161 |
| `view.newGuidesFromShape` | New Guides From Shape | View |  | file_cmds.rs:1169 |
| `view.clearCanvasGuides` | Clear Canvas Guides | View |  | file_cmds.rs:1170 |
| `type.antiAlias.none` | None | Type › Anti-Alias |  | type_extra_cmds.rs:519 |
| `type.antiAlias.sharp` | Sharp | Type › Anti-Alias |  | type_extra_cmds.rs:520 |
| `type.antiAlias.crisp` | Crisp | Type › Anti-Alias |  | type_extra_cmds.rs:521 |
| `type.antiAlias.strong` | Strong | Type › Anti-Alias |  | type_extra_cmds.rs:522 |
| `type.antiAlias.smooth` | Smooth | Type › Anti-Alias |  | type_extra_cmds.rs:523 |
| `type.antiAlias.windowsLcd` | Windows LCD | Type › Anti-Alias |  | type_extra_cmds.rs:524 |
| `type.antiAlias.windows` | Windows | Type › Anti-Alias |  | type_extra_cmds.rs:525 |
| `type.orientation.horizontal` | Horizontal | Type › Orientation |  | type_extra_cmds.rs:526 |
| `type.orientation.vertical` | Vertical | Type › Orientation |  | type_extra_cmds.rs:527 |
| `type.openType.standardLigatures` | Standard Ligatures | Type › OpenType |  | type_extra_cmds.rs:528 |
| `type.openType.contextualAlternates` | Contextual Alternates | Type › OpenType |  | type_extra_cmds.rs:529 |
| `type.openType.discretionaryLigatures` | Discretionary Ligatures | Type › OpenType |  | type_extra_cmds.rs:530 |
| `type.openType.swash` | Swash | Type › OpenType |  | type_extra_cmds.rs:531 |
| `type.openType.oldstyle` | Oldstyle | Type › OpenType |  | type_extra_cmds.rs:532 |
| `type.openType.stylisticAlternates` | Stylistic Alternates | Type › OpenType |  | type_extra_cmds.rs:533 |
| `type.openType.titlingAlternates` | Titling Alternates | Type › OpenType |  | type_extra_cmds.rs:534 |
| `type.openType.ornaments` | Ornaments | Type › OpenType |  | type_extra_cmds.rs:535 |
| `type.openType.ordinals` | Ordinals | Type › OpenType |  | type_extra_cmds.rs:536 |
| `type.openType.fractions` | Fractions | Type › OpenType |  | type_extra_cmds.rs:537 |
| `type.createWorkPath` | Create Work Path | Type |  | type_extra_cmds.rs:538 |
| `type.convertToShape` | Convert to Shape | Type |  | type_extra_cmds.rs:539 |
| `type.rasterizeTypeLayer` | Rasterize Type Layer | Type |  | type_extra_cmds.rs:540 |
| `type.convertToParagraphText` | Convert to Paragraph Text | Type |  | type_extra_cmds.rs:541 |
| `type.convertToPointText` | Convert to Point Text | Type |  | type_extra_cmds.rs:542 |
| `type.warpText` | Warp Text… | Type |  | type_extra_cmds.rs:544 |
| `type.updateAllTextLayers` | Update All Text Layers | Type |  | type_extra_cmds.rs:551 |
| `type.replaceAllMissingFonts` | Replace All Missing Fonts | Type |  | type_extra_cmds.rs:552 |
| `type.resolveMissingFonts` | Resolve Missing Fonts… | Type |  | type_extra_cmds.rs:558 |
| `type.pasteLoremIpsum` | Paste Lorem Ipsum | Type |  | type_extra_cmds.rs:566 |
| `type.saveDefaultTypeStyles` | Save Default Type Styles | Type |  | type_extra_cmds.rs:574 |
| `type.loadDefaultTypeStyles` | Load Default Type Styles | Type |  | type_extra_cmds.rs:581 |
| `edit.checkSpelling` | Check Spelling… | Edit |  | type_spell_cmds.rs:237 |
| `type.insertText` | Insert Glyph | — |  | type_spell_cmds.rs:247 |
| `layer.smartObjects.convertToSmartObject` | ? | Layer › Smart Objects |  | smart_cmds.rs:877 |
| `filter.convertForSmartFilters` | Convert for Smart Filters | Filter |  | smart_cmds.rs:878 |
| `layer.smartObjects.newSmartObjectViaCopy` | ? | Layer › Smart Objects |  | smart_cmds.rs:879 |
| `layer.smartObjects.rasterize` | ? | Layer › Smart Objects |  | smart_cmds.rs:880 |
| `layer.smartObjects.editContents` | ? | Layer › Smart Objects |  | smart_cmds.rs:881 |
| `layer.smartObjects.saveContents` | Save Contents | — |  | smart_cmds.rs:889 |
| `layer.smartObjects.replaceContents` | ? | Layer › Smart Objects |  | smart_cmds.rs:893 |
| `layer.smartObjects.exportContents` | ? | Layer › Smart Objects |  | smart_cmds.rs:894 |
| `layer.smartObjects.relinkToFile` | ? | Layer › Smart Objects |  | smart_cmds.rs:895 |
| `layer.smartObjects.updateModifiedContent` | ? | Layer › Smart Objects |  | smart_cmds.rs:899 |
| `layer.smartObjects.updateAllModifiedContent` | ? | Layer › Smart Objects |  | smart_cmds.rs:904 |
| `layer.smartObjects.convertToEmbedded` | ? | Layer › Smart Objects |  | smart_cmds.rs:912 |
| `layer.smartObjects.convertToLinked` | ? | Layer › Smart Objects |  | smart_cmds.rs:918 |
| `layer.smartFilter.disableSmartFilters` | ? | ? |  | smart_cmds.rs:934 |
| `layer.smartFilter.deleteFilterMask` | ? | ? |  | smart_cmds.rs:947 |
| `layer.smartFilter.disableFilterMask` | ? | ? |  | smart_cmds.rs:953 |
| `layer.smartFilter.blendingOptions` | ? | ? |  | smart_cmds.rs:968 |
| `layer.smartFilter.clearSmartFilters` | ? | ? |  | smart_cmds.rs:976 |
| `layer.smartFilter.setVisible` | Show/Hide Smart Filter | — |  | smart_cmds.rs:984 |
| `layer.smartFilter.setParams` | Edit Smart Filter | — |  | smart_cmds.rs:992 |
| `layer.smartFilter.delete` | Delete Smart Filter | — |  | smart_cmds.rs:999 |
| `layer.smartFilter.move` | Move Smart Filter | — |  | smart_cmds.rs:1000 |
| `select.allLayers` | All Layers | Select | Cmd+Alt+A | layer_multi_cmds.rs:754 |
| `select.deselectLayers` | Deselect Layers | Select |  | layer_multi_cmds.rs:755 |
| `select.findLayers` | Find Layers | Select | Cmd+Alt+Shift+F | layer_multi_cmds.rs:763 |
| `layer.selectLinkedLayers` | Select Linked Layers | Layer |  | layer_multi_cmds.rs:764 |
| `layer.align.topEdges` | Top Edges | Layer › Align |  | layer_multi_cmds.rs:765 |
| `layer.align.verticalCenters` | Vertical Centers | Layer › Align |  | layer_multi_cmds.rs:766 |
| `layer.align.bottomEdges` | Bottom Edges | Layer › Align |  | layer_multi_cmds.rs:767 |
| `layer.align.leftEdges` | Left Edges | Layer › Align |  | layer_multi_cmds.rs:768 |
| `layer.align.horizontalCenters` | Horizontal Centers | Layer › Align |  | layer_multi_cmds.rs:769 |
| `layer.align.rightEdges` | Right Edges | Layer › Align |  | layer_multi_cmds.rs:770 |
| `layer.distribute.topEdges` | Top Edges | Layer › Distribute |  | layer_multi_cmds.rs:771 |
| `layer.distribute.verticalCenters` | Vertical Centers | Layer › Distribute |  | layer_multi_cmds.rs:772 |
| `layer.distribute.bottomEdges` | Bottom Edges | Layer › Distribute |  | layer_multi_cmds.rs:776 |
| `layer.distribute.leftEdges` | Left Edges | Layer › Distribute |  | layer_multi_cmds.rs:777 |
| `layer.distribute.horizontalCenters` | Horizontal Centers | Layer › Distribute |  | layer_multi_cmds.rs:778 |
| `layer.distribute.rightEdges` | Right Edges | Layer › Distribute |  | layer_multi_cmds.rs:782 |
| `layer.distribute.horizontally` | Horizontally | Layer › Distribute |  | layer_multi_cmds.rs:784 |
| `layer.distribute.vertically` | Vertically | Layer › Distribute |  | layer_multi_cmds.rs:792 |
| `layer.linkLayers` | Link Layers | Layer |  | layer_multi_cmds.rs:796 |
| `layer.mergeLayers` | Merge Layers | Layer | Cmd+E | layer_multi_cmds.rs:799 |
| `layer.new.groupFromLayers` | Group from Layers… | Layer › New |  | layer_multi_cmds.rs:800 |
| `layer.arrange.reverse` | Reverse | Layer › Arrange |  | layer_multi_cmds.rs:801 |
| `layer.lockLayers` | Lock Layers… | Layer |  | layer_multi_cmds.rs:803 |
| `layer.renameLayer` | Rename Layer | Layer |  | layer_multi_cmds.rs:811 |
| `prefs.get` | Get Preferences | — |  | prefs.rs:1545 |
| `prefs.set` | Set Preferences | — |  | prefs.rs:1554 |
| `prefs.reset` | Reset Preferences | — |  | prefs.rs:1562 |
| `edit.preferences.general` | ? | ? |  | prefs.rs:1563 |
| `edit.preferences.interface` | ? | ? |  | prefs.rs:1564 |
| `edit.preferences.workspace` | ? | ? |  | prefs.rs:1565 |
| `edit.preferences.tools` | ? | ? |  | prefs.rs:1566 |
| `edit.preferences.historyLog` | ? | ? |  | prefs.rs:1567 |
| `edit.preferences.fileHandling` | ? | ? |  | prefs.rs:1568 |
| `edit.preferences.export` | ? | ? |  | prefs.rs:1569 |
| `edit.preferences.performance` | ? | ? |  | prefs.rs:1570 |
| `edit.preferences.scratchDisks` | ? | ? |  | prefs.rs:1571 |
| `edit.preferences.cursors` | ? | ? |  | prefs.rs:1572 |
| `edit.preferences.transparencyAndGamut` | ? | ? |  | prefs.rs:1573 |
| `edit.preferences.unitsAndRulers` | ? | ? |  | prefs.rs:1574 |
| `edit.preferences.guidesGridAndSlices` | ? | ? |  | prefs.rs:1575 |
| `edit.preferences.plugIns` | ? | ? |  | prefs.rs:1576 |
| `edit.preferences.type` | ? | ? |  | prefs.rs:1577 |
| `edit.preferences.enhancedControls` | ? | ? |  | prefs.rs:1578 |
| `edit.preferences.rawDefaults` | ? | ? |  | prefs.rs:1579 |
| `edit.preferences.integrations` | ? | ? |  | prefs.rs:1580 |
| `edit.keyboardShortcuts` | Keyboard Shortcuts… | Edit | Cmd+Alt+Shift+K | prefs.rs:1582 |
| `edit.menus` | Menus… | Edit | Cmd+Alt+Shift+M | prefs.rs:1591 |
| `edit.toolbar` | Toolbar… | Edit |  | prefs.rs:1599 |
| `edit.fade` | Fade… | Edit | Cmd+Shift+F | edit_menu_cmds.rs:930 |
| `edit.purge.undo` | Undo | Edit › Purge |  | edit_menu_cmds.rs:938 |
| `edit.purge.clipboard` | Clipboard | Edit › Purge |  | edit_menu_cmds.rs:939 |
| `edit.purge.histories` | Histories | Edit › Purge |  | edit_menu_cmds.rs:940 |
| `edit.purge.videoCache` | Video Cache | Edit › Purge |  | edit_menu_cmds.rs:941 |
| `edit.purge.all` | All | Edit › Purge |  | edit_menu_cmds.rs:944 |
| `edit.contentAwareFill` | Content-Aware Fill… | Edit |  | edit_menu_cmds.rs:946 |
| `edit.contentAwareScale` | Content-Aware Scale | Edit | Cmd+Alt+Shift+C | edit_menu_cmds.rs:955 |
| `edit.defineBrushPreset` | Define Brush Preset… | Edit |  | edit_menu_cmds.rs:964 |
| `edit.defineCustomShape` | Define Custom Shape… | Edit |  | edit_menu_cmds.rs:973 |
| `edit.findAndReplaceText` | Find and Replace Text… | Edit |  | edit_menu_cmds.rs:982 |
| `edit.presets.presetManager` | Preset Manager… | Edit › Presets |  | edit_menu_cmds.rs:991 |
| `edit.presets.exportImportPresets` | Export/Import Presets… | Edit › Presets |  | edit_menu_cmds.rs:1000 |
| `edit.fillForeground` | Fill with Foreground Color | — | Alt+Backspace | fill_key_cmds.rs:45 |
| `edit.fillBackground` | Fill with Background Color | — | Cmd+Backspace | fill_key_cmds.rs:55 |
| `edit.fillForegroundPreserve` | Fill with Foreground Color, Preserve Transparency | — | Alt+Shift+Backspace | fill_key_cmds.rs:65 |
| `edit.fillBackgroundPreserve` | Fill with Background Color, Preserve Transparency | — | Cmd+Shift+Backspace | fill_key_cmds.rs:75 |
| `layer.stampVisible` | Stamp Visible | — | Cmd+Alt+Shift+E | stamp_cmds.rs:146 |
| `layer.stampDown` | Stamp Down | — | Cmd+Alt+E | stamp_cmds.rs:156 |
| `edit.autoAlignLayers` | ? | ? |  | align_cmds.rs:225 |
| `edit.autoBlendLayers` | ? | ? |  | align_cmds.rs:231 |
| `file.automate.photomerge` | Photomerge… | File › Automate |  | photo_cmds.rs:798 |
| `file.automate.mergeToHdrPro` | Merge to HDR Pro… | File › Automate |  | photo_cmds.rs:808 |
| `file.automate.cropAndStraightenPhotos` | Crop and Straighten Photos | File › Automate |  | photo_cmds.rs:818 |
| `filter.lensCorrection` | Lens Correction… | Filter |  | lens_cmds.rs:383 |
| `filter.adaptiveWideAngle` | Adaptive Wide Angle… | Filter |  | lens_cmds.rs:393 |
| `filter.cameraRaw` | Camera Raw Filter… | Filter |  | lens_cmds.rs:403 |
| `file.automate.lensCorrection` | Lens Correction… | File › Automate |  | lens_cmds.rs:413 |
| `filter.vanishingPoint` | Vanishing Point… | Filter | Cmd+Alt+V | vp_cmds.rs:199 |
| `image.adjustments.shadowsHighlights` | Shadows/Highlights… | Image › Adjustments |  | adjust_cmds.rs:353 |
| `image.adjustments.replaceColor` | Replace Color… | Image › Adjustments |  | adjust_cmds.rs:361 |
| `image.adjustments.matchColor` | Match Color… | Image › Adjustments |  | adjust_cmds.rs:369 |
| `image.adjustments.hdrToning` | HDR Toning… | Image › Adjustments |  | adjust_cmds.rs:377 |
| `image.adjustments.colorLookup.list` | List Color Lookup Looks | — |  | adjust_cmds.rs:385 |
| `layer.layerMask.apply` | Apply | Layer › Layer Mask |  | layer_menu_cmds.rs:729 |
| `layer.layerMask.fromTransparency` | From Transparency | Layer › Layer Mask |  | layer_menu_cmds.rs:730 |
| `layer.layerMask.hideSelection` | Hide Selection | Layer › Layer Mask |  | layer_menu_cmds.rs:731 |
| `layer.maskAllObjects` | Mask All Objects | Layer |  | layer_menu_cmds.rs:732 |
| `layer.matting.defringe` | Defringe… | Layer › Matting |  | layer_menu_cmds.rs:733 |
| `layer.matting.removeBlackMatte` | Remove Black Matte | Layer › Matting |  | layer_menu_cmds.rs:734 |
| `layer.matting.removeWhiteMatte` | Remove White Matte | Layer › Matting |  | layer_menu_cmds.rs:735 |
| `layer.matting.colorDecontaminate` | Color Decontaminate… | Layer › Matting |  | layer_menu_cmds.rs:737 |
| `layer.smartObjects.revealInFinder` | Reveal in Finder | Layer › Smart Objects |  | layer_menu_cmds.rs:757 |
| `layer.layerStyle.blendingOptions` | Blending Options… | Layer › Layer Style |  | layer_menu_cmds.rs:765 |
| `layer.layerStyle.globalLight` | Global Light… | Layer › Layer Style |  | layer_menu_cmds.rs:773 |
| `layer.layerStyle.createLayer` | Create Layer | Layer › Layer Style |  | layer_menu_cmds.rs:780 |
| `layer.layerStyle.scaleEffects` | Scale Effects… | Layer › Layer Style |  | layer_menu_cmds.rs:781 |
| `layer.layerContentOptions` | Layer Content Options… | Layer |  | layer_menu_cmds.rs:783 |
| `layer.quickExportAsPng` | Quick Export as PNG | Layer |  | layer_menu_cmds.rs:792 |
| `layer.exportAs` | Export As… | Layer |  | layer_menu_cmds.rs:799 |
| `image.rotation.arbitrary` | Arbitrary… | Image › Image Rotation |  | mode_cmds.rs:423 |
| `image.mode.indexedColor` | Indexed Color… | Image › Mode |  | mode_cmds.rs:431 |
| `image.mode.colorTable` | Color Table… | Image › Mode |  | mode_cmds.rs:443 |
| `image.mode.bitmap` | Bitmap… | Image › Mode |  | mode_cmds.rs:451 |
| `image.mode.duotone` | Duotone… | Image › Mode |  | mode_cmds.rs:459 |
| `image.mode.multichannel` | Multichannel | Image › Mode |  | multichannel_cmds.rs:208 |
| `edit.definePattern` | Define Pattern… | Edit |  | pattern_cmds.rs:352 |
| `pattern.list` | Patterns | — |  | pattern_cmds.rs:362 |
| `pattern.rename` | Rename Pattern | — |  | pattern_cmds.rs:372 |
| `pattern.delete` | Delete Pattern | — |  | pattern_cmds.rs:382 |
| `pattern.import` | Import Patterns… | — |  | pattern_cmds.rs:392 |
| `pattern.export` | Export Patterns… | — |  | pattern_cmds.rs:402 |
| `layer.newFillLayer.pattern` | Pattern… | Layer › New Fill Layer |  | pattern_cmds.rs:412 |
| `brush.texturePattern` | Brush Texture Pattern | — |  | pattern_cmds.rs:422 |
| `edit.transform.warp` | Warp | Edit › Transform |  | warp_cmds.rs:406 |
| `layer.smartObjects.warp` | Warp | Layer › Smart Objects |  | warp_cmds.rs:416 |
| `edit.transform.splitWarpCrosswise` | Split Warp Crosswise | Edit › Transform |  | warp_cmds.rs:426 |
| `edit.transform.splitWarpHorizontally` | Split Warp Horizontally | Edit › Transform |  | warp_cmds.rs:436 |
| `edit.transform.splitWarpVertically` | Split Warp Vertically | Edit › Transform |  | warp_cmds.rs:446 |
| `edit.transform.removeWarpSplit` | Remove Warp Split | Edit › Transform |  | warp_cmds.rs:456 |
| `edit.transform.warpGrid` | Warp Grid | — |  | warp_cmds.rs:466 |
| `layerComp.new` | New Layer Comp… | — |  | comps_cmds.rs:381 |
| `layerComp.update` | Update Layer Comp | — |  | comps_cmds.rs:389 |
| `layerComp.apply` | Apply Layer Comp | — |  | comps_cmds.rs:396 |
| `layerComp.previous` | Apply Previous Layer Comp | — |  | comps_cmds.rs:397 |
| `layerComp.next` | Apply Next Layer Comp | — |  | comps_cmds.rs:398 |
| `layerComp.delete` | Delete Layer Comp | — |  | comps_cmds.rs:399 |
| `layerComp.duplicate` | Duplicate Layer Comp | — |  | comps_cmds.rs:400 |
| `layerComp.rename` | Rename Layer Comp | — |  | comps_cmds.rs:401 |
| `layerComp.setComment` | Layer Comp Comment | — |  | comps_cmds.rs:402 |
| `layerComp.setOptions` | Layer Comp Options… | — |  | comps_cmds.rs:404 |
| `layerComp.restoreLastDocumentState` | Restore Last Document State | — |  | comps_cmds.rs:411 |
| `layerComp.updateWarnings` | Layer Comp Warnings | — |  | comps_cmds.rs:413 |
| `layerComp.list` | List Layer Comps | — |  | comps_cmds.rs:423 |
| `file.export.layerCompsToFiles` | Layer Comps to Files… | File › Export |  | comps_cmds.rs:432 |
| `layer.new.artboard` | Artboard… | Layer › New |  | artboard_cmds.rs:440 |
| `layer.new.artboardFromGroup` | Artboard from Group… | Layer › New |  | artboard_cmds.rs:448 |
| `layer.new.artboardFromLayers` | Artboard from Layers… | Layer › New |  | artboard_cmds.rs:456 |
| `layer.artboard.set` | Edit Artboard | — |  | artboard_cmds.rs:464 |
| `view.clearSelectedArtboardGuides` | Clear Selected Artboard Guides | View |  | artboard_cmds.rs:472 |
| `file.export.artboardsToFiles` | Artboards to Files… | File › Export |  | artboard_cmds.rs:480 |
| `file.export.artboardsToPdf` | Artboards to PDF… | File › Export |  | artboard_cmds.rs:488 |
| `filter.liquify` | Liquify… | Filter |  | distort_cmds.rs:371 |
| `edit.puppetWarp` | Puppet Warp | Edit |  | distort_cmds.rs:381 |
| `layer.smartObjects.puppetWarp` | Puppet Warp | Layer › Smart Objects |  | distort_cmds.rs:391 |
| `edit.perspectiveWarp` | Perspective Warp | Edit |  | distort_cmds.rs:401 |
| `layer.smartObjects.perspectiveWarp` | Perspective Warp | Layer › Smart Objects |  | distort_cmds.rs:411 |
| `image.analysis.setMeasurementScale` | Set Measurement Scale… | Image › Analysis |  | analysis_cmds.rs:1106 |
| `image.analysis.selectDataPoints` | Select Data Points… | Image › Analysis |  | analysis_cmds.rs:1115 |
| `image.analysis.recordMeasurements` | Record Measurements | Image › Analysis |  | analysis_cmds.rs:1124 |
| `image.analysis.rulerTool` | Ruler Tool | Image › Analysis |  | analysis_cmds.rs:1133 |
| `image.analysis.countTool` | Count Tool | Image › Analysis |  | analysis_cmds.rs:1142 |
| `image.analysis.placeScaleMarker` | Place Scale Marker… | Image › Analysis |  | analysis_cmds.rs:1151 |
| `image.analysis.straightenLayer` | Straighten Layer | — |  | analysis_cmds.rs:1160 |
| `image.analysis.info` | Analysis Info | — |  | analysis_cmds.rs:1168 |
| `count.add` | Add Count | — |  | analysis_cmds.rs:1169 |
| `count.remove` | Remove Count | — |  | analysis_cmds.rs:1170 |
| `count.move` | Move Count | — |  | analysis_cmds.rs:1171 |
| `count.clear` | Clear Count | — |  | analysis_cmds.rs:1172 |
| `count.newGroup` | New Count Group | — |  | analysis_cmds.rs:1173 |
| `count.deleteGroup` | Delete Count Group | — |  | analysis_cmds.rs:1174 |
| `count.setGroup` | Count Group Options | — |  | analysis_cmds.rs:1176 |
| `measurementLog.list` | Measurement Log | — |  | analysis_cmds.rs:1184 |
| `measurementLog.delete` | Delete Measurements | — |  | analysis_cmds.rs:1185 |
| `measurementLog.export` | Export Measurements… | — |  | analysis_cmds.rs:1187 |
| `notes.add` | New Note | — |  | notes_cmds.rs:194 |
| `notes.set` | Edit Note | — |  | notes_cmds.rs:204 |
| `notes.delete` | Delete Note | — |  | notes_cmds.rs:214 |
| `notes.list` | Notes | — |  | notes_cmds.rs:224 |
| `file.import.notes` | Notes… | File › Import |  | notes_cmds.rs:234 |
| `view.proofSetup.workingCyanPlate` | ? | View › Proof Setup |  | proof_sim.rs:303 |
| `view.proofSetup.workingMagentaPlate` | ? | View › Proof Setup |  | proof_sim.rs:304 |
| `view.proofSetup.workingYellowPlate` | ? | View › Proof Setup |  | proof_sim.rs:305 |
| `view.proofSetup.workingBlackPlate` | ? | View › Proof Setup |  | proof_sim.rs:306 |
| `view.proofSetup.workingCmyPlate` | ? | View › Proof Setup |  | proof_sim.rs:307 |
| `view.proofSetup.legacyMacintoshRgb` | ? | View › Proof Setup |  | proof_sim.rs:308 |
| `view.proofSetup.colorBlindnessProtanopia` | ? | View › Proof Setup |  | proof_sim.rs:309 |
| `view.proofSetup.colorBlindnessDeuteranopia` | ? | View › Proof Setup |  | proof_sim.rs:310 |
| `view.thirtyTwoBitPreviewOptions` | 32-bit Preview Options… | View |  | proof_sim.rs:312 |
| `gradient.presets.list` | Gradient Presets | — |  | presets/gradients.rs:494 |
| `gradient.presets.select` | Select Gradient | — |  | presets/gradients.rs:504 |
| `gradient.presets.apply` | New Gradient Fill Layer from Preset | — |  | presets/gradients.rs:516 |
| `gradient.presets.new` | New Gradient Preset | — |  | presets/gradients.rs:528 |
| `gradient.presets.edit` | Edit Gradient Presets | — |  | presets/gradients.rs:538 |
| `gradient.presets.reset` | Restore Default Gradients | — |  | presets/gradients.rs:548 |
| `pattern.presets.list` | Pattern Presets | — |  | presets/patterns.rs:161 |
| `pattern.presets.select` | Select Pattern | — |  | presets/patterns.rs:171 |
| `pattern.presets.apply` | New Pattern Fill Layer from Preset | — |  | presets/patterns.rs:181 |
| `pattern.presets.new` | New Pattern Preset | — |  | presets/patterns.rs:191 |
| `pattern.presets.edit` | Edit Pattern Presets | — |  | presets/patterns.rs:201 |
| `style.presets.list` | Style Presets | — |  | presets/styles.rs:313 |
| `style.presets.apply` | Apply Style | — |  | presets/styles.rs:323 |
| `style.presets.new` | New Style… | — |  | presets/styles.rs:333 |
| `style.presets.edit` | Edit Style Presets | — |  | presets/styles.rs:343 |
| `style.presets.reset` | Restore Default Styles | — |  | presets/styles.rs:353 |
| `shape.presets.list` | Shape Presets | — |  | presets/shapes.rs:432 |
| `shape.presets.place` | Place Custom Shape | — |  | presets/shapes.rs:442 |
| `shape.presets.new` | New Shape Preset | — |  | presets/shapes.rs:452 |
| `shape.presets.edit` | Edit Shape Presets | — |  | presets/shapes.rs:462 |
| `shape.presets.reset` | Restore Default Shapes | — |  | presets/shapes.rs:472 |
| `tool.presets.list` | Tool Presets | — |  | presets/tools.rs:143 |
| `tool.presets.new` | New Tool Preset… | — |  | presets/tools.rs:153 |
| `tool.presets.select` | Select Tool Preset | — |  | presets/tools.rs:163 |
| `tool.presets.edit` | Edit Tool Presets | — |  | presets/tools.rs:173 |
| `tool.presets.reset` | Reset Tool Presets | — |  | presets/tools.rs:183 |
| `cloneSource.list` | Clone Sources | — |  | presets/clone_source.rs:346 |
| `cloneSource.select` | Select Clone Source | — |  | presets/clone_source.rs:356 |
| `cloneSource.set` | Set Clone Source | — |  | presets/clone_source.rs:366 |
| `cloneSource.resetTransform` | Reset Transform | — |  | presets/clone_source.rs:376 |
| `cloneSource.overlay` | Clone Source Overlay | — |  | presets/clone_source.rs:386 |
| `filter.render.flame` | Flame… | Filter › Render |  | render_cmds.rs:188 |
| `filter.render.pictureFrame` | Picture Frame… | Filter › Render |  | render_cmds.rs:198 |
| `filter.render.tree` | Tree… | Filter › Render |  | render_cmds.rs:208 |
| `slice.new` | Slice Tool | — |  | slice_cmds.rs:452 |
| `slice.fromGuides` | Slices From Guides | — |  | slice_cmds.rs:459 |
| `slice.set` | Slice Options… | — |  | slice_cmds.rs:463 |
| `slice.promote` | Promote | — |  | slice_cmds.rs:470 |
| `slice.delete` | Delete Slice | — |  | slice_cmds.rs:471 |
| `slice.divide` | Divide Slice… | — |  | slice_cmds.rs:473 |
| `slice.list` | List Slices | — |  | slice_cmds.rs:481 |
| `layer.newLayerBasedSlice` | New Layer Based Slice | Layer |  | slice_cmds.rs:491 |
| `view.lockSlices` | Lock Slices | View |  | slice_cmds.rs:498 |
| `view.clearSlices` | Clear Slices | View |  | slice_cmds.rs:499 |
| `file.export.saveForWebLegacy` | Save for Web (Legacy)… | File › Export | Cmd+Alt+Shift+S | web_cmds.rs:1167 |
| `file.export.exportPreferences` | Export Preferences… | File › Export |  | web_cmds.rs:1176 |
| `file.export.quickExport` | Quick Export | — |  | web_cmds.rs:1185 |
| `file.generate.imageAssets` | Image Assets | File › Generate |  | web_cmds.rs:1194 |
| `file.automate.contactSheetII` | Contact Sheet II… | File › Automate |  | automate_cmds.rs:525 |
| `file.automate.createDroplet` | Create Droplet… | File › Automate |  | automate_cmds.rs:533 |
| `file.automate.runDroplet` | Run Droplet | — |  | automate_cmds.rs:541 |
| `file.scripts.statistics` | Statistics… | File › Scripts |  | automate_cmds.rs:549 |
| `file.scripts.browse` | Browse… | File › Scripts |  | automate_cmds.rs:557 |
| `file.scripts.scriptEventsManager` | Script Events Manager… | File › Scripts |  | automate_cmds.rs:565 |
| `file.print` | Print… | File | Cmd+P | print_cmds.rs:554 |
| `file.printOneCopy` | Print One Copy | File | Cmd+Alt+Shift+P | print_cmds.rs:556 |
| `file.package` | Package… | File |  | print_cmds.rs:565 |
| `file.export.pathsToIllustrator` | Paths to Illustrator… | File › Export |  | print_cmds.rs:574 |
| `layer.pickAt` | Auto-Select Layer | — |  | pick_cmds.rs:86 |
| `layer.selectAbove` | ? | ? |  | layer_nav_cmds.rs:95 |
| `layer.selectBelow` | ? | ? |  | layer_nav_cmds.rs:96 |
| `layer.selectTop` | ? | ? |  | layer_nav_cmds.rs:97 |
| `layer.selectBottom` | ? | ? |  | layer_nav_cmds.rs:98 |
| `layer.addAboveToSelection` | ? | ? |  | layer_nav_cmds.rs:99 |
| `layer.addBelowToSelection` | ? | ? |  | layer_nav_cmds.rs:100 |
| `layer.new.frameFromLayers` | Frame from Layers | Layer › New |  | frame_cmds.rs:79 |
| `edit.presets.migratePresets` | Migrate Presets | Edit › Presets |  | migrate_cmds.rs:69 |
| `image.trap` | Trap… | Image |  | trap_cmds.rs:47 |
| `timeline.create` | ? | ? |  | timeline_cmds.rs:104 |
| `timeline.delete` | ? | ? |  | timeline_cmds.rs:105 |
| `timeline.setFrame` | ? | ? |  | timeline_cmds.rs:106 |
| `timeline.nextFrame` | ? | ? |  | timeline_cmds.rs:107 |
| `timeline.previousFrame` | ? | ? |  | timeline_cmds.rs:108 |
| `timeline.setProps` | ? | ? |  | timeline_cmds.rs:109 |
| `timeline.info` | ? | ? |  | timeline_cmds.rs:110 |
| `layer.videoLayers.newBlankVideoLayer` | ? | Layer › Video Layers |  | video_cmds.rs:359 |
| `layer.videoLayers.insertBlankFrame` | ? | Layer › Video Layers |  | video_cmds.rs:360 |
| `layer.videoLayers.duplicateFrame` | ? | Layer › Video Layers |  | video_cmds.rs:361 |
| `layer.videoLayers.deleteFrame` | ? | Layer › Video Layers |  | video_cmds.rs:362 |
| `layer.videoLayers.restoreFrame` | ? | Layer › Video Layers |  | video_cmds.rs:363 |
| `layer.videoLayers.restoreAllFrames` | ? | Layer › Video Layers |  | video_cmds.rs:364 |
| `layer.videoLayers.showAlteredVideo` | ? | Layer › Video Layers |  | video_cmds.rs:365 |
| `layer.videoLayers.rasterize` | ? | Layer › Video Layers |  | video_cmds.rs:366 |
| `layer.rasterize.video` | Video | Layer › Rasterize |  | video_cmds.rs:367 |
| `layer.videoLayers.newVideoLayerFromFile` | ? | Layer › Video Layers |  | video_cmds.rs:368 |
| `layer.videoLayers.replaceFootage` | ? | Layer › Video Layers |  | video_cmds.rs:369 |
| `layer.videoLayers.interpretFootage` | ? | Layer › Video Layers |  | video_cmds.rs:370 |
| `layer.videoLayers.reloadFrame` | ? | Layer › Video Layers |  | video_cmds.rs:371 |
| `file.import.videoFramesToLayers` | Video Frames to Layers… | File › Import |  | video_cmds.rs:372 |
| `file.export.renderVideo` | Render Video… | File › Export |  | video_cmds.rs:373 |
| `jobs.list` | List Background Jobs | — |  | jobs.rs:729 |
| `jobs.cancel` | Cancel Background Job | — |  | jobs.rs:739 |
| `file.import.wiaSupport` | WIA Support… | File › Import |  | wia_cmds.rs:26 |
| `image.variables.define` | Define… | Image › Variables |  | variables_cmds.rs:387 |
| `image.variables.dataSets` | Data Sets… | Image › Variables |  | variables_cmds.rs:394 |
| `image.applyDataSet` | Apply Data Set… | Image |  | variables_cmds.rs:401 |
| `file.import.variableDataSets` | Variable Data Sets… | File › Import |  | variables_cmds.rs:408 |
| `file.export.dataSetsAsFiles` | Data Sets as Files… | File › Export |  | variables_cmds.rs:415 |
| `variables.list` | ? | ? |  | variables_cmds.rs:422 |
| `plugin.list` | List Plug-ins | — |  | plugin_cmds.rs:226 |
| `plugin.install` | Install Plug-in… | Filter › Plug-ins |  | plugin_cmds.rs:239 |
| `plugin.remove` | Remove Plug-in | — |  | plugin_cmds.rs:249 |
| `plugin.reload` | Reload Plug-ins | — |  | plugin_cmds.rs:262 |
| `plugin.run` | Run Plug-in | — |  | plugin_cmds.rs:272 |
| `layer.setExpanded` | Expand/Collapse Group | — |  | group_view_cmds.rs:84 |
| `layer.setEffectsExpanded` | Expand/Collapse Effects | — |  | fx_view_cmds.rs:64 |
| `view.layerMask` | View Layer Mask | — |  | mask_view_cmds.rs:126 |

## 10. Localisation (lu, `crates/ui-egui/src/i18n/`)

- **10 langues** (`LANGUAGES`, `i18n/mod.rs:78-94`) : English `en` (source, intégrée, pas de catalogue), 日本語 `ja`, 简体中文 `zh-hans`, 繁體中文 `zh-hant` (zh-TW/HK/MO), Español `es`, Русский `ru`, Čeština `cs`, **Français `fr`**, Bahasa Indonesia `id`, 한국어 `ko`. Catalogues `*.tsv` embarqués par `include_str!` ; règles de pluriel par langue (français : 0 et 1 au singulier, `plural_fr` l.73-75). Licence des traductions : `i18n/LICENSE-translations.txt`. Doc : `docs/localization.md`, `docs/localization-zh-hans.md`.
- **Clés** : le texte anglais du code est la clé (`tl!("…")` → `i18n::t`, `lib.rs:11-15`) ; format TSV « contexte ⇥ source ⇥ traduction » (`fr.tsv:1-10`) : contexte vide = chaîne simple ; `@id` = traduction attachée à un **id de commande** (prioritaire sur le libellé pour ce menu, `tr_id` l.310) ; `@plural` = formes « one|other » ; autre contexte (ex. `cameraRaw`) = homonyme désambiguïsé (`tr_ctx` l.305). Échappements `\n \t \\` ; placeholders `{nom}` obligatoires des deux côtés (`fmt` l.315, `trn` l.324). Une chaîne absente s'affiche en anglais.
- Fonctions : `tr` (l.300), `tr_ctx` (l.305), `tr_id` (l.310), `fmt` (l.315), `trn` (l.324), `current`/`set_current` (l.242-247), `system_lang` (l.190, détection de la locale système, repli anglais) ; la préférence `interface.language` (`auto` = système) se change à chaud dans Préférences › Interface › Language (`docs/localization.md`).
- Les ids de commande, chemins de menus logiques, canal de contrôle, CLI et MCP ne voient jamais de texte traduit (`i18n/mod.rs:1-5`). Les menus sont traduits au rendu (`menus.rs:764, 849`).
- Conventions françaises (en-tête de `fr.tsv`) : menus en noms, commandes à l'infinitif, casse de phrase, espace insécable avant « : ; ? ! % » et dans les guillemets, RGB/CMYK → RVB/CMJN, « … » conservé ; traduction « clean-room » (sans ressource Adobe).

| Fichier | Lignes de traduction (hors commentaires) | Entrées @id | Entrées @plural | Entrées à contexte |
|---|---|---|---|---|
| cs.tsv | 2020 | 4 | 4 | 13 |
| es.tsv | 2103 | 1 | 5 | 15 |
| fr.tsv | 2465 | 2 | 5 | 8 |
| id.tsv | 2463 | 0 | 5 | 8 |
| ja.tsv | 2010 | 0 | 5 | 6 |
| ko.tsv | 2010 | 0 | 5 | 6 |
| ru.tsv | 2219 | 0 | 5 | 21 |
| zh-hans.tsv | 2050 | 0 | 5 | 8 |
| zh-hant.tsv | 2013 | 0 | 5 | 9 |

Toutes les entrées des menus (§1) ont une traduction française dans `fr.tsv` sauf la ligne dynamique des fichiers récents (vérifié par script).

