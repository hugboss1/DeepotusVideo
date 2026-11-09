// recolorerui.test.mjs — lot D5 « Couleur et motif » (t477) : Recolorer l'illustration. Les tables pures de
// js/mod-recolorer.js (réduire à N couleurs, harmoniser, mélanger) et l'action du menu (js/mod-recolorerui.js, VL factice).
import { reduire, harmoniser, melanger } from "../js/mod-recolorer.js";
import { couleurs_actions } from "../js/mod-recolorerui.js";
import { T } from "../js/mod-i18n.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : ""));
};
const refus = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
const C = (...l) => l.map(([hex, n]) => ({ hex, n }));

/* ── réduire ── */
{
  const c = C(["#ff0000", 5], ["#0000ff", 3], ["#fe0000", 1]);
  const t2 = reduire(c, 2);
  ok("réduire à 2 : les rouges proches se rejoignent sur le plus employé", t2["#fe0000"] === "#ff0000" && t2["#ff0000"] === "#ff0000" && t2["#0000ff"] === "#0000ff", JSON.stringify(t2));
  const t1 = reduire(c, 1);
  ok("réduire à 1 : tout vers la couleur du groupe le plus employé", Object.values(t1).every((h) => h === "#ff0000"), JSON.stringify(t1));
  ok("réduire à N ≥ nombre de couleurs : identité", Object.entries(reduire(c, 3)).every(([a, b]) => a === b) && Object.keys(reduire(c, 9)).length === 3);
  // la distance est perceptive (Lab) : le gris moyen est plus proche du gris clair que du jaune vif
  const t = reduire(C(["#ffff00", 4], ["#c8c8c8", 3], ["#808080", 1]), 2);
  ok("distance perceptive (Lab)", t["#808080"] === "#c8c8c8" && t["#ffff00"] === "#ffff00", JSON.stringify(t));
  // les deux noirs proches se rejoignent (6 usages) : leur couleur l'emporte sur le gris seul pourtant plus employé (4)
  const t3 = reduire(C(["#000000", 3], ["#030303", 3], ["#0a0a0a", 4]), 1);
  ok("fusion : le total des usages décide du représentant", Object.values(t3).every((h) => h === "#000000"), JSON.stringify(t3));
  const tg = reduire(C(["#000000", 3], ["#080808", 2], ["#101010", 1]), 2);
  ok("Lab avec la courbe gamma de sRGB (les noirs proches)", tg["#080808"] === "#000000" && tg["#101010"] === "#101010", JSON.stringify(tg));
  ok("réduire : N non entier → refus traduit", refus(() => reduire(c, 2.5)) === T("vectorlab.couleurs.borne", { min: 1, max: 64 }));
  ok("réduire : N hors bornes → refus traduit", refus(() => reduire(c, 0)) === T("vectorlab.couleurs.borne", { min: 1, max: 64 }));
}

/* ── harmoniser ── */
{
  const c = C(["#ff0000", 5], ["#808080", 2], ["#00ff00", 1]);
  const t = harmoniser(c, "complementaire");
  ok("complémentaire : la base garde sa teinte, la suivante passe à l'opposé, le gris reste", t["#ff0000"] === "#ff0000" && t["#00ff00"] === "#00ffff" && t["#808080"] === "#808080", JSON.stringify(t));
  ok("triade : 120°", harmoniser(c, "triade")["#00ff00"] === "#00ff00");
  const a = harmoniser(C(["#ff0000", 3], ["#00ff00", 2], ["#0000ff", 1]), "analogue");
  ok("analogue : 0, +30°, −30°", a["#00ff00"] === "#ff8000" && a["#0000ff"] === "#ff0080", JSON.stringify(a));
  ok("monochrome : une seule teinte, clarté et saturation gardées", harmoniser(C(["#ff0000", 2], ["#4040bf", 1]), "monochrome")["#4040bf"] === "#bf4040");
  ok("la base est la PREMIÈRE couleur colorée (les gris ne comptent pas)", harmoniser(C(["#808080", 9], ["#00ff00", 2], ["#ff0000", 1]), "complementaire")["#ff0000"] === "#ff00ff");
  ok("que des gris : identité", Object.entries(harmoniser(C(["#808080", 1], ["#ffffff", 1]), "triade")).every(([x, y]) => x === y));
  ok("l'ordre d'usage est refait (entrée non triée)", harmoniser(C(["#00ff00", 1], ["#ff0000", 5]), "complementaire")["#00ff00"] === "#00ffff");
  ok("règle inconnue → refus traduit", refus(() => harmoniser(c, "pentade")) === T("vectorlab.couleur.harm_inconnue", { type: "pentade" }));
}

/* ── mélanger ── */
{
  const c = C(["#111111", 1], ["#222222", 1], ["#333333", 1], ["#444444", 1]);
  const m = melanger(c, 7);
  const vals = Object.values(m).sort(), cles = Object.keys(m).sort();
  ok("mélanger : une permutation des mêmes couleurs", JSON.stringify(vals) === JSON.stringify(cles));
  ok("mélanger : jamais l'identité (au moins deux couleurs)", Object.entries(m).some(([x, y]) => x !== y) && [1, 2, 3, 4, 5, 6, 8].every((g) => Object.entries(melanger(c, g)).some(([x, y]) => x !== y)));
  ok("mélanger : la graine fixe le tirage", JSON.stringify(melanger(c, 7)) === JSON.stringify(m));
  ok("mélanger : deux graines donnent au moins un autre tirage", [1, 2, 3, 4, 5].some((g) => JSON.stringify(melanger(c, g)) !== JSON.stringify(m)));
  ok("mélanger deux couleurs : toujours échangées, quelle que soit la graine", Array.from({ length: 20 }, (_, g) => melanger(C(["#111111", 1], ["#222222", 1]), g + 1)).every((x) => x["#111111"] === "#222222"));
  ok("mélanger une seule couleur : identité", JSON.stringify(melanger(C(["#111111", 1]), 3)) === JSON.stringify({ "#111111": "#111111" }));
}

/* ── l'action du menu (VL factice) ── */
const doc = () => ({ v: 1, taille: { w: 100, h: 100 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
  { id: "a", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "#ff0000", contour: "#000000" } },
  { id: "b", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "#ff0000" } },
  { id: "n", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "none" } }] }] });
const vl = (d, sel) => {
  const VL = { etat: { doc: d, selection: sel }, toasts: [],
    executer(fn, ...a) { try { const x = JSON.parse(JSON.stringify(VL.etat.doc)); const r = fn(x, ...a); VL.etat.doc = x; return r; } catch (e) { VL.toast(e.message, true); return undefined; } },
    toast(m, e) { VL.toasts.push([m, !!e]); }, rendre() {} };
  return VL;
};
{
  const VL = vl(doc(), ["a", "b"]);
  const A = couleurs_actions(VL);
  let spec = null, vu = null;
  A.demanderRecolorer = async (s) => { spec = s; s.surChange({ "#ff0000": "#00ff00" }); vu = VL.etat.doc.calques[0].objets[1].style.fond; return null; };
  ok("recolorer : possible avec une sélection", A.action("recolorer").peut());
  await A.action("recolorer").faire();
  ok("recolorer : le dialogue reçoit les couleurs de la sélection, par usage", spec && spec.couleurs.length === 2 && spec.couleurs[0].hex === "#ff0000" && spec.couleurs[0].n === 2 && spec.titre === T("vectorlab.recolorer.d_titre"), JSON.stringify(spec && spec.couleurs));
  ok("recolorer : aperçu en direct, Annuler rend l'avant", vu === "#00ff00" && VL.etat.doc.calques[0].objets[1].style.fond === "#ff0000");
  A.demanderRecolorer = async () => ({ "#ff0000": "#123456", "#000000": "#000000" });
  await A.action("recolorer").faire();
  ok("recolorer : appliqué en une exécution", VL.etat.doc.calques[0].objets[0].style.fond === "#123456" && VL.etat.doc.calques[0].objets[1].style.fond === "#123456" && VL.etat.doc.calques[0].objets[0].style.contour === "#000000");
  const V2 = vl(doc(), ["n"]);
  const A2 = couleurs_actions(V2);
  let ouvert = false;
  A2.demanderRecolorer = async () => { ouvert = true; return null; };
  await A2.action("recolorer").faire();
  ok("aucune couleur : dit, sans dialogue", !ouvert && V2.toasts.at(-1)[0] === T("vectorlab.recolorer.aucune_couleur") && V2.toasts.at(-1)[1]);
  V2.etat.selection = [];
  ok("sans sélection : impossible", !A2.action("recolorer").peut());
}

if (echecs.length) {
  console.error(`recolorerui : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("recolorerui : ok");
