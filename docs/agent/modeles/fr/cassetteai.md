---
famille: cassetteai
natures: [musique]
ids: [cassetteai]
voies: [fal]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; registre music_service, écran Musique de Son & VFX
description: À utiliser quand on veut une musique de fond très vite et pour presque rien avec CassetteAI : itérer sur une ambiance, essais rapides avant un modèle plus cher, piste instrumentale de quelques minutes, musique de fond pour une vidéo, facturation à la minute entamée.
---
## Aperçu

CassetteAI rend une piste instrumentale en quelques secondes de calcul, avec un curseur de durée. Pas de paroles,
pas de graine, pas de case instrumental. Il est facturé **à la minute de sortie entamée** : c'est le moyen le moins
cher d'essayer une ambiance avant de la confier à un modèle plus soigné.

## Référence rapide

- [COÛT] Minute entamée : une piste d'une minute et une seconde coûte deux minutes. Régler la durée juste sous une
  minute ronde quand c'est possible.
- [MÉTHODE] Itérer ici : trouver le genre, l'instrumentation et le tempo en plusieurs essais courts, puis rejouer la
  même description sur un modèle plus soigné pour la version finale.
- [PROMPT] Une ou deux phrases : genre, humeur, instruments, tempo. Préciser la place laissée à une voix off
  (« sparse, leaves room for narration ») quand la piste ira sous une voix.
- [PIÈGE] Une ambiance de l'écran porte déjà un tempo : ne pas en écrire un second dans la description.
- [PIÈGE] Des paroles saisies ne partent pas ; l'app renvoie une note. Pour une chanson, prendre un modèle à champ
  paroles.
- [PIÈGE] La durée a un plancher : le curseur ne descend pas sous le minimum du modèle (lire la carte du modèle).
  Pour un jingle très court, couper au Montage.
- [PIÈGE] Sans graine, chaque relance est une autre prise : garder la piste réussie.
- [CHOIX] Qualité de production en dessous des modèles plus chers (relevé 2026-11) : bon pour une maquette, une
  vidéo interne ou un fond discret ; écouter au casque avant une publication.
- [CHOIX] Pas encore dans l'app : plusieurs prises par tir, une piste chantée.

## Exemple

Brief : « je ne sais pas quel style mettre sous ma vidéo de voyage de deux minutes ; propose-moi des pistes ».

Réglages : CassetteAI, durée juste sous deux minutes. Trois tirs, une description chacun :

```
Upbeat acoustic travel pop, bright ukulele, hand claps, light percussion, sunny and carefree, 116 BPM
```

```
Cinematic indie, warm electric guitar swells, soft piano, steady kick, wide and nostalgic, 90 BPM
```

```
Chill electronic, mellow synth chords, soft side-chained pads, relaxed groove, 100 BPM
```

L'utilisateur choisit à l'écoute ; la description retenue part ensuite sur un modèle plus soigné pour la version
finale, si elle doit être publiée.

## Erreurs fréquentes

- Régler la durée à une minute et quelques secondes : la minute entamée est facturée en entier.
- Attendre une voix ou des paroles : l'app ne lui envoie que la description, pour une piste instrumentale.
- Publier une maquette sans réécoute : la production est plus simple que celle des modèles plus chers.
