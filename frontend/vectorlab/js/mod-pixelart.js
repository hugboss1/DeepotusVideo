// mod-pixelart.js — le complément Aseprite du lot E : géométrie pixel-parfaite
// (Bresenham, rectangle), symétrie, palette indexée par median cut,
// quantification, pixelisation au plus proche voisin, score de raccord 3×3
// (la métrique du Tilelab : différence des bords opposés), feuille de tuiles
// + index JSON, bande de cadres, pelure d'oignon. Module FEUILLE, tampons
// {w, h, data} comme mod-pixel.

const _tampon = (w, h) => ({ w, h, data: new Uint8ClampedArray(w * h * 4) });
const _hex = (r, g, b) => "#" + [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0").toUpperCase()).join("");
function _rgb(hex) {
  const s = String(hex).replace(/^#/, "");
  const h = s.length === 3 ? s.split("").map((c) => c + c).join("") : s;
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

// lot 2 : pixel-parfait (Aseprite) — dans un coin en L (a, b, c) où a et c
// sont diagonaux, b est de trop ; un seul passage, l'entrée n'est pas mutée
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
export function ligne_pixel(x0, y0, x1, y1) {
  x0 |= 0; y0 |= 0; x1 |= 0; y1 |= 0;
  const pts = [], dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  for (;;) {
    pts.push([x0, y0]);
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 >= dy) { err += dy; x0 += sx; }
    if (e2 <= dx) { err += dx; y0 += sy; }
  }
  return pts;
}
export function rect_pixel(x0, y0, x1, y1) {
  const xa = Math.min(x0, x1) | 0, xb = Math.max(x0, x1) | 0, ya = Math.min(y0, y1) | 0, yb = Math.max(y0, y1) | 0;
  const vus = new Set(), pts = [];
  const add = (x, y) => { const k = x + "," + y; if (!vus.has(k)) { vus.add(k); pts.push([x, y]); } };
  for (let x = xa; x <= xb; x++) { add(x, ya); add(x, yb); }
  for (let y = ya; y <= yb; y++) { add(xa, y); add(xb, y); }
  return pts;
}
export function symetrie(points, w, h, { h: horiz = false, v: vert = false } = {}) {
  const vus = new Set(), out = [];
  const add = (x, y) => { const k = x + "," + y; if (!vus.has(k)) { vus.add(k); out.push([x, y]); } };
  for (const [x, y] of points) {
    add(x, y);
    if (horiz) add(w - 1 - x, y);
    if (vert) add(x, h - 1 - y);
    if (horiz && vert) add(w - 1 - x, h - 1 - y);
  }
  return out;
}

/* ── palette (median cut) et quantification ── */
export function palette_extraire(img, n = 16) {
  const cible = Math.min(64, Math.max(2, n | 0));
  const px = [];
  for (let i = 0; i < img.w * img.h; i++) if (img.data[i * 4 + 3] >= 128) px.push([img.data[i * 4], img.data[i * 4 + 1], img.data[i * 4 + 2]]);
  if (!px.length) return [];
  let boites = [px];
  while (boites.length < cible) {
    let iMax = -1, eMax = -1, cMax = 0;
    boites.forEach((b, i) => {
      if (b.length < 2) return;
      for (let c = 0; c < 3; c++) {
        let lo = 255, hi = 0;
        for (const p of b) { if (p[c] < lo) lo = p[c]; if (p[c] > hi) hi = p[c]; }
        if (hi - lo > eMax) { eMax = hi - lo; iMax = i; cMax = c; }
      }
    });
    if (iMax < 0 || eMax <= 0) break;
    const b = boites[iMax].slice().sort((p, q) => p[cMax] - q[cMax]), m = b.length >> 1;
    boites.splice(iMax, 1, b.slice(0, m), b.slice(m));
  }
  const out = new Set();
  for (const b of boites) {
    const s = [0, 0, 0];
    for (const p of b) { s[0] += p[0]; s[1] += p[1]; s[2] += p[2]; }
    out.add(_hex(s[0] / b.length, s[1] / b.length, s[2] / b.length));
  }
  return [...out];
}
export function quantifier(img, palette) {
  if (!palette || !palette.length) throw new Error("quantifier : palette vide");
  const pal = palette.map(_rgb), d = img.data;
  for (let i = 0; i < img.w * img.h; i++) {
    if (d[i * 4 + 3] === 0) continue;
    let best = 0, bd = Infinity;
    for (let k = 0; k < pal.length; k++) {
      const dd = (d[i * 4] - pal[k][0]) ** 2 + (d[i * 4 + 1] - pal[k][1]) ** 2 + (d[i * 4 + 2] - pal[k][2]) ** 2;
      if (dd < bd) { bd = dd; best = k; }
    }
    d[i * 4] = pal[best][0]; d[i * 4 + 1] = pal[best][1]; d[i * 4 + 2] = pal[best][2];
  }
  return img;
}
export function pixeliser(img, cible_w) {
  const w = Math.round(cible_w);
  if (!(w >= 1)) throw new Error("pixeliser : largeur cible ≥ 1 requise");
  const h = Math.max(1, Math.round(img.h * w / img.w)), out = _tampon(w, h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const sx = Math.min(img.w - 1, Math.floor(x * img.w / w)), sy = Math.min(img.h - 1, Math.floor(y * img.h / h));   // coin haut-gauche du bloc (plus proche voisin)
    for (let c = 0; c < 4; c++) out.data[(y * w + x) * 4 + c] = img.data[(sy * img.w + sx) * 4 + c];
  }
  return out;
}
export function raccord_3x3(img) {
  const { w, h } = img, out = _tampon(w * 3, h * 3);
  for (let ty = 0; ty < 3; ty++) for (let tx = 0; tx < 3; tx++) for (let y = 0; y < h; y++) {
    out.data.set(img.data.subarray(y * w * 4, (y + 1) * w * 4), ((ty * h + y) * w * 3 + tx * w) * 4);
  }
  // métrique du Tilelab : écart moyen (RGB) entre la colonne gauche et la droite, la rangée haute et la basse
  let s = 0, n = 0;
  for (let y = 0; y < h; y++) for (let c = 0; c < 3; c++) { s += Math.abs(img.data[(y * w) * 4 + c] - img.data[(y * w + w - 1) * 4 + c]); n++; }
  for (let x = 0; x < w; x++) for (let c = 0; c < 3; c++) { s += Math.abs(img.data[x * 4 + c] - img.data[((h - 1) * w + x) * 4 + c]); n++; }
  const score = n ? 1 - (s / n) / 255 : 1;
  return { img: out, score: Math.round(score * 1000) / 1000 };
}

/* ── feuille de tuiles, bande, pelure ── */
function _copier(dst, src, ox, oy) {
  for (let y = 0; y < src.h; y++) dst.data.set(src.data.subarray(y * src.w * 4, (y + 1) * src.w * 4), ((oy + y) * dst.w + ox) * 4);
}
export function feuille_tuiles(tuiles, colonnes = 8) {
  if (!tuiles || !tuiles.length) throw new Error("feuille : aucune tuile");
  const { w, h } = tuiles[0].img;
  if (tuiles.some((t) => t.img.w !== w || t.img.h !== h)) throw new Error("feuille : toutes les tuiles doivent avoir la même taille");
  const cols = Math.max(1, Math.min(tuiles.length, colonnes | 0)), lignes = Math.ceil(tuiles.length / cols);
  const img = _tampon(w * cols, h * lignes), index = [];
  tuiles.forEach((t, i) => {
    const x = (i % cols) * w, y = Math.floor(i / cols) * h;
    _copier(img, t.img, x, y);
    index.push({ nom: t.nom || `tuile_${i}`, x, y, w, h });
  });
  return { img, index };
}
export function bande(imgs) {
  if (!imgs || !imgs.length) throw new Error("bande : aucun cadre");
  const h = Math.max(...imgs.map((i) => i.h)), w = imgs.reduce((s, i) => s + i.w, 0), out = _tampon(w, h);
  let x = 0;
  for (const im of imgs) { _copier(out, im, x, 0); x += im.w; }
  return out;
}
export function pelure(courant, precedent, alpha = 0.5) {
  const out = { w: courant.w, h: courant.h, data: new Uint8ClampedArray(courant.data) };
  if (!precedent) return out;
  for (let y = 0; y < Math.min(courant.h, precedent.h); y++) for (let x = 0; x < Math.min(courant.w, precedent.w); x++) {
    const i = (y * courant.w + x) * 4, j = (y * precedent.w + x) * 4;
    if (out.data[i + 3] !== 0 || precedent.data[j + 3] === 0) continue;
    out.data[i] = precedent.data[j]; out.data[i + 1] = precedent.data[j + 1]; out.data[i + 2] = precedent.data[j + 2];
    out.data[i + 3] = Math.round(precedent.data[j + 3] * alpha);
  }
  return out;
}
