// dxf.test.mjs — mod-dxf (lot G) : polylignes (px du document) → mm, Y vers
// le haut, DXF R12 texte (LWPOLYLINE fermées). Module feuille.
import { dxf_de, polylignes_mm } from "../js/mod-dxf.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
const compte = (s, re) => (s.match(re) || []).length;
{
  const mm = polylignes_mm([[[10, 10], [110, 10], [110, 60]]], { x: 10, y: 10, w: 100, h: 50 }, 254);
  ok("px → mm au dpi 254 (10 px = 1 mm), origine en bas à gauche du cadre, Y retourné : (10,10) → (0,5), (110,60) → (10,0)",
     mm.length === 1 && JSON.stringify(mm[0][0]) === "[0,5]" && JSON.stringify(mm[0][2]) === "[10,0]" && JSON.stringify(mm[0][1]) === "[10,5]", JSON.stringify(mm));
  ok("état vide : [] → []", polylignes_mm([], { x: 0, y: 0, w: 1, h: 1 }, 300).length === 0);
  const d = dxf_de([[[0, 0], [10, 0], [10, 5]], [[1, 1], [2, 1], [2, 2]]], { calque: "decoupe" });
  ok("DXF : sections HEADER ($INSUNITS 4 = mm), TABLES, ENTITIES, EOF", /\$INSUNITS\n 70\n +4\n/.test(d) && d.includes("SECTION\n  2\nENTITIES") && d.trim().endsWith("EOF"), d.slice(0, 200));
  ok("deux LWPOLYLINE fermées (flag 70 = 1) sur le calque, 3 sommets chacune", compte(d, /LWPOLYLINE/g) === 2 && compte(d.slice(d.indexOf("ENTITIES")), /\n 70\n +1\n/g) === 2 && compte(d, /\n 90\n +3\n/g) === 2 && compte(d, /\n  8\ndecoupe\n/g) >= 2, d);
  ok("les coordonnées sont écrites en 10 / 20, avec le point décimal", d.includes(" 10\n10\n 20\n5") || d.includes(" 10\n10.0\n 20\n5.0"), d);
  let refus = 0; try { dxf_de([], {}); } catch { refus++; }
  try { dxf_de([[[0, 0], [1, 1]]], {}); } catch { refus++; }
  ok("vide et polyligne à moins de 3 points refusés", refus === 2);
  ok("calque par défaut « 0 »", dxf_de([[[0, 0], [1, 0], [1, 1]]]).includes("\n  8\n0\n"));
}
if (echecs.length) {
  console.error("ECHECS dxf :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA dxf : PASS (7 controles)");
