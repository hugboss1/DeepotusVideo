// apparence2.test.mjs — lot F côté modèle : style.effets / fusion /
// contours / masque (validation + compilation), doc.motifs (fond
// « motif:<id> »), dégradé conique, dégradé de transparence (masque),
// couleurs globales (« glob:<nom> » résolu à la compilation, suppression
// qui résout), écrêtage vectoriel (groupe.clip → <clipPath>).
import { parserDoc, compilerSVG, op_style, op_motif_creer, op_motif_modifier, op_motif_supprimer,
         op_degrade_creer, op_degrade_transparence, op_couleur_globale_definir, op_couleur_globale_supprimer,
         op_ecreter, op_desecreter, op_deplacer } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
const compte = (s, re) => (s.match(re) || []).length;
const base = () => ({
  v: 1, nom: "F", taille: { w: 200, h: 100 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
    { id: "r1", type: "rect", x: 10, y: 10, w: 80, h: 40, style: { fond: "#FF0000" } },
    { id: "e1", type: "ellipse", cx: 150, cy: 50, rx: 30, ry: 20, style: { fond: "#00FF00" } },
  ] }],
});
const essaie = (fn) => { try { fn(); return true; } catch { return false; } };

/* ── effets, fusion, contours, masque : validation ── */
{
  let refus = 0;
  for (const mauvais of [{ effets: "x" }, { effets: [{ type: "zz" }] }, { fusion: "plus" }, { contours: {} }, { contours: [{ epaisseur: 0 }] },
                         { contours: [{ couleur: "bleu", epaisseur: 2 }] }, { masque: 3 }, { masque: "grad:absent" }]) {
    const d = base(); d.calques[0].objets[0].style = { ...d.calques[0].objets[0].style, ...mauvais };
    if (!essaie(() => parserDoc(d))) refus++;
  }
  ok("parserDoc refuse 8 styles avancés malformés", refus === 8, String(refus));
  const d = base();
  d.degrades = { g1: { type: "lineaire", x1: 0, y1: 0, x2: 1, y2: 0, stops: [{ t: 0, couleur: "#FFFFFF" }, { t: 1, couleur: "#000000" }] } };
  d.calques[0].objets[0].style = { fond: "#FF0000", effets: [{ type: "ombre" }], fusion: "multiply", contours: [{ couleur: "#0000FF", epaisseur: 6 }], masque: "grad:g1" };
  ok("parserDoc accepte un style avancé complet", essaie(() => parserDoc(d)));
  ok("état vide : sans style avancé, la compilation d'un rect est INCHANGÉE", compilerSVG(base()).includes('<rect data-objet="r1" x="10" y="10" width="80" height="40" fill="#FF0000"/>'), compilerSVG(base()));
}
/* ── compilation ── */
{
  const d = base();
  op_style(d, ["r1"], { effets: [{ type: "ombre", dx: 5, dy: 5 }, { type: "lueur" }] });
  const svg = compilerSVG(d);
  ok("effets : un <filter id=fx_r1> dans les defs, filter=url(#fx_r1) sur l'objet, l'id reste unique", svg.includes('<filter id="fx_r1"') && svg.includes('filter="url(#fx_r1)"') && compte(svg, /data-objet="r1"/g) === 1, svg);
  op_style(d, ["r1"], { effets: null, fusion: "screen" });
  ok("fusion : style mix-blend-mode", compilerSVG(d).includes('style="mix-blend-mode:screen"'));
  op_style(d, ["r1"], { fusion: "normal" });
  ok("fusion normal : rien d'émis", !compilerSVG(d).includes("mix-blend-mode"));
  op_style(d, ["r1"], { fusion: null, contours: [{ couleur: "#0000FF", epaisseur: 10 }, { couleur: "#FFFF00", epaisseur: 4 }] });
  const s2 = compilerSVG(d);
  ok("multi-contours : un <g data-objet> qui enveloppe deux copies sans id (fill none, du plus large au plus fin) puis l'objet", s2.includes('<g data-objet="r1">') && compte(s2, /data-objet="r1"/g) === 1 && compte(s2, /<rect /g) === 3
     && s2.indexOf('stroke-width="10"') < s2.indexOf('stroke-width="4"') && s2.indexOf('stroke-width="4"') < s2.indexOf('fill="#FF0000"') && compte(s2, /data-contour=/g) === 2, s2);
  ok("état vide : contours [] → compilation nue", (() => { op_style(d, ["r1"], { contours: [] }); return compilerSVG(d).includes('<rect data-objet="r1" x="10"'); })());
}
/* ── motifs ── */
{
  const d = base();
  const id = op_motif_creer(d, { type: "hachures", pas: 6 });
  ok("op_motif_creer → m1, stocké", id === "m1" && d.motifs.m1.pas === 6 && d.motifs.m1.type === "hachures");
  op_style(d, ["r1"], { fond: "motif:m1" });
  const svg = compilerSVG(d);
  ok("fond motif : <pattern id=m1> dans les defs, fill=url(#m1)", svg.includes('<pattern id="m1"') && svg.includes('fill="url(#m1)"'), svg);
  op_motif_modifier(d, "m1", { angle: 90, couleur: "#123456" });
  ok("op_motif_modifier", d.motifs.m1.angle === 90 && compilerSVG(d).includes("rotate(90)"));
  ok("motif inconnu : fond none (jamais un document cassé)", (() => { op_style(d, ["e1"], { fond: "motif:zz" }); return compilerSVG(d).includes('data-objet="e1"') && compilerSVG(d).match(/data-objet="e1"[^>]*fill="none"/); })());
  ok("op_motif_supprimer résout les fonds qui le référencent en none", (() => { op_motif_supprimer(d, "m1"); return !d.motifs.m1 && d.calques[0].objets[0].style.fond === "none"; })());
  let refus = 0; try { op_motif_creer(d, { type: "zz" }); } catch { refus++; }
  try { op_motif_modifier(d, "m9", {}); } catch { refus++; }
  ok("motif invalide ou inconnu refusé", refus === 2);
  ok("parserDoc refuse doc.motifs malformé", !essaie(() => { const x = base(); x.motifs = { a: { type: "zz" } }; parserDoc(x); }));
}
/* ── conique et transparence ── */
{
  const d = base();
  const g = op_degrade_creer(d, { type: "conique", cx: 50, cy: 30, r: 40, angle: 0, stops: [{ t: 0, couleur: "#FF0000" }, { t: 1, couleur: "#0000FF" }] });
  op_style(d, ["r1"], { fond: `grad:${g}` });
  const svg = compilerSVG(d);
  ok("conique : compilé en <pattern id=g1> de 72 secteurs, référencé par fill", svg.includes(`<pattern id="${g}"`) && compte(svg, /<path d="M 50 30/g) === 72 && svg.includes(`fill="url(#${g})"`), svg.slice(0, 200));
  op_deplacer(d, ["r1"], 10, 5);
  ok("le conique suit la forme (cx, cy)", d.degrades[g].cx === 60 && d.degrades[g].cy === 35);
  const m = op_degrade_transparence(d, ["e1"], { x: 120, y: 30, w: 60, h: 40 });
  const s2 = compilerSVG(d);
  ok("transparence : dégradé blanc→noir sur la bbox, style.masque = grad:<id>, <mask id=m_<id>> + mask=url", d.degrades[m].stops[0].couleur === "#FFFFFF" && d.degrades[m].x1 === 120 && d.calques[0].objets[1].style.masque === `grad:${m}`
     && s2.includes(`<mask id="m_${m}">`) && s2.includes(`mask="url(#m_${m})"`) && s2.includes(`fill="url(#${m})"`), s2);
  ok("le masque suit la forme aussi", (() => { op_deplacer(d, ["e1"], 10, 0); return d.degrades[m].x1 === 130; })());
  let refus = 0; try { op_degrade_creer(d, { type: "conique", cx: 0, cy: 0, r: 0 }); } catch { refus++; }
  ok("conique à rayon nul refusé", refus === 1);
}
/* ── couleurs globales ── */
{
  const d = base();
  op_couleur_globale_definir(d, "marque", "#12ab34");
  ok("définir : stockée en majuscules", d.couleursGlobales.marque === "#12AB34");
  op_style(d, ["r1"], { fond: "glob:marque", contour: "glob:marque", epaisseur: 2 });
  d.degrades = { g1: { type: "lineaire", x1: 0, y1: 0, x2: 1, y2: 0, stops: [{ t: 0, couleur: "glob:marque" }, { t: 1, couleur: "#000000" }] } };
  op_style(d, ["e1"], { fond: "grad:g1", contours: [{ couleur: "glob:marque", epaisseur: 3 }] });
  const svg = compilerSVG(d);
  ok("compilation : fond, contour, stop et multi-contour résolus en hex", svg.includes('fill="#12AB34"') && svg.includes('stroke="#12AB34"') && svg.includes('stop-color="#12AB34"') && compte(svg, /#12AB34/g) >= 4 && !svg.includes("glob:"), svg);
  op_couleur_globale_definir(d, "marque", "#FF00FF");
  ok("changer la teinte change tout", compte(compilerSVG(d), /#FF00FF/g) >= 4 && !compilerSVG(d).includes("#12AB34"));
  let refus = 0;
  for (const [n, h] of [["", "#FFFFFF"], ["a b", "#FFFFFF"], ["x", "rouge"]]) { try { op_couleur_globale_definir(d, n, h); } catch { refus++; } }
  ok("nom vide, nom avec espace, hex invalide refusés", refus === 3);
  ok("référence inconnue : repli none à la compilation, doc accepté", (() => { op_style(d, ["r1"], { fond: "glob:absente" }); return compilerSVG(d).match(/data-objet="r1"[^>]*fill="none"/) !== null; })());
  op_style(d, ["r1"], { fond: "glob:marque" });
  op_couleur_globale_supprimer(d, "marque");
  ok("supprimer RÉSOUT les références en hex (fond, contour, stop, contours)", !(d.couleursGlobales && d.couleursGlobales.marque) && d.calques[0].objets[0].style.fond === "#FF00FF" && d.calques[0].objets[0].style.contour === "#FF00FF"
     && d.degrades.g1.stops[0].couleur === "#FF00FF" && d.calques[0].objets[1].style.contours[0].couleur === "#FF00FF", JSON.stringify(d.calques[0].objets[0].style));
  ok("état vide : supprimer une couleur inconnue refusé", !essaie(() => op_couleur_globale_supprimer(d, "zz")));
  ok("parserDoc refuse couleursGlobales malformé", !essaie(() => { const x = base(); x.couleursGlobales = { a: "rouge" }; parserDoc(x); }));
}
/* ── écrêtage ── */
{
  const d = base();
  const gid = op_ecreter(d, "r1", ["e1"]);
  const g = d.calques[0].objets.find((o) => o.id === gid);
  ok("op_ecreter : un groupe {clip: r1} qui contient r1 puis e1, l'objet-conteneur en premier", g && g.type === "groupe" && g.clip === "r1" && g.enfants.map((o) => o.id).join(",") === "r1,e1" && d.calques[0].objets.length === 1, JSON.stringify(d.calques[0].objets));
  const svg = compilerSVG(d);
  ok("compilé : <clipPath id=clip_<g>> avec la géométrie du conteneur SANS id, le groupe porte clip-path, e1 dedans, r1 dessiné aussi",
     svg.includes(`<clipPath id="clip_${gid}">`) && svg.includes(`clip-path="url(#clip_${gid})"`) && compte(svg, /data-objet="r1"/g) === 1 && compte(svg, /<rect /g) === 2 && svg.includes('data-objet="e1"'), svg);
  const ids = op_desecreter(d, gid);
  ok("op_desecreter rend les objets au calque", ids.join(",") === "r1,e1" && d.calques[0].objets.length === 2 && !d.calques[0].objets.some((o) => o.type === "groupe"));
  let refus = 0; try { op_ecreter(d, "zz", ["e1"]); } catch { refus++; }
  try { op_ecreter(d, "r1", []); } catch { refus++; }
  try { op_desecreter(d, "r1"); } catch { refus++; }
  ok("conteneur inconnu, contenu vide, désécrêter un non-groupe refusés", refus === 3, String(refus));
  ok("parserDoc refuse un clip qui ne désigne pas un enfant", !essaie(() => { const x = base(); x.calques[0].objets = [{ id: "g", type: "groupe", clip: "zz", style: {}, enfants: [x.calques[0].objets[0]] }]; parserDoc(x); }));
}

if (echecs.length) {
  console.error("ECHECS apparence2 :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA apparence2 : PASS (34 controles)");
