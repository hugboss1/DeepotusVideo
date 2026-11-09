---
famille: wan
natures: [video_i2v, video_fl]
ids: [wan-3.0]
voies: [fal]
releve: 2026-11-09
source: scenario-wan, scenario-video (scenario-labs/skills, MIT), registre fal_service
description: À utiliser quand on anime une image avec Wan 3.0 (Alibaba), qu'on veut une image de fin, un plan long d'un seul tenant, un seed pour comparer des variantes, un brouillon en basse résolution avant le final, ou qu'un clip Wan change le contenu de l'image, affiche du texte illisible ou s'écarte du prompt écrit.
---
## Aperçu

Wan 3.0 anime une image de départ, avec une image de fin en option. Il a un seed et un choix de résolution, mais pas
de champ négatif. Le cadre suit l'image de départ : il n'a pas de champ format. Ses durées vont loin : lire la durée
maximale dans Membres. Les faits ci-dessous viennent des versions 2.x ; ils sont transposés à 3.0 avec prudence.

## Référence rapide

- [PROMPT] Ne décrire que le mouvement, la caméra et le rythme. Redécrire l'image gaspille le prompt.
- [PIÈGE] Un clip depuis une image ne change pas le contenu de cette image. Pour un autre décor ou une autre tenue,
  retoucher d'abord l'image, puis l'animer.
- [PROMPT] Une action et un mouvement de caméra nommé par plan. Sur un plan long, une action continue et lente ; des
  repères de temps s'il y a plusieurs temps.
- [PIÈGE] Pas de champ négatif. Les exclusions courantes s'écrivent en fin de prompt (« no subtitles, no on-screen
  text ») ; le reste se décrit en positif.
- [PIÈGE] Le texte lisible dans l'image est peu fiable sur toute la famille. Le poser au montage.
- [PIÈGE] Les versions 2.x réécrivent le prompt par défaut avant de générer (relevé 2026-11). Si 3.0 fait de même, un
  prompt précis peut être dilué : à confirmer au premier tir. Un clip qui s'écarte d'une consigne exacte en est le
  signe.
- [PIÈGE] Le format suit l'image : une image horizontale donne un clip horizontal. Préparer l'image de départ au
  format voulu avant le tir.
- [PIÈGE] L'image de fin doit montrer le même décor, le même sujet et la même lumière que l'image de départ ; sinon
  le modèle invente une transition.
- [COÛT] La résolution pèse lourd sur le prix : sur Wan 2.7, le 1080p coûtait environ trois fois le 720p
  (relevé 2026-11). Lire l'écart réel dans Membres. Chercher le mouvement en basse résolution, à la durée finale.
- [PIÈGE] Même seed et même prompt ne redonnent pas la même prise dans une autre résolution. Le brouillon valide le
  mouvement, pas le clip final.
- [MÉTHODE] Le seed sert à comparer : même image, même seed, même durée, une seule clause du prompt changée par tir.
- [CHOIX] Pas encore dans l'app : édition d'une vidéo par instruction, recadrage génératif, remplacement d'un
  personnage, plans multiples, son importé synchronisé aux lèvres. Ne pas les promettre.

## Exemple

Brief : « Un Reel vertical pour la boulangerie : la vitrine au petit matin, la caméra recule lentement pour révéler
la rue, et on termine sur la façade entière. » L'image de départ 9:16 (vitrine en plan rapproché) est validée.
L'image de fin 9:16 (façade entière, même lumière) est retouchée depuis l'image de départ.

Prompt :

```
The camera slowly pulls back from the shop window and rises slightly, revealing the quiet street and the full
bakery facade. Warm light glows inside the shop while the early morning sky brightens gently. A few leaves drift
across the pavement. Steady, smooth motion. No subtitles, no on-screen text.
```

Réglages : Wan 3.0 ; image de départ et image de fin : oui ; durée moyenne ; résolution basse pour les essais à seed
fixe, puis la plus haute pour le clip retenu ; le nom de la boulangerie s'incruste au Montage.

## Erreurs fréquentes

- Demander dans le prompt un autre décor que celui de l'image : le clip garde l'image et ignore la consigne.
- Écrire le nom de la boutique dans le prompt pour qu'il apparaisse sur l'enseigne : il sort déformé.
- Chercher un champ négatif : il n'existe pas sur ce membre. Écrire les exclusions courantes en fin de prompt.
- Itérer directement en haute résolution : chaque essai coûte plusieurs fois le prix d'un brouillon.
