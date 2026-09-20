// reperes.test.mjs — doc.reperes {fondPerdu:[ox,oy], zoneSure:[ox,oy]} :
// validation, rectangles dérivés, guides d'aimantation, commande op_reperes.
// L'état VIDE est construit d'abord : sans repères, rects nuls et guides vides.
import { parserDoc, compilerSVG, op_reperes, reperes_rects, reperes_guides }
  from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const base = () => ({ v: 1, nom: "R", taille: { w: 400, h: 300 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [] }] });

{
  const d = base();
  const r = reperes_rects(d);
  ok("état vide : deux rects nuls", r.fondPerdu === null && r.zoneSure === null, JSON.stringify(r));
  const g = reperes_guides(d);
  ok("état vide : guides vides", g.v.length === 0 && g.h.length === 0);
}
{
  const d = base();
  op_reperes(d, { fondPerdu: [12, 12], zoneSure: [30, 25] });
  ok("op_reperes pose les deux", JSON.stringify(d.reperes)
     === JSON.stringify({ fondPerdu: [12, 12], zoneSure: [30, 25] }), JSON.stringify(d.reperes));
  const r = reperes_rects(d);
  ok("rect fond perdu = ligne de coupe", JSON.stringify(r.fondPerdu)
     === JSON.stringify({ x: 12, y: 12, w: 376, h: 276 }), JSON.stringify(r));
  ok("rect zone sûre", JSON.stringify(r.zoneSure)
     === JSON.stringify({ x: 30, y: 25, w: 340, h: 250 }));
  const g = reperes_guides(d);
  ok("guides : 4 verticaux, 4 horizontaux, triés",
     JSON.stringify(g.v) === JSON.stringify([12, 30, 370, 388])
     && JSON.stringify(g.h) === JSON.stringify([12, 25, 275, 288]), JSON.stringify(g));
  ok("parserDoc accepte", (() => { try { parserDoc(d); return true; } catch { return false; } })());
  ok("les repères ne sont JAMAIS compilés", !compilerSVG(d).includes("repere")
     && !compilerSVG(d).includes('x="12" y="12" width="376"'));
  // un nombre = retrait uniforme
  op_reperes(d, { zoneSure: 40 });
  ok("un nombre pose [n,n]", JSON.stringify(d.reperes.zoneSure) === "[40,40]");
  // null retire la clé ; la dernière clé retirée retire doc.reperes
  op_reperes(d, { zoneSure: null });
  ok("null retire une clé", d.reperes.zoneSure === undefined && d.reperes.fondPerdu);
  op_reperes(d, { fondPerdu: null });
  ok("plus rien → doc.reperes disparaît", d.reperes === undefined);
}
{
  let refus = 0;
  for (const p of [{ fondPerdu: [-1, 0] }, { fondPerdu: [300, 0] },   // ≥ W/2
                   { zoneSure: "x" }, { inconnu: 3 }, { fondPerdu: [1] }]) {
    try { op_reperes(base(), p); } catch { refus++; }
  }
  ok("op_reperes refuse 5 patchs invalides", refus === 5, String(refus));
  let refusDoc = 0;
  for (const r of [{ fondPerdu: [200, 0] }, { zoneSure: 5 }, [1, 2], { bidon: [1, 1] }]) {
    const d = base(); d.reperes = r;
    try { parserDoc(d); } catch { refusDoc++; }
  }
  ok("parserDoc refuse 4 reperes malformés", refusDoc === 4, String(refusDoc));
}

if (echecs.length) {
  console.error("ECHECS reperes :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA reperes : PASS (13 controles)");
