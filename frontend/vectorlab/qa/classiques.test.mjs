// classiques.test.mjs — éditeur complet (E8) : dupliquer, miroir,
// aligner, distribuer, rayon d'angle. Les bboxes d'alignement sont
// FOURNIES par l'appelant (le DOM mesure, l'op reste pure — patron
// op_redimensionner).
import { op_dupliquer, op_miroir, op_aligner, op_distribuer,
         op_rect_rayon, chemin_parser } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

const banc = () => ({
  v: 1, taille: { w: 400, h: 300 },
  calques: [{ id: "c1", nom: "fond", visible: true, verrou: false, objets: [
    { id: "r1", type: "rect", x: 10, y: 10, w: 40, h: 20, style: {} },
    { id: "e1", type: "ellipse", cx: 100, cy: 50, rx: 20, ry: 10, style: {} },
    { id: "p1", type: "path", d: "M0 0 L10 0 C15 5 20 5 20 10", style: {} },
    { id: "t1", type: "texte", x: 50, y: 80, contenu: "abc", style: {} },
    { id: "g1", type: "groupe", enfants: [
      { id: "ga", type: "rect", x: 200, y: 200, w: 10, h: 10, style: {} }] },
  ] }],
});
const tousIds = (d) => {
  const out = [];
  (function v(objs) { for (const o of objs) { out.push(o.id);
    if (o.type === "groupe") v(o.enfants || []); } })(d.calques[0].objets);
  return out;
};

/* ── dupliquer : clones décalés, IDS NEUFS RÉCURSIFS, posés sur la source ── */
{
  const d = banc();
  const neufs = op_dupliquer(d, ["r1", "g1"], 12, 12);
  ok("dupliquer rend 2 ids neufs", neufs.length === 2
     && !neufs.includes("r1") && !neufs.includes("g1"), JSON.stringify(neufs));
  ok("7 objets de tête après", d.calques[0].objets.length === 7);
  const ids = tousIds(d);
  ok("tous les ids uniques (enfant de groupe re-identifié)",
     new Set(ids).size === ids.length && ids.filter((x) => x === "ga").length === 1,
     ids.join(","));
  const clone = d.calques[0].objets.find((o) => o.type === "rect" && o.id !== "r1"
    && o.x === 22);
  ok("clone de r1 décalé de +12", !!clone && clone.y === 22);
  const iSrc = d.calques[0].objets.findIndex((o) => o.id === "r1");
  ok("le clone se pose JUSTE AU-DESSUS de la source",
     d.calques[0].objets[iSrc + 1] === clone);
  ok("la source n'a pas bougé", d.calques[0].objets[iSrc].x === 10);
}
{
  const d = banc();
  d.calques[0].verrou = true;
  let refus = 0;
  try { op_dupliquer(d, ["r1"]); } catch { refus++; }
  ok("calque verrouillé → rien à dupliquer", refus === 1);
}

/* ── miroir : géométrie brute autour de la bbox fournie ── */
{
  const d = banc();
  const ref = { x: 10, y: 10, w: 110, h: 50 };          // centre x = 65
  op_miroir(d, ["r1", "e1"], "h", ref);
  const r1 = d.calques[0].objets[0], e1 = d.calques[0].objets[1];
  ok("miroir h : rect", r1.x === 80 && r1.y === 10, JSON.stringify(r1));
  ok("miroir h : ellipse", e1.cx === 30 && e1.cy === 50);
}
{
  const d = banc();
  op_miroir(d, ["p1"], "h", { x: 0, y: 0, w: 20, h: 10 });   // centre x = 10
  const segs = chemin_parser(d.calques[0].objets[2].d);
  ok("miroir h : path (points ET poignées)",
     segs[0].p[0] === 20 && segs[1].p[0] === 10
     && segs[2].p[0] === 5 && segs[2].p[2] === 0 && segs[2].p[4] === 0,
     d.calques[0].objets[2].d);
  ok("miroir h : y intacts", segs[2].p[1] === 5 && segs[2].p[5] === 10);
}
{
  const d = banc();
  op_miroir(d, ["r1"], "v", { x: 10, y: 10, w: 40, h: 100 }); // centre y = 60
  ok("miroir v : rect", d.calques[0].objets[0].y === 90
     && d.calques[0].objets[0].x === 10);
  op_miroir(d, ["t1"], "h", { x: 0, y: 0, w: 100, h: 100 });
  ok("miroir texte : position seule", d.calques[0].objets[3].x === 50
     && d.calques[0].objets[3].contenu === "abc");
  let refus = 0;
  try { op_miroir(d, ["r1"], "diagonale", { x: 0, y: 0, w: 1, h: 1 }); }
  catch { refus++; }
  try { op_miroir(d, ["r1"], "h", null); } catch { refus++; }
  ok("miroir : axe inconnu et bbox absente refusés", refus === 2);
}

/* ── aligner : sur la référence fournie (sélection OU page) ── */
{
  const d = banc();
  const paires = [
    { id: "r1", bbox: { x: 10, y: 10, w: 40, h: 20 } },
    { id: "e1", bbox: { x: 80, y: 40, w: 40, h: 20 } },
  ];
  const ref = { x: 0, y: 0, w: 400, h: 300 };
  op_aligner(d, paires, "gauche", ref);
  ok("aligner gauche", d.calques[0].objets[0].x === 0
     && d.calques[0].objets[1].cx === 20,
     JSON.stringify([d.calques[0].objets[0].x, d.calques[0].objets[1].cx]));
  const d2 = banc();
  op_aligner(d2, paires, "centreH", ref);
  ok("aligner centreH", d2.calques[0].objets[0].x === 180
     && d2.calques[0].objets[1].cx === 200);
  const d3 = banc();
  op_aligner(d3, paires, "bas", ref);
  ok("aligner bas", d3.calques[0].objets[0].y === 280
     && d3.calques[0].objets[1].cy === 290);
  let refus = 0;
  try { op_aligner(d3, paires, "milieu", ref); } catch { refus++; }
  ok("aligner : mode inconnu refusé", refus === 1);
}

/* ── distribuer : écarts égaux, les extrêmes ne bougent pas ── */
{
  const d = banc();
  d.calques[0].objets.push(
    { id: "dA", type: "rect", x: 0, y: 0, w: 10, h: 10, style: {} },
    { id: "dB", type: "rect", x: 15, y: 0, w: 10, h: 10, style: {} },
    { id: "dC", type: "rect", x: 50, y: 0, w: 10, h: 10, style: {} });
  const paires = [
    { id: "dA", bbox: { x: 0, y: 0, w: 10, h: 10 } },
    { id: "dB", bbox: { x: 15, y: 0, w: 10, h: 10 } },
    { id: "dC", bbox: { x: 50, y: 0, w: 10, h: 10 } },
  ];
  op_distribuer(d, paires, "h");
  const o = (id) => d.calques[0].objets.find((x) => x.id === id);
  ok("distribuer h : écarts égaux (15)", o("dA").x === 0 && o("dB").x === 25
     && o("dC").x === 50, [o("dA").x, o("dB").x, o("dC").x].join(","));
  let refus = 0;
  try { op_distribuer(d, paires.slice(0, 2), "h"); } catch { refus++; }
  ok("distribuer : moins de 3 refusé", refus === 1);
}

/* ── rayon d'angle : rects seuls, borné à min(L,H)/2 ── */
{
  const d = banc();
  ok("rayon posé sur le rect seul", op_rect_rayon(d, ["r1", "e1"], 6) === 1
     && d.calques[0].objets[0].rx === 6);
  op_rect_rayon(d, ["r1"], 999);
  ok("rayon borné à min(L,H)/2", d.calques[0].objets[0].rx === 10);
  op_rect_rayon(d, ["r1"], 0);
  ok("rayon 0 retire la clé", !("rx" in d.calques[0].objets[0]));
  let refus = 0;
  try { op_rect_rayon(d, ["e1"], 4); } catch { refus++; }
  try { op_rect_rayon(d, ["r1"], -2); } catch { refus++; }
  ok("sans rect et rayon négatif refusés", refus === 2);
}

if (echecs.length) {
  console.error("ECHECS classiques :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA classiques : PASS (19 controles)");
