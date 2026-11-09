// mod-recolorer.js — lot D5 « Couleur et motif », T1 (t475 ; plan 2026-11-09-vectorlab-d5-couleur-motif.md) : les
// COULEURS d'une sélection et leur réassignation, socle de « Recolorer l'illustration » et d'Édition › Couleurs.
//
// Une couleur vit dans un EMPLACEMENT : le fond, le contour, un contour multiple ou un effet d'un objet, un arrêt d'un
// dégradé employé, la couleur ou le fond d'un motif employé. Les groupes sont parcourus ; les copies générées d'un objet
// vivant (`genere`) ne le sont pas : leur source les refait. Une couleur globale (« glob:<nom> ») est résolue ; la
// réassigner pose une couleur simple sur l'objet visé, la globale ne change pas.
// PARTAGE. Un dégradé ou un motif employé aussi HORS de la sélection est cloné (id neuf) avant d'être modifié, et la
// sélection entière passe sur ce clone : on ne change jamais ce qui n'est pas sélectionné.
// Règle de mod-bool : tout se CALCULE avant de muter (un refus ne laisse rien à moitié fait).
import { T } from "./mod-i18n.js";

export function hex_normal(v) {
  if (typeof v !== "string") return null;
  const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(v.trim());
  if (!m) return null;
  const h = m[1].toLowerCase();
  return "#" + (h.length === 3 ? h.split("").map((c) => c + c).join("") : h);
}

/* ── les objets visés : les ids demandés (calques et objets déverrouillés), puis tout leur intérieur, une fois ── */
function _cibles(doc, ids) {
  const voulu = new Set(ids || []), out = [];
  const dans = (objs) => {
    for (const o of objs || []) {
      if (o.genere) continue;
      if (voulu.has(o.id) && !o.verrou) out.push(o);
      if (o.type === "groupe") dans(o.enfants);
    }
  };
  for (const c of doc.calques || []) if (!c.verrou) dans(c.objets);
  const vus = new Set(), tous = [];
  const visiter = (o) => {
    if (o.genere || vus.has(o)) return;
    vus.add(o); tous.push(o);
    if (o.type === "groupe") (o.enfants || []).forEach(visiter);
  };
  out.forEach(visiter);
  return tous;
}

/* ── les emplacements : { lire, ecrire, ou } ; les références grad: / motif: à part ── */
function _emplacementsStyle(s, ou0, out, refs) {
  if (!s) return;
  const champ = (cle, ou) => {
    const v = s[cle];
    if (typeof v !== "string") return;
    if (v.startsWith("grad:")) { refs.push({ genre: "degrade", id: v.slice(5), s, cle }); return; }
    if (v.startsWith("motif:")) { refs.push({ genre: "motif", id: v.slice(6), s, cle }); return; }
    out.push({ lire: () => s[cle], ecrire: (x) => { s[cle] = x; }, ou });
  };
  champ("fond", ou0);
  champ("contour", "contour");
  for (const c of s.contours || []) out.push({ lire: () => c.couleur, ecrire: (x) => { c.couleur = x; }, ou: "contour" });
  for (const e of s.effets || []) if (e && e.couleur !== undefined) out.push({ lire: () => e.couleur, ecrire: (x) => { e.couleur = x; }, ou: "effet" });
}
function _emplacementsObjets(objets, out, refs) {
  for (const o of objets) _emplacementsStyle(o.style, o.type === "texte" ? "texte" : "fond", out, refs);
}
function _emplacementsDef(doc, genre, id, out) {
  if (genre === "degrade") {
    const g = (doc.degrades || {})[id];
    for (const st of (g && g.stops) || []) out.push({ lire: () => st.couleur, ecrire: (x) => { st.couleur = x; }, ou: "degrade" });
    return;
  }
  const m = (doc.motifs || {})[id];
  if (!m) return;
  if (m.couleur !== undefined) out.push({ lire: () => m.couleur, ecrire: (x) => { m.couleur = x; }, ou: "motif" });
  if (m.fond !== undefined) out.push({ lire: () => m.fond, ecrire: (x) => { m.fond = x; }, ou: "motif" });
  // un motif fait d'objets (T4) : leurs couleurs aussi (les références qu'ils portent ne sont pas suivies)
  const sous = [], emp = [];
  const visiter = (o) => { sous.push(o); if (o.type === "groupe") (o.enfants || []).forEach(visiter); };
  (m.objets || []).forEach(visiter);
  _emplacementsObjets(sous, emp, []);
  for (const e of emp) out.push({ ...e, ou: "motif" });
}

/* hex d'un emplacement (globale résolue) et le nom de la globale, ou null */
function _valeur(doc, v) {
  if (typeof v === "string" && v.startsWith("glob:")) {
    const h = hex_normal((doc.couleursGlobales || {})[v.slice(5)]);
    return h ? { hex: h, globale: v.slice(5) } : null;
  }
  const h = hex_normal(v);
  return h ? { hex: h, globale: null } : null;
}

function _releve(doc, ids) {
  const objets = _cibles(doc, ids);
  const emp = [], refs = [];
  _emplacementsObjets(objets, emp, refs);
  const defs = new Map();                                  // "degrade:g1" → { genre, id, emp: [] }
  for (const r of refs) {
    const k = r.genre + ":" + r.id;
    if (!defs.has(k)) { const e = []; _emplacementsDef(doc, r.genre, r.id, e); defs.set(k, { genre: r.genre, id: r.id, emp: e, refs: [] }); }
    defs.get(k).refs.push(r);
  }
  return { objets, emp, defs };
}

export function couleurs_selection(doc, ids) {
  const { emp, defs } = _releve(doc, ids);
  const tous = [...emp, ...[...defs.values()].flatMap((d) => d.emp)];
  const par = new Map();
  for (const e of tous) {
    const v = _valeur(doc, e.lire());
    if (!v) continue;
    if (!par.has(v.hex)) par.set(v.hex, { hex: v.hex, n: 0, ou: new Set(), globales: new Set() });
    const x = par.get(v.hex);
    x.n++; x.ou.add(e.ou);
    if (v.globale) x.globales.add(v.globale);
  }
  return [...par.values()].map((x) => ({ hex: x.hex, n: x.n, ou: [...x.ou], globales: [...x.globales] }))
    .sort((a, b) => b.n - a.n || (a.hex < b.hex ? -1 : 1));
}

/* les références à un dégradé ou un motif HORS des objets visés (symboles compris, copies générées exclues) */
function _refsHors(doc, objets) {
  const dedans = new Set(objets), n = new Map();
  const compter = (s) => {
    if (!s) return;
    for (const cle of ["fond", "contour", "masque"]) {
      const v = s[cle];
      if (typeof v !== "string") continue;
      const k = v.startsWith("grad:") ? "degrade:" + v.slice(5) : v.startsWith("motif:") ? "motif:" + v.slice(6) : null;
      if (k) n.set(k, (n.get(k) || 0) + 1);
    }
  };
  const visiter = (objs) => {
    for (const o of objs || []) {
      if (o.genere) continue;
      if (!dedans.has(o)) compter(o.style);
      if (o.type === "groupe") visiter(o.enfants);
    }
  };
  for (const c of doc.calques || []) visiter(c.objets);
  for (const s of Object.values(doc.symboles || {})) visiter(s.objets);
  for (const m of Object.values(doc.motifs || {})) visiter(m.objets);
  return n;
}
const _idLibre = (table, prefixe) => { let k = 1; while ((prefixe + k) in table) k++; return prefixe + k; };

// le cœur : f(hex) → hex, appelée UNE fois par couleur distincte ; tout est calculé avant de muter
function _reecrire(doc, ids, f) {
  const { objets, emp, defs } = _releve(doc, ids);
  if (!objets.length) throw new Error(T("vectorlab.recolorer.aucune_selection"));
  const cache = new Map();
  const nouvelle = (hex) => {
    if (!cache.has(hex)) {
      const r = f(hex), h = hex_normal(r);
      if (!h) throw new Error(T("vectorlab.recolorer.couleur_invalide", { c: r }));
      cache.set(hex, h);
    }
    return cache.get(hex);
  };
  const plan = (liste) => liste.map((e) => {
    const v = _valeur(doc, e.lire());
    if (!v) return null;
    const h = nouvelle(v.hex);
    return h !== v.hex ? { e, h } : null;
  }).filter(Boolean);
  const aFaire = plan(emp);
  const hors = _refsHors(doc, objets);
  const clones = [];
  for (const d of defs.values()) {
    const p = plan(d.emp);
    if (!p.length) continue;
    clones.push({ d, p, partage: (hors.get(d.genre + ":" + d.id) || 0) > 0 });
  }
  // mutations
  let n = 0;
  for (const { e, h } of aFaire) { e.ecrire(h); n++; }
  for (const { d, p, partage } of clones) {
    if (partage) {
      const table = d.genre === "degrade" ? doc.degrades : doc.motifs;
      const nid = _idLibre(table, d.genre === "degrade" ? "g" : "m");
      table[nid] = JSON.parse(JSON.stringify(table[d.id]));
      const e2 = [];
      _emplacementsDef(doc, d.genre, nid, e2);
      const p2 = plan(e2);
      for (const { e, h } of p2) { e.ecrire(h); n++; }
      for (const r of d.refs) r.s[r.cle] = (d.genre === "degrade" ? "grad:" : "motif:") + nid;
    } else {
      for (const { e, h } of p) { e.ecrire(h); n++; }
    }
  }
  return n;
}

/* table : { ancienne: nouvelle } (hex, toute casse) → nombre de couleurs réécrites */
export function op_recolorer(doc, ids, table) {
  const t = new Map();
  for (const [a, b] of Object.entries(table || {})) {
    const ha = hex_normal(a), hb = hex_normal(b);
    if (!ha) throw new Error(T("vectorlab.recolorer.couleur_invalide", { c: a }));
    if (!hb) throw new Error(T("vectorlab.recolorer.couleur_invalide", { c: b }));
    t.set(ha, hb);
  }
  return _reecrire(doc, ids, (h) => t.get(h) || h);
}

export function op_couleurs_transformer(doc, ids, f) {
  return _reecrire(doc, ids, f);
}
