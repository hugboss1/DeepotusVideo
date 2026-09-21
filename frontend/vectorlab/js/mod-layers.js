// mod-layers.js — le panneau des calques (T1.4 côté UI). L'ordre du tableau
// est l'ordre de peinture : le panneau s'affiche INVERSÉ (le dessus en
// haut). Toute mutation passe par les commandes pures via VL.executer.
// Relooking Affinity (R3, 18/09) : tête « Opacité · Normal » sur le calque
// actif (mode de fusion de calque), rangée [chevron][vignette][nom][🔒][👁],
// barre d'actions en bas (renommer, réglage, masque, calque pixel, FX |
// groupe, nouveau, monter, descendre, supprimer). Les data-act restent.
import { icone_svg } from "./mod-icones.js";
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


/* ── 21/09 : l'ARBRE du panneau (pur) — Affinity montre sous chaque calque
   ses objets, sous un objet ses masques et effets. Rangées dans l'ordre
   d'affichage (le dessus en haut) : {niveau, genre, id, calque, nom, icone,
   actif, plie, type}. `plies` = Set des calques repliés. */
const _LIB_TYPE = { rect: "rect", ellipse: "ellipse", path: "path", texte: "texte", textechemin: "texte", cadre: "cadre", image: "image", groupe: "groupe", instance: "instance", tuile: "tuiles", forme: "forme" };
export function icone_objet(o) { return _LIB_TYPE[o && o.type] || "forme"; }
export function arbre_calques(doc, calqueActif, plies) {
  const out = [];
  if (!doc || !Array.isArray(doc.calques)) return out;
  const P = plies || new Set();
  const objet = (o, calque, niveau, genre = "objet", nomForce = null) => {
    const nom = nomForce || o.nom || `${o.type} · ${o.id}`;
    out.push({ niveau, genre, id: o.id, calque, nom, icone: genre === "ecretage" ? "ecretage" : icone_objet(o), type: o.type });
    if (genre === "ecretage") return;
    if (o.style && o.style.masque) out.push({ niveau: niveau + 1, genre: "masque", id: o.id, calque, nom: "Masque de transparence", icone: "masque", type: o.type });
    const fx = o.style && Array.isArray(o.style.effets) ? o.style.effets.length : 0;
    if (fx) out.push({ niveau: niveau + 1, genre: "effet", id: o.id, calque, nom: `Effets (${fx})`, icone: "effet", type: o.type });
    if (o.type === "groupe") for (const e of [...(o.enfants || [])].reverse()) objet(e, calque, niveau + 1, o.clip && e.id === o.clip ? "ecretage" : "objet", o.clip && e.id === o.clip ? "Masque d'écrêtage" : null);
  };
  for (const c of [...doc.calques].reverse()) {
    const plie = P.has(c.id);
    out.push({ niveau: 0, genre: "calque", id: c.id, calque: c.id, nom: c.nom || c.id, icone: "calque", actif: c.id === calqueActif, plie, type: "calque", visible: c.visible !== false, verrou: !!c.verrou });
    if (plie) continue;
    for (const o of [...(c.objets || [])].reverse()) objet(o, c.id, 1);
  }
  return out;
}

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

  // 21/09 : les calques repliés (persistés) — le calque actif se déplie de lui-même
  const CLE_PLIES = "dz_vl_calques_plies";
  let plies = new Set();
  try { plies = new Set(JSON.parse(localStorage.getItem(CLE_PLIES) || "[]")); } catch (e) { plies = new Set(); }
  const sauverPlies = () => { try { localStorage.setItem(CLE_PLIES, JSON.stringify([...plies])); } catch (e) { /* stockage indisponible */ } };
  function rendreCalques() {
    const hote = $("#listeCalques");
    if (!hote || !etat.doc) return;
    const sel = new Set(etat.selection || []);
    const lignes = arbre_calques(etat.doc, etat.calqueActif, plies).map((r) => {
      if (r.genre === "calque") {
        const c = etat.doc.calques.find((x) => x.id === r.id) || {};
        const nObj = (c.objets || []).length;
        return `
      <div class="calque${r.actif ? " actif" : ""}${r.plie ? " plie" : ""}"
           data-calque="${esc(r.id)}"
           title="Clic : calque actif · double-clic sur le nom : renommer">
        <span class="calque-chevron" title="${r.plie ? "Déplier" : "Replier"} les objets du calque (${nObj})">${nObj ? (r.plie ? "▸" : "▾") : ""}</span>
        <span class="calque-vig" title="Le contenu de ce calque">${vignette_calque_svg(etat.doc, r.id, 28, 28, VL.imageUrl)}</span>
        <span class="nom">${esc(r.nom)}</span>
        <button data-act="verrou" class="${r.verrou ? "" : "off"}" title="Verrou">🔒</button>
        <button data-act="oeil" class="${r.visible ? "" : "off"}" title="Visibilité">👁</button>
      </div>`;
      }
      const titre = r.genre === "objet" ? "Clic : sélectionner l'objet (Maj : ajouter)" : r.genre === "ecretage" ? "L'enfant qui écrête le groupe (Apparence)" : r.genre === "masque" ? "Masque de transparence de l'objet (Apparence)" : "Effets de calque de l'objet (Apparence)";
      return `
      <div class="calque-objet${sel.has(r.id) && r.genre === "objet" ? " selectionne" : ""}" data-objet="${esc(r.id)}" data-genre="${r.genre}" data-calque="${esc(r.calque)}" style="--niv:${r.niveau}" title="${titre}">
        <span class="co-ic">${icone_svg(r.icone, 14)}</span><span class="nom">${esc(r.nom)}</span>
      </div>`;
    }).join("");
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
  async function renommer(id) {
    const c = etat.doc.calques.find((x) => x.id === id);
    const nom = await VL.dialogue.saisir("Nom du calque :", { valeur: c ? c.nom : "", titre: "Renommer le calque", valider: "Renommer" });
    if (nom !== null) VL.executer(op_calque_renommer, id, nom);
  }

  $("#listeCalques").addEventListener("click", (ev) => {
    if (ev.target.dataset.act === "exemple") {
      if (VL.vitrailExemple) VL.vitrailExemple();
      return;
    }
    // 21/09 : une rangée d'objet — sélection (Maj : ajout) ; masque / écrêtage / effets → l'onglet Apparence
    const lo = ev.target.closest(".calque-objet");
    if (lo) {
      const oid = lo.dataset.objet;
      etat.calqueActif = lo.dataset.calque;
      if (lo.dataset.genre === "objet") VL.setSelection(ev.shiftKey ? [...new Set([...etat.selection, oid])] : [oid]);
      else { VL.setSelection([oid]); if (VL.ouvrirOnglet) VL.ouvrirOnglet("apparence"); }
      rendreCalques();
      return;
    }
    const ligne = ev.target.closest(".calque");
    if (!ligne) return;
    const id = ligne.dataset.calque;
    const act = ev.target.dataset.act;
    const c = etat.doc.calques.find((x) => x.id === id);
    if (!c) return;
    if (ev.target.classList.contains("calque-chevron")) { if (plies.has(id)) plies.delete(id); else plies.add(id); sauverPlies(); rendreCalques(); return; }
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
  $("#calquesActions")?.addEventListener("click", async (ev) => {
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
      if (await VL.dialogue.confirmer(`Supprimer le calque « ${c.nom} » et ses objets ?`, { ok: "Supprimer", danger: true })) {
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
  const suivantSelCalques = VL.surSelection;
  VL.surSelection = () => { suivantSelCalques(); rendreCalques(); };   // 21/09 : la rangée d'objet suit la sélection
}
