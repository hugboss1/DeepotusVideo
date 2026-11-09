---
famille: nano-banana
natures: [image]
ids: [nano-banana, nano-banana-pro, nano-banana-2.1]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-gemini-image, scenario-multi-reference, scenario-consistency, scenario-product-shots (scenario-labs/skills, MIT) ; registres image_providers et pricing
description: À utiliser quand on génère ou retouche une image avec Nano Banana (Gemini image de Google) : Nano Banana, Nano Banana Pro, Nano Banana 2.1, retouche par instruction, fusion de plusieurs images de référence, personnage ou produit à garder identique, photo produit fidèle, mot mal orthographié dans l'image, choix de la résolution 1K, 2K ou 4K, membre Nano Banana le moins cher.
---
## Aperçu

Nano Banana génère une image depuis un texte ou retouche des images par instruction, avec plusieurs références. Trois
membres : Nano Banana (le plus ancien), Nano Banana Pro (retouches complexes et fusion d'images) et Nano Banana 2.1.
Aucun membre n'a de seed, de masque, de champ négatif ni de fond transparent. Pro et 2.1 ont une rangée « Résolution »
dans la pastille de modèle.

## Référence rapide

- [PROMPT] Des phrases : sujet, décor, lumière, style. Une liste de mots séparés par des virgules rend moins bien.
- [PROMPT] Séparer ce qui est imposé de ce que le modèle peut inventer. Les détails inventés obéissent aussi aux
  contraintes (« no lettering anywhere » interdit aussi les runes décoratives).
- [PROMPT] Identité : dire en toutes lettres que les traits du visage restent identiques pendant que la pose, la
  lumière ou le décor changent.
- [PROMPT] Plusieurs références : une ligne par image, « Image N = <rôle> only », puis ce qu'elle ne doit **pas**
  prêter. Une image prête tout ce qu'elle montre si on ne l'interdit pas (le personnage d'une référence de style entre
  dans la scène).
- [PROMPT] Placer en premier le rôle le plus souvent ignoré (souvent le style), avec « This is the most important
  job ». Prêter concrètement : « copy its soft clay materials and warm bounce light », pas « use its style ».
- [PROMPT] Un seul sujet principal par image. Deux identités se partagent l'attention : les générer séparément, puis
  les réunir par une retouche.
- [PIÈGE] Sans masque, une retouche locale s'écrit en phrase : nommer la zone, le changement, et ce qui ne bouge pas.
- [PIÈGE] Sans seed, une relance donne une variation, jamais la même image. Garder la bonne sortie.
- [PIÈGE] Un mot qui sort déformé : ne pas relancer tout le visuel. Repasser l'image gardée en référence et épeler le
  mot lettre par lettre (« spelled L, U, M, E, N »), sans rien changer d'autre.
- [PIÈGE] Nano Banana et Pro : une retouche garde le cadre de l'image d'entrée, sauf si un format est demandé.
  Nano Banana 2.1 reçoit toujours le format de la requête : le prendre égal à celui de l'image d'entrée pour ne pas la
  recadrer.
- [PIÈGE] Aucun fond transparent : l'image sort opaque et la réponse le dit. Demander « plain white background », puis
  détourer (fiche détourage).
- [PIÈGE] « Film still » ou « cinematic » cuisent souvent des bandes noires. Ajouter « full frame edge to edge, no
  letterboxing ».
- [PROMPT] Peau visible : nommer la texture (« visible pores, fine peach fuzz »), sinon le rendu sort lissé.
- [MÉTHODE] Photo produit : partir de la vraie photo, jamais d'un texte. Prompt « preserve-first » : le produit
  exact de la référence, proportions et couleurs inchangées, le texte déjà présent sur l'étiquette cité mot pour mot,
  puis la surface, la lumière et l'ombre de contact.
- [MÉTHODE] Contrôle produit : relire l'étiquette lettre par lettre. Une étiquette qui a dérivé se relance depuis la
  photo source avec la clause resserrée, jamais depuis la sortie fautive.
- [MÉTHODE] Un jeu (angles, poses, scènes) = un appel par élément. Le nombre d'images d'un appel ne donne que des
  variations du même prompt.
- [MÉTHODE] Cohérence sur Pro et 2.1, qui prennent beaucoup de références : compléter les places avec des vues déjà
  validées du même personnage (face, profil, pied), propres et sans décor.
- [MÉTHODE] Fuite d'une référence : vérifier que son rôle est visible et que rien d'autre d'elle ne l'est. Corriger
  en resserrant sa ligne et en relançant, pas par une retouche de la sortie.
- [CHOIX] Nano Banana pour itérer à bas prix ; Pro pour les retouches complexes, la fusion d'images et la fidélité
  produit ; 2.1 pour l'usage courant à résolution réglable.
- [CHOIX] Le nombre de références de Membres est la limite de l'app. Pour Nano Banana (le premier), elle est plus
  basse que celle du fournisseur, par prudence.
- [COÛT] L'écart de prix est surtout **entre membres**, moins entre résolutions. Comparer le devis de deux membres
  avant une série.
- [COÛT] Pro : 2K coûte comme 1K, 4K double. Prendre 2K d'emblée pour un final ; 4K seulement pour une impression.
- [PIÈGE] Sans choix, Pro part en 1K : passer la rangée « Résolution » à 2K, même prix.
- [COÛT] Nano Banana 2.1 est facturé aux jetons : la résolution fait le prix, chaque référence s'ajoute en entrée, et
  le devis reste une estimation. Brouillon en 1K, final dans la résolution voulue.
- [CHOIX] Pas encore dans l'app : niveau de réflexion, recherche web du fournisseur, image tirée d'une vidéo, un
  membre plus léger et plus rapide, résolution sous 1K.

## Exemple

Brief : « ma tasse en céramique bleue (photo jointe) posée sur une table de terrasse au matin, dans l'ambiance de
mon moodboard, pour un post carré ».

Références : image 1 = la photo de la tasse ; image 2 = le moodboard. Prompt :

```
A photo for a square social post. Each reference picture has exactly one job.
Image 1 (the blue ceramic mug) = subject only. Keep the exact mug: shape, handle, glaze color and the small white
rim unchanged. Do not copy its studio background or lighting.
Image 2 (the moodboard) = mood and color palette only: warm early-morning light, soft cream and terracotta tones.
Do not copy any object, plant or furniture from it.
The mug stands on a weathered wooden café table on a terrace, low side light from the left, a soft contact shadow
falling right, shallow depth of field. Full frame edge to edge. No lettering anywhere.
```

Réglages : Nano Banana Pro, résolution 2K (même prix que 1K), format carré demandé, une image par appel. Contrôle :
la forme, l'anse et le liseré blanc de la tasse ; le décor ne reprend aucun objet du moodboard. Une variante d'angle
= un nouvel appel avec le même prompt et la même clause finale changée.

## Erreurs fréquentes

- Relancer pour retrouver « la même image en mieux » : sans seed, c'est une autre image.
- Écrire « transparent background » : la sortie est opaque. Fond uni, puis détourage.
- Donner deux références sans rôle : leurs traits se mélangent.
- Chaîner chaque retouche sur la précédente : le produit dérive. Revenir à la photo source.
