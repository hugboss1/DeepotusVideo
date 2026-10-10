// mod-style.js — le panneau Apparence (T2.5) : fond (couleur / aucun /
// dégradé linéaire ou radial), contour (couleur, épaisseur, pointillés,
// joint), opacité, ordre z, grouper/dégrouper, stops du dégradé. Chaque
// interaction = UNE commande via VL.executer ; le panneau reflète le
// premier objet sélectionné, sinon le style courant des nouveaux objets.
import { T } from "./mod-i18n.js";
import { op_style, op_ordre, op_grouper, op_degrouper, op_degrade_creer,
         op_degrade_modifier, op_degrade_stop_ajouter,
         op_degrade_stop_modifier, op_degrade_stop_supprimer,
         op_deplacer, op_redimensionner, op_aligner, op_distribuer,
         op_miroir, op_rect_rayon, op_incliner, op_dupliquer_puissance,
         selection_par_attribut, formule }
  from "./mod-doc.js";
import { op_booleen, op_division, op_contour } from "./mod-bool.js";
import { POLICES } from "./mod-texte3d.js";
import { dzi } from "./mod-icones.js";

const POINTILLES = [["", T("vectorlab.style.trait_plein")], ["6 4", T("vectorlab.style.trait_tirets")], ["2 3", T("vectorlab.style.trait_points")]];
const JOINTS = ["round", "miter", "bevel"];

export function initStyle(VL) {
  const { $, etat } = VL;
  const hote = $("#panneauStyle");

  function objetReflete() {
    if (!etat.selection.length) return null;
    const t = VL.objetDe(etat.selection[0]);
    return t ? t.objet : null;
  }
  function styleReflete() {
    const o = objetReflete();
    return o ? (o.style || {}) : etat.styleCourant;
  }

  function appliquer(patch) {
    for (const [k, v] of Object.entries(patch)) {
      if (v === null) delete etat.styleCourant[k];
      else etat.styleCourant[k] = v;
    }
    if (etat.selection.length) {
      VL.executer(op_style, etat.selection.slice(), patch);
    } else rendrePanneau();
  }

  function degradeDefaut(type) {
    if (etat.selection.length !== 1) {
      VL.toast(T("vectorlab.style.degrade_un"), true);
      return;
    }
    const b = VL.bboxSelectionDoc();
    const sel = etat.selection.slice();
    const base = typeof styleReflete().fond === "string"
      && !styleReflete().fond.startsWith("grad:")
      && styleReflete().fond !== "none"
      ? styleReflete().fond : "#0047AB";
    const spec = type === "lineaire"
      ? { type, x1: b.x, y1: b.y + b.h / 2, x2: b.x + b.w,
          y2: b.y + b.h / 2,
          stops: [{ t: 0, couleur: base }, { t: 1, couleur: "#FFFFFF" }] }
      : { type, cx: b.x + b.w / 2, cy: b.y + b.h / 2,
          r: Math.max(b.w, b.h) / 2,
          stops: [{ t: 0, couleur: "#FFFFFF" }, { t: 1, couleur: base }] };
    VL.executer((doc) => {          // une seule entrée d'historique
      const id = op_degrade_creer(doc, spec);
      op_style(doc, sel, { fond: "grad:" + id });
    });
  }

  function fondDegradeId() {
    const f = styleReflete().fond;
    return (typeof f === "string" && f.startsWith("grad:")) ? f.slice(5) : null;
  }

  /* la bbox DOCUMENT d'un objet, mesurée au DOM (contour compris) — les
     ops d'alignement restent pures, c'est l'écran qui mesure (E8) */
  const bboxDocDe = (id) => VL.bboxDocDe(id);   // mesurée par le cœur (lot C)
  function pairesSelection() {
    return etat.selection
      .map((id) => ({ id, bbox: bboxDocDe(id) }))
      .filter((p) => p.bbox);
  }
  function reunion(paires) {
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const { bbox: b } of paires) {
      x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y);
      x1 = Math.max(x1, b.x + b.w); y1 = Math.max(y1, b.y + b.h);
    }
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
  }

  function rendrePanneau() {
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const s = styleReflete();
    const fondCouleur = (typeof s.fond === "string" && s.fond.startsWith("#"))
      ? s.fond : "#9DB4D6";
    const gid = fondDegradeId();
    const g = gid && etat.doc.degrades ? etat.doc.degrades[gid] : null;
    const sel = etat.selection.length;
    const b = sel ? VL.bboxSelectionDoc() : null;
    const nv = (px) => Math.round(VL.versUnite(px) * 100) / 100;
    const suf = VL.unites().affichage;
    hote.innerHTML = `
      ${b ? `
      <div class="ap-ligne"><span>X · Y</span>
        <input type="text" id="apX" value="${nv(b.x)}"
               title="${T("vectorlab.style.x_titre", { suf })}"/>
        <input type="text" id="apY" value="${nv(b.y)}"
               title="${T("vectorlab.style.y_titre", { suf })}"/>
      </div>
      <div class="ap-ligne"><span>${T("vectorlab.style.l_h")}</span>
        <input type="text" id="apW" value="${nv(b.w)}"
               title="${T("vectorlab.style.largeur_titre", { suf })}"/>
        <input type="text" id="apH" value="${nv(b.h)}"
               title="${T("vectorlab.style.hauteur_titre", { suf })}"/>
      </div>
` : ""}`;
    hote.innerHTML += `
      <div class="ap-ligne"><span>${T("vectorlab.style.fond")}</span>
        <button class="nu-pastille" id="apFond" style="background:${fondCouleur}"
                data-hex="${fondCouleur}"
                title="${T("vectorlab.style.fond_titre")}"></button>
        <button id="apFondAucun" class="${s.fond === "none" ? "actif" : ""}"
                title="${T("vectorlab.style.sans_fond")}" aria-label="${T("vectorlab.style.sans_fond")}">${dzi("dz-edit-sans-couleur", 16)}</button>
        <button id="apGradL" title="${T("vectorlab.style.grad_l_titre")}" aria-label="${T("vectorlab.style.grad_l")}">${dzi("dz-edit-degrade-lineaire", 16)}</button>
        <button id="apGradR" title="${T("vectorlab.style.grad_r_titre")}" aria-label="${T("vectorlab.style.grad_r")}">${dzi("dz-edit-degrade-radial", 16)}</button>
      </div>
      <div class="ap-ligne"><span>${T("vectorlab.style.contour")}</span>
        <button class="nu-pastille" id="apContour"
                style="background:${s.contour && s.contour !== "none" ? s.contour : "#1F1512"}"
                data-hex="${s.contour && s.contour !== "none" ? s.contour : "#1F1512"}"
                title="${T("vectorlab.style.contour_titre")}"></button>
        <button id="apContourAucun"
                class="${!s.contour || s.contour === "none" ? "actif" : ""}"
                title="${T("vectorlab.style.sans_contour")}" aria-label="${T("vectorlab.style.sans_contour")}">${dzi("dz-edit-sans-contour", 16)}</button>
        <input type="number" id="apEpaisseur" min="0.5" max="200" step="0.5"
               value="${s.epaisseur ?? 2}" title="${T("vectorlab.style.epaisseur")}"/>
      </div>
      <div class="ap-ligne"><span>${T("vectorlab.style.trait")}</span>
        <select id="apPointilles" title="${T("vectorlab.style.pointilles")}">${POINTILLES.map(
          ([v, l]) => `<option value="${v}"${(s.pointilles || "") === v
            ? " selected" : ""}>${l}</option>`).join("")}</select>
        <select id="apJoint" title="${T("vectorlab.style.joint")}">${JOINTS.map(
          (j) => `<option${(s.joint || "round") === j ? " selected" : ""}>${j}
          </option>`).join("")}</select>
      </div>
      <div class="ap-ligne"><span>${T("vectorlab.style.opacite")}</span>
        <vl-curseur id="apOpacite" min="0" max="100" step="1"
               value="${Math.round((s.opacite ?? 1) * 100)}"></vl-curseur>
      </div>
      <div class="ap-ligne"><span>${T("vectorlab.style.incliner")}</span>
        <input type="number" id="apKx" step="1" value="0" title="${T("vectorlab.style.kx_titre")}"/>
        <input type="number" id="apKy" step="1" value="0" title="${T("vectorlab.style.ky_titre")}"/>
        <button id="apIncliner" ${sel ? "" : "disabled"} title="${T("vectorlab.style.incliner_titre")}" aria-label="${T("vectorlab.style.incliner_sel")}">${dzi("dz-edit-incliner", 16)}</button>
        <button id="apPivotRaz" title="${T("vectorlab.style.pivot_raz")}" aria-label="${T("vectorlab.style.pivot_raz")}">${dzi("dz-edit-pivot", 16)}</button>
      </div>
      <div class="ap-ligne"><span>${T("vectorlab.style.puissance")}</span>
        <input type="number" id="apPn" min="1" max="200" value="3" title="${T("vectorlab.style.p_n")}"/>
        <input type="number" id="apPdx" step="any" value="20" title="${T("vectorlab.style.p_dx")}"/>
        <input type="number" id="apPdy" step="any" value="0" title="${T("vectorlab.style.p_dy")}"/>
      </div>
      <div class="ap-ligne"><span></span>
        <input type="number" id="apProt" step="1" value="0" title="${T("vectorlab.style.p_rot")}"/>
        <input type="number" id="apPech" step="0.05" min="0.05" value="1" title="${T("vectorlab.style.p_ech")}"/>
        <button id="apPuissance" ${sel ? "" : "disabled"} title="${T("vectorlab.style.puissance_titre")}" aria-label="${T("vectorlab.style.puissance_btn")}">${dzi("dz-action-dupliquer", 16)}</button>
      </div>
      <div class="ap-ligne"><span>${T("vectorlab.style.attribut")}</span>
        ${[["fond", T("vectorlab.style.attr_fond")], ["contour", T("vectorlab.style.attr_contour")], ["type", T("vectorlab.style.attr_type")]].map(([k, lib]) => `<button data-attr="${k}" ${sel === 1 ? "" : "disabled"} title="${T("vectorlab.style.attr_titre", { k: lib })}">${lib}</button>`).join("")}
      </div>
      <div class="ap-ligne"><span>${T("vectorlab.style.decaler")}</span>
        <input type="number" id="apDecal" step="any" value="5" title="${T("vectorlab.style.decal_titre")}"/>
        <button id="apDecaler" ${sel ? "" : "disabled"} title="${T("vectorlab.style.decaler_titre")}">${T("vectorlab.style.decaler_btn")}</button>
      </div>
      ${objetReflete() && objetReflete().type === "rect" ? `
      <div class="ap-ligne"><span>${T("vectorlab.style.rayon")}</span>
        <input type="number" id="apRayon" min="0" step="1"
               value="${objetReflete().rx || 0}"
               title="${T("vectorlab.style.rayon_titre")}"/>
      </div>` : ""}
      ${/* Texte & logo : fonte, corps, graisse, interlettrage et contours vivent dans le panneau Texte */ ""}
      ${g ? `<div class="ap-stops" title="${T("vectorlab.style.stops_titre")}">
        ${g.stops.map((st, i) => `<div class="ap-stop">
          <button class="nu-pastille" data-stop="${i}"
                  style="background:${st.couleur}" data-hex="${st.couleur}"
                  title="${T("vectorlab.style.stop_titre")}"></button>
          <input type="number" data-stopt="${i}" min="0" max="100"
                 value="${Math.round(st.t * 100)}"/>%
          <button data-stopx="${i}" title="${T("vectorlab.style.stop_x")}" aria-label="${T("vectorlab.style.stop_x")}">${dzi("dz-action-supprimer", 16)}</button>
        </div>`).join("")}
        <button id="apStopPlus" title="${T("vectorlab.style.stop_plus")}">${dzi("dz-action-ajouter", 16)}${T("vectorlab.style.stop")}</button>
      </div>` : ""}`;

    if (b) {
      const majPos = (patch) => {
        const b0 = VL.bboxSelectionDoc();
        if (!b0) return;
        const sel2 = etat.selection.slice();
        if ("x" in patch || "y" in patch) {
          const dx = "x" in patch ? VL.depuisUnite(patch.x) - b0.x : 0;
          const dy = "y" in patch ? VL.depuisUnite(patch.y) - b0.y : 0;
          if (dx || dy) VL.executer(op_deplacer, sel2, dx, dy);
        } else {
          const b1 = { ...b0 };
          if ("w" in patch) b1.w = Math.max(1, VL.depuisUnite(patch.w));
          if ("h" in patch) b1.h = Math.max(1, VL.depuisUnite(patch.h));
          if (b1.w !== b0.w || b1.h !== b0.h) {
            VL.executer(op_redimensionner, sel2, b0, b1);
          }
        }
      };
      // lot B : les champs acceptent des FORMULES (« +50% », « *2 », « 10+5 »)
      const lireF = (cle, texte) => {
        const b0 = VL.bboxSelectionDoc();
        return formule(nv(b0[cle]), texte);
      };
      for (const [id, cle] of [["apX", "x"], ["apY", "y"], ["apW", "w"], ["apH", "h"]]) {
        $("#" + id).addEventListener("change", (e) => {
          try { majPos({ [cle]: lireF(cle, e.target.value) }); }
          catch (er) { VL.toast(er.message, true); rendrePanneau(); }
        });
      }
      $("#apIncliner").addEventListener("click", () => {
        const b0 = VL.bboxSelectionDoc(); if (!b0) return;
        const piv = etat.pivot || [b0.x + b0.w / 2, b0.y + b0.h / 2];
        VL.executer(op_incliner, etat.selection.slice(), +$("#apKx").value || 0, +$("#apKy").value || 0, piv[0], piv[1]);
      });
      $("#apPivotRaz").addEventListener("click", () => { etat.pivot = null; VL.rendreOverlay(); });
      $("#apPuissance").addEventListener("click", () => {
        const ids = VL.executer(op_dupliquer_puissance, etat.selection.slice(), Math.round(+$("#apPn").value || 1),
          { dx: +$("#apPdx").value || 0, dy: +$("#apPdy").value || 0, rotation: +$("#apProt").value || 0, echelle: +$("#apPech").value || 1 });
        if (ids) VL.setSelection(ids);
      });
      hote.querySelectorAll("[data-attr]").forEach((btn) => btn.addEventListener("click", () => {
        try { VL.setSelection(selection_par_attribut(etat.doc, etat.selection[0], btn.dataset.attr)); }
        catch (er) { VL.toast(er.message, true); }
      }));
      // id distinct de la pastille de contour (deux « apContour » liaient la pastille au décalage)
      $("#apDecaler").addEventListener("click", () => {
        const ids = VL.executer(op_contour, etat.selection.slice(), +$("#apDecal").value || 0);
        if (ids) VL.setSelection(ids);
      });
    }
    if (objetReflete() && objetReflete().type === "rect") {
      $("#apRayon").addEventListener("change", (e) => VL.executer(
        op_rect_rayon, etat.selection.slice(),
        Math.max(0, +e.target.value || 0)));
    }
    $("#apFond").addEventListener("click", (e) =>
      VL.ouvrirNuancier(e.currentTarget.dataset.hex,
                        (hex) => appliquer({ fond: hex }), e.currentTarget));
    $("#apFondAucun").addEventListener("click",
      () => appliquer({ fond: "none" }));
    $("#apGradL").addEventListener("click", () => degradeDefaut("lineaire"));
    $("#apGradR").addEventListener("click", () => degradeDefaut("radial"));
    $("#apContour").addEventListener("click", (e) =>
      VL.ouvrirNuancier(e.currentTarget.dataset.hex,
                        (hex) => appliquer({ contour: hex }), e.currentTarget));
    $("#apContourAucun").addEventListener("click",
      () => appliquer({ contour: null }));
    $("#apEpaisseur").addEventListener("change",
      (e) => appliquer({ epaisseur: Math.max(0.5, +e.target.value || 1) }));
    $("#apPointilles").addEventListener("change",
      (e) => appliquer({ pointilles: e.target.value || null }));
    $("#apJoint").addEventListener("change",
      (e) => appliquer({ joint: e.target.value === "round"
                                ? null : e.target.value }));
    $("#apOpacite").addEventListener("change",
      (e) => appliquer({ opacite: +e.target.value === 100
                                  ? null : +e.target.value / 100 }));
    /* Texte & logo : fonte, corps, graisse, interlettrage et contours se règlent dans le panneau Texte (mod-typo) */
    if (g) {
      hote.querySelectorAll("[data-stop]").forEach((btn) =>
        btn.addEventListener("click", () => VL.ouvrirNuancier(
          btn.dataset.hex,
          (hex) => VL.executer(op_degrade_stop_modifier, gid,
                               +btn.dataset.stop, { couleur: hex }),
          btn)));
      hote.querySelectorAll("[data-stopt]").forEach((inp) =>
        inp.addEventListener("change", () => VL.executer(
          op_degrade_stop_modifier, gid, +inp.dataset.stopt,
          { t: Math.max(0, Math.min(1, +inp.value / 100)) })));
      hote.querySelectorAll("[data-stopx]").forEach((b) =>
        b.addEventListener("click", () => VL.executer(
          op_degrade_stop_supprimer, gid, +b.dataset.stopx)));
      $("#apStopPlus").addEventListener("click", () => VL.executer(
        op_degrade_stop_ajouter, gid, { t: 0.5, couleur: "#888888" }));
    }
  }

  // les ACTIONS de la sélection — appelées par le menu détaché Sélection (les
  // rangées du panneau qui les portaient sont parties : une seule source)
  VL.actions = VL.actions || {};
  VL.actions.selection = {
    aligner: (mode) => { const paires = pairesSelection(); if (!paires.length) return;
      const ref = paires.length === 1 ? { x: 0, y: 0, w: etat.doc.taille.w, h: etat.doc.taille.h } : reunion(paires);
      VL.executer(op_aligner, paires, mode, ref); },
    distribuer: (axe) => { const paires = pairesSelection(); if (paires.length >= 3) VL.executer(op_distribuer, paires, axe); },
    miroir: (axe) => { const paires = pairesSelection(); if (paires.length) VL.executer(op_miroir, etat.selection.slice(), axe, reunion(paires)); },
    dupliquer: () => VL.dupliquerSelection(),
    ordre: (mode) => { if (etat.selection.length) VL.executer(op_ordre, etat.selection.slice(), mode); },
    grouper: () => { const id = VL.executer(op_grouper, etat.selection.slice()); if (id) VL.setSelection([id]); },
    degrouper: () => { const ids = VL.executer(op_degrouper, etat.selection[0]); if (ids) VL.setSelection(ids); },
    booleen: (op) => { const sel2 = etat.selection.slice(); if (sel2.length < 2) return;
      if (op === "division") { const ids = VL.executer(op_division, sel2); if (ids) VL.setSelection(ids); }
      else { const id = VL.executer(op_booleen, sel2, op); if (id) VL.setSelection([id]); } },
    peut: () => ({ n: etat.selection.length, groupe: etat.selection.length === 1 && objetReflete() && objetReflete().type === "groupe" }),
  };
  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { suivantRendu(); rendrePanneau(); };
  const suivantSel = VL.surSelection;
  VL.surSelection = () => { suivantSel(); rendrePanneau(); };
  VL.opDegradeModifier = op_degrade_modifier;   // pour les poignées (tools)
}
