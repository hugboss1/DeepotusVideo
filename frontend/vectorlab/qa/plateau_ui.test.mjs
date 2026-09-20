// plateau_ui.test.mjs — la logique PURE des panneaux du lot C : lignes des
// terrains (échappement, actif, hauteur), libellé de grille, lignes des planches.
import { terrainLigne, grilleLibelle } from "../js/mod-plateau.js";
import { plancheLigne } from "../js/mod-planches.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
{
  const h = terrainLigne("foret", { nom: "For<êt>", couleur: "#3F7D3A", hauteur_mm: 3 }, true);
  ok("terrainLigne : échappe, pastille couleur, hauteur mm, actif", h.includes("For&lt;êt&gt;") && h.includes("background:#3F7D3A") && h.includes("3 mm") && h.includes('class="terrain actif"') && h.includes('data-terrain="foret"'), h);
  ok("terrainLigne inactif", !terrainLigne("mer", { nom: "Mer", couleur: "#2B5F9E", hauteur_mm: 0 }, false).includes("actif"));
}
{
  ok("grilleLibelle sans grille", grilleLibelle(null, 8) === "⊞ 8");
  ok("grilleLibelle hex", grilleLibelle({ type: "hex", pas: 32, orientation: "plat" }, 8) === "⊞ hex 32 plat");
  ok("grilleLibelle carrée subdivisée", grilleLibelle({ type: "carree", pas: 20, sous: 4 }, 8) === "⊞ 20 ÷4");
}
{
  const h = plancheLigne({ id: "p1", nom: "Carte <1>", x: 0, y: 0, w: 750, h: 1050 }, { affichage: "mm", dpi: 300 });
  ok("plancheLigne : nom échappé, taille en unité d'affichage, 4 actions", h.includes("Carte &lt;1&gt;") && h.includes("63.5 × 88.9 mm") && ["zoom", "png", "renommer", "supprimer"].every((a) => h.includes(`data-pl-${a}="p1"`)), h);
}
if (echecs.length) {
  console.error("ECHECS plateau_ui :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA plateau_ui : PASS (6 controles)");
