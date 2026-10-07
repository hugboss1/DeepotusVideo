// mod-relief.js — le plateau en relief du lot H : une grille de hauteurs
// (rangée 0 = nord) devient une PLAQUE fermée — surface, socle plat à z=0,
// quatre murs — en mm, avec exagération verticale ; gravure d'un tracé
// (abaisse les cellules à portée) ; découpe en DALLES numérotées qui
// partagent leur rang de bord ; t124 : LOGEMENTS creusés sous le socle de
// part et d'autre d'une arête commune et CLÉS séparées qui les alignent.
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

// t124 : `logements` = rectangles de CELLULES (i0, j0, ni, nj — cellule (i, j) entre les sommets i..i+1,
// j..j+1) creusés depuis le dessous jusqu'à `prof_logement` mm. Le fond de ces cellules monte à cette
// hauteur ; un mur intérieur borde la poche ; les murs extérieurs se coupent au niveau de la poche pour
// que chaque arête garde son opposée (une poche au bord s'ouvre sur le côté : c'est la moitié d'un tenon).
export function plaque(grid, w, h, { largeur_mm, socle_mm, mm_par_m, exageration = 1, z_min = 0, logements = [], prof_logement = 0 }) {
  if (!(w >= 2 && h >= 2) || grid.length < w * h) throw new Error("relief : grille d'au moins 2 × 2 requise");
  if (!(socle_mm > 0)) throw new Error("relief : socle > 0 mm requis");
  if (!(largeur_mm > 0) || !(mm_par_m > 0)) throw new Error("relief : largeur et mm/m > 0 requis");
  const cell = largeur_mm / (w - 1);
  const X = (i) => i * cell, Y = (j) => (h - 1 - j) * cell;          // nord en haut → y grand
  const Z = (i, j) => socle_mm + Math.max(0, grid[j * w + i] - z_min) * mm_par_m * exageration;
  const P = (i, j) => [X(i), Y(j), Z(i, j)];
  const out = [];
  const L = logements || [];
  if (L.length && !(prof_logement > 0 && prof_logement < socle_mm)) throw new Error("relief : 0 < profondeur de logement < socle");
  const creux = (i, j) => L.some((r) => i >= r.i0 && i < r.i0 + r.ni && j >= r.j0 && j < r.j0 + r.nj);
  const F = (i, j) => (L.length && creux(i, j) ? prof_logement : 0);       // le fond de la cellule (i, j)
  const Pz = (i, j, z) => [X(i), Y(j), z];
  for (let j = 0; j + 1 < h; j++) for (let i = 0; i + 1 < w; i++) {
    const f = F(i, j);
    _quad(out, P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1), [0, 0, 1]);
    _quad(out, Pz(i, j, f), Pz(i + 1, j, f), Pz(i + 1, j + 1, f), Pz(i, j + 1, f), [0, 0, -1]);
  }
  // un pan de mur extérieur, de a à b (sommets), sous une cellule de fond f ; coupé au niveau des poches
  // dès qu'il y en a une
  const mur = (a, b, f, dir) => {
    if (!L.length) { _quad(out, Pz(...a, 0), Pz(...b, 0), P(...b), P(...a), dir); return; }
    if (f === 0) _quad(out, Pz(...a, 0), Pz(...b, 0), Pz(...b, prof_logement), Pz(...a, prof_logement), dir);
    _quad(out, Pz(...a, prof_logement), Pz(...b, prof_logement), P(...b), P(...a), dir);
  };
  for (let i = 0; i + 1 < w; i++) {
    mur([i, 0], [i + 1, 0], F(i, 0), [0, 1, 0]);                         // nord
    mur([i, h - 1], [i + 1, h - 1], F(i, h - 2), [0, -1, 0]);            // sud
  }
  for (let j = 0; j + 1 < h; j++) {
    mur([0, j], [0, j + 1], F(0, j), [-1, 0, 0]);                        // ouest
    mur([w - 1, j], [w - 1, j + 1], F(w - 2, j), [1, 0, 0]);             // est
  }
  // les murs intérieurs des poches : entre deux cellules de fonds différents, de 0 à la poche, face vers le vide
  if (L.length) {
    for (let j = 0; j + 1 < h; j++) for (let i = 0; i + 2 < w; i++) {
      const a = F(i, j), b = F(i + 1, j);
      if (a !== b) _quad(out, Pz(i + 1, j, 0), Pz(i + 1, j + 1, 0), Pz(i + 1, j + 1, prof_logement), Pz(i + 1, j, prof_logement), [b ? 1 : -1, 0, 0]);
    }
    for (let j = 0; j + 2 < h; j++) for (let i = 0; i + 1 < w; i++) {
      const a = F(i, j), b = F(i, j + 1);
      if (a !== b) _quad(out, Pz(i, j + 1, 0), Pz(i + 1, j + 1, 0), Pz(i + 1, j + 1, prof_logement), Pz(i, j + 1, prof_logement), [0, b ? -1 : 1, 0]);
    }
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

// t124 : le RUBAN — un mur fermé qui suit le tracé (x, y en mm) et monte à l'altitude ENREGISTRÉE du GPX
// (z en mm, sommet par sommet), base plate à z=0 pour s'imprimer debout. Épaisseur centrée sur le tracé,
// joints en onglet (bornés à 4 × la demi-épaisseur dans les virages serrés) : l'aire vaut longueur ×
// épaisseur. Les doublons consécutifs (GPS à l'arrêt) tombent.
export function ruban(pts, epaisseur) {
  if (!(epaisseur > 0)) throw new Error("ruban : épaisseur > 0 mm requise");
  const P = [];
  for (const p of pts || []) {
    const q = P[P.length - 1];
    if (!q || Math.hypot(p[0] - q[0], p[1] - q[1]) > 1e-9) P.push(p);
  }
  if (P.length < 2) throw new Error("ruban : deux points distincts au moins");
  if (P.some((p) => !(p[2] > 0))) throw new Error("ruban : hauteur > 0 mm à chaque point");
  const n = P.length, e = epaisseur / 2;
  const nrm = [];                        // normale gauche de chaque segment
  for (let k = 0; k + 1 < n; k++) {
    const dx = P[k + 1][0] - P[k][0], dy = P[k + 1][1] - P[k][1], l = Math.hypot(dx, dy);
    nrm.push([-dy / l, dx / l]);
  }
  const off = P.map((p, k) => {
    if (k === 0) return nrm[0].map((v) => v * e);
    if (k === n - 1) return nrm[n - 2].map((v) => v * e);
    const a = nrm[k - 1], b = nrm[k], sx = a[0] + b[0], sy = a[1] + b[1], ls = Math.hypot(sx, sy);
    if (ls < 1e-9) return a.map((v) => v * e);                       // demi-tour : pas d'onglet
    const mx = sx / ls, my = sy / ls, cos = mx * a[0] + my * a[1];
    const k2 = Math.min(4, 1 / Math.max(1e-9, cos)) * e;
    return [mx * k2, my * k2];
  });
  const G = (k, z) => [P[k][0] + off[k][0], P[k][1] + off[k][1], z], D = (k, z) => [P[k][0] - off[k][0], P[k][1] - off[k][1], z];
  const out = [];
  for (let k = 0; k + 1 < n; k++) {
    const z0 = P[k][2], z1 = P[k + 1][2], [nx, ny] = nrm[k];
    _quad(out, G(k, z0), G(k + 1, z1), D(k + 1, z1), D(k, z0), [0, 0, 1]);
    _quad(out, G(k, 0), G(k + 1, 0), D(k + 1, 0), D(k, 0), [0, 0, -1]);
    _quad(out, G(k, 0), G(k + 1, 0), G(k + 1, z1), G(k, z0), [nx, ny, 0]);
    _quad(out, D(k, 0), D(k + 1, 0), D(k + 1, z1), D(k, z0), [-nx, -ny, 0]);
  }
  const t0 = [nrm[0][1], -nrm[0][0]], t1 = [nrm[n - 2][1], -nrm[n - 2][0]];   // tangentes
  _quad(out, G(0, 0), D(0, 0), D(0, P[0][2]), G(0, P[0][2]), [-t0[0], -t0[1], 0]);
  _quad(out, G(n - 1, 0), D(n - 1, 0), D(n - 1, P[n - 1][2]), G(n - 1, P[n - 1][2]), [t1[0], t1[1], 0]);
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
// t124 : les tenons d'un découpage en dalles. Chaque arête commune reçoit une ou deux poches (au quart et
// aux trois quarts, une seule au milieu si l'arête est courte), moitié dans chaque dalle, alignées sur la
// grille : ka cellules de chaque côté (≈ demi_mm), kb le long (≈ long_mm). Profondeur = socle − 0,8 mm
// (le plafond de la poche garde 0,8 mm de matière) ; la clé = la poche entière moins `jeu` par face, et
// moins `jeu` en hauteur. Une dalle trop étroite (moins de ka + 1 cellules) ou un socle trop mince : rien,
// et la raison est dite.
export function tenons(parts, cell_mm, socle_mm, { jeu = 0.2, demi_mm = 4, long_mm = 8 } = {}) {
  const par_dalle = {}, cles = [];
  for (const d of parts) par_dalle[d.nom] = [];
  const prof = Math.round((socle_mm - 0.8) * 1000) / 1000;
  if (!(prof >= 0.8)) return { prof: 0, par_dalle, cles, raison: "tenons : socle trop mince (1,6 mm au moins)" };
  const ka = Math.max(1, Math.round(demi_mm / cell_mm)), kb = Math.max(1, Math.round(long_mm / cell_mm));
  let raison = "";
  const places = (len) => (len >= 4 * kb ? [0.25, 0.75] : len >= kb + 2 ? [0.5] : [])
    .map((f) => Math.max(0, Math.min(len - kb, Math.round(len * f - kb / 2))));
  for (const A of parts) for (const B of parts) {
    const est = B.x0 === A.x0 + A.w - 1 && B.y0 === A.y0, sud = B.y0 === A.y0 + A.h - 1 && B.x0 === A.x0;
    if (!est && !sud) continue;
    const ca = est ? A.w - 1 : A.h - 1, cb = est ? B.w - 1 : B.h - 1, len = est ? A.h - 1 : A.w - 1;
    if (ca < ka + 1 || cb < ka + 1) { raison = "tenons : dalle trop étroite pour un logement"; continue; }
    const pos = places(len);
    if (!pos.length) { raison = "tenons : arête trop courte pour un logement"; continue; }
    for (const p of pos) {
      if (est) {
        par_dalle[A.nom].push({ i0: ca - ka, j0: p, ni: ka, nj: kb });
        par_dalle[B.nom].push({ i0: 0, j0: p, ni: ka, nj: kb });
        cles.push({ lx: 2 * ka * cell_mm - 2 * jeu, ly: kb * cell_mm - 2 * jeu, h: prof - jeu });
      } else {
        par_dalle[A.nom].push({ i0: p, j0: ca - ka, ni: kb, nj: ka });
        par_dalle[B.nom].push({ i0: p, j0: 0, ni: kb, nj: ka });
        cles.push({ lx: kb * cell_mm - 2 * jeu, ly: 2 * ka * cell_mm - 2 * jeu, h: prof - jeu });
      }
    }
  }
  return { prof, par_dalle, cles, ...(cles.length || !raison ? {} : { raison }) };
}
// une clé : la boîte lx × ly × h posée en (ox, oy), base à z=0
export function cle(lx, ly, hz, ox = 0, oy = 0) {
  const p = (x, y, z) => [ox + x, oy + y, z], out = [];
  _quad(out, p(0, 0, hz), p(lx, 0, hz), p(lx, ly, hz), p(0, ly, hz), [0, 0, 1]);
  _quad(out, p(0, 0, 0), p(lx, 0, 0), p(lx, ly, 0), p(0, ly, 0), [0, 0, -1]);
  _quad(out, p(0, 0, 0), p(lx, 0, 0), p(lx, 0, hz), p(0, 0, hz), [0, -1, 0]);
  _quad(out, p(0, ly, 0), p(lx, ly, 0), p(lx, ly, hz), p(0, ly, hz), [0, 1, 0]);
  _quad(out, p(0, 0, 0), p(0, ly, 0), p(0, ly, hz), p(0, 0, hz), [-1, 0, 0]);
  _quad(out, p(lx, 0, 0), p(lx, ly, 0), p(lx, ly, hz), p(lx, 0, hz), [1, 0, 0]);
  return out;
}
export function sous_grille(grid, w, h, d) {
  const g = [];
  for (let j = d.y0; j < d.y0 + d.h; j++) for (let i = d.x0; i < d.x0 + d.w; i++) g.push(grid[j * w + i]);
  return { grid: g, w: d.w, h: d.h };
}
