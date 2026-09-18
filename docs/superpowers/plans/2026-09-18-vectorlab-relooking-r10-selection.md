# Vectorlab relooking Affinity — R10 l'outil Sélection de classe Affinity + finalisation du Nœud — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).
> Demande de l'utilisateur (18/09) : « analyse mieux l'outil sélection
> d'Affinity et raffine le nôtre et finalise : pas de poignées de rotation
> ou d'échelle sur une sélection de nœuds, pas de conversion Intelligent,
> pas de réglage séparé du magnétisme aux nœuds ».

## Analyse de l'outil Déplacer (Sélection) d'Affinity

| Geste ou réglage d'Affinity | Aujourd'hui dans le Vectorlab | Décision |
|---|---|---|
| Clic = sélectionner, Maj+clic = ajouter / retirer, clic sur le vide = désélectionner | oui | conservé |
| Glisser depuis le vide = cadre ; par défaut les objets **entièrement inclus** ; Alt = les objets **touchés** | cadre « touchés » seulement | `cadre_selection` pur (inclus / touchés), Alt bascule |
| Glisser un objet = déplacer ; **Maj** = contraint aux axes ; **Alt** = déplacer une **copie** | déplacer avec magnétisme | `contraindre_axe` pur (Maj) ; Alt+glisser duplique puis déplace la copie (mod-selectionui) |
| Poignées : coin / côté ; Maj = proportions ; **Ctrl = depuis le centre** | proportions par Maj | Ctrl = miroir du delta sur le côté opposé (mod-tools) |
| Poignée de rotation, Maj = pas de 15° | oui | conservé |
| Contour de l'objet au **survol** | — | `#ovSurvol` : boîte fine bleue de l'objet sous le curseur |
| **Double-clic** sur une courbe → outil Nœud ; sur un texte → édition | texte seulement | double-clic sur path / forme → outil Nœuds (chemin sélectionné) |
| Flèches = 1 px, Maj = 10 px ; Ctrl+D duplique | oui | conservé |
| Barre contextuelle : « n objet(s) », X · Y · L · H, rotation, Sélection auto, Configuration / Paramètres | libellé + opacité | X · Y · L · H inline (déplacer / redimensionner par commandes) + opacité |

## Finalisation du Nœud (restes de R9)

| Reste | Décision |
|---|---|
| Poignées de rotation / échelle sur une sélection de nœuds | ≥ 2 ancres sélectionnées → boîte en pointillés, 8 poignées d'échelle (Maj = proportions) et une poignée de rotation (Maj = 15°) dans l'overlay ; `bbox_ancres`, `bbox_par_poignee`, `noeuds_tourner` purs ; `op_noeuds_transformer` existant pour l'échelle |
| Conversion « Intelligent » | `noeud_intelligent(segs, i)` pur : tangentes Catmull-Rom (direction voisin suivant − voisin précédent, longueurs proportionnelles aux distances) ; action `VL.actions.plume.intelligent` et bouton dans les barres Plume et Nœuds |
| Magnétisme aux nœuds | `etat.aimantNoeuds` (défaut vrai), bascule « Magnétisme » dans la barre du Nœud ; respecté par le glisser d'ancre (mod-tools), d'ancres multiples (mod-outils2), de poignées et de segments (mod-noeudui) |

**Architecture :** `mod-selection.js` feuille : `contraindre_axe(dx, dy)`,
`cadre_selection(boites, cadre, mode)` → ids, `bbox_ancres(ancres,
indices)`, `poignees_bbox(b)` → 8 points + rotation, `bbox_par_poignee(b0,
k, pt, {proportions, centre})`, `noeuds_tourner(segs, indices, cx, cy, deg)`
; `mod-noeud.js` gagne `noeud_intelligent` ; `mod-selectionui.js` : Alt+glisser
= copie déplacée (capture), double-clic → Nœuds, survol ; `mod-noeudui.js`
: poignées de transformation des nœuds (`VL.surOverlay` chaîné) ;
`mod-tools.js` : Maj sur le déplacement, Ctrl sur le redimensionnement,
cadre inclus / touchés (Alt), `aimantNoeuds` ; `mod-outils2.js` :
`aimantNoeuds` ; `mod-contexte` : X · Y · L · H, Intelligent, Magnétisme.

**Tech :** vanilla ESM ; node `qa/run.mjs` ; preuve 8799 par gestes réels.

### Task 1 : `mod-selection.js` + `noeud_intelligent` (RED → vert)
### Task 2 : mod-tools / mod-outils2 (modificateurs, cadre, magnétisme), mod-selectionui, mod-noeudui (poignées), contexte
### Task 3 : preuve en réel — cadre inclus vs Alt touchés, Maj contraint, Alt copie déplacée (+1 objet, l'original immobile), Ctrl depuis le centre (centre fixe), survol (`#ovSurvol`), double-clic → outil Nœuds, X · Y · L · H de la barre ; nœuds : 2 ancres → 8 poignées + rotation, échelle par poignée (Maj proportions), rotation (Maj 15°), Intelligent (tangentes posées), Magnétisme désactivé → poignée non aimantée ; 0 erreur, document valide
### Task 4 : déploiement, relevé, mémoire, push
