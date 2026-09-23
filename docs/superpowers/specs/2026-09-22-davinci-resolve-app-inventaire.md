# Montage « ergonomie, design, usage » — inventaire de DaVinci Resolve 21.1, l'application (22/09/2026)

> Relevé fait en LECTURE SEULE par pilotage du bureau Windows (`mcp__computer-use`,
> Loupe Windows à 200 %, écran 5120 × 1440). Resolve 21.1 (build du
> 10/09/2026, `ReadMe.html`) était lancé mais RÉDUIT, sur le projet « New
> Project » (vide, aucun média). Pour lire l'interface, la fenêtre a été
> restaurée et redimensionnée à 2560 × 1440 en haut à gauche, puis REMISE
> maximisée et réduite ; le gestionnaire de projets a été ouvert (bouton ⌂),
> déplacé à l'origine pour être lu, puis fermé par son bouton « Close ». Les
> pages Edit, Deliver et Media ont été visitées par les onglets du bas ; la page
> active au départ était Cut, elle est Media à la fin (aucune donnée, aucune
> préférence, aucun réglage de rendu modifié — la liste des presets a été
> ouverte puis fermée par Échap). Un clic est tombé dans la zone de transport
> de la page Cut sans effet visible. Complète le relevé du site du 21/09
> (`2026-09-21-davinci-resolve-inventaire.md`, fonctionnel) par ce qui se VOIT
> dans l'application : structure, cotes, couleurs, menus, dialogues d'import,
> de projet et de livraison. Les cotes sont en px écran à 100 % (fenêtre
> 2560 × 1440), mesurées sous Loupe et divisées par deux.

## 0. Ce que dit le ReadMe 21.1 (notes de version, 10/09/2026) — les traits utiles au Montage

Résumé du fichier `C:\Program Files\Blackmagic Design\DaVinci Resolve\Documents\ReadMe.html`
(la liste complète est dans le fichier ; ici, les entrées qui touchent une
page Cut/Edit/Deliver ou l'import, sans la partie Fusion/Color/Photo) :

| Page | Nouveautés 21.1 relevées |
|---|---|
| Media | champs de la vue liste éditables ; recherche dans les sous-bins avec correspondance exacte ; aperçu des géométries ; changer le timecode de départ de plusieurs clips ; supprimer plusieurs marqueurs en vue liste ; dates créé/modifié pour multicams, compound clips et timelines ; raccourcis pour afficher/masquer la vue des bins |
| Cut / Edit | **presets d'inspecteur** ; **workflow de comparaison de timelines** ; Data Burn lisant les métadonnées d'une piste ; marqueurs de présentation avec annotations, réponses et statut ; zoom des formes d'onde ; **indicateur de tête de lecture dans l'inspecteur et le viewer** ; la sélection se vide quand on pose In/Out ; trim editor amélioré (glisser + nudge) ; dynamic trim par défaut en mode trim ; **couper/copier/coller des TROUS** ; option « échelle automatique des formes d'onde » ; option « afficher la durée des clips » ; **transitions sur les clips d'ajustement** ; export de la liste des marqueurs en PDF ; Alt+glisser conserve les transitions ; sauvegardes de timeline avec historique ; préférences : arrêter la lecture au scrub, toujours jouer l'audio au déplacement de tête, sélectionner le clip après la lame ; inspecteur qui suit la sélection automatique de piste ; solo/clear solo ; pipette de couleur Fusion dans les viewers ; aperçu du texte des titres dans le navigateur de polices ; sélection du vide après le dernier clip ; Replay : vue d'entrée depuis le mode run |
| Deliver / général | raccourcis pour les actions du menu de la file de rendu ; export de présentation avec sous-titres ; QuickTime et MXF avec plusieurs sous-titres embarqués ; export `.drp` dans la gestion des médias ; options d'archive (stills, LUTs, médias utilisés) ; EXR HTJ2K ; presets clavier utilisateur qui héritent des défauts |
| Notes | l'API de script Python **passe en Studio** ; version gratuite limitée à l'Ultra HD en sortie et à un GPU |

Traduction pour nous : « presets d'inspecteur », « couper/coller des trous », « durée des clips affichée », « transitions sur les clips d'ajustement » et « indicateur de tête dans l'inspecteur » sont les cinq entrées qui recoupent des lots déjà planifiés (L3 D-9, L7) ou proposables à faible coût.

## 1. Structure des zones (fenêtre 2560 × 1440, page Cut au départ)

| Zone | Hauteur / largeur mesurées | Contenu |
|---|---|---|
| Barre de menus | ≈ 28 | logo · **DaVinci Resolve · File · Edit · Trim · Timeline · Clip · Mark · View · Playback · Fusion · Color · Fairlight · Workspace · Help** ; à droite ▁ ▢ ✕ |
| Barre d'interface | ≈ 34 (y 28–62) | gauche : onglets de panneau (Cut : **Media Pool · Sync Bin · Transitions · Titles · Effects · Keyframes** ; Edit : **Media Pool · Effects · Index · Sound Library · Keyframes**) ; centre : **nom du projet** en gras (« New Project ») ; droite : **Quick Export · Full Screen · Mixer · Inspector** (Cut) / **Quick Export · Mixer · Metadata · Inspector** (Edit) / **Audio · Metadata · Inspector · Capture** (Media) / **Render Queue** (Deliver) |
| Bande haute | ≈ 640 (y 62–700) | Cut : media pool 1280 px de large à gauche (barre d'outils du pool ≈ 30 px : icônes nouveau bin, import, dossier, cloud, sync, lien, vue ▦, recherche, tri), bin « Master », message centré **« No clips in media pool » / « Add clips from Media Storage to get started »** ; viewer unique à droite (≈ 1240 px), barre d'outils du viewer (≈ 30 px : vue, timecode 00:00:00:00, ratio, zoom, options), **vu-mètre vertical** de 40 px à l'extrême droite (échelle 0 … −50). Edit : media pool 620 px (arbre **Bins +** / « Master » ; **Smart Bins +** / Keywords / Collections en bas) + **deux viewers** (source « 50 % » / timeline « 50 % ») de 970 px chacun, chacun avec timecode gauche et droite, barre de transport propre (|◀◀ ◀ ■ ▶ ▶▶| ↻) et boutons In/Out. Media : **Media Storage** (arbre des volumes : `E:\VideoResolve (Usage: 65%)`, `C:\ (Usage: 65%)`, `D:\`, `DATA (E:\)`), viewer « 53 % », panneau **Embedded Audio** (Meters / Waveform, 16 canaux + Monitor). Deliver : **Render Settings** 450 px + viewer + **Render Queue** 420 px |
| Transport / barre de timeline | 34 (y 700–734) | Cut : à gauche 2 icônes (mode timeline), au centre 6 outils d'édition (smart insert, append, ripple overwrite, close-up, place on top, source overwrite), puis 3 icônes de vue, puis outils (rasoir, lien, marqueur…), **‹ ● ›** (jog), **|◀◀ ◀ ■ ▶ ▶▶| ↻**, **▶| |◀**, **TCG 00:00:00:00** ; Edit : à gauche 3 icônes (options, vue, micro), au centre les **outils** — flèche (sélection), trim, dynamic trim, lame, insert, overwrite, replace, — puis **arc (courbes)**, lien, cadenas, **drapeau bleu ▾**, **marqueur bleu ▾**, 4 boutons de zoom (vue complète, détail, zoom ajusté, −  ●  +), haut-parleur + curseur + **DIM** |
| Timeline | ≈ 700 (y 734–1410) | Cut : **double timeline** — bande haute = toute la timeline (règle 01:00:00:00 → 01:01:30:00 par pas de 10 s), bande basse = zoom autour de la tête (règle par pas de 2 s), tête blanche avec triangle ; en-tête gauche 140 px avec 3 icônes (audio, vidéo, sous-titres ?) puis 5 icônes (vidéo ▣, audio, ciseaux, **drapeau bleu**, œil). Edit : colonne de timecode **01:00:00:00** (gros, 260 px), règle 8 s par graduation (01:00:00:00 → 01:01:04:00), zone vidéo (≈ 420 px) puis zone audio (≈ 130 px) séparées par une ligne, barre de défilement horizontale |
| Barre des pages | 34 (y 1406–1440) | gauche : logo + **DaVinci Resolve 21** ; centre : **Media · Photo · Cut · Edit · Fusion · Color · Fairlight · Deliver** (icône 22 px au-dessus du libellé 11 px, pas ≈ 100 px, page active en blanc sur fond noir avec **soulignement rouge** de 2 px) ; droite : **⌂** (Project Manager) · **⚙** (Project Settings) |

## 2. Couleurs (échantillonnées sur captures, approximatives)

| Rôle | Valeur |
|---|---|
| fond des panneaux (media pool, inspecteur, timeline vide) | ≈ #28282a … #2b2b2d |
| fond des barres (menus, interface, transport, pages) | ≈ #1f1f21 … #222224 |
| fond du viewer | #000000 |
| séparateurs | ≈ #3a3a3c |
| texte principal | ≈ #d6d6d6 ; secondaire ≈ #8f8f8f ; désactivé ≈ #5a5a5a |
| accent « page active » | soulignement **rouge** ≈ #e8433a ; sélection de carte (Project Manager) : contour rouge 1 px |
| accent « actif » (drapeau, marqueur, œil, curseur de zoom) | **bleu** ≈ #3b7dff |
| onglets de panneau actifs | texte blanc, pas de fond ; onglet « Video/Audio/File » du Deliver : fond ≈ #3a3a3c sur le sélectionné |
| bouton d'action (Add to Render Queue, New Project, Close) | pilule fond ≈ #2f2f31, contour ≈ #4a4a4c, rayon ≈ 12 px ; désactivé texte ≈ #5a5a5a |

## 3. Typographie

Une seule famille sans-serif (Open Sans ou équivalent). Menus ≈ 12 px ; libellés de panneau et onglets ≈ 11–12 px ; nom de projet ≈ 13 px gras ; timecode de timeline (Edit) ≈ 22 px, chiffres tabulaires ; `TCG 00:00:00:00` ≈ 12 px gras ; graduations de règle ≈ 9 px. Aucune capitale forcée sauf « TCG » et « DIM ».

## 4. Menus (relevés entrée par entrée)

**File** : New Project… · Open Recent Project ▸ · New Bin (Ctrl+Shift+N, désactivée) · New Smart Bin… (désactivée) · New Timeline… (Ctrl+N) · Close Timeline (désactivée) · — · *[cinq entrées masquées par la barre de la Loupe : Save Project (Ctrl+S), Save Project As…, Save Project With Reduced Media, Revert to… — non relevées]* · Revert to Last Saved Version… (désactivée) · — · Import ▸ · Import Project… · Import Metadata To ▸ · — · Export ▸ · Export Project… (Ctrl+E) · Export Metadata From ▸ · — · Quick Export… · — · Project Manager… (Shift+0) · Project Settings… (Shift+9) · Project Notes… · — · ✓ Single User Project · Multiple User Collaboration (désactivée) · — · Media Management… · Reconform from Bins… · Reconform from Media Storage… · — · easyDCP ▸ · — · Blackmagic Cloud Account ▸

**Timeline** : Add Transition (Ctrl+T) · Add Video Only Transition (Alt+T) · Add Audio Only Transition (Shift+T) · — · Select Clips ▸ · Select Transitions · *[quatre entrées masquées par la barre de la Loupe]* · AI Tools ▸ (désactivée) · Multicam Editing (Ctrl+Shift+\) · Record Voiceover… · — · Audio ▸ · Video ▸ · — · Match Frame (F) · — · ✓ Snapping (N) · ✓ Linked Selection (Ctrl+Shift+L) · — · Source Track Selector ▸ · Auto Select ▸ · Track Lock ▸ · Sync Lock ▸ · Video Track Enable ▸ · — · Output Blanking ▸ · — · Load Current Timeline to Source Viewer (désactivée) · Find Current Timeline in Media Pool (désactivée)

**Edit, Trim, Clip, Mark, View, Playback, Workspace, Help** : non relevés entrée par entrée (le menu Edit ne s'est pas ouvert au premier clic — « un clic sur deux » comme Affinity ; le relevé du site du 21/09 en porte le contenu fonctionnel).

## 5. Dialogues et panneaux relevés

### 5.1 Project Manager (⌂ ou Shift+0) — fenêtre 1350 × 768

Onglets en haut : **Local** (actif, soulignement rouge) · **Network** · **Cloud** ; titre centré « DaVinci Resolve 21 » ; fil « **Projects** » ; barre d'outils droite : nouveau dossier, ?, curseur de taille des vignettes, tri ⇅, ⓘ, vue ▦ (active) / ☰, recherche. Corps : grille de cartes (vignette 140 × 80 + nom en dessous ; carte sélectionnée = contour rouge) — ici une seule carte « New Project ». Pied : **Export** · **Import** (à gauche) · **New Project** · **Close** (au centre-droit). Double-clic sur une carte ouvre le projet ; « New Project » crée une timeline VIDE (aucun média posé).

### 5.2 Page Media (import)

Arbre **Media Storage** des volumes avec le taux d'occupation ; le corps liste les fichiers du dossier choisi ; glisser vers le **Media Pool** (bas) importe. Bas de page : **Bins** (Master) · **Smart Bins** (Keywords, Collections) · media pool « No clips in media pool » · panneau **Metadata** « Nothing to inspect ». Aucun média n'a été importé.

### 5.3 Page Deliver (livraison)

**Render Settings – Custom Export** : `Preset` (liste déroulante, voir 5.4) · `File Name` (Untitled) · `Location` (Browse) · `Render` ● Single clip ○ Individual clips · onglets **Video · Audio · File** · ✓ Export Video · `Format` QuickTime · `Codec` H.264 · `Encoder` Auto · ☐ Network Optimization · `Resolution` Timeline Resolution (1920 × 1080 grisés) · ☐ Use vertical resolution · `Frame rate` Timeline Frame Rate (24 frames per second) · ☐ Chapters from Markers · `Encoding Profile` Auto · … · `Key Frames` ● Automatic ○ Every 30 frames · ✓ Frame reordering · `Preset` Balanced · `Rate Control` Quality · `Quality` Best · ▸ Advanced Settings · ▸ Subtitle Settings · pied : **Estimated File Size 0.00 MB** · bouton **Add to Render Queue** (désactivé sans timeline). Viewer : IN 00:00:00:00 · OUT 00:00:00:00 · DURATION 00:00:00:00 ; sous le viewer, une timeline en lecture seule avec **Render : Entire Timeline ▾** et zoom. **Render Queue** : « No jobs in queue », bouton **Render All** (désactivé).

### 5.4 Liste des presets de livraison (déroulante `Preset`)

Custom Export · *[deux entrées masquées par la barre de la Loupe, vraisemblablement H.264 Master et un preset cloud]* · HyperDeck · H.265 Master · ProRes 422 HQ · **YouTube 1080p ▸** · **Vimeo 1080p ▸** · **TikTok 1080p ▸** · Presentations · Dropbox 1080p ▸ · IMF Generic · Final Cut Pro 7 ▸ · Premiere XML · Audio Only · AVID AAF · Pro Tools (liste coupée en bas de fenêtre, suite non relevée). Les presets « plateforme » portent une icône de marque et un sous-menu de résolutions ; ils sont **la porte de sortie vers les réseaux** (upload direct après rendu si le compte est lié).

## 6. Gestes et comportements notés

- **Une page = un espace de travail** : la barre des pages (bas) change tout l'écran ; la barre d'interface (haut) ne change que les panneaux visibles de la page. Le nom du projet reste au centre, les boutons Quick Export / Mixer / Inspector à droite.
- **Quick Export** est présent sur Cut, Edit et Deliver : un rendu rapide sans passer par la file.
- **Inspector** est un panneau à bascule (bouton en haut à droite), pas une colonne permanente : fermé par défaut sur ce projet vide.
- **Double timeline** (Cut) : la bande haute montre toujours toute la séquence, la bande basse suit la tête ; les deux ont leur règle.
- L'application a démarré RÉDUITE et un clic hors de la fenêtre après un raccourci système ne fait que rendre le focus : les onglets ne répondent qu'au deuxième clic dans ce cas (mesuré trois fois).
- Chaque bouton d'action a une infobulle ; les états désactivés sont gris ≈ #5a5a5a, jamais masqués.

## 7. Non relevé

| Élément | Raison |
|---|---|
| Menus Edit, Trim, Clip, Mark, View, Playback, Workspace, Help | non ouverts (temps) ; contenu fonctionnel dans le relevé du 21/09 |
| Cinq entrées du menu File, quatre du menu Timeline, deux presets Deliver | masqués par la barre flottante de la Loupe (qui ignore les clics synthétiques) |
| Inspecteur ouvert avec un clip, barres contextuelles par état de sélection | projet vide, aucun média importé (import = écriture dans la base de projets, refusée en lecture seule) |
| Pages Fusion, Color, Fairlight, Photo | hors du sujet « Montage » |
| Dialogues New Project…, Quick Export…, Project Settings | non ouverts (ils créent ou modifient) |
