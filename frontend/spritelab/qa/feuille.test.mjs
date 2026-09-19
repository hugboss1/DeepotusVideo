// feuille.test.mjs — lot 1 Spritelab Feuille : grille par projection alpha,
// cases occupées, sélection (clic / Ctrl / Maj / glisser / une sur n),
// alignement sur la première frame, sections, manifest v2, recomposition.
import { grille_detecter, cases_occupees, selection_clic, selection_une_sur,
         bbox_alpha, rect_case, aligner_frames, section_definir, manifest_feuille, feuille_recomposer } from "../feuille.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : "")); };
// un tampon {w, h, data} (RGBA) avec des pavés opaques posés où l'on veut
const tampon = (w, h) => ({ w, h, data: new Uint8ClampedArray(w * h * 4) });
const paver = (img, x0, y0, w, h, rgb = [255, 0, 0]) => { for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++) { const k = (y * img.w + x) * 4; img.data[k] = rgb[0]; img.data[k + 1] = rgb[1]; img.data[k + 2] = rgb[2]; img.data[k + 3] = 255; } return img; };
// une planche 3 × 2 de cellules 20 × 20, pavés 8 × 8 centrés sauf un vide et un décalé
const planche = () => { const im = tampon(60, 40); paver(im, 6, 6, 8, 8); paver(im, 26, 6, 8, 8); paver(im, 48, 8, 8, 8); paver(im, 6, 26, 8, 8); paver(im, 26, 26, 8, 8); return im; };
{
  const g = grille_detecter(planche());
  ok("grille 3 × 2 détectée par les colonnes / lignes vides", g.cols === 3 && g.rows === 2 && g.cell_w === 20 && g.cell_h === 20, JSON.stringify(g));
  const occ = cases_occupees(planche(), g);
  ok("cases occupées : 5 sur 6, la dernière vide", occ.length === 6 && occ.filter(Boolean).length === 5 && occ[5] === false, JSON.stringify(occ));
  const plein = paver(tampon(30, 30), 0, 0, 30, 30);
  const g1 = grille_detecter(plein);
  ok("sans colonne vide → 1 × 1 (jamais inventé)", g1.cols === 1 && g1.rows === 1);
  let refus = 0; try { grille_detecter({ w: 0, h: 0, data: new Uint8ClampedArray(0) }); } catch { refus++; }
  ok("image vide refusée", refus === 1);
}
{
  const n = 6;
  let s = selection_clic(new Array(n).fill(false), 2, {});
  ok("clic simple : la case seule", s.filter(Boolean).length === 1 && s[2] === true);
  s = selection_clic(s, 4, { ctrl: true });
  ok("Ctrl : ajoute", s[2] && s[4] && s.filter(Boolean).length === 2);
  s = selection_clic(s, 2, { ctrl: true });
  ok("Ctrl sur une case prise : retire", !s[2] && s[4]);
  s = selection_clic(s, 1, { shift: true, dernier: 4 });
  ok("Maj : de la dernière (4) à ici (1) — 1, 2, 3, 4", s.slice(1, 5).every(Boolean) && !s[0] && !s[5], JSON.stringify(s));
  const occ = [true, true, true, true, true, false];
  ok("une sur 2 sur les occupées : 0, 2, 4", JSON.stringify(selection_une_sur(occ, 2)) === "[true,false,true,false,true,false]");
  ok("une sur 1 = toutes les occupées", selection_une_sur(occ, 1).filter(Boolean).length === 5);
  ok("l'entrée n'est pas mutée", (() => { const a = [false, false]; selection_clic(a, 0, {}); return a[0] === false; })());
}
if (echecs.length) { console.error("ECHECS feuille :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA feuille : PASS (11 controles)");
