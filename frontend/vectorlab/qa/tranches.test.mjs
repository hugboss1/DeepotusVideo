// tranches.test.mjs — mod-tranches (lot G) : tranches par mode (bbox
// injectée), résolutions lues et bornées, nommage @2x, plan d'export,
// saignée et marques de coupe / repérage. Module feuille, états vides.
import { MODES, tranches_de, resolutions_lire, FORMATS, nom_export, plan_export, mm_px, cadre_saignee,
         marques_svg } from "../js/mod-tranches.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
const compte = (s, re) => (s.match(re) || []).length;
const doc = {
  v: 1, taille: { w: 400, h: 300 },
  planches: [{ id: "p1", nom: "Recto", x: 0, y: 0, w: 200, h: 300 }, { id: "p2", nom: "Verso", x: 200, y: 0, w: 200, h: 300 }],
  calques: [
    { id: "c1", nom: "fond", visible: true, verrou: false, objets: [{ id: "r1", type: "rect", x: 10, y: 10, w: 50, h: 20 }] },
    { id: "c2", nom: "détail", visible: false, verrou: false, objets: [{ id: "e1", type: "ellipse", cx: 100, cy: 100, rx: 10, ry: 5 }] },
    { id: "c3", nom: "vide", visible: true, verrou: false, objets: [] },
  ],
};
const bboxDe = (o) => o.type === "rect" ? { x: o.x, y: o.y, w: o.w, h: o.h } : { x: o.cx - o.rx, y: o.cy - o.ry, w: 2 * o.rx, h: 2 * o.ry };

{
  ok("cinq modes", JSON.stringify(MODES.map((m) => m.id)) === '["document","planches","calques","objets","dessinees"]');
  const d = tranches_de(doc, "document", { bboxDe });
  ok("document : une tranche « doc » = la page", d.length === 1 && d[0].nom === "doc" && JSON.stringify(d[0].cadre) === JSON.stringify({ x: 0, y: 0, w: 400, h: 300 }));
  const p = tranches_de(doc, "planches", { bboxDe });
  ok("planches : une par planche, nommée par son nom assaini", p.length === 2 && p[0].nom === "Recto" && p[1].cadre.x === 200, JSON.stringify(p));
  const c = tranches_de(doc, "calques", { bboxDe });
  ok("calques : les calques VISIBLES non vides, bbox de leurs objets, calqueId porté", c.length === 1 && c[0].nom === "fond" && c[0].calqueId === "c1" && JSON.stringify(c[0].cadre) === JSON.stringify({ x: 10, y: 10, w: 50, h: 20 }), JSON.stringify(c));
  const o = tranches_de(doc, "objets", { bboxDe, ids: ["r1", "e1"] });
  ok("objets : une tranche par id sélectionné, nommée par l'id", o.length === 2 && o[1].nom === "e1" && o[1].cadre.w === 20, JSON.stringify(o));
  const t = tranches_de(doc, "dessinees", { dessinees: [{ nom: "t1", x: 5, y: 5, w: 30, h: 30 }] });
  ok("dessinées : les rectangles de la session", t.length === 1 && t[0].nom === "t1" && t[0].cadre.w === 30);
  ok("état vide : sans planche, sans sélection, sans tranche dessinée → []", tranches_de({ taille: { w: 1, h: 1 }, calques: [] }, "planches", {}).length === 0 && tranches_de(doc, "objets", { bboxDe, ids: [] }).length === 0 && tranches_de(doc, "dessinees", {}).length === 0);
  let refus = 0; try { tranches_de(doc, "zz", {}); } catch { refus++; }
  ok("mode inconnu refusé", refus === 1);
  ok("les noms de tranche sont assainis (espaces → tirets, accents retirés)", tranches_de({ taille: { w: 1, h: 1 }, calques: [], planches: [{ id: "p", nom: "Ma planche é!", x: 0, y: 0, w: 1, h: 1 }] }, "planches", {})[0].nom === "Ma-planche-e");
}
{
  ok("résolutions : « 1, 2, 4 » → [1,2,4] ; doublons et hors bornes tombent ; 4 valeurs au plus ; vide → [1]",
     JSON.stringify(resolutions_lire("1, 2, 4")) === "[1,2,4]" && JSON.stringify(resolutions_lire("2,2,0,9,3")) === "[2,3]" && resolutions_lire("1,2,3,4,5,6").length === 4 && JSON.stringify(resolutions_lire("")) === "[1]");
  ok("six formats, png en tête, pdf et dxf présents", FORMATS.map((f) => f.id).join(",") === "png,jpeg,webp,svg,pdf,dxf");
  ok("nom : vector_<doc>_<tranche>@2x.png ; 1× sans suffixe ; transparent _t ; jpeg → .jpg",
     nom_export("abc", "doc", 2, "png", false) === "vector_abc_doc@2x.png" && nom_export("abc", "Recto", 1, "jpeg", false) === "vector_abc_Recto.jpg" && nom_export("abc", "t1", 4, "webp", true) === "vector_abc_t1@4x_t.webp");
  const plan = plan_export("abc", [{ nom: "doc", cadre: { x: 0, y: 0, w: 1, h: 1 } }, { nom: "t1", cadre: { x: 0, y: 0, w: 1, h: 1 } }], [1, 2], ["png", "jpeg", "svg", "pdf"], false);
  ok("plan : tranches × résolutions pour les rasters, UNE entrée par tranche pour svg, UNE seule entrée pdf pour tout le lot", plan.filter((e) => e.format === "png").length === 4 && plan.filter((e) => e.format === "svg").length === 2 && plan.filter((e) => e.format === "pdf").length === 1 && plan.every((e) => e.nom), JSON.stringify(plan));
  ok("état vide : sans tranche → plan vide", plan_export("abc", [], [1], ["png"], false).length === 0);
}
{
  ok("mm → px au dpi du document", mm_px(25.4, 300) === 300 && mm_px(0, 72) === 0);
  const c = cadre_saignee({ x: 10, y: 10, w: 100, h: 50 }, 5);
  ok("la saignée élargit le cadre de chaque côté", JSON.stringify(c) === JSON.stringify({ x: 5, y: 5, w: 110, h: 60 }));
  const m = marques_svg({ x: 10, y: 10, w: 100, h: 50 }, 5, { coupe: true, reperage: true }, 8);
  ok("marques : un groupe, 8 traits de coupe (deux par coin) hors saignée, 4 repères (cercle + croix)", m.startsWith("<g") && compte(m, /<line/g) === 8 + 8 && compte(m, /<circle/g) === 4 && m.includes('x1="10"') && !m.includes("NaN"), m.slice(0, 300));
  ok("les traits de coupe restent dehors : un trait vertical du coin haut-gauche va de y = 10 − 5 − 8 à y = 10 − 5", /x1="10" y1="-3" x2="10" y2="5"/.test(marques_svg({ x: 10, y: 10, w: 100, h: 50 }, 5, { coupe: true }, 8)), marques_svg({ x: 10, y: 10, w: 100, h: 50 }, 5, { coupe: true }, 8));
  ok("état vide : sans coupe ni repérage → chaîne vide", marques_svg({ x: 0, y: 0, w: 1, h: 1 }, 0, {}, 8) === "");
}
if (echecs.length) {
  console.error("ECHECS tranches :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA tranches : PASS (21 controles)");
