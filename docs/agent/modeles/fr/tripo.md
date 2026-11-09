---
famille: tripo
natures: [modele3d]
ids: [tripo, tripo-h3.1, tripo-p2, tripo-p1]
voies: [fal]
releve: 2026-11-09
source: scenario-3d (scenario-labs/skills, MIT) ; registres asset3d_service, moteurs3d_neufs, pricing (asset3d)
description: À utiliser quand on transforme une image ou une description en modèle 3D avec Tripo : Tripo v2.5, Tripo H3.1 (v3.1), Tripo P2, Tripo Smart Mesh (P1) ; asset de jeu low-poly, budget de faces, maillage quad, quatre vues face dos profils, brouillon sans texture puis texture, PBR, delight, export GLB ou FBX vers Unity, Unreal, Godot ou Blender.
---
## Aperçu

Tripo reconstruit un maillage depuis une image, et pour P2 et Smart Mesh aussi depuis un texte. Quatre membres :
v2.5 (le plus complet en formats), H3.1 (vues multiples dans un ordre imposé), P2 (le plus récent, topologie quad,
quatre paliers de texture) et Smart Mesh (low-poly). On les lance depuis Game Assets › 3D › Créer ; les vues
multiples passent par le panneau « Vues d'abord » du 3D Studio ou par l'ancien formulaire 3D de Game Assets.

## Référence rapide

- [PROMPT] Image source : un seul sujet, centré, entier avec de la marge, sur fond uni, lumière douce et égale,
  sans ombre portée ni texte. Une ombre ou un reflet de la photo est cuit dans la texture.
- [PROMPT] Mode Texte (P2 et Smart Mesh) : une phrase anglaise qui nomme l'objet, sa matière, sa silhouette et son
  style. Mieux : générer d'abord une image concept validée, puis la convertir.
- [PROMPT] Le champ « Sujet » de Créer ne part pas chez Tripo en mode Image : il ne sert qu'au prompt des vues
  générées.
- [CHOIX] Vues multiples : seuls v2.5 et H3.1 les lisent (colonne vues des Membres). L'app range elle-même les
  vues dans l'ordre que H3.1 exige ; la vue de face est obligatoire.
- [PIÈGE] Profils inversés : « gauche » est la gauche du **personnage** (nez vers la gauche du cadre). Une paire
  inversée peut fusionner face et dos en une coque. Regarder les vues dans « Vues d'abord » avant de tirer.
- [CHOIX] Personnage à rigger : Tripo n'a pas de paramètre de pose. La T-pose ou l'A-pose passe par les vues
  générées : sans vues multiples, l'écran refuse la pose. P2 et Smart Mesh n'en ont aucune voie.
- [CHOIX] Topologie : P2 et Smart Mesh exposent `face_limit` (roue des réglages) ; P2 ajoute `quad`. Smart Mesh vise
  les accessoires et décors légers. Un nombre de quads n'est pas un nombre de triangles.
- [PIÈGE] glTF ne stocke que des triangles : le GLB d'un tir `quad` arrive triangulé. Créer ne télécharge que le
  GLB, et l'ancien formulaire, qui sait demander le FBX, n'envoie pas les réglages de la roue. Le maillage quad
  natif de P2 n'arrive donc pas encore dans l'app.
- [CHOIX] `delight` (P2, actif par défaut) retire l'éclairage de la photo. Ne le couper que si l'ombrage peint est
  voulu.
- [CHOIX] `auto_size` (P2) met le modèle à l'échelle réelle en mètres. Sans lui, la taille est normalisée.
- [MÉTHODE] Variante d'un même volume : garder l'image et `model_seed` (P2, Smart Mesh), changer le reste.
- [COÛT] Brouillon d'abord : texture coupée (`texture` décoché dans la roue de P2 et Smart Mesh, case Textures de
  l'ancien formulaire pour v2.5 et H3.1). On juge la silhouette, puis on paie la texture.
- [COÛT] Chez P2, `texture_quality` change le prix ; le prix des Membres est celui du palier par défaut. Couper la
  texture coupe aussi le PBR, sans quoi il serait facturé.
- [COÛT] Plusieurs modèles cochés, plusieurs images ou une quantité supérieure à un : un tir payé chacun. Lire le
  total estimé avant Générer.
- [MÉTHODE] Texture d'un brouillon validé : 3D Studio › Préparer › « Approuver la géométrie », puis l'écran Texture.
- [CHOIX] Pas encore dans l'app : graine de texture séparée, alignement de texture, `face_limit`, `quad` et
  géométrie détaillée de H3.1, palier HD de H3.1 et de v2.5 depuis un écran.
- [MÉTHODE] Hésiter entre deux membres : 3D Studio › « Comparer les moteurs » tire la même image et mesure triangles,
  arêtes ouvertes et étanchéité.

## Exemple

Brief : « un coffre au trésor low-poly pour mon jeu mobile, à importer dans Unity ».

Image concept validée, coffre de trois quarts sur fond gris clair uni, lumière plate. Créer, mode Image, Tripo P2,
roue des réglages : `texture` décoché, `face_limit` bas, `model_seed` fixé. Le brouillon se regarde : couvercle,
serrure, pieds. Validé, on relance avec `texture` coché, `texture_quality` standard et le même `model_seed`. Le GLB
part ensuite vers Unity par 3D Studio › Exporter.

Prompt du concept, dans le générateur d'image :

```
A low-poly wooden treasure chest with iron bands and a round padlock, three-quarter view from slightly above,
whole object in frame with margin, plain light grey background, soft even lighting, no cast shadow, no text.
```

## Erreurs fréquentes

- Donner une photo sur fond chargé : le décor entre dans le maillage ou dans la texture. Détourer d'abord, ou
  régénérer sur fond uni.
- Cocher T-pose sur P2 ou Smart Mesh : refusé, ces membres ne posent rien.
- Payer la texture avant d'avoir vu la silhouette.
- Croire que le GLB d'un tir quad garde ses quads.
