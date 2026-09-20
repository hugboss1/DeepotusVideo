// plume.test.mjs — mod-plume : la Plume de classe Affinity — état de tracé
// pur et ses transitions (nœud vif / lisse, droite, retirer, finir, fermer),
// élastique courbe, contrainte à 45°, lissage Catmull-Rom (mode Intelligent),
// ouvrir / lisser / fractionner un chemin, prolongation depuis une
// extrémité, types d'ancres. Feuille.
import { trace_debut, trace_ajouter, trace_poignee, trace_retirer, trace_finir, elastique, contraindre_angle, lisser_catmull, chemin_ouvrir, chemin_lisser, chemin_fractionner, trace_depuis_chemin, extremite_proche, types_ancres } from "../js/mod-plume.js";
import { chemin_parser } from "../js/mod-doc.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 250) : "")); };
const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
{
  let t = trace_debut([10, 10]);
  ok("début : un M, une ancre, pas de sortante", t.segs.length === 1 && t.segs[0].c === "M" && t.ancres.length === 1 && t.sortante === null);
  t = trace_ajouter(t, [50, 10]);
  ok("ajouter sans poignée : un L (nœud vif)", t.segs[1].c === "L" && t.ancres.length === 2);
  t = trace_poignee(t, [70, 30]);
  ok("glisser depuis le nœud : le L devient C avec poignée entrante miroir, la sortante est mémorisée", t.segs[1].c === "C" && t.segs[1].p[2] === 30 && t.segs[1].p[3] === -10 && t.sortante && t.sortante[0] === 70 && t.sortante[1] === 30, JSON.stringify(t.segs[1]));
  t = trace_ajouter(t, [90, 60]);
  ok("nœud suivant après une sortante : un C qui part de la sortante", t.segs[2].c === "C" && t.segs[2].p[0] === 70 && t.segs[2].p[1] === 30 && t.segs[2].p[4] === 90 && t.sortante === null);
  const td = trace_ajouter(t, [120, 60], { droite: true });
  ok("clic droit : un L même après une courbe (le nœud précédent garde sa tangente)", td.segs[3].c === "L");
  const tr = trace_retirer(t);
  ok("retirer : le dernier nœud s'en va, l'état d'origine intact ; retirer le seul nœud → null", tr.ancres.length === 2 && tr.segs.length === 2 && t.ancres.length === 3 && trace_retirer(trace_debut([0, 0])) === null);
  ok("finir : d canonique ; fermer ajoute Z ; un seul nœud → null", trace_finir(t).startsWith("M 10 10") && !trace_finir(t).includes("Z") && trace_finir(t, { fermer: true }).endsWith("Z") && trace_finir(trace_debut([1, 1])) === null);
  ok("élastique : droite quand le dernier nœud n'a pas de sortante, courbe C quand il en a une", elastique(t, [100, 100]).startsWith("M 90 60 L 100 100") && elastique(trace_poignee(trace_ajouter(trace_debut([0, 0]), [10, 0]), [20, 5]), [30, 30]).includes("C 20 5"));
  ok("élastique : trace nulle → chaîne vide", elastique(null, [1, 1]) === "");
  const c = contraindre_angle([0, 0], [10, 3]);
  ok("contraindre_angle : 45° — (10,3) → (10,0), (10,9) → diagonale, même point → même point", c[0] === 10 && c[1] === 0 && pres(contraindre_angle([0, 0], [10, 9])[0], contraindre_angle([0, 0], [10, 9])[1]) && contraindre_angle([5, 5], [5, 5]).join() === "5,5");
  const sm = lisser_catmull([[0, 0], [10, 10], [20, 0], [30, 10]]);
  ok("lisser_catmull : M puis des C (n − 1), les nœuds sont conservés, poignées tangentes", sm.length === 4 && sm[0].c === "M" && sm.slice(1).every((s) => s.c === "C") && sm[1].p[4] === 10 && sm[1].p[5] === 10 && sm[3].p[4] === 30, JSON.stringify(sm));
  ok("lisser_catmull : fermé → un C de retour puis Z ; moins de 2 points → []", lisser_catmull([[0, 0], [10, 0], [10, 10]], true).some((s) => s.c === "Z") && lisser_catmull([[0, 0], [10, 0], [10, 10]], true).filter((s) => s.c === "C").length === 3 && lisser_catmull([[1, 1]]).length === 0);
  ok("chemin_ouvrir : retire Z ; déjà ouvert → inchangé", chemin_ouvrir("M 0 0 L 10 0 L 10 10 Z") === "M 0 0 L 10 0 L 10 10" && chemin_ouvrir("M 0 0 L 10 0") === "M 0 0 L 10 0");
  const li = chemin_lisser("M 0 0 L 10 10 L 20 0 L 30 10");
  ok("chemin_lisser : toutes les ancres deviennent lisses (des C), positions conservées", chemin_parser(li).filter((s) => s.c === "C").length === 3 && li.startsWith("M 0 0") && li.includes("30 10"));
  const fr = chemin_fractionner("M 0 0 L 10 0 L 20 0 L 30 0", 2);
  ok("chemin_fractionner : ouvert à l'ancre 2 → deux chemins qui partagent l'ancre", fr.length === 2 && fr[0] === "M 0 0 L 10 0 L 20 0" && fr[1] === "M 20 0 L 30 0");
  ok("chemin_fractionner : fermé → un seul chemin ouvert à l'ancre ; ancre d'extrémité d'un ouvert → inchangé", chemin_fractionner("M 0 0 L 10 0 L 10 10 Z", 1).length === 1 && chemin_fractionner("M 0 0 L 10 0 L 10 10 Z", 1)[0].startsWith("M 10 0") && !chemin_fractionner("M 0 0 L 10 0 L 10 10 Z", 1)[0].includes("Z") && chemin_fractionner("M 0 0 L 10 0", 0).length === 1);
  const tc = trace_depuis_chemin("M 0 0 C 5 5 15 5 20 0 L 30 0");
  ok("trace_depuis_chemin : les segs et les ancres du chemin, sortante nulle ; fermé → null", tc.ancres.length === 3 && tc.segs.length === 3 && tc.sortante === null && trace_depuis_chemin("M 0 0 L 1 0 Z") === null);
  ok("extremite_proche : fin, début, ni l'un ni l'autre, fermé → null", extremite_proche("M 0 0 L 10 0", [10.5, 0.2], 1) === "fin" && extremite_proche("M 0 0 L 10 0", [0.3, 0], 1) === "debut" && extremite_proche("M 0 0 L 10 0", [5, 0], 1) === null && extremite_proche("M 0 0 L 10 0 Z", [0, 0], 1) === null);
  ok("types_ancres : vif / lisse par ancre", types_ancres("M 0 0 L 10 0 C 12 0 20 5 20 10").join() === "vif,vif,lisse" && types_ancres("M 0 0 C 0 5 5 10 10 10").join() === "lisse,lisse" && types_ancres("").length === 0);
}
if (echecs.length) { console.error("ECHECS plume :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA plume : PASS (19 controles)");
