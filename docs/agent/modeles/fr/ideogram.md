---
famille: ideogram
natures: [image]
ids: [ideogram-4.5]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-ideogram, scenario-text-overlay, scenario-brand-kit (scenario-labs/skills, MIT), registres image_providers et pricing
description: À utiliser quand on génère ou retouche une image avec Ideogram 4.5, que le texte dans l'image doit sortir juste (titre d'affiche, enseigne, couverture, packaging, nom de marque, slogan), qu'on hésite à couper la réécriture du prompt (magic prompt), qu'on choisit un palier de qualité, qu'on veut une retouche qui touche peu le reste ou un rendu peint (aquarelle, gouache, crayon), ou qu'une image Ideogram paraphrase la copie ou sort opaque.
---
## Aperçu

Ideogram 4.5 (via fal, clé fal) se spécialise dans la typographie : du texte lisible et juste dans l'image. Il fait le
texte vers image et la retouche. En retouche, la première image est celle qu'on modifie, les suivantes servent de
références. Il n'a pas de seed et ne rend pas de fond transparent dans l'app.

## Référence rapide

- [CHOIX] Le prendre quand le texte compte : affiche, titre, enseigne, couverture, étiquette. Il tient aussi mieux un
  médium peint (aquarelle, gouache, crayon) que les généralistes (relevé 2026-11).
- [CHOIX] En retouche, il modifie moins de pixels hors de la zone visée qu'un généraliste (relevé 2026-11, un
  échantillon) : bon choix pour changer un texte d'enseigne, ajouter ou retirer un objet.
- [CHOIX] Moins bon sur un produit photoréaliste, sur un personnage décrit en détail, et pour changer une matière ou
  une couleur précise : il dérive vers une teinte voisine et peut recolorer ce qui devait rester.
- [PROMPT] L'interrupteur « Réécriture du prompt » de la pastille est actif par défaut : le fournisseur réécrit le
  prompt et peut paraphraser la copie. Le COUPER dès qu'il y a un slogan, un titre ou un nom de marque exact. Le
  laisser pour un prompt court d'exploration.
- [PIÈGE] La réécriture ne vaut que pour le texte vers image. En retouche, l'interrupteur n'a pas d'effet : la
  copie doit être citée telle quelle dans le prompt.
- [PROMPT] Chaque copie : entre guillemets, avec sa place, sa graisse et son style (« headline "SPRING MARKET", top
  center, bold serif »). Peu de chaînes, courtes.
- [PROMPT] Couleurs d'une charte : citer les codes hex tels quels. Une couleur non nommée dérive d'un tir à l'autre.
- [PROMPT] Fond d'un futur carton incrusté : réserver une zone calme et sans texte (bande haute vide, tiers droit
  sombre) et la décrire comme telle.
- [COÛT] Rangée « Qualité » : low, medium, high. Défaut high, son palier le plus cher : high vaut plusieurs fois
  medium (relevé 2026-11). Brouillons en low ou medium, final en high. Le format ne change pas le prix (relevé
  2026-11).
- [PIÈGE] Sans seed, le final en high est un nouveau tirage : composition voisine de la piste low, pas identique.
  Prévoir deux finaux, ou garder la piste low si elle suffit.
- [PIÈGE] Les noms de paliers ne s'alignent pas entre familles : le high d'Ideogram est son plafond, pas le « high »
  d'une autre famille. Comparer à prix égal, dans Membres.
- [MÉTHODE] Retouche : l'image à modifier en premier, puis les références, chacune avec un rôle. Écrire « keep
  everything else exactly the same » puis la liste de ce qui doit rester.
- [PIÈGE] « transparent background » dans le prompt : l'image sort opaque et la réponse le dit. Demander « plain flat
  background » d'une couleur unie, puis détourer (fiche détourage).
- [CHOIX] Pas encore dans l'app : masque de retouche, garder la toile exacte de l'image source, résolution 2K,
  édition de précision, génération transparente native, texte en calques éditables, personnage par référence, seed.

## Exemple

Brief : « Une affiche portrait pour notre marché de printemps, style aquarelle, avec "MARCHÉ DE PRINTEMPS" en haut et
la date en bas. »

Prompt :

```
Watercolor poster illustration with soft paper texture. A lively open-air flower market under striped awnings,
baskets of tulips and daffodils, pastel spring light. Top center, large hand-lettered serif headline in deep green
reading "MARCHÉ DE PRINTEMPS". The bottom fifth stays as calm blank watercolor wash, with no text. No other text.
```

Réglages : Ideogram 4.5, format portrait, « Réécriture du prompt » coupée, qualité low pour deux ou trois brouillons,
puis le même prompt en high. On relit le titre lettre à lettre, accent compris. La date s'incruste ensuite dans la
bande vide (Templates) : un chiffre généré peut sortir faux.

## Erreurs fréquentes

- Laisser la réécriture active avec un slogan : il sort reformulé. La couper.
- Chercher la composition en high : chaque brouillon coûte le prix final.
- Demander un fond transparent : l'image sort opaque. Fond uni, puis détourage.
- Comparer deux familles « en high » comme si c'était le même palier : comparer les prix dans Membres.
- Mettre l'image à retoucher en deuxième position : c'est la première qui est modifiée.
