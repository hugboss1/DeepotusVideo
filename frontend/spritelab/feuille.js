// feuille.js — lot 1 « Spritelab Feuille » (19/09/2026) : inspecter une
// planche existante. PUR : tampons {w, h, data} RGBA, aucun DOM. Grille par
// projection de l'alpha, sélection par index de case, alignement sur la
// première frame sélectionnée, sections nommées, manifest v2 (même forme que
// sprite_service), recomposition alignée. Banc : qa/feuille.test.mjs.

const _alphaCols = (img) => { const s = new Uint32Array(img.w); for (let y = 0; y < img.h; y++) for (let x = 0; x < img.w; x++) s[x] += img.data[(y * img.w + x) * 4 + 3]; return s; };
const _alphaRows = (img) => { const s = new Uint32Array(img.h); for (let y = 0; y < img.h; y++) for (let x = 0; x < img.w; x++) s[y] += img.data[(y * img.w + x) * 4 + 3]; return s; };
// le nombre de BANDES de contenu séparées par au moins une colonne / ligne vide
const _bandes = (s) => { let n = 0, dedans = false; for (const v of s) { if (v > 0 && !dedans) { n++; dedans = true; } else if (v === 0) dedans = false; } return n; };

// grille uniforme : cols = bandes en x, rows = bandes en y ; sans colonne
// vide on rend 1 × 1 — l'utilisateur saisit, on n'invente jamais
export function grille_detecter(img) {
  if (!img || !(img.w > 0) || !(img.h > 0)) throw new Error("feuille : image vide");
  const cols = Math.max(1, _bandes(_alphaCols(img))), rows = Math.max(1, _bandes(_alphaRows(img)));
  return { cols, rows, cell_w: Math.floor(img.w / cols), cell_h: Math.floor(img.h / rows) };
}
export function rect_case(g, i) {
  const c = i % g.cols, r = Math.floor(i / g.cols);
  return { x: c * g.cell_w, y: r * g.cell_h, w: g.cell_w, h: g.cell_h };
}
export function bbox_alpha(img, rect) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (let y = rect.y; y < rect.y + rect.h && y < img.h; y++) for (let x = rect.x; x < rect.x + rect.w && x < img.w; x++) {
    if (img.data[(y * img.w + x) * 4 + 3] > 0) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  }
  return x0 === Infinity ? null : { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 };
}
export function cases_occupees(img, g) {
  const out = [];
  for (let i = 0; i < g.cols * g.rows; i++) out.push(bbox_alpha(img, rect_case(g, i)) !== null);
  return out;
}
// clic = la case seule ; Ctrl = bascule ; Maj = de la dernière case cliquée à
// celle-ci dans l'ordre de lecture (l'Analyzer dit « Shift last→here »)
export function selection_clic(sel, i, { ctrl = false, shift = false, dernier = null } = {}) {
  const out = sel.slice();
  if (i < 0 || i >= out.length) return out;
  if (shift && dernier !== null && dernier >= 0 && dernier < out.length) {
    const [a, b] = dernier <= i ? [dernier, i] : [i, dernier];
    for (let k = a; k <= b; k++) out[k] = true;
    return out;
  }
  if (ctrl) { out[i] = !out[i]; return out; }
  out.fill(false); out[i] = true;
  return out;
}
// « une sur n » se compte sur les cases OCCUPÉES, les vides ne comptent pas
export function selection_une_sur(occupees, n) {
  const pas = Math.max(1, Math.floor(+n || 1));
  let k = 0;
  return occupees.map((o) => { if (!o) return false; const garde = k % pas === 0; k++; return garde; });
}

export const MODES_ALIGNEMENT = ["deux", "x", "pieds"];
// décalage entier par case pour ramener le centre x et / ou le bas de l'alpha
// sur ceux de la PREMIÈRE case sélectionnée (« Auto Align » de l'Analyzer :
// les feuilles d'IA tremblent) ; borné à la cellule, jamais hors champ
export function aligner_frames(img, g, sel, mode = "deux") {
  if (!MODES_ALIGNEMENT.includes(mode)) throw new Error(`alignement : mode ${mode} inconnu (deux, x, pieds)`);
  const n = g.cols * g.rows, out = [];
  let ref = null;
  for (let i = 0; i < n; i++) {
    if (!sel[i]) continue;
    const b = bbox_alpha(img, rect_case(g, i));
    if (b) { const r = rect_case(g, i); ref = { cx: b.x - r.x + b.w / 2, bas: b.y - r.y + b.h }; break; }
  }
  for (let i = 0; i < n; i++) {
    const r = rect_case(g, i), b = sel[i] ? bbox_alpha(img, r) : null;
    if (!b || !ref) { out.push({ dx: 0, dy: 0 }); continue; }
    let dx = mode === "pieds" ? 0 : Math.round(ref.cx - (b.x - r.x + b.w / 2));
    let dy = mode === "x" ? 0 : Math.round(ref.bas - (b.y - r.y + b.h));
    dx = Math.max(-(b.x - r.x), Math.min(r.w - (b.x - r.x + b.w), dx));
    dy = Math.max(-(b.y - r.y), Math.min(r.h - (b.y - r.y + b.h), dy));
    out.push({ dx, dy });
  }
  return out;
}
export const MODES_SECTION = ["boucle", "pingpong", "inverse"];
export function section_definir() { throw new Error("section_definir : tâche 3"); }
export function manifest_feuille() { throw new Error("manifest_feuille : tâche 3"); }
export function feuille_recomposer() { throw new Error("feuille_recomposer : tâche 3"); }
