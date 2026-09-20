// mod-crayon.js — le CRAYON à main levée du lot B : les points du geste se
// simplifient (Ramer–Douglas–Peucker), se lissent (Catmull-Rom → Bézier
// cubiques passant PAR les points) et se ferment d'eux-mêmes quand la fin
// rejoint le début. Module FEUILLE : aucun import, aucun DOM ; le d sort
// canonique (2 décimales).
const nbc = (x) => String(Math.round(Number((x * 100).toPrecision(12))) / 100);

function _distSeg(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1], l2 = dx * dx + dy * dy;
  const t = l2 ? Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2)) : 0;
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
}
export function simplifier(points, tol) {
  const pts = points.map((p) => [+p[0], +p[1]]);
  if (pts.length <= 2 || !(tol > 0)) return pts;
  const garder = new Array(pts.length).fill(false);
  garder[0] = garder[pts.length - 1] = true;
  const pile = [[0, pts.length - 1]];
  while (pile.length) {
    const [i0, i1] = pile.pop();
    let iMax = -1, dMax = tol;
    for (let i = i0 + 1; i < i1; i++) {
      const d = _distSeg(pts[i], pts[i0], pts[i1]);
      if (d > dMax) { dMax = d; iMax = i; }
    }
    if (iMax >= 0) { garder[iMax] = true; pile.push([i0, iMax], [iMax, i1]); }
  }
  return pts.filter((_, i) => garder[i]);
}

export function est_ferme(points, seuil) {
  if (!points || points.length < 3) return false;
  const a = points[0], b = points[points.length - 1];
  return Math.hypot(a[0] - b[0], a[1] - b[1]) <= seuil;
}

export function lisser_vers_d(points, { tol = 1, fermer = false, tension = 1 } = {}) {
  let pts = simplifier(points || [], tol);
  if (pts.length < 2) throw new Error("crayon : au moins deux points");
  const seuilFerme = Math.max(4, 4 * tol);
  const clos = fermer && est_ferme(pts, seuilFerme);
  if (clos) pts = pts.slice(0, -1);              // la fin rejoint le début : absorbée
  if (pts.length === 2 && !clos) return `M ${nbc(pts[0][0])} ${nbc(pts[0][1])} L ${nbc(pts[1][0])} ${nbc(pts[1][1])}`;
  const n = pts.length;
  const P = (i) => clos ? pts[((i % n) + n) % n] : pts[Math.max(0, Math.min(n - 1, i))];
  const k = tension / 6;
  let d = `M ${nbc(pts[0][0])} ${nbc(pts[0][1])}`;
  const nSeg = clos ? n : n - 1;
  for (let i = 0; i < nSeg; i++) {
    const p0 = P(i - 1), p1 = P(i), p2 = P(i + 1), p3 = P(i + 2);
    const c1 = [p1[0] + (p2[0] - p0[0]) * k, p1[1] + (p2[1] - p0[1]) * k];
    const c2 = [p2[0] - (p3[0] - p1[0]) * k, p2[1] - (p3[1] - p1[1]) * k];
    d += ` C ${nbc(c1[0])} ${nbc(c1[1])} ${nbc(c2[0])} ${nbc(c2[1])} ${nbc(p2[0])} ${nbc(p2[1])}`;
  }
  return clos ? d + " Z" : d;
}
