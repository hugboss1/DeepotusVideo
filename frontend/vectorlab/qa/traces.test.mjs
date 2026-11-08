// traces.test.mjs — lot D1 « Tracés » (t422…) : les commandes de tracé reprises d'Illustrator, opérations PURES de
// js/mod-traces.js. Martinez vendorisé en vrai, comme opsbool2.
// T1 (t422) Vectoriser le contour : le trait devient une surface pleine de la couleur du trait ; un objet rempli
// devient un groupe [fond sans contour, contour vectorisé] à la même place ; refus sans trace.
// T2 (t423) Simplifier : moins de points, forme tenue, angles gardés, jamais plus de points que l'original.
// T3 (t424) Ajouter des points d'ancrage : un point au milieu de chaque segment, segment de fermeture compris ; forme identique.
// T4 (t425) Moyenne : les nœuds choisis vont à leur position moyenne — horizontale (même y), verticale (même x) ou les deux.
// T5 (t426) Nettoyer : points isolés, objets invisibles, textes vides retirés du document entier ; liens et masques protégés.
// T6 (t427) Diviser les objets en dessous : le tracé du dessus découpe chaque objet rempli situé SOUS lui, puis disparaît.
// T7 (t428) Lignes et colonnes : la boîte de l'objet devient une grille de rectangles séparés par des gouttières, repères en option.
import { createRequire } from "node:module";
import { fournirMartinez, aplatir_objet, versMulti, aire_multi } from "../js/mod-bool.js";
import { op_contour_vectoriser, op_simplifier, simplifier_apercu, op_points_ajouter, compter_ancres, op_noeuds_moyenne, op_nettoyer, op_diviser_dessous, op_lignes_colonnes } from "../js/mod-traces.js";
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
const tousIdsDoc = (d) => { const out = []; for (const c of d.calques) (function v(l) { for (const o of l) { out.push(o.id); if (o.type === "groupe") v(o.enfants || []); } })(c.objets); return out; };
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

/* ── T3 : Ajouter des points d'ancrage ── */
// distance d'un point au tracé aplati (pour vérifier qu'un point neuf est SUR la forme d'origine)
const surTrace = (o, pt) => Math.min(...aplatir_objet(o).map((ring) => Math.min(...ring.slice(0, -1).map((a, k) => {
  const b = ring[k + 1], dx = b[0] - a[0], dy = b[1] - a[1], l2 = dx * dx + dy * dy;
  const t = l2 ? Math.max(0, Math.min(1, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy) / l2)) : 0;
  return Math.hypot(pt[0] - a[0] - t * dx, pt[1] - a[1] - t * dy); }))));
const finsDe = (d) => chemin_parser(d).filter((g) => g.c !== "Z").map((g) => g.p.slice(-2));
{
  // rectangle : 4 → 8 points, aire identique, chaque milieu sur un côté ; devient un chemin, id / style / transform gardés
  const d = doc({ id: "r", type: "rect", x: 10, y: 20, w: 100, h: 50, transform: "rotate(15 60 45)", nom: "R",
                  style: { fond: "#0047AB", contour: "#000", epaisseur: 2 } });
  const avant = { ...objets(d)[0] };
  const ids = op_points_ajouter(d, ["r"]);
  const o = objets(d)[0];
  ok("T3 rectangle : 8 points", ids.length === 1 && o.type === "path" && compter_ancres(o.d) === 8, o.d);
  ok("T3 rectangle : aire identique", pres(aire(o), aire(avant), 0.01), [aire(o), aire(avant)]);
  ok("T3 rectangle : les milieux des 4 côtés, segment de fermeture compris",
     JSON.stringify(finsDe(o.d)) === JSON.stringify([[10, 20], [60, 20], [110, 20], [110, 45], [110, 70], [60, 70], [10, 70], [10, 45]]), JSON.stringify(finsDe(o.d)));
  ok("T3 id, nom, style et transform gardés", o.id === "r" && o.nom === "R" && o.style.fond === "#0047AB" && o.transform === "rotate(15 60 45)");
}
{
  // cercle en 4 cubiques : 8 cubiques, chaque point neuf sur le cercle, aire identique
  const k = 27.6142;
  const d4 = `M 50 0 C 50 ${k} ${k} 50 0 50 C ${-k} 50 -50 ${k} -50 0 C -50 ${-k} ${-k} -50 0 -50 C ${k} -50 50 ${-k} 50 0 Z`;
  const d = doc({ id: "c", type: "path", d: d4, style: { fond: "#eee" } });
  const ref = { id: "x", type: "path", d: d4, style: {} };
  op_points_ajouter(d, ["c"]);
  const o = objets(d)[0];
  ok("T3 cercle : 8 points, que des cubiques", compter_ancres(o.d) === 8 && chemin_parser(o.d).filter((g) => g.c === "C").length === 8, o.d);
  ok("T3 cercle : chaque point est sur le cercle d'origine (≤ 0,3 px)", finsDe(o.d).every((pt) => surTrace(ref, pt) <= 0.3), JSON.stringify(finsDe(o.d)));
  ok("T3 cercle : aire identique (± 0,05 %)", pres(aire(o), aire(ref), 0.05), [aire(o), aire(ref)]);
  ok("T3 un point neuf est au milieu de son arc (45°)", finsDe(o.d).some((pt) => Math.hypot(pt[0] - 35.36, pt[1] - 35.36) < 0.2), JSON.stringify(finsDe(o.d)));
}
{
  // tracé ouvert : pas de segment de fermeture ; quadratique coupée ; deux sous-chemins
  const d = doc({ id: "o", type: "path", d: "M 0 0 L 100 0 Q 150 0 150 50", style: { fond: "none", contour: "#000", epaisseur: 1 } },
                { id: "s", type: "path", d: "M 0 0 L 10 0 L 10 10 Z M 20 0 L 30 0 L 30 10 L 20 0 Z", style: { fond: "#eee" } });
  op_points_ajouter(d, ["o", "s"]);
  const o = objets(d)[0], s2 = objets(d)[1];
  ok("T3 ouvert : 3 → 5 points, toujours ouvert", compter_ancres(o.d) === 5 && !/Z/.test(o.d), o.d);
  ok("T3 quadratique coupée en deux quadratiques", chemin_parser(o.d).filter((g) => g.c === "Q").length === 2, o.d);
  ok("T3 deux sous-chemins : 3 → 6 et 3 → 6 (un retour explicite au départ ne reçoit pas de point en plus)",
     compter_ancres(s2.d) === 12 && chemin_parser(s2.d).filter((g) => g.c === "M").length === 2, s2.d);
}
{
  // ellipse et forme deviennent des chemins ; texte et groupe ignorés ; rien à faire → refus, sans trace
  const d = doc({ id: "e", type: "ellipse", cx: 0, cy: 0, rx: 40, ry: 20, style: { fond: "#eee" } },
                { id: "t", type: "texte", x: 0, y: 0, texte: "A", style: { fond: "#000" } });
  const ids = op_points_ajouter(d, ["e", "t"]);
  ok("T3 ellipse : chemin de 8 points, aire π·40·20 (± 0,5 %)", ids.length === 1 && objets(d)[0].type === "path"
     && compter_ancres(objets(d)[0].d) === 8 && pres(aire(objets(d)[0]), Math.PI * 800, 0.5), objets(d)[0].d);
  ok("T3 le texte n'a pas bougé", objets(d)[1].type === "texte" && objets(d)[1].texte === "A");
  const v = doc({ id: "t", type: "texte", x: 0, y: 0, texte: "A", style: { fond: "#000" } });
  const avantV = JSON.stringify(v);
  ok("T3 rien de traçable : refus traduit, document intact", refus(() => op_points_ajouter(v, ["t"])) === T("vectorlab.traces.points_rien") && JSON.stringify(v) === avantV);
  ok("T3 la clé existe", T("vectorlab.traces.points_rien") !== "vectorlab.traces.points_rien");
  // deux passes : 4 → 8 → 16
  const r = doc({ id: "r", type: "rect", x: 0, y: 0, w: 80, h: 80, style: { fond: "#eee" } });
  op_points_ajouter(r, ["r"]); op_points_ajouter(r, ["r"]);
  ok("T3 deux passes : 16 points", compter_ancres(objets(r)[0].d) === 16, objets(r)[0].d);
  // après Z, un segment repart du DÉPART du sous-chemin (règle SVG) : son milieu se calcule depuis là
  const z = doc({ id: "z", type: "path", d: "M 0 0 L 10 0 L 10 10 Z L 0 10", style: { fond: "none", contour: "#000", epaisseur: 1 } });
  op_points_ajouter(z, ["z"]);
  ok("T3 segment après Z : son milieu part du départ (0 5)", finsDe(objets(z)[0].d).some((pt) => pt[0] === 0 && pt[1] === 5), objets(z)[0].d);
}

/* ── T4 : Moyenne ── */
{
  const tri = () => doc({ id: "p", type: "path", d: "M 0 0 L 100 10 L 50 80 L 200 200 Z", style: { fond: "#eee" } });
  const pts = (d) => finsDe(objets(d)[0].d);
  const a = tri(); op_noeuds_moyenne(a, "p", [0, 1, 2], "deux");
  ok("T4 les deux : les 3 nœuds au barycentre (50 30), le 4e immobile",
     JSON.stringify(pts(a)) === JSON.stringify([[50, 30], [50, 30], [50, 30], [200, 200]]), JSON.stringify(pts(a)));
  const h = tri(); op_noeuds_moyenne(h, "p", [0, 1, 2], "horizontale");
  ok("T4 horizontale : même y (30), x gardés", JSON.stringify(pts(h)) === JSON.stringify([[0, 30], [100, 30], [50, 30], [200, 200]]), JSON.stringify(pts(h)));
  const v = tri(); op_noeuds_moyenne(v, "p", [0, 2], "verticale");
  ok("T4 verticale : même x (25), y gardés", JSON.stringify(pts(v)) === JSON.stringify([[25, 0], [100, 10], [25, 80], [200, 200]]), JSON.stringify(pts(v)));
  // les poignées suivent leur nœud
  const c = doc({ id: "c", type: "path", d: "M 0 0 C 10 0 20 10 30 10 L 60 40", style: { fond: "none", contour: "#000", epaisseur: 1 } });
  op_noeuds_moyenne(c, "c", [1, 2], "deux");
  const g = chemin_parser(objets(c)[0].d);
  ok("T4 la poignée d'arrivée suit son nœud (même décalage)", g[1].c === "C" && g[1].p[2] === 35 && g[1].p[3] === 25 && g[1].p[4] === 45 && g[1].p[5] === 25, JSON.stringify(g[1]));
  // refus : un seul nœud, mode inconnu → document intact
  const r1 = tri(), av1 = JSON.stringify(r1);
  ok("T4 un seul nœud : refus de l'alignement, document intact", refus(() => op_noeuds_moyenne(r1, "p", [1], "deux")) === T("vectorlab.noeuds.err_aligner") && JSON.stringify(r1) === av1);
  const r2 = tri(), av2 = JSON.stringify(r2);
  ok("T4 mode inconnu : refus, document intact", refus(() => op_noeuds_moyenne(r2, "p", [0, 1], "diagonale")) !== null && JSON.stringify(r2) === av2);
}

/* ── T5 : Nettoyer ── */
{
  const plein = (id) => ({ id, type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#eee" } });
  const semer = () => ({ v: 1, taille: { w: 400, h: 400 }, calques: [
    { id: "c1", nom: "a", visible: true, verrou: false, objets: [
      plein("ok1"),
      { id: "iso", type: "path", d: "M 5 5", style: { fond: "none", contour: "#000", epaisseur: 1 } },
      { id: "iso2", type: "path", d: "M 5 5 Z", style: { fond: "#eee" } },
      { id: "inv", type: "ellipse", cx: 0, cy: 0, rx: 5, ry: 5, style: { fond: "none", contour: "none" } },
      { id: "inv0", type: "rect", x: 0, y: 0, w: 5, h: 5, style: { fond: "none", contour: "#000", epaisseur: 0 } },
      { id: "vide", type: "texte", x: 0, y: 0, contenu: "  \n ", style: { fond: "#000" } },
      { id: "cvide", type: "cadre", x: 0, y: 0, w: 50, h: 20, contenu: "", style: { fond: "#000" } },
      { id: "txt", type: "texte", x: 0, y: 0, contenu: "Bonjour", style: { fond: "#000" } },
      { id: "trait", type: "path", d: "M 0 0 L 9 9", style: { fond: "none", contour: "#000", epaisseur: 1 } },
      { id: "app", type: "rect", x: 0, y: 0, w: 5, h: 5, style: { fond: "none", contour: "none", contours: [{ couleur: "#f00", epaisseur: 3 }] } },
      { id: "grad", type: "rect", x: 0, y: 0, w: 5, h: 5, style: { fond: "grad:g1" } },
      // guide invisible d'un texte sur chemin, source invisible d'un contour vivant : protégés
      { id: "guide", type: "path", d: "M 0 0 L 100 0", style: { fond: "none", contour: "none" } },
      { id: "tc", type: "textechemin", d: "M 0 0 L 100 0", chemin: "guide", contenu: "le long", style: { fond: "#000" } },
      { id: "src", type: "path", d: "M 0 0 L 50 0 L 50 50 Z", style: { fond: "none", contour: "none" } },
      { id: "viv", type: "path", d: "M 0 0 L 9 0 L 9 9 Z", derive: { source: "src", decalage: 2 }, style: { fond: "#eee" } },
      // groupe : un invisible dedans part ; un groupe vidé part aussi ; un groupe écrêté est laissé tel quel
      { id: "g", type: "groupe", style: {}, enfants: [plein("ok2"), { id: "ginv", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "none" } }] },
      { id: "gv", type: "groupe", style: {}, enfants: [{ id: "gviso", type: "path", d: "M 1 1", style: { fond: "#eee" } }] },
      { id: "gm", type: "groupe", clip: "m", style: {}, enfants: [{ id: "m", type: "rect", x: 0, y: 0, w: 9, h: 9, style: { fond: "none", contour: "none" } }, plein("ok3")] },
    ] },
    { id: "c2", nom: "verrou", visible: true, verrou: true, objets: [{ id: "vinv", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "none" } }] },
  ] });
  const d = semer();
  const r = op_nettoyer(d, { isoles: true, invisibles: true, textesVides: true });
  const restants = new Set(tousIdsDoc(d));
  ok("T5 compte exact : 3 isolés, 3 invisibles, 2 textes vides", r.isoles === 3 && r.invisibles === 3 && r.textesVides === 2, JSON.stringify(r));
  for (const id of ["iso", "iso2", "inv", "inv0", "vide", "cvide", "ginv", "gviso", "gv"]) ok(`T5 « ${id} » est parti`, !restants.has(id));
  for (const id of ["ok1", "txt", "trait", "app", "grad", "guide", "tc", "src", "viv", "g", "ok2", "gm", "m", "ok3", "vinv"]) ok(`T5 « ${id} » est resté`, restants.has(id));
  // options : seulement les textes vides
  const e = semer();
  const r2 = op_nettoyer(e, { isoles: false, invisibles: false, textesVides: true });
  ok("T5 une seule case : seuls les textes vides partent", r2.isoles === 0 && r2.invisibles === 0 && r2.textesVides === 2
     && tousIdsDoc(e).includes("iso") && tousIdsDoc(e).includes("inv") && !tousIdsDoc(e).includes("vide"), JSON.stringify(r2));
  const f = semer();
  const r3 = op_nettoyer(f, { isoles: true, invisibles: false, textesVides: false });
  ok("T5 seulement les points isolés : textes vides et invisibles restent", r3.isoles === 3 && r3.invisibles === 0 && r3.textesVides === 0
     && tousIdsDoc(f).includes("vide") && tousIdsDoc(f).includes("inv") && !tousIdsDoc(f).includes("iso"), JSON.stringify(r3));
  // rien à nettoyer : refus traduit, document intact (VL.executer ne pousse rien dans l'historique)
  const n = doc(plein("a"));
  const avant = JSON.stringify(n);
  ok("T5 rien à nettoyer : refus traduit, document intact", refus(() => op_nettoyer(n, { isoles: true, invisibles: true, textesVides: true })) === T("vectorlab.traces.nettoyer_rien") && JSON.stringify(n) === avant);
  ok("T5 la clé existe", T("vectorlab.traces.nettoyer_rien") !== "vectorlab.traces.nettoyer_rien");
}

/* ── T6 : Diviser les objets en dessous ── */
{
  const R = (id, x, y, w, h, fond = "#0047AB", extra = {}) => ({ id, type: "rect", x, y, w, h, style: { fond }, ...extra });
  const cercle = { id: "k", type: "ellipse", cx: 100, cy: 50, rx: 30, ry: 30, style: { fond: "#ff0000", contour: "#000", epaisseur: 1 } };
  const d = { v: 1, taille: { w: 400, h: 400 }, calques: [
    { id: "c0", nom: "bas", visible: true, verrou: false, objets: [R("B", 100, 0, 100, 100, "#00aa00")] },
    { id: "c1", nom: "haut", visible: true, verrou: false, objets: [
      R("A", 0, 0, 100, 100), R("loin", 300, 300, 50, 50), R("verr", 60, 40, 30, 20, "#999999", { verrou: true }),
      R("dedans", 95, 45, 10, 10, "#777777"),
      { ...cercle }, R("dessus", 120, 40, 30, 20, "#ffff00") ] },
    { id: "c2", nom: "plus haut", visible: true, verrou: false, objets: [R("calqueHaut", 120, 60, 30, 20, "#ff00ff")] } ] };
  const aireA = 10000, demi = Math.PI * 900 / 2;
  const avantLoin = JSON.stringify(d.calques[1].objets[1]), avantVerr = JSON.stringify(d.calques[1].objets[2]), avantDessus = JSON.stringify(d.calques[1].objets[5]);
  const avantDedans = JSON.stringify(d.calques[1].objets[3]), avantHaut = JSON.stringify(d.calques[2].objets[0]);
  const ids = op_diviser_dessous(d, "k");
  const tous = d.calques.flatMap((c) => c.objets);
  const deA = tous.filter((o) => o.style.fond === "#0047AB" && o.id !== "loin"), deB = tous.filter((o) => o.style.fond === "#00aa00");
  ok("T6 deux objets touchés → 4 morceaux rendus", ids.length === 4 && deA.length === 2 && deB.length === 2, JSON.stringify(ids));
  ok("T6 le couteau a disparu", !tous.some((o) => o.id === "k"));
  ok("T6 A : un demi-disque + le reste, aire totale conservée", deA.some((o) => pres(aire(o), demi, 1)) && pres(deA.reduce((t, o) => t + aire(o), 0), aireA, 0.2),
     JSON.stringify(deA.map(aire)));
  ok("T6 B (calque du dessous) : divisé aussi, aire conservée", pres(deB.reduce((t, o) => t + aire(o), 0), aireA, 0.2), JSON.stringify(deB.map(aire)));
  ok("T6 les morceaux de B restent dans SON calque, à sa place", d.calques[0].objets.length === 2 && d.calques[0].objets.every((o) => o.style.fond === "#00aa00"));
  ok("T6 objet non touché, objet verrouillé, objet AU-DESSUS : intacts",
     tous.some((o) => JSON.stringify(o) === avantLoin) && tous.some((o) => JSON.stringify(o) === avantVerr) && tous.some((o) => JSON.stringify(o) === avantDessus));
  ok("T6 objet ENTIÈREMENT dans le couteau : intact ; objet d'un calque AU-DESSUS : intact",
     tous.some((o) => JSON.stringify(o) === avantDedans) && tous.some((o) => JSON.stringify(o) === avantHaut));
  ok("T6 ordre de peinture : les morceaux de A sont sous l'objet verrouillé", d.calques[1].objets.findIndex((o) => o.id === "verr") > d.calques[1].objets.findIndex((o) => ids.includes(o.id)));
  ok("T6 ids uniques", new Set(tousIdsDoc(d)).size === tousIdsDoc(d).length, tousIdsDoc(d));
}
{
  // couteau OUVERT (une ligne) : coupe le long de la ligne, deux moitiés de 5000
  const d = doc({ id: "r", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "#0047AB" } },
                { id: "l", type: "path", d: "M 50 -10 L 50 110", style: { fond: "none", contour: "#000", epaisseur: 4 } });
  const ids = op_diviser_dessous(d, "l");
  ok("T6 ligne : deux moitiés d'aire 5000 (± 0,1 %)", ids.length === 2 && objets(d).length === 2 && objets(d).every((o) => pres(aire(o), 5000, 0.1)),
     JSON.stringify(objets(d).map(aire)));
  // couteau tourné : la rotation compte
  const t = doc({ id: "r", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "#0047AB" } },
                { id: "l", type: "path", d: "M -10 50 L 110 50", transform: "rotate(90 50 50)", style: { fond: "none", contour: "#000", epaisseur: 1 } });
  op_diviser_dessous(t, "l");
  const xs = objets(t).map((o) => bbox(o)[2]).sort((a, b) => a - b);
  // objet du dessous TOURNÉ : sa rotation compte (rect 200 × 20 tourné de 90° autour de (50 50) = vertical, x de 40 à 60)
  const u = doc({ id: "r", type: "rect", x: -50, y: 40, w: 200, h: 20, transform: "rotate(90 50 50)", style: { fond: "#0047AB" } },
                { id: "l", type: "path", d: "M 0 50 L 100 50", style: { fond: "none", contour: "#000", epaisseur: 1 } });
  op_diviser_dessous(u, "l");
  ok("T6 objet tourné : coupé en deux moitiés de 2000 (sa rotation est appliquée)", objets(u).length === 2 && objets(u).every((o) => pres(aire(o), 2000, 0.2)), JSON.stringify(objets(u).map(aire)));
  ok("T6 couteau tourné de 90° : coupe verticale (bords droits à 50 et 100)", objets(t).length === 2 && Math.abs(xs[0] - 50) < 0.1 && Math.abs(xs[1] - 100) < 0.1, JSON.stringify(xs));
}
{
  // refus : rien dessous, couteau non traçable → message, document intact
  const d = doc({ id: "r", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#eee" } },
                { id: "k", type: "ellipse", cx: 200, cy: 200, rx: 5, ry: 5, style: { fond: "#f00" } });
  const av = JSON.stringify(d);
  // un trait qui entre dans l'objet sans le traverser ne le coupe pas
  const m = doc({ id: "r", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "#eee" } },
                { id: "l", type: "path", d: "M 50 -10 L 50 40", style: { fond: "none", contour: "#000", epaisseur: 1 } });
  const avM = JSON.stringify(m);
  ok("T6 trait qui ne traverse pas : refus « ne traverse aucun objet », document intact", refus(() => op_diviser_dessous(m, "l")) === T("vectorlab.traces.diviser_rien") && JSON.stringify(m) === avM);
  ok("T6 le couteau ne touche rien : refus traduit, document intact", refus(() => op_diviser_dessous(d, "k")) === T("vectorlab.traces.diviser_rien") && JSON.stringify(d) === av);
  const e = doc({ id: "r", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#eee" } }, { id: "t", type: "texte", x: 0, y: 0, contenu: "A", style: { fond: "#000" } });
  const av2 = JSON.stringify(e);
  ok("T6 couteau = texte : refus traduit, document intact", refus(() => op_diviser_dessous(e, "t")) === T("vectorlab.traces.diviser_couteau") && JSON.stringify(e) === av2);
  ok("T6 les clés existent", T("vectorlab.traces.diviser_rien") !== "vectorlab.traces.diviser_rien" && T("vectorlab.traces.diviser_couteau") !== "vectorlab.traces.diviser_couteau");
}

/* ── T7 : Lignes et colonnes ── */
{
  const geo = (o) => [o.x, o.y, o.w, o.h];
  const d = doc({ id: "a", type: "rect", x: 0, y: 0, w: 5, h: 5, style: { fond: "#eee" } },
                { id: "r", type: "rect", x: 0, y: 0, w: 100, h: 100, nom: "Planche", style: { fond: "#0047AB", contour: "#000", epaisseur: 1 } },
                { id: "z", type: "rect", x: 0, y: 0, w: 5, h: 5, style: { fond: "#eee" } });
  const ids = op_lignes_colonnes(d, "r", { lignes: 2, colonnes: 2, gouttiereLignes: 10, gouttiereColonnes: 10 });
  const cel = objets(d).slice(1, 5);
  ok("T7 2 × 2, gouttière 10 : 4 rectangles 45 × 45 aux bonnes places, ligne par ligne", ids.length === 4 && objets(d).length === 6
     && JSON.stringify(cel.map(geo)) === JSON.stringify([[0, 0, 45, 45], [55, 0, 45, 45], [0, 55, 45, 45], [55, 55, 45, 45]]), JSON.stringify(cel.map(geo)));
  ok("T7 la source disparaît, les cellules prennent sa place et son style", !tousIdsDoc(d).includes("r") && objets(d)[0].id === "a" && objets(d)[5].id === "z"
     && cel.every((o) => o.type === "rect" && o.style.fond === "#0047AB" && o.style.epaisseur === 1));
  ok("T7 ids rendus = cellules, uniques", JSON.stringify(ids) === JSON.stringify(cel.map((o) => o.id)) && new Set(tousIdsDoc(d)).size === tousIdsDoc(d).length);
  ok("T7 sans repères demandés : aucun repère posé", !d.guides || ((d.guides.v || []).length === 0 && (d.guides.h || []).length === 0), JSON.stringify(d.guides));
}
{
  const d = doc({ id: "r", type: "rect", x: 10, y: 20, w: 100, h: 60, style: { fond: "#eee" } });
  op_lignes_colonnes(d, "r", { lignes: 1, colonnes: 3, gouttiereLignes: 0, gouttiereColonnes: 5 });
  ok("T7 3 colonnes, gouttière 5 : largeur 30, x = 10, 45, 80", JSON.stringify(objets(d).map((o) => [o.x, o.y, o.w, o.h])) === JSON.stringify([[10, 20, 30, 60], [45, 20, 30, 60], [80, 20, 30, 60]]),
     JSON.stringify(objets(d).map((o) => [o.x, o.w])));
  const u = doc({ id: "r", type: "rect", x: 10, y: 20, w: 100, h: 60, style: { fond: "#eee" } });
  op_lignes_colonnes(u, "r", { lignes: 1, colonnes: 1 });
  ok("T7 1 × 1 : un rectangle identique", objets(u).length === 1 && JSON.stringify([objets(u)[0].x, objets(u)[0].y, objets(u)[0].w, objets(u)[0].h]) === "[10,20,100,60]");
}
{
  // repères : bords de chaque colonne et de chaque ligne, sans doublon avec un repère existant
  const d = doc({ id: "r", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "#eee" } });
  d.guides = { v: [0], h: [] };
  op_lignes_colonnes(d, "r", { lignes: 2, colonnes: 2, gouttiereLignes: 10, gouttiereColonnes: 10, reperes: true });
  const tri = (a) => [...a].sort((x, y) => x - y);
  ok("T7 repères verticaux 0, 45, 55, 100 (le 0 existant n'est pas doublé)", JSON.stringify(tri(d.guides.v)) === "[0,45,55,100]", JSON.stringify(d.guides));
  ok("T7 repères horizontaux 0, 45, 55, 100", JSON.stringify(tri(d.guides.h)) === "[0,45,55,100]", JSON.stringify(d.guides));
}
{
  // objet tourné : sa boîte RÉELLE (ellipse 100 × 40 tournée de 90° autour de son centre → x 30..70, y 0..100)
  const d = doc({ id: "e", type: "ellipse", cx: 50, cy: 50, rx: 50, ry: 20, transform: "rotate(90 50 50)", style: { fond: "#eee" } });
  op_lignes_colonnes(d, "e", { lignes: 2, colonnes: 1, gouttiereLignes: 0 });
  const g = objets(d).map((o) => [o.x, o.y, o.w, o.h].map((v) => Math.round(v * 10) / 10));
  ok("T7 objet tourné : grille dans sa boîte réelle, sans transform", JSON.stringify(g) === "[[30,0,40,50],[30,50,40,50]]" && objets(d).every((o) => !o.transform), JSON.stringify(g));
}
{
  // refus : nombres invalides, gouttières trop grandes, objet non traçable → message, document intact
  const cas = [
    [{ lignes: 0, colonnes: 2 }, "vectorlab.traces.lignes_nombre"],
    [{ lignes: 1.5, colonnes: 2 }, "vectorlab.traces.lignes_nombre"],
    [{ lignes: 2, colonnes: 101 }, "vectorlab.traces.lignes_nombre"],
    [{ lignes: 1, colonnes: 2, gouttiereColonnes: 100 }, "vectorlab.traces.lignes_taille"],
    [{ lignes: 2, colonnes: 1, gouttiereLignes: -1 }, "vectorlab.traces.lignes_taille"],
  ];
  for (const [opts, cle] of cas) {
    const d = doc({ id: "r", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "#eee" } });
    const av = JSON.stringify(d);
    ok(`T7 refus ${JSON.stringify(opts)} → ${cle}, document intact`, refus(() => op_lignes_colonnes(d, "r", opts)) === T(cle) && JSON.stringify(d) === av);
    ok(`T7 la clé ${cle} existe`, T(cle) !== cle);
  }
  const t = doc({ id: "t", type: "texte", x: 0, y: 0, contenu: "A", style: { fond: "#000" } });
  const avT = JSON.stringify(t);
  ok("T7 objet non traçable : refus traduit, document intact", refus(() => op_lignes_colonnes(t, "t", { lignes: 2, colonnes: 2 })) === T("vectorlab.traces.lignes_objet") && JSON.stringify(t) === avT);
  ok("T7 la clé lignes_objet existe", T("vectorlab.traces.lignes_objet") !== "vectorlab.traces.lignes_objet");
}

if (echecs.length) {
  console.error(`traces : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("traces : ok");
