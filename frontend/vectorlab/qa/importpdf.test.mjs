// importpdf.test.mjs — lot D4 « Interop » (t471) : lire la PREMIÈRE page d'un PDF en objets vectoriels du Vectorlab
// (js/mod-importpdf.js). Trois sources : un PDF écrit par mod-pdf.js lui-même (aller-retour), des PDF écrits À LA MAIN
// ici (table xref classique, puis flux xref à prédicteur PNG + flux d'objets compressés), et des fichiers refusés.
import { deflateSync } from "node:zlib";
import { createRequire } from "node:module";
import { pdf_vers_objets } from "../js/mod-importpdf.js";
import { pdf_page, pdf_assembler } from "../js/mod-pdf.js";
import { polylignes_objet, fournirMartinez, versMulti, aplatir_objet, aire_multi } from "../js/mod-bool.js";
import { T } from "../js/mod-i18n.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const aire = (o) => aire_multi(versMulti(aplatir_objet(o)));
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : ""));
};
const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
const refus = async (p) => { try { await p; return null; } catch (e) { return e.message; } };
const enc = (s) => Uint8Array.from(s, (c) => c.charCodeAt(0) & 255);
const concat = (...p) => { const o = new Uint8Array(p.reduce((s, x) => s + x.length, 0)); let k = 0; for (const x of p) { o.set(x, k); k += x.length; } return o; };
const boite = (o) => {
  const P = polylignes_objet(o).flatMap((l) => l.points);
  const xs = P.map((p) => p[0]), ys = P.map((p) => p[1]);
  return { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
};
const K = 96 / 72;

/* un PDF à table xref classique : corps[i] = corps de l'objet i+1 (texte, ou [dict, octets du flux]) */
function classique(corps, trailer) {
  const parts = [enc("%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")];
  let pos = parts[0].length;
  const off = [];
  corps.forEach((c, i) => {
    off.push(pos);
    const b = Array.isArray(c) ? concat(enc(`${i + 1} 0 obj\n<< ${c[0]} /Length ${c[1].length} >>\nstream\n`), c[1], enc("\nendstream\nendobj\n"))
      : enc(`${i + 1} 0 obj\n${c}\nendobj\n`);
    parts.push(b); pos += b.length;
  });
  parts.push(enc(`xref\n0 ${corps.length + 1}\n0000000000 65535 f \n` + off.map((o) => `${String(o).padStart(10, "0")} 00000 n \n`).join("")
    + `trailer\n<< /Size ${corps.length + 1} ${trailer} >>\nstartxref\n${pos}\n%%EOF\n`));
  return concat(...parts);
}

/* un PDF 1.5 « moderne » : les objets `dansStm` vivent dans un flux d'objets compressé, l'index est un flux xref
   compressé avec prédicteur PNG (Up), comme les écrivent Illustrator et la plupart des outils */
function moderne(corps, dansStm, racine) {
  const n = corps.length;                                   // objets 1..n ; n+1 = ObjStm ; n+2 = flux xref
  const stmIds = dansStm.slice();
  let entete = "", donnees = "";
  for (const id of stmIds) { entete += `${id} ${donnees.length} `; donnees += corps[id - 1] + "\n"; }
  const stmBrut = enc(entete + donnees);
  const stm = deflateSync(stmBrut);
  const parts = [enc("%PDF-1.5\n%\xe2\xe3\xcf\xd3\n")];
  let pos = parts[0].length;
  const ent = new Map();
  corps.forEach((c, i) => {
    const id = i + 1;
    if (stmIds.includes(id)) { ent.set(id, [2, n + 1, stmIds.indexOf(id)]); return; }
    ent.set(id, [1, pos, 0]);
    const b = Array.isArray(c) ? concat(enc(`${id} 0 obj\n<< ${c[0]} /Length ${c[1].length} >>\nstream\n`), c[1], enc("\nendstream\nendobj\n"))
      : enc(`${id} 0 obj\n${c}\nendobj\n`);
    parts.push(b); pos += b.length;
  });
  ent.set(n + 1, [1, pos, 0]);
  const bs = concat(enc(`${n + 1} 0 obj\n<< /Type /ObjStm /N ${stmIds.length} /First ${entete.length} /Filter /FlateDecode /Length ${stm.length} >>\nstream\n`), stm, enc("\nendstream\nendobj\n"));
  parts.push(bs); pos += bs.length;
  ent.set(n + 2, [1, pos, 0]);
  // lignes de 7 octets (W [1 4 2]), chacune précédée de l'octet de filtre PNG 2 (Up)
  const lignes = [];
  for (let id = 0; id <= n + 2; id++) {
    const e = id === 0 ? [0, 0, 65535] : ent.get(id);
    lignes.push([e[0], (e[1] >>> 24) & 255, (e[1] >>> 16) & 255, (e[1] >>> 8) & 255, e[1] & 255, (e[2] >> 8) & 255, e[2] & 255]);
  }
  const brut = [];
  let prec = [0, 0, 0, 0, 0, 0, 0];
  for (const l of lignes) { brut.push(2, ...l.map((v, k) => (v - prec[k] + 256) & 255)); prec = l; }
  const xs = deflateSync(Uint8Array.from(brut));
  parts.push(concat(enc(`${n + 2} 0 obj\n<< /Type /XRef /Size ${n + 3} /W [1 4 2] /Root ${racine} 0 R /Filter /FlateDecode `
    + `/DecodeParms << /Predictor 12 /Columns 7 >> /Length ${xs.length} >>\nstream\n`), xs, enc(`\nendstream\nendobj\nstartxref\n${pos}\n%%EOF\n`)));
  return concat(...parts);
}

/* ── 1. aller-retour : un PDF écrit par mod-pdf.js (dpi 96 : 1 px du document = 0,75 pt) ── */
{
  const doc = { v: 1, nom: "P", taille: { w: 300, h: 200 }, degrades: { g1: { type: "lineaire", x1: 0, y1: 0, x2: 1, y2: 0, stops: [{ t: 0, couleur: "#ff8800" }, { t: 1, couleur: "#000000" }] } },
    calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
      { id: "r", type: "rect", x: 10, y: 20, w: 50, h: 30, style: { fond: "#ff0000", contour: "#0000ff", epaisseur: 2, joint: "miter" } },
      { id: "e", type: "ellipse", cx: 150, cy: 100, rx: 40, ry: 20, style: { fond: "#00ff00", opacite: 0.5 } },
      { id: "p", type: "path", d: "M200 150 C220 120 260 120 280 150", style: { fond: "none", contour: "#123456", epaisseur: 3, pointilles: "6 4", joint: "bevel" } },
      { id: "t", type: "path", d: "M10 150 L60 150 L60 190 L10 190 Z M20 160 L50 160 L50 180 L20 180 Z", style: { fond: "#333333", regle: "evenodd" } },
      { id: "g", type: "rect", x: 100, y: 160, w: 60, h: 20, style: { fond: "grad:g1" } },
    ] }] };
  for (const compresser of [true, false]) {
    const octets = await pdf_assembler([pdf_page(doc, { x: 0, y: 0, w: 300, h: 200 }, { dpi: 96 })], { compresser });
    const a = await pdf_vers_objets(octets);
    const n = compresser ? "compressé" : "brut";
    ok(`aller-retour (${n}) : taille de page = document`, pres(a.taille.w, 300) && pres(a.taille.h, 200), JSON.stringify(a.taille));
    ok(`aller-retour (${n}) : 5 chemins, 1 page`, a.objets.length === 5 && a.objets.every((o) => o.type === "path") && a.stats.pages === 1, JSON.stringify(a.objets.map((o) => o.type)));
    const [r, e, p, t, g] = a.objets;
    const br = boite(r);
    ok(`rect (${n}) : géométrie`, pres(br.x, 10) && pres(br.y, 20) && pres(br.w, 50) && pres(br.h, 30), JSON.stringify(br));
    ok(`rect (${n}) : fond, contour, épaisseur, jointure`, r.style.fond === "#ff0000" && r.style.contour === "#0000ff" && pres(r.style.epaisseur, 2) && r.style.joint === "miter", JSON.stringify(r.style));
    const be = boite(e);
    ok(`ellipse (${n}) : géométrie et opacité (ExtGState ca)`, pres(be.x, 110, 0.05) && pres(be.w, 80, 0.05) && pres(be.h, 40, 0.05) && e.style.fond === "#00ff00" && pres(e.style.opacite, 0.5) && e.style.contour === "none", JSON.stringify([be, e.style]));
    ok(`courbe (${n}) : cubique gardée, pointillés, jointure biseau, sans fond`, /C/.test(p.d) && p.style.fond === "none" && p.style.pointilles === "6 4" && p.style.joint === "bevel" && pres(p.style.epaisseur, 3), JSON.stringify(p));
    ok(`trou (${n}) : evenodd`, t.style.regle === "evenodd" && (t.d.match(/M/g) || []).length === 2);
    const bg = boite(g);
    ok(`dégradé (${n}) : la forme écrêtée, remplie de la 1re couleur, comptée`, pres(bg.x, 100) && pres(bg.w, 60) && g.style.fond === "#ff8800" && a.stats.ignores.degrade === 1, JSON.stringify([bg, g.style, a.stats]));
  }
  // un calque translucide devient un Form XObject (Do) : son contenu est lu
  const translucide = { ...doc, calques: [{ ...doc.calques[0], opacite: 0.5, objets: [doc.calques[0].objets[0]] }] };
  const a = await pdf_vers_objets(await pdf_assembler([pdf_page(translucide, { x: 0, y: 0, w: 300, h: 200 }, { dpi: 96 })]));
  ok("Form XObject (calque translucide) : contenu lu, opacité reportée", a.objets.length === 1 && pres(boite(a.objets[0]).x, 10) && pres(a.objets[0].style.opacite, 0.5), JSON.stringify(a.objets));
}

/* ── 2. PDF écrit à la main, table xref classique : opérateurs ── */
const CONTENU = [
  "q 2 0 0 2 10 10 cm 0 0 1 rg 0 0 10 10 re f Q",                 // carré bleu 20 pt en (10, 10)
  "1 0 0 RG 3 w [4 2] 0 d 1 j 50 50 m 100 50 l S",                 // trait rouge
  "0 1 1 0 k 0 1 1 0 K 0.5 w 20 60 m 40 60 l 40 80 l h B",          // CMJN → rouge, fermé, fond + contour
  "/GS1 gs 0.5 g 120 10 m 130 10 l 135 15 130 20 v 125 25 120 20 y h f*",         // gris, ca 0,5, v et y, evenodd
  "BT /F1 12 Tf 10 90 Td (Bonjour) Tj ET",                          // texte : compté
  "q /Im1 Do Q",                                                     // image : comptée
  "/Fm1 Do",                                                         // Form : lu, avec sa matrice
  "q 150 60 m 190 60 l 190 90 l W n /Sh1 sh Q",                      // dégradé dans un écrêtage
  "BI /W 2 /H 1 /CS /G /BPC 8 ID \x00\xff EI",                       // image en ligne : comptée, sautée
  "/Cs1 cs 0.2 0.4 0.6 scn 160 10 m 170 10 l 170 20 l f",            // espace nommé (ICCBased, N 3)
  "0 0 m 5 5 l W n",                                                 // découpe seule : rien de peint après
].join("\n");
const RESS = "<< /ExtGState << /GS1 << /ca 0.5 >> >> /XObject << /Im1 6 0 R /Fm1 7 0 R >> /Shading << /Sh1 << /ShadingType 2 /ColorSpace /DeviceRGB "
  + "/Coords [0 0 1 0] /Function << /FunctionType 3 /Domain [0 1] /Functions [<< /FunctionType 2 /Domain [0 1] /C0 [0 0.5 1] /C1 [1 1 1] /N 1 >>] /Bounds [] /Encode [0 1] >> >> >> "
  + "/ColorSpace << /Cs1 [/ICCBased 8 0 R] >> /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>";
const PAGE_CORPS = (contenus) => [
  "<< /Type /Catalog /Pages 2 0 R >>",
  "<< /Type /Pages /Kids [3 0 R 9 0 R] /Count 2 /MediaBox [0 0 200 100] >>",
  `<< /Type /Page /Parent 2 0 R /Resources 4 0 R /Contents ${contenus} >>`,
  RESS,
  ["", enc(CONTENU)],
  ["/Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceGray /BitsPerComponent 8", enc("\x80")],
  ["/Type /XObject /Subtype /Form /BBox [0 0 50 50] /Matrix [1 0 0 1 100 0]", enc("0 0 1 rg 0 30 m 10 30 l 10 40 l f")],
  ["/N 3", enc("icc")],
  "<< /Type /Page /Parent 2 0 R /Contents 10 0 R >>",
  ["", enc("0 0 m 1 1 l S")],
];
{
  const a = await pdf_vers_objets(classique(PAGE_CORPS("5 0 R"), "/Root 1 0 R"));
  const pt = (x, y) => [x * K, (100 - y) * K];
  ok("MediaBox héritée du nœud Pages, pt → px", pres(a.taille.w, 200 * K) && pres(a.taille.h, 100 * K), JSON.stringify(a.taille));
  ok("deux pages : la première seule, le nombre de pages est dit", a.stats.pages === 2);
  const [carre, trait, cmjn, gris, form, deg, iccb] = a.objets;
  ok("8 objets dessinés… (7 vus ici + rien d'autre)", a.objets.length === 7, JSON.stringify(a.objets.map((o) => o.style.fond + "/" + o.style.contour)));
  const bc = boite(carre), [x0, y0] = pt(10, 30);
  ok("cm + re : carré bleu, repère retourné", pres(bc.x, x0) && pres(bc.y, y0) && pres(bc.w, 20 * K) && pres(bc.h, 20 * K) && carre.style.fond === "#0000ff" && carre.style.contour === "none", JSON.stringify([bc, carre.style]));
  ok("trait : RG, w, d, j", trait.style.fond === "none" && trait.style.contour === "#ff0000" && pres(trait.style.epaisseur, 3 * K) && trait.style.pointilles === nbs([4 * K, 2 * K]) && trait.style.joint === "round", JSON.stringify(trait.style));
  ok("k / K : CMJN → RVB ; h ferme ; B = fond + contour", cmjn.style.fond === "#ff0000" && cmjn.style.contour === "#ff0000" && /Z$/.test(cmjn.d), JSON.stringify(cmjn));
  ok("gs (ca), g, v et y, f* → evenodd", gris.style.fond === "#808080" && pres(gris.style.opacite, 0.5) && gris.style.regle === "evenodd" && (gris.d.match(/C/g) || []).length === 2 && gris.d.includes("C173.3333 120 180 113.3333 173.3333 106.6667") && gris.d.includes("C166.6667 100 160 106.6667 160 106.6667"), JSON.stringify(gris));
  const bf = boite(form);
  ok("Form XObject : sa /Matrix appliquée", pres(bf.x, 100 * K) && pres(bf.y, (100 - 40) * K) && form.style.fond === "#0000ff", JSON.stringify(bf));
  ok("sh dans un écrêtage : la forme de l'écrêtage, couleur C0", pres(boite(deg).x, 150 * K) && deg.style.fond === "#0080ff", JSON.stringify(deg));
  ok("espace nommé ICCBased à 3 composantes", iccb.style.fond === "#336699", JSON.stringify(iccb.style));
  ok("comptés : textes, images (XObject + en ligne), dégradé ; aucune découpe inappliquée", a.stats.ignores.texte === 1 && a.stats.ignores.image === 2 && a.stats.ignores.decoupe === 0 && a.stats.ignores.degrade === 1, JSON.stringify(a.stats));
  ok("importés = objets dessinés", a.stats.importes === 7);
  // plusieurs flux de contenu, dans l'ordre
  const b = await pdf_vers_objets(classique(PAGE_CORPS("[5 0 R 10 0 R]"), "/Root 1 0 R"));
  ok("Contents en tableau : les flux s'enchaînent", b.objets.length === 8);
}

/* ── 3. PDF « moderne » : flux xref à prédicteur, flux d'objets compressé, contenu compressé ── */
{
  const corps = PAGE_CORPS("5 0 R").map((c) => (Array.isArray(c) ? [c[0] + " /Filter /FlateDecode", deflateSync(c[1])] : c));
  const a = await pdf_vers_objets(moderne(corps, [1, 2, 3, 4, 9], 1));
  ok("flux xref + ObjStm + Flate : même lecture", a.objets.length === 7 && a.stats.pages === 2 && a.objets[0].style.fond === "#0000ff", JSON.stringify(a.stats));
  // un startxref faux : la table est reconstruite en parcourant le fichier
  const casse = classique(PAGE_CORPS("5 0 R"), "/Root 1 0 R");
  const s = String.fromCharCode(...casse).replace(/startxref\n\d+/, "startxref\n999999");
  const c = await pdf_vers_objets(enc(s));
  ok("startxref faux : objets retrouvés par balayage", c.objets.length === 7);
  // /Rotate 90 : la page tourne, largeur et hauteur s'échangent
  const rot = PAGE_CORPS("5 0 R"); rot[2] = rot[2].replace("/Type /Page ", "/Type /Page /Rotate 90 ");
  const r = await pdf_vers_objets(classique(rot, "/Root 1 0 R"));
  const br = boite(r.objets[0]);
  ok("Rotate 90 : taille échangée, carré (10..30, 10..30) en x = y_pdf", pres(r.taille.w, 100 * K) && pres(r.taille.h, 200 * K) && pres(br.x, 10 * K) && pres(br.y, 10 * K), JSON.stringify([r.taille, br]));
}

/* ── 3 bis. cas ciblés, une page chacun ── */
const unePage = (contenu, ress = "", extra = []) => classique([
  "<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
  `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << ${ress} >> /Contents 4 0 R >>`, ["", enc(contenu)], ...extra], "/Root 1 0 R");
{
  const SH = "/Shading << /S << /ShadingType 2 /ColorSpace /DeviceRGB /Coords [0 0 1 0] /Function << /FunctionType 2 /C0 [1 0 0] /C1 [0 0 1] >> >> >>";
  let a = await pdf_vers_objets(unePage("0 0 m 10 0 l 10 10 l b"));
  ok("b : ferme le tracé, puis fond + contour", a.objets.length === 1 && /Z$/.test(a.objets[0].d) && a.objets[0].style.contour === "#000000", JSON.stringify(a.objets));
  a = await pdf_vers_objets(unePage("/S sh", SH));
  ok("sh sans écrêtage : rien de dessiné (toute la page), compté", a.objets.length === 0 && a.stats.ignores.degrade === 1);
  a = await pdf_vers_objets(unePage("/Pattern cs /P1 scn 0 0 10 10 re f", `/Pattern << /P1 << /PatternType 2 ${SH.replace("/Shading << /S ", "/Shading ").replace(/ >>$/, "")} >> >>`));
  ok("motif de type dégradé (PatternType 2) : 1re couleur, compté en dégradé", a.objets[0] && a.objets[0].style.fond === "#ff0000" && a.stats.ignores.degrade === 1 && a.stats.ignores.motif === 0, JSON.stringify([a.objets, a.stats]));
  a = await pdf_vers_objets(unePage("/Pattern cs /P1 scn 0 0 10 10 re f", "/Pattern << /P1 << /PatternType 1 >> >>"));
  ok("motif de pavage : gris, compté en motif", a.objets[0].style.fond === "#808080" && a.stats.ignores.motif === 1);
  a = await pdf_vers_objets(unePage("/G gs /F Do", "/ExtGState << /G << /ca 0.5 >> >> /XObject << /F 5 0 R >>",
    [["/Type /XObject /Subtype /Form /BBox [0 0 50 50] /Resources << /ExtGState << /G << /ca 0.5 >> >> >>", enc("/G gs 0 0 10 10 re f")]]));
  ok("opacités imbriquées : celle du Form multiplie celle de ses objets", a.objets.length === 1 && pres(a.objets[0].style.opacite, 0.25), JSON.stringify(a.objets));
  // découpe rectangulaire : un rectangle qui dépasse est rogné, une forme hors découpe disparaît, une forme contenue reste
  a = await pdf_vers_objets(unePage("q 0 0 50 50 re W n 20 20 60 60 re f 60 60 10 10 re f 5 5 10 10 re f 5 30 m 10 40 l 15 30 l f Q 70 70 10 10 re f"));
  const bx = a.objets.map(boite);
  ok("découpe rectangulaire appliquée (rogner, écarter, garder), non comptée", a.objets.length === 4 && pres(bx[0].w, 30 * K) && pres(bx[0].x, 20 * K) && pres(bx[0].y, 50 * K)
     && pres(bx[1].w, 10 * K) && pres(bx[3].x, 70 * K) && a.stats.ignores.decoupe === 0, JSON.stringify([bx, a.stats]));
  // deux découpes rectangulaires s'intersectent ; Q les retire
  a = await pdf_vers_objets(unePage("q 0 0 50 50 re W n q 30 30 50 50 re W n 0 0 100 100 re f Q 0 0 100 100 re f Q 0 0 100 100 re f"));
  const b2 = a.objets.map(boite);
  ok("découpes imbriquées : intersection, puis levées par Q", a.objets.length === 3 && pres(b2[0].w, 20 * K) && pres(b2[0].x, 30 * K) && pres(b2[1].w, 50 * K) && pres(b2[2].w, 100 * K), JSON.stringify(b2));
  // découpe non rectangulaire (triangle) : le remplissage est intersecté (booléens) ; dedans, les courbes restent
  a = await pdf_vers_objets(unePage("q 0 0 m 40 0 l 0 40 l h W n 0 0 40 40 re f 2 2 m 6 2 l 6 6 2 6 v h f 60 60 10 10 re f Q"));
  ok("découpe triangulaire : le carré devient le triangle, la forme dedans garde sa courbe, la forme dehors disparaît",
     a.objets.length === 2 && pres(aire(a.objets[0]), 800 * K * K, 1) && /C/.test(a.objets[1].d) && a.stats.ignores.decoupe === 0, JSON.stringify([a.objets.map((o) => o.d), a.stats]));
  // découpe en anneau (W*) : Chrome dessine ainsi les bordures arrondies
  a = await pdf_vers_objets(unePage("q 0 0 m 50 0 l 50 50 l 0 50 l h 10 10 m 40 10 l 40 40 l 10 40 l h W* n 0 0 100 100 re f Q"));
  ok("découpe en anneau (evenodd) : il ne reste que l'anneau", a.objets.length === 1 && pres(aire(a.objets[0]), (2500 - 900) * K * K, 1), JSON.stringify(a.objets));
  // un trait coupé par une découpe : gardé entier, compté ; un trait hors découpe : écarté
  a = await pdf_vers_objets(unePage("q 0 0 m 40 0 l 0 40 l h W n 5 5 m 60 5 l S 80 80 m 90 90 l S Q"));
  ok("trait coupé par une découpe : gardé, compté ; trait dehors : écarté", a.objets.length === 1 && a.stats.ignores.decoupe === 1, JSON.stringify(a.stats));
  // sh dans deux découpes : la dernière, dans la précédente
  a = await pdf_vers_objets(unePage("q 0 0 50 50 re W n 25 0 50 50 re W n /S sh Q", SH));
  ok("sh dans deux découpes : leur intersection", a.objets.length === 1 && pres(boite(a.objets[0]).w, 25 * K) && a.objets[0].style.fond === "#ff0000", JSON.stringify(a.objets));
  a = await pdf_vers_objets(unePage("0 0 m 6 6 v 10 l 1 2 3 c 0 0 10 10 re f"));
  ok("opérateurs incomplets ignorés (aucun NaN)", a.objets.length === 1 && !/NaN/.test(a.objets[0].d) && /^M0 133/.test(a.objets[0].d), JSON.stringify(a.objets));
  // découpes : cas limites
  a = await pdf_vers_objets(unePage("q 0 0 20 100 re W n 0 0 m 40 0 l 0 40 l h W n 0 0 40 40 re f Q"));
  ok("rectangle + triangle : le remplissage est dans les deux", a.objets.length === 1 && pres(aire(a.objets[0]), 600 * K * K, 1), JSON.stringify(a.objets));
  a = await pdf_vers_objets(unePage("q 0 0 m 40 0 l 0 40 l h W n 30 30 8 8 re f Q"));
  ok("dans la boîte du triangle mais hors du triangle : écarté", a.objets.length === 0, JSON.stringify(a.objets));
  a = await pdf_vers_objets(unePage("q 20 0 m 40 20 l 20 40 l 0 20 l h W n 0 0 40 40 re f Q"));
  ok("un losange n'est pas un rectangle", a.objets.length === 1 && pres(aire(a.objets[0]), 800 * K * K, 1), JSON.stringify(a.objets));
  a = await pdf_vers_objets(unePage("q 0 0 10 10 re W n 20 20 10 10 re W n 0 0 100 100 re f Q"));
  ok("deux découpes disjointes : rien de visible", a.objets.length === 0, JSON.stringify(a.objets));
  a = await pdf_vers_objets(unePage("9 0 0 m 10 0 l 10 10 l f"));
  ok("opérandes en trop : seuls les derniers comptent", a.objets.length === 1 && /^M0 133/.test(a.objets[0].d), JSON.stringify(a.objets));
  // sans les booléens (martinez absent) : les découpes RECTANGULAIRES s'appliquent quand même, exactement
  fournirMartinez(null);
  a = await pdf_vers_objets(unePage("q 0 0 50 50 re W n 20 20 60 60 re f 5 5 m 15 5 l 15 15 10 20 5 15 c h f Q"));
  ok("sans booléens : rectangle rogné, courbe dedans gardée, rien de compté", a.objets.length === 2 && pres(boite(a.objets[0]).w, 30 * K) && /C/.test(a.objets[1].d) && a.stats.ignores.decoupe === 0, JSON.stringify([a.objets, a.stats]));
  a = await pdf_vers_objets(unePage("q 0 0 m 40 0 l 0 40 l h W n 0 0 40 40 re f Q"));
  ok("sans booléens : découpe non rectangulaire non appliquée, comptée", a.objets.length === 1 && pres(boite(a.objets[0]).w, 40 * K) && pres(boite(a.objets[0]).h, 40 * K) && a.stats.ignores.decoupe === 1, JSON.stringify(a.stats));
  fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
  a = await pdf_vers_objets(unePage("q 0 0 10 10 re W n 20 20 10 10 re W n /S sh Q", SH));
  ok("sh dans deux découpes disjointes : rien", a.objets.length === 0 && a.stats.ignores.degrade === 1);
  // du bruit AVANT l'en-tête (plus d'1 Ko) : le PDF reste lisible
  const bruit = concat(enc("x".repeat(2000) + "\n"), unePage("0 0 10 10 re f"));
  a = await pdf_vers_objets(bruit);
  ok("octets avant %PDF : objets retrouvés", a.objets.length === 1);
}
/* ── 3 ter. mise à jour incrémentale par flux xref : l'objet le plus récent l'emporte ── */
{
  const corps = PAGE_CORPS("5 0 R").map((c) => (Array.isArray(c) ? [c[0] + " /Filter /FlateDecode", deflateSync(c[1])] : c));
  const v1 = moderne(corps, [1, 2, 3, 4, 9], 1);
  const prev = +String.fromCharCode(...v1.slice(-40)).match(/startxref\n(\d+)/)[1];
  const neuf = enc("5 0 obj\n<< /Length 18 >>\nstream\n0 0 1 1 re f\n     \nendstream\nendobj\n");
  const pos5 = v1.length, posX = v1.length + neuf.length;
  const ligne = (t, o) => [t, (o >>> 24) & 255, (o >>> 16) & 255, (o >>> 8) & 255, o & 255, 0, 0];
  const lignes = [ligne(1, pos5), ligne(1, posX)];
  const xs = deflateSync(Uint8Array.from(lignes.flat()));
  const maj = concat(v1, neuf, enc(`13 0 obj\n<< /Type /XRef /Size 14 /W [1 4 2] /Index [5 1 13 1] /Prev ${prev} /Root 1 0 R /Filter /FlateDecode /Length ${xs.length} >>\nstream\n`),
    xs, enc(`\nendstream\nendobj\nstartxref\n${posX}\n%%EOF\n`));
  const a = await pdf_vers_objets(maj);
  ok("mise à jour incrémentale : le nouveau contenu (1 carré) remplace l'ancien", a.objets.length === 1 && pres(boite(a.objets[0]).w, K), JSON.stringify(a.stats));
}

/* ── 4. refus ── */
{
  ok("pas un PDF → refus traduit", await refus(pdf_vers_objets(enc("bonjour"))) === T("vectorlab.importer.pdf_invalide"));
  ok("vide → refus traduit", await refus(pdf_vers_objets(new Uint8Array(0))) === T("vectorlab.importer.pdf_invalide"));
  ok("chiffré → refus traduit", await refus(pdf_vers_objets(classique(PAGE_CORPS("5 0 R"), "/Root 1 0 R /Encrypt << /Filter /Standard >>"))) === T("vectorlab.importer.pdf_chiffre"));
  const sansPage = classique(["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [] /Count 0 >>"], "/Root 1 0 R");
  ok("aucune page → refus traduit", await refus(pdf_vers_objets(sansPage)) === T("vectorlab.importer.pdf_invalide"));
  const lzw = PAGE_CORPS("5 0 R"); lzw[4] = ["/Filter /LZWDecode", enc("x")];
  ok("filtre non pris en charge → refus qui le nomme", await refus(pdf_vers_objets(classique(lzw, "/Root 1 0 R"))) === T("vectorlab.importer.pdf_filtre", { filtre: "LZWDecode" }));
}

function nbs(v) { return v.map((x) => String(Math.round(x * 1e4) / 1e4)).join(" "); }

if (echecs.length) {
  console.error(`importpdf : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("importpdf : ok");
