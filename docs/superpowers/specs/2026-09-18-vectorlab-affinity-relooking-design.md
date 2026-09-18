# Vectorlab « relooking Affinity » — conception (18/09/2026)

> Mission : faire ressembler et se comporter le Vectorlab quasi à
> l'identique d'Affinity (suite Canva), à partir de l'inventaire relevé
> sur le bureau (`2026-09-18-vectorlab-affinity-relooking-inventaire.md`)
> et des deux captures de référence décrites par l'utilisateur. Les huit
> lots fonctionnels A→G, le panneau droit, le design aéré, Texte & logo,
> lisibilité / menus détachés et redondances / miniatures sont livrés :
> ce chantier ne change PAS ce que le Vectorlab sait faire, il change
> comment cela se présente et se commande.

## 1. Décisions tranchées

**R-D1 — Reproduit à l'identique.** La charpente en six bandes (barre de
menus, barre des personas en pastilles, barre contextuelle, onglet de
document, rangée outils / canevas / pile, barre d'état) ; les dix menus
et leurs entrées quand une action existe dans le Vectorlab ; les
pastilles de persona colorées (Vecteur cyan, Pixel violet) ; la colonne
d'outils à boutons carrés, icônes fines monochromes, triangle d'angle,
flyout VERTICAL de la famille d'outils avec « Outil X » et raccourci ; les
trois groupes de panneaux à onglets de la pile de droite, avec chevron de
repli ; les rangées de calques (vignette sur damier, nom, œil, rangée
sélectionnée bleue, opacité et mode de fusion en tête, boutons d'action en
bas) ; le Navigateur (vignette + curseur de zoom) ; le Transformer ;
l'Historique ; la barre d'état (pagination, phrase d'aide aux verbes en
gras) ; le thème gris anthracite, accents bleu / violet / cyan ; le canevas
uni sans damier ; les dimensions relevées (menus 32, personas 42, contexte
32, onglet 26, colonne 44, pile 264, état 22).

**R-D2 — Adapté.** Pas de persona Mise en page ni d'IA Canva (payant / en
ligne) : la barre n'a que **Vecteur** et **Pixel**. Le persona **Export**
existant disparaît de la barre : ses deux sections deviennent l'onglet
**Exporter** du troisième groupe (disponible dans les deux personas) et le
bouton « ▎Exporter SVG ▾ » de la barre des personas ouvre le menu
d'export existant ; l'outil `tranche` rejoint la colonne des deux
personas. Les panneaux propres au Vectorlab (Grille, Plateau & terrains,
Planches, Carte réelle, Repères, Panneau de verre, Texte, Image, Pixel,
Bibliothèque) deviennent des onglets supplémentaires des trois groupes ;
une rangée d'onglets passe à la ligne quand elle est trop longue (pas
de menu de débordement). Canaux n'a pas d'objet (pas de modèle de
canaux) : l'onglet n'existe pas. Histogramme, Navigateur et Historique
sont ajoutés (petits modules purs). Le nom de la planche au-dessus de la
page est reproduit.

**R-D3 — Zéro dépendance, modules purs conservés (D7/D9 de la conception
mère).** Tout est vanilla ESM + CSS ; le SVG-DOM, `mod-doc`, les 45+
commandes, les bancs existants ne bougent pas. Les nouveaux modules sont
des FEUILLES bancables node : `mod-menus.js` (arbre des menus : titre,
entrées, raccourci, disponibilité, action nommée), `mod-familles.js`
(familles d'outils par persona, membre courant), `mod-icones.js` (sprite
d'icônes fines, un chemin par outil et par action), `mod-onglets.js`
(groupes d'onglets par persona, onglet actif mémorisé `dz_vl_onglets`),
`mod-contexte.js` (contenu de la barre contextuelle selon outil et
sélection), `mod-statut.js` (phrase d'aide, pagination), `mod-navigateur.js`
(rectangle de vue, zoom ↔ curseur), `mod-histogramme.js` (256 × 4 depuis un
tampon). L'UI ne fait que traduire ces données en DOM et déléguer aux
actions existantes (`VL.actions.<module>`, `VL.flyout`, `VL.sauver`…).

**R-D4 — Les ids existants restent.** Tous les modules livrés se lient à
des ids (`#panneauStyle`, `#listeCalques`, `#btnSauver`, `#expMenu`,
`#hintOutil`, `#docMeta`…). Le nouvel `index.html` les DÉPLACE, il ne les
renomme pas : `#hintOutil` devient la phrase de la barre d'état,
`#docMeta` le message de la barre d'état (les toasts y arrivent),
`#docTitle` l'onglet de document, `#personas` la rangée de pastilles,
`#btnExporter/#expMenu` le bouton « Exporter SVG ▾ », `#btnAnnuler/#btnRefaire`
les flèches de la barre des personas, `#outils` la colonne. Les sections
`<details id="…Details">` sont conservées comme CONTENU d'onglets : le
`summary` est masqué, l'onglet actif ouvre la section (`open`), les
autres sont fermées — `mod-panneaux` continue de mémoriser l'état, un
onglet actif = section ouverte.

**R-D5 — Correspondance panneau Affinity → module Vectorlab.**

| Groupe | Onglet (persona Vecteur) | Contenu existant |
|---|---|---|
| 1 | Couleur | nuancier de `mod-couleur` hébergé en place (plus un popover) + fond / contour de `#panneauStyle` |
| 1 | Échantillons | palette du document (`doc.palette`, `mod-couleur`) + couleurs globales (`mod-apparence2`) |
| 1 | Trait | rangées Contour / Trait / Pointillés / Joint de `#panneauStyle` |
| 1 | Apparence | `#apparence2Details` (effets, fusion, contours, motifs, styles) |
| 1 | Texte | `#texteDetails` |
| 2 | Calques | `#calquesDetails` relookée (§3) |
| 2 | Tracé | `#noeudsDetails` + `#formeDetails` |
| 2 | FX | sous-section effets de `mod-apparence2` (ancre dans Apparence, l'onglet ouvre Apparence à la sous-section) |
| 2 | Styles | sous-section styles / symboles d'Apparence + |
| 2 | Image | `#imageDetails` |
| 2 | Planches | `#planchesDetails` |
| 2 | Grille | `#grilleDetails` |
| 2 | Plateau | `#plateauDetails` |
| 2 | Carte | `#carteDetails` |
| 2 | Vitrail | `#vitrailDetails` |
| 2 | Stock | `#assetsDetails` (Bibliothèque) |
| 3 | Transformer | X · Y · L · H · Incliner · Puissance de `#panneauStyle` (déplacées dans `#panneauTransformer`) |
| 3 | Navigateur | `mod-navigateur` (vignette + curseur de zoom) |
| 3 | Historique | `#instantanesDetails` + liste des pas (`Historique`) |
| 3 | Repères | `#reperesDetails` |
| 3 | Exporter | `#exportDetails` + `#exportPlusDetails` |

Persona Pixel : groupe 1 = Histogramme · Couleur ; groupe 2 = Calques ·
Pinceaux (rayon / dureté / tolérance de `#panneauPixel`) · Pixel (le reste
du panneau Pixel : ajustements, pixel-art, cadres) · Image · Stock ; groupe
3 = Navigateur · Transformer · Historique · Exporter.

**R-D6 — Colonne d'outils : familles.** Un bouton par FAMILLE, montrant
le membre courant ; le triangle d'angle / l'appui long ouvre la liste
verticale des membres (« Outil Rectangle · R ») ; le clic droit garde le
menu de réglages existant (`mod-flyout`). Familles Vecteur : Déplacer
[select] · Nœuds [noeuds, coin] · Plume [plume, crayon, pinceauv] · Formes
[rect, ellipse, ligne, forme] · Constructeur [constructeur, couteau,
gomme] · Texte [texte] · Image [image (menu)] · Apparence [apparence
(menu)] · Symboles [symbole (menu)] · Mesure [mesure, pipette] · Tuiles
[tuiles] · IA [ia] · Tranche [tranche]. Familles Pixel : Déplacer [select]
· Sélection [px-selrect, px-lasso, px-baguette] · Pinceau [px-pinceau,
px-gomme, px-cloner] · Seau [px-seau] · Pixel-art [px-crayon, px-ligne,
px-rectpx] · Tranche [tranche]. Un raccourci clavier qui choisit un
membre non affiché fait basculer la famille sur lui.

**R-D7 — Barre contextuelle par outil.** Données pures (`mod-contexte`) :
libellé de la sélection (« Aucune sélection » / « 3 objets » / « rect
r12 »), puis les réglages de l'outil courant en champs inline (forme
courante, largeur, rayon, terrain, tolérance, dureté), les bascules
Grille / Aimant / Unité (les boutons existants y sont déplacés), et, sans
sélection, « Configuration du document… » (dialogue : nom, taille, dpi,
unité, fond — commandes existantes) et « Paramètres de l'appli… » (bulles,
grille par défaut). Chaque champ délègue à l'état existant
(`etat.formeCourante`, `etat.gommeLargeur`, `etat.px.*`…) puis `VL.rendre()`.

**R-D8 — Thème.** Variables `--aff-*` en tête de `vectorlab.css` (fond
#2b2b2b, barres #232323, canevas #262626, texte #d0d0d0, muet #9a9a9a,
sélection #2b6fd6, cyan #22c3d8, violet #cf6fe3, bordure #3a3a3a) ; les
anciennes couleurs codées en dur sont remplacées par les variables dans
une couche finale (sans réécrire les lots) ; champs 24 px, rangées 28 px,
texte 12 px, coins 4 px ; curseurs `input[type=range]` stylés (piste 4 px,
poignée ronde 12 px blanche cerclée) ; `select` sombres ; menus #1e1e1e.

**R-D9 — Preuve.** Chaque lot : banc node RED puis vert pour les modules
purs ; preuve en réel sur 8799 à 1400 × 900 : hauteurs mesurées
(`offsetHeight`) des six bandes, familles qui basculent au raccourci,
menus qui exécutent (un objet dupliqué par le menu Edition), onglets qui
ouvrent la bonne section et se souviennent au rechargement, rangées de
calques ≥ 32 px avec vignette, Navigateur qui suit le zoom, phrase
d'état qui change avec l'outil, audit de lisibilité (aucun `scrollWidth`
> `clientWidth`, aucun bouton tronqué) dans les deux personas ;
déploiement vérifié par hash-object.

## 2. Ce qui n'est pas fait (assumé)

Mise en page, IA Canva, Canaux, dock déplaçable (les groupes ont un ordre
fixe), préréglages de fenêtre, Studios, insertion 3D, notes / index /
tables des menus Texte (entrées absentes, pas grisées : un menu ne montre
que ce que le Vectorlab sait faire, sauf les entrées structurantes
d'Affinity gardées grisées pour la ressemblance quand elles annoncent une
capacité proche — listées dans `mod-menus`).

## 3. Rangée de calque Affinity (contrat)

`.calque` = grille 3 colonnes : chevron (groupes futurs, vide), vignette
26 × 26 sur damier (`vignette_calque_svg`), nom (double-clic renomme),
œil à droite ; hauteur 34 ; sélectionnée = fond `--aff-selection`, texte
blanc ; verrou = cadenas à côté de l'œil ; en tête du panneau : « Opacité
[100 % ▾] [Normal ▾] » agissant sur le calque actif — le mode de fusion
de calque est un champ nouveau `calque.fusion` (16 modes SVG, compilé en
`style="mix-blend-mode"` sur le `<g data-calque>`), commande
`op_calque_fusion`, refusé si inconnu, absent = normal (miroir pytest) ;
en bas : ✎ (renommer) · Réglage (→ onglet Pixel, ajustements) · Masque (→
Apparence, masque) · Calque pixel (→ Image, poser) · FX (→ Apparence,
effets) | Groupe (grouper la sélection) · Nouveau calque · Supprimer.

## 4. Lots

| Lot | Contenu | Plan |
|---|---|---|
| R1 | charpente : barre de menus (`mod-menus`), pastilles, barre contextuelle (squelette), onglet de document, barre d'état (`mod-statut`), persona Export → onglet | `2026-09-18-vectorlab-relooking-r1-charpente.md` |
| R2 | colonne d'outils : `mod-icones`, `mod-familles`, flyouts verticaux, raccourcis affichés | `…-r2-outils.md` |
| R3 | pile de droite : `mod-onglets`, trois groupes, Calques Affinity + `calque.fusion`, Navigateur, Transformer, Historique | `…-r3-pile.md` |
| R4 | thème et densité : variables, champs, curseurs, menus, canevas uni | `…-r4-theme.md` |
| R5 | barre contextuelle par outil : `mod-contexte`, Configuration du document, Paramètres | `…-r5-contexte.md` |
| R6 | raffinements : Histogramme, bulles riches (titre + gestes), aide Raccourcis, nom de planche sur la page, audit final des deux personas | `…-r6-raffinements.md` |
