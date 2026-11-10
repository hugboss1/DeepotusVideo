---
famille: mureka
natures: [musique]
ids: [mureka-9.5]
voies: [fal]
releve: 2026-11-09
source: scenario-minimax-music, scenario-audio (scenario-labs/skills, MIT) ; registre music_service, écran Musique de Son & VFX
description: À utiliser quand on veut une chanson complète et soignée avec Mureka 9.5 : avec ses propres paroles ou sur une simple description, chanson de marque, titre pour un clip, paroles longues, balises [Verse] [Chorus], différence de prix avec ou sans paroles.
---
## Aperçu

Mureka 9.5 rend une chanson complète, chantée. Deux façons de la demander :
- **avec vos paroles** : il chante vos mots ;
- **sur description seule** : il écrit lui-même les paroles.

Le prix change selon le cas : la demande **avec paroles coûte moins cher** que la description seule. La carte du
modèle et le devis en tiennent compte ; le bloc Membres affiche le prix sans paroles. Pas de curseur de durée, pas
de graine, pas de case instrumental.

## Référence rapide

- [COÛT] Écrire les paroles, même courtes, fait baisser le prix du tir. La description seule est le cas le plus cher.
- [PROMPT] La description porte le style seulement : genre, humeur, tempo, timbre de voix, instruments, production.
  Jamais de paroles dedans.
- [PROMPT] Paroles : l'éditeur ajoute couplet, refrain et pont ; l'app les envoie en `[Verse]`, `[Chorus]`,
  `[Bridge]` (et `[Intro]`, `[Outro]`). Une autre balise part telle quelle.
- [PROMPT] Deux à quatre lignes par section, une ligne vide entre sections, `[Outro]` en dernier pour une fin
  propre. Indications de jeu entre parenthèses : « (softly) ».
- [PIÈGE] Les balises seules ne comptent pas comme des paroles : un éditeur qui ne contient que des sections vides
  part comme une description seule, au prix fort.
- [PIÈGE] Pas d'interrupteur instrumental dans l'app : attendre une chanson chantée (piste sans voix possible côté
  fournisseur : à confirmer). Pour une piste sans voix, prendre un modèle avec la case « instrumental ».
- [PIÈGE] Durée choisie par le modèle : une durée demandée est ignorée. Couper ou boucler au Montage.
- [PIÈGE] Sans graine, chaque relance est une nouvelle chanson : garder la prise réussie.
- [CHOIX] Paroles longues : l'app laisse partir chez Mureka des textes plus longs que chez les autres modèles de
  chanson. Au-delà de sa limite, le texte est coupé à la fin, sans avertissement.
- [MÉTHODE] Tester la mélodie et la structure sur un modèle de chanson moins cher, puis faire la version finale sur
  Mureka avec les mêmes paroles.
- [CHOIX] Pas encore dans l'app : reprise d'un morceau existant, choix de la durée, instrumental.

## Exemple

Brief : « une chanson indie-folk pour la vidéo anniversaire de notre association, avec nos paroles ».

Réglages : Mureka 9.5. Description :

```
Warm indie folk, 96 BPM, G major, gentle male lead with group harmonies on the chorus, fingerpicked acoustic
guitar, soft kick, tambourine, mandolin, intimate and hopeful
```

Paroles (ici en français, chantées telles quelles) :

```
[Verse]
Dix ans déjà, des mains qui se tendent
Des matins froids, des cafés qui attendent

[Chorus]
(all together) On est là, encore là
Et la route continue sous nos pas

[Outro]
Encore là
```

Écouter la diction du français ligne par ligne ; si un mot sort mal, le réécrire plus simple plutôt que d'ajouter
une consigne dans la description.

## Erreurs fréquentes

- Laisser les paroles vides « pour voir » : c'est le tir le plus cher.
- Chercher un instrumental chez Mureka : l'app n'a pas de case pour le demander.
- Copier le style dans les paroles (« folk song, warm ») : il le chante.
