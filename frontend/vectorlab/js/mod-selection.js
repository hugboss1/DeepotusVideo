// mod-selection.js — l'outil Sélection de classe Affinity (R10) : le
// déplacement contraint aux axes (Maj), le cadre de sélection (objets
// entièrement inclus, ou touchés avec Alt), la boîte d'un jeu d'ancres,
// les poignées d'une boîte, le redimensionnement par poignée (proportions,
// depuis le centre), la rotation d'ancres autour d'un centre. Feuille pure.
export function contraindre_axe(dx, dy) {
  return Math.abs(dx) >= Math.abs(dy) ? [dx, 0] : [0, dy];
}
export function cadre_selection(boites, cadre, mode = "inclus") {
  if (!Array.isArray(boites) || !cadre || !(cadre.w > 0) || !(cadre.h > 0)) return [];
  const x1 = cadre.x + cadre.w, y1 = cadre.y + cadre.h;
  const touche = mode === "touches";
  return boites.filter((b) => touche
    ? (b.x < x1 && b.x + b.w > cadre.x && b.y < y1 && b.y + b.h > cadre.y)
    : (b.x >= cadre.x && b.y >= cadre.y && b.x + b.w <= x1 && b.y + b.h <= y1)).map((b) => b.id);
}
export function bbox_ancres(ancres, indices) {
  const pts = (indices || []).map((i) => ancres[i]).filter(Boolean);
  if (!pts.length) return null;
  const xs = pts.map((a) => a.x), ys = pts.map((a) => a.y);
  const x = Math.min(...xs), y = Math.min(...ys);
  return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
}
// l'ordre des poignées du cœur : 0 haut-gauche, 1 haut, 2 haut-droit, 3 droit, 4 bas-droit, 5 bas, 6 bas-gauche, 7 gauche
export function poignees_bbox(b) {
  const { x, y, w, h } = b;
  return { poignees: [[x, y], [x + w / 2, y], [x + w, y], [x + w, y + h / 2], [x + w, y + h], [x + w / 2, y + h], [x, y + h], [x, y + h / 2]], rotation: [x + w / 2, y - 26] };
}
export function bbox_par_poignee(b0, k, pt, { proportions = false, centre = false } = {}) {
  if (!(k >= 0 && k <= 7)) return { ...b0 };
  const b = { ...b0 };
  const [ax, ay] = pt;
  if ([0, 6, 7].includes(k)) { b.w = b.x + b.w - ax; b.x = ax; }
  if ([2, 3, 4].includes(k)) { b.w = ax - b.x; }
  if ([0, 1, 2].includes(k)) { b.h = b.y + b.h - ay; b.y = ay; }
  if ([4, 5, 6].includes(k)) { b.h = ay - b.y; }
  if (proportions && b0.w > 0 && b0.h > 0 && [0, 2, 4, 6].includes(k)) {
    const s = Math.max(Math.abs(b.w) / b0.w, Math.abs(b.h) / b0.h);
    const w2 = b0.w * s, h2 = b0.h * s;
    if ([0, 6].includes(k)) b.x = b.x + b.w - w2;
    if ([0, 2].includes(k)) b.y = b.y + b.h - h2;
    b.w = w2; b.h = h2;
  }
  if (centre) {
    // le centre de b0 reste fixe : le côté opposé bouge du même delta
    const cx = b0.x + b0.w / 2, cy = b0.y + b0.h / 2;
    const dw = [0, 6, 7].includes(k) ? (b0.x - b.x) : [2, 3, 4].includes(k) ? (b.w - b0.w) : 0;
    const dh = [0, 1, 2].includes(k) ? (b0.y - b.y) : [4, 5, 6].includes(k) ? (b.h - b0.h) : 0;
    b.w = b0.w + 2 * dw; b.h = b0.h + 2 * dh; b.x = cx - b.w / 2; b.y = cy - b.h / 2;
  }
  b.w = Math.max(1, b.w); b.h = Math.max(1, b.h);
  return b;
}
export function noeuds_tourner(segs, indices, cx, cy, deg) {
  const out = segs.map((s) => ({ c: s.c, p: s.p.slice() }));
  const idx = (indices || []).filter((i) => Number.isInteger(i));
  if (!idx.length || !deg) return out;
  const pk = out.map((s, k) => s.c !== "Z" ? k : -1).filter((k) => k >= 0);
  const a = deg * Math.PI / 180, cos = Math.cos(a), sin = Math.sin(a);
  const r = (v) => Math.round(v * 1e6) / 1e6;
  const tourner = (p, j) => { const x = p[j] - cx, y = p[j + 1] - cy; p[j] = r(cx + x * cos - y * sin); p[j + 1] = r(cy + x * sin + y * cos); };
  for (const i of idx) {
    const s = out[pk[i]]; if (!s) continue;
    for (let j = s.c === "C" ? 2 : 0; j < s.p.length; j += 2) tourner(s.p, j);   // l'ancre et son entrante
    const sn = out[pk[i + 1]];
    if (sn && sn.c === "C") tourner(sn.p, 0);                                     // sa sortante
  }
  return out;
}
