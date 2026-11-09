---
famille: gpt-image
natures: [image]
ids: [gpt-image-1, gpt-image-1-mini, gpt-image-2, gpt-image-2-fal, gpt-image-2.5-flare, gpt-image-2.5-sunburst, gpt-image-2.5-flare-fal, gpt-image-2.5-sunburst-fal]
voies: [openai, fal]
releve: 2026-11-09
source: scenario-image, scenario-gpt-image, scenario-multi-reference, scenario-text-overlay (scenario-labs/skills, MIT), registres image_providers et pricing
description: À utiliser quand on génère ou retouche une image avec GPT Image (GPT Image 2.5 Flare, 2.5 Sunburst, GPT Image 2, GPT Image 1, 1 mini), qu'on hésite entre la clé OpenAI et la clé fal, qu'on choisit un palier de qualité (brouillon low, final high, xhigh, max), qu'on veut un vrai fond transparent, plusieurs images de référence, du texte lisible sur un packaging ou une affiche, ou qu'une image GPT perd des consignes, sort opaque ou au mauvais cadre.
---
## Aperçu

GPT Image (OpenAI) génère et retouche par un seul prompt. L'app propose GPT Image 1 et 1 mini (clé OpenAI seulement),
GPT Image 2, et GPT Image 2.5 en deux variantes, Flare et Sunburst. GPT Image 2 et les deux 2.5 existent sur deux voies
jumelles : en direct (clé OpenAI) ou via fal (clé fal). C'est le même modèle, avec deux factures et des réglages un peu
différents. Aucun membre n'a de seed : chaque tir est une nouvelle image.

## Référence rapide

- [CHOIX] Flare est rapide et économique, d'une qualité voisine de GPT Image 2 : il sert au travail courant. Sunburst
  sert à la qualité : texte dense de packaging, chiffres, schémas, retouches qui doivent tenir la géométrie.
- [CHOIX] Un travail neuf part sur 2.5. GPT Image 2 n'a pas les paliers hauts. GPT Image 1 et 1 mini n'ont ni palier
  de qualité ni fond transparent dans l'app ; 1 mini reste le moins cher pour un essai.
- [CHOIX] Voie fal seulement : plusieurs références en retouche, fond transparent sur Sunburst et sur GPT Image 2,
  paliers xhigh et max sur 2.5. La voie directe n'envoie qu'UNE image d'entrée.
- [COÛT] La rangée « Qualité » de la pastille bouge le prix plus que le format : low, medium, high, plus xhigh et max
  via fal sur 2.5. Défaut high. Le choix est mémorisé par modèle, pour tous les écrans.
- [COÛT] Brouillon bas, final haut : low coûte une petite fraction de high. On cherche la composition en low, puis on
  relance le prompt retenu en high : sans seed, c'est un nouveau tirage, voisin mais pas identique. Un palier plus haut ne garantit pas un meilleur résultat : xhigh et max seulement
  quand high a raté une exigence précise.
- [COÛT] Retouche via fal : chaque image de référence est facturée en entrée, en plus de l'image rendue (relevé
  2026-11). Ne joindre que les références qui ont un rôle.
- [COÛT] GPT Image 2 en direct sans palier choisi : OpenAI applique son propre défaut, et le devis compte high.
- [PIÈGE] Vrai fond transparent : 2.5 Flare (deux voies), 2.5 Sunburst via fal et GPT Image 2 via fal. Le mot
  « transparent background » dans le prompt pose le réglage d'office sur ces membres. Sur les autres, l'image sort
  opaque et la réponse le dit : détourer ensuite (fiche détourage).
- [PIÈGE] Un fond transparent garde un halo de couleur sous les pixels effacés. Garder PNG ou WebP de bout en bout : un
  JPEG ou un fond sombre montre un liseré.
- [PROMPT] Ordre = poids : style, médium, sujet et ambiance d'abord ; puis scène, détails, lumière, texte. Nommer
  l'usage (publicité, maquette d'interface, infographie, key art) règle le niveau de finition.
- [PROMPT] Photoréalisme : écrire « photorealistic » et des textures concrètes (pores, tissu usé, grain). Pour une
  personne : cadrage, regard, ce que font les mains.
- [PROMPT] Un brief détaillé se normalise, il ne s'embellit pas. Ne jamais ajouter de personnage, de marque, de
  slogan ou de placement gauche/droite non demandé.
- [PROMPT] Texte : en plus des guillemets, donner un brief de mise en page (zone de chaque élément, rang de taille, ce
  qui reste vide), la graisse, la casse et le nombre d'occurrences ; finir par « no extra words, no duplicate text ».
- [PIÈGE] Au-delà d'environ sept exigences distinctes, certaines tombent sans bruit (relevé 2026-11). Poser une base
  propre, puis une modification ciblée par retouche.
- [PIÈGE] Le format : en direct, seulement carré, paysage ou portrait ; un 16:9 ou un 4:3 du projet sort au paysage
  le plus proche. Via fal, les formats du projet passent tels quels. Recadrer ensuite si le cadre exact compte.
- [PIÈGE] Une personnalité publique nommée fait refuser l'image : décrire un archétype.
- [PIÈGE] Un prompt complexe peut prendre environ deux minutes (relevé 2026-11) : attendre, ne pas relancer.
- [MÉTHODE] Plusieurs références (voie fal) : une phrase pour le médium, puis « Each reference picture has exactly one
  job: » et une ligne par image : « Image N (ce qu'elle montre) = JOB only. … Do not … ». Le rôle le plus souvent
  ignoré (le style) vient en premier.
- [MÉTHODE] Une référence prête tout ce qu'elle montre : dire pour chacune ce qu'il ne faut pas prendre. Un seul sujet
  principal par tir. Une fuite se corrige en resserrant la ligne et en relançant, pas par retouche.
- [CHOIX] Pas encore dans l'app : masque de retouche, taille en pixels (4K, vrai 21:9), plusieurs références en
  direct, fond transparent de Sunburst en direct, réglage de fidélité aux références.

## Exemple

Brief : « Une affiche carrée pour notre thé glacé COOL LEAF : la bouteille sur fond menthe, le nom en grand en haut.
Le prix et le logo viendront après. »

Prompt :

```
Product advertising poster, clean studio photography. A frosted glass bottle of iced tea stands centered on a
plain mint-green background, with water droplets on the glass and a soft shadow below. Top center, large bold
condensed sans-serif headline in white, all caps, reading "COOL LEAF". The lower third stays empty and calm.
Photorealistic, crisp label edges. No extra words, no duplicate text.
```

Réglages : GPT Image 2.5 Sunburst (voie selon la clé présente), format carré, qualité low pour trois brouillons ; on
garde la meilleure composition, puis le même prompt en high, une seule image. On relit le titre lettre à lettre. Le
prix et le logo s'incrustent ensuite dans la zone laissée vide (Templates ou Card Forge).

## Erreurs fréquentes

- Chercher une composition en high : chaque essai coûte le prix final. Brouillons en low.
- Joindre trois références sur la voie directe : seule la première part. Prendre le jumeau via fal.
- Écrire « transparent background » sur GPT Image 1 ou Sunburst en direct : l'image sort opaque. Prendre Flare ou un
  membre via fal.
- Enregistrer en JPEG une image détourée : le fond devient opaque et un liseré apparaît.
- Prendre xhigh ou max d'emblée, sans savoir ce que high a raté.
- Empiler dix consignes dans un prompt : certaines disparaissent. Base d'abord, retouches ciblées ensuite.
