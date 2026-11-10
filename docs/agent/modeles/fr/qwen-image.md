---
famille: qwen-image
natures: [image]
ids: [qwen-image-3]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-multi-reference (scenario-labs/skills, MIT) ; registres image_providers, pricing et parallaxe
description: À utiliser quand on génère ou retouche une image avec Qwen Image (Alibaba) : Qwen Image 3, essais rapides et peu coûteux, pistes de composition avant un final sur un autre modèle, retouche à une ou plusieurs images de référence, découpe d'une peinture en calques (Qwen-Image-Layered).
---
## Aperçu

Qwen Image 3 génère une image depuis un texte, ou retouche à partir d'une ou plusieurs images de référence. Il est peu
coûteux (lire Membres). Il n'a ni seed, ni masque, ni champ négatif, ni fond
transparent, et sa pastille n'a ni palier de qualité ni rangée de résolution. Peu de retours publics existent sur ce
modèle : la fiche s'en tient aux règles d'image générales et au registre.

## Référence rapide

- [CHOIX] Le prendre pour explorer à bas prix : composition, cadrage, palette. Le final peut ensuite passer sur un
  modèle plus fidèle, avec l'image retenue en référence.
- [PROMPT] Séparer ce qui est imposé de ce que le modèle peut inventer : les détails inventés obéissent aussi aux
  contraintes (pas de lettres décoratives dans un visuel sans texte).
- [PROMPT] Plusieurs références : une ligne par image, « Image N = <rôle> only », puis ce qu'elle ne doit **pas**
  prêter. Le nombre de références envoyées se lit dans Membres.
- [MÉTHODE] Retouche : « change only X », puis la liste de ce qui reste. Tout ce qui n'est pas nommé peut changer.
- [PIÈGE] L'app envoie le format choisi à chaque appel, retouche comprise : la sortie suit ce format, pas le cadre de
  l'image d'entrée. Choisir le format de l'image d'entrée pour ne pas la recadrer.
- [PIÈGE] La taille rendue peut différer de la taille attendue. Relire la largeur et la hauteur du fichier.
- [PIÈGE] Le nombre d'images d'un appel répète le même prompt : il donne des variations, pas un jeu. Un jeu (angles,
  déclinaisons) = un appel par élément.
- [PIÈGE] Aucun fond transparent : l'image sort opaque et la réponse le dit. Demander « plain white background », puis
  détourer (fiche détourage).
- [PIÈGE] « Film still » ou un rapport écrit en prose cuisent des bandes noires. Ajouter « full frame edge to edge, no
  letterboxing ».
- [PIÈGE] Sans seed, une relance est une nouvelle image. Garder la sortie retenue.
- [CHOIX] Découpe en calques : Qwen-Image-Layered n'est pas dans la pastille. Il n'est servi que par l'onglet « Décor
  en parallaxe » du Tilelab.

## Exemple

Brief : « trois pistes rapides d'un décor de forêt pour mon jeu de plateforme, avant de choisir la direction ».

Prompt (un appel, plusieurs images) :

```
A side-scrolling platformer background: an old pine forest at dusk, layered depth from a misty far ridge to dark
trunks in the foreground, warm orange sky fading to violet. Painterly, soft edges, readable silhouettes. No
characters, no lettering anywhere. Full frame edge to edge.
```

Réglages : Qwen Image 3, format paysage, trois images dans le même appel : ce sont trois variations du même prompt,
c'est ce qu'on veut ici. La piste retenue sert de référence au final ; les vues suivantes d'un même niveau se font un
appel par vue.

## Erreurs fréquentes

- Demander « trois angles du même décor » en un appel : on obtient trois variations, pas trois angles.
- Écrire « transparent background » : la sortie est opaque.
- Retoucher une image carrée avec un format paysage choisi : la sortie est recadrée.
