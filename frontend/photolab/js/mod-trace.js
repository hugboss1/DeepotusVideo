// mod-trace.js — t156 (parité L6) : outils Plume (P) et Sélection de tracé (A), panneau Tracés.
// Plume (amont vector_ui.rs) : clic = sommet d'angle, glisser = sommet lisse (poignées symétriques), clic sur le premier
// sommet = fermer, Entrée = terminer, Échap = abandonner, Ctrl+Entrée = sélection ; rien n'est envoyé avant la fin :
// mode Tracé -> path.set {name: "work"} (« Work Path »), mode Forme -> shape.create {kind: "path"}. Sélection de tracé :
// glisser = déplacer le tracé cible (calque de forme : shape.edit {move} ; sinon le tracé de travail). Tracés : lignes
// lues par path.list (enregistrés, de travail, du calque) ; clic = montrer le tracé sur la toile ; pied : remplir,
// contour, sélection, tracé depuis la sélection, nouveau, supprimer. Fonctions PURES exportées (qa/trace.test.mjs).
import { demanderNom } from "./mod-nommer.js";

export const TOLERANCE_FERMER = 6;            // px écran (amont)
const arr = (v) => Math.round(v * 100) / 100;
const pt = (p) => [arr(p[0]), arr(p[1])];

/* ── plume ── */
export const noeudAngle = (p) => ({ anchor: [p[0], p[1]], in: [p[0], p[1]], out: [p[0], p[1]], smooth: false });
// Glisser depuis le dernier sommet : poignée de sortie sous le pointeur, poignée d'entrée symétrique (sommet lisse).
export function tirerPoignee(noeuds, p) {
  if (!noeuds.length) return noeuds;
  const n = noeuds[noeuds.length - 1], a = n.anchor;
  const out = [p[0], p[1]], inn = [2 * a[0] - p[0], 2 * a[1] - p[1]];
  return [...noeuds.slice(0, -1), { anchor: a, in: inn, out, smooth: Math.hypot(p[0] - a[0], p[1] - a[1]) > 0.5 }];
}
// Le point écran s ferme-t-il le tracé (au moins deux sommets, près du premier) ?
export function fermeLeTrace(noeuds, s, ecran, tol = TOLERANCE_FERMER) {
  if (noeuds.length < 2) return false;
  const e = ecran(noeuds[0].anchor[0], noeuds[0].anchor[1]);
  return Math.hypot(e.x - s.x, e.y - s.y) <= tol;
}
export function chemin(noeuds, ferme) {
  return { subpaths: [{ closed: !!ferme, op: "combine", knots: noeuds.map((n) => ({ anchor: pt(n.anchor), in: pt(n.in), out: pt(n.out), smooth: !!n.smooth })) }],
    fillRule: "nonzero" };
}
// La commande de fin de tracé, ou null (moins de deux sommets).
export function commandePlume(mode, noeuds, ferme, fg = "#000000") {
  if (noeuds.length < 2) return null;
  const path = chemin(noeuds, ferme);
  if (mode === "forme") {
    return { command: "shape.create", params: { kind: "path", path, fill: ferme ? fg : null, stroke: ferme ? null : { width: 1, color: fg } } };
  }
  return { command: "path.set", params: { name: "work", path } };
}
export const MODES_PLUME = ["trace", "forme"];

/* ── chemins (affichage, déplacement) ── */
// Chemin du moteur -> attribut d SVG, par `ecran(x, y)` -> {x, y} (courbes de Bézier entre sommets).
export function dChemin(path, ecran) {
  if (!path || !Array.isArray(path.subpaths)) return "";
  const k = (n) => (Array.isArray(n) ? { anchor: n, in: n, out: n } : n);
  const P = (p) => { const e = ecran(p[0], p[1]); return arr(e.x) + " " + arr(e.y); };
  return path.subpaths.map((sp) => {
    const ns = (sp.knots || []).map(k);
    if (!ns.length) return "";
    let d = "M" + P(ns[0].anchor);
    const seg = (a, b) => " C" + P(a.out) + " " + P(b.in) + " " + P(b.anchor);
    for (let i = 1; i < ns.length; i++) d += seg(ns[i - 1], ns[i]);
    if (sp.closed && ns.length > 1) d += seg(ns[ns.length - 1], ns[0]) + " Z";
    return d;
  }).join(" ");
}
export function deplacerChemin(path, dx, dy) {
  const m = (p) => [arr(p[0] + dx), arr(p[1] + dy)];
  return { ...path, subpaths: (path.subpaths || []).map((sp) => ({ ...sp, knots: (sp.knots || []).map((n) => (Array.isArray(n) ? m(n)
    : { ...n, anchor: m(n.anchor), in: m(n.in || n.anchor), out: m(n.out || n.anchor) })) })) };
}
// Bornes [x0, y0, x1, y1] des ancres et poignées (vignettes).
export function bornes(path) {
  const xs = [], ys = [];
  for (const sp of (path && path.subpaths) || []) for (const n of sp.knots || []) {
    for (const p of Array.isArray(n) ? [n] : [n.anchor, n.in || n.anchor, n.out || n.anchor]) { xs.push(p[0]); ys.push(p[1]); }
  }
  return xs.length ? [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] : null;
}
// Lignes du panneau Tracés depuis path.list : enregistrés, puis de travail, puis celui du calque.
export function lignesTraces(liste) {
  if (!liste) return [];
  const l = (liste.paths || []).map((p) => ({ nom: p.name, cle: p.name, type: "enregistre" }));
  if (liste.workPath) l.push({ nom: null, cle: "work", type: "travail" });
  if (liste.layerPath) l.push({ nom: liste.layerPath.name, cle: "layer", type: "calque", calque: liste.layerPath.layer });
  return l;
}
// Cible de la Sélection de tracé : le calque de forme actif, sinon le tracé de travail.
export function cibleSelection(doc, liste) {
  const actif = doc && (doc.layers || []).find((x) => x.id === doc.activeLayer);
  if (actif && actif.kind === "Shape") return { type: "forme", calque: actif.id };
  if (liste && liste.workPath) return { type: "travail" };
  return null;
}
export function commandeDeplacement(cible, dx, dy, pathTravail) {
  if (!cible || (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5)) return null;
  if (cible.type === "forme") return { command: "shape.edit", params: { layer: cible.calque, move: [arr(dx), arr(dy)] } };
  if (cible.type === "travail" && pathTravail) return { command: "path.set", params: { name: "work", path: deplacerChemin(pathTravail, dx, dy) } };
  return null;
}
// Prochain nom libre « <base> n » parmi les tracés enregistrés.
export function nomLibre(liste, base) {
  const pris = new Set(((liste && liste.paths) || []).map((p) => p.name));
  let n = 1;
  while (pris.has(base + " " + n)) n++;
  return base + " " + n;
}

/* ── t254 (M5, photocraft 0.10) : ancres, poignées et segments (amont direct_select.rs, anchor_tools.rs) ── */
// Les outils qui éditent un tracé point par point. Ils visent, devant d'abord : le tracé enregistré choisi dans le
// panneau Tracés, la forme du calque actif, puis le tracé de travail (amont active_paths, sans masque vectoriel).
export const OUTILS_ANCRES = ["directSelection", "convertPoint", "addAnchorPoint", "deleteAnchorPoint"];
export const OUTILS_PLUMES = ["pen", "freeformPen", "curvaturePen"];
export const OUTILS_TRACE = [...OUTILS_PLUMES, ...OUTILS_ANCRES, "pathSelection"];
export const TOLERANCE_ANCRE = 6;            // px écran (amont)
export const AJUSTEMENT = { min: 0.5, max: 10, defaut: 2 };   // Plume libre › Ajustement de courbe (px, amont curve_fit)
const knot = (n) => (Array.isArray(n) ? { anchor: n, in: n, out: n, smooth: false } : { ...n, in: n.in || n.anchor, out: n.out || n.anchor });
const egal = (a, b) => Math.abs(a[0] - b[0]) < 1e-9 && Math.abs(a[1] - b[1]) < 1e-9;
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
// Point de la courbe de Bézier cubique du segment a -> b à t.
export function pointSegment(a, b, t) {
  const A = knot(a), B = knot(b), u = 1 - t;
  const w = [u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t], P = [A.anchor, A.out, B.in, B.anchor];
  return [0, 1].map((i) => w[0] * P[0][i] + w[1] * P[1][i] + w[2] * P[2][i] + w[3] * P[3][i]);
}
// Segments d'un sous-tracé : {k, a, b} (k = l'ancre qu'il quitte ; un sous-tracé fermé a aussi le segment du retour).
export function segments(sp) {
  const ns = ((sp && sp.knots) || []).map(knot), out = [];
  for (let k = 0; k + 1 < ns.length; k++) out.push({ k, a: ns[k], b: ns[k + 1] });
  if (sp && sp.closed && ns.length > 1) out.push({ k: ns.length - 1, a: ns[ns.length - 1], b: ns[0] });
  return out;
}
// Ce que le point DOCUMENT p touche sur `path` (tol en px document) : une poignée montrée, sinon une ancre, sinon un
// segment (t affiné), sinon null — l'ordre de l'amont (edit::hit) : les ancres passent avant les segments.
export function toucher(path, p, tol, montrees = []) {
  const sps = (path && path.subpaths) || [];
  let mieux = null;
  for (const h of montrees) {
    const n = sps[h.sp] && sps[h.sp].knots && sps[h.sp].knots[h.k];
    if (!n) continue;
    const d = dist(knot(n)[h.h], p);
    if (d <= tol && (!mieux || d < mieux.d)) mieux = { type: "poignee", sp: h.sp, k: h.k, h: h.h, d };
  }
  if (mieux) return mieux;
  sps.forEach((sp, s) => ((sp && sp.knots) || []).forEach((n, k) => {
    const d = dist(knot(n).anchor, p);
    if (d <= tol && (!mieux || d < mieux.d)) mieux = { type: "ancre", sp: s, k, d };
  }));
  if (mieux) return mieux;
  sps.forEach((sp, s) => segments(sp).forEach(({ k, a, b }) => {
    for (let i = 0; i <= 48; i++) {
      const t = i / 48, d = dist(pointSegment(a, b, t), p);
      if (d <= tol && (!mieux || d < mieux.d)) mieux = { type: "segment", sp: s, k, t, d };
    }
  }));
  if (mieux && mieux.type === "segment") {
    // affinage du t par dichotomie autour du meilleur échantillon
    const { a, b } = segments(sps[mieux.sp]).find((x) => x.k === mieux.k);
    let lo = Math.max(0, mieux.t - 1 / 48), hi = Math.min(1, mieux.t + 1 / 48);
    for (let i = 0; i < 24; i++) {
      const m1 = lo + (hi - lo) / 3, m2 = hi - (hi - lo) / 3;
      if (dist(pointSegment(a, b, m1), p) < dist(pointSegment(a, b, m2), p)) hi = m2; else lo = m1;
    }
    mieux.t = Math.min(0.999, Math.max(0.001, Math.round(((lo + hi) / 2) * 1000) / 1000));
  }
  return mieux;
}
// Poignées montrées : les deux de chaque ancre choisie et celles du segment cliqué (une poignée rentrée ne se montre pas).
export function poigneesMontrees(path, ancres, segment) {
  const sps = (path && path.subpaths) || [], out = [];
  const ajouter = (s, k, h) => {
    const n = sps[s] && sps[s].knots && sps[s].knots[k];
    if (n && !egal(knot(n)[h], knot(n).anchor) && !out.some((x) => x.sp === s && x.k === k && x.h === h)) out.push({ sp: s, k, h });
  };
  for (const [s, k] of ancres || []) { ajouter(s, k, "in"); ajouter(s, k, "out"); }
  if (segment) {
    const sp = sps[segment[0]], nb = (sp && sp.knots && sp.knots.length) || 0;
    ajouter(segment[0], segment[1], "out");
    if (nb) ajouter(segment[0], (segment[1] + 1) % nb, "in");
  }
  return out;
}
// Ancres dont le point est dans le cadre DOCUMENT [x0, y0, x1, y1] (cadre de sélection de la Sélection directe).
export function ancresDans(path, r) {
  const [x0, x1] = [Math.min(r[0], r[2]), Math.max(r[0], r[2])], [y0, y1] = [Math.min(r[1], r[3]), Math.max(r[1], r[3])], out = [];
  ((path && path.subpaths) || []).forEach((sp, s) => ((sp && sp.knots) || []).forEach((n, k) => {
    const a = knot(n).anchor;
    if (a[0] >= x0 && a[0] <= x1 && a[1] >= y0 && a[1] <= y1) out.push([s, k]);
  }));
  return out;
}
// Paramètres de cible d'une édition : {type: "travail"} -> work, {type: "forme"} -> layer (calque actif),
// {type: "enregistre", nom} -> le tracé enregistré.
export function paramsCible(c) {
  if (!c) return null;
  if (c.type === "forme") return { name: "layer" };
  if (c.type === "enregistre") return { name: c.nom };
  return { name: "work" };
}
const pt2 = (p) => [arr(p[0]), arr(p[1])];
// Une édition (glisser de d0 à d1, points DOCUMENT) -> la commande du moteur, ou null si rien ne bouge.
// edit : {type: "ancres", ancres, courbure?} | {type: "poignee", sp, k, h, de, independant} | {type: "segment", sp, k, t}
//      | {type: "convertir", sp, k} (glisser = poignées lisses tirées, clic = angle)
export function commandeEdition(edit, d0, d1, cible) {
  const base = paramsCible(cible);
  if (!edit || !base) return null;
  const d = [d1[0] - d0[0], d1[1] - d0[1]], bouge = Math.hypot(d[0], d[1]) >= 0.5;
  switch (edit.type) {
    case "ancres":
      if (!bouge || !edit.ancres.length) return null;
      return { command: "path.moveAnchors", params: { ...base, anchors: edit.ancres.map((a) => [a[0], a[1]]), move: pt2(d), ...(edit.courbure ? { curvature: true } : {}) } };
    case "poignee":
      if (!bouge) return null;
      return { command: "path.moveHandle", params: { ...base, subpath: edit.sp, knot: edit.k, handle: edit.h, to: pt2([edit.de[0] + d[0], edit.de[1] + d[1]]), independent: !!edit.independant } };
    case "segment":
      if (!bouge) return null;
      return { command: "path.bendSegment", params: { ...base, subpath: edit.sp, knot: edit.k, t: edit.t, move: pt2(d) } };
    case "convertir":
      return { command: "path.convertPoint", params: { ...base, subpath: edit.sp, knot: edit.k, ...(bouge ? { out: pt2(d1) } : {}) } };
    default: return null;
  }
}
// Aperçu (à l'écran seulement : le moteur rend le vrai tracé à la validation) de l'édition en cours.
export function apercuEdition(path, edit, d0, d1) {
  if (!path || !edit) return path;
  const d = [d1[0] - d0[0], d1[1] - d0[1]];
  const m = (p) => [p[0] + d[0], p[1] + d[1]];
  const sps = (path.subpaths || []).map((sp) => ({ ...sp, knots: (sp.knots || []).map(knot) }));
  const n = (s, k) => sps[s] && sps[s].knots[k];
  if (edit.type === "ancres") {
    for (const [s, k] of edit.ancres) { const x = n(s, k); if (x) Object.assign(x, { anchor: m(x.anchor), in: m(x.in), out: m(x.out) }); }
  } else if (edit.type === "poignee") {
    const x = n(edit.sp, edit.k);
    if (x) {
      const autre = edit.h === "in" ? "out" : "in", to = m(edit.de);
      x[edit.h] = to;
      if (x.smooth && !edit.independant) {
        const l = dist(x[autre], x.anchor), v = [x.anchor[0] - to[0], x.anchor[1] - to[1]], lv = Math.hypot(v[0], v[1]) || 1;
        x[autre] = [x.anchor[0] + (v[0] / lv) * l, x.anchor[1] + (v[1] / lv) * l];
      } else if (edit.independant) x.smooth = false;
    }
  } else if (edit.type === "segment") {
    const sp = sps[edit.sp], a = n(edit.sp, edit.k), b = sp && sp.knots[(edit.k + 1) % sp.knots.length];
    if (a && b) {
      const droit = egal(a.out, a.anchor) && egal(b.in, b.anchor);
      if (droit) { for (const x of [a, b]) Object.assign(x, { anchor: m(x.anchor), in: m(x.in), out: m(x.out) }); }
      else {
        const t = edit.t, u = 1 - t, den = 3 * u * t * (u + t) || 1;
        a.out = [a.out[0] + (d[0] * u) / den, a.out[1] + (d[1] * u) / den];
        b.in = [b.in[0] + (d[0] * t) / den, b.in[1] + (d[1] * t) / den];
      }
    }
  } else if (edit.type === "convertir") {
    const x = n(edit.sp, edit.k);
    if (x) {
      if (Math.hypot(d[0], d[1]) < 0.5) Object.assign(x, { in: x.anchor, out: x.anchor, smooth: false });
      else Object.assign(x, { out: d1, in: [2 * x.anchor[0] - d1[0], 2 * x.anchor[1] - d1[1]], smooth: true });
    }
  }
  return { ...path, subpaths: sps };
}
// Ajout / Suppression de point d'ancrage : Alt échange les deux outils (amont anchor_tools::effective).
export function outilAncre(outil, alt) {
  if (outil === "addAnchorPoint") return alt ? "deleteAnchorPoint" : "addAnchorPoint";
  if (outil === "deleteAnchorPoint") return alt ? "addAnchorPoint" : "deleteAnchorPoint";
  return outil;
}
// Le clic de l'outil d'ancre sur ce qu'il touche -> la commande (un segment pour Ajouter, une ancre pour Supprimer).
export function commandeAncre(outil, toucheVal, cible) {
  const base = paramsCible(cible);
  if (!toucheVal || !base) return null;
  if (outil === "addAnchorPoint" && toucheVal.type === "segment") return { command: "path.addAnchor", params: { ...base, subpath: toucheVal.sp, knot: toucheVal.k, t: toucheVal.t } };
  if (outil === "deleteAnchorPoint" && toucheVal.type === "ancre") return { command: "path.deleteAnchor", params: { ...base, subpath: toucheVal.sp, knot: toucheVal.k } };
  return null;
}
// Ancres choisies triées pour une suppression une à une (de la fin vers le début : les indices restent justes).
export const ordreSuppression = (ancres) => [...(ancres || [])].sort((a, b) => b[0] - a[0] || b[1] - a[1]);
// Suppr de la Sélection directe : une ancre à la fois (un seul état, clé `cle`) ; toutes les ancres du tracé choisies
// -> le tracé lui-même (le moteur refuse de retirer la dernière ancre) ; la forme d'un calque n'est jamais supprimée.
export function commandesSuppression(path, ancres, cible, cle) {
  const base = paramsCible(cible);
  if (!base || !ancres || !ancres.length) return [];
  const total = ((path && path.subpaths) || []).reduce((n, sp) => n + ((sp && sp.knots) || []).length, 0);
  const uniques = new Set(ancres.map((a) => a[0] + ":" + a[1]));
  if (total && uniques.size >= total) return cible.type === "forme" ? [] : [{ command: "path.delete", params: { name: base.name } }];
  return ordreSuppression(ancres).map(([s, k]) => ({ command: "path.deleteAnchor", params: { ...base, subpath: s, knot: k, coalesce: cle } }));
}

/* ── Plume de courbure et Plume libre : ancres posées par l'écran, poignées calculées par le MOTEUR ── */
// Aperçu des poignées (Catmull-Rom au tiers) ; à la validation, le moteur les recalcule (path.moveAnchors curvature).
export function noeudsCourbure(ancres, angles = [], ferme = false) {
  const n = ancres.length;
  return ancres.map((a, i) => {
    const angle = !!angles[i] || (!ferme && (i === 0 || i === n - 1)) || n < 3;
    if (angle) return { anchor: a, in: a, out: a, smooth: !angles[i] && n >= 3 };
    const p = ancres[(i - 1 + n) % n], q = ancres[(i + 1) % n];
    const tx = (q[0] - p[0]) / 6, ty = (q[1] - p[1]) / 6;
    return { anchor: a, in: [a[0] - tx, a[1] - ty], out: [a[0] + tx, a[1] + ty], smooth: true };
  });
}
// Commandes de fin de la Plume de courbure / libre : le tracé (ancres lisses, poignées rentrées) puis le recalcul
// de courbure du moteur, fondus en UN état d'historique par la même clé `coalesce`.
export function commandesCourbure(mode, ancres, angles, ferme, fg, cle) {
  if (!ancres || ancres.length < 2) return null;
  const knots = ancres.map((a, i) => ({ anchor: pt2(a), in: pt2(a), out: pt2(a), smooth: !angles[i] }));
  const path = { subpaths: [{ closed: !!ferme, op: "combine", knots }], fillRule: "nonzero" };
  const premiere = mode === "forme"
    ? { command: "shape.create", params: { kind: "path", path, fill: ferme ? fg : null, stroke: ferme ? null : { width: 1, color: fg }, coalesce: cle } }
    : { command: "path.set", params: { name: "work", path, coalesce: cle } };
  const reflux = { command: "path.moveAnchors", params: { name: mode === "forme" ? "layer" : "work", anchors: [[0, 0]], move: [0, 0], curvature: true, coalesce: cle } };
  return knots.some((k) => k.smooth) ? [premiere, reflux] : [premiere];
}
// Plume libre : simplification du tracé à main levée (Ramer-Douglas-Peucker, tolérance = Ajustement de courbe en px
// DOCUMENT) ; un virage de plus de 70° devient un angle (amont : les angles de fit_trace).
function distSegment(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1], l = dx * dx + dy * dy;
  if (!l) return dist(p, a);
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l));
  return dist(p, [a[0] + t * dx, a[1] + t * dy]);
}
export function simplifier(points, tol) {
  if (!points || points.length < 3) return (points || []).slice();
  let iMax = 0, dMax = 0;
  for (let i = 1; i < points.length - 1; i++) { const d = distSegment(points[i], points[0], points[points.length - 1]); if (d > dMax) { dMax = d; iMax = i; } }
  if (dMax <= tol) return [points[0], points[points.length - 1]];
  return [...simplifier(points.slice(0, iMax + 1), tol).slice(0, -1), ...simplifier(points.slice(iMax), tol)];
}
export function anglesVifs(ancres, ferme = false, seuil = 70) {
  const n = ancres.length;
  return ancres.map((a, i) => {
    if (!ferme && (i === 0 || i === n - 1)) return false;
    const p = ancres[(i - 1 + n) % n], q = ancres[(i + 1) % n];
    const u = [a[0] - p[0], a[1] - p[1]], v = [q[0] - a[0], q[1] - a[1]];
    const c = (u[0] * v[0] + u[1] * v[1]) / ((Math.hypot(...u) * Math.hypot(...v)) || 1);
    return Math.acos(Math.max(-1, Math.min(1, c))) * 180 / Math.PI > seuil;
  });
}
// Fin d'un geste de Plume libre (points DOCUMENT, tolFermer en px document) -> {ancres, angles, ferme} ou null.
export function traceLibre(points, ajustement, tolFermer) {
  if (!points || points.length < 2) return null;
  const longueur = points.slice(1).reduce((s, p, i) => s + dist(p, points[i]), 0);
  if (longueur < 1) return null;                                                   // un clic ne trace rien
  const ferme = dist(points[0], points[points.length - 1]) < tolFermer && longueur > 4 * tolFermer;
  let ancres = simplifier(points, Math.max(AJUSTEMENT.min, Math.min(AJUSTEMENT.max, Number(ajustement) || AJUSTEMENT.defaut)));
  if (ferme && ancres.length > 2) ancres = ancres.slice(0, -1);
  if (ancres.length < 2) return null;
  return { ancres: ancres.map(pt2), angles: anglesVifs(ancres, ferme), ferme };
}

/* ── menu contextuel des outils de tracé (amont canvas_tool_menu.rs PEN_MENU, entrées que le Photolab sert) ── */
// cible : {nom} du tracé visé ; forme : le calque actif est un calque de forme (avec fond ? contour ?) ; presse :
// ce que le presse-papiers de la session tient (fond, contour).
export function entreesMenuTrace(etat) {
  const e = etat || {}, nom = e.nom || null, enregistre = !!nom && nom !== "work" && nom !== "layer";
  const f = e.forme || null, pp = e.presse || {};
  return [
    { id: "path.toSelection", cle: "photolab.traces.selection", actif: !!nom },
    { id: "path.fill", cle: "photolab.traces.remplir", actif: !!nom && nom !== "layer" },
    { id: "path.stroke", cle: "photolab.traces.contour", actif: !!nom && nom !== "layer" },
    null,
    { id: "path.clippingPath.set", cle: "photolab.traces.detourage", actif: enregistre },
    { id: "path.clippingPath.clear", cle: "photolab.traces.detourage_retirer", actif: !!e.detourage },
    null,
    { id: "path.transform", cle: "photolab.traces.transformer", actif: !!nom },
    null,
    { id: "path.style.copyFill", cle: "photolab.traces.copier_fond", actif: !!(f && f.fond) },
    { id: "path.style.copyStroke", cle: "photolab.traces.copier_contour", actif: !!(f && f.contour) },
    null,
    { id: "path.style.pasteFill", cle: "photolab.traces.coller_fond", actif: !!f && !!pp.fond },
    { id: "path.style.pasteStroke", cle: "photolab.traces.coller_contour", actif: !!f && !!pp.contour },
  ];
}
// Champs des dialogues (format de photolab_registre.structurer) : bornes et défauts du dialogue amont.
export const CHAMPS_TRANSFORMER = [
  { cle: "translateX", cleLibelle: "photolab.traces.champ_deplacement_x", type: "number", min: -30000, max: 30000, defaut: 0, unite: "px" },
  { cle: "translateY", cleLibelle: "photolab.traces.champ_deplacement_y", type: "number", min: -30000, max: 30000, defaut: 0, unite: "px" },
  { cle: "scaleX", cleLibelle: "photolab.traces.champ_echelle_x", type: "number", min: 0.01, max: 100, defaut: 1 },
  { cle: "scaleY", cleLibelle: "photolab.traces.champ_echelle_y", type: "number", min: 0.01, max: 100, defaut: 1 },
  { cle: "angle", type: "number", min: -360, max: 360, defaut: 0, unite: "deg" },
];
export const CHAMPS_DETOURAGE = [{ cle: "flatness", cleLibelle: "photolab.traces.champ_aplatissement", type: "number", min: 0, max: 100, defaut: 0, entier: true }];

/* ───────────── côté DOM ───────────── */

export function initTrace(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const NS = "http://www.w3.org/2000/svg";
  const fg = () => (PL.etat.couleurs && PL.etat.couleurs.fg) || "#000000";
  PL.etat.plume = { mode: "trace" };
  let noeuds = [], tire = false, survol = null;
  let liste = null, choisi = null, cheminChoisi = null, cheminTravail = null, revLue = null;
  let cheminCalque = null;     // t254 : tracé de la forme du calque actif (path.info {name: "layer"})
  let deplace = null;          // Sélection de tracé : {d0, path, cible}

  const redessiner = () => { if (PL.dessinerFourmis) PL.dessinerFourmis(); };
  function finir(versSelection = false) {
    const c = commandePlume(PL.etat.plume.mode, noeuds, false, fg());
    noeuds = []; tire = false; redessiner();
    if (!c) return;
    PL.executer(c.command, c.params).then((r) => { if (versSelection && r && r.ok && c.command === "path.set") PL.executer("path.toSelection", { name: "work" }); });
  }
  PL.gestes.pen = {
    appui(p) {
      if (fermeLeTrace(noeuds, { x: p.sx, y: p.sy }, PL.vue.versEcran)) {
        const c = commandePlume(PL.etat.plume.mode, noeuds, true, fg());
        noeuds = []; redessiner();
        if (c) PL.executer(c.command, c.params);
        return;
      }
      noeuds = [...noeuds, noeudAngle([p.x, p.y])]; tire = true; redessiner();
    },
    bouger(p) { if (tire) { noeuds = tirerPoignee(noeuds, [p.x, p.y]); redessiner(); } },
    relacher() { tire = false; },
    survol(p) { survol = [p.x, p.y]; if (noeuds.length) redessiner(); },
    touche(ev) {
      if (!noeuds.length) return false;
      if (ev.key === "Enter") { finir(false); return true; }
      if (ev.key === "Escape") { noeuds = []; redessiner(); return true; }
      return false;
    },
    quitter() { if (noeuds.length >= 2) finir(false); else { noeuds = []; } },
    annuler() { tire = false; },
  };
  // Ctrl+Entrée : le tracé en cours devient une sélection (le répartiteur ignore les touches avec Ctrl).
  document.addEventListener("keydown", (ev) => {
    if (PL.etat.outil === "pen" && noeuds.length && (ev.ctrlKey || ev.metaKey) && ev.key === "Enter") { ev.preventDefault(); finir(true); }
  });
  PL.gestes.pathSelection = {
    async appui(p) {
      await relireListe();
      const cible = cibleSelection(PL.etat.doc, liste);
      deplace = cible ? { d0: [p.x, p.y], cible, d: [0, 0] } : null;
    },
    bouger(p) { if (deplace) { deplace.d = [p.x - deplace.d0[0], p.y - deplace.d0[1]]; redessiner(); } },
    relacher() {
      if (!deplace) return;
      const c = commandeDeplacement(deplace.cible, deplace.d[0], deplace.d[1], cheminTravail);
      deplace = null; redessiner();
      if (c) PL.executer(c.command, c.params);
    },
    annuler() { deplace = null; redessiner(); },
    quitter() { deplace = null; },
  };

  /* ── t254 (M5) : Sélection directe, Conversion de point, Ajout / Suppression de point d'ancrage ── */
  const tolDoc = () => TOLERANCE_ANCRE / Math.max(0.01, PL.vue.v.z);
  // Les tracés que ces outils éditent, devant d'abord : le tracé enregistré choisi, la forme active, le tracé de travail.
  function candidats() {
    const out = [];
    if (choisi && choisi.type === "enregistre" && cheminChoisi) out.push({ cible: { type: "enregistre", nom: choisi.cle }, path: cheminChoisi });
    if (cheminCalque) out.push({ cible: { type: "forme" }, path: cheminCalque });
    if (cheminTravail) out.push({ cible: { type: "travail" }, path: cheminTravail });
    return out;
  }
  const memeCible = (a, b) => !!a && !!b && a.type === b.type && (a.nom || null) === (b.nom || null);
  let ds = { cible: null, ancres: [], segment: null };      // ancres choisies (Sélection directe, Conversion de point)
  let edition = null;                                       // glisser en cours : {edit, cible, base, d0, d1} | {cadre}
  let survolAncre = null;                                   // Ajout / Suppression : {path, touche}
  const cheminCible = (cible) => (candidats().find((c) => memeCible(c.cible, cible)) || {}).path || null;
  const choisir = (cible, ancres, segment = null) => { ds = { cible, ancres, segment }; };
  const valide = (path, [s, k]) => !!(path && path.subpaths && path.subpaths[s] && path.subpaths[s].knots && path.subpaths[s].knots[k]);
  function toucherCandidats(p, avecPoignees) {
    const tol = tolDoc();
    if (avecPoignees && ds.cible) {
      const path = cheminCible(ds.cible);
      const t = path && toucher(path, p, tol, poigneesMontrees(path, ds.ancres, ds.segment));
      if (t && t.type === "poignee") return { cible: ds.cible, path, touche: t };
    }
    for (const c of candidats()) { const t = toucher(c.path, p, tol); if (t) return { cible: c.cible, path: c.path, touche: t }; }
    return null;
  }
  const cleUnique = (base) => base + "-" + Date.now().toString(36) + "-" + Math.floor(Math.random() * 1e6).toString(36);
  async function enchainer(cmds) {
    for (const c of cmds || []) { const r = await PL.executer(c.command, c.params); if (!r || !r.ok) return false; }
    return true;
  }
  function editer(c) { if (c) PL.executer(c.command, c.params); }
  PL.gestes.directSelection = {
    async appui(p, ev) {
      await relireListe();
      const h = toucherCandidats([p.x, p.y], true);
      const d0 = [p.x, p.y];
      if (!h) { edition = { cadre: { d0, d1: d0, ajouter: !!ev.shiftKey } }; redessiner(); return; }
      const t = h.touche;
      if (t.type === "poignee") {
        const n = knot(h.path.subpaths[t.sp].knots[t.k]);
        edition = { cible: h.cible, base: h.path, d0, d1: d0, edit: { type: "poignee", sp: t.sp, k: t.k, h: t.h, de: n[t.h], independant: !!ev.altKey } };
      } else if (t.type === "ancre") {
        const deja = memeCible(ds.cible, h.cible) ? ds.ancres : [];
        const dedans = deja.some((a) => a[0] === t.sp && a[1] === t.k);
        let ancres;
        if (ev.altKey) ancres = h.path.subpaths[t.sp].knots.map((_, k) => [t.sp, k]);                  // ⌥ : le sous-tracé entier
        else if (ev.shiftKey) ancres = dedans ? deja.filter((a) => !(a[0] === t.sp && a[1] === t.k)) : [...deja, [t.sp, t.k]];
        else ancres = dedans ? deja : [[t.sp, t.k]];
        choisir(h.cible, ancres);
        edition = ancres.length ? { cible: h.cible, base: h.path, d0, d1: d0, edit: { type: "ancres", ancres } } : null;
      } else {
        choisir(h.cible, [], [t.sp, t.k]);
        edition = { cible: h.cible, base: h.path, d0, d1: d0, edit: { type: "segment", sp: t.sp, k: t.k, t: t.t } };
      }
      redessiner();
    },
    bouger(p) { if (edition) { if (edition.cadre) edition.cadre.d1 = [p.x, p.y]; else edition.d1 = [p.x, p.y]; redessiner(); } },
    relacher() {
      const e = edition; edition = null;
      if (!e) return;
      if (e.cadre) {
        const c = candidats().find((x) => memeCible(x.cible, ds.cible)) || candidats()[0];
        const dans = c ? ancresDans(c.path, [e.cadre.d0[0], e.cadre.d0[1], e.cadre.d1[0], e.cadre.d1[1]]) : [];
        const glisse = Math.hypot(e.cadre.d1[0] - e.cadre.d0[0], e.cadre.d1[1] - e.cadre.d0[1]) * PL.vue.v.z >= 3;
        if (!glisse) choisir(null, []);                                                                   // clic dans le vide
        else if (c) choisir(c.cible, e.cadre.ajouter && memeCible(ds.cible, c.cible) ? [...ds.ancres, ...dans.filter((a) => !ds.ancres.some((b) => b[0] === a[0] && b[1] === a[1]))] : dans);
        redessiner(); return;
      }
      redessiner();
      editer(commandeEdition(e.edit, e.d0, e.d1, e.cible));
    },
    touche(ev) {
      if (!ds.cible || !ds.ancres.length) return false;
      const pas = ev.shiftKey ? 10 : 1;
      const fl = { ArrowLeft: [-pas, 0], ArrowRight: [pas, 0], ArrowUp: [0, -pas], ArrowDown: [0, pas] }[ev.key];
      if (fl) { editer(commandeEdition({ type: "ancres", ancres: ds.ancres }, [0, 0], fl, ds.cible)); return true; }
      if (ev.key === "Delete" || ev.key === "Backspace") {
        const cmds = commandesSuppression(cheminCible(ds.cible), ds.ancres, ds.cible, cleUnique("pl-ancres"));
        choisir(ds.cible, []); enchainer(cmds); redessiner(); return true;
      }
      if (ev.key === "Escape") { choisir(null, []); redessiner(); return true; }
      return false;
    },
    annuler() { edition = null; redessiner(); },
    quitter() { edition = null; },
  };
  PL.gestes.convertPoint = {
    async appui(p, ev) {
      await relireListe();
      const h = toucherCandidats([p.x, p.y], true);
      const d0 = [p.x, p.y];
      edition = null;
      if (!h || h.touche.type === "segment") return;                       // amont : un segment ou le vide ne fait rien
      const t = h.touche;
      if (t.type === "poignee") {
        const n = knot(h.path.subpaths[t.sp].knots[t.k]);
        edition = { cible: h.cible, base: h.path, d0, d1: d0, edit: { type: "poignee", sp: t.sp, k: t.k, h: t.h, de: n[t.h], independant: true } };
      } else {
        choisir(h.cible, [[t.sp, t.k]]);                                       // l'ancre convertie montre ses poignées
        edition = { cible: h.cible, base: h.path, d0, d1: d0, edit: { type: "convertir", sp: t.sp, k: t.k } };
      }
      redessiner();
    },
    bouger(p) { if (edition) { edition.d1 = [p.x, p.y]; redessiner(); } },
    relacher() { const e = edition; edition = null; redessiner(); if (e) editer(commandeEdition(e.edit, e.d0, e.d1, e.cible)); },
    annuler() { edition = null; redessiner(); },
    quitter() { edition = null; },
  };
  for (const id of ["addAnchorPoint", "deleteAnchorPoint"]) {
    PL.gestes[id] = {
      async appui(p, ev) {
        await relireListe();
        const outil = outilAncre(id, ev.altKey);
        for (const c of candidats()) {
          const cmd = commandeAncre(outil, toucher(c.path, [p.x, p.y], tolDoc()), c.cible);
          if (cmd) { choisir(null, []); survolAncre = null; editer(cmd); return; }
        }
      },
      bouger() {},
      relacher() {},
      survol(p, ev) {
        const outil = outilAncre(id, ev && ev.altKey);
        survolAncre = null;
        for (const c of candidats()) {
          const t = toucher(c.path, [p.x, p.y], tolDoc());
          if (t && ((outil === "addAnchorPoint" && t.type === "segment") || (outil === "deleteAnchorPoint" && t.type === "ancre"))) { survolAncre = { path: c.path, touche: t }; break; }
        }
        redessiner();
      },
      quitter() { survolAncre = null; },
    };
  }

  /* Plume de courbure : clic = ancre lisse (glisser = la placer), clic sur la première = fermer, double-clic = angle ;
     sans tracé en cours, glisser une ancre du tracé actif la déplace et la courbe suit (path.moveAnchors curvature),
     double-clic sur une de ses ancres = path.convertPoint curvature. Fin = Entrée, Échap abandonne. */
  let courbe = { ancres: [], angles: [], deplace: null };
  const finirCourbe = async (ferme) => {
    const c = commandesCourbure(PL.etat.plume.mode, courbe.ancres, courbe.angles, ferme, fg(), cleUnique("pl-courbure"));
    courbe = { ancres: [], angles: [], deplace: null }; redessiner();
    if (c) await enchainer(c);
  };
  const ancreCourbe = (p) => {
    const tol = tolDoc();
    let i = null, m = Infinity;
    courbe.ancres.forEach((a, k) => { const d = dist(a, [p.x, p.y]); if (d < tol && d < m) { m = d; i = k; } });
    return i;
  };
  PL.gestes.curvaturePen = {
    async appui(p) {
      if (!courbe.ancres.length) {
        await relireListe();
        const h = toucherCandidats([p.x, p.y], false);
        if (h && h.touche.type === "ancre") {                                   // tracé actif : la courbe suit l'ancre tirée
          choisir(h.cible, [[h.touche.sp, h.touche.k]]);
          edition = { cible: h.cible, base: h.path, d0: [p.x, p.y], d1: [p.x, p.y], edit: { type: "ancres", ancres: [[h.touche.sp, h.touche.k]], courbure: true } };
          redessiner(); return;
        }
      }
      const i = ancreCourbe(p);
      if (i === 0 && courbe.ancres.length >= 3) { finirCourbe(true); return; }
      if (i == null) { courbe.ancres = [...courbe.ancres, [p.x, p.y]]; courbe.angles = [...courbe.angles, false]; courbe.deplace = courbe.ancres.length - 1; }
      else courbe.deplace = i;
      redessiner();
    },
    bouger(p) {
      if (edition) { edition.d1 = [p.x, p.y]; redessiner(); return; }
      if (courbe.deplace != null) { courbe.ancres = courbe.ancres.map((a, k) => (k === courbe.deplace ? [p.x, p.y] : a)); redessiner(); }
    },
    relacher() {
      if (edition) { const e = edition; edition = null; redessiner(); editer(commandeEdition(e.edit, e.d0, e.d1, e.cible)); return; }
      courbe.deplace = null;
    },
    async double(p) {
      if (courbe.ancres.length) {
        const i = ancreCourbe(p);
        if (i != null) { courbe.angles = courbe.angles.map((v, k) => (k === i ? !v : v)); redessiner(); }
        return;
      }
      await relireListe();
      const h = toucherCandidats([p.x, p.y], false);
      if (h && h.touche.type === "ancre") editer({ command: "path.convertPoint", params: { ...paramsCible(h.cible), subpath: h.touche.sp, knot: h.touche.k, curvature: true } });
    },
    survol(p) { survol = [p.x, p.y]; if (courbe.ancres.length) redessiner(); },
    touche(ev) {
      if (!courbe.ancres.length) return false;
      if (ev.key === "Enter") { finirCourbe(false); return true; }
      if (ev.key === "Escape") { courbe = { ancres: [], angles: [], deplace: null }; redessiner(); return true; }
      return false;
    },
    quitter() { if (courbe.ancres.length >= 2) finirCourbe(false); else courbe = { ancres: [], angles: [], deplace: null }; edition = null; },
    annuler() { courbe.deplace = null; edition = null; },
  };
  /* Plume libre : glisser = tracé à main levée, simplifié (Ajustement de courbe) puis lissé par le moteur. */
  PL.etat.plume.ajustement = AJUSTEMENT.defaut;
  let libre = null;
  PL.gestes.freeformPen = {
    appui(p) { libre = [[p.x, p.y]]; PL.apercu = { type: "trace", points: libre }; redessiner(); },
    bouger(p) { if (libre) { libre.push([p.x, p.y]); PL.apercu = { type: "trace", points: libre }; redessiner(); } },
    relacher() {
      const pts = libre; libre = null; PL.apercu = null; redessiner();
      const t = traceLibre(pts, PL.etat.plume.ajustement, tolDoc());
      if (t) enchainer(commandesCourbure(PL.etat.plume.mode, t.ancres, t.angles, t.ferme, fg(), cleUnique("pl-libre")));
    },
    annuler() { libre = null; PL.apercu = null; redessiner(); },
    quitter() { libre = null; },
  };
  // Les indices choisis ne valent que pour le tracé tel qu'il était : relus à chaque document.
  PL.surDoc.push(() => {
    const path = ds.cible && cheminCible(ds.cible);
    if (ds.cible && path) ds = { ...ds, ancres: ds.ancres.filter((a) => valide(path, a)) };
  });

  /* menu contextuel des outils de tracé (clic droit sur la toile) */
  let pressePapiers = { fond: false, contour: false };
  let menuCtx = null;
  const fermerMenuCtx = () => { if (menuCtx) { menuCtx.remove(); menuCtx = null; } };
  function nomVise() {
    if (choisi) return choisi.cle;
    if (liste && liste.workPath) return "work";
    if (cheminCalque) return "layer";
    return null;
  }
  async function etatMenu() {
    await relireListe();
    const d = PL.etat.doc;
    const actif = d && (d.layers || []).find((x) => x.id === d.activeLayer);
    let forme = null;
    if (actif && actif.kind === "Shape") {
      forme = { fond: true, contour: true };
      try { const r = await PL.post("/executer", { command: "shape.info", params: {} }); if (r) forme = { fond: r.fill != null, contour: r.stroke != null }; } catch (e) { /* facultatif */ }
    }
    return { nom: nomVise(), forme, presse: pressePapiers, detourage: !!(liste && liste.clippingPath) };
  }
  async function choisirMenu(id, nom) {
    if (id === "path.fill") return PL.executer("path.fill", { name: nom, color: fg() });
    if (id === "path.stroke") return PL.executer("path.stroke", { name: nom, tool: "brush" });
    if (id === "path.toSelection") return PL.executer("path.toSelection", { name: nom });
    if (id === "path.transform") {
      return PL.ouvrirReglage({ id, libelle: T("photolab.traces.transformer"), champs: CHAMPS_TRANSFORMER },
        { versCommande: (p) => ({ command: id, params: { name: nom, ...p } }) });
    }
    if (id === "path.clippingPath.set") {
      return PL.ouvrirReglage({ id, libelle: T("photolab.traces.detourage"), champs: CHAMPS_DETOURAGE },
        { versCommande: (p) => ({ command: id, params: { name: nom, ...p } }) });
    }
    const r = await PL.executer(id, {});
    if (r && r.ok && id === "path.style.copyFill") pressePapiers = { ...pressePapiers, fond: true };
    if (r && r.ok && id === "path.style.copyStroke") pressePapiers = { ...pressePapiers, contour: true };
    return r;
  }
  async function ouvrirMenuCtx(x, y, cibleNom) {
    fermerMenuCtx();
    const e = await etatMenu();
    if (cibleNom !== undefined) e.nom = cibleNom;
    const m = document.createElement("div"); m.className = "menu-panneau tra-menu"; m.setAttribute("role", "menu");
    for (const it of entreesMenuTrace(e)) {
      if (!it) { const s = document.createElement("div"); s.className = "menu-sep"; m.appendChild(s); continue; }
      const l = document.createElement("div"); l.className = "menu-ligne " + (it.actif ? "actif" : "inactif"); l.setAttribute("role", "menuitem"); l.dataset.id = it.id;
      if (!it.actif) l.setAttribute("aria-disabled", "true");
      const lib = document.createElement("span"); lib.className = "menu-lib"; lib.textContent = T(it.cle) + (it.id === "path.transform" || it.id === "path.clippingPath.set" ? "…" : "");
      l.appendChild(lib);
      l.addEventListener("pointerenter", () => m.querySelectorAll(".menu-ligne").forEach((x) => x.classList.toggle("survol", x === l)));
      l.addEventListener("click", (ev) => { ev.stopPropagation(); if (!it.actif) return; fermerMenuCtx(); choisirMenu(it.id, e.nom); });
      m.appendChild(l);
    }
    document.body.appendChild(m);
    m.style.left = Math.min(x, innerWidth - m.offsetWidth - 4) + "px";
    m.style.top = Math.min(y, innerHeight - m.offsetHeight - 4) + "px";
    menuCtx = m;
  }
  document.addEventListener("pointerdown", (ev) => { if (menuCtx && !ev.target.closest(".tra-menu")) fermerMenuCtx(); }, true);
  document.addEventListener("keydown", (ev) => { if (menuCtx && ev.key === "Escape") { ev.stopPropagation(); fermerMenuCtx(); } }, true);
  const toile = PL.$("#toile");
  if (toile) toile.addEventListener("contextmenu", (ev) => {
    if (!PL.etat.doc || !OUTILS_TRACE.includes(PL.etat.outil)) return;
    ev.preventDefault(); ouvrirMenuCtx(ev.clientX, ev.clientY);
  });

  // Dessins sur la toile : tracé de la plume (et sa ligne élastique), tracé choisi dans le panneau, tracé déplacé.
  PL.dessinsSup = PL.dessinsSup || [];
  // t254 : tracés éditables, leurs ancres (choisies pleines) et poignées ; aperçu de l'édition en cours ; survol des
  // outils d'ancre ; Plume de courbure en cours ; cadre de sélection des ancres.
  PL.dessinsSup.push((svg, el, ecran) => {
    const outil = PL.etat.outil;
    const ancre = (p, cls) => { const e = ecran(p[0], p[1]); svg.appendChild(el("rect", { x: e.x - 3, y: e.y - 3, width: 6, height: 6 }, cls)); };
    const poignee = (a, h) => {
      const e0 = ecran(a[0], a[1]), e1 = ecran(h[0], h[1]);
      svg.appendChild(el("line", { x1: e0.x, y1: e0.y, x2: e1.x, y2: e1.y }, "trace-poignee"));
      svg.appendChild(el("circle", { cx: e1.x, cy: e1.y, r: 3 }, "trace-poignee"));
    };
    if (OUTILS_ANCRES.includes(outil) || (outil === "curvaturePen" && !courbe.ancres.length)) {
      for (const c of candidats()) {
        const enEdition = edition && !edition.cadre && memeCible(edition.cible, c.cible);
        const path = enEdition ? apercuEdition(c.path, edition.edit, edition.d0, edition.d1) : c.path;
        svg.appendChild(el("path", { d: dChemin(path, ecran), fill: "none" }, "trace-montre"));
        const miens = memeCible(ds.cible, c.cible);
        (path.subpaths || []).forEach((sp, s) => (sp.knots || []).forEach((n, k) => {
          ancre(knot(n).anchor, miens && ds.ancres.some((a) => a[0] === s && a[1] === k) ? "trace-ancre actif" : "trace-ancre");
        }));
        if (miens) for (const h of poigneesMontrees(path, ds.ancres, ds.segment)) { const n = knot(path.subpaths[h.sp].knots[h.k]); poignee(n.anchor, n[h.h]); }
      }
      if (survolAncre && (outil === "addAnchorPoint" || outil === "deleteAnchorPoint")) {
        const t = survolAncre.touche, sp = survolAncre.path.subpaths[t.sp];
        if (t.type === "segment") {
          const s = segments(sp).find((x) => x.k === t.k);
          if (s) {
            const pts = Array.from({ length: 33 }, (_, i) => ecran(...pointSegment(s.a, s.b, i / 32)));
            svg.appendChild(el("path", { d: "M" + pts.map((q) => arr(q.x) + " " + arr(q.y)).join(" L"), fill: "none" }, "trace-survol"));
            ancre(pointSegment(s.a, s.b, t.t), "trace-ancre actif");
          }
        } else ancre(knot(sp.knots[t.k]).anchor, "trace-ancre actif trace-survol-ancre");
      }
      if (edition && edition.cadre) {
        const a = ecran(...edition.cadre.d0), b = ecran(...edition.cadre.d1);
        svg.appendChild(el("rect", { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), width: Math.abs(b.x - a.x), height: Math.abs(b.y - a.y) }, "trace-cadre"));
      }
    }
    if (outil === "curvaturePen" && courbe.ancres.length) {
      const suivantes = survol && courbe.deplace == null && courbe.ancres.length >= 2 ? [...courbe.ancres, survol] : courbe.ancres;
      const ns = noeudsCourbure(suivantes, courbe.angles, false);
      svg.appendChild(el("path", { d: dChemin({ subpaths: [{ closed: false, knots: ns }] }, ecran), fill: "none" }, "trace-cours"));
      if (survol && courbe.ancres.length === 1) {
        const a = ecran(...courbe.ancres[0]), b = ecran(...survol);
        svg.appendChild(el("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y }, "trace-elastique"));
      }
      courbe.ancres.forEach((a, i) => {
        if (courbe.angles[i]) ancre(a, i === courbe.ancres.length - 1 ? "trace-ancre actif" : "trace-ancre");
        else { const e = ecran(a[0], a[1]); svg.appendChild(el("circle", { cx: e.x, cy: e.y, r: 3.5 }, i === courbe.ancres.length - 1 ? "trace-ancre actif" : "trace-ancre")); }
      });
    }
  });
  PL.dessinsSup.push((svg, el, ecran) => {
    if (PL.etat.outil === "pen" && noeuds.length) {
      svg.appendChild(el("path", { d: dChemin(chemin(noeuds, false), ecran), fill: "none" }, "trace-cours"));
      if (survol && !tire) {
        const a = ecran(noeuds[noeuds.length - 1].anchor[0], noeuds[noeuds.length - 1].anchor[1]), b = ecran(survol[0], survol[1]);
        svg.appendChild(el("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y }, "trace-elastique"));
      }
      noeuds.forEach((n, i) => { const e = ecran(n.anchor[0], n.anchor[1]); svg.appendChild(el("rect", { x: e.x - 3, y: e.y - 3, width: 6, height: 6 }, i === noeuds.length - 1 ? "trace-ancre actif" : "trace-ancre")); });
      const n = noeuds[noeuds.length - 1];
      if (n.smooth) for (const h of [n.in, n.out]) {
        const a = ecran(n.anchor[0], n.anchor[1]), e = ecran(h[0], h[1]);
        svg.appendChild(el("line", { x1: a.x, y1: a.y, x2: e.x, y2: e.y }, "trace-poignee"));
        svg.appendChild(el("circle", { cx: e.x, cy: e.y, r: 3 }, "trace-poignee"));
      }
    }
    const montre = deplace && deplace.cible.type === "travail" && cheminTravail ? deplacerChemin(cheminTravail, deplace.d[0], deplace.d[1])
      : PL.etat.outil === "pathSelection" && cheminTravail ? cheminTravail : cheminChoisi;
    if (montre) svg.appendChild(el("path", { d: dChemin(montre, ecran), fill: "none" }, "trace-montre"));
  });

  /* panneau Tracés */
  const corps = PL.$("#corpsTraces");
  async function relireListe() {
    const d = PL.etat.doc;
    if (!d) { liste = null; cheminTravail = null; return; }
    if (revLue === d.revision && liste) return;
    revLue = d.revision;
    try { liste = await PL.post("/executer", { command: "path.list", params: {} }); } catch (e) { liste = null; }
    cheminTravail = null;
    if (liste && liste.workPath) {
      try { const r = await PL.post("/executer", { command: "path.info", params: { name: "work" } }); cheminTravail = r && r.path; } catch (e) { /* facultatif */ }
    }
    // t254 : la forme du calque actif et le tracé enregistré choisi, relus avec le document (les outils d'ancre les éditent)
    cheminCalque = null;
    const actif = (d.layers || []).find((x) => x.id === d.activeLayer);
    if (liste && liste.layerPath && actif && actif.kind === "Shape") {
      try { const r = await PL.post("/executer", { command: "path.info", params: { name: "layer" } }); cheminCalque = r && r.path; } catch (e) { /* facultatif */ }
    }
    if (choisi && choisi.type === "enregistre") {
      if (!(liste && (liste.paths || []).some((p) => p.name === choisi.cle))) { choisi = null; cheminChoisi = null; }
      else { try { const r = await PL.post("/executer", { command: "path.info", params: { name: choisi.cle } }); cheminChoisi = r && r.path; } catch (e) { /* facultatif */ } }
    }
  }
  if (!corps) return;
  const zone = document.createElement("div"); zone.className = "tra-liste";
  const pied = document.createElement("div"); pied.className = "pr-pied";
  corps.append(zone, pied);
  const bouton = (icone, cle, fn) => {
    const b = document.createElement("button"); b.type = "button"; b.className = "pr-btn"; b.dataset.icone = icone;
    b.title = T(cle); b.setAttribute("aria-label", b.title); b.addEventListener("click", fn); pied.appendChild(b); return b;
  };
  const nomCible = () => (choisi ? choisi.cle : liste && liste.workPath ? "work" : null);
  const bRemplir = bouton("dz-edit-remplir-trace", "photolab.traces.remplir", () => { const n = nomCible(); if (n) PL.executer("path.fill", { name: n, color: fg() }); });
  const bContour = bouton("dz-edit-contour-trace", "photolab.traces.contour", () => { const n = nomCible(); if (n) PL.executer("path.stroke", { name: n, tool: "brush" }); });
  const bSelection = bouton("dz-edit-charger-selection", "photolab.traces.selection", () => { const n = nomCible(); if (n) PL.executer("path.toSelection", { name: n }); });
  const bDepuisSel = bouton("dz-edit-selection-vers-trace", "photolab.traces.depuis_selection", () => PL.executer("select.toWorkPath", { tolerance: 2 }));
  bouton("dz-action-ajouter", "photolab.traces.nouveau", async () => {
    await relireListe();
    PL.executer("path.set", { name: nomLibre(liste, T("photolab.traces.base")), path: { subpaths: [] } });
  });
  const bSuppr = bouton("dz-action-supprimer", "photolab.traces.supprimer", () => { if (choisi && choisi.type !== "calque") { PL.executer("path.delete", { name: choisi.cle }); choisi = null; cheminChoisi = null; } });
  if (PL.hydraterIcones) PL.hydraterIcones(pied);

  function vignette(path) {
    const svg = document.createElementNS(NS, "svg"); svg.setAttribute("class", "tra-vignette"); svg.setAttribute("viewBox", "0 0 40 30");
    const d = PL.etat.doc;
    if (path && d) {
      const k = Math.min(40 / d.width, 30 / d.height), ox = (40 - d.width * k) / 2, oy = (30 - d.height * k) / 2;
      const p = document.createElementNS(NS, "path");
      p.setAttribute("d", dChemin(path, (x, y) => ({ x: ox + x * k, y: oy + y * k })));
      svg.appendChild(p);
    }
    return svg;
  }
  async function cheminDe(l) {
    try { const r = await PL.post("/executer", { command: "path.info", params: { name: l.cle } }); return r && r.path; } catch (e) { return null; }
  }
  let jeton = 0;               // deux dessins peuvent se chevaucher (async) : seul le dernier remplit la liste
  async function dessiner() {
    const n = ++jeton;
    const d = PL.etat.doc;
    if (!d) { zone.textContent = ""; [bRemplir, bContour, bSelection, bDepuisSel, bSuppr].forEach((b) => { b.disabled = true; }); return; }
    await relireListe();
    const frag = document.createDocumentFragment();
    for (const l of lignesTraces(liste)) {
      const row = document.createElement("div"); row.className = "tra-ligne" + (choisi && choisi.cle === l.cle ? " choisi" : "") + (l.type !== "enregistre" ? " italique" : "");
      const nom = document.createElement("span"); nom.className = "tra-nom";
      nom.textContent = l.type === "travail" ? T("photolab.traces.travail") : l.nom;
      if (l.type !== "travail") nom.setAttribute("data-dz-brut", "");
      const p = await cheminDe(l);
      row.append(vignette(p), nom);
      // t254 : le tracé de détourage (enregistré dans le PSD) est marqué ; clic droit = le menu des tracés pour ce tracé
      if (liste && liste.clippingPath && liste.clippingPath.name === l.cle) {
        const m = document.createElement("span"); m.className = "tra-detourage"; m.textContent = T("photolab.traces.detourage_marque"); row.appendChild(m);
      }
      row.addEventListener("contextmenu", (ev) => { ev.preventDefault(); choisi = l; cheminChoisi = p; dessiner(); redessiner(); ouvrirMenuCtx(ev.clientX, ev.clientY, l.cle); });
      row.addEventListener("click", () => { choisi = l; cheminChoisi = p; dessiner(); redessiner(); });
      row.addEventListener("dblclick", async () => {
        if (l.type === "calque") return;
        if (l.type === "travail") { await relireListe(); PL.executer("path.rename", { name: "work", to: nomLibre(liste, T("photolab.traces.base")) }); return; }
        const n = await demanderNom(PL, T("commun.action.renommer"), l.nom);
        if (n) PL.executer("path.rename", { name: l.cle, to: n });
      });
      frag.appendChild(row);
    }
    if (n !== jeton) return;
    zone.replaceChildren(frag);
    if (choisi && !lignesTraces(liste).some((x) => x.cle === choisi.cle)) { choisi = null; cheminChoisi = null; }
    const aTrace = !!(choisi || (liste && liste.workPath));
    bRemplir.disabled = bContour.disabled = bSelection.disabled = !aTrace;
    bDepuisSel.disabled = !d.hasSelection;
    bSuppr.disabled = !choisi || choisi.type === "calque";
  }
  PL.surDoc.push(() => { revLue = null; if (corps.offsetParent || PL.etat.outil === "pathSelection") dessiner(); });
  PL.traces = { dessiner, liste: () => liste, noeuds: () => noeuds, choisi: () => choisi,
    // t254 : état des outils d'ancre (bancs, preuve) et tracés où l'outil Texte peut poser un texte (forme active, travail)
    ancres: () => ({ cible: ds.cible, ancres: ds.ancres, segment: ds.segment }), courbe: () => courbe,
    async cheminsTexte() {
      await relireListe();
      const d = PL.etat.doc, out = [];
      if (cheminCalque && d) out.push({ path: cheminCalque, shape: d.activeLayer });
      if (cheminTravail) out.push({ path: cheminTravail });
      return out;
    },
    menu: (x, y) => ouvrirMenuCtx(x, y) };

  // Barre d'options de la plume : mode Tracé / Forme.
  PL.barresOutils = PL.barresOutils || {};
  PL.barresOutils.pen = (barre) => {
    const w = document.createElement("label"); w.className = "opt fo-champ";
    const s = document.createElement("span"); s.textContent = T("photolab.plume.mode");
    const sel = document.createElement("select");
    for (const v of MODES_PLUME) { const o = document.createElement("option"); o.value = v; o.textContent = T(v === "trace" ? "photolab.plume.mode_trace" : "photolab.plume.mode_forme"); sel.appendChild(o); }
    sel.value = PL.etat.plume.mode; sel.addEventListener("change", () => { PL.etat.plume.mode = sel.value; });
    const aide = document.createElement("span"); aide.className = "opt-aide"; aide.textContent = T("photolab.plume.aide");
    w.append(s, sel); barre.append(w, aide);
  };
  // t254 : barres des nouvelles plumes et des outils d'ancre — la Plume libre et la Plume de courbure gardent le mode
  // Tracé / Forme de la Plume (un seul réglage, comme l'amont) ; la Plume libre a son Ajustement de courbe.
  const aide = (barre, cle) => { const a = document.createElement("span"); a.className = "opt-aide"; a.textContent = T(cle); barre.appendChild(a); };
  const choixMode = (barre) => {
    const w = document.createElement("label"); w.className = "opt fo-champ";
    const s = document.createElement("span"); s.textContent = T("photolab.plume.mode");
    const sel = document.createElement("select");
    for (const v of MODES_PLUME) { const o = document.createElement("option"); o.value = v; o.textContent = T(v === "trace" ? "photolab.plume.mode_trace" : "photolab.plume.mode_forme"); sel.appendChild(o); }
    sel.value = PL.etat.plume.mode; sel.addEventListener("change", () => { PL.etat.plume.mode = sel.value; });
    w.append(s, sel); barre.appendChild(w);
  };
  PL.barresOutils.freeformPen = (barre) => {
    choixMode(barre);
    const w = document.createElement("label"); w.className = "opt fo-champ";
    const s = document.createElement("span"); s.textContent = T("photolab.plume.ajustement");
    const n = Object.assign(document.createElement("input"), { type: "number", min: AJUSTEMENT.min, max: AJUSTEMENT.max, step: 0.5, value: PL.etat.plume.ajustement, className: "pl-ajustement" });
    n.addEventListener("change", () => { const v = Math.min(AJUSTEMENT.max, Math.max(AJUSTEMENT.min, Number(n.value) || AJUSTEMENT.defaut)); n.value = v; PL.etat.plume.ajustement = v; });
    w.append(s, n); barre.appendChild(w);
    barre.insertAdjacentHTML("beforeend", '<span class="opt-unite">px</span>');
    aide(barre, "photolab.plume_libre.aide");
  };
  PL.barresOutils.curvaturePen = (barre) => { choixMode(barre); aide(barre, "photolab.plume_courbure.aide"); };
  PL.barresOutils.directSelection = (barre) => aide(barre, "photolab.selection_directe.aide");
  PL.barresOutils.convertPoint = (barre) => aide(barre, "photolab.conversion_point.aide");
  PL.barresOutils.addAnchorPoint = (barre) => aide(barre, "photolab.ajout_ancre.aide");
  PL.barresOutils.deleteAnchorPoint = (barre) => aide(barre, "photolab.suppression_ancre.aide");
  PL.barresOutils.pathSelection = (barre) => {
    const aide = document.createElement("span"); aide.className = "opt-aide"; aide.textContent = T("photolab.selection_trace.aide"); barre.appendChild(aide);
  };
}
