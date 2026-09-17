// mod-impression.js — lot D : le dialogue « Impression 3D » du Vectorlab.
// Trois modes : CALQUES (l'extrusion par calque du plan slicer, hauteurs
// mm, surcharge « nom=mm »), TUILES (une pièce par tuile : socle + relief
// du terrain ; lot = un STL par tuile + plateau.3mf + nomenclature),
// LOGO (la sélection unie, biseau en marches, évidement à mur minimal).
// Aperçu 3D AVANT tir : GLB minimal écrit ici, montré dans <model-viewer>
// du bundle. Et le texte → chemins (opentype.js, polices du dist) depuis
// le panneau Apparence. Logique PURE en tête (banc node). Les textes non
// vectorisés sont ignorés et DITS, jamais bloquants.
import { aplatir_objet, contour_en_multi, versMulti } from "./mod-bool.js";
import { extruder, stl_binaire, volume_de } from "./mod-extrude.js";
import { MUR_MIN_MM, extruder_biseau, extruder_evide, plateau_pieces, glb_de_triangles,
         nomenclature_csv } from "./mod-solide.js";
import { terrains_de, op_texte_vectoriser } from "./mod-doc.js";
import { hex_centre, hex_sommets } from "./mod-grille.js";
import { POLICES, texte_vers_d } from "./mod-texte3d.js";

/* ── pur ── */
const num = (v, def) => {
  const n = parseFloat(String(v).replace(",", "."));
  return Number.isFinite(n) ? n : def;
};
export function reglages_lire(f) {
  const mode = ["calques", "tuiles", "logo"].includes(f.mode) ? f.mode : "calques";
  const h0 = num(f.hauteur, 3);
  const hauteur = Math.max(0.2, h0 > 0 ? h0 : 3);
  const socle = Math.max(0, num(f.socle, 0));
  const biseau = Math.min(Math.max(0, num(f.biseau, 0)), Math.max(0, hauteur - 0.2));
  const mur = Math.max(MUR_MIN_MM, num(f.mur, 1.2));
  const plancher = Math.min(Math.max(0, num(f.plancher, 1)), Math.max(0, hauteur - 0.2));
  return { mode, hauteur, socle, biseau, evide: !!f.evide, mur, plancher, pas: 0.2 };
}
export function hauteurs_par_calque(texte, calques) {
  let globale = null;
  const parCalque = {};
  for (const part of String(texte || "").split(",")) {
    const t = part.trim();
    if (!t) continue;
    const m = /^(.+?)\s*=\s*([0-9.,]+)$/.exec(t);   // « Verres = 2 » aussi
    if (m) parCalque[m[1].trim().toLowerCase()] = num(m[2], 0);
    else if (globale === null && num(t, 0) > 0) globale = num(t, 0);
  }
  if (!(globale > 0)) throw new Error("hauteur en mm invalide (ex. « 3, contours=5 »)");
  const out = {};
  for (const c of calques) {
    const k = (c.nom || "").toLowerCase();
    if (parCalque[k] !== undefined) out[k] = parCalque[k];
  }
  return { globale, parCalque: out };
}
export function resume_impression({ triangles, bbox_mm, pieces, ignores }) {
  const dim = bbox_mm.map(([a, b]) => Math.round(b - a)).join(" × ") + " mm";
  let s = `${dim} · ${pieces} pièce(s) · ${triangles} triangles`;
  if (ignores) s += ` · ${ignores} texte(s) ignoré(s) (vectoriser d'abord)`;
  return s;
}
function bboxDe(tris) {
  const b = [[Infinity, -Infinity], [Infinity, -Infinity], [Infinity, -Infinity]];
  for (const t of tris) for (const p of t) for (let i = 0; i < 3; i++) {
    b[i][0] = Math.min(b[i][0], p[i]); b[i][1] = Math.max(b[i][1], p[i]);
  }
  return b;
}

/* ── DOM ── */
export function initImpression(VL) {
  const { $, etat } = VL;
  const dlg = $("#impDlg");
  let courant = null;            // { pieces:[{nom, tris, …}], ignores, tous, bbox, glbUrl }

  const mz = () => {
    if (!window.martinez) throw new Error("martinez indisponible (vendor non chargé)");
    return window.martinez;
  };
  const sMm = () => 25.4 / ((etat.doc.unites && etat.doc.unites.dpi) || 96);
  const enMm = (mp) => mp.map((poly) => poly.map((ring) => ring.map(([x, y]) => [x * sMm(), -y * sMm()])));
  const grilleHex = () => {
    const g = VL.grilleDoc();
    return g && g.type === "hex" ? g : { pas: 32, orientation: "pointe", origine: [0, 0], echelle: [1, 1] };
  };

  function multiDe(objets, compte) {
    let mp = null;
    for (const o of objets) {
      if (o.type === "texte") { compte.ignores++; continue; }
      let m = null;
      if (o.type === "tuile") {
        const g = grilleHex();
        const [cx, cy] = hex_centre(o.q, o.r, g);
        const ring = hex_sommets(cx, cy, g.pas, g.orientation, g.echelle);
        ring.push([ring[0][0], ring[0][1]]);
        m = [[ring]];
      } else {
        try {
          const fond = o.style && o.style.fond;
          m = (fond && fond !== "none") ? versMulti(aplatir_objet(o)) : contour_en_multi(o);
        } catch (e) { compte.ignores++; continue; }
      }
      if (!m || !m.length) continue;
      mp = mp ? mz().union(mp, m) : m;
    }
    return mp;
  }

  function construire(r) {
    const doc = etat.doc, compte = { ignores: 0 };
    const pieces = [];
    if (r.mode === "tuiles") {
      const g = VL.grilleDoc();
      if (!g || g.type !== "hex") throw new Error("tuiles : le document n'a pas de grille hexagonale");
      const tuiles = doc.calques.filter((c) => c.visible)
        .flatMap((c) => c.objets.filter((o) => o.type === "tuile"));
      if (!tuiles.length) throw new Error("tuiles : aucune tuile visible");
      pieces.push(...plateau_pieces(tuiles, terrains_de(doc), g, { socle_mm: r.socle, sMm: sMm() })
        .filter((p) => p.tris.length));
    } else if (r.mode === "logo") {
      const sel = etat.selection.length
        ? etat.selection.map((id) => VL.objetDe(id)).filter(Boolean).map((t) => t.objet)
        : doc.calques.filter((c) => c.visible).flatMap((c) => c.objets);
      const mp = multiDe(sel, compte);
      if (!mp || !mp.length) throw new Error("logo : rien d'extrudable (sélection vide ou textes non vectorisés)");
      const mm = enMm(mp);
      const tris = r.evide ? extruder_evide(mz(), mm, r.hauteur, r.mur, r.plancher)
                 : extruder_biseau(mz(), mm, r.hauteur, r.biseau, r.pas);
      pieces.push({ nom: "logo", tris, hauteur_mm: r.hauteur });
    } else {
      const h = hauteurs_par_calque($("#impHauteurs").value, doc.calques);
      for (const c of doc.calques) {
        if (!c.visible) continue;
        const hc = h.parCalque[(c.nom || "").toLowerCase()] ?? h.globale;
        if (!(hc > 0)) continue;
        const mp = multiDe(c.objets, compte);
        if (!mp || !mp.length) continue;
        pieces.push({ nom: (c.nom || c.id).replace(/[^A-Za-z0-9_-]+/g, "_").slice(0, 40) || c.id,
                      tris: extruder(enMm(mp), hc, 0), hauteur_mm: hc });
      }
      if (!pieces.length) throw new Error("rien d'extrudable (calques visibles vides ?)");
    }
    const tous = pieces.flatMap((p) => p.tris);
    return { pieces, ignores: compte.ignores, tous, bbox: bboxDe(tous) };
  }

  function lire() {
    return reglages_lire({ mode: $("#impMode").value, hauteur: $("#impHauteur").value,
      socle: $("#impSocle").value, biseau: $("#impBiseau").value, evide: $("#impEvide").checked,
      mur: $("#impMur").value, plancher: $("#impPlancher").value });
  }
  function apercu() {
    const r = lire();
    const c = construire(r);
    if (courant && courant.glbUrl) URL.revokeObjectURL(courant.glbUrl);
    courant = { ...c, r, glbUrl: URL.createObjectURL(new Blob([glb_de_triangles(c.tous)],
                                                               { type: "model/gltf-binary" })) };
    $("#impViewer").setAttribute("src", courant.glbUrl);
    $("#impResume").textContent = resume_impression({ triangles: c.tous.length, bbox_mm: c.bbox,
      pieces: c.pieces.length, ignores: c.ignores }) + ` · volume ${Math.round(volume_de(c.tous) / 1000)} cm³`;
    const large = Math.max(...c.bbox.map(([a, b]) => b - a));
    $("#impGarde").textContent = large > 256
      ? `⚠ ${Math.round(large)} mm dépasse le plateau de 256 mm — le lot par tuile imprime pièce à pièce` : "";
    $("#impUnStl").disabled = false;
    $("#impLot").disabled = r.mode !== "tuiles";
    return courant;
  }
  async function unStl() {
    if (!courant) apercu();
    const stl = stl_binaire(courant.tous);
    const ps = new URLSearchParams({ nom: etat.meta.name, source: "vectorlab", etanche: "inconnue" });
    const r = await fetch("/api/print3d/from-stl?" + ps, { method: "POST",
      headers: { "Content-Type": "application/octet-stream" }, body: stl });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    apresExport(d);
    return d;
  }
  async function lot() {
    if (!courant) apercu();
    const fd = new FormData();
    for (const p of courant.pieces) {
      fd.append("pieces", new File([stl_binaire(p.tris)], p.nom + ".stl", { type: "application/octet-stream" }));
    }
    fd.append("nomenclature", nomenclature_csv(courant.pieces));
    const ps = new URLSearchParams({ nom: etat.meta.name, source: "vectorlab" });
    const r = await fetch("/api/print3d/lot?" + ps, { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    apresExport(d);
    return d;
  }
  function apresExport(d) {
    $("#impResume").textContent = `dossier d'impression : ${d.dossier} (${d.triangles} triangles`
      + `${d.pieces ? `, ${d.pieces} pièces` : ""})` + (d.avertissement ? " — " + d.avertissement : "");
    $("#impOuvrir").disabled = false;
    $("#impOuvrir").dataset.dossier = d.dossier;
    VL.toast(`export écrit : ${d.dossier}`);
  }
  async function ouvrir() {
    const dossier = $("#impOuvrir").dataset.dossier;
    if (!dossier) return;
    const o = await fetch("/api/print3d/open", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ dossier }) });
    const od = await o.json().catch(() => ({}));
    if (!o.ok) throw new Error(od.detail || o.statusText);
    VL.toast(`slicer ouvert (${od.mode})`);
  }
  function fermer() {
    dlg.classList.add("hidden");
    dlg.innerHTML = "";
    if (courant && courant.glbUrl) URL.revokeObjectURL(courant.glbUrl);
    courant = null;
  }

  VL.impression = (modeInitial) => {
    const doc = etat.doc, dpi = (doc.unites && doc.unites.dpi) || 96, s = 25.4 / dpi;
    const aHex = !!(doc.grille && doc.grille.type === "hex")
      && doc.calques.some((c) => c.objets.some((o) => o.type === "tuile"));
    const mode = modeInitial || (aHex ? "tuiles" : (etat.selection.length ? "logo" : "calques"));
    dlg.innerHTML = `<div class="vl-dlg-boite imp-boite">
      <div class="vl-dlg-tete"><b>Impression 3D</b><span class="imp-doc">${Math.round(doc.taille.w * s)} × ${Math.round(doc.taille.h * s)} mm à ${dpi} dpi · plateau 256 mm</span><span class="spacer"></span><button id="impFermer" title="Fermer">✕</button></div>
      <div class="imp-corps">
        <div class="imp-regles">
          <label>Mode <select id="impMode">
            <option value="calques"${mode === "calques" ? " selected" : ""}>Calques (relief par calque)</option>
            <option value="tuiles"${mode === "tuiles" ? " selected" : ""}${aHex ? "" : " disabled"}>Tuiles (socle + terrain, lot)</option>
            <option value="logo"${mode === "logo" ? " selected" : ""}>Logo (sélection unie : biseau / évidement)</option></select></label>
          <label class="imp-calques">Hauteurs (mm, « nom=mm ») <input id="impHauteurs" type="text" value="3"/></label>
          <label class="imp-logo">Hauteur (mm) <input id="impHauteur" type="number" step="0.1" min="0.2" value="5"/></label>
          <label class="imp-tuiles">Socle (mm) <input id="impSocle" type="number" step="0.1" min="0" value="2"/></label>
          <label class="imp-logo">Biseau (mm) <input id="impBiseau" type="number" step="0.1" min="0" value="0.6"/></label>
          <label class="imp-logo imp-ligne"><input type="checkbox" id="impEvide"/> évider (mur ≥ ${MUR_MIN_MM} mm)</label>
          <label class="imp-logo">Mur (mm) <input id="impMur" type="number" step="0.1" min="${MUR_MIN_MM}" value="1.2"/></label>
          <label class="imp-logo">Plancher (mm) <input id="impPlancher" type="number" step="0.1" min="0" value="1"/></label>
          <button id="impApercu" class="primaire">Aperçu 3D</button>
          <p id="impResume" class="tr-etat">réglez, puis Aperçu</p><p id="impGarde" class="imp-garde"></p>
        </div>
        <model-viewer id="impViewer" loading="eager" reveal="auto" camera-controls auto-rotate shadow-intensity="1" exposure="1" class="imp-viewer"></model-viewer>
      </div>
      <div class="tr-pied"><button id="impUnStl" disabled title="Un seul STL + 3MF (tout le rendu en une pièce)">Un STL</button>
        <button id="impLot" disabled title="Un STL par tuile + plateau.3mf + nomenclature.csv">Lot par tuile</button>
        <button id="impOuvrir" disabled title="Ouvrir le .3mf dans le slicer">Ouvrir le slicer</button></div></div>`;
    dlg.classList.remove("hidden");
    const majMode = () => {
      const m = $("#impMode").value;
      dlg.querySelectorAll(".imp-calques").forEach((e) => { e.style.display = m === "calques" ? "" : "none"; });
      dlg.querySelectorAll(".imp-logo").forEach((e) => { e.style.display = m === "logo" ? "" : "none"; });
      dlg.querySelectorAll(".imp-tuiles").forEach((e) => { e.style.display = m === "tuiles" ? "" : "none"; });
    };
    majMode();
    const garde = (fn) => () => Promise.resolve().then(fn).catch((e) => {
      $("#impResume").textContent = e.message; VL.toast(e.message, true); });
    $("#impMode").addEventListener("change", majMode);
    $("#impApercu").addEventListener("click", garde(apercu));
    $("#impUnStl").addEventListener("click", garde(unStl));
    $("#impLot").addEventListener("click", garde(lot));
    $("#impOuvrir").addEventListener("click", garde(ouvrir));
    $("#impFermer").addEventListener("click", fermer);
  };
  // la preuve appelle ces trois-là sans cliquer
  VL.impressionApercu = apercu;
  VL.impressionUnStl = unStl;
  VL.impressionLot = lot;

  /* ── texte → chemins : la police du dist, lue par opentype.js ── */
  const polices = new Map();
  async function police(id) {
    const p = POLICES.find((x) => x.id === id) || POLICES[0];
    if (!window.opentype) throw new Error("opentype.js indisponible (vendor non chargé)");
    if (!polices.has(p.id)) {
      const r = await fetch("/fonts/" + p.fichier);
      if (!r.ok) throw new Error(`police ${p.fichier} introuvable (${r.status})`);
      polices.set(p.id, window.opentype.parse(await r.arrayBuffer()));
    }
    return polices.get(p.id);
  }
  VL.vectoriserTexte = async (id, policeId) => {
    const t = VL.objetDe(id);
    if (!t || t.objet.type !== "texte") throw new Error("pas un texte");
    const o = t.objet, s = o.style || {};
    const font = await police(policeId);
    const d = texte_vers_d(font, o.contenu, +s.corps || 16, +o.x, +o.y, +s.interlettrage || 0);
    const r = VL.executer(op_texte_vectoriser, id, d);
    if (r) { VL.setSelection([id]); VL.toast("texte vectorisé — c'est maintenant un chemin (annulable)"); }
    return r;
  };
}
