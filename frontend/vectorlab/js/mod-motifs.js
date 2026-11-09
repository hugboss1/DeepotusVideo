// mod-motifs.js — lot D5 « Couleur et motif », T4 (t478 ; plan 2026-11-09-vectorlab-d5-couleur-motif.md) : les motifs
// FAITS D'OBJETS, à côté des quatre motifs paramétriques de mod-effets.js.
//
// MODÈLE. doc.motifs[id] = { type: "objets", pavage, largeur, hauteur, espacement: { h, v }, objets, fond? } : les objets
// sont en coordonnées de la tuile (0, 0) – (largeur, hauteur). Le pas vaut la tuile plus l'espacement (négatif =
// chevauchement). Pavages :
//   * grille ;
//   * brique_lignes (une rangée sur deux décalée d'une demi-tuile) ;
//   * brique_colonnes (une colonne sur deux) ;
//   * hexagone (rangées décalées, au pas de 3/4 de la tuile).
// CELLULE. Le pavage est périodique ; sa cellule (une ou deux rangées / colonnes) reçoit toutes les copies qui la
// touchent : le SVG (<pattern>) et le PDF (PatternType 1) répètent la même cellule. Un motif employé DANS un motif est
// émis aussi (motifs_fermeture) ; un motif qui se contiendrait est refusé (motifs_cycle).
// Pas d'effet, de masque ni d'écrêtage dans un motif : leurs définitions ne suivent pas les copies d'une cellule.
import { T } from "./mod-i18n.js";
import { polylignes_objet } from "./mod-bool.js";

export const PAVAGES = ["grille", "brique_lignes", "brique_colonnes", "hexagone"];
const TYPES = new Set(["rect", "ellipse", "path", "forme", "texte", "groupe"]);
const RECETTES = ["repetition", "fusion_vive", "deformation", "pinceau", "derive"];
const OBJETS_MAX = 2000;
const nb = (x) => String(Math.round(x * 1e4) / 1e4 + 0);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const _num = (v) => (typeof v === "number" ? v : Number(v));
// un objet illisible dans un motif (données écrites à la main) est sauté : il ne casse pas le rendu du document
const _sur = (f, repli = "") => { try { return f(); } catch { return repli; } };

/* ── validation ── */
export function motif_objets_valider(m) {
  if (!m || m.type !== "objets" || !PAVAGES.includes(m.pavage)) throw new Error(T("vectorlab.motifs.pavage", { pavage: m && m.pavage }));
  const l = _num(m.largeur), h = _num(m.hauteur);
  if (!(l >= 0.5 && l <= 10000 && h >= 0.5 && h <= 10000)) throw new Error(T("vectorlab.motifs.taille"));
  const e = m.espacement || {}, eh = _num(e.h ?? 0), ev = _num(e.v ?? 0);
  const pasV = (m.pavage === "hexagone" ? h * 0.75 : h) + ev;
  if (!(Number.isFinite(eh) && Number.isFinite(ev) && eh <= 10000 && ev <= 10000 && l + eh >= 0.5 && pasV >= 0.5)) throw new Error(T("vectorlab.motifs.espacement"));
  if (!Array.isArray(m.objets) || !m.objets.length) throw new Error(T("vectorlab.motifs.vide"));
  let n = 0;
  const visiter = (o) => {
    if (!o || !TYPES.has(o.type)) throw new Error(T("vectorlab.motifs.type_objet", { type: o && o.type }));
    const s = o.style || {};
    if ((s.effets && s.effets.length) || s.masque || o.clip) throw new Error(T("vectorlab.motifs.effets"));
    if (++n > OBJETS_MAX) throw new Error(T("vectorlab.motifs.trop", { n: OBJETS_MAX }));
    if (o.type === "groupe") (o.enfants || []).forEach(visiter);
  };
  m.objets.forEach(visiter);
  if (m.fond !== undefined && m.fond !== "none" && !/^(#[0-9a-f]{3}|#[0-9a-f]{6}|glob:.+)$/i.test(String(m.fond))) {
    throw new Error(T("vectorlab.recolorer.couleur_invalide", { c: m.fond }));
  }
  return m;
}

/* ── la cellule périodique : { l, h, copies: [[x, y]] } (coins hauts-gauches des tuiles qui touchent la cellule) ── */
export function motif_objets_cellule(m) {
  const L = +m.largeur, H = +m.hauteur, e = m.espacement || {};
  const W = L + (+e.h || 0);
  const pasV = (m.pavage === "hexagone" ? H * 0.75 : H) + (+e.v || 0);
  const lignes = m.pavage === "brique_lignes" || m.pavage === "hexagone", colonnes = m.pavage === "brique_colonnes";
  const l = colonnes ? 2 * W : W, h = lignes ? 2 * pasV : pasV;
  const copies = [];
  const ni = Math.ceil(L / W) + 2, nj = Math.ceil(H / pasV) + 2;
  for (let j = -nj; j <= Math.ceil(h / pasV) + 1; j++) {
    for (let i = -ni; i <= Math.ceil(l / W) + 1; i++) {
      const x = i * W + (lignes && j % 2 ? W / 2 : 0), y = j * pasV + (colonnes && i % 2 ? pasV / 2 : 0);
      if (x + L > 0 && x < l && y + H > 0 && y < h) copies.push([x, y]);
    }
  }
  return { l, h, copies };
}

/* ── SVG : rendre(o) → SVG d'un objet (sans id), couleur(v) → couleur résolue (globales) ── */
export function motif_objets_svg(id, m, rendre, couleur = (c) => c) {
  const { l, h, copies } = motif_objets_cellule(m);
  const corps = m.objets.map((o) => _sur(() => rendre(o))).join("");
  const f = m.fond && m.fond !== "none" ? couleur(m.fond) : null;
  const fond = f && f !== "none" ? `<rect x="0" y="0" width="${nb(l)}" height="${nb(h)}" fill="${esc(f)}"/>` : "";
  return `<pattern id="${esc(id)}" patternUnits="userSpaceOnUse" width="${nb(l)}" height="${nb(h)}">${fond}`
    + copies.map(([x, y]) => `<g transform="translate(${nb(x)} ${nb(y)})">${corps}</g>`).join("") + `</pattern>`;
}

/* ── les références portées par les objets d'un motif ── */
function _refs(m) {
  const motifs = [], degrades = [];
  const visiter = (o) => {
    for (const v of [o.style && o.style.fond, o.style && o.style.contour]) {
      if (typeof v !== "string") continue;
      if (v.startsWith("motif:")) motifs.push(v.slice(6));
      else if (v.startsWith("grad:")) degrades.push(v.slice(5));
    }
    if (o.type === "groupe") (o.enfants || []).forEach(visiter);
  };
  if (m && m.type === "objets") (m.objets || []).forEach(visiter);
  return { motifs, degrades };
}
// ajoute aux listes de _defs (mod-doc) les motifs et dégradés employés DANS les motifs d'objets, transitivement
export function motifs_fermeture(doc, motifs, refs) {
  const mots = doc.motifs || {};
  for (let k = 0; k < motifs.length; k++) {
    const r = _refs(mots[motifs[k]]);
    for (const id of r.motifs) if (!motifs.includes(id)) motifs.push(id);
    for (const id of r.degrades) if (!refs.includes(id)) refs.push(id);
  }
}
export function motifs_cycle(motifs) {
  const etat = new Map();                                     // 1 = en cours, 2 = fini
  const visiter = (id, depart) => {
    if (etat.get(id) === 2) return;
    if (etat.get(id) === 1) throw new Error(T("vectorlab.motifs.cycle", { id: depart }));
    etat.set(id, 1);
    for (const r of _refs((motifs || {})[id]).motifs) if ((motifs || {})[r]) visiter(r, depart);
    etat.set(id, 2);
  };
  for (const id of Object.keys(motifs || {})) visiter(id, id);
}

/* ── PDF (appelé par _motif de mod-pdf.js) : la cellule en motif de pavage, ses objets dessinés par _objet ── */
export function motif_objets_pdf(ctx, spec, { dessiner, raison, matrice_mul, matrice_inverse }) {
  const mat = matrice_mul(matrice_inverse(ctx.espace), ctx.ctm);
  const cle = JSON.stringify([spec, mat.map(nb)]);
  if (!ctx.patCles.has(cle)) {
    const nom = `P${ctx.patCles.size + 1}`;
    ctx.patCles.set(cle, nom);
    const { l, h, copies } = motif_objets_cellule(spec);
    const ID = [1, 0, 0, 1, 0, 0], sous = { ...ctx, ctm: ID, espace: ID };
    const L = [];
    if (spec.fond && spec.fond !== "none") L.push(dessiner({ id: "_fond", type: "rect", x: 0, y: 0, w: l, h, style: { fond: spec.fond } }, sous));
    const corps = spec.objets.filter((o) => !raison(o, sous)).map((o) => _sur(() => dessiner(o, sous))).filter(Boolean).join("\n");
    for (const [x, y] of copies) L.push(`q\n1 0 0 1 ${nb(x)} ${nb(y)} cm\n${corps}\nQ`);
    ctx.patterns[nom] = { contenu: L.join("\n"), bbox: [0, 0, l, h], pas: l, pasX: l, pasY: h, matrice: mat, ressources: true };
  }
  return ctx.patCles.get(cle);
}

/* ── les ops ── */
function _cibles(doc, ids) {
  const voulu = new Set(ids || []), out = [];
  const dans = (objs) => {
    for (const o of objs || []) {
      if (o.genere) continue;
      if (voulu.has(o.id) && !o.verrou) { out.push(o); continue; }
      if (o.type === "groupe") dans(o.enfants);
    }
  };
  for (const c of doc.calques || []) if (!c.verrou) dans(c.objets);
  return out;
}
function _nettoyer(o) {
  if (o.cache) return null;
  const c = { ...o };
  delete c.genere; delete c.clip;
  for (const k of RECETTES) delete c[k];
  if (c.style) { c.style = { ...c.style }; delete c.style.effets; delete c.style.masque; }
  if (Array.isArray(c.enfants)) c.enfants = c.enfants.map(_nettoyer).filter(Boolean);
  return JSON.parse(JSON.stringify(c));
}
function _boite(o) {
  try {
    const P = polylignes_objet(o).flatMap((l) => l.points);
    if (P.length) return [Math.min(...P.map((p) => p[0])), Math.min(...P.map((p) => p[1])), Math.max(...P.map((p) => p[0])), Math.max(...P.map((p) => p[1]))];
  } catch { /* texte : sa boîte approchée */ }
  if (o.type === "groupe") {
    const bs = (o.enfants || []).map(_boite).filter(Boolean);
    return bs.length ? [Math.min(...bs.map((b) => b[0])), Math.min(...bs.map((b) => b[1])), Math.max(...bs.map((b) => b[2])), Math.max(...bs.map((b) => b[3]))] : null;
  }
  if (o.type === "texte") {
    const c = +((o.style || {}).corps) || 16, n = String(o.contenu || "").length;
    return [+o.x || 0, (+o.y || 0) - c, (+o.x || 0) + n * c * 0.6, (+o.y || 0) + c * 0.2];
  }
  return null;
}
function _depuis(doc, ids) {
  const cibles = _cibles(doc, ids);
  if (!cibles.length) throw new Error(T("vectorlab.motifs.aucune_selection"));
  for (const o of cibles) if (!TYPES.has(o.type)) throw new Error(T("vectorlab.motifs.type_objet", { type: o.type }));
  const objets = cibles.map(_nettoyer).filter(Boolean);
  const bs = objets.map(_boite).filter(Boolean);
  if (!bs.length) throw new Error(T("vectorlab.motifs.vide"));
  const x0 = Math.min(...bs.map((b) => b[0])), y0 = Math.min(...bs.map((b) => b[1]));
  const x1 = Math.max(...bs.map((b) => b[2])), y1 = Math.max(...bs.map((b) => b[3]));
  for (const o of objets) o.transform = `translate(${nb(-x0)} ${nb(-y0)})` + (o.transform ? " " + o.transform : "");
  return { objets, largeur: Math.max(0.5, x1 - x0), hauteur: Math.max(0.5, y1 - y0), x0, y0 };
}
const _poser = (doc, id, m) => {
  motif_objets_valider(m);
  motifs_cycle({ ...(doc.motifs || {}), [id]: m });
  if (!doc.motifs) doc.motifs = {};
  doc.motifs[id] = m;
};

export function op_motif_depuis_selection(doc, ids, opts = {}) {
  const { x0, y0, ...c } = _depuis(doc, ids);
  const e = opts.espacement || {};
  const m = { type: "objets", pavage: opts.pavage || "grille", largeur: c.largeur, hauteur: c.hauteur,
    espacement: { h: +e.h || 0, v: +e.v || 0 }, objets: c.objets };
  if (opts.fond !== undefined) m.fond = opts.fond;
  let k = 1;
  while (("m" + k) in (doc.motifs || {})) k++;
  _poser(doc, "m" + k, m);
  return "m" + k;
}
function _motifObjets(doc, id) {
  const m = (doc.motifs || {})[id];
  if (!m) throw new Error(T("vectorlab.doc.motif_inconnu", { id }));
  if (m.type !== "objets") throw new Error(T("vectorlab.motifs.pas_objets"));
  return m;
}
export function op_motif_regler(doc, id, patch = {}) {
  const m = { ..._motifObjets(doc, id) };
  for (const k of ["pavage", "espacement", "fond"]) if (patch[k] !== undefined) m[k] = patch[k];
  _poser(doc, id, m);
}
export function op_motif_contenu(doc, id, ids) {
  const m = _motifObjets(doc, id);
  const { x0, y0, ...c } = _depuis(doc, ids);
  _poser(doc, id, { ...m, ...c });
}

/* ── T5 (t479) : l'aperçu en direct de « Créer un motif… » (sur une COPIE du document) : le motif, et un rectangle
   qu'il remplit, posé sur la sélection — 3 × 3 cellules, au moins la taille de la sélection ── */
export function motif_apercu(doc, ids, opts = {}) {
  const { x0, y0 } = _depuis(doc, ids);
  const id = op_motif_depuis_selection(doc, ids, opts);
  const m = doc.motifs[id], { l, h } = motif_objets_cellule(m);
  const calque = doc.calques.find((c) => !c.verrou) || doc.calques[0];
  calque.objets.push({ id: "_apercu_motif", type: "rect", x: x0, y: y0, w: Math.max(3 * l, m.largeur), h: Math.max(3 * h, m.hauteur), style: { fond: "motif:" + id, contour: "#1a202c", epaisseur: 1 } });
  return id;
}
// les motifs d'objets du document, dans l'ordre naturel des ids, avec le nombre d'objets qui les emploient en fond
export function motifs_objets_liste(doc) {
  const usages = new Map();
  const visiter = (objs) => {
    for (const o of objs || []) {
      const f = o.style && o.style.fond;
      if (typeof f === "string" && f.startsWith("motif:")) usages.set(f.slice(6), (usages.get(f.slice(6)) || 0) + 1);
      if (o.type === "groupe") visiter(o.enfants);
    }
  };
  for (const c of doc.calques || []) visiter(c.objets);
  return Object.entries(doc.motifs || {}).filter(([, m]) => m && m.type === "objets")
    .map(([id, m]) => ({ id, pavage: m.pavage, objets: (m.objets || []).length, usages: usages.get(id) || 0 }))
    .sort((a, b) => a.id.localeCompare(b.id, "fr", { numeric: true }));
}
