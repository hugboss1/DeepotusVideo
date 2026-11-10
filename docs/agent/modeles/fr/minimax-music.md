---
famille: minimax-music
natures: [musique]
ids: [minimax-music-26, minimax-music-20, minimax-music-3]
voies: [fal]
releve: 2026-11-09
source: scenario-minimax-music, scenario-audio (scenario-labs/skills, MIT) ; registre music_service, écran Musique de Son & VFX
description: À utiliser quand on veut une vraie chanson chantée avec MiniMax Music (2.6, 2.0 ou 3) : couplets et refrains, paroles écrites ou écrites par le modèle, générique, hymne de marque, jingle chanté, chanson pour un clip, balises [Verse] [Chorus] [Bridge], paroles exigées refusées, instrumental MiniMax, chanson de plusieurs minutes.
---
## Aperçu

MiniMax Music chante une chanson complète à partir de deux champs : la description (le style) et les paroles (les
mots). Les trois membres ne se règlent pas pareil :
- **2.6** : paroles facultatives et case « instrumental » ; durée choisie par le modèle ; prix par piste.
- **2.0** : paroles **obligatoires** ; pas d'instrumental ; durée choisie par le modèle ; prix par piste.
- **3** : paroles **obligatoires** ; curseur de durée et graine ; prix à la seconde de la durée demandée.

## Référence rapide

- [PROMPT] La description porte le style seulement : genre, humeur, tempo, tonalité, timbre de la voix
  (« warm female alto, close-mic »), instruments, production. Jamais de paroles dedans : le modèle décrirait au lieu
  de chanter.
- [PROMPT] Les paroles portent les mots seulement, une balise de section par ligne. L'éditeur ajoute couplet,
  refrain et pont ; l'app les envoie en `[Verse]`, `[Chorus]`, `[Bridge]` (et `[Intro]`, `[Outro]`). Une autre
  balise (`[Pre Chorus]`, `[Inst]`, `[Solo]`) part telle quelle.
- [PROMPT] Deux à quatre lignes par section. Un saut de ligne = une nouvelle ligne chantée ; une ligne vide entre
  sections = une respiration (source publique, relevé 2026-11).
- [PROMPT] Entre parenthèses, une indication de jeu, pas un mot chanté : « (whispered) », « (belted) ».
- [PROMPT] Finir par `[Outro]` : sans elle, la chanson peut couper net.
- [PROMPT] L'anglais et le mandarin chantent le plus régulièrement (source publique, relevé 2026-11). Le français
  marche, mais écouter la diction avant de valider.
- [PIÈGE] 2.0 et 3 refusent, avant toute dépense, des paroles trop courtes : les balises ne comptent pas, seuls les
  mots chantés comptent.
- [MÉTHODE] 2.6 : case « instrumental » cochée par défaut ; l'éditeur de paroles n'apparaît qu'une fois la case
  décochée. Décochée et paroles vides : le modèle écrit lui-même les paroles depuis la description.
- [PIÈGE] Paroles laissées vides sur 2.6 en espérant un instrumental : il chante des mots inventés. Cocher la case.
- [MÉTHODE] Le bouton « squelette persona » pose une trame (couplet, refrain, pont) nourrie par l'espace de marque :
  un point de départ, à réécrire avant le tir.
- [COÛT] 3 est facturé à la durée demandée, pas à la durée rendue : régler le curseur sur la longueur utile.
- [CHOIX] Chanson courte au moindre prix : 2.0. Instrumental ou paroles écrites par le modèle : 2.6. Longueur
  maîtrisée ou prise reproductible (graine) : 3.
- [PIÈGE] La graine de 3 ne redonne la même chanson qu'à réglages identiques ; changer un mot donne une autre prise.
- [CHOIX] Pas encore dans l'app : la reprise d'un morceau existant dans un autre style (cover), l'interrupteur
  instrumental de 3, le choix du format de sortie.

## Exemple

Brief : « un jingle chanté de 30 secondes pour ma boulangerie, joyeux, en anglais ».

Réglages : MiniMax Music 3, durée sur la longueur voulue, une graine fixée (un entier quelconque) dès le premier essai. Description :

```
Bright acoustic pop jingle, 112 BPM, C major, cheerful female lead with a light doubled chorus, ukulele,
hand claps, glockenspiel, clean radio-ready mix
```

Paroles :

```
[Verse]
Golden crust at early light
Warm bread waiting, baked just right

[Chorus]
(belted) Come on in, the oven's on
Fresh every morning, sing along

[Outro]
Fresh every morning
```

Écouter. Si la voix plaît, garder la graine : une relance identique la redonne ; changer de graine pour une autre
prise.

## Erreurs fréquentes

- Écrire « happy pop song about bread » dans les paroles : il le chante mot pour mot.
- Mettre les paroles dans la description : la chanson décrit au lieu de chanter.
- Choisir 2.0 pour un instrumental : il exige des paroles et n'a pas de case instrumental.
- Laisser le curseur de 3 bien au-delà du besoin : la facture suit la durée demandée.
