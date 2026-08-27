// snapshot.test.mjs — LE verrou de la phase 2 (T2.4) : un document de
// référence exerçant tout (dégradés linéaire/radial + stop-opacity + repli
// manquant + dégradé inutilisé élagué, dash/joint/opacités objet-calque,
// groupe stylé transformé, calque caché) compilé → chaîne SVG attendue
// LITTÉRALE, diff exact. Toute dérive de compilation rougit ici.
import { compilerSVG } from "../js/mod-doc.js";

const doc = {
  v: 1, nom: "Snapshot", taille: { w: 200, h: 100 }, fond: "#FFFFFF",
  degrades: {
    g1: { type: "lineaire", x1: 0, y1: 0, x2: 200, y2: 0,
          stops: [{ t: 0, couleur: "#0047AB" }, { t: 1, couleur: "#DAA520" }] },
    g2: { type: "radial", cx: 150, cy: 50, r: 30,
          stops: [{ t: 1, couleur: "#046307" },
                  { t: 0, couleur: "#FFFFFF", opacite: 0.5 }] },
    gInutile: { type: "lineaire", x1: 0, y1: 0, x2: 1, y2: 1,
                stops: [{ t: 0, couleur: "#000000" },
                        { t: 1, couleur: "#FFFFFF" }] },
  },
  calques: [
    { id: "c1", nom: "fond", visible: true, verrou: false, opacite: 0.9,
      objets: [
        { id: "r1", type: "rect", x: 10, y: 10, w: 80, h: 40,
          style: { fond: "grad:g1", contour: "#1F1512", epaisseur: 4,
                   pointilles: "6 4", joint: "bevel", opacite: 0.75 } },
        { id: "e1", type: "ellipse", cx: 150, cy: 50, rx: 30, ry: 20,
          style: { fond: "grad:g2" } },
      ] },
    { id: "c2", nom: "dessin", visible: true, verrou: false, objets: [
      { id: "grp", type: "groupe", style: { opacite: 0.5 },
        transform: "rotate(15 100 50)", enfants: [
          { id: "p1", type: "path", d: "M 10 90 L 60 90",
            style: { fond: "none", contour: "#9B111E", epaisseur: 2 } },
          { id: "t1", type: "rect", x: 20, y: 70, w: 10, h: 10,
            style: { fond: "grad:manquant" } },
        ] },
    ] },
    { id: "c3", nom: "cache", visible: false, verrou: false, objets: [] },
  ],
};

const attendu =
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"`
  + ` width="200" height="100">`
  + `<defs>`
  + `<linearGradient id="g1" gradientUnits="userSpaceOnUse" x1="0" y1="0"`
  + ` x2="200" y2="0">`
  + `<stop offset="0" stop-color="#0047AB"/>`
  + `<stop offset="1" stop-color="#DAA520"/>`
  + `</linearGradient>`
  + `<radialGradient id="g2" gradientUnits="userSpaceOnUse" cx="150"`
  + ` cy="50" r="30">`
  + `<stop offset="0" stop-color="#FFFFFF" stop-opacity="0.5"/>`
  + `<stop offset="1" stop-color="#046307"/>`
  + `</radialGradient>`
  + `</defs>`
  + `<rect x="0" y="0" width="200" height="100" fill="#FFFFFF" data-fond="1"/>`
  + `<g data-calque="c1" data-nom="fond" opacity="0.9">`
  + `<rect data-objet="r1" x="10" y="10" width="80" height="40"`
  + ` fill="url(#g1)" stroke="#1F1512" stroke-width="4"`
  + ` stroke-linejoin="bevel" stroke-linecap="round"`
  + ` stroke-dasharray="6 4" opacity="0.75"/>`
  + `<ellipse data-objet="e1" cx="150" cy="50" rx="30" ry="20"`
  + ` fill="url(#g2)"/>`
  + `</g>`
  + `<g data-calque="c2" data-nom="dessin">`
  + `<g data-objet="grp" fill="none" opacity="0.5"`
  + ` transform="rotate(15 100 50)">`
  + `<path data-objet="p1" d="M 10 90 L 60 90" fill="none"`
  + ` stroke="#9B111E" stroke-width="2" stroke-linejoin="round"`
  + ` stroke-linecap="round"/>`
  + `<rect data-objet="t1" x="20" y="70" width="10" height="10"`
  + ` fill="none"/>`
  + `</g>`
  + `</g>`
  + `<g data-calque="c3" data-nom="cache" style="display:none"></g>`
  + `</svg>`;

const obtenu = compilerSVG(doc);
if (obtenu !== attendu) {
  let i = 0;
  while (i < Math.min(obtenu.length, attendu.length)
         && obtenu[i] === attendu[i]) i++;
  console.error("ECHEC snapshot — premier écart à l'octet " + i);
  console.error("  attendu … " + attendu.slice(Math.max(0, i - 40), i + 60));
  console.error("  obtenu  … " + obtenu.slice(Math.max(0, i - 40), i + 60));
  process.exit(1);
}
// la compilation est PURE : elle ne mute jamais le document
const avant = JSON.stringify(doc);
compilerSVG(doc);
if (JSON.stringify(doc) !== avant) {
  console.error("ECHEC snapshot — compilerSVG a muté le document");
  process.exit(1);
}
console.log("QA snapshot : PASS (diff exact + purete)");
