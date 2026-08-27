// extrude.test.mjs — impression 3D (phase 3 du plan slicer) : triangulation
// par oreilles à ponts de trous, prisme fermé, STL binaire. PUR — aucun
// martinez ici (l'union des calques vit dans l'UI, déjà éprouvée).
import { trianguler, extruder, stl_binaire, volume_de }
  from "../js/mod-extrude.js";
import { aire_multi } from "../js/mod-bool.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

const carre = (x, y, c) => [[x, y], [x + c, y], [x + c, y + c], [x, y + c],
                            [x, y]];
const inverse = (r) => r.slice().reverse();
const aire2d = (tris) => tris.reduce((s, [a, b, c]) =>
  s + Math.abs((b[0] - a[0]) * (c[1] - a[1])
             - (b[1] - a[1]) * (c[0] - a[0])) / 2, 0);

/* ── triangulation : aires exactes, simple / trou / concave / orientations ── */
{
  const t = trianguler([[carre(0, 0, 10)]]);
  ok("carré simple → 2 triangles d'aire 100", t.length === 2
     && Math.abs(aire2d(t) - 100) < 1e-9, `${t.length} tris, ${aire2d(t)}`);
}
{
  const multi = [[carre(0, 0, 20), inverse(carre(5, 5, 10))]];
  const t = trianguler(multi);
  const attendu = Math.abs(aire_multi(multi));
  ok("carré à trou : l'aire triangulée = aire_multi (300) à ±0,5 %",
     Math.abs(aire2d(t) - attendu) / attendu < 0.005
     && Math.abs(attendu - 300) < 1e-6, `${aire2d(t)} vs ${attendu}`);
}
{
  // un L concave (6 sommets, aire 300)
  const L = [[0, 0], [20, 0], [20, 10], [10, 10], [10, 20], [0, 20], [0, 0]];
  const t = trianguler([[L]]);
  ok("L concave → 4 triangles d'aire 300", t.length === 4
     && Math.abs(aire2d(t) - 300) < 1e-9, `${t.length}, ${aire2d(t)}`);
}
{
  // orientations inversées en ENTRÉE : le normaliseur les redresse
  const multi = [[inverse(carre(0, 0, 20)), carre(5, 5, 10)]];
  const t = trianguler(multi);
  ok("orientations inversées tolérées (aire 300)",
     Math.abs(aire2d(t) - 300) < 1e-6, aire2d(t));
}

/* ── extrusion : volume exact, maillage FERMÉ, zBase ── */
function fermeture(tris) {
  // chaque arête ORIENTÉE doit avoir son inverse — 2-variété orientée close
  const cle = (p) => p.map((v) => v.toFixed(6)).join(",");
  const comptes = new Map();
  for (const [a, b, c] of tris) {
    for (const [p, q] of [[a, b], [b, c], [c, a]]) {
      comptes.set(cle(p) + "|" + cle(q),
                  (comptes.get(cle(p) + "|" + cle(q)) || 0) + 1);
    }
  }
  for (const [k, n] of comptes) {
    const [p, q] = k.split("|");
    if (n !== (comptes.get(q + "|" + p) || 0)) return false;
  }
  return true;
}
{
  const tris = extruder([[carre(0, 0, 10)]], 5);
  ok("prisme du carré : 12 triangles", tris.length === 12, tris.length);
  ok("volume = aire × hauteur (500)",
     Math.abs(volume_de(tris) - 500) < 1e-6, volume_de(tris));
  ok("maillage fermé (chaque arête et son inverse)", fermeture(tris));
  const zs = tris.flat().map((v) => v[2]);
  ok("z ∈ [0, 5]", Math.min(...zs) === 0 && Math.max(...zs) === 5);
}
{
  const tris = extruder([[carre(0, 0, 20), inverse(carre(5, 5, 10))]], 3);
  ok("prisme à trou : volume (400−100)×3 = 900 à ±0,5 %",
     Math.abs(volume_de(tris) - 900) / 900 < 0.005, volume_de(tris));
  ok("prisme à trou : fermé", fermeture(tris));
}
{
  const tris = extruder([[carre(0, 0, 10)]], 5, 10);
  const zs = tris.flat().map((v) => v[2]);
  ok("zBase respecté (z ∈ [10, 15])",
     Math.min(...zs) === 10 && Math.max(...zs) === 15);
  let refus = 0;
  try { extruder([[carre(0, 0, 10)]], 0); } catch { refus++; }
  ok("hauteur nulle refusée", refus === 1);
}

/* ── STL binaire : octets exacts ── */
{
  const tris = extruder([[carre(0, 0, 10)]], 5);
  const stl = stl_binaire(tris);
  ok("STL : 84 + 50×n octets", stl.length === 84 + 50 * tris.length,
     stl.length);
  const dv = new DataView(stl.buffer, stl.byteOffset, stl.byteLength);
  ok("STL : compte de triangles", dv.getUint32(80, true) === tris.length);
}

if (echecs.length) {
  console.error("ECHECS extrude :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA extrude : PASS (13 controles)");
