# Vectorlab — lot D5 « Couleur et motif » (plan, 09/11/2026)

> **Spec** : `docs/superpowers/specs/2026-11-08-illustrator-vectorlab-inventaire.md`, décision D5 (« Recolorer
> l'illustration, éditeur de motif (pavage grille / brique / hexagone), puis pinceaux artistique, dispersion et
> motif »). C'est le dernier lot de l'inventaire Illustrator ; il est enchaîné après D4 à la demande de l'utilisateur.
> **Branche** : `claude/vectorlab-d5-couleur`, tirée d'origin/main 9ccd9224. **Suivi** : t475-t483.
>
> **But** :
> - changer d'un geste les couleurs d'une illustration entière ;
> - faire un motif avec ses propres dessins ;
> - peindre un tracé avec un dessin : étiré, semé ou répété.

## Relevé (code d'origin/main)

### Couleurs

- **Où elles vivent.**
  - `style.fond` vaut un hex, `grad:<id>`, `motif:<id>`, `glob:<nom>` ou `none`.
  - `style.contour` vaut un hex, `glob:` ou `none`.
  - `style.contours[]` liste des `{ couleur, epaisseur }`.
  - Les dégradés (`doc.degrades`) et les motifs (`doc.motifs`) portent aussi des couleurs.
- **Ce qui existe déjà.**
  - Une seule op réécrit des couleurs dans tout le document : `op_couleur_globale_supprimer` (`mod-doc.js:1136`), avec son visiteur `_visiterObjets`.
  - `mod-couleur.js` fournit les conversions (RVB, TSV, TSL, CMJN) et `palette_harmonique(hex, type)` (complémentaire, analogue, triade, tétrade, monochrome).
- **Ce qui manque.** Aucune commande ne recolore une sélection, et rien d'Édition › Couleurs n'existe. Les menus sont plats (`mod-menus.js`), sans sous-menu.

### Motifs

- Ils sont **paramétriques seulement** : `{ type ∈ hachures|points|damier|grille, pas, angle, epaisseur, couleur, fond? }`.
- Code : `mod-effets.js:130-163` (`motif_valider`, `motif_svg`), `op_motif_creer`/`modifier`/`supprimer` (`mod-doc.js:1110-1124`), `_motif` de `mod-pdf.js:236`.
- Un motif ne peut pas contenir d'objets. L'interface (`mod-apparence2.js:162-233`) crée un motif mais n'en modifie aucun.

### Pinceaux

- `mod-pinceauvec.js` (profils plat, fuseau, calligraphie) écrit un chemin **figé** : ni le profil ni les points ne sont gardés.
- Le mécanisme vivant de D2/D3 peut porter un pinceau vivant :
  - un groupe porte une recette, la source `cache` et des enfants `genere` ;
  - le recalcul se fait par empreinte (`vivants_d2_rafraichir` → `deformations_rafraichir`) ;
  - Décomposer passe par `op_derive_detacher`.
- La grille de D2 sait déjà décaler en brique et en hexagone (`mod-repeter.js:145-162`).

## Tâches

### T1 (t475) — Les couleurs d'une sélection, et leur réassignation

`mod-recolorer.js` (neuf, pur).

- **`couleurs_selection(doc, ids)` → `[{ hex, n, ou: [fond|contour|degrade|motif|texte…] }]`**
  - Les couleurs distinctes, triées par usage.
  - Elle visite les groupes, les instances (pas leur symbole), les dégradés et les motifs que la sélection emploie.
  - Les copies générées (`genere`) ne sont pas visitées : c'est leur source qui compte.
  - Une `glob:` est résolue et marquée `globale`.
- **`op_recolorer(doc, ids, table)`** : `table` va de l'ancienne couleur hex à la nouvelle.
  - Elle réécrit `fond`, `contour` et `contours[]`.
  - Un dégradé ou un motif **partagé** avec des objets hors sélection est **cloné** avant d'être modifié : on ne change pas ce qu'on n'a pas sélectionné.
  - Une couleur globale réassignée devient une couleur simple sur les objets visés ; la globale elle-même ne change pas.
  - Refus traduits : aucune sélection, couleur invalide.
- **`op_couleurs_transformer(doc, ids, f)`** applique `f(hex) → hex` à toutes ces couleurs. C'est le socle de T2.
- Banc `qa/recolorer.test.mjs`, écrit rouge d'abord : partage, clones, globales, groupes, instances, copies générées, textes.

### T2 (t476) — Édition › Couleurs

- **Fonctions pures dans `mod-recolorer.js`** :
  - `inverser` ;
  - `niveaux_de_gris` (luminance) ;
  - `saturer(pct)` (de −100 à +100 %, −100 = désaturer) ;
  - `equilibre({ mode: rvb|tsl, a, b, c })` ;
  - `fusion(doc, ids, sens: horizontal|vertical|avant_arriere)`. Elle interpole les **fonds** entre l'objet le plus à gauche et le plus à droite (ou haut / bas, ou dessous / dessus), comme Illustrator : il faut au moins trois objets colorés.
- **Interface** (module neuf `mod-recolorerui.js`) :
  - un bloc « Couleurs » au menu Édition (entrées plates, car il n'y a pas de sous-menu) ;
  - des dialogues pré-remplis avec **aperçu en direct** (`dialogue_apercu` de D2) ;
  - une seule étape d'annulation.

### T3 (t477) — Recolorer l'illustration…

- **Le dialogue** :
  - une ligne par couleur actuelle (pastille, nombre d'usages) → nouvelle couleur (champ couleur) ;
  - des boutons **Harmonie** (règle au choix, depuis la couleur la plus employée), **Réduire à N couleurs** (regroupement des couleurs proches, en Lab), **Mélanger** et **Réinitialiser** ;
  - un aperçu en direct, une seule étape d'annulation.
- **Pures et bancables** : `reduire(couleurs, n)` et `harmoniser(couleurs, regle)`.
- Entrée Édition › **Recolorer l'illustration…**.

### T4 (t478) — Motifs faits d'objets (modèle)

- **Le nouveau type** : `{ type: "objets", pavage, largeur, hauteur, espacement: { h, v }, objets: [...], fond? }`.
  - `pavage` vaut `grille`, `brique_lignes`, `brique_colonnes` ou `hexagone`.
  - Les objets sont en coordonnées de la tuile (0, 0).
- **Les fonctions** :
  - `motif_valider` accepte ce type ;
  - `motif_svg` écrit un `<pattern>` dont la cellule répète les copies décalées : brique = cellule de 2 rangées, hexagone = cellule de 2 rangées décalées d'une demi-tuile ;
  - `mod-pdf.js` (`_motif`) dessine les objets de la cellule en opérateurs PDF.
- **Les ops** :
  - `op_motif_depuis_selection(doc, ids, opts)` crée le motif à partir de la sélection, les objets étant ramenés à leur boîte ;
  - `op_motif_regler(doc, id, opts)` change ses réglages ;
  - `op_motif_contenu(doc, id, ids)` remplace son contenu par la sélection.
- **Garde** : un motif ne se contient pas lui-même, même indirectement.
- Banc : validation, SVG (cellule et décalages), PDF (aller-retour par l'import de D4), cycles refusés.

### T5 (t479) — Éditeur de motif (interface)

- Vecteur › **Créer un motif…** (depuis la sélection) ouvre un dialogue :
  - pavage, espacement H/V, taille de la tuile ;
  - aperçu en direct d'un carré pavé ;
  - **Appliquer aux objets sélectionnés** (fond).
- Onglet Apparence :
  - la liste des motifs du document ;
  - **Modifier…** (le même dialogue) et **Remplacer par la sélection** ;
  - **Supprimer**, qui garde la règle actuelle : les fonds qui l'emploient passent à `none`.
- Les 4 motifs paramétriques restent tels quels.

### T6 (t480) — Pinceaux artistique, dispersion et motif (modèle vivant)

- **La définition** : `doc.pinceaux[id] = { nom, genre: artistique|dispersion|motif, objets, params }`, créée depuis une sélection.
- **Le tracé peint** : un groupe vivant `{ pinceau: { id, params?, empreinte }, enfants: [chemin source cache, ...générés <g>_p<k>] }`, recalculé par empreinte à la fin de `deformations_rafraichir`.
  - **artistique** : le dessin est **étiré le long** du tracé (l'abscisse suit la longueur, l'ordonnée suit la normale). Réglages : échelle de largeur, retournement, étirement proportionnel ou non.
  - **dispersion** : des copies **semées** le long du tracé. Réglages : espacement, taille, rotation (suit le tracé ou fixe), écart latéral, chacun avec un aléa à graine stable, comme la Rugosité de D3.
  - **motif** : le dessin est **répété en tuiles** le long du tracé, chaque tuile courbée comme pour l'artistique. Réglages : espacement, ajustement (étirer pour finir pile, ou couper).
- **Les ops** : `op_pinceau_creer`, `op_pinceau_appliquer(doc, ids, pid, params)`, `op_pinceau_regler`, `op_pinceau_retirer` (rend le tracé seul).
- Décomposer garde le dessin peint en objets ordinaires.
- Banc : géométrie de chaque genre (longueurs, bornes, tuiles), graine stable, empreinte, tracé fermé, définition supprimée (les tracés peints reviennent simples).

### T7 (t481) — Pinceaux (interface)

- Vecteur › **Nouveau pinceau…** (depuis la sélection) : nom et genre.
- Vecteur › **Appliquer un pinceau…** : liste des pinceaux du document, réglages et aperçu en direct.
- Onglet Apparence, section « Pinceau vivant » : recette, **Options…**, **Retirer le pinceau**, **Décomposer**.
- L'outil Pinceau existant (profils) reste inchangé.

### T8 (t482) — Connaissance et guide

- Fiches catalogue des entrées neuves (skill `connaissance-agent`).
- Cartes « Recolorer », « Motifs » et « Pinceaux » au chapitre Vectorlab du guide, en FR et en EN (skill `guide-deepotus`).

### T9 (t483) — Preuve et livraison

- QA complète et bancs Python.
- Preuve 8799 en FR et en EN :
  - recolorer une illustration importée (D4) ;
  - motif en brique appliqué puis exporté en SVG et en PDF ;
  - trois pinceaux sur un même tracé, modifié ensuite.
- PR unique. Installation seulement sur accord.

## Hors lot

- La roue chromatique interactive de Recolorer (une table et des harmonies la remplacent).
- Le mode d'édition de motif « en place » sur la toile.
- Les bibliothèques de nuances et de pinceaux fournies.
- Les pinceaux calligraphique et soies, déjà approchés par les profils.
- La surimpression, CMJN et les profils de couleur.
