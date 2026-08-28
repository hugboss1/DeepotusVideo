## 🐙 Deepotus Video Gen v2.6.0 — "Bibliothèque unifiée"

**La Bibliothèque devient le carrefour de l'application, et la carte part à
l'imprimante 3D.** Chaque asset connaît désormais sa provenance et s'« envoie
vers » dix surfaces ; un sélecteur commun remplace les pickers locaux ; le
service print3d écrit des dossiers STL/3MF aux millimètres réels ; et l'écran
suit le design du 26/08 jusqu'aux animations du menu.

### Bibliothèque : provenance & « Envoyer vers… »

- **Provenance de chaque asset** — la table `library_assets` note qui a
  produit quoi (fonction, provider) ; tous les producteurs y écrivent, et la
  réconciliation au démarrage rétro-indexe l'existant (998 assets au premier
  lancement).
- **Chips de tri** — « par fonction » sur les Images, « par provider » sur
  les Renders.
- **« Envoyer vers… »** sur chaque asset — dix cibles : Studio, Quick,
  Template, Bible, Montage, Cardforge, Sprites, Scheduler, impression 3D,
  planche. Chaque envoi réutilise le mécanisme de l'écran qui le possède —
  aucun doublon.
- **Sélecteur unifié** — 996 vignettes réelles, recherche, tri par date,
  greffé au nœud Image du Studio et aux écrans Quick ; import direct d'un
  fichier local ou d'un cadre Figma (jeton personnel dans Réglages, message
  clair sans jeton).

### Impression 3D réelle

- **Service print3d** (stdlib pure) : GLB → dossier STL + 3MF aux
  millimètres réels ; la garde du plateau (256 mm, Centauri Carbon 2)
  avertit sans interdire.
- **« → Impression 3D »** depuis la Forge 3D, le hub 3D et « Envoyer
  vers… » ; le .3mf s'ouvre dans votre slicer par association.
- **Relief vitrail par calque** (0 / 2 / 5 mm) côté Vectorlab.
- **Chapitre 20 du guide** (FR/EN, PDF 31 pages), capturé sur l'application
  réelle.

### Cardforge : écrans 02/03 et pont Vectorlab

- Le **bandeau** se règle à la souris sur le plan (plein manuel / pointillé
  auto, double-clic = auto), avec les bornes du backend en miroir.
- **Colonnes coulissantes** : chaque pièce dit combien de ses colonnes
  dorment, la scène absorbe la place libérée ; zoom d'aperçu.
- **Pont cartes ↔ Vectorlab** : des documents vectoriels ancrés au jeu,
  l'onglet Vectoriel du panneau Face (créer, ouvrir dans l'éditeur, poser
  l'export 2× comme illustration, supprimer) — le même fichier sert les
  décors de cadre. Nouvelle entrée « Vectorlab » au rail de navigation.

### Le design tient jusqu'au menu

- **Animations de repli du rail** (§4.4 du handoff) : libellés qui
  s'échappent en cascade (25 ms par ligne), rebond des icônes armé par le
  geste seul, icône immobile au pixel, largeur sur la courbe du design ;
  `prefers-reduced-motion` respecté.
- Le **livrable design** (design.md, toile de référence interactive) entre
  au dépôt.

### Architecture & réparations

- **Cards** : plus un réseau nu dans les pièces — les dehors `/api/vector`
  et `/api/print3d` passent par le CORE (routes et verbes figés, entrées
  validées).
- **Pipeline seedance** : un rendu payé ne se perd plus à l'étape d'assemblage
  (import manquant attrapé, ligne réparée rejouée sans nouvelle dépense) ;
  banc d'hygiène des imports sur tout le backend.

---

126 commits depuis v2.5.0 (25/08 → 28/08).

### Installation

Téléchargez `DeepotusVideoGen-Setup-2.6.0.exe` et lancez-le. Aucun prérequis :
Python et ffmpeg sont embarqués. L'app s'installe dans
`%LOCALAPPDATA%\DeepotusVideoGen` et **vos données, clés et rendus sont
conservés** lors d'une mise à jour (ils vivent dans
`%LOCALAPPDATA%\DeepotusVideoGenData`).

Le détail technique complet est dans [`CHANGELOG.md`](../CHANGELOG.md).
