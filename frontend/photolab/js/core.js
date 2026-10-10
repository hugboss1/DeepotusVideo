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
import { initPeinture } from "./mod-peinture.js";
import { initPinceaux } from "./mod-pinceaux.js";
import { initEspaces } from "./mod-espaces.js";
import { initAffichage } from "./mod-affichage.js";
import { initNuancier } from "./mod-nuancier.js";
import { initPresets } from "./mod-presets.js";
import { initInfos } from "./mod-infos.js";
import { initCouches } from "./mod-couches.js";
import { initCompositions } from "./mod-compositions.js";
import { initTransformer } from "./mod-transformer.js";
import { initFormes } from "./mod-formes.js";
import { initTrace } from "./mod-trace.js";
import { initTexte } from "./mod-texte.js";
import { initRecherche } from "./mod-recherche.js";
import { initGalerie } from "./mod-galerie.js";
import { initMasquer } from "./mod-masquer.js";
import { initDocuments } from "./mod-documents.js";
import { initMode } from "./mod-mode.js";
import { initRaccourcis } from "./mod-raccourcis.js";
import { initApropos } from "./mod-apropos.js";
import { initPreferences } from "./mod-preferences.js";
import { initMesure } from "./mod-mesure.js";
import { initClavier } from "./mod-clavier.js";
import { initModificateurs } from "./mod-modificateurs.js";
import { initGestionnaire } from "./mod-gestionnaire.js";

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

// Icônes : suite Deepotus Glyph (G4) — /shared/icons/dz-icons.js, chargé par index.html AVANT les modules, rend une
// clé « dz-… » en SVG en ligne (currentColor : nos jetons). Synchrone ; décorative (aria-hidden) : le bouton porte son
// aria-label. Une clé inconnue rend "" (dzIcone l'annonce en console).
PL.icone = function icone(cle, taille = 16) {
  return window.dzIcone ? window.dzIcone(cle, { taille }) : "";
};
PL.hydraterIcones = function hydraterIcones(racine = document) {
  for (const n of PL.$$("[data-icone]", racine)) {
    if (n.dataset.icone && !n.querySelector("svg")) n.insertAdjacentHTML("afterbegin", PL.icone(n.dataset.icone, Number(n.dataset.taille) || 16));
  }
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
initPreferences(PL);     // t159 : juste après l'API — les modules lisent PL.prefs.v au moment où ils servent
initVue(PL);
initOutils(PL);
initMenus(PL);
initApropos(PL);         // t140 : remplace l'à propos simple de mod-menus (crédits + licences)
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
initGalerie(PL);           // t157 : après le dialogue générique (coquille, PL.prendreReglage) ; donne PL.ouvrirGalerie aux menus et aux filtres dynamiques
initMasquer(PL);           // t157 : Sélectionner et masquer (PL.actions["select.selectAndMask"], barre des outils de sélection)
initDocuments(PL);         // t158 : après le fichier (remplace « Fermer », PL.choisirImage) et le dialogue générique (PL.choixDialogue)
initMode(PL);              // t158 : Image › Mode (PL.ouvrirMode pour les menus)
initRaccourcis(PL);
initGestes(PL);       // répartiteur des gestes + aperçu #fourmis, AVANT les outils qui s'y inscrivent
initSelection(PL);
initDeplacer(PL);
initRecadrer(PL);
initPipette(PL);
initPeinture(PL);     // t155 : après la pipette (Alt-clic des pinceaux la réutilise) et le répartiteur des gestes
initPinceaux(PL);     // t155 : après la peinture (PL.optionsPeintureDe) ; branche Fenêtre › Pinceaux… dans PL.actions
initAffichage(PL);    // t152 : après le Déplacement (il enveloppe PL.gestes.move pour les repères) et la vue
// t153 : panneaux Nuancier, Dégradés, Motifs (groupe Couleur), Compositions (groupe Propriétés), Couches (groupe
// Calques), Histogramme et Infos (groupe Infos) — après le cycle (PL.surDoc), la vue (PL.vue.filtre) et la Couleur.
initNuancier(PL);
initPresets(PL, "degrades");
initPresets(PL, "motifs");
initInfos(PL);
initCouches(PL);
initCompositions(PL);
initPresets(PL, "formes");     // t156 : panneaux Formes (groupe Couleur) et Styles (groupe Propriétés)
initPresets(PL, "styles");
initFormes(PL);          // t156 : outils de forme, plume / tracés, texte, Rechercher — après les gestes et les outils
initTrace(PL);
initTexte(PL);
initRecherche(PL);
initMesure(PL);          // t160 : Règle, Comptage, Note, Tranches ; panneaux Mesures et Notes — après les gestes et l'affichage
initModificateurs(PL);   // t159 : Fenêtre › Touches de modification (capture des événements, coche de Fenêtre)
initGestionnaire(PL);    // t159 : Édition › Préréglages (gestionnaire, export / import)
initClavier(PL);         // t159 : Raccourcis clavier et Menus — son décorateur passe APRÈS tous les autres (raccourcis, masques)
initTransformer(PL);     // t154 : après les gestes (PL.gestesPrioritaires, PL.dessinerTransformation) et les outils (barre d'options)

// Onglets du groupe Calques | Historique | Navigateur, et rail d'icônes : calques/historique/navigateur montrent leur
// onglet ; couleur et réglages (Propriétés) replient ou déplient leur groupe.
PL.montrerOnglet = function montrerOnglet(nom) {
  PL.$$("#grpCalques .onglet").forEach((o) => {
    const oui = o.dataset.onglet === nom;
    o.classList.toggle("actif", oui); o.setAttribute("aria-selected", oui ? "true" : "false");
  });
  PL.$$("#grpCalques .groupe-corps").forEach((c) => { c.hidden = c.dataset.vue !== nom; });
  if (nom === "navigateur" && PL.dessinerNavigateur) PL.dessinerNavigateur();
  if (nom === "couches" && PL.couches) { PL.couches.relireVignettes(); PL.couches.dessiner(); }
  if (nom === "traces" && PL.traces) PL.traces.dessiner();
  majRail();
};
function majRail() {
  const onglet = (PL.$("#grpCalques .onglet.actif") || {}).dataset;
  PL.$$("#rail button[data-panneau]").forEach((b) => {
    const p = b.dataset.panneau;
    const oui = p === "couleur" ? !PL.$("#grpCouleur").hidden : p === "reglages" ? !PL.$("#grpProprietes").hidden
      : p === "pinceaux" ? !PL.$("#grpPinceaux").hidden : p === "infos" ? !PL.$("#grpInfos").hidden
        : p === "texte" ? !PL.$("#grpTexte").hidden : onglet && onglet.onglet === p;
    b.classList.toggle("actif", !!oui); b.setAttribute("aria-pressed", oui ? "true" : "false");
  });
}
PL.majRail = majRail;      // t138 B5 : créer un calque de réglage rouvre #grpProprietes s'il était replié
PL.$$("#grpCalques .onglet").forEach((o) => o.addEventListener("click", () => PL.montrerOnglet(o.dataset.onglet)));
PL.$$("#rail button[data-panneau]").forEach((b) => b.addEventListener("click", () => {
  const p = b.dataset.panneau;
  if (p === "couleur") PL.$("#grpCouleur").hidden = !PL.$("#grpCouleur").hidden;
  else if (p === "reglages") PL.$("#grpProprietes").hidden = !PL.$("#grpProprietes").hidden;
  else if (p === "pinceaux") PL.basculerPinceaux();          // t155 : replie / déplie, et relit le moteur à l'ouverture
  else if (p === "infos") { PL.$("#grpInfos").hidden = !PL.$("#grpInfos").hidden; PL.surOngletMontre("infos", PL.ongletDevant("#grpInfos", "data-onglet-in")); }
  else if (p === "texte") { PL.$("#grpTexte").hidden = !PL.$("#grpTexte").hidden; PL.surOngletMontre("texte", PL.ongletDevant("#grpTexte", "data-onglet-tx")); }
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

// t153 : onglets des groupes Couleur (data-onglet-co) et Infos (data-onglet-in), même mécanique que Propriétés ; un
// onglet montré relit ce qu'il affiche (listes du moteur, histogramme, compositions).
PL.ongletDevant = (sel, attr) => { const o = PL.$(sel + " .onglet.actif"); return o ? o.getAttribute(attr) : null; };
PL.surOngletMontre = function surOngletMontre(groupe, nom) {
  if (nom === "degrades" && PL.presets) PL.presets.degrades.relire();
  else if (nom === "motifs" && PL.presets) PL.presets.motifs.relire();
  else if (nom === "histogramme" && PL.histogramme) PL.histogramme.relire();
  else if (nom === "compositions" && PL.compositions) PL.compositions.relire();
  else if ((nom === "formes" || nom === "styles") && PL.presets && PL.presets[nom]) PL.presets[nom].relire();     // t156
  else if (nom === "traces" && PL.traces) PL.traces.dessiner();
  else if (PL.surOngletTexte && ["caractere", "paragraphe", "glyphes", "stylesCar", "stylesPar"].includes(nom)) PL.surOngletTexte(nom);
  else if ((nom === "mesures" || nom === "notes") && PL.mesure) PL.mesure.surOnglet(nom);     // t160
};
for (const [sel, attr, vue] of [["#grpCouleur", "data-onglet-co", "vueCo"], ["#grpInfos", "data-onglet-in", "vueIn"], ["#grpTexte", "data-onglet-tx", "vueTx"]]) {
  const montrer = (nom) => {
    PL.$$(sel + " .onglet").forEach((o) => {
      const oui = o.getAttribute(attr) === nom;
      o.classList.toggle("actif", oui); o.setAttribute("aria-selected", oui ? "true" : "false");
    });
    PL.$$(sel + " .groupe-corps").forEach((c) => { c.hidden = c.dataset[vue] !== nom; });
    PL.surOngletMontre(sel, nom);
  };
  PL.$$(sel + " .onglet").forEach((o) => o.addEventListener("click", () => montrer(o.getAttribute(attr))));
}
for (const nom of ["compositions", "styles"]) {
  PL.$$(`#grpProprietes [data-onglet-pr="${nom}"]`).forEach((o) => o.addEventListener("click", () => PL.surOngletMontre("#grpProprietes", nom)));
}

// t151 : espaces de travail, APRÈS le rail et ses onglets (ils les rejouent pour appliquer une disposition).
initEspaces(PL);

PL.hydraterIcones();
PL.afficherAccueil(true);
window.PL = PL;
