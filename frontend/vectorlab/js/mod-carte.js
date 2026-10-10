// mod-carte.js — lot H côté UI : le panneau « Carte réelle » — importer un
// GPX (trace, points, emprise à l'échelle), poser le fond OpenStreetMap
// (attribution due, affichée et écrite au document), charger le relief
// Terrarium (grille de hauteurs dans doc.geo + image ombrée dans le
// magasin), vectoriser les courbes de niveau, découper en tuiles par palier
// et ouvrir l'impression 3D en mode relief. Logique PURE en tête (banc).
import { T } from "./mod-i18n.js";
import { dzi } from "./mod-icones.js";
import { gpx_parser, cadrage, echelle_libelle, courbes_niveau, ombrage, profil_stats, profil_svg } from "./mod-geo.js";
import { op_geo_importer, op_geo_relief, op_geo_courbes, op_geo_tuiles, op_calque_ajouter,
         op_calque_reordonner, op_calque_opacite } from "./mod-doc.js";

/* ── pur ── */
export function libelle_carte(geo, unites) {
  if (!geo) return T("vectorlab.carte.libelle_vide");
  const dpi = (unites && unites.dpi) || 96;
  const km = (geo.emprise_px.w * geo.m_par_px / 1000).toFixed(1).replace(".", ",");
  const mm = Math.round(geo.emprise_px.w * 25.4 / dpi);
  return T("vectorlab.carte.libelle", { echelle: echelle_libelle(geo.m_par_px, dpi), km, mm });
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

// t124 : le profil altimétrique de chaque trace (doc.geo.parcours) — longueur, D+ / D−, bornes, graphe
export function profil_html(geo) {
  const P = (geo && geo.parcours) || [];
  return P.map((p, k) => {
    const st = profil_stats(p);
    const lg = st.longueur_m >= 1000 ? `${(st.longueur_m / 1000).toFixed(1).replace(".", ",")} km` : `${Math.round(st.longueur_m)} m`;
    const titre = P.length > 1 ? T("vectorlab.carte.trace_n", { n: k + 1 }) : "";
    return `<div class="carte-profil"><p class="carte-attribution">${titre}${lg} · D+ ${Math.round(st.dplus)} m · D− ${Math.round(st.dmoins)} m`
      + ` · ${Math.round(st.min)} → ${Math.round(st.max)} m ${T("vectorlab.carte.altitude_enreg")}</p>${profil_svg(p, 260, 90)}</div>`;
  }).join("");
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
      <div class="ap-ligne"><button id="carteImporter" class="primaire" title="${T("vectorlab.carte.importer_aide")}">${dzi("dz-action-importer", 16)}${T("vectorlab.carte.importer")}</button>
        <input type="file" id="carteGpxInput" accept=".gpx,application/gpx+xml" hidden/></div>
      <div class="ap-ligne"><button id="carteFond" ${g ? "" : "disabled"} title="${T("vectorlab.carte.fond_aide")}">${dzi("dz-media-fond-carte", 16)}${T("vectorlab.carte.fond")}</button>
        <button id="carteRelief" ${g ? "" : "disabled"} title="${T("vectorlab.carte.relief_aide")}">${dzi("dz-lab3d-relief", 16)}${T("vectorlab.carte.relief")}</button></div>
      <div class="ap-ligne"><span>${T("vectorlab.carte.courbes")}</span><input type="number" id="cartePas" value="50" min="1" step="1" title="${T("vectorlab.carte.pas_aide")}"/>
        <button id="carteCourbes" ${R ? "" : "disabled"} title="${T("vectorlab.carte.courbes_aide")}">${dzi("dz-edit-courbes-niveau", 16)}${T("vectorlab.carte.courbes")}</button></div>
      <div class="ap-ligne"><span>${T("vectorlab.carte.tuiles")}</span><input type="number" id="carteTuilePas" value="40" min="8" step="1" title="${T("vectorlab.carte.rayon_hex")}"/>
        <input type="number" id="carteReliefMm" value="10" min="1" step="0.5" title="${T("vectorlab.carte.relief_mm")}"/>
        <button id="carteTuiles" ${R ? "" : "disabled"} title="${T("vectorlab.carte.tuiles_aide")}">${dzi("dz-edit-grille-hex", 16)}${T("vectorlab.carte.decouper")}</button></div>
      <div class="ap-ligne"><button id="carteImprimer" ${R ? "" : "disabled"} title="${T("vectorlab.carte.imprimer_aide")}">${dzi("dz-lab3d-impression-3d", 16)}${T("vectorlab.carte.imprimer")}</button></div>
      ${profil_html(g)}
      ${g && g.attribution ? `<p class="carte-attribution">${g.attribution}</p>` : ""}
      ${R ? `<p class="carte-attribution">${T("vectorlab.carte.relief_info", { w: R.w, h: R.h, min: Math.round(R.min), max: Math.round(R.max), pas: R.pasM, zoom: R.zoom ?? g.zoom })}</p>` : ""}`;
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
    if (r) { etat.calqueActif = r.calques.trace; VL.zoomAjuster(); VL.toast(T("vectorlab.carte.gpx_importe", { n: r.nPoints, echelle: echelle_libelle(cadre.m_par_px, (etat.doc.unites || {}).dpi || 96) })); }
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
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || T("vectorlab.carte.err_fond", { s: r.status }));
    const blob = await r.blob();
    const attr = (await (await fetch("/api/geo/attribution")).json()).osm;
    await poserCalqueImage("fond OpenStreetMap", blob);
    VL.executer((d) => { d.geo.attribution = attr; });
    VL.toast(T("vectorlab.carte.fond_pose", { attr }));
  }
  async function relief() {
    const g = etat.doc.geo;
    const r = await fetch("/api/geo/relief", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ emprise: g.emprise, zoom: g.zoom }) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || T("vectorlab.carte.err_relief", { s: r.status }));
    VL.executer(op_geo_relief, d);
    // l'image ombrée : canvas → PNG → magasin du document (lot A)
    const gris = ombrage(d.hauteurs, d.w, d.h, d.pasM, 1);
    const cv = document.createElement("canvas");
    cv.width = d.w; cv.height = d.h;
    cv.getContext("2d").putImageData(new ImageData(ombrage_rgba(gris, d.w, d.h), d.w, d.h), 0, 0);
    const blob = await new Promise((res) => cv.toBlob(res, "image/png"));
    await poserCalqueImage("relief (ombrage)", blob, 0.7);
    VL.toast(T("vectorlab.carte.relief_charge", { w: d.w, h: d.h, min: Math.round(d.min), max: Math.round(d.max) }));
  }
  function courbes() {
    const R = etat.doc.geo.relief, E = etat.doc.geo.emprise_px;
    const pas = Math.max(1, +$("#cartePas").value || 50);
    const lignes = [];
    for (const n of niveaux(R.min, R.max, pas)) lignes.push(...lignes_vers_px(courbes_niveau(R.hauteurs, R.w, R.h, n), R, E));
    const r = VL.executer(op_geo_courbes, lignes, pas);
    if (r) VL.toast(T("vectorlab.carte.courbes_posees", { n: r.n, pas }));
  }
  function tuiles() {
    const r = VL.executer(op_geo_tuiles, { pas: +$("#carteTuilePas").value || 40, relief_mm: +$("#carteReliefMm").value || 10 });
    if (r) { etat.calqueActif = r.calqueId; VL.setOutil("tuiles"); VL.toast(T("vectorlab.carte.tuiles_palier", { n: r.tuiles.length })); }
  }

  const suivant = VL.surRendu;
  VL.surRendu = () => { suivant(); rendre(); };
  VL.carteImporter = importer;          // la preuve importe un GPX sans boîte de fichier
  VL.carteFond = fond; VL.carteRelief = relief; VL.carteCourbes = courbes; VL.carteTuiles = tuiles;
}
