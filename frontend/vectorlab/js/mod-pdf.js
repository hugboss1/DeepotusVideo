// mod-pdf.js — t121 : le PDF VECTORIEL du Vectorlab, écrit depuis le MODÈLE du document (pas depuis le SVG).
//
// POURQUOI LE MODÈLE. La spec (D7) interdit un interpréteur SVG serveur et toute dépendance : le PDF du lot G
// était donc une image JPEG par page. Ici, un module PUR (bancable sous node) lit les objets du document —
// chemins, formes, rects, ellipses, tuiles, textes (en contours, glyphes fournis par l'écran), groupes, symboles —
// et écrit les opérateurs PDF : un vrai PDF vectoriel, sans bibliothèque.
//
// LE REPLI, DIT. Ce qu'un PDF simple ne porte pas (effets SVG, masques, images, cadres et textes sur chemin,
// dégradés et motifs jusqu'à leur traduction) n'est pas avalé : l'objet de PREMIER NIVEAU qui en contient est
// listé dans `rasters`, avec sa raison. L'écran le rend seul, avec son alpha, et l'assembleur le pose en image
// (SMask) À SA PLACE dans l'ordre de peinture. Les stats le comptent, l'écran le dit.
//
// GROUPES DE TRANSPARENCE. L'opacité SVG d'un élément ou d'un calque s'applique au RÉSULTAT composé : multiplier
// l'alpha objet par objet assombrirait les recouvrements (deux objets d'un calque à 0,4 qui se chevauchent). Un
// calque ou un groupe translucide, ou un objet translucide qui a fond ET contour, devient donc un Form XObject
// dessiné sous un ExtGState `ca`/`CA` ; un objet translucide à une seule peinture garde un simple `ca`.
//
// REPÈRE. Le document est en px, y vers le bas ; la page en points, y vers le haut. Une seule matrice de base
// `k 0 0 -k −x·k (y+h)·k` (k = 72 / dpi du document) : tout le reste s'écrit en coordonnées du document.
import { T } from "./mod-i18n.js";
import { chemin_parser, terrains_de, grille_tuiles, terrain_motif_spec } from "./mod-doc.js";
import { forme_d } from "./mod-formes.js";
import { hex_centre, hex_d } from "./mod-grille.js";

/* ── nombres ── */
export function nb(x) {
  return String(Math.round(+x * 1000) / 1000);       // String(-0) vaut déjà "0"
}

/* ── matrices [a b c d e f] (convention SVG/PDF : x' = a·x + c·y + e, y' = b·x + d·y + f) ── */
const ID = [1, 0, 0, 1, 0, 0];
export function matrice_mul(m, n) {        // m · n : n s'applique d'abord
  return [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
          m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
          m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]];
}
const ARGS = { matrix: [6], translate: [1, 2], scale: [1, 2], rotate: [1, 3], skewX: [1], skewY: [1] };
export function matrice_de(t) {
  const src = String(t || "").trim();
  if (!src) return ID.slice();
  let m = ID.slice(), reste = src;
  const re = /^\s*(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)\s*,?/;
  while (reste.trim()) {
    const x = re.exec(reste);
    if (!x) throw new Error(T("vectorlab.pdf.transform_illisible", { src }));
    const a = x[2].trim().split(/[\s,]+/).filter(Boolean).map(Number);
    if (!ARGS[x[1]].includes(a.length) || a.some((v) => !Number.isFinite(v))) throw new Error(`transform : ${x[1]}(${x[2]})`);
    const rad = (d) => d * Math.PI / 180;
    let n;
    switch (x[1]) {
      case "matrix": n = a; break;
      case "translate": n = [1, 0, 0, 1, a[0], a[1] || 0]; break;
      case "scale": n = [a[0], 0, 0, a.length > 1 ? a[1] : a[0], 0, 0]; break;
      case "rotate": {
        const c = Math.cos(rad(a[0])), s = Math.sin(rad(a[0]));
        n = [c, s, -s, c, 0, 0];
        if (a.length === 3) n = matrice_mul(matrice_mul([1, 0, 0, 1, a[1], a[2]], n), [1, 0, 0, 1, -a[1], -a[2]]);
        break;
      }
      case "skewX": n = [1, 0, Math.tan(rad(a[0])), 1, 0, 0]; break;
      case "skewY": n = [1, Math.tan(rad(a[0])), 0, 1, 0, 0]; break;
    }
    m = matrice_mul(m, n);
    reste = reste.slice(x[0].length);
  }
  return m;
}
const _cm = (m) => `${m.map(nb).join(" ")} cm`;
const _estId = (m) => m.every((v, i) => Math.abs(v - ID[i]) < 1e-12);

/* ── chemins : le d canonique (M L C Q Z absolus) → opérateurs PDF ; Q devient une cubique EXACTE ── */
export function chemin_ops(d) {
  const out = [];
  let px = 0, py = 0, sx = 0, sy = 0;
  for (const s of chemin_parser(d)) {
    const p = s.p;
    switch (s.c) {
      case "M": out.push(`${nb(p[0])} ${nb(p[1])} m`); px = sx = p[0]; py = sy = p[1]; break;
      case "L": out.push(`${nb(p[0])} ${nb(p[1])} l`); px = p[0]; py = p[1]; break;
      case "C": out.push(`${p.map(nb).join(" ")} c`); px = p[4]; py = p[5]; break;
      case "Q": {
        const [qx, qy, x, y] = p;
        out.push([px + 2 / 3 * (qx - px), py + 2 / 3 * (qy - py), x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y), x, y].map(nb).join(" ") + " c");
        px = x; py = y; break;
      }
      case "Z": out.push("h"); px = sx; py = sy; break;
    }
  }
  return out.join(" ");
}

/* ── couleurs : #RGB, #RGBA, #RRGGBB, #RRGGBBAA, glob:<nom> → [r g b a] en 0..1, ou null ── */
export function couleur_rgba(v, globales = {}) {
  if (typeof v === "string" && v.startsWith("glob:")) return globales[v.slice(5)] ? couleur_rgba(globales[v.slice(5)]) : null;
  if (v === undefined || v === null || v === "none") return null;
  const m = /^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.exec(String(v));
  if (!m) return undefined;                 // couleur que le PDF ne sait pas lire : l'appelant rasterise
  let h = m[1];
  if (h.length <= 4) h = [...h].map((c) => c + c).join("");
  const c = [0, 2, 4, 6].map((i) => (i < h.length ? parseInt(h.slice(i, i + 2), 16) : 255) / 255);
  return c;
}
const _rgb = (c) => `${nb(c[0])} ${nb(c[1])} ${nb(c[2])}`;

/* ── géométrie d'un objet simple → opérateurs de chemin (repère de l'objet) ── */
const K = 0.5522847498307936;               // 4/3 (√2 − 1) : la cubique qui approche un quart de cercle
function _ellipse(cx, cy, rx, ry) {
  const kx = rx * K, ky = ry * K;
  return [`${nb(cx)} ${nb(cy - ry)} m`,
    `${nb(cx + kx)} ${nb(cy - ry)} ${nb(cx + rx)} ${nb(cy - ky)} ${nb(cx + rx)} ${nb(cy)} c`,
    `${nb(cx + rx)} ${nb(cy + ky)} ${nb(cx + kx)} ${nb(cy + ry)} ${nb(cx)} ${nb(cy + ry)} c`,
    `${nb(cx - kx)} ${nb(cy + ry)} ${nb(cx - rx)} ${nb(cy + ky)} ${nb(cx - rx)} ${nb(cy)} c`,
    `${nb(cx - rx)} ${nb(cy - ky)} ${nb(cx - kx)} ${nb(cy - ry)} ${nb(cx)} ${nb(cy - ry)} c`, "h"].join(" ");
}
function _rect(x, y, w, h, rx) {
  const r = Math.min(+rx || 0, w / 2, h / 2);
  if (!(r > 0)) return `${nb(x)} ${nb(y)} m ${nb(x + w)} ${nb(y)} l ${nb(x + w)} ${nb(y + h)} l ${nb(x)} ${nb(y + h)} l h`;
  const k = r * K;
  return [`${nb(x + r)} ${nb(y)} m`, `${nb(x + w - r)} ${nb(y)} l`,
    `${nb(x + w - r + k)} ${nb(y)} ${nb(x + w)} ${nb(y + r - k)} ${nb(x + w)} ${nb(y + r)} c`, `${nb(x + w)} ${nb(y + h - r)} l`,
    `${nb(x + w)} ${nb(y + h - r + k)} ${nb(x + w - r + k)} ${nb(y + h)} ${nb(x + w - r)} ${nb(y + h)} c`, `${nb(x + r)} ${nb(y + h)} l`,
    `${nb(x + r - k)} ${nb(y + h)} ${nb(x)} ${nb(y + h - r + k)} ${nb(x)} ${nb(y + h - r)} c`, `${nb(x)} ${nb(y + r)} l`,
    `${nb(x)} ${nb(y + r - k)} ${nb(x + r - k)} ${nb(y)} ${nb(x + r)} ${nb(y)} c`, "h"].join(" ");
}

/* ── la raison de rasteriser un objet (null = vectoriel) ── */
const _A_RASTER = { image: "image", cadre: T("vectorlab.pdf.raison_cadre"), textechemin: T("vectorlab.pdf.raison_textechemin") };
// le FOND : couleur, dégradé (shading), motif (pavage) — ou ce qu'un shading ne porte pas
function _raisonFond(v, ctx) {
  if (v === undefined || v === "none") return null;
  if (typeof v === "string" && v.startsWith("grad:")) {
    const g = (ctx.doc.degrades || {})[v.slice(5)];
    if (!g) return null;                                  // dégradé orphelin : none, comme le SVG
    if (g.type === "conique") return T("vectorlab.pdf.degrade_conique");
    for (const st of g.stops || []) {
      const c = couleur_rgba(st.couleur, ctx.globales);
      if (!c) return T("vectorlab.pdf.degrade_arret", { c: st.couleur });
      // un shading PDF interpole des couleurs, pas une transparence : un arrêt translucide se rasterise
      if (c[3] < 1 || (st.opacite !== undefined && +st.opacite < 1)) return T("vectorlab.pdf.degrade_translucide");
    }
    return null;
  }
  if (typeof v === "string" && v.startsWith("motif:")) return null;   // existant → pavage ; orphelin → none
  return couleur_rgba(v, ctx.globales) === undefined ? T("vectorlab.pdf.couleur", { v }) : null;
}
// le CONTOUR : une couleur seulement ; un dégradé ou un motif de trait n'a pas d'équivalent simple
function _raisonContour(v, ctx) {
  if (typeof v === "string" && v.startsWith("grad:")) return (ctx.doc.degrades || {})[v.slice(5)] ? T("vectorlab.pdf.degrade_contour") : null;
  if (typeof v === "string" && v.startsWith("motif:")) return (ctx.doc.motifs || {})[v.slice(6)] ? T("vectorlab.pdf.motif_contour") : null;
  return v === undefined || v === "none" || couleur_rgba(v, ctx.globales) !== undefined ? null : T("vectorlab.pdf.couleur", { v });
}
function _raison(o, ctx) {
  const s = o.style || {};
  if (_A_RASTER[o.type]) return _A_RASTER[o.type];
  if (s.effets && s.effets.length) return T("vectorlab.pdf.effet");
  if (s.masque) return T("vectorlab.pdf.masque");
  const r = _raisonFond(s.fond, ctx) || _raisonContour(s.contour, ctx)
    || (s.contours || []).map((c) => _raisonContour(c.couleur, ctx)).find(Boolean);
  if (r) return r;
  if (o.type === "texte") {
    // les glyphes viennent de l'écran (opentype) ; il peut refuser en disant pourquoi ({raison})
    const g = ctx.glyphes && ctx.glyphes(o);
    if (!g) return T("vectorlab.pdf.raison_police");
    if (g.raison) return g.raison;
  }
  if (o.type === "groupe") for (const e of o.enfants || []) { const x = _raison(e, ctx); if (x) return x; }
  if (o.type === "instance") {
    const sym = (ctx.doc.symboles || {})[o.symbole];
    if (sym) for (const e of sym.objets || []) { const x = _raison(e, ctx); if (x) return x; }
  }
  return null;
}

/* ── ExtGState : un nom par combinaison (ca, CA, BM) ── */
const BM = { normal: "Normal", multiply: "Multiply", screen: "Screen", overlay: "Overlay", darken: "Darken",
  lighten: "Lighten", "color-dodge": "ColorDodge", "color-burn": "ColorBurn", "hard-light": "HardLight",
  "soft-light": "SoftLight", difference: "Difference", exclusion: "Exclusion", hue: "Hue", saturation: "Saturation",
  color: "Color", luminosity: "Luminosity" };
function _gs(ctx, { ca = 1, CA = 1, fusion } = {}) {
  const bm = fusion && fusion !== "normal" ? BM[fusion] : undefined;
  if (ca === 1 && CA === 1 && !bm) return "";
  const cle = `${ca}|${CA}|${bm || ""}`;
  if (!ctx.gsCles.has(cle)) {
    const nom = `G${ctx.gsCles.size + 1}`;
    ctx.gsCles.set(cle, nom);
    ctx.gs[nom] = { ca, CA, ...(bm ? { BM: bm } : {}) };
  }
  return `/${ctx.gsCles.get(cle)} gs`;
}
function _forme(ctx, contenu) {
  const nom = `F${Object.keys(ctx.formes).length + 1}`;
  ctx.formes[nom] = contenu;
  return nom;
}

/* ── matrices : l'inverse (l'espace par défaut d'un Form → celui de la page) ── */
export function matrice_inverse(m) {
  const det = m[0] * m[3] - m[1] * m[2];
  if (!det) throw new Error(T("vectorlab.pdf.matrice"));
  return [m[3] / det, -m[1] / det, -m[2] / det, m[0] / det, (m[2] * m[5] - m[3] * m[4]) / det, (m[1] * m[4] - m[0] * m[5]) / det];
}

/* ── dégradés : un SHADING (type 2 linéaire, 3 radial), fonction de couture entre les arrêts. Les arrêts
   bornent comme en SVG : avant le premier, sa couleur TIENT ; après le dernier, aussi. Les coordonnées sont
   celles de l'objet (userSpaceOnUse) : `sh` peint dans le repère courant, rien à recalculer. ── */
function _fonction(stops, ctx) {
  const pts = stops.slice().sort((a, b) => a.t - b.t)
    .map((s) => ({ t: Math.min(1, Math.max(0, +s.t)), c: couleur_rgba(s.couleur, ctx.globales) }));
  if (pts[0].t > 0) pts.unshift({ t: 0, c: pts[0].c });
  if (pts[pts.length - 1].t < 1) pts.push({ t: 1, c: pts[pts.length - 1].c });
  const f2 = (a, b) => `<< /FunctionType 2 /Domain [0 1] /C0 [${_rgb(a)}] /C1 [${_rgb(b)}] /N 1 >>`;
  if (pts.length === 2) return f2(pts[0].c, pts[1].c);
  const fs = [], bornes = [], enc = [];
  for (let i = 0; i + 1 < pts.length; i++) {
    fs.push(f2(pts[i].c, pts[i + 1].c)); enc.push("0 1");
    if (i + 1 < pts.length - 1) bornes.push(nb(pts[i + 1].t));
  }
  return `<< /FunctionType 3 /Domain [0 1] /Functions [${fs.join(" ")}] /Bounds [${bornes.join(" ")}] /Encode [${enc.join(" ")}] >>`;
}
function _shading(ctx, g) {
  const cle = JSON.stringify(g);
  if (!ctx.shCles.has(cle)) {
    const nom = `Sh${ctx.shCles.size + 1}`;
    ctx.shCles.set(cle, nom);
    const coords = g.type === "radial" ? [g.cx, g.cy, 0, g.cx, g.cy, g.r] : [g.x1, g.y1, g.x2, g.y2];
    ctx.shadings[nom] = `<< /ShadingType ${g.type === "radial" ? 3 : 2} /ColorSpace /DeviceRGB /Coords [${coords.map(nb).join(" ")}] `
      + `/Function ${_fonction(g.stops || [], ctx)} /Extend [true true] >>`;
  }
  return ctx.shCles.get(cle);
}

/* ── motifs (lot F, et ceux des terrains — t122) : un motif de PAVAGE PDF (PatternType 1). Sa matrice va de
   l'espace du motif vers l'espace PAR DÉFAUT de là où il est peint — la page, ou le Form d'un groupe de
   transparence (PDF 1.7 §8.7.3.1) : inverse(espace) · CTM courante · rotate(angle). Un motif par (spec, matrice). ── */
const MOTIF_DEFAUT = { pas: 8, angle: 45, epaisseur: 1, couleur: "#1F1512" };   // celui de motif_svg (mod-effets)
function _motif(ctx, spec) {
  const m = { ...MOTIF_DEFAUT, ...spec };
  const p = +m.pas, e = +m.epaisseur;
  const rot = +m.angle ? matrice_de(`rotate(${+m.angle})`) : ID;
  const mat = matrice_mul(matrice_inverse(ctx.espace), matrice_mul(ctx.ctm, rot));
  const cle = JSON.stringify([m, mat.map(nb)]);
  if (!ctx.patCles.has(cle)) {
    const nom = `P${ctx.patCles.size + 1}`;
    ctx.patCles.set(cle, nom);
    const c = couleur_rgba(m.couleur, ctx.globales) || [0, 0, 0, 1];
    const f = m.fond && m.fond !== "none" ? couleur_rgba(m.fond, ctx.globales) : null;
    const L = [];
    if (f) L.push(`${_rgb(f)} rg\n${_rect(0, 0, p, p)}\nf`);
    const trait = `${_rgb(c)} RG\n${nb(e)} w\n0 J`;          // <line> SVG : bouts carrés coupés (butt)
    switch (m.type) {
      case "hachures": L.push(`${trait}\n0 ${nb(p / 2)} m ${nb(p)} ${nb(p / 2)} l\nS`); break;
      case "points": L.push(`${_rgb(c)} rg\n${_ellipse(p / 2, p / 2, Math.max(0.2, e), Math.max(0.2, e))}\nf`); break;
      case "damier": L.push(`${_rgb(c)} rg\n${_rect(0, 0, p / 2, p / 2)}\nf\n${_rect(p / 2, p / 2, p / 2, p / 2)}\nf`); break;
      case "grille": L.push(`${trait}\n0 0 m ${nb(p)} 0 l\nS\n0 0 m 0 ${nb(p)} l\nS`); break;
    }
    ctx.patterns[nom] = { contenu: L.join("\n"), bbox: [0, 0, p, p], pas: p, matrice: mat };
  }
  return ctx.patCles.get(cle);
}

/* ── le fond d'un objet, résolu : {couleur} | {degrade} | {motif} | null ── */
function _fondDe(v, ctx) {
  if (v && typeof v === "object" && v.__motif) return { type: "motif", spec: v.__motif };
  if (v === undefined || v === "none") return null;
  if (typeof v === "string" && v.startsWith("grad:")) {
    const g = (ctx.doc.degrades || {})[v.slice(5)];
    return g ? { type: "degrade", g } : null;
  }
  if (typeof v === "string" && v.startsWith("motif:")) {
    const m = (ctx.doc.motifs || {})[v.slice(6)];
    return m ? { type: "motif", spec: m } : null;
  }
  const c = couleur_rgba(v, ctx.globales);
  return c ? { type: "couleur", c } : null;
}
const _peintureDe = (v, ctx) => !!_fondDe(v, ctx);

/* ── peinture d'un chemin : réglages de trait, fond (couleur, shading, pavage), opérateur ── */
const JOINT = { miter: 0, round: 1, bevel: 2 };
function _peindre(chemin, s, ctx, { sansOpacite = false } = {}) {
  const F = _fondDe(s.fond, ctx), contour = couleur_rgba(s.contour, ctx.globales) || null;
  if (!F && !contour) return "";
  const op = sansOpacite ? 1 : Number(s.opacite === undefined ? 1 : s.opacite);
  const L = [];
  const g = _gs(ctx, { ca: (F && F.type === "couleur" ? F.c[3] : 1) * op, CA: (contour ? contour[3] : 1) * op });
  if (g) L.push(g);
  const eo = s.regle === "evenodd" ? "*" : "";
  const trait = () => {
    const tirets = String(s.pointilles || "").trim().split(/[\s,]+/).filter(Boolean).map(Number);
    return [`${_rgb(contour)} RG`, `${nb(Number(s.epaisseur || 1))} w`, `${JOINT[s.joint || "round"] ?? 1} j`, "1 J",
      tirets.length && tirets.every((v) => v >= 0) ? `[${tirets.map(nb).join(" ")}] 0 d` : "[] 0 d"];
  };
  if (F && F.type === "degrade") {
    // le dégradé remplit le chemin par écrêtage ; le contour, s'il y en a un, se trace PAR-DESSUS
    L.push(`q\n${chemin}\nW${eo} n\n/${_shading(ctx, F.g)} sh\nQ`);
    if (contour) L.push(...trait(), chemin, "S");
  } else {
    if (F && F.type === "couleur") L.push(`${_rgb(F.c)} rg`);
    if (F && F.type === "motif") L.push(`/Pattern cs /${_motif(ctx, F.spec)} scn`);
    if (contour) L.push(...trait());
    L.push(chemin, F && contour ? `B${eo}` : F ? `f${eo}` : "S");
  }
  // un ExtGState posé ici ne doit pas FUIR sur les objets suivants : q … Q autour
  return g ? `q\n${L.join("\n")}\nQ` : L.join("\n");
}

/* ── le chemin (repère de l'objet) d'un objet géométrique, ou null ── */
function _chemin(o, ctx) {
  switch (o.type) {
    case "rect": return _rect(+o.x, +o.y, +o.w, +o.h, o.rx);
    case "ellipse": return _ellipse(+o.cx, +o.cy, +o.rx, +o.ry);
    case "path": return chemin_ops(o.d);
    case "forme": return chemin_ops(forme_d(o));
    case "tuile": {
      const g = ctx.grille, [cx, cy] = hex_centre(o.q, o.r, g);
      return chemin_ops(hex_d(cx, cy, g.pas, g.orientation, g.echelle));
    }
    default: return null;
  }
}

/* ── un objet vectoriel → son flux (sans le q/Q de son transform) ── */
function _corps(o, ctx) {
  const s0 = o.style || {};
  if (o.type === "groupe") {
    const L = [];
    if (o.clip) {
      const c = (o.enfants || []).find((e) => e.id === o.clip);
      const ch = c && _chemin(c, ctx);
      if (ch) L.push(c.transform ? `q\n${_cm(matrice_de(c.transform))}\n${ch}\nW n\nQ` : `${ch}\nW n`);
    }
    for (const e of o.enfants || []) { const x = _objet(e, ctx); if (x) L.push(x); }
    return L.join("\n");
  }
  if (o.type === "instance") {
    // t123 : l'instance en cours d'édition en place est masquée — son calque d'édition la montre déjà
    if (ctx.doc.edition && ctx.doc.edition.instance === o.id) return "";
    const sym = (ctx.doc.symboles || {})[o.symbole];
    return sym ? (sym.objets || []).map((e) => _objet(e, ctx)).filter(Boolean).join("\n") : "";
  }
  if (o.type === "texte") {
    const gl = ctx.glyphes(o) || [];
    const s = { ...s0 };
    if (!s.fond || s.fond === "none") s.fond = s.contour || "#1F1512";
    return gl.map((g) => _peindre(chemin_ops(g.d), { ...s, regle: "evenodd" }, ctx)).filter(Boolean).join("\n");
  }
  let s = s0;
  if (o.type === "tuile") {
    // la tuile : la couleur de son terrain, ou son MOTIF (t122, même spécification que le SVG) ; un fond
    // surchargé sur la tuile l'emporte (…s0)
    const f = ctx.terrains[o.terrain];
    const fond = !f ? "#888888" : f.motif ? { __motif: terrain_motif_spec(f, ctx.grille.pas) } : f.couleur;
    s = { fond, contour: "#1F1512", epaisseur: 1, ...s0 };
  }
  const ch = _chemin(o, ctx);
  if (!ch) return "";
  const L = [];
  // contours multiples (lot F) : dessous, du plus épais au plus fin, chacun avec SA propre opacité
  for (const c of (s.contours || []).slice().sort((a, b) => b.epaisseur - a.epaisseur)) {
    L.push(_peindre(ch, { contour: c.couleur, epaisseur: c.epaisseur, pointilles: c.pointilles, opacite: c.opacite, joint: s.joint }, ctx));
  }
  L.push(_peindre(ch, { ...s, contours: undefined }, ctx, { sansOpacite: ctx.sansOpacite }));
  return L.filter(Boolean).join("\n");
}

/* ── un objet vectoriel complet : transform, opacité de groupe, fusion ── */
function _objet(o, ctx) {
  const s = o.style || {};
  const op = Number(s.opacite === undefined ? 1 : s.opacite);
  const peint = o.type === "groupe" || o.type === "instance" || (s.contours && s.contours.length)
    || (_peintureDe(s.fond, ctx) && couleur_rgba(s.contour, ctx.globales));
  let m = matrice_de(o.transform);
  if (o.type === "instance") m = matrice_mul(m, [o.sx === undefined ? 1 : +o.sx, 0, 0, o.sy === undefined ? 1 : +o.sy, +o.x, +o.y]);
  // la CTM suivie à la main : la matrice d'un motif en dépend
  const enf = { ...ctx, ctm: matrice_mul(ctx.ctm, m) };
  let corps, etat = false;                // etat : le corps pose un gs ou un écrêtage → q … Q obligatoire
  if (op !== 1 && peint) {
    // groupe de transparence : le corps sans son opacité, dessiné d'un bloc sous ca/CA ; son espace par
    // défaut est la CTM au moment du Do
    const interieur = _corps(o, { ...enf, espace: enf.ctm, sansOpacite: true });
    if (!interieur.trim()) return "";
    corps = `${_gs(ctx, { ca: op, CA: op, fusion: s.fusion })}\n/${_forme(ctx, interieur)} Do`;
    etat = true;
  } else {
    const fu = _gs(ctx, { fusion: s.fusion });
    const interieur = _corps(o, enf);
    if (!interieur.trim()) return "";
    corps = (fu ? fu + "\n" : "") + interieur;
    etat = !!fu || (o.type === "groupe" && !!o.clip);
  }
  if (_estId(m) && !etat) return corps;
  return `q\n${_estId(m) ? "" : _cm(m) + "\n"}${corps}\nQ`;
}

/* ── LA PAGE : une tranche (cadre en px du document) → flux + ressources + rasters à fournir ── */
export function pdf_page(doc, cadre, opts = {}) {
  const dpi = +opts.dpi || 300, k = 72 / dpi;
  const base = [k, 0, 0, -k, -cadre.x * k, (cadre.y + cadre.h) * k];
  const ctx = { doc, globales: doc.couleursGlobales || {}, terrains: terrains_de(doc), grille: grille_tuiles(doc),
    glyphes: opts.glyphes || (() => null), gs: {}, gsCles: new Map(), formes: {}, rasters: [],
    shadings: {}, shCles: new Map(), patterns: {}, patCles: new Map(),
    ctm: base, espace: ID, stats: { vectoriels: 0, rasterises: 0 } };
  const L = [_cm(base)];
  if (doc.fond && !opts.transparent) {
    const c = couleur_rgba(doc.fond, ctx.globales);
    if (c) L.push(`${_rgb(c)} rg\n${_rect(0, 0, +doc.taille.w, +doc.taille.h)}\nf`);
  }
  for (const c of doc.calques) {
    if (c.visible === false) continue;
    const op = c.opacite === undefined ? 1 : Number(c.opacite);
    const enForme = op !== 1 || (c.fusion && c.fusion !== "normal");
    // décidé AVANT les objets : dans le Form du calque, l'espace par défaut est la CTM du Do (la base)
    const cctx = enForme ? { ...ctx, espace: ctx.ctm } : ctx;
    const morceaux = [];
    for (const o of c.objets) {
      const r = _raison(o, cctx);
      if (r) {
        const nom = `I${ctx.rasters.length + 1}`;
        ctx.rasters.push({ id: o.id, nom, raison: r, calque: c.id });
        ctx.stats.rasterises++;
        morceaux.push(`%%RASTER ${nom}%%`);
        continue;
      }
      const x = _objet(o, cctx);
      if (x) { morceaux.push(x); ctx.stats.vectoriels++; }
    }
    if (!morceaux.length) continue;
    if (enForme) {
      // le calque translucide : UN groupe de transparence pour tous ses objets
      const nom = _forme(ctx, morceaux.join("\n"));
      L.push(`q\n${_gs(ctx, { ca: op, CA: op, fusion: c.fusion })}\n/${nom} Do\nQ`);
    } else L.push(...morceaux);
  }
  return { w_pt: cadre.w * k, h_pt: cadre.h * k, contenu: L.join("\n"), formes: ctx.formes, gs: ctx.gs,
           shadings: ctx.shadings, patterns: ctx.patterns, rasters: ctx.rasters, stats: ctx.stats, cadre, k };
}

/* ── L'ASSEMBLAGE : pages → octets PDF 1.4 (xref exacte). Les rasters de chaque page sont fournis par
   l'écran dans `page.images[nom] = {x, y, w, h (px du document), largeur, hauteur (px de l'image), rgba}` ;
   un raster sans image est REFUSÉ — jamais un trou muet. Flate par CompressionStream (navigateur et node). ── */
async function _deflate(octets) {
  const flux = new Blob([octets]).stream().pipeThrough(new CompressionStream("deflate"));
  return new Uint8Array(await new Response(flux).arrayBuffer());
}
const _enc = new TextEncoder();
const _latin = (s) => _enc.encode(s);

export async function pdf_assembler(pages, { compresser = true } = {}) {
  if (!pages || !pages.length) throw new Error(T("vectorlab.pdf.aucune_page"));
  const objets = [];                      // objets[i] = Uint8Array du corps de l'objet i+1
  const ajouter = (corps) => { objets.push(corps); return objets.length; };
  const reserver = () => ajouter(null);
  const flux = async (dict, donnees) => {
    let d = typeof donnees === "string" ? _latin(donnees) : donnees, filtre = "";
    if (compresser) { d = await _deflate(d); filtre = " /Filter /FlateDecode"; }
    return _concat(_latin(`<< ${dict}${filtre} /Length ${d.length} >>\nstream\n`), d, _latin("\nendstream"));
  };
  const catalogue = reserver(), racine = reserver();
  const kids = [];
  for (const p of pages) {
    for (const r of p.rasters || []) {
      if (!(p.images || {})[r.nom]) throw new Error(T("vectorlab.pdf.raster_sans_image", { nom: r.nom, id: r.id, raison: r.raison }));
    }
    // un raster se pose là où son marqueur l'attend — dans la page, ou dans le Form d'un calque translucide
    const poser = (texte) => texte.replace(/%%RASTER (I\d+)%%/g, (_, nom) => {
      const im = (p.images || {})[nom];
      return `q ${nb(im.w)} 0 0 ${nb(-im.h)} ${nb(im.x)} ${nb(im.y + im.h)} cm /${nom} Do Q`;
    });
    const contenu = poser(p.contenu);
    const xobj = [];
    for (const r of p.rasters || []) {
      const im = p.images[r.nom];
      const n =im.largeur * im.hauteur, rgb = new Uint8Array(3 * n), a = new Uint8Array(n);
      for (let i = 0; i < n; i++) { rgb[3 * i] = im.rgba[4 * i]; rgb[3 * i + 1] = im.rgba[4 * i + 1]; rgb[3 * i + 2] = im.rgba[4 * i + 2]; a[i] = im.rgba[4 * i + 3]; }
      const masque = ajouter(await flux(`/Type /XObject /Subtype /Image /Width ${im.largeur} /Height ${im.hauteur} /ColorSpace /DeviceGray /BitsPerComponent 8`, a));
      const img = ajouter(await flux(`/Type /XObject /Subtype /Image /Width ${im.largeur} /Height ${im.hauteur} /ColorSpace /DeviceRGB /BitsPerComponent 8 /SMask ${masque} 0 R`, rgb));
      xobj.push(`/${r.nom} ${img} 0 R`);
    }
    const ressources = reserver();
    for (const [nom, c] of Object.entries(p.formes || {})) {
      // le haut de l'image en (x, y) du document : la matrice de base a déjà retourné l'axe y
      const f = ajouter(await flux(`/Type /XObject /Subtype /Form /BBox [-100000 -100000 100000 100000] /Group << /S /Transparency >> /Resources ${ressources} 0 R`, poser(c)));
      xobj.push(`/${nom} ${f} 0 R`);
    }
    const gs = Object.entries(p.gs || {}).map(([nom, g]) => `/${nom} << /Type /ExtGState /ca ${nb(g.ca)} /CA ${nb(g.CA)}${g.BM ? ` /BM /${g.BM}` : ""} >>`).join(" ");
    const sh = Object.entries(p.shadings || {}).map(([nom, d]) => `/${nom} ${d}`).join(" ");
    const pats = [];
    for (const [nom, P] of Object.entries(p.patterns || {})) {
      const b = P.bbox.map(nb).join(" ");
      const o = ajouter(await flux(`/Type /Pattern /PatternType 1 /PaintType 1 /TilingType 1 /BBox [${b}] /XStep ${nb(P.pas)} `
        + `/YStep ${nb(P.pas)} /Resources << /ProcSet [/PDF] >> /Matrix [${P.matrice.map((v) => nb(v)).join(" ")}]`, P.contenu));
      pats.push(`/${nom} ${o} 0 R`);
    }
    objets[ressources - 1] = _latin(`<< /ProcSet [/PDF /ImageC] /ExtGState << ${gs} >> /XObject << ${xobj.join(" ")} >> `
      + `/Shading << ${sh} >> /Pattern << ${pats.join(" ")} >> >>`);
    const c = ajouter(await flux("", contenu));
    kids.push(ajouter(_latin(`<< /Type /Page /Parent ${racine} 0 R /MediaBox [0 0 ${nb(p.w_pt)} ${nb(p.h_pt)}] /Resources ${ressources} 0 R /Contents ${c} 0 R >>`)));
  }
  objets[racine - 1] = _latin(`<< /Type /Pages /Kids [${kids.map((k) => `${k} 0 R`).join(" ")}] /Count ${kids.length} >>`);
  objets[catalogue - 1] = _latin(`<< /Type /Catalog /Pages ${racine} 0 R >>`);
  const morceaux = [_latin("%PDF-1.4\n%âãÏÓ\n")];
  let pos = morceaux[0].length;
  const offsets = [];
  objets.forEach((corps, i) => {
    offsets.push(pos);
    const m = _concat(_latin(`${i + 1} 0 obj\n`), corps, _latin("\nendobj\n"));
    morceaux.push(m); pos += m.length;
  });
  const xref = [`xref\n0 ${objets.length + 1}\n0000000000 65535 f \n`, ...offsets.map((o) => `${String(o).padStart(10, "0")} 00000 n \n`),
    `trailer\n<< /Size ${objets.length + 1} /Root ${catalogue} 0 R >>\nstartxref\n${pos}\n%%EOF\n`].join("");
  morceaux.push(_latin(xref));
  return _concat(...morceaux);
}
function _concat(...parts) {
  const n = parts.reduce((s, p) => s + p.length, 0), out = new Uint8Array(n);
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}
