// mod-recolorerui.js — lot D5 « Couleur et motif », T2 (t476) : Édition › Couleurs dans l'interface. Les entrées du
// menu Édition sont des actions « couleurs:<x> », résolues par mod-charpente (préfixe greffé par t476.py) ; les
// transformations viennent de mod-recolorer.js et s'appliquent à la SÉLECTION en une seule étape d'annulation. Saturer et
// Régler l'équilibre ouvrent un dialogue pré-rempli avec aperçu en direct (dialogue_apercu de D2).
import { T } from "./mod-i18n.js";
import { formulaire_dom } from "./mod-tracesui.js";
import { dialogue_apercu } from "./mod-repeterui.js";
import { op_couleurs_transformer, op_couleurs_fusion, inverser, niveaux_de_gris, saturer, equilibre, couleurs_selection, op_recolorer,
         reduire, harmoniser, melanger } from "./mod-recolorer.js";
import { HARMONIES } from "./mod-couleur.js";
import { initMotifsUI } from "./mod-motifsui.js";
import { initPinceauxUI } from "./mod-pinceauxui.js";

export function champs_equilibre(p = {}) {
  const nb = (id, lib, valeur) => ({ id, type: "nombre", libelle: T(lib), valeur, min: -100, max: 100, pas: 1 });
  return [
    { id: "mode", type: "choix", valeur: p.mode || "rvb", options: [["rvb", T("vectorlab.couleurs.o_rvb")], ["cmjn", T("vectorlab.couleurs.o_cmjn")]] },
    nb("a", "vectorlab.couleurs.c_a", p.a ?? 0), nb("b", "vectorlab.couleurs.c_b", p.b ?? 0),
    nb("c", "vectorlab.couleurs.c_c", p.c ?? 0), nb("d", "vectorlab.couleurs.c_d", p.d ?? 0)];
}

const _esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// t477 : le dialogue Recolorer l'illustration — une ligne par couleur (actuelle → nouvelle), harmonie, réduction,
// mélange, réinitialisation ; chaque changement passe par spec.surChange(table) (aperçu en direct)
export function dialogue_recolorer_dom(spec) {
  return new Promise((resoudre) => {
    let hote = document.querySelector("#vlTracesDlg");
    if (!hote) { hote = document.createElement("div"); hote.id = "vlTracesDlg"; hote.className = "vl-dlg hidden"; document.body.appendChild(hote); }
    const C = spec.couleurs;
    let graine = 1;
    const ligne = (c, i) => `<div class="rec-ligne" style="display:grid;grid-template-columns:28px 16px 44px 1fr;gap:8px;align-items:center">
      <span title="${_esc(c.hex)}" style="width:28px;height:20px;background:${c.hex};border:1px solid var(--vl-bord, #555)"></span><svg width="16" height="12" viewBox="0 0 16 12" aria-hidden="true"><path d="M1 6 H13 M9 2 L13 6 L9 10" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>
      <input type="color" data-i="${i}" value="${c.hex}" aria-label="${_esc(T("vectorlab.recolorer.nouvelle"))} ${_esc(c.hex)}" style="width:44px;height:24px;padding:0;border:0"/>
      <span style="opacity:.75">${_esc(c.hex)} · ${_esc(T("vectorlab.recolorer.usages", { n: c.n }))}</span></div>`;
    hote.innerHTML = `<div class="vl-dlg-boite vl-dlg-petite" role="dialog" aria-modal="true" aria-label="${_esc(spec.titre)}">
      <div class="vl-dlg-tete"><b>${_esc(spec.titre)}</b></div>
      <div class="vl-dlg-corps" style="display:flex;flex-direction:column;gap:8px">
        <div style="display:grid;grid-template-columns:28px 16px 44px 1fr;gap:8px;opacity:.7"><span>${_esc(T("vectorlab.recolorer.actuelle"))}</span><span></span><span>${_esc(T("vectorlab.recolorer.nouvelle"))}</span><span></span></div>
        <div style="display:flex;flex-direction:column;gap:6px;max-height:300px;overflow:auto">${C.map(ligne).join("")}</div>
        <label style="display:flex;gap:8px;align-items:center">${_esc(T("vectorlab.recolorer.harmonie"))}
          <select data-role="regle">${HARMONIES.map((h) => `<option value="${h.id}">${_esc(h.libelle)}</option>`).join("")}</select>
          <button data-role="harmonie">${_esc(T("vectorlab.recolorer.appliquer_harmonie"))}</button></label>
        <label style="display:flex;gap:8px;align-items:center">${_esc(T("vectorlab.recolorer.reduire"))}
          <input type="number" data-role="n" min="1" max="${Math.min(64, C.length)}" step="1" value="${Math.max(1, Math.min(3, C.length))}" style="width:56px"/>
          ${_esc(T("vectorlab.recolorer.reduire_unite"))} <button data-role="reduire">${_esc(T("vectorlab.recolorer.reduire_btn"))}</button></label>
        <div style="display:flex;gap:8px"><button data-role="melanger">${_esc(T("vectorlab.recolorer.melanger"))}</button><button data-role="reinitialiser">${_esc(T("vectorlab.recolorer.reinitialiser"))}</button></div>
      </div>
      <div class="vl-dlg-pied"><button data-role="annuler">${_esc(T("vectorlab.traces.annuler"))}</button><button data-role="ok" class="vl-dlg-defaut">${_esc(T("vectorlab.traces.appliquer"))}</button></div></div>`;
    const entrees = [...hote.querySelectorAll('input[type="color"]')];
    const lire = () => Object.fromEntries(C.map((c, i) => [c.hex, entrees[i].value]));
    const changer = () => { if (spec.surChange) spec.surChange(lire()); };
    const poser = (table) => { C.forEach((c, i) => { entrees[i].value = table[c.hex] || c.hex; }); changer(); };
    const essayer = (f) => { try { poser(f()); } catch (e) { /* une borne refusée : rien ne change */ } };
    entrees.forEach((e) => e.addEventListener("input", changer));
    hote.querySelector('[data-role="harmonie"]').addEventListener("click", () => essayer(() => harmoniser(C, hote.querySelector('[data-role="regle"]').value)));
    hote.querySelector('[data-role="reduire"]').addEventListener("click", () => essayer(() => reduire(C, Number(hote.querySelector('[data-role="n"]').value))));
    hote.querySelector('[data-role="melanger"]').addEventListener("click", () => essayer(() => melanger(C, graine++)));
    hote.querySelector('[data-role="reinitialiser"]').addEventListener("click", () => poser({}));
    const fin = (ok) => { const v = ok ? lire() : null; hote.classList.add("hidden"); hote.innerHTML = ""; document.removeEventListener("keydown", touche, true); resoudre(v); };
    const touche = (ev) => { if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); fin(false); } };
    hote.querySelector('[data-role="annuler"]').addEventListener("click", () => fin(false));
    hote.querySelector('[data-role="ok"]').addEventListener("click", () => fin(true));
    document.addEventListener("keydown", touche, true);
    hote.classList.remove("hidden");
    (entrees[0] || hote.querySelector('[data-role="ok"]')).focus();
  });
}

export function couleurs_actions(VL) {
  const etat = VL.etat;
  const sel = () => (etat.doc ? (etat.selection || []).slice() : []);
  const A = { demander: (spec) => formulaire_dom(spec), demanderRecolorer: (spec) => dialogue_recolorer_dom(spec) };
  A.dialogue = (spec, appliquer) => dialogue_apercu(VL, (s) => A.demander(s), spec, appliquer);
  const direct = (f) => ({ peut: () => sel().length >= 1, faire: async () => { VL.executer(op_couleurs_transformer, sel(), f); } });
  const fusion = (sens) => ({ peut: () => sel().length >= 1, faire: async () => { VL.executer(op_couleurs_fusion, sel(), sens); } });
  const ACTIONS = {
    inverser: direct(inverser),
    gris: direct(niveaux_de_gris),
    saturer: { peut: () => sel().length >= 1, faire: async () => {
      const ids = sel();
      const v = await A.dialogue({ titre: T("vectorlab.couleurs.d_saturer"), champs: [{ id: "pct", type: "nombre", libelle: T("vectorlab.couleurs.c_pct"), valeur: 20, min: -100, max: 100, pas: 1 }] },
        (d, x) => op_couleurs_transformer(d, ids, (h) => saturer(h, x.pct)));
      if (v) VL.executer(op_couleurs_transformer, ids, (h) => saturer(h, v.pct));
    } },
    equilibre: { peut: () => sel().length >= 1, faire: async () => {
      const ids = sel();
      const v = await A.dialogue({ titre: T("vectorlab.couleurs.d_equilibre"), champs: champs_equilibre() }, (d, x) => op_couleurs_transformer(d, ids, (h) => equilibre(h, x)));
      if (v) VL.executer(op_couleurs_transformer, ids, (h) => equilibre(h, v));
    } },
    recolorer: { peut: () => sel().length >= 1, faire: async () => {
      const ids = sel(), couleurs = couleurs_selection(etat.doc, ids);
      if (!couleurs.length) { VL.toast(T("vectorlab.recolorer.aucune_couleur"), true); return; }
      const v = await dialogue_apercu(VL, (s) => A.demanderRecolorer(s), { titre: T("vectorlab.recolorer.d_titre"), couleurs }, (d, table) => op_recolorer(d, ids, table));
      if (v) VL.executer(op_recolorer, ids, v);
    } },
    fusion_h: fusion("horizontal"),
    fusion_v: fusion("vertical"),
    fusion_z: fusion("avant_arriere"),
  };
  // t479 / t481 : les actions « couleurs:motif_* » et « couleurs:pinceau_* » (mod-motifsui.js, mod-pinceauxui.js)
  A.action = (nom) => ACTIONS[nom] || (VL.motifsUI && VL.motifsUI.action(nom)) || (VL.pinceauxUI && VL.pinceauxUI.action(nom)) || { peut: () => false, faire: () => {} };
  return A;
}

export function initRecolorerUI(VL) {
  initMotifsUI(VL);
  initPinceauxUI(VL);
  const A = couleurs_actions(VL);
  VL.couleursUI = A;
  return A;
}
