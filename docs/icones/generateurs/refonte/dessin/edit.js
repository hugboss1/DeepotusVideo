// Mission « edit » : toutes les clés de la famille edit (lexique.json). Usage : node dessin/edit.js [filtre]
// Chaque icône = liste de calques DU HAUT VERS LE BAS passée à M.icone (réserve monochrome automatique).
// Séries (CHARTE §6) : un GABARIT par série, seule la partie porteuse de la différence change.
"use strict";
const fs = require("fs"), path = require("path");
const G = require("../geo.js"), M = require("../motifs.js");
const OUT = path.join(__dirname, "..", "svg");
fs.mkdirSync(OUT, { recursive: true });
const PALE = .38;
const pl = (d, x = {}) => ({ d, op: 1, ...x }), pa = (d, x = {}) => ({ d, op: PALE, ...x });
const badge = type => ({ d: M.badge(type), op: 1, reserve: M.RES_BADGE });
const { union, moins, inter, placer, arc, rectR, polyR, pt, trait, lisse, pill, ellipse } = M;
const R = G.rect;
const I = {};
// transformations de calques entiers (séries orientées)
const tourne = (cs, rot) => cs.map(c => ({ ...c, d: placer(c.d, { rot }) }));
const miroir = cs => cs.map(c => ({ ...c, d: placer(c.d, { miroir: true }) }));
const retourneV = cs => cs.map(c => ({ ...c, d: placer(c.d, { miroir: true, rot: 180 }) }));
// flèche double (deux flèches depuis le milieu)
const double = (x1, y1, x2, y2, w = 2.6, hw = 7, hl = 4.8) => { const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
  return union(G.arrow(mx, my, x1, y1, w, hw, hl), G.arrow(mx, my, x2, y2, w, hw, hl)); };
// lettre T sans pied : barre + fût
const T = (x, y, w, h, b = 3, f = 3.2) => union(R(x, y, w, b, 0.6), R(x + w / 2 - f / 2, y, f, h, 0.6));
// anneau rectangulaire
const cadre = (x, y, w, h, e = 2.2, r = 1.4) => R(x, y, w, h, r) + R(x + e, y + e, w - 2 * e, h - 2 * e, Math.max(0.4, r - e / 2));
// pointillés : retire des fentes (rectangles) d'un contour
const fentes = (d, rs) => moins(d, ...rs);
// anneau circulaire en tirets : n fentes radiales de largeur g
const anneauTirets = (cx, cy, r, e, n, g = 1.8, a0 = 0) => {
  const cuts = []; for (let i = 0; i < n; i++) { const a = a0 + i * 360 / n; cuts.push(pill(...pt(cx, cy, r - e, a), ...pt(cx, cy, r + e, a), g)); }
  return moins(G.ring(cx, cy, r + e / 2, r - e / 2), ...cuts);
};
// polygone incliné (oblique) : x' = x + (cy - y)·k
const oblique = (pts, k = 0.25, cy = 12) => pts.map(([x, y]) => [x + (cy - y) * k, y]);
// forme fermée lissée (contour polaire)
const blob = (cx, cy, rf, n = 72) => { const p = []; for (let i = 0; i < n; i++) { const a = i * 2 * Math.PI / n; const r = rf(a); p.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); } return G.poly(p); };

// ═══════════════════════════ Série « alignements » (6) ═════════════════════════════════════════════════
// Gabarit : barre de référence pleine 2,6 × 20 ; deux blocs pâles de 5,4 d'épaisseur (long 15,9 / court 10).
const ALIGN_BORD = () => [pl(R(2, 2, 2.6, 20, 1.3)), pa(R(6.1, 4.4, 15.9, 5.4, 1.4) + R(6.1, 14.2, 10, 5.4, 1.4))];
const ALIGN_AXE = () => [pl(R(10.7, 2, 2.6, 20, 1.3)), pa(R(3, 4.4, 18, 5.4, 1.4) + R(6, 14.2, 12, 5.4, 1.4))];
I["dz-edit-aligner-gauche"] = () => ALIGN_BORD();
I["dz-edit-aligner-droite"] = () => miroir(ALIGN_BORD());
I["dz-edit-aligner-haut"] = () => tourne(ALIGN_BORD(), 90);
I["dz-edit-aligner-bas"] = () => tourne(ALIGN_BORD(), -90);
I["dz-edit-aligner-centre-h"] = () => ALIGN_AXE();
I["dz-edit-aligner-centre-v"] = () => tourne(ALIGN_AXE(), 90);

// ═══════════════════════════ Série « distributions » (2) ═══════════════════════════════════════════════
// Gabarit : deux bornes pâles pleine hauteur, trois blocs pleins de 2,8 à écarts égaux (1,7).
const DISTRIB = () => [pl(R(6.1, 5.5, 2.8, 13, 1) + R(10.6, 5.5, 2.8, 13, 1) + R(15.1, 5.5, 2.8, 13, 1)),
  pa(R(2, 2, 2.4, 20, 1.2) + R(19.6, 2, 2.4, 20, 1.2))];
I["dz-edit-distribuer-h"] = () => DISTRIB();
I["dz-edit-distribuer-v"] = () => tourne(DISTRIB(), 90);

// ═══════════════════════════ Série « égaliser » (2) ════════════════════════════════════════════════════
const EGAL = () => [pl(double(18.8, 2, 18.8, 22, 2.6, 6.4, 4.6)), pa(R(2, 4, 4.6, 16, 1.2) + R(8.4, 4, 4.6, 16, 1.2))];
I["dz-edit-meme-hauteur"] = () => EGAL();
I["dz-edit-meme-largeur"] = () => tourne(EGAL(), 90);

// ═══════════════════════════ Série « pile » (4) ════════════════════════════════════════════════════════
// Gabarit : deux plaques pâles à gauche ; à droite la flèche pleine (courte = un rang, longue + butée = tout).
const PLAQUES = () => pa(M.plaque({ cx: 8, cy: 7.4, w: 12.6, h: 5.6 }) + M.plaque({ cx: 8, cy: 16.6, w: 12.6, h: 5.6 }));
// un rang : flèche courte dans la moitié vers laquelle on va ; tout : flèche pleine hauteur qui bute sur une barre.
I["dz-edit-monter"] = () => [pl(G.arrow(18.8, 13.6, 18.8, 2.2, 2.6, 6.4, 5.2)), PLAQUES()];
I["dz-edit-descendre"] = () => [pl(G.arrow(18.8, 10.4, 18.8, 21.8, 2.6, 6.4, 5.2)), PLAQUES()];
I["dz-edit-premier-plan"] = () => [pl(R(15.6, 2, 6.4, 2.4, 1.2)), pl(G.arrow(18.8, 22, 18.8, 6, 2.6, 6, 5)), PLAQUES()];
I["dz-edit-arriere-plan"] = () => [pl(R(15.6, 19.6, 6.4, 2.4, 1.2)), pl(G.arrow(18.8, 2, 18.8, 18, 2.6, 6, 5)), PLAQUES()];

// ═══════════════════════════ Série « booléens » (4) ════════════════════════════════════════════════════
// Gabarit : disques A (9,4 ; 9,4) et B (14,6 ; 14,6), rayon 7,2. Forme pleine = résultat ; contours pâles = opérandes.
const DA = G.circle(9.4, 9.4, 7.2), DB = G.circle(14.6, 14.6, 7.2);
const ANA = G.ring(9.4, 9.4, 7.2, 5), ANB = G.ring(14.6, 14.6, 7.2, 5);
I["dz-edit-union"] = () => [pl(union(DA, DB))];
I["dz-edit-soustraire"] = () => [pl(moins(DA, DB)), pa(ANB)];
I["dz-edit-intersection"] = () => [pl(inter(DA, DB)), pa(union(ANA, ANB))];
I["dz-edit-division"] = () => { const lens = inter(DA, DB), z = M.dilater(lens, 1.8);
  return [pl(lens + placer(moins(DA, z), { dx: -0.6, dy: -0.6 }) + placer(moins(DB, z), { dx: 0.6, dy: 0.6 }))]; };

// ═══════════════════════════ Série « texte-alignement » (8) ════════════════════════════════════════════
// Gabarit : quatre lignes de 2,6 au pas de 5,4 dans 2–22 ; seules longueurs et calage changent.
const LIGNES = (longs, cal) => [pl(longs.map((L, i) => { const c = Array.isArray(cal) ? cal[i] : cal;
  const x = c === "g" ? 2 : c === "d" ? 22 - L : 12 - L / 2; return R(x, 2.6 + i * 5.4, L, 2.6, 1.3); }).join(""))];
I["dz-edit-texte-aligner-gauche"] = () => LIGNES([20, 12, 16, 9], "g");
I["dz-edit-texte-aligner-centre"] = () => LIGNES([20, 12, 16, 8], "c");
I["dz-edit-texte-aligner-droite"] = () => LIGNES([20, 12, 16, 9], "d");
I["dz-edit-justifier"] = () => LIGNES([20, 20, 20, 20], "g");
I["dz-edit-justifier-gauche"] = () => LIGNES([20, 20, 20, 7], "g");
I["dz-edit-justifier-centre"] = () => LIGNES([20, 20, 20, 7], ["g", "g", "g", "c"]);
I["dz-edit-justifier-droite"] = () => LIGNES([20, 20, 20, 7], ["g", "g", "g", "d"]);

// ═══════════════════════════ Série « texte-style » (7) ═════════════════════════════════════════════════
// Gabarit : lettre pleine sur la hauteur de capitale 2,5–21,5 ; marque (trait, barre, flèche, petite lettre) pâle.
const LET_B = () => moins(union(R(4.6, 2.5, 4.6, 19, 0.8), rectR(4.6, 2.5, 12.6, 9.8, [0.8, 4.8, 4.8, 0]), rectR(4.6, 11.1, 14.2, 10.4, [0, 5.2, 5.2, 0.8])),
  rectR(9.2, 6.2, 3.8, 2.6, [0, 1.3, 1.3, 0]), rectR(9.2, 14.6, 4.8, 3.4, [0, 1.7, 1.7, 0]));
I["dz-edit-texte-gras"] = () => [pl(LET_B())];
I["dz-edit-texte-italique"] = () => [pl(union(polyR(oblique([[7.2, 2.5], [16.8, 2.5], [16.8, 5.3], [7.2, 5.3]]), 0.6),
  G.poly(oblique([[10.3, 4], [13.7, 4], [13.7, 20], [10.3, 20]])), polyR(oblique([[7.2, 18.7], [16.8, 18.7], [16.8, 21.5], [7.2, 21.5]]), 0.6)))];
I["dz-edit-texte-souligne"] = () => [pl(`M4.8 2.5H9.4V10.6A2.6 2.6 0 0 0 14.6 10.6V2.5H19.2V10.6A7.2 7.2 0 0 1 4.8 10.6Z`), pa(R(3, 19.6, 18, 2.4, 1.2))];
const LET_S = () => union(arc(12, 7.6, 3.6, 3.2, 90, 330), arc(12, 14.8, 3.6, 3.2, 270, 510));
I["dz-edit-texte-barre"] = () => [pl(LET_S()), pa(R(2, 10.7, 3.6, 2.6, 1.3) + R(18.4, 10.7, 3.6, 2.6, 1.3))];
I["dz-edit-texte-capitales"] = () => [pl(T(2, 3, 9.2, 18) + T(12.8, 3, 9.2, 18))];
I["dz-edit-texte-petites-capitales"] = () => [pl(T(2, 2.5, 11.6, 19, 3.2, 3.4)), pa(T(15.2, 10, 6.8, 11.5, 2.6, 2.8))];
I["dz-edit-orientation-texte"] = () => [pl(T(2, 2.5, 12, 19, 3.2, 3.4)), pa(double(18.8, 2, 18.8, 22, 2.6, 6, 4.6))];

// ═══════════════════════════ Série « anim-mots » (3) : la lettre A ═════════════════════════════════════
I["dz-edit-anim-couleur"] = () => { const vague = trait(lisse([[3, 20], [7, 18.2], [12, 20.2], [17, 18.2], [21, 20]], 10), 2.4);
  const a = union(G.ring(16.4, 12.2, 3.9, 1.7), R(18.2, 8.3, 2.4, 7.8, 1));
  return [pl(M.lettreA({ k: 0.66, dx: -4, dy: -3.6 })), pl(vague), pa(a)]; };
I["dz-edit-anim-halo"] = () => [pl(M.lettreA({ k: 0.56, dy: 0.2 })), pa(G.ring(12, 12, 10.2, 8))];
I["dz-edit-anim-rebond"] = () => [pl(M.lettreA({ k: 0.56, dy: -4.4 })), pa(arc(12, 22, 9.4, 2.4, 180, 360) + R(2, 20.4, 4, 2.2, 1.1) + R(18, 20.4, 4, 2.2, 1.1))];

// ═══════════════════════════ Série « couleur » (5) ═════════════════════════════════════════════════════
I["dz-edit-couleur-fond"] = () => [pl(R(2, 2, 12.4, 12.4, 1.4)), pa(cadre(9.6, 9.6, 12.4, 12.4, 2.6))];
I["dz-edit-couleur-contour"] = () => [pl(cadre(2, 2, 12.4, 12.4, 3.2)), pa(R(9.6, 9.6, 12.4, 12.4, 1.4))];
I["dz-edit-couleurs-defaut"] = () => [pl(R(2, 11.4, 10.6, 10.6, 1.4)), pa(R(8.4, 6, 10.6, 10.6, 1.4))];
I["dz-edit-echanger-couleurs"] = () => [pl(union(R(6, 5.1, 6.6, 2.6), arc(12.4, 11.6, 5.2, 2.6, 270, 360), R(16.3, 11.4, 2.6, 5.4),
  G.poly([[7.6, 2], [2, 6.4], [7.6, 10.8]]), G.poly([[13.2, 16.4], [17.6, 22], [22, 16.4]])))];
I["dz-edit-sans-couleur"] = () => [pl(pill(2.6, 21.4, 21.4, 2.6, 2.8)), pa(R(4, 4, 16, 16, 1.4))];

// ═══════════════════════════ Série « grouper » (2) ═════════════════════════════════════════════════════
// crochet d'angle en L : sommet en (x, y), branches de longueur l vers (sx, sy)
const coin = (x, y, sx, sy, l = 6) => union(R(sx > 0 ? x : x - l, sy > 0 ? y : y - 2.4, l, 2.4, 1.2), R(sx > 0 ? x : x - 2.4, sy > 0 ? y : y - l, 2.4, l, 1.2));
const CROCHETS = (l = 6) => coin(2, 2, 1, 1, l) + coin(22, 2, -1, 1, l) + coin(2, 22, 1, -1, l) + coin(22, 22, -1, -1, l);
I["dz-edit-grouper"] = () => [pl(R(6, 6, 5.2, 5.2, 0.8) + R(12.8, 12.8, 5.2, 5.2, 0.8)), pa(CROCHETS())];
I["dz-edit-degrouper"] = () => [pl(R(2, 2, 7.6, 7.6, 1) + R(14.4, 14.4, 7.6, 7.6, 1)), pa(coin(22, 2, -1, 1, 7) + coin(2, 22, 1, -1, 7))];

// ═══════════════════════════ Série « symboles » (3) ════════════════════════════════════════════════════
I["dz-edit-lier"] = () => [pl(M.chaine())];
I["dz-edit-detacher"] = () => { const lien = (garde, dx, dy) => placer(moins(G.rect(6, 8.3, 12, 7.4, 3.7) + G.rect(8.4, 10.7, 7.2, 2.6, 1.3), garde), { rot: -45, dx, dy });
  const A = lien(R(0, 0, 11.2, 24), 3.4, -3.4), B = lien(R(12.8, 0, 12, 24), -3.4, 3.4);
  return [pl(A + B), pa(pill(6.6, 7.4, 4.8, 5.6, 2.2) + pill(17.4, 16.6, 19.2, 18.4, 2.2) + pill(8.2, 3.6, 7.6, 2.4, 2.2) + pill(15.8, 20.4, 16.4, 21.6, 2.2))]; };
I["dz-edit-symbole"] = () => { const los = cx => G.poly([[cx, 3], [cx + 5, 12], [cx, 21], [cx - 5, 12]]);
  const creux = moins(los(17), G.poly([[17, 7.4], [19.4, 12], [17, 16.6], [14.6, 12]]));
  const tirets = moins(creux, R(13.6, 5.6, 7, 1.8), R(13.6, 16.6, 7, 1.8));
  return [pl(polyR([[7, 3], [12, 12], [7, 21], [2, 12]], 0.6)), pa(tirets)]; };

// ═══════════════════════════ Série « repères » (4) ═════════════════════════════════════════════════════
I["dz-edit-grille"] = () => { let g = R(2, 2, 20, 20, 1.4); // quadrillage 3 × 3 d'un seul tenant : traits de 2, cases de 4,67
  for (const i of [0, 1, 2]) for (const j of [0, 1, 2]) g = moins(g, R(4 + j * 6, 4 + i * 6, 4, 4, 0.4));
  return [pl(g)]; };
I["dz-edit-grille-hex"] = () => { const r = 5.6, dx = r * Math.cos(Math.PI / 6), c = 7.8, e = 2.54;

  const H = [[12 - dx, c], [12 + dx, c], [12, c + 1.5 * r]];
  return [pl(union(...H.map(([x, y]) => moins(G.ngon(x, y, r + e / 2, 6, -90), G.ngon(x, y, r - e / 2, 6, -90)))))]; };
I["dz-edit-reperes"] = () => { const m = []; for (const [x, sx] of [[6.6, -1], [17.4, 1]]) for (const [y, sy] of [[6.6, -1], [17.4, 1]]) {
    m.push(R(sx < 0 ? x : x - 2.2, sy < 0 ? 2 : 19, 2.2, 3, 1.1), R(sx < 0 ? 2 : 19, sy < 0 ? y : y - 2.2, 3, 2.2, 1.1)); }
  return [pl(m.join("")), pa(R(6.6, 6.6, 10.8, 10.8, 1.2))]; };
I["dz-edit-cadres-edition"] = () => { const h = [[2, 4], [16.8, 4], [2, 14.8], [16.8, 14.8]].map(([x, y]) => R(x, y, 5.2, 5.2, 0.8)).join("");
  const traits = R(8.7, 4.3, 2.6, 2.2, 0.6) + R(12.7, 4.3, 2.6, 2.2, 0.6) + R(8.7, 17.5, 2.6, 2.2, 0.6) + R(12.7, 17.5, 2.6, 2.2, 0.6) + R(2.3, 10.7, 2.2, 2.6, 0.6) + R(19.5, 10.7, 2.2, 2.6, 0.6);
  return [pl(h), pa(traits)]; };

// ═══════════════════════════ Transformations ═══════════════════════════════════════════════════════════
const MIROIR = () => [pl(R(11, 2, 2, 4, 1) + R(11, 10, 2, 4, 1) + R(11, 18, 2, 4, 1)), pl(polyR([[9.3, 3.6], [9.3, 20.4], [2, 20.4]], 0.8)), pa(polyR([[14.7, 3.6], [14.7, 20.4], [22, 20.4]], 0.8))];
I["dz-edit-miroir-h"] = () => MIROIR();
I["dz-edit-miroir-v"] = () => tourne(MIROIR(), -90);
I["dz-edit-incliner"] = () => [pl(polyR([[10, 2.5], [21.5, 2.5], [14, 21.5], [2.5, 21.5]], 1)), pa(R(2.5, 2.5, 19, 19, 1.4))];
I["dz-edit-transformer"] = () => { const c = 12, a = (x, y) => G.arrow(c, c, x, y, 2.4, 4.8, 3.4); // têtes étroites : aucun jour fermé au centre
  const h = [[2, 2], [17, 2], [2, 17], [17, 17]].map(([x, y]) => R(x, y, 5, 5, 0.8));
  return [pl(union(a(12, 5.9), a(12, 18.1), a(5.9, 12), a(18.1, 12))), pa(union(cadre(2, 2, 20, 20, 2.2), ...h))]; };
I["dz-edit-pivot"] = () => { const t = []; for (const a of [0, 90, 180, 270]) t.push(pill(...pt(12, 12, 7.4, a), ...pt(12, 12, 8.8, a), 2.4));
  return [pl(G.ring(12, 12, 4.8, 2.4) + t.join("")), pa(cadre(2, 2, 20, 20, 2.2))]; };
I["dz-edit-point-reference"] = () => { const p = []; for (const y of [4, 12, 20]) for (const x of [4, 12, 20]) if (x !== 12 || y !== 12) p.push(R(x - 2, y - 2, 4, 4, 0.8));
  return [pl(R(8.4, 8.4, 7.2, 7.2, 1)), pa(p.join(""))]; };
I["dz-edit-decaler-px"] = () => [pl(R(13.6, 7.8, 8.4, 8.4, 0.8)), pa(G.arrow(2, 12, 12, 12, 2.6, 7.4, 5))];
I["dz-edit-pointe-fleche"] = () => { const u = [Math.SQRT1_2, -Math.SQRT1_2], n = [Math.SQRT1_2, Math.SQRT1_2], tip = [21.4, 2.6], b = [tip[0] - 9 * u[0], tip[1] - 9 * u[1]];
  return [pl(polyR([tip, [b[0] + 5.6 * n[0], b[1] + 5.6 * n[1]], [b[0] - 5.6 * n[0], b[1] - 5.6 * n[1]]], 0.6)), pa(pill(3.6, 20.4, 12.6, 11.4, 2.8))]; };
I["dz-edit-relatif"] = () => { const t = polyR([[12, 2.6], [22, 21], [2, 21]], 1); return [pl(moins(t, M.eroder(t, 3)))]; };
I["dz-edit-conserver-proportions"] = () => [badge("cadenas"), pl(double(5.4, 17.6, 16.6, 6.4, 2.6, 6.6, 4.6)), pa(R(2, 3, 20, 18, 1.4))];
I["dz-edit-directions"] = () => [pa(G.circle(12, 12, 2.2)), pl(G.star(12, 12, 10.2, 3.4, 4, -90))];

// ═══════════════════════════ Chemins, nœuds, conversions ═══════════════════════════════════════════════
I["dz-edit-inverser-sens"] = () => [
  pl(union(R(3, 4.7, 16, 2.6, 1.3), polyR([[21.6, 7.3], [14.6, 7.3], [14.6, 1.8]], 0.4)) + union(R(5, 16.7, 16, 2.6, 1.3), polyR([[2.4, 16.7], [9.4, 16.7], [9.4, 22.2]], 0.4))),
  pa(trait(lisse([[2.6, 12.6], [7, 10.6], [12, 12], [17, 13.4], [21.4, 11.4]], 10), 2.2))];
I["dz-edit-epaissir"] = () => { const s = trait(lisse([[7.2, 16.8], [9.4, 10.6], [16.8, 7.2]], 10), 3.2);
  return [pl(s), pa(moins(M.dilater(s, 3.8), M.dilater(s, 1.6)))]; };
I["dz-edit-convertir-en-cadre"] = () => { const h = [[3.4, 3.4], [20.6, 3.4], [3.4, 20.6], [20.6, 20.6]].map(([x, y]) => R(x - 2.2, y - 2.2, 4.4, 4.4, 0.6));
  return [pl(R(7.1, 7.3, 9.8, 2.2, 1.1) + R(7.1, 10.9, 9.8, 2.2, 1.1) + R(7.1, 14.5, 6.4, 2.2, 1.1)), pa(union(cadre(3.4, 3.4, 17.2, 17.2, 2.2, 0.8), ...h))]; };
I["dz-edit-convertir-en-chemin"] = () => { // A gras dont on ne garde que le contour (2), nœuds carrés pâles à l'apex et aux pieds
  const A = moins(G.poly([[9, 2.6], [15, 2.6], [21.6, 21.2], [15.4, 21.2], [14.4, 17.8], [9.6, 17.8], [8.6, 21.2], [2.4, 21.2]]), G.poly([[12, 8.4], [13.7, 13.6], [10.3, 13.6]]));
  const contour = moins(A, M.eroder(A, 2));
  const n = [[12, 3.2], [3.4, 20.6], [20.6, 20.6]].map(([x, y]) => R(x - 2.2, y - 2.2, 4.4, 4.4, 0.6)).join("");
  return [pa(n), pl(contour)]; };
// escalier de pixels pâle ; la courbe lisse pleine l'enveloppe en passant au ras de ses angles saillants
I["dz-edit-vectoriser"] = () => [pl(arc(22, 22, 19.4, 2.6, 180, 270)),
  pa(G.poly([[3.4, 22], [3.4, 17.4], [8, 17.4], [8, 12.8], [12.6, 12.8], [12.6, 8.2], [17.2, 8.2], [17.2, 3.6], [22, 3.6], [22, 22]]))];
I["dz-edit-courbes-niveau"] = () => { const w = (R0, k) => a => R0 * (1 + k * Math.sin(3 * a + 0.6) + 0.05 * Math.cos(2 * a));
  return [pl(moins(blob(12, 12, w(10, 0.06)), blob(12, 12, w(7.8, 0.06))) + moins(blob(12.8, 12.6, w(6.2, 0.1)), blob(12.8, 12.6, w(4, 0.1))) + blob(13.4, 13, w(2.4, 0.1)))]; };

// ═══════════════════════════ Série « sélection-tracé » (5) ═════════════════════════════════════════════
const carreTirets = (x, y, w, h, e = 2.2) => { const d = cadre(x, y, w, h, e, 1);
  const cx1 = x + w / 3, cx2 = x + 2 * w / 3, cy = y + h / 2;
  return moins(d, R(cx1 - 0.9, y - 1, 1.8, e + 2), R(cx2 - 0.9, y - 1, 1.8, e + 2), R(cx1 - 0.9, y + h - e - 1, 1.8, e + 2), R(cx2 - 0.9, y + h - e - 1, 1.8, e + 2),
    R(x - 1, cy - 0.9, e + 2, 1.8), R(x + w - e - 1, cy - 0.9, e + 2, 1.8)); };
I["dz-edit-charger-selection"] = () => [pl(G.arrow(2, 12, 15.2, 12, 2.6, 7.6, 5)), pa(anneauTirets(14.6, 12, 6.6, 2.2, 8, 1.8, 22.5))];
I["dz-edit-enregistrer-selection"] = () => [pl(carreTirets(4, 2, 16, 11.6)), pa(M.plaque({ cx: 12, cy: 18.7, w: 20, h: 6.6 }))];
I["dz-edit-selection-vers-trace"] = () => [pl(trait(lisse([[7, 17], [8.4, 11.4], [15.6, 12.6], [17, 7]], 10), 2.6) + R(4.6, 14.8, 4.4, 4.4, 0.6) + R(15, 5, 4.4, 4.4, 0.6)),
  pa(carreTirets(2, 2, 20, 20))];
I["dz-edit-contour-trace"] = () => [pl(M.pinceau({ k: 0.56, dx: 5.4, dy: -5.4 })), pa(moins(ellipse(9.6, 14.4, 7.6, 6.4), ellipse(9.6, 14.4, 5.4, 4.2)))];
I["dz-edit-remplir-trace"] = () => { const f = blob(12, 12.4, a => 8.4 * (1 + 0.1 * Math.sin(2 * a + 0.4) + 0.05 * Math.cos(3 * a)));
  const pts = [-50, 70, 190].map(a => pt(12, 12.4, 8.4 * (1 + 0.1 * Math.sin(2 * a * Math.PI / 180 + 0.4) + 0.05 * Math.cos(3 * a * Math.PI / 180)), a));
  return [pa(pts.map(([x, y]) => R(x - 1.9, y - 1.9, 3.8, 3.8, 0.6)).join("")), pl(f)]; };

// ═══════════════════════════ Série « dégradés » (3) + motif ════════════════════════════════════════════
const BOITE = R(2, 2, 20, 20, 1.4);
I["dz-edit-degrade-lineaire"] = () => [pl(inter(BOITE, R(2, 2, 6, 20) + R(9.6, 2, 3.6, 20) + R(15.2, 2, 2.4, 20) + R(20, 2, 2, 20)))];
I["dz-edit-degrade-radial"] = () => { const pts = []; for (let i = 0; i < 12; i++) pts.push(G.circle(...pt(12, 12, 9.85, i * 30 + 15), 1.05));
  return [pl(G.circle(12, 12, 3.4) + G.ring(12, 12, 7.2, 5) + pts.join(""))]; };
I["dz-edit-degrade-conique"] = () => { const bornes = [-90, 30, 120, 190, 245, 270]; let d = G.circle(12, 12, 10);
  for (const a of bornes) d = moins(d, pill(12, 12, ...pt(12, 12, 11, a), 1.8));
  return [pl(moins(d, G.circle(12, 12, 2.4)))]; };
I["dz-edit-motif"] = () => { const L = (x, y, r) => G.poly([[x, y - r], [x + r, y], [x, y + r], [x - r, y]]);
  return [pl(L(12, 12, 2.6) + L(8.3, 8.3, 2.6) + L(15.7, 8.3, 2.6) + L(8.3, 15.7, 2.6) + L(15.7, 15.7, 2.6)), pa(cadre(2, 2, 20, 20, 2.2))]; };

// ═══════════════════════════ Série « tuiles » (2) ══════════════════════════════════════════════════════
I["dz-edit-autotuile"] = () => [pl(rectR(2, 2, 11, 11, [1.4, 0, 6, 0])), pa(BOITE)];
I["dz-edit-seamless"] = () => [pl(R(8.6, 8.6, 6.8, 6.8, 0.8)), pa(R(8.6, 2, 6.8, 5, 0.8) + R(8.6, 17, 6.8, 5, 0.8) + R(2, 8.6, 5, 6.8, 0.8) + R(17, 8.6, 5, 6.8, 0.8))];

// ═══════════════════════════ Montage, scène ════════════════════════════════════════════════════════════
// fer à cheval incliné de 45° (ouverture en haut à droite) : jamais confondu avec le U du soulignement
const AIM = { rot: 45, k: 0.94, cx: 12, cy: 12, dx: -0.6, dy: 0.8 };
I["dz-edit-aimanter"] = () => [pl(placer(union(arc(12, 13.4, 6.4, 4.4, 0, 180), R(3.4, 8.4, 4.4, 5.2), R(16.2, 8.4, 4.4, 5.2)), AIM)), pa(placer(R(3.4, 2, 4.4, 4.9, 0.8) + R(16.2, 2, 4.4, 4.9, 0.8), AIM))];
I["dz-edit-couper"] = () => [pl(union(R(9, 2, 6, 5.4, 1), polyR([[10.4, 6], [13.6, 6], [13.6, 18.6], [12, 22], [10.4, 18.6]], 0.6))), pa(R(2, 9, 20, 8.4, 1.4))];
I["dz-edit-ripple"] = () => [pl(G.arrow(2, 5.4, 21.8, 5.4, 2.6, 7, 5)), pa(R(2, 11, 5.6, 10, 1.2) + R(9.2, 11, 5.6, 10, 1.2) + R(16.4, 11, 5.6, 10, 1.2))];
I["dz-edit-energie"] = () => [pl(trait([[2.6, 12], [6.4, 12], [9, 4], [12.6, 17.4], [15.2, 8], [17.4, 12], [21.4, 12]], 2.4)), pa(R(2, 20, 20, 2, 1))];

// ═══════════════════════════ Texte, notes, effets ══════════════════════════════════════════════════════
I["dz-edit-annotation"] = () => { const corps = polyR([[2, 2], [22, 2], [22, 14.6], [14.6, 22], [2, 22]], 1.4), oreille = G.poly([[14.6, 22], [14.6, 14.6], [22, 14.6]]);
  return [pl(union(moins(corps, M.reserve(oreille, 1.6), R(5.4, 6, 13.2, 2.4, 1.2), R(5.4, 10.8, 8.6, 2.4, 1.2)), polyR([[14.6, 21.6], [14.6, 15.4], [21, 15.4]], 0.5)))]; };
I["dz-edit-paragraphes"] = () => [pl(union(G.circle(8.8, 8, 5.4), R(8.8, 2.6, 10, 2.6), R(11.2, 2.6, 2.6, 18.8, 0.6), R(16.2, 2.6, 2.6, 18.8, 0.6), R(8.8, 2.6, 4, 10.8)))];
I["dz-edit-effet"] = () => [pl(union(R(5.4, 6.4, 2.8, 15.2, 0.6), arc(10, 6.8, 3.2, 2.8, 180, 300), R(2.6, 10, 8, 2.6, 1.3)) + union(pill(13.4, 11.4, 20.6, 20.6, 2.8), pill(20.6, 11.4, 13.4, 20.6, 2.8)))];

// ═══════════════════════════ écriture ═════════════════════════════════════════════════════════════════
const filtre = process.argv[2] || "";
let n = 0;
for (const [cle, fn] of Object.entries(I)) {
  if (filtre && !cle.includes(filtre)) continue;
  fs.writeFileSync(path.join(OUT, cle + ".svg"), M.icone(fn()));
  n++;
}
console.log(n + " icônes écrites dans " + OUT);
