// mod-layers.js — le panneau des calques (T1.4 côté UI). L'ordre du tableau
// est l'ordre de peinture : le panneau s'affiche INVERSÉ (le dessus en
// haut). Toute mutation passe par les commandes pures via VL.executer.
// Relooking Affinity (R3, 18/09) : tête « Opacité · Normal » sur le calque
// actif (mode de fusion de calque), rangée [chevron][vignette][nom][🔒][👁],
// barre d'actions en bas (renommer, réglage, masque, calque pixel, FX |
// groupe, nouveau, monter, descendre, supprimer). Les data-act restent.
import { op_calque_ajouter, op_calque_renommer, op_calque_reordonner,
         op_calque_visible, op_calque_verrou, op_calque_supprimer,
         op_calque_opacite, op_calque_fusion, MODES_FUSION_CALQUE, compilerSVG } from "./mod-doc.js";

/* ── la MINIATURE d'un calque (pure) : le document compilé avec ce seul
   calque visible, sans fond de page, ajusté dans une boîte w×h sur un
   damier ; les data-objet / data-calque sont retirés (aucun hit-testing
   dans une vignette) et les ids de defs préfixés pour ne pas entrer en
   conflit avec le canevas. Un calque inconnu → chaîne vide. */
export function vignette_calque_svg(doc, calqueId, w = 40, h = 28, image) {
  if (!doc || !(doc.calques || []).some((c) => c.id === calqueId)) return "";
  const d = JSON.parse(JSON.stringify(doc));
  delete d.fond;
  // les autres calques sont RETIRÉS (cachés, ils seraient compilés en display:none)
  d.calques = d.calques.filter((c) => c.id === calqueId);
  for (const c of d.calques) { c.visible = true; delete c.opacite; delete c.fusion; }
  let svg;
  try { svg = compilerSVG(d, { image }); } catch (e) { return ""; }
  const pre = `v${String(calqueId).replace(/[^A-Za-z0-9_-]/g, "")}_`;
  svg = svg.replace(/ data-objet="[^"]*"/g, "").replace(/ data-calque="[^"]*"/g, "").replace(/ data-nom="[^"]*"/g, "")
           .replace(/ id="([^"]+)"/g, ` id="${pre}$1"`).replace(/url\(#([^)]+)\)/g, `url(#${pre}$1)`).replace(/href="#([^"]+)"/g, `href="#${pre}$1"`);
  const damier = `<defs><pattern id="${pre}damier" width="8" height="8" patternUnits="userSpaceOnUse" patternContentUnits="userSpaceOnUse"><rect width="8" height="8" fill="#20242d"/><rect width="4" height="4" fill="#2b303b"/><rect x="4" y="4" width="4" height="4" fill="#2b303b"/></pattern></defs><rect x="0" y="0" width="${+d.taille.w}" height="${+d.taille.h}" fill="url(#${pre}damier)" data-damier="1"/>`;
  return svg.replace(/^<svg([^>]*) width="[^"]*" height="[^"]*">/, (m, attrs) => `<svg${attrs} width="${w}" height="${h}" preserveAspectRatio="xMidYMid meet">` + damier);
}

const LIB_FUSION = { normal: "Normal", multiply: "Produit", screen: "Superposition", overlay: "Incrustation", darken: "Obscurcir", lighten: "Éclaircir", "color-dodge": "Densité couleur −", "color-burn": "Densité couleur +", "hard-light": "Lumière crue", "soft-light": "Lumière tamisée", difference: "Différence", exclusion: "Exclusion", hue: "Teinte", saturation: "Saturation", color: "Couleur", luminosity: "Luminosité" };

export function initCalques(VL) {
  const { $, etat } = VL;
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  const actif = () => etat.doc && etat.doc.calques.find((c) => c.id === etat.calqueActif);

  // la tête et la barre d'actions (une fois) : autour de #listeCalques
  const liste = $("#listeCalques");
  const section = liste && liste.parentElement;
  if (section && !$("#calquesTete")) {
    const tete = document.createElement("div");
    tete.id = "calquesTete";
    tete.innerHTML = `<span>Opacité</span><input type="number" id="calqueOpacite" min="0" max="100" value="100" title="Opacité du calque actif (%)"/><span>%</span>
      <select id="calqueFusion" title="Mode de fusion du calque actif">${MODES_FUSION_CALQUE.map((m) => `<option value="${m}">${LIB_FUSION[m] || m}</option>`).join("")}</select>`;
    section.insertBefore(tete, liste);
    const actions = document.createElement("div");
    actions.id = "calquesActions";
    actions.innerHTML = `<button data-act="renommer" title="Renommer le calque actif">✎</button>
      <button data-act="reglage" title="Calque de réglage : niveaux, courbes, HSL… (onglet Pixel)">◐</button>
      <button data-act="masque" title="Masque de luminance de la sélection (Apparence)">◫</button>
      <button data-act="pixel" title="Nouveau calque pixel : poser une image de la Bibliothèque">▦</button>
      <button data-act="fx" title="Effets de calque : ombre, lueur, biseau… (Apparence)">fx</button>
      <span class="ca-sep"></span>
      <button data-act="groupe" title="Grouper la sélection">⧉</button>
      <button id="btnCalquePlus" title="Nouveau calque">＋</button>
      <button data-act="monter" title="Monter le calque actif d'un cran">▲</button>
      <button data-act="descendre" title="Descendre le calque actif d'un cran">▼</button>
      <button data-act="poubelle" title="Supprimer le calque actif et ses objets">🗑</button>`;
    section.appendChild(actions);
    // l'ancien ＋ du summary (s'il existe encore) cède l'id au nouveau bouton
    const vieux = section.querySelector("summary #btnCalquePlus"); if (vieux) vieux.remove();
  }

  function rendreTete() {
    const c = actif();
    const op = $("#calqueOpacite"), fu = $("#calqueFusion");
    if (!op || !fu) return;
    op.disabled = fu.disabled = !c;
    if (!c) return;
    if (document.activeElement !== op) op.value = Math.round((c.opacite ?? 1) * 100);
    fu.value = c.fusion || "normal";
  }

  function rendreCalques() {
    const hote = $("#listeCalques");
    if (!hote || !etat.doc) return;
    const lignes = [...etat.doc.calques].reverse().map((c) => `
      <div class="calque${c.id === etat.calqueActif ? " actif" : ""}"
           data-calque="${esc(c.id)}"
           title="Clic : calque actif · double-clic sur le nom : renommer">
        <span class="calque-chevron"></span>
        <span class="calque-vig" title="Le contenu de ce calque">${vignette_calque_svg(etat.doc, c.id, 28, 28, VL.imageUrl)}</span>
        <span class="nom">${esc(c.nom || c.id)}</span>
        <button data-act="verrou" class="${c.verrou ? "" : "off"}" title="Verrou">🔒</button>
        <button data-act="oeil" class="${c.visible ? "" : "off"}" title="Visibilité">👁</button>
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
    rendreTete();
  }

  $("#listeCalques").addEventListener("dblclick", (ev) => {
    const ligne = ev.target.closest(".calque");
    if (!ligne || !ev.target.classList.contains("nom")) return;
    renommer(ligne.dataset.calque);
  });
  function renommer(id) {
    const c = etat.doc.calques.find((x) => x.id === id);
    const nom = prompt("Nom du calque :", c ? c.nom : "");
    if (nom !== null) VL.executer(op_calque_renommer, id, nom);
  }

  $("#listeCalques").addEventListener("click", (ev) => {
    if (ev.target.dataset.act === "exemple") {
      if (VL.vitrailExemple) VL.vitrailExemple();
      return;
    }
    const ligne = ev.target.closest(".calque");
    if (!ligne) return;
    const id = ligne.dataset.calque;
    const act = ev.target.dataset.act;
    const c = etat.doc.calques.find((x) => x.id === id);
    if (!c) return;
    if (act === "oeil") VL.executer(op_calque_visible, id, !c.visible);
    else if (act === "verrou") VL.executer(op_calque_verrou, id, !c.verrou);
    else {
      etat.calqueActif = id;
      rendreCalques();
    }
  });

  // la tête : opacité et fusion du calque actif
  $("#calqueOpacite")?.addEventListener("change", (ev) => {
    const c = actif(); if (!c) return;
    VL.executer(op_calque_opacite, c.id, Math.max(0, Math.min(100, +ev.target.value)) / 100);
  });
  $("#calqueFusion")?.addEventListener("change", (ev) => {
    const c = actif(); if (!c) return;
    VL.executer(op_calque_fusion, c.id, ev.target.value);
  });

  // la barre d'actions
  $("#calquesActions")?.addEventListener("click", (ev) => {
    const b = ev.target.closest("button"); if (!b || !etat.doc) return;
    const act = b.dataset.act, c = actif();
    const i = c ? etat.doc.calques.indexOf(c) : -1;
    const A = VL.actions || {};
    if (act === "renommer" && c) renommer(c.id);
    else if (act === "reglage") VL.ouvrirOnglet && VL.ouvrirOnglet("pixel");
    else if (act === "masque" || act === "fx") VL.ouvrirOnglet && VL.ouvrirOnglet("apparence");
    else if (act === "pixel") { if (A.image && A.image.biblio) A.image.biblio(); else VL.ouvrirOnglet && VL.ouvrirOnglet("image"); }
    else if (act === "groupe") { if (etat.selection.length >= 2 && A.selection) A.selection.grouper(); else VL.toast("grouper : sélectionner au moins deux objets", true); }
    else if (act === "monter" && c) VL.executer(op_calque_reordonner, c.id, Math.min(etat.doc.calques.length - 1, i + 1));   // monter à l'écran = vers la fin
    else if (act === "descendre" && c) VL.executer(op_calque_reordonner, c.id, Math.max(0, i - 1));
    else if (act === "poubelle" && c) {
      if (confirm(`Supprimer le calque « ${c.nom} » et ses objets ?`)) {
        VL.executer(op_calque_supprimer, c.id);
        if (!actif()) { etat.calqueActif = etat.doc.calques[etat.doc.calques.length - 1].id; rendreCalques(); }
      }
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
