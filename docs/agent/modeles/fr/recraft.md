---
famille: recraft
natures: [image]
ids: [recraft-4.1-vecteur]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-brand-kit (scenario-labs/skills, MIT), registres image_providers et pricing
description: À utiliser quand on veut une image VECTORIELLE (SVG) avec Recraft 4.1 vecteur : logo, icône, pictogramme, motif, illustration plate à recolorer ou agrandir sans perte au Vectorlab, quand on cherche pourquoi Recraft n'apparaît pas dans un écran d'image, ou quand on veut retoucher, décliner ou recolorer un SVG généré.
---
## Aperçu

Recraft 4.1 vecteur (via fal, clé fal) rend un SVG : des tracés éditables, pas des pixels. Il ne fait que le texte
vers image : pas de retouche, pas d'image de référence, pas de seed. Il n'est servi qu'aux demandes qui réclament un SVG :
aujourd'hui l'agent, aucun écran ne le propose encore (relevé 2026-11). Une demande raster est refusée avant tout tir ;
le SVG rendu s'ouvre ensuite au Vectorlab. Chaque image est un appel.

## Référence rapide

- [CHOIX] Le prendre pour ce qui doit rester net à toute taille et se recolorer : logo, icône, pictogramme, motif,
  illustration plate. Pas pour du photoréalisme, des textures ou des dégradés riches.
- [PROMPT] Décrire une géométrie plate et fermée, peu de couleurs, les codes hex de la charte cités tels quels.
  Écrire « flat vector illustration », pas « photo » ni « render ».
- [PROMPT] Dire ce qu'il faut éviter (dégradé maillé, étincelles, éclair décoratif, globe) : sinon le modèle reprend
  ses motifs par défaut.
- [PROMPT] Logo : une seule idée sur ce que fait la marque, réduite jusqu'à se lire en une couleur à la taille d'une
  icône d'onglet.
- [MÉTHODE] Trois candidats, chacun sur une méthode de construction différente (monogramme, verbe du produit en
  symbole, espace négatif à double lecture, géométrie sur grille), plutôt que trois tirs de la même idée.
- [MÉTHODE] Contrôle au Vectorlab : nom lu lettre à lettre, formes fermées et centrées, couleurs vérifiées sur les
  remplissages du SVG, pas sur l'aperçu. En cas d'échec, relancer avec un prompt resserré.
- [MÉTHODE] Variantes (monochrome, inversé, sur fond papier) : recolorer les remplissages au Vectorlab. Régénérer
  changerait aussi la géométrie.
- [PIÈGE] Aucune retouche par prompt : corriger les tracés au Vectorlab, ou relancer.
- [PIÈGE] Une « police » générée n'est qu'un dessin. Le wordmark se dessine une fois puis se réutilise ; le reste du
  texte se compose au Vectorlab avec une vraie police.
- [COÛT] Le fournisseur publie deux prix différents pour ce modèle ; le devis retient le plus haut (relevé 2026-10).
  La facture peut donc être plus basse que le devis.
- [CHOIX] Pas encore dans l'app : palette imposée par paramètre, style de référence, vectorisation d'une image raster.

## Exemple

Brief : « Un logo pour notre atelier de vélos, Roue Libre, deux couleurs de notre charte : #1F3A5F et #F2B134. »

Prompt :

```
Flat vector logo mark for a bicycle repair workshop. A single bicycle wheel whose spokes form a wrench, closed
geometric shapes, centered, generous empty margin. Two colors only: #1F3A5F and #F2B134. Wordmark below reading
"ROUE LIBRE" in a bold geometric sans serif. No gradients, no sparkles, no globe, no other text.
```

Réglages : Recraft 4.1 vecteur demandé par l'agent en sortie SVG, format carré, trois appels avec trois idées de construction
différentes (roue-clé, chaîne en boucle, monogramme R). On garde le meilleur, on vérifie les deux couleurs dans les
remplissages, puis on décline la version monochrome en recolorant.

## Erreurs fréquentes

- Le chercher dans un écran d'image raster (Library, Atelier DA) : il n'y est pas, c'est voulu.
- Joindre une image à retoucher : refusée. Retoucher les tracés au Vectorlab.
- Régénérer pour obtenir la version inversée : la forme change. Recolorer le SVG gardé.
- Laisser les couleurs implicites : elles dérivent d'un tir à l'autre. Citer les hex.
