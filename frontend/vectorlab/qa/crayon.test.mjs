// crayon.test.mjs — mod-crayon (lot B) : simplification RDP, lissage
// Catmull-Rom → Bézier cubiques, fermeture automatique. Module feuille.
import { simplifier, lisser_vers_d, est_ferme } from "../js/mod-crayon.js";
import { chemin_parser } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
{
  // 11 points presque alignés (bruit 0,2) → RDP tol 1 garde les deux bouts
  const pts = []; for (let i = 0; i <= 10; i++) pts.push([i * 10, (i % 2) * 0.2]);
  ok("RDP : une quasi-droite se réduit à 2 points", simplifier(pts, 1).length === 2);
  const coude = [[0, 0], [50, 0.1], [100, 0], [100, 50], [100, 100]];
  const s = simplifier(coude, 1);
  ok("RDP : le coude garde son sommet (3 points)", s.length === 3 && s[1][0] === 100 && s[1][1] === 0, JSON.stringify(s));
  ok("RDP : tolérance 0 → tout garder ; ≤ 2 points → inchangé", simplifier(coude, 0).length === 5 && simplifier([[0, 0]], 5).length === 1);
}
{
  ok("est_ferme : fin à 5 px du début, seuil 8", est_ferme([[0, 0], [50, 0], [50, 50], [3, 4]], 8) && !est_ferme([[0, 0], [50, 0], [50, 50], [30, 30]], 8) && !est_ferme([[0, 0], [1, 1]], 8));
}
{
  const pts = [[0, 0], [40, 30], [80, 0], [120, 30]];
  const d = lisser_vers_d(pts, { tol: 0.5, fermer: false });
  const segs = chemin_parser(d);
  ok("lissé : M puis des C (une cubique par intervalle), ouvert", segs[0].c === "M" && segs.slice(1).every((s) => s.c === "C") && segs.length === 4 && !d.includes("Z"), d);
  ok("la courbe passe par les points (ancres = points d'entrée)", segs.slice(1).every((s, i) => s.p[4] === pts[i + 1][0] && s.p[5] === pts[i + 1][1]), d);
  const carre = [[0, 0], [100, 0], [100, 100], [0, 100], [2, 3]];
  const df = lisser_vers_d(carre, { tol: 0.5, fermer: true });
  ok("fermé : le dernier point (proche du premier) est absorbé et le chemin se ferme par Z", df.endsWith("Z") && chemin_parser(df).filter((s) => s.c === "C").length === 4, df);
  let refus = 0; try { lisser_vers_d([[0, 0]], {}); } catch { refus++; }
  ok("moins de deux points → refus", refus === 1);
  const deux = lisser_vers_d([[0, 0], [10, 0]], {});
  ok("deux points → un segment droit (L)", /^M 0 0 L 10 0$/.test(deux), deux);
}

if (echecs.length) {
  console.error("ECHECS crayon :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA crayon : PASS (10 controles)");
