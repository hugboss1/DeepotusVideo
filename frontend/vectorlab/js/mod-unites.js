// mod-unites.js — éditeur complet (E2) : les unités d'affichage du
// document (px, mm, cm, in) et les libellés de cote des gestes. PUR —
// aucun DOM ; le document reste en px (l'unité est une affaire
// d'affichage, `unites.dpi` fait le pont physique).

const _DEC = { px: 0, mm: 1, cm: 2, in: 2 };
export const UNITES = ["px", "mm", "cm", "in"];

export function pxParUnite(unite, dpi) {
  const d = +dpi > 0 ? +dpi : 96;
  switch (unite) {
    case "mm": return d / 25.4;
    case "cm": return d / 2.54;
    case "in": return d;
    default: return 1;                       // px
  }
}

function _u(unites) {
  const u = unites || {};
  return { affichage: UNITES.includes(u.affichage) ? u.affichage : "px",
           dpi: +u.dpi > 0 ? +u.dpi : 96 };
}

export function versUnite(px, unites) {
  const { affichage, dpi } = _u(unites);
  return px / pxParUnite(affichage, dpi);
}

export function depuisUnite(valeur, unites) {
  const { affichage, dpi } = _u(unites);
  return valeur * pxParUnite(affichage, dpi);
}

export function suffixe(unite) {
  return UNITES.includes(unite) ? unite : "px";
}

function _fr(n, dec) {
  // demi vers le haut, à l'abri du flottant nu (6,35 → 6,4, jamais 6,3) —
  // même remède que le sérialiseur de chemins : toPrecision(12)
  const f = Math.pow(10, dec);
  const r = Math.round(Number((n * f).toPrecision(12))) / f;
  let s = r.toFixed(dec);
  if (dec > 0) s = s.replace(/0+$/, "").replace(/\.$/, "");
  if (s === "-0") s = "0";
  return s.replace(".", ",");
}

export function formatNombre(px, unites) {
  const { affichage } = _u(unites);
  return _fr(versUnite(px, unites), _DEC[affichage]);
}

export function formatMesure(px, unites) {
  return formatNombre(px, unites) + " " + suffixe(_u(unites).affichage);
}

/* Le libellé qui suit CE qu'on dessine : L × H pour les formes, rayon et
   diamètre pour les cercles, rx × ry pour les ellipses, longueur ∠ angle
   pour les segments, Δ pour les déplacements. */
export function libelle_mesure(kind, geom, unites) {
  const suf = suffixe(_u(unites).affichage);
  const fn = (px) => formatNombre(px, unites);
  if (kind === "rect") {
    return `${fn(geom.w)} × ${fn(geom.h)} ${suf}`;
  }
  if (kind === "ellipse") {
    const { rx, ry } = geom;
    if (Math.abs(rx - ry) <= 0.5) {
      return `r ${fn(rx)} · ⌀ ${fn(2 * rx)} ${suf}`;
    }
    return `r ${fn(rx)} × ${fn(ry)} ${suf}`;
  }
  if (kind === "segment") {
    const long = Math.hypot(geom.dx, geom.dy);
    const a = Math.round(Math.atan2(geom.dy, geom.dx) * 180 / Math.PI * 10) / 10;
    return `${formatMesure(long, unites)} ∠ ${String(a).replace(".", ",")}°`;
  }
  if (kind === "delta") {
    return `Δ ${fn(geom.dx)} ; ${fn(geom.dy)} ${suf}`;
  }
  throw new Error(`libelle_mesure: genre inconnu ${kind}`);
}
