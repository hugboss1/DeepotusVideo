# Vectorlab — lot 3 « Calque modèle et pixel-art guidé » — conception (19/09/2026)

> Demande de l'utilisateur (19/09) : « utiliser un calque modèle d'une
> image générée ou importée, appliquer par-dessus la grille carrée aux
> différentes dimensions, générer un pixel-art par-dessus, l'exporter vers
> Spritelab, les tuiles ou l'impression 3D ; choisir et sauver les couleurs
> depuis des swatches ou par une pipette depuis le modèle ». Réponses aux
> questions de conception : **C** (cellule et taille cible liées, aperçu de
> la grille), **D** (pipette exacte / moyenne / dominante + pré-remplissage),
> **C** (swatches + couleurs utilisées + palette depuis le modèle), **D**
> (impression 3D : une pièce par couleur, une hauteur par couleur).
> Approche retenue : **le document connaît son modèle** (deux clés de
> `doc.pixelart`), validée le 19/09. Ce lot passe AVANT Tilelab 2.

## 1. Le modèle

Une image du document (posée depuis la Bibliothèque, un fichier ou une
génération — mécanismes existants de `mod-image`), verrouillée et atténuée
par ses réglages existants, désignée « modèle » depuis le panneau Pixel.

- `doc.pixelart.modele = { id: <id de l'objet image>, cellule: <entier ≥ 1> }`
  et `doc.pixelart.calque = <id de l'objet image pixel>` ; validés dans
  `_validerPixelart` (clés ajoutées à `_CLES_PIXELART`), posés par
  `op_pixelart`, retirés par `null`. Un seul modèle par document. Un
  modèle dont l'objet a disparu est ignoré (pas d'erreur), le panneau le dit.
- Le modèle n'est jamais modifié par ce lot : la pipette et le
  pré-remplissage le LISENT (tampon en cache, comme les cadres).

## 2. La grille et le calque pixel

Panneau Pixel, section « Calque pixel sur le modèle » :

- Deux champs liés : **cellule** (px du modèle par pixel d'art : 4 · 8 · 16 ·
  32 · 64, saisie libre acceptée) et **taille cible** (largeur en pixels
  d'art). `cellule_et_cible(nat, { cellule } | { cible })` (pure) :
  `cible_w = ceil(nat.w / cellule)`, `cible_h = ceil(nat.h / cellule)` ;
  depuis une cible : `cellule = max(1, round(nat.w / cible_w))` puis
  recalcul de la cible réelle. Changer l'un réécrit l'autre.
- **Aperçu** : tant que le modèle est désigné et qu'aucun calque pixel
  n'existe, l'overlay trace la grille des cellules sur le rectangle du
  modèle (lignes tous les `cellule` px natifs, projetées par le rognage /
  rectangle de l'objet, même patron que la grille pixel du persona). Le
  nombre de cellules est borné (≤ 65 536) : au-delà l'overlay ne trace
  que le cadre et le panneau dit « cellule trop petite pour l'aperçu ».
- **Créer le calque pixel** : une image transparente `cible_w × cible_h`
  déposée par la route existante, posée sur le rectangle exact du modèle
  (x, y, w, h identiques) dans un calque nommé « pixel » créé au-dessus du
  modèle, `doc.pixelart.calque` posé, `doc.pixelart.tuile` posé à la taille
  d'une tuile d'art si l'utilisateur le demande (case « tuile = … »), puis
  édition ouverte (`editer(id)`). Une commande, annulable.

## 3. La pipette depuis le modèle et le pré-remplissage

- **Mode de la pipette** dans la barre contextuelle (crayon, pinceau,
  seau) : `exact` · `moyenne` (défaut) · `dominante`, champ
  `pxPipetteMode` (mod-contexte, pur). La pipette (Alt+clic, R lot 2)
  échantillonne **le modèle** quand `doc.pixelart.modele` existe et que le
  calque édité est `doc.pixelart.calque` ; sinon elle échantillonne l'image
  éditée comme aujourd'hui.
- `echantillon_cellule(modele, rect, mode)` (pure, mod-pixelart) : `rect` =
  la cellule du modèle sous le pixel d'art ; `exact` = le pixel au centre
  de la cellule ; `moyenne` = moyenne RGB des pixels d'alpha > 0 (alpha
  moyen) ; `dominante` = la couleur la plus fréquente après réduction à 64
  niveaux par canal. Cellule entièrement transparente → `null` (la pipette
  ne change rien, le dit).
- Clic gauche → `etat.px.couleur` ; clic droit → **ajoute aux swatches**
  (`op_pixelart({ palette: [...palette, hex] })`, sans doublon).
- **Remplir depuis le modèle** : `remplir_depuis_modele(modele, cible_w,
  cible_h, cellule, mode, palette | null)` (pure) → un tampon
  `cible_w × cible_h` ; avec palette, chaque couleur est ramenée à la plus
  proche (`quantifier`). L'UI remplace le tampon du calque pixel et
  `commettre` (journal `.pix`, annulable) ; les pixels déjà peints sont
  ÉCRASÉS (dit dans le libellé : « remplit tout le calque »).

## 4. Swatches et couleurs utilisées

Panneau Pixel, section « Couleurs » (remplace la rangée palette actuelle) :

- **Swatches** = `doc.pixelart.palette` (existant, sauvé avec le document) :
  pastilles ordonnées ; clic = couleur courante ; clic droit = secondaire ;
  Alt+clic = retirer ; « + » ajoute la couleur courante ; **Palette depuis
  le modèle** = `palette_extraire(modele, N)` (existant, appliqué au
  modèle) ; « Extraire » existant reste sur le calque édité.
- **Couleurs utilisées** = `couleurs_utilisees(img, max = 64)` (pure) :
  les couleurs opaques du calque pixel triées par fréquence, recalculées
  après chaque commit ; pastilles cliquables ; « Tout mettre en swatches ».
- Le rangement en palettes nommées partagées Spritelab / Tilelab / Pixel
  reste au lot 4 (Tilelab 2 + palettes unifiées), qui lira
  `doc.pixelart.palette` tel quel.

## 5. Exports

- **Spritelab / Tilelab** : boutons existants « → Spritelab », « → Tilelab »
  (dépôt en Bibliothèque, provenance vectorlab). Un calque pixel de taille
  tuile part au Tilelab, un sprite au Spritelab ; « Envoyer vers » de la
  Bibliothèque reste le pont général.
- **Impression 3D — mode « Pixel-art »** du dialogue (`mod-impression`) :
  `pixels_vers_pieces(img, cellule_mm, hauteurs, { socle_mm })` (pure,
  mod-solide) : pour chaque couleur opaque, les pixels s'unissent en
  rectangles par lignes (fusion horizontale des runs, puis union des
  rectangles adjacents verticalement quand ils ont les mêmes bornes — pas
  de martinez pixel par pixel), chaque couleur = une pièce
  `{ nom: "px_<hex>", couleur, hauteur_mm, tris }` extrudée à SA hauteur ;
  socle optionnel = une pièce « socle » du rectangle entier. Table des
  hauteurs par couleur dans le dialogue, préremplie par la luminosité
  (`hauteurs_par_luminosite(couleurs, min_mm, max_mm)` pure : clair haut,
  sombre bas, bornes réglables), chaque ligne modifiable. Les pièces passent
  par la chaîne R12 (GLB coloré, 3MF par objet coloré, lot = un STL par
  couleur + nomenclature). L'aire de chaque pièce = nombre de pixels de la
  couleur × cellule_mm² (le banc le mesure).

## 6. Modules, tests, preuve

| Fichier | Ajouts |
|---|---|
| `mod-doc.js` | `pixelart.modele`, `pixelart.calque` (validation, `op_pixelart`) |
| `mod-pixelart.js` | `cellule_et_cible`, `echantillon_cellule`, `remplir_depuis_modele`, `couleurs_utilisees` |
| `mod-solide.js` | `pixels_vers_pieces`, `hauteurs_par_luminosite`, `rects_de_pixels` (fusion des runs) |
| `mod-contexte.js` | champ `pxPipetteMode` |
| `mod-pixelui.js` | section modèle / calque pixel, overlay de grille, pipette modèle, remplissage, couleurs |
| `mod-impression.js` | mode « Pixel-art », table des hauteurs |
| bancs | `pixelart.test`, `solide.test`, `pixel_doc.test`, `contexte.test`, `impression_ui.test` (RED d'abord) |

Preuve en réel (8799, 1400 × 900) : un modèle synthétique 64 × 64 à quatre
aplats connus → cellule 16 → calque 4 × 4 ; grille tracée (4 × 4 lignes) ;
pipette moyenne sur une cellule = l'aplat ; remplissage → 4 couleurs ;
swatches et couleurs utilisées = ces 4 couleurs ; mode Pixel-art de
l'impression → 4 pièces colorées d'aire 16 × cellule_mm² chacune, hauteurs
distinctes par luminosité, GLB à 4 matériaux ; « Un STL » / lot relus sur
disque. Aucun Python touché : aucune relance.

## 7. Place dans le chantier

Lot **3** (ce spec) → lot **4** Tilelab 2 + palettes unifiées → lot **5**
Playground, fonds, contour sombre. La conception
`2026-09-19-sorceress-sprite-suite-design.md` est amendée en conséquence.
