// geo.test.mjs — mod-geo (lot H) : GPX par expressions régulières,
// Mercator local en mètres, cadrage à la page et échelle, tuiles XYZ,
// marching squares, échantillonnage, paliers, ombrage. Module feuille.
import { R_TERRE, gpx_parser, mercator_m, cadrage, echelle_libelle, tuile_xyz,
         tuiles_couvrant, zoom_pour, latlon_de_tuile, courbes_niveau,
         echantillon_moyen, paliers_bornes, palier, ombrage } from "../js/mod-geo.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (a, b, tol) => Math.abs(a - b) <= tol;

/* ── GPX ── */
const GPX = `<?xml version="1.0"?><gpx version="1.1" creator="banc">
<wpt lat="45.01" lon="6.02"><name>Refuge &amp; col</name></wpt>
<trk><name>Boucle</name><trkseg>
<trkpt lat="45.000" lon="6.000"><ele>1500.5</ele><time>2026-09-17T10:00:00Z</time></trkpt>
<trkpt lat="45.010" lon="6.010"><ele>1620</ele></trkpt>
</trkseg></trk>
<rte><rtept lat="45.005" lon="6.005"></rtept></rte></gpx>`;
{
  const g = gpx_parser(GPX);
  ok("2 traces (trk + rte), 3 points de trace, 1 waypoint nommé (entité décodée)", g.traces.length === 2 && g.traces[0].length === 2
     && g.traces[1].length === 1 && g.points.length === 1 && g.points[0].nom === "Refuge & col", JSON.stringify(g).slice(0, 200));
  ok("ele lue, absente = null", g.traces[0][0].ele === 1500.5 && g.traces[1][0].ele === null);
  ok("emprise sur tous les points", g.emprise.minLat === 45 && g.emprise.maxLat === 45.01 && g.emprise.minLon === 6 && g.emprise.maxLon === 6.02 && g.n === 4, JSON.stringify(g.emprise));
  let refus = 0;
  for (const x of ["<gpx></gpx>", "pas du xml", "<gpx><trkpt lat=\"x\" lon=\"1\"/></gpx>"]) { try { gpx_parser(x); } catch { refus++; } }
  ok("GPX sans point / illisible / lat non numérique refusés", refus === 3, String(refus));
}
/* ── Mercator local ── */
{
  ok("R_TERRE WGS84", R_TERRE === 6378137);
  const c = mercator_m(45, 6, 45, 6);
  ok("le centre est à [0, 0]", c[0] === 0 && Math.abs(c[1]) < 1e-6);
  const e = mercator_m(45, 6.01, 45, 6);
  ok("+0,01° de longitude à 45° ≈ 786 m vers l'est", pres(e[0], 786, 2) && Math.abs(e[1]) < 1e-6, e.join(","));
  const n = mercator_m(45.01, 6, 45, 6);
  ok("+0,01° de latitude ≈ 1112 m vers le NORD (y positif)", pres(n[1], 1112, 3) && n[1] > 0, n.join(","));
}
/* ── cadrage ── */
{
  // emprise ≈ 2 km × 1 km autour de 45°/6°
  const dLon = 2000 / (R_TERRE * Math.cos(45 * Math.PI / 180)) * 180 / Math.PI;
  const dLat = 1000 / R_TERRE * 180 / Math.PI;
  const emprise = { minLat: 45 - dLat / 2, maxLat: 45 + dLat / 2, minLon: 6 - dLon / 2, maxLon: 6 + dLon / 2 };
  const k = cadrage(emprise, { w: 1000, h: 600 }, 50);
  ok("centre = milieu de l'emprise", pres(k.centre[0], 45, 1e-9) && pres(k.centre[1], 6, 1e-9));
  ok("largeur ≈ 2000 m, hauteur ≈ 1000 m", pres(k.largeur_m, 2000, 5) && pres(k.hauteur_m, 1000, 5), [k.largeur_m, k.hauteur_m].join(","));
  ok("m_par_px = max(2000/900, 1000/500) = 2,22", pres(k.m_par_px, 2000 / 900, 0.01), k.m_par_px);
  const c = k.vers_px(45, 6);
  ok("le centre tombe au centre de la page", pres(c[0], 500, 1e-6) && pres(c[1], 300, 1e-6), c.join(","));
  const no = k.vers_px(emprise.maxLat, emprise.minLon);
  ok("le coin nord-ouest tombe en haut à gauche (y petit)", no[0] < 500 && no[1] < 300 && pres(no[0], 50, 3), no.join(","));
  ok("échelle « 1 : 8 400 » à 96 dpi (arrondie à la centaine)", echelle_libelle(2000 / 900, 96) === "1 : 8 400", echelle_libelle(2000 / 900, 96));
  ok("échelle à 300 dpi : 1 : 26 200 (le px physique est plus petit)", echelle_libelle(2000 / 900, 300) === "1 : 26 200", echelle_libelle(2000 / 900, 300));
}
/* ── tuiles XYZ ── */
{
  ok("lat 0 lon 0 z 1 → (1, 1)", JSON.stringify(tuile_xyz(0, 0, 1)) === JSON.stringify({ x: 1, y: 1 }));
  const t = tuile_xyz(45, 6, 10);
  ok("45°/6° z10 → x 529, y 368", t.x === 529 && t.y === 368, JSON.stringify(t));
  const c = tuiles_couvrant({ minLat: 45, maxLat: 45.2, minLon: 6, maxLon: 6.3 }, 10);
  ok("couverture : n = (xmax−xmin+1)·(ymax−ymin+1)", c.n === (c.xmax - c.xmin + 1) * (c.ymax - c.ymin + 1) && c.n >= 2);
  const z = zoom_pour({ minLat: 45, maxLat: 45.02, minLon: 6, maxLon: 6.03 }, 16);
  ok("zoom_pour : le plus fin sous 16 tuiles, dans 1..15", z >= 1 && z <= 15 && tuiles_couvrant({ minLat: 45, maxLat: 45.02, minLon: 6, maxLon: 6.03 }, z).n <= 16
     && (z === 15 || tuiles_couvrant({ minLat: 45, maxLat: 45.02, minLon: 6, maxLon: 6.03 }, z + 1).n > 16), String(z));
  const p = latlon_de_tuile(1, 1, 1);
  ok("coin NO de la tuile (1,1) z1 = (0°, 0°)", pres(p.lat, 0, 1e-9) && pres(p.lon, 0, 1e-9), JSON.stringify(p));
}
/* ── marching squares ── */
{
  const grid = [0, 0, 0, 0, 10, 0, 0, 0, 0];
  const lignes = courbes_niveau(grid, 3, 3, 5);
  ok("un pic : une boucle fermée de 4 segments (5 sommets, premier = dernier)", lignes.length === 1 && lignes[0].length === 5
     && lignes[0][0][0] === lignes[0][4][0] && lignes[0][0][1] === lignes[0][4][1], JSON.stringify(lignes));
  ok("les sommets sont à mi-arête (x ou y = 0,5 / 1,5)", lignes[0].every(([x, y]) => [0.5, 1.5].includes(x) || [0.5, 1.5].includes(y)), JSON.stringify(lignes));
  ok("état vide : niveau hors bornes → []", courbes_niveau(grid, 3, 3, 20).length === 0 && courbes_niveau(grid, 3, 3, -1).length === 0);
  const pente = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3];        // 4 colonnes × 3 lignes, croît en x
  const l = courbes_niveau(pente, 4, 3, 1.5);
  ok("une pente : une ligne ouverte verticale à x = 1,5", l.length === 1 && l[0].every(([x]) => pres(x, 1.5, 1e-9)) && l[0].length === 3, JSON.stringify(l));
}
/* ── échantillon, paliers, ombrage ── */
{
  const grid = [1, 2, 3, 4, 5, 6, 7, 8, 9];
  ok("moyenne dans le rayon 1 autour du centre = 5", pres(echantillon_moyen(grid, 3, 3, 1, 1, 1), 5, 1e-9), echantillon_moyen(grid, 3, 3, 1, 1, 1));
  ok("hors grille → null", echantillon_moyen(grid, 3, 3, 10, 10, 0.5) === null);
  const b = paliers_bornes(0, 100, 4);
  ok("bornes égales : [25, 50, 75]", JSON.stringify(b) === "[25,50,75]");
  ok("palier : 10→0, 25→1, 99→3, 500→3", palier(10, b) === 0 && palier(25, b) === 1 && palier(99, b) === 3 && palier(500, b) === 3);
  const plat = ombrage(new Array(9).fill(100), 3, 3, 10);
  ok("plan : gris moyen partout", plat.length === 9 && plat.every((v) => v > 120 && v < 200), [...plat].join(","));
  // la lumière vient du nord-ouest (azimut 315°) : une pente HAUTE au
  // sud-est (bas-droite) regarde le nord-ouest → éclairée ; haute au
  // nord-ouest → elle regarde le sud-est, dans l'ombre
  const hautNordOuest = [30, 20, 10, 20, 10, 0, 10, 0, -10];
  const hautSudEst = hautNordOuest.slice().reverse();
  ok("la pente qui regarde le nord-ouest est plus claire qu'un plan, celle qui lui tourne le dos plus sombre",
     ombrage(hautSudEst, 3, 3, 10)[4] > plat[4] && ombrage(hautNordOuest, 3, 3, 10)[4] < plat[4],
     [ombrage(hautSudEst, 3, 3, 10)[4], ombrage(hautNordOuest, 3, 3, 10)[4]].join(","));
}

if (echecs.length) {
  console.error("ECHECS geo :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA geo : PASS (28 controles)");
