// solide.test.mjs — lot D : retrait par différence (martinez vendorisé),
// biseau en marches, évidement à mur minimal, pièces d'un plateau de
// tuiles, GLB minimal, nomenclature. Les volumes se MESURENT (volume_de).
import { createRequire } from "node:module";
import { fournirMartinez } from "../js/mod-bool.js";
import { volume_de, extruder } from "../js/mod-extrude.js";
import { MUR_MIN_MM, inset_multi, extruder_biseau, extruder_evide, plateau_pieces,
         glb_de_triangles, nomenclature_csv } from "../js/mod-solide.js";
import { grille_normaliser, hex_centre } from "../js/mod-grille.js";
import { TERRAINS_DEFAUT } from "../js/mod-doc.js";

const mz = createRequire(import.meta.url)("../vendor/martinez.umd.js");
fournirMartinez(mz);
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (a, b, tol) => Math.abs(a - b) <= tol;
const carre = (x, y, c) => [[x, y], [x + c, y], [x + c, y + c], [x, y + c], [x, y]];
const aireMulti = (mp) => mp.reduce((s, poly) => s + poly.reduce((t, ring, i) => {
  let a = 0;
  for (let k = 0; k + 1 < ring.length; k++) a += ring[k][0] * ring[k + 1][1] - ring[k + 1][0] * ring[k][1];
  return t + (i === 0 ? Math.abs(a) : -Math.abs(a)) / 2;
}, 0), 0);

/* ── retrait ── */
{
  const m = [[carre(0, 0, 20)]];
  const r = inset_multi(mz, m, 2);
  ok("retrait 2 d'un carré 20 → aire ≈ 16² (±3 %)", pres(aireMulti(r), 256, 8), aireMulti(r));
  ok("retrait trop grand → multi vide", inset_multi(mz, m, 11).length === 0);
  ok("retrait 0 → inchangé", pres(aireMulti(inset_multi(mz, m, 0)), 400, 1e-6));
  let refus = 0; try { inset_multi(mz, m, -1); } catch { refus++; }
  ok("retrait négatif refusé", refus === 1);
}
/* ── biseau : le volume est entre le prisme rétréci et le prisme plein ── */
{
  const m = [[carre(0, 0, 20)]];
  const plein = volume_de(extruder(m, 5));                       // 2000
  const tris = extruder_biseau(mz, m, 5, 2, 0.5);                 // biseau 2 mm en marches de 0,5
  const v = volume_de(tris);
  ok("biseau : volume < plein, > prisme à retrait plein", v < plein - 1 && v > volume_de(extruder(inset_multi(mz, m, 2), 5)), `${v} / ${plein}`);
  // chanfrein exact : 20²·3 + ∫₀² (20−2t)² dt = 1200 + 592 = 1792 ; les marches surestiment un peu
  ok("biseau : volume dans [1790, 1900]", v >= 1790 && v <= 1900, v);
  ok("biseau : z max = hauteur", Math.max(...tris.flat().map((p) => p[2])) === 5);
  let refus = 0;
  for (const [h, b] of [[5, 5], [5, -1], [0, 1]]) { try { extruder_biseau(mz, m, h, b, 0.5); } catch { refus++; } }
  ok("biseau refuse b ≥ h, b < 0, h ≤ 0", refus === 3, String(refus));
  ok("biseau 0 = prisme simple", pres(volume_de(extruder_biseau(mz, m, 5, 0, 0.5)), plein, 1e-6));
}
/* ── évidement : mur et plancher ── */
{
  const m = [[carre(0, 0, 20)]];
  const tris = extruder_evide(mz, m, 10, 2, 1);                   // mur 2, plancher 1
  const v = volume_de(tris);
  // plancher 20²·1 = 400 + murs (400 − 256)·9 = 1296 → 1696 (±3 %)
  ok("évidé : volume ≈ 1696", pres(v, 1696, 55), v);
  let refus = 0;
  try { extruder_evide(mz, m, 10, 0.5, 1); } catch (e) { refus += /mur/.test(e.message) ? 1 : 0; }
  try { extruder_evide(mz, m, 10, 11, 1); } catch (e) { refus += /forme/.test(e.message) ? 1 : 0; }
  try { extruder_evide(mz, m, 1, 2, 1); } catch { refus++; }
  ok("évidé refuse mur < MUR_MIN_MM (dit « mur »), mur qui vide la forme (dit « forme »), plancher ≥ h",
     refus === 3 && MUR_MIN_MM === 0.8, String(refus));
}
/* ── plateau : une pièce par tuile, socle + hauteur du terrain ── */
{
  const g = grille_normaliser({ type: "hex", pas: 40 });
  const tuiles = [{ id: "t1", type: "tuile", q: 0, r: 0, terrain: "plaine" },
                  { id: "t2", type: "tuile", q: 1, r: 0, terrain: "montagne", hauteur_mm: 12 },
                  { id: "t3", type: "tuile", q: 0, r: 1, terrain: "inconnu" }];
  const pieces = plateau_pieces(tuiles, TERRAINS_DEFAUT, g, { socle_mm: 2, sMm: 25.4 / 96 });
  ok("3 pièces, nommées par cellule", pieces.length === 3 && pieces[0].nom === "tuile_0_0" && pieces[1].terrain === "montagne", JSON.stringify(pieces.map((p) => p.nom)));
  ok("hauteur = socle + terrain ; surcharge de la tuile", pieces[0].hauteur_mm === 4 && pieces[1].hauteur_mm === 14);
  ok("terrain inconnu → socle seul, dit", pieces[2].hauteur_mm === 2 && pieces[2].inconnu === true);
  const s = 40 * 25.4 / 96;                                        // rayon en mm
  const aireHex = 3 * Math.sqrt(3) / 2 * s * s;
  ok("volume de la première pièce = aire hex × 4 mm (±1 %)", pres(volume_de(pieces[0].tris), aireHex * 4, aireHex * 4 * 0.01), volume_de(pieces[0].tris));
  ok("y retourné (plateau y-haut) : centre en y négatif pour r > 0", pieces[2].tris.flat().every((p) => p[1] <= 1e-6) && hex_centre(0, 1, g)[1] > 0);
  ok("chaque pièce porte son centre mm", Array.isArray(pieces[1].centre_mm) && pieces[1].centre_mm.length === 2);
  ok("état vide : aucune tuile → []", plateau_pieces([], TERRAINS_DEFAUT, g, { socle_mm: 2, sMm: 1 }).length === 0);
  ok("nom sans signe moins (m)", plateau_pieces([{ type: "tuile", q: -2, r: 1, terrain: "mer" }], TERRAINS_DEFAUT, g, { socle_mm: 1, sMm: 1 })[0].nom === "tuile_m2_1");
}
/* ── GLB minimal ── */
{
  const tris = extruder([[carre(0, 0, 10)]], 3);
  const glb = glb_de_triangles(tris);
  const dv = new DataView(glb.buffer, glb.byteOffset, glb.byteLength);
  ok("magic glTF, version 2, longueur totale", dv.getUint32(0, true) === 0x46546C67 && dv.getUint32(4, true) === 2 && dv.getUint32(8, true) === glb.byteLength);
  const lenJson = dv.getUint32(12, true);
  ok("chunk JSON puis BIN", dv.getUint32(16, true) === 0x4E4F534A && dv.getUint32(20 + lenJson + 4, true) === 0x004E4942);
  const json = JSON.parse(new TextDecoder().decode(glb.slice(20, 20 + lenJson)).trim());
  ok("un maillage, POSITION + NORMAL, count = 3 × triangles", json.meshes.length === 1
     && json.accessors[json.meshes[0].primitives[0].attributes.POSITION].count === tris.length * 3
     && json.accessors[json.meshes[0].primitives[0].attributes.NORMAL].count === tris.length * 3, JSON.stringify(json.accessors));
  ok("bornes min/max de la POSITION", JSON.stringify(json.accessors[0].min) === "[0,0,0]" && JSON.stringify(json.accessors[0].max) === "[10,10,3]", JSON.stringify(json.accessors[0]));
  ok("longueurs multiples de 4", lenJson % 4 === 0 && dv.getUint32(20 + lenJson, true) % 4 === 0);
  let refus = 0; try { glb_de_triangles([]); } catch { refus++; }
  ok("aucun triangle → refus", refus === 1);
}
/* ── nomenclature ── */
{
  const csv = nomenclature_csv([{ nom: "tuile_0_0", q: 0, r: 0, terrain: "plaine", hauteur_mm: 4, tris: [1, 2] },
                                { nom: "tuile_1_0", q: 1, r: 0, terrain: "mont;agne", hauteur_mm: 14, tris: [1] }]);
  const lignes = csv.trim().split("\n");
  ok("en-tête + 2 lignes, ; échappé par guillemets", lignes.length === 3 && lignes[0] === "piece;q;r;terrain;hauteur_mm;triangles"
     && lignes[2] === 'tuile_1_0;1;0;"mont;agne";14;1', csv);
}

if (echecs.length) {
  console.error("ECHECS solide :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA solide : PASS (26 controles)");
