// mod-repeter.js — lot D2 « Répéter et fusionner » (spec 2026-11-08-illustrator-vectorlab-inventaire.md, plan
// 2026-11-08-vectorlab-d2-repeter-fusionner.md) : les RÉPÉTITIONS VIVANTES d'Illustrator.
//
// Une répétition est un GROUPE qui porte sa recette : { repetition: { mode, params, empreinte }, enfants: [source,
// ...copies] }. Les copies sont STOCKÉES (l'export, l'impression, le serveur et une version plus ancienne les voient
// sans rien savoir des répétitions), marquées `genere: true`, d'ids `<groupe>_r<k>` (descendants `<copie>_<j>`) qui
// ne recroisent jamais les `o<n>` d'idLibre. `vivants_d2_rafraichir` passe après CHAQUE commande, appelé par
// derives_rafraichir (mod-vivants.js) : la source modifiée, les copies suivent dans la même étape d'historique.
// L'empreinte couvre la source ET les réglages : seule une empreinte changée coûte un recalcul. Une source disparue,
// ou un recalcul impossible, laisse le groupe à son dernier état — jamais une exception au rendu.
// Règle de mod-bool : tout se CALCULE avant de muter, un refus ne laisse aucune trace.
import { T } from "./mod-i18n.js";
import { polylignes_objet } from "./mod-bool.js";

const MAX_COPIES = 200;
const MODES = new Set(["radiale"]);
const nbc = (x) => String(Math.round(Number((x * 100).toPrecision(12))) / 100);

/* ── la boîte d'un objet, transform compris (la géométrie des booléens) ── */
function _boite(o) {
  let lignes;
  if (o.type === "image" || o.type === "cadre") {
    lignes = polylignes_objet({ type: "rect", x: o.x, y: o.y, w: o.w, h: o.h, transform: o.transform });
  } else {
    try { lignes = polylignes_objet(o); } catch (e) { return null; }
  }
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const l of lignes) for (const [x, y] of l.points) {
    if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
  }
  if (!(x1 >= x0) || !(y1 >= y0)) return null;
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}

/* ── réglages : défauts, bornes ── */
function _entier(v, min, max, cle) {
  const n = Number(v);
  if (!Number.isInteger(n) || n < min || n > max) throw new Error(T(cle, { min, max }));
  return n;
}
function _positif(v, cle) {
  const n = Number(v);
  if (!Number.isFinite(n) || n <= 0 || n > 1e5) throw new Error(T(cle));
  return n;
}
function _params(mode, p, source, base = {}) {
  const v = { ...base, ...(p || {}) };
  if (mode === "radiale") {
    const b = _boite(source);
    return {
      nombre: _entier(v.nombre === undefined ? 8 : v.nombre, 2, 100, "vectorlab.repeter.nombre"),
      rayon: _positif(v.rayon === undefined ? Math.hypot(b.w, b.h) / 2 : v.rayon, "vectorlab.repeter.rayon"),
      orienter: v.orienter === undefined ? true : !!v.orienter,
    };
  }
  throw new Error(T("vectorlab.repeter.mode", { mode }));
}

/* ── les copies ── */
// une copie profonde SANS les liens vivants de la source (une copie suivrait la mauvaise source) ni recette (une
// copie de répétition est figée : seule la source se recalcule), ids dérivés de celui de la copie
function _copier(o, id) {
  const c = JSON.parse(JSON.stringify(o));
  const nettoyer = (x) => {
    delete x.derive; delete x.repetition; delete x.genere;
    if (x.type === "textechemin") { delete x.chemin; delete x.empreinte; }
    if (x.type === "groupe") for (const e of x.enfants || []) nettoyer(e);
  };
  nettoyer(c);
  const renommer = (x, i) => {
    x.id = i;
    if (x.type === "groupe") {
      (x.enfants || []).forEach((e, j) => renommer(e, `${i}_${j + 1}`));
      if (x.clip) x.clip = `${i}_1`;               // un groupe écrêté : son conteneur est le premier enfant
    }
  };
  renommer(c, id);
  c.genere = true;
  return c;
}
function _prefixer(o, t) { o.transform = o.transform ? `${t} ${o.transform}` : t; return o; }

function _copies(gid, mode, p, source) {
  const out = [];
  if (mode === "radiale") {
    const b = _boite(source);
    if (!b) throw new Error(T("vectorlab.repeter.source_type"));
    const sx = b.x + b.w / 2, sy = b.y + b.h / 2;
    const cx = sx, cy = sy + p.rayon;            // la source en haut du cercle, comme Illustrator
    for (let k = 1; k < p.nombre; k++) {
      const a = 360 * k / p.nombre;
      const c = _copier(source, `${gid}_r${k}`);
      if (p.orienter) _prefixer(c, `rotate(${nbc(a)} ${nbc(cx)} ${nbc(cy)})`);
      else {
        const r = a * Math.PI / 180, dx = sx - cx, dy = sy - cy;
        const nx = cx + dx * Math.cos(r) - dy * Math.sin(r), ny = cy + dx * Math.sin(r) + dy * Math.cos(r);
        _prefixer(c, `translate(${nbc(nx - sx)} ${nbc(ny - sy)})`);
      }
      out.push(c);
    }
  }
  if (out.length + 1 > MAX_COPIES) throw new Error(T("vectorlab.repeter.trop", { max: MAX_COPIES }));
  return out;
}
const _empreinte = (g) => JSON.stringify([g.enfants[0], g.repetition.mode, g.repetition.params]);

function _reconstruire(g) {
  const source = g.enfants[0];
  g.enfants = [source, ..._copies(g.id, g.repetition.mode, g.repetition.params, source)];
  g.repetition.empreinte = _empreinte(g);
}

/* ── chercher ── */
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
function _idsPris(doc) {
  const pris = new Set();
  const v = (objs) => { for (const o of objs || []) { pris.add(o.id); if (o.type === "groupe") v(o.enfants); } };
  for (const c of doc.calques) v(c.objets);
  for (const s of Object.values(doc.symboles || {})) v(s.objets);
  return pris;
}
function _source_ids(doc) {
  const pris = _idsPris(doc);
  let n = 1;
  return () => { while (pris.has("o" + n)) n++; pris.add("o" + n); return "o" + n; };
}

/* ── T1 (t450) Objet › Répétition › Radiale ──
   La sélection (objets du premier niveau d'un calque déverrouillé) devient la SOURCE — plusieurs objets sont
   d'abord groupés — et le groupe vivant prend la place du plus haut d'entre eux. -> id du groupe vivant */
export function op_repeter(doc, ids, mode, params = {}) {
  if (!MODES.has(mode)) throw new Error(T("vectorlab.repeter.mode", { mode }));
  const voulu = new Set(ids || []);
  if (!voulu.size) throw new Error(T("vectorlab.repeter.rien"));
  const cibles = [];
  for (const c of doc.calques) {
    for (const o of c.objets) if (voulu.has(o.id)) cibles.push({ calque: c, objet: o });
  }
  if (cibles.length !== voulu.size) {
    const genere = [...voulu].some((id) => { const t = _trouver(doc, id); return t && t.objet.genere; });
    throw new Error(T(genere ? "vectorlab.repeter.copie_generee" : "vectorlab.repeter.rien"));
  }
  if (cibles.some((t) => t.calque.verrou)) throw new Error(T("vectorlab.repeter.verrou"));
  // tout se calcule AVANT de muter
  const neuf = _source_ids(doc);
  const objs = cibles.map((t) => t.objet);
  const source = objs.length === 1 ? objs[0] : { id: neuf(), type: "groupe", style: {}, enfants: objs };
  if (!_boite(source)) throw new Error(T("vectorlab.repeter.source_type"));
  const p = _params(mode, params, source);
  const gid = neuf();
  const g = { id: gid, type: "groupe", style: {}, repetition: { mode, params: p, empreinte: "" }, enfants: [source] };
  _reconstruire(g);
  // muter : le groupe à la place du plus haut, les autres retirés
  const haut = cibles[cibles.length - 1];
  const idx = haut.calque.objets.indexOf(haut.objet);
  haut.calque.objets.splice(idx, 1, g);
  for (const t of cibles.slice(0, -1)) t.calque.objets.splice(t.calque.objets.indexOf(t.objet), 1);
  return gid;
}

// Options de répétition : les réglages fournis remplacent les anciens, les autres restent
export function op_repetition_regler(doc, id, params = {}) {
  const t = _trouver(doc, id);
  if (!t) throw new Error(T("vectorlab.repeter.introuvable", { id }));
  const g = t.objet;
  if (!g.repetition) throw new Error(T("vectorlab.repeter.pas_repetition", { id }));
  const p = _params(g.repetition.mode, params, g.enfants[0], g.repetition.params);
  const essai = { ...g, repetition: { ...g.repetition, params: p } };
  _reconstruire(essai);
  g.repetition = essai.repetition;
  g.enfants = essai.enfants;
}

/* ── vivant : appelé par derives_rafraichir après chaque commande ── */
export function vivants_d2_rafraichir(doc) {
  let n = 0;
  // les répétitions les plus profondes d'abord : une répétition de répétition lit une source déjà à jour
  const v = (objs) => {
    for (const o of objs || []) {
      if (o.type !== "groupe") continue;
      v(o.enfants);
      if (!o.repetition || !Array.isArray(o.enfants) || !o.enfants.length) continue;
      if (o.enfants[0].genere) continue;            // la source a disparu : dernier état gardé
      if (_empreinte(o) === o.repetition.empreinte) continue;
      try {
        const essai = { ...o, repetition: { ...o.repetition } };
        _reconstruire(essai);
        o.enfants = essai.enfants;
        o.repetition = essai.repetition;
        n++;
      } catch (e) {
        /* recalcul impossible (source devenue sans géométrie…) : dernier état gardé, retenté au prochain */
      }
    }
  };
  for (const c of doc.calques) v(c.objets);
  return n;
}

// Décomposer : la répétition redevient un groupe ordinaire ; ses copies reçoivent des ids o<n> neufs
export function repetition_decomposer(doc, g) {
  const neuf = _source_ids(doc);
  const renommer = (x) => {
    x.id = neuf();
    if (x.type === "groupe") {
      for (const e of x.enfants || []) renommer(e);
      if (x.clip && x.enfants && x.enfants[0]) x.clip = x.enfants[0].id;
    }
  };
  for (const e of g.enfants.slice(1)) { if (e.genere) { delete e.genere; renommer(e); } }
  delete g.repetition;
}
