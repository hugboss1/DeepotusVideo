// symboles.test.mjs — lot F : styles d'objet réutilisables (copie à
// l'application) et symboles VIVANTS (doc.symboles + objet instance → <use>).
import { parserDoc, compilerSVG, op_style_definir, op_style_appliquer, op_style_supprimer,
         op_symbole_creer, op_instance_poser, op_symbole_detacher, op_symbole_supprimer, op_symbole_modifier,
         op_deplacer, op_redimensionner, op_supprimer, bbox_objet } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
const compte = (s, re) => (s.match(re) || []).length;
const essaie = (fn) => { try { fn(); return true; } catch { return false; } };
const base = () => ({
  v: 1, nom: "S", taille: { w: 300, h: 200 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
    { id: "r1", type: "rect", x: 10, y: 10, w: 40, h: 20, style: { fond: "#FF0000", contour: "#000000", epaisseur: 2 } },
    { id: "e1", type: "ellipse", cx: 30, cy: 50, rx: 20, ry: 10, style: { fond: "#00FF00" } },
    { id: "p1", type: "path", d: "M 100 100 L 140 100 L 120 140 Z", style: { fond: "#0000FF" } },
  ] }],
});

/* ── styles d'objet ── */
{
  const d = base();
  op_style_definir(d, "rouge-cerne", { fond: "#FF0000", contour: "#000000", epaisseur: 2, effets: [{ type: "ombre" }] });
  ok("définir : stocké sous son nom, copie profonde", d.styles["rouge-cerne"].effets[0].type === "ombre");
  op_style_appliquer(d, ["p1"], "rouge-cerne");
  ok("appliquer : le style est COPIÉ sur l'objet (fond, contour, effets)", d.calques[0].objets[2].style.fond === "#FF0000" && d.calques[0].objets[2].style.effets.length === 1 && d.calques[0].objets[2].style !== d.styles["rouge-cerne"]);
  d.styles["rouge-cerne"].fond = "#123456";
  ok("pas de lien vivant : changer le style stocké ne touche pas l'objet", d.calques[0].objets[2].style.fond === "#FF0000");
  op_style_supprimer(d, "rouge-cerne");
  ok("supprimer : le champ vide disparaît, l'objet garde son apparence", d.styles === undefined && d.calques[0].objets[2].style.fond === "#FF0000");
  let refus = 0;
  try { op_style_definir(d, "", {}); } catch { refus++; }
  try { op_style_definir(d, "x", { fusion: "zz" }); } catch { refus++; }
  try { op_style_appliquer(d, ["p1"], "absent"); } catch { refus++; }
  try { op_style_supprimer(d, "absent"); } catch { refus++; }
  ok("nom vide, style invalide, style absent (appliquer, supprimer) refusés", refus === 4, String(refus));
  ok("parserDoc refuse doc.styles malformé", !essaie(() => { const x = base(); x.styles = { a: { effets: "x" } }; parserDoc(x); }));
}
/* ── symboles ── */
{
  const d = base();
  const sid = op_symbole_creer(d, ["r1", "e1"], "pion");
  const sym = d.symboles[sid];
  ok("créer : le symbole porte les deux objets (retirés du calque), sa bbox, son nom", sid === "s1" && sym.nom === "pion" && sym.objets.length === 2 && JSON.stringify(sym.bbox) === JSON.stringify({ x: 10, y: 10, w: 40, h: 50 }), JSON.stringify(sym));
  const inst = d.calques[0].objets.find((o) => o.type === "instance");
  ok("créer pose une instance à la place, à l'origine (x 0, y 0, sx 1, sy 1), les originaux ne sont plus dans le calque", inst && inst.symbole === sid && inst.x === 0 && inst.y === 0 && inst.sx === 1 && inst.sy === 1 && d.calques[0].objets.length === 2, JSON.stringify(d.calques[0].objets));
  const svg = compilerSVG(d);
  ok("compilé : <g id=sym_s1> dans les defs avec les objets SANS id, l'instance est un <use href=#sym_s1 data-objet>", svg.includes('<g id="sym_s1">') && compte(svg, /data-objet="r1"/g) === 0 && svg.includes('<use data-objet="' + inst.id + '"') && svg.includes('href="#sym_s1"'), svg);
  const i2 = op_instance_poser(d, "c1", sid, 100, 20);
  ok("poser une seconde instance : translate(100 20)", compilerSVG(d).includes(`data-objet="${i2}"`) && compilerSVG(d).includes('transform="translate(100 20)') , compilerSVG(d));
  ok("bbox d'une instance : bbox du symbole translatée et mise à l'échelle", JSON.stringify(bbox_objet(d.calques[0].objets.find((o) => o.id === i2), d)) === JSON.stringify({ x: 110, y: 30, w: 40, h: 50 }));
  op_deplacer(d, [i2], 5, 5);
  op_redimensionner(d, [i2], { x: 115, y: 35, w: 40, h: 50 }, { x: 115, y: 35, w: 80, h: 50 });
  const o2 = d.calques[0].objets.find((o) => o.id === i2);
  ok("déplacer et redimensionner une instance : x, y, sx — l'origine recule de bx·sx pour que la bbox reste à 115", o2.x === 95 && o2.y === 25 && Math.abs(o2.sx - 2) < 1e-9 && o2.sy === 1 && JSON.stringify(bbox_objet(o2, d)) === JSON.stringify({ x: 115, y: 35, w: 80, h: 50 }), JSON.stringify(o2));
  ok("le <use> porte translate puis scale", compilerSVG(d).includes(`transform="translate(95 25) scale(2 1)"`), compilerSVG(d));
  op_symbole_modifier(d, sid, (objets) => { objets[0].style.fond = "#ABCDEF"; });
  ok("modifier le symbole change toutes les instances (VIVANT) : une seule définition, deux <use>", compte(compilerSVG(d), /#ABCDEF/g) === 1 && compte(compilerSVG(d), /<use /g) === 2);
  ok("supprimer un symbole encore instancié : refusé", !essaie(() => op_symbole_supprimer(d, sid)));
  const ids = op_symbole_detacher(d, i2);
  ok("détacher : les objets copiés (ids neufs) à la place de l'instance, translatés et mis à l'échelle", ids.length === 2 && !ids.includes("r1") && d.calques[0].objets.some((o) => o.id === ids[0] && o.type === "rect" && o.x === 115 + (10 - 10) * 2 && o.w === 80) && !d.calques[0].objets.some((o) => o.type === "instance" && o.id === i2), JSON.stringify(d.calques[0].objets));   // l'id libéré peut être réattribué à une copie
  op_supprimer(d, [inst.id]);
  op_symbole_supprimer(d, sid);
  ok("plus d'instance : le symbole se supprime, le champ vide disparaît", d.symboles === undefined);
  let refus = 0;
  try { op_symbole_creer(d, [], "vide"); } catch { refus++; }
  try { op_instance_poser(d, "c1", "s9", 0, 0); } catch { refus++; }
  try { op_symbole_detacher(d, "p1"); } catch { refus++; }
  ok("créer sans objet, poser un symbole inconnu, détacher un non-instance refusés", refus === 3, String(refus));
  ok("parserDoc refuse une instance dont le symbole manque", !essaie(() => { const x = base(); x.calques[0].objets.push({ id: "i9", type: "instance", symbole: "s9", x: 0, y: 0, sx: 1, sy: 1 }); parserDoc(x); }));
  ok("parserDoc accepte un symbole + instance bien formés", essaie(() => { const x = base(); x.symboles = { s1: { nom: "a", bbox: { x: 0, y: 0, w: 1, h: 1 }, objets: [{ id: "q", type: "rect", x: 0, y: 0, w: 1, h: 1, style: {} }] } }; x.calques[0].objets.push({ id: "i9", type: "instance", symbole: "s1", x: 0, y: 0, sx: 1, sy: 1 }); parserDoc(x); }));
}
if (echecs.length) {
  console.error("ECHECS symboles :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA symboles : PASS (21 controles)");
