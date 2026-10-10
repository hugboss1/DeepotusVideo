# DeepotusVideo — catalogue d’icônes pour implémentation

**Version :** 2026-10-09 · **Périmètre :** 133 clés SVG autonomes · **Référence générée :** `DeepotusVideo-reference-planche-04.png`

## Statut des sources

La planche 04 est une **référence de direction artistique** pour 32 cases, repérées par ligne et colonne ci-dessous. Elle ne livre pas des fichiers vectoriels séparés et ne certifie pas une précision géométrique à 16 px. Les 133 SVG du paquet sont les fichiers actuellement importables ; ils ont été créés avant cette planche et doivent être revus graphiquement à sa lumière. Aucun tracé ne doit être annoncé comme « extrait » ou « vectorisé » de la planche.

Le Markdown fourni mentionne un inventaire JSON/CSV et `DESIGN.md §15`, mais ces fichiers ne figuraient pas parmi les pièces reçues. Il est donc impossible de garantir ici la correspondance avec chaque commande réelle de l’application ou les 27 tracés historiques. Le tableau donne un contrat de clés et de sens, à confronter aux composants du dépôt.

## Contrat de rendu

- Fichier : `dz-<famille>-<nom>.svg` ; symbole du même identifiant dans `dz-icons.svg`. `viewBox="0 0 24 24"`.
- Dessin : zone utile 20 × 20 ; sujet `currentColor` à opacité 1 ; support à 0,38 dans les SVG fournis. Aucun fond incorporé.
- Couleurs et tailles pilotées par l’interface ; vérifier sur `#13171c` à 16, 18 et 24 px, sur Windows, macOS et iPhone.
- Fournir un libellé accessible sur le bouton ou l’élément porteur. Une icône décorative reçoit `aria-hidden="true"` et `focusable="false"`. Le seul SVG ne doit pas porter le sens accessible.
- Les rotations du chevron sont définies par CSS selon le sens. L’état actif change la couleur CSS, jamais le fichier ni une couleur intégrée.

```html
<button type="button" aria-label="Importer">
  <svg class="dzi" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <use href="/shared/icons/dz-icons.svg#dz-action-importer"></use>
  </svg>
</button>
```

```css
.dzi { width: 1.25rem; height: 1.25rem; display: inline-block; fill: currentColor; flex: none; }
.dzi--16 { width: 16px; height: 16px; }
.dzi--24 { width: 24px; height: 24px; }
```

## Référence visuelle : planche 04

Les positions `L1C1` à `L4C8` désignent les cases de l’image, de gauche à droite. Certaines images générées sont des interprétations plus riches que le glyphe SVG correspondant : la planche sert à juger silhouette et poids visuel, tandis que la règle de dessin reste prioritaire. Exemple : `dz-action-generer` apparaît dans la dernière case sous forme d’image et étincelle, alors que son SVG courant est une étincelle seule ; **ne pas remplacer silencieusement le sens global de Générer par Générer une image**.

## Inventaire importable

La colonne « planche 04 » indique uniquement une référence visuelle ; `—` signifie qu’aucune case de cette planche ne représente la clé. Chaque fichier est relatif au dossier `deepotusvideo-icons/`.

### `nav` — Rail, écrans et espaces de travail (14)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-nav-accueil` | Accueil | — |
| `dz-nav-quick` | Quick | — |
| `dz-nav-studio` | Studio | — |
| `dz-nav-scheduler` | Scheduler | L4C3 |
| `dz-nav-card-forge` | Card forge | — |
| `dz-nav-vectorlab` | Vectorlab | — |
| `dz-nav-photolab` | Photolab | — |
| `dz-nav-spritelab` | Spritelab | — |
| `dz-nav-tilelab` | Tilelab | — |
| `dz-nav-lab3d` | Lab3d | — |
| `dz-nav-game-assets` | Game assets | — |
| `dz-nav-bibliotheque` | Bibliotheque | — |
| `dz-nav-export` | Export | — |
| `dz-nav-parametres` | Parametres | — |

### `cat` — Catégories, angles vifs (8)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-cat-personnage` | Personnage | — |
| `dz-cat-decor` | Decor | — |
| `dz-cat-objet` | Objet | — |
| `dz-cat-interface` | Interface | — |
| `dz-cat-texture` | Texture | — |
| `dz-cat-animation` | Animation | — |
| `dz-cat-audio` | Audio | — |
| `dz-cat-3d` | 3d | — |

### `action` — Actions et commandes transversales (26)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-action-ajouter` | Ajouter | — |
| `dz-action-fermer` | Fermer | — |
| `dz-action-supprimer` | Supprimer | — |
| `dz-action-dupliquer` | Dupliquer | — |
| `dz-action-copier` | Copier | — |
| `dz-action-coller` | Coller | — |
| `dz-action-importer` | Importer | — |
| `dz-action-exporter` | Exporter | — |
| `dz-action-telecharger` | Telecharger | — |
| `dz-action-envoyer-vers` | Envoyer vers | — |
| `dz-action-generer` | Generer | L4C8 |
| `dz-action-cout` | Cout | — |
| `dz-action-quick` | Quick | — |
| `dz-action-actualiser` | Actualiser | — |
| `dz-action-reinitialiser` | Reinitialiser | — |
| `dz-action-reessayer` | Reessayer | — |
| `dz-action-regenerer` | Regenerer | — |
| `dz-action-rotation` | Rotation | — |
| `dz-action-annuler` | Annuler | — |
| `dz-action-retablir` | Retablir | — |
| `dz-action-enregistrer` | Enregistrer | — |
| `dz-action-chercher` | Chercher | — |
| `dz-action-reglages` | Reglages | — |
| `dz-action-chevron` | Chevron | — |
| `dz-action-grouper` | Grouper | — |
| `dz-action-degrouper` | Degrouper | — |

### `etat` — États et propriétés (9)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-etat-visible` | Visible | L4C4 |
| `dz-etat-masque` | Masque | L4C5 |
| `dz-etat-verrouille` | Verrouille | L4C6 |
| `dz-etat-libre` | Libre | L4C7 |
| `dz-etat-succes` | Succes | — |
| `dz-etat-avertissement` | Avertissement | — |
| `dz-etat-erreur` | Erreur | — |
| `dz-etat-attente` | Attente | — |
| `dz-etat-information` | Information | — |

### `media` — Médias et transport (13)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-media-lecture` | Lecture | — |
| `dz-media-pause` | Pause | — |
| `dz-media-arret` | Arret | — |
| `dz-media-precedent` | Precedent | — |
| `dz-media-suivant` | Suivant | — |
| `dz-media-image` | Image | — |
| `dz-media-video` | Video | — |
| `dz-media-audio` | Audio | — |
| `dz-media-voix` | Voix | — |
| `dz-media-texte` | Texte | — |
| `dz-media-timeline` | Timeline | — |
| `dz-media-film` | Film | L4C1 |
| `dz-media-forme-onde` | Forme onde | L4C2 |

### `edit` — Édition, alignement et pile (19)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-edit-aligner-gauche` | Aligner gauche | — |
| `dz-edit-aligner-centre-h` | Aligner centre h | — |
| `dz-edit-aligner-droite` | Aligner droite | — |
| `dz-edit-aligner-haut` | Aligner haut | — |
| `dz-edit-aligner-centre-v` | Aligner centre v | — |
| `dz-edit-aligner-bas` | Aligner bas | — |
| `dz-edit-distribuer-h` | Distribuer horizontalement | — |
| `dz-edit-distribuer-v` | Distribuer verticalement | — |
| `dz-edit-pile-premier` | Mettre au premier plan | — |
| `dz-edit-pile-avancer` | Avancer d’un plan | — |
| `dz-edit-pile-reculer` | Reculer d’un plan | — |
| `dz-edit-pile-dernier` | Mettre à l’arrière-plan | — |
| `dz-edit-deplacer` | Deplacer | — |
| `dz-edit-redimensionner` | Redimensionner | — |
| `dz-edit-rogner` | Rogner | — |
| `dz-edit-fusionner` | Fusionner | — |
| `dz-edit-soustraire` | Soustraire | — |
| `dz-edit-intersection` | Intersection | — |
| `dz-edit-exclusion` | Exclusion | — |

### `outil-vec` — Outils vectoriels (9)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-outil-vec-selection` | Selection | — |
| `dz-outil-vec-noeud` | Noeud | — |
| `dz-outil-vec-plume` | Plume | — |
| `dz-outil-vec-courbe` | Courbe | — |
| `dz-outil-vec-rectangle` | Rectangle | — |
| `dz-outil-vec-ellipse` | Ellipse | — |
| `dz-outil-vec-polygone` | Polygone | — |
| `dz-outil-vec-texte` | Texte | — |
| `dz-outil-vec-pipette` | Pipette | — |

### `outil-px` — Outils pixel (8)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-outil-px-crayon` | Crayon | — |
| `dz-outil-px-pinceau` | Pinceau | — |
| `dz-outil-px-gomme` | Gomme | — |
| `dz-outil-px-pot` | Pot | — |
| `dz-outil-px-selection` | Selection | — |
| `dz-outil-px-degrade` | Degrade | — |
| `dz-outil-px-symetrie` | Symetrie | — |
| `dz-outil-px-tampon` | Tampon | — |

### `outil-photo` — Outils photo (7)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-outil-photo-recadrer` | Recadrer | — |
| `dz-outil-photo-correcteur` | Correcteur | L1C1 |
| `dz-outil-photo-clone` | Clone | L1C2 |
| `dz-outil-photo-selection-sujet` | Selection sujet | L1C3 |
| `dz-outil-photo-flou` | Flou | L1C4 |
| `dz-outil-photo-luminosite` | Luminosite | L1C5 |
| `dz-outil-photo-contraste` | Contraste | L1C6 |

### `calque` — Types de calques (7)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-calque-pixel` | Pixel | L1C7 |
| `dz-calque-vectoriel` | Vectoriel | L1C8 |
| `dz-calque-texte` | Texte | L2C1 |
| `dz-calque-masque` | Masque | L2C2 |
| `dz-calque-reglage` | Reglage | L2C3 |
| `dz-calque-effet` | Effet | L2C4 |
| `dz-calque-groupe` | Groupe | L2C5 |

### `lab3d` — Scène, matériaux et animation 3D (10)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-lab3d-cube` | Cube | L2C6 |
| `dz-lab3d-sphere` | Sphere | L2C7 |
| `dz-lab3d-camera` | Camera | L2C8 |
| `dz-lab3d-lumiere` | Lumiere | L3C1 |
| `dz-lab3d-materiau` | Materiau | L3C2 |
| `dz-lab3d-rig` | Rig | L3C3 |
| `dz-lab3d-os` | Os | L3C4 |
| `dz-lab3d-rotation` | Rotation | L3C5 |
| `dz-lab3d-extrusion` | Extrusion | L3C6 |
| `dz-lab3d-scene` | Scene | L3C7 |

### `marque` — Identité Deepotus (3)

| Clé SVG / symbole | Sens de commande proposé | Planche 04 |
| --- | --- | --- |
| `dz-marque-poulpe` | Poulpe | L3C8 |
| `dz-marque-favicon` | Favicon | — |
| `dz-marque-fenetre` | Icône de fenêtre | — |

## Séries à intégrer ensemble

| Série | Clés | Contrôle attendu |
| --- | --- | --- |
| Flux | `dz-action-importer`, `dz-action-exporter`, `dz-action-telecharger`, `dz-action-envoyer-vers` | Direction de la flèche et nature du réceptacle distinctes. |
| Visibilité | `dz-etat-visible`, `dz-etat-masque` | Même œil de base, barre d’occlusion sur masqué. |
| Verrou | `dz-etat-verrouille`, `dz-etat-libre` | Même boîtier, anse ouverte ou fermée. |
| Transport | `dz-media-lecture`, `dz-media-pause`, `dz-media-arret`, `dz-media-precedent`, `dz-media-suivant` | Silhouettes et dimensions homogènes. |
| Alignement | les six `dz-edit-aligner-*` | Guide discret commun, objets pleins. |
| Distribution | `dz-edit-distribuer-h`, `dz-edit-distribuer-v` | Espacements égaux sur les deux axes. |
| Pile | `dz-edit-pile-premier`, `dz-edit-pile-avancer`, `dz-edit-pile-reculer`, `dz-edit-pile-dernier` | Vérifier que les quatre états restent distincts à 16 px. |

## Correspondances et points à reprendre avant fusion

1. `dz-nav-spritelab` et `dz-nav-tilelab` partagent actuellement le même tracé. Ils représentent des écrans différents : dessiner deux silhouettes distinctes si ces entrées coexistent dans le rail.
2. `dz-marque-poulpe`, `dz-marque-favicon` et `dz-marque-fenetre` partagent actuellement la même silhouette. Traiter les deux derniers comme des exports/adaptations de marque, pas comme trois commandes différentes.
3. `dz-action-generer` est une étincelle générique. Ajouter une nouvelle clé spécifique `dz-action-generer-image` uniquement si l’interface exige de distinguer cette action ; la case L4C8 suggère un cadre d’image.
4. Les tracés `dz-edit-pile-*` et les six alignements doivent être éprouvés à 16 px sur le vrai fond. La génération d’image n’est pas une preuve de conformité pixel par pixel.
5. Ne pas remplacer automatiquement un pictogramme existant avant l’inventaire des usages réels (`source`, `écran`, `action`, `aria-label`). Le relevé Markdown n’intègre pas les lignes JSON annoncées.
6. La planche utilise des aplats gris et blancs sur le fond sombre. La livraison applicative reste `currentColor` avec deux opacités, et non les pixels de la planche.

## Procédure d’intégration

1. Copier les SVG et `dz-icons.svg` dans le répertoire d’assets partagé. Garder les noms du manifeste comme clés stables.
2. Ajouter une table `clé → libellé accessible → action` dans les composants, en résolvant les usages réels dans le dépôt.
3. Remplacer les emojis, Unicode et anciens glyphes écran par écran, sans affecter une même clé à deux sens différents.
4. Tester en contexte les paires et séries à 16, 18 et 24 px, au repos, actif et désactivé. Examiner les fonds sombres et les teintes de catégorie.
5. Comparer les 27 icônes de `DESIGN.md §15` lorsqu’il sera disponible, puis corriger les divergences avant fusion.

## Fichiers du paquet

- `dz-*.svg` : 133 fichiers autonomes.
- `dz-icons.svg` : sprite de 133 symboles.
- `manifest.json` : ordre et clés.
- `DeepotusVideo-reference-planche-04.png` : quatrième planche générée, référence visuelle.
- Ce document : critères et inventaire.
