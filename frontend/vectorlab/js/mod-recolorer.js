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
import { polylignes_objet } from "./mod-bool.js";

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

/* ── T2 (t476) : Édition › Couleurs — transformations PURES d'une couleur hex (sans arrondi intermédiaire) ── */
const _rvb = (h) => { const v = parseInt(hex_normal(h).slice(1), 16); return [(v >> 16) & 255, (v >> 8) & 255, v & 255]; };
const _hex = (r, g, b) => "#" + [r, g, b].map((x) => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, "0")).join("");
const _borne = (v, min, max) => {
  const n = Number(v === undefined ? 0 : v);
  if (!Number.isFinite(n) || n < min || n > max) throw new Error(T("vectorlab.couleurs.borne", { min, max }));
  return n;
};
export function inverser(h) { const [r, g, b] = _rvb(h); return _hex(255 - r, 255 - g, 255 - b); }
export function niveaux_de_gris(h) {
  const [r, g, b] = _rvb(h), y = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return _hex(y, y, y);
}
function _versTsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2, d = max - min;
  if (!d) return [0, 0, l];
  const s = d / (1 - Math.abs(2 * l - 1));
  const h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
}
function _depuisTsl(h, s, l) {
  const c = (1 - Math.abs(2 * l - 1)) * s, hp = (((h % 360) + 360) % 360) / 60, x = c * (1 - Math.abs((hp % 2) - 1));
  const [r, g, b] = hp < 1 ? [c, x, 0] : hp < 2 ? [x, c, 0] : hp < 3 ? [0, c, x] : hp < 4 ? [0, x, c] : hp < 5 ? [x, 0, c] : [c, 0, x];
  const m = l - c / 2;
  return _hex((r + m) * 255, (g + m) * 255, (b + m) * 255);
}
// pct de −100 (désaturé) à +100 (saturation doublée, bornée à 100 %)
export function saturer(h, pct) {
  const p = _borne(pct, -100, 100);
  const [t, s, l] = _versTsl(..._rvb(h));
  return _depuisTsl(t, Math.max(0, Math.min(1, s * (1 + p / 100))), l);
}
// mode rvb : a, b, c = rouge, vert, bleu ; mode cmjn : a, b, c, d = cyan, magenta, jaune, noir — en % de la pleine
// échelle, de −100 à +100, ajoutés puis bornés
export function equilibre(h, { mode, a, b, c, d } = {}) {
  const v = [a, b, c, d].map((x) => _borne(x, -100, 100) / 100);
  const [r, g, bl] = _rvb(h);
  if (mode === "rvb") return _hex(r + v[0] * 255, g + v[1] * 255, bl + v[2] * 255);
  if (mode === "cmjn") {
    const n = 1 - Math.max(r, g, bl) / 255;
    const k = (x) => (n >= 1 ? 0 : (1 - x / 255 - n) / (1 - n));
    const cl = (x) => Math.max(0, Math.min(1, x));
    const C = cl(k(r) + v[0]), M = cl(k(g) + v[1]), J = cl(k(bl) + v[2]), N = cl(n + v[3]);
    return _hex(255 * (1 - C) * (1 - N), 255 * (1 - M) * (1 - N), 255 * (1 - J) * (1 - N));
  }
  throw new Error(T("vectorlab.couleurs.mode", { mode }));
}

/* la fusion : les FONDS des objets intermédiaires, interpolés par rang entre les deux objets extrêmes (gauche → droite,
   haut → bas, ou dessous → dessus) ; il faut au moins trois objets à fond de couleur simple */
const SENS = ["horizontal", "vertical", "avant_arriere"];
function _centre(o) {
  try {
    const P = polylignes_objet(o).flatMap((l) => l.points);
    if (P.length) {
      const xs = P.map((p) => p[0]), ys = P.map((p) => p[1]);
      return [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
    }
  } catch { /* texte, image : leur point */ }
  return [+o.x || +o.cx || 0, +o.y || +o.cy || 0];
}
export function op_couleurs_fusion(doc, ids, sens) {
  if (!SENS.includes(sens)) throw new Error(T("vectorlab.couleurs.sens", { sens }));
  const objets = _cibles(doc, ids).filter((o) => o.type !== "groupe" && o.style && _valeur(doc, o.style.fond));
  if (objets.length < 3) throw new Error(T("vectorlab.couleurs.fusion_trois"));
  const k = sens === "horizontal" ? 0 : 1;
  const ordre = sens === "avant_arriere" ? objets.slice() : objets.map((o, i) => ({ o, i, c: _centre(o)[k] }))
    .sort((a, b) => a.c - b.c || a.i - b.i).map((x) => x.o);
  const a = _rvb(_valeur(doc, ordre[0].style.fond).hex), b = _rvb(_valeur(doc, ordre[ordre.length - 1].style.fond).hex);
  const n = ordre.length - 1;
  let faits = 0;
  for (let i = 1; i < n; i++) {
    const t = i / n;
    ordre[i].style.fond = _hex(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
    faits++;
  }
  return faits;
}

/* ── T3 (t477) : Recolorer l'illustration — des TABLES { ancienne: nouvelle } sur les couleurs d'une sélection
   ([{ hex, n }], celles de couleurs_selection) ; le dialogue les montre, op_recolorer les applique ── */
const _lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
function _lab(h) {
  const [r, g, b] = _rvb(h).map(_lin);
  const x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, y = 0.2126 * r + 0.7152 * g + 0.0722 * b, z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883;
  const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116);
  return [116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))];
}
const _parUsage = (couleurs) => couleurs.map((c, i) => ({ ...c, i })).sort((a, b) => b.n - a.n || a.i - b.i);

// regroupe les couleurs les plus proches (distance Lab) jusqu'à n groupes ; un groupe prend la couleur du plus lourd
// (en usages) des deux qu'on réunit
export function reduire(couleurs, n) {
  const N = _borne(n, 1, 64);
  if (!Number.isInteger(N)) throw new Error(T("vectorlab.couleurs.borne", { min: 1, max: 64 }));
  const groupes = _parUsage(couleurs).map((c) => ({ rep: c.hex, lab: _lab(c.hex), n: c.n, membres: [c.hex] }));
  while (groupes.length > N) {
    let mi = 0, mj = 1, md = Infinity;
    for (let i = 0; i < groupes.length; i++) for (let j = i + 1; j < groupes.length; j++) {
      const a = groupes[i].lab, b = groupes[j].lab, d = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2;
      if (d < md) { md = d; mi = i; mj = j; }
    }
    const A = groupes[mi], B = groupes[mj], fort = B.n > A.n ? B : A;
    A.rep = fort.rep; A.lab = fort.lab; A.n += B.n; A.membres.push(...B.membres);
    groupes.splice(mj, 1);
  }
  const t = {};
  for (const g of groupes) for (const m of g.membres) t[m] = g.rep;
  return t;
}

// la règle d'harmonie tourne la teinte des couleurs COLORÉES (dans l'ordre d'usage) autour de la première d'entre elles,
// en gardant leur saturation et leur clarté ; les gris restent
const REGLES = { complementaire: [0, 180], analogue: [0, 30, -30], triade: [0, 120, 240], tetrade: [0, 90, 180, 270], monochrome: [0] };
export function harmoniser(couleurs, regle) {
  const pas = REGLES[regle];
  if (!pas) throw new Error(T("vectorlab.couleur.harm_inconnue", { type: regle }));
  const t = {};
  let base = null, k = 0;
  for (const c of _parUsage(couleurs)) {
    const [h, s, l] = _versTsl(..._rvb(c.hex));
    if (s < 0.05) { t[c.hex] = c.hex; continue; }
    if (base === null) base = h;
    t[c.hex] = _depuisTsl(base + pas[k++ % pas.length], s, l);
  }
  return t;
}

// une permutation des couleurs entre elles, à graine stable ; jamais l'identité dès qu'il y a deux couleurs
function _hasard(graine) {
  let a = (graine >>> 0) || 1;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
export function melanger(couleurs, graine = 1) {
  const hex = couleurs.map((c) => c.hex), p = hex.slice(), r = _hasard(graine);
  for (let i = p.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [p[i], p[j]] = [p[j], p[i]]; }
  if (p.length > 1 && p.every((h, i) => h === hex[i])) p.push(p.shift());
  return Object.fromEntries(hex.map((h, i) => [h, p[i]]));
}
