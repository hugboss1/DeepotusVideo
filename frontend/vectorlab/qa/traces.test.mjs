// traces.test.mjs — lot D1 « Tracés » (t422…) : les commandes de tracé reprises d'Illustrator, opérations PURES de
// js/mod-traces.js. Martinez vendorisé en vrai, comme opsbool2.
// T1 (t422) Vectoriser le contour : le trait devient une surface pleine de la couleur du trait ; un objet rempli
// devient un groupe [fond sans contour, contour vectorisé] à la même place ; refus sans trace.
import { createRequire } from "node:module";
import { fournirMartinez, aplatir_objet, versMulti, aire_multi } from "../js/mod-bool.js";
import { op_contour_vectoriser } from "../js/mod-traces.js";
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

if (echecs.length) {
  console.error(`traces : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("traces : ok");
