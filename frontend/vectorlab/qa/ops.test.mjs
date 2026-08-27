// ops.test.mjs — opérations d'objets sur le modèle (T1.2) : ajouter,
// supprimer, déplacer, redimensionner (application affine exacte), tourner
// (composition de transform). Toutes PURES : doc muté, vérifié au JSON.
import { op_ajouter, op_supprimer, op_deplacer, op_redimensionner,
         op_tourner } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 140) : ""));
};

const banc = () => ({
  v: 1, nom: "Banc", taille: { w: 1000, h: 1000 },
  calques: [
    { id: "c1", nom: "libre", visible: true, verrou: false, objets: [
      { id: "r1", type: "rect", x: 10, y: 20, w: 100, h: 50, style: {} },
      { id: "e1", type: "ellipse", cx: 300, cy: 400, rx: 60, ry: 90, style: {} },
      { id: "p1", type: "path", d: "M 0 0 L 10 0 C 10 5 5 10 0 10 Z", style: {} },
    ] },
    { id: "c2", nom: "verrouille", visible: true, verrou: true, objets: [
      { id: "r2", type: "rect", x: 0, y: 0, w: 5, h: 5, style: {} },
    ] },
  ],
});

// ── ajouter : id unique généré, en fin de calque, refus du verrouillé ──
{
  const d = banc();
  const id = op_ajouter(d, "c1", { type: "rect", x: 1, y: 1, w: 2, h: 2, style: {} });
  ok("ajouter rend un id", typeof id === "string" && id.length > 0, id);
  const objets = d.calques[0].objets;
  ok("ajouté en fin de calque (dessus)", objets[objets.length - 1].id === id);
  const id2 = op_ajouter(d, "c1", { type: "rect", x: 0, y: 0, w: 1, h: 1, style: {} });
  ok("ids uniques", id2 !== id && !objets.slice(0, -1).some(o => o.id === id2));
  let refus = 0;
  try { op_ajouter(d, "c2", { type: "rect", x: 0, y: 0, w: 1, h: 1 }); } catch { refus++; }
  try { op_ajouter(d, "cX", { type: "rect", x: 0, y: 0, w: 1, h: 1 }); } catch { refus++; }
  ok("refus calque verrouillé + calque inconnu", refus === 2, String(refus));
}

// ── supprimer : retire, ignore le verrouillé, rend le compte ──
{
  const d = banc();
  const n = op_supprimer(d, ["r1", "p1", "r2", "inconnu"]);
  ok("supprime 2 (r1, p1), ignore verrouillé et inconnu", n === 2, String(n));
  ok("r1 et p1 partis", !JSON.stringify(d).includes('"r1"') && !JSON.stringify(d).includes('"p1"'));
  ok("r2 (verrouillé) intact", d.calques[1].objets.length === 1);
}

// ── déplacer : rect, ellipse, path (tous les points), verrouillé ignoré ──
{
  const d = banc();
  op_deplacer(d, ["r1", "e1", "p1", "r2"], 5, -10);
  const [r, e, p] = d.calques[0].objets;
  ok("rect déplacé", r.x === 15 && r.y === 10, `${r.x},${r.y}`);
  ok("ellipse déplacée", e.cx === 305 && e.cy === 390);
  ok("path déplacé point à point",
     p.d === "M 5 -10 L 15 -10 C 15 -5 10 0 5 0 Z", p.d);
  ok("verrouillé pas déplacé", d.calques[1].objets[0].x === 0);
}

// ── redimensionner : application affine exacte bboxAvant → bboxApres ──
{
  const d = banc();
  // avant : le rect r1 exactement ; après : ×2 et décalé
  op_redimensionner(d, ["r1"], { x: 10, y: 20, w: 100, h: 50 },
                                { x: 110, y: 120, w: 200, h: 100 });
  const r = d.calques[0].objets[0];
  ok("rect redimensionné", r.x === 110 && r.y === 120 && r.w === 200 && r.h === 100,
     JSON.stringify(r));
  op_redimensionner(d, ["e1"], { x: 240, y: 310, w: 120, h: 180 },
                                { x: 0, y: 0, w: 60, h: 90 });
  const e = d.calques[0].objets[1];
  ok("ellipse redimensionnée", e.cx === 30 && e.cy === 45 && e.rx === 30 && e.ry === 45,
     JSON.stringify(e));
  op_redimensionner(d, ["p1"], { x: 0, y: 0, w: 10, h: 10 },
                                { x: 100, y: 100, w: 20, h: 20 });
  const p = d.calques[0].objets[2];
  ok("path redimensionné", p.d === "M 100 100 L 120 100 C 120 110 110 120 100 120 Z", p.d);
}

// ── tourner : compose le transform (préfixe = rotation dans le repère doc) ──
{
  const d = banc();
  op_tourner(d, ["r1"], 60, 45, 90);
  ok("rotation posée", d.calques[0].objets[0].transform === "rotate(90 60 45)",
     d.calques[0].objets[0].transform);
  op_tourner(d, ["r1"], 60, 45, 15);
  ok("rotation composée en préfixe",
     d.calques[0].objets[0].transform === "rotate(15 60 45) rotate(90 60 45)",
     d.calques[0].objets[0].transform);
}

if (echecs.length) {
  console.error("ECHECS ops :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA ops : PASS (14 controles)");
