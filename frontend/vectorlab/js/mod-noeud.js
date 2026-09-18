// mod-noeud.js — l'outil Nœud de classe Affinity (R9) : le segment le plus
// proche d'un point, la déformation d'un segment au glisser (poids de
// Bernstein), le déplacement d'une poignée (lisse : l'opposée s'aligne en
// gardant sa longueur ; libre : seule), la suppression lisse d'un nœud,
// le point d'un segment. Feuille pure ; mod-noeudui traduit.
import { chemin_ancres } from "./mod-doc.js";

const clone = (segs) => segs.map((s) => ({ c: s.c, p: s.p.slice() }));
const fin = (s) => [s.p[s.p.length - 2], s.p[s.p.length - 1]];
const porteurs = (segs) => segs.map((s, k) => s.c !== "Z" ? k : -1).filter((k) => k >= 0);
// le point de départ du segment k (la fin du porteur précédent)
function depart(segs, k) {
  for (let j = k - 1; j >= 0; j--) if (segs[j].c !== "Z") return fin(segs[j]);
  return null;
}
function evaluer(p0, s, t) {
  const u = 1 - t;
  if (s.c === "L") return [p0[0] + (s.p[0] - p0[0]) * t, p0[1] + (s.p[1] - p0[1]) * t];
  if (s.c === "C") { const [x1, y1, x2, y2, x3, y3] = s.p; return [u * u * u * p0[0] + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3, u * u * u * p0[1] + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3]; }
  if (s.c === "Q") { const [x1, y1, x2, y2] = s.p; return [u * u * p0[0] + 2 * u * t * x1 + t * t * x2, u * u * p0[1] + 2 * u * t * y1 + t * t * y2]; }
  return null;
}
// le Z est traité comme une droite de retour vers le M
function segmentVirtuel(segs, k) {
  const s = segs[k];
  if (!s) return null;
  if (s.c === "Z") { const m = segs.find((x) => x.c === "M"); return m ? { c: "L", p: fin(m) } : null; }
  return s;
}
export function point_segment(segs, k, t) {
  const s = segmentVirtuel(segs, k), p0 = depart(segs, k);
  if (!s || !p0 || s.c === "M") return null;
  return evaluer(p0, s, Math.max(0, Math.min(1, +t || 0)));
}
export function segment_proche(segs, pt, tol, pas = 24) {
  if (!Array.isArray(segs) || !segs.length) return null;
  const pk = porteurs(segs);
  let best = null;
  segs.forEach((s, k) => {
    if (s.c === "M") return;
    const sv = segmentVirtuel(segs, k), p0 = depart(segs, k);
    if (!sv || !p0) return;
    for (let j = 0; j <= pas; j++) {
      const t = j / pas, q = evaluer(p0, sv, t);
      const d = Math.hypot(q[0] - pt[0], q[1] - pt[1]);
      if (d <= tol && (!best || d < best.dist)) {
        const i = s.c === "Z" ? 0 : pk.indexOf(k);
        best = { k, i, t, dist: d, point: q };
      }
    }
  });
  return best;
}
export function segment_tirer(segs, k, t, dx, dy) {
  const out = clone(segs);
  const s = out[k];
  if (!s || s.c === "M" || s.c === "Z") return out;
  const p0 = depart(out, k);
  if (!p0) return out;
  const u = Math.max(0.05, Math.min(0.95, +t || 0.5));
  if (s.c === "L") { const f = s.p; out[k] = { c: "C", p: [p0[0] + (f[0] - p0[0]) / 3, p0[1] + (f[1] - p0[1]) / 3, p0[0] + 2 * (f[0] - p0[0]) / 3, p0[1] + 2 * (f[1] - p0[1]) / 3, f[0], f[1]] }; }
  else if (s.c === "Q") { const [x1, y1, x2, y2] = s.p; out[k] = { c: "C", p: [p0[0] + 2 * (x1 - p0[0]) / 3, p0[1] + 2 * (y1 - p0[1]) / 3, x2 + 2 * (x1 - x2) / 3, y2 + 2 * (y1 - y2) / 3, x2, y2] }; }
  const c = out[k];
  const w = 1 / (3 * u * (1 - u));   // même poids sur les deux contrôles : B(t) bouge exactement de (dx, dy)
  c.p[0] += dx * w; c.p[1] += dy * w; c.p[2] += dx * w; c.p[3] += dy * w;
  return out;
}
export function poignee_deplacer(segs, i, role, pt, { mode = "lisse" } = {}) {
  const out = clone(segs);
  const pk = porteurs(out);
  const k = pk[i];
  if (k === undefined) return out;
  const a = chemin_ancres(out)[i];
  const vive = (p) => p && (p.x !== a.x || p.y !== a.y);
  const s = out[k], kn = pk[i + 1], sn = kn === undefined ? null : out[kn];
  const poserEntrante = (x, y) => { if (s.c === "C") { s.p[2] = x; s.p[3] = y; } else if (s.c === "Q") { s.p[0] = x; s.p[1] = y; } };
  const poserSortante = (x, y) => { if (sn && sn.c === "C") { sn.p[0] = x; sn.p[1] = y; } };
  if (role === "sortante") {
    if (!vive(a.sortante)) return out;
    poserSortante(+pt[0], +pt[1]);
    if (mode === "lisse" && vive(a.entrante)) { const L = Math.hypot(a.entrante.x - a.x, a.entrante.y - a.y), d = Math.hypot(pt[0] - a.x, pt[1] - a.y) || 1; poserEntrante(a.x - (pt[0] - a.x) / d * L, a.y - (pt[1] - a.y) / d * L); }
  } else if (role === "entrante") {
    if (!vive(a.entrante)) return out;
    poserEntrante(+pt[0], +pt[1]);
    if (mode === "lisse" && vive(a.sortante)) { const L = Math.hypot(a.sortante.x - a.x, a.sortante.y - a.y), d = Math.hypot(pt[0] - a.x, pt[1] - a.y) || 1; poserSortante(a.x - (pt[0] - a.x) / d * L, a.y - (pt[1] - a.y) / d * L); }
  }
  return out;
}
export function noeud_supprimer_lisse(segs, i) {
  const out = clone(segs);
  const pk = porteurs(out);
  const n = pk.length;
  if (n <= 2 || i < 0 || i >= n) return out;
  const k = pk[i];
  if (i === 0) { const kn = pk[1]; const f = fin(out[kn]); out.splice(0, kn + 1, { c: "M", p: f }); return out; }
  if (i === n - 1) { out.splice(k, 1); return out; }
  const s = out[k], sn = out[pk[i + 1]];
  const p0 = depart(out, k), f = fin(sn);
  const c1 = s.c === "C" ? [s.p[0], s.p[1]] : p0, c2 = sn.c === "C" ? [sn.p[2], sn.p[3]] : f;
  const droit = s.c === "L" && sn.c === "L";
  out.splice(k, 2, droit ? { c: "L", p: f } : { c: "C", p: [c1[0], c1[1], c2[0], c2[1], f[0], f[1]] });
  return out;
}
