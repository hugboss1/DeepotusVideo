// exportplus_ui.test.mjs — lot G : la logique PURE du panneau « Export + »
// (lecture bornée des réglages, résumé du plan, pages PDF depuis les
// tranches, mm d'une tranche au dpi) et de l'outil tranche.
import { reglages_lire, resume_plan, pages_pdf, HINTS4, tranche_normaliser } from "../js/mod-exportplus.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
{
  const r = reglages_lire({ mode: "planches", resolutions: "1, 2", formats: ["png", "pdf", "zz"], transparent: true, saignee: "3,5", coupe: true, reperage: false, dpi: "150", qualite: "1.5" });
  ok("réglages : mode, résolutions lues, formats filtrés, saignée nombre (virgule), coupe, dpi borné, qualité bornée 0..1",
     r.mode === "planches" && JSON.stringify(r.resolutions) === "[1,2]" && JSON.stringify(r.formats) === '["png","pdf"]' && r.transparent === true && r.saignee === 3.5 && r.coupe === true && r.reperage === false && r.dpi === 150 && r.qualite === 1, JSON.stringify(r));
  const d = reglages_lire({ mode: "zz", resolutions: "abc", formats: [], saignee: "-2", dpi: "5" });
  ok("valeurs folles : mode document, résolutions [1], formats [png], saignée 0, dpi ≥ 36", d.mode === "document" && JSON.stringify(d.resolutions) === "[1]" && JSON.stringify(d.formats) === '["png"]' && d.saignee === 0 && d.dpi === 36, JSON.stringify(d));
  ok("état vide : sans rien → défauts", reglages_lire({}).mode === "document" && reglages_lire({}).dpi === 300 && reglages_lire({}).qualite === 0.92);
  const plan = [{ format: "png", k: 1, nom: "a.png" }, { format: "png", k: 2, nom: "a@2x.png" }, { format: "pdf", nom: "lot.pdf", tranches: [1, 2] }, { format: "dxf", nom: "a.dxf" }];
  const s = resume_plan(plan);
  ok("résumé : nombre de fichiers, rasters vers la Bibliothèque, PDF/DXF téléchargés", s.includes("4 fichier") && s.includes("2") && /Biblioth/.test(s) && /télécharg/.test(s), s);
  ok("état vide : plan vide → « rien à exporter »", /rien/i.test(resume_plan([])));
  const pages = pages_pdf([{ nom: "a", cadre: { x: 0, y: 0, w: 750, h: 1050 } }], 300, 3);
  ok("pages PDF : mm depuis les px au dpi du document (750 px @300 = 63,5 mm) + saignée de chaque côté, w_px au dpi d'export", pages.length === 1 && Math.abs(pages[0].w_mm - 69.5) < 1e-9 && Math.abs(pages[0].h_mm - 94.9) < 1e-9 && pages[0].w_px === Math.round((750 + 2 * 300 * 3 / 25.4)) , JSON.stringify(pages));
  ok("tranche_normaliser : coins dans l'ordre, taille minimale 1, nom tN", JSON.stringify(tranche_normaliser(50, 60, 10, 20, 3)) === JSON.stringify({ nom: "t3", x: 10, y: 20, w: 40, h: 40 }) && tranche_normaliser(5, 5, 5, 5, 1).w === 1);
  ok("indice de l'outil tranche", typeof HINTS4.tranche === "string");
}
if (echecs.length) {
  console.error("ECHECS exportplus_ui :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA exportplus_ui : PASS (8 controles)");
