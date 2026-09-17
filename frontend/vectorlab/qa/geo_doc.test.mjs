// geo_doc.test.mjs — lot H côté modèle : doc.geo (validation), l'import
// GPX en trois calques, le relief posé, les courbes de niveau en chemins,
// la découpe en tuiles par palier de relief. États vides construits.
import { parserDoc, compilerSVG, op_geo_importer, op_geo_relief, op_geo_courbes,
         op_geo_tuiles, TERRAINS_DEFAUT } from "../js/mod-doc.js";
import { gpx_parser, cadrage } from "../js/mod-geo.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const base = () => ({ v: 1, nom: "Carte", taille: { w: 1000, h: 600 }, unites: { affichage: "mm", dpi: 96 },
  calques: [{ id: "c1", nom: "calque 1", visible: true, verrou: false, objets: [] }] });
const GPX = `<gpx><wpt lat="45.01" lon="6.02"><name>Refuge</name></wpt><trk><trkseg>
<trkpt lat="45.000" lon="6.000"><ele>1500</ele></trkpt><trkpt lat="45.010" lon="6.010"><ele>1620</ele></trkpt>
<trkpt lat="45.005" lon="6.020"><ele>1580</ele></trkpt></trkseg></trk></gpx>`;

/* ── import ── */
let docImporte;
{
  const d = base();
  const g = gpx_parser(GPX);
  const k = cadrage(g.emprise, d.taille, 40);
  const r = op_geo_importer(d, g, k);
  ok("trois calques nés : trace, points, emprise (verrouillé)", r.calques.trace && r.calques.points && r.calques.emprise
     && d.calques.find((c) => c.id === r.calques.emprise).verrou === true && d.calques.length === 4, JSON.stringify(r));
  const trace = d.calques.find((c) => c.id === r.calques.trace);
  ok("la trace : un path par segment, contour seul, 3 ancres", trace.objets.length === 1 && trace.objets[0].type === "path"
     && trace.objets[0].style.fond === "none" && (trace.objets[0].d.match(/L /g) || []).length === 2, JSON.stringify(trace.objets[0]).slice(0, 160));
  const pts = d.calques.find((c) => c.id === r.calques.points);
  ok("les points : une pastille + un texte nommé", pts.objets.some((o) => o.type === "ellipse") && pts.objets.some((o) => o.type === "texte" && o.contenu === "Refuge"));
  const emp = d.calques.find((c) => c.id === r.calques.emprise).objets[0];
  ok("l'emprise : un rect pointillé dans les marges (x ≈ 40 ou y ≈ 40)", emp.type === "rect" && emp.style.pointilles && (Math.abs(emp.x - 40) < 1 || Math.abs(emp.y - 40) < 1), JSON.stringify(emp));
  ok("doc.geo posé : centre, m_par_px, zoom, emprise, emprise_px", d.geo && d.geo.centre.length === 2 && d.geo.m_par_px > 0
     && Number.isInteger(d.geo.zoom) && d.geo.emprise.minLat === 45 && d.geo.emprise_px.w > 0, JSON.stringify(d.geo));
  ok("le document passe parserDoc et se compile", (() => { try { return compilerSVG(parserDoc(d)).includes("data-objet"); } catch (e) { return e.message; } })() === true);
  docImporte = d;
  let refus = 0;
  try { op_geo_importer(base(), { traces: [], points: [], n: 0, emprise: g.emprise }, k); } catch { refus++; }
  ok("import sans point refusé", refus === 1);
}
/* ── validation de geo ── */
{
  let refus = 0;
  for (const geo of [{ centre: [1] }, { centre: [45, 6], m_par_px: 0 }, { centre: [45, 6], m_par_px: 1, emprise: { minLat: 2, maxLat: 1, minLon: 0, maxLon: 1 } },
                     { centre: [45, 6], m_par_px: 1, relief: { w: 2, h: 2, min: 0, max: 1, pasM: 1, hauteurs: [1, 2, 3] } }]) {
    const d = base(); d.geo = geo; try { parserDoc(d); } catch { refus++; }
  }
  ok("parserDoc refuse 4 geo malformés (centre, m_par_px, emprise inversée, relief incohérent)", refus === 4, String(refus));
}
/* ── relief ── */
{
  const d = JSON.parse(JSON.stringify(docImporte));
  // 4 × 3, pente de 1000 à 1200 m d'ouest en est
  const relief = { w: 4, h: 3, min: 1000, max: 1200, pasM: 50, hauteurs: [1000, 1067, 1133, 1200, 1000, 1067, 1133, 1200, 1000, 1067, 1133, 1200] };
  op_geo_relief(d, relief);
  ok("le relief est posé dans doc.geo", d.geo.relief.w === 4 && d.geo.relief.hauteurs.length === 12);
  ok("parserDoc accepte", (() => { try { parserDoc(d); return true; } catch { return false; } })());
  let refus = 0;
  try { op_geo_relief(base(), relief); } catch { refus++; }                          // pas de geo
  try { op_geo_relief(JSON.parse(JSON.stringify(docImporte)), { w: 4, h: 3, hauteurs: [1] }); } catch { refus++; }
  ok("relief refusé sans geo ou incohérent", refus === 2, String(refus));
  /* courbes */
  const r = op_geo_courbes(d, [[[100, 100], [200, 150], [300, 100]], [[400, 400], [500, 400]]], 50);
  const c = d.calques.find((x) => x.id === r.calqueId);
  ok("courbes : un calque nommé par le pas, 2 chemins ouverts, contour fin", c.nom === "courbes 50 m" && r.n === 2 && c.objets.every((o) => o.type === "path" && o.style.fond === "none" && !o.d.endsWith("Z")), JSON.stringify(c.objets[0]));
  let refusC = 0; try { op_geo_courbes(d, [], 50); } catch { refusC++; }
  ok("courbes : aucune ligne → refus", refusC === 1);
  /* tuiles par palier */
  const t = op_geo_tuiles(d, { pas: 40, relief_mm: 10 });
  const cal = d.calques.find((x) => x.id === t.calqueId);
  ok("tuiles : une grille hex et un calque de tuiles couvrant l'emprise", d.grille && d.grille.type === "hex" && d.grille.pas === 40 && cal.objets.length === t.tuiles.length && t.tuiles.length >= 20, `${t.tuiles.length}`);
  const terrains = new Set(cal.objets.map((o) => o.terrain));
  ok("les terrains suivent la pente : au moins 3 paliers différents, tous connus", terrains.size >= 3 && [...terrains].every((k) => TERRAINS_DEFAUT[k]), [...terrains].join(","));
  ok("hauteur_mm de chaque tuile dans [0, relief_mm], l'est plus haut que l'ouest",
     cal.objets.every((o) => o.hauteur_mm >= 0 && o.hauteur_mm <= 10.0001)
     && (() => { const ouest = cal.objets.filter((o) => o.q < 0).map((o) => o.hauteur_mm); const est = cal.objets.filter((o) => o.q > 3).map((o) => o.hauteur_mm);
                 const m = (a) => a.reduce((s, v) => s + v, 0) / Math.max(1, a.length); return est.length && ouest.length && m(est) > m(ouest); })(), JSON.stringify(cal.objets.slice(0, 3)));
  ok("le résultat porte les paliers et compile", Array.isArray(t.paliers) && t.paliers.length === 4 && compilerSVG(parserDoc(d)).includes("data-terrain"));
  let refusT = 0; try { op_geo_tuiles(JSON.parse(JSON.stringify(docImporte)), { pas: 40 }); } catch { refusT++; }
  ok("tuiles sans relief → refus", refusT === 1);
}

if (echecs.length) {
  console.error("ECHECS geo_doc :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA geo_doc : PASS (16 controles)");
