# Game Assets 2D — LOT 1 « Spritelab Feuille » : inspecter, sélectionner, aligner, sectionner une feuille existante — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module
> pur). Steps use checkbox (`- [ ]`) syntax for tracking.

> Conception validée le 19/09/2026 par l'utilisateur :
> `docs/superpowers/specs/2026-09-19-sorceress-sprite-suite-design.md`
> (D1 « une feuille existante entre dans Spritelab », D4 palettes
> unifiées reportées au lot 3 ; **répartition** : Game Assets = production
> et inspection, persona Pixel du Vectorlab = édition, tuiles iso et
> rastérisation d'une image générée — lot 2). Inventaire source :
> `…-sorceress-sprite-suite-inventaire.md` §5.1 (Sprite Analyzer).
> Branche `chantier/vectorlab-affinity`. Ce plan est COMMIS avant le code.

**Goal :** dans Spritelab, un quatrième onglet de source « Feuille » ouvre
une planche PNG existante (Library ou fichier local), détecte sa grille,
laisse sélectionner les cases au glisser (Ctrl ajoute / retire, Maj étend,
« une sur n »), aligne les frames qui tremblent (deux axes / horizontal /
pieds + nudges 1 px), nomme des sections (début, fin, mode boucle /
ping-pong / inversé), lit l'animation, et livre une feuille alignée PNG +
un manifest JSON copiable — le tout **en local, sans backend, sans clé**.

**Architecture :** un module pur ESM `frontend/spritelab/feuille.js`
(bancable node sur des tampons `{w, h, data}` comme `mod-pixelart`) :
`grille_detecter`, `cases_occupees`, `selection_clic`, `selection_une_sur`,
`bbox_alpha`, `aligner_frames`, `section_definir`, `manifest_feuille`,
`feuille_recomposer`. L'UI vit dans `spritelab.js` (script classique) qui
importe le module par `<script type="module">` exposant `window.SLF` ; un
onglet « 🗂 Feuille » dans la colonne source, la colonne du milieu montre la
planche sur un canvas avec la grille et la sélection, la colonne de droite
réutilise le lecteur (`buildPlayer` gagne une variante locale) et gagne
Alignement, Sections, JSON. Aucun fichier Python touché : aucune relance.

**Tech Stack :** vanilla JS, ESM pur + banc node (`frontend/spritelab/qa/run.mjs`,
même patron que `frontend/vectorlab/qa`), canvas 2D, `/api/images` (liste),
`/api/images/upload` (sauver la feuille alignée en Library, préfixe
`sprites_feuille_`).

---

## Décisions d'implémentation

- **Détection de grille par projection alpha.** Colonnes et lignes dont
  l'alpha est nul sur toute la hauteur / largeur séparent des BANDES de
  contenu ; `cols` = nombre de bandes en x, `rows` = en y, la cellule =
  `w / cols` × `h / rows` (grille uniforme, comme la Suite). Si aucune
  colonne vide n'existe (planche sans marges), on rend `{cols: 1, rows: 1}`
  et l'utilisateur saisit col × row : jamais une valeur inventée.
- **Sélection = tableau de booléens par case**, une case par index
  `i = row * cols + col`. Clic simple = cette case seule ; Ctrl = bascule ;
  Maj = de la dernière case cliquée à celle-ci (ordre de lecture) ; glisser
  = « peindre » l'état de la première case survolée (Affinity-like, la Suite
  dit « Drag paint over »). « Une sur n » se calcule sur les cases OCCUPÉES.
- **Alignement sur la première frame sélectionnée** : bbox de l'alpha par
  case ; mode `deux` = centre x et bas y ; `x` = centre x seulement ; `pieds`
  = bas y seulement. Résultat = décalage entier `{dx, dy}` par case, borné
  pour ne pas sortir de la cellule (dit dans le résumé). Les nudges
  ajoutent ±1 à ce décalage.
- **Sections** : `{nom, debut, fin, mode}` sur les INDEX DE LA SÉLECTION
  (0…n−1 dans l'ordre), pas sur les cases ; `mode` ∈ `boucle` |
  `pingpong` | `inverse` ; deux sections peuvent se chevaucher (comme Start
  · Middle · End), un nom vide est refusé.
- **Manifest version 2**, même forme que celui de `sprite_service`
  (`grid`, `frames[{index, rect, offset}]`, `fps`) plus `sections[]`,
  `source: {kind: "feuille", filename}` — un lecteur Unity/Godot existant le
  lit comme avant.
- **Recomposition** : la feuille alignée est redessinée case par case avec
  les décalages, en gardant la grille d'origine ; export PNG par
  `canvas.toBlob`, JSON par `Blob` + ancre `download`, « Copier le JSON »
  par `navigator.clipboard`.
- **Vers le Vectorlab** : « Sauver en Library » suffit — le mécanisme
  « Envoyer vers… » de la Library et le sélecteur du Vectorlab (28/08)
  prennent le relais ; l'édition (lot 2) se fait dans le persona Pixel.

## Cartographie des fichiers

| Fichier | Rôle |
|---|---|
| `frontend/spritelab/feuille.js` (créer) | module pur (T1–T3) |
| `frontend/spritelab/qa/run.mjs`, `qa/feuille.test.mjs` (créer) | banc node (T1–T3) |
| `frontend/spritelab/index.html` (modifier) | onglet « 🗂 Feuille », zone de planche, panneau Alignement / Sections / JSON (T4) |
| `frontend/spritelab/spritelab.js` (modifier) | UI de l'onglet, gestes, lecteur local, exports (T4) |
| `frontend/spritelab/spritelab.css` (modifier) | grille, cases, sections (T4) |
| `docs/superpowers/plans/2026-09-19-spritelab-feuille-lot-1.md` | ce plan + relevé |

---

### Task 1 : grille, cases occupées, sélection (pur)

**Files :** Create `frontend/spritelab/feuille.js`, `frontend/spritelab/qa/run.mjs`, `frontend/spritelab/qa/feuille.test.mjs`

- [ ] **Step 1 : le banc RED** — `qa/run.mjs` :

```js
// qa/run.mjs — lance tous les *.test.mjs du dossier. Un échec = exit 1.
import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const ici = dirname(fileURLToPath(import.meta.url));
for (const f of readdirSync(ici).filter((n) => n.endsWith(".test.mjs")).sort()) {
  await import(pathToFileURL(join(ici, f)));
}
console.log("QA spritelab : tous les bancs sont passes.");
```

`qa/feuille.test.mjs` (première tranche) :

```js
// feuille.test.mjs — lot 1 Spritelab Feuille : grille par projection alpha,
// cases occupées, sélection (clic / Ctrl / Maj / glisser / une sur n),
// alignement sur la première frame, sections, manifest v2, recomposition.
import { grille_detecter, cases_occupees, selection_clic, selection_une_sur,
         bbox_alpha, aligner_frames, section_definir, manifest_feuille, feuille_recomposer } from "../feuille.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : "")); };
// un tampon {w, h, data} (RGBA) avec des pavés opaques posés où l'on veut
const tampon = (w, h) => ({ w, h, data: new Uint8ClampedArray(w * h * 4) });
const paver = (img, x0, y0, w, h, rgb = [255, 0, 0]) => { for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++) { const k = (y * img.w + x) * 4; img.data[k] = rgb[0]; img.data[k + 1] = rgb[1]; img.data[k + 2] = rgb[2]; img.data[k + 3] = 255; } return img; };
// une planche 3 × 2 de cellules 20 × 20, pavés 8 × 8 centrés sauf un vide et un décalé
const planche = () => { const im = tampon(60, 40); paver(im, 6, 6, 8, 8); paver(im, 26, 6, 8, 8); paver(im, 48, 8, 8, 8); paver(im, 6, 26, 8, 8); paver(im, 26, 26, 8, 8); return im; };
{
  const g = grille_detecter(planche());
  ok("grille 3 × 2 détectée par les colonnes / lignes vides", g.cols === 3 && g.rows === 2 && g.cell_w === 20 && g.cell_h === 20, JSON.stringify(g));
  const occ = cases_occupees(planche(), g);
  ok("cases occupées : 5 sur 6, la dernière vide", occ.length === 6 && occ.filter(Boolean).length === 5 && occ[5] === false, JSON.stringify(occ));
  const plein = paver(tampon(30, 30), 0, 0, 30, 30);
  const g1 = grille_detecter(plein);
  ok("sans colonne vide → 1 × 1 (jamais inventé)", g1.cols === 1 && g1.rows === 1);
  let refus = 0; try { grille_detecter({ w: 0, h: 0, data: new Uint8ClampedArray(0) }); } catch { refus++; }
  ok("image vide refusée", refus === 1);
}
{
  const n = 6;
  let s = selection_clic(new Array(n).fill(false), 2, {});
  ok("clic simple : la case seule", s.filter(Boolean).length === 1 && s[2] === true);
  s = selection_clic(s, 4, { ctrl: true });
  ok("Ctrl : ajoute", s[2] && s[4] && s.filter(Boolean).length === 2);
  s = selection_clic(s, 2, { ctrl: true });
  ok("Ctrl sur une case prise : retire", !s[2] && s[4]);
  s = selection_clic(s, 1, { shift: true, dernier: 4 });
  ok("Maj : de la dernière (4) à ici (1) — 1, 2, 3, 4", s.slice(1, 5).every(Boolean) && !s[0] && !s[5], JSON.stringify(s));
  const occ = [true, true, true, true, true, false];
  ok("une sur 2 sur les occupées : 0, 2, 4", JSON.stringify(selection_une_sur(occ, 2)) === "[true,false,true,false,true,false]");
  ok("une sur 1 = toutes les occupées", selection_une_sur(occ, 1).filter(Boolean).length === 5);
  ok("l'entrée n'est pas mutée", (() => { const a = [false, false]; selection_clic(a, 0, {}); return a[0] === false; })());
}
if (echecs.length) { console.error("ECHECS feuille :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA feuille : PASS (12 controles)");
```

- [ ] **Step 2 : RED constaté** — `node frontend/spritelab/qa/run.mjs` → `ERR_MODULE_NOT_FOUND` sur `feuille.js`.

- [ ] **Step 3 : implémenter** — `frontend/spritelab/feuille.js` :

```js
// feuille.js — lot 1 « Spritelab Feuille » (19/09/2026) : inspecter une
// planche existante. PUR : tampons {w, h, data} RGBA, aucun DOM. Grille par
// projection de l'alpha, sélection par index de case, alignement sur la
// première frame sélectionnée, sections nommées, manifest v2 (même forme que
// sprite_service), recomposition alignée. Banc : qa/feuille.test.mjs.
const _alphaCols = (img) => { const s = new Uint32Array(img.w); for (let y = 0; y < img.h; y++) for (let x = 0; x < img.w; x++) s[x] += img.data[(y * img.w + x) * 4 + 3]; return s; };
const _alphaRows = (img) => { const s = new Uint32Array(img.h); for (let y = 0; y < img.h; y++) for (let x = 0; x < img.w; x++) s[y] += img.data[(y * img.w + x) * 4 + 3]; return s; };
const _bandes = (s) => { let n = 0, dedans = false; for (const v of s) { if (v > 0 && !dedans) { n++; dedans = true; } else if (v === 0) dedans = false; } return n; };

export function grille_detecter(img) {
  if (!img || !(img.w > 0) || !(img.h > 0)) throw new Error("feuille : image vide");
  const cols = Math.max(1, _bandes(_alphaCols(img))), rows = Math.max(1, _bandes(_alphaRows(img)));
  return { cols, rows, cell_w: Math.floor(img.w / cols), cell_h: Math.floor(img.h / rows) };
}
export function rect_case(g, i) {
  const c = i % g.cols, r = Math.floor(i / g.cols);
  return { x: c * g.cell_w, y: r * g.cell_h, w: g.cell_w, h: g.cell_h };
}
export function bbox_alpha(img, rect) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (let y = rect.y; y < rect.y + rect.h && y < img.h; y++) for (let x = rect.x; x < rect.x + rect.w && x < img.w; x++) {
    if (img.data[(y * img.w + x) * 4 + 3] > 0) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  }
  return x0 === Infinity ? null : { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 };
}
export function cases_occupees(img, g) {
  const out = [];
  for (let i = 0; i < g.cols * g.rows; i++) out.push(bbox_alpha(img, rect_case(g, i)) !== null);
  return out;
}
export function selection_clic(sel, i, { ctrl = false, shift = false, dernier = null } = {}) {
  const out = sel.slice();
  if (i < 0 || i >= out.length) return out;
  if (shift && dernier !== null && dernier >= 0 && dernier < out.length) {
    const [a, b] = dernier <= i ? [dernier, i] : [i, dernier];
    for (let k = a; k <= b; k++) out[k] = true;
    return out;
  }
  if (ctrl) { out[i] = !out[i]; return out; }
  out.fill(false); out[i] = true;
  return out;
}
export function selection_une_sur(occupees, n) {
  const pas = Math.max(1, Math.floor(+n || 1));
  let k = 0;
  return occupees.map((o) => { if (!o) return false; const garde = k % pas === 0; k++; return garde; });
}
```

- [ ] **Step 4 : vert** — `node frontend/spritelab/qa/run.mjs` → `QA feuille : PASS (12 controles)`.
- [ ] **Step 5 : commit** — `git add frontend/spritelab/feuille.js frontend/spritelab/qa && git commit --only frontend/spritelab/feuille.js frontend/spritelab/qa/run.mjs frontend/spritelab/qa/feuille.test.mjs -m "spritelab feuille : grille par projection alpha, cases occupees, selection (pur, banc node)"`

### Task 2 : alignement sur la première frame (pur)

**Files :** Modify `frontend/spritelab/feuille.js`, `frontend/spritelab/qa/feuille.test.mjs`

- [ ] **Step 1 : RED** — ajouter au banc avant la ligne `if (echecs.length)` :

```js
{
  const im = planche(), g = grille_detecter(im);
  const sel = [true, true, true, false, false, false];        // la case 2 est décalée de +2 en x et +2 en y
  const off = aligner_frames(im, g, sel, "deux");
  ok("deux axes : la case 2 revient sur la première (dx −2, dy −2), les autres 0", off.length === 6 && off[0].dx === 0 && off[0].dy === 0 && off[2].dx === -2 && off[2].dy === -2 && off[3].dx === 0, JSON.stringify(off));
  ok("x seulement : dy reste 0", aligner_frames(im, g, sel, "x")[2].dy === 0 && aligner_frames(im, g, sel, "x")[2].dx === -2);
  ok("pieds : dx reste 0, le bas s'aligne", aligner_frames(im, g, sel, "pieds")[2].dx === 0 && aligner_frames(im, g, sel, "pieds")[2].dy === -2);
  ok("une case non sélectionnée ou vide → 0, 0", aligner_frames(im, g, sel, "deux")[5].dx === 0);
  let refus = 0; try { aligner_frames(im, g, sel, "diagonale"); } catch { refus++; }
  ok("mode inconnu refusé", refus === 1);
  const b = bbox_alpha(im, rect_case(g, 2));
  ok("bbox alpha de la case 2 : 8 × 8 en (48, 8)", b.x === 48 && b.y === 8 && b.w === 8 && b.h === 8, JSON.stringify(b));
  // le décalage est BORNÉ à la cellule : un pavé collé au bord ne sort pas
  const im2 = paver(paver(tampon(40, 20), 6, 6, 8, 8), 20, 0, 8, 8);
  const g2 = grille_detecter(im2), o2 = aligner_frames(im2, g2, [true, true], "deux");
  ok("borné : dy ≤ ce que la cellule permet", o2[1].dy === 6 && o2[1].dx === -2, JSON.stringify(o2));
}
```

Importer `rect_case` dans le banc et passer le compte à 19.

- [ ] **Step 2 : RED constaté** (`aligner_frames is not a function`).
- [ ] **Step 3 : implémenter** :

```js
export const MODES_ALIGNEMENT = ["deux", "x", "pieds"];
// décalage entier par case pour ramener le centre x et / ou le bas de l'alpha
// sur ceux de la PREMIÈRE case sélectionnée ; borné à la cellule
export function aligner_frames(img, g, sel, mode = "deux") {
  if (!MODES_ALIGNEMENT.includes(mode)) throw new Error(`alignement : mode ${mode} inconnu (deux, x, pieds)`);
  const n = g.cols * g.rows, out = [];
  let ref = null;
  for (let i = 0; i < n; i++) { if (sel[i]) { const b = bbox_alpha(img, rect_case(g, i)); if (b) { const r = rect_case(g, i); ref = { cx: b.x - r.x + b.w / 2, bas: b.y - r.y + b.h }; break; } } }
  for (let i = 0; i < n; i++) {
    const r = rect_case(g, i), b = sel[i] ? bbox_alpha(img, r) : null;
    if (!b || !ref) { out.push({ dx: 0, dy: 0 }); continue; }
    let dx = mode === "pieds" ? 0 : Math.round(ref.cx - (b.x - r.x + b.w / 2));
    let dy = mode === "x" ? 0 : Math.round(ref.bas - (b.y - r.y + b.h));
    dx = Math.max(-(b.x - r.x), Math.min(r.w - (b.x - r.x + b.w), dx));
    dy = Math.max(-(b.y - r.y), Math.min(r.h - (b.y - r.y + b.h), dy));
    out.push({ dx, dy });
  }
  return out;
}
```

- [ ] **Step 4 : vert** ; **Step 5 : commit** — `git commit --only frontend/spritelab/feuille.js frontend/spritelab/qa/feuille.test.mjs -m "spritelab feuille : alignement sur la premiere frame (deux axes, x, pieds), borne a la cellule"`

### Task 3 : sections, manifest v2, recomposition (pur)

**Files :** Modify `frontend/spritelab/feuille.js`, `frontend/spritelab/qa/feuille.test.mjs`

- [ ] **Step 1 : RED** :

```js
{
  let S = section_definir([], { nom: "marche", debut: 0, fin: 3, mode: "boucle" }, 5);
  ok("section posée", S.length === 1 && S[0].nom === "marche" && S[0].fin === 3);
  S = section_definir(S, { nom: "saut", debut: 2, fin: 4, mode: "pingpong" }, 5);
  ok("deux sections peuvent se chevaucher", S.length === 2);
  S = section_definir(S, { nom: "marche", debut: 1, fin: 3, mode: "inverse" }, 5);
  ok("même nom = remplace", S.length === 2 && S.find((s) => s.nom === "marche").debut === 1);
  let refus = 0;
  for (const mauvaise of [{ nom: "", debut: 0, fin: 1, mode: "boucle" }, { nom: "x", debut: 3, fin: 1, mode: "boucle" }, { nom: "x", debut: 0, fin: 9, mode: "boucle" }, { nom: "x", debut: 0, fin: 1, mode: "yoyo" }]) { try { section_definir(S, mauvaise, 5); } catch { refus++; } }
  ok("nom vide, fin < début, hors bornes, mode inconnu → refusés", refus === 4);
  const im = planche(), g = grille_detecter(im), sel = [true, true, true, false, true, false];
  const off = aligner_frames(im, g, sel, "deux");
  const m = manifest_feuille({ img: im, g, sel, offsets: off, fps: 12, sections: S, filename: "wizard.png" });
  ok("manifest v2 : 4 frames dans l'ordre des cases, rect + offset, fps, sections, source feuille", m.version === 2 && m.frames.length === 4 && m.frames[3].index === 3 && m.frames[3].rect.x === 20 && m.frames[3].rect.y === 20 && m.frames[2].offset.dx === -2 && m.fps === 12 && m.sections.length === 2 && m.source.kind === "feuille" && m.source.filename === "wizard.png" && m.grid.cols === 3, JSON.stringify(m).slice(0, 200));
  ok("frames[i].case = l'index de la case d'origine", m.frames[3].case === 4);
  const out = feuille_recomposer(im, g, off);
  ok("recomposée : même taille, la case 2 ramenée à (46, 6)", out.w === 60 && out.h === 40 && out.data[((6 * 60) + 46) * 4 + 3] === 255 && out.data[((8 * 60) + 48 + 7) * 4 + 3] === 255 && out.data[((15 * 60) + 55) * 4 + 3] === 0, "");
  ok("recomposée sans décalage = identique", (() => { const z = feuille_recomposer(im, g, off.map(() => ({ dx: 0, dy: 0 }))); for (let k = 0; k < z.data.length; k++) if (z.data[k] !== im.data[k]) return false; return true; })());
}
```

Compte → 28.

- [ ] **Step 2 : RED constaté**.
- [ ] **Step 3 : implémenter** :

```js
export const MODES_SECTION = ["boucle", "pingpong", "inverse"];
export function section_definir(sections, s, nFrames) {
  const nom = String(s.nom || "").trim();
  if (!nom) throw new Error("section : nom requis");
  const debut = Math.floor(+s.debut), fin = Math.floor(+s.fin);
  if (!(debut >= 0) || !(fin >= debut) || fin >= nFrames) throw new Error(`section : bornes 0 ≤ début ≤ fin < ${nFrames}`);
  if (!MODES_SECTION.includes(s.mode)) throw new Error("section : mode boucle, pingpong ou inverse");
  const out = sections.filter((x) => x.nom !== nom);
  out.push({ nom, debut, fin, mode: s.mode });
  return out;
}
export function manifest_feuille({ img, g, sel, offsets, fps, sections, filename }) {
  const frames = [];
  for (let i = 0; i < g.cols * g.rows; i++) {
    if (!sel[i]) continue;
    const r = rect_case(g, i), o = offsets[i] || { dx: 0, dy: 0 };
    frames.push({ index: frames.length, case: i, file: null, rect: { x: r.x, y: r.y, w: r.w, h: r.h }, offset: { dx: o.dx, dy: o.dy } });
  }
  return { version: 2, source: { kind: "feuille", filename: filename || null, w: img.w, h: img.h },
           grid: { cols: g.cols, rows: g.rows, cell_w: g.cell_w, cell_h: g.cell_h },
           frames, fps: +fps || 12, sections: (sections || []).map((s) => ({ ...s })) };
}
// la planche redessinée case par case avec ses décalages (bornés en amont)
export function feuille_recomposer(img, g, offsets) {
  const out = { w: img.w, h: img.h, data: new Uint8ClampedArray(img.w * img.h * 4) };
  for (let i = 0; i < g.cols * g.rows; i++) {
    const r = rect_case(g, i), o = offsets[i] || { dx: 0, dy: 0 };
    for (let y = 0; y < r.h; y++) for (let x = 0; x < r.w; x++) {
      const sx = r.x + x, sy = r.y + y, tx = sx + o.dx, ty = sy + o.dy;
      if (tx < r.x || ty < r.y || tx >= r.x + r.w || ty >= r.y + r.h || sx >= img.w || sy >= img.h) continue;
      const ks = (sy * img.w + sx) * 4, kt = (ty * img.w + tx) * 4;
      out.data[kt] = img.data[ks]; out.data[kt + 1] = img.data[ks + 1]; out.data[kt + 2] = img.data[ks + 2]; out.data[kt + 3] = img.data[ks + 3];
    }
  }
  return out;
}
```

- [ ] **Step 4 : vert (28)** ; **Step 5 : commit** — `git commit --only frontend/spritelab/feuille.js frontend/spritelab/qa/feuille.test.mjs -m "spritelab feuille : sections nommees, manifest v2, recomposition alignee (purs)"`

### Task 4 : l'onglet « Feuille » de Spritelab (UI)

**Files :** Modify `frontend/spritelab/index.html`, `spritelab.js`, `spritelab.css`

- [ ] **Step 1 : index.html** — dans `#srcTabs` après l'onglet Vidéo : `<button class="tab" data-src="feuille" title="Ouvrir une planche existante (Library ou fichier) : grille, sélection, alignement, sections, JSON">🗂 Feuille</button>`. Après `#srcUpload` :

```html
    <!-- Feuille existante (lot 1, 19/09) : inspecter une planche déjà faite -->
    <div id="srcFeuille" class="src-body hidden">
      <div class="upload-box"><label class="btn">📂 Ouvrir un PNG de mon PC <input id="feuilleFile" type="file" accept="image/png,image/webp" hidden></label>
        <div class="hint">ou choisis une planche de la Library ci-dessous — tout se fait en local, rien n'est envoyé.</div></div>
      <input id="feuilleSearch" class="search" placeholder="🔎 Filtrer les planches…">
      <div id="feuilleGrid" class="img-grid"><div class="empty-note">Chargement de la Library…</div></div>
    </div>
```

Dans `#stripPane`, après `#strip` : la zone de planche (cachée hors mode feuille) :

```html
    <div id="feuillePane" class="feuille hidden">
      <div class="feuille-bar">
        <button id="fDetect" class="btn" title="Détecter colonnes, lignes et cases occupées par les colonnes vides de la planche">Auto-détecter</button>
        <label class="fld inline">Grille <input id="fCols" type="number" min="1" max="64" value="1"> × <input id="fRows" type="number" min="1" max="64" value="1"> <button id="fOk" class="btn ghost" title="Appliquer ces colonnes et lignes">OK</button></label>
        <span id="fDims" class="counter">—</span><span id="fCount" class="counter">0/0</span>
        <button id="fAll" class="btn ghost" title="Sélectionner toutes les cases occupées">Toutes</button><button id="fNone" class="btn ghost" title="Vider la sélection">Aucune</button>
        <span class="fld inline">Une sur <button class="btn ghost fEvery" data-n="1">1</button><button class="btn ghost fEvery" data-n="2">2</button><button class="btn ghost fEvery" data-n="3">3</button><button class="btn ghost fEvery" data-n="4">4</button></span>
      </div>
      <div class="hint">Glisser peint la sélection · Ctrl ajoute / retire · Maj étend depuis la dernière case</div>
      <div id="fWrap" class="feuille-wrap"><canvas id="fCanvas"></canvas></div>
    </div>
```

Dans `#outPane`, après `#exports` :

```html
    <div id="feuilleOut" class="feuille-out hidden">
      <div class="settings">
        <div class="settings-sec">Alignement <span class="hint">sur la première frame sélectionnée</span></div>
        <div class="row"><button id="fAlDeux" class="btn" title="Centre horizontal et pieds">Les deux axes</button><button id="fAlX" class="btn" title="Centre horizontal seulement">Gauche / droite</button><button id="fAlPieds" class="btn" title="Bas de l'alpha seulement (les pieds)">Pieds</button><button id="fAlZero" class="btn ghost" title="Retirer tous les décalages">Remettre</button></div>
        <div class="row nudges"><span class="hint">Frame courante :</span><button class="btn ghost fNudge" data-dx="0" data-dy="-1" title="1 px vers le haut">↑</button><button class="btn ghost fNudge" data-dx="-1" data-dy="0">←</button><button class="btn ghost fNudge" data-dx="1" data-dy="0">→</button><button class="btn ghost fNudge" data-dx="0" data-dy="1">↓</button></div>
        <div class="settings-sec">Sections</div>
        <div id="fSections" class="sections"></div>
        <div class="row"><input id="fSecNom" class="fld" placeholder="nom (marche, saut…)"><select id="fSecMode"><option value="boucle">boucle</option><option value="pingpong">ping-pong</option><option value="inverse">inversé</option></select><button id="fSecAdd" class="btn" title="La section = la sélection courante, dans l'ordre de lecture">+ depuis la sélection</button></div>
        <div class="settings-sec">Export</div>
        <div class="row"><button id="fCopyJson" class="btn" title="Copie le manifest v2 (grille, frames, décalages, fps, sections)">📋 Copier le JSON</button><button id="fDlJson" class="btn">⬇ JSON</button><button id="fDlPng" class="btn">⬇ Planche alignée</button><button id="fSaveLib" class="btn primary" title="Sauve la planche alignée en Library (préfixe sprites_feuille_) — de là, « Envoyer vers » le Vectorlab">💾 Save to Library</button></div>
        <div id="fStatus" class="status hidden"></div>
      </div>
    </div>
```

Et en fin de `<body>`, avant `spritelab.js` : `<script type="module">import * as SLF from "./feuille.js"; window.SLF = SLF; document.dispatchEvent(new Event("slf-pret"));</script>`.

- [ ] **Step 2 : spritelab.css** — ajouter :

```css
/* ── lot 1 : Feuille (19/09) ── */
.feuille{flex:1;display:flex;flex-direction:column;min-height:0}
.feuille-bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:8px 10px;border-bottom:1px solid var(--stroke)}
.fld.inline{display:inline-flex;align-items:center;gap:4px;width:auto}.fld.inline input{width:56px}
.feuille-wrap{flex:1;overflow:auto;background:var(--bg-base);padding:10px}
#fCanvas{image-rendering:pixelated;cursor:crosshair;max-width:100%}
.feuille-out .row{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:4px 0}
.sections{display:flex;flex-direction:column;gap:4px}
.section-row{display:flex;gap:8px;align-items:center;font-size:12.5px;border:1px solid var(--stroke);border-radius:8px;padding:4px 8px}
.section-row .nom{flex:1;color:var(--ink-strong)}
```

- [ ] **Step 3 : spritelab.js** — un bloc « Feuille » avant `wire()` :

```js
/* ───────── lot 1 : Feuille existante (19/09) — tout en local ───────── */
const F = { img: null, filename: null, g: null, sel: [], occ: [], off: [], sections: [], dernier: null, peint: null, courant: 0 };
const fTampon = () => { const c = document.createElement("canvas"); c.width = F.img.naturalWidth; c.height = F.img.naturalHeight; const x = c.getContext("2d"); x.drawImage(F.img, 0, 0); const d = x.getImageData(0, 0, c.width, c.height); return { w: c.width, h: c.height, data: d.data }; };
async function feuilleOuvrir(src, filename) {
  const im = new Image(); im.crossOrigin = "anonymous"; im.src = src;
  await im.decode();
  F.img = im; F.filename = filename; F.tampon = fTampon(); F.off = []; F.sections = []; F.dernier = null;
  feuilleDetect();
  setSource({ kind: "feuille", label: filename });
  $("#feuillePane").classList.remove("hidden"); $("#strip").classList.add("hidden"); $("#feuilleOut").classList.remove("hidden");
}
function feuilleDetect() {
  F.g = window.SLF.grille_detecter(F.tampon);
  $("#fCols").value = F.g.cols; $("#fRows").value = F.g.rows;
  feuilleGrille();
}
function feuilleGrille() {
  const cols = parseInt($("#fCols").value, 10) || 1, rows = parseInt($("#fRows").value, 10) || 1;
  F.g = { cols, rows, cell_w: Math.floor(F.tampon.w / cols), cell_h: Math.floor(F.tampon.h / rows) };
  F.occ = window.SLF.cases_occupees(F.tampon, F.g);
  F.sel = F.occ.slice(); F.off = F.occ.map(() => ({ dx: 0, dy: 0 })); F.sections = [];
  $("#fDims").textContent = `${F.tampon.w}×${F.tampon.h} · cases ${F.g.cell_w}×${F.g.cell_h}`;
  feuilleDessiner(); feuilleJoueur();
}
function feuilleDessiner() {
  const cv = $("#fCanvas"), g = F.g; cv.width = F.tampon.w; cv.height = F.tampon.h;
  const x = cv.getContext("2d"); x.imageSmoothingEnabled = false;
  const rec = window.SLF.feuille_recomposer(F.tampon, g, F.off);
  x.putImageData(new ImageData(rec.data, rec.w, rec.h), 0, 0);
  for (let i = 0; i < g.cols * g.rows; i++) {
    const r = window.SLF.rect_case(g, i);
    x.fillStyle = F.sel[i] ? "rgba(58,166,107,.22)" : "rgba(0,0,0,0)"; x.fillRect(r.x, r.y, r.w, r.h);
    x.strokeStyle = F.sel[i] ? "#3aa66b" : (F.occ[i] ? "#3a3a3a" : "#222"); x.lineWidth = 1; x.strokeRect(r.x + .5, r.y + .5, r.w - 1, r.h - 1);
    x.fillStyle = "#9a9a9a"; x.font = "9px system-ui"; x.fillText(String(i), r.x + 2, r.y + 9);
  }
  const n = F.sel.filter(Boolean).length; $("#fCount").textContent = `${n}/${F.occ.filter(Boolean).length}`;
  $("#fSections").innerHTML = F.sections.map((s) => `<div class="section-row"><span class="nom">${esc(s.nom)}</span><span>${s.debut}–${s.fin}</span><span>${s.mode}</span><button class="btn ghost fSecDel" data-nom="${esc(s.nom)}" title="Retirer">✕</button></div>`).join("") || `<div class="hint">aucune section — sélectionne des cases puis « + depuis la sélection »</div>`;
  $$(".fSecDel").forEach((b) => b.onclick = () => { F.sections = F.sections.filter((s) => s.nom !== b.dataset.nom); feuilleDessiner(); });
}
const fCaseDe = (ev) => { const cv = $("#fCanvas"), r = cv.getBoundingClientRect(); const x = (ev.clientX - r.left) * cv.width / r.width, y = (ev.clientY - r.top) * cv.height / r.height; const c = Math.floor(x / F.g.cell_w), l = Math.floor(y / F.g.cell_h); return (c < 0 || l < 0 || c >= F.g.cols || l >= F.g.rows) ? -1 : l * F.g.cols + c; };
function feuilleGestes() {
  const cv = $("#fCanvas");
  cv.onpointerdown = (ev) => { const i = fCaseDe(ev); if (i < 0) return; ev.preventDefault(); cv.setPointerCapture(ev.pointerId);
    F.sel = window.SLF.selection_clic(F.sel, i, { ctrl: ev.ctrlKey || ev.metaKey, shift: ev.shiftKey, dernier: F.dernier });
    F.peint = F.sel[i]; F.dernier = i; F.courant = i; feuilleDessiner(); feuilleJoueur(); };
  cv.onpointermove = (ev) => { if (F.peint === null || !(ev.buttons & 1)) return; const i = fCaseDe(ev); if (i < 0 || F.sel[i] === F.peint) return; F.sel = F.sel.slice(); F.sel[i] = F.peint; F.dernier = i; feuilleDessiner(); };
  cv.onpointerup = () => { F.peint = null; feuilleJoueur(); };
}
function feuilleJoueur() {                      // le lecteur local : les cases sélectionnées, avec leurs décalages
  cancelAnimationFrame(player.raf);
  const rec = window.SLF.feuille_recomposer(F.tampon, F.g, F.off);
  const src = document.createElement("canvas"); src.width = rec.w; src.height = rec.h; src.getContext("2d").putImageData(new ImageData(rec.data, rec.w, rec.h), 0, 0);
  const idx = F.sel.map((v, i) => v ? i : -1).filter((i) => i >= 0);
  const cv = $("#cv"); cv.width = F.g.cell_w; cv.height = F.g.cell_h;
  $("#outEmpty").classList.add("hidden"); $("#player").classList.remove("hidden"); $("#exports").classList.add("hidden"); $("#sheetWrap").classList.add("hidden");
  $("#outInfo").textContent = `${F.g.cols}×${F.g.rows} · ${F.g.cell_w}px · ${idx.length} frames · ${F.filename || ""}`;
  player.n = idx.length; player.i = 0; player.acc = 0; player.last = 0; player.playing = true; $("#playBtn").textContent = "⏸";
  applyZoom(); applyBg();
  const ctx = cv.getContext("2d");
  const tick = (t) => { const fps = parseInt($("#pfps").value, 10) || 8; if (!player.last) player.last = t;
    if (player.playing && player.n) { player.acc += t - player.last; const step = 1000 / fps; while (player.acc >= step) { player.acc -= step; player.i = (player.i + 1) % player.n; } }
    player.last = t; if (player.n) { const r = window.SLF.rect_case(F.g, idx[player.i]); ctx.clearRect(0, 0, cv.width, cv.height); ctx.imageSmoothingEnabled = false; ctx.drawImage(src, r.x, r.y, r.w, r.h, 0, 0, r.w, r.h); }
    player.raf = requestAnimationFrame(tick); };
  player.raf = requestAnimationFrame(tick);
}
function feuilleAligner(mode) { try { F.off = mode ? window.SLF.aligner_frames(F.tampon, F.g, F.sel, mode) : F.occ.map(() => ({ dx: 0, dy: 0 })); feuilleDessiner(); feuilleJoueur(); } catch (e) { toast(e.message, true); } }
function feuilleManifest() { return window.SLF.manifest_feuille({ img: F.tampon, g: F.g, sel: F.sel, offsets: F.off, fps: parseInt($("#pfps").value, 10) || 12, sections: F.sections, filename: F.filename }); }
async function feuillePngBlob() { const rec = window.SLF.feuille_recomposer(F.tampon, F.g, F.off); const c = document.createElement("canvas"); c.width = rec.w; c.height = rec.h; c.getContext("2d").putImageData(new ImageData(rec.data, rec.w, rec.h), 0, 0); return new Promise((r) => c.toBlob(r, "image/png")); }
const fTelecharger = (blob, nom) => { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = nom; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
function feuilleWire() {
  $("#feuilleFile").onchange = (e) => { const f = e.target.files[0]; if (f) feuilleOuvrir(URL.createObjectURL(f), f.name); };
  $("#feuilleSearch").oninput = renderFeuilleGrid;
  $("#fDetect").onclick = feuilleDetect; $("#fOk").onclick = feuilleGrille;
  $("#fAll").onclick = () => { F.sel = F.occ.slice(); feuilleDessiner(); feuilleJoueur(); };
  $("#fNone").onclick = () => { F.sel = F.occ.map(() => false); feuilleDessiner(); feuilleJoueur(); };
  $$(".fEvery").forEach((b) => b.onclick = () => { F.sel = window.SLF.selection_une_sur(F.occ, +b.dataset.n); feuilleDessiner(); feuilleJoueur(); });
  $("#fAlDeux").onclick = () => feuilleAligner("deux"); $("#fAlX").onclick = () => feuilleAligner("x"); $("#fAlPieds").onclick = () => feuilleAligner("pieds"); $("#fAlZero").onclick = () => feuilleAligner(null);
  $$(".fNudge").forEach((b) => b.onclick = () => { const o = F.off[F.courant]; if (!o) return; F.off = F.off.slice(); F.off[F.courant] = { dx: o.dx + +b.dataset.dx, dy: o.dy + +b.dataset.dy }; feuilleDessiner(); feuilleJoueur(); });
  $("#fSecAdd").onclick = () => { const idx = F.sel.map((v, i) => v ? i : -1).filter((i) => i >= 0); if (!idx.length) return toast("sélectionne des cases d'abord", true);
    try { F.sections = window.SLF.section_definir(F.sections, { nom: $("#fSecNom").value, debut: 0, fin: idx.length - 1, mode: $("#fSecMode").value }, idx.length); $("#fSecNom").value = ""; feuilleDessiner(); } catch (e) { toast(e.message, true); } };
  $("#fCopyJson").onclick = async () => { await navigator.clipboard.writeText(JSON.stringify(feuilleManifest(), null, 2)); toast("manifest copié"); };
  $("#fDlJson").onclick = () => fTelecharger(new Blob([JSON.stringify(feuilleManifest(), null, 2)], { type: "application/json" }), (F.filename || "feuille").replace(/\.\w+$/, "") + ".json");
  $("#fDlPng").onclick = async () => fTelecharger(await feuillePngBlob(), (F.filename || "feuille").replace(/\.\w+$/, "") + "_alignee.png");
  $("#fSaveLib").onclick = async () => { const fd = new FormData(); fd.append("file", await feuillePngBlob(), `sprites_feuille_${Date.now()}.png`); const r = await fetch("/api/images/upload", { method: "POST", body: fd }); const d = await r.json().catch(() => ({})); if (!r.ok) return toast(d.detail || r.statusText, true); toast(`sauvé en Library : ${d.filename} — « Envoyer vers » le Vectorlab depuis la Library`); };
  feuilleGestes();
}
function renderFeuilleGrid() {
  const q = ($("#feuilleSearch").value || "").toLowerCase();
  const list = libImages.filter((im) => !q || im.filename.toLowerCase().includes(q));
  $("#feuilleGrid").innerHTML = list.length ? list.map((im) => `<div class="img-item" data-f="${esc(im.filename)}"><img loading="lazy" src="/api/images/${encodeURIComponent(im.filename)}"><div class="img-name">${esc(im.filename)}</div></div>`).join("") : `<div class="empty-note">Aucune image.</div>`;
  $$("#feuilleGrid .img-item").forEach((el) => el.onclick = () => feuilleOuvrir(`/api/images/${encodeURIComponent(el.dataset.f)}`, el.dataset.f));
}
window.SL = Object.assign(window.SL || {}, { feuille: { ouvrir: feuilleOuvrir, etat: () => F, manifest: feuilleManifest } });   // la preuve
```

Dans `switchSrcTab`, le corps `srcFeuille` suit les autres (`$("#srcFeuille").classList.toggle("hidden", which !== "feuille")` selon le patron existant) ; quand on quitte l'onglet Feuille, `#feuillePane` se cache et `#strip` revient. `wire()` appelle `feuilleWire()` après le chargement du module : `document.addEventListener("slf-pret", feuilleWire, { once: true }); if (window.SLF) feuilleWire();`. `loadImages()` appelle aussi `renderFeuilleGrid()`.

- [ ] **Step 4 : `node --check frontend/spritelab/spritelab.js`**, banc `run.mjs`.
- [ ] **Step 5 : commit** — `git commit --only frontend/spritelab/index.html frontend/spritelab/spritelab.js frontend/spritelab/spritelab.css -m "spritelab : onglet Feuille — grille, selection au glisser, alignement, sections, manifest v2, tout en local"`

### Task 5 : preuve en réel (backend du worktree 8799, viewport 1400 × 900)

- [ ] Lancer le backend du worktree (données isolées), ouvrir `http://127.0.0.1:8799/spritelab/`, `resize_window` 1400 × 900, substituer rAF par un temporisateur si le volet est caché (piège R12).
- [ ] Fabriquer en page une planche 4 × 2 de 32 px (pavés décalés sur deux cases, une case vide) par canvas → `SL.feuille.ouvrir(dataURL, "banc.png")` : mesurer `fCols`/`fRows` = 4/2, `fCount` = 7/7 ; clic case 1 → 1/7 ; Ctrl+clic case 3 → 2 ; Maj+clic case 6 → 3–6 sélectionnées ; glisser de la case 0 à la case 2 avec `PointerEvent` sur `#fCanvas` → les cases survolées prennent l'état peint ; « Une sur 2 » → 4 cases ; « Les deux axes » → `SL.feuille.etat().off` des cases décalées = leur décalage inverse ; nudge ↑ → dy − 1 sur la case courante ; section « marche » boucle → dans le manifest ; « Copier le JSON » avec `navigator.clipboard.writeText` stubé → JSON v2 avec `sections[0].nom === "marche"` ; « Save to Library » → `/api/images/upload` reçoit `sprites_feuille_*.png` (relu par `/api/images`) ; le lecteur `#cv` mesure `cell_w × cell_h` et tourne (deux lectures de `player.i` distinctes).
- [ ] Onglet Feuille depuis la Library : la planche sauvée s'ouvre par clic dans `#feuilleGrid`.
- [ ] 0 erreur console neuve ; `taskkill` du PID 8799 ; `preset: desktop`.

### Task 6 : déploiement, relevé, mémoire, push

- [ ] Fichiers touchés (statiques seuls) : installé = base `27bde1b`/`eb9bae0` par `git hash-object` ; sauvegarde `_backup_predeploy_2026-09-19-spritelab-feuille` ; copie depuis `git archive HEAD` ; hash = cible. **Aucun Python touché : pas de relance.** Vérifier que `/spritelab/` de l'installé sert `feuille.js` (route statique existante sur le dossier).
- [ ] Relevé de livraison en tête de ce plan ; mémoire (`MEMORY.md` + un fichier `spritelab-feuille.md` : contrats `feuille.js`, manifest v2, répartition Game Assets / Pixel, pièges) ; `git push origin chantier/vectorlab-affinity`.
