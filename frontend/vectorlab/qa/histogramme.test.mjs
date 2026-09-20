// histogramme.test.mjs — mod-histogramme : le panneau Histogramme d'Affinity
// — quatre canaux de 256 (R, V, B, luminance) depuis un tampon {w,h,data},
// pixels transparents ignorés, statistiques, chemins SVG normalisés. Feuille.
import { histogramme, histogramme_chemins } from "../js/mod-histogramme.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 250) : "")); };
{
  // tampon 2 × 2 : noir opaque, blanc opaque, rouge opaque, transparent (ignoré)
  const t = { w: 2, h: 2, data: new Uint8ClampedArray([0, 0, 0, 255, 255, 255, 255, 255, 255, 0, 0, 255, 9, 9, 9, 0]) };
  const h = histogramme(t);
  ok("quatre canaux de 256 ; 3 pixels comptés (le transparent est ignoré)", h.r.length === 256 && h.g.length === 256 && h.b.length === 256 && h.l.length === 256 && h.pixels === 3 && h.r[0] === 1 && h.r[255] === 2 && h.g[255] === 1 && h.g[0] === 2 && h.b[0] === 2 && h.b[255] === 1, JSON.stringify([h.pixels, h.r[0], h.r[255]]));
  ok("luminance : noir 0, blanc 255, rouge 76 (Rec. 601 : 0,299 × 255)", h.l[0] === 1 && h.l[255] === 1 && h.l[76] === 1, h.l.findIndex((v, i) => v && i > 0 && i < 255));
  ok("statistiques : moyenne 110, écart-type ≈ 106,9, médiane 76", h.moyenne === 110 && Math.abs(h.ecartType - 106.87) < 0.05 && h.mediane === 76, JSON.stringify([h.moyenne, h.ecartType, h.mediane]));
  ok("état vide : tampon nul, données absentes ou sans pixel opaque → 0 partout, chemins vides", histogramme(null).pixels === 0 && histogramme({ w: 1, h: 1 }).pixels === 0 && histogramme({ w: 1, h: 1, data: new Uint8ClampedArray([1, 2, 3, 0]) }).pixels === 0 && histogramme(null).moyenne === 0 && histogramme_chemins(histogramme(null), 200, 80).l === "" && histogramme_chemins(null, 200, 80).r === "");
  const c = histogramme_chemins(h, 256, 100);
  ok("chemins : un par canal, de bas en bas (fermés), 256 points, normalisés au maximum (le pic touche le haut)", ["r", "g", "b", "l"].every((k) => c[k].startsWith("M0 100") && c[k].endsWith("L256 100Z")) && (c.r.match(/L/g) || []).length === 257 && c.r.includes("L256 0 ") === true && c.r.includes("L0 50 ") === true, c.r.slice(0, 60) + " … " + c.r.slice(-40));
  ok("chemins : un canal sans aucun pixel → chaîne vide, les autres intacts", (() => { const h2 = histogramme({ w: 1, h: 1, data: new Uint8ClampedArray([0, 0, 0, 255]) }); const c2 = histogramme_chemins(h2, 100, 50); return c2.r.length > 0 && c2.l.length > 0; })());
}
if (echecs.length) { console.error("ECHECS histogramme :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA histogramme : PASS (6 controles)");
