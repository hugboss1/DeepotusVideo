// aimant_objets.test.mjs — l'aimantation aux OBJETS (lot C) : une boîte en
// mouvement s'aligne sur les bords et les centres des voisins, et sur les
// écarts réguliers ; l'état vide (aucun voisin) ne bouge rien.
import { aimant_objets, aimant_ecarts, aimant_fusion } from "../js/mod-aimant.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const B = (x, y, w, h) => ({ x, y, w, h });

{
  const r = aimant_objets(B(10.4, 20, 30, 30), [], 5);
  ok("état vide : dx=dy=0, aucune ligne", r.dx === 0 && r.dy === 0 && r.lignes.length === 0);
}
{
  const cands = [B(100, 100, 50, 50)];
  let r = aimant_objets(B(103, 300, 20, 20), cands, 5);
  ok("gauche→gauche : dx=-3, ligne v à 100", r.dx === -3 && r.lignes.some((l) => l.axe === "v" && l.pos === 100), JSON.stringify(r));
  r = aimant_objets(B(126, 300, 20, 20), cands, 5);
  ok("droite→droite : 146→150, dx=4", r.dx === 4, JSON.stringify(r));
  r = aimant_objets(B(113, 300, 20, 20), cands, 5);
  ok("centre→centre : 123→125, dx=2", r.dx === 2, JSON.stringify(r));
  r = aimant_objets(B(152, 300, 20, 20), cands, 5);
  ok("gauche→droite du voisin : dx=-2", r.dx === -2, JSON.stringify(r));
  r = aimant_objets(B(300, 97, 20, 20), cands, 5);
  ok("haut→haut : dy=3, ligne h à 100", r.dy === 3 && r.lignes.some((l) => l.axe === "h" && l.pos === 100), JSON.stringify(r));
  r = aimant_objets(B(300, 300, 20, 20), cands, 5);
  ok("hors tolérance : rien", r.dx === 0 && r.dy === 0 && r.lignes.length === 0);
  r = aimant_objets(B(104, 300, 20, 20), [B(100, 0, 10, 10), B(106, 0, 10, 10)], 5);
  ok("le candidat le plus proche gagne (106)", r.dx === 2, JSON.stringify(r));
}
/* ── écarts : A[0..50] gap 20 B[70..120] → C se pose à 140 ── */
{
  const cands = [B(0, 0, 50, 50), B(70, 0, 50, 50)];
  let r = aimant_ecarts(B(137, 0, 30, 30), cands, 5);
  ok("écart régulier après B : x→140, dx=3, ligne écart", r.dx === 3 && r.lignes.some((l) => l.type === "ecart"), JSON.stringify(r));
  r = aimant_ecarts(B(-52, 0, 30, 30), cands, 5);
  ok("écart régulier avant A : droite à -20 → x=-50, dx=2", r.dx === 2, JSON.stringify(r));
  r = aimant_ecarts(B(400, 0, 30, 30), cands, 5);
  ok("écart : hors tolérance → rien", r.dx === 0 && r.lignes.length === 0);
  ok("écart : moins de deux voisins → rien", aimant_ecarts(B(137, 0, 30, 30), [cands[0]], 5).dx === 0);
}
{
  const f = aimant_fusion([{ dx: 0, dy: 3, lignes: [{ axe: "h", pos: 1 }] }, { dx: 2, dy: 0, lignes: [{ axe: "v", pos: 2 }] }]);
  ok("fusion : le premier résultat non nul par axe, lignes concaténées", f.dx === 2 && f.dy === 3 && f.lignes.length === 2, JSON.stringify(f));
}

if (echecs.length) {
  console.error("ECHECS aimant_objets :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA aimant_objets : PASS (13 controles)");
