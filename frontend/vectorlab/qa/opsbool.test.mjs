// opsbool.test.mjs — union/soustraction/intersection (T3.3) et la
// division-métier (T3.4) : le résultat remplace les opérandes à
// l'emplacement du plus BAS avec son style ; la division garde les plombs
// et remplace la plaque par ses fragments (compte EXACT, trous en
// sous-chemins). Martinez injecté par le résolveur.
import { createRequire } from "node:module";
import { fournirMartinez, op_booleen, op_division, aplatir_objet, aire_de }
  from "../js/mod-bool.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (nom, obtenu, attendu, pct = 0.5) => {
  const marge = Math.abs(attendu) * pct / 100;
  ok(nom, Math.abs(obtenu - attendu) <= marge,
     `${obtenu} attendu ${attendu} ±${marge.toFixed(1)}`);
};
const R = (id, x, y, w, h, style) => ({ id, type: "rect", x, y, w, h,
  style: style || { fond: "#9DB4D6" } });
const banc = () => ({
  v: 1, nom: "B", taille: { w: 300, h: 200 },
  calques: [{ id: "c1", nom: "s", visible: true, verrou: false, objets: [
    { id: "temoin", type: "rect", x: 250, y: 150, w: 10, h: 10, style: {} },
    R("ra", 0, 0, 100, 100, { fond: "#0047AB", epaisseur: 2 }),
    R("rb", 50, 0, 100, 100),
  ] }],
});
const aireDoc = (doc, id) => {
  const o = doc.calques[0].objets.find((x) => x.id === id);
  return aire_de(aplatir_objet(o));
};

// union : un path au calque+index du plus bas, style du bas, aire exacte
{
  const d = banc();
  const id = op_booleen(d, ["ra", "rb"], "union");
  const objets = d.calques[0].objets;
  ok("remplace les opérandes à l'index du bas",
     objets.length === 2 && objets[1].id === id && objets[1].type === "path",
     objets.map((o) => o.id).join(","));
  ok("style du plus bas conservé", objets[1].style.fond === "#0047AB");
  pres("aire union", aireDoc(d, id), 15000, 0.01);
}
// intersection et soustraction
{
  const d = banc();
  const id = op_booleen(d, ["ra", "rb"], "intersection");
  pres("aire intersection", aireDoc(d, id), 5000, 0.01);
}
{
  const d = banc();
  const id = op_booleen(d, ["ra", "rb"], "soustraction");
  pres("aire soustraction", aireDoc(d, id), 5000, 0.01);
  const xs = aplatir_objet(d.calques[0].objets[1]).flat().map((p) => p[0]);
  ok("la soustraction garde le côté du bas (x ≤ 50)",
     Math.max(...xs) <= 50.01, String(Math.max(...xs)));
}

// refus : <2 objets ; texte ; résultat vide SANS mutation
{
  const d = banc();
  let refus = 0;
  try { op_booleen(d, ["ra"], "union"); } catch { refus++; }
  d.calques[0].objets.push({ id: "tx", type: "texte", x: 0, y: 0,
                             contenu: "x", style: {} });
  try { op_booleen(d, ["ra", "tx"], "union"); } catch { refus++; }
  d.calques[0].objets.push(R("loin", 200, 150, 20, 20));
  const avant = JSON.stringify(d);
  try { op_booleen(d, ["ra", "loin"], "intersection"); } catch { refus++; }
  ok("refus <2 / texte / intersection vide", refus === 3, String(refus));
  ok("le refus n'a RIEN muté", JSON.stringify(d) === avant);
}

// division-métier : plaque + plomb TRACÉ (fond none, contour épais)
{
  const d = banc();
  d.calques[0].objets = [
    R("plaque", 0, 0, 100, 100, { fond: "#DAA520" }),
    { id: "plomb", type: "path", d: "M 50 -10 L 50 110",
      style: { fond: "none", contour: "#1F1512", epaisseur: 10 } },
  ];
  const ids = op_division(d, ["plaque", "plomb"]);
  ok("bande verticale → 2 fragments EXACTEMENT", ids.length === 2,
     String(ids.length));
  const restants = d.calques[0].objets.map((o) => o.id);
  ok("le plomb est conservé, la plaque partie",
     restants.includes("plomb") && !restants.includes("plaque"),
     restants.join(","));
  ok("fragments AVANT le plomb (à l'index de la plaque)",
     restants[0] === ids[0] && restants[1] === ids[1]
     && restants[2] === "plomb", restants.join(","));
  pres("aire du fragment gauche", aireDoc(d, ids[0]), 4500);
  pres("aire du fragment droit", aireDoc(d, ids[1]), 4500);
  ok("style de la plaque copié", d.calques[0].objets[0].style.fond === "#DAA520");
}

// division par découpeur PLEIN entièrement intérieur → 1 fragment troué
{
  const d = banc();
  d.calques[0].objets = [
    R("plaque", 0, 0, 100, 100, { fond: "#DAA520" }),
    { id: "disque", type: "ellipse", cx: 50, cy: 50, rx: 20, ry: 20,
      style: { fond: "#FFFFFF" } },
  ];
  const ids = op_division(d, ["plaque", "disque"]);
  ok("découpe intérieure → 1 fragment", ids.length === 1, String(ids.length));
  const frag = d.calques[0].objets.find((o) => o.id === ids[0]);
  ok("le trou vit en sous-chemin", (frag.d.match(/M /g) || []).length === 2,
     frag.d.slice(0, 60));
  pres("aire plaque moins disque", aireDoc(d, ids[0]),
       10000 - Math.PI * 400);
}

if (echecs.length) {
  console.error("ECHECS opsbool :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA opsbool : PASS (15 controles)");
