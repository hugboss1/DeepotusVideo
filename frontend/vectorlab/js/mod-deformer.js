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

const EFFETS = new Set(["enveloppe", "distorsion", "torsion", "rugosite", "zigzag", "gonfler", "pointes"]);
export const STYLES_POINTES = ["aucune", "triangle", "ouverte", "cercle", "carre", "barre"];
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
function _entier(v, defaut, min, max) {
  const n = Number(v === undefined ? defaut : v);
  if (!Number.isInteger(n) || n < min || n > max) throw new Error(T("vectorlab.deformer.entier", { min, max }));
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
  if (effet === "distorsion") {
    // haut-gauche, haut-droit, bas-droit, bas-gauche : le déplacement [dx, dy] de chaque coin de la boîte
    const c = v.coins === undefined ? [[0, 0], [0, 0], [0, 0], [0, 0]] : v.coins;
    const ok = Array.isArray(c) && c.length === 4 && c.every((q) => Array.isArray(q) && q.length === 2
      && q.every((x) => typeof x === "number" && Number.isFinite(x) && Math.abs(x) <= 1e5));
    if (!ok) throw new Error(T("vectorlab.deformer.coins"));
    return { coins: c.map((q) => [q[0], q[1]]) };
  }
  if (effet === "torsion") return { angle: _nombre(v.angle, 45, -3600, 3600, "vectorlab.deformer.angle") };
  if (effet === "rugosite") return {
    taille: _nombre(v.taille, 5, 0, 1000, "vectorlab.deformer.valeur"),
    details: _nombre(v.details, 10, 0.1, 100, "vectorlab.deformer.valeur"),
    lisse: !!v.lisse,
    graine: _entier(v.graine, 1, 0, 1e9),
  };
  if (effet === "pointes") {
    const debut = v.debut === undefined ? "aucune" : v.debut, fin = v.fin === undefined ? "triangle" : v.fin;
    for (const x of [debut, fin]) if (!STYLES_POINTES.includes(x)) throw new Error(T("vectorlab.deformer.pointe", { pointe: x }));
    if (debut === "aucune" && fin === "aucune") throw new Error(T("vectorlab.deformer.aucune_pointe"));
    return { debut, fin, echelle: _nombre(v.echelle, 100, 10, 1000, "vectorlab.deformer.pourcent") };
  }
  if (effet === "gonfler") return { pourcent: _nombre(v.pourcent, 30, -200, 200, "vectorlab.deformer.pourcent") };
  if (effet === "zigzag") return {
    taille: _nombre(v.taille, 5, 0, 1000, "vectorlab.deformer.valeur"),
    cretes: _entier(v.cretes, 4, 1, 100),
    lisse: !!v.lisse,
  };
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
/* ── T2 (t461) Distorsion libre : interpolation bilinéaire entre les quatre coins déplacés de la boîte ── */
function _distorsion(p, B) {
  const [hg, hd, bd, bg] = [[B.x, B.y], [B.x + B.w, B.y], [B.x + B.w, B.y + B.h], [B.x, B.y + B.h]]
    .map((c, i) => [c[0] + p.coins[i][0], c[1] + p.coins[i][1]]);
  return ([x, y]) => {
    const u = B.w > 0 ? (x - B.x) / B.w : 0.5, v = B.h > 0 ? (y - B.y) / B.h : 0.5;
    const a = (1 - u) * (1 - v), b = u * (1 - v), c = u * v, d = (1 - u) * v;
    return [a * hg[0] + b * hd[0] + c * bd[0] + d * bg[0], a * hg[1] + b * hd[1] + c * bd[1] + d * bg[1]];
  };
}
/* ── T2 (t461) Torsion : chaque point tourne autour du centre d'un angle proportionnel à sa distance (0 au centre,
   l'angle entier à la demi-diagonale de la boîte) ── */
function _torsion(p, B) {
  const cx = B.x + B.w / 2, cy = B.y + B.h / 2, rmax = Math.hypot(B.w, B.h) / 2 || 1;
  return ([x, y]) => {
    const dx = x - cx, dy = y - cy, a = p.angle * Math.PI / 180 * Math.min(1, Math.hypot(dx, dy) / rmax);
    return [cx + dx * Math.cos(a) - dy * Math.sin(a), cy + dx * Math.sin(a) + dy * Math.cos(a)];
  };
}
/* ── T3 (t462) Rugosité et Zigzag : ils travaillent LE LONG du tracé (échantillons, normales), une ligne à la fois ;
   ils rendent { ligne(l, i) -> { points, lisse } } au lieu d'une fonction de point ── */
// un générateur pseudo-aléatoire à graine (mulberry32) : la même graine redonne le même tracé à chaque recalcul
function _prng(a) {
  return () => {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
// des points à intervalles égaux le long d'une polyligne (fermée : le dernier ne répète pas le premier)
function _echantillonner(l, pas) {
  const q = l.ferme ? l.points.concat([l.points[0]]) : l.points;
  const cum = [0];
  for (let i = 1; i < q.length; i++) cum.push(cum[i - 1] + Math.hypot(q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]));
  const L = cum[cum.length - 1];
  const n = Math.max(l.ferme ? 3 : 1, Math.round(L / pas));
  const out = [];
  let j = 1;
  for (let k = 0; k < (l.ferme ? n : n + 1); k++) {
    const s = L * k / n;
    while (j < q.length - 1 && cum[j] < s) j++;
    const d = cum[j] - cum[j - 1], u = d > 0 ? (s - cum[j - 1]) / d : 0;
    out.push([q[j - 1][0] + (q[j][0] - q[j - 1][0]) * u, q[j - 1][1] + (q[j][1] - q[j - 1][1]) * u]);
  }
  return out;
}
function _rugosite(p) {
  return { ligne: (l, i) => {
    const r = _prng(p.graine * 1000003 + i * 7919);
    return { points: _echantillonner(l, 100 / p.details).map(([x, y]) => [x + (r() * 2 - 1) * p.taille, y + (r() * 2 - 1) * p.taille]), lisse: p.lisse };
  } };
}
// chaque segment d'origine : 2 × crêtes intervalles, les points intérieurs écartés de ± taille selon la normale ;
// les ancres restent en place
function _zigzag(p) {
  return { ligne: (l) => {
    const q = l.ferme ? l.points.concat([l.points[0]]) : l.points;
    const out = [q[0]], n = 2 * p.cretes;
    for (let i = 1; i < q.length; i++) {
      const [ax, ay] = q[i - 1], [bx, by] = q[i], L = Math.hypot(bx - ax, by - ay) || 1;
      const nx = -(by - ay) / L, ny = (bx - ax) / L;
      for (let k = 1; k <= n; k++) {
        const e = k < n ? (k % 2 ? 1 : -1) * p.taille : 0;
        out.push([ax + (bx - ax) * k / n + nx * e, ay + (by - ay) * k / n + ny * e]);
      }
    }
    if (l.ferme) out.pop();
    return { points: out, lisse: p.lisse };
  } };
}
// une suite de points en courbes (Catmull-Rom → Bézier cubiques), fermée ou non
function _dLisse(q, ferme) {
  const n = q.length, P = (i) => (ferme ? q[(i + n) % n] : q[Math.max(0, Math.min(n - 1, i))]);
  let d = `M${nbc(q[0][0])} ${nbc(q[0][1])}`;
  for (let i = 0; i < (ferme ? n : n - 1); i++) {
    const p0 = P(i - 1), p1 = P(i), p2 = P(i + 1), p3 = P(i + 2);
    d += ` C${nbc(p1[0] + (p2[0] - p0[0]) / 6)} ${nbc(p1[1] + (p2[1] - p0[1]) / 6)} ${nbc(p2[0] - (p3[0] - p1[0]) / 6)} ${nbc(p2[1] - (p3[1] - p1[1]) / 6)} ${nbc(p2[0])} ${nbc(p2[1])}`;
  }
  return d + (ferme ? " Z" : "");
}
/* ── T4 (t463) Contraction et dilatation : chaque segment entre deux sommets devient une cubique ; par rapport au
   centre de la boîte, les ancres se déplacent de −p/2 et les poignées (aux tiers du segment) de +p : dilatation
   (p > 0) bombée, contraction (p < 0) en étoile, comme Contraction et dilatation d'Illustrator. Rend le tracé lui-même. */
function _gonfler(p, B) {
  const cx = B.x + B.w / 2, cy = B.y + B.h / 2, k = p.pourcent / 100;
  const vers = ([x, y], f) => `${nbc(cx + (x - cx) * f)} ${nbc(cy + (y - cy) * f)}`;
  return { ligne: (l) => {
    const q = l.ferme ? l.points.concat([l.points[0]]) : l.points;
    let d = "M" + vers(q[0], 1 - k / 2);
    for (let i = 1; i < q.length; i++) {
      const a = q[i - 1], b = q[i];
      const h1 = [a[0] + (b[0] - a[0]) / 3, a[1] + (b[1] - a[1]) / 3], h2 = [a[0] + 2 * (b[0] - a[0]) / 3, a[1] + 2 * (b[1] - a[1]) / 3];
      d += ` C${vers(h1, 1 + k)} ${vers(h2, 1 + k)} ${vers(b, 1 - k / 2)}`;
    }
    return { d: d + (l.ferme ? " Z" : "") };
  } };
}
const _TRANSFORMEES = { enveloppe: _enveloppe, distorsion: _distorsion, torsion: _torsion, rugosite: _rugosite, zigzag: _zigzag, gonfler: _gonfler };

/* ── T5 (t464) Pointes de flèche : sur chaque ligne OUVERTE, le trait raccourci de la longueur d'une pointe pleine et
   des pointes orientées selon la tangente du bout (taille proportionnelle à l'épaisseur du trait × échelle) ── */
// la polyligne privée de `L` px à partir de son début (depuisFin = false) ou de sa fin
function _raccourcir(q, L, depuisFin) {
  const p = depuisFin ? q.slice().reverse() : q.slice();
  let reste = L;
  while (p.length > 1) {
    const [ax, ay] = p[0], [bx, by] = p[1], d = Math.hypot(bx - ax, by - ay);
    if (d > reste) { p[0] = [ax + (bx - ax) * reste / d, ay + (by - ay) * reste / d]; break; }
    reste -= d; p.shift();
  }
  return depuisFin ? p.reverse() : p;
}
function _pointe(style, bout, t, w, couleur, id) {
  // bout : le point d'extrémité ; t : la tangente unitaire vers l'extérieur ; n : la normale
  const n = [-t[1], t[0]], at = (a, b) => [bout[0] + t[0] * a + n[0] * b, bout[1] + t[1] * a + n[1] * b];
  const ecr = (ps, ferme) => "M" + ps.map(([x, y]) => `${nbc(x)} ${nbc(y)}`).join(" L") + (ferme ? " Z" : "");
  const plein = { fond: couleur, contour: "none" }, trait = { fond: "none", contour: couleur, epaisseur: w };
  if (style === "triangle") return { id, type: "path", d: ecr([at(0, 0), at(-3 * w, 1.25 * w), at(-3 * w, -1.25 * w)], true), style: plein };
  if (style === "ouverte") return { id, type: "path", d: ecr([at(-3 * w, 1.25 * w), at(0, 0), at(-3 * w, -1.25 * w)], false), style: trait };
  if (style === "carre") return { id, type: "path", d: ecr([at(-1.5 * w, -1.5 * w), at(1.5 * w, -1.5 * w), at(1.5 * w, 1.5 * w), at(-1.5 * w, 1.5 * w)], true), style: plein };
  if (style === "barre") return { id, type: "path", d: ecr([at(0, -2 * w), at(0, 2 * w)], false), style: trait };
  return { id, type: "ellipse", cx: bout[0], cy: bout[1], rx: 1.5 * w, ry: 1.5 * w, style: plein };   // cercle
}
function _resultatPointes(gid, F, p, cache) {
  const out = [];
  let k = 0;
  const neuf = () => `${gid}_d${++k}`;
  for (const f of F) {
    const ouvertes = f.lignes.filter((l) => !l.ferme && l.points.length >= 2);
    if (!ouvertes.length) continue;
    const w = (Number(f.style.epaisseur) > 0 ? Number(f.style.epaisseur) : 1) * p.echelle / 100;
    const couleur = typeof f.style.contour === "string" && f.style.contour !== "none" ? f.style.contour : "#000000";
    const traits = [], pointes = [];
    for (const l of ouvertes) {
      let q = l.points;
      const tan = (a, b) => { const d = Math.hypot(a[0] - b[0], a[1] - b[1]) || 1; return [(a[0] - b[0]) / d, (a[1] - b[1]) / d]; };
      const bouts = [["debut", q[0], tan(q[0], q[1])], ["fin", q[q.length - 1], tan(q[q.length - 1], q[q.length - 2])]];
      for (const [cote, bout, t] of bouts) {
        const st = p[cote];
        if (st === "aucune") continue;
        if (st === "triangle") q = _raccourcir(q, 3 * w, cote === "fin");   // la pointe pleine prend la place du bout du trait
        pointes.push([st, bout, t]);
      }
      traits.push("M" + q.map(([x, y]) => `${nbc(x)} ${nbc(y)}`).join(" L"));
    }
    out.push({ id: neuf(), type: "path", d: traits.join(" "), style: _cloner(f.style), genere: true });
    for (const [st, bout, t] of pointes) out.push({ ..._pointe(st, bout, t, w, couleur, neuf()), genere: true });
  }
  if (!out.length) throw new Error(T("vectorlab.deformer.ouvert"));
  if (cache) for (const o of out) o.cache = true;
  return out;
}

/* ── le résultat ── */
function _resultat(gid, source, effet, params, cache) {
  const F = _feuilles(source);
  if (!F.length) throw new Error(T("vectorlab.deformer.sans_geometrie"));
  if (effet === "pointes") return _resultatPointes(gid, F, params, cache);
  const B = _boite(F);
  // le pas grandit sur un très grand dessin, pour rester sous POINTS_MAX points
  const pas = Math.max(PAS_MAX, (2 * (B.w + B.h) * F.length) / POINTS_MAX);
  const tr = _TRANSFORMEES[effet](params, B);
  let ni = 0;
  return F.map((f, k) => {
    const d = f.lignes.map((l) => {
      // une fonction de point (enveloppe, distorsion, torsion) ou un traitement de ligne (rugosité, zigzag)
      const res = typeof tr === "function" ? { points: _subdiviser(l, pas).map(tr), lisse: false } : tr.ligne(l, ni++);
      if (res.d !== undefined) return res.d;           // un effet qui écrit son tracé (contraction et dilatation)
      const { points: q, lisse } = res;
      if (q.some(([x, y]) => !Number.isFinite(x) || !Number.isFinite(y))) throw new Error(T("vectorlab.deformer.sans_geometrie"));
      if (lisse) return _dLisse(q, l.ferme);
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
