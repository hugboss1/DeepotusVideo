# Vectorlab classe Affinity — LOT E : persona Pixel et mode pixel-art — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module pur).

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot E + « Complément au lot E — mode pixel-art type Aseprite vers le
> Tilelab » ; D1 raster en PNG à côté du JSON avec journal d'annulation par
> fichier `.pix<n>.png` ×10 ; D8 une surface, des personas Vecteur / Pixel /
> Export ; D9 modules purs). Branche `chantier/vectorlab-affinity`, après le
> lot B (`6a09007`). Ce plan est COMMIS avant le code.

> **RELEVÉ DE LIVRAISON (17/09/2026) : LOT E LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ — Python touché : RELANCE du backend installé (8765) par l'utilisateur.**
>
> **Livré** (7 commits `c5d9244`→`eea0020`, poussés) : `mod-pixel.js` feuille
> (tampon, pinceau/gomme par estampes à dureté, seau contigu ou global,
> sélections en masque — rect, lasso, baguette, couleur, croître,
> contracter, inverser, bbox —, masque de calque, niveaux / courbes / HSL /
> N&B / seuil par LUT, flou en boîte, clonage, extraction) ;
> `mod-pixelart.js` feuille (Bresenham, rectangle pixel, symétrie, palette
> median cut, quantification, pixelisation au plus proche voisin, raccord
> 3×3 + score, feuille de tuiles + index, bande, pelure) ; backend
> `remplacer_image` (journal `.pix<k>.png` ×10) et `annuler_image`, routes
> `PUT /vector/docs/{id}/images/{name}` → `{name, rev}` et
> `POST …/annuler` (409 à vide) ; modèle `doc.pixelart {tuile, palette,
> symetrie}` + `op_pixelart`, `op_image_rev` (l'href gagne `?v=rev`,
> `image_rev_max`, l'export inline le PNG à la bonne révision sans cache) ;
> UI `mod-persona.js` (onglets Vecteur / Pixel / Export, classe body,
> panneau Export qui délègue aux exports existants) et `mod-pixelui.js`
> (dix outils `px-*` en capture, aperçu incrémental, masque et grille pixel
> en overlay, ajustements, masque de calque, sélection → vecteur,
> pixel-art : tuile, symétrie, palette, quantifier, pixeliser l'image ou la
> sélection vectorielle, raccord 3×3, feuille PNG + JSON, cadres, pelure,
> bande, envoyer vers Tilelab / Spritelab).
>
> **TDD tenu** : RED ×5 (pixel, pixelart, pytest journal + routes, pixel_doc,
> pixel_ui). Bancs : node **814 contrôles** (+86 : pixel 34, pixelart 19,
> pixel_doc 17, pixel_ui 16), pytest `test_vector_docs` **32 passed** (+3).
> Le banc a corrigé deux choses : la palette median cut MOYENNE ses boîtes
> (l'assertion attendait des hex ronds), et la pixelisation échantillonne le
> COIN du bloc (le centre sautait la rangée du haut d'un 8 → 4).
>
> **Prouvé en réel** (8799, données isolées, viewport 1400×900, gestes
> `PointerEvent` synthétiques, lecture DOM) : onglet Pixel → 10 outils
> visibles, 1 vecteur (select), panneaux vectoriels à 0 px ; « Éditer les
> pixels » → tampon **16×16** lu du PNG ; pinceau (12,3)→(12,9) → trait
> **joint**, `?v=2` sur l'href, pixel relu **au serveur** ; gomme → alpha 0 ;
> « Annuler pixels » → rév. 6 → 5, le pixel revient ; seau contigu ; rect
> 4×4 → N&B **seulement dans le masque** ; symétrie H + crayon → (1,13) et
> (14,13) ; ligne pixel ; tuile 8×8 → `body.pixelart`, rendu
> `pixelated`, lignes de tuile ; palette 4 + quantifier ; raccord 3×3 →
> canevas 48×48 visible, score 0,689 ; baguette 54 px, inverser 202, Échap
> 0 ; croître / contracter ; masque de calque → alpha 0 hors sélection ;
> → vecteur → image 3×3 posée à sa place + dialogue Vectoriser ; clonage
> (0,15) → (5,5) ; lasso 48 px ; nouveau cadre → calque « cadres » à 2
> images, pelure en overlay ; bande + feuille **32×16, 2 tuiles** (PNG +
> JSON, ancre stubée) ; → Tilelab → `vector_…_tuile_img4.png` dans la
> Bibliothèque ; persona Export → 6 boutons, PNG 1× déposé ; sauvegarde →
> `pixelart`, `rev 10`, `cadres 2` relus.
>
> **Trois défauts attrapés par la preuve** : le pinceau ne joignait pas ses
> points entre deux `pointermove` (l'aperçu incrémental repartait du dernier
> point sans le segment) ; les outils à rayon visaient le COIN du pixel
> (coordonnée continue − 0,5 = centre entier de mod-pixel, source du
> clonage comprise) ; la feuille refusait tout document mêlé (filtrée à la
> taille de tuile).
>
> **Déployé** : 16 fichiers (=base lot B `0738aa4` vérifiés par
> hash-object) → sauvegarde `_backup_predeploy_2026-09-17f-vectorlab-lotE`
> (8 fichiers) → copie depuis `git archive eea0020` → **16 = cible, 94/94 du
> Vectorlab = cible**, pré-vol `import app.main` OK. **`routes.py` et
> `vector_store.py` touchés : l'utilisateur relance le backend installé.**
>
> **Reste** : la rotation d'un objet image est ignorée par la
> correspondance point → pixel ; le pinceau doux re-mélange légèrement aux
> jointures des segments ; les téléchargements (feuille, bande) et
> l'ouverture du Tilelab sont prouvés par stubs (ancre, `window.open`) ;
> les courbes n'ont qu'un point de contrôle (128 → sortie) ; les cadres
> sont des objets image ordinaires (pas de ligne de temps) ; le Ctrl+Z du
> document ne rend pas les pixels (dit : journal serveur, D1).

**Goal :** retoucher les calques image au pixel (pinceau, gomme, seau,
sélections rectangle / lasso / baguette / par couleur, croissance et
contraction, masque de calque, niveaux, courbes, HSL, noir & blanc, seuil,
clonage, flou, sélection → vecteur), et fabriquer délibérément des tuiles
pixel-art (unités de tuile, zoom au plus proche voisin, grille pixel,
crayon / ligne / rectangle pixel-parfaits, seau contigu ou global, symétrie,
palette indexée, pixelisation d'un vecteur, aperçu de raccord 3×3, feuille
de tuiles + JSON, cadres d'animation avec pelure d'oignon et bande,
« Envoyer vers Tilelab / Spritelab »), sous un persona Pixel à côté de
Vecteur et Export.

**Architecture :** deux modules FEUILLES purs sur des tampons
`{w, h, data: Uint8ClampedArray}` (le format d'ImageData, sans DOM) :
`mod-pixel.js` (outils raster, sélections en masque `Uint8Array`,
ajustements par LUT, flou, clonage, masque de calque) et `mod-pixelart.js`
(Bresenham, rectangle pixel, symétrie, palette indexée par median cut,
quantification, pixelisation, score de raccord 3×3, feuille de tuiles +
index, bande, pelure d'oignon). Le backend gagne `remplacer_image` (journal
`.pix<n>.png` ×10) et `annuler_image` + deux routes. `mod-doc.js` gagne
`pixelart` (unités de tuile, palette, symétrie) et `op_image_rev` (le
résolveur d'href ajoute `?v=rev` : les pixels changent, le JSON reste
léger). L'UI `mod-persona.js` pose les trois onglets (D8) ; `mod-pixelui.js`
porte les outils et panneaux du persona Pixel ; chaque geste raster =
lecture du PNG en ImageData → opération pure → PUT du PNG → `op_image_rev`.

**Décisions (dites au relevé) :** l'historique raster (Ctrl+Z du document)
ne rend pas les pixels : le bouton « Annuler pixels » (journal par fichier)
le fait — D1 ; les sélections vivent dans la session (masque en px natifs) ;
les cadres d'animation sont les objets `image` d'un calque nommé
« cadres », dans l'ordre de peinture ; « Envoyer vers Tilelab / Spritelab »
dépose le PNG dans la Bibliothèque (source `vectorlab`) et ouvre la surface
dans un nouvel onglet (écart : pas le bus d'événements du bundle) ; le
persona Export réunit les exports existants (SVG, PNG, Bible, Impression 3D)
sans format nouveau (lot G).

## Tasks

1. **`mod-pixel.js`** (banc `pixel.test.mjs`) — `tampon(w,h)`, `pinceau(img, points, {rayon, couleur, durete, masque})`,
   `gomme(img, points, {rayon, masque})`, `seau(img, x, y, couleur, {tolerance, global, masque})`,
   `sel_rect(w,h,r)`, `sel_lasso(w,h,poly)`, `sel_baguette(img,x,y,tol)`, `sel_couleur(img,couleur,tol)`,
   `sel_croitre(m,w,h,n)`, `sel_contracter(m,w,h,n)`, `sel_inverser(m)`, `sel_bbox(m,w,h)`,
   `masque_calque(img, m)` (alpha ← min(alpha, masque)), `niveaux(img,{noir,blanc,gamma},m)`,
   `courbes(img, points, m)`, `hsl(img,{h,s,l},m)`, `noir_blanc(img,m)`, `seuil(img,v,m)`,
   `flou(img, rayon, m)`, `cloner(img, sx, sy, dx, dy, rayon)`, `extraire(img, m)` (sous-image de la bbox, alpha masqué).
2. **`mod-pixelart.js`** (banc `pixelart.test.mjs`) — `ligne_pixel`, `rect_pixel`, `symetrie(points,w,h,{h,v})`,
   `palette_extraire(img,n)`, `quantifier(img,palette)`, `pixeliser(img, cible_w)`, `raccord_3x3(img)`,
   `feuille_tuiles(imgs, colonnes)` → `{img, index:[{nom,x,y,w,h}]}`, `bande(imgs)`, `pelure(img, prec, alpha)`.
3. **Backend** (pytest `test_vector_docs.py`) — `remplacer_image(did, nom, octets)` (journal `.pix<n>.png` ×10),
   `annuler_image(did, nom)` ; `PUT /vector/docs/{id}/images/{name}`, `POST /vector/docs/{id}/images/{name}/annuler`.
4. **Modèle** (`pixel_doc.test.mjs`) — `doc.pixelart {tuile, palette, symetrie}` validé, `op_pixelart`, `op_image_rev`,
   résolveur `?v=rev`.
5. **UI** — `mod-persona.js` (onglets Vecteur / Pixel / Export, classe `persona-*` sur body), `mod-pixelui.js`
   (outils et panneaux Pixel, pipeline PNG → ImageData → op → PUT → rev ; pixel-art : grille, `image-rendering:
   pixelated`, palette, symétrie, pixeliser, raccord, feuille, cadres, pelure, bande, envoyer vers).
6. Miroirs pytest, preuve en réel, déploiement (Python touché → relance), relevé.
