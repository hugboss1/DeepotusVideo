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
règles, raccourcis (V sélection, P plume, R rect, E ellipse, N nœuds,
Ctrl+Z/Y, Suppr, G grille).
**Preuve :** banc qa headless sur CHAQUE commande (le doc JSON après commande
== attendu, aller-retour compiler/parser stable octet à octet) ; scénario
navigateur : dessiner 3 objets sur 2 calques, sauver, rouvrir → JSON
identique ; undo ramène exactement l'état précédent (comparaison JSON).

> **RELEVÉ (27/08) : PHASE 1 LIVRÉE ET DÉPLOYÉE.** Six unités pures
> (chemins, objets, nœuds, calques, historique, aimant/guides) chacune à son
> cycle RED→GREEN — **69 contrôles qa node verts** — puis la couche gestes
> (T1.7) et la preuve (T1.8). Preuves app réelle sur un document jetable
> (créé puis archivé) : rect tracé par GESTES POINTER SYNTHÉTIQUES avec
> aimantation grille constatée (61→64, pas 8), cercle Maj exact, 3 objets
> sur 2 calques, **undo = état exact d'avant (JSON strict)**, refaire,
> sauver v2, **rouvrir = identique à l'octet** ; panneau calques et barre
> d'outils rendus. Périmètre assumé v1, noté : pas de drag individuel de
> poignée de Bézier en mode nœuds (déplacer/convertir/supprimer l'ancre,
> conformes au contrat) ; redimensionner un objet déjà tourné transforme la
> géométrie brute ; preview du déplacement par transform préfixé. Déploiement
> statique seul (backend intact, santé inchangée). Prochaine étape :
> phase 2 (apparence), sur ordre.

### Expansion d'exécution (27/08, après validation du plan)

Toutes les opérations sont PURES dans `mod-doc.js` (le modèle ET ses
mutations — la vérité reste un seul module testable sans DOM) ; l'UI
(`mod-tools.js`, `mod-layers.js`, `core.js`) ne fait que traduire des gestes
en commandes. Undo = pile de INSTANTANÉS du JSON (cap 100), classe pure
`Historique`. La rotation s'accumule dans `transform` (rotate a cx cy) ;
déplacement et redimensionnement réécrivent la GÉOMÉTRIE (les booléens de
phase 3 veulent des coordonnées vraies) — un redimensionnement sur objet
déjà tourné transforme la géométrie brute (limite assumée v1). Chemins :
`d` reste la vérité (M/L/C/Q/Z absolus, forme canonique) ; le parseur
structure, le sérialiseur canonise, l'aller-retour est stable à l'octet.
Guides persistés dans `doc.guides {v:[],h:[]}` (mutations = commandes,
donc annulables) ; `parserDoc` les accepte en option.

- [x] **T1.1 chemins** : `chemin_parser(d)` / `chemin_serialiser(segs)`
  M/L/C/Q/Z absolus, canonique, round-trip octet à octet — qa
  `chemin.test.mjs` RED d'abord
- [x] **T1.2 objets** : `op_ajouter(doc, calque, objet)` (id unique, calque
  actif, refus calque verrouillé), `op_supprimer(doc, ids)`,
  `op_deplacer(doc, ids, dx, dy)` (rect/ellipse/path C-Q compris),
  `op_redimensionner(doc, ids, bboxAvant, bboxApres)` (application affine
  exacte), `op_tourner(doc, ids, cx, cy, deg)` (compose transform) — qa
  `ops.test.mjs`
- [x] **T1.3 nœuds** : `op_noeud_deplacer(doc, id, iAncre, dx, dy)` (les
  poignées C attachées suivent), `op_noeud_convertir(doc, id, iAncre)`
  (angle↔courbe, poignées symétriques déduites des voisins),
  `op_noeud_supprimer`, `op_chemin_fermer` — qa `noeuds.test.mjs`
- [x] **T1.4 calques** : `op_calque_ajouter/renommer/reordonner/visible/
  verrou/supprimer` — qa `calques.test.mjs` ; panneau `mod-layers.js`
- [x] **T1.5 historique** : classe `Historique` (capturer/annuler/refaire,
  cap 100, refaire invalidé par une nouvelle commande) — qa
  `historique.test.mjs`
- [x] **T1.6 aimantation & guides** : `aimanter(v, {pas, guides}, tol)` ;
  `op_guide_ajouter/deplacer/supprimer` ; `parserDoc` accepte
  `doc.guides` — qa `aimant.test.mjs`
- [x] **T1.7 UI** : barre d'outils (V/P/R/E/N), overlay écran (poignées 8 +
  rotation, lasso, aperçu d'outil, ancres), règles + guides tirés à la
  souris, panneau calques, raccourcis, rendu sélection ; gestes → commandes
  via `executer()` du core (node --check + preuve navigateur)
- [x] **T1.8 io & preuve** : Sauver (PUT version bump, témoin modifié,
  Ctrl+S) ; scénario navigateur réel : 3 objets sur 2 calques → sauver →
  rouvrir → JSON identique ; undo = état exact ; déploiement (fichiers
  statiques seuls, backend intact) ; relevé au plan

## Phase 2 — Apparence

Contrats : fond/contour (couleur, épaisseur, pointillés, joints), dégradés
linéaires/radiaux (poignées sur canevas, stops éditables), opacité
objet/calque, groupes (grouper/dégrouper, transformations composées), ordre z
(avant/arrière), pipette. **Preuve :** snapshots SVG au banc (docs de
référence compilés → SVG attendu figé, diff exact) ; rendu réel vérifié.

> **RELEVÉ (27/08) : PHASE 2 LIVRÉE ET DÉPLOYÉE.** Quatre cycles RED→GREEN
> purs (style/opacités 11, dégradés 13, groupes/ordre/sommet 15, snapshot
> complet au diff exact + pureté — passé au premier jet, le littéral étant
> la spec) → **157 contrôles qa node cumulés** ; puis panneau Apparence,
> poignées de dégradé sur canevas, pipette, opacité par calque, sélection
> remontée au sommet. Preuves app réelles (doc jetable archivé) : contrôles
> du panneau dispatchés → style + dash rendus ; bouton dégradé → `<defs>` +
> `fill="url(#g1)"` + 2 poignées + stops UI ; **drag de poignée 240→400
> avec aimant à 144** ; grouper au panneau puis **saisir un ENFANT déplace
> le bloc entier (dx identiques, sélection restée sur le groupe)** ;
> dégrouper ; ordre z constaté ; **pipette : rb hérite `grad:g1` +
> pointillés** ; opacité calque 0.6 rendue, undo/redo exacts ; sauvé v2.
> Périmètre v1 assumé : dégradés sur le FOND (pas le contour), pas de
> point focal radial. Prochaine étape : phase 3 (booléens & texte), sur
> ordre.

### Expansion d'exécution (27/08, phase 1 livrée)

Décisions : les dégradés vivent dans `doc.degrades {id: {type: lineaire|
radial, stops:[{t, couleur, opacite?}], x1..y2 | cx,cy,r}}` en coordonnées
DOCUMENT (`userSpaceOnUse`) — c'est ce qui rend les poignées sur canevas
possibles ; un fond y réfère par `style.fond = "grad:<id>"`, la compilation
émet `<defs>` et retombe sur `none` si le dégradé manque (jamais de
document cassé). Le style des nouveaux objets devient un ÉTAT
(`etat.styleCourant`, nourri par le panneau et la pipette). Grouper déplace
les objets (ordre de peinture conservé) dans le calque de l'objet le plus
haut, en fin de calque ; dégrouper POUSSE le transform du groupe dans les
enfants (préfixe). La sélection au clic REMONTE AU SOMMET (`sommetDe`) :
cliquer un enfant sélectionne son groupe. `stroke-linejoin` reste `round`
par défaut (compat phase 1), `joint` le surcharge ; `pointilles` est la
chaîne dasharray. Pipette : adopte le style de l'objet cliqué et
l'applique à la sélection si elle existe.

- [x] **T2.1 style, joints, pointillés, opacités** : `op_style(doc, ids,
  patch)` (null retire la clé), `op_calque_opacite`, compilation
  dasharray/linejoin/opacity calque — qa `apparence.test.mjs` RED d'abord
- [x] **T2.2 dégradés** : `op_degrade_creer/modifier/stop_ajouter/
  stop_modifier/stop_supprimer (≥2 restants)/supprimer`, compilation
  `<defs>` triée par t, `url(#id)`, repli `none` — qa `degrades.test.mjs`
- [x] **T2.3 groupes & ordre z** : `op_grouper` (≥2 objets, hôte = calque du
  plus haut), `op_degrouper` (transform poussé aux enfants),
  `op_ordre(devant|derriere|avant|arriere)` par calque, `sommetDe(doc, id)`
  — qa `groupes.test.mjs`
- [x] **T2.4 snapshot complet figé** : un document de référence exerçant
  TOUT (dash+joint+opacités, dégradé linéaire et radial, groupe transformé,
  ordre) compilé → chaîne SVG attendue LITTÉRALE, diff exact — qa
  `snapshot.test.mjs`
- [x] **T2.5 UI** : panneau Apparence (`mod-style.js` : fond/contour/
  épaisseur/pointillés/joint/opacité, éditeur de stops, boutons dégradé
  linéaire/radial), poignées de dégradé sur canevas (drag →
  `op_degrade_modifier`), pipette (outil I), boutons grouper/dégrouper et
  ordre z, opacité par calque dans le panneau calques, sélection remontée
  au sommet, `styleCourant` — node --check
- [x] **T2.6 déploiement & preuve réelle** : statiques déployés, scénario
  navigateur (styles appliqués, dégradé rendu en `url(#…)`, groupe qui se
  déplace d'un bloc, ordre z constaté, pipette), relevé au plan

## Phase 3 — Booléens & texte

Contrats : union/soustraction/intersection/division sur 2+ objets
(aplatissement Bézier à tolérance 0,25 px, martinez, retraçage en paths) ; le
cas-métier « une plaque de verre DIVISÉE par le réseau de plombs devient des
fragments indépendants » est un preset une-action ; texte SVG (fonte, corps,
graisse, interlettrage) posé et transformable. **Preuve :** banc qa des
booléens sur cas de référence (aires attendues à ±0,5 %, compte de fragments
exact sur la division) ; licence martinez jointe et créditée.

> **RELEVÉ (27/08) : PHASE 3 LIVRÉE ET DÉPLOYÉE.** Martinez 0.7.4 vendorisé
> (58,6 Ko UMD, licence MIT jointe, `package.json` commonjs local, fumée
> node exacte 15000/5000/5000) ; aplatissement à matrices composées et
> subdivision 0,25 px (plancher 64 sur l'ellipse — le polygone inscrit
> sous-estimait l'aire de 0,54 %, le banc l'a attrapé) ; ops booléennes au
> plus bas + division-métier à contours GONFLÉS ; texte SVG complet.
> **43 contrôles qa neufs (189 cumulés)** — dont un VRAI défaut attrapé :
> martinez ne garantit pas l'opposition d'orientation des trous, `_dDePoly`
> la force (sinon rendu nonzero plein et aires additionnées). Preuves app
> réelles (doc jetable archivé) : **plaque + croix de deux plombs TRACÉS →
> bouton ⧉ → 4 fragments EXACTEMENT**, plombs intacts, style doré copié,
> 4 paths rendus ; **undo de la division = état exact**, refaire ; texte
> posé à l'outil (« Vitrail Młoda Polska » rendu), corps 36 + bold
> appliqués au panneau et constatés dans le DOM ; sauvé v2. Périmètre v1
> assumé : `rx` des rects arrondis ignoré à l'aplatissement ; un texte
> dans une sélection booléenne est refusé avec message (vectorisation hors
> périmètre, conforme au plan). Prochaine étape : phase 4 (exports &
> intégrations), sur ordre.

### Expansion d'exécution (27/08, phase 2 livrée)

Décisions : martinez vendorisé en UMD sous `vendor/` avec un `package.json
{type: commonjs}` local (node le `require`, le navigateur le charge en
script classique avant les modules → `window.martinez`) ; le wrapper
`mod-bool.js` reçoit la lib par résolveur (`fournirMartinez()` au banc,
`window.martinez` à l'écran). L'aplatissement APPLIQUE le transform de
l'objet (suites de `rotate` composées en matrice — les seules que nos ops
émettent). Un découpeur à fond `none` compte par son CONTOUR GONFLÉ
(union de quadrilatères par segment + disques aux sommets, joints/bouts
ronds comme notre rendu) — c'est ce qui permet au réseau de plombs TRACÉ à
la plume de découper la plaque. La division garde les plombs et remplace
la plaque par ses fragments (un objet par polygone, trous en sous-chemins,
style de la plaque). Sémantique : union = tous ; intersection = pli de
tous ; soustraction = le plus BAS moins l'union des autres ; le résultat
remplace les opérandes à l'emplacement du plus bas, son style conservé.
Le texte porte fonte/corps/graisse/interlettrage DANS `style` (op_style
marche gratuitement) ; le redimensionnement met le corps à l'échelle ; la
vectorisation des glyphes reste hors périmètre (un texte dans une
sélection booléenne est refusé avec message).

- [x] **T3.1 vendor** : martinez UMD épinglé + LICENCE jointe +
  `package.json` commonjs local + résolveur `mod-bool.js` — fumée qa
  (union 2 carrés, require node)
- [x] **T3.2 aplatir** : `aplatir_objet(objet, tol=0.25)` → anneaux
  (rect exact, ellipse adaptative, path M/L/C/Q/Z par subdivision,
  sous-chemins multiples, transform appliqué) + `aire_de(anneaux)` — qa
  `booleens.test.mjs` : aires ±0,5 % (ellipse, cercle en 4 cubiques),
  rotation à aire conservée
- [x] **T3.3 union/soustraction/intersection** : `op_booleen(doc, ids,
  mode)` — remplace au plus bas, style conservé, aires exactes sur rects
  (15000/5000/5000), refus <2 objets et texte
- [x] **T3.4 division** : `op_division(doc, ids)` — plaque = le plus bas,
  découpeurs = fonds pleins OU contours gonflés, fragments indépendants
  (compte EXACT : bande verticale → 2 ; découpeur intérieur → 1 avec trou
  en sous-chemin), plombs conservés
- [x] **T3.5 texte** : compilation `<text>` échappée (police, corps,
  graisse, interlettrage depuis style), déplacement/redimensionnement
  (corps à l'échelle), snapshot étendu — qa `texte.test.mjs`
- [x] **T3.6 UI** : outil Texte (T, clic → invite), section Fonte du
  panneau (sélection texte), rangée Booléens (∪ ⊖ ∩ ⧉ — ⧉ EST le preset
  métier « diviser le verre par les plombs »), raccourcis — node --check
- [x] **T3.7 déploiement & preuve réelle** : plaque + plombs à la plume →
  division dans l'app réelle (fragments comptés, plombs intacts), texte
  posé/stylé, relevé au plan

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

> **RELEVÉ (27/08) : PHASE 4 LIVRÉE ET DÉPLOYÉE.** Tranché : le client
> compile, le serveur stocke atomique et sert (`POST …/export` + `GET
> export.svg` — RED pytest puis GREEN, banc vector 6 tests) ; menu Exporter
> (SVG, PNG 1×/2×/4× rasterisés canvas → `POST /images/upload` existant,
> fond transparent coché d'office en rôle lumière, → Bible). Preuves app
> réelles sur la « Baie vitrail - demo » : SVG stocké et servi en
> image/svg+xml (l'ogive dedans) ; **PNG 1× (640×960) et 2× (1280×1920)
> VISIBLES dans la Library réelle** ; **PNG transparent à alpha 0 constaté
> au pixel**, l'opaque au coin exactement #F8F4E3 ; **liaison Bible par le
> vrai flux du menu** (export 2× ajouté aux `inspiration_images` d'une
> entité de test, retirée ensuite) — **aucun tir payant**. La preuve a
> attrapé un défaut réel : l'export transparent écrasait l'opaque (même
> nom) → suffixe `_t`. Staleness du GET documentée (sert le dernier
> export). Prochaine étape : phase 5 (vitrail natif), sur ordre.

### Expansion d'exécution (27/08, phase 3 livrée)

TRANCHÉ (le point laissé ouvert) : **le client compile, le serveur stocke
et sert**. Un port Python du compilateur créerait un DEUXIÈME compilateur à
maintenir en parité ; le compilateur JS est unique, verrouillé par le
snapshot qa au diff exact — la « preuve de parité » n'a plus d'objet. Le
`GET export.svg` sert donc le DERNIER SVG poussé (`POST …/export {svg}`,
écrit atomiquement `<id>.svg` à côté du JSON), avec un 404 parlant tant que
rien n'a été exporté ; l'UI ré-exporte à chaque demande, la staleness est
documentée. Le PNG se rasterise au client (SVG → Image → canvas ×k → blob)
et part par `POST /images/upload` EXISTANT (nom `vector_<id>_<k>x.png`) —
il apparaît dans la Library comme tout PNG du dossier. « → Bible » :
l'export 2× est ajouté à `inspiration_images` de l'entité choisie par le
`PUT /bible/entities/{id}` EXISTANT — le conditionnement de planche reste
l'affaire de la machinerie en place (opt-in payant de l'utilisateur,
aucun tir ici). Fond transparent : compilation d'un clone sans `fond`
(case cochée d'office pour un rôle `lumiere`).

- [x] **T4.1 backend** : `POST /api/vector/docs/{id}/export` {svg} (400 si
  pas un `<svg`, 404 id inconnu, écrit `<id>.svg` atomique) et
  `GET /api/vector/docs/{id}/export.svg` (sert image/svg+xml, 404 parlant
  avant tout export, le ré-export remplace) — RED pytest d'abord
- [x] **T4.2 client** : `mod-export.js` — menu Exporter (SVG serveur +
  téléchargement, PNG 1×/2×/4× → Library, case fond transparent), la
  rasterisation canvas — node --check
- [x] **T4.3 → bible** : dialogue de liaison (liste des entités, ajout de
  l'export 2× aux `inspiration_images`) — node --check
- [x] **T4.4 déploiement & preuve réelle** : SVG stocké/servi vérifié,
  **PNG visibles dans la Library réelle** (1× et 2×, dimensions
  doublées), PNG lumière à pixel alpha VÉRIFIÉ, liaison bible constatée
  sur une entité de test créée puis retirée, relevé au plan

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

### Expansion d'exécution (27/08, phase 4 livrée)

Décisions : la mesure de couverture des plombs se fait DEUX fois — au banc
qa node en ANALYTIQUE (union martinez des contours GONFLÉS de la baie
générée / aire de la toile, bornes lues DANS la fiche épinglée par le
test — zéro constante recopiée), et en PIL AU PIXEL sur l'export PNG réel
(pixels proches du plomb / total, pendant la preuve T5.5 — le banc backend
n'a pas de rasterizer SVG et ne lira pas le dossier images de
l'utilisateur). Le générateur est PUR (`generer_baie(famille, params)` →
objets sans id) ; l'insertion est UNE commande composée (calques `verre`
sous `contours` créés au besoin par NOM, `op_ajouter` en série). Réseau de
meneaux/traverses sous la naissance de l'ogive ; tympan = un panneau ;
bordure = contour intérieur en retrait de `bordure×min(W,H)`, fraction
CLAMPÉE aux bornes de la fiche ; les verres cyclent sur les 5 ancres ; les
contours sont des tracés `fond:none` — donc DIVISIBLES par le ⧉ existant.

- [ ] **T5.1 endpoint fiche** : `GET /api/vector/vitrail` sert
  `familles.vitrail` de la copie épinglée — le pytest compare à l'octet
  avec le fichier (divergence → rouge) — RED d'abord
- [ ] **T5.2 générateur + motifs** : `generer_baie` (ogive/rectangle,
  colonnes×rangées, bordure clampée, comptes exacts, ancres cyclées,
  plomb de la fiche), `motif_iris`/`motif_rayons`/`motif_halo` (groupes,
  palette de la fiche) — qa `vitrail.test.mjs` RED d'abord
- [ ] **T5.3 couverture analytique** : part des contours gonflés de la
  baie par défaut ∈ bornes `part_contours_plomb` LUES dans la fiche
  (export `contour_en_multi` de mod-bool) — même banc
- [ ] **T5.4 UI** : panneau Vitrail (palette 5 ancres + plomb cliquables,
  bouton Baie… avec invite de paramètres, boutons Iris/Rayons/Halo),
  nourri par l'endpoint (caché si indisponible) — node --check
- [ ] **T5.5 déploiement & preuve réelle** : un vitrail complet créé DANS
  l'app (baie générée + motifs + couleurs à la palette), export PNG →
  Library, **mesure PIL au pixel dans les bornes de la fiche**, zéro
  générateur d'images, relevé au plan

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
