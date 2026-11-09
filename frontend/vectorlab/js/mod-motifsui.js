// mod-motifsui.js — lot D5 « Couleur et motif », T5 (t479) : l'éditeur de motif dans l'interface.
//   * Vecteur › Créer un motif… : depuis la sélection ; pavage, espacements et fond se règlent avec un aperçu en direct
//     (un rectangle rempli du motif posé sur la sélection, sur une copie du document) ;
//   * Vecteur › Motifs du document… : la liste des motifs d'objets (vignette, pavage, usages), et pour chacun
//     Appliquer (fond de la sélection), Réglages…, Remplacer par la sélection, Supprimer.
// Les actions « couleurs:motif_creer » et « couleurs:motifs » arrivent par mod-recolorerui.js (préfixe greffé par t476) ;
// l'init est faite par initRecolorerUI. Les quatre motifs paramétriques gardent leur place dans l'onglet Apparence.
import { T } from "./mod-i18n.js";
import { formulaire_dom } from "./mod-tracesui.js";
import { dialogue_apercu } from "./mod-repeterui.js";
import { op_motif_depuis_selection, op_motif_regler, op_motif_contenu, motif_apercu, motifs_objets_liste, PAVAGES } from "./mod-motifs.js";
import { op_style, op_motif_supprimer, compilerSVG } from "./mod-doc.js";

const NOMS_PAVAGES = { grille: "vectorlab.motifs.p_grille", brique_lignes: "vectorlab.motifs.p_brique_lignes",
  brique_colonnes: "vectorlab.motifs.p_brique_colonnes", hexagone: "vectorlab.motifs.p_hexagone" };
const _esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export function champs_motif(m = {}) {
  const e = m.espacement || {};
  const fond = m.fond && m.fond !== "none" && /^#/.test(m.fond) ? m.fond : null;
  const nb = (id, lib, valeur) => ({ id, type: "nombre", libelle: T(lib), valeur, min: -1000, max: 10000, pas: 1 });
  return [
    { id: "pavage", type: "choix", valeur: m.pavage || "grille", options: PAVAGES.map((p) => [p, T(NOMS_PAVAGES[p])]) },
    nb("eh", "vectorlab.motifs.c_eh", +e.h || 0), nb("ev", "vectorlab.motifs.c_ev", +e.v || 0),
    { id: "fond_actif", type: "case", libelle: T("vectorlab.motifs.c_fond_actif"), valeur: !!fond },
    { id: "fond", type: "couleur", libelle: T("vectorlab.motifs.c_fond"), valeur: fond || "#ffffff" }];
}
export function opts_formulaire(v) {
  return { pavage: v.pavage, espacement: { h: +v.eh || 0, v: +v.ev || 0 }, fond: v.fond_actif ? v.fond : "none" };
}
// une vignette 64 × 40 remplie du motif (le document lui prête ses motifs, dégradés et couleurs globales)
export function motif_vignette(doc, id) {
  const mini = { v: 1, taille: { w: 64, h: 40 }, motifs: doc.motifs, degrades: doc.degrades, couleursGlobales: doc.couleursGlobales,
    calques: [{ id: "c", nom: "c", visible: true, verrou: false, objets: [{ id: "r", type: "rect", x: 0, y: 0, w: 64, h: 40, style: { fond: "motif:" + id } }] }] };
  try { return compilerSVG(mini); } catch { return ""; }
}

// la liste : { titre, motifs: [{ id, pavage, objets, usages, vignette }] } → Promise({ action, id } | null)
export function dialogue_liste_dom(spec) {
  return new Promise((resoudre) => {
    let hote = document.querySelector("#vlTracesDlg");
    if (!hote) { hote = document.createElement("div"); hote.id = "vlTracesDlg"; hote.className = "vl-dlg hidden"; document.body.appendChild(hote); }
    const bouton = (action, id, cle) => `<button data-action="${action}" data-id="${_esc(id)}">${_esc(T(cle))}</button>`;
    const ligne = (m) => `<div style="display:grid;grid-template-columns:64px 1fr;gap:10px;align-items:center">
      <span style="width:64px;height:40px;display:block;border:1px solid var(--vl-bord, #555);overflow:hidden">${m.vignette.replace(/<svg /, '<svg width="64" height="40" ')}</span>
      <div style="display:flex;flex-direction:column;gap:4px"><span><b>${_esc(m.id)}</b> · ${_esc(T(NOMS_PAVAGES[m.pavage] || NOMS_PAVAGES.grille))} · ${_esc(T("vectorlab.motifs.usages", { n: m.usages }))}</span>
      <span style="display:flex;gap:6px;flex-wrap:wrap">${bouton("appliquer", m.id, "vectorlab.motifs.appliquer")}${bouton("regler", m.id, "vectorlab.motifs.regler")}${bouton("remplacer", m.id, "vectorlab.motifs.remplacer")}${bouton("supprimer", m.id, "vectorlab.motifs.supprimer")}</span></div></div>`;
    hote.innerHTML = `<div class="vl-dlg-boite vl-dlg-petite" role="dialog" aria-modal="true" aria-label="${_esc(spec.titre)}">
      <div class="vl-dlg-tete"><b>${_esc(spec.titre)}</b></div>
      <div class="vl-dlg-corps" style="display:flex;flex-direction:column;gap:10px;max-height:420px;overflow:auto">${spec.motifs.map(ligne).join("")}</div>
      <div class="vl-dlg-pied"><button data-role="fermer" class="vl-dlg-defaut">${_esc(T("vectorlab.motifs.fermer"))}</button></div></div>`;
    const fin = (v) => { hote.classList.add("hidden"); hote.innerHTML = ""; document.removeEventListener("keydown", touche, true); resoudre(v); };
    const touche = (ev) => { if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); fin(null); } };
    hote.querySelectorAll("[data-action]").forEach((b) => b.addEventListener("click", () => fin({ action: b.dataset.action, id: b.dataset.id })));
    hote.querySelector('[data-role="fermer"]').addEventListener("click", () => fin(null));
    document.addEventListener("keydown", touche, true);
    hote.classList.remove("hidden");
    hote.querySelector('[data-role="fermer"]').focus();
  });
}

export function motifs_actions(VL) {
  const etat = VL.etat;
  const sel = () => (etat.doc ? (etat.selection || []).slice() : []);
  const A = { demander: (spec) => formulaire_dom(spec), demanderListe: (spec) => dialogue_liste_dom(spec) };
  const dialogue = (spec, appliquer) => dialogue_apercu(VL, (s) => A.demander(s), spec, appliquer);
  const ACTIONS = {
    motif_creer: { peut: () => sel().length >= 1, faire: async () => {
      const ids = sel();
      const v = await dialogue({ titre: T("vectorlab.motifs.d_creer"), champs: champs_motif() }, (d, x) => motif_apercu(d, ids, opts_formulaire(x)));
      if (!v) return;
      const id = VL.executer(op_motif_depuis_selection, ids, opts_formulaire(v));
      if (id) VL.toast(T("vectorlab.motifs.cree", { id }));
    } },
    motifs: { peut: () => !!etat.doc, faire: async () => {
      const liste = motifs_objets_liste(etat.doc);
      if (!liste.length) { VL.toast(T("vectorlab.motifs.aucun"), true); return; }
      const r = await A.demanderListe({ titre: T("vectorlab.motifs.d_liste"), motifs: liste.map((m) => ({ ...m, vignette: motif_vignette(etat.doc, m.id) })) });
      if (!r) return;
      const ids = sel();
      if (r.action === "appliquer") {
        if (!ids.length) { VL.toast(T("vectorlab.motifs.selection_requise"), true); return; }
        VL.executer(op_style, ids, { fond: "motif:" + r.id });
      } else if (r.action === "regler") {
        const m = etat.doc.motifs[r.id];
        const v = await dialogue({ titre: T("vectorlab.motifs.d_regler", { id: r.id }), champs: champs_motif(m) }, (d, x) => op_motif_regler(d, r.id, opts_formulaire(x)));
        if (v) VL.executer(op_motif_regler, r.id, opts_formulaire(v));
      } else if (r.action === "remplacer") {
        VL.executer(op_motif_contenu, r.id, ids);
      } else if (r.action === "supprimer") {
        VL.executer(op_motif_supprimer, r.id);
      }
    } },
  };
  A.action = (nom) => ACTIONS[nom] || null;
  return A;
}

export function initMotifsUI(VL) {
  VL.motifsUI = motifs_actions(VL);
  return VL.motifsUI;
}
