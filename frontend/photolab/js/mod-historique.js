// mod-historique.js — le panneau Historique (C2) : la liste des états APPLIQUÉS (doc.inspect.history ; le moteur fait
// disparaître les états annulés), le dernier en accent ; clic sur un état antérieur = N annulations en UNE requête
// (/historique {annuler: N}, le moteur n'a aucun saut direct) ; boutons annuler / rétablir.
// Fonctions PURES exportées (qa/panneaux.test.mjs).

export function etatsHistorique(history, canRedo = false) {
  const h = Array.isArray(history) ? history : [];
  return h.map((nom, index) => ({ index, nom: String(nom), courant: index === h.length - 1, canRedo: !!canRedo }));
}

// Clic sur l'état k parmi n appliqués -> n-1-k annulations (0 = l'état courant ou un index hors liste).
export function annulationsPour(k, history) {
  const n = Array.isArray(history) ? history.length : 0;
  if (!Number.isInteger(k) || k < 0 || k >= n) return 0;
  return n - 1 - k;
}

// /historique accepte 1..100 par requête : un saut plus long part en tranches de 100 (237 -> 100, 100, 37).
export function tranches(n, max = 100) {
  const t = [];
  for (let r = Math.max(0, Math.floor(n)); r > 0; r -= max) t.push(Math.min(max, r));
  return t;
}

// Les états portent le nom anglais de la commande (« Gaussian Blur », « New Layer »). En français, on reprend le
// libellé du catalogue des menus quand il existe (sans « … ») ; sinon le nom du moteur tel quel.
export function tableEtats(catalogue) {
  const t = new Map();
  for (const e of (catalogue && catalogue.entrees) || []) {
    if (!e.libelle_en || !e.libelle_fr) continue;
    const en = e.libelle_en.replace(/…$/, "").trim();
    if (!t.has(en)) t.set(en, e.libelle_fr.replace(/…$/, "").trim());
  }
  return t;
}
// Noms d'états que les commandes du P2 font naître dans le moteur (relevés dans les sources photocraft 0.3.0 :
// s.edit("…") de crates/engine/src/commands.rs, edit_cmds.rs, selection_cmds.rs, smartselect_cmds.rs,
// layer_multi_cmds.rs, image_cmds.rs, transform_cmds.rs, fill_cmds.rs, brush_cmds.rs) -> clé du dictionnaire.
// Les clés existantes sont réutilisées quand le français est le même (outils, boutons du panneau Calques).
export const ETATS_MOTEUR = {
  "Open": "photolab.histo.open",
  "New": "photolab.histo.new",
  "Rectangular Marquee": "photolab.outil.rect_marquee",
  "Elliptical Marquee": "photolab.outil.ellipse_marquee",
  "Lasso": "photolab.outil.lasso",
  "Polygonal Lasso": "photolab.outil.polygon_lasso",
  "Magic Wand": "photolab.outil.magic_wand",
  "Quick Selection": "photolab.outil.quick_selection",
  "Deselect": "photolab.histo.deselect",
  "Select All": "photolab.histo.select_all",
  "Inverse": "photolab.histo.inverse",
  "Reselect": "photolab.histo.reselect",
  "Layer Via Copy": "photolab.histo.layer_via_copy",
  "Layer Via Cut": "photolab.histo.layer_via_cut",
  "New Layer": "photolab.calques.nouveau",
  "New Group": "photolab.calques.nouveau_groupe",
  "Duplicate Layer": "photolab.calques.dupliquer",
  "Duplicate Layers": "photolab.histo.duplicate_layers",
  "Delete Layer": "photolab.calques.supprimer",
  "Delete Layers": "photolab.histo.delete_layers",
  "Merge Down": "photolab.histo.merge_down",
  "Group Layers": "photolab.histo.group_layers",
  "Reorder Layers": "photolab.histo.reorder_layers",
  "Layer Properties": "photolab.histo.layer_properties",
  "Layer Visibility": "photolab.histo.layer_visibility",
  "Show Layers": "photolab.histo.show_layers",
  "Hide Layers": "photolab.histo.hide_layers",
  "Lock Layers": "photolab.histo.lock_layers",
  "Rename Layer": "photolab.histo.rename_layer",
  "Move": "photolab.outil.move",
  "Free Transform": "photolab.histo.free_transform",
  "Crop": "photolab.outil.crop",
  "Invert": "photolab.histo.invert",
  "Fill": "photolab.histo.fill",
  "Clear": "photolab.histo.clear",
  "Brush Tool": "photolab.outil.brush",
};

// Ordre : carte ci-dessus (fr et en, par le dictionnaire) -> libellé du catalogue des menus (fr) -> nom du moteur.
export function traduireEtat(nom, table, t = null) {
  const cle = ETATS_MOTEUR[nom];
  if (cle && t) { const s = t(cle); if (s && s !== cle) return s; }
  return (table && table.get(nom)) || nom;
}

export function initHistorique(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const lang = () => (window.dzLang ? window.dzLang() : "fr");
  const corps = PL.$("#corpsHistorique");
  corps.textContent = "";
  const barre = document.createElement("div"); barre.className = "hi-barre";
  const bouton = (ico, cle) => {
    const b = document.createElement("button"); b.type = "button"; b.className = "hi-bouton";
    b.title = T(cle); b.setAttribute("aria-label", b.title); b.dataset.icone = ico;
    PL.icone(ico).then((svg) => { b.innerHTML = svg; });
    return b;
  };
  const bAnnuler = bouton("undo-2", "photolab.historique.annuler");
  const bRetablir = bouton("redo-2", "photolab.historique.retablir");
  barre.append(bAnnuler, bRetablir);
  const liste = document.createElement("ol"); liste.className = "hi-liste";
  corps.append(barre, liste);
  let table = null;
  if (lang() === "fr") fetch("donnees/menus.json").then((r) => r.json()).then((c) => { table = tableEtats(c); dessiner(PL.etat.doc); }).catch(() => {});

  // Même chemin que Ctrl+Z / Ctrl+Maj+Z (mod-cycle : cumul, file FIFO, tranches de 100).
  bAnnuler.addEventListener("click", () => PL.historique(-1));
  bRetablir.addEventListener("click", () => PL.historique(1));

  function dessiner(doc) {
    liste.textContent = "";
    bAnnuler.disabled = !(doc && doc.canUndo);
    bRetablir.disabled = !(doc && doc.canRedo);
    if (!doc) return;
    const h = doc.history || [];
    for (const e of etatsHistorique(h, doc.canRedo)) {
      const li = document.createElement("li");
      li.className = "hi-etat" + (e.courant ? " courant" : "");
      li.textContent = traduireEtat(e.nom, table, T);
      li.title = e.nom;
      li.addEventListener("click", () => {
        const n = annulationsPour(e.index, h);
        if (n > 0) PL.historique(-n);
      });
      liste.appendChild(li);
    }
    const dernier = liste.lastElementChild;
    if (dernier && !corps.hidden) dernier.scrollIntoView({ block: "nearest" });
  }
  PL.surDoc.push(dessiner);
  dessiner(null);
}
