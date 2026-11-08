# Cartes hexagonales recto verso dans le Card Forge — conception (07/11/2026)

Constat de départ : `docs/superpowers/specs/2026-11-05-workflow-cartes-constat.md`.

## Intention

L'utilisateur veut fabriquer des jeux de cartes hexagonales, recto et verso, à partir de ses propres fichiers de design.
Les cartes se posent côte à côte pendant la partie : elles créent des relations entre elles ou forment un plateau qui
grandit. Les cartes partent ensuite à la découpe, à la main ou sur une machine (CNC, laser).

**Décision de l'utilisateur :** un lien est un symbole, un chiffre ou une lettre imprimé dans le fichier de design.
L'application ne construit rien pour les liens.

**Décision de l'utilisateur :** ce chantier passe avant le parcours rectangulaire (lot, extraction, bordures, catalogue).

## Objectifs

1. Un format hexagonal dans le Card Forge : aperçu, zone sûre, fond perdu et trait de coupe suivent l'hexagone.
2. Créer un jeu depuis N fichiers de design, en un geste, sans cadre ni texte ajoutés.
3. Recto et verso : un verso commun, ou un verso propre à chaque carte.
4. Sortir une planche imprimable et un fichier de coupe qui tombent exactement au même endroit.
5. Donner à l'utilisateur un gabarit pour dessiner au bon format dans le Photolab ou le Vectorlab.
6. Corriger les noms accentués, qui bloquent tout parcours par image (53 cartes sur 93 dans le fichier réel).

## Hors périmètre

- Plateau d'essai, poser des tuiles à l'écran, vérification des raccords, règles du jeu.
- Volume 3D, texture de matière, export glTF, Forge 3D, exports de table virtuelle, livret et mockup en hexagonal.
- Paquets d'imprimeurs (MPC, The Game Crafter…) : la découpe se fait à la main ou à la machine.
- Foil et vernis en hexagonal.
- Cadres dessinés du Card Forge en hexagonal : le design porte tout.
- Génération par IA : aucune dépense dans ce chantier.
- Extraction d'illustrations, sélection multiple de la Bibliothèque, bordures importées, catalogue enrichi, « carte
  suivante » du Photolab, retour Vectorlab : second chantier, déjà cadré avec l'utilisateur.

## Ce qui ferait un échec, même si tout fonctionne

- Une seule carte rectangulaire change d'un pixel : aperçu, PDF ou planche. Les formats existants restent intacts.
- Le fichier de coupe et la planche ne tombent pas au même endroit.
- Les bords d'un recto et de son verso ne coïncident pas après retournement de la feuille.
- Un écran laisse croire qu'une sortie hors périmètre est valable en hexagonal, au lieu de le dire.
- Un fichier de l'utilisateur est modifié ou écrasé.

## Contraintes du dépôt

- TDD et mutations, preuve à l'écran dans les deux langues sur un backend de preuve, jamais sur le 8765.
- Aucune chaîne en dur : `dzT`, FR et EN. Charte `dz-charte.css`, angles vifs. Fiches de l'assistant (`connaissance-agent`).
- `CardGeom` est gelée : tout ajout passe par une propriété, jamais par un champ.
- La règle de géométrie de `contract.py` reste la seule source des pixels.
- La branche doit partir de `origin/main` à jour (`e9d4cc97` ou plus récent : le Photolab a changé de moteur).
- **Aucun patch du bundle n'est prévu** : tout tient dans `frontend/cardforge`, `frontend/shared` et le backend. Si un
  patch devient nécessaire, le maillon de queue est à revérifier sur `origin/main`.

## Comment ça marche

### Formats

Un hexagone régulier vit dans le rectangle qui l'englobe. `trim_mm` reste ce rectangle, et toile, fond perdu et rendu ne
changent donc pas de logique. `FORMATS` gagne une clé facultative `forme` ; son absence vaut « rect ».

Quatre tailles, mesurées d'un côté plat au côté opposé (50, 63,5, 75 et 90 mm), chacune en deux orientations : pointe en
haut ou côté plat en haut. Soit 8 formats. *Choix de conception : l'utilisateur n'a pas donné de taille.* Il n'y a pas de
taille libre dans ce chantier.

Pour une mesure `p` de côté plat à côté plat : pointe en haut, `trim_mm = (p, p × 2/√3)` ; côté plat en haut,
`trim_mm = (p × 2/√3, p)`.

`CardGeom` gagne des propriétés dérivées : `forme` et `contour_mm` (les six sommets, depuis le coin de coupe). Le
contour décalé donne le fond perdu (vers l'extérieur) et la zone sûre (vers l'intérieur), à distance perpendiculaire
aux côtés. `corner_mm` arrondit les sommets ; il vaut 0 par défaut pour un hexagone. *Choix de conception.*

Aux deux pointes, le fond perdu décalé dépasse la toile de 0,155 × fond perdu (0,46 mm pour 3 mm). Il est tronqué à la
toile : la règle de `contract.py` ne change pas, et il reste plus de 2,5 mm de fond perdu à la pointe. *Choix de conception.*

### Aperçu

Le rendu de la carte reste rectangulaire, puis un masque hexagonal est appliqué au trait de coupe. Les guides affichent
coupe, fond perdu et zone sûre hexagonaux. Hors du fond perdu, l'aperçu montre le fond de l'écran.

Les pièces hors périmètre (Cadre, Volume, Matières, Forge 3D, Édition, et foil/vernis dans Impression) restent visibles
au rail et disent qu'elles ne gèrent pas encore l'hexagone. Leurs routes de production refusent un deck hexagonal avec
une phrase claire (409), plutôt que de rendre un rectangle. La Typographie reste active : ses zones sont rectangulaires
mais utiles pour un texte posé sur le design.

Changer le format d'un deck existant entre rectangle et hexagone reste possible. Le cadre existant du deck n'est alors
plus dessiné, sans être effacé, et il revient si le deck repasse en rectangle.

### Créer un jeu depuis des images

Route `POST /api/cards/decks/depuis-images` :
`{name, format, images: [noms…], versos?: [noms…], verso_commun?: nom}` -> `{deck}`.

- Vérifie chaque image dans la Bibliothèque, sinon 404 nommant le fichier ; rien n'est créé si une image manque.
- Sème un deck pleine carte : `frame.family: "none"`, ornements éteints, `type.slots: []`, `type.seeded: true`,
  `face.seeded: true`, `face.fit: "cover"`. Prouvé à la main le 05/11 sur 6 cartes.
- Remplit la table `data` : colonnes `nom`, `art`, `dos` ; `map` vers `art` et `back`. Le deck reste un deck ordinaire :
  noms et ordre se reprennent dans Données.
- N'écrit jamais dans les images : l'original reste intact.
- Sert aussi les rectangles : un jeu de cartes finies se crée par la même route.

**Fond perdu.** L'image remplit toujours la toile. Le dialogue porte une case « Mon fichier inclut le fond perdu »,
cochée d'office si le rapport des images est celui de la toile (fichier fait sur le gabarit). Cochée : le deck garde le
fond perdu natif du format. Décochée : le deck naît à fond perdu 0, le fichier s'arrête à la coupe, et rien n'est rogné,
donc aucun symbole de lien placé au bord n'est perdu ; l'écran prévient alors qu'une découpe imprécise peut laisser un
liseré. Les cartes finies du lot réel sont dans ce second cas. *Choix de conception.*

Le premier format proposé est déduit du rapport des images. Un écart de rapport est signalé, carte par carte, avant la
création : pour les 4 cartes 977 × 1610 du lot réel, l'écran dit qu'elles seront recadrées.

### L'écran de création

Dans la galerie du Card Forge, une entrée « Nouveau jeu depuis des images » ouvre un dialogue :

1. nom et format ;
2. choix des images : grille de la Bibliothèque, recherche, filtre par projet, « tout », et import depuis l'ordinateur
   (fichiers multiples) ;
3. verso : aucun, une image commune, ou appariement automatique ;
4. récapitulatif (nombre de cartes, avertissements), puis création et ouverture du deck.

**Ordre :** tri naturel des noms de fichiers. **Appariement :** un fichier `<nom>_verso.<ext>` est le verso de
`<nom>_recto.<ext>` ou de `<nom>.<ext>` (FR) ; `_back` et `_front` valent de même. Un recto sans verso est signalé, sans
blocage, et sort blanc. *Choix de conception.*

**Verso.** Le verso commun est recopié dans la colonne `dos` de chaque ligne : il n'y a qu'un seul mécanisme, `card.back`,
et pas d'écran de verso à créer. Aujourd'hui `paintBack` sort aussitôt si `family === "none"` : il doit dessiner
`card.back` quel que soit le cadre, sans changer le rendu d'un deck rectangulaire qui a un cadre. L'aperçu du verso, le PDF
et `/card` passent tous par cette voie. *Choix de conception.* Le nom de carte est le nom de fichier sans extension, tiret bas remplacé par une espace.

### Gabarit

« Télécharger le gabarit », dans l'onglet Impression d'un deck hexagonal et dans le dialogue, livre un PNG transparent à
la taille de la toile et un SVG en millimètres, avec coupe, fond perdu et zone sûre. L'utilisateur l'ouvre dans le
Photolab ou le Vectorlab pour dessiner, et notamment pour placer ses symboles de liens au milieu des côtés. Le gabarit
marque le milieu de chaque côté par un repère discret. *Choix de conception.*

### Planche, coupe, recto verso

L'imposition gagne un mode nid d'abeilles pour les formats hexagonaux : rangées décalées d'une demi-cellule, au plus
serré permis par la gouttière et le fond perdu. La planche reste contrôlée par le même plan côté serveur et côté écran.
Le fond perdu de deux voisines ne doit jamais se chevaucher : la gouttière minimale vaut `2 × fond perdu`. En dessous,
un deck hexagonal est **refusé** avec une phrase claire. Les rectangles gardent leur comportement (avertissement
`gouttiere_courte`, fond perdu rogné) : il n'existe pas de rognage hexagonal. *Choix de conception.*

Le plan produit trois sorties, dans le même repère et à la même échelle :

- **PDF d'impression** : recto puis verso par page. Le verso est disposé en miroir horizontal pour un retournement sur
  le grand côté, selon la logique recto verso existante.
- **Fichier de coupe**, en SVG et en DXF, en millimètres, à l'échelle 1, une polyligne fermée par carte. Un calque de
  coupe et un calque de repères séparés. Un fichier par page, livrés ensemble dans un ZIP (`page-01.svg`, `page-01.dxf`…).
  La coupe se fait **recto dessus** : les fichiers suivent la page recto. *Choix de conception.* Le DXF réutilise l'écriture existante si elle convient (`build_dxf` dans
  `cards/gltf.py`, ou `mod-dxf.js`) ; le choix est au constructeur.
- **Coupe à la main** : un trait de coupe fin, facultatif, imprimé directement sur la planche.

Trois repères d'alignement, identiques sur la planche et dans le fichier de coupe, permettent de caler la machine sur la
feuille imprimée. Asymétriques, pour interdire un montage à l'envers. Ils sont imprimés sur le recto et, en miroir, sur
le verso, pour contrôler le calage. Les traits de coupe en croix des rectangles ne s'appliquent pas à l'hexagone.
Toutes les feuilles existantes sont admises (A4, Letter, A3).

**Routes existantes en hexagonal.** `/print/card` rend la carte en PNG, transparente hors du fond perdu. `/print/sheet` et
`/print/pdf` suivent le plan en nid d'abeilles. Refusées avec une phrase claire : `/print/pack`, le foil et le vernis,
`/gltf`, `/solid`, `/forge3d`, `/edition`. Les onglets Export 3D et Import restent visibles et disent qu'ils ne gèrent pas
encore l'hexagone.

### Noms accentués

`_NOM_IMAGE` et `_NOM_SERVI` (`photolab_routes.py`) et `NOM` (`frontend/shared/dz-envoi.js`, copie dans `dist/shared`)
acceptent les lettres Unicode. Restent refusés : séparateurs de dossier, caractères de contrôle, noms réservés Windows.
Les contrôles de confinement au dossier restent. Le renommage de la Bibliothèque ne remplace plus les accents par `_`
(`routes.py`, ligne 4191 au relevé). Un envoi refusé n'ouvre plus le lab en silence : il dit pourquoi. La base de nom
d'un fichier enregistré ne garde plus l'empreinte `entrees/` ni l'extension collée (`…-png.png`). Les autres gardes de
noms que ces parcours traversent sont à relever et corriger dans le même esprit.

## Fini quand

- Sur un backend de preuve, en FR et en EN : création d'un jeu hexagonal depuis au moins 3 designs tirés du zip réel,
  avec versos, visible dans le Card Forge, images d'origine identiques (empreintes vérifiées).
- Planche PDF et fichiers SVG et DXF produits ; superposition vérifiée par calcul sur les sommets et les repères, et le
  rendu regardé.
- Parcours rectangulaire de la tâche d'origine prouvé avec les vraies cartes : import, au moins 3 cartes rééditées dans
  le Photolab, dont des noms accentués, nouveau deck pleine carte, lot d'origine intact.
- Bancs verts dont la non-régression des formats rectangulaires, mutations, PR ouverte vers main.
- Tâche au suivi (artifact `9WVmPNinFLNN3Xxv2EHGht`, collection `taches`, prochain id libre à vérifier).
- Fusion et installation : seulement sur accord de l'utilisateur.

## Laissé au constructeur

- Identifiants exacts des formats et clés i18n.
- Découpe en tâches et commits, tant qu'il y a une seule PR.
- Valeurs de gouttière par défaut, position et forme précise des repères.
- Forme du refus (409) tant qu'elle reste une phrase claire dans les deux langues.
- Ajustement des bancs qui comptent 12 formats.
