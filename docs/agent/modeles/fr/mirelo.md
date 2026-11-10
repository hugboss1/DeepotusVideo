---
famille: mirelo
natures: [sfx_texte, sfx_video]
ids: [mirelo-1.6, mirelo-video]
voies: [fal]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; registre sfx_service (schémas fal relus le 12/10/2026)
description: À utiliser quand on génère un bruitage avec Mirelo SFX 1.6, sur description (plusieurs variantes d'un même son en un seul tir) ou depuis un clip vidéo du Montage pour obtenir la vidéo sonorisée, ou quand un bruitage Mirelo est refusé pour sa durée ou affiché « prix à mesurer ».
---
## Aperçu

Mirelo SFX 1.6 fait des effets sonores. **Mirelo SFX 1.6** part d'une description et rend toutes ses variations en
**un seul tir**. **Mirelo SFX 1.6 (vidéo sonorisée)** part d'un clip et rend la **vidéo avec son bruitage** :
l'app la range dans la Bibliothèque (Rendus) et en extrait la piste son, rangée dans les sons. Écrans : Son & VFX ›
SFX › « Générer des SFX » et le tiroir Sons du Montage › Générer (sélecteur « Modèle ») pour la description ; tiroir
Sons › Générer › « Depuis la vidéo » pour le clip vidéo sélectionné dans la timeline.

## Référence rapide

- [PROMPT] Description : un seul événement par son ; la source, la matière, l'action, l'espace (« a heavy wooden
  door creaks open slowly, stone hallway, faint echo »).
- [PROMPT] Des mots de son concrets (« creak », « thud », « crackle ») plutôt qu'une ambiance générale.
- [CHOIX] Plusieurs variantes d'un même son : Mirelo les rend en un seul tir (le nombre de variations part comme
  nombre d'échantillons). Utile pour choisir le meilleur de plusieurs pas, coups ou impacts.
- [PIÈGE] L'app envoie toujours le nombre d'échantillons voulu, même à un : sans lui, le fournisseur en produit
  et en facture plusieurs.
- [PIÈGE] Sans durée, c'est le défaut du modèle qui part. Régler la durée voulue ; elle est bornée à la plage de
  Membres.
- [CHOIX] Le curseur « Fidélité » du tiroir ne part pas chez Mirelo : seul le texte compte.
- [CHOIX] Vidéo : prendre Mirelo quand on veut la **vidéo déjà sonorisée** (un rendu à poser tel quel). Pour une
  piste son seule, calée sous le clip d'origine, un autre membre de la liste « Depuis la vidéo ».
- [PIÈGE] Vidéo : l'app envoie la durée du clip source. Un clip plus long que la plage de Membres est refusé
  avant tout tir, jamais coupé : couper le clip au plan utile d'abord.
- [PROMPT] Vidéo : la description est facultative ; l'image dicte le moment des sons. N'écrire que la nature d'un
  son que le modèle rate (« boots on wet cobblestones »).
- [CHOIX] Vidéo : pas de case « Garder la voix ». Ce que devient la parole d'origine dans la vidéo rendue est à
  confirmer : sur un plan parlé, préférer un membre qui garde la voix, ou mixer au Montage.
- [MÉTHODE] La vidéo sonorisée devient un rendu de la Bibliothèque (Rendus) : la poser au Montage par ce rendu ;
  la piste extraite sert si l'on préfère garder l'image d'origine.
- [COÛT] Les deux membres sont « prix à mesurer » : chiffrés à zéro au devis mais facturés par fal, le plafond ne
  les freine pas. Faire un seul essai court avant une série.
- [MÉTHODE] Hors ElevenLabs direct, le bouton s'arme en deux clics : le premier montre le devis, le second tire.
- [CHOIX] Pas encore dans l'app : graine, choix du format audio, plusieurs vidéos sonorisées en un tir.

## Exemple

Brief : « il me faut un grincement de porte de cave pour mon court métrage, je veux pouvoir choisir ».

Réglages : Montage › tiroir Sons (B) › Générer, modèle Mirelo SFX 1.6, durée de quelques secondes, Variations : 3.
Description :

```
a heavy wooden cellar door creaks open slowly on rusty hinges, stone stairwell, faint echo
```

Premier clic : le devis (prix à mesurer) ; second clic : un seul tir, trois sons. Les écouter, garder le meilleur
en favori, supprimer les autres.

## Erreurs fréquentes

- Lancer plusieurs tirs d'une variation pour comparer : un seul tir à plusieurs variations suffit.
- Envoyer un long clip à bruiter : il est refusé, le couper d'abord.
- Prendre la vidéo sonorisée d'un plan dialogué sans l'écouter : rien ne demande de garder la parole.
- Lancer une série en se fiant au devis à zéro : le prix réel est facturé par fal.
