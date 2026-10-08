// mod-calques.js — le panneau Calques (C2, inventaire B §3 / A4) : filtre, mode de fusion, opacité, verrous, fond,
// liste (œil, vignette, nom renommable, cadenas), sélection au clic, glisser pour réordonner, boutons du pied.
// Chaque geste = une commande moteur (layer.*) puis un cycle ; le panneau ne garde en propre QUE les verrous (le moteur
// ne les relit pas) et les groupes repliés. Fonctions PURES exportées (qa/panneaux.test.mjs).

import { brut } from "./mod-cycle.js";

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
  { cle: "transparency", icone: "grid-3x3", cle_libelle: "photolab.verrou.transparence" },
  { cle: "pixels", icone: "brush", cle_libelle: "photolab.verrou.pixels" },
  { cle: "position", icone: "move", cle_libelle: "photolab.verrou.position" },
  { cle: "artboard", icone: "scan", cle_libelle: "photolab.verrou.plan" },
  { cle: "all", icone: "lock", cle_libelle: "photolab.verrou.tout" },
];
export function basculerVerrou(etat, cle) {
  const e = {};
  for (const v of VERROUS) e[v.cle] = !!(etat && etat[v.cle]);
  e[cle] = !e[cle];
  return e;
}

// L'arrière-plan : dernier calque à la racine, nommé « Background » par le moteur (cadenas, comme photocraft).
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
  const icone = (nom, cible) => { cible.dataset.icone = nom; PL.icone(nom).then((svg) => { if (cible.dataset.icone === nom) cible.innerHTML = svg; }); return cible; };
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
  const bientot = (b) => { b.disabled = true; b.classList.add("bientot"); b.title += " — " + T("photolab.outil.bientot"); return b; };
  const bLien = bientot(bouton("", "link", T("photolab.calques.lier")));
  const bFx = bientot(bouton("", null, T("photolab.calques.style"))); bFx.textContent = "fx";
  const bMasque = bientot(bouton("", "scan", T("photolab.calques.masque")));
  const bReglage = bientot(bouton("", "circle", T("photolab.calques.reglage")));
  const bGroupe = bouton("", "folder-plus", T("photolab.calques.nouveau_groupe"));
  const bNouveau = bouton("", "file-plus", T("photolab.calques.nouveau"));
  const bDupliquer = bouton("", "copy", T("photolab.calques.dupliquer"));
  const bFusionner = bouton("", "layers", T("photolab.calques.fusionner"));
  const bSupprimer = bouton("", "trash-2", T("photolab.calques.supprimer"));
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
  bNouveau.addEventListener("click", () => PL.executer("layer.new.layer", {}));
  bGroupe.addEventListener("click", () => PL.executer("layer.groupLayers", {}));
  bDupliquer.addEventListener("click", () => PL.executer("layer.duplicate", {}));
  bFusionner.addEventListener("click", () => PL.executer("layer.mergeDown", {}));
  bSupprimer.addEventListener("click", () => PL.executer("layer.delete", {}));
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
    if (c.groupe) { icone("layers", box); return box; }
    const url = PL.etat.vignettes[String(c.id)];
    if (url) { const im = el("img"); im.alt = ""; im.src = url; im.dataset.id = String(c.id); box.appendChild(im); }
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
    const oeil = bouton("cq-oeil", c.visible === false ? "eye-off" : "eye", T(c.visible === false ? "photolab.calques.montrer" : "photolab.calques.masquer"));
    oeil.addEventListener("click", (ev) => { ev.stopPropagation(); PL.executer("layer.setProps", { layer: c.id, visible: c.visible === false }); });
    const retrait = el("span", "cq-retrait"); retrait.style.width = c.profondeur * 14 + "px";
    const chevron = el("span", "cq-chevron");
    if (c.groupe) {
      const ouvert = c.expanded !== false && !replies.has(c.id);
      const b = bouton("cq-plier", ouvert ? "chevron-down" : "chevron-right", T(ouvert ? "photolab.calques.replier" : "photolab.calques.deplier"));
      b.addEventListener("click", (ev) => { ev.stopPropagation(); if (replies.has(c.id)) replies.delete(c.id); else replies.add(c.id); dessiner(PL.etat.doc); });
      chevron.appendChild(b);
    }
    // Le nom est une donnée de l'utilisateur : la surcouche de traduction n'y touche pas (data-dz-brut).
    const nom = brut(el("span", "cq-nom", c.name || ""));
    nom.addEventListener("dblclick", (ev) => { ev.stopPropagation(); clearTimeout(minutClic); minutClic = null; renommer(c, nom); });
    l.append(oeil, retrait, chevron, vignette(c), nom);
    const idf = idFusion(c.blend);
    if (idf && idf !== "normal" && idf !== "passThrough") {
      const m = MODES_FUSION.find((x) => x.id === idf);
      l.appendChild(el("span", "cq-mode", m ? T(m.cle) : c.blend));
    }
    const v = PL.etat.verrous[c.id];
    if (estFond(c, doc.layers) || (v && Object.values(v).some(Boolean))) {
      const cad = el("span", "cq-cadenas"); cad.title = T("photolab.verrou.tout"); icone("lock", cad); l.appendChild(cad);
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
    for (const b of [bGroupe, bNouveau, bDupliquer, bFusionner, bSupprimer]) b.disabled = !doc;
    if (!doc) return;
    const f = filtre.value.trim().toLowerCase();
    // Filtre : tout déplié (un calque qui correspond se voit même dans un groupe fermé dans le moteur).
    const lignes = aplatirCalques(doc.layers, replies, !!f).filter((c) => !f || String(c.name || "").toLowerCase().includes(f));
    lignes.forEach((c, i) => liste.appendChild(ligne(c, doc, lignes, i)));
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
  });
  dessiner(null);
}
