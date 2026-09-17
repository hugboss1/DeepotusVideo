// mod-noeuds.js — les NŒUDS MULTIPLES du lot B : déplacer, aligner,
// transformer plusieurs ancres à la fois, diviser un segment (de Casteljau),
// inverser le sens d'un chemin, joindre deux chemins ouverts, arrondir les
// coins (Q tangent), choisir des ancres au rectangle. Sur le d canonique de
// mod-doc (chemin_parser / chemin_serialiser). PUR.
import { chemin_parser, chemin_serialiser, chemin_ancres } from "./mod-doc.js";

function _path(doc, id) {
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const o = c.objets.find((x) => x.id === id);
    if (o) {
      if (o.type !== "path") throw new Error(`objet ${id}: pas un chemin`);
      return { calque: c, objet: o };
    }
  }
  throw new Error(`chemin introuvable (ou calque verrouillé): ${id}`);
}
const _porteurs = (segs) => segs.map((s, k) => (s.c === "Z" ? -1 : k)).filter((k) => k >= 0);
const _fin = (s) => [s.p[s.p.length - 2], s.p[s.p.length - 1]];
function _indices(list, n) {
  const out = [...new Set(list.map((i) => +i))];
  for (const i of out) if (!(Number.isInteger(i) && i >= 0 && i < n)) throw new Error(`ancre ${i} hors chemin`);
  return out;
}
function _decalerAncre(segs, noeuds, i, dx, dy) {
  const s = segs[noeuds[i]];
  s.p[s.p.length - 2] += dx; s.p[s.p.length - 1] += dy;
  if (s.c === "C") { s.p[2] += dx; s.p[3] += dy; }
  if (s.c === "Q") { s.p[0] += dx; s.p[1] += dy; }
  const kn = noeuds[i + 1];
  if (kn !== undefined && segs[kn].c === "C") { segs[kn].p[0] += dx; segs[kn].p[1] += dy; }
}

export function op_noeuds_deplacer(doc, id, indices, dx, dy) {
  const { objet } = _path(doc, id);
  const segs = chemin_parser(objet.d), noeuds = _porteurs(segs);
  for (const i of _indices(indices, noeuds.length)) _decalerAncre(segs, noeuds, i, dx, dy);
  objet.d = chemin_serialiser(segs);
}

const _MODES = { gauche: ["x", "min"], centreH: ["x", "moy"], droite: ["x", "max"],
                 haut: ["y", "min"], centreV: ["y", "moy"], bas: ["y", "max"] };
export function op_noeuds_aligner(doc, id, indices, mode) {
  if (!_MODES[mode]) throw new Error(`aligner : mode inconnu ${mode}`);
  const { objet } = _path(doc, id);
  const segs = chemin_parser(objet.d), noeuds = _porteurs(segs);
  const idx = _indices(indices, noeuds.length);
  if (idx.length < 2) throw new Error("aligner : deux ancres au moins");
  const [axe, agg] = _MODES[mode];
  const vals = idx.map((i) => _fin(segs[noeuds[i]])[axe === "x" ? 0 : 1]);
  const cible = agg === "min" ? Math.min(...vals) : agg === "max" ? Math.max(...vals)
              : vals.reduce((s, v) => s + v, 0) / vals.length;
  idx.forEach((i, k) => {
    const d = cible - vals[k];
    if (d) _decalerAncre(segs, noeuds, i, axe === "x" ? d : 0, axe === "x" ? 0 : d);
  });
  objet.d = chemin_serialiser(segs);
}

export function op_noeuds_transformer(doc, id, indices, av, ap) {
  if (!(av.w > 0) || !(av.h > 0)) throw new Error("transformer : boîte de départ vide");
  const { objet } = _path(doc, id);
  const segs = chemin_parser(objet.d), noeuds = _porteurs(segs);
  const idx = _indices(indices, noeuds.length);
  const fx = (X) => (X - av.x) * (ap.w / av.w) + ap.x, fy = (Y) => (Y - av.y) * (ap.h / av.h) + ap.y;
  for (const i of idx) {
    const s = segs[noeuds[i]];
    // l'ancre et sa poignée entrante, puis la poignée sortante du segment suivant
    for (let k = s.c === "C" ? 2 : 0; k < s.p.length; k += 2) { s.p[k] = fx(s.p[k]); s.p[k + 1] = fy(s.p[k + 1]); }
    const kn = noeuds[i + 1];
    if (kn !== undefined && segs[kn].c === "C") { segs[kn].p[0] = fx(segs[kn].p[0]); segs[kn].p[1] = fy(segs[kn].p[1]); }
  }
  objet.d = chemin_serialiser(segs);
}

// diviser le segment qui MÈNE à l'ancre i (i ≥ 1) au paramètre t
export function op_noeud_inserer(doc, id, i, t = 0.5) {
  const { objet } = _path(doc, id);
  const segs = chemin_parser(objet.d), noeuds = _porteurs(segs);
  if (!(Number.isInteger(i) && i >= 1 && i < noeuds.length)) throw new Error("diviser : choisir une ancre après la première");
  const k = noeuds[i], s = segs[k];
  const [x0, y0] = _fin(segs[noeuds[i - 1]]);
  const u = Math.min(0.95, Math.max(0.05, +t || 0.5));
  const L = (a, b) => a + (b - a) * u;
  if (s.c === "L") {
    segs.splice(k, 0, { c: "L", p: [L(x0, s.p[0]), L(y0, s.p[1])] });
  } else if (s.c === "C") {
    const [x1, y1, x2, y2, x3, y3] = s.p;
    const ax = L(x0, x1), ay = L(y0, y1), bx = L(x1, x2), by = L(y1, y2), cx = L(x2, x3), cy = L(y2, y3);
    const dx = L(ax, bx), dy = L(ay, by), ex = L(bx, cx), ey = L(by, cy), mx = L(dx, ex), my = L(dy, ey);
    segs.splice(k, 1, { c: "C", p: [ax, ay, dx, dy, mx, my] }, { c: "C", p: [ex, ey, cx, cy, x3, y3] });
  } else if (s.c === "Q") {
    const [x1, y1, x2, y2] = s.p;
    const ax = L(x0, x1), ay = L(y0, y1), bx = L(x1, x2), by = L(y1, y2), mx = L(ax, bx), my = L(ay, by);
    segs.splice(k, 1, { c: "Q", p: [ax, ay, mx, my] }, { c: "Q", p: [bx, by, x2, y2] });
  } else throw new Error("diviser : segment non divisible");
  objet.d = chemin_serialiser(segs);
  return i;
}

export function op_chemin_inverser(doc, id) {
  const { objet } = _path(doc, id);
  const segs = chemin_parser(objet.d), noeuds = _porteurs(segs);
  const ferme = segs.some((s) => s.c === "Z");
  const out = [{ c: "M", p: _fin(segs[noeuds[noeuds.length - 1]]) }];
  for (let i = noeuds.length - 1; i >= 1; i--) {
    const s = segs[noeuds[i]], prev = _fin(segs[noeuds[i - 1]]);
    if (s.c === "L") out.push({ c: "L", p: prev });
    else if (s.c === "C") out.push({ c: "C", p: [s.p[2], s.p[3], s.p[0], s.p[1], prev[0], prev[1]] });
    else if (s.c === "Q") out.push({ c: "Q", p: [s.p[0], s.p[1], prev[0], prev[1]] });
  }
  if (ferme) out.push({ c: "Z", p: [] });
  objet.d = chemin_serialiser(out);
}

export function op_chemins_joindre(doc, idA, idB) {
  const a = _path(doc, idA), b = _path(doc, idB);
  const sa = chemin_parser(a.objet.d), sb = chemin_parser(b.objet.d);
  if (sa.some((s) => s.c === "Z") || sb.some((s) => s.c === "Z")) throw new Error("joindre : les deux chemins doivent être ouverts");
  if (!sb.length || sb[0].c !== "M") throw new Error("joindre : chemin B sans départ");
  sa.push({ c: "L", p: sb[0].p.slice() }, ...sb.slice(1));
  a.objet.d = chemin_serialiser(sa);
  b.calque.objets.splice(b.calque.objets.indexOf(b.objet), 1);
  return idA;
}

// coins arrondis : entre deux segments DROITS, l'ancre devient Q tangent
export function op_coins_arrondir(doc, ids, rayon) {
  const r = +rayon;
  if (!(r > 0)) throw new Error("coins : rayon > 0 requis");
  let n = 0;
  for (const id of ids) {
    let cible;
    try { cible = _path(doc, id); } catch { continue; }
    const segs = chemin_parser(cible.objet.d), noeuds = _porteurs(segs);
    const ferme = segs.some((s) => s.c === "Z");
    const P = noeuds.map((k) => _fin(segs[k]));
    const droit = (k) => k !== undefined && (segs[k].c === "L" || segs[k].c === "M");
    const nA = P.length;
    if (nA < 3) continue;
    const coin = (i) => {                    // le coin en i est-il entre deux droites ?
      const prev = i > 0 ? i - 1 : (ferme ? nA - 1 : -1), next = i < nA - 1 ? i + 1 : (ferme ? 0 : -1);
      if (prev < 0 || next < 0) return null;
      if (!droit(noeuds[i]) || !droit(noeuds[next])) return null;
      const p = P[i], a = P[prev], b = P[next];
      const la = Math.hypot(a[0] - p[0], a[1] - p[1]), lb = Math.hypot(b[0] - p[0], b[1] - p[1]);
      if (la < 1e-9 || lb < 1e-9) return null;
      const d1 = Math.min(r, la / 2), d2 = Math.min(r, lb / 2);
      return { A: [p[0] + (a[0] - p[0]) / la * d1, p[1] + (a[1] - p[1]) / la * d1],
               B: [p[0] + (b[0] - p[0]) / lb * d2, p[1] + (b[1] - p[1]) / lb * d2], p };
    };
    const coins = P.map((_, i) => coin(i));
    if (!coins.some(Boolean)) continue;
    const out = [];
    const debut = ferme && coins[0] ? coins[0].B : P[0];
    out.push({ c: "M", p: debut.slice() });
    const ordre = ferme ? [...Array(nA - 1).keys()].map((i) => i + 1).concat([0]) : [...Array(nA - 1).keys()].map((i) => i + 1);
    for (const i of ordre) {
      const c = coins[i];
      if (c) { out.push({ c: "L", p: c.A }, { c: "Q", p: [c.p[0], c.p[1], c.B[0], c.B[1]] }); n++; }
      else if (!(ferme && i === 0)) out.push({ c: "L", p: P[i].slice() });
    }
    if (ferme) out.push({ c: "Z", p: [] });
    cible.objet.d = chemin_serialiser(out);
  }
  return n;
}

export function ancres_dans_rect(segs, rect) {
  return chemin_ancres(segs).filter((a) => a.x >= rect.x && a.x <= rect.x + rect.w
    && a.y >= rect.y && a.y <= rect.y + rect.h).map((a) => a.i);
}
