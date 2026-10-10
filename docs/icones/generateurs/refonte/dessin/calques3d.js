// Mission « calques-3d-categories » : familles calque, lab3d, cat (74 clés). Usage : node dessin/calques3d.js [filtre]
// Chaque icône = une liste de calques DU HAUT VERS LE BAS passée à M.icone (règle du monochrome : chaque calque est
// évidé de la réserve 1,5 de ceux du dessus ; badge : 1,4). ATTENTION : la réserve d'un calque est sa silhouette
// REMPLIE ; tout ce qui se loge dans le trou d'un anneau doit donc être listé AU-DESSUS de cet anneau.
// Famille cat : angles vifs partout (rayon 0) ; les courbes naturelles (disque, arc) restent des courbes.
"use strict";
const fs = require("fs"), path = require("path");
const G = require("../geo.js"), M = require("../motifs.js");
const OUT = path.join(__dirname, "..", "svg");
fs.mkdirSync(OUT, { recursive: true });
const PALE = .38;
const pl = (d, x = {}) => ({ d, op: 1, ...x }), pa = (d, x = {}) => ({ d, op: PALE, ...x });
const badge = type => ({ d: M.badge(type), op: 1, reserve: M.RES_BADGE });
const { union, moins, inter, placer, arc, rectR, polyR, pt, trait, lisse, pill, ellipse } = M;
const R0 = (x, y, w, h) => G.rect(x, y, w, h, 0); // angle vif (famille cat)
const hex = (cx, cy, r) => [-90, -30, 30, 90, 150, 210].map(a => pt(cx, cy, r, a));
const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
/** Fente droite de largeur w de a vers b, prolongée de e aux deux bouts (pour couper une forme de part en part). */
const fente = (a, b, w = 1.6, e = 0.6) => { const L = Math.hypot(b[0] - a[0], b[1] - a[1]), u = [(b[0] - a[0]) / L, (b[1] - a[1]) / L], n = [-u[1] * w / 2, u[0] * w / 2];
  const A = [a[0] - u[0] * e, a[1] - u[1] * e], B = [b[0] + u[0] * e, b[1] + u[1] * e];
  return G.poly([[A[0] + n[0], A[1] + n[1]], [B[0] + n[0], B[1] + n[1]], [B[0] - n[0], B[1] - n[1]], [A[0] - n[0], A[1] - n[1]]]); };
/** Demi-plan (grand polygone) du côté gauche du vecteur a→b. */
const demiPlan = (a, b) => { const u = [b[0] - a[0], b[1] - a[1]], L = Math.hypot(...u), k = 60 / L, n = [u[1] * k, -u[0] * k];
  const A = [a[0] - u[0] * k, a[1] - u[1] * k], B = [b[0] + u[0] * k, b[1] + u[1] * k];
  return G.poly([A, B, [B[0] + n[0], B[1] + n[1]], [A[0] + n[0], A[1] + n[1]]]); };
/** Secteur angulaire (degrés, horaire) d'un disque. */
const secteur = (cx, cy, r, a0, a1) => { const pts = [[cx, cy]]; for (let i = 0; i <= 8; i++) pts.push(pt(cx, cy, r * 1.3, a0 + (a1 - a0) * i / 8)); return inter(G.circle(cx, cy, r), G.poly(pts)); };
/** Os : fût en pilule et deux têtes doubles, de a vers b. */
const os = (a, b, w = 3, rt = 2.5) => { const L = Math.hypot(b[0] - a[0], b[1] - a[1]), u = [(b[0] - a[0]) / L, (b[1] - a[1]) / L], n = [-u[1], u[0]], k = rt * 0.82;
  const tete = (p, s) => G.circle(p[0] + n[0] * k - u[0] * s, p[1] + n[1] * k - u[1] * s, rt) + G.circle(p[0] - n[0] * k - u[0] * s, p[1] - n[1] * k - u[1] * s, rt);
  return union(pill(...a, ...b, w), tete(a, 0.4), tete(b, -0.4)); };
const I = {};

// ═══════════════════════════════════════ cat : onglets Game Assets (série ga-onglets, design15 §2.4) ════════
I["dz-cat-3d"] = () => { const H = hex(12, 12, 10.2), C = [12, 12];
  return [pl(G.poly([H[0], H[1], C, H[5]])), pa(moins(G.poly(H), fente(C, [12, 23], 1.6, 0)))]; };
I["dz-cat-studio-3d"] = () => { const H = hex(12, 12.2, 4.6), C = [12, 12.2];
  const cube = moins(G.poly(H), fente(C, H[1], 1.4, 0.4), fente(C, H[5], 1.4, 0.4), fente(C, H[3], 1.4, 0.4));
  return [pl(cube), pa(R0(2, 3.4, 20, 17.6) + R0(4.4, 5.8, 15.2, 12.8))]; };
I["dz-cat-sprites"] = () => [pl(R0(5.6, 7.2, 6, 5.2) + R0(12.4, 12.2, 6, 5.2)), pa(R0(2, 2.6, 20, 18.4))];
I["dz-cat-tuiles"] = () => { // damier 3 × 3 (le 2 × 2 du design15 se confondait avec nav-templates : IoU 0,87)
  const c = (i, j) => R0(2 + j * 7.2, 2 + i * 7.2, 5.6, 5.6), P = [], Q = [];
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) ((i + j) % 2 ? Q : P).push(c(i, j));
  return [pl(P.join("")), pa(Q.join(""))]; };
I["dz-cat-matieres"] = () => [pl(M.sphere({ partie: "moitie" })), pa(M.sphere({ partie: "gauche" }))];
I["dz-cat-cartes"] = () => [pl(R0(11, 3, 9.8, 15.6)), pa(placer(R0(3.6, 6.4, 10.4, 14), { rot: -12, cx: 8.8, cy: 13.4 }))];
I["dz-cat-assets-2d"] = () => [pl(G.circle(16.9, 7, 4.7) + G.poly([[2.2, 21.6], [12, 13.2], [21.8, 21.6]])), pa(R0(2.2, 2.4, 9.2, 9.2))];

// ═══════════════════════════════════════ cat : catégories de nœuds du Studio (série studio-categories) ═════
I["dz-cat-source"] = () => { const base = R0(7.4, 4.8, 9.2, 15), P = { cx: 12, cy: 19.8 };
  return [pl(base), pa(moins(union(placer(base, { rot: -30, ...P }), placer(base, { rot: 30, ...P })), R0(0, 17.6, 24, 9)))]; };
I["dz-cat-generateur"] = () => [pl(moins(G.ngon(12, 12, 10.6, 6, 0), M.etincelle({ cx: 12, cy: 12, r: 6.4, eclat: false })))];
I["dz-cat-composition"] = () => [pl(G.circle(14.6, 12.2, 3.8)), pl(R0(5.4, 7.4, 7.6, 7.6)), pa(R0(1.6, 3.4, 20.8, 17.2) + R0(3.8, 5.6, 16.4, 12.8))];
I["dz-cat-animation"] = () => { const c = pt(20, 20.5, 15, 254);
  return [pl(G.poly([[c[0], c[1] - 4.4], [c[0] + 4.4, c[1]], [c[0], c[1] + 4.4], [c[0] - 4.4, c[1]]])), pa(arc(20, 20.5, 15, 2.6, 180, 262))]; };
I["dz-cat-montage"] = () => { const seg = x => { let d = R0(x, 3.6, 9.2, 16.8);
  for (const nx of [x + 2, x + 5.6]) d = moins(d, R0(nx, 2.6, 1.6, 3.2), R0(nx, 18.8, 1.6, 3.2));
  return moins(d, R0(x + 2, 7.8, 5.2, 8.4)); };
  return [pl(seg(2) + seg(12.8))]; };
I["dz-cat-audio"] = () => [pl(union(R0(3, 14.6, 8.4, 6.8), R0(9, 2.2, 2.4, 14))), pa(G.poly([[12.6, 2.2], [20.8, 7], [20.8, 13], [12.6, 8.2]]))];
I["dz-cat-maitre"] = () => { const hs = [7.6, 13.6, 13.6, 13.6, 10], cy = 14.6;
  return [pl(R0(2, 2.2, 20, 2.8)), pa(hs.map((h, i) => R0(2 + i * 4.4, cy - Math.min(h, 13.6) / 2, 2.4, Math.min(h, 13.6))).join(""))]; };
I["dz-cat-sortie"] = () => [pl(G.poly([[8.4, 7.6], [22, 12], [8.4, 16.4]])), pa(R0(2, 3.6, 14.4, 16.8) + R0(4.4, 6, 9.6, 12))];

// ═══════════════════════════════════════ cat : entités de la bible de l'Atelier (série atelier-entites) ══════
I["dz-cat-personnage"] = () => [pl(G.ngon(12, 6.2, 4.4, 8, -112.5) + G.poly([[2.6, 22], [2.6, 16.6], [7.2, 12.4], [16.8, 12.4], [21.4, 16.6], [21.4, 22]]))];
I["dz-cat-lieu"] = () => [pl(M.repere({ cx: 12, cy: 7.2, r: 6 })), pa(R0(2.4, 19.6, 19.2, 2.6))];
I["dz-cat-decor"] = () => [pl(R0(2, 2, 20, 2.4) + G.poly([[2.6, 21.6], [2.6, 16.6], [8.6, 10.6], [12.2, 14.4], [15.4, 11.4], [21.4, 17], [21.4, 21.6]])), pa(R0(4.2, 6, 15.6, 15.6))];
I["dz-cat-objet"] = () => { const corps = moins(G.poly([[8.4, 6.8], [15.6, 6.8], [18.4, 9.6], [18.4, 18.8], [15.6, 21.6], [8.4, 21.6], [5.6, 18.8], [5.6, 9.6]]), R0(9.2, 11, 5.6, 7.4));
  return [pl(corps), pa(arc(12, 6.6, 4.2, 2.4, 220, 320))]; };
I["dz-cat-ambiance"] = () => [pl(M.nuage({ x: 1.6, y: 10.6, w: 16.4, h: 11 })), pa(G.circle(15.6, 8, 6.2))];
I["dz-cat-date"] = () => { const un = union(R0(11.6, 11.6, 2.6, 8.2), G.poly([[11.6, 11.6], [14.2, 11.6], [9, 15.4], [9, 13.4]]));
  return [pl(R0(3, 2.4, 18, 5.4)), pa(moins(R0(3, 9.4, 18, 12.6), un))]; }; // chiffre 1 évidé

// ═══════════════════════════════════════ calque : types de calques (série calques) ═══════════════════════════
const plaque = (cy = 17.4, h = 8.4) => M.plaque({ cx: 12, cy, w: 20, h });
I["dz-calque-nouveau"] = () => { const o = { y: 2.6, h: 8.4, w: 20, n: 2, pas: 6.6, forme: "parallelogramme" };
  return [badge("plus"), pl(M.pile({ ...o, partie: "dessus" })), pa(M.pile({ ...o, partie: "dessous" }))]; };
I["dz-calque-groupe"] = () => { const dos = polyR([[2, 3.6], [9.6, 3.6], [11.4, 6], [22, 6], [22, 20.8], [2, 20.8]], 1.2);
  const anneau = moins(dos, G.rect(4.2, 8.2, 15.6, 10.4, 0.6));
  return [pa(M.plaque({ cx: 12, cy: 11.2, w: 12.6, h: 2.8, r: 0.4 }) + M.plaque({ cx: 12, cy: 15.6, w: 12.6, h: 2.8, r: 0.4 })), pl(anneau)]; };
I["dz-calque-pixel"] = () => [pl(M.damier({ x: 6.2, y: 2, s: 11.6, n: 2 })), pa(plaque())];
I["dz-calque-texte"] = () => [pl(union(G.rect(4.8, 2, 14.4, 3.2, 0.6), G.rect(10.6, 2, 2.8, 15, 0.6))), pa(plaque())];
I["dz-calque-vectoriel"] = () => { const A = [5.4, 10.6], B = [18.6, 4.4], g = lisse([A, [9.6, 9.8], [11.6, 7.2], [14.2, 4.8], B], 10);
  return [pl(union(G.rect(A[0] - 2.4, A[1] - 2.4, 4.8, 4.8, 0.6), G.rect(B[0] - 2.4, B[1] - 2.4, 4.8, 4.8, 0.6), trait(g, 2.4))), pa(plaque())]; };
I["dz-calque-masque"] = () => [pl(G.rect(2, 3.6, 20, 16.8, 1.4) + G.circle(12, 12, 5.2))];
I["dz-calque-objet-dynamique"] = () => [pl(G.rect(12, 12, 10, 10, 1.4) + G.rect(15, 15, 4, 4, 0.6)), pa(G.rect(2, 2, 15.6, 15.6, 1.4))];
I["dz-calque-reglage"] = () => { const c = [12, 8.6], r = 6.6, a = [c[0] - 6, c[1] + 6], b = [c[0] + 6, c[1] - 6];
  return [pl(inter(G.circle(...c, r), demiPlan(a, b))), pa(moins(G.circle(...c, r), demiPlan(a, b))), pa(plaque(17.6, 8))]; };
I["dz-calque-ecretage"] = () => { const sq = G.rect(9.4, 2, 12.4, 11.4, 1.4);
  return [pl(inter(G.circle(12, 11.8, 6.2), sq)), pl(M.flecheCoudee({ x: 2.2, y: 2, w: 19.6, h: 16.4, hw: 7.2, hl: 5 })), pa(sq)]; };
I["dz-calque-fusionner"] = () => [pl(M.fleche({ x1: 12, y1: 1.6, x2: 12, y2: 15.4, w: 2.8, hw: 8.4, hl: 5.4 })),
  pa(M.plaque({ cx: 12, cy: 5.6, w: 20, h: 6.4 })), pa(M.plaque({ cx: 12, cy: 18.6, w: 20, h: 6.4 }))];

// ═══════════════════════════════════════ calque : réglages photo (série reglages-photo) ══════════════════════
const cadreReglage = () => G.rect(2, 2, 20, 20, 1.4) + G.rect(4.2, 4.2, 15.6, 15.6, 0.6);
I["dz-calque-courbes"] = () => [pl(trait(lisse([[3.2, 20.8], [7.6, 19.4], [10.6, 14.8], [13.4, 9.2], [16.4, 4.6], [20.8, 3.2]], 10), 2.6)), pa(cadreReglage())];
I["dz-calque-seuil"] = () => [pl(trait([[3, 16.8], [11.6, 16.8], [12, 16.4], [12, 7.6], [12.4, 7.2], [21, 7.2]], 2.6)), pa(cadreReglage())];
I["dz-calque-exposition"] = () => { const a = [2, 22], b = [22, 2];
  return [pl(moins(inter(G.circle(12, 12, 10.2), demiPlan(a, b)), G.plus(8.2, 8.2, 6, 2.2))), pa(moins(G.circle(12, 12, 10.2), demiPlan(a, b), G.rect(13, 14.7, 6, 2.2)))]; };
I["dz-calque-filtre-photo"] = () => [pl(moins(G.circle(8.4, 12, 6.4), arc(8.4, 12, 3.2, 1.8, 195, 260))), pa(G.ring(13.8, 12, 8.4, 5.8))];
I["dz-calque-inverser"] = () => { const a = [0, 24], b = [24, 0], c = [12, 12], rc = 4.8, sq = G.rect(2, 2, 20, 20, 1.4);
  return [pl(moins(G.circle(...c, rc), demiPlan(a, b))), pa(inter(G.circle(...c, rc), demiPlan(a, b))), pl(inter(sq, demiPlan(a, b))), pa(moins(sq, demiPlan(a, b)))]; };
I["dz-calque-luminosite-contraste"] = () => { const rays = []; for (let i = 0; i < 8; i++) { const a = -90 + i * 45; rays.push(pill(...pt(12, 12, 8, a), ...pt(12, 12, 10.2, a), 2.4)); }
  return [pl(union(...rays, M.sphere({ cx: 12, cy: 12, r: 5.4, partie: "moitie" }))), pa(M.sphere({ cx: 12, cy: 12, r: 5.4, partie: "gauche" }))]; };
I["dz-calque-mappage-degrade"] = () => { const tri = x => G.poly([[x - 2.8, 3.6], [x + 2.8, 3.6], [x, 9.4]]); // repères au-dessus d'une bande courte en quatre paliers
  return [pl(tri(4.8) + tri(12) + tri(19.2)), pa([0, 1, 2, 3].map(i => G.rect(2 + i * 5.4, 11.4, 3.8, 8.4, 0.6)).join(""))]; };
I["dz-calque-melangeur-couches"] = () => { const C = [[12, 7.8], [7.6, 15.2], [16.4, 15.2]], r = 6.2, D = C.map(c => G.circle(...c, r));
  return [pl(union(inter(D[0], D[1]), inter(D[1], D[2]), inter(D[0], D[2]))), pa(union(...D))]; };
I["dz-calque-niveaux"] = () => { const tri = x => G.poly([[x, 15.6], [x + 2.7, 21.4], [x - 2.7, 21.4]]);
  const mont = polyR([[2, 13.4], [2, 11.4], [4.4, 8.6], [6.4, 4.4], [8.6, 2.2], [10.8, 4.6], [12.6, 8.4], [14.6, 7.4], [16.8, 6.4], [19.2, 9.6], [22, 11.6], [22, 13.4]], 0.6);
  return [pl(tri(4.8) + tri(12) + tri(19.2)), pa(mont)]; };
I["dz-calque-noir-blanc"] = () => [pl(G.rect(2, 6, 9.2, 12, 1.4)), pa(G.rect(12.8, 6, 9.2, 12, 1.4) + G.rect(15, 8.2, 4.8, 7.6, 0.6))];
I["dz-calque-posteriser"] = () => [pl(G.circle(12, 12, 2.6)), pa(G.ring(12, 12, 6.3, 4.1)), pl(G.ring(12, 12, 10.2, 7.8))];
I["dz-calque-table-couleurs"] = () => { const H = hex(12, 12, 10.4), C = [12, 12];
  const faces = [[H[5], H[0], H[1], C], [C, H[1], H[2], H[3]], [H[4], H[5], C, H[3]]], cells = [];
  for (const [p0, p1, p2, p3] of faces) { const m01 = mid(p0, p1), m12 = mid(p1, p2), m23 = mid(p2, p3), m30 = mid(p3, p0), c = mid(m01, m23);
    cells.push([[p0, m01, c, m30], [m01, p1, m12, c], [c, m12, p2, m23], [m30, c, m23, p3]].map(q => G.poly(q))); }
  const k = d => M.eroder(d, 0.8);
  const plein = [cells[0][0], cells[0][2], cells[1][1], cells[1][3], cells[2][1], cells[2][3]].map(k), pale = [cells[0][1], cells[0][3], cells[1][0], cells[1][2], cells[2][0], cells[2][2]].map(k);
  return [pl(union(...plein)), pa(union(...pale))]; };
I["dz-calque-teinte-saturation"] = () => { const s = i => secteur(12, 12, 10.2, -90 + i * 60, -30 + i * 60), trou = G.circle(12, 12, 2.6);
  return [pl(moins(union(s(0), s(2), s(4)), trou)), pa(moins(union(s(1), s(3), s(5)), trou))]; };
I["dz-calque-vibrance"] = () => { const tri = polyR([[12, 1.8], [22.4, 21.6], [1.6, 21.6]], 1.2);
  return [pa(inter(tri, R0(0, 0, 24, 7.6))), pl(moins(tri, R0(0, 0, 24, 9.2), R0(0, 14.4, 24, 1.6)))]; };
I["dz-calque-balance-couleurs"] = () => { const fleau = union(G.rect(2.6, 5, 18.8, 2.4, 1.2), G.poly([[12, 1.8], [14.2, 5.2], [9.8, 5.2]]),
  G.rect(4.8, 6.2, 2, 6), G.rect(17.2, 6.2, 2, 6), `M2.4 11.8H9.2A3.4 3.4 0 0 1 2.4 11.8Z`, `M14.8 11.8H21.6A3.4 3.4 0 0 1 14.8 11.8Z`);
  return [pl(fleau), pa(union(G.rect(10.8, 6, 2.4, 14, 0.4), G.rect(6.4, 19.4, 11.2, 2.6, 1.3)))]; };
I["dz-calque-couleur-selective"] = () => [pl(G.ring(12, 13.6, 8.2, 6) + M.goutte({ cx: 12, cy: 15, r: 2.8 })),
  pa(M.goutte({ cx: 3.4, cy: 5.8, r: 2.2 }) + M.goutte({ cx: 20.6, cy: 5.8, r: 2.2 }))];

// ═══════════════════════════════════════ lab3d : primitives (série primitives-3d) ════════════════════════════
const ombre = () => ellipse(12, 20.2, 9.4, 2.2);
I["dz-lab3d-cube"] = () => { const F = [[4, 7.2], [13.4, 7.2], [13.4, 16.6], [4, 16.6]], T = [[4, 7.2], [9, 2.2], [18.4, 2.2], [13.4, 7.2]], S = [[13.4, 7.2], [18.4, 2.2], [18.4, 11.6], [13.4, 16.6]];
  const c = union(G.poly(F), G.poly(T), G.poly(S)), cut = union(fente([4, 7.2], [13.4, 7.2], 1.4, 0), fente([13.4, 7.2], [13.4, 16.6], 1.4, 0), fente([13.4, 7.2], [18.4, 2.2], 1.4, 0));
  return [pl(moins(c, cut)), pa(ombre())]; };
I["dz-lab3d-sphere"] = () => [pl(moins(G.circle(12, 9.4, 7.2), arc(12, 9.4, 4, 1.8, 195, 255))), pa(ombre())];
I["dz-lab3d-cylindre"] = () => { const top = ellipse(12, 4.8, 6.6, 2.6), corps = union(G.rect(5.4, 4.8, 13.2, 9.4), ellipse(12, 14.2, 6.6, 2.4));
  return [pl(union(top, moins(corps, M.dilater(top, 1.6)))), pa(ombre())]; };
I["dz-lab3d-capsule"] = () => [pl(moins(G.rect(7.4, 1.8, 9.2, 14.8, 4.6), G.rect(5, 8.4, 14, 1.6))), pa(ombre())];

// ═══════════════════════════════════════ lab3d : nœuds de la Forge 3D (série forge3d-noeuds) ════════════════
I["dz-lab3d-plan"] = () => { const T = [12, 3.8], Rr = [22.2, 12], B = [12, 20.2], L = [1.8, 12], C = [12, 12];
  const mTR = mid(T, Rr), mRB = mid(Rr, B), mBL = mid(B, L), mLT = mid(L, T);
  return [pl(G.poly([T, mTR, C, mLT]) + G.poly([C, mRB, B, mBL])), pa(G.poly([mTR, Rr, mRB, C]) + G.poly([mLT, C, mBL, L]))]; };
I["dz-lab3d-maillage"] = () => { // losange en treillis triangulaire : lignes parallèles aux côtés + trois horizontales
  const T = [12, 1.8], Rr = [22.2, 12], B = [12, 22.2], L = [1.8, 12], C = [12, 12], mTR = mid(T, Rr), mRB = mid(Rr, B), mBL = mid(B, L), mLT = mid(L, T);
  const cuts = union(fente(mLT, mRB), fente(mTR, mBL), fente(L, Rr), fente(mLT, mTR), fente(mBL, mRB));
  return [pl(moins(polyR([T, Rr, B, L], 0.8), cuts))]; };
I["dz-lab3d-filaire"] = () => { const H = hex(12, 12, 10), C = [12, 12], w = 2.2, e = [];
  for (let i = 0; i < 6; i++) e.push(pill(...H[i], ...H[(i + 1) % 6], w));
  e.push(pill(...C, ...H[1], w), pill(...C, ...H[5], w), pill(...C, ...H[3], w));
  return [pl(union(...e))]; };
I["dz-lab3d-extrusion"] = () => [pl(G.rect(2.2, 9.6, 12.2, 12.2, 1.2)), pa(M.fleche({ x1: 8.6, y1: 15.4, x2: 21.8, y2: 2.2, w: 2.8, hw: 8.2, hl: 5.6 }))];
I["dz-lab3d-relief"] = () => [pl(polyR([[2, 14.2], [2, 11.2], [6.4, 5.4], [9.6, 9.2], [13.8, 2.2], [17.8, 8.4], [19.8, 6.6], [22, 9.2], [22, 14.2]], 0.6)), pa(G.rect(2, 15.8, 20, 6, 1.2))];
I["dz-lab3d-artefact"] = () => { const g = polyR([[6.4, 2.6], [17.6, 2.6], [22.2, 8.8], [12, 21.8], [1.8, 8.8]], 0.8);
  const cuts = union(fente([1, 8.8], [23, 8.8]), fente([9.2, 2], [7.2, 8.8], 1.6, 0.2), fente([14.8, 2], [16.8, 8.8], 1.6, 0.2), fente([7.2, 8.8], [10.6, 15.4], 1.6, 0), fente([16.8, 8.8], [13.4, 15.4], 1.6, 0));
  return [pl(moins(g, cuts))]; };
I["dz-lab3d-assemblage"] = () => [pl(union(G.rect(2, 2, 14.4, 5.6, 0.8), G.rect(2, 2, 5.6, 14.4, 0.8))), pa(union(G.rect(9.2, 16.4, 12.8, 5.6, 0.8), G.rect(16.4, 9.2, 5.6, 12.8, 0.8)))];

// ═══════════════════════════════════════ lab3d : génération, export, optimisation ═══════════════════════════
I["dz-lab3d-generer-modele"] = () => { const H = hex(10.4, 10.6, 8.8), C = [10.4, 10.6];
  return [badge("etincelle"), pl(G.poly([H[0], H[1], C, H[5]])), pa(moins(G.poly(H), fente(C, [10.4, 22], 1.6, 0)))]; };
I["dz-lab3d-optimiser"] = () => { const presse = s => { const x = s > 0 ? 1.6 : 22.4; return union(R0(s > 0 ? x : x - 2.4, 5.4, 2.4, 13.2), G.poly([[x + s * 2.4, 8.2], [x + s * 6.2, 12], [x + s * 2.4, 15.8]])); };
  return [pl(presse(1) + presse(-1)), pa(M.cube({ cx: 12, cy: 12, r: 5.4 }))]; };
I["dz-lab3d-lod"] = () => [pl(G.rect(2, 15.8, 20, 5.8, 0.8) + G.rect(5.4, 9.2, 13.2, 5, 0.8) + G.rect(8.8, 2.6, 6.4, 5, 0.8))];
I["dz-lab3d-impression-3d"] = () => [pl(union(G.rect(6.8, 1.8, 10.4, 5.6, 0.8), G.poly([[8.8, 7], [15.2, 7], [12, 11.6]]))),
  pa(union(G.rect(2, 19, 20, 2.8, 1), G.rect(6.8, 13.2, 10.4, 6.2, 0.6)))];
I["dz-lab3d-orienter"] = () => [pl(placer(G.rect(7.6, 9.6, 8.4, 7.6, 1), { rot: 24, cx: 11.8, cy: 13.4 })),
  pa(G.rect(2, 19.4, 20, 2.6, 1.2) + M.flecheCourbe({ cx: 12, cy: 11.6, r: 8.4, e: 2.4, a0: 196, a1: 322, hw: 6.4, hl: 4.4 }))];
I["dz-lab3d-rotation"] = () => { const cx = 12, cy = 12.4, rx = 10, ry = 6.2, P = t => [cx + rx * Math.cos(t * Math.PI / 180), cy + ry * Math.sin(t * Math.PI / 180)], pts = [];
  for (let t = 168; t >= 34; t -= 6) pts.push(P(t));
  const e = P(34), d = [10 * Math.sin(34 * Math.PI / 180), -6.2 * Math.cos(34 * Math.PI / 180)], L = Math.hypot(...d), u = [d[0] / L, d[1] / L], n = [-u[1], u[0]];
  const tete = G.poly([[e[0] + n[0] * 3.6, e[1] + n[1] * 3.6], [e[0] + u[0] * 5, e[1] + u[1] * 5], [e[0] - n[0] * 3.6, e[1] - n[1] * 3.6]]);
  return [pl(union(trait(pts, 2.6), tete)), pa(ellipse(12, 9, 7.6, 3.2))]; };

// ═══════════════════════════════════════ lab3d : matériaux (série materiaux) ════════════════════════════════
I["dz-lab3d-materiau"] = () => [pl(pill(7.2, 12.4, 12.4, 7.2, 2.6) + pill(8.4, 17.2, 17.2, 8.4, 2.2)), pa(G.rect(2, 2, 20, 20, 1.4))];
I["dz-lab3d-forger-matiere"] = () => [badge("etincelle"), pl(moins(G.rect(2, 2, 17.6, 17.6, 1.4), pill(5.4, 11.4, 11.4, 5.4, 2.4)))];
I["dz-lab3d-deriver-maps"] = () => [pl([0, 1, 2].map(i => G.rect(15.6, 2.2 + i * 6.8, 6.4, 5.2, 0.8)).join("")), pa(G.rect(2, 6.4, 11.4, 11.2, 1.4))];
I["dz-lab3d-procedural"] = () => { const sq = G.rect(2, 2, 20, 20, 1.4), c = (pts, tone) => ({ d: M.eroder(G.poly(pts), 0.8), tone });
  const a = [9, 8.2], b = [7.4, 15.2], cc = [15.2, 12.4], d = [14.6, 5.6], e = [17.2, 18];
  const cells = [c([[0, 0], [10.6, 0], d, a, [0, 9.6]], 1), c([[10.6, 0], [24, 0], [24, 8.6], d], 0), c([d, [24, 8.6], [24, 14.2], cc], 1), c([a, d, cc, b], 0),
    c([[0, 9.6], a, b, [0, 16.6]], 0), c([b, cc, e, [11.6, 24], [0, 24], [0, 16.6]], 1), c([cc, [24, 14.2], [24, 24], e], 0), c([e, [24, 24], [11.6, 24]], 0)];
  const k = t => union(...cells.filter(x => x.tone === t).map(x => inter(x.d, sq)));
  return [pl(k(1)), pa(k(0))]; };

// ═══════════════════════════════════════ lab3d : lumières, caméra ══════════════════════════════════════════
I["dz-lab3d-hdri"] = () => [pl(moins(`M2.4 13A9.6 9.6 0 0 1 21.6 13Z`, G.circle(14.4, 8.4, 1.9))), pa(ellipse(12, 15.8, 10, 4.8))];
I["dz-lab3d-lumiere"] = () => { // projecteur en haut à gauche, axe à 45°, cône qui s'élargit vers le bas à droite
  const u = [Math.SQRT1_2, Math.SQRT1_2], n = [-Math.SQRT1_2, Math.SQRT1_2], c0 = [6, 6], Q = (a, b) => [c0[0] + u[0] * a + n[0] * b, c0[1] + u[1] * a + n[1] * b];
  const proj = polyR([Q(-4, -3.2), Q(1.8, -3.2), Q(3.6, -4.4), Q(3.6, 4.4), Q(1.8, 3.2), Q(-4, 3.2)], 0.6);
  const cone = G.poly([Q(5.4, -4.4), Q(24, -10), Q(24, 10), Q(5.4, 4.4)]);
  return [pl(proj), pa(inter(cone, G.rect(2, 2, 20, 20, 1.4)))]; };
I["dz-lab3d-camera"] = () => [pl(union(G.rect(2, 7.6, 10.4, 9, 1.2), G.rect(4, 5, 4.4, 3, 0.6), G.rect(11.8, 9.8, 2.8, 4.6, 0.4))),
  pa(G.poly([[16.2, 9.8], [22, 4.4], [22, 19.8], [16.2, 14.4]]))];

// ═══════════════════════════════════════ lab3d : squelette (série squelette) ═══════════════════════════════
I["dz-lab3d-os"] = () => [pl(os([5.4, 18.6], [18.6, 5.4]))];
I["dz-lab3d-piece"] = () => [pl(placer(G.rect(8, 8.6, 8, 6.8, 1), { rot: -45 })), pa(os([4.8, 19.2], [19.2, 4.8]))];
I["dz-lab3d-rig"] = () => { const w = 2.2, J = (x, y) => G.circle(x, y, 2);
  const corps = union(G.circle(12, 3.8, 2.8), pill(12, 8.4, 12, 13.8, w), pill(12, 8.4, 6.6, 10.6, w), pill(6.6, 10.6, 3.8, 15.2, w), pill(12, 8.4, 17.4, 10.6, w), pill(17.4, 10.6, 20.2, 15.2, w),
    pill(12, 13.8, 8.6, 17.4, w), pill(8.6, 17.4, 7.4, 21.8, w), pill(12, 13.8, 15.4, 17.4, w), pill(15.4, 17.4, 16.6, 21.8, w), J(12, 8.4), J(6.6, 10.6), J(17.4, 10.6), J(12, 13.8), J(8.6, 17.4), J(15.4, 17.4));
  return [pl(corps)]; };

// ═══════════════════════════════════════ écriture ═════════════════════════════════════════════════════════
const filtre = process.argv[2] || "";
let n = 0;
for (const [cle, fn] of Object.entries(I)) {
  if (filtre && !cle.includes(filtre)) continue;
  fs.writeFileSync(path.join(OUT, cle + ".svg"), M.icone(fn()));
  n++;
}
console.log(n + " icônes écrites dans " + OUT);
