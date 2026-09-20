// effets.test.mjs — mod-effets (lot F) : effets de calque → <filter>, modes
// de fusion, motifs → <pattern>, dégradé conique → secteurs interpolés.
// Module feuille, états vides construits.
import { EFFETS, effet_defaut, effets_valider, filtre_svg, MODES_FUSION, MOTIFS, motif_defaut,
         motif_valider, motif_svg, conique_secteurs, conique_svg, couleur_interpoler } from "../js/mod-effets.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
const compte = (s, re) => (s.match(re) || []).length;

/* ── effets ── */
{
  ok("six effets nommés", JSON.stringify(EFFETS.map((e) => e.id)) === '["ombre","ombre_interne","lueur","biseau","contour","incrustation"]');
  const o = effet_defaut("ombre");
  ok("défaut ombre : type, décalage, flou, couleur, opacité", o.type === "ombre" && o.dx === 4 && o.dy === 4 && o.flou === 4 && /^#/.test(o.couleur) && o.opacite === 0.5, JSON.stringify(o));
  let refus = 0; try { effet_defaut("zz"); } catch { refus++; }
  ok("effet inconnu refusé", refus === 1);
  refus = 0;
  for (const mauvais of ["x", [{ type: "zz" }], [{ type: "ombre", flou: -1 }], [{ type: "lueur", opacite: 2 }], [{ type: "contour", largeur: 0 }], [{ type: "ombre", couleur: "rouge" }]]) {
    try { effets_valider(mauvais); } catch { refus++; }
  }
  ok("effets_valider refuse 6 listes malformées", refus === 6, String(refus));
  ok("état vide : liste vide valide", (() => { try { effets_valider([]); return true; } catch { return false; } })());
  const f = filtre_svg("fx_o1", [effet_defaut("ombre")]);
  ok("filtre ombre : <filter id> avec flou, décalage, flood, composite, merge", f.startsWith('<filter id="fx_o1"') && f.includes("feGaussianBlur") && f.includes('dx="4"') && f.includes("feFlood") && f.includes("feMerge") && f.endsWith("</filter>"), f);
  ok("la région dépasse la boîte (x −25 %, largeur 150 %)", f.includes('x="-25%"') && f.includes('width="150%"'));
  const tous = filtre_svg("fx", EFFETS.map((e) => effet_defaut(e.id)));
  ok("les six effets se chaînent dans un même filtre, le résultat final s'appelle SourceGraphic en dernier merge", compte(tous, /<fe/g) >= 12 && tous.includes('in="SourceGraphic"'), tous.slice(0, 200));
  ok("ombre interne : composite « out » + arithmétique", filtre_svg("f", [effet_defaut("ombre_interne")]).includes('operator="out"'));
  ok("biseau : lumière spéculaire", filtre_svg("f", [effet_defaut("biseau")]).includes("feSpecularLighting"));
  ok("contour : morphologie dilate à la largeur", filtre_svg("f", [{ ...effet_defaut("contour"), largeur: 3 }]).includes('operator="dilate" radius="3"'));
  ok("incrustation : flood de la couleur composé « in »", filtre_svg("f", [effet_defaut("incrustation")]).includes('operator="in"'));
  ok("état vide : sans effet → chaîne vide", filtre_svg("f", []) === "");
  ok("16 modes de fusion, normal en tête, multiply et screen présents", MODES_FUSION.length === 16 && MODES_FUSION[0] === "normal" && MODES_FUSION.includes("multiply") && MODES_FUSION.includes("screen") && MODES_FUSION.includes("luminosity"));
}
/* ── motifs ── */
{
  ok("quatre motifs", JSON.stringify(MOTIFS.map((m) => m.id)) === '["hachures","points","damier","grille"]');
  const h = motif_defaut("hachures");
  ok("hachures par défaut : pas 8, angle 45, épaisseur 1, couleur", h.type === "hachures" && h.pas === 8 && h.angle === 45 && h.epaisseur === 1 && /^#/.test(h.couleur), JSON.stringify(h));
  let refus = 0;
  for (const mauvais of [null, { type: "zz" }, { type: "hachures", pas: 0 }, { type: "points", couleur: 3 }, { type: "damier", pas: -2 }]) { try { motif_valider(mauvais); } catch { refus++; } }
  ok("motif_valider refuse 5 motifs malformés", refus === 5, String(refus));
  const p = motif_svg("m1", h);
  ok("hachures → pattern userSpaceOnUse de la taille du pas, tourné à l'angle, une ligne", p.startsWith('<pattern id="m1"') && p.includes('patternUnits="userSpaceOnUse"') && p.includes('width="8"') && p.includes("rotate(45)") && p.includes("<line") && p.endsWith("</pattern>"), p);
  ok("points → cercle ; damier → deux rects ; grille → deux lignes", motif_svg("a", motif_defaut("points")).includes("<circle") && compte(motif_svg("b", motif_defaut("damier")), /<rect/g) === 2 && compte(motif_svg("c", motif_defaut("grille")), /<line/g) === 2);
  ok("un fond de motif se dessine derrière", motif_svg("d", { ...h, fond: "#FFFFFF" }).includes('fill="#FFFFFF"'));
}
/* ── conique ── */
{
  ok("interpolation RGB : milieu de noir et blanc = #808080, bornes exactes", couleur_interpoler("#000000", "#FFFFFF", 0.5) === "#808080" && couleur_interpoler("#FF0000", "#0000FF", 0) === "#FF0000" && couleur_interpoler("#FF0000", "#0000FF", 1) === "#0000FF");
  const g = { type: "conique", cx: 50, cy: 50, r: 40, angle: 0, stops: [{ t: 0, couleur: "#FF0000" }, { t: 1, couleur: "#0000FF" }] };
  const s = conique_secteurs(g, 8);
  ok("8 secteurs, chacun un triangle fermé depuis le centre, couleurs de rouge vers bleu", s.length === 8 && s.every((x) => /^M 50 50 L .* Z$/.test(x.d)) && s[0].couleur === "#FF0000" && s[7].couleur !== "#FF0000", JSON.stringify(s[0]));
  ok("le premier secteur part à l'angle (0° = vers la droite), rayon ×1,5 pour couvrir les coins du carré", /L 110(\.0+)? 50(\.0+)? /.test(s[0].d), s[0].d);
  const sv = conique_svg("g9", g);
  ok("pattern conique : userSpaceOnUse sur le carré [cx−r, cx+r]², 72 secteurs", sv.includes('x="10" y="10" width="80" height="80"') && compte(sv, /<path/g) === 72 && sv.includes('id="g9"'), sv.slice(0, 160));
  ok("secteurs en décalage d'angle : le premier commence à 90°", /L 50(\.0+)? 110(\.0+)? /.test(conique_secteurs({ ...g, angle: 90 }, 4)[0].d));
  let refus = 0; try { conique_secteurs({ ...g, stops: [] }, 8); } catch { refus++; }
  ok("état vide : sans stop refusé", refus === 1);
}

if (echecs.length) {
  console.error("ECHECS effets :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA effets : PASS (27 controles)");
