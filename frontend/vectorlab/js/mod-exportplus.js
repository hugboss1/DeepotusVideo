// mod-exportplus.js — le persona Export du lot G : panneau « Export + »
// (mode de tranche, résolutions, formats, preset d'impression, plan de
// nommage, export lot), outil « tranche » dessinée sur la scène, rendu
// JPEG / WebP / PNG par canvas (marques de coupe comprises), SVG par
// tranche, PDF par la route stdlib du backend, DXF par aplatir_objet.
// Les rasters partent dans la Bibliothèque (route d'import existante, nom
// `vector_…` = provenance vectorlab) ; SVG, PDF et DXF se téléchargent.
import { MODES, FORMATS, tranches_de, resolutions_lire, plan_export, mm_px, cadre_saignee, marques_svg } from "./mod-tranches.js";
import { dxf_de, polylignes_mm } from "./mod-dxf.js";
import { bbox_objet } from "./mod-doc.js";
import { aplatir_objet } from "./mod-bool.js";

const SNS = "http://www.w3.org/2000/svg";
export const HINTS4 = { tranche: "glisser un rectangle : une tranche à exporter · Échap efface les tranches dessinées" };
const _num = (v, d) => { if (v === undefined || v === null || String(v).trim() === "") return d; const x = +String(v).replace(",", "."); return Number.isFinite(x) ? x : d; };

export function reglages_lire(c = {}) {
  const formats = (Array.isArray(c.formats) ? c.formats : []).filter((f) => FORMATS.some((x) => x.id === f));
  return {
    mode: MODES.some((m) => m.id === c.mode) ? c.mode : "document",
    resolutions: resolutions_lire(c.resolutions),
    formats: formats.length ? formats : ["png"],
    transparent: !!c.transparent,
    saignee: Math.max(0, Math.min(50, _num(c.saignee, 0))),
    coupe: !!c.coupe, reperage: !!c.reperage,
    dpi: Math.max(36, Math.min(1200, Math.round(_num(c.dpi, 300)))),
    qualite: Math.max(0.1, Math.min(1, _num(c.qualite, 0.92))),
  };
}
export function resume_plan(plan) {
  if (!plan || !plan.length) return "rien à exporter (aucune tranche ou aucun format)";
  const raster = plan.filter((e) => (FORMATS.find((f) => f.id === e.format) || {}).raster).length;
  const autres = plan.length - raster;
  return `${plan.length} fichier(s) : ${raster} raster(s) vers la Bibliothèque, ${autres} téléchargé(s) (SVG / PDF / DXF)`;
}
// pages PDF : la tranche en mm au dpi du DOCUMENT, saignée ajoutée de chaque
// côté ; w_px / h_px à l'échelle k du rendu
export function pages_pdf(tranches, dpiDoc, saigneeMm, k = 1) {
  const s = mm_px(saigneeMm, dpiDoc);
  return tranches.map((t) => ({
    w_mm: t.cadre.w / dpiDoc * 25.4 + 2 * saigneeMm, h_mm: t.cadre.h / dpiDoc * 25.4 + 2 * saigneeMm,
    w_px: Math.round((t.cadre.w + 2 * s) * k), h_px: Math.round((t.cadre.h + 2 * s) * k),
  }));
}
export function tranche_normaliser(x0, y0, x1, y1, n) {
  const x = Math.min(x0, x1), y = Math.min(y0, y1);
  return { nom: `t${n}`, x, y, w: Math.max(1, Math.abs(x1 - x0)), h: Math.max(1, Math.abs(y1 - y0)) };
}

export function initExportPlus(VL) {
  const { $, etat } = VL;
  const hote = $("#panneauExportPlus"), stage = $("#stage");
  etat.tranches = [];
  etat.exportPlus = { mode: "document", resolutions: "1", formats: ["png"], transparent: false, saignee: 0, coupe: false, reperage: false, dpi: 300, qualite: 0.92 };
  let geste = null;

  // l'outil tranche dans la barre (persona Export)
  {
    const b = document.createElement("button");
    b.dataset.outil = "tranche"; b.className = "outil-export"; b.title = "Tranche — glisser un rectangle à exporter (persona Export)"; b.textContent = "⧉";
    b.addEventListener("click", () => VL.setOutil("tranche"));
    $("#outils").appendChild(b);
  }
  stage.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0 || !etat.doc || etat.outil !== "tranche") return;
    ev.stopPropagation(); ev.preventDefault();
    const [x, y] = VL.aimantePt(...VL.docPt(ev.clientX, ev.clientY));
    geste = { x0: x, y0: y, x1: x, y1: y };
  }, true);
  stage.addEventListener("pointermove", (ev) => {
    if (!geste) return;
    ev.stopPropagation();
    [geste.x1, geste.y1] = VL.aimantePt(...VL.docPt(ev.clientX, ev.clientY));
    const t = $("#ovTmp"); if (!t) return;
    t.innerHTML = "";
    const [ax, ay] = VL.ecranPt(Math.min(geste.x0, geste.x1), Math.min(geste.y0, geste.y1));
    const r = document.createElementNS(SNS, "rect");
    r.setAttribute("x", ax); r.setAttribute("y", ay); r.setAttribute("width", Math.abs(geste.x1 - geste.x0) * etat.zoom); r.setAttribute("height", Math.abs(geste.y1 - geste.y0) * etat.zoom);
    r.setAttribute("fill", "rgba(57,179,208,.10)"); r.setAttribute("stroke", "#39b3d0"); r.setAttribute("stroke-dasharray", "6 4");
    t.appendChild(r);
  }, true);
  stage.addEventListener("pointerup", (ev) => {
    if (!geste) return;
    ev.stopPropagation();
    const g = geste; geste = null;
    const t = $("#ovTmp"); if (t) t.innerHTML = "";
    if (Math.abs(g.x1 - g.x0) < 2 || Math.abs(g.y1 - g.y0) < 2) return;
    etat.tranches.push(tranche_normaliser(g.x0, g.y0, g.x1, g.y1, etat.tranches.length + 1));
    etat.exportPlus.mode = "dessinees";
    VL.rendreOverlay(); rendre();
  }, true);
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && etat.outil === "tranche" && etat.tranches.length) { etat.tranches = []; VL.rendreOverlay(); rendre(); ev.stopImmediatePropagation(); }
  }, true);
  const suivantOverlay = VL.surOverlay;
  VL.surOverlay = (ov) => {
    suivantOverlay(ov);
    if (etat.persona !== "export" || !etat.tranches.length) return;
    for (const t of etat.tranches) {
      const [ax, ay] = VL.ecranPt(t.x, t.y);
      const r = document.createElementNS(SNS, "rect");
      r.setAttribute("x", ax); r.setAttribute("y", ay); r.setAttribute("width", t.w * etat.zoom); r.setAttribute("height", t.h * etat.zoom);
      r.setAttribute("fill", "none"); r.setAttribute("stroke", "#39b3d0"); r.setAttribute("stroke-dasharray", "6 4"); r.setAttribute("class", "tranche");
      ov.appendChild(r);
      const l = document.createElementNS(SNS, "text");
      l.setAttribute("x", ax + 3); l.setAttribute("y", ay - 3); l.setAttribute("fill", "#39b3d0"); l.setAttribute("font-size", "11"); l.textContent = t.nom;
      ov.appendChild(l);
    }
  };

  /* ── le rendu d'une tranche ── */
  const dpiDoc = () => (VL.unites && VL.unites().dpi) || 300;
  function docPour(t) {
    const doc = JSON.parse(JSON.stringify(etat.doc));
    if (t.calqueId) for (const c of doc.calques) c.visible = c.id === t.calqueId;
    if (t.id) for (const c of doc.calques) c.objets = c.objets.filter((o) => o.id === t.id);
    return doc;
  }
  async function svgTranche(t, r) {
    const s = mm_px(r.saignee, dpiDoc());
    const cadre = cadre_saignee(t.cadre, s);
    let svg = await VL.svgCourant(r.transparent, cadre, docPour(t));
    const marques = marques_svg(t.cadre, s, { coupe: r.coupe, reperage: r.reperage }, Math.max(6, s || 8));
    if (marques) {
      // les marques vivent HORS du cadre élargi : la vue s'agrandit d'autant
      const L = Math.max(6, s || 8) + 2, c2 = cadre_saignee(cadre, L);
      svg = await VL.svgCourant(r.transparent, c2, docPour(t));
      svg = svg.replace(/<\/svg>\s*$/, marques + "</svg>");
      return { svg, cadre: c2 };
    }
    return { svg, cadre };
  }
  function rasteriser(svg, cadre, k, format, r) {
    return new Promise((res, rej) => {
      const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" })), img = new Image();
      img.onload = () => {
        const cv = document.createElement("canvas");
        cv.width = Math.max(1, Math.round(cadre.w * k)); cv.height = Math.max(1, Math.round(cadre.h * k));
        const cx = cv.getContext("2d");
        if (format === "jpeg" || (!r.transparent && format !== "png")) { cx.fillStyle = etat.doc.fond || "#FFFFFF"; cx.fillRect(0, 0, cv.width, cv.height); }
        cx.drawImage(img, 0, 0, cv.width, cv.height);
        URL.revokeObjectURL(url);
        cv.toBlob((b) => b ? res(b) : rej(new Error("rendu vide")), { png: "image/png", jpeg: "image/jpeg", webp: "image/webp" }[format], r.qualite);
      };
      img.onerror = () => { URL.revokeObjectURL(url); rej(new Error("SVG non décodable")); };
      img.src = url;
    });
  }
  const telecharger = (blob, nom) => { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = nom; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
  async function deposer(blob, nom) {
    const fd = new FormData();
    fd.append("file", new File([blob], nom, { type: blob.type }));
    const rp = await fetch("/api/images/upload", { method: "POST", body: fd });
    const d = await rp.json().catch(() => ({}));
    if (!rp.ok) throw new Error(d.detail || rp.statusText);
    return d.filename;
  }
  function dxfTranche(t, r) {
    const doc = docPour(t);
    const anneaux = [];
    const visiter = (objs) => { for (const o of objs || []) { if (o.type === "groupe") { visiter(o.enfants); continue; } if (["texte", "cadre", "textechemin", "image", "instance"].includes(o.type)) continue; try { anneaux.push(...aplatir_objet(o)); } catch (e) { /* objet non aplatissable */ } } };
    for (const c of doc.calques) if (c.visible !== false) visiter(c.objets);
    // un anneau compte s'il CHEVAUCHE la tranche (bbox), pas seulement s'il y a un sommet dedans
    const c = t.cadre;
    const dedans = anneaux.filter((a) => {
      const xs = a.map((q) => q[0]), ys = a.map((q) => q[1]);
      return Math.max(...xs) >= c.x && Math.min(...xs) <= c.x + c.w && Math.max(...ys) >= c.y && Math.min(...ys) <= c.y + c.h;
    });
    if (!dedans.length) return null;                 // rien à découper : la tranche est sautée (dit au toast)
    return dxf_de(polylignes_mm(dedans, t.cadre, dpiDoc()), { calque: t.nom });
  }
  function tranches() {
    const r = reglages_lire(etat.exportPlus);
    return tranches_de(etat.doc, r.mode, { ids: etat.selection.slice(), bboxDe: (o) => bbox_objet(o, etat.doc), dessinees: etat.tranches });
  }
  function plan() {
    const r = reglages_lire(etat.exportPlus);
    return plan_export(etat.docId, tranches(), r.resolutions, r.formats, r.transparent);
  }
  async function exporterLot() {
    const r = reglages_lire(etat.exportPlus), p = plan();
    if (!p.length) throw new Error("rien à exporter");
    const faits = [], sautes = [];
    for (const e of p) {
      if (e.format === "pdf") {
        const k = r.dpi / dpiDoc(), specs = pages_pdf(e.tranches, dpiDoc(), r.saignee, k), fd = new FormData();
        for (let i = 0; i < e.tranches.length; i++) {
          const { svg, cadre } = await svgTranche(e.tranches[i], { ...r, coupe: r.coupe, reperage: r.reperage });
          specs[i].w_px = Math.max(1, Math.round(cadre.w * k)); specs[i].h_px = Math.max(1, Math.round(cadre.h * k));
          specs[i].w_mm = cadre.w / dpiDoc() * 25.4; specs[i].h_mm = cadre.h / dpiDoc() * 25.4;
          fd.append("pages_fichiers", new File([await rasteriser(svg, cadre, k, "jpeg", r)], `page${i}.jpg`, { type: "image/jpeg" }));
        }
        fd.append("pages", JSON.stringify(specs));
        const rp = await fetch(`/api/vector/docs/${encodeURIComponent(etat.docId)}/pdf`, { method: "POST", body: fd });
        if (!rp.ok) { const d = await rp.json().catch(() => ({})); throw new Error(d.detail || rp.statusText); }
        telecharger(await rp.blob(), e.nom); faits.push(e.nom); continue;
      }
      if (e.format === "dxf") {
        const dxf = dxfTranche(e.tranche, r);
        if (!dxf) { sautes.push(e.nom); continue; }
        telecharger(new Blob([dxf], { type: "application/dxf" }), e.nom); faits.push(e.nom); continue;
      }
      const { svg, cadre } = await svgTranche(e.tranche, r);
      if (e.format === "svg") { telecharger(new Blob([svg], { type: "image/svg+xml" }), e.nom); faits.push(e.nom); continue; }
      faits.push(await deposer(await rasteriser(svg, cadre, e.k, e.format, r), e.nom));
    }
    VL.toast(`export lot : ${faits.length} fichier(s) — ${faits.slice(0, 3).join(", ")}${faits.length > 3 ? "…" : ""}${sautes.length ? ` · ${sautes.length} DXF vide(s) sauté(s)` : ""}`);
    return faits;
  }

  /* ── panneau ── */
  function rendre() {
    if (!hote) return;
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const r = etat.exportPlus;
    let p = [], erreur = "";
    try { p = plan(); } catch (e) { erreur = e.message; }
    hote.innerHTML = `
      <div class="ap-ligne"><span>Tranches</span><select id="exMode">${MODES.map((m) => `<option value="${m.id}"${r.mode === m.id ? " selected" : ""}>${m.libelle}</option>`).join("")}</select></div>
      <div class="ap-ligne"><span></span><i class="px-note">${etat.tranches.length} dessinée(s)</i><button id="exTrancheOutil" title="Dessiner une tranche sur la scène">⧉ dessiner</button><button id="exTrancheX" ${etat.tranches.length ? "" : "disabled"} title="Efface les tranches dessinées">✕</button></div>
      <div class="ap-ligne"><span>Résol.</span><input type="text" id="exRes" value="${r.resolutions}" title="Résolutions raster, ex. 1, 2, 4 (suffixe @2x)" style="width:70px"/>
        <label title="Sans le fond du document"><input type="checkbox" id="exTransp"${r.transparent ? " checked" : ""}/> transp.</label></div>
      <div class="a2-champs">${FORMATS.map((f) => `<label><input type="checkbox" data-format="${f.id}"${r.formats.includes(f.id) ? " checked" : ""}/> ${f.libelle}</label>`).join("")}</div>
      <details ${r.saignee || r.coupe || r.reperage ? "open" : ""}><summary class="px-tete">Impression</summary>
        <div class="ap-ligne"><span>Saignée</span><input type="number" id="exSaignee" step="0.5" min="0" value="${r.saignee}" title="Fond perdu (mm) ajouté de chaque côté"/><span style="width:auto">mm</span>
          <input type="number" id="exDpi" min="36" max="1200" value="${r.dpi}" title="dpi du PDF"/><span style="width:auto">dpi</span></div>
        <div class="ap-ligne"><label><input type="checkbox" id="exCoupe"${r.coupe ? " checked" : ""}/> traits de coupe</label><label><input type="checkbox" id="exRep"${r.reperage ? " checked" : ""}/> repérage</label></div>
        <div class="ap-ligne"><span>Qualité</span><input type="range" id="exQual" min="0.3" max="1" step="0.01" value="${r.qualite}" title="JPEG / WebP"/><b id="exQualVal">${Math.round(r.qualite * 100)}</b></div>
      </details>
      <div class="ex-plan" id="exPlan">${erreur ? `<i class="px-note">${erreur}</i>` : p.map((e) => `<div title="${e.format}">${e.nom}</div>`).join("") || `<i class="px-note">${resume_plan([])}</i>`}</div>
      <div class="ap-ligne"><button id="exLot" class="primaire" ${p.length ? "" : "disabled"} style="flex:1" title="${resume_plan(p)}">Exporter le lot (${p.length})</button></div>`;
    const on = (id, ev, fn) => { const e = $("#" + id); if (e) e.addEventListener(ev, fn); };
    const maj = (patch) => { Object.assign(etat.exportPlus, patch); rendre(); };
    on("exMode", "change", (ev) => maj({ mode: ev.target.value }));
    on("exTrancheOutil", "click", () => { VL.setPersona && etat.persona !== "export" && VL.setPersona("export"); VL.setOutil("tranche"); });
    on("exTrancheX", "click", () => { etat.tranches = []; VL.rendreOverlay(); rendre(); });
    on("exRes", "change", (ev) => maj({ resolutions: ev.target.value }));
    on("exTransp", "change", (ev) => maj({ transparent: ev.target.checked }));
    hote.querySelectorAll("[data-format]").forEach((c) => c.addEventListener("change", () => maj({ formats: [...hote.querySelectorAll("[data-format]:checked")].map((x) => x.dataset.format) })));
    on("exSaignee", "change", (ev) => maj({ saignee: ev.target.value }));
    on("exDpi", "change", (ev) => maj({ dpi: ev.target.value }));
    on("exCoupe", "change", (ev) => maj({ coupe: ev.target.checked }));
    on("exRep", "change", (ev) => maj({ reperage: ev.target.checked }));
    on("exQual", "input", (ev) => { etat.exportPlus.qualite = +ev.target.value; $("#exQualVal").textContent = Math.round(ev.target.value * 100); });
    on("exLot", "click", () => { $("#exLot").disabled = true; exporterLot().catch((e) => VL.toast(e.message, true)).finally(rendre); });
  }
  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { suivantRendu(); rendre(); };
  const suivantSel = VL.surSelection;
  VL.surSelection = () => { suivantSel(); rendre(); };
  const suivantPersona = VL.surPersona;
  VL.surPersona = () => { suivantPersona(); rendre(); };
  const suivantOutil = VL.surOutil;
  VL.surOutil = () => { suivantOutil(); const h = $("#hintOutil"); if (h && HINTS4[etat.outil]) h.textContent = HINTS4[etat.outil]; };
  VL.exporterLot = exporterLot;          // la preuve
  VL.planExport = plan;
  rendre();
}
