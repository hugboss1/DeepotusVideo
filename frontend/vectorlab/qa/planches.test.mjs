// planches.test.mjs — lot C : doc.planches (cadres nommés), commandes,
// guides d'aimantation, compilerSVG(doc, {cadre}) dont le viewBox EST la
// planche. État vide construit.
import { parserDoc, compilerSVG, op_planche_ajouter, op_planche_modifier,
         op_planche_supprimer, planches_guides, planche_de } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const base = () => ({ v: 1, nom: "P", taille: { w: 800, h: 600 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
    { id: "r1", type: "rect", x: 100, y: 100, w: 50, h: 50, style: { fond: "#0047AB" } }] }] });

{
  const d = base();
  ok("état vide : aucun guide", planches_guides(d).v.length === 0 && planches_guides(d).h.length === 0);
  ok("état vide : planche_de rend null", planche_de(d, "p1") === null);
  const id = op_planche_ajouter(d, { nom: "Plateau", x: 0, y: 0, w: 400, h: 300 });
  ok("ajouter → p1, planche stockée", id === "p1" && d.planches.length === 1 && d.planches[0].nom === "Plateau");
  const id2 = op_planche_ajouter(d, { x: 400, y: 0, w: 400, h: 600 });
  ok("second id p2, nom par défaut", id2 === "p2" && d.planches[1].nom === "Planche 2");
  op_planche_modifier(d, "p1", { nom: "Carte", w: 200 });
  ok("modifier fusionne", d.planches[0].nom === "Carte" && d.planches[0].w === 200 && d.planches[0].h === 300);
  const g = planches_guides(d);
  ok("guides : bords des planches, triés, uniques", JSON.stringify(g.v) === JSON.stringify([0, 200, 400, 800]) && JSON.stringify(g.h) === JSON.stringify([0, 300, 600]), JSON.stringify(g));
  ok("parserDoc accepte", (() => { try { parserDoc(d); return true; } catch { return false; } })());
  ok("les planches ne sont JAMAIS compilées", !compilerSVG(d).includes("planche"));
  const svg = compilerSVG(d, { cadre: planche_de(d, "p2") });
  ok("cadre : viewBox = la planche, width/height = sa taille", svg.includes('viewBox="400 0 400 600"') && svg.includes('width="400" height="600"'), svg.slice(0, 160));
  ok("cadre : le contenu entier reste (le viewBox rogne)", svg.includes('data-objet="r1"'));
  op_planche_supprimer(d, "p1");
  ok("supprimer", d.planches.length === 1 && d.planches[0].id === "p2");
  op_planche_supprimer(d, "p2");
  ok("plus de planche → doc.planches disparaît", d.planches === undefined);
  let refus = 0;
  for (const s of [{ x: 0, y: 0, w: 0, h: 10 }, { x: 0, y: 0, w: 10 }, "x"]) { try { op_planche_ajouter(base(), s); } catch { refus++; } }
  try { op_planche_modifier(base(), "p9", {}); } catch { refus++; }
  ok("refus : 3 specs + planche inconnue", refus === 4, String(refus));
  const m = base(); m.planches = [{ id: "p1", x: 0, y: 0, w: -5, h: 5 }];
  let refusDoc = false; try { parserDoc(m); } catch { refusDoc = true; }
  ok("parserDoc refuse une planche malformée", refusDoc);
}

if (echecs.length) {
  console.error("ECHECS planches :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA planches : PASS (15 controles)");
