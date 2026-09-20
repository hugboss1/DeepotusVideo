// mod-charpente.js — la charpente d'Affinity : barre de menus (mod-menus),
// onglet de document, barre d'état (mod-statut), cotes de la sélection,
// résumé du document, aide Raccourcis (F1). Traduit et délègue aux
// actions existantes (VL.*, VL.actions.<module>, boutons par id) — ne
// calcule rien : les données sont dans les deux modules feuilles.
import { MENUS_BARRE, menus_construire, raccourci_de } from "./mod-menus.js";
import { phrase_statut, statut_html, onglet_document, pagination } from "./mod-statut.js";
import { op_calque_supprimer, op_calque_renommer, op_calque_verrou, op_calque_visible, op_supprimer } from "./mod-doc.js";

export function initCharpente(VL) {
  const { $, etat } = VL;
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  const clic = (sel) => { const b = $(sel); if (!b || b.disabled) return false; b.click(); return true; };
  const A = () => VL.actions || {};
  const sel = () => etat.selection.length;
  const calqueActif = () => etat.doc && etat.doc.calques.find((x) => x.id === etat.calqueActif);
  const textesSel = () => etat.selection.filter((id) => { const t = VL.objetDe(id); return t && (t.objet.type === "texte" || t.objet.type === "cadre"); });
  // onglets de la pile : R3 pose VL.ouvrirOnglet ; en attendant, la section <details>
  const ouvrirOnglet = (nom) => { if (VL.ouvrirOnglet) return VL.ouvrirOnglet(nom); const d = $("#" + nom + "Details"); if (d) { d.open = true; d.scrollIntoView({ block: "start" }); } };

  /* ── la table des actions : nom → { peut(), faire(entree) } ── */
  const T = {
    biblio: { peut: () => true, faire: () => VL.ouvrirBiblio() },
    nouveau: { peut: () => true, faire: () => { VL.ouvrirBiblio(); setTimeout(() => { const n = $("#bibNouvNom"); if (n) n.focus(); }, 60); } },
    sauver: { peut: () => !!etat.doc, faire: () => VL.sauver() },
    brouillon: { peut: () => !!(etat.doc && VL.restaurerBrouillon), faire: () => VL.restaurerBrouillon() },
    imageFichier: { peut: () => !!(etat.doc && A().image), faire: () => A().image.fichier() },
    imageBiblio: { peut: () => !!(etat.doc && A().image), faire: () => A().image.biblio() },
    imageColler: { peut: () => !!(etat.doc && A().image), faire: () => A().image.coller() },
    imageGenerer: { peut: () => !!(etat.doc && A().image), faire: () => A().image.generer() },
    imageVectoriser: { peut: () => !!(etat.doc && A().image && A().image.vectoriser), faire: () => A().image.vectoriser() },
    gpx: { peut: () => !!etat.doc, faire: () => { ouvrirOnglet("carte"); clic("#carteGpxInput"); } },
    exporter: { peut: () => !!etat.doc, faire: () => ouvrirOnglet("exporter") },
    expSvg: { peut: () => !!etat.doc, faire: () => clic("#expSvg") },
    expPng2: { peut: () => !!etat.doc, faire: () => clic("#expPng2") },
    expPrint3d: { peut: () => !!etat.doc, faire: () => clic("#expPrint3d") },
    expBible: { peut: () => !!etat.doc, faire: () => clic("#expBible") },
    configDoc: { peut: () => !!etat.doc, faire: () => VL.configurerDocument ? VL.configurerDocument() : VL.toast("configuration du document : lot R5", true) },
    parametres: { peut: () => true, faire: () => VL.parametresAppli ? VL.parametresAppli() : VL.toast("paramètres de l'appli : lot R5", true) },
    annuler: { peut: () => !!etat.doc && etat.histo.peutAnnuler(), faire: () => VL.annuler() },
    refaire: { peut: () => !!etat.doc && etat.histo.peutRefaire(), faire: () => VL.refaire() },
    toutSelectionner: { peut: () => !!etat.doc, faire: () => VL.setSelection(etat.doc.calques.filter((c) => c.visible && !c.verrou).flatMap((c) => c.objets.map((o) => o.id))) },
    deselectionner: { peut: () => sel() > 0, faire: () => VL.setSelection([]) },
    selAttribut: { peut: () => sel() === 1, faire: () => ouvrirOnglet("transformer") },
    copier: { peut: () => sel() > 0, faire: () => VL.copierSelection() },
    coller: { peut: () => !!(etat.pressePapiers && etat.pressePapiers.ids.length), faire: () => VL.collerSelection() },
    dupliquer: { peut: () => sel() > 0, faire: () => VL.dupliquerSelection() },
    puissance: { peut: () => sel() > 0, faire: () => ouvrirOnglet("transformer") },
    supprimer: { peut: () => sel() > 0, faire: () => { VL.executer(op_supprimer, etat.selection.slice()); VL.setSelection([]); } },
    creerStyle: { peut: () => sel() === 1, faire: () => { ouvrirOnglet("apparence"); const n = $("#a2StNom"); if (n) n.focus(); } },
    instantane: { peut: () => !!etat.doc, faire: () => { ouvrirOnglet("historique"); const n = $("#insNom"); if (n) n.focus(); } },
    unite: { peut: () => !!etat.doc, faire: () => clic("#btnUnite") },
    ouvrir: { peut: () => true, faire: (x) => ouvrirOnglet(x.ouvre) },
    "outil:texte": { peut: () => !!etat.doc, faire: () => VL.setOutil("texte") },
    "flyout:texte": { peut: () => !!(etat.doc && VL.flyout), faire: () => VL.flyout.ouvrir("texte") },
    "flyout:forme": { peut: () => !!(etat.doc && VL.flyout), faire: () => VL.flyout.ouvrir("forme") },
    editerTexte: { peut: () => textesSel().length === 1 && !!VL.editerTexte, faire: () => VL.editerTexte(textesSel()[0]) },
    vectoriserTexte: { peut: () => textesSel().length >= 1 && !!VL.vectoriserTexte, faire: () => { for (const id of textesSel()) VL.vectoriserTexte(id); } },
    vectoriserGlyphes: { peut: () => textesSel().length === 1 && !!VL.vectoriserTexte, faire: () => VL.vectoriserTexte(textesSel()[0], undefined, true) },
    symboleCreer: { peut: () => sel() > 0 && !!VL.flyout, faire: () => VL.flyout.ouvrir("symbole") },
    grouper: { peut: () => sel() >= 2 && !!A().selection, faire: () => A().selection.grouper() },
    degrouper: { peut: () => !!(A().selection && A().selection.peut && A().selection.peut().groupe), faire: () => A().selection.degrouper() },
    pxEditer: { peut: () => !!etat.doc, faire: () => { VL.setPersona("pixel"); setTimeout(() => clic("#pxEditer"), 60); } },
    calqueNouveau: { peut: () => !!etat.doc, faire: () => clic("#btnCalquePlus") },
    calqueRenommer: { peut: () => !!calqueActif(), faire: async () => { const c = calqueActif(); const nom = await VL.dialogue.saisir("Nom du calque :", { valeur: c.nom || "", titre: "Renommer le calque", valider: "Renommer" }); if (nom !== null) VL.executer(op_calque_renommer, c.id, nom); } },
    calqueSupprimer: { peut: () => !!(etat.doc && etat.doc.calques.length > 1 && calqueActif()), faire: async () => { const c = calqueActif(); if (await VL.dialogue.confirmer(`Supprimer le calque « ${c.nom} » et ses objets ?`, { ok: "Supprimer", danger: true })) { VL.executer(op_calque_supprimer, c.id); if (!calqueActif()) { etat.calqueActif = etat.doc.calques[etat.doc.calques.length - 1].id; VL.rendre(); } } } },
    calqueVerrou: { peut: () => !!calqueActif(), faire: () => { const c = calqueActif(); VL.executer(op_calque_verrou, c.id, !c.verrou); } },
    calqueOeil: { peut: () => !!calqueActif(), faire: () => { const c = calqueActif(); VL.executer(op_calque_visible, c.id, !c.visible); } },
    zoomAjuster: { peut: () => !!etat.doc, faire: () => VL.zoomAjuster() },
    zoomCent: { peut: () => !!etat.doc, faire: () => VL.zoomCent() },
    grille: { peut: () => true, faire: () => clic("#btnGrille") },
    aimant: { peut: () => true, faire: () => clic("#btnAimant") },
    raccourcis: { peut: () => true, faire: () => ouvrirRaccourcis() },
    guide: { peut: () => true, faire: () => window.open("/guide/", "_blank") },
    apropos: { peut: () => true, faire: () => VL.toast("Vectorlab — Deepotus Video Gen : éditeur vectoriel et raster, charpente Affinity") },
  };
  function resoudre(action) {
    if (T[action]) return T[action];
    const [pre, arg] = String(action).split(":");
    const S = () => A().selection, N = () => A().noeuds, P = () => A().pixel;
    if (pre === "bool") return { peut: () => sel() >= 2 && !!S(), faire: () => S().booleen(arg) };
    if (pre === "ordre") return { peut: () => sel() >= 1 && !!S(), faire: () => S().ordre(arg) };
    if (pre === "noeuds") return { peut: () => { const n = N(); if (!n || !n.peut) return false; const p = n.peut(); return arg === "joindre" ? !!p.deux : arg === "diviser" ? !!p.ancre : arg === "inverser" ? !!p.chemin : !!p.sel; }, faire: () => N()[arg]() };
    if (pre === "pixel") return { peut: () => !!(P() && etat.px && etat.px.id), faire: () => P()[arg]() };
    if (pre === "persona") return { peut: () => !!VL.setPersona, faire: () => VL.setPersona(arg) };
    return { peut: () => false, faire: () => {} };
  }
  VL.menuAction = (nom, entree) => { const r = resoudre(nom); if (!r.peut(entree || {})) return false; r.faire(entree || {}); return true; };   // la preuve et les menus
  VL.menuPeut = (nom, entree) => resoudre(nom).peut(entree || {});

  /* ── la barre de menus ── */
  const mb = $("#menubar");
  let ouvert = null, ouvertPour = null;
  function fermer() { if (ouvert) { ouvert.remove(); ouvert = null; ouvertPour = null; } mb.querySelectorAll(".mb-titre.actif").forEach((b) => b.classList.remove("actif")); }
  function ouvrirMenu(titreEl, m) {
    fermer();
    titreEl.classList.add("actif");
    const menu = menus_construire([m], (a, x) => resoudre(a).peut(x))[0];
    const d = document.createElement("div");
    d.className = "mb-menu"; d.dataset.menu = m.titre;
    d.innerHTML = menu.entrees.map((x, i) => x === "-" ? `<hr/>` : `<button class="mb-item" data-i="${i}" data-id="${esc(x.id)}" ${x.desactive ? "disabled" : ""}><span>${esc(x.libelle)}</span><small>${esc(raccourci_de(x))}</small></button>`).join("");
    d.querySelectorAll(".mb-item").forEach((b) => b.addEventListener("click", () => { const x = menu.entrees[+b.dataset.i]; fermer(); resoudre(x.action).faire(x); }));
    const r = titreEl.getBoundingClientRect();
    d.style.left = r.left + "px"; d.style.top = r.bottom + "px";
    document.body.appendChild(d); ouvert = d; ouvertPour = titreEl;
  }
  if (mb) {
    mb.innerHTML = MENUS_BARRE.map((m, i) => `<button class="mb-titre" data-i="${i}">${esc(m.titre)}</button>`).join("");
    mb.querySelectorAll(".mb-titre").forEach((b) => {
      b.addEventListener("click", (ev) => { ev.stopPropagation(); if (ouvertPour === b) fermer(); else ouvrirMenu(b, MENUS_BARRE[+b.dataset.i]); });
      b.addEventListener("pointerenter", () => { if (ouvert && ouvertPour !== b) ouvrirMenu(b, MENUS_BARRE[+b.dataset.i]); });
    });
    document.addEventListener("pointerdown", (ev) => { if (ouvert && !ouvert.contains(ev.target) && !mb.contains(ev.target)) fermer(); }, true);
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && ouvert) { fermer(); ev.stopImmediatePropagation(); } }, true);
  }
  VL.menus = { ouvrir: (titre) => { const i = MENUS_BARRE.findIndex((m) => m.titre === titre); if (i < 0) return false; ouvrirMenu(mb.querySelectorAll(".mb-titre")[i], MENUS_BARRE[i]); return true; }, fermer, element: () => ouvert };   // la preuve

  /* ── l'aide Raccourcis (F1) : construite depuis les menus ── */
  function ouvrirRaccourcis() {
    let dlg = $("#raccDlg");
    if (!dlg) { dlg = document.createElement("div"); dlg.id = "raccDlg"; dlg.className = "vl-dlg"; document.body.appendChild(dlg); }
    const lignes = MENUS_BARRE.flatMap((m) => m.entrees.filter((x) => x !== "-" && x.raccourci).map((x) => `<tr><td>${esc(m.titre)}</td><td>${esc(x.libelle)}</td><td><kbd>${esc(raccourci_de(x))}</kbd></td></tr>`)).join("");
    const outils = [["V", "Déplacer"], ["P", "Plume"], ["B", "Crayon"], ["J", "Pinceau vectoriel"], ["R", "Rectangle"], ["E", "Ellipse"], ["L", "Ligne"], ["F", "Forme"], ["N", "Nœuds"], ["C", "Coin"], ["X", "Couteau"], ["W", "Gomme"], ["S", "Shape Builder"], ["T", "Texte"], ["M", "Mesure"], ["I", "Pipette"], ["K", "Tuiles"], ["G", "Grille"], ["Espace", "Main (panoramique)"], ["Ctrl+0", "Zoom : ajuster"], ["Ctrl+1", "Zoom : 100 %"]].map(([k, l]) => `<tr><td>Outils</td><td>${l}</td><td><kbd>${k}</kbd></td></tr>`).join("");
    dlg.innerHTML = `<div class="vl-dlg-boite racc-boite"><div class="vl-dlg-tete"><b>Raccourcis clavier</b><span class="spacer"></span><button id="raccFermer" title="Fermer">✕</button></div><div class="racc-corps"><table>${lignes}${outils}</table></div></div>`;
    dlg.classList.remove("hidden");
    $("#raccFermer").addEventListener("click", () => dlg.classList.add("hidden"));
    dlg.addEventListener("click", (ev) => { if (ev.target === dlg) dlg.classList.add("hidden"); });
  }
  const ba = $("#btnAide"); if (ba) ba.addEventListener("click", ouvrirRaccourcis);
  document.addEventListener("keydown", (ev) => { if (ev.key === "F1") { ouvrirRaccourcis(); ev.preventDefault(); } });

  /* ── onglet de document, résumé, cotes, pagination ── */
  function majOnglet() {
    const t = $("#docTitle"); if (t) t.textContent = onglet_document(etat.meta, etat.zoom, etat.sale);
    const d = etat.doc, pd = $("#pbDoc"), pc = $("#pbCotes"), sp = $("#sbPages");
    if (pd) { const u = VL.unites(); pd.textContent = d ? `${d.taille.w} × ${d.taille.h}px, ${(d.taille.w * d.taille.h / 1e6).toFixed(2)}MP, ${u.affichage} · ${u.dpi} dpi` : ""; }
    if (pc) { const b = d && etat.selection.length ? VL.bboxSelectionDoc() : null; pc.textContent = b ? VL.cote("rect", { w: b.w, h: b.h }) : "Pas de données"; }   /* libelle_mesure ne connaît que rect / ellipse / segment / delta */
    if (sp) sp.textContent = `|◀ ◀ ${pagination(d ? d.planches : [], etat.plancheCourante)} ▶ ▶|`;
  }
  VL.majStatut = () => { const h = $("#hintOutil"); if (!h) return; h.innerHTML = statut_html(phrase_statut(etat.outil, etat.selection.length, VL.hints || {})); };
  const sRendu = VL.surRendu, sSel = VL.surSelection, sOutil = VL.surOutil, sVue = VL.surVue;
  VL.surRendu = () => { sRendu(); majOnglet(); };
  VL.surSelection = () => { sSel(); majOnglet(); VL.majStatut(); };
  VL.surOutil = () => { sOutil(); VL.majStatut(); };
  VL.surVue = () => { sVue(); majOnglet(); };
  majOnglet(); VL.majStatut();
}
