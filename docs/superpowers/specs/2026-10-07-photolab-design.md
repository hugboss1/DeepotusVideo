# Photolab « reproduire photocraft dans Deepotus » — conception depuis l'inventaire de photocraft v0.3.0

> Inventaire : `2026-10-07-photocraft-inventaire.md` (partie A à l'écran, partie B tirée du code, 2 954 lignes),
> captures `2026-10-07-photocraft-captures/`. Skill de mise en œuvre : `lab-externe-deepotus`.
> Équivalent chez nous : aucun éditeur raster en calques aujourd'hui. Modèles à suivre : le Vectorlab
> (`frontend/vectorlab/`, 76 modules `js/mod-*.js`, monté par `backend/app/main.py`, entrée de barre par
> `scripts/patch_bundle_vectorlab.py`), la Bibliothèque (`backend/app/services/library_index.py` : `SOURCES`,
> `noter`), « Envoyer vers » (`__dzSendTo`, `__dzLibPicker`), la langue (`/shared/dz-i18n.js`, t134).
>
> Demande de l'utilisateur (07/10) : « reproduire à l'identique ce que photocraft produit », « comme vectorlab : une
> fonctionnalité supplémentaire dans la barre de sélection des applications », « en respectant le design général de
> l'application tout en gardant les icônes et les éléments de design de photocraft », « lier cette nouvelle fonction
> aux autres fonctionnalités ». Décisions à valider AVANT le plan.

## Tableau d'écart

| Chez eux (photocraft 0.3.0) | Aujourd'hui chez nous | Décision |
|---|---|---|
| **Moteur** : 24 crates Rust, registre de 500+ commandes (684 ids relevés), même moteur pour l'interface, la CLI, le canal JSON et MCP (B §9) | — | **À faire (D1)** : `photocraft-cli serve` en stdio, version 0.3.0 épinglée, piloté par `backend/app/services/photolab_moteur.py` ; chaque geste de l'écran = une commande moteur → résultats identiques par construction |
| Rendu : compositeur GPU (wgpu), tuiles copy-on-write | — | **Adapté (D1)** : `doc.render` du moteur (PNG) affiché dans un `<canvas>` ; aperçu local en JS pendant un geste, rendu moteur à la validation. Latence à MESURER en premier (spike P1) |
| Zones (A1) : menus 32 · options 36 · onglets · outils 2 col. · rail 5 icônes · 3 groupes de panneaux · état 24 | Vectorlab : `mod-menus`, `mod-barrecontexte`, `mod-onglets`, `mod-barreoutils` + `mod-flyout`, `mod-panneaux`, `mod-statut` | **Adapté (D2)** : même découpage de zones et mêmes cotes que photocraft, dans les tokens Deepotus (`theme-v2.css` : fond #0a0a0c, panneaux #151519/#1c1c21, accent doré #f0b429, Inter/IBM Plex/JetBrains Mono) |
| Icônes : 112 SVG Lucide (`assets/icons`, licence ISC) | icônes maison (DESIGN.md §15, glyphe bicolore) | **Conservé de l'amont (D2)** : les SVG Lucide de photocraft copiés dans `frontend/photolab/icones/` avec leur licence ; trait `currentColor` coloré par nos tokens |
| 5 thèmes (Pro gris par défaut, sombre violet, clair…), qui changent aussi la disposition (A8) | un seul thème (Cinema) | **Écarté** : un seul thème, le nôtre. On reprend de la variante « moderne » le panneau Properties flottant et la barre d'état enrichie (« RGB · 8 bit · 1920 × 1080 · 2 calques · Ajuster ») |
| **Menus** : 10 menus, 653 entrées, 140 séparateurs, raccourcis, entrées grisées selon l'état (B §1) | — | **À faire (D3)** : menus GÉNÉRÉS depuis le catalogue amont (données `menu_catalog.rs` exportées en JSON, MIT/Apache) ; une entrée = un `engine.execute` ; grisée par l'état renvoyé par le moteur. Tout le catalogue d'un coup, mais une entrée sans écran (voir D9) reste visible grisée avec « bientôt » |
| Dialogues : New Document (7 catégories, 33 préréglages), Image/Canvas Size, Export As, Save for Web, Préférences 18 sections (B §5) | — | **À faire (D3)** : sur mesure pour New Document, Image/Canvas Size, Export, et les réglages phares ; GÉNÉRIQUES pour le reste à partir de la description `params` de chaque commande (texte « JSON-ish » : à structurer, coût mesuré en P1) |
| Outils : 45 outils, 20 emplacements, 5 sections, flyout clic droit ou appui long, lettres V M L W C I B E G T H Z J S Y O P A U (B §2, A7) | `mod-barreoutils` + `mod-flyout` (familles d'outils du Vectorlab) | **Adapté (D4)** : même grille, mêmes lettres, même flyout ; outils livrés par lots (P2 : déplacement, sélections, recadrage, pipette, main, zoom ; P3b : peinture et retouche ; texte, formes, plume ensuite) |
| Barre d'options par outil (≈ 30 variantes, B §2) | `mod-barrecontexte` | **Adapté** : même champs et bornes, rendus par nos composants |
| Panneaux : 6 groupes / 19 onglets (Color, Swatches, Gradients, Patterns │ Properties, Adjustments │ Character, Paragraph │ Navigator, Histogram, Info │ History, Actions, Layer Comps │ Layers, Channels, Paths) | Vectorlab : `mod-layers`, `mod-couleur`, `mod-navigateur`, `mod-histogramme`, `mod-pile` | **Adapté** : P2 = Layers, Properties, Color, History, Navigator ; P3 = Adjustments, Swatches, Gradients, Channels ; ensuite Character/Paragraph, Paths, Info, Layer Comps. Actions écarté (D9) |
| Panneau Calques : filtre Kind + 5, mode, Opacity/Fill, 5 verrous, ligne œil/vignette/masque/nom, pied de 7 boutons, ⌘-clic vignette = sélection, ⌥-clic masque, double-clics (B §3, §9) | `mod-layers` (calques vectoriels) | **À faire** : `photolab/js/mod-calques.js`, chaque action = commande `layer.*` |
| 16 calques de réglage (Levels, Curves, Hue/Sat, Brightness/Contrast, Invert, Threshold, Posterize, Exposure, Vibrance, Color Balance, Channel Mixer, Gradient Map, Photo Filter, Selective Color, Black & White, Color Lookup) + 6 destructifs (B §4) | — | **À faire (P3)** : les 16 dans Properties ; Courbes et Niveaux sur mesure (éditeur à points, histogramme), le reste générique |
| 75 filtres en 11 sous-menus + Camera Raw, Liquify, Vanishing Point, Lens Correction, Adaptive Wide Angle (B §4) | — | **À faire (P3)** : les 75 par dialogue générique + aperçu moteur ; **Écarté au départ (D9)** : Camera Raw, Liquify, Vanishing Point, Adaptive Wide Angle, Puppet Warp (interfaces lourdes à part) |
| 27 modes de fusion + Pass Through ; 10 styles de calque + Blending Options (B §4) | modes de fusion du Vectorlab (SVG) | **À faire (P3)** : liste plate identique ; dialogue Style de calque générique |
| Gestes et raccourcis : Espace = main, ⌘Espace zoom, [ ] taille, ⇧[ ] dureté, chiffres = opacité (deux chiffres < 800 ms), ⇧ contraint, ⌥ duplique / soustrait, ↩/Échap, ⌘-clic droit = choisir le calque (B §8) | conventions du Vectorlab (Maj, Alt, Ctrl) | **Conservé de l'amont (D4)** : table de raccourcis reprise telle quelle (Ctrl sous Windows), seuils compris (2 pt duplication, 8° hystérésis, 0,35 s appui long) |
| Formats : PSD/PSB fidèles (307/309 re-sauvegardes), PNG, JPEG, TIFF, WebP (écriture sans perte seulement), GIF, BMP, TGA, ICO, QOI, PNM, EXR, HDR ; raws DNG/CR2/ARW… ; `.pcraft` natif (B §6) | Bibliothèque : images PNG/JPEG/WebP | **Conservé (D5)** : tout ce que le moteur lit s'ouvre ; fichier de travail `.pcraft` rangé à côté de son aperçu PNG ; export PNG/JPG/WebP/TIFF/TGA/PSD |
| Aucune IA générative (Select Subject heuristique) | génération fal/OpenAI (payante, gardée) | **Adapté (D7)** : les générateurs Deepotus deviennent des SOURCES du Photolab (ouvrir une image générée, « Envoyer vers Photolab ») ; aucun appel payant depuis le Photolab |
| Localisation : 10 langues, `fr.tsv` 2 465 entrées, clés = texte anglais + `@id` (B §10) | `dz-i18n` (t134), français de référence | **Conservé (D6)** : les libellés FR et EN de photocraft importés dans `frontend/shared/i18n/photolab.json` ; l'écran naît bilingue |
| Accueil : « New document… », « Open… », dépôt de fichier, liens Discord/GitHub/ArtCraft (A2) | — | **Adapté** : « Nouveau », « Ouvrir depuis la Bibliothèque », « Ouvrir un fichier », dépôt ; liens ArtCraft/Discord retirés (D8) |
| Préréglage « Default Photoshop Size », nom et logos ArtCraft | — | **Écarté (D8)** : renommés (« Taille par défaut ») ; aucun logo amont ; crédit et licences dans « À propos » |
| Enregistrer / Ouvrir : sélecteur système (bureau), téléchargement (web) | Bibliothèque, dépôt `/api/images/upload` | **Adapté (D5)** : Ouvrir et Enregistrer passent par la Bibliothèque (et par un fichier local en option) |
| Impression, scripts/droplets, actions, plugins wasm, MCP, timeline vidéo, Camera Raw | Montage (vidéo), Chapitres | **Écarté (D9)** au départ : hors du besoin « retouche dans Deepotus » ; la vidéo reste au Montage |
| App native `photocraft.exe --control` (GPU natif, polices CJK) | — | **Adapté (D10)** : repli « Ouvrir dans l'app native » pour les très gros fichiers, en P5 |

## Décisions tranchées

**D1 — Le moteur de photocraft fait le calcul, notre écran le pilote.** « Identique » ne se tient qu'avec le même
moteur : `photocraft-cli serve` (stdio, JSON lignes : `engine.execute`, `doc.open/new/save/inspect/render`) épinglé en
0.3.0 et vérifié par empreinte, piloté par le backend. Écart assumé : un aller-retour serveur par geste ; d'où un
**spike de latence en tête de P1** (rendu 1920 × 1080 après un filtre et après un trait de pinceau) — si le rendu
complet est trop lent, rendu par région ou à l'échelle de la vue, sinon repli D10.

*Règle de décision du spike (écrite avant la mesure)* — sur l'aller-retour « commande + rendu 1920 » (médiane de 5) :
≤ 300 ms → D1 tel quel (rendu complet à chaque geste validé) ; 300 ms à 1,5 s → P2 rend à la taille de la vue
(`maxSide` = plus grand côté du canevas affiché) et garde un aperçu JS pendant les gestes continus ; > 1,5 s → le dire
à l'utilisateur avant P2 (rendu par région à demander en amont ou à faire dans un fork, ou repli D10).

*Mesure du 07/10/2026 (spike t136)* — `scripts/photolab_mesure.py`, photocraft-cli 0.3.0, image synthétique 1920 × 1080,
machine : AMD Ryzen Threadripper 2950X (16 cœurs, 32 processeurs logiques), 64 Go de RAM (68 605 505 536 o), Windows 11.
Deux passages à la suite, rien d'autre en cours :

| Mesure (1920 × 1080, médiane de 5) | Passage 1 | Passage 2 |
|---|---|---|
| `doc.render` maxSide 1024 | 85 ms (82–93) | 83 ms (80–91) |
| `doc.render` maxSide 1920 | 74 ms (73–75) | 74 ms (72–77) |
| flou gaussien r=3 | 55 ms (53–56) | 58 ms (54–60) |
| niveaux | 741 ms (520–754) | 742 ms (534–765) |
| nouveau calque + remplissage | 2 ms (2–2) | 2 ms (2–2) |
| **aller-retour flou + rendu 1920** | **148 ms (144–169)** | **163 ms (158–169)** |

Les médianes sont stables d'un passage à l'autre (aller-retour : 148 → 163 ms, soit 10 %, dans les ± 15 %).
**Décision : aller-retour 148 / 163 ms ≤ 300 ms → D1 tel quel** (rendu complet 1920 à chaque geste validé), sans rendu
par région ni repli D10. Réserve à reprendre en P2 : les niveaux coûtent ≈ 740 ms à eux seuls (très au-dessus des
autres commandes), donc un curseur de niveaux continu ne peut pas rappeler le moteur à chaque cran — aperçu JS pendant
le glissement, commande au relâchement.

**D2 — Disposition et icônes de photocraft, couleurs et typographie de Deepotus.** Les zones, cotes, grilles d'outils,
flyouts et icônes Lucide sont ceux de photocraft ; fonds, accent doré, polices et composants sont ceux de `theme-v2`.
Un seul thème.

**D3 — Les menus et la plupart des dialogues sont générés.** 653 entrées à la main seraient des mois ; le catalogue
amont (données) et la description `params` des commandes permettent de tout exposer tôt, en sur-mesure seulement là
où l'interaction l'exige (Nouveau, Taille, Export, Courbes, Niveaux, Style de calque).

**D4 — Gestes et raccourcis repris à l'identique** (table de B §8), adaptés à Windows (Cmd = Ctrl).

**D5 — Fichiers : `.pcraft` comme fichier de travail dans la Bibliothèque**, aperçu PNG à côté ; PSD/PSB et images
en entrée ; un export n'écrase jamais l'original.

**D6 — Bilingue d'emblée** par le dictionnaire `dz-i18n` (zone `photolab`), alimenté par `fr.tsv` de l'amont.

**D7 — Liens avec Deepotus** : Bibliothèque (source `photolab` dans `SOURCES`), « Envoyer vers Photolab » depuis la
Bibliothèque, et depuis le Photolab vers Studio, Quick, Montage, Vectorlab, Spritelab, Tile Lab, Cardforge ; aucune
route payante.

**D8 — Marques** : ni « Photoshop » ni « ArtCraft » dans l'interface ; crédits, licences (MIT OU Apache-2.0, OFL,
ISC/Lucide, SCOWL) et lien du dépôt dans « À propos ».

**D9 — Hors périmètre de départ** : Camera Raw, Liquify, Vanishing Point, Adaptive Wide Angle, Puppet Warp, impression,
actions/scripts/droplets, plugins wasm, MCP, timeline. Visibles grisés « bientôt » dans les menus générés.

**D10 — Repli app native** (`photocraft.exe --control`, port libre, jeton par fichier) pour les gros documents, en P5.

## Lots proposés (remplacent le découpage provisoire t136-t140)

1. **P1 (t136) — moteur et pont** : vendor/photocraft.toml (release 0.3.0, 65 Mo, empreinte), `photolab_moteur.py`
   (session serve, verrou, délai, redémarrage, racines autorisées), routes `/api/photolab/*` ; **spike de latence** ;
   bancs de fidélité (même commande et même entrée → même résultat que `photocraft-cli` lui-même) ; menu catalogue
   exporté en JSON. Téléchargement à autoriser.
2. **P2 (t137) — écran socle** : `frontend/photolab/` + entrée de barre + ⌘K ; zones de D2 ; Nouveau / Ouvrir /
   Enregistrer (Bibliothèque) ; canevas (zoom, main, Espace) ; panneaux Layers, Properties, Color, History, Navigator ;
   outils Déplacement, sélections (rectangle, ellipse, lasso, baguette), recadrage, pipette, main, zoom ; menus générés.
3. **P3 (t138) — réglages, filtres, fusion, styles** : 16 calques de réglage (Courbes et Niveaux sur mesure), 75 filtres
   par dialogue générique avec aperçu, 27 modes, Style de calque.
4. **P3b (nouvelle tâche) — peinture et retouche** : Pinceau, Crayon, Gomme(s), Dégradé, Pot, Tampon, Correcteurs,
   Densité, Flou/Netteté/Doigt ; puis Texte, Formes, Plume (peut se scinder).
5. **P4 (t139) — liens** : Bibliothèque, Envoyer vers (aller et retour), source `photolab`.
6. **P5 (t140) — installation, licences, aide, repli natif**.

## Question à l'utilisateur

D1 est le pivot : faire calculer le moteur de photocraft (résultats identiques) plutôt que de réécrire ses filtres en
JavaScript (rapide à l'écran, jamais identique). Le spike de latence en tête de P1 dira si le rendu suit ; s'il ne
suit pas, le plan propose rendu par région, puis le repli natif.
