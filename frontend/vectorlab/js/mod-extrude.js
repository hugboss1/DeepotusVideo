// mod-extrude.js — impression 3D (phase 3 du plan slicer) : un multi
// polygone (la forme aplatie/unie d'un calque) devient un PRISME fermé —
// capots triangulés par oreilles (ponts de trous), murs par segment —
// puis un STL binaire. PUR : aucun DOM, aucun martinez (l'union vit dans
// l'UI, déjà éprouvée par mod-bool).

const EPS = 1e-12;

function _ouvrir(ring) {
  const p = ring.map((v) => [+v[0], +v[1]]);
  if (p.length > 1) {
    const a = p[0], b = p[p.length - 1];
    if (a[0] === b[0] && a[1] === b[1]) p.pop();
  }
  return p;
}

function _aire2(pts) {
  let s = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length];
    s += x1 * y2 - x2 * y1;
  }
  return s / 2;
}

function _croix(a, b, c) {
  return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
}

function _dansTriangleStrict(a, b, c, p) {
  const d1 = _croix(a, b, p), d2 = _croix(b, c, p), d3 = _croix(c, a, p);
  return d1 > EPS && d2 > EPS && d3 > EPS;
}

/* Un point DANS l'oreille ou SUR une de ses arêtes la bloque — le L concave
   l'a payé : un sommet posé exactement sur la diagonale laissait couper une
   oreille qui recouvrait le creux (aire 400 pour 300). Les DOUBLONS de pont
   (mêmes coordonnées qu'un coin) ne bloquent pas : exclusion par égalité. */
function _bloqueOreille(a, b, c, p) {
  for (const s of [a, b, c]) {
    if (p[0] === s[0] && p[1] === s[1]) return false;
  }
  return _croix(a, b, p) >= -EPS && _croix(b, c, p) >= -EPS
      && _croix(c, a, p) >= -EPS;
}

/* ── ponts de trous (algorithme du rayon +x, le classique d'earcut) ── */
function _pont(poly, trou) {
  let iM = 0;
  for (let i = 1; i < trou.length; i++) {
    if (trou[i][0] > trou[iM][0]) iM = i;
  }
  const M = trou[iM];
  let meilleur = null;
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i], b = poly[(i + 1) % poly.length];
    if ((a[1] > M[1]) === (b[1] > M[1])) continue;
    const x = a[0] + ((M[1] - a[1]) / (b[1] - a[1])) * (b[0] - a[0]);
    if (x >= M[0] - 1e-9 && (!meilleur || x < meilleur.x)) {
      meilleur = { x, i, a, b };
    }
  }
  if (!meilleur) throw new Error("extrusion : trou hors de son contour");
  let iVis = (meilleur.a[0] > meilleur.b[0])
    ? meilleur.i : (meilleur.i + 1) % poly.length;
  // un sommet REFLEX dans le triangle M-I-P vole la visibilité (earcut) :
  // prendre alors le plus proche de M
  const I = [meilleur.x, M[1]];
  for (let i = 0; i < poly.length; i++) {
    if (i === iVis) continue;
    const p = poly[i];
    const reflex = _croix(poly[(i - 1 + poly.length) % poly.length], p,
                          poly[(i + 1) % poly.length]) <= 0;
    if (!reflex) continue;
    if (_dansTriangleStrict(M, I, poly[iVis], p)
        || _dansTriangleStrict(M, poly[iVis], I, p)) {
      if (Math.hypot(p[0] - M[0], p[1] - M[1])
          < Math.hypot(poly[iVis][0] - M[0], poly[iVis][1] - M[1])) {
        iVis = i;
      }
    }
  }
  const rot = trou.slice(iM).concat(trou.slice(0, iM));
  return [...poly.slice(0, iVis + 1), ...rot, [rot[0][0], rot[0][1]],
          [poly[iVis][0], poly[iVis][1]], ...poly.slice(iVis + 1)];
}

function _fusionnerTrous(outer, trous) {
  let poly = outer.slice();
  const tri = trous.slice().sort((h1, h2) =>
    Math.max(...h2.map((p) => p[0])) - Math.max(...h1.map((p) => p[0])));
  for (const t of tri) poly = _pont(poly, t);
  return poly;
}

/* ── oreilles ── */
function _earclip(poly) {
  const idx = poly.map((_, i) => i);
  const tris = [];
  let garde = 0;
  while (idx.length > 3 && garde < 100000) {
    garde++;
    let coupe = false;
    for (let k = 0; k < idx.length; k++) {
      const i0 = idx[(k - 1 + idx.length) % idx.length];
      const i1 = idx[k];
      const i2 = idx[(k + 1) % idx.length];
      const a = poly[i0], b = poly[i1], c = poly[i2];
      if (_croix(a, b, c) <= EPS) continue;      // reflex ou plat
      let occupe = false;
      for (const j of idx) {
        if (j === i0 || j === i1 || j === i2) continue;
        if (_bloqueOreille(a, b, c, poly[j])) { occupe = true; break; }
      }
      if (occupe) continue;
      tris.push([a, b, c]);
      idx.splice(k, 1);
      coupe = true;
      break;
    }
    if (!coupe) {
      // dégénérescence (colinéaires du pont) : couper quand même — le banc
      // mesure l'AIRE, une coupe plate n'ajoute rien
      tris.push([poly[idx[idx.length - 1]], poly[idx[0]], poly[idx[1]]]);
      idx.splice(0, 1);
    }
  }
  if (idx.length === 3) {
    tris.push([poly[idx[0]], poly[idx[1]], poly[idx[2]]]);
  }
  return tris;
}

export function trianguler(multi) {
  const out = [];
  for (const anneaux of multi) {
    const rings = anneaux.map(_ouvrir).filter((r) => r.length >= 3);
    if (!rings.length) continue;
    const outer = _aire2(rings[0]) >= 0 ? rings[0]
      : rings[0].slice().reverse();
    const trous = rings.slice(1).map((r) =>
      _aire2(r) <= 0 ? r : r.slice().reverse());
    out.push(..._earclip(_fusionnerTrous(outer, trous)));
  }
  return out;
}

/* ── le prisme fermé : capots (haut +Z, bas inversé) + murs par segment ── */
export function extruder(multi, hauteur, zBase = 0) {
  const h = +hauteur;
  if (!(h > 0)) throw new Error("extrusion : hauteur > 0 requise");
  const z0 = +zBase || 0;
  const tris3d = [];
  for (const anneaux of multi) {
    const rings = anneaux.map(_ouvrir).filter((r) => r.length >= 3);
    if (!rings.length) continue;
    const outer = _aire2(rings[0]) >= 0 ? rings[0]
      : rings[0].slice().reverse();
    const trous = rings.slice(1).map((r) =>
      _aire2(r) <= 0 ? r : r.slice().reverse());
    for (const [a, b, c] of _earclip(_fusionnerTrous(outer, trous))) {
      tris3d.push([[a[0], a[1], z0 + h], [b[0], b[1], z0 + h],
                   [c[0], c[1], z0 + h]]);
      tris3d.push([[a[0], a[1], z0], [c[0], c[1], z0], [b[0], b[1], z0]]);
    }
    for (const ring of [outer, ...trous]) {
      for (let i = 0; i < ring.length; i++) {
        const p = ring[i], q = ring[(i + 1) % ring.length];
        tris3d.push([[p[0], p[1], z0], [q[0], q[1], z0],
                     [q[0], q[1], z0 + h]]);
        tris3d.push([[p[0], p[1], z0], [q[0], q[1], z0 + h],
                     [p[0], p[1], z0 + h]]);
      }
    }
  }
  return tris3d;
}

export function volume_de(tris) {
  let v = 0;
  for (const [a, b, c] of tris) {
    v += (a[0] * (b[1] * c[2] - b[2] * c[1])
        + a[1] * (b[2] * c[0] - b[0] * c[2])
        + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6;
  }
  return v;
}

export function stl_binaire(tris) {
  const buf = new ArrayBuffer(84 + 50 * tris.length);
  const dv = new DataView(buf);
  const tete = "Deepotus Vectorlab - extrusion STL (mm)";
  for (let i = 0; i < tete.length; i++) dv.setUint8(i, tete.charCodeAt(i));
  dv.setUint32(80, tris.length, true);
  let off = 84;
  for (const [a, b, c] of tris) {
    const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
    const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz,
        nz = ux * vy - uy * vx;
    const long = Math.hypot(nx, ny, nz);
    if (long > 0) { nx /= long; ny /= long; nz /= long; }
    for (const v of [[nx, ny, nz], a, b, c]) {
      dv.setFloat32(off, v[0], true);
      dv.setFloat32(off + 4, v[1], true);
      dv.setFloat32(off + 8, v[2], true);
      off += 12;
    }
    dv.setUint16(off, 0, true);
    off += 2;
  }
  return new Uint8Array(buf);
}
