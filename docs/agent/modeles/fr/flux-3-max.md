---
famille: flux-3-max
natures: [video_i2v, video_fl]
ids: [flux-3-max]
voies: [fal]
releve: 2026-11-09
source: scenario-video, scenario-moderation (scenario-labs/skills, MIT), registre fal_service
description: À utiliser quand on anime une image avec FLUX 3 Max (Black Forest Labs) en vidéo, quand on veut une image de début et une image de fin sur le même modèle, une boucle qui revient à sa pose, un seed pour reprendre une prise, un clip muet, ou un repli après un refus de modération chez un fournisseur plus strict.
---
## Aperçu

FLUX 3 Max anime une image de départ, avec une image de fin si on la donne, sur le même appel. Il a un champ format
et un seed. Il n'a pas de champ négatif. Son interrupteur de son existe, et l'app le laisse toujours coupé : le clip
arrive muet. Peu de retours publics existent sur ce modèle vidéo ; la fiche s'en tient aux règles vidéo
générales et au registre.

## Référence rapide

- [PROMPT] Ne décrire que le mouvement : une action, un mouvement de caméra nommé, la lumière qui change. L'image
  porte déjà le décor et le style.
- [PROMPT] Une caméra et une action par plan. Quand le plan a deux temps, les dire dans l'ordre, avec un repère de
  temps.
- [PIÈGE] Sans champ négatif, une exclusion s'écrit dans le prompt, en positif quand c'est possible. Garder « no
  subtitles, no on-screen text ».
- [PIÈGE] Le format se règle dans le champ format. Si l'image n'a pas ce format, le modèle recadre ou complète :
  recadrer l'image avant le tir.
- [PROMPT] Inutile d'écrire une ligne de son : le clip est muet. Le son vient ensuite de la voix off, de la musique
  ou des bruitages du projet.
- [MÉTHODE] Image de fin : la donner seulement pour atterrir sur une pose précise. Elle garde le même cadre et le même
  sujet que l'image de départ.
- [MÉTHODE] Boucle : donner la même image en début et en fin, et décrire un mouvement qui part et revient. Vérifier
  le raccord en lisant le clip en boucle.
- [MÉTHODE] Seed : le noter sur une prise retenue. Le même seed avec le même prompt et les mêmes réglages permet de
  la retrouver ; changer une seule clause à la fois.
- [CHOIX] Modération : les modèles FLUX sont parmi les plus permissifs relevés (relevé 2026-11). C'est un repli
  raisonnable après un refus chez un fournisseur plus strict, à coût voisin.
- [COÛT] Brouillon d'abord à la plus basse résolution des Membres, à la durée finale. Changer de résolution est une
  nouvelle génération, même avec le même seed.
- [CHOIX] Le texte vers vidéo et la vidéo par images-clés multiples existent chez Black Forest Labs mais pas encore
  dans l'app.

## Exemple

Brief : « L'illustration de ma mascotte, un renard en écharpe ; je veux une vidéo verticale qui tourne en boucle sur
mon profil : il cligne des yeux et son écharpe flotte. »

Prompt :

```
The fox stands in place and blinks once, slowly. Its scarf lifts gently in a light breeze, then settles back to
its starting position. The camera stays locked and still. The background does not change. No subtitles, no
on-screen text.
```

Réglages : image de départ = l'illustration recadrée en vertical ; image de fin : oui, la même image, pour fermer la
boucle ; format vertical dans le champ format ; durée courte ; résolution la plus basse pour le brouillon ; seed noté
sur la prise retenue ; son ajouté au montage.

## Erreurs fréquentes

- Écrire une ligne de son en attendant de l'entendre : le clip arrive muet.
- Donner une image de fin dont le cadre diffère de l'image de départ : le modèle invente un trajet de caméra.
- Demander plusieurs actions et plusieurs mouvements de caméra dans le même plan : le mouvement se brouille.
- Relancer sans noter le seed, puis ne plus retrouver la bonne prise.
- Changer trois clauses à la fois entre deux tirs : on ne sait plus laquelle a compté.
