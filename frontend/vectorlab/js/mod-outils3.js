// mod-outils3.js — les outils d'Affinity ajoutés au Vectorlab (R7) : la
// géométrie PURE des gestes — cadrer / zoomer (Loupe), dégradé au glisser,
// rognage d'image au glisser, cadre de texte au glisser, disque de masque
// des pinceaux de retouche. Feuille pure ; mod-outils3ui traduit.
export const ZOOM_MIN = 0.05, ZOOM_MAX = 16;
const borneZoom = (z) => Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z));
export function rect_normalise(a, b, min = 0) {
  if (!Array.isArray(a) || !Array.isArray(b)) return null;
  const x = Math.min(a[0], b[0]), y = Math.min(a[1], b[1]), w = Math.abs(a[0] - b[0]), h = Math.abs(a[1] - b[1]);
  if (!(w >= min) || !(h >= min) || !(w > 0) || !(h > 0)) return null;
  return { x, y, w, h };
}
export function zoom_rect(rect, scene, marge = 40) {
  if (!rect || !(rect.w > 0) || !(rect.h > 0) || !scene || !(scene.w > 0) || !(scene.h > 0)) return null;
  const zoom = borneZoom(Math.min((scene.w - 2 * marge) / rect.w, (scene.h - 2 * marge) / rect.h));
  return { zoom, tx: scene.w / 2 - (rect.x + rect.w / 2) * zoom, ty: scene.h / 2 - (rect.y + rect.h / 2) * zoom };
}
export function zoom_point(vue, pt, facteur) {
  const z2 = borneZoom((vue.zoom || 1) * (+facteur || 1)), k = z2 / (vue.zoom || 1);
  return { zoom: z2, tx: pt[0] - (pt[0] - vue.tx) * k, ty: pt[1] - (pt[1] - vue.ty) * k };
}
const HEX = /^#[0-9a-f]{6}$/i;
export function degrade_de_glisser(p1, p2, style) {
  if (!p1 || !p2 || (p1[0] === p2[0] && p1[1] === p2[1])) return null;
  const fond = style && HEX.test(style.fond || "") ? style.fond : "#000000";
  return { type: "lineaire", x1: p1[0], y1: p1[1], x2: p2[0], y2: p2[1], stops: [{ t: 0, couleur: fond }, { t: 1, couleur: "#FFFFFF" }] };
}
export function rognage_de_rect(objet, rect) {
  if (!objet || !objet.nat || !(objet.nat.w > 0) || !(objet.nat.h > 0) || !(objet.w > 0) || !(objet.h > 0) || !rect) return null;
  const r0 = objet.rognage || { x: 0, y: 0, w: objet.nat.w, h: objet.nat.h };   // la portion native affichée
  const kx = r0.w / objet.w, ky = r0.h / objet.h;                                  // px natifs par px document
  let x0 = r0.x + (rect.x - objet.x) * kx, y0 = r0.y + (rect.y - objet.y) * ky;
  let x1 = x0 + rect.w * kx, y1 = y0 + rect.h * ky;
  x0 = Math.max(0, Math.min(objet.nat.w, x0)); x1 = Math.max(0, Math.min(objet.nat.w, x1));
  y0 = Math.max(0, Math.min(objet.nat.h, y0)); y1 = Math.max(0, Math.min(objet.nat.h, y1));
  const out = { x: Math.round(x0), y: Math.round(y0), w: Math.round(x1 - x0), h: Math.round(y1 - y0) };
  return out.w > 0 && out.h > 0 ? out : null;
}
export function cadre_de_rect(rect, style, contenu) {
  const s = { corps: 16, ...(style || {}) };
  return { type: "cadre", x: +rect.x, y: +rect.y, w: +rect.w, h: +rect.h, contenu: contenu && String(contenu).trim() ? String(contenu) : "Texte", style: s };
}
export function disque_masque(w, h, cx, cy, r) {
  const m = new Uint8Array(Math.max(0, (w | 0) * (h | 0)));
  const rr = Math.max(0, +r || 0), x0 = Math.max(0, Math.floor(cx - rr)), x1 = Math.min(w - 1, Math.ceil(cx + rr)), y0 = Math.max(0, Math.floor(cy - rr)), y1 = Math.min(h - 1, Math.ceil(cy + rr));
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if ((x - cx) * (x - cx) + (y - cy) * (y - cy) <= rr * rr) m[y * w + x] = 255;
  return m;
}
