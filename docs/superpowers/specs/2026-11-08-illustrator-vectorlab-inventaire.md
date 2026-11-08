# Adobe Illustrator 2025 → Vectorlab : inventaire et tableau d'écart (08/11/2026)

> **Comment ce relevé a été fait.** Lecture seule des fichiers d'installation d'Illustrator 2025
> (`C:\Program Files\Adobe\Adobe Illustrator 2025`) :
> - le jeu de raccourcis par défaut `Presets/fr_FR/Raccourcis clavier/Paramètres par défaut Illustrator.kys`, qui
>   énumère chaque commande de menu (≈ 570) et chaque outil (≈ 130) sous leur identifiant interne ;
> - les dossiers de modules `Plug-ins/Tools`, `Illustrator Filters`, `Illustrator Formats` et `Extensions` (≈ 90 modules).
>
> Illustrator n'a **pas** été ouvert : aucune préférence ni aucun document n'ont été touchés. **Non relevé à l'écran** :
> libellés français exacts, barres contextuelles, bornes des réglages, phrases d'aide. Les fonctions 2024-2025 marquées
> *(module)* sont déduites du seul nom de leur module : elles sont à confirmer à l'écran.
>
> **Côté Vectorlab**, l'état est relevé dans le code d'origin/main 076690cb : `frontend/vectorlab/js/` (familles, menus,
> onglets, `mod-*.js`) et les routes `/vector/*`.
>
> **Exclusions déjà décidées le 17/09** (spec `2026-09-17-vectorlab-affinity-design.md`) : filet/mesh, formes
> composées non destructives, LAB/ICC/Pantone, contraintes, PSD/AI/EPS, correcteur orthographique, scripting. Elles sont
> rappelées dans le tableau sans être rouvertes d'office.

Légende de la colonne « Chez nous » : ✅ présent · ◐ partiel · ✗ absent · ⛔ exclu le 17/09.

## 1. Outils

| Chez eux (Illustrator) | Chez nous | Détail / fichier |
|---|---|---|
| Sélection, Sélection directe, Sélection progressive | ✅ | `deplacer`, `noeuds` (mod-familles.js) |
| Baguette magique vectorielle (même remplissage, contour…) | ◐ | Édition › Sélectionner par attribut ; pas d'outil |
| Lasso (points vectoriels) | ✗ | lasso seulement en persona Pixel |
| Plume, Ajout / Suppression / Conversion de point | ◐ | Plume + Nœud + Coin ; pas d'outils dédiés ajout/suppression |
| **Courbure** | ✗ | — |
| Crayon, Lissage, Gomme de tracé | ◐ | Crayon (RDP) ✅ ; **Lissage** ✗, **Gomme de tracé** ✗ (seulement la Gomme vectorielle par surface) |
| Pinceau (calligraphique, dispersion, artistique, motif, soies) | ◐ | pinceau vectoriel à profils (plat, fuseau, calligraphie) ; **dispersion, artistique, motif et soies** ✗ |
| **Forme de tache (Blob brush)** | ✗ | — |
| **Shaper** (forme dessinée à main levée → forme nette) | ✗ | — |
| Rectangle, Rectangle arrondi, Ellipse, Polygone, Étoile | ✅ | `rect`, `ellipse`, `forme` paramétrique (+ engrenage, flèche, donut, spirale) |
| Segment, **Arc**, Spirale | ◐ | Ligne ✅, Spirale ✅ ; **Arc** ✗ |
| **Grille rectangulaire / polaire** (objets) | ✗ | les grilles du document existent, pas en objets |
| **Halo** | ✗ | — |
| Texte, Texte captif, Texte curviligne | ✅ | `texte`, `cadre`, `op_texte_sur_chemin` |
| **Texte vertical** (3 variantes), **Retouche de texte** (Touch Type) | ✗ | — |
| Rotation, Miroir, Mise à l'échelle, Inclinaison (point d'origine cliqué) | ◐ | via le panneau Transformer et les poignées ; pas d'outils à point d'origine |
| **Remodelage** | ✗ | — |
| **Outil Largeur** (largeur variable sur un trait existant) | ✗ | largeur seulement au tracé du pinceau |
| **Fluidité** : Déformation, Tourbillon, Contraction, Dilatation, Festons, Cristallisation, Fronces | ✗ | — |
| **Transformation manuelle** (distorsion libre, perspective) | ✗ | — |
| Concepteur de formes | ✅ | `constructeur` |
| Ciseaux, Cutter | ✅ | Diviser au nœud, `couteau` |
| Gomme | ✅ | `gomme` vectorielle |
| **Peinture dynamique** (pot + sélection) | ✗ | — |
| **Grille de perspective** (outil + sélection) | ✗ | — |
| Filet | ⛔ | — |
| Dégradé | ✅ | `degrade` (linéaire, radial, conique) + `transparence` |
| Pipette, Mesure | ✅ | `pipette`, `mesure` |
| **Cotation** (Dimension, 2025) *(module)* | ◐ | la Mesure existe ; la cote posée et persistante ✗ |
| **Dégradé de formes (Blend)** | ✗ | — |
| **Symbolisme** (8 outils : pulvérisateur, décaleur…) | ✗ | les symboles existent, pas leur pulvérisation |
| **Graphes** (9 types : colonnes, barres, courbes, secteurs, radar…) | ✗ | — |
| Plan de travail, Tranche, Sélection de tranche | ✅ | `planche`, `tranche` |
| Main, Zoom, **Rotation de la vue** | ◐ | Main et Loupe ✅ ; Rotation de la vue ✗ |

## 2. Menus Objet, Sélection, Texte, Affichage

| Chez eux | Chez nous | Détail |
|---|---|---|
| Tracé › Joindre, **Moyenne** | ◐ | Relier les courbes ✅ ; Moyenne ✗ |
| Tracé › **Vectoriser le contour** | ✗ | — |
| Tracé › Décalage | ✅ | `op_contour`, vivant |
| Tracé › **Simplifier** (curseur, sur un tracé existant) | ✗ | seulement au tracé du crayon |
| Tracé › **Ajouter / Supprimer des points d'ancrage**, **Diviser les objets en dessous**, **Lignes et colonnes**, **Nettoyer** (points isolés, tracés vides) | ✗ | — |
| Pathfinder (11 opérations : réunion, soustraction, intersection, exclusion, division, découpage, fusion, recadrage, contour, soustraction arrière…) | ◐ | union, soustraction, intersection, division ✅ ; **exclusion, découpage, fusion, recadrage, contour, soustraction arrière** ✗ ; Répéter le dernier Pathfinder ✗ |
| Tracé transparent (tracé composé) Créer / Annuler | ◐ | à vérifier : les booléens produisent des tracés à trous, pas de commande dédiée |
| **Répétition** vivante (radiale, grille, miroir) *(module RepeatArts)* | ◐ | Dupliquer en puissance + miroir ponctuel ; pas d'objet répété vivant |
| **Fusion** (créer, options, remplacer la trajectoire, inverser) | ✗ | — |
| **Distorsion de l'enveloppe** (déformation prédéfinie, filet, objet du dessus) | ✗ | — |
| **Perspective** | ✗ | — |
| **Peinture dynamique** | ✗ | — |
| Vectorisation de l'image (options, préréglages, vectorisation dynamique) | ◐ | `mod-trace.js` (imagetracerjs) ; préréglages et ré-édition vivante limités |
| **Habillage de texte** | ✗ | — |
| Masque d'écrêtage (créer / libérer / modifier) | ✅ | `op_ecreter` / `op_desecreter` |
| Développer / Développer l'aspect / Convertir en forme | ◐ | objets vivants (`mod-vivants.js`), développement partiel |
| **Pixelliser** (objet → image), **Mosaïque d'objets** | ✗ | la persona Pixel existe, mais pas la commande objet → bitmap |
| **Mode isolation** | ◐ | seulement pour l'édition des symboles |
| Sélection › **Même** (fond, contour, épaisseur, opacité, mode, style, symbole), Inverser, **Enregistrer la sélection** | ◐ | Sélectionner par attribut ; Inverser vectoriel ✗ ; sélection enregistrée ✗ |
| Texte › **Chaînage** de cadres, **Titre ajusté**, **Casse** (MAJ / min / Titre / Phrase), **Ponctuation typographique**, **Alignement optique**, **Caractères masqués**, **Rechercher la police**, **Rechercher / Remplacer** | ✗ | débordement signalé, mais pas de chaînage |
| Texte › options du texte curviligne (Arc-en-ciel, Inclinaison, 3D, Escalier, Gravité) | ✗ | un seul mode |
| Texte › **Glyphes**, **OpenType** (ligatures, variantes), **Styles de caractère / paragraphe** | ✗ | — |
| Texte › Vectoriser | ✅ | par texte ou par glyphe |
| Correcteur orthographique | ⛔ | — |
| Affichage › **Tracés (Ctrl+Y)**, **Aperçu de la surimpression**, **Aperçu des pixels**, **Épreuve couleurs** | ✗ | — |
| Affichage › Repères (créer, verrouiller, libérer), règles, grille, magnétisme au point / à la grille, **repères commentés** | ◐ | repères, règles, grilles, aimant ✅ ; repères **commentés** (étiquettes « intersection », « centre ») ✗ |
| Affichage › **Vues enregistrées**, **Mode présentation**, modes d'écran | ✗ | — |

## 3. Effets (Effet › …, vivants)

| Chez eux | Chez nous | Détail |
|---|---|---|
| Esthétiques : Ombre portée, Lueur interne / externe | ✅ | `mod-effets.js` EFFETS (+ biseau, incrustation) |
| Esthétiques : **Contour progressif** (plume), **Arrondis** (en effet), **Gribouillage** | ◐ | Arrondir les coins en opération ✅ ; contour progressif et gribouillage ✗ |
| **Distorsion et transformation** : Distorsion libre, Contraction et dilatation, Rugosité, Transformation, Torsion, Zigzag | ✗ | — |
| **Déformation** : 15 styles (arc, arche, renflement, coquille, drapeau, onde, poisson, montée, œil de poisson, gonflement, compression, torsion…) | ✗ | — |
| **3D et matériaux** : Extrusion, Révolution, Gonflement, Rotation, matériaux, éclairage, rendu par lancer de rayons | ◐ | extrusion STL pour l'impression 3D seulement ; pas d'effet 3D vectoriel |
| Pathfinder en effet | ✗ | — |
| Tracé en effet : Contour de l'objet, Décalage, Vectoriser le contour | ◐ | Décalage vivant ✅ |
| **Pointes de flèche** | ✗ | aucun marqueur SVG |
| Convertir en forme (rectangle, arrondi, ellipse) | ✗ | — |
| Pixellisation en effet, **Galerie d'effets Photoshop** (≈ 50 filtres) | ✗ | — |
| Filtres SVG | ✅ | les effets sont des filtres SVG chaînés |
| Appliquer le dernier effet | ✗ | — |

## 4. Couleur, motifs, apparence

| Chez eux | Chez nous | Détail |
|---|---|---|
| Nuancier, couleurs globales, guide des couleurs (harmonies) | ✅ | `op_couleur_globale_*`, harmonies dans `mod-couleur.js` |
| **Recolorer l'illustration** (roue, liens d'harmonie, réassignation) | ✗ | — |
| Édition › Couleurs : Régler l'équilibre, Désaturer, Saturer, Inverser, Fusion horizontale / verticale / avant-arrière, Convertir CMJN / RVB / Niveaux de gris, Surimpression noire | ✗ | la persona Pixel a ses réglages, mais rien sur les objets vectoriels |
| Document CMJN / RVB, profils | ⛔ | — |
| **Créer un motif** (mode Motif : pavage grille / brique / hexagone, chevauchement, copies) | ◐ | 4 motifs fixes (hachures, points, damier, grille) |
| Apparence : plusieurs fonds et contours par objet, empilés | ◐ | à vérifier dans « Apparence + » (`mod-apparence2.js`) |
| Styles graphiques, symboles | ✅ | `op_style_*`, `op_symbole_*` |
| Transparence : modes de fusion, masque d'opacité | ✅ | 16 modes, masque de luminance |
| **Bibliothèques** de nuances, de symboles, de styles et de pinceaux | ✗ | — |

## 5. Fichiers, panneaux, automatisation

| Chez eux | Chez nous | Détail |
|---|---|---|
| **Ouvrir / importer SVG, PDF**, AI, EPS, DXF/DWG, CDR, CGM ; importer du texte DOCX / RTF | ✗ / ⛔ | images, GPX, presse-papiers seulement ; **import SVG et PDF** ✗ (AI/EPS ⛔) |
| Enregistrer AI / EPS | ⛔ | — |
| Exporter SVG, PDF, PNG, JPEG, DXF | ✅ | + WebP, STL / 3MF, traits de coupe et fond perdu |
| Exporter TIFF, PSD, **DWG**, JSON (Lottie ?) *(module)* | ✗ | — |
| Exporter pour écrans (plans de travail × échelles) | ✅ | tranches × résolutions |
| **Assemblage** (polices + liens), **Imprimer**, Info du fichier, **Versions** | ◐ | instantanés et historique ✅ ; assemblage et impression ✗ |
| Panneaux **Glyphes**, **Liens**, **Actions**, **Variables**, **Info**, **Attributs**, **Propriétés** contextuel, **Styles de caractère / paragraphe**, **Interactivité SVG**, **Aperçu des séparations** | ✗ | la route `/vector/links` existe, sans panneau |
| Actions, traitement par lots, scripts | ⛔ | — |
| **Commentaires** partagés *(module Commenting)* | ✗ | — |
| **Animation** *(module AnimationPanelUI)* | ◐ | « Envoyer vers › Animation » (Studio) |

## 6. IA (Firefly et assimilés)

| Chez eux | Chez nous | Détail |
|---|---|---|
| Générer des vecteurs (texte → illustration vectorielle) *(GenerateCore, FireflyService)* | ✅ | Illustration SVG par LLM (`mod-ia.js`), Calque IA G8 |
| **Recolorer par IA** (palette décrite en mots) *(DiffusionColoring)* | ✗ | — |
| **Retype** (identifier la police d'une image, rendre un texte vectorisé éditable) *(ReType)* | ✗ | — |
| **Turntable** (vues tournées d'un objet 2D) *(TurntableUI)* | ✗ | — |
| **Maquette / Mockup** (poser l'illustration sur une photo d'objet) | ✗ | à confirmer à l'écran |
| **Remplissage génératif de forme**, **motif génératif** | ✗ | à confirmer à l'écran |
| Segmentation d'image *(ImageSegmentation)* | ◐ | retrait du fond dans le Calque IA |

## Décisions proposées (à valider AVANT tout plan)

**D1 — Lot « Tracés » (fort rendement, peu de risque).** Les commandes suivantes sont pures géométrie, testables en
banc et très utilisées pour les cartes et les plateaux : Vectoriser le contour, Simplifier, Ajouter / Supprimer des
points, Moyenne, Nettoyer, Diviser les objets en dessous, Lignes et colonnes, et les 6 opérations Pathfinder qui
manquent (exclusion, découpage, fusion, recadrage, contour, soustraction arrière).

**D2 — Lot « Répéter et fusionner ».** Fusion (blend) entre deux formes, et Répétition vivante radiale / grille / miroir.
Les deux servent directement les ornements de cartes et les plateaux hexagonaux.

**D3 — Lot « Déformer ».** Enveloppe par déformation prédéfinie (les 15 styles), Distorsion libre, Rugosité, Zigzag,
Torsion, Contraction et dilatation, Pointes de flèche. Ce sont des effets vivants, dans la logique de `mod-vivants.js`.

**D4 — Lot « Interop ».** Import SVG d'abord, puis import PDF (première page, vectoriel). Sans cet import, aucune
ressource vectorielle externe n'entre dans le Vectorlab ; AI/EPS restent exclus.

**D5 — Lot « Couleur et motif ».** Recolorer l'illustration (réassignation des couleurs d'une sélection), éditeur de motif
(pavage grille / brique / hexagone), puis pinceaux artistique, dispersion et motif.

**À trancher par l'utilisateur** : rouvrir ou non des exclusions du 17/09 (filet de dégradé, imports AI/EPS) ; garder
hors périmètre les graphes, le symbolisme, la perspective et la peinture dynamique (coût élevé, usage faible pour les
cartes) — c'est la proposition par défaut.
