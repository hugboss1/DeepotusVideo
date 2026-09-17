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

> **RELEVÉ DE LIVRAISON (17/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Diagnostic d'abord** (8799, gestes réels) : les **18 boutons** de la
> barre prennent leur outil et affichent leur indice ; les **8 outils de
> création** (rect, ellipse, ligne, forme, crayon, pinceau vectoriel, plume,
> texte) posent un objet au geste ; la sélection déplace. Ce qui ne
> répondait pas : choisir une forme dans la liste ne posait rien sans
> glisser, et les bulles recouvraient une liste ouverte.
>
> **Livré** (commits `c3e02e6`→`1a8134d`, poussés) : `mod-flyout.js` (pur :
> entrées Forme avec glyphes et courante marquée, entrées Symboles avec état
> vide dit, position à droite bornée ; UI : marque d'angle, clic droit /
> angle / appui long 400 ms, un menu à la fois, Échap et clic dehors) ;
> bouton Symboles dans la barre ; une forme se pose au **clic** (rayon 40)
> ; Aligner et Puissance sur deux rangées ; libellé = premier `span` d'une
> rangée (un span porte-boutons se partage la place ou se replie) ; champs
> jamais sous 40 px, boutons d'icône jamais sous 30 px, rangée qui se replie
> plutôt que d'écraser ; glyphes courts miroir / dupliquer ; bulles
> retardées de 450 ms, cachées au clic, au focus d'un champ ou à la
> molette, muettes sur l'élément qu'on vient de cliquer ; icône Sélection en
> flèche.
>
> **TDD** : RED constaté (banc `flyout.test.mjs`, 7 contrôles) ; node **977
> contrôles sur 61 bancs**, pytest `test_vector_docs` **40 passed**.
>
> **Prouvé en réel** (8799, viewport 1400×900) : **audit de lisibilité au
> DOM** — toutes sections ouvertes, dans les trois personas, avec six
> sélections représentatives (rien, rect, deux, trois, chemin, texte) :
> **224 rangées et 469 champs vus, 0 débordement, 0 champ sous 28 px, 0
> bouton tronqué** (les trois défauts trouvés en route — Aligner à 19 px,
> Motifs et Teintes du vitrail qui débordaient — sont corrigés) ; menu Forme
> ouvert au clic droit à droite du bouton (**7 entrées**, Polygone marqué),
> choix Étoile → outil Forme, liste du panneau synchronisée ; **clic sans
> glisser → étoile de rayon 40** ; menu Symboles à vide (« aucun symbole »
> désactivé + Créer), création depuis la sélection → s1, menu qui le liste
> (« 2 objets »), pose → instance `<use>` sélectionnée ; bulle : rien à 200
> ms de survol, forcée puis cachée par le focus d'un champ ; icône Sélection
> = flèche (capture).
>
> **Déployé** : 8 fichiers (= base `05a5b7a` par hash-object, 2 absents) →
> sauvegarde `_backup_predeploy_2026-09-17l-vectorlab-lisibilite` → `git
> archive 1a8134d` → **8 = cible, 118/118 du Vectorlab = cible**. Aucun
> Python.
>
> **Reste** : les menus détachés couvrent Forme et Symboles (les autres
> sections restent dans le panneau) ; l'appui long ne se prouve qu'à la
> souris réelle ; le clic droit sur la barre perd le menu contextuel du
> navigateur.

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
