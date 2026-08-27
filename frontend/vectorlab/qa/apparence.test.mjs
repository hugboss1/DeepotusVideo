// apparence.test.mjs — style, joints, pointillés, opacités (T2.1).
// op_style fusionne un patch (null retire la clé) ; la compilation émet
// dasharray, linejoin (round par défaut — compat phase 1), l'opacité
// d'objet et l'opacité de calque.
import { op_style, op_calque_opacite, compilerSVG } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

const banc = () => ({
  v: 1, nom: "App", taille: { w: 100, h: 100 },
  calques: [
    { id: "c1", nom: "a", visible: true, verrou: false, objets: [
      { id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10,
        style: { fond: "#111111", contour: "#222222", epaisseur: 2 } },
    ] },
    { id: "c2", nom: "b", visible: true, verrou: true, objets: [
      { id: "r2", type: "rect", x: 0, y: 0, w: 5, h: 5, style: {} },
    ] },
  ],
});

// op_style : fusion, retrait par null, verrouillé ignoré
{
  const d = banc();
  op_style(d, ["r1", "r2"], { fond: "#ABCDEF", pointilles: "6 4",
                              joint: "bevel", opacite: 0.5, contour: null });
  const s = d.calques[0].objets[0].style;
  ok("fusion du patch", s.fond === "#ABCDEF" && s.pointilles === "6 4"
     && s.joint === "bevel" && s.opacite === 0.5, JSON.stringify(s));
  ok("null retire la clé", !("contour" in s), JSON.stringify(s));
  ok("l'épaisseur préexistante survit", s.epaisseur === 2);
  ok("verrouillé intact",
     JSON.stringify(d.calques[1].objets[0].style) === "{}");
}

// compilation : dasharray, joint, opacités
{
  const d = banc();
  op_style(d, ["r1"], { pointilles: "6 4", joint: "bevel", opacite: 0.5 });
  op_calque_opacite(d, "c1", 0.8);
  const svg = compilerSVG(d);
  ok("dasharray émis", svg.includes('stroke-dasharray="6 4"'), svg);
  ok("joint surchargé", svg.includes('stroke-linejoin="bevel"'));
  ok("opacité d'objet", svg.includes('opacity="0.5"'));
  ok("opacité de calque", /data-calque="c1"[^>]*opacity="0.8"/.test(svg), svg);
}

// compat phase 1 : sans joint ni pointillés, la sortie ne change pas
{
  const d = banc();
  const svg = compilerSVG(d);
  ok("linejoin round par défaut", svg.includes('stroke-linejoin="round"'));
  ok("pas de dasharray par défaut", !svg.includes("stroke-dasharray"));
}

// bornes : opacité de calque clampée, calque inconnu refusé
{
  const d = banc();
  op_calque_opacite(d, "c1", 4);
  ok("opacité clampée à 1", d.calques[0].opacite === 1);
  let refus = false;
  try { op_calque_opacite(d, "cX", 0.5); } catch { refus = true; }
  ok("calque inconnu refusé", refus);
}

if (echecs.length) {
  console.error("ECHECS apparence :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA apparence : PASS (11 controles)");
