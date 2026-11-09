---
famille: kling
natures: [video_i2v, video_fl]
ids: [kling-v3-pro, kling-v3-standard, kling-v3-turbo-pro, kling-v4]
voies: [fal]
releve: 2026-11-09
source: scenario-kling, scenario-video (scenario-labs/skills, MIT), registre fal_service
description: À utiliser quand on anime une image avec Kling (Kling 4.0, Kling v3 Pro, v3 Standard, v3 Turbo Pro), qu'on hésite entre ces membres, qu'on veut une image de fin pour fixer l'atterrissage du plan, un champ négatif, un plan long d'un seul tenant, ou qu'un clip Kling bouge trop, se fige, dérive ou arrive au mauvais format.
---
## Aperçu

Kling (Kuaishou) anime une image de départ, avec une image de fin sur trois de ses quatre membres. L'app propose
v3 Standard, v3 Pro, v3 Turbo Pro et 4.0. Aucun membre n'a de champ format : le cadre suit l'image de départ.
Aucun membre n'a de seed : chaque tir est une nouvelle prise.

## Référence rapide

- [CHOIX] v3 Standard sert à chercher le mouvement à moindre coût. v3 Pro sert à la prise finale du même plan.
- [CHOIX] v3 Turbo Pro n'accepte **pas** d'image de fin, ni de négatif. Il convient à un plan libre dont seule
  l'ouverture compte. Pour un atterrissage imposé, prendre v3 Pro, v3 Standard ou 4.0.
- [CHOIX] 4.0 est le plus long des membres (lire la durée maximale dans Membres). Il prend une image de fin et une
  résolution, mais ni négatif ni seed.
- [PROMPT] Ordre de réalisateur : sujet, une action, un mouvement de caméra nommé, puis lumière et style. Des phrases
  naturelles, pas une liste de mots-clés.
- [PROMPT] Mouvement composé (« dolly in while orbiting ») : garder un seul mouvement dominant par plan. Le second
  va dans un autre plan.
- [PROMPT] Négatif (v3 Pro et v3 Standard seulement) : une liste courte d'artefacts. Une longue liste rigidifie le
  mouvement.
- [PIÈGE] Une scène chargée tient mieux sur un plan court. Sur une durée longue, demander une action simple et
  continue, sinon le clip hésite ou se fige ; mieux vaut couper en plusieurs plans.
- [PIÈGE] Le format suit l'image : une image horizontale donne un clip horizontal. Préparer l'image de départ au
  format voulu avant le tir.
- [PIÈGE] L'image de fin fixe l'atterrissage. Elle doit montrer le même décor, le même sujet et la même lumière que
  l'image de départ ; sinon le modèle invente une transition (fondu, morphing).
- [MÉTHODE] Kling n'étend pas un clip. Pour continuer, extraire la dernière image du clip gardé et la donner en image
  de départ d'un nouveau tir. Écrire ce prompt d'après ce que montre cette image, puis monter en coupe franche.
- [PIÈGE] v3 Turbo Pro et 4.0 n'ont pas d'interrupteur son : le clip peut arriver avec une piste générée (à
  confirmer au premier tir). Prévoir de la remplacer au montage, et ne demander ni musique ni silence dans le prompt.
- [COÛT] Sans seed, refaire en Pro un plan trouvé en Standard donne une autre prise. Si la prise Standard convient,
  la garder et l'agrandir (upscale vidéo) plutôt que la re-rendre.
- [CHOIX] Pas encore dans l'app : plans multiples dans un tir, personnages par éléments, références d'identité,
  tête parlante. Ne pas les promettre.

## Exemple

Brief : « Une vidéo verticale pour TikTok : notre tasse de café fumante sur une table en bois, la caméra s'approche
doucement et finit en gros plan sur la tasse. » L'image de départ 9:16 (tasse en plan moyen) est validée. L'image de
fin 9:16 (même tasse en gros plan, même lumière) est retouchée depuis l'image de départ.

Prompt :

```
Steam rises slowly from the coffee cup. The camera performs a slow, steady dolly in toward the cup and settles on
a close-up. Soft morning window light from the left stays constant. Smooth, natural motion.
```

Réglages : Kling v3 Standard pour un premier essai, puis v3 Pro ; image de départ et image de fin : oui ; durée
courte ; négatif : « subtitles, on-screen text, warped cup, flicker ». Le logo et le slogan s'incrustent ensuite au
Montage.

## Erreurs fréquentes

- Choisir v3 Turbo Pro pour un plan qui doit finir sur une image précise : il n'a pas d'image de fin. Passer en
  v3 Pro ou en 4.0.
- Partir d'une image horizontale pour une vidéo verticale : le clip garde le format de l'image. Recadrer ou
  régénérer l'image d'abord.
- Écrire deux mouvements de caméra et trois actions dans un plan long : le mouvement devient flou ou s'arrête.
- Remplir le négatif de vingt termes : le sujet bouge à peine. Trois ou quatre artefacts suffisent.
- Re-rendre en Pro en espérant retrouver la prise Standard : sans seed, c'est un autre clip.
