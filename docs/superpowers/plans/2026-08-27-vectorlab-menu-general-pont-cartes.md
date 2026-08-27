# Vectorlab au menu général + pont Cartes — expansion d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline dans la session du spawn task_0c033bf7). Steps use
> checkbox (`- [ ]`) syntax for tracking.

> Suite du plan `2026-08-27-editeur-vectoriel-vitrail.md` (COMPLET 0→6, on
> n'y touche pas). Ordre utilisateur du 27/08 : « une fonctionnalité propre
> vectorielle qui peut être jointe depuis les "chapitres" mais aussi cartes
> pour encore plus affiner les designs des cartes ou des illustrations ».
> Les chapitres y accèdent déjà (phase 6) ; ce chantier livre les deux accès
> manquants. Cette expansion est COMMITTÉE avant le code (patron des
> phases 0→6).

**Goal :** la catégorie « Vectorlab » au rail de navigation de la SPA
(icône au style §15-2, teinte `--cat-vectoriel`, vue iframe `/vectorlab/`),
une page d'accueil bibliothèque du Vectorlab quand `?doc` est absent, et le
pont Cartes : des documents vectoriels rattachés à un jeu du Cardforge avec
le chemin retour export PNG → illustration de carte, sans étape obscure.

**Architecture :** un patcher bundle NEUF en queue de chaîne (squelette
patch_bundle_cardforge.py) pour le rail ; la bibliothèque vit dans la
surface SOURCE `frontend/vectorlab` (module `mod-biblio.js`, logique pure
testée au banc qa node) ; l'ancrage carte = colonne `deck_id` sur
`vector_docs` (patron `_auto_migrate`) ; le retour = l'art id `img:` du
Cardforge qui résout déjà les fichiers de la Library où l'export
`vector_<id>_2x.png` arrive déjà.

**Tech stack :** patch chirurgical du minifié (ancres uniques, équilibrage
de parenthèses jamais de regex), vanilla JS ESM, FastAPI/SQLAlchemy,
pytest un-processus-par-fichier (`scripts\run-tests.ps1`), banc qa node
UTF-8 (203 contrôles à garder verts).

---

## Décisions (tranchées ici, avant le code)

**D1 — La catégorie : id `vectorlab`, libellé « Vectorlab », entre
Game Assets et Settings.** Entrée du tableau nav `Uu` :
`{id:"vectorlab",label:"Vectorlab",icon:"vectorpen",desc:"Éditeur vectoriel & vitrail",new:!0}`,
insérée AVANT l'entrée settings (ancre unique vérifiée : count==1 dans le
bundle). La vue est une branche de rendu ajoutée après celle du hub Game
Assets : `s==="vectorlab"&&r.jsx("iframe",{src:"/vectorlab/",title:"Vectorlab",style:{position:"absolute",inset:0,width:"100%",height:"100%",border:"0",background:"var(--bg-base)"}},"pvlab")`
— le conteneur des vues est `position:relative`, l'iframe le remplit.
Le rail lui-même RESTE à l'or de marque (DESIGN.md §15-3.2 : le rail pilote
des sections frères) ; la teinte de catégorie vit DANS la surface.

**D2 — L'icône `vectorpen` : courbe de Bézier + ancres + poignées.** Style
§15-2 strict : grille 24×24, masses pleines `fill="currentColor"` portées
par le groupe, sujet à opacité 1, support à `.32`, aucun contour, aucune
couleur en dur, aucun PNG. Sujet = le ruban de courbe (bande pleine entre
deux cubiques, ~2,6 px d'épaisseur) tendu de l'ancre bas-gauche à l'ancre
haut-droite, plus les DEUX ancres carrées tournées à 45° (l'écho exact des
ancres du mode nœuds de l'éditeur). Support = l'appareil de poignées : une
barre fine à −45° croisant le ventre de la courbe, terminée par deux
pastilles rondes. Tracé complet (documenté aussi en DESIGN.md §15-bis,
ajout daté — le fichier reste la vérité design) :

```html
<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
  <rect x="1.7" y="7.8" width="14" height="1.7" rx=".85"
        transform="rotate(-45 8.7 8.7)" opacity=".32"/>
  <circle cx="13.6" cy="3.7" r="2" opacity=".32"/>
  <circle cx="3.7" cy="13.6" r="2" opacity=".32"/>
  <path d="M4.1 18.6 C4.1 9 9 4.1 18.6 4.1 L18.6 6.7 C10.4 6.7 6.7 10.4 6.7 18.6 z"/>
  <rect x="3.4" y="16.6" width="4" height="4" transform="rotate(45 5.4 18.6)"/>
  <rect x="16.6" y="3.4" width="4" height="4" transform="rotate(45 18.6 5.4)"/>
</svg>
```

Dans la carte d'icônes du bundle, l'entrée est posée au format des voisines
(props React camelCase, le glyphe porte sa couleur) devant `gamegrid:` —
même geste d'insertion que dzdesign pour gamegrid.

**D3 — La teinte : `--cat-vectoriel`, teinte OKLCH 340 (rose vitrail).**
Mêmes clarté/chroma que les six existantes : sombre `oklch(.72 .13 340)`,
thème clair `oklch(.52 .12 340)`. La roue est occupée en 25/80/145/200/255/
300 ; 340 tombe au milieu du plus grand arc vide (300→25) — distinct de
tout voisin d'au moins 40°, contraste `--cat-ink` équivalent aux six
mesurées (§15-bis : la clarté commande le contraste). Ajoutée aux TROIS
copies qui font système : `frontend/shared/deepotus.tokens.css` (source),
`frontend/dist/shared/deepotus.tokens.css` (copie servie sous `/shared/`,
reste byte-identique à la source), `frontend/dist/theme-v2.css` (couche
tokens de la page du bundle — le PIÈGE mémorisé : elle ne charge pas la
feuille partagée). Consommateur : `vectorlab.css` gagne
`@import url("/shared/deepotus.tokens.css");` (même mécanisme que
cardforge.css) et pose `--cat: var(--cat-vectoriel)` sur `:root` — les
accents de la bibliothèque (liseré, boutons primaires, focus) lisent
`var(--cat)`. La surface vectorlab RESTE à son thème sombre propre
(état livré des phases 0→6, l'éditeur n'a pas de thème clair) ; on ajoute
`select{color-scheme:dark}` (patron dropdown-theming) pour que les popups
des selects natifs de la bibliothèque suivent, et la preuve vérifie
l'iframe dans l'app en thème sombre ET clair (la surface est légitimement
sombre dans les deux, comme un panneau outil).

**D4 — La bibliothèque du Vectorlab (`?doc` absent).** Dans la surface
source, pas le bundle. `index.html` gagne une section `#biblio` cachée par
défaut ; `core.js:charger()` sans `?doc` bascule `body.mode-biblio` (CSS :
la rangée d'édition et les contrôles d'édition de l'en-tête se cachent, la
bibliothèque s'affiche) et appelle `VL.ouvrirBiblio()`. Contenu : rangée de
création (input nom, select rôle libre/decor/lumiere/personnage, input
taille `640×960`, bouton Créer), rangée de filtre (recherche debounce
300 ms → `?q=`, select rôle → `?role=`), grille de cartes-vignettes
(`GET /api/vector/docs` — sans filtre la route liste TOUS les docs, tri
updated_at desc déjà servi). Chaque carte : vignette
`/api/vector/docs/<id>/vignette.png?v=<version>` (cache-buster phase 6,
repli ◧ si aucune), nom échappé, `rôle · v<n>`, badge d'ancrage (⚓ chapitre
/ 🂠 cartes / ◇ bibliothèque), boutons Ouvrir (`location.href="?doc=<id>"`),
Dupliquer (`POST /duplicate`, nom au prompt, la copie reste où elle est),
Supprimer (confirm — la suppression ARCHIVE, phase 0). Créer :
`POST /vector/docs {name, role, doc: docVierge(nom, w, h)}` puis ouverture
`?doc=<id>`. L'éditeur gagne dans l'en-tête un bouton `⌂ Bibliothèque`
(retour `/vectorlab/`, confirm si `etat.sale`). La logique PURE
(`parseTaille`, `docVierge`, `bibLigne`, `bibVide`) vit dans
`js/mod-biblio.js` et se teste au banc node (`qa/biblio.test.mjs`, RED
d'abord) — `docVierge` est prouvé compatible `parserDoc` de mod-doc. Aucun
endpoint nouveau : les routes phase 0/6 suffisent.

**D5 — L'ancrage carte↔doc : colonne `deck_id` (patron `_auto_migrate`),
PAS la convention de préfixe sur `entity_id`.** Motifs : `entity_id` est
déjà sémantisé « entité de la bible » (D3 du plan mère) et String(36) ne
laisse pas la place d'un préfixe + id ; `deck_id` est le miroir exact de
`chapter_id` (nullable, indexable, filtrable proprement). Mécanique :
`VECTOR_DOCS_COLUMNS = [("deck_id", "VARCHAR(36)")]` + l'entrée
`("vector_docs", VECTOR_DOCS_COLUMNS)` dans la boucle de `_auto_migrate`
+ la colonne sur le modèle. Routes étendues (TDD RED d'abord, section M du
banc) : `POST /vector/docs` accepte `deck_id`, `GET /vector/docs` filtre
`?deck_id=`, `_vector_meta` l'expose, `POST /duplicate` accepte `deck_id`
(la copie s'ancre au jeu). Pas de liaisons d'instanciation deck (YAGNI v1 :
les docs d'un jeu lui appartiennent) ; pas de cascade à la suppression d'un
jeu (même règle que les chapitres phase 0 : l'existence de l'ancre n'est
pas contrôlée, un doc orphelin reste visible et supprimable dans la
bibliothèque). La MIGRATION est exercée en vrai : le banc pré-crée à froid
une table `vector_docs` à l'ANCIENNE forme avec une ligne héritée, puis
tout le banc tourne sur la base migrée (la ligne héritée survit,
`deck_id IS NULL`).

**D6 — Le pont côté Cardforge : 4e onglet « Vectoriel » du panneau P1
(mod-face.js).** C'est LE panneau des illustrations (Catalogue / Importées
/ Générer par IA) — l'ancrage le plus court vers « affiner les designs des
cartes ». `["cat","imp","ai"]` devient `["cat","imp","ai","vec"]`, bouton
`data-tab="vec"` libellé `Vectoriel <n>`, volet `#cf-face-pane-vec` :
rangée de création (input nom + bouton « + Nouveau document » →
`POST /vector/docs {name, role:"libre", deck_id: CF.doc().id, doc}` avec la
taille de la FENÊTRE D'ILLUSTRATION courante arrondie — `frameWindow(g)` —
repli 815×1110 ; puis `window.open("/vectorlab/?doc=<id>")`), bouton
Rafraîchir, liste des docs du jeu (`GET /api/vector/docs?deck_id=`,
vignettes cache-bustées `?v=`) avec par ligne : Ouvrir (window.open, le
geste déjà employé par mod-export pour export.svg), « Poser 2× » et
Supprimer (confirm, DELETE = archive). « Poser 2× » = LE chemin retour :
`fetch HEAD /api/images/vector_<id>_2x.png` → si absent, toast « exporte
d'abord en PNG 2× depuis le Vectorlab (menu Exporter) » ; si présent,
`IMGS.delete(imgURL(nom))` (purge du cache de session — sinon un ré-export
resservirait l'ancien pixel) puis `setArt("img:vector_<id>_2x.png")` — le
préfixe `img:` est déjà résolu par `artSource` (magasin `/api/images/`),
par la pose, par l'aperçu et par la production ; le fichier est RÉÉCRIT en
place par tout ré-export (upload même nom) : rééditer le vecteur puis
ré-exporter suffit à rafraîchir la carte. Le décor de cadre accepte
déjà `img:<fichier de la Library>` (`DECOR_SRC_RE`) : le même PNG sert
les décors sans travail nouveau — dit dans l'aide du volet. L'état VECS
se recharge au changement de document (événement `core:doc`) et au bouton
Rafraîchir. Miroirs pytest (section O) au patron K/L.

**D7 — Le patcher : `scripts/patch_bundle_vectorlab.py`, NOUVELLE queue de
chaîne.** Squelette copié de patch_bundle_cardforge.py avec ses DANGERS
au complet : jamais `repatch_all.py --from` sur la queue (mtimes menteurs
vfxrack/subs), lancement SEUL, lecture/écriture `newline=""` (bundle CRLF),
jamais d'ancre imprimée (console cp1252), backup dédié `.bak_vectorlab`
poussé en queue par mtime, garde de double application (marqueur
`src:"/vectorlab/"`), sanity pré-backup, parité de deltas recalculée,
sondes de stabilité (les sondes cardforge + `dz_nav_collapsed` + `__dzCatBar`
— les patchs amont doivent rester intacts), `--check` à sec, vérification
post-écriture sinon restauration. Trois ancres (unicité vérifiée dans le
bundle courant, count==1 chacune) :

- **V1-icone** — ancre `gamegrid:r.jsxs("g",{fill:"currentColor",children:[`
  → insertion de l'entrée `vectorpen:` (tracé D2 au format ICONS de
  dzdesign) devant, suivie de l'ancre intacte.
- **V2-nav** — ancre
  `{id:"settings",label:"Settings",icon:"cog",desc:"Keys, paths, persona"}`
  → l'entrée D1 + une virgule + l'ancre intacte.
- **V3-vue** — ancre `s==="assets3d"&&r.jsx(DzGameAssetsHub,{variant:e}),`
  → l'ancre intacte + la branche iframe D1 + une virgule.

Après application : copie `.mjs` + `node --check` (module ES), test manuel
de la garde (2e lancement → refus), `--check` sur l'app installée = refus
attendu au marqueur (patron cardforge : on COPIE le bundle patché, on ne
repatche pas l'app).

**D8 — Preuve réelle et nettoyage.** App réelle `http://127.0.0.1:8765`
après déploiement sha-vérifié + stop/relance + santé 2.5.0. Piloter par
`javascript_tool` (le Browser pane ne composite pas toujours ; ni await ni
return top-level → tout en `(async () => {...})()`). Chaîne prouvée :
catégorie au rail (icône rendue, entrée cliquée → iframe bibliothèque),
recherche réelle, création d'un doc jetable → l'éditeur s'ouvre, retour ⌂ ;
côté Cardforge sur un JEU DE TEST créé par l'API cards : onglet Vectoriel →
créer un doc lié, l'ouvrir, y dessiner par `VL.executer`, Sauver, exporter
PNG 2× (`VL.exporterPNG(2)`), retour cardforge → Rafraîchir → Poser 2× →
`face.src === "img:vector_<id>_2x.png"` ET l'aperçu peint. NETTOYAGE
vérifié aux endpoints : docs jetables archivés par DELETE, jeu de test
supprimé, PNG jetables retirés de la Library (`DELETE /api/images/{f}`),
les docs réels « Baie vitrail - demo » et « Vitrail - baie generee »
INTOUCHÉS.

## Structure de fichiers

```
scripts/patch_bundle_vectorlab.py       NEUF — patcher queue de chaîne (D7)
frontend/dist/assets/index-BEOJX8L5.js  patché V1/V2/V3 (résultat committé)
frontend/dist/theme-v2.css              + --cat-vectoriel (2 blocs)
frontend/shared/deepotus.tokens.css     + --cat-vectoriel (2 blocs)
frontend/dist/shared/deepotus.tokens.css  copie byte-identique de la source
frontend/vectorlab/index.html           + section #biblio + bouton ⌂
frontend/vectorlab/vectorlab.css        + @import tokens, --cat, styles biblio
frontend/vectorlab/js/mod-biblio.js     NEUF — pur (parseTaille, docVierge,
                                        bibLigne, bibVide) + initBiblio(VL)
frontend/vectorlab/js/core.js           charger() → mode biblio ; init module
frontend/vectorlab/qa/biblio.test.mjs   NEUF — banc node RED d'abord
frontend/cardforge/js/mod-face.js       onglet « Vectoriel » (D6)
backend/app/services/storage.py         deck_id + VECTOR_DOCS_COLUMNS
backend/app/api/routes.py               deck_id sur POST/GET/duplicate/méta
backend/tests/test_vector_docs.py       + pré-seed migration, sections M/N/O
DESIGN.md                               §15-bis : ajout daté (icône + teinte)
```

---

## Task 1 : le pont backend `deck_id` (TDD)

**Files:** Modify `backend/app/services/storage.py`,
`backend/app/api/routes.py`, `backend/tests/test_vector_docs.py`.

- [ ] **1.1 RED** — dans test_vector_docs.py : (a) au module, APRÈS le bloc
  d'env et AVANT tout import app, pré-créer la base à l'ANCIENNE forme
  (sqlite3 stdlib : table `vector_docs` sans `deck_id` + une ligne héritée
  `vd-legacy` nommée « Legacy pré-migration », chapter ch-legacy, role
  decor) ; (b) section M :

```python
# ── M. le pont cartes : deck_id (colonne _auto_migrate) + migration réelle ───

def test_le_pont_cartes_deck_id_et_la_migration():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import VectorDoc, async_session_factory, init_db
        await init_db()                      # migre la base pré-créée à froid
        async with async_session_factory() as s:
            legacy = await s.get(VectorDoc, "vd-legacy")
            assert legacy is not None and legacy.name == "Legacy pré-migration"
            assert legacy.deck_id is None    # la colonne est née, la ligne a survécu
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/vector/docs", json={
                "name": "Décor de carte", "role": "libre",
                "deck_id": "deck_test77", "doc": _doc("Décor de carte")})
            assert r.status_code == 200, r.text
            did = r.json()["id"]
            r = await c.get(f"/api/vector/docs/{did}")
            assert r.json()["meta"]["deck_id"] == "deck_test77"
            r = await c.get("/api/vector/docs", params={"deck_id": "deck_test77"})
            assert [d["name"] for d in r.json()["docs"]] == ["Décor de carte"]
            r = await c.post(f"/api/vector/docs/{did}/duplicate",
                             json={"deck_id": "deck_test77", "name": "Copie deck"})
            assert r.status_code == 200
            nid = r.json()["id"]
            r = await c.get(f"/api/vector/docs/{nid}")
            assert r.json()["meta"]["deck_id"] == "deck_test77"
            for x in (did, nid):
                assert (await c.delete(f"/api/vector/docs/{x}")).status_code == 200

    asyncio.run(scenario())
```

- [ ] **1.2** le voir échouer (`run-tests.ps1 -Filter vector`) — colonne et
  filtre inexistants
- [ ] **1.3 GREEN** — storage.py : colonne
  `deck_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)`
  + `VECTOR_DOCS_COLUMNS = [("deck_id", "VARCHAR(36)")]` + l'entrée dans la
  boucle `_auto_migrate` ; routes.py : `deck_id` accepté au POST, filtré au
  GET, exposé par `_vector_meta`, accepté au duplicate
- [ ] **1.4** banc vector vert (16 tests + le neuf) ; voisins atelier ×2
  verts
- [ ] **1.5 commit** — `vectorlab : ancre deck_id (pont cartes) par _auto_migrate, migration exercee a froid`

## Task 2 : la bibliothèque du Vectorlab (TDD qa node)

**Files:** Create `frontend/vectorlab/js/mod-biblio.js`,
`frontend/vectorlab/qa/biblio.test.mjs` ; Modify `index.html`,
`vectorlab.css`, `js/core.js`, `backend/tests/test_vector_docs.py` (N).

- [ ] **2.1 RED** — `qa/biblio.test.mjs` (patron des bancs existants,
  sortie UTF-8) : `parseTaille` (« 640×960 », « 640x960 », « 640 x 960 » →
  {w:640,h:960} ; refuse vide/NaN/≤0/>8192) ; `docVierge("Baie", 640, 960)`
  → accepté par `parserDoc` de mod-doc, un calque `c1` déverrouillé
  visible, objets [] ; `bibLigne(meta)` → contient
  `vignette.png?v=<version>` si `vignette:true` et le repli sinon, nom
  ÉCHAPPÉ (`<script>` neutralisé), badge ⚓/🂠/◇ selon
  chapter_id/deck_id/aucun, les trois `data-bib-*` portant l'id ;
  `bibVide(q, role)` nomme les filtres actifs
- [ ] **2.2** le voir échouer (`node qa/run.mjs` → module introuvable)
- [ ] **2.3 GREEN pur** — mod-biblio.js : les quatre fonctions pures
  exportées (echappement local, badges, cache-buster) + `initBiblio(VL)`
  (DOM seulement à l'appel)
- [ ] **2.4** banc qa node vert (203 + les neufs)
- [ ] **2.5 UI** — index.html (section #biblio + bouton ⌂ dans la barre),
  vectorlab.css (@import tokens, `--cat`, `select{color-scheme:dark}`,
  grille de cartes, mode-biblio), core.js (charger() sans ?doc →
  `VL.ouvrirBiblio()` ; initBiblio dans la chaîne d'init) ; `node --check`
  sur core.js et mod-biblio.js
- [ ] **2.6 miroir pytest** — section N (RED puis GREEN) : index.html porte
  `id="biblio"` et le bouton ⌂ ; mod-biblio.js interroge `/vector/docs`,
  ouvre `?doc=`, duplique et supprime ; core.js appelle `ouvrirBiblio`
- [ ] **2.7 commit** — `vectorlab : page d'accueil bibliotheque (recherche, roles, creer/dupliquer/supprimer, vignettes)`

## Task 3 : l'onglet Vectoriel du Cardforge

**Files:** Modify `frontend/cardforge/js/mod-face.js`,
`backend/tests/test_vector_docs.py` (O).

- [ ] **3.1 RED miroir** — section O : mod-face.js contient
  `"vec"` dans la liste des onglets, `data-tab="vec"`,
  `cf-face-pane-vec`, `/api/vector/docs?deck_id=`, `/vectorlab/?doc=`,
  `img:vector_` et le HEAD de présence `/api/images/vector_`
- [ ] **3.2 GREEN** — mod-face.js : état module `VECS` + `chargerVecs()`
  (fetch par deck courant, silencieux hors deck), onglet + volet (création
  taille fenêtre d'illustration via `frameWindow(g)` repli 815×1110,
  Rafraîchir, lignes vignette/Ouvrir/Poser 2×/Supprimer), `poserVec` (HEAD
  puis purge `IMGS` puis `setArt("img:…")`), rechargement sur `core:doc` ;
  `node --check`
- [ ] **3.3** banc vector vert ; `run-tests.ps1 -Filter cards_face` vert
  (le miroir cards du panneau P1)
- [ ] **3.4 commit** — `cardforge : onglet Vectoriel du panneau face - docs lies au jeu, poser l'export 2x en illustration`

## Task 4 : la teinte `--cat-vectoriel`

**Files:** Modify `frontend/shared/deepotus.tokens.css`,
`frontend/dist/shared/deepotus.tokens.css`, `frontend/dist/theme-v2.css`.

- [ ] **4.1** les deux blocs de chaque fichier (sombre `.72 .13 340`,
  clair `.52 .12 340`), la copie dist/shared restant byte-identique à la
  source (sha comparés) ; vectorlab.css consomme (fait en 2.5)
- [ ] **4.2 commit** — `design : teinte de categorie --cat-vectoriel (OKLCH 340) aux trois feuilles de tokens`

## Task 5 : le patcher bundle + DESIGN.md

**Files:** Create `scripts/patch_bundle_vectorlab.py` ; Modify
`frontend/dist/assets/index-BEOJX8L5.js` (résultat), `DESIGN.md`.

- [ ] **5.1** le patcher D7 (squelette cardforge complet) ; `--check` sur
  le dépôt : 3 ancres à 1, marqueur absent, CRLF homogène
- [ ] **5.2** application ; sondes stables à 1 ; copie `.mjs` +
  `node --check` ; relance → refus de double application constaté
- [ ] **5.3** DESIGN.md §15-bis : ajout daté 27/08 (l'icône vectorpen —
  tracé complet —, la teinte 340, l'entrée nav, la branche iframe, le
  patcher en queue)
- [ ] **5.4 commit** — `bundle : categorie Vectorlab au rail (icone vectorpen, entree nav, vue iframe) - patcher assert-garde en queue de chaine`

## Task 6 : déploiement + preuve réelle + nettoyage (D8)

- [ ] **6.1** copie sha-vérifiée vers `%LOCALAPPDATA%\DeepotusVideoGen`
  (backend touché ⇒ stop.ps1, relance uvicorn cachée, santé 2.5.0)
- [ ] **6.2** la preuve D8 au navigateur, de bout en bout, thème sombre
  puis clair pour le rail/l'iframe
- [ ] **6.3** nettoyage vérifié aux endpoints (docs jetables, jeu de test,
  PNG jetables ; les 2 docs réels intouchés)
- [ ] **6.4** relevé dans CE document + commit final —
  `docs(plans): releve du chantier vectorlab menu general + pont cartes`

## Hors périmètre (assumé)

Liaisons d'instanciation deck↔doc (le patron chapitre reste disponible si
le besoin naît) ; rôle éditable après création ; thème clair de la surface
Vectorlab ; toute dépense API (le chantier est local de bout en bout).
