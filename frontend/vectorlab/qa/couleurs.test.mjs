// couleurs.test.mjs — lot D5 « Couleur et motif » (t476) : Édition › Couleurs. Les transformations de couleur
// (js/mod-recolorer.js, pures), la fusion entre objets extrêmes, et l'interface (js/mod-recolorerui.js, VL factice).
import { createRequire } from "node:module";
import { inverser, niveaux_de_gris, saturer, equilibre, op_couleurs_fusion } from "../js/mod-recolorer.js";
import { couleurs_actions } from "../js/mod-recolorerui.js";
import { fournirMartinez } from "../js/mod-bool.js";
import { T } from "../js/mod-i18n.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : ""));
};
const refus = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };

/* ── transformations pures ── */
ok("inverser", inverser("#102030") === "#efdfcf" && inverser("#FFFFFF") === "#000000");
ok("niveaux de gris (luminance Rec. 709)", niveaux_de_gris("#ff0000") === "#363636" && niveaux_de_gris("#00ff00") === "#b6b6b6" && niveaux_de_gris("#777777") === "#777777", niveaux_de_gris("#ff0000"));
ok("saturer 0 : identique ; gris : reste gris", saturer("#3a7bd5", 0) === "#3a7bd5" && saturer("#808080", 50) === "#808080");
ok("saturer −100 : désaturé à clarté égale", saturer("#cc3333", -100) === "#808080", saturer("#cc3333", -100));
ok("saturer +100 : saturation doublée (bornée)", saturer("#996666", 100) === "#b34d4d" && saturer("#ff0000", 100) === "#ff0000", saturer("#996666", 100));
ok("saturer : hors bornes → refus traduit", refus(() => saturer("#ffffff", 150)) === T("vectorlab.couleurs.borne", { min: -100, max: 100 }));
ok("équilibre RVB (en % de la pleine échelle, bornée)", equilibre("#808080", { mode: "rvb", a: 10, b: -20, c: 0 }) === "#9a4d80" && equilibre("#f0f0f0", { mode: "rvb", a: 50, b: 0, c: 0 }) === "#fff0f0",
   equilibre("#808080", { mode: "rvb", a: 10, b: -20, c: 0 }));
ok("équilibre CMJN", equilibre("#ff0000", { mode: "cmjn", a: 50, b: 0, c: 0, d: 0 }) === "#800000" && equilibre("#ffffff", { mode: "cmjn", a: 0, b: 0, c: 0, d: 100 }) === "#000000",
   equilibre("#ff0000", { mode: "cmjn", a: 50, b: 0, c: 0, d: 0 }));
ok("saturer : clarté ≠ 50 %, borne à 100 % de saturation", saturer("#e6b3b3", -50) === "#d9c0c0" && saturer("#ff8080", 100) === "#ff8080");
ok("équilibre : le bleu ; le noir en CMJN reste noir (sans division par zéro)", equilibre("#808080", { mode: "rvb", a: 0, b: 0, c: 30 }) === "#8080cd"
   && equilibre("#000000", { mode: "cmjn", a: 0, b: 0, c: 0, d: 0 }) === "#000000" && equilibre("#000000", { mode: "cmjn", a: 50, b: 0, c: 0, d: 0 }) === "#000000");
ok("équilibre : mode inconnu → refus traduit", refus(() => equilibre("#000000", { mode: "lab" })) === T("vectorlab.couleurs.mode", { mode: "lab" }));

/* ── fusion ── */
const R = (id, x, y, fond) => ({ id, type: "rect", x, y, w: 10, h: 10, style: { fond } });
const doc = (...objets) => ({ v: 1, taille: { w: 400, h: 400 }, couleursGlobales: { Noir: "#000000" },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets }] });
{
  const d = doc(R("a", 0, 100, "glob:Noir"), R("b", 100, 0, "#ffffff"), R("m", 50, 50, "#ff0000"), R("m2", 25, 200, "#123456"), R("n", 75, 300, "none"));
  const n = op_couleurs_fusion(d, ["a", "b", "m", "m2", "n"], "horizontal");
  const f = (id) => d.calques[0].objets.find((o) => o.id === id).style.fond;
  ok("horizontale : extrêmes gauche / droite gardés (globale comprise), intermédiaires par rang", f("a") === "glob:Noir" && f("b") === "#ffffff"
     && f("m2") === "#555555" && f("m") === "#aaaaaa" && f("n") === "none" && n === 2, JSON.stringify(d.calques[0].objets.map((o) => o.style.fond)));
  const d2 = doc(R("a", 0, 100, "#000000"), R("b", 100, 0, "#ffffff"), R("m", 50, 50, "#ff0000"));
  op_couleurs_fusion(d2, ["a", "b", "m"], "vertical");
  ok("verticale : du haut (b) vers le bas (a)", d2.calques[0].objets[2].style.fond === "#808080" && d2.calques[0].objets[1].style.fond === "#ffffff");
  const d3 = doc(R("a", 0, 0, "#000000"), R("m", 0, 0, "#ff0000"), R("b", 0, 0, "#ffffff"));
  op_couleurs_fusion(d3, ["b", "m", "a"], "avant_arriere");
  ok("avant-arrière : de l'objet du dessous à celui du dessus", d3.calques[0].objets[1].style.fond === "#808080");
  const g = doc({ id: "g", type: "groupe", style: {}, enfants: [R("a", 0, 0, "#000000"), R("m", 50, 0, "#ff0000"), R("b", 100, 0, "#ffffff")] });
  op_couleurs_fusion(g, ["g"], "horizontal");
  ok("un groupe : ses objets", g.calques[0].objets[0].enfants[1].style.fond === "#808080");
  // quatre objets dont l'ordre de gauche à droite n'est pas celui de haut en bas
  const Q = () => doc(R("a", 0, 300, "#000000"), R("b", 300, 0, "#ffffff"), R("c", 100, 100, "#ff0000"), R("d", 200, 200, "#00ff00"));
  const qh = Q(), qv = Q();
  op_couleurs_fusion(qh, ["a", "b", "c", "d"], "horizontal");
  op_couleurs_fusion(qv, ["a", "b", "c", "d"], "vertical");
  ok("horizontale et verticale suivent chacune leur axe", qh.calques[0].objets[2].style.fond === "#555555" && qv.calques[0].objets[2].style.fond === "#aaaaaa"
     && qv.calques[0].objets[3].style.fond === "#555555", JSON.stringify([qh.calques[0].objets.map((o) => o.style.fond), qv.calques[0].objets.map((o) => o.style.fond)]));
  // le rang suit le CENTRE de chaque objet, pas son bord
  const big = { id: "big", type: "rect", x: 20, y: 0, w: 200, h: 10, style: { fond: "#ff0000" } };
  const dc = doc(R("a", 0, 0, "#000000"), big, R("m", 60, 0, "#00ff00"), R("b", 300, 0, "#ffffff"));
  op_couleurs_fusion(dc, ["a", "big", "m", "b"], "horizontal");
  ok("rang par centre", dc.calques[0].objets[2].style.fond === "#555555" && dc.calques[0].objets[1].style.fond === "#aaaaaa");
  // un groupe à fond n'est pas un des objets fusionnés : ses enfants le sont
  const gf = doc({ id: "g", type: "groupe", style: { fond: "#00ff00" }, enfants: [R("a", 0, 0, "#000000"), R("m", 50, 0, "#ff0000"), R("b", 100, 0, "#ffffff")] });
  op_couleurs_fusion(gf, ["g"], "horizontal");
  ok("groupe à fond : ignoré, ses enfants fusionnés", gf.calques[0].objets[0].style.fond === "#00ff00" && gf.calques[0].objets[0].enfants[1].style.fond === "#808080");
  ok("moins de trois objets colorés → refus traduit", refus(() => op_couleurs_fusion(doc(R("a", 0, 0, "#000000"), R("b", 9, 0, "#ffffff"), R("c", 5, 0, "grad:g")), ["a", "b", "c"], "horizontal")) === T("vectorlab.couleurs.fusion_trois"));
  ok("sens inconnu → refus traduit", refus(() => op_couleurs_fusion(doc(), [], "diagonal")) === T("vectorlab.couleurs.sens", { sens: "diagonal" }));
}

/* ── interface (VL factice) ── */
const vl = (d, sel) => {
  const VL = { etat: { doc: d, selection: sel }, toasts: [], rendus: 0,
    executer(fn, ...a) { try { const x = JSON.parse(JSON.stringify(VL.etat.doc)); const r = fn(x, ...a); VL.etat.doc = x; return r; } catch (e) { VL.toast(e.message, true); return undefined; } },
    toast(m, e) { VL.toasts.push([m, !!e]); }, rendre() { VL.rendus++; } };
  return VL;
};
{
  const VL = vl(doc(R("a", 0, 0, "#102030"), R("b", 50, 0, "#ff0000"), R("c", 99, 0, "#ffffff")), ["a"]);
  const A = couleurs_actions(VL);
  ok("inverser : possible avec une sélection", A.action("inverser").peut());
  await A.action("inverser").faire();
  ok("inverser : la sélection seule, en une exécution", VL.etat.doc.calques[0].objets[0].style.fond === "#efdfcf" && VL.etat.doc.calques[0].objets[1].style.fond === "#ff0000");
  await A.action("gris").faire();
  ok("niveaux de gris", /^#([0-9a-f]{2})\1\1$/.test(VL.etat.doc.calques[0].objets[0].style.fond), VL.etat.doc.calques[0].objets[0].style.fond);
  VL.etat.selection = ["a", "b", "c"];
  VL.etat.doc.calques[0].objets[0].style.fond = "#000000";
  await A.action("fusion_h").faire();
  ok("fusion horizontale", VL.etat.doc.calques[0].objets[1].style.fond === "#808080");
  // un dialogue : l'aperçu montre le document modifié, Annuler rend le document d'avant
  VL.etat.selection = ["b"];
  VL.etat.doc.calques[0].objets[1].style.fond = "#cc3333";
  let vu = null;
  A.demander = async (spec) => { spec.surChange({ pct: -100 }); vu = VL.etat.doc.calques[0].objets[1].style.fond; return null; };
  await A.action("saturer").faire();
  ok("saturer : aperçu en direct, puis Annuler rend l'avant", vu === "#808080" && VL.etat.doc.calques[0].objets[1].style.fond === "#cc3333", vu);
  A.demander = async (spec) => ({ pct: -100 });
  await A.action("saturer").faire();
  ok("saturer : appliqué", VL.etat.doc.calques[0].objets[1].style.fond === "#808080");
  A.demander = async (spec) => { vu = spec.champs.map((c) => c.id).join(","); return { mode: "rvb", a: 0, b: 0, c: 0 }; };
  await A.action("equilibre").faire();
  ok("équilibre : ses champs", vu === "mode,a,b,c,d", vu);
  VL.etat.selection = [];
  ok("sans sélection : rien n'est possible", ["inverser", "gris", "saturer", "equilibre", "fusion_h", "fusion_v", "fusion_z"].every((k) => !A.action(k).peut()));
  ok("action inconnue : jamais possible", !A.action("zzz").peut());
  const VQ = vl(doc(R("a", 0, 300, "#000000"), R("b", 300, 0, "#ffffff"), R("c", 100, 100, "#ff0000"), R("d", 200, 200, "#00ff00")), ["a", "b", "c", "d"]);
  await couleurs_actions(VQ).action("fusion_v").faire();
  ok("fusion verticale (menu)", VQ.etat.doc.calques[0].objets[2].style.fond === "#aaaaaa");
  VL.etat.selection = ["a"];
  await A.action("fusion_v").faire();
  ok("fusion impossible : l'erreur est dite", VL.toasts.at(-1)[0] === T("vectorlab.couleurs.fusion_trois") && VL.toasts.at(-1)[1]);
}

if (echecs.length) {
  console.error(`couleurs : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("couleurs : ok");
