// mod-aimant.js — l'aimantation aux OBJETS (lot C, § 2.5 d'Affinity) : une
// boîte en mouvement s'aligne sur les bords et les centres de ses voisins
// (bords contre bords, centre sur centre, bord contre bord opposé =
// accolement) et sur les écarts réguliers entre voisins. Module FEUILLE,
// pur : les boîtes sont FOURNIES par l'appelant (l'écran mesure).
// un bord ne s'aligne que sur un bord, un centre que sur un centre — le
// banc a démasqué la version « tout contre tout » (un bord droit s'aimantait
// au centre d'un voisin, une pose qu'aucun utilisateur ne veut)
function _axe(paires, tol) {
  let meilleur = null, ecart = tol + 1e-9;
  for (const [vals, cibles] of paires) for (const v of vals) for (const c of cibles) {
    const e = Math.abs(c - v);
    if (e < ecart) { ecart = e; meilleur = { d: c - v, pos: c }; }
  }
  return meilleur;
}
export function aimant_objets(b, candidats, tol) {
  const out = { dx: 0, dy: 0, lignes: [] };
  if (!candidats || !candidats.length) return out;
  const bx = [], cxm = [], by = [], cym = [];
  for (const c of candidats) {
    bx.push(c.x, c.x + c.w); cxm.push(c.x + c.w / 2);
    by.push(c.y, c.y + c.h); cym.push(c.y + c.h / 2);
  }
  const mx = _axe([[[b.x, b.x + b.w], bx], [[b.x + b.w / 2], cxm]], tol);
  const my = _axe([[[b.y, b.y + b.h], by], [[b.y + b.h / 2], cym]], tol);
  if (mx) { out.dx = mx.d; out.lignes.push({ axe: "v", pos: mx.pos, type: "bord" }); }
  if (my) { out.dy = my.d; out.lignes.push({ axe: "h", pos: my.pos, type: "bord" }); }
  return out;
}
function _ecartsAxe(cands, k0, k1) {
  // positions candidates pour reproduire l'écart entre deux voisins
  // ADJACENTS le long de l'axe (k0 = "x"|"y", k1 = "w"|"h")
  const tri = cands.slice().sort((a, c) => a[k0] - c[k0]);
  const cibles = [];
  for (let i = 0; i + 1 < tri.length; i++) {
    const A = tri[i], Bv = tri[i + 1];
    const g = Bv[k0] - (A[k0] + A[k1]);
    if (g < 0) continue;
    cibles.push({ debut: Bv[k0] + Bv[k1] + g, fin: A[k0] - g });     // après B, avant A
  }
  return cibles;
}
export function aimant_ecarts(b, candidats, tol) {
  const out = { dx: 0, dy: 0, lignes: [] };
  if (!candidats || candidats.length < 2) return out;
  for (const [k0, k1, dk, axe] of [["x", "w", "dx", "v"], ["y", "h", "dy", "h"]]) {
    let meilleur = null, ecart = tol + 1e-9;
    for (const c of _ecartsAxe(candidats, k0, k1)) {
      for (const [v, cible] of [[b[k0], c.debut], [b[k0] + b[k1], c.fin]]) {
        const e = Math.abs(cible - v);
        if (e < ecart) { ecart = e; meilleur = { d: cible - v, pos: cible }; }
      }
    }
    if (meilleur) { out[dk] = meilleur.d; out.lignes.push({ axe, pos: meilleur.pos, type: "ecart" }); }
  }
  return out;
}
export function aimant_fusion(resultats) {
  const out = { dx: 0, dy: 0, lignes: [] };
  for (const r of resultats) {
    if (!out.dx && r.dx) out.dx = r.dx;
    if (!out.dy && r.dy) out.dy = r.dy;
    out.lignes.push(...(r.lignes || []));
  }
  return out;
}
