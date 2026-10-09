// mod-pinceaux.js — t155 (parité L5) : le groupe de panneaux des outils de peinture, onglets Pinceaux │ Paramètres de
// pinceau │ Source de duplication │ Outils prédéfinis (Fenêtre › Pinceaux, Paramètres du pinceau F5, Source de
// duplication, Outils prédéfinis). Tout passe par le moteur : brush.presets.list / tools.setBrush / brush.get,
// cloneSource.list / set / resetTransform, tool.presets.list / select / new / edit.
// Écart assumé (plan L5) : Paramètres de pinceau = la section « Forme de la pointe » seulement.
// Fonctions PURES exportées (qa/pinceaux.test.mjs).
import { OUTILS_PEINTURE, TAILLE_MIN, TAILLE_MAX, optionsPeinture } from "./mod-peinture.js";
import { ouvrirDialogue } from "./mod-fichier.js";

export const ONGLETS_PINCEAUX = ["pinceaux", "parametres", "source", "predefinis"];
export const ACTIONS_FENETRE = {
  "window.panel.brushes": "pinceaux",
  "window.panel.brushSettings": "parametres",
  "window.panel.cloneSource": "source",
  "window.panel.toolPresets": "predefinis",
};

const borne = (v, a, b) => Math.min(b, Math.max(a, Number(v) || 0));
// Clés du dictionnaire en minuscules (règle de test_i18n_l0) : espacementActif -> espacement_actif.
const snake = (s) => s.replace(/[A-Z]/g, (c) => "_" + c.toLowerCase());

// brush.presets.list -> préréglages dont le nom contient le filtre (sans casse).
export function presetsVisibles(liste, filtre) {
  const l = liste && Array.isArray(liste.presets) ? liste.presets : [];
  const f = String(filtre || "").trim().toLowerCase();
  return l.filter((p) => p && typeof p.name === "string" && (!f || p.name.toLowerCase().includes(f)));
}

// brush.get -> {taille, durete} de l'outil (px entiers, dureté en %) ; null si illisible.
export function pointeVersOptions(b) {
  if (!b || !Number.isFinite(Number(b.size)) || !Number.isFinite(Number(b.hardness))) return null;
  return { taille: Math.round(borne(b.size, TAILLE_MIN, TAILLE_MAX)), durete: Math.round(borne(b.hardness, 0, 1) * 100) };
}

// Un champ de « Forme de la pointe » -> paramètres de tools.setBrush, dans les bornes de CHAMPS_POINTE du pont.
export function paramsPointe(champ, v) {
  switch (champ) {
    case "taille": return { size: Math.round(borne(v, TAILLE_MIN, TAILLE_MAX)) };
    case "durete": return { hardness: borne(v, 0, 100) / 100 };
    case "espacement": return { spacing: borne(v, 1, 1000) / 100 };
    case "espacementActif": return { spacingEnabled: !!v };
    case "angle": return { angle: borne(v, -180, 180) };
    case "rondeur": return { roundness: borne(v, 1, 100) / 100 };
    case "retournerX": return { flipX: !!v };
    case "retournerY": return { flipY: !!v };
    default: return null;
  }
}

// cloneSource.list -> champs de la source active ; null si illisible.
export function sourceVersChamps(liste) {
  const s = liste && Array.isArray(liste.sources) ? liste.sources.find((x) => x && x.index === liste.active) : null;
  if (!s) return null;
  const o = Array.isArray(s.offset) ? s.offset : [0, 0];
  return { index: s.index, source: Array.isArray(s.source) ? s.source : null, decalageX: o[0], decalageY: o[1],
    largeur: s.width, hauteur: s.height, angle: s.rotation, retournerH: !!s.flipH, retournerV: !!s.flipV };
}

// Un champ de la Source de duplication -> paramètres de cloneSource.set pour la source `index`.
export function paramsSource(index, champ, v) {
  const p = { decalage: "offset", largeur: "width", hauteur: "height", angle: "rotation", retournerH: "flipH", retournerV: "flipV" }[champ];
  return p ? { index, [p]: v } : null;
}

// tool.presets.list -> préréglages (tous, ou ceux de l'outil actif).
export function predefinisVisibles(liste, outil, seulementActif) {
  const l = liste && Array.isArray(liste.presets) ? liste.presets : [];
  return l.filter((p) => p && typeof p.name === "string" && (!seulementActif || p.tool === outil));
}
// Outil dont la taille / dureté suivent la pointe du moteur : l'outil courant s'il a une taille, sinon le Pinceau.
export function cibleSynchro(outil) {
  return OUTILS_PEINTURE[outil] && optionsPeinture(outil).some((o) => o.cle === "taille") ? outil : "brush";
}
// Outil d'un préréglage -> un outil de peinture de l'écran (les ids du moteur et de l'écran sont les mêmes) ou null.
export const outilDuPreset = (t) => (Object.prototype.hasOwnProperty.call(OUTILS_PEINTURE, t) ? t : null);

/* ───────────── côté DOM ───────────── */

export function initPinceaux(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const grp = PL.$("#grpPinceaux");
  if (!grp) return;
  // Les réglages du moteur se lisent sans document (session) : /executer direct, comme le panneau Couleur.
  const moteur = async (command, params = {}) => {
    try { return await PL.post("/executer", { command, params }); } catch (e) { return undefined; }     // signalé par mod-api
  };
  const el = (tag, classe, texte) => { const e = document.createElement(tag); if (classe) e.className = classe; if (texte != null) e.textContent = texte; return e; };
  const corps = {};
  for (const n of ONGLETS_PINCEAUX) corps[n] = PL.$(`[data-vue-pi="${n}"]`, grp);
  let actif = "pinceaux";

  // Après un préréglage ou un réglage de la pointe : la taille et la dureté de l'outil COURANT suivent la pointe (chaque
  // outil garde ses réglages, comme dans l'application de référence) ; le Pinceau si l'outil courant n'a pas de taille.
  async function synchroniserPointe() {
    const o = pointeVersOptions(await moteur("brush.get"));
    if (!o) return null;
    const id = cibleSynchro(PL.etat.outil);
    const store = PL.optionsPeintureDe(id);
    if (store.taille !== undefined) store.taille = o.taille;
    if (store.durete !== undefined) store.durete = o.durete;
    if (PL.reconstruireOptions) PL.reconstruireOptions();
    return o;
  }

  /* onglet Pinceaux */
  const recherche = el("input", "pi-recherche"); recherche.type = "search"; recherche.placeholder = T("photolab.pinceaux.rechercher");
  recherche.setAttribute("aria-label", recherche.placeholder);
  const liste = el("ul", "pi-liste");
  corps.pinceaux.append(recherche, liste);
  let presets = null, choisi = null;
  function dessinerPresets() {
    liste.textContent = "";
    for (const p of presetsVisibles(presets, recherche.value)) {
      const li = el("li", "pi-ligne" + (p.name === choisi ? " actif" : ""));
      const b = el("button", "pi-bouton"); b.type = "button";
      const rond = el("span", "pi-rond"); rond.style.setProperty("--pi-durete", String(p.hardness ?? 1));
      const nom = el("span", "pi-nom", p.name); nom.setAttribute("data-dz-brut", "");       // nom du moteur : une donnée
      const t = el("span", "pi-taille", Math.round(p.size || 0) + " px");
      b.append(rond, nom, t);
      b.addEventListener("click", async () => {
        if ((await moteur("tools.setBrush", { preset: p.name })) === undefined) return;
        choisi = p.name; dessinerPresets();
        await synchroniserPointe();
      });
      li.appendChild(b);
      liste.appendChild(li);
    }
  }
  recherche.addEventListener("input", dessinerPresets);

  /* onglet Paramètres de pinceau (Forme de la pointe) */
  const champsPointe = {};
  const ligne = (cle, controle, unite) => {
    const l = el("label", "pi-champ"); l.append(el("span", "pi-lib", T("photolab.pinceaux." + snake(cle))), controle);
    if (unite) l.append(el("span", "pi-unite", unite));
    return l;
  };
  const nombre = (cle, min, max, unite) => {
    const n = el("input"); n.type = "number"; n.min = min; n.max = max; n.step = 1;
    n.addEventListener("change", () => envoyerPointe(cle, Number(n.value)));
    champsPointe[cle] = n;
    return ligne(cle, n, unite);
  };
  const casePointe = (cle) => {
    const c = el("input"); c.type = "checkbox";
    c.addEventListener("change", () => envoyerPointe(cle, c.checked));
    champsPointe[cle] = c;
    return ligne(cle, c);
  };
  corps.parametres.append(el("h4", "pi-titre", T("photolab.pinceaux.forme_pointe")),
    nombre("taille", TAILLE_MIN, TAILLE_MAX, "px"), nombre("durete", 0, 100, "%"), casePointe("espacementActif"),
    nombre("espacement", 1, 1000, "%"), nombre("angle", -180, 180, "°"), nombre("rondeur", 1, 100, "%"),
    casePointe("retournerX"), casePointe("retournerY"));
  async function envoyerPointe(cle, v) {
    const p = paramsPointe(cle, v);
    if (!p) return;
    if ((await moteur("tools.setBrush", p)) === undefined) return;
    await lirePointe();
    await synchroniserPointe();
  }
  async function lirePointe() {
    const b = await moteur("brush.get");
    if (!b) return;
    const v = { taille: Math.round(b.size), durete: Math.round(b.hardness * 100), espacement: Math.round(b.spacing * 100), angle: Math.round(b.angle),
      rondeur: Math.round(b.roundness * 100), espacementActif: !!b.spacingEnabled, retournerX: !!b.flipX, retournerY: !!b.flipY };
    for (const [k, c] of Object.entries(champsPointe)) {
      if (document.activeElement === c) continue;
      if (c.type === "checkbox") c.checked = v[k]; else c.value = v[k];
    }
  }

  /* onglet Source de duplication */
  const boutonsSrc = el("div", "pi-sources");
  for (let i = 0; i < 5; i++) {
    const b = el("button", "pi-source", String(i + 1)); b.type = "button"; b.dataset.index = String(i);
    b.title = T("photolab.pinceaux.source_n", { n: i + 1 }); b.setAttribute("aria-label", b.title);
    b.addEventListener("click", async () => { if ((await moteur("cloneSource.select", { index: i })) !== undefined) lireSource(); });
    boutonsSrc.appendChild(b);
  }
  const etatSrc = el("p", "pi-etat");
  const champsSrc = {};
  const nombreSrc = (cle, min, max, unite) => {
    const n = el("input"); n.type = "number"; n.min = min; n.max = max; n.step = 1;
    n.addEventListener("change", () => envoyerSource(cle));
    champsSrc[cle] = n;
    return ligne(cle, n, unite);
  };
  const caseSrc = (cle) => {
    const c = el("input"); c.type = "checkbox";
    c.addEventListener("change", () => envoyerSource(cle));
    champsSrc[cle] = c;
    return ligne(cle, c);
  };
  const reinit = el("button", "pi-action", T("photolab.pinceaux.reinitialiser")); reinit.type = "button";
  corps.source.append(boutonsSrc, etatSrc, nombreSrc("decalageX", -30000, 30000, "px"), nombreSrc("decalageY", -30000, 30000, "px"),
    nombreSrc("largeur", 1, 1000, "%"), nombreSrc("hauteur", 1, 1000, "%"), nombreSrc("angle", -180, 180, "°"),
    caseSrc("retournerH"), caseSrc("retournerV"), reinit);
  let srcIndex = 0;
  async function envoyerSource(cle) {
    const v = cle === "decalageX" || cle === "decalageY"
      ? paramsSource(srcIndex, "decalage", [Number(champsSrc.decalageX.value) || 0, Number(champsSrc.decalageY.value) || 0])
      : paramsSource(srcIndex, cle, champsSrc[cle].type === "checkbox" ? champsSrc[cle].checked : Number(champsSrc[cle].value));
    if (v && (await moteur("cloneSource.set", v)) !== undefined) lireSource();
  }
  reinit.addEventListener("click", async () => { if ((await moteur("cloneSource.resetTransform", { index: srcIndex })) !== undefined) lireSource(); });
  async function lireSource() {
    const c = sourceVersChamps(await moteur("cloneSource.list"));
    if (!c) return;
    srcIndex = c.index;
    PL.$$(".pi-source", boutonsSrc).forEach((b) => b.classList.toggle("actif", Number(b.dataset.index) === c.index));
    etatSrc.textContent = c.source ? T("photolab.pinceaux.source_posee", { x: Math.round(c.source[0]), y: Math.round(c.source[1]) })
      : T("photolab.pinceaux.source_aucune");
    for (const [k, e] of Object.entries(champsSrc)) {
      if (document.activeElement === e) continue;
      if (e.type === "checkbox") e.checked = !!c[k]; else e.value = Math.round(c[k]);
    }
  }
  PL.lireSource = () => { if (!grp.hidden && actif === "source") lireSource(); };

  /* onglet Outils prédéfinis */
  const seulActif = el("input"); seulActif.type = "checkbox";
  const lSeul = el("label", "pi-champ"); lSeul.append(seulActif, el("span", "pi-lib", T("photolab.pinceaux.outil_actif_seul")));
  const listePre = el("ul", "pi-liste");
  const nomNouveau = el("input", "pi-recherche"); nomNouveau.type = "text"; nomNouveau.maxLength = 64;
  nomNouveau.placeholder = T("photolab.pinceaux.nom_prereglage"); nomNouveau.setAttribute("aria-label", nomNouveau.placeholder);
  const bNouveau = el("button", "pi-action", T("photolab.pinceaux.nouveau_prereglage")); bNouveau.type = "button";
  const rangNouveau = el("div", "pi-rang"); rangNouveau.append(nomNouveau, bNouveau);
  corps.predefinis.append(lSeul, listePre, rangNouveau);
  let predefinis = null;
  function dessinerPredefinis() {
    listePre.textContent = "";
    for (const p of predefinisVisibles(predefinis, PL.etat.outil, seulActif.checked)) {
      const li = el("li", "pi-ligne");
      const b = el("button", "pi-bouton"); b.type = "button";
      const nom = el("span", "pi-nom", p.name); nom.setAttribute("data-dz-brut", "");
      b.append(nom, el("span", "pi-taille", T("photolab.outil." + snake(p.tool))));
      b.addEventListener("click", async () => {
        const r = await moteur("tool.presets.select", { preset: p.name });
        if (r === undefined) return;
        const outil = outilDuPreset(r && r.tool);
        if (outil && PL.choisirOutil) PL.choisirOutil(outil);
        await synchroniserPointe();
      });
      const sup = el("button", "pi-suppr", "×"); sup.type = "button";
      sup.title = T("photolab.pinceaux.supprimer"); sup.setAttribute("aria-label", sup.title + " " + p.name);
      sup.addEventListener("click", async () => {
        const d = window.__dzDialogue;
        const question = T("photolab.pinceaux.supprimer_question", { nom: p.name });
        const oui = d ? await d.confirmer(question, { titre: T("photolab.pinceaux.supprimer"), ok: T("photolab.pinceaux.supprimer") })
          : (await ouvrirDialogue(PL, { titre: T("photolab.pinceaux.supprimer"),
            construire({ corps: c }) { c.appendChild(el("p", "", question)); },
            boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("photolab.pinceaux.supprimer"), principal: true }] })) === "ok";
        if (!oui) return;
        if ((await moteur("tool.presets.edit", { action: "delete", preset: p.name })) !== undefined) lirePredefinis();
      });
      li.append(b, sup);
      listePre.appendChild(li);
    }
  }
  seulActif.addEventListener("change", dessinerPredefinis);
  bNouveau.addEventListener("click", async () => {
    const nom = nomNouveau.value.trim();
    if (!OUTILS_PEINTURE[PL.etat.outil]) { PL.signaler(T("photolab.pinceaux.choisir_outil"), true); return; }
    const p = { tool: PL.etat.outil, includeColor: false };
    if (nom) p.name = nom;
    if ((await moteur("tool.presets.new", p)) !== undefined) { nomNouveau.value = ""; lirePredefinis(); }
  });
  async function lirePredefinis() { predefinis = await moteur("tool.presets.list"); dessinerPredefinis(); }
  PL.surOutil.push(() => { if (!grp.hidden && actif === "predefinis") dessinerPredefinis(); });

  /* onglets */
  async function rafraichir() {
    if (actif === "pinceaux") { if (!presets) presets = await moteur("brush.presets.list"); dessinerPresets(); }
    else if (actif === "parametres") lirePointe();
    else if (actif === "source") lireSource();
    else lirePredefinis();
  }
  function montrer(nom) {
    actif = nom;
    PL.$$(".onglet", grp).forEach((o) => { const oui = o.dataset.ongletPi === nom; o.classList.toggle("actif", oui); o.setAttribute("aria-selected", oui ? "true" : "false"); });
    for (const n of ONGLETS_PINCEAUX) corps[n].hidden = n !== nom;
    if (!grp.hidden) rafraichir();
  }
  PL.$$(".onglet", grp).forEach((o) => o.addEventListener("click", () => montrer(o.dataset.ongletPi)));
  PL.montrerPinceaux = (nom) => { grp.hidden = false; montrer(nom || actif); if (PL.majRail) PL.majRail(); };
  // t159 : après le gestionnaire ou un import de préréglages, la liste est relue au prochain affichage
  PL.pinceaux = { relire: () => { presets = null; if (!grp.hidden) rafraichir(); } };
  PL.basculerPinceaux = () => { grp.hidden = !grp.hidden; if (!grp.hidden) rafraichir(); if (PL.majRail) PL.majRail(); };
  PL.actions = PL.actions || {};
  for (const [id, onglet] of Object.entries(ACTIONS_FENETRE)) PL.actions[id] = () => PL.montrerPinceaux(onglet);
  montrer("pinceaux");
}
