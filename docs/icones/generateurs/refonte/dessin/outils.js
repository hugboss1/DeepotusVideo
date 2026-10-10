// Mission « outils » : familles outil-vec, outil-px, outil-photo (91 clés). Usage : node dessin/outils.js [filtre]
// Un outil = un geste : l'instrument au ton plein (sujet), la trace qu'il laisse au ton pâle (support).
// Gabarit commun des instruments tenus en main (pinceau, crayon, gomme, baguette…) : pointe en bas à gauche,
// corps vers le haut à droite (45°) ; dans la série « instrument + trace », la pointe est vers (10,14) et la
// trace occupe le quart bas-gauche. Épaisseurs absolues ≥ 2, jours ≥ 1,6 (les instruments réduits sont
// redessinés à cotes absolues, jamais par mise à l'échelle des motifs).
// Calques DU HAUT VERS LE BAS passés à M.icone (réserve monochrome 1,5 automatique).
"use strict";
const fs = require("fs"), path = require("path");
const G = require("../geo.js"), M = require("../motifs.js");
const OUT = path.join(__dirname, "..", "svg");
const PALE = .38;
const pl = (d, x = {}) => ({ d, op: 1, ...x }), pa = (d, x = {}) => ({ d, op: PALE, ...x });
const { union, moins, inter, placer, arc, rectR, polyR, pt, trait, lisse, pill, ellipse, eroder, dilater } = M;
const RAD = Math.PI / 180;
const I = {};

// ═══════════════════════════════════════ outillage local ══════════════════════════════════════════════
/** Pose un dessin « debout » (pointe en (0,0), corps vers −y) : pointe en (x,y), corps orienté à rot degrés (45 = haut-droite). */
const poser = (d, x, y, rot = 45) => placer(d, { rot, cx: 0, cy: 0, dx: x, dy: y });
/** Instruments à cotes absolues (debout, pointe en 0,0). parties renvoyées séparément. */
const INST = {
  // pinceau : touffe en goutte 4,6 × 6,4 ; jour 1,6 ; virole 4,6 × 3 ; manche 2,4 jusqu'à L
  pinceau(L = 17) {
    const touffe = `M-2.3 -6.4H2.3C2.3 -3.4 1.1 -1.6 0 0C-1.1 -1.6 -2.3 -3.4 -2.3 -6.4Z`;
    const manche = union(G.rect(-2.3, -11, 4.6, 3, 0.6), G.rect(-1.2, -L, 2.4, L - 10, 1.2));
    return { touffe, manche };
  },
  // crayon : pointe conique + corps 4,8 ; jour 1,6 ; gomme de tête 3
  crayon(L = 18) {
    const corps = `M-2.4 ${-(L - 4.6)}H2.4V-5.6L0 0L-2.4 -5.6Z`;
    const tete = G.rect(-2.4, -L, 4.8, 3, 1);
    return { corps, tete };
  },
  // gomme : semelle 6,4 × 4,2 ; jour 1,6 ; corps 6,4 × (L − 5,8)
  gomme(L = 15, w = 6.6) {
    const semelle = G.rect(-w / 2, -4.2, w, 4.2, 1);
    const corps = G.rect(-w / 2, -L, w, L - 5.8, 1);
    return { semelle, corps };
  },
};
const P = (o, x, y, rot) => { const r = {}; for (const k in o) r[k] = poser(o[k], x, y, rot); return r; };
const tout = o => union(...Object.values(o));

/** Ancre carrée (nœud), losange, ronde. */
const ancre = (x, y, s = 5) => G.rect(x - s / 2, y - s / 2, s, s, 0.6);
const ancreRonde = (x, y, r = 2.8) => G.circle(x, y, r);
const ancreLosange = (x, y, r = 3.6) => polyR([[x, y - r], [x + r, y], [x, y + r], [x - r, y]], 0.5);
/** Poignée de forme (série « formes ») : carré plein 5. */
const poignee = (x, y) => ancre(x, y, 5);
/** Contour (épaisseur e) d'une forme pleine. */
const contour = (d, e = 2.4) => moins(d, eroder(d, e));

/** Tirets le long d'un polygone fermé (pts). coins = true : un L plein à chaque angle (bras a) ; sinon les
 *  angles sont ouverts. w épaisseur, g jour visible (≥ 1,6), c longueur visée d'un tiret (centre). */
function tiretsPoly(pts, { w = 2.4, g = 1.8, c = 2.4, coins = true, a = 3.4 } = {}) {
  const n = pts.length, parts = [], G0 = g + w; // jour entre axes (bouts ronds) ; longueur visible d'un tiret = axe + w
  const U = (p, q) => { const L = Math.hypot(q[0] - p[0], q[1] - p[1]); return [(q[0] - p[0]) / L, (q[1] - p[1]) / L, L]; };
  const lg = i => U(pts[i], pts[(i + 1) % n])[2];
  const court = i => coins && lg(i) < 2 * a + G0;            // côté trop court pour un jour : tracé plein
  const bras = i => court(i) ? lg(i) / 2 + 0.01 : a;          // bras des coins posés sur le côté i
  for (let i = 0; i < n; i++) {
    const p = pts[i], q = pts[(i + 1) % n], [ux, uy, L] = U(p, q);
    if (!court(i)) {
      const s0 = coins ? a + G0 : G0 / 2, s1 = coins ? L - a - G0 : L - G0 / 2, Lm = s1 - s0;
      if (Lm > 0.2) {
        let k = Math.max(1, Math.round((Lm + G0) / (c + G0))); let cc = (Lm - (k - 1) * G0) / k;
        while (cc < 0.2 && k > 1) { k--; cc = (Lm - (k - 1) * G0) / k; }
        for (let j = 0; j < k; j++) { const t0 = s0 + j * (cc + G0), t1 = t0 + cc; parts.push(trait([[p[0] + ux * t0, p[1] + uy * t0], [p[0] + ux * t1, p[1] + uy * t1]], w)); }
      }
    }
    if (coins) { const o = pts[(i + n - 1) % n], [vx, vy] = U(p, o), bp = bras((i + n - 1) % n), bn = bras(i);
      parts.push(trait([[p[0] + vx * bp, p[1] + vy * bp], p, [p[0] + ux * bn, p[1] + uy * bn]], w)); }
  }
  return union(...parts);
}
/** Tirets le long d'une courbe fermée f(t), t ∈ [0,1) : n tirets, jour visible g. */
function tiretsCourbe(fn, n, { w = 2.4, g = 1.8, phase = 0 } = {}) {
  const N = 360, pts = []; for (let i = 0; i <= N; i++) pts.push(fn(i / N));
  const L = [0]; for (let i = 1; i <= N; i++) L.push(L[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const T = L[N], pas = T / n, cc = pas - (g + w), parts = [];
  const at = s => { s = ((s % T) + T) % T; let i = 1; while (i < N && L[i] < s) i++; const u = (s - L[i - 1]) / (L[i] - L[i - 1] || 1); return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * u, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * u]; };
  for (let j = 0; j < n; j++) { const s0 = phase * pas + j * pas, seg = []; for (let k = 0; k <= 8; k++) seg.push(at(s0 + cc * k / 8)); parts.push(trait(seg, w)); }
  return union(...parts);
}
const fEllipse = (cx, cy, rx, ry, a0 = -90) => t => { const a = (a0 + 360 * t) * RAD; return [cx + rx * Math.cos(a), cy + ry * Math.sin(a)]; };
/** Pointeur (flèche de sélection), pointe en (x,y), échelle k. */
const pointeur = (x = 5.4, y = 2.2, k = 1) => polyR([[0, 0], [0, 16.6], [4.2, 12.9], [7.1, 19.3], [9.6, 18.3], [6.8, 12], [12.1, 12]].map(([u, v]) => [x + u * k, y + v * k]), 0.7);
/** Étincelle à quatre branches (éclat). */
const eclat = (x, y, R) => { const k = R * 0.2; return `M${G.r1(x)} ${G.r1(y - R)}Q${G.r1(x + k)} ${G.r1(y - k)} ${G.r1(x + R)} ${G.r1(y)}Q${G.r1(x + k)} ${G.r1(y + k)} ${G.r1(x)} ${G.r1(y + R)}Q${G.r1(x - k)} ${G.r1(y + k)} ${G.r1(x - R)} ${G.r1(y)}Q${G.r1(x - k)} ${G.r1(y - k)} ${G.r1(x)} ${G.r1(y - R)}Z`; };

// Instruments au gabarit « instrument + trace » : pointe vers (9.6,14.4), corps vers le haut à droite.
const brosse = () => P(INST.pinceau(15.4), 9.6, 14.4);
const mine = () => P(INST.crayon(15.8), 9.6, 14.4);
const bloc = () => P(INST.gomme(13.4), 10.4, 13.6);

// ═══════════════════════════════════════ outils de base ═══════════════════════════════════════════════
I["dz-outil-vec-selection"] = () => [pl(pointeur(5.6, 2.2, 1.06))];
I["dz-outil-vec-noeud"] = () => { const p = pointeur(3, 2, 0.98); return [pl(ancre(18.6, 18.6, 6)), pa(contour(p, 2.2))]; };
I["dz-outil-vec-main"] = () => {
  const doigts = [[8.2, 12.6, 6.6, 5], [11.6, 12, 11.4, 3.2], [14.8, 12.4, 16.2, 4.2], [17.6, 14, 20, 7.8]].map(([a, b, c, d]) => pill(a, b, c, d, 2.6));
  const paume = rectR(6.4, 11, 13.6, 11, [2, 2.6, 5, 4.4]);
  const pouce = pill(7.4, 17.4, 3, 11.2, 2.8);
  return [pl(union(paume, pouce, ...doigts))];
};
I["dz-outil-vec-loupe"] = () => [pl(union(G.circle(9.8, 9.8, 7.6), pill(15, 15, 20.4, 20.4, 3.6)))];
I["dz-outil-vec-mesure"] = () => {
  const L = 23.2, h = 7.6, x0 = 12 - L / 2, y0 = 12 - h / 2; let d = G.rect(x0, y0, L, h, 1.2);
  const marques = []; for (let i = 0; i < 6; i++) { const x = x0 + 3 + i * 3.5; marques.push(G.rect(x - 0.8, y0 - 1, 1.6, i % 2 ? 3.6 : 5.4, 0)); }
  d = moins(d, ...marques); return [pl(placer(d, { rot: -45 }))];
};
I["dz-outil-vec-pipette"] = () => {
  // debout : poire (tête ronde) + collerette, tube effilé ; pointe en (0,0)
  const tube = `M-1.4 -11H1.4V-3L0 0L-1.4 -3Z`;
  const coll = G.rect(-3.4, -13.2, 6.8, 2.4, 0.8);
  const poire = union(G.circle(0, -17.6, 3.2), G.rect(-2.2, -17.6, 4.4, 3.4, 0.4));
  const pos = d => poser(d, 6.4, 17.4, 45);
  return [pl(union(pos(poire), pos(coll))), pl(pos(tube)), pa(M.goutte({ cx: 4.4, cy: 19.6, r: 2.8 }))];
};
I["dz-outil-photo-deplacer"] = () => {
  const c = [10.6, 10.6], R = 8.6;
  const croix = union(G.rect(c[0] - 1.2, c[1] - R + 4, 2.4, 2 * R - 8), G.rect(c[0] - R + 4, c[1] - 1.2, 2 * R - 8, 2.4),
    ...[[0, -1], [0, 1], [-1, 0], [1, 0]].map(([u, v]) => G.arrow(c[0] + u * 2, c[1] + v * 2, c[0] + u * R, c[1] + v * R, 2.4, 6.4, 4)));
  return [pl(croix), pa(pointeur(14.4, 12.8, 0.46))];
};

// ═══════════════════════════════════════ sélections ═══════════════════════════════════════════════════
const carre = (x, y, s) => [[x, y], [x + s, y], [x + s, y + s], [x, y + s]];
I["dz-outil-px-selection"] = () => [pl(tiretsPoly(carre(3.2, 3.2, 17.6), { a: 4, c: 3.2 }))];
I["dz-outil-px-selection-ellipse"] = () => [pl(tiretsCourbe(fEllipse(12, 12, 8.8, 7.2, -90), 8, { phase: 0.5 }))];
const lassoCorde = () => trait(lisse([[6.2, 15.4], [4.4, 17.8], [6.4, 20.4], [10.4, 20.6]], 10), 2.4);
I["dz-outil-px-lasso"] = () => {
  const boucle = placer(G.ring(13, 9.4, 8.8, 6.4), { rot: 0 }), b2 = placer(ellipse(13, 9.4, 8.8, 6.2), { rot: -14, cx: 13, cy: 9.4 });
  const anneau = moins(b2, placer(ellipse(13, 9.4, 6.4, 3.8), { rot: -14, cx: 13, cy: 9.4 }));
  return [pl(union(anneau, G.circle(6.4, 14.6, 2.4))), pa(lassoCorde())];
};
I["dz-outil-px-lasso-polygonal"] = () => {
  const pts = [[4.4, 9.6], [10, 2.6], [21.2, 4.2], [18.4, 14.2], [8.6, 15.2]];
  const dOut = polyR(pts, 0.6), anneau = moins(dOut, eroder(dOut, 2.4));
  return [pl(union(anneau, G.circle(6.4, 14.6, 2.4))), pa(lassoCorde())];
};
I["dz-outil-px-baguette"] = () => [
  pl(union(pill(3.6, 20.4, 13.4, 10.6, 3))),
  pa(eclat(17, 7, 4.4) + eclat(20.2, 13.4, 1.9) + eclat(10.8, 3.9, 1.9))];
I["dz-outil-px-selection-rapide"] = () => { const b = brosse(); return [pl(tout(b)), pa(tiretsCourbe(fEllipse(7.6, 16.2, 4.8, 4.8), 5, { w: 2.2, g: 1.7 }))]; };
I["dz-outil-photo-selection-objet"] = () => [pl(M.cube({ cx: 12, cy: 12, r: 5.6 })), pa(tiretsPoly(carre(3.2, 3.2, 17.6), { a: 4, c: 3 }))];
I["dz-outil-photo-selection-sujet"] = () => {
  const a = 4.6, w = 2.4, L = (x, y, sx, sy) => trait([[x + sx * a, y], [x, y], [x, y + sy * a]], w);
  const coins = union(L(3, 3, 1, 1), L(21, 3, -1, 1), L(3, 21, 1, -1), L(21, 21, -1, -1));
  return [pl(M.buste({ cx: 12, y: 5.6, w: 10.4, h: 13 })), pa(coins)];
};
I["dz-outil-photo-affiner-contour"] = () => { const b = brosse(); return [pl(tout(b)), pa(tiretsPoly(carre(3.2, 8.2, 12.6), { a: 3.4, c: 2 }))]; };
// modes de sélection : gabarit deux carrés A (haut-gauche) et B (bas-droite), recouvrement 6
const A = carre(3.2, 3.2, 12), B = carre(8.8, 8.8, 12);
I["dz-outil-photo-selection-nouvelle"] = () => [pl(tiretsPoly(carre(4, 4, 16), { coins: false, c: 2.6, g: 2 }))];
I["dz-outil-photo-selection-ajouter"] = () => [pl(tiretsPoly([[3.2, 3.2], [15.2, 3.2], [15.2, 8.8], [20.8, 8.8], [20.8, 20.8], [8.8, 20.8], [8.8, 15.2], [3.2, 15.2]], { a: 3, c: 2.4 }))];
I["dz-outil-photo-selection-intersection"] = () => [pl(G.rect(8.8, 8.8, 6.4, 6.4, 0.4)), pa(union(tiretsPoly(A, { a: 3, c: 2.4 }), tiretsPoly(B, { a: 3, c: 2.4 })))];
I["dz-outil-photo-selection-soustraire"] = () => [pl(tiretsPoly([[3.2, 3.2], [15.2, 3.2], [15.2, 8.8], [8.8, 8.8], [8.8, 15.2], [3.2, 15.2]], { a: 3, c: 2.4 })), pa(tiretsPoly(B, { a: 3, c: 2.4 }))];

// ═══════════════════════════════════════ peinture ═════════════════════════════════════════════════════
I["dz-outil-px-pinceau"] = () => [pl(M.pinceau({ k: 1.1 }))];
I["dz-outil-vec-pinceau"] = () => { const b = brosse();
  const fuseau = trait(lisse([[2.8, 21], [5.4, 18.6], [8.2, 19.6], [11.4, 20.4]], 12), u => 1.6 + 2.2 * Math.sin(Math.PI * u));
  return [pl(tout(b)), pa(fuseau)]; };
I["dz-outil-px-pinceau-melangeur"] = () => { const b = brosse(); return [pl(tout(b)), pa(M.goutte({ cx: 5.6, cy: 17.4, r: 3.8 }))]; };
I["dz-outil-photo-pinceau-historique"] = () => { const b = brosse(); return [pl(tout(b)), pa(M.flecheCourbe({ cx: 9, cy: 13.4, r: 5.8, e: 2.4, a0: -40, a1: -300, hw: 6, hl: 3.8 }))]; };
I["dz-outil-vec-tuiles"] = () => { const b = brosse(); return [pl(tout(b)), pa(G.ngon(5.6, 14.8, 3.6, 6, 0) + G.ngon(9.4, 18.4, 3.6, 6, 0))]; };
I["dz-outil-px-crayon"] = () => { const m = mine();
  return [pl(tout(m)), pa(G.rect(2.4, 18.6, 3.6, 3.6, 0.3) + G.rect(7.6, 18.6, 3.6, 3.6, 0.3) + G.rect(2.4, 13.4, 3.6, 3.6, 0.3))]; };
I["dz-outil-vec-crayon"] = () => { const m = mine();
  return [pl(tout(m)), pa(trait(lisse([[2.8, 12.4], [3.6, 18.6], [8, 20.6], [13.4, 19.6]], 12), 2.4))]; };
I["dz-outil-px-ligne"] = () => { const st = []; for (let i = 0; i < 4; i++) st.push(G.rect(2.6 + i * 4.2, 16 - i * 3.3, 6.2, 3.6, 0)); return [pl(union(...st))]; };
I["dz-outil-px-rectangle"] = () => { // carré aux angles « en marche de pixel » : un cran retiré dehors, un cran gardé dedans
  const cran = (x, y, s, k) => G.poly([[x + k, y], [x + s - k, y], [x + s - k, y + k], [x + s, y + k], [x + s, y + s - k], [x + s - k, y + s - k], [x + s - k, y + s], [x + k, y + s], [x + k, y + s - k], [x, y + s - k], [x, y + k], [x + k, y + k]]);
  return [pl(moins(cran(2.6, 2.6, 18.8, 2.6), cran(5.2, 5.2, 13.6, 2.6)))];
};
I["dz-outil-px-pot"] = () => { // seau couché vers la droite : cuve évasée, lèvre séparée, anse en travers ; la peinture tombe
  const cuve = polyR([[-5.6, -3.4], [5.6, -3.4], [4.4, 6.6], [-4.4, 6.6]], 1.2), levre = G.rect(-6.6, -7.2, 13.2, 2.4, 1.2);
  const anse = arc(0, -2, 8.2, 2, 215, 325);
  const pos = d => placer(d, { rot: 112, cx: 0, cy: 0, dx: 9.4, dy: 9.6 });
  return [pl(union(pos(cuve), pos(levre))), pa(M.goutte({ cx: 18.2, cy: 18.4, r: 3.2 }))];
};
I["dz-outil-px-degrade"] = () => { // bandes qui s'amincissent (le dégradé) au-dessus du geste : segment tiré entre deux poignées
  const bandes = rectR(2.6, 2.6, 6.4, 11.4, [1.4, 0.4, 0.4, 1.4]) + G.rect(10.8, 2.6, 4.2, 11.4, 0.4) + G.rect(16.8, 2.6, 2.4, 11.4, 0.4) + rectR(21, 2.6, 0.01, 11.4, [0, 0, 0, 0]);
  const seg = union(pill(5.4, 18.8, 18.6, 18.8, 2.2), G.circle(5.4, 18.8, 3), G.circle(18.6, 18.8, 3));
  return [pl(seg), pa(rectR(2.6, 2.6, 6.4, 11.4, [1.4, 0.4, 0.4, 1.4]) + G.rect(10.8, 2.6, 4.2, 11.4, 0.4) + G.rect(16.8, 2.6, 2.4, 11.4, 0.4) + G.rect(21, 2.6, 0.01, 0.01))];
};
I["dz-outil-px-symetrie"] = () => {
  const axe = []; for (let i = 0; i < 5; i++) { const t0 = 2.6 + i * 4.2; axe.push(pill(t0, 24 - t0, t0 + 2, 22 - t0, 2.2)); }
  const s1 = lisse([[3.4, 13.4], [5, 7.6], [10.4, 4.6]], 10), s2 = s1.map(([x, y]) => [24 - y, 24 - x]);
  const w = u => 2.2 + 1 * Math.sin(Math.PI * u);
  return [pl(union(trait(s1, w), trait(s2, w))), pa(union(...axe))];
};

// ═══════════════════════════════════════ gommes ═══════════════════════════════════════════════════════
I["dz-outil-px-gomme"] = () => { const g = bloc(); return [pl(tout(g)), pa(G.rect(2.4, 19.4, 10.4, 2.6, 1.3))]; };
I["dz-outil-px-gomme-magique"] = () => { const g = bloc(); return [pl(tout(g)), pa(eclat(6.2, 17.8, 4.6))]; };
I["dz-outil-px-gomme-fond"] = () => { const g = bloc();
  const ciseaux = union(G.ring(4.6, 20, 2.4, 0.9), G.ring(8.8, 20.6, 2.4, 0.9) , pill(5.4, 17.8, 9, 12.6, 2), pill(8.2, 18.4, 4.6, 12.8, 2));
  return [pl(tout(g)), pa(union(moins(G.circle(4.4, 19.8, 2.5), G.circle(4.4, 19.8, 0.9)), moins(G.circle(9.2, 19.8, 2.5), G.circle(9.2, 19.8, 0.9)), pill(5.6, 17.6, 8.6, 11.6, 2), pill(8, 17.6, 5, 11.6, 2)))]; };
I["dz-outil-vec-gomme"] = () => { const g = P(INST.gomme(10.4), 12.4, 11.4);
  const forme = moins(G.rect(2.6, 6, 15.4, 15.4, 2.4), G.circle(14.8, 9.2, 6.2));
  return [pl(tout(g)), pa(forme)]; };

// ═══════════════════════════════════════ formes (contour pâle + poignée carrée pleine en bas à droite) ═══
const forme = (d, h, e = 2.4) => [pl(poignee(...h)), pa(contour(d, e))];
const sur = (cx, cy, rx, ry, deg) => [cx + rx * Math.cos(deg * RAD), cy + ry * Math.sin(deg * RAD)];
I["dz-outil-vec-rectangle"] = () => forme(G.rect(2.6, 3.6, 17, 15, 1.4), [19.6, 18.6]);
I["dz-outil-vec-ellipse"] = () => forme(ellipse(11.4, 11.4, 9.2, 7.6), sur(11.4, 11.4, 9.2, 7.6, 42));
I["dz-outil-vec-triangle"] = () => forme(polyR([[10.8, 2.4], [19.4, 19.4], [2.4, 19.4]], 1), [19.4, 19.4]);
I["dz-outil-vec-polygone"] = () => forme(polyR(Array.from({ length: 5 }, (_, i) => pt(11.6, 11.6, 9.8, -90 + 72 * i)), 0.8), pt(11.6, 11.6, 9.8, 54));
I["dz-outil-vec-hexagone"] = () => forme(polyR(Array.from({ length: 6 }, (_, i) => pt(11.6, 11.2, 9.6, 60 * i)), 0.8), pt(11.6, 11.2, 9.6, 60));
I["dz-outil-vec-forme"] = () => { const c = [11.4, 12], v = pt(...c, 9.6, 30);
  return [pl(union(pill(...c, ...v, 2.4), G.circle(...c, 2.4), poignee(...v))), pa(contour(polyR(Array.from({ length: 6 }, (_, i) => pt(...c, 9.6, -90 + 60 * i)), 0.8)))]; };
I["dz-outil-vec-etoile"] = () => { const c = [11.6, 11.8], R0 = 9.8, pts = []; for (let i = 0; i < 10; i++) pts.push(pt(...c, i % 2 ? R0 * 0.48 : R0, -90 + 36 * i));
  return forme(polyR(pts, 0.6), pt(...c, R0, 54), 2.2); };
I["dz-outil-vec-engrenage"] = () => { const c = [11.4, 11.4];
  const roue = moins(M.engrenage({ cx: c[0], cy: c[1], r: 9.8, n: 6, moyeu: 0.01 }), G.circle(...c, 4.6));
  return [pl(poignee(...pt(...c, 9.2, 30))), pa(roue)]; };
I["dz-outil-vec-donut"] = () => { const c = [11.8, 11.8]; return [pl(poignee(...pt(...c, 8.4, 45))), pa(G.ring(...c, 9.6, 7.2) + G.ring(...c, 4.8, 2.4))]; };
I["dz-outil-vec-fleche"] = () => forme(polyR([[2.4, 8.4], [11.6, 8.4], [11.6, 3], [21.4, 11.8], [11.6, 20.6], [11.6, 15.2], [2.4, 15.2]], 0.8), [11.6, 19.4], 2.2);
I["dz-outil-vec-forme-perso"] = () => { const g = `M10.6 2.4C13 6.4 19.4 9.6 19.4 14.6A7.6 7.6 0 0 1 4.2 15.6C3.4 11.4 8 8.4 10.6 2.4Z`;
  return forme(placer(g, { dy: -0.8 }), [17.4, 17.8]); };
I["dz-outil-vec-spirale"] = () => { const pts = []; for (let i = 0; i <= 160; i++) { const t = i / 160, a = 4 * Math.PI * t, r = 1.2 + 8 * t; pts.push([12 + r * Math.cos(a - Math.PI / 2), 12 + r * Math.sin(a - Math.PI / 2)]); }
  return [pl(trait(pts, 2.4))]; };
I["dz-outil-vec-ligne"] = () => [pl(ancre(5, 19, 5.2) + ancre(19, 5, 5.2)), pa(pill(5, 19, 19, 5, 2.4))];

// ═══════════════════════════════════════ nœuds ════════════════════════════════════════════════════════
const bout = (x, y) => G.circle(x, y, 2.2);
I["dz-outil-vec-noeud-lisse"] = () => [pl(ancreRonde(12, 12, 3.6)), pa(union(pill(4.2, 16, 19.8, 8, 2.2), bout(4.2, 16), bout(19.8, 8)))];
I["dz-outil-vec-noeud-vif"] = () => [pl(ancre(12, 17, 6)), pa(union(pill(12, 17, 4, 5, 2.2), pill(12, 17, 20, 5, 2.2), bout(4, 5), bout(20, 5)))];
I["dz-outil-vec-noeud-intelligent"] = () => [pl(ancreLosange(12, 9.4, 4.4)), pa(arc(12, 19.4, 10, 2.4, 205, 335))];
const anneauOuvert = (a0, a1) => arc(12, 13, 8, 2.4, a0, a1);
I["dz-outil-vec-fermer-chemin"] = () => [pl(ancre(9.4, 5, 4.6) + ancre(14.6, 5, 4.6)), pa(anneauOuvert(-75, 255))];
I["dz-outil-vec-ouvrir-chemin"] = () => { const p = pt(12, 13, 8, -150), q = pt(12, 13, 8, -30);
  return [pl(ancre(...p, 4.8) + ancre(...q, 4.8)), pa(anneauOuvert(-30, 210))]; };
I["dz-outil-vec-fractionner"] = () => {
  const c = trait(lisse([[3.2, 16.6], [7.4, 11.4], [12, 12], [16.6, 12.6], [20.8, 7.4]], 10), 2.4);
  return [pl(G.rect(8.6, 8.6, 2.6, 6.8, 0.5) + G.rect(12.8, 8.6, 2.6, 6.8, 0.5)), pa(c)]; };
I["dz-outil-vec-relier"] = () => [
  pl(union(pill(6, 17.4, 18, 17.4, 2.4), ancre(5.4, 17.4, 5), ancre(18.6, 17.4, 5))),
  pa(trait(lisse([[3.4, 3.8], [3.8, 9], [5.4, 14]], 8), 2.4) + trait(lisse([[20.6, 3.8], [20.2, 9], [18.6, 14]], 8), 2.4))];
I["dz-outil-vec-lisser"] = () => {
  const lis = []; for (let i = 0; i <= 40; i++) { const x = 2.8 + 18.4 * i / 40; lis.push([x, 8.6 - 3.4 * Math.sin((x - 2.8) / 18.4 * 2 * Math.PI)]); }
  return [pl(trait(lis, 2.6)), pa(trait([[2.8, 20.6], [7.4, 14.4], [12, 20.6], [16.6, 14.4], [21.2, 20.6]], 2.2))]; };

// ═══════════════════════════════════════ dessin vectoriel ═════════════════════════════════════════════
I["dz-outil-vec-plume"] = () => {
  const bec = `M12 22.2C14.4 18.4 18.6 14.8 18.6 11.4L15.4 6.4H8.6L5.4 11.4C5.4 14.8 9.6 18.4 12 22.2Z`;
  return [pl(moins(bec, G.rect(11.2, 13.4, 1.6, 10), G.circle(12, 12.6, 1.9)) + G.rect(8.6, 1.8, 6.8, 2.8, 0.8))];
};
I["dz-outil-vec-couteau"] = () => {
  const lame = `M10.2 13.2H14.8V3.4C14.8 2.2 13.8 1.4 12.8 1.6C11 4.6 10.2 8.4 10.2 13.2Z`, manche = G.rect(10.3, 14.8, 4.4, 8, 1.8);
  const pos = d => placer(d, { rot: 42, cx: 12.4, cy: 12.4 });
  return [pl(pos(lame)), pa(pos(manche))];
};
I["dz-outil-vec-coin"] = () => [pl(arc(11.6, 10.6, 7.6, 2.6, 90, 180)), pa(pill(4, 3.6, 4, 12, 2.6) + pill(10, 18.2, 20.4, 18.2, 2.6))];
I["dz-outil-vec-constructeur"] = () => {
  const a = G.circle(8.4, 9.8, 6.8), b = G.circle(15.6, 9.8, 6.8);
  return [pl(G.plus(18.8, 18.8, 6.4, 2.2)), pl(inter(a, b)), pa(union(a, b))];
};

// ═══════════════════════════════════════ texte ════════════════════════════════════════════════════════
const petitT = (x, y, w = 9.4, h = 10.4, e = 2.4) => union(G.rect(x - w / 2, y, w, e, 0.5), G.rect(x - e / 2, y, e, h, 0.5));
I["dz-outil-vec-texte"] = () => [pl(M.lettreT({ k: 0.8, dx: -3.2 })), pa(union(G.rect(17.7, 3, 2.4, 18, 0.4), G.rect(16.2, 3, 5.4, 2.2, 1.1), G.rect(16.2, 18.8, 5.4, 2.2, 1.1)))];
I["dz-outil-vec-cadre-texte"] = () => {
  const cadre = contour(G.rect(4.2, 4.2, 15.6, 15.6, 0.6), 2), poig = [[4.2, 4.2], [19.8, 4.2], [4.2, 19.8], [19.8, 19.8]].map(([x, y]) => ancre(x, y, 4.6)).join("");
  return [pl(petitT(12, 7.8, 8.6, 8.6)), pa(union(cadre, poig))];
};
I["dz-outil-vec-texte-sur-chemin"] = () => [
  pl(placer(petitT(10, 3.4, 10.4, 10.6, 2.6), { rot: -24, cx: 10, cy: 8.6 })),
  pa(trait(lisse([[3.4, 20.4], [9.6, 19], [15.6, 15.4], [20.6, 10]], 12), 2.4))];

// ═══════════════════════════════════════ vitrail ══════════════════════════════════════════════════════
/** Pièces d'une région séparées en sous-chemins extérieurs (aucune pièce trouée ici). */
const pieces = d => d.split(/(?=M)/).filter(s => s.trim());
const centre = d => { const p = M.aplatir(d)[0]; let x = 0, y = 0; p.forEach(q => { x += q[0]; y += q[1]; }); return [x / p.length, y / p.length]; };
I["dz-outil-vec-vitrail-grille"] = () => {
  const cadre = G.rect(3, 3, 18, 18, 1.4), pleins = [], pales = [];
  for (let i = -4; i <= 4; i++) for (let j = -4; j <= 4; j++) {
    const u0 = 24 + 7.4 * i - 3.7 + 0.8, u1 = u0 + 7.4 - 1.6, v0 = 7.4 * j - 3.7 + 0.8, v1 = v0 + 7.4 - 1.6;
    const X = (u, v) => [(u + v) / 2, (u - v) / 2];
    const cell = inter(cadre, G.poly([X(u0, v0), X(u1, v0), X(u1, v1), X(u0, v1)]));
    if (!cell || M.aire(cell) < 3) continue;
    (Math.abs(i) + Math.abs(j) > 1 ? pales : pleins).push(cell);
  }
  return [pl(union(...pleins)), pa(union(...pales))];
};
I["dz-outil-vec-vitrail-plomb"] = () => {
  const cadre = G.rect(3, 3, 18, 18, 1.4), w = 1.6;
  const plombs = union(pill(1, 10.6, 23, 7.4, w), pill(9.4, 1, 12.4, 23, w), pill(11, 14.6, 23, 17.8, w), pill(1, 16.6, 11, 13.6, w), pill(16.6, 1, 16.4, 8.4, w));
  const ps = pieces(moins(cadre, plombs)).sort((a, b) => centre(a)[1] - centre(b)[1] || centre(a)[0] - centre(b)[0]);
  const pleins = [], pales = [];
  ps.forEach((p, i) => (i % 2 ? pales : pleins).push(p));
  return [pl(union(...pleins)), pa(union(...pales))];
};
I["dz-outil-vec-vitrail-arc"] = () => {
  const ogive = `M3.6 21.6V11.4C3.6 7 7.6 3.8 12 1.8C16.4 3.8 20.4 7 20.4 11.4V21.6Z`;
  const ps = pieces(moins(ogive, G.rect(11.2, 0, 1.6, 24), G.rect(0, 12.2, 24, 1.6)));
  const hg = ps.filter(p => centre(p)[0] < 12 && centre(p)[1] < 12.6), bd = ps.filter(p => centre(p)[0] > 12 && centre(p)[1] > 12.6);
  const autres = ps.filter(p => !hg.includes(p) && !bd.includes(p));
  return [pl(union(...hg, ...bd)), pa(union(...autres))];
};
I["dz-outil-vec-vitrail-rosette"] = () => {
  const c = [12, 12], festons = union(...Array.from({ length: 6 }, (_, i) => G.circle(...pt(...c, 6.2, -90 + 60 * i), 4)), G.circle(...c, 7));
  let petales = moins(festons, G.circle(...c, 4.6)); for (let i = 0; i < 6; i++) petales = moins(petales, pill(...pt(...c, 3, -60 + 60 * i), ...pt(...c, 12, -60 + 60 * i), 1.6));
  return [pl(petales), pa(G.circle(...c, 3))];
};
I["dz-outil-vec-halo"] = () => { const c = [12, 12], r = []; for (let i = 0; i < 8; i++) r.push(pill(...pt(...c, 8, -90 + 45 * i), ...pt(...c, 9, -90 + 45 * i), 2.4));
  return [pl(G.ring(...c, 5, 2.6)), pa(union(...r))]; };
I["dz-outil-vec-rayons"] = () => {
  const o = [12, 21.6], n = 5, a0 = -168, a1 = -12, pas = (a1 - a0) / n, pleins = [], pales = [];
  for (let i = 0; i < n; i++) {
    let w = G.poly([o, pt(...o, 30, a0 + i * pas), pt(...o, 30, a0 + (i + 1) * pas)]);
    w = moins(inter(w, G.rect(2, 2, 20, 20)), G.circle(...o, 5.4), pill(...o, ...pt(...o, 30, a0 + i * pas), 1.6), pill(...o, ...pt(...o, 30, a0 + (i + 1) * pas), 1.6));
    (i % 2 ? pales : pleins).push(w);
  }
  return [pl(union(...pleins)), pa(union(...pales))];
};
I["dz-outil-vec-iris"] = () => {
  const centrale = `M12 2.2C14.8 5 15.2 9.4 12 13.2C8.8 9.4 9.2 5 12 2.2Z`;
  const cote = trait(lisse([[10.4, 14.2], [6.6, 13.4], [3.6, 10.4], [4.4, 6.8], [6.6, 7.4]], 10), u => 3 - 0.9 * u);
  const cote2 = placer(cote, { miroir: true });
  return [pl(union(centrale, cote, cote2, G.rect(7.6, 15.4, 8.8, 2.4, 1.2))), pa(pill(12, 19.4, 12, 20.6, 2.6) + pill(12.6, 19.8, 16.6, 18.8, 2.2))];
};

// ═══════════════════════════════════════ planches, tranches, couleur ══════════════════════════════════
I["dz-outil-vec-apparence"] = () => [pl(G.circle(8.8, 15.2, 6.6)), pa(G.ring(14.6, 9.4, 7.4, 4.8))];
I["dz-outil-vec-plan-de-travail"] = () => [pl(G.rect(2.6, 2.4, 10.4, 3.2, 0.8)), pa(contour(G.rect(2.6, 7.4, 18.8, 14.2, 1.4), 2.4))];
const tranche = (x, y, s, k) => { const coin = G.rect(x, y, k, k, 1.2), un = union(G.rect(x + k / 2 - 0.4, y + k * 0.22, 1.8, k * 0.58, 0.2), pill(x + k / 2 + 0.2, y + k * 0.3, x + k / 2 - 1.8, y + k * 0.44, 1.6));
  return { coin: moins(coin, un), cadre: contour(G.rect(x, y, s, s, 1.4), 2.4) }; };
I["dz-outil-vec-tranche"] = () => { const t = tranche(2.6, 2.6, 18.8, 9.4); return [pl(t.coin), pa(t.cadre)]; };
I["dz-outil-photo-selection-tranche"] = () => { const t = tranche(2.4, 2.4, 15, 8); return [pl(pointeur(12.4, 10.4, 0.62)), pa(union(t.coin, t.cadre))]; };
I["dz-outil-vec-transparence"] = () => {
  const cs = []; const x0 = 12, w = (21.4 - x0) / 3, y0 = 2.6, h = 18.8 / 6;
  for (let i = 0; i < 6; i++) for (let j = 0; j < 3; j++) if ((i + j) % 2 === 0) cs.push(G.rect(x0 + j * w - 0.05, y0 + i * h - 0.05, w + 0.1, h + 0.1));
  return [pl(rectR(2.6, 2.6, 7.8, 18.8, [1.4, 0, 0, 1.4])), pa(union(...cs))];
};

// ═══════════════════════════════════════ retouche ═════════════════════════════════════════════════════
const pansement = (cx, cy, L, W) => { let d = G.rect(cx - L / 2, cy - W / 2, L, W, W / 2);
  d = moins(d, ...[[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([u, v]) => G.circle(cx + u * 1.8, cy + v * 1.8, 0.85)));
  return placer(d, { rot: -45, cx, cy }); };
I["dz-outil-photo-correcteur"] = () => [pl(pansement(12, 12, 23, 9))];
I["dz-outil-photo-correcteur-tache"] = () => [pl(pansement(13.4, 10.6, 17.6, 8.4)), pa(tiretsCourbe(fEllipse(10.4, 13.6, 7.6, 7.6, 0), 7))];
I["dz-outil-photo-tampon"] = () => [pl(union(G.circle(12, 5, 3.2), G.rect(10.6, 6.4, 2.8, 6, 0.4), rectR(3.6, 11.6, 16.8, 5.6, [2.4, 2.4, 1, 1]))), pa(G.rect(3.6, 19, 16.8, 2.6, 1.3))];
I["dz-outil-photo-piece"] = () => [
  pl(G.rect(13, 2.6, 8.4, 8.4, 1.2)),
  pl(union(pill(5.4, 10.4, 5.4, 5.4, 2.4), pill(5.4, 5.4, 8, 5.4, 2.4), G.poly([[7.4, 2.4], [11.4, 5.4], [7.4, 8.4]]))),
  pa(tiretsPoly(carre(3.2, 12.4, 8.4), { a: 1.9, c: 1.6, g: 1.7 }))];

// ═══════════════════════════════════════ retouche locale ══════════════════════════════════════════════
I["dz-outil-photo-flou"] = () => [pl(M.goutte())];
I["dz-outil-photo-nettete"] = () => [pl(polyR([[12, 2], [12, 21.6], [5.6, 21.6]], 0.6)), pa(polyR([[12, 2], [18.4, 21.6], [12, 21.6]], 0.6))];
I["dz-outil-photo-eponge"] = () => [pl(moins(`M2.6 8.4C2.6 5.4 5 4.6 7.4 5.4C9.4 6 10.6 4.2 13 4.6C15.2 5 16 6.2 18.2 5.4C20.4 4.6 21.4 6.2 21.4 8.4V16.6C21.4 18.8 19.8 19.8 17.6 19.6C15.6 19.4 14.4 20.4 12 20C9.6 19.6 8.6 19.4 6.4 19.8C4.2 20.2 2.6 19 2.6 16.8Z`,
  G.circle(7, 9.6, 1.6), G.circle(13.4, 9, 1.3), G.circle(17.6, 11.4, 1.6), G.circle(9.6, 15.4, 1.4), G.circle(15.2, 15.6, 1.2), G.circle(5.4, 15.4, 0.9)))];
I["dz-outil-photo-doigt"] = () => {
  const poing = rectR(9.8, 10.6, 11.6, 11.4, [3, 3.4, 3.4, 3.4]);
  return [pl(pill(12.2, 13, 4, 4.8, 3.2)), pa(moins(poing, G.rect(14.6, 14.6, 8, 1.6), G.rect(14.6, 18, 8, 1.6)))];
};
I["dz-outil-photo-densite-plus"] = () => {
  const anneau = G.ring(7.8, 9, 5, 2.4);
  const doigts = [[13.8, 12, 14.4, 3.4], [17, 12.4, 18.4, 4.6], [19.8, 13.6, 21.2, 8.2]].map(([a, b, c, d]) => pill(a, b, c, d, 2.6));
  return [pl(union(anneau, rectR(9.4, 11.4, 12, 10.6, [2, 2.4, 5, 4.4]), ...doigts))];
};
I["dz-outil-photo-densite-moins"] = () => [pl(G.circle(15, 9, 6)), pa(pill(11, 13, 3.8, 20.2, 2.6))];

// ═══════════════════════════════════════ divers ═══════════════════════════════════════════════════════
I["dz-outil-photo-compteur"] = () => [pl(moins(G.circle(16.8, 16.8, 5.2), G.rect(16, 14, 1.8, 6, 0.2), pill(16.4, 14.6, 14.6, 16, 1.6))), pa(G.plus(9.6, 9.6, 15.2, 2.4))];
I["dz-outil-photo-recadrer"] = () => [pl(union(G.rect(5, 2.4, 2.6, 16.6, 0.6), G.rect(5, 16.4, 16.6, 2.6, 0.6), G.rect(2.4, 5, 16.6, 2.6, 0.6), G.rect(16.4, 5, 2.6, 16.6, 0.6)))];

// ═══════════════════════════════════════ profils du pinceau vectoriel (même trajet, seul le profil change) ═
const trajet = () => lisse([[4.6, 16.2], [8.6, 8.6], [15.4, 15.4], [19.4, 7.8]], 14);
I["dz-outil-vec-profil-plat"] = () => [pl(trait(trajet(), 4))];
I["dz-outil-vec-profil-fuseau"] = () => [pl(trait(trajet(), u => 1.4 + 5 * Math.sin(Math.PI * u)))];
I["dz-outil-vec-profil-calligraphie"] = () => { const p = trajet(), n = [2.5, -2.5], q = [];
  for (let i = 0; i + 1 < p.length; i++) { const a = p[i], b = p[i + 1]; q.push(G.poly([[a[0] + n[0], a[1] + n[1]], [b[0] + n[0], b[1] + n[1]], [b[0] - n[0], b[1] - n[1]], [a[0] - n[0], a[1] - n[1]]])); }
  return [pl(union(...q))]; };

// ═══════════════════════════════════════ écriture ═════════════════════════════════════════════════════
if (require.main === module) {
  const filtre = process.argv[2] || "";
  let n = 0;
  for (const [cle, fn] of Object.entries(I)) {
    if (filtre && !cle.includes(filtre)) continue;
    fs.writeFileSync(path.join(OUT, cle + ".svg"), M.icone(fn()));
    n++;
  }
  console.log(n + " icônes écrites dans " + OUT);
}
module.exports = I;
