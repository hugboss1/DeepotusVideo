// mod-export.js — exports (phase 4) : le client COMPILE (compilateur
// unique, verrouillé au snapshot qa) ; le SVG part au serveur qui le
// stocke et le sert ; le PNG se rasterise ici (SVG → Image → canvas ×k)
// et part par la route d'import EXISTANTE de la Library ; « → Bible »
// ajoute l'export 2× aux inspiration_images d'une entité — le
// conditionnement de planche reste l'opt-in payant de la machinerie en
// place, rien ne tire ici.
import { compilerSVG } from "./mod-doc.js";
import { aplatir_objet, contour_en_multi, versMulti } from "./mod-bool.js";
import { extruder, stl_binaire } from "./mod-extrude.js";

export function initExport(VL) {
  const { $, etat } = VL;

  function svgCourant(transparent) {
    const doc = JSON.parse(JSON.stringify(etat.doc));
    if (transparent) delete doc.fond;
    return compilerSVG(doc);
  }

  async function exporterSVG() {
    const r = await fetch("/api/vector/docs/"
      + encodeURIComponent(etat.docId) + "/export", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ svg: svgCourant($("#expTransparent").checked) }),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    VL.toast(`SVG stocké : ${d.filename}`);
    window.open("/api/vector/docs/" + encodeURIComponent(etat.docId)
                + "/export.svg", "_blank");
  }

  function rasteriser(k, transparent) {
    return new Promise((res, rej) => {
      const blob = new Blob([svgCourant(transparent)],
                            { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);
      const img = new Image();
      img.onload = () => {
        const w = Math.round(etat.doc.taille.w * k);
        const h = Math.round(etat.doc.taille.h * k);
        const cv = document.createElement("canvas");
        cv.width = w;
        cv.height = h;
        cv.getContext("2d").drawImage(img, 0, 0, w, h);
        URL.revokeObjectURL(url);
        cv.toBlob((png) => png ? res(png)
                              : rej(new Error("rasterisation vide")),
                  "image/png");
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        rej(new Error("SVG non décodable par le navigateur"));
      };
      img.src = url;
    });
  }

  async function exporterPNG(k) {
    const transparent = $("#expTransparent").checked;
    const png = await rasteriser(k, transparent);
    // le transparent porte son suffixe : il n'écrase jamais l'opaque
    const nom = `vector_${etat.docId}_${k}x${transparent ? "_t" : ""}.png`;
    const fd = new FormData();
    fd.append("file", new File([png], nom, { type: "image/png" }));
    const r = await fetch("/api/images/upload", { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    VL.toast(`${d.filename} déposé dans la Library (${k}×)`);
    return d.filename;
  }

  async function vignette() {
    // phase 6 : le mini-export qui suit chaque Sauver — 256 px de plus
    // grand côté, POSTé en binaire vers <id>.png à côté du JSON. Jamais
    // par /images/upload : la Library réelle reste propre.
    const { w, h } = etat.doc.taille;
    const png = await rasteriser(256 / Math.max(w, h), false);
    const r = await fetch("/api/vector/docs/"
      + encodeURIComponent(etat.docId) + "/vignette", {
      method: "POST", headers: { "Content-Type": "image/png" }, body: png,
    });
    if (!r.ok) throw new Error("vignette : " + r.status);
  }

  async function versBible() {
    const ents = (await VL.api.get("/bible/entities")).entities || [];
    if (!ents.length) {
      VL.toast("aucune entité dans la bible — crée-la dans l'Atelier", true);
      return;
    }
    const liste = ents.map((e, i) => `${i + 1}) [${e.kind}] ${e.name}`)
      .join("\n");
    const rep = prompt("Lier l'export 2× à quelle entité ?\n" + liste, "1");
    if (rep === null) return;
    const e = ents[(+rep || 0) - 1];
    if (!e) { VL.toast("numéro d'entité inconnu", true); return; }
    const fn = await exporterPNG(2);
    const insp = [...(e.inspiration_images || []), fn];
    await VL.api.put("/bible/entities/" + encodeURIComponent(e.id),
                     { inspiration_images: insp });
    VL.toast(`ajouté aux inspirations de « ${e.name} » — les planches `
             + "peuvent s'y conditionner (tir opt-in)");
  }

  /* ── impression 3D (phase 3 du plan slicer) : chaque calque visible
     s'aplatit (fonds pleins par aplatir_objet, tracés par leur contour
     GONFLÉ — les plombs), s'unit par martinez, puis s'extrude en prisme
     fermé à SA hauteur (relief). Le y du SVG descend, celui du plateau
     monte : retourné. Les textes sont ignorés et DITS, jamais bloquants. */
  async function imprimer3D() {
    const doc = etat.doc;
    const dpi = (doc.unites && doc.unites.dpi) || 96;
    const sMm = 25.4 / dpi;
    const rep = prompt(
      "Hauteur d'extrusion en mm ? Un nombre (ex. 3), plus des surcharges "
      + "par calque « nom=mm » à la virgule (ex. « 2, contours=5 » : les "
      + "plombs plus hauts que les verres).\nLe document fait "
      + `${Math.round(doc.taille.w * sMm)} × ${Math.round(doc.taille.h * sMm)} mm `
      + `à ${dpi} dpi — le plateau Centauri Carbon 2 fait 256 mm.`, "3");
    if (rep === null) return;
    let globale = null;
    const surcharges = {};
    for (const part of rep.split(",")) {
      const t = part.trim();
      if (!t) continue;
      const m = /^(.+?)=([0-9.]+)$/.exec(t);
      if (m) surcharges[m[1].trim().toLowerCase()] = +m[2];
      else if (globale === null && +t > 0) globale = +t;
    }
    if (!(globale > 0)) throw new Error("hauteur en mm invalide");
    const mz = window.martinez;
    if (!mz) throw new Error("martinez indisponible (vendor non chargé)");
    const tris = [];
    let ignores = 0;
    for (const c of doc.calques) {
      if (!c.visible) continue;
      const h = surcharges[(c.nom || "").toLowerCase()] ?? globale;
      if (!(h > 0)) continue;
      let mp = null;
      for (const o of c.objets) {
        if (o.type === "texte") { ignores++; continue; }
        let m = null;
        try {
          const fond = o.style && o.style.fond;
          m = (fond && fond !== "none")
            ? versMulti(aplatir_objet(o))
            : contour_en_multi(o);
        } catch (e) { ignores++; continue; }
        if (!m || !m.length) continue;
        mp = mp ? mz.union(mp, m) : m;
      }
      if (!mp || !mp.length) continue;
      const mmMulti = mp.map((poly) => poly.map((ring) =>
        ring.map(([x, y]) => [x * sMm, -y * sMm])));
      tris.push(...extruder(mmMulti, h, 0));
    }
    if (!tris.length) {
      throw new Error("rien d'extrudable (calques visibles vides ?)");
    }
    const stl = stl_binaire(tris);
    const ps = new URLSearchParams({ nom: etat.meta.name,
      source: "vectorlab", etanche: "inconnue" });
    const r = await fetch("/api/print3d/from-stl?" + ps, {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" }, body: stl });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    VL.toast(`dossier d'impression : ${d.dossier} (${d.triangles} triangles`
      + (ignores ? `, ${ignores} objet(s) ignoré(s) — textes` : "") + ")");
    if (confirm(`Export écrit (${d.dossier}) — ouvrir le .3mf dans le `
                + "slicer ?")) {
      const o = await fetch("/api/print3d/open", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dossier: d.dossier }) });
      const od = await o.json().catch(() => ({}));
      if (!o.ok) throw new Error(od.detail || o.statusText);
    }
  }

  /* ── le menu ── */
  const menu = $("#expMenu");
  $("#btnExporter").addEventListener("click", () => {
    menu.classList.toggle("hidden");
    if (!menu.classList.contains("hidden")) {
      // rôle lumière : fond transparent coché d'office (superposition)
      $("#expTransparent").checked =
        !!(etat.meta && etat.meta.role === "lumiere");
    }
  });
  const garde = (fn) => () => {
    menu.classList.add("hidden");
    Promise.resolve().then(fn).catch((e) => VL.toast(e.message, true));
  };
  $("#expSvg").addEventListener("click", garde(exporterSVG));
  $("#expPng1").addEventListener("click", garde(() => exporterPNG(1)));
  $("#expPng2").addEventListener("click", garde(() => exporterPNG(2)));
  $("#expPng4").addEventListener("click", garde(() => exporterPNG(4)));
  $("#expBible").addEventListener("click", garde(versBible));
  $("#expPrint3d").addEventListener("click", garde(imprimer3D));

  VL.exporterPNG = exporterPNG;      // la preuve et les phases suivantes
  VL.vignette = vignette;            // le save de core.js l'appelle
}
