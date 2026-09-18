// mod-noeudui.js — l'outil Nœud de classe Affinity (R9), en complément de
// mod-tools (ancres) et mod-outils2 (lasso d'ancres) : les POIGNÉES se
// tirent (lisse : l'opposée s'aligne ; Alt : libre ; Maj : angle
// contraint), un SEGMENT du chemin sélectionné se déforme au glisser
// (une droite devient courbe), le double-clic sur un segment insère un
// nœud à cet endroit, Suppr fait une suppression LISSE, la barre
// contextuelle porte conversions / actions / alignements. Écouteurs en
// CAPTURE sur #stage, aperçu par patch du clone, UNE commande au pointerup.
import { segment_proche, segment_tirer, poignee_deplacer, noeud_supprimer_lisse } from "./mod-noeud.js";
import { contraindre_angle } from "./mod-plume.js";
import { chemin_parser, chemin_serialiser, chemin_ancres, op_supprimer } from "./mod-doc.js";
import { op_noeud_inserer, op_noeuds_aligner } from "./mod-noeuds.js";

export const HINT_NOEUDS = "cliquer un nœud pour le sélectionner, Maj ajoute · glisser un nœud, une poignée (Alt casse la tangente, Maj contraint) ou un segment · double-clic sur un segment insère un nœud, sur un nœud le convertit · Suppr retire en lissant";

export function initNoeudUI(VL) {
  const { $, etat } = VL;
  const stage = $("#stage");
  if (!stage) return;
  VL.hints = Object.assign(VL.hints || {}, { noeuds: HINT_NOEUDS });
  let geste = null;
  const actif = () => etat.outil === "noeuds" && !!etat.doc;
  const chemin = () => VL.pathSelectionne();
  const poserD = (id, d) => { const el = document.querySelector(`#canvasHost [data-objet="${id}"]`); if (el) { const p = el.tagName === "path" ? el : el.querySelector("path"); if (p) p.setAttribute("d", d); } };

  stage.addEventListener("pointerdown", (ev) => {
    if (!actif() || ev.button !== 0) return;
    const p = chemin(); if (!p) return;
    const t = ev.target;
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
    const segs = chemin_parser(p.d);
    // 1. une poignée
    const pg = t.closest && t.closest(".poignee-noeud");
    if (pg) {
      geste = { type: "poignee", id: p.id, i: +pg.dataset.ancre, role: pg.dataset.role, segs, d0: p.d };
      etat.ancreSel = geste.i;
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
      let pt = ev.altKey ? [dx, dy] : VL.aimantePt(dx, dy);
      if (ev.shiftKey) pt = contraindre_angle([a.x, a.y], pt);
      segs = poignee_deplacer(geste.segs, geste.i, geste.role, pt, { mode: ev.altKey ? "libre" : "lisse" });
    } else {
      segs = segment_tirer(geste.segs, geste.k, geste.t, dx - geste.x0, dy - geste.y0);
    }
    geste.d = chemin_serialiser(segs);
    poserD(geste.id, geste.d);
  }, true);
  stage.addEventListener("pointerup", (ev) => {
    if (!geste) return;
    ev.stopPropagation();
    const g = geste; geste = null;
    if (g.d && g.d !== g.d0) VL.executer((doc) => { const o = doc.calques.flatMap((c) => c.objets).find((x) => x.id === g.id); if (!o) throw new Error("chemin introuvable"); o.d = g.d; });
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
  VL.actions = VL.actions || {};
  VL.actions.noeuds = Object.assign(VL.actions.noeuds || {}, {
    aligner: (mode) => { const p = chemin(); const idx = etat.ancresSel && etat.ancresSel.length > 1 ? etat.ancresSel.slice() : null; if (!p || !idx) { VL.toast("aligner : sélectionner au moins deux nœuds (lasso ou Maj+clic)", true); return; } VL.executer(op_noeuds_aligner, p.id, idx, mode); },
    supprimerLisse: () => VL.surTouche(new KeyboardEvent("keydown", { key: "Delete" })),
  });
  for (const m of ["gauche", "centreH", "droite", "haut", "centreV", "bas"]) VL.actions.noeuds["al-" + m] = () => VL.actions.noeuds.aligner(m);
  VL.noeudui = { geste: () => geste };   // la preuve
}
