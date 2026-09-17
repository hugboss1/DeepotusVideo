// formes.test.mjs — mod-formes (lot B) : les sept formes paramétriques →
// d canonique, défauts, validation des paramètres, poignées de paramètres.
// Module feuille ; les d sont relus par chemin_parser pour compter.
import { FORMES, forme_defaut, forme_params_valider, forme_d, forme_poignees,
         forme_poignee_deplacer } from "../js/mod-formes.js";
import { chemin_parser } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (a, b, tol = 1e-6) => Math.abs(a - b) <= tol;
const bbox = (d) => { let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; for (const s of chemin_parser(d)) for (let k = 0; k < s.p.length; k += 2) { x0 = Math.min(x0, s.p[k]); x1 = Math.max(x1, s.p[k]); y0 = Math.min(y0, s.p[k + 1]); y1 = Math.max(y1, s.p[k + 1]); } return { x0, y0, x1, y1 }; };
const nM = (d) => (d.match(/M /g) || []).length, nL = (d) => (d.match(/L /g) || []).length, nZ = (d) => (d.match(/Z/g) || []).length;

ok("FORMES : 7 entrées {id, nom}, ids uniques", FORMES.length === 7 && new Set(FORMES.map((f) => f.id)).size === 7
   && ["polygone", "etoile", "engrenage", "fleche", "donut", "spirale", "hexagone"].every((id) => FORMES.some((f) => f.id === id)));
{
  const o = forme_defaut("polygone", 100, 100, 50);
  ok("défaut polygone : type forme, centre, rayon, 6 côtés", o.type === "forme" && o.forme === "polygone" && o.cx === 100 && o.r === 50 && o.params.n === 6, JSON.stringify(o));
  const d = forme_d(o);
  ok("polygone 6 : M + 5 L + Z, premier sommet en haut (angle −90°)", nM(d) === 1 && nL(d) === 5 && nZ(d) === 1 && d.startsWith("M 100 50"), d);
  const b = bbox(d);
  ok("polygone inscrit dans le rayon", pres(b.y0, 50) && pres(b.y1, 150) && b.x1 - b.x0 < 100.01);
  const h = forme_defaut("hexagone", 0, 0, 10);
  ok("hexagone = polygone à 6 côtés", h.forme === "polygone" && h.params.n === 6);
  ok("polygone n=3 : 3 sommets", nL(forme_d({ ...o, params: { n: 3 } })) === 2);
}
{
  const o = forme_defaut("etoile", 0, 0, 100);
  ok("défaut étoile : 5 branches, ratio 0,5", o.params.n === 5 && pres(o.params.ratio, 0.5));
  const d = forme_d(o);
  ok("étoile 5 : 10 sommets", nL(d) === 9 && nZ(d) === 1, d);
  const pts = chemin_parser(d).filter((s) => s.c !== "Z").map((s) => Math.hypot(s.p[0], s.p[1]));
  // le d est arrondi à 2 décimales : c'est le contrat — tolérance 0,02
  ok("rayons alternés 100 / 50", pts.every((r, i) => pres(r, i % 2 === 0 ? 100 : 50, 0.02)), pts.map((v) => v.toFixed(1)).join(","));
}
{
  const o = forme_defaut("engrenage", 0, 0, 100);
  const d = forme_d(o);
  ok("engrenage : 4 sommets par dent, fermé", nL(d) === o.params.dents * 4 - 1 && nZ(d) === 1, `${nL(d)} / ${o.params.dents}`);
  const rayons = chemin_parser(d).filter((s) => s.c !== "Z").map((s) => Math.hypot(s.p[0], s.p[1]));
  ok("rayons : extérieur 100, intérieur 100 − profondeur", pres(Math.max(...rayons), 100, 0.02) && pres(Math.min(...rayons), 100 - o.params.profondeur, 0.02));
}
{
  const o = forme_defaut("fleche", 0, 0, 100);
  const d = forme_d(o);
  ok("flèche : 7 sommets, pointe à droite (x max = +longueur/2)", nL(d) === 6 && nZ(d) === 1 && pres(bbox(d).x1, 100), d);
  ok("flèche : hauteur = tête", pres(bbox(d).y1 - bbox(d).y0, o.params.tete));
}
{
  const o = forme_defaut("donut", 0, 0, 100);
  const d = forme_d(o);
  ok("donut : deux anneaux (2 M, 2 Z), evenodd", nM(d) === 2 && nZ(d) === 2 && o.style && o.style.regle === "evenodd", d.slice(0, 60));
  const rayons = chemin_parser(d).filter((s) => s.c === "C").map((s) => Math.hypot(s.p[4], s.p[5]));
  ok("rayons 100 et 50 (ratio 0,5)", pres(Math.max(...rayons), 100, 1e-6) && pres(Math.min(...rayons), 50, 1e-6));
}
{
  const o = forme_defaut("spirale", 0, 0, 100);
  const d = forme_d(o);
  ok("spirale : chemin OUVERT, contour seul, part du centre", !d.includes("Z") && d.startsWith("M 0 0") && o.style.fond === "none", d.slice(0, 40));
  ok("spirale : le dernier point est au rayon", pres(Math.hypot(...chemin_parser(d).at(-1).p.slice(-2)), 100, 0.5));
  const f = forme_d({ ...o, params: { ...o.params, type: "fibonacci" } });
  ok("spirale fibonacci : autre courbe, même rayon final", f !== d && pres(Math.hypot(...chemin_parser(f).at(-1).p.slice(-2)), 100, 0.5));
}
{
  let refus = 0;
  for (const [f, p] of [["polygone", { n: 2 }], ["etoile", { n: 5, ratio: 1.5 }], ["engrenage", { dents: 2, profondeur: 5 }], ["fleche", { longueur: -1 }], ["donut", { ratio: 0 }], ["spirale", { tours: 0 }], ["nuage", {}]]) {
    try { forme_params_valider(f, { ...forme_defaut(f === "nuage" ? "polygone" : f, 0, 0, 10).params, ...p }); } catch { refus++; }
  }
  ok("7 paramètres invalides refusés", refus === 7, String(refus));
  let refusD = false; try { forme_d({ type: "forme", forme: "polygone", cx: 0, cy: 0, r: 0, params: { n: 4 } }); } catch { refusD = true; }
  ok("rayon nul refusé", refusD);
}
/* ── poignées : rayon (et ratio pour l'étoile / donut) ── */
{
  const o = forme_defaut("etoile", 100, 100, 50);
  const pg = forme_poignees(o);
  ok("étoile : deux poignées, rayon (en haut) et ratio", pg.length === 2 && pg.some((p) => p.cle === "r" && pres(p.x, 100) && pres(p.y, 50)) && pg.some((p) => p.cle === "ratio"), JSON.stringify(pg));
  const patch = forme_poignee_deplacer(o, "r", 100, 20);
  ok("tirer la poignée du rayon → r = 80", pres(patch.r, 80), JSON.stringify(patch));
  const pr = forme_poignee_deplacer(o, "ratio", 100 + 20 * Math.cos(-Math.PI / 2 + Math.PI / 5), 100 + 20 * Math.sin(-Math.PI / 2 + Math.PI / 5));
  ok("tirer la poignée du ratio → ratio = 0,4 (20/50), borné ]0,1[", pres(pr.params.ratio, 0.4, 1e-6), JSON.stringify(pr));
  ok("polygone : une seule poignée (rayon)", forme_poignees(forme_defaut("polygone", 0, 0, 10)).length === 1);
  let refus = false; try { forme_poignee_deplacer(o, "zzz", 0, 0); } catch { refus = true; }
  ok("poignée inconnue refusée", refus);
}

if (echecs.length) {
  console.error("ECHECS formes :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA formes : PASS (25 controles)");
