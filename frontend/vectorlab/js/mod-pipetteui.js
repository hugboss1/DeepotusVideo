// mod-pipetteui.js — l'UI du Sélecteur de couleur (21/09/2026), patron de
// mod-plumeui : écoute en CAPTURE sur #stage quand `etat.outil === "pipette"`
// et arrête la propagation (mod-tools ne voit que le Ctrl + clic = l'ancienne
// pipette de STYLE). Au pointerdown, le document est rasterisé UNE fois à
// l'échelle de l'écran (sérialisation du <svg> de #canvasHost, transform
// retiré, <image href> inlinées, image-rendering recopié — la voie mesurée
// du skill didacticiel-option) ; la loupe (120 px, ×8, croix) suit le
// pointeur avec la lecture R : G : B ; au pointerup la couleur prélevée va
// au fond (clic droit : contour) de la sélection si « Appliquer », sinon à
// la couleur courante. Maj inverse la loupe, Alt inverse « Appliquer ».
import { echantillon_rayon, hex_de_rgb, pipette_decision, PIPETTE_DEFAUT } from "./mod-pipette.js";
import { op_style } from "./mod-doc.js";

export function initPipetteUI(VL) {
  const { $, etat } = VL;
  const stage = $("#stage");
  if (!stage) return;
  etat.pipette = { ...PIPETTE_DEFAUT, ...(etat.pipette || {}) };
  const loupe = document.createElement("div");
  loupe.className = "vl-loupe hidden";
  loupe.innerHTML = `<canvas width="120" height="120"></canvas><div class="vl-loupe-val"></div>`;
  document.body.appendChild(loupe);
  const lcv = loupe.querySelector("canvas"), lval = loupe.querySelector(".vl-loupe-val");
  let raster = null, geste = null;

  async function inliner(svg) {
    const clone = svg.cloneNode(true);
    const origs = [...svg.querySelectorAll("image")], imgs = [...clone.querySelectorAll("image")];
    imgs.forEach((im, i) => { const cs = origs[i] && getComputedStyle(origs[i]).imageRendering; if (cs && cs !== "auto") im.setAttribute("style", "image-rendering:" + cs); });
    for (const im of imgs) {
      const href = im.getAttribute("href") || im.getAttribute("xlink:href") || "";
      if (!href || href.startsWith("data:")) continue;
      try {
        const r = await fetch(href); if (!r.ok) throw new Error(String(r.status));
        const b = await r.blob();
        const d = await new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.readAsDataURL(b); });
        im.setAttribute("href", d); im.removeAttribute("xlink:href");
      } catch (e) { /* image injoignable : elle restera vide */ }
    }
    return clone;
  }
  // le rendu du document à l'échelle de l'écran, en coordonnées du stage
  async function rasteriser(source) {
    const svg = $("#canvasHost svg"); if (!svg) return null;
    const sr = stage.getBoundingClientRect(), bb = svg.getBoundingClientRect();
    const clone = await inliner(svg);
    if (source === "calque" && etat.calqueActif) {
      for (const g of [...clone.querySelectorAll("[data-calque]")]) if (g.getAttribute("data-calque") !== etat.calqueActif) g.remove();
    }
    if (!clone.getAttribute("xmlns")) clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clone.removeAttribute("style"); clone.style.transform = "none";
    clone.setAttribute("width", String(Math.max(1, Math.round(bb.width)))); clone.setAttribute("height", String(Math.max(1, Math.round(bb.height))));
    const s = new XMLSerializer().serializeToString(clone);
    const img = new Image();
    await new Promise((res, rej) => { img.onload = res; img.onerror = () => rej(new Error("rendu illisible")); img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(s); });
    const cv = document.createElement("canvas"); cv.width = Math.max(1, Math.round(sr.width)); cv.height = Math.max(1, Math.round(sr.height));
    const ctx = cv.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(img, bb.left - sr.left, bb.top - sr.top, bb.width, bb.height);
    const d = ctx.getImageData(0, 0, cv.width, cv.height);
    return { w: d.width, h: d.height, data: d.data, canvas: cv, sr };
  }
  function lire(ev) {
    if (!raster) return null;
    const x = ev.clientX - raster.sr.left, y = ev.clientY - raster.sr.top;
    const e = echantillon_rayon(raster, x, y, etat.pipette.rayon);
    return e && { ...e, x, y, hex: e.n ? hex_de_rgb(e.r, e.g, e.b) : null };
  }
  function montrerLoupe(ev, e) {
    const veut = ev.shiftKey ? !etat.pipette.loupe : !!etat.pipette.loupe;
    if (!veut || !e) { loupe.classList.add("hidden"); return; }
    const ctx = lcv.getContext("2d"); ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, 120, 120);
    ctx.drawImage(raster.canvas, Math.round(e.x) - 7.5, Math.round(e.y) - 7.5, 15, 15, 0, 0, 120, 120);
    ctx.strokeStyle = "rgba(255,255,255,.9)"; ctx.lineWidth = 1; ctx.strokeRect(56.5, 56.5, 8, 8);
    ctx.strokeStyle = "rgba(0,0,0,.6)"; ctx.strokeRect(55.5, 55.5, 10, 10);
    lval.textContent = e.n ? `R : ${e.r}  G : ${e.g}  B : ${e.b}` : "transparent";
    loupe.style.left = (ev.clientX - 60) + "px"; loupe.style.top = (ev.clientY - 60 - 76) + "px";
    loupe.classList.remove("hidden");
  }
  function appliquerCouleur(hex, ev, droit) {
    // `ev.button` n'est pas assignable (getter) : le bouton du geste voyage à part
    const cible = ev.target && ev.target.closest && ev.target.closest("[data-objet]");
    const d = pipette_decision({ appliquer: etat.pipette.appliquer, alt: ev.altKey, ctrl: false, droit: !!droit, selection: etat.selection, cible: cible && cible.dataset.objet });
    if (!hex) { VL.toast("transparent — couleur inchangée"); return; }
    if (d.action === "fond" || d.action === "contour") {
      VL.executer(op_style, etat.selection.slice(), d.action === "fond" ? { fond: hex } : { contour: hex, epaisseur: (etat.styleCourant && etat.styleCourant.epaisseur) || 2 });
      VL.toast(`${d.action} de la sélection : ${hex}`);
    } else {
      etat.styleCourant = { ...etat.styleCourant, fond: hex };
      VL.toast(`couleur courante : ${hex} — les nouveaux objets la prendront`);
      VL.surSelection();
    }
  }
  stage.addEventListener("contextmenu", (ev) => { if (etat.outil === "pipette") ev.preventDefault(); }, true);
  stage.addEventListener("pointerdown", (ev) => {
    if (etat.outil !== "pipette" || !etat.doc) return;
    if (ev.ctrlKey) return;                         // Ctrl + clic : le style de l'objet — mod-tools (l'ancienne pipette)
    ev.stopImmediatePropagation(); ev.preventDefault();
    geste = { droit: ev.button === 2, dernier: null };
    try { stage.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
    rasteriser(etat.pipette.source).then((r) => { raster = r; if (!geste) return; const e = lire(ev); geste.dernier = e; montrerLoupe(ev, e); }).catch((e) => { VL.toast("pipette : " + e.message, true); geste = null; });
  }, true);
  stage.addEventListener("pointermove", (ev) => {
    if (!geste) return;
    ev.stopImmediatePropagation();
    const e = lire(ev); geste.dernier = e; montrerLoupe(ev, e);
  }, true);
  stage.addEventListener("pointerup", (ev) => {
    if (!geste) return;
    ev.stopImmediatePropagation();
    const g = geste; geste = null;
    loupe.classList.add("hidden");
    const fin = () => { const e = raster ? (lire(ev) || g.dernier) : g.dernier; appliquerCouleur(e && e.hex, ev, g.droit); };
    if (raster) fin(); else setTimeout(fin, 250);   // le rendu arrive encore
  }, true);
  VL.hints = Object.assign(VL.hints || {}, { pipette: "Cliquer ou Glisser pour prélever une couleur — Ctrl : le style de l'objet · Maj : loupe · Alt : appliquer à la sélection" });
  VL.pipette = { rasteriser, lire, loupe, get raster() { return raster; } };   // la preuve
}
