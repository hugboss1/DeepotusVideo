// pixelart.test.mjs — mod-pixelart (lot E, complément Aseprite) : ligne et
// rectangle pixel-parfaits (Bresenham), symétrie, palette indexée (median
// cut), quantification, pixelisation au plus proche voisin, score de raccord
// 3×3, feuille de tuiles + index, bande, pelure d'oignon. Module feuille.
import { ligne_pixel, rect_pixel, symetrie, palette_extraire, quantifier, pixeliser, raccord_3x3,
         feuille_tuiles, bande, pelure } from "../js/mod-pixelart.js";
import { tampon, pinceau } from "../js/mod-pixel.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const px = (img, x, y) => Array.from(img.data.slice((y * img.w + x) * 4, (y * img.w + x) * 4 + 4));
const hex = (r, g, b) => "#" + [r, g, b].map((v) => v.toString(16).padStart(2, "0").toUpperCase()).join("");

{
  const l = ligne_pixel(0, 0, 4, 2);
  ok("Bresenham (0,0)→(4,2) : 5 pixels, extrémités exactes, sans trou", l.length === 5 && JSON.stringify(l[0]) === "[0,0]" && JSON.stringify(l[4]) === "[4,2]"
     && l.every((p, i) => i === 0 || (Math.abs(p[0] - l[i - 1][0]) <= 1 && Math.abs(p[1] - l[i - 1][1]) <= 1)), JSON.stringify(l));
  ok("ligne verticale : 4 pixels", ligne_pixel(1, 1, 1, 4).length === 4);
  const r = rect_pixel(2, 2, 5, 4);
  ok("rectangle 4×3 : le contour = 10 pixels, coins compris", r.length === 10 && r.some(([x, y]) => x === 2 && y === 2) && r.some(([x, y]) => x === 5 && y === 4) && !r.some(([x, y]) => x === 3 && y === 3), JSON.stringify(r));
  const s = symetrie([[1, 2]], 8, 8, { h: true, v: false });
  ok("symétrie horizontale sur 8 px : (1,2) et (6,2)", s.length === 2 && s.some(([x, y]) => x === 6 && y === 2));
  ok("symétrie h+v : 4 points", symetrie([[1, 2]], 8, 8, { h: true, v: true }).length === 4);
  ok("symétrie d'un point sur l'axe : dédoublonné", symetrie([[4, 4]], 8, 8, { h: true, v: true }).length === 2 || symetrie([[3, 3]], 7, 7, { h: true, v: true }).length === 1);
}
/* ── palette et quantification ── */
{
  const t = tampon(4, 1);
  t.data.set([255, 0, 0, 255, 250, 5, 5, 255, 0, 0, 255, 255, 0, 0, 250, 255]);
  const p = palette_extraire(t, 2);
  ok("palette 2 couleurs : un rouge et un bleu", p.length === 2 && p.some((c) => /^#F[0-9A-F]0[0-9A-F]0[0-9A-F]$/.test(c)) && p.some((c) => /^#0[0-9A-F]0[0-9A-F]F[0-9A-F]$/.test(c)), JSON.stringify(p));
  ok("palette : n borné 2..64, pixels transparents ignorés", palette_extraire(tampon(2, 2), 8).length === 0 && palette_extraire(t, 999).length <= 64);
  quantifier(t, ["#FF0000", "#0000FF"]);
  ok("quantifier : chaque pixel prend la couleur la plus proche", hex(...px(t, 1, 0).slice(0, 3)) === "#FF0000" && hex(...px(t, 3, 0).slice(0, 3)) === "#0000FF");
  let refus = 0; try { quantifier(t, []); } catch { refus++; }
  ok("palette vide refusée", refus === 1);
}
/* ── pixelisation ── */
{
  const t = tampon(8, 8);
  pinceau(t, [[0, 0], [7, 0]], { rayon: 0.5, couleur: "#000000" });     // rangée du haut noire
  const p = pixeliser(t, 4);
  ok("pixeliser 8 → 4 : 4×4, plus proche voisin (rangée du haut noire, le reste transparent)", p.w === 4 && p.h === 4 && px(p, 0, 0)[3] === 255 && px(p, 0, 1)[3] === 0);
  let refus = 0; try { pixeliser(t, 0); } catch { refus++; }
  ok("largeur cible nulle refusée", refus === 1);
}
/* ── raccord 3×3 ── */
{
  const uni = tampon(8, 8); pinceau(uni, [[0, 0], [7, 7]], { rayon: 20, couleur: "#808080" });
  const r = raccord_3x3(uni);
  ok("un aplat uniforme raccorde parfaitement : score 1", r.score === 1 && r.img.w === 24 && r.img.h === 24, JSON.stringify([r.score, r.img.w]));
  const bord = tampon(8, 8); pinceau(bord, [[0, 0], [7, 7]], { rayon: 20, couleur: "#808080" }); pinceau(bord, [[0, 0], [0, 7]], { rayon: 0.5, couleur: "#FFFFFF" });
  const r2 = raccord_3x3(bord);
  ok("une colonne claire au bord gauche : score < 1, la mosaïque montre la couture", r2.score < 1 && r2.score > 0, r2.score);
}
/* ── feuille, bande, pelure ── */
{
  const a = tampon(4, 4), b = tampon(4, 4), c = tampon(4, 4);
  pinceau(a, [[0, 0]], { rayon: 0.5, couleur: "#FF0000" }); pinceau(b, [[0, 0]], { rayon: 0.5, couleur: "#00FF00" }); pinceau(c, [[0, 0]], { rayon: 0.5, couleur: "#0000FF" });
  const f = feuille_tuiles([{ nom: "a", img: a }, { nom: "b", img: b }, { nom: "c", img: c }], 2);
  ok("feuille 2 colonnes : 8×8, 3 entrées d'index à leur place", f.img.w === 8 && f.img.h === 8 && f.index.length === 3 && JSON.stringify(f.index[2]) === JSON.stringify({ nom: "c", x: 0, y: 4, w: 4, h: 4 }), JSON.stringify(f.index));
  ok("les pixels sont copiés à leur place", px(f.img, 4, 0)[1] === 255 && px(f.img, 0, 4)[2] === 255);
  const s = bande([a, b, c]);
  ok("bande : 12×4, cadres côte à côte", s.w === 12 && s.h === 4 && px(s, 8, 0)[2] === 255);
  const p = pelure(b, a, 0.5);
  ok("pelure d'oignon : le cadre précédent apparaît à demi-alpha là où le courant est vide, le courant reste intact", px(p, 0, 0)[1] === 255 && px(p, 0, 0)[3] === 255 && (() => { const q = tampon(2, 1); pinceau(q, [[1, 0]], { rayon: 0.5, couleur: "#FF0000" }); const w = tampon(2, 1); const r = pelure(w, q, 0.5); return r.data[7] === 128 && r.data[4] === 255; })());
  let refus = 0; try { feuille_tuiles([], 2); } catch { refus++; }
  try { feuille_tuiles([{ nom: "a", img: a }, { nom: "b", img: tampon(5, 5) }], 2); } catch { refus++; }
  ok("feuille vide ou tailles différentes refusées", refus === 2);
}

if (echecs.length) {
  console.error("ECHECS pixelart :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA pixelart : PASS (19 controles)");
