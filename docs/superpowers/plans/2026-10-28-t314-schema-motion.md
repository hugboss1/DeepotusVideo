# t314 — C2 Illustration ou schéma → base d'animation motion — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** dans le Vectorlab, « Scanner un schéma… » : une photo d'illustration ou de schéma est **détourée**
(`detourage.py`), ses éléments sont **séparés et classés** (formes, flèches, étiquettes lues par l'OCR de t312), chaque
élément est **vectorisé** par le moteur du Vectorlab (imagetracerjs de `mod-trace.js`) et devient un **calque nommé** d'un
document neuf ; puis « Envoyer vers › Animation » ouvre le Studio sur un graphe prêt : nœud **Animation** (un élément image
par calque, révélé dans l'**ordre qui suit les flèches**, prêt pour « Chorégraphier ») et nœud **Rendu motion code** (page
déterministe, locale et gratuite).

**Architecture :**
- `services/schema_calques.py` (Pillow seul, pas de numpy dans le python embarqué) : masque du détouré, composantes
  connexes à basse définition, classement forme / flèche / étiquette, extrémités et pointe des flèches, liens
  forme → forme, ordre de révélation, découpe PNG par élément.
- `services/schema_animation.py` (pur) : calques rastérisés → éléments du nœud Animation, page motion code (données en
  base64, passe `motion_code.controler`), graphe Studio (Animation en tête, Direction motion, Rendu motion code, Render).
- `api/schema_routes.py` : `GET /api/schema/devis`, `POST /api/schema/analyser`, `POST /api/schema/animation`.
- Vectorlab : `js/mod-schema.js` (module neuf : dialogue, construction du document, envoi vers Animation) ; deux entrées
  du menu Fichier (`mod-menus.js`, `mod-charpente.js`) et l'init dans `core.js`, consignées en éditions S du groupe L6
  `scripts/i18n_l6/t314.py`.
- Boîte d'agent `scan` : + `calques_illustration` (carte, devis du détourage), sans agent qui la déclare (§11 bis).
- **Aucun maillon de bundle** : le Studio sait déjà ouvrir un graphe posé dans `window.__dzRenderGraph` puis
  `deepotus:navigate {view:"studio"}` (Envoyer vers › Studio de la Bibliothèque). Le tag `dzschemamotion` reste libre.

**Tech Stack :** FastAPI, Pillow, pricing/plafonds, matte_service (coutures fal), scan_ocr (Windows.Media.Ocr),
motion_code, studio_graph, Vectorlab (modules ES, imagetracerjs vendorisé), dzT, L6, L10.

**Spec :** `docs/superpowers/specs/2026-10-25-boite-a-outils-design.md` §7.3 (+ §2 anti-objectifs, §4 boîte `scan`,
§7.1 hôtes, §11 bis). Base : `chantier/boite-inspiration` f65b5b1a (t313 sur t312 + origin/main).

## Global Constraints

- Bancs Python depuis `backend/` avec le python embarqué, `PYTHONUTF8=1`, un à la fois, au premier plan ; données
  temporaires (`DEEPOTUS_DATA_DIR`), clés vidées ; aucun appel réseau : fal remplacé par les coutures `matte_service._upload
  / _fal_subscribe / _download`, OCR par `scan_ocr.lire_page`.
- Détourage : défaut `local-chroma` (gratuit) ; `aucun` (PNG déjà transparent ; opaque → masque estimé par la couleur du
  pourtour, même `pixel_ops.chroma_key`) ; les modèles fal du registre (`detourage.ids(IMAGE)`, voie fal) sont **payants** :
  devis gratuit, `max_usd` confirmé par l'écran (coût recalculé > max_usd → 409 sans appel), refus gratuits
  `routes._detourage_controles` (400/503) AVANT `routes._plafond([op_cout], "scan")` (402), route avec
  `_require_local_depense`. `local-rembg` n'est proposé que si `importlib.util.find_spec("rembg")`.
- Étiquettes : `scan_ocr.lire_page(octets, langue)` (fr | en ; `auto` = fr) ; OCR indisponible → aucune étiquette,
  `avertissements: ["ocr_indisponible"]`, jamais d'échec. Journaux : nombres, tailles, durées — jamais le texte lu.
- Bornes : image ≤ 20 Mo et ≤ 60 MP (`scan_pages.charger`, une seule image, pas de PDF multi-pages : la 1re page) ;
  analyse à `COTE_ANALYSE = 600` px ; au plus `MAX_ELEMENTS = 40` éléments (au-delà : les plus petits fondus dans un
  élément « Détails ») ; découpes en data URL PNG.
- Ordre de révélation (choix de Claude, §7.3) : tri topologique des formes par les flèches (départ par l'ordre de
  lecture : rangées de haut en bas, puis gauche à droite) ; une flèche juste après sa forme de départ ; une étiquette juste
  après son parent (forme qui la contient, sinon flèche proche) ; cycle → la forme restante la plus haut-gauche ; flèche
  sans départ : juste avant sa cible ; le reste à la fin, en ordre de lecture.
- Animation : `aspect` = format du nœud le plus proche du rapport du document (9:16, 4:5, 1:1, 16:9) ; durée
  `clamp(1.5 + 0.7 × n, 4, 30)` s ; entrée de 0,6 s, chaque élément tenu jusqu'à la fin ; formes `pop`, flèches glissent
  depuis leur queue (keyframes x/y), étiquettes `fade-in` ; images dans la Bibliothèque sous le nom STABLE
  `vector_<docId>_c<calqueId>.png` (réécrit en place à chaque envoi, route d'import existante).
- Page motion code : écrite par nous, données base64, aucune URL, contrôlée par `motion_code.controler` avant
  `motion_code.enregistrer` ; flèches révélées par un `clip-path` qui avance de la queue vers la pointe.
- Textes : FR référence, EN traduction ; Vectorlab = clés `vectorlab.schema.*` et `vectorlab.menus.schema_*` dans
  `frontend/shared/i18n/vectorlab.json` + `scripts/i18n_assembler.py` ; messages serveur neufs → L10
  (`scripts/i18n_l10_traductions.json`, `i18n_l10_erreurs.py --check`) ; noms de calques produits dans la langue demandée.
- Toute édition d'un module existant du Vectorlab → éditions S du groupe `scripts/i18n_l6/t314.py`, puis
  `i18n_l6_generer.py` ; test_i18n_l6 ne doit pas rougir davantage qu'à la base (mod-didact seul).
- Jamais 8765 ni 8799 ; preuve sur 8798.

## Review Focus

1. Photo de schéma sur papier (fond pas parfaitement uni, ombre) : chroma refuse (`ok=False`) → message clair qui propose
   un détourage fal ou « aucun », pas de 500. (Tâche 3 : test 3c.)
2. Image sans flèche ni texte (illustration pure) : au moins un calque, ordre = lecture, pas de lien. (Tâche 1 : 1h.)
3. Flèche à deux pointes ou trait sans pointe : classée flèche non dirigée (`dirigee: false`), aucun lien orienté inventé.
   (Tâche 1 : 1e.)
4. Document Vectorlab modifié après le scan (calque supprimé, renommé, ajouté, masqué) : l'envoi suit le document — calques
   absents ignorés, nouveaux à la fin, masqués/vides sautés. (Tâche 5 : 5d.)
5. Vectorlab ouvert seul (sans l'application autour) : le graphe est enregistré au magasin du Studio et le toast dit
   « Ouvrir un graphe » au lieu d'échouer. (Tâche 5 : 5e ; route : 3h, graphe enregistré.)

---

### Task 1: `schema_calques.py` — séparer, classer, relier, ordonner

**Files:** Create `backend/app/services/schema_calques.py` ; Test `backend/tests/test_schema_calques.py` (lanceur `__main__`,
schémas dessinés par Pillow : rectangles contour et pleins, flèches à pointe triangulaire, trait sans pointe, double
pointe, fond blanc).

**Interfaces — Produces :**
- `masque_de(img: PIL.Image) -> (PIL.Image "L", estime: bool)` — alpha > 127 ; image opaque → `pixel_ops.chroma_key`
  (`estime=True`) ; `ValueError("fond_non_uni")` si la clé échoue.
- `analyser(img: PIL.Image RGBA, lignes: list[{"texte","mots":[{"texte","x","y","l","h"}]}], langue="fr") -> dict` :
  `{"largeur","hauteur","elements":[{"id":"e01","nature":"forme"|"fleche"|"etiquette"|"details","nom",
  "boite":{"x","y","w","h"},"ordre":int,"parent":id|None,"texte"?, "lignes"?:[{"texte","boite"}], "couleur"?,
  "dirigee"?, "queue"?:{"x","y"}, "pointe"?:{"x","y"}, "de"?, "vers"?, "png"?: bytes}],"liens":[{"fleche","de","vers"}],
  "avertissements":[]}` — coordonnées dans l'image d'origine ; `png` = découpe RGBA de la boîte limitée aux pixels de la
  composante (formes, flèches, détails) ; étiquettes sans png, avec `couleur` (#RRGGBB du texte, pris dans l'image).
- `NOMS = {"fr": {...}, "en": {...}}` : « Forme 3 — Client », « Flèche 2 : Client → Serveur », « Étiquette 4 : … »,
  « Détails » (EN : Shape / Arrow / Label / Details).

**Algorithme (non déterminé par les tests) :** composantes 8-connexes du masque réduit (BFS) ; bruit < 0,02 % de l'aire
jeté ; composante dont ≥ 60 % de la boîte tombe dans une boîte de ligne OCR (+2 px) = glyphe (absorbé par l'étiquette) ;
trous (fond non atteint par remplissage depuis le bord de la boîte) ≥ 2 % de la boîte → forme ; sinon double balayage
géodésique (a = plus loin d'un pixel, b = plus loin de a, longueur L) : `L / sqrt(|P|) ≥ 2.5` → flèche, sinon forme ;
pointe = l'extrémité la plus massive dans un rayon `max(3, 0.2 L)` si ratio ≥ 1.25, sinon `dirigee: false` ;
de / vers = forme dont la boîte élargie de 3 % de la diagonale contient l'extrémité (la plus proche).

- [ ] **1.1 Tests (rouges)** : 1a deux rectangles contour + flèche gauche→droite → 2 formes, 1 flèche dirigée, lien e(A)→e(B),
  ordre A, flèche, B ; 1b la flèche droite→gauche inverse le lien et l'ordre ; 1c lignes OCR « Client » dans A et
  « Serveur » dans B → 2 étiquettes, parents A et B, noms des formes et de la flèche avec ces textes, étiquette juste après
  son parent, aucun glyphe compté comme forme ; 1d rectangle plein (sans trou) reste forme ; 1e trait sans pointe et
  double pointe → `dirigee False`, aucun lien ; 1f chaîne A→B→C dessinée de droite à gauche → ordre A,B,C (suit les
  flèches, pas la lecture) ; 1g cycle A→B→A → les deux formes présentes une fois, A (haut-gauche) d'abord ; 1h illustration
  sans flèche ni texte → ordre de lecture ; 1i > 40 composantes → 40 au plus dont un « details » ; 1j png de chaque
  forme = PNG RGBA de la taille de sa boîte, pixels hors composante transparents ; 1k `masque_de` opaque fond blanc →
  estime True ; fond bariolé → ValueError ; 1l noms EN ; 1m image 3000 px analysée en < 5 s.
- [ ] **1.2 Implémenter** jusqu'au vert ; **1.3** mutations (seuil 2.5, ratio 1.25, absorption des glyphes) : un banc rougit.
- [ ] **1.4 Commit** « t314 : schema_calques — formes, flèches, étiquettes, liens et ordre de révélation (tâche 1) ».

### Task 2: `schema_animation.py` — calques → nœud Animation, page motion code, graphe Studio

**Files:** Create `backend/app/services/schema_animation.py` ; Test `backend/tests/test_schema_animation.py`.

**Interfaces — Consumes :** `motion_code.controler/enregistrer`, `motion_choregraphe._PRESETS`, `studio_graph.valider`,
`animation_service._wh`. **Produces :**
- `aspect_pour(w, h) -> str` ; `duree_pour(n) -> float`.
- `elements(calques: list[{"image","nom","nature","boite","largeur_png","hauteur_png","queue"?,"pointe"?}], largeur, hauteur,
  aspect, duree_s) -> list` — éléments `type: "image"`, `filename`, `start/dur/hold`, keyframes bornées comme
  `motion_choregraphe._cles`, x/y = centre de la boîte placé dans le cadre (document ajusté à 90 % du cadre), `scale` =
  facteur d'ajustement × boite.w / largeur_png.
- `page(calques_avec_octets, largeur, hauteur, aspect, duree_s, fond="#ffffff") -> str` — HTML autonome ; `controler(page)==[]`.
- `graphe(nom, elements, page_id, script, aspect, duree_s) -> dict` — nœuds `an1` Animation (en tête, props {durationS, fps:30,
  elements, selected:0, script}), `md1` MotionDirection (défauts), `mc1` MotionCode {script, durationS, fps:30, pageId},
  `rn1` Render {format: aspect} ; arêtes md1→an1.direction, md1→mc1.direction, an1.out→rn1.in.
- [ ] **2.1 Tests (rouges)** : 2a aspect 16:9 pour 1600×900, 9:16 pour 900×1600, 1:1 pour 1000×1000 ; 2b starts strictement
  croissants dans l'ordre reçu, tout élément visible à la fin (`animation_service.transform_at(el, d-0.01)` non None) ;
  2c un élément centré dans le document est à x=y=50 ; scale cohérent (boite 200 px, png 400 px → moitié du facteur) ;
  2d flèche : 1re clé décalée vers sa queue, dernière clé à sa place ; 2e `motion_code.controler(page)==[]`, page sans
  « http », nom de calque « location fetch( » ne fait pas refuser la page ; 2f `studio_graph.valider(graphe)` sans
  avertissement ni refus, premier nœud `an1` ; 2g 0 calque → ValueError.
- [ ] **2.2 Implémenter** ; **2.3 Commit** « t314 : schema_animation — éléments Animation, page motion code, graphe (tâche 2) ».

### Task 3: routes `/api/schema/*`

**Files:** Create `backend/app/api/schema_routes.py` ; Modify `backend/app/main.py` (router, prefix `/api/schema`) ;
`scripts/i18n_l10_traductions.json` ; `backend/tests/_recensement_payant.py` et `test_plafonds_garde.py` si le recensement
l'exige ; Test `backend/tests/test_schema_routes.py`.

**Interfaces — Produces :**
- `GET /api/schema/devis?modele=` → `{modele, usd, voie, disponible, raison}` (gratuit ; `modeles` = liste
  `[{id, label, voie, usd}]` quand `modele` absent).
- `POST /api/schema/analyser` multipart `image`, `detourage` (défaut `local-chroma`), `langue` (fr|en|auto), `max_usd`
  (requis pour fal) → `{largeur, hauteur, detourage, usd, elements:[… png → "png": "data:image/png;base64,…"], liens,
  avertissements, duree_ms}` ; erreurs 400 (langue, modèle), 413/415 (image), 409 `{message, usd}` (coût changé),
  422 « fond_non_uni » (message qui propose fal ou « aucun »), 402 plafond, 503 clé absente, 502 fournisseur.
- `POST /api/schema/animation` JSON `{nom, largeur, hauteur, calques:[{image, nom, nature, boite, queue?, pointe?}],
  script?}` → `{graph, graph_id, page_id, aspect, duree_s}` ; images vérifiées dans la Bibliothèque (nom simple,
  `_FICHIER` du chorégraphe, existe) sinon 400 qui la nomme ; graphe enregistré au magasin du Studio
  (`<nom> — schéma animé`, id stable `g_schema_<sha8 du nom>`).
- [ ] **3.1 Tests (rouges)** : 3a sans hôte local → 403 ; 3b local-chroma sur un schéma blanc → 200, éléments, png data
  URL, aucun appel fal ; 3c fond bariolé → 422 traduit en EN avec Accept-Language en ; 3d fal sans `max_usd` → 409 sans
  appel ; 3e fal clé absente → 503 avant toute ligne `depenses` ; 3f fal avec faux `_fal_subscribe` → 200, une ligne de
  dépense, image détourée utilisée ; 3g OCR indisponible → 200 + `ocr_indisponible` ; 3h `/animation` → graphe valide,
  fichier dans studio_graphs, page lisible par `motion_code.lire` ; 3i image absente → 400 ; 3j journaux sans le texte lu.
- [ ] **3.2 Implémenter** ; L10 : `PYTHONUTF8=1 python scripts/i18n_l10_erreurs.py --check` vert ; test_plafonds_garde,
  test_i18n_l10 verts. **3.3 Commit** « t314 : routes /api/schema (devis, analyser, animation) + L10 (tâche 3) ».

### Task 4: outil d'agent `calques_illustration` (boîte `scan`)

**Files:** Modify `backend/app/services/agent_outils.py` (fonction + entrée OUTILS, nature `carte`),
`backend/app/services/agent_boites.py` (boîte scan), `backend/tests/test_agent_outils.py` si un compte est figé ;
Test `backend/tests/test_agent_schema.py`.
- Signature `async def calques_illustration(ctx, image: str = "", detourage: str = "local-chroma") -> dict` : nom
  d'image confiné à la Bibliothèque (mêmes refus que `lire_texte_image`), modèle du registre IMAGE ; rend une carte
  `{"type":"carte","genre":"devis","action":"calques_illustration","devis":usd,"arguments":{"genre":"calques_illustration",
  "image","detourage","usd"}}` ; n'appelle rien.
- [ ] **4.1 Tests** : 4a carte locale à 0 $ ; 4b modèle fal → usd = `pricing.estimate(op_cout)` ; 4c nom avec dossier
  refusé ; 4d `agent_boites.verifier()==[]`, outil dans la boîte scan, aucun agent ; 4e definitions Campagnes inchangées.
- [ ] **4.2 Implémenter**, bancs agent verts ; **4.3 Commit**.

### Task 5: Vectorlab — « Scanner un schéma… » et « Envoyer vers › Animation »

**Files:** Create `frontend/vectorlab/js/mod-schema.js`, `frontend/vectorlab/qa/schema.test.mjs` ; Modify
`frontend/vectorlab/js/mod-menus.js` (Fichier : `schema` « Scanner un schéma… » après `generer`, `schemaAnimation`
« Envoyer vers › Animation » après `bible`), `mod-charpente.js` (actions `schemaScanner` peut toujours,
`schemaAnimation` peut si doc), `core.js` (import + `initSchema(VL)` après `initExport`), `qa/menus.test.mjs`,
`vectorlab.css` (bloc « ══ t314 »), `frontend/shared/i18n/vectorlab.json`, `scripts/i18n_l6/t314.py`.

**Interfaces — Produces (purs, exportés) :**
- `doc_depuis_analyse(analyse, traces: Map<id, objets[]>, nom) -> doc` — calques empilés formes, flèches, détails,
  étiquettes (dessus) ; étiquettes = objets `texte` (x = boite.x, y = boite.y + 0,8·h, `contenu`, style {fond: couleur,
  police: "Segoe UI", corps: round(0,9·h)}) ; `doc.schema = {ordre:[calqueId…], natures:{calqueId:{nature, queue?, pointe?}}}`.
- `ordre_envoi(doc) -> calqueId[]` — `doc.schema.ordre` filtré aux calques existants visibles non vides, puis les autres
  visibles non vides dans l'ordre d'empilement.
- `nom_png(docId, calqueId) -> "vector_<docId>_c<calqueId>.png"`.
- DOM `initSchema(VL)` : `VL.schemaScanner()` ouvre la boîte (dépôt / fichier, choix du détourage avec prix, langue des
  étiquettes, « Analyser » → aperçu liste ordonnée, « Créer le document » → tracé imagetracerjs de chaque png par
  `options_trace`/`tracedata_vers_objets` de mod-trace.js, POST /api/vector/docs, ouverture `?doc=`) ; confirmation du
  devis avant tout détourage payant ; `VL.schemaAnimation()` rastérise chaque calque seul (`VL.svgCourant(true, null,
  doc réduit)` → canvas → `recadrer_alpha`), dépose le PNG par `/api/images/upload`, appelle `/api/schema/animation`,
  pose `top.__dzRenderGraph` et `top.dispatchEvent(deepotus:navigate {view:"studio"})` ; sans application autour : toast
  « graphe enregistré, ouvrez-le dans le Studio ».
- [ ] **5.1 Tests node (rouges)** : 5a doc valide (taille, calques nommés, ids uniques, étiquettes en haut) ; 5b ordre
  reconstitué = ordre d'analyse ; 5c étiquette = objet texte au bon corps ; 5d `ordre_envoi` après suppression, ajout,
  masquage ; 5e nom_png ; menus.test : entrées `schema` et `schemaAnimation` dans Fichier.
- [ ] **5.2 Implémenter**, saisie L6 `t314.py`, `i18n_l6_generer.py`, `i18n_assembler.py` ; `node qa/run.mjs` vert ;
  test_i18n_l6 et test_icones_g3_vectorlab pas plus rouges qu'à la base. **5.3 Commit**.

### Task 6: catalogue de l'agent « Demander », AGENT.md, CHANGELOG

- [ ] `python scripts/agent/catalogue.py` puis fiches des deux entrées neuves (rôle FR/EN d'après le code) ; `--check`
  vert ; AGENT.md : parcours « schéma → animation » (court, structure ≤ base) ; CHANGELOG ; test_agent_catalogue,
  test_agents_md verts. **Commit.**

### Task 7: preuve à l'écran (8798) et relecture finale

- [ ] Lanceur `scratchpad/t314/serve_t314.py` (copie de t313 : données jetables, faux fal par les coutures matte_service,
  OCR Windows réel) ; schéma de démonstration dessiné par Pillow ; captures FR et EN dans
  `docs/superpowers/specs/captures/t314/` : menu, boîte, analyse, document aux calques nommés, Studio avec le nœud
  Animation rempli, page motion code ; port libéré à la fin.
- [ ] Relecture critique de tout le diff (sous-agent), une vague de corrections, bancs base vs HEAD, registre à jour.
