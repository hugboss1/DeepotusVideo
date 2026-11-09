---
famille: voicebox
natures: [voix]
ids: [voicebox]
voies: [local]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; façade voice_providers (contrat Voicebox v0.5.0), voice_direction
description: À utiliser quand on veut une voix off gratuite, locale ou hors ligne avec Voicebox, qu'on choisit le fournisseur de voix (Auto, ElevenLabs ou Voicebox), qu'on fait un brouillon de narration avant la voix payante, qu'on crée ou choisit un profil de voix Voicebox (Kokoro, Chatterbox, voix clonée), ou que Voicebox est injoignable, lent ou sans profil.
---
## Aperçu

Voicebox est un serveur de voix **local et gratuit**, lancé à côté de l'app. Il n'a ni clé ni devis. Les voix sont
des **profils** créés dans l'application Voicebox (préréglage ou voix clonée) ; l'app ne fait que les lire. Le
moteur de synthèse vient du profil : Kokoro par défaut, Chatterbox pour le clonage sur une carte graphique récente.
Il sert les mêmes écrans que la voix ElevenLabs : Son & VFX › Voix off, l'onglet Voix off de Quick, le nœud
Voiceover du Studio, les Chapitres.

## Référence rapide

- [MÉTHODE] Le fournisseur se choisit dans Réglages › Fournisseurs par défaut › Fournisseur de voix. « Auto » prend
  ElevenLabs si sa clé est posée, sinon Voicebox s'il répond. Pour forcer Voicebox avec une clé ElevenLabs posée,
  le choisir explicitement.
- [PIÈGE] Voicebox réglé mais injoignable : le réglage retombe sur ElevenLabs si sa clé est posée, et la page
  Voix off repasse en mode payant (devis, deux clics). Quick et le nœud Voiceover, qui demandent Voicebox
  explicitement, sont refusés sans bascule. Lancer le serveur (Réglages › Fournisseurs par défaut donne la commande).
- [PIÈGE] Aucun profil : la génération échoue. En créer un dans l'application Voicebox (Voices), puis recharger la
  liste des voix.
- [CHOIX] Sans voix choisie, l'app prend un profil de la langue du texte, Kokoro de préférence, sinon le premier
  profil venu. Un identifiant de voix ElevenLabs hérité est ignoré au profit de ce profil.
- [PROMPT] Le texte ne porte que les mots à dire, dans la langue du profil. La langue envoyée est celle du
  sélecteur « Langue du texte » (français ou anglais).
- [PIÈGE] Voicebox ne lit aucune balise de jeu. Les balises connues (`[whispers]`, `[laughs]`…) sont retirées avant
  l'envoi ; un autre crochet part tel quel et sera lu.
- [CHOIX] Modèle et réglages (stabilité, vitesse…) sont fixés par l'application Voicebox : ceux de la page sont
  ignorés. Le ton se règle par le choix du profil et par la ponctuation.
- [COÛT] Gratuit : un seul clic, sans devis ni plafond. Le prix se paie en temps : la synthèse est asynchrone et
  bien plus lente sur processeur seul qu'avec une carte graphique, surtout en Chatterbox.
- [MÉTHODE] Brouillon de narration : caler le montage sur une voix Voicebox, puis générer la voix finale sur
  ElevenLabs avec le même texte. Le rythme changera : recaler les coupes après.
- [CHOIX] Clonage : se fait dans l'application Voicebox, pas par « Cloner cette voix » (qui crée une voix
  ElevenLabs). Ne cloner qu'une voix dont on a le droit.
- [CHOIX] Pas de jeu expressif, pas de balises, pas de dialogue à plusieurs voix : pour cela, la voix ElevenLabs
  (fiche ElevenLabs).

## Exemple

Brief : « une voix off française gratuite pour caler le montage de mon teaser, je paierai la vraie voix une fois les
coupes figées ».

Réglages : Réglages › Fournisseurs par défaut › Fournisseur de voix : Voicebox. Dans l'application Voicebox, un
profil français sur Kokoro. Son & VFX › Voix off : la voix « profil français », langue du texte Français, script :

```
Sous la surface, quelque chose remonte… Et cette fois, personne ne l'arrêtera.
```

Un clic, gratuit. La piste rejoint la Bibliothèque (sons) et se pose au Montage. Coupes figées : repasser le
fournisseur sur ElevenLabs et générer la version finale.

## Erreurs fréquentes

- Laisser des balises v3 dans le script en pensant qu'elles joueront : elles sont retirées, la lecture reste plate.
- Régler stabilité ou vitesse sur la page avec Voicebox actif : sans effet.
- Ne pas avoir de profil dans la langue du texte : l'app prend un autre profil, dont la voix n'est pas faite pour
  cette langue. Créer le profil de la langue.
- Lancer un long texte sur processeur seul sans prévoir le temps : tester d'abord une phrase.
