// mod-pinceaux.js — lot D5 « Couleur et motif », T6 (t480 ; plan 2026-11-09-vectorlab-d5-couleur-motif.md) : les
// pinceaux artistique, dispersion et motif d'Illustrator, VIVANTS.
//
// DÉFINITION. doc.pinceaux[id] = { nom, genre, objets, largeur, hauteur } : un dessin fait depuis une sélection, ramené
// à l'origine (ids pc<n>). TRACÉ PEINT. Un groupe { pinceau: { id, params, empreinte }, enfants: [source cachée,
// ...générés <groupe>_p<k>] }, sur le modèle des déformations de D3 : la source reste intacte mais cachée (le rendu et
// les booléens la sautent), le dessin est fait de copies générées stockées. Le recalcul suit l'empreinte (source,
// définition, réglages) après chaque commande : pinceaux_rafraichir, appelé à la fin de deformations_rafraichir.
//   * artistique : le dessin est ÉTIRÉ le long du tracé (abscisse → longueur, ordonnée → normale) ;
//   * motif : le dessin est RÉPÉTÉ en tuiles qui suivent le tracé (étirées pour finir pile, ou coupées) ;
//   * dispersion : des COPIES semées le long du tracé (taille, rotation, écart, avec un aléa à graine stable).
// Règle de mod-bool : tout se CALCULE avant de muter.
import { T } from "./mod-i18n.js";
import { polylignes_objet } from "./mod-bool.js";
import { selection_normalisee } from "./mod-motifs.js";

export const GENRES = ["artistique", "dispersion", "motif"];
const TRACES = new Set(["path", "rect", "ellipse", "forme"]);
const COPIES_MAX = 2000, PAS = 2;            // PAS : aucun segment posé ne dépasse ~2 px
const nb = (x) => String(Math.round(x * 1e4) / 1e4 + 0);
const nbc = (x) => String(Math.round(x * 100) / 100 + 0);
const _cloner = (o) => JSON.parse(JSON.stringify(o));

/* ── réglages ── */
const DEFAUTS = {
  artistique: { echelle: 1, retourner: false, proportionnel: false },
  motif: { echelle: 1, espacement: 0, ajustement: "etirer" },
  dispersion: { espacement: 100, taille: 100, taille_alea: 0, rotation: "trace", rotation_alea: 0, ecart: 0, ecart_alea: 0, graine: 1 },
};
const BORNES = { echelle: [0.05, 20], espacement_motif: [-90, 1000], espacement: [1, 1000], taille: [1, 1000], taille_alea: [0, 100],
  rotation_alea: [0, 180], ecart: [-500, 500], ecart_alea: [0, 500], graine: [1, 1e6] };
const CHOIX = { ajustement: ["etirer", "couper"], rotation: ["trace", "fixe"] };
export function params_pinceau(genre, p = {}, base = {}) {
  if (!GENRES.includes(genre)) throw new Error(T("vectorlab.pinceaux.genre", { genre }));
  const out = { ...DEFAUTS[genre], ...base };
  for (const [k, v] of Object.entries(p || {})) {
    if (!(k in DEFAUTS[genre]) || v === undefined) continue;
    if (typeof DEFAUTS[genre][k] === "boolean") { out[k] = !!v; continue; }
    if (CHOIX[k]) {
      if (!CHOIX[k].includes(v)) throw new Error(T("vectorlab.pinceaux.choix", { v }));
      out[k] = v; continue;
    }
    const [min, max] = BORNES[genre === "motif" && k === "espacement" ? "espacement_motif" : k];
    const n = Number(v);
    if (!Number.isFinite(n) || n < min || n > max) throw new Error(T("vectorlab.pinceaux.borne", { min, max }));
    out[k] = k === "graine" ? Math.round(n) : n;
  }
  return out;
}

/* ── géométrie : les sous-tracés de la source, abscisse curviligne ── */
function _chemins(source) {
  let lignes;
  try { lignes = polylignes_objet({ ...source, cache: false }); } catch { return []; }
  return lignes.filter((l) => l.points.length >= 2).map((l) => {
    const P = l.ferme ? l.points.concat([l.points[0]]) : l.points.slice();
    const cum = [0];
    for (let i = 1; i < P.length; i++) cum.push(cum[i - 1] + Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]));
    return { P, cum, L: cum[cum.length - 1] };
  }).filter((c) => c.L > 1e-6);
}
// le point et la tangente unitaire à l'abscisse s
function _a(c, s) {
  let lo = 0, hi = c.cum.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (c.cum[m] <= s) lo = m; else hi = m; }
  const [ax, ay] = c.P[lo], [bx, by] = c.P[hi], d = c.cum[hi] - c.cum[lo] || 1;
  const t = (s - c.cum[lo]) / d, lx = (bx - ax) / d, ly = (by - ay) / d;
  return [ax + (bx - ax) * t, ay + (by - ay) * t, lx, ly];
}
// les feuilles d'un dessin : { style, lignes } (transforms des groupes appliquées)
function _feuilles(objets) {
  const out = [];
  const v = (o, parents) => {
    if (o.type === "groupe") { (o.enfants || []).forEach((e) => v(e, [...parents, o])); return; }
    let objet = o;
    for (let i = parents.length - 1; i >= 0; i--) objet = { type: "groupe", transform: parents[i].transform, enfants: [objet] };
    let lignes;
    try { lignes = polylignes_objet(objet).filter((l) => l.points.length >= 2); } catch { return; }
    if (lignes.length) out.push({ style: o.style || {}, lignes });
  };
  objets.forEach((o) => v(o, []));
  return out;
}
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
function _prng(graine) {
  let a = graine >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

/* ── le dessin d'un tracé peint ── */
// une tuile du dessin posée le long du sous-tracé c : x du dessin → abscisse s0 + x·kx, y → normale (y − H/2)·ky
function _poser(F, c, H, s0, kx, ky, ajouter) {
  const pas = Math.max(0.05, PAS / Math.max(kx, 1e-6));
  for (const f of F) {
    const d = f.lignes.map((l) => "M" + _subdiviser(l, pas).map(([x, y]) => {
      const [px, py, tx, ty] = _a(c, s0 + x * kx), v = (y - H / 2) * ky;
      return `${nbc(px - ty * v)} ${nbc(py + tx * v)}`;
    }).join(" L") + (l.ferme ? " Z" : "")).join(" ");
    ajouter({ type: "path", d, style: _cloner(f.style) });
  }
}
function _resultat(gid, source, def, p) {
  const chemins = _chemins(source);
  const out = [];
  const W = +def.largeur, H = +def.hauteur;
  const ajouter = (o) => { out.push({ id: `${gid}_p${out.length + 1}`, ...o, genere: true }); };
  if (def.genre === "dispersion") {
    const pas = W * p.taille / 100 * p.espacement / 100;
    const total = chemins.reduce((n, c) => n + Math.floor(c.L / pas + 1e-9) + 1, 0);
    if (total > COPIES_MAX) throw new Error(T("vectorlab.pinceaux.trop", { n: COPIES_MAX }));
    const r = _prng(p.graine);
    for (const c of chemins) {
      for (let s = 0; s <= c.L + 1e-9; s += pas) {
        const [px, py, tx, ty] = _a(c, s);
        const f = p.taille / 100 * (1 + p.taille_alea / 100 * (2 * r() - 1));
        const a = (p.rotation === "trace" ? Math.atan2(ty, tx) * 180 / Math.PI : 0) + p.rotation_alea * (2 * r() - 1);
        const off = (p.ecart + p.ecart_alea * (2 * r() - 1)) / 100 * W * f;
        const k = out.length + 1;
        let j = 0;
        const renommer = (o) => { o.id = `${gid}_p${k}_${++j}`; if (o.type === "groupe") (o.enfants || []).forEach(renommer); return o; };
        out.push({ id: `${gid}_p${k}`, type: "groupe", style: {}, genere: true,
          transform: `translate(${nb(px - ty * off)} ${nb(py + tx * off)}) rotate(${nb(a)}) scale(${nb(f)}) translate(${nb(-W / 2)} ${nb(-H / 2)})`,
          enfants: _cloner(def.objets).map(renommer) });
      }
    }
    return out;
  }
  const F = _feuilles(def.objets);
  if (!F.length) throw new Error(T("vectorlab.pinceaux.sans_geometrie"));
  for (const c of chemins) {
    if (def.genre === "artistique") {
      const kx = c.L / W;
      _poser(F, c, H, 0, kx, (p.proportionnel ? kx : p.echelle) * (p.retourner ? -1 : 1), ajouter);
    } else {
      const unite = W * p.echelle * (1 + p.espacement / 100);
      const n = p.ajustement === "couper" ? Math.floor((c.L + W * p.echelle * p.espacement / 100) / unite + 1e-9) : Math.max(1, Math.round(c.L / unite));
      const k = p.ajustement === "couper" ? 1 : c.L / (n * unite);
      for (let i = 0; i < n; i++) _poser(F, c, H, i * unite * k, p.echelle * k, p.echelle, ajouter);
    }
  }
  return out;
}
const _empreinte = (g, def) => JSON.stringify([g.enfants[0], def, g.pinceau.params]);
function _reconstruire(doc, g) {
  const def = (doc.pinceaux || {})[g.pinceau.id];
  if (!def) throw new Error(T("vectorlab.pinceaux.inconnu", { id: g.pinceau.id }));
  const source = g.enfants[0];
  g.enfants = [source, ..._resultat(g.id, source, def, g.pinceau.params)];
  g.pinceau.empreinte = _empreinte(g, def);
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

/* ══ les ops ══ */
export function op_pinceau_creer(doc, ids, { nom, genre } = {}) {
  if (!GENRES.includes(genre)) throw new Error(T("vectorlab.pinceaux.genre", { genre }));
  if (!ids || !ids.length) throw new Error(T("vectorlab.pinceaux.aucune_selection"));
  const { objets, largeur, hauteur } = selection_normalisee(doc, ids);
  const pinceaux = doc.pinceaux || {};
  let k = 1;
  while (("pc" + k) in pinceaux) k++;
  const n = Object.keys(pinceaux).length + 1;
  if (!doc.pinceaux) doc.pinceaux = {};
  doc.pinceaux["pc" + k] = { nom: String(nom || "").trim() || T("vectorlab.pinceaux.nom_defaut", { n }), genre, objets, largeur, hauteur };
  return "pc" + k;
}

// chaque tracé sélectionné (premier niveau d'un calque déverrouillé) devient un tracé peint → ids des groupes
export function op_pinceau_appliquer(doc, ids, pid, params = {}) {
  const def = (doc.pinceaux || {})[pid];
  if (!def) throw new Error(T("vectorlab.pinceaux.inconnu", { id: pid }));
  const voulu = new Set(ids || []);
  const cibles = [];
  for (const c of doc.calques) for (const o of c.objets) if (voulu.has(o.id)) cibles.push({ calque: c, objet: o });
  if (!cibles.length) throw new Error(T("vectorlab.pinceaux.aucune_selection"));
  if (cibles.some((t) => t.calque.verrou)) throw new Error(T("vectorlab.repeter.verrou"));
  for (const t of cibles) if (!TRACES.has(t.objet.type)) throw new Error(T("vectorlab.pinceaux.pas_trace", { type: t.objet.type }));
  const p = params_pinceau(def.genre, params);
  const neuf = _neuf(doc);
  const groupes = cibles.map((t) => {
    const source = { ..._cloner(t.objet), cache: true };
    const g = { id: neuf(), type: "groupe", style: {}, pinceau: { id: pid, params: p, empreinte: "" }, enfants: [source] };
    _reconstruire(doc, g);                                   // tout se calcule AVANT de muter
    return g;
  });
  cibles.forEach((t, i) => t.calque.objets.splice(t.calque.objets.indexOf(t.objet), 1, groupes[i]));
  return groupes.map((g) => g.id);
}

function _peint(doc, id) {
  const t = _trouver(doc, id);
  if (!t || !t.objet.pinceau) throw new Error(T("vectorlab.pinceaux.pas_pinceau", { id }));
  return t;
}
export function op_pinceau_regler(doc, id, params = {}) {
  const g = _peint(doc, id).objet;
  const def = (doc.pinceaux || {})[g.pinceau.id];
  if (!def) throw new Error(T("vectorlab.pinceaux.inconnu", { id: g.pinceau.id }));
  const essai = { ...g, enfants: g.enfants.map(_cloner), pinceau: { ...g.pinceau, params: params_pinceau(def.genre, params, g.pinceau.params) } };
  _reconstruire(doc, essai);
  g.enfants = essai.enfants;
  g.pinceau = essai.pinceau;
}
function _rendre(t) {
  const liste = t.parent ? t.parent.enfants : t.calque.objets;
  const source = _cloner(t.objet.enfants[0]);
  delete source.cache;
  liste.splice(liste.indexOf(t.objet), 1, source);
  return source.id;
}
// Retirer le pinceau : le tracé revient seul, visible, à la place du groupe
export function op_pinceau_retirer(doc, id) {
  const t = _peint(doc, id);
  if (!t.parent && t.calque.verrou) throw new Error(T("vectorlab.repeter.verrou"));
  return _rendre(t);
}
// Supprimer un pinceau : tous ses tracés peints reviennent simples
export function op_pinceau_supprimer(doc, pid) {
  if (!(doc.pinceaux || {})[pid]) throw new Error(T("vectorlab.pinceaux.inconnu", { id: pid }));
  const ids = [];
  const v = (objs) => { for (const o of objs || []) { if (o.pinceau && o.pinceau.id === pid) ids.push(o.id); else if (o.type === "groupe") v(o.enfants); } };
  for (const c of doc.calques) v(c.objets);
  for (const id of ids) _rendre(_trouver(doc, id));
  delete doc.pinceaux[pid];
}

/* ── vivant : appelé à la fin de deformations_rafraichir (mod-deformer.js) ── */
export function pinceaux_rafraichir(doc) {
  let n = 0;
  const v = (objs) => {
    for (const o of objs || []) {
      if (o.type !== "groupe") continue;
      v(o.enfants);
      if (!o.pinceau || !Array.isArray(o.enfants) || !o.enfants.length || o.enfants[0].genere) continue;
      const def = (doc.pinceaux || {})[o.pinceau.id];
      if (!def || _empreinte(o, def) === o.pinceau.empreinte) continue;     // définition disparue : dernier état gardé
      try { _reconstruire(doc, o); n++; } catch { /* recalcul impossible : dernier état gardé */ }
    }
  };
  for (const c of doc.calques) v(c.objets);
  return n;
}
