// feuille_tuiles.js — lot 4 « Tilelab 2 » (19/09/2026) : une planche de
// tuiles existante. PUR : tampons {w, h, data} RGBA, aucun DOM. Détection
// des tuiles par composantes connexes (4-connexes) de l'alpha, fusion des
// bbox qui se chevauchent, taille commune (médiane), feuille alignée
// (chaque tuile centrée dans une cellule uniforme), grille de placement
// carrée ou iso 2:1, index des placements. Banc : qa/feuille_tuiles.test.mjs.
const _tampon = (w, h) => ({ w, h, data: new Uint8ClampedArray(w * h * 4) });
const _chevauche = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

export function tuiles_detecter(img, { min = 2 } = {}) {
  if (!img || !(img.w > 0) || !(img.h > 0)) throw new Error("feuille : image vide");
  const { w, h, data } = img, vu = new Uint8Array(w * h);
  let boites = [];
  const pile = [];
  for (let s = 0; s < w * h; s++) {
    if (vu[s] || !data[s * 4 + 3]) continue;
    let x0 = w, y0 = h, x1 = -1, y1 = -1;
    pile.push(s); vu[s] = 1;
    while (pile.length) {
      const i = pile.pop(), x = i % w, y = (i / w) | 0;
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
        const j = ny * w + nx; if (vu[j] || !data[j * 4 + 3]) continue;
        vu[j] = 1; pile.push(j);
      }
    }
    boites.push({ x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 });
  }
  // deux composantes dont les bbox se chevauchent = une seule tuile (un sprite en morceaux)
  let fusion = true;
  while (fusion) {
    fusion = false;
    for (let i = 0; i < boites.length && !fusion; i++) for (let j = i + 1; j < boites.length; j++) {
      if (_chevauche(boites[i], boites[j])) {
        const a = boites[i], b = boites[j], x0 = Math.min(a.x, b.x), y0 = Math.min(a.y, b.y);
        boites[i] = { x: x0, y: y0, w: Math.max(a.x + a.w, b.x + b.w) - x0, h: Math.max(a.y + a.h, b.y + b.h) - y0 };
        boites.splice(j, 1); fusion = true; break;
      }
    }
  }
  boites = boites.filter((b) => b.w >= min && b.h >= min);
  boites.sort((a, b) => a.y - b.y || a.x - b.x);
  return boites.map((b, i) => ({ nom: `tuile_${i}`, ...b }));
}

// lot 5 : réordonnancement manuel — la tuile i glisse de delta (±1), les noms suivent l'ordre
export function tuiles_deplacer(tuiles, i, delta) {
  const out = (tuiles || []).map((t) => ({ ...t })), j = i + delta;
  if (i < 0 || i >= out.length || j < 0 || j >= out.length) return out;
  [out[i], out[j]] = [out[j], out[i]];
  return out.map((t, k) => ({ ...t, nom: `tuile_${k}` }));
}
const _mediane = (v) => { const s = v.slice().sort((a, b) => a - b); return s.length ? s[(s.length - 1) >> 1] : 0; };
export function taille_commune(tuiles) {
  if (!tuiles || !tuiles.length) return { w: 0, h: 0 };
  return { w: _mediane(tuiles.map((t) => t.w)), h: _mediane(tuiles.map((t) => t.h)) };
}

function _copier(dst, src, sx, sy, sw, sh, dx, dy) {
  for (let y = 0; y < sh; y++) for (let x = 0; x < sw; x++) {
    const tx = dx + x, ty = dy + y, ox = sx + x, oy = sy + y;
    if (tx < 0 || ty < 0 || tx >= dst.w || ty >= dst.h || ox < 0 || oy < 0 || ox >= src.w || oy >= src.h) continue;
    const k = (oy * src.w + ox) * 4; if (!src.data[k + 3]) continue;
    const j = (ty * dst.w + tx) * 4;
    dst.data[j] = src.data[k]; dst.data[j + 1] = src.data[k + 1]; dst.data[j + 2] = src.data[k + 2]; dst.data[j + 3] = src.data[k + 3];
  }
}

// chaque tuile CENTRÉE dans une cellule uniforme (cell + pad), `cols` colonnes
export function feuille_alignee(img, tuiles, { cell_w, cell_h, cols = 8, pad = 0 } = {}) {
  if (!tuiles || !tuiles.length) throw new Error("feuille : aucune tuile");
  const cw = Math.max(1, (cell_w | 0) + 2 * pad), ch = Math.max(1, (cell_h | 0) + 2 * pad);
  const nc = Math.max(1, Math.min(tuiles.length, cols | 0)), nr = Math.ceil(tuiles.length / nc);
  const out = _tampon(cw * nc, ch * nr), index = [];
  tuiles.forEach((t, i) => {
    const x = (i % nc) * cw, y = Math.floor(i / nc) * ch;
    _copier(out, img, t.x, t.y, t.w, t.h, x + Math.floor((cw - t.w) / 2), y + Math.floor((ch - t.h) / 2));
    index.push({ nom: t.nom || `tuile_${i}`, x, y, w: cw, h: ch, source: { x: t.x, y: t.y, w: t.w, h: t.h } });
  });
  return { img: out, index };
}

/* ── grille de placement : carrée (x = c·w, y = r·h) ou iso 2:1
   (x = (c − r)·w/2 + (rows − 1)·w/2, y = (c + r)·h/2) ── */
export function position_cellule(c, r, g) {
  if (g.type === "iso") return { x: Math.round((c - r) * g.cell_w / 2 + (g.rows - 1) * g.cell_w / 2), y: Math.round((c + r) * g.cell_h / 2) };
  return { x: c * g.cell_w, y: r * g.cell_h };
}
export function cellule_de_point(x, y, g) {
  if (g.type === "iso") {
    const xp = x - (g.rows - 1) * g.cell_w / 2, u = xp / (g.cell_w / 2), v = y / (g.cell_h / 2);
    return { c: Math.floor((u + v) / 2), r: Math.floor((v - u) / 2) };
  }
  return { c: Math.floor(x / g.cell_w), r: Math.floor(y / g.cell_h) };
}
export function taille_placement(g, tuile_h = 0) {
  if (g.type === "iso") return { w: Math.round((g.cols + g.rows) * g.cell_w / 2), h: Math.round((g.cols + g.rows) * g.cell_h / 2) + Math.max(0, tuile_h - g.cell_h) };
  return { w: g.cols * g.cell_w, h: g.rows * g.cell_h };
}
export function placement_index(placements, g) {
  return (placements || []).map((p) => ({ c: p.c, r: p.r, tuile: p.tuile, ...position_cellule(p.c, p.r, g) }));
}
// les placements se dessinent dans l'ordre r puis c (l'iso se recouvre de haut en bas)
export function placement_rendre(img, tuiles, placements, g) {
  const th = Math.max(0, ...(tuiles || []).map((t) => t.h));
  const { w, h } = taille_placement(g, th), out = _tampon(w, h);
  const tri = (placements || []).slice().sort((a, b) => (a.r + a.c) - (b.r + b.c) || a.r - b.r);
  for (const p of tri) {
    const t = tuiles[p.tuile]; if (!t) continue;
    const { x, y } = position_cellule(p.c, p.r, g);
    _copier(out, img, t.x, t.y, t.w, t.h, x, y);
  }
  return out;
}
