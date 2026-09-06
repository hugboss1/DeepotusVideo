// degrades_suivent.test.mjs — le dégradé SUIT la forme (remontée du
// 06/09/2026 : « les poignées de modification de la profondeur du dégradé
// et de son orientation ne suivent pas la forme »).
//
// Mesuré au navigateur avant correction : une ellipse en (375,525) avec un
// dégradé radial au même centre ; après `op_deplacer(+120,+60)` l'ellipse
// était en (495,585) et le dégradé toujours en (375,525) ; après un
// redimensionnement ×0,5 l'ellipse avait rx=100 et le dégradé r=200.
// Ce banc épingle la correction, et la RÉSERVE : `op_tourner` ne touche
// PAS au dégradé — il pose un `transform` sur l'objet, et le user space
// d'un serveur de peinture est celui de l'élément qui le référence.
import { op_ajouter, op_degrade_creer, op_style, op_deplacer,
         op_redimensionner, op_tourner, op_miroir, op_dupliquer }
  from "../js/mod-doc.js";

const echecs = [];
let total = 0;
const ok = (nom, cond, detail = "") => {
  total += 1;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

const docNeuf = () => ({ v: "1", taille: { w: 750, h: 1050 },
  calques: [{ id: "c1", nom: "fond", objets: [] }] });

// une ellipse + son dégradé radial, aux mêmes centre et rayon
function scene(type = "radial") {
  const doc = docNeuf();
  const id = op_ajouter(doc, "c1", { type: "ellipse", cx: 375, cy: 525,
    rx: 200, ry: 170, style: { fond: "#0d2b6b" } });
  const gid = op_degrade_creer(doc, type === "radial"
    ? { type: "radial", cx: 375, cy: 525, r: 200,
        stops: [{ t: 0, couleur: "#fff" }, { t: 1, couleur: "#0d2b6b" }] }
    : { type: "lineaire", x1: 175, y1: 525, x2: 575, y2: 525,
        stops: [{ t: 0, couleur: "#fff" }, { t: 1, couleur: "#0d2b6b" }] });
  op_style(doc, [id], { fond: "grad:" + gid });
  return { doc, id, gid, g: () => doc.degrades[gid],
           o: () => doc.calques[0].objets.find((x) => x.id === id) };
}

// ── déplacement : le dégradé suit, exactement ──
{
  const s = scene();
  op_deplacer(s.doc, [s.id], 120, 60);
  ok("radial: le centre suit le déplacement (+120,+60)",
     s.g().cx === 495 && s.g().cy === 585, JSON.stringify(s.g()));
  ok("radial: le rayon ne bouge pas sur un déplacement", s.g().r === 200);
  ok("radial: forme et dégradé restent concentriques",
     s.g().cx === s.o().cx && s.g().cy === s.o().cy);

  const l = scene("lineaire");
  op_deplacer(l.doc, [l.id], -40, 25);
  ok("linéaire: les DEUX extrémités suivent",
     l.g().x1 === 135 && l.g().y1 === 550
     && l.g().x2 === 535 && l.g().y2 === 550, JSON.stringify(l.g()));
}

// ── redimensionnement : points mappés, rayon à la moyenne des facteurs ──
{
  const s = scene();
  const av = { x: 175, y: 355, w: 400, h: 340 };
  op_redimensionner(s.doc, [s.id], av, { x: 175, y: 355, w: 200, h: 170 });
  ok("radial: le centre suit le redimensionnement ×0,5",
     s.g().cx === 275 && s.g().cy === 440, JSON.stringify(s.g()));
  ok("radial: le rayon suit (moyenne des deux facteurs, écart déclaré)",
     s.g().r === 100, String(s.g().r));
  ok("radial: forme et dégradé restent concentriques après échelle",
     s.g().cx === s.o().cx && s.g().cy === s.o().cy);

  // échelle NON uniforme : la moyenne est le choix retenu, il est épinglé
  const s2 = scene();
  op_redimensionner(s2.doc, [s2.id], av, { x: 175, y: 355, w: 800, h: 340 });
  ok("radial: échelle non uniforme (×2 en x, ×1 en y) → rayon ×1,5",
     s2.g().r === 300, String(s2.g().r));

  const l = scene("lineaire");
  op_redimensionner(l.doc, [l.id], av, { x: 175, y: 355, w: 200, h: 340 });
  ok("linéaire: les extrémités sont mappées comme la géométrie",
     l.g().x1 === 175 && l.g().x2 === 375, JSON.stringify(l.g()));
}

// ── rotation : RÉSERVE — le dégradé ne bouge pas, et c'est juste ──
{
  const s = scene();
  const avant = JSON.stringify(s.g());
  op_tourner(s.doc, [s.id], 375, 525, 30);
  ok("rotation: le dégradé n'est PAS touché (le transform de l'objet "
     + "emporte déjà son serveur de peinture)",
     JSON.stringify(s.g()) === avant);
  ok("rotation: et l'objet porte bien le transform",
     /rotate\(30/.test(s.o().transform || ""), s.o().transform);
}

// ── miroir ──
{
  const l = scene("lineaire");
  op_miroir(l.doc, [l.id], "h", { x: 175, y: 355, w: 400, h: 340 });
  ok("miroir horizontal: les extrémités se reflètent",
     l.g().x1 === 575 && l.g().x2 === 175, JSON.stringify(l.g()));
  ok("miroir horizontal: les ordonnées ne bougent pas",
     l.g().y1 === 525 && l.g().y2 === 525);
}

// ── duplication : la copie a SON dégradé, l'original ne bouge plus ──
{
  const s = scene();
  const neufs = op_dupliquer(s.doc, [s.id], 12, 12);
  const copie = s.doc.calques[0].objets.find((x) => x.id === neufs[0]);
  const gidCopie = String(copie.style.fond).slice(5);
  ok("dupliquer: la copie pointe un AUTRE dégradé", gidCopie !== s.gid);
  ok("dupliquer: le dégradé de la copie est décalé comme elle",
     s.doc.degrades[gidCopie].cx === 387
     && s.doc.degrades[gidCopie].cy === 537,
     JSON.stringify(s.doc.degrades[gidCopie]));
  ok("dupliquer: celui de l'original n'a pas bougé",
     s.g().cx === 375 && s.g().cy === 525, JSON.stringify(s.g()));
  // et déplacer la copie ne touche plus l'original
  op_deplacer(s.doc, [neufs[0]], 100, 0);
  ok("dupliquer: déplacer la copie laisse le dégradé de l'original en place",
     s.g().cx === 375 && s.doc.degrades[gidCopie].cx === 487,
     JSON.stringify([s.g().cx, s.doc.degrades[gidCopie].cx]));
}

// ── partage : un dégradé visé par DEUX objets n'est transporté qu'une fois ──
{
  const s = scene();
  const id2 = op_ajouter(s.doc, "c1", { type: "rect", x: 10, y: 10,
    w: 50, h: 50, style: { fond: "grad:" + s.gid } });
  op_deplacer(s.doc, [s.id, id2], 10, 10);
  ok("partage: deux objets, UN seul transport du dégradé (pas +20)",
     s.g().cx === 385 && s.g().cy === 535, JSON.stringify(s.g()));
}

// ── états vides : rien ne casse, rien ne ment ──
{
  const doc = docNeuf();
  const id = op_ajouter(doc, "c1", { type: "rect", x: 0, y: 0, w: 10, h: 10,
    style: { fond: "#123456" } });
  op_deplacer(doc, [id], 5, 5);
  ok("sans dégradé: le déplacement ne crée aucune table de dégradés",
     doc.degrades === undefined || Object.keys(doc.degrades).length === 0);
  const d2 = docNeuf();
  const i2 = op_ajouter(d2, "c1", { type: "rect", x: 0, y: 0, w: 10, h: 10,
    style: { fond: "grad:fantome" } });
  op_deplacer(d2, [i2], 5, 5);
  ok("dégradé fantôme (référence morte): aucune levée",
     d2.calques[0].objets[0].x === 5);
}

if (echecs.length) {
  console.error("ECHECS degrades_suivent :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA degrades_suivent : PASS (" + total + " controles)");
