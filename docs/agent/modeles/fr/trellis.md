---
famille: trellis
natures: [modele3d]
ids: [trellis, triposr, trellis-2]
voies: [fal]
releve: 2026-11-09
source: scenario-3d (scenario-labs/skills, MIT) ; registres asset3d_service, moteurs3d_neufs, pricing (asset3d)
description: À utiliser quand on convertit une seule image en modèle 3D GLB avec TRELLIS (Microsoft) ou TripoSR : Trellis, TRELLIS 2, TripoSR ; accessoire ou objet compact depuis une image, essai rapide et bon marché d'un concept, résolution et taille de texture, décimation, remaillage, seed, GLB texturé direct sans réglage.
---
## Aperçu

Trois membres qui lisent **une seule** image et rendent un GLB texturé, sans mode texte ni pose :

- **TripoSR** : reconstruction rapide et la moins chère, pour juger un concept, pas pour livrer.
- **Trellis** : GLB texturé direct, sans aucun réglage.
- **TRELLIS 2** : le plus réglable (résolution de géométrie, taille de texture, décimation, remaillage, seed).

On les lance depuis Game Assets › 3D › Créer.

## Référence rapide

- [PROMPT] Image source : un objet compact, centré, entier avec de la marge, fond uni, lumière égale, sans ombre
  portée ni texte. Les faces cachées sont inventées : choisir l'angle de trois quarts qui en montre le plus.
- [PROMPT] Le champ « Sujet » de Créer ne part pas chez ces membres : seule l'image compte.
- [CHOIX] Accessoire, arme, meuble, rocher : cette famille suffit souvent, une image et un GLB texturé direct.
  Personnage à rigger ou objet dont le dos compte : un membre qui lit des vues multiples ou pose le sujet.
- [CHOIX] Aucun membre n'a de brouillon sans texture (colonne brouillon des Membres). Le brouillon de cette famille,
  c'est TripoSR : une forme vite vue, peu chère, puis le tir final sur un autre membre.
- [CHOIX] TRELLIS 2, `resolution` : la finesse de la géométrie. Le palier le plus bas pour un essai, le plus haut pour
  un objet à petits détails.
- [CHOIX] TRELLIS 2, `texture_size` : la taille des cartes. Une texture plus grande alourdit le fichier sans changer la
  forme : la garder modérée pour le jeu mobile ou le web.
- [CHOIX] TRELLIS 2, `decimation_target` : vise un nombre de faces, avec un plancher. Sous ce plancher, réduire après
  coup dans 3D Studio › Préparer (local, gratuit).
- [CHOIX] TRELLIS 2, `remesh` (actif par défaut) refait un maillage propre. Le couper seulement pour comparer avec le
  maillage brut.
- [MÉTHODE] Variante d'un même objet : même image, même `seed` (TRELLIS 2), un seul réglage changé à la fois.
- [PIÈGE] TRELLIS 2 n'a aucun réglage PBR : les cartes du GLB livré sont celles que rend le fournisseur, à vérifier
  (à confirmer au premier tir).
- [COÛT] TRELLIS 2 : le prix suit `resolution` ; celui des Membres est le palier par défaut. La taille de texture
  et la décimation ne changent pas le devis.
- [COÛT] Plusieurs membres cochés dans Créer = un tir payé chacun. Pour départager, 3D Studio › « Comparer les
  moteurs » mesure triangles, arêtes ouvertes et étanchéité sur la même image.
- [PIÈGE] Formats : GLB seul pour les trois. FBX, OBJ ou STL se font dans 3D Studio › Exporter.
- [CHOIX] Pas encore dans l'app : texte vers 3D, vues multiples, choix de format de sortie.

## Exemple

Brief : « un tonneau en bois cerclé pour mon décor de taverne, rendu propre mais léger ».

Image : tonneau seul, de trois quarts, légèrement en plongée, fond gris clair uni. Créer, mode Image, TripoSR pour
voir la forme à bas coût. La silhouette convient ; même image, TRELLIS 2, roue des réglages : `resolution` au palier
médian, `texture_size` modérée, `remesh` actif, `seed` fixé. Le GLB passe ensuite par 3D Studio › Préparer pour
tenir le budget de la scène.

Prompt de l'image concept, dans le générateur d'image :

```
A single oak barrel with two iron hoops, three-quarter view from slightly above, whole object in frame with margin,
plain light grey background, soft even lighting, no cast shadow, no text.
```

## Erreurs fréquentes

- Livrer le maillage de TripoSR comme asset final : c'est un essai.
- Donner une photo de groupe : les objets ressortent souvent soudés en un seul bloc. Un objet par image.
- Pousser `texture_size` au maximum pour un asset de jeu : fichier lourd, forme identique.
- Attendre une T-pose de cette famille : l'écran la refuse.
