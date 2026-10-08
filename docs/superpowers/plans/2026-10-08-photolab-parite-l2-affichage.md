# Photolab parité L2 (t152) — menu Affichage : zooms, règles, grille, repères, extras, aimantation

> Relevé : `specs/2026-10-08-photolab-bientot-inventaire.md` §3 (menu Affichage de la référence, avec ses
> raccourcis) ; amont `crates/ui-egui/src/view_cmds.rs`, `state.rs` (Extras), `engine/src/prefs.rs`
> (GuidesGridAndSlices), `snap_ui.rs`. Base : origin/main 92bec8ed, branche `chantier/photolab-parite-l2`.

## Faits établis (vrai moteur, 08/10)

- `view.newGuide`, `moveGuide`, `deleteGuide`, `clearGuides`, `newGuideLayout` modifient le document et posent des
  états d'historique : « New Guide », « Move Guide », « Delete Guide », « Clear Guides », « New Guide Layout ».
  `newGuideLayout` répond `{horizontal, vertical}` (le nombre de repères créés).
- **`doc.inspect` ne rend PAS les repères.** Ils vivent dans `Document.guides {horizontal, vertical}`, que le `.pcraft`
  enregistre dans `manifest.json` (`document.guides`). Voie de lecture : `image.duplicate`, puis `doc.save` de la copie
  en `.pcraft` sous `rendus/`, `doc.close` de la copie, `doc.select` de l'original, lecture du zip, effacement du
  fichier. Coût mesuré : 130 ms en 1920 × 1080. L'original reste intact (même révision, même historique).
- Noms d'historique des opérations qui déplacent les repères : « Canvas Size », « Image Size », « Flip Canvas
  Horizontal », « Crop », « Trim ».

**Valeurs amont reprises :**
- extras actifs ; règles et grille masquées ; repères visibles ; aimantation active ; repères non verrouillés ;
- Afficher : contours de la sélection, grille de pixels et aperçu du pinceau actifs ; contours du calque inactifs ;
- Aimanter à : tout actif ;
- seuil d'aimantation : 8 px d'écran ;
- grille d'un pouce (selon les ppi du document) en 4 subdivisions ;
- couleurs : repères `#4affff`, grille `#8c8c8c` ;
- Taille d'impression : 72 / ppi ; Adapter le(s) calque(s) : bornes des calques sélectionnés, marge de 20 px.

## Décisions

| Entrée | Décision |
|---|---|
| Zoom avant / arrière, Adapter à l'écran, 100 %, 200 %, Taille d'impression, Adapter le(s) calque(s) | **Repris** : fonctions de la vue |
| Symétrie horizontale | **Repris** : miroir de la vue seulement. Une conversion commune sert au contour de sélection, au Navigateur et au recadrage. |
| Modes d'écran (standard, plein écran avec menus, plein écran), touche F pour passer de l'un à l'autre | **Adapté** : le plein écran masque les barres et panneaux de la page (le Photolab est dans un cadre de l'application) ; Échap revient au mode standard |
| Extras (Ctrl+H) ; Afficher › contours du calque, contours de la sélection, grille (Ctrl+'), repères (Ctrl+;), repères du canevas, grille de pixels, aperçu du pinceau, Tout ; Options d'affichage des extras… | **Repris** |
| Règles (Ctrl+R), avec création de repères en glissant depuis une règle, déplacement et suppression en glissant (outil Déplacement) | **Repris** : par le moteur (`newGuide`, `moveGuide`, `deleteGuide`) |
| Aimanter (Maj+Ctrl+;) ; Aimanter à › repères, grille, calques, limites du document, Tout | **Repris** pour les sélections rectangle et ellipse, le recadrage, le déplacement de calque et les repères |
| Verrouiller les repères (Alt+Ctrl+;) | **Repris** |
| Aperçu pixel art | **Repris** : pixels francs à tout zoom |
| Adapter le plan de travail, repères du plan de travail, maillage, épingles, aperçu du motif | **Écarté** (pas de plans de travail ni de déformation à épingles) |
| Tracé cible (L6), compteur, tranches, notes, aimanter aux tranches (L10), repères intelligents | restent « bientôt » |

Les options d'affichage sont des préférences de l'écran : elles sont gardées par navigateur (stockage local), sans rien
écrire dans le moteur.

## Tâches

- **A** — `PM.reperes(s)` (séquence sous verrou, cache par génération, document et révision) et route
  `GET /api/photolab/reperes`. Banc `test_photolab_affichage.py` sur le vrai moteur : lecture après création,
  déplacement, suppression et annulation ; original intact ; aucun fichier laissé ; cache.
- **B** — module pur `js/mod-affichage.js` (QA `qa/affichage.test.mjs`) :
  - options et bascules, décoration du menu Affichage ;
  - zoom de taille d'impression, bornes des calques ;
  - pas de la grille, graduations des règles, `aimanter` ;
  - règle de relecture des repères ; cycle des modes d'écran.
- **C** — `mod-vue.js` : miroir (`versEcran`, `versDoc`, `rectVersEcran`) et pixel art ; contour de sélection,
  Navigateur et recadrage passent par la conversion commune.
- **D** — DOM : repères, grille, grille de pixels et contours du calque dessinés dans `#fourmis` ; règles ; gestes des
  repères ; modes d'écran ; aimantation dans les sélections, le recadrage et le déplacement.
- **E** — menus (`TRAITES_PAR_ECRAN`, coches), raccourcis, textes fr/en, fiche didactique, mutations, preuve 8799,
  recomptage.

## Relevé d'exécution (08/10/2026)

**Bancs.**
- `test_photolab_affichage` : 15/15 sur le vrai moteur (lecture, original intact, cache, annulation, route).
- QA node : séries vertes, dont la nouvelle `affichage` (70).
- `test_photolab_textes` : 7/7 (deux lignes réécrites plutôt qu'autorisées ; `commun.action.appliquer` réutilisé).
- Bancs Photolab et `test_i18n_l0` : verts, hors les 7 rouges d'environnement connus (identiques sur origin/main).

**Mutations** : 14 sur 14 tuées, sources restaurées et vérifiées par `cmp`.
- Écran : relecture des repères, miroir de `versDoc` et du Déplacement, cible la plus proche, calque déplacé exclu
  des cibles, grille de pixels au-delà de 500 %, Extras, 72 ppi, Règles traitées par l'écran, `rectVersEcran`,
  aimantation du point de geste.
- Pont : clé du cache, copie refermée, fichier temporaire effacé.

**Preuve sur 8799** (gestes réels, vrai backend jetable) :
- Ctrl+R ouvre les règles. Un glisser depuis la règle du haut crée « New Guide » (horizontal à 150, dessiné) ; depuis
  la règle de gauche, un repère vertical aimanté au centre (323 → 320).
- Outil Déplacement : un repère glissé de 150 à 101 donne « Move Guide » ; sorti du document, il donne
  « Delete Guide » ; l'annulation le rétablit (relu).
- Ctrl+' affiche la grille (59 lignes, dont 15 majeures). Ctrl+H masque grille et repères. 200 % ; Taille
  d'impression à 72 ppi = 100 % ; Adapter ; grille de pixels à 800 % (225 lignes), absente une fois l'image ajustée.
- Sélection rectangle aimantée au bord du document (3 → 0) et au repère (98 → 101).
- Miroir : un trait rouge à x = 50 dans le document s'affiche à droite (écran 927 au lieu de 93). Une sélection tracée
  à l'écran donne les bonnes coordonnées dans le document, et le contour suit. Aucun état d'historique : le document
  n'est pas touché.
- F : menus, puis plein écran (barres et panneaux masqués) ; Échap revient au mode standard.
- Le dialogue des extras s'applique (grille éteinte, contours du calque allumés). Les coches du menu sont justes ;
  l'état est gardé par le navigateur.
- Repères verrouillés : un glisser ne les déplace pas. Effacer les repères (commande moteur) donne « Clear Guides »,
  relu (0 repère).
- Écran en anglais vérifié (dialogue, menu View), puis retour au français.

**Défaut du lot précédent trouvé à l'écran** : dans une fenêtre de moins de 900 px, le sélecteur d'espace (t151)
recouvrait la barre de menus. Il s'efface désormais ; le choix reste dans Fenêtre.

**Recomptage** `lister_bientot.mjs` : 185 entrées de menu + 16 outils + 11 onglets + 2 boutons = 214 (244 avant).

**Pas de fiche didactique** : les entrées du menu Affichage n'ont pas d'élément de page stable à survoler (les règles
sont cachées par défaut).
