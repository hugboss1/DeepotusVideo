/* t405 (31/10/2026) — la CINÉMATIQUE INVERSE des poignées ambre de l'outil Pose (écran Affiner), sans DOM ni
   three.js : elle tourne sous node (banc qa/affiner.test.mjs). affiner.js lit les positions MONDE des os, appelle ces
   fonctions, puis pose les rotations monde rendues sur les os (parent⁻¹ · delta · monde).

   Relevé de Sorceress (§6, Refine) : « Pose bones (P) — click a bone to rotate; drag amber IK handles ». Chez nous :
   - bras et jambes : IK ANALYTIQUE à deux os (haut du membre, bas du membre, effecteur main / pied). Le plan de pli
     vient du pli COURANT (le coude reste du côté où il est) ; un membre tendu, ou plié à l'envers, prend le côté
     NATUREL (coude vers l'arrière, genou vers l'avant) : jamais de genou ni de coude retourné. Un pli minimal
     (angle intérieur ≥ 20°) empêche le membre de se replier sur lui-même ; une cible hors de portée tend le membre
     DROIT vers elle.
   - la tête : CCD (descente cyclique des coordonnées) sur la chaîne colonne → cou, chaque articulation bornée
     (angle relatif à son parent, mesuré depuis le début du geste).
   Vecteurs [x, y, z], quaternions [x, y, z, w] (convention three.js : q · v · q⁻¹). */
"use strict";

export const PLI_MIN = 20;              // angle intérieur minimal au coude / genou (degrés)
export const LIMITE_COLONNE = 30;       // rotation maximale d'une vertèbre (ou du cou) pendant un geste (degrés)

/* ── vecteurs ─────────────────────────────────────────────────────────────── */

export const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
export const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export const len = (a) => Math.hypot(a[0], a[1], a[2]);
export const dist = (a, b) => len(sub(a, b));
export function norm(a) { const l = len(a); return l > 1e-12 ? mul(a, 1 / l) : [0, 0, 0]; }

/* la part de `v` perpendiculaire à l'axe unitaire `u` */
export const perp = (v, u) => sub(v, mul(u, dot(v, u)));

/* ── quaternions ──────────────────────────────────────────────────────────── */

export const ID = [0, 0, 0, 1];
export function qmul(a, b) {
  return [a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1], a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
    a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3], a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]];
}
export const qconj = (q) => [-q[0], -q[1], -q[2], q[3]];
export function qrot(q, v) {
  const r = qmul(qmul(q, [v[0], v[1], v[2], 0]), qconj(q));
  return [r[0], r[1], r[2]];
}
/* l'angle (radians, 0..π) d'une rotation */
export const qangle = (q) => 2 * Math.acos(Math.min(1, Math.abs(q[3])));

/* la rotation la plus courte qui amène le vecteur unitaire `u` sur `v` */
export function qDeVers(u, v) {
  const d = dot(u, v);
  if (d < -1 + 1e-10) {                       // opposés : un demi-tour autour d'un axe perpendiculaire quelconque
    let ax = cross([1, 0, 0], u);
    if (len(ax) < 1e-6) ax = cross([0, 1, 0], u);
    ax = norm(ax);
    return [ax[0], ax[1], ax[2], 0];
  }
  const c = cross(u, v);
  const q = [c[0], c[1], c[2], 1 + d];
  const l = Math.hypot(...q);
  return q.map((x) => x / l);
}

/* une fraction `t` (0..1) de la rotation q (depuis l'identité) */
export function qfraction(q, t) {
  const s = q[3] < 0 ? -1 : 1;                // le plus court chemin
  const w = Math.min(1, s * q[3]), a = Math.acos(w);
  if (a < 1e-9) return [...ID];
  const k = Math.sin(a * t) / Math.sin(a);
  return [s * q[0] * k, s * q[1] * k, s * q[2] * k, Math.cos(a * t)];
}

/* ── deux os : bras (épaule, coude, poignet) ou jambe (hanche, genou, cheville) ─ */

/* a, b, c : positions monde du haut du membre, du milieu (coude / genou), de l'effecteur ; cible : où mener c.
   opts : {naturel : direction de pli naturelle (coude → arrière, genou → avant), pliMin (degrés)}.
   Rend {milieu, bout, qHaut, qBas, atteint, plan} : qHaut (rotation monde du haut du membre) amène b sur `milieu` ;
   qBas, appliquée APRÈS qHaut au bas du membre (il en hérite), amène l'effecteur sur `bout`. */
export function deuxOs(a, b, c, cible, { naturel = null, pliMin = PLI_MIN } = {}) {
  const l1 = dist(a, b), l2 = dist(b, c), t = sub(cible, a), dBrut = len(t);
  if (l1 < 1e-9 || l2 < 1e-9 || dBrut < 1e-9) return { milieu: [...b], bout: [...c], qHaut: [...ID], qBas: [...ID], atteint: false, plan: null };
  const dir = mul(t, 1 / dBrut);
  const cMin = Math.cos((Math.max(0, Math.min(179, pliMin)) * Math.PI) / 180);
  const dMin = Math.max(Math.abs(l1 - l2), Math.sqrt(Math.max(0, l1 * l1 + l2 * l2 - 2 * l1 * l2 * cMin)));
  const dMax = l1 + l2;
  const d = Math.min(dMax, Math.max(dMin, dBrut));
  /* le côté du pli : le pli courant (le milieu hors de la droite haut → bout) ; tendu, ou retourné contre le côté
     naturel, il prend le côté naturel */
  const ligne = norm(sub(c, a));
  let pole = perp(sub(b, a), ligne);
  const nat = naturel ? norm(naturel) : null;
  if (len(pole) < 1e-4 * l1 || (nat && dot(pole, nat) < 0)) pole = nat || pole;
  let pn = perp(pole, dir);
  if (len(pn) < 1e-9) {                       // pôle aligné sur la cible : n'importe quelle perpendiculaire
    pn = cross(dir, [0, 1, 0]);
    if (len(pn) < 1e-6) pn = cross(dir, [1, 0, 0]);
  }
  pn = norm(pn);
  const cosA = Math.max(-1, Math.min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)));
  const sinA = Math.sqrt(Math.max(0, 1 - cosA * cosA));
  const milieu = add(a, mul(add(mul(dir, cosA), mul(pn, sinA)), l1));
  const bout = add(a, mul(dir, d));
  const qHaut = qDeVers(norm(sub(b, a)), norm(sub(milieu, a)));
  const bas = qrot(qHaut, sub(c, b));
  const qBas = qDeVers(norm(bas), norm(sub(bout, milieu)));
  return { milieu, bout, qHaut, qBas, atteint: dist(bout, cible) <= 1e-6 * Math.max(1, dMax), plan: pn };
}

/* ── CCD : la colonne jusqu'à la tête ─────────────────────────────────────── */

/* points : [p0 … pn] positions monde des articulations (p0 la première vertèbre, pn l'effecteur : la tête) ; les
   articulations 0..n−1 tournent. limites : degrés par articulation (nombre ou tableau), angle de sa rotation RELATIVE
   à son parent, depuis le début du geste. Rend {points, rotations : n quaternions MONDE cumulés (os i), atteint,
   distance}. Les longueurs ne changent jamais (que des rotations). */
export function ccd(points, cible, { iterations = 64, limites = LIMITE_COLONNE, tol = 1e-4 } = {}) {
  const P = points.map((p) => [...p]);
  const n = P.length - 1;
  const G = Array.from({ length: Math.max(0, n) }, () => [...ID]);
  const lim = (i) => ((Array.isArray(limites) ? limites[i] : limites) * Math.PI) / 180;
  const total = P.slice(1).reduce((s, p, i) => s + dist(p, P[i]), 0);
  const seuil = tol * Math.max(1, total);
  for (let it = 0; it < iterations && n > 0; it++) {
    if (dist(P[n], cible) <= seuil) break;
    for (let i = n - 1; i >= 0; i--) {
      const u = norm(sub(P[n], P[i])), v = norm(sub(cible, P[i]));
      if (len(u) < 0.5 || len(v) < 0.5) continue;
      let r = qDeVers(u, v);
      const parent = i > 0 ? G[i - 1] : ID;
      const relatif = (q) => qangle(qmul(qconj(parent), qmul(q, G[i])));
      if (relatif(r) > lim(i)) {              // la borne : la plus grande fraction de r qui la respecte
        let lo = 0, hi = 1;
        for (let k = 0; k < 24; k++) { const m = (lo + hi) / 2; if (relatif(qfraction(r, m)) <= lim(i)) lo = m; else hi = m; }
        r = qfraction(r, lo);
        if (relatif(r) > lim(i) + 1e-9) continue;   // déjà au-delà (ne s'aggrave pas)
      }
      for (let k = i; k < n; k++) G[k] = qmul(r, G[k]);
      for (let k = i + 1; k <= n; k++) P[k] = add(P[i], qrot(r, sub(P[k], P[i])));
    }
  }
  const distance = n > 0 ? dist(P[n], cible) : 0;
  return { points: P, rotations: G, atteint: distance <= seuil, distance };
}

/* les rotations monde CUMULÉES de ccd → la rotation à poser sur chaque os, de la racine vers la tête, sachant qu'un os
   hérite de celle de son parent : Δᵢ = Gᵢ · Gᵢ₋₁⁻¹ */
export function deltasEnChaine(G) {
  return G.map((g, i) => (i ? qmul(g, qconj(G[i - 1])) : [...g]));
}

/* ── les chaînes d'un squelette ───────────────────────────────────────────── */

/* os : [{nom, parent (nom|null), role}] → les poignées : main / pied (deux os au-dessus d'eux) et tête (la colonne et le
   cou jusqu'au bassin). Rend [{poignee, type: "membre"|"colonne", os: [noms de la racine à l'effecteur], naturel}]
   (naturel : "arriere" pour un coude, "avant" pour un genou). */
export function chaines(os, roleDe) {
  const par = new Map(os.map((o) => [o.nom, o]));
  const r = (n) => (n && par.has(n) ? roleDe(n) : null);
  const out = [];
  for (const o of os) {
    const ro = r(o.nom) || "";
    const m = /^(main|pied)_(g|d)$/.exec(ro);
    if (m) {
      const mi = o.parent && par.get(o.parent), ha = mi && mi.parent && par.get(mi.parent);
      if (!mi || !ha) continue;
      out.push({ poignee: o.nom, type: "membre", os: [ha.nom, mi.nom, o.nom], naturel: m[1] === "main" ? "arriere" : "avant" });
    } else if (ro === "tete") {
      const ch = [o.nom];
      let p = o.parent;
      while (p && par.has(p) && ["colonne", "cou"].includes(r(p))) { ch.unshift(p); p = par.get(p).parent; }
      if (ch.length >= 2) out.push({ poignee: o.nom, type: "colonne", os: ch, naturel: null });
    }
  }
  return out;
}
