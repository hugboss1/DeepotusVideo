// noeuds2.test.mjs — mod-noeuds (lot B) : nœuds MULTIPLES (déplacer,
// aligner, transformer), diviser un segment, inverser, joindre, coins
// arrondis, sélection d'ancres au rectangle. Sur chemin_parser/serialiser.
import { op_noeuds_deplacer, op_noeuds_aligner, op_noeuds_transformer, op_noeud_inserer,
         op_chemin_inverser, op_chemins_joindre, op_coins_arrondir, ancres_dans_rect }
  from "../js/mod-noeuds.js";
import { chemin_parser, chemin_ancres } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const doc = (d, id = "p") => ({ v: 1, taille: { w: 400, h: 400 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false,
  objets: [{ id, type: "path", d, style: { fond: "#0047AB" } }] }] });
const chemin = (dc, id = "p") => dc.calques[0].objets.find((o) => o.id === id);
const ancres = (dc, id = "p") => chemin_ancres(chemin_parser(chemin(dc, id).d)).map((a) => [a.x, a.y]);
const CARRE = "M 0 0 L 100 0 L 100 100 L 0 100 Z";

{
  const d = doc(CARRE);
  op_noeuds_deplacer(d, "p", [1, 2], 10, 0);
  ok("déplacer deux ancres : les deux bougent, les autres non", JSON.stringify(ancres(d)) === "[[0,0],[110,0],[110,100],[0,100]]", JSON.stringify(ancres(d)));
  let refus = 0; try { op_noeuds_deplacer(d, "p", [9], 1, 1); } catch { refus++; }
  ok("ancre hors chemin refusée", refus === 1);
}
{
  const d = doc(CARRE);
  op_noeuds_aligner(d, "p", [0, 2], "centreH");
  ok("aligner centreH : les deux ancres à x = 50", ancres(d)[0][0] === 50 && ancres(d)[2][0] === 50, JSON.stringify(ancres(d)));
  const e = doc(CARRE);
  op_noeuds_aligner(e, "p", [1, 2], "haut");
  ok("aligner haut : y = min", ancres(e)[1][1] === 0 && ancres(e)[2][1] === 0);
  let refus = 0; try { op_noeuds_aligner(e, "p", [1], "haut"); } catch { refus++; }
  try { op_noeuds_aligner(e, "p", [1, 2], "diagonale"); } catch { refus++; }
  ok("aligner : une seule ancre ou mode inconnu refusés", refus === 2);
}
{
  const d = doc(CARRE);
  op_noeuds_transformer(d, "p", [0, 1, 2, 3], { x: 0, y: 0, w: 100, h: 100 }, { x: 0, y: 0, w: 50, h: 50 });
  ok("transformer : toutes les ancres à l'échelle 1/2", JSON.stringify(ancres(d)) === "[[0,0],[50,0],[50,50],[0,50]]", JSON.stringify(ancres(d)));
  const c = doc("M 0 0 C 0 50 100 50 100 0");
  op_noeuds_transformer(c, "p", [0, 1], { x: 0, y: 0, w: 100, h: 50 }, { x: 0, y: 0, w: 200, h: 50 });
  ok("transformer : les poignées suivent (C)", chemin(c).d === "M 0 0 C 0 50 200 50 200 0", chemin(c).d);
}
{
  const d = doc(CARRE);
  const i = op_noeud_inserer(d, "p", 1, 0.5);
  ok("diviser le segment 0→1 au milieu : ancre (50,0) insérée en 1, 5 ancres", i === 1 && ancres(d).length === 5 && JSON.stringify(ancres(d)[1]) === "[50,0]", JSON.stringify(ancres(d)));
  const c = doc("M 0 0 C 0 100 100 100 100 0");
  op_noeud_inserer(c, "p", 1, 0.5);
  const segs = chemin_parser(chemin(c).d);
  ok("diviser une cubique : deux C (de Casteljau), point milieu (50, 75)", segs.length === 3 && segs[1].c === "C" && segs[2].c === "C" && segs[1].p[4] === 50 && segs[1].p[5] === 75, chemin(c).d);
  let refus = 0; try { op_noeud_inserer(d, "p", 0, 0.5); } catch { refus++; }
  ok("diviser avant la première ancre : refusé", refus === 1);
}
{
  const d = doc("M 0 0 L 100 0 C 120 20 120 80 100 100");
  op_chemin_inverser(d, "p");
  ok("inverser : part de l'ancienne fin, poignées échangées", chemin(d).d === "M 100 100 C 120 80 120 20 100 0 L 0 0", chemin(d).d);
  const f = doc(CARRE);
  op_chemin_inverser(f, "p");
  ok("inverser un chemin fermé : reste fermé, 4 ancres", chemin(f).d.endsWith("Z") && ancres(f).length === 4 && JSON.stringify(ancres(f)[0]) === "[0,100]", chemin(f).d);
}
{
  const d = doc("M 0 0 L 10 0", "a");
  d.calques[0].objets.push({ id: "b", type: "path", d: "M 20 0 L 30 0", style: {} });
  const r = op_chemins_joindre(d, "a", "b");
  ok("joindre : B s'accroche à la fin de A, B disparaît", r === "a" && chemin(d, "a").d === "M 0 0 L 10 0 L 20 0 L 30 0" && d.calques[0].objets.length === 1, chemin(d, "a").d);
  const e = doc(CARRE, "a"); e.calques[0].objets.push({ id: "b", type: "path", d: "M 0 0 L 1 1", style: {} });
  let refus = 0; try { op_chemins_joindre(e, "a", "b"); } catch { refus++; }
  ok("joindre un chemin fermé : refusé", refus === 1);
}
{
  const d = doc(CARRE);
  const n = op_coins_arrondir(d, ["p"], 10);
  const segs = chemin_parser(chemin(d).d);
  ok("coins arrondis : 4 coins, 4 Q, fermé", n === 4 && segs.filter((s) => s.c === "Q").length === 4 && chemin(d).d.endsWith("Z"), chemin(d).d);
  ok("le premier point du contour est à 10 du coin (10, 0)", chemin(d).d.startsWith("M 10 0"), chemin(d).d);
  const o = doc("M 0 0 L 100 0 L 100 100");
  ok("chemin ouvert : un seul coin", op_coins_arrondir(o, ["p"], 10) === 1);
  let refus = 0; try { op_coins_arrondir(d, ["p"], 0); } catch { refus++; }
  ok("rayon nul refusé", refus === 1);
  const g = doc("M 0 0 L 100 0 L 100 100 L 0 100 Z");
  op_coins_arrondir(g, ["p"], 500);
  ok("rayon trop grand : borné à la demi-arête (pas de croisement)", chemin(g).d.startsWith("M 50 0"), chemin(g).d);
}
{
  const segs = chemin_parser(CARRE);
  ok("ancres dans le rectangle : [1]", JSON.stringify(ancres_dans_rect(segs, { x: 50, y: -10, w: 100, h: 60 })) === "[1]");
  ok("rectangle vide → []", ancres_dans_rect(segs, { x: 300, y: 300, w: 10, h: 10 }).length === 0);
}

if (echecs.length) {
  console.error("ECHECS noeuds2 :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA noeuds2 : PASS (21 controles)");
