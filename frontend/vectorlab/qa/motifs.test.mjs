// motifs.test.mjs — lot D5 « Couleur et motif » (t478) : les motifs FAITS D'OBJETS (js/mod-motifs.js) et leur rendu
// SVG (compilerSVG de mod-doc.js) et PDF (mod-pdf.js, relu par l'import de D4). Pavage grille, brique (lignes ou
// colonnes) ou hexagone, espacement (négatif = chevauchement), cellule périodique ; cycles refusés.
import { createRequire } from "node:module";
import { motif_objets_valider, motif_objets_cellule, op_motif_depuis_selection, op_motif_regler, op_motif_contenu, PAVAGES } from "../js/mod-motifs.js";
import { compilerSVG, parserDoc } from "../js/mod-doc.js";
import { pdf_page, pdf_assembler } from "../js/mod-pdf.js";
import { pdf_vers_objets } from "../js/mod-importpdf.js";
import { fournirMartinez } from "../js/mod-bool.js";
import { T } from "../js/mod-i18n.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : ""));
};
const refus = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
const ROND = { id: "x", type: "ellipse", cx: 5, cy: 5, rx: 5, ry: 5, style: { fond: "#ff0000" } };
const M = (extra = {}) => ({ type: "objets", pavage: "grille", largeur: 10, hauteur: 10, espacement: { h: 0, v: 0 }, objets: [ROND], ...extra });

/* ── validation ── */
{
  ok("les quatre pavages", JSON.stringify(PAVAGES) === JSON.stringify(["grille", "brique_lignes", "brique_colonnes", "hexagone"]));
  ok("un motif d'objets valide", refus(() => motif_objets_valider(M())) === null);
  ok("pavage inconnu → refus traduit", refus(() => motif_objets_valider(M({ pavage: "spirale" }))) === T("vectorlab.motifs.pavage", { pavage: "spirale" }));
  ok("taille nulle → refus traduit", refus(() => motif_objets_valider(M({ largeur: 0 }))) === T("vectorlab.motifs.taille"));
  ok("espacement qui annule la cellule → refus traduit", refus(() => motif_objets_valider(M({ espacement: { h: -10, v: 0 } }))) === T("vectorlab.motifs.espacement")
     && refus(() => motif_objets_valider(M({ espacement: { h: -9.5, v: 0 } }))) === null);
  ok("hexagone : le pas vertical (3/4 de la tuile) borne l'espacement", refus(() => motif_objets_valider(M({ pavage: "hexagone", espacement: { h: 0, v: -8 } }))) === T("vectorlab.motifs.espacement")
     && refus(() => motif_objets_valider(M({ espacement: { h: 0, v: -8 } }))) === null);
  ok("sans objets → refus traduit", refus(() => motif_objets_valider(M({ objets: [] }))) === T("vectorlab.motifs.vide"));
  ok("objet non pris (image), même dans un groupe → refus traduit", refus(() => motif_objets_valider(M({ objets: [{ id: "g", type: "groupe", style: {}, enfants: [{ id: "i", type: "image", x: 0, y: 0, w: 1, h: 1, href: "a.png", nat: { w: 1, h: 1 }, style: {} }] }] })))
     === T("vectorlab.motifs.type_objet", { type: "image" }));
  ok("effets ou masque dans un motif → refus traduit", refus(() => motif_objets_valider(M({ objets: [{ ...ROND, style: { fond: "#000000", effets: [{ type: "ombre" }] } }] }))) === T("vectorlab.motifs.effets"));
  ok("fond de couleur invalide → refus", refus(() => motif_objets_valider(M({ fond: "rouge" }))) !== null && refus(() => motif_objets_valider(M({ fond: "#ffffff" }))) === null);
}

/* ── la cellule périodique ── */
{
  const g = motif_objets_cellule(M({ espacement: { h: 2, v: 4 } }));
  ok("grille : cellule = tuile + espacement, une copie", g.l === 12 && g.h === 14 && g.copies.length === 1 && g.copies[0][0] === 0 && g.copies[0][1] === 0, JSON.stringify(g));
  const b = motif_objets_cellule(M({ pavage: "brique_lignes" }));
  ok("brique (lignes) : deux rangées, la seconde décalée d'une demi-tuile (et son reste à gauche)", b.l === 10 && b.h === 20
     && b.copies.some(([x, y]) => x === 5 && y === 10) && b.copies.some(([x, y]) => x === -5 && y === 10) && b.copies.some(([x, y]) => x === 0 && y === 0), JSON.stringify(b.copies));
  const c = motif_objets_cellule(M({ pavage: "brique_colonnes" }));
  ok("brique (colonnes) : deux colonnes, la seconde décalée d'une demi-tuile", c.l === 20 && c.h === 10 && c.copies.some(([x, y]) => x === 10 && y === 5) && c.copies.some(([x, y]) => x === 10 && y === -5), JSON.stringify(c.copies));
  const h = motif_objets_cellule(M({ pavage: "hexagone" }));
  ok("hexagone : rangées au pas de 3/4 de la tuile, décalées d'une demi-tuile", h.l === 10 && pres(h.h, 15) && h.copies.some(([x, y]) => x === 5 && pres(y, 7.5)), JSON.stringify(h));
  const r = motif_objets_cellule(M({ espacement: { h: -4, v: -4 } }));
  ok("chevauchement : les voisines qui débordent dans la cellule sont dessinées", r.l === 6 && r.copies.length === 4 && r.copies.some(([x, y]) => x === -6 && y === -6), JSON.stringify(r.copies));
  ok("seules les copies qui touchent la cellule", motif_objets_cellule(M()).copies.every(([x, y]) => x + 10 > 0 && x < 10 && y + 10 > 0 && y < 10));
}

/* ── créer, régler, remplacer ── */
const doc = (...objets) => ({ v: 1, taille: { w: 200, h: 200 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets }] });
{
  const d = doc(
    { id: "a", type: "rect", x: 50, y: 60, w: 10, h: 20, style: { fond: "#00ff00", effets: [{ type: "ombre", dx: 1, dy: 1, flou: 1, couleur: "#000000", opacite: 0.5 }] } },
    { id: "b", type: "ellipse", cx: 70, cy: 70, rx: 5, ry: 5, style: { fond: "#0000ff" } },
    { id: "cible", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "#ffffff" } });
  const id = op_motif_depuis_selection(d, ["a", "b"], { pavage: "brique_lignes", espacement: { h: 2, v: 0 } });
  const m = d.motifs[id];
  ok("créé depuis la sélection : id m<n>, type objets, réglages", /^m\d+$/.test(id) && m.type === "objets" && m.pavage === "brique_lignes" && m.espacement.h === 2);
  ok("taille = boîte de la sélection", pres(m.largeur, 25) && pres(m.hauteur, 20), JSON.stringify([m.largeur, m.hauteur]));
  ok("objets ramenés à l'origine (translate), effets retirés, originaux intacts", m.objets.length === 2 && m.objets[0].transform === "translate(-50 -60)"
     && !m.objets[0].style.effets && d.calques[0].objets[0].style.effets.length === 1 && d.calques[0].objets.length === 3, JSON.stringify(m.objets[0]));
  ok("le document reste valide", refus(() => parserDoc(d)) === null, refus(() => parserDoc(d)));
  op_motif_regler(d, id, { pavage: "hexagone", espacement: { h: 0, v: 1 }, fond: "#eeeeee" });
  ok("régler : pavage, espacement, fond", d.motifs[id].pavage === "hexagone" && d.motifs[id].espacement.v === 1 && d.motifs[id].fond === "#eeeeee" && d.motifs[id].objets.length === 2);
  ok("régler : un réglage refusé ne change rien", refus(() => op_motif_regler(d, id, { pavage: "zz" })) === T("vectorlab.motifs.pavage", { pavage: "zz" }) && d.motifs[id].pavage === "hexagone");
  ok("régler un motif paramétrique → refus traduit", (() => { d.motifs.mp = { type: "points", pas: 8 }; return refus(() => op_motif_regler(d, "mp", { pavage: "grille" })) === T("vectorlab.motifs.pas_objets"); })());
  op_motif_contenu(d, id, ["b"]);
  ok("remplacer le contenu : la nouvelle sélection, sa taille ; les réglages restent", d.motifs[id].objets.length === 1 && pres(d.motifs[id].largeur, 10) && d.motifs[id].pavage === "hexagone");
  // un cycle : le contenu emploie le motif lui-même
  d.calques[0].objets[2].style.fond = "motif:" + id;
  ok("cycle (le motif se contiendrait) → refus traduit, rien de changé", refus(() => op_motif_contenu(d, id, ["cible"])) === T("vectorlab.motifs.cycle", { id }) && d.motifs[id].objets.length === 1);
  ok("objet verrouillé : pas pris", refus(() => op_motif_depuis_selection(doc({ id: "v", type: "rect", x: 0, y: 0, w: 1, h: 1, verrou: true, style: {} }), ["v"], {})) === T("vectorlab.motifs.aucune_selection"));
  ok("fond donné à la création", (() => { const x = doc({ id: "q", type: "rect", x: 0, y: 0, w: 4, h: 4, style: { fond: "#000000" } }); const i = op_motif_depuis_selection(x, ["q"], { fond: "#ffffff" }); return x.motifs[i].fond === "#ffffff"; })());
  ok("sélection vide → refus traduit", refus(() => op_motif_depuis_selection(d, [], {})) === T("vectorlab.motifs.aucune_selection"));
  ok("image dans la sélection → refus traduit", refus(() => op_motif_depuis_selection(doc({ id: "i", type: "image", x: 0, y: 0, w: 1, h: 1, href: "a.png", nat: { w: 1, h: 1 }, style: {} }), ["i"], {})) === T("vectorlab.motifs.type_objet", { type: "image" }));
  // un objet vivant : ses copies générées gardées en objets simples, la source cachée d'une déformation retirée
  const v = doc({ id: "g", type: "groupe", style: {}, deformation: { effet: "torsion" }, enfants: [
    { id: "s", type: "rect", x: 0, y: 0, w: 10, h: 10, cache: true, style: { fond: "#000000" } },
    { id: "g_d1", type: "path", d: "M0 0 L10 0 L10 10 Z", genere: true, style: { fond: "#000000" } }] });
  const iv = op_motif_depuis_selection(v, ["g"], {});
  const gv = v.motifs[iv].objets[0];
  ok("objet vivant : recette retirée, source cachée retirée, copie générée gardée", !gv.deformation && gv.enfants.length === 1 && gv.enfants[0].id === "g_d1" && !gv.enfants[0].genere, JSON.stringify(gv));
}

/* ── SVG ── */
{
  const d = doc({ id: "f", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "motif:m1" } });
  d.couleursGlobales = { Fond: "#fafafa" };
  d.degrades = { g1: { type: "lineaire", x1: 0, y1: 0, x2: 10, y2: 0, stops: [{ t: 0, couleur: "#ff0000" }, { t: 1, couleur: "#0000ff" }] } };
  d.motifs = { m1: M({ pavage: "brique_lignes", fond: "glob:Fond", objets: [ROND, { id: "y", type: "rect", x: 0, y: 0, w: 2, h: 2, style: { fond: "motif:m2" } }, { id: "z", type: "rect", x: 3, y: 3, w: 2, h: 2, style: { fond: "grad:g1" } }] }),
    m2: { type: "points", pas: 4 } };
  const svg = compilerSVG(d);
  const pat = (svg.match(/<pattern id="m1"[\s\S]*?<\/pattern>/) || [""])[0];
  ok("SVG : <pattern> de la cellule (10 × 20)", /width="10" height="20"/.test(pat), pat.slice(0, 200));
  ok("SVG : une copie par position (translate)", (pat.match(/<g transform="translate\(/g) || []).length === motif_objets_cellule(d.motifs.m1).copies.length && /translate\(5 10\)/.test(pat), pat);
  ok("SVG : fond (globale résolue), objets dessinés", /<rect x="0" y="0" width="10" height="20" fill="#fafafa"\/>/.test(pat) && /<ellipse/.test(pat) && /fill="#ff0000"/.test(pat));
  ok("SVG : un motif et un dégradé employés DANS le motif sont émis aussi", /<pattern id="m2"/.test(svg) && /<linearGradient id="g1"/.test(svg), svg.slice(0, 400));
  ok("SVG : sans id d'objet dans le motif", !/data-objet="x"/.test(pat));
  d.motifs.m2 = M({ objets: [{ id: "w", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "motif:m1" } }] });
  ok("SVG : un cycle entre motifs → refus traduit", refus(() => compilerSVG(d)) === T("vectorlab.motifs.cycle", { id: "m1" }) || refus(() => compilerSVG(d)) === T("vectorlab.motifs.cycle", { id: "m2" }), refus(() => compilerSVG(d)));
}

/* ── un objet illisible dans un motif : sauté, le reste est rendu (SVG et PDF) ── */
{
  const d = doc({ id: "f", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "motif:m1" } });
  d.motifs = { m1: M({ objets: [{ id: "bad", type: "forme", forme: "etoile", cx: 5, cy: 5, r: 4, style: { fond: "#000000" } }, ROND] }) };
  let svg = null;
  ok("SVG : l'objet illisible est sauté, le rond est rendu", refus(() => { svg = compilerSVG(d); }) === null && /<pattern id="m1"[\s\S]*<ellipse/.test(svg), refus(() => compilerSVG(d)));
  const P = Object.values(pdf_page(d, { x: 0, y: 0, w: 200, h: 200 }, { dpi: 96 }).patterns)[0];
  ok("PDF : idem", P && /1 0 0 rg/.test(P.contenu));
}

/* ── PDF : un motif de pavage dont la cellule porte les objets ── */
{
  const d = doc({ id: "f", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "motif:m1" } });
  d.motifs = { m1: M({ pavage: "brique_colonnes", espacement: { h: 2, v: 0 }, objets: [ROND, { id: "t", type: "rect", x: 0, y: 0, w: 4, h: 4, style: { fond: "#00ff00", opacite: 0.5 } }] }) };
  const p = pdf_page(d, { x: 0, y: 0, w: 200, h: 200 }, { dpi: 96 });
  const P = Object.values(p.patterns)[0];
  ok("PDF : un motif de pavage, cellule 24 × 10, pas X / Y distincts", P && P.pasX === 24 && P.pasY === 10 && P.bbox.join(" ") === "0 0 24 10" && P.ressources === true, JSON.stringify(P && { ...P, contenu: undefined }));
  ok("PDF : la cellule porte les copies (cm) et les objets (couleur, opacité par gs)", (P.contenu.match(/ cm\n/g) || []).length >= motif_objets_cellule(d.motifs.m1).copies.length && /1 0 0 rg/.test(P.contenu) && /\/G\d+ gs/.test(P.contenu), P.contenu.slice(0, 300));
  const octets = await pdf_assembler([p]);
  const s = Buffer.from(octets).toString("latin1");
  ok("PDF assemblé : /XStep 24 /YStep 10, ressources de la page", /\/XStep 24 \/YStep 10 \/Resources \d+ 0 R/.test(s), (s.match(/\/XStep[^\n]{0,80}/) || [""])[0]);
  // un texte sans glyphes fournis se rastériserait : dans un motif, il est sauté (jamais de marqueur RASTER)
  const dt = doc({ id: "f", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "motif:m1" } });
  dt.motifs = { m1: M({ objets: [ROND, { id: "tx", type: "texte", x: 0, y: 8, contenu: "A", style: { fond: "#000000", corps: 8 } }] }) };
  const pt = pdf_page(dt, { x: 0, y: 0, w: 200, h: 200 }, { dpi: 96 });
  const Pt = Object.values(pt.patterns)[0];
  ok("PDF : un objet qui se rastériserait est sauté dans le motif", Pt && !/RASTER/.test(Pt.contenu) && /1 0 0 rg/.test(Pt.contenu) && pt.rasters.length === 0, Pt && Pt.contenu.slice(0, 200));
  // un fond en dégradé conique se rastériserait aussi : sauté, jamais de shading faux dans la cellule
  const dk = doc({ id: "f", type: "rect", x: 0, y: 0, w: 100, h: 100, style: { fond: "motif:m1" } });
  dk.degrades = { gc: { type: "conique", cx: 5, cy: 5, r: 5, angle: 0, stops: [{ t: 0, couleur: "#ff0000" }, { t: 1, couleur: "#0000ff" }] } };
  dk.motifs = { m1: M({ objets: [ROND, { id: "k", type: "rect", x: 0, y: 0, w: 4, h: 4, style: { fond: "grad:gc" } }] }) };
  const pk = pdf_page(dk, { x: 0, y: 0, w: 200, h: 200 }, { dpi: 96 });
  const Pk = Object.values(pk.patterns)[0];
  ok("PDF : un fond conique (rastérisé ailleurs) est sauté dans le motif", Pk && !/ sh/.test(Pk.contenu) && !/NaN/.test(Pk.contenu) && Object.keys(pk.shadings).length === 0, Pk && Pk.contenu.slice(0, 300));
  const relu = await pdf_vers_objets(octets);
  ok("PDF relu (import D4) : un objet, rempli (motif → gris compté)", relu.objets.length === 1 && relu.stats.ignores.motif === 1, JSON.stringify(relu.stats));
}

if (echecs.length) {
  console.error(`motifs : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("motifs : ok");
