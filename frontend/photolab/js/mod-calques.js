// mod-calques.js — le panneau Calques (C2, inventaire B §3 / A4) : filtre, mode de fusion, opacité, verrous, fond,
// liste (œil, vignette, nom renommable, cadenas), sélection au clic, glisser pour réordonner, boutons du pied.
// Chaque geste = une commande moteur (layer.*) puis un cycle ; le panneau ne garde en propre QUE les verrous (le moteur
// ne les relit pas) et les groupes repliés. Fonctions PURES exportées (qa/panneaux.test.mjs).

import { brut } from "./mod-cycle.js";

// t157 : un filtre est-il rééditable dans le dialogue générique (au moins un champ montrable) ? Copie MINIMALE de
// champsVisibles (mod-champs importe ce module : l'import inverse ferait une boucle).
const OPAQUES_SF = new Set(["json", "struct", "intArray", "union", "?", "layerId", "index", "docIndex"]);
const champsVisibles = (champs) => (Array.isArray(champs) ? champs : []).filter((c) => c && c.cle !== "layer" && !OPAQUES_SF.has(c.type));

const DELAI_CLIC = 220;                         // ms : laisse passer un double-clic avant de sélectionner
const TYPE_GLISSER = "application/x-photolab-calque";

// Arbre doc.inspect (haut -> bas) -> liste à plat avec profondeur. Un groupe replié (par l'écran, ou fermé dans le
// moteur : expanded === false) cache ses enfants — sauf `toutDeplier` (filtre par nom : un calque qui correspond doit se
// voir, même rangé dans un groupe fermé).
export function aplatirCalques(layers, replies = new Set(), toutDeplier = false) {
  const sortie = [];
  const voir = (liste, profondeur) => {
    for (const c of liste || []) {
      const groupe = Array.isArray(c.children);
      sortie.push({ ...c, profondeur, groupe });
      if (groupe && (toutDeplier || (c.expanded !== false && !replies.has(c.id)))) voir(c.children, profondeur + 1);
    }
  };
  voir(layers, 0);
  return sortie;
}

// Dépôt d'une ligne glissée -> paramètres de layer.moveTo. « En dessous » d'un groupe DÉPLIÉ (sa ligne suivante est
// plus profonde) : l'indicateur est dessiné sous la ligne du groupe, donc au-dessus de sa première ligne visible.
export function cibleDepot(lignes, index, position) {
  const c = lignes[index], suiv = lignes[index + 1];
  if (position === "below" && c && c.groupe && suiv && suiv.profondeur > c.profondeur) return { target: suiv.id, position: "above" };
  return { target: c.id, position };
}

export function trouverCalque(layers, id) {
  for (const c of layers || []) {
    if (c.id === id) return c;
    const r = Array.isArray(c.children) ? trouverCalque(c.children, id) : null;
    if (r) return r;
  }
  return null;
}

// Clic sur une ligne -> paramètres de layer.select. Maj = plage (l'emporte), Ctrl = ajouter / retirer.
export function actionSelection(id, ctrl, maj) {
  return { layer: id, mode: maj ? "range" : ctrl ? "toggle" : "replace" };
}

// 0..1 -> « 50 % » (fr, espace) / « 50% » (en).
export function pourcent(x, lang = "fr") {
  const n = Math.round(Math.max(0, Math.min(1, Number(x) || 0)) * 100);
  return lang === "fr" ? n + " %" : n + "%";
}
// « 50 », « 50 % », « 12,5 » -> 0..1 ; illisible -> null.
export function depuisPourcent(s) {
  const m = /^\s*(-?\d+(?:[.,]\d+)?)\s*%?\s*$/.exec(String(s == null ? "" : s));
  if (!m) return null;
  return Math.max(0, Math.min(1, Number(m[1].replace(",", ".")) / 100));
}

// Les 27 modes de photocraft dans l'ordre du menu (BlendMode::LAYER_MODES, inventaire B §4.3). `moteur` = nom rendu
// par doc.inspect ; `id` = valeur acceptée par layer.setProps (relevé le 08/10 : camelCase accepté, « lddg » refusé).
const snake = (s) => s.replace(/[A-Z]/g, (c) => "_" + c.toLowerCase());
const mode = (id, moteur) => ({ id, moteur, cle: "photolab.fusion." + snake(id) });
export const MODES_FUSION = [
  mode("normal", "Normal"), mode("dissolve", "Dissolve"), mode("darken", "Darken"), mode("multiply", "Multiply"),
  mode("colorBurn", "Color Burn"), mode("linearBurn", "Linear Burn"), mode("darkerColor", "Darker Color"),
  mode("lighten", "Lighten"), mode("screen", "Screen"), mode("colorDodge", "Color Dodge"), mode("linearDodge", "Linear Dodge (Add)"),
  mode("lighterColor", "Lighter Color"), mode("overlay", "Overlay"), mode("softLight", "Soft Light"), mode("hardLight", "Hard Light"),
  mode("vividLight", "Vivid Light"), mode("linearLight", "Linear Light"), mode("pinLight", "Pin Light"), mode("hardMix", "Hard Mix"),
  mode("difference", "Difference"), mode("exclusion", "Exclusion"), mode("subtract", "Subtract"), mode("divide", "Divide"),
  mode("hue", "Hue"), mode("saturation", "Saturation"), mode("color", "Color"), mode("luminosity", "Luminosity"),
];
export const MODE_TRANSFERT = mode("passThrough", "Pass Through");     // groupes seulement, en tête de liste
const norm = (s) => String(s || "").toLowerCase().replace(/[^a-z]/g, "");
export function idFusion(nomMoteur) {
  const n = norm(nomMoteur);
  const m = [MODE_TRANSFERT, ...MODES_FUSION].find((x) => norm(x.moteur) === n || norm(x.id) === n);
  return m ? m.id : null;
}

// Dépôt d'une ligne glissée : au-dessus / en dessous ; dans un groupe entre 30 et 70 % de la hauteur de sa ligne.
export function positionDepot(y, hauteur, estGroupe) {
  if (estGroupe && y >= hauteur * 0.3 && y <= hauteur * 0.7) return "into";
  return y < hauteur / 2 ? "above" : "below";
}

// Les 5 verrous de photocraft (panels.rs:1337-1378) ; état tenu par l'écran, envoyé COMPLET à layer.setProps.
export const VERROUS = [
  { cle: "transparency", icone: "dz-etat-verrou-transparence", cle_libelle: "photolab.verrou.transparence" },
  { cle: "pixels", icone: "dz-etat-verrou-pixels", cle_libelle: "photolab.verrou.pixels" },
  { cle: "position", icone: "dz-etat-verrou-position", cle_libelle: "photolab.verrou.position" },
  { cle: "artboard", icone: "dz-etat-verrou-plan-travail", cle_libelle: "photolab.verrou.plan" },
  { cle: "all", icone: "dz-etat-verrouille", cle_libelle: "photolab.verrou.tout" },
];
export function basculerVerrou(etat, cle) {
  const e = {};
  for (const v of VERROUS) e[v.cle] = !!(etat && etat[v.cle]);
  e[cle] = !e[cle];
  return e;
}

// L'arrière-plan : dernier calque à la racine, nommé « Background » par le moteur (cadenas, comme photocraft).
// Le calque porte-t-il des effets (doc.inspect : effects.items, absent quand il n'y en a aucun) ? -> badge « fx » de sa
// ligne (t138 B6). Ici et non dans mod-styles.js : mod-styles importe ce module, l'inverse ferait une boucle d'imports.
export function aDesEffets(calque) {
  return !!(calque && calque.effects && Array.isArray(calque.effects.items) && calque.effects.items.length);
}

/* t157 : masques, liens, filtres dynamiques */

// Bouton Masque (amont layer_menu_ui.rs:13-20, référence) : avec une sélection, révéler (Alt : masquer) la sélection ;
// sans, tout révéler (Alt : tout masquer). Un calque qui a déjà son masque de fusion reçoit un masque VECTORIEL
// (Alt : qui masque tout).
export function commandeMasque(aSelection, alt, aDejaUnMasque) {
  if (aDejaUnMasque) return { command: "layer.vectorMask.add", params: alt ? { hide: true } : {} };
  const nom = aSelection ? (alt ? "hideSelection" : "revealSelection") : (alt ? "hideAll" : "revealAll");
  return { command: "layer.layerMask." + nom, params: {} };
}

// Calques choisis d'un doc.inspect (selected, ou le calque actif à défaut).
export function calquesChoisis(doc) {
  const out = [];
  const voir = (l) => { for (const c of l || []) { if (c.selected) out.push(c); if (Array.isArray(c.children)) voir(c.children); } };
  voir(doc && doc.layers);
  if (!out.length && doc && doc.activeLayer != null) { const a = trouverCalque(doc.layers, doc.activeLayer); if (a) out.push(a); }
  return out;
}
// Lier : deux calques choisis au moins, ou un calque déjà lié (la commande bascule : elle délie) — amont
// layer_multi_cmds.rs:179-187.
export function peutLier(doc) {
  const c = calquesChoisis(doc);
  return c.length >= 2 || (c.length === 1 && c[0].linkGroup != null);
}

// Geste sur la vignette d'un masque (amont mask_thumbs_ui.rs:182-205) -> {action, operation?} :
// Ctrl = charger le masque comme sélection (Maj ajouter, Alt soustraire, les deux intersection), Maj = activer /
// désactiver, Alt = voir le masque seul sur la toile, sinon choisir le calque.
export function gesteMasque(ev) {
  const ctrl = !!(ev && (ev.ctrlKey || ev.metaKey)), maj = !!(ev && ev.shiftKey), alt = !!(ev && ev.altKey);
  if (ctrl) return { action: "selection", operation: maj && alt ? "intersect" : maj ? "add" : alt ? "subtract" : "new" };
  if (maj && !alt) return { action: "activer" };
  if (alt) return { action: "voir" };
  return { action: "choisir" };
}

// Les filtres dynamiques d'un objet dynamique, tels que le panneau les montre : le DERNIER appliqué en haut ; `index`
// reste celui du moteur (0 = le premier appliqué, en bas).
export function filtresDynamiques(calque) {
  const f = calque && Array.isArray(calque.smartFilters) ? calque.smartFilters : [];
  return f.map((x, index) => ({ ...x, index })).reverse();
}
// Glisser un filtre dynamique sur un autre : layer.smartFilter.move {index, to} (même calque seulement).
export function deplacementFiltre(source, cible) {
  if (!source || !cible || source.layer !== cible.layer || source.index === cible.index) return null;
  return { layer: source.layer, index: source.index, to: cible.index };
}

export function estFond(calque, racines) {
  const l = racines || [];
  return !!calque && l.length > 0 && l[l.length - 1] === calque && calque.name === "Background" && !Array.isArray(calque.children);
}

/* ───────────── côté DOM ───────────── */

export function initCalques(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const corps = PL.$("#corpsCalques");
  const replies = new Set();
  PL.etat.verrous = {};          // id -> {transparency, pixels, position, artboard, all}
  let enRenommage = null;        // id du calque dont le nom est en cours d'édition (la liste n'est pas redessinée)
  let enAttente = false;
  let minutClic = null;          // clic simple en attente (annulé par un double-clic)

  const el = (tag, classe, texte) => { const e = document.createElement(tag); if (classe) e.className = classe; if (texte != null) e.textContent = texte; return e; };
  const icone = (nom, cible) => { cible.dataset.icone = nom; cible.innerHTML = PL.icone(nom); return cible; };
  const bouton = (classe, ico, titre) => {
    const b = el("button", classe); b.type = "button"; b.title = titre; b.setAttribute("aria-label", titre);
    if (ico) icone(ico, b);
    return b;
  };
  const actif = () => (PL.etat.doc ? PL.etat.doc.activeLayer : null);

  /* en-tête : filtre ; fusion + opacité ; verrous + fond */
  const tete = el("div", "cq-tete");
  const filtre = el("input", "cq-filtre"); filtre.type = "search"; filtre.placeholder = T("photolab.calques.filtre");
  filtre.setAttribute("aria-label", filtre.placeholder);
  const fusion = el("select", "cq-fusion"); fusion.setAttribute("aria-label", T("photolab.calques.fusion"));
  const opacite = el("input", "cq-nombre"); opacite.type = "number"; opacite.min = "0"; opacite.max = "100"; opacite.step = "1";
  const fond = el("input", "cq-nombre"); fond.type = "number"; fond.min = "0"; fond.max = "100"; fond.step = "1";
  const l1 = el("div", "cq-l"); l1.append(filtre);
  const lOp = el("label", "cq-champ"); lOp.append(el("span", "", T("photolab.calques.opacite")), opacite, el("span", "pl-unite", "%"));
  const l2 = el("div", "cq-l"); l2.append(fusion, lOp);
  const verrous = el("span", "cq-verrous");
  const bVerrous = VERROUS.map((v) => { const b = bouton("cq-verrou", v.icone, T(v.cle_libelle)); b.dataset.verrou = v.cle; verrous.appendChild(b); return b; });
  const lFond = el("label", "cq-champ"); lFond.append(el("span", "", T("photolab.calques.fond")), fond, el("span", "pl-unite", "%"));
  const l3 = el("div", "cq-l"); l3.append(el("span", "cq-lib", T("photolab.calques.verrou")), verrous, lFond);
  tete.append(l1, l2, l3);

  const liste = el("div", "cq-liste"); liste.setAttribute("role", "listbox"); liste.setAttribute("aria-label", T("photolab.panneau.calques"));
  const pied = el("div", "cq-pied");
  const bLien = bouton("", "dz-edit-lier", T("photolab.calques.lier"));
  // t138 B6 : le dialogue Style de calque (mod-styles.js, lu à l'exécution : aucun import croisé).
  const bFx = bouton("", "dz-edit-effet", T("photolab.calques.style"));
  const bMasque = bouton("", "dz-calque-masque", T("photolab.calques.masque"));
  // t138 B5 : petit menu des 16 calques de réglage (mod-reglages.js, lu à l'exécution : aucun import croisé).
  const bReglage = bouton("", "dz-calque-reglage", T("photolab.calques.reglage"));
  bReglage.setAttribute("aria-haspopup", "menu");
  const bGroupe = bouton("", "dz-action-nouveau-dossier", T("photolab.calques.nouveau_groupe"));
  const bNouveau = bouton("", "dz-calque-nouveau", T("photolab.calques.nouveau"));
  const bDupliquer = bouton("", "dz-action-dupliquer", T("photolab.calques.dupliquer"));
  const bFusionner = bouton("", "dz-calque-fusionner", T("photolab.calques.fusionner"));
  const bSupprimer = bouton("", "dz-action-supprimer", T("photolab.calques.supprimer"));
  pied.append(bLien, bFx, bMasque, bReglage, bGroupe, bNouveau, bDupliquer, bFusionner, bSupprimer);
  corps.textContent = "";
  corps.append(tete, liste, pied);

  /* commandes */
  const props = (p) => { const a = actif(); if (a != null) PL.executer("layer.setProps", { layer: a, ...p }); };
  fusion.addEventListener("change", () => props({ blend: fusion.value }));
  const surPourcent = (champ, cle) => champ.addEventListener("change", () => {
    const v = depuisPourcent(champ.value);
    if (v == null) { majEntete(PL.etat.doc); return; }
    props({ [cle]: v });
  });
  surPourcent(opacite, "opacity"); surPourcent(fond, "fill");
  bVerrous.forEach((b) => b.addEventListener("click", () => {
    const a = actif(); if (a == null) return;
    PL.etat.verrous[a] = basculerVerrou(PL.etat.verrous[a], b.dataset.verrou);
    majEntete(PL.etat.doc);
    PL.executer("layer.setProps", { layer: a, locks: PL.etat.verrous[a] });
  }));
  bReglage.addEventListener("click", () => { if (PL.reglages) PL.reglages.menu(bReglage); });
  bFx.addEventListener("click", () => { if (PL.ouvrirStyles) PL.ouvrirStyles(); });
  bNouveau.addEventListener("click", () => PL.executer("layer.new.layer", {}));
  bGroupe.addEventListener("click", () => PL.executer("layer.groupLayers", {}));
  bDupliquer.addEventListener("click", () => PL.executer("layer.duplicate", {}));
  bFusionner.addEventListener("click", () => PL.executer("layer.mergeDown", {}));
  bSupprimer.addEventListener("click", () => PL.executer("layer.delete", {}));
  // t157 : Lier (bascule) et Masque (Alt : qui masque ; un calque déjà masqué reçoit un masque vectoriel)
  bLien.addEventListener("click", () => PL.executer("layer.linkLayers", {}));
  bMasque.addEventListener("click", (ev) => {
    const doc = PL.etat.doc, c = doc && actif() != null ? trouverCalque(doc.layers, actif()) : null;
    if (!c) return;
    const m = commandeMasque(!!doc.hasSelection, ev.altKey, !!c.hasMask);
    PL.executer(m.command, m.params);
  });
  filtre.addEventListener("input", () => dessiner(PL.etat.doc));

  function majEntete(doc) {
    const c = doc && actif() != null ? trouverCalque(doc.layers, actif()) : null;
    for (const x of [fusion, opacite, fond, ...bVerrous]) x.disabled = !c;
    fusion.textContent = "";
    const modes = c && Array.isArray(c.children) ? [MODE_TRANSFERT, ...MODES_FUSION] : MODES_FUSION;
    for (const m of modes) { const o = el("option", "", T(m.cle)); o.value = m.id; fusion.appendChild(o); }
    if (!c) { opacite.value = ""; fond.value = ""; bVerrous.forEach((b) => b.classList.remove("actif")); return; }
    fusion.value = idFusion(c.blend) || "normal";
    opacite.value = Math.round((c.opacity ?? 1) * 100);
    fond.value = Math.round((c.fill ?? 1) * 100);
    const v = PL.etat.verrous[c.id] || {};
    bVerrous.forEach((b) => { b.classList.toggle("actif", !!v[b.dataset.verrou]); b.setAttribute("aria-pressed", v[b.dataset.verrou] ? "true" : "false"); });
  }

  function vignette(c) {
    const box = el("span", "cq-vignette");
    if (c.groupe) { icone("dz-calque-groupe", box); return box; }
    // Calque de réglage : l'icône de son kind à la place de la vignette (il n'a pas de pixels) ; double-clic -> son
    // éditeur dans l'onglet Propriétés. dataset.icone (posé par icone()) tient les vignettes à l'écart de cette case.
    const kr = PL.reglages ? PL.reglages.kindDe(c) : null;
    if (kr) {
      icone(PL.reglages.icone(kr), box);
      box.classList.add("reglage");
      box.title = T(PL.reglages.cle(kr));
      box.addEventListener("dblclick", (ev) => {
        ev.stopPropagation();
        clearTimeout(minutClic); minutClic = null;          // le clic simple différé ne doit pas passer après
        if (c.id !== actif()) PL.executer("layer.select", actionSelection(c.id, false, false));
        PL.reglages.montrer("proprietes");
      });
      return box;
    }
    const url = PL.etat.vignettes[String(c.id)];
    if (url) { const im = el("img"); im.alt = ""; im.src = url; im.dataset.id = String(c.id); box.appendChild(im); }
    // t157 : badge de l'objet dynamique dans le coin de sa vignette (amont smart_ui.rs:12-21)
    if (/smart/i.test(String(c.kind || ""))) {
      const b = el("span", "cq-badge-dynamique"); b.title = T("photolab.calques.objet_dynamique");
      b.innerHTML = PL.icone("dz-calque-objet-dynamique");
      box.classList.add("dynamique"); box.appendChild(b);
    }
    return box;
  }

  function ligne(c, doc, lignes, index) {
    const l = el("div", "cq-ligne");
    l.dataset.id = String(c.id);
    l.setAttribute("role", "option");
    const choisi = c.selected || c.id === doc.activeLayer;
    l.setAttribute("aria-selected", choisi ? "true" : "false");
    l.classList.toggle("choisi", !!choisi);
    l.classList.toggle("cache", c.visible === false);
    l.draggable = true;
    const oeil = bouton("cq-oeil", c.visible === false ? "dz-etat-cache" : "dz-etat-visible", T(c.visible === false ? "photolab.calques.montrer" : "photolab.calques.masquer"));
    oeil.addEventListener("click", (ev) => { ev.stopPropagation(); PL.executer("layer.setProps", { layer: c.id, visible: c.visible === false }); });
    const retrait = el("span", "cq-retrait"); retrait.style.width = c.profondeur * 14 + "px";
    const chevron = el("span", "cq-chevron");
    if (c.groupe) {
      const ouvert = c.expanded !== false && !replies.has(c.id);
      const b = bouton("cq-plier" + (ouvert ? "" : " pl-replie"), "dz-action-deplier", T(ouvert ? "photolab.calques.replier" : "photolab.calques.deplier"));
      b.addEventListener("click", (ev) => { ev.stopPropagation(); if (replies.has(c.id)) replies.delete(c.id); else replies.add(c.id); dessiner(PL.etat.doc); });
      chevron.appendChild(b);
    }
    // Le nom est une donnée de l'utilisateur : la surcouche de traduction n'y touche pas (data-dz-brut).
    const nom = brut(el("span", "cq-nom", c.name || ""));
    nom.addEventListener("dblclick", (ev) => { ev.stopPropagation(); clearTimeout(minutClic); minutClic = null; renommer(c, nom); });
    l.append(oeil, retrait, chevron, vignette(c), ...masque(c), nom);
    if (aDesEffets(c)) l.appendChild(badgeFx(c));
    // t157 : calque lié (amont : icône « link » à droite de la ligne)
    if (c.linkGroup != null) { const li = el("span", "cq-lie"); li.title = T("photolab.calques.lie"); icone("dz-edit-lier", li); l.appendChild(li); }
    // t157 : objet dynamique à filtres — triangle qui replie ses sous-lignes
    if (Array.isArray(c.smartFilters) && c.smartFilters.length) {
      const cle = "sf-" + c.id, ouvert = !replies.has(cle);
      const b = bouton("cq-sf-plier" + (ouvert ? "" : " pl-replie"), "dz-action-deplier", T(ouvert ? "photolab.filtres.replier" : "photolab.filtres.deplier"));
      b.addEventListener("click", (ev) => { ev.stopPropagation(); if (replies.has(cle)) replies.delete(cle); else replies.add(cle); dessiner(PL.etat.doc); });
      l.appendChild(b);
    }
    const idf = idFusion(c.blend);
    if (idf && idf !== "normal" && idf !== "passThrough") {
      const m = MODES_FUSION.find((x) => x.id === idf);
      l.appendChild(el("span", "cq-mode", m ? T(m.cle) : c.blend));
    }
    const v = PL.etat.verrous[c.id];
    if (estFond(c, doc.layers) || (v && Object.values(v).some(Boolean))) {
      const cad = el("span", "cq-cadenas"); cad.title = T("photolab.verrou.tout"); icone("dz-etat-verrouille", cad); l.appendChild(cad);
    }
    // Clic simple différé : un double-clic (renommer) doit trouver le nom encore en place. Sélectionner tout de suite
    // relancerait un cycle qui redessine la liste entre les deux clics.
    l.addEventListener("click", (ev) => {
      if (enRenommage != null || ev.detail > 1) return;
      const ctrl = ev.ctrlKey || ev.metaKey, maj = ev.shiftKey;
      clearTimeout(minutClic);
      minutClic = setTimeout(() => {
        minutClic = null;
        if (enRenommage == null) PL.executer("layer.select", actionSelection(c.id, ctrl, maj));
      }, DELAI_CLIC);
    });
    /* glisser pour réordonner : layer.moveTo {target, position}. La source voyage dans le dataTransfer (type propre) :
       aucun état qui survive à un redessin, et un fichier déposé depuis le bureau sur une ligne est ignoré. */
    const effacer = () => PL.$$(".cq-ligne", liste).forEach((x) => x.classList.remove("depot-above", "depot-below", "depot-into"));
    const notreGlisser = (ev) => ev.dataTransfer && Array.from(ev.dataTransfer.types || []).includes(TYPE_GLISSER);
    l.addEventListener("dragstart", (ev) => { ev.dataTransfer.effectAllowed = "move"; ev.dataTransfer.setData(TYPE_GLISSER, String(c.id)); });
    l.addEventListener("dragend", effacer);
    l.addEventListener("dragover", (ev) => {
      if (!notreGlisser(ev)) return;
      ev.preventDefault();
      const r = l.getBoundingClientRect();
      const pos = positionDepot(ev.clientY - r.top, r.height, c.groupe);
      l.classList.remove("depot-above", "depot-below", "depot-into");
      l.classList.add("depot-" + pos);
    });
    l.addEventListener("dragleave", () => l.classList.remove("depot-above", "depot-below", "depot-into"));
    l.addEventListener("drop", (ev) => {
      if (!notreGlisser(ev)) return;
      ev.preventDefault();
      effacer();
      const src = Number(ev.dataTransfer.getData(TYPE_GLISSER));
      const r = l.getBoundingClientRect();
      const d = cibleDepot(lignes, index, positionDepot(ev.clientY - r.top, r.height, c.groupe));
      if (!Number.isFinite(src) || src === c.id || src === d.target) return;
      PL.executer("layer.moveTo", { layer: src, target: d.target, position: d.position });
    });
    return l;
  }

  // Badge « fx » d'un calque qui a des effets ; double-clic -> dialogue Style de calque SUR CE calque : il est d'abord
  // sélectionné et relu (le dialogue lit le calque actif de PL.etat.doc), puis le dialogue s'ouvre.
  function badgeFx(c) {
    const b = el("span", "cq-fx"); b.innerHTML = PL.icone("dz-edit-effet");
    b.title = T("photolab.calques.style");
    b.addEventListener("dblclick", async (ev) => {
      ev.stopPropagation();
      clearTimeout(minutClic); minutClic = null;           // le clic simple différé ne doit pas passer après
      if (!PL.ouvrirStyles) return;
      if (c.id !== actif()) {
        const r = await PL.executer("layer.select", actionSelection(c.id, false, false), { cycle: false });
        if (!(r && r.ok)) return;
        await PL.cycle();
      }
      PL.ouvrirStyles();
    });
    return b;
  }

  // Renommer en place : Entrée ou clic ailleurs valide, Échap annule (photocraft, layer_row_ui.rs:228-277).
  function renommer(c, nom) {
    enRenommage = c.id;
    const champ = el("input", "cq-renommer"); champ.type = "text"; champ.value = c.name || ""; champ.maxLength = 120;
    nom.replaceWith(champ);
    champ.focus(); champ.select();
    let fini = false;
    const finir = async (valider) => {
      if (fini) return; fini = true;
      enRenommage = null;
      const v = champ.value.trim();
      enAttente = false;
      if (valider && v && v !== c.name) {
        const r = await PL.executer("layer.renameLayer", { layer: c.id, name: v });
        if (!r.ok) dessiner(PL.etat.doc);                // refus (pont ou moteur, déjà signalé) : l'ancien nom revient
      } else dessiner(PL.etat.doc);
    };
    champ.addEventListener("keydown", (ev) => {
      ev.stopPropagation();
      if (ev.key === "Enter") { ev.preventDefault(); finir(true); } else if (ev.key === "Escape") { ev.preventDefault(); finir(false); }
    });
    champ.addEventListener("blur", () => finir(true));
    champ.addEventListener("click", (ev) => ev.stopPropagation());
  }

  function dessiner(doc) {
    if (enRenommage != null) { enAttente = true; return; }      // jamais sous les doigts de l'utilisateur
    majEntete(doc);
    liste.textContent = "";
    for (const b of [bFx, bReglage, bGroupe, bNouveau, bDupliquer, bFusionner, bSupprimer]) b.disabled = !doc;
    bLien.disabled = !doc || !peutLier(doc);
    bMasque.disabled = !doc || actif() == null;
    bMasque.title = T("photolab.calques.masque") + (doc && doc.hasSelection ? " — " + T("photolab.calques.masque_selection") : "");
    bMasque.setAttribute("aria-label", bMasque.title);
    if (!doc) return;
    const f = filtre.value.trim().toLowerCase();
    // Filtre : tout déplié (un calque qui correspond se voit même dans un groupe fermé dans le moteur).
    const lignes = aplatirCalques(doc.layers, replies, !!f).filter((c) => !f || String(c.name || "").toLowerCase().includes(f));
    lignes.forEach((c, i) => {
      liste.appendChild(ligne(c, doc, lignes, i));
      if (Array.isArray(c.smartFilters) && c.smartFilters.length && !replies.has("sf-" + c.id)) for (const x of lignesFiltres(c)) liste.appendChild(x);
    });
  }

  /* ── t157 : masque de fusion d'une ligne ── */
  const etatMasque = (id) => PL.etat.etatsMasques[id] || (PL.etat.etatsMasques[id] = { active: true, lie: true });
  let vueMasque = null;                  // id du calque dont le masque est montré seul sur la toile (Alt-clic)
  function masque(c) {
    if (!c.hasMask) return [];
    const em = etatMasque(c.id);
    // chaîne : liée par défaut (le moteur ne relit pas cet état) ; clic = lier / délier le masque au calque
    const chaine = bouton("cq-chaine" + (em.lie ? " lie" : ""), "dz-edit-lier", T(em.lie ? "photolab.calques.masque_lie" : "photolab.calques.masque_delie"));
    chaine.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const r = await PL.executer("layer.layerMask.linked", { layer: c.id });
      if (r && r.ok && r.r && typeof r.r.linked === "boolean") etatMasque(c.id).lie = r.r.linked;
    });
    const box = el("span", "cq-vignette cq-masque" + (em.active ? "" : " inactif") + (vueMasque === c.id ? " vu" : ""));
    box.title = T("photolab.calques.vignette_masque");
    box.dataset.masque = String(c.id);
    const url = PL.etat.vignettesMasques && PL.etat.vignettesMasques[String(c.id)];
    if (url) { const im = el("img"); im.alt = ""; im.src = url; box.appendChild(im); }
    box.addEventListener("click", (ev) => {
      ev.stopPropagation();
      clearTimeout(minutClic); minutClic = null;
      const g = gesteMasque(ev);
      if (g.action === "selection") PL.executer("select.loadSelection", { channel: "mask", layer: c.id, operation: g.operation });
      else if (g.action === "activer") {
        PL.executer("layer.layerMask.enabled", { layer: c.id }).then((r) => {
          if (r && r.ok && r.r && typeof r.r.enabled === "boolean") { etatMasque(c.id).active = r.r.enabled; dessiner(PL.etat.doc); }
        });
      } else if (g.action === "voir") voirMasque(c.id);
      else {
        if (vueMasque != null) quitterVueMasque();
        if (c.id !== actif()) PL.executer("layer.select", actionSelection(c.id, false, false));
      }
    });
    return [chaine, box];
  }
  // Alt-clic : le masque seul sur la toile (rendu par le pont, comme la vignette) ; Alt-clic à nouveau, clic sur la
  // vignette ou toute modification du document : retour à l'image.
  async function voirMasque(id) {
    if (vueMasque === id) { quitterVueMasque(); return; }
    vueMasque = id;
    dessiner(PL.etat.doc);
    const voulu = PL.vue.maxSideVoulu();
    try {
      const r = await PL.get("/masques?layer=" + id + "&maxSide=" + Math.max(16, Math.min(2048, voulu || 1024)));
      const m = r && r.masques && r.masques[0];
      if (!m || vueMasque !== id) return;
      const im = new Image();
      im.onload = () => { if (vueMasque === id) PL.vue.poserApercu(im, voulu); };
      im.src = m.png;
    } catch (e) { vueMasque = null; dessiner(PL.etat.doc); }
  }
  function quitterVueMasque() { vueMasque = null; PL.cycle(); }
  PL.surDoc.push((doc) => { if (vueMasque != null && !(doc && trouverCalque(doc.layers, vueMasque))) vueMasque = null; });
  if (PL.surRendu) PL.surRendu.push(() => { if (vueMasque != null) { vueMasque = null; dessiner(PL.etat.doc); } });

  /* ── t157 : filtres dynamiques sous un objet dynamique ── */
  const TYPE_FILTRE = "application/x-photolab-filtre";
  // L'entrée de menu d'un filtre (libellé, champs), sinon celle du registre.
  function entreeDe(commande) {
    const voir = (l) => { for (const e of l || []) { if (e.id === commande) return e; const r = e.entrees ? voir(e.entrees) : null; if (r) return r; } return null; };
    const arbre = (PL.menus && PL.menus.arbre) || [];
    for (const m of arbre) { const r = voir(m.entrees); if (r) return r; }
    const reg = (PL.menus && PL.menus.registre) || [];
    const r = (Array.isArray(reg) ? reg : []).find((x) => x && x.id === commande);
    return r ? { id: commande, libelle: r.label || commande, champs: r.champs } : null;
  }
  const PREFIXE_GALERIE = "filter.gallery.";
  function libelleFiltre(cmd) {
    if (cmd === "filter.filterGallery") return T("photolab.galerie.titre");
    if (String(cmd || "").startsWith(PREFIXE_GALERIE)) {
      const cle = "photolab.galerie.f." + cmd.slice(PREFIXE_GALERIE.length).replace(/[A-Z]/g, (x) => "_" + x.toLowerCase());
      const t = T(cle);
      if (t && t !== cle) return t;
    }
    const e = entreeDe(cmd);
    return e ? String(e.libelle || cmd).replace(/…$/, "") : String(cmd || "");
  }
  function lignesFiltres(c) {
    const off = c.smartFiltersEnabled === false;
    const tete = el("div", "cq-ligne cq-sf-tete" + (off ? " cache" : ""));
    const oeilT = bouton("cq-oeil", off ? "dz-etat-cache" : "dz-etat-visible", T(off ? "photolab.filtres.activer" : "photolab.filtres.desactiver"));
    oeilT.addEventListener("click", (ev) => { ev.stopPropagation(); PL.executer("layer.smartFilter.disableSmartFilters", { layer: c.id }); });
    const r = el("span", "cq-retrait"); r.style.width = (c.profondeur * 14 + 22) + "px";
    tete.append(oeilT, r, el("span", "cq-sf-nom", T("photolab.filtres.titre")));
    const out = [tete];
    for (const f of filtresDynamiques(c)) {
      const cache = f.visible === false || off;
      const l = el("div", "cq-ligne cq-sf" + (cache ? " cache" : ""));
      l.dataset.filtre = String(f.index);
      const oeil = bouton("cq-oeil", f.visible === false ? "dz-etat-cache" : "dz-etat-visible", T(f.visible === false ? "photolab.calques.montrer" : "photolab.calques.masquer"));
      oeil.addEventListener("click", (ev) => { ev.stopPropagation(); PL.executer("layer.smartFilter.setVisible", { layer: c.id, index: f.index }); });
      const rr = el("span", "cq-retrait"); rr.style.width = (c.profondeur * 14 + 36) + "px";
      const nom = el("span", "cq-sf-nom", libelleFiltre(f.command));
      nom.title = T("photolab.filtres.editer");
      nom.addEventListener("dblclick", (ev) => { ev.stopPropagation(); editerFiltre(c, f); });
      const opt = bouton("cq-sf-opt", "dz-action-reglages", T("photolab.filtres.options"));
      opt.addEventListener("click", (ev) => { ev.stopPropagation(); optionsFiltre(c, f); });
      const sup = bouton("cq-sf-sup", "dz-action-supprimer", T("photolab.filtres.supprimer"));
      sup.addEventListener("click", (ev) => { ev.stopPropagation(); PL.executer("layer.smartFilter.delete", { layer: c.id, index: f.index }); });
      l.append(oeil, rr, nom, opt, sup);
      // glisser pour réordonner dans la pile du même calque
      l.draggable = true;
      l.addEventListener("dragstart", (ev) => { ev.stopPropagation(); ev.dataTransfer.effectAllowed = "move"; ev.dataTransfer.setData(TYPE_FILTRE, c.id + ":" + f.index); });
      l.addEventListener("dragover", (ev) => { if (Array.from(ev.dataTransfer.types || []).includes(TYPE_FILTRE)) { ev.preventDefault(); ev.stopPropagation(); l.classList.add("depot-above"); } });
      l.addEventListener("dragleave", () => l.classList.remove("depot-above"));
      l.addEventListener("drop", (ev) => {
        l.classList.remove("depot-above");
        const [lid, idx] = String(ev.dataTransfer.getData(TYPE_FILTRE) || "").split(":").map(Number);
        const d = deplacementFiltre({ layer: lid, index: idx }, { layer: c.id, index: f.index });
        if (!d) return;
        ev.preventDefault(); ev.stopPropagation();
        PL.executer("layer.smartFilter.move", d);
      });
      out.push(l);
    }
    return out;
  }
  // Double-clic sur un filtre : son dialogue, rempli de ses réglages, AVEC aperçu (layer.smartFilter.setParams joué sur
  // copie) ; la Galerie se rouvre avec sa pile.
  async function editerFiltre(c, f) {
    if (c.id !== actif()) {
      const r = await PL.executer("layer.select", actionSelection(c.id, false, false), { cycle: false });
      if (!(r && r.ok)) return;
      await PL.cycle();
    }
    const vers = (p) => ({ command: "layer.smartFilter.setParams", params: { layer: c.id, index: f.index, params: p } });
    if (f.command === "filter.filterGallery") {
      if (PL.ouvrirGalerie) PL.ouvrirGalerie({ pile: (f.params || {}).effects, filtreDynamique: { layer: c.id, index: f.index } });
      return;
    }
    const e = entreeDe(f.command);
    const champs = e && Array.isArray(e.champs) ? e.champs : [];
    if (!e || !PL.ouvrirReglage || !champsVisibles(champs).length) { PL.signaler(T("photolab.filtres.non_modifiable")); return; }
    PL.ouvrirReglage({ ...e, libelle: libelleFiltre(f.command) }, { initiales: f.params || {}, versCommande: vers });
  }
  // Options de fusion d'un filtre (mode et opacité), aperçu compris.
  function optionsFiltre(c, f) {
    if (!PL.ouvrirReglage) return;
    const champs = [{ cle: "blend", type: "enum", valeurs: MODES_FUSION.map((m) => m.id), optionnel: true },
      { cle: "opacity", type: "number", min: 0, max: 100, entier: true, unite: "%", optionnel: true }];
    PL.ouvrirReglage({ id: "layer.smartFilter.blendingOptions", libelle: T("photolab.filtres.options_de", { nom: libelleFiltre(f.command) }), champs },
      { initiales: { blend: idFusion(f.blend) || "normal", opacity: Math.round((f.opacity == null ? 1 : f.opacity) * 100) }, apercu: true,
        versCommande: (p) => ({ command: "layer.smartFilter.blendingOptions", params: { layer: c.id, index: f.index, blend: p.blend || "normal",
          opacity: Math.round(p.opacity == null ? 100 : p.opacity) / 100 } }) });
  }

  PL.surDoc.push(dessiner);
  PL.surVignettes.push((carte) => {
    if (!PL.etat.doc || enRenommage != null) return;
    PL.$$(".cq-ligne", liste).forEach((l) => {
      const url = carte[l.dataset.id];
      const box = PL.$(".cq-vignette", l);
      if (!url || !box || box.dataset.icone) return;
      let im = PL.$("img", box);
      if (!im) { im = el("img"); im.alt = ""; box.appendChild(im); }
      if (im.getAttribute("src") !== url) im.src = url;
    });
    // t157 : vignettes des masques de fusion (arrivées avec celles des calques)
    PL.$$(".cq-masque[data-masque]", liste).forEach((box) => {
      const url = PL.etat.vignettesMasques && PL.etat.vignettesMasques[box.dataset.masque];
      if (!url) return;
      let im = PL.$("img", box);
      if (!im) { im = el("img"); im.alt = ""; box.appendChild(im); }
      if (im.getAttribute("src") !== url) im.src = url;
    });
  });
  dessiner(null);
}
