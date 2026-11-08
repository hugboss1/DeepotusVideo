# Cartes hexagonales recto verso — plan d'implémentation (t421)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fabriquer dans le Card Forge des jeux hexagonaux recto verso depuis N fichiers de design, jusqu'à la planche et au fichier de coupe, et débloquer les noms accentués.

**Architecture:** Un hexagone vit dans le rectangle qui l'englobe : `trim_mm`, toile et rendu restent, un masque et un contour s'ajoutent. L'imposition hexagonale vit dans un fichier à part (`cards/print_hex.py`) qui ne touche pas `Plan` ni `build_plan` : c'est la garantie que les rectangles ne bougent pas d'un pixel. Le plan hexagonal n'existe que côté serveur ; l'écran affiche sa réponse.

**Tech Stack:** FastAPI, Pillow, JS sans bundler du Card Forge, bancs Python à lanceur `__main__` et bancs `node`.

**Spec:** `docs/superpowers/specs/2026-11-07-cartes-hexagonales-design.md` (+ constat `2026-11-05-workflow-cartes-constat.md`).

## Global Constraints

- Python embarqué : `$PY = $env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe`, lancé depuis `backend/` : `& $PY tests/<banc>.py`. Il ignore PYTHONPATH : chaque banc insère `backend/` lui-même et a son lanceur `__main__`.
- Aucune chaîne visible en dur : `dzT`, FR et EN, dans `frontend/shared/i18n/cartes.json` (ou `photolab`, `vectorlab` selon l'écran), puis `scripts/i18n_assembler.py`. Tout message serveur neuf passe par `app.i18n` si le module voisin le fait.
- Charte `dz-charte.css`, angles vifs. Noms et commentaires en français, datés t421.
- `CardGeom` gelée : propriétés seulement. `contract.py` reste la seule source des pixels.
- Aucun patch du bundle. Aucune dépense IA. Jamais le 8765.
- Une copie `frontend/dist/shared` reste identique à `frontend/shared`.
- Un rectangle ne change d'aucun pixel : aucun chemin rectangulaire ne reçoit de branche qui modifie son résultat.
- Une seule PR, branche `claude/workflow-cartes-60a8e2`. Commits `cartes : <quoi> (t421)`, avec `git commit --only <fichiers>`.
- `.claude/launch.json` local contient une entrée de preuve : ne pas le committer.

## Review Focus

1. Un nom accentué en forme décomposée (NFD, zip venant d'un Mac) : accepté comme sa forme composée (test en tâche 1).
2. Un jeu dont le nombre de cartes laisse une dernière page incomplète, en recto verso : chaque verso reste en face de son recto (test en tâche 7).
3. Un deck passé en hexagone puis revenu en rectangle : cadre, slots et table intacts (test en tâche 3).
4. Un fichier importé deux fois devient `x_recto-1.png` : il n'est pas apparié en silence au mauvais verso, il est signalé sans verso (test en tâche 5).
5. Un design déjà à la coupe (sans fond perdu) : rien n'est rogné, même aux milieux des côtés où sont les symboles (test en tâche 4).

---

### Task 1 : Noms accentués

**Files:**
- Modify: `backend/app/api/photolab_routes.py:36-37` et `/bibliotheque`, `backend/app/api/routes.py` (renommage, ligne ~4191), `frontend/shared/dz-envoi.js`, `frontend/dist/shared/dz-envoi.js`, `frontend/photolab/js/mod-fichier.js`, `frontend/vectorlab/js/mod-envoi.js`, `frontend/tilelab/envoi.js`
- Test: `backend/tests/test_noms_accentues.py`, `frontend/shared/qa/envoi_noms.test.mjs`

**Interfaces:**
- Produces : `lireEnvoi` / `recevoir` rendent `{image, via}`, ou `{refus: nom}` quand un envoi destiné à l'écran porte un nom invalide ; `null` s'il n'y a rien.

- [ ] **Step 1 : Bancs rouges.** `test_noms_accentues.py`, sur un dossier jetable : `/ouvrir` et `/actions/lot` acceptent `adrian_veilleur_des_âmes_fracturées.png` et sa forme NFD ; refusent `a/b.png`, `a\b.png`, `..`, `x\n.png`, `con.png`, `nul.txt` ; le renommage garde `été` ; `/bibliotheque` sans `nom`, sur un document `544a527f-carte.png`, donne une base `carte` sans empreinte ni `-png`. `envoi_noms.test.mjs` : `nomValide` vrai pour les deux formes, faux pour `a/b.png` ; `lireEnvoi` d'un envoi `{cible:"photolab", image:"a/b.png"}` rend `{refus:"a/b.png"}`.
- [ ] **Step 2 : Vérifier le rouge.** `& $PY tests/test_noms_accentues.py` puis `node frontend/shared/qa/envoi_noms.test.mjs` : échecs sur les noms accentués.
- [ ] **Step 3 : Implémenter.** `_NOM_IMAGE = r"[\ẁ-ͯ]([\ẁ-ͯ. -]{0,179}[\ẁ-ͯ-])?"`, `_NOM_SERVI` de même sans espace ; JS : `/^[\p{L}\p{M}\p{N}_][\p{L}\p{M}\p{N}._ -]{0,180}$/u`. Garder `_PERIPHERIQUE` et le confinement au dossier. Renommage : remplacer le tri ASCII par le retrait des seuls caractères interdits de Windows (`\/:*?"<>|` et contrôles). `/bibliotheque` : appliquer au nom par défaut le même nettoyage que `nomDocument` (empreinte en tête, extension, `-png`). Les trois labs affichent `commun.envoi.refuse` sur `r.refus`, et n'ouvrent rien.
- [ ] **Step 4 : Relever les autres gardes** : `git grep -n "A-Za-z0-9" backend/app/api backend/app/services/library_index.py backend/app/services/cards/data.py` ; corriger celles qu'un nom de la Bibliothèque traverse dans ce parcours. Les gardes de `doc`, `did` et fichiers internes (`DECOR_SRC_RE`, `img_N.png`) restent.
- [ ] **Step 5 : Vert.** Mêmes commandes, puis `& $PY tests/test_photolab_envoi.py`.
- [ ] **Step 6 : Commit.** `cartes : les noms accentués passent le Photolab et les envois (t421)`.

### Task 2 : Formats et géométrie

**Files:**
- Create: `backend/app/services/cards/hexa.py`
- Modify: `backend/app/services/cards/contract.py`, `backend/app/services/cards/core.py` (défaut de coin), `frontend/cardforge/js/core.js:113-…`, `frontend/shared/i18n/cartes.json`, les bancs comptant 12 formats (`test_cards_core.py:209,399,406` et ceux que `git grep -n "12" backend/tests/test_cards_*.py` désigne)
- Test: `backend/tests/test_cards_hexa.py`

**Interfaces:**
- Produces, Python :
  - `FORMATS[id]["forme"] == "hex"` et `["orientation"] in ("pointe", "plat")`. Ids : `hex_p50, hex_p635, hex_p75, hex_p90` (pointe en haut), `hex_f50, hex_f635, hex_f75, hex_f90` (côté plat en haut).
  - `CardGeom.forme -> "rect" | "hex"`, `CardGeom.orientation -> str | None`, `CardGeom.contour_mm -> list[tuple[float, float]]` (six sommets, repère coin haut-gauche de la coupe, sens horaire depuis le sommet haut).
  - `hexa.decale(points, d_mm) -> list[tuple]` (décalage perpendiculaire, `d_mm` > 0 vers l'extérieur).
  - `hexa.contour_toile_mm(g) -> list[tuple]` : contour du fond perdu en repère toile, tronqué à la toile (polygone éventuellement à plus de 6 sommets).
  - `hexa.contour_sur_mm(g) -> list[tuple]` : zone sûre, repère toile.
  - `hexa.milieux_cotes_mm(g) -> list[tuple]`.
- Produces, JS : `geom.forme`, `geom.orientation`, `geom.contour_mm`, `CF.hexContours(g) -> {coupe, fond, sur, milieux}`, mêmes valeurs à 0,001 mm près.

- [ ] **Step 1 : Banc rouge.** `test_cards_hexa.py` : `trim_mm` de `hex_p50` = `(50.0, 57.735)`, `hex_f50` = `(57.735, 50.0)`, `hex_p90` = `(90.0, 103.923)` ; six sommets, côtés égaux à 0,002 près ; `decale` de 3 mm donne une apothème + 3 ; pour `hex_p50` à fond perdu 3 mm, tous les points de `contour_toile_mm` restent dans la toile et la pointe est à au moins 2,5 mm de la coupe ; `geom("poker_us").forme == "rect"` ; `to_dict` d'un rectangle inchangé (égalité stricte avec un instantané). Confrontation Python / JS sur les 8 formats, sur le patron de `test_cards_core.py:406`.
- [ ] **Step 2 : Vérifier le rouge.** `& $PY tests/test_cards_hexa.py`.
- [ ] **Step 3 : Implémenter.** Arrondir `trim_mm` à 3 décimales. `p × 2/√3`. `hexa.py` sans dépendance à part `contract` ; troncature par découpe Sutherland-Hodgman sur le rectangle de toile. `normalize_format` : `corner_mm` 0 par défaut pour un hexagone. Exclure les 8 formats de `fmts` des profils d'imprimeurs (`contract.py:186`). Libellés traduits sur le patron `cartes.core.fmt_*` (FR « Hexagone 50 mm, pointe en haut », EN « Hexagon 50 mm, point up » ; « côté plat en haut » / « flat side up »).
- [ ] **Step 4 : Vert.** `& $PY tests/test_cards_hexa.py`, puis `test_cards_core.py`, `test_cards_print.py`, `test_cards_gabarits.py`.
- [ ] **Step 5 : Commit.** `cartes : huit formats hexagonaux et leur contour (t421)`.

### Task 3 : Aperçu hexagonal, verso sans cadre, pièces hors périmètre

**Files:**
- Modify: `frontend/cardforge/js/core.js` (`renderQueued` ~654-726, `guidesPainter` ~612, `galThumb` ~1906), `frontend/cardforge/js/mod-frame.js:3520` (`paintBack`) et son painter de recto, rails de `mod-solid`, `mod-texture`, `mod-gltf`, `mod-forge3d`, `mod-edition`, `mod-capture`, `frontend/cardforge/index.html` si besoin, `backend/app/services/cards/print.py`, `solid.py`, `gltf.py`, `forge3d.py`, `edition.py`
- Test: `backend/tests/test_cards_hexa_ecran.py`, `backend/tests/test_cards_hexa_refus.py`

**Interfaces:**
- Consumes : `CF.hexContours(g)`, `geom.forme`.
- Produces : `contract.refuser_si_hex(g, sortie: str) -> None` lève `HTTPException(409, …)` avec la phrase `cartes.hexa.non_gere`.
- Produces : `CF.horsHex(id) -> bool`, table des rails hors périmètre : `frame, solid, texture, gltf, forge3d, edition, capture`.

- [ ] **Step 1 : Bancs rouges.** `test_cards_hexa_ecran.py`, sous node avec le patron des bancs `_ecran` : après rendu d'un deck hexagonal, l'angle de la toile est transparent et le centre opaque ; un deck rectangulaire appelle `clip` autant de fois qu'avant (empreinte du rendu identique) ; `paintBack` avec `family:"none"` et `card.back` dessine le verso, sans `card.back` laisse la face blanche ; un deck à cadre et sans `card.back` dessine le même dos qu'avant ; **hexagone puis retour rectangle** : `doc.frame`, `doc.type.slots`, `doc.data` égaux à l'état de départ. `test_cards_hexa_refus.py` : 409 avec phrase sur `/print/pack`, `/print/preflight`, `/print/foil-mask`, `/gltf` (routes de production), `/solid`, `/forge3d` (lancement), `/edition/tts`, `/edition/livret`, `/edition/mockup` pour un deck `hex_p50` ; 200 sur les mêmes pour `poker_us`.
- [ ] **Step 2 : Vérifier le rouge.**
- [ ] **Step 3 : Implémenter.** En fin de rendu, si `g.forme === "hex"` : composition `destination-in` du polygone `fond`. Guides : polygones coupe, fond, sûr à la place des rectangles. `galThumb` dessine l'hexagone. `paintBack` : en tête, si `card.back` et `family === "none"`, poser le verso sur la toile et sortir ; la branche existante reste intacte. Le painter de cadre sort sans rien dessiner si hexagone, sans toucher au document. Les rails `horsHex` affichent `cartes.hexa.non_gere`. Lister les routes réelles avec `grep -n "@router" backend/app/services/cards/{solid,gltf,forge3d,edition}.py` et placer `refuser_si_hex` sur celles qui produisent une sortie, pas sur les lectures dont l'écran a besoin au chargement.
- [ ] **Step 4 : Vert.** Ces bancs, puis `test_cards_frame.py`, `test_cards_face.py`, `node frontend/cardforge/qa/test_core_contract.mjs`.
- [ ] **Step 5 : Commit.** `cartes : aperçu hexagonal, verso sans cadre, sorties refusées (t421)`.

### Task 4 : Créer un deck depuis des images

**Files:**
- Create: `backend/app/services/cards/depuis_images.py`
- Modify: `backend/app/services/cards/__init__.py` (inclure le routeur AVANT `core`, comme `models`)
- Test: `backend/tests/test_cards_depuis_images.py`

**Interfaces:**
- Consumes : `core.create_deck`, `core.patch_deck`, `settings.images_path`.
- Produces : `POST /api/cards/decks/depuis-images`, corps `{name, format, images: [str], versos?: [str|null], verso_commun?: str, fond_perdu?: bool = true}` -> `{deck}`. `versos` a la longueur de `images` s'il est présent ; `verso_commun` l'exclut (400 si les deux).
- Produces : `GET /api/cards/gabarit/{fmt}.{ext}` réservé à la tâche 6 (même routeur).

- [ ] **Step 1 : Banc rouge.** Trois images dont une accentuée : le deck a `frame.family == "none"`, `gem/banner` faux, `corner == "none"`, `type.slots == []`, `type.seeded`, `face.seeded`, `face.fit == "cover"`, `data.columns == ["nom","art","dos"]`, `data.map == {"art":"art","dos":"back"}`, ordre des lignes égal à l'ordre reçu ; `nom` = nom sans extension, `_` remplacés par des espaces ; `verso_commun` recopié sur chaque ligne ; `fond_perdu: false` -> `format.bleed_mm == 0` et `safe_mm` conservé ; `fond_perdu` vrai -> fond perdu natif ; image absente -> 404 nommant le fichier **et aucun deck créé** (compte `list_deck_summaries` inchangé) ; nom avec séparateur -> 400 ; `images` vide -> 400 ; plus de 500 images -> 400 ; format inconnu -> 400 ; empreintes des images inchangées. Rouvert par `POST /{did}/data/build`, `cards[0].art` et `cards[0].back` sont justes. **Sans fond perdu, sur `hex_p50`, la zone couverte par l'image contient les six milieux de côtés de la coupe.**
- [ ] **Step 2 : Vérifier le rouge.**
- [ ] **Step 3 : Implémenter `depuis_images.py`.** Valider tout avant `create_deck`. Écrire par `core.patch_deck` : `format`, `frame`, `type`, `face`, `data`. Limite 500, comme le traitement par lots. Pas de ligne `dos` vide différente d'une chaîne vide.
- [ ] **Step 4 : Vert.** Banc, puis `test_cards_models.py`, `test_cards_data.py`.
- [ ] **Step 5 : Commit.** `cartes : créer un deck depuis des images (t421)`.

### Task 5 : Dialogue « Nouveau jeu depuis des images »

**Files:**
- Create: `frontend/cardforge/js/depuis-images.js`, `frontend/cardforge/js/depuis-images-logique.js`, `frontend/cardforge/css/depuis-images.css`
- Modify: `frontend/cardforge/js/core.js` (entrée de galerie ~1990, API publique), `frontend/cardforge/index.html`, `frontend/shared/i18n/cartes.json`
- Test: `frontend/cardforge/qa/depuis_images.test.mjs`, `backend/tests/test_cards_depuis_images_ecran.py`

**Interfaces:**
- Consumes : route de la tâche 4, `GET /api/images`, `GET /api/library/projets`, `GET /api/library/projets/{pid}`, `POST /api/images/upload`.
- Produces, core : `CF.bibliotheque = {images(), projets(), projet(id), importer(file)}`, `CF.deckDepuisImages(corps)`.
- Produces, logique pure (`window.CFImages` et export node) :
  - `triNaturel(noms) -> noms`
  - `apparier(noms) -> {cartes: [{recto, verso|null}], sansVerso: [noms], orphelins: [noms]}`
  - `nomCarte(fichier) -> str`
  - `inclutFondPerdu(wImg, hImg, fmt, bleed) -> bool` (rapport de la toile à 0,5 % près)
  - `formatPropose(dims, formats) -> id` (rapport médian, ordre des formats en cas d'égalité)
  - `ecarts(dims, fmt, inclut) -> [nom]`

- [ ] **Step 1 : Banc rouge.** `depuis_images.test.mjs` : `triNaturel(["c10","c2","C1"])` = `["C1","c2","c10"]` avec accents ; `apparier` : `a_recto.png`+`a_verso.png`, `b.png`+`b_verso.png`, `c_front.png`+`c_back.png` appariés, `d_verso.png` seul dans `orphelins`, **`e_recto-1.png` + `e_verso.png` : `e_recto-1.png` dans `sansVerso` et `e_verso.png` dans `orphelins`** ; `nomCarte("la_magnat_de_la_tech.png")` = `la magnat de la tech` ; `formatPropose` donne `poker_us` pour 89 × 1060×1484 + 4 × 977×1610, et `ecarts` nomme les 4 ; `inclutFondPerdu` vrai à la taille du gabarit, faux à la taille de coupe.
- [ ] **Step 2 : Vérifier le rouge.**
- [ ] **Step 3 : Implémenter la logique**, puis le dialogue en quatre temps de la spec, avec `window.__dzDialogue` si son API le permet, sinon la structure de la galerie. Grille : `loading="lazy"`, recherche, filtre projet, « tout », import multiple. Verso : aucun, commun, apparié. Récapitulatif avec `ecarts`, `sansVerso`, `orphelins`, et l'avertissement de liseré quand la case est décochée. Création : `CF.deckDepuisImages`, puis ouverture par `?deck=`.
- [ ] **Step 4 : Banc d'écran.** `test_cards_depuis_images_ecran.py` : présence de l'entrée de galerie, chaque clé `cartes.depuis.*` en FR et EN, aucune chaîne en dur dans `depuis-images.js`.
- [ ] **Step 5 : Vert**, puis `node frontend/cardforge/qa/test_core_contract.mjs` et `& $PY ..\scripts\i18n_assembler.py --check` si l'option existe.
- [ ] **Step 6 : Commit.** `cartes : dialogue de création depuis des images (t421)`.

### Task 6 : Gabarit à télécharger

**Files:**
- Modify: `backend/app/services/cards/depuis_images.py`, `backend/app/services/cards/hexa.py`, `frontend/cardforge/js/depuis-images.js`, `frontend/cardforge/js/mod-print.js`
- Test: `backend/tests/test_cards_gabarit_hexa.py`

**Interfaces:**
- Consumes : `hexa.contour_toile_mm`, `hexa.contour_sur_mm`, `hexa.milieux_cotes_mm`.
- Produces : `hexa.gabarit_svg(g) -> str`, `hexa.gabarit_png(g) -> bytes`, `GET /api/cards/gabarit/{fmt}.{svg|png}?bleed_mm=&dpi=`. Rectangle : 404 ; le gabarit est hexagonal.

- [ ] **Step 1 : Banc rouge.** PNG : RGBA, taille `canvas_px`, DPI inscrit, fond transparent aux angles, opaque nulle part hors des traits. SVG : `width="…mm"`, `viewBox` en mm, trois groupes `coupe`, `fond-perdu`, `zone-sure`, six repères `milieu` ; sommets de `coupe` égaux à `contour_mm` + décalage fond perdu à 0,01 mm.
- [ ] **Step 2 : Vérifier le rouge.**
- [ ] **Step 3 : Implémenter.** Couleurs distinctes et légende par la `class` SVG, pas de texte dans l'image. Boutons « Télécharger le gabarit » (PNG, SVG) dans le dialogue et l'onglet Impression.
- [ ] **Step 4 : Vert.**
- [ ] **Step 5 : Commit.** `cartes : gabarit hexagonal (t421)`.

### Task 7 : Plan en nid d'abeilles et fichiers de coupe

**Files:**
- Create: `backend/app/services/cards/print_hex.py`
- Modify: `backend/app/services/cards/print.py` (routes seulement ; `print_hex` ne déclare pas de routeur)
- Test: `backend/tests/test_cards_print_hex.py`

**Interfaces:**
- Consumes : `CardGeom`, `hexa`, `contract.SHEETS`.
- Produces :
  - `PlanHex` (dataclass) : `sheet`, `size_mm`, `geom`, `marge_mm`, `gouttiere_mm`, `cases: list[tuple[float,float]]` (coin haut-gauche de la coupe, mm, par page), `n_cartes`, `pages`, `reperes_mm: list[tuple[float,float]]`, `trait: bool`, `duplex: bool`.
  - `plan_hex(g, sheet, marge_mm, gouttiere_mm, n, trait, duplex) -> PlanHex`, `ValueError` si `gouttiere_mm < 2 × bleed_mm`, ou si aucune case n'entre.
  - `carte_de(p, page, k, cote) -> tuple[x, y]` (`cote` `"recto"|"verso"` ; verso = `size_w - x - trim_w`), `contour_page_mm(p, k) -> points`.
  - `coupe_svg(p, page) -> str`, `coupe_dxf(p, page) -> str`, `coupe_zip(p) -> bytes`.
  - `compose_page(p, images: list[Image], page, cote) -> Image`, `pdf_planche(p, recto, verso) -> bytes`.
  - Routes, sous `/api/cards/{did}/print/hex` : `POST /plan` (`{sheet, marge_mm, gouttiere_mm, n_cards, trait, duplex}` -> plan en dict), `POST /coupe` (ZIP), `POST /pdf` (form `spec`, `fronts`, `backs`, comme `/pdf`).

- [ ] **Step 1 : Banc rouge.** Calculs : `hex_p50` sur A4, marge 12, gouttière 6 : rangées décalées d'une demi-case, écart perpendiculaire entre deux voisines égal à 6 à 0,01 près, aucune paire de contours de fond perdu ne se chevauche, toutes les cases dans la marge, et aucune à moins de 3 mm d'un repère ; plus de cases par page qu'en grille droite ; idem `hex_f90` sur A3. Gouttière 5 pour un fond perdu 3 -> `ValueError`. Repères : trois, aucune symétrie (l'ensemble tourné de 180° ou retourné diffère). **7 cartes pour une page de 6 en duplex : page 2 recto et verso n'ont qu'une carte, et son verso est exactement à la position miroir.** Pour chaque case, chaque sommet du verso = miroir du recto à 0,01 mm. Sorties : SVG `width` en mm, calques `coupe`, `reperes`, une polyligne fermée par carte ; DXF R12 lisible par un petit lecteur de banc : `$INSUNITS` 4, calques `COUPE` et `REPERES`, `POLYLINE` fermées, `CIRCLE` pour les repères, Y inversé (y DXF = hauteur - y) ; sommets SVG = DXF = `contour_page_mm` à 0,01 mm ; repères identiques partout ; ZIP `page-01.svg`, `page-01.dxf`…. Image : `compose_page` à la taille exacte de la feuille, angle hors carte blanc, centre de case égal au centre de la carte, repères présents, trait présent seulement si `trait`, recto sans verso laissé blanc. PDF : `pages × (2 si duplex)`, page au format de la feuille.
- [ ] **Step 2 : Vérifier le rouge.**
- [ ] **Step 3 : Implémenter le plan.**

Pointe en haut, avec `W` = largeur, `H` = hauteur, `g` = gouttière (écart perpendiculaire) :

```text
pas_x = W + g
pas_y = 0.75 * H + g * sqrt(3) / 2
rangée impaire : décalage x de pas_x / 2
```

Côté plat en haut : échanger les axes. Trois repères Ø 5 mm dans la marge : haut-gauche, haut-droit, bas-gauche à une distance différente du bord, pour rompre la symétrie. La zone des cases laisse la marge, repères compris. Centrer l'ensemble. Portrait seulement (`flip` long). `sheet == "card"` refusé.

- [ ] **Step 4 : Implémenter sorties et routes.** `build_dxf` (3DFACE) ne convient pas : écrire `POLYLINE`/`VERTEX`/`SEQEND` et `CIRCLE` à la main, R12, à côté. PDF par Pillow (`save_all`, `resolution=dpi`), trait et repères pixélisés : le fichier de coupe seul est vectoriel. `compose_page` colle chaque carte avec le masque `contour_toile_mm` ; les images sont déjà masquées mais la toile de la carte reste l'autorité. Les routes appellent `_deck` puis refusent un rectangle (400).
- [ ] **Step 5 : Vert**, puis `& $PY tests/test_cards_print.py` (inchangé).
- [ ] **Step 6 : Commit.** `cartes : planche en nid d'abeilles et fichiers de coupe (t421)`.

### Task 8 : Écran d'impression hexagonal

**Files:**
- Modify: `frontend/cardforge/js/mod-print.js`, `frontend/cardforge/css/mod-print.css`, `frontend/shared/i18n/cartes.json`
- Test: `backend/tests/test_cards_print_hex_ecran.py`

**Interfaces:**
- Consumes : routes `/print/hex/*`, `M.api`.

- [ ] **Step 1 : Banc rouge.** Sous `geom.forme === "hex"`, le panneau rend le bloc `data-role="hex"` et n'appelle ni `layoutOf` ni `layout`, ni `preflight` ; pour un rectangle, le panneau est identique à l'instantané et aucun appel `print/hex` ne part. Clés FR et EN présentes.
- [ ] **Step 2 : Vérifier le rouge.**
- [ ] **Step 3 : Implémenter.** Réglages feuille (A4, Letter, A3), marge, gouttière, recto verso, trait imprimé. Aperçu de page dessiné depuis `POST hex/plan`. Message d'erreur serveur affiché tel quel. Boutons « PDF d'impression » et « Fichier de coupe (ZIP) ». Rendu des cartes par `cardBlob`, comme l'export existant. Un rappel : couper recto dessus.
- [ ] **Step 4 : Vert.**
- [ ] **Step 5 : Commit.** `cartes : écran d'impression hexagonal (t421)`.

### Task 9 : Preuves, assistant, documentation, PR

**Files:**
- Modify: `AGENTS.md`, `docs/agent/catalogue/*`, `docs/agent/AGENT.md`, `scripts/run-tests.ps1` si les bancs y sont listés
- Create: mémoire `cartes-hexagonales-t421.md`

- [ ] **Step 1 : Mutations.** Copier les sources, puis muter et vérifier qu'un banc rougit : décalage de rangée, signe du miroir verso, inversion Y du DXF, seuil `2 × bleed`, troncature à la toile, garde `refuser_si_hex`, `family == "none"` de `paintBack`, regex de nom, `fond_perdu`. Restaurer et comparer avec `cmp`.
- [ ] **Step 2 : Skill `connaissance-agent`** pour les éléments visibles neufs.
- [ ] **Step 3 : `.\scripts\run-tests.ps1`.** Vert, ou chaque rouge comparé à `origin/main`, et nommé dans la PR.
- [ ] **Step 4 : Preuve à l'écran hexagonale** sur 8799, données neuves, en FR puis EN : 3 designs tirés du zip (extraits à la dimension du gabarit, dont un nom accentué) + un verso → jeu `hex_p75` visible, verso regardé, PDF et ZIP ouverts et regardés, sommets recalculés sur les fichiers produits. Empreintes des images d'origine identiques.
- [ ] **Step 5 : Preuve rectangulaire** du parcours d'origine : import par l'écran, 3 cartes dont 2 accentuées rééditées dans le Photolab et enregistrées, deck `poker_us` sans fond perdu créé depuis le dialogue, originaux intacts.
- [ ] **Step 6 : `AGENTS.md`** (`hexa.py`, `print_hex.py`, `depuis_images.py`, dialogue), mémoire et index.
- [ ] **Step 7 : Suivi.** Créer `t421` dans `taches` de l'artifact `9WVmPNinFLNN3Xxv2EHGht`, sur le modèle de `t420`.
- [ ] **Step 8 : PR vers main**, puis `get_status` / `bind_pr` et lecture de la CI. Pas de fusion ni d'installation sans accord.
