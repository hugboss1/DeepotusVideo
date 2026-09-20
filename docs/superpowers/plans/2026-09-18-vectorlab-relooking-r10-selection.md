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

> **RELEVÉ DE LIVRAISON (18/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Livré** (commit `4b04f00`, poussé) : `mod-selection.js` feuille
> (`contraindre_axe`, `cadre_selection` inclus / touchés, `bbox_ancres`,
> `poignees_bbox`, `bbox_par_poignee` proportions / centre,
> `noeuds_tourner` ; RED constaté, 12 contrôles) ; `noeud_intelligent`
> dans mod-noeud (Catmull-Rom, 16 contrôles) ; `mod-selectionui.js` :
> Alt+glisser = copie déplacée qui PART DE LA PLACE de l'original (le
> décalage d'`op_dupliquer` est compensé), double-clic sur une courbe →
> outil Nœuds, survol en boîte bleue ; `mod-tools` : Maj contraint le
> déplacement, Ctrl redimensionne depuis le centre, cadre entièrement
> inclus par défaut et touchés avec Alt, magnétisme aux nœuds respecté ;
> `mod-outils2` idem ; `mod-noeudui` : boîte + 8 poignées d'échelle (Maj
> proportions) + poignée de rotation (Maj 15°) sur ≥ 2 ancres,
> `VL.actions.noeuds.intelligent` ; barre contextuelle : X · Y · L · H de
> la sélection (déplacer / redimensionner par les commandes existantes),
> Intelligent dans Plume et Nœuds, bascule Magnétisme du Nœud.
>
> **Prouvé en réel** (8799, 1400 × 900, gestes pointeur) : cadre
> (80,80)-(320,200) → `[s1]` inclus, avec Alt → `[s1, s2]` ; Maj pendant le
> glisser → dx 50, dy 0 ; Alt+glisser → +1 objet, original immobile, copie
> exactement à +60 ; Ctrl sur la poignée bas-droit → centre (350,130)
> inchangé ; survol → `#ovSurvol rect` ; X = 500 et L = 50 par la barre ;
> double-clic sur une courbe → outil Nœuds, 4 ancres avant et après ; 3
> ancres → 9 poignées, échelle → `L 309 300 L 309 509` ; rotation Maj →
> ancres tournées par pas de 15° ; Intelligent → ancre lisse en C ;
> Magnétisme décoché → `etat.aimantNoeuds` false ; 0 erreur, document
> valide.
>
> **Deux défauts attrapés par la preuve** : Maj tenu DÈS l'appui bascule
> la sélection (comme Affinity) — la contrainte joue pendant le glisser ;
> le double-clic passait aux Nœuds ET insérait un nœud : deux écouteurs
> de capture sur le même élément ne s'arrêtent qu'avec
> `stopImmediatePropagation` ; la copie Alt partait décalée de 12 px
> (compensée).
>
> **Déployé** : installé = base R9 `595caa2` (150, 0 divergent) →
> sauvegarde `_backup_predeploy_2026-09-18-relooking-r10` → 153/153 = cible.
>
> **Reste (assumé)** : Ctrl+clic pour sélectionner un enfant de groupe
> (les enfants ne sont pas sélectionnables seuls) ; le mode « Sélection
> auto » et le cycle Tab d'Affinity ; les trois restes de R9 sont clos.

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
