// icones.test.mjs — mod-icones : depuis G3 (10/10/2026) chaque outil, action
// contextuelle et type de rangée pointe sur SA clé de la suite « Deepotus
// Glyph » (/shared/icons) ; hors navigateur dzi rend une référence au sprite
// servi ; l'inconnu reçoit la clé de repli dz-etat-inconnu. Feuille.
import { ICONES, RANGEES, REPLI, dzi, icone_svg, icone_rangee, outils_sans_icone } from "../js/mod-icones.js";
import { FAMILLES } from "../js/mod-familles.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
{
  const tous = FAMILLES.flatMap((f) => f.membres.map((m) => m.outil));
  ok("une icône par outil de toutes les familles", outils_sans_icone(tous).length === 0, outils_sans_icone(tous).join(","));
  const s = icone_svg("rect");
  ok("svg : la clé de la suite (rect → dz-outil-vec-rectangle), classes dzi + ic + taille, décoratif", s.startsWith('<svg class="dzi ic dzi--18"') && s.includes('href="/shared/icons/dz-icons.svg#dz-outil-vec-rectangle"') && s.includes('aria-hidden="true"'), s);
  ok("taille : width/height posés", icone_svg("rect", 18).includes('width="18" height="18"') && icone_rangee("path", 14).includes('width="14" height="14"'));
  ok("inconnu : le repli dz-etat-inconnu et pas une exception", REPLI === "dz-etat-inconnu" && icone_svg("zz").includes("#dz-etat-inconnu") && icone_rangee("zz").includes("#dz-etat-inconnu") && outils_sans_icone(["zz", "rect"]).join() === "zz");
  ok("état vide : liste vide → aucun manquant", outils_sans_icone([]).length === 0 && outils_sans_icone(undefined).length === 0);
  ok("chaque entrée est une clé dz-* (aucun fragment SVG maison)", [...Object.values(ICONES), ...Object.values(RANGEES)].every((v) => /^dz-[a-z0-9-]+$/.test(v)));
  // dans la page, le runtime /shared/icons/dz-icons.js (window.dzIcone) rend l'icône
  globalThis.dzIcone = (cle, o) => `[${cle}|${o.taille}|${o.classe}]`;
  ok("avec le runtime : dzIcone(clé, {taille, classe})", icone_svg("plume", 18) === "[dz-outil-vec-plume|18|ic dzi--18]" && dzi("dz-action-aide", 14) === "[dz-action-aide|14|]");
  delete globalThis.dzIcone;
}
if (echecs.length) { console.error("ECHECS icones :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA icones : PASS (7 controles)");
