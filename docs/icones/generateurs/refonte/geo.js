// Primitives communes de la refonte « Deepotus Glyph » (CHARTE.md).
// Chaque fonction rend une sous-chaîne de `d` (sous-chemin fermé). On assemble plusieurs sous-chemins
// dans UN path avec fill-rule="evenodd" : un sous-chemin contenu dans un autre fait un TROU.
// Usage : const G = require("./geo.js");
const r1 = n => Math.round(n * 10) / 10;
const f = (...a) => a.map(r1).join(" ");

/** Rectangle à coins arrondis (r = 0 : angles vifs). */
function rect(x, y, w, h, r = 0) {
  r = Math.min(r, w / 2, h / 2);
  if (!r) return `M${f(x, y)}H${r1(x + w)}V${r1(y + h)}H${r1(x)}Z`;
  return `M${f(x + r, y)}H${r1(x + w - r)}A${f(r, r)} 0 0 1 ${f(x + w, y + r)}V${r1(y + h - r)}` +
    `A${f(r, r)} 0 0 1 ${f(x + w - r, y + h)}H${r1(x + r)}A${f(r, r)} 0 0 1 ${f(x, y + h - r)}` +
    `V${r1(y + r)}A${f(r, r)} 0 0 1 ${f(x + r, y)}Z`;
}
/** Disque. */
function circle(cx, cy, r) {
  return `M${f(cx - r, cy)}A${f(r, r)} 0 1 0 ${f(cx + r, cy)}A${f(r, r)} 0 1 0 ${f(cx - r, cy)}Z`;
}
/** Anneau (disque évidé) : à mettre seul dans un path evenodd. */
function ring(cx, cy, rOut, rIn) { return circle(cx, cy, rOut) + circle(cx, cy, rIn); }
/** Polygone à partir de points [[x,y],…]. */
function poly(pts) { return "M" + pts.map(p => f(p[0], p[1])).join("L") + "Z"; }
/** Polygone régulier (n côtés), rotation en degrés. */
function ngon(cx, cy, r, n, rot = -90) {
  const pts = [];
  for (let i = 0; i < n; i++) { const a = (rot + i * 360 / n) * Math.PI / 180; pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); }
  return poly(pts);
}
/** Étoile (n branches). */
function star(cx, cy, rOut, rIn, n = 4, rot = -90) {
  const pts = [];
  for (let i = 0; i < 2 * n; i++) { const a = (rot + i * 180 / n) * Math.PI / 180, r = i % 2 ? rIn : rOut; pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); }
  return poly(pts);
}
/** Segment épais à bouts ronds (pilule) de (x1,y1) à (x2,y2), épaisseur w. */
function pill(x1, y1, x2, y2, w) {
  const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1, nx = -dy / L * w / 2, ny = dx / L * w / 2, r = w / 2;
  return `M${f(x1 + nx, y1 + ny)}L${f(x2 + nx, y2 + ny)}A${f(r, r)} 0 0 0 ${f(x2 - nx, y2 - ny)}L${f(x1 - nx, y1 - ny)}A${f(r, r)} 0 0 0 ${f(x1 + nx, y1 + ny)}Z`;
}
/** Flèche pleine : de (x1,y1) vers (x2,y2), fût w, tête de largeur hw et longueur hl. */
function arrow(x1, y1, x2, y2, w = 2.6, hw = 8, hl = 5.4) {
  const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L, nx = -uy, ny = ux;
  const bx = x2 - ux * hl, by = y2 - uy * hl;
  return poly([[x1 + nx * w / 2, y1 + ny * w / 2], [bx + nx * w / 2, by + ny * w / 2], [bx + nx * hw / 2, by + ny * hw / 2], [x2, y2],
    [bx - nx * hw / 2, by - ny * hw / 2], [bx - nx * w / 2, by - ny * w / 2], [x1 - nx * w / 2, y1 - ny * w / 2]]);
}
/** Croix grecque (plus) centrée, bras de longueur totale s, épaisseur w. */
function plus(cx, cy, s, w) { const h = s / 2, k = w / 2;
  return poly([[cx - k, cy - h], [cx + k, cy - h], [cx + k, cy - k], [cx + h, cy - k], [cx + h, cy + k], [cx + k, cy + k], [cx + k, cy + h], [cx - k, cy + h], [cx - k, cy + k], [cx - h, cy + k], [cx - h, cy - k], [cx - k, cy - k]]); }
/** Croix en X. */
function cross(cx, cy, s, w) { return rot(plus(cx, cy, s, w), 45, cx, cy); }
/** Rotation d'un chemin composé uniquement de M/L/H/V/Z absolus (pas d'arcs). Pour les arcs, utiliser transform. */
function rot(d, deg, cx, cy) {
  const a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  let X = 0, Y = 0;
  return d.replace(/([MLHVZ])([^MLHVZ]*)/g, (m, cmd, args) => {
    const n = args.trim() ? args.trim().split(/[\s,]+/).map(Number) : [];
    if (cmd === "Z") return "Z";
    if (cmd === "H") X = n[0]; else if (cmd === "V") Y = n[0]; else { X = n[0]; Y = n[1]; }
    const x = cx + (X - cx) * c - (Y - cy) * s, y = cy + (X - cx) * s + (Y - cy) * c;
    return (cmd === "M" ? "M" : "L") + f(x, y);
  });
}
/** Coche (✓) pleine, épaisseur w, dans la boîte (x,y,s). */
function check(x, y, s, w = 2.6) {
  const p1 = [x + s * .12, y + s * .55], p2 = [x + s * .4, y + s * .82], p3 = [x + s * .9, y + s * .22];
  return pill(p1[0], p1[1], p2[0], p2[1], w) + pill(p2[0], p2[1], p3[0], p3[1], w);
}
/** Badge du quart bas-droit (CHARTE §4) : rend { trou, badge } — `trou` à ajouter au(x) chemin(s) de base
 *  (réserve), `badge` = le cercle du badge au ton sujet. Le symbole du badge se découpe DANS le cercle (evenodd). */
function badge(cx = 18, cy = 18, r = 4.6, gap = 1.4) { return { trou: circle(cx, cy, r + gap), badge: circle(cx, cy, r) }; }

/** Construit le SVG final. parts = [{d, op: 1|.38, evenodd: bool}] ou {stroke: d} pour un élément filaire. */
function svg(parts) {
  const body = parts.map(p => {
    if (p.stroke) return `<path d="${p.stroke}" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"${p.op === .38 ? ' opacity=".38"' : ""}/>`;
    return `<path${p.evenodd ? ' fill-rule="evenodd"' : ""} d="${p.d}"${p.op === .38 ? ' opacity=".38"' : ""}/>`;
  }).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">${body}</svg>`;
}
module.exports = { rect, circle, ring, poly, ngon, star, pill, arrow, plus, cross, rot, check, badge, svg, r1 };
