## 🐙 Deepotus Video Gen v2.3.0 — "Cardforge"

**Nouveau : un éditeur de cartes à jouer complet**, dans un 9ᵉ sous-onglet
**Card Forge** du hub Game Assets — de la face importée ou générée par IA
jusqu'à la planche prête pour l'imprimeur et l'export 3D façon NFT.

### Huit modules, sans configurer aucune clé

- **Face** — import local ou génération IA (clé fal.ai existante,
  optionnelle), cadrage et définition effective affichée en direct.
- **Cadres & bordures** — filets, coins, rareté, dos de carte, redessinés à
  n'importe quelle définition (jamais un PNG figé).
- **Typographie** — 23 polices déjà embarquées, encadré de règles qui
  s'adapte au texte au lieu de le tronquer en silence.
- **Import CSV** — colonnes vers champs, quantités, deck complet en un
  import, encodage détecté automatiquement (les accents ne cassent rien).
- **Volume** — aperçu 3D avec épaisseur, tranche et recto/verso réels.
- **Matières** — 8 canaux PBR (couleur, normale, rugosité, métallique,
  occlusion, hauteur, émissive, ORM), calculés localement.
- **Export impression** — 300 DPI réels, fond perdu **et** zone de sécurité,
  PDF avec `TrimBox`/`BleedBox` et traits de coupe vectoriels : ce qu'aucune
  des références gratuites du domaine ne fournit ensemble.
- **Export 3D** — `.glb` **et** `.gltf` autonome, avec le jeu de maps PBR
  complet.

Tout fonctionne sans clé API : Pillow et pypdf calculent chaque fichier en
local. Seule la génération de face par IA utilise votre clé fal.ai existante.

### Connu, pas encore corrigé

- Le canal d'émission des textures est produit et livré dans l'archive 3D,
  mais n'est câblé par aucun fichier de maillage : il n'apparaît pas encore
  dans un moteur de rendu.
- Le cadrage par défaut d'une illustration peut laisser une bonne partie de
  la face sous le cadre selon le gabarit choisi ; l'écran l'indique en
  pourcentage, sans encore proposer de correction en un clic.

### Installation

Téléchargez `DeepotusVideoGen-Setup-2.3.0.exe` et lancez-le. Aucun prérequis :
Python et ffmpeg sont embarqués. L'app s'installe dans
`%LOCALAPPDATA%\DeepotusVideoGen` et **vos données, clés et rendus sont
conservés** lors d'une mise à jour (ils vivent dans
`%LOCALAPPDATA%\DeepotusVideoGenData`).

Le détail technique complet est dans [`CHANGELOG.md`](../CHANGELOG.md).
