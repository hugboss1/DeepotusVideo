// mod-deformer.js — lot D3 « Déformer » (spec 2026-11-08-illustrator-vectorlab-inventaire.md, plan
// 2026-11-08-vectorlab-d3-deformer.md) : les DÉFORMATIONS VIVANTES d'Illustrator.
//
// Une déformation est un GROUPE qui porte sa recette : { deformation: { effet, params, edition?, empreinte },
// enfants: [source, ...résultat] }. La source reste l'objet d'origine, intacte mais CACHÉE (`cache: true`, que le rendu
// et les booléens sautent) ; le résultat est fait de chemins générés (`genere: true`, ids `<groupe>_d<k>`) en
// coordonnées du document, stockés comme les copies de D2. « Modifier le contenu » montre la source et cache le
// résultat ; le recalcul suit l'empreinte (source et réglages) après chaque commande (deformations_rafraichir, appelé
// par vivants_d2_rafraichir de mod-repeter.js). Règle de mod-bool : tout se CALCULE avant de muter.
import { T } from "./mod-i18n.js";
import { polylignes_objet } from "./mod-bool.js";

const EFFETS = new Set(["enveloppe"]);
const PAS_MAX = 2;                    // aucun segment déformé ne dépasse 2 px : une droite peut se courber
const POINTS_MAX = 20000;
const nbc = (x) => String(Math.round(x * 100) / 100 + 0);
const _cloner = (o) => JSON.parse(JSON.stringify(o));

export const STYLES_ENVELOPPE = ["arc", "arc_bas", "arc_haut", "arche", "renflement", "coquille_bas", "coquille_haut",
  "drapeau", "vague", "poisson", "montee", "oeil", "gonflement", "pression", "torsion"];

/* ── réglages ── */
function _nombre(v, defaut, min, max, cle) {
  const n = Number(v === undefined ? defaut : v);
  if (!Number.isFinite(n) || n < min || n > max) throw new Error(T(cle, { min, max }));
  return n;
}
function _params(effet, p = {}, base = {}) {
  const v = { ...base, ...p };
  if (effet === "enveloppe") {
    const style = v.style === undefined ? "arc" : v.style;
    if (!STYLES_ENVELOPPE.includes(style)) throw new Error(T("vectorlab.deformer.style", { style }));
    const orientation = v.orientation === undefined ? "horizontale" : v.orientation;
    if (orientation !== "horizontale" && orientation !== "verticale") throw new Error(T("vectorlab.deformer.orientation"));
    return {
      style, orientation,
      courbure: _nombre(v.courbure, 50, -100, 100, "vectorlab.deformer.pourcent"),
      distH: _nombre(v.distH, 0, -100, 100, "vectorlab.deformer.pourcent"),
      distV: _nombre(v.distV, 0, -100, 100, "vectorlab.deformer.pourcent"),
    };
  }
  throw new Error(T("vectorlab.deformer.effet", { effet }));
}

/* ── la géométrie de la source : ses feuilles (style + polylignes, transforms des groupes compris) ── */
function _feuilles(o, parents = []) {
  if (o.type === "groupe") return (o.enfants || []).flatMap((e) => _feuilles(e, [...parents, o]));
  let objet = o;
  for (let i = parents.length - 1; i >= 0; i--) objet = { type: "groupe", transform: parents[i].transform, enfants: [objet] };
  let lignes;
  try { lignes = polylignes_objet(objet).filter((l) => l.points.length >= 2); } catch (e) { return []; }
  return lignes.length ? [{ style: o.style || {}, lignes }] : [];
}
function _boite(feuilles) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const f of feuilles) for (const l of f.lignes) for (const [x, y] of l.points) {
    if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
  }
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}
// chaque segment découpé en pas de PAS_MAX px au plus (fermeture comprise)
function _subdiviser(l, pas) {
  const q = l.ferme ? l.points.concat([l.points[0]]) : l.points;
  const out = [q[0]];
  for (let i = 1; i < q.length; i++) {
    const [ax, ay] = q[i - 1], [bx, by] = q[i];
    const n = Math.max(1, Math.ceil(Math.hypot(bx - ax, by - ay) / pas));
    for (let k = 1; k <= n; k++) out.push([ax + (bx - ax) * k / n, ay + (by - ay) * k / n]);
  }
  if (l.ferme) out.pop();
  return out;
}

/* ── l'Enveloppe : u, v ∈ [0, 1] dans la boîte, s = 2u − 1, t = 2v − 1, b = courbure (−1..1) ──
   chaque style rend le déplacement [dx, dy] d'un point ; les coins restent en place sauf montée, drapeau et vague */
const _ENV = {
  arc: (P) => [0, -P.b * P.H / 2 * (1 - P.s * P.s)],
  arc_bas: (P) => [0, P.b * P.H / 2 * (1 - P.s * P.s) * P.v],
  arc_haut: (P) => [0, -P.b * P.H / 2 * (1 - P.s * P.s) * (1 - P.v)],
  arche: (P) => [-(P.x - P.cx) * P.b * 0.25 * (1 - P.v), -P.b * P.H / 2 * (1 - P.s * P.s) * (1 - P.v)],
  renflement: (P) => [0, P.b * P.H / 2 * (1 - P.s * P.s) * P.t],
  coquille_bas: (P) => [-(P.x - P.cx) * P.b * 0.25 * P.v, P.b * P.H / 2 * (1 - Math.abs(P.s)) * P.v],
  coquille_haut: (P) => [-(P.x - P.cx) * P.b * 0.25 * (1 - P.v), -P.b * P.H / 2 * (1 - Math.abs(P.s)) * (1 - P.v)],
  drapeau: (P) => [0, -P.b * P.H / 4 * Math.sin(2 * Math.PI * P.u)],
  vague: (P) => [0, -P.b * P.H / 4 * Math.sin(2 * Math.PI * P.u) * -P.t],
  poisson: (P) => [0, (P.y - P.cy) * P.b * (0.5 * Math.sin(Math.PI * P.u) - 0.5 * P.u)],
  montee: (P) => [0, -P.b * P.H / 2 * Math.sin(Math.PI / 2 * P.s)],
  oeil: (P) => { const f = P.b * 0.5 * Math.max(0, 1 - (P.s * P.s + P.t * P.t) / 2); return [(P.x - P.cx) * f, (P.y - P.cy) * f]; },
  gonflement: (P) => [(P.x - P.cx) * P.b * 0.5 * (1 - P.t * P.t), (P.y - P.cy) * P.b * 0.5 * (1 - P.s * P.s)],
  pression: (P) => [-(P.x - P.cx) * P.b * 0.5 * (1 - P.t * P.t), (P.y - P.cy) * P.b * 0.5 * (1 - P.s * P.s)],
  torsion: (P) => {
    const a = P.b * Math.PI / 2 * Math.max(0, 1 - Math.hypot(P.s, P.t) / Math.SQRT2);
    const x = P.x - P.cx, y = P.y - P.cy;
    return [x * Math.cos(a) - y * Math.sin(a) - x, x * Math.sin(a) + y * Math.cos(a) - y];
  },
};
function _enveloppe(p, B) {
  const vert = p.orientation === "verticale";
  // en orientation verticale, le même calcul sur la boîte transposée (x ↔ y)
  const W = vert ? B.h : B.w, H = vert ? B.w : B.h, x0 = vert ? B.y : B.x, y0 = vert ? B.x : B.y;
  const cx = x0 + W / 2, cy = y0 + H / 2, b = p.courbure / 100, dh = p.distH / 100, dv = p.distV / 100, f = _ENV[p.style];
  return ([X, Y]) => {
    const x = vert ? Y : X, y = vert ? X : Y;
    const u = W > 0 ? (x - x0) / W : 0.5, v = H > 0 ? (y - y0) / H : 0.5;
    const [ddx, ddy] = f({ x, y, u, v, s: 2 * u - 1, t: 2 * v - 1, b, W, H, cx, cy });
    let nx = x + ddx, ny = y + ddy;
    // distorsions : la hauteur varie de gauche à droite (H), la largeur de haut en bas (V) — un trapèze
    ny = cy + (ny - cy) * (1 + dh * (u - 0.5));
    nx = cx + (nx - cx) * (1 + dv * (v - 0.5));
    return vert ? [ny, nx] : [nx, ny];
  };
}
const _TRANSFORMEES = { enveloppe: _enveloppe };

/* ── le résultat ── */
function _resultat(gid, source, effet, params, cache) {
  const F = _feuilles(source);
  if (!F.length) throw new Error(T("vectorlab.deformer.sans_geometrie"));
  const B = _boite(F);
  // le pas grandit sur un très grand dessin, pour rester sous POINTS_MAX points
  const pas = Math.max(PAS_MAX, (2 * (B.w + B.h) * F.length) / POINTS_MAX);
  const tr = _TRANSFORMEES[effet](params, B);
  return F.map((f, k) => {
    const d = f.lignes.map((l) => {
      const q = _subdiviser(l, pas).map(tr);
      if (q.some(([x, y]) => !Number.isFinite(x) || !Number.isFinite(y))) throw new Error(T("vectorlab.deformer.sans_geometrie"));
      return "M" + q.map(([x, y]) => `${nbc(x)} ${nbc(y)}`).join(" L") + (l.ferme ? " Z" : "");
    }).join(" ");
    const r = { id: `${gid}_d${k + 1}`, type: "path", d, style: _cloner(f.style), genere: true };
    if (cache) r.cache = true;
    return r;
  });
}
const _empreinte = (g) => JSON.stringify([g.enfants[0], g.deformation.effet, g.deformation.params]);
function _reconstruire(g) {
  const source = g.enfants[0];
  g.enfants = [source, ..._resultat(g.id, source, g.deformation.effet, g.deformation.params, !!g.deformation.edition)];
  g.deformation.empreinte = _empreinte(g);
}
function _rejouer(g, changer) {
  const essai = { ...g, enfants: g.enfants.map(_cloner), deformation: { ...g.deformation } };
  changer(essai);
  _reconstruire(essai);
  g.enfants = essai.enfants;
  g.deformation = essai.deformation;
}

/* ── chercher, ids ── */
function _trouver(doc, id) {
  for (const c of doc.calques) {
    const r = (function v(objs, parent) {
      for (const o of objs || []) {
        if (o.id === id) return { objet: o, calque: c, parent };
        if (o.type === "groupe") { const x = v(o.enfants, o); if (x) return x; }
      }
      return null;
    })(c.objets, null);
    if (r) return r;
  }
  return null;
}
function _neuf(doc) {
  const pris = new Set();
  const v = (objs) => { for (const o of objs || []) { pris.add(o.id); if (o.type === "groupe") v(o.enfants); } };
  for (const c of doc.calques) v(c.objets);
  for (const s of Object.values(doc.symboles || {})) v(s.objets);
  let n = 1;
  return () => { while (pris.has("o" + n)) n++; pris.add("o" + n); return "o" + n; };
}
function _deformation(doc, id) {
  const t = _trouver(doc, id);
  if (!t) throw new Error(T("vectorlab.deformer.introuvable", { id }));
  if (!t.objet.deformation) throw new Error(T("vectorlab.deformer.pas_deformation", { id }));
  return t;
}

/* ══ T1 (t460) Objet › Déformer ══
   La sélection (objets du premier niveau d'un calque déverrouillé ; plusieurs sont d'abord groupés) devient la
   source ; le groupe vivant prend la place du plus haut. -> id du groupe */
export function op_deformer(doc, ids, effet, params = {}) {
  if (!EFFETS.has(effet)) throw new Error(T("vectorlab.deformer.effet", { effet }));
  const voulu = new Set(ids || []);
  if (!voulu.size) throw new Error(T("vectorlab.deformer.rien"));
  const cibles = [];
  for (const c of doc.calques) for (const o of c.objets) if (voulu.has(o.id)) cibles.push({ calque: c, objet: o });
  if (cibles.length !== voulu.size) {
    const genere = [...voulu].some((id) => { const t = _trouver(doc, id); return t && t.objet.genere; });
    throw new Error(T(genere ? "vectorlab.repeter.copie_generee" : "vectorlab.deformer.rien"));
  }
  if (cibles.some((t) => t.calque.verrou)) throw new Error(T("vectorlab.repeter.verrou"));
  const p = _params(effet, params);
  const neuf = _neuf(doc);
  const objs = cibles.map((t) => t.objet);
  const source = objs.length === 1 ? _cloner(objs[0]) : { id: neuf(), type: "groupe", style: {}, enfants: _cloner(objs) };
  source.cache = true;
  const g = { id: neuf(), type: "groupe", style: {}, deformation: { effet, params: p, empreinte: "" }, enfants: [source] };
  _reconstruire(g);                                  // tout se calcule AVANT de muter
  const haut = cibles[cibles.length - 1];
  haut.calque.objets.splice(haut.calque.objets.indexOf(haut.objet), 1, g);
  for (const t of cibles.slice(0, -1)) t.calque.objets.splice(t.calque.objets.indexOf(t.objet), 1);
  return g.id;
}

// Options de déformation : les réglages fournis remplacent les anciens, les autres restent
export function op_deformation_regler(doc, id, params = {}) {
  const g = _deformation(doc, id).objet;
  const p = _params(g.deformation.effet, params, g.deformation.params);
  _rejouer(g, (e) => { e.deformation.params = p; });
}

// Modifier le contenu : la source visible et le résultat caché ; encore une fois : l'inverse, recalculé
export function op_deformation_editer(doc, id) {
  const g = _deformation(doc, id).objet;
  _rejouer(g, (e) => {
    e.deformation.edition = !e.deformation.edition;
    if (e.deformation.edition) delete e.enfants[0].cache; else e.enfants[0].cache = true;
    if (!e.deformation.edition) delete e.deformation.edition;
  });
}

// Annuler la déformation : la source seule revient à la place du groupe, visible
export function op_deformation_annuler(doc, id) {
  const t = _deformation(doc, id);
  const liste = t.parent ? t.parent.enfants : t.calque.objets;
  if (!t.parent && t.calque.verrou) throw new Error(T("vectorlab.repeter.verrou"));
  const source = _cloner(t.objet.enfants[0]);
  delete source.cache;
  liste.splice(liste.indexOf(t.objet), 1, source);
  return source.id;
}

/* ── vivant : appelé par vivants_d2_rafraichir (mod-repeter.js), donc par derives_rafraichir ── */
export function deformations_rafraichir(doc) {
  let n = 0;
  const v = (objs) => {
    for (const o of objs || []) {
      if (o.type !== "groupe") continue;
      v(o.enfants);
      if (!o.deformation || !Array.isArray(o.enfants) || !o.enfants.length) continue;
      if (o.enfants[0].genere) continue;                       // la source a disparu : dernier état gardé
      if (_empreinte(o) === o.deformation.empreinte) continue;
      try { _rejouer(o, () => {}); n++; } catch (e) { /* recalcul impossible : dernier état gardé */ }
    }
  };
  for (const c of doc.calques) v(c.objets);
  return n;
}
