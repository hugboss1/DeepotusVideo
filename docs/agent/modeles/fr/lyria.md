---
famille: lyria
natures: [musique]
ids: [lyria3, lyria-3.5]
voies: [fal]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; registre music_service, écran Musique de Son & VFX
description: À utiliser quand on génère une musique de fond avec Lyria (Google) : Lyria 3, modèle par défaut de l'écran Musique, ou Lyria 3.5 ; nappe, jingle, boucle courte, musique d'ambiance pour une Reel ou une vidéo, piste instrumentale, voix chantée sans paroles imposées, prompt négatif musique, tempo en BPM, durée fixe de Lyria 3.
---
## Aperçu

Lyria compose une piste depuis une description, sans champ de paroles. Lyria 3 est le modèle par défaut de l'écran
Musique (Son & VFX) : sa durée est imposée, Lyria 3.5 choisit la sienne. Aucun des deux ne prend de graine. Le prix
est par piste, quelle que soit la longueur rendue. La piste arrive dans la Bibliothèque (sons), prête pour le
Montage.

## Référence rapide

- [PROMPT] Ordre utile : genre, humeur, instrumentation, production, tempo. Le début du prompt pèse le plus ; une
  ambiance choisie passe devant la description.
- [PROMPT] Décrire une évolution simple en mots de musicien : « starts with solo piano, strings join halfway, ends on
  a held chord ». Pas de minutage à la seconde : sans champ de structure, rien ne le garantit.
- [PIÈGE] Les ambiances de l'écran contiennent déjà un tempo. En écrire un second dans la description donne deux
  tempos dans le prompt : soit l'ambiance, soit le tempo écrit, pas les deux.
- [PROMPT] Le tempo s'écrit « 92 BPM ». Le serveur accepte un champ `bpm` qui remplace tout tempo écrit, mais l'écran
  ne l'expose pas encore.
- [MÉTHODE] Instrumental : la case « instrumental » (cochée par défaut). L'app l'envoie en prompt négatif (voix,
  chant, paroles, chœur), jamais dans la description. Ne pas écrire « no vocals » : le mot dessine ce qu'il nomme.
- [CHOIX] Case décochée : Lyria peut chanter, mais les mots sont les siens. Des paroles exactes demandent un modèle
  de musique à champ paroles (colonne « paroles » des Membres).
- [PIÈGE] Une durée envoyée à Lyria est ignorée ; l'app renvoie une note. Lyria 3 rend toujours la même longueur
  (lire la carte du modèle). Pour couvrir une vidéo plus longue, prendre un modèle à durée réglable.
- [CHOIX] Lyria 3 pour une nappe ou un jingle court, au plus bas prix par piste ; Lyria 3.5 quand la qualité prime
  et que la durée peut varier.
- [COÛT] Prix fixe par piste : chaque essai coûte autant. Écouter avant de relancer, et changer une seule chose du
  prompt par relance.
- [PIÈGE] Sans graine, chaque relance est une autre prise : garder la piste réussie.
- [CHOIX] Pas encore dans l'app : un champ « prompt négatif » libre à l'écran (le serveur l'accepte), le champ
  tempo, plusieurs prises par tir.

## Exemple

Brief : « une boucle calme pour le fond de ma Reel de recettes, sans voix ».

Ambiance : aucune. Description :

```
Warm acoustic lo-fi, soft brushed drums, muted nylon guitar, gentle upright bass, cozy kitchen mood,
relaxed and steady, clean mix with room for a voice-over, 84 BPM
```

Réglages : Lyria 3, case « instrumental » cochée. Écouter la piste dans le Montage sous la voix off ; si la guitare
couvre la voix, relancer avec « sparse arrangement » à la place de « gentle upright bass ».

## Erreurs fréquentes

- Écrire « no vocals » dans la description au lieu de cocher « instrumental » : le chant peut apparaître.
- Choisir l'ambiance « Hype » puis écrire « slow, 70 BPM » : deux tempos se contredisent.
- Promettre une durée précise avec Lyria : l'écran n'a pas de curseur pour elle, et une durée passée par l'API ne
  part pas.
- Coller des paroles dans la description : rien ne garantit qu'elles soient chantées telles quelles.
