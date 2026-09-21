# Montage « aussi poussé que Resolve » — inventaire de DaVinci Resolve 21 (21/09/2026)

> Relevé fait en LECTURE SEULE par le volet intégré, sur le site public
> `blackmagicdesign.com/products/davinciresolve` (version présentée : DaVinci
> Resolve 21 / 21.1, sans compte, aucun bandeau accepté, aucun formulaire).
> Pages lues intégralement : Overview, Edit, Cut, Color, Fusion, Fairlight,
> Media (média + livraison), Collaboration, What's New, Tech Specs. Le texte
> a été extrait par `fetch` + `DOMParser` depuis l'onglet du volet (même
> origine), pied de page et catalogue matériel écartés. **Le logiciel lui-même
> n'a pas été installé** : les cotes, couleurs, typographies et menus entrée
> par entrée de l'application ne sont donc PAS relevés (voir §10). Ce qui
> suit est ce que le site DIT que le logiciel fait, page par page, avec les
> gestes et réglages qu'il nomme. État final du site : identique au départ.

## 0. Cadrage

| | |
|---|---|
| Cible | DaVinci Resolve 21 (gratuit) et Resolve Studio 21 (295 $) — les fonctions « Studio » sont marquées **[Studio]** |
| Fonction visée | toute la table de montage : pistes, découpe, trim, transitions, titres, inspecteur, keyframes, audio, étalonnage, sous-titres, multicam, IA, export |
| Équivalent chez nous | module « Montage » : couche `frontend/patches/son-vfx-montage.js` (bloc `sonvfx`, intouchable) + couche `frontend/patches/montage.js` (`window.DzMontage`, patcher `scripts/patch_bundle_montage.py`) + `backend/app/services/montage_service.py` (routes `/api/montage/*`, ffmpeg) + `effects_engine.py`, `subtitle_service.py`, `transcribe_service.py`, `subs_translate_service.py` |
| Hors périmètre d'entrée | matériel (claviers, panneaux, consoles), Blackmagic Cloud, DeckLink/UltraStudio, RAW caméra, Dolby Vision/Atmos, 3D stéréo, VR |

## 1. Structure du logiciel telle que décrite (zones)

Les cotes ne sont pas relevables sur un site marketing ; les positions sont
celles que le texte donne.

| Zone | Position dite | Contenu |
|---|---|---|
| Barre de pages | bas de l'écran | 8 pages : Media · Photo · Cut · Edit · Fusion · Color · Fairlight · Deliver — « un seul clic pour changer de tâche » |
| Media pool | haut gauche (Edit, Cut) | clips du projet, bins, smart bins, power bins ; vues icône / liste / **filmstrip / slate** (Cut) ; recherche ; barre latérale des bins |
| Effects library | haut gauche (icône) | > 100 transitions, > 80 effets GPU/CPU, titres 2D/3D, Fusion titles, OpenFX tiers, adjustment clips, Fairlight FX |
| Source viewer / Timeline viewer | centre, deux moniteurs (Edit) ; **un seul viewer** avec « source tape » (Cut) | boutons in/out en bas à droite, overlay d'édition, on-screen controls, menu « … » (waveform overlay), pop-up bas gauche (annotations, on-screen controls), **tool strip** sous l'image (Cut) |
| Inspector | haut droite | onglets **Video · Sizing (Cut) · Audio · Effects · File (métadonnées, RAW) · Transition** ; boutons losange de keyframe sur chaque réglage |
| Timeline | bas | pistes V au-dessus, A en dessous, **pistes de sous-titres au-dessus des pistes vidéo** ; en-têtes avec ciblage, verrou, sync ; icône « options de vue » (onglets, empilement) ; icône keyframe à gauche de la barre d'outils (ouvre l'éditeur de courbes SOUS chaque clip) |
| Double timeline (Cut) | haut = programme entier, bas = zone zoomée | « ne plus jamais zoomer » ; les deux sont éditables ; glisser entre les deux |
| Mixer | Edit et Fairlight | fader par piste, vu-mètres, tranches de bus |
| Node editor (Color, Fusion) | haut droite (Color) / bas (Fusion) | graphe de nœuds, vue « liste de calques » (21) |
| Scopes | bas droite (Color) | Parade · Waveform · Vectorscope · Histogram · CIE |
| Gallery (Color) | haut gauche | stills, albums, « Apply Grade » |
| Render queue (Deliver) | droite | liste de jobs, batch, rendu distant **[Studio]** |

## 2. Couleurs et 3. Typographie

Non relevées (logiciel non installé ; le site n'en montre que des captures
compressées). Le site lui-même : fond `#111`–`#1b1b1b` (échantillonné sur
la barre de navigation), accent orange `#e8871e` (bouton « Free Download
Now »), texte blanc, titres de section en cyan `#3ec6ef` sur la page Edit.

## 4. Menus

Le site ne montre aucun menu entrée par entrée. Entrées NOMMÉES par le
texte : **File ▸ Quick Export** (« disponible sur toutes les pages »), **File
▸ New Bin**, **File ▸ Project Settings ▸ Color Management**, **DaVinci
Resolve ▸ Keyboard Customization** (presets d'autres logiciels, export du
preset), **View ▸ Show Audio Track Layers**, **Workspace ▸ People**, **clic
droit ▸ AI tools ▸ Analyze clip for People**, **clic droit ▸ Shot Match to
This Clip**, **clic droit ▸ Elastic Wave**, **clic droit ▸ Normalize**,
**clic droit ▸ Analyze audio level**, **clic droit ▸ Bounce…/Export audio
files**, **clic droit ▸ External audio process**, **clic droit ▸ Create
macro** (Fusion).

## 5. Parcours page par page (fonctions relevées entrée par entrée)

### 5.1 Page Edit — « le NLE professionnel »

**Import.** Glisser-déposer fichiers ou dossiers (sous-dossiers conservés) dans
le media pool ; formats H.264/H.265/ProRes/BRAW/EXR ; aucune transcodage
imposé ; proxies « robustes ».

**Marquage.** Double-clic charge le clip dans le source viewer ; boutons In /
Out en bas à droite ; raccourcis **I** / **O** ; marquage AUDIO et VIDÉO
séparés (split edits, J/L-cut) ; waveform dans le viewer ; scrub « bande
magnétique » avec son.

**Sept modes d'édition** (overlay au dépôt sur le viewer, boutons de barre,
raccourcis) :

| Mode | Effet |
|---|---|
| Insert | insère à la tête et pousse tout à droite ; coupe le clip sous la tête |
| Overwrite | écrase à la tête |
| Replace | remplace un clip par un autre de MÊME durée (le out du nouveau est recalculé) |
| Fit to Fill | remplace en recalculant une VITESSE pour remplir le trou |
| Place on Top | pose sur la piste vidéo libre suivante (titres, PIP) |
| Append at End | ajoute après le dernier clip, tête ignorée ; multi-clips |
| Ripple Overwrite | remplace par une autre durée et RIPPLE le reste |

Puis **swap** et **shuffle** pour réordonner.

**Trim (outil Trim, curseur contextuel)** : Roll (les deux côtés, durée totale
inchangée) · Ripple (allonge/raccourcit et décale la suite) · Slip (déplace
in/out à l'intérieur du clip, contour blanc = source entière) · Slide (déplace
le clip, les voisins compensent). Trim pendant la lecture, avec le son, sur
plusieurs points de plusieurs pistes ; **JKL dynamique** (trim en lecture
bouclée) ; **trim asymétrique** ; commandes « extend », « trim to playhead ».

**Transitions et effets.** Bibliothèque > 100 transitions (wipes, dissolves),
> 80 effets (blurs, flares, warps) ; glisser sur un clip ou une coupe ; durée
par glissement des bords OU inspecteur ; OpenFX tiers.

**Titres.** Text (2D), Text+, Fusion titles (> 100 animés 2D/3D), subtitle
generator ; édition dans l'inspecteur (police, taille, couleur, etc.).

**Keyframes.** Losange à côté de CHAQUE réglage de l'inspecteur ; on-screen
controls pour position/taille/rotation ; icônes keyframe/curve **sur le clip**
dans la timeline → éditeur de keyframes et de courbes sous le clip ; ease
(béziers), copier/coller/déplacer en groupe ; (21) modes loop / pingpong /
relatif, ajustement multi-clips, zoom normalisé, bézier 4 points pour le
retiming.

**Audio (dans Edit).** Barre de niveau au milieu du clip (glisser) ; inspecteur
: niveau, pan, pitch, **EQ paramétrique 6 bandes** ; fader de piste dans le
mixer ; vu-mètres ; > 25 Fairlight FX.

**Livraison.** Quick Export (menu File) : presets YouTube / Vimeo / Dropbox /
TikTok / X, upload direct après connexion ; presets personnalisés créés sur la
page Deliver.

**Outils avancés nommés :** Retime control (speed ramps par courbe, position
d'image + vitesse ; qualité nearest / frame blending / optical flow ; **Speed
Warp [Studio]**) · Picture in Picture (on-screen controls, keyframes, drop
shadow) · **Dynamic Zoom** (bascule dans l'inspecteur, rectangle VERT = début,
ROUGE = fin, glisser/redimensionner) · Stabilisation (camera lock, zoom, crop
ratio, smoothing, strength, bouton « stabilize ») + correction d'objectif ·
**Smooth Cut** (transition par optical flow qui gomme un jump cut) · timelines
empilées et en onglets (copier/coller entre timelines) · Curve editor sous les
clips (liste des paramètres, béziers) · Waveform overlay dans le viewer ·
**Adjustment clips** (piste au-dessus : effet appliqué à tout ce qui est
dessous, nommables, rangeables dans un bin) · **Multicam** (4/9/16/25+
angles, viewer multi, sync par waveform / timecode / in-out, bascule audio
seule ou vidéo seule, retrim et changement d'angle après coup) · **Raccourcis
personnalisables** (tout, y compris menus contextuels ; presets Premiere/FCP/
Avid ; export) · **Sous-titres** (import TTML/SRT/XML/MXF-IMF, création à la
main, piste au-dessus des vidéos, plusieurs pistes = langues, plusieurs
captions par piste, style de piste dans l'inspecteur ; rendu incrusté OU export
TTML/SRT/VTT) · **Marqueurs** (couleur, titre, description, mots-clés, durée)
et **annotations** (surlignage, dessin, texte, formes, partagées) · **Bins**
et smart bins (par caméra, date, scène) · **Reconnaissance faciale [Studio]**
(bins par personne).

### 5.2 Page Cut — « éditer vite »

- **Double timeline** (haut : programme entier ; bas : zone zoomée ; glisser
  entre les deux).
- **Trim automatique** au survol du point de coupe, curseur qui change ;
  **trim editor A/B** dans le viewer (double-clic sur une coupe : clip A en
  haut, B en bas, compteurs d'images, nudge) ; trois lieux de trim.
- **Smart indicator** : marque le point de coupe le plus proche de la tête ;
  la plupart des modes n'exigent pas d'in/out. Boutons : **Smart Insert ·
  Append at End · Place On Top · Close Up [IA : trouve les visages et zoome]
  · Ripple Overwrite · Source Overwrite** (cutaway synchronisé sur la piste
  au-dessus).
- **Source Tape** : tout le bin en une seule « bande » scrollable dans le
  viewer ; fast preview.
- Trim : Roll · Trim in/out (ripple auto) · **Slip = icône au milieu du clip,
  Slide = même icône + Maj** · Durée de transition = glisser le bord de l'icône
  (bulle numérique) · **Audio trim** (loupe de waveform, icône à gauche de
  la timeline haute).
- **Sync bin** (multicam : tous les clips synchrones à la tête en multiview →
  in/out → Source Overwrite) ; **Multi Source** (caméras en cours
  d'enregistrement).
- **Clip inspector** : onglets Video (blend modes, stabilisation,
  distorsion), Sizing (position, crop, échelle), Audio (niveau, pan, pitch,
  EQ), Effects, File (métadonnées, RAW), Transition.
- **Tool strip** (icône outils, bas gauche du viewer) : transform, crop,
  niveau audio, vitesse, stabilisation, correction d'objectif, dynamic zoom.
- Effets/transitions/titres : **aperçu au survol** (déplacer le curseur de
  gauche à droite sur le titre de l'effet) ; catégories blurs, color,
  lighting, stylize, warping, texture ; templates tiers installables.
- **Boring detector** : seuil de longueur max (gris) et de jump cut min
  (rouge), bouton analyser.
- Petits écrans : interface qui se reconfigure ; menus d'import et de rendu
  dans la page.
- Media pool : vues icône / filmstrip / liste / **slate** (vignette + shot,
  scene, take, nom, timecode) ; (21) smart bins dans le menu des bins.
- **Quick Export** sur toutes les pages : presets YouTube / Vimeo / TikTok,
  ProRes, H.264/H.265, presets locaux personnalisés.
- Voice-over palette (page Overview).

### 5.3 Page Color

- **Primaires** : roues Lift / Gamma / Gain / Offset (+ master dial sous
  chaque roue) ; **barres** primaires ; roues **Log** (shadows/midtones/
  highlights resserrés) ; réglages : contrast, pivot, saturation, hue,
  temperature, tint, **midtone detail**, **color boost (vibrance)**,
  shadows, highlights.
- **Auto** : bouton auto color (balance + contraste) ; **Shot Match to This
  Clip** (clic droit) ; **color match** sur chip chart (choix du chart,
  alignement, match).
- **Courbes** : custom (R, G, B, Y + histogramme live), Hue vs Hue, Hue vs
  Sat, Hue vs Lum, Lum vs Sat, Sat vs Sat.
- **Secondaires** : qualifier (pipette, plages H/S/L, magic wand pour voir le
  key) ; **Power Windows** (cercle, courbe/plume, dégradé ; taille, pan,
  rotation, adoucissement ; intérieur/extérieur) ; **tracker** (pan, tilt,
  zoom, rotation, perspective 3D ; track forward/back ; stabilisation ;
  attacher un effet à un objet).
- **Nœuds** : série/parallèle, node editor en flow chart ; (21) vue **liste de
  calques** ; nœuds partagés (verrouillés par défaut) ; groupes (pre-clip /
  clip / post-clip) et (21) versions de groupe.
- **Resolve FX** > 90 : blurs, color, glows, lens flares, vignettes, beauty
  (**face refinement [Studio]**, Ultra Beauty), restoration (dirt removal,
  dust buster, deflicker, chromatic aberration, dead pixel, deband, **object
  removal [Studio]**, patch replacer), sharpening (**UltraSharpen** 21),
  stylize, texture, transform, warp ; **light effects** (aperture
  diffraction, glow, lens flare, lens reflection, light rays, presets golden
  hour / headlights / sci-fi).
- **Scopes** : parade (RGB/YRGB/YCbCr), waveform, vectorscope, histogram, CIE
  chromaticity.
- **Gallery** : still (clic droit viewer), albums, middle-click sur la
  filmstrip pour copier un grade, « Apply Grade », groupes.
- **Compare** : image wipe (horizontal, vertical, mixte, alpha, différence,
  PIP), split screen ; **lightbox** (toutes les vignettes gradées, zoom).
- **HDR [Studio]** : palette HDR par zones, Dolby Vision / HDR10+ / HDR Vivid,
  ST.2084 / HLG ; **Color Warper** (grille hue/sat, hue/lum) ; **RAW
  palette** ; **RGB mixer** (monochrome) ; **noise reduction temporelle et
  spatiale [Studio]** (palette motion effects) ; color management (RCM, ACES,
  tone mapping, LUT) ; **Magic Mask [Studio]** (21 : render in place) ;
  (21) MultiMaster trim manager ; stéréo 3D.

### 5.4 Page Fusion (VFX, motion graphics)

Nœuds (MediaIn → outils → MediaOut), cinq opérations : Merge (fond jaune /
premier plan vert), Insert effects (> 200 tools), Masks (entrée bleue,
trackables), Adjust (inspecteur, keyframes), Fine-tune (spline et keyframe
editors) · **Text+** (police, taille, alignement, espacement, kerning,
interligne ; shading : dégradés, contours, ombres, glows ; animation par bloc
/ ligne / mot / **caractère**) et **Text 3D** (extrusion, biseau, matériaux)
· tracker 2D → « match move » (infographies suivies, PSD multi-calques) ·
paint (clone, par image ou plage, suit un track) · planar tracker + corner
pin · Delta Keyer (pré-matte, matte, fringe, clean plate) · particules 3D
(émetteur + rendu, gravité, friction, turbulence…) · tracker caméra 3D ·
Shift+Espace = recherche d'outil ; versions de nœud ; 1 / 2 = viewers, ~ =
vider · espace 3D (formes, merge 3D, caméra, lumières, ombres), import FBX /
Alembic / (21) USD · Spline editor (linéaire, bézier, b-spline ; reverse,
loop, ping-pong ; squash/stretch de keyframes ; copier une forme de courbe)
· modifiers et expressions (« follower » pour le texte) · roto (béziers,
b-splines, feather par point) · **macros/templates** exposant des contrôles
choisis à Edit/Cut · volumétriques, deep pixel, set extensions · scripting
Python et Lua · (21) Krokodove (70 graphiques), Fairlight Animator
(animation pilotée par l'audio), macro editor inspector view.

### 5.5 Page Fairlight (audio)

- **Focus mode** : bas du clip = sélectionner/déplacer, haut = point d'édition,
  glisser = plage ; playhead qui suit la sélection.
- **Clip** : volume, pan, pitch, **EQ 6 bandes** par clip ; poignées de fondu
  sur les bords ; ligne de gain au milieu ; **Alt/Option + clic = keyframe de
  volume** ; normalisation (clic droit) ; waveform mise à jour en direct.
- **Automation** : icône toolbar, latch/touch, courbes par paramètre dans
  l'en-tête de piste, preview sans écriture, bus aussi.
- **Waveform editing** : zoom jusqu'à l'échantillon → crayon qui redessine.
- **Mixer** : fader, panner stéréo/3D, 6 slots d'effets, dynamics
  (expander/gate, compresseur, limiteur), EQ 6 bandes par tranche ; A/B,
  presets, copie entre pistes.
- **Fairlight FX** > 25 : de-esser, de-hummer, noise reduction (auto ou
  « learn »), **ducker** (source dialogue → cible musique ; duck level,
  recovery), reverb ; **Voice Isolation** et **Music Remixer** (IA) ; VST /
  AU tiers ; Chain FX (21).
- **Sound library** : recherche, marquage, audition dans la timeline,
  confirm/cancel, sync à la tête.
- **Enregistrement** : patch d'entrée, arm (R), record ; prises en couches ;
  **ADR** (cues, beeps, compte à rebours, prompts, prises notées) ; Foley
  sampler [Studio].
- **Elastic wave** (retime sans changement de pitch, keyframes Cmd+clic).
- **Track layers** (prises empilées, fantôme au glisser, composites).
- Bounce clips / pistes / mix ; external processing (iZotope RX) ; loudness
  meters (standard choisi, bleu/jaune/rouge), graphe de loudness, analyse
  hors ligne ; 3D panner [Studio] ; **sync scrollers** (filmstrip + waveform
  déroulants) ; channel mapping (mono ↔ multicanal, adaptatif 36 canaux) ;
  **index** (clips, pistes, marqueurs → spotting list, états lock/arm/solo/
  mute au balayage, réordonner) ; (21) dossiers de pistes repliables, EQ et
  level matcher ; 2 000 pistes, FlexBus (36 canaux, 60 destinations).

### 5.6 Pages Media et Deliver

- **Media** : arborescence des disques en haut, media pool en bas, viewer,
  metadata inspector (> 200 champs, groupes prédéfinis, jeux personnalisés,
  renommage par scène/plan/prise) ; bins / smart bins / **power bins**
  (visibles dans tous les projets) ; **sync audio-vidéo** (timecode ou
  waveform, ou manuel par « link ») aussi dans la timeline Edit ; clone tool
  (checksum XXHash64, plusieurs destinations) ; LUT côté source ; extraction
  audio.
- **Deliver** : Quick Export (YouTube / Vimeo / TikTok / X ; ProRes ; H.264 /
  H.265 ; **audio seul** ; presets maison) ; **render queue** (plusieurs
  timelines ou clips, batch, audio + vidéo / audio seul / vidéo seul, rendu
  distant [Studio]) ; DCP ; (21) MainConcept H.265 / MV-HEVC ; résolutions
  carrées et verticales dans les réglages de projet et de timeline.

### 5.7 Collaboration

Bibliothèque de projets multi-utilisateurs (Blackmagic Cloud ou Project
Server privé gratuit) ; verrouillage automatique de bins et de timelines ;
timelines multi-utilisateurs avec **acceptation des changements** dans le
viewer et **comparaison visuelle de timelines** (ajouté / supprimé / déplacé /
rogné) ; chat intégré ; **marqueurs privés ou partagés** ; cache et monitoring
par utilisateur ; mode lecture seule ; clips auto-verrouillés pendant
l'étalonnage ; **live save** ; Presentations (revue avec marqueurs
bidirectionnels) ; Proxy Generator (dossiers surveillés → H.264 / H.265 /
ProRes) ; sync caméra → cloud.

### 5.8 IA « DaVinci Neural Engine » (surtout [Studio])

Facial recognition (bins par personne) · object detection · **Smart Reframe**
(vertical/carré) · Speed Warp · Super Scale · auto color / color matching ·
Voice Isolation · Music Remixer · Magic Mask · **IntelliSearch** (recherche par
contenu, mots du dialogue, visages) · **AI Speech Generator** (TTS, clonage sur
10 s, vitesse/pitch/inflexion) · CineFocus (profondeur de champ, bokeh) · Face
Age Transformer · Face Reshaper · Blemish Removal · Slate ID (métadonnées
depuis le clap) · UltraSharpen · Motion Deblur · **IntelliScript** (script
Final Draft ou texte → assemblage d'une timeline depuis la transcription) ·
transcription pour sous-titres et **text based editing [Studio]** · IntelliTrack
(panner piloté par la vidéo) · Close Up (Cut).

### 5.9 Nouveautés 21 utiles au montage (What's New)

Keyframes : loop / pingpong / relatif, multi-clips, zoom normalisé des
courbes, bézier 4 points pour le retiming ; effets Fusion animables depuis
Edit/Cut ; **Lottie (.lottie/.json) et OGraf HTML** dans le media pool avec
alpha ; Text+ / MultiText : correcteur multilingue, navigateur de polices,
emojis, **style par caractère** ; smart bins dans Cut ; **Picture in Picture
Resolve FX** (taille, position, coins arrondis, ombre) ; **colonnes note ★ et
tags Good Take / Rejected** ; résolutions verticales ; upload direct réseaux
sociaux ; import ATEM Mini ISO ; EQ clip 6 bandes partout.

## 6. Composants (tels que décrits)

| Composant | États / variantes relevés |
|---|---|
| Overlay d'édition (viewer) | 7 zones : insert, overwrite, replace, fit to fill, place on top, append at end, ripple overwrite |
| Curseur de trim contextuel | ripple / roll / slip / slide selon la position ; icône slip au milieu (Cut) |
| Trim editor A/B (Cut) | clip A en haut, B en bas, compteurs, nudge ; fermé par clic dans la timeline |
| Clip vidéo | barre de niveau (audio), icônes keyframe/curve, contour blanc = source complète (slip), poignées de fondu (audio), bord de transition glissable |
| Dynamic zoom | rectangles vert (début) / rouge (fin) dans le viewer |
| Boring detector | surlignages gris (trop long) / rouge (jump cut) |
| Marqueur | couleur, titre, description, mots-clés, durée, privé/partagé |
| Loudness meter | bleu conforme / jaune tolérance / rouge dépassement |
| Fader d'automation | rouge en écriture, vert terminé |
| Effets/titres | aperçu au survol par balayage gauche-droite |

## 7. Gestes et raccourcis relevés

| Geste / touche | Effet | Page |
|---|---|---|
| I / O | in / out | Edit |
| J K L | lecture arrière / pause / avant ; trim dynamique JKL | Edit |
| Double-clic clip du pool | charger dans le source viewer | Edit |
| Double-clic coupe | trim editor A/B | Cut |
| Glisser bord de clip | trim (ripple auto sur Cut) | Edit, Cut |
| Glisser icône milieu de clip | slip ; **+ Maj** = slide | Cut |
| Glisser bord d'icône de transition | durée (bulle numérique) | Cut |
| Glisser barre de niveau du clip | volume du clip | Edit, Fairlight |
| Alt/Option + clic sur la ligne de gain | keyframe de volume | Fairlight |
| Cmd + clic / Cmd + glisser (elastic wave) | keyframe de retime / ancrer | Fairlight |
| Clic bas / haut du clip / glisser plage | sélection / point d'édition / plage (focus mode) | Fairlight |
| Middle-click sur la filmstrip | copier le grade | Color |
| Clic droit viewer | grab still | Color |
| Glisser dans une roue / master dial | couleur / niveau d'une plage tonale | Color |
| Pipette + glisser | qualifier | Color |
| Shift + Espace | recherche d'outil | Fusion |
| 1 / 2 / ~ | viewer gauche / droit / vider | Fusion |
| Glisser entre les deux timelines | déplacer un clip | Cut |
| Survol + balayage sur un effet | aperçu | Cut |
| Espace | stop enregistrement | Fairlight |
| Zoom à fond | crayon de waveform | Fairlight |
| Tout raccourci | remappable, presets Premiere / FCP / Avid | toutes |

## 8. Réglages et dialogues nommés

| Dialogue / palette | Champs |
|---|---|
| Stabilisation (inspecteur) | camera lock, zoom, crop ratio, smoothing, strength, bouton Stabilize |
| Retime | courbe position/vitesse ; nearest / frame blending / optical flow / Speed Warp |
| Dynamic zoom | on/off, rectangles début/fin |
| Boring detector | longueur max (s), jump cut min (images), Analyze |
| Ducker | source(s) dialogue, duck level, recovery, seuil |
| Noise reduction (audio) | auto / learn |
| Dynamics | expander/gate, compressor, limiter, A/B, presets |
| Noise reduction (vidéo) [Studio] | temporel / spatial, chroma / luma |
| Tracker | pan, tilt, zoom, rotation, perspective 3D, forward/back |
| Power window | forme, taille, pan, rotation, softness, inside/outside |
| Object removal [Studio] | search range, blend mode, clean plate |
| Patch replacer | source/cible, forme, softness, detail |
| Keyframe editor (21) | ease, loop, pingpong, relatif |
| Quick Export | preset (YouTube, Vimeo, TikTok, X, ProRes, H.264, H.265, audio seul, maison) |
| Render queue | job, audio+vidéo / audio seul / vidéo seul, batch |
| Keyboard customization | commande → touche, presets, export |
| Sous-titres (inspecteur) | style de piste : police, couleur, taille, position ; import TTML/SRT/XML ; export TTML/SRT/VTT |
| Project settings | color management (color science, input/timeline/output, tone mapping, LUT), résolutions verticales/carrées, format audio 3D |

## 9. Comportements notés

- Toute action de Cut « fait quelque chose au clic » : pas de mode outil.
- Les transitions se posent sur la coupe, leur durée se règle sur place.
- Les sous-titres sont une PISTE (au-dessus des vidéos), avec plusieurs
  pistes = plusieurs langues, et deux sorties (incrustation ou fichier).
- Les adjustment clips agissent « du haut vers le bas » sur tout ce qui est
  dessous — un effet posé une fois pour N clips.
- L'inspecteur est le même sur Cut, Edit, Fusion, Fairlight (« ils marchent
  tous pareil »).
- Le même keyframe (losange) existe sur chaque paramètre ; les courbes sont
  visibles SOUS le clip dans la timeline.
- Le retime et la stabilisation sont des PROPRIÉTÉS de clip, pas des effets.
- Quick Export est accessible depuis toutes les pages ; le Deliver n'est
  nécessaire que pour les presets et la file de rendu.

## 10. Non relevé

| Élément | Raison |
|---|---|
| Menus complets entrée par entrée, raccourcis par défaut exhaustifs, cotes, couleurs, typographies du logiciel | logiciel non installé ; le site n'en montre que des captures |
| Barre d'outils de la timeline Edit (liste exacte des boutons) | seuls « trim », « keyframe », « snap », « timeline view options » sont nommés |
| Tech Specs logiciel (formats d'import/export exhaustifs) | la page Tech Specs ne liste que le matériel |
| Fonctions Photo, VR, stéréo 3D, HDR, Cloud, panneaux | hors périmètre du Montage |
| Comportement réel (latence, qualité des trackers, de la stabilisation) | non mesurable sur un site |
