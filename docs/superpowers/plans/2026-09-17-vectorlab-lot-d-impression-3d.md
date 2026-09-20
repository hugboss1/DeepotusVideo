# Vectorlab classe Affinity — LOT D : impression 3D, tuiles, logos, texte — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module
> pur). Steps use checkbox (`- [ ]`) syntax for tracking.

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot D ; décision D4 : la chaîne existante `mod-extrude.js` +
> `print3d.py` gagne socle par tuile, relief par terrain, biseau et
> évidement pour les logos, texte vectorisé par `opentype.js` MIT
> vendorisé, lot d'impression ; D7 zéro dépendance payante ; D9 modules
> purs). Branche `chantier/vectorlab-affinity`, après le lot C (`dd030e8`).
> Ce plan est COMMIS avant le code.

> **RELEVÉ DE LIVRAISON (17/09/2026) : LOT D LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ — relance du backend à faire.**
>
> **Livré** (8 commits `830a99a`→`00a46cc`, poussés) : opentype.js 1.3.4
> vendorisé (MIT) ; `mod-solide.js` (retrait par DIFFÉRENCES SUCCESSIVES —
> l'union préalable du bandeau perdait son trou : carré 20 retiré de 2 →
> aire 100 au lieu de 256, mesuré ; biseau en marches de 0,2 mm ; évidement
> à mur ≥ 0,8 mm et plancher, refus parlants « mur » / « forme » ; pièces de
> plateau socle + terrain, y retourné ; GLB minimal POSITION+NORMAL ;
> nomenclature CSV) ; `mod-texte3d.js` (16 polices OFL du dist, commandes →
> `d` canonique, `texte_vers_d` avec crénage et interlettrage) ;
> `op_texte_vectoriser` (même id, même fond, evenodd) ; backend `creer_lot`
> + `POST /print3d/lot` multipart (un STL par pièce, `plateau.3mf`,
> `nomenclature.csv`, `impression.json` lot:true, garde 256 qui avertit) ;
> `mod-impression.js` : dialogue à trois modes (calques / tuiles / logo),
> aperçu 3D `<model-viewer>` du bundle (`loading="eager"`), « Un STL »,
> « Lot par tuile », « Ouvrir le slicer », texte → chemins depuis Apparence
> (sélecteur de police). Le `prompt()` du plan slicer a déménagé, pins
> mis à jour EN LE DISANT.
>
> **TDD tenu** : RED ×4 (modules et `creer_lot` absents, route 405) ; le
> banc solide a démasqué le trou perdu de l'union martinez → différences
> progressives (256 exact, 6 ms). Bancs : node **558 contrôles** (+44 :
> solide 26, texte3d 11, impression_ui 7), pytest `test_print3d` **13**
> (+2), `test_vector_docs` **28** (+1).
>
> **Prouvé en réel** (backend du worktree 8799, données isolées, viewport
> 1400×900) sur le plateau du lot C (38 tuiles) : dialogue ouvert par
> Exporter → Impression 3D, mode Tuiles proposé d'office ; Aperçu en 10 ms
> → **38 pièces, 760 triangles, 165 × 116 × 5 mm, 53 cm³**, hauteurs {5, 2}
> (forêt 3 + socle 2 ; mer 0 + 2), viewer `src` blob, `offsetHeight` 540,
> `model-viewer.loaded === true`, `getDimensions()` = 165,0 × 116,4 × 5
> (égal au bbox calculé) ; **Lot par tuile** → `preuve-lot-c-lot-20260917`,
> 38 pièces, 760 triangles, relu par `/api/print3d/exports` : lot true, 38
> STL, `plateau.3mf`, `nomenclature.csv`. Logo (3 rects unis, h 5) : plein
> 6720 mm³ > biseau 1 mm 6573 > évidé (mur 1,2, plancher 1) 2494 ;
> `extruder_evide` mur 0,3 → « mur ≥ 0.8 mm », mur 6 → « mur trop épais pour
> cette forme » ; `reglages_lire` borne le mur à 0,8 ; « Un STL » →
> `preuve-lot-c-20260917`, 132 triangles. Texte « AB » Anton 120 →
> Apparence → 16 polices → Vectoriser : `path` evenodd, fond gardé, 5
> sous-chemins, `<path>` au DOM 112 px de large, annulable ; Logo → 2 956
> triangles, 0 ignoré ; un texte non vectorisé ajouté → « 1 texte(s)
> ignoré(s) » dit. Pièges : `model-viewer` ne charge pas à l'intersection
> dans un volet caché (→ eager) ; son canvas reste 300×150 sans rAF, la
> preuve est `loaded` + dimensions.
>
> **Déployé** : 7 fichiers du Vectorlab = base lot C (`dd030e8`),
> `print3d.py` et `routes.py` = base lot A (`7c99667`) → sauvegarde
> `_backup_predeploy_2026-09-17c-vectorlab-lotD` → copie depuis `git
> archive 00a46cc` → **72 fichiers = cible**, pré-vol du python embarqué OK
> (`creer_lot` importé). **`print3d.py` et `routes.py` sont du Python : la
> route `/print3d/lot` n'existe qu'après relance — c'est l'utilisateur qui
> relance.**
>
> **Reste** : biseau en marches (pas un chanfrein exact) ; texte vectorisé
> irréversible hors historique ; polices proposées = 16 OFL sûres du dist ;
> le plateau assemblé est un seul maillage 3MF (pas un objet par tuile) ;
> capture d'écran du volet impossible pendant la preuve (rendu différé).

**Goal :** depuis le Vectorlab, imprimer en 3D un plateau de tuiles (socle
+ relief par terrain, un STL par tuile, un 3MF de plateau, une
nomenclature), un logo (biseau des arêtes, évidement à mur minimal
contrôlé) et un texte (glyphes vectorisés en chemins, donc extrudables et
booléens), avec un aperçu 3D avant tir dans le `<model-viewer>` déjà
vendorisé.

**Architecture :** deux modules purs nouveaux — `mod-solide.js` (retrait
d'un multipolygone par différence avec son contour gonflé, biseau en
marches fines, évidement à mur et plancher, pièces d'un plateau, écrivain
GLB minimal pour l'aperçu, nomenclature) et `mod-texte3d.js` (commandes
opentype → `d` canonique, catalogue des polices livrées) — bancables node ;
`opentype.js` vendorisé sous `vendor/` ; `mod-doc.js` gagne
`op_texte_vectoriser` ; le backend gagne `creer_lot` et
`POST /print3d/lot` (multipart, un STL par pièce + nomenclature) ; l'UI
`mod-impression.js` remplace le `prompt()` de l'export 3D par un dialogue
(mode Calques / Tuiles / Logo, hauteurs, socle, biseau, évidement, aperçu
3D, un STL ou un lot, ouverture du slicer). Le `model-viewer` est celui du
bundle (`/assets/model-viewer.min.js`), les polices celles du dist
(`/fonts/*.ttf`, déjà livrées).

**Tech Stack :** vanilla ESM, martinez (vendor), opentype.js 1.3.4 (MIT),
node 24 (`qa/run.mjs`), FastAPI stdlib (`print3d.py`), pytest.

---

## Décisions d'implémentation (tranchées ici, dites au relevé)

- **Biseau en marches fines.** Un chanfrein exact demande de lofter deux
  contours de sommets différents ; à 0,2 mm de couche, un escalier de
  marches de 0,2 mm est indistinguable à l'impression. `extruder_biseau`
  empile des prismes de plus en plus rétrécis (retrait linéaire) sur la
  hauteur du biseau. Robuste sur tout multipolygone, aucune géométrie
  nouvelle.
- **Retrait par différence.** `inset_multi(mz, multi, d)` = multi ∖ (contour
  gonflé de largeur 2d de chacun de ses anneaux) — réutilise la voie
  éprouvée du contour gonflé (mod-bool) et martinez. Un retrait qui vide la
  forme est REFUSÉ en le disant (« mur trop épais pour cette forme »).
- **Épaisseur de mur minimale** : 0,8 mm (deux passes d'une buse 0,4) —
  refus parlant sous ce seuil ; la garde des 256 mm du plateau reste au
  backend (avertit, n'interdit pas).
- **Une tuile = un prisme** de hauteur socle + hauteur du terrain (même
  empreinte, donc un seul solide) ; le plateau assemblé = toutes les tuiles
  concaténées dans un seul 3MF ; le lot = un STL par tuile + le 3MF +
  `nomenclature.csv` (pièce, q, r, terrain, hauteur mm, triangles).
- **Texte → chemins** : `opentype.js` lit une police du dist (OFL,
  déjà livrée) et rend les commandes M/L/C/Q/Z absolues ; l'objet `texte`
  devient un `path` (même id, même fond) par `op_texte_vectoriser` —
  irréversible sauf par l'historique (dit dans le libellé). Polices
  proposées : celles du dist dont la licence est claire (Google Fonts OFL) ;
  écart : les quatre polices de provenance incertaine ne sont pas listées.
- **Aperçu 3D** : GLB minimal écrit côté client (positions + normales, sans
  index — le même triangle-soupe que le STL), affiché dans `<model-viewer>`
  du bundle ; aucun appel backend pour l'aperçu.

---

## Cartographie des fichiers

| Fichier | Rôle |
|---|---|
| `frontend/vectorlab/vendor/opentype.min.js` + `LICENSE-opentype.txt` (créer) | glyphes → contours (T0) |
| `frontend/vectorlab/js/mod-solide.js` (créer) | pur : `inset_multi`, `extruder_biseau`, `extruder_evide`, `plateau_pieces`, `glb_de_triangles`, `nomenclature_csv`, `MUR_MIN_MM` (T1) |
| `frontend/vectorlab/js/mod-texte3d.js` (créer) | pur : `POLICES`, `commandes_vers_d`, `texte_vers_d` (T2) |
| `frontend/vectorlab/js/mod-doc.js` (modifier) | `op_texte_vectoriser` (T2) |
| `backend/app/services/print3d.py`, `backend/app/api/routes.py` (modifier) | `creer_lot`, `POST /print3d/lot` (T3) |
| `frontend/vectorlab/js/mod-impression.js` (créer) | dialogue Impression 3D (T4) |
| `frontend/vectorlab/js/mod-export.js`, `mod-style.js`, `core.js`, `index.html`, `vectorlab.css` (modifier) | délégation, bouton « Vectoriser le texte », inits, dialogue, model-viewer (T4) |
| `frontend/vectorlab/qa/solide.test.mjs`, `texte3d.test.mjs`, `impression_ui.test.mjs` (créer) | bancs node |
| `backend/tests/test_print3d.py`, `test_vector_docs.py` (modifier) | lot, miroirs (T3, T5) |

---

## Task 0 : vendoriser opentype.js

- [ ] `curl -sL -o frontend/vectorlab/vendor/opentype.min.js https://cdn.jsdelivr.net/npm/opentype.js@1.3.4/dist/opentype.min.js`
  et `curl -sL -o frontend/vectorlab/vendor/LICENSE-opentype.txt https://cdn.jsdelivr.net/npm/opentype.js@1.3.4/LICENSE`
  (attendu ~171 001 octets ; licence « The MIT License (MIT) »). Préfixer la
  licence de `opentype.js 1.3.4 — https://github.com/opentypejs/opentype.js`.
- [ ] Node : `node -e "const o=require('./frontend/vectorlab/vendor/opentype.min.js'); const fs=require('fs'); const f=o.parse(fs.readFileSync('frontend/dist/fonts/Anton.ttf').buffer.slice(0)); console.log(f.familyName, f.unitsPerEm)"`
  → `Anton 2048` (ou l'unitsPerEm réel). Le UMD exporte `opentype` en
  CommonJS ; au navigateur `<script src="vendor/opentype.min.js">` pose
  `window.opentype`. Mettre à jour la description de `vendor/package.json`.
- [ ] Commit : `vectorlab : opentype.js 1.3.4 vendorise (MIT) — les glyphes deviennent des chemins (D4/D7)`.

---

## Task 1 : `mod-solide.js` — retrait, biseau, évidement, plateau, GLB, nomenclature

**Files :** Create `frontend/vectorlab/js/mod-solide.js` ; Test `frontend/vectorlab/qa/solide.test.mjs`

- [ ] **Step 1 : banc RED**

```js
// solide.test.mjs — lot D : retrait par différence (martinez vendorisé),
// biseau en marches, évidement à mur minimal, pièces d'un plateau de
// tuiles, GLB minimal, nomenclature. Les volumes se MESURENT (volume_de).
import { createRequire } from "node:module";
import { fournirMartinez } from "../js/mod-bool.js";
import { volume_de, extruder } from "../js/mod-extrude.js";
import { MUR_MIN_MM, inset_multi, extruder_biseau, extruder_evide, plateau_pieces,
         glb_de_triangles, nomenclature_csv } from "../js/mod-solide.js";
import { grille_normaliser, hex_centre } from "../js/mod-grille.js";
import { TERRAINS_DEFAUT } from "../js/mod-doc.js";

const mz = createRequire(import.meta.url)("../vendor/martinez.umd.js");
fournirMartinez(mz);
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (a, b, tol) => Math.abs(a - b) <= tol;
const carre = (x, y, c) => [[x, y], [x + c, y], [x + c, y + c], [x, y + c], [x, y]];
const aireMulti = (mp) => mp.reduce((s, poly) => s + poly.reduce((t, ring, i) => {
  let a = 0; for (let k = 0; k + 1 < ring.length; k++) a += ring[k][0] * ring[k + 1][1] - ring[k + 1][0] * ring[k][1];
  return t + (i === 0 ? Math.abs(a) : -Math.abs(a)) / 2; }, 0), 0);

/* ── retrait ── */
{
  const m = [[carre(0, 0, 20)]];
  const r = inset_multi(mz, m, 2);
  ok("retrait 2 d'un carré 20 → aire ≈ 16² (±3 %)", pres(aireMulti(r), 256, 8), aireMulti(r));
  ok("retrait trop grand → multi vide", inset_multi(mz, m, 11).length === 0);
  ok("retrait 0 → inchangé", pres(aireMulti(inset_multi(mz, m, 0)), 400, 1e-6));
  let refus = 0; try { inset_multi(mz, m, -1); } catch { refus++; }
  ok("retrait négatif refusé", refus === 1);
}
/* ── biseau : le volume est entre le prisme rétréci et le prisme plein ── */
{
  const m = [[carre(0, 0, 20)]];
  const plein = volume_de(extruder(m, 5));                       // 2000
  const tris = extruder_biseau(mz, m, 5, 2, 0.5);                 // biseau 2 mm en marches de 0,5
  const v = volume_de(tris);
  ok("biseau : volume < plein, > prisme à retrait plein", v < plein - 1 && v > volume_de(extruder(inset_multi(mz, m, 2), 5)), `${v} / ${plein}`);
  // borne théorique du chanfrein exact : 20²·3 + ∫ (20-2t)² dt sur 2 mm ≈ 1200 + 592 = 1792 ; les marches surestiment légèrement
  ok("biseau : volume dans [1790, 1900]", v >= 1790 && v <= 1900, v);
  ok("biseau : z max = hauteur", Math.max(...tris.flat().map((p) => p[2])) === 5);
  let refus = 0;
  for (const [h, b] of [[5, 5], [5, -1], [0, 1]]) { try { extruder_biseau(mz, m, h, b, 0.5); } catch { refus++; } }
  ok("biseau refuse b ≥ h, b < 0, h ≤ 0", refus === 3, String(refus));
  ok("biseau 0 = prisme simple", pres(volume_de(extruder_biseau(mz, m, 5, 0, 0.5)), plein, 1e-6));
}
/* ── évidement : mur et plancher ── */
{
  const m = [[carre(0, 0, 20)]];
  const tris = extruder_evide(mz, m, 10, 2, 1);                   // mur 2, plancher 1
  const v = volume_de(tris);
  // plancher 20²·1 = 400 + murs (400 − 256)·9 = 1296 → 1696 (±3 %)
  ok("évidé : volume ≈ 1696", pres(v, 1696, 55), v);
  let refus = 0;
  try { extruder_evide(mz, m, 10, 0.5, 1); } catch (e) { refus += /mur/.test(e.message) ? 1 : 0; }
  try { extruder_evide(mz, m, 10, 11, 1); } catch (e) { refus += /forme/.test(e.message) ? 1 : 0; }
  try { extruder_evide(mz, m, 1, 2, 1); } catch { refus++; }
  ok("évidé refuse mur < MUR_MIN_MM (dit « mur »), mur qui vide la forme (dit « forme »), plancher ≥ h", refus === 3 && MUR_MIN_MM === 0.8, String(refus));
}
/* ── plateau : une pièce par tuile, socle + hauteur du terrain ── */
{
  const g = grille_normaliser({ type: "hex", pas: 40 });
  const doc = { taille: { w: 400, h: 400 }, unites: { dpi: 96 } };
  const tuiles = [{ id: "t1", type: "tuile", q: 0, r: 0, terrain: "plaine" },
                  { id: "t2", type: "tuile", q: 1, r: 0, terrain: "montagne", hauteur_mm: 12 },
                  { id: "t3", type: "tuile", q: 0, r: 1, terrain: "inconnu" }];
  const pieces = plateau_pieces(tuiles, TERRAINS_DEFAUT, g, { socle_mm: 2, sMm: 25.4 / 96 });
  ok("3 pièces, nommées par cellule", pieces.length === 3 && pieces[0].nom === "tuile_0_0" && pieces[1].terrain === "montagne");
  ok("hauteur = socle + terrain ; surcharge de la tuile", pieces[0].hauteur_mm === 4 && pieces[1].hauteur_mm === 14);
  ok("terrain inconnu → socle seul, dit", pieces[2].hauteur_mm === 2 && pieces[2].inconnu === true);
  const s = 40 * 25.4 / 96;                                        // rayon en mm
  const aireHex = 3 * Math.sqrt(3) / 2 * s * s;
  ok("volume de la première pièce = aire hex × 4 mm (±1 %)", pres(volume_de(pieces[0].tris), aireHex * 4, aireHex * 4 * 0.01), volume_de(pieces[0].tris));
  ok("y retourné (plateau y-haut) : centre en y négatif pour r > 0", pieces[2].tris.flat().every((p) => p[1] <= 1e-6) && hex_centre(0, 1, g)[1] > 0);
  ok("chaque pièce porte son centre mm", Array.isArray(pieces[1].centre_mm) && pieces[1].centre_mm.length === 2);
  ok("état vide : aucune tuile → []", plateau_pieces([], TERRAINS_DEFAUT, g, { socle_mm: 2, sMm: 1 }).length === 0);
}
/* ── GLB minimal ── */
{
  const tris = extruder([[carre(0, 0, 10)]], 3);
  const glb = glb_de_triangles(tris);
  const dv = new DataView(glb.buffer, glb.byteOffset, glb.byteLength);
  ok("magic glTF, version 2, longueur totale", dv.getUint32(0, true) === 0x46546C67 && dv.getUint32(4, true) === 2 && dv.getUint32(8, true) === glb.byteLength);
  const lenJson = dv.getUint32(12, true);
  ok("chunk JSON puis BIN", dv.getUint32(16, true) === 0x4E4F534A && dv.getUint32(20 + lenJson + 4, true) === 0x004E4942);
  const json = JSON.parse(new TextDecoder().decode(glb.slice(20, 20 + lenJson)).trim());
  ok("un maillage, POSITION + NORMAL, count = 3 × triangles", json.meshes.length === 1
     && json.accessors[json.meshes[0].primitives[0].attributes.POSITION].count === tris.length * 3
     && json.accessors[json.meshes[0].primitives[0].attributes.NORMAL].count === tris.length * 3, JSON.stringify(json.accessors));
  ok("bornes min/max de la POSITION", JSON.stringify(json.accessors[0].min) === "[0,0,0]" && JSON.stringify(json.accessors[0].max) === "[10,10,3]", JSON.stringify(json.accessors[0]));
  ok("longueurs multiples de 4", lenJson % 4 === 0 && dv.getUint32(20 + lenJson, true) % 4 === 0);
  let refus = 0; try { glb_de_triangles([]); } catch { refus++; }
  ok("aucun triangle → refus", refus === 1);
}
/* ── nomenclature ── */
{
  const csv = nomenclature_csv([{ nom: "tuile_0_0", q: 0, r: 0, terrain: "plaine", hauteur_mm: 4, tris: [1, 2] },
                                { nom: "tuile_1_0", q: 1, r: 0, terrain: "mont;agne", hauteur_mm: 14, tris: [1] }]);
  const lignes = csv.trim().split("\n");
  ok("en-tête + 2 lignes, ; échappé par guillemets", lignes.length === 3 && lignes[0] === "piece;q;r;terrain;hauteur_mm;triangles"
     && lignes[2] === 'tuile_1_0;1;0;"mont;agne";14;1', csv);
}

if (echecs.length) {
  console.error("ECHECS solide :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA solide : PASS (25 controles)");
```

- [ ] **Step 2 : RED** — module introuvable.

- [ ] **Step 3 : `mod-solide.js`**

```js
// mod-solide.js — impression 3D du lot D (D4) : retrait d'un multipolygone
// par DIFFÉRENCE avec son contour gonflé (la voie éprouvée de mod-bool),
// biseau en marches fines (indistinguable d'un chanfrein à 0,2 mm de
// couche), évidement à mur minimal contrôlé, pièces d'un plateau de tuiles
// (socle + relief par terrain), GLB minimal pour l'aperçu, nomenclature.
// PUR : martinez est FOURNI par l'appelant (mz), aucun DOM.
import { extruder } from "./mod-extrude.js";
import { contour_en_multi } from "./mod-bool.js";
import { hex_centre, hex_sommets } from "./mod-grille.js";

export const MUR_MIN_MM = 0.8;          // deux passes d'une buse de 0,4

function _ringsDe(multi) {
  const out = [];
  for (const poly of multi) for (const ring of poly) out.push(ring);
  return out;
}
// retrait d = multi ∖ (contour gonflé de largeur 2d des anneaux)
export function inset_multi(mz, multi, d) {
  if (!(d >= 0)) throw new Error("retrait : distance ≥ 0 requise");
  if (d === 0) return multi;
  let bande = null;
  for (const ring of _ringsDe(multi)) {
    const pts = ring.slice();
    const objet = { type: "path", style: { epaisseur: 2 * d },
      d: "M " + pts.map(([x, y]) => `${x} ${y}`).join(" L ") + " Z" };
    const m = contour_en_multi(objet);
    if (m && m.length) bande = bande ? mz.union(bande, m) : m;
  }
  if (!bande) return multi;
  const r = mz.diff(multi, bande);
  return (r || []).filter((poly) => poly && poly.length && poly[0].length >= 4);
}

export function extruder_biseau(mz, multi, hauteur, biseau, pasMm = 0.2) {
  const h = +hauteur, b = +biseau;
  if (!(h > 0)) throw new Error("biseau : hauteur > 0 requise");
  if (!(b >= 0)) throw new Error("biseau : retrait ≥ 0 requis");
  if (b >= h) throw new Error("biseau : le retrait doit rester sous la hauteur");
  if (b === 0) return extruder(multi, h, 0);
  const n = Math.max(1, Math.ceil(b / Math.max(0.05, +pasMm || 0.2)));
  const dz = b / n;
  const tris = extruder(multi, h - b, 0);
  for (let k = 1; k <= n; k++) {
    const m = inset_multi(mz, multi, (b * k) / n);
    if (!m.length) break;                       // la pointe se ferme d'elle-même
    tris.push(...extruder(m, dz, h - b + (k - 1) * dz));
  }
  return tris;
}

export function extruder_evide(mz, multi, hauteur, mur, plancher) {
  const h = +hauteur, w = +mur, p = +plancher;
  if (!(h > 0)) throw new Error("évidement : hauteur > 0 requise");
  if (!(w >= MUR_MIN_MM)) throw new Error(`évidement : mur ≥ ${MUR_MIN_MM} mm (deux passes de buse)`);
  if (!(p >= 0) || p >= h) throw new Error("évidement : plancher ≥ 0 et sous la hauteur");
  const interieur = inset_multi(mz, multi, w);
  if (!interieur.length) throw new Error("évidement : mur trop épais pour cette forme (elle se vide)");
  const coque = mz.diff(multi, interieur);
  const tris = p > 0 ? extruder(multi, p, 0) : [];
  tris.push(...extruder(coque, h - p, p));
  return tris;
}

/* ── plateau : une pièce par tuile — prisme hex de hauteur socle + terrain ;
   y RETOURNÉ (SVG y-bas → plateau y-haut), mm par sMm ── */
export function plateau_pieces(tuiles, terrains, g, { socle_mm, sMm }) {
  const out = [];
  for (const t of tuiles) {
    if (t.type !== "tuile") continue;
    const fiche = terrains[t.terrain];
    const relief = t.hauteur_mm !== undefined ? +t.hauteur_mm : (fiche ? +fiche.hauteur_mm : 0);
    const hauteur = +socle_mm + relief;
    const [cx, cy] = hex_centre(t.q, t.r, g);
    const ring = hex_sommets(cx, cy, g.pas, g.orientation, g.echelle).map(([x, y]) => [x * sMm, -y * sMm]);
    ring.push([ring[0][0], ring[0][1]]);
    const piece = { nom: `tuile_${t.q}_${t.r}`.replace(/-/g, "m"), id: t.id, q: t.q, r: t.r, terrain: t.terrain,
                    hauteur_mm: hauteur, centre_mm: [cx * sMm, -cy * sMm],
                    tris: hauteur > 0 ? extruder([[ring]], hauteur, 0) : [] };
    if (!fiche) piece.inconnu = true;
    out.push(piece);
  }
  return out;
}

/* ── GLB minimal : une primitive TRIANGLES, POSITION + NORMAL, sans index ── */
export function glb_de_triangles(tris) {
  if (!tris || !tris.length) throw new Error("GLB : aucun triangle");
  const n = tris.length * 3;
  const pos = new Float32Array(n * 3), nrm = new Float32Array(n * 3);
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  let k = 0;
  for (const [a, b, c] of tris) {
    const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
    const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    const l = Math.hypot(nx, ny, nz) || 1; nx /= l; ny /= l; nz /= l;
    for (const p of [a, b, c]) {
      pos[k * 3] = p[0]; pos[k * 3 + 1] = p[1]; pos[k * 3 + 2] = p[2];
      nrm[k * 3] = nx; nrm[k * 3 + 1] = ny; nrm[k * 3 + 2] = nz;
      for (let i = 0; i < 3; i++) { min[i] = Math.min(min[i], p[i]); max[i] = Math.max(max[i], p[i]); }
      k++;
    }
  }
  const binLen = pos.byteLength + nrm.byteLength;
  const json = {
    asset: { version: "2.0", generator: "Deepotus Vectorlab" },
    scene: 0, scenes: [{ nodes: [0] }], nodes: [{ mesh: 0 }],
    meshes: [{ primitives: [{ attributes: { POSITION: 0, NORMAL: 1 }, mode: 4, material: 0 }] }],
    materials: [{ pbrMetallicRoughness: { baseColorFactor: [0.82, 0.78, 0.7, 1], metallicFactor: 0, roughnessFactor: 0.6 } }],
    buffers: [{ byteLength: binLen }],
    bufferViews: [{ buffer: 0, byteOffset: 0, byteLength: pos.byteLength, target: 34962 },
                  { buffer: 0, byteOffset: pos.byteLength, byteLength: nrm.byteLength, target: 34962 }],
    accessors: [{ bufferView: 0, componentType: 5126, count: n, type: "VEC3", min, max },
                { bufferView: 1, componentType: 5126, count: n, type: "VEC3" }],
  };
  let js = JSON.stringify(json);
  while (js.length % 4) js += " ";
  const jsBytes = new TextEncoder().encode(js);
  const total = 12 + 8 + jsBytes.length + 8 + binLen;
  const out = new Uint8Array(total);
  const dv = new DataView(out.buffer);
  dv.setUint32(0, 0x46546C67, true); dv.setUint32(4, 2, true); dv.setUint32(8, total, true);
  dv.setUint32(12, jsBytes.length, true); dv.setUint32(16, 0x4E4F534A, true);
  out.set(jsBytes, 20);
  const offBin = 20 + jsBytes.length;
  dv.setUint32(offBin, binLen, true); dv.setUint32(offBin + 4, 0x004E4942, true);
  out.set(new Uint8Array(pos.buffer), offBin + 8);
  out.set(new Uint8Array(nrm.buffer), offBin + 8 + pos.byteLength);
  return out;
}

export function nomenclature_csv(pieces) {
  const q = (v) => { const s = String(v ?? ""); return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const lignes = ["piece;q;r;terrain;hauteur_mm;triangles"];
  for (const p of pieces) lignes.push([p.nom, p.q, p.r, p.terrain, p.hauteur_mm, (p.tris || []).length].map(q).join(";"));
  return lignes.join("\n") + "\n";
}
```

- [ ] **Step 4 : GREEN** (ajuster les tolérances du banc SEULEMENT après avoir
  vérifié à la main le volume théorique) ; commit
  `vectorlab : mod-solide — retrait par difference, biseau en marches, evidement a mur minimal, pieces de plateau, GLB minimal, nomenclature (lot D, T1)`.

---

## Task 2 : `mod-texte3d.js` + `op_texte_vectoriser`

**Files :** Create `frontend/vectorlab/js/mod-texte3d.js` ; Modify `mod-doc.js` ; Test `frontend/vectorlab/qa/texte3d.test.mjs`

- [ ] **Step 1 : banc RED**

```js
// texte3d.test.mjs — lot D : les glyphes d'une police du dist deviennent
// des chemins du modèle (opentype.js vendorisé, en vrai sur Anton.ttf), et
// op_texte_vectoriser remplace le texte par un path (même id, même fond).
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { POLICES, commandes_vers_d, texte_vers_d } from "../js/mod-texte3d.js";
import { parserDoc, compilerSVG, op_texte_vectoriser, chemin_parser } from "../js/mod-doc.js";

const require = createRequire(import.meta.url);
const opentype = require("../vendor/opentype.min.js");
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
{
  ok("POLICES : ≥ 12 entrées {id, nom, fichier}, fichiers .ttf, ids uniques", POLICES.length >= 12
     && POLICES.every((p) => p.id && p.nom && /\.ttf$/.test(p.fichier)) && new Set(POLICES.map((p) => p.id)).size === POLICES.length);
  ok("POLICES : les quatre de provenance incertaine ne sont PAS listées",
     !POLICES.some((p) => /DistantGalaxy|Hacked|SuperFeel|SuperPencil|PolandKaito|GraffitiBrush|DrippingMarker/.test(p.fichier)));
}
{
  const d = commandes_vers_d([{ type: "M", x: 0, y: 0 }, { type: "L", x: 10, y: 0 }, { type: "Q", x1: 10, y1: 5, x: 10, y: 10 },
                              { type: "C", x1: 8, y1: 12, x2: 2, y2: 12, x: 0, y: 10 }, { type: "Z" }]);
  ok("commandes → d canonique absolu", d === "M 0 0 L 10 0 Q 10 5 10 10 C 8 12 2 12 0 10 Z", d);
  let refus = 0; try { commandes_vers_d([{ type: "H", x: 1 }]); } catch { refus++; }
  ok("commande inconnue refusée", refus === 1);
}
{
  const buf = readFileSync(new URL("../../dist/fonts/Anton.ttf", import.meta.url));
  const font = opentype.parse(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
  const d = texte_vers_d(font, "A", 100, 20, 120);
  const segs = chemin_parser(d);
  ok("« A » : un chemin fermé avec un trou (2 × M), que M/L/Q/Z", (d.match(/M /g) || []).length === 2 && segs.every((s) => "MLQCZ".includes(s.c)));
  let minX = 1e9, maxX = -1e9, maxY = -1e9;
  for (const s of segs) for (let k = 0; k < s.p.length; k += 2) { minX = Math.min(minX, s.p[k]); maxX = Math.max(maxX, s.p[k]); maxY = Math.max(maxY, s.p[k + 1]); }
  ok("posé à x=20, ligne de base y=120, largeur < corps", minX >= 19 && maxX < 120 && maxY <= 121, [minX, maxX, maxY].join(" "));
  const d2 = texte_vers_d(font, "AA", 100, 0, 0, 10);
  ok("deux lettres, interlettrage : plus large", (() => { let m = -1e9; for (const s of chemin_parser(d2)) for (let k = 0; k < s.p.length; k += 2) m = Math.max(m, s.p[k]); return m > maxX - 20 + 60; })());
  ok("texte vide → d vide", texte_vers_d(font, "", 100, 0, 0) === "");
  // la commande du modèle
  const doc = { v: 1, nom: "T", taille: { w: 400, h: 200 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
    { id: "t1", type: "texte", x: 20, y: 120, contenu: "A", style: { fond: "#0047AB", police: "Anton", corps: 100 } }] }] };
  op_texte_vectoriser(doc, "t1", d);
  const o = doc.calques[0].objets[0];
  ok("op_texte_vectoriser : même id, type path, fond gardé, evenodd, plus de contenu", o.id === "t1" && o.type === "path" && o.d === d
     && o.style.fond === "#0047AB" && o.style.regle === "evenodd" && o.contenu === undefined && o.style.police === undefined, JSON.stringify(o));
  ok("le document compilé passe", compilerSVG(parserDoc(doc)).includes('data-objet="t1"'));
  let refus = 0;
  try { op_texte_vectoriser(doc, "t1", d); } catch { refus++; }           // déjà un path
  try { op_texte_vectoriser(doc, "zz", d); } catch { refus++; }
  try { op_texte_vectoriser({ ...doc, calques: [{ id: "c", verrou: false, objets: [{ id: "t", type: "texte", contenu: "x" }] }] }, "t", ""); } catch { refus++; }
  ok("refus : pas un texte, introuvable, d vide", refus === 3, String(refus));
}
if (echecs.length) {
  console.error("ECHECS texte3d :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA texte3d : PASS (11 controles)");
```

- [ ] **Step 2 : RED** — module introuvable.

- [ ] **Step 3 : `mod-texte3d.js`**

```js
// mod-texte3d.js — lot D : le texte devient des CHEMINS (D4) par
// opentype.js vendorisé — donc extrudable et booléen. PUR : la police est
// fournie (opentype.Font), les commandes deviennent un d canonique.
import { chemin_parser, chemin_serialiser } from "./mod-doc.js";

// les polices du dist dont la licence est claire (Google Fonts, OFL) —
// écart dit : les polices de provenance incertaine ne sont pas proposées
export const POLICES = [
  { id: "anton", nom: "Anton", fichier: "Anton.ttf" },
  { id: "archivo", nom: "Archivo Black", fichier: "ArchivoBlack.ttf" },
  { id: "bebas", nom: "Bebas Neue", fichier: "BebasNeue.ttf" },
  { id: "bungee", nom: "Bungee", fichier: "Bungee.ttf" },
  { id: "cinzel", nom: "Cinzel", fichier: "Cinzel.ttf" },
  { id: "plex", nom: "IBM Plex Sans", fichier: "IBMPlexSans.ttf" },
  { id: "inter", nom: "Inter", fichier: "Inter.ttf" },
  { id: "jetbrains", nom: "JetBrains Mono", fichier: "JetBrainsMono.ttf" },
  { id: "monoton", nom: "Monoton", fichier: "Monoton.ttf" },
  { id: "pacifico", nom: "Pacifico", fichier: "Pacifico.ttf" },
  { id: "marker", nom: "Permanent Marker", fichier: "PermanentMarker.ttf" },
  { id: "press", nom: "Press Start 2P", fichier: "PressStart2P.ttf" },
  { id: "righteous", nom: "Righteous", fichier: "Righteous.ttf" },
  { id: "grotesk", nom: "Space Grotesk", fichier: "SpaceGrotesk.ttf" },
  { id: "staatliches", nom: "Staatliches", fichier: "Staatliches.ttf" },
  { id: "abril", nom: "Abril Fatface", fichier: "AbrilFatface.ttf" },
];

export function commandes_vers_d(cmds) {
  const parts = [];
  for (const c of cmds) {
    switch (c.type) {
      case "M": parts.push(`M ${c.x} ${c.y}`); break;
      case "L": parts.push(`L ${c.x} ${c.y}`); break;
      case "Q": parts.push(`Q ${c.x1} ${c.y1} ${c.x} ${c.y}`); break;
      case "C": parts.push(`C ${c.x1} ${c.y1} ${c.x2} ${c.y2} ${c.x} ${c.y}`); break;
      case "Z": parts.push("Z"); break;
      default: throw new Error(`glyphe : commande ${c.type} inconnue`);
    }
  }
  return parts.length ? chemin_serialiser(chemin_parser(parts.join(" "))) : "";
}

// x, y = origine de la ligne de base (comme <text>) ; taille = corps en px
export function texte_vers_d(font, texte, taille, x, y, interlettrage = 0) {
  const s = String(texte || "");
  if (!s) return "";
  const path = font.getPath(s, x, y, taille, { kerning: true, letterSpacing: interlettrage / taille });
  return commandes_vers_d(path.commands);
}
```

`mod-doc.js`, après `op_vectoriser_poser` :

```js
/* ── texte → chemins (lot D) : l'objet garde son id et son fond, perd sa
   fonte ; les glyphes à trous se peignent en evenodd ── */
export function op_texte_vectoriser(doc, id, d) {
  if (typeof d !== "string" || !d.trim()) throw new Error("vectoriser : chemin vide (texte vide ou police muette)");
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const i = c.objets.findIndex((o) => o.id === id);
    if (i < 0) continue;
    const o = c.objets[i];
    if (o.type !== "texte") throw new Error(`${id}: pas un texte`);
    const s = { ...(o.style || {}) };
    for (const k of ["police", "corps", "graisse", "interlettrage"]) delete s[k];
    if (!s.fond || s.fond === "none") s.fond = s.contour || "#1F1512";
    c.objets[i] = { id: o.id, type: "path", d: chemin_serialiser(chemin_parser(d)),
                    style: { ...s, regle: "evenodd" }, ...(o.transform ? { transform: o.transform } : {}) };
    return o.id;
  }
  throw new Error(`texte introuvable (ou calque verrouillé): ${id}`);
}
```

- [ ] **Step 4 : GREEN** ; commit `vectorlab : texte vers chemins par opentype.js — POLICES du dist, commandes → d canonique, op_texte_vectoriser (lot D, T2)`.

---

## Task 3 : backend — `creer_lot` et `POST /print3d/lot`

**Files :** Modify `backend/app/services/print3d.py`, `backend/app/api/routes.py` ; Test `backend/tests/test_print3d.py`

- [ ] **Step 1 : tests RED (dans test_print3d.py, section F)**

```python
# ── F. lot D : le LOT d'impression — un STL par pièce, un 3MF de plateau, nomenclature ──

def test_le_lot_ecrit_une_piece_par_stl_un_plateau_et_la_nomenclature():
    from app.services import print3d as P3
    base = pathlib.Path(_tmp, "print3d-lot")
    pieces = [("tuile_0_0", _deux_triangles()), ("tuile_1_0", _deux_triangles())]
    nomen = "piece;q;r;terrain;hauteur_mm;triangles\ntuile_0_0;0;0;plaine;4;2\ntuile_1_0;1;0;mer;2;2\n"
    out = P3.creer_lot(base, "Plateau test", pieces, nomen, source="vectorlab")
    d = base / out["dossier"]
    assert out["pieces"] == 2 and sorted(p.name for p in d.glob("*.stl")) == ["tuile_0_0.stl", "tuile_1_0.stl"]
    assert (d / "plateau.3mf").is_file() and (d / "nomenclature.csv").read_text("utf-8") == nomen
    meta = _json.loads((d / "impression.json").read_text("utf-8"))
    assert meta["lot"] is True and meta["pieces"] == 2 and meta["triangles"] == 4
    # le 3MF de plateau réunit TOUTES les pièces
    assert len(P3.lire_stl((d / "tuile_0_0.stl").read_bytes())) == 2
    # la liste des exports voit le lot
    assert any(e["dossier"] == out["dossier"] and e.get("lot") for e in P3.lister_exports(base))
    # refus : aucune pièce ; nom de pièce hors patron (traversée)
    with pytest.raises(ValueError):
        P3.creer_lot(base, "Vide", [], "", source="banc")
    with pytest.raises(ValueError):
        P3.creer_lot(base, "Mauvais", [("../x", _deux_triangles())], "", source="banc")


def test_la_route_lot_recoit_le_multipart():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services import print3d as P3
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        stl = P3.ecrire_stl(_deux_triangles())
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/print3d/lot", params={"nom": "Plateau banc", "source": "vectorlab"},
                             files=[("pieces", ("tuile_0_0.stl", stl, "application/octet-stream")),
                                    ("pieces", ("tuile_1_0.stl", stl, "application/octet-stream"))],
                             data={"nomenclature": "piece;q;r;terrain;hauteur_mm;triangles\n"})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["pieces"] == 2 and d["triangles"] == 4 and "dossier" in d
            base = pathlib.Path(_tmp, "print3d")
            assert (base / d["dossier"] / "plateau.3mf").is_file()
            # sans pièce → 400 ; un STL illisible → 400
            r = await c.post("/api/print3d/lot", params={"nom": "x"}, data={"nomenclature": ""})
            assert r.status_code in (400, 422)
            r = await c.post("/api/print3d/lot", params={"nom": "x"},
                             files=[("pieces", ("a.stl", b"pas un stl", "application/octet-stream"))],
                             data={"nomenclature": ""})
            assert r.status_code == 400

    asyncio.run(scenario())
```

- [ ] **Step 2 : RED** (`AttributeError: creer_lot`).

- [ ] **Step 3 : service**

```python
_NOM_PIECE = re.compile(r"[A-Za-z0-9_-]{1,60}")


def creer_lot(base, nom, pieces, nomenclature, source=""):
    """Lot D : `<slug>-lot-<date>/` avec UN STL PAR PIÈCE (`<piece>.stl`), le
    plateau assemblé `plateau.3mf` (toutes les pièces réunies), la
    `nomenclature.csv` fournie par le client et `impression.json`
    (`lot: true`). Les pièces arrivent en mm — aucune mise à l'échelle."""
    import datetime as _dt
    from pathlib import Path
    if not pieces:
        raise ValueError("lot : aucune pièce")
    for nom_piece, _ in pieces:
        if not _NOM_PIECE.fullmatch(str(nom_piece)):
            raise ValueError(f"lot : nom de pièce invalide « {nom_piece} » ([A-Za-z0-9_-])")
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    jour = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    racine = f"{_slug(nom)}-lot-{jour}"
    dossier = base / racine
    n = 2
    while dossier.exists():
        dossier = base / f"{racine}-{n}"
        n += 1
    dossier.mkdir()
    tous = []
    for nom_piece, tris in pieces:
        (dossier / f"{nom_piece}.stl").write_bytes(ecrire_stl(tris))
        tous.extend(tris)
    (dossier / "plateau.3mf").write_bytes(ecrire_3mf(tous, nom=nom))
    (dossier / "nomenclature.csv").write_text(str(nomenclature or ""), "utf-8")
    bb = bbox(tous)
    plus_grande = max(b[1] - b[0] for b in bb)
    avertissement = None
    if plus_grande > 256.0 + 1e-6:
        avertissement = (f"{plus_grande:.0f} mm dépasse le plateau de la Centauri Carbon 2 "
                         "(256 mm) — imprimer les pièces séparément (un STL par tuile)")
    meta = {"nom": str(nom), "source": str(source), "lot": True, "pieces": len(pieces),
            "stl": [f"{p}.stl" for p, _ in pieces], "mf3": "plateau.3mf",
            "nomenclature": "nomenclature.csv", "triangles": len(tous),
            "avertissement": avertissement,
            "cree": _dt.datetime.now(_dt.timezone.utc).isoformat()}
    (dossier / "impression.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    out = {"dossier": dossier.name, "pieces": len(pieces), "mf3": "plateau.3mf", "triangles": len(tous)}
    if avertissement:
        out["avertissement"] = avertissement
    return out
```

(`import re` en tête si absent.) Route, après `print3d_from_stl` :

```python
@router.post("/print3d/lot")
async def print3d_lot(nom: str = "plateau", source: str = "vectorlab",
                      pieces: list[UploadFile] = File(default=[]),
                      nomenclature: str = Form(default="")):
    """Lot D : multipart — un STL binaire par pièce (`pieces`, nom de fichier
    = nom de pièce) + la nomenclature CSV ; écrit un STL par pièce, le 3MF
    de plateau et la nomenclature. Pièces en mm, jamais remises à l'échelle."""
    from app.services import print3d as P3
    if not pieces:
        raise HTTPException(400, "lot : aucune pièce")
    lues = []
    for up in pieces:
        octets = await up.read()
        try:
            tris = P3.lire_stl(octets)
        except ValueError as e:
            raise HTTPException(400, f"{up.filename}: {e}")
        lues.append((Path(up.filename or "piece").stem, tris))
    try:
        return await asyncio.to_thread(P3.creer_lot, _print3d_base(), str(nom)[:80], lues,
                                       nomenclature, str(source)[:40])
    except ValueError as e:
        raise HTTPException(400, str(e))
```

- [ ] **Step 4 : GREEN** (`pytest tests/test_print3d.py -q`) ; commit
  `print3d : le lot d'impression — un STL par piece, plateau.3mf, nomenclature.csv, POST /print3d/lot multipart (lot D, T3)`.

---

## Task 4 : UI — `mod-impression.js`, texte vectorisé, délégation, model-viewer

**Files :** Create `frontend/vectorlab/js/mod-impression.js` ; Modify `mod-export.js`, `mod-style.js`, `core.js`, `index.html`, `vectorlab.css` ; Test `frontend/vectorlab/qa/impression_ui.test.mjs`

- [ ] **Step 1 : banc RED de la logique pure**

```js
// impression_ui.test.mjs — lot D : la logique pure du dialogue d'impression
// (lecture des réglages bornés, hauteurs par calque, libellé de résumé).
import { reglages_lire, hauteurs_par_calque, resume_impression } from "../js/mod-impression.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : "")); };
{
  const r = reglages_lire({ mode: "logo", hauteur: "5", socle: "2", biseau: "1", evide: true, mur: "1.2", plancher: "1" });
  ok("réglages bornés, nombres", r.mode === "logo" && r.hauteur === 5 && r.biseau === 1 && r.evide === true && r.mur === 1.2, JSON.stringify(r));
  const b = reglages_lire({ mode: "x", hauteur: "-3", socle: "abc", biseau: "9", mur: "0.1", plancher: "50" });
  ok("valeurs folles : mode calques, hauteur 3 par défaut, socle 0, biseau borné sous la hauteur, mur ≥ 0,8, plancher sous la hauteur",
     b.mode === "calques" && b.hauteur === 3 && b.socle === 0 && b.biseau < b.hauteur && b.mur === 0.8 && b.plancher < b.hauteur, JSON.stringify(b));
}
{
  const h = hauteurs_par_calque("3, contours=5, Verres = 2", [{ nom: "verres" }, { nom: "contours" }, { nom: "autre" }]);
  ok("hauteur globale + surcharges par nom (insensible à la casse)", h.globale === 3 && h.parCalque.verres === 2 && h.parCalque.contours === 5 && h.parCalque.autre === undefined, JSON.stringify(h));
  let refus = 0; try { hauteurs_par_calque("abc", []); } catch { refus++; }
  ok("sans hauteur globale valide → refus", refus === 1);
}
{
  const s = resume_impression({ triangles: 1200, bbox_mm: [[0, 50], [0, 30], [0, 4]], pieces: 7, ignores: 2 });
  ok("résumé : dimensions mm arrondies, pièces, triangles, ignorés dits", s.includes("50 × 30 × 4 mm") && s.includes("7 pièce") && s.includes("1200") && s.includes("2 texte"), s);
}
if (echecs.length) { console.error("ECHECS impression_ui :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA impression_ui : PASS (5 controles)");
```

- [ ] **Step 2 : `mod-impression.js`**

```js
// mod-impression.js — lot D : le dialogue « Impression 3D » du Vectorlab.
// Trois modes : CALQUES (l'extrusion par calque du plan slicer, hauteurs
// mm, surcharge « nom=mm »), TUILES (une pièce par tuile : socle + relief
// du terrain ; lot = un STL par tuile + plateau.3mf + nomenclature),
// LOGO (la sélection unie, biseau en marches, évidement à mur minimal).
// Aperçu 3D AVANT tir : GLB minimal écrit ici, montré dans <model-viewer>
// du bundle. Logique PURE en tête (banc node).
import { aplatir_objet, contour_en_multi, versMulti } from "./mod-bool.js";
import { extruder, stl_binaire, volume_de } from "./mod-extrude.js";
import { MUR_MIN_MM, extruder_biseau, extruder_evide, plateau_pieces, glb_de_triangles,
         nomenclature_csv } from "./mod-solide.js";
import { terrains_de } from "./mod-doc.js";
import { hex_centre, hex_sommets } from "./mod-grille.js";

/* ── pur ── */
const num = (v, def) => { const n = parseFloat(String(v).replace(",", ".")); return Number.isFinite(n) ? n : def; };
export function reglages_lire(f) {
  const mode = ["calques", "tuiles", "logo"].includes(f.mode) ? f.mode : "calques";
  const hauteur = Math.max(0.2, num(f.hauteur, 3) > 0 ? num(f.hauteur, 3) : 3);
  const socle = Math.max(0, num(f.socle, 0));
  const biseau = Math.min(Math.max(0, num(f.biseau, 0)), Math.max(0, hauteur - 0.2));
  const mur = Math.max(MUR_MIN_MM, num(f.mur, 1.2));
  const plancher = Math.min(Math.max(0, num(f.plancher, 1)), Math.max(0, hauteur - 0.2));
  return { mode, hauteur, socle, biseau, evide: !!f.evide, mur, plancher, pas: 0.2 };
}
export function hauteurs_par_calque(texte, calques) {
  let globale = null; const parCalque = {};
  for (const part of String(texte || "").split(",")) {
    const t = part.trim(); if (!t) continue;
    const m = /^(.+?)=([0-9.,]+)$/.exec(t);
    if (m) parCalque[m[1].trim().toLowerCase()] = num(m[2], 0);
    else if (globale === null && num(t, 0) > 0) globale = num(t, 0);
  }
  if (!(globale > 0)) throw new Error("hauteur en mm invalide (ex. « 3, contours=5 »)");
  const out = {};
  for (const c of calques) { const k = (c.nom || "").toLowerCase(); if (parCalque[k] !== undefined) out[k] = parCalque[k]; }
  return { globale, parCalque: out };
}
export function resume_impression({ triangles, bbox_mm, pieces, ignores }) {
  const dim = bbox_mm.map(([a, b]) => Math.round(b - a)).join(" × ") + " mm";
  let s = `${dim} · ${pieces} pièce(s) · ${triangles} triangles`;
  if (ignores) s += ` · ${ignores} texte(s) ignoré(s) (vectoriser d'abord)`;
  return s;
}
function bboxDe(tris) {
  const b = [[Infinity, -Infinity], [Infinity, -Infinity], [Infinity, -Infinity]];
  for (const t of tris) for (const p of t) for (let i = 0; i < 3; i++) { b[i][0] = Math.min(b[i][0], p[i]); b[i][1] = Math.max(b[i][1], p[i]); }
  return b;
}

/* ── DOM ── */
export function initImpression(VL) {
  const { $, etat } = VL;
  const dlg = $("#impDlg");
  let courant = null;            // { pieces:[{nom, tris, ...}], ignores, glbUrl }

  const mz = () => { if (!window.martinez) throw new Error("martinez indisponible (vendor non chargé)"); return window.martinez; };
  const sMm = () => 25.4 / ((etat.doc.unites && etat.doc.unites.dpi) || 96);
  const enMm = (mp) => mp.map((poly) => poly.map((ring) => ring.map(([x, y]) => [x * sMm(), -y * sMm()])));

  function multiDe(objets, compte) {
    let mp = null;
    for (const o of objets) {
      if (o.type === "texte") { compte.ignores++; continue; }
      if (o.type === "tuile") {
        const g = VL.grilleDoc() && VL.grilleDoc().type === "hex" ? VL.grilleDoc() : { pas: 32, orientation: "pointe", origine: [0, 0], echelle: [1, 1] };
        const [cx, cy] = hex_centre(o.q, o.r, g);
        const ring = hex_sommets(cx, cy, g.pas, g.orientation, g.echelle); ring.push([ring[0][0], ring[0][1]]);
        const m = [[ring]]; mp = mp ? mz().union(mp, m) : m; continue;
      }
      let m = null;
      try {
        const fond = o.style && o.style.fond;
        m = (fond && fond !== "none") ? versMulti(aplatir_objet(o)) : contour_en_multi(o);
      } catch (e) { compte.ignores++; continue; }
      if (!m || !m.length) continue;
      mp = mp ? mz().union(mp, m) : m;
    }
    return mp;
  }

  function construire(r) {
    const doc = etat.doc, compte = { ignores: 0 };
    const pieces = [];
    if (r.mode === "tuiles") {
      const g = VL.grilleDoc();
      if (!g || g.type !== "hex") throw new Error("tuiles : le document n'a pas de grille hexagonale");
      const tuiles = doc.calques.filter((c) => c.visible).flatMap((c) => c.objets.filter((o) => o.type === "tuile"));
      if (!tuiles.length) throw new Error("tuiles : aucune tuile visible");
      pieces.push(...plateau_pieces(tuiles, terrains_de(doc), g, { socle_mm: r.socle, sMm: sMm() }).filter((p) => p.tris.length));
    } else if (r.mode === "logo") {
      const sel = etat.selection.length ? etat.selection.map((id) => VL.objetDe(id)).filter(Boolean).map((t) => t.objet)
                : doc.calques.filter((c) => c.visible).flatMap((c) => c.objets);
      const mp = multiDe(sel, compte);
      if (!mp || !mp.length) throw new Error("logo : rien d'extrudable (sélection vide ou textes non vectorisés)");
      const mm = enMm(mp);
      const tris = r.evide ? extruder_evide(mz(), mm, r.hauteur, r.mur, r.plancher)
                 : extruder_biseau(mz(), mm, r.hauteur, r.biseau, r.pas);
      pieces.push({ nom: "logo", tris, hauteur_mm: r.hauteur });
    } else {
      const h = hauteurs_par_calque($("#impHauteurs").value, doc.calques);
      for (const c of doc.calques) {
        if (!c.visible) continue;
        const hc = h.parCalque[(c.nom || "").toLowerCase()] ?? h.globale;
        if (!(hc > 0)) continue;
        const mp = multiDe(c.objets, compte);
        if (!mp || !mp.length) continue;
        pieces.push({ nom: (c.nom || c.id).replace(/[^A-Za-z0-9_-]+/g, "_").slice(0, 40) || c.id, tris: extruder(enMm(mp), hc, 0), hauteur_mm: hc });
      }
      if (!pieces.length) throw new Error("rien d'extrudable (calques visibles vides ?)");
    }
    const tous = pieces.flatMap((p) => p.tris);
    return { pieces, ignores: compte.ignores, tous, bbox: bboxDe(tous) };
  }

  function lire() {
    return reglages_lire({ mode: $("#impMode").value, hauteur: $("#impHauteur").value, socle: $("#impSocle").value,
      biseau: $("#impBiseau").value, evide: $("#impEvide").checked, mur: $("#impMur").value, plancher: $("#impPlancher").value });
  }
  function apercu() {
    const r = lire();
    const c = construire(r);
    if (courant && courant.glbUrl) URL.revokeObjectURL(courant.glbUrl);
    courant = { ...c, r, glbUrl: URL.createObjectURL(new Blob([glb_de_triangles(c.tous)], { type: "model/gltf-binary" })) };
    const mv = $("#impViewer");
    mv.setAttribute("src", courant.glbUrl);
    $("#impResume").textContent = resume_impression({ triangles: c.tous.length, bbox_mm: c.bbox, pieces: c.pieces.length, ignores: c.ignores })
      + ` · volume ${Math.round(volume_de(c.tous) / 1000)} cm³`;
    const large = Math.max(...c.bbox.map(([a, b]) => b - a));
    $("#impGarde").textContent = large > 256 ? `⚠ ${Math.round(large)} mm dépasse le plateau de 256 mm — le lot par tuile imprime pièce à pièce` : "";
    $("#impUnStl").disabled = false; $("#impLot").disabled = r.mode !== "tuiles";
  }
  async function unStl() {
    if (!courant) apercu();
    const stl = stl_binaire(courant.tous);
    const ps = new URLSearchParams({ nom: etat.meta.name, source: "vectorlab", etanche: "inconnue" });
    const r = await fetch("/api/print3d/from-stl?" + ps, { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: stl });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    apresExport(d);
  }
  async function lot() {
    if (!courant) apercu();
    const fd = new FormData();
    for (const p of courant.pieces) fd.append("pieces", new File([stl_binaire(p.tris)], p.nom + ".stl", { type: "application/octet-stream" }));
    fd.append("nomenclature", nomenclature_csv(courant.pieces));
    const ps = new URLSearchParams({ nom: etat.meta.name, source: "vectorlab" });
    const r = await fetch("/api/print3d/lot?" + ps, { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    apresExport(d);
  }
  function apresExport(d) {
    $("#impResume").textContent = `dossier d'impression : ${d.dossier} (${d.triangles} triangles${d.pieces ? `, ${d.pieces} pièces` : ""})`
      + (d.avertissement ? " — " + d.avertissement : "");
    $("#impOuvrir").disabled = false; $("#impOuvrir").dataset.dossier = d.dossier;
    VL.toast(`export écrit : ${d.dossier}`);
  }
  async function ouvrir() {
    const dossier = $("#impOuvrir").dataset.dossier; if (!dossier) return;
    const o = await fetch("/api/print3d/open", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ dossier }) });
    const od = await o.json().catch(() => ({}));
    if (!o.ok) throw new Error(od.detail || o.statusText);
    VL.toast(`slicer ouvert (${od.mode})`);
  }
  function fermer() { dlg.classList.add("hidden"); dlg.innerHTML = ""; if (courant && courant.glbUrl) URL.revokeObjectURL(courant.glbUrl); courant = null; }

  VL.impression = (modeInitial) => {
    const doc = etat.doc, dpi = (doc.unites && doc.unites.dpi) || 96, s = 25.4 / dpi;
    const aHex = !!(doc.grille && doc.grille.type === "hex") && doc.calques.some((c) => c.objets.some((o) => o.type === "tuile"));
    const mode = modeInitial || (aHex ? "tuiles" : (etat.selection.length ? "logo" : "calques"));
    dlg.innerHTML = `<div class="vl-dlg-boite imp-boite">
      <div class="vl-dlg-tete"><b>Impression 3D</b><span class="imp-doc">${Math.round(doc.taille.w * s)} × ${Math.round(doc.taille.h * s)} mm à ${dpi} dpi · plateau 256 mm</span><span class="spacer"></span><button id="impFermer" title="Fermer">✕</button></div>
      <div class="imp-corps">
        <div class="imp-regles">
          <label>Mode <select id="impMode">
            <option value="calques"${mode === "calques" ? " selected" : ""}>Calques (relief par calque)</option>
            <option value="tuiles"${mode === "tuiles" ? " selected" : ""}${aHex ? "" : " disabled"}>Tuiles (socle + terrain, lot)</option>
            <option value="logo"${mode === "logo" ? " selected" : ""}>Logo (sélection unie : biseau / évidement)</option></select></label>
          <label class="imp-calques">Hauteurs (mm, « nom=mm ») <input id="impHauteurs" type="text" value="3"/></label>
          <label class="imp-logo">Hauteur (mm) <input id="impHauteur" type="number" step="0.1" min="0.2" value="5"/></label>
          <label class="imp-tuiles">Socle (mm) <input id="impSocle" type="number" step="0.1" min="0" value="2"/></label>
          <label class="imp-logo">Biseau (mm) <input id="impBiseau" type="number" step="0.1" min="0" value="0.6"/></label>
          <label class="imp-logo"><input type="checkbox" id="impEvide"/> évider (mur ≥ ${MUR_MIN_MM} mm)</label>
          <label class="imp-logo">Mur (mm) <input id="impMur" type="number" step="0.1" min="${MUR_MIN_MM}" value="1.2"/></label>
          <label class="imp-logo">Plancher (mm) <input id="impPlancher" type="number" step="0.1" min="0" value="1"/></label>
          <button id="impApercu" class="primaire">Aperçu 3D</button>
          <p id="impResume" class="tr-etat">réglez, puis Aperçu</p><p id="impGarde" class="imp-garde"></p>
        </div>
        <model-viewer id="impViewer" camera-controls auto-rotate shadow-intensity="1" exposure="1" style="flex:1;min-height:360px;background:#fff;border-radius:6px"></model-viewer>
      </div>
      <div class="tr-pied"><button id="impUnStl" disabled title="Un seul STL + 3MF (tout le rendu en une pièce)">Un STL</button>
        <button id="impLot" disabled title="Un STL par tuile + plateau.3mf + nomenclature.csv">Lot par tuile</button>
        <button id="impOuvrir" disabled title="Ouvrir le .3mf dans le slicer">Ouvrir le slicer</button></div></div>`;
    dlg.classList.remove("hidden");
    const majMode = () => { const m = $("#impMode").value; dlg.querySelectorAll(".imp-calques").forEach((e) => e.style.display = m === "calques" ? "" : "none");
      dlg.querySelectorAll(".imp-logo").forEach((e) => e.style.display = m === "logo" ? "" : "none");
      dlg.querySelectorAll(".imp-tuiles").forEach((e) => e.style.display = m === "tuiles" ? "" : "none"); };
    majMode();
    const garde = (fn) => () => Promise.resolve().then(fn).catch((e) => { $("#impResume").textContent = e.message; VL.toast(e.message, true); });
    $("#impMode").addEventListener("change", majMode);
    $("#impApercu").addEventListener("click", garde(apercu));
    $("#impUnStl").addEventListener("click", garde(unStl));
    $("#impLot").addEventListener("click", garde(lot));
    $("#impOuvrir").addEventListener("click", garde(ouvrir));
    $("#impFermer").addEventListener("click", fermer);
  };
}
```

- [ ] **Step 3 : câblages**

  - `mod-export.js` : `imprimer3D` devient `function imprimer3D() { if (VL.impression) VL.impression(); }` ; retirer les imports devenus inutiles (`aplatir_objet`, `contour_en_multi`, `versMulti`, `extruder`, `stl_binaire`) ; commentaire de tête : la voie 3D vit dans `mod-impression.js`.
  - `mod-style.js` : pour un `texte` sélectionné, une rangée
    `<div class="ap-ligne"><span>3D</span><select id="apPolice3d">…POLICES…</select><button id="apVectoriserTexte" title="Remplace le texte par ses contours (police du dist, opentype.js) — extrudable et booléen ; annulable par l'historique">Vectoriser</button></div>` ;
    clic → `VL.vectoriserTexte(id, policeId)`. Ce dernier vit dans
    `mod-impression.js` (ou un petit `initTexte3d` dans le même fichier) :
    charge `/fonts/<fichier>` (cache par id, `opentype.parse(await (await fetch(url)).arrayBuffer())`),
    `texte_vers_d(font, o.contenu, corps, o.x, o.y, o.style.interlettrage || 0)`,
    puis `VL.executer(op_texte_vectoriser, id, d)`. Refus parlant si `window.opentype` absent.
  - `core.js` : `import { initImpression } from "./mod-impression.js";` + `initImpression(VL);` après `initPlanches(VL)`.
  - `index.html` : `<div id="impDlg" class="vl-dlg hidden"></div>` ; scripts `vendor/opentype.min.js` (classique) et `<script type="module" src="/assets/model-viewer.min.js"></script>` (le bundle du dist, déjà vendorisé) AVANT `js/core.js`.
  - CSS : `.imp-boite { width: min(1100px, 95vw); } .imp-corps { display:flex; gap:14px; padding:12px; } .imp-regles { width: 260px; display:flex; flex-direction:column; gap:8px; } .imp-regles label { display:flex; flex-direction:column; font-size:12px; color:#9aa3b2; gap:3px; } .imp-garde { color:#e0b34a; font-size:12px; margin:0; } .imp-doc { color:#8b93a0; font-size:12px; margin-left:8px; }`

- [ ] **Step 4 : `node --check`, `node qa/run.mjs` ; commit** `vectorlab : dialogue Impression 3D — modes calques/tuiles/logo, biseau, evidement, apercu GLB dans model-viewer, un STL ou un lot par tuile, texte vectorise depuis Apparence (lot D, T4)`.

---

## Task 5 : miroirs pytest

- `test_print3d.py::test_le_miroir_vectorlab_extrusion` : les assertions sur
  `mod-export.js` (`/api/print3d/from-stl`, `/api/print3d/open`, `ignor`)
  visent désormais `mod-impression.js` — le dire dans le test (la voie 3D a
  déménagé au lot D) ; ajouter `assert "/api/print3d/lot" in imp and "model-viewer" in html and "opentype.min.js" in html`.
- `test_vector_docs.py::test_le_miroir_lot_d_impression` : modules
  `mod-solide.js`, `mod-texte3d.js`, `mod-impression.js` présents et initialisés ; vendor
  `opentype.min.js` + licence MIT ; bancs `solide`, `texte3d`, `impression_ui` ;
  `op_texte_vectoriser` dans mod-doc ; `apVectoriserTexte` dans mod-style ;
  `creer_lot` dans print3d.py.
- Commit `vectorlab : miroirs pytest du lot D (lot D, T5)`.

## Task 6 : preuve en réel (8799, données isolées, viewport émulé)

- Plateau : ouvrir le doc du lot C (`9165b7ff4044`, 38 tuiles) → Exporter →
  Impression 3D → mode Tuiles, socle 2 → Aperçu : résumé « N pièce(s) »,
  `#impViewer` a un `src` blob et `offsetHeight > 0`, `model-viewer` chargé
  (`customElements.get("model-viewer")`) ; « Lot par tuile » → réponse
  `{pieces: 38, dossier}` ; lire `impression.json` du dossier via
  `/api/print3d/exports` (lot true, 38 STL, plateau.3mf, nomenclature.csv).
- Logo : doc avec un rect et une ellipse unis, mode Logo, biseau 1 →
  Aperçu : volume < prisme plein ; évider mur 1,2 plancher 1 → volume plus
  petit encore ; mur 0,3 → refus « mur ≥ 0,8 » ; « Un STL » → dossier.
- Texte : poser un texte « AB » (Anton, corps 120) → Apparence →
  Vectoriser → l'objet devient `path` (`data-objet` avec `d` qui contient ≥ 2
  « M ») ; Logo → Aperçu : triangles > 0 (le texte s'extrude) ; le compteur
  d'ignorés tombe à 0.
- Négatifs : mode Tuiles sur un doc sans grille hex → option désactivée /
  refus parlant ; Aperçu sans rien de visible → « rien d'extrudable ».

## Task 7 : déploiement et relevé

- Table `git hash-object` (base = `dd030e8` pour les fichiers du lot C ;
  `print3d.py`, `routes.py` = `7c99667`… vérifier) ; sauvegarde
  `_backup_predeploy_2026-09-17c-vectorlab-lotD` ; copie `frontend/vectorlab`
  + `backend/app/services/print3d.py` + `backend/app/api/routes.py` ;
  pré-vol python embarqué ; **Python touché → l'utilisateur relance**.
- Relevé en tête, commit, push, mémoire.

## Auto-revue

- **Couverture §4 lot D** : extrusion par tuile (socle + relief par terrain) ✔ T1/T4 ; assemblage plateau (plateau.3mf) ✔ T3 ; lot d'export (STL par tuile, 3MF, nomenclature) ✔ T3/T4 ; logos : biseau ✔, évidement ✔, épaisseur de mur minimale (0,8) ✔, règle des 256 (garde backend conservée + affichée) ✔ ; texte vectorisé (opentype.js) puis extrudable et booléen ✔ T2/T4 ; aperçu 3D par `<model-viewer>` vendorisé ✔ T4.
- **Écarts déclarés** : biseau en marches (0,2 mm) et non chanfrein exact ; texte vectorisé irréversible hors historique ; polices proposées = OFL sûres du dist ; l'aperçu n'a pas d'échelle affichée (les mm sont dans le résumé).
- **Cohérence des noms** : `MUR_MIN_MM / inset_multi / extruder_biseau / extruder_evide / plateau_pieces / glb_de_triangles / nomenclature_csv` ; `POLICES / commandes_vers_d / texte_vers_d` ; `op_texte_vectoriser` ; `reglages_lire / hauteurs_par_calque / resume_impression / initImpression` ; `VL.impression / VL.vectoriserTexte` ; `creer_lot`, `POST /print3d/lot`.
