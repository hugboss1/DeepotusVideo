---
famille: sam3-objets
natures: [objets3d]
ids: [sam-3-3d-objects, sam-3-3d-body]
voies: [fal]
releve: 2026-11-09
source: scenario-walkable-room, scenario-3d (scenario-labs/skills, MIT) ; registres storyboard3d, pricing (objets3d)
description: À utiliser quand on reconstruit en 3D les objets ou les personnes de l'image d'un plan avec SAM 3 (Meta) : « Reconstruire en 3D » de l'Atelier, storyboard 3D, objets 3D placés dans le Plateau, corps humain 3D, liste d'objets séparés par des virgules, scène 3D depuis une image, previs, objets manquants ou mal placés après reconstruction.
---
## Aperçu

SAM 3 isole des éléments de l'image d'un plan et les reconstruit en GLB **placés**, posés comme instances de la
scène du Plateau liée au plan. Deux membres :

- **objets 3D** (défaut) : un GLB par objet nommé, chacun avec sa position ;
- **corps humain 3D** : toutes les personnes de l'image en un seul GLB, posé comme une instance « sujet ».

On le lance depuis l'Atelier : carte du plan › « Reconstruire en 3D (SAM 3) ». L'image source est l'image de
production du plan, sinon son croquis.

## Référence rapide

- [PROMPT] Objets : des noms courts séparés par des virgules, en anglais, un par objet à isoler :
  « knight, wooden table, oil lamp ». Le champ est prérempli avec les objets du plan : le relire et le traduire.
- [PROMPT] Nommer ce qui se voit nettement dans l'image, avec un mot qui le distingue (« red chair » quand il y a
  deux chaises). Un objet absent de l'image ne sort pas.
- [PIÈGE] SAM 3 ne rend aucun nom par objet. L'app pose les noms de la liste dans l'ordre où les objets reviennent,
  qui peut différer de l'ordre écrit. Vérifier chaque instance dans le Plateau.
- [CHOIX] Corps humain : la liste est facultative et ne part pas au modèle ; elle ne sert qu'à nommer. Les personnes
  ressortent soudées en un seul GLB, sans position par personne.
- [CHOIX] Image de production plutôt que croquis : un croquis au trait donne des volumes pauvres et une texture plate.
- [PROMPT] Image qui se reconstruit bien : objets séparés, peu cachés les uns par les autres, sol visible, lumière
  lisible. Un objet coupé par le cadre revient incomplet.
- [PIÈGE] Le repère entre SAM 3 et le Plateau n'est pas encore confirmé (l'app le suppose identique, à trancher au
  premier tir réel). Une position ou une rotation fausse se corrige à la main dans le Plateau.
- [PIÈGE] Chaque reconstruction remplace les instances SAM 3 précédentes du plan. Le décor posé à la main reste.
- [PIÈGE] Au-delà d'un plafond d'objets par tir, les objets en trop sont écartés ; l'écran le dit. Découper en deux
  tirs si la liste est longue.
- [COÛT] Prix par requête, quel que soit le nombre d'objets ; l'unité de facturation de fal est à confirmer au
  premier tir (l'écran le rappelle). Le devis passe par le plafond « chapitres ».
- [MÉTHODE] Contrôle : ouvrir le Plateau du plan (proposé à la fin), compter les objets, vérifier noms, échelle et
  contact au sol, puis seulement générer la vidéo du plan depuis le Plateau.
- [CHOIX] Un objet seul, à soigner comme asset (topologie, texture, rig) : pas ce modèle, mais un générateur 3D de
  Game Assets › 3D › Créer depuis une image isolée.
- [CHOIX] Pas encore dans l'app : désigner les objets par des rectangles, régler le seuil de détection, fixer une
  graine.

## Exemple

Brief : « sur le plan 4, la taverne : je veux le chevalier, la table et la lanterne en 3D pour cadrer la caméra ».

Atelier, plan 4, « Reconstruire en 3D (SAM 3) », modèle objets 3D, image de production. Champ Objets :

```
knight, wooden table, hanging lantern
```

Après le tir, ouvrir le Plateau : trois instances. La lanterne porte le nom « wooden table » : renommer, remonter la
lanterne sous la poutre, poser la caméra, puis lancer la vidéo du plan.

## Erreurs fréquentes

- Laisser la liste en français ou en phrases : les objets sont moins bien trouvés.
- Croire que le nom affiché correspond à l'objet : l'ordre peut tourner.
- Relancer pour ajouter un objet oublié : le tir remplace les objets SAM 3 déjà posés. Relancer avec la liste
  complète.
- Prendre corps humain pour deux personnages à placer séparément : ils arrivent en un seul bloc.
