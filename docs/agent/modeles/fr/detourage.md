---
famille: detourage
natures: [detourage_image, detourage_video]
ids: [local-rembg, local-chroma, birefnet-v2, bria-rmbg, pixelcut, ideogram-rmbg, feynobg, sam3-sujet, bria-objet, rembg-fal, birefnet-v2-video, bria-video-v3, veed-video-rapide, pixelcut-video, sam31-video]
voies: [local, fal]
releve: 2026-11-09
source: scenario-image-editing, scenario-image (scenario-labs/skills, MIT) ; registre detourage, matte_service, decor_service
description: À utiliser quand on doit retirer le fond d'une image ou d'une vidéo, choisir un détoureur (rembg local, fond uni ou fond vert, BiRefNet, Bria, Pixelcut, Ideogram, FeyNobg, SAM 3 ou SAM 3.1 pour un sujet nommé, VEED), détourer une photo produit, des cheveux, un personnage, un sprite ou une prise vidéo, obtenir un PNG ou une vidéo avec alpha, ou quand un détourage laisse une frange, un halo ou un fond résiduel.
---
## Aperçu

Le détourage retire le fond et rend un PNG avec alpha (image) ou une vidéo avec alpha (`.mov` ProRes ou `.webm`
VP9). Deux membres sont **locaux et gratuits** : rembg et le fond uni (chroma). Les autres passent par fal et sont
payants, à l'image, à la seconde ou par tranches d'images (colonne prix des Membres). Trois membres exigent un
**sujet nommé** : ils gardent ce qu'on nomme et effacent le reste. Le même registre sert la Bibliothèque, le
matte du Montage, les sprites, Card Forge, le 3D Studio et le « Décor seul » de l'Avatar live.

## Référence rapide

- [CHOIX] Commencer **local** : rembg pour un sujet net sur un fond quelconque, fond uni pour un fond d'une seule
  couleur. Ne passer à fal que si le bord est mauvais.
- [CHOIX] Fond uni (`local-chroma`) : il prend la couleur du pourtour, verte ou autre. Il refuse si le pourtour
  n'est pas uni ou si le sujet couvre presque tout le cadre (ou presque rien). Idéal pour un fond vert ou une
  image générée sur fond plat.
- [CHOIX] Cheveux, fourrure, bords fins : BiRefNet v2. L'app règle l'image sur le modèle lourd, à haute résolution
  de travail, avec affinage des bords ; la vidéo sur le modèle léger, à résolution plus basse.
- [CHOIX] Photo produit, objet net : Bria RMBG 2.0, Pixelcut ou Ideogram ; le moins cher qui rend un bord propre
  sur un essai.
- [CHOIX] Plusieurs sujets dans l'image, un seul à garder : SAM 3 (« garder un sujet nommé ») ou Bria objet
  (« extraire un objet nommé »). Écrire le sujet en quelques mots anglais : « the red backpack », « the woman on
  the left ».
- [PIÈGE] Un membre à sujet sans sujet est refusé avant toute dépense. Les autres ignorent un sujet.
- [CHOIX] `rembg-fal` est l'ancien rembg servi par fal ; rembg local fait le même travail gratuitement quand il
  est installé.
- [CHOIX] Vidéo : BiRefNet v2 vidéo est le défaut. Bria VRMBG 3.0 garde la piste son. SAM 3.1 suit un sujet nommé
  sur toute la prise. VEED rapide et Pixelcut vidéo rendent un `.webm`.
- [MÉTHODE] Vidéo : détourer d'abord **une image** du milieu de la prise avec le jumeau image du membre (Bria
  RMBG pour Bria vidéo, SAM 3 pour SAM 3.1, BiRefNet pour BiRefNet vidéo et VEED, Pixelcut pour Pixelcut vidéo). L'écran « Décor seul » de l'Avatar live le fait
  avant de lancer la vidéo.
- [CHOIX] Une animation courte ou une boucle peut se détourer plus proprement image par image (images extraites)
  qu'en détourage vidéo (relevé 2026-11). Le coût suit alors le nombre d'images.
- [COÛT] À la seconde (Bria vidéo ; BiRefNet vidéo aussi, mais « prix à mesurer ») : la durée fait le prix. Par tranches d'images (VEED, Pixelcut
  vidéo, SAM 3.1) : à durée égale, une cadence élevée coûte plus. Couper la prise au plan utile avant.
- [COÛT] Sprites : chaque image de la feuille est un détourage facturé. Fond uni ou rembg local d'abord.
- [COÛT] Un membre marqué « prix à mesurer » est chiffré à zéro au devis mais facturé par fal : le plafond ne le
  freine pas. L'essayer sur une seule image.
- [COÛT] Préférer un générateur d'image qui rend un vrai fond transparent (colonne « transp. » de sa fiche) : cela
  évite une passe facturée.
- [PROMPT] Image générée pour être détourée, par un modèle sans fond transparent : demander « plain light grey
  background, soft even light, subject fully in frame ». Éviter un fond de la couleur du sujet.
- [PROMPT] Vidéo générée pour être détourée : « plain background, locked-off camera, no cuts ». Fond uni et caméra
  fixe donnent un matte propre.
- [PIÈGE] Frange : un liseré semi-transparent de l'ancien fond peut rester au bord. Vérifier sur un fond sombre
  **et** clair, pas sur le damier.
- [PIÈGE] Verre, fumée, voile : l'intérieur peut sortir percé ou opaque selon le membre. Vérifier en mesurant
  l'alpha, pas à l'œil.
- [PIÈGE] Un matte réexporté en MP4 perd son alpha. Garder le `.mov` ou le `.webm` jusqu'au Montage.
- [CHOIX] Pas encore dans l'app : les réglages propres des membres fal (choisir le modèle interne de BiRefNet, mode « sujet
  humain » de VEED) ; l'app les fixe.

## Exemple

Brief : « J'ai 12 photos de mes bougies sur la table de la cuisine ; il me faut des PNG détourés pour la boutique,
et une de ces photos montre aussi un vase que je ne veux pas. »

Réglages : rembg local sur une photo d'essai. Le bord de la mèche reste flou : Bria RMBG 2.0 sur la même photo,
bord net, puis les 11 autres. Pour la photo au vase, SAM 3 avec le sujet :

```
the white candle in the glass jar
```

Contrôle : chaque PNG posé sur un fond noir puis sur un fond blanc, à 100 %, pour voir une frange ou un reste de
nappe.

## Erreurs fréquentes

- Payer un détoureur fal pour une image sur fond vert ou fond uni : le fond uni local suffit.
- Lancer une vidéo entière sans aperçu sur une image : le bord raté se paie sur toute la durée.
- Prendre un membre à sujet pour une image à un seul sujet : refus sans sujet, et rien de mieux qu'un généraliste.
- Écrire « transparent background » dans le prompt d'un générateur, puis s'étonner du fond opaque : détourer
  ensuite.
- Juger le détourage sur le damier de l'aperçu : la frange ne s'y voit pas.
