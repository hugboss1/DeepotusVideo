# Photolab parité L4 (t154) — Transformation manuelle (Ctrl+T) et Édition › Transformation ›

> Relevé : `specs/2026-10-08-photolab-bientot-inventaire.md` §3 (barre d'options de la référence lue sous Ctrl+T,
> annulée par Échap) ; amont photocraft v0.3.0 `ui-egui/src/transform_tool.rs`, `engine/src/transform_cmds.rs`,
> `algo/src/transform.rs`. Base : origin/main 419caf63, branche `chantier/photolab-parite-l4`.

## Faits établis (vrai moteur, 08/10)

- `edit.transform {rect?, quad?, matrix?, interpolation?, layer?}` : `quad` = où vont les coins du cadre source (HG, HD,
  BD, BG) ; `rect` par défaut = contenu du calque ∩ sélection, rendu dans la réponse `{rect}`. Matrice = affine.
- La sélection suit la transformation ; l'arrière-plan sans sélection se transforme aussi au moteur (l'amont le grise :
  repris). État d'historique : « Free Transform ». `edit.transform.again` refusé tant qu'aucune transformation.
- Aucun aperçu de transformation dans le moteur : `/apercu` (étapes jouées sur une COPIE, rendu du moteur) admet
  désormais `edit.transform` — l'image montrée pendant la session vient du moteur (D1).

## Décisions

| Entrée | Décision |
|---|---|
| Transformation libre (Ctrl+T) | **Repris** : cadre = contenu du calque ∩ sélection, 8 poignées + point de référence, gestes de l'amont (coin = homothétie proportionnelle, Maj libère, Alt depuis le point de référence ; bord = un axe ; dedans = déplacer, Maj = 8 directions ; dehors = rotation, Maj = pas de 15° ; Ctrl+coin = déformation libre ; Ctrl+bord = inclinaison ; Ctrl+Alt+Maj+coin = perspective ; glisser ou Alt+clic = point de référence ; flèches = 1 px, Maj = 10 px) ; Entrée ou double-clic = valider, Échap = annuler ; Ctrl+Z dans la session = pas précédent |
| Mise à l'échelle, Rotation, Inclinaison, Déformation, Perspective | **Repris de la référence** (l'amont ne contraint rien) : la session s'ouvre dans ce mode et le geste d'une poignée est celui du mode |
| Barre d'options | **Repris de la référence** : point de référence (grille 3 × 3), X et Y (Δ = relatif), L % et H % (liés), angle, inclinaisons H et V, interpolation, Valider / Annuler |
| Aperçu | **Adapté** : contour et poignées pendant le geste, image rendue par le moteur sur copie à chaque relâchement (pas de texture déformée par l'écran) |
| Calque de réglage sans masque, arrière-plan sans sélection, cadre vide | refusés avec un message (amont) |
| Déformer (warp), Déformation de la marionnette | hors lot (warp : maillage ; marionnette : D9) |

## Tâches

- **A** — `COMMANDES_APERCU` + `edit.transform` ; banc `test_photolab_transformation.py` (liste blanche, aperçu sur copie :
  original intact, rendu = application réelle à l'octet).
- **B** — module pur `js/mod-transformer.js` (QA `qa/transformation.test.mjs`) : homographie, cadre source, prise des
  poignées, gestes, lecture et édition des champs, commande.
- **C** — DOM : mode prioritaire dans le répartiteur des gestes, poignées dans `#fourmis`, barre d'options, menus
  (`TRAITES_PAR_ECRAN`, `NECESSITE_DOC`), Ctrl+T, textes fr/en.
- **D** — mutations, preuve 8799, recomptage (198 -> 192).

## Relevé d'exécution (08/10/2026)

**Faits nouveaux.**
- `doc.inspect` ne marque pas l'arrière-plan : reconnu comme le calque du bas nommé « Background » (nom du moteur).
- L'aperçu `/apercu` d'un `edit.transform` est identique pixel pour pixel au rendu après application réelle.
- Les sous-modes de l'amont ne contraignent rien (`menus.rs` : même `begin`) ; ceux de l'écran suivent la référence.

**Bancs.**
- `test_photolab_transformation` : 14/14 (liste blanche, aperçu sur copie, original intact, égalité de pixels, route).
- QA node : toutes les séries vertes, dont la nouvelle `transformation` (57).
- `test_photolab_apercu` 83/83 (la liste des commandes d'aperçu a gagné `edit.transform` sans rien casser).
- Mutations : 12 sur 12 tuées, sources restaurées et vérifiées par `cmp`.

**Preuve sur 8799** (gestes réels, vrai backend jetable) :
- Ctrl+T (raccourci du catalogue) ouvre la session sur le contenu du calque (20,20)-(60,50) : 8 poignées, point de
  référence, barre « Transformation libre » X 40, Y 35, L 100 %, H 100 %, angle 0.
- Coin bas droit tiré de (60,50) à (100,60) : 200 % proportionnel ; l'image affichée est l'aperçu du moteur ; aucun état
  d'historique pendant la session. Rotation au dehors, puis Ctrl+Z : le cadre revient au pas précédent (historique
  intact). Entrée : un seul « Free Transform », calque (19,19,82,62).
- Barre : point de référence haut gauche, L 50 % lié (H suit), angle 30°, inclinaison H 10°. Échap : session fermée,
  rendu du moteur rétabli, aucun état.
- Édition › Transformation › Perspective (menu) : le coin HG tiré de 15 px, le coin HD part à l'opposé (34 / 86) ;
  double-clic : « Free Transform ».
- Arrière-plan sans sélection : refusé avec le message ; avec une sélection (0,0,30,30) : session ouverte sur elle.
  Changer d'outil annule la session et rend la barre de l'outil.
- Écran en anglais vérifié (Skew, W, H skew, Nearest Neighbor, bulles), puis retour au français.

**Recomptage** `lister_bientot.mjs` : 192 (198 avant).
