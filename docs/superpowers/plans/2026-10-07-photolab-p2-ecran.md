# Photolab P2 — l'écran dans la barre des applications — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** un écran « Photolab » ouvert depuis la barre des applications de Deepotus, comme le Vectorlab, qui pilote le moteur photocraft (P1, `/api/photolab`) : documents (nouveau, ouvrir depuis la Bibliothèque, enregistrer), canevas (zoom, main), menus générés depuis le catalogue de photocraft, panneaux Calques / Propriétés / Couleur / Historique / Navigateur, outils Déplacement, sélections (rectangle, ellipse, lasso, lasso polygonal, baguette, sélection rapide), Recadrage, Pipette, Main, Zoom. Bilingue (`dzT`).

**Architecture :** page statique `frontend/photolab/` montée par le backend comme `/vectorlab/`, ouverte dans une iframe par une entrée de la barre (patcher de queue `scripts/patch_bundle_photolab.py`, modèle `patch_bundle_assets2d.py` de t125). Modules ES `js/mod-*.js` initialisés par `js/core.js` autour d'un objet `PL` (modèle `VL` du Vectorlab). Toute logique calculable est une fonction PURE exportée, bancable sous node (`frontend/photolab/qa/*.test.mjs`, modèle `frontend/vectorlab/qa/`). L'écran n'invente aucun pixel : chaque geste validé = une commande moteur (`/api/photolab/executer`), puis un rendu complet (`/api/photolab/rendu`) — décision D1, latence mesurée 148-163 ms.

**Spec :** `docs/superpowers/specs/2026-10-07-photolab-design.md` (D2 disposition et icônes de photocraft + tokens Deepotus, D3 menus générés, D4 gestes repris, D5 fichiers, D6 bilingue, D8 marques) ; inventaire `2026-10-07-photocraft-inventaire.md` (A1 cotes, B §1 menus, B §2 outils, B §3 panneaux, B §8 gestes) ; relevé des commandes moteur ci-dessous.

**Tech :** HTML/CSS/JS sans framework (ES modules), FastAPI, Python 3.13 embarqué, node pour les bancs JS.

---

## Faits établis (relevés le 07/10/2026)

**Moteur (vérifiés en direct sur `photocraft-cli serve` 0.3.0)** — chaque ligne est `id {paramètres} → résultat` :
- Calques : `layer.new.layer {name?}→{layer}` · `layer.delete {layer?}` · `layer.duplicate {layer?}→{layer}` · `layer.select {layer, mode: replace|toggle|range|add}→{selected:[ids]}` · `layer.renameLayer {layer?, name}` · `layer.setProps {layer?, name?, visible?, opacity 0..1?, fill 0..1?, blend?, locks:{transparency,pixels,position,artboard,all}?}` · `layer.moveTo {layer?, target, position: above|below|into}` · `layer.groupLayers {name?}→{layer}` · `layer.mergeDown {layer?}` · `layer.new.layerFromBackground {}→{layer}` · `layer.new.layerViaCopy {}` · `layer.translate {layer?, dx, dy}` · `layer.pickAt {x, y, target: layer|group, select: true, list?}→{layer}|{layers:[{layer,name}]}`.
- Sélections : `select.all|deselect|inverse|reselect {}` · `select.rect {x, y, width, height, mode: replace|add|subtract|intersect, ellipse: bool, antiAlias, feather}` · `select.lasso {points:[[x,y]…], mode, antiAlias, feather}` · `select.magicWand {x, y, tolerance 0..255=32, contiguous=true, antiAlias, sampleAllLayers=false, mode}` · `select.quick {points, size=30, mode, sampleAllLayers, enhanceEdge}`.
- Déplacer le contenu d'une sélection : `edit.transform {matrix:[1,0,0,1,dx,dy]}` (sélection active) ; sans sélection : `layer.translate`.
- Recadrage : `image.crop {x, y, width, height, deleteCroppedPixels=true}` ; `image.crop {}` = à la sélection.
- Couleurs : `document.pixel {x, y}→[r,g,b,a]` (flottants du composite) · `tools.setColors {foreground?, background?: "#rrggbb"}` · `tools.swapColors {}` · `tools.defaultColors {}` ; relecture par la méthode `session.list` (`foreground`, `background` en RGBA flottant).
- Historique : `edit.undo {}`, `edit.redo {}` ; `doc.inspect.history` = noms des états APPLIQUÉS (les annulés disparaissent ; `canRedo`) ; aucun saut direct → N × `edit.undo` dans un `batch`.
- `doc.inspect` : `activeLayer, selectedLayers, canUndo, canRedo, history, revision, width, height, depth, mode, resolution, name, hasSelection, selectionBounds [x,y,w,h]|null, layers[]` (arbre, haut → bas : `{id, name, kind, visible, opacity, fill, blend, clipped, hasMask, bounds [x,y,w,h], selected, linkGroup}`, groupes : `children`, `expanded`). **Les verrous ne sont PAS relisibles** → l'écran garde leur état.
- `doc.render {maxSide = 1024 ; 0 = taille réelle ; 2048 max}` ; aucun rendu par région ni par calque.
- Vignettes de calque : `image.duplicate {name}→{document}` (copie, active), puis `layer.setProps {visible:false}` sur les autres calques, `doc.render`, `doc.close` — dans le SERVICE (méthodes `doc.select`/`doc.close` non exposées à l'écran).
- Paramètres inconnus : ignorés en silence par le moteur → l'écran n'envoie que des paramètres listés ici.

**Deepotus :**
- Montage d'un lab statique : `backend/app/main.py:460-487` (classe `_VectorlabStatic`, `Cache-Control: no-cache, must-revalidate`, redirection sans barre).
- Barre : patcher de queue en OCTETS sur `frontend/dist/assets/index-BEOJX8L5.js` (modèle `scripts/patch_bundle_assets2d.py`, t125) : icône avant `gamegrid:r.jsxs("g",{fill:"currentColor",children:[`, entrée de rail avant `{id:"settings",label:"Settings",icon:"cog",desc:"Keys, paths, persona"}`, vue iframe après `s==="vectorlab"&&r.jsx("iframe",{src:"/vectorlab/",…},"pvlab"),`, liste des vues navigables `Yu=[…,"settings","vectorlab"]` (ajouter `"photolab"`). Banc de rejeu octet pour octet (modèle `backend/tests/test_assets2d_lanceur.py`). Compteurs figés : `x.useState(` = 731, `DzTracks` = 181. `test_assets2d_lanceur.py:96-97` épingle `"news","library","settings","vectorlab"],sg=Yu.includes(` → à faire suivre.
- Icônes du rail : carte `Sh` du bundle, glyphe 24 × 24 en `currentColor` (DESIGN.md §15-2) ; teinte de catégorie `--cat-*` dans `frontend/shared/deepotus.tokens.css`, `frontend/dist/shared/deepotus.tokens.css`, `frontend/dist/theme-v2.css`.
- Bibliothèque : ouvrir = `parent.__dzLibPicker({titre}, cb(nom))` puis `fetch("/api/images/"+nom)` ; la provenance d'un dépôt vient du PRÉFIXE du nom (`routes.py:3665-3674` : `vector_` → `noter([...],"vectorlab")`) ; libellés `library_index.SOURCES` (`backend/app/services/library_index.py:25-44`), `_PREFIXES` (l.49-60), `SOURCES_PROPRES` (l.68).
- Pages qui chargent `/shared/dz-i18n*.js` et `/shared/dz-plafonds.js` : listes `PAGES` de `test_i18n_l0.py:35-37` et `test_p2_plafonds_ecran.py:26-28` → ajouter `frontend/photolab/index.html`.
- Icônes de photocraft : SVG Lucide (ISC) dans `assets/icons/` des sources v0.3.0 (extraites : `<scratchpad>/t136src/x/storytold-photocraft-60224d3/assets/icons/`), licence `assets/icons/LICENSE-lucide.txt`.

## Conventions (rappel)
Bancs Python : scripts `__main__`, `check()`, `=== N passed, M failed ===`, Python embarqué, depuis `backend/`. Bancs JS : `frontend/photolab/qa/*.test.mjs` + `qa/run.mjs` (copier le lanceur du Vectorlab), `node qa/run.mjs` depuis `frontend/photolab/`. Write/Edit pour tout fichier à `\n`/`\` (jamais de heredoc). Ne jamais lancer `tests/mutations_*.py`. `python scripts/restaurer_bak_montage.py` avant les bancs du bundle. Bundle lu/écrit en OCTETS. Pas de commit sans « commit et ouvre la PR ».

## Fichiers

| Fichier | Rôle |
|---|---|
| `backend/app/api/photolab_routes.py` (modifié) | + `GET /session`, `POST /historique {annuler:n}|{retablir:n}`, `GET /vignettes?maxSide=`, `POST /bibliotheque {format}` |
| `backend/app/services/photolab_moteur.py` (modifié) | + `vignettes(session, maxSide)` (copie de document, un rendu par calque) |
| `backend/app/api/routes.py` (modifié) | préfixe `photolab_` → `LI.noter(...,"photolab")` à l'upload |
| `backend/app/services/library_index.py` (modifié) | `SOURCES["photolab"]="Photolab"`, préfixe, `SOURCES_PROPRES` |
| `backend/app/main.py` (modifié) | montage statique `/photolab/` |
| `backend/tests/test_photolab_ecran_api.py` (créé) | bancs des routes ajoutées (faux moteur + vrai moteur pour les vignettes) |
| `frontend/photolab/index.html`, `photolab.css` (créés) | la page et ses zones |
| `frontend/photolab/js/core.js` (créé) | `PL`, cycle inspect → rendu, raccourcis |
| `frontend/photolab/js/mod-api.js` | appels `/api/photolab/*`, génération, erreurs |
| `frontend/photolab/js/mod-vue.js` | canevas : zoom, main, conversions écran ↔ document, taille de rendu |
| `frontend/photolab/js/mod-menus.js` | menus générés depuis `donnees/menus.json` + registre |
| `frontend/photolab/js/mod-outils.js` | barre d'outils (20 emplacements, flyouts), lettres, barre d'options |
| `frontend/photolab/js/mod-selection.js` | gestes des sélections → commandes |
| `frontend/photolab/js/mod-deplacer.js`, `mod-recadrer.js`, `mod-pipette.js` | outils |
| `frontend/photolab/js/mod-calques.js`, `mod-proprietes.js`, `mod-couleur.js`, `mod-historique.js`, `mod-navigateur.js` | panneaux |
| `frontend/photolab/js/mod-fichier.js` | Nouveau / Ouvrir (Bibliothèque) / Enregistrer |
| `frontend/photolab/icones/*.svg` + `LICENSE-lucide.txt` + `ATTRIBUTION.md` | icônes de photocraft |
| `frontend/photolab/qa/run.mjs`, `qa/*.test.mjs`, `package.json` | bancs JS purs |
| `frontend/shared/i18n/photolab.json` (+ réassemblage) | textes de l'écran FR/EN |
| `scripts/patch_bundle_photolab.py` (créé) | maillon de queue : icône, rail, iframe, vue navigable |
| `frontend/dist/assets/index-BEOJX8L5.js` (modifié par le patcher, commis) | |
| `frontend/shared/deepotus.tokens.css`, `frontend/dist/shared/deepotus.tokens.css`, `frontend/dist/theme-v2.css` | `--cat-photo` |
| `backend/tests/test_photolab_lanceur.py` (créé) | rejeu du patcher octet pour octet + composant sous node |
| `backend/tests/test_i18n_l0.py`, `test_p2_plafonds_ecran.py`, `test_assets2d_lanceur.py` (modifiés) | page ajoutée aux listes ; épingle `Yu` suivie |

---

## Phase A — backend de l'écran

### Task A1 : routes `session`, `historique`, `vignettes`, `bibliotheque`

**Files :** Modify `backend/app/api/photolab_routes.py`, `backend/app/services/photolab_moteur.py`, `backend/app/api/routes.py`, `backend/app/services/library_index.py` ; Test `backend/tests/test_photolab_ecran_api.py`.

Contrat (à tester d'abord, faux moteur `tests/faux_photocraft.py` étendu des méthodes `session.list`, `batch`, `image.duplicate`, `doc.select`, `doc.close`, `layer.setProps` ; plus une section VRAI moteur pour les vignettes, rouge si le binaire manque) :
1. `GET /api/photolab/session` → résultat de la méthode `session.list` + en-tête de génération. Le banc vérifie `{"active", "documents", "foreground", "background"}`.
2. `POST /api/photolab/historique {"annuler": n}` ou `{"retablir": n}` (1 ≤ n ≤ 100, entier ; les deux à la fois → 400) → UNE requête `batch {"steps":[{"command":"edit.undo"}…], "stopOnError": true}` ; rend `doc.inspect` après. Banc : 3 annulations = 1 batch de 3 étapes (le faux moteur compte), n=0 → 400, n=101 → 400.
3. `GET /api/photolab/vignettes?maxSide=48` (16 ≤ maxSide ≤ 256) → `{"vignettes": {"<id>": "/api/photolab/rendus/vig-<gen>-<id>-<rev>.png", …}}`. Service `photolab_moteur.vignettes(s, max_side)` sous le verrou de la session (UNE séquence `appeler_g` par étape, jamais d'appel concurrent) : `doc.inspect` (lit `revision`, `layers` à plat, index actif via `session.list`), `image.duplicate {name:"dz-vignettes"}`, pour chaque calque pixel/texte/forme : `layer.setProps {visible:true}` sur lui, `{visible:false}` sur les autres, `doc.render {maxSide, path:"rendus/vig-…png"}` ; puis `doc.close` de la copie et `doc.select` de l'original (index relu dans `session.list`) — dans un `try/finally` qui referme la copie quoi qu'il arrive. Cache par `(génération, revision)` : une deuxième demande à la même révision ne relance rien (banc : le faux moteur compte zéro `image.duplicate` la seconde fois). Les anciennes vignettes `vig-*` d'une autre révision sont supprimées. Banc VRAI moteur : document 64×32 blanc + un calque rempli `#ff0000` → la vignette du calque rouge a un pixel central rouge, celle du fond est blanche, et `doc.inspect` après l'appel montre le MÊME document actif, inchangé (même `revision`, même nombre de calques, tous `visible` comme avant).
4. `POST /api/photolab/bibliotheque {"format": "png"|"jpg", "quality"?}` → `doc.save` en `exports/` puis copie dans `settings.images_path` sous `photolab_<horodatage>_<base>.<ext>` et `LI.noter([nom], "photolab")` ; rend `{"filename": nom}`. Dans `routes.py` (dépôt `/images/upload`), le préfixe `photolab_` est reconnu comme `vector_` (→ source `photolab`), et `library_index.SOURCES["photolab"] = "Photolab"`, `_PREFIXES` gagne `("photolab_", "photolab")`, `SOURCES_PROPRES` gagne `"photolab"`. Banc : le fichier existe dans le dossier images, `GET /api/images` le liste avec `source == "photolab"`.

- [ ] Step 1 : écrire `backend/tests/test_photolab_ecran_api.py` (les 4 contrats ci-dessus, faux moteur + section vrai moteur pour 3) — rouge (404).
- [ ] Step 2 : étendre `tests/faux_photocraft.py` (méthodes listées, compteur d'appels exposé par une commande `dz.compte`).
- [ ] Step 3 : implémenter ; vert. Relancer `test_photolab_moteur.py`, `test_photolab_routes.py`, `test_photolab_fidelite.py` (doivent rester verts).

### Task A2 : montage statique `/photolab/`

**Files :** Modify `backend/app/main.py` (copie du bloc Vectorlab, `name="photolab"`, redirection `/photolab` → `/photolab/`, `Cache-Control: no-cache, must-revalidate`) ; Test : ajouter au banc A1 : `GET /photolab/` → 200 text/html contenant `<title>Photolab`, `GET /photolab` → 307 vers `/photolab/`, en-tête `cache-control` présent.

- [ ] Step 1 : test rouge ; Step 2 : bloc de montage (après celui du Vectorlab) ; Step 3 : vert.

---

## Phase B — la page, le canevas, les menus (pas encore d'outils)

Chaque module expose `export function init<Nom>(PL)` et ses fonctions PURES exportées ; `core.js` les initialise dans l'ordre : api, vue, menus, outils, panneaux, fichier.

### Task B1 : squelette, zones, design

**Files :** Create `frontend/photolab/index.html`, `photolab.css`, `js/core.js`, `js/mod-api.js`, `qa/run.mjs` (copie de `frontend/vectorlab/qa/run.mjs`), `qa/package.json` ou `package.json` (`"type":"module"`), `qa/zones.test.mjs`, `ATTRIBUTION.md`, `icones/` + `icones/LICENSE-lucide.txt`.

Exigences :
- `<html lang="fr">`, `<title>Photolab</title>` ; dans `<head>` AVANT tout autre script : `<script src="/shared/dz-i18n-dico.js"></script>` puis `<script src="/shared/dz-i18n.js"></script>` ; puis `<script src="/shared/dz-plafonds.js"></script>` et `<script src="/shared/dialogue.js"></script>` ; `js/core.js` en `type="module"` en fin de `<body>`.
- `photolab.css` : `@import url("/shared/deepotus.tokens.css");` ; `:root{--cat:var(--cat-photo)}` ; AUCUNE couleur en dur hors des jetons (`--bg-base`, `--bg-panel`, `--bg-panel-2`, `--ink*`, `--stroke*`, `--accent*`), polices `--f-ui`/`--f-mono`.
- Zones (ids fixes, cotes de photocraft A1, en px) : `#menubar` hauteur 32 · `#options` 36 · `#onglets` 26 · `#outils` largeur 68 (deux colonnes de 32, gouttière 4) · `#scene` (contient `canvas#toile` + `#fourmis` overlay SVG + règles absentes en P2) · `#rail` largeur 34 (5 boutons : réglages, navigateur, couleur, calques, historique) · `#panneaux` largeur 278 (trois `<section>` empilées : `#grpCouleur` [Couleur], `#grpProprietes` [Propriétés], `#grpCalques` [Calques, Historique, Navigateur en onglets]) · `#statut` hauteur 24 (zoom, « RGB · 8 bits », « 1920 × 1080 px », nombre de calques, message).
- Écran d'accueil sans document (`#accueil`, centré) : titre « Photolab », phrase « Crée un document ou ouvre une image. », boutons « Nouveau… Ctrl+N » (plein, accent), « Ouvrir depuis la Bibliothèque… Ctrl+O » (contour), « Dépose une image ici pour l'ouvrir. » — AUCUN lien ArtCraft/Discord (D8).
- Icônes : copier depuis les sources v0.3.0 (`<scratchpad>/t136src/x/storytold-photocraft-60224d3/assets/icons/`) les SVG utilisés par les outils et panneaux de P2 (liste dans B3), + `LICENSE-lucide.txt` ; `ATTRIBUTION.md` dit : icônes Lucide (ISC) via photocraft 0.3.0 (MIT OU Apache-2.0), catalogue des menus et libellés FR de photocraft. Les SVG sont insérés en ligne (fetch puis `innerHTML`) pour que `stroke="currentColor"` prenne nos jetons.
- `mod-api.js` : `api(methode, chemin, corps?)` → JSON ; mémorise l'en-tête `X-Photolab-Generation` ; si la génération CHANGE alors qu'un document était ouvert → `PL.signaler(dzT("photolab.moteur.relance"))` et retour à l'accueil (documents perdus) ; traduit 409 en « Moteur occupé… » (retenter une fois après 300 ms), 503 en message d'installation, 504/422 en toast avec le message.
- `qa/zones.test.mjs` : lit `index.html` et `photolab.css` (readFileSync) et vérifie : ordre des scripts (dico puis runtime avant tout script), présence des ids de zones, `@import` des jetons, aucune couleur hex/rgb en dur dans `photolab.css` hors `var(--…)`, aucune chaîne « ArtCraft », « Discord », « Photoshop ».

- [ ] Step 1 : `qa/zones.test.mjs` rouge ; Step 2 : fichiers ; Step 3 : `node qa/run.mjs` vert ; Step 4 : ajouter `frontend/photolab/index.html` aux listes `PAGES` de `backend/tests/test_i18n_l0.py` et `backend/tests/test_p2_plafonds_ecran.py`, relancer ces deux bancs (verts).

### Task B2 : le canevas — vue, zoom, main, taille de rendu

**Files :** Create `frontend/photolab/js/mod-vue.js`, `qa/vue.test.mjs`.

Fonctions PURES (code complet à écrire et tester d'abord) :

```js
// Zoom par paliers de photocraft (canvas.rs:353-358, inventaire B §8) : 1 % … 6400 %.
export const PALIERS = [0.01,0.02,0.03,0.04,0.05,0.0625,0.0833,0.125,0.1667,0.25,0.3333,0.5,0.6667,1,2,3,4,5,6,7,8,12,16,32,64];
export function palier(z, sens) { /* sens +1 : premier palier > z ; -1 : dernier < z ; borné aux extrêmes */ }
export function ajuster(doc, vue, marge = 16) { /* zoom qui fait tenir doc {w,h} dans vue {w,h} moins la marge, borné 0.01..64 */ }
export function versDoc(v, x, y) { /* écran -> document : ((x - v.ox) / v.z, (y - v.oy) / v.z) */ }
export function versEcran(v, x, y) { /* document -> écran */ }
export function zoomAutour(v, z2, px, py) { /* nouveau v {z, ox, oy} qui garde le point écran (px,py) fixe */ }
export function tailleRendu(doc, z, dpr = 1) { /* maxSide à demander : ceil(max(w,h) * z * dpr) borné [64, 2048] et <= max(w,h) ;
   0 (taille réelle) si max(w,h) <= 4096 et le besoin dépasse 2048 ; sinon 2048 (flou assumé au très fort zoom, dit dans le statut) */ }
```

Comportements (dans `initVue(PL)`) : rendu `img` du dernier `/rendu` dessiné dans `canvas#toile` à `v.z` avec `imageSmoothingEnabled = z < 1` ; fond damier sous la transparence ; Ctrl+molette ou pincement = zoom autour du pointeur (`zoomAutour`), Alt+molette = ×1,05 par cran, molette = panoramique (Maj = horizontal) ; Espace tenu = main temporaire (outil courant rendu au relâchement) ; bouton du milieu = main ; Ctrl+0 = ajuster, Ctrl+1 = 100 %, Ctrl+= / Ctrl+- = palier suivant/précédent ; quand `tailleRendu` change de plus de 25 % au zoom, redemander un rendu (débounce 150 ms). Statut : zoom en %.

`qa/vue.test.mjs` : paliers (palier(1,+1)=2, palier(1,-1)=0.6667, bornes), ajuster (1920×1080 dans 1000×600 → 0.5389 à 1e-3 près avec marge 16), aller-retour versDoc/versEcran, zoomAutour garde le point fixe (à 1e-9), tailleRendu (doc 1920×1080 : z 0.5 → 960 ; z 1 dpr 1 → 1920 ; z 2 → 0 ; doc 6000×4000 z 1 → 2048).

- [ ] Step 1 : test rouge ; Step 2 : implémenter ; Step 3 : vert.

### Task B3 : barre d'outils, flyouts, lettres, barre d'options

**Files :** Create `frontend/photolab/js/mod-outils.js`, `qa/outils.test.mjs`.

Données PURES exportées (inventaire B §2, ordre de `Tool::ALL`) :

```js
// 20 emplacements en 5 sections ; chaque outil : {id, lettre, icone (fichier de icones/), actif:P2?}
export const EMPLACEMENTS = [
  // section 1
  [{id:"move", lettre:"V", icone:"move", p2:true}],
  [{id:"rectMarquee", lettre:"M", icone:"rectangle-horizontal", p2:true}, {id:"ellipseMarquee", lettre:"M", icone:"circle", p2:true}],
  [{id:"lasso", lettre:"L", icone:"lasso", p2:true}, {id:"polygonLasso", lettre:"L", icone:"pentagon", p2:true}],
  [{id:"magicWand", lettre:"W", icone:"wand", p2:true}, {id:"quickSelection", lettre:"W", icone:"lasso-select", p2:true}, {id:"objectSelection", lettre:"W", icone:"scan", p2:false}],
  [{id:"crop", lettre:"C", icone:"crop", p2:true}, {id:"slice", lettre:"C", icone:"scissors", p2:false}, {id:"sliceSelect", lettre:"C", icone:"mouse-pointer-2", p2:false}],
  [{id:"eyedropper", lettre:"I", icone:"pipette", p2:true}, {id:"ruler", lettre:"I", icone:"ruler", p2:false}, {id:"note", lettre:"I", icone:"message-square", p2:false}, {id:"count", lettre:"I", icone:"hash", p2:false}],
  // section 2 (peinture et retouche : P3b)
  [{id:"spotHealing", lettre:"J", icone:"bandage", p2:false}, {id:"healing", lettre:"J", icone:"bandage", p2:false}, {id:"patch", lettre:"J", icone:"bandage", p2:false}],
  [{id:"brush", lettre:"B", icone:"brush", p2:false}, {id:"pencil", lettre:"B", icone:"pencil", p2:false}, {id:"mixerBrush", lettre:"B", icone:"brush", p2:false}],
  [{id:"cloneStamp", lettre:"S", icone:"stamp", p2:false}],
  [{id:"historyBrush", lettre:"Y", icone:"history", p2:false}],
  [{id:"eraser", lettre:"E", icone:"eraser", p2:false}, {id:"backgroundEraser", lettre:"E", icone:"eraser-background", p2:false}, {id:"magicEraser", lettre:"E", icone:"eraser-magic", p2:false}],
  [{id:"gradient", lettre:"G", icone:"blend", p2:false}, {id:"paintBucket", lettre:"G", icone:"paint-bucket", p2:false}],
  [{id:"blur", lettre:"", icone:"droplet", p2:false}, {id:"sharpen", lettre:"", icone:"triangle", p2:false}, {id:"smudge", lettre:"", icone:"pointer", p2:false}],
  [{id:"dodge", lettre:"O", icone:"sun", p2:false}, {id:"burn", lettre:"O", icone:"flame", p2:false}, {id:"sponge", lettre:"O", icone:"cloud", p2:false}],
  // section 3
  [{id:"pen", lettre:"P", icone:"pen-tool", p2:false}],
  [{id:"type", lettre:"T", icone:"type", p2:false}],
  [{id:"pathSelection", lettre:"A", icone:"mouse-pointer-2", p2:false}],
  [{id:"rectangle", lettre:"U", icone:"rectangle-horizontal", p2:false}, {id:"ellipseShape", lettre:"U", icone:"circle", p2:false}, {id:"triangle", lettre:"U", icone:"triangle", p2:false}, {id:"polygon", lettre:"U", icone:"pentagon", p2:false}, {id:"line", lettre:"U", icone:"minus", p2:false}, {id:"customShape", lettre:"U", icone:"diamond", p2:false}],
  // section 4
  [{id:"hand", lettre:"H", icone:"hand", p2:true}],
  [{id:"zoom", lettre:"Z", icone:"search", p2:true}],
];
export const SECTIONS = [6, 8, 4, 2];                     // nombre d'emplacements par section (somme 20)
export function outilParLettre(lettre, courant, maj, prefMaj = false) { /* cyclage de photocraft (shortcuts.rs:327-340) :
  lettre du groupe courant -> outil suivant du groupe (si !prefMaj ou maj) ; autre groupe -> premier outil du groupe ;
  outils p2:false ignorés (on saute au suivant p2:true du groupe, sinon null) */ }
export function emplacementDe(id) { /* index de l'emplacement */ }
```

Si une icône nommée ci-dessus n'existe pas dans `assets/icons/` des sources, prendre l'icône Lucide la plus proche présente dans ce dossier et corriger la donnée (le banc vérifie que chaque `icone` existe dans `frontend/photolab/icones/`).

Comportements : clic = outil (les `p2:false` sont visibles, grisés, infobulle « {nom} — bientôt ») ; clic droit ou appui > 350 ms sur un emplacement groupé = flyout (liste icône + nom + lettre à droite, puce sur l'outil actif) ; lettres au clavier (hors champ de saisie) via `outilParLettre` ; infobulle « Nom (lettre) » ; pastilles de couleur avant/arrière-plan sous la barre (X = inverser → `tools.swapColors`, D = défaut → `tools.defaultColors`, clic = sélecteur `<input type=color>` → `tools.setColors`). Barre d'options (`#options`) selon l'outil : sélections → mode (nouveau / ajouter / soustraire / intersection), contour progressif px, lissage ; baguette → tolérance 0-255 (32), contiguë, tous les calques ; sélection rapide → taille (30) ; recadrage → « Supprimer les pixels recadrés » ; déplacement → « Sélection auto. » (calque/groupe).

`qa/outils.test.mjs` : 20 emplacements, sections somme 20, chaque `icone` présente dans `icones/`, cyclage (M depuis move → rectMarquee ; M depuis rectMarquee → ellipseMarquee ; M depuis ellipseMarquee → rectMarquee ; W saute objectSelection ; prefMaj sans Maj garde l'outil courant du groupe), lettres d'un outil p2:false seul (B) → null.

- [ ] Step 1 : test rouge ; Step 2 : implémenter ; Step 3 : vert.

### Task B4 : menus générés

**Files :** Create `frontend/photolab/js/mod-menus.js`, `qa/menus.test.mjs`.

PURE :

```js
// catalogue = donnees/menus.json ; registre = GET /api/photolab/commandes ([{id,label,menu,shortcut,params,enabled}]) ;
// refuses = préfixes refusés par le pont (copie de PREFIXES_REFUSES, en minuscules) ; lang = "fr"|"en".
export function construireMenus(catalogue, registre, refuses, lang) {
  /* -> [{nom, nom_affiche, entrees:[{type:"separateur"} | {type:"sous-menu", nom, nom_affiche, entrees}
        | {type:"commande", id, libelle, raccourci (Ctrl+… affiché, Cmd->Ctrl), etat:"actif"|"inactif"|"bientot"}]}]
     - ordre exact du catalogue ; sous-menu placé à la position de son premier enfant ;
     - séparateurs en tête/fin ou doublés supprimés ;
     - etat "bientot" si l'id est absent du registre, ou préfixe refusé (file./app./automate./…) SAUF les ids que l'écran
       traite lui-même : file.new, file.open, file.close, file.save, file.saveAs, file.export.exportAs ;
     - etat "inactif" si registre.enabled === false ; sinon "actif" ;
     - menu « Aide » ajouté en dernier (le catalogue s'arrête à Window) : une entrée « À propos du Photolab » (id "pl.apropos"). */
}
export function raccourciAffiche(s) { /* "Cmd+Shift+N" -> "Ctrl+Maj+N" (fr) / "Ctrl+Shift+N" (en) ; "Cmd+=" -> "Ctrl+=" */ }
```

Comportements : barre `#menubar` (10 menus), menus déroulants au style de photocraft (A5 : libellé à gauche, raccourci à droite gris, entrées inactives grisées, « ▸ » des sous-menus, survol = bande accent), navigation clavier (↑ ↓ → ← ↩ Échap), défilement si trop haut ; un clic sur une entrée « actif » sans paramètres → `/executer {command:id}` puis rafraîchir ; une entrée dont le registre décrit des paramètres obligatoires (texte `params` non vide et différent de `{}`) → `etat` reste « actif » mais ouvre un dialogue « Ce réglage arrive en P3 » (P3 = dialogues générés) — sauf celles traitées par l'écran ; « bientot » → infobulle « Bientôt dans le Photolab ». Libellés selon `dzLang()`.

`qa/menus.test.mjs` (catalogue réel `donnees/menus.json` + registre factice minimal) : 10 menus (9 + Aide), File commence par « Nouveau… » (fr) / « New… » (en), « Ctrl+N », `file.saveAs` traité par l'écran (actif), `file.place.embedded` → « bientot », aucune entrée doublée de séparateurs, sous-menu Filter › Blur contient « Flou gaussien… », raccourciAffiche.

- [ ] Step 1 : test rouge ; Step 2 : implémenter ; Step 3 : vert.

---

## Phase C — documents, panneaux, outils

### Task C1 : fichier — Nouveau, Ouvrir, Enregistrer

**Files :** Create `frontend/photolab/js/mod-fichier.js`, `qa/fichier.test.mjs`.

PURE : `PRESETS` (sous-ensemble des 33 de photocraft, B §5, renommés D8 : « Taille par défaut » 7 × 5 in @ 300 ppi = 2100 × 1500, « HDTV 1080p » 1920 × 1080 @ 72, « 4K UHD » 3840 × 2160, « Instagram carré » 1080 × 1080, « Story 9:16 » 1080 × 1920, « A4 300 ppi » 2480 × 3508, « Web 1366 × 768 ») et `parametresNouveau(form)` → `{width, height, resolution, mode:"rgb", depth:8, background:"white"|"black"|"transparent"|"#rrggbb", name}` borné 1..30000, rejet clair sinon.
Dialogue Nouveau (style A3 : catégories en onglets, cartes de préréglages, colonne « Détails » nom/largeur/hauteur/orientation/résolution/fond, « Fermer » / « Créer ») → `/nouveau`. Ouvrir : `parent.__dzLibPicker({titre: dzT(...)}, nom => /ouvrir {filename:nom})` si le parent existe (même origine), sinon grille de repli `/api/images`. Dépôt d'un fichier sur la page : `POST /api/images/upload` (FormData `file`) puis `/ouvrir`. Enregistrer : « Enregistrer dans la Bibliothèque » (PNG, Ctrl+S) → `/bibliotheque {format:"png"}` + toast avec le nom ; « Exporter… » (Ctrl+Alt+Maj+W) → dialogue format PSD / PCRAFT / PNG / JPG (qualité) / WEBP / TIFF → `/enregistrer` puis téléchargement par l'URL rendue. Fermer (Ctrl+W) → confirmation (dialogue maison) si `revision` a changé depuis le dernier enregistrement, puis retour à l'accueil côté écran (le document reste dans la session du moteur ; un Nouveau ou un Ouvrir suivant le remplace comme document actif).
`qa/fichier.test.mjs` : chaque preset dans les bornes, `parametresNouveau` (largeur 0 → erreur, fond « transparent » accepté, hex invalide → erreur), aucun preset ne contient « Photoshop ».

- [ ] Steps TDD : test rouge → implémentation → vert.

### Task C2 : panneaux Calques, Propriétés, Couleur, Historique, Navigateur

**Files :** Create `mod-calques.js`, `mod-proprietes.js`, `mod-couleur.js`, `mod-historique.js`, `mod-navigateur.js`, `qa/panneaux.test.mjs`.

PURES à tester : `aplatirCalques(layers)` (arbre → liste avec `profondeur`, ordre haut → bas), `actionSelection(id, ctrl, maj)` → `{layer:id, mode: replace|toggle|range}`, `pourcent(x)` (0..1 → « 50 % ») et `depuisPourcent("50")` → 0.5 borné, `MODES_FUSION` (les 27 de B §4 dans l'ordre de photocraft, libellés fr/en), `versHex([r,g,b,a])` (flottants → « #rrggbb »), `etatsHistorique(history, canRedo)` → liste affichable, `annulationsPour(indexClique, history)` → n à annuler (clic sur l'état k de n états appliqués → n-1-k).
Calques (B §3, A4) : filtre « Type » (texte libre sur le nom en P2), mode de fusion (menu des 27) + Opacité % + « Verr. : » (5 boutons, état tenu par l'écran — le moteur ne le relit pas) + Fond % ; lignes : œil (`layer.setProps {visible}`), vignette (`/vignettes`, rechargée quand `revision` change, débounce 400 ms), nom (double-clic = renommer en place, ↩ valide, Échap annule → `layer.renameLayer`), cadenas sur l'arrière-plan ; clic / Ctrl+clic / Maj+clic → `layer.select` ; glisser une ligne → `layer.moveTo {target, position: above|below|into (groupes, 30-70 % de la hauteur)}` ; pied : nouveau calque, nouveau groupe, dupliquer, fusionner vers le bas, supprimer (les boutons masque/fx/réglage restent visibles, grisés « bientôt »). Propriétés : sans calque → document (L × H px, résolution, mode, profondeur) ; avec calque → nom, type, bornes `[x,y,w,h]`. Couleur : pastilles + `<input type=color>` + hex. Historique : liste des états (le dernier en accent) ; clic sur un état antérieur → `/historique {annuler:n}` ; boutons ↶ ↷ (Ctrl+Z / Ctrl+Maj+Z). Navigateur : vignette (dernier rendu réduit) + rectangle de la vue ; clic/glisser = recentrer.

- [ ] Steps TDD.

### Task C3 : outils Déplacement, sélections, Recadrage, Pipette

**Files :** Create `mod-selection.js`, `mod-deplacer.js`, `mod-recadrer.js`, `mod-pipette.js`, `qa/gestes.test.mjs`.

PURES à tester d'abord (`qa/gestes.test.mjs`) :
- `rectDepuisGlisser(x0,y0,x1,y1,{carre,centre})` → `{x,y,width,height}` entiers ≥ 0 (Maj = carré, Alt = depuis le centre ; règle « fresh » de B §8 : un modificateur tenu À L'APPUI choisit le mode, pas la contrainte).
- `modeSelection(barre, maj, alt, aLAppui)` → replace|add|subtract|intersect (Maj = ajouter, Alt = soustraire, Maj+Alt = intersection, sinon le mode de la barre).
- `fermeturePolygone(points, x, y, z)` → vrai si à moins de 8 px écran du premier sommet avec ≥ 3 sommets.
- `deplacementCommande(aSelection, dx, dy, calque)` → `{command:"edit.transform", params:{matrix:[1,0,0,1,dx,dy]}}` si sélection, sinon `{command:"layer.translate", params:{layer, dx, dy}}` ; `contrainteAxe(dx,dy)` (Maj : axe dominant).
- `rectRecadrage` = `rectDepuisGlisser` borné au document.
Comportements (coordonnées document par `versDoc`) : rectangle/ellipse → `select.rect {…, ellipse, mode, antiAlias, feather}` au relâchement (un rectangle < 2 px désélectionne → `select.deselect`) ; lasso → `select.lasso {points}` (< 3 points → désélectionner) ; lasso polygonal : clic = sommet, double-clic ou fermeture → `select.lasso`, ↩ valide, Échap annule ; baguette → `select.magicWand {x,y,tolerance,contiguous,sampleAllLayers,mode}` ; sélection rapide → `select.quick {points (trace du glisser), size, mode}` ; Ctrl+A / Ctrl+D / Ctrl+Maj+I. Déplacement : glisser → aperçu par translation CSS du rendu pendant le geste, commande au relâchement ; Maj = axe ; flèches 1 px, Maj+flèches 10 px ; « Sélection auto. » ou Ctrl+clic → `layer.pickAt {x,y,target,select:true}`. Recadrage : tracer le cadre (poignées aux coins, 8 px), ↩ ou double-clic → `image.crop {x,y,width,height,deleteCroppedPixels}`, Échap annule ; sans cadre et avec sélection → `image.crop {}`. Pipette : clic → `document.pixel` → `tools.setColors {foreground}` (Alt → background). Sélection affichée : contour pointillé animé du rectangle `selectionBounds` dans `#fourmis` (le moteur ne donne que les bornes en P2 — dit dans le statut).
Après chaque commande : `/inspecter` puis `/rendu` (et vignettes débouncées) — un seul cycle en vol à la fois, le suivant fusionné.

- [ ] Steps TDD.

### Task C4 : textes et langue

**Files :** Create `frontend/shared/i18n/photolab.json` (clés `photolab.*`, fr de référence + en) ; réassembler (`python scripts/i18n_assembler.py`) ; tout texte de l'écran passe par `dzT("photolab.…")` (les libellés de menus viennent de `menus.json` selon `dzLang()`) ; `qa/textes.test.mjs` : aucun texte français en dur dans `index.html` et `js/*.js` hors clés (relevé : `python <skill traduction-deepotus>/scripts/releve_chaines.py frontend/photolab --fr-seulement --hors-dico frontend/shared/i18n/photolab.json frontend/shared/i18n/commun.json` ne sort rien) — banc Python `backend/tests/test_photolab_textes.py` qui lance ce relevé. `test_i18n_l0.py` doit rester vert (assemblage à jour).

- [ ] Steps TDD.

---

## Phase D — l'entrée dans la barre des applications

### Task D1 : patcher de queue `patch_bundle_photolab.py`

**Files :** Create `scripts/patch_bundle_photolab.py`, `backend/tests/test_photolab_lanceur.py` ; Modify `frontend/dist/assets/index-BEOJX8L5.js` (par le patcher), les 3 feuilles de jetons (`--cat-photo: oklch(.74 .12 200)` à côté de `--cat-vectoriel`), `backend/tests/test_assets2d_lanceur.py` (épingle `Yu`).

Modèle exact : `scripts/patch_bundle_assets2d.py` (t125) — lire en octets, BOM géré, `PATCHES = [(tag, ancre, remplacement, n)]`, deltas figés calculés à la première application et écrits dans le script, `SONDE_AMONT`, marqueur contre la double application (`{id:"photolab",`), `--check`, BASELINE = le bundle commis de `main` au moment de la tâche (noter son commit), aucun `.bak` laissé.
Sections :
1. icône `photolab` (glyphe 24 × 24 `currentColor` selon DESIGN.md §15-2 : un objectif — anneau evenodd + diaphragme à 6 lames simplifié ; masses pleines, support .26-.45) insérée avant `gamegrid:r.jsxs("g",{fill:"currentColor",children:[` ;
2. entrée de rail `{id:"photolab",label:"Photolab",icon:"photolab",desc:"Retouche d'image & calques",new:!0},` insérée juste APRÈS l'entrée `{id:"vectorlab",…},` (ancre : l'entrée vectorlab complète) ;
3. vue `s==="photolab"&&r.jsx("iframe",{src:"/photolab/",title:"Photolab",style:{position:"absolute",inset:0,width:"100%",height:"100%",border:"0",background:"var(--bg-base)"}},"pplab"),` insérée après la vue vectorlab ;
4. `Yu` : `"settings","vectorlab"]` → `"settings","vectorlab","photolab"]`.
`test_photolab_lanceur.py` (modèle `test_assets2d_lanceur.py`) : rejeu depuis la BASELINE dans un dossier temporaire (CRLF du poste) = bundle commis octet pour octet ; second passage refusé (« double application ») ; chaque section une fois ; `x.useState(` = 731 et `DzTracks` = 181 inchangés ; `node --check` ; l'icône `Sh.photolab` existe et rend un `<g>`. Mettre à jour l'épingle de `test_assets2d_lanceur.py:96-97` vers la nouvelle liste `Yu` (commentaire : t137).

- [ ] Steps : banc rouge → patcher → appliquer → banc vert → `python scripts/restaurer_bak_montage.py` puis balayage des bancs qui lisent le bundle.

---

## Phase E — preuve et fin

### Task E1 : mutations, balayage, preuve, compte rendu

- [ ] Mutations (sources copiées AVANT, comparées APRÈS), chacune doit rougir son banc : `palier` sans borne haute ; `zoomAutour` qui ne garde pas le point ; `outilParLettre` qui ne saute pas les p2:false ; `construireMenus` qui garde les doubles séparateurs ; `modeSelection` qui inverse Maj/Alt ; `deplacementCommande` qui ignore la sélection ; vignettes sans `try/finally` (la copie reste ouverte → le banc vrai moteur voit 2 documents) ; patcher sans la section `Yu` ; route `/historique` sans borne 100.
- [ ] Balayage : `restaurer_bak_montage.py` puis `tests/test_*.py` qui lisent le bundle, `main.py`, les pages ou les routes ; `node qa/run.mjs` (photolab) et `node qa/run.mjs` (vectorlab, doit rester vert).
- [ ] Preuve sur 8799 (`preuve-t115`, moteur présent) dans le navigateur intégré à 1400 × 900 : clic sur « Photolab » dans la barre → iframe ; Nouveau (HDTV 1080p) ; Ouvrir depuis la Bibliothèque (`herbe.png`) ; zoom Ctrl+molette, Espace-glisser ; sélection rectangle puis Ctrl+J (calque par copier) ; déplacer le calque de 100 px ; baguette ; recadrer ; pipette → pastille ; historique : clic 2 états en arrière ; panneau Calques : vignettes, œil, opacité 50 %, renommer ; menus : Filtre › Flou › Flou gaussien… (dialogue « P3 ») ; Image › Réglages › Négatif (actif, exécuté) ; Enregistrer dans la Bibliothèque → visible dans la Bibliothèque avec la source « Photolab » ; bascule en English → libellés anglais. Captures de chaque étape clé.
- [ ] Suivi (note t137), mémoire, compte rendu ; attendre « commit et ouvre la PR ». Installation : backend (routes, main.py, library_index) → relance ; bundle → rafraîchir la page.

---

## Auto-revue

- **Couverture du lot P2 de la spec** : écran monté et ouvert depuis la barre (A2, D1) ; zones et design D2 (B1) ; canevas zoom/main (B2) ; outils et lettres D4 (B3, C3) ; menus générés D3 (B4) ; Nouveau/Ouvrir/Enregistrer D5 (C1, A1-4) ; panneaux Calques/Propriétés/Couleur/Historique/Navigateur (C2, A1) ; bilingue D6 (C4) ; D8 (B1, C1, B4). Hors P2 et dit : peinture, retouche, texte, formes, plume (P3b) ; dialogues de paramètres des filtres et réglages (P3) ; masques, styles (P3) ; liens « Envoyer vers » aller-retour complets (P4).
- **Écart assumé au gabarit du skill** : le code complet est donné pour les fonctions PURES et leurs bancs (signatures et règles exactes), et le comportement de l'interface est spécifié précisément sans être écrit d'avance — écrire ici des milliers de lignes d'interface serait illusoire ; chaque implémenteur reçoit sa tâche, ses fonctions pures, ses bancs et les relevés.
- **Noms cohérents** : `PL`, `init*`, `palier`, `ajuster`, `versDoc`, `versEcran`, `zoomAutour`, `tailleRendu`, `EMPLACEMENTS`, `SECTIONS`, `outilParLettre`, `emplacementDe`, `construireMenus`, `raccourciAffiche`, `PRESETS`, `parametresNouveau`, `aplatirCalques`, `actionSelection`, `pourcent`, `depuisPourcent`, `MODES_FUSION`, `versHex`, `etatsHistorique`, `annulationsPour`, `rectDepuisGlisser`, `modeSelection`, `fermeturePolygone`, `deplacementCommande`, `contrainteAxe`, `rectRecadrage`.
