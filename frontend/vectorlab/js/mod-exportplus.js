// mod-exportplus.js — le persona Export du lot G : panneau « Export + »
// (mode de tranche, résolutions, formats, preset d'impression, plan de
// nommage, export lot), outil « tranche » dessinée sur la scène, rendu
// JPEG / WebP / PNG par canvas (marques de coupe comprises), SVG par
// tranche, PDF par la route stdlib du backend, DXF par aplatir_objet.
// Les rasters partent dans la Bibliothèque (route d'import existante, nom
// `vector_…` = provenance vectorlab) ; SVG, PDF et DXF se téléchargent.
import { T } from "./mod-i18n.js";
import { MODES, FORMATS, tranches_de, resolutions_lire, plan_export, mm_px, cadre_saignee, marques_svg, marques_objets } from "./mod-tranches.js";
import { dxf_de, polylignes_mm } from "./mod-dxf.js";
import { bbox_objet } from "./mod-doc.js";
import { aplatir_objet } from "./mod-bool.js";
import { pdf_page, pdf_assembler, matrice_de, matrice_mul } from "./mod-pdf.js";
import { dzi } from "./mod-icones.js";

const SNS = "http://www.w3.org/2000/svg";
export const HINTS4 = { tranche: T("vectorlab.export.hint_tranche") };
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
    // t121 : le PDF est VECTORIEL par défaut ; « image » garde l'ancien PDF du lot G (une image par page)
    pdf: c.pdf === "image" ? "image" : "vectoriel",
  };
}

/* ── t121 : le PDF vectoriel, logique pure ── */
// la boîte des pixels visibles d'un rendu RGBA, et ses pixels — un raster ne pèse que ce qu'il montre
export function recadrer_alpha(rgba, w, h) {
  let x0 = w, y0 = h, x1 = -1, y1 = -1;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (rgba[4 * (y * w + x) + 3]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  }
  if (x1 < 0) return null;
  const largeur = x1 - x0 + 1, hauteur = y1 - y0 + 1, out = new Uint8Array(4 * largeur * hauteur);
  for (let y = 0; y < hauteur; y++) out.set(rgba.subarray(4 * ((y0 + y) * w + x0), 4 * ((y0 + y) * w + x1 + 1)), 4 * y * largeur);
  return { x0, y0, largeur, hauteur, rgba: out };
}
// le document réduit à UN objet de premier niveau : sans fond, opacité et fusion de calque neutres — dans le
// PDF, le Form du calque les applique déjà ; les appliquer deux fois assombrirait le raster
export function doc_seul(doc, calqueId, id) {
  const d = JSON.parse(JSON.stringify(doc));
  delete d.fond;
  for (const c of d.calques) {
    c.objets = c.id === calqueId ? c.objets.filter((o) => o.id === id) : [];
    c.opacite = 1; c.fusion = "normal";
  }
  return d;
}
export function textes_de(doc) {
  const out = [];
  const visiter = (objs) => { for (const o of objs || []) { if (o.type === "texte") out.push(o); if (o.type === "groupe") visiter(o.enfants); } };
  for (const c of doc.calques || []) visiter(c.objets);
  for (const s of Object.values(doc.symboles || {})) visiter(s.objets);
  return out;
}
// t124 : ce que la découpe reçoit, en anneaux du document. Le transform des groupes se compose (il se
// perdait : la visite descendait dans les enfants sans lui) ; une instance découpe les objets de son
// symbole à sa place (même ordre que le PDF : transform · placement) ; un texte découpe les contours de
// ses glyphes, fournis par l'écran (opentype), le trou d'un O compris. Le reste est sauté ET compté par
// raison : image (pas de contour à découper), cadre et texte sur chemin (pas de glyphes posés), texte
// refusé (gras/italique synthétisés) ou police non chargée, symbole absent.
export function anneaux_dxf(doc, glyphes = () => null) {
  const anneaux = [], sautes = {};
  const saute = (r) => { sautes[r] = (sautes[r] || 0) + 1; };
  // aplatir_objet (mod-bool) ne lit que rotate() dans un transform : on l'aplatit nu, puis la matrice
  // complète (mod-pdf) s'applique aux points
  const aplatir = (o, m) => {
    let an;
    try { an = aplatir_objet({ ...o, transform: undefined }); } catch (e) { saute(o.type); return; }
    for (const a of an) anneaux.push(a.map(([x, y]) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]));
  };
  const SANS = { image: "image", cadre: T("vectorlab.export.raison_cadre"), textechemin: T("vectorlab.export.raison_textechemin") };
  const visiter = (objs, mParent) => {
    for (const o of objs || []) {
      if (SANS[o.type]) { saute(SANS[o.type]); continue; }
      const m = matrice_mul(mParent, matrice_de(o.transform));
      if (o.type === "groupe") { visiter(o.enfants, m); continue; }
      if (o.type === "instance") {
        if (doc.edition && doc.edition.instance === o.id) continue;      // t123 : son calque d'édition la montre
        const sym = (doc.symboles || {})[o.symbole];
        if (!sym) { saute(T("vectorlab.export.raison_symbole")); continue; }
        visiter(sym.objets, matrice_mul(m, [o.sx === undefined ? 1 : +o.sx, 0, 0, o.sy === undefined ? 1 : +o.sy, +o.x || 0, +o.y || 0]));
        continue;
      }
      if (o.type === "texte") {
        const g = glyphes(o);
        if (!g || g.raison) { saute((g && g.raison) || T("vectorlab.export.raison_police")); continue; }
        for (const gl of g) aplatir({ type: "path", d: gl.d }, m);
        continue;
      }
      aplatir(o, m);
    }
  };
  for (const c of doc.calques || []) if (c.visible !== false) visiter(c.objets, [1, 0, 0, 1, 0, 0]);
  return { anneaux, sautes };
}
export function resume_pdf(st) {
  const r = Object.entries(st.raisons || {}).map(([k, n]) => (n > 1 ? `${k} ×${n}` : k)).join(", ");
  return T("vectorlab.export.resume_pdf", { v: st.vectoriels, raster: st.rasterises ? T("vectorlab.export.resume_pdf_raster", { n: st.rasterises, r }) : T("vectorlab.export.resume_pdf_aucun") });
}
export function resume_plan(plan) {
  if (!plan || !plan.length) return T("vectorlab.export.plan_vide");
  const raster = plan.filter((e) => (FORMATS.find((f) => f.id === e.format) || {}).raster).length;
  const autres = plan.length - raster;
  return T("vectorlab.export.resume_plan", { n: plan.length, raster, autres });
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
  etat.exportPlus = { mode: "document", resolutions: "1", formats: ["png"], transparent: false, saignee: 0, coupe: false, reperage: false, dpi: 300, qualite: 0.92, pdf: "vectoriel" };
  let geste = null;

  // l'outil tranche dans la barre (persona Export)
  {
    const b = document.createElement("button");
    b.dataset.outil = "tranche"; b.title = T("vectorlab.export.outil_tranche");   // l'icône : mod-barreoutils
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
        cv.toBlob((b) => b ? res(b) : rej(new Error(T("vectorlab.export.rendu_vide"))), { png: "image/png", jpeg: "image/jpeg", webp: "image/webp" }[format], r.qualite);
      };
      img.onerror = () => { URL.revokeObjectURL(url); rej(new Error(T("vectorlab.export.svg_non_decodable"))); };
      img.src = url;
    });
  }
  /* ── t121 : le PDF VECTORIEL — mod-pdf écrit les vecteurs, l'écran ne fournit que les glyphes et les rasters ── */
  // un raster : l'objet SEUL rendu sur la page (au dpi d'export), recadré sur ses pixels visibles
  function rgbaDe(svg, cadre, k) {
    return new Promise((res, rej) => {
      const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" })), img = new Image();
      img.onload = () => {
        const cv = document.createElement("canvas");
        cv.width = Math.max(1, Math.round(cadre.w * k)); cv.height = Math.max(1, Math.round(cadre.h * k));
        const cx = cv.getContext("2d");
        cx.drawImage(img, 0, 0, cv.width, cv.height);
        URL.revokeObjectURL(url);
        res({ data: cx.getImageData(0, 0, cv.width, cv.height).data, w: cv.width, h: cv.height });
      };
      img.onerror = () => { URL.revokeObjectURL(url); rej(new Error(T("vectorlab.export.svg_non_decodable"))); };
      img.src = url;
    });
  }
  async function rasterObjet(doc, cadre, ra, k) {
    const svg = await VL.svgCourant(true, cadre, doc_seul(doc, ra.calque, ra.id));
    const { data, w, h } = await rgbaDe(svg, cadre, k);
    const c = recadrer_alpha(data, w, h);
    // un objet qui ne montre rien (hors tranche, transparent) : un pixel transparent, jamais un trou d'image
    if (!c) return { x: cadre.x, y: cadre.y, w: 1 / k, h: 1 / k, largeur: 1, hauteur: 1, rgba: new Uint8Array(4) };
    return { x: cadre.x + c.x0 / k, y: cadre.y + c.y0 / k, w: c.largeur / k, h: c.hauteur / k, largeur: c.largeur, hauteur: c.hauteur, rgba: c.rgba };
  }
  async function pdfVectoriel(e, r) {
    const pages = [], st = { vectoriels: 0, rasterises: 0, raisons: {} };
    const k = r.dpi / dpiDoc();
    for (const t of e.tranches) {
      const s = mm_px(r.saignee, dpiDoc());
      let cadre = cadre_saignee(t.cadre, s);
      const doc = docPour(t);
      if (r.coupe || r.reperage) {
        // les marques, en VECTEURS aussi : la même géométrie que le SVG, hors du cadre élargi d'autant
        const L = Math.max(6, s || 8);
        doc.calques.push({ id: "__marques", nom: "marques", visible: true, verrou: true, objets: marques_objets(t.cadre, s, { coupe: r.coupe, reperage: r.reperage }, L) });
        cadre = cadre_saignee(cadre, L + 2);
      }
      const glyphes = new Map();
      for (const o of textes_de(doc)) {
        try { glyphes.set(o.id, VL.glyphesTexte ? await VL.glyphesTexte(o) : null); } catch (err) { glyphes.set(o.id, { raison: T("vectorlab.export.raison_texte", { m: err.message }) }); }
      }
      const p = pdf_page(doc, cadre, { dpi: dpiDoc(), transparent: r.transparent, glyphes: (o) => glyphes.get(o.id) || null });
      p.images = {};
      for (const ra of p.rasters) {
        p.images[ra.nom] = await rasterObjet(doc, cadre, ra, k);
        st.raisons[ra.raison] = (st.raisons[ra.raison] || 0) + 1;
      }
      st.vectoriels += p.stats.vectoriels; st.rasterises += p.stats.rasterises;
      pages.push(p);
    }
    return { blob: new Blob([await pdf_assembler(pages)], { type: "application/pdf" }), st };
  }
  VL.pdfVectoriel = pdfVectoriel;          // poignée de preuve

  const telecharger = (blob, nom) => { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = nom; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
  async function deposer(blob, nom) {
    const fd = new FormData();
    fd.append("file", new File([blob], nom, { type: blob.type }));
    const rp = await fetch("/api/images/upload", { method: "POST", body: fd });
    const d = await rp.json().catch(() => ({}));
    if (!rp.ok) throw new Error(d.detail || rp.statusText);
    return d.filename;
  }
  // t124 : textes (glyphes de l'écran, comme le PDF) et instances découpés ; ce qui est sauté s'additionne
  // dans `ignores` pour le toast
  async function dxfTranche(t, r, ignores = {}) {
    const doc = docPour(t);
    const glyphes = new Map();
    for (const o of textes_de(doc)) {
      try { glyphes.set(o.id, VL.glyphesTexte ? await VL.glyphesTexte(o) : null); } catch (err) { glyphes.set(o.id, { raison: T("vectorlab.export.raison_texte", { m: err.message }) }); }
    }
    const { anneaux, sautes } = anneaux_dxf(doc, (o) => glyphes.get(o.id) || null);
    for (const [k, n] of Object.entries(sautes)) ignores[k] = (ignores[k] || 0) + n;
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
    if (!p.length) throw new Error(T("vectorlab.export.rien"));
    const faits = [], sautes = [], ignores = {};
    let bilanPdf = "";
    for (const e of p) {
      if (e.format === "pdf" && r.pdf === "vectoriel") {
        const { blob, st } = await pdfVectoriel(e, r);
        telecharger(blob, e.nom); faits.push(e.nom); bilanPdf = resume_pdf(st);
        continue;
      }
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
        const dxf = await dxfTranche(e.tranche, r, ignores);
        if (!dxf) { sautes.push(e.nom); continue; }
        telecharger(new Blob([dxf], { type: "application/dxf" }), e.nom); faits.push(e.nom); continue;
      }
      const { svg, cadre } = await svgTranche(e.tranche, r);
      if (e.format === "svg") { telecharger(new Blob([svg], { type: "image/svg+xml" }), e.nom); faits.push(e.nom); continue; }
      faits.push(await deposer(await rasteriser(svg, cadre, e.k, e.format, r), e.nom));
    }
    VL.toast(`${T("vectorlab.export.toast_lot", { n: faits.length })}${faits.slice(0, 3).join(", ")}${faits.length > 3 ? "…" : ""}${sautes.length ? ` · ${T("vectorlab.export.toast_dxf_vides", { n: sautes.length })}` : ""}${Object.keys(ignores).length ? ` · ${T("vectorlab.export.toast_hors_decoupe")}${Object.entries(ignores).map(([k, n]) => (n > 1 ? `${k} ×${n}` : k)).join(", ")}` : ""}${bilanPdf ? ` · ${bilanPdf}` : ""}`);
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
      <div class="ap-ligne"><span>${T("vectorlab.export.tranches")}</span><i class="px-note">${(MODES.find((m) => m.id === r.mode) || {}).libelle || r.mode} — ${T("vectorlab.export.menu_tranche")}</i></div>
      <div class="ap-ligne"><span></span><i class="px-note">${T("vectorlab.export.n_dessinees", { n: etat.tranches.length })}</i><button id="exTrancheOutil" title="${T("vectorlab.export.dessiner_titre")}">${dzi("dz-outil-vec-tranche", 16)}${T("vectorlab.export.dessiner")}</button><button id="exTrancheX" ${etat.tranches.length ? "" : "disabled"} title="${T("vectorlab.export.effacer_tranches")}" aria-label="${T("vectorlab.export.effacer_tranches")}">${dzi("dz-action-vider", 16)}</button></div>
      <div class="ap-ligne"><span>${T("vectorlab.export.resol")}</span><input type="text" id="exRes" value="${r.resolutions}" title="${T("vectorlab.export.resol_titre")}" style="width:70px"/>
        <label title="${T("vectorlab.export.transp_titre")}"><input type="checkbox" id="exTransp"${r.transparent ? " checked" : ""}/> ${T("vectorlab.export.transp")}</label></div>
      <div class="a2-champs">${FORMATS.map((f) => `<label><input type="checkbox" data-format="${f.id}"${r.formats.includes(f.id) ? " checked" : ""}/> ${f.libelle}</label>`).join("")}</div>
      <details ${r.saignee || r.coupe || r.reperage ? "open" : ""}><summary class="px-tete">${T("vectorlab.export.impression")}</summary>
        <div class="ap-ligne"><span>${T("vectorlab.export.saignee")}</span><input type="number" id="exSaignee" step="0.5" min="0" value="${r.saignee}" title="${T("vectorlab.export.saignee_titre")}"/><span style="width:auto">mm</span>
          <input type="number" id="exDpi" min="36" max="1200" value="${r.dpi}" title="${T("vectorlab.export.dpi_titre")}"/><span style="width:auto">dpi</span></div>
        <div class="ap-ligne"><span>PDF</span><select id="exPdf" title="${T("vectorlab.export.pdf_titre")}">
          <option value="vectoriel"${r.pdf === "vectoriel" ? " selected" : ""}>${T("vectorlab.export.opt_vectoriel")}</option><option value="image"${r.pdf === "image" ? " selected" : ""}>image</option></select></div>
        <div class="ap-ligne"><label><input type="checkbox" id="exCoupe"${r.coupe ? " checked" : ""}/> ${T("vectorlab.export.traits_coupe")}</label><label><input type="checkbox" id="exRep"${r.reperage ? " checked" : ""}/> ${T("vectorlab.export.reperage")}</label></div>
        <div class="ap-ligne"><span>${T("vectorlab.export.qualite")}</span><input type="range" id="exQual" min="0.3" max="1" step="0.01" value="${r.qualite}" title="JPEG / WebP"/><b id="exQualVal">${Math.round(r.qualite * 100)}</b></div>
      </details>
      <div class="ex-plan" id="exPlan">${erreur ? `<i class="px-note">${erreur}</i>` : p.map((e) => `<div title="${e.format}">${e.nom}</div>`).join("") || `<i class="px-note">${resume_plan([])}</i>`}</div>
      <div class="ap-ligne"><button id="exLot" class="primaire" ${p.length ? "" : "disabled"} style="flex:1" title="${resume_plan(p)}">${dzi("dz-action-exporter", 16)}${T("vectorlab.export.exporter_lot", { n: p.length })}</button></div>`;
    const on = (id, ev, fn) => { const e = $("#" + id); if (e) e.addEventListener(ev, fn); };
    const maj = (patch) => { Object.assign(etat.exportPlus, patch); rendre(); };
    on("exTrancheOutil", "click", () => { VL.setPersona && etat.persona !== "export" && VL.setPersona("export"); VL.setOutil("tranche"); });
    on("exTrancheX", "click", () => { etat.tranches = []; VL.rendreOverlay(); rendre(); });
    on("exRes", "change", (ev) => maj({ resolutions: ev.target.value }));
    on("exTransp", "change", (ev) => maj({ transparent: ev.target.checked }));
    hote.querySelectorAll("[data-format]").forEach((c) => c.addEventListener("change", () => maj({ formats: [...hote.querySelectorAll("[data-format]:checked")].map((x) => x.dataset.format) })));
    on("exSaignee", "change", (ev) => maj({ saignee: ev.target.value }));
    on("exDpi", "change", (ev) => maj({ dpi: ev.target.value }));
    on("exPdf", "change", (ev) => maj({ pdf: ev.target.value }));
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
  VL.hints = Object.assign(VL.hints || {}, HINTS4);
  VL.surOutil = () => { suivantOutil(); if (VL.majStatut) VL.majStatut(); else { const h = $("#hintOutil"); if (h && HINTS4[etat.outil]) h.textContent = HINTS4[etat.outil]; } };
  VL.exporterLot = exporterLot;          // la preuve
  VL.planExport = plan;
  rendre();
}
