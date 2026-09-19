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
/* ── lot 2 : tramage (True Pixel : None · Ordered · Floyd-S) et rastérisation
   d'une image générée — l'entrée n'est jamais mutée ── */
const _BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
const _plusProche = (pal, r, g, b) => { let best = pal[0], d0 = Infinity; for (const c of pal) { const d = (c[0] - r) ** 2 + (c[1] - g) ** 2 + (c[2] - b) ** 2; if (d < d0) { d0 = d; best = c; } } return best; };
export function dither_ordonne(img, palette, force = 32) {
  if (!palette || !palette.length) throw new Error("tramage : palette vide");
  const pal = palette.map(_rgb), out = { w: img.w, h: img.h, data: new Uint8ClampedArray(img.data) };
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
  if (!palette || !palette.length) throw new Error("tramage : palette vide");
  const pal = palette.map(_rgb), out = { w: img.w, h: img.h, data: new Uint8ClampedArray(img.data) };
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
/* ── lot 2 : pelure double (Sprite Editor : rouge = précédent, bleu = suivant),
   là où le courant est transparent ── */
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
/* ── lot 2 : tuile iso 2:1 — le losange inscrit, le pavage aux décalages
   (±w/2, ±h/2), le score de raccord = 1 − écart RGB moyen entre pixels
   adjacents de la tuile centrale et de ses voisines ── */
export function masque_losange(w, h) {
  const m = new Uint8Array(w * h), cx = w / 2, cy = h / 2;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    // + 0,5 / cy : le gabarit iso classique (32 × 16 → rangées de 4, 8, … 32 pixels)
    if (Math.abs((x + 0.5 - cx) / cx) + Math.abs((y + 0.5 - cy) / cy) <= 1 + 0.5 / cy) m[y * w + x] = 255;
  }
  return m;
}
// le losange PAR TUILE, pavé sur toute l'image (la peinture iso est bornée
// à la tuile sous le curseur) ; sans tuile → le losange de l'image entière
export function masque_losanges(w, h, tw, th) {
  if (!(tw >= 1) || !(th >= 1)) return masque_losange(w, h);
  const u = masque_losange(tw, th), m = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) m[y * w + x] = u[(y % th) * tw + (x % tw)];
  return m;
}
/* ── lot 3 : le calque modèle — cellule ↔ cible, pipette SUR LE MODÈLE (exacte,
   moyenne, dominante), remplissage depuis le modèle, couleurs utilisées ── */
export function cellule_et_cible(nat, { cellule, cible } = {}) {
  const w = Math.max(1, nat.w | 0), h = Math.max(1, nat.h | 0);
  const c = cellule !== undefined ? Math.max(1, Math.round(+cellule) || 1) : Math.max(1, Math.round(w / Math.max(1, Math.round(+cible) || 1)));
  return { cellule: c, cible_w: Math.max(1, Math.ceil(w / c)), cible_h: Math.max(1, Math.ceil(h / c)) };
}
export const MODES_PIPETTE = ["exact", "moyenne", "dominante"];
const _hexDe = (r, g, b) => "#" + [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0").toUpperCase()).join("");
const _classe = (d, k) => ((d[k] >> 2) << 12) | ((d[k + 1] >> 2) << 6) | (d[k + 2] >> 2);   // 64 niveaux par canal
export function echantillon_cellule(img, rect, mode = "moyenne") {
  if (!MODES_PIPETTE.includes(mode)) throw new Error("pipette : mode exact, moyenne ou dominante");
  const x0 = Math.max(0, rect.x | 0), y0 = Math.max(0, rect.y | 0);
  const x1 = Math.min(img.w, x0 + Math.max(1, rect.w | 0)), y1 = Math.min(img.h, y0 + Math.max(1, rect.h | 0));
  if (x0 >= x1 || y0 >= y1) return null;
  const d = img.data;
  if (mode === "exact") {
    const cx = Math.min(x1 - 1, x0 + ((x1 - x0) >> 1)), cy = Math.min(y1 - 1, y0 + ((y1 - y0) >> 1)), k = (cy * img.w + cx) * 4;
    return d[k + 3] ? _hexDe(d[k], d[k + 1], d[k + 2]) : null;
  }
  let sr = 0, sg = 0, sb = 0, n = 0; const votes = new Map();
  for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
    const k = (y * img.w + x) * 4; if (!d[k + 3]) continue;
    n++; sr += d[k]; sg += d[k + 1]; sb += d[k + 2];
    const q = _classe(d, k); votes.set(q, (votes.get(q) || 0) + 1);
  }
  if (!n) return null;
  if (mode === "moyenne") return _hexDe(sr / n, sg / n, sb / n);
  let best = -1, bn = 0; for (const [q, c] of votes) if (c > bn) { bn = c; best = q; }
  // la dominante rend la MOYENNE des pixels de la classe gagnante, pas le centre de classe
  let r = 0, g = 0, b = 0, m = 0;
  for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { const k = (y * img.w + x) * 4; if (d[k + 3] && _classe(d, k) === best) { r += d[k]; g += d[k + 1]; b += d[k + 2]; m++; } }
  return _hexDe(r / m, g / m, b / m);
}
export function remplir_depuis_modele(modele, cible_w, cible_h, cellule, mode = "moyenne", palette = null) {
  const out = _tampon(cible_w, cible_h);
  for (let y = 0; y < cible_h; y++) for (let x = 0; x < cible_w; x++) {
    const hex = echantillon_cellule(modele, { x: x * cellule, y: y * cellule, w: cellule, h: cellule }, mode);
    if (!hex) continue;
    const [r, g, b] = _rgb(hex), k = (y * cible_w + x) * 4;
    out.data[k] = r; out.data[k + 1] = g; out.data[k + 2] = b; out.data[k + 3] = 255;
  }
  return palette && palette.length ? quantifier(out, palette) : out;
}
export function couleurs_utilisees(img, max = 64) {
  const votes = new Map(), d = img.data;
  for (let k = 0; k < img.w * img.h; k++) { if (!d[k * 4 + 3]) continue; const h = _hexDe(d[k * 4], d[k * 4 + 1], d[k * 4 + 2]); votes.set(h, (votes.get(h) || 0) + 1); }
  return [...votes.entries()].sort((a, b) => b[1] - a[1]).slice(0, Math.max(1, max | 0)).map(([h]) => h);
}
/* ── lot 5 : retouche True Pixel — contour sombre (dilatation 4-connexe de
   l'alpha), accentuer (masque flou 3 × 3, alpha conservé), agrandir (plus
   proche voisin ×k) — l'entrée n'est jamais mutée ── */
export function contour_sombre(img, couleur = "#101010", epaisseur = 1) {
  const [r, g, b] = _rgb(couleur), out = { w: img.w, h: img.h, data: new Uint8ClampedArray(img.data) };
  for (let e = 0; e < Math.max(1, epaisseur | 0); e++) {
    const opaque = new Uint8Array(img.w * img.h);
    for (let k = 0; k < img.w * img.h; k++) opaque[k] = out.data[k * 4 + 3] ? 1 : 0;
    for (let y = 0; y < img.h; y++) for (let x = 0; x < img.w; x++) {
      const k = y * img.w + x; if (opaque[k]) continue;
      const voisin = (x > 0 && opaque[k - 1]) || (x + 1 < img.w && opaque[k + 1]) || (y > 0 && opaque[k - img.w]) || (y + 1 < img.h && opaque[k + img.w]);
      if (voisin) { out.data[k * 4] = r; out.data[k * 4 + 1] = g; out.data[k * 4 + 2] = b; out.data[k * 4 + 3] = 255; }
    }
  }
  return out;
}
export function accentuer(img, force = 1) {
  const out = { w: img.w, h: img.h, data: new Uint8ClampedArray(img.data) }, f = +force || 0;
  if (f === 0) return out;
  const px = (x, y, c) => img.data[(Math.min(img.h - 1, Math.max(0, y)) * img.w + Math.min(img.w - 1, Math.max(0, x))) * 4 + c];
  for (let y = 0; y < img.h; y++) for (let x = 0; x < img.w; x++) {
    const k = (y * img.w + x) * 4; if (!img.data[k + 3]) continue;
    for (let c = 0; c < 3; c++) {
      let s = 0; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) s += px(x + dx, y + dy, c);
      out.data[k + c] = Math.max(0, Math.min(255, Math.round(img.data[k + c] + f * (img.data[k + c] - s / 9))));
    }
  }
  return out;
}
export function agrandir(img, k) {
  const n = Math.round(+k); if (!(n >= 1)) throw new Error("agrandir : facteur ≥ 1");
  const out = _tampon(img.w * n, img.h * n);
  for (let y = 0; y < out.h; y++) for (let x = 0; x < out.w; x++) {
    const i = ((y / n | 0) * img.w + (x / n | 0)) * 4, j = (y * out.w + x) * 4;
    out.data[j] = img.data[i]; out.data[j + 1] = img.data[i + 1]; out.data[j + 2] = img.data[i + 2]; out.data[j + 3] = img.data[i + 3];
  }
  return out;
}
export function pavage_iso(img) {
  const { w, h } = img, m = masque_losange(w, h), W = w * 3, H = h * 3, out = _tampon(W, H), qui = new Int8Array(W * H).fill(-1);
  const pos = [[w, h, 0], [w / 2, h / 2, 1], [3 * w / 2, h / 2, 2], [w / 2, 3 * h / 2, 3], [3 * w / 2, 3 * h / 2, 4], [0, h, 5], [2 * w, h, 6], [w, 0, 7], [w, 2 * h, 8]];
  for (const [ox, oy, id] of pos) for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (!m[y * w + x]) continue;
    const tx = Math.round(ox) + x, ty = Math.round(oy) + y;
    if (tx < 0 || ty < 0 || tx >= W || ty >= H) continue;
    const k = (ty * W + tx) * 4, j = (y * w + x) * 4;
    out.data[k] = img.data[j]; out.data[k + 1] = img.data[j + 1]; out.data[k + 2] = img.data[j + 2]; out.data[k + 3] = img.data[j + 3];
    qui[ty * W + tx] = id;
  }
  let s = 0, n = 0;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x; if (qui[i] !== 0) continue;
    for (const [dx, dy] of [[1, 0], [0, 1], [-1, 0], [0, -1]]) {
      const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
      const j = ny * W + nx; if (qui[j] <= 0) continue;
      for (let c = 0; c < 3; c++) s += Math.abs(out.data[i * 4 + c] - out.data[j * 4 + c]); n++;
    }
  }
  return { img: out, score: n ? Math.round((1 - (s / n) / 255) * 1000) / 1000 : 1 };
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
