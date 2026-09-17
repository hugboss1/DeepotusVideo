# Vectorlab — lisibilité auditée, menus détachés de la barre d'outils, pose au clic, icône Sélection — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).

> Demande du 17/09/2026 (trois captures) : « cumul trop illisible des
> champs, vérifie toutes les catégories » ; « des fonctionnalités du panneau
> pourraient habiter en menu détaché depuis la colonne de gauche (symboles,
> formes) » ; « nouvelle icône pour Sélection » ; « les outils proposés ne
> fonctionnent pas » — diagnostic : les 18 boutons prennent leur outil et
> les 8 outils de création posent un objet au geste ; ce qui ne répond pas
> est le CHOIX d'une forme dans la liste (rien ne se pose sans glisser) et
> les bulles d'information qui recouvrent les listes ouvertes.

> **RELEVÉ DE LIVRAISON** : à écrire ici en fin de lot.

**Goal :** aucune rangée du panneau ne déborde ni n'écrase ses champs (audit
de TOUTES les sections, dans les trois personas, prouvé au DOM) ; la barre
de gauche gagne des menus détachés (flyout) : Forme (les sept formes, la
courante marquée) et Symboles (poser une instance, créer depuis la
sélection) ; une forme se pose au CLIC (rayon 40) autant qu'au glisser ; les
bulles d'information attendent 450 ms, se cachent dès qu'une liste ou un
champ prend le focus et ne recouvrent plus une liste ouverte ; l'icône
Sélection devient une flèche.

**Architecture :** `mod-flyout.js` — pur : `flyout_formes(FORMES, courante)`,
`flyout_symboles(symboles)` (état vide → entrée « aucun symbole »),
`flyout_position(bouton, taille, fenetre, marge)` (à droite du bouton,
borné) ; `initFlyout(VL)` : marque d'angle sur les boutons à menu, ouverture
au clic droit / clic sur l'angle / appui long, fermeture Échap / clic dehors ;
mod-outils2 : clic sans glisser = forme au rayon 40 ; mod-style : rangée
Puissance en deux rangées, glyphes courts pour miroir / dupliquer ; CSS :
garde-fou `.ap-ligne` (repli en deux lignes plutôt qu'écrasement, largeur
minimale des champs 40 px) ; mod-infobulle : délai, focus, suppression après
clic ; index.html : symbole `t-select` en flèche, bouton Symboles.

**Décisions :** le clic droit ouvre le menu (le navigateur perd son menu
contextuel sur la barre seulement) ; l'appui long dure 400 ms ; les menus
vivent dans `#flyout` (un seul à la fois) ; la rangée qui déborde malgré tout
se replie (les champs repliés commencent sous le libellé).

## Tasks
1. `mod-flyout.js` pur (banc `flyout.test.mjs`) + `initFlyout`, bouton Symboles, pose au clic, icône.
2. Lisibilité : Puissance, miroir, garde-fou, bulles ; audit DOM de toutes les rangées (preuve).
3. Preuve, déploiement (statiques seuls), relevé.
