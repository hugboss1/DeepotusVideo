# Vectorlab classe Affinity — LOT F : apparence avancée — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module pur).

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot F ; §2.6 couleur et remplissages, §2.7 calques et effets, §2.8
> texte, §2.10 symboles et styles ; D2 champs optionnels `symboles{}`,
> `styles{}`, `couleursGlobales{}`, objet `instance` ; D9 modules purs).
> Branche `chantier/vectorlab-affinity`, après le lot E (`8e2f8f0`). Ce
> plan est COMMIS avant le code.

> **RELEVÉ DE LIVRAISON** : à écrire ici en fin de lot.

**Goal :** donner au Vectorlab l'apparence de classe Affinity : effets de
calque par filtres SVG (ombre externe / interne, lueur, biseau, contour,
incrustation), modes de fusion, écrêtage vectoriel (« coller dans »),
motifs et hachures, dégradé conique et dégradé de transparence,
multi-contours, couleurs globales et palettes harmoniques, styles d'objet
réutilisables, symboles à instances synchronisées, cadre de texte
(paragraphes, alignement, justification) et texte sur chemin, pinceau
vectoriel à profil.

**Architecture :** trois modules FEUILLES purs — `mod-effets.js` (les
effets → `<filter>`, les 16 modes de fusion du SVG, les motifs →
`<pattern>`, le dégradé conique → `<pattern>` de secteurs interpolés),
`mod-texteplus.js` (mesure approximative injectable, coupe des lignes,
`<tspan>` alignés / justifiés, texte sur chemin) et `mod-pinceauvec.js`
(contour fermé d'un trait à profil plat / fuseau / calligraphie) ;
`mod-couleur.js` gagne `palette_harmonique` ; `mod-doc.js` gagne les
champs `style.effets / fusion / contours / masque`, `doc.motifs`,
`doc.couleursGlobales` (résolution `glob:<nom>` à la compilation),
`doc.styles`, `doc.symboles` + objet `instance` (`<use>`), `groupe.clip`
(écrêtage → `<clipPath>`), le dégradé `conique`, les objets `cadre` et
`textechemin`. L'UI `mod-apparence2.js` porte les panneaux (Effets, Fusion,
Contours, Motifs, Couleurs globales, Styles, Symboles, Texte +) et l'outil
pinceau vectoriel (J) ; `mod-style.js` gagne les boutons dégradé conique /
transparence et écrêtage.

**Décisions d'implémentation (dites au relevé) :**
- Les copies compilées d'un objet (multi-contours, géométrie d'écrêtage,
  corps des symboles) sont émises SANS `data-objet` (`ctx.sansId`) : un
  seul élément porte l'id — le hit-testing et la sélection restent ceux du
  cœur. Un objet à contours multiples ou à effet est enveloppé dans
  `<g data-objet>` (patron de l'objet `image`) ; sans apparence avancée la
  compilation est INCHANGÉE (les snapshots existants tiennent).
- Le dégradé conique n'existe pas en SVG : il se compile en `<pattern
  patternUnits="userSpaceOnUse">` de 72 secteurs aux couleurs interpolées
  (linéaire en RGB), couvrant le carré `[cx−r, cx+r]²`.
- Le dégradé de transparence est un MASQUE : `style.masque = "grad:<id>"`
  compile `<mask id="m_<id>"><rect fill="url(#<id>)"/></mask>` — les
  couleurs des stops valent luminance (blanc opaque, noir transparent).
- Les effets sont une LISTE ordonnée `style.effets` ; chaque objet à effets
  a son `<filter id="fx_<objet>">` (région ×1,5 pour les ombres).
- Le mode de fusion est `style.fusion` (16 valeurs SVG) → attribut
  `style="mix-blend-mode:…"`.
- Une couleur globale se référence par `"glob:<nom>"` dans `fond`,
  `contour`, les stops et les contours multiples ; supprimer une couleur
  globale RÉSOUT ses références en hex (jamais de référence pendante).
- Un style d'objet est une COPIE au moment de l'application (pas de lien
  vivant) ; un symbole, lui, est VIVANT : ses instances `<use>` suivent.
- Le symbole porte la géométrie de ses objets en coordonnées d'origine
  et sa `bbox` ; l'instance porte `x, y, sx, sy` (translation + échelle).
  « Détacher » copie les objets translatés dans le calque de l'instance.
- Le cadre de texte coupe ses lignes avec une mesure INJECTABLE
  (`opts.mesure(texte, style)`) : au banc, une approximation (0,55 × corps
  par caractère) ; au navigateur, `measureText` du canvas. Le texte sur
  chemin COPIE le `d` du chemin (pas de lien vivant : la conception ne
  promet pas de formes composées non destructives).
- Le pinceau vectoriel produit un CHEMIN FERMÉ rempli (pas un contour) :
  largeur × profil(t) le long du trait lissé (mod-crayon).

## Tasks

1. **`mod-effets.js`** (banc `effets.test.mjs`) — `EFFETS` (ombre, ombre_interne, lueur, biseau, contour, incrustation),
   `effet_defaut(type)`, `effets_valider(liste)`, `filtre_svg(id, effets)` (chaîne fe*, région −25 %…150 %),
   `MODES_FUSION` (16), `MOTIFS` (hachures, points, damier, grille), `motif_defaut(type)`, `motif_valider(m)`,
   `motif_svg(id, m)` (`<pattern patternUnits="userSpaceOnUse">`), `conique_secteurs(g, n)` → [{d, couleur}],
   `conique_svg(id, g)`, `couleur_interpoler(a, b, t)`.
2. **`mod-doc.js` apparence** (banc `apparence2.test.mjs`) — validation `style.effets/fusion/contours/masque`, compilation
   (filter, mix-blend-mode, copies de contour, mask), `doc.motifs` + `op_motif_creer/modifier/supprimer` + fond `motif:<id>`,
   dégradé `conique {cx, cy, r, angle}`, `op_degrade_transparence(doc, ids, bbox)`, `doc.couleursGlobales` +
   `op_couleur_globale_definir/supprimer`, résolution `glob:` (fond, contour, stops, contours), `groupe.clip` +
   `op_ecreter(doc, idConteneur, ids)` / `op_desecreter(doc, idGroupe)`.
3. **`mod-couleur.js`** (banc `harmonie.test.mjs`) — `palette_harmonique(hex, type)` : complementaire (2), analogue (3),
   triade (3), tetrade (4), monochrome (5) ; hex majuscules ; type inconnu refusé.
4. **Styles et symboles** (banc `symboles.test.mjs`) — `doc.styles` + `op_style_definir/appliquer/supprimer`,
   `doc.symboles` + objet `instance {symbole, x, y, sx, sy}` (compilé `<use href="#sym_<id>">`, defs `<g id="sym_<id>">`),
   `op_symbole_creer(doc, ids, bbox)`, `op_instance_poser(doc, calqueId, symId, x, y)`, `op_symbole_detacher(doc, id)`,
   `op_symbole_supprimer` (refus s'il reste des instances), déplacer / redimensionner une instance, bbox.
5. **`mod-texteplus.js`** (banc `texteplus.test.mjs`) — `mesure_approx(texte, style)`, `couper_lignes(contenu, largeur, style, mesure)`
   (mots, retours forcés, mot trop long coupé), `cadre_tspans(o, lignes, mesure)` (`<tspan x y textLength>` selon `aligner`),
   objets `cadre` et `textechemin` compilés dans mod-doc (`opts.mesure`), `op_texte_en_cadre`, `op_texte_sur_chemin`.
6. **`mod-pinceauvec.js`** (banc `pinceauvec.test.mjs`) — `PROFILS`, `profil(nom, t)`, `trait_profil(points, {largeur, profil, angle})` → `d` fermé.
7. **UI** `mod-apparence2.js` + `mod-style.js` + `core.js` + `index.html` + CSS ; banc pur `apparence2_ui.test.mjs`
   (libellés des effets, lecture des réglages) ; miroir pytest.
8. Preuve en réel (8799), déploiement (statiques seuls → pas de relance), relevé.
