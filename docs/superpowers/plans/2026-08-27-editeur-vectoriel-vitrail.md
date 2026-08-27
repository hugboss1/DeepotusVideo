# Éditeur vectoriel « Vectorlab » — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **CE PLAN EST SOUMIS À L'UTILISATEUR AVANT TOUT CODE** (ordre du 27/08 :
> « fonctionnalité nouvelle à planifier »). Rien de ce document n'est
> implémenté. La phase 0 est détaillée au pas TDD prêt à exécuter ; les
> phases 1→6 sont cadrées par contrats et critères de preuve, et chacune
> reçoit son expansion pas-à-pas (writing-plans) dans sa session d'exécution,
> après validation de ce plan.

**Goal :** un véritable éditeur vectoriel intégré à l'app (calques, chemins de
Bézier, booléens, dégradés, texte, export SVG/PNG), pensé pour créer et
retoucher des illustrations vitrail — plombs = tracés, fragments de verre =
aplats, nativement vectoriels — et ancré à la section chapitres du DA pour
définir, chapitre par chapitre, les éléments de DÉCOR, de LUMIÈRE et de
PERSONNAGES dans une bibliothèque réutilisable.

**Architecture :** surface modulaire en sources `frontend/vectorlab/` (patron
cardforge/atelier : vanilla JS core+mods+qa, servie par FastAPI, jamais le
bundle) ; le document est un JSON versionné (vérité), compilé vers SVG-DOM
pour l'édition et l'export ; fichiers sur disque + index SQLite ; booléens par
bibliothèque vendorisée (martinez, MIT) sur polygones aplatis ; PNG rasterisé
CLIENT (zéro dépendance backend) et déposé dans la Library.

**Tech stack :** vanilla JS modulaire, SVG DOM, FastAPI + SQLAlchemy
(storage.py, patron `_auto_migrate`), martinez-polygon-clipping vendorisé,
harnais `scripts/run-tests.ps1` (backend) + banc `qa/` node headless (patron
cardforge), fiche épinglée `style_vitrail.json` pour le mode vitrail.

---

## Décisions d'architecture (brainstorm du 27/08, tranché)

**D1 — Surface UI : module source, pas le bundle.** Un éditeur complet ne se
patche pas dans du minifié. `frontend/vectorlab/` (nom au patron
spritelab/tilelab), monté comme `/atelier` (statique no-cache dans main.py),
ouvert depuis la SPA et l'Atelier par lien/iframe avec query params
(`/vectorlab/?doc=<id>`). La mémoire frontend-compiled-only l'impose ; le
précédent cardforge (44 116 lignes en 11 modules sources) le prouve.

**D2 — Moteur : SVG-DOM à l'écran, JSON en vérité.** Le document JSON
(calques/objets/styles) se compile vers SVG pour l'édition (hit-testing natif,
thème CSS, export quasi gratuit) ; on ne lit JAMAIS le DOM comme état. Canvas
2D (redraw + hit-testing maison) refusé pour V1 : coût sans gain à l'échelle
vitrail (centaines de fragments). Bézier : path data M/L/C/Q/Z + éditeur de
nœuds. Booléens : aplatir les chemins en polygones (tolérance paramétrée),
opérer via martinez vendorisé, retracer — l'approche suffit au « verre
découpé par les plombs ». Dégradés : linear/radial SVG natifs. Texte : <text>
SVG en V1 (fontes du starter-catalog), vectorisation des glyphes hors V1.

**D3 — Données : fichiers + index.** Contenu dans
`%LOCALAPPDATA%\DeepotusVideoGenData\assets\vector\<doc_id>.json` (écriture
atomique tmp+rename, historique `.v<n>.json` conservé ×10) ; catalogue et
ancrage dans SQLite (`VectorDoc` : id, name, chapter_id?, entity_id?, role,
version, updated_at — patron `V1_2_NEW_COLUMNS`/`_auto_migrate`). Les exports
partent dans le dossier images existant → toute l'app les voit (planches,
épisodes, Scheduler).

**D4 — Ancrage chapitres du DA.** L'Atelier gagne par chapitre un panneau
« Éléments vectoriels » filtré par rôle (`decor` / `lumiere` / `personnage`) :
créer (doc pré-lié chapter_id+role), ouvrir (vectorlab), exporter vers la
bible (le PNG exporté devient `inspiration_image` d'une entité → alimente les
planches existantes). Un doc sans chapter_id = bibliothèque globale ; un
chapitre peut RÉFÉRENCER un doc d'un autre (instanciation sans copie). Les
docs `lumiere` sont des calques de halos/dégradés pensés pour se superposer.

**D5 — Vitrail natif via la fiche épinglée.** Le mode vitrail lit
`style_vitrail.json` (servie par l'API) : palette pré-chargée aux ancres hex
de la famille, générateur paramétrique de baie (ogive, réseau de plombs,
bordure ornementale aux fractions déclarées), presets de motifs (iris, rayons,
halo). La part de contours de l'export se MESURE (PIL au banc, esprit
mesure_style) contre les bornes déclarées 6–15 %.

**D6 — Réutilisation cardforge : les patterns, pas le moteur.** mod-face.js
(4 385 lignes) est un éditeur de mise en page canvas : multi-sélection,
guides, snap, undo, drag-handles s'y calquent (mêmes conventions d'UX et de
banc qa/), mais il n'a ni Bézier ni SVG — le moteur géométrique est neuf.

**D7 — Coûts : 0 $.** Tout est local (édition, booléens, exports). Seul un
tir de planche conditionnée par un décor exporté coûterait — c'est l'opt-in
déjà réglé par la machinerie existante (devis/ordre), hors périmètre.

## Structure de fichiers (verrouillée)

```
frontend/vectorlab/
  index.html            coquille + chargement des modules
  vectorlab.css         thème (tokens deepotus, clair/sombre)
  js/core.js            bus d'événements, état, undo/redo, io API (patron cardforge)
  js/mod-doc.js         modèle-document JSON <-> compilation SVG (LA vérité)
  js/mod-tools.js       outils: sélection, rect, ellipse, plume (Bézier), nœuds
  js/mod-layers.js      calques, z-ordre, verrous, visibilité
  js/mod-style.js       fonds, contours, dégradés, opacité, pipette
  js/mod-bool.js        wrapper martinez: union/soustraction/intersection/division
  js/mod-text.js        texte SVG simple
  js/mod-vitrail.js     mode vitrail: fiche épinglée, générateur de baie, presets
  js/mod-export.js      SVG (serveur), PNG (rasterisation client -> Library)
  vendor/martinez.min.js  booléens (MIT, vendorisé, LICENSE jointe)
  qa/                   banc node headless du modèle-document (patron cardforge/qa)
backend/app/api/routes.py         + routes /vector/* (section dédiée)
backend/app/services/storage.py   + modèle VectorDoc (+ _auto_migrate)
backend/app/services/vector_store.py  disque: atomique, historique, chemins
backend/app/main.py               + mount statique /vectorlab (copie du bloc /atelier)
backend/tests/test_vector_docs.py banc CRUD + disque + ancrage chapitre
frontend/atelier/atelier.js       + panneau « Éléments vectoriels » par chapitre
```

---

## Phase 0 — Socle & contrats (détaillée, prête à exécuter après validation)

> **RELEVÉ (27/08, validation utilisateur reçue) : PHASE 0 LIVRÉE ET
> DÉPLOYÉE.** Quatre cycles RED→GREEN constatés (magasin disque, index
> SQLite, CRUD 5 routes, miroirs+mount) ; banc `test_vector_docs.py` 5 tests
> verts, banc qa node 10 contrôles verts, 9 fichiers de tests voisins verts ;
> déployé sha-vérifié (14 fichiers), santé 2.5.0. Preuves app réelle : doc
> « Baie vitrail - demo » créé v1 → réécrit v2 → rouvert dans
> `/vectorlab/?doc=` (SVG 640×960, calques verre+plombs, 6 objets, cadre de
> plomb à 18), archive `.v1.json` sur disque, panneau « Éléments
> vectoriels » servi par l'Atelier (aucun chapitre réel : le panneau par
> chapitre est verrouillé aux miroirs du banc, sans polluer les données).
> Deux adaptations en route, sans dévier du plan : le banc qa cardforge est
> navigateur (pas node) — le qa Vectorlab est un vrai banc node autonome
> (`qa/run.mjs`), comme le plan le nommait ; `package.json {type: module}`
> local pour que node lise les mêmes fichiers ESM que le navigateur.
> Prochaine étape : phase 1 (dessin), sur ordre.

Livrable : la surface `/vectorlab` servie, le CRUD complet des documents
versionnés ancrables à un chapitre, un canvas SVG qui affiche un document —
ouvrable depuis l'Atelier. Preuve : banc backend vert + créer/rouvrir un doc
depuis l'app réelle.

### Task 0.1 : modèle VectorDoc + magasin disque

**Files:**
- Modify: `backend/app/services/storage.py` (classe VectorDoc + migration)
- Create: `backend/app/services/vector_store.py`
- Test: `backend/tests/test_vector_docs.py`

- [x] **Step 1 : écrire le test qui échoue**

```python
"""Vectorlab — documents vectoriels versionnés (fichiers + index SQLite).
Run: pytest tests/test_vector_docs.py -q"""
import asyncio, json, os, pathlib, sys, tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_le_magasin_ecrit_atomique_et_historise():
    from app.services import vector_store as VS
    doc = {"v": 1, "nom": "Baie test", "taille": {"w": 640, "h": 960},
           "calques": [{"id": "c1", "nom": "plombs", "visible": True,
                        "verrou": False, "objets": []}]}
    did = VS.creer(doc)                    # écrit <did>.json
    assert VS.lire(did)["nom"] == "Baie test"
    doc["nom"] = "Baie v2"
    v = VS.ecrire(did, doc)                # bump version + garde .v1.json
    assert v == 2 and VS.lire(did)["nom"] == "Baie v2"
    dossier = pathlib.Path(os.environ["VECTOR_FOLDER"])
    assert (dossier / f"{did}.v1.json").is_file()
    # l'écriture est atomique: jamais de fichier tronqué visible
    assert json.loads((dossier / f"{did}.json").read_text("utf-8"))["nom"] == "Baie v2"
```

- [x] **Step 2 : le voir échouer** — `pytest tests/test_vector_docs.py -q` →
  `ModuleNotFoundError: app.services.vector_store`
- [x] **Step 3 : implémenter `vector_store.py`** (uuid4 hex pour `did` ;
  dossier depuis `settings`/env `VECTOR_FOLDER` avec défaut
  `DeepotusVideoGenData/assets/vector` ; `ecrire` = rotation `.v<n>.json`
  (garder 10), écriture `tmp` + `os.replace`)
- [x] **Step 4 : le voir passer**, puis ajouter au même fichier le test du
  modèle SQLite (VectorDoc: id/name/chapter_id/entity_id/role/version/
  updated_at, insertion + relecture via `async_session_factory`), le voir
  échouer, implémenter (classe + entrée `_auto_migrate`), le voir passer
- [x] **Step 5 : commit** — `vectorlab : magasin disque atomique historise + index VectorDoc`

### Task 0.2 : routes CRUD `/api/vector/docs`

**Files:**
- Modify: `backend/app/api/routes.py` (section `# /vectorlab`)
- Test: `backend/tests/test_vector_docs.py` (section app, patron test_style_da)

- [x] **Step 1 : test RED (app bootée, stubs du banc, zéro clé réelle)** —
  `POST /api/vector/docs {name, role, chapter_id?, doc}` → `{id, version:1}` ;
  `GET /api/vector/docs?chapter_id=&role=` → liste filtrée triée
  updated_at ; `GET /api/vector/docs/{id}` → `{meta, doc}` ;
  `PUT /api/vector/docs/{id} {doc}` → version bump ; `DELETE` → 200 et le
  fichier part en historique (pas de suppression brute) ; rôles limités à
  `("decor","lumiere","personnage","libre")` sinon 400
- [x] **Step 2 : le voir échouer** (404 sur les routes)
- [x] **Step 3 : implémenter** (handlers minces sur vector_store + VectorDoc)
- [x] **Step 4 : le voir passer** ; relancer aussi
  `run-tests.ps1 -Filter vector`
- [x] **Step 5 : commit** — `vectorlab : CRUD /vector/docs versionne, ancrable chapitre/entite`

### Task 0.3 : surface servie + canvas lecture

**Files:**
- Modify: `backend/app/main.py` (mount `/vectorlab`, copie du bloc `/atelier`)
- Create: `frontend/vectorlab/index.html`, `vectorlab.css`, `js/core.js`,
  `js/mod-doc.js`
- Test: `frontend/vectorlab/qa/doc_compile.test.mjs` (node, patron cardforge/qa)

- [x] **Step 1 : test RED qa** — `compilerSVG(doc)` rend un `<svg>` string :
  taille du doc, un `<g>` par calque (ordre, `display:none` si invisible), un
  `<path d>` par objet path, rect/ellipse natifs ; `parserDoc(json)` refuse
  (`throw`) un doc sans `v`/`taille`/`calques`
- [x] **Step 2 : le voir échouer** (`node qa/run.mjs` — runner copié du
  cardforge, sortie UTF-8 forcée, leçon du harnais)
- [x] **Step 3 : implémenter mod-doc** (compilation pure, aucune lecture DOM)
- [x] **Step 4 : passer** ; puis index.html + core.js chargent `?doc=<id>`
  via l'API et affichent le SVG (zoom/pan basiques molette+glisser)
- [x] **Step 5 : preuve navigateur** — créer un doc par curl, ouvrir
  `http://127.0.0.1:8765/vectorlab/?doc=<id>`, voir le rendu ; commit
  `vectorlab : surface servie, compilation doc->SVG prouvée au banc qa`

### Task 0.4 : bouton d'ancrage dans l'Atelier

**Files:**
- Modify: `frontend/atelier/atelier.js` (+ section chapitre)
- Test: assertion miroir dans `backend/tests/test_vector_docs.py` (le JS
  contient le panneau et l'appel `/vector/docs?chapter_id=`)

- [x] Panneau « Éléments vectoriels » sous le chapitre ouvert : liste (nom,
  rôle, version), « + Décor / + Lumière / + Personnage » (POST puis ouverture
  `/vectorlab/?doc=`), lien « ouvrir ». RED (assertion miroir) → GREEN →
  preuve navigateur réelle → commit — `atelier : panneau elements vectoriels par chapitre`

---

## Phase 1 — Dessin (outils, calques, sélection, undo)

Contrats : plume Bézier (clic=ancre, glisser=poignées, double-clic=fin,
édition de nœuds : déplacer/convertir angle↔courbe/supprimer), rect/ellipse
(shift=carré/cercle), sélection simple/multi (lasso + shift-clic),
transformations (déplacer/redimensionner avec poignées/rotation), calques
(créer/renommer/réordonner/verrou/visibilité), undo/redo (pile de commandes
sur le JSON — patron core cardforge), snapping grille + guides tirés des
règles, raccourcis (V plume P rect R ellipse E, Ctrl+Z/Y, Suppr).
**Preuve :** banc qa headless sur CHAQUE commande (le doc JSON après commande
== attendu, aller-retour compiler/parser stable octet à octet) ; scénario
navigateur : dessiner 3 objets sur 2 calques, sauver, rouvrir → JSON
identique ; undo ramène exactement l'état précédent (comparaison JSON).

## Phase 2 — Apparence

Contrats : fond/contour (couleur, épaisseur, pointillés, joints), dégradés
linéaires/radiaux (poignées sur canevas, stops éditables), opacité
objet/calque, groupes (grouper/dégrouper, transformations composées), ordre z
(avant/arrière), pipette. **Preuve :** snapshots SVG au banc (docs de
référence compilés → SVG attendu figé, diff exact) ; rendu réel vérifié.

## Phase 3 — Booléens & texte

Contrats : union/soustraction/intersection/division sur 2+ objets
(aplatissement Bézier à tolérance 0,25 px, martinez, retraçage en paths) ; le
cas-métier « une plaque de verre DIVISÉE par le réseau de plombs devient des
fragments indépendants » est un preset une-action ; texte SVG (fonte, corps,
graisse, interlettrage) posé et transformable. **Preuve :** banc qa des
booléens sur cas de référence (aires attendues à ±0,5 %, compte de fragments
exact sur la division) ; licence martinez jointe et créditée.

## Phase 4 — Exports & intégrations

Contrats : export SVG (GET `/api/vector/docs/{id}/export.svg` — compilation
serveur du JSON, même code que qa via port Python minime OU compilation
client POSTée : trancher à l'exécution sur preuve de parité au banc) ; export
PNG rasterisé CLIENT (SVG → canvas → blob) déposé dans la Library via la
route d'import existante, tailles 1×/2×/4× ; « → bible » : l'export devient
`inspiration_images` d'une entité choisie (planches conditionnées ensuite par
la machinerie EXISTANTE) ; docs `lumiere` exportables en PNG à fond
transparent (superposition). **Preuve :** PNG visible dans la Library de
l'app réelle ; banc : l'export SVG d'un doc de référence est stable ; aucun
tir payant (le conditionnement de planche reste opt-in utilisateur).

## Phase 5 — Vitrail natif

Contrats : mode vitrail lisant la fiche épinglée via `GET /api/vector/vitrail`
(sert `familles.vitrail` de `style_vitrail.json` — palette ancres, bornes,
motifs) ; palette de l'éditeur pré-chargée (5 ancres + plomb `#1F1512`) ;
générateur paramétrique de baie (ogive ou rectangle, densité de réseau,
bordure aux fractions 5–15 %) produisant plombs (calque `contours`, strokes
épais) + fonds de verre (calque `verre`) prêts à diviser ; presets de motifs
(iris, rayons géométriques, halo) en groupes insérables. **Preuve :** un
vitrail complet créé dans l'app SANS générateur d'images ; au banc, une
mesure PIL de l'export PNG vérifie la part de pixels de contours dans
6–15 % de la toile (bornes déclarées de la fiche — même esprit que
mesure_style walkuski) ; la fiche reste l'unique source (pas de constantes
recopiées : le test rougit si l'endpoint et la fiche divergent).

## Phase 6 — Bibliothèque par chapitre

Contrats : bibliothèque globale (docs sans chapitre) + instanciation par
RÉFÉRENCE dans d'autres chapitres (table de liaison `chapter_id↔doc_id`,
l'édition du doc se voit partout, « dupliquer » pour diverger) ; filtre par
rôle ; vignettes (mini-export PNG au save) ; recherche par nom. **Preuve :**
scénario réel : 2 chapitres partagent un décor, l'édition se propage, la
duplication isole ; banc CRUD des liaisons.

---

## Ordre, dépendances, estimation

0 → 1 → 2 → 3 → 4 → 5 → 6 strictement (chaque phase livre un logiciel
utilisable et prouvé). Grossièrement : P0 une session ; P1 la plus lourde
(deux à trois sessions) ; P2–P6 une session chacune. Discipline transverse :
TDD RED d'abord partout, `run-tests.ps1` un processus par fichier, banc qa
node en UTF-8 forcé, commits fréquents en français sobre, déploiement au
patron sha+stop+relance+santé, ZÉRO dépense API (l'éditeur est local de bout
en bout).

## Hors périmètre (assumé)

Vectorisation de texte en chemins ; import SVG externe arbitraire (v2 —
l'import d'images bitmap en objets `image` suffit à décalquer) ; dégradés en
maille ; symboles à surcharges ; historique collaboratif. Rien de tout cela
ne bloque le flux vitrail → chapitres → planches.
