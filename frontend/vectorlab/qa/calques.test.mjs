// calques.test.mjs — opérations de calques (T1.4) : ajouter, renommer,
// réordonner, visibilité, verrou, supprimer (jamais le dernier).
import { op_calque_ajouter, op_calque_renommer, op_calque_reordonner,
         op_calque_visible, op_calque_verrou, op_calque_supprimer }
  from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 140) : ""));
};

const banc = () => ({
  v: 1, nom: "Banc", taille: { w: 100, h: 100 },
  calques: [
    { id: "c1", nom: "fond", visible: true, verrou: false, objets: [
      { id: "o1", type: "rect", x: 0, y: 0, w: 1, h: 1, style: {} }] },
    { id: "c2", nom: "verre", visible: true, verrou: false, objets: [] },
  ],
});
const ids = (d) => d.calques.map((c) => c.id).join(",");

{
  const d = banc();
  const id = op_calque_ajouter(d, "plombs");
  ok("ajout en fin (peint au-dessus), id unique",
     d.calques[2].id === id && id !== "c1" && id !== "c2"
     && d.calques[2].nom === "plombs" && d.calques[2].visible === true
     && d.calques[2].verrou === false && d.calques[2].objets.length === 0,
     ids(d));
}
{
  const d = banc();
  op_calque_renommer(d, "c1", "arrière-plan");
  ok("renommage", d.calques[0].nom === "arrière-plan");
}
{
  const d = banc();
  op_calque_ajouter(d, "trois");           // c1, c2, c3
  op_calque_reordonner(d, "c1", 2);        // c1 tout en haut de la pile
  ok("réordonner c1 → index 2", ids(d) === "c2,c3,c1", ids(d));
  op_calque_reordonner(d, "c1", 0);
  ok("réordonner c1 → index 0", ids(d) === "c1,c2,c3", ids(d));
}
{
  const d = banc();
  op_calque_visible(d, "c1", false);
  op_calque_verrou(d, "c2", true);
  ok("visibilité et verrou posés",
     d.calques[0].visible === false && d.calques[1].verrou === true);
}
{
  const d = banc();
  op_calque_supprimer(d, "c1");
  ok("suppression du calque et de ses objets",
     ids(d) === "c2" && !JSON.stringify(d).includes('"o1"'), ids(d));
  let refus = false;
  try { op_calque_supprimer(d, "c2"); } catch { refus = true; }
  ok("jamais le dernier calque", refus && d.calques.length === 1);
}
{
  const d = banc();
  let refus = 0;
  try { op_calque_renommer(d, "cX", "x"); } catch { refus++; }
  try { op_calque_reordonner(d, "cX", 0); } catch { refus++; }
  ok("calque inconnu → refus", refus === 2, String(refus));
}

if (echecs.length) {
  console.error("ECHECS calques :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA calques : PASS (8 controles)");
