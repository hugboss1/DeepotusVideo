// mod-barrecontexte.js — la barre contextuelle d'Affinity (R5) : rend le
// libellé de la sélection et les champs de l'outil courant (mod-contexte),
// applique les changements dans l'état existant puis rend ; les dialogues
// « Configuration du document… » (taille, dpi, unité, fond — UNE commande)
// et « Paramètres de l'appli… » (bulles, pas de grille, aimantation —
// dz_vl_params, relus à l'ouverture). Traduit et délègue.
import { icone_svg } from "./mod-icones.js";
import { libelle_selection, champs_de, appliquer_champ, params_lire, params_poser, params_serialiser } from "./mod-contexte.js";
import { FORMES } from "./mod-formes.js";
import { PROFILS } from "./mod-pinceauvec.js";
import { terrains_de, op_style, op_deplacer, op_redimensionner } from "./mod-doc.js";
import { UNITES } from "./mod-unites.js";

const CLE = "dz_vl_params";
export function initBarreContexte(VL) {
  const { $, etat } = VL;
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  const hSel = $("#cbSelection"), hOutil = $("#cbOutil");
  if (!hSel || !hOutil) return;
  let params = params_lire(null);
  try { params = params_lire(localStorage.getItem(CLE)); } catch (e) { /* stockage indisponible */ }

  const objetsSel = () => etat.selection.map((id) => { const t = VL.objetDe(id); return t ? t.objet : null; }).filter(Boolean);
  function vue() {
    return { selection: etat.selection, objets: objetsSel(), formeCourante: etat.formeCourante, formes: FORMES, gommeLargeur: etat.gommeLargeur, coinRayon: etat.coinRayon,
             pinceauv: etat.pinceauv, profils: PROFILS, px: etat.px, terrainCourant: etat.terrainCourant, terrains: etat.doc ? terrains_de(etat.doc) : {}, typo: etat.typo, exportPlus: etat.exportPlus, plume: etat.plume, aimantNoeuds: etat.aimantNoeuds, selectionAuto: etat.selectionAuto, bbox: etat.selection.length ? VL.bboxSelectionDoc() : null };
  }
  function rendre() {
    hSel.textContent = libelle_selection(objetsSel());
    if (!etat.doc) { hOutil.innerHTML = ""; return; }
    const champs = champs_de(etat.outil, vue());
    let prefixePrec = null;
    hOutil.innerHTML = champs.map((c) => {
      if (c.type === "bouton") {
        // 21/09 : des ICÔNES à bulle (le libellé devient le title) ; un séparateur entre deux groupes (plume:* | noeuds:*)
        const pre = String(c.id).includes(":") ? String(c.id).split(":")[0] : "";
        const sep = prefixePrec !== null && pre !== prefixePrec ? `<span class="cb-sep"></span>` : "";
        prefixePrec = pre;
        if (c.icone) return `${sep}<button class="cb-bouton cb-icone" data-champ="${c.id}" title="${esc(c.titre || c.libelle)}" aria-label="${esc(c.libelle)}">${icone_svg(c.icone, 16)}</button>`;
        return `${sep}<button class="cb-bouton" data-champ="${c.id}"${c.titre ? ` title="${esc(c.titre)}"` : ""}>${esc(c.libelle)}</button>`;
      }
      prefixePrec = null;
      if (c.type === "bascule") return `<label class="cb-champ"><input type="checkbox" data-champ="${c.id}" ${c.valeur ? "checked" : ""}/>${esc(c.libelle)}</label>`;
      if (c.type === "couleur") return `<label class="cb-champ cb-couleur"${c.titre ? ` title="${esc(c.titre)}"` : ""}><span>${esc(c.libelle)}</span><input type="color" data-champ="${c.id}" value="${c.valeur || "#000000"}"${c.valeur ? "" : ' class="vide"'}/><button type="button" class="cb-vider" data-vider="${c.id}" title="Transparent (la gomme)">∅</button></label>`;
      if (c.type === "select") return `<label class="cb-champ"><span>${esc(c.libelle)}</span><select data-champ="${c.id}">${c.options.map((o) => `<option value="${esc(o.id)}"${o.id === c.valeur ? " selected" : ""}>${esc(o.libelle)}</option>`).join("")}</select></label>`;
      return `<label class="cb-champ"><span>${esc(c.libelle)}</span><input type="number" data-champ="${c.id}" value="${c.valeur}" min="${c.min}" max="${c.max}" step="${c.pas}"/></label>`;
    }).join("");
    hOutil.querySelectorAll("[data-champ]").forEach((el) => {
      const id = el.dataset.champ;
      if (el.tagName === "BUTTON") { el.addEventListener("click", () => { if (id === "configDoc") configurerDocument(); else if (id === "parametres") parametresAppli(); else if (id.includes(":")) { const [m, a] = id.split(":"); const A = (VL.actions || {})[m]; if (A && A[a]) A[a](); } }); return; }
      el.addEventListener("change", () => appliquer(id, el.type === "checkbox" ? el.checked : el.value));
    });
    hOutil.querySelectorAll("[data-vider]").forEach((b) => b.addEventListener("click", () => { appliquer(b.dataset.vider, ""); rendre(); }));
  }
  function appliquer(id, valeur) {
    const patch = appliquer_champ(etat, id, valeur);
    if (patch.style) { if (etat.selection.length) VL.executer(op_style, etat.selection.slice(), patch.style); return; }
    if (patch.styleTexte) {   // R11 : sur le texte sélectionné, sinon les défauts des prochains textes
      const cibles = etat.selection.filter((id) => { const t = VL.objetDe(id); return t && ["texte", "cadre", "textechemin"].includes(t.objet.type); });
      if (cibles.length) VL.executer(op_style, cibles, patch.styleTexte);
      else { etat.typo = etat.typo || {}; etat.typo.styleDefaut = { ...(etat.typo.styleDefaut || {}), ...patch.styleTexte }; rendre(); }
      return;
    }
    if (patch.bbox) {   // R10 : X · Y · L · H de la barre — déplacer ou redimensionner par les commandes existantes
      const b0 = VL.bboxSelectionDoc(); if (!b0 || !etat.selection.length) return;
      const b1 = { ...b0, ...patch.bbox };
      if (patch.bbox.x !== undefined || patch.bbox.y !== undefined) VL.executer(op_deplacer, etat.selection.slice(), b1.x - b0.x, b1.y - b0.y);
      else VL.executer(op_redimensionner, etat.selection.slice(), b0, b1);
      return;
    }
    for (const [k, v] of Object.entries(patch)) {
      if (v && typeof v === "object" && etat[k] && typeof etat[k] === "object") Object.assign(etat[k], v); else etat[k] = v;
    }
    if (patch.typo && VL.surSelection) VL.surSelection();
    if (etat.doc) VL.rendre();
  }

  /* ── Configuration du document… ── */
  function dialogue(id, titre, corps, onOk) {
    let dlg = $("#" + id);
    if (!dlg) { dlg = document.createElement("div"); dlg.id = id; dlg.className = "vl-dlg"; document.body.appendChild(dlg); }
    dlg.innerHTML = `<div class="vl-dlg-boite cfg-boite"><div class="vl-dlg-tete"><b>${esc(titre)}</b><span class="spacer"></span><button data-x title="Fermer">✕</button></div><div class="cfg-corps">${corps}</div><div class="tr-pied"><button data-x>Annuler</button><button class="primaire" data-ok>OK</button></div></div>`;
    dlg.classList.remove("hidden");
    const fermer = () => dlg.classList.add("hidden");
    dlg.querySelectorAll("[data-x]").forEach((b) => b.addEventListener("click", fermer));
    dlg.querySelector("[data-ok]").addEventListener("click", () => { if (onOk(dlg) !== false) fermer(); });
    return dlg;
  }
  function configurerDocument() {
    if (!etat.doc) return;
    const d = etat.doc, u = VL.unites();
    dialogue("cfgDlg", "Configuration du document", `
      <label>Largeur (px)<input type="number" id="cfgW" min="1" max="20000" value="${+d.taille.w}"/></label>
      <label>Hauteur (px)<input type="number" id="cfgH" min="1" max="20000" value="${+d.taille.h}"/></label>
      <label>Résolution (dpi)<input type="number" id="cfgDpi" min="36" max="1200" value="${u.dpi}"/></label>
      <label>Unité d'affichage<select id="cfgUnite">${UNITES.map((x) => `<option value="${x}"${x === u.affichage ? " selected" : ""}>${x}</option>`).join("")}</select></label>
      <label>Fond de page<span class="cfg-fond"><input type="checkbox" id="cfgFondOn" ${d.fond ? "checked" : ""}/><input type="color" id="cfgFond" value="${d.fond && /^#[0-9a-f]{6}$/i.test(d.fond) ? d.fond : "#ffffff"}"/></span></label>
      <p class="px-note">Une seule commande, annulable (Ctrl+Z) ; les objets ne bougent pas.</p>`, (dlg) => {
      const w = Math.max(1, +dlg.querySelector("#cfgW").value || 1), h = Math.max(1, +dlg.querySelector("#cfgH").value || 1);
      const dpi = Math.max(36, +dlg.querySelector("#cfgDpi").value || 96), unite = dlg.querySelector("#cfgUnite").value;
      const fondOn = dlg.querySelector("#cfgFondOn").checked, fond = dlg.querySelector("#cfgFond").value;
      VL.executer((doc) => { doc.taille = { w, h }; doc.unites = { affichage: unite, dpi }; if (fondOn) doc.fond = fond; else delete doc.fond; });
      VL.zoomAjuster();
    });
  }
  /* ── Paramètres de l'appli… ── */
  function appliquerParams() {
    document.body.classList.toggle("sans-bulles", !params.bulles);
    const ba = $("#btnAimant");
    if (ba && etat.aimantObjets !== params.aimant) { etat.aimantObjets = params.aimant; ba.classList.toggle("actif", params.aimant); }
  }
  function parametresAppli() {
    dialogue("paramDlg", "Paramètres de l'appli", `
      <label><input type="checkbox" id="prBulles" ${params.bulles ? "checked" : ""}/> Bulles d'information au survol</label>
      <label>Pas de grille par défaut (px)<input type="number" id="prGrille" min="1" max="512" value="${params.grillePas}"/></label>
      <label><input type="checkbox" id="prAimant" ${params.aimant ? "checked" : ""}/> Aimantation aux objets à l'ouverture</label>
      <p class="px-note">Mémorisés dans ce navigateur (dz_vl_params).</p>`, (dlg) => {
      params = params_poser(params, "bulles", dlg.querySelector("#prBulles").checked);
      params = params_poser(params, "grillePas", +dlg.querySelector("#prGrille").value);
      params = params_poser(params, "aimant", dlg.querySelector("#prAimant").checked);
      try { localStorage.setItem(CLE, params_serialiser(params)); localStorage.setItem("dz_vl_grille_pas", String(params.grillePas)); } catch (e) { /* stockage indisponible */ }
      appliquerParams();
      const sg = $("#selGrille"); if (sg && [...sg.options].some((o) => +o.value === params.grillePas)) { sg.value = String(params.grillePas); sg.dispatchEvent(new Event("change")); }
    });
  }
  VL.configurerDocument = configurerDocument;
  VL.parametresAppli = parametresAppli;
  VL.params = () => params;   // la preuve
  appliquerParams();

  const sOutil = VL.surOutil, sSel = VL.surSelection, sRendu = VL.surRendu, sPersona = VL.surPersona;
  VL.surOutil = () => { sOutil(); rendre(); };
  VL.surSelection = () => { sSel(); rendre(); };
  VL.surRendu = () => { sRendu(); rendre(); };
  VL.surPersona = () => { sPersona(); rendre(); };
  rendre();
}
