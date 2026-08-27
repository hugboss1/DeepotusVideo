// mod-export.js — exports (phase 4) : le client COMPILE (compilateur
// unique, verrouillé au snapshot qa) ; le SVG part au serveur qui le
// stocke et le sert ; le PNG se rasterise ici (SVG → Image → canvas ×k)
// et part par la route d'import EXISTANTE de la Library ; « → Bible »
// ajoute l'export 2× aux inspiration_images d'une entité — le
// conditionnement de planche reste l'opt-in payant de la machinerie en
// place, rien ne tire ici.
import { compilerSVG } from "./mod-doc.js";

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

  VL.exporterPNG = exporterPNG;      // la preuve et les phases suivantes
}
