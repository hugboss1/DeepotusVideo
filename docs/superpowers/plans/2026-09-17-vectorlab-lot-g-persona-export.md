# Vectorlab classe Affinity — LOT G : persona Export — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module pur).

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot G ; §2.11 export ; D7 zéro dépendance : le PDF s'écrit côté
> backend avec la stdlib, patron `print3d.py` ; D8 le persona Export ; D9
> modules purs). Branche `chantier/vectorlab-affinity`, après le lot F
> (`f4c721e`). Ce plan est COMMIS avant le code.

> **RELEVÉ DE LIVRAISON** : à écrire ici en fin de lot.

**Goal :** donner au persona Export les tranches (document, planches,
calques, objets sélectionnés, tranches dessinées), les formats JPEG / WebP
/ PDF / DXF à côté de SVG / PNG, la multi-résolution en un tir (1×, 2×, 4×
avec suffixe `@2x`), les presets d'impression (fond perdu / saignée, traits
de coupe, marques de repérage), le nommage automatique et l'export lot.

**Architecture :** deux modules FEUILLES purs — `mod-tranches.js` (tranches
par mode avec `bboxDe` injectée, résolutions lues et bornées, nommage
`vector_<doc>_<tranche>@<k>x.<ext>`, plan d'export = tranches × résolutions
× formats, saignée et marques de coupe / repérage en SVG) et `mod-dxf.js`
(polylignes → DXF R12 en mm, texte pur) ; le backend gagne
`pdf_service.py` (stdlib : pages en points, une image JPEG `DCTDecode` par
page) et la route multipart `POST /vector/docs/{id}/pdf` ; l'UI
`mod-exportplus.js` (panneau « Export + » du persona Export, outil
« tranche » qui se dessine sur la scène, rastérisation JPEG / WebP par
canvas, DXF par `aplatir_objet` de mod-bool, lot déposé dans la
Bibliothèque par la route d'import existante, PDF et DXF téléchargés).

**Décisions d'implémentation (dites au relevé) :**
- Le PDF est RASTER : une page par tranche, l'image JPEG (qualité 0,92) au
  dpi choisi, page en points depuis les mm (dpi du document). Un PDF
  vectoriel demanderait un interpréteur SVG côté serveur (hors D7).
- JPEG n'a pas d'alpha : le fond du document (ou blanc) est peint d'abord ;
  WebP garde l'alpha.
- Le DXF est en mm (dpi du document), Y vers le haut (origine en bas à
  gauche de la tranche), `LWPOLYLINE` fermées par anneau ; les objets
  passent par `aplatir_objet` (tolérance 0,25 px) — texte et images sont
  ignorés (dit dans le panneau).
- Le preset d'impression ÉLARGIT le cadre de la saignée (mm) : le fond du
  document ne couvre que la page, les objets qui débordent apparaissent
  dans la saignée ; traits de coupe aux quatre coins (hors saignée),
  marques de repérage (cercle + croix) au milieu des quatre côtés.
- Une tranche dessinée vit dans la session (`etat.tranches`), nommée
  `t1, t2…` ; elle s'efface par Échap dans l'outil ou par le panneau.
- Le nommage : `vector_<docId>_<tranche>` + `@2x` (k ≠ 1) + `_t`
  (transparent) + `.ext` ; le document entier a la tranche `doc`.

## Tasks

1. **`mod-tranches.js`** (banc `tranches.test.mjs`) — `MODES` (document, planches, calques, objets, dessinees),
   `tranches_de(doc, mode, {ids, bboxDe, dessinees})` → `[{nom, cadre, calqueId?}]`, `resolutions_lire(texte)` (1..8, uniques, ≤ 4 valeurs),
   `FORMATS` (png, jpeg, webp, svg, pdf, dxf), `nom_export(docId, tranche, k, ext, transparent)`, `plan_export(docId, tranches, ks, formats, transparent)`,
   `mm_px(mm, dpi)`, `cadre_saignee(cadre, saigneePx)`, `marques_svg(cadre, saigneePx, {coupe, reperage}, longueur)`.
2. **`mod-dxf.js`** (banc `dxf.test.mjs`) — `dxf_de(polylignes, {calque})` (HEADER $INSUNITS 4 mm, TABLES, ENTITIES LWPOLYLINE fermées, EOF), vide refusé,
   `polylignes_mm(anneaux, cadre, dpi)` (px document → mm, Y retourné).
3. **Backend** (`test_vector_docs.py`) — `pdf_service.creer_pdf(pages)` (pages = [{w_mm, h_mm, jpeg}]) → bytes `%PDF-1.4` avec xref valide,
   `POST /vector/docs/{id}/pdf` multipart (`pages` JSON + fichiers `page<i>`) → `application/pdf` ; 400 sans page, 404 doc inconnu.
4. **UI** `mod-exportplus.js` (banc `exportplus_ui.test.mjs` : `reglages_lire`, `resume_plan`) — panneau « Export + » (mode de tranche, résolutions,
   formats, preset impression, aperçu du plan de nommage, « Exporter le lot »), outil `tranche` (glisser un rectangle, Échap efface), rastérisation
   `rasteriser(cadre, k, format, transparent, marques)`, DXF via `aplatir_objet`, PDF via la route, lot → Bibliothèque ; `mod-persona.js` héberge le panneau ;
   `core.js`, `index.html`, CSS ; miroir pytest.
5. Preuve en réel (8799), déploiement (Python touché → relance), relevé.
