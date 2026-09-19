// feuille_tuiles.test.mjs — lot 4 Tilelab 2 : détection des tuiles par les
// composantes connexes de l'alpha, taille commune, feuille alignée,
// placement carré / iso, index des placements. Module feuille pur.
import { tuiles_detecter, taille_commune, feuille_alignee, placement_rendre, placement_index } from "../feuille_tuiles.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
const tampon = (w, h) => ({ w, h, data: new Uint8ClampedArray(w * h * 4) });
const paver = (im, x0, y0, w, h, rgb = [255, 0, 0]) => { for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++) { const k = (y * im.w + x) * 4; im.data[k] = rgb[0]; im.data[k + 1] = rgb[1]; im.data[k + 2] = rgb[2]; im.data[k + 3] = 255; } return im; };
// une planche 40 × 20 : trois tuiles 8 × 8 (à (2,2), (14,2), (26,4)), un pixel isolé, deux morceaux verts séparés d'une colonne
const pl = paver(paver(paver(tampon(40, 20), 2, 2, 8, 8), 14, 2, 8, 8), 26, 4, 8, 8); paver(pl, 37, 1, 1, 1); paver(pl, 2, 13, 4, 6, [0, 255, 0]); paver(pl, 7, 13, 3, 6, [0, 255, 0]);
{
  const T = tuiles_detecter(pl, { min: 2 });
  ok("cinq tuiles (le pixel isolé filtré), triées par y puis x", T.length === 5 && T[0].x === 2 && T[0].y === 2 && T[1].x === 14 && T[2].x === 26 && T[3].y === 13 && T[3].x === 2 && T[4].x === 7, JSON.stringify(T));
  ok("bboxes disjointes = deux tuiles (les morceaux verts restent séparés)", T[3].w === 4 && T[4].w === 3);
  ok("taille commune = médiane 8 × 8", JSON.stringify(taille_commune(T.slice(0, 3))) === JSON.stringify({ w: 8, h: 8 }));
  ok("min 10 → aucune", tuiles_detecter(pl, { min: 10 }).length === 0);
  ok("image vide refusée", (() => { try { tuiles_detecter({ w: 0, h: 0, data: new Uint8ClampedArray(0) }); return false; } catch { return true; } })());
  // deux composantes dont les bbox se CHEVAUCHENT fusionnent (un sprite en deux morceaux diagonaux)
  // un L (6 × 6) et un pavé 2 × 2 dans son creux, sans contact : bboxes qui se chevauchent → une tuile
  const d = paver(paver(paver(tampon(8, 8), 0, 0, 6, 1), 0, 1, 1, 5), 2, 2, 2, 2);
  ok("chevauchement de bbox → une tuile 6 × 6", tuiles_detecter(d).length === 1 && tuiles_detecter(d)[0].w === 6 && tuiles_detecter(d)[0].h === 6, JSON.stringify(tuiles_detecter(d)));
}
{
  const T = tuiles_detecter(pl, { min: 2 }).slice(0, 3);
  const F = feuille_alignee(pl, T, { cell_w: 10, cell_h: 10, cols: 2, pad: 0 });
  ok("feuille alignée : 2 colonnes → 20 × 20, trois entrées, la 3e en (0,10)", F.img.w === 20 && F.img.h === 20 && F.index.length === 3 && F.index[2].x === 0 && F.index[2].y === 10, JSON.stringify(F.index));
  ok("chaque tuile centrée dans sa cellule : le pixel (1,1) de la cellule 0 est rouge, (0,0) transparent", F.img.data[((1 * 20) + 1) * 4 + 3] === 255 && F.img.data[3] === 0);
  ok("index : source conservée", F.index[0].source.x === 2 && F.index[0].source.w === 8);
  const g = { type: "carree", cols: 3, rows: 2, cell_w: 8, cell_h: 8 };
  const R = placement_rendre(pl, T, [{ c: 0, r: 0, tuile: 0 }, { c: 2, r: 1, tuile: 1 }], g);
  ok("placement carré : 24 × 16, tuile 0 en (0,0), tuile 1 en (16,8)", R.w === 24 && R.h === 16 && R.data[3] === 255 && R.data[((8 * 24) + 16) * 4 + 3] === 255 && R.data[((8 * 24) + 0) * 4 + 3] === 0);
  const gi = { type: "iso", cols: 2, rows: 2, cell_w: 8, cell_h: 4 };
  const Ri = placement_rendre(pl, T, [{ c: 0, r: 0, tuile: 0 }, { c: 1, r: 0, tuile: 1 }], gi);
  ok("placement iso 2 × 2 de 8 × 4 avec des tuiles 8 × 8 : 16 × (8 + 4)", Ri.w === 16 && Ri.h === 12, `${Ri.w}×${Ri.h}`);
  ok("placement_index : liste {c, r, tuile, x, y}", JSON.stringify(placement_index([{ c: 2, r: 1, tuile: 1 }], g)) === JSON.stringify([{ c: 2, r: 1, tuile: 1, x: 16, y: 8 }]));
  ok("placement_index iso : (1,0) → x = 8, y = 2", JSON.stringify(placement_index([{ c: 1, r: 0, tuile: 1 }], gi)[0]) === JSON.stringify({ c: 1, r: 0, tuile: 1, x: 8, y: 2 }));
}
if (echecs.length) { console.error("ECHECS feuille_tuiles :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA feuille_tuiles : PASS (13 controles)");
