---
famille: elevenlabs
natures: [voix, sfx_texte, musique]
ids: [eleven_multilingual_v2, eleven_v3, eleven_flash_v2_5, elevenlabs-direct, elevenlabs-v2-fal, elevenlabs-music-2.5]
voies: [elevenlabs, fal]
releve: 2026-11-09
source: scenario-elevenlabs, scenario-audio (scenario-labs/skills, MIT) ; registres elevenlabs_service, voice_direction, sfx_service, music_service
description: À utiliser quand on fait une voix off ou une narration avec ElevenLabs (Multilingual v2, Eleven v3, Flash v2.5), qu'on dirige le jeu par balises ([whispers], [laughs], [excited]), qu'on règle stabilité, similarité ou vitesse, qu'une balise est lue à voix haute, qu'on génère un bruitage ElevenLabs SFX (direct ou via fal) ou une musique ElevenLabs Music 2.5, ou qu'on hésite entre qualité, expressivité et coût d'une voix.
---
## Aperçu

ElevenLabs sert trois natures. La **voix** (Multilingual v2 par défaut, Eleven v3 expressif, Flash v2.5 rapide et
moins cher) passe par la clé ElevenLabs. Le **bruitage** sur description existe en direct (clé ElevenLabs) et en
jumeau via fal. La **musique** (Music 2.5) passe par fal. Écrans : Son & VFX › Voix off (aussi l'onglet Voix off de
Quick et le nœud Voiceover du Studio) ; Son & VFX › SFX › « Générer des SFX » et le tiroir Sons du Montage ›
Générer ; Son & VFX › Musique › Générer.

## Référence rapide

- [PROMPT] Voix : le script ne porte **que** les mots à dire, dans leur langue. « Say this angrily » écrit dans le
  texte peut être prononcé. Le jeu passe par les balises (v3) ou par les réglages.
- [CHOIX] Eleven v3 est le seul membre qui lit les balises en ligne (`[whispers]`, `[sighs]`, `[excited]`…). Sur
  Multilingual v2 et Flash v2.5, l'app retire les balises connues avant l'envoi et le dit dans la note de fin.
- [PIÈGE] Seules les balises de la palette sont retirées. Un autre crochet (« [Scène 2] ») part tel quel et sera lu.
  Sur v3, une balise hors palette part aussi, avec une note : elle peut être lue à voix haute.
- [PIÈGE] Une balise est une demande, pas une garantie : deux tirs identiques peuvent jouer différemment. Écouter
  avant de valider, relancer si la balise a été ignorée.
- [PROMPT] Pauses : par la ponctuation (points de suspension, phrase courte). v3 ne lit pas les balises de pause SSML.
- [CHOIX] Eleven v3 ne règle que la stabilité, en trois crans : Créative (plus de jeu, suit mieux les balises),
  Naturelle, Robuste (plus stable, répond moins aux balises). Multilingual v2 et Flash v2.5 ont les curseurs
  Stabilité, Similarité et Vitesse.
- [CHOIX] Narration posée, qualité : Multilingual v2. Jeu expressif ou émotions : Eleven v3. Volume, brouillon,
  textes longs : Flash v2.5.
- [PIÈGE] « Langue du texte » (français ou anglais) choisit la voix par défaut de la langue ; elle ne traduit rien
  et n'est pas envoyée au modèle. Écrire le texte dans la langue voulue et choisir une voix qui la parle.
- [MÉTHODE] Un texte plus long que la limite par requête (colonne « car. max ») est découpé aux fins de phrase,
  puis recollé. Sur Son & VFX › Voix off et Quick, le champ s'arrête à cette limite ; les narrations longues passent
  par les Chapitres, qui restent au modèle par défaut de l'app.
- [COÛT] La voix se paie au caractère envoyé, balises comprises (colonne prix, par 1 000 caractères). Premier clic :
  le devis ; second clic : la synthèse.
- [CHOIX] « Cloner cette voix » (bibliothèque de voix) crée une voix ElevenLabs à partir de prises : ne cloner
  qu'une voix dont on a le droit.
- [PROMPT] Bruitage : nommer la source, la matière, l'action et l'espace (« a ceramic mug set down on a wooden
  table, small kitchen, close and dry »). Un seul événement par son ; une variante = une autre génération.
- [PROMPT] Une acoustique sèche se dit en positif (« dry, close-miked »), pas par « no reverb ».
- [CHOIX] Bruitage : « Fidélité » haute colle au texte, basse laisse plus de liberté. Durée : auto (le modèle
  choisit) ou précise, bornée à la plage de Membres.
- [CHOIX] Sans clé ElevenLabs mais avec la clé fal, l'app sert le jumeau fal (« via fal ») avec la même
  description. Après un refus de modération, essayer l'autre voie avant de réécrire.
- [COÛT] Bruitage direct : chiffré à la seconde demandée et par variation ; en durée auto, le coût suit la durée
  rendue. Le jumeau fal est « prix à mesurer » : chiffré à zéro, le plafond ne le freine pas. « Générer des SFX »
  de Son & VFX tire toujours deux variations.
- [PROMPT] Musique : genre, humeur, instruments et tempo dans la description ; la durée dans son champ. Une
  vignette d'ambiance porte déjà un tempo : ne pas en écrire un second.
- [CHOIX] Musique : l'interrupteur « instrumental » est la seule façon fiable d'avoir une piste sans voix.
  Interrupteur coupé, le modèle peut chanter, mais le champ paroles est ignoré (note) : on ne choisit pas les mots.
- [COÛT] Music 2.5 se facture à la minute entamée : une piste d'une minute et deux secondes paie deux minutes.
- [MÉTHODE] Musique : même graine et mêmes réglages redonnent la même piste. Changer la graine pour une autre prise.
- [CHOIX] Pas encore dans l'app : code de langue, graine de voix, dialogue à plusieurs voix, doublage,
  transformation de voix, son bouclable (`loop`), plan de musique par sections, paroles imposées à Music 2.5.

## Exemple

Brief : « voix off française de quelques secondes pour une pub de café : un chuchotement complice, puis un ton
enjoué ».

Réglages : Son & VFX › Voix off, modèle Eleven v3, stabilité Créative, langue du texte Français, une voix
française de la bibliothèque. Script (les mots restent en français, les balises en anglais) :

```
[whispers] Chut… le café est prêt. [excited] Et cette fois, il est vraiment bon !
```

Premier clic : le devis s'affiche ; second clic : la synthèse. Écouter : si le chuchotement est ignoré, relancer
tel quel. Pour une lecture plus sage, passer en Multilingual v2 : les balises sont retirées et le ton passe par la
stabilité.

## Erreurs fréquentes

- Écrire la consigne de ton dans le script (« (angry) ») : elle est lue. Une balise de la palette sur v3, sinon
  la stabilité.
- Garder des balises en passant à Multilingual v2 ou Flash v2.5, puis s'étonner d'une lecture plate : elles ont
  été retirées.
- Mettre plusieurs bruits dans une description (« porte, pas, puis cri ») : un événement par son, assemblés au
  Montage.
- Demander une chanson avec paroles à Music 2.5 : les paroles ne partent pas. Prendre un membre de musique à
  colonne « paroles ».
- Choisir une durée de musique juste au-dessus d'une minute ronde : la minute entamée est payée.
