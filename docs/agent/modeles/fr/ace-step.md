---
famille: ace-step
natures: [musique]
ids: [ace-step]
voies: [fal]
releve: 2026-11-09
source: scenario-ace-step, scenario-audio (scenario-labs/skills, MIT) ; registre music_service, écran Musique de Son & VFX
description: À utiliser quand on veut une chanson avec paroles au plus bas prix avec ACE-Step : chanson chantée ou instrumental, durée réglable, graine reproductible, balises [verse] [chorus] [bridge] [inst], genres en mots-clés, maquette de chanson, essais nombreux avant un modèle plus cher.
---
## Aperçu

ACE-Step (première génération, servie par fal) chante des paroles structurées ou joue un instrumental. Il n'a **pas
de champ description** : l'app envoie la description comme une liste de **tags** (genres, humeur, instruments). Il
prend une durée réglable et une graine ; il est facturé à la seconde de la durée demandée, ce qui en fait le membre
le moins cher pour itérer.

## Référence rapide

- [PROMPT] Description = des mots-clés séparés par des virgules, pas des phrases : « synth-pop, upbeat, female
  vocals, 80s drum machine, bright, 120 BPM ». Cette fiche contredit ici la règle des phrases complètes.
- [PROMPT] Le timbre de voix se dit aussi en tags : « male vocals », « soft female vocals », « choir ».
- [MÉTHODE] Case « instrumental » cochée (défaut) : l'app envoie `[inst]` et rien d'autre ; l'éditeur de paroles est
  caché. Décocher la case pour écrire des paroles.
- [PIÈGE] Case décochée mais paroles vides : ACE-Step joue quand même un instrumental (`[inst]`). Il n'écrit pas de
  paroles lui-même.
- [PROMPT] Paroles : l'éditeur ajoute couplet, refrain et pont ; l'app les convertit en balises minuscules
  `[verse]`, `[chorus]`, `[bridge]` (et `[intro]`, `[outro]`). Une balise inconnue part telle quelle.
- [PROMPT] Sections courtes, deux à quatre lignes ; une ligne vide entre sections. Finir par `[outro]` pour une fin
  propre.
- [COÛT] Facturé à la seconde de la durée réglée, pas de la durée rendue : régler le curseur sur la longueur utile.
- [MÉTHODE] Maquette : régler le texte, la structure et le tempo sur ACE-Step, à durée courte ; passer à un modèle
  plus soigné seulement quand la chanson tient.
- [MÉTHODE] Graine : en fixer une dès le premier essai. Même graine et mêmes réglages redonnent la même prise ;
  changer un mot des paroles donne une autre prise.
- [PIÈGE] La qualité de voix et la diction sont en dessous des modèles plus chers : écouter chaque ligne avant de
  publier.
- [CHOIX] Pas encore dans l'app : ACE-Step 1.5 et ses modes d'édition (reprise dans un autre style, réécriture d'une
  section, ajout d'une piste, séparation), les champs tempo et tonalité dédiés, plusieurs prises par tir.

## Exemple

Brief : « une petite chanson rigolote sur mon chat pour une vidéo TikTok, en anglais, pas chère, je veux tester
plusieurs versions ».

Réglages : ACE-Step, case « instrumental » décochée, durée courte, graine fixée. Description :

```
funk, playful, male vocals, slap bass, clavinet, tight drums, horn stabs, 105 BPM
```

Paroles :

```
[verse]
He knocks the glass right off the shelf
Then blames the dog and licks his paw

[chorus]
Mister Whiskers, king of the night
Sleeps all day, then starts a fight

[outro]
King of the night
```

Pour une autre version, changer seulement la graine ; pour une autre ambiance, changer seulement les tags.

## Erreurs fréquentes

- Écrire la description en longues phrases : les tags deviennent flous.
- Recocher « instrumental » après avoir écrit des paroles : l'éditeur se cache et les paroles ne partent pas.
- Attendre des paroles écrites par le modèle avec un éditeur vide : il joue un instrumental.
- Régler la durée au maximum « pour voir » : la facture suit la durée demandée.
