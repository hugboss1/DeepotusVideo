// pixel.test.mjs — mod-pixel (lot E) : outils raster purs sur un tampon
// {w, h, data} (le format d'ImageData, sans DOM) — pinceau, gomme, seau,
// sélections en masque (rect, lasso, baguette, couleur, croître, contracter,
// inverser), masque de calque, ajustements (niveaux, courbes, HSL, N&B,
// seuil), flou, clonage, extraction. États vides construits.
import { tampon, pinceau, gomme, seau, sel_rect, sel_lasso, sel_baguette, sel_couleur, sel_croitre,
         sel_contracter, sel_inverser, sel_bbox, masque_calque, niveaux, courbes, hsl, noir_blanc,
         seuil, flou, cloner, extraire } from "../js/mod-pixel.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const px = (img, x, y) => Array.from(img.data.slice((y * img.w + x) * 4, (y * img.w + x) * 4 + 4));
const compte = (m) => m.reduce((s, v) => s + (v ? 1 : 0), 0);

{
  const t = tampon(4, 3);
  ok("tampon : w, h, data = w·h·4 zéros", t.w === 4 && t.h === 3 && t.data.length === 48 && t.data.every((v) => v === 0));
  let refus = 0; try { tampon(0, 3); } catch { refus++; }
  ok("tampon vide refusé", refus === 1);
}
/* ── pinceau / gomme ── */
{
  const t = tampon(20, 20);
  pinceau(t, [[10, 10]], { rayon: 3, couleur: "#FF0000", durete: 1 });
  ok("pinceau : le centre est rouge opaque, un coin non", JSON.stringify(px(t, 10, 10)) === "[255,0,0,255]" && px(t, 0, 0)[3] === 0);
  ok("pinceau rond : (13,10) peint, (14,14) non", px(t, 13, 10)[3] === 255 && px(t, 14, 14)[3] === 0);
  pinceau(t, [[0, 0], [19, 19]], { rayon: 1, couleur: "#00FF00" });
  ok("un trait joint ses points : le milieu (10,10) est repeint vert", JSON.stringify(px(t, 10, 10)) === "[0,255,0,255]");
  const m = new Uint8Array(400); m[10 * 20 + 10] = 255;
  const u = tampon(20, 20);
  pinceau(u, [[10, 10]], { rayon: 3, couleur: "#0000FF", masque: m });
  ok("masque : seul le pixel autorisé est peint", px(u, 10, 10)[3] === 255 && px(u, 11, 10)[3] === 0);
  gomme(t, [[10, 10]], { rayon: 2 });
  ok("gomme : alpha à 0 au centre, le coin vert reste", px(t, 10, 10)[3] === 0 && px(t, 0, 0)[3] === 255);
  const d = tampon(20, 20);
  pinceau(d, [[10, 10]], { rayon: 5, couleur: "#000000", durete: 0 });
  ok("dureté 0 : le bord est plus transparent que le centre", px(d, 10, 10)[3] > px(d, 14, 10)[3] && px(d, 14, 10)[3] > 0, [px(d, 10, 10)[3], px(d, 14, 10)[3]].join(","));
}
/* ── seau ── */
{
  const t = tampon(6, 6);
  pinceau(t, [[0, 0], [5, 0]], { rayon: 0.5, couleur: "#000000" });   // un mur noir en haut
  pinceau(t, [[2, 1], [2, 5]], { rayon: 0.5, couleur: "#000000" });   // un mur vertical
  seau(t, 0, 3, "#FF0000", { tolerance: 0 });
  ok("seau contigu : la zone gauche est rouge, la droite non, le mur non", px(t, 0, 3)[0] === 255 && px(t, 4, 3)[3] === 0 && JSON.stringify(px(t, 2, 3)) === "[0,0,0,255]");
  seau(t, 5, 5, "#00FF00", { tolerance: 0, global: true });
  ok("seau global : tous les pixels transparents deviennent verts, y compris à gauche… non : la gauche est déjà rouge", px(t, 4, 3)[1] === 255 && px(t, 0, 3)[0] === 255);
  const u = tampon(3, 1); u.data.set([100, 100, 100, 255, 110, 110, 110, 255, 200, 200, 200, 255]);
  seau(u, 0, 0, "#FF0000", { tolerance: 20 });
  ok("tolérance 20 : le voisin à 10 près est repeint, celui à 100 non", px(u, 1, 0)[0] === 255 && px(u, 2, 0)[0] === 200);
  let refus = 0; try { seau(u, 9, 9, "#FFF", {}); } catch { refus++; }
  ok("seau hors tampon refusé", refus === 1);
}
/* ── sélections ── */
{
  const m = sel_rect(10, 10, { x: 2, y: 3, w: 4, h: 2 });
  ok("sel_rect : 8 pixels", compte(m) === 8 && m[3 * 10 + 2] === 255 && m[3 * 10 + 6] === 0);
  const l = sel_lasso(10, 10, [[0, 0], [10, 0], [0, 10]]);
  ok("sel_lasso triangle : ≈ la moitié (40..60)", compte(l) >= 40 && compte(l) <= 60, compte(l));
  ok("état vide : lasso < 3 points → masque vide", compte(sel_lasso(10, 10, [[0, 0], [1, 1]])) === 0);
  const t = tampon(6, 6);
  pinceau(t, [[0, 0], [5, 0]], { rayon: 0.5, couleur: "#000000" });
  const b = sel_baguette(t, 0, 3, 0);
  ok("baguette sur la zone vide sous le mur : 30 pixels (36 − 6)", compte(b) === 30, compte(b));
  const c = sel_couleur(t, "#000000", 0);
  ok("par couleur : les 6 pixels noirs", compte(c) === 6);
  const cr = sel_croitre(m, 10, 10, 1);
  ok("croître de 1 : 8 → 24 (4×2 devient 6×4)", compte(cr) === 24, compte(cr));
  const ct = sel_contracter(cr, 10, 10, 1);
  ok("contracter de 1 revient à 8", compte(ct) === 8);
  ok("inverser : 100 − 8", compte(sel_inverser(m)) === 92);
  ok("bbox de la sélection", JSON.stringify(sel_bbox(m, 10, 10)) === JSON.stringify({ x: 2, y: 3, w: 4, h: 2 }));
  ok("bbox d'un masque vide → null", sel_bbox(new Uint8Array(100), 10, 10) === null);
}
/* ── masque de calque, ajustements ── */
{
  const t = tampon(4, 1); t.data.set([255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255]);
  const m = new Uint8Array([255, 128, 0, 255]);
  masque_calque(t, m);
  ok("masque de calque : alpha ← masque", px(t, 0, 0)[3] === 255 && px(t, 1, 0)[3] === 128 && px(t, 2, 0)[3] === 0);
  const g = tampon(3, 1); g.data.set([0, 0, 0, 255, 128, 128, 128, 255, 255, 255, 255, 255]);
  niveaux(g, { noir: 64, blanc: 192, gamma: 1 });
  ok("niveaux 64..192 : 128 reste 128, 0 → 0, 255 → 255", px(g, 1, 0)[0] === 128 && px(g, 0, 0)[0] === 0 && px(g, 2, 0)[0] === 255, [px(g, 0, 0)[0], px(g, 1, 0)[0], px(g, 2, 0)[0]].join(","));
  const g2 = tampon(1, 1); g2.data.set([64, 64, 64, 255]);
  niveaux(g2, { noir: 0, blanc: 255, gamma: 2 });
  ok("gamma 2 éclaircit les tons moyens", px(g2, 0, 0)[0] > 64);
  const c = tampon(1, 1); c.data.set([128, 128, 128, 255]);
  courbes(c, [[0, 0], [128, 200], [255, 255]]);
  ok("courbes : le point de contrôle relève 128 à 200", px(c, 0, 0)[0] === 200, px(c, 0, 0)[0]);
  const h = tampon(1, 1); h.data.set([255, 0, 0, 255]);
  hsl(h, { h: 120, s: 0, l: 0 });
  ok("HSL : rouge tourné de 120° → vert", px(h, 0, 0)[1] === 255 && px(h, 0, 0)[0] < 5, px(h, 0, 0).join(","));
  const nb = tampon(1, 1); nb.data.set([255, 0, 0, 255]);
  noir_blanc(nb);
  ok("N&B : gris (luminance ≈ 54)", px(nb, 0, 0)[0] === px(nb, 0, 0)[1] && px(nb, 0, 0)[0] > 40 && px(nb, 0, 0)[0] < 90, px(nb, 0, 0).join(","));
  const s = tampon(2, 1); s.data.set([100, 100, 100, 255, 200, 200, 200, 255]);
  seuil(s, 128);
  ok("seuil 128 : noir puis blanc", px(s, 0, 0)[0] === 0 && px(s, 1, 0)[0] === 255);
  const sm = tampon(2, 1); sm.data.set([100, 100, 100, 255, 100, 100, 100, 255]);
  seuil(sm, 128, new Uint8Array([255, 0]));
  ok("un ajustement respecte le masque", px(sm, 0, 0)[0] === 0 && px(sm, 1, 0)[0] === 100);
}
/* ── flou, clonage, extraction ── */
{
  const t = tampon(5, 1); t.data.set([0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255, 255, 0, 0, 0, 255, 0, 0, 0, 255]);
  flou(t, 1);
  ok("flou rayon 1 : le pic s'étale sur ses voisins", px(t, 2, 0)[0] < 255 && px(t, 1, 0)[0] > 0 && px(t, 0, 0)[0] === 0, [px(t, 0, 0)[0], px(t, 1, 0)[0], px(t, 2, 0)[0]].join(","));
  const c = tampon(10, 10);
  pinceau(c, [[2, 2]], { rayon: 0.5, couleur: "#FF0000" });
  cloner(c, 2, 2, 7, 7, 1);
  ok("clonage : la source rouge est copiée au point cible", px(c, 7, 7)[0] === 255 && px(c, 2, 2)[0] === 255);
  const m = sel_rect(10, 10, { x: 6, y: 6, w: 3, h: 3 });
  const e = extraire(c, m);
  ok("extraire : sous-image de la bbox, 3×3, alpha masqué (pixel cloné présent)", e.w === 3 && e.h === 3 && e.x === 6 && px(e, 1, 1)[0] === 255);
  let refus = 0; try { extraire(c, new Uint8Array(100)); } catch { refus++; }
  ok("extraire sans sélection refusé", refus === 1);
}

/* ── lot 2 : le pinceau CARRÉ (Sprite Editor : ROUND / SQUARE) ── */
{
  const t = tampon(9, 9);
  pinceau(t, [[4, 4]], { rayon: 2, couleur: "#FF0000", durete: 1, forme: "carre" });
  const opaque = (x, y) => t.data[(y * 9 + x) * 4 + 3] === 255;
  ok("pinceau carré rayon 2 : le coin (2,2) est peint (Tchebychev), pas (1,4)", opaque(2, 2) && opaque(6, 6) && !opaque(1, 4) && !opaque(4, 1));
  const r = tampon(9, 9); pinceau(r, [[4, 4]], { rayon: 2, couleur: "#FF0000", durete: 1 });
  ok("pinceau rond rayon 2 : le coin (2,2) n'est PAS peint", r.data[(2 * 9 + 2) * 4 + 3] === 0 && r.data[(4 * 9 + 2) * 4 + 3] === 255);
  const g = tampon(5, 5); pinceau(g, [[2, 2]], { rayon: 2, couleur: "#00FF00", forme: "carre" }); gomme(g, [[2, 2]], { rayon: 1, forme: "carre" });
  ok("gomme carrée rayon 1 : le centre et (1,1) vidés, (0,0) reste", g.data[(2 * 5 + 2) * 4 + 3] === 0 && g.data[(1 * 5 + 1) * 4 + 3] === 0 && g.data[0 + 3] === 255);
}
if (echecs.length) {
  console.error("ECHECS pixel :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA pixel : PASS (37 controles)");
