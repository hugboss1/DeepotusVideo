# Vectorlab classe Affinity — LOT H : cartes réelles (GPX, relief, plateau imprimable) — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module
> pur). Steps use checkbox (`- [ ]`) syntax for tracking.

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot H — cinq pas réversibles : importer, habiller, découper,
> prévisualiser, imprimer ; sources Terrarium AWS et OSM sans clé ; D7 zéro
> dépendance payante ; D9 modules purs). Dépend de A (image), C (tuiles),
> D (extrusion) — tous livrés. Branche `chantier/vectorlab-affinity`, après
> le lot D (`f227982`). Ce plan est COMMIS avant le code.

> **RELEVÉ DE LIVRAISON (17/09/2026) : LOT H LIVRÉ, PROUVÉ SUR DONNÉES RÉELLES, DÉPLOYÉ — relance du backend à faire.**
>
> **Livré** (8 commits `2548fd8`→`abb2de8`, poussés) : `mod-geo.js` feuille
> (GPX par expressions régulières, Mercator local à l'échelle vraie au
> centre, cadrage à la page + « 1 : N », tuiles XYZ, marching squares
> chaînés, échantillon, paliers, ombrage Horn) ; `mod-relief.js` feuille
> (plaque fermée étanche avec socle et murs, gravure du tracé, dalles
> numérotées à bord partagé, sous-grille) ; modèle : `doc.geo` validé,
> `op_geo_importer` (calques emprise 🔒, trace, points), `op_geo_relief`,
> `op_geo_courbes`, `op_geo_tuiles` (plateau hex sur l'emprise, terrain par
> palier, `hauteur_mm` proportionnelle) ; backend `geo_service.py` (Terrarium
> + OSM par hook réseau, cache disque `cache/geo`, décodage Pillow sans
> numpy, mosaïque rognée, rééchantillonnée ≤ 160, « sans donnée » −32768 →
> plancher valide et compté) + routes `/geo/relief`, `/geo/fond`,
> `/geo/attribution` (400 / 502 parlants) ; UI `mod-carte.js` (panneau Carte
> réelle : Importer GPX, Fond OSM avec attribution écrite au document,
> Relief ombré en calque à 0,7, Courbes, Découper, Imprimer) ; mode
> `relief` du dialogue Impression 3D (largeur, exagération, socle, gravure
> du tracé, dalles si > 256 mm, lot par dalle).
>
> **TDD tenu** : RED ×5 (modules, exports, `geo_service`, route 405,
> miroir). Bancs : node **628 contrôles** (+70 : geo 28, relief 17, geo_doc
> 16, carte_ui 9), pytest `test_geo` **6 passed** (synthétiques Terrarium
> avec carré haut ET carré « sans donnée », cache = zéro requête au second
> appel, > 16 tuiles refusé AVANT toute requête, réseau muet → 502).
>
> **Prouvé sur données RÉELLES** (backend du worktree 8799, données isolées,
> viewport 1400×900) autour de 45,0° N / 6,0° E (Alpes) : GPX synthétique de
> 13 points + 1 waypoint → calques `emprise 🔒`, `trace`, `points`,
> emprise_px 816 × 820, **« 1 : 13 900 · 3,0 km de large · 216 mm
> imprimés »**, zoom 14 ; **Relief Terrarium réel** : 148 × 148 en 6,8 s la
> première fois (1,3 s ensuite : cache), **1 445 → 2 850 m**, 20,27 m par
> cellule, image ombrée posée en calque « relief (ombrage) » à 0,7 (le
> premier appel avait rendu min −32768 : le « sans donnée » a été attrapé
> ICI et corrigé) ; Courbes à 100 m → **25 chemins** au DOM ; Découper (hex
> 40, relief 10 mm) → **195 tuiles**, cinq terrains (mer 109, plaine 14,
> forêt 24, colline 36, montagne 12), hauteurs 0 → 9,1 mm, pinceau actif ;
> **Fond OSM réel** posé en calque du bas (2,9 s), attribution © OpenStreetMap
> contributors écrite dans `doc.geo` et affichée ; Impression 3D mode relief
> proposé (4 champs) : plaque 216 mm, exagération 1,5, gravure 0,6 → **1
> pièce, 87 612 triangles, 216 × 216 × 155 mm**, `model-viewer.loaded` et
> `getDimensions()` = bbox ; la gravure ôte du volume (2 331 664 →
> 2 331 321 mm³) ; largeur 400 → **4 dalles** `dalle_1_1…2_2`, garde « 400 mm
> dépasse le plateau », lot actif ; « Un STL » → `preuve-lot-h-20260917` ;
> Sauver → relu : `geo` + relief 21 904 hauteurs, 8 calques, 224 Ko de
> JSON (les hauteurs sont des données, dit).
>
> **Déployé** : 6 fichiers = base lot D (`00a46cc`) → sauvegarde
> `_backup_predeploy_2026-09-17d-vectorlab-lotH` → copie depuis `git archive
> abb2de8` → **79 fichiers = cible**, pré-vol du python embarqué OK. **Python
> touché (`geo_service.py`, `routes.py`) : les routes `/geo` n'existent
> qu'après relance — c'est l'utilisateur qui relance.**
>
> **Reste** : dalles juxtaposées numérotées, sans tenons (le spec disait
> « emboîtables ») ; le relief à l'échelle vraie × 1,5 fait 155 mm de haut
> sur les Alpes — l'exagération se règle à la main ; les hauteurs vivent
> dans le JSON du document (≤ 160 × 160) ; la trace GPX ne porte pas encore
> ses altitudes en 3D (la gravure suit le tracé, pas le profil).

**Goal :** importer un `.gpx`, le poser à l'échelle sur la page (trace,
points, emprise), l'habiller d'un fond OSM et d'un relief Terrarium (ombré,
courbes de niveau vectorielles), le découper en tuiles hexagonales dont la
hauteur vient du relief, le prévisualiser en 3D (plaque continue ou tuiles,
exagération verticale) et l'imprimer (plaque, dalles ≤ 256 mm, ou lot de
tuiles).

**Architecture :** `mod-geo.js` FEUILLE (parse GPX par expressions
régulières — node n'a pas de DOMParser —, Mercator local en mètres,
cadrage à la page et échelle « 1 : N », mathématiques des tuiles XYZ,
marching squares pour les courbes de niveau, échantillonnage, paliers,
ombrage) ; `mod-relief.js` FEUILLE (grille de hauteurs → plaque fermée
avec socle et murs, gravure du tracé, découpe en dalles) ; `geo_service.py`
backend (tuiles Terrarium et OSM par hooks réseau monkeypatchables, cache
disque `DeepotusVideoGenData/cache/geo`, décodage des hauteurs par Pillow —
sans numpy —, assemblage et rééchantillonnage) + trois routes ;
`mod-doc.js` gagne le champ optionnel `geo` (centre, m_par_px, zoom,
emprise, relief) et `op_geo_importer` ; `mod-carte.js` UI (panneau « Carte
réelle ») et un mode `relief` dans le dialogue Impression 3D du lot D.

**Décisions d'implémentation (dites au relevé) :**
- Les hauteurs vivent dans `doc.geo.relief.hauteurs` (grille ≤ 160×160 de
  nombres arrondis au décimètre) : ce sont des DONNÉES, pas des pixels — D1
  ne s'y oppose pas ; l'image ombrée, elle, va au magasin d'images.
- Découpe en dalles : juxtaposition NUMÉROTÉE avec un rang de cellules
  partagé (bords coïncidents) — pas de tenons ; écart déclaré (le spec dit
  « emboîtables »).
- OSM : `User-Agent` explicite, attribution © OpenStreetMap contributors
  affichée dans le panneau et écrite dans le document (`geo.attribution`),
  au plus 16 tuiles par appel ; Terrarium : idem, décodage
  `(R·256 + G + B/256) − 32768`.
- Sans réseau : l'import GPX seul fonctionne ; fond et relief rendent une
  erreur parlante (502).

---

## Task 1 : `mod-geo.js` — GPX, projection, cadrage, tuiles, courbes, paliers, ombrage

**Test `qa/geo.test.mjs`** (RED d'abord) — contrôles : parse d'un GPX
synthétique (2 trkpt avec ele, 1 rtept, 1 wpt nommé, refus sans point,
refus XML sans lat) ; Mercator local (centre → [0,0], +0,01° de lon à
lat 45 ≈ 786 m, +0,01° de lat ≈ 1112 m, y vers le NORD) ; cadrage
(emprise 2×1 km sur page 1000×600 marge 50 → m_par_px = 2000/900 ≈ 2,22 ;
`vers_px(centre)` = [500, 300] ; libellé « 1 : 8 400 » à 96 dpi arrondi au
centième supérieur) ; tuiles XYZ (lat 0 lon 0 z 1 → x 1 y 1 ; couverture
d'une emprise ; `zoom_pour` borne les tuiles à 16) ; marching squares
(grille 3×3 avec un pic central au niveau 5 → une boucle fermée de 8
sommets ; état vide : niveau hors bornes → []) ; échantillon moyen ;
paliers (bornes égales, index) ; ombrage (plan → 0,5 ± ; pente face au
nord-ouest plus claire).

**Signatures** (module sans import) :
```js
export const R_TERRE = 6378137;
export function gpx_parser(xml) → { traces: [[{lat, lon, ele}]], points: [{lat, lon, nom}], emprise: {minLat, maxLat, minLon, maxLon}, n }
export function mercator_m(lat, lon, lat0, lon0) → [x_m, y_m]      // y vers le nord
export function cadrage(emprise, taille, marge = 40) → { centre: [lat0, lon0], m_par_px, largeur_m, hauteur_m, vers_px(lat, lon) → [x, y] }
export function echelle_libelle(m_par_px, dpi) → "1 : 8 400"
export function tuile_xyz(lat, lon, z) → { x, y }
export function tuiles_couvrant(emprise, z) → { xmin, xmax, ymin, ymax, n }
export function zoom_pour(emprise, maxTuiles = 16) → z (le plus fin tel que n ≤ maxTuiles, 1..15)
export function latlon_de_tuile(z, x, y) → { lat, lon }                // coin NO
export function courbes_niveau(grid, w, h, niveau) → [[[x, y], …], …]  // coords grille
export function echantillon_moyen(grid, w, h, cx, cy, rayon) → nombre | null
export function paliers_bornes(min, max, n) → [b1, …, b(n-1)]
export function palier(v, bornes) → index 0..n-1
export function ombrage(grid, w, h, pasM, exag = 1) → Uint8ClampedArray (w·h, 0..255)
```

Commit : `vectorlab : mod-geo — GPX, Mercator local, cadrage et echelle, tuiles XYZ, courbes de niveau, paliers, ombrage (lot H, T1)`.

## Task 2 : `mod-relief.js` — plaque, gravure, dalles

**Test `qa/relief.test.mjs`** : plaque 3×3 plate (h=10 m) largeur 30 mm,
socle 2, exagération 1, mm_par_m 0,1 → volume = 30×30×(2+1) ; z max = 3 ;
étanche (chaque arête partagée deux fois : compter les arêtes orientées) ;
gravure d'un tracé abaisse les cellules dans le rayon ; dalles : grille
9×5 max 4 → 3×2 dalles avec bord partagé, numérotées ; état vide : grille
2×1 refusée.

```js
export function plaque(grid, w, h, { largeur_mm, socle_mm, mm_par_m, exageration = 1, z_min }) → tris
export function graver(grid, w, h, polylignes, profondeur, rayon) → grid (copie)
export function dalles(w, h, maxCellules) → [{ nom, x0, y0, w, h }]
export function sous_grille(grid, w, h, d) → { grid, w, h }
```

Commit : `vectorlab : mod-relief — plaque fermee (socle, murs), gravure du trace, decoupe en dalles numerotees (lot H, T2)`.

## Task 3 : modèle — `doc.geo`, `op_geo_importer`, `op_geo_relief`, terrain par relief

`parserDoc` : `geo` optionnel `{centre:[lat,lon], m_par_px>0, zoom:int, emprise:{…}, attribution?, relief?:{w,h,min,max,pasM,hauteurs:[w·h]}}`.
`op_geo_importer(doc, cadre, gpx)` : pose `doc.geo`, trois calques `trace`
(paths contour `#d0553a` 3), `points` (ellipse r 5 + texte nom), `emprise`
(rect verrouillé, calque verrouillé) ; `op_geo_relief(doc, relief)` ;
`op_geo_courbes(doc, polylignes_px, pas)` ; `op_geo_tuiles(doc, spec)` :
génère le plateau (lot C) puis affecte terrain + `hauteur_mm` par palier
depuis le relief. Test `qa/geo_doc.test.mjs`.

## Task 4 : backend `geo_service.py` + routes

Tests `backend/tests/test_geo.py` : tuile Terrarium synthétique (Pillow,
hauteur 100 m partout sauf un carré à 300 m) ; décodage exact ;
`hauteurs()` assemble 4 tuiles, rogne à l'emprise, rééchantillonne ≤ 160,
min/max justes ; cache : second appel → 0 requête (compteur du hook) ;
refus zoom trop fin (> 16 tuiles) ; `fond()` rend un PNG de la bonne
taille ; routes `POST /geo/relief`, `POST /geo/fond`, `GET /geo/attribution`
(400 emprise invalide, 502 réseau muet).

Commit : `geo : tuiles Terrarium et OSM en cache, hauteurs decodees par Pillow, fond assemble, routes /geo (lot H, T4)`.

## Task 5 : UI `mod-carte.js` + mode `relief` du dialogue Impression 3D

Panneau « Carte réelle » (details) : Importer GPX (file input → `gpx_parser`
→ `cadrage` → `op_geo_importer`), échelle affichée « 1 : N · L km · l mm »,
« Fond de carte OSM » (POST /geo/fond → blob → pose dans un calque `fond`
en bas, cadré sur l'emprise, attribution), « Relief » (POST /geo/relief →
`op_geo_relief` + image ombrée posée dans un calque `relief` opacité 0,7),
« Courbes de niveau » (pas m → `courbes_niveau` par niveau → px →
`op_geo_courbes`), « Découper en tuiles » (rayon px de l'hexagone →
`op_geo_tuiles`), « Aperçu 3D / Imprimer » (`VL.impression("relief")`).
Mode `relief` de `mod-impression.js` : exagération, socle, gravure du
tracé (profondeur mm), plaque via `mod-relief` ; si la plaque > 256 mm →
« Lot par dalles » (`/print3d/lot`, un STL par dalle + nomenclature).
Tests purs `qa/carte_ui.test.mjs` (libellés, conversion grille → px).

## Task 6 : miroirs pytest, preuve en réel, déploiement, relevé

Preuve : GPX synthétique (une boucle de 12 points autour de 45,0 / 6,0 avec
ele) importé → 3 calques, échelle lue ; relief RÉEL Terrarium (zoom choisi,
grille ≤ 160, min < max) ; ombrage posé ; courbes à 50 m → N chemins ;
tuiles rayon 3 → terrains par palier, `hauteur_mm` variées ; Impression 3D
mode relief → aperçu chargé (dimensions), « Un STL » ; fond OSM posé
(attribution visible). Déploiement : vectorlab + `geo_service.py` +
`routes.py` → **relance à faire**.
