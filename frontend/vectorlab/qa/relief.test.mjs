// relief.test.mjs — mod-relief (lot H) : grille de hauteurs → plaque fermée
// (surface, socle, murs), gravure du tracé, découpe en dalles numérotées,
// sous-grille. Les volumes se mesurent ; l'étanchéité se compte par arêtes.
import { plaque, graver, dalles, sous_grille } from "../js/mod-relief.js";
import { volume_de } from "../js/mod-extrude.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (a, b, tol) => Math.abs(a - b) <= tol;
// une plaque est étanche si chaque arête orientée (a→b) a son opposée (b→a)
function etanche(tris) {
  const cle = (p) => p.map((v) => Math.round(v * 1e6) / 1e6).join(",");
  const aretes = new Map();
  for (const [a, b, c] of tris) for (const [p, q] of [[a, b], [b, c], [c, a]]) {
    const k = cle(p) + ">" + cle(q);
    aretes.set(k, (aretes.get(k) || 0) + 1);
  }
  for (const [k, n] of aretes) {
    const [p, q] = k.split(">");
    if (n !== 1 || aretes.get(q + ">" + p) !== 1) return false;
  }
  return true;
}

/* ── plaque plate : 3×3 cellules de hauteur 10 m, 30 mm de large ── */
{
  const grid = new Array(9).fill(10);
  const tris = plaque(grid, 3, 3, { largeur_mm: 30, socle_mm: 2, mm_par_m: 0.1, exageration: 1, z_min: 0 });
  const v = volume_de(tris);
  ok("volume = 30 × 30 × (2 + 10·0,1) = 2700 mm³", pres(v, 2700, 1e-6), v);
  ok("z max = socle + hauteur = 3 mm ; z min = 0", pres(Math.max(...tris.flat().map((p) => p[2])), 3, 1e-9) && pres(Math.min(...tris.flat().map((p) => p[2])), 0, 1e-9));
  ok("étanche : chaque arête a son opposée", etanche(tris));
  ok("8 triangles de surface + 8 de fond + 4 côtés × 2 cellules × 2 = 32", tris.length === 32, tris.length);
  // exagération ×3 : la surface monte, le socle non
  const t3 = plaque(grid, 3, 3, { largeur_mm: 30, socle_mm: 2, mm_par_m: 0.1, exageration: 3, z_min: 0 });
  ok("exagération 3 : z max = 2 + 3", pres(Math.max(...t3.flat().map((p) => p[2])), 5, 1e-9));
  // z_min : la hauteur de référence — une grille entre 100 et 110 m avec z_min 100 donne le même solide
  const g2 = new Array(9).fill(110);
  ok("z_min soustrait : 110 m avec z_min 100 = 10 m", pres(volume_de(plaque(g2, 3, 3, { largeur_mm: 30, socle_mm: 2, mm_par_m: 0.1, exageration: 1, z_min: 100 })), 2700, 1e-6));
  // la hauteur de la plaque suit le ratio w/h de la grille : 4×2 cellules → 30 × 10 mm
  const g4 = new Array(8).fill(0);
  const t4 = plaque(g4, 4, 2, { largeur_mm: 30, socle_mm: 1, mm_par_m: 0.1, exageration: 1, z_min: 0 });
  ok("plaque 4×2 : 30 mm × 10 mm, socle seul → 300 mm³", pres(volume_de(t4), 300, 1e-6), volume_de(t4));
  let refus = 0;
  try { plaque([1, 2], 2, 1, { largeur_mm: 30, socle_mm: 1, mm_par_m: 0.1 }); } catch { refus++; }
  try { plaque(grid, 3, 3, { largeur_mm: 30, socle_mm: 0, mm_par_m: 0.1 }); } catch { refus++; }
  ok("refus : grille < 2×2 ; socle ≤ 0", refus === 2, String(refus));
}
/* ── gravure ── */
{
  const grid = new Array(25).fill(100);           // 5×5
  const g = graver(grid, 5, 5, [[[0, 2], [4, 2]]], 20, 0.6);   // une ligne horizontale au milieu
  ok("copie : l'original n'est pas touché", grid.every((v) => v === 100));
  ok("la ligne du milieu est abaissée de 20, les autres non", [10, 11, 12, 13, 14].every((i) => g[i] === 80) && [0, 4, 20, 24, 7].every((i) => g[i] === 100), g.join(","));
  ok("rayon 1,2 : les lignes voisines aussi", graver(grid, 5, 5, [[[0, 2], [4, 2]]], 20, 1.2)[7] === 80);
}
/* ── dalles ── */
{
  // 9 sommets = 8 cellules en x, 5 sommets = 4 cellules en y ; 3 cellules par dalle
  const d = dalles(9, 5, 3);
  ok("9×5 en dalles de 3 cellules : 3 × 2 = 6 dalles, bord PARTAGÉ (la dalle suivante repart du dernier sommet)", d.length === 6
     && d[0].x0 === 0 && d[0].w === 4 && d[1].x0 === 3 && d[1].w === 4 && d[2].x0 === 6 && d[2].w === 3
     && d[3].y0 === 3 && d[3].h === 2, JSON.stringify(d));
  ok("noms numérotés ligne_colonne", d[0].nom === "dalle_1_1" && d[1].nom === "dalle_1_2" && d[3].nom === "dalle_2_1", JSON.stringify(d.map((x) => x.nom)));
  ok("9×5 en dalles de 4 : 2 dalles côte à côte", dalles(9, 5, 4).length === 2 && dalles(9, 5, 4)[1].x0 === 4);
  ok("chaque dalle couvre ≥ 2 sommets par axe et la réunion couvre toute la grille",
     d.every((x) => x.w >= 2 && x.h >= 2) && Math.max(...d.map((x) => x.x0 + x.w)) === 9 && Math.max(...d.map((x) => x.y0 + x.h)) === 5, JSON.stringify(d));
  ok("une grille qui tient → une seule dalle", dalles(4, 4, 10).length === 1);
  const grid = [...Array(45).keys()];             // 9×5, valeur = index
  const sg = sous_grille(grid, 9, 5, d[1]);
  ok("sous-grille de la dalle 2 : w×h valeurs, première = index (x0 + y0·9)", sg.w === d[1].w && sg.h === d[1].h && sg.grid.length === sg.w * sg.h && sg.grid[0] === d[1].x0 + d[1].y0 * 9, JSON.stringify(sg).slice(0, 80));
}

if (echecs.length) {
  console.error("ECHECS relief :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA relief : PASS (17 controles)");
