// pdf.test.mjs — t121 : le PDF VECTORIEL écrit depuis le modèle du document (mod-pdf.js, pur).
// Les opérateurs sont lus dans le flux de la page ; la relecture par un vrai lecteur (pypdf) est le banc
// Python test_vector_pdf.py, qui rejoue ce module par node.
import { matrice_de, matrice_mul, chemin_ops, couleur_rgba, pdf_page, pdf_assembler } from "../js/mod-pdf.js";

const echecs = [];
let nControles = 0;
const ok = (nom, cond, detail = "") => {
  nControles++;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
const proche = (a, b, e = 1e-9) => a.length === b.length && a.every((v, i) => Math.abs(v - b[i]) < e);
const base = (objets = [], extra = {}) => ({ v: 1, nom: "P", taille: { w: 300, h: 200 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets }], ...extra });
const CADRE = { x: 0, y: 0, w: 300, h: 200 };
const page = (doc, opts = {}) => pdf_page(doc, CADRE, { dpi: 72, ...opts });

/* ── matrices ── */
{
  ok("translate", proche(matrice_de("translate(10 20)"), [1, 0, 0, 1, 10, 20]));
  ok("translate à un argument", proche(matrice_de("translate(7)"), [1, 0, 0, 1, 7, 0]));
  ok("scale(2) et scale(2 3)", proche(matrice_de("scale(2)"), [2, 0, 0, 2, 0, 0]) && proche(matrice_de("scale(2,3)"), [2, 0, 0, 3, 0, 0]));
  ok("rotate(90)", proche(matrice_de("rotate(90)"), [0, 1, -1, 0, 0, 0], 1e-12));
  // rotate(a cx cy) = translate(cx cy) rotate(a) translate(-cx -cy) : le point (cx, cy) ne bouge pas
  const r = matrice_de("rotate(90 10 10)");
  ok("rotate autour d'un point le laisse fixe", Math.abs(r[0] * 10 + r[2] * 10 + r[4] - 10) < 1e-9 && Math.abs(r[1] * 10 + r[3] * 10 + r[5] - 10) < 1e-9, JSON.stringify(r));
  ok("matrix(a b c d e f)", proche(matrice_de("matrix(1 2 3 4 5 6)"), [1, 2, 3, 4, 5, 6]));
  ok("skewX(45)", proche(matrice_de("skewX(45)"), [1, 0, 1, 1, 0, 0], 1e-12));
  // une LISTE se compose de gauche à droite : translate puis scale = T·S
  ok("liste composée T·S", proche(matrice_de("translate(1 2) scale(3)"), [3, 0, 0, 3, 1, 2]));
  ok("vide = identité", proche(matrice_de(""), [1, 0, 0, 1, 0, 0]) && proche(matrice_de(undefined), [1, 0, 0, 1, 0, 0]));
  ok("matrice_mul", proche(matrice_mul([2, 0, 0, 2, 0, 0], [1, 0, 0, 1, 5, 0]), [2, 0, 0, 2, 10, 0]));
  let refus = 0;
  for (const t of ["tourne(3)", "translate(a b)", "matrix(1 2 3)"]) { try { matrice_de(t); } catch { refus++; } }
  ok("transformations malformées refusées", refus === 3, String(refus));
}
/* ── chemins ── */
{
  ok("M L Z → m l h", chemin_ops("M 0 0 L 10 0 L 10 5 Z") === "0 0 m 10 0 l 10 5 l h");
  ok("C → c", chemin_ops("M 0 0 C 1 2 3 4 5 6") === "0 0 m 1 2 3 4 5 6 c");
  // Q (quadratique) → cubique EXACTE : P0 + 2/3 (Q − P0) et P2 + 2/3 (Q − P2)
  ok("Q → c exacte", chemin_ops("M 0 0 Q 3 3 6 0") === "0 0 m 2 2 4 2 6 0 c", chemin_ops("M 0 0 Q 3 3 6 0"));
  ok("nombres courts, sans -0", chemin_ops("M -0 0.12345 L 1.0006 2") === "0 0.123 m 1.001 2 l", chemin_ops("M -0 0.12345 L 1.0006 2"));
}
/* ── couleurs ── */
{
  ok("#RRGGBB", proche(couleur_rgba("#FF8000"), [1, 128 / 255, 0, 1]));
  ok("#RGB", proche(couleur_rgba("#F80"), [1, 136 / 255, 0, 1]));
  ok("#RRGGBBAA : alpha", proche(couleur_rgba("#00000080"), [0, 0, 0, 128 / 255]));
  ok("none / indéfini → null", couleur_rgba("none") === null && couleur_rgba(undefined) === null);
  ok("glob: résolue par la table", proche(couleur_rgba("glob:marque", { marque: "#0000FF" }), [0, 0, 1, 1]));
  ok("glob: inconnue → null", couleur_rgba("glob:zz", {}) === null);
}
/* ── la page : repère, fond, rect, contour ── */
{
  const p = page(base([{ id: "r1", type: "rect", x: 10, y: 20, w: 30, h: 40, style: { fond: "#FF0000" } }]));
  ok("taille en points : px au dpi du document (72 → 1:1)", p.w_pt === 300 && p.h_pt === 200, `${p.w_pt} ${p.h_pt}`);
  ok("repère : y retourné, origine au haut du cadre", p.contenu.startsWith("1 0 0 -1 0 200 cm"), p.contenu.slice(0, 40));
  ok("rect plein : couleur + chemin + f", /1 0 0 rg\n10 20 m 40 20 l 40 60 l 10 60 l h\nf/.test(p.contenu), p.contenu);
  ok("aucun raster pour un rect plein", p.rasters.length === 0 && p.stats.vectoriels === 1 && p.stats.rasterises === 0);
  const p300 = pdf_page(base([]), CADRE, { dpi: 300 });
  ok("dpi 300 : 300 px = 72 pt", Math.abs(p300.w_pt - 72) < 1e-9 && p300.contenu.startsWith("0.24 0 0 -0.24 0 48 cm"), p300.contenu.slice(0, 40));
  const decale = pdf_page(base([]), { x: 50, y: 10, w: 100, h: 100 }, { dpi: 72 });
  ok("cadre décalé : l'origine suit", decale.contenu.startsWith("1 0 0 -1 -50 110 cm"), decale.contenu.slice(0, 40));
  const c = page(base([{ id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#00FF00", contour: "#0000FF", epaisseur: 3, joint: "miter", pointilles: "4 2" } }]));
  ok("contour : RG, w, j, J, d et B (fond + contour)", /0 0 1 RG/.test(c.contenu) && /3 w/.test(c.contenu) && /0 j/.test(c.contenu) && /1 J/.test(c.contenu) && /\[4 2\] 0 d/.test(c.contenu) && /\nB\n?/.test(c.contenu), c.contenu);
  const s = page(base([{ id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { contour: "#000000" } }]));
  ok("contour seul : S, jointure ronde par défaut", /\nS/.test(s.contenu) && /1 j/.test(s.contenu) && !/\nf/.test(s.contenu), s.contenu);
  const eo = page(base([{ id: "p1", type: "path", d: "M 0 0 L 10 0 L 10 10 Z", style: { fond: "#000000", regle: "evenodd" } }]));
  ok("evenodd : f*", /\nf\*/.test(eo.contenu), eo.contenu);
  const rien = page(base([{ id: "p1", type: "path", d: "M 0 0 L 10 0 L 10 10 Z", style: {} }]));
  ok("ni fond ni contour : rien n'est peint", !/\n[fBS]\*?\n?$/m.test(rien.contenu.split("\n").slice(1).join("\n")) && !/ re|\nf/.test(rien.contenu), rien.contenu);
  const fond = page(base([], { fond: "#123456" }));
  ok("fond du document peint sous tout", /0.071 0.204 0.337 rg\n0 0 m 300 0 l 300 200 l 0 200 l h\nf/.test(fond.contenu), fond.contenu);
  ok("… sauf transparent", !/rg/.test(page(base([], { fond: "#123456" }), { transparent: true }).contenu));
}
/* ── géométries ── */
{
  const e = page(base([{ id: "e1", type: "ellipse", cx: 50, cy: 50, rx: 20, ry: 10, style: { fond: "#000000" } }]));
  ok("ellipse : 4 cubiques fermées", (e.contenu.match(/\d c\b/g) || []).length === 4 && /h\nf/.test(e.contenu), e.contenu);
  const rr = page(base([{ id: "r", type: "rect", x: 0, y: 0, w: 40, h: 20, rx: 5, style: { fond: "#000000" } }]));
  ok("rect arrondi : 4 coins en cubiques", (rr.contenu.match(/\d c\b/g) || []).length === 4, rr.contenu);
  const f = page(base([{ id: "f", type: "forme", forme: "polygone", cx: 50, cy: 50, r: 10, params: { n: 6 }, style: { fond: "#000000" } }]));
  ok("forme : son chemin (6 côtés)", (f.contenu.match(/\d l\b/g) || []).length === 5 && /\d m\b/.test(f.contenu), f.contenu);
  const d = base([{ id: "t1", type: "tuile", q: 0, r: 0, terrain: "foret" }]); d.grille = { type: "hex", pas: 20, sous: 1, orientation: "pointe", origine: [0, 0], echelle: [1, 1] };
  const t = page(d);
  ok("tuile : hexagone à la couleur du terrain (forêt #3F7D3A) + contour brun", /0.247 0.49 0.227 rg/.test(t.contenu) && (t.contenu.match(/\d l\b/g) || []).length === 5 && /\nB/.test(t.contenu), t.contenu);
  const tr = page(base([{ id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, transform: "translate(5 6)", style: { fond: "#000000" } }]));
  ok("transform d'objet : q, cm, Q autour", /q\n1 0 0 1 5 6 cm\n/.test(tr.contenu) && /\nQ/.test(tr.contenu), tr.contenu);
}
/* ── opacité, fusion, groupes de transparence ── */
{
  const o = page(base([{ id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#000000", opacite: 0.5 } }]));
  ok("opacité, fond seul : ExtGState ca", /\/G\d+ gs/.test(o.contenu) && Object.values(o.gs).some((g) => g.ca === 0.5) && !Object.keys(o.formes).length, JSON.stringify(o.gs));
  const fa = page(base([{ id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#00000080" } }]));
  ok("alpha de la couleur → ca", Object.values(fa.gs).some((g) => Math.abs(g.ca - 128 / 255) < 1e-9));
  // fond + contour à demi-opacité : un GROUPE (sinon la zone de recouvrement serait deux fois plus sombre)
  const g = page(base([{ id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#000000", contour: "#FF0000", epaisseur: 4, opacite: 0.5 } }]));
  ok("opacité fond + contour : groupe de transparence (Form) dessiné à ca .5", Object.keys(g.formes).length === 1 && /\/F\d+ Do/.test(g.contenu) && Object.values(g.gs).some((x) => x.ca === 0.5 && x.CA === 0.5), g.contenu);
  const m = page(base([{ id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#000000", fusion: "multiply" } }]));
  ok("fusion multiply → BM /Multiply", Object.values(m.gs).some((x) => x.BM === "Multiply"));
  const cd = page(base([{ id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#000000", fusion: "color-dodge" } }]));
  ok("fusion color-dodge → ColorDodge", Object.values(cd.gs).some((x) => x.BM === "ColorDodge"));
  const dc = base([{ id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#000000" } }, { id: "r2", type: "rect", x: 5, y: 5, w: 10, h: 10, style: { fond: "#000000" } }]);
  dc.calques[0].opacite = 0.4;
  const pc = page(dc);
  ok("calque à .4 : UN groupe pour ses deux objets", Object.keys(pc.formes).length === 1 && (pc.contenu.match(/ Do/g) || []).length === 1 && Object.values(pc.formes)[0].split("\nf").length === 3, JSON.stringify(pc.formes));
  const inv = base([{ id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#FF0000" } }]); inv.calques[0].visible = false;
  ok("calque invisible : rien", !/rg/.test(page(inv).contenu) && page(inv).stats.vectoriels === 0);
}
/* ── groupes, écrêtage, symboles ── */
{
  const g = page(base([{ id: "g", type: "groupe", transform: "scale(2)", style: {}, enfants: [
    { id: "a", type: "rect", x: 0, y: 0, w: 5, h: 5, style: { fond: "#000000" } },
    { id: "b", type: "rect", x: 10, y: 0, w: 5, h: 5, style: { fond: "#FF0000" } }] }]));
  ok("groupe : cm du groupe puis ses enfants dans l'ordre", /2 0 0 2 0 0 cm\n[\s\S]*0 0 0 rg[\s\S]*1 0 0 rg/.test(g.contenu), g.contenu);
  const cl = page(base([{ id: "g", type: "groupe", clip: "c", style: {}, enfants: [
    { id: "c", type: "ellipse", cx: 10, cy: 10, rx: 5, ry: 5, style: {} },
    { id: "a", type: "rect", x: 0, y: 0, w: 20, h: 20, style: { fond: "#000000" } }] }]));
  ok("groupe écrêté : chemin du conteneur puis W n, avant les enfants", /c h\nW n\n[\s\S]*0 0 0 rg\n0 0 m 20 0 l/.test(cl.contenu), cl.contenu);
  const sy = base([{ id: "i1", type: "instance", symbole: "s1", x: 100, y: 50, sx: 2, sy: 2 }]);
  sy.symboles = { s1: { nom: "S", objets: [{ id: "x", type: "rect", x: 0, y: 0, w: 4, h: 4, style: { fond: "#00FF00" } }] } };
  const ps = page(sy);
  ok("instance : translate(x y) scale(sx sy) puis les objets du symbole", /1 0 0 1 100 50 cm\n2 0 0 2 0 0 cm\n[\s\S]*0 1 0 rg\n0 0 m 4 0 l/.test(ps.contenu) || /2 0 0 2 100 50 cm\n[\s\S]*0 1 0 rg/.test(ps.contenu), ps.contenu);
}
/* ── le REPLI raster : ce qu'un PDF simple ne porte pas, objet de premier niveau par objet ── */
{
  const d = base([
    { id: "v", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#000000" } },
    { id: "fx", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#000000", effets: [{ type: "ombre", dx: 2, dy: 2, flou: 3, couleur: "#000000", opacite: 0.5 }] } },
    { id: "im", type: "image", href: "a.png", x: 0, y: 0, w: 10, h: 10, nat: { w: 10, h: 10 } },
    { id: "g", type: "groupe", style: {}, enfants: [{ id: "tc", type: "textechemin", d: "M 0 0 L 10 0", contenu: "x", style: {} }] },
    { id: "v2", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#FF0000" } },
  ]);
  const p = page(d);
  ok("rasters : effet, image, et le GROUPE qui contient un texte sur chemin", JSON.stringify(p.rasters.map((r) => r.id)) === '["fx","im","g"]', JSON.stringify(p.rasters));
  ok("chaque raster a un nom d'image et une raison dite", p.rasters.every((r) => /^I\d+$/.test(r.nom) && r.raison), JSON.stringify(p.rasters));
  // l'ORDRE de peinture est gardé : le marqueur du raster est à sa place entre v et v2
  const iv = p.contenu.indexOf("0 0 0 rg"), ifx = p.contenu.indexOf("%%RASTER I1%%"), iv2 = p.contenu.indexOf("1 0 0 rg");
  ok("ordre de peinture gardé (v, rasters, v2)", iv >= 0 && ifx > iv && iv2 > p.contenu.indexOf("%%RASTER I3%%"), p.contenu);
  ok("stats : 2 vectoriels, 3 rasterisés", p.stats.vectoriels === 2 && p.stats.rasterises === 3, JSON.stringify(p.stats));
  const tx = page(base([{ id: "t", type: "texte", x: 10, y: 20, contenu: "Hé", style: { fond: "#000000", corps: 12 } }]));
  ok("texte sans glyphes fournis : rasterisé (raison texte)", tx.rasters.length === 1 && /texte/.test(tx.rasters[0].raison), JSON.stringify(tx.rasters));
  const gl = pdf_page(base([{ id: "t", type: "texte", x: 10, y: 20, contenu: "H", style: { fond: "#112233", corps: 12 } }]), CADRE,
    { dpi: 72, glyphes: (o) => o.id === "t" ? [{ car: "H", d: "M 0 0 L 5 0 L 5 5 Z" }] : null });
  ok("texte avec glyphes : vectoriel, contours pleins en evenodd", gl.rasters.length === 0 && /0.067 0.133 0.2 rg/.test(gl.contenu) && /\nf\*/.test(gl.contenu), gl.contenu);
}
/* ── l'assemblage : un PDF lisible, xref exacte, images avec SMask ── */
{
  const dec = new TextDecoder("latin1");
  const p1 = page(base([{ id: "r1", type: "rect", x: 10, y: 20, w: 30, h: 40, style: { fond: "#FF0000" } }]));
  const p2 = page(base([{ id: "fx", type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#000000", effets: [{ type: "ombre" }] } }]));
  const rgba = new Uint8Array(4 * 2 * 3); for (let i = 0; i < 6; i++) rgba.set([255, 0, 0, i * 40], 4 * i);
  const octets = await pdf_assembler([p1, { ...p2, images: { I1: { x: 1, y: 2, w: 8, h: 6, largeur: 2, hauteur: 3, rgba } } }], { compresser: false });
  const s = dec.decode(octets);
  ok("en-tête %PDF-1.4", s.startsWith("%PDF-1.4\n"));
  ok("deux pages", /\/Type \/Pages \/Kids \[[^\]]+\] \/Count 2/.test(s), s.slice(0, 400));
  const xref = +s.match(/startxref\n(\d+)/)[1];
  ok("startxref pointe sur xref", s.slice(xref, xref + 4) === "xref");
  const lignes = s.slice(xref).split("\n"), n = +lignes[1].split(" ")[1];
  let bons = 0;
  for (let i = 1; i < n; i++) { const off = +lignes[2 + i].slice(0, 10); if (s.startsWith(`${i} 0 obj`, off)) bons++; }
  ok("chaque entrée de xref pointe sur son objet", bons === n - 1, `${bons}/${n - 1}`);
  ok("image : RGB 2x3 + SMask", /\/Subtype \/Image \/Width 2 \/Height 3 \/ColorSpace \/DeviceRGB \/BitsPerComponent 8 \/SMask \d+ 0 R/.test(s) && /\/ColorSpace \/DeviceGray/.test(s), s.replace(/stream[\s\S]*?endstream/g, "…"));
  ok("raster posé à son rectangle, y retourné (8 x 6 en (1, 2))", s.includes("q 8 0 0 -6 1 8 cm /I1 Do Q"), "");
  let refus = 0;
  try { await pdf_assembler([p2], { compresser: false }); } catch (e) { if (/I1 \(fx, effet\) n'a pas d'image/.test(e.message)) refus++; }
  ok("un raster sans son image : refusé (jamais un trou muet)", refus === 1);
}

if (echecs.length) {
  console.error("ECHECS pdf :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log(`QA pdf : PASS (${nControles} controles)`);
