// Plateau hexagonal, lot 1, tâche 1 — le miroir JS de la géométrie de la grille
// (frontend/shared/dz-decoupe-hex-logique.js), mêmes cas et mêmes valeurs que
// backend/tests/test_cards_plateau_grille.py (qui compare aussi FORMATS_HEX au contrat).
// Lancer : node frontend/shared/qa/decoupe_hex_logique.test.mjs
import * as L from "../dz-decoupe-hex-logique.js";

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => {
  n++;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 400) : ""));
};
const proche = (a, b, e = 1e-6) => Math.abs(a - b) <= e;
const SQ3 = Math.sqrt(3);

// 1 pointe 6 x 4, 90 mm
{
  const g = L.grille("hex_p90", 6, 4);
  const h = 90 * 2 / SQ3;
  ok("1.1 24 centres", g.centres.length === 24);
  ok("1.2 largeur", proche(g.largeurMm, 6 * 90 + 45 + 6), g.largeurMm);
  ok("1.3 hauteur", proche(g.hauteurMm, h + 3 * 0.75 * h + 6), g.hauteurMm);
  const c0 = g.centres[0];
  ok("1.4 premier centre", c0.r === 1 && c0.c === 1 && proche(c0.x, 48) && proche(c0.y, 3 + h / 2), JSON.stringify(c0));
  const c6 = g.centres[6];
  ok("1.5 rangée paire décalée", c6.r === 2 && c6.c === 1 && proche(c6.x, 93), JSON.stringify(c6));
}

// 2 voisins à p
for (const fmt of ["hex_p50", "hex_f635"]) {
  const g = L.grille(fmt, 4, 3);
  const p = L.FORMATS_HEX[fmt].p;
  const pts = g.centres;
  let mini = Infinity;
  for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
    mini = Math.min(mini, Math.hypot(pts[i].x - pts[j].x, pts[i].y - pts[j].y));
  }
  ok(`2.1 ${fmt} distance mini = p`, proche(mini, p, 1e-9), mini);
  const ref = pts.find(q => q.r === 2 && q.c === 2);
  const nb = pts.filter(q => q !== ref && proche(Math.hypot(q.x - ref.x, q.y - ref.y), p, 1e-9));
  ok(`2.2 ${fmt} six voisins`, nb.length === 6, nb.length);
}

// 3 plat = transposée
{
  const a = L.grille("hex_p75", 3, 5), b = L.grille("hex_f75", 5, 3);
  ok("3.1 transposée", proche(a.largeurMm, b.hauteurMm) && proche(a.hauteurMm, b.largeurMm));
  const g = L.grille("hex_f50", 2, 2);
  const q = (r, c) => g.centres.find(z => z.r === r && z.c === c);
  ok("3.2 colonnes paires décalées", proche(q(1, 2).y - q(1, 1).y, 25));
  ok("3.3 premier centre plat", proche(q(1, 1).x, 3 + 50 * 2 / SQ3 / 2));
}

// 4 une rangée, fond perdu explicite
ok("4.1 une rangée", proche(L.grille("hex_p50", 3, 1).largeurMm, 3 * 50 + 6));
ok("4.2 fond perdu explicite", proche(L.grille("hex_p50", 1, 1, 0).largeurMm, 50));

// 5 bornes
for (const a of [["poker", 2, 2], ["hex_p50", 0, 2], ["hex_p50", 31, 1], ["hex_p50", 30, 17]]) {
  let leve = false;
  try { L.grille(...a); } catch (e) { leve = e instanceof Error; }
  ok("5.1 refus " + a.join("/"), leve);
}
ok("5.2 constantes", L.COTE_MAX === 30 && L.TUILES_MAX === 500 && L.PIXELS_MAX === 150000000);

// 6 cadrage couvrant
{
  const eq = (r, [x, y, w, h]) => proche(r.x, x) && proche(r.y, y) && proche(r.w, w) && proche(r.h, h);
  ok("6.1", eq(L.cadrageCouvrant(2000, 1000, 2, 1), [0, 0, 2000, 1000]));
  ok("6.2", eq(L.cadrageCouvrant(2000, 1000, 1, 1), [500, 0, 1000, 1000]));
  ok("6.3", eq(L.cadrageCouvrant(2000, 1000, 1, 1, 1, 0), [0, 0, 1000, 1000]));
  ok("6.4", eq(L.cadrageCouvrant(2000, 1000, 1, 1, 2, 1, 1), [1500, 500, 500, 500]));
  ok("6.5 zoom < 1 ramené à 1", JSON.stringify(L.cadrageCouvrant(2000, 1000, 1, 1, 0.2)) === JSON.stringify(L.cadrageCouvrant(2000, 1000, 1, 1)));
}

// 7 ppp
ok("7.1 ppp effectif", proche(L.pppEffectif(3000, 254), 300));

if (echecs.length) {
  console.error(`ÉCHEC ${echecs.length}/${n}\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log(`ok ${n}/${n}`);
