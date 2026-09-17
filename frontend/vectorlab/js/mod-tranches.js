// mod-tranches.js — le persona Export, côté PUR (lot G) : les tranches
// (document, planches, calques visibles, objets sélectionnés, tranches
// dessinées) avec une bbox INJECTÉE, les résolutions lues et bornées, le
// nommage `vector_<doc>_<tranche>@<k>x[_t].<ext>`, le plan d'export
// (tranches × résolutions × formats), la saignée et les marques de coupe /
// repérage en SVG (coordonnées du document). Module FEUILLE.

export const MODES = [
  { id: "document", libelle: "Document entier" },
  { id: "planches", libelle: "Chaque planche" },
  { id: "calques", libelle: "Chaque calque visible" },
  { id: "objets", libelle: "Chaque objet sélectionné" },
  { id: "dessinees", libelle: "Tranches dessinées" },
];
export const FORMATS = [
  { id: "png", ext: "png", libelle: "PNG", raster: true },
  { id: "jpeg", ext: "jpg", libelle: "JPEG", raster: true },
  { id: "webp", ext: "webp", libelle: "WebP", raster: true },
  { id: "svg", ext: "svg", libelle: "SVG", raster: false },
  { id: "pdf", ext: "pdf", libelle: "PDF (impression)", raster: false },
  { id: "dxf", ext: "dxf", libelle: "DXF (découpe)", raster: false },
];
export const nom_sain = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").trim()
  .replace(/\s+/g, "-").replace(/[^A-Za-z0-9_-]/g, "");

function _union(bs) {
  const x0 = Math.min(...bs.map((b) => b.x)), y0 = Math.min(...bs.map((b) => b.y));
  return { x: x0, y: y0, w: Math.max(...bs.map((b) => b.x + b.w)) - x0, h: Math.max(...bs.map((b) => b.y + b.h)) - y0 };
}
export function tranches_de(doc, mode, { ids = [], bboxDe = () => null, dessinees = [] } = {}) {
  if (!MODES.some((m) => m.id === mode)) throw new Error(`mode de tranche inconnu : ${mode}`);
  const T = (nom, cadre, extra = {}) => ({ nom: nom_sain(nom) || "tranche", cadre: { x: +cadre.x, y: +cadre.y, w: +cadre.w, h: +cadre.h }, ...extra });
  switch (mode) {
    case "document": return [T("doc", { x: 0, y: 0, w: doc.taille.w, h: doc.taille.h })];
    case "planches": return (doc.planches || []).map((p) => T(p.nom || p.id, p, { plancheId: p.id }));
    case "calques": {
      const out = [];
      for (const c of doc.calques || []) {
        if (c.visible === false) continue;
        const bs = (c.objets || []).map(bboxDe).filter((b) => b && b.w >= 0 && b.h >= 0);
        if (!bs.length) continue;
        out.push(T(c.nom || c.id, _union(bs), { calqueId: c.id }));
      }
      return out;
    }
    case "objets": {
      const out = [];
      const visiter = (objs) => { for (const o of objs || []) { if (ids.includes(o.id)) { const b = bboxDe(o); if (b) out.push(T(o.id, b, { id: o.id })); } if (o.type === "groupe") visiter(o.enfants); } };
      for (const c of doc.calques || []) visiter(c.objets);
      return out;
    }
    default: return (dessinees || []).map((t, i) => T(t.nom || `t${i + 1}`, t));
  }
}
export function resolutions_lire(texte) {
  const vus = new Set();
  for (const m of String(texte || "").split(/[,\s;]+/)) {
    const k = Math.round(+m);
    if (Number.isFinite(k) && k >= 1 && k <= 8) vus.add(k);
    if (vus.size >= 4) break;
  }
  return vus.size ? [...vus] : [1];
}
export function nom_export(docId, tranche, k, format, transparent) {
  const f = FORMATS.find((x) => x.id === format) || { ext: format, raster: true };
  const suffixe = f.raster && k !== 1 ? `@${k}x` : "";
  return `vector_${nom_sain(docId)}_${nom_sain(tranche)}${suffixe}${transparent && f.raster ? "_t" : ""}.${f.ext}`;
}
// tranches × résolutions pour les rasters ; une entrée par tranche pour
// svg / dxf ; UNE entrée pdf pour tout le lot (une page par tranche)
export function plan_export(docId, tranches, ks, formats, transparent) {
  const out = [];
  if (!tranches.length) return out;
  for (const format of formats) {
    const f = FORMATS.find((x) => x.id === format);
    if (!f) continue;
    if (format === "pdf") { out.push({ format, nom: nom_export(docId, "lot", 1, "pdf", false), tranches: tranches.slice() }); continue; }
    for (const t of tranches) {
      if (f.raster) for (const k of ks) out.push({ format, k, tranche: t, nom: nom_export(docId, t.nom, k, format, transparent) });
      else out.push({ format, k: 1, tranche: t, nom: nom_export(docId, t.nom, 1, format, false) });
    }
  }
  return out;
}
export const mm_px = (mm, dpi) => +mm * +dpi / 25.4;
export function cadre_saignee(cadre, s) {
  return { x: cadre.x - s, y: cadre.y - s, w: cadre.w + 2 * s, h: cadre.h + 2 * s };
}
const _n = (v) => String(Math.round(v * 100) / 100);
// traits de coupe : deux par coin, HORS de la saignée, longueur L ;
// repères : cercle + croix au milieu de chaque côté, sur la saignée
export function marques_svg(cadre, s, { coupe = false, reperage = false } = {}, L = 8) {
  if (!coupe && !reperage) return "";
  const x0 = cadre.x, y0 = cadre.y, x1 = cadre.x + cadre.w, y1 = cadre.y + cadre.h;
  const l = (a, b, c, d) => `<line x1="${_n(a)}" y1="${_n(b)}" x2="${_n(c)}" y2="${_n(d)}"/>`;
  const parts = [];
  if (coupe) {
    for (const [x, sx] of [[x0, -1], [x1, 1]]) for (const [y, sy] of [[y0, -1], [y1, 1]]) {
      parts.push(l(x, y + sy * (s + L), x, y + sy * s));       // vertical, du dehors vers la saignée
      parts.push(l(x + sx * (s + L), y, x + sx * s, y));       // horizontal
    }
  }
  if (reperage) {
    const r = L / 2;
    for (const [cx, cy] of [[(x0 + x1) / 2, y0 - s - r], [(x0 + x1) / 2, y1 + s + r], [x0 - s - r, (y0 + y1) / 2], [x1 + s + r, (y0 + y1) / 2]]) {
      parts.push(`<circle cx="${_n(cx)}" cy="${_n(cy)}" r="${_n(r * 0.7)}"/>`, l(cx - r, cy, cx + r, cy), l(cx, cy - r, cx, cy + r));
    }
  }
  return `<g data-marques="1" fill="none" stroke="#000000" stroke-width="0.5">${parts.join("")}</g>`;
}
