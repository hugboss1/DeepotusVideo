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


/* ── R12 : couleurs de pièce, GLB multi-matériaux ── */
{
  const { COULEUR_DEFAUT, couleur_de_piece, couleur_dominante, hex_vers_facteur, glb_de_pieces } = await import("../js/mod-solide.js");
  const T = TERRAINS_DEFAUT;
  ok("tuile → couleur de la fiche du terrain", couleur_de_piece({ type: "tuile", terrain: "foret" }, T) === "#3F7D3A");
  ok("tuile de terrain inconnu → gris de terrains_de", couleur_de_piece({ type: "tuile", terrain: "lave" }, T) === "#888888");
  ok("fond hex → ce fond", couleur_de_piece({ type: "rect", style: { fond: "#ff0000" } }, T) === "#ff0000");
  ok("fond dégradé → le contour hex", couleur_de_piece({ type: "path", style: { fond: "grad:g1", contour: { couleur: "#00ff00", epaisseur: 2 } } }, T) === "#00ff00");
  ok("sans fond ni contour → COULEUR_DEFAUT (le blanc cassé d'avant)", couleur_de_piece({ type: "path", style: { fond: "none" } }, T) === COULEUR_DEFAUT && COULEUR_DEFAUT === "#D1C7B3");
  ok("dominante = vote, pas moyenne", couleur_dominante([{ style: { fond: "#ff0000" } }, { style: { fond: "#0000ff" } }, { style: { fond: "#ff0000" } }], T) === "#ff0000");
  ok("dominante d'une liste vide → défaut", couleur_dominante([], T) === COULEUR_DEFAUT);
  const f = hex_vers_facteur("#ff8000");
  ok("facteur glTF linéarisé : #ff8000 → [1, ≈0,216, 0, 1]", f.length === 4 && f[0] === 1 && pres(f[1], 0.2158, 0.002) && f[2] === 0 && f[3] === 1, JSON.stringify(f));
  ok("hex court accepté, invalide → défaut", hex_vers_facteur("#fff")[0] === 1 && pres(hex_vers_facteur("bleu")[0], hex_vers_facteur(COULEUR_DEFAUT)[0], 1e-9));
  const a = extruder([[carre(0, 0, 10)]], 2, 0), b = extruder([[carre(20, 0, 10)]], 3, 0);
  const glb = glb_de_pieces([{ nom: "a", tris: a, couleur: "#ff0000" }, { nom: "b", tris: b, couleur: "#0000ff" }]);
  const dv = new DataView(glb.buffer);
  const jlen = dv.getUint32(12, true);
  const json = JSON.parse(new TextDecoder().decode(glb.subarray(20, 20 + jlen)));
  ok("GLB : 2 primitives, 2 matériaux, chacune sur son matériau", json.meshes[0].primitives.length === 2 && json.materials.length === 2
     && json.meshes[0].primitives[0].material === 0 && json.meshes[0].primitives[1].material === 1, JSON.stringify(json.meshes));
  ok("GLB : matériaux de couleurs DIFFÉRENTES (rouge puis bleu)", json.materials[0].pbrMetallicRoughness.baseColorFactor[0] === 1 && json.materials[1].pbrMetallicRoughness.baseColorFactor[2] === 1
     && json.materials[0].pbrMetallicRoughness.baseColorFactor[2] === 0);
  ok("GLB : accessors comptent les sommets de chaque pièce", json.accessors[0].count === a.length * 3 && json.accessors[2].count === b.length * 3);
  ok("GLB : longueur totale = en-tête + JSON + BIN", dv.getUint32(8, true) === glb.length && glb.length % 4 === 0);
  const g1 = glb_de_triangles(a), j1 = JSON.parse(new TextDecoder().decode(g1.subarray(20, 20 + new DataView(g1.buffer).getUint32(12, true))));
  ok("glb_de_triangles reste : une primitive, le matériau par défaut", j1.materials.length === 1 && pres(j1.materials[0].pbrMetallicRoughness.baseColorFactor[0], hex_vers_facteur(COULEUR_DEFAUT)[0], 1e-6));
  const g = grille_normaliser({ type: "hex", pas: 20 });
  const P = plateau_pieces([{ id: "t1", type: "tuile", q: 0, r: 0, terrain: "mer" }], T, g, { socle_mm: 2, sMm: 1 });
  ok("plateau_pieces pose la couleur de la fiche", P[0].couleur === "#2B5F9E");
}

/* ── R12 : dépouille (angle des flancs) ── */
{
  const { extruder_depouille, retourner_z } = await import("../js/mod-solide.js");
  const base = [[carre(0, 0, 20)]];
  const largeurA = (tris, z, tol = 1e-6) => {   // largeur en x de la tranche à la cote z (sommets à cette cote)
    let mn = Infinity, mx = -Infinity;
    for (const t of tris) for (const p of t) if (Math.abs(p[2] - z) <= tol) { mn = Math.min(mn, p[0]); mx = Math.max(mx, p[0]); }
    return mx - mn;
  };
  const droit = extruder_depouille(mz, base, 5, 0);
  ok("angle 0 = extrusion droite (même volume)", pres(volume_de(droit), 2000, 1e-6));
  const pos = extruder_depouille(mz, base, 5, 30);
  // la base est EXACTE (la forme dessinée) ; le sommet porte l'erreur d'UNE marche par flanc (retrait / n ≤ 0,2 mm)
  const retrait30 = 5 * Math.tan(Math.PI / 6), marche = retrait30 / Math.min(24, Math.ceil(retrait30 / 0.2));
  ok("angle +30° : base 20, sommet rétréci de 2·5·tan30 ≈ 5,77 à une marche près", pres(largeurA(pos, 0), 20, 1e-6) && pres(largeurA(pos, 5), 20 - 2 * retrait30, 2 * marche + 1e-6) && largeurA(pos, 5) <= 20 - 2 * retrait30 + 2 * marche + 1e-6, `${largeurA(pos, 0)} / ${largeurA(pos, 5)} (marche ${marche})`);
  ok("angle +30° : volume entre celui du sommet et celui de la base", volume_de(pos) < 2000 && volume_de(pos) > (20 - 5.77) ** 2 * 5, volume_de(pos));
  const neg = extruder_depouille(mz, base, 5, -30);
  ok("angle −30° : le SOMMET garde 20, la base est rétrécie", pres(largeurA(neg, 5), 20, 1e-6) && largeurA(neg, 0) < 15, `${largeurA(neg, 0)} / ${largeurA(neg, 5)}`);
  ok("angle −30° : même volume que +30° (miroir en z), et fermé (volume > 0)", pres(volume_de(neg), volume_de(pos), 1e-6) && volume_de(neg) > 0);
  ok("z min 0 après retournement", Math.min(...neg.flatMap((t) => t.map((p) => p[2]))) >= -1e-9);
  let refus = 0;
  try { extruder_depouille(mz, base, 5, 60); } catch { refus++; }
  try { extruder_depouille(mz, base, 0, 10); } catch { refus++; }
  ok("angle > 45° et hauteur 0 refusés", refus === 2);
  ok("retourner_z : z → h − z, orientation inversée (volume conservé positif)", pres(volume_de(retourner_z(droit, 5)), 2000, 1e-6));
  const pointe = extruder_depouille(mz, base, 30, 45);  // retrait 30 > demi-côté 10 : la pointe se ferme d'elle-même
  ok("la pointe se ferme sans erreur (pyramide tronquée en marches)", volume_de(pointe) > 0 && volume_de(pointe) < 20 * 20 * 30);
  const combo = extruder_biseau(mz, base, 5, 1, 0.2, { depouille: 20 });
  ok("biseau + dépouille : sommet plus étroit que la dépouille seule", largeurA(combo, 5) < largeurA(extruder_depouille(mz, base, 5, 20), 5) - 1);
  ok("biseau sans option : inchangé", pres(volume_de(extruder_biseau(mz, base, 5, 1, 0.2)), volume_de(extruder_biseau(mz, base, 5, 1)), 1e-9));
}
/* ── lot 3 : pixel-art → pièces (rectangles de pixels, une pièce et une hauteur par couleur) ── */
{
  const { rects_de_pixels, pixels_vers_pieces, hauteurs_par_luminosite } = await import("../js/mod-solide.js");
  const img = { w: 4, h: 3, data: new Uint8ClampedArray(4 * 3 * 4) };
  const pose = (x, y, rgb) => { const k = (y * 4 + x) * 4; img.data[k] = rgb[0]; img.data[k + 1] = rgb[1]; img.data[k + 2] = rgb[2]; img.data[k + 3] = 255; };
  pose(0, 0, [255, 0, 0]); pose(1, 0, [255, 0, 0]); pose(0, 1, [255, 0, 0]); pose(1, 1, [255, 0, 0]); pose(3, 2, [255, 0, 0]);
  pose(2, 0, [0, 0, 255]); pose(2, 1, [0, 0, 255]); pose(2, 2, [0, 0, 255]);
  const rr = rects_de_pixels(img, "#FF0000");
  ok("rouge : 2 rectangles (le bloc 2 × 2 fusionné, le pixel isolé)", rr.length === 2 && rr.some((r) => r.w === 2 && r.h === 2) && rr.some((r) => r.w === 1 && r.h === 1), JSON.stringify(rr));
  ok("bleu : 1 rectangle 1 × 3 (runs fusionnés verticalement)", JSON.stringify(rects_de_pixels(img, "#0000FF")) === JSON.stringify([{ x: 2, y: 0, w: 1, h: 3 }]), JSON.stringify(rects_de_pixels(img, "#0000FF")));
  const P = pixels_vers_pieces(img, 2, { "#FF0000": 4, "#0000FF": 1.5 }, { socle_mm: 0 });
  const aire = (tris) => tris.filter((t) => t[0][2] === t[1][2] && t[1][2] === t[2][2] && t[0][2] > 0).reduce((s, [a, b, c]) => s + Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2, 0);
  ok("deux pièces nommées par hex, colorées, à leur hauteur", P.length === 2 && P[0].nom === "px_ff0000" && P[0].couleur === "#FF0000" && P[0].hauteur_mm === 4 && P[1].hauteur_mm === 1.5, JSON.stringify(P.map((p) => [p.nom, p.couleur, p.hauteur_mm])));
  ok("aire du capot rouge = 5 pixels × 4 mm² = 20 ; bleu = 3 × 4 = 12", pres(aire(P[0].tris), 20, 1e-6) && pres(aire(P[1].tris), 12, 1e-6), `${aire(P[0].tris)} / ${aire(P[1].tris)}`);
  ok("volume rouge = 20 × 4 = 80", pres(volume_de(P[0].tris), 80, 1e-6), volume_de(P[0].tris));
  ok("y retourné : les pièces ont des y ≤ 0 (plateau y-haut)", P[0].tris.flat().some((p) => p[1] < 0) && !P[0].tris.flat().some((p) => p[1] > 0));
  const S = pixels_vers_pieces(img, 2, { "#FF0000": 4, "#0000FF": 1.5 }, { socle_mm: 1 });
  ok("socle : une pièce de plus, 8 × 6 × 1 mm sous les pièces, pièces posées à z = 1", S.length === 3 && S[2].nom === "socle" && pres(volume_de(S[2].tris), 48, 1e-6) && Math.min(...S[0].tris.flat().map((p) => p[2])) === 1, S.length);
  ok("couleur sans hauteur → hauteur par défaut 2", pixels_vers_pieces(img, 2, {}, {})[0].hauteur_mm === 2);
  const H = hauteurs_par_luminosite(["#000000", "#FFFFFF", "#808080"], 1, 5);
  ok("hauteurs par luminosité : noir 1, blanc 5, gris ≈ 3", H["#000000"] === 1 && H["#FFFFFF"] === 5 && pres(H["#808080"], 3, 0.1), JSON.stringify(H));
  ok("une seule couleur → max", hauteurs_par_luminosite(["#123456"], 1, 5)["#123456"] === 5);
}
if (echecs.length) {
  console.error("ECHECS solide :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA solide : PASS (62 controles)");
