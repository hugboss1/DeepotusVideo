// navigateur.test.mjs — mod-navigateur : le panneau Navigateur d'Affinity
// — échelle de la vignette, cadre de la portion visible, curseur ↔ zoom
// (échelle logarithmique 5 % → 1600 %). Feuille.
import { echelle_vignette, cadre_vue, zoom_de_curseur, curseur_de_zoom, ZOOM_MIN, ZOOM_MAX } from "../js/mod-navigateur.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
{
  const e = echelle_vignette({ w: 640, h: 960 }, 240, 150);
  ok("échelle : la page tient dans 240 × 150 (portrait → k = 150/960), centrée", pres(e.k, 150 / 960, 1e-6) && pres(e.ox, (240 - 640 * 150 / 960) / 2) && e.oy === 0, JSON.stringify(e));
  const e2 = echelle_vignette({ w: 1000, h: 500 }, 240, 150);
  ok("échelle : paysage → k = 240/1000, centré verticalement", pres(e2.k, 0.24, 1e-6) && e2.ox === 0 && pres(e2.oy, (150 - 120) / 2));
  ok("état vide : taille absente ou nulle → k 0 sans exception", echelle_vignette(null, 240, 150).k === 0 && echelle_vignette({ w: 0, h: 0 }, 240, 150).k === 0);
  // scène 800 × 600, page 640 × 960 vue au zoom 1 avec tx 40, ty 40 : on voit la page de (−40,−40) à (760,560) → bornée à la page : 0..640 × 0..560
  const c = cadre_vue({ w: 640, h: 960 }, { zoom: 1, tx: 40, ty: 40 }, { w: 800, h: 600 }, e);
  ok("cadre : portion visible bornée à la page, en coordonnées vignette", pres(c.x, e.ox) && pres(c.y, 0) && pres(c.w, 640 * e.k) && pres(c.h, 560 * e.k), JSON.stringify(c));
  const c2 = cadre_vue({ w: 640, h: 960 }, { zoom: 2, tx: -200, ty: -300 }, { w: 800, h: 600 }, e);
  ok("cadre : zoom 2 décalé → fenêtre 400 × 300 doc à partir de (100,150)", pres(c2.x, e.ox + 100 * e.k) && pres(c2.y, 150 * e.k) && pres(c2.w, 400 * e.k) && pres(c2.h, 300 * e.k), JSON.stringify(c2));
  ok("cadre : sans document → null", cadre_vue(null, { zoom: 1, tx: 0, ty: 0 }, { w: 800, h: 600 }, e) === null);
  ok("curseur ↔ zoom : 0 → 5 %, 1000 → 1600 %, 100 % au milieu à 2 % près", pres(zoom_de_curseur(0), ZOOM_MIN, 1e-9) && pres(zoom_de_curseur(1000), ZOOM_MAX, 1e-9) && pres(zoom_de_curseur(500), 1, 0.35) && Math.abs(curseur_de_zoom(1) - 500) < 60);
  ok("aller-retour à 1 % près, bornes respectées", [0.05, 0.25, 1, 4, 16].every((z) => pres(zoom_de_curseur(curseur_de_zoom(z)), z, z * 0.01)) && curseur_de_zoom(0.001) === 0 && curseur_de_zoom(99) === 1000);
}
if (echecs.length) { console.error("ECHECS navigateur :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA navigateur : PASS (8 controles)");
