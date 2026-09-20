# Vectorlab classe Affinity — LOT F : apparence avancée — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module pur).

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot F ; §2.6 couleur et remplissages, §2.7 calques et effets, §2.8
> texte, §2.10 symboles et styles ; D2 champs optionnels `symboles{}`,
> `styles{}`, `couleursGlobales{}`, objet `instance` ; D9 modules purs).
> Branche `chantier/vectorlab-affinity`, après le lot E (`8e2f8f0`). Ce
> plan est COMMIS avant le code.

> **RELEVÉ DE LIVRAISON (17/09/2026) : LOT F LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Livré** (10 commits `410c7f5`→`30ab83c`, poussés) : `mod-effets.js` feuille
> (six effets chaînés dans UN `<filter>` par objet : ombre, ombre interne,
> lueur, biseau spéculaire, contour par morphologie, incrustation ; 16 modes
> de fusion ; motifs hachures / points / damier / grille en `<pattern>` ;
> dégradé conique en 72 secteurs interpolés) ; modèle : `style.effets /
> fusion / contours / masque` validés et compilés (enveloppe `<g data-objet>`
> avec copies SANS id, `mix-blend-mode`, masque de luminance), `doc.motifs`
> + fond `motif:<id>`, dégradé `conique` qui suit la forme,
> `op_degrade_transparence`, `doc.couleursGlobales` (`glob:<nom>` résolu à
> la compilation et à la suppression), écrêtage `groupe.clip` → `<clipPath>`
> (`op_ecreter` / `op_desecreter`), `doc.styles` (copie à l'application),
> `doc.symboles` + objet `instance` → `<use>` d'un `<g id=sym_>` des defs
> (créer / poser / modifier / détacher / supprimer, origine qui suit la bbox
> à l'échelle), objets `cadre` (mod-texteplus feuille : mesure injectable,
> coupe aux mots / retours / caractères, tspans gauche / centre / droite /
> justifié, retrait, débordement) et `textechemin` (`d` copié, décalage) ;
> `mod-couleur` : `palette_harmonique` (5 harmonies) ; `mod-pinceauvec.js`
> feuille (plat / fuseau / calligraphie → chemin fermé) ; UI
> `mod-apparence2.js` (panneau Apparence + en sept sections, outil pinceau
> vectoriel J, mesure du texte du navigateur injectée au rendu et à l'export).
>
> **TDD tenu** : RED ×7 (effets, apparence2, harmonie, symboles, texteplus,
> pinceauvec, apparence2_ui). Bancs : node **948 contrôles** (+134 : effets
> 27, apparence2 34, harmonie 8, symboles 21, texteplus 24, pinceauvec 12,
> apparence2_ui 8), pytest `test_vector_docs` **34 passed** (+2 : miroir de
> surface et aller-retour des champs). Le banc a redressé deux attentes :
> les secteurs du conique prennent un rayon ×1,5 (couvrir les coins du
> carré) et l'origine d'une instance recule de bx·sx sous l'échelle (la bbox
> reste en place) ; un id libéré par une instance détachée se réattribue à
> une copie (ids libres du modèle).
>
> **Prouvé en réel** (8799, données isolées, viewport 1400×900, gestes
> pointeur synthétiques, lecture DOM) : ombre + lueur → `<g data-objet>
> filter=url(#fx_r1)`, filtre de **10 primitives**, dx 12 relu dans
> `feOffset`, retrait d'un effet ; fusion multiply → `mix-blend-mode` calculé
> ; deux contours → **3 ellipses** (10, 6, principale), 2 copies
> `data-contour` ; conique → `<pattern>` de **72 secteurs**, `fill=url(#g1)`
> ; transparence → `<mask id=m_g2>` + `mask=url`, retrait ; motif damier
> pas 12 → pattern à 2 rects ; coller dans → groupe `clip r1`, `clip-path`,
> p1 dedans, libérer → 0 groupe ; couleur globale « Ma-marque » → fond
> `glob:` rendu `#12AB34`, teinte changée → `#FF00FF` partout, suppression
> → hex résolu ; harmonie triade → 3 couleurs dans la palette ; style
> « cerne » (avec ombre) appliqué à e1 → `filter=url(#fx_e1)` ; symbole
> « pion » (r1 + e1) → `<use href=#sym_s1>` de 360 px d'écran, seconde
> instance posée `translate(24 24)`, **glissée au pointeur** (x 24 → 88),
> détachée en rect + ellipse (1 `<use>` restant) ; texte → cadre 200×60 →
> **2 tspans** coupés par `measureText` (92 px pour 14 caractères), justifié
> → 1 `textLength` ; texte + chemin → `textechemin`, `<textPath
> href=#tp_t1>`, p1 conservé, décalage 30 % relu ; pinceau vectoriel J,
> largeur 12 → chemin **fermé de 19 sommets** rempli sans contour, 66 px de
> haut ; Ctrl+Z → 5 objets ; sauvegarde → `styles`, `symboles`,
> `textechemin` relus.
>
> **Deux défauts attrapés par la preuve** : la section Texte + ne s'affichait
> qu'à sélection unique (texte + chemin n'offraient pas « sur le chemin ») ;
> l'harmonie perdait son type et ses pastilles au re-rendu du panneau.
>
> **Déployé** : 18 fichiers (= base lot E `eea0020` vérifiés par
> hash-object, 11 absents) → sauvegarde
> `_backup_predeploy_2026-09-17g-vectorlab-lotF` (7 fichiers) → copie depuis
> `git archive 30ab83c` → **18 = cible, 105/105 du Vectorlab = cible**.
> **Aucun Python touché : aucune relance nécessaire.**
>
> **Reste** : le conique est une approximation en secteurs (pas de vrai
> dégradé continu) ; les effets ne s'appliquent pas aux objets `image` ni
> aux enfants d'un symbole ; le biseau est un éclairage spéculaire simple ;
> le masque de transparence est linéaire gauche → droite (ses points se
> règlent comme un dégradé) ; l'édition VIVANTE d'un symbole passe par
> détacher → modifier → recréer (pas de mode d'édition en place) ; le cadre
> de texte n'a pas de poignées propres (redimensionner par la bbox) ; le
> texte sur chemin ne suit pas les modifications ultérieures du chemin (d
> copié, dit dans la conception).

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
