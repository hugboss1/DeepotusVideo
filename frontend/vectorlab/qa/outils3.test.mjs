// outils3.test.mjs — mod-outils3 : les outils d'Affinity ajoutés au
// Vectorlab (R7) — loupe (cadrer / zoomer autour d'un point), dégradé au
// glisser, rognage d'image au glisser, cadre de texte au glisser, disque
// de masque des pinceaux de retouche. Feuille.
import { zoom_rect, zoom_point, degrade_de_glisser, rognage_de_rect, cadre_de_rect, rect_normalise, disque_masque } from "../js/mod-outils3.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 250) : "")); };
const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
{
  const r = rect_normalise([50, 80], [10, 20], 4);
  ok("rect_normalise : deux points dans n'importe quel ordre → {x,y,w,h} positif", r.x === 10 && r.y === 20 && r.w === 40 && r.h === 60);
  ok("rect_normalise : sous le minimum → null ; points absents → null", rect_normalise([0, 0], [2, 3], 4) === null && rect_normalise(null, [1, 1]) === null);
  const z = zoom_rect({ x: 100, y: 100, w: 200, h: 100 }, { w: 800, h: 600 }, 40);
  ok("zoom_rect : la scène cadre le rectangle avec la marge (zoom = min des deux axes), centré", pres(z.zoom, Math.min(720 / 200, 520 / 100)) && pres(z.tx + 200 * z.zoom, 800 / 2) && pres(z.ty + 150 * z.zoom, 300), JSON.stringify(z));
  ok("zoom_rect : borné 0,05..16 ; rect ou scène invalide → null", zoom_rect({ x: 0, y: 0, w: 1, h: 1 }, { w: 800, h: 600 }, 40).zoom === 16 && zoom_rect({ x: 0, y: 0, w: 1e6, h: 1e6 }, { w: 800, h: 600 }, 40).zoom === 0.05 && zoom_rect(null, { w: 800, h: 600 }) === null && zoom_rect({ x: 0, y: 0, w: 10, h: 10 }, { w: 0, h: 0 }) === null);
  const v = zoom_point({ zoom: 1, tx: 40, ty: 40 }, [240, 140], 1.25);
  ok("zoom_point : ×1,25, le point écran reste fixe ; borné 0,05..16", pres(v.zoom, 1.25) && pres(240 - (240 - 40) * 1.25, v.tx) && pres(140 - (140 - 40) * 1.25, v.ty) && zoom_point({ zoom: 15, tx: 0, ty: 0 }, [0, 0], 2).zoom === 16 && zoom_point({ zoom: 0.06, tx: 0, ty: 0 }, [0, 0], 0.5).zoom === 0.05, JSON.stringify(v));
  const g = degrade_de_glisser([10, 20], [110, 20], { fond: "#ff0000" });
  ok("degrade_de_glisser : linéaire de p1 à p2, stops fond → blanc ; fond absent ou none → noir", g.type === "lineaire" && g.x1 === 10 && g.x2 === 110 && g.stops[0].couleur === "#ff0000" && g.stops[1].couleur === "#FFFFFF" && degrade_de_glisser([0, 0], [1, 1], { fond: "none" }).stops[0].couleur === "#000000" && degrade_de_glisser([0, 0], [1, 1], null).stops[0].couleur === "#000000");
  ok("degrade_de_glisser : points confondus → null", degrade_de_glisser([5, 5], [5, 5], {}) === null);
  const img = { type: "image", x: 100, y: 100, w: 200, h: 100, nat: { w: 400, h: 200 } };
  const rg = rognage_de_rect(img, { x: 150, y: 125, w: 100, h: 50 });
  ok("rognage_de_rect : rect document → pixels natifs (échelle 2), entiers", rg.x === 100 && rg.y === 50 && rg.w === 200 && rg.h === 100, JSON.stringify(rg));
  ok("rognage_de_rect : borné à l'image (un rect qui déborde est coupé), vide → null, image sans nat → null", (() => { const b = rognage_de_rect(img, { x: 0, y: 0, w: 150, h: 500 }); return b.x === 0 && b.y === 0 && b.w === 100 && b.h === 200; })() && rognage_de_rect(img, { x: 500, y: 500, w: 10, h: 10 }) === null && rognage_de_rect({ type: "image", x: 0, y: 0, w: 1, h: 1 }, { x: 0, y: 0, w: 1, h: 1 }) === null);
  ok("rognage_de_rect : une image déjà rognée compose les deux rognages", (() => { const i2 = { ...img, rognage: { x: 100, y: 50, w: 200, h: 100 } }; const b = rognage_de_rect(i2, { x: 100, y: 100, w: 100, h: 50 }); return b.x === 100 && b.y === 50 && b.w === 100 && b.h === 50; })());
  const c = cadre_de_rect({ x: 10, y: 20, w: 200, h: 80 }, { police: "Anton", corps: 18, fond: "#123456" }, "Bonjour");
  ok("cadre_de_rect : objet cadre avec contenu, style police / corps / fond, sans id", c.type === "cadre" && c.x === 10 && c.w === 200 && c.h === 80 && c.contenu === "Bonjour" && c.style.police === "Anton" && c.style.corps === 18 && c.style.fond === "#123456" && c.id === undefined);
  ok("cadre_de_rect : contenu vide → « Texte », style absent → corps 16", cadre_de_rect({ x: 0, y: 0, w: 10, h: 10 }, null, "").contenu === "Texte" && cadre_de_rect({ x: 0, y: 0, w: 10, h: 10 }, null, "").style.corps === 16);
  const m = disque_masque(10, 10, 5, 5, 2);
  ok("disque_masque : 255 dans le disque (centre, rayon), 0 dehors, longueur w × h", m.length === 100 && m[5 * 10 + 5] === 255 && m[5 * 10 + 7] === 255 && m[5 * 10 + 8] === 0 && m[0] === 0);
  ok("disque_masque : centre hors du tampon → borné sans exception ; rayon 0 → le pixel seul", disque_masque(4, 4, 10, 10, 3).length === 16 && disque_masque(4, 4, 1, 1, 0)[5] === 255 && disque_masque(4, 4, 1, 1, 0).filter((v) => v).length === 1);
}
if (echecs.length) { console.error("ECHECS outils3 :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA outils3 : PASS (14 controles)");
