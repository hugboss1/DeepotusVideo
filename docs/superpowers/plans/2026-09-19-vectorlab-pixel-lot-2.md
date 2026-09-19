# Game Assets 2D — LOT 2 « persona Pixel de classe Sprite Editor » : ligne de temps, gestes, tuile iso, rastérisation — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module
> pur). Steps use checkbox (`- [ ]`) syntax for tracking.

> Conception validée le 19/09/2026 :
> `docs/superpowers/specs/2026-09-19-sorceress-sprite-suite-design.md` (D2 +
> **répartition** : le persona Pixel du Vectorlab est l'ÉDITEUR — sprites et
> tuiles, y compris **iso 2:1**, et **rastérisation d'une image générée**).
> Inventaire source : `…-sorceress-sprite-suite-inventaire.md` §5.2 (Sprite
> Editor) et §5.3 (Tile Studio). Contrats du lot E à respecter :
> `mod-pixel` / `mod-pixelart` feuilles pures, `etat.px`, tampons `{w, h,
> data}`, cadres = images du calque « cadres », journal `.pix<k>.png`,
> `doc.pixelart {tuile, palette, symetrie}` + `op_pixelart`, familles
> (`mod-familles`), champs de contexte (`mod-contexte`), `VL.hints`,
> `VL.actions.pixel`. Branche `chantier/vectorlab-affinity`, après le lot 1
> (`72e8093`). Ce plan est COMMIS avant le code.

**Goal :** le persona Pixel gagne les gestes du Sprite Editor (couleur
secondaire au clic droit — transparente = gomme —, Maj+clic = segment
depuis le dernier point, Alt+clic = pipette, pinceau rond ou carré, crayon
pixel-parfait), une **ligne de temps** des cadres (vignettes, lecture
Entrée / boucle / FPS, pelure rouge = précédent et bleue = suivant,
dupliquer / vide / supprimer), un **mode tuile iso 2:1** (grille en
losange, peinture bornée au losange, raccord ×9 en pavage iso avec score)
et la commande **« Rastériser cette image »** (pixeliser à une largeur
cible, palette, tramage ordonné ou Floyd-Steinberg) — en local, sans
Python.

**Architecture :** tout le calcul dans les feuilles pures existantes :
`mod-pixel.js` (pinceau / gomme gagnent `forme: "rond" | "carre"`),
`mod-pixelart.js` (`pixel_parfait`, `dither_ordonne`, `dither_floyd`,
`rasteriser`, `pelure_double`, `masque_losange`, `pavage_iso`) ;
`mod-doc.js` (`doc.pixelart.iso`) ; `mod-contexte.js` (champs Forme /
Parfait) ; l'UI `mod-pixelui.js` traduit (gestes en capture, panneau
« Ligne de temps », iso, rastérisation, `VL.actions.pixel.rasteriser`).
Bancs existants étendus : `pixel.test`, `pixelart.test`, `pixel_doc.test`,
`contexte.test`. Aucun fichier Python : aucune relance.

---

## Décisions d'implémentation

- **Secondaire** : `etat.px.secondaire` = hex ou `null` (transparent).
  Bouton droit = peindre avec la secondaire ; `null` → la gomme (le
  Sprite Editor dit « transparent = erase »). `contextmenu` sur `#stage`
  est empêché en persona Pixel. `X` échange primaire et secondaire.
- **Maj+clic** avec pinceau / crayon / gomme : un segment du dernier point
  posé (`etat.px.dernier`, en pixels natifs) au point cliqué, une commande ;
  sans dernier point = un clic normal.
- **Alt+clic** avec un outil de peinture = pipette (le cloner garde Alt =
  source) : la couleur du pixel (alpha > 0) devient la primaire ; bouton
  droit + Alt = la secondaire.
- **Pinceau carré** : `_carre` dans mod-pixel (même dureté, distance de
  Tchebychev) ; option `forme` de `pinceau` et `gomme`, champ « Forme » dans
  la barre contextuelle.
- **Pixel-parfait** (`pixel_parfait(points)`) : retire le pixel médian d'un
  coin en L (trois pixels dont le premier et le troisième sont diagonaux)
  — l'algorithme d'Aseprite. Le crayon le fait par défaut
  (`etat.px.parfait = true`, bascule dans la barre) ; l'aperçu du crayon
  repart du tampon de départ à chaque cadre (tracé ENTIER re-filtré), les
  autres outils gardent l'aperçu incrémental.
- **Pelure double** : `pelure_double(courant, precedent, suivant, alpha)` =
  précédent teinté rouge et suivant teinté bleu là où le courant est
  transparent (le Sprite Editor : « red = previous, blue = next »).
- **Ligne de temps** : section du panneau Pixel ; les cadres viennent de
  `cadres_de(doc)` (ordre du calque « cadres »), vignettes depuis le cache
  des tampons, clic = éditer ce cadre, ▶/⏸ (Entrée quand rien n'a le focus),
  boucle, FPS ; dupliquer = nouveau cadre copié APRÈS le courant ; vide =
  cadre transparent après le courant ; supprimer = `op_supprimer` du cadre
  courant (≥ 2 cadres). Une lecture = un canvas du panneau, jamais le
  document.
- **Iso 2:1** : `doc.pixelart.iso` (booléen, `op_pixelart({iso})`) ;
  `masque_losange(w, h)` = les pixels du losange inscrit ; quand iso est
  vrai et qu'aucune sélection n'est posée, la peinture est BORNÉE au losange
  (masque implicite) ; la grille de l'overlay trace le losange de tuile ;
  le raccord montre `pavage_iso(img)` = le losange répété aux décalages
  (±w/2, ±h/2) et son score = 1 − écart moyen RGB des paires de pixels
  adjacents entre la tuile centrale et ses voisines.
- **Rastériser** : `rasteriser(img, { cible_w, palette, dither })` =
  `pixeliser` puis `quantifier` (dither `aucun`) ou `dither_ordonne` (Bayer
  4 × 4) ou `dither_floyd` ; la commande remplace l'image éditée (journal
  `.pix<k>.png`, annulable) et met à jour `nat` ; palette = celle du
  document ou extraite à N couleurs ; champs dans le panneau.

## Cartographie des fichiers

| Fichier | Rôle |
|---|---|
| `frontend/vectorlab/js/mod-pixel.js` | `forme` carré du pinceau / gomme (T1) |
| `frontend/vectorlab/js/mod-pixelart.js` | `pixel_parfait` (T1), `dither_ordonne`, `dither_floyd`, `rasteriser` (T2), `pelure_double`, `masque_losange`, `pavage_iso` (T3) |
| `frontend/vectorlab/js/mod-doc.js` | `pixelart.iso` (T3) |
| `frontend/vectorlab/js/mod-contexte.js` | champs Forme / Parfait / Secondaire (T4) |
| `frontend/vectorlab/qa/pixel.test.mjs`, `pixelart.test.mjs`, `pixel_doc.test.mjs`, `contexte.test.mjs` | RED puis vert (T1–T4) |
| `frontend/vectorlab/js/mod-pixelui.js`, `vectorlab.css` | gestes (T5), ligne de temps + pelure (T6), iso + rastériser (T7) |

---

### Task 1 : pinceau carré et pixel-parfait (purs)

**Files :** Modify `mod-pixel.js`, `mod-pixelart.js`, `qa/pixel.test.mjs`, `qa/pixelart.test.mjs`

- [ ] **Step 1 : RED** — dans `pixel.test.mjs` (avant `if (echecs.length)`) :

```js
{
  const t = tampon(9, 9);
  pinceau(t, [[4, 4]], { rayon: 2, couleur: "#FF0000", durete: 1, forme: "carre" });
  const opaque = (x, y) => t.data[(y * 9 + x) * 4 + 3] === 255;
  ok("pinceau carré rayon 2 : le coin (2,2) est peint (Tchebychev), pas (1,4)", opaque(2, 2) && opaque(6, 6) && !opaque(1, 4) && !opaque(4, 1));
  const r = tampon(9, 9); pinceau(r, [[4, 4]], { rayon: 2, couleur: "#FF0000", durete: 1 });
  ok("pinceau rond rayon 2 : le coin (2,2) n'est PAS peint", r.data[(2 * 9 + 2) * 4 + 3] === 0 && r.data[(4 * 9 + 2) * 4 + 3] === 255);
  const g = tampon(5, 5); pinceau(g, [[2, 2]], { rayon: 2, couleur: "#00FF00", forme: "carre" }); gomme(g, [[2, 2]], { rayon: 1, forme: "carre" });
  ok("gomme carrée rayon 1 : le centre et (1,1) vidés, (0,0) reste", g.data[(2 * 5 + 2) * 4 + 3] === 0 && g.data[(1 * 5 + 1) * 4 + 3] === 0 && g.data[0 + 3] === 255);
}
```

et dans `pixelart.test.mjs` (importer `pixel_parfait`) :

```js
{
  const l = ligne_pixel(0, 0, 3, 2);            // Bresenham : (0,0) (1,1)? … contient des coins en L
  const p = pixel_parfait([[0, 0], [1, 0], [1, 1], [2, 1], [2, 2]]);
  ok("pixel-parfait : les coins en L perdent leur pixel médian → (0,0) (1,1) (2,2)", JSON.stringify(p) === "[[0,0],[1,1],[2,2]]", JSON.stringify(p));
  ok("un tracé déjà diagonal ou droit ne change pas", JSON.stringify(pixel_parfait([[0, 0], [1, 0], [2, 0]])) === "[[0,0],[1,0],[2,0]]" && pixel_parfait([[0, 0], [1, 1]]).length === 2);
  ok("moins de trois points : inchangé", pixel_parfait([[3, 3]]).length === 1 && pixel_parfait([]).length === 0);
  ok("l'entrée n'est pas mutée", (() => { const a = [[0, 0], [1, 0], [1, 1]]; pixel_parfait(a); return a.length === 3; })());
  ok("ligne_pixel reste brute (le filtre est à part)", l.length >= 4);
}
```

- [ ] **Step 2 : RED constaté** (`pixel_parfait is not a function` ; pinceau carré peint le rond).
- [ ] **Step 3 : implémenter** — mod-pixel : après `_disque`,

```js
// R lot 2 : l'estampe CARRÉE (distance de Tchebychev), même dureté
function _carre(img, cx, cy, rayon, durete, masque, fn) {
  const r = Math.max(0.5, +rayon || 1), d0 = r * Math.min(1, Math.max(0, durete));
  for (let y = Math.max(0, Math.floor(cy - r)); y <= Math.min(img.h - 1, Math.ceil(cy + r)); y++) {
    for (let x = Math.max(0, Math.floor(cx - r)); x <= Math.min(img.w - 1, Math.ceil(cx + r)); x++) {
      const d = Math.max(Math.abs(x - cx), Math.abs(y - cy));
      if (d > r) continue;
      let a = d <= d0 ? 1 : (r > d0 ? 1 - (d - d0) / (r - d0) : 1);
      a *= _m(masque, y * img.w + x);
      if (a > 0) fn(y * img.w + x, a);
    }
  }
}
const _estampe = (forme) => (forme === "carre" ? _carre : _disque);
```

`pinceau(img, points, { rayon = 1, couleur = "#000000", durete = 1, masque, forme = "rond" } = {})` et `gomme(…, forme = "rond")` appellent `_estampe(forme)(img, x, y, rayon, durete, masque, …)`. mod-pixelart :

```js
// lot 2 : pixel-parfait (Aseprite) — dans un coin en L (a, b, c) où a et c
// sont diagonaux, b est de trop ; on filtre en un passage, sans muter
export function pixel_parfait(points) {
  const out = [];
  for (const p of points || []) {
    const n = out.length;
    if (n >= 2) {
      const a = out[n - 2], b = out[n - 1];
      const orthoAB = (a[0] === b[0]) !== (a[1] === b[1]), orthoBP = (b[0] === p[0]) !== (b[1] === p[1]);
      const diagAP = Math.abs(a[0] - p[0]) === 1 && Math.abs(a[1] - p[1]) === 1;
      if (orthoAB && orthoBP && diagAP) { out[n - 1] = p; continue; }
    }
    out.push(p);
  }
  return out;
}
```

- [ ] **Step 4 : vert** — `node frontend/vectorlab/qa/run.mjs`. **Step 5 : commit** — `git commit --only frontend/vectorlab/js/mod-pixel.js frontend/vectorlab/js/mod-pixelart.js frontend/vectorlab/qa/pixel.test.mjs frontend/vectorlab/qa/pixelart.test.mjs -m "vectorlab pixel lot 2 : pinceau carre et crayon pixel-parfait (purs)"`

### Task 2 : tramage et rastérisation (purs)

**Files :** Modify `mod-pixelart.js`, `qa/pixelart.test.mjs`

- [ ] **Step 1 : RED** :

```js
{
  const { dither_ordonne, dither_floyd, rasteriser } = await import("../js/mod-pixelart.js");
  // un dégradé horizontal de gris 16 × 4, palette noir / blanc
  const g = tampon(16, 4); for (let y = 0; y < 4; y++) for (let x = 0; x < 16; x++) { const k = (y * 16 + x) * 4, v = Math.round(x * 255 / 15); g.data[k] = g.data[k + 1] = g.data[k + 2] = v; g.data[k + 3] = 255; }
  const pal = ["#000000", "#FFFFFF"];
  const o = dither_ordonne(g, pal), f = dither_floyd(g, pal), q = quantifier(g, pal);
  const blancs = (im) => { let n = 0; for (let i = 0; i < im.w * im.h; i++) if (im.data[i * 4] === 255) n++; return n; };
  ok("tramage ordonné : chaque pixel est DANS la palette", (() => { for (let i = 0; i < 64; i++) if (![0, 255].includes(o.data[i * 4])) return false; return true; })());
  ok("tramage ordonné : le milieu du dégradé mélange noir et blanc (la quantification seule fait un seuil)", (() => { let mix = 0; for (let y = 0; y < 4; y++) for (let x = 6; x < 10; x++) if (o.data[(y * 16 + x) * 4] !== q.data[(y * 16 + x) * 4]) mix++; return mix > 0; })());
  ok("tramage ordonné : autant de blancs qu'attendu à ± 20 % (≈ la moitié)", Math.abs(blancs(o) - 32) <= 13, blancs(o));
  ok("Floyd-Steinberg : dans la palette, et ≈ la moitié de blancs", (() => { for (let i = 0; i < 64; i++) if (![0, 255].includes(f.data[i * 4])) return false; return Math.abs(blancs(f) - 32) <= 10; })(), blancs(f));
  ok("Floyd : alpha conservé, pixels transparents ignorés", (() => { const t = tampon(4, 1); t.data[3] = 255; const r = dither_floyd(t, pal); return r.data[3] === 255 && r.data[7] === 0; })());
  ok("l'entrée n'est pas mutée", g.data[(2 * 16 + 8) * 4] === Math.round(8 * 255 / 15));
  // rastériser : 32 × 32 → 8 de large, palette 2, tramage
  const im = tampon(32, 32); for (let i = 0; i < 32 * 32; i++) { im.data[i * 4] = (i % 32) * 8; im.data[i * 4 + 1] = 0; im.data[i * 4 + 2] = 0; im.data[i * 4 + 3] = 255; }
  const r1 = rasteriser(im, { cible_w: 8, palette: ["#000000", "#FF0000"], dither: "aucun" });
  ok("rastériser : 8 × 8, palette respectée", r1.w === 8 && r1.h === 8 && [0, 255].includes(r1.data[0]) && [0, 255].includes(r1.data[(7 * 8 + 7) * 4]));
  ok("rastériser sans palette : pixelise seulement (couleurs libres)", rasteriser(im, { cible_w: 8 }).data[(3 * 8 + 4) * 4] > 0);
  let refus = 0; try { rasteriser(im, { cible_w: 0 }); } catch { refus++; } try { rasteriser(im, { cible_w: 8, palette: pal, dither: "yoyo" }); } catch { refus++; }
  ok("largeur nulle ou tramage inconnu → refus", refus === 2);
}
```

- [ ] **Step 2 : RED constaté**. **Step 3 : implémenter** (mod-pixelart, après `quantifier`) :

```js
/* ── lot 2 : tramage (True Pixel : None · Ordered · Floyd-S) et rastérisation ── */
const _BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
const _plusProche = (pal, r, g, b) => { let best = pal[0], d0 = Infinity; for (const c of pal) { const d = (c[0] - r) ** 2 + (c[1] - g) ** 2 + (c[2] - b) ** 2; if (d < d0) { d0 = d; best = c; } } return best; };
const _rgbPal = (palette) => palette.map((h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]);
export function dither_ordonne(img, palette, force = 32) {
  const pal = _rgbPal(palette), out = { w: img.w, h: img.h, data: new Uint8ClampedArray(img.data) };
  for (let y = 0; y < img.h; y++) for (let x = 0; x < img.w; x++) {
    const k = (y * img.w + x) * 4;
    if (out.data[k + 3] === 0) continue;
    const t = (_BAYER4[y & 3][x & 3] / 16 - 0.5) * force;
    const c = _plusProche(pal, out.data[k] + t, out.data[k + 1] + t, out.data[k + 2] + t);
    out.data[k] = c[0]; out.data[k + 1] = c[1]; out.data[k + 2] = c[2];
  }
  return out;
}
export function dither_floyd(img, palette) {
  const pal = _rgbPal(palette), out = { w: img.w, h: img.h, data: new Uint8ClampedArray(img.data) };
  const err = new Float32Array(img.w * img.h * 3);
  const diffuser = (x, y, e, f) => { if (x < 0 || x >= img.w || y >= img.h) return; const j = (y * img.w + x) * 3; err[j] += e[0] * f; err[j + 1] += e[1] * f; err[j + 2] += e[2] * f; };
  for (let y = 0; y < img.h; y++) for (let x = 0; x < img.w; x++) {
    const i = y * img.w + x, k = i * 4;
    if (out.data[k + 3] === 0) continue;
    const r = out.data[k] + err[i * 3], g = out.data[k + 1] + err[i * 3 + 1], b = out.data[k + 2] + err[i * 3 + 2];
    const c = _plusProche(pal, r, g, b), e = [r - c[0], g - c[1], b - c[2]];
    out.data[k] = c[0]; out.data[k + 1] = c[1]; out.data[k + 2] = c[2];
    diffuser(x + 1, y, e, 7 / 16); diffuser(x - 1, y + 1, e, 3 / 16); diffuser(x, y + 1, e, 5 / 16); diffuser(x + 1, y + 1, e, 1 / 16);
  }
  return out;
}
export const DITHERS = ["aucun", "ordonne", "floyd"];
export function rasteriser(img, { cible_w, palette = null, dither = "aucun" } = {}) {
  if (!(cible_w >= 1)) throw new Error("rastériser : largeur cible ≥ 1");
  if (!DITHERS.includes(dither)) throw new Error("rastériser : tramage aucun, ordonne ou floyd");
  const p = pixeliser(img, Math.round(cible_w));
  if (!palette || !palette.length) return p;
  return dither === "ordonne" ? dither_ordonne(p, palette) : dither === "floyd" ? dither_floyd(p, palette) : quantifier(p, palette);
}
```

- [ ] **Step 4 : vert**. **Step 5 : commit** — `… -m "vectorlab pixel lot 2 : tramage ordonne / Floyd-Steinberg et rasteriser (purs)"`

### Task 3 : pelure double, losange iso, pavage iso, `pixelart.iso` (purs)

**Files :** Modify `mod-pixelart.js`, `mod-doc.js`, `qa/pixelart.test.mjs`, `qa/pixel_doc.test.mjs`

- [ ] **Step 1 : RED** — pixelart :

```js
{
  const { pelure_double, masque_losange, pavage_iso } = await import("../js/mod-pixelart.js");
  const cur = tampon(4, 1), prev = tampon(4, 1), next = tampon(4, 1);
  const pose = (t, x, rgb) => { const k = x * 4; t.data[k] = rgb[0]; t.data[k + 1] = rgb[1]; t.data[k + 2] = rgb[2]; t.data[k + 3] = 255; };
  pose(cur, 0, [0, 255, 0]); pose(prev, 0, [9, 9, 9]); pose(prev, 1, [9, 9, 9]); pose(next, 2, [9, 9, 9]); pose(next, 3, [9, 9, 9]); pose(prev, 3, [9, 9, 9]);
  const d = pelure_double(cur, prev, next, 0.5);
  ok("pelure double : le courant intact, le précédent ROUGE à demi-alpha, le suivant BLEU", d.data[1] === 255 && d.data[3] === 255 && d.data[4] === 255 && d.data[6] === 128 && d.data[10] === 255 && d.data[8] === 0 && d.data[11] === 128, Array.from(d.data));
  ok("là où précédent ET suivant : mélange violet (rouge et bleu)", d.data[12] > 0 && d.data[14] > 0);
  const m = masque_losange(8, 4);
  ok("losange 8 × 4 : le centre dedans, les coins dehors, la rangée du milieu pleine", m[1 * 8 + 4] === 255 && m[0] === 0 && m[7] === 0 && m[3 * 8 + 0] === 0 && m[2 * 8 + 0] === 255 && m[2 * 8 + 7] === 255);
  ok("losange : ≈ la moitié des pixels", (() => { let n = 0; for (const v of m) if (v) n++; return n >= 14 && n <= 20; })());
  const tuile = tampon(8, 4); for (let i = 0; i < 32; i++) if (m[i]) { tuile.data[i * 4] = 100; tuile.data[i * 4 + 1] = 200; tuile.data[i * 4 + 2] = 50; tuile.data[i * 4 + 3] = 255; }
  const pv = pavage_iso(tuile);
  ok("pavage iso : 3 × 3 tuiles → 24 × 12, score 1 pour une tuile unie", pv.img.w === 24 && pv.img.h === 12 && pv.score === 1, JSON.stringify([pv.img.w, pv.img.h, pv.score]));
  ok("pavage iso : le centre est plein et une voisine décalée (w/2, h/2) aussi", pv.img.data[((6 * 24) + 12) * 4 + 3] === 255 && pv.img.data[((3 * 24) + 8) * 4 + 3] === 255);
  const t2 = { w: 8, h: 4, data: new Uint8ClampedArray(tuile.data) }; for (let x = 0; x < 4; x++) for (let y = 0; y < 4; y++) if (m[y * 8 + x]) { t2.data[(y * 8 + x) * 4] = 250; }
  ok("une tuile dont la moitié gauche diffère a un score < 1", pavage_iso(t2).score < 1);
}
```

pixel_doc :

```js
{
  const d = { v: 1, taille: { w: 64, h: 64 }, calques: [{ id: "c", nom: "c", visible: true, objets: [] }] };
  op_pixelart(d, { tuile: { w: 32, h: 16 }, iso: true });
  ok("pixelart.iso accepté", d.pixelart.iso === true);
  let refus = 0; try { op_pixelart(d, { iso: "oui" }); } catch { refus++; }
  ok("iso non booléen refusé", refus === 1);
  op_pixelart(d, { iso: null });
  ok("iso retiré par null", d.pixelart.iso === undefined);
  parserDoc(JSON.parse(JSON.stringify({ ...d, pixelart: { tuile: { w: 32, h: 16 }, iso: true } })));
  ok("parserDoc accepte iso", true);
}
```

(vérifier les imports `op_pixelart`, `parserDoc` en tête de `pixel_doc.test.mjs` et adapter le gabarit de document à celui du banc).

- [ ] **Step 2 : RED constaté**. **Step 3 : implémenter** — mod-pixelart :

```js
/* ── lot 2 : pelure double (Sprite Editor : rouge = précédent, bleu = suivant) ── */
export function pelure_double(courant, precedent, suivant, alpha = 0.5) {
  const out = { w: courant.w, h: courant.h, data: new Uint8ClampedArray(courant.data) };
  const teinter = (src, rgbT) => {
    if (!src) return;
    for (let y = 0; y < Math.min(courant.h, src.h); y++) for (let x = 0; x < Math.min(courant.w, src.w); x++) {
      const i = (y * courant.w + x) * 4, j = (y * src.w + x) * 4;
      if (courant.data[i + 3] !== 0 || src.data[j + 3] === 0) continue;
      const a = Math.round(src.data[j + 3] * alpha);
      if (out.data[i + 3] === 0) { out.data[i] = rgbT[0]; out.data[i + 1] = rgbT[1]; out.data[i + 2] = rgbT[2]; out.data[i + 3] = a; }
      else { out.data[i] = Math.max(out.data[i], rgbT[0]); out.data[i + 1] = Math.max(out.data[i + 1], rgbT[1]); out.data[i + 2] = Math.max(out.data[i + 2], rgbT[2]); out.data[i + 3] = Math.max(out.data[i + 3], a); }
    }
  };
  teinter(precedent, [255, 0, 0]); teinter(suivant, [0, 0, 255]);
  return out;
}
/* ── lot 2 : tuile iso 2:1 — le losange inscrit, le pavage aux décalages (±w/2, ±h/2), le score de raccord ── */
export function masque_losange(w, h) {
  const m = new Uint8Array(w * h), cx = w / 2, cy = h / 2;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (Math.abs((x + 0.5 - cx) / cx) + Math.abs((y + 0.5 - cy) / cy) <= 1) m[y * w + x] = 255;
  }
  return m;
}
export function pavage_iso(img) {
  const { w, h } = img, m = masque_losange(w, h), out = _tampon(w * 3, h * 3), qui = new Int8Array(w * 3 * h * 3).fill(-1);
  // les neuf tuiles : centre (w, h) et les voisines aux décalages (±w/2, ±h/2) et (±w, 0), (0, ±h)
  const pos = [[w, h, 0], [w / 2, h / 2, 1], [3 * w / 2, h / 2, 2], [w / 2, 3 * h / 2, 3], [3 * w / 2, 3 * h / 2, 4], [0, h, 5], [2 * w, h, 6], [w, 0, 7], [w, 2 * h, 8]];
  for (const [ox, oy, id] of pos) for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (!m[y * w + x]) continue;
    const tx = Math.round(ox) + x, ty = Math.round(oy) + y;
    if (tx < 0 || ty < 0 || tx >= w * 3 || ty >= h * 3) continue;
    const k = (ty * w * 3 + tx) * 4, j = (y * w + x) * 4;
    out.data[k] = img.data[j]; out.data[k + 1] = img.data[j + 1]; out.data[k + 2] = img.data[j + 2]; out.data[k + 3] = img.data[j + 3];
    qui[ty * w * 3 + tx] = id;
  }
  // score : écart RGB moyen entre pixels adjacents dont l'un est au centre et l'autre chez une voisine
  let s = 0, n = 0;
  const W = w * 3;
  for (let y = 0; y < h * 3; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x; if (qui[i] !== 0) continue;
    for (const [dx, dy] of [[1, 0], [0, 1], [-1, 0], [0, -1]]) {
      const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= W || ny >= h * 3) continue;
      const j = ny * W + nx; if (qui[j] <= 0) continue;
      for (let c = 0; c < 3; c++) s += Math.abs(out.data[i * 4 + c] - out.data[j * 4 + c]); n++;
    }
  }
  return { img: out, score: n ? Math.round((1 - (s / n) / 255) * 1000) / 1000 : 1 };
}
```

mod-doc : `_CLES_PIXELART = ["tuile", "palette", "symetrie", "iso"]` ; dans `_validerPixelart` : `if (p.iso !== undefined && typeof p.iso !== "boolean") throw new Error("pixelart: iso booléen");` ; dans `op_pixelart` : `if (k === "iso") p.iso = v;` (garder la branche `null` → delete).

- [ ] **Step 4 : vert** (`pixelart`, `pixel_doc`, `run.mjs`). **Step 5 : commit** — `… -m "vectorlab pixel lot 2 : pelure double, losange iso, pavage iso et pixelart.iso (purs)"`

### Task 4 : champs de contexte (pur)

**Files :** Modify `mod-contexte.js`, `qa/contexte.test.mjs`

- [ ] **Step 1 : RED** — dans `contexte.test.mjs`, trouver le gabarit d'appel de `champs_de(...)` (l'état factice) et ajouter :

```js
{
  const px = { rayon: 4, durete: 1, forme: "carre", parfait: false, secondaire: null };
  const c1 = champs_de({ outil: "px-pinceau", px }).map((c) => c.id);
  ok("pinceau : champ Forme (rond / carré) et Secondaire", c1.includes("pxForme") && c1.includes("pxSecondaire"));
  const c2 = champs_de({ outil: "px-crayon", px });
  ok("crayon : bascule Pixel-parfait (valeur lue dans etat.px.parfait)", c2.some((c) => c.id === "pxParfait" && c.type === "bascule" && c.valeur === false) && c2.some((c) => c.id === "pxSecondaire"));
  ok("gomme : Forme mais pas Secondaire", champs_de({ outil: "px-gomme", px }).some((c) => c.id === "pxForme") && !champs_de({ outil: "px-gomme", px }).some((c) => c.id === "pxSecondaire"));
}
```

(adapter `champs_de` au nom réel de la fonction exportée et à la forme de son argument, lus dans le fichier).

- [ ] **Step 2 : RED constaté**. **Step 3 : implémenter** : le `case "px-pinceau": …` devient deux cas — `px-pinceau` / `px-cloner` / `px-flou` / `px-eclaircir` / `px-assombrir` : `[…rayon, dureté, select("pxForme", "Forme", px.forme || "rond", [{id:"rond", libelle:"Rond"}, {id:"carre", libelle:"Carré"}]), { id: "pxSecondaire", type: "couleur", libelle: "Secondaire", valeur: px.secondaire || "" }]` (le cloner / flou / … n'ont pas la secondaire : ne l'ajouter qu'à `px-pinceau`) ; `px-gomme` : rayon, dureté, Forme ; `px-crayon` : `[{ id: "pxParfait", type: "bascule", libelle: "Pixel-parfait", valeur: px.parfait !== false }, { id: "pxSecondaire", type: "couleur", … }]`. Si le type `couleur` n'existe pas dans mod-barrecontexte, le rendre comme un `<input type="color">` + bouton « ∅ » (transparent) — lire le rendu des types dans `mod-barrecontexte.js` avant.

- [ ] **Step 4 : vert**. **Step 5 : commit**.

### Task 5 : les gestes du Sprite Editor (UI)

**Files :** Modify `mod-pixelui.js`, `vectorlab.css`

- [ ] `etat.px` gagne `secondaire: null, forme: "rond", parfait: true, dernier: null`. `HINTS_PIXEL` : pinceau « … · clic droit = secondaire (∅ = gomme) · Maj+clic = segment depuis le dernier point · Alt+clic = pipette », crayon idem + « pixel-parfait ».
- [ ] `stage.addEventListener("contextmenu", (ev) => { if (estPixel()) ev.preventDefault(); }, true)`.
- [ ] `pointerdown` : accepter `ev.button === 2` pour les outils de peinture (`px-pinceau`, `px-crayon`, `px-ligne`, `px-rectpx`, `px-seau`) → `geste.droit = true` et la couleur du geste = `etat.px.secondaire` ; si `secondaire === null` et l'outil est pinceau / crayon → le geste devient une gomme (`type: "px-gomme"` avec la forme du pinceau). Alt+clic (hors cloner) → pipette : lire le pixel du tampon ; alpha > 0 → `etat.px.couleur` (ou `secondaire` si bouton droit), `rendrePanneau()`, `VL.toast(hex)`, retour. Maj+clic avec `etat.px.dernier` et outil pinceau / crayon / gomme → segment `[dernier, p]` appliqué au tampon (crayon : `pixel_parfait(ligne_pixel(...))` si `parfait`) puis `commettre()`, retour.
- [ ] `appliquer` : `opts()` lit `forme: etat.px.forme` et la couleur du geste ; crayon en mode parfait : `geste.base` (copie du tampon au pointerdown), à chaque move `apercu = copie de base` + tracé entier `pixel_parfait(points→ligne_pixel)` ; au pointerup pareil.
- [ ] Après chaque geste appliqué : `etat.px.dernier = dernier point` (en pixels natifs).
- [ ] Raccourci `x` (persona Pixel, hors champ) : échange primaire / secondaire ; la barre contextuelle `pxSecondaire` et `pxForme` / `pxParfait` mettent à jour `etat.px` (via le mécanisme existant de `mod-barrecontexte` : `champ → etat.px[clé]` ; lire comment `pxRayon` est relié et faire pareil).
- [ ] `node --check`, `run.mjs` ; commit `… -m "vectorlab pixel lot 2 : secondaire au clic droit, Maj-segment, Alt-pipette, forme du pinceau, crayon pixel-parfait"`.

### Task 6 : ligne de temps et pelure double (UI)

**Files :** Modify `mod-pixelui.js`, `vectorlab.css`

- [ ] Panneau Pixel : la section « Cadres » devient **« Ligne de temps »** : rangée `#pxTimeline` de vignettes (canvas 40 px, `data-id`, courant surligné), boutons ▶/⏸ (`#pxPlay`), boucle (`#pxLoop`, coché), FPS (`#pxFps`, 12), ＋ Dupliquer (`#pxCadreDup`), ＋ Vide (`#pxCadreVide`), ✕ Supprimer (`#pxCadreSuppr`, désactivé si < 2 cadres), pelure (case existante, désormais rouge / bleu) ; un canvas de lecture `#pxLecture` (taille du cadre, `image-rendering: pixelated`, zoom ajusté à 120 px).
- [ ] Lecture : rAF dans le panneau, `player` local `{i, acc, last, playing}` ; les tampons via `tamponsDe(cadres)` (cache) ; Entrée (persona Pixel, rien de focalisé) bascule lecture.
- [ ] Dupliquer = `deposerNouvelleImage(copie du tampon, rect à droite du courant)` + `op_ajouter` dans « cadres » à l'index suivant (commande : `c.objets.splice(i + 1, 0, objet)`) ; Vide = tampon transparent de la même taille ; Supprimer = `VL.executer(op_supprimer, [id])` puis `editer(voisin)`.
- [ ] Overlay : `pelure(t, prec, .5)` remplacé par `pelure_double(t, prec, suiv, .5)` (suiv = cache du cadre `i + 1`).
- [ ] Commit `… -m "vectorlab pixel lot 2 : ligne de temps (vignettes, lecture, dupliquer / vide / supprimer) et pelure rouge / bleue"`.

### Task 7 : tuile iso et « Rastériser cette image » (UI)

**Files :** Modify `mod-pixelui.js`, `vectorlab.css`

- [ ] Section « Pixel-art » du panneau : case **« Tuile iso 2:1 »** (`#pxIso`) → `VL.executer(op_pixelart, { iso: !!checked })` ; en iso, le raccord (`#pxRaccordCv`) montre `pavage_iso(t)` et son score ; `opts()` : si `etat.doc.pixelart.iso && !etat.px.masque` → `masque: masque_losange(t.w, t.h)` (peinture bornée) ; overlay : quand iso, tracer le losange de chaque tuile (`M cx,y0 L x1,cy L cx,y1 L x0,cy Z` par cellule) à la place des lignes de tuile.
- [ ] Section **« Rastériser »** (visible quand une image est éditée ou sélectionnée) : largeur cible (`#pxRastW`, défaut `tuile.w` ou 64), palette (`#pxRastPal` : « aucune » / « du document » / « extraire N »), tramage (`#pxRastDither` : aucun / ordonné / Floyd-Steinberg), bouton **Rastériser cette image** → `rasteriser(t, …)` → `etat.px.tampon = r` → `commettre({ w: r.w, h: r.h })` (l'objet garde son rectangle, `nat` change) ; `VL.actions.pixel.rasteriser = …` ; hint dans le panneau : « une image générée (Library → Image) devient un calque pixel éditable ».
- [ ] Commit `… -m "vectorlab pixel lot 2 : tuile iso 2:1 (losange, pavage, score) et Rasteriser cette image (pixeliser + palette + tramage)"`.

### Task 8 : preuve en réel (8799, 1400 × 900)

- [ ] Document avec une image 16 × 16 (PNG fabriqué → `POST /vector/docs/{id}/images` → objet image) ; persona Pixel ; `VL.pixelEditer(id)`.
- [ ] Gestes `PointerEvent` sur `#stage` : pinceau bouton droit avec secondaire `#00FF00` → pixel vert ; secondaire ∅ → pixel transparent ; Alt+clic sur un pixel rouge → `etat.px.couleur === "#FF0000"` ; Maj+clic → segment posé (pixels entre les deux points) ; forme carré rayon 2 → coin peint ; crayon parfait : tracé en escalier → aucun coin en L dans le résultat (relire le tampon) ; `x` échange les couleurs.
- [ ] Ligne de temps : ＋ Dupliquer → 2 cadres, vignettes 2, ▶ fait varier `i` (deux lectures), Vide → 3, Supprimer → 2 ; pelure : overlay contient une couche rouge ET une couche bleue (`pelure_double` mesurée sur le cadre du milieu).
- [ ] Iso : `pxIso` coché → `doc.pixelart.iso === true`, overlay avec des losanges, peinture hors losange refusée (pixel de coin reste transparent), raccord `pavage_iso` 3w × 3h avec score.
- [ ] Rastériser : image 64 × 64 dégradé → cible 16, palette 4 extraites, Floyd → `nat` 16 × 16, ≤ 4 couleurs, rev incrémentée, annulable (`/annuler`).
- [ ] 0 erreur ; `taskkill` 8799 ; `preset: desktop`.

### Task 9 : déploiement (statiques seuls) et Task 10 : relevé, mémoire, push

- [ ] Installé = base `72e8093` par hash pour chaque fichier touché ; sauvegarde `_backup_predeploy_2026-09-19-pixel-lot2` ; `git archive HEAD` ; hash = cible ; aucune relance.
- [ ] Relevé en tête de ce plan ; mémoire (`spritelab-feuille.md` : lot 2 livré + pièges ; ligne MEMORY.md) ; push.
