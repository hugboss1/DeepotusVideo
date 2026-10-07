// dxf.test.mjs — mod-dxf (lot G) : polylignes (px du document) → mm, Y vers
// le haut, DXF R12 texte (LWPOLYLINE fermées). Module feuille.
import { dxf_de, polylignes_mm } from "../js/mod-dxf.js";
import { anneaux_dxf } from "../js/mod-exportplus.js";

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
/* ── t124 : ce que la découpe reçoit — textes en glyphes, instances, groupes transformés ── */
{
  const bb = (an) => { const xs = an.flatMap((a) => a.map((q) => q[0])), ys = an.flatMap((a) => a.map((q) => q[1]));
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)].map((v) => Math.round(v * 1000) / 1000).join(","); };
  const carre = (x, y, c) => ({ type: "rect", x, y, w: c, h: c });
  // groupe décalé de (100,0) : son rect doit l'être aussi (avant t124, le groupe était descendu sans son transform)
  const g = anneaux_dxf({ calques: [{ id: "c", objets: [{ id: "g", type: "groupe", transform: "translate(100 0)", enfants: [{ id: "r", ...carre(0, 0, 10) }] }] }] });
  ok("groupe transformé : le rect suit le translate", g.anneaux.length === 1 && bb(g.anneaux) === "100,0,110,10", bb(g.anneaux));
  // instance : symbole (un carré 10) posé en (50,20), échelle 2, puis tourné par son transform
  const doc = { symboles: { s1: { objets: [{ id: "sq", ...carre(0, 0, 10) }] } },
    calques: [{ id: "c", objets: [
      { id: "i1", type: "instance", symbole: "s1", x: 50, y: 20, sx: 2, sy: 2 },
      { id: "i2", type: "instance", symbole: "s1", x: 0, y: 0, transform: "translate(200 0)" },
      { id: "i3", type: "instance", symbole: "absent", x: 0, y: 0 }] }] };
  const i = anneaux_dxf(doc);
  ok("instance : le symbole est découpé à sa place et à son échelle", i.anneaux.length === 2 && bb([i.anneaux[0]]) === "50,20,70,40" && bb([i.anneaux[1]]) === "200,0,210,10",
     i.anneaux.map((a) => bb([a])).join(" | "));
  ok("instance d'un symbole absent : sautée et dite", i.sautes["symbole absent"] === 1, JSON.stringify(i.sautes));
  ok("instance éditée en place : sautée (son calque d'édition la porte)", anneaux_dxf({ ...doc, edition: { instance: "i1" } }).anneaux.length === 1);
  // texte : les glyphes (d en coordonnées document) arrivent par la fonction de l'écran, le transform du texte s'applique
  const glyphes = (o) => (o.id === "t1" ? [{ car: "I", d: "M0 0L2 0L2 10L0 10Z" }, { car: "O", d: "M4 0L8 0L8 10L4 10ZM5 1L7 1L7 9L5 9Z" }]
                          : o.id === "t2" ? { raison: "texte gras, italique ou souligné (synthétisé à l'écran)" } : null);
  const t = anneaux_dxf({ calques: [{ id: "c", objets: [
    { id: "t1", type: "texte", x: 0, y: 0, contenu: "IO", transform: "translate(0 30)" },
    { id: "t2", type: "texte", x: 0, y: 0, contenu: "x" },
    { id: "t3", type: "texte", x: 0, y: 0, contenu: "y" },
    { id: "im", type: "image", x: 0, y: 0, w: 5, h: 5, href: "a.png", nat: { w: 5, h: 5 } }] }] }, glyphes);
  ok("texte : un anneau par contour de glyphe (le O garde son trou), transform appliqué", t.anneaux.length === 3 && bb(t.anneaux) === "0,30,8,40", t.anneaux.length + " " + bb(t.anneaux));
  ok("texte refusé ou sans police, image : sautés et comptés par raison",
     t.sautes["texte gras, italique ou souligné (synthétisé à l'écran)"] === 1 && t.sautes["texte (police non chargée)"] === 1 && t.sautes.image === 1, JSON.stringify(t.sautes));
  // un texte DANS un symbole : glyphes par l'id du texte, sous le placement de l'instance
  const ts = anneaux_dxf({ symboles: { s: { objets: [{ id: "t1", type: "texte", x: 0, y: 0, contenu: "IO" }] } },
    calques: [{ id: "c", objets: [{ id: "i", type: "instance", symbole: "s", x: 10, y: 10 }] }] }, glyphes);
  ok("texte d'un symbole : placé par l'instance", ts.anneaux.length === 3 && bb(ts.anneaux) === "10,10,18,20", bb(ts.anneaux));
  ok("calque masqué : rien", anneaux_dxf({ calques: [{ id: "c", visible: false, objets: [{ id: "r", ...carre(0, 0, 5) }] }] }).anneaux.length === 0);
}
if (echecs.length) {
  console.error("ECHECS dxf :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA dxf : PASS (15 controles)");
