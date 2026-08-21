## 🐙 Deepotus Video Gen v2.4.0 — "Cardforge universel"

**Card Forge devient un atelier complet** : la carte s'exporte **par couches**
prouvées au pixel, les couches se traitent dans un **graphe 3D** gratuit et
local, et le graphe s'ouvre aux **moteurs image→3D** — avec matières,
finitions holographiques et fusion des GLB moteurs dans l'artefact final.

### L'atelier 3D, sans configurer aucune clé

- **Export par couches** — six couches nommées par rôle + le composite,
  recto et verso, 300 DPI réels ; l'écran prouve l'empilement (0 px d'écart)
  avant de téléverser, le serveur contre-prouve en PIL et scelle un manifeste.
- **Graphe 3D gratuit** — traitements plan/relief (relief solide, fermé par
  construction), assemblage, artefact glTF/GLB propre dès l'écriture + STL
  binaire, metadata façon NFT — tout en local, 0 $.
- **Matières & finitions** — les matières de la boutique tuilées au pas
  physique (pack MR glTF), finitions argent/dorure **holographiques**
  (iridescence, clearcoat, anisotropie) relues dans les octets du GLB.
- **Fusion 3D** — le maillage d'un moteur est réindexé dans VOTRE artefact,
  ajusté à la boîte de sa couche ; STL mixte seulement si tout est fermé
  (refus motivé sinon, jamais un solide menteur).

### Les moteurs image→3D (optionnels, prix AVANT)

7 moteurs sur le nœud `mesh3d` : **tripo, hunyuan, trellis, rodin, triposr**
(fal, prix en $) et **Meshy 6/7 en API directe** (crédits — grille officielle
20/30/35, ultra +5 cr sur v7). Le coût s'affiche avant chaque lancement, le
job est suivi nœud par nœud, un poll ne tue jamais un job payé, et le
simulateur Meshy (`MESHY_MOCK=1`) permet de tout essayer sans dépenser un
crédit.

### Fluidité

Toutes les surfaces de manipulation à la souris du lab suivent la barre
§9.6 : un seul patch par frame d'animation, état final exact au relâché,
poignées 12 px, molette coalescée — le rectangle ne traîne plus derrière le
curseur.

### Connu, pas encore corrigé

- Le chatoiement holographique est prouvé dans les octets du GLB ; le juger
  à l'œil en tournant le viewer reste à faire.
- Le guide illustré s'arrête aux 8 modules : pas encore de chapitre Forge 3D.
- La rétention du double stockage des binaires Meshy reste à arbitrer.

### Installation

Téléchargez `DeepotusVideoGen-Setup-2.4.0.exe` et lancez-le. Aucun prérequis :
Python et ffmpeg sont embarqués. L'app s'installe dans
`%LOCALAPPDATA%\DeepotusVideoGen` et **vos données, clés et rendus sont
conservés** lors d'une mise à jour (ils vivent dans
`%LOCALAPPDATA%\DeepotusVideoGenData`).

Le détail technique complet est dans [`CHANGELOG.md`](../CHANGELOG.md).
