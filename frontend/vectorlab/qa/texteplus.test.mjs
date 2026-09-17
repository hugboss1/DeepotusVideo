// texteplus.test.mjs — lot F : cadre de texte (mesure injectable, coupe des
// lignes, tspans alignés / justifiés, débordement) et texte sur chemin ;
// les objets `cadre` et `textechemin` du modèle.
import { mesure_approx, couper_lignes, cadre_tspans } from "../js/mod-texteplus.js";
import { parserDoc, compilerSVG, op_texte_en_cadre, op_texte_sur_chemin, op_textechemin_decalage, op_deplacer,
         op_redimensionner, bbox_objet } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
const compte = (s, re) => (s.match(re) || []).length;
const essaie = (fn) => { try { fn(); return true; } catch { return false; } };
const style = { corps: 10 };

/* ── mesure et coupe ── */
{
  ok("mesure approximative : 0,55 × corps par caractère, gras un peu plus large", mesure_approx("abcd", style) === 22 && mesure_approx("abcd", { corps: 10, graisse: "bold" }) > 22 && mesure_approx("", style) === 0);
  const l = couper_lignes("un deux trois quatre", 60, style);
  ok("coupe aux mots : « un deux » (38,5) tient dans 60, « trois » passe à la ligne", JSON.stringify(l) === JSON.stringify(["un deux", "trois", "quatre"]), JSON.stringify(l));
  ok("un retour forcé coupe toujours", JSON.stringify(couper_lignes("a\nb c", 200, style)) === JSON.stringify(["a", "b c"]));
  ok("un mot plus long que la largeur se coupe aux caractères", JSON.stringify(couper_lignes("abcdefghij", 30, style)) === JSON.stringify(["abcde", "fghij"]), JSON.stringify(couper_lignes("abcdefghij", 30, style)));
  ok("état vide : contenu vide → une ligne vide", JSON.stringify(couper_lignes("", 100, style)) === JSON.stringify([""]));
  ok("la mesure est injectable", JSON.stringify(couper_lignes("aa bb", 10, style, (t) => t.length)) === JSON.stringify(["aa bb"]));
}
/* ── tspans ── */
{
  const o = { x: 10, y: 20, w: 100, h: 50, style: { corps: 10, interligne: 1.5, aligner: "gauche" } };
  const g = cadre_tspans(o, ["un", "deux"]);
  ok("gauche : x = x du cadre, y = y + corps puis + corps × interligne", g.html.includes('<tspan x="10" y="30">un</tspan>') && g.html.includes('<tspan x="10" y="45">deux</tspan>') && !g.deborde, g.html);
  const c = cadre_tspans({ ...o, style: { corps: 10, aligner: "centre" } }, ["un"]);
  ok("centre : x au milieu, text-anchor middle", c.html.includes('x="60"') && c.html.includes('text-anchor="middle"'), c.html);
  const d = cadre_tspans({ ...o, style: { corps: 10, aligner: "droite" } }, ["un"]);
  ok("droite : x au bord droit, text-anchor end", d.html.includes('x="110"') && d.html.includes('text-anchor="end"'), d.html);
  const j = cadre_tspans({ ...o, style: { corps: 10, aligner: "justifie" } }, ["un deux", "trois"]);
  ok("justifié : textLength = largeur sur les lignes pleines, pas sur la dernière ni un mot seul", compte(j.html, /textLength="100"/g) === 1 && j.html.includes('lengthAdjust="spacing"') && !j.html.includes('>trois</tspan>') === false, j.html);
  const r = cadre_tspans({ ...o, style: { corps: 10, retrait: 8 } }, ["un", "deux"]);
  ok("retrait : la première ligne seulement", r.html.includes('x="18"') && r.html.includes('x="10" y'));
  const deb = cadre_tspans({ ...o, h: 12 }, ["a", "b", "c"]);
  ok("débordement : les lignes sous le cadre tombent, deborde = vrai", compte(deb.html, /<tspan/g) === 1 && deb.deborde === true);
  ok("le contenu est échappé", cadre_tspans(o, ["a<b"]).html.includes("a&lt;b"));
}
/* ── modèle : cadre ── */
{
  const base = () => ({ v: 1, nom: "T", taille: { w: 300, h: 200 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
    { id: "t1", type: "texte", x: 10, y: 40, contenu: "Verre et plomb du vitrail", style: { fond: "#1F1512", corps: 10 } },
    { id: "p1", type: "path", d: "M 20 100 C 60 20 140 20 180 100", style: { contour: "#000000", epaisseur: 1 } },
  ] }] });
  const d = base();
  op_texte_en_cadre(d, "t1", 60, 40);
  const o = d.calques[0].objets[0];
  ok("texte → cadre : type cadre, x gardé, y remonté du corps, w/h posés, contenu et style gardés", o.type === "cadre" && o.x === 10 && o.y === 30 && o.w === 60 && o.h === 40 && o.contenu.startsWith("Verre") && o.style.corps === 10, JSON.stringify(o));
  const svg = compilerSVG(d);
  ok("compilé : <text data-objet=t1> avec plusieurs tspans (la coupe à 60 px), fond du style", svg.includes('<text data-objet="t1"') && compte(svg, /<tspan/g) >= 3 && svg.includes('fill="#1F1512"'), svg);
  ok("la mesure du navigateur s'injecte par opts.mesure", compte(compilerSVG(d, { mesure: () => 1 }), /<tspan/g) === 1);
  op_deplacer(d, ["t1"], 5, 5); op_redimensionner(d, ["t1"], { x: 15, y: 35, w: 60, h: 40 }, { x: 15, y: 35, w: 120, h: 40 });
  ok("déplacer / redimensionner un cadre : x, y, w ; bbox = le cadre", o.x === 15 && o.y === 35 && o.w === 120 && JSON.stringify(bbox_objet(o)) === JSON.stringify({ x: 15, y: 35, w: 120, h: 40 }), JSON.stringify(o));
  ok("parserDoc refuse un cadre sans taille ou sans contenu", !essaie(() => { const x = base(); x.calques[0].objets.push({ id: "k", type: "cadre", x: 0, y: 0, w: 0, h: 10, contenu: "a", style: {} }); parserDoc(x); })
     && !essaie(() => { const x = base(); x.calques[0].objets.push({ id: "k", type: "cadre", x: 0, y: 0, w: 10, h: 10, contenu: 3, style: {} }); parserDoc(x); }));
  ok("texte introuvable ou taille nulle refusés", !essaie(() => op_texte_en_cadre(base(), "zz", 10, 10)) && !essaie(() => op_texte_en_cadre(base(), "t1", 0, 10)));
  // texte sur chemin
  const e = base();
  op_texte_sur_chemin(e, "t1", "p1");
  const tc = e.calques[0].objets[0];
  ok("texte → textechemin : le d du chemin est COPIÉ, décalage 0, le chemin reste", tc.type === "textechemin" && tc.d === "M 20 100 C 60 20 140 20 180 100" && tc.decalage === 0 && e.calques[0].objets[1].type === "path", JSON.stringify(tc));
  const s2 = compilerSVG(e);
  ok("compilé : <g data-objet=t1> avec un <path id=tp_t1> invisible et <textPath href=#tp_t1 startOffset=0%>", s2.includes('<g data-objet="t1"') && s2.includes('<path id="tp_t1"') && s2.includes('<textPath href="#tp_t1" startOffset="0%">Verre') && compte(s2, /data-objet="t1"/g) === 1, s2);
  op_textechemin_decalage(e, "t1", 25);
  ok("décalage 25 %", compilerSVG(e).includes('startOffset="25%"') && !essaie(() => op_textechemin_decalage(e, "t1", 120)));
  op_deplacer(e, ["t1"], 10, 0);
  ok("déplacer un texte sur chemin décale son d", tc.d.startsWith("M 30 100"), tc.d);
  ok("texte sur un objet qui n'est pas un chemin : refusé", !essaie(() => { const x = base(); x.calques[0].objets.push({ id: "r", type: "rect", x: 0, y: 0, w: 5, h: 5, style: {} }); op_texte_sur_chemin(x, "t1", "r"); }));
}

if (echecs.length) {
  console.error("ECHECS texteplus :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA texteplus : PASS (24 controles)");
