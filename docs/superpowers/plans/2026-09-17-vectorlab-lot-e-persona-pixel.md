# Vectorlab classe Affinity — LOT E : persona Pixel et mode pixel-art — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module pur).

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot E + « Complément au lot E — mode pixel-art type Aseprite vers le
> Tilelab » ; D1 raster en PNG à côté du JSON avec journal d'annulation par
> fichier `.pix<n>.png` ×10 ; D8 une surface, des personas Vecteur / Pixel /
> Export ; D9 modules purs). Branche `chantier/vectorlab-affinity`, après le
> lot B (`6a09007`). Ce plan est COMMIS avant le code.

> **RELEVÉ DE LIVRAISON** : à écrire ici en fin de lot.

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
