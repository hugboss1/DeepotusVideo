// vivants.test.mjs — t123 : ce que les lots B et F laissaient « figé ».
//  1. les effets (ombre, flou…) s'appliquent aussi aux objets IMAGE ;
//  2. le texte sur chemin SUIT son chemin (le d n'est plus une copie morte) ;
//  3. le contour décalé est VIVANT : il se recalcule quand sa source change ;
//  4. un symbole s'édite EN PLACE (ouvrir → modifier → refermer), toutes ses instances suivent.
import { createRequire } from "node:module";
import { parserDoc, compilerSVG, op_style, op_deplacer, op_texte_sur_chemin, chemin_parser,
         op_symbole_ouvrir, op_symbole_fermer, op_symbole_abandonner } from "../js/mod-doc.js";
import { effet_defaut } from "../js/mod-effets.js";
import { forme_d } from "../js/mod-formes.js";
import { fournirMartinez, op_contour, aire_de, aplatir_objet } from "../js/mod-bool.js";
const aire = (o) => Math.abs(aire_de(aplatir_objet(o)));
import { derives_rafraichir, op_derive_detacher } from "../js/mod-vivants.js";
import { pdf_page } from "../js/mod-pdf.js";
fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));

const echecs = [];
let nControles = 0;
const ok = (nom, cond, detail = "") => {
  nControles++;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 240) : ""));
};
const base = (objets = []) => ({ v: 1, nom: "V", taille: { w: 400, h: 300 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets }] });

/* ── 1. effets sur une image ── */
{
  const img = () => ({ id: "im", type: "image", href: "a.png", x: 10, y: 10, w: 100, h: 50, nat: { w: 200, h: 100 } });
  const d = base([img()]);
  op_style(d, ["im"], { effets: [effet_defaut("ombre")] });
  const svg = compilerSVG(d);
  ok("image + effet : filtre posé sur le groupe de l'image", /<g data-objet="im"[^>]*filter="url\(#fx_im\)"/.test(svg), svg.slice(0, 600));
  ok("image + effet : le <filter id=fx_im> est dans les defs", svg.includes('<filter id="fx_im"'), svg.slice(0, 400));
  ok("image + effet : l'image est toujours là", (svg.match(/<image /g) || []).length === 1);
  const sans = compilerSVG(base([img()]));
  ok("image sans effet : aucun filtre (le SVG d'avant)", !/filter=/.test(sans) && !sans.includes("<filter"));
  const f = base([img()]);
  op_style(f, ["im"], { fusion: "multiply" });
  ok("image + fusion : mix-blend-mode sur le groupe", /<g data-objet="im"[^>]*mix-blend-mode:multiply/.test(compilerSVG(f)), compilerSVG(f).slice(0, 400));
}

/* ── 2. le texte sur chemin SUIT son chemin ── */
{
  const d = base([{ id: "p", type: "path", d: "M 0 100 C 50 0 150 0 200 100", style: { contour: "#000000" } },
                  { id: "t", type: "texte", x: 0, y: 0, contenu: "Bonjour", style: { fond: "#000000", corps: 20 } }]);
  op_texte_sur_chemin(d, "t", "p");
  const t = () => d.calques[0].objets.find((o) => o.id === "t");
  ok("op_texte_sur_chemin garde le LIEN (id du chemin) et l'empreinte de sa géométrie", t().chemin === "p" && typeof t().empreinte === "string" && t().d === "M 0 100 C 50 0 150 0 200 100", JSON.stringify(t()));
  ok("rien n'a changé : rafraîchir ne touche à rien", derives_rafraichir(d) === 0);
  op_deplacer(d, ["p"], 10, 20);
  const dp = d.calques[0].objets[0].d;
  ok("le chemin bouge → le texte suit (même d)", derives_rafraichir(d) === 1 && t().d === dp, `${t().d} / ${dp}`);
  ok("… et une seconde passe ne refait rien", derives_rafraichir(d) === 0);
  // une source FORME : le texte suit son d recalculé
  const f = base([{ id: "f", type: "forme", forme: "polygone", cx: 100, cy: 100, r: 40, params: { n: 5 }, style: { contour: "#000000" } },
                  { id: "t", type: "texte", x: 0, y: 0, contenu: "x", style: {} }]);
  op_texte_sur_chemin(f, "t", "f");
  f.calques[0].objets[0].r = 60;
  derives_rafraichir(f);
  ok("source forme : le texte suit son nouveau rayon", f.calques[0].objets[1].d === forme_d(f.calques[0].objets[0]));
  // une source TOURNÉE : le texte prend le même transform (sinon il ne serait pas SUR le chemin)
  f.calques[0].objets[0].transform = "rotate(30 100 100)";
  derives_rafraichir(f);
  ok("source tournée : le texte reçoit le même transform", f.calques[0].objets[1].transform === "rotate(30 100 100)");
  delete f.calques[0].objets[0].transform;
  derives_rafraichir(f);
  ok("… et le perd avec elle", f.calques[0].objets[1].transform === undefined);
  // la source supprimée : le texte garde son dernier tracé, rien ne lève
  const dAvant = f.calques[0].objets[1].d;
  f.calques[0].objets.splice(0, 1);
  let leve = false; try { derives_rafraichir(f); } catch { leve = true; }
  ok("source supprimée : le texte garde son tracé, rien ne lève", !leve && f.calques[0].objets[0].d === dAvant);
  // la source DANS un groupe est trouvée
  const g = base([{ id: "g", type: "groupe", style: {}, enfants: [{ id: "p", type: "path", d: "M 0 0 L 100 0", style: {} }] },
                  { id: "t", type: "texte", x: 0, y: 0, contenu: "x", style: {} }]);
  op_texte_sur_chemin(g, "t", "p");
  g.calques[0].objets[0].enfants[0].d = "M 0 0 L 200 0";
  ok("source dans un groupe : suivie", derives_rafraichir(g) === 1 && g.calques[0].objets[1].d === "M 0 0 L 200 0");
  // posé sur un chemin DÉJÀ tourné : le texte prend son transform dès la pose
  const tr = base([{ id: "p", type: "path", d: "M 0 0 L 100 0", transform: "rotate(20 50 0)", style: {} },
                   { id: "t", type: "texte", x: 0, y: 0, contenu: "x", style: {} }]);
  op_texte_sur_chemin(tr, "t", "p");
  ok("posé sur un chemin tourné : même transform dès la pose", tr.calques[0].objets[1].transform === "rotate(20 50 0)");
  // l'id du chemin désigne désormais autre chose (un rect) : le texte n'y lit rien
  const autre = base([{ id: "p", type: "path", d: "M 0 0 L 100 0", style: {} }, { id: "t", type: "texte", x: 0, y: 0, contenu: "x", style: {} }]);
  op_texte_sur_chemin(autre, "t", "p");
  autre.calques[0].objets[0] = { id: "p", type: "rect", x: 0, y: 0, w: 10, h: 10, style: {} };
  ok("la source n'est plus un chemin : le texte garde son tracé", derives_rafraichir(autre) === 0 && autre.calques[0].objets[1].d === "M 0 0 L 100 0");
  ok("le document lié reste valide", (() => { try { parserDoc(d); return true; } catch (e) { return e.message; } })() === true);
}
/* ── 3. le contour décalé est VIVANT ── */
{
  const d = base([{ id: "r", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "#FF0000" } }]);
  const [id] = op_contour(d, ["r"], 5);
  const c = () => d.calques[0].objets.find((o) => o.id === id);
  ok("op_contour : le contour garde sa source, son décalage et l'empreinte", c().derive && c().derive.source === "r" && c().derive.decalage === 5 && typeof c().derive.empreinte === "string", JSON.stringify(c().derive));
  const aire0 = aire(c());
  ok("contour + 5 d'un carré de 100 : aire ≈ 110² − 4·(5² − π·5²/4)", Math.abs(aire0 - (110 * 110 - 4 * (25 - Math.PI * 25 / 4))) < 15, String(aire0));
  ok("rien n'a changé : rafraîchir ne touche à rien", derives_rafraichir(d) === 0);
  // la source grandit : le contour se recalcule
  d.calques[0].objets[0].w = 200;
  ok("la source s'élargit → le contour se recalcule", derives_rafraichir(d) === 1 && aire(c()) > aire0 + 100 * 100, `${aire(c())} vs ${aire0}`);
  ok("… et une seconde passe ne recalcule rien (l'empreinte est à jour)", derives_rafraichir(d) === 0);
  // la source se déplace : le contour suit
  op_deplacer(d, ["r"], 50, 0);
  derives_rafraichir(d);
  const xs = chemin_parser(c().d).flatMap((s) => s.p.filter((_, k) => k % 2 === 0));
  ok("la source se déplace → le contour suit (x min ≈ 45)", Math.abs(Math.min(...xs) - 45) < 0.5, String(Math.min(...xs)));
  // un retrait qui viderait la forme : le contour garde son dernier tracé (pas d'exception au rendu)
  const e = base([{ id: "r", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "#FF0000" } }]);
  const [ide] = op_contour(e, ["r"], -5);
  const avant = e.calques[0].objets.find((o) => o.id === ide).d;
  e.calques[0].objets[0].w = 6; e.calques[0].objets[0].h = 6;
  let leve = false; try { derives_rafraichir(e); } catch { leve = true; }
  ok("retrait qui viderait la forme : le dernier tracé reste, rien ne lève", !leve && e.calques[0].objets.find((o) => o.id === ide).d === avant);
  // détacher : le contour redevient un chemin ordinaire
  op_derive_detacher(d, id);
  d.calques[0].objets[0].w = 300;
  ok("op_derive_detacher : plus de lien, le contour ne suit plus", c().derive === undefined && derives_rafraichir(d) === 0);
  ok("le document lié reste valide", (() => { try { parserDoc(e); return true; } catch (x) { return x.message; } })() === true);
}

/* ── 4. un symbole s'édite EN PLACE ── */
{
  const avecSymbole = () => {
    const d = base([{ id: "i1", type: "instance", symbole: "s1", x: 100, y: 50, sx: 2, sy: 2, style: {} },
                    { id: "i2", type: "instance", symbole: "s1", x: 0, y: 0, sx: 1, sy: 1, style: {} }]);
    d.symboles = { s1: { nom: "Pion", bbox: { x: 0, y: 0, w: 10, h: 10 }, objets: [{ id: "a", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#FF0000" } }] } };
    return d;
  };
  const d = avecSymbole();
  const cid = op_symbole_ouvrir(d, "i1");
  const cal = d.calques.find((c) => c.id === cid);
  ok("ouvrir : un calque d'édition juste après celui de l'instance", d.calques.indexOf(cal) === 1 && /Pion/.test(cal.nom), JSON.stringify(d.calques.map((c) => c.id)));
  ok("ouvrir : les objets À LA PLACE et à l'échelle de l'instance (x 100, y 50, 20 x 20)", cal.objets.length === 1 && cal.objets[0].x === 100 && cal.objets[0].y === 50 && cal.objets[0].w === 20 && cal.objets[0].h === 20, JSON.stringify(cal.objets));
  ok("ouvrir : des ids neufs (le symbole garde les siens)", cal.objets[0].id !== "a" && d.symboles.s1.objets[0].id === "a");
  ok("ouvrir : l'état d'édition est noté", d.edition && d.edition.sid === "s1" && d.edition.instance === "i1" && d.edition.calque === cid, JSON.stringify(d.edition));
  const svg = compilerSVG(d);
  ok("pendant l'édition : l'instance éditée est masquée, l'autre reste", !/<use data-objet="i1"/.test(svg) && /<use data-objet="i2"/.test(svg), svg.slice(0, 500));
  const pp = pdf_page(d, { x: 0, y: 0, w: 400, h: 300 }, { dpi: 72 });
  ok("pendant l'édition : le PDF ne dessine pas l'instance éditée en double (calque d'édition + i2 seulement)", (pp.contenu.match(/1 0 0 rg/g) || []).length === 2, pp.contenu);
  ok("pendant l'édition : le document reste valide", (() => { try { parserDoc(d); return true; } catch (x) { return x.message; } })() === true);
  let refus = 0; try { op_symbole_ouvrir(d, "i2"); } catch (e) { if (/déjà/.test(e.message)) refus++; }
  ok("une seule édition à la fois", refus === 1);
  // on modifie EN PLACE : le rect s'élargit (40 de large à l'échelle 2 = 20 dans le symbole), une ellipse s'ajoute
  cal.objets[0].w = 40;
  cal.objets.push({ id: "e9", type: "ellipse", cx: 140, cy: 60, rx: 10, ry: 10, style: { fond: "#0000FF" } });
  op_symbole_fermer(d);
  const sym = d.symboles.s1;
  ok("terminer : le calque d'édition disparaît, l'état aussi", !d.calques.some((c) => c.id === cid) && d.edition === undefined);
  ok("terminer : le rect revient dans l'espace du symbole (w 20)", sym.objets.length === 2 && sym.objets[0].x === 0 && sym.objets[0].w === 20 && sym.objets[0].h === 10, JSON.stringify(sym.objets[0]));
  ok("terminer : l'ellipse aussi (cx 20, cy 5, r 5)", sym.objets[1].type === "ellipse" && sym.objets[1].cx === 20 && sym.objets[1].cy === 5 && sym.objets[1].rx === 5, JSON.stringify(sym.objets[1]));
  ok("terminer : la boîte du symbole suit son nouveau contenu", sym.bbox.x === 0 && sym.bbox.y === 0 && sym.bbox.w === 25 && sym.bbox.h === 10, JSON.stringify(sym.bbox));
  ok("terminer : les instances n'ont pas bougé (elles suivent le symbole)", d.calques[0].objets[0].x === 100 && d.calques[0].objets[0].sx === 2);
  const svg2 = compilerSVG(d);
  ok("terminer : les deux instances montrent le nouveau contenu", /<use data-objet="i1"/.test(svg2) && /<use data-objet="i2"/.test(svg2) && /<g id="sym_s1">[\s\S]*<ellipse/.test(svg2), svg2.slice(0, 600));
  // abandonner : rien ne change
  const a = avecSymbole();
  const avant = JSON.stringify(a.symboles);
  const ca = op_symbole_ouvrir(a, "i2");
  a.calques.find((c) => c.id === ca).objets[0].w = 99;
  op_symbole_abandonner(a);
  ok("abandonner : le symbole est intact, le calque et l'état disparaissent", JSON.stringify(a.symboles) === avant && a.calques.length === 1 && a.edition === undefined);
  // refus dits
  let r2 = 0;
  try { op_symbole_fermer(avecSymbole()); } catch (e) { if (/aucune/.test(e.message)) r2++; }
  try { op_symbole_abandonner(avecSymbole()); } catch (e) { if (/aucune/.test(e.message)) r2++; }
  const v = avecSymbole(); const cv = op_symbole_ouvrir(v, "i1"); v.calques.find((c) => c.id === cv).objets = [];
  try { op_symbole_fermer(v); } catch (e) { if (/vide/.test(e.message)) r2++; }
  try { op_symbole_ouvrir(avecSymbole(), "zz"); } catch (e) { if (/instance/.test(e.message)) r2++; }
  ok("refus dits : rien à fermer, rien à abandonner, symbole vide, instance introuvable", r2 === 4, String(r2));
  // plusieurs calques : le calque d'édition s'insère JUSTE APRÈS celui de l'instance, pas en dernier
  const m = avecSymbole();
  m.calques.push({ id: "c2", nom: "dessus", visible: true, verrou: false, objets: [] });
  const cm = op_symbole_ouvrir(m, "i1");
  ok("calque d'édition juste après celui de l'instance (avant c2)", JSON.stringify(m.calques.map((c) => c.id)) === JSON.stringify(["c1", cm, "c2"]), JSON.stringify(m.calques.map((c) => c.id)));
  // un symbole dont la boîte NE PART PAS de l'origine : la copie tombe sur l'instance (x + sx · bbox.x)
  const o5 = base([{ id: "i1", type: "instance", symbole: "s1", x: 100, y: 50, sx: 2, sy: 2, style: {} }]);
  o5.symboles = { s1: { nom: "Décalé", bbox: { x: 5, y: 5, w: 10, h: 10 }, objets: [{ id: "a", type: "rect", x: 5, y: 5, w: 10, h: 10, style: { fond: "#FF0000" } }] } };
  const c5 = op_symbole_ouvrir(o5, "i1");
  const r5 = o5.calques.find((c) => c.id === c5).objets[0];
  ok("boîte hors origine : la copie est là où l'instance la dessine (110, 60, 20 x 20)", r5.x === 110 && r5.y === 60 && r5.w === 20, JSON.stringify(r5));
  op_symbole_fermer(o5);
  ok("… et revient intacte dans le symbole", JSON.stringify(o5.symboles.s1.objets[0]) === JSON.stringify({ id: o5.symboles.s1.objets[0].id, type: "rect", x: 5, y: 5, w: 10, h: 10, style: { fond: "#FF0000" } }) && JSON.stringify(o5.symboles.s1.bbox) === JSON.stringify({ x: 5, y: 5, w: 10, h: 10 }), JSON.stringify(o5.symboles.s1));
}

if (echecs.length) {
  console.error("ECHECS vivants :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log(`QA vivants : PASS (${nControles} controles)`);
