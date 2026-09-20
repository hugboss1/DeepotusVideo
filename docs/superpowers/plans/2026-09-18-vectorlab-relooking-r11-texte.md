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

> **RELEVÉ DE LIVRAISON (18/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Livré** (commit `0c859f6`, poussé) : `mod-texte.js` feuille
> (`corps_de_glisser`, `champs_texte`, `patch_texte` borné, `cycle_suivant`,
> `GRAISSES`, `ANCRES` ; RED constaté, 6 contrôles) ; `mod-doc.js` :
> `style.italique` / `style.souligne` validés (booléens) et compilés
> (`font-style`, `text-decoration`), graisse validée (banc texte 9) ;
> `_objetsCibles` PROFOND — un enfant de groupe est une cible (banc ops 14 :
> déplacer et supprimer un enfant) ; `core.objetDe` profond ;
> `mod-texteui.js` : clic = texte au corps courant, glisser = texte au corps
> de la hauteur tirée (aperçu « n px »), clic sur une courbe ou une forme =
> texte sur ce chemin puis édition en place, indicateur rouge de
> débordement d'un cadre, Tab / Maj+Tab ; `mod-tools` : Ctrl+clic vise
> l'enfant cliqué, Sélection auto décochée = tout glisser déplace la
> sélection courante sans en changer ; `mod-typo` : `poserTexte(x, y,
> corps)` et `etat.typo.styleDefaut` ; barre contextuelle : huit champs de
> style du texte (outil Texte, ou texte sélectionné en outil Sélection),
> sinon défauts des prochains textes ; bascule « Sélection auto ».
>
> **Prouvé en réel** (8799, 1400 × 900, gestes pointeur) : glisser de 60
> px avec l'outil Texte → texte de corps 60 ; barre sur le texte
> sélectionné : gras / italique / souligné / centre / corps 36 → le `<text>`
> porte `font-weight="bold" font-style="italic" text-decoration="underline"
> text-anchor="middle"` ; italique + corps 24 posés sans sélection → le
> texte suivant les a ; clic sur une courbe (trait 14) → objet
> `textechemin` (+1) ; cadre 60 × 20 débordant → `data-deborde` et carré
> rouge dans l'overlay ; clic sur un groupe → `g1`, Ctrl+clic → `e1`, Ctrl+
> glisser → `e1.x` 500 → 550, le frère immobile ; Sélection auto décochée
> puis glisser sur un autre objet → la sélection `cad` reste et bouge de
> 50 ; Tab → objet suivant, Maj+Tab → retour ; 0 erreur, document valide.
>
> **Défauts attrapés par la preuve** : Échap dans l'éditeur ANNULE un texte
> neuf (le blur le valide) ; un clic sur une courbe était refusé quand
> l'éditeur restait ouvert (il est maintenant fermé par blur) ; le
> déplacement d'un enfant échouait sans bruit (`_objetsCibles` ne voyait
> que le premier niveau).
>
> **Déployé** : installé = base R10 `4b04f00` (153, 0 divergent) →
> sauvegarde `_backup_predeploy_2026-09-18-relooking-r11` → 156/156 = cible.
>
> **Reste (assumé)** : pas de styles de caractère / paragraphe nommés ni
> de justification (le cadre ne connaît que gauche / centre / droite) ; le
> texte sur chemin garde le décalage du panneau Apparence + ; les trois
> restes de R10 sont clos.

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
