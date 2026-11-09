---
famille: rodin
natures: [modele3d]
ids: [rodin, rodin-2.5]
voies: [fal]
releve: 2026-11-09
source: scenario-rodin, scenario-3d (scenario-labs/skills, MIT) ; registres asset3d_service, moteurs3d_neufs, pose3d, pricing (asset3d)
description: À utiliser quand on génère un modèle 3D avec Rodin (Hyper3D, Deemos) : Rodin et Rodin Gen-2.5 ; personnage à rigger en T-pose ou A-pose, plusieurs vues du même sujet, texte vers 3D, palier tier, maillage quad ou triangles (quality_mesh_option), matériau PBR, HighPack, textures HD, export GLB FBX OBJ STL USDZ.
---
## Aperçu

Rodin reconstruit un maillage depuis une ou plusieurs vues du même sujet ; Rodin 2.5 part aussi d'un texte. Avec Meshy,
c'est une des deux familles qui demandent une **pose de rig** au moteur lui-même : la T-pose ou l'A-pose marche
sans vues multiples. Cinq formats en sortie. Rodin 2.5 expose tous ses réglages dans la roue de Game Assets › 3D › Créer.

## Référence rapide

- [PROMPT] Image source : un sujet, centré, entier avec de la marge, fond uni, lumière égale sans ombre portée.
  Plusieurs images doivent montrer le **même** sujet sous d'autres angles, jamais un autre concept.
- [PROMPT] Rodin 2.5, mode Image : le champ « Sujet » part comme prompt. Vide, le modèle décrit lui-même les images.
  Une phrase anglaise courte qui nomme le sujet, la matière et ce qui ne se voit pas (« a quiver on the back »).
- [PROMPT] Mode Texte (2.5 seulement) : une phrase anglaise, un sujet, sa matière, sa silhouette, son style.
- [CHOIX] Personnage à rigger : choisir T-pose ou A-pose dans Créer. Corps entier, bras écartés du torse. Pour un
  objet, l'écran refuse la pose.
- [PIÈGE] Rodin 2.5 reçoit seulement « une pose de rig », sans dire laquelle. Pour forcer l'A-pose, l'écrire aussi
  dans le Sujet (« standing in an A-pose, arms angled down »). Le premier Rodin reçoit la phrase de pose tout seul.
- [CHOIX] Vues multiples : Créer envoie une image par tir (Multi-images = un modèle par image). Plusieurs vues du
  même sujet partent depuis « Vues d'abord » du 3D Studio, ou l'ancien formulaire 3D (case Vues multiples). Lire la
  colonne vues des Membres.
- [CHOIX] Rodin 2.5, `tier` : densité de géométrie, du plus léger au plus dense. `quality_mesh_option` choisit
  topologie et budget en une valeur (« 18K Quad », « 50K Triangle ») ; les budgets permis dépendent du `tier`,
  fal refuse les autres.
- [CHOIX] Rodin 2.5, `material` : PBR (défaut) pour un moteur de jeu, Shaded pour un rendu à éclairage peint, None
  pour la forme seule.
- [CHOIX] Rodin 2.5 : `hd_texture` affine la texture ; `highpack` ajoute textures plus fines et géométrie plus dense.
  Sur un maillage quad, HighPack multiplie fortement le nombre de faces (relevé 2026-11).
- [MÉTHODE] Variante d'un même sujet : même image, même `seed`, un seul réglage changé.
- [PIÈGE] Rodin 2.5, `geometry_file_format` : l'app range toujours le fichier principal sous le nom `model.glb`.
  Garder GLB et convertir dans 3D Studio › Exporter (à confirmer : un FBX choisi ici arriverait mal nommé).
- [COÛT] `highpack` est un supplément ajouté au devis. Le prix des Membres est celui des réglages par défaut.
- [COÛT] Le devis de Rodin 2.5 ne bouge pas avec `tier` ; un palier extrême peut être facturé davantage par fal
  (relevé 2026-11, à confirmer). Comparer au tableau des dépenses après un premier tir.
- [COÛT] Aucun brouillon sans texture (colonne brouillon). Essayer d'abord au `tier` bas, sans HighPack ; le final
  ensuite.
- [CHOIX] Pas encore dans l'app : palier de qualité du premier Rodin depuis un écran (il part en moyen), mode
  symétrique, mode créatif, découpe d'un maillage en pièces par Rodin.
- [MÉTHODE] Rig : après validation, 3D Studio › Préparer › « Approuver la géométrie », puis l'écran Rig.

## Exemple

Brief : « une archère stylisée à animer dans Unity, carquois dans le dos ».

Image : l'archère validée, de face, corps entier, en A-pose, fond gris uni, lumière plate. Créer, mode Image,
Rodin 2.5, pose A-pose. Roue des réglages : `tier` Gen-2.5-Low pour l'essai, `material` PBR, `quality_mesh_option`
« 18K Quad », `seed` fixé, HighPack non. Sujet :

```
A stylized female archer standing in an A-pose, arms straight and angled down away from the body, leather armor,
a quiver of arrows on her back.
```

La silhouette validée, même image et même `seed` au `tier` par défaut, puis le rig dans le 3D Studio.

## Erreurs fréquentes

- Cocher T-pose sur une épée ou un coffre : refus, ce n'est pas un personnage.
- Mélanger deux concepts dans les images d'un même tir : le maillage les fusionne.
- Activer HighPack sur un maillage quad destiné au temps réel : trop de faces.
- Juger la famille sur le premier Rodin : il part toujours au palier moyen. Rodin 2.5 règle sa densité.
