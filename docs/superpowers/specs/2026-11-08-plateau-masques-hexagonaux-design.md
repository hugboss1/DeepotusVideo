# Plateau, masques et illustrations hexagonaux — conception (08/11/2026)

Suite du chantier t421 (cartes hexagonales recto verso, PR #523, installée le 08/11). Ce document est la
référence pour le plan d'implémentation. Ce que l'utilisateur a dit est marqué comme tel ; le reste est
marqué *Choix de conception* et peut être corrigé à la relecture.

## Intention

L'utilisateur fabrique des jeux à base d'hexagones, sur deux échelles :

- **Petites cartes hexagonales.** Elles portent des sujets ou des paramètres. Posées côte à côte, elles montrent des
  liens qui font évoluer la main ou le statut d'un joueur pendant la partie.
- **Grandes tuiles.** Posées au fil de la partie, elles construisent un plateau différent à chaque fois, ce qui allonge
  la durée de vie du jeu.

Aujourd'hui, le Card Forge imprime et découpe un hexagone fait ailleurs, mais rien dans l'application ne
**fabrique** les hexagones. L'utilisateur veut un **parcours fluide et simple** pour :

1. partir d'une image (fond de plateau) dans le Photolab ou le Vectorlab, la découper selon une grille hexagonale à la
   taille choisie, et envoyer les tuiles dans un **jeu neuf** du Card Forge sous la dénomination « plateau » ;
2. poser ensuite sur ces tuiles des **masques** (cadre, valeurs, liens). Les masques sont dessinés dans le Photolab ou
   le Vectorlab, enregistrés comme **modèles** dans le Card Forge et **rééditables** dans leur lab ;
3. **générer par IA** des illustrations au format hexagonal : une par petite carte, et des fonds de plateau entiers.

## Ce que l'utilisateur a décidé

- Parcours en trois temps : découpe dans le lab, jeu « plateau » dans le Card Forge, masques empilés (maquette validée
  le 08/11, « c'est bon »).
- **Tuiles de bord : on ajuste la grille à l'image.** L'utilisateur choisit le nombre de tuiles (colonnes × rangées),
  et l'image est agrandie ou recadrée pour qu'aucune tuile ne soit coupée (option C de la maquette).
- Les masques viennent du Photolab ou du Vectorlab, s'enregistrent comme modèles dans le Card Forge et se rouvrent dans
  leur lab pour être modifiés.
- **Partage décor / contenu** : le lab dessine le décor (cadre, bandeau, pastilles vides) ; le Card Forge écrit dans ces
  emplacements le contenu propre à chaque tuile (nom, chiffre, symbole de lien), tiré du tableau du jeu.
- Les deux usages de l'IA sont voulus : illustration par petite carte, et fond de plateau entier.
- Un lien est un symbole imprimé, un chiffre ou une lettre (décidé en t421) ; les cartes sont découpées à la main ou
  par fichier CNC / laser (t421, déjà livré).
- Ordre des lots : 1 découpe du plateau, 2 masques, 3 IA. Le chantier rectangulaire différé (extraction de
  l'illustration, bordures importées, « carte suivante ») passe après.
- Aucune dépense IA sans accord explicite de l'utilisateur.

## Objectifs

- **G1.** Depuis le Photolab ou le Vectorlab, découper l'image ouverte en grille hexagonale ajustée, et créer en un
  clic un jeu « plateau » dans le Card Forge, sans toucher l'image d'origine.
- **G2.** Dessiner un masque hexagonal dans un lab, l'enregistrer comme modèle du Card Forge avec ses emplacements
  variables, l'appliquer à un jeu hexagonal, le rouvrir dans son lab pour le modifier.
- **G3.** Générer par IA des illustrations à la forme hexagonale, par carte depuis le tableau ou pour un fond de plateau,
  avec devis avant chaque lancement.

## Hors périmètre

- Vérifier les règles du jeu (si deux côtés « s'accordent »). L'application imprime les symboles ; le jeu se joue sur
  la table.
- Exports 3D, table virtuelle, livret, mockup, foil et vernis en hexagonal : ils restent refusés comme en t421.
- Familles de cadres dessinées du Card Forge (runic, arcane…) en hexagonal : le masque importé les remplace.
- Tailles hexagonales libres : on reste sur les 8 formats de t421.
- Le chantier rectangulaire différé.

## Anti-objectifs (échec même si « ça marche »)

- L'image d'origine, un masque déjà appliqué à un jeu, ou un jeu existant modifiés sans que l'utilisateur l'ait voulu.
- Une tuile coupée par le bord de l'image.
- Une dépense IA partie sans devis affiché ni confirmation.
- Un parcours qui oblige à exporter, renommer et réimporter à la main entre le lab et le Card Forge.
- Une phrase d'écran en dur, en une seule langue.

## Contraintes du dépôt

Celles d'`AGENTS.md`, rappelées ici parce qu'elles pèsent sur le plan :

- TDD et mutations ; preuve à l'écran en FR et en EN sur le backend de preuve 8799, jamais sur 8765.
- Chaînes dans les dictionnaires ; tout `HTTPException` neuf a son entrée L10 (`scripts/i18n_l10_traductions.json`,
  puis régénération de `backend/app/i18n/erreurs.json`).
- Les JS du Card Forge `core/mod-face/mod-frame/mod-print` et `tilelab/envoi.js` sont **générés** depuis les saisies
  `scripts/i18n_l7/*.py` et `scripts/i18n_l9/*.py` : on modifie la saisie, jamais le JS.
- Charte `dz-charte.css`, angles vifs.
- Fiches de l'assistant (catalogue, AGENT.md) pour chaque élément visible neuf.
- Noms d'images : garde unique `backend/app/services/noms.py` (accents acceptés).
- Le préfixe de fichier `plateau_` est **déjà pris** dans la Bibliothèque (plans de scène du Studio,
  `library_index.py` ~58) : les tuiles ne doivent pas l'utiliser.

## Ce qui existe et sert de base (relevé du 08/11)

- Géométrie : `services/cards/contract.py` (8 formats hex, `trim_mm` = rectangle englobant, fond perdu natif 3 mm,
  `CardGeom.contour_mm`) et `services/cards/hexa.py` (`contour_coupe_toile_mm`, `contour_toile_mm`, `contour_sur_mm`,
  `milieux_cotes_mm`, `gabarit_svg/png`).
- Création de jeu : `POST /api/cards/decks/depuis-images` (`services/cards/depuis_images.py`) sème un jeu pleine carte
  (`frame.family:"none"`, `type.slots:[]`, `data` = `nom/art/dos`) qui **référence** les images de la Bibliothèque sans
  les copier.
- Le document de jeu n'a **aucun champ de catégorie** ; `normalize_deck` (core.py ~180) jette toute clé inconnue.
- Emplacements : `doc.type.slots[]`, `box=[x,y,w,h]` en mm depuis le coin de coupe, `kind` texte / image / formes ; la
  Typographie est active en hexagonal. Les préréglages sont écrits en fractions de la zone sûre.
- Catalogue de modèles de jeu : `services/cards/models.py` (`/api/cards/models`). Il **ne garde aucune image**
  (`_frame_sans_import`).
- Photolab : menus générés depuis `frontend/photolab/donnees/menus.json` via les listes d'insertion de
  `mod-menus.js` ; enregistrement Bibliothèque avec lignée (`parent`, relation `retouche`) ; dialogues
  `ouvrirDialogue`.
- Vectorlab : grille hexagonale déjà présente (`mod-grille.js`, `hex_*`), générateur « Plateau » (`mod-plateau.js`),
  export PNG **sans lignée** (`mod-export.js`, `/api/images/upload`), documents rouverts par `?doc=`.
- Aucun découpeur image → tuiles n'existe (ni Photolab, ni Vectorlab, ni Tile Lab).
- IA : `POST /api/images/generate` (tailles nommées seulement : square_hd, portrait_4_3, landscape_16_9…), plafonds
  `services/plafonds.py` (catégorie `cartes`, confirmation `X-DZ-Plafond: confirme`), lot depuis le tableau du jeu
  `/api/cards/{did}/lot/{modeles,devis,generer}` (`services/cards/data.py`, mur de 10 $ par lot, 12 lignes par appel,
  `confirmer:true` obligatoire).

## Lot 1 — Découpe du plateau

### Parcours

1. Dans le Photolab (image ouverte) ou le Vectorlab (document ouvert) : commande **« Découper en hexagones… »**.
   *Choix de conception : Photolab, menu Image ; Vectorlab, menu Fichier › Exporter, à côté des exports par tranches.*
2. Un dialogue commun aux deux labs montre l'image avec la grille par-dessus et règle :
   - **taille de tuile** : un des 8 formats hex de t421 (taille + orientation pointe / plat) ;
   - **colonnes × rangées** ;
   - **cadrage** : l'image couvre toujours toute la grille (y compris le fond perdu de chaque tuile) ; l'utilisateur
     fait glisser et zoome l'image derrière la grille, jamais en dessous du zoom qui couvre tout ;
   - **résolution effective** affichée (points par pouce à l'impression) avec un avertissement sous 300 ppp ;
   - **nom du jeu**, par défaut « Plateau — <nom de l'image> » ;
   - **verso commun** facultatif (une image de la Bibliothèque).
3. **« Créer le jeu plateau »** : le Card Forge s'ouvre sur le jeu neuf.

### Géométrie de la grille

Grille d'hexagones jointifs (côtés communs), rangées décalées d'une demi-tuile (pointe en haut) ou colonnes décalées
(côté plat en haut). Le rectangle englobant de la grille, augmenté du fond perdu, fixe le rapport de cadrage. Chaque
tuile est rendue sur sa **toile complète** (rectangle `trim_mm` + fond perdu) : le fond perdu vient **des pixels voisins
de l'image**, pas d'un prolongement artificiel. Hors du contour de fond perdu hexagonal, la tuile est transparente.
*Choix de conception.*

*Choix de conception :* la découpe se fait **côté serveur** (Pillow), à partir d'une image de la Bibliothèque, pour une
seule implémentation partagée par les deux labs. Le Photolab enregistre d'abord le document dans la Bibliothèque (geste
existant, lignée `retouche`) ; le Vectorlab exporte son rendu à la résolution demandée, avec lignée (à ajouter).

### Route et données

- Nouvelle route `POST /api/cards/decks/plateau` :
  `{image, format, colonnes, rangees, cadrage:{zoom, x, y}, name?, verso_commun?}` → `{deck, tuiles:[noms]}`.
  Bornes à fixer par le plan (colonnes et rangées ≥ 1, total ≤ `IMAGES_MAX` = 500).
- Chaque tuile est écrite dans la Bibliothèque : nom `tuile_<base>_<did court>_r01c01.png` *(choix de conception,
  préfixe neuf ; voir les précisions plus bas)*,
  `parent` = l'image source, relation `plateau`, source `cardforge`.
- Le jeu est semé comme `depuis-images` (pleine carte, sans cadre), avec en plus :
  - un champ racine **`categorie`** (`"plateau"` ou absent), conservé par `normalize_deck`, renvoyé par l'index
    `GET /decks` et affiché en badge et filtre dans la galerie du Card Forge ;
  - colonnes de données `nom, art, dos, rang, colonne` ; `nom` = `plateau-01`, `plateau-02`… dans l'ordre de lecture
    (l'utilisateur a validé ce nommage sur la maquette).
- En cas d'échec en cours de découpe, rien ne reste : ni tuiles, ni jeu.

### Ce qui est prouvé à la fin du lot

Sur 8799, en FR et en EN : depuis le Photolab puis depuis le Vectorlab, une image coupée en 6 × 4 tuiles 90 mm pointe en
haut donne un jeu « plateau » de 24 cartes, l'image source inchangée (empreinte identique), les tuiles jointives quand
on les recompose (pas de pixel perdu ni dupliqué au joint), et l'impression nid d'abeilles de t421 fonctionne sur ce jeu.

## Lot 2 — Masques hexagonaux

### Ce qu'est un masque

Un **modèle de masque** = une image décor transparente (cadre, bandeau, pastilles vides) à la taille d'une toile
hexagonale + une liste d'**emplacements variables** (texte ou image) positionnés sur ce décor + un nom. On peut
**empiler** plusieurs masques sur un jeu (par exemple cadre, puis valeurs, puis liens), dans un ordre réglable.

### Dessiner un masque dans un lab

- Photolab et Vectorlab : **« Nouveau masque hexagonal… »** crée un document à la taille de la toile du format choisi
  (fond transparent), avec le gabarit de t421 (coupe, fond perdu, zone sûre) en **calque guide non exporté**.
- **« Enregistrer comme masque Card Forge »** : PNG transparent dans la Bibliothèque (relation `masque`) et entrée au
  catalogue des masques. Le document de travail du lab (`.pcraft` du Photolab, document du Vectorlab) reste lié au
  modèle pour la réédition.

### Emplacements variables (dans le Card Forge)

- Placés et réglés dans le Card Forge, sur le décor, avec les outils de la Typographie existants (`type.slots`).
- **Préréglages hexagonaux** fournis : « Liens » (six emplacements centrés sur `milieux_cotes_mm`, un par côté, chacun
  relié à une colonne `lien_1`…`lien_6`), « Bandeau valeur » (titre + chiffre), « Pastille centrale ».
  *Choix de conception sur la liste exacte.*
- Un emplacement de lien affiche soit un texte (lettre, chiffre, symbole Unicode), soit une image de la Bibliothèque si
  la cellule contient un nom d'image. *Choix de conception.*
- Le modèle enregistre ses emplacements **en fractions de la toile**, pour qu'un même masque serve aux 4 tailles d'une
  même orientation (le décor est redimensionné). *Choix de conception.*

### Catalogue, application, réédition

- Catalogue des masques séparé de celui des modèles de jeu, qui lui **garde ses fichiers image** : route
  `/api/cards/masques` (lister, enregistrer, supprimer), stockage sous le dossier des modèles. *Choix de conception.*
- **Appliquer** un masque à un jeu hexagonal **copie** son décor dans le jeu et y ajoute ses emplacements : un jeu
  existant ne change jamais quand le modèle change ensuite (supposition présentée à l'utilisateur, non contredite).
- **Modifier dans le Photolab / le Vectorlab** depuis le catalogue rouvre le document de travail. À l'enregistrement,
  l'utilisateur choisit **« Remplacer le modèle »** ou **« Enregistrer une variante »**. Un bouton « Mettre à jour depuis
  le modèle » dans le jeu permet de reprendre volontairement la nouvelle version.
- Le rendu des masques passe par toutes les sorties hexagonales existantes (aperçu, carte PNG, planche, PDF) ; le décor
  est rogné au contour de fond perdu comme le reste de la carte.
- Le panneau Cadre reste « pas encore en hexagonal » ; les masques ont leur propre entrée au rail (ou une section de la
  Typographie — au constructeur de choisir l'emplacement le plus lisible).

### Ce qui est prouvé à la fin du lot

Sur 8799, FR et EN : un masque cadre dessiné dans le Photolab, un masque liens dans le Vectorlab, tous deux enregistrés,
appliqués empilés au jeu « plateau » du lot 1 ; six symboles différents par tuile tirés du tableau ; réédition du cadre
en variante sans changer le jeu ; impression PDF correcte.

## Lot 3 — Illustrations IA au format hexagonal

- Les générateurs ne rendent que des rectangles (tailles nommées). L'application demande une image **un peu plus grande
  que la toile**, centrée sur le sujet, puis la recadre à la toile hexagonale (le fond perdu compris). Le prompt reçoit
  une consigne de composition : sujet centré, rien d'important dans les coins. *Choix de conception.*
- **Par carte** : le lot depuis le tableau existant (`/lot/devis`, `/lot/generer`) gagne le recadrage hexagonal quand le
  jeu est hexagonal ; taille demandée `square_hd` pour les deux orientations. *Choix de conception.* Murs, plafonds,
  devis et `confirmer:true` inchangés.
- **Fond de plateau** : dans le dialogue de découpe du lot 1, **« Générer le fond… »** (prompt, style) choisit la taille
  nommée la plus proche du rapport de la grille, montre le devis, génère après confirmation (catégorie de plafond
  `cartes`), puis place le résultat dans le dialogue comme image source. Si la résolution effective est sous 300 ppp,
  le dialogue le dit et propose l'agrandissement existant (`upscale`), avec son propre devis. *Choix de conception.*
- Toute image générée entre dans la Bibliothèque avec sa recette, comme aujourd'hui.

### Ce qui est prouvé à la fin du lot

Sans dépense : devis affiché, refus sans confirmation, recadrage hexagonal testé sur des images fournies par le test
(fournisseur simulé). **Une génération réelle n'a lieu qu'avec l'accord explicite de l'utilisateur dans la session**,
montant annoncé.

## Précisions après relecture (choix de conception)

Une relecture « constructeur » a relevé sept points ; tous sont tranchés ici, sans changer ce que l'utilisateur a
décidé. Chacun est un *choix de conception* corrigeable.

1. **Où naissent les emplacements d'un masque.** Le lab enregistre le décor seul : le modèle naît **sans
   emplacement**. On l'applique à un jeu hexagonal, on place ses emplacements dans le Card Forge (outils de la
   Typographie, préréglages hexagonaux), puis **« Enregistrer dans le modèle »** remonte décor et emplacements au
   catalogue (même choix « Remplacer » / « Variante »). Pas d'éditeur d'emplacements séparé dans le catalogue.
2. **Stockage dans le jeu.** Nouveau champ racine `masques: [{id, modele, version, src, ordre, alpha}]`, conservé par
   `normalize_deck`. Le décor est **copié dans le dossier du jeu** (`decks/{did}/masques/`), pas dans la Bibliothèque.
   Les emplacements restent dans `type.slots`, **marqués** du `id` du masque qui les a apportés : retirer ou mettre à
   jour un masque ne touche que ses propres emplacements ; ceux posés à la main ne sont jamais touchés.
3. **Image source de la découpe.** L'aperçu de la grille et la résolution se calculent dans le navigateur sur les
   pixels du document ouvert. Le passage par la Bibliothèque se fait **au clic sur « Créer »** :
   - Photolab : si le document est l'image de la Bibliothèque sans modification, elle sert telle quelle ; sinon un
     enregistrement Bibliothèque est fait (geste existant, lignée `retouche`).
   - Vectorlab : le document est rendu à la résolution qui donne 300 ppp sur la grille (borné à `COTE_MAX` 8192 px,
     avec avertissement si la borne fait passer sous 300 ppp), avec lignée vers le document.
   - Si la découpe échoue ensuite, cette image source reste dans la Bibliothèque : c'est un enregistrement légitime.
     Tuiles et jeu, eux, ne restent pas.
4. **Résolution des tuiles.** Le serveur rééchantillonne **une seule fois** l'image cadrée à la taille de la grille à
   la résolution du jeu (300 ppp par défaut), puis découpe sans autre rééchantillonnage. Chaque pixel de la zone utile
   appartient à la tuile dont le centre est le plus proche (les cellules d'un réseau hexagonal sont exactement ses
   hexagones) : la partition est exacte sans exiger un pas entier. Agrandir est accepté, avec l'avertissement sous
   300 ppp. Le test de joint vérifie la recomposition sur cette image rééchantillonnée.
5. **Même image découpée deux fois.** Le nom porte l'identifiant court du jeu : `tuile_<base>_<did court>_r01c01.png`.
   Rien n'est jamais écrasé.
6. **Taille de dessin d'un masque.** « Nouveau masque hexagonal » ouvre la toile de la **plus grande taille** de
   l'orientation choisie (90 mm, fond perdu compris, 300 ppp) ; le décor est réduit pour les tailles plus petites,
   jamais agrandi. Un masque Vectorlab peut être réexporté à la taille cible.
7. **Jeux concernés.** Les masques s'appliquent à **tout jeu hexagonal**, pas seulement aux jeux « plateau » : les
   petites cartes à liens en sont le premier usage. Les tests couvrent un jeu « plateau » et un jeu `depuis-images`.

## Laissé au constructeur

- Découpage des lots en tâches, noms internes, structure des modules front partagés entre les deux labs.
- Les bornes exactes (colonnes, rangées, zoom), les libellés finaux FR/EN dans le ton des écrans existants.
- La place des masques dans le rail du Card Forge.
- La forme du lien entre un modèle de masque et son document de travail dans chaque lab.
