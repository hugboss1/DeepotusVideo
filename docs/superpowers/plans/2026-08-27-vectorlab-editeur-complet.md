# Vectorlab éditeur complet — formats, couleur vraie, unités & cotes vives

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, session du 27/08). Steps use checkbox (`- [x]`) syntax.

> Ordre utilisateur du 27/08 (verbatim condensé) : « vectorlab ne soit pas
> cantonné au preset vitrail — éditer tout type d'illustration
> vectorielle ; commencer un nouveau document, choisir son format ; une
> palette plus étendue avec un véritable sélecteur de couleur en RGB ou en
> CMY ; toute autre fonctionnalité classique d'un éditeur vectoriel best
> of class ; un outil règle au choix en mm/cm/inch ; voir les mesures
> s'afficher en temps réel le long du geste, en accord avec ce que je
> dessine (longueur/largeur pour les formes, rayon/diamètre pour les
> cercles/ellipses…) ». Expansion COMMITTÉE avant le code (patron 0→6).

> **RELEVÉ (27/08) : CHANTIER LIVRÉ, DÉPLOYÉ, PROUVÉ EN RÉEL, NETTOYÉ.**
> Huit commits T1→T8 + preuve. TDD tenu : RED constaté à chaque module
> (unites 17, couleur 15, classiques 19, formats +7 — **41 contrôles qa
> neufs, 275 cumulés**), un pin de test corrigé contre sa propre règle
> (6,35 mm → 6,4 : arrondi demi-haut toPrecision(12), patron du
> sérialiseur) ; banc vector 20 tests, cards_face 147 verts ; déployé
> sha-vérifié (10 fichiers statiques, backend intact, santé 2.5.0).
> **Preuves app réelle** (gestes pointer synthétiques, DOM) : select des
> 9 formats servi, A4 → 2480×3508 px, unités mm/300, taille reflétée
> verrouillée, bouton d'unité « mm », vitrail REPLIÉ ; **cotes vives
> pendant le geste** : rect « 42 × 21 mm », cercle Maj « r 12,9 · ⌀ 25,7
> mm », outil mesure « 25,7 mm ∠ 0° » SANS rien créer, outil ligne
> « 50,8 mm ∠ 0° » → segment né ; **nuancier par la pastille du
> panneau** : CMJN 100/0/0/0 → #00FFFF, ＋ palette du document
> (`doc.palette`), Appliquer → fond ET rendu DOM #00FFFF, popover
> refermé ; cycle d'unité mm→cm par le bouton puis **annulé** (vraie
> commande) ; X saisi 50 mm → bbox exacte ; centreH d'un objet seul →
> page (1240 px exact) ; dupliquer +1, miroir, rayon 24 posé. Nettoyage :
> doc jetable archivé, les 2 docs réels seuls restants.

**Goal :** le Vectorlab devient un éditeur vectoriel généraliste : formats
de document à la création (A4/A5/carré/16:9/carte… px ou mm), unités
d'affichage px/mm/cm/in portées par le document (règles, cotes, panneau),
vrai sélecteur de couleur (SV+teinte, RGB, CMJN naïf, hex, palette du
document + palette étendue + récentes), cotes EN DIRECT le long de chaque
geste (L×H, r/⌀, longueur∠angle, Δ), et le socle des classiques :
dupliquer, copier/coller, flèches clavier, miroir H/V, aligner/distribuer,
rayon d'angle, panneau X/Y/L/H numérique, outil ligne, outil mesure,
zoom 100 %/ajuster. Le vitrail reste à un clic mais cesse d'occuper le
panneau : replié par défaut.

**Architecture :** trois modules PURS nouveaux ou étendus, bancables node
RED d'abord — `mod-unites.js` (conversions px↔mm/cm/in par dpi, formatage,
libellés de cote), `mod-couleur.js` (hex↔rgb↔hsv↔cmjn, palette par défaut
générée, ops palette du document), `mod-doc.js` (+ op_dupliquer, op_miroir,
op_aligner, op_distribuer, op_rect_rayon — les bboxes d'alignement sont
FOURNIES par l'appelant, patron op_redimensionner) ; l'UI (core, tools,
style, biblio) ne fait que traduire. Le document JSON gagne deux champs
OPTIONNELS rétro-compatibles : `unites {affichage, dpi}` et `palette []`.

**Tech stack :** vanilla ESM, banc qa node (217 contrôles à garder verts),
miroirs pytest test_vector_docs (section P), zéro dépendance nouvelle,
zéro dépense API.

---

## Décisions (tranchées avant le code)

**E1 — Modèle rétro-compatible.** `doc.unites = {affichage: "px"|"mm"|
"cm"|"in", dpi: entier 24..1200}` et `doc.palette = ["#RRGGBB", …]`,
OPTIONNELS : `parserDoc` les accepte et les valide mollement (types ;
affichage inconnu → refus), les documents existants (« Baie vitrail -
demo », « Vitrail - baie generee ») s'ouvrent inchangés (px/96 implicite,
palette vide). `compilerSVG` ne change pas (le SVG reste en px — l'unité
est une AFFAIRE D'AFFICHAGE ; le pont mm réel de l'impression 3D lira
`unites.dpi`). Aucun champ n'est écrit tant que l'utilisateur n'y touche
pas.

**E2 — `mod-unites.js` (pur).** `pxParUnite(unite, dpi)` (px:1,
mm:dpi/25.4, cm:dpi/2.54, in:dpi) ; `versUnite/depuisUnite` ;
`formatMesure(px, unites)` avec précision par unité (px arrondi entier,
mm 1 déc., cm 2, in 2, virgule française) ; `libelle_mesure(kind, geom,
unites)` — `rect {w,h}` → « L × H », `ellipse {rx,ry}` → cercle si
|rx−ry| ≤ 0,5 px → « r … · ⌀ … » sinon « rx × ry », `segment {dx,dy}` →
« longueur ∠ angle° » (angle écran, 1 déc.), `delta {dx,dy}` →
« Δ dx ; dy ». Tout passe au banc qa (`unites.test.mjs`) RED d'abord.

**E3 — Règles et sélecteur d'unité.** `dessinerRegles` (core.js) gradue
dans l'UNITÉ D'AFFICHAGE : pas « joli » choisi dans {1,2,5}×10^k unités,
le plus petit dont l'écart écran ≥ 44 px, sous-graduations ÷5, étiquettes
sans suffixe. Le suffixe vit sur un BOUTON CYCLIQUE dans la barre (px →
mm → cm → in), qui écrit `doc.unites` par `executer` (annulable, sauvé
avec le document). Le dpi vient du document (posé à la création par le
format — E5) ; il n'est pas éditable en place en v1 (dit au survol du
bouton).

**E4 — Le sélecteur de couleur (popover) + palettes.** Conversions PURES
dans `mod-couleur.js` : `hexVersRgb`/`rgbVersHex` (strict #RRGGBB),
`rgbVersHsv`/`hsvVersRgb`, `rgbVersCmjn`/`cmjnVersRgb` (naïf, SANS profil
ICC — assumé et dit dans l'UI : « CMJN indicatif »), `palette_defaut()`
générée = 48 nuances (12 teintes × 3 clartés + 12 neutres du blanc au
noir), toutes hex valides et uniques ; `op_palette_ajouter/retirer(doc,
hex)` (dédoublonnée, annulable, sauvée). Le POPOVER (partie DOM de
mod-couleur, `VL.ouvrirNuancier(hexInitial, onChoix)`) : carré
saturation/valeur (canvas) + barre de teinte + champs R/G/B (0-255),
C/M/J/N (%), hex, aperçu avant/après, palette du document (＋ ajouter /
✕ retirer), 48 nuances par défaut, 10 récentes (session). Il REMPLACE les
`input[type=color]` du panneau Apparence (fond, contour, stops de
dégradé) par des pastilles-boutons ; la palette vitrail (fiche épinglée)
ne bouge pas. Validation = UNE commande ; Échap/clic dehors = rien.

**E5 — Formats à la création (bibliothèque ET pont cartes).** La rangée
de création de la bibliothèque gagne un select FORMATS (table pure dans
mod-biblio, testée) : Libre px (la taille saisie) · Carré 2048 ·
16:9 1920×1080 · 9:16 1080×1920 · A4 portrait/paysage 210×297 mm @300 ·
A5 148×210 mm @300 · Carte poker 63,5×88,9 mm @300 · Vitrail 640×960.
`formatVersDoc(id, tailleTexte)` → `{w, h, unites}` (les formats
physiques posent `{affichage:"mm", dpi:300}` et calculent les px ; les
formats px posent px/96 ; « Libre » lit la taille saisie). Le champ
taille REFLÈTE le format choisi et redevient éditable en Libre.
`docVierge` gagne `unites` optionnel. Le pont cartes (mod-face) pose
`{affichage:"mm", dpi:g.dpi}` sur ses documents (la carte est un objet
physique).

**E6 — Cotes vives le long du geste (mod-tools).** Une étiquette SVG dans
le groupe d'aperçu (`text` à 12/zoom, halo `paint-order:stroke` pour la
lisibilité sur tout fond, posée à +14/zoom du curseur) affichée PENDANT :
tracé rect (L × H), tracé ellipse (r · ⌀ ou rx × ry), redimensionnement
(L × H de b1), déplacement (Δ), plume (longueur ∠ angle du segment en
cours), ligne et mesure (longueur ∠ angle) ; la rotation garde son ° ;
TOUT en unité d'affichage via `libelle_mesure`. Zéro nouvelle mutation :
l'étiquette vit et meurt avec l'aperçu.

**E7 — Deux outils nouveaux.** « Ligne » (raccourci L, glyphe ╱) : un
DRAG pose un segment `path M…L…` au style courant (contour) — une
commande au pointerup, cote vive pendant. « Mesure » (raccourci M, glyphe
⤢) : le même drag affiche longueur/∠/Δ et ne committe RIEN (aucune
entrée d'historique). Boutons ajoutés au rail d'outils, raccourcis dans
core.js.

**E8 — Le socle des classiques.** Ops PURES nouvelles dans mod-doc
(banc `classiques.test.mjs` RED d'abord) :
- `op_dupliquer(doc, ids, dx=12, dy=12)` → clones décalés, IDS NEUFS
  RÉCURSIFS (groupes compris), retourne les ids ; Ctrl+D.
- Presse-papiers INTERNE : Ctrl+C clone la sélection en mémoire, Ctrl+V
  colle par `op_dupliquer`-like décalé de +12 par collage successif
  (UI seule — la pureté est déjà dans op_ajouter/op_dupliquer).
- Flèches clavier : ±1 px (±10 avec Maj) par `op_deplacer`.
- `op_miroir(doc, ids, axe "h"|"v")` : symétrie de la GÉOMÉTRIE BRUTE
  autour du centre de la bbox FOURNIE (rect/ellipse/path — points ET
  poignées ; texte : position seule, glyphes non réfléchis — dit).
  Limite v1 assumée (même esprit que le resize) : un objet déjà tourné
  réfléchit sa géométrie brute.
- `op_aligner(doc, paires, mode)` / `op_distribuer(doc, paires, axe)` —
  `paires = [{id, bbox}]` FOURNIES par l'appelant (le DOM mesure, l'op
  reste pure — patron op_redimensionner) ; modes gauche/centreH/droite/
  haut/centreV/bas ; distribution à écarts égaux (≥3 objets). UI : une
  sélection UNIQUE s'aligne sur LA PAGE (bbox du document), plusieurs
  s'alignent sur la bbox de sélection — le classique.
- `op_rect_rayon(doc, ids, rayon)` : le `rx` des rects (compilerSVG
  l'émet déjà) — input « Rayon » dans Apparence quand un rect est
  reflété.
- Panneau Position/Taille : X/Y/L/H numériques EN UNITÉ D'AFFICHAGE en
  tête d'Apparence (lit la bbox de sélection, écrit op_deplacer /
  op_redimensionner) — le « transform panel » classique.
- Zoom : Ctrl+0 = ajuster le document à la scène, Ctrl+1 = 100 %.

**E9 — Le vitrail devient un MODE discret.** Le panneau Vitrail passe
dans un `<details>` replié par défaut (état mémorisé `dz_vl_vitrail`,
localStorage) — l'éditeur s'ouvre généraliste, le vitrail reste à un
clic. Rien d'autre ne bouge (fiche épinglée, générateur, mesures).

**Hors périmètre v1 (assumé, dit).** CMJN calibré ICC/pantones ; édition
du dpi après création ; dégradés sur le contour ; extrémités de flèches ;
poignées Bézier individuelles en mode nœuds (limite v1 du plan mère,
inchangée) ; import SVG externe ; styles de texte au caractère. Rien de
tout cela ne bloque « éditer tout type d'illustration vectorielle ».

## Structure de fichiers

```
frontend/vectorlab/js/mod-unites.js    NEUF — pur (E2)
frontend/vectorlab/js/mod-couleur.js   NEUF — pur (E4) + popover DOM
frontend/vectorlab/js/mod-doc.js       + ops E8 ; parserDoc accepte E1
frontend/vectorlab/js/mod-biblio.js    + FORMATS/formatVersDoc (E5)
frontend/vectorlab/js/mod-tools.js     + cotes vives, ligne, mesure (E6/E7)
frontend/vectorlab/js/mod-style.js     + pastilles→nuancier, X/Y/L/H,
                                       aligner/distribuer/miroir/rayon
frontend/vectorlab/js/core.js          + règles en unités, bouton d'unité,
                                       raccourcis (L/M/flèches/Ctrl+D/C/V/0/1)
frontend/vectorlab/index.html          + outils ╱ ⤢, bouton unité, select
                                       format, details Vitrail
frontend/vectorlab/vectorlab.css       + nuancier, étiquettes, details
frontend/vectorlab/qa/unites.test.mjs      NEUF — RED d'abord
frontend/vectorlab/qa/couleur.test.mjs     NEUF — RED d'abord
frontend/vectorlab/qa/classiques.test.mjs  NEUF — RED d'abord
frontend/vectorlab/qa/biblio.test.mjs      + blocs formats (RED d'abord)
frontend/cardforge/js/mod-face.js      le doc créé porte unites mm/dpi
backend/tests/test_vector_docs.py      section P (miroirs éditeur complet)
```

## Tasks (TDD, une par commit)

- [x] **T1 unités** : qa `unites.test.mjs` RED (conversions exactes
  300 dpi : 300 px = 25,4 mm = 2,54 cm = 1 in ; formatMesure px/mm/cm/in ;
  libelle_mesure rect/cercle/ellipse/segment/delta) → mod-unites.js →
  GREEN → commit
- [x] **T2 couleur pure** : qa `couleur.test.mjs` RED (hex↔rgb strict,
  rgb↔hsv aller-retour, rgb↔cmjn naïf bornes 0/100, palette_defaut 48
  uniques valides, op_palette_ajouter dédoublonne / retirer, parserDoc
  accepte palette et REFUSE une non-liste) → mod-couleur.js (pur) +
  parserDoc (E1 : unites + palette) → GREEN → commit
- [x] **T3 classiques purs** : qa `classiques.test.mjs` RED
  (op_dupliquer ids neufs récursifs + décalage ; op_miroir h/v rect/
  ellipse/path exactes, texte position seule ; op_aligner 6 modes sur
  paires ; op_distribuer écarts égaux, refus < 3 ; op_rect_rayon borné
  ≥ 0 et rects seuls) → ops dans mod-doc → GREEN → commit
- [x] **T4 formats** : blocs RED dans biblio.test.mjs (FORMATS ≥ 8
  entrées, formatVersDoc A4 = 2480×3508 px @300 + unites mm, carte
  poker 750×1050, libre lit la taille, vitrail 640×960 px) →
  mod-biblio + rangée de création (select) → GREEN → commit
- [x] **T5 UI unités & cotes & outils** : règles en unités + bouton
  cyclique (core), étiquette d'aperçu + cotes sur rect/ellipse/resize/
  move/plume (mod-tools), outils ligne ╱ et mesure ⤢ (+ raccourcis
  L/M), Ctrl+0/Ctrl+1 ; node --check → commit
- [x] **T6 UI couleur** : popover nuancier (SV+teinte+RGB+CMJN+hex+
  palettes), pastilles fond/contour/stops, ＋/✕ palette du document ;
  details Vitrail replié (E9) ; node --check → commit
- [x] **T7 UI classiques** : X/Y/L/H en unités, rangées Aligner/
  Distribuer/Miroir/Dupliquer/Rayon dans Apparence, Ctrl+D/C/V,
  flèches ±1/±10 ; node --check → commit
- [x] **T8 miroirs + pont cartes** : section P pytest RED→GREEN
  (mod-unites/mod-couleur existent et sont branchés, index.html porte
  les outils et le bouton d'unité, mod-face pose unites mm) ; banc
  vector + qa node complets verts → commit
- [x] **T9 déploiement & preuve réelle** : sha+déploiement statique,
  preuve navigateur (créer un A4 → règles en mm, tracer un rect → cote
  vive « L × H mm » constatée dans l'aperçu DOM, cercle → « r · ⌀ »,
  outil mesure, nuancier : CMJN→hex appliqué à un fond par la vraie
  UI, palette du document sauvée puis rouverte, aligner 3 objets,
  dupliquer, miroir, X/Y/L/H, unité cyclée px→mm sauvée) ; nettoyage
  des docs jetables ; relevé ici ; push
