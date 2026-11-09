// mod-tracesui.js — lot D1 « Tracés » (t430) : les commandes de mod-traces.js dans l'interface. Les menus (bloc
// Tracé et Pathfinder du menu Vecteur) nomment des actions « traces:<arg> » que mod-charpente résout ICI ; le menu
// détaché Sélection reçoit les six Pathfinder ; Ctrl+4 répète le dernier Pathfinder (booléens d'origine compris).
// Les réglages se demandent par un formulaire maison (classes vl-dlg) ; `demander` est remplaçable (banc qa/).
import { T } from "./mod-i18n.js";
import { op_contour_vectoriser, op_simplifier, simplifier_apercu, op_points_ajouter, op_noeuds_moyenne, op_nettoyer,
         op_diviser_dessous, op_lignes_colonnes, op_pathfinder } from "./mod-traces.js";

export const PATHFINDER = [
  ["exclusion", "vectorlab.traces.pf_exclusion"], ["soustraction_arriere", "vectorlab.traces.pf_soustraction_arriere"],
  ["decoupage", "vectorlab.traces.pf_decoupage"], ["fusion", "vectorlab.traces.pf_fusion"],
  ["recadrage", "vectorlab.traces.pf_recadrage"], ["contour", "vectorlab.traces.pf_contour"],
];

const _esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// le formulaire dans la page : { titre, champs: [{ id, type: curseur | case | nombre | choix | couleur (t479), libelle, valeur, min, max,
// pas, options: [[valeur, libelle]] }], apercu?: (valeurs) => texte, surChange?: (valeurs) => void } -> Promise(valeurs | null)
// t455 : exporté pour les dialogues de mod-repeterui.js ; surChange sert leur aperçu en direct sur le document
export function formulaire_dom(spec) {
  return new Promise((resoudre) => {
    let hote = document.querySelector("#vlTracesDlg");
    if (!hote) { hote = document.createElement("div"); hote.id = "vlTracesDlg"; hote.className = "vl-dlg hidden"; document.body.appendChild(hote); }
    const champ = (c) => {
      if (c.type === "case") return `<label style="display:flex;gap:8px;align-items:center"><input type="checkbox" data-id="${c.id}" ${c.valeur ? "checked" : ""}/> ${_esc(c.libelle)}</label>`;
      if (c.type === "choix") return `<fieldset style="border:0;padding:0;margin:0;display:flex;flex-direction:column;gap:4px">${c.options.map(([v, l]) =>
        `<label style="display:flex;gap:8px;align-items:center"><input type="radio" name="${c.id}" data-id="${c.id}" value="${_esc(v)}" ${v === c.valeur ? "checked" : ""}/> ${_esc(l)}</label>`).join("")}</fieldset>`;
      if (c.type === "couleur") return `<label style="display:flex;gap:8px;align-items:center;justify-content:space-between">${_esc(c.libelle)} <input type="color" data-id="${c.id}" value="${_esc(c.valeur)}" style="width:44px;height:24px;padding:0;border:0"/></label>`;   // t479
      const type = c.type === "curseur" ? "range" : "number";
      return `<label style="display:flex;gap:8px;align-items:center;justify-content:space-between">${_esc(c.libelle)} <span style="display:flex;gap:6px;align-items:center"><input type="${type}" data-id="${c.id}" min="${c.min ?? ""}" max="${c.max ?? ""}" step="${c.pas ?? 1}" value="${c.valeur}" style="width:${type === "range" ? "160px" : "72px"}"/>${type === "range" ? `<output data-sortie="${c.id}">${c.valeur}</output>` : ""}</span></label>`;
    };
    hote.innerHTML = `<div class="vl-dlg-boite vl-dlg-petite" role="dialog" aria-modal="true" aria-label="${_esc(spec.titre)}">
      <div class="vl-dlg-tete"><b>${_esc(spec.titre)}</b></div>
      <div class="vl-dlg-corps">${spec.champs.map(champ).join("")}${spec.apercu ? `<p class="trc-apercu" style="opacity:.8"></p>` : ""}</div>
      <div class="vl-dlg-pied"><button data-role="annuler">${_esc(T("vectorlab.traces.annuler"))}</button><button data-role="ok" class="vl-dlg-defaut">${_esc(T("vectorlab.traces.appliquer"))}</button></div></div>`;
    const lire = () => {
      const v = {};
      for (const c of spec.champs) {
        if (c.type === "case") v[c.id] = hote.querySelector(`[data-id="${c.id}"]`).checked;
        else if (c.type === "choix") { const r = hote.querySelector(`[data-id="${c.id}"]:checked`); v[c.id] = r ? r.value : c.valeur; }
        else if (c.type === "couleur") v[c.id] = hote.querySelector(`[data-id="${c.id}"]`).value;
        else v[c.id] = Number(hote.querySelector(`[data-id="${c.id}"]`).value);
      }
      return v;
    };
    const majApercu = () => {
      for (const o of hote.querySelectorAll("output[data-sortie]")) o.textContent = hote.querySelector(`[data-id="${o.dataset.sortie}"]`).value;
      const p = hote.querySelector(".trc-apercu"); if (p) p.textContent = spec.apercu(lire());
      if (spec.surChange) spec.surChange(lire());
    };
    const fin = (ok) => { const v = ok ? lire() : null; hote.classList.add("hidden"); hote.innerHTML = ""; document.removeEventListener("keydown", touche, true); resoudre(v); };
    const touche = (ev) => { if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); fin(false); } else if (ev.key === "Enter") { ev.preventDefault(); ev.stopPropagation(); fin(true); } };
    hote.querySelectorAll("input").forEach((i) => i.addEventListener("input", majApercu));
    hote.querySelector('[data-role="annuler"]').addEventListener("click", () => fin(false));
    hote.querySelector('[data-role="ok"]').addEventListener("click", () => fin(true));
    document.addEventListener("keydown", touche, true);
    hote.classList.remove("hidden");
    majApercu();
    (hote.querySelector("input") || hote.querySelector('[data-role="ok"]')).focus();
  });
}

// les actions, sans DOM : { action(arg) -> { peut, faire }, flyoutBool(e, p), pathfinder(mode), dernier() }
export function traces_actions(VL) {
  const etat = VL.etat;
  const sel = () => (etat.doc ? etat.selection.slice() : []);
  const objets = () => sel().map((id) => VL.objetDe(id)).filter(Boolean).map((t) => t.objet);
  const poser = (ids) => { if (Array.isArray(ids) && ids.length) VL.setSelection(ids); };
  let dernier = null;                                  // { mode } Pathfinder, ou { bool } booléen d'origine
  const A = {
    demander: (spec) => formulaire_dom(spec),
    dernier: () => dernier,
    noterBooleen: (op) => { dernier = { bool: op }; },
    pathfinder: (mode) => { dernier = { mode }; poser(VL.executer(op_pathfinder, sel(), mode)); },
  };
  const T_ = {
    contour: { peut: () => sel().length >= 1, faire: () => poser(VL.executer(op_contour_vectoriser, sel())) },
    simplifier: { peut: () => sel().length >= 1, faire: async () => {
      const os = objets();
      const v = await A.demander({ titre: T("vectorlab.traces.simplifier_titre"), champs: [
        { id: "precision", type: "curseur", libelle: T("vectorlab.traces.precision"), min: 0, max: 100, pas: 1, valeur: 50 },
        { id: "droites", type: "case", libelle: T("vectorlab.traces.droites"), valeur: false }],
        apercu: (x) => { let av = 0, ap = 0; for (const o of os) { try { const r = simplifier_apercu(o, x); av += r.avant; ap += r.apres; } catch (e) { /* objet non simplifiable */ } } return T("vectorlab.traces.simplifier_apercu", { avant: av, apres: ap }); } });
      if (v) poser(VL.executer(op_simplifier, sel(), { precision: v.precision, droites: !!v.droites }));
    } },
    ajouter: { peut: () => sel().length >= 1, faire: () => poser(VL.executer(op_points_ajouter, sel())) },
    supprimer: { peut: () => etat.outil === "noeuds" && !!VL.pathSelectionne() && ((etat.ancreSel !== null && etat.ancreSel !== undefined) || (etat.ancresSel || []).length > 0)
                 && !!(VL.actions && VL.actions.noeuds && VL.actions.noeuds.supprimerLisse),
                 faire: () => VL.actions.noeuds.supprimerLisse() },
    moyenne: { peut: () => !!VL.pathSelectionne() && (etat.ancresSel || []).length >= 2, faire: async () => {
      const p = VL.pathSelectionne(), idx = (etat.ancresSel || []).slice();
      const v = await A.demander({ titre: T("vectorlab.traces.moyenne_titre"), champs: [{ id: "axe", type: "choix", valeur: "deux", options: [
        ["horizontale", T("vectorlab.traces.moyenne_h")], ["verticale", T("vectorlab.traces.moyenne_v")], ["deux", T("vectorlab.traces.moyenne_deux")]] }] });
      if (v && p) VL.executer(op_noeuds_moyenne, p.id, idx, v.axe);
    } },
    nettoyer: { peut: () => !!etat.doc, faire: async () => {
      const v = await A.demander({ titre: T("vectorlab.traces.nettoyer_titre"), champs: [
        { id: "isoles", type: "case", libelle: T("vectorlab.traces.n_isoles"), valeur: true },
        { id: "invisibles", type: "case", libelle: T("vectorlab.traces.n_invisibles"), valeur: true },
        { id: "textesVides", type: "case", libelle: T("vectorlab.traces.n_textes"), valeur: true }] });
      if (!v) return;
      const r = VL.executer(op_nettoyer, { isoles: !!v.isoles, invisibles: !!v.invisibles, textesVides: !!v.textesVides });
      if (r) { const n = r.isoles + r.invisibles + r.textesVides; VL.toast(T(n > 1 ? "vectorlab.traces.nettoyer_bilan_plusieurs" : "vectorlab.traces.nettoyer_bilan_un", { n })); }
    } },
    diviser: { peut: () => sel().length === 1, faire: () => poser(VL.executer(op_diviser_dessous, sel()[0])) },
    lignes: { peut: () => sel().length === 1, faire: async () => {
      const v = await A.demander({ titre: T("vectorlab.traces.lignes_titre"), champs: [
        { id: "lignes", type: "nombre", libelle: T("vectorlab.traces.l_lignes"), min: 1, max: 100, valeur: 2 },
        { id: "colonnes", type: "nombre", libelle: T("vectorlab.traces.l_colonnes"), min: 1, max: 100, valeur: 2 },
        { id: "gouttiereLignes", type: "nombre", libelle: T("vectorlab.traces.l_g_lignes"), min: 0, pas: 0.5, valeur: 0 },
        { id: "gouttiereColonnes", type: "nombre", libelle: T("vectorlab.traces.l_g_colonnes"), min: 0, pas: 0.5, valeur: 0 },
        { id: "reperes", type: "case", libelle: T("vectorlab.traces.l_reperes"), valeur: false }] });
      if (v) poser(VL.executer(op_lignes_colonnes, sel()[0], v));
    } },
    repeter: { peut: () => !!dernier && sel().length >= 2, faire: () => {
      if (dernier && dernier.mode) A.pathfinder(dernier.mode);
      else if (dernier && dernier.bool && VL.actions && VL.actions.selection) VL.actions.selection.booleen(dernier.bool);
    } },
  };
  for (const [k] of PATHFINDER) T_["pf-" + k] = { peut: () => sel().length >= 2, faire: () => A.pathfinder(k) };
  A.action = (arg) => T_[arg] || { peut: () => false, faire: () => {} };
  A.flyoutBool = (e, p) => PATHFINDER.map(([k, cle]) => e("pf-" + k, T(cle), p.n >= 2, () => A.pathfinder(k), ""));
  return A;
}

export function initTracesUI(VL) {
  const A = traces_actions(VL);
  VL.traces = A;
  VL.actions = VL.actions || {};
  VL.actions.traces = A;
  // les booléens d'origine (union, soustraction, intersection, division) deviennent aussi « le dernier Pathfinder »
  const S = VL.actions.selection;
  if (S && S.booleen && !S.booleen.__traces) {
    const orig = S.booleen;
    S.booleen = (op) => { if (VL.traces) VL.traces.noterBooleen(op); return orig(op); };   // le VL.traces COURANT
    S.booleen.__traces = true;
  }
  if (typeof document !== "undefined") {
    document.addEventListener("keydown", (ev) => {
      if (!ev.ctrlKey || ev.key !== "4" || ev.altKey || ev.shiftKey) return;
      const cible = ev.target;
      if (cible && (cible.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(cible.tagName || ""))) return;
      const r = A.action("repeter");
      ev.preventDefault();
      if (r.peut()) r.faire(); else VL.toast(T("vectorlab.traces.repeter_rien"), true);
    });
  }
  return A;
}
