// mod-solide.js — impression 3D du lot D (D4) : retrait d'un multipolygone
// par DIFFÉRENCE avec son contour gonflé (la voie éprouvée de mod-bool),
// biseau en marches fines (indistinguable d'un chanfrein à 0,2 mm de
// couche), évidement à mur minimal contrôlé, pièces d'un plateau de tuiles
// (socle + relief par terrain), GLB minimal pour l'aperçu, nomenclature.
// PUR : martinez est FOURNI par l'appelant (mz), aucun DOM.
import { extruder } from "./mod-extrude.js";
import { hex_centre, hex_sommets } from "./mod-grille.js";

export const MUR_MIN_MM = 0.8;          // deux passes d'une buse de 0,4

function _ringsDe(multi) {
  const out = [];
  for (const poly of multi) for (const ring of poly) out.push(ring);
  return out;
}

function _disque(cx, cy, r, n = 24) {
  const p = [];
  for (let k = 0; k < n; k++) {
    const a = 2 * Math.PI * k / n;
    p.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
  }
  p.push([p[0][0], p[0][1]]);
  return p;
}
const _propre = (mp) => (mp || []).filter((poly) => poly && poly.length && poly[0].length >= 4);

// retrait d = multi ∖ bande de largeur 2d autour de chaque arête. La bande
// se retire PIÈCE PAR PIÈCE (un quadrilatère puis un disque par arête) :
// l'UNION préalable de toutes les pièces perdait le trou du bandeau
// (mesuré : un carré 20 retiré de 2 rendait une aire de 100 au lieu de
// 256) — les arêtes tangentes des disques et des quadrilatères font
// trébucher martinez ; des différences successives, jamais.
export function inset_multi(mz, multi, d) {
  if (!(d >= 0)) throw new Error("retrait : distance ≥ 0 requise");
  if (d === 0) return multi;
  let out = multi;
  for (const ring of _ringsDe(multi)) {
    const pts = ring.slice(0, -1);
    for (let k = 0; k < pts.length; k++) {
      const p = pts[k], q = pts[(k + 1) % pts.length];
      const dx = q[0] - p[0], dy = q[1] - p[1], lg = Math.hypot(dx, dy);
      if (lg < 1e-9) continue;
      const nx = -dy / lg * d, ny = dx / lg * d;
      const quad = [[[p[0] + nx, p[1] + ny], [q[0] + nx, q[1] + ny],
                     [q[0] - nx, q[1] - ny], [p[0] - nx, p[1] - ny], [p[0] + nx, p[1] + ny]]];
      out = _propre(mz.diff(out, [quad]));
      if (!out.length) return out;
      // +1 % : la tangente du disque ne coïncide plus avec le bord du
      // quadrilatère (coïncidence exacte = martinez égaré, mesuré au lot B)
      out = _propre(mz.diff(out, [[_disque(p[0], p[1], d * 1.01)]]));
      if (!out.length) return out;
    }
  }
  return out;
}

export function extruder_biseau(mz, multi, hauteur, biseau, pasMm = 0.2) {
  const h = +hauteur, b = +biseau;
  if (!(h > 0)) throw new Error("biseau : hauteur > 0 requise");
  if (!(b >= 0)) throw new Error("biseau : retrait ≥ 0 requis");
  if (b >= h) throw new Error("biseau : le retrait doit rester sous la hauteur");
  if (b === 0) return extruder(multi, h, 0);
  const n = Math.max(1, Math.ceil(b / Math.max(0.05, +pasMm || 0.2)));
  const dz = b / n;
  const tris = extruder(multi, h - b, 0);
  for (let k = 1; k <= n; k++) {
    const m = inset_multi(mz, multi, (b * k) / n);
    if (!m.length) break;                       // la pointe se ferme d'elle-même
    tris.push(...extruder(m, dz, h - b + (k - 1) * dz));
  }
  return tris;
}

export function extruder_evide(mz, multi, hauteur, mur, plancher) {
  const h = +hauteur, w = +mur, p = +plancher;
  if (!(h > 0)) throw new Error("évidement : hauteur > 0 requise");
  if (!(w >= MUR_MIN_MM)) {
    throw new Error(`évidement : mur ≥ ${MUR_MIN_MM} mm (deux passes de buse)`);
  }
  if (!(p >= 0) || p >= h) throw new Error("évidement : plancher ≥ 0 et sous la hauteur");
  const interieur = inset_multi(mz, multi, w);
  if (!interieur.length) {
    throw new Error("évidement : mur trop épais pour cette forme (elle se vide)");
  }
  const coque = mz.diff(multi, interieur);
  const tris = p > 0 ? extruder(multi, p, 0) : [];
  tris.push(...extruder(coque, h - p, p));
  return tris;
}

/* ── plateau : une pièce par tuile — prisme hex de hauteur socle + terrain ;
   y RETOURNÉ (SVG y-bas → plateau y-haut), mm par sMm ── */
export function plateau_pieces(tuiles, terrains, g, { socle_mm, sMm }) {
  const out = [];
  for (const t of tuiles) {
    if (t.type !== "tuile") continue;
    const fiche = terrains[t.terrain];
    const relief = t.hauteur_mm !== undefined ? +t.hauteur_mm : (fiche ? +fiche.hauteur_mm : 0);
    const hauteur = +socle_mm + relief;
    const [cx, cy] = hex_centre(t.q, t.r, g);
    const ring = hex_sommets(cx, cy, g.pas, g.orientation, g.echelle)
      .map(([x, y]) => [x * sMm, -y * sMm]);
    ring.push([ring[0][0], ring[0][1]]);
    const piece = { nom: `tuile_${t.q}_${t.r}`.replace(/-/g, "m"), id: t.id, q: t.q, r: t.r,
                    terrain: t.terrain, hauteur_mm: hauteur, centre_mm: [cx * sMm, -cy * sMm],
                    tris: hauteur > 0 ? extruder([[ring]], hauteur, 0) : [] };
    if (!fiche) piece.inconnu = true;
    out.push(piece);
  }
  return out;
}

/* ── GLB minimal : une primitive TRIANGLES, POSITION + NORMAL, sans index ── */
export function glb_de_triangles(tris) {
  if (!tris || !tris.length) throw new Error("GLB : aucun triangle");
  const n = tris.length * 3;
  const pos = new Float32Array(n * 3), nrm = new Float32Array(n * 3);
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  let k = 0;
  for (const [a, b, c] of tris) {
    const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
    const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    const l = Math.hypot(nx, ny, nz) || 1;
    nx /= l; ny /= l; nz /= l;
    for (const p of [a, b, c]) {
      pos[k * 3] = p[0]; pos[k * 3 + 1] = p[1]; pos[k * 3 + 2] = p[2];
      nrm[k * 3] = nx; nrm[k * 3 + 1] = ny; nrm[k * 3 + 2] = nz;
      for (let i = 0; i < 3; i++) {
        min[i] = Math.min(min[i], p[i]); max[i] = Math.max(max[i], p[i]);
      }
      k++;
    }
  }
  const binLen = pos.byteLength + nrm.byteLength;
  const json = {
    asset: { version: "2.0", generator: "Deepotus Vectorlab" },
    scene: 0, scenes: [{ nodes: [0] }], nodes: [{ mesh: 0 }],
    meshes: [{ primitives: [{ attributes: { POSITION: 0, NORMAL: 1 }, mode: 4, material: 0 }] }],
    materials: [{ pbrMetallicRoughness: { baseColorFactor: [0.82, 0.78, 0.7, 1],
                                          metallicFactor: 0, roughnessFactor: 0.6 } }],
    buffers: [{ byteLength: binLen }],
    bufferViews: [{ buffer: 0, byteOffset: 0, byteLength: pos.byteLength, target: 34962 },
                  { buffer: 0, byteOffset: pos.byteLength, byteLength: nrm.byteLength, target: 34962 }],
    accessors: [{ bufferView: 0, componentType: 5126, count: n, type: "VEC3", min, max },
                { bufferView: 1, componentType: 5126, count: n, type: "VEC3" }],
  };
  let js = JSON.stringify(json);
  while (js.length % 4) js += " ";
  const jsBytes = new TextEncoder().encode(js);
  const total = 12 + 8 + jsBytes.length + 8 + binLen;
  const out = new Uint8Array(total);
  const dv = new DataView(out.buffer);
  dv.setUint32(0, 0x46546C67, true); dv.setUint32(4, 2, true); dv.setUint32(8, total, true);
  dv.setUint32(12, jsBytes.length, true); dv.setUint32(16, 0x4E4F534A, true);
  out.set(jsBytes, 20);
  const offBin = 20 + jsBytes.length;
  dv.setUint32(offBin, binLen, true); dv.setUint32(offBin + 4, 0x004E4942, true);
  out.set(new Uint8Array(pos.buffer), offBin + 8);
  out.set(new Uint8Array(nrm.buffer), offBin + 8 + pos.byteLength);
  return out;
}

export function nomenclature_csv(pieces) {
  const q = (v) => {
    const s = String(v ?? "");
    return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lignes = ["piece;q;r;terrain;hauteur_mm;triangles"];
  for (const p of pieces) {
    lignes.push([p.nom, p.q, p.r, p.terrain, p.hauteur_mm, (p.tris || []).length].map(q).join(";"));
  }
  return lignes.join("\n") + "\n";
}
