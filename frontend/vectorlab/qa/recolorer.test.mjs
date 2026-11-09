// recolorer.test.mjs — lot D5 « Couleur et motif » (t475) : les couleurs d'une sélection et leur réassignation
// (js/mod-recolorer.js, pur). Fonds, contours, contours multiples, effets, dégradés et motifs employés, couleurs
// globales ; un dégradé ou un motif PARTAGÉ avec un objet hors sélection est cloné, jamais modifié pour lui.
import { couleurs_selection, op_recolorer, op_couleurs_transformer, hex_normal } from "../js/mod-recolorer.js";
import { parserDoc } from "../js/mod-doc.js";
import { T } from "../js/mod-i18n.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : ""));
};
const refus = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
const clone = (x) => JSON.parse(JSON.stringify(x));

const DOC = () => ({
  v: 1, taille: { w: 400, h: 400 },
  couleursGlobales: { Marque: "#336699" },
  degrades: {
    g1: { type: "lineaire", x1: 0, y1: 0, x2: 1, y2: 0, stops: [{ t: 0, couleur: "#FF0000" }, { t: 1, couleur: "#00ff00" }] },
    g2: { type: "lineaire", x1: 0, y1: 0, x2: 1, y2: 0, stops: [{ t: 0, couleur: "#ff0000" }, { t: 1, couleur: "#0000ff" }] },
  },
  motifs: { m1: { type: "points", pas: 8, angle: 0, epaisseur: 1, couleur: "#ff0000", fond: "#ffffff" } },
  calques: [
    { id: "c1", nom: "a", visible: true, verrou: false, objets: [
      { id: "r", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#FF0000", contour: "#000000", epaisseur: 1,
        contours: [{ couleur: "#ff0000", epaisseur: 3 }], effets: [{ type: "ombre", dx: 2, dy: 2, flou: 2, couleur: "#000000", opacite: 0.5 }] } },
      { id: "e", type: "ellipse", cx: 50, cy: 50, rx: 5, ry: 5, style: { fond: "glob:Marque", contour: "none" } },
      { id: "g", type: "groupe", style: {}, enfants: [
        { id: "g_a", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "grad:g1" } },
        { id: "g_b", type: "texte", x: 0, y: 0, contenu: "A", style: { fond: "#ff0000" } },
      ] },
      { id: "p", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "motif:m1" } },
      { id: "h", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "grad:g2" } },   // g2 : hors sélection aussi
      { id: "hors", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "grad:g2", contour: "#FF0000" } },
      { id: "rep", type: "groupe", style: {}, repetition: { mode: "grille" }, enfants: [
        { id: "src", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "#abcdef" } },
        { id: "rep_r1", type: "rect", x: 2, y: 0, w: 1, h: 1, genere: true, style: { fond: "#abcdef" } },
      ] },
    ] },
    { id: "c2", nom: "verrou", visible: true, verrou: true, objets: [
      { id: "v", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "#ff0000" } },
    ] },
  ],
});

/* ── hex_normal ── */
ok("hex_normal : #RGB, #RRGGBB, casse ; le reste → null", hex_normal("#F00") === "#ff0000" && hex_normal("#00FF00") === "#00ff00"
   && hex_normal("none") === null && hex_normal("grad:g1") === null && hex_normal("#12345") === null && hex_normal(undefined) === null);

/* ── couleurs_selection ── */
{
  const d = DOC();
  const c = couleurs_selection(d, ["r", "e", "g", "p"]);
  const de = (h) => c.find((x) => x.hex === h);
  ok("rouge : fond, contours multiples, dégradé, texte, motif — compté 5 fois, en tête", c[0].hex === "#ff0000" && c[0].n === 5
     && ["fond", "contour", "degrade", "texte", "motif"].every((o) => c[0].ou.includes(o)), JSON.stringify(c));
  ok("noir : contour et ombre (effet)", de("#000000") && de("#000000").n === 2 && de("#000000").ou.includes("effet"), JSON.stringify(de("#000000")));
  ok("couleur globale résolue, nommée", de("#336699") && de("#336699").globales.includes("Marque"));
  ok("dégradé : ses arrêts ; motif : couleur et fond", de("#00ff00").ou.includes("degrade") && de("#ffffff").ou.includes("motif"));
  ok("tri : par usage décroissant puis hex", c.every((x, i) => !i || c[i - 1].n > x.n || (c[i - 1].n === x.n && c[i - 1].hex < x.hex)));
  ok("contour none non compté", !c.some((x) => x.hex === null));
  ok("objet absent ou calque verrouillé : ignorés", couleurs_selection(d, ["v", "zz"]).length === 0);
  const r = couleurs_selection(d, ["rep"]);
  ok("vivant : la source compte, pas les copies générées", r.length === 1 && r[0].n === 1, JSON.stringify(r));
  ok("un groupe et son enfant sélectionnés : comptés une fois", couleurs_selection(d, ["g", "g_b"]).find((x) => x.hex === "#ff0000").n === 2);
  ok("rien de muté", JSON.stringify(d) === JSON.stringify(DOC()));
}

/* ── op_recolorer ── */
{
  const d = DOC();
  const n = op_recolorer(d, ["r", "e", "g", "p"], { "#FF0000": "#123456", "#336699": "#ABCDEF", "#ffffff": "#000000" });
  const o = (id) => d.calques[0].objets.find((x) => x.id === id) || d.calques[0].objets.find((x) => x.id === "g").enfants.find((x) => x.id === id);
  ok("fond, contours multiples réécrits ; contour noir intact", o("r").style.fond === "#123456" && o("r").style.contours[0].couleur === "#123456" && o("r").style.contour === "#000000");
  ok("globale réassignée → couleur simple sur l'objet ; la globale reste", o("e").style.fond === "#abcdef" && d.couleursGlobales.Marque === "#336699");
  ok("texte dans un groupe", o("g_b").style.fond === "#123456");
  ok("dégradé employé seulement par la sélection : modifié sur place", o("g_a").style.fond === "grad:g1" && d.degrades.g1.stops[0].couleur === "#123456" && d.degrades.g1.stops[1].couleur === "#00ff00");
  ok("motif employé seulement par la sélection : couleur et fond", d.motifs.m1.couleur === "#123456" && d.motifs.m1.fond === "#000000");
  ok("nombre de couleurs réécrites rendu", n === 7, n);
  ok("hors sélection intact", o("hors").style.contour === "#FF0000" && d.degrades.g2.stops[0].couleur === "#ff0000" && d.calques[1].objets[0].style.fond === "#ff0000");
  ok("le document reste valide", refus(() => parserDoc(d)) === null, refus(() => parserDoc(d)));
}
{
  // g2 est partagé avec « hors » : il est CLONÉ pour « h », jamais modifié pour « hors »
  const d = DOC();
  op_recolorer(d, ["h"], { "#ff0000": "#010203" });
  const h = d.calques[0].objets.find((x) => x.id === "h"), hors = d.calques[0].objets.find((x) => x.id === "hors");
  const nid = h.style.fond.slice(5);
  ok("dégradé partagé : cloné (id neuf) pour la sélection", h.style.fond !== "grad:g2" && nid in d.degrades && d.degrades[nid].stops[0].couleur === "#010203", JSON.stringify(h.style));
  ok("dégradé partagé : l'original intact pour l'objet hors sélection", hors.style.fond === "grad:g2" && d.degrades.g2.stops[0].couleur === "#ff0000");
  // deux objets sélectionnés qui partagent un dégradé partagé avec un tiers : UN seul clone
  const d2 = DOC();
  d2.calques[0].objets.push({ id: "h2", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "grad:g2" } });
  op_recolorer(d2, ["h", "h2"], { "#ff0000": "#010203" });
  const a = d2.calques[0].objets.find((x) => x.id === "h").style.fond, b = d2.calques[0].objets.find((x) => x.id === "h2").style.fond;
  ok("un seul clone pour la sélection entière", a === b && a !== "grad:g2" && Object.keys(d2.degrades).length === 3, JSON.stringify(Object.keys(d2.degrades)));
  // motif partagé
  const d3 = DOC();
  d3.calques[0].objets.push({ id: "p2", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "motif:m1" } });
  op_recolorer(d3, ["p"], { "#ff0000": "#010203" });
  const p = d3.calques[0].objets.find((x) => x.id === "p").style.fond;
  ok("motif partagé : cloné, l'original intact", p !== "motif:m1" && d3.motifs[p.slice(6)].couleur === "#010203" && d3.motifs.m1.couleur === "#ff0000", JSON.stringify(d3.motifs));
  // une couleur qui ne change pas ne clone rien
  const d4 = DOC();
  op_recolorer(d4, ["h"], { "#999999": "#000000" });
  ok("rien à changer dans le dégradé partagé : pas de clone", Object.keys(d4.degrades).length === 2 && d4.calques[0].objets.find((x) => x.id === "h").style.fond === "grad:g2");
}
{
  const d = DOC();
  ok("couleur invalide → refus traduit", refus(() => op_recolorer(d, ["r"], { "#ff0000": "rouge" })) === T("vectorlab.recolorer.couleur_invalide", { c: "rouge" }));
  ok("sélection vide → refus traduit", refus(() => op_recolorer(d, [], { "#ff0000": "#000000" })) === T("vectorlab.recolorer.aucune_selection"));
  ok("vivant : la source est recolorée, les copies générées attendent le recalcul", (() => {
    const x = DOC(); op_recolorer(x, ["rep"], { "#abcdef": "#111111" });
    const g = x.calques[0].objets.find((o) => o.id === "rep");
    return g.enfants[0].style.fond === "#111111" && g.enfants[1].style.fond === "#abcdef";
  })());
}

/* ── un motif fait d'objets (T4) : leurs couleurs comptent et se réassignent ── */
{
  const d = DOC();
  d.motifs.m2 = { type: "objets", objets: [{ id: "x", type: "groupe", style: {}, enfants: [{ id: "y", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "#0A0B0C", contour: "#ff0000" } }] }] };
  d.calques[0].objets.push({ id: "pm", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "motif:m2" } });
  const c = couleurs_selection(d, ["pm"]);
  ok("motif d'objets : couleurs de ses objets (groupes compris), marquées motif", c.length === 2 && c.every((x) => x.ou.length === 1 && x.ou[0] === "motif") && c.some((x) => x.hex === "#0a0b0c"), JSON.stringify(c));
  op_recolorer(d, ["pm"], { "#0a0b0c": "#ffffff" });
  ok("motif d'objets : recoloré sur place (non partagé)", d.motifs.m2.objets[0].enfants[0].style.fond === "#ffffff" && d.motifs.m2.objets[0].enfants[0].style.contour === "#ff0000");
}

/* ── cas limites du partage et des cibles ── */
{
  ok("une copie générée visée directement : ignorée", couleurs_selection(DOC(), ["rep_r1"]).length === 0);
  ok("l'intérieur d'une copie générée visé directement : ignoré", (() => {
    const d = DOC(); d.calques[0].objets.find((o) => o.id === "rep").enfants.push({ id: "rep_r2", type: "groupe", genere: true, style: {}, enfants: [{ id: "rep_r2_0", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "#ff0000" } }] });
    return couleurs_selection(d, ["rep_r2_0"]).length === 0;
  })());
  ok("ancienne couleur invalide → refus traduit", refus(() => op_recolorer(DOC(), ["r"], { rouge: "#000000" })) === T("vectorlab.recolorer.couleur_invalide", { c: "rouge" }));
  // les copies générées d'une source qui emploie un dégradé ne le « partagent » pas : il est modifié sur place
  const d = DOC();
  d.degrades.g3 = { type: "lineaire", x1: 0, y1: 0, x2: 1, y2: 0, stops: [{ t: 0, couleur: "#abcdef" }, { t: 1, couleur: "#000000" }] };
  const rep = d.calques[0].objets.find((o) => o.id === "rep");
  rep.enfants[0].style.fond = "grad:g3"; rep.enfants[1].style.fond = "grad:g3";
  op_recolorer(d, ["rep"], { "#abcdef": "#111111" });
  ok("copies générées : pas de clone, le dégradé change sur place", rep.enfants[0].style.fond === "grad:g3" && d.degrades.g3.stops[0].couleur === "#111111" && Object.keys(d.degrades).length === 3);
  // un symbole qui emploie le dégradé le partage : clone
  const d2 = DOC();
  d2.symboles = { s1: { nom: "S", bbox: { x: 0, y: 0, w: 1, h: 1 }, objets: [{ id: "sy", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "grad:g1" } }] } };
  op_recolorer(d2, ["g"], { "#ff0000": "#222222" });
  ok("dégradé employé par un symbole : cloné, l'original intact", d2.degrades.g1.stops[0].couleur === "#FF0000" && d2.calques[0].objets.find((o) => o.id === "g").enfants[0].style.fond !== "grad:g1");
}

/* ── op_couleurs_transformer ── */
{
  const d = DOC();
  const vus = [];
  op_couleurs_transformer(d, ["r", "g"], (h) => { vus.push(h); return h === "#ff0000" ? "#00FFFF" : h; });
  const r = d.calques[0].objets[0];
  ok("f reçoit des hex normalisés, une fois par couleur distincte", vus.length === new Set(vus).size && vus.every((h) => /^#[0-9a-f]{6}$/.test(h)), vus.join(","));
  ok("f appliquée partout (fond, dégradé), sortie normalisée", r.style.fond === "#00ffff" && d.degrades.g1.stops[0].couleur === "#00ffff");
  ok("f qui rend une couleur invalide → refus, rien de muté", (() => {
    const x = DOC(), avant = JSON.stringify(x);
    const m = refus(() => op_couleurs_transformer(x, ["r"], () => "zz"));
    return m === T("vectorlab.recolorer.couleur_invalide", { c: "zz" }) && JSON.stringify(x) === avant;
  })());
}

if (echecs.length) {
  console.error(`recolorer : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("recolorer : ok");
