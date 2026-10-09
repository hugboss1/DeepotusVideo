// qa/menus.test.mjs — menus générés (B4) : catalogue réel donnees/menus.json + registre factice minimal.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { construireMenus, raccourciAffiche, indexRegistre, REFUSES, TRAITES_PAR_ECRAN, actionEntree, aiguillage, cibleDialogue, rechercherEntree, placerPanneau } from "../js/mod-menus.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const catalogue = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));
const src = readFileSync(join(racine, "js/mod-menus.js"), "utf8");

// t138 : chaque entrée porte ses `champs` (GET /commandes, structurés par photolab_registre) — recopiés du registre réel.
const RAYON = { cle: "radius", type: "number", min: 0.1, max: 1000, entier: false, optionnel: false, defaut: 1 };
const registre = [
  { id: "filter.blur.gaussianBlur", label: "Gaussian Blur…", menu: ["Filter", "Blur"], shortcut: null, params: "{\"radius\":0.1..1000=1}", enabled: true, champs: [RAYON] },
  { id: "edit.undo", label: "Undo", menu: ["Edit"], shortcut: "Cmd+Z", params: "{}", enabled: false, champs: [] },
  { id: "image.adjustments.invert", label: "Invert", menu: ["Image", "Adjustments"], shortcut: "Cmd+I", params: "{}", enabled: true, champs: [] },
  { id: "select.all", label: "All", menu: ["Select"], shortcut: "Cmd+A", params: "", enabled: true, champs: [] },
  { id: "layer.layerMask.revealAll", label: "Reveal All", menu: ["Layer", "Layer Mask"], shortcut: null, params: "{\"layer\":id?}", enabled: true,
    champs: [{ cle: "layer", type: "layerId", optionnel: true }] },
  { id: "filter.filterGallery", label: "Filter Gallery…", menu: ["Filter"], shortcut: null, params: "{…}", enabled: true,
    champs: [{ cle: "effects", type: "json", optionnel: false }, { cle: "list", type: "bool", optionnel: false }] },
  { id: "filter.liquify", label: "Liquify…", menu: ["Filter"], shortcut: null, params: "{…}", enabled: true,
    champs: [{ cle: "strokes", type: "struct", optionnel: false }, { cle: "meshSize", type: "number", unite: "px", optionnel: true }] },
  { id: "image.adjustments.curves", label: "Curves…", menu: ["Image", "Adjustments"], shortcut: "Cmd+M", params: "{…}", enabled: true,
    champs: [{ cle: "points", type: "json", optionnel: false }, { cle: "red", type: "json", optionnel: false }] },
  { id: "layer.newAdjustmentLayer.invert", label: "Invert…", menu: ["Layer", "New Adjustment Layer"], shortcut: null, params: "{}", enabled: true, champs: [] },
  { id: "layer.newAdjustmentLayer.levels", label: "Levels…", menu: ["Layer", "New Adjustment Layer"], shortcut: null, params: "{…}", enabled: true,
    champs: [{ cle: "gamma", type: "number", min: 0.01, max: 9.99, entier: false, optionnel: false, defaut: 1 }, { cle: "red", type: "json", optionnel: false }] },
  { id: "layer.layerStyle.dropShadow", label: "Drop Shadow…", menu: ["Layer", "Layer Style"], shortcut: null, params: "{…}", enabled: true,
    champs: [{ cle: "opacity", type: "number", min: 0, max: 100, entier: true, optionnel: false, defaut: 75 }, { cle: "layer", type: "layerId", optionnel: false }] },
  { id: "layer.layerStyle.clear", label: "Clear Layer Style", menu: ["Layer", "Layer Style"], shortcut: null, params: "{\"layer\":id}", enabled: true,
    champs: [{ cle: "layer", type: "layerId", optionnel: false }] },
  // SANS_EDITEUR (mod-champs) : {layer?} seul s'exécuterait directement ; l'écran ne montre pas les filtres dynamiques
  { id: "filter.convertForSmartFilters", label: "Convert for Smart Filters", menu: ["Filter"], shortcut: null, params: "{\"layer\":id?}", enabled: true,
    champs: [{ cle: "layer", type: "layerId", optionnel: true }] },
  // pont ancien (sans `champs`) : on ne devine pas -> dialogue si la description n'est pas vide
  { id: "filter.blur.boxBlur", label: "Box Blur…", menu: ["Filter", "Blur"], shortcut: null, params: "{\"radius\":1..2000=10}", enabled: true },
];
const t = (lang) => (c) => ({
  fr: { "photolab.menu.aide": "Aide", "photolab.menu.apropos": "À propos du Photolab" },
  en: { "photolab.menu.aide": "Help", "photolab.menu.apropos": "About Photolab" },
}[lang][c] || c);

const fr = construireMenus(catalogue, registre, REFUSES, "fr", t("fr"));
const en = construireMenus(catalogue, registre, REFUSES, "en", t("en"));

// 1. structure
check("1.1 dix menus (9 + Aide)", fr.length === 10 && en.length === 10, fr.map((m) => m.nom).join());
check("1.2 ordre du catalogue puis Aide", fr.map((m) => m.nom).join() === "File,Edit,Image,Layer,Type,Select,Filter,View,Window,Aide", fr.map((m) => m.nom).join());
check("1.3 noms affichés fr", fr.slice(0, 9).map((m) => m.nom_affiche).join() === "Fichier,Édition,Image,Calque,Texte,Sélection,Filtre,Affichage,Fenêtre", fr.map((m) => m.nom_affiche).join());
check("1.4 noms affichés en = noms du catalogue", en.slice(0, 9).every((m) => m.nom_affiche === m.nom));
check("1.5 Aide : À propos / About", fr[9].nom_affiche === "Aide" && fr[9].entrees[0].libelle === "À propos du Photolab" && en[9].nom_affiche === "Help" && en[9].entrees[0].libelle === "About Photolab");
check("1.6 Aide : id pl.apropos, actif", fr[9].entrees.length === 1 && fr[9].entrees[0].id === "pl.apropos" && fr[9].entrees[0].etat === "actif");

// 2. menu Fichier
const fichier = fr[0].entrees, fichierEn = en[0].entrees;
check("2.1 File commence par Nouveau…", fichier[0].libelle === "Nouveau…" && fichierEn[0].libelle === "New…", fichier[0].libelle);
check("2.2 raccourci Ctrl+N", fichier[0].raccourci === "Ctrl+N");
const trouver = (entrees, id) => { for (const e of entrees) { if (e.id === id) return e; if (e.entrees) { const r = trouver(e.entrees, id); if (r) return r; } } return null; };
check("2.3 file.saveAs traité par l'écran : actif sans registre", trouver(fichier, "file.saveAs").etat === "actif");
check("2.4 file.export.exportAs actif (sous-menu Exporter)", trouver(fichier, "file.export.exportAs").etat === "actif");
check("2.5 file.placeEmbedded -> bientot", trouver(fichier, "file.placeEmbedded").etat === "bientot");
check("2.6 file.automate.batch -> bientot (préfixe refusé)", trouver(fichier, "file.automate.batch").etat === "bientot");
for (const id of ["file.new", "file.open", "file.close", "file.save", "file.saveAs", "file.export.exportAs"])
  check("2.7 écran : " + id, TRAITES_PAR_ECRAN.has(id));

// 3. sous-menus : position et contenu
const exporter = fichier.find((e) => e.type === "sous-menu" && e.nom === "Export");
check("3.1 sous-menu Exporter dans Fichier", !!exporter && exporter.nom_affiche === "Exporter");
const posExport = fichier.indexOf(exporter), posRevert = fichier.findIndex((e) => e.id === "file.revert");
check("3.2 sous-menu après « Revenir », à la place de son premier enfant", posExport > posRevert && fichier[posExport - 1].type === "separateur", [posRevert, posExport]);
const filtre = fr[6].entrees;
const flou = filtre.find((e) => e.type === "sous-menu" && e.nom === "Blur");
check("3.3 Filtre › Flou", !!flou && flou.nom_affiche === "Flou");
const gauss = flou.entrees.find((e) => e.id === "filter.blur.gaussianBlur");
check("3.4 Flou gaussien…", gauss && gauss.libelle === "Flou gaussien…", gauss && gauss.libelle);
check("3.5 flou gaussien actif, ses champs transportés", gauss.etat === "actif" && Array.isArray(gauss.champs) && gauss.champs[0].cle === "radius" && !("parametres" in gauss));
check("3.6 en : Gaussian Blur…", en[6].entrees.find((e) => e.nom === "Blur").entrees.find((e) => e.id === "filter.blur.gaussianBlur").libelle === "Gaussian Blur…");
check("3.7 flou « moyenne » absent du registre -> bientot", flou.entrees.find((e) => e.id === "filter.blur.average").etat === "bientot");
const profond = fr[3].entrees.find((e) => e.nom === "Smart Objects");
check("3.8 sous-menu de sous-menu (Calque › Objets intelligents › Mode de pile)", profond && profond.entrees.some((e) => e.type === "sous-menu" && e.nom === "Stack Mode"));

// 4. états
check("4.1 enabled:false -> inactif", trouver(fr[1].entrees, "edit.undo").etat === "inactif");
const neg = trouver(fr[2].entrees, "image.adjustments.invert");
check("4.2 négatif : actif, sans champs", neg.etat === "actif" && Array.isArray(neg.champs) && neg.champs.length === 0);
check("4.3 select.all (params vide) : actif sans champs", trouver(fr[5].entrees, "select.all").champs.length === 0);
check("4.5 D9 (Fluidité) -> bientot malgré le registre", trouver(fr[6].entrees, "filter.liquify").etat === "bientot");
check("4.6 galerie de filtres : éditeur sur mesure (t157) -> actif", trouver(fr[6].entrees, "filter.filterGallery").etat === "actif");
check("4.9 Convertir pour les filtres dynamiques : actif (t157, le panneau Calques les montre)", trouver(fr[6].entrees, "filter.convertForSmartFilters").etat === "actif");
check("4.7 courbes : famille sur mesure, jamais « bientôt » par ses opaques", trouver(fr[2].entrees, "image.adjustments.curves").etat === "actif");
check("4.8 entrée absente du registre : champs null", trouver(fr[6].entrees, "filter.blur.average").champs === null);
check("4.4 raccourci converti", neg.raccourci === "Ctrl+I" && trouver(fichier, "file.save").raccourci === "Ctrl+S" && trouver(fr[1].entrees, "edit.undo").raccourci === "");

// 5. séparateurs
function verifSeparateurs(entrees, chemin) {
  let bon = true;
  if (entrees.length && (entrees[0].type === "separateur" || entrees[entrees.length - 1].type === "separateur")) { bon = false; console.error("  séparateur en tête/fin :", chemin); }
  for (let i = 1; i < entrees.length; i++) if (entrees[i].type === "separateur" && entrees[i - 1].type === "separateur") { bon = false; console.error("  séparateurs doublés :", chemin); }
  for (const e of entrees) if (e.type === "sous-menu") { if (!e.entrees.length) { bon = false; console.error("  sous-menu vide :", chemin + ">" + e.nom); } bon = verifSeparateurs(e.entrees, chemin + ">" + e.nom) && bon; }
  return bon;
}
check("5.1 aucun séparateur en tête/fin/doublé, aucun sous-menu vide (fr)", fr.every((m) => verifSeparateurs(m.entrees, m.nom)));
check("5.2 idem (en)", en.every((m) => verifSeparateurs(m.entrees, m.nom)));
// catalogue mal formé : doubles et bords supprimés
const mauvais = { menus_fr: {}, entrees: [
  { chemin: ["A"], separateur: true }, { chemin: ["A"], id: "x.a", libelle_en: "A", libelle_fr: "A", raccourci: null },
  { chemin: ["A"], separateur: true }, { chemin: ["A"], separateur: true }, { chemin: ["A"], id: "x.b", libelle_en: "B", libelle_fr: "B", raccourci: null },
  { chemin: ["A"], separateur: true } ] };
const mm = construireMenus(mauvais, [], REFUSES, "en", t("en"))[0].entrees;
check("5.3 catalogue mal formé nettoyé", mm.map((e) => e.type === "separateur" ? "-" : e.id).join() === "x.a,-,x.b", mm.map((e) => e.type === "separateur" ? "-" : e.id).join());
// un sous-menu dont tous les enfants disparaissent n'existe pas (ici : aucun, mais le séparateur seul ne fait pas un menu)
const seul = construireMenus({ menus_fr: {}, entrees: [{ chemin: ["A", "B"], separateur: true }, { chemin: ["A"], id: "x.a", libelle_en: "A", libelle_fr: "A", raccourci: null }] }, [], REFUSES, "en", t("en"))[0].entrees;
check("5.4 sous-menu réduit à un séparateur supprimé", seul.length === 1 && seul[0].id === "x.a");

// 6. raccourcis
check("6.1 fr", raccourciAffiche("Cmd+Shift+N", "fr") === "Ctrl+Maj+N");
check("6.2 en", raccourciAffiche("Cmd+Shift+N", "en") === "Ctrl+Shift+N");
check("6.3 Cmd+=", raccourciAffiche("Cmd+=", "fr") === "Ctrl+=" && raccourciAffiche("Cmd+=", "en") === "Ctrl+=");
check("6.4 ordre conservé, Alt inchangé", raccourciAffiche("Cmd+Alt+Shift+W", "fr") === "Ctrl+Alt+Maj+W");
check("6.5 touches seules", raccourciAffiche("F12", "fr") === "F12" && raccourciAffiche("Q", "fr") === "Q");
check("6.6 vide/null", raccourciAffiche(null, "fr") === "" && raccourciAffiche("", "en") === "");
check("6.7 ponctuation", raccourciAffiche("Cmd+-", "fr") === "Ctrl+-" && raccourciAffiche("Cmd+Shift+[", "fr") === "Ctrl+Maj+[");

// 7. refuses : copie de PREFIXES_REFUSES du pont
const py = readFileSync(join(racine, "../../backend/app/services/photolab_moteur.py"), "utf8");
const m = py.match(/PREFIXES_REFUSES = \(([\s\S]*?)\)\s*#/);
const prefPy = m ? [...m[1].matchAll(/"([^"]+)"/g)].map((x) => x[1].toLowerCase()) : [];
check("7.1 REFUSES identique à PREFIXES_REFUSES (lecture du source Python)", prefPy.length > 0 && JSON.stringify(prefPy) === JSON.stringify(REFUSES.map((x) => x.toLowerCase())), JSON.stringify([prefPy, REFUSES]));
check("7.2 REFUSES en minuscules", REFUSES.every((x) => x === x.toLowerCase()));

// 8. actions
const idx = indexRegistre(registre);
check("8.1 indexRegistre (tableau)", idx.get("edit.undo").enabled === false && indexRegistre({ commands: registre }).size === registre.length && indexRegistre(null).size === 0);
check("8.2 parametresRequis supprimé (remplacé par les champs)", !/parametresRequis/.test(src));
check("8.3 action écran", actionEntree(trouver(fichier, "file.new")) === "ecran");
check("8.4 action à propos", actionEntree(fr[9].entrees[0]) === "apropos");
check("8.5 action exécuter", actionEntree(neg) === "executer");
check("8.6 Flou gaussien -> dialogue par ses champs", actionEntree(gauss) === "dialogue");
check("8.7 bientôt / inactif -> rien", actionEntree(trouver(fichier, "file.placeEmbedded")) === "rien" && actionEntree(trouver(fr[1].entrees, "edit.undo")) === "rien");
const reveler = trouver(fr[3].entrees, "layer.layerMask.revealAll");
check("8.8 Révéler tout (layer caché seul) -> exécuter", reveler && actionEntree(reveler) === "executer");
const courbes = trouver(fr[2].entrees, "image.adjustments.curves");
check("8.9 Courbes (que des opaques, famille sur mesure) -> dialogue", actionEntree(courbes) === "dialogue");
const calqueNeg = trouver(fr[3].entrees, "layer.newAdjustmentLayer.invert");
check("8.10 calque de réglage Négatif (aucun champ) -> exécuter", calqueNeg && actionEntree(calqueNeg) === "executer");
const effacer = trouver(fr[3].entrees, "layer.layerStyle.clear");
check("8.11 Effacer le style (layer seul, hors familles de style) -> exécuter", effacer && actionEntree(effacer) === "executer");
const boite = trouver(fr[6].entrees, "filter.blur.boxBlur");
check("8.12 pont sans champs : description non vide -> dialogue (jamais d'exécution à l'aveugle)", boite && boite.champs === null && actionEntree(boite) === "dialogue");
check("8.13 actionEntree sans champs : vide -> exécuter", actionEntree({ type: "commande", id: "x.y", etat: "actif", champs: [] }) === "executer"
  && actionEntree({ type: "commande", id: "x.y", etat: "actif" }) === "dialogue");

// 12. aiguillage des familles sur mesure (PUR)
check("12.1 courbes / niveaux destructifs", aiguillage("image.adjustments.curves") === "courbes" && aiguillage("image.adjustments.levels") === "niveaux");
check("12.2 calques de réglage (courbes et niveaux compris)", aiguillage("layer.newAdjustmentLayer.levels") === "reglage" && aiguillage("layer.newAdjustmentLayer.curves") === "reglage"
  && aiguillage("layer.newAdjustmentLayer.invert") === "reglage");
check("12.3 les 10 styles et blendingOptions", ["dropShadow", "innerShadow", "outerGlow", "innerGlow", "stroke", "colorOverlay", "gradientOverlay",
  "patternOverlay", "bevelEmboss", "satin", "blendingOptions"].every((k) => aiguillage("layer.layerStyle." + k) === "style"));
check("12.4 autres layerStyle -> générique", ["clear", "copyLayerStyle", "pasteLayerStyle", "globalLight", "scaleEffects", "createLayer", "hideAllEffects"]
  .every((k) => aiguillage("layer.layerStyle." + k) === "generique"));
check("12.5 le reste -> générique", aiguillage("filter.blur.gaussianBlur") === "generique" && aiguillage("image.adjustments.hueSaturation") === "generique"
  && aiguillage("layer.newAdjustmentLayer") === "generique" && aiguillage("") === "generique" && aiguillage(null) === "generique");
// cibleDialogue : où va un « dialogue » selon les fonctions que l'écran possède déjà (B2-B6 les ajoutent une à une).
const tout = { ouvrirReglage: 1, ouvrirCourbes: 1, ouvrirNiveaux: 1, creerReglage: 1, ouvrirStyles: 1 };
const lev = trouver(fr[3].entrees, "layer.newAdjustmentLayer.levels"), ombre = trouver(fr[3].entrees, "layer.layerStyle.dropShadow");
check("12.6 tout présent : famille sur mesure d'abord", cibleDialogue(courbes, tout) === "courbes" && cibleDialogue(lev, tout) === "reglage"
  && cibleDialogue(ombre, tout) === "style" && cibleDialogue(gauss, tout) === "generique");
check("12.7 rien de présent : bientot", [courbes, lev, ombre, gauss].every((e) => cibleDialogue(e, {}) === "bientot"));
check("12.8 générique seul : repli pour une famille qui a des champs visibles, bientot sinon",
  cibleDialogue(lev, { ouvrirReglage: 1 }) === "generique" && cibleDialogue(ombre, { ouvrirReglage: 1 }) === "generique"
  && cibleDialogue(courbes, { ouvrirReglage: 1 }) === "bientot" && cibleDialogue(gauss, { ouvrirReglage: 1 }) === "generique");
check("12.9 sur mesure sans générique", cibleDialogue(courbes, { ouvrirCourbes: 1 }) === "courbes" && cibleDialogue(gauss, { ouvrirCourbes: 1 }) === "bientot");
// P3 livrée : plus de message « arrive en P3 » ; un dialogue introuvable dit « bientôt » comme le reste du menu.
const dico = JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8"));
check("12.11 photolab.menu.p3 retirée (source et dictionnaire), photolab.menu.bientot présente",
  !/photolab\.menu\.p3/.test(src) && !("photolab.menu.p3" in dico) && !!dico["photolab.menu.bientot"]);
// activer : l'exécution directe passe par la file FIFO (PL.executer), plus jamais PL.post("/executer") en direct.
check("12.10 activer : exécuter par PL.executer, pas de post direct", /PL\.executer\(e\.id, \{\}\)/.test(src) && !/PL\.post\("\/executer"/.test(src));

// 13. styles de calque : le menu prend le vocabulaire du dictionnaire (photolab.styles.<k>) quand il existe, comme le
// dialogue (libelleStyle) — « Contour… » et non « Contourner… » du catalogue ; ponctuation du catalogue gardée.
const DICO_STYLES = {
  fr: { "photolab.styles.bevelemboss": "Biseautage et estampage", "photolab.styles.stroke": "Contour", "photolab.styles.options_fusion": "Options de fusion" },
  en: { "photolab.styles.bevelemboss": "Bevel & Emboss", "photolab.styles.stroke": "Stroke", "photolab.styles.options_fusion": "Blending options" },
};
const tS = (lang) => (c) => DICO_STYLES[lang][c] || t(lang)(c);
const frS = construireMenus(catalogue, registre, REFUSES, "fr", tS("fr")), enS = construireMenus(catalogue, registre, REFUSES, "en", tS("en"));
const lib = (menus, k) => trouver(menus[3].entrees, "layer.layerStyle." + k).libelle;
check("13.1 fr : Contour…, Biseautage et estampage…, Options de fusion…", lib(frS, "stroke") === "Contour…" && lib(frS, "bevelEmboss") === "Biseautage et estampage…"
  && lib(frS, "blendingOptions") === "Options de fusion…", [lib(frS, "stroke"), lib(frS, "bevelEmboss"), lib(frS, "blendingOptions")]);
check("13.2 en : Stroke…, Bevel & Emboss…, Blending options…", lib(enS, "stroke") === "Stroke…" && lib(enS, "bevelEmboss") === "Bevel & Emboss…"
  && lib(enS, "blendingOptions") === "Blending options…", [lib(enS, "stroke"), lib(enS, "bevelEmboss"), lib(enS, "blendingOptions")]);
check("13.3 sans clé au dictionnaire : libellé du catalogue (Ombre portée…, Effacer le style de calque)", lib(frS, "dropShadow") === "Ombre portée…"
  && lib(frS, "clear") === "Effacer le style de calque" && lib(enS, "dropShadow") === "Drop Shadow…");
check("13.4 traducteur par défaut : le catalogue tel quel", lib(fr, "stroke") === "Contourner…" && lib(en, "bevelEmboss") === "Bevel & Emboss…");
check("13.5 menus.json intact (Contourner… au catalogue)", catalogue.entrees.find((e) => e.id === "layer.layerStyle.stroke").libelle_fr === "Contourner…");

// 9. recherche d'une entrée par raccourci (Ctrl+Z, etc. : le moteur seul dit si la commande existe)
check("9.1 rechercherEntree par id", rechercherEntree(fr, "image.adjustments.invert").id === "image.adjustments.invert" && rechercherEntree(fr, "nimporte") === null);

// 11. placement des panneaux dans la fenêtre (M11) : sous-menu retourné à gauche s'il déborde, hauteur et haut bornés
const F = { w: 1000, h: 700 };
const sm = placerPanneau({ gauche: 100, droite: 340, haut: 50, bas: 74 }, { w: 240, h: 200 }, F, "droite");
check("11.1 sous-menu à droite de la ligne", sm.x === 338 && sm.y === 46 && sm.maxH >= 200, JSON.stringify(sm));
const smG = placerPanneau({ gauche: 800, droite: 960, haut: 50, bas: 74 }, { w: 240, h: 200 }, F, "droite");
check("11.2 débordement à droite : retourné à gauche", smG.x === 800 - 240 + 2, JSON.stringify(smG));
const bas = placerPanneau({ gauche: 100, droite: 340, haut: 600, bas: 624 }, { w: 240, h: 300 }, F, "droite");
check("11.3 sous-menu trop bas : remonté dans la fenêtre", bas.y + 300 <= F.h - 8 && bas.y >= 8, JSON.stringify(bas));
const haut = placerPanneau({ gauche: 10, droite: 60, haut: 31, bas: 31 }, { w: 240, h: 900 }, F, "bas");
check("11.4 menu de la barre : sous le bouton, hauteur bornée à la fenêtre", haut.y === 31 && haut.maxH === F.h - 31 - 8 && haut.x === 10, JSON.stringify(haut));
const bordD = placerPanneau({ gauche: 900, droite: 960, haut: 31, bas: 31 }, { w: 240, h: 100 }, F, "bas");
check("11.5 menu de la barre : borné au bord droit", bordD.x + 240 <= F.w - 2, JSON.stringify(bordD));
const tiny = placerPanneau({ gauche: 0, droite: 50, haut: 0, bas: 10 }, { w: 240, h: 900 }, { w: 300, h: 100 }, "droite");
check("11.6 fenêtre minuscule : jamais de y négatif", tiny.y >= 0 && tiny.x >= 0, JSON.stringify(tiny));

// 10. aucune chaîne française en dur dans le module (C4) ni mot interdit
check("10.1 sans ArtCraft/Discord/Photoshop", !/artcraft|discord|photoshop/i.test(src));
check("10.2 pas de texte français accentué en dur", !/[éèêàùçô]/i.test(src.replace(/\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "")));

console.log(`menus : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
