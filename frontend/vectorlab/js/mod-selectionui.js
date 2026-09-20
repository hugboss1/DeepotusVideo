// mod-selectionui.js — l'outil Sélection de classe Affinity (R10), en
// complément de mod-tools : Alt+glisser déplace une COPIE (la sélection
// est dupliquée puis la copie suit le curseur, une commande de
// déplacement au relâcher), le double-clic sur une courbe passe à l'outil
// Nœuds, le survol dessine la boîte de l'objet sous le curseur. Écouteurs
// en CAPTURE sur #stage ; les modificateurs Maj (déplacement contraint) et
// Ctrl (redimensionner depuis le centre) et le cadre inclus / touchés
// vivent dans mod-tools (retouches R10).
import { contraindre_axe } from "./mod-selection.js";
import { op_deplacer } from "./mod-doc.js";

const SNS = "http://www.w3.org/2000/svg";
export function initSelectionUI(VL) {
  const { $, etat } = VL;
  const stage = $("#stage");
  if (!stage) return;
  let geste = null;
  const actif = () => etat.outil === "select" && !!etat.doc;

  /* ── Alt + glisser : déplacer une copie ── */
  stage.addEventListener("pointerdown", (ev) => {
    if (!actif() || ev.button !== 0 || !ev.altKey) return;
    const cible = ev.target.closest && ev.target.closest("[data-objet]");
    if (!cible) return;
    const id = VL.sommetDe(cible.dataset.objet) || cible.dataset.objet;
    if (!etat.selection.includes(id)) VL.setSelection([id]);
    const ids = etat.selection.slice();
    const b0 = VL.bboxSelectionDoc();
    VL.dupliquerSelection();                     // les copies sont sélectionnées (op_dupliquer les décale : on compense)
    const copies = etat.selection.slice();
    if (!copies.length || copies.join() === ids.join()) return;
    const b1 = VL.bboxSelectionDoc();
    const offX = b1 && b0 ? b1.x - b0.x : 0, offY = b1 && b0 ? b1.y - b0.y : 0;
    ev.stopImmediatePropagation(); ev.preventDefault();
    try { stage.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
    geste = { type: "copie", x0: dx, y0: dy, dxA: -offX, dyA: -offY, offX, offY, els: VL.selectionElems().map((el) => [el, el.getAttribute("transform") || ""]) };
    for (const [el, orig] of geste.els) el.setAttribute("transform", `translate(${-offX} ${-offY})` + (orig ? " " + orig : ""));
  }, true);
  stage.addEventListener("pointermove", (ev) => {
    if (geste) {
      ev.stopImmediatePropagation();
      const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
      let [mx, my] = [dx - geste.x0, dy - geste.y0];
      if (ev.shiftKey) [mx, my] = contraindre_axe(mx, my);
      const [ax, ay] = VL.aimantePt(geste.x0 + mx, geste.y0 + my);
      geste.dxA = ax - geste.x0 - geste.offX; geste.dyA = ay - geste.y0 - geste.offY;
      for (const [el, orig] of geste.els) el.setAttribute("transform", `translate(${geste.dxA} ${geste.dyA})` + (orig ? " " + orig : ""));
      VL.rendreOverlay();
      return;
    }
    if (!actif()) { cacherSurvol(); return; }
    survoler(ev);
  }, true);
  stage.addEventListener("pointerup", (ev) => {
    if (!geste) return;
    ev.stopImmediatePropagation();
    const g = geste; geste = null;
    if (g.dxA || g.dyA) VL.executer(op_deplacer, etat.selection.slice(), g.dxA, g.dyA); else VL.rendre();   // la copie part de la place de l'original
  }, true);

  /* ── double-clic sur une courbe → outil Nœuds ── */
  stage.addEventListener("dblclick", (ev) => {
    if (!actif()) return;
    const cible = ev.target.closest && ev.target.closest("[data-objet]");
    if (!cible) return;
    const t = VL.objetDe(cible.dataset.objet);
    if (!t || !["path", "forme"].includes(t.objet.type) || t.calque.verrou) return;
    ev.stopImmediatePropagation(); ev.preventDefault();   // mesuré : les autres écouteurs de capture de #stage (Nœuds) verraient sinon ce double-clic et inséreraient un nœud
    VL.setSelection([t.objet.id]);
    VL.setOutil("noeuds");
  }, true);

  /* ── survol : la boîte de l'objet sous le curseur ── */
  function couche() {
    const o = $("#overlay"); if (!o) return null;
    let g = o.querySelector("#ovSurvol");
    if (!g) { g = document.createElementNS(SNS, "g"); g.id = "ovSurvol"; g.setAttribute("pointer-events", "none"); o.appendChild(g); }
    return g;
  }
  let survole = null;
  function cacherSurvol() { const g = $("#ovSurvol"); if (g) g.innerHTML = ""; survole = null; }
  function survoler(ev) {
    const cible = ev.target.closest && ev.target.closest("#canvasHost [data-objet]");
    const id = cible ? (VL.sommetDe(cible.dataset.objet) || cible.dataset.objet) : null;
    if (!id || etat.selection.includes(id)) { cacherSurvol(); return; }
    if (id === survole) return;
    survole = id;
    const g = couche(); if (!g) return; g.innerHTML = "";
    const el = document.querySelector(`#canvasHost [data-objet="${id}"]`); if (!el) return;
    const r = el.getBoundingClientRect(), r0 = stage.getBoundingClientRect();
    const rect = document.createElementNS(SNS, "rect");
    for (const [k, v] of Object.entries({ x: r.left - r0.left, y: r.top - r0.top, width: r.width, height: r.height, fill: "none", stroke: "#4a90e2", "stroke-width": 1, opacity: .8 })) rect.setAttribute(k, v);
    g.appendChild(rect);
  }
  stage.addEventListener("pointerleave", cacherSurvol);
  const sOutil = VL.surOutil, sSel = VL.surSelection;
  VL.surOutil = () => { sOutil(); cacherSurvol(); };
  VL.surSelection = () => { sSel(); cacherSurvol(); };
  VL.selectionui = { geste: () => geste, survole: () => survole };   // la preuve
}
