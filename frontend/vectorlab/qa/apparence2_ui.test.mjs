// apparence2_ui.test.mjs — lot F : la logique PURE du panneau « Apparence + »
// (lecture bornée d'un effet depuis ses champs, champs par type, libellés,
// lecture des contours, nom de style) et de l'outil pinceau vectoriel.
import { EFFET_CHAMPS, lire_effet, libelle_effet, contours_lire, nom_valide, HINTS3, OUTILS3 } from "../js/mod-apparence2.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
{
  ok("chaque effet a ses champs : l'ombre dx/dy/flou/couleur/opacite, le contour largeur/couleur/opacite", JSON.stringify(EFFET_CHAMPS.ombre.map((c) => c.cle)) === '["dx","dy","flou","couleur","opacite"]' && EFFET_CHAMPS.contour.some((c) => c.cle === "largeur") && Object.keys(EFFET_CHAMPS).length === 6);
  const e = lire_effet("ombre", { dx: "6", dy: "-2,5", flou: "abc", couleur: "#ff0000", opacite: "150" });
  ok("lire_effet : nombres (virgule acceptée), flou illisible → défaut, opacité bornée à 1, couleur en majuscules", e.type === "ombre" && e.dx === 6 && e.dy === -2.5 && e.flou === 4 && e.couleur === "#FF0000" && e.opacite === 1, JSON.stringify(e));
  ok("lire_effet : un type inconnu refuse", (() => { try { lire_effet("zz", {}); return false; } catch { return true; } })());
  ok("libellé : type + paramètres saillants", libelle_effet({ type: "ombre", dx: 4, dy: 4, flou: 4 }).startsWith("Ombre externe") && libelle_effet({ type: "contour", largeur: 3 }).includes("3"));
  const c = contours_lire([{ couleur: "#0000ff", epaisseur: "4" }, { couleur: "rouge", epaisseur: "2" }, { couleur: "#00FF00", epaisseur: "0" }]);
  ok("contours_lire : hex majuscules, épaisseur nombre, les lignes invalides tombent", c.length === 1 && c[0].couleur === "#0000FF" && c[0].epaisseur === 4, JSON.stringify(c));
  ok("état vide : contours_lire([]) → []", contours_lire([]).length === 0);
  ok("nom_valide : lettres/chiffres/-/_ seulement, espaces → tirets", nom_valide(" Ma Marque ") === "Ma-Marque" && nom_valide("é!") === "" && nom_valide("ok_1") === "ok_1");
  ok("outil pinceau vectoriel : id pinceauv, touche j, indice présent", OUTILS3.some((o) => o.id === "pinceauv" && o.touche === "j") && typeof HINTS3.pinceauv === "string");
}
if (echecs.length) {
  console.error("ECHECS apparence2_ui :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA apparence2_ui : PASS (8 controles)");
