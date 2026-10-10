// mod-compositions.js — t153 (parité L3) : le panneau Compositions de calques, onglet du groupe Propriétés.
// Liste lue par layerComp.list (hors historique ; doc.inspect.layerComps ne donne que id et nom) : « Dernier état du
// document » en tête (layerComp.restoreLastDocumentState, permis seulement quand une composition est appliquée), puis
// chaque composition : case d'application (layerComp.apply), avertissement des calques manquants
// (layerComp.updateWarnings {clear}), nom (double-clic = layerComp.rename ; le commentaire en bulle), trois options
// visibilité / position / apparence (layerComp.setOptions). Pied : précédente, suivante, mettre à jour, nouvelle
// (dialogue : nom, options, commentaire), supprimer. Fonctions PURES exportées (qa/panneaux3.test.mjs).
import { ouvrirDialogue } from "./mod-fichier.js";
import { demanderNom } from "./mod-nommer.js";

export const OPTIONS = [
  { cle: "visibility", icone: "dz-etat-visible", lib: "photolab.compositions.visibilite" },
  { cle: "position", icone: "dz-outil-photo-deplacer", lib: "photolab.compositions.position" },
  { cle: "appearance", icone: "dz-edit-effet", lib: "photolab.compositions.apparence" },
];

// Réponse de layerComp.list -> {dernierEtat: {coche, actif}, lignes: [{id, nom, commentaire, appliquee, manquants,
// visibility, position, appearance}]}.
export function lignesCompositions(r) {
  const comps = (r && Array.isArray(r.comps)) ? r.comps : [];
  const appliquee = r ? r.lastApplied : null;
  return {
    dernierEtat: { coche: appliquee == null, actif: appliquee != null && !!(r && r.hasLastDocumentState) },
    lignes: comps.map((c) => ({ id: c.id, nom: c.name, commentaire: c.comment || "", appliquee: c.id === appliquee,
      manquants: c.missingLayers || 0, visibility: !!c.visibility, position: !!c.position, appearance: !!c.appearance })),
  };
}
// La composition visée par Mettre à jour / Supprimer : la sélection du panneau, sinon la dernière appliquée (amont).
export const cible = (sel, r) => (sel != null && (r.comps || []).some((c) => c.id === sel) ? sel : r && r.lastApplied != null ? r.lastApplied : null);
// Paramètres de layerComp.new d'après le dialogue (nom vide -> nom du moteur « Layer Comp N »).
export function paramsNouvelle(saisie) {
  const p = { visibility: !!saisie.visibility, position: !!saisie.position, appearance: !!saisie.appearance };
  const nom = String(saisie.nom || "").trim();
  if (nom) p.name = nom.slice(0, 64);
  const com = String(saisie.commentaire || "").trim();
  if (com) p.comment = com.slice(0, 500);
  return p;
}

export function initCompositions(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const corps = PL.$("#corpsCompositions");
  if (!corps) return;
  const liste = document.createElement("div"); liste.className = "cmp-liste";
  const pied = document.createElement("div"); pied.className = "pr-pied";
  corps.append(liste, pied);
  let r = null, sel = null, revLue = null;
  const bouton = (icone, cle, fn, gauche) => {
    const b = document.createElement("button"); b.type = "button"; b.className = "pr-btn" + (gauche ? " gauche" : ""); b.dataset.icone = icone;
    b.title = T(cle); b.setAttribute("aria-label", b.title); b.addEventListener("click", fn); pied.appendChild(b); return b;
  };
  const exec = (c, p = {}) => PL.executer(c, p).then(() => relire(true));
  const bPrec = bouton("dz-action-element-precedent", "photolab.compositions.precedente", () => exec("layerComp.previous"), true);
  const bSuiv = bouton("dz-action-element-suivant", "photolab.compositions.suivante", () => exec("layerComp.next"), true);
  const bMaj = bouton("dz-action-redefinir", "photolab.compositions.mettre_a_jour", () => { const c = cible(sel, r || {}); if (c != null) exec("layerComp.update", { comp: c }); });
  bouton("dz-action-ajouter", "photolab.compositions.nouvelle", nouvelle);
  const bSuppr = bouton("dz-action-supprimer", "photolab.compositions.supprimer", () => { const c = cible(sel, r || {}); if (c != null) { sel = null; exec("layerComp.delete", { comp: c }); } });
  if (PL.hydraterIcones) PL.hydraterIcones(pied);

  function nouvelle() {
    if (!PL.etat.doc) return;
    const s = { nom: "", visibility: true, position: true, appearance: true, commentaire: "" };
    ouvrirDialogue(PL, { titre: T("photolab.compositions.nouvelle_titre"), classe: "cmp-dlg",
      construire: ({ corps: c }) => {
        const champ = (lib, el) => { const l = document.createElement("label"); l.className = "cmp-champ"; const sp = document.createElement("span"); sp.textContent = lib; l.append(sp, el); c.appendChild(l); return el; };
        const nom = champ(T("photolab.compositions.nom"), Object.assign(document.createElement("input"), { type: "text", maxLength: 64 }));
        nom.setAttribute("data-dz-brut", ""); nom.addEventListener("input", () => { s.nom = nom.value; });
        setTimeout(() => nom.focus(), 0);
        const p = document.createElement("p"); p.className = "cmp-sous"; p.textContent = T("photolab.compositions.appliquer_a"); c.appendChild(p);
        for (const o of OPTIONS) {
          const cb = Object.assign(document.createElement("input"), { type: "checkbox", checked: true });
          const l = document.createElement("label"); l.className = "cmp-case"; l.append(cb, document.createTextNode(" " + T(o.lib)));
          cb.addEventListener("change", () => { s[o.cle] = cb.checked; }); c.appendChild(l);
        }
        const com = champ(T("photolab.compositions.commentaire"), Object.assign(document.createElement("textarea"), { rows: 3, maxLength: 500 }));
        com.setAttribute("data-dz-brut", ""); com.addEventListener("input", () => { s.commentaire = com.value; });
      },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }],
    }).then(async (role) => {
      if (role !== "ok") return;
      const res = await PL.executer("layerComp.new", paramsNouvelle(s));
      if (res && res.ok && res.r && res.r.comp != null) sel = res.r.comp;
      relire(true);
    });
  }

  function dessiner() {
    liste.textContent = "";
    const d = PL.etat.doc;
    if (!d) { [bPrec, bSuiv, bMaj, bSuppr].forEach((b) => { b.disabled = true; }); return; }
    const v = lignesCompositions(r);
    const tete = document.createElement("div"); tete.className = "cmp-ligne cmp-dernier";
    const caseD = document.createElement("button"); caseD.type = "button"; caseD.className = "cmp-case-app" + (v.dernierEtat.coche ? " coche" : "");
    caseD.setAttribute("aria-label", T("photolab.compositions.dernier_etat")); caseD.disabled = !v.dernierEtat.actif;
    caseD.addEventListener("click", () => exec("layerComp.restoreLastDocumentState"));
    const nomD = document.createElement("span"); nomD.className = "cmp-nom"; nomD.textContent = T("photolab.compositions.dernier_etat");
    tete.append(caseD, nomD);
    liste.appendChild(tete);
    if (!v.lignes.length) {
      const p = document.createElement("p"); p.className = "cmp-vide"; p.textContent = T("photolab.compositions.vide"); liste.appendChild(p);
    }
    for (const l of v.lignes) {
      const row = document.createElement("div"); row.className = "cmp-ligne" + (sel === l.id ? " choisie" : "");
      row.dataset.comp = String(l.id);
      const caseA = document.createElement("button"); caseA.type = "button"; caseA.className = "cmp-case-app" + (l.appliquee ? " coche" : "");
      caseA.setAttribute("aria-label", T("photolab.compositions.appliquer"));
      caseA.addEventListener("click", (ev) => { ev.stopPropagation(); sel = l.id; exec("layerComp.apply", { comp: l.id }); });
      const alerte = document.createElement("button"); alerte.type = "button"; alerte.className = "cmp-alerte"; alerte.innerHTML = PL.icone("dz-etat-avertissement");
      alerte.hidden = !l.manquants; alerte.title = T("photolab.compositions.manquants", { n: l.manquants }); alerte.setAttribute("aria-label", alerte.title);
      alerte.addEventListener("click", (ev) => { ev.stopPropagation(); exec("layerComp.updateWarnings", { clear: true }); });
      const nom = document.createElement("span"); nom.className = "cmp-nom"; nom.textContent = l.nom; nom.setAttribute("data-dz-brut", "");
      if (l.commentaire) { nom.title = l.commentaire; }
      const opts = document.createElement("span"); opts.className = "cmp-options";
      for (const o of OPTIONS) {
        const b = document.createElement("button"); b.type = "button"; b.className = "cmp-opt" + (l[o.cle] ? " actif" : ""); b.dataset.icone = o.icone;
        b.title = T(o.lib); b.setAttribute("aria-label", b.title); b.setAttribute("aria-pressed", l[o.cle] ? "true" : "false");
        b.addEventListener("click", (ev) => { ev.stopPropagation(); exec("layerComp.setOptions", { comp: l.id, [o.cle]: !l[o.cle] }); });
        opts.appendChild(b);
      }
      row.append(caseA, alerte, nom, opts);
      row.addEventListener("click", () => { sel = l.id; dessiner(); });
      row.addEventListener("dblclick", async () => {
        const n = await demanderNom(PL, T("commun.action.renommer"), l.nom);
        if (n) exec("layerComp.rename", { comp: l.id, name: n });
      });
      liste.appendChild(row);
    }
    if (PL.hydraterIcones) PL.hydraterIcones(liste);
    const n = v.lignes.length;
    bPrec.disabled = bSuiv.disabled = !n;
    bMaj.disabled = bSuppr.disabled = cible(sel, r || {}) == null;
  }
  async function relire(force = false) {
    const d = PL.etat.doc;
    if (!d) { r = null; revLue = null; dessiner(); return; }
    if (!force && (revLue === d.revision || !corps.offsetParent)) { dessiner(); return; }
    revLue = d.revision;
    try { r = await PL.post("/executer", { command: "layerComp.list", params: {} }); } catch (e) { r = null; }
    dessiner();
  }
  PL.surDoc.push(() => relire());
  PL.compositions = { relire: () => relire(true), etat: () => r };
}
