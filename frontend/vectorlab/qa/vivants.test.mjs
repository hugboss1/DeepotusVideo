// vivants.test.mjs — t123 : ce que les lots B et F laissaient « figé ».
//  1. les effets (ombre, flou…) s'appliquent aussi aux objets IMAGE ;
//  2. le texte sur chemin SUIT son chemin (le d n'est plus une copie morte) ;
//  3. le contour décalé est VIVANT : il se recalcule quand sa source change ;
//  4. un symbole s'édite EN PLACE (ouvrir → modifier → refermer), toutes ses instances suivent.
import { createRequire } from "node:module";
import { parserDoc, compilerSVG, op_style, op_deplacer, op_texte_sur_chemin, chemin_parser } from "../js/mod-doc.js";
import { effet_defaut } from "../js/mod-effets.js";
import { forme_d } from "../js/mod-formes.js";
import { fournirMartinez, op_contour, aire_de, aplatir_objet } from "../js/mod-bool.js";
const aire = (o) => Math.abs(aire_de(aplatir_objet(o)));
import { derives_rafraichir, op_derive_detacher } from "../js/mod-vivants.js";
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

if (echecs.length) {
  console.error("ECHECS vivants :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log(`QA vivants : PASS (${nControles} controles)`);
