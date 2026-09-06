// mod-layers.js — le panneau des calques (T1.4 côté UI). L'ordre du tableau
// est l'ordre de peinture : le panneau s'affiche INVERSÉ (le dessus en
// haut). Toute mutation passe par les commandes pures via VL.executer.
import { op_calque_ajouter, op_calque_renommer, op_calque_reordonner,
         op_calque_visible, op_calque_verrou, op_calque_supprimer,
         op_calque_opacite } from "./mod-doc.js";

export function initCalques(VL) {
  const { $, etat } = VL;

  function rendreCalques() {
    const hote = $("#listeCalques");
    if (!hote || !etat.doc) return;
    const lignes = [...etat.doc.calques].reverse().map((c) => `
      <div class="calque${c.id === etat.calqueActif ? " actif" : ""}"
           data-calque="${c.id}"
           title="Clic : calque actif · double-clic sur le nom : renommer">
        <button data-act="oeil" class="${c.visible ? "" : "off"}"
                title="Visibilité">👁</button>
        <button data-act="verrou" class="${c.verrou ? "" : "off"}"
                title="Verrou">🔒</button>
        <span class="nom">${c.nom || c.id}</span>
        <input type="number" class="op" data-act="opacite" min="0" max="100"
               value="${Math.round((c.opacite ?? 1) * 100)}"
               title="Opacité du calque (%)"/>
        <button data-act="monter" title="Monter d'un cran">▲</button>
        <button data-act="descendre" title="Descendre d'un cran">▼</button>
        <button data-act="poubelle" title="Supprimer le calque et ses objets">🗑</button>
      </div>`).join("");
    // §8.5 du handoff Vectorlab : document sans le moindre objet — le
    // texte d'amorce et « Poser une baie d'exemple » (VL.vitrailExemple,
    // câblé par délégation plus bas).
    const vide = etat.doc.calques.every((c) => !c.objets.length);
    hote.innerHTML = lignes + (vide ? `
      <div class="vl-amorce">Document vide. Choisir un motif dans le
      panneau Vitrail, puis tracer la baie sur la page.</div>
      <button class="vl-amorce-btn" data-act="exemple"
        title="Pose une baie à arc aux proportions de la démo — un seul geste, annulable">Poser une baie d'exemple</button>` : "");
  }

  $("#listeCalques").addEventListener("dblclick", (ev) => {
    const ligne = ev.target.closest(".calque");
    if (!ligne || !ev.target.classList.contains("nom")) return;
    const id = ligne.dataset.calque;
    const c = etat.doc.calques.find((x) => x.id === id);
    const nom = prompt("Nom du calque :", c ? c.nom : "");
    if (nom !== null) VL.executer(op_calque_renommer, id, nom);
  });

  $("#listeCalques").addEventListener("change", (ev) => {
    const ligne = ev.target.closest(".calque");
    if (!ligne || ev.target.dataset.act !== "opacite") return;
    VL.executer(op_calque_opacite, ligne.dataset.calque,
                Math.max(0, Math.min(100, +ev.target.value)) / 100);
  });

  $("#listeCalques").addEventListener("click", (ev) => {
    if (ev.target.dataset.act === "exemple") {
      if (VL.vitrailExemple) VL.vitrailExemple();
      return;
    }
    const ligne = ev.target.closest(".calque");
    if (!ligne) return;
    if (ev.target.dataset.act === "opacite") return;   // l'input gère seul
    const id = ligne.dataset.calque;
    const act = ev.target.dataset.act;
    const c = etat.doc.calques.find((x) => x.id === id);
    if (!c) return;
    const i = etat.doc.calques.indexOf(c);
    if (act === "oeil") VL.executer(op_calque_visible, id, !c.visible);
    else if (act === "verrou") VL.executer(op_calque_verrou, id, !c.verrou);
    else if (act === "monter") {              // monter à l'écran = vers la fin
      VL.executer(op_calque_reordonner, id,
                  Math.min(etat.doc.calques.length - 1, i + 1));
    } else if (act === "descendre") {
      VL.executer(op_calque_reordonner, id, Math.max(0, i - 1));
    } else if (act === "poubelle") {
      if (confirm(`Supprimer le calque « ${c.nom} » et ses objets ?`)) {
        VL.executer(op_calque_supprimer, id);
        if (etat.calqueActif === id) {
          etat.calqueActif =
            etat.doc.calques[etat.doc.calques.length - 1].id;
          rendreCalques();
        }
      }
    } else {
      etat.calqueActif = id;
      rendreCalques();
    }
  });

  $("#btnCalquePlus").addEventListener("click", () => {
    const id = VL.executer(op_calque_ajouter,
                           "calque " + (etat.doc.calques.length + 1));
    if (id) { etat.calqueActif = id; rendreCalques(); }
  });

  const suivant = VL.surRendu;
  VL.surRendu = () => { suivant(); rendreCalques(); };
}
