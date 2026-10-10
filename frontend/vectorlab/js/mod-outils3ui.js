// mod-outils3ui.js — les outils d'Affinity ajoutés au Vectorlab (R7) :
// Main (H), Loupe (Z), Plan de travail, Dégradé, Transparence (Y), Cadre
// de texte, Recadrer, et les pinceaux de retouche raster Flou / Éclaircir /
// Assombrir. Gestes en CAPTURE sur #stage (patron de mod-exportplus), une
// commande par geste via VL.executer, aperçu dans #ovTmp ; la géométrie est
// dans mod-outils3 (pure), les pixels dans mod-pixel (pur).
import { T } from "./mod-i18n.js";
import { zoom_rect, zoom_point, degrade_de_glisser, rognage_de_rect, cadre_de_rect, rect_normalise, disque_masque } from "./mod-outils3.js";
import { op_planche_ajouter, op_degrade_creer, op_degrade_transparence, op_image_rogner, op_ajouter, op_style } from "./mod-doc.js";
import { flou, hsl } from "./mod-pixel.js";

export const OUTILS3 = [
  { id: "main", touche: "h", titre: T("vectorlab.outils3.titre_main") },
  { id: "loupe", touche: "z", titre: T("vectorlab.outils3.titre_loupe") },
  { id: "planche", touche: "", titre: T("vectorlab.outils3.titre_planche") },
  { id: "degrade", touche: "", titre: T("vectorlab.outils3.titre_degrade") },
  { id: "transparence", touche: "y", titre: T("vectorlab.outils3.titre_transparence") },
  { id: "cadre", touche: "", titre: T("vectorlab.outils3.titre_cadre") },
  { id: "recadrer", touche: "", titre: T("vectorlab.outils3.titre_recadrer") },
  { id: "px-flou", touche: "", titre: T("vectorlab.outils3.titre_flou"), pixel: true },
  { id: "px-eclaircir", touche: "", titre: T("vectorlab.outils3.titre_eclaircir"), pixel: true },
  { id: "px-assombrir", touche: "", titre: T("vectorlab.outils3.titre_assombrir"), pixel: true },
];
export const HINTS5 = {
  main: T("vectorlab.outils3.hint_main"),
  loupe: T("vectorlab.outils3.hint_loupe"),
  planche: T("vectorlab.outils3.hint_planche"),
  degrade: T("vectorlab.outils3.hint_degrade"),
  transparence: T("vectorlab.outils3.hint_transparence"),
  cadre: T("vectorlab.outils3.hint_cadre"),
  recadrer: T("vectorlab.outils3.hint_recadrer"),
  "px-flou": T("vectorlab.outils3.hint_flou"),
  "px-eclaircir": T("vectorlab.outils3.hint_eclaircir"),
  "px-assombrir": T("vectorlab.outils3.hint_assombrir"),
};
const SNS = "http://www.w3.org/2000/svg";

export function initOutils3(VL) {
  const { $, etat } = VL;
  const stage = $("#stage"), nav = $("#outils");
  if (!stage || !nav) return;
  for (const o of OUTILS3) {
    const b = document.createElement("button");
    b.dataset.outil = o.id; b.title = o.titre; if (o.pixel) b.className = "outil-pixel";
    b.addEventListener("click", () => VL.setOutil(o.id));
    nav.appendChild(b);
  }
  VL.hints = Object.assign(VL.hints || {}, HINTS5);
  let geste = null;
  const scene = () => { const r = stage.getBoundingClientRect(); return { w: r.width, h: r.height }; };
  const ecran = (ev) => { const r = stage.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; };
  const apercu = (rect, couleur = "#4a90e2") => {
    const t = $("#ovTmp"); if (!t) return; t.innerHTML = "";
    if (!rect) return;
    const [x, y] = VL.ecranPt(rect.x, rect.y);
    const el = document.createElementNS(SNS, "rect");
    for (const [k, v] of Object.entries({ x, y, width: rect.w * etat.zoom, height: rect.h * etat.zoom, fill: "none", stroke: couleur, "stroke-width": 1, "stroke-dasharray": "5 3" })) el.setAttribute(k, v);
    t.appendChild(el);
  };
  const imageSel = () => { if (etat.selection.length !== 1) return null; const t = VL.objetDe(etat.selection[0]); return t && t.objet.type === "image" ? t.objet : null; };
  const pxOutil = () => etat.outil === "px-flou" || etat.outil === "px-eclaircir" || etat.outil === "px-assombrir";

  stage.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0 || !etat.doc) return;
    const o = etat.outil;
    if (!OUTILS3.some((x) => x.id === o)) return;
    ev.stopPropagation(); ev.preventDefault();
    try { stage.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
    const [ex, ey] = ecran(ev);
    if (o === "main") { geste = { type: "main", x: ev.clientX, y: ev.clientY, tx: etat.tx, ty: etat.ty }; stage.classList.add("main-panoramique"); return; }
    if (o === "loupe") { geste = { type: "loupe", e0: [ex, ey], e1: [ex, ey], alt: ev.altKey }; return; }
    if (pxOutil()) {
      const t = etat.px && etat.px.tampon;
      if (!t || !etat.px.id) { VL.toast(T("vectorlab.outils3.retouche_dabord"), true); geste = null; return; }
      geste = { type: "retouche", outil: o, n: 0 };
      retoucher(ev); return;
    }
    const p = VL.docPt(ev.clientX, ev.clientY);
    geste = { type: o, p0: VL.aimantePt(...p), p1: VL.aimantePt(...p) };
  }, true);
  stage.addEventListener("pointermove", (ev) => {
    if (!geste) return;
    ev.stopPropagation();
    if (geste.type === "main") { etat.tx = geste.tx + (ev.clientX - geste.x); etat.ty = geste.ty + (ev.clientY - geste.y); VL.appliquerVue(); return; }
    if (geste.type === "retouche") { retoucher(ev); return; }
    if (geste.type === "loupe") { geste.e1 = ecran(ev); const a = VL.docPt(0, 0); const r = rect_normalise([(geste.e0[0] - etat.tx) / etat.zoom, (geste.e0[1] - etat.ty) / etat.zoom], [(geste.e1[0] - etat.tx) / etat.zoom, (geste.e1[1] - etat.ty) / etat.zoom], 0); apercu(Math.hypot(geste.e1[0] - geste.e0[0], geste.e1[1] - geste.e0[1]) >= 6 ? r : null, "#fff"); void a; return; }
    geste.p1 = VL.aimantePt(...VL.docPt(ev.clientX, ev.clientY));
    if (geste.type === "degrade") { const t = $("#ovTmp"); if (t) { t.innerHTML = ""; const [x1, y1] = VL.ecranPt(...geste.p0), [x2, y2] = VL.ecranPt(...geste.p1); const l = document.createElementNS(SNS, "line"); for (const [k, v] of Object.entries({ x1, y1, x2, y2, stroke: "#39b3d0", "stroke-width": 1.5 })) l.setAttribute(k, v); t.appendChild(l); } return; }
    apercu(rect_normalise(geste.p0, geste.p1, 0), geste.type === "planche" ? "#e0b34a" : geste.type === "recadrer" ? "#d0553a" : "#4a90e2");
  }, true);
  stage.addEventListener("pointerup", (ev) => {
    if (!geste) return;
    ev.stopPropagation();
    const g = geste; geste = null;
    const t = $("#ovTmp"); if (t) t.innerHTML = "";
    if (g.type === "main") { stage.classList.remove("main-panoramique"); return; }
    if (g.type === "retouche") { if (g.n && VL.pixelCommettre) VL.pixelCommettre(); VL.rendre(); return; }
    if (g.type === "loupe") {
      const d = Math.hypot(g.e1[0] - g.e0[0], g.e1[1] - g.e0[1]);
      let v;
      if (d >= 6) v = zoom_rect(rect_normalise([(g.e0[0] - etat.tx) / etat.zoom, (g.e0[1] - etat.ty) / etat.zoom], [(g.e1[0] - etat.tx) / etat.zoom, (g.e1[1] - etat.ty) / etat.zoom], 0), scene(), 40);
      else v = zoom_point({ zoom: etat.zoom, tx: etat.tx, ty: etat.ty }, g.e0, g.alt ? 1 / 1.25 : 1.25);
      if (v) { etat.zoom = v.zoom; etat.tx = v.tx; etat.ty = v.ty; VL.appliquerVue(); }
      return;
    }
    const rect = rect_normalise(g.p0, g.p1, 4);
    if (g.type === "planche") {
      if (!rect) { VL.toast(T("vectorlab.outils3.planche_glisser"), true); return; }
      const n = ((etat.doc.planches || []).length + 1);
      const id = VL.executer(op_planche_ajouter, { nom: `Planche ${n}`, x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.w), h: Math.round(rect.h) });
      if (id) VL.toast(T("vectorlab.outils3.planche_posee", { nom: "Planche " + n }));
      return;
    }
    if (g.type === "degrade") {
      if (!etat.selection.length) { VL.toast(T("vectorlab.outils3.degrade_dabord"), true); return; }
      const tete = VL.objetDe(etat.selection[0]);
      const spec = degrade_de_glisser(g.p0, g.p1, (tete && tete.objet.style) || etat.styleCourant);
      if (!spec) return;
      const ids = etat.selection.slice();
      VL.executer((doc) => { const gid = op_degrade_creer(doc, spec); op_style(doc, ids, { fond: `grad:${gid}` }); });
      return;
    }
    if (g.type === "transparence") {
      if (!etat.selection.length) { VL.toast(T("vectorlab.outils3.transparence_dabord"), true); return; }
      if (!rect) return;
      VL.executer(op_degrade_transparence, etat.selection.slice(), rect);
      return;
    }
    if (g.type === "cadre") {
      if (!rect) { VL.toast(T("vectorlab.outils3.cadre_glisser"), true); return; }
      const s = { police: (etat.typo && (etat.typo.polices.find((p) => p.id === etat.typo.courante) || {}).famille) || "sans-serif", corps: 16, fond: etat.styleCourant.contour || "#1F1512" };
      const id = VL.executer(op_ajouter, etat.calqueActif, cadre_de_rect(rect, s, "Texte"));
      if (id) { VL.setOutil("select"); VL.setSelection([id]); if (VL.editerTexte) VL.editerTexte(id); }
      return;
    }
    if (g.type === "recadrer") {
      const img = imageSel();
      if (!img) { VL.toast(T("vectorlab.outils3.recadrer_dabord"), true); return; }
      if (!rect) return;
      const rg = rognage_de_rect(img, rect);
      if (!rg) { VL.toast(T("vectorlab.outils3.recadrer_hors"), true); return; }
      // le rognage garde l'échelle : l'objet prend la taille du rectangle
      VL.executer((doc) => { op_image_rogner(doc, img.id, rg); const o = doc.calques.flatMap((c) => c.objets).find((x) => x.id === img.id); o.x = rect.x; o.y = rect.y; o.w = rect.w; o.h = rect.h; });
    }
  }, true);
  stage.addEventListener("dblclick", (ev) => {
    if (etat.outil !== "recadrer") return;
    const img = imageSel(); if (!img || !img.rognage) return;
    ev.stopPropagation();
    VL.executer(op_image_rogner, img.id, null);
    VL.toast(T("vectorlab.outils3.rognage_retire"));
  }, true);

  /* ── retouche raster : un disque de masque au point, la primitive de mod-pixel dessus ── */
  function retoucher(ev) {
    const t = etat.px.tampon, o = VL.objetDe(etat.px.id);
    if (!t || !o) return;
    const im = o.objet, [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
    const r0 = im.rognage || { x: 0, y: 0, w: im.nat.w, h: im.nat.h };
    const px = r0.x + (dx - im.x) * r0.w / im.w, py = r0.y + (dy - im.y) * r0.h / im.h;   // px natifs
    const rayon = Math.max(1, etat.px.rayon || 4);
    const m = disque_masque(t.w, t.h, px, py, rayon);
    if (etat.px.masque) for (let i = 0; i < m.length; i++) if (!etat.px.masque[i]) m[i] = 0;   // la sélection raster borne
    if (geste.outil === "px-flou") flou(t, 1, m);
    else hsl(t, { l: geste.outil === "px-eclaircir" ? 6 : -6 }, m);
    geste.n++;
    if (VL.pixelApercu) VL.pixelApercu(); else if (geste.n % 4 === 1) VL.rendre();
  }

  /* ── raccourcis : H, Z, Y ── */
  const sTouche = VL.surTouche;
  VL.surTouche = (ev) => {
    const k = ev.key.toLowerCase();
    if (!ev.ctrlKey && !ev.altKey && (k === "h" || k === "z" || k === "y") && etat.doc) { VL.setOutil(k === "h" ? "main" : k === "z" ? "loupe" : "transparence"); return; }
    sTouche(ev);
  };
  VL.outils3 = { OUTILS3 };   // la preuve
}
