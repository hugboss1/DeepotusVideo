## 🐙 Deepotus Video Gen v2.2.0 — "Catalogue de démarrage"

**Le logiciel est utilisable dès l'installation, sans aucune clé API.**

Jusqu'ici, l'écran **Son & VFX** ne proposait que des promesses : cinq faux
bruitages injouables, six vignettes VFX mortes annonçant « pas encore câblé —
$0.06 par élément », et une génération de musique sans backend. Un nouvel
utilisateur n'avait rien à essayer, seulement des tarifs.

### Ce que vous pouvez faire sans configurer quoi que ce soit

- **606 bruitages** classés en 8 familles (impacts, pas & matières, interface,
  numérique/rétro, science-fiction, objets, cartes, jingles). Écoutables dans
  l'app, ajoutés à la Bibliothèque en un clic — le Montage et le rendu les
  traitent ensuite comme n'importe quel son importé.
- **Génération de sprites de particules** : 12 effets prêts à l'emploi
  (explosion, fumée, éclat doré, étincelles, aura magique, départ de coup,
  poussière, traînée, braises, onde de choc, arcs électriques, cendres & neige)
  sur 80 textures. La simulation tourne **en local** : aucun appel réseau,
  aucun crédit, **0 $**. La sortie est une planche complète avec images, GIF
  d'aperçu, export ZIP et pack Unity.
- **5 séquences animées** assemblées en planche en un clic.
- Un onglet **« ✨ Démarrer »** ouvre désormais le Sprite Lab — les autres
  onglets sont vides tant qu'on n'a rien produit.

Tous ces éléments sont sous licence **Creative Commons Zero**
([Kenney](https://kenney.nl)) : usage commercial libre, aucune attribution
exigée. Les attributions sont livrées quand même dans
`backend/app/assets/starter/NOTICE.txt`.

### Génération de musique (clé fal.ai)

Quatre modèles sur la **même clé que la vidéo**, aucun compte supplémentaire :
**Lyria 3** (Google, 30 s, voix et paroles multilingues), **Stable Audio 2.5**
(durée libre jusqu'à ~190 s, pour couvrir une vidéo entière), **MiniMax Music
2.6** (vraie chanson : couplets, refrains, voix chantée ou instrumental) et
**CassetteAI** (jusqu'à 3 min, rapide et bon marché). Plus 8 ambiances qui
écrivent pour vous le genre, le tempo et l'instrumentation.

Chaque modèle affiche ce qu'il sait faire : un réglage qu'il ne gère pas est
retiré de la demande **et vous est signalé**, plutôt que d'être ignoré en
silence.

### Correctif d'interface

Le rail gauche de Son & VFX affichait la liste des **voix** quel que soit le
générateur sélectionné : choisir « VFX particules » laissait des comédiens à
l'écran. Le rail suit désormais la catégorie choisie, dans les deux sens.

### Installation

Téléchargez `DeepotusVideoGen-Setup-2.2.0.exe` et lancez-le. Aucun prérequis :
Python et ffmpeg sont embarqués. L'app s'installe dans
`%LOCALAPPDATA%\DeepotusVideoGen` et **vos données, clés et rendus sont
conservés** lors d'une mise à jour (ils vivent dans
`%LOCALAPPDATA%\DeepotusVideoGenData`).

Le détail technique complet est dans [`CHANGELOG.md`](../CHANGELOG.md).
