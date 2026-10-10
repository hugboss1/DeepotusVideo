// Mission « media » : types de média, transport, timeline, pistes, audio, voix, sous-titres, images clés…
// Usage : node dessin/media.js [filtre]
// Chaque icône = liste de calques DU HAUT VERS LE BAS passée à M.icone (règle du monochrome : chaque calque
// est évidé de la réserve 1,5 de ceux du dessus ; badge : 1,4).
"use strict";
const fs = require("fs"), path = require("path");
const G = require("../geo.js"), M = require("../motifs.js"), MM = require("./motifs-media.js");
const OUT = path.join(__dirname, "..", "svg");
const PALE = .38;
const pl = (d, x = {}) => ({ d, op: 1, ...x }), pa = (d, x = {}) => ({ d, op: PALE, ...x });
const badge = type => ({ d: M.badge(type), op: 1, reserve: M.RES_BADGE });
const { union, moins, inter, placer, arc, rectR, polyR, pt, trait, lisse, pill, ellipse, reserve, aire } = M;
const I = {};

// ═══════════════════════════════ Série transport (CHARTE §6) ═══════════════════════════════════════════
// Gabarit commun : hauteur 16 (y 4–20), centré sur 12 ; triangles arrondis 1 ; barres 2,8 à rayon 1,2.
const T = { y0: 4, y1: 20 };
I["dz-media-lecture"] = () => [pl(MM.tri(6.4, 20.2, T.y0, T.y1))];
I["dz-media-pause"] = () => [pl(G.rect(5.2, T.y0, 5, 16, 1.4) + G.rect(13.8, T.y0, 5, 16, 1.4))];
I["dz-media-arret"] = () => [pl(G.rect(4.6, 4.6, 14.8, 14.8, 1.8))];
I["dz-media-precedent"] = () => [pl(G.rect(3.6, T.y0, 3, 16, 1.2) + MM.tri(8.2, 20.4, T.y0, T.y1, "gauche"))];
I["dz-media-suivant"] = () => [pl(G.rect(17.4, T.y0, 3, 16, 1.2) + MM.tri(3.6, 15.8, T.y0, T.y1, "droite"))];
// image par image : petit triangle + une case d'image pâle (même hauteur 16)
const caseImage = x => G.rect(x, T.y0, 8.4, 16, 1.4) + "";
I["dz-media-image-precedente"] = () => [pl(MM.tri(2.4, 10, 7, 17, "gauche")), pa(caseImage(13.2))];
I["dz-media-image-suivante"] = () => [pl(MM.tri(14, 21.6, 7, 17, "droite")), pa(caseImage(2.4))];
I["dz-media-rec"] = () => [pl(G.circle(12, 12, 5.4)), pa(G.ring(12, 12, 10, 7.8))];
I["dz-media-vitesse"] = () => { // compteur : traits gradués sur un arc pâle, aiguille pleine et moyeu
  const c = [12, 16.4], ticks = [];
  for (let i = 0; i <= 6; i++) { const a = 180 + i * 30; ticks.push(pill(...pt(...c, 7.8, a), ...pt(...c, 10, a), 2.2)); }
  const aig = union(G.circle(...c, 2.8), pill(...c, ...pt(...c, 6.6, -52), 2.4));
  return [pl(aig), pa(union(...ticks, G.rect(2, 19.4, 20, 2.4, 1.2)))];
};

// ═══════════════════════════════ Types de média (série types-media) ════════════════════════════════════
I["dz-media-image"] = () => [pl(M.image({ partie: "paysage" })), pa(M.image({ partie: "cadre" }))];
// écran 16:9 en anneau, triangle plein au centre, barre de progression pâle dessous (≠ logo YouTube plein)
const ecranVideo = () => [pl(MM.tri(9.4, 15.8, 6.6, 13.8) + G.rect(2, 2.6, 20, 14.8, 1.6) + G.rect(4.2, 4.8, 15.6, 10.4, 0.6)), pa(G.rect(2, 19.2, 20, 2.6, 1.3))];
I["dz-media-video"] = () => ecranVideo();
I["dz-media-film"] = () => { // bandes perforées pâles, trois cases pleines
  let bandes = G.rect(4, 2, 4, 20, 1) + G.rect(16, 2, 4, 20, 1);
  for (let i = 0; i < 5; i++) { const y = 3.4 + i * 3.8; bandes = moins(bandes, G.rect(3, y, 2.6, 1.6), G.rect(18.4, y, 2.6, 1.6)); }
  const cases = [0, 1, 2].map(i => G.rect(9.5, 2 + i * 6.93, 5, 5.33, 0.8)).join("");
  return [pl(cases), pa(bandes)];
};
I["dz-media-audio"] = () => [pl(M.hautParleur({ partie: "corps" })), pa(M.hautParleur({ partie: "ondes" }))];
I["dz-media-texte"] = () => [pl(M.lettreT({ k: 0.8, dy: -1.6 })), pa(G.rect(2.4, 19.6, 19.2, 2.4, 1.2))];
I["dz-media-fichier"] = () => [pl(M.feuille({ lignes: 3, partie: "corps" })), pa(M.feuille({ partie: "oreille" }))];
I["dz-media-post"] = () => [ // carte pâle, vignette pleine en haut, deux lignes
  pl(G.rect(7, 5.6, 10, 6.2, 0.8) + G.rect(7, 13.3, 10, 2.2, 1.1) + G.rect(7, 17, 6.4, 2.2, 1.1)),
  pa(G.rect(3.5, 2, 17, 20.6, 2.4))];
I["dz-media-reel"] = () => [pl(MM.tri(10, 16.8, 8.2, 15.8)), pa(G.rect(5, 1.8, 14, 20.4, 2.4) + G.rect(7.2, 4, 9.6, 16, 0.8))];

// ═══════════════════════════════ Timeline, pistes, images clés ═════════════════════════════════════════
I["dz-media-tete-lecture"] = () => [pl(polyR([[5, 2.2], [19, 2.2], [19, 6.4], [12, 11.6], [5, 6.4]], 1)), pa(G.rect(10.7, 13.1, 2.6, 9, 1.3))];
const regle = (x = 2, w = 20) => { // règle graduée (pâle) : corps, graduations creusées depuis le haut (pas 4)
  let d = G.rect(x, 2.6, w, 8, 1.2);
  for (let i = 0, gx = x + 3.4; gx + 1.6 < x + w - 2; i++, gx += 4) d = moins(d, G.rect(gx, 1.6, 1.6, i % 2 ? 5.6 : 3.8));
  return d;
};
// allonger : règle courte + double flèche vers l'extérieur ; raccourcir : règle pleine largeur + deux flèches vers le centre
I["dz-media-timeline-allonger"] = () => [pl(union(G.arrow(12, 17.2, 2, 17.2, 2.6, 9.2, 6), G.arrow(11.9, 17.2, 22, 17.2, 2.6, 9.2, 6))), pa(regle(6, 12))];
I["dz-media-timeline-raccourcir"] = () => [pl(G.arrow(2, 17.2, 11.2, 17.2, 2.6, 9.2, 6) + G.arrow(22, 17.2, 12.8, 17.2, 2.6, 9.2, 6)), pa(regle())];
const clip = () => G.rect(2, 2.5, 20, 13.5, 2);
I["dz-media-piste-audio"] = () => [badge("plus"),
  pl(G.rect(6, 7.2, 2.4, 4.2, 1.2) + G.rect(10.4, 5.6, 2.4, 7.4, 1.2) + G.rect(14.8, 7.6, 2.4, 3.4, 1.2)), pa(clip())];
I["dz-media-piste-video"] = () => [badge("plus"), pl(G.rect(6, 6, 5, 6.5, 0.8) + G.rect(13, 6, 5, 6.5, 0.8)), pa(clip())];
I["dz-media-incrustation"] = () => [badge("plus"), pl(G.rect(12.6, 6.6, 6.4, 4.8, 0.6)), pa(G.rect(2, 3, 20, 16, 1.4) + G.rect(4.2, 5.2, 15.6, 11.6, 0.6))];
I["dz-media-titre"] = () => [badge("plus"), pl(union(G.rect(2, 2, 16, 4.4, 0.8), G.rect(7.6, 2, 4.4, 19.6, 0.8)))];
I["dz-media-muet"] = () => [pl(M.hautParleur({ partie: "corps" })), pa(G.cross(17.4, 12, 9.4, 2.4))];
I["dz-media-solo"] = () => [
  pl(G.rect(2, 13, 5.6, 9, 1.8) + G.rect(16.4, 13, 5.6, 9, 1.8)),
  pa(union(arc(12, 12.4, 8.4, 2.4, 180, 360), G.rect(2.4, 12.4, 2.4, 3), G.rect(19.2, 12.4, 2.4, 3)))];
I["dz-media-marqueur"] = () => [pl(polyR([[8.4, 2.4], [21, 7.6], [8.4, 12.8]], 0.8)), pa(G.rect(4, 2, 2.6, 20, 1.3))];
I["dz-media-image-cle"] = () => [badge("plus"), pl(MM.losange(10.6, 10.6, 8.6))];
I["dz-media-image-cle-retirer"] = () => // losange plein suivi d'un trait « moins » plein, sans pastille (silhouette ≠ image clé + badge)
  [pl(G.rect(17, 10.6, 5, 2.8, 1.4)), pl(MM.losange(9.2, 12, 7.4, 7.4, 0.8))];
I["dz-media-automation"] = () => {
  const P = [[4.4, 17.4], [12, 6.4], [19.6, 15.4]];
  const courbe = trait(lisse(P, 14), 2.2);
  return [pl(P.map(p => MM.losange(...p, 3)).join("")), pa(courbe)];
};
I["dz-media-inserer"] = () => [pl(M.flecheCoudee({ x: 4, y: 2, w: 16, h: 9.6 })), pa(G.rect(2, 17.4, 20, 4.6, 1.4))];

// ═══════════════════════════════ Son ══════════════════════════════════════════════════════════════════
const sinus = (x0, x1, cy, amp, per, ph = 0) => { const p = []; for (let x = x0; x <= x1 + 1e-6; x += 0.25) p.push([x, cy - amp * Math.sin(ph + 2 * Math.PI * (x - x0) / per)]); return p; };
I["dz-media-forme-onde"] = () => [pl(trait(sinus(3.2, 20.8, 12, 6.4, 11.7), 2.6))];
I["dz-media-ameliorer"] = () => [
  pl(trait(sinus(12.6, 20.8, 12, 4.6, 8.2, 0), 2.6)),
  pa(trait([[3.2, 12], [5, 7.4], [6.8, 16.2], [8.6, 9.4], [10.4, 12]], 2.2))];
I["dz-media-extraire-son"] = () => {
  let bande = G.rect(2, 2, 7.4, 20, 1);
  for (let i = 0; i < 5; i++) { const y = 3.4 + i * 3.8; bande = moins(bande, G.rect(1, y, 2.6, 1.6), G.rect(7.8, y, 2.6, 1.6)); }
  bande = moins(bande, G.rect(4.6, 4.4, 1.6, 15.2, 0.6));
  return [pl(G.rect(11.6, 8.4, 2.4, 7.2, 1.2) + G.rect(15.6, 4, 2.4, 16, 1.2) + G.rect(19.6, 9.4, 2.4, 5.2, 1.2)), pa(bande)];
};
I["dz-media-stems"] = () => [badge("etincelle"),
  pl(G.rect(10.4, 2.6, 11.6, 2.6, 1.3) + G.rect(10.4, 7.4, 11.6, 2.6, 1.3) + G.rect(10.4, 12.2, 3.4, 2.6, 1.3)),
  pa(G.rect(2, 7, 2.4, 10, 1.2) + G.rect(5.6, 3, 2.4, 18, 1.2))];

// ═══════════════════════════════ Voix (profil) ═════════════════════════════════════════════════════════
const ondesVoix = (cx, cy, rs, a0 = -42, a1 = 42) => rs.map(r => arc(cx, cy, r, 2.4, a0, a1)).join("");
I["dz-media-voix"] = () => [pl(MM.profil({ k: 0.9, dx: -1.8 })), pa(union(ondesVoix(13.4, 12.8, [4, 7.8], -40, 40)))];
I["dz-media-generer-voix"] = () => [badge("etincelle"), pl(MM.profil({ k: 0.94, dx: -0.6 })), pa(arc(15.4, 10.6, 5, 2.4, -60, 0))];
I["dz-media-cloner-voix"] = () => [badge("etincelle"), pl(MM.profil({ k: 0.82, dx: 1.4, dy: 1.6 })), pa(MM.profil({ k: 0.82, dx: -3.4, dy: -1.6 }))];
I["dz-media-isoler-voix"] = () => {
  const p = MM.profil({ k: 0.8, dx: -2.2, dy: 0.8 }), r = reserve(p, 1.5), b = M.badge("etincelle", { trou: 1.4 });
  const pts = []; // trame de bruit : points Ø2,2 au pas 4,2, gardés seulement s'ils sont hors réserves
  for (let y = 3; y < 22; y += 3.8) for (let x = 3 + (Math.round((y - 3) / 3.8) % 2) * 1.9; x < 22; x += 3.8) {
    const d = G.circle(x, y, 1.1); if (!aire(inter(d, r)) && !aire(inter(d, b)) && x < 21 && y < 21) pts.push(d); }
  return [badge("etincelle"), pl(p), pa(pts.join(""))];
};
I["dz-media-dicter"] = () => [pl(M.micro({ partie: "capsule" })), pa(M.micro({ partie: "pied" }))];
I["dz-media-preecoute"] = () => { // oreille : hélix pleine, conque pâle
  const helix = trait(lisse([[6.4, 9.6], [8.2, 4.4], [12.6, 2.6], [17.2, 4.8], [18.4, 9.6], [16.6, 13.6], [14, 15.6], [13.2, 19], [10.6, 21.4], [7.6, 20.4]], 12), 2.6);
  const conque = trait(lisse([[10.4, 12.4], [10.6, 8.6], [13, 7.6], [14.6, 9.4], [13.4, 12.2]], 12), 2.2);
  return [pl(helix), pa(conque)];
};
I["dz-media-avatar"] = () => [pl(M.buste({ cx: 8, y: 3.4, w: 12, h: 18.6 })), pa(union(ondesVoix(8, 7.9, [7.6, 11.6], -32, 26)))];
I["dz-media-persona"] = () => [pl(M.bulle({ x: 9.4, y: 2, w: 12.6, h: 8.4, queue: "gauche" })), pa(M.buste({ cx: 8.4, y: 9.6, w: 12.8, h: 12.4 }))];
I["dz-media-apparitions"] = () => [
  pl(G.rect(13.2, 5, 8.8, 2.6, 1.3) + G.rect(13.2, 10.7, 8.8, 2.6, 1.3) + G.rect(13.2, 16.4, 6, 2.6, 1.3)),
  pa(M.buste({ cx: 6.6, y: 4, w: 9.2, h: 16 }))];

// ═══════════════════════════════ Images, vidéo, IA ═════════════════════════════════════════════════════
I["dz-media-generer-image"] = () => [badge("etincelle"), pl(M.image({ partie: "paysage" })), pa(M.image({ partie: "cadre" }))];
I["dz-media-generer-video"] = () => [badge("etincelle"), ecranVideo()[0]]; // même écran, la barre de progression laisse place au badge
I["dz-media-generer-script"] = () => [badge("etincelle"), pl(M.feuille({ lignes: 3, partie: "corps" })), pa(M.feuille({ partie: "oreille" }))];
I["dz-media-animatique"] = () => [pl(MM.tri(11.8, 22, 4, 20)), pa(G.rect(2, 2.6, 7.6, 8.2, 1.2) + G.rect(2, 13.2, 7.6, 8.2, 1.2))];
I["dz-media-assembler"] = () => { // trois cases pâles qui convergent vers une bande pleine perforée
  let bande = G.rect(12, 5, 10, 14, 1.4);
  [13.6, 17.2].forEach(x => { bande = moins(bande, G.rect(x, 4, 1.8, 2.6), G.rect(x, 17.4, 1.8, 2.6)); });
  bande = moins(bande, G.rect(20.2, 4, 3, 2.6), G.rect(20.2, 17.4, 3, 2.6));
  return [pl(bande), pa(G.rect(2, 2.4, 6, 5, 1) + G.rect(3.6, 9.5, 6, 5, 1) + G.rect(2, 16.6, 6, 5, 1))];
};
I["dz-media-extraits"] = () => [pl(G.rect(2, 3, 5.4, 9, 1) + G.rect(9.3, 3, 5.4, 9, 1) + G.rect(16.6, 3, 5.4, 9, 1)), pa(G.rect(2, 15.6, 20, 5.4, 1.4))];
I["dz-media-rendre"] = () => {
  let bande = G.rect(2, 6.4, 12, 11.2, 1);
  [3.4, 7, 10.6].forEach(x => { bande = moins(bande, G.rect(x, 5.4, 1.8, 2.6), G.rect(x, 15.6, 1.8, 2.6)); });
  return [pl(MM.tri(11.6, 22, 2.6, 21.4)), pa(bande)];
};
I["dz-media-mouvements-camera"] = () => [pl(M.camera({ x: 3.4, y: 2, s: 0.82 })), pa(M.flecheCourbe({ cx: 12, cy: 2, r: 17.4, e: 2.4, a0: 122, a1: 62, hw: 6.4, hl: 4.4 }))];
I["dz-media-incrustation"] = I["dz-media-incrustation"];
I["dz-media-sous-titres"] = () => [pl(G.rect(5.4, 10.6, 13.2, 2.4, 1.2) + G.rect(7.8, 14.4, 8.4, 2.4, 1.2)), pa(G.rect(2, 3.6, 20, 16.8, 1.6))];
I["dz-media-prompt"] = () => [pl(M.curseurTexte({ cx: 12, y: 5.6, h: 9.4 })), pa(M.bulle({ x: 2, y: 2.2, w: 20, h: 15.6 }))];

// ═══════════════════════════════ Texte, polices ════════════════════════════════════════════════════════
I["dz-media-police"] = () => {
  const A = placer(M.lettreA(), { k: 0.7, dx: -3.6, dy: 2.4 });
  const a = moins(union(G.circle(18.4, 17.6, 3.6), G.rect(19.8, 11.6, 2.2, 9.6, 1.1)), G.circle(18.2, 17.6, 1.4));
  return [pl(A), pa(a)];
};

// ═══════════════════════════════ News, régions, planification ══════════════════════════════════════════
I["dz-media-article"] = () => [
  pl(G.rect(6.4, 6, 6.8, 2.6, 0.6) + G.rect(6.4, 10.2, 4.8, 8.4, 0.6) + G.rect(12.8, 10.2, 4.8, 2.2, 0.6) + G.rect(12.8, 13.3, 4.8, 2.2, 0.6) + G.rect(12.8, 16.4, 4.8, 2.2, 0.6)),
  pa(M.feuille({ x: 2.6, w: 18.8, h: 20.2 }))];
I["dz-media-flux-rss"] = () => { const c = [7.4, 16.6];
  return [pl(moins(G.rect(2.5, 2.5, 19, 19, 3.2), G.circle(...c, 2.2), arc(...c, 6.2, 2.2, -90, 0), arc(...c, 10.6, 2.2, -90, 0)))]; };
I["dz-media-badge-direct"] = () => [pl(G.circle(12, 12, 2.4)), pa(union(arc(12, 12, 5.2, 2.4, -40, 40), arc(12, 12, 5.2, 2.4, 140, 220), arc(12, 12, 9, 2.4, -40, 40), arc(12, 12, 9, 2.4, 140, 220)))];
I["dz-media-badge-prix"] = () => { // étiquette à œillet inclinée, pleine ; ficelle pâle
  const tag = placer(moins(polyR([[2.6, 12], [8.6, 5.4], [21.4, 5.4], [21.4, 18.6], [8.6, 18.6]], 1.4), G.circle(8, 12, 1.8)), { rot: -40, cx: 13, cy: 13.4 });
  return [pl(tag), pa(trait(lisse([[8.3, 15.5], [4.6, 12.6], [3.4, 7.4], [5.6, 3.2], [9.4, 3]], 12), 2.2))]; };
I["dz-media-sticker"] = () => { // pastille dont le coin bas-droit se soulève (rabat pâle, reflet du segment)
  const c = 12, r = 10, k = 32.5, seg = [], n = 40; // ligne de pli x + y = k
  const t = Math.acos((k - 2 * c) / (r * Math.SQRT2)); // demi-angle autour de 45°
  for (let i = 0; i <= n; i++) { const a = Math.PI / 4 - t + 2 * t * i / n; seg.push([c + r * Math.cos(a), c + r * Math.sin(a)]); }
  const rabat = polyR(seg.map(([x, y]) => [k - y, k - x]), 0);
  return [pa(rabat), pl(moins(G.circle(c, c, r), G.poly([[k, -5], [k + 30, -5], [k + 30, 30], [-5, 30], [-5, k + 5]])))];
};
I["dz-media-emoji"] = () => [pl(moins(G.circle(12, 12, 10), ellipse(8.6, 9.2, 1.5, 2.1), ellipse(15.4, 9.2, 1.5, 2.1), arc(12, 12, 5.6, 2.2, 28, 152)))];
I["dz-media-emoji-auto"] = () => { const c = [12, 9.2], R0 = 7.4;
  return [pl(moins(G.circle(...c, R0), ellipse(9.4, 7.4, 1.2, 1.7), ellipse(14.6, 7.4, 1.2, 1.7), arc(c[0], c[1], 4, 1.8, 30, 150))), pa(G.rect(2, 18.2, 20, 3.6, 1.2))]; };
I["dz-media-chaine-du-jour"] = () => { // soleil levant pâle au-dessus d'un lot de trois lignes pleines
  const rays = [-150, -120, -90, -60, -30].map(a => pill(...pt(12, 10.4, 7.6, a), ...pt(12, 10.4, 9.4, a), 2.2)).join("");
  return [pl(G.rect(2, 12.2, 20, 2.6, 1.3) + G.rect(5, 15.9, 14, 2.6, 1.3) + G.rect(8, 19.6, 8, 2.6, 1.3)), pa(union(`M6.6 10.4A5.4 5.4 0 0 1 17.4 10.4Z`, rays))]; };
I["dz-media-creneaux"] = () => {
  const sect = (a0, a1) => { const p = []; for (let a = a0; a <= a1 + 1e-6; a += 3) p.push(pt(12, 12, 10, a)); for (let a = a1; a >= a0 - 1e-6; a -= 3) p.push(pt(12, 12, 3.4, a)); return G.poly(p); };
  return [pl(sect(-90, -18) + sect(48, 120)), pa(G.circle(12, 12, 10))];
};
I["dz-media-duree"] = () => {
  const c = [12, 13.6];
  return [pl(union(G.ring(...c, 8.4, 6), pill(...c, ...pt(...c, 4.6, -50), 2.4))), pa(union(G.rect(9.6, 1.6, 4.8, 2.4, 1), G.rect(10.8, 3, 2.4, 2.4)) + pill(...pt(...c, 10.6, -45), ...pt(...c, 11.2, -45), 2.4))];
};
I["dz-media-routage"] = () => [ // entrée pâle qui se divise en deux sorties fléchées pleines (Y couché)
  pl(union(G.arrow(10.6, 12, 21.6, 4.4, 2.6, 8.4, 5.8), G.arrow(10.6, 12, 21.6, 19.6, 2.6, 8.4, 5.8), G.circle(10.6, 12, 1.3))), pa(G.rect(2, 10.7, 6.4, 2.6, 1.3))];
I["dz-media-graphe-depart"] = () => [pl(union(G.rect(5.5, 10, 4.4, 4.4, 0.8), G.rect(14.1, 6, 4.4, 4.4, 0.8), G.rect(14.1, 14, 4.4, 4.4, 0.8), G.rect(9, 11.2, 3.6, 2), G.rect(11, 7.2, 2, 10), G.rect(11, 7.2, 4, 2), G.rect(11, 15.2, 4, 2))), pa(G.rect(2, 2.4, 20, 19.6, 1.6))];
I["dz-media-pack-depart"] = () => { // caisse à lattes pleine, couvercle pâle soulevé (charnière à droite)
  const caisse = moins(G.rect(3, 11.2, 18, 10.8, 1.4), G.rect(8.6, 12.6, 1.6, 8), G.rect(13.8, 12.6, 1.6, 8));
  return [pl(caisse), pa(placer(G.rect(2.4, 6.4, 19.6, 3, 1), { rot: 12, cx: 21.6, cy: 9.2, dy: 1.2 }))];
};
I["dz-media-coffre"] = () => {
  const molette = moins(G.circle(10.4, 11.6, 4.6), G.rect(9.6, 6.4, 1.6, 3.4, 0.6));
  return [pl(molette), pl(G.rect(17.4, 8.6, 2.2, 6, 1.1)), pa(union(G.rect(2, 2.4, 20, 17.2, 1.8), G.rect(4, 18, 3.6, 3.8, 0.8), G.rect(16.4, 18, 3.6, 3.8, 0.8)))];
};
I["dz-media-fond-carte"] = () => [
  pl(G.poly([[2, 5.2], [7.6, 2.6], [7.6, 18.8], [2, 21.4]]) + G.poly([[16.4, 5.2], [22, 2.6], [22, 18.8], [16.4, 21.4]])),
  pa(G.poly([[9.2, 2.6], [14.8, 5.2], [14.8, 21.4], [9.2, 18.8]]))];
I["dz-media-feuille"] = () => [pl(M.grille({ x: 5.4, y: 6.4, w: 13.2, h: 11.2, n: 3, m: 2, g: 1.6, r: 0.5 })), pa(G.rect(2, 3, 20, 18, 1.4))];
I["dz-media-tuile-iso"] = () => [pl(MM.losange(9, 16, 7, 3.6, 0.8)), pa(G.ngon(15.6, 7.8, 6, 6, -90))];
I["dz-media-manuscrit"] = () => {
  const anneaux = [5.6, 10.2, 14.8, 19.4].map(y => G.rect(2, y - 1.1, 7.2, 2.2, 1.1)).join("");
  return [pl(anneaux), pl(G.rect(5, 4.4, 14.2, 17.6, 1.4)), pa(G.rect(9, 2, 13, 16.4, 1.4))];
};

// ═══════════════════════════════ écriture ═════════════════════════════════════════════════════════════
const filtre = process.argv[2] || "";
let n = 0;
for (const [cle, fn] of Object.entries(I)) {
  if (filtre && !cle.includes(filtre)) continue;
  fs.writeFileSync(path.join(OUT, cle + ".svg"), M.icone(fn()));
  n++;
}
console.log(n + " icônes écrites dans " + OUT);
