// mod-plume.js — la Plume de classe Affinity (R8) : l'état de tracé PUR
// {segs, ancres, sortante} et ses transitions, l'élastique courbe, la
// contrainte à 45°, le lissage Catmull-Rom (mode Intelligent), ouvrir /
// lisser / fractionner un chemin, la prolongation depuis une extrémité,
// les types d'ancres (vif / lisse). Feuille pure ; mod-plumeui traduit.
import { chemin_parser, chemin_serialiser, chemin_ancres } from "./mod-doc.js";

const clone = (t) => ({ segs: t.segs.map((s) => ({ c: s.c, p: s.p.slice() })), ancres: t.ancres.map((a) => a.slice()), sortante: t.sortante ? t.sortante.slice() : null });
export const trace_debut = (pt) => ({ segs: [{ c: "M", p: [+pt[0], +pt[1]] }], ancres: [[+pt[0], +pt[1]]], sortante: null });
export function trace_ajouter(trace, pt, { droite = false } = {}) {
  const t = clone(trace);
  const [x, y] = [+pt[0], +pt[1]];
  if (t.sortante && !droite) t.segs.push({ c: "C", p: [t.sortante[0], t.sortante[1], x, y, x, y] });
  else t.segs.push({ c: "L", p: [x, y] });
  t.ancres.push([x, y]); t.sortante = null;
  return t;
}
// glisser depuis le dernier nœud : la poignée SORTANTE suit le curseur, l'ENTRANTE est son miroir (sym) ou reste (asymétrique)
export function trace_poignee(trace, pt, { sym = true } = {}) {
  const t = clone(trace);
  const a = t.ancres[t.ancres.length - 1], s = t.segs[t.segs.length - 1];
  const ex = 2 * a[0] - pt[0], ey = 2 * a[1] - pt[1];
  if (sym && s.c === "L") { const prev = t.ancres[t.ancres.length - 2]; t.segs[t.segs.length - 1] = { c: "C", p: [prev[0], prev[1], ex, ey, a[0], a[1]] }; }
  else if (sym && s.c === "C") { s.p[2] = ex; s.p[3] = ey; }
  t.sortante = [+pt[0], +pt[1]];
  return t;
}
export function trace_retirer(trace) {
  if (!trace || trace.ancres.length <= 1) return null;
  const t = clone(trace);
  t.segs.pop(); t.ancres.pop(); t.sortante = null;
  return t;
}
export function trace_finir(trace, { fermer = false } = {}) {
  if (!trace || trace.ancres.length < 2) return null;
  const segs = trace.segs.map((s) => ({ c: s.c, p: s.p.slice() }));
  if (fermer) segs.push({ c: "Z", p: [] });
  return chemin_serialiser(segs);
}
export function elastique(trace, curseur) {
  if (!trace || !trace.ancres.length) return "";
  const a = trace.ancres[trace.ancres.length - 1];
  const seg = trace.sortante ? { c: "C", p: [trace.sortante[0], trace.sortante[1], curseur[0], curseur[1], curseur[0], curseur[1]] } : { c: "L", p: [curseur[0], curseur[1]] };
  return chemin_serialiser([{ c: "M", p: [a[0], a[1]] }, seg]);
}
export function contraindre_angle(p0, p, pas = 45) {
  const dx = p[0] - p0[0], dy = p[1] - p0[1], d = Math.hypot(dx, dy);
  if (!d) return [p[0], p[1]];
  // la direction est arrondie au pas, le point est PROJETÉ dessus (Affinity : la tangente glisse sur l'axe contraint)
  const a = Math.atan2(dy, dx), q = Math.round(a / (pas * Math.PI / 180)) * (pas * Math.PI / 180);
  const ux = Math.cos(q), uy = Math.sin(q), l = dx * ux + dy * uy;
  const r = (v) => Math.round(v * 1e6) / 1e6;
  return [r(p0[0] + l * ux), r(p0[1] + l * uy)];
}
// Catmull-Rom → Bézier cubique (tension 0,5) : les nœuds sont conservés, les poignées tangentes aux voisins
export function lisser_catmull(points, ferme = false) {
  const P = (points || []).map((p) => [+p[0], +p[1]]);
  const n = P.length;
  if (n < 2) return [];
  const at = (i) => ferme ? P[((i % n) + n) % n] : P[Math.max(0, Math.min(n - 1, i))];
  const segs = [{ c: "M", p: P[0].slice() }];
  const fin = ferme ? n : n - 1;
  for (let i = 0; i < fin; i++) {
    const p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
    segs.push({ c: "C", p: [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6, p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1]] });
  }
  if (ferme) segs.push({ c: "Z", p: [] });
  return segs;
}
export function chemin_ouvrir(d) {
  const segs = chemin_parser(d).filter((s) => s.c !== "Z");
  return chemin_serialiser(segs);
}
export function chemin_lisser(d) {
  const segs = chemin_parser(d);
  const ferme = segs.some((s) => s.c === "Z");
  const pts = chemin_ancres(segs).map((a) => [a.x, a.y]);
  return chemin_serialiser(lisser_catmull(pts, ferme));
}
export function chemin_fractionner(d, i) {
  const segs = chemin_parser(d);
  const ferme = segs.some((s) => s.c === "Z");
  const porteurs = segs.map((s, k) => s.c !== "Z" ? k : -1).filter((k) => k >= 0);
  const n = porteurs.length;
  if (i === undefined || i < 0 || i >= n) return [d];
  const fin = (s) => [s.p[s.p.length - 2], s.p[s.p.length - 1]];
  if (ferme) {
    // ouvrir à l'ancre i : le chemin repart de cette ancre et fait le tour
    const corps = porteurs.slice(1).map((k) => segs[k]);            // les segments après M, dans l'ordre
    const retour = { c: "L", p: fin(segs[porteurs[0]]) };              // Z = retour droit au départ
    const anneau = [...corps, retour];                                // n segments, l'ancre i est la fin du segment i-1 (ancre 0 = M)
    const depart = fin(i === 0 ? segs[porteurs[0]] : segs[porteurs[i]]);
    const ordre = [...anneau.slice(i), ...anneau.slice(0, i)];
    return [chemin_serialiser([{ c: "M", p: depart }, ...ordre.map((s) => ({ c: s.c, p: s.p.slice() }))])];
  }
  if (i === 0 || i === n - 1) return [d];
  const a = segs.slice(0, porteurs[i] + 1), b = [{ c: "M", p: fin(segs[porteurs[i]]) }, ...segs.slice(porteurs[i] + 1)];
  return [chemin_serialiser(a), chemin_serialiser(b)];
}
export function trace_depuis_chemin(d) {
  const segs = chemin_parser(d);
  if (!segs.length || segs.some((s) => s.c === "Z")) return null;
  return { segs: segs.map((s) => ({ c: s.c, p: s.p.slice() })), ancres: chemin_ancres(segs).map((a) => [a.x, a.y]), sortante: null };
}
export function extremite_proche(d, pt, tol) {
  const segs = chemin_parser(d);
  if (!segs.length || segs.some((s) => s.c === "Z")) return null;
  const an = chemin_ancres(segs);
  if (an.length < 2) return null;
  const f = an[an.length - 1], s0 = an[0];
  if (Math.hypot(pt[0] - f.x, pt[1] - f.y) <= tol) return "fin";
  if (Math.hypot(pt[0] - s0.x, pt[1] - s0.y) <= tol) return "debut";
  return null;
}
export function types_ancres(d) {
  if (!d) return [];
  const segs = chemin_parser(d);
  // la même règle qu'op_noeud_convertir : l'ENTRANTE décide ; l'ancre M (sans entrante) se juge sur sa sortante
  return chemin_ancres(segs).map((a, i) => {
    const vive = (p) => p && (p.x !== a.x || p.y !== a.y);
    return vive(a.entrante) || (i === 0 && vive(a.sortante)) ? "lisse" : "vif";
  });
}
