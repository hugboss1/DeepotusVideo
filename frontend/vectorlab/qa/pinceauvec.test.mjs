// pinceauvec.test.mjs — mod-pinceauvec (lot F) : le pinceau vectoriel à
// profil — un trait devient un CHEMIN FERMÉ dont la largeur suit un profil
// (plat, fuseau, calligraphie à angle fixe). Module feuille.
import { PROFILS, profil, trait_profil } from "../js/mod-pinceauvec.js";
import { chemin_parser } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
const bbox = (d) => {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const s of chemin_parser(d)) for (let k = 0; k < s.p.length; k += 2) { x0 = Math.min(x0, s.p[k]); x1 = Math.max(x1, s.p[k]); y0 = Math.min(y0, s.p[k + 1]); y1 = Math.max(y1, s.p[k + 1]); }
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
};
{
  ok("trois profils", JSON.stringify(PROFILS.map((p) => p.id)) === '["plat","fuseau","calligraphie"]');
  ok("plat = 1 partout ; fuseau = 0 aux bouts, 1 au milieu ; calligraphie = 1", profil("plat", 0) === 1 && profil("fuseau", 0) === 0 && Math.abs(profil("fuseau", 0.5) - 1) < 1e-9 && profil("calligraphie", 0.3) === 1);
  let refus = 0; try { profil("zz", 0); } catch { refus++; }
  try { trait_profil([[0, 0]], {}); } catch { refus++; }
  ok("profil inconnu et trait à un seul point refusés", refus === 2);
  const ligne = [[0, 0], [50, 0], [100, 0]];
  const plat = trait_profil(ligne, { largeur: 10, profil: "plat" });
  ok("plat sur une droite : contour fermé de hauteur 10, largeur 100, qui commence au bord gauche", /^M 0 5 /.test(plat) && plat.endsWith("Z") && JSON.stringify(bbox(plat)) === JSON.stringify({ x: 0, y: -5, w: 100, h: 10 }), plat);
  ok("les deux rives : aller sur une rive, retour sur l'autre", plat.includes("L 100 5") && plat.includes("L 100 -5") && plat.includes("L 0 -5"));
  const fus = trait_profil(ligne, { largeur: 10, profil: "fuseau" });
  ok("fuseau : nul aux bouts (M 0 0), plein au milieu (50 ±5)", /^M 0 0 /.test(fus) && fus.includes("L 50 5") && fus.includes("L 50 -5"), fus);
  const cal = trait_profil(ligne, { largeur: 10, profil: "calligraphie", angle: 0 });
  ok("calligraphie à 0° sur une droite horizontale : la plume est parallèle au trait, hauteur nulle, x de −5 à 105", bbox(cal).h === 0 && bbox(cal).x === -5 && bbox(cal).w === 110, cal);
  const cal90 = trait_profil(ligne, { largeur: 10, profil: "calligraphie", angle: 90 });
  ok("calligraphie à 90° : plume perpendiculaire, hauteur 10", Math.abs(bbox(cal90).h - 10) < 1e-9, cal90);
  const courbe = trait_profil([[0, 0], [30, 40], [60, 0]], { largeur: 6, profil: "plat" });
  ok("un coude : 6 sommets (3 par rive), chemin fermé", (courbe.match(/L /g) || []).length === 5 && courbe.endsWith("Z"), courbe);
  ok("largeur par défaut 8, profil fuseau par défaut", Math.abs(bbox(trait_profil(ligne, {})).h - 8) < 1e-9 && /^M 0 0 /.test(trait_profil(ligne, {})));
  ok("points doublons tolérés (tangente du voisin)", essaie(() => trait_profil([[0, 0], [0, 0], [10, 0]], { profil: "plat" })));
}
function essaie(fn) { try { fn(); return true; } catch { return false; } }
if (echecs.length) {
  console.error("ECHECS pinceauvec :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA pinceauvec : PASS (12 controles)");
