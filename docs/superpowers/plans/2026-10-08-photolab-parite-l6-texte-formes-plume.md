# Photolab parité L6 (t156) — texte, formes, plume, tracés

> Relevé : `specs/2026-10-08-photolab-bientot-inventaire.md` (lot 6) et `-liste.md` ; amont photocraft v0.3.0
> `ui-egui/src/type_tool.rs`, `type_panels_ui.rs`, `vector_ui.rs`, `preset_panels.rs`, `palette.rs`, `view_cmds.rs` ;
> moteur `type_cmds.rs`, `type_styles_cmds.rs`, `vector_cmds.rs`. Base : origin/main 70fb958c, branche
> `chantier/photolab-parite-l6`.

## Périmètre (35 éléments « bientôt »)

- Outils (9) : Texte (T), Rectangle, Ellipse, Triangle, Polygone, Trait, Forme personnalisée (U), Plume (P), Sélection
  de tracé (A).
- Panneaux (3 absents) : Caractère, Paragraphe, Tracés ; et Fenêtre › Caractère, Paragraphe, Tracés, Glyphes, Styles de
  caractère, Styles de paragraphe, Formes, Styles (8) ; Texte › Panneaux › (5).
- Texte › Taille de l'aperçu des polices (5), Options de langue (4) ; Édition › Rechercher.

## Faits établis (vrai moteur, 08/10)

- `type.fonts` -> `{families}` : les polices du système (le navigateur du même poste les affiche).
- `type.create {x, y | box, text, font, size, color, align…}` -> `{layer, bounds}` ; « New Type Layer » ; nom = première
  ligne (40 car.). `doc.inspect` donne `text {font, sizePt, text}` au calque « Type ».
- `type.info` -> runs (styles par plage, `size_pt`, `font_family`, `color {c:[r,g,b,a]}`…), paragraphes, lignes, `shape`
  Point|Box, `transform`. `type.setStyle {range?, …}` « Set Type Style » ; `type.edit {text | replace}` « Edit Type » ;
  `type.insertText` « Insert Glyph » -> `{caret}`.
- Styles : `type.characterStyle.*` / `type.paragraphStyle.*` ; liste `{styles:[{id,name,…}], current:{character,
  characterOverride, paragraph, paragraphOverride}}` ; id 0 = aucun / Paragraphe de base.
- `shape.create {kind rect|roundedRect|ellipse|polygon|star|line|path, rect, radii, sides, from, to, weight, fill,
  stroke}` « New Shape Layer » ; triangle = polygone 3 côtés. `shape.presets.list` : groupes Symbols, Arrows…
- `path.set {name: work, path}` « Work Path » ; `path.rename` « Save Path » ; `path.toSelection` « Make Selection » ;
  `select.toWorkPath` « Make Work Path » ; `path.stroke` exige un calque de pixels ; `path.list` / `path.info`.
- Préréglages sans rendu : vignettes de forme et de style rendues par le pont (`/presets/{forme|style}/vignette.png`,
  document temporaire refermé, comme les motifs).

## Décisions

| Entrée | Décision |
|---|---|
| Outil Texte | **Adapté** : clic = texte de point, glisser ≥ 4 px = texte de paragraphe, clic sur un calque de texte = l'éditer ; la saisie se fait dans un éditeur posé sur la toile (zone de texte à la police et à la taille du calque), validée par Ctrl+Entrée, Échap (comme la référence et l'amont), clic ailleurs ou changement d'outil ; Annuler par le bouton. Une validation = `type.create` ou `type.edit {text}`. Le moteur rend le texte (D1) |
| Barre d'options du texte | orientation, police (liste des polices du système, aperçu à la taille choisie), style, taille, anti-crénelage, alignement, couleur, valider / annuler |
| Caractère, Paragraphe | **Repris** (champs de l'amont : police, style, taille, interlignage, crénage, approche, échelles, décalage, couleur, faux gras / italique, capitales, souligné, barré ; 7 alignements, retraits, espaces, césure) ; valeurs lues par `type.info` ; appliquées à la sélection de l'éditeur (range) sinon au calque |
| Glyphes | **Adapté** : catégories de l'amont (Latin de base… Flèches, Ornements) sans lecture de la table de la police ; récents (12) ; insertion `type.insertText` au curseur |
| Styles de caractère / paragraphe | **Repris** : liste, « + » des remplacements, appliquer (Alt = effacer les remplacements), nouveau, dupliquer, supprimer, redéfinir, effacer le remplacement, renommer |
| Taille de l'aperçu des polices | **Repris et branché** (l'amont ne le lit pas) : taille des noms dans la liste des polices |
| Options de langue | **Adapté** : préférence d'écran ; Moyen-Orient montre la direction (G->D, D->G) au Paragraphe, Asie orientale l'orientation verticale ; Composeur : bascule mémorisée |
| Formes (U) | **Repris** : glisser (Maj carré / 45°, Alt depuis le centre), aperçu du contour, `shape.create` ; barre : remplissage (case + couleur), contour (épaisseur, couleur, alignement), rayon, côtés, épaisseur du trait, forme personnalisée |
| Plume (P) | **Repris** : clic = sommet, glisser = sommet lisse, clic sur le premier = fermer, Entrée = terminer, Échap = abandonner, Ctrl+Entrée = sélection ; mode Tracé (`path.set` travail) ou Forme (`shape.create kind path`) |
| Sélection de tracé (A) | **Repris** : glisser = déplacer le tracé cible (calque de forme : `shape.edit {move}` ; sinon le tracé de travail) |
| Tracés | **Repris** : lignes (enregistrés, de travail, du calque), vignettes, clic = le montrer sur la toile (mieux que l'amont), double-clic = enregistrer / renommer, pied : remplir, contour, sélection, tracé depuis la sélection, nouveau, supprimer |
| Formes, Styles (panneaux) | **Repris** : navigateurs de préréglages (comme Dégradés / Motifs) ; Formes : clic = forme de l'outil, double-clic = la placer ; Styles : clic = l'appliquer (Maj = ajouter) |
| Rechercher (Ctrl+K, catalogue) | **Repris** (palette de l'amont) : recherche dans les entrées de menu ACTIVES et les outils, ↑ ↓ Entrée Échap |

## Relevé d'exécution (08-09/10/2026)

**Défauts de la liste blanche trouvés à l'écran (corrigés dans le pont, avec bancs de refus).**
- `path` était refusé partout comme fichier : pour `path.set`, `shape.create`, `shape.edit`, `shape.presets.new`, un OBJET
  (tracé vectoriel) ou « work » est admis (`COMMANDES_TRACE`) ; une chaîne « fichier » cachée dedans reste refusée.
- `type.create` résume ses clés (« …character keys ») : il admet celles de `type.setStyle` (sans `layer`, `range`).
- `align` absent de `type.setStyle` et tronqué (« justify… ») pour `type.create` : énumération complète déclarée
  (`CHAMP_ALIGN`) ; le moteur nomme `justify` la justification « dernière ligne à gauche » (l'écran traduit).

**Autres défauts corrigés.** Panneau Tracés dessiné deux fois (deux dessins asynchrones) -> jeton ; bonus des outils de la
recherche appliqué sans correspondance (tous les outils remontaient) -> trouvé par le banc ; « Récents » déjà traduit
« Recent » -> « Récemment utilisés ».

**Bancs.**
- `test_photolab_texte` : 44/44 (liste blanche, vignettes de forme et de style, parcours sur le vrai moteur, route).
- Mutations : 17 sur 17 tuées (M15 « chaîne admise comme tracé » survivait : refus d'une chaîne qui n'est ni un tracé ni « work » ajouté), sources restaurées et vérifiées par `cmp`.
- QA node : toutes les séries vertes, dont la nouvelle `texte` (67) ; bancs figés mis à jour (outils 1.5 et 2.11c,
  espaces 1.2-1.10, 2.5, 5.4, panneaux 11.3, zones 2.3-2.4, panneaux3 6.4, test_photolab_espaces 1c).
- Bancs Photolab et `test_i18n_l0` verts, hors les 7 rouges d'environnement connus.

**Preuve sur 8799** (gestes réels, vrai backend jetable, FR puis EN) :
- Formes : rectangle, rectangle arrondi avec contour, cercle (Maj), triangle, hexagone, trait à 0° (Maj), cœur : sept
  « New Shape Layer » ; aperçus pendant le geste.
- Plume : deux angles, un sommet lisse, clic sur le premier -> « Work Path » ; Tracés : double-clic -> « Tracé 1 » (« Save
  Path »), clic -> tracé montré sur la toile, sélection, contour (pinceau), remplissage ; mode Forme -> calque de forme ;
  Sélection de tracé : forme déplacée de (20, 30) (« Edit Shape »).
- Formes / Styles : groupes traduits, vignettes 64 px rendues par le moteur ; clic = forme de l'outil (Étoile), double-clic =
  placée ; style « Ombre portée » appliqué (« Apply Style: Drop Shadow ») ; un seul document ouvert.
- Texte : clic -> éditeur, Ctrl+Entrée -> « New Type Layer » ; clic sur le calque -> édition ; « monde » sélectionné passé à
  40 pt (plages 24 / 40) ; Échap valide (« Edit Type ») ; boîte de paragraphe (Box 180 × 70) ; centré, justifié, justifié
  tout, retrait 12 pt ; glyphe € inséré (« Insert Glyph ») et récent ; police Arial par la liste (aperçu 24 px après Texte ›
  Taille de l'aperçu › Très grande, coché) ; style de caractère créé ; Paragraphe de base listé.
- Rechercher : Ctrl+K, « Dupliquer le calque — Calque », Entrée sur « Ellipse — Outils » choisit l'outil.

**Recomptage** `lister_bientot.mjs` : 157 (192 avant).
