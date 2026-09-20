# Vectorlab classe Affinity — LOT G : persona Export — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module pur).

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot G ; §2.11 export ; D7 zéro dépendance : le PDF s'écrit côté
> backend avec la stdlib, patron `print3d.py` ; D8 le persona Export ; D9
> modules purs). Branche `chantier/vectorlab-affinity`, après le lot F
> (`f4c721e`). Ce plan est COMMIS avant le code.

> **RELEVÉ DE LIVRAISON (17/09/2026) : LOT G LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ — Python touché : RELANCE du backend installé (8765) par l'utilisateur.**
>
> **Livré** (7 commits `4dc4964`→`8cfece4`, poussés) : `mod-tranches.js`
> feuille (cinq modes de tranche avec bbox injectée, résolutions bornées,
> nommage `vector_<doc>_<tranche>@<k>x[_t].<ext>`, plan tranches ×
> résolutions × formats — le PDF en une entrée —, saignée, marques de
> coupe et de repérage en SVG) ; `mod-dxf.js` feuille (px → mm au dpi du
> document, Y vers le haut, DXF R12 en `LWPOLYLINE` fermées) ; backend
> `pdf_service.creer_pdf` (stdlib : pages en points depuis les mm, une
> image JPEG `DCTDecode` par page, xref valide) et `POST
> /vector/docs/{id}/pdf` multipart en téléchargement ; UI
> `mod-exportplus.js` (panneau « Export + » : mode de tranche, résolutions,
> six formats, preset d'impression — saignée mm, traits de coupe, repérage,
> dpi, qualité —, plan de nommage visible, « Exporter le lot ») + outil
> « tranche » dessinée (overlay, Échap), rendu canvas PNG / JPEG / WebP
> avec marques, SVG par tranche, PDF par la route, DXF par `aplatir_objet`
> ; `svgCourant` compile un document isolé (calque ou objet).
>
> **TDD tenu** : RED ×5 (tranches, dxf, pytest PDF + route, exportplus_ui).
> Bancs : node **984 contrôles** (+36 : tranches 21, dxf 7, exportplus_ui
> 8), pytest `test_vector_docs` **37 passed** (+3). Le banc a redressé deux
> regex (les entiers DXF sont justifiés sur 6 colonnes ; le drapeau 70 de
> la table des calques se comptait avec ceux des polylignes) et un lecteur
> de réglages qui prenait une valeur absente pour 0.
>
> **Prouvé en réel** (8799, données isolées, viewport 1400×900, gestes
> pointeur synthétiques, lecture DOM, ancres de téléchargement stubées et
> relues) : onglet Export → panneau **294 px**, outils select + tranche
> seuls ; plan par mode : document `_doc.png`, planches `_Recto` /
> `_Verso`, calques `_fond` / `_detail`, objets `_r1` ; résolutions « 1, 2 »
> et six formats → **9 entrées** nommées (`@2x`, `.jpg`, `.webp`, `.svg`,
> `_lot.pdf`, `.dxf`) ; tranche dessinée au pointeur → `t1` (aimantée à la
> grille), overlay 1, mode « dessinées » ; preset saignée 3 mm + coupe +
> repérage + 150 dpi ; **export lot : 9 fichiers** — PNG 220×220, WebP
> 220×220 (`image/webp`), JPEG @2x **440×440** servis par la Bibliothèque ;
> SVG relu avec `data-marques`, **16 traits + 4 cercles**, viewBox élargi
> −30 −30 220 220 ; PDF relu : `%PDF-1.4`, 1 page, `MediaBox 62.36 pt`
> (= 22 mm : 9,6 mm + 2 × 3 mm de saignée + marques), `DCTDecode`, largeur
> 130 px au dpi 150 ; DXF relu : 1 `LWPOLYLINE` sur le calque `t1`,
> `$INSUNITS`, premier point (−1,2 ; 10,8) mm ; Échap → 0 tranche.
>
> **Un défaut attrapé par la preuve** : le DXF ne gardait que les anneaux
> ayant un SOMMET dans la tranche — un rectangle qui l'englobe n'en a
> aucun et faisait échouer tout le lot ; chevauchement de bbox, et une
> tranche sans découpe est sautée en le disant.
>
> **Déployé** : 12 fichiers (= base lot F `30ab83c` vérifiés par
> hash-object, 7 absents) → sauvegarde
> `_backup_predeploy_2026-09-17h-vectorlab-lotG` (5 fichiers) → copie
> depuis `git archive 8cfece4` → **12 = cible, 111/111 du Vectorlab =
> cible**, pré-vol `import app.main` + `pdf_service` OK. **`routes.py` et
> `pdf_service.py` touchés : l'utilisateur relance le backend installé.**
>
> **Reste** : le PDF est raster (JPEG au dpi choisi), pas vectoriel ; le
> DXF ignore texte, images et instances (dit dans le panneau) ; le SVG par
> tranche se télécharge (le SVG serveur du document reste celui du menu) ;
> les tranches dessinées vivent dans la session ; la saignée montre les
> objets qui débordent de la page mais n'étire pas le fond.
>
> **Le chantier « Vectorlab classe Affinity » est COMPLET : lots A, C, D,
> H, B, E, F, G livrés dans l'ordre de la conception.**

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
