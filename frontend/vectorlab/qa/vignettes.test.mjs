// vignettes.test.mjs — mod-layers : la miniature d'un calque = le document
// compilé avec CE calque seul visible, sans fond, ajusté dans une boîte w×h
// sur un damier ; un calque vide ou inconnu donne une vignette vide.
import { vignette_calque_svg } from "../js/mod-layers.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
const doc = { v: 1, taille: { w: 400, h: 200 }, fond: "#FFFFFF", calques: [
  { id: "c1", nom: "fond", visible: true, verrou: false, objets: [{ id: "r1", type: "rect", x: 10, y: 10, w: 100, h: 50, style: { fond: "#FF0000" } }] },
  { id: "c2", nom: "detail", visible: false, verrou: false, objets: [{ id: "e1", type: "ellipse", cx: 300, cy: 100, rx: 40, ry: 20, style: { fond: "#00FF00" } }] },
  { id: "c3", nom: "vide", visible: true, verrou: false, objets: [] },
] };
{
  const v = vignette_calque_svg(doc, "c1", 44, 32);
  ok("vignette c1 : un <svg> de 44×32, viewBox de la page, le rect rouge dedans, PAS l'ellipse, PAS le fond de page", v.startsWith("<svg") && v.includes('width="44"') && v.includes('height="32"') && v.includes('viewBox="0 0 400 200"') && v.includes('fill="#FF0000"') && !v.includes("#00FF00") && !v.includes('data-fond'), v);
  const v2 = vignette_calque_svg(doc, "c2", 44, 32);
  ok("vignette c2 : le calque caché est quand même rendu (c'est SON contenu), sans le rect", v2.includes("#00FF00") && !v2.includes("#FF0000"), v2);
  ok("le damier de fond est là et aucun data-objet ne sort (pas de hit-testing dans une vignette)", v.includes("damier") && !v.includes("data-objet="));
  ok("état vide : calque vide → svg sans objet ; calque inconnu → chaîne vide", !vignette_calque_svg(doc, "c3", 44, 32).includes("<rect x=\"10\"") && vignette_calque_svg(doc, "zz", 44, 32) === "");
  ok("le résolveur d'image est transmis", vignette_calque_svg({ ...doc, calques: [{ id: "i", nom: "i", visible: true, verrou: false, objets: [{ id: "im", type: "image", x: 0, y: 0, w: 10, h: 10, href: "img1.png", nat: { w: 1, h: 1 }, style: {} }] }] }, "i", 44, 32, (h) => "/U/" + h).includes('href="/U/img1.png"'));
}
if (echecs.length) {
  console.error("ECHECS vignettes :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA vignettes : PASS (5 controles)");
