# Vectorlab relooking Affinity — R11 l'outil Texte de classe Affinity + finalisation de la Sélection — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).
> Demande de l'utilisateur (18/09) : « analyse l'outil texte d'Affinity et
> raffine le nôtre et finalise : Ctrl+clic pour sélectionner un enfant de
> groupe, le mode Sélection auto, le cycle Tab ».

## Analyse de l'outil Texte d'Affinity

| Geste ou réglage d'Affinity | Aujourd'hui dans le Vectorlab | Décision |
|---|---|---|
| Deux outils : **Texte artistique** (clic = poser, **glisser = poser en donnant le corps** par la hauteur) et **Cadre de texte** (glisser un cadre) | clic = poser (corps 48 fixe) ; cadre au glisser (R7) | le glisser donne le corps (`corps_de_glisser`), le clic garde le corps courant |
| Clic sur une courbe avec l'outil Texte → **texte sur un chemin** | menu Apparence + (texte puis chemin) | clic sur un chemin / une forme avec l'outil Texte → texte posé puis mis sur le chemin, édition en place |
| Barre contextuelle : police, style (Regular / Bold / Italic), corps, alignement, gras / italique / souligné, interligne, approche, ligne de base | police seule (R5) | police, corps, graisse, italique, souligné, alignement, interligne, interlettrage — sur le texte sélectionné, sinon défauts des prochains textes |
| Italique et souligné | absents du modèle | `style.italique` (font-style) et `style.souligne` (text-decoration) : validés, compilés |
| Cadre qui déborde : indicateur rouge | `data-deborde` compilé, rien à l'écran | carré rouge au coin bas-droit du cadre sélectionné qui déborde |
| Édition en place, Échap finit, double-clic réédite | oui | conservé |

## Finalisation de la Sélection (restes de R10)

| Reste | Décision |
|---|---|
| Ctrl+clic sélectionne un **enfant de groupe** | mod-tools : avec Ctrl, la cible est l'objet cliqué lui-même (pas son sommet) et il devient sélectionnable ; déplacement, style et poignées suivent (les commandes travaillent en profondeur) |
| **Sélection auto** | `etat.selectionAuto` (défaut vrai), bascule dans la barre de l'outil Sélection ; décochée avec une sélection : tout glisser déplace la sélection courante sans en changer |
| **Cycle Tab** | Tab = objet sélectionnable suivant, Maj+Tab = précédent (`cycle_suivant` pur), dans l'outil Sélection |

**Architecture :** `mod-texte.js` feuille (`corps_de_glisser`, `champs_texte`,
`patch_texte`, `cycle_suivant`, `GRAISSES`, `ANCRES`) ; `mod-doc.js` :
`italique` / `souligne` validés et compilés (banc texte) ; `mod-texteui.js`
: capture en outil `texte` (clic / glisser / clic sur un chemin),
indicateur de débordement (`surOverlay`), Tab (`surTouche`) ;
`mod-tools.js` : Ctrl+clic et Sélection auto ; `mod-contexte` /
`mod-barrecontexte` : champs du texte (patch de style → `op_style` sur le
texte sélectionné, sinon `etat.typo.styleDefaut`), bascule Sélection auto.

### Task 1 : `mod-texte.js` + italique / souligné (RED → vert)
### Task 2 : `mod-texteui.js`, mod-tools, contexte, mod-typo (défauts)
### Task 3 : preuve en réel — glisser avec l'outil Texte → corps = hauteur ; clic sur une courbe → objet `textechemin` ; barre : corps 36, gras, italique, souligné, alignement centre, interligne → le SVG compilé porte font-weight / font-style / text-decoration / text-anchor ; cadre débordant → carré rouge ; Ctrl+clic sur un enfant de groupe → sélection de l'enfant, glisser → il bouge seul ; Sélection auto décochée → glisser sur un autre objet déplace la sélection courante ; Tab / Maj+Tab cyclent ; 0 erreur, document valide
### Task 4 : déploiement, relevé, mémoire, push
