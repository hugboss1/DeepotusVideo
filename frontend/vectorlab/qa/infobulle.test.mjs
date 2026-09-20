// infobulle.test.mjs — mod-infobulle : la bulle d'information stylée qui
// remplace le title natif — position centrée sous l'ancre, bornée à la
// fenêtre, au-dessus si la place manque ; texte coupé en lignes lisibles.
import { bulle_position, texte_bulle } from "../js/mod-infobulle.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
const fen = { w: 1000, h: 600 };
{
  const p = bulle_position({ x: 400, y: 100, w: 40, h: 28 }, { w: 200, h: 50 }, fen, 8);
  ok("centrée sous l'ancre : x = centre − moitié, y = bas de l'ancre + marge, dessous", p.x === 320 && p.y === 136 && p.dessous === true, JSON.stringify(p));
  const g = bulle_position({ x: 10, y: 100, w: 40, h: 28 }, { w: 200, h: 50 }, fen, 8);
  ok("bornée à gauche : x ≥ marge", g.x === 8, JSON.stringify(g));
  const d = bulle_position({ x: 980, y: 100, w: 40, h: 28 }, { w: 200, h: 50 }, fen, 8);
  ok("bornée à droite : x + w ≤ fenêtre − marge", d.x === 1000 - 8 - 200, JSON.stringify(d));
  const b = bulle_position({ x: 400, y: 560, w: 40, h: 28 }, { w: 200, h: 50 }, fen, 8);
  ok("pas de place dessous : au-dessus de l'ancre", b.dessous === false && b.y === 560 - 8 - 50, JSON.stringify(b));
  const t = bulle_position({ x: 400, y: 4, w: 40, h: 4 }, { w: 200, h: 700 }, fen, 8);
  ok("bulle plus haute que la fenêtre : y borné à la marge", t.y === 8, JSON.stringify(t));
  ok("état vide : ancre sans taille → centrée sur le point", JSON.stringify(bulle_position({ x: 500, y: 300, w: 0, h: 0 }, { w: 100, h: 20 }, fen, 8)) === JSON.stringify({ x: 450, y: 308, dessous: true }));
  ok("texte : « — » et « · » deviennent des retours de ligne, espaces repliés", JSON.stringify(texte_bulle("Rayon d'angle — borné à min(L,H)/2 · 0 = vifs")) === JSON.stringify(["Rayon d'angle", "borné à min(L,H)/2", "0 = vifs"]));
  ok("texte : la parenthèse de raccourci finale reste sur la première ligne, vide → []", JSON.stringify(texte_bulle("Sélection (V)")) === JSON.stringify(["Sélection (V)"]) && texte_bulle("").length === 0 && texte_bulle(null).length === 0);
}
if (echecs.length) {
  console.error("ECHECS infobulle :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA infobulle : PASS (8 controles)");
