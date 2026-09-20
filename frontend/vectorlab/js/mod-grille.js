// mod-grille.js — la GÉOMÉTRIE des grilles du Vectorlab (lot C) : quatre
// réseaux (carrée subdivisée, isométrique, triangulaire, hexagonale pointe
// ou plat), origine et échelle par axe, tracé borné à la page, aimantation
// au réseau, mathématiques hexagonales axiales (D3). Module FEUILLE : aucun
// import, aucun DOM — le banc node l'exerce tel quel.
export const GRILLE_TYPES = ["carree", "iso", "tri", "hex"];
const S3 = Math.sqrt(3);
const nbc = (x) => String(Math.round(Number((x * 100).toPrecision(12))) / 100);
const GRILLE_MAX_CELLULES = 20000;

export function grille_normaliser(g) {
  if (!g || typeof g !== "object") throw new Error("grille: objet requis");
  if (!GRILLE_TYPES.includes(g.type)) {
    throw new Error(`grille: type ${g.type} inconnu (${GRILLE_TYPES.join("|")})`);
  }
  if (!(+g.pas > 0)) throw new Error("grille: pas > 0 requis");
  const sous = g.sous === undefined ? 1 : +g.sous;
  if (!(Number.isInteger(sous) && sous >= 1)) throw new Error("grille: sous = entier ≥ 1");
  const orientation = g.orientation === undefined ? "pointe" : g.orientation;
  if (!["pointe", "plat"].includes(orientation)) throw new Error("grille: orientation pointe|plat");
  const origine = g.origine === undefined ? [0, 0] : g.origine;
  if (!Array.isArray(origine) || origine.length !== 2 || !origine.every(Number.isFinite)) {
    throw new Error("grille: origine [x, y]");
  }
  const echelle = g.echelle === undefined ? [1, 1] : g.echelle;
  if (!Array.isArray(echelle) || echelle.length !== 2 || !echelle.every((v) => v > 0)) {
    throw new Error("grille: echelle [sx > 0, sy > 0]");
  }
  return { type: g.type, pas: +g.pas, sous, orientation,
           origine: [+origine[0], +origine[1]], echelle: [+echelle[0], +echelle[1]] };
}

/* ── hexagones (axial q, r) ── */
export function hex_centre(q, r, g) {
  const s = g.pas;
  const [x, y] = g.orientation === "plat"
    ? [s * 1.5 * q, s * S3 * (r + q / 2)]
    : [s * S3 * (q + r / 2), s * 1.5 * r];
  return [g.origine[0] + x * g.echelle[0], g.origine[1] + y * g.echelle[1]];
}
export function hex_sommets(cx, cy, s, orientation, echelle = [1, 1]) {
  const dep = orientation === "plat" ? 0 : -90;
  const out = [];
  for (let k = 0; k < 6; k++) {
    const a = (dep + 60 * k) * Math.PI / 180;
    out.push([cx + s * Math.cos(a) * echelle[0], cy + s * Math.sin(a) * echelle[1]]);
  }
  return out;
}
export function hex_d(cx, cy, s, orientation, echelle = [1, 1]) {
  const p = hex_sommets(cx, cy, s, orientation, echelle);
  return "M " + p.map(([x, y]) => `${nbc(x)} ${nbc(y)}`).join(" L ") + " Z";
}
function _arrondiCube(qf, rf) {
  const sf = -qf - rf;
  let q = Math.round(qf), r = Math.round(rf);
  const s = Math.round(sf);
  const dq = Math.abs(q - qf), dr = Math.abs(r - rf), ds = Math.abs(s - sf);
  if (dq > dr && dq > ds) q = -r - s; else if (dr > ds) r = -q - s;
  return { q, r };
}
export function hex_depuis_point(x, y, g) {
  const s = g.pas;
  const lx = (x - g.origine[0]) / g.echelle[0], ly = (y - g.origine[1]) / g.echelle[1];
  const [qf, rf] = g.orientation === "plat"
    ? [lx * 2 / 3 / s, (-lx / 3 + S3 / 3 * ly) / s]
    : [(S3 / 3 * lx - ly / 3) / s, ly * 2 / 3 / s];
  return _arrondiCube(qf, rf);
}

/* ── les cellules d'un plateau : disque de rayon n ou rectangle ── */
export function grille_cellules(spec) {
  if (!spec || typeof spec !== "object") throw new Error("plateau: spécification requise");
  const out = [];
  if (spec.mode === "rayon") {
    const n = +spec.rayon;
    if (!(Number.isInteger(n) && n >= 0 && n <= 60)) throw new Error("plateau: rayon entier 0..60");
    for (let q = -n; q <= n; q++) {
      for (let r = Math.max(-n, -q - n); r <= Math.min(n, -q + n); r++) out.push({ q, r });
    }
    return out;
  }
  if (spec.mode === "rect") {
    const c = +spec.colonnes, l = +spec.lignes;
    if (!(Number.isInteger(c) && c >= 1 && c <= 120 && Number.isInteger(l) && l >= 1 && l <= 120)) {
      throw new Error("plateau: colonnes et lignes entières 1..120");
    }
    // décalage « odd-r » → axial : q = col − floor(row / 2)
    for (let row = 0; row < l; row++) {
      for (let col = 0; col < c; col++) out.push({ q: col - Math.floor(row / 2), r: row });
    }
    return out;
  }
  throw new Error(`plateau: mode ${spec.mode} inconnu (rayon|rect)`);
}

/* ── lignes bornées à la page ── */
function _clip(x0, y0, dx, dy, W, H) {
  // segment de la droite (x0,y0)+t·(dx,dy) dans [0,W]×[0,H] (Liang–Barsky)
  let t0 = -Infinity, t1 = Infinity;
  for (const [p, q] of [[-dx, x0], [dx, W - x0], [-dy, y0], [dy, H - y0]]) {
    if (p === 0) { if (q < 0) return null; continue; }
    const t = q / p;
    if (p < 0) t0 = Math.max(t0, t); else t1 = Math.min(t1, t);
  }
  if (t0 >= t1) return null;
  return [x0 + t0 * dx, y0 + t0 * dy, x0 + t1 * dx, y0 + t1 * dy];
}
function _famille(angleDeg, espacement, origine, W, H) {
  // toutes les droites de direction `angle`, espacées de `espacement`
  // perpendiculairement, passant par le réseau d'origine `origine`
  const a = angleDeg * Math.PI / 180;
  const dx = Math.cos(a), dy = Math.sin(a);
  const nx = -dy, ny = dx;                       // normale unitaire
  const d0 = origine[0] * nx + origine[1] * ny;  // offset de la droite d'origine
  const coins = [[0, 0], [W, 0], [0, H], [W, H]].map(([x, y]) => x * nx + y * ny);
  const kMin = Math.ceil((Math.min(...coins) - d0) / espacement);
  const kMax = Math.floor((Math.max(...coins) - d0) / espacement);
  let d = "";
  for (let k = kMin; k <= kMax; k++) {
    const off = d0 + k * espacement;
    const seg = _clip(off * nx, off * ny, dx, dy, W, H);
    if (seg) d += `M ${nbc(seg[0])} ${nbc(seg[1])} L ${nbc(seg[2])} ${nbc(seg[3])} `;
  }
  return d;
}
export function grille_d(g, taille) {
  const W = +taille.w, H = +taille.h;
  const [sx, sy] = g.echelle;
  if (g.type === "carree") {
    const px = g.pas * sx / g.sous, py = g.pas * sy / g.sous;
    if ((W / px) * (H / py) > GRILLE_MAX_CELLULES) return "";
    let d = "";
    const x0 = ((g.origine[0] % px) + px) % px, y0 = ((g.origine[1] % py) + py) % py;
    for (let x = x0; x < W; x += px) if (x > 0) d += `M ${nbc(x)} 0 L ${nbc(x)} ${nbc(H)} `;
    for (let y = y0; y < H; y += py) if (y > 0) d += `M 0 ${nbc(y)} L ${nbc(W)} ${nbc(y)} `;
    return d.trim();
  }
  if (g.type === "iso") {
    // réseau losange de base a=(√3/2·s, s/2), b=(√3/2·s, −s/2) : droites à
    // ±30°, espacement perpendiculaire = s·cos 30°
    const s = g.pas * sy, e = s * Math.cos(30 * Math.PI / 180);
    if ((W / (g.pas * sx)) * (H / s) * 2 > GRILLE_MAX_CELLULES) return "";
    return (_famille(30, e, g.origine, W, H) + _famille(-30, e, g.origine, W, H)).trim();
  }
  if (g.type === "tri") {
    const s = g.pas * sx, e = s * S3 / 2;         // hauteur du triangle équilatéral
    if ((W / s) * (H / e) * 2 > GRILLE_MAX_CELLULES) return "";
    return (_famille(0, e, g.origine, W, H) + _famille(60, e, g.origine, W, H)
            + _famille(120, e, g.origine, W, H)).trim();
  }
  // hex : un hexagone fermé par cellule visible
  const s = g.pas;
  const a0 = hex_depuis_point(0, 0, g), a1 = hex_depuis_point(W, 0, g),
        a2 = hex_depuis_point(0, H, g), a3 = hex_depuis_point(W, H, g);
  const qs = [a0.q, a1.q, a2.q, a3.q], rs = [a0.r, a1.r, a2.r, a3.r];
  const qMin = Math.min(...qs) - 2, qMax = Math.max(...qs) + 2;
  const rMin = Math.min(...rs) - 2, rMax = Math.max(...rs) + 2;
  if ((qMax - qMin + 1) * (rMax - rMin + 1) > GRILLE_MAX_CELLULES) return "";
  let d = "";
  for (let q = qMin; q <= qMax; q++) {
    for (let r = rMin; r <= rMax; r++) {
      const [cx, cy] = hex_centre(q, r, g);
      if (cx < -s * sx || cx > W + s * sx || cy < -s * sy || cy > H + s * sy) continue;
      d += hex_d(cx, cy, s, g.orientation, g.echelle) + " ";
    }
  }
  return d.trim();
}

/* ── aimantation au réseau : le sommet le plus proche ── */
function _reseau(x, y, a, b, origine) {
  // coordonnées fractionnaires dans la base (a, b), arrondies
  const det = a[0] * b[1] - a[1] * b[0];
  const lx = x - origine[0], ly = y - origine[1];
  const u = Math.round((lx * b[1] - ly * b[0]) / det);
  const v = Math.round((a[0] * ly - a[1] * lx) / det);
  return [origine[0] + u * a[0] + v * b[0], origine[1] + u * a[1] + v * b[1]];
}
export function grille_aimanter(g, x, y) {
  const [sx, sy] = g.echelle;
  if (g.type === "carree") {
    const p = g.pas / g.sous;
    return _reseau(x, y, [p * sx, 0], [0, p * sy], g.origine);
  }
  if (g.type === "iso") {
    const s = g.pas;
    return _reseau(x, y, [S3 / 2 * s * sx, s / 2 * sy], [S3 / 2 * s * sx, -s / 2 * sy], g.origine);
  }
  if (g.type === "tri") {
    const s = g.pas;
    return _reseau(x, y, [s * sx, 0], [s / 2 * sx, S3 / 2 * s * sy], g.origine);
  }
  const { q, r } = hex_depuis_point(x, y, g);
  const [cx, cy] = hex_centre(q, r, g);
  let meilleur = [cx, cy], dist = Math.hypot(x - cx, y - cy);
  for (const [px, py] of hex_sommets(cx, cy, g.pas, g.orientation, g.echelle)) {
    const dd = Math.hypot(x - px, y - py);
    if (dd < dist) { dist = dd; meilleur = [px, py]; }
  }
  return meilleur;
}
