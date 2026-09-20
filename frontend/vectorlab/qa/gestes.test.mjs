// gestes.test.mjs — mod-doc, lot B : l'objet forme dans le modèle (valide,
// compilé, déplacé, redimensionné en sx/sy, réfléchi), op_forme_param,
// op_forme_en_chemin, inclinaison, duplication puissance, sélection par
// attribut, formules du panneau, historique 1000 pas et instantanés nommés.
import { parserDoc, compilerSVG, op_deplacer, op_redimensionner, op_miroir, op_forme_param,
         op_forme_en_chemin, op_incliner, op_dupliquer_puissance, selection_par_attribut,
         formule, Historique } from "../js/mod-doc.js";
import { forme_defaut } from "../js/mod-formes.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (a, b, tol = 1e-6) => Math.abs(a - b) <= tol;
const base = (...objets) => ({ v: 1, nom: "G", taille: { w: 400, h: 400 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets }] });
const rect = (id, x, y, w, h, style = { fond: "#0047AB" }) => ({ id, type: "rect", x, y, w, h, style });

/* ── forme dans le modèle ── */
{
  const f = { ...forme_defaut("etoile", 100, 100, 50), id: "f" };
  const d = base(f);
  ok("parserDoc accepte une forme", (() => { try { parserDoc(d); return true; } catch { return false; } })());
  const svg = compilerSVG(d);
  ok("compile en <path data-forme> au d de la forme", svg.includes('<path data-objet="f" data-forme="etoile" d="M 100 50'), svg.slice(0, 200));
  op_deplacer(d, ["f"], 10, -5);
  ok("déplacer une forme : son centre bouge", f.cx === 110 && f.cy === 95);
  op_redimensionner(d, ["f"], { x: 60, y: 45, w: 100, h: 100 }, { x: 60, y: 45, w: 50, h: 100 });
  ok("redimensionner : sx/sy portent l'échelle, le centre suit", pres(f.sx, 0.5) && pres(f.sy, 1) && pres(f.cx, 85), JSON.stringify(f));
  op_miroir(d, ["f"], "h", { x: 0, y: 0, w: 400, h: 400 });
  ok("miroir h : centre réfléchi", pres(f.cx, 315));
  op_forme_param(d, "f", { r: 30, params: { n: 7, ratio: 0.3 } });
  ok("op_forme_param fusionne rayon et params", f.r === 30 && f.params.n === 7 && f.params.ratio === 0.3);
  let refus = 0;
  try { op_forme_param(d, "f", { params: { n: 2 } }); } catch { refus++; }
  const m = base({ ...forme_defaut("polygone", 0, 0, 10), id: "x", params: { n: 1 } });
  try { parserDoc(m); } catch { refus++; }
  ok("paramètres invalides refusés par la commande ET par parserDoc", refus === 2, String(refus));
  const id = op_forme_en_chemin(d, "f");
  const o = d.calques[0].objets[0];
  ok("convertir en courbes : même id, type path, d figé, plus de params", id === "f" && o.type === "path" && o.d.startsWith("M ") && o.params === undefined, JSON.stringify(o).slice(0, 120));
}
/* ── inclinaison ── */
{
  const d = base(rect("r", 0, 0, 100, 50));
  op_incliner(d, ["r"], 20, 0, 50, 25);
  ok("incliner : skewX autour du centre", d.calques[0].objets[0].transform === "translate(50 25) skewX(20) translate(-50 -25)", d.calques[0].objets[0].transform);
  op_incliner(d, ["r"], 0, 10, 50, 25);
  ok("une seconde inclinaison se compose devant", d.calques[0].objets[0].transform.startsWith("translate(50 25) skewY(10) translate(-50 -25) translate(50 25) skewX(20)"));
  let refus = 0; try { op_incliner(d, ["r"], 90, 0, 0, 0); } catch { refus++; }
  ok("|angle| ≥ 89° refusé", refus === 1);
}
/* ── duplication puissance ── */
{
  const d = base(rect("r", 0, 0, 20, 20));
  const ids = op_dupliquer_puissance(d, ["r"], 3, { dx: 30, dy: 0, rotation: 0, echelle: 1 });
  const xs = d.calques[0].objets.map((o) => o.x);
  ok("3 copies décalées de 30 chacune", ids.length === 3 && JSON.stringify(xs) === "[0,30,60,90]", JSON.stringify(xs));
  const e = base(rect("r", 0, 0, 20, 20));
  op_dupliquer_puissance(e, ["r"], 2, { dx: 0, dy: 0, rotation: 15, echelle: 1 });
  ok("rotation cumulée : 15° puis 30° autour du centre", /rotate\(15 /.test(e.calques[0].objets[1].transform) && /rotate\(30 /.test(e.calques[0].objets[2].transform), JSON.stringify(e.calques[0].objets.map((o) => o.transform)));
  const g = base(rect("r", 0, 0, 20, 20));
  op_dupliquer_puissance(g, ["r"], 2, { dx: 0, dy: 0, rotation: 0, echelle: 0.5 });
  ok("échelle cumulée : 10 puis 5 de côté, autour du centre", pres(g.calques[0].objets[1].w, 10) && pres(g.calques[0].objets[2].w, 5) && pres(g.calques[0].objets[2].x + 2.5, 10), JSON.stringify(g.calques[0].objets.map((o) => [o.x, o.w])));
  let refus = 0; try { op_dupliquer_puissance(g, ["r"], 0, { dx: 1 }); } catch { refus++; }
  try { op_dupliquer_puissance(g, ["r"], 500, { dx: 1 }); } catch { refus++; }
  ok("n hors 1..200 refusé", refus === 2);
}
/* ── sélection par attribut ── */
{
  const d = base(rect("a", 0, 0, 1, 1, { fond: "#111", contour: "#000" }), rect("b", 0, 0, 1, 1, { fond: "#111" }),
                 { id: "c", type: "ellipse", cx: 0, cy: 0, rx: 1, ry: 1, style: { fond: "#222", contour: "#000" } }, rect("e", 0, 0, 1, 1, { fond: "#333" }));
  ok("même fond que a : a, b", JSON.stringify(selection_par_attribut(d, "a", "fond")) === '["a","b"]');
  ok("même contour que a : a, c", JSON.stringify(selection_par_attribut(d, "a", "contour")) === '["a","c"]');
  ok("même type que a : a, b, e", JSON.stringify(selection_par_attribut(d, "a", "type")) === '["a","b","e"]');
  ok("un calque verrouillé n'est pas sélectionnable", (() => { const e = JSON.parse(JSON.stringify(d)); e.calques.push({ id: "c2", verrou: true, visible: true, objets: [rect("z", 0, 0, 1, 1, { fond: "#111" })] }); return !selection_par_attribut(e, "a", "fond").includes("z"); })());
  let refus = 0; try { selection_par_attribut(d, "zz", "fond"); } catch { refus++; }
  try { selection_par_attribut(d, "a", "poids"); } catch { refus++; }
  ok("référence inconnue ou clé inconnue refusées", refus === 2);
}
/* ── formules ── */
{
  ok("+50 % → 150 ; −25 % → 75 ; ×2 → 200 ; /4 → 25", formule(100, "+50%") === 150 && formule(100, "-25%") === 75 && formule(100, "*2") === 200 && formule(100, "/4") === 25);
  ok("10+5 → 15 (expression absolue) ; 42 → 42 ; +10 → 110 ; virgule décimale", formule(100, "10+5") === 15 && formule(100, "42") === 42 && formule(100, "+10") === 110 && formule(100, "2,5*2") === 5);
  let refus = 0; for (const t of ["abc", "", "1e9e", "alert(1)", "2**"]) { try { formule(100, t); } catch { refus++; } }
  ok("texte illisible ou code refusé (5 cas)", refus === 5, String(refus));
}
/* ── historique 1000 et instantanés nommés ── */
{
  const h = new Historique();
  ok("1000 pas par défaut", h.cap === 1000);
  const d = base(rect("r", 0, 0, 1, 1));
  for (let i = 0; i < 1005; i++) { d.calques[0].objets[0].x = i; h.capturer(d); }
  ok("la pile se borne à 1000", h._avant.length === 1000);
  h.instantane("avant retouche", d);
  d.calques[0].objets[0].x = 9999;
  const r = h.restaurer("avant retouche");
  ok("instantané nommé : un clone qui ignore la mutation postérieure, listé", r.calques[0].objets[0].x === 1004 && h.instantanes().includes("avant retouche") && r !== d);
  let refus = 0; try { h.restaurer("inconnu"); } catch { refus++; }
  try { h.instantane("", d); } catch { refus++; }
  ok("instantané inconnu / nom vide refusés", refus === 2);
}

if (echecs.length) {
  console.error("ECHECS gestes :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA gestes : PASS (26 controles)");
