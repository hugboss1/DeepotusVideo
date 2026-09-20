# Vectorlab « classe Affinity » — conception et découpage

> Ordre utilisateur du 17/09/2026 (verbatim condensé) : « faire de VideoGen un
> best of class vendable au prix BYO keys de 65 € ou un peu moins ; se
> focaliser sur le Vectorlab : quasi un clone d'Affinity par le canvas ;
> créer ou éditer les images générées dans l'application ; surtout mieux
> éditer les cartes à imprimer ; préparer des impressions 3D de logos ou de
> petites extrusions ; exemple concret : travailler vectoriellement sur le
> plateau de jeu, joindre un quadrillage hexagonal, imprimer en 3D des tuiles
> de terrain pour le futur shop Deepotus / Rippled et pour les autres
> utilisateurs ; analyser complètement Affinity fonction par fonction et
> l'implémenter dans le Vectorlab. »

> Précision du 17/09 : « Affinity » désigne bien la suite Affinity de Canva
> (Vector, Pixel, Layout studios) ; l'inventaire du §2 en relève. Les
> facilités propres à l'application Canva elle-même (gabarits, IA en ligne)
> restent hors périmètre.

> **STATUT : CONCEPTION SOUMISE À VALIDATION. Aucun code.** Le chantier est
> trop vaste pour un seul plan : il est découpé en huit lots indépendants,
> chacun recevant son propre plan d'exécution (writing-plans) après accord
> sur ce document et sur l'ordre des lots.

---

## 1. État du Vectorlab au 17/09 (ce sur quoi on bâtit)

Trois chantiers livrés, déployés, prouvés (27/08 ×3, refonte 06/09) :
`frontend/vectorlab/` en vanilla ESM, **4 243 lignes** en 12 modules,
**banc qa node de 275 contrôles**, miroirs pytest `test_vector_docs`.

| Brique | Ce qui existe |
|---|---|
| Modèle | JSON versionné = vérité (`mod-doc.js`, pur), compilé vers SVG-DOM ; calques, objets `rect / ellipse / path / texte / groupe`, styles (fond, contour, épaisseur, pointillés, joint, opacité), dégradés linéaire/radial, guides, palette, unités px/mm/cm/in + dpi |
| Commandes | 45 `op_*` pures sous historique d'instantanés (100), essai sur clone (échec sans trace) |
| Outils | sélection, plume Bézier, rect, ellipse, ligne, nœuds, mesure, pipette, texte ; cotes vives ; grille carrée d'aimantation ; aligner/distribuer, miroir, dupliquer, rayon d'angle, ordre z, groupes |
| Booléens | union / soustraction / intersection / différence / division via martinez vendorisé (MIT) sur polygones aplatis |
| Couleur | sélecteur SV+teinte, RGB, CMJN naïf, hex, palette du document |
| Export | SVG serveur, PNG 1×/2×/4× (raster client), → Bible, → Impression 3D (extrusion prisme par calque, hauteurs mm, STL + 3MF, ouverture slicer) |
| Ponts | rail de la SPA (iframe), bibliothèque, chapitres de l'Atelier (décor / lumière / personnage), Cardforge (doc ancré `deck_id`, export 2× → illustration de carte, jauge DPI) |
| Vitrail | générateur de baie, motifs, fiche de style épinglée (replié par défaut) |

**Manques structurels** (mesurés au dépôt, pas supposés) :

- **aucun objet `image`** : impossible de poser une image générée dans un
  document — donc impossible de l'éditer, de la détourer, de la vectoriser ;
- **aucune couche raster** : pas de pinceau, pas de sélection pixel, pas
  d'ajustement ;
- **une seule grille**, carrée, d'aimantation seulement ; pas d'hexagonale,
  pas d'isométrique, aucune notion de tuile ;
- **pas de formes paramétriques** (polygone, étoile, hexagone, engrenage) ;
- **pas de masques, pas d'effets de calque, pas de modes de fusion, pas de
  symboles, pas de planches (artboards), pas de tranches d'export** ;
- **pas de texte vectorisé** : un texte s'exporte en `<text>`, il ne peut
  ni s'extruder en 3D ni se découper en booléen ;
- le pont Cartes est **à sens unique** (Vectorlab → carte) : on ne ramène
  pas la face d'une carte existante dans l'éditeur avec ses repères
  physiques (fond perdu, zone sûre).

---

## 2. Affinity fonction par fonction — inventaire et verdict

Source : inventaire fonctionnel d'Affinity Designer (persona Vecteur,
Pixel, Export) et du Vector Studio d'Affinity actuel, relu le 17/09.
Verdict par ligne : **✓ fait**, **~ partiel**, **✗ à faire** (avec le lot),
**— hors périmètre** (justifié).

### 2.1 Dessin vectoriel

| Fonction Affinity | Verdict | Lot |
|---|---|---|
| Plume avec changement de type de nœud en cours de tracé | ~ (plume + double-clic angle↔courbe) | B |
| Crayon main levée avec lissage et fermeture auto | ✗ | B |
| Pinceau vectoriel (trait à profil tête/corps/queue) | ✗ | F |
| Couteau (découpe formes, courbes, texte) | ✗ | B |
| Gomme vectorielle | ✗ | B |
| Formes intelligentes : polygone, étoile, engrenage, flèche, camembert, donut, nuage, cœur | ✗ | B |
| Coins arrondis absolus / pourcentage, outil Coin | ~ (rayon de rect seulement) | B |
| Carré/cercle parfaits par Maj | ✓ | — |
| Conversion primitive → courbes | ~ (implicite) | B |
| Spirale (linéaire, décroissante, Fibonacci) | ✗ | B |
| Outil Contour (décalage non destructif, offset) | ✗ | B |
| Outil Aire (aire et périmètre) | ~ (`aire_de` existe, pas d'outil) | B |
| Outil Mesure | ✓ | — |

### 2.2 Nœuds et courbes

| Fonction | Verdict | Lot |
|---|---|---|
| Sélection multi-nœuds (lasso, cadre) | ✗ (un nœud à la fois) | B |
| Aligner/distribuer des nœuds | ✗ | B |
| Transformer une sélection de nœuds | ✗ | B |
| Diviser une courbe, ajouter un nœud au milieu | ✗ | B |
| Supprimer un segment / lisser à la suppression | ~ | B |
| Joindre deux courbes, inverser le sens | ✗ | B |

### 2.3 Booléens

| Fonction | Verdict | Lot |
|---|---|---|
| Union, intersection, soustraction, division, combinaison | ✓ | — |
| Formes composées éditables (non destructif) | — : coût élevé, gain faible pour l'impression | — |
| Diviser dans les groupes | ~ | B |
| Trancher avec une courbe ouverte | ✗ (le couteau le couvre) | B |
| Shape Builder (clic pour fusionner/retirer des régions) | ✗ | B |

### 2.4 Transformations, sélection, alignement

| Fonction | Verdict | Lot |
|---|---|---|
| Panneau X/Y/L/H, rotation, formules (+50 %) | ~ (pas de formules ni d'inclinaison) | B |
| Rotation par poignée avec centre déplaçable, outil Point de transformation | ~ | B |
| Inclinaison (skew) | ✗ | B |
| Duplication puissance (répéter la transformation) | ✗ | B |
| Sélection par attribut (même fond, même contour, même type) | ✗ | B |
| Aligner sur sélection / page / marges / premier objet | ~ (sélection et page) | B |
| Distribuer avec écart fixe | ~ | B |

### 2.5 Grilles, guides, aimantation

| Fonction | Verdict | Lot |
|---|---|---|
| Règles en unité du document, guides | ✓ | — |
| Guides de marge et de fond perdu | ✗ | A |
| Grille carrée/rectangulaire subdivisée | ~ (pas de subdivision) | C |
| Grilles axonométriques (isométrique, 2 axes / 3 axes) | ✗ | C |
| Grille triangulaire | ✗ | C |
| **Grille hexagonale** (Affinity ne l'a qu'en triangulaire ; Deepotus l'exige) | ✗ | C |
| Origine de grille déplaçable, échelle par axe | ✗ | C |
| Aimantation aux objets (bords, centres, écarts), candidats | ✗ (grille + guides seulement) | C |
| Mode cube / grille alignée sur un objet | — | — |

### 2.6 Couleur, remplissages, contours

| Fonction | Verdict | Lot |
|---|---|---|
| RGB, hex, HSV, CMJN, niveaux de gris | ~ (CMJN naïf, gris absent) | F |
| LAB, profils ICC, Pantone | — : impression maison, pas d'offset | — |
| Couleurs globales (modifier une teinte partout) | ✗ | F |
| Palettes harmoniques (complémentaire, analogue) | ✗ | F |
| Dégradés linéaire / radial | ✓ | — |
| Dégradés elliptique / conique | ✗ | F |
| Dégradé de transparence | ✗ | F |
| Remplissage bitmap (motif image) | ✗ | A |
| Remplissage motif / hachures | ✗ | F |
| Multi-contours et multi-remplissages | ✗ | F |
| Remplissage par inondation vectoriel | ✗ | B |
| Mesh gradient | — : rendu SVG absent, coût disproportionné | — |

### 2.7 Calques, masques, effets

| Fonction | Verdict | Lot |
|---|---|---|
| Groupes imbriqués, verrou, visibilité, opacité de calque | ✓ | — |
| Masques de calque (raster) | ✗ | E |
| Écrêtage vectoriel (coller dans / insérer dans) | ✗ | F |
| Modes de fusion (34 chez Affinity ; les 16 du SVG suffisent) | ✗ | F |
| Ombre externe/interne, lueur, contour, biseau, incrustation | ✗ | F |
| Ajustements non destructifs (niveaux, courbes, HSL, N&B…) | ✗ | E |
| Vecteur et raster mêlés dans une pile | ✗ | E |

### 2.8 Texte

| Fonction | Verdict | Lot |
|---|---|---|
| Texte artistique | ✓ | — |
| Cadre de texte (paragraphes, justification, retraits) | ✗ | F |
| Texte sur chemin | ✗ | F |
| Styles de caractère / paragraphe | ✗ | F |
| Ligatures, OpenType avancé | — | — |
| **Vectorisation des glyphes** (texte → courbes) | ✗ | D |
| Correcteur orthographique | — | — |

### 2.9 Persona Pixel

| Fonction | Verdict | Lot |
|---|---|---|
| Calques pixel, image placée | ✗ | A (image), E (pixel) |
| Pinceaux à pression, buse, symétrie | ✗ (pinceau simple + gomme d'abord) | E |
| Sélections : rectangle, lasso, baguette, par couleur | ✗ | E |
| Affinage de sélection, croissance / contraction | ~ | E |
| Retouche : clonage, correcteur, flou, netteté | ✗ | E |
| **Vectorisation d'image (Image Trace)** | ✗ | A |
| Déformation mesh, perspective | — | — |

### 2.10 Symboles, contraintes, planches, styles, ressources

| Fonction | Verdict | Lot |
|---|---|---|
| Symboles avec instances synchronisées | ✗ | F |
| Contraintes UI | — : pas de cible UI | — |
| Planches multiples (artboards) dans un document | ✗ | C |
| Styles d'objet réutilisables | ✗ | F |
| Panneau Assets (bibliothèque de formes) | ~ (Bibliothèque unifiée existe) | C |
| Historique 8 000 pas, instantanés nommés | ~ (100 pas) | B |
| Sauvegarde automatique | ✗ | A |

### 2.11 Export

| Fonction | Verdict | Lot |
|---|---|---|
| SVG, PNG multi-résolution | ✓ | — |
| JPEG, WebP | ✗ | G |
| PDF (impression) | ✗ | G |
| DXF (découpe laser) | ✗ | G |
| Tranches, export par objet / planche / calque | ✗ | G |
| Export lot, suffixes @2x | ~ | G |
| Presets d'impression (fond perdu, traits de coupe) | ✗ | G |
| PSD, AI, EPS | — | — |
| **STL / 3MF** (Affinity ne l'a pas) | ✓, à étendre | D |

---

## 3. Décisions d'architecture (tranchées ici)

**D1 — Le moteur reste SVG-DOM pour le vecteur ; le raster entre par des
calques image adossés à Canvas 2D hors écran.** « Par le canvas » de l'ordre
se lit comme « sur la surface de dessin », pas comme une réécriture en
Canvas 2D. Réécrire 4 243 lignes prouvées par 275 contrôles pour gagner un
hit-testing maison serait une régression. Chaque calque raster est un objet
`image` (`href` vers un fichier PNG du document, jamais du base64 dans le
JSON) ; les opérations pixel travaillent sur un `OffscreenCanvas` et
réécrivent le PNG. L'historique d'instantanés JSON reste léger : le raster
a **son propre journal d'annulation par fichier** (`.pix<n>.png`, ×10,
patron des `.v<n>.json`).

**D2 — Le modèle-document s'étend par champs optionnels rétro-compatibles**
(patron `unites`/`palette` du 27/08) : `planches[]`, `grille {type, pas,
orientation, origine, sous}`, `symboles{}`, `styles{}`, `couleursGlobales{}`,
objets nouveaux `image`, `forme` (paramétrique avec `params` et `d`
recalculé), `instance`, `tuile`. `parserDoc` refuse tout champ malformé ;
un document v1 s'ouvre inchangé.

**D3 — Le plateau et les tuiles sont des objets de premier rang, pas une
grille dessinée.** Une `tuile` porte `{q, r}` (coordonnées axiales), un
`terrain` (clé de la fiche de terrains du document), une `hauteur_mm` et
une `forme` hex dérivée de la grille. Le générateur pose N tuiles ; on les
peint (terrain) au pinceau de tuiles ; le pont 3D les extrude une par une
ou en plateau assemblé.

**D4 — L'impression 3D s'appuie sur la chaîne existante** (`mod-extrude.js`
côté client pour le prisme, `print3d.py` pour STL/3MF/slicer) et gagne :
socle par tuile, relief par niveau de terrain, biseau et évidement pour les
logos, texte vectorisé par `opentype.js` (MIT, vendorisé) avant extrusion,
lot d'impression (un STL par tuile + un 3MF de plateau).

**D5 — Le pont Cartes devient bidirectionnel.** « Éditer cette face dans le
Vectorlab » crée un document au format physique du jeu (dpi du jeu), pose la
face actuelle en calque image verrouillé, dessine les guides de fond perdu
et de zone sûre, et « Poser 2× » (existant) ramène le résultat.

**D6 — Vectorisation par `imagetracerjs`** (MIT, vendorisé, pur JS) : une
image générée devient des chemins par aplats de couleur (nombre de
couleurs, lissage, seuil). C'est la porte « créer depuis une génération »
sans GPU ni API.

**D7 — Zéro dépendance payante, zéro appel API dans tout ce chantier.** Le
prix BYO keys l'impose : tout se vendorise en MIT (martinez, imagetracerjs,
opentype.js). Le PDF s'écrit côté backend avec la stdlib (patron
`print3d.py`), pas par une bibliothèque.

**D8 — Une surface, des personas.** Trois onglets en tête de l'éditeur :
**Vecteur**, **Pixel**, **Export**, chacun changeant la barre d'outils et le
panneau. Le vitrail reste un mode replié du persona Vecteur.

**D9 — Tout module nouveau est pur et bancable node d'abord** (RED avant
UI), l'UI ne fait que traduire, une commande par geste via `VL.executer`.
Chaque lot ajoute ses tests au banc `qa/` et ses miroirs pytest.

---

## 4. Les huit lots

Chaque lot = un spec court + un plan + une exécution TDD + preuve en réel +
déploiement, indépendamment livrable. Ordre proposé par valeur pour le
shop et pour l'utilisateur payant.

### Lot A — Images et cartes (P0)

Objet `image` (pose depuis la Bibliothèque, un fichier, le presse-papiers,
une génération) ; opacité, rognage rectangulaire, verrou ; guides de marge
et de fond perdu ; pont Cartes retour (D5) ; vectorisation (D6) avec aperçu
avant validation ; sauvegarde automatique (brouillon toutes les 30 s,
restauré à l'ouverture).
Preuve : une face de carte générée par le Cardforge s'ouvre dans le
Vectorlab, se vectorise en 8 couleurs, se retouche, se repose sur la carte,
la jauge DPI reste au 2×.

### Lot B — Géométrie et gestes de classe Affinity

Formes paramétriques (polygone, étoile, hexagone, engrenage, flèche,
donut, spirale) avec poignées de paramètres ; crayon lissé ; couteau ;
gomme vectorielle ; outil Coin et Contour (offset) ; nœuds multiples
(lasso, aligner, transformer, diviser, joindre, inverser) ; inclinaison,
pivot déplaçable, formules dans le panneau ; duplication puissance ;
sélection par attribut ; Shape Builder sur les booléens existants ;
historique 1 000 pas et instantanés nommés.

### Lot C — Grilles, plateau et planches

Grilles carrée subdivisée, isométrique, triangulaire, **hexagonale**
(pointe en haut / plat en haut, taille, origine, échelle) ; aimantation
aux objets (bords, centres, écarts) ; générateur de quadrillage hex
(rayon en tuiles ou rectangle, numérotation axiale optionnelle) ; objets
`tuile` et fiche de terrains (nom, couleur, hauteur mm, motif) ; pinceau
de tuiles ; planches multiples (un plateau, des cartes, des tuiles dans un
même document) ; panneau Assets branché sur la Bibliothèque.

### Lot D — Impression 3D : tuiles, logos, texte

Extrusion par tuile (socle + relief par terrain), assemblage plateau, lot
d'export (STL par tuile, 3MF de plateau, feuille de nomenclature) ; logos :
biseau, évidement, épaisseur de mur minimale contrôlée (règle des 256 et
garde existante) ; texte vectorisé (`opentype.js`) puis extrudable et
booléen ; aperçu 3D avant tir par le `<model-viewer>` déjà vendorisé.

### Lot E — Persona Pixel

Calques raster (D1) ; pinceau, gomme, seau ; sélections rectangle, lasso,
baguette, par couleur, croissance/contraction ; masque de calque ;
ajustements niveaux, courbes, HSL, N&B, seuil ; clonage et flou ; exporter
la sélection vers un objet vectoriel (pont vers D6).

### Lot F — Apparence avancée

Effets de calque par filtres SVG (ombre, lueur, biseau, contour,
incrustation) ; modes de fusion ; écrêtage vectoriel ; motifs et hachures ;
dégradés conique et de transparence ; multi-contours ; couleurs globales
et palettes harmoniques ; symboles et styles d'objet ; cadre de texte et
texte sur chemin ; pinceau vectoriel à profil.

### Lot G — Persona Export

Tranches (par objet, planche, calque, dessinées), formats JPEG / WebP /
PDF / DXF, multi-résolution en un tir, presets d'impression (fond perdu,
traits de coupe, marques de repérage), nommage automatique, export lot.

---

### Lot H — Cartes réelles : GPX, relief, plateau imprimable

> Ajout du 17/09 (précision utilisateur) : « importer une carte type GPX
> pour exploiter une carte réelle comme plateau de jeu, modifier l'aperçu
> 3D et envoyer vers une impression 3D ».

**Ce qu'un GPX contient et ne contient pas.** Un GPX porte des traces
(suites de points lat/lon avec altitude le long du tracé), des points
d'intérêt et une emprise. Il ne porte **aucun relief hors du tracé** : pour
un plateau en relief il faut un modèle numérique de terrain (MNT). Source
retenue : les tuiles d'altitude Terrarium d'AWS Open Data (publiques,
gratuites, sans clé, PNG où l'altitude se décode par
`(R·256 + G + B/256) − 32768`), mises en cache sur disque ; fond de carte
optionnel par tuiles OpenStreetMap (attribution obligatoire, cache, usage
modéré). Zéro clé, conforme au BYO keys ; sans réseau, le tracé seul
s'importe quand même.

**Workflow préconisé (cinq pas, chacun réversible).**

1. **Importer** un `.gpx` : parse pur (`mod-geo.js`), projection Mercator
   locale en mètres autour du centre de l'emprise, ajustement à la planche
   (échelle affichée « 1 : 25 000 », largeur réelle en km, largeur imprimée
   en mm). Naissent trois calques : `trace` (chemins), `points` (symboles,
   nom en texte), `emprise` (rectangle verrouillé). Le document reste en px
   à son dpi : l'échelle géographique est un champ optionnel
   `geo {centre, zoom, echelle}`.
2. **Habiller** : bouton « Fond de carte » (calque image OSM, lot A) et
   « Relief » (calque image de hauteurs, niveaux de gris 16 bits stockés
   PNG, plus ombrage calculé pour l'écran). Les courbes de niveau se
   vectorisent par marching squares (`mod-geo.js`, pur) à un pas choisi
   (10 m, 25 m…) : de vrais chemins, éditables, extrudables.
3. **Découper** : le quadrillage hex du lot C se pose sur la carte ; chaque
   tuile échantillonne le relief (moyenne ou médiane) et reçoit une
   `hauteur_mm` quantifiée par paliers (fiche de terrains : mer, plaine,
   colline, montagne, avec seuils d'altitude). L'utilisateur repeint les
   tuiles au pinceau si le résultat déplaît.
4. **Prévisualiser en 3D** : construction GLB côté backend
   (`gltf_builder.py` existant) à partir soit de la grille de hauteurs
   (plaque continue, tracé gravé ou en relief, exagération verticale
   réglable), soit des tuiles (lot D) ; affichage dans le `<model-viewer>`
   vendorisé ; réglages en direct : exagération, épaisseur du socle, pas de
   quantification, résolution du maillage.
5. **Imprimer** : la chaîne `print3d.py` existante écrit STL/3MF avec la
   garde de 256 mm ; mode plaque (un fichier) ou mode tuiles (un STL par
   tuile, un 3MF de plateau, nomenclature) ; découpe automatique d'une
   plaque plus grande que le plateau en dalles emboîtables.

**Implémentation.** `mod-geo.js` pur (GPX → points, projection, emprise,
courbes de niveau, échantillonnage hex) banc node RED ; `geo_service.py`
backend (tuiles Terrarium et OSM : téléchargement, cache
`DeepotusVideoGenData\cache\geo`, assemblage en une image, décodage des
hauteurs, rééchantillonnage) pytest avec tuiles synthétiques ;
`mod-relief.js` (grille de hauteurs → triangles avec socle et murs,
gravure du tracé) partage `stl_binaire` de `mod-extrude.js`. Dépend de A
(image), C (tuiles), D (extrusion par tuile). Se place **après D**.

### Complément au lot E — mode pixel-art « type Aseprite » vers le Tilelab

> Précision utilisateur du 17/09 : « utiliser le Vectorlab comme générateur
> de tuiles à envoyer vers le Tilelab : ne faudrait-il pas une fonction type
> Aseprite ? »

Oui. Le Tilelab (chantier 9e) consomme **une image de la Bibliothèque** et
lui applique seamless, pixel-art optionnel et pavage 3×3 avec score de
raccord. Le Vectorlab sait déjà exporter un PNG vers la Bibliothèque ; ce
qui manque est la **fabrication délibérée d'une tuile pixel-art**, que le
persona Pixel du lot E gagne sous la forme d'un mode dédié :

- document en unités de tuile (16, 32, 48, 64 px), zoom au plus proche
  voisin sans lissage, grille pixel visible, crayon 1 px, ligne et
  rectangle pixel-parfaits, seau contigu ou global, symétrie H/V ;
- **palette indexée** (8 à 64 entrées) : chaque pixel référence une entrée,
  changer l'entrée repeint la tuile ; import d'une palette depuis le
  document ou depuis une image ; réduction de couleurs à la vectorisation ;
- **pixelisation d'un vecteur** : rasteriser la planche à N px sans
  anticrénelage, puis quantifier sur la palette, pour dessiner la tuile en
  vecteur et la livrer en pixel-art ;
- **aperçu de raccord 3×3 en direct** (même métrique que le Tilelab), avec
  décalage de moitié pour voir la couture ;
- **feuille de tuiles** : plusieurs planches 32×32 exportées en une image
  atlas plus un JSON d'index (nom, position, tags de terrain) ;
- **cadres d'animation** avec pelure d'oignon et export en bande, pour le
  Spritelab ;
- « Envoyer vers Tilelab » et « Envoyer vers Spritelab » par le mécanisme
  « Envoyer vers… » de la Bibliothèque (source `vectorlab`, provenance
  tracée).

Le raster d'un pixel-art n'est jamais lissé : `image-rendering: pixelated`
à l'écran, et l'export PNG écrit les pixels tels quels, sans le rendu 2×/4×
des documents vectoriels.

## 5. Hors périmètre (assumé)

Mesh gradient, formes composées non destructives, LAB / ICC / Pantone,
contraintes UI, PSD / AI / EPS, correcteur orthographique, déformation
mesh, scripting intégré, intégration Canva. Chacun coûte plus qu'il ne
rapporte à un logiciel vendu 65 € dont la cible est l'impression maison,
les cartes et le plateau.

---

## 6. Tests et preuve

- Banc `qa/` node : chaque module pur reçoit son fichier `*.test.mjs`
  (RED d'abord) ; la règle des assertions négatives des dix bancs
  s'applique (état vide construit, négation démasquée).
- Miroirs pytest `test_vector_docs.py` pour tout champ nouveau du modèle et
  toute route ; `test_print3d.py` pour les tuiles et le lot.
- Preuve en réel par gestes pointer synthétiques et lecture DOM (patron des
  relevés du 27/08), mesure `offsetHeight` et non seule existence des nœuds.
- Déploiement vérifié par `git hash-object` (jamais sha256 d'octets).
