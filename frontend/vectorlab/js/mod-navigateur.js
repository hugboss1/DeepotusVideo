// mod-navigateur.js — le panneau Navigateur d'Affinity (R3) : la page en
// vignette, le cadre de la portion visible dans la scène, un curseur de
// zoom à échelle logarithmique (5 % → 1600 %). Feuille pure.
export const ZOOM_MIN = 0.05, ZOOM_MAX = 16;
export function echelle_vignette(taille, vw, vh) {
  const w = taille && +taille.w, h = taille && +taille.h;
  if (!(w > 0) || !(h > 0) || !(vw > 0) || !(vh > 0)) return { k: 0, ox: 0, oy: 0 };
  const k = Math.min(vw / w, vh / h);
  return { k, ox: (vw - w * k) / 2, oy: (vh - h * k) / 2 };
}
// vue = {zoom, tx, ty} (la transformation écran du cœur), scene = {w, h}
export function cadre_vue(taille, vue, scene, e) {
  if (!taille || !(+taille.w > 0) || !(+taille.h > 0) || !vue || !scene || !e || !(e.k > 0)) return null;
  const z = vue.zoom || 1;
  let x0 = -vue.tx / z, y0 = -vue.ty / z, x1 = (scene.w - vue.tx) / z, y1 = (scene.h - vue.ty) / z;
  x0 = Math.max(0, Math.min(+taille.w, x0)); x1 = Math.max(0, Math.min(+taille.w, x1));
  y0 = Math.max(0, Math.min(+taille.h, y0)); y1 = Math.max(0, Math.min(+taille.h, y1));
  return { x: e.ox + x0 * e.k, y: e.oy + y0 * e.k, w: (x1 - x0) * e.k, h: (y1 - y0) * e.k };
}
const L0 = Math.log(ZOOM_MIN), L1 = Math.log(ZOOM_MAX);
export function zoom_de_curseur(v) {
  const t = Math.max(0, Math.min(1000, +v || 0)) / 1000;
  return Math.exp(L0 + (L1 - L0) * t);
}
export function curseur_de_zoom(z) {
  const zz = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, +z || 1));
  return Math.round(1000 * (Math.log(zz) - L0) / (L1 - L0));
}
