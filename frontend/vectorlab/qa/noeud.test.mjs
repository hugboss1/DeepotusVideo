// noeud.test.mjs — mod-noeud : l'outil Nœud de classe Affinity — segment le
// plus proche d'un point, déformation d'un segment au glisser, poignées
// (lisse / libre), suppression lisse, point sur un segment. Feuille.
import { segment_proche, segment_tirer, poignee_deplacer, noeud_supprimer_lisse, point_segment } from "../js/mod-noeud.js";
import { chemin_parser, chemin_serialiser, chemin_ancres } from "../js/mod-doc.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 250) : "")); };
const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
const P = (d) => chemin_parser(d), S = (s) => chemin_serialiser(s);
{
  const droit = P("M 0 0 L 100 0 L 100 100");
  const sp = segment_proche(droit, [50, 3], 5);
  ok("segment_proche : la droite 0→100 à t 0,5, ancre de fin 1, distance 3", sp && sp.k === 1 && sp.i === 1 && pres(sp.t, 0.5, 0.03) && pres(sp.dist, 3, 0.2), JSON.stringify(sp));
  ok("segment_proche : trop loin → null ; segs vides → null", segment_proche(droit, [50, 50], 5) === null && segment_proche([], [0, 0], 5) === null);
  const ferme = P("M 0 0 L 100 0 L 100 100 Z");
  const spz = segment_proche(ferme, [50, 52], 5);
  ok("segment_proche : le Z compte comme la droite de retour (100,100 → 0,0)", spz && spz.k === 3 && spz.i === 0, JSON.stringify(spz));
  ok("point_segment : milieu d'une droite, point d'une courbe", point_segment(droit, 1, 0.5).join() === "50,0" && pres(point_segment(P("M 0 0 C 0 100 100 100 100 0"), 1, 0.5)[1], 75));
  const tire = segment_tirer(droit, 1, 0.5, 0, 40);
  ok("segment_tirer : une droite devient un C qui PASSE par le point tiré (extrémités fixes)", tire[1].c === "C" && pres(point_segment(tire, 1, 0.5)[1], 40) && tire[1].p[4] === 100 && tire[1].p[5] === 0 && tire[2].c === "L", S(tire));
  const courbe = P("M 0 0 C 30 0 70 0 100 0");
  const tire2 = segment_tirer(courbe, 1, 0.25, 0, 20);
  ok("segment_tirer : une courbe passe par le point tiré à t 0,25 ; l'original intact", pres(point_segment(tire2, 1, 0.25)[1], 20) && courbe[1].p[1] === 0, S(tire2));
  ok("segment_tirer : index hors chemin ou Z → inchangé (même d)", S(segment_tirer(droit, 9, 0.5, 1, 1)) === S(droit) && S(segment_tirer(ferme, 3, 0.5, 1, 1)) === S(ferme));
  const lisse = P("M 0 0 C 10 -10 40 -10 50 0 C 60 10 90 10 100 0");
  const pd = poignee_deplacer(lisse, 1, "sortante", [50, 30]);
  const a1 = chemin_ancres(pd)[1];
  ok("poignee_deplacer lisse : la sortante suit, l'entrante s'aligne à l'opposé en gardant sa longueur (≈ 14,1)", a1.sortante.x === 50 && a1.sortante.y === 30 && pres(a1.entrante.x, 50) && pres(a1.entrante.y, -14.14, 0.05), JSON.stringify(a1));
  const pl = poignee_deplacer(lisse, 1, "sortante", [50, 30], { mode: "libre" });
  ok("poignee_deplacer libre : seule la sortante bouge", chemin_ancres(pl)[1].entrante.x === 40 && chemin_ancres(pl)[1].entrante.y === -10 && chemin_ancres(pl)[1].sortante.y === 30);
  const pe = poignee_deplacer(lisse, 1, "entrante", [20, 0]);
  ok("poignee_deplacer entrante lisse : la sortante s'aligne (longueur 14,1 gardée)", chemin_ancres(pe)[1].entrante.x === 20 && pres(chemin_ancres(pe)[1].sortante.x, 64.14, 0.05) && pres(chemin_ancres(pe)[1].sortante.y, 0, 0.05));
  ok("poignee_deplacer : ancre sans cette poignée ou index hors chemin → inchangé", S(poignee_deplacer(droit, 1, "entrante", [1, 1])) === S(droit) && S(poignee_deplacer(lisse, 9, "sortante", [1, 1])) === S(lisse));
  const sup = noeud_supprimer_lisse(lisse, 1);
  ok("noeud_supprimer_lisse : un seul C entre les voisins avec leurs tangentes", sup.length === 2 && sup[1].c === "C" && sup[1].p.join() === "10,-10,90,10,100,0", S(sup));
  ok("noeud_supprimer_lisse : ancre d'extrémité → segment retiré ; 2 ancres → inchangé", chemin_ancres(noeud_supprimer_lisse(lisse, 2)).length === 2 && S(noeud_supprimer_lisse(P("M 0 0 L 5 5"), 0)) === "M 0 0 L 5 5");
  ok("noeud_supprimer_lisse sur un chemin de droites : reste une droite entre les voisins", S(noeud_supprimer_lisse(droit, 1)) === "M 0 0 L 100 100");
}
if (echecs.length) { console.error("ECHECS noeud :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA noeud : PASS (14 controles)");
