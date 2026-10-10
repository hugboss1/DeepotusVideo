// Mission « fondations » : familles nav, etat, marque (sauf reseau). Usage : node dessin/fondations.js [filtre]
// Chaque icône = une liste de calques DU HAUT VERS LE BAS passée à M.icone (règle du monochrome appliquée :
// chaque calque est évidé de la réserve 1,5 de ceux du dessus ; badge : 1,4).
"use strict";
const fs = require("fs"), path = require("path");
const G = require("../geo.js"), M = require("../motifs.js");
const OUT = path.join(__dirname, "..", "svg");
fs.mkdirSync(OUT, { recursive: true });
const PALE = .38;
const pl = (d, x = {}) => ({ d, op: 1, ...x }), pa = (d, x = {}) => ({ d, op: PALE, ...x });
const badge = type => ({ d: M.badge(type), op: 1, reserve: M.RES_BADGE });
const { union, moins, inter, placer, arc, rectR, polyR, pt, trait, lisse, pill, ellipse } = M;
const I = {};

// ═══════════════════════════════════════ nav : rail ═══════════════════════════════════════════════════
I["dz-nav-quick"] = () => [pl(M.eclair())];
I["dz-nav-studio"] = () => [pl(M.graphe({ partie: "noeuds" })), pa(M.graphe({ partie: "liens" }))];
I["dz-nav-chapitres"] = () => [pl(moins(M.livre({ partie: "droite" }), polyR([[15.2, 8.2], [19.6, 11.2], [15.2, 14.2]], 0.5))), pa(M.livre({ partie: "gauche" }))];
I["dz-nav-son-vfx"] = () => { const o = { hauteurs: [0.28, 0.6, 1, 0.68, 0.28] }; return [pl(M.onde({ ...o, partie: "centre" })), pa(M.onde({ ...o, partie: "bords" }))]; };
I["dz-nav-montage"] = () => [
  pl(union(G.rect(17.6, 5.4, 2.4, 16.6, 1.2), polyR([[15.6, 2], [22, 2], [22, 5.2], [18.8, 7.8], [15.6, 5.2]], 0.7))),
  pa(G.rect(2, 5.4, 9.6, 2.6, 1.3) + G.rect(2, 10.7, 13.6, 2.6, 1.3) + G.rect(2, 16, 7.6, 2.6, 1.3))];
I["dz-nav-scheduler"] = () => {
  const o = { x: 2.5, y: 1.6, w: 19, h: 20.4 }, c = [12, 15.6];
  const aig = union(pill(c[0], c[1] + 0.3, c[0], c[1] - 3.2, 2.2), pill(c[0] - 0.3, c[1], c[0] + 3.4, c[1] + 1.6, 2.2));
  return [pl(union(M.calendrier({ ...o, partie: "anneaux" }), M.calendrier({ ...o, partie: "bandeau" }))), pa(moins(M.calendrier({ ...o, partie: "corps" }), aig))];
};
I["dz-nav-templates"] = () => [pl(G.rect(2.4, 3, 8.6, 18, 1.4)), pa(G.rect(12.6, 3, 9, 8.2, 1.4) + G.rect(12.6, 12.8, 9, 8.2, 1.4))];
I["dz-nav-news"] = () => { const c = [4.4, 19.6];
  return [pl(G.circle(...c, 2.4) + arc(...c, 14, 2.6, -90, 0)), pa(arc(...c, 8.2, 2.6, -90, 0))]; };
I["dz-nav-bibliotheque"] = () => { const o = { y: 2.4, h: 10.4, pas: 4.2 }; return [pl(M.pile({ ...o, partie: "dessus" })), pa(M.pile({ ...o, partie: "dessous" }))]; };
I["dz-nav-game-assets"] = () => [pl(G.ngon(16.9, 16.9, 5.4, 6, -90)), pa(G.rect(2.4, 2.4, 8, 8, 1.4) + G.rect(13.2, 2.4, 8, 8, 1.4) + G.rect(2.4, 13.2, 8, 8, 1.4))];
I["dz-nav-reglages"] = () => [pl(G.circle(15.4, 7.6, 3.2) + G.circle(8.6, 16.4, 3.2)), pa(G.rect(2, 6.4, 20, 2.4, 1.2) + G.rect(2, 15.2, 20, 2.4, 1.2))];
I["dz-nav-photolab"] = () => { // diaphragme : six lames découpées par le prolongement des côtés de l'hexagone d'ouverture
  const c = 12, rh = 3.4, V = i => pt(c, c, rh, -90 + i * 60);
  let lames = G.circle(c, c, 6.9);
  for (let i = 0; i < 6; i++) { const a = V(i), b = V(i + 1), u = [b[0] - a[0], b[1] - a[1]], l = Math.hypot(...u);
    lames = moins(lames, pill(a[0], a[1], b[0] + u[0] / l * 9, b[1] + u[1] / l * 9, 1.6)); }
  lames = moins(lames, G.ngon(c, c, rh + 0.4, 6, -90));
  return [pl(lames), pa(G.ring(c, c, 10.2, 8))];
};
I["dz-nav-vectorlab"] = () => { const A = [4.6, 4.6], B = [19.4, 4.6], C = [12, 19.4];
  return [pa(G.rect(A[0] - 2.4, A[1] - 2.4, 4.8, 4.8, 0.8) + G.rect(B[0] - 2.4, B[1] - 2.4, 4.8, 4.8, 0.8) + G.rect(C[0] - 2.4, C[1] - 2.4, 4.8, 4.8, 0.8)),
    pl(union(pill(...A, ...C, 3.2), pill(...B, C[0] + 0.01, C[1] + 0.2, 3.2)))]; };

// ═══════════════════════════════════════ nav : labs ═══════════════════════════════════════════════════
I["dz-nav-atelier"] = () => { // plume d'oie plantée dans un encrier
  const plume = placer(union(moins(`M12 1.4C15.2 4.4 15.6 10.2 12.8 15.4H11.2C8.4 10.2 8.8 4.4 12 1.4Z`, pill(12, 5.4, 12, 13.6, 1.6)), G.poly([[11.2, 15], [12.8, 15], [12, 19.8]])), { rot: 32, cx: 12, cy: 15 });
  return [pl(placer(plume, { dx: 2.6, dy: -0.4 })), pa(union(G.rect(2.4, 13.4, 14.4, 8.6, 2.2), G.rect(5.6, 10.6, 8, 3.4, 0.8)))];
};
I["dz-nav-bible"] = () => [pa(G.rect(17.4, 8.4, 4.4, 3.4, 1)), pl(M.livreFerme({ x: 3, w: 16.6 }))];
I["dz-nav-etabli"] = () => { // imprimante 3D : portique pâle, chariot + buse et objet imprimé pleins
  const portique = union(G.rect(2.4, 2.4, 19.2, 2.6, 1), G.rect(2.4, 2.4, 2.6, 19.6, 1), G.rect(19, 2.4, 2.6, 19.6, 1), G.rect(2, 19.6, 20, 2.4, 1));
  const tete = union(G.rect(8.4, 6.4, 7.2, 3.2, 0.8), G.poly([[10.6, 9.4], [13.4, 9.4], [12, 11.4]]));
  const objet = M.cube({ cx: 12, cy: 15.6, r: 3.9, arete: 1.2 });
  return [pl(tete), pl(objet), pa(portique)];
};
I["dz-nav-plateau"] = () => [pl(M.camera({ x: 2, y: 2, s: 0.92 })), pa(union(pill(8, 17.6, 3.6, 22, 2.2), pill(8, 17.6, 12.4, 22, 2.2), G.rect(6.9, 16.6, 2.2, 5.4, 1.1)))];
I["dz-nav-episodes"] = () => [pl(moins(G.rect(2, 8.4, 20, 13.6, 2.6), G.rect(4.4, 10.8, 11.4, 8.8, 0.8), G.circle(18.9, 13.2, 1), G.circle(18.9, 17.4, 1))),
  pa(union(pill(11.6, 6.8, 6.6, 2, 2.2), pill(12.4, 6.8, 17.4, 2, 2.2)))];
I["dz-nav-direction-artistique"] = () => { // palette ovale, trou de pouce, trois godets évidés
  let p = placer(ellipse(12, 12, 10.2, 8.8), { rot: -12, cx: 12, cy: 12 });
  p = moins(p, G.circle(18.8, 18.6, 3.6), G.circle(7.6, 15.4, 2), G.circle(6.8, 9.2, 1.7), G.circle(11.6, 6.6, 1.7), G.circle(16.6, 8.2, 1.7));
  return [pl(p)];
};
I["dz-nav-documents"] = () => { const f = { x: 7.4, y: 4.4, w: 12.4, h: 17.6, coin: 4.4 };
  return [pl(M.feuille(f)), pa(placer(M.feuille(f), { rot: -22, cx: 7.4, cy: 22 }))]; };
I["dz-nav-versions"] = () => { const F = (x, y) => M.feuille({ x, y, w: 13.6, h: 15.6, coin: 4 });
  const front = moins(F(2.4, 6.4), G.circle(9.2, 15, 4.4)), aig = union(pill(9.2, 15.3, 9.2, 12.4, 1.9), pill(8.9, 15, 11.6, 15, 1.9));
  return [pl(union(front, aig)), pa(F(8, 2))]; };
// ═══════════════════════════════════════ nav : Card Forge (série cf-etapes) ═══════════════════════════
const carte = (x = 4.5, y = 2, w = 15, h = 20) => G.rect(x, y, w, h, 1.6);
I["dz-nav-cf-galerie"] = () => [pl(M.grille({ x: 3.4, y: 2, w: 17.2, h: 20, g: 2.2, r: 1.2 }))];
I["dz-nav-cf-face"] = () => [pl(G.rect(8, 5.6, 8, 7.6, 0.8)), pa(carte())];
I["dz-nav-cf-cadre"] = () => [pl(carte(4.5, 2, 15, 20) + G.rect(7.1, 4.6, 9.8, 14.8, 0.6)), pa(G.rect(8.7, 6.2, 6.6, 11.6, 0.6) + G.rect(10.7, 8.2, 2.6, 7.6, 0.2))];
I["dz-nav-cf-typo"] = () => [pl(M.lettreA({ k: 0.82, dy: -1.6 })), pa(G.rect(2.6, 19.6, 18.8, 2.4, 1.2))];
I["dz-nav-cf-donnees"] = () => { let corps = rectR(2.4, 9.4, 19.2, 12.6, [0, 0, 1.4, 1.4]);
  for (const [x, y] of [[5, 12], [12.8, 12], [5, 16.8], [12.8, 16.8]]) corps = moins(corps, G.rect(x, y, 6.2, 2.6, 0.6));
  return [pl(rectR(2.4, 2.6, 19.2, 5.2, [1.4, 1.4, 0, 0])), pa(corps)]; };
I["dz-nav-cf-volume"] = () => { // carte posée en perspective, tranche épaisse pleine
  const A = [2, 10.4], B = [10.4, 4.6], C = [22, 10.4], D = [13.6, 16.2], e = 4;
  const tranche = union(G.poly([A, D, [D[0], D[1] + e], [A[0], A[1] + e]]), G.poly([D, C, [C[0], C[1] + e], [D[0], D[1] + e]]));
  return [pl(tranche, { reserve: 1.6 }), pa(G.poly([A, B, C, D]))]; };
I["dz-nav-cf-matieres"] = () => { const s = { cx: 16, cy: 16, r: 5.8 };
  return [pl(M.sphere({ ...s, partie: "moitie" })), pa(M.sphere({ ...s, partie: "gauche" })), pa(carte(2.4, 2, 13.6, 18.6))]; };
I["dz-nav-cf-impression"] = () => { let f = G.rect(6.6, 12.4, 10.8, 9.6, 1); f = moins(f, G.rect(8.8, 15, 6.4, 1.8, 0.9), G.rect(8.8, 18.4, 4.4, 1.8, 0.9));
  return [pl(f), pa(G.rect(2.2, 6.8, 19.6, 9.2, 1.8) + G.rect(6.6, 2, 10.8, 3.2, 0.8))]; };
I["dz-nav-cf-export-3d"] = () => [pl(M.fleche({ x1: 11.6, y1: 12.4, x2: 21.8, y2: 2.2, w: 2.8, hw: 8.4, hl: 5.8 })), pa(M.cube({ cx: 9.6, cy: 13.8, r: 8 }))];
I["dz-nav-cf-forge-3d"] = () => [pl(M.cube({ cx: 15.4, cy: 12, r: 6.8 })),
  pa(G.rect(2, 2.6, 5.4, 5.4, 1) + G.rect(2, 16, 5.4, 5.4, 1) + G.rect(6, 4.2, 4.2, 2.2) + G.rect(6, 17.6, 4.2, 2.2) + union(G.rect(8, 4.2, 2.2, 15.6), G.rect(8, 10.9, 3.6, 2.2)))];
I["dz-nav-cf-import"] = () => [pl(M.fleche({ x1: 1.8, y1: 12, x2: 15.4, y2: 12 })), pa(carte(8, 2, 13.8, 20))];
I["dz-nav-cf-edition"] = () => [pl(G.rect(2, 3, 18, 6.8, 1.4)), pa(G.rect(4, 11.4, 18, 10.6, 1.4))];

// ═══════════════════════════════════════ nav : panneaux du Photolab (série panneaux) ══════════════════
I["dz-nav-panneau-calques"] = () => { const o = { y: 3, h: 8.8, w: 20, pas: 4.6, forme: "parallelogramme" };
  return [pl(M.pile({ ...o, partie: "dessus" })), pa(M.pile({ ...o, partie: "dessous" }))]; };
I["dz-nav-panneau-couleur"] = () => [pl(G.circle(8.6, 8.6, 6.6)), pa(G.circle(15.4, 15.4, 6.6))]; // couleurs avant-plan / arrière-plan
I["dz-nav-panneau-historique"] = () => [pl(M.flecheCourbe({ cx: 12, cy: 9.6, r: 6.2, a0: 20, a1: -200, hw: 7, hl: 4.8, e: 2.6 })),
  pa(G.rect(2, 15, 20, 2.4, 1.2) + G.rect(2, 19.6, 13, 2.4, 1.2))];
I["dz-nav-panneau-infos"] = () => [pl(union(G.ring(12, 12, 4.8, 2.8), pill(12, 3.6, 12, 6.6, 2.2), pill(12, 17.4, 12, 20.4, 2.2), pill(3.6, 12, 6.6, 12, 2.2), pill(17.4, 12, 20.4, 12, 2.2))),
  pa(G.rect(2, 2, 20, 20, 2) + G.rect(4.2, 4.2, 15.6, 15.6, 0.8))];
I["dz-nav-panneau-navigateur"] = () => { const nord = G.poly([[18.2, 5.8], [10.4, 10.4], [13.6, 13.6]]), sud = G.poly([[5.8, 18.2], [13.6, 13.6], [10.4, 10.4]]);
  return [pl(nord), pa(sud, { colle: true }), pa(G.ring(12, 12, 10.2, 7.8))]; };
I["dz-nav-panneau-pinceaux"] = () => [pl(G.circle(17.2, 6.6, 4.4) + G.circle(10.2, 12.6, 3.3) + G.circle(4.6, 17.8, 2.4))];
I["dz-nav-panneau-texte"] = () => [pl(M.lettreA({ k: 0.66, dx: -4.4, dy: 0.6 })), pa(G.rect(15.6, 9.6, 6.4, 2.4, 1.2) + G.rect(15.6, 14.6, 6.4, 2.4, 1.2) + G.rect(15.6, 19.6, 6.4, 2.4, 1.2))];
I["dz-nav-panneau-ajustements"] = () => { // trois curseurs verticaux (≠ nav-reglages, horizontaux, boutons ronds)
  const xs = [4.6, 12, 19.4], ys = [14.6, 6.4, 11.6];
  return [pl(xs.map((x, i) => G.rect(x - 2.8, ys[i] - 1.8, 5.6, 3.6, 1)).join("")), pa(xs.map(x => G.rect(x - 1.2, 2, 2.4, 20, 1.2)).join(""))]; };
// ═══════════════════════════════════════ nav : espaces de travail ═════════════════════════════════════
const coins = () => { const L = (x, y, sx, sy) => union(G.rect(Math.min(x, x + sx * 6), y - (sy < 0 ? 2.2 : 0), 6, 2.2, 0.6), G.rect(x - (sx < 0 ? 2.2 : 0), Math.min(y, y + sy * 6), 2.2, 6, 0.6));
  return L(2, 2, 1, 1) + L(22, 2, -1, 1) + L(2, 22, 1, -1) + L(22, 22, -1, -1); };
I["dz-nav-espace-pixel"] = () => { const c = 3.6, px = [[6.6, 13.8], [10.2, 13.8], [10.2, 10.2], [13.8, 10.2], [13.8, 6.6]];
  return [pl(union(...px.map(([x, y]) => G.rect(x - 0.05, y - 0.05, c + 0.1, c + 0.1)), G.rect(6.6, 13.8, 10.8, c))), pa(coins())]; };
I["dz-nav-espace-vecteur"] = () => { const g = lisse([[8.2, 15.8], [9.4, 12.6], [12, 12], [14.6, 11.4], [15.8, 8.2]], 10);
  return [pl(G.rect(5.6, 14.4, 4.2, 4.2, 0.6) + G.rect(14.2, 5.4, 4.2, 4.2, 0.6), { colle: true }), pl(trait(g, 2.4)), pa(coins())]; };
I["dz-nav-espace-travail"] = () => { // fenêtre à trois volets : barre d'outils, toile, panneau
  const outils = moins(rectR(2, 7.4, 4.4, 14, [0, 0, 0, 1.4]), G.rect(3.3, 9.4, 1.8, 1.8), G.rect(3.3, 13, 1.8, 1.8));
  const panneau = moins(rectR(16.2, 7.4, 5.8, 14, [0, 0, 1.4, 0]), G.rect(17.6, 10, 3, 1.6), G.rect(17.6, 13.4, 3, 1.6));
  return [pl(rectR(2, 2.6, 20, 3.2, [1.4, 1.4, 0, 0]) + outils + panneau), pa(G.rect(7.6, 7.4, 7.4, 14, 0.6))]; };
// ═══════════════════════════════════════ nav : divers ═════════════════════════════════════════════════
I["dz-nav-accueil"] = () => [pl(M.maison())];
I["dz-nav-analytics"] = () => [pl(trait([[2.4, 13.4], [8, 8.6], [12.6, 11.2], [21.2, 3.2]], 2.6)),
  pa(G.rect(2.4, 17.2, 4.4, 4.8, 1) + G.rect(9.8, 14.4, 4.4, 7.6, 1) + G.rect(17.2, 10.6, 4.4, 11.4, 1))];
I["dz-nav-boite-reception"] = () => { // bac de réception « inbox » : plateau à ressaut central, sans flèche
  const plateau = polyR([[2, 13.4], [7.6, 13.4], [9.2, 16.2], [14.8, 16.2], [16.4, 13.4], [22, 13.4], [22, 21], [2, 21]], 1);
  const cadre = moins(G.rect(2, 3, 20, 18, 1.6), G.rect(4.4, 5.4, 15.2, 20, 0.6));
  return [pl(plateau, { colle: true }), pa(cadre)]; };
I["dz-nav-campagne"] = () => [pl(union(polyR([[2.4, 8.4], [6.2, 8.4], [17.6, 3], [17.6, 18.2], [6.2, 12.8], [2.4, 12.8]], 1), G.rect(18.6, 2, 3, 17.2, 1.5))),
  pa(pill(8.4, 15, 9.8, 20.6, 2.6))];
I["dz-nav-cles-api"] = () => [pl(M.cle())];
I["dz-nav-corbeille"] = () => { // panier à papier ouvert, treillis évidé, sans couvercle
  let p = union(polyR([[3.4, 5.6], [20.6, 5.6], [18.4, 22], [5.6, 22]], 1.4), G.rect(2, 3, 20, 3.2, 1.4));
  for (const [x, y] of [[8.4, 8.6], [13.4, 8.6], [8.8, 14.6], [13, 14.6]]) p = moins(p, G.rect(x, y, 2.2, 4.2, 0.6));
  return [pl(p)]; };
I["dz-nav-file-rendus"] = () => [pl(G.rect(2, 2.6, 12.4, 5.6, 2.8)), pa(G.rect(15.9, 2.6, 6.1, 5.6, 2.8) + G.rect(2, 11.6, 20, 3.4, 1.7) + G.rect(2, 18.2, 14, 3.4, 1.7))];
I["dz-nav-guide"] = () => [pl(polyR([[3.4, 5.4], [17.4, 5.4], [21, 8.2], [17.4, 11], [3.4, 11]], 0.8) + polyR([[20.6, 13], [6.6, 13], [3, 15.8], [6.6, 18.6], [20.6, 18.6]], 0.8)),
  pa(G.rect(10.8, 1.6, 2.4, 20.6, 1.2) + G.rect(7.6, 20.6, 8.8, 1.8, 0.9))];
I["dz-nav-projets"] = () => [pl(M.classeur({ partie: "onglets" })), pa(M.classeur({ partie: "corps" }))];
I["dz-nav-prompts"] = () => { const fiche = G.rect(4.6, 7.6, 11, 14.4, 1.2), P = { cx: 10, cy: 22 };
  return [pl(M.bulle({ x: 11.4, y: 2, w: 10.6, h: 7.6, queue: "gauche" })), pa(fiche), pa(placer(fiche, { rot: -14, ...P })), pa(placer(fiche, { rot: 14, ...P }))]; };
I["dz-nav-transfert"] = () => [pl(M.fleche({ x1: 3, y1: 4.6, x2: 21.2, y2: 4.6, w: 2.6, hw: 7.6, hl: 5 })),
  pa(M.ecran({ x: 2, y: 10.4, w: 9, h: 7, plein: true }) + M.ecran({ x: 13, y: 10.4, w: 9, h: 7, plein: true }))];

// ═══════════════════════════════════════ etat ═════════════════════════════════════════════════════════
I["dz-etat-succes"] = () => [pl(moins(G.circle(12, 12, 10), M.coche({ x: 5.8, y: 6.4, s: 12.8, w: 2.6 })))];
I["dz-etat-avertissement"] = () => [pl(moins(polyR([[12, 1.8], [22.4, 20.8], [1.6, 20.8]], 1.8), G.rect(10.8, 8.2, 2.4, 6.8, 1.2), G.circle(12, 17.6, 1.4)))];
I["dz-etat-erreur"] = () => [pl(moins(polyR(Array.from({ length: 8 }, (_, i) => pt(12, 12, 10.6, -112.5 + i * 45)), 1.2), G.cross(12, 12, 10.4, 2.4)))];
I["dz-etat-information"] = () => [pl(moins(G.rect(2, 2, 20, 20, 5), G.circle(12, 7.2, 1.6), G.rect(10.8, 10.2, 2.4, 7.8, 1.2)))];
I["dz-etat-attente"] = () => [pl(M.sablier({ partie: "verre" })), pa(M.sablier({ partie: "cadre" }))];
I["dz-etat-acquitte"] = () => { let anneau = G.ring(12, 12, 10.2, 8);
  for (let i = 0; i < 8; i++) anneau = moins(anneau, pill(...pt(12, 12, 6, i * 45 + 22.5), ...pt(12, 12, 12, i * 45 + 22.5), 1.8));
  return [pl(M.coche({ x: 6.4, y: 6.6, s: 11.4, w: 2.6 })), pa(anneau)]; };
I["dz-etat-actif"] = () => [pl(union(arc(12, 13, 8, 2.6, -55, 235))), pl(G.rect(10.7, 1.8, 2.6, 10.4, 1.3))];
I["dz-etat-contourne"] = () => { // le signal passe AU-DESSUS du bloc d'effet sans le traverser (effet contourné)
  const g = lisse([[2.4, 16.4], [5.6, 16.2], [7.6, 9], [12, 6.6], [16.4, 9], [17.8, 13.4]], 10);
  return [pl(union(trait(g, 2.6), G.poly([[14.4, 13], [21.2, 12.2], [18.6, 18.8]]))), pa(G.rect(8.2, 13, 6.6, 9, 1.2))]; };
I["dz-etat-derive"] = () => [pl(M.flecheCoudee({ x: 4.2, y: 9.6, w: 17.6, h: 9.4 })), pa(G.circle(5.5, 5.2, 3.2))];
I["dz-etat-enregistre"] = () => [badge("coche"), pl(M.disquette({ x: 2.5, y: 2.5, s: 18 }))];
I["dz-etat-modifie"] = () => [pl(union(pill(12, 2.6, 12, 21.4, 3.4), pill(...pt(12, 12, 9.4, -30), ...pt(12, 12, 9.4, 150), 3.4), pill(...pt(12, 12, 9.4, 30), ...pt(12, 12, 9.4, 210), 3.4)))];
I["dz-etat-epingle"] = () => [pl(M.punaise())];
I["dz-etat-exclu"] = () => [pl(pill(3, 3, 21, 21, 2.8)), pa(G.rect(2.6, 2.6, 18.8, 18.8, 1.6) + G.rect(4.8, 4.8, 14.4, 14.4, 0.6))];
I["dz-etat-sans-apercu"] = () => { let cadre = polyR([[2, 4], [16.4, 4], [22, 9.6], [22, 20], [2, 20]], 1.2); cadre = moins(cadre, polyR([[4.2, 6.2], [15.4, 6.2], [19.8, 10.6], [19.8, 17.8], [4.2, 17.8]], 0.6));
  return [pl(pill(3.4, 18.6, 18.6, 5.4, 2.6)), pl(G.poly([[16.4, 4], [16.4, 9.6], [22, 9.6]])), pa(cadre)]; };
I["dz-etat-grave"] = () => [pl(moins(G.rect(3, 3, 18, 18, 2.4), pill(8.4, 15.6, 15.6, 8.4, 2.4)))];
I["dz-etat-ia"] = () => { const R = 4, k = 0.6, c = [12, 12];
  const st = `M${c[0]} ${c[1] - R}Q${c[0] + k} ${c[1] - k} ${c[0] + R} ${c[1]}Q${c[0] + k} ${c[1] + k} ${c[0]} ${c[1] + R}Q${c[0] - k} ${c[1] + k} ${c[0] - R} ${c[1]}Q${c[0] - k} ${c[1] - k} ${c[0]} ${c[1] - R}Z`;
  return [pl(moins(G.rect(1.6, 5.8, 20.8, 12.4, 6.2), st, G.circle(17.4, 9.4, 1.3)))]; };
I["dz-etat-inconnu"] = () => { let r = G.rect(3, 3, 18, 18, 1.6) + G.rect(5.4, 5.4, 13.2, 13.2, 0.4);
  r = moins(r, G.rect(8.4, 1, 1.8, 6), G.rect(13.8, 1, 1.8, 6), G.rect(8.4, 17, 1.8, 6), G.rect(13.8, 17, 1.8, 6), G.rect(1, 8.4, 6, 1.8), G.rect(1, 13.8, 6, 1.8), G.rect(17, 8.4, 6, 1.8), G.rect(17, 13.8, 6, 1.8));
  return [pl(r)]; };
I["dz-etat-vide"] = () => [pl(G.rect(2, 4, 20, 16, 2.4) + G.rect(5.4, 7.4, 13.2, 9.2, 0.8))];
I["dz-etat-libre"] = () => [pl(M.cadenas({ ouvert: true, partie: "corps" })), pa(M.cadenas({ ouvert: true, partie: "anse" }))];
I["dz-etat-verrouille"] = () => [pl(M.cadenas({ partie: "corps" })), pa(M.cadenas({ partie: "anse" }))];
I["dz-etat-verrou-pixels"] = () => [badge("cadenas"), pl(M.pinceau({ k: 0.92, dx: -1.2, dy: -1.2 }))];
I["dz-etat-verrou-position"] = () => { const c = 10.4, a = 8.4, hw = 6, hl = 4.4;
  const croix = union(M.fleche({ x1: c, y1: c, x2: c, y2: c - a, hw, hl }), M.fleche({ x1: c, y1: c, x2: c, y2: c + a, hw, hl }), M.fleche({ x1: c, y1: c, x2: c - a, y2: c, hw, hl }), M.fleche({ x1: c, y1: c, x2: c + a, y2: c, hw, hl }));
  return [badge("cadenas"), pl(croix)]; };
I["dz-etat-verrou-transparence"] = () => [badge("cadenas"), pl(M.damier({ x: 2, y: 2, s: 18, n: 3 }))];
I["dz-etat-verrou-plan-travail"] = () => { const L = (x, y, sx, sy) => union(G.rect(sx > 0 ? x : x - 9, y - (sy < 0 ? 2.6 : 0), 9, 2.6, 0.6), G.rect(x - (sx < 0 ? 2.6 : 0), sy > 0 ? y : y - 9, 2.6, 9, 0.6));
  return [badge("cadenas"), pl(L(2, 2, 1, 1) + L(22, 2, -1, 1) + L(2, 22, 1, -1)), pa(G.rect(7, 7, 10, 10, 1))]; };
I["dz-etat-meilleur"] = () => { const coupe = union(`M6.2 2.6H17.8V8.4A5.8 5.8 0 0 1 6.2 8.4Z`, arc(6.2, 6.6, 2.4, 2.2, 90, 270), arc(17.8, 6.6, 2.4, 2.2, -90, 90), G.rect(10.8, 13.6, 2.4, 4.4));
  return [pl(coupe), pa(G.rect(5.8, 18.6, 12.4, 3.4, 1))]; };
I["dz-etat-mobile"] = () => [pl(M.telephone())];
I["dz-etat-note"] = () => { const s = cx => M.etoile({ cx, cy: 12.4, r: 4.1, ri: 0.48 });
  return [pl(s(4.1) + s(12)), pa(s(19.9))]; };
I["dz-etat-option-active"] = () => [pl(moins(G.rect(4, 4, 16, 16, 2.4), M.coche({ x: 6.6, y: 7, s: 10.6, w: 2.4 })))];
I["dz-etat-origine"] = () => { const a = union(G.ring(12, 4.4, 2.8, 1), G.rect(10.8, 7, 2.4, 13.4, 0.6), G.rect(7, 9, 10, 2.4, 1.2), arc(12, 12.4, 8.2, 2.4, 25, 155),
  G.poly([[2.2, 12.8], [7, 13.6], [3.6, 17.2]]), G.poly([[21.8, 12.8], [17, 13.6], [20.4, 17.2]]));
  return [pl(a)]; };
I["dz-etat-plafond"] = () => { // jauge en demi-cercle, aiguille couchée au maximum contre la butée (≠ action-mesurer : aiguille libre)
  const c = [12, 17.4];
  return [pl(union(G.circle(...c, 2.6), pill(...c, 21, c[1], 2.6)) + arc(...c, 8.8, 2.6, -40, -4)), pa(arc(...c, 8.8, 2.6, -176, -52))]; };
I["dz-etat-publie"] = () => [badge("coche"), pl(M.avion({ k: 0.94, dx: -1.6, dy: -1 }))];
I["dz-etat-rappel"] = () => [pl(M.cloche())];
I["dz-etat-selection-multiple"] = () => { const pointille = (x, y, w, h) => { let r = G.rect(x, y, w, h, 1) + G.rect(x + 2, y + 2, w - 4, h - 4, 0.2);
  for (const t of [0.5]) { r = moins(r, G.rect(x + w * t - 0.9, y - 1, 1.8, h + 2), G.rect(x - 1, y + h * t - 0.9, w + 2, 1.8)); } return r; };
  return [pl(pointille(2, 8.6, 13.4, 13.4)), pa(pointille(8.6, 2, 13.4, 13.4))]; };
I["dz-etat-visible"] = () => [pl(M.oeil())];
I["dz-etat-cache"] = () => [pl(M.oeil({ barre: true }))];

// ═══════════════════════════════════════ marque ═══════════════════════════════════════════════════════
I["dz-marque-poulpe"] = () => [pl(M.poulpe())];
I["dz-marque-icone-app"] = () => [pl(moins(G.rect(1.6, 1.6, 20.8, 20.8, 5.4), M.poulpe({ k: 0.8, dy: 0.4 })))];
I["dz-marque-icone-adaptative"] = () => [pl(M.poulpe({ k: 0.62, yeux: true })), pa(moins(G.rect(1.4, 1.4, 21.2, 21.2), G.circle(12, 12, 8.6)))];
I["dz-marque-icone-monochrome"] = () => [pl(M.poulpe({ k: 0.62, yeux: false }))];
I["dz-marque-notification"] = () => { // tête ronde + trois tentacules épais, silhouette pleine (alpha seul)
  const tete = moins(union(G.circle(12, 8.4, 6.6), G.rect(7.4, 9, 9.2, 5.6, 2.4)), placer(ellipse(9.4, 10.6, 1.9, 1.15), { rot: 24, cx: 9.4, cy: 10.6 }), placer(ellipse(14.6, 10.6, 1.9, 1.15), { rot: -24, cx: 14.6, cy: 10.6 }));
  const t = c => trait(lisse(c, 12), u => 3.4 - 0.8 * u);
  return [pl(union(tete, t([[8.6, 13.2], [6.6, 17], [3.4, 19.4], [2.4, 17.2]]), t([[12, 14], [12, 18], [12, 21.6]]), t([[15.4, 13.2], [17.4, 17], [20.6, 19.4], [21.6, 17.2]])))]; };
I["dz-marque-splash"] = () => [pl(M.poulpe({ k: 0.64 })), pa(G.ring(12, 12, 10.6, 8.4))];
I["dz-marque-oracle"] = () => { const rays = []; for (let i = 0; i < 10; i++) { const a = -90 + i * 36; rays.push(pill(...pt(12, 12, 8.2, a), ...pt(12, 12, 10.4, a), 2.2)); }
  const R0 = (7.4 ** 2 + 4.4 ** 2) / 8.8, oeil = moins(`M4.6 12A${R0} ${R0} 0 0 1 19.4 12A${R0} ${R0} 0 0 1 4.6 12Z`, G.circle(12, 12, 2.4));
  return [pl(oeil), pa(union(...rays))]; };
I["dz-marque-seer"] = () => [pl(moins(G.circle(12, 9.6, 7.8), arc(12, 9.6, 4.6, 1.8, 200, 250))), pa(polyR([[4.4, 22], [19.6, 22], [17, 16.4], [7, 16.4]], 1))];

// ═══════════════════════════════════════ écriture ═════════════════════════════════════════════════════
const filtre = process.argv[2] || "";
let n = 0;
for (const [cle, fn] of Object.entries(I)) {
  if (filtre && !cle.includes(filtre)) continue;
  fs.writeFileSync(path.join(OUT, cle + ".svg"), M.icone(fn()));
  n++;
}
console.log(n + " icônes écrites dans " + OUT);
