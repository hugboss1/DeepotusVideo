---
famille: sonilo
natures: [sfx_texte, sfx_video]
ids: [sonilo-1.1, sonilo-video]
voies: [fal]
releve: 2026-11-09
source: scenario-sonilo, scenario-audio (scenario-labs/skills, MIT) ; registre sfx_service (schémas fal relus le 12/10/2026)
description: À utiliser quand on génère un bruitage avec Sonilo 1.1, sur description (son long, ambiance, nappe d'effets) ou depuis un clip vidéo du Montage (bruitage calé sur l'image, piste son seule), qu'on veut garder la parole d'une vidéo pendant le bruitage, ou qu'on cherche un bruitage vidéo chiffré à la seconde.
---
## Aperçu

Sonilo 1.1 fait des effets sonores, jamais de parole ni de chant. Deux membres : **Sonilo 1.1** part d'une
description, **Sonilo 1.1 (vidéo)** part d'un clip vidéo et rend une **piste son seule**, calée sur l'image, à
poser sous le clip. Les deux rendent du WAV. Écrans : Son & VFX › SFX › « Générer des SFX » et le tiroir Sons du
Montage › Générer (sélecteur « Modèle ») pour la description ; tiroir Sons › Générer › « Depuis la vidéo » pour le
clip vidéo sélectionné dans la timeline. Sonilo vidéo est le modèle proposé par défaut pour un clip.

## Référence rapide

- [PROMPT] Description : un seul événement par son. Ordre : source, matière, espace, intensité (« a heavy steel
  door slams shut, concrete stairwell, loud and close »).
- [PROMPT] Des mots physiques plutôt que des humeurs : « hollow », « muffled », « punchy » décrivent un son ;
  « scary » ne dit rien au modèle.
- [PROMPT] Sonilo n'a pas de repère de temps dans un son décrit : dire l'intention de durée dans le texte (« a short
  click », « a long rumbling roll ») **et** régler la durée.
- [PIÈGE] Sans durée, c'est le défaut du modèle qui part, pas une durée adaptée au son : régler la durée voulue.
  Elle est bornée à la plage de Membres.
- [CHOIX] Description longue et continue (ambiance, roulement, vent) : Sonilo couvre la plus longue plage de durée
  de la liste (Membres).
- [PROMPT] Vidéo : l'image décide **quand** le son arrive, la description seulement **à quoi** il ressemble. Le
  bruitage suit l'image ; la piste d'origine ne sert qu'à « Garder la voix ».
- [PROMPT] Vidéo : une description vide est permise et souvent la meilleure : le modèle lit le clip et bruite
  chaque plan. N'écrire que pour corriger un son raté (« wet footsteps on gravel »).
- [CHOIX] « Garder la voix » (case de Sonilo vidéo seulement) demande au modèle de garder la parole de la vidéo.
  Son effet exact sur la piste rendue est à confirmer : écouter le premier essai.
- [PIÈGE] Sonilo ne rend jamais de voix générée ni de musique chantée. Pour une voix, la fiche voix ; pour une
  musique, la nature musique.
- [MÉTHODE] Bruitage et musique se génèrent en pistes séparées et se mixent au Montage. Ne jamais faire passer un
  clip déjà bruité dans un outil qui remplace toute sa piste : le bruitage disparaît.
- [CHOIX] Aucune graine : chaque tir est une nouvelle prise. Garder les bonnes prises dans la Bibliothèque.
- [COÛT] Description : à la seconde de son rendu, et par variation (chaque variation est un tir). « Générer des
  SFX » de Son & VFX en tire toujours deux.
- [COÛT] Vidéo : à la seconde **du clip source**. Couper le clip au plan utile avant de le bruiter.
- [MÉTHODE] Hors ElevenLabs direct, le bouton s'arme en deux clics : le premier montre le devis du serveur, le
  second tire.
- [CHOIX] Le curseur « Fidélité » du tiroir ne part pas chez Sonilo : seul le texte compte.
- [CHOIX] Pas encore dans l'app : descriptions par plage de temps (`segments`), décalage de départ, choix du format
  audio, musique Sonilo, vidéo rendue avec la piste mixée.

## Exemple

Brief : « bruiter le plan de mon skateur qui retombe sur le béton ; il crie "yes!" à l'atterrissage et je veux
garder son cri ».

Réglages : Montage, clip vidéo sélectionné dans la timeline, puis tiroir Sons (B) › Générer › « Depuis la vidéo ».
Modèle Sonilo 1.1 (vidéo), case « Garder la voix » cochée. Premier essai avec la description vide. Les roues sonnent
lisses : second essai avec

```
rough urethane wheels rolling on cracked concrete, hard deck slap on landing, open street air
```

Premier clic : le devis à la seconde du clip ; second clic : le tir. La piste rejoint la Bibliothèque (sons), liée au
clip ; la poser sous le clip au Montage.

## Erreurs fréquentes

- Décrire toute la scène en une phrase pour un son sur description (« door, steps, scream ») : un événement par son.
- Bruiter un clip entier de plusieurs plans pour un seul effet : le prix suit toute la durée du clip.
- Écrire un prompt détaillé dès le premier essai vidéo : la description vide fait souvent mieux.
- Attendre une voix ou un chant de Sonilo : il n'en produit pas.
