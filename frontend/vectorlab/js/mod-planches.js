// mod-planches.js — lot C : le panneau Planches (liste, ajouter depuis la
// sélection ou depuis la page, zoom sur une planche, renommer, retirer,
// PNG 2× de la planche). Les cadres se tracent dans l'overlay du cœur.
import { op_planche_ajouter, op_planche_modifier, op_planche_supprimer,
         planche_de } from "./mod-doc.js";
import { versUnite, suffixe } from "./mod-unites.js";

const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* ── pur ── */
export function plancheLigne(p, unites) {
  const u = (v) => Math.round(versUnite(v, unites) * 10) / 10;
  return `<div class="planche-ligne" data-planche="${esc(p.id)}">`
    + `<span class="nom" title="${esc(p.nom)}">${esc(p.nom)}</span>`
    + `<small>${u(p.w)} × ${u(p.h)} ${esc(suffixe(unites.affichage))}</small>`
    + `<button data-pl-zoom="${esc(p.id)}" title="Cadrer la vue sur la planche">⌕</button>`
    + `<button data-pl-png="${esc(p.id)}" title="PNG 2× de la planche → Library">2×</button>`
    + `<button data-pl-renommer="${esc(p.id)}" title="Renommer">✎</button>`
    + `<button data-pl-supprimer="${esc(p.id)}" title="Retirer la planche (les objets restent)">✕</button>`
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
      : `<p class="vl-amorce">Aucune planche — la page entière est la seule surface.</p>`)
      + `<div class="ap-ligne"><button id="plaSel" ${etat.selection.length ? "" : "disabled"}
           title="Une planche au cadre de la sélection">＋ sélection</button>
         <button id="plaPage" title="Une planche de la taille de la page, à droite de la dernière">＋ page</button></div>`;
    $("#plaSel").addEventListener("click", () => {
      const b = VL.bboxSelectionDoc();
      if (!b) return;
      const id = VL.executer(op_planche_ajouter, { nom: "", x: Math.round(b.x), y: Math.round(b.y),
                                                    w: Math.round(b.w), h: Math.round(b.h) });
      if (id) VL.toast(`planche ${id} créée`);
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
        .then((f) => VL.toast(`${f} déposé (planche ${p.nom})`))
        .catch((e) => VL.toast(e.message, true));
    }));
    hote.querySelectorAll("[data-pl-renommer]").forEach((b) => b.addEventListener("click", async () => {
      const p = planche_de(etat.doc, b.dataset.plRenommer);
      const nom = await VL.dialogue.saisir("Nom de la planche :", { valeur: p.nom, titre: "Renommer la planche", valider: "Renommer" });
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
