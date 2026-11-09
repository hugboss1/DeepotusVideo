// mod-pinceauxui.js — lot D5 « Couleur et motif », T7 (t481) : les pinceaux de mod-pinceaux.js dans l'interface.
//   * Vecteur › Nouveau pinceau… (depuis la sélection : nom, genre) ;
//   * Vecteur › Appliquer un pinceau… (choix du pinceau, puis ses réglages avec aperçu en direct) ;
//   * Vecteur › Options du pinceau…, Retirer le pinceau, Supprimer un pinceau… ;
//   * la section « Pinceau vivant » de l'onglet Apparence, branchée par mod-repeterui.js (Options…, Décomposer et leur
//     câblage existent déjà) ; « Retirer » y est écouté par délégation.
// Les actions « couleurs:pinceau_* » arrivent par mod-recolorerui.js (préfixe greffé par t476) ; l'init est faite par
// initRecolorerUI. L'outil Pinceau à profils (mod-pinceauvec.js) reste tel quel.
import { T } from "./mod-i18n.js";
import { formulaire_dom } from "./mod-tracesui.js";
import { dialogue_apercu } from "./mod-repeterui.js";
import { op_pinceau_creer, op_pinceau_appliquer, op_pinceau_regler, op_pinceau_retirer, op_pinceau_supprimer, GENRES, params_pinceau } from "./mod-pinceaux.js";

const NOMS_GENRES = { artistique: "vectorlab.pinceaux.g_artistique", dispersion: "vectorlab.pinceaux.g_dispersion", motif: "vectorlab.pinceaux.g_motif" };
const _esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export function champs_pinceau(genre, base = {}) {
  const p = params_pinceau(genre, {}, base);
  const nb = (id, lib, min, max, pas = 1) => ({ id, type: "nombre", libelle: T(lib), valeur: p[id], min, max, pas });
  const cs = (id, lib) => ({ id, type: "case", libelle: T(lib), valeur: !!p[id] });
  if (genre === "artistique") return [nb("echelle", "vectorlab.pinceaux.c_echelle", 0.05, 20, 0.05), cs("retourner", "vectorlab.pinceaux.c_retourner"), cs("proportionnel", "vectorlab.pinceaux.c_proportionnel")];
  if (genre === "motif") return [nb("echelle", "vectorlab.pinceaux.c_echelle", 0.05, 20, 0.05), nb("espacement", "vectorlab.pinceaux.c_espacement_motif", -90, 1000),
    { id: "ajustement", type: "choix", valeur: p.ajustement, options: [["etirer", T("vectorlab.pinceaux.o_etirer")], ["couper", T("vectorlab.pinceaux.o_couper")]] }];
  return [nb("espacement", "vectorlab.pinceaux.c_espacement", 1, 1000), nb("taille", "vectorlab.pinceaux.c_taille", 1, 1000), nb("taille_alea", "vectorlab.pinceaux.c_taille_alea", 0, 100),
    { id: "rotation", type: "choix", valeur: p.rotation, options: [["trace", T("vectorlab.pinceaux.o_trace")], ["fixe", T("vectorlab.pinceaux.o_fixe")]] },
    nb("rotation_alea", "vectorlab.pinceaux.c_rotation_alea", 0, 180), nb("ecart", "vectorlab.pinceaux.c_ecart", -500, 500), nb("ecart_alea", "vectorlab.pinceaux.c_ecart_alea", 0, 500),
    nb("graine", "vectorlab.pinceaux.c_graine", 1, 1e6)];
}
export function resume_pinceau(doc, g) {
  const def = (doc.pinceaux || {})[g.pinceau.id];
  if (!def) return T("vectorlab.pinceaux.a_disparu", { id: g.pinceau.id });
  return T("vectorlab.pinceaux.a_resume", { nom: def.nom, genre: T(NOMS_GENRES[def.genre]) });
}

export function pinceaux_actions(VL) {
  const etat = VL.etat;
  const sel = () => (etat.doc ? (etat.selection || []).slice() : []);
  const A = { demander: (spec) => formulaire_dom(spec) };
  const dialogue = (spec, appliquer) => dialogue_apercu(VL, (s) => A.demander(s), spec, appliquer);
  const defs = () => Object.entries((etat.doc && etat.doc.pinceaux) || {});
  const peint = () => {
    const s = sel();
    if (s.length !== 1) return null;
    const t = VL.objetDe(s[0]);
    return t && t.objet.pinceau ? t.objet : null;
  };
  const choisir = (titre) => A.demander({ titre, champs: [{ id: "pinceau", type: "choix", valeur: defs()[0][0],
    options: defs().map(([id, p]) => [id, `${p.nom} (${T(NOMS_GENRES[p.genre])})`]) }] });
  const ACTIONS = {
    pinceau_nouveau: { peut: () => sel().length >= 1, faire: async () => {
      const ids = sel();
      const v = await A.demander({ titre: T("vectorlab.pinceaux.d_nouveau"), champs: [
        { id: "nom", type: "texte", libelle: T("vectorlab.pinceaux.c_nom"), valeur: "" },
        { id: "genre", type: "choix", valeur: "artistique", options: GENRES.map((g) => [g, T(NOMS_GENRES[g])]) }] });
      if (!v) return;
      const pid = VL.executer(op_pinceau_creer, ids, v);
      if (pid) VL.toast(T("vectorlab.pinceaux.cree", { nom: etat.doc.pinceaux[pid].nom }));
    } },
    pinceau_appliquer: { peut: () => sel().length >= 1, faire: async () => {
      if (!defs().length) { VL.toast(T("vectorlab.pinceaux.aucun"), true); return; }
      const ids = sel();
      const c = await choisir(T("vectorlab.pinceaux.d_choisir"));
      if (!c) return;
      const def = etat.doc.pinceaux[c.pinceau];
      const v = await dialogue({ titre: T("vectorlab.pinceaux.d_reglages", { nom: def.nom }), champs: champs_pinceau(def.genre) }, (d, x) => op_pinceau_appliquer(d, ids, c.pinceau, x));
      if (!v) return;
      const gs = VL.executer(op_pinceau_appliquer, ids, c.pinceau, v);
      if (gs && VL.setSelection) VL.setSelection(gs);
    } },
    pinceau_options: { peut: () => !!peint(), faire: async () => {
      const g = peint(), def = (etat.doc.pinceaux || {})[g.pinceau.id];
      if (!def) { VL.toast(T("vectorlab.pinceaux.inconnu", { id: g.pinceau.id }), true); return; }
      const v = await dialogue({ titre: T("vectorlab.pinceaux.d_reglages", { nom: def.nom }), champs: champs_pinceau(def.genre, g.pinceau.params) }, (d, x) => op_pinceau_regler(d, g.id, x));
      if (v) VL.executer(op_pinceau_regler, g.id, v);
    } },
    pinceau_retirer: { peut: () => !!peint(), faire: async () => {
      const id = VL.executer(op_pinceau_retirer, peint().id);
      if (id && VL.setSelection) VL.setSelection([id]);
    } },
    pinceau_supprimer: { peut: () => defs().length > 0, faire: async () => {
      const c = await choisir(T("vectorlab.pinceaux.d_supprimer"));
      if (c) VL.executer(op_pinceau_supprimer, c.pinceau);
    } },
  };
  A.action = (nom) => ACTIONS[nom] || null;
  // la section « Pinceau vivant » de l'onglet Apparence (Options… et Décomposer réutilisent le câblage de D2)
  A.sectionApparence = (o) => `<details open><summary class="px-tete">${_esc(T("vectorlab.pinceaux.a_titre"))}</summary>
      <div class="ap-ligne"><i class="px-note" style="flex:1">${_esc(resume_pinceau(etat.doc, o))}</i><button id="a2VivantOptions">${_esc(T("vectorlab.repeter.a_options"))}</button><button id="a2PinRetirer" title="${_esc(T("vectorlab.pinceaux.a_retirer_titre"))}">${_esc(T("vectorlab.pinceaux.m_retirer"))}</button><button id="a2Detacher" title="${_esc(T("vectorlab.repeter.a_decomposer_titre"))}">${_esc(T("vectorlab.repeter.m_decomposer"))}</button></div>
    </details>`;
  return A;
}

export function initPinceauxUI(VL) {
  const A = pinceaux_actions(VL);
  VL.pinceauxUI = A;
  if (typeof document !== "undefined") {
    document.addEventListener("click", (ev) => {
      const b = ev.target && ev.target.closest && ev.target.closest("#a2PinRetirer");
      if (b) { const r = A.action("pinceau_retirer"); if (r.peut()) r.faire(); }
    });
  }
  return A;
}
