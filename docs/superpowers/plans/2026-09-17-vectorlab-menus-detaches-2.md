# Vectorlab — menus détachés pour les autres sections — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).

> Demande du 17/09/2026 : « ajoute les menus détachés pour les autres
> sections », après Forme et Symboles (`4c1fc2a`). Même mécanique
> (`mod-flyout.js` : clic droit, angle, appui long) ; chaque menu délègue
> aux commandes et panneaux existants — rien de nouveau au modèle.

> **RELEVÉ DE LIVRAISON** : à écrire ici en fin de lot.

**Goal :** chaque outil de la barre de gauche dont le panneau porte des
choix ou des actions fréquentes gagne un menu détaché :
- **Sélection** → Aligner (6), Ordre (4), Grouper / Dégrouper, Booléens (4)
  ; **Nœuds** → Diviser, Inverser, Joindre, Coins arrondis ;
- **Texte** → les typographies (la courante marquée) + Déposer une police ;
- **Crayon / Pinceau vectoriel** → profil plat / fuseau / calligraphie,
  largeurs 4 · 8 · 16 ; **Gomme** → largeurs 6 · 12 · 24 ; **Coin** → rayons
  5 · 10 · 20 ;
- **Tuiles** → les terrains de la fiche (pastille, nom, hauteur), le
  courant marqué, + Générer le plateau ;
- **Pixel** : Pinceau / Gomme raster → rayons 1 · 2 · 4 · 8 · 16, dureté
  nette / douce ; Seau / Baguette → tolérances 0 · 16 · 48, global ;
  Sélection rectangle / Lasso → Tout, Aucune, Inverser, Croître, Contracter ;
- **Export** : Tranche → les cinq modes de tranche (le courant marqué) +
  Effacer les tranches.

**Architecture :** `mod-flyout.js` gagne des bâtisseurs PURS
(`flyout_choix(liste, courant, {glyphe})`, `flyout_presets(valeurs,
courante, unite)`, `flyout_terrains(terrains, courant)`, `flyout_polices
(polices, courante)`, `flyout_actions(liste, disponibles)`) et un registre
`MENUS` (outil → bâtisseur + action) ; les actions délèguent aux boutons
des panneaux existants par id (`#apGrouper`, `#ndDiviser`, `#pxSelTout`…)
ou aux états (`etat.pinceauv`, `etat.px`, `etat.terrainCourant`,
`etat.exportPlus.mode`, `etat.typo.courante`) — un menu marque ses boutons
au chargement (`.a-menu`), y compris ceux que les modules ajoutent.

**Décisions :** un bouton dont le panneau n'est pas rendu (rien de
sélectionné) montre ses actions DÉSACTIVÉES plutôt que de les cacher ; la
liste des typos est celle du panneau Texte (bibliothèque + déposées +
système) ; les presets ne remplacent pas les champs du panneau, ils les
préremplissent.

## Tasks
1. Bâtisseurs purs + registre (banc `flyout.test.mjs` étendu, RED d'abord).
2. Preuve en réel : chaque menu ouvert, compté, une action jouée ; déploiement statiques ; relevé.
