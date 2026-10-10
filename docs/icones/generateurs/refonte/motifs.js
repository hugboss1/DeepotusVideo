// Motifs partagés de la suite « Deepotus Glyph » (CHARTE.md). Un même objet = un même dessin partout.
//
// ─── Contrat ───────────────────────────────────────────────────────────────────────────────────────────
// • Chaque motif est une fonction `M.nom(o)` qui renvoie une chaîne `d` (sous-chemins fermés, à mettre dans
//   un path `fill-rule="evenodd"`). Les valeurs par défaut de `o` donnent le motif en PLEINE TAILLE dans la
//   grille 24 (zone utile 2–22) ; on le réduit ou le déplace par ses paramètres de position et de taille.
//   Les épaisseurs restent ABSOLUES (≥ 2) quand on réduit : c'est voulu, la lisibilité à 16 px prime.
// • `o.trou = g` (ex. 1.5) : au lieu du dessin, renvoie sa SILHOUETTE PLEINE dilatée de g, à soustraire
//   d'un autre élément (réserve de la règle du monochrome). Ex. : M.moins(support, M.loupe({trou: 1.5})).
// • `o.partie` (motifs à deux tons) : choisit une partie nommée (listée dans la doc du motif) pour la
//   poser à un autre ton ; sans `partie`, le motif entier en un seul ton (parties déjà séparées par 1,6).
// • Le plus simple pour une icône à deux tons : `M.icone([{d: sujet}, {d: support, op: .38}])` — les
//   calques sont listés DU HAUT VERS LE BAS ; chaque calque est automatiquement évidé de la silhouette
//   dilatée (réserve 1,5 ; 1,4 pour un badge) de tout ce qui est au-dessus. Renvoie le SVG complet.
// • Booléens exacts (Martinez, MIT, vendu par le Vectorlab) : M.union, M.moins, M.inter, M.remplir,
//   M.dilater, M.eroder, M.arrondir. Ils aplatissent les arcs (polylignes au dixième) : à n'employer
//   que quand le evenodd simple ne suffit pas (un trou qui DÉBORDE de la forme se remplirait en evenodd).
// ───────────────────────────────────────────────────────────────────────────────────────────────────────
"use strict";
const G = require("./geo.js");
const MARTINEZ = "C:/Users/olivi/DeepotusVideo/frontend/vectorlab/vendor/martinez.umd.js";
const martinez = require(MARTINEZ);

const r1 = G.r1, f = (...a) => a.map(r1).join(" ");

// ── Correctif de geo.js (en mémoire, sans toucher au fichier) ─────────────────────────────────────────
// geo.pill() trace ses bouts avec le mauvais sens de balayage (sweep 1 au lieu de 0) : les bouts sont CREUX
// (pilule en « os ») et une pilule courte disparaît presque ; geo.check() en hérite. Charger motifs.js
// remplace G.pill et G.check par la version juste pour tout le processus (cache de require partagé).
function pill(x1, y1, x2, y2, w) {
  const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1, nx = -dy / L * w / 2, ny = dx / L * w / 2, r = w / 2;
  return `M${f(x1 + nx, y1 + ny)}L${f(x2 + nx, y2 + ny)}A${f(r, r)} 0 0 0 ${f(x2 - nx, y2 - ny)}L${f(x1 - nx, y1 - ny)}A${f(r, r)} 0 0 0 ${f(x1 + nx, y1 + ny)}Z`;
}
function check(x, y, s, w = 2.6) {
  const p1 = [x + s * .12, y + s * .55], p2 = [x + s * .4, y + s * .82], p3 = [x + s * .9, y + s * .22];
  return pill(p1[0], p1[1], p2[0], p2[1], w) + pill(p2[0], p2[1], p3[0], p3[1], w);
}
G.pill = pill; G.check = check;
const RES = 1.5;      // réserve monochrome (CHARTE §3 : 1,4–1,6)
const RES_BADGE = 1.4; // réserve d'un badge (CHARTE §4)
const E = 2.4;        // épaisseur courante d'un contour plein (≥ 2)
const RAD = Math.PI / 180;

// ═════════════════════════════ 1. Chemins : lecture, transformation, aplatissement ═════════════════════
/** Lit un `d` (M L H V A C Q Z, absolus ou relatifs) → liste de commandes absolues. */
function lire(d) {
  const t = d.match(/[MLHVACQZmlhvacqz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?/g) || [];
  const out = []; let i = 0, cmd = "", X = 0, Y = 0, X0 = 0, Y0 = 0;
  const n = () => +t[i++];
  while (i < t.length) {
    if (/[a-z]/i.test(t[i])) cmd = t[i++];
    const rel = cmd === cmd.toLowerCase(), C = cmd.toUpperCase(), ox = rel ? X : 0, oy = rel ? Y : 0;
    if (C === "Z") { out.push({ c: "Z" }); X = X0; Y = Y0; continue; }
    if (C === "M") { X = n() + ox; Y = n() + oy; X0 = X; Y0 = Y; out.push({ c: "M", p: [X, Y] }); cmd = rel ? "l" : "L"; continue; }
    if (C === "L") { X = n() + ox; Y = n() + oy; out.push({ c: "L", p: [X, Y] }); continue; }
    if (C === "H") { X = n() + ox; out.push({ c: "L", p: [X, Y] }); continue; }
    if (C === "V") { Y = n() + oy; out.push({ c: "L", p: [X, Y] }); continue; }
    if (C === "A") { const rx = n(), ry = n(), ro = n(), la = n(), sw = n(); X = n() + ox; Y = n() + oy;
      out.push({ c: "A", rx, ry, ro, la, sw, p: [X, Y] }); continue; }
    if (C === "C") { const a = [n() + ox, n() + oy], b = [n() + ox, n() + oy]; X = n() + ox; Y = n() + oy; out.push({ c: "C", a, b, p: [X, Y] }); continue; }
    if (C === "Q") { const a = [n() + ox, n() + oy]; X = n() + ox; Y = n() + oy; out.push({ c: "Q", a, p: [X, Y] }); continue; }
    throw new Error("commande non gérée : " + cmd);
  }
  return out;
}
/** Écrit une liste de commandes en `d` arrondi au dixième. */
function ecrire(cs) {
  return cs.map(k => k.c === "Z" ? "Z" : k.c === "A" ? `A${f(k.rx, k.ry, k.ro)} ${k.la} ${k.sw} ${f(...k.p)}`
    : k.c === "C" ? `C${f(...k.a, ...k.b, ...k.p)}` : k.c === "Q" ? `Q${f(...k.a, ...k.p)}` : k.c + f(...k.p)).join("");
}
/** Transformation affine SIMILITUDE (échelle uniforme, rotation, miroir) appliquée à un `d`, arcs compris.
 *  o = {k=1, rot=0 (degrés, horaire), cx=12, cy=12 (centre de rotation/échelle), dx=0, dy=0, miroir=false (axe vertical)} */
function placer(d, o = {}) {
  const k = o.k ?? 1, a = (o.rot || 0) * RAD, cx = o.cx ?? 12, cy = o.cy ?? 12, mx = o.miroir ? -1 : 1;
  const c = Math.cos(a), s = Math.sin(a);
  const P = ([x, y]) => { let u = (x - cx) * mx * k, v = (y - cy) * k; return [cx + u * c - v * s + (o.dx || 0), cy + u * s + v * c + (o.dy || 0)]; };
  return ecrire(lire(d).map(q => q.c === "Z" ? q : q.c === "A"
    ? { ...q, rx: q.rx * k, ry: q.ry * k, ro: q.ro + (o.rot || 0), sw: mx < 0 ? 1 - q.sw : q.sw, p: P(q.p) }
    : { ...q, p: P(q.p), a: q.a && P(q.a), b: q.b && P(q.b) }));
}
function arcCentre(x1, y1, rx, ry, phi, fa, fs, x2, y2) { // SVG F.6.5 (rx = ry dans cette suite, phi ignoré si rx = ry)
  const cp = Math.cos(phi), sp = Math.sin(phi);
  const dx = (x1 - x2) / 2, dy = (y1 - y2) / 2, x1p = cp * dx + sp * dy, y1p = -sp * dx + cp * dy;
  let L = x1p * x1p / (rx * rx) + y1p * y1p / (ry * ry); if (L > 1) { rx *= Math.sqrt(L); ry *= Math.sqrt(L); }
  const num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p, den = rx * rx * y1p * y1p + ry * ry * x1p * x1p;
  let co = Math.sqrt(Math.max(0, num / den)); if (fa === fs) co = -co;
  const cxp = co * rx * y1p / ry, cyp = -co * ry * x1p / rx;
  const cx = cp * cxp - sp * cyp + (x1 + x2) / 2, cy = sp * cxp + cp * cyp + (y1 + y2) / 2;
  const ang = (ux, uy, vx, vy) => Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
  const t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry);
  let dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry);
  if (!fs && dt > 0) dt -= 2 * Math.PI; else if (fs && dt < 0) dt += 2 * Math.PI;
  return { cx, cy, rx, ry, t1, dt, cp, sp };
}
/** `d` → anneaux de points [[x,y]…] (arcs et courbes aplatis, flèche ≤ 0,02). */
function aplatir(d) {
  const rings = []; let cur = null, X = 0, Y = 0;
  for (const q of lire(d)) {
    if (q.c === "M") { if (cur && cur.length > 2) rings.push(cur); cur = [q.p.slice()]; }
    else if (q.c === "L") cur.push(q.p.slice());
    else if (q.c === "A") {
      if (!q.rx || !q.ry) { cur.push(q.p.slice()); }
      else { const A = arcCentre(X, Y, q.rx, q.ry, q.ro * RAD, q.la, q.sw, q.p[0], q.p[1]);
        const r = Math.max(A.rx, A.ry), step = 2 * Math.acos(Math.max(-1, 1 - 0.02 / r)), n = Math.max(2, Math.ceil(Math.abs(A.dt) / step));
        for (let i = 1; i <= n; i++) { const t = A.t1 + A.dt * i / n, ex = A.rx * Math.cos(t), ey = A.ry * Math.sin(t);
          cur.push(i === n ? q.p.slice() : [A.cp * ex - A.sp * ey + A.cx, A.sp * ex + A.cp * ey + A.cy]); } }
    } else if (q.c === "C" || q.c === "Q") {
      const n = 16;
      for (let i = 1; i <= n; i++) { const t = i / n, u = 1 - t;
        cur.push(q.c === "C" ? [u * u * u * X + 3 * u * u * t * q.a[0] + 3 * u * t * t * q.b[0] + t * t * t * q.p[0], u * u * u * Y + 3 * u * u * t * q.a[1] + 3 * u * t * t * q.b[1] + t * t * t * q.p[1]]
          : [u * u * X + 2 * u * t * q.a[0] + t * t * q.p[0], u * u * Y + 2 * u * t * q.a[1] + t * t * q.p[1]]); }
    } else if (q.c === "Z") { if (cur && cur.length > 2) rings.push(cur); cur = null; continue; }
    if (q.p) { X = q.p[0]; Y = q.p[1]; }
  }
  if (cur && cur.length > 2) rings.push(cur);
  return rings;
}

// ═════════════════════════════ 2. Booléens exacts (régions planes) ════════════════════════════════════
const ferme = r => { const a = r.slice(); const p = a[0], z = a[a.length - 1]; if (p[0] !== z[0] || p[1] !== z[1]) a.push(p.slice()); return a; };
const multi = g => !g || !g.length ? [] : typeof g[0][0][0] === "number" ? [g] : g; // Polygon → MultiPolygon
/** `d` (règle evenodd) → région Martinez (MultiPolygon). */
function region(d) {
  let acc = [];
  for (const r of aplatir(d)) { const p = [[ferme(r)]]; acc = acc.length ? multi(martinez.xor(acc, p)) : p; }
  return acc;
}
/** Région → `d`. Les calculs intermédiaires gardent 3 décimales (Martinez supporte mal les arêtes quasi
 *  confondues que créerait un arrondi précoce) ; l'arrondi au dixième se fait à la toute fin (M.fin, M.icone). */
function versD(mp, dec = 3) {
  const q = 10 ** dec, rr = v => Math.round(v * q) / q, fmt = (x, y) => `${rr(x)} ${rr(y)}`; let s = "";
  for (const poly of multi(mp)) for (const ring of poly) {
    let pts = ring.map(([x, y]) => [rr(x), rr(y)]);
    pts = pts.filter((p, i) => i === 0 || p[0] !== pts[i - 1][0] || p[1] !== pts[i - 1][1]);
    if (pts.length > 1 && pts[0][0] === pts[pts.length - 1][0] && pts[0][1] === pts[pts.length - 1][1]) pts.pop();
    let ok = true; while (ok && pts.length > 3) { ok = false;
      for (let i = 0; i < pts.length; i++) { const a = pts[(i + pts.length - 1) % pts.length], b = pts[i], c = pts[(i + 1) % pts.length];
        if (Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) < 1e-4) { pts.splice(i, 1); ok = true; break; } } }
    if (pts.length < 3) continue;
    let ar = 0; for (let i = 0; i < pts.length; i++) { const p = pts[i], r = pts[(i + 1) % pts.length]; ar += p[0] * r[1] - r[0] * p[1]; }
    if (Math.abs(ar / 2) < 0.12) continue; // éclat sans surface (artefact de calcul)
    s += "M" + pts.map(p => fmt(...p)).join("L") + "Z";
  }
  return s;
}
/** Arrondi final au dixième d'un `d` (texte), arcs conservés ; supprime les points répétés qu'il crée. */
function fin(d) {
  return d.replace(/-?\d*\.?\d+(?:e-?\d+)?/g, n => { const v = Math.round(+n * 10) / 10; return String(Object.is(v, -0) ? 0 : v); })
    .replace(/L(-?[\d.]+ -?[\d.]+)(?=L\1(?![\d.]))/g, "");
}
const R = x => typeof x === "string" ? region(x) : x;
const op = (fn, a, bs) => { let acc = R(a); for (const b of bs) { const rb = R(b); if (!rb.length) continue; acc = acc.length || fn !== martinez.diff ? multi(fn(acc.length ? acc : [], rb)) : acc; } return acc; };
/** Union de plusieurs `d`. */
function union(...ds) { ds = ds.filter(Boolean); if (!ds.length) return ""; let acc = R(ds[0]); for (const b of ds.slice(1)) { const rb = R(b); if (rb.length) acc = acc.length ? multi(martinez.union(acc, rb)) : rb; } return versD(acc); }
/** a privé de b, c… */
function moins(a, ...bs) { let acc = R(a); for (const b of bs.filter(Boolean)) { const rb = R(b); if (rb.length && acc.length) acc = multi(martinez.diff(acc, rb)); } return versD(acc); }
/** Intersection. */
function inter(a, b) { const ra = R(a), rb = R(b); return ra.length && rb.length ? versD(multi(martinez.intersection(ra, rb))) : ""; }
/** Silhouette pleine : bouche tous les trous. */
function remplir(d) { const mp = R(d); let acc = []; for (const p of multi(mp)) { const o = [[p[0]]]; acc = acc.length ? multi(martinez.union(acc, o)) : o; } return versD(acc); }
function pillPts(x1, y1, x2, y2, r) { // pilule aplatie (Minkowski d'un segment par un disque)
  const a = Math.atan2(y2 - y1, x2 - x1), n = Math.max(6, Math.ceil(Math.PI / (2 * Math.acos(Math.max(-1, 1 - 0.02 / r))))), pts = [];
  for (let i = 0; i <= n; i++) { const t = a + Math.PI / 2 + Math.PI * i / n; pts.push([x1 + r * Math.cos(t), y1 + r * Math.sin(t)]); }
  for (let i = 0; i <= n; i++) { const t = a - Math.PI / 2 + Math.PI * i / n; pts.push([x2 + r * Math.cos(t), y2 + r * Math.sin(t)]); }
  return [[ferme(pts)]];
}
function bords(mp, g) { // union de rectangles (un par bord) et de disques (un par sommet) : Minkowski du contour par un disque
  // Les disques sont des polygones CIRCONSCRITS et tournés d'un angle propre à chaque sommet : aucun point ne
  // coïncide avec un coin de rectangle (Martinez supporte mal les arêtes confondues).
  const parts = []; let k = 0;
  for (const poly of multi(mp)) for (const ring of poly) for (let i = 0; i + 1 < ring.length; i++) {
    const [x1, y1] = ring[i], [x2, y2] = ring[i + 1], L = Math.hypot(x2 - x1, y2 - y1); if (L < 1e-6) continue;
    const nx = -(y2 - y1) / L * g, ny = (x2 - x1) / L * g;
    parts.push([[ferme([[x1 + nx, y1 + ny], [x2 + nx, y2 + ny], [x2 - nx, y2 - ny], [x1 - nx, y1 - ny]])]]);
    const n = Math.max(12, Math.ceil(Math.PI / Math.acos(Math.max(-1, 1 - 0.02 / g)))), rc = g / Math.cos(Math.PI / n), off = 0.37 + 0.61 * (k++ % 7);
    const c = []; for (let j = 0; j < n; j++) { const t = off + 2 * Math.PI * j / n; c.push([x1 + rc * Math.cos(t), y1 + rc * Math.sin(t)]); }
    parts.push([[ferme(c)]]);
  }
  let acc = [];
  for (const p of parts) acc = acc.length ? multi(martinez.union(acc, p)) : p;
  return acc;
}
/** Dilatation exacte (Minkowski par un disque de rayon g) : angles saillants arrondis au rayon g. */
function dilater(d, g) { const mp = R(d); if (!mp.length || !g) return versD(mp); return versD(multi(martinez.union(mp, bords(mp, g)))); }
/** Érosion (inverse de la dilatation). */
function eroder(d, g) { const mp = R(d); if (!mp.length || !g) return versD(mp); return versD(multi(martinez.diff(mp, bords(mp, g)))); }
/** Arrondit les angles saillants au rayon r (ouverture morphologique). */
function arrondir(d, r) { return dilater(eroder(d, r), r); }
/** Contour de réserve d'un dessin : silhouette pleine dilatée de g. */
function reserve(d, g = RES) { return dilater(remplir(d), g); }
/** Aire d'un `d` (règle evenodd) — utile aux contrôles. */
function aire(d) { let s = 0; for (const p of multi(R(d))) p.forEach((ring, i) => { let a = 0; for (let j = 0; j + 1 < ring.length; j++) a += ring[j][0] * ring[j + 1][1] - ring[j + 1][0] * ring[j][1]; s += (i ? -1 : 1) * Math.abs(a / 2); }); return s; }

/** Empile des formes d'UN MÊME TON (liste du haut vers le bas) : chacune est évidée de la réserve g des
 *  précédentes, puis tout est réuni. Sert à séparer les parties d'un motif (onglet/dossier, couvercle/cuve…). */
function empiler(ds, g = 1.6) {
  let cache = "", out = [];
  for (const d of ds.filter(Boolean)) { out.push(cache ? moins(d, cache) : d); cache = cache ? union(cache, reserve(d, g)) : reserve(d, g); }
  return out.length === 1 ? out[0] : union(...out);
}
/** Fabrique l'icône finale. calques = [{d, op: 1|.38, reserve?: 1.5, colle?: false}] DU HAUT VERS LE BAS.
 *  Chaque calque est privé de la silhouette dilatée de ceux du dessus (règle du monochrome) ; `colle: true`
 *  soude le calque à celui du dessous sans réserve. Renvoie le texte SVG (via G.svg). */
function icone(calques) {
  let cache = ""; const parts = [];
  for (const c of calques.filter(c => c && c.d)) {
    const d = cache ? moins(c.d, cache) : c.d;
    if (d) parts.push({ d: fin(d), op: c.op === .38 ? .38 : 1, evenodd: true });
    const z = c.colle ? remplir(c.d) : reserve(c.d, c.reserve ?? RES);
    cache = cache ? union(cache, z) : z;
  }
  return G.svg(parts.reverse());
}
// fabrique commune : applique `trou` / `partie`
function sortie(o, parties, tout) {
  const d = o.partie ? parties[o.partie] : (tout ?? Object.values(parties).filter(Boolean).join(""));
  if (d === undefined) throw new Error("partie inconnue : " + o.partie + " (" + Object.keys(parties).join(", ") + ")");
  return o.trou ? reserve(d, o.trou) : d;
}

// ═════════════════════════════ 3. Primitives complémentaires de geo.js ═════════════════════════════════
const pt = (cx, cy, r, deg) => [cx + r * Math.cos(deg * RAD), cy + r * Math.sin(deg * RAD)];
/** Bande en arc de cercle à bouts ronds (anse, onde, flèche courbe) : centre, rayon médian r, épaisseur e,
 *  de a0 à a1 en degrés (0 = droite, sens horaire). */
function arc(cx, cy, r, e, a0, a1) {
  const ro = r + e / 2, ri = r - e / 2, h = e / 2, big = Math.abs(a1 - a0) > 180 ? 1 : 0, sw = a1 > a0 ? 1 : 0;
  const [p0, p1, p2, p3] = [pt(cx, cy, ro, a0), pt(cx, cy, ro, a1), pt(cx, cy, ri, a1), pt(cx, cy, ri, a0)];
  return `M${f(...p0)}A${f(ro, ro)} 0 ${big} ${sw} ${f(...p1)}A${f(h, h)} 0 0 ${sw} ${f(...p2)}A${f(ri, ri)} 0 ${big} ${1 - sw} ${f(...p3)}A${f(h, h)} 0 0 ${sw} ${f(...p0)}Z`;
}
/** Ellipse pleine. */
function ellipse(cx, cy, rx, ry) { return `M${f(cx - rx, cy)}A${f(rx, ry)} 0 1 0 ${f(cx + rx, cy)}A${f(rx, ry)} 0 1 0 ${f(cx - rx, cy)}Z`; }
/** Rectangle à rayons distincts [hg, hd, bd, bg]. */
function rectR(x, y, w, h, [a, b, c, d]) {
  const A = (r, x2, y2) => r ? `A${f(r, r)} 0 0 1 ${f(x2, y2)}` : `L${f(x2, y2)}`;
  return `M${f(x + a, y)}H${r1(x + w - b)}${A(b, x + w, y + b)}V${r1(y + h - c)}${A(c, x + w - c, y + h)}H${r1(x + d)}${A(d, x, y + h - d)}V${r1(y + a)}${A(a, x + a, y)}Z`;
}
/** Polygone dont chaque angle est arrondi au rayon r (arcs exacts, polygone convexe ou non). */
function polyR(pts, r = 0.8) {
  if (!r) return G.poly(pts);
  const n = pts.length; let s = "";
  for (let i = 0; i < n; i++) {
    const p = pts[i], a = pts[(i + n - 1) % n], b = pts[(i + 1) % n];
    const u = [a[0] - p[0], a[1] - p[1]], v = [b[0] - p[0], b[1] - p[1]], lu = Math.hypot(...u), lv = Math.hypot(...v);
    const th = Math.acos(Math.max(-1, Math.min(1, (u[0] * v[0] + u[1] * v[1]) / (lu * lv))));
    const t = Math.min(r / Math.tan(th / 2), lu / 2, lv / 2), rr = t * Math.tan(th / 2);
    const p1 = [p[0] + u[0] / lu * t, p[1] + u[1] / lu * t], p2 = [p[0] + v[0] / lv * t, p[1] + v[1] / lv * t];
    const sw = (u[0] * v[1] - u[1] * v[0]) < 0 ? 1 : 0;
    s += (i ? "L" : "M") + f(...p1) + `A${f(rr, rr)} 0 0 ${sw} ${f(...p2)}`;
  }
  return s + "Z";
}

/** Union équilibrée (diviser pour régner) d'une liste de régions Martinez — rapide et stable. */
function unionListe(rs) { rs = rs.filter(r => r.length); if (!rs.length) return []; while (rs.length > 1) { const n = [];
  for (let i = 0; i < rs.length; i += 2) n.push(i + 1 < rs.length ? multi(martinez.union(rs[i], rs[i + 1])) : rs[i]); rs = n; } return rs[0]; }
const disque = (x, y, r, off = 0) => { const n = Math.max(12, Math.ceil(Math.PI / Math.acos(Math.max(-1, 1 - 0.02 / r)))), rc = r / Math.cos(Math.PI / n), c = [];
  for (let j = 0; j < n; j++) { const t = off + 2 * Math.PI * j / n; c.push([x + rc * Math.cos(t), y + rc * Math.sin(t)]); } return [[ferme(c)]]; };
/** Trait épais à bouts ronds le long d'une polyligne (pts) ; w = épaisseur fixe ou fonction w(t), t ∈ [0,1]
 *  (effilé). Union de trapèzes et de disques (robuste même dans les boucles serrées). Renvoie un `d`. */
function trait(pts, w = 2.4) {
  const W = typeof w === "function" ? w : () => w, n = pts.length, L = [0];
  for (let i = 1; i < n; i++) L.push(L[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const h = i => W(L[i] / (L[n - 1] || 1)) / 2, parts = [];
  for (let i = 0; i < n; i++) {
    parts.push(disque(pts[i][0], pts[i][1], h(i), 0.37 + 0.61 * (i % 7)));
    if (i + 1 < n) { const [x1, y1] = pts[i], [x2, y2] = pts[i + 1], l = Math.hypot(x2 - x1, y2 - y1); if (l < 1e-6) continue;
      const nx = -(y2 - y1) / l, ny = (x2 - x1) / l, a = h(i) * 0.999, b = h(i + 1) * 0.999;
      parts.push([[ferme([[x1 + nx * a, y1 + ny * a], [x2 + nx * b, y2 + ny * b], [x2 - nx * b, y2 - ny * b], [x1 - nx * a, y1 - ny * a]])]]); }
  }
  return versD(unionListe(parts));
}
/** Courbe lissée (Catmull-Rom centripète simplifiée) passant par des points de contrôle → polyligne dense. */
function lisse(ctrl, pas = 12) {
  const P = [ctrl[0], ...ctrl, ctrl[ctrl.length - 1]], out = [];
  for (let i = 1; i < P.length - 2; i++) for (let k = 0; k < pas; k++) { const t = k / pas, t2 = t * t, t3 = t2 * t;
    out.push([0, 1].map(j => 0.5 * (2 * P[i][j] + (-P[i - 1][j] + P[i + 1][j]) * t + (2 * P[i - 1][j] - 5 * P[i][j] + 4 * P[i + 1][j] - P[i + 2][j]) * t2 + (-P[i - 1][j] + 3 * P[i][j] - 3 * P[i + 1][j] + P[i + 2][j]) * t3))); }
  out.push(ctrl[ctrl.length - 1]); return out;
}

// ═════════════════════════════ 4. Motifs ═══════════════════════════════════════════════════════════════
const M = {};

// ── Contenants, documents ────────────────────────────────────────────────────────────────────────────
/** dossier — chemise à onglet : bande d'onglet au dos + rabat avant séparé de 1,6 (fermé) ou incliné (ouvert). parties : dos, rabat. */
M.dossier = (o = {}) => {
  const { x = 2, y = 3.5, w = 20, h = 17, ouvert = false } = o, tw = Math.max(5.6, w * 0.4), top = y + 2.2;
  const dos = `M${f(x, y + 1.4)}A1.4 1.4 0 0 1 ${f(x + 1.4, y)}H${r1(x + tw - 1.2)}L${f(x + tw + 1, top)}H${r1(x + w - 1.4)}A1.4 1.4 0 0 1 ${f(x + w, top + 1.4)}V${r1(y + h - 1.4)}A1.4 1.4 0 0 1 ${f(x + w - 1.4, y + h)}H${r1(x + 1.4)}A1.4 1.4 0 0 1 ${f(x, y + h - 1.4)}Z`;
  const rabat = ouvert ? polyR([[x + 3.4, y + 7.4], [x + w + 0.6, y + 7.4], [x + w - 2.6, y + h], [x, y + h]], 1.2)
    : G.rect(x, y + 6, w, h - 6, 1.4);
  const d = empiler([rabat, dos], 1.6), r = moins(dos, reserve(rabat, 1.6));
  return sortie(o, { dos: r, rabat }, d);
};
/** feuille — page portrait à coin corné : l'oreille est un triangle séparé du corps par une réserve en L ; lignes de texte évidées en option (o.lignes = n). parties : corps, oreille. */
M.feuille = (o = {}) => {
  const { x = 4, y = 2, w = 16, h = 20, coin = 5.6, lignes = 0 } = o;
  const corps = `M${f(x + 1.4, y)}H${r1(x + w - coin)}L${f(x + w, y + coin)}V${r1(y + h - 1.4)}A1.4 1.4 0 0 1 ${f(x + w - 1.4, y + h)}H${r1(x + 1.4)}A1.4 1.4 0 0 1 ${f(x, y + h - 1.4)}V${r1(y + 1.4)}A1.4 1.4 0 0 1 ${f(x + 1.4, y)}Z`;
  const oreille = G.poly([[x + w - coin, y], [x + w - coin, y + coin], [x + w, y + coin]]);
  let c = moins(corps, reserve(oreille, 1.6));
  for (let i = 0; i < lignes; i++) { const ly = y + coin + 3.4 + i * 3.6; if (ly + 1.8 > y + h - 2.2) break;
    c = moins(c, G.rect(x + 2.4, ly, (i === lignes - 1 ? 0.55 : 1) * (w - 4.8), 1.8, 0.9)); }
  return sortie(o, { corps: c, oreille }, union(c, oreille));
};
/** image — cadre paysage (anneau ou plaque pleine si o.plein) contenant une montagne à deux pics et un soleil. parties : cadre, paysage. */
M.image = (o = {}) => {
  const { x = 2, y = 4, w = 20, h = 16, plein = false } = o, e = 2.2, g = 1.6, ix = x + e + g, iy = y + e + g, iw = w - 2 * (e + g), ih = h - 2 * (e + g);
  const cadre = plein ? G.rect(x, y, w, h, 1.4) : G.rect(x, y, w, h, 1.4) + G.rect(x + e, y + e, w - 2 * e, h - 2 * e, 0.6);
  const base = iy + ih, sr = Math.max(1.4, Math.min(2.2, ih * 0.2));
  const paysage = union(polyR([[ix, base], [ix + iw * 0.34, iy + ih * 0.3], [ix + iw * 0.56, iy + ih * 0.62], [ix + iw * 0.7, iy + ih * 0.46], [ix + iw, base]], 0.6),
    G.rect(ix, base - 0.8, iw, 0.8)) + G.circle(ix + iw - sr, iy + sr, sr);
  return sortie(o, { cadre, paysage });
};
/** pellicule — bande de film à perforations ouvertes sur les bords (dents 2 / crans 1,6) et cases évidées ; o.horizontal pour la coucher. */
M.pellicule = (o = {}) => {
  const { x = 5, y = 2, w = 14, h = 20, cases = 3, horizontal = false } = o;
  const W = horizontal ? h : w, H = horizontal ? w : h; // dessin vertical dans (0,0,W,H) puis placé
  let d = G.rect(0, 0, W, H, 1);
  const n = Math.floor((H - 2) / 3.6); const y0 = (H - (n * 3.6 - 2)) / 2;
  for (let i = 0; i < n; i++) { const yy = y0 + i * 3.6; d = moins(d, G.rect(-1, yy, 2.6, 1.6), G.rect(W - 1.6, yy, 2.6, 1.6)); }
  const cx0 = 3.6, cw = W - 7.2, ch = (H - 2 * 2 - (cases - 1) * 2) / cases;
  for (let i = 0; i < cases; i++) d = moins(d, G.rect(cx0, 2 + i * (ch + 2), cw, ch, 0.6));
  d = horizontal ? placer(d, { rot: -90, cx: 0, cy: 0, dx: x, dy: y + w }) : placer(d, { dx: x, dy: y, cx: 0, cy: 0 });
  return sortie(o, { tout: d }, d);
};
/** clap — clap de cinéma : corps évidé d'une bande rayée + barre supérieure levée, rayée en biais. parties : barre, corps. */
M.clap = (o = {}) => {
  const { x = 2, y = 2.5, w = 20, h = 19 } = o, top = y + 7;
  let corps = G.rect(x, top, w, y + h - top, 1.4);
  let bande = G.rect(x, y + 3, w, 3.2, 0.8); // barre levée (avant rotation)
  for (let i = 0; i < 4; i++) { const sx = x + 3 + i * 4.6; bande = moins(bande, G.poly([[sx, y + 2], [sx + 2, y + 2], [sx + 0.2, y + 7], [sx - 1.8, y + 7]])); }
  const barre = placer(bande, { rot: -14, cx: x + 1, cy: y + 6.2 });
  for (let i = 0; i < 4; i++) { const sx = x + 3 + i * 4.6; corps = moins(corps, G.poly([[sx + 1.4, top + 0.01], [sx + 3, top], [sx + 1.6, top + 3.2], [sx, top + 3.2]])); }
  corps = moins(corps, G.rect(x - 1, top + 3.2, w + 2, 1.6));
  return sortie(o, { barre, corps }, empiler([barre, corps], 1.6));
};
/** bac — bac ouvert en U (importer, exporter, vider) : murs de 2,6, fond arrondi. */
M.bac = (o = {}) => {
  const { x = 2.5, y = 13, w = 19, h = 9, e = 2.6 } = o;
  const d = `M${f(x, y)}H${r1(x + e)}V${r1(y + h - e)}H${r1(x + w - e)}V${r1(y)}H${r1(x + w)}V${r1(y + h - 1.6)}A1.6 1.6 0 0 1 ${f(x + w - 1.6, y + h)}H${r1(x + 1.6)}A1.6 1.6 0 0 1 ${f(x, y + h - 1.6)}Z`;
  return sortie(o, { tout: d }, d);
};
/** classeur — boîte d'archives à onglets décalés (projets). parties : onglets, corps. */
M.classeur = (o = {}) => {
  const { x = 2, y = 3, w = 20, h = 18 } = o, tw = (w - 2.8) / 3;
  const corps = G.rect(x, y + 5.6, w, h - 5.6, 1.4);
  const onglets = [0, 1, 2].map(i => rectR(x + 1.4 + i * tw, y + i * 1.2, tw - 0.6, 6 - i * 1.2 + 1, [1, 1, 0, 0])).join("");
  return sortie(o, { onglets: union(onglets), corps }, empiler([corps, union(onglets)], 1.6));
};

// ── Images, film, son ────────────────────────────────────────────────────────────────────────────────
/** onde — forme d'onde en barres arrondies (largeur 2,4, pas ≥ 4) ; o.hauteurs = fractions de h. parties : centre, bords. */
M.onde = (o = {}) => {
  const { x = 2, y = 3, w = 20, h = 18, hauteurs = [0.3, 0.62, 1, 0.5, 0.3], bw = 2.4 } = o, n = hauteurs.length, pas = (w - bw) / (n - 1), cy = y + h / 2;
  const barres = hauteurs.map((k, i) => G.rect(x + i * pas, cy - Math.max(bw, h * k) / 2, bw, Math.max(bw, h * k), bw / 2));
  return sortie(o, { centre: barres.slice(1, -1).join(""), bords: barres[0] + barres[n - 1] }, barres.join(""));
};
/** hautParleur — haut-parleur (aimant + pavillon) suivi de 0 à 2 ondes en arc. parties : corps, ondes. */
M.hautParleur = (o = {}) => {
  const { x = 2, cy = 12, s = 1, ondes = 2 } = o;
  const corps = polyR([[x, cy - 3.4 * s], [x + 3.6 * s, cy - 3.4 * s], [x + 9 * s, cy - 8 * s], [x + 9 * s, cy + 8 * s], [x + 3.6 * s, cy + 3.4 * s], [x, cy + 3.4 * s]], 0.8);
  const ar = [arc(x + 9 * s, cy, 4.4 * s, 2.4, -50, 50), arc(x + 9 * s, cy, 8.4 * s, 2.4, -55, 55)].slice(0, ondes).join("");
  return sortie(o, { corps, ondes: ar });
};
/** micro — micro de studio : capsule en pilule, étrier en U, pied et socle. parties : capsule, pied. */
M.micro = (o = {}) => {
  const { cx = 12, y = 2, s = 1 } = o;
  const capsule = G.rect(cx - 3.4 * s, y, 6.8 * s, 12 * s, 3.4 * s);
  const pied = arc(cx, y + 8.4 * s, 6.6 * s, 2.2, 0, 180) + G.rect(cx - 1.1, y + 15 * s, 2.2, 3.6 * s) + G.rect(cx - 4.4 * s, y + 18 * s, 8.8 * s, 2.2, 1.1);
  return sortie(o, { capsule, pied: union(pied) });
};
/** lecture — triangle de lecture aux angles arrondis, pointe à droite (o.dir = "gauche" pour le retourner). */
M.lecture = (o = {}) => {
  const { cx = 12.8, cy = 12, s = 16, dir = "droite" } = o, h = s * 0.866;
  let d = polyR([[cx - h / 3, cy - s / 2], [cx + 2 * h / 3, cy], [cx - h / 3, cy + s / 2]], 1);
  if (dir === "gauche") d = placer(d, { miroir: true, cx, cy });
  return sortie(o, { tout: d }, d);
};
/** camera — caméra de cinéma : boîtier, objectif conique, deux bobines au-dessus (o.bobines). parties : boitier, bobines. */
M.camera = (o = {}) => {
  const { x = 2, y = 3, s = 1, bobines = true } = o, by = y + (bobines ? 8 : 0) * s;
  const boitier = union(G.rect(x, by, 13 * s, 8.4 * s, 1.4), polyR([[x + 13 * s, by + 4.2 * s - 1.4], [x + 19.6 * s, by + 0.6 * s], [x + 19.6 * s, by + 7.8 * s], [x + 13 * s, by + 4.2 * s + 1.4]], 0.6));
  const bob = bobines ? G.circle(x + 3.4 * s, y + 3.6 * s, 3.4 * s) + G.circle(x + 10 * s, y + 3.6 * s, 3.4 * s) : "";
  return sortie(o, { boitier, bobines: bob }, bobines ? empiler([boitier, union(bob)], 1.6) : boitier);
};

// ── Volumes, matières ────────────────────────────────────────────────────────────────────────────────
/** cube — cube isométrique (hexagone) en trois faces séparées par des arêtes évidées de 1,4. parties : dessus, gauche, droite. */
M.cube = (o = {}) => {
  const { cx = 12, cy = 12, r = 10, arete = 1.4 } = o, P = a => pt(cx, cy, r, a), C = [cx, cy];
  const dessus = G.poly([P(-90), P(-30), C, P(-150)]), droite = G.poly([P(-30), P(30), P(90), C]), gauche = G.poly([P(-150), C, P(90), P(150)]);
  const cut = G.pill(cx, cy, ...P(-30), arete) + G.pill(cx, cy, ...P(-150), arete) + G.pill(cx, cy, ...P(90), arete);
  const k = d => moins(d, union(cut));
  return sortie(o, { dessus: k(dessus), gauche: k(gauche), droite: k(droite) }, moins(G.poly([P(-90), P(-30), P(30), P(90), P(150), P(-150)]), union(cut)));
};
/** sphere — sphère d'échantillon : disque, moitié droite pleine, ou disque à reflet évidé. parties : disque, moitie, gauche, reflet. */
M.sphere = (o = {}) => {
  const { cx = 12, cy = 12, r = 9.4 } = o;
  const disque = G.circle(cx, cy, r);
  const moitie = `M${f(cx, cy - r)}A${f(r, r)} 0 0 1 ${f(cx, cy + r)}Z`, gauche = `M${f(cx, cy + r)}A${f(r, r)} 0 0 1 ${f(cx, cy - r)}Z`;
  const reflet = moins(disque, arc(cx, cy, r * 0.62, 1.8, 195, 255));
  return sortie(o, { disque, moitie, gauche, reflet }, reflet);
};
/** pile — pile de plaques (calques, Bibliothèque) : plaque du haut entière, les autres en chevrons dessous. o.forme = "losange" | "parallelogramme". parties : dessus, dessous. */
M.pile = (o = {}) => {
  const { cx = 12, y = 2.6, w = 19, h = 10, n = 3, pas = 4.2, forme = "losange" } = o;
  const plaque = yy => forme === "losange" ? polyR([[cx, yy], [cx + w / 2, yy + h / 2], [cx, yy + h], [cx - w / 2, yy + h / 2]], 1)
    : polyR([[cx - w / 2 + h * 0.5, yy], [cx + w / 2, yy], [cx + w / 2 - h * 0.5, yy + h], [cx - w / 2, yy + h]], 0.8);
  const ps = Array.from({ length: n }, (_, i) => plaque(y + i * pas));
  const dessous = []; let cache = reserve(ps[0], 1.6);
  for (let i = 1; i < n; i++) { dessous.push(moins(ps[i], cache)); cache = union(cache, reserve(ps[i], 1.6)); }
  return sortie(o, { dessus: ps[0], dessous: union(...dessous) });
};
/** plaque — une plaque de calque en parallélogramme penché (unité des icônes de calques). */
M.plaque = (o = {}) => {
  const { cx = 12, cy = 12, w = 20, h = 9, r = 1 } = o;
  const d = polyR([[cx - w / 2 + h * 0.5, cy - h / 2], [cx + w / 2, cy - h / 2], [cx + w / 2 - h * 0.5, cy + h / 2], [cx - w / 2, cy + h / 2]], r);
  return sortie(o, { tout: d }, d);
};
/** damier — damier n × n (transparence, pixels, tuiles) : cases pleines alternées, coins soudés. */
M.damier = (o = {}) => {
  const { x = 3, y = 3, s = 18, n = 3, impair = false } = o, c = s / n; const cs = [];
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (((i + j) % 2 === 0) !== impair) cs.push(G.rect(x + j * c - 0.06, y + i * c - 0.06, c + 0.12, c + 0.12)); // recouvrement infime : coins non confondus
  const d = union(...cs); return sortie(o, { tout: d }, d);
};
/** grille — planche de rectangles arrondis en n colonnes × m lignes, gouttière g (vue grille, galerie, planche). */
M.grille = (o = {}) => {
  const { x = 2.5, y = 2.5, w = 19, h = 19, n = 2, m = 2, g = 2, r = 1.2 } = o, cw = (w - (n - 1) * g) / n, ch = (h - (m - 1) * g) / m; const cs = [];
  for (let i = 0; i < m; i++) for (let j = 0; j < n; j++) cs.push(G.rect(x + j * (cw + g), y + i * (ch + g), cw, ch, r));
  return sortie(o, { tout: cs.join("") }, cs.join(""));
};
/** graphe — graphe de nœuds du Studio : un nœud à gauche relié par des liens coudés à deux nœuds à droite. parties : noeuds, liens. */
M.graphe = (o = {}) => {
  const { x = 2, y = 3, w = 20, h = 18, n = 6.2 } = o, ly = y + h / 2, ry1 = y + n / 2, ry2 = y + h - n / 2, mx = x + w / 2;
  const noeuds = G.rect(x, ly - n / 2, n, n, 1.4) + G.rect(x + w - n, y, n, n, 1.4) + G.rect(x + w - n, y + h - n, n, n, 1.4);
  const liens = union(G.rect(x + n - 0.5, ly - 1.1, mx - x - n + 1.6, 2.2), G.rect(mx - 1.1, ry1 - 1.1, 2.2, ry2 - ry1 + 2.2),
    G.rect(mx - 1.1, ry1 - 1.1, x + w - n - mx + 1.6, 2.2), G.rect(mx - 1.1, ry2 - 1.1, x + w - n - mx + 1.6, 2.2));
  return sortie(o, { noeuds, liens }, empiler([noeuds, liens], 1.6));
};

// ── Outils de la main ───────────────────────────────────────────────────────────────────────────────
// Outils dessinés DEBOUT (pointe en bas, centre 12,12, longueur 20) puis inclinés : o.angle (défaut 45° :
// pointe en bas à gauche), o.k (échelle), o.dx/dy (décalage).
const incline = (d, o, a = 45) => placer(d, { rot: o.angle ?? a, k: o.k ?? 1, dx: o.dx || 0, dy: o.dy || 0 });
/** pinceau — pinceau : manche en pilule, virole, touffe en goutte pointue (séparée de la virole). parties : manche, touffe. */
M.pinceau = (o = {}) => {
  const manche = union(G.rect(10.7, 1, 2.6, 10, 1.3), G.rect(9.6, 9.6, 4.8, 3.6, 0.6));
  const touffe = `M${f(9.2, 14.8)}H14.8C14.8 18.6 13.4 21 12 23C10.6 21 9.2 18.6 9.2 14.8Z`;
  return sortie(o, { manche: incline(manche, o), touffe: incline(touffe, o) });
};
/** crayon — crayon : gomme de tête séparée, corps hexagonal, pointe conique à mine. parties : corps, tete. */
M.crayon = (o = {}) => {
  const tete = G.rect(9.6, 1, 4.8, 3.4, 1.2);
  const corps = `M9.6 6H14.4V16.6L12 22.4L9.6 16.6Z`;
  return sortie(o, { corps: incline(corps, o), tete: incline(tete, o) });
};
/** gomme — gomme en biais : pavé dont le tiers bas (la semelle) est séparé par une rainure. parties : corps, semelle. */
M.gomme = (o = {}) => {
  const corps = G.rect(8, 2, 8, 11.4, 1.2), semelle = G.rect(8, 15, 8, 6.4, 1.2);
  return sortie(o, { corps: incline(corps, o), semelle: incline(semelle, o) });
};
/** punaise — punaise de liège inclinée : tête, fût, collerette, aiguille pointue. */
M.punaise = (o = {}) => {
  const d = union(G.rect(7.6, 1.4, 8.8, 2.6, 1.2), G.rect(9.4, 3.4, 5.2, 6.6), polyR([[6.4, 10], [17.6, 10], [17.6, 12.6], [6.4, 12.6]], 1), `M11 12H13V20L12 22.6L11 20Z`);
  const r = incline(d, o, 40); return sortie(o, { tout: r }, r);
};
/** cle — clé horizontale : anneau évidé à gauche, tige, deux dents. */
M.cle = (o = {}) => {
  const { x = 2, cy = 12, s = 1 } = o;
  let d = union(G.circle(x + 5 * s, cy, 5 * s), G.rect(x + 8 * s, cy - 1.3, 12 * s, 2.6, 0.6), G.rect(x + 13.6 * s, cy, 2.4, 5 * s, 0.4), G.rect(x + 17.6 * s, cy, 2.4, 3.8 * s, 0.4));
  d = moins(d, G.circle(x + 4.6 * s, cy, 2 * s)); return sortie(o, { tout: d }, d);
};
/** loupe — loupe : anneau (épaisseur 2,4) et manche en pilule vers le bas à droite. parties : anneau, manche, lentille (intérieur, pour y découper + ou −). */
M.loupe = (o = {}) => {
  const { cx = 10, cy = 10, r = 7.6, e = 2.4 } = o, a = pt(cx, cy, r, 45);
  const anneau = G.ring(cx, cy, r, r - e), lentille = G.circle(cx, cy, r - e);
  const manche = G.pill(a[0] + 0.4, a[1] + 0.4, cx + r + 4.4, cy + r + 4.4, 3.2);
  return sortie(o, { anneau, manche, lentille }, union(anneau, manche));
};

// ── Sécurité, visibilité, temps ─────────────────────────────────────────────────────────────────────
/** cadenas — cadenas : corps à trou de serrure + anse en arc (fermée, ou pivotée vers la droite, jambe droite libre, si o.ouvert). parties : corps, anse. */
M.cadenas = (o = {}) => {
  const { cx = 12, y = 1.6, w = 16, h = 20.4, ouvert = false } = o, by = y + h * 0.46, ar = w * 0.3;
  const corps = moins(G.rect(cx - w / 2, by, w, y + h - by, 1.8), G.circle(cx, by + (y + h - by) * 0.42, 1.7), G.rect(cx - 0.8, by + (y + h - by) * 0.42, 1.6, 3.4, 0.6));
  const top = y + 1.2 + ar; // centre de l'arc ; ouvert : l'anse pivote vers la droite, jambe gauche dans le corps, jambe droite libre
  const ax = ouvert ? cx + ar * 0.9 : cx;
  const anse = ouvert ? union(arc(ax, top, ar, 2.4, 180, 360), G.rect(ax - ar - 1.2, top, 2.4, by - top + 0.6), G.rect(ax + ar - 1.2, top, 2.4, 1.4, 1.2))
    : union(arc(cx, top, ar, 2.4, 180, 360), G.rect(cx - ar - 1.2, top, 2.4, by - top + 0.6), G.rect(cx + ar - 1.2, top, 2.4, by - top + 0.6));
  return sortie(o, { corps, anse }, union(corps, anse));
};
/** oeil — œil en amande, iris évidé et pupille pleine ; o.barre ajoute une barre diagonale (masqué) avec réserve. parties : amande, barre. */
M.oeil = (o = {}) => {
  const { cx = 12, cy = 12, w = 21, h = 13, barre = false } = o, R0 = ((w / 2) ** 2 + (h / 2) ** 2) / h;
  const amande = moins(`M${f(cx - w / 2, cy)}A${f(R0, R0)} 0 0 1 ${f(cx + w / 2, cy)}A${f(R0, R0)} 0 0 1 ${f(cx - w / 2, cy)}Z`, G.circle(cx, cy, 3.6)) + G.circle(cx, cy, 1.8);
  if (!barre) return sortie(o, { amande });
  const b = G.pill(cx - 7.6, cy - 8.4, cx + 7.6, cy + 8.4, 2.6);
  return sortie(o, { amande: moins(amande, reserve(b, 1.5)), barre: b }, union(moins(amande, reserve(b, 1.5)), b));
};
/** horloge — horloge : cadran en anneau (ou disque plein si o.plein, aiguilles alors évidées) et deux aiguilles. parties : cadran, aiguilles. */
M.horloge = (o = {}) => {
  const { cx = 12, cy = 12, r = 10, e = 2.4, plein = false, h = -90, m = 0 } = o, la = plein ? r - 3 : r - e - 2.2, lb = la * 0.72;
  const aig = union(G.pill(cx, cy, ...pt(cx, cy, la, h), 2.4), G.pill(...pt(cx, cy, -0.4, m), ...pt(cx, cy, lb, m), 2.4)); // départs décalés : bouts non confondus
  const cadran = plein ? G.circle(cx, cy, r) : G.ring(cx, cy, r, r - e);
  return sortie(o, { cadran, aiguilles: aig }, plein ? moins(cadran, aig) : union(cadran, aig));
};
/** calendrier — calendrier mural : deux anneaux, bandeau d'en-tête plein, corps séparé (évidé d'une grille si o.grille). parties : anneaux, bandeau, corps. */
M.calendrier = (o = {}) => {
  const { x = 2.5, y = 1.6, w = 19, h = 20.4, grille = false } = o, hb = y + 7.2;
  const anneaux = G.rect(x + w * 0.28 - 1.1, y, 2.2, 5, 1.1) + G.rect(x + w * 0.72 - 1.1, y, 2.2, 5, 1.1);
  const bandeau = moins(rectR(x, y + 2.4, w, hb - y - 2.4, [1.4, 1.4, 0, 0]), reserve(anneaux, 1.2));
  let corps = rectR(x, hb + 1.6, w, y + h - hb - 1.6, [0, 0, 1.4, 1.4]);
  if (grille) { const cw = (w - 4.8 - 2 * 1.6) / 3, ch = (y + h - hb - 1.6 - 4.4 - 1.6) / 2;
    for (let i = 0; i < 2; i++) for (let j = 0; j < 3; j++) corps = moins(corps, G.rect(x + 2.4 + j * (cw + 1.6), hb + 1.6 + 2.2 + i * (ch + 1.6), cw, ch, 0.4)); }
  return sortie(o, { anneaux, bandeau, corps }, union(anneaux, bandeau, corps));
};
/** sablier — sablier : traverses haute et basse ; ampoules en contour de 2 avec le sable soudé aux parois (reste en haut, tas en bas). parties : cadre (traverses), verre (contour + sable). */
M.sablier = (o = {}) => {
  const { cx = 12, y = 1.8, w = 16, h = 20.4 } = o, b = 2.6, t = y + b + 1.6, B = y + h - b - 1.6, hw = w / 2 - 1.2, mid = (t + B) / 2;
  const ext = polyR([[cx - hw, t], [cx + hw, t], [cx + 1.3, mid], [cx + hw, B], [cx - hw, B], [cx - 1.3, mid]], 0.8);
  const paroi = moins(ext, eroder(ext, 2));
  const sable = union(inter(ext, G.rect(cx - w, t + (mid - t) * 0.5, 2 * w, mid - t)), inter(ext, G.poly([[cx, mid + (B - mid) * 0.25], [cx + w, B + 2], [cx - w, B + 2]])));
  const cadre = G.rect(cx - w / 2, y, w, b, 1.3) + G.rect(cx - w / 2, y + h - b, w, b, 1.3);
  return sortie(o, { cadre, verre: union(paroi, sable) });
};
/** cloche — cloche : robe galbée à lèvre évasée, bouton au sommet, battant séparé dessous. parties : robe, battant. */
M.cloche = (o = {}) => {
  const { cx = 12, y = 1.6, w = 19, s = 1 } = o, lip = y + 15.6 * s;
  const robe = union(`M${f(cx - 6.4 * s, lip)}V${r1(y + 9 * s)}C${f(cx - 6.4 * s, y + 4.6 * s, cx - 3.6 * s, y + 2.4 * s, cx, y + 2.4 * s)}C${f(cx + 3.6 * s, y + 2.4 * s, cx + 6.4 * s, y + 4.6 * s, cx + 6.4 * s, y + 9 * s)}V${r1(lip)}Z`,
    G.rect(cx - w / 2, lip - 0.4, w, 2.6, 1.3), G.rect(cx - 1.3, y, 2.6, 3.2, 1));
  const battant = `M${f(cx - 3, lip + 3.8)}H${r1(cx + 3)}A3 3 0 0 1 ${f(cx - 3, lip + 3.8)}Z`;
  return sortie(o, { robe, battant });
};

// ── Personnes, parole, monde ────────────────────────────────────────────────────────────────────────
/** buste — personne : tête ronde et épaules en dôme, séparées de 1,6. parties : tete, epaules. */
M.buste = (o = {}) => {
  const { cx = 12, y = 2, w = 18, h = 20 } = o, rt = h * 0.23, ty = y + rt, ey = ty + rt + 1.8, R0 = Math.min(w / 2, (y + h - ey) * 0.95);
  const tete = G.circle(cx, ty, rt);
  const epaules = `M${f(cx - w / 2, y + h - 1)}V${r1(ey + R0)}A${f(R0, R0)} 0 0 1 ${f(cx - w / 2 + R0, ey)}H${r1(cx + w / 2 - R0)}A${f(R0, R0)} 0 0 1 ${f(cx + w / 2, ey + R0)}V${r1(y + h - 1)}A1 1 0 0 1 ${f(cx + w / 2 - 1, y + h)}H${r1(cx - w / 2 + 1)}A1 1 0 0 1 ${f(cx - w / 2, y + h - 1)}Z`;
  return sortie(o, { tete, epaules });
};
/** bulle — bulle de dialogue : rectangle arrondi (o.forme "rect") ou ovale ("rond") avec queue en bas à gauche (o.queue "droite" pour l'inverser). */
M.bulle = (o = {}) => {
  const { x = 2, y = 3, w = 20, h = 15, forme = "rect", queue = "gauche" } = o;
  const corps = forme === "rond" ? ellipse(x + w / 2, y + h / 2, w / 2, h / 2) : G.rect(x, y, w, h, 3);
  const qx = queue === "gauche" ? x + w * 0.22 : x + w * 0.78, s = queue === "gauche" ? 1 : -1;
  const q = G.poly([[qx - 2.4 * s, y + h - 1.5], [qx + 3 * s, y + h - 1.5], [qx - 2.4 * s, y + h + 4.4]]);
  const d = union(corps, q); return sortie(o, { tout: d }, d);
};
/** globe — globe terrestre : disque découpé d'un méridien en ellipse et d'un équateur (fentes 1,6). */
M.globe = (o = {}) => {
  const { cx = 12, cy = 12, r = 10 } = o;
  const d = moins(G.circle(cx, cy, r), moins(ellipse(cx, cy, r * 0.48, r + 1), ellipse(cx, cy, r * 0.48 - 1.6, r - 1.6 + 1)), G.rect(cx - r - 1, cy - 0.8, 2 * r + 2, 1.6));
  return sortie(o, { tout: d }, d);
};
/** telephone — téléphone portrait : coque arrondie, écran évidé, ergot de haut-parleur. */
M.telephone = (o = {}) => {
  const { cx = 12, cy = 12, w = 12.4, h = 20.4 } = o;
  const d = G.rect(cx - w / 2, cy - h / 2, w, h, 2.4) + G.rect(cx - w / 2 + 2.2, cy - h / 2 + 3.6, w - 4.4, h - 7.2, 0.6);
  return sortie(o, { tout: d }, d);
};
/** ecran — moniteur : dalle (anneau, ou pleine si o.plein) et pied en T séparé. parties : dalle, pied. */
M.ecran = (o = {}) => {
  const { x = 2, y = 2.6, w = 20, h = 14, plein = false, pied = true } = o;
  const dalle = plein ? G.rect(x, y, w, h, 1.4) : G.rect(x, y, w, h, 1.4) + G.rect(x + 2.2, y + 2.2, w - 4.4, h - 4.4, 0.6);
  const p = pied ? union(G.rect(x + w / 2 - 1.3, y + h + 1, 2.6, 3), G.rect(x + w / 2 - w * 0.25, y + h + 3.4, w * 0.5, 2.4, 1.2)) : "";
  return sortie(o, { dalle, pied: p }, p ? empiler([dalle, p], 1.6) : dalle);
};
/** livre — livre ouvert : deux pages au bord de reliure plus bas, séparées par une gouttière de 1,6. parties : gauche, droite. */
M.livre = (o = {}) => {
  const { cx = 12, y = 3.6, w = 20, h = 17 } = o, pw = w / 2 - 0.8;
  const page = s => { const xo = cx - s * (w / 2), xi = cx - s * 0.8, sw = s > 0 ? 1 : 0;
    return `M${f(xo, y + 1.4)}A1.4 1.4 0 0 ${sw} ${f(xo + s * 1.4, y)}H${r1(xi - s * 1.6)}A1.6 1.6 0 0 ${sw} ${f(xi, y + 1.6)}V${r1(y + h)}C${f(xi - s * 1.2, y + h - 1.2, xi - s * 3, y + h - 1.6, xi - s * 4.4, y + h - 1.6)}H${r1(xo)}Z`; };
  void pw; return sortie(o, { gauche: page(1), droite: page(-1) });
};
/** livreFerme — livre fermé épais vu de face : couverture, dos séparé par une fente, bloc des pages évidé en bas (o.fermoir ajoute une patte sur la tranche). */
M.livreFerme = (o = {}) => {
  const { x = 3.5, y = 2, w = 17, h = 20, fermoir = false } = o;
  let d = moins(G.rect(x, y, w, h, 1.6), G.rect(x + 3.4, y - 1, 1.6, h + 2), rectR(x + 5, y + h - 4.2, w - 5 + 1, 1.8, [0.9, 0, 0, 0.9]));
  if (fermoir) d = moins(d, G.rect(x + w - 4.6, y + h * 0.36 - 1.6, 6, 6.4 + 1.6, 1)), d = union(d, G.rect(x + w - 3.2, y + h * 0.36, 4.4, 3.2, 1));
  return sortie(o, { tout: d }, d);
};

// ── Signes ──────────────────────────────────────────────────────────────────────────────────────────
/** etincelle — étincelle IA à quatre branches aux flancs incurvés, avec un éclat secondaire (o.eclat). parties : grande, eclat. */
M.etincelle = (o = {}) => {
  const { cx = 10.6, cy = 13.4, r = 8.6, eclat = true } = o;
  const st = (x, y, R) => { const k = R * 0.16; return `M${f(x, y - R)}Q${f(x + k, y - k, x + R, y)}Q${f(x + k, y + k, x, y + R)}Q${f(x - k, y + k, x - R, y)}Q${f(x - k, y - k, x, y - R)}Z`; };
  const grande = st(cx, cy, r), e = eclat ? st(cx + r * 0.95, cy - r * 0.95, r * 0.42) : "";
  return sortie(o, { grande, eclat: e }, eclat ? empiler([e, grande], 1.4) : grande);
};
/** eclair — éclair de Quick (réservé à Quick et à ses dérivés). */
M.eclair = (o = {}) => {
  const { k = 1, dx = 0, dy = 0 } = o;
  const d = placer(polyR([[14.2, 1.8], [5.2, 14.2], [10.8, 14.2], [9.4, 22.2], [18.8, 9.4], [13.2, 9.4]], 0.6), { k, dx, dy });
  return sortie(o, { tout: d }, d);
};
/** etoile — étoile à cinq branches à pointes adoucies (favori, note). */
M.etoile = (o = {}) => {
  const { cx = 12, cy = 12.6, r = 10.4, ri = 0.46 } = o;
  const pts = []; for (let i = 0; i < 10; i++) pts.push(pt(cx, cy, i % 2 ? r * ri : r, -90 + i * 36));
  const d = polyR(pts, 0.7); return sortie(o, { tout: d }, d);
};
/** drapeau — drapeau sur hampe : tissu ondulé (o.forme "rect") ou fanion à queue d'aronde ("fanion"). parties : hampe, tissu. */
M.drapeau = (o = {}) => {
  const { x = 4, y = 2, h = 20, w = 15, forme = "rect" } = o;
  const hampe = G.rect(x, y, 2.6, h, 1.3);
  const tissu = forme === "fanion" ? G.poly([[x + 2.6, y + 1], [x + w, y + 1], [x + w - 3.6, y + 5.4], [x + w, y + 9.8], [x + 2.6, y + 9.8]])
    : `M${f(x + 2.6, y + 1)}C${f(x + 6, y - 0.4, x + 9, y + 2.6, x + w, y + 1)}V${r1(y + 10)}C${f(x + 9, y + 11.6, x + 6, y + 8.6, x + 2.6, y + 10)}Z`;
  return sortie(o, { hampe, tissu }, union(hampe, tissu));
};
/** coche — coche ✓ pleine (épaisseur 2,6, bouts ronds) dans la boîte (x, y, s). */
M.coche = (o = {}) => {
  const { x = 2.5, y = 3, s = 19, w = 2.8 } = o, p1 = [x + s * .12, y + s * .55], p2 = [x + s * .4, y + s * .82], p3 = [x + s * .9, y + s * .22];
  const u = [p2[0] - p1[0], p2[1] - p1[1]], L = Math.hypot(...u), q = [p2[0] + u[0] / L * 0.3, p2[1] + u[1] / L * 0.3]; // prolongé : bouts non confondus
  const d = union(pill(...p1, ...q, w), pill(...p2, ...p3, w)); return sortie(o, { tout: d }, d);
};
/** maillon — maillon de chaîne en stade évidé (largeur 7,4, épaisseur 2,4) orienté par o.angle. */
M.maillon = (o = {}) => {
  const { cx = 12, cy = 12, l = 12, w = 7.4, e = 2.4, angle = -45 } = o;
  const d = placer(G.rect(cx - l / 2, cy - w / 2, l, w, w / 2) + G.rect(cx - l / 2 + e, cy - w / 2 + e, l - 2 * e, w - 2 * e, w / 2 - e), { rot: angle, cx, cy });
  return sortie(o, { tout: d }, d);
};
/** chaine — deux maillons en diagonale qui se chevauchent ; celui du haut passe devant (réserve 1,4). parties : avant, arriere. */
M.chaine = (o = {}) => {
  const { cx = 12, cy = 12, l = 11, angle = -45 } = o, u = pt(0, 0, 3.6, angle);
  const avant = M.maillon({ cx: cx - u[0], cy: cy - u[1], l, angle }), arriere = M.maillon({ cx: cx + u[0], cy: cy + u[1], l, angle });
  const ar = moins(arriere, inter(reserve(avant, 1.4), G.circle(cx + u[0] * 0.4 + 2, cy + u[1] * 0.4 + 2, 5)));
  return sortie(o, { avant, arriere: moins(ar, inter(avant, ar)) }, union(avant, moins(ar, reserve(avant, 1.4))));
};
/** engrenage — roue dentée (8 dents trapézoïdales) à moyeu évidé. */
M.engrenage = (o = {}) => {
  const { cx = 12, cy = 12, r = 10.2, n = 8, moyeu = 3.2 } = o, rr = r - 2.6, pts = [];
  for (let i = 0; i < n; i++) { const a = -90 + i * 360 / n, da = 360 / n;
    pts.push(pt(cx, cy, rr, a - da * 0.32), pt(cx, cy, r, a - da * 0.18), pt(cx, cy, r, a + da * 0.18), pt(cx, cy, rr, a + da * 0.32)); }
  const d = polyR(pts, 0.5) + G.circle(cx, cy, moyeu); return sortie(o, { tout: d }, d);
};
/** soleil — disque et rayons en pilules détachés (o.rayons = 8). parties : disque, rayons. */
M.soleil = (o = {}) => {
  const { cx = 12, cy = 12, r = 4.4, l = 10.4, n = 8 } = o, rays = [];
  for (let i = 0; i < n; i++) { const a = -90 + i * 360 / n; rays.push(G.pill(...pt(cx, cy, r + 2.6, a), ...pt(cx, cy, l - 1.1, a), 2.4)); }
  return sortie(o, { disque: G.circle(cx, cy, r), rayons: rays.join("") });
};
/** nuage — nuage à trois bosses et base plate. */
M.nuage = (o = {}) => {
  const { x = 1.6, y = 5, w = 20.8, h = 14 } = o, b = y + h;
  const d = union(G.circle(x + 5, b - 5, 5), G.circle(x + w * 0.52, b - h + 6.6, 6.6), G.circle(x + w - 4.6, b - 4.6, 4.6), G.rect(x + 5, b - 6, w - 9.6, 6));
  return sortie(o, { tout: d }, d);
};
/** goutte — goutte d'eau pointe en haut (couleur, liquide, flou). */
M.goutte = (o = {}) => {
  const { cx = 12, cy = 14.4, r = 7 } = o, top = cy - r * 1.75;
  const d = `M${f(cx, top)}C${f(cx + r * 0.4, top + r * 0.9, cx + r, cy - r * 0.55, cx + r, cy)}A${f(r, r)} 0 0 1 ${f(cx - r, cy)}C${f(cx - r, cy - r * 0.55, cx - r * 0.4, top + r * 0.9, cx, top)}Z`;
  return sortie(o, { tout: d }, d);
};
/** repere — repère de lieu (goutte renversée) à œil évidé. */
M.repere = (o = {}) => {
  const { cx = 12, cy = 9.4, r = 7.4 } = o;
  const d = placer(M.goutte({ cx, cy: 24 - cy, r }), { miroir: false, rot: 180, cx, cy: 12 }) + G.circle(cx, cy, 2.6);
  return sortie(o, { tout: d }, d);
};
/** lettreA — lettre A capitale à contre-forme évidée et barre (typographie, texte). */
M.lettreA = (o = {}) => {
  const { k = 1, dx = 0, dy = 0 } = o;
  const d = placer(moins(G.poly([[9.8, 2.6], [14.2, 2.6], [21, 21.4], [17.2, 21.4], [15.6, 16.8], [8.4, 16.8], [6.8, 21.4], [3, 21.4]]), G.poly([[12, 7.4], [14.4, 13.6], [9.6, 13.6]])), { k, dx, dy });
  return sortie(o, { tout: d }, d);
};
/** lettreT — lettre T capitale à empattements (outil texte, calque texte). */
M.lettreT = (o = {}) => {
  const { k = 1, dx = 0, dy = 0 } = o;
  const d = placer(union(G.rect(3, 2.5, 18, 3, 0.6), G.rect(10.5, 2.5, 3, 19, 0.6), G.rect(8, 19, 8, 2.6, 0.6)), { k, dx, dy });
  return sortie(o, { tout: d }, d);
};
/** curseurTexte — curseur de saisie en I (prompt, renommer, texte). */
M.curseurTexte = (o = {}) => {
  const { cx = 12, y = 3, h = 18 } = o;
  const d = union(G.rect(cx - 1.2, y, 2.4, h, 0.4), G.rect(cx - 3.6, y, 7.2, 2.2, 1.1), G.rect(cx - 3.6, y + h - 2.2, 7.2, 2.2, 1.1));
  return sortie(o, { tout: d }, d);
};
/** reglette — curseur de réglage : rail en pilule et bouton rond détaché (réglages, niveaux). parties : rail, bouton. */
M.reglette = (o = {}) => {
  const { x = 2, cy = 12, w = 20, pos = 0.6, rb = 3.2 } = o, bx = x + rb + (w - 2 * rb) * pos;
  return sortie(o, { rail: G.rect(x, cy - 1.2, w, 2.4, 1.2), bouton: G.circle(bx, cy, rb) }, empiler([G.circle(bx, cy, rb), G.rect(x, cy - 1.2, w, 2.4, 1.2)], 1.6));
};
/** carte — carte à jouer portrait arrondie, pivotable (o.angle) ; o.fenetre évide une fenêtre d'illustration. */
M.carte = (o = {}) => {
  const { cx = 12, cy = 12, w = 13, h = 19, angle = 0, fenetre = false } = o;
  let d = G.rect(cx - w / 2, cy - h / 2, w, h, 1.6);
  if (fenetre) d += G.rect(cx - w / 2 + 2.2, cy - h / 2 + 2.2, w - 4.4, h * 0.5, 0.6);
  if (angle) d = placer(d, { rot: angle, cx, cy });
  return sortie(o, { tout: d }, d);
};
/** avion — avion en papier (publier, programmer) : aile haute et aile basse séparées par le pli. parties : haute, basse. */
M.avion = (o = {}) => {
  const { k = 1, dx = 0, dy = 0 } = o, P = d => placer(d, { k, dx, dy });
  const haute = P(polyR([[21.6, 2.4], [2.4, 10.6], [8.4, 13.4]], 0.6)), basse = P(polyR([[21.6, 2.4], [11.6, 15.2], [14.4, 21.6]], 0.6));
  const pli = P(polyR([[9.4, 15], [10.6, 16.4], [9.8, 20.6]], 0.3));
  return sortie(o, { haute, basse, pli }, empiler([basse, haute, pli], 1.4));
};
/** disquette — disquette carrée à coin coupé : volet évidé en haut, étiquette évidée en bas. */
M.disquette = (o = {}) => {
  const { x = 3, y = 3, s = 18 } = o;
  const d = polyR([[x, y], [x + s - 4, y], [x + s, y + 4], [x + s, y + s], [x, y + s]], 1.4) + G.rect(x + 3.6, y + 2.4, s - 9.6, 4.6, 0.6) + G.rect(x + 3, y + s - 7.8, s - 6, 5.4, 0.8);
  return sortie(o, { tout: d }, d);
};

// ── Flèches ─────────────────────────────────────────────────────────────────────────────────────────
/** fleche — flèche droite pleine (fût 2,6, tête 8 × 5,4) de (x1,y1) vers (x2,y2) ; reprend G.arrow. */
M.fleche = (o = {}) => { const { x1 = 4, y1 = 12, x2 = 20, y2 = 12, w = 2.6, hw = 8.4, hl = 5.6 } = o; const d = G.arrow(x1, y1, x2, y2, w, hw, hl); return sortie(o, { tout: d }, d); };
/** flecheCourbe — flèche en arc de cercle (annuler, rétablir, actualiser, historique) : bande de a0 à a1 (degrés, horaire), tête au bout a1. */
M.flecheCourbe = (o = {}) => {
  const { cx = 12, cy = 12, r = 7.6, e = 2.6, a0 = 200, a1 = 470, hw = 8, hl = 5.6 } = o, s = Math.sign(a1 - a0);
  const amax = a1 - s * (hl / r) / RAD * 0.75, band = arc(cx, cy, r, e, a0, amax);
  const p = pt(cx, cy, r, a1 - s * (hl / r) / RAD * 0.85), tan = [-Math.sin((a1) * RAD) * s, Math.cos(a1 * RAD) * s], nrm = [Math.cos((a1 - s * (hl / r) / RAD * 0.85) * RAD), Math.sin((a1 - s * (hl / r) / RAD * 0.85) * RAD)];
  const tip = [p[0] + tan[0] * hl, p[1] + tan[1] * hl];
  const tete = G.poly([[p[0] + nrm[0] * hw / 2, p[1] + nrm[1] * hw / 2], tip, [p[0] - nrm[0] * hw / 2, p[1] - nrm[1] * hw / 2]]);
  const d = union(band, tete); return sortie(o, { tout: d }, d);
};
/** flecheCoudee — flèche coudée ↳ (dérivé, envoyer vers) : descend puis part à droite. */
M.flecheCoudee = (o = {}) => {
  const { x = 4, y = 3, w = 17, h = 15, e = 2.6, hw = 8.4, hl = 5.6 } = o;
  const d = union(rectR(x, y, e, h - e / 2 + 0.01, [e / 2, e / 2, 0, 0]), `M${f(x, y + h - e / 2 - 3)}V${r1(y + h + e / 2)}H${r1(x + w - hl + 0.2)}V${r1(y + h - e / 2)}H${r1(x + e + 3)}A3 3 0 0 1 ${f(x + e, y + h - e / 2 - 3)}Z`,
    G.poly([[x + w - hl, y + h - hw / 2], [x + w, y + h], [x + w - hl, y + h + hw / 2]]));
  return sortie(o, { tout: d }, d);
};

// ── Marque ──────────────────────────────────────────────────────────────────────────────────────────
/** poulpe — le poulpe Deepotus (d'après deepotus-logo.png) : tête en bulbe, yeux en amande inclinés « sourcils
 *  froncés » évidés, six tentacules effilés qui s'enroulent vers l'extérieur. o.k / o.dx / o.dy pour le réduire,
 *  o.yeux = false pour la silhouette pleine. parties : tete, tentacules. */
M.poulpe = (o = {}) => {
  const { k = 1, dx = 0, dy = 0, yeux = true } = o, P = d => placer(d, { k, dx, dy, cx: 12, cy: 12 });
  const tete0 = union(G.circle(12, 7, 5.3), polyR([[7.2, 8], [16.8, 8], [14.6, 13.6], [9.4, 13.6]], 1.4));
  const oeil = (cx, s) => placer(ellipse(cx, 10.2, 1.75, 0.95), { rot: 26 * s, cx, cy: 10.2 });
  const tete = yeux ? moins(tete0, oeil(9.9, 1), oeil(14.1, -1)) : tete0;
  const eff = t => 2.3 - 0.3 * t; // tentacule effilé (2,3 → 2)
  const T = [
    [[7.8, 11.2], [5.2, 12.4], [3, 11.6], [2.4, 9.2], [3.6, 7.6], [5.2, 7.8]],        // bras haut : s'enroule vers le haut
    [[8.8, 13.2], [6.8, 15.6], [4.2, 17], [2.4, 16.4], [2.4, 14.6]],                       // bras moyen : file en dehors, pointe relevée
    [[10.5, 13.8], [10.1, 16.8], [8.6, 19.4], [6.4, 21], [4.8, 20.6]],                     // bras bas : pend puis s'enroule en dehors
  ];
  const tent = T.flatMap(c => { const g = lisse(c, 12); return [trait(g, eff), trait(g.map(([x, y]) => [24 - x, y]), eff)]; });
  const tentacules = union(...tent);
  return sortie(o, { tete: P(tete), tentacules: P(tentacules) }, P(union(tete, tentacules)));
};

/** maison — maison (accueil) : toit à deux pans débordant, corps, porte évidée ouverte en bas (o.porte = false pour la retirer). */
M.maison = (o = {}) => {
  const { x = 1.6, y = 2, w = 20.8, h = 20, porte = true } = o, cx = x + w / 2, ey = y + h * 0.46;
  let d = union(polyR([[cx, y], [x + w, ey], [x, ey]], 1), G.rect(x + w * 0.16, ey - 1, w * 0.68, y + h - ey + 1, 1.2));
  if (porte) d = moins(d, rectR(cx - 2.3, y + h - 6.6, 4.6, 7.6, [1.4, 1.4, 0, 0]));
  return sortie(o, { tout: d }, d);
};

// ── Badges (CHARTE §4) ──────────────────────────────────────────────────────────────────────────────
/** badge — pastille Ø9,2 du quart bas-droit (centre 18,18) portant son symbole évidé : plus, moins, etincelle, fleche-sortante, coche, horloge ; « cadenas » est un mini-cadenas plein. À passer en tête de M.icone avec reserve 1,4. */
M.badge = (type, o = {}) => {
  const { cx = 18, cy = 18, r = 4.6 } = o, disc = G.circle(cx, cy, r);
  const sym = {
    plus: () => G.plus(cx, cy, 5, 1.8),
    moins: () => G.rect(cx - 2.5, cy - 0.9, 5, 1.8),
    etincelle: () => { const R = 3, k = 0.5; return `M${f(cx, cy - R)}Q${f(cx + k, cy - k, cx + R, cy)}Q${f(cx + k, cy + k, cx, cy + R)}Q${f(cx - k, cy + k, cx - R, cy)}Q${f(cx - k, cy - k, cx, cy - R)}Z`; },
    "fleche-sortante": () => union(G.pill(cx - 1.8, cy + 1.8, cx + 0.9, cy - 0.9, 1.7), G.poly([[cx - 0.6, cy - 2.4], [cx + 2.4, cy - 2.4], [cx + 2.4, cy + 0.6]])),
    coche: () => union(G.pill(cx - 2.4, cy + 0.1, cx - 0.5, cy + 2, 1.7), G.pill(cx - 0.7, cy + 1.8, cx + 2.5, cy - 1.6, 1.7)),
    horloge: () => union(G.pill(cx, cy + 0.3, cx, cy - 2.6, 1.7), G.pill(cx - 0.3, cy, cx + 2.1, cy, 1.7)),
  };
  if (type === "cadenas") { const d = union(G.rect(cx - 4.2, cy - 0.6, 8.4, 5.6, 1), arc(cx, cy - 1.4, 2.3, 1.8, 180, 360), G.rect(cx - 3.2, cy - 1.4, 1.8, 1.2), G.rect(cx + 1.4, cy - 1.4, 1.8, 1.2));
    return o.trou ? reserve(d, o.trou) : d; }
  if (!sym[type]) throw new Error("badge inconnu : " + type + " (CHARTE §4)");
  return o.trou ? reserve(disc, o.trou) : moins(disc, sym[type]());
};

module.exports = Object.assign(M, {
  // outillage
  lire, ecrire, placer, aplatir, region, versD, fin, union, moins, inter, remplir, dilater, eroder, arrondir, reserve, aire, empiler, icone,
  arc, ellipse, rectR, polyR, pt, trait, lisse, pill, RES, RES_BADGE, E,
});
