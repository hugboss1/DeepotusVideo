// mod-solide.js — impression 3D du lot D (D4) : retrait d'un multipolygone
// par DIFFÉRENCE avec son contour gonflé (la voie éprouvée de mod-bool),
// biseau en marches fines (indistinguable d'un chanfrein à 0,2 mm de
// couche), évidement à mur minimal contrôlé, pièces d'un plateau de tuiles
// (socle + relief par terrain), GLB minimal pour l'aperçu, nomenclature.
// PUR : martinez est FOURNI par l'appelant (mz), aucun DOM.
import { extruder } from "./mod-extrude.js";
import { hex_centre, hex_sommets } from "./mod-grille.js";

export const MUR_MIN_MM = 0.8;          // deux passes d'une buse de 0,4

/* ── R12 : la couleur d'une pièce (l'aperçu 3D et le 3MF la portent, le STL
   ne le peut pas) ── */
export const COULEUR_DEFAUT = "#D1C7B3";     // le blanc cassé d'avant R12 : un document sans couleur ne change pas
const _HEX = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;
function _hex6(h) {
  if (typeof h !== "string" || !_HEX.test(h)) return null;
  return h.length === 4 ? "#" + h[1] + h[1] + h[2] + h[2] + h[3] + h[3] : h;
}
export function couleur_de_piece(objet, terrains) {
  if (!objet) return COULEUR_DEFAUT;
  if (objet.type === "tuile") {
    const f = terrains && terrains[objet.terrain];
    return (f && _hex6(f.couleur)) || "#888888";
  }
  const s = objet.style || {};
  return _hex6(s.fond) || (s.contour && _hex6(s.contour.couleur)) || COULEUR_DEFAUT;
}
// le VOTE, pas la moyenne (une moyenne fait un marron)
export function couleur_dominante(objets, terrains) {
  const votes = new Map();
  for (const o of objets || []) {
    if (!o || o.type === "texte") continue;
    const c = couleur_de_piece(o, terrains);
    votes.set(c, (votes.get(c) || 0) + 1);
  }
  let best = COULEUR_DEFAUT, n = 0;
  for (const [c, k] of votes) if (k > n) { best = c; n = k; }
  return best;
}
// glTF veut le LINÉAIRE (même conversion que gltf_builder._srgb_to_linear)
const _lin = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
export function hex_vers_facteur(hex) {
  const h = _hex6(hex) || COULEUR_DEFAUT;
  const v = [1, 3, 5].map((i) => _lin(parseInt(h.slice(i, i + 2), 16) / 255));
  return [v[0], v[1], v[2], 1];
}

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

/* ── R12 : la dépouille — retrait r(z) = z · tan(angle), en marches de retrait
   ≤ 0,2 mm (24 au plus : un texte de 300 arêtes reste sous la seconde) ;
   angle négatif = la forme dessinée est le SOMMET (extrusion positive
   retournée en z — aucun « outset », martinez perd des morceaux sur les
   unions successives, mesuré au lot B) ── */
export const DEPOUILLE_MAX = 45;
export function retourner_z(tris, h) {
  return tris.map(([a, b, c]) => [[a[0], a[1], h - a[2]], [c[0], c[1], h - c[2]], [b[0], b[1], h - b[2]]]);
}
export function extruder_depouille(mz, multi, hauteur, angleDeg, pasMm = 0.2, zBase = 0) {
  const h = +hauteur, a = +angleDeg || 0;
  if (!(h > 0)) throw new Error("dépouille : hauteur > 0 requise");
  if (Math.abs(a) > DEPOUILLE_MAX) throw new Error(`dépouille : angle entre −${DEPOUILLE_MAX}° et ${DEPOUILLE_MAX}°`);
  if (a === 0) return extruder(multi, h, zBase);
  const retrait = h * Math.tan(Math.abs(a) * Math.PI / 180);
  const n = Math.min(24, Math.max(1, Math.ceil(retrait / Math.max(0.05, +pasMm || 0.2))));
  const dz = h / n;
  const tris = [];
  for (let k = 0; k < n; k++) {
    const m = k === 0 ? multi : inset_multi(mz, multi, retrait * k / n);
    if (!m.length) break;                        // la pointe se ferme d'elle-même
    tris.push(...extruder(m, dz, k * dz));
  }
  const out = a > 0 ? tris : retourner_z(tris, h);
  return zBase ? out.map((t) => t.map(([x, y, z]) => [x, y, z + zBase])) : out;
}

// R12 : option { depouille } — le corps sous le biseau prend la dépouille,
// les marches du biseau partent du retrait atteint à z = h − b (une
// dépouille négative retourne le corps : le biseau part du contour dessiné)
export function extruder_biseau(mz, multi, hauteur, biseau, pasMm = 0.2, { depouille = 0 } = {}) {
  const h = +hauteur, b = +biseau, dp = +depouille || 0;
  if (!(h > 0)) throw new Error("biseau : hauteur > 0 requise");
  if (!(b >= 0)) throw new Error("biseau : retrait ≥ 0 requis");
  if (b >= h) throw new Error("biseau : le retrait doit rester sous la hauteur");
  if (b === 0) return extruder_depouille(mz, multi, h, dp, pasMm);
  const n = Math.max(1, Math.ceil(b / Math.max(0.05, +pasMm || 0.2)));
  const dz = b / n;
  const tris = extruder_depouille(mz, multi, h - b, dp, pasMm);
  const r0 = dp > 0 ? (h - b) * Math.tan(dp * Math.PI / 180) : 0;
  for (let k = 1; k <= n; k++) {
    const m = inset_multi(mz, multi, r0 + (b * k) / n);
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
                    terrain: t.terrain, couleur: (fiche && _hex6(fiche.couleur)) || "#888888", hauteur_mm: hauteur, centre_mm: [cx * sMm, -cy * sMm],
                    tris: hauteur > 0 ? extruder([[ring]], hauteur, 0) : [] };
    if (!fiche) piece.inconnu = true;
    out.push(piece);
  }
  return out;
}

/* ── GLB minimal : un mesh, UNE PRIMITIVE PAR PIÈCE (POSITION + NORMAL, sans
   index), un matériau par pièce (baseColorFactor sRGB → linéaire) ── */
export function glb_de_pieces(pieces) {
  const P = (pieces || []).filter((p) => p && p.tris && p.tris.length);
  if (!P.length) throw new Error("GLB : aucun triangle");
  const buffers = [], views = [], accessors = [], materials = [], primitives = [];
  let off = 0;
  for (const piece of P) {
    const n = piece.tris.length * 3;
    const pos = new Float32Array(n * 3), nrm = new Float32Array(n * 3);
    const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
    let k = 0;
    for (const [a, b, c] of piece.tris) {
      const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
      const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
      let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      const l = Math.hypot(nx, ny, nz) || 1;
      nx /= l; ny /= l; nz /= l;
      for (const p of [a, b, c]) {
        pos[k * 3] = p[0]; pos[k * 3 + 1] = p[1]; pos[k * 3 + 2] = p[2];
        nrm[k * 3] = nx; nrm[k * 3 + 1] = ny; nrm[k * 3 + 2] = nz;
        for (let i = 0; i < 3; i++) { min[i] = Math.min(min[i], p[i]); max[i] = Math.max(max[i], p[i]); }
        k++;
      }
    }
    const vPos = views.length;
    views.push({ buffer: 0, byteOffset: off, byteLength: pos.byteLength, target: 34962 });
    buffers.push(pos); off += pos.byteLength;
    views.push({ buffer: 0, byteOffset: off, byteLength: nrm.byteLength, target: 34962 });
    buffers.push(nrm); off += nrm.byteLength;
    const aPos = accessors.length;
    accessors.push({ bufferView: vPos, componentType: 5126, count: n, type: "VEC3", min, max });
    accessors.push({ bufferView: vPos + 1, componentType: 5126, count: n, type: "VEC3" });
    materials.push({ name: piece.nom || `piece${materials.length}`,
      pbrMetallicRoughness: { baseColorFactor: hex_vers_facteur(piece.couleur), metallicFactor: 0, roughnessFactor: 0.6 } });
    primitives.push({ attributes: { POSITION: aPos, NORMAL: aPos + 1 }, mode: 4, material: materials.length - 1 });
  }
  // les Float32 sont des multiples de 4 : aucun bourrage entre pièces
  const json = {
    asset: { version: "2.0", generator: "Deepotus Vectorlab" },
    scene: 0, scenes: [{ nodes: [0] }], nodes: [{ mesh: 0 }],
    meshes: [{ primitives }], materials,
    buffers: [{ byteLength: off }], bufferViews: views, accessors,
  };
  let js = JSON.stringify(json);
  while (js.length % 4) js += " ";
  const jsBytes = new TextEncoder().encode(js);
  const total = 12 + 8 + jsBytes.length + 8 + off;
  const out = new Uint8Array(total);
  const dv = new DataView(out.buffer);
  dv.setUint32(0, 0x46546C67, true); dv.setUint32(4, 2, true); dv.setUint32(8, total, true);
  dv.setUint32(12, jsBytes.length, true); dv.setUint32(16, 0x4E4F534A, true);
  out.set(jsBytes, 20);
  const offBin = 20 + jsBytes.length;
  dv.setUint32(offBin, off, true); dv.setUint32(offBin + 4, 0x004E4942, true);
  let cur = offBin + 8;
  for (const b of buffers) { out.set(new Uint8Array(b.buffer), cur); cur += b.byteLength; }
  return out;
}
export function glb_de_triangles(tris) {
  return glb_de_pieces([{ nom: "piece", tris, couleur: COULEUR_DEFAUT }]);
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
