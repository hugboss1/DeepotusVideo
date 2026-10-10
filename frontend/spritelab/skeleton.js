/* Squelette Spine — t111 (plan-sprites T12). Module PUR : l'état du rig et ses gestes, sans DOM ; spritelab.js dessine
   et câble. La page parle comme elle voit : positions en pixels DE CASE (y vers le bas), angle VISUEL d'un os en degrés
   (sens trigonométrique, 90 = vers le haut). sprite_skeleton.py convertit vers les repères LOCAUX de Spine — une seule
   fois, côté serveur. Mêmes règles que le backend (lues par le banc qa/skeleton.test.mjs) : noms, bornes. */

export const MAX_OS = 24;
export const MAX_PIECES = 24;
export const NOM = /^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$/;

const borne = (v, lo, hi) => Math.max(lo, Math.min(hi, Number(v) || 0));
const r3 = (v) => Math.round(v * 1000) / 1000;
/* ]-180, 180], comme `_angle` côté serveur : atan2(-0, -30) rend -180 (zéro négatif de -dy), le même angle que 180 */
const angle = (r) => { const a = ((r + 180) % 360 + 360) % 360 - 180; return a === -180 ? 180 : a; };

export function charger(manifest) {
  const g = (manifest && manifest.grid) || {};
  return { cw: g.cell_w || 0, ch: g.cell_h || 0, n: ((manifest && manifest.frames) || []).length,
           frame: 0, bones: [], pieces: [], sel: "", outil: "os" };
}

export function allerA(s, i) {
  s.frame = Math.max(0, Math.min(Math.max(0, s.n - 1), i | 0));
  return s.frame;
}

export function nomLibre(prefixe, pris) {
  const set = new Set(pris);
  for (let i = 1; ; i++) if (!set.has(prefixe + i)) return prefixe + i;
}

/* un os au glisser : de la base `a` vers le bout `b`. Un clic (moins de 2 px) pose un os court dressé (90°). Il
   s'accroche à l'os sélectionné (sinon à la racine) et devient la sélection : on pose une chaîne d'un geste à l'autre. */
export function ajouterOs(s, a, b) {
  if (s.bones.length >= MAX_OS) throw new Error(__dzT9("sprites.sp2_skm.max_os", "{n} os au plus", { n: MAX_OS }));
  const x = borne(a.x, 0, s.cw), y = borne(a.y, 0, s.ch);
  const dx = borne(b.x, 0, s.cw) - x, dy = borne(b.y, 0, s.ch) - y;
  const long = Math.hypot(dx, dy);
  const os = { name: nomLibre("os", s.bones.map((o) => o.name)),
               parent: s.bones.some((o) => o.name === s.sel) ? s.sel : "root",
               x: r3(x), y: r3(y), length: long < 2 ? 0 : r3(long),
               rotation: long < 2 ? 90 : r3(angle(Math.atan2(-dy, dx) * 180 / Math.PI)) };
  s.bones.push(os);
  s.sel = os.name;
  return os;
}

/* une pièce au glisser : boîte entière, rognée à la case, accrochée à l'os sélectionné (ou au dernier posé) */
export function ajouterPiece(s, a, b) {
  if (!s.bones.length) throw new Error(__dzT9("sprites.sp2_skm.os_dabord", "pose d'abord un os : une pièce s'accroche à un os"));
  if (s.pieces.length >= MAX_PIECES) throw new Error(__dzT9("sprites.sp2_skm.max_pieces", "{n} pièces au plus", { n: MAX_PIECES }));
  const x0 = Math.max(0, Math.floor(Math.min(a.x, b.x))), y0 = Math.max(0, Math.floor(Math.min(a.y, b.y)));
  const x1 = Math.min(s.cw, Math.ceil(Math.max(a.x, b.x))), y1 = Math.min(s.ch, Math.ceil(Math.max(a.y, b.y)));
  if (x1 - x0 < 2 || y1 - y0 < 2) return null;
  const os = s.bones.some((o) => o.name === s.sel) ? s.sel : s.bones[s.bones.length - 1].name;
  const p = { name: nomLibre("piece", s.pieces.map((q) => q.name)), bone: os, x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
  s.pieces.push(p);
  return p;
}

export function renommerOs(s, ancien, neuf) {
  const n = String(neuf || "").trim();
  if (!NOM.test(n) || n === "root" || s.bones.some((o) => o.name === n)) return false;
  const os = s.bones.find((o) => o.name === ancien);
  if (!os) return false;
  os.name = n;
  for (const o of s.bones) if (o.parent === ancien) o.parent = n;
  for (const p of s.pieces) if (p.bone === ancien) p.bone = n;
  if (s.sel === ancien) s.sel = n;
  return true;
}

export function renommerPiece(s, ancien, neuf) {
  const n = String(neuf || "").trim();
  if (!NOM.test(n) || s.pieces.some((p) => p.name === n)) return false;
  const p = s.pieces.find((q) => q.name === ancien);
  if (!p) return false;
  p.name = n;
  return true;
}

/* supprimer un os emporte ses descendants et leurs pièces — sinon le corps serait refusé (parent ou os inconnu) */
export function supprimerOs(s, nom) {
  const partis = new Set([nom]);
  for (const o of s.bones) if (partis.has(o.parent)) partis.add(o.name);      // parent avant enfant : un seul passage
  const n0 = s.bones.length, p0 = s.pieces.length;
  s.bones = s.bones.filter((o) => !partis.has(o.name));
  s.pieces = s.pieces.filter((p) => !partis.has(p.bone));
  if (partis.has(s.sel)) s.sel = "";
  return { os: n0 - s.bones.length, pieces: p0 - s.pieces.length };
}

export function supprimerPiece(s, nom) {
  const n = s.pieces.length;
  s.pieces = s.pieces.filter((p) => p.name !== nom);
  return s.pieces.length < n;
}

export const pret = (s) => s.bones.length > 0 && s.pieces.length > 0;

export function corps(s) {
  return { frame: s.frame,
           bones: s.bones.map(({ name, parent, x, y, length, rotation }) => ({ name, parent, x, y, length, rotation })),
           pieces: s.pieces.map(({ name, bone, x, y, w, h }) => ({ name, bone, x, y, w, h })) };
}
// t149 (traduction L9) : dzT dans la page, le français sous node (bancs)
function __dzT9(k, fr, v) { return typeof globalThis.dzT === "function" ? globalThis.dzT(k, v) : String(fr).replace(/\{(\w+)\}/g, (m, n) => (v && v[n] != null ? String(v[n]) : m)); }
