---
famille: veo
natures: [video_i2v, video_fl]
ids: [veo-3.1-fast-fal, veo-3.1-fal, veo-3.1-lite-fal]
voies: [fal]
releve: 2026-11-09
source: scenario-veo (scenario-labs/skills, MIT) ; registre fal_service
description: À utiliser quand on anime une image avec Veo (Google) : Veo 3.1, Veo 3.1 Fast ou Veo 3.1 Lite servis par fal, image vers vidéo ou transition entre une image de début et une image de fin, prompt long et cinématographique, seed fixe pour comparer des formulations, champ négatif, refus de modération Google, extension d'un clip Veo, choix entre Lite et 3.1.
---
## Aperçu

Les trois membres Veo passent par fal ; les entrées Google directes sont retirées. Chacun anime une image de départ
et accepte une image de fin, un seed et un champ négatif. Avec une image de fin, l'app bascule seule sur l'endpoint
de transition. L'app coupe toujours la piste son.

## Référence rapide

- [PROMPT] Prose au présent, dans cet ordre : cadrage et caméra, sujet, action, contexte, style. Un seul arc
  principal par plan.
- [PROMPT] Veo suit les prompts développés : viser environ 90 à 250 mots (relevé 2026-11). En image vers vidéo,
  ces mots décrivent le mouvement, la caméra et la lumière, pas ce que l'image montre déjà.
- [PROMPT] Plusieurs temps : une ligne par temps avec son repère de temps, tous dans la durée choisie.
- [PROMPT] Transition début → fin : décrire un seul mouvement continu qui mène de la première image à la seconde.
- [PROMPT] Décrire la scène voulue, pas une liste de négations. Le champ négatif sert à décourager quelques défauts
  précis (« text, watermark, extra fingers »).
- [PROMPT] L'app coupe le son : n'écrire ni dialogue, ni effet, ni ambiance. Le son se pose au Montage.
- [PIÈGE] Une image de départ qui ne suit pas le format demandé peut être recadrée. La préparer au format de
  livraison avant le tir.
- [MÉTHODE] Comparer des formulations : garder le même seed et ne changer qu'une clause à la fois. Le seed ne
  garantit pas la même prise d'un membre à l'autre.
- [CHOIX] Lite pour les essais et les séries, Fast pour l'usage courant, 3.1 pour le plan final qui doit tenir.
- [COÛT] Lite coûte nettement moins que 3.1 pour un même plan (écart réel dans Membres). Brouillon en Lite à la durée
  finale, final en 3.1 ou Fast avec le même prompt.
- [COÛT] Sur 3.1 et Fast, le prix ne dépend pas de la résolution : prendre la plus haute. Sur Lite, elle change le
  prix.
- [COÛT] L'extension Veo de l'app a coûté plus qu'un plan neuf (relevé 2026-11). Viser d'abord le plan en un seul
  passage, à la durée la plus longue lue dans Membres.
- [PIÈGE] Extension : le prompt est obligatoire, et un clip venu d'un autre modèle peut être refusé ou mal prolongé.
  Pour continuer un plan, la dernière image du clip peut servir d'image de départ à un nouveau plan.
- [CHOIX] Modération : le filtre de Google est le plus strict sur les marques, les personnages connus et les
  ressemblances avec des personnes réelles. Les trois membres partagent ce filtre, et monter en gamme ne
  l'assouplit pas. Après un refus, passer à un autre fournisseur avec le même prompt.
- [CHOIX] Pas encore dans l'app : texte vers vidéo et images de référence (sujet ou style).

## Exemple

Brief : « une vidéo verticale pour TikTok : ma tasse de café sur la table de la terrasse, la vapeur monte, lumière
du matin ; je veux finir sur la tasse en gros plan ».

Image de départ : la terrasse en 9:16, tasse au tiers bas. Image de fin : la même tasse en gros plan, générée
depuis l'image de départ. Prompt :

```
Medium shot slowly pushing in to a close-up, camera at table height, steady and smooth. A white ceramic cup of black
coffee sits on a weathered wooden café table. Thin steam rises from the cup and curls to the left in a light breeze.
Low morning sun from the right rakes across the table and catches the steam, warm highlights on the rim. Leaves in
the soft background sway gently. The push-in is one continuous move that ends framed tight on the cup. Natural
photographic look, shallow depth of field, no subtitles, no on-screen text.
```

Négatif : « text, logo, watermark, extra cups ». Réglages : Veo 3.1 Lite pour l'essai, durée la plus longue, image de
fin : oui, seed fixé. Prompt et seed gardés pour le final en Veo 3.1.

## Erreurs fréquentes

- Écrire un prompt de dix mots : Veo comble le vide à sa façon. Donner caméra, lumière et mouvement en phrases.
- Mettre les défauts à éviter dans le prompt (« no blur, no people ») : ils apparaissent. Les placer dans le champ
  négatif.
- Changer le prompt et le seed en même temps : on ne sait plus ce qui a joué.
- Compter sur l'extension pour rallonger un plan court : elle coûte plus qu'un plan neuf.
