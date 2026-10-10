// mod-planches.js — lot C : le panneau Planches (liste, ajouter depuis la
// sélection ou depuis la page, zoom sur une planche, renommer, retirer,
// PNG 2× de la planche). Les cadres se tracent dans l'overlay du cœur.
import { T } from "./mod-i18n.js";
import { op_planche_ajouter, op_planche_modifier, op_planche_supprimer,
         planche_de } from "./mod-doc.js";
import { versUnite, suffixe } from "./mod-unites.js";
import { dzi } from "./mod-icones.js";

const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* ── pur ── */
export function plancheLigne(p, unites) {
  const u = (v) => Math.round(versUnite(v, unites) * 10) / 10;
  return `<div class="planche-ligne" data-planche="${esc(p.id)}">`
    + `<span class="nom" title="${esc(p.nom)}">${esc(p.nom)}</span>`
    + `<small>${u(p.w)} × ${u(p.h)} ${esc(suffixe(unites.affichage))}</small>`
    + `<button data-pl-zoom="${esc(p.id)}" title="${T("vectorlab.planches.cadrer")}" aria-label="${T("vectorlab.planches.cadrer")}">${dzi("dz-action-ajuster-vue", 16)}</button>`
    + `<button data-pl-png="${esc(p.id)}" title="${T("vectorlab.planches.png")}">2×</button>`
    + `<button data-pl-renommer="${esc(p.id)}" title="${T("vectorlab.planches.renommer")}" aria-label="${T("vectorlab.planches.renommer")}">${dzi("dz-action-renommer", 16)}</button>`
    + `<button data-pl-supprimer="${esc(p.id)}" title="${T("vectorlab.planches.retirer_titre")}" aria-label="${T("vectorlab.planches.retirer")}">${dzi("dz-action-supprimer", 16)}</button>`
    + `</div>`;
}

/* ── DOM ── */
export function initPlanches(VL) {
  const { $, etat } = VL;
  const hote = $("#panneauPlanches");

  function rendre() {
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const ps = etat.doc.planches || [];
    hote.innerHTML = (ps.length ? ps.map((p) => plancheLigne(p, VL.unites())).join("")
      : `<p class="vl-amorce">${T("vectorlab.planches.aucune")}</p>`)
      + `<div class="ap-ligne"><button id="plaSel" ${etat.selection.length ? "" : "disabled"}
           title="${T("vectorlab.planches.sel_titre")}">${dzi("dz-action-ajouter", 16)}${T("vectorlab.planches.selection")}</button>
         <button id="plaPage" title="${T("vectorlab.planches.page_titre")}">${dzi("dz-action-ajouter", 16)}page</button></div>`;
    $("#plaSel").addEventListener("click", () => {
      const b = VL.bboxSelectionDoc();
      if (!b) return;
      const id = VL.executer(op_planche_ajouter, { nom: "", x: Math.round(b.x), y: Math.round(b.y),
                                                    w: Math.round(b.w), h: Math.round(b.h) });
      if (id) VL.toast(T("vectorlab.planches.creee", { id }));
    });
    $("#plaPage").addEventListener("click", () => {
      const der = ps[ps.length - 1];
      const x = der ? der.x + der.w + 40 : 0;
      VL.executer(op_planche_ajouter, { nom: "", x, y: 0, w: etat.doc.taille.w, h: etat.doc.taille.h });
    });
    hote.querySelectorAll("[data-pl-zoom]").forEach((b) =>
      b.addEventListener("click", () => zoomSur(b.dataset.plZoom)));
    hote.querySelectorAll("[data-pl-png]").forEach((b) => b.addEventListener("click", () => {
      const p = planche_de(etat.doc, b.dataset.plPng);
      VL.exporterPNG(2, { cadre: p, suffixe: "_" + p.id })
        .then((f) => VL.toast(T("vectorlab.planches.depose", { f, nom: p.nom })))
        .catch((e) => VL.toast(e.message, true));
    }));
    hote.querySelectorAll("[data-pl-renommer]").forEach((b) => b.addEventListener("click", async () => {
      const p = planche_de(etat.doc, b.dataset.plRenommer);
      const nom = await VL.dialogue.saisir(T("vectorlab.planches.nom"), { valeur: p.nom, titre: T("vectorlab.planches.renommer_titre"), valider: T("vectorlab.planches.renommer") });
      if (nom !== null) VL.executer(op_planche_modifier, p.id, { nom });
    }));
    hote.querySelectorAll("[data-pl-supprimer]").forEach((b) =>
      b.addEventListener("click", () => VL.executer(op_planche_supprimer, b.dataset.plSupprimer)));
  }
  function zoomSur(id) {
    const p = planche_de(etat.doc, id);
    if (!p) return;
    const r = $("#stage").getBoundingClientRect();
    etat.zoom = Math.max(0.05, Math.min(16, Math.min((r.width - 80) / p.w, (r.height - 80) / p.h)));
    etat.tx = (r.width - p.w * etat.zoom) / 2 - p.x * etat.zoom;
    etat.ty = (r.height - p.h * etat.zoom) / 2 - p.y * etat.zoom;
    VL.appliquerVue();
  }
  const suivant = VL.surRendu;
  VL.surRendu = () => { suivant(); rendre(); };
  const suivantSel = VL.surSelection;
  VL.surSelection = () => { suivantSel(); rendre(); };
  VL.zoomPlanche = zoomSur;
}
