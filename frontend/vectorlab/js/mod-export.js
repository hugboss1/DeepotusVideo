// mod-export.js — exports (phase 4) : le client COMPILE (compilateur
// unique, verrouillé au snapshot qa) ; le SVG part au serveur qui le
// stocke et le sert ; le PNG se rasterise ici (SVG → Image → canvas ×k)
// et part par la route d'import EXISTANTE de la Library ; « → Bible »
// ajoute l'export 2× aux inspiration_images d'une entité — le
// conditionnement de planche reste l'opt-in payant de la machinerie en
// place, rien ne tire ici.
import { compilerSVG } from "./mod-doc.js";
import { image_hrefs, image_rev_max } from "./mod-image.js";

export function initExport(VL) {
  const { $, etat } = VL;

  async function svgCourant(transparent, cadre, docBase) {
    const doc = JSON.parse(JSON.stringify(docBase || etat.doc));   // lot G : une tranche compile SON document (calque / objet isolé)
    if (transparent) delete doc.fond;
    // un SVG chargé comme <img> ne peut PAS charger d'images externes :
    // chaque PNG du document est inliné en data: — pour l'export seulement,
    // le JSON stocké ne porte jamais de base64 (D1)
    const carte = new Map();
    for (const href of image_hrefs(doc)) {
      const r = await fetch(VL.imageUrl(href, image_rev_max(doc, href)), { cache: "no-store" });   // lot E : jamais un PNG périmé
      if (!r.ok) throw new Error(`image ${href} introuvable (${r.status})`);
      const b = await r.blob();
      carte.set(href, await new Promise((res, rej) => {
        const fr = new FileReader();
        fr.onload = () => res(fr.result); fr.onerror = () => rej(new Error("lecture image"));
        fr.readAsDataURL(b);
      }));
    }
    return compilerSVG(doc, { image: (h) => carte.get(h) || h, cadre, mesure: VL.mesureTexte });   // lot F : les cadres de texte se coupent comme à l'écran
  }

  async function exporterSVG() {
    const r = await fetch("/api/vector/docs/"
      + encodeURIComponent(etat.docId) + "/export", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ svg: await svgCourant($("#expTransparent").checked) }),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    VL.toast(`SVG stocké : ${d.filename}`);
    window.open("/api/vector/docs/" + encodeURIComponent(etat.docId)
                + "/export.svg", "_blank");
  }

  async function rasteriser(k, transparent, cadre) {
    const svg = await svgCourant(transparent, cadre);
    const taille = cadre || etat.doc.taille;       // lot C : une planche a SA taille
    return new Promise((res, rej) => {
      const blob = new Blob([svg], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);
      const img = new Image();
      img.onload = () => {
        const w = Math.round(taille.w * k);
        const h = Math.round(taille.h * k);
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

  async function exporterPNG(k, opts = {}) {
    const transparent = $("#expTransparent").checked;
    const png = await rasteriser(k, transparent, opts.cadre);
    // le transparent porte son suffixe : il n'écrase jamais l'opaque ; une
    // planche porte le sien (lot C) — l'export du document reste stable
    const nom = `vector_${etat.docId}${opts.suffixe || ""}_${k}x${transparent ? "_t" : ""}.png`;
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

  /* ── impression 3D : la voie du lot D — le dialogue de mod-impression.js
     (modes calques / tuiles / logo, aperçu 3D, un STL ou un lot). Le
     prompt() de la phase 3 du plan slicer a déménagé là-bas. */
  function imprimer3D() {
    if (!VL.impression) throw new Error("impression 3D indisponible (module non chargé)");
    VL.impression();
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
  VL.svgCourant = svgCourant;        // lot G : le persona Export rend ses tranches par ici
  VL.vignette = vignette;            // le save de core.js l'appelle
}
