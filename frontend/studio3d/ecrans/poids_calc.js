/* t396 (31/10/2026) — le CALCUL des poids de peau de l'écran Affiner, sans DOM ni three.js : il tourne sous node
   (banc qa/affiner.test.mjs). affiner.js ne fait que relier ces opérations au pinceau, au lasso et à la vue.

   Les poids d'un maillage skinné sont ceux de three.js : `j` (skinIndex) et `w` (skinWeight), QUATRE influences par
   sommet, indices dans les os de la peau. Chaque opération garde l'invariant : quatre influences au plus, somme 1 (un
   sommet n'est jamais vidé : si l'os peint tenait tout et qu'on le retire, le reste va à l'os de REPLI, son parent).
   Relevé de Sorceress (§6, Refine) : outils Choisir l'os (1), Peindre (2), Lasso (3, sommets VUS seulement, t405),
   Pose (P, poignées IK : ik_calc.js) ; opérations Fixer R,
   Ajouter A, Retirer S, Lisser D, Flouter F ; atténuation linéaire / douce / constante ; miroir (M) ; isoler (5) ;
   sommets sans poids ; `[ ]` taille, Ctrl + molette rayon, Maj + molette force ; annuler / rétablir. */
"use strict";

export const OUTILS = ["os", "peindre", "lasso", "pose"];
export const MODES = ["fixer", "ajouter", "retirer", "lisser", "flouter"];
export const ATTENUATIONS = ["lineaire", "douce", "constante"];
export const VUES = ["poids", "texture", "ombre", "fil"];
export const OPERATIONS = ["orphelins", "confinement", "epaules", "coutures", "guerison", "tout"];

/* le clavier de Sorceress (QWERTY : R, A, S, D, F) ; `e.key` en minuscule */
export const TOUCHES = {
  "1": { outil: "os" }, "2": { outil: "peindre" }, "3": { outil: "lasso" }, p: { outil: "pose" },
  r: { mode: "fixer" }, a: { mode: "ajouter" }, s: { mode: "retirer" }, d: { mode: "lisser" }, f: { mode: "flouter" },
  m: { bascule: "miroir" }, "4": { panneau: "os" }, "5": { bascule: "isoler" },
  "[": { taille: -1 }, "]": { taille: 1 },
};
export const EGAL = 1e-9;

export function action(e) {
  if (!e || e.altKey || e.metaKey) return null;
  const k = String(e.key || "").toLowerCase();
  if ((e.ctrlKey) && (k === "z" || k === "y")) return { histoire: k === "z" && !e.shiftKey ? "annuler" : "retablir" };
  if (e.ctrlKey) return null;
  return TOUCHES[k] || null;
}

/* ── un sommet : {os: poids} ↔ quatre places ──────────────────────────────── */

export function creerPoids(j, w, n = Math.floor(j.length / 4)) {
  return { n, j: Uint16Array.from(j.slice(0, n * 4)), w: Float32Array.from(w.slice(0, n * 4)) };
}

export function lire(P, v) {
  const o = {};
  for (let k = 0; k < 4; k++) {
    const x = P.w[v * 4 + k];
    if (x > 0) o[P.j[v * 4 + k]] = (o[P.j[v * 4 + k]] || 0) + x;
  }
  return o;
}

/* quatre influences au plus, triées, somme 1 ; une ÉGALITÉ à la coupe n'est jamais tranchée par l'index (le miroir
   gauche/droite resterait asymétrique) : les ex æquo partent ensemble — même règle que poids_corrections.py */
export function normaliser(o, maxi = 4) {
  let items = Object.entries(o).map(([k, x]) => [Number(k), x]).filter(([, x]) => x > 1e-6);
  items.sort((a, b) => b[1] - a[1] || a[0] - b[0]);
  if (items.length > maxi) {
    const coupe = items[maxi][1];
    const gardes = items.slice(0, maxi).filter(([, x]) => x > coupe + EGAL);
    items = gardes.length ? gardes : items.slice(0, maxi);
  }
  const s = items.reduce((a, [, x]) => a + x, 0);
  const out = {};
  if (s <= 1e-6) return out;
  for (const [k, x] of items) out[k] = x / s;
  return out;
}

export function ecrire(P, v, o) {
  const items = Object.entries(normaliser(o)).map(([k, x]) => [Number(k), x]).sort((a, b) => b[1] - a[1] || a[0] - b[0]);
  if (!items.length) return false;              // jamais un sommet vide : on refuse l'écriture
  for (let k = 0; k < 4; k++) {
    P.j[v * 4 + k] = k < items.length ? items[k][0] : 0;
    P.w[v * 4 + k] = k < items.length ? items[k][1] : 0;
  }
  return true;
}

export function poidsDe(P, v, os) {
  let s = 0;
  for (let k = 0; k < 4; k++) if (P.j[v * 4 + k] === os) s += P.w[v * 4 + k];
  return s;
}

export function somme(P, v) {
  let s = 0;
  for (let k = 0; k < 4; k++) s += P.w[v * 4 + k];
  return s;
}

/* fixe le poids de `os` à `valeur` ; les autres os gardent leurs proportions sur 1 − valeur. S'il n'y en a pas, le
   reste va à `repli` (le parent de l'os) ; sans repli, l'os garde tout. */
export function fixer(o, os, valeur, repli = null) {
  const x = Math.min(1, Math.max(0, valeur));
  const autres = Object.entries(o).filter(([k]) => Number(k) !== os);
  const s = autres.reduce((a, [, y]) => a + y, 0);
  const out = {};
  if (s > 1e-6) {
    if (x < 1) for (const [k, y] of autres) out[k] = (y / s) * (1 - x);
    if (x > 0) out[os] = x;
  } else if (x < 1 && repli != null && repli !== os) {
    out[os] = x;
    out[repli] = 1 - x;
  } else {
    out[os] = 1;
  }
  return out;
}

/* ── l'atténuation et le pinceau ──────────────────────────────────────────── */

export function attenuation(t, type = "douce") {
  if (!(t >= 0) || t > 1) return 0;
  if (type === "constante") return 1;
  if (type === "lineaire") return 1 - t;
  return 1 - t * t * (3 - 2 * t);     // douce : smoothstep inversé
}

export function dansRayon(positions, n, c, r, type = "douce") {
  const out = [];
  const r2 = r * r;
  for (let v = 0; v < n; v++) {
    const dx = positions[v * 3] - c[0], dy = positions[v * 3 + 1] - c[1], dz = positions[v * 3 + 2] - c[2];
    const d2 = dx * dx + dy * dy + dz * dz;
    if (d2 <= r2) {
      const f = attenuation(Math.sqrt(d2) / r, type);
      if (f > 0) out.push([v, f]);
    }
  }
  return out;
}

/* le nouveau {os: poids} d'un sommet sous une opération ; `voisin` : la moyenne des voisins ({os: poids}) */
export function operer(o, mode, os, force, f, voisin = null, repli = null) {
  const a = Math.min(1, Math.max(0, force)) * f;
  const w = o[os] || 0;
  if (mode === "fixer") return fixer(o, os, w + (force - w) * f, repli);
  if (mode === "ajouter") return fixer(o, os, w + a, repli);
  if (mode === "retirer") return fixer(o, os, w - a, repli);
  if (mode === "lisser") {
    if (!voisin) return o;
    return fixer(o, os, w + ((voisin[os] || 0) - w) * a, repli);
  }
  if (mode === "flouter") {
    if (!voisin) return o;
    const out = {};
    for (const [k, x] of Object.entries(o)) out[k] = (1 - a) * x;
    for (const [k, x] of Object.entries(voisin)) out[k] = (out[k] || 0) + a * x;
    return out;
  }
  return o;
}

/* ── soudure et adjacence ─────────────────────────────────────────────────── */

/* deux sommets de même position (couture d'UV) : un seul représentant. Int32Array n → plus petit sommet du groupe */
export function souder(positions, n, eps = 1e-6) {
  const canon = new Int32Array(n);
  const vus = new Map();
  for (let v = 0; v < n; v++) {
    const cle = `${Math.round(positions[v * 3] / eps)},${Math.round(positions[v * 3 + 1] / eps)},${Math.round(positions[v * 3 + 2] / eps)}`;
    const c = vus.get(cle);
    if (c === undefined) { vus.set(cle, v); canon[v] = v; } else canon[v] = c;
  }
  return canon;
}

/* l'adjacence des représentants (CSR : debut[n + 1], liste) à partir des triangles (index, ou séquentiels) */
export function adjacence(index, n, canon) {
  const ens = Array.from({ length: n }, () => null);
  const ajouter = (a, b) => {
    if (a === b) return;
    (ens[a] = ens[a] || new Set()).add(b);
    (ens[b] = ens[b] || new Set()).add(a);
  };
  const m = index ? index.length : n;
  for (let t = 0; t + 2 < m; t += 3) {
    const a = canon[index ? index[t] : t], b = canon[index ? index[t + 1] : t + 1], c = canon[index ? index[t + 2] : t + 2];
    ajouter(a, b); ajouter(b, c); ajouter(c, a);
  }
  const debut = new Int32Array(n + 1);
  for (let v = 0; v < n; v++) debut[v + 1] = debut[v] + (ens[v] ? ens[v].size : 0);
  const liste = new Int32Array(debut[n]);
  for (let v = 0; v < n; v++) if (ens[v]) { let k = debut[v]; for (const x of ens[v]) liste[k++] = x; }
  return { debut, liste, canon };
}

export function voisins(adj, v) {
  const c = adj.canon[v];
  return adj.liste.subarray(adj.debut[c], adj.debut[c + 1]);
}

export function moyenneVoisins(P, adj, v) {
  const vs = voisins(adj, v);
  if (!vs.length) return null;
  const out = {};
  for (const q of vs) for (const [k, x] of Object.entries(lire(P, q))) out[k] = (out[k] || 0) + x / vs.length;
  return out;
}

/* ── le miroir ────────────────────────────────────────────────────────────── */

/* le sommet miroir (x → 2·axe − x) de chaque sommet : le PLUS PROCHE du reflet à moins de `tol`, −1 sinon. Un modèle
   généré n'est jamais exactement symétrique : la tolérance se règle sur la résolution du maillage (affiner.js : 1 %
   de la taille), et la grille de cases de côté `tol` ne fouille que les 27 cases voisines du reflet. */
export function carteMiroir(positions, n, axe = 0, tol = 1e-4) {
  const c = (x) => Math.floor(x / tol);
  const table = new Map();
  for (let v = 0; v < n; v++) {
    const k = `${c(positions[v * 3])},${c(positions[v * 3 + 1])},${c(positions[v * 3 + 2])}`;
    const l = table.get(k);
    if (l) l.push(v); else table.set(k, [v]);
  }
  const out = new Int32Array(n).fill(-1);
  const t2 = tol * tol;
  for (let v = 0; v < n; v++) {
    const x = 2 * axe - positions[v * 3], y = positions[v * 3 + 1], z = positions[v * 3 + 2];
    const cx = c(x), cy = c(y), cz = c(z);
    let best = -1, bd = t2;
    for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) for (let k = -1; k <= 1; k++) {
      for (const u of table.get(`${cx + i},${cy + j},${cz + k}`) || []) {
        const dx = positions[u * 3] - x, dy = positions[u * 3 + 1] - y, dz = positions[u * 3 + 2] - z;
        const d = dx * dx + dy * dy + dz * dz;
        if (d <= bd && (best < 0 || d < bd || u < best)) { bd = d; best = u; }
      }
    }
    out[v] = best;
  }
  return out;
}

/* la longueur moyenne des arêtes (adjacence soudée) : l'échelle du maillage, qui règle la tolérance du miroir */
export function areteMoyenne(positions, adj, max = 20000) {
  let s = 0, k = 0;
  const n = adj.debut.length - 1;
  for (let v = 0; v < n && k < max; v++) {
    for (let i = adj.debut[v]; i < adj.debut[v + 1] && k < max; i++) {
      const u = adj.liste[i];
      if (u <= v) continue;
      s += Math.hypot(positions[u * 3] - positions[v * 3], positions[u * 3 + 1] - positions[v * 3 + 1], positions[u * 3 + 2] - positions[v * 3 + 2]);
      k++;
    }
  }
  return k ? s / k : 0;
}

const COTES = [[/_l$/i, "_r"], [/_r$/i, "_l"], [/\.l$/i, ".R"], [/\.r$/i, ".L"]];
/* le nom de l'os miroir : suffixes _l/_r, .L/.R, préfixes Left/Right (Mixamo), sinon lui-même */
export function nomMiroir(nom) {
  const s = String(nom);
  for (const [re, rep] of COTES) {
    if (re.test(s)) {
      const fin = s.slice(-2);
      const neuf = rep[0] + (fin[1] === fin[1].toUpperCase() ? rep[1].toUpperCase() : rep[1].toLowerCase());
      return s.slice(0, -2) + neuf;
    }
  }
  if (/left/i.test(s)) return s.replace(/left/i, (m) => (m[0] === "L" ? "Right" : m === "LEFT" ? "RIGHT" : "right"));
  if (/right/i.test(s)) return s.replace(/right/i, (m) => (m[0] === "R" ? "Left" : m === "RIGHT" ? "LEFT" : "left"));
  return s;
}

export function osMiroir(noms) {
  const idx = new Map(noms.map((n, i) => [n, i]));
  return Int32Array.from(noms.map((n, i) => { const m = idx.get(nomMiroir(n)); return m === undefined ? i : m; }));
}

/* ── le trait : un pas de pinceau, enregistré pour annuler ────────────────── */

export function debutTrait() { return { avant: new Map() }; }

function noter(tr, P, v) {
  if (tr && !tr.avant.has(v)) tr.avant.set(v, [P.j.slice(v * 4, v * 4 + 4), P.w.slice(v * 4, v * 4 + 4)]);
}

export function finTrait(tr, P) {
  if (!tr || !tr.avant.size) return null;
  const sommets = Int32Array.from([...tr.avant.keys()].sort((a, b) => a - b));
  const k = sommets.length;
  const d = { sommets, avantJ: new Uint16Array(k * 4), avantW: new Float32Array(k * 4),
    apresJ: new Uint16Array(k * 4), apresW: new Float32Array(k * 4) };
  sommets.forEach((v, i) => {
    const [aj, aw] = tr.avant.get(v);
    d.avantJ.set(aj, i * 4); d.avantW.set(aw, i * 4);
    d.apresJ.set(P.j.subarray(v * 4, v * 4 + 4), i * 4); d.apresW.set(P.w.subarray(v * 4, v * 4 + 4), i * 4);
  });
  return d;
}

/* un coup de pinceau (ou un lasso : `touches` = [[v, f]]). Jacobi : lisser et flouter lisent les poids d'AVANT le pas.
   opts : {mode, os, force, repli, adj, miroir (Int32Array|null : sommet miroir), osM (Int32Array|null : os miroir),
   verrou (Set de sommets qu'on ne touche pas, l'isolement)} ; rend les sommets modifiés */
export function appliquer(P, touches, opts, tr = null) {
  const { mode, os, force, repli = null, adj = null, miroir = null, osM = null, verrou = null } = opts;
  const travaux = new Map();            // sommet → [[os, f, repli], …] (deux au plus : le sien et celui de son miroir)
  const ajouter = (v, o, f, r) => {
    const l = travaux.get(v) || [];
    if (!l.some(([o2, f2]) => o2 === o && f2 === f)) l.push([o, f, r]);
    travaux.set(v, l);
  };
  for (const [v, f] of touches) {
    ajouter(v, os, f, repli);
    if (miroir && miroir[v] >= 0) ajouter(miroir[v], osM ? osM[os] : os, f, osM && repli != null ? osM[repli] : repli);
  }
  const avant = new Map();
  if (mode === "lisser" || mode === "flouter") for (const v of travaux.keys()) avant.set(v, moyenneVoisins(P, adj, v));
  const faits = new Set();
  for (const [v, ops] of travaux) {
    if (verrou && verrou.has(v)) continue;
    const o = lire(P, v), vois = avant.get(v) || null;
    const un = (x, [b, f, r]) => normaliser(operer(x, mode, b, force, f, vois, r));
    let neuf;
    if (ops.length === 1) neuf = un(o, ops[0]);
    else {
      /* deux gestes sur un même sommet (le sien et le reflet d'un autre, ou un sommet sur l'axe) : la moyenne des
         deux ordres, sans quoi l'ordre de parcours casserait la symétrie gauche/droite */
      const ab = un(un(o, ops[0]), ops[1]), ba = un(un(o, ops[1]), ops[0]);
      neuf = {};
      for (const [k, x] of Object.entries(ab)) neuf[k] = x / 2;
      for (const [k, x] of Object.entries(ba)) neuf[k] = (neuf[k] || 0) + x / 2;
    }
    noter(tr, P, v);
    if (ecrire(P, v, neuf)) faits.add(v);
  }
  return [...faits].sort((a, b) => a - b);
}

/* ── l'historique ─────────────────────────────────────────────────────────── */

/* une entrée = un trait (delta de finTrait) ou un trait sur plusieurs maillages : {parts: [{cle, d}]} ; `P` est alors
   une fonction cle → P. annuler / retablir rendent les sommets rendus (ou [{cle, sommets}] pour un trait composé). */
export class Historique {
  constructor(max = 200) { this.pile = []; this.pos = 0; this.max = max; }
  pousser(d) {
    if (!d || (d.parts && !d.parts.length)) return;
    this.pile.length = this.pos;
    this.pile.push(d);
    if (this.pile.length > this.max) this.pile.shift();
    this.pos = this.pile.length;
  }
  get peutAnnuler() { return this.pos > 0; }
  get peutRetablir() { return this.pos < this.pile.length; }
  _poser(P, d, apres) {
    if (d.parts) return d.parts.map(({ cle, d: x }) => ({ cle, sommets: this._poser(P(cle), x, apres) }));
    const j = apres ? d.apresJ : d.avantJ, w = apres ? d.apresW : d.avantW;
    d.sommets.forEach((v, i) => { P.j.set(j.subarray(i * 4, i * 4 + 4), v * 4); P.w.set(w.subarray(i * 4, i * 4 + 4), v * 4); });
    return [...d.sommets];
  }
  annuler(P) {
    if (!this.peutAnnuler) return [];
    return this._poser(P, this.pile[--this.pos], false);
  }
  retablir(P) {
    if (!this.peutRetablir) return [];
    return this._poser(P, this.pile[this.pos++], true);
  }
  vider() { this.pile = []; this.pos = 0; }
}

/* ── lasso, sommets sans poids, isolement, couleurs ───────────────────────── */

export function dansPolygone(x, y, poly) {
  let dedans = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) dedans = !dedans;
  }
  return dedans;
}

/* `ecran` : Float32Array n·2 (pixels) ; `visible` : Uint8Array n facultatif (0 : sommet caché, voir visibles) */
export function selectionLasso(ecran, n, poly, visible = null) {
  if (!poly || poly.length < 3) return [];
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [x, y] of poly) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
  const out = [];
  for (let v = 0; v < n; v++) {
    if (visible && !visible[v]) continue;
    const x = ecran[v * 2], y = ecran[v * 2 + 1];
    if (x < x0 || x > x1 || y < y0 || y > y1) continue;
    if (dansPolygone(x, y, poly)) out.push(v);
  }
  return out;
}

/* ── l'occlusion du lasso : un tampon de profondeur logiciel ──────────────── */

/* t405 — Sorceress : « Lasso select polygons (3) — drag on the model ». Le lasso ne prend que les sommets VUS : les
   triangles (déformés, projetés) de tous les maillages sont rastérisés dans un tampon de profondeur (profondeur de
   vue, en unités du modèle), restreint à la boîte du lasso ; un sommet est visible si sa profondeur ne dépasse pas
   de plus de `eps` la PLUS LOINTAINE des surfaces les plus proches de son voisinage 3 × 3 (un sommet de silhouette,
   ou un triangle plus petit qu'un pixel, n'est pas caché à tort par son propre bord). Choisi contre un lancer de
   rayon par candidat (BVH absente du projet) et une passe GPU (lecture de pixels, nuanceur de peau à dupliquer) :
   le calcul vit ici, sous node : ~ 12 ms pour 50 000 sommets et 100 000 triangles (banc qa/affiner.test.mjs). */

export function boitePolygone(poly, W, H, marge = 2) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [x, y] of poly) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
  return [Math.max(0, Math.floor(x0) - marge), Math.max(0, Math.floor(y0) - marge),
    Math.min(W - 1, Math.ceil(x1) + marge), Math.min(H - 1, Math.ceil(y1) + marge)];
}

export function tamponProfondeur(W, H, boite = null) {
  const w = Math.max(1, Math.ceil(W)), h = Math.max(1, Math.ceil(H));
  const [x0, y0, x1, y1] = boite || [0, 0, w - 1, h - 1];
  return { W: w, H: h, x0: Math.max(0, x0), y0: Math.max(0, y0), x1: Math.min(w - 1, x1), y1: Math.min(h - 1, y1),
    z: new Float32Array(w * h).fill(Infinity) };
}

/* les triangles (index, ou séquentiels) d'un maillage dans le tampon ; `prof` : profondeur de vue (> 0 devant la
   caméra), les triangles qui passent derrière elle sont ignorés */
export function rasteriser(tb, ecran, prof, index, n) {
  const { W, z, x0, y0, x1, y1 } = tb;
  const m = index ? index.length : n;
  for (let t = 0; t + 2 < m; t += 3) {
    const a = index ? index[t] : t, b = index ? index[t + 1] : t + 1, c = index ? index[t + 2] : t + 2;
    const za = prof[a], zb = prof[b], zc = prof[c];
    if (!(za > 0 && zb > 0 && zc > 0)) continue;
    const ax = ecran[a * 2], ay = ecran[a * 2 + 1], bx = ecran[b * 2], by = ecran[b * 2 + 1], cx = ecran[c * 2], cy = ecran[c * 2 + 1];
    const mx = Math.max(x0, Math.floor(Math.min(ax, bx, cx))), Mx = Math.min(x1, Math.ceil(Math.max(ax, bx, cx)));
    if (mx > Mx) continue;
    const my = Math.max(y0, Math.floor(Math.min(ay, by, cy))), My = Math.min(y1, Math.ceil(Math.max(ay, by, cy)));
    if (my > My) continue;
    const aire = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
    if (Math.abs(aire) < 1e-12) continue;
    const inv = 1 / aire;
    for (let y = my; y <= My; y++) {
      const py = y + 0.5;
      for (let x = mx; x <= Mx; x++) {
        const px = x + 0.5;
        const wa = ((bx - px) * (cy - py) - (by - py) * (cx - px)) * inv;
        if (wa < -1e-7) continue;
        const wb = ((cx - px) * (ay - py) - (cy - py) * (ax - px)) * inv;
        if (wb < -1e-7) continue;
        const wc = 1 - wa - wb;
        if (wc < -1e-7) continue;
        const zz = wa * za + wb * zb + wc * zc, k = y * W + x;
        if (zz < z[k]) z[k] = zz;
      }
    }
  }
}

/* Uint8Array n : 1 si le sommet est vu (ou hors de la boîte du tampon, qu'on n'a pas regardée), 0 s'il est caché */
export function visibles(tb, ecran, prof, n, eps) {
  const { W, z, x0, y0, x1, y1 } = tb;
  const out = new Uint8Array(n).fill(1);
  for (let v = 0; v < n; v++) {
    const x = Math.floor(ecran[v * 2]), y = Math.floor(ecran[v * 2 + 1]);
    if (x < x0 || x > x1 || y < y0 || y > y1) continue;
    if (!(prof[v] > 0)) { out[v] = 0; continue; }
    let loin = -Infinity;
    for (let j = Math.max(y0, y - 1); j <= Math.min(y1, y + 1); j++) {
      for (let i = Math.max(x0, x - 1); i <= Math.min(x1, x + 1); i++) { const q = z[j * W + i]; if (q > loin) loin = q; }
    }
    if (prof[v] > loin + eps) out[v] = 0;
  }
  return out;
}

/* le lasso sur plusieurs maillages : [{ecran, prof, index, n}] → une sélection par maillage. `travers` : l'ancien
   comportement (tout ce qui est entouré, devant comme derrière). Rend {selections, ms}. */
export function lassoMaillages(maillages, poly, W, H, { travers = false, eps = 0 } = {}) {
  const t0 = typeof performance !== "undefined" ? performance.now() : Date.now();
  if (!poly || poly.length < 3) return { selections: maillages.map(() => []), ms: 0 };
  let vis = maillages.map(() => null);
  if (!travers) {
    const tb = tamponProfondeur(W, H, boitePolygone(poly, W, H));
    for (const m of maillages) rasteriser(tb, m.ecran, m.prof, m.index, m.n);
    vis = maillages.map((m) => visibles(tb, m.ecran, m.prof, m.n, eps));
  }
  const selections = maillages.map((m, k) => selectionLasso(m.ecran, m.n, poly, vis[k]));
  const t1 = typeof performance !== "undefined" ? performance.now() : Date.now();
  return { selections, ms: t1 - t0 };
}

export function sansPoids(P) {
  const out = [];
  for (let v = 0; v < P.n; v++) if (somme(P, v) < 1e-6) out.push(v);
  return out;
}

/* les sommets que l'isolement protège : ceux que l'os choisi ne touche pas (on ne peint que sur son domaine) */
export function horsDomaine(P, os) {
  const s = new Set();
  for (let v = 0; v < P.n; v++) if (poidsDe(P, v, os) <= 0) s.add(v);
  return s;
}

/* la carte de chaleur : 0 bleu nuit → cyan → vert → jaune → 1 rouge */
const PALETTE = [[0.05, 0.08, 0.32], [0.0, 0.65, 0.9], [0.1, 0.8, 0.3], [0.98, 0.85, 0.1], [0.92, 0.12, 0.1]];
export function chaleur(w) {
  const t = Math.min(1, Math.max(0, w)) * (PALETTE.length - 1);
  const i = Math.min(PALETTE.length - 2, Math.floor(t)), u = t - i;
  return PALETTE[i].map((c, k) => c + (PALETTE[i + 1][k] - c) * u);
}

export function couleurs(P, os, { isoler = false, sortie = null, sansPoidsRouge = true } = {}) {
  const c = sortie || new Float32Array(P.n * 3);
  for (let v = 0; v < P.n; v++) {
    const w = poidsDe(P, v, os);
    let rgb;
    if (sansPoidsRouge && somme(P, v) < 1e-6) rgb = [1, 0, 1];          // magenta : aucun os ne tient ce sommet
    else if (isoler && w <= 0) rgb = [0.16, 0.16, 0.18];
    else rgb = chaleur(w);
    c[v * 3] = rgb[0]; c[v * 3 + 1] = rgb[1]; c[v * 3 + 2] = rgb[2];
  }
  return c;
}

/* ── réglages au clavier et à la molette ──────────────────────────────────── */

export const TAILLE = { min: 0.002, max: 2, pas: 1.15 };
export function ajusterTaille(r, sens, hauteur = 1) {
  const lo = TAILLE.min * hauteur, hi = TAILLE.max * hauteur;
  return Math.min(hi, Math.max(lo, sens > 0 ? r * TAILLE.pas : r / TAILLE.pas));
}
export function ajusterForce(f, sens) {
  return Math.round(Math.min(1, Math.max(0.01, f + (sens > 0 ? 0.05 : -0.05))) * 100) / 100;
}

/* ── les rôles des os (comme mouvement_rig.role) pour les poses d'essai ───── */

export function role(nom) {
  let s = String(nom).replace(/^.*[:|]/, "").replace(/^([LR])([A-Z][a-z])/, "$1_$2").replace(/([a-z0-9])([A-Z])/g, "$1_$2");
  let cote = null;
  const reste = [];
  for (const t of s.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)) {
    if (t === "left" || t === "l") cote = "g";
    else if (t === "right" || t === "r") cote = "d";
    else if (!["mixamorig", "bip", "bip01", "def", "org", "mch", "jnt", "joint", "bone"].includes(t)) reste.push(t);
  }
  let base = reste.join("");
  for (const [pre, c] of [["left", "g"], ["right", "d"]]) if (base.startsWith(pre) && base.length > pre.length) { cote = c; base = base.slice(pre.length); }
  const A = { epaule: ["shoulder", "clavicle", "collar", "collarbone"], bras: ["arm", "upperarm", "uparm"],
    avantbras: ["forearm", "lowerarm", "lowarm"], main: ["hand", "wrist"], cuisse: ["upleg", "thigh", "upperleg"],
    jambe: ["leg", "shin", "calf", "lowerleg"], pied: ["foot", "ankle"], cou: ["neck", "neck01", "neck1"], tete: ["head"],
    bassin: ["hips", "pelvis"] };
  for (const [r, al] of Object.entries(A)) {
    if (al.includes(base)) {
      if (r === "cou" || r === "tete" || r === "bassin") return cote ? null : r;
      return cote ? `${r}_${cote}` : null;
    }
  }
  if (!cote && /^(spine|chest|upperchest)/.test(base)) return "colonne";
  return null;
}

/* les POSES D'ESSAI (la batterie d'amplitude de poids_corrections.py, à voir sur le modèle) : rôle → rotation locale
   en degrés (X, Y, Z) ; le côté droit en miroir (Y et Z changent de signe) */
export const POSES = {
  bras_leves: [["bras", [0, 0, -60]]], bras_avant: [["bras", [0, -60, 0]]], coudes: [["avantbras", [0, -100, 0]]],
  hanches: [["cuisse", [-80, 0, 0]]], genoux: [["jambe", [100, 0, 0]]], cou: [["cou", [35, 0, 0]]],
  torsion: [["colonne", [0, 15, 0]]],
};
export function rotationsDePose(nomPose, noms) {
  const out = {};
  for (const [r, [x, y, z]] of POSES[nomPose] || []) {
    for (const n of noms) {
      const ro = role(n);
      if (ro === `${r}_g`) out[n] = [x, y, z];
      else if (ro === `${r}_d`) out[n] = [x, -y || 0, -z || 0];
      else if (ro === r) out[n] = [x, y, z];
    }
  }
  return out;
}

/* le quaternion LOCAL d'une pose, relatif au repos : conj(repos) · posé (ce que poids_corrections attend) */
export function quatRelatif(qr, qp) {
  const [x1, y1, z1, w1] = [-qr[0], -qr[1], -qr[2], qr[3]];
  const [x2, y2, z2, w2] = qp;
  return [w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
    w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2];
}

/* ── les corps de requête ─────────────────────────────────────────────────── */

/* maillages : [{mesh, primitive, P, sales: Set}] → le corps de POST /enregistrer (les seuls sommets touchés) */
export function corpsEnregistrer(version, maillages) {
  const modifs = [];
  for (const m of maillages) {
    if (!m.sales || !m.sales.size) continue;
    const sommets = [...m.sales].sort((a, b) => a - b);
    const joints = [], poids = [];
    for (const v of sommets) for (let k = 0; k < 4; k++) { joints.push(m.P.j[v * 4 + k]); poids.push(Math.round(m.P.w[v * 4 + k] * 1e6) / 1e6); }
    modifs.push({ mesh: m.mesh, primitive: m.primitive, sommets, joints, poids });
  }
  return { version, modifs };
}

export function corpsCorriger(version, operation, { os = null, parametres = {} } = {}) {
  const c = { version, operation, parametres: { ...parametres } };
  if (os) c.os = os;
  return c;
}

/* le compte rendu d'une correction, en une ligne lisible (clé i18n + variables) */
export function resumeRapport(r) {
  if (!r) return null;
  const op = r.correction;
  if (op === "orphelins") return { cle: "aff.rap_orphelins", v: { n: r.ilots || 0 } };
  if (op === "confinement") return { cle: "aff.rap_confinement", v: { n: r.points || 0 } };
  if (op === "epaules") return { cle: "aff.rap_epaules", v: { n: r.points || 0 } };
  if (op === "coutures") return { cle: "aff.rap_coutures", v: { n: (r.coutures && r.coutures.collier) || 0 } };
  if (op === "guerison") {
    const g = r.guerison || [];
    return { cle: "aff.rap_guerison", v: { a: g.reduce((s, x) => s + x.avant, 0), b: g.reduce((s, x) => s + x.apres, 0), p: g.length } };
  }
  if (op === "tout") return { cle: "aff.rap_tout", v: { n: r.points || 0 } };
  return null;
}
