// doc_compile.test.mjs — banc headless du modèle-document (node, aucun DOM).
// La compilation JSON -> SVG est PURE : la même fonction sert l'écran,
// l'export et ce banc. Le JSON est la vérité, le SVG une projection.
import { compilerSVG, parserDoc } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 120) : ""));
};

const doc = {
  v: 1, nom: "Banc", taille: { w: 640, h: 960 }, fond: "#14161a",
  calques: [
    { id: "c1", nom: "verre", visible: true, verrou: false, objets: [
      { id: "o1", type: "rect", x: 10, y: 20, w: 100, h: 50,
        style: { fond: "#0047AB", contour: "#1F1512", epaisseur: 4 } },
      { id: "o2", type: "ellipse", cx: 320, cy: 480, rx: 60, ry: 90,
        style: { fond: "#9B111E" } },
    ] },
    { id: "c2", nom: "plombs", visible: false, verrou: false, objets: [
      { id: "o3", type: "path", d: "M 10 10 C 40 10 60 40 60 80 Z",
        style: { fond: "none", contour: "#1F1512", epaisseur: 8 } },
    ] },
  ],
};

const svg = compilerSVG(doc);
ok("racine svg + viewBox du document",
   svg.startsWith("<svg") && svg.includes('viewBox="0 0 640 960"'),
   svg.slice(0, 90));
const g1 = svg.indexOf('data-calque="c1"');
const g2 = svg.indexOf('data-calque="c2"');
ok("un <g> par calque, dans l'ordre", g1 >= 0 && g2 > g1, `${g1}/${g2}`);
ok("le calque invisible est masqué", svg.includes("display:none"));
ok("rect natif avec style", svg.includes("<rect") && svg.includes('x="10"')
   && svg.includes('fill="#0047AB"'));
ok("ellipse native", svg.includes("<ellipse") && svg.includes('cx="320"'));
ok("path: le d passe verbatim",
   svg.includes('d="M 10 10 C 40 10 60 40 60 80 Z"'));
ok("le contour de plomb porte son épaisseur", svg.includes('stroke-width="8"'));
ok("le fond du document est peint", svg.includes('data-fond="1"'));

// parserDoc refuse tout document sans v / taille / calques valides
let refus = 0;
for (const mauvais of [{}, { v: 1 }, { v: 1, taille: { w: 1, h: 1 } },
                       "pas un objet", { v: 1, taille: { w: 0, h: 5 },
                                         calques: [] }]) {
  try { parserDoc(mauvais); } catch { refus++; }
}
ok("parserDoc refuse les documents invalides", refus === 5, String(refus));
const rond = parserDoc(JSON.parse(JSON.stringify(doc)));
ok("parserDoc accepte le document du banc", rond.calques.length === 2);

if (echecs.length) {
  console.error("ECHECS doc_compile :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA doc_compile : PASS (10 controles)");
