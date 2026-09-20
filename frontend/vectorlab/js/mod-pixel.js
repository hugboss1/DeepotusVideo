// mod-pixel.js — le persona PIXEL du lot E (D1) : outils raster PURS sur un
// tampon {w, h, data: Uint8ClampedArray} (le format d'ImageData, sans DOM).
// Pinceau et gomme (disques estampés le long du trait, dureté), seau
// (contigu ou global, tolérance), sélections en MASQUE Uint8Array (0..255) —
// rectangle, lasso, baguette, par couleur, croître / contracter / inverser —,
// masque de calque, ajustements par LUT (niveaux, courbes, HSL, N&B, seuil),
// flou en boîte séparable, clonage, extraction. Module FEUILLE.

export function tampon(w, h) {
  if (!(w >= 1 && h >= 1)) throw new Error("tampon : taille ≥ 1 requise");
  return { w: Math.round(w), h: Math.round(h), data: new Uint8ClampedArray(Math.round(w) * Math.round(h) * 4) };
}
export function rgb_de(hex) {
  const s = String(hex || "").trim().replace(/^#/, "");
  const h = s.length === 3 ? s.split("").map((c) => c + c).join("") : s;
  if (!/^[0-9a-fA-F]{6}$/.test(h)) throw new Error(`couleur hex attendue : ${hex}`);
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
const _m = (masque, i) => (masque ? masque[i] / 255 : 1);

// source-over d'une couleur opaque à l'alpha `a` (0..1) sur le pixel i
function _poser(img, i, rgb, a) {
  if (a <= 0) return;
  const d = img.data, o = i * 4;
  const da = d[o + 3] / 255, ra = a + da * (1 - a);
  if (ra <= 0) return;
  for (let k = 0; k < 3; k++) d[o + k] = Math.round((rgb[k] * a + d[o + k] * da * (1 - a)) / ra);
  d[o + 3] = Math.round(ra * 255);
}
function* _estampes(points, rayon) {
  const pas = Math.max(0.25, rayon / 2);
  if (points.length === 1) { yield points[0]; return; }
  for (let k = 0; k + 1 < points.length; k++) {
    const [x0, y0] = points[k], [x1, y1] = points[k + 1];
    const L = Math.hypot(x1 - x0, y1 - y0), n = Math.max(1, Math.ceil(L / pas));
    for (let s = 0; s <= n; s++) yield [x0 + (x1 - x0) * s / n, y0 + (y1 - y0) * s / n];
  }
}
function _disque(img, cx, cy, rayon, durete, masque, fn) {
  const r = Math.max(0.5, +rayon || 1), d0 = r * Math.min(1, Math.max(0, durete));
  for (let y = Math.max(0, Math.floor(cy - r)); y <= Math.min(img.h - 1, Math.ceil(cy + r)); y++) {
    for (let x = Math.max(0, Math.floor(cx - r)); x <= Math.min(img.w - 1, Math.ceil(cx + r)); x++) {
      const d = Math.hypot(x - cx, y - cy);
      if (d > r) continue;
      let a = d <= d0 ? 1 : (r > d0 ? 1 - (d - d0) / (r - d0) : 1);
      a *= _m(masque, y * img.w + x);
      if (a > 0) fn(y * img.w + x, a);
    }
  }
}
// lot 2 : l'estampe CARRÉE (Sprite Editor : ROUND / SQUARE) — distance de
// Tchebychev, même dureté
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
export function pinceau(img, points, { rayon = 1, couleur = "#000000", durete = 1, masque, forme = "rond" } = {}) {
  const rgb = rgb_de(couleur);
  const vus = new Map();                      // un pixel n'est posé qu'à son alpha MAX du trait
  for (const [x, y] of _estampes(points, rayon)) {
    _estampe(forme)(img, x, y, rayon, durete, masque, (i, a) => { if (!vus.has(i) || vus.get(i) < a) vus.set(i, a); });
  }
  for (const [i, a] of vus) _poser(img, i, rgb, a);
  return img;
}
export function gomme(img, points, { rayon = 1, durete = 1, masque, forme = "rond" } = {}) {
  const vus = new Map();
  for (const [x, y] of _estampes(points, rayon)) {
    _estampe(forme)(img, x, y, rayon, durete, masque, (i, a) => { if (!vus.has(i) || vus.get(i) < a) vus.set(i, a); });
  }
  for (const [i, a] of vus) img.data[i * 4 + 3] = Math.round(img.data[i * 4 + 3] * (1 - a));
  return img;
}

/* ── seau et sélections ── */
function _proche(d, i, cible, tol) {
  const o = i * 4;
  return Math.abs(d[o] - cible[0]) <= tol && Math.abs(d[o + 1] - cible[1]) <= tol
      && Math.abs(d[o + 2] - cible[2]) <= tol && Math.abs(d[o + 3] - cible[3]) <= tol;
}
function _region(img, x, y, tol) {
  const { w, h, data } = img;
  if (!(x >= 0 && y >= 0 && x < w && y < h)) throw new Error("point hors du tampon");
  const i0 = (y | 0) * w + (x | 0), cible = Array.from(data.slice(i0 * 4, i0 * 4 + 4));
  const m = new Uint8Array(w * h);
  const pile = [i0];
  m[i0] = 255;
  while (pile.length) {
    const i = pile.pop(), px = i % w, py = (i - px) / w;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = px + dx, ny = py + dy;
      if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
      const j = ny * w + nx;
      if (m[j] || !_proche(data, j, cible, tol)) continue;
      m[j] = 255; pile.push(j);
    }
  }
  return { m, cible };
}
export function seau(img, x, y, couleur, { tolerance = 0, global = false, masque } = {}) {
  const rgb = rgb_de(couleur);
  const { m, cible } = _region(img, x, y, tolerance);
  const n = img.w * img.h;
  for (let i = 0; i < n; i++) {
    const dedans = global ? _proche(img.data, i, cible, tolerance) : m[i] === 255;
    if (dedans) _poser(img, i, rgb, _m(masque, i));
  }
  return img;
}
export function sel_rect(w, h, r) {
  const m = new Uint8Array(w * h);
  for (let y = Math.max(0, r.y); y < Math.min(h, r.y + r.h); y++) for (let x = Math.max(0, r.x); x < Math.min(w, r.x + r.w); x++) m[y * w + x] = 255;
  return m;
}
export function sel_lasso(w, h, poly) {
  const m = new Uint8Array(w * h);
  if (!poly || poly.length < 3) return m;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const px = x + 0.5, py = y + 0.5;
    let dedans = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const [xi, yi] = poly[i], [xj, yj] = poly[j];
      if ((yi > py) !== (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi) dedans = !dedans;
    }
    if (dedans) m[y * w + x] = 255;
  }
  return m;
}
export function sel_baguette(img, x, y, tol = 0) { return _region(img, x, y, tol).m; }
export function sel_couleur(img, couleur, tol = 0) {
  const cible = [...rgb_de(couleur), 255];
  const m = new Uint8Array(img.w * img.h);
  for (let i = 0; i < m.length; i++) if (_proche(img.data, i, cible, tol)) m[i] = 255;
  return m;
}
function _morpho(m, w, h, n, dilate) {
  let cur = m;
  for (let k = 0; k < n; k++) {
    const out = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let v = dilate ? 0 : 255;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const nx = x + dx, ny = y + dy;
        const s = (nx < 0 || ny < 0 || nx >= w || ny >= h) ? 0 : cur[ny * w + nx];
        v = dilate ? Math.max(v, s) : Math.min(v, s);
      }
      out[y * w + x] = v;
    }
    cur = out;
  }
  return cur;
}
export const sel_croitre = (m, w, h, n = 1) => _morpho(m, w, h, n, true);
export const sel_contracter = (m, w, h, n = 1) => _morpho(m, w, h, n, false);
export function sel_inverser(m) { const o = new Uint8Array(m.length); for (let i = 0; i < m.length; i++) o[i] = 255 - m[i]; return o; }
export function sel_bbox(m, w, h) {
  let x0 = w, y0 = h, x1 = -1, y1 = -1;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (m[y * w + x]) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
  return x1 < 0 ? null : { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 };
}
export function masque_calque(img, m) {
  for (let i = 0; i < img.w * img.h; i++) img.data[i * 4 + 3] = Math.min(img.data[i * 4 + 3], m[i]);
  return img;
}

/* ── ajustements par LUT (respectent le masque) ── */
function _lut(img, lut, masque) {
  const d = img.data;
  for (let i = 0; i < img.w * img.h; i++) {
    const k = _m(masque, i);
    if (k <= 0) continue;
    for (let c = 0; c < 3; c++) {
      const v = d[i * 4 + c], n = lut[v];
      d[i * 4 + c] = k >= 1 ? n : Math.round(v + (n - v) * k);
    }
  }
  return img;
}
export function niveaux(img, { noir = 0, blanc = 255, gamma = 1 } = {}, masque) {
  const lut = new Uint8ClampedArray(256), g = gamma > 0 ? 1 / gamma : 1;
  for (let v = 0; v < 256; v++) lut[v] = Math.round(255 * Math.pow(Math.min(1, Math.max(0, (v - noir) / Math.max(1e-9, blanc - noir))), g));
  return _lut(img, lut, masque);
}
export function courbes(img, points, masque) {
  const pts = (points || []).slice().sort((a, b) => a[0] - b[0]);
  if (pts.length < 2) throw new Error("courbes : deux points au moins");
  const lut = new Uint8ClampedArray(256);
  for (let v = 0; v < 256; v++) {
    let k = 0;
    while (k + 1 < pts.length - 1 && pts[k + 1][0] <= v) k++;
    const [x0, y0] = pts[k], [x1, y1] = pts[k + 1];
    lut[v] = Math.round(x1 === x0 ? y0 : y0 + (y1 - y0) * (v - x0) / (x1 - x0));
  }
  return _lut(img, lut, masque);
}
function _rgb2hsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const M = Math.max(r, g, b), m = Math.min(r, g, b), l = (M + m) / 2;
  if (M === m) return [0, 0, l];
  const d = M - m, s = l > 0.5 ? d / (2 - M - m) : d / (M + m);
  let h = M === r ? (g - b) / d + (g < b ? 6 : 0) : M === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
}
function _hsl2rgb(h, s, l) {
  const f = (n) => { const k = (n + h / 30) % 12, a = s * Math.min(l, 1 - l); return l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)); };
  return [f(0), f(8), f(4)].map((v) => Math.round(v * 255));
}
export function hsl(img, { h = 0, s = 0, l = 0 } = {}, masque) {
  const d = img.data;
  for (let i = 0; i < img.w * img.h; i++) {
    const k = _m(masque, i);
    if (k <= 0) continue;
    let [hh, ss, ll] = _rgb2hsl(d[i * 4], d[i * 4 + 1], d[i * 4 + 2]);
    hh = ((hh + h) % 360 + 360) % 360;
    ss = Math.min(1, Math.max(0, ss + s / 100));
    ll = Math.min(1, Math.max(0, ll + l / 100));
    const [r, g, b] = _hsl2rgb(hh, ss, ll);
    d[i * 4] = Math.round(d[i * 4] + (r - d[i * 4]) * k);
    d[i * 4 + 1] = Math.round(d[i * 4 + 1] + (g - d[i * 4 + 1]) * k);
    d[i * 4 + 2] = Math.round(d[i * 4 + 2] + (b - d[i * 4 + 2]) * k);
  }
  return img;
}
const _lum = (d, o) => 0.299 * d[o] + 0.587 * d[o + 1] + 0.114 * d[o + 2];
export function noir_blanc(img, masque) {
  const d = img.data;
  for (let i = 0; i < img.w * img.h; i++) {
    const k = _m(masque, i);
    if (k <= 0) continue;
    const y = Math.round(_lum(d, i * 4));
    for (let c = 0; c < 3; c++) d[i * 4 + c] = Math.round(d[i * 4 + c] + (y - d[i * 4 + c]) * k);
  }
  return img;
}
export function seuil(img, v = 128, masque) {
  const d = img.data;
  for (let i = 0; i < img.w * img.h; i++) {
    if (_m(masque, i) <= 0) continue;
    const t = _lum(d, i * 4) >= v ? 255 : 0;
    d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = t;
  }
  return img;
}

/* ── flou en boîte séparable, clonage, extraction ── */
export function flou(img, rayon = 1, masque) {
  const r = Math.max(0, Math.round(rayon));
  if (!r) return img;
  const { w, h } = img, src = img.data, tmp = new Float32Array(w * h * 4), out = new Float32Array(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) for (let c = 0; c < 4; c++) {
    let s = 0, n = 0;
    for (let k = -r; k <= r; k++) { const xx = x + k; if (xx >= 0 && xx < w) { s += src[(y * w + xx) * 4 + c]; n++; } }
    tmp[(y * w + x) * 4 + c] = s / n;
  }
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) for (let c = 0; c < 4; c++) {
    let s = 0, n = 0;
    for (let k = -r; k <= r; k++) { const yy = y + k; if (yy >= 0 && yy < h) { s += tmp[(yy * w + x) * 4 + c]; n++; } }
    out[(y * w + x) * 4 + c] = s / n;
  }
  for (let i = 0; i < w * h; i++) {
    const k = _m(masque, i);
    if (k <= 0) continue;
    for (let c = 0; c < 4; c++) src[i * 4 + c] = Math.round(src[i * 4 + c] + (out[i * 4 + c] - src[i * 4 + c]) * k);
  }
  return img;
}
export function cloner(img, sx, sy, dx, dy, rayon = 4) {
  const copie = new Uint8ClampedArray(img.data), r = Math.max(0.5, rayon);
  for (let y = Math.max(0, Math.floor(dy - r)); y <= Math.min(img.h - 1, Math.ceil(dy + r)); y++) {
    for (let x = Math.max(0, Math.floor(dx - r)); x <= Math.min(img.w - 1, Math.ceil(dx + r)); x++) {
      if (Math.hypot(x - dx, y - dy) > r) continue;
      const xs = Math.round(x - dx + sx), ys = Math.round(y - dy + sy);
      if (xs < 0 || ys < 0 || xs >= img.w || ys >= img.h) continue;
      for (let c = 0; c < 4; c++) img.data[(y * img.w + x) * 4 + c] = copie[(ys * img.w + xs) * 4 + c];
    }
  }
  return img;
}
export function extraire(img, m) {
  const b = sel_bbox(m, img.w, img.h);
  if (!b) throw new Error("extraire : aucune sélection");
  const out = tampon(b.w, b.h);
  for (let y = 0; y < b.h; y++) for (let x = 0; x < b.w; x++) {
    const i = (y + b.y) * img.w + (x + b.x), j = y * b.w + x;
    for (let c = 0; c < 3; c++) out.data[j * 4 + c] = img.data[i * 4 + c];
    out.data[j * 4 + 3] = Math.round(img.data[i * 4 + 3] * m[i] / 255);
  }
  out.x = b.x; out.y = b.y;
  return out;
}
