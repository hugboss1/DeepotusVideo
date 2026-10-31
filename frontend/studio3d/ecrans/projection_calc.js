/* t394 (31/10/2026) — le CALCUL de la projection multi-vues de l'écran Texture (volet 2/2), sans DOM ni three.js :
   il tourne sous node (banc qa/projection.test.mjs). projection.js ne fait que lui fournir le maillage, les images et
   les matrices de three.js, puis peindre ce qu'il rend.

   Le chemin d'une texture auto : pour chaque vue, une caméra (cameraDePose) ; le modèle rendu de là part chez le
   modèle d'image ; l'image rendue revient et se PROJETTE sur l'atlas UV : chaque texel connaît sa position et sa
   normale 3D (rasteriserUV : les triangles dessinés dans l'espace UV), se projette dans chaque caméra
   (projeterPoint), n'y prend la couleur que s'il est VU (carteProfondeur : la profondeur la plus proche par pixel,
   rastérisée depuis la même caméra) et pèse max(0, n·v)^k ; les vues se fondent par moyenne pondérée, la vue au plus
   fort poids « possède » le texel (accumulerVue, finaliser).

   Puis les retouches, sur l'atlas peint : gomme (le texel d'origine revient), estomper, combler depuis les voisins
   (zone ou tout l'atlas : les texels qu'aucune vue n'a vus), soigner les coutures (les deux bords d'une couture UV
   moyennés), annuler / rétablir par carreaux mémorisés.

   Conventions : matrices 4×4 en COLONNES (comme three.js, e[col*4 + ligne]) ; UV glTF (origine en HAUT à gauche :
   texel (x, y) = (u·W, v·H), sans retournement, GLTFLoader pose flipY = false) ; images en lignes du haut vers le bas. */
"use strict";
import { direction } from "./texture_calc.js";

/* ── matrices ─────────────────────────────────────────────────────────────── */
const sous = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const vect = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const scal = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const unit = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };

/* la matrice de VUE d'une caméra posée en `oeil` qui regarde `cible` (l'inverse de son repère, comme lookAt) */
export function regarder(oeil, cible, haut = [0, 1, 0]) {
  const z = unit(sous(oeil, cible));
  let x = vect(haut, z);
  if (Math.hypot(...x) < 1e-9) x = vect([0, 0, 1], z);      // haut parallèle à la visée : un autre « haut »
  x = unit(x);
  const y = vect(z, x);
  return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -scal(x, oeil), -scal(y, oeil), -scal(z, oeil), 1];
}

/* la projection perspective d'OpenGL (celle de THREE.PerspectiveCamera), fov VERTICAL en degrés */
export function perspective(fov, aspect, pres, loin) {
  const f = 1 / Math.tan((fov * Math.PI) / 360);
  return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (loin + pres) / (pres - loin), -1, 0, 0, (2 * loin * pres) / (pres - loin), 0];
}

export function multiplier(a, b) {
  const o = new Array(16).fill(0);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
    let s = 0;
    for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k];
    o[c * 4 + r] = s;
  }
  return o;
}

export function matriceCamera({ oeil, cible, haut = [0, 1, 0], fov, aspect = 1, pres, loin }) {
  return multiplier(perspective(fov, aspect, pres, loin), regarder(oeil, cible, haut));
}

/* un point du monde dans l'image d'une caméra : (u, v) dans [0, 1] (v du HAUT vers le bas), `w` = la distance le
   long de la visée (le w du clip, positif devant la caméra) */
export function projeterPoint(M, x, y, z) {
  const cx = M[0] * x + M[4] * y + M[8] * z + M[12];
  const cy = M[1] * x + M[5] * y + M[9] * z + M[13];
  const cw = M[3] * x + M[7] * y + M[11] * z + M[15];
  if (!(cw > 1e-9)) return { u: NaN, v: NaN, w: cw, devant: false };
  return { u: (cx / cw) * 0.5 + 0.5, v: 0.5 - (cy / cw) * 0.5, w: cw, devant: true };
}

/* la caméra d'une pose de disposition autour de la sphère englobante {centre, rayon} : le modèle entier tient dans
   le cadre carré au zoom 1 (marge 8 %), la moitié au zoom 2 ; `decalage` monte ou descend la cible (× rayon) */
export const FOV = 30;
export function cameraDePose(p, sphere, fov = FOV) {
  const r = Math.max(1e-6, Number(sphere.rayon) || 1);
  const c = sphere.centre;
  const zoom = Math.max(0.25, Number(p.zoom) || 1);
  const cible = [c[0], c[1] + (Number(p.decalage) || 0) * r, c[2]];
  const d = direction(p);
  const distance = (r * 1.08) / Math.sin((fov * Math.PI) / 360) / zoom;
  const oeil = [cible[0] + d.x * distance, cible[1] + d.y * distance, cible[2] + d.z * distance];
  const pres = Math.max(distance - 2.2 * r, distance * 0.01), loin = distance + 2.2 * r;
  return { oeil, cible, haut: [0, 1, 0], fov, aspect: 1, pres, loin,
    M: matriceCamera({ oeil, cible, haut: [0, 1, 0], fov, aspect: 1, pres, loin }) };
}

/* la sphère englobante (boîte → centre, demi-diagonale) d'un nuage de positions [x, y, z, x, y, z…] */
export function sphereDe(positions) {
  const mn = [Infinity, Infinity, Infinity], mx = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < positions.length; i += 3) for (let k = 0; k < 3; k++) {
    const v = positions[i + k];
    if (v < mn[k]) mn[k] = v;
    if (v > mx[k]) mx[k] = v;
  }
  if (!(mn[0] <= mx[0])) return { centre: [0, 0, 0], rayon: 1 };
  const centre = [0, 1, 2].map((k) => (mn[k] + mx[k]) / 2);
  return { centre, rayon: Math.max(1e-6, Math.hypot(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]) / 2) };
}

/* ── la taille de l'atlas : celle de la texture d'origine, bornée à [512, 4096] ; 2048 sans texture ─────────────── */
export function tailleAtlas(l, h) {
  const b = (x) => Math.max(512, Math.min(4096, Math.round(x)));
  return Number(l) > 0 && Number(h) > 0 ? { W: b(l), H: b(h) } : { W: 2048, H: 2048 };
}

/* ── l'atlas : les triangles dessinés dans l'espace UV ─────────────────────── */
/* maillage = { positions, normales?, uvs, indices? } (tableaux plats, positions et normales dans le MONDE).
   Rend { W, H, n, texels (indices d'atlas couverts), pos (3n), nrm (3n), masque (W·H, 1 = couvert) }.
   Un texel est couvert si son CENTRE tombe dans un triangle ; puis, s'il ne l'est pas, à moins de `bord` px d'un
   triangle (rastérisation conservatrice : pas de fissure d'un texel le long des bords d'îlots). */
export function rasteriserUV(maillage, W, H, bord = 0.7) {
  const P = maillage.positions, U = maillage.uvs, N = maillage.normales || null;
  const I = maillage.indices || Uint32Array.from({ length: P.length / 3 }, (_, i) => i);
  const tri = new Int32Array(W * H).fill(-1);
  const dedans = new Uint8Array(W * H);
  const nt = I.length / 3;
  for (let t = 0; t < nt; t++) {
    const a = I[3 * t], b = I[3 * t + 1], c = I[3 * t + 2];
    const ax = U[2 * a] * W, ay = U[2 * a + 1] * H, bx = U[2 * b] * W, by = U[2 * b + 1] * H, cx = U[2 * c] * W, cy = U[2 * c + 1] * H;
    const aire = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
    if (!(Math.abs(aire) > 1e-12)) continue;
    const s = aire > 0 ? 1 : -1;
    const lab = Math.hypot(bx - ax, by - ay), lbc = Math.hypot(cx - bx, cy - by), lca = Math.hypot(ax - cx, ay - cy);
    const x0 = Math.max(0, Math.floor(Math.min(ax, bx, cx) - bord)), x1 = Math.min(W - 1, Math.ceil(Math.max(ax, bx, cx) + bord));
    const y0 = Math.max(0, Math.floor(Math.min(ay, by, cy) - bord)), y1 = Math.min(H - 1, Math.ceil(Math.max(ay, by, cy) + bord));
    for (let y = y0; y <= y1; y++) {
      const py = y + 0.5;
      for (let x = x0; x <= x1; x++) {
        const px = x + 0.5;
        // distances signées aux trois arêtes (positives dedans)
        const e0 = s * ((bx - ax) * (py - ay) - (by - ay) * (px - ax)) / lab;
        const e1 = s * ((cx - bx) * (py - by) - (cy - by) * (px - bx)) / lbc;
        const e2 = s * ((ax - cx) * (py - cy) - (ay - cy) * (px - cx)) / lca;
        const k = y * W + x;
        if (e0 >= -1e-7 && e1 >= -1e-7 && e2 >= -1e-7) { tri[k] = t; dedans[k] = 1; }
        else if (!dedans[k] && tri[k] < 0 && e0 >= -bord && e1 >= -bord && e2 >= -bord) tri[k] = t;
      }
    }
  }
  let n = 0;
  for (let k = 0; k < tri.length; k++) if (tri[k] >= 0) n++;
  const texels = new Int32Array(n), pos = new Float32Array(3 * n), nrm = new Float32Array(3 * n), masque = new Uint8Array(W * H);
  let j = 0;
  for (let k = 0; k < tri.length; k++) {
    const t = tri[k];
    if (t < 0) continue;
    masque[k] = 1;
    texels[j] = k;
    const a = I[3 * t], b = I[3 * t + 1], c = I[3 * t + 2];
    const px = (k % W) + 0.5, py = Math.floor(k / W) + 0.5;
    const ax = U[2 * a] * W, ay = U[2 * a + 1] * H, bx = U[2 * b] * W, by = U[2 * b + 1] * H, cx = U[2 * c] * W, cy = U[2 * c + 1] * H;
    const den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy);
    let l0 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / den;
    let l1 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / den;
    let l2 = 1 - l0 - l1;
    // un texel de bord (centre hors du triangle) : barycentres ramenés dans le triangle, pas d'extrapolation
    l0 = Math.max(0, l0); l1 = Math.max(0, l1); l2 = Math.max(0, l2);
    const sl = l0 + l1 + l2 || 1;
    l0 /= sl; l1 /= sl; l2 /= sl;
    for (let q = 0; q < 3; q++) pos[3 * j + q] = l0 * P[3 * a + q] + l1 * P[3 * b + q] + l2 * P[3 * c + q];
    let nx, ny, nz;
    if (N) {
      nx = l0 * N[3 * a] + l1 * N[3 * b] + l2 * N[3 * c];
      ny = l0 * N[3 * a + 1] + l1 * N[3 * b + 1] + l2 * N[3 * c + 1];
      nz = l0 * N[3 * a + 2] + l1 * N[3 * b + 2] + l2 * N[3 * c + 2];
    } else {
      [nx, ny, nz] = vect(sous([P[3 * b], P[3 * b + 1], P[3 * b + 2]], [P[3 * a], P[3 * a + 1], P[3 * a + 2]]),
        sous([P[3 * c], P[3 * c + 1], P[3 * c + 2]], [P[3 * a], P[3 * a + 1], P[3 * a + 2]]));
    }
    const ln = Math.hypot(nx, ny, nz) || 1;
    nrm[3 * j] = nx / ln; nrm[3 * j + 1] = ny / ln; nrm[3 * j + 2] = nz / ln;
    j++;
  }
  return { W, H, n, texels, pos, nrm, masque };
}

/* ── la carte de profondeur d'une caméra : la plus petite distance `w` par pixel (rastérisation des triangles, les
   deux faces, 1/w interpolé linéairement à l'écran = profondeur exacte en perspective) ──────────────────────── */
export function carteProfondeur(maillage, M, w, h) {
  const P = maillage.positions;
  const I = maillage.indices || Uint32Array.from({ length: P.length / 3 }, (_, i) => i);
  const prof = new Float32Array(w * h).fill(Infinity);
  const nv = P.length / 3;
  const sx = new Float32Array(nv), sy = new Float32Array(nv), iw = new Float32Array(nv);
  for (let i = 0; i < nv; i++) {
    const p = projeterPoint(M, P[3 * i], P[3 * i + 1], P[3 * i + 2]);
    sx[i] = p.u * w; sy[i] = p.v * h; iw[i] = p.devant ? 1 / p.w : -1;
  }
  for (let t = 0; t < I.length; t += 3) {
    const a = I[t], b = I[t + 1], c = I[t + 2];
    if (iw[a] <= 0 || iw[b] <= 0 || iw[c] <= 0) continue;          // derrière la caméra : nos vues n'en ont pas
    const aire = (sx[b] - sx[a]) * (sy[c] - sy[a]) - (sy[b] - sy[a]) * (sx[c] - sx[a]);
    if (!(Math.abs(aire) > 1e-12)) continue;
    const x0 = Math.max(0, Math.floor(Math.min(sx[a], sx[b], sx[c]))), x1 = Math.min(w - 1, Math.ceil(Math.max(sx[a], sx[b], sx[c])));
    const y0 = Math.max(0, Math.floor(Math.min(sy[a], sy[b], sy[c]))), y1 = Math.min(h - 1, Math.ceil(Math.max(sy[a], sy[b], sy[c])));
    for (let y = y0; y <= y1; y++) {
      const py = y + 0.5;
      for (let x = x0; x <= x1; x++) {
        const px = x + 0.5;
        const l0 = ((sx[b] - px) * (sy[c] - py) - (sy[b] - py) * (sx[c] - px)) / aire;
        const l1 = ((sx[c] - px) * (sy[a] - py) - (sy[c] - py) * (sx[a] - px)) / aire;
        const l2 = 1 - l0 - l1;
        if (l0 < -1e-6 || l1 < -1e-6 || l2 < -1e-6) continue;
        const d = 1 / (l0 * iw[a] + l1 * iw[b] + l2 * iw[c]);
        const k = y * w + x;
        if (d < prof[k]) prof[k] = d;
      }
    }
  }
  return prof;
}

/* ── la projection d'une vue sur l'atlas ──────────────────────────────────── */
export function nouvelAccumulateur(atlas) {
  return { somme: new Float32Array(4 * atlas.n), meilleur: new Float32Array(atlas.n), proprio: new Int8Array(atlas.n).fill(-1) };
}

/* une image {data RGBA, width, height} lue en (u, v) ∈ [0, 1], bilinéaire, pixels aux centres */
export function echantillon(img, u, v, out) {
  const W = img.width, H = img.height, D = img.data;
  const x = Math.min(W - 1, Math.max(0, u * W - 0.5)), y = Math.min(H - 1, Math.max(0, v * H - 0.5));
  const x0 = Math.floor(x), y0 = Math.floor(y), x1 = Math.min(W - 1, x0 + 1), y1 = Math.min(H - 1, y0 + 1);
  const fx = x - x0, fy = y - y0;
  for (let q = 0; q < 3; q++) {
    const h0 = D[4 * (y0 * W + x0) + q] * (1 - fx) + D[4 * (y0 * W + x1) + q] * fx;
    const h1 = D[4 * (y1 * W + x0) + q] * (1 - fx) + D[4 * (y1 * W + x1) + q] * fx;
    out[q] = h0 * (1 - fy) + h1 * fy;
  }
  return out;
}

/* le poids d'une vue pour un texel : max(0, n·v)^k, v = du texel vers l'œil */
export function poids(n, oeil, p, k = 4) {
  const v = unit(sous(oeil, p));
  const c = scal(n, v);
  return c > 0 ? Math.pow(c, k) : 0;
}

/* `vue` = { M, oeil, profondeur, pw, ph, image } ; `biais` : la tolérance du test de profondeur (unités du monde).
   Ajoute la vue `iv` à l'accumulateur ; rend le nombre de texels qu'elle a vus. */
export function accumulerVue(atlas, vue, acc, iv, { k = 4, biais = 1e-3, de = 0, a = atlas.n } = {}) {
  const { pos, nrm } = atlas, { M, oeil, profondeur, pw, ph, image } = vue;
  const c = [0, 0, 0];
  let vus = 0;
  for (let j = de; j < Math.min(a, atlas.n); j++) {
    const x = pos[3 * j], y = pos[3 * j + 1], z = pos[3 * j + 2];
    const vx = oeil[0] - x, vy = oeil[1] - y, vz = oeil[2] - z;
    const lv = Math.hypot(vx, vy, vz) || 1;
    const cos = (nrm[3 * j] * vx + nrm[3 * j + 1] * vy + nrm[3 * j + 2] * vz) / lv;
    if (!(cos > 0)) continue;                                       // le texel tourne le dos à la caméra
    const p = projeterPoint(M, x, y, z);
    if (!p.devant || p.u < 0 || p.u > 1 || p.v < 0 || p.v > 1) continue;
    if (profondeur) {
      const qx = Math.min(pw - 1, Math.floor(p.u * pw)), qy = Math.min(ph - 1, Math.floor(p.v * ph));
      if (p.w > profondeur[qy * pw + qx] + biais) continue;         // caché par une autre surface
    }
    const wt = Math.pow(cos, k);
    if (!(wt > 0)) continue;
    echantillon(image, p.u, p.v, c);
    acc.somme[4 * j] += c[0] * wt; acc.somme[4 * j + 1] += c[1] * wt; acc.somme[4 * j + 2] += c[2] * wt; acc.somme[4 * j + 3] += wt;
    if (wt > acc.meilleur[j]) { acc.meilleur[j] = wt; acc.proprio[j] = iv; }
    vus++;
  }
  return vus;
}

/* la fusion : chaque texel vu prend la moyenne pondérée de ses vues ; il est marqué peint (1) et possédé par sa vue
   au plus fort poids. Un texel qu'aucune vue n'a vu garde sa couleur (l'origine) et reste non peint : un TROU. */
export function finaliser(atlas, acc, etat) {
  let peints = 0;
  for (let j = 0; j < atlas.n; j++) {
    const s = acc.somme[4 * j + 3];
    if (!(s > 0)) continue;
    const k = atlas.texels[j];
    etat.couleur[4 * k] = acc.somme[4 * j] / s;
    etat.couleur[4 * k + 1] = acc.somme[4 * j + 1] / s;
    etat.couleur[4 * k + 2] = acc.somme[4 * j + 2] / s;
    etat.peint[k] = 1;
    etat.proprio[k] = acc.proprio[j];
    peints++;
  }
  return peints;
}

/* ── l'état peint de l'atlas ──────────────────────────────────────────────── */
/* original : l'atlas d'origine (RGBA W·H), masque : les texels couverts par les UV. couleur part de l'original : un
   texel jamais peint s'enregistre tel qu'il était. peint : 0 rien, 1 projeté, 2 comblé ou retouché. */
export function nouvelEtat(W, H, original, masque) {
  return { W, H, original, masque, couleur: new Uint8ClampedArray(original), peint: new Uint8Array(W * H),
    proprio: new Int8Array(W * H).fill(-1) };
}

const rectDisque = (E, cx, cy, r) => {
  const x0 = Math.max(0, Math.floor(cx - r)), y0 = Math.max(0, Math.floor(cy - r));
  const x1 = Math.min(E.W - 1, Math.ceil(cx + r)), y1 = Math.min(E.H - 1, Math.ceil(cy + r));
  return { x: x0, y: y0, w: Math.max(0, x1 - x0 + 1), h: Math.max(0, y1 - y0 + 1) };
};
export const rectTout = (E) => ({ x: 0, y: 0, w: E.W, h: E.H });
const dansDisque = (x, y, cx, cy, r) => (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r;

/* GOMME : le texel d'origine revient, la peinture s'en va */
export function gommer(E, cx, cy, r) {
  const R = rectDisque(E, cx, cy, r);
  for (let y = R.y; y < R.y + R.h; y++) for (let x = R.x; x < R.x + R.w; x++) {
    if (!dansDisque(x, y, cx, cy, r)) continue;
    const k = y * E.W + x;
    for (let q = 0; q < 4; q++) E.couleur[4 * k + q] = E.original[4 * k + q];
    E.peint[k] = 0; E.proprio[k] = -1;
  }
  return R;
}

/* ESTOMPER : chaque texel couvert du disque vers la moyenne de ses voisins couverts (5×5), d'autant plus qu'il est
   près du centre (`force` ∈ [0, 1]) ; lu sur une copie, pas de traînée dans le sens du balayage */
export function estomper(E, cx, cy, r, force = 0.5) {
  const R = rectDisque(E, cx, cy, r + 2);
  const W = E.W, src = E.couleur.slice(4 * (R.y * W), 4 * ((R.y + R.h) * W));
  const lire = (x, y, q) => src[4 * ((y - R.y) * W + x) + q];
  for (let y = R.y; y < R.y + R.h; y++) for (let x = R.x; x < R.x + R.w; x++) {
    const k = y * W + x;
    if (!E.masque[k] || !dansDisque(x, y, cx, cy, r)) continue;
    const s = [0, 0, 0];
    let n = 0;
    for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
      const xx = x + dx, yy = y + dy;
      if (xx < 0 || yy < R.y || xx >= W || yy >= R.y + R.h || !E.masque[yy * W + xx]) continue;
      for (let q = 0; q < 3; q++) s[q] += lire(xx, yy, q);
      n++;
    }
    if (!n) continue;
    const d = Math.sqrt((x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2) / Math.max(r, 1e-6);
    const f = Math.max(0, Math.min(1, force)) * Math.max(0, 1 - d * d);
    for (let q = 0; q < 3; q++) E.couleur[4 * k + q] = lire(x, y, q) * (1 - f) + (s[q] / n) * f;
    if (!E.peint[k]) E.peint[k] = 2;
  }
  return R;
}

/* le TROU (poche) que touche un disque : les texels couverts non peints reliés (4-voisinage) à ceux du disque */
export function poche(E, cx, cy, r) {
  const { W, H } = E, R = rectDisque(E, cx, cy, r);
  const dans = new Uint8Array(W * H), pile = [];
  for (let y = R.y; y < R.y + R.h; y++) for (let x = R.x; x < R.x + R.w; x++) {
    const k = y * W + x;
    if (E.masque[k] && !E.peint[k] && dansDisque(x, y, cx, cy, r)) { dans[k] = 1; pile.push(k); }
  }
  const b = { x0: W, y0: H, x1: -1, y1: -1 };
  while (pile.length) {
    const k = pile.pop(), x = k % W, y = (k - x) / W;
    b.x0 = Math.min(b.x0, x); b.y0 = Math.min(b.y0, y); b.x1 = Math.max(b.x1, x); b.y1 = Math.max(b.y1, y);
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const xx = x + dx, yy = y + dy, kk = yy * W + xx;
      if (xx < 0 || yy < 0 || xx >= W || yy >= H || dans[kk] || !E.masque[kk] || E.peint[kk]) continue;
      dans[kk] = 1; pile.push(kk);
    }
  }
  const rect = b.x1 < 0 ? { x: R.x, y: R.y, w: 0, h: 0 }
    : { x: Math.max(0, b.x0 - 1), y: Math.max(0, b.y0 - 1), w: Math.min(W - 1, b.x1 + 1) - Math.max(0, b.x0 - 1) + 1,
      h: Math.min(H - 1, b.y1 + 1) - Math.max(0, b.y0 - 1) + 1 };
  return { dans, rect };
}

/* COMBLER : les texels couverts mais NON peints — de la poche que touche le disque `zone` {x, y, r} (« combler depuis
   les voisins »), ou de tout l'atlas si `zone` est nul (« tout combler ») — prennent la couleur de leurs voisins
   peints, par vagues depuis le bord du trou (un front de diffusion), puis quelques passes de lissage sur les seuls
   texels comblés. Un trou sans aucun voisin peint reste un trou. Rend { rect, combles }. */
export function combler(E, zone = null, lissages = 4) {
  const { W, H } = E;
  const P = zone ? poche(E, zone.x, zone.y, zone.r) : null;
  const R = P ? P.rect : rectTout(E);
  const remplissable = (k) => E.masque[k] && !E.peint[k] && (!P || P.dans[k] === 1);
  const fait = new Uint8Array(W * H);
  const source = (k) => E.peint[k] > 0 || fait[k];
  const V = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  const voisins = (k, f) => {
    const x = k % W, y = (k - x) / W;
    for (const [dx, dy] of V) {
      const xx = x + dx, yy = y + dy;
      if (xx >= 0 && yy >= 0 && xx < W && yy < H) f(yy * W + xx);
    }
  };
  // le premier front : les texels à combler qui touchent déjà une peinture
  let front = [];
  const vu = new Uint8Array(W * H);
  for (let y = R.y; y < R.y + R.h; y++) for (let x = R.x; x < R.x + R.w; x++) {
    const k = y * W + x;
    if (!remplissable(k)) continue;
    let touche = false;
    voisins(k, (kk) => { if (E.masque[kk] && E.peint[kk] > 0) touche = true; });
    if (touche) { front.push(k); vu[k] = 1; }
  }
  let combles = 0;
  while (front.length) {                                             // un îlot sans aucune peinture reste un trou
    const pret = [];
    for (const k of front) {
      const s = [0, 0, 0];
      let n = 0;
      voisins(k, (kk) => {
        if (!E.masque[kk] || !source(kk)) return;
        for (let q = 0; q < 3; q++) s[q] += E.couleur[4 * kk + q];
        n++;
      });
      if (n) pret.push([k, s[0] / n, s[1] / n, s[2] / n]);
    }
    const suivant = [];
    for (const [k, r, g, b] of pret) {
      E.couleur[4 * k] = r; E.couleur[4 * k + 1] = g; E.couleur[4 * k + 2] = b;
      fait[k] = 1; combles++;
    }
    for (const [k] of pret) voisins(k, (kk) => { if (!vu[kk] && remplissable(kk)) { vu[kk] = 1; suivant.push(kk); } });
    front = suivant;
  }
  const lus = [];
  for (let k = 0; k < fait.length; k++) if (fait[k]) lus.push(k);
  for (let p = 0; p < lissages; p++) {
    const neuf = new Float32Array(3 * lus.length);
    lus.forEach((k, i) => {
      const x = k % W, y = (k - x) / W;
      const s = [E.couleur[4 * k], E.couleur[4 * k + 1], E.couleur[4 * k + 2]];
      let n = 1;
      for (const [dx, dy] of V) {
        const xx = x + dx, yy = y + dy;
        if (xx < 0 || yy < 0 || xx >= W || yy >= H || !E.masque[yy * W + xx] || !source(yy * W + xx)) continue;
        for (let q = 0; q < 3; q++) s[q] += E.couleur[4 * (yy * W + xx) + q];
        n++;
      }
      for (let q = 0; q < 3; q++) neuf[3 * i + q] = s[q] / n;
    });
    lus.forEach((k, i) => { for (let q = 0; q < 3; q++) E.couleur[4 * k + q] = neuf[3 * i + q]; });
  }
  for (const k of lus) { E.peint[k] = 2; E.proprio[k] = -1; }
  return { rect: R, combles };
}

/* les TROUS : texels couverts par les UV qu'aucune vue (ni retouche) n'a peints — le visualiseur de fissures */
export function trous(E) {
  let n = 0;
  for (let k = 0; k < E.masque.length; k++) if (E.masque[k] && !E.peint[k]) n++;
  return n;
}

/* ── les coutures UV : une arête du maillage dont les deux côtés ont des UV différents ────────────────────────── */
/* rend [[a0, a1, b0, b1], …] en pixels d'atlas : l'arête vue du côté A (a0 → a1) et du côté B (b0 → b1), dans le
   même sens 3D. Les sommets sont appariés par leur POSITION (arrondie), pas par leur index : un GLB coupe ses
   sommets aux coutures. */
export function coutures(maillage, W, H, tolerance = 1e-5) {
  const P = maillage.positions, U = maillage.uvs;
  const I = maillage.indices || Uint32Array.from({ length: P.length / 3 }, (_, i) => i);
  const q = (i) => `${Math.round(P[3 * i] / tolerance)},${Math.round(P[3 * i + 1] / tolerance)},${Math.round(P[3 * i + 2] / tolerance)}`;
  const aretes = new Map();
  for (let t = 0; t < I.length; t += 3) for (let e = 0; e < 3; e++) {
    let i = I[t + e], j = I[t + ((e + 1) % 3)];
    let ki = q(i), kj = q(j);
    if (ki === kj) continue;
    if (ki > kj) { [i, j] = [j, i]; [ki, kj] = [kj, ki]; }
    const cle = ki + "|" + kj;
    const uv = [U[2 * i] * W, U[2 * i + 1] * H, U[2 * j] * W, U[2 * j + 1] * H];
    if (!aretes.has(cle)) aretes.set(cle, []);
    const l = aretes.get(cle);
    if (!l.some((v) => v.every((x, n) => Math.abs(x - uv[n]) < 1e-3))) l.push(uv);
  }
  const out = [];
  for (const l of aretes.values()) for (let a = 1; a < l.length; a++)
    out.push([[l[0][0], l[0][1]], [l[0][2], l[0][3]], [l[a][0], l[a][1]], [l[a][2], l[a][3]]]);
  return out;
}

/* SOIGNER : le long de chaque couture, le texel du côté A et celui du côté B prennent leur moyenne — la fissure de
   couleur entre deux îlots disparaît. Rend le nombre de paires moyennées. */
export function soigner(E, paires) {
  const { W, H } = E;
  let n = 0;
  const texel = (x, y) => {
    const xx = Math.min(W - 1, Math.max(0, Math.floor(x))), yy = Math.min(H - 1, Math.max(0, Math.floor(y)));
    return yy * W + xx;
  };
  for (const [a0, a1, b0, b1] of paires) {
    const pas = Math.max(1, Math.ceil(Math.max(Math.hypot(a1[0] - a0[0], a1[1] - a0[1]), Math.hypot(b1[0] - b0[0], b1[1] - b0[1]))));
    const vus = new Set();
    for (let s = 0; s <= pas; s++) {
      const t = s / pas;
      const ka = texel(a0[0] + (a1[0] - a0[0]) * t, a0[1] + (a1[1] - a0[1]) * t);
      const kb = texel(b0[0] + (b1[0] - b0[0]) * t, b0[1] + (b1[1] - b0[1]) * t);
      if (ka === kb || vus.has(ka + ":" + kb)) continue;
      vus.add(ka + ":" + kb);
      for (let c = 0; c < 3; c++) {
        const m = (E.couleur[4 * ka + c] + E.couleur[4 * kb + c]) / 2;
        E.couleur[4 * ka + c] = m; E.couleur[4 * kb + c] = m;
      }
      if (!E.peint[ka]) E.peint[ka] = 2;
      if (!E.peint[kb]) E.peint[kb] = 2;
      n++;
    }
  }
  return n;
}

/* DÉBORDER (à l'enregistrement) : `n` px de couleur poussés hors des îlots, sur les texels non couverts, pour que le
   filtrage bilinéaire et les mipmaps ne ramènent pas le fond aux bords */
export function deborder(couleur, masque, W, H, n = 4) {
  const fait = Uint8Array.from(masque);
  for (let p = 0; p < n; p++) {
    const neufs = [];
    for (let k = 0; k < fait.length; k++) {
      if (fait[k]) continue;
      const x = k % W, y = (k - x) / W;
      const s = [0, 0, 0, 0];
      let c = 0;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const xx = x + dx, yy = y + dy;
        if (xx < 0 || yy < 0 || xx >= W || yy >= H || !fait[yy * W + xx]) continue;
        for (let q = 0; q < 4; q++) s[q] += couleur[4 * (yy * W + xx) + q];
        c++;
      }
      if (c) neufs.push([k, s.map((v) => v / c)]);
    }
    for (const [k, s] of neufs) { for (let q = 0; q < 4; q++) couleur[4 * k + q] = s[q]; fait[k] = 1; }
  }
  return couleur;
}

/* ── annuler / rétablir : des carreaux (rectangles) mémorisés avant chaque geste ───────────────────────────── */
export function nouvellePile(maxOctets = 192 * 1024 * 1024, maxPas = 30) {
  return { passe: [], futur: [], maxOctets, maxPas };
}
const copier = (E, R) => {
  const c = new Uint8ClampedArray(4 * R.w * R.h), p = new Uint8Array(R.w * R.h), o = new Int8Array(R.w * R.h);
  for (let y = 0; y < R.h; y++) {
    const k = (R.y + y) * E.W + R.x;
    c.set(E.couleur.subarray(4 * k, 4 * (k + R.w)), 4 * y * R.w);
    p.set(E.peint.subarray(k, k + R.w), y * R.w);
    o.set(E.proprio.subarray(k, k + R.w), y * R.w);
  }
  return { ...R, c, p, o, octets: c.length + 2 * p.length };
};
const coller = (E, carreau) => {
  const { x, y: y0, w, h, c, p, o } = carreau;
  for (let y = 0; y < h; y++) {
    const k = (y0 + y) * E.W + x;
    E.couleur.set(c.subarray(4 * y * w, 4 * (y + 1) * w), 4 * k);
    E.peint.set(p.subarray(y * w, (y + 1) * w), k);
    E.proprio.set(o.subarray(y * w, (y + 1) * w), k);
  }
};
/* à appeler AVANT un geste qui touchera `rect`. `suite` : le carreau rejoint le pas précédent (un TRAIT de pinceau
   est un seul pas d'annulation, fait d'autant de carreaux que de touches). Annuler recolle les carreaux d'un pas du
   dernier au premier (le premier tient l'état d'avant le trait) ; rétablir recolle les copies prises juste avant
   l'annulation, toutes du même état, donc dans n'importe quel ordre. */
export function memoriser(pile, E, rect, suite = false) {
  if (!rect || rect.w <= 0 || rect.h <= 0) return;
  const c = copier(E, rect);
  const dernier = pile.passe[pile.passe.length - 1];
  if (suite && dernier) { dernier.carreaux.push(c); dernier.octets += c.octets; }
  else pile.passe.push({ carreaux: [c], octets: c.octets });
  pile.futur.length = 0;
  let total = pile.passe.reduce((s, p) => s + p.octets, 0);
  while (pile.passe.length > 1 && (pile.passe.length > pile.maxPas || total > pile.maxOctets)) total -= pile.passe.shift().octets;
}
const englobe = (l) => l.reduce((r, c) => unionRect(r, { x: c.x, y: c.y, w: c.w, h: c.h }), null);
export function annuler(pile, E) {
  const pas = pile.passe.pop();
  if (!pas) return null;
  const copies = pas.carreaux.map((c) => copier(E, c));
  for (let i = pas.carreaux.length - 1; i >= 0; i--) coller(E, pas.carreaux[i]);
  pile.futur.push({ carreaux: copies, octets: pas.octets });
  return englobe(pas.carreaux);
}
export function retablir(pile, E) {
  const pas = pile.futur.pop();
  if (!pas) return null;
  const copies = pas.carreaux.map((c) => copier(E, c));
  for (const c of pas.carreaux) coller(E, c);
  pile.passe.push({ carreaux: copies, octets: pas.octets });
  return englobe(pas.carreaux);
}
export const unionRect = (a, b) => {
  if (!a) return b;
  if (!b) return a;
  const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
  return { x, y, w: Math.max(a.x + a.w, b.x + b.w) - x, h: Math.max(a.y + a.h, b.y + b.h) - y };
};
/* le rect que touchera un pinceau de rayon r posé en (cx, cy) (marge de l'estompe comprise) */
export const rectPinceau = (E, cx, cy, r) => rectDisque(E, cx, cy, r + 2);

/* ── l'affichage ──────────────────────────────────────────────────────────── */
/* une teinte par vue (18 au plus), espacées au nombre d'or pour que deux vues voisines ne se ressemblent pas */
export function couleurVue(i) {
  const h = ((i * 0.618034) % 1) * 360, s = 0.7, l = 0.55;
  const f = (n) => { const k = (n + h / 30) % 12; return l - s * Math.min(l, 1 - l) * Math.max(-1, Math.min(k - 3, 9 - k, 1)); };
  return [Math.round(f(0) * 255), Math.round(f(8) * 255), Math.round(f(4) * 255)];
}
export const MODES = ["peint", "vues", "trous", "original"];
const TROU = [255, 0, 200];

/* compose l'image affichée (atlas à plat et texture du modèle) dans `sortie` (RGBA W·H), sur `rect` :
   peint → la couleur (avec `cacher`, un texel non peint montre un damier gris au lieu de l'origine) ; vues → la
   teinte de la vue propriétaire (gris foncé : aucune) ; trous → la couleur, les trous en magenta ; original → l'origine */
export function composer(E, mode, cacher, sortie, rect = rectTout(E)) {
  const { W } = E;
  for (let y = rect.y; y < rect.y + rect.h; y++) for (let x = rect.x; x < rect.x + rect.w; x++) {
    const k = y * W + x, o = 4 * k;
    let r = E.couleur[o], g = E.couleur[o + 1], b = E.couleur[o + 2];
    if (mode === "original") { r = E.original[o]; g = E.original[o + 1]; b = E.original[o + 2]; }
    else if (mode === "vues") {
      if (E.proprio[k] >= 0) {
        const c = couleurVue(E.proprio[k]);
        const l = (0.3 * r + 0.59 * g + 0.11 * b) / 255;
        r = c[0] * (0.55 + 0.45 * l); g = c[1] * (0.55 + 0.45 * l); b = c[2] * (0.55 + 0.45 * l);
      } else if (E.peint[k]) { r = g = b = 150; }
      else { r = g = b = 48; }
    } else if (mode === "trous" && E.masque[k] && !E.peint[k]) { [r, g, b] = TROU; }
    else if (mode === "peint" && cacher && !E.peint[k]) { r = g = b = ((x >> 4) + (y >> 4)) % 2 ? 96 : 128; }
    sortie[o] = r; sortie[o + 1] = g; sortie[o + 2] = b; sortie[o + 3] = 255;
  }
  return sortie;
}
