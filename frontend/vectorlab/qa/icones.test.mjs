// icones.test.mjs — mod-icones : le sprite d'icônes fines (trait 1,5,
// viewBox 24, monochrome currentColor) — une icône par outil des deux
// personas, un repli générique pour l'inconnu. Feuille.
import { ICONES, icone_svg, outils_sans_icone } from "../js/mod-icones.js";
import { FAMILLES } from "../js/mod-familles.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
{
  const tous = FAMILLES.flatMap((f) => f.membres.map((m) => m.outil));
  ok("une icône par outil de toutes les familles", outils_sans_icone(tous).length === 0, outils_sans_icone(tous).join(","));
  const s = icone_svg("rect");
  ok("svg : viewBox 24, trait currentColor 1.5, sans remplissage, classe ic", s.startsWith('<svg class="ic" viewBox="0 0 24 24"') && s.includes('stroke="currentColor"') && s.includes('stroke-width="1.5"') && s.includes('fill="none"'), s);
  ok("taille : width/height posés", icone_svg("rect", 18).includes('width="18" height="18"'));
  ok("inconnu : le repli (un carré pointillé) et pas une exception", icone_svg("zz").includes("stroke-dasharray") && outils_sans_icone(["zz", "rect"]).join() === "zz");
  ok("état vide : liste vide → aucun manquant", outils_sans_icone([]).length === 0 && outils_sans_icone(undefined).length === 0);
  ok("chaque icône est un fragment SVG non vide sans script", Object.values(ICONES).every((v) => typeof v === "string" && v.length > 10 && !/script|on\w+=/i.test(v)));
}
if (echecs.length) { console.error("ECHECS icones :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA icones : PASS (6 controles)");
