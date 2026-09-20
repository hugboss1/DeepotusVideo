// mod-carte.js — lot H côté UI : le panneau « Carte réelle » — importer un
// GPX (trace, points, emprise à l'échelle), poser le fond OpenStreetMap
// (attribution due, affichée et écrite au document), charger le relief
// Terrarium (grille de hauteurs dans doc.geo + image ombrée dans le
// magasin), vectoriser les courbes de niveau, découper en tuiles par palier
// et ouvrir l'impression 3D en mode relief. Logique PURE en tête (banc).
import { gpx_parser, cadrage, echelle_libelle, courbes_niveau, ombrage } from "./mod-geo.js";
import { op_geo_importer, op_geo_relief, op_geo_courbes, op_geo_tuiles, op_calque_ajouter,
         op_calque_reordonner, op_calque_opacite } from "./mod-doc.js";

/* ── pur ── */
export function libelle_carte(geo, unites) {
  if (!geo) return "Importer un fichier GPX : la trace se pose à l'échelle, l'emprise devient la page.";
  const dpi = (unites && unites.dpi) || 96;
  const km = (geo.emprise_px.w * geo.m_par_px / 1000).toFixed(1).replace(".", ",");
  const mm = Math.round(geo.emprise_px.w * 25.4 / dpi);
  return `${echelle_libelle(geo.m_par_px, dpi)} · ${km} km de large · ${mm} mm imprimés`;
}
export function grille_vers_px(i, j, relief, E) {
  return [Math.round((E.x + i / (relief.w - 1) * E.w) * 10) / 10,
          Math.round((E.y + j / (relief.h - 1) * E.h) * 10) / 10];
}
export function lignes_vers_px(lignes, relief, E) {
  return lignes.map((l) => l.map(([i, j]) => grille_vers_px(i, j, relief, E)));
}
export function niveaux(min, max, pas) {
  const out = [];
  if (!(pas > 0)) return out;
  for (let n = Math.ceil(min / pas) * pas; n < max && out.length < 400; n += pas) {
    if (n > min) out.push(Math.round(n * 1000) / 1000);
  }
  return out;
}
export function ombrage_rgba(gris, w, h) {
  const out = new Uint8ClampedArray(w * h * 4);
  for (let k = 0; k < w * h; k++) {
    out[k * 4] = gris[k]; out[k * 4 + 1] = gris[k]; out[k * 4 + 2] = gris[k]; out[k * 4 + 3] = 255;
  }
  return out;
}

/* ── DOM ── */
export function initCarte(VL) {
  const { $, etat } = VL;
  const hote = $("#panneauCarte");

  function rendre() {
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const g = etat.doc.geo;
    const R = g && g.relief;
    hote.innerHTML = `
      <p class="carte-libelle" id="carteLibelle">${libelle_carte(g, etat.doc.unites)}</p>
      <div class="ap-ligne"><button id="carteImporter" class="primaire" title="Un fichier .gpx : traces, points nommés, emprise — projetés en mètres et cadrés dans la page">⬆ Importer un GPX…</button>
        <input type="file" id="carteGpxInput" accept=".gpx,application/gpx+xml" hidden/></div>
      <div class="ap-ligne"><button id="carteFond" ${g ? "" : "disabled"} title="Fond OpenStreetMap assemblé par le backend (cache disque) et posé en calque « fond » — © OpenStreetMap contributors">🗺 Fond de carte OSM</button>
        <button id="carteRelief" ${g ? "" : "disabled"} title="Relief Terrarium (AWS Open Data, sans clé) : grille de hauteurs dans le document + image ombrée en calque « relief »">⛰ Relief</button></div>
      <div class="ap-ligne"><span>Courbes</span><input type="number" id="cartePas" value="50" min="1" step="1" title="Pas des courbes de niveau (m)"/>
        <button id="carteCourbes" ${R ? "" : "disabled"} title="Vectorise les courbes de niveau (marching squares) — de vrais chemins">≋ Courbes</button></div>
      <div class="ap-ligne"><span>Tuiles</span><input type="number" id="carteTuilePas" value="40" min="8" step="1" title="Rayon de l'hexagone (px)"/>
        <input type="number" id="carteReliefMm" value="10" min="1" step="0.5" title="Relief total du plateau (mm)"/>
        <button id="carteTuiles" ${R ? "" : "disabled"} title="Quadrillage hexagonal sur l'emprise : chaque tuile prend le terrain de son palier d'altitude et une hauteur en mm">⬡ Découper</button></div>
      <div class="ap-ligne"><button id="carteImprimer" ${R ? "" : "disabled"} title="Aperçu 3D de la plaque en relief (exagération, socle, gravure du tracé) puis STL / dalles">🖨 Aperçu 3D / Imprimer</button></div>
      ${g && g.attribution ? `<p class="carte-attribution">${g.attribution}</p>` : ""}
      ${R ? `<p class="carte-attribution">relief ${R.w} × ${R.h} · ${Math.round(R.min)} → ${Math.round(R.max)} m · ${R.pasM} m/cellule · zoom ${R.zoom ?? g.zoom}</p>` : ""}`;
    $("#carteImporter").addEventListener("click", () => $("#carteGpxInput").click());
    $("#carteGpxInput").addEventListener("change", () => {
      const f = $("#carteGpxInput").files && $("#carteGpxInput").files[0];
      $("#carteGpxInput").value = "";
      if (f) f.text().then(importer).catch((e) => VL.toast(e.message, true));
    });
    const garde = (fn) => () => Promise.resolve().then(fn).catch((e) => VL.toast(e.message, true));
    $("#carteFond").addEventListener("click", garde(fond));
    $("#carteRelief").addEventListener("click", garde(relief));
    $("#carteCourbes").addEventListener("click", garde(courbes));
    $("#carteTuiles").addEventListener("click", garde(tuiles));
    $("#carteImprimer").addEventListener("click", () => VL.impression("relief"));
  }

  function importer(texte) {
    const gpx = gpx_parser(texte);
    const cadre = cadrage(gpx.emprise, etat.doc.taille, 40);
    const r = VL.executer(op_geo_importer, gpx, cadre);
    if (r) { etat.calqueActif = r.calques.trace; VL.zoomAjuster(); VL.toast(`GPX importé : ${r.nPoints} point(s), ${echelle_libelle(cadre.m_par_px, (etat.doc.unites || {}).dpi || 96)}`); }
  }

  async function poserCalqueImage(nomCalque, blob, opacite) {
    // le calque hôte, créé EN BAS (fond) — puis l'image cadrée sur l'emprise
    const E = etat.doc.geo.emprise_px;
    const id = VL.executer((d) => {
      const cid = op_calque_ajouter(d, nomCalque);
      op_calque_reordonner(d, cid, 0);
      if (opacite !== undefined) op_calque_opacite(d, cid, opacite);
      return cid;
    });
    if (!id) return;
    etat.calqueActif = id;
    const oid = await VL.poserBlob(blob);
    if (!oid) return;
    VL.executer((d) => {
      for (const c of d.calques) { const o = c.objets.find((x) => x.id === oid); if (o) Object.assign(o, { x: E.x, y: E.y, w: E.w, h: E.h }); }
    });
  }
  async function fond() {
    const g = etat.doc.geo;
    const r = await fetch("/api/geo/fond", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ emprise: g.emprise, zoom: g.zoom }) });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `fond : ${r.status}`);
    const blob = await r.blob();
    const attr = (await (await fetch("/api/geo/attribution")).json()).osm;
    await poserCalqueImage("fond OpenStreetMap", blob);
    VL.executer((d) => { d.geo.attribution = attr; });
    VL.toast("fond de carte posé — " + attr);
  }
  async function relief() {
    const g = etat.doc.geo;
    const r = await fetch("/api/geo/relief", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ emprise: g.emprise, zoom: g.zoom }) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || `relief : ${r.status}`);
    VL.executer(op_geo_relief, d);
    // l'image ombrée : canvas → PNG → magasin du document (lot A)
    const gris = ombrage(d.hauteurs, d.w, d.h, d.pasM, 1);
    const cv = document.createElement("canvas");
    cv.width = d.w; cv.height = d.h;
    cv.getContext("2d").putImageData(new ImageData(ombrage_rgba(gris, d.w, d.h), d.w, d.h), 0, 0);
    const blob = await new Promise((res) => cv.toBlob(res, "image/png"));
    await poserCalqueImage("relief (ombrage)", blob, 0.7);
    VL.toast(`relief chargé : ${d.w} × ${d.h}, ${Math.round(d.min)} → ${Math.round(d.max)} m`);
  }
  function courbes() {
    const R = etat.doc.geo.relief, E = etat.doc.geo.emprise_px;
    const pas = Math.max(1, +$("#cartePas").value || 50);
    const lignes = [];
    for (const n of niveaux(R.min, R.max, pas)) lignes.push(...lignes_vers_px(courbes_niveau(R.hauteurs, R.w, R.h, n), R, E));
    const r = VL.executer(op_geo_courbes, lignes, pas);
    if (r) VL.toast(`${r.n} courbe(s) de niveau au pas de ${pas} m`);
  }
  function tuiles() {
    const r = VL.executer(op_geo_tuiles, { pas: +$("#carteTuilePas").value || 40, relief_mm: +$("#carteReliefMm").value || 10 });
    if (r) { etat.calqueActif = r.calqueId; VL.setOutil("tuiles"); VL.toast(`${r.tuiles.length} tuile(s) par palier — pinceau actif`); }
  }

  const suivant = VL.surRendu;
  VL.surRendu = () => { suivant(); rendre(); };
  VL.carteImporter = importer;          // la preuve importe un GPX sans boîte de fichier
  VL.carteFond = fond; VL.carteRelief = relief; VL.carteCourbes = courbes; VL.carteTuiles = tuiles;
}
