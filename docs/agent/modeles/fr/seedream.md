---
famille: seedream
natures: [image]
ids: [seedream-5-pro]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-seedream, scenario-multi-reference (scenario-labs/skills, MIT) ; registres image_providers, pricing et parallaxe
description: À utiliser quand on génère ou retouche une image avec Seedream (ByteDance) : Seedream 5 Pro, affiche ou visuel avec un titre exact, texte dans une écriture non latine, retouche à plusieurs images de référence, remplacement d'un texte sur une image existante, coût d'une retouche à plusieurs références, découpe d'une peinture en calques (Layerize).
---
## Aperçu

Seedream 5 Pro génère une image depuis un texte, ou retouche à partir d'une ou plusieurs images de référence : sans
référence, c'est une génération ; avec, une retouche. Il tient bien un texte court et exact, y compris dans une
écriture non latine. Il n'a ni seed, ni masque, ni champ négatif, ni fond transparent. Sa pastille n'a ni palier de
qualité ni rangée de résolution.

## Référence rapide

- [PROMPT] Texte : citer chaque chaîne entre guillemets, dire sa place et son rang de taille (« the title "NIGHT
  TIDE", large, top third »). Peu d'éléments, sur une ou deux tailles.
- [PIÈGE] Les lettres sont dessinées, pas composées : un paragraphe ou un petit libellé sort en formes illisibles.
  Dates, crédits, prix et mentions passent en incrustation dès le départ.
- [MÉTHODE] Mot déformé : relancer en épelant le mot lettre par lettre après la chaîne citée. S'il résiste, le poser
  en incrustation.
- [PROMPT] Remplacer un texte sur une image existante : citer la nouvelle chaîne, épingler sa position, exiger la
  police, la taille et la couleur d'origine, et « everything else unchanged ».
- [PROMPT] Plusieurs références : une ligne par image, « Image N = <rôle> only », puis ce qu'elle ne doit **pas**
  prêter. Une référence prête tout ce qu'elle montre si on ne l'interdit pas.
- [PROMPT] Le rôle le plus souvent ignoré (souvent le style) passe en premier. Prêter concrètement (« copy its grainy
  risograph texture and two-ink look ») plutôt que « use its style ».
- [PROMPT] Séparer ce qui est imposé de ce que le modèle peut inventer : les détails inventés obéissent aussi aux
  contraintes (pas de lettres décoratives dans un visuel sans texte).
- [PIÈGE] L'app envoie le format choisi à chaque appel, retouche comprise : la sortie suit ce format, pas le cadre de
  l'image d'entrée. Choisir le format de l'image d'entrée pour une retouche qui ne doit pas recadrer.
- [PIÈGE] La taille rendue peut différer de la taille attendue. Relire la largeur et la hauteur du fichier avant de
  l'utiliser.
- [MÉTHODE] Taille exacte (bannière, icône) : générer au format le plus proche au-dessus, au même rapport, puis
  redimensionner. Agrandir ne rend pas de détail.
- [PIÈGE] Aucun fond transparent : l'image sort opaque et la réponse le dit. Retoucher une image détourée lui rend un
  fond plein ; détourer après la retouche (fiche détourage).
- [PIÈGE] Sans seed, une relance est une nouvelle image. Garder la sortie réussie ; pour une variante, ne changer que
  la dernière clause.
- [PIÈGE] « Film still » ou un rapport écrit en prose cuisent des bandes noires. Ajouter « full frame edge to edge, no
  letterboxing ».
- [MÉTHODE] Un jeu (angles, déclinaisons) = un appel par élément. Le nombre d'images d'un appel ne donne que des
  variations du même prompt.
- [COÛT] Chaque image d'entrée au-delà de la première ajoute un petit coût (relevé 2026-11). Le devis ne le compte
  pas : la facture d'une retouche à plusieurs références dépasse un peu le devis.
- [COÛT] Un seul prix, sans palier de brouillon : chaque essai coûte un final. Régler le texte et la composition sur
  une image avant d'en demander plusieurs.
- [CHOIX] Seedream 5 Pro rend plus lentement que les variantes rapides de la famille (relevé 2026-11), absentes de
  l'app. Le prendre pour un texte exact ou une retouche à références, pas pour des dizaines d'essais.
- [CHOIX] Découpe en calques : Seedream Layerize n'est pas dans la pastille. Il n'est servi que par l'onglet « Décor
  en parallaxe » du Tilelab, facturé par calque généré.
- [CHOIX] Pas encore dans l'app : taille en pixels exacts, jeu d'images liées en un seul appel, mode d'optimisation
  du prompt, retouche qui garde la transparence d'une référence, membres Lite, Flash et 4.5.

## Exemple

Brief : « une affiche verticale pour mon festival "NIGHT TIDE", dans le style de ma planche de risographie (jointe) ;
les dates et le lieu viendront après ».

Référence : image 1 = la planche de style. Prompt :

```
A vertical festival poster. Image 1 = style only: copy its grainy risograph texture, two-ink look in deep teal and
coral, slight misregistration. This is the most important job. Do not copy any shape, figure or word from it.
A huge stylized wave curls across the lower two thirds, a small moon above it. The title "NIGHT TIDE" in tall
condensed letters, large, centered in the top third. No other text. Leave a plain teal band empty along the bottom
for later text. Full frame edge to edge.
```

Réglages : Seedream 5 Pro, format portrait, une référence. Contrôle : le titre lettre par lettre, la bande du bas
vide. Les dates et le lieu s'incrustent ensuite (Templates ou Card Forge), jamais dans le prompt.

## Erreurs fréquentes

- Écrire les dates et le lieu dans le prompt : ils sortent mal orthographiés ou illisibles.
- Retoucher une photo carrée avec un format portrait choisi : la sortie est recadrée.
- Joindre une référence de style sans dire quoi ne pas copier : son sujet entre dans l'affiche.
- Compter sur le devis pour une retouche à cinq références : chaque image en plus se paie.
- Écrire « transparent background » : la sortie est opaque. Fond uni, puis détourage.
