// qa/deformer-m7.test.mjs — t256 (Photolab M7 PR 3, moteur photocraft 0.10) : Ctrl+T › Déformer. Maillage du moteur
// (edit.transform.warpGrid : (3c+1) × (3r+1) points, ancre tous les 3), gestes (une ancre emmène ses poignées), report
// d'une transformation libre, tracé, validation edit.transform.warp. Fonctions PURES ; formes relevées sur le vrai
// moteur (backend/tests/test_photolab_m7.py [7]).
import { readFileSync } from "node:fs";
import { GRILLES_DEFORMER, LIB_GRILLES, dimensionsMaillage, estAncre, poigneesDe, deplacerPointMaillage, maillageSurQuad,
  pointMaillageProche, commandeDeformation, traceMaillage, coins } from "../js/mod-transformer.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const proche = (a, b, e = 1e-6) => Math.abs(a - b) < e;

// maillage neutre « Par défaut » sur [0, 0, 200, 120] tel que le moteur le rend (16 points)
const neutre = (n, rect = [0, 0, 200, 120]) => {
  const k = 3 * n + 1, us = Array.from({ length: n + 1 }, (_, i) => i / n), points = [];
  for (let y = 0; y < k; y++) for (let x = 0; x < k; x++) points.push([rect[0] + (rect[2] - rect[0]) * x / (k - 1), rect[1] + (rect[3] - rect[1]) * y / (k - 1)]);
  return { style: "custom", bend: 0, hDistort: 0, vDistort: 0, vertical: false, bounds: [...rect], mesh: { us, vs: [...us], points } };
};
const W1 = neutre(1), W3 = neutre(3);

// 1. grilles offertes = liste fermée du pont
const py = readFileSync(new URL("../../../backend/app/services/photolab_registre.py", import.meta.url), "utf8");
check("1.1 grilles Par défaut / 3 / 4 / 5 = l'énumération du pont", eq(GRILLES_DEFORMER, ["default", "3", "4", "5"])
  && /\("edit\.transform\.warpGrid", "size"\): \{"type": "enum", "valeurs": \["default", "3", "4", "5"\]\}/.test(py));
check("1.2 un libellé par grille", GRILLES_DEFORMER.every((g) => /^photolab\.transformation\.grille_/.test(LIB_GRILLES[g])));

// 2. dimensions et ancres
check("2.1 Par défaut : 4 × 4 ; 3 × 3 : 10 × 10", eq(dimensionsMaillage(W1.mesh), { cols: 4, rows: 4 }) && eq(dimensionsMaillage(W3.mesh), { cols: 10, rows: 10 }));
check("2.2 ancres tous les 3 points (coins, et 33 en 3 × 3) ; poignées ailleurs",
  estAncre(0, 4) && estAncre(3, 4) && estAncre(12, 4) && estAncre(15, 4) && !estAncre(1, 4) && !estAncre(5, 4)
  && estAncre(33, 10) && !estAncre(34, 10) && W3.mesh.points.filter((_, i) => estAncre(i, 10)).length === 16);
check("2.3 poignées d'une ancre : voisines dans la grille, bornées aux bords", eq(poigneesDe(0, 4, 4), [1, 4]) && eq(poigneesDe(33, 10, 10).sort((a, b) => a - b), [23, 32, 34, 43]));

// 3. glisser
let w = deplacerPointMaillage(W1, 0, 5, -3);
check("3.1 glisser une ancre : elle et ses poignées bougent, le reste non ; l'original intact",
  eq(w.mesh.points[0], [5, -3]) && eq(w.mesh.points[1], [W1.mesh.points[1][0] + 5, -3]) && eq(w.mesh.points[4], [5, W1.mesh.points[4][1] - 3])
  && eq(w.mesh.points[5], W1.mesh.points[5]) && eq(W1.mesh.points[0], [0, 0]));
w = deplacerPointMaillage(W1, 5, 10, 10);
check("3.2 glisser une poignée : elle seule", w.mesh.points.filter((p, i) => !eq(p, W1.mesh.points[i])).length === 1);

// 4. report d'une transformation libre
const rect = [0, 0, 200, 120];
const deplace = coins(rect).map(([x, y]) => [x + 10, y + 20]);
w = maillageSurQuad(W1, rect, deplace);
check("4.1 quadrilatère décalé : chaque point du maillage suit (+10, +20)", w.mesh.points.every((p, i) => proche(p[0], W1.mesh.points[i][0] + 10) && proche(p[1], W1.mesh.points[i][1] + 20)));
check("4.2 quadrilatère identique : maillage inchangé", maillageSurQuad(W3, rect, coins(rect)).mesh.points.every((p, i) => proche(p[0], W3.mesh.points[i][0]) && proche(p[1], W3.mesh.points[i][1])));

// 5. prise à l'écran (échelle 2)
const ecran = (x, y) => ({ x: x * 2, y: y * 2 });
check("5.1 point le plus proche dans la tolérance ; rien loin de tout", pointMaillageProche(W1, { x: 3, y: 2 }, ecran) === 0 && pointMaillageProche(W1, { x: 200, y: 120 }, ecran) === -1);
check("5.2 à égalité, l'ancre l'emporte sur la poignée", pointMaillageProche({ ...W1, mesh: { ...W1.mesh, points: W1.mesh.points.map((p, i) => (i === 1 ? [0, 0] : p)) } }, { x: 0, y: 0 }, ecran) === 0);

// 6. validation
check("6.1 rien de modifié : aucune commande", commandeDeformation(W1, false, 3) === null && commandeDeformation(null, true, 3) === null);
const c = commandeDeformation(deplacerPointMaillage(W1, 5, 1 / 3, 0), true, 3, "nearest");
check("6.2 edit.transform.warp {layer, warp (arrondi au millième), interpolation}", c.command === "edit.transform.warp" && c.params.layer === 3
  && c.params.interpolation === "nearest" && c.params.warp.mesh.points[5][0] === Math.round((W1.mesh.points[5][0] + 1 / 3) * 1000) / 1000
  && c.params.warp.bounds.length === 4);
check("6.3 interpolation inconnue : bicubique", commandeDeformation(W1, true, 3, "zorg").params.interpolation === "bicubic");

// 7. tracé
const t = traceMaillage(W3, ecran);
check("7.1 3 × 3 : 4 lignes + 4 colonnes d'ancres, chacune en 3 segments de Bézier", t.lignes.length === 8 && t.lignes.every((d) => (d.match(/C/g) || []).length === 3));
check("7.2 bras ancre–poignée et 100 points dont 16 ancres", t.points.length === 100 && t.points.filter((p) => p.ancre).length === 16 && t.bras.length > 0);

console.log(`deformer-m7 : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
