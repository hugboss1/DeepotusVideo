// traces.test.mjs — lot D1 « Tracés » (t422…) : les commandes de tracé reprises d'Illustrator, opérations PURES de
// js/mod-traces.js. Martinez vendorisé en vrai, comme opsbool2.
// T1 (t422) Vectoriser le contour : le trait devient une surface pleine de la couleur du trait ; un objet rempli
// devient un groupe [fond sans contour, contour vectorisé] à la même place ; refus sans trace.
// T2 (t423) Simplifier : moins de points, forme tenue, angles gardés, jamais plus de points que l'original.
import { createRequire } from "node:module";
import { fournirMartinez, aplatir_objet, versMulti, aire_multi } from "../js/mod-bool.js";
import { op_contour_vectoriser, op_simplifier, simplifier_apercu } from "../js/mod-traces.js";
import { chemin_parser } from "../js/mod-doc.js";
import { T } from "../js/mod-i18n.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
const pres = (a, b, pct) => Math.abs(a - b) <= Math.abs(b) * pct / 100;
const doc = (...objets) => ({ v: 1, taille: { w: 400, h: 400 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets }] });
const objets = (d) => d.calques[0].objets;
const aire = (o) => aire_multi(versMulti(aplatir_objet(o)));
const tousIds = (d) => { const out = []; (function v(l) { for (const o of l) { out.push(o.id); if (o.type === "groupe") v(o.enfants || []); } })(objets(d)); return out; };
const refus = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };

/* ── T1 : Vectoriser le contour ── */
{
  // carré 100 sans fond, trait 10 : anneau 110² − 90² = 4000, dont les 4 coins carrés 5 × 5 deviennent des quarts de disque (joints ronds) : 4000 − 100 + π·5²
  const d = doc({ id: "a", type: "rect", x: 0, y: 0, w: 50, h: 50, style: { fond: "#eee" } },
                { id: "r", type: "rect", x: 100, y: 100, w: 100, h: 100,
                  style: { fond: "none", contour: "#123456", epaisseur: 10, opacite: 0.5 } },
                { id: "z", type: "rect", x: 0, y: 300, w: 10, h: 10, style: { fond: "#eee" } });
  const ids = op_contour_vectoriser(d, ["r"]);
  const o = objets(d)[1];
  ok("T1 carré sans fond : un seul chemin rendu, à la place de l'original", ids.length === 1 && objets(d).length === 3
     && o.id === ids[0] && o.type === "path", JSON.stringify(ids));
  ok("T1 le chemin prend la couleur du trait en fond, sans contour", o.style.fond === "#123456"
     && (o.style.contour === "none" || o.style.contour === undefined), JSON.stringify(o.style));
  ok("T1 l'opacité de l'objet est gardée", o.style.opacite === 0.5, JSON.stringify(o.style));
  ok("T1 aire = 4000 − 100 + π·25 (± 0,5 %)", pres(aire(o), 3900 + Math.PI * 25, 0.5), aire(o));
  ok("T1 l'anneau a un trou (le carré intérieur)", aplatir_objet(o).length === 2, aplatir_objet(o).length);
  ok("T1 les voisins ne bougent pas", objets(d)[0].id === "a" && objets(d)[2].id === "z");
  ok("T1 aucun id en double", new Set(tousIds(d)).size === tousIds(d).length, tousIds(d));
}
{
  // ligne ouverte : un seul anneau, bouts ronds
  const d = doc({ id: "l", type: "path", d: "M 0 0 L 100 0", style: { fond: "none", contour: "#000000", epaisseur: 4 } });
  const [id] = op_contour_vectoriser(d, ["l"]);
  const o = objets(d)[0];
  ok("T1 ligne ouverte : un anneau", o.id === id && aplatir_objet(o).length === 1, aplatir_objet(o).length);
  ok("T1 ligne ouverte : aire = 400 + π·4 (± 0,5 %)", pres(aire(o), 400 + Math.PI * 4, 0.5), aire(o));
}
{
  // objet rempli ET tracé : groupe [fond sans contour, contour vectorisé], à la même place
  const d = doc({ id: "a", type: "rect", x: 0, y: 0, w: 5, h: 5, style: { fond: "#eee" } },
                { id: "r", type: "rect", x: 10, y: 10, w: 100, h: 50,
                  style: { fond: "#ff0000", contour: "#000000", epaisseur: 2,
                           contours: [{ couleur: "#00ff00", epaisseur: 6 }] } });
  const [gid] = op_contour_vectoriser(d, ["r"]);
  const g = objets(d)[1];
  ok("T1 objet rempli : un groupe à la même place", g.id === gid && g.type === "groupe" && objets(d).length === 2
     && (g.enfants || []).length === 2, JSON.stringify(g).slice(0, 200));
  const [fond, trait] = g.enfants || [];
  ok("T1 l'enfant du bas est le fond, sans contour, id d'origine", fond && fond.id === "r" && fond.type === "rect"
     && fond.style.fond === "#ff0000" && (fond.style.contour === "none" || fond.style.contour === undefined),
     JSON.stringify(fond));
  ok("T1 l'enfant du haut est le contour vectorisé, sans les contours d'Apparence +", trait && trait.type === "path"
     && trait.style.fond === "#000000" && !trait.style.contours, JSON.stringify(trait && trait.style));
  ok("T1 les contours d'Apparence + restent sur le fond", fond && Array.isArray(fond.style.contours)
     && fond.style.contours.length === 1);
  ok("T1 aire du contour = 102 × 52 − 98 × 48 − 4 + π (± 0,5 %)", trait && pres(aire(trait), 596 + Math.PI, 0.5),
     trait && aire(trait));
  ok("T1 ids distincts (groupe, fond, contour)", new Set(tousIds(d)).size === tousIds(d).length, tousIds(d));
}
{
  // transform appliqué : le chemin vectorisé est en coordonnées du document, sans transform ; le fond garde le sien
  const d = doc({ id: "r", type: "rect", x: 0, y: 0, w: 100, h: 20, transform: "rotate(90 0 0)",
                  style: { fond: "#ff0000", contour: "#000000", epaisseur: 2 } });
  op_contour_vectoriser(d, ["r"]);
  const [fond, trait] = objets(d)[0].enfants;
  const xs = aplatir_objet(trait).flat().map((p) => p[0]);
  ok("T1 rotation : le contour est déjà tourné (x dans [-21, 1]) et sans transform", !trait.transform
     && Math.min(...xs) >= -21.01 && Math.max(...xs) <= 1.01, `${Math.min(...xs)}..${Math.max(...xs)}`);
  ok("T1 rotation : le fond garde son transform", fond.transform === "rotate(90 0 0)");
}
{
  // sélection mêlée : seul l'objet tracé est vectorisé
  const d = doc({ id: "p", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#eee" } },
                { id: "q", type: "ellipse", cx: 50, cy: 50, rx: 20, ry: 10, style: { fond: "none", contour: "#000", epaisseur: 1 } });
  const ids = op_contour_vectoriser(d, ["p", "q"]);
  ok("T1 sélection mêlée : l'objet sans trait est laissé tel quel", ids.length === 1
     && JSON.stringify(objets(d)[0]) === JSON.stringify({ id: "p", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#eee" } })
     && objets(d)[1].type === "path", JSON.stringify(ids));
}
/* refus : rien de vectorisable → message traduit, document intact */
{
  const cas = [
    ["sans trait", { id: "a", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#eee" } }],
    ["trait d'épaisseur 0", { id: "a", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "none", contour: "#000", epaisseur: 0 } }],
    ["trait en pointillés", { id: "a", type: "path", d: "M 0 0 L 50 0", style: { fond: "none", contour: "#000", epaisseur: 2, pointilles: "6 4" } }],
    ["texte", { id: "a", type: "texte", x: 0, y: 0, texte: "Bonjour", style: { fond: "none", contour: "#000", epaisseur: 1 } }],
  ];
  for (const [nom, o] of cas) {
    const d = doc(o), avant = JSON.stringify(d);
    const m = refus(() => op_contour_vectoriser(d, ["a"]));
    ok(`T1 refus (${nom}) : message traduit`, m === T("vectorlab.traces.sans_contour"), m);
    ok(`T1 refus (${nom}) : document intact`, JSON.stringify(d) === avant);
  }
  ok("T1 la clé du refus existe dans le dictionnaire", T("vectorlab.traces.sans_contour") !== "vectorlab.traces.sans_contour");
  const v = doc({ id: "a", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "none", contour: "#000", epaisseur: 2 } });
  v.calques[0].verrou = true;
  const avantV = JSON.stringify(v);
  ok("T1 calque verrouillé : refus et document intact", refus(() => op_contour_vectoriser(v, ["a"])) !== null
     && JSON.stringify(v) === avantV);
}

/* ── T2 : Simplifier ── */
// points d'ancrage : par sous-chemin, le M et chaque fin de segment ; un retour EXPLICITE au départ avant Z ne compte pas
const ancres = (d) => { let n = 0, sous = [];
  const fin = () => { if (sous.length > 1 && sous.ferme) { const a = sous[0], b = sous[sous.length - 1]; if (Math.abs(a[0] - b[0]) < 1e-6 && Math.abs(a[1] - b[1]) < 1e-6) sous.pop(); } n += sous.length; sous = []; };
  for (const g of chemin_parser(d)) { if (g.c === "M") { fin(); sous.push(g.p.slice(0, 2)); } else if (g.c === "Z") { sous.ferme = true; fin(); } else sous.push(g.p.slice(-2)); }
  fin(); return n; };
const polyD = (pts, fermer) => "M " + pts.map((p) => p.map((v) => v.toFixed(3)).join(" ")).join(" L ") + (fermer ? " Z" : "");
const cercle = (n, r = 50, cx = 100, cy = 100) => Array.from({ length: n }, (_, k) => [cx + r * Math.cos(2 * Math.PI * k / n), cy + r * Math.sin(2 * Math.PI * k / n)]);
const bbox = (o) => { const p = aplatir_objet(o).flat(); const xs = p.map((q) => q[0]), ys = p.map((q) => q[1]); return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]; };
{
  const d = doc({ id: "c", type: "path", d: polyD(cercle(200), true), style: { fond: "#0047AB", contour: "#000", epaisseur: 1 }, nom: "Cercle" });
  const avant = ancres(objets(d)[0].d);
  const ap = simplifier_apercu(objets(d)[0], { precision: 50 });
  ok("T2 aperçu : nombre de points avant → après", ap.avant === avant && ap.apres < avant && ap.apres === ancres(ap.d), JSON.stringify([ap.avant, ap.apres]));
  const ids = op_simplifier(d, ["c"], { precision: 50 });
  const o = objets(d)[0];
  ok("T2 cercle de 200 points → au moins 10 fois moins de points (mesuré : 16)", ids.length === 1 && ancres(o.d) <= 20 && ancres(o.d) >= 4, ancres(o.d));
  ok("T2 cercle : aire tenue (± 1 %)", pres(aire(o), Math.PI * 2500, 1), aire(o));
  const b = bbox(o);
  ok("T2 cercle : boîte tenue (± 1,5 px)", Math.abs(b[0] - 50) <= 1.5 && Math.abs(b[1] - 50) <= 1.5 && Math.abs(b[2] - 150) <= 1.5 && Math.abs(b[3] - 150) <= 1.5, JSON.stringify(b));
  ok("T2 cercle : courbes, fermé", /C/.test(o.d) && /Z\s*$/.test(o.d), o.d.slice(0, 80));
  ok("T2 id, nom et style gardés", o.id === "c" && o.nom === "Cercle" && o.style.fond === "#0047AB" && o.style.epaisseur === 1);
  ok("T2 l'aperçu rend exactement ce que pose la commande", o.d === ap.d);
}
{
  const d0 = polyD(cercle(200), true);
  const d = doc({ id: "c", type: "path", d: d0, style: { fond: "#eee" } });
  const m = refus(() => op_simplifier(d, ["c"], { precision: 100 }));
  ok("T2 précision 100 % : rien à gagner, refus « déjà simple », tracé inchangé", m === T("vectorlab.traces.simplifier_deja") && objets(d)[0].d === d0, m);
}
{
  // carré dont les côtés portent 40 points alignés : 4 angles, côtés droits, aire exacte
  const pts = [];
  for (const [a, b] of [[[0, 0], [100, 0]], [[100, 0], [100, 100]], [[100, 100], [0, 100]], [[0, 100], [0, 0]]]) {
    for (let k = 0; k < 10; k++) pts.push([a[0] + (b[0] - a[0]) * k / 10, a[1] + (b[1] - a[1]) * k / 10]);
  }
  const d = doc({ id: "q", type: "path", d: polyD(pts, true), style: { fond: "#eee" } });
  op_simplifier(d, ["q"], { precision: 50 });
  const o = objets(d)[0];
  ok("T2 carré : 4 points (les angles sont gardés)", ancres(o.d) === 4, o.d);
  ok("T2 carré : aire exacte (± 0,1 %)", pres(aire(o), 10000, 0.1), aire(o));
  ok("T2 carré : entre deux angles, un segment droit (L), pas une courbe", !/C/.test(o.d), o.d);
  const e = doc({ id: "q", type: "path", d: polyD(pts, true), style: { fond: "#eee" } });
  op_simplifier(e, ["q"], { precision: 50, droites: true });
  ok("T2 lignes droites : que des segments L", !/C/.test(objets(e)[0].d) && ancres(objets(e)[0].d) === 4, objets(e)[0].d);
}
{
  // ligne bruitée ouverte (± 0,2 px) : deux points, pas de fermeture
  const pts = Array.from({ length: 100 }, (_, k) => [k * 3, (k % 2 ? 0.2 : -0.2)]);
  const d = doc({ id: "l", type: "path", d: polyD(pts, false), style: { fond: "none", contour: "#000", epaisseur: 1 } });
  op_simplifier(d, ["l"], { precision: 50 });
  const o = objets(d)[0];
  ok("T2 ligne bruitée : 2 points, ouverte", ancres(o.d) === 2 && !/Z/.test(o.d), o.d);
}
{
  // deux sous-chemins : deux M ; le transform est gardé, la géométrie reste locale
  const d = doc({ id: "p", type: "path", d: polyD(cercle(120, 20, 30, 30), true) + " " + polyD(cercle(120, 20, 130, 30), true),
                  transform: "rotate(30 80 30)", style: { fond: "#eee" } });
  op_simplifier(d, ["p"], { precision: 50 });
  const o = objets(d)[0];
  ok("T2 deux sous-chemins gardés", chemin_parser(o.d).filter((s) => s.c === "M").length === 2, o.d.slice(0, 60));
  ok("T2 transform gardé tel quel", o.transform === "rotate(30 80 30)");
  const ms = chemin_parser(o.d).filter((s) => s.c === "M").map((s) => s.p);
  ok("T2 géométrie restée locale : chaque sous-chemin part de son point d'origine NON tourné (50 30) et (150 30)",
     Math.hypot(ms[0][0] - 50, ms[0][1] - 30) < 0.5 && Math.hypot(ms[1][0] - 150, ms[1][1] - 30) < 0.5, JSON.stringify(ms));
}
{
  // jamais PLUS de points : un cercle en 4 cubiques reste tel quel ; une forme / ellipse non plus
  const k = 27.6142;
  const d4 = `M 50 0 C 50 ${k} ${k} 50 0 50 C ${-k} 50 -50 ${k} -50 0 C -50 ${-k} ${-k} -50 0 -50 C ${k} -50 50 ${-k} 50 0 Z`;
  const d = doc({ id: "a", type: "path", d: d4, style: { fond: "#eee" } }, { id: "e", type: "ellipse", cx: 0, cy: 0, rx: 30, ry: 20, style: { fond: "#eee" } });
  const avant = JSON.stringify(d);
  const m = refus(() => op_simplifier(d, ["a", "e"], { precision: 50 }));
  ok("T2 rien à gagner : refus « déjà simple » et document intact", m === T("vectorlab.traces.simplifier_deja") && JSON.stringify(d) === avant, m);
}
{
  // une forme paramétrique devient un chemin quand elle gagne à être simplifiée ; texte et groupe sont ignorés
  const pts = cercle(300);
  const d = doc({ id: "t", type: "texte", x: 0, y: 0, texte: "A", style: { fond: "#000" } },
                { id: "p", type: "path", d: polyD(pts, true), style: { fond: "#eee" } });
  const ids = op_simplifier(d, ["t", "p"], { precision: 30 });
  ok("T2 sélection mêlée : seul le tracé change", ids.length === 1 && ids[0] === "p" && objets(d)[0].type === "texte");
  const v = doc({ id: "t", type: "texte", x: 0, y: 0, texte: "A", style: { fond: "#000" } });
  const avantV = JSON.stringify(v);
  ok("T2 rien de simplifiable : refus traduit, document intact", refus(() => op_simplifier(v, ["t"], { precision: 50 })) === T("vectorlab.traces.simplifier_rien") && JSON.stringify(v) === avantV);
  ok("T2 les clés existent", T("vectorlab.traces.simplifier_rien") !== "vectorlab.traces.simplifier_rien" && T("vectorlab.traces.simplifier_deja") !== "vectorlab.traces.simplifier_deja");
  // précision plus basse = moins de points
  const a = simplifier_apercu({ id: "x", type: "path", d: polyD(cercle(300), true), style: {} }, { precision: 20 });
  const b = simplifier_apercu({ id: "x", type: "path", d: polyD(cercle(300), true), style: {} }, { precision: 80 });
  ok("T2 précision 20 % donne moins de points que 80 %", a.apres < b.apres, JSON.stringify([a.apres, b.apres]));
}

if (echecs.length) {
  console.error(`traces : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("traces : ok");
