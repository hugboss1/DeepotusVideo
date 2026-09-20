// typo.test.mjs — Texte & logo : mod-typo pur (familles de polices,
// @font-face, validation d'un fichier de police par magic, glyphes séparés
// et texte multi-lignes par opentype sur la vraie Anton.ttf) et le modèle
// (texte multi-lignes en tspans, ancre, vectorisation en un chemin par
// glyphe → groupe). Aucun DOM.
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { polices_toutes, font_face_css, police_fichier_valide, glyphes_separes, texte_multi_d, lignes_de } from "../js/mod-typo.js";
import { POLICES } from "../js/mod-texte3d.js";
import { parserDoc, compilerSVG, op_texte_vectoriser, chemin_parser } from "../js/mod-doc.js";

const require = createRequire(import.meta.url);
const opentype = require("../vendor/opentype.min.js");
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
const compte = (s, re) => (s.match(re) || []).length;
const font = opentype.parse(readFileSync(new URL("../../dist/fonts/Anton.ttf", import.meta.url)).buffer.slice(0));

/* ── familles et @font-face ── */
{
  const t = polices_toutes(POLICES, [{ nom: "MaTypo.ttf" }], ["Arial"]);
  ok("toutes : bibliothèque (source lib), déposées (user, famille = nom sans extension), système ; ids uniques",
     t.filter((p) => p.source === "lib").length === POLICES.length && t.some((p) => p.source === "user" && p.famille === "MaTypo" && p.url === "/api/fonts/user/MaTypo.ttf")
     && t.some((p) => p.source === "systeme" && p.famille === "Arial") && new Set(t.map((p) => p.id)).size === t.length, JSON.stringify(t.slice(-2)));
  ok("état vide : sans dépôt ni système → la bibliothèque seule", polices_toutes(POLICES, [], []).length === POLICES.length);
  const css = font_face_css(polices_toutes(POLICES, [{ nom: "MaTypo.ttf" }], ["Arial"]));
  ok("@font-face : une règle par police à URL (lib + user), aucune pour le système, famille et url citées", compte(css, /@font-face/g) === POLICES.length + 1 && css.includes('font-family: "Anton"') && css.includes('url("/fonts/Anton.ttf")') && css.includes('url("/api/fonts/user/MaTypo.ttf")') && !css.includes("Arial"), css.slice(0, 200));
  const ttf = readFileSync(new URL("../../dist/fonts/Anton.ttf", import.meta.url));
  ok("police_fichier_valide : TTF vrai accepté (magic 00010000), OTF (OTTO), WOFF (wOFF), WOFF2 (wOF2)", police_fichier_valide("a.ttf", ttf) && police_fichier_valide("b.otf", Buffer.from("OTTO1234")) && police_fichier_valide("c.woff", Buffer.from("wOFF1234")) && police_fichier_valide("d.woff2", Buffer.from("wOF21234")));
  ok("refusés : extension inconnue, magic faux, nom hors patron, vide", !police_fichier_valide("a.png", ttf) && !police_fichier_valide("a.ttf", Buffer.from("PNG.....")) && !police_fichier_valide("../a.ttf", ttf) && !police_fichier_valide("a.ttf", Buffer.alloc(0)));
}
/* ── glyphes et multi-lignes (opentype réel) ── */
{
  const g = glyphes_separes(font, "AB C", 40, 10, 50, 0);
  ok("glyphes séparés : un chemin par caractère NON blanc, dans l'ordre, chacun fermé, x croissant", g.length === 3 && g.map((x) => x.car).join("") === "ABC" && g.every((x) => /Z$/.test(x.d)) && g[0].x < g[1].x && g[1].x < g[2].x, JSON.stringify(g.map((x) => [x.car, x.x])));
  ok("un glyphe a une bbox : le A fait ≈ 40 de haut", (() => { let y0 = 1e9, y1 = -1e9; for (const s of chemin_parser(g[0].d)) for (let k = 1; k < s.p.length; k += 2) { y0 = Math.min(y0, s.p[k]); y1 = Math.max(y1, s.p[k]); } return y1 - y0 > 25 && y1 - y0 < 45; })());
  ok("état vide : texte vide ou blanc → []", glyphes_separes(font, "", 40, 0, 0).length === 0 && glyphes_separes(font, "  ", 40, 0, 0).length === 0);
  ok("lignes_de : coupe aux retours, garde les vides intermédiaires, retire les fins", JSON.stringify(lignes_de("a\nb\n\nc\n")) === JSON.stringify(["a", "b", "", "c"]) && JSON.stringify(lignes_de("")) === JSON.stringify([""]));
  const d1 = texte_multi_d(font, ["A"], 40, 10, 50, 0, 1.2, "start"), d2 = texte_multi_d(font, ["A", "A"], 40, 10, 50, 0, 1.2, "start");
  ok("multi-lignes : deux lignes = deux fois plus de segments, la seconde descendue de corps × interligne", compte(d2, /M /g) === 2 * compte(d1, /M /g) && (() => { let y = -1e9; for (const s of chemin_parser(d2)) for (let k = 1; k < s.p.length; k += 2) y = Math.max(y, s.p[k]); return y > 50 + 40 * 1.2 - 2 && y < 50 + 40 * 1.2 + 2; })(), d2.slice(0, 80));
  const dm = texte_multi_d(font, ["A"], 40, 100, 50, 0, 1.2, "middle"), de = texte_multi_d(font, ["A"], 40, 100, 50, 0, 1.2, "end");
  const xmin = (d) => { let x = 1e9; for (const s of chemin_parser(d)) for (let k = 0; k < s.p.length; k += 2) x = Math.min(x, s.p[k]); return x; };
  ok("ancre : middle centre sur x, end finit à x", xmin(dm) < 100 && xmin(dm) > 70 && xmin(de) < xmin(dm), [xmin(dm), xmin(de)].join(","));
}
/* ── modèle ── */
{
  const base = () => ({ v: 1, taille: { w: 300, h: 200 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
    { id: "t1", type: "texte", x: 20, y: 60, contenu: "Deep\nOtus", style: { fond: "#1F1512", corps: 30, police: "Anton", interligne: 1.1, ancre: "middle" } }] }] });
  const svg = compilerSVG(base());
  ok("texte multi-lignes : <text> avec deux <tspan x dy>, la seconde à dy = corps × interligne, text-anchor middle", compte(svg, /<tspan/g) === 2 && svg.includes('dy="33"') && svg.includes('text-anchor="middle"') && svg.includes(">Deep</tspan>") && svg.includes(">Otus</tspan>"), svg);
  ok("une seule ligne : compilation inchangée (pas de tspan)", !compilerSVG({ ...base(), calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [{ id: "t1", type: "texte", x: 20, y: 60, contenu: "Deep", style: { corps: 30 } }] }] }).includes("<tspan"));
  ok("parserDoc refuse une ancre inconnue", (() => { const d = base(); d.calques[0].objets[0].style.ancre = "gauche"; try { parserDoc(d); return false; } catch { return true; } })());
  const d = base();
  const ids = op_texte_vectoriser(d, "t1", [{ car: "D", d: "M 0 0 L 10 0 L 10 10 Z" }, { car: "O", d: "M 20 0 L 30 0 L 30 10 Z" }]);
  const g = d.calques[0].objets[0];
  ok("vectoriser par glyphe : le texte devient un GROUPE (même id) de chemins aux ids neufs, fond et evenodd gardés, un data-car par chemin",
     g.type === "groupe" && g.id === "t1" && g.enfants.length === 2 && ids.length === 2 && !ids.includes("t1") && g.enfants[0].style.fond === "#1F1512" && g.enfants[0].style.regle === "evenodd" && g.enfants[1].car === "O", JSON.stringify(g));
  ok("vectoriser en un seul chemin : inchangé (path même id)", (() => { const e = base(); op_texte_vectoriser(e, "t1", "M 0 0 L 10 0 L 10 10 Z"); return e.calques[0].objets[0].type === "path" && e.calques[0].objets[0].id === "t1"; })());
  ok("état vide : liste vide refusée", (() => { try { op_texte_vectoriser(base(), "t1", []); return false; } catch { return true; } })());
}
if (echecs.length) {
  console.error("ECHECS typo :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA typo : PASS (17 controles)");
