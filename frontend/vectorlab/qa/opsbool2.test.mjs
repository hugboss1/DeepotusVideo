// opsbool2.test.mjs — mod-bool, lot B : les formes paramétriques s'aplatissent,
// le couteau coupe par une droite, la gomme retire un trait gonflé, le
// contour décale (dehors par union du trait, dedans par retrait), les ATOMES
// du Shape Builder et la commande du constructeur. Martinez vendorisé en vrai.
import { createRequire } from "node:module";
import { fournirMartinez, aplatir_objet, aire_de, op_couteau, op_gomme, op_contour,
         atomes, point_dans_multi, op_constructeur, aire_multi } from "../js/mod-bool.js";
import { forme_defaut } from "../js/mod-formes.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (a, b, tol) => Math.abs(a - b) <= tol;
const doc = (...objets) => ({ v: 1, taille: { w: 400, h: 400 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets }] });
const rect = (id, x, y, w, h) => ({ id, type: "rect", x, y, w, h, style: { fond: "#0047AB" } });
const objets = (d) => d.calques[0].objets;
const aireObj = (o) => Math.abs(aire_de(aplatir_objet(o)));

{
  const f = forme_defaut("polygone", 50, 50, 10); f.params.n = 4; f.id = "f";
  const an = aplatir_objet(f);
  ok("une forme s'aplatit : un anneau fermé de 5 points, aire 200 (carré de diagonale 20)", an.length === 1 && an[0].length === 5 && pres(Math.abs(aire_de(an)), 200, 1e-6), JSON.stringify(an));
}
/* ── couteau ── */
{
  const d = doc(rect("r", 0, 0, 100, 100));
  const ids = op_couteau(d, ["r"], [50, -10, 50, 110]);
  ok("couteau vertical : deux chemins de 5000, l'original disparaît", ids.length === 2 && objets(d).length === 2 && objets(d).every((o) => o.type === "path" && pres(aireObj(o), 5000, 1)), JSON.stringify(ids));
  ok("les morceaux gardent le style", objets(d).every((o) => o.style.fond === "#0047AB"));
  const e = doc(rect("r", 0, 0, 100, 100));
  let refus = 0; try { op_couteau(e, ["r"], [200, 0, 200, 100]); } catch (x) { refus += /coupe rien/.test(x.message) ? 1 : 0; }
  ok("une droite qui ne traverse rien : refus « ne coupe rien »", refus === 1 && objets(e).length === 1);
  const o = doc(rect("r", 0, 0, 100, 100));
  const ids2 = op_couteau(o, ["r"], [0, 0, 100, 100]);
  ok("couteau en diagonale : deux triangles", ids2.length === 2 && objets(o).every((p) => pres(aireObj(p), 5000, 1)));
}
/* ── gomme ── */
{
  const d = doc(rect("r", 0, 0, 100, 100));
  const ids = op_gomme(d, ["r"], "M -10 50 L 110 50", 10);
  const total = objets(d).reduce((s, o) => s + aireObj(o), 0);
  ok("gomme horizontale de 10 : deux morceaux, aire totale 9000 (±1 %)", ids.length === 2 && pres(total, 9000, 90), `${ids.length} / ${total}`);
  const e = doc(rect("r", 0, 0, 100, 100));
  const ids3 = op_gomme(e, ["r"], "M -10 -50 L 110 -50", 10);
  ok("un trait hors de la forme : rien n'est retiré, la forme reste (dite intacte)", ids3.length === 1 && pres(aireObj(objets(e)[0]), 10000, 1));
  const f = doc(rect("r", 0, 0, 100, 100));
  const ids4 = op_gomme(f, ["r"], "M 50 50 L 50 50", 300);
  ok("tout gommer : la forme disparaît, aucun id", ids4.length === 0 && objets(f).length === 0);
}
/* ── contour (décalage) ── */
{
  const d = doc(rect("r", 0, 0, 100, 100));
  const ids = op_contour(d, ["r"], 5);
  const n = objets(d).find((o) => o.id === ids[0]);
  // carré gonflé de 5 : 110² − coins arrondis (4 − π)·25 ≈ 12078
  ok("contour +5 : une COPIE décalée, l'original reste, aire ≈ 12078 (±1 %)", ids.length === 1 && objets(d).length === 2 && pres(aireObj(n), 12078, 121), aireObj(n));
  const e = doc(rect("r", 0, 0, 100, 100));
  const ids2 = op_contour(e, ["r"], -5);
  ok("contour −5 : aire 8100 (±1 %)", pres(aireObj(objets(e).find((o) => o.id === ids2[0])), 8100, 81));
  let refus = 0; try { op_contour(e, ["r"], 0); } catch { refus++; }
  try { op_contour(e, ["r"], -60); } catch (x) { refus += /vide/.test(x.message) ? 1 : 0; }
  ok("décalage nul refusé ; retrait qui vide la forme dit « vide »", refus === 2, String(refus));
}
/* ── atomes et constructeur ── */
{
  const A = [[[[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]]], B = [[[[50, 50], [150, 50], [150, 150], [50, 150], [50, 50]]]];
  const at = atomes([A, B]);
  const aires = at.map((m) => Math.round(aire_multi(m))).sort((a, b) => a - b);
  ok("deux carrés qui se chevauchent : 3 atomes (2500, 7500, 7500)", JSON.stringify(aires) === "[2500,7500,7500]", JSON.stringify(aires));
  ok("point_dans_multi : (25,25) dans A∖B seulement", at.filter((m) => point_dans_multi(m, 25, 25)).length === 1 && at.filter((m) => point_dans_multi(m, 75, 75)).length === 1 && at.filter((m) => point_dans_multi(m, 300, 300)).length === 0);
  ok("état vide : aucune forme → []", atomes([]).length === 0);
  const d = doc(rect("a", 0, 0, 100, 100), rect("b", 50, 50, 100, 100));
  const id = op_constructeur(d, ["a", "b"], [{ x: 25, y: 25 }, { x: 75, y: 75 }], "fusionner");
  ok("fusionner A∖B + A∩B → un chemin d'aire 10000, les originaux partent", objets(d).length === 1 && objets(d)[0].id === id && pres(aireObj(objets(d)[0]), 10000, 1), JSON.stringify(objets(d).map((o) => o.id)));
  const e = doc(rect("a", 0, 0, 100, 100), rect("b", 50, 50, 100, 100));
  op_constructeur(e, ["a", "b"], [{ x: 75, y: 75 }], "retirer");
  ok("retirer A∩B → le reste (15000) en un chemin", objets(e).length === 1 && pres(aireObj(objets(e)[0]), 15000, 1), aireObj(objets(e)[0]));
  let refus = 0; try { op_constructeur(e, [objets(e)[0].id], [{ x: 999, y: 999 }], "fusionner"); } catch { refus++; }
  ok("un clic hors de tout atome : refus", refus === 1);
}

if (echecs.length) {
  console.error("ECHECS opsbool2 :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA opsbool2 : PASS (16 controles)");
