// mod-repeterui.js — lot D2 « Répéter et fusionner » (t455) : les répétitions et fusions vivantes de mod-repeter.js
// dans l'interface. Les menus (bloc Répétition et Fusion du menu Vecteur) nomment des actions « repeter:<arg> » que
// mod-charpente résout ICI ; l'onglet Apparence montre la recette de l'objet vivant sélectionné (sectionApparence) ;
// Ctrl+Alt+B crée une fusion. Les dialogues reprennent le formulaire de mod-tracesui.js avec un APERÇU EN DIRECT :
// chaque changement rejoue l'opération sur une copie du document d'avant (rien n'entre dans l'historique) ;
// Annuler rend le document d'avant, Appliquer passe UNE fois par VL.executer (une étape d'annulation).
import { T } from "./mod-i18n.js";
import { formulaire_dom } from "./mod-tracesui.js";
import { op_repeter, op_repetition_regler, repetition_defauts, op_fusionner, op_fusion_regler, op_fusion_annuler,
         op_fusion_trajectoire, op_fusion_inverser_trajectoire, op_fusion_inverser_ordre } from "./mod-repeter.js";
import { derives_rafraichir, op_derive_detacher } from "./mod-vivants.js";

const _esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const _r2 = (x) => Math.round(Number(x) * 100) / 100;

// les champs d'un dialogue de répétition, pré-remplis par des réglages
export function champs_repetition(mode, p) {
  if (mode === "radiale") return [
    { id: "nombre", type: "nombre", libelle: T("vectorlab.repeter.c_nombre"), min: 2, max: 100, valeur: p.nombre },
    { id: "rayon", type: "nombre", libelle: T("vectorlab.repeter.c_rayon"), min: 0.5, pas: 0.5, valeur: _r2(p.rayon) },
    { id: "orienter", type: "case", libelle: T("vectorlab.repeter.c_orienter"), valeur: p.orienter }];
  if (mode === "grille") return [
    { id: "lignes", type: "nombre", libelle: T("vectorlab.repeter.c_lignes"), min: 1, max: 50, valeur: p.lignes },
    { id: "colonnes", type: "nombre", libelle: T("vectorlab.repeter.c_colonnes"), min: 1, max: 50, valeur: p.colonnes },
    { id: "ecartX", type: "nombre", libelle: T("vectorlab.repeter.c_ecart_x"), pas: 0.5, valeur: p.ecartX },
    { id: "ecartY", type: "nombre", libelle: T("vectorlab.repeter.c_ecart_y"), pas: 0.5, valeur: p.ecartY },
    { id: "decalage", type: "choix", valeur: p.decalage, options: [
      ["aucun", T("vectorlab.repeter.dec_aucun")], ["brique_lignes", T("vectorlab.repeter.dec_brique_lignes")],
      ["brique_colonnes", T("vectorlab.repeter.dec_brique_colonnes")], ["hexagones", T("vectorlab.repeter.dec_hexagones")]] },
    { id: "miroirLignes", type: "case", libelle: T("vectorlab.repeter.c_miroir_lignes"), valeur: p.miroirLignes },
    { id: "miroirColonnes", type: "case", libelle: T("vectorlab.repeter.c_miroir_colonnes"), valeur: p.miroirColonnes }];
  return [
    { id: "angle", type: "nombre", libelle: T("vectorlab.repeter.c_angle"), min: 0, max: 359, valeur: p.angle },
    { id: "ecart", type: "nombre", libelle: T("vectorlab.repeter.c_ecart"), pas: 0.5, valeur: p.ecart }];
}
export function champs_fusion(f) {
  return [
    { id: "mode", type: "choix", valeur: f.mode, options: [
      ["etapes", T("vectorlab.fusion.mode_etapes")], ["distance", T("vectorlab.fusion.mode_distance")], ["couleur", T("vectorlab.fusion.mode_couleur")]] },
    { id: "etapes", type: "nombre", libelle: T("vectorlab.fusion.c_etapes"), min: 1, max: 200, valeur: f.etapes },
    { id: "pas", type: "nombre", libelle: T("vectorlab.fusion.c_pas"), min: 0.5, pas: 0.5, valeur: f.pas },
    { id: "orienter", type: "case", libelle: T("vectorlab.fusion.c_orienter"), valeur: f.orienter }];
}
const _TITRES = { radiale: "vectorlab.repeter.d_radiale", grille: "vectorlab.repeter.d_grille", miroir: "vectorlab.repeter.d_miroir" };

// la recette d'un objet vivant, en une phrase (onglet Apparence)
export function resume_vivant(o) {
  if (o && o.repetition) {
    const p = o.repetition.params, m = o.repetition.mode;
    if (m === "radiale") return T("vectorlab.repeter.resume_radiale", { nombre: p.nombre, rayon: _r2(p.rayon) });
    if (m === "grille") return T("vectorlab.repeter.resume_grille", { lignes: p.lignes, colonnes: p.colonnes });
    return T("vectorlab.repeter.resume_miroir", { angle: _r2(p.angle) });
  }
  if (o && o.fusion_vive) {
    const n = (o.enfants || []).filter((e) => e.genere).length;
    return T(o.fusion_vive.trajectoire ? "vectorlab.fusion.resume_trajectoire" : "vectorlab.fusion.resume", { n });
  }
  return "";
}

// les actions, sans DOM : { action(arg) -> { peut, faire }, sectionApparence(o), demander, dialogue }
export function repeter_actions(VL) {
  const etat = VL.etat;
  const sel = () => (etat.doc ? etat.selection.slice() : []);
  const obj = (id) => { const t = VL.objetDe(id); return t ? t.objet : null; };
  const vivant = (cle) => { const s = sel(); if (s.length !== 1) return null; const o = obj(s[0]); return o && o[cle] ? o : null; };
  const poser = (r) => { if (typeof r === "string") VL.setSelection([r]); else if (Array.isArray(r) && r.length) VL.setSelection(r); };
  const rendre = () => { if (VL.rendre) VL.rendre(); };
  const A = { demander: (spec) => formulaire_dom(spec) };
  // l'aperçu en direct : `appliquer(docEssai, valeurs)` sur une copie du document d'avant ; une valeur refusée par
  // l'opération montre le document d'avant. Rend les valeurs (ou null) ; le document d'avant est TOUJOURS remis.
  A.dialogue = async (spec, appliquer) => {
    const avant = etat.doc;
    const montrer = (v) => {
      try { const essai = JSON.parse(JSON.stringify(avant)); appliquer(essai, v); derives_rafraichir(essai); etat.doc = essai; }
      catch (e) { etat.doc = avant; }
      rendre();
    };
    let v = null;
    try { v = await A.demander({ ...spec, surChange: montrer }); }
    finally { etat.doc = avant; rendre(); }
    return v;
  };
  const repeter = (mode) => ({
    peut: () => sel().length >= 1,
    faire: async () => {
      const ids = sel();
      const def = repetition_defauts(etat.doc, ids, mode);
      if (!def) { VL.toast(T("vectorlab.repeter.source_type"), true); return; }
      const v = await A.dialogue({ titre: T(_TITRES[mode]), champs: champs_repetition(mode, def) }, (d, x) => op_repeter(d, ids, mode, x));
      if (v) poser(VL.executer(op_repeter, ids, mode, v));
    },
  });
  const optionsRepetition = async (g) => {
    const m = g.repetition.mode;
    const v = await A.dialogue({ titre: T(_TITRES[m]), champs: champs_repetition(m, g.repetition.params) }, (d, x) => op_repetition_regler(d, g.id, x));
    if (v) VL.executer(op_repetition_regler, g.id, v);
  };
  const optionsFusion = async (g) => {
    const v = await A.dialogue({ titre: T("vectorlab.fusion.d_options"), champs: champs_fusion(g.fusion_vive) }, (d, x) => op_fusion_regler(d, g.id, x));
    if (v) VL.executer(op_fusion_regler, g.id, v);
  };
  const fus = () => vivant("fusion_vive"), rep = () => vivant("repetition");
  // Remplacer la trajectoire : deux objets, dont exactement une fusion
  const paireTrajectoire = () => {
    const s = sel();
    if (s.length !== 2) return null;
    const os = s.map(obj);
    const k = os.findIndex((o) => o && o.fusion_vive);
    if (k < 0 || (os[1 - k] && os[1 - k].fusion_vive)) return null;
    return { fusion: s[k], chemin: s[1 - k] };
  };
  const T_ = {
    radiale: repeter("radiale"), grille: repeter("grille"), miroir: repeter("miroir"),
    options: { peut: () => !!(rep() || fus()), faire: () => (rep() ? optionsRepetition(rep()) : fus() ? optionsFusion(fus()) : undefined) },
    decomposer: { peut: () => !!(rep() || fus()), faire: () => VL.executer(op_derive_detacher, sel()[0]) },
    fusionner: { peut: () => sel().length === 2, faire: () => poser(VL.executer(op_fusionner, sel(), {})) },
    fusionOptions: { peut: () => !!fus(), faire: () => optionsFusion(fus()) },
    fusionAnnuler: { peut: () => !!fus(), faire: () => poser(VL.executer(op_fusion_annuler, sel()[0])) },
    trajectoire: { peut: () => !!paireTrajectoire(), faire: () => { const p = paireTrajectoire(); VL.executer(op_fusion_trajectoire, p.fusion, p.chemin); poser(p.fusion); } },
    inverserTrajectoire: { peut: () => !!fus(), faire: () => VL.executer(op_fusion_inverser_trajectoire, sel()[0]) },
    inverserOrdre: { peut: () => !!fus(), faire: () => VL.executer(op_fusion_inverser_ordre, sel()[0]) },
  };
  A.action = (arg) => T_[arg] || { peut: () => false, faire: () => {} };
  // la section « vivant » de l'onglet Apparence (Détacher réutilise le bouton a2Detacher et son câblage)
  A.sectionApparence = (o) => {
    if (!o || !(o.repetition || o.fusion_vive)) return "";
    const titre = T(o.repetition ? "vectorlab.repeter.a_titre" : "vectorlab.fusion.a_titre");
    return `<details open><summary class="px-tete">${_esc(titre)}</summary>
        <div class="ap-ligne"><i class="px-note" style="flex:1">${_esc(resume_vivant(o))}</i><button id="a2VivantOptions">${_esc(T("vectorlab.repeter.a_options"))}</button><button id="a2Detacher" title="${_esc(T("vectorlab.repeter.a_decomposer_titre"))}">${_esc(T("vectorlab.repeter.m_decomposer"))}</button></div>
      </details>`;
  };
  return A;
}

export function initRepeterUI(VL) {
  const A = repeter_actions(VL);
  VL.repeterUI = A;
  VL.actions = VL.actions || {};
  VL.actions.repeter = A;
  if (typeof document !== "undefined") {
    // Ctrl+Alt+B : Fusion › Créer, comme Illustrator
    document.addEventListener("keydown", (ev) => {
      if (!ev.ctrlKey || !ev.altKey || ev.shiftKey || String(ev.key).toLowerCase() !== "b") return;
      const cible = ev.target;
      if (cible && (cible.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(cible.tagName || ""))) return;
      ev.preventDefault();
      const r = A.action("fusionner");
      if (r.peut()) r.faire(); else VL.toast(T("vectorlab.fusion.deux"), true);
    });
  }
  return A;
}
