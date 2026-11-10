---
famille: ltx
natures: [video_i2v, video_fl]
ids: [ltx-2.5-fast, ltx-2.5-pro]
voies: [fal]
releve: 2026-11-09
source: scenario-video, scenario-moderation (scenario-labs/skills, MIT) ; registre fal_service
description: À utiliser quand on anime une image avec LTX (Lightricks) : LTX 2.5 Fast ou LTX 2.5 Pro, image vers vidéo ou plan entre une image de début et une image de fin, plan plus long à petit prix, choix entre Fast et Pro.
---
## Aperçu

LTX 2.5 existe en deux variantes du même modèle : Fast et Pro, la variante « qualité ». Les deux animent une image de
départ et acceptent une image de fin. Elles n'ont ni seed ni champ négatif. L'app coupe la piste son, et laisse le
mouvement de caméra et la cadence d'images à leur valeur par défaut.

## Référence rapide

- [PROMPT] La caméra n'a pas de champ dans l'app : l'écrire dans le prompt, un mouvement nommé et lent par plan
  (« slow push-in », « static camera »).
- [PROMPT] L'image de départ porte l'identité et le style. Le prompt décrit le mouvement, la caméra et le rythme,
  pas ce que l'image montre déjà.
- [PROMPT] Pas de champ négatif : écrire en positif ce qui doit rester (« the background stays still »). Un défaut
  nommé dans le prompt tend à apparaître.
- [PROMPT] L'app coupe le son : n'écrire aucune ligne de son.
- [PIÈGE] Les durées vont par paliers fixes, différents entre Fast et Pro. Une durée hors palier est ramenée au plus
  proche, avec une note : lire les paliers dans Membres.
- [PIÈGE] Pas de seed : chaque relance est une nouvelle prise. Ne changer qu'une clause à la fois et garder la prise
  réussie.
- [CHOIX] Fast pour les plans longs et les essais ; Pro pour un plan court qui doit être plus soigné.
- [COÛT] Le son natif est compris dans le prix des deux variantes : le couper ne fait rien baisser.
- [COÛT] Brouillon en Fast à la durée finale, puis Pro avec le même prompt si le plan tient dans ses durées.
- [MÉTHODE] Image de fin : décrire un seul mouvement continu de la première image vers la seconde.

## Exemple

Brief : « une Story 9:16 qui montre ma veste en jean sur un portant, la caméra tourne doucement autour ».

Image de départ : la veste sur son portant, en 9:16, fond d'atelier clair. Prompt :

```
Slow orbit to the right around the denim jacket hanging on a metal rack, camera at chest height, steady and smooth.
The jacket sways slightly as the air moves, the fabric folds shifting with the motion. Soft window light from the
left stays constant. The rack and the workshop background stay still. No subtitles, no on-screen text.
```

Réglages : LTX 2.5 Fast, durée moyenne, image de fin : non. Si le mouvement convient et que la durée existe chez
Pro, relance en Pro avec le même prompt : c'est une nouvelle prise.

## Erreurs fréquentes

- Demander une durée hors palier et découvrir après coup un clip plus court ou plus long : lire Membres avant le
  tir.
- Écrire « no camera shake » : décrire plutôt « steady and smooth ».
- Relancer en Pro en espérant la même prise améliorée : sans seed, c'est un autre rendu.
