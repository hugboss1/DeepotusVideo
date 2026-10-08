// core.js — le cœur du Photolab (B1) : objet PL, aides communes (sélecteur, icônes en ligne, toasts),
// puis initialisation des modules dans l'ordre. Les autres modules arrivent avec les tâches suivantes.
import { initApi } from "./mod-api.js";
import { initVue } from "./mod-vue.js";
import { initOutils } from "./mod-outils.js";
import { initMenus } from "./mod-menus.js";
import { initCycle } from "./mod-cycle.js";
import { initFichier } from "./mod-fichier.js";
import { initDialogueReglage } from "./mod-dialogue-reglage.js";
import { initCourbes } from "./mod-courbes.js";
import { initReglages } from "./mod-reglages.js";
import { initStyles } from "./mod-styles.js";
import { initCalques } from "./mod-calques.js";
import { initProprietes } from "./mod-proprietes.js";
import { initCouleur } from "./mod-couleur.js";
import { initHistorique } from "./mod-historique.js";
import { initNavigateur } from "./mod-navigateur.js";
import { initGestes } from "./mod-gestes.js";
import { initSelection } from "./mod-selection.js";
import { initDeplacer } from "./mod-deplacer.js";
import { initRecadrer } from "./mod-recadrer.js";
import { initPipette } from "./mod-pipette.js";
import { initRaccourcis } from "./mod-raccourcis.js";

const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);

export const PL = {
  etat: {
    doc: null,          // dernier doc.inspect (null = écran d'accueil)
    outil: "move",
    generation: null,   // suivie par mod-api
  },
  surRendu: [],         // crochets appelés après chaque rendu : PL.surRendu.push(fn)
};

PL.$ = (sel, racine = document) => racine.querySelector(sel);
PL.$$ = (sel, racine = document) => Array.from(racine.querySelectorAll(sel));

// Message dans la barre d'état + toast (erreur = bordure accent).
let minuterie = null;
PL.signaler = function signaler(message, erreur = false) {
  const st = PL.$("#stMessage");
  if (st) { st.textContent = message; st.classList.toggle("erreur", !!erreur); }
  const zone = PL.$("#toasts");
  if (zone) {
    while (zone.children.length >= 3) zone.firstElementChild.remove();      // au plus 3 toasts visibles
    const t = document.createElement("div");
    t.className = "toast" + (erreur ? " erreur" : "");
    t.textContent = message;
    zone.appendChild(t);
    setTimeout(() => t.remove(), erreur ? 6000 : 3500);
  }
  clearTimeout(minuterie);
  minuterie = setTimeout(() => { if (st) st.textContent = ""; }, 8000);
};

// Icônes Lucide de photocraft : fetch puis insertion en ligne, pour que stroke="currentColor" suive nos jetons.
const cacheIcones = new Map();
PL.icone = function icone(nom) {
  if (!cacheIcones.has(nom)) {
    // Un échec (réseau, 404) n'est PAS mis en cache : la prochaine demande réessaie. Les SVG sont décoratifs (le bouton
    // porte son aria-label) : aria-hidden.
    const demande = fetch("icones/" + nom + ".svg")
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error("icône " + nom))))
      .then((svg) => svg.replace(/^\s*<svg/, '<svg aria-hidden="true" focusable="false"'))
      .catch(() => { cacheIcones.delete(nom); return ""; });
    cacheIcones.set(nom, demande);
  }
  return cacheIcones.get(nom);
};
PL.hydraterIcones = async function hydraterIcones(racine = document) {
  const noeuds = PL.$$("[data-icone]", racine);
  await Promise.all(noeuds.map(async (n) => {
    if (n.dataset.icone && !n.querySelector("svg")) n.insertAdjacentHTML("afterbegin", await PL.icone(n.dataset.icone));
  }));
};

// Accueil / document ouvert.
PL.afficherAccueil = function afficherAccueil(oui) {
  const a = PL.$("#accueil");
  if (a) a.hidden = !oui;
  const c = PL.$("#toile");
  if (c) c.hidden = oui;
};
PL.surMoteurRelance = () => PL.afficherAccueil(true);

// Ordre d'initialisation (une tâche = un module) :
//   api (B1) -> vue (B2) -> outils (B3) -> menus (B4) -> cycle (C1) -> panneaux (C2) -> fichier (C1) -> raccourcis (C1)
//   -> gestes et outils du canevas (C3)
// outils avant menus : la barre d'options et PL.choisirOutil existent quand le premier menu s'ouvre. Le cycle avant
// les panneaux et le fichier : ils s'abonnent à PL.surDoc qu'il crée.
initApi(PL);
initVue(PL);
initOutils(PL);
initMenus(PL);
initCycle(PL);
initCalques(PL);
initProprietes(PL);
initCouleur(PL);
initHistorique(PL);
initNavigateur(PL);
initFichier(PL);
initDialogueReglage(PL);   // t138 B2 : après le cycle (PL.surDoc, PL.cycle, PL.executer) ; les menus l'appellent par PL.ouvrirReglage
initCourbes(PL);           // t138 B4 : après le dialogue générique (coquille, PL.prendreReglage) ; Ctrl+M / Ctrl+L y mènent
initReglages(PL);          // t138 B5 : après les Courbes (éditeur réutilisé) ; donne PL.creerReglage aux menus et PL.reglages aux panneaux
initStyles(PL);            // t138 B6 : après le dialogue générique (coquille, PL.prendreReglage) ; donne PL.ouvrirStyles aux menus et au bouton fx
initRaccourcis(PL);
initGestes(PL);       // répartiteur des gestes + aperçu #fourmis, AVANT les outils qui s'y inscrivent
initSelection(PL);
initDeplacer(PL);
initRecadrer(PL);
initPipette(PL);

// Onglets du groupe Calques | Historique | Navigateur, et rail d'icônes : calques/historique/navigateur montrent leur
// onglet ; couleur et réglages (Propriétés) replient ou déplient leur groupe.
PL.montrerOnglet = function montrerOnglet(nom) {
  PL.$$("#grpCalques .onglet").forEach((o) => {
    const oui = o.dataset.onglet === nom;
    o.classList.toggle("actif", oui); o.setAttribute("aria-selected", oui ? "true" : "false");
  });
  PL.$$("#grpCalques .groupe-corps").forEach((c) => { c.hidden = c.dataset.vue !== nom; });
  if (nom === "navigateur" && PL.dessinerNavigateur) PL.dessinerNavigateur();
  majRail();
};
function majRail() {
  const onglet = (PL.$("#grpCalques .onglet.actif") || {}).dataset;
  PL.$$("#rail button[data-panneau]").forEach((b) => {
    const p = b.dataset.panneau;
    const oui = p === "couleur" ? !PL.$("#grpCouleur").hidden : p === "reglages" ? !PL.$("#grpProprietes").hidden : onglet && onglet.onglet === p;
    b.classList.toggle("actif", !!oui); b.setAttribute("aria-pressed", oui ? "true" : "false");
  });
}
PL.majRail = majRail;      // t138 B5 : créer un calque de réglage rouvre #grpProprietes s'il était replié
PL.$$("#grpCalques .onglet").forEach((o) => o.addEventListener("click", () => PL.montrerOnglet(o.dataset.onglet)));
PL.$$("#rail button[data-panneau]").forEach((b) => b.addEventListener("click", () => {
  const p = b.dataset.panneau;
  if (p === "couleur") PL.$("#grpCouleur").hidden = !PL.$("#grpCouleur").hidden;
  else if (p === "reglages") PL.$("#grpProprietes").hidden = !PL.$("#grpProprietes").hidden;
  else PL.montrerOnglet(p);
  majRail();
}));
majRail();

// Libellés d'accessibilité : les aria-label du HTML sont traduits par le runtime (FR -> dictionnaire) ; les boutons du
// rail reçoivent leur nom à partir des clés du dictionnaire pour rester justes si la langue change.
PL.$$("#rail button[data-panneau]").forEach((b) => {
  const cle = b.dataset.panneau === "reglages" ? "photolab.rail.ajustements" : "photolab.panneau." + b.dataset.panneau;
  b.title = T(cle); b.setAttribute("aria-label", b.title);
});

PL.hydraterIcones();
PL.afficherAccueil(true);
window.PL = PL;
