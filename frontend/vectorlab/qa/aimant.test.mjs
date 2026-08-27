// aimant.test.mjs — aimantation (T1.6) : guides d'abord (l'intention posée
// par l'utilisateur), grille ensuite, rien hors tolérance ; guides
// persistés dans doc.guides et mutés par commandes (donc annulables).
import { aimanter, op_guide_ajouter, op_guide_deplacer, op_guide_supprimer,
         parserDoc } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 140) : ""));
};

// grille : accroche dans la tolérance, sinon valeur inchangée
ok("grille accroche", aimanter(15.1, { pas: 8, guides: [] }, 2) === 16);
ok("grille hors tolérance", aimanter(12.3, { pas: 8, guides: [] }, 2) === 12.3);
// guide prioritaire sur la grille
ok("guide avant grille",
   aimanter(15.1, { pas: 8, guides: [15.5] }, 2) === 15.5);
// guide le plus proche
ok("guide le plus proche",
   aimanter(20, { pas: 0, guides: [18, 21] }, 3) === 21);
// sans pas ni guides : identité
ok("identité", aimanter(7.7, { pas: 0, guides: [] }, 2) === 7.7);

// guides du document : commandes
{
  const d = { v: 1, nom: "g", taille: { w: 10, h: 10 },
              calques: [{ id: "c1", nom: "l", visible: true, verrou: false,
                          objets: [] }] };
  const i = op_guide_ajouter(d, "v", 120);
  op_guide_ajouter(d, "h", 40);
  ok("guides créés", d.guides.v[i] === 120 && d.guides.h[0] === 40,
     JSON.stringify(d.guides));
  op_guide_deplacer(d, "v", i, 130);
  ok("guide déplacé", d.guides.v[i] === 130);
  op_guide_supprimer(d, "v", i);
  ok("guide supprimé", d.guides.v.length === 0);
  let refus = 0;
  try { op_guide_ajouter(d, "x", 1); } catch { refus++; }
  try { op_guide_deplacer(d, "h", 9, 1); } catch { refus++; }
  ok("axe inconnu + index hors bornes → refus", refus === 2, String(refus));
  // le document avec guides reste valide au parseur
  ok("parserDoc accepte doc.guides",
     parserDoc(JSON.parse(JSON.stringify(d))).guides.h[0] === 40);
}

if (echecs.length) {
  console.error("ECHECS aimant :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA aimant : PASS (9 controles)");
