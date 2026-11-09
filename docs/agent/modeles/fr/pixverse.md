---
famille: pixverse
natures: [video_i2v]
ids: [pixverse-v6]
voies: [fal]
releve: 2026-11-09
source: scenario-video (scenario-labs/skills, MIT), registre fal_service
description: À utiliser quand on anime une image avec PixVerse v6, qu'on veut comparer des variantes de prompt à seed fixe, se servir d'un champ négatif, choisir la résolution d'un clip court, ou qu'on hésite entre PixVerse et un membre d'une autre famille qui accepte une image de fin.
---
## Aperçu

PixVerse v6 anime une image de départ. Il n'accepte pas d'image de fin. Il a un seed, un champ négatif et un choix de
résolution. Le cadre suit l'image de départ : il n'a pas de champ format. Ses durées sont peu nombreuses : les lire
dans Membres.

## Référence rapide

- [CHOIX] Le prendre pour un plan court dont seule l'ouverture compte. Pour un plan qui doit finir sur une image
  précise, prendre un membre qui accepte une image de fin.
- [MÉTHODE] Le seed permet de comparer : garder la même image, le même seed et la même durée, puis changer une seule
  clause du prompt par tir. La différence vient alors de cette clause.
- [PIÈGE] Le seed ne garantit pas la même prise d'une résolution à l'autre. Un brouillon en basse résolution valide
  le mouvement, pas le clip final.
- [PROMPT] Une action et un mouvement de caméra nommé par plan, en phrases. Ne décrire que le mouvement : l'image
  porte déjà le sujet et le décor.
- [PROMPT] Négatif : une liste courte d'artefacts visibles (« flicker, warped hands, on-screen text »). Une longue
  liste rigidifie le mouvement.
- [PIÈGE] Le format suit l'image : une image horizontale donne un clip horizontal. Préparer l'image de départ au
  format voulu avant le tir.
- [PIÈGE] Les durées natives sont fixes. Une durée cible plus longue est rallongée par l'app (ffmpeg), pas générée
  par le modèle : pour plus de mouvement, enchaîner deux plans depuis la dernière image.
- [COÛT] Chercher le mouvement en résolution basse, à la durée finale, puis rendre une fois en haute résolution.
- [CHOIX] Pas encore dans l'app : préréglages de style et effets du fournisseur. Ne pas les promettre.

## Exemple

Brief : « Une story verticale pour Instagram : la bouteille de parfum posée sur un rocher mouillé, une vague vient
lécher le rocher, la caméra tourne un peu autour. » L'image de départ 9:16 est validée.

Prompt :

```
A small wave rolls in and washes over the base of the wet rock, then pulls back. The camera makes a slow orbit to
the right around the perfume bottle. Soft overcast light, gentle sea spray in the air.
```

Réglages : PixVerse v6 ; durée courte ; résolution basse pour deux ou trois essais à seed fixe, puis haute
résolution pour le clip retenu ; négatif : « flicker, distorted bottle, on-screen text » ; image de fin : non
disponible.

## Erreurs fréquentes

- Le choisir pour un plan qui doit atterrir sur une image donnée : il n'a pas d'image de fin. Changer de famille.
- Changer le prompt, le seed et la résolution en même temps : on ne sait plus ce qui a amélioré le clip.
- Croire que le seed reproduira en haute résolution la prise vue en basse résolution.
- Partir d'une image horizontale pour une story verticale : le clip garde le format de l'image.
