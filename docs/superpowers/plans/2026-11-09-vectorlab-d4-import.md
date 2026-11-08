# Vectorlab — lot D4 « Interop » : importer du SVG et du PDF (plan, 09/11/2026)

> **Spec** : `docs/superpowers/specs/2026-11-08-illustrator-vectorlab-inventaire.md`, décision D4 (« Import SVG d'abord,
> puis import PDF (première page, vectoriel). Sans cet import, aucune ressource vectorielle externe n'entre dans le
> Vectorlab ; AI/EPS restent exclus »). Enchaîné après D3 à la demande de l'utilisateur.
> **Branche** : `claude/vectorlab-d4-import`, tirée d'origin/main 2c4cba2e. **Suivi** : t469-t474.
>
> **But** : faire entrer dans un document du Vectorlab un fichier SVG ou la première page d'un PDF, en **objets
> vectoriels éditables** (chemins, rectangles, ellipses, textes, groupes), pas en image.

## Relevé (code d'origin/main)

- Aucun import vectoriel. Les seules entrées de fichiers sont :
  - les images (`mod-image.js`, `imageFichier`, avec `<input type=file>`) ;
  - le GPX (`mod-carte.js`) ;
  - le scan de schéma (`mod-schema.js`).
- `mod-pdf.js` ÉCRIT un PDF vectoriel depuis le modèle. Il fournit les matrices et les nombres, mais pas de lecture.
- Ce que le modèle sait porter :
  - les objets `rect`, `ellipse`, `path` (d absolu M L C Q Z), `texte`, `groupe`, `image` ;
  - une chaîne SVG `transform` (lue par les booléens depuis D2) ;
  - les styles `fond`, `contour`, `epaisseur`, `opacite`, `pointilles`.
- Les bancs tournent sous node, sans DOMParser : l'analyse doit être **pure** (lecteur XML maison, minimal).

## Tâches

### T1 (t469) — Lire un SVG

`mod-importsvg.js` (neuf, pur) : `svg_vers_objets(texte) → { objets, taille, stats }`.

- **Lecteur XML minimal** : éléments, attributs, texte, entités de base ; commentaires, CDATA et DOCTYPE ignorés.
- **Éléments**
  - `svg` : `viewBox`, `width` et `height` ; l'échelle du viewBox va dans un groupe.
  - `g`, avec son `transform`.
  - `rect` : un rectangle à coins arrondis devient un chemin.
  - `circle`, `ellipse`.
  - `line`, `polyline`, `polygon` : deviennent des chemins.
  - `path`, normalisé en absolu M L C Q Z :
    - les commandes relatives sont converties ;
    - H et V deviennent L ;
    - S et T deviennent C et Q ;
    - A (les arcs) devient des cubiques.
  - `text` et `tspan` : deviennent des `texte` (position, contenu, corps, police, couleur).
  - `use` : la référence `#id` est développée, avec son x et son y.
  - `image` : seule une `data:` est gardée ; sinon elle est ignorée et comptée.
  - `defs`, `symbol`, `clipPath`, `mask`, `filter`, `style` : ne sont pas dessinés.
- **Styles**
  - Ils sont lus depuis les attributs, `style="…"` et les règles simples `.classe { … }` et `élément { … }` d'une
    balise `<style>`.
  - Ils sont hérités du groupe.
  - Propriétés reconnues : `fill`, `stroke`, `stroke-width`, `opacity` (+ `fill-opacity` / `stroke-opacity` sur
    l'opacité), `stroke-dasharray`, `display:none` / `visibility:hidden` (l'objet est ignoré).
  - Couleurs : `#rgb`, `#rrggbb`, `rgb()`, les noms courants, `none`, `currentColor`.
  - Un `url(#dégradé)` donne la couleur du premier arrêt. C'est un écart dit : pas d'import de dégradé.
- `stats` compte ce qui est importé et ce qui est ignoré, par raison. L'UI le dit en une ligne.
- Banc `qa/importsvg.test.mjs`, écrit rouge d'abord :
  - chaque élément ;
  - l'héritage ;
  - les classes ;
  - les transforms ;
  - le viewBox ;
  - les arcs (point d'arrivée exact, aire d'un cercle en `A` ± 1 %) ;
  - les commandes relatives ;
  - `use` ;
  - un SVG malformé → refus traduit.

### T2 (t470) — Importer un SVG dans le document

- `op_importer_svg(doc, analyse, { calque, x, y })` :
  - tout entre dans UN groupe (ids `o<n>` neufs, sans collision) ;
  - il est posé au point voulu, par défaut le centre de la page ;
  - son nom est celui du fichier.
- **Interface**
  - Menu Fichier › **Importer (SVG, PDF)…**, avec un sélecteur de fichier `.svg,.pdf`.
  - Un **SVG collé** (texte du presse-papiers commençant par `<svg`, comme une copie d'Illustrator ou de Figma) entre
    pareil.
  - Un **SVG déposé** sur la toile entre pareil.
  - Toast : « N objets importés ; M ignorés (raisons) ».
- Banc et preuve : un SVG réel, comme le logo de l'application et un pictogramme d'icône ; export SVG → réimport,
  qui donne la même géométrie (aller-retour).

### T3 (t471) — Lire un PDF (première page, vectoriel)

`mod-importpdf.js` (neuf, pur sauf la décompression) : `pdf_vers_objets(octets) → Promise<{ objets, taille, stats }>`.

- **Structure** : la table `xref` classique et les **flux xref**, les **flux d'objets** (ObjStm), `FlateDecode` par
  `DecompressionStream("deflate")` (navigateur et node ≥ 18). Il faut ensuite trouver la première page (Pages › Kids)
  et lire son ou ses `Contents`, sa `MediaBox` et ses `Resources`.
- **Opérateurs** :
  - état graphique : `q Q cm` ;
  - tracés : `m l c v y h re` ;
  - peinture : `f F f* S s B B* b b* n` ;
  - découpe : `W W*` (ignorée, et comptée) ;
  - couleurs : `g G rg RG k K` (CMJN converti en RVB), `cs CS sc scn SC SCN` (DeviceRGB, DeviceGray, DeviceCMYK) ;
  - trait : `w`, `d` ;
  - transparence : `gs` (`ca` et `CA` de l'ExtGState) ;
  - `Do` : les Form XObjects sont parcourus, les images sont comptées et ignorées ;
  - texte : `BT … ET` compté et ignoré. C'est l'écart principal, dit dans l'interface : les textes d'un PDF sont
    souvent en polices incorporées.
- **Repère** : le y du PDF monte. La MediaBox est retournée vers le repère du document, et 1 pt = 1 px × 96 / 72.
- Banc `qa/importpdf.test.mjs` :
  - un PDF produit par `mod-pdf.js` lui-même, réimporté (aller-retour : mêmes rectangles et couleurs) ;
  - un PDF écrit à la main, avec un flux compressé et un flux d'objets ;
  - un PDF chiffré ou illisible → refus traduit.

### T4 (t472) — Importer un PDF dans le document

- Même entrée « Importer (SVG, PDF)… » et même dépôt sur la toile. L'import est asynchrone, avec un toast « Lecture
  du PDF… », puis le bilan, par exemple : « 128 objets importés ; textes (12) et images (2) ignorés ».
- Banc d'interface (VL factice) et preuve 8799 avec un vrai PDF vectoriel.

### T5 (t473) — Connaissance et guide

- Fiche catalogue de l'entrée neuve (skill `connaissance-agent`).
- Carte « Importer » au chapitre Vectorlab du guide, qui dit ce qui est ignoré (skill `guide-deepotus`).

### T6 (t474) — Preuve et livraison

- QA complète et bancs Python ; preuve 8799 en FR et en EN (SVG par fichier, par collage et par dépôt ; PDF ;
  aller-retours).
- PR unique. Installation seulement sur accord.

## Hors lot

- Les dégradés et motifs SVG ou PDF, les masques et les filtres.
- Les textes d'un PDF (polices incorporées).
- Les pages suivantes d'un PDF.
- AI et EPS (exclus le 17/09).
