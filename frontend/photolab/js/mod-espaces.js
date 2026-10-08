// mod-espaces.js — t151 (parité L1) : espaces de travail du Photolab et Fenêtre › <panneau>.
// Une disposition décrit les quatre groupes de panneaux (ordre ; ouvert, replié = icône du rail seule, ou masqué ;
// onglet actif), la barre d'outils (1 ou 2 colonnes ; jeu complet ou « base ») et la présence des deux barres. Les
// sept espaces fournis adaptent ceux de l'application de référence (relevé du 08/10, spec §2.2) aux groupes qui
// existent ; chaque espace mémorise sa disposition modifiée ; l'état est enregistré par /api/photolab/espaces
// (photolab_espaces.py, dont GROUPES / FOURNIS / MAX_PERSO sont la copie exacte — banc test_photolab_espaces [3]).
// Écran pur : aucune commande moteur. Fonctions PURES exportées (qa/espaces.test.mjs).
import { EMPLACEMENTS } from "./mod-outils.js";
import { ouvrirDialogue } from "./mod-fichier.js";

// t153 : Nuancier, Dégradés, Motifs (groupe Couleur), Compositions (Propriétés), Couches (Calques), et le groupe Infos.
export const GROUPES = { couleur: ["couleur", "nuancier", "degrades", "motifs"], proprietes: ["proprietes", "ajustements", "compositions"],
  pinceaux: ["pinceaux", "parametres", "source", "predefinis"], calques: ["calques", "couches", "historique", "navigateur"],
  infos: ["histogramme", "infos"] };
export const FOURNIS = ["essentiel", "base", "graphisme", "mouvement", "peinture", "photo", "pixel"];
export const MAX_PERSO = 20;
const MAX_NOM = 64;
// Noms des espaces fournis, en français ET en anglais, lus dans le dictionnaire (window.DZ_I18N) au moment de l'appel :
// un espace personnel ne peut pas les porter. Le pont garde sa propre liste (photolab_espaces.NOMS_FOURNIS).
function nomsFournis() {
  const d = globalThis.DZ_I18N || {};
  const noms = new Set(FOURNIS);
  for (const f of FOURNIS) for (const v of Object.values(d["photolab.espace." + f] || {})) if (typeof v === "string") noms.add(v.toLowerCase());
  return noms;
}
// Message de chaque refus de nouvelEspace (clés écrites en entier : le banc des textes les vérifie).
export const ERREURS = { vide: "photolab.espace.erreur_vide", long: "photolab.espace.erreur_long", pris: "photolab.espace.erreur_pris",
  plein: "photolab.espace.erreur_plein" };

// Entrée de menu de chaque espace fourni : celles du catalogue de photocraft, et une entrée de l'écran pour Base
// (l'amont n'a pas d'« outils de base »).
export const ID_MENU = { essentiel: "window.workspace.essentials", base: "pl.espace.base", graphisme: "window.workspace.graphicAndWeb",
  mouvement: "window.workspace.motion", peinture: "window.workspace.painting", photo: "window.workspace.photography", pixel: "window.workspace.pixelArt" };
export const espaceDuMenu = (id) => {
  const f = FOURNIS.find((k) => ID_MENU[k] === id);
  if (f) return f;
  return typeof id === "string" && id.startsWith("pl.espace.") ? id.slice("pl.espace.".length) : null;
};
// Les entrées du sous-menu Espace de travail que l'écran sert (catalogue).
export const ACTIONS_ESPACE = ["window.workspace.essentials", "window.workspace.photography", "window.workspace.painting", "window.workspace.pixelArt",
  "window.workspace.graphicAndWeb", "window.workspace.motion", "window.workspace.resetWorkspace", "window.workspace.newWorkspace",
  "window.workspace.deleteWorkspace", "window.workspace.lockWorkspace"];
// Fenêtre › <panneau> -> groupe et onglet ; Options / Outils -> une barre.
export const PANNEAUX = {
  "window.panel.color": { groupe: "couleur", onglet: "couleur" },
  "window.panel.properties": { groupe: "proprietes", onglet: "proprietes" },
  "window.panel.adjustments": { groupe: "proprietes", onglet: "ajustements" },
  "window.panel.brushes": { groupe: "pinceaux", onglet: "pinceaux" },
  "window.panel.brushSettings": { groupe: "pinceaux", onglet: "parametres" },
  "window.panel.cloneSource": { groupe: "pinceaux", onglet: "source" },
  "window.panel.toolPresets": { groupe: "pinceaux", onglet: "predefinis" },
  "window.panel.layers": { groupe: "calques", onglet: "calques" },
  "window.panel.history": { groupe: "calques", onglet: "historique" },
  "window.panel.navigator": { groupe: "calques", onglet: "navigateur" },
  "window.panel.swatches": { groupe: "couleur", onglet: "nuancier" },
  "window.panel.gradients": { groupe: "couleur", onglet: "degrades" },
  "window.panel.patterns": { groupe: "couleur", onglet: "motifs" },
  "window.panel.layerComps": { groupe: "proprietes", onglet: "compositions" },
  "window.panel.channels": { groupe: "calques", onglet: "couches" },
  "window.panel.histogram": { groupe: "infos", onglet: "histogramme" },
  "window.panel.info": { groupe: "infos", onglet: "infos" },
};
export const BARRES = { "window.panel.options": "options", "window.panel.tools": "barreOutils" };
// Jeu « base » (référence « Outils de base », ≈ 16 emplacements) : ces emplacements (outil principal) sont cachés.
export const HORS_BASE = ["lasso", "historyBrush", "eraser", "blur", "pathSelection"];

const g = (id, etat, onglet = GROUPES[id][0]) => ({ id, etat, onglet });
const dispo = (colonnes, outils, groupes) => ({ colonnes, outils, options: true, barreOutils: true, groupes });
// Adaptation de la référence (spec §2.2) : Essentiel = l'écran d'avant t151, inchangé.
// t153 : le groupe Infos (Histogramme | Infos) ouvert là où la référence le montre (Mouvement, Photographie) ;
// Peinture et Pixel art ouvrent le Couleur sur le Nuancier (référence Peinture : Nuancier devant).
export const DISPOSITIONS = {
  essentiel: dispo(2, "tous", [g("couleur", "ouvert"), g("proprietes", "ouvert"), g("pinceaux", "replie"), g("calques", "ouvert"), g("infos", "replie")]),
  base: dispo(1, "base", [g("proprietes", "ouvert"), g("calques", "ouvert"), g("couleur", "replie"), g("pinceaux", "masque"), g("infos", "masque")]),
  graphisme: dispo(1, "tous", [g("couleur", "replie"), g("proprietes", "ouvert"), g("calques", "ouvert"), g("pinceaux", "masque"), g("infos", "masque")]),
  mouvement: dispo(1, "tous", [g("infos", "ouvert"), g("proprietes", "ouvert", "ajustements"), g("calques", "ouvert"), g("couleur", "replie"), g("pinceaux", "replie", "parametres")]),
  peinture: dispo(1, "tous", [g("couleur", "ouvert", "nuancier"), g("pinceaux", "ouvert"), g("calques", "ouvert"), g("proprietes", "replie"), g("infos", "masque")]),
  photo: dispo(1, "tous", [g("infos", "ouvert"), g("proprietes", "ouvert", "ajustements"), g("calques", "ouvert"), g("couleur", "replie"), g("pinceaux", "replie", "source")]),
  pixel: dispo(2, "tous", [g("couleur", "ouvert", "nuancier"), g("calques", "ouvert"), g("proprietes", "replie"), g("pinceaux", "replie"), g("infos", "replie")]),
};

const copie = (o) => JSON.parse(JSON.stringify(o));
export const etatDefaut = () => ({ version: 1, actif: "essentiel", verrouille: false, modifs: {}, perso: [] });

// Les groupes absents (un lot futur en ajoute) se placent à la fin, repliés, sur leur premier onglet.
export function completer(d) {
  const c = copie(d);
  for (const id of Object.keys(GROUPES)) if (!c.groupes.some((x) => x.id === id)) c.groupes.push(g(id, "replie"));
  return c;
}
const connu = (etat, id) => FOURNIS.includes(id) || etat.perso.some((p) => p.id === id);
export function dispositionDe(etat, id) {
  const p = etat.perso.find((x) => x.id === id);
  return completer((etat.modifs && etat.modifs[id]) || (p && p.disposition) || DISPOSITIONS[id] || DISPOSITIONS.essentiel);
}
export const choisir = (etat, id) => (connu(etat, id) ? { ...etat, actif: id } : etat);
// La disposition modifiée de l'espace actif ; verrouillé, rien n'est gardé (l'espace revient tel quel).
export const memoriser = (etat, d) => (etat.verrouille ? etat : { ...etat, modifs: { ...etat.modifs, [etat.actif]: copie(d) } });
export function reinitialiser(etat) {
  const modifs = { ...etat.modifs };
  delete modifs[etat.actif];
  return { ...etat, modifs };
}
export const basculerVerrou = (etat) => ({ ...etat, verrouille: !etat.verrouille });

// Nouvel espace -> {etat, id} ou {erreur: vide | long | pris | plein}. Sans « Barre d'outils », la barre d'Essentiel.
export function nouvelEspace(etat, nomBrut, d, avecOutils) {
  const nom = String(nomBrut == null ? "" : nomBrut).trim();
  if (!nom) return { erreur: "vide" };
  if (nom.length > MAX_NOM || [...nom].some((ch) => ch.charCodeAt(0) < 32)) return { erreur: "long" };
  const cle = nom.toLowerCase();
  if (nomsFournis().has(cle) || etat.perso.some((p) => p.nom.toLowerCase() === cle)) return { erreur: "pris" };
  if (etat.perso.length >= MAX_PERSO) return { erreur: "plein" };
  let n = 1;
  while (etat.perso.some((p) => p.id === "perso-" + n)) n++;
  const id = "perso-" + n;
  const disposition = copie(d);
  if (!avecOutils) { disposition.colonnes = DISPOSITIONS.essentiel.colonnes; disposition.outils = DISPOSITIONS.essentiel.outils; }
  return { id, etat: { ...etat, actif: id, perso: [...etat.perso, { id, nom, disposition }] } };
}
export function supprimerEspace(etat, id) {
  if (!etat.perso.some((p) => p.id === id)) return etat;
  const modifs = { ...etat.modifs };
  delete modifs[id];
  return { ...etat, actif: etat.actif === id ? "essentiel" : etat.actif, modifs, perso: etat.perso.filter((p) => p.id !== id) };
}
export function nomEspace(etat, id, t) {
  if (FOURNIS.includes(id)) return t("photolab.espace." + id);
  const p = etat.perso.find((x) => x.id === id);
  return p ? p.nom : id;
}

// Fenêtre › <panneau> : coché quand le panneau se voit (groupe ouvert, onglet devant) ; undefined si inconnu.
export function panneauCoche(d, id) {
  if (id in BARRES) return !!d[BARRES[id]];
  const p = PANNEAUX[id];
  if (!p) return undefined;
  const x = d.groupes.find((y) => y.id === p.groupe);
  return !!x && x.etat === "ouvert" && x.onglet === p.onglet;
}
// Coché -> le groupe se masque ; sinon il s'ouvre sur cet onglet. Les barres se montrent ou se cachent.
export function basculerPanneau(d, id) {
  const c = copie(d);
  if (id in BARRES) { c[BARRES[id]] = !c[BARRES[id]]; return c; }
  const p = PANNEAUX[id];
  if (!p) return c;
  const x = c.groupes.find((y) => y.id === p.groupe);
  if (!x) return c;
  if (panneauCoche(d, id)) x.etat = "masque";
  else { x.etat = "ouvert"; x.onglet = p.onglet; }
  return c;
}

// L'arbre des menus (construireMenus) -> le même, avec le sous-menu Fenêtre › Espace de travail reconstruit (ordre,
// Base, espaces personnels, coches, « Réinitialiser <nom> ») et les coches de Fenêtre › <panneau>. N'altère pas
// l'arbre reçu.
export function decorerMenus(menus, etat, d, t) {
  const sortie = copie(menus);
  const fen = sortie.find((m) => m.nom === "Window");
  if (!fen) return sortie;
  const commande = (id, libelle, extra = {}) => ({ type: "commande", id, libelle, raccourci: "", etat: "actif", champs: [], ...extra });
  const voir = (liste) => {
    for (let i = 0; i < liste.length; i++) {
      const e = liste[i];
      if (e.type === "sous-menu" && e.nom === "Workspace") {
        const trouve = (id) => e.entrees.find((x) => x.id === id);
        const raccourcis = trouve("edit.keyboardShortcuts");
        const garde = (id, extra) => ({ ...(trouve(id) || commande(id, id)), ...extra });
        e.entrees = [
          ...FOURNIS.map((f) => commande(ID_MENU[f], t("photolab.espace." + f), { coche: etat.actif === f })),
          ...etat.perso.map((p) => commande("pl.espace." + p.id, p.nom, { coche: etat.actif === p.id, brut: true })),
          { type: "separateur" },
          garde("window.workspace.resetWorkspace", { libelle: t("photolab.espace.reinitialiser", { nom: nomEspace(etat, etat.actif, t) }), etat: "actif" }),
          garde("window.workspace.newWorkspace", { etat: "actif" }),
          garde("window.workspace.deleteWorkspace", { etat: etat.perso.length ? "actif" : "inactif" }),
          { type: "separateur" },
          ...(raccourcis ? [raccourcis] : []),
          garde("window.workspace.lockWorkspace", { etat: "actif", coche: !!etat.verrouille }),
        ];
      } else if (e.type === "sous-menu") voir(e.entrees);
      else if (e.type === "commande" && (e.id in PANNEAUX || e.id in BARRES)) liste[i] = { ...e, etat: "actif", coche: panneauCoche(d, e.id) };
    }
  };
  voir(fen.entrees);
  return sortie;
}

/* ───────────── côté DOM ───────────── */

const SECTIONS = { couleur: "#grpCouleur", proprietes: "#grpProprietes", pinceaux: "#grpPinceaux", calques: "#grpCalques", infos: "#grpInfos" };
const ONGLET = { couleur: "data-onglet-co", proprietes: "data-onglet-pr", pinceaux: "data-onglet-pi", calques: "data-onglet", infos: "data-onglet-in" };
const RAIL = { reglages: "proprietes", couleur: "couleur", pinceaux: "pinceaux", calques: "calques", historique: "calques", navigateur: "calques",
  infos: "infos" };

export function initEspaces(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const panneaux = PL.$("#panneaux");
  let etat = etatDefaut();
  let courante = dispositionDe(etat, etat.actif);
  let application = false;          // pendant appliquer() : les clics d'onglets simulés ne sont pas des changements
  let minutSauve = null;

  function appliquer(d) {
    application = true;
    try {
      courante = completer(d);
      for (const x of courante.groupes) {
        const sec = PL.$(SECTIONS[x.id]);
        if (!sec) continue;
        panneaux.appendChild(sec);
        sec.hidden = x.etat !== "ouvert";
        // Le groupe Pinceaux ne lit le moteur (préréglages, pointe, sources) qu'à son ouverture : un espace qui l'ouvre
        // passe par PL.montrerPinceaux, sinon sa liste resterait vide (vu en preuve : onglet déjà devant, aucun clic).
        if (x.id === "pinceaux" && x.etat === "ouvert" && PL.montrerPinceaux) { PL.montrerPinceaux(x.onglet); continue; }
        const attr = ONGLET[x.id];
        const o = attr && sec.querySelector(`[${attr}="${x.onglet}"]`);
        if (o && !o.classList.contains("actif")) o.click();
      }
      PL.$$("#rail button[data-panneau]").forEach((b) => {
        const x = courante.groupes.find((y) => y.id === RAIL[b.dataset.panneau]);
        b.hidden = !!x && x.etat === "masque";
      });
      const outils = PL.$("#outils");
      outils.classList.toggle("une-colonne", courante.colonnes === 1);
      outils.hidden = !courante.barreOutils;
      PL.$$("#outils button[data-emplacement]").forEach((b) => {
        b.hidden = courante.outils === "base" && HORS_BASE.includes(EMPLACEMENTS[Number(b.dataset.emplacement)][0].id);
      });
      PL.$("#options").hidden = !courante.options;
      if (PL.majRail) PL.majRail();
      if (PL.dessinerNavigateur) PL.dessinerNavigateur();
      // t153 : un groupe ouvert sur un onglet déjà devant (aucun clic rejoué) relit quand même ce qu'il montre.
      if (PL.surOngletMontre) for (const x of courante.groupes) if (x.etat === "ouvert") PL.surOngletMontre(x.id, x.onglet);
    } finally { application = false; }
    dessinerChoix();
    if (PL.menus && PL.menus.redessiner) PL.menus.redessiner();
  }

  // L'écran tel qu'il est -> disposition (ordre des sections, ouvert / replié / masqué, onglet devant).
  function capturer() {
    const d = copie(courante);
    const ordre = [...panneaux.children].map((sec) => Object.keys(SECTIONS).find((k) => PL.$(SECTIONS[k]) === sec)).filter(Boolean);
    d.groupes = ordre.map((id) => {
      const sec = PL.$(SECTIONS[id]);
      const avant = courante.groupes.find((y) => y.id === id);
      const attr = ONGLET[id];
      const o = attr ? sec.querySelector(`[${attr}].actif`) : null;
      const onglet = o ? o.getAttribute(attr) : GROUPES[id][0];
      const etatG = !sec.hidden ? "ouvert" : avant && avant.etat === "masque" ? "masque" : "replie";
      return { id, etat: etatG, onglet };
    });
    return completer(d);
  }

  async function sauver() {
    clearTimeout(minutSauve);
    minutSauve = setTimeout(async () => {
      try { await PL.api("PUT", "/espaces", etat); } catch (e) { /* signalé par mod-api */ }
    }, 300);
  }
  function changer(nouvel, d) { etat = nouvel; appliquer(d || dispositionDe(etat, etat.actif)); sauver(); }

  // Un clic de rail ou d'onglet a changé l'écran : l'espace actif le mémorise (sauf verrou).
  const apresClic = () => setTimeout(() => {
    if (application) return;
    const d = capturer();
    if (JSON.stringify(d) === JSON.stringify(courante)) return;
    courante = d;
    etat = memoriser(etat, d);
    if (!etat.verrouille) sauver();
    if (PL.menus && PL.menus.redessiner) PL.menus.redessiner();
  }, 0);
  PL.$("#rail").addEventListener("click", apresClic);
  panneaux.addEventListener("click", (ev) => { if (ev.target.closest && ev.target.closest(".onglet")) apresClic(); });

  /* sélecteur dans la barre de menus */
  const choix = document.createElement("select");
  choix.id = "pl-espace"; choix.className = "espace-choix";
  choix.title = T("photolab.espace.choisir"); choix.setAttribute("aria-label", choix.title);
  // Dans une boîte fixe (en haut à droite) : le « ? » de l'aide (mod-didact, posé APRÈS l'élément) reste à côté.
  const boite = document.createElement("div"); boite.className = "espace-boite";
  boite.appendChild(choix);
  document.body.appendChild(boite);
  function dessinerChoix() {
    choix.textContent = "";
    for (const id of [...FOURNIS, ...etat.perso.map((p) => p.id)]) {
      const o = document.createElement("option");
      o.value = id; o.textContent = nomEspace(etat, id, T);
      if (!FOURNIS.includes(id)) o.setAttribute("data-dz-brut", "");          // nom donné par l'utilisateur
      choix.appendChild(o);
    }
    choix.value = etat.actif;
  }
  choix.addEventListener("change", () => changer(choisir(etat, choix.value)));

  /* dialogues */
  async function nouveau() {
    let nom = null, outils = null;
    const r = await ouvrirDialogue(PL, {
      titre: T("photolab.espace.nouveau_titre"),
      construire({ corps }) {
        const l = document.createElement("label"); l.className = "dz-champ";
        const s = document.createElement("span"); s.textContent = T("photolab.espace.nom");
        nom = document.createElement("input"); nom.type = "text"; nom.maxLength = MAX_NOM; nom.value = T("photolab.espace.sans_titre");
        l.append(s, nom);
        const cl = document.createElement("label"); cl.className = "dz-case";
        outils = document.createElement("input"); outils.type = "checkbox"; outils.checked = true;
        const cs = document.createElement("span"); cs.textContent = T("photolab.espace.capturer_outils");
        cl.append(outils, cs);
        const p = document.createElement("p"); p.className = "dz-note"; p.textContent = T("photolab.espace.capture_note");
        corps.append(l, p, cl);
        setTimeout(() => { nom.focus(); nom.select(); }, 0);
      },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("photolab.espace.enregistrer"), principal: true }],
    });
    if (r !== "ok") return;
    const res = nouvelEspace(etat, nom.value, capturer(), outils.checked);
    if (res.erreur) { PL.signaler(T(ERREURS[res.erreur], { max: MAX_PERSO }), true); return; }
    changer(res.etat);
    PL.signaler(T("photolab.espace.cree", { nom: nomEspace(etat, res.id, T) }));
  }
  async function supprimer() {
    if (!etat.perso.length) return;
    let liste = null;
    const r = await ouvrirDialogue(PL, {
      titre: T("photolab.espace.supprimer_titre"),
      construire({ corps }) {
        const l = document.createElement("label"); l.className = "dz-champ";
        const s = document.createElement("span"); s.textContent = T("photolab.espace.espace");
        liste = document.createElement("select");
        for (const p of etat.perso) { const o = document.createElement("option"); o.value = p.id; o.textContent = p.nom; o.setAttribute("data-dz-brut", ""); liste.appendChild(o); }
        l.append(s, liste); corps.appendChild(l);
      },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("photolab.espace.supprimer"), principal: true }],
    });
    if (r !== "ok") return;
    const nom = nomEspace(etat, liste.value, T);
    changer(supprimerEspace(etat, liste.value));
    PL.signaler(T("photolab.espace.supprime", { nom }));
  }

  /* menus */
  PL.actions = PL.actions || {};
  for (const f of FOURNIS) PL.actions[ID_MENU[f]] = () => changer(choisir(etat, f));
  PL.actions["window.workspace.resetWorkspace"] = () => changer(reinitialiser(etat));
  PL.actions["window.workspace.newWorkspace"] = nouveau;
  PL.actions["window.workspace.deleteWorkspace"] = supprimer;
  PL.actions["window.workspace.lockWorkspace"] = () => { etat = basculerVerrou(etat); sauver(); if (PL.menus && PL.menus.redessiner) PL.menus.redessiner(); };
  for (const id of [...Object.keys(PANNEAUX), ...Object.keys(BARRES)]) {
    PL.actions[id] = () => { const d = basculerPanneau(courante, id); etat = memoriser(etat, d); appliquer(d); if (!etat.verrouille) sauver(); };
  }
  // Espaces personnels : une entrée par espace, ids dynamiques.
  PL.actionEspace = (id) => { const k = espaceDuMenu(id); if (k && connu(etat, k)) { changer(choisir(etat, k)); return true; } return false; };
  PL.espaces = { get etat() { return etat; }, get disposition() { return courante; }, decorer: (menus) => decorerMenus(menus, etat, courante, T), appliquer, capturer };

  dessinerChoix();
  // Lecture silencieuse : sans route (ancien backend) ou sans réponse, l'écran garde Essentiel.
  PL.get("/espaces", true).then((lu) => {
    if (!lu || !Array.isArray(lu.perso)) return;
    etat = lu;
    appliquer(dispositionDe(etat, etat.actif));
  }).catch(() => {});
  if (PL.menus && PL.menus.redessiner) PL.menus.redessiner();
}
