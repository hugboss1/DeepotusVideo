// mod-relief.js — le plateau en relief du lot H : une grille de hauteurs
// (rangée 0 = nord) devient une PLAQUE fermée — surface, socle plat à z=0,
// quatre murs — en mm, avec exagération verticale ; gravure d'un tracé
// (abaisse les cellules à portée) ; découpe en DALLES numérotées qui
// partagent leur rang de bord (juxtaposition, pas de tenons — écart dit).
// Module FEUILLE : aucun import, aucun DOM ; les volumes se mesurent.

function _orienter(a, b, c, dir) {
  // rend le triangle dont la normale pointe dans le sens de `dir`
  const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
  const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
  const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
  return (nx * dir[0] + ny * dir[1] + nz * dir[2]) >= 0 ? [a, b, c] : [a, c, b];
}
function _quad(out, p0, p1, p2, p3, dir) {
  out.push(_orienter(p0, p1, p2, dir), _orienter(p0, p2, p3, dir));
}

export function plaque(grid, w, h, { largeur_mm, socle_mm, mm_par_m, exageration = 1, z_min = 0 }) {
  if (!(w >= 2 && h >= 2) || grid.length < w * h) throw new Error("relief : grille d'au moins 2 × 2 requise");
  if (!(socle_mm > 0)) throw new Error("relief : socle > 0 mm requis");
  if (!(largeur_mm > 0) || !(mm_par_m > 0)) throw new Error("relief : largeur et mm/m > 0 requis");
  const cell = largeur_mm / (w - 1);
  const X = (i) => i * cell, Y = (j) => (h - 1 - j) * cell;          // nord en haut → y grand
  const Z = (i, j) => socle_mm + Math.max(0, grid[j * w + i] - z_min) * mm_par_m * exageration;
  const P = (i, j) => [X(i), Y(j), Z(i, j)], P0 = (i, j) => [X(i), Y(j), 0];
  const out = [];
  for (let j = 0; j + 1 < h; j++) for (let i = 0; i + 1 < w; i++) {
    _quad(out, P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1), [0, 0, 1]);
    _quad(out, P0(i, j), P0(i + 1, j), P0(i + 1, j + 1), P0(i, j + 1), [0, 0, -1]);
  }
  for (let i = 0; i + 1 < w; i++) {
    _quad(out, P0(i, 0), P0(i + 1, 0), P(i + 1, 0), P(i, 0), [0, 1, 0]);                 // nord
    _quad(out, P0(i, h - 1), P0(i + 1, h - 1), P(i + 1, h - 1), P(i, h - 1), [0, -1, 0]); // sud
  }
  for (let j = 0; j + 1 < h; j++) {
    _quad(out, P0(0, j), P0(0, j + 1), P(0, j + 1), P(0, j), [-1, 0, 0]);                 // ouest
    _quad(out, P0(w - 1, j), P0(w - 1, j + 1), P(w - 1, j + 1), P(w - 1, j), [1, 0, 0]);  // est
  }
  return out;
}

function _distSeg(px, py, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const l2 = dx * dx + dy * dy;
  const t = l2 ? Math.max(0, Math.min(1, ((px - a[0]) * dx + (py - a[1]) * dy) / l2)) : 0;
  return Math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy));
}
export function graver(grid, w, h, polylignes, profondeur, rayon) {
  const out = grid.slice();
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
    let proche = false;
    for (const l of polylignes) {
      for (let k = 0; k + 1 < l.length && !proche; k++) if (_distSeg(i, j, l[k], l[k + 1]) <= rayon) proche = true;
      if (l.length === 1 && Math.hypot(i - l[0][0], j - l[0][1]) <= rayon) proche = true;
      if (proche) break;
    }
    if (proche) out[j * w + i] -= profondeur;
  }
  return out;
}

export function dalles(w, h, maxCellules) {
  const m = Math.max(1, Math.floor(maxCellules));
  const cx = w - 1, cy = h - 1;
  const nx = Math.max(1, Math.ceil(cx / m)), ny = Math.max(1, Math.ceil(cy / m));
  const out = [];
  for (let r = 0; r < ny; r++) for (let c = 0; c < nx; c++) {
    const x0 = c * m, y0 = r * m;
    out.push({ nom: `dalle_${r + 1}_${c + 1}`, x0, y0,
               w: Math.min(m, cx - x0) + 1, h: Math.min(m, cy - y0) + 1 });
  }
  return out;
}
export function sous_grille(grid, w, h, d) {
  const g = [];
  for (let j = d.y0; j < d.y0 + d.h; j++) for (let i = d.x0; i < d.x0 + d.w; i++) g.push(grid[j * w + i]);
  return { grid: g, w: d.w, h: d.h };
}
