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
import { chemin_parser, terrains_de, grille_tuiles } from "./mod-doc.js";
import { forme_d } from "./mod-formes.js";
import { hex_centre, hex_d } from "./mod-grille.js";

/* ── nombres ── */
export function nb(x) {
  const v = Math.round(+x * 1000) / 1000;
  return v === 0 ? "0" : String(v);
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
    if (!x) throw new Error(`transform illisible : ${src}`);
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
const _A_RASTER = { image: "image", cadre: "cadre de texte", textechemin: "texte sur chemin" };
function _raisonPeinture(v, ctx) {
  if (v === undefined || v === "none") return null;
  if (typeof v === "string" && v.startsWith("grad:")) return "dégradé";
  if (typeof v === "string" && v.startsWith("motif:")) return "motif";
  return couleur_rgba(v, ctx.globales) === undefined ? `couleur ${v}` : null;
}
function _raison(o, ctx) {
  const s = o.style || {};
  if (_A_RASTER[o.type]) return _A_RASTER[o.type];
  if (s.effets && s.effets.length) return "effet";
  if (s.masque) return "masque de transparence";
  const r = _raisonPeinture(s.fond, ctx) || _raisonPeinture(s.contour, ctx)
    || (s.contours || []).map((c) => _raisonPeinture(c.couleur, ctx)).find(Boolean);
  if (r) return r;
  if (o.type === "texte" && !(ctx.glyphes && ctx.glyphes(o))) return "texte (police non chargée)";
  if (o.type === "tuile") {
    const f = ctx.terrains[o.terrain];
    if (f && f.motif && !(s.fond !== undefined)) return "motif de terrain";
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

/* ── peinture d'un chemin : réglages de trait, couleurs, opérateur ── */
const JOINT = { miter: 0, round: 1, bevel: 2 };
function _peindre(chemin, s, ctx, { sansOpacite = false } = {}) {
  const fond = couleur_rgba(s.fond, ctx.globales), contour = couleur_rgba(s.contour, ctx.globales);
  if (!fond && !contour) return "";
  const op = Number(s.opacite === undefined ? 1 : s.opacite);
  const L = [];
  const g = _gs(ctx, { ca: (fond ? fond[3] : 1) * (sansOpacite ? 1 : op), CA: (contour ? contour[3] : 1) * (sansOpacite ? 1 : op) });
  if (g) L.push(g);
  if (fond) L.push(`${_rgb(fond)} rg`);
  if (contour) {
    L.push(`${_rgb(contour)} RG`, `${nb(Number(s.epaisseur || 1))} w`, `${JOINT[s.joint || "round"] ?? 1} j`, "1 J");
    const tirets = String(s.pointilles || "").trim().split(/[\s,]+/).filter(Boolean).map(Number);
    L.push(tirets.length && tirets.every((v) => v >= 0) ? `[${tirets.map(nb).join(" ")}] 0 d` : "[] 0 d");
  }
  const eo = s.regle === "evenodd" ? "*" : "";
  L.push(chemin, fond && contour ? `B${eo}` : fond ? `f${eo}` : "S");
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
    const f = ctx.terrains[o.terrain];
    s = { fond: f ? f.couleur : "#888888", contour: "#1F1512", epaisseur: 1, ...s0 };
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
    || (couleur_rgba(s.fond, ctx.globales) && couleur_rgba(s.contour, ctx.globales));
  let m = matrice_de(o.transform);
  if (o.type === "instance") m = matrice_mul(m, [o.sx === undefined ? 1 : +o.sx, 0, 0, o.sy === undefined ? 1 : +o.sy, +o.x, +o.y]);
  let corps, etat = false;                // etat : le corps pose un gs ou un écrêtage → q … Q obligatoire
  if (op !== 1 && peint) {
    // groupe de transparence : le corps sans son opacité, dessiné d'un bloc sous ca/CA
    const interieur = _corps(o, { ...ctx, sansOpacite: true });
    if (!interieur.trim()) return "";
    corps = `${_gs(ctx, { ca: op, CA: op, fusion: s.fusion })}\n/${_forme(ctx, interieur)} Do`;
    etat = true;
  } else {
    const fu = _gs(ctx, { fusion: s.fusion });
    const interieur = _corps(o, ctx);
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
  const ctx = { doc, globales: doc.couleursGlobales || {}, terrains: terrains_de(doc), grille: grille_tuiles(doc),
    glyphes: opts.glyphes || (() => null), gs: {}, gsCles: new Map(), formes: {}, rasters: [],
    stats: { vectoriels: 0, rasterises: 0 } };
  const L = [_cm([k, 0, 0, -k, -cadre.x * k, (cadre.y + cadre.h) * k])];
  if (doc.fond && !opts.transparent) {
    const c = couleur_rgba(doc.fond, ctx.globales);
    if (c) L.push(`${_rgb(c)} rg\n${_rect(0, 0, +doc.taille.w, +doc.taille.h)}\nf`);
  }
  for (const c of doc.calques) {
    if (c.visible === false) continue;
    const morceaux = [];
    for (const o of c.objets) {
      const r = _raison(o, ctx);
      if (r) {
        const nom = `I${ctx.rasters.length + 1}`;
        ctx.rasters.push({ id: o.id, nom, raison: r, calque: c.id });
        ctx.stats.rasterises++;
        morceaux.push(`%%RASTER ${nom}%%`);
        continue;
      }
      const x = _objet(o, ctx);
      if (x) { morceaux.push(x); ctx.stats.vectoriels++; }
    }
    if (!morceaux.length) continue;
    const op = c.opacite === undefined ? 1 : Number(c.opacite);
    if (op !== 1 || (c.fusion && c.fusion !== "normal")) {
      // le calque translucide : UN groupe de transparence pour tous ses objets
      const nom = _forme(ctx, morceaux.join("\n"));
      L.push(`q\n${_gs(ctx, { ca: op, CA: op, fusion: c.fusion })}\n/${nom} Do\nQ`);
    } else L.push(...morceaux);
  }
  return { w_pt: cadre.w * k, h_pt: cadre.h * k, contenu: L.join("\n"), formes: ctx.formes, gs: ctx.gs,
           rasters: ctx.rasters, stats: ctx.stats, cadre, k };
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
  if (!pages || !pages.length) throw new Error("pdf : aucune page");
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
      if (!(p.images || {})[r.nom]) throw new Error(`pdf : le raster ${r.nom} (${r.id}, ${r.raison}) n'a pas d'image`);
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
    objets[ressources - 1] = _latin(`<< /ProcSet [/PDF /ImageC] /ExtGState << ${gs} >> /XObject << ${xobj.join(" ")} >> >>`);
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
