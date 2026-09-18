// mod-texteui.js — l'outil Texte de classe Affinity (R11), en complément
// de mod-typo (édition en place) : clic = texte artistique au corps
// courant, glisser = texte artistique dont le CORPS est la hauteur du
// glisser, clic sur une courbe ou une forme = texte sur ce chemin ;
// indicateur rouge d'un cadre qui déborde ; Tab / Maj+Tab cyclent la
// sélection (outil Sélection). Écouteurs en CAPTURE sur #stage.
import { corps_de_glisser, cycle_suivant } from "./mod-texte.js";
import { op_ajouter, op_texte_sur_chemin } from "./mod-doc.js";

const SNS = "http://www.w3.org/2000/svg";
export const HINT_TEXTE = "cliquer pour poser un texte au corps courant · glisser pour poser un texte au corps de la hauteur tirée · cliquer sur une courbe pour écrire le long de cette courbe · Échap finit";

export function initTexteUI(VL) {
  const { $, etat } = VL;
  const stage = $("#stage");
  if (!stage) return;
  VL.hints = Object.assign(VL.hints || {}, { texte: HINT_TEXTE });
  let geste = null;
  const actif = () => etat.outil === "texte" && !!etat.doc;
  const styleDefaut = () => Object.assign({ corps: 48 }, (etat.typo && etat.typo.styleDefaut) || {});

  stage.addEventListener("pointerdown", (ev) => {
    if (!actif() || ev.button !== 0) return;
    const ed = $(".tx-editeur");
    if (ed) { ed.blur(); }                                // un texte en cours d'édition : le blur le finit (mod-typo), puis on continue
    const cible = ev.target.closest && ev.target.closest("#canvasHost [data-objet]");
    const t = cible && VL.objetDe(cible.dataset.objet);
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
    // clic sur une courbe / une forme : un texte sur ce chemin
    if (t && ["path", "forme"].includes(t.objet.type) && !t.calque.verrou) {
      ev.stopImmediatePropagation(); ev.preventDefault();
      const s = styleDefaut();
      const idT = VL.executer((doc) => {
        const id = op_ajouter(doc, etat.calqueActif, { type: "texte", x: dx, y: dy, contenu: "Texte", style: { fond: etat.styleCourant.contour || "#1F1512", police: s.police || (etat.typo && (etat.typo.polices.find((p) => p.id === etat.typo.courante) || {}).famille) || "Segoe UI", corps: s.corps, ...s } });
        op_texte_sur_chemin(doc, id, t.objet.id);
        return id;
      });
      if (idT) { VL.setOutil("select"); VL.setSelection([idT]); if (VL.editerTexte) VL.editerTexte(idT); }
      return;
    }
    if (t && ["texte", "cadre", "textechemin"].includes(t.objet.type)) return;   // rééditer : mod-tools / mod-typo
    ev.stopImmediatePropagation(); ev.preventDefault();
    try { stage.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
    const [ax, ay] = VL.aimantePt(dx, dy);
    geste = { x0: ax, y0: ay, x1: ax, y1: ay };
  }, true);
  stage.addEventListener("pointermove", (ev) => {
    if (!geste) return;
    ev.stopImmediatePropagation();
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
    geste.x1 = dx; geste.y1 = dy;
    const tmp = $("#ovTmp"); if (!tmp) return; tmp.innerHTML = "";
    const corps = corps_de_glisser(geste.x0, geste.y0, geste.x1, geste.y1, styleDefaut().corps);
    const [ex, ey] = VL.ecranPt(geste.x0, Math.min(geste.y0, geste.y1));
    const r = document.createElementNS(SNS, "rect");
    for (const [k, v] of Object.entries({ x: ex, y: ey, width: Math.max(2, Math.abs(geste.x1 - geste.x0)) * etat.zoom, height: corps * etat.zoom, fill: "none", stroke: "#4a90e2", "stroke-dasharray": "4 3" })) r.setAttribute(k, v);
    tmp.appendChild(r);
    const l = document.createElementNS(SNS, "text");
    l.setAttribute("x", ex + 4); l.setAttribute("y", ey - 4); l.setAttribute("fill", "#4a90e2"); l.setAttribute("font-size", "11"); l.textContent = `${corps} px`;
    tmp.appendChild(l);
  }, true);
  stage.addEventListener("pointerup", (ev) => {
    if (!geste) return;
    ev.stopImmediatePropagation();
    const g = geste; geste = null;
    const tmp = $("#ovTmp"); if (tmp) tmp.innerHTML = "";
    const corps = corps_de_glisser(g.x0, g.y0, g.x1, g.y1, styleDefaut().corps);
    const y = Math.hypot(g.x1 - g.x0, g.y1 - g.y0) < 6 ? g.y0 : Math.max(g.y0, g.y1);   // la ligne de base au bas du glisser
    if (VL.poserTexte) VL.poserTexte(g.x0, y, corps);
  }, true);

  /* ── un cadre qui déborde : carré rouge au coin bas-droit (Affinity) ── */
  const sOverlay = VL.surOverlay;
  VL.surOverlay = (o) => {
    sOverlay(o);
    if (!etat.doc || etat.selection.length !== 1) return;
    const el = document.querySelector(`#canvasHost [data-objet="${etat.selection[0]}"][data-deborde]`);
    const t = VL.objetDe(etat.selection[0]);
    if (!el || !t || t.objet.type !== "cadre") return;
    const [ex, ey] = VL.ecranPt(t.objet.x + t.objet.w, t.objet.y + t.objet.h);
    const r = document.createElementNS(SNS, "rect");
    for (const [k, v] of Object.entries({ x: ex - 5, y: ey - 5, width: 10, height: 10, fill: "#e33", stroke: "#fff", class: "cadre-deborde", "pointer-events": "none" })) r.setAttribute(k, v);
    const titre = document.createElementNS(SNS, "title"); titre.textContent = "Le texte déborde du cadre"; r.appendChild(titre);
    o.appendChild(r);
  };

  /* ── Tab / Maj+Tab : l'objet sélectionnable suivant / précédent (outil Sélection) ── */
  const sTouche = VL.surTouche;
  VL.surTouche = (ev) => {
    if (ev.key === "Tab" && etat.outil === "select" && etat.doc && !$(".tx-editeur")) {
      const ids = etat.doc.calques.filter((c) => c.visible && !c.verrou).flatMap((c) => c.objets.map((o) => o.id));
      const suivant = cycle_suivant(ids, etat.selection.length === 1 ? etat.selection[0] : null, ev.shiftKey ? -1 : 1);
      if (suivant) VL.setSelection([suivant]);
      ev.preventDefault(); return;
    }
    sTouche(ev);
  };
  VL.texteui = { geste: () => geste };   // la preuve
}
