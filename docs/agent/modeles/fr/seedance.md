---
famille: seedance
natures: [video_i2v, video_fl]
ids: [seedance-v1-pro, seedance-2, seedance-2-fast, seedance-2.5]
voies: [fal]
releve: 2026-11-09
source: scenario-seedance, scenario-seedance-drafts, scenario-seedance-storyboard, scenario-seedance-music-video (scenario-labs/skills, MIT) ; registre fal_service
description: À utiliser quand on anime une image avec Seedance (ByteDance) : Seedance 2.5, 2.0, 2.0 Fast ou 1.0 Pro, image vers vidéo ou plan début + fin, enchaînement de plans par poses, chorégraphie, danse, combat, clip musical, refus de modération ByteDance, choix du membre Seedance le moins cher pour un brouillon.
---
## Aperçu

Seedance anime une image de départ, avec ou sans image de fin. Le modèle n'a ni champ caméra ni masque : la caméra
s'écrit dans le prompt. L'app coupe toujours la piste son et envoie la durée en secondes entières. Seedance 2.5 est
le membre par défaut ; Seedance 1.0 Pro est le seul membre qui accepte un seed.

## Référence rapide

- [PROMPT] Un mouvement de caméra dominant et une action par plan. Une liste d'actions sans repère fait couper le
  modèle à l'intérieur du clip.
- [PROMPT] Plusieurs temps : des battements horodatés, un par temps, le dernier fini avant la fin de la durée, et la
  mention « one continuous take ».
- [PROMPT] Chorégraphie et action : des verbes et des poses d'entrée et de sortie, jamais des adjectifs
  (« dances energetically » ne donne rien). Écrire l'action comme de la physique : approche, contact, poussée,
  retour ; les tissus suivent avec un temps de retard.
- [PROMPT] Nommer la position à l'écran en plus de la pose (« on the left third, facing right ») : une pose en miroir
  casse le raccord.
- [PROMPT] L'app coupe le son : n'écrire aucune ligne de son ni de musique. La musique se pose au Montage.
- [PIÈGE] Seedance 2.5 n'a pas de champ de format : le cadre suit l'image de départ. Préparer l'image au format de
  livraison avant le tir.
- [PIÈGE] Le format livré tombe souvent près du format demandé, pas dessus. Mesurer le fichier et recadrer au
  format de livraison.
- [PIÈGE] La durée livrée peut différer de la durée demandée. Lire la durée réelle avant de caler un montage.
- [PIÈGE] Une durée absente de la liste du membre est ramenée à la plus proche, avec une note. Lire les durées
  permises dans Membres.
- [MÉTHODE] Plans enchaînés : chaque plan finit dans la pose où commence le suivant. N plans demandent N + 1 images
  de bord ; le plan N part de l'image N et finit sur l'image N + 1.
- [MÉTHODE] Images de bord : un prompt identique d'une image à l'autre, seule la clause de pose change, même
  cadrage. Revoir le jeu complet avant d'animer : chaque dérive de costume tombe sur une coupe.
- [PIÈGE] À une jointure, la taille de plan ne peut pas changer : c'est la même image des deux côtés. Changer
  d'échelle par un mouvement de caméra dans le plan.
- [PIÈGE] Un personnage qui sort du cadre et revient dans le même plan revient souvent changé. Placer sorties et
  retours sur une image de bord.
- [CHOIX] Pas de seed sur 2.0 et 2.5 : chaque relance est une nouvelle prise. Garder la prise réussie ; relancer en
  plus haute résolution donne une autre prise.
- [COÛT] L'écart de prix entre membres est large pour un même plan : le lire dans Membres. Comparer le devis de
  deux membres avant une série.
- [COÛT] Brouillon : 2.5 au palier bas ou 2.0 Fast, à la durée finale. Il valide le prompt et le mouvement ; le
  final, au palier haut, est une nouvelle prise.
- [COÛT] Seedance 2.5 est facturé aux jetons : le devis est une estimation, la facture peut s'en écarter. Couper
  le son ne change pas son prix.
- [CHOIX] Avec une image de fin, Seedance 1.0 Pro est servi par sa variante Lite, pas par Pro.
- [CHOIX] Modération : un refus du rendu vient du filtre de la famille, et un autre Seedance refuse pareil.
  Changer de fournisseur, même prompt. Un personnage pris pour une œuvre protégée est bloqué quelle que soit la
  formulation ; les mots d'arme ou de violence bloquent même en dessin animé.
- [CHOIX] Pas encore dans l'app : images, vidéos ou sons de référence, brouillon finalisable sans régénérer,
  texte vers vidéo, extension.
- [MÉTHODE] Revue d'une prise : planche contact du clip entier à deux images par seconde, puis gros plans là où ça
  casse (mains rapides, cheveux longs en rotation, visage), puis lecture à vitesse réelle.

## Exemple

Brief : « une Reel 9:16 de la danseuse de mon affiche : elle tourne sur elle-même puis salue, fond de rue au
crépuscule ».

Image de départ : l'affiche recadrée en 9:16, danseuse de face au centre. Prompt :

```
One continuous take. Medium-wide shot, slow dolly-in from street level. First half: she pivots on her left foot,
a full turn, her skirt swinging out and settling a beat after her body stops. Second half: she ends facing the
camera in the center third and bows, right hand on her chest. Street lamps stay steady, no subtitles, no
on-screen text.
```

Réglages : Seedance 2.5, palier bas pour la prise d'essai, durée courte, image de fin : non. Une fois la prise
validée, même prompt au palier haut : c'est une nouvelle prise, à revoir comme la première.

## Erreurs fréquentes

- Écrire « 9:16 » dans le prompt de Seedance 2.5 : le format ne vient que de l'image de départ.
- Demander une danse « énergique » : sans verbes ni poses de bord, le mouvement reste flou.
- Enchaîner un plan sur la sortie précédente sans revoir la dernière image : écrire le prompt suivant d'après
  l'image réelle (positions, orientation), pas d'après le plan prévu.
- Relancer à l'identique après un refus de modération : le filtre bloque à nouveau, et un rendu refusé peut être
  facturé.
