---
famille: minimax-video
natures: [video_i2v, video_fl]
ids: [h3-max]
voies: [fal]
releve: 2026-11-09
source: scenario-minimax-video, scenario-video (scenario-labs/skills, MIT), registre fal_service
description: À utiliser quand on anime une image avec MiniMax H3 Max (Hailuo), quand on veut piloter la caméra par commandes entre crochets, quand on fixe une image de début et une image de fin, quand le fond ondule ou que l'image dérive, ou quand on se demande si le prompt sera réécrit ou si le clip arrive avec du son.
---
## Aperçu

H3 Max anime une image de départ, avec une image de fin si on la donne. Le cadre suit l'image : il n'y a pas de champ
format. Il a un seed. Il lit le prompt de près, y compris les commandes de caméra entre crochets. L'app envoie toujours
le mode d'expansion de prompt « équilibré » : le texte peut être reformulé avant le rendu.

## Référence rapide

- [PROMPT] Ne décrire que le mouvement : sujet, une action, caméra, lumière qui change. L'image porte déjà le décor et
  le style.
- [PROMPT] Les mouvements de caméra se nomment entre crochets : `[Push in]`, `[Pull out]`, `[Pan left]`,
  `[Tilt up]`, `[Truck right]`, `[Pedestal up]`, `[Zoom out]`, `[Tracking shot]`, `[Static shot]`.
- [PROMPT] Plusieurs commandes dans un même crochet jouent ensemble (`[Pan left, Pedestal up]`) ; des crochets
  séparés jouent l'un après l'autre. Trois commandes par crochet au plus (relevé 2026-11).
- [PIÈGE] Au-delà de deux ou trois indications de mouvement, le fond ondule et les textures scintillent. Garder une
  commande de caméra et une action.
- [PIÈGE] Même sans mouvement demandé, le plan dérive. Pour un plan fixe, écrire `[Static shot]` et « locked camera,
  tripod mounted ».
- [PIÈGE] Le prompt est réécrit par l'expansion « équilibrée », que l'app ne permet pas encore de couper. Une
  formulation exacte peut donc bouger : vérifier sur la sortie que l'action demandée est bien là.
- [PROMPT] Garder le prompt court et dense. La limite relevée est de 2 000 caractères, et des prompts bien plus courts
  ont été refusés à travers un intermédiaire (relevé 2026-11).
- [PIÈGE] Le modèle livre toujours une piste son ; il n'a pas d'interrupteur. L'app la retire au téléchargement :
  la voix off ou la musique du projet se posent au Montage.
- [PROMPT] Ne rien dire du son dans le prompt, ni « no music » : la piste est retirée de toute façon.
- [CHOIX] Une source publique plafonnait l'image vers vidéo à 768P, alors que le registre de l'app propose aussi
  1080p. À confirmer au premier tir en 1080p : vérifier la taille réellement livrée.
- [CHOIX] L'app demande 720p : le fournisseur reçoit 768P, sa résolution voisine. Le fichier livré n'a donc pas
  exactement la hauteur d'un 720p.
- [COÛT] Brouillon d'abord à la plus basse résolution des Membres, à la durée finale. Le brouillon valide la
  composition et le mouvement, pas les pixels : changer de résolution est une nouvelle génération, même avec le même
  seed.
- [MÉTHODE] Image de fin : la donner seulement quand le plan doit atterrir sur une pose précise. Elle doit garder le
  même cadre et le même sujet que l'image de départ.
- [CHOIX] Références d'identité, texte vers vidéo, extension, version Turbo et remplacement de personnes existent chez
  MiniMax mais pas encore dans l'app.

## Exemple

Brief : « Ma photo produit d'une bouteille de parfum sur un rocher mouillé ; je veux un plan vertical de réseau
social, la caméra qui s'approche doucement, des gouttes qui tombent. »

Prompt :

```
[Push in] Slow, steady approach toward the perfume bottle on the wet rock. A few water drops fall from above and
splash softly on the stone beside the bottle. Light ripples move across the glass. The bottle stays still and sharp.
No subtitles, no on-screen text.
```

Réglages : image de départ = la photo produit déjà recadrée en vertical (le cadre suit l'image) ; image de fin : non ;
durée courte ; résolution la plus basse pour le brouillon, puis la plus haute une fois le mouvement validé ; seed noté
pour reprendre le brouillon retenu ; le clip arrive muet, le son se pose au Montage.

## Erreurs fréquentes

- Empiler « orbit », « zoom », « pan » et « dolly » dans une phrase : le fond ondule. Une seule commande entre
  crochets.
- Donner une image paysage en espérant un clip vertical : il n'y a pas de champ format. Recadrer l'image en vertical
  avant le tir.
- Juger le grain final sur le brouillon en basse résolution, puis s'étonner que le rendu final diffère : c'est une
  autre génération.
- Compter sur une phrase exacte du prompt alors que l'expansion la reformule : relire la sortie.
- Décrire une ambiance sonore dans le prompt : elle est générée, payée, puis retirée.
