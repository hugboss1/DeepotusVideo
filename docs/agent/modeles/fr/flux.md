---
famille: flux
natures: [image]
ids: [flux, flux-3]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-consistency (scenario-labs/skills, MIT) ; registre image_providers, routes images
description: À utiliser quand on génère ou retouche une image avec FLUX (Black Forest Labs) : FLUX schnell rapide à seed, FLUX Kontext pour ses retouches, FLUX 3 en texte vers image ou retouche à plusieurs références ; quand on veut rejouer une recette à l'identique, noter un seed, faire une planche de l'Atelier DA, ou qu'une retouche FLUX refuse l'identité de l'espace ou sort au mauvais format.
---
## Aperçu

La famille a deux membres d'image. **FLUX rapide** (`flux`, FLUX schnell) fait du texte vers image et rend un
**seed** : c'est le seul générateur d'image de l'app qui rejoue une recette au pixel près. Ses retouches passent
par **FLUX Kontext**, qui ne prend qu'**une** image d'entrée. **FLUX 3** (`flux-3`) fait du texte vers image et de la
retouche à plusieurs références, sans seed. Aucun des deux ne rend de fond transparent.

## Référence rapide

- [CHOIX] FLUX rapide pour chercher vite et pour tout ce qui doit être rejoué à l'identique : planches et croquis
  de l'Atelier DA, recettes 🔁. C'est le générateur par défaut des planches quand aucun n'est choisi.
- [CHOIX] FLUX 3 pour une image finale plus soignée, ou pour une retouche qui doit garder l'identité de l'espace
  (mascotte, produits) : il reçoit plusieurs références.
- [MÉTHODE] Seed : il s'affiche avec 🔒 sur la planche. « Rejouer la recette verrouillée » renvoie le même prompt et
  le même seed, donc la même image. Changer une seule clause à la fois pour savoir laquelle a compté.
- [PIÈGE] Le seed ne rejoue qu'avec le même prompt, le même format et le même membre. Il ne transporte rien vers
  FLUX 3 ni vers un autre prompt.
- [PIÈGE] Avec un autre générateur que FLUX rapide, la recette garde les prompts et le chaînage, pas l'image au pixel.
  L'Atelier DA l'affiche dans sa note sous le choix du générateur.
- [PIÈGE] Retouche avec FLUX rapide = FLUX Kontext, une image seulement. Demander l'identité de l'espace est refusé
  avant toute dépense : passer à FLUX 3 ou à un autre modèle à références multiples.
- [PIÈGE] Une retouche FLUX (Kontext ou FLUX 3) sort au format demandé, pas à celui de l'image d'entrée ; sans
  format, elle sort en vertical. Choisir le format de l'image source avant le tir.
- [PROMPT] Retouche Kontext : une instruction courte, « change only X », puis ce qui doit rester (visage, tenue,
  cadrage). Kontext garde bien l'identité d'un sujet unique.
- [PROMPT] Phrases naturelles : sujet, action, décor, lumière, style. Aucun champ négatif dans l'app : écrire
  l'exclusion en positif (« plain white background », « no text »).
- [PIÈGE] Fond transparent : aucun membre n'a de champ de fond ; l'écrire dans le prompt donne un fond opaque. Demander
  « plain light grey background », puis détourer (fiche détourage).
- [COÛT] FLUX 3 rend une image par appel : n images = n appels, n fois facturés. Le devis les compte.
- [COÛT] Le devis chiffre une retouche Kontext au tarif de FLUX rapide, alors que Kontext est facturé au mégapixel,
  plusieurs fois plus cher (relevé 2026-11). La facture dépasse le devis.
- [COÛT] FLUX rapide est le moins cher de la famille : y chercher la composition, puis passer en FLUX 3 pour le
  final. Ce passage donne une autre image, sans seed commun.
- [CHOIX] FLUX 3 n'a ni rangée « Qualité » ni rangée « Résolution » dans la pastille : l'app fixe sa résolution.
  Pas encore dans l'app : choisir la résolution de FLUX 3, ou retenir Kontext comme modèle de retouche à part.
- [CHOIX] Le filtre de sécurité de fal est actif sur FLUX rapide en texte vers image.

## Exemple

Brief : « Une couverture d'épisode, un phare la nuit sous la pluie, style gravure ; je veux pouvoir la refaire plus
tard exactement pareille, puis une variante à l'aube. »

Prompt (FLUX rapide, format paysage) :

```
A lone lighthouse on a rocky cliff at night, heavy rain slanting across the beam of light, rough sea below.
Black and white engraving style, fine cross-hatching, high contrast. Full frame edge to edge, no text.
```

Réglages : FLUX rapide, format paysage, seed laissé libre au premier tir puis noté sur l'image retenue. Pour la
variante, même seed et même texte, une seule clause changée : « at dawn, pale light on the horizon » à la place de
« at night ». Pour le final, FLUX 3 avec le même prompt : c'est une nouvelle image, à valider comme telle.

## Erreurs fréquentes

- Demander à FLUX 3 de « reprendre le seed » de FLUX rapide : il n'a pas de seed, l'image change.
- Retoucher avec l'identité de l'espace en laissant FLUX rapide : refus. Choisir FLUX 3.
- Lancer une retouche sans choisir de format : l'image carrée ou horizontale ressort verticale.
- Écrire « transparent background » : fond opaque. Fond uni, puis détourage.
- Croire le devis d'une retouche Kontext : il est sous-estimé.
