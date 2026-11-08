// importsvg.test.mjs — lot D4 « Interop » (t469) : lire un SVG en objets du Vectorlab (js/mod-importsvg.js, pur).
// Lecteur XML maison (pas de DOMParser sous node), éléments, chemins normalisés (relatifs, H V S T, arcs → cubiques),
// styles (attributs, style="", classes de <style>, héritage), transforms, viewBox, use, textes ; ce qui est ignoré
// est compté.
import { createRequire } from "node:module";
import { svg_vers_objets, chemin_normaliser, xml_lire } from "../js/mod-importsvg.js";
import { polylignes_objet, fournirMartinez, versMulti, aplatir_objet, aire_multi } from "../js/mod-bool.js";
import { chemin_parser } from "../js/mod-doc.js";
import { T } from "../js/mod-i18n.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 240) : ""));
};
const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
const refus = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
const aire = (o) => aire_multi(versMulti(aplatir_objet(o)));
const pts = (o) => polylignes_objet(o).flatMap((l) => l.points);
const proche = (o, x, y) => pts(o).reduce((m, p) => Math.min(m, Math.hypot(p[0] - x, p[1] - y)), Infinity);
const svg = (corps, attrs = 'width="400" height="300"') => `<?xml version="1.0"?><!DOCTYPE svg><svg xmlns="http://www.w3.org/2000/svg" ${attrs}>${corps}</svg>`;
const un = (corps, attrs) => svg_vers_objets(svg(corps, attrs)).objets[0];
const commandes = (d) => (d.match(/[A-Za-z]/g) || []).join("");

/* ── le lecteur XML ── */
{
  const r = xml_lire(`<?xml version="1.0"?><!-- c --><a x="1" y='2'><b/><c>t &amp; &lt;u&gt; &#65;&#x42;<![CDATA[<d>]]></c></a>`);
  ok("xml : racine, attributs aux deux guillemets", r.nom === "a" && r.attrs.x === "1" && r.attrs.y === "2");
  ok("xml : enfants, élément vide, commentaire ignoré", r.enfants.length === 2 && r.enfants[0].nom === "b" && r.enfants[1].nom === "c");
  ok("xml : entités et CDATA dans le texte", r.enfants[1].texte === "t & <u> AB<d>", r.enfants[1].texte);
  ok("xml : noms à préfixe (xlink:href)", xml_lire(`<u xlink:href="#a"/>`).attrs["xlink:href"] === "#a");
  ok("xml : mal formé → refus traduit", refus(() => xml_lire("<a><b></a>")) === T("vectorlab.importer.xml_invalide") && refus(() => xml_lire("pas du xml")) === T("vectorlab.importer.xml_invalide"));
  ok("xml : balise fermante qui ne correspond pas, élément non fermé", refus(() => xml_lire("<a><b></c></a>")) !== null && refus(() => xml_lire("<a><b/>")) !== null);
}
/* ── les chemins ── */
{
  ok("chemin absolu inchangé (M L C Q Z)", commandes(chemin_normaliser("M0 0 L10 0 C10 5 5 10 0 10 Q-5 5 0 0 Z")) === "MLCQZ");
  ok("relatif → absolu", chemin_normaliser("m10 10 l5 0 l0 5 z") === "M10 10 L15 10 L15 15 Z", chemin_normaliser("m10 10 l5 0 l0 5 z"));
  ok("H et V → L", chemin_normaliser("M0 0 H10 V20 h-5 v-5") === "M0 0 L10 0 L10 20 L5 20 L5 15", chemin_normaliser("M0 0 H10 V20 h-5 v-5"));
  ok("M suivi de paires implicites → L", chemin_normaliser("M0 0 10 0 10 10") === "M0 0 L10 0 L10 10");
  ok("m relatif suivi de paires → l relatives", chemin_normaliser("m1 1 2 0 0 2") === "M1 1 L3 1 L3 3");
  ok("nombres serrés (1.5.5, -1-2, 1e1)", chemin_normaliser("M1.5.5L-1-2L1e1 0") === "M1.5 0.5 L-1 -2 L10 0", chemin_normaliser("M1.5.5L-1-2L1e1 0"));
  ok("S : poignée réfléchie de la C précédente", chemin_normaliser("M0 0 C0 10 10 10 10 0 S20 -10 20 0") === "M0 0 C0 10 10 10 10 0 C10 -10 20 -10 20 0", chemin_normaliser("M0 0 C0 10 10 10 10 0 S20 -10 20 0"));
  ok("S sans C avant : poignée = point courant", chemin_normaliser("M0 0 S10 10 20 0") === "M0 0 C0 0 10 10 20 0");
  ok("S après une Q : poignée = point courant", chemin_normaliser("M0 0 Q5 10 10 0 S20 -10 20 0") === "M0 0 Q5 10 10 0 C10 0 20 -10 20 0", chemin_normaliser("M0 0 Q5 10 10 0 S20 -10 20 0"));
  ok("T : poignée réfléchie de la Q précédente", chemin_normaliser("M0 0 Q5 10 10 0 T20 0") === "M0 0 Q5 10 10 0 Q15 -10 20 0", chemin_normaliser("M0 0 Q5 10 10 0 T20 0"));
  ok("après Z, le point courant revient au départ du sous-chemin", chemin_normaliser("M5 5 l10 0 z l0 10") === "M5 5 L15 5 Z L5 15", chemin_normaliser("M5 5 l10 0 z l0 10"));
  // arcs : un cercle de rayon 50 en deux demi-arcs, drapeaux serrés (« 01 »)
  const c = chemin_normaliser("M50 100 A50 50 0 1 0 150 100 a50 50 0 10-100 0Z");
  ok("arc → cubiques seulement", /^M[^A]*Z$/.test(c) && commandes(c).replace(/C/g, "") === "MZ", c);
  const o = { type: "path", d: c };
  ok("arc : l'aire d'un cercle de rayon 50 (± 1 %)", pres(aire(o), Math.PI * 2500, Math.PI * 25), aire(o));
  ok("arc : le point d'arrivée est exact", /150 100/.test(c) && proche(o, 100, 50) < 0.6 && proche(o, 100, 150) < 0.6);
  ok("arc à rayon nul → une ligne", chemin_normaliser("M0 0 A0 0 0 0 1 10 10") === "M0 0 L10 10");
  ok("arc à un seul rayon nul → une ligne", chemin_normaliser("M0 0 A0 5 0 0 1 10 10") === "M0 0 L10 10");
  ok("arc trop petit : rayons agrandis (le point d'arrivée reste)", /20 0$/.test(chemin_normaliser("M0 0 A1 1 0 0 1 20 0")), chemin_normaliser("M0 0 A1 1 0 0 1 20 0"));
  ok("arc trop petit : demi-cercle de rayon 10", proche({ type: "path", d: chemin_normaliser("M0 0 A1 1 0 0 1 20 0") }, 10, -10) < 0.6);
  const long = (d) => { const p = pts({ type: "path", d: chemin_normaliser(d) }); let s = 0; for (let k = 1; k < p.length; k++) s += Math.hypot(p[k][0] - p[k - 1][0], p[k][1] - p[k - 1][1]); return s; };
  ok("arc : petit (drapeaux 0 0) = un quart de cercle", pres(long("M0 0 A10 10 0 0 0 10 10"), 5 * Math.PI, 0.2), long("M0 0 A10 10 0 0 0 10 10"));
  ok("arc : grand (drapeaux 1 0) = trois quarts", pres(long("M0 0 A10 10 0 1 0 10 10"), 15 * Math.PI, 0.5), long("M0 0 A10 10 0 1 0 10 10"));
  ok("le résultat se relit par chemin_parser", chemin_parser(c).length > 2);
  ok("chemin invalide → refus traduit", refus(() => chemin_normaliser("M0 0 X1 1")) === T("vectorlab.importer.chemin_invalide"));
}
/* ── éléments ── */
{
  const r = un('<rect x="10" y="20" width="30" height="40" fill="#f00"/>');
  ok("rect", r.type === "rect" && r.x === 10 && r.y === 20 && r.w === 30 && r.h === 40 && r.style.fond === "#ff0000" && r.style.contour === "none", JSON.stringify(r));
  const rr = un('<rect x="0" y="0" width="100" height="50" rx="10"/>');
  ok("rect arrondi → chemin, aire = rectangle − coins", rr.type === "path" && pres(aire(rr), 5000 - (400 - 100 * Math.PI), 6), aire(rr));
  const ci = un('<circle cx="50" cy="60" r="20" stroke="blue" stroke-width="3" fill="none"/>');
  ok("cercle → ellipse, contour nommé", ci.type === "ellipse" && ci.cx === 50 && ci.cy === 60 && ci.rx === 20 && ci.ry === 20 && ci.style.contour === "#0000ff" && ci.style.epaisseur === 3 && ci.style.fond === "none", JSON.stringify(ci));
  const el = un('<ellipse cx="5" cy="6" rx="7" ry="8"/>');
  ok("ellipse ; fond noir par défaut", el.type === "ellipse" && el.rx === 7 && el.ry === 8 && el.style.fond === "#000000");
  ok("ligne → chemin ouvert (sans fond)", un('<line x1="0" y1="0" x2="10" y2="5" stroke="#000"/>').d === "M0 0 L10 5");
  ok("polyligne → chemin ouvert", un('<polyline points="0,0 10,0 10,10" fill="none" stroke="red"/>').d === "M0 0 L10 0 L10 10");
  ok("polygone → chemin fermé", un('<polygon points="0 0 10 0 10 10"/>').d === "M0 0 L10 0 L10 10 Z");
  const p = un('<path d="m0 0 h10 v10 z" fill="rgb(0, 128, 255)" opacity="0.5"/>');
  ok("chemin normalisé, rgb(), opacité", p.type === "path" && p.d === "M0 0 L10 0 L10 10 Z" && p.style.fond === "#0080ff" && p.style.opacite === 0.5, JSON.stringify(p));
  const t = un('<text x="10" y="30" font-family="Inter" font-size="24" fill="#123456">Bon<tspan font-weight="bold">jour</tspan></text>');
  ok("texte : position, contenu des tspan, police, corps, couleur", t.type === "texte" && t.x === 10 && t.y === 30 && t.contenu === "Bonjour" && t.style.police === "Inter" && t.style.corps === 24 && t.style.fond === "#123456", JSON.stringify(t));
  ok("ids provisoires uniques", (() => { const a = svg_vers_objets(svg('<rect width="1" height="1"/><rect width="2" height="2"/>')).objets; return a[0].id !== a[1].id; })());
}
/* ── styles ── */
{
  const r = svg_vers_objets(svg('<style>.rouge { fill: #e00; } rect { stroke: #0f0 } .epais{stroke-width:4}</style><g fill="#00f" stroke-width="2"><rect class="rouge epais" width="1" height="1"/><rect width="1" height="1" style="fill:#abc;opacity:.25"/><circle r="1"/></g>')).objets[0];
  const [a, b, c] = r.enfants;
  ok("classe > attribut hérité ; élément CSS ; plusieurs classes", a.style.fond === "#ee0000" && a.style.contour === "#00ff00" && a.style.epaisseur === 4, JSON.stringify(a.style));
  ok("une classe l'emporte sur une balise écrite après", un('<style>.a{fill:red} rect{fill:blue}</style><rect class="a" width="1" height="1"/>').style.fond === "#ff0000");
  ok("style=\"\" > CSS ; opacité", b.style.fond === "#aabbcc" && b.style.opacite === 0.25 && b.style.epaisseur === 2, JSON.stringify(b.style));
  ok("héritage du groupe (fill, stroke-width)", c.style.fond === "#0000ff" && c.style.epaisseur === 2, JSON.stringify(c.style));
  ok("fill-opacity se reporte sur l'opacité", un('<rect width="1" height="1" fill="red" fill-opacity="0.4"/>').style.opacite === 0.4);
  ok("fill-rule evenodd hérité → regle", un('<g fill-rule="evenodd"><path d="M0 0 L1 0 L1 1 Z"/></g>').enfants[0].style.regle === "evenodd" && !("regle" in un('<rect width="1" height="1"/>').style));
  ok("jointure : onglet par défaut (SVG), ronde si demandée, absente sans contour", un('<line x2="5" stroke="#000"/>').style.joint === "miter"
     && un('<line x2="5" stroke="#000" stroke-linejoin="round"/>').style.joint === "round" && !("joint" in un('<rect width="1" height="1"/>').style));
  ok("pointillés", un('<line x2="5" stroke="#000" stroke-dasharray="4,2"/>').style.pointilles === "4 2");
  ok("currentColor", un('<g color="#336699"><rect width="1" height="1" fill="currentColor"/></g>').enfants[0].style.fond === "#336699");
  ok("url(#dégradé) → couleur du premier arrêt", un('<defs><linearGradient id="g"><stop offset="0" stop-color="#ff8800"/><stop offset="1" stop-color="#000"/></linearGradient></defs><rect width="1" height="1" fill="url(#g)"/>').style.fond === "#ff8800");
  const cachee = svg_vers_objets(svg('<rect width="1" height="1" display="none"/><rect width="1" height="1" style="visibility:hidden"/><rect width="2" height="2"/>'));
  ok("display:none et visibility:hidden : ignorés et comptés", cachee.objets.length === 1 && cachee.stats.ignores.cache === 2, JSON.stringify(cachee.stats));
}
/* ── transforms, use, viewBox ── */
{
  const g = un('<g transform="translate(10 20)"><rect width="5" height="5" transform="rotate(45)"/></g>');
  ok("groupe : transform gardé, enfant aussi", g.type === "groupe" && g.transform === "translate(10 20)" && g.enfants[0].transform === "rotate(45)");
  const u = svg_vers_objets(svg('<defs><rect id="p" width="4" height="4" fill="#0a0"/></defs><use href="#p" x="10" y="5"/><use xlink:href="#p"/>')).objets;
  ok("use : la référence développée, x/y en translate", u.length === 2 && u[0].type === "groupe" && u[0].transform === "translate(10 5)" && u[0].enfants[0].type === "rect" && u[0].enfants[0].style.fond === "#00aa00", JSON.stringify(u[0]));
  ok("use xlink:href ; ids distincts des deux copies", u[1].enfants[0].type === "rect" && u[1].enfants[0].id !== u[0].enfants[0].id);
  ok("use vers un id absent : ignoré et compté", svg_vers_objets(svg('<use href="#nope"/>')).stats.ignores.use === 1);
  // viewBox 0 0 100 50 dans 400 × 200 : échelle 4, la page fait 400 × 200
  const vb = svg_vers_objets(svg('<rect width="10" height="10"/>', 'width="400" height="200" viewBox="0 0 100 50"'));
  ok("viewBox : taille de page et groupe mis à l'échelle", vb.taille.w === 400 && vb.taille.h === 200 && vb.objets.length === 1 && vb.objets[0].type === "groupe" && vb.objets[0].transform === "matrix(4 0 0 4 0 0)", JSON.stringify(vb.objets[0]));
  ok("viewBox seul : la page prend sa taille, sans échelle", (() => { const a = svg_vers_objets(svg('<rect width="1" height="1"/>', 'viewBox="10 20 300 150"')); return a.taille.w === 300 && a.taille.h === 150 && a.objets[0].transform === "matrix(1 0 0 1 -10 -20)"; })());
  ok("viewBox non proportionnel : « meet », centré", svg_vers_objets(svg('<rect width="1" height="1"/>', 'width="200" height="100" viewBox="0 0 100 100"')).objets[0].transform === "matrix(1 0 0 1 50 0)");
  ok("unités : mm et pt en px", (() => { const a = svg_vers_objets(svg("", 'width="25.4mm" height="72pt"')); return pres(a.taille.w, 96) && pres(a.taille.h, 96); })());
  ok("sans taille ni viewBox : 300 × 150 (défaut SVG)", (() => { const a = svg_vers_objets(svg("", "")); return a.taille.w === 300 && a.taille.h === 150; })());
  ok("hauteur seule + viewBox : largeur proportionnelle", svg_vers_objets(svg("", 'height="100" viewBox="0 0 200 50"')).taille.w === 400);
  ok("viewBox égal à la page : pas de groupe d'échelle", un('<rect width="1" height="1"/>', 'width="400" height="300" viewBox="0 0 400 300"').type === "rect");
}
/* ── ignorés, bilan, refus ── */
{
  const a = svg_vers_objets(svg('<image href="photo.png" width="10" height="10"/><foreignObject/><rect width="1" height="1" filter="url(#f)" clip-path="url(#c)"/><g></g>'));
  ok("image et foreignObject ignorés ; filtre et découpe comptés ; groupe vide écarté", a.objets.length === 1 && a.stats.ignores.image === 1 && a.stats.ignores.inconnu === 1
     && a.stats.ignores.filtre === 1 && a.stats.ignores.decoupe === 1, JSON.stringify(a));
  ok("bilan : objets importés comptés (feuilles)", svg_vers_objets(svg('<g><rect width="1" height="1"/><circle r="2"/></g><line x2="1" stroke="#000"/>')).stats.importes === 3);
  ok("pas de <svg> → refus traduit", refus(() => svg_vers_objets("<html></html>")) === T("vectorlab.importer.svg_invalide"));
  ok("vide → refus traduit", refus(() => svg_vers_objets("")) === T("vectorlab.importer.xml_invalide"));
}

if (echecs.length) {
  console.error(`importsvg : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("importsvg : ok");
