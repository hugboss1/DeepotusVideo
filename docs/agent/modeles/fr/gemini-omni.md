---
famille: gemini-omni
natures: [video_i2v, video_fl]
ids: [gemini-omni-flash, gemini-omni-flash-google]
voies: [fal, gemini]
releve: 2026-11-09
source: scenario-gemini-omni, scenario-video, scenario-moderation (scenario-labs/skills, MIT), registre fal_service
description: À utiliser quand on anime une image avec Gemini Omni Flash 1.1 (Google), par la voie fal ou par la clé Google, quand on hésite entre ces deux jumeaux, quand on remplace un Veo 3.1 Google arrêté, quand un rendu Google est refusé par la modération, ou quand on se demande pourquoi le clip arrive avec du son.
---
## Aperçu

Gemini Omni Flash anime une image de départ, avec une image de fin si on la donne. Il existe en deux jumeaux : la
voie fal (solde fal) et la voie Google (clé Google, crédits Google). C'est le même modèle des deux côtés. Il n'a ni
seed ni champ négatif. Il génère toujours une piste son, que l'app retire au téléchargement.

## Référence rapide

- [PROMPT] Avec une image de départ, décrire le mouvement qui la prolonge, pas une scène immobile. L'image fixe déjà le
  décor et le style.
- [PROMPT] Phrases complètes : une action, un mouvement de caméra nommé, la lumière. Les mots d'ambiance seuls ne
  survivent pas au rendu.
- [PIÈGE] Un clip tient un seul moment continu. Une histoire en plusieurs scènes dans un seul tir se brouille :
  découper en plans et monter ensuite.
- [PIÈGE] Sans champ négatif, une exclusion s'écrit dans le prompt, en positif quand c'est possible. Garder seulement
  « no subtitles, no on-screen text ».
- [PIÈGE] Sans seed, deux tirs du même prompt diffèrent toujours. Pour garder une prise, garder le fichier, pas la
  recette.
- [PIÈGE] Le modèle livre toujours une piste son ; il n'a pas d'interrupteur. L'app la retire au téléchargement :
  le clip arrive muet, le son se pose au Montage (voix off, musique, bruitages).
- [PROMPT] N'écrire aucune ligne de son ni de musique : elle serait payée puis retirée.
- [CHOIX] Voie fal ou voie Google : choisir selon la clé présente et le solde à utiliser. Les réglages et le rendu
  attendu sont les mêmes.
- [CHOIX] Les Veo 3.1 servis par la clé Google sont arrêtés ; ce jumeau Google les remplace.
- [CHOIX] Modération : la famille passe par le filtre de Google, le plus strict relevé (relevé 2026-11). Après un
  refus, essayer d'abord le jumeau de l'autre voie, puis une famille d'un autre fournisseur.
- [COÛT] Le devis de l'app chiffre un prix par résolution. Une source publique relevait au contraire un prix
  identique quelle que soit la résolution : à confirmer au premier tir en comparant devis et facture.
- [COÛT] Le brouillon le moins cher est une durée courte. La résolution supérieure est suréchantillonnée (relevé
  2026-11) : elle n'ajoute pas de détail réel.
- [MÉTHODE] Image de fin : la donner seulement pour atterrir sur une pose précise, avec le même cadre et le même sujet
  que l'image de départ.
- [CHOIX] Texte vers vidéo, références d'identité, édition et extension de vidéo existent chez Google mais pas encore
  dans l'app.

## Exemple

Brief : « Un portrait d'une cycliste en ville au coucher du soleil ; je veux une courte vidéo verticale où elle
démarre et s'éloigne ; le son de rue viendra au montage. »

Prompt :

```
The cyclist pushes off and rides slowly away down the street, her jacket moving in the wind. The camera holds
still at eye level and lets her shrink into the warm evening light. No subtitles, no on-screen text.
```

Réglages : image de départ = le portrait ; image de fin : non ; format vertical dans le champ format ; durée courte ;
résolution la plus basse ; voie selon la clé présente ; bruits de rue ajoutés au Montage.

## Erreurs fréquentes

- Raconter trois scènes dans un tir : le modèle n'en tient qu'une. Un tir par plan.
- Payer la résolution supérieure pour gagner du détail : elle serait suréchantillonnée (relevé 2026-11). Garder
  la plus basse sauf besoin de livraison.
- Réécrire trois fois un prompt refusé : passer d'abord au jumeau, puis à un autre fournisseur.
- Décrire le son voulu dans le prompt : la piste est retirée, le son se pose au Montage.
- Décrire de nouveau la tenue et le visage déjà visibles sur l'image : ces mots se battent contre l'image.
