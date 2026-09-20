# Vectorlab — menus détachés pour les autres sections — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).

> Demande du 17/09/2026 : « ajoute les menus détachés pour les autres
> sections », après Forme et Symboles (`4c1fc2a`). Même mécanique
> (`mod-flyout.js` : clic droit, angle, appui long) ; chaque menu délègue
> aux commandes et panneaux existants — rien de nouveau au modèle.

> **RELEVÉ DE LIVRAISON (17/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Livré** (commits `c1c757e`→`3c32bf8`, poussés) : `mod-flyout.js` gagne
> les bâtisseurs purs `flyout_choix`, `flyout_presets` (la valeur courante
> hors liste passe en tête), `flyout_terrains` (pastille, hauteur),
> `flyout_polices` (rendues dans leur famille, source en détail),
> `flyout_actions` (désactivée si sa cible n'existe pas) et le registre
> `MENUS` : **17 outils à menu** — Forme, Symboles, Sélection (aligner ×6,
> ordre ×4, grouper / dégrouper, booléens ×4 ; tout désactivé sans
> sélection), Nœuds (diviser, inverser, joindre, coins), Typographies (les
> polices + Déposer), Pinceau vectoriel et Crayon (3 profils, largeurs 4 · 8
> · 16 · 24), Gomme (6 · 12 · 24 · 48), Coin (5 · 10 · 20 · 40), Terrains
> (fiche du document + Générer le plateau), Pinceau / Gomme raster (rayons 1
> → 16, dureté nette / douce), Seau / Baguette (tolérances 0 · 16 · 48 · 96,
> Global), Sélection raster (tout, aucune, inverser, croître, contracter,
> par couleur), Tranches (les cinq modes + Effacer). Les boutons ajoutés
> par les modules (pixel, export, pinceau vectoriel) sont armés
> automatiquement ; un menu long défile (70 % de la fenêtre au plus).
>
> **TDD** : RED constaté (banc `flyout.test.mjs` étendu à 15 contrôles) ;
> node **985 contrôles sur 61 bancs**, pytest `test_vector_docs` **40
> passed**.
>
> **Prouvé en réel** (8799, viewport 1400×900) : **16 boutons armés** ;
> Sélection à vide → aligner, grouper et booléens désactivés ; avec deux
> objets → Grouper actif, clic → **groupe** ; Nœuds sur un chemin → 4
> entrées, « Inverser » change le `d` ; Typographies sur t1 → **17 entrées**
> (Anton marquée), « Bebas Neue » → police du texte ; Pinceau vectoriel →
> calligraphie + 16 px, outil pris ; Crayon partage le menu ; Gomme 24,
> Coin 20 ; Terrains → 5 pastilles, Plaine marquée, « Forêt » → terrain
> courant + outil tuiles ; persona Pixel : pinceau raster rayon 8 + douce
> (0,3), seau tolérance 48 + global, sélection raster 6 entrées toutes
> désactivées sans image éditée, gomme / baguette / lasso ouverts ; persona
> Export : tranche → 6 entrées, Document marqué, Effacer désactivé, « Chaque
> planche » → mode `planches` et liste du panneau synchronisée ; Forme 7 et
> Symboles 2 toujours là ; Échap ferme.
>
> **Déployé** : 3 fichiers (= base `4c1fc2a` par hash-object) → sauvegarde
> `_backup_predeploy_2026-09-17m-vectorlab-menus2` → `git archive 3c32bf8`
> → **3 = cible, 118/118 du Vectorlab = cible**. Aucun Python.
>
> **Reste** : Apparence (couleurs), Apparence +, Image, Repères, Grille,
> Planches, Carte réelle et Bibliothèque n'ont pas de bouton d'outil et
> restent dans le panneau (leurs réglages sont des formulaires, pas des
> choix rapides) ; les menus délèguent aux boutons des panneaux — une
> action y est désactivée quand le panneau ne la propose pas.

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

## Addendum (17/09) : poignées de forme muettes à la souris — corrigé, prouvé, déployé

> Signalé par l'utilisateur (capture d'une spirale) : « les ancres de
> modification des formes (pastille jaune) ne fonctionnent sur aucune forme ».
> **Cause** : `#overlay` est en `pointer-events: none` et seules les classes
> listées sont ré-activées (`.poignee`, `.poignee-rot`, `.guide`, `.ancre`,
> `.poignee-grad`) — `.poignee-forme` et `.poignee-pivot` (lot B) ne l'étaient
> pas : une vraie souris passait au travers de la pastille et prenait l'objet.
> La preuve du lot B dispatchait ses événements SUR l'élément, ce qui ne
> passe pas par le test de pointeur — d'où un défaut invisible au banc.
> **Correctif** : `#overlay .poignee-forme, #overlay .poignee-pivot {
> pointer-events: auto }` (+ grossissement au survol). **Prouvé avec la
> souris du navigateur** (viewport 1200×800, `elementFromPoint` = la
> poignée, puis `left_click_drag` réel de 26 px) : spirale r **60 → 72,13**,
> centre inchangé, entrée d'historique posée. Déployé (statiques seuls).

## Addendum 2 (17/09) : menus Image et Apparence — livrés, prouvés, déployés

> Demande : « ajoute les menus détachés pour images et apparences aussi ».
> Deux boutons de la barre (persona Vecteur, cachés ailleurs) qui ne sont
> que des menus : **Image** (Bibliothèque, Fichier, Presse-papiers, Générer
> → le menu Image de l'en-tête ; sur une image sélectionnée : Vectoriser,
> Image entière, Verrouiller / Déverrouiller, Éditer les pixels → persona
> Pixel + chargement) ; **Apparence** (Couleur de fond / de contour → le
> nuancier, Sans fond, Sans contour, épaisseurs 1 · 2 · 4 · 8, opacités 100 ·
> 75 · 50 · 25 — réglages qui patchent la sélection ou, à vide, le style
> courant —, dégradé linéaire / radial / conique, transparence, motif,
> effets ombre / lueur). Bâtisseur pur `flyout_reglages` (banc 18
> contrôles). **Défaut latent trouvé en route** : deux boutons portaient
> l'id `apContour` (la pastille de contour et « décaler ») — la pastille
> déclenchait AUSSI le décalage et le bouton « décaler » était muet ;
> renommé `apDecaler`.
> **Prouvé** (8799, 1400×900) : 21 boutons visibles en Vecteur, les deux
> cachés en Pixel ; Apparence sur r1 → **19 entrées**, épaisseur 8 et
> opacité 0,5 posées, sans fond, ombre ajoutée, dégradé linéaire, nuancier
> ouvert par « Couleur de contour » ; clic sur la pastille de contour → **0
> objet ajouté** ; à vide, « 4 px » patche le style courant ; Image sans
> sélection → 4 entrées désactivées ; sur une image → Verrouiller puis
> Déverrouiller relus, « Éditer les pixels » → persona Pixel et tampon
> **8×8 chargé**. Déployé (statiques seuls).

