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
{
  const im = planche(), g = grille_detecter(im);
  const sel = [true, true, true, false, false, false];        // la case 2 est décalée de +2 en x et +2 en y
  const off = aligner_frames(im, g, sel, "deux");
  ok("deux axes : la case 2 revient sur la première (dx −2, dy −2), les autres 0", off.length === 6 && off[0].dx === 0 && off[0].dy === 0 && off[2].dx === -2 && off[2].dy === -2 && off[3].dx === 0, JSON.stringify(off));
  ok("x seulement : dy reste 0", aligner_frames(im, g, sel, "x")[2].dy === 0 && aligner_frames(im, g, sel, "x")[2].dx === -2);
  ok("pieds : dx reste 0, le bas s'aligne", aligner_frames(im, g, sel, "pieds")[2].dx === 0 && aligner_frames(im, g, sel, "pieds")[2].dy === -2);
  ok("une case non sélectionnée ou vide → 0, 0", aligner_frames(im, g, sel, "deux")[5].dx === 0);
  let refus = 0; try { aligner_frames(im, g, sel, "diagonale"); } catch { refus++; }
  ok("mode inconnu refusé", refus === 1);
  const b = bbox_alpha(im, rect_case(g, 2));
  ok("bbox alpha de la case 2 : 8 × 8 en (48, 8)", b.x === 48 && b.y === 8 && b.w === 8 && b.h === 8, JSON.stringify(b));
  const im2 = paver(paver(tampon(40, 20), 6, 6, 8, 8), 20, 0, 8, 8);
  const g2 = grille_detecter(im2), o2 = aligner_frames(im2, g2, [true, true], "deux");
  ok("la case 1 (pavé en 20,0) remonte de 6 et se recentre de 6 sur la case 0", o2[1].dy === 6 && o2[1].dx === 6, JSON.stringify(o2));
  // le décalage est BORNÉ à la cellule : un pavé large voudrait +10 mais ne peut bouger que de 4
  const im3 = paver(paver(tampon(40, 20), 16, 0, 4, 8), 20, 0, 16, 8);
  const o3 = aligner_frames(im3, { cols: 2, rows: 1, cell_w: 20, cell_h: 20 }, [true, true], "x");
  ok("borné : dx = 4 (le bord de la cellule), pas 10", o3[1].dx === 4 && o3[1].dy === 0, JSON.stringify(o3));
}
{
  let S = section_definir([], { nom: "marche", debut: 0, fin: 3, mode: "boucle" }, 5);
  ok("section posée", S.length === 1 && S[0].nom === "marche" && S[0].fin === 3);
  S = section_definir(S, { nom: "saut", debut: 2, fin: 4, mode: "pingpong" }, 5);
  ok("deux sections peuvent se chevaucher", S.length === 2);
  S = section_definir(S, { nom: "marche", debut: 1, fin: 3, mode: "inverse" }, 5);
  ok("même nom = remplace", S.length === 2 && S.find((s) => s.nom === "marche").debut === 1);
  let refus = 0;
  for (const mauvaise of [{ nom: "", debut: 0, fin: 1, mode: "boucle" }, { nom: "x", debut: 3, fin: 1, mode: "boucle" }, { nom: "x", debut: 0, fin: 9, mode: "boucle" }, { nom: "x", debut: 0, fin: 1, mode: "yoyo" }]) { try { section_definir(S, mauvaise, 5); } catch { refus++; } }
  ok("nom vide, fin < début, hors bornes, mode inconnu → refusés", refus === 4);
  const im = planche(), g = grille_detecter(im), sel = [true, true, true, false, true, false];
  const off = aligner_frames(im, g, sel, "deux");
  const m = manifest_feuille({ img: im, g, sel, offsets: off, fps: 12, sections: S, filename: "wizard.png" });
  ok("manifest v2 : 4 frames dans l'ordre des cases, rect + offset, fps, sections, source feuille", m.version === 2 && m.frames.length === 4 && m.frames[3].index === 3 && m.frames[3].rect.x === 20 && m.frames[3].rect.y === 20 && m.frames[2].offset.dx === -2 && m.fps === 12 && m.sections.length === 2 && m.source.kind === "feuille" && m.source.filename === "wizard.png" && m.grid.cols === 3, JSON.stringify(m).slice(0, 200));
  ok("frames[i].case = l'index de la case d'origine", m.frames[3].case === 4);
  const out = feuille_recomposer(im, g, off);
  ok("recomposée : même taille, la case 2 ramenée à (46, 6)", out.w === 60 && out.h === 40 && out.data[((6 * 60) + 46) * 4 + 3] === 255 && out.data[((13 * 60) + 53) * 4 + 3] === 255 && out.data[((15 * 60) + 55) * 4 + 3] === 0 && out.data[((8 * 60) + 48) * 4 + 3] === 255, "");
  ok("recomposée sans décalage = identique", (() => { const z = feuille_recomposer(im, g, off.map(() => ({ dx: 0, dy: 0 }))); for (let k = 0; k < z.data.length; k++) if (z.data[k] !== im.data[k]) return false; return true; })());
}
if (echecs.length) { console.error("ECHECS feuille :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA feuille : PASS (28 controles)");
