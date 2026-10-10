// Mission « action » : les 98 clés de la famille action (verbes communs). Usage : node dessin/action.js [filtre]
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

// ═══════════════════════════════════════ gabarits partagés de la famille ══════════════════════════════
/** Flèche en arc (sens horaire si a1 > a0), tête au bout a1 — gabarit commun des « re- » (épaisseur 2,6). */
const boucle = (cx, cy, r, a0, a1, hw = 7, hl = 5) => M.flecheCourbe({ cx, cy, r, a0, a1, hw, hl });
/** Série zoom/chercher : la MÊME loupe (M.loupe par défaut) ; le signe est posé DANS la lentille (partie « lentille »
 *  du motif) au lieu d'un badge : avec un badge, les trois loupes ne différaient que par le symbole évidé du badge
 *  (IoU monochrome 0,96 > 0,92 refusé). Signe plein, réserve 1,5 calculée par M.icone. */
const LOUPE = { cx: 9.2, cy: 9.2, r: 7.8, e: 2.2 }; // manche jusqu'à 21,4 (+ bout rond) : reste dans 1–23
const loupeSigne = signe => [pl(signe), pl(M.loupe(LOUPE))];
/** Recherche sémantique : la loupe retournée (manche à gauche) laisse le quart bas-droit au badge étincelle. */
const loupeBadge = () => placer(M.loupe({ cx: 10, cy: 9.6, r: 7, e: 2.2 }), { miroir: true, cx: 12 });
const etinc = (x, y, R) => { const k = R * 0.16; return `M${x} ${y - R}Q${x + k} ${y - k} ${x + R} ${y}Q${x + k} ${y + k} ${x} ${y + R}Q${x - k} ${y + k} ${x - R} ${y}Q${x - k} ${y - k} ${x} ${y - R}Z`; };
/** Téléphone et écran de PC de la série telephone-pc. */
const tel = (cx, cy, w = 7.6, h = 13) => G.rect(cx - w / 2, cy - h / 2, w, h, 1.6) + G.rect(cx - w / 2 + 2, cy - h / 2 + 2.4, w - 4, h - 4.8, 0.4);
const pc = (x, y, w, h) => union(G.rect(x, y, w, h, 1.4)) + G.rect(x + 2, y + 2, w - 4, h - 4, 0.4);
const piedPc = (x, y, w, h) => G.rect(x + w / 2 - 3.6, y + h + 1.6, 7.2, 2.2, 1.1);
/** Fiche recette : fiche portrait à onglet LATÉRAL (intercalaire), jamais d'onglet en haut (≠ dossier). */
const ficheRecette = () => union(G.rect(2.4, 2, 14.6, 20, 1.4), rectR(16.4, 3.6, 4.4, 6.4, [0, 1.2, 1.2, 0]));
const ficheLignes = () => G.rect(5.6, 6.4, 8.2, 2.4, 1.2) + G.rect(5.6, 11.2, 8.2, 2.4, 1.2) + G.rect(5.6, 16, 5, 2.4, 1.2);
/** Viseur : quatre équerres d'angle (épaisseur e, bras l) dans le carré (x, y, s). */
const equerres = (x, y, s, l = 6, e = 2.6, r = 0.8) => {
  const L = (cx, cy, sx, sy) => union(G.rect(sx > 0 ? cx : cx - l, sy > 0 ? cy : cy - e, l, e, r), G.rect(sx > 0 ? cx : cx - e, sy > 0 ? cy : cy - l, e, l, r));
  return L(x, y, 1, 1) + L(x + s, y, -1, 1) + L(x, y + s, 1, -1) + L(x + s, y + s, -1, -1);
};

// ═══════════════════════════════════════ fermer / supprimer / retirer / abandonner / vider ═════════════
I["dz-action-fermer"] = () => [pl(union(pill(5, 5, 19, 19, 3.4), pill(19, 5, 5, 19, 3.4)))];
I["dz-action-supprimer"] = () => {
  let cuve = polyR([[4.4, 8.6], [19.6, 8.6], [18, 22], [6, 22]], 1.4);
  cuve = moins(cuve, G.rect(9.2, 11.4, 1.8, 7.6, 0.9), G.rect(13, 11.4, 1.8, 7.6, 0.9));
  const couvercle = union(G.rect(2.4, 4.4, 19.2, 2.6, 1.3), rectR(8.6, 1.6, 6.8, 3.4, [1.2, 1.2, 0, 0]));
  return [pl(cuve), pa(moins(couvercle, G.rect(10.6, 3.4, 2.8, 1.2)))];
};
I["dz-action-retirer"] = () => [badge("moins"), pl(G.rect(2, 3.4, 20, 6.4, 3.2)), pa(G.rect(2, 12.6, 10.4, 6.4, 3.2))];
I["dz-action-abandonner"] = () => [pl(union(G.ring(12, 12, 10, 7.4), inter(pill(5, 19, 19, 5, 2.8), G.circle(12, 12, 8))))];
I["dz-action-vider"] = () => { // seau plein renversé (ouverture en bas à gauche), éclats pâles qui en tombent
  const seau = union(polyR([[7, 8.4], [17, 8.4], [15.6, 19], [8.4, 19]], 1), G.rect(5.4, 5.2, 13.2, 2.6, 1.3));
  const bac = placer(seau, { rot: 128, cx: 12, cy: 12, k: 0.86, dx: 2.8, dy: -3.4 });
  const eclats = G.rect(2.6, 14.4, 3, 3, 0.6) + placer(G.rect(8.4, 17, 3, 3, 0.6), { rot: 30, cx: 9.9, cy: 18.5 }) + placer(G.rect(3.4, 19.6, 2.8, 2.8, 0.5), { rot: 15, cx: 4.8, cy: 21 });
  return [pl(bac), pa(eclats)];
};
I["dz-action-nettoyer"] = () => { // balai : virole + brosse pleines (poils fendus en bas), manche pâle
  let brosse = union(G.rect(-3.2, 0, 6.4, 2.8, 0.8), polyR([[-4, 4.4], [4, 4.4], [5.2, 10.4], [-5.2, 10.4]], 0.8));
  brosse = moins(brosse, G.rect(-2.6, 7, 1.6, 4.4, 0), G.rect(1, 7, 1.6, 4.4, 0));
  brosse = placer(brosse, { rot: 40, cx: 0, cy: 0, dx: 12, dy: 9.4 });
  return [pl(brosse), pa(pill(12.6, 8.6, 17.5, 2.8, 2.6))];
};
I["dz-action-recycler"] = () => {
  const c = [12, 12.6], R = 9.6, out = [];
  for (let i = 0; i < 3; i++) {
    const a = -90 + i * 120, b = a + 120, A = pt(...c, R, a), B = pt(...c, R, b);
    const P = t => [A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t];
    out.push(G.arrow(...P(0.16), ...P(0.86), 2.8, 7.2, 4.8));
  }
  return [pl(union(...out))];
};

// ═══════════════════════════════════════ ajouter / nouveau / dupliquer… (badge plus) ═══════════════════
I["dz-action-ajouter"] = () => [pl(union(G.rect(10.2, 2.6, 3.6, 18.8, 1.8), G.rect(2.6, 10.2, 18.8, 3.6, 1.8)))];
I["dz-action-nouveau"] = () => [badge("plus"), pl(M.feuille({ x: 3, y: 2, w: 15.4, h: 20 }))];
I["dz-action-nouveau-dossier"] = () => [badge("plus"), pl(M.dossier({ x: 2, y: 3, w: 20, h: 17 }))];
I["dz-action-dupliquer"] = () => { const F = (x, y) => M.feuille({ x, y, w: 12.6, h: 15.6, coin: 4.4 });
  return [badge("plus"), pl(F(2.4, 2)), pa(F(8.6, 6.6))]; };
I["dz-action-copier"] = () => { const F = (x, y) => M.feuille({ x, y, w: 12.6, h: 15.6, coin: 4.4 });
  return [pl(F(9, 6.4)), pa(F(2.4, 2))]; };
I["dz-action-coller"] = () => {
  const planche = moins(G.rect(2.6, 3.6, 14.4, 18.4, 1.6), G.rect(6.4, 1, 6.8, 2.6 + 0.01));
  const pince = rectR(6.4, 1.6, 6.8, 4.2, [1.2, 1.2, 0.6, 0.6]);
  const f = moins(M.feuille({ x: 9.8, y: 8.6, w: 12.2, h: 13.4, coin: 4 }), G.arrow(15.4, 11.6, 15.4, 20, 2, 6, 3.6));
  return [pl(f), pa(union(planche, pince))];
};
I["dz-action-ajouter-bibliotheque"] = () => { const o = { cx: 11, y: 2.2, w: 18, h: 9.8, pas: 4 };
  return [badge("plus"), pl(M.pile({ ...o, partie: "dessus" })), pa(M.pile({ ...o, partie: "dessous" }))]; };
I["dz-action-ajouter-calendrier"] = () => { const o = { x: 2, y: 1.6, w: 18.4, h: 19, grille: true };
  return [badge("plus"), pl(union(M.calendrier({ ...o, partie: "anneaux" }), M.calendrier({ ...o, partie: "bandeau" }))), pa(M.calendrier({ ...o, partie: "corps" }))]; };
I["dz-action-figer-recette"] = () => [badge("plus"), pl(moins(ficheRecette(), ficheLignes()))];
I["dz-action-lancer-recette"] = () => [pl(polyR([[12, 9.8], [22, 15.8], [12, 21.8]], 1)), pa(ficheRecette())];

// ═══════════════════════════════════════ importer / exporter / télécharger / envoyer ═══════════════════
I["dz-action-importer"] = () => [pl(M.fleche({ x1: 12, y1: 1.6, x2: 12, y2: 17.4, w: 3, hw: 9, hl: 6 })), pa(M.bac())];
I["dz-action-exporter"] = () => [pl(M.fleche({ x1: 12, y1: 17.4, x2: 12, y2: 1.6, w: 3, hw: 9, hl: 6 })), pa(M.bac())];
I["dz-action-telecharger"] = () => [pl(M.fleche({ x1: 12, y1: 1.6, x2: 12, y2: 17, w: 3, hw: 10, hl: 6.4 })), pa(G.rect(2.4, 19.4, 19.2, 2.8, 1.4))];
I["dz-action-envoyer-vers"] = () => [pl(M.flecheCoudee({ x: 6.4, y: 9.4, w: 15.8, h: 8.8, e: 2.8, hw: 8.4, hl: 5.4 })), pa(M.feuille({ x: 2, y: 1.6, w: 12, h: 15.4, coin: 4 }))];
I["dz-action-ouvrir-externe"] = () => {
  let cadre = G.rect(2.4, 4.6, 17, 17, 2) + G.rect(4.8, 7, 12.2, 12.2, 0.6);
  cadre = moins(cadre, G.rect(11.2, 3, 10, 9.4));
  return [pl(M.fleche({ x1: 9.6, y1: 14.4, x2: 21.8, y2: 2.2, w: 2.8, hw: 8.4, hl: 5.6 })), pa(cadre)];
};

// ═══════════════════════════════════════ publier / programmer / répondre ═══════════════════════════════
const avion = () => M.avion({ k: 0.94, dx: -1.6, dy: -1 });
I["dz-action-publier"] = () => [pl(M.avion({ k: 0.9, dx: 0.8, dy: -0.8 })), pa(pill(2.6, 21.4, 6.2, 17.8, 2.2) + pill(2.4, 15.4, 4.6, 13.2, 2.2))];
I["dz-action-programmer"] = () => [badge("horloge"), ...I["dz-action-publier"]()];
I["dz-action-repondre"] = () => {
  const fl = union(trait(lisse([[7.2, 14.6], [13, 14.6], [17, 16.2], [19.2, 21]], 10), 2.8), G.poly([[8.4, 9.6], [2.2, 14.6], [8.4, 19.6]]));
  return [pl(fl), pa(M.bulle({ x: 6.4, y: 1.6, w: 15.6, h: 10, queue: "droite" }))];
};

// ═══════════════════════════════════════ annuler / rétablir / restaurer / « re- » ═════════════════════
I["dz-action-annuler"] = () => [pl(boucle(12.6, 13, 7.8, 75, -175, 8.6, 5.8))];
I["dz-action-retablir"] = () => [pl(placer(boucle(12.6, 13, 7.8, 75, -175, 8.6, 5.8), { miroir: true, cx: 12 }))];
I["dz-action-actualiser"] = () => [pl(union(boucle(12, 12, 7.4, 200, 330, 6.8, 4.8), boucle(12, 12, 7.4, 20, 150, 6.8, 4.8)))];
I["dz-action-reessayer"] = () => [pl(boucle(12, 12.4, 8.2, -45, 250, 7.4, 5)), pa(G.rect(10.8, 7.4, 2.4, 5.6, 1.2) + G.circle(12, 16, 1.3))];
I["dz-action-recalculer"] = () => [pl(boucle(12, 12, 8.4, 140, 420, 7.4, 5)), pa(M.engrenage({ cx: 12, cy: 12, r: 5, n: 6, moyeu: 1.6 }))];
I["dz-action-regenerer"] = () => [badge("etincelle"), pl(boucle(11, 11, 8, 95, 355, 7.2, 5))];
I["dz-action-reinitialiser"] = () => [pl(boucle(11.6, 12.8, 7.6, -112, -398, 7, 4.8)), pa(G.circle(...pt(11.6, 12.8, 7.6, -74), 2.2))];
I["dz-action-restaurer"] = () => {
  const aig = union(pill(12.4, 12.8, 12.4, 8.6, 2.2), pill(12.1, 12.6, 15.2, 14.4, 2.2));
  return [pl(boucle(12.4, 12.8, 8.2, 160, -120, 7, 4.8)), pa(aig)];
};
I["dz-action-redefinir"] = () => [pl(boucle(10.4, 11.2, 6, 180, 358, 7.4, 5)), pa(moins(G.rect(8.6, 14.6, 13.4, 7.6, 1.4), G.rect(15.4, 1, 8, 15.6)))];

// ═══════════════════════════════════════ chercher / zoom / vue ═════════════════════════════════════════
I["dz-action-chercher"] = () => [pl(M.loupe(LOUPE))];
I["dz-action-zoom-avant"] = () => loupeSigne(union(G.rect(5.1, 7.5, 8.2, 3.4, 1.2), G.rect(7.5, 5.1, 3.4, 8.2, 1.2)));
I["dz-action-zoom-arriere"] = () => loupeSigne(G.rect(5.1, 7.5, 8.2, 3.4, 1.2));
I["dz-action-recherche-semantique"] = () => [badge("etincelle"), pl(loupeBadge())];
I["dz-action-ajuster-vue"] = () => [pl(equerres(2, 2, 20, 6.4, 2.6)), pa(G.rect(7.2, 8.4, 9.6, 7.2, 1))];
I["dz-action-capturer"] = () => [pl(G.circle(12, 12, 3.4)), pa(equerres(3.6, 3.6, 16.8, 5, 2.4, 1.2))];
I["dz-action-recentrer"] = () => [pl(G.circle(12, 12, 3.6)), pa(G.ring(12, 12, 10, 7.6))];

// ═══════════════════════════════════════ navigation d'assistant / défilement ══════════════════════════
I["dz-action-continuer"] = () => [pl(M.fleche({ x1: 2.4, y1: 12, x2: 21.6, y2: 12, w: 3, hw: 11, hl: 7 }))];
I["dz-action-retour"] = () => [pl(M.fleche({ x1: 21.6, y1: 12, x2: 2.4, y2: 12, w: 3, hw: 11, hl: 7 }))];
I["dz-action-deplier"] = () => [pl(trait([[4.6, 8.6], [12, 16], [19.4, 8.6]], 3.2))];
const points3 = x0 => G.circle(x0, 12, 1.1) + G.circle(x0 + 3.8, 12, 1.1) + G.circle(x0 + 7.6, 12, 1.1);
I["dz-action-element-precedent"] = () => [pl(trait([[9.2, 4.6], [3.4, 12], [9.2, 19.4]], 3)), pa(points3(13.4))];
I["dz-action-element-suivant"] = () => [pl(trait([[14.8, 4.6], [20.6, 12], [14.8, 19.4]], 3)), pa(points3(3))];
I["dz-action-trier"] = () => [pl(M.fleche({ x1: 7, y1: 21.6, x2: 7, y2: 2.4, w: 2.8, hw: 8, hl: 5.6 }) + M.fleche({ x1: 17, y1: 2.4, x2: 17, y2: 21.6, w: 2.8, hw: 8, hl: 5.6 }))];
I["dz-action-duel"] = () => [pl(M.fleche({ x1: 1.8, y1: 12, x2: 10.6, y2: 12, w: 2.8, hw: 10, hl: 5.6 }) + M.fleche({ x1: 22.2, y1: 12, x2: 13.4, y2: 12, w: 2.8, hw: 10, hl: 5.6 }))];

// ═══════════════════════════════════════ menus / vues / panneaux ═══════════════════════════════════════
I["dz-action-menu"] = () => [pl(G.rect(3, 4.4, 18, 2.8, 1.4) + G.rect(3, 10.6, 18, 2.8, 1.4) + G.rect(3, 16.8, 18, 2.8, 1.4))];
I["dz-action-plus-options"] = () => [pl(G.circle(4.6, 12, 2.4) + G.circle(12, 12, 2.4) + G.circle(19.4, 12, 2.4))];
I["dz-action-poignee"] = () => { let d = ""; for (const x of [9, 15]) for (const y of [5, 12, 19]) d += G.circle(x, y, 1.9); return [pl(d)]; };
I["dz-action-vue-grille"] = () => [pl(M.grille({ x: 2.4, y: 2.4, w: 19.2, h: 19.2, n: 3, m: 3, g: 2.2, r: 1 }))];
I["dz-action-vue-liste"] = () => { let p = "", l = ""; for (const y of [4.2, 10.4, 16.6]) { p += G.rect(2, y, 4.2, 4.2, 0.8); l += G.rect(8, y + 0.8, 14, 2.6, 1.3); } return [pl(p), pa(l)]; };
I["dz-action-panneau-lateral"] = () => [pl(rectR(2, 3, 7, 18, [1.4, 0, 0, 1.4])), pa(moins(rectR(2, 3, 20, 18, [1.4, 1.4, 1.4, 1.4]), G.rect(4, 5.2, 15.8, 13.6, 0.6)))];
I["dz-action-disposition-colonne"] = () => [pl(G.rect(5.8, 6.6, 12.4, 4.6, 0.8) + G.rect(5.8, 12.8, 12.4, 4.6, 0.8)), pa(G.rect(2, 3, 20, 18, 1.4) + G.rect(4.2, 5.2, 15.6, 13.6, 0.6))];
I["dz-action-comparer"] = () => [pl(union(G.rect(10.8, 1.6, 2.4, 20.8, 1.2), G.circle(12, 12, 3.4))), pa(G.rect(2, 4, 9, 16, 1.4) + G.rect(13, 4, 9, 16, 1.4))];

// ═══════════════════════════════════════ enregistrer / ouvrir / ranger ════════════════════════════════
I["dz-action-enregistrer"] = () => { // l'étiquette pâle est posée DANS la fenêtre : calque du dessus (sinon la réserve, qui bouche les trous, la mangerait)
  const x = 3, y = 3, s = 18;
  const corps = moins(polyR([[x, y], [x + s - 4, y], [x + s, y + 4], [x + s, y + s], [x, y + s]], 1.4), G.rect(x + 3.6, y + 2.4, s - 9.6, 4.6, 0.6));
  return [pa(G.rect(x + 3.6, y + s - 7.6, s - 7.2, 4, 0.6)), pl(corps)];
};
I["dz-action-enregistrer-modele"] = () => [pl(M.disquette({ x: 8.4, y: 8.4, s: 13.6 })), pa(G.rect(2, 2, 7.4, 20, 1.4) + G.rect(10.6, 2, 11.4, 5.4, 1.4))];
I["dz-action-ouvrir"] = () => { const o = { x: 2, y: 3, w: 20, h: 17.4, ouvert: true };
  return [pl(M.dossier({ ...o, partie: "rabat" })), pa(M.dossier({ ...o, partie: "dos" }))]; };
I["dz-action-ranger"] = () => [pl(M.fleche({ x1: 12, y1: 1.4, x2: 12, y2: 17.8, w: 3, hw: 9, hl: 6 })), pa(M.dossier({ x: 2, y: 6.4, w: 20, h: 15.6 }))];
I["dz-action-rangement-auto"] = () => [pl(boucle(14.5, 14.8, 5, 120, 400, 6.6, 4.4)), pa(M.dossier({ x: 2, y: 2, w: 17, h: 14.4 }))];
I["dz-action-choisir-bibliotheque"] = () => {
  const curseur = placer(polyR([[0, 0], [0, 14.4], [3.8, 11], [6.4, 16.4], [9, 15.2], [6.6, 9.8], [11.4, 9.8]], 0.6), { cx: 0, cy: 0, k: 0.9, dx: 11.4, dy: 7.4 });
  const o = { cx: 10, y: 2, w: 17, h: 9.4, pas: 3.8 };
  return [pl(curseur), pa(M.pile(o))];
};

// ═══════════════════════════════════════ édition, texte ════════════════════════════════════════════════
I["dz-action-modifier"] = () => [pl(M.crayon({ k: 1, dx: -0.4, dy: -0.4 })), pa(G.rect(12.6, 19.6, 9.4, 2.4, 1.2))];
I["dz-action-renommer"] = () => [pl(M.curseurTexte({ cx: 15.6, y: 2.2, h: 19.6 })), pa(G.rect(2, 7, 20, 10, 2) + G.rect(4.2, 9.2, 15.6, 5.6, 0.6)), pa(G.rect(5.4, 10.8, 5.6, 2.4, 1.2))];
I["dz-action-reecrire-ia"] = () => [badge("etincelle"), pl(G.rect(2, 3, 20, 2.6, 1.3) + G.rect(2, 8.6, 20, 2.6, 1.3) + G.rect(2, 14.2, 10.4, 2.6, 1.3) + G.rect(2, 19.4, 7, 2.6, 1.3))];
I["dz-action-langue"] = () => {
  const wen = union(G.rect(15, 1.6, 2.4, 2.4, 0.6), G.rect(10.6, 4.6, 11.4, 2.2, 1.1), pill(13, 9, 21.2, 16.6, 2.2), pill(20, 9, 11.8, 16.6, 2.2));
  return [pl(M.lettreA({ k: 0.66, dx: -3.2, dy: 3.6 })), pa(wen)];
};
I["dz-action-aide"] = () => {
  const q = union(arc(12, 9.2, 3.4, 2.4, 180, 395), G.rect(10.8, 11, 2.4, 3.6, 0.6));
  return [pl(moins(G.circle(12, 12, 10.2), q, G.circle(12, 18.2, 1.5)))];
};
I["dz-action-raccourcis"] = () => {
  let k = G.rect(1.6, 4.4, 20.8, 15.2, 2);
  for (const y of [6.6, 10.8]) for (let i = 0; i < 4; i++) k = moins(k, G.rect(3.9 + i * 4.6, y, 2.4, 2.2, 0.4));
  k = moins(k, G.rect(6.4, 15, 11.2, 1.8, 0.6));
  return [pl(k)];
};
I["dz-action-palette-commandes"] = () => { // fenêtre dont la ligne de saisie (invite « › » + curseur) est en haut ; résultats pâles dessous
  const barre = moins(G.rect(2, 2, 20, 7.6, 2), trait([[5.4, 3.8], [7.8, 5.8], [5.4, 7.8]], 1.8), G.rect(15.6, 3.6, 1.8, 4.4, 0.4));
  const corps = moins(G.rect(2, 11.2, 20, 10.8, 1.4), G.rect(4.4, 13.4, 13.6, 2.4, 1.2), G.rect(4.4, 17.6, 9, 2.4, 1.2));
  return [pl(barre), pa(corps)];
};

// ═══════════════════════════════════════ générer / IA / fabriquer / lancer ════════════════════════════
I["dz-action-generer"] = () => {
  const st = (x, y, R) => { const k = R * 0.16; return `M${x} ${y - R}Q${x + k} ${y - k} ${x + R} ${y}Q${x + k} ${y + k} ${x} ${y + R}Q${x - k} ${y + k} ${x - R} ${y}Q${x - k} ${y - k} ${x} ${y - R}Z`; };
  return [pl(st(10.4, 12.6, 8.6)), pa(st(19, 4.8, 3.4) + st(19.4, 19.2, 2.8))];
};
I["dz-action-aleatoire"] = () => {
  const c = [12, 12], s = 17;
  let de = G.rect(c[0] - s / 2, c[1] - s / 2, s, s, 3.6);
  for (const [dx, dy] of [[-4.2, -4.2], [4.2, -4.2], [0, 0], [-4.2, 4.2], [4.2, 4.2]]) de = moins(de, G.circle(c[0] + dx, c[1] + dy, 1.6));
  return [pl(placer(de, { rot: -12, cx: 12, cy: 12 }))];
};
I["dz-action-fabriquer"] = () => {
  const tete = placer(G.rect(-6, -2.6, 12, 5.2, 1), { rot: -45, cx: 0, cy: 0, dx: 11.6, dy: 10 });
  const manche = pill(13.2, 11.6, 21, 19.4, 2.8);
  return [pl(union(tete, manche)), pa(G.rect(2, 13.6, 8.4, 8.4, 1.2))];
};
I["dz-action-lancer"] = () => {
  const corps = union(`M12 1.4C15.4 4 16.2 8.4 15.6 15.2H8.4C7.8 8.4 8.6 4 12 1.4Z`, polyR([[8.6, 10.2], [4.6, 15.4], [4.6, 18], [8.6, 16]], 0.6), polyR([[15.4, 10.2], [19.4, 15.4], [19.4, 18], [15.4, 16]], 0.6));
  const fusee = moins(corps, G.circle(12, 8.2, 1.8));
  const flamme = `M9.6 17H14.4C14.4 19.4 13.2 21 12 22.8C10.8 21 9.6 19.4 9.6 17Z`;
  return [pl(placer(fusee, { rot: 45, cx: 12, cy: 12, dx: 0.6, dy: -0.6 })), pa(placer(flamme, { rot: 45, cx: 12, cy: 12, dx: 0.6, dy: -0.6 }))];
};
I["dz-action-suggerer"] = () => {
  const ampoule = union(G.circle(10.4, 8.2, 6.4), polyR([[5.4, 9.4], [15.4, 9.4], [13.8, 15], [7, 15]], 1));
  return [badge("etincelle"), pl(ampoule), pa(G.rect(7, 16.6, 6.8, 2.2, 1.1) + G.rect(8.2, 19.8, 4.4, 2.2, 1.1))];
};
I["dz-action-rouvrir-quick"] = () => [badge("fleche-sortante"), pl(M.eclair({ k: 0.92, dx: -2.2, dy: -0.8 }))];
I["dz-action-rouvrir-studio"] = () => { const o = { x: 2, y: 2, w: 16.4, h: 13.6, n: 5.4 };
  return [badge("fleche-sortante"), pl(M.graphe({ ...o, partie: "noeuds" })), pa(M.graphe({ ...o, partie: "liens" }))]; };
I["dz-action-decouper-plans"] = () => {
  let bande = G.rect(15, 1.6, 7, 13.4, 1.2);
  bande = moins(bande, G.rect(14, 5.6, 9, 1.6), G.rect(14, 9.8, 9, 1.6));
  const ciseaux = union(G.ring(4.8, 6.2, 3, 1), G.ring(4.8, 16.6, 3, 1), pill(7.4, 8, 13.2, 13.4, 2.4), pill(7.4, 14.8, 13.2, 9.4, 2.4));
  return [badge("etincelle"), pl(ciseaux), pa(bande)];
};
I["dz-action-tester"] = () => {
  const ext = polyR([[8.6, 1.8], [15.4, 1.8], [15.4, 3.6], [14.4, 3.6], [14.4, 8.6], [21, 20.2], [19.8, 22.2], [4.2, 22.2], [3, 20.2], [9.6, 8.6], [9.6, 3.6], [8.6, 3.6]], 0.8);
  const paroi = moins(ext, M.eroder(ext, 2.2));
  const liquide = inter(M.eroder(ext, 3.7), G.rect(0, 13.6, 24, 10));
  return [pl(liquide), pa(paroi)];
};
I["dz-action-mesurer"] = () => {
  const c = [12, 16.4];
  return [pl(union(G.circle(...c, 2.6), pill(...c, ...pt(...c, 8, -55), 2.6))), pa(arc(...c, 9, 3, 180, 360))];
};
I["dz-action-cout"] = () => { // pile de pièces sans signe monétaire (neutre : wallet en USD) : face du dessus pleine, tranches pâles
  const tranches = G.rect(3, 10.2, 18, 3.2, 1.6) + G.rect(3, 15, 18, 3.2, 1.6) + G.rect(3, 19.8, 18, 2.6, 1.3);
  return [pl(ellipse(12, 5.2, 9, 3.6)), pa(tranches)];
};
I["dz-action-quantite"] = () => { // trois cartes nues en éventail (pivot en bas), celle de devant pleine
  const carte = a => M.carte({ cx: 12, cy: 11.4, w: 9.6, h: 14.6, angle: 0 }), P = (d, a) => placer(d, { rot: a, cx: 12, cy: 21 });
  return [pl(P(carte(), 22)), pa(P(carte(), 0)), pa(P(carte(), -22))];
};
I["dz-action-favori"] = () => [pl(M.etoile())];
I["dz-action-valider"] = () => [pl(M.coche())];
I["dz-action-reglages"] = () => [pl(M.engrenage())];
I["dz-action-theme"] = () => [pl(`M12 4.2A7.8 7.8 0 0 1 12 19.8Z`), pa(G.ring(12, 12, 10.2, 7.8))];
I["dz-action-tout-selectionner"] = () => [pl(moins(G.rect(2, 7.4, 14.6, 14.6, 2.2), M.coche({ x: 4.2, y: 9.6, s: 10.2, w: 2.4 }))), pa(G.rect(7.4, 2, 14.6, 14.6, 2.2))];
I["dz-action-detourer"] = () => [pl(M.buste({ cx: 13.4, y: 5, w: 13.6, h: 17 })), pa(M.damier({ x: 2, y: 2, s: 20, n: 4 }))];
I["dz-action-connecter"] = () => {
  const fiche = union(G.rect(2, 7.4, 8.6, 9.2, 2), G.rect(10, 8.8, 4.4, 2.2, 0.6), G.rect(10, 13, 4.4, 2.2, 0.6));
  return [pl(fiche), pa(rectR(16, 2.6, 6, 18.8, [2, 1.4, 1.4, 2]))];
};
I["dz-action-reprendre-reglages"] = () => [pl(M.fleche({ x1: 18.6, y1: 22, x2: 18.6, y2: 2, w: 2.8, hw: 8, hl: 5.6 })),
  pa(M.reglette({ x: 2, cy: 7.2, w: 12.4, pos: 0.8, rb: 2.4 }) + M.reglette({ x: 2, cy: 16.8, w: 12.4, pos: 0.2, rb: 2.4 }))];
I["dz-action-recurrence"] = () => [pl(boucle(14.4, 14.8, 5.2, 110, 390, 6.6, 4.4)), pa(M.calendrier({ x: 2, y: 1.6, w: 18.4, h: 19 }))];

// ═══════════════════════════════════════ série téléphone ↔ PC ═════════════════════════════════════════
I["dz-action-appairer"] = () => [pl(tel(7, 14.4, 8.4, 15.2)), pl(M.maillon({ cx: 17.6, cy: 17.2, l: 9.6, w: 6.4, e: 2.2, angle: -45 })), pa(pc(2, 1.8, 20, 10.4))];
I["dz-action-emporter"] = () => [pl(tel(17.8, 12, 8.4, 20)), pl(M.fleche({ x1: 2.2, y1: 18.8, x2: 12.2, y2: 18.8, w: 2.6, hw: 6.6, hl: 4.6 })), pa(pc(2, 2.4, 10.4, 8.4) + piedPc(2, 2.4, 10.4, 8.4))];
I["dz-action-transferer-pc"] = () => [pl(pc(10.2, 4, 11.8, 10.4) + piedPc(10.2, 4, 11.8, 10.4)), pl(M.fleche({ x1: 2.2, y1: 19.4, x2: 8.6, y2: 19.4, w: 2.6, hw: 6.6, hl: 4.4 })), pa(tel(5.2, 8.4, 6.4, 12.8))];
I["dz-action-synchroniser"] = () => [pl(union(boucle(12, 12, 9.2, 200, 330, 5.2, 4), boucle(12, 12, 9.2, 20, 150, 5.2, 4))), pa(tel(12, 12, 6.8, 11))];
I["dz-action-epingler-mobile"] = () => [pl(M.punaise({ k: 0.6, dx: 4.6, dy: -4.4 })), pa(tel(9.4, 13, 11, 18))];
I["dz-action-scanner-qr"] = () => {
  const rep = (x, y) => G.rect(x, y, 5.6, 5.6, 0.8) + G.rect(x + 2, y + 2, 1.6, 1.6, 0.2);
  return [pl(rep(5.6, 5.6) + rep(12.8, 5.6) + rep(5.6, 12.8) + G.rect(13.8, 13.8, 3.6, 3.6, 0.6)), pa(equerres(1.8, 1.8, 20.4, 5.4, 2.2))];
};

I["dz-action-apercu"] = () => {
  const R0 = (7.4 ** 2 + 4.4 ** 2) / 8.8, oeil = moins(`M4.6 9.8A${R0} ${R0} 0 0 1 19.4 9.8A${R0} ${R0} 0 0 1 4.6 9.8Z`, G.circle(12, 9.8, 2.3));
  return [pl(oeil), pa(G.rect(2, 2, 20, 15.6, 1.4) + G.rect(7, 19.4, 10, 2.4, 1.2))];
};
I["dz-action-convertir"] = () => {
  const F = (x, y) => M.feuille({ x, y, w: 8, h: 10, coin: 3 });
  return [pl(M.fleche({ x1: 11.4, y1: 6.4, x2: 22, y2: 6.4, w: 2.6, hw: 7, hl: 4.6 }) + M.fleche({ x1: 12.6, y1: 17.6, x2: 2, y2: 17.6, w: 2.6, hw: 7, hl: 4.6 })), pa(F(2, 1.6) + F(14, 12.4))];
};

// ═══════════════════════════════════════ écriture ═════════════════════════════════════════════════════
const LEX = require("../lexique.json").filter(e => e.famille === "action").map(e => e.cle);
const manquent = LEX.filter(k => !I[k]), enTrop = Object.keys(I).filter(k => !LEX.includes(k));
if (manquent.length || enTrop.length) console.log("manquent :", manquent.join(", ") || "—", "| en trop :", enTrop.join(", ") || "—");
const filtre = process.argv[2] || "";
let n = 0;
for (const [cle, fn] of Object.entries(I)) {
  if (filtre && !cle.includes(filtre)) continue;
  fs.writeFileSync(path.join(OUT, cle + ".svg"), M.icone(fn()));
  n++;
}
console.log(n + " icônes écrites dans " + OUT);
