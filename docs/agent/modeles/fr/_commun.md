---
famille: _commun
releve: 2026-11-09
source: scenario-image, scenario-video, scenario-consistency, scenario-moderation, scenario-text-overlay, scenario-audio (scenario-labs/skills, MIT)
description: À utiliser quand on lit n'importe quelle fiche modèle : règles d'écriture de prompt, de références, de texte, de son, de cohérence et de modération valables pour toutes les familles d'image, de vidéo, de son et de 3D.
---
## Aperçu

Une fiche de famille peut préciser ou contredire ces règles : elle gagne alors.
Les paramètres d'un modèle (durées, formats, prix) se lisent dans le bloc « Membres », jamais dans le texte.

## Référence rapide

- [PROMPT] Écrire en phrases complètes, pas en liste de mots-clés.
- [PROMPT] Un mot écrit dessine ce qu'il nomme : « no gray » fait apparaître du gris. Formuler en positif (« plain
  white background ») ou passer par le champ négatif quand le membre en a un.
- [PROMPT] Le format se règle dans le champ prévu, jamais dans le texte : un ratio écrit en prose donne des bandes
  noires ou un recadrage.
- [PROMPT] Un fond transparent se demande par le paramètre ou par un détourage ; écrit dans le prompt, il sort opaque.
- [PROMPT] Prompt en anglais. Texte dans l'image : le citer entre guillemets dans sa langue, accents compris, dire
  son rôle et sa place, finir par « no other text ».
- [PIÈGE] Un prix, une mention légale, un numéro ou le logo existant d'une marque n'est **jamais** généré : on
  l'incruste ensuite (Templates, Montage, Card Forge), un chiffre généré peut sortir faux. Un logo neuf se dessine
  (fiche Recraft).
- [MÉTHODE] Retouche : « change only X », puis la liste de ce qui doit rester. Une seule modification par passe ; la
  liste se répète à chaque passe.
- [MÉTHODE] Références : donner à chaque image un rôle selon sa position (« image 1 : identité du visage, image 2 :
  tenue »). Une référence sans rôle est souvent ignorée.
- [MÉTHODE] Cohérence : une seule référence forte et validée sert d'entrée à **chaque** image du jeu. Ne jamais
  enchaîner une sortie sur la précédente : la dérive s'additionne.
- [MÉTHODE] Base + delta : un texte de base identique d'une image à l'autre décrit tout ce qui ne change pas ; seule la
  dernière clause change.
- [PIÈGE] Le seed ne transporte pas une identité d'un prompt à un autre, et « same as before » n'a aucune mémoire.
- [MÉTHODE] Continuité et identité ne se confondent pas : la dernière image d'un plan gardé peut ouvrir le plan
  suivant (raccord), mais le personnage se vérifie toujours contre l'image validée, jamais contre la sortie d'avant.
- [MÉTHODE] Vidéo depuis une image : ne décrire que le mouvement, pas ce qui est déjà visible. Une caméra et une action
  par plan ; des repères de temps quand il y a plusieurs temps.
- [PIÈGE] Tourner autour d'un sujet vu sur une seule photo : le modèle invente les faces cachées. Limiter l'angle,
  ou donner une image de fin qui montre la face voulue.
- [MÉTHODE] Image fixe d'abord, approuvée, puis animation depuis cette image. On relance depuis l'image approuvée,
  jamais depuis une sortie qui a dérivé.
- [PROMPT] Son : nommer les sons en positif. « No music » fait souvent refuser la piste ; pour couper l'audio, utiliser
  l'interrupteur du membre.
- [COÛT] Brouillon d'abord quand le membre le permet (palier bas, basse résolution, aperçu), à la durée finale ; le
  final ensuite.
- [CHOIX] Modération : en cas de refus, changer d'abord de **fournisseur** à coût voisin (le jumeau de voie compte),
  car une même famille partage le même filtre. Puis une seule réécriture honnête, puis arrêt.
- [COÛT] Un rendu vidéo refusé après génération peut être facturé.

## Exemple

Brief : « trois vues du même personnage pour une planche ». On génère la vue de face, on la valide, puis on écrit
pour chaque autre vue : « Same character as image 1: short black hair, round glasses, yellow raincoat with two
pockets, green boots, plain unlettered studio background. Change only the view: left profile, nose pointing left. »
Les deux autres vues reprennent la même phrase de base, seule la fin change, et partent toutes de la vue de face
validée.

## Erreurs fréquentes

- Recopier dans le prompt un prix ou un slogan exact : il sort mal orthographié. Le poser en incrustation.
- Corriger trois choses à la fois en retouche : le modèle en change d'autres. Une à la fois.
