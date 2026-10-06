/* Hitboxes par frame — T112 (spec sorceress-sprite-suite, lot « Combat » : « calque hitboxes = rectangles par frame
   dans le manifest, dessin au glisser, C/V entre frames »). Module PUR : l'état et ses gestes, sans DOM — spritelab.js
   ne fait que dessiner et câbler. Mêmes règles que le backend (sprite_hitbox.py) : rectangles en pixels DE CASE,
   entiers, rognés à la case, type « hit » (frappe) ou « hurt » (peut être touché), 16 au plus par frame. */

export const TYPES = ["hit", "hurt"];
export const MAX_PAR_FRAME = 16;

const entier = (v) => Math.round(Number(v) || 0);

/* un rectangle borné à la case, ou null s'il n'en reste rien */
export function borner(r, cw, ch) {
  const x = entier(r.x), y = entier(r.y), w = entier(r.w), h = entier(r.h);
  const x0 = Math.max(0, x), y0 = Math.max(0, y), x1 = Math.min(cw, x + w), y1 = Math.min(ch, y + h);
  if (x1 <= x0 || y1 <= y0) return null;
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0, type: TYPES.includes(r.type) ? r.type : "hit" };
}

/* deux points de glisser (dans n'importe quel ordre) → un rectangle ; un clic (moins de 2 px) ne crée rien */
export function rectDepuisGlisser(a, b, cw, ch, type = "hit") {
  const x0 = Math.floor(Math.min(a.x, b.x)), y0 = Math.floor(Math.min(a.y, b.y));
  const x1 = Math.ceil(Math.max(a.x, b.x)), y1 = Math.ceil(Math.max(a.y, b.y));
  if (x1 - x0 < 2 || y1 - y0 < 2) return null;
  return borner({ x: x0, y: y0, w: x1 - x0, h: y1 - y0, type }, cw, ch);
}

/* l'état d'édition depuis un manifeste : une liste PAR frame (copies), frame 0, rien de sélectionné */
export function charger(manifest) {
  const g = manifest.grid || {};
  return {
    cw: g.cell_w || 0, ch: g.cell_h || 0,
    rects: (manifest.frames || []).map((f) => (f.hitboxes || []).map((r) => ({ ...r }))),
    frame: 0, sel: -1, presse: null, sale: false,
  };
}

export function allerA(s, i) {
  s.frame = Math.max(0, Math.min(s.rects.length - 1, i | 0));
  s.sel = -1;
  return s.frame;
}

export function ajouter(s, r) {
  const liste = s.rects[s.frame];
  if (!r || liste.length >= MAX_PAR_FRAME) return -1;
  liste.push(r);
  s.sel = liste.length - 1;
  s.sale = true;
  return s.sel;
}

/* le rectangle sous le point (le dernier dessiné est dessus) ; sélectionne et rend son rang, ou -1 */
export function selectionnerSous(s, x, y) {
  const liste = s.rects[s.frame];
  for (let k = liste.length - 1; k >= 0; k--) {
    const r = liste[k];
    if (x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h) return (s.sel = k);
  }
  return (s.sel = -1);
}

/* l'inspecteur : champs modifiés sur le sélectionné, rognés ; un type inconnu est ignoré */
export function modifier(s, champs) {
  const liste = s.rects[s.frame];
  if (s.sel < 0 || !liste[s.sel]) return null;
  const cur = liste[s.sel];
  const voulu = { ...cur, ...champs };
  if (!TYPES.includes(voulu.type)) voulu.type = cur.type;
  const b = borner(voulu, s.cw, s.ch);
  if (!b) return null;
  liste[s.sel] = b;
  s.sale = true;
  return b;
}

export function supprimer(s) {
  const liste = s.rects[s.frame];
  if (s.sel < 0 || !liste[s.sel]) return false;
  liste.splice(s.sel, 1);
  s.sel = -1;
  s.sale = true;
  return true;
}

/* Ctrl+C : toute la frame courante ; Ctrl+V : s'ajoute à la frame courante, jusqu'au plafond */
export function copier(s) {
  s.presse = s.rects[s.frame].map((r) => ({ ...r }));
  return s.presse.length;
}

export function coller(s) {
  if (!s.presse || !s.presse.length) return 0;
  const liste = s.rects[s.frame];
  let n = 0;
  for (const r of s.presse) {
    if (liste.length >= MAX_PAR_FRAME) break;
    liste.push({ ...r });
    n++;
  }
  if (n) { s.sel = liste.length - 1; s.sale = true; }
  return n;
}

/* le corps de POST /api/assets/sprite/{job}/hitboxes */
export function corps(s) {
  return { hitboxes: s.rects.map((l) => l.map((r) => ({ x: r.x, y: r.y, w: r.w, h: r.h, type: r.type }))) };
}
