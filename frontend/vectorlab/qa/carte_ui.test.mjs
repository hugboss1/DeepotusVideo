// carte_ui.test.mjs — lot H : la logique PURE du panneau « Carte réelle » :
// libellé d'échelle (1 : N, km, mm imprimés), conversion grille de relief →
// px de page, lignes de niveau → px, niveaux d'un pas, image ombrée (RGBA).
import { libelle_carte, grille_vers_px, lignes_vers_px, niveaux, ombrage_rgba } from "../js/mod-carte.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
{
  const geo = { m_par_px: 2000 / 900, emprise_px: { x: 50, y: 50, w: 900, h: 450 } };
  const l = libelle_carte(geo, { affichage: "mm", dpi: 96 });
  ok("libellé : échelle, largeur réelle en km, largeur imprimée en mm", l.includes("1 : 8 400") && l.includes("2,0 km") && l.includes("238 mm"), l);
  ok("sans geo : libellé d'amorce", libelle_carte(null, { dpi: 96 }).includes("Importer"));
}
{
  const relief = { w: 5, h: 3 }, E = { x: 100, y: 200, w: 400, h: 200 };
  ok("coin (0,0) de la grille → coin NO de l'emprise", JSON.stringify(grille_vers_px(0, 0, relief, E)) === "[100,200]");
  ok("dernier sommet (4,2) → coin SE", JSON.stringify(grille_vers_px(4, 2, relief, E)) === "[500,400]");
  const lp = lignes_vers_px([[[0, 0], [2, 1]], [[4, 2]]], relief, E);
  ok("lignes → px, arrondies au dixième", JSON.stringify(lp) === "[[[100,200],[300,300]],[[500,400]]]", JSON.stringify(lp));
}
{
  ok("niveaux : multiples du pas dans ]min, max[", JSON.stringify(niveaux(1012, 1188, 50)) === "[1050,1100,1150]");
  ok("niveaux : pas plus grand que l'amplitude → []", niveaux(10, 20, 50).length === 0);
  ok("niveaux : garde 400 niveaux au plus", niveaux(0, 100000, 1).length <= 400);
}
{
  const rgba = ombrage_rgba(new Uint8ClampedArray([0, 128, 255]), 3, 1);
  ok("RGBA : gris posé sur R, G, B, alpha 255", rgba.length === 12 && rgba[0] === 0 && rgba[4] === 128 && rgba[5] === 128 && rgba[8] === 255 && rgba[3] === 255 && rgba[11] === 255);
}
if (echecs.length) { console.error("ECHECS carte_ui :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA carte_ui : PASS (9 controles)");
