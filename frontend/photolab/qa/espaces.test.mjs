// qa/espaces.test.mjs — t151 (parité L1) : espaces de travail, fonctions PURES de mod-espaces.js.
// Sept espaces fournis (décision Q1), disposition par groupes (ordre, ouvert / replié / masqué, onglet actif),
// barre d'outils 1 ou 2 colonnes et jeu « base », espaces personnels (nom, 20 au plus), verrou, réinitialisation,
// Fenêtre › <panneau> coché / basculé, et le sous-menu Espace de travail reconstruit sur l'arbre des menus.
import {
  GROUPES, FOURNIS, MAX_PERSO, PANNEAUX, BARRES, ID_MENU, HORS_BASE, DISPOSITIONS, etatDefaut, completer, dispositionDe,
  choisir, memoriser, reinitialiser, nouvelEspace, supprimerEspace, basculerVerrou, basculerPanneau, panneauCoche,
  nomEspace, espaceDuMenu, decorerMenus, ACTIONS_ESPACE, ERREURS,
} from "../js/mod-espaces.js";
import { EMPLACEMENTS } from "../js/mod-outils.js";
import { construireMenus, REFUSES, TRAITES_PAR_ECRAN, actionEntree } from "../js/mod-menus.js";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const t = (c, v) => c + (v ? JSON.stringify(v) : "");
// Le dictionnaire tel que la page le charge (dz-i18n-dico.js -> window.DZ_I18N) : les noms des espaces fournis y sont lus.
globalThis.DZ_I18N = JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), "..", "..", "shared", "i18n", "photolab.json"), "utf8"));

// 1. données
check("1.1 sept espaces fournis, dans l'ordre Q1", eq(FOURNIS, ["essentiel", "base", "graphisme", "mouvement", "peinture", "photo", "pixel"]));
check("1.2 six groupes et leurs onglets (t153 : Infos, Nuancier/Dégradés/Motifs, Compositions, Couches ; t156 : Texte, Formes, Styles, Tracés)",
  eq(Object.keys(GROUPES), ["couleur", "proprietes", "pinceaux", "calques", "infos", "texte"]) && GROUPES.calques.includes("historique")
  && eq(GROUPES.couleur, ["couleur", "nuancier", "degrades", "motifs", "formes"]) && eq(GROUPES.infos, ["histogramme", "infos"])
  && eq(GROUPES.calques, ["calques", "couches", "traces", "historique", "navigateur"]) && eq(GROUPES.proprietes, ["proprietes", "ajustements", "styles", "compositions"])
  && eq(GROUPES.texte, ["caractere", "paragraphe", "glyphes", "stylesCar", "stylesPar"]));
check("1.3 chaque espace fourni a une disposition complète et valide", FOURNIS.every((f) => {
  const d = DISPOSITIONS[f];
  return d && [1, 2].includes(d.colonnes) && ["tous", "base"].includes(d.outils) && d.options === true && d.barreOutils === true
    && d.groupes.length === 6 && new Set(d.groupes.map((g) => g.id)).size === 6
    && d.groupes.every((g) => ["ouvert", "replie", "masque"].includes(g.etat) && GROUPES[g.id].includes(g.onglet));
}));
const ess = DISPOSITIONS.essentiel;
check("1.4 Essentiel = l'écran d'avant t151 (deux colonnes, Couleur, Propriétés, Calques ouverts, Pinceaux replié) + Infos et Texte repliés (t153, t156)",
  ess.colonnes === 2 && ess.outils === "tous" && eq(ess.groupes.map((g) => g.id + ":" + g.etat + ":" + g.onglet),
    ["couleur:ouvert:couleur", "proprietes:ouvert:proprietes", "pinceaux:replie:pinceaux", "calques:ouvert:calques", "infos:replie:histogramme", "texte:replie:caractere"]));
check("1.4c t156 : Graphisme et web ouvre le groupe Texte sur Caractère", (({ etat, onglet }) => etat === "ouvert" && onglet === "caractere")(DISPOSITIONS.graphisme.groupes.find((g) => g.id === "texte")));
check("1.4b t153 : Photographie et Mouvement ouvrent l'Histogramme, Peinture le Nuancier",
  ["photo", "mouvement"].every((f) => { const x = DISPOSITIONS[f].groupes.find((g) => g.id === "infos"); return x.etat === "ouvert" && x.onglet === "histogramme"; })
  && DISPOSITIONS.peinture.groupes.find((g) => g.id === "couleur").onglet === "nuancier");
check("1.5 Base : jeu d'outils réduit, une colonne", DISPOSITIONS.base.outils === "base" && DISPOSITIONS.base.colonnes === 1);
check("1.6 Peinture : Pinceaux ouvert", DISPOSITIONS.peinture.groupes.find((g) => g.id === "pinceaux").etat === "ouvert");
check("1.7 Photo : Ajustements devant", DISPOSITIONS.photo.groupes.find((g) => g.id === "proprietes").onglet === "ajustements");
check("1.8 les espaces ne se ressemblent pas deux à deux", new Set(FOURNIS.map((f) => JSON.stringify(DISPOSITIONS[f]))).size === 7);
const premiers = EMPLACEMENTS.map((e) => e[0].id);
check("1.9 HORS_BASE : 5 emplacements de la barre (15 restent)", HORS_BASE.length === 5 && HORS_BASE.every((id) => premiers.includes(id))
  && premiers.filter((id) => !HORS_BASE.includes(id)).length === 15, HORS_BASE);
check("1.10 Fenêtre › <panneau> : 30 panneaux (t153 : +7 ; t156 : +8 Fenêtre, +5 Texte › Panneaux) + 2 barres", Object.keys(PANNEAUX).length === 30 && eq(BARRES, { "window.panel.options": "options", "window.panel.tools": "barreOutils" })
  && Object.values(PANNEAUX).every((p) => GROUPES[p.groupe].includes(p.onglet)));
check("1.11 sept entrées de menu pour les sept espaces (Base : entrée de l'écran)", eq(Object.keys(ID_MENU), FOURNIS) && ID_MENU.base === "pl.espace.base"
  && ID_MENU.essentiel === "window.workspace.essentials" && FOURNIS.every((f) => espaceDuMenu(ID_MENU[f]) === f));
check("1.12 MAX_PERSO = 20", MAX_PERSO === 20);

// 2. état
const e0 = etatDefaut();
check("2.1 défaut", eq(e0, { version: 1, actif: "essentiel", verrouille: false, modifs: {}, perso: [] }));
check("2.2 etatDefaut rend une copie", etatDefaut() !== etatDefaut());
check("2.3 dispositionDe : la fournie, en COPIE", eq(dispositionDe(e0, "peinture"), DISPOSITIONS.peinture) && dispositionDe(e0, "peinture") !== DISPOSITIONS.peinture);
check("2.4 espace inconnu -> Essentiel", eq(dispositionDe(e0, "zorg"), DISPOSITIONS.essentiel));
const incomplete = { ...ess, groupes: [{ id: "calques", etat: "ouvert", onglet: "calques" }] };
const c = completer(incomplete);
check("2.5 completer : les groupes manquants s'ajoutent repliés à la fin (lot futur)", c.groupes.length === 6 && c.groupes[0].id === "calques"
  && c.groupes.slice(1).every((g) => g.etat === "replie" && g.onglet === GROUPES[g.id][0]));
let e = choisir(e0, "photo");
check("2.6 choisir un espace connu", e.actif === "photo" && e0.actif === "essentiel");
check("2.7 choisir un espace inconnu : rien ne change", choisir(e0, "zorg") === e0);
const modif = { ...dispositionDe(e, "photo"), colonnes: 2 };
e = memoriser(e, modif);
check("2.8 memoriser : la disposition modifiée de l'espace actif", eq(e.modifs.photo, modif) && eq(dispositionDe(e, "photo"), modif));
check("2.9 … gardée quand on change d'espace puis revient", eq(dispositionDe(choisir(choisir(e, "base"), "photo"), "photo"), modif));
const ev = basculerVerrou(e);
check("2.10 verrouillé : memoriser ne garde rien", ev.verrouille === true && eq(memoriser(ev, { ...modif, colonnes: 1 }).modifs.photo, modif));
check("2.11 basculerVerrou deux fois", basculerVerrou(ev).verrouille === false);
const er = reinitialiser(e);
check("2.12 reinitialiser : la disposition fournie revient", !("photo" in er.modifs) && eq(dispositionDe(er, "photo"), DISPOSITIONS.photo));

// 3. espaces personnels
let r = nouvelEspace(e0, "  Mon atelier ", modif, true);
check("3.1 nouvelEspace : id perso-1, nom nettoyé, devient actif", r.etat && r.id === "perso-1" && r.etat.actif === "perso-1"
  && eq(r.etat.perso, [{ id: "perso-1", nom: "Mon atelier", disposition: modif }]), r);
const d1 = dispositionDe(r.etat, "perso-1");
check("3.2 dispositionDe d'un espace personnel", eq(d1, modif));
const sansOutils = nouvelEspace(r.etat, "Autre", { ...modif, colonnes: 1, outils: "base" }, false);
check("3.3 sans « Barre d'outils » : colonnes et jeu d'outils d'Essentiel", sansOutils.id === "perso-2"
  && sansOutils.etat.perso[1].disposition.colonnes === 2 && sansOutils.etat.perso[1].disposition.outils === "tous");
check("3.4 nom vide -> erreur vide", nouvelEspace(e0, "   ", modif, true).erreur === "vide");
check("3.5 nom de 65 caractères -> erreur long", nouvelEspace(e0, "x".repeat(65), modif, true).erreur === "long");
check("3.6 nom avec saut de ligne -> erreur long (une ligne)", nouvelEspace(e0, "a\nb", modif, true).erreur === "long");
check("3.7 nom déjà pris (sans casse) -> erreur pris", nouvelEspace(r.etat, "MON ATELIER", modif, true).erreur === "pris");
check("3.8 nom d'un espace fourni (fr ou en, lu dans le dictionnaire) -> erreur pris", ["Peinture", "painting", "Essentiel", "Pixel art", "graphic and web", "Basics"].every((n) => nouvelEspace(e0, n, modif, true).erreur === "pris"));
let plein = e0;
for (let i = 0; i < MAX_PERSO; i++) plein = nouvelEspace(plein, "E" + i, modif, true).etat;
check("3.9 au-delà de 20 -> erreur plein", plein.perso.length === 20 && nouvelEspace(plein, "E99", modif, true).erreur === "plein");
const trou = supprimerEspace(sansOutils.etat, "perso-1");
check("3.10 l'id suivant prend le premier numéro libre", nouvelEspace(trou, "Trois", modif, true).id === "perso-1");
let s = memoriser(choisir(sansOutils.etat, "perso-2"), modif);
s = supprimerEspace(s, "perso-2");
check("3.11 supprimer l'espace actif : retour à Essentiel, changements oubliés", s.actif === "essentiel" && !s.perso.some((p) => p.id === "perso-2") && !("perso-2" in s.modifs));
check("3.12 supprimer un espace fourni : rien", supprimerEspace(e0, "photo") === e0);
check("3.13 nomEspace : fourni par le dictionnaire, personnel par son nom", nomEspace(r.etat, "photo", t) === "photolab.espace.photo" && nomEspace(r.etat, "perso-1", t) === "Mon atelier");

// 4. Fenêtre › <panneau>
const d = dispositionDe(e0, "essentiel");
check("4.1 Calques coché, Historique non (onglet derrière)", panneauCoche(d, "window.panel.layers") && !panneauCoche(d, "window.panel.history"));
check("4.2 Pinceaux replié : non coché", !panneauCoche(d, "window.panel.brushes"));
check("4.3 barres cochées", panneauCoche(d, "window.panel.options") && panneauCoche(d, "window.panel.tools"));
let b = basculerPanneau(d, "window.panel.history");
check("4.4 Historique : groupe ouvert, onglet Historique", b.groupes.find((g) => g.id === "calques").onglet === "historique" && panneauCoche(b, "window.panel.history"));
b = basculerPanneau(b, "window.panel.history");
check("4.5 rebasculer : le groupe est masqué", b.groupes.find((g) => g.id === "calques").etat === "masque" && !panneauCoche(b, "window.panel.layers"));
b = basculerPanneau(d, "window.panel.brushSettings");
check("4.6 Paramètres du pinceau : groupe Pinceaux ouvert sur Paramètres", eq(b.groupes.find((g) => g.id === "pinceaux"), { id: "pinceaux", etat: "ouvert", onglet: "parametres" }));
check("4.7 Outils : la barre se masque puis revient", basculerPanneau(d, "window.panel.tools").barreOutils === false && basculerPanneau(basculerPanneau(d, "window.panel.tools"), "window.panel.tools").barreOutils === true);
check("4.8 basculer ne modifie pas l'original", d.groupes.find((g) => g.id === "calques").onglet === "calques" && d.barreOutils === true);
check("4.9 panneau inconnu : copie inchangée", eq(basculerPanneau(d, "window.panel.actions"), d) && panneauCoche(d, "window.panel.actions") === undefined);

// 5. menus : sous-menu Espace de travail et coches
const ici = dirname(fileURLToPath(import.meta.url));
const cat = JSON.parse(readFileSync(join(ici, "..", "donnees", "menus.json"), "utf8"));
const reg = JSON.parse(readFileSync(join(ici, "..", "..", "..", "backend", "tests", "photocraft_commandes_0.3.0.json"), "utf8"));
const arbre = construireMenus(cat, reg, REFUSES, "fr", t);
const etatP = memoriser(choisir(r.etat, "perso-1"), modif);
const dec = decorerMenus(arbre, etatP, dispositionDe(etatP, "perso-1"), t);
const fen = dec.find((m) => m.nom === "Window");
const es = fen.entrees.find((x) => x.type === "sous-menu" && x.nom === "Workspace");
const lignes = es.entrees.map((x) => (x.type === "separateur" ? "---" : x.id + (x.coche ? "*" : "") + ":" + x.etat));
check("5.1 ordre : 7 fournis, les personnels, ---, réinitialiser, nouveau, supprimer, ---, raccourcis, verrouiller", eq(lignes, [
  "window.workspace.essentials:actif", "pl.espace.base:actif", "window.workspace.graphicAndWeb:actif", "window.workspace.motion:actif",
  "window.workspace.painting:actif", "window.workspace.photography:actif", "window.workspace.pixelArt:actif", "pl.espace.perso-1*:actif",
  "---", "window.workspace.resetWorkspace:actif", "window.workspace.newWorkspace:actif", "window.workspace.deleteWorkspace:actif",
  "---", "edit.keyboardShortcuts:actif", "window.workspace.lockWorkspace:actif"]), lignes);
check("5.2 libellés : dictionnaire pour les fournis, nom pour les personnels, « Réinitialiser » nomme l'espace",
  es.entrees[0].libelle === "photolab.espace.essentiel" && es.entrees[7].libelle === "Mon atelier"
  && es.entrees.find((x) => x.id === "window.workspace.resetWorkspace").libelle === 'photolab.espace.reinitialiser{"nom":"Mon atelier"}');
check("5.3 sans espace personnel : Supprimer inactif ; verrou coché quand verrouillé", (() => {
  const d2 = decorerMenus(arbre, basculerVerrou(e0), dispositionDe(e0, "essentiel"), t);
  const w = d2.find((m) => m.nom === "Window").entrees.find((x) => x.nom === "Workspace").entrees;
  return w.find((x) => x.id === "window.workspace.deleteWorkspace").etat === "inactif" && w.find((x) => x.id === "window.workspace.lockWorkspace").coche === true
    && w.find((x) => x.id === "window.workspace.essentials").coche === true;
})());
const plat = []; const voir = (l) => { for (const x of l) { if (x.type === "sous-menu") voir(x.entrees); else if (x.type === "commande") plat.push(x); } };
voir(fen.entrees);
const panneauxMenu = plat.filter((x) => x.id in PANNEAUX || x.id in BARRES);
check("5.4 les 27 entrées Fenêtre › <panneau> servies (t153 : +7 ; t156 : +8) : actives et cochables", panneauxMenu.length === 27 && panneauxMenu.every((x) => x.etat === "actif" && typeof x.coche === "boolean"),
  panneauxMenu.map((x) => x.id + ":" + x.etat));
check("5.5 coches de Fenêtre suivent la disposition", plat.find((x) => x.id === "window.panel.layers").coche === true && plat.find((x) => x.id === "window.panel.history").coche === false);
check("5.6 les autres panneaux restent « bientôt »", plat.find((x) => x.id === "window.panel.actions").etat === "bientot" && plat.find((x) => x.id === "window.arrange.cascade").etat === "bientot");
check("5.7 decorerMenus ne modifie pas l'arbre reçu", !JSON.stringify(arbre).includes("pl.espace.base"));
check("5.8 entrées d'espace et de panneau traitées par l'écran (jamais envoyées au moteur)",
  [...plat.filter((x) => /^(window\.workspace|pl\.espace|window\.panel)/.test(x.id) && x.etat !== "bientot")].every((x) => actionEntree(x) === "ecran"),
  plat.filter((x) => /^(window\.workspace|pl\.espace|window\.panel)/.test(x.id) && x.etat !== "bientot" && actionEntree(x) !== "ecran").map((x) => x.id));
check("5.9 TRAITES_PAR_ECRAN : les 10 entrées d'espace et les 12 de panneaux", [...ACTIONS_ESPACE, ...Object.keys(PANNEAUX), ...Object.keys(BARRES)].every((id) => TRAITES_PAR_ECRAN.has(id)));
check("5.10 sans le sous-menu (catalogue réduit) : l'arbre est rendu tel quel", eq(decorerMenus([{ nom: "File", entrees: [] }], e0, d, t), [{ nom: "File", entrees: [] }]));

// 6. dictionnaire : chaque clé photolab.espace.* écrite dans le module (et celles composées : espaces, erreurs)
const dico = JSON.parse(readFileSync(join(ici, "..", "..", "shared", "i18n", "photolab.json"), "utf8"));
const src = readFileSync(join(ici, "..", "js", "mod-espaces.js"), "utf8");
const cles = new Set([...src.matchAll(/"(photolab\.espace\.[a-z_]+)"/g)].map((m) => m[1]).filter((k) => !k.endsWith("_")));
for (const f of FOURNIS) cles.add("photolab.espace." + f);
for (const k of Object.values(ERREURS)) cles.add(k);
const manquantes = [...cles].filter((k) => !dico[k] || !dico[k].fr || !dico[k].en);
check("6.1 toutes les clés photolab.espace.* existent en fr et en en", manquantes.length === 0, manquantes.join(" "));
check("6.2 « Réinitialiser » nomme l'espace ({nom}) dans les deux langues", /\{nom\}/.test((dico["photolab.espace.reinitialiser"] || {}).fr || "") && /\{nom\}/.test((dico["photolab.espace.reinitialiser"] || {}).en || ""));
check("6.3 noms des espaces fournis = décision Q1", FOURNIS.map((f) => (dico["photolab.espace." + f] || {}).fr).join("|") === "Essentiel|Base|Graphisme et web|Mouvement|Peinture|Photo|Pixel art");

// 7. côté DOM (épingles) : un groupe Pinceaux ouvert par un espace recharge sa liste ; les clics simulés pendant
// appliquer() ne sont pas mémorisés comme des changements
check("7.1 Pinceaux ouvert par un espace -> PL.montrerPinceaux (liste chargée)", /x\.id === "pinceaux" && x\.etat === "ouvert" && PL\.montrerPinceaux\) \{ PL\.montrerPinceaux\(x\.onglet\)/.test(src));
check("7.2 appliquer() neutralise la mémorisation pendant ses propres clics", /application = true;/.test(src) && /if \(application\) return;/.test(src));

const srcRacc = readFileSync(join(ici, "..", "js", "mod-raccourcis.js"), "utf8");
check("7.3 les raccourcis de Fenêtre (F5-F8) marchent sans document", /!String\(e\.id\)\.startsWith\("window\."\)/.test(srcRacc));

console.log(`espaces : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
