---
famille: stable-audio
natures: [musique, sfx_texte]
ids: [stable-audio-25, stable-audio-3, stable-audio-3-sfx]
voies: [fal]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; registres music_service et sfx_service, écrans Musique et SFX de Son & VFX
description: À utiliser quand on veut une musique instrumentale longue ou une nappe avec Stable Audio (Stability AI) : Stable Audio 2.5 ou 3, piste qui couvre toute une vidéo, ambiance, drone, texture sonore, durée réglée à la seconde, graine reproductible ; ou un bruitage sur description avec Stable Audio 3 SFX (impact, whoosh, ambiance de lieu) dans l'écran SFX.
---
## Aperçu

Stable Audio rend de l'audio **instrumental** depuis une description : jamais de voix chantée, jamais de paroles.
Deux membres servent l'écran Musique (Son & VFX) avec un curseur de durée et une graine. Le troisième,
Stable Audio 3 SFX, sert l'écran SFX : un bruitage depuis une description, sans graine. Les deux membres de musique
sont facturés **par piste**, quelle que soit la durée réglée.

## Référence rapide

- [CHOIX] Piste qui doit couvrir toute la vidéo : régler la durée à la longueur du montage. Stable Audio 3 va plus
  loin que 2.5 (lire la plage sur la carte du modèle).
- [COÛT] Prix par piste : une piste longue coûte autant qu'une courte. Générer directement à la durée finale plutôt
  que d'assembler des morceaux.
- [PROMPT] Musique : genre, humeur, instrumentation, texture, tempo, en une ou deux phrases. Les textures marchent
  bien : « slow evolving pad », « granular shimmer », « sub bass drone ».
- [PROMPT] Évolution : la nommer en mots simples (« builds slowly, peaks near the end »). Aucun champ de structure :
  un minutage précis n'est pas garanti.
- [PIÈGE] Des paroles saisies ne partent pas : l'app renvoie une note. Pour une chanson, prendre un modèle à champ
  paroles.
- [PIÈGE] Pas de case « instrumental » ici : le membre ne chante pas. Écrire « no vocals » est inutile et peut nuire.
- [PIÈGE] Une ambiance de l'écran porte déjà un tempo : ne pas en écrire un second.
- [MÉTHODE] Graine : en fixer une dès le premier essai. Même graine et mêmes réglages redonnent la même piste ;
  changer la graine seule donne une variante du même prompt.
- [CHOIX] Pas encore dans l'app : le prompt négatif de Stable Audio 3 à l'écran (le serveur l'accepte), plusieurs
  prises par tir, la reprise d'un audio existant.
- [PROMPT] SFX : un seul événement par tir, dans l'ordre source, matière, action, espace, intensité : « heavy oak
  door slams shut in a stone hallway, short tail ». Des mots physiques (« hollow », « muffled », « punchy ») plutôt
  que des humeurs.
- [PIÈGE] SFX sans durée réglée : le son part à la durée par défaut du modèle, bien plus longue qu'un impact. Régler
  la durée à l'événement.
- [PIÈGE] L'écran SFX demande deux variations, mais Stable Audio 3 SFX en rend une par tir. Relancer pour une
  variante.
- [COÛT] Stable Audio 3 SFX est « prix à mesurer » : le devis vaut zéro et le plafond ne le freine pas, mais fal le
  facture. L'essayer sur un seul son avant une série.
- [CHOIX] Stable Audio 3 SFX convient aux ambiances de lieu et aux sons de quelques secondes ; pour un impact très
  bref, comparer avec un autre modèle de la nature SFX sur description.

## Exemple

Brief : « une nappe sombre sous mon court-métrage de 3 minutes sur les fonds marins, sans voix ».

Réglages : Stable Audio 3, durée réglée sur la longueur du montage, graine fixée. Description :

```
Dark ambient underwater score, slow evolving synth pad, deep sub bass pulses, distant metallic pings,
soft granular shimmer, builds slowly and fades out at the end, 60 BPM
```

Ambiance : aucune (le tempo est déjà écrit). Si la piste est trop chargée, garder la graine et retirer « distant
metallic pings » : seule cette partie change.

## Erreurs fréquentes

- Chercher une voix chantée chez Stable Audio : il n'en fait pas.
- Assembler plusieurs pistes courtes pour couvrir une vidéo : une piste longue coûte le même prix.
- Laisser la durée vide pour un bruitage : le fichier sort bien plus long que l'événement.
- Mettre plusieurs sons dans un prompt SFX (« door slam then footsteps ») : un événement par tir.
