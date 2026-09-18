// impression_ui.test.mjs — lot D : la logique pure du dialogue d'impression
// (lecture des réglages bornés, hauteurs par calque, libellé de résumé).
import { reglages_lire, hauteurs_par_calque, resume_impression } from "../js/mod-impression.js";
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
{
  const r = reglages_lire({ mode: "logo", hauteur: "5", socle: "2", biseau: "1", evide: true, mur: "1.2", plancher: "1" });
  ok("réglages bornés, nombres", r.mode === "logo" && r.hauteur === 5 && r.biseau === 1 && r.evide === true && r.mur === 1.2, JSON.stringify(r));
  const b = reglages_lire({ mode: "x", hauteur: "-3", socle: "abc", biseau: "9", mur: "0.1", plancher: "50" });
  ok("valeurs folles : mode calques, hauteur 3 par défaut, socle 0, biseau borné sous la hauteur, mur ≥ 0,8, plancher sous la hauteur",
     b.mode === "calques" && b.hauteur === 3 && b.socle === 0 && b.biseau < b.hauteur && b.mur === 0.8 && b.plancher < b.hauteur, JSON.stringify(b));
  ok("virgule décimale acceptée", reglages_lire({ hauteur: "2,5" }).hauteur === 2.5);
  ok("dépouille lue, bornée ±45, 0 par défaut", reglages_lire({ mode: "logo", depouille: "20" }).depouille === 20
     && reglages_lire({ mode: "logo", depouille: "90" }).depouille === 45 && reglages_lire({ mode: "logo", depouille: "-70" }).depouille === -45
     && reglages_lire({ mode: "logo" }).depouille === 0 && reglages_lire({ depouille: "abc" }).depouille === 0);
}
{
  const h = hauteurs_par_calque("3, contours=5, Verres = 2", [{ nom: "verres" }, { nom: "contours" }, { nom: "autre" }]);
  ok("hauteur globale + surcharges par nom (insensible à la casse)", h.globale === 3 && h.parCalque.verres === 2 && h.parCalque.contours === 5 && h.parCalque.autre === undefined, JSON.stringify(h));
  let refus = 0; try { hauteurs_par_calque("abc", []); } catch { refus++; }
  ok("sans hauteur globale valide → refus", refus === 1);
}
{
  const s = resume_impression({ triangles: 1200, bbox_mm: [[0, 50], [0, 30], [0, 4]], pieces: 7, ignores: 2 });
  ok("résumé : dimensions mm arrondies, pièces, triangles, ignorés dits", s.includes("50 × 30 × 4 mm") && s.includes("7 pièce") && s.includes("1200") && s.includes("2 texte"), s);
  ok("sans ignoré : rien de dit", !resume_impression({ triangles: 1, bbox_mm: [[0, 1], [0, 1], [0, 1]], pieces: 1, ignores: 0 }).includes("texte"));
}
{
  const { couleurs_json, couleur_du_lot } = await import("../js/mod-impression.js");
  const P = [{ nom: "a", couleur: "#ff0000" }, { nom: "b" }, { nom: "c", couleur: "#ff0000" }, { nom: "d", couleur: "#00ff00" }];
  ok("couleurs_json : seules les pièces colorées, par nom", couleurs_json(P) === JSON.stringify({ a: "#ff0000", c: "#ff0000", d: "#00ff00" }));
  ok("couleur_du_lot : le vote des pièces", couleur_du_lot(P) === "#ff0000");
  ok("couleur_du_lot sans couleur → null", couleur_du_lot([{ nom: "x" }]) === null);
}
if (echecs.length) { console.error("ECHECS impression_ui :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA impression_ui : PASS (11 controles)");
