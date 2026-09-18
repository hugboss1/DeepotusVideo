// mod-noeudui.js — l'outil Nœud de classe Affinity (R9), en complément de
// mod-tools (ancres) et mod-outils2 (lasso d'ancres) : les POIGNÉES se
// tirent (lisse : l'opposée s'aligne ; Alt : libre ; Maj : angle
// contraint), un SEGMENT du chemin sélectionné se déforme au glisser
// (une droite devient courbe), le double-clic sur un segment insère un
// nœud à cet endroit, Suppr fait une suppression LISSE, la barre
// contextuelle porte conversions / actions / alignements. Écouteurs en
// CAPTURE sur #stage, aperçu par VL.apercuNoeuds (R12 : chemin ET overlay
// suivent le curseur à chaque pointermove, un cadre rAF au plus), UNE
// commande au pointerup qui pose exactement ce qui est affiché.
import { segment_proche, segment_tirer, poignee_deplacer, noeud_supprimer_lisse, noeud_intelligent } from "./mod-noeud.js";
import { bbox_ancres, poignees_bbox, bbox_par_poignee, noeuds_tourner } from "./mod-selection.js";
import { contraindre_angle } from "./mod-plume.js";
import { chemin_parser, chemin_serialiser, chemin_ancres, op_supprimer } from "./mod-doc.js";
import { op_noeud_inserer, op_noeuds_aligner, op_noeuds_transformer } from "./mod-noeuds.js";
const SNS = "http://www.w3.org/2000/svg";

export const HINT_NOEUDS = "cliquer un nœud pour le sélectionner, Maj ajoute · glisser un nœud, une poignée (Alt casse la tangente, Maj contraint) ou un segment · double-clic sur un segment insère un nœud, sur un nœud le convertit · Suppr retire en lissant";

export function initNoeudUI(VL) {
  const { $, etat } = VL;
  const stage = $("#stage");
  if (!stage) return;
  VL.hints = Object.assign(VL.hints || {}, { noeuds: HINT_NOEUDS });
  let geste = null;
  if (etat.aimantNoeuds === undefined) etat.aimantNoeuds = true;   // R10 : magnétisme aux nœuds, réglage séparé
  const actif = () => etat.outil === "noeuds" && !!etat.doc;
  const aimante = (dx, dy) => etat.aimantNoeuds === false ? [dx, dy] : VL.aimantePt(dx, dy);
  const chemin = () => VL.pathSelectionne();

  stage.addEventListener("pointerdown", (ev) => {
    if (!actif() || ev.button !== 0) return;
    const p = chemin(); if (!p) return;
    const t = ev.target;
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
    const segs = chemin_parser(p.d);
    // 0. R10 : une poignée de TRANSFORMATION de la sélection de nœuds (≥ 2 ancres)
    const pt0 = t.closest && t.closest(".poignee-noeuds-transf");
    if (pt0 && etat.ancresSel && etat.ancresSel.length > 1) {
      const b0 = bbox_ancres(chemin_ancres(segs), etat.ancresSel);
      if (b0 && (pt0.dataset.k === "rot" || (b0.w > 0 && b0.h > 0))) {
        const cx = b0.x + b0.w / 2, cy = b0.y + b0.h / 2;
        geste = pt0.dataset.k === "rot" ? { type: "noeuds-rot", id: p.id, segs, d0: p.d, cx, cy, a0: Math.atan2(dy - cy, dx - cx) }
                                        : { type: "noeuds-echelle", id: p.id, segs, d0: p.d, k: +pt0.dataset.k, b0 };
        VL.apercuNoeuds.debut(p.id, segs);
        ev.stopPropagation(); ev.preventDefault();
        try { stage.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
        return;
      }
    }
    // 1. une poignée
    const pg = t.closest && t.closest(".poignee-noeud");
    if (pg) {
      geste = { type: "poignee", id: p.id, i: +pg.dataset.ancre, role: pg.dataset.role, segs, d0: p.d };
      etat.ancreSel = geste.i;
      VL.apercuNoeuds.debut(p.id, segs);
      ev.stopPropagation(); ev.preventDefault();
      try { stage.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
      return;
    }
    // 2. un segment du chemin sélectionné (pas une ancre : mod-tools s'en charge)
    if (t.closest && t.closest(".ancre")) return;
    const objEl = t.closest && t.closest("[data-objet]");
    if (objEl && objEl.dataset.objet === p.id) {
      const sp = segment_proche(segs, [dx, dy], 8 / etat.zoom);
      if (sp) {
        geste = { type: "segment", id: p.id, k: sp.k, t: sp.t, x0: dx, y0: dy, segs, d0: p.d };
        VL.apercuNoeuds.debut(p.id, segs);
        ev.stopPropagation(); ev.preventDefault();
        try { stage.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
      }
    }
  }, true);
  stage.addEventListener("pointermove", (ev) => {
    if (!geste) return;
    ev.stopPropagation();
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
    let segs;
    if (geste.type === "poignee") {
      const a = chemin_ancres(geste.segs)[geste.i];
      let pt = ev.altKey ? [dx, dy] : aimante(dx, dy);
      if (ev.shiftKey) pt = contraindre_angle([a.x, a.y], pt);
      segs = poignee_deplacer(geste.segs, geste.i, geste.role, pt, { mode: ev.altKey ? "libre" : "lisse" });
    } else if (geste.type === "noeuds-echelle") {
      const b1 = bbox_par_poignee(geste.b0, geste.k, aimante(dx, dy), { proportions: ev.shiftKey });
      const d2 = { calques: [{ id: "c", objets: [{ id: geste.id, type: "path", d: chemin_serialiser(geste.segs) }] }] };
      op_noeuds_transformer(d2, geste.id, etat.ancresSel.slice(), geste.b0, b1);
      segs = chemin_parser(d2.calques[0].objets[0].d); geste.b1 = b1;
    } else if (geste.type === "noeuds-rot") {
      let a = (Math.atan2(dy - geste.cy, dx - geste.cx) - geste.a0) * 180 / Math.PI;
      if (ev.shiftKey) a = Math.round(a / 15) * 15;
      segs = noeuds_tourner(geste.segs, etat.ancresSel, geste.cx, geste.cy, a); geste.angle = a;
    } else {
      segs = segment_tirer(geste.segs, geste.k, geste.t, dx - geste.x0, dy - geste.y0);
    }
    geste.d = chemin_serialiser(segs);
    VL.apercuNoeuds.poser(segs, geste.d);
  }, true);
  stage.addEventListener("pointerup", (ev) => {
    if (!geste) return;
    ev.stopPropagation();
    const g = geste; geste = null;
    const fin = VL.apercuNoeuds.fin();           // R12 : ce qui est affiché est ce qui est posé
    const d = fin && fin.d ? fin.d : g.d;
    if (d && d !== g.d0) VL.executer((doc) => { const o = doc.calques.flatMap((c) => c.objets).find((x) => x.id === g.id); if (!o) throw new Error("chemin introuvable"); o.d = d; });
    else VL.rendreOverlay();
  }, true);
  // double-clic sur un segment : un nœud à cet endroit (sur une ancre, mod-tools convertit)
  stage.addEventListener("dblclick", (ev) => {
    if (!actif()) return;
    const p = chemin(); if (!p) return;
    if (ev.target.closest && (ev.target.closest(".ancre") || ev.target.closest(".poignee-noeud"))) return;
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
    const sp = segment_proche(chemin_parser(p.d), [dx, dy], 8 / etat.zoom);
    if (!sp || sp.i < 1) return;
    ev.stopPropagation(); ev.preventDefault();
    const i = VL.executer(op_noeud_inserer, p.id, sp.i, sp.t);
    if (i !== undefined) { etat.ancreSel = i; etat.ancresSel = [i]; VL.rendreOverlay(); }
  }, true);
  // Suppr : suppression LISSE (avant mod-tools)
  const sTouche = VL.surTouche;
  VL.surTouche = (ev) => {
    if (actif() && (ev.key === "Delete" || ev.key === "Backspace") && etat.ancreSel !== null && !(etat.ancresSel && etat.ancresSel.length > 1)) {
      const p = chemin();
      if (p) {
        const segs = chemin_parser(p.d), n = chemin_ancres(segs).length;
        if (n <= 2) VL.executer(op_supprimer, [p.id]);
        else { const d = chemin_serialiser(noeud_supprimer_lisse(segs, etat.ancreSel)); VL.executer((doc) => { const o = doc.calques.flatMap((c) => c.objets).find((x) => x.id === p.id); o.d = d; }); }
        etat.ancreSel = null; etat.ancresSel = []; VL.purgerSelection(); VL.rendreOverlay(); ev.preventDefault(); return;
      }
    }
    sTouche(ev);
  };
  /* ── R10 : la boîte et les poignées d'une sélection de nœuds (≥ 2 ancres) ── */
  const sOverlay = VL.surOverlay;
  VL.surOverlay = (o) => {
    sOverlay(o);
    if (!actif() || !etat.ancresSel || etat.ancresSel.length < 2) return;
    const p = chemin(); if (!p) return;
    const b = bbox_ancres(chemin_ancres(etat.noeudsApercu || chemin_parser(p.d)), etat.ancresSel);   // R12 : depuis l'aperçu pendant le geste
    if (!b) return;
    const [ex, ey] = VL.ecranPt(b.x, b.y), be = { x: ex, y: ey, w: b.w * etat.zoom, h: b.h * etat.zoom };
    const el = (nom, attrs) => { const e = document.createElementNS(SNS, nom); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); o.appendChild(e); return e; };
    el("rect", { x: be.x - 6, y: be.y - 6, width: be.w + 12, height: be.h + 12, fill: "none", stroke: "#2b6fd6", "stroke-width": 1, "stroke-dasharray": "4 3", "pointer-events": "none" });
    const P = poignees_bbox({ x: be.x - 6, y: be.y - 6, w: be.w + 12, h: be.h + 12 });
    P.poignees.forEach(([x, y], k) => el("rect", { x: x - 4, y: y - 4, width: 8, height: 8, fill: "#fff", stroke: "#2b6fd6", class: "poignee-noeuds-transf", "data-k": k }));
    el("line", { x1: P.rotation[0], y1: P.rotation[1] + 26, x2: P.rotation[0], y2: P.rotation[1] + 6, stroke: "#2b6fd6" });
    el("circle", { cx: P.rotation[0], cy: P.rotation[1], r: 5, fill: "#fff", stroke: "#2b6fd6", class: "poignee-noeuds-transf", "data-k": "rot" });
  };
  VL.actions = VL.actions || {};
  VL.actions.noeuds = Object.assign(VL.actions.noeuds || {}, {
    aligner: (mode) => { const p = chemin(); const idx = etat.ancresSel && etat.ancresSel.length > 1 ? etat.ancresSel.slice() : null; if (!p || !idx) { VL.toast("aligner : sélectionner au moins deux nœuds (lasso ou Maj+clic)", true); return; } VL.executer(op_noeuds_aligner, p.id, idx, mode); },
    supprimerLisse: () => VL.surTouche(new KeyboardEvent("keydown", { key: "Delete" })),
    intelligent: () => { const p = chemin(); const i = etat.ancreSel !== null && etat.ancreSel !== undefined ? etat.ancreSel : (p ? chemin_ancres(chemin_parser(p.d)).length - 1 : -1); if (!p || i < 0) { VL.toast("intelligent : choisir un nœud", true); return; } const d = chemin_serialiser(noeud_intelligent(chemin_parser(p.d), i)); VL.executer((doc) => { const o = doc.calques.flatMap((c) => c.objets).find((x) => x.id === p.id); o.d = d; }); },
  });
  for (const m of ["gauche", "centreH", "droite", "haut", "centreV", "bas"]) VL.actions.noeuds["al-" + m] = () => VL.actions.noeuds.aligner(m);
  VL.noeudui = { geste: () => geste };   // la preuve
}
