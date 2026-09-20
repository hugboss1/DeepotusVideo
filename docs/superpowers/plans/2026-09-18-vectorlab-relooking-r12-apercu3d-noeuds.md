# Vectorlab relooking Affinity — R12 aperçu 3D en couleurs, dépouille du logo, nœuds qui suivent le curseur — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module
> pur). Steps use checkbox (`- [ ]`) syntax for tracking.
> Demande de l'utilisateur (18/09/2026, capture du dialogue Impression 3D,
> mode Logo, « hello » extrudé tout en blanc cassé) : (a) l'aperçu 3D en
> couleurs, (b) le réglage du « degré d'extrusion » du logo, (c) l'outil
> Nœud dont les nœuds et poignées « ne suivent pas strictement le curseur »
> et « arrivent en retard sur le relâchement ».
> Branche `chantier/vectorlab-affinity`, après R11 (`e2c692a`). Ce plan est
> COMMIS avant le code.

> **RELEVÉ DE LIVRAISON (19/09/2026, nuit du 18) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ — `print3d.py` et `routes.py` sont du Python : l'utilisateur relance le backend.**
>
> **Livré** (plan `5b23275`, puis `cef2d9a` → `82054df`, 9 commits) :
> mod-solide : `COULEUR_DEFAUT` (le blanc cassé d'avant, donc rien ne change
> sans couleur), `couleur_de_piece` (tuile → fiche du terrain, fond hex, sinon
> contour hex, sinon défaut), `couleur_dominante` (vote), `hex_vers_facteur`
> (sRGB → linéaire), `glb_de_pieces` (une primitive + un matériau PAR PIÈCE ;
> `glb_de_triangles` conservé), `plateau_pieces` pose `couleur`,
> `extruder_depouille` (retrait z·tan α en marches ≤ 0,2 mm, 24 au plus ;
> angle négatif = extrusion retournée en z par `retourner_z`, la forme dessinée
> devient le sommet), `extruder_biseau(…, { depouille })` ; print3d.py :
> `ecrire_3mf` accepte des pièces `(nom, tris, couleur)` → `<basematerials>`
> + UN OBJET PAR PIÈCE (ferme le reste « un seul maillage » du lot D), la
> liste de triangles nue reste acceptée ; `creer_export(couleur)` ;
> `creer_lot` à trois éléments ; routes `from-stl?couleur=` et `lot` Form
> `couleurs` JSON (hex invalide ou JSON cassé = ignoré, jamais un 400) ;
> mod-impression : pièces colorées (logo = dominante de la sélection, calque
> = dominante de ses objets, relief = sable), `couleurs_json` /
> `couleur_du_lot`, `reglages_lire.depouille` borné ±45, champ **Dépouille
> des flancs (°)** + curseur synchronisés, l'évidement la désactive en le
> disant ; mod-noeudapercu : `planificateur({raf, caf})` (une demande en vol,
> `vider()` au relâchement) + `VL.apercuNoeuds.debut/poser/fin` ;
> `noeuds_deplacer_segs` pur (mod-noeuds, `op_noeuds_deplacer` l'appelle) ;
> les CINQ gestes (ancre de mod-tools, ancres de mod-outils2, poignée /
> segment / échelle / rotation de mod-noeudui) posent l'aperçu par ce chemin
> — plus aucun `JSON.parse(JSON.stringify(doc))` au pointermove, plus de
> remise du `d` d'avant au pointerup ; le cœur et la boîte de transformation
> dessinent depuis `etat.noeudsApercu` pendant le geste.
>
> **TDD tenu** : RED ×5 constatés (couleurs, dépouille, impression_ui ×2,
> noeudapercu ; pytest ×2). Bancs : solide 26 → **52**, impression_ui 7 →
> **11**, noeudapercu **10** (nouveau), pytest test_print3d 13 → **15** ;
> `run.mjs` tous passés, `test_vector_docs` inchangé. Le banc de la dépouille
> a démasqué UNE MARCHE d'écart au sommet (retrait / n par flanc) : la base
> est gardée EXACTE (la forme dessinée), le sommet porte l'erreur ≤ 0,2 mm par
> flanc — tolérance flottante corrigée par `4799168` (un commit était parti sur
> un banc rouge, ma chaîne `grep` avait masqué l'échec — dit).
>
> **Prouvé en réel** (backend du worktree 8799, données isolées, viewport
> 1400 × 900, document créé par `POST /vector/docs` — il lui faut `v: 1`) :
> **nœuds** — ancre 1 tirée sur 6 `pointermove` : écart carré-de-l'ancre ↔
> curseur **0,000 px** à chaque pas, sortante qui suit (+40, 0 conservé),
> **0 `JSON.stringify` pendant le glisser**, `d` final = `d` de l'aperçu,
> `etat.noeudsApercu` remis à null ; poignée sortante : 0,000 px ×3, `C 380
> 220 …` ; segment : la droite devient `C 166.67 263.33 → 283.33 → 303.33`
> (progressif), final = aperçu ; ancres 2 et 3 (mod-outils2) : 0,000 px ×3
> chacune, la boîte de transformation suit exactement (−20 15, −40 30, −55
> 35) ; 0 erreur. **Aperçu 3D** — mode Calques sur deux calques rouge / bleu :
> GLB à **2 primitives, matériaux `[1,0,0,1]` et `[0,0,1,1]`**, `model-viewer
> .loaded === true`, résumé « 89 × 81 × 3 mm · 2 pièce(s) » ; mode Logo sur
> le rect rouge (31,75 mm, h 5) : dépouille 0 → base = sommet = 31,75 ;
> **+30° → sommet 26,361** (31,75 − 5,774 + une marche 0,385) ; **−30° →
> base 26,361, sommet 31,75** (miroir) ; curseur → champ (12) ; évider →
> champ désactivé « l'évidement ignore la dépouille » ; « Un STL » →
> `preuve-r12-20260918`, `impression.json.couleur = "#ff0000"`, le 3MF
> contient `<base displaycolor="#FF0000FF"/>` et `<object … pid="1"
> pindex="0">` (relu sur disque). Piège de preuve : dans le volet caché du
> navigateur intégré `requestAnimationFrame` ne tire JAMAIS (`rafReel:
> false` mesuré) — le planificateur lit le global à l'appel, la preuve l'a
> substitué par un temporisateur de 16 ms ; dans un navigateur visible c'est
> le vrai rAF.
>
> **Déployé** : 14 fichiers installés = base `e2c692a` (deux nouveaux) →
> sauvegarde `_backup_predeploy_2026-09-18-relooking-r12` (12 fichiers) →
> `git archive HEAD` → **14/14 = cible** par hash-object ; pré-vol du python
> embarqué `import app.main` + `couleur_valide` OK. `test_print3d.py` n'est
> pas installé (les bancs `qa/` le sont).
>
> **Mode Tuiles rejoué en réel sur le backend INSTALLÉ (19/09, port 8765)** :
> document de quatre tuiles (mer, plaine, forêt, montagne) → mode « tuiles »
> proposé d'office, aperçu GLB à **4 primitives, un matériau par terrain**
> (`#2B5F9E`, `#7FB069`, `#3F7D3A`, `#8A8A8A`), hauteurs socle + terrain 2 /
> 4 / 5 / 10 mm, `loaded` vrai ; « Lot par tuile » → 4 STL + nomenclature +
> `plateau.3mf` à **quatre objets colorés** (`<base displaycolor>` ×4, un
> `<item>` par objet) et `impression.json.couleurs` par pièce. Piège
> mesuré : le premier lot est sorti à l'ANCIEN format (un objet, sans
> matériau) — le processus 8765 datait du 18/09 19:05, les fichiers Python du
> 19/09 00:02 : « relancé » se VÉRIFIE par `Get-Process … StartTime` contre le
> `LastWriteTime` de l'installé, jamais sur parole ; relance faite ici avec
> l'accord de l'utilisateur.
>
> **Reste (assumé)** : le STL ne porte pas de couleur (format) ; une pièce =
> une couleur (pas de couleur par face) ; la dépouille négative avec biseau
> fait partir le biseau du contour dessiné ; la capture d'écran du volet
> reste impossible pendant la preuve (rendu différé).

## Analyse

### (a) Pourquoi l'aperçu 3D est monochrome

| Où | Ce qui se passe aujourd'hui | Où la couleur peut passer |
|---|---|---|
| `mod-impression.js` `construire()` | une **pièce** par calque (mode Calques), par tuile (`plateau_pieces`), une seule pièce « logo » (sélection UNIE par martinez), une par dalle (Relief) ; une pièce = `{nom, tris, hauteur_mm}` | la pièce gagne `couleur` (hex) : logo = couleur DOMINANTE des fonds de la sélection ; calque = dominante des fonds de ses objets ; tuile = `couleur` de la fiche du terrain ; relief = sable par défaut |
| `mod-solide.js` `glb_de_triangles(tris)` | UN mesh, UNE primitive, UN matériau `baseColorFactor [0.82, 0.78, 0.7]` (le blanc cassé de la capture) | `glb_de_pieces(pieces)` : une primitive PAR PIÈCE, un matériau par pièce (`baseColorFactor` = hex → sRGB linéarisé, comme `gltf_builder._srgb_to_linear`) |
| `mod-extrude.js` `stl_binaire` | le STL n'a pas de couleur (format) | inchangé, dit au relevé |
| `print3d.py` `ecrire_3mf` | un seul `<object>` sans matériau ; le lot concatène TOUTES les pièces dans un seul maillage | `<basematerials>` du cœur 3MF (`displaycolor="#RRGGBBFF"`) + un `<object pid pindex>` PAR PIÈCE → le slicer (Elegoo / Orca) montre les couleurs et sépare les pièces |
| `routes.py` | `from-stl` reçoit des octets STL ; `lot` reçoit des STL + la nomenclature | `from-stl` gagne `couleur` (query, hex) ; `lot` gagne `couleurs` (Form, JSON `{piece: hex}`) |

### (b) « Degré d'extrusion » du logo

Le dialogue a déjà **Hauteur (mm)** à pas 0,1 (`step="0.1" min="0.2"`) : le pas n'est pas le manque. Ce qui manque est l'**angle de dépouille** des flancs (Affinity Designer n'extrude pas ; les logiciels de logo 3D appellent ça *bevel/draft angle*). Décision : un réglage **Dépouille (°)** de −45 à +45, 0 = flancs droits, positif = base plus large que le sommet, en PLUS de la hauteur et du biseau. Et, comme la demande dit « degré d'extrusion », un curseur `range` synchronisé avec le champ pour l'ajuster au doigt — les deux (angle + curseur).

Géométrie : `extruder_biseau` empile déjà des prismes rétrécis par `inset_multi` (marches de 0,2 mm). La dépouille est le MÊME mécanisme sur toute la hauteur : retrait r(z) = z · tan(angle). Un angle négatif ne demande pas d'« outset » (martinez perd des morceaux sur les unions successives, mesuré au lot B) : on extrude la dépouille positive puis on **retourne z** (z → h − z, triangles ré-orientés) — la forme dessinée devient le sommet, la base est rétrécie. Mur minimal et garde 256 mm inchangés ; une marche qui vide la forme s'arrête d'elle-même (« la pointe se ferme »), comme le biseau. L'évidement ignore la dépouille (dit dans le dialogue).

### (c) Pourquoi les nœuds sont en retard sur le curseur

| Module | Geste | Au `pointermove` | Défaut mesuré dans le code |
|---|---|---|---|
| `mod-tools.js` | `ancre` (un nœud) | `JSON.parse(JSON.stringify(geste.docAvant))` — un CLONE COMPLET DU DOCUMENT à chaque mouvement, puis `op_noeud_deplacer` sur le clone, puis `setAttribute("d")` | le clone coûte O(document) par événement ; l'overlay (carré de l'ancre, poignées, traits) n'est PAS redessiné : le nœud affiché reste à sa place jusqu'au `pointerup` — c'est la « latence » vue |
| `mod-outils2.js` | `ancres` (plusieurs nœuds) | `JSON.parse(JSON.stringify(etat.doc))` par mouvement + `op_noeuds_deplacer` | idem, et le clone est celui du document COURANT |
| `mod-noeudui.js` | `poignee`, `segment`, `noeuds-echelle`, `noeuds-rot` | pur (pas de clone) mais seul le `d` du chemin est patché (`poserD`) | poignées, traits et boîte de transformation figés pendant le geste ; au `pointerup` `VL.executer` re-rend tout — le saut final est le « retard » |
| `mod-tools.js` `pointerup` | `ancre` | remet le `d` D'AVANT puis exécute la commande | un aller-retour visible (flash) avant le rendu final |
| tous | aimantation `VL.aimantePt` | le point posé est le point AIMANTÉ, l'overlay n'est pas redessiné | ce qui est affiché (chemin aimanté) ≠ le carré de l'ancre (pas bougé) ; le relâchement « saute » |

Objectif Affinity : à chaque `pointermove`, nœuds, poignées, traits et segment suivent le curseur ; un seul clone par geste (aucun : on travaille sur les `segs` parsés une fois au `pointerdown`) ; le redessin est **planifié en `requestAnimationFrame`** (un cadre au plus par écran) et l'overlay est redessiné **depuis la géométrie de l'aperçu** (`etat.noeudsApercu`), pas depuis le document ; le `pointerup` VIDE le cadre en attente (ce qui est affiché est ce qui est posé) puis pose exactement le `d` affiché en UNE commande.

## Décisions tranchées

- **Couleur de pièce** = `couleur_de_piece(objet, terrains)` (mod-solide, pur) : tuile → `terrains[terrain].couleur` ; objet à fond hex → ce fond ; fond `grad:`/`motif:`/`glob:`/`none` → contour hex s'il existe, sinon `COULEUR_DEFAUT = "#D1C7B3"` (le blanc cassé d'avant, donc AUCUN changement pour un document sans couleur). `couleur_dominante(objets, terrains)` = la couleur la plus fréquente parmi les pièces candidates (le vote, pas la moyenne : une moyenne fait un marron).
- **Facteur glTF** : `hex_vers_facteur(hex)` → `[r, g, b, 1]` sRGB → linéaire (la spec glTF exige le linéaire ; `gltf_builder.py` fait la même conversion).
- **GLB** : `glb_de_pieces(pieces)` — un mesh, N primitives, N matériaux, un `bufferView` POSITION + un NORMAL par primitive ; `glb_de_triangles(tris)` reste (= une pièce de couleur par défaut) pour ne rien casser.
- **3MF** : `ecrire_3mf(pieces_ou_tris, nom)` accepte soit une liste de triangles (comme avant, un objet, sans couleur) soit une liste de `(nom, tris, couleur|None)` → `<basematerials id="1">` avec une `<base>` par pièce colorée, un `<object id=k pid="1" pindex=…>` par pièce, un `<item>` par objet. `creer_export(..., couleur=None)` et `creer_lot` (pièces à 2 ou 3 éléments) suivent. Le plateau du lot devient UN OBJET PAR PIÈCE (ferme un reste du lot D).
- **Routes** : `POST /print3d/from-stl?couleur=%23RRGGBB` ; `POST /print3d/lot` gagne `couleurs` (Form, JSON objet `{nom_piece: hex}`) ; hex validés par `^#[0-9A-Fa-f]{6}$`, un hex invalide est IGNORÉ (pas de 400 : la couleur est un confort).
- **Dépouille** : `extruder_depouille(mz, multi, hauteur, angleDeg, pasMm)` (mod-solide) — marches de retrait `≤ 0,2 mm` plafonnées à 24 marches (un texte de 300 arêtes reste sous la seconde) ; angle borné ±45 ; `retourner_z(tris, h)` pour le négatif ; `extruder_biseau(mz, multi, h, b, pas, { depouille })` : le corps sous le biseau prend la dépouille, les marches du biseau partent du retrait atteint à z = h − b. `reglages_lire` gagne `depouille` (borné ±45, 0 par défaut). Dialogue : `#impDepouille` (number) + `#impDepouilleR` (range) synchronisés ; « évider » désactive la dépouille en le disant.
- **Nœuds** : module feuille `mod-noeudapercu.js` — pur : `planificateur({ raf, caf })` → `{ demander(fn), vider(), enAttente() }` (au plus UNE demande en vol ; `vider()` exécute la dernière tout de suite), `noeuds_deplacer_segs(segs, indices, dx, dy)` (exporté par mod-noeuds, utilisé par `op_noeuds_deplacer` ET par les gestes — plus aucun clone de document) ; DOM : `initNoeudApercu(VL)` pose `VL.apercuNoeuds = { debut(id, segs), poser(segs, d), fin() }` : `poser` planifie en rAF « `d` sur le `<path>` + `etat.noeudsApercu = segs` + `VL.rendreOverlay()` » ; `fin()` vide le cadre et rend `{ d }` du dernier aperçu. Le cœur (`rendreOverlay`) et `mod-noeudui` (`surOverlay`, boîte de transformation) lisent `etat.noeudsApercu || chemin_parser(p.d)`. Les cinq gestes (ancre, ancres, poignee, segment, noeuds-echelle/rot) passent par ce chemin ; `pointerup` de mod-tools ne remet plus le `d` d'avant.
- **Aimantation** : conservée (réglage `etat.aimantNoeuds` de R10) mais l'overlay suit désormais le point AIMANTÉ ; la preuve d'écart ≤ 1 px se fait aimantation coupée (elle est un décalage VOULU sinon).

## Cartographie des fichiers

| Fichier | Rôle |
|---|---|
| `frontend/vectorlab/js/mod-solide.js` (modifier) | `COULEUR_DEFAUT`, `couleur_de_piece`, `couleur_dominante`, `hex_vers_facteur`, `glb_de_pieces`, `plateau_pieces` pose `couleur`, `extruder_depouille`, `retourner_z`, `extruder_biseau` option `depouille` (T1, T4) |
| `frontend/vectorlab/qa/solide.test.mjs` (modifier) | RED puis vert des fonctions ci-dessus (T1, T4) |
| `backend/app/services/print3d.py` (modifier) | `ecrire_3mf` par pièces colorées, `creer_export(couleur)`, `creer_lot` pièces à 3 (T2) |
| `backend/app/api/routes.py` (modifier) | `couleur` sur from-stl, `couleurs` sur lot (T2) |
| `backend/tests/test_print3d.py` (modifier) | miroir pytest (T2) |
| `frontend/vectorlab/js/mod-impression.js` (modifier) | pièces colorées, `glb_de_pieces`, `couleurs_json`, envoi de la couleur, champ Dépouille (T3, T5) |
| `frontend/vectorlab/qa/impression_ui.test.mjs` (modifier) | `reglages_lire.depouille`, `couleurs_json` (T3, T5) |
| `frontend/vectorlab/js/mod-noeudapercu.js` (créer) | `planificateur`, `initNoeudApercu` (T6, T7) |
| `frontend/vectorlab/js/mod-noeuds.js` (modifier) | export `noeuds_deplacer_segs` (T6) |
| `frontend/vectorlab/qa/noeudapercu.test.mjs` (créer) | RED puis vert (T6) |
| `frontend/vectorlab/js/core.js` (modifier) | ancres depuis `etat.noeudsApercu`, init du module (T7) |
| `frontend/vectorlab/js/mod-tools.js`, `mod-outils2.js`, `mod-noeudui.js` (modifier) | gestes via `VL.apercuNoeuds` (T7) |
| `frontend/vectorlab/vectorlab.css` (modifier) | rangée du curseur de dépouille (T5) |

---

### Task 1 : couleurs de pièce et GLB multi-matériaux (mod-solide, pur)

**Files :** Modify `frontend/vectorlab/js/mod-solide.js`, `frontend/vectorlab/qa/solide.test.mjs`

- [ ] **Step 1 : le banc RED** — ajouter en fin de `solide.test.mjs`, avant la ligne `if (echecs.length)` :

```js
/* ── R12 : couleurs de pièce, GLB multi-matériaux ── */
{
  const { COULEUR_DEFAUT, couleur_de_piece, couleur_dominante, hex_vers_facteur, glb_de_pieces } = await import("../js/mod-solide.js");
  const T = TERRAINS_DEFAUT;
  ok("tuile → couleur de la fiche du terrain", couleur_de_piece({ type: "tuile", terrain: "foret" }, T) === "#3F7D3A");
  ok("tuile de terrain inconnu → gris de terrains_de", couleur_de_piece({ type: "tuile", terrain: "lave" }, T) === "#888888");
  ok("fond hex → ce fond", couleur_de_piece({ type: "rect", style: { fond: "#ff0000" } }, T) === "#ff0000");
  ok("fond dégradé → le contour hex", couleur_de_piece({ type: "path", style: { fond: "grad:g1", contour: { couleur: "#00ff00", epaisseur: 2 } } }, T) === "#00ff00");
  ok("sans fond ni contour → COULEUR_DEFAUT (le blanc cassé d'avant)", couleur_de_piece({ type: "path", style: { fond: "none" } }, T) === COULEUR_DEFAUT && COULEUR_DEFAUT === "#D1C7B3");
  ok("dominante = vote, pas moyenne", couleur_dominante([{ style: { fond: "#ff0000" } }, { style: { fond: "#0000ff" } }, { style: { fond: "#ff0000" } }], T) === "#ff0000");
  ok("dominante d'une liste vide → défaut", couleur_dominante([], T) === COULEUR_DEFAUT);
  const f = hex_vers_facteur("#ff8000");
  ok("facteur glTF linéarisé : #ff8000 → [1, ≈0,216, 0, 1]", f.length === 4 && f[0] === 1 && pres(f[1], 0.2158, 0.002) && f[2] === 0 && f[3] === 1, JSON.stringify(f));
  ok("hex court accepté, invalide → défaut", hex_vers_facteur("#fff")[0] === 1 && pres(hex_vers_facteur("bleu")[0], hex_vers_facteur(COULEUR_DEFAUT)[0], 1e-9));
  const a = extruder([[carre(0, 0, 10)]], 2, 0), b = extruder([[carre(20, 0, 10)]], 3, 0);
  const glb = glb_de_pieces([{ nom: "a", tris: a, couleur: "#ff0000" }, { nom: "b", tris: b, couleur: "#0000ff" }]);
  const dv = new DataView(glb.buffer);
  const jlen = dv.getUint32(12, true);
  const json = JSON.parse(new TextDecoder().decode(glb.subarray(20, 20 + jlen)));
  ok("GLB : 2 primitives, 2 matériaux, chacune sur son matériau", json.meshes[0].primitives.length === 2 && json.materials.length === 2
     && json.meshes[0].primitives[0].material === 0 && json.meshes[0].primitives[1].material === 1, JSON.stringify(json.meshes));
  ok("GLB : matériaux de couleurs DIFFÉRENTES (rouge puis bleu)", json.materials[0].pbrMetallicRoughness.baseColorFactor[0] === 1 && json.materials[1].pbrMetallicRoughness.baseColorFactor[2] === 1
     && json.materials[0].pbrMetallicRoughness.baseColorFactor[2] === 0);
  ok("GLB : accessors comptent les sommets de chaque pièce", json.accessors[0].count === a.length * 3 && json.accessors[2].count === b.length * 3);
  ok("GLB : longueur totale = en-tête + JSON + BIN", dv.getUint32(8, true) === glb.length && glb.length % 4 === 0);
  const g1 = glb_de_triangles(a), j1 = JSON.parse(new TextDecoder().decode(g1.subarray(20, 20 + new DataView(g1.buffer).getUint32(12, true))));
  ok("glb_de_triangles reste : une primitive, le matériau par défaut", j1.materials.length === 1 && pres(j1.materials[0].pbrMetallicRoughness.baseColorFactor[0], hex_vers_facteur(COULEUR_DEFAUT)[0], 1e-6));
  const g = grille_normaliser({ type: "hex", pas: 20 });
  const P = plateau_pieces([{ id: "t1", type: "tuile", q: 0, r: 0, terrain: "mer" }], T, g, { socle_mm: 2, sMm: 1 });
  ok("plateau_pieces pose la couleur de la fiche", P[0].couleur === "#2B5F9E");
}
```

- [ ] **Step 2 : constater le RED** — `node frontend/vectorlab/qa/solide.test.mjs` → `ECHECS solide` avec « couleur_de_piece is not a function » (ou TypeError équivalent), exit 1.

- [ ] **Step 3 : implémenter** — dans `mod-solide.js`, après `MUR_MIN_MM` :

```js
export const COULEUR_DEFAUT = "#D1C7B3";     // le blanc cassé d'avant R12 : un document sans couleur ne change pas
const _HEX = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;
function _hex6(h) {
  if (typeof h !== "string" || !_HEX.test(h)) return null;
  return h.length === 4 ? "#" + h[1] + h[1] + h[2] + h[2] + h[3] + h[3] : h;
}
export function couleur_de_piece(objet, terrains) {
  if (!objet) return COULEUR_DEFAUT;
  if (objet.type === "tuile") {
    const f = terrains && terrains[objet.terrain];
    return (f && _hex6(f.couleur)) || "#888888";
  }
  const s = objet.style || {};
  return _hex6(s.fond) || (s.contour && _hex6(s.contour.couleur)) || COULEUR_DEFAUT;
}
export function couleur_dominante(objets, terrains) {
  const votes = new Map();
  for (const o of objets || []) {
    if (!o || o.type === "texte") continue;
    const c = couleur_de_piece(o, terrains);
    votes.set(c, (votes.get(c) || 0) + 1);
  }
  let best = COULEUR_DEFAUT, n = 0;
  for (const [c, k] of votes) if (k > n) { best = c; n = k; }
  return best;
}
const _lin = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
export function hex_vers_facteur(hex) {
  const h = _hex6(hex) || COULEUR_DEFAUT;
  const v = [1, 3, 5].map((i) => _lin(parseInt(h.slice(i, i + 2), 16) / 255));
  return [v[0], v[1], v[2], 1];
}
```

Dans `plateau_pieces`, ajouter `couleur: (fiche && _hex6(fiche.couleur)) || "#888888",` dans l'objet `piece` (après `terrain: t.terrain,`).

Remplacer `glb_de_triangles` par :

```js
/* ── GLB minimal : un mesh, UNE PRIMITIVE PAR PIÈCE (POSITION + NORMAL, sans
   index), un matériau par pièce (baseColorFactor sRGB → linéaire) ── */
export function glb_de_pieces(pieces) {
  const P = (pieces || []).filter((p) => p && p.tris && p.tris.length);
  if (!P.length) throw new Error("GLB : aucun triangle");
  const buffers = [], views = [], accessors = [], materials = [], primitives = [];
  let off = 0;
  for (const piece of P) {
    const n = piece.tris.length * 3;
    const pos = new Float32Array(n * 3), nrm = new Float32Array(n * 3);
    const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
    let k = 0;
    for (const [a, b, c] of piece.tris) {
      const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
      const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
      let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      const l = Math.hypot(nx, ny, nz) || 1;
      nx /= l; ny /= l; nz /= l;
      for (const p of [a, b, c]) {
        pos[k * 3] = p[0]; pos[k * 3 + 1] = p[1]; pos[k * 3 + 2] = p[2];
        nrm[k * 3] = nx; nrm[k * 3 + 1] = ny; nrm[k * 3 + 2] = nz;
        for (let i = 0; i < 3; i++) { min[i] = Math.min(min[i], p[i]); max[i] = Math.max(max[i], p[i]); }
        k++;
      }
    }
    const vPos = views.length;
    views.push({ buffer: 0, byteOffset: off, byteLength: pos.byteLength, target: 34962 });
    buffers.push(pos); off += pos.byteLength;
    views.push({ buffer: 0, byteOffset: off, byteLength: nrm.byteLength, target: 34962 });
    buffers.push(nrm); off += nrm.byteLength;
    const aPos = accessors.length;
    accessors.push({ bufferView: vPos, componentType: 5126, count: n, type: "VEC3", min, max });
    accessors.push({ bufferView: vPos + 1, componentType: 5126, count: n, type: "VEC3" });
    materials.push({ name: piece.nom || `piece${materials.length}`,
      pbrMetallicRoughness: { baseColorFactor: hex_vers_facteur(piece.couleur), metallicFactor: 0, roughnessFactor: 0.6 } });
    primitives.push({ attributes: { POSITION: aPos, NORMAL: aPos + 1 }, mode: 4, material: materials.length - 1 });
  }
  const json = {
    asset: { version: "2.0", generator: "Deepotus Vectorlab" },
    scene: 0, scenes: [{ nodes: [0] }], nodes: [{ mesh: 0 }],
    meshes: [{ primitives }], materials,
    buffers: [{ byteLength: off }], bufferViews: views, accessors,
  };
  let js = JSON.stringify(json);
  while (js.length % 4) js += " ";
  const jsBytes = new TextEncoder().encode(js);
  const total = 12 + 8 + jsBytes.length + 8 + off;
  const out = new Uint8Array(total);
  const dv = new DataView(out.buffer);
  dv.setUint32(0, 0x46546C67, true); dv.setUint32(4, 2, true); dv.setUint32(8, total, true);
  dv.setUint32(12, jsBytes.length, true); dv.setUint32(16, 0x4E4F534A, true);
  out.set(jsBytes, 20);
  const offBin = 20 + jsBytes.length;
  dv.setUint32(offBin, off, true); dv.setUint32(offBin + 4, 0x004E4942, true);
  let cur = offBin + 8;
  for (const b of buffers) { out.set(new Uint8Array(b.buffer), cur); cur += b.byteLength; }
  return out;
}
export function glb_de_triangles(tris) {
  return glb_de_pieces([{ nom: "piece", tris, couleur: COULEUR_DEFAUT }]);
}
```

(Les tailles Float32 sont multiples de 4 : aucun bourrage entre pièces.)

- [ ] **Step 4 : vert** — `node frontend/vectorlab/qa/solide.test.mjs` → `QA solide : PASS (41 controles)` (26 + 15). Mettre à jour le compte dans la ligne finale du banc. Puis `node frontend/vectorlab/qa/run.mjs` → tous passent.

- [ ] **Step 5 : commit** — `git commit --only frontend/vectorlab/js/mod-solide.js frontend/vectorlab/qa/solide.test.mjs -m "vectorlab R12 : couleur de piece et GLB multi-materiaux (mod-solide)"`

### Task 2 : 3MF par pièces colorées, `couleur` sur les routes (Python)

**Files :** Modify `backend/app/services/print3d.py`, `backend/app/api/routes.py`, `backend/tests/test_print3d.py`

- [ ] **Step 1 : RED** — ajouter dans `test_print3d.py` :

```python
def test_le_3mf_porte_une_couleur_et_un_objet_par_piece():
    import io
    import xml.etree.ElementTree as ET
    import zipfile
    from app.services import print3d as P3
    ns = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
    data = P3.ecrire_3mf([("a", _deux_triangles(), "#ff0000"), ("b", _deux_triangles(), None)], nom="Banc")
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("3D/3dmodel.model").decode("utf-8"))
    objets = root.findall(f".//{ns}object")
    assert len(objets) == 2 and [o.get("name") for o in objets] == ["a", "b"]
    bases = root.findall(f".//{ns}basematerials/{ns}base")
    assert len(bases) == 1 and bases[0].get("displaycolor") == "#FF0000FF"
    assert objets[0].get("pid") == "1" and objets[0].get("pindex") == "0"
    assert objets[1].get("pid") is None                   # sans couleur : aucun matériau
    assert len(root.findall(f".//{ns}build/{ns}item")) == 2
    # la voie d'avant (liste de triangles) donne toujours un objet unique sans matériau
    old = ET.fromstring(zipfile.ZipFile(io.BytesIO(P3.ecrire_3mf(_deux_triangles(), nom="X"))).read("3D/3dmodel.model").decode("utf-8"))
    assert len(old.findall(f".//{ns}object")) == 1 and not old.findall(f".//{ns}basematerials")
    # export simple coloré + lot à trois éléments
    base = pathlib.Path(_tmp, "print3d-couleur")
    out = P3.creer_export(base, "Logo", _deux_triangles(), None, "vectorlab", couleur="#00ff00")
    meta = _json.loads((base / out["dossier"] / "impression.json").read_text("utf-8"))
    assert meta["couleur"] == "#00ff00"
    x = ET.fromstring(zipfile.ZipFile(base / out["dossier"] / out["mf3"]).read("3D/3dmodel.model").decode("utf-8"))
    assert x.find(f".//{ns}base").get("displaycolor") == "#00FF00FF"
    lot = P3.creer_lot(base, "Plateau", [("t1", _deux_triangles(), "#2B5F9E"), ("t2", _deux_triangles())], "", source="banc")
    y = ET.fromstring(zipfile.ZipFile(base / lot["dossier"] / "plateau.3mf").read("3D/3dmodel.model").decode("utf-8"))
    assert len(y.findall(f".//{ns}object")) == 2 and y.find(f".//{ns}base").get("displaycolor") == "#2B5F9EFF"
    # un hex invalide est ignoré, jamais un refus
    out2 = P3.creer_export(base, "Logo2", _deux_triangles(), None, "vectorlab", couleur="bleu")
    assert _json.loads((base / out2["dossier"] / "impression.json").read_text("utf-8"))["couleur"] is None


def test_les_routes_print3d_transmettent_la_couleur():
    import asyncio
    import zipfile
    import xml.etree.ElementTree as ET
    from httpx import AsyncClient, ASGITransport
    ns = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"

    async def scenario():
        from app.main import app
        from app.services import print3d as P3
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        stl = P3.ecrire_stl(_deux_triangles())
        base = pathlib.Path(_tmp, "print3d")
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/print3d/from-stl", params={"nom": "Logo couleur", "couleur": "#ff8000"},
                             content=stl, headers={"Content-Type": "application/octet-stream"})
            assert r.status_code == 200, r.text
            x = ET.fromstring(zipfile.ZipFile(base / r.json()["dossier"] / r.json()["mf3"]).read("3D/3dmodel.model").decode("utf-8"))
            assert x.find(f".//{ns}base").get("displaycolor") == "#FF8000FF"
            r2 = await c.post("/api/print3d/lot", params={"nom": "Plateau couleur"},
                              files=[("pieces", ("t1.stl", stl, "application/octet-stream")),
                                     ("pieces", ("t2.stl", stl, "application/octet-stream"))],
                              data={"nomenclature": "piece\n", "couleurs": _json.dumps({"t1": "#2B5F9E", "t2": "pas-un-hex"})})
            assert r2.status_code == 200, r2.text
            y = ET.fromstring(zipfile.ZipFile(base / r2.json()["dossier"] / "plateau.3mf").read("3D/3dmodel.model").decode("utf-8"))
            objs = y.findall(f".//{ns}object")
            assert len(objs) == 2 and objs[0].get("pid") == "1" and objs[1].get("pid") is None
            # un JSON de couleurs cassé n'empêche pas le lot
            r3 = await c.post("/api/print3d/lot", params={"nom": "Plateau sans"},
                              files=[("pieces", ("t1.stl", stl, "application/octet-stream"))],
                              data={"nomenclature": "", "couleurs": "{pas du json"})
            assert r3.status_code == 200, r3.text
    asyncio.run(scenario())
```

- [ ] **Step 2 : constater le RED** — depuis `backend/` : `<python embarqué> -m pytest tests/test_print3d.py -q -k couleur` → 2 failed (`TypeError: ecrire_3mf() ... 'couleur'` / `AssertionError` sur `base`).

- [ ] **Step 3 : implémenter** — `print3d.py` : remplacer `ecrire_3mf` par :

```python
_HEX6 = re.compile(r"^#[0-9A-Fa-f]{6}$")


def couleur_valide(c):
    """Un hex #RRGGBB ou None — une couleur invalide est IGNORÉE (confort,
    jamais un refus)."""
    return c if isinstance(c, str) and _HEX6.match(c) else None


def _pieces_de(tris_ou_pieces, nom):
    """Accepte une liste de triangles (un objet, sans couleur) ou une liste
    de (nom, tris[, couleur])."""
    if tris_ou_pieces and isinstance(tris_ou_pieces[0], tuple) \
            and isinstance(tris_ou_pieces[0][0], str):
        out = []
        for p in tris_ou_pieces:
            out.append((str(p[0]), p[1], couleur_valide(p[2] if len(p) > 2 else None)))
        return out
    return [(str(nom), tris_ou_pieces, None)]


def _mesh_xml(tris):
    index, sommets, faces = {}, [], []
    for t in tris:
        ids = []
        for v in t:
            cle = (round(v[0], 6), round(v[1], 6), round(v[2], 6))
            i = index.get(cle)
            if i is None:
                i = len(sommets)
                index[cle] = i
                sommets.append(cle)
            ids.append(i)
        faces.append(ids)
    xml = ["<mesh>", "<vertices>"]
    xml += [f'<vertex x="{v[0]:g}" y="{v[1]:g}" z="{v[2]:g}"/>' for v in sommets]
    xml += ["</vertices>", "<triangles>"]
    xml += [f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in faces]
    xml += ["</triangles>", "</mesh>"]
    return xml


def ecrire_3mf(tris_ou_pieces, nom="Deepotus") -> bytes:
    """3MF minimal : sommets DÉDUPLIQUÉS, triangles indexés, UN OBJET PAR
    PIÈCE, un item de build par objet ; les pièces colorées portent un
    matériau `<basematerials>` (displaycolor #RRGGBBFF, cœur 3MF) — le
    fichier qu'on OUVRE (l'unité mm y est dite, pas devinée)."""
    pieces = _pieces_de(tris_ou_pieces, nom)
    bases = []            # (index du matériau) par pièce colorée
    for _, _, c in pieces:
        if c:
            bases.append(c.upper() + "FF")
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<model unit="millimeter" xml:lang="fr-FR" xmlns="{_3MF_NS}">',
        "<resources>",
    ]
    if bases:
        xml.append('<basematerials id="1">')
        xml += [f'<base name="{_xml(pieces[k][0])}" displaycolor="{bases[j]}"/>'
                for j, k in enumerate(i for i, p in enumerate(pieces) if p[2])]
        xml.append("</basematerials>")
    premier = 2 if bases else 1
    pindex = 0
    for k, (nom_piece, tris, c) in enumerate(pieces):
        mat = ""
        if c:
            mat = f' pid="1" pindex="{pindex}"'
            pindex += 1
        xml.append(f'<object id="{premier + k}" type="model" name="{_xml(nom_piece)}"{mat}>')
        xml += _mesh_xml(tris)
        xml.append("</object>")
    xml.append("</resources>")
    xml.append("<build>" + "".join(f'<item objectid="{premier + k}"/>' for k in range(len(pieces))) + "</build>")
    xml.append("</model>")
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _3MF_TYPES)
        z.writestr("_rels/.rels", _3MF_RELS)
        z.writestr("3D/3dmodel.model", "\n".join(xml))
    return tampon.getvalue()
```

`creer_export(base, nom, tris, cible_mm=None, source="", etancheite="inconnue", couleur=None)` : `couleur = couleur_valide(couleur)` ; le 3MF s'écrit `ecrire_3mf([(str(nom), monde, couleur)], nom=nom)` si `couleur` sinon comme avant ; `meta["couleur"] = couleur`.

`creer_lot` : `pieces` = liste de `(nom, tris)` ou `(nom, tris, couleur)` ; la validation du nom lit `p[0]` ; le plateau s'écrit `ecrire_3mf([(p[0], p[1], p[2] if len(p) > 2 else None) for p in pieces], nom=nom)` ; `meta["couleurs"] = {p[0]: couleur_valide(p[2]) for p in pieces if len(p) > 2 and couleur_valide(p[2])}`.

`routes.py` : `print3d_from_stl(..., couleur: str | None = None)` → `P3.creer_export(..., "garantie" if ... else "inconnue", couleur=couleur)` (passer par un `functools.partial` ou un lambda dans `to_thread` : `await asyncio.to_thread(lambda: P3.creer_export(_print3d_base(), str(nom)[:80], tris, cible_mm, str(source)[:40], "garantie" if etanche == "garantie" else "inconnue", couleur=couleur))`). `print3d_lot(..., couleurs: str = Form(default=""))` : 

```python
    table = {}
    if couleurs:
        try:
            table = json.loads(couleurs)
            if not isinstance(table, dict):
                table = {}
        except ValueError:
            table = {}          # la couleur est un confort : jamais un 400
    ...
        lues.append((Path(up.filename or "piece").stem, tris))
    lues = [(n, t, table.get(n)) for n, t in lues]
```

(vérifier que `json` est importé dans routes.py — sinon `import json` en tête.)

- [ ] **Step 4 : vert** — `pytest tests/test_print3d.py -q` → `15 passed`. Puis `pytest tests/test_vector_docs.py -q` inchangé.

- [ ] **Step 5 : commit** — `git commit --only backend/app/services/print3d.py backend/app/api/routes.py backend/tests/test_print3d.py -m "print3d : 3MF a un objet par piece et couleur par materiau, couleur sur from-stl et lot"`

### Task 3 : le dialogue envoie des pièces colorées

**Files :** Modify `frontend/vectorlab/js/mod-impression.js`, `frontend/vectorlab/qa/impression_ui.test.mjs`

- [ ] **Step 1 : RED** — dans `impression_ui.test.mjs`, importer `couleurs_json, couleur_du_lot` et ajouter :

```js
{
  const { couleurs_json, couleur_du_lot } = await import("../js/mod-impression.js");
  const P = [{ nom: "a", couleur: "#ff0000" }, { nom: "b" }, { nom: "c", couleur: "#ff0000" }, { nom: "d", couleur: "#00ff00" }];
  ok("couleurs_json : seules les pièces colorées, par nom", couleurs_json(P) === JSON.stringify({ a: "#ff0000", c: "#ff0000", d: "#00ff00" }));
  ok("couleur_du_lot : le vote des pièces", couleur_du_lot(P) === "#ff0000");
  ok("couleur_du_lot sans couleur → null", couleur_du_lot([{ nom: "x" }]) === null);
}
```

- [ ] **Step 2 : RED constaté** — `node frontend/vectorlab/qa/impression_ui.test.mjs` → échec « couleurs_json is not a function ».

- [ ] **Step 3 : implémenter** — en tête de mod-impression (zone pure) :

```js
export function couleurs_json(pieces) {
  const o = {};
  for (const p of pieces || []) if (p && p.couleur) o[p.nom] = p.couleur;
  return JSON.stringify(o);
}
export function couleur_du_lot(pieces) {
  const votes = new Map();
  for (const p of pieces || []) if (p && p.couleur) votes.set(p.couleur, (votes.get(p.couleur) || 0) + 1);
  let best = null, n = 0;
  for (const [c, k] of votes) if (k > n) { best = c; n = k; }
  return best;
}
```

Import : `glb_de_pieces, couleur_dominante` de mod-solide (garder `glb_de_triangles` importé n'est plus utile → le retirer). Dans `construire` : relief → `couleur: "#D8C9A3"` (sable) ; logo → `couleur: couleur_dominante(sel, terrains_de(doc))` ; calques → `couleur: couleur_dominante(c.objets, terrains_de(doc))` ; tuiles → déjà posée par `plateau_pieces`. Dans `apercu` : `glb_de_pieces(c.pieces)` à la place de `glb_de_triangles(c.tous)`. Dans `unStl` : `const cl = couleur_du_lot(courant.pieces); if (cl) ps.set("couleur", cl);`. Dans `lot` : `fd.append("couleurs", couleurs_json(courant.pieces));`.

- [ ] **Step 4 : vert** — `node frontend/vectorlab/qa/run.mjs` ; `node --check frontend/vectorlab/js/mod-impression.js`.

- [ ] **Step 5 : commit** — `git commit --only frontend/vectorlab/js/mod-impression.js frontend/vectorlab/qa/impression_ui.test.mjs -m "vectorlab R12 : l'apercu 3D et les exports portent la couleur des pieces"`

### Task 4 : la dépouille (mod-solide, pur)

**Files :** Modify `frontend/vectorlab/js/mod-solide.js`, `frontend/vectorlab/qa/solide.test.mjs`

- [ ] **Step 1 : RED** — ajouter au banc solide :

```js
/* ── R12 : dépouille (angle des flancs) ── */
{
  const { extruder_depouille, retourner_z } = await import("../js/mod-solide.js");
  const base = [[carre(0, 0, 20)]];
  const largeurA = (tris, z, tol = 1e-6) => {   // largeur en x de la tranche à la cote z (sommets à cette cote)
    let mn = Infinity, mx = -Infinity;
    for (const t of tris) for (const p of t) if (Math.abs(p[2] - z) <= tol) { mn = Math.min(mn, p[0]); mx = Math.max(mx, p[0]); }
    return mx - mn;
  };
  const droit = extruder_depouille(mz, base, 5, 0);
  ok("angle 0 = extrusion droite (même volume)", pres(volume_de(droit), 2000, 1e-6));
  const pos = extruder_depouille(mz, base, 5, 30);
  ok("angle +30° : base 20, sommet rétréci de 2·5·tan30 ≈ 5,77", pres(largeurA(pos, 0), 20, 1e-6) && pres(largeurA(pos, 5), 20 - 2 * 5 * Math.tan(Math.PI / 6), 0.3), `${largeurA(pos, 0)} / ${largeurA(pos, 5)}`);
  ok("angle +30° : volume entre celui du sommet et celui de la base", volume_de(pos) < 2000 && volume_de(pos) > (20 - 5.77) ** 2 * 5, volume_de(pos));
  const neg = extruder_depouille(mz, base, 5, -30);
  ok("angle −30° : le SOMMET garde 20, la base est rétrécie", pres(largeurA(neg, 5), 20, 1e-6) && largeurA(neg, 0) < 15, `${largeurA(neg, 0)} / ${largeurA(neg, 5)}`);
  ok("angle −30° : même volume que +30° (miroir en z), et fermé (volume > 0)", pres(volume_de(neg), volume_de(pos), 1e-6) && volume_de(neg) > 0);
  ok("z min 0 après retournement", Math.min(...neg.flatMap((t) => t.map((p) => p[2]))) >= -1e-9);
  let refus = 0;
  try { extruder_depouille(mz, base, 5, 60); } catch { refus++; }
  try { extruder_depouille(mz, base, 0, 10); } catch { refus++; }
  ok("angle > 45° et hauteur 0 refusés", refus === 2);
  ok("retourner_z : z → h − z, orientation inversée (volume conservé positif)", pres(volume_de(retourner_z(droit, 5)), 2000, 1e-6));
  const pointe = extruder_depouille(mz, base, 30, 45);  // retrait 30 > demi-côté 10 : la pointe se ferme d'elle-même
  ok("la pointe se ferme sans erreur (pyramide tronquée en marches)", volume_de(pointe) > 0 && volume_de(pointe) < 20 * 20 * 30);
  const combo = extruder_biseau(mz, base, 5, 1, 0.2, { depouille: 20 });
  ok("biseau + dépouille : sommet plus étroit que la dépouille seule", largeurA(combo, 5) < largeurA(extruder_depouille(mz, base, 5, 20), 5) - 1);
  ok("biseau sans option : inchangé", pres(volume_de(extruder_biseau(mz, base, 5, 1, 0.2)), volume_de(extruder_biseau(mz, base, 5, 1)), 1e-9));
}
```

- [ ] **Step 2 : RED constaté** — `node frontend/vectorlab/qa/solide.test.mjs` → « extruder_depouille is not a function ».

- [ ] **Step 3 : implémenter** —

```js
export const DEPOUILLE_MAX = 45;
export function retourner_z(tris, h) {
  return tris.map(([a, b, c]) => [[a[0], a[1], h - a[2]], [c[0], c[1], h - c[2]], [b[0], b[1], h - b[2]]]);
}
// la dépouille : retrait r(z) = z · tan(angle), en marches de retrait ≤ 0,2 mm
// (24 au plus : un texte de 300 arêtes reste sous la seconde) ; angle
// négatif = la forme dessinée est le SOMMET (extrusion positive retournée)
export function extruder_depouille(mz, multi, hauteur, angleDeg, pasMm = 0.2, zBase = 0) {
  const h = +hauteur, a = +angleDeg || 0;
  if (!(h > 0)) throw new Error("dépouille : hauteur > 0 requise");
  if (Math.abs(a) > DEPOUILLE_MAX) throw new Error(`dépouille : angle entre −${DEPOUILLE_MAX}° et ${DEPOUILLE_MAX}°`);
  if (a === 0) return extruder(multi, h, zBase);
  const retrait = h * Math.tan(Math.abs(a) * Math.PI / 180);
  const n = Math.min(24, Math.max(1, Math.ceil(retrait / Math.max(0.05, +pasMm || 0.2))));
  const dz = h / n;
  const tris = [];
  for (let k = 0; k < n; k++) {
    const m = k === 0 ? multi : inset_multi(mz, multi, retrait * k / n);
    if (!m.length) break;                        // la pointe se ferme d'elle-même
    tris.push(...extruder(m, dz, k * dz));
  }
  const out = a > 0 ? tris : retourner_z(tris, h);
  return zBase ? out.map((t) => t.map(([x, y, z]) => [x, y, z + zBase])) : out;
}
```

`extruder_biseau(mz, multi, hauteur, biseau, pasMm = 0.2, { depouille = 0 } = {})` : si `b === 0` → `return extruder_depouille(mz, multi, h, depouille, pasMm)` ; sinon le corps `extruder(multi, h - b, 0)` devient `extruder_depouille(mz, multi, h - b, depouille, pasMm)` et le retrait de départ des marches du biseau vaut `r0 = depouille > 0 ? (h - b) * Math.tan(depouille * Math.PI / 180) : 0` : `inset_multi(mz, multi, r0 + (b * k) / n)`. (Une dépouille négative avec biseau : le corps est retourné, le biseau part du contour dessiné — r0 = 0 ; dit au relevé.)

- [ ] **Step 4 : vert** — `node frontend/vectorlab/qa/solide.test.mjs` → `PASS (52 controles)` ; `run.mjs` tous passent.

- [ ] **Step 5 : commit** — `git commit --only frontend/vectorlab/js/mod-solide.js frontend/vectorlab/qa/solide.test.mjs -m "vectorlab R12 : depouille des flancs (angle ±45°) en marches, retournee pour le negatif"`

### Task 5 : le réglage Dépouille dans le dialogue

**Files :** Modify `frontend/vectorlab/js/mod-impression.js`, `frontend/vectorlab/qa/impression_ui.test.mjs`, `frontend/vectorlab/vectorlab.css`

- [ ] **Step 1 : RED** — dans le premier bloc du banc impression_ui :

```js
  ok("dépouille lue, bornée ±45, 0 par défaut", reglages_lire({ mode: "logo", depouille: "20" }).depouille === 20
     && reglages_lire({ mode: "logo", depouille: "90" }).depouille === 45 && reglages_lire({ mode: "logo", depouille: "-70" }).depouille === -45
     && reglages_lire({ mode: "logo" }).depouille === 0 && reglages_lire({ depouille: "abc" }).depouille === 0);
```

- [ ] **Step 2 : RED constaté** (`depouille` undefined).

- [ ] **Step 3 : implémenter** — `reglages_lire` : `const depouille = Math.max(-DEPOUILLE_MAX, Math.min(DEPOUILLE_MAX, num(f.depouille, 0)));` et le renvoyer. `lire()` : `depouille: $("#impDepouille").value`. `construire` (logo) : `extruder_biseau(mz(), mm, r.hauteur, r.biseau, r.pas, { depouille: r.depouille })`. Dialogue, après la ligne Biseau :

```html
<label class="imp-logo">Dépouille des flancs (°, 0 = droits, + = base plus large) <span class="imp-range"><input id="impDepouilleR" type="range" min="-45" max="45" step="1" value="0"/><input id="impDepouille" type="number" step="1" min="-45" max="45" value="0"/></span></label>
```

Synchronisation : `$("#impDepouilleR").addEventListener("input", () => { $("#impDepouille").value = $("#impDepouilleR").value; }); $("#impDepouille").addEventListener("input", () => { $("#impDepouilleR").value = $("#impDepouille").value; });` et `$("#impEvide").addEventListener("change", () => { const e = $("#impEvide").checked; $("#impDepouille").disabled = e; $("#impDepouilleR").disabled = e; $("#impDepouille").title = e ? "l'évidement ignore la dépouille" : ""; })`. CSS : `.imp-range { display: flex; gap: 6px; align-items: center; } .imp-range input[type=range] { flex: 1; min-width: 0; } .imp-range input[type=number] { width: 58px; }`.

- [ ] **Step 4 : vert** + `node --check`.
- [ ] **Step 5 : commit** — `git commit --only frontend/vectorlab/js/mod-impression.js frontend/vectorlab/qa/impression_ui.test.mjs frontend/vectorlab/vectorlab.css -m "vectorlab R12 : reglage Depouille (°) + curseur dans le dialogue Impression 3D"`

### Task 6 : le planificateur d'aperçu et le déplacement pur (mod-noeudapercu, mod-noeuds)

**Files :** Create `frontend/vectorlab/js/mod-noeudapercu.js`, `frontend/vectorlab/qa/noeudapercu.test.mjs` ; Modify `frontend/vectorlab/js/mod-noeuds.js`

- [ ] **Step 1 : RED** — `qa/noeudapercu.test.mjs` :

```js
// noeudapercu.test.mjs — R12 : l'aperçu des nœuds suit le curseur — un
// planificateur à UN cadre en vol (rAF simulé), vidé au relâchement, et le
// déplacement d'ancres sur des segs SANS clone de document.
import { planificateur } from "../js/mod-noeudapercu.js";
import { noeuds_deplacer_segs, op_noeuds_deplacer } from "../js/mod-noeuds.js";
import { chemin_parser, chemin_serialiser, chemin_ancres } from "../js/mod-doc.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : "")); };
{
  const cadres = [];
  let annules = 0;
  const raf = (fn) => { cadres.push(fn); return cadres.length; };
  const caf = () => { annules++; };
  const P = planificateur({ raf, caf });
  const vus = [];
  P.demander(() => vus.push(1));
  P.demander(() => vus.push(2));
  P.demander(() => vus.push(3));
  ok("trois demandes → UN cadre en vol", cadres.length === 1 && P.enAttente() === true && vus.length === 0);
  cadres[0]();
  ok("le cadre exécute la DERNIÈRE demande seulement", vus.join() === "3" && P.enAttente() === false);
  P.demander(() => vus.push(4));
  const r = P.vider();
  ok("vider() exécute tout de suite la demande en attente et annule le cadre", vus.join() === "3,4" && r === true && annules === 1 && P.enAttente() === false);
  ok("vider() sans demande → false, rien d'exécuté", P.vider() === false && vus.length === 2);
  cadres[1] && cadres[1]();
  ok("un cadre annulé qui tirerait quand même n'exécute rien", vus.length === 2);
}
{
  const segs = chemin_parser("M 0 0 L 100 0 C 120 0 140 20 140 40 L 0 40 Z");
  const s2 = noeuds_deplacer_segs(segs, [1], 5, 7);
  ok("noeuds_deplacer_segs ne mute pas l'entrée", chemin_serialiser(segs) === "M 0 0 L 100 0 C 120 0 140 20 140 40 L 0 40 Z");
  const a = chemin_ancres(s2);
  ok("l'ancre 1 et sa sortante suivent", a[1].x === 105 && a[1].y === 7 && a[1].sortante.x === 125 && a[1].sortante.y === 7, JSON.stringify(a[1]));
  const doc = { calques: [{ id: "c", objets: [{ id: "p", type: "path", d: chemin_serialiser(segs) }] }] };
  op_noeuds_deplacer(doc, "p", [1], 5, 7);
  ok("op_noeuds_deplacer = la même géométrie (même fonction dessous)", doc.calques[0].objets[0].d === chemin_serialiser(s2));
  let refus = 0; try { noeuds_deplacer_segs(segs, [9], 1, 1); } catch { refus++; }
  ok("indice hors chemin refusé", refus === 1);
}
if (echecs.length) { console.error("ECHECS noeudapercu :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA noeudapercu : PASS (10 controles)");
```

- [ ] **Step 2 : RED constaté** — `node frontend/vectorlab/qa/noeudapercu.test.mjs` → `ERR_MODULE_NOT_FOUND`.

- [ ] **Step 3 : implémenter** — `mod-noeuds.js` : 

```js
export function noeuds_deplacer_segs(segs, indices, dx, dy) {
  const out = segs.map((s) => ({ c: s.c, p: s.p.slice() })), noeuds = _porteurs(out);
  for (const i of _indices(indices, noeuds.length)) _decalerAncre(out, noeuds, i, dx, dy);
  return out;
}
export function op_noeuds_deplacer(doc, id, indices, dx, dy) {
  const { objet } = _path(doc, id);
  objet.d = chemin_serialiser(noeuds_deplacer_segs(chemin_parser(objet.d), indices, dx, dy));
}
```

`mod-noeudapercu.js` :

```js
// mod-noeudapercu.js — R12 : pendant un geste de l'outil Nœud, le chemin ET
// l'overlay (ancres, poignées, boîte) suivent le curseur à chaque
// pointermove, au rythme d'UN cadre d'animation ; le relâchement VIDE le
// cadre en attente puis pose exactement ce qui est affiché. Pur en tête
// (planificateur bancable), DOM en bas. Aucun clone de document : les
// gestes travaillent sur les segs parsés une fois au pointerdown.
export function planificateur({ raf, caf }) {
  let fn = null, id = null;
  const tirer = () => { id = null; const f = fn; fn = null; if (f) f(); };
  return {
    demander(f) { fn = f; if (id === null) id = raf(tirer); },
    vider() { if (!fn) { if (id !== null) { caf(id); id = null; } return false; } const f = fn; fn = null; if (id !== null) { caf(id); id = null; } f(); return true; },
    enAttente: () => fn !== null,
  };
}

export function initNoeudApercu(VL) {
  const { etat } = VL;
  const P = planificateur({ raf: (f) => requestAnimationFrame(f), caf: (i) => cancelAnimationFrame(i) });
  let courant = null;    // { id, el, d }
  const pathEl = (id) => { const el = document.querySelector(`#canvasHost [data-objet="${id}"]`); if (!el) return null; return el.tagName === "path" ? el : el.querySelector("path"); };
  VL.apercuNoeuds = {
    debut(id, segs) { courant = { id, el: pathEl(id), d: null }; etat.noeudsApercu = segs || null; },
    poser(segs, d) {
      if (!courant) return;
      courant.d = d;
      P.demander(() => { if (courant && courant.el) courant.el.setAttribute("d", d); etat.noeudsApercu = segs; VL.rendreOverlay(); });
    },
    fin() { P.vider(); const c = courant; courant = null; etat.noeudsApercu = null; return c ? { d: c.d } : null; },
    enCours: () => !!courant,
  };
}
```

- [ ] **Step 4 : vert** — `node frontend/vectorlab/qa/noeudapercu.test.mjs` → PASS (10) ; `run.mjs` tous passent (`noeuds`, `noeuds2`, `noeud` inchangés).
- [ ] **Step 5 : commit** — `git commit --only frontend/vectorlab/js/mod-noeudapercu.js frontend/vectorlab/js/mod-noeuds.js frontend/vectorlab/qa/noeudapercu.test.mjs -m "vectorlab R12 : planificateur d'apercu a un cadre et deplacement d'ancres sans clone (purs)"`

### Task 7 : les cinq gestes passent par l'aperçu, l'overlay lit l'aperçu

**Files :** Modify `frontend/vectorlab/js/core.js`, `mod-tools.js`, `mod-outils2.js`, `mod-noeudui.js`

- [ ] **Step 1 : core.js** — import `initNoeudApercu` ; dans `rendreOverlay`, `const ancres = chemin_ancres(etat.noeudsApercu || chemin_parser(p.d));` ; appeler `initNoeudApercu(VL);` juste APRÈS `initOutils(VL)` (il n'utilise que `etat`, `rendreOverlay`). Ajouter `noeudsApercu: null` à l'état initial.

- [ ] **Step 2 : mod-tools.js** — import `noeuds_deplacer_segs` de `./mod-noeuds.js`. `pointerdown` ancre : `geste = { type: "ancre", id: p.id, i: etat.ancreSel, x0: dx, y0: dy, segs: chemin_parser(p.d), d0: p.d }; VL.apercuNoeuds.debut(p.id, geste.segs); VL.rendreOverlay();`. `pointermove` ancre :

```js
    } else if (geste.type === "ancre") {
      const [ax, ay] = etat.aimantNoeuds === false ? [dx, dy] : VL.aimantePt(dx, dy);
      geste.dxA = ax - geste.x0; geste.dyA = ay - geste.y0;
      const segs = noeuds_deplacer_segs(geste.segs, [geste.i], geste.dxA, geste.dyA);
      geste.d = chemin_serialiser(segs);
      VL.apercuNoeuds.poser(segs, geste.d);
```

`pointerup` ancre : `const fin = VL.apercuNoeuds.fin(); if (fin && fin.d && fin.d !== g.d0) VL.executer((doc) => { const o = doc.calques.flatMap((c) => c.objets).find((x) => x.id === g.id); if (!o) throw new Error("chemin introuvable"); o.d = fin.d; }); else VL.rendre();` (plus de remise du `d` d'avant ; `docContient` reste pour les autres gestes).

- [ ] **Step 3 : mod-outils2.js** — import `noeuds_deplacer_segs` ; `pointerdown` ancres : `geste = { type: "ancres", id: p.id, x0: dx, y0: dy, dxA: 0, dyA: 0, segs: chemin_parser(p.d), d0: p.d }; VL.apercuNoeuds.debut(p.id, geste.segs);` ; `pointermove` : `const segs = noeuds_deplacer_segs(geste.segs, etat.ancresSel, geste.dxA, geste.dyA); geste.d = chemin_serialiser(segs); VL.apercuNoeuds.poser(segs, geste.d);` (importer `chemin_serialiser`) ; `pointerup` : `const fin = VL.apercuNoeuds.fin(); if (fin && fin.d && fin.d !== g.d0) VL.executer((doc) => { const o = doc.calques.flatMap((c) => c.objets).find((x) => x.id === g.id); if (!o) throw new Error("chemin introuvable"); o.d = fin.d; }); else VL.rendre();`.

- [ ] **Step 4 : mod-noeudui.js** — `poserD` disparaît ; à chaque `pointerdown` qui pose un geste : `VL.apercuNoeuds.debut(p.id, segs)` ; `pointermove` : `geste.d = chemin_serialiser(segs); VL.apercuNoeuds.poser(segs, geste.d);` ; `pointerup` : `const fin = VL.apercuNoeuds.fin(); if (fin && fin.d && fin.d !== g.d0) VL.executer(...o.d = fin.d...) else VL.rendreOverlay();`. `surOverlay` (boîte de transformation) : `bbox_ancres(chemin_ancres(etat.noeudsApercu || chemin_parser(p.d)), etat.ancresSel)`.

- [ ] **Step 5 : `node --check`** sur les quatre modules (piège du `//` en fin de ligne à accolade) ; `node frontend/vectorlab/qa/run.mjs` tous passent.

- [ ] **Step 6 : commit** — `git commit --only frontend/vectorlab/js/core.js frontend/vectorlab/js/mod-tools.js frontend/vectorlab/js/mod-outils2.js frontend/vectorlab/js/mod-noeudui.js -m "vectorlab R12 : noeuds, poignees et segments suivent le curseur a chaque pointermove (un cadre, sans clone), le relachement pose ce qui est affiche"`

### Task 8 : preuve en réel (backend du worktree 8799, viewport 1400 × 900)

- [ ] Lancer : `DEEPOTUS_DATA_DIR=<scratchpad>/data PORT=8799 python -m uvicorn app.main:app --host 127.0.0.1 --port 8799` en arrière-plan depuis `backend/` (python embarqué), ouvrir `http://127.0.0.1:8799/vectorlab/` dans le navigateur intégré, `resize_window` 1400 × 900.
- [ ] **Nœuds** : créer un chemin `M 100 100 L 300 100 C 340 100 380 140 380 180 L 100 180 Z` (via `VL.executer(op_ajouter, …)`), outil Nœuds, `etat.aimantNoeuds = false`, dispatcher `pointerdown` sur `.ancre[data-ancre="1"]` puis 6 `pointermove` réels (`left_click_drag` de la souris du navigateur ou `PointerEvent` + attente d'un cadre) : à chaque pas, lire la position du carré `.ancre[data-ancre="1"]` dans `#overlay` (centre du rect, transform rotate) et la comparer à `VL.ecranPt(docPt(curseur))` → **écart ≤ 1 px** ; au `pointerup`, `d` du document === dernier `geste.d` (l'aperçu) ; `etat.noeudsApercu === null` après. Même mesure pour une poignée (`.poignee-noeud`) et un segment (mod-noeudui) et pour deux ancres sélectionnées (mod-outils2). Mesurer aussi qu'aucun `JSON.stringify` du document n'est appelé pendant le `pointermove` (compteur posé sur `JSON.stringify` : 0 pendant les mouvements).
- [ ] **Aperçu 3D** : deux rects de fonds `#ff0000` et `#0000ff` (calque « rouge » et calque « bleu »), Exporter → Impression 3D, mode Calques, Aperçu → relire le blob `#impViewer.src` → GLB : 2 primitives, matériaux `[1,0,0,1]` et `[0,0,1,1]` (linéarisés), `model-viewer.loaded === true`. Mode Logo sur le rect rouge : dépouille 0 → largeur de base = largeur du sommet ; dépouille 30 → largeur du sommet mesurée sur les triangles à z = h < largeur de base de 2·h·tan30 (±0,3) ; dépouille −30 → l'inverse ; « Un STL » → dossier créé, `impression.json.couleur === "#ff0000"`, le 3MF contient `displaycolor="#FF0000FF"` (relire par `/api/print3d/exports` + lecture du zip côté python).
- [ ] 0 erreur console neuve ; `taskkill /PID <8799> /F` à la fin.

### Task 9 : déploiement vers `%LOCALAPPDATA%\DeepotusVideoGen`

- [ ] Pour chaque fichier touché : `git hash-object <installé>` = hash dans `e2c692a` (ou `0c859f6`) — sinon STOP et dire.
- [ ] Sauvegarde `_backup_predeploy_2026-09-18-relooking-r12` (copie des fichiers touchés), copie depuis `git archive HEAD`, re-vérifier hash-object = cible.
- [ ] Pré-vol Python : `python -c "import sys; sys.path.insert(0, r'<installé>\backend'); import app.main; from app.services import print3d; print(print3d.couleur_valide('#ff0000'))"` avec le python embarqué → `#ff0000`. **`print3d.py` et `routes.py` sont du Python : l'utilisateur relance le backend.**

### Task 10 : relevé, mémoire, push

- [ ] Relevé de livraison en tête de ce plan (livré / TDD / prouvé / déployé / reste), commit `--only` du plan.
- [ ] Mémoire : `vectorlab-relooking-affinity.md` (R12 + pièges nouveaux), ligne dans `MEMORY.md`.
- [ ] `git push origin chantier/vectorlab-affinity`.
