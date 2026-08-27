// mod-bool.js — booléens (phase 3) : aplatissement des objets en anneaux
// de points (tolérance 0,25 px), pont vers martinez (vendorisé, MIT —
// vendor/LICENSE-martinez.txt), opérations union/soustraction/intersection
// et division-métier. Le transform des objets est APPLIQUÉ à
// l'aplatissement (suites de rotate composées en matrice — les seules que
// nos opérations émettent).
import { chemin_parser, chemin_serialiser } from "./mod-doc.js";

/* ── résolveur martinez : injecté au banc, window.martinez à l'écran ── */
let _mz = null;
export function fournirMartinez(m) { _mz = m; }
function _martinez() {
  if (_mz) return _mz;
  if (typeof window !== "undefined" && window.martinez) {
    _mz = window.martinez;
    return _mz;
  }
  throw new Error("martinez indisponible (vendor/martinez.umd.js non chargé)");
}

const TOL = 0.25;

/* ── matrices 2D [a b c d e f] : x' = a x + c y + e ; y' = b x + d y + f ── */
const _IDENT = [1, 0, 0, 1, 0, 0];
function _mul(m, n) {
  return [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
          m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
          m[0] * n[4] + m[2] * n[5] + m[4],
          m[1] * n[4] + m[3] * n[5] + m[5]];
}
function _matriceDe(transform) {
  let m = _IDENT;
  if (!transform) return m;
  const re = /rotate\(\s*(-?[\d.]+)(?:[\s,]+(-?[\d.]+)[\s,]+(-?[\d.]+))?\s*\)/g;
  let t;
  while ((t = re.exec(transform)) !== null) {
    const a = (+t[1]) * Math.PI / 180;
    const cx = +(t[2] || 0), cy = +(t[3] || 0);
    const cos = Math.cos(a), sin = Math.sin(a);
    // rotate(a cx cy) = translate(cx cy) rotate(a) translate(-cx -cy)
    const r = [cos, sin, -sin, cos,
               cx - cos * cx + sin * cy, cy - sin * cx - cos * cy];
    m = _mul(m, r);              // gauche → droite : le plus à droite s'applique en premier
  }
  return m;
}
const _pt = (m, x, y) => [m[0] * x + m[2] * y + m[4],
                          m[1] * x + m[3] * y + m[5]];

/* ── aplatissement des courbes ── */
function _plat_cubique(out, p0, p1, p2, p3, tol, prof = 0) {
  // plat si les contrôles collent à la corde (distance perpendiculaire)
  const dx = p3[0] - p0[0], dy = p3[1] - p0[1];
  const d1 = Math.abs((p1[0] - p0[0]) * dy - (p1[1] - p0[1]) * dx);
  const d2 = Math.abs((p2[0] - p0[0]) * dy - (p2[1] - p0[1]) * dx);
  const long = Math.hypot(dx, dy) || 1e-9;
  if (prof >= 16 || (d1 + d2) / long <= tol) { out.push(p3); return; }
  const mi = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  const p01 = mi(p0, p1), p12 = mi(p1, p2), p23 = mi(p2, p3);
  const p012 = mi(p01, p12), p123 = mi(p12, p23);
  const p0123 = mi(p012, p123);
  _plat_cubique(out, p0, p01, p012, p0123, tol, prof + 1);
  _plat_cubique(out, p0123, p123, p23, p3, tol, prof + 1);
}

function _polylignes_path(d, tol) {
  const segs = chemin_parser(d);
  const lignes = [];
  let cour = null;
  for (const s of segs) {
    if (s.c === "M") {
      if (cour && cour.points.length > 1) lignes.push(cour);
      cour = { points: [[s.p[0], s.p[1]]], ferme: false };
    } else if (!cour) {
      throw new Error("chemin sans M initial");
    } else if (s.c === "L") {
      cour.points.push([s.p[0], s.p[1]]);
    } else if (s.c === "C") {
      const p0 = cour.points[cour.points.length - 1];
      _plat_cubique(cour.points, p0, [s.p[0], s.p[1]], [s.p[2], s.p[3]],
                    [s.p[4], s.p[5]], tol);
    } else if (s.c === "Q") {
      // élévation de degré : quadratique → cubique équivalente
      const p0 = cour.points[cour.points.length - 1];
      const c = [s.p[0], s.p[1]], p3 = [s.p[2], s.p[3]];
      const c1 = [p0[0] + 2 / 3 * (c[0] - p0[0]), p0[1] + 2 / 3 * (c[1] - p0[1])];
      const c2 = [p3[0] + 2 / 3 * (c[0] - p3[0]), p3[1] + 2 / 3 * (c[1] - p3[1])];
      _plat_cubique(cour.points, p0, c1, c2, p3, tol);
    } else if (s.c === "Z") {
      cour.ferme = true;
      lignes.push(cour);
      cour = null;
    }
  }
  if (cour && cour.points.length > 1) lignes.push(cour);
  return lignes;
}

function _points_ellipse(cx, cy, rx, ry, tol) {
  const r = Math.max(Math.abs(rx), Math.abs(ry), 1e-6);
  const pas = 2 * Math.acos(Math.max(-1, 1 - Math.min(tol, r) / r));
  // plancher 64 : le polygone INSCRIT sous-estime l'aire en ~(2π²/3)/n² —
  // à 64 l'erreur d'aire est ≤ 0,16 %, sous le contrat ±0,5 %
  const n = Math.max(64, Math.min(720, Math.ceil(2 * Math.PI / (pas || 0.1))));
  const pts = [];
  for (let k = 0; k < n; k++) {
    const a = 2 * Math.PI * k / n;
    pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]);
  }
  return pts;
}

/* polylignes d'un objet (matrice parent appliquée), SANS fermeture forcée —
   la voie du contour gonflé en dépend */
export function polylignes_objet(objet, tol = TOL, mParent = _IDENT) {
  const m = _mul(mParent, _matriceDe(objet.transform));
  const appl = (lignes) => lignes.map((l) => ({
    ferme: l.ferme, points: l.points.map(([x, y]) => _pt(m, x, y)) }));
  switch (objet.type) {
    case "rect": {
      const { x, y, w, h } = objet;
      return appl([{ ferme: true,
        points: [[x, y], [x + w, y], [x + w, y + h], [x, y + h]] }]);
    }
    case "ellipse":
      return appl([{ ferme: true,
        points: _points_ellipse(objet.cx, objet.cy, objet.rx, objet.ry, tol) }]);
    case "path":
      return appl(_polylignes_path(objet.d, tol));
    case "groupe": {
      const out = [];
      for (const e of objet.enfants || []) {
        out.push(...polylignes_objet(e, tol, m));
      }
      return out;
    }
    case "texte":
      throw new Error("texte : vectorisation hors périmètre — retire le "
                      + "texte de la sélection booléenne");
    default:
      throw new Error(`type non aplatissable: ${objet.type}`);
  }
}

/* anneaux FERMÉS (premier == dernier) — l'entrée des booléens */
export function aplatir_objet(objet, tol = TOL) {
  const anneaux = [];
  for (const l of polylignes_objet(objet, tol)) {
    if (l.points.length < 3) continue;
    const ring = l.points.slice();
    const p0 = ring[0], pn = ring[ring.length - 1];
    if (p0[0] !== pn[0] || p0[1] !== pn[1]) ring.push([p0[0], p0[1]]);
    anneaux.push(ring);
  }
  return anneaux;
}

/* aire d'un jeu d'anneaux : somme SIGNÉE absolue (les trous, en
   orientation opposée, se soustraient) */
export function aire_de(anneaux) {
  let total = 0;
  for (const ring of anneaux) {
    let s = 0;
    for (let k = 0; k < ring.length - 1; k++) {
      s += ring[k][0] * ring[k + 1][1] - ring[k + 1][0] * ring[k][1];
    }
    total += s / 2;
  }
  return Math.abs(total);
}
