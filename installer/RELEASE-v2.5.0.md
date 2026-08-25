## 🐙 Deepotus Video Gen v2.5.0 — "Cardforge composable"

**Card Forge accepte une carte qui vient d'ailleurs, et laisse composer la
sienne comme dans un éditeur vectoriel.** Une 10e pièce importe un scan ou un
rendu et le mesure en local, gratuitement ; la mise en page passe à la
multi-sélection façon Figma ; la 3D gagne l'extrusion, les matériaux **verre**
et une occlusion enfin visible.

### Importer une carte, sans dépenser

- **Pièce « capture »** — dépôt recto/verso, aperçu, admission durcie sous
  concurrence, service par liste blanche.
- **Analyse locale (0 $)** — bordure, zones par grille 1,5 mm, fond,
  palette, échelle déduite du format, drapeau sur toute zone qui touche la
  bande de retrait. Les confiances sont **affichées chiffrées**, jamais
  présentées comme des certitudes.
- **Trois adoptions cloisonnées** — l'illustration, la bordure (famille la
  plus proche, écart affiché) et les zones (boîtes → slots), chacune en un
  seul pas d'annulation.
- **Détourage IA optionnel** — prix affiché avant, coalescence par jeu (12
  clics simultanés ne paient qu'une fois) et refus d'un détourage payé qui
  rendrait l'image quasi intacte.

### Composer comme dans Figma

Sélection en **lot** (clic+Maj, lasso, Échap), **6 alignements**, 2
distributions, 2 égalisations, réglages communs avec la valeur « mixte »,
rotation à la poignée (Maj = 15°), et des **guides d'aimantation**
objet-à-objet à 0,6 mm (voisins, fenêtre du cadre, centre de carte ; Alt
débraye, grille 0,25 mm en repli). Nouvelles primitives de formes — `rect`,
`ellipse`, `line`, `arrow` — gemme de rareté et ornements de coin libérés,
liseré de plaque sur toute zone.

### La 3D : extrusion, verre, occlusion

Nœud **`extrude`** et anneau-contour en objet (cadre ou Sceau, mm,
matériau assignable) ; **3 recettes de verre** (verre, verre dépoli,
translucide) écrites aux extensions glTF transmission / volume / ior /
specular ; **occlusion visible et débrayable** ; ondulation douce de la carte,
mesurée et avouée. Une carte importée part en 3D sans reconstruction, avec un
manifeste de capture qui n'emprunte jamais la preuve d'une autre.

### Illustrations « série », sous plafond dur

Une voie d'images générées à côté du vectoriel — jamais à sa place — avec
devis affiché avant, confirmation obligatoire, journal de dépense après chaque
case, et un **plafond qui ne bouge que sur ordre de l'utilisateur**. Le
vectoriel reste gratuit et complet : 18 sujets × 6 compositions × 12 palettes,
0 octet réseau.

### Fiabilité

Listing des jeux **×61** plus rapide, six 404 d'un jeu neuf éteints, trois
bugs antérieurs réparés (autosave, jeu fantôme, perte de sous-arbre), et
l'installeur allégé des sauvegardes internes du bundle (~13 Mo) qui n'avaient
rien à faire chez un acheteur.

### Connu, pas encore corrigé

- Le redimensionnement d'un **lot** de blocs n'est pas livré (le déplacement,
  l'alignement et la distribution le sont).
- La palette d'éléments des modèles personnels reste à moitié vide : quatre
  arbitrages produit sont posés, l'implémentation attend la décision.
- Le chapitre du guide illustré sur l'import et la composition n'est pas
  encore écrit.

### Installation

Téléchargez `DeepotusVideoGen-Setup-2.5.0.exe` et lancez-le. Aucun prérequis :
Python et ffmpeg sont embarqués. L'app s'installe dans
`%LOCALAPPDATA%\DeepotusVideoGen` et **vos données, clés et rendus sont
conservés** lors d'une mise à jour (ils vivent dans
`%LOCALAPPDATA%\DeepotusVideoGenData`).

Le détail technique complet est dans [`CHANGELOG.md`](../CHANGELOG.md).
