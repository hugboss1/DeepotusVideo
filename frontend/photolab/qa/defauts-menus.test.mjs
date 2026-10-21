// qa/defauts-menus.test.mjs — défauts des menus relevés par le catalogue de l'assistant (#415), relevé du 20/10/2026
// (docs/superpowers/specs/2026-10-20-photolab-defauts-menus-releve.md). Lot A : entrées grisées « bientôt », outils
// d'Image › Analyse, libellé sans « … », raccourcis de l'écran, masque de calque Activer / Désactiver, Lier / Délier.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { construireMenus, REFUSES, TRAITES_PAR_ECRAN, NECESSITE_DOC, BIENTOT_ECRAN, OUTILS_ANALYSE, SANS_POINTS, actionEntree, rechercherEntree } from "../js/mod-menus.js";
import { RACCOURCIS_ECRAN, raccourciEcran } from "../js/mod-raccourcis.js";
import { decorerTexte, COMPOSEUR, PREFS_DEFAUT, basculerPref } from "../js/mod-texte.js";
import { decorerMasque, IDS_MASQUE } from "../js/mod-calques.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const catalogue = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));

// Registre factice : chaque id du catalogue existe, actif, sans champ — le pire cas (tout s'exécuterait).
const registre = catalogue.entrees.filter((e) => e.id).map((e) => ({ id: e.id, enabled: true, champs: [] }));
const DICO = { "photolab.touche.delete": { fr: "Suppr", en: "Delete" }, "photolab.menu.masque_activer": { fr: "Activer le masque de calque", en: "Enable Layer Mask" },
  "photolab.menu.masque_desactiver": { fr: "Désactiver le masque de calque", en: "Disable Layer Mask" },
  "photolab.menu.masque_lier": { fr: "Lier le masque de calque", en: "Link Layer Mask" }, "photolab.menu.masque_delier": { fr: "Délier le masque de calque", en: "Unlink Layer Mask" } };
const tr = (lang) => (c) => (DICO[c] ? DICO[c][lang] : c);
const fr = construireMenus(catalogue, registre, REFUSES, "fr", tr("fr"));
const en = construireMenus(catalogue, registre, REFUSES, "en", tr("en"));

// 1. entrées grisées « bientôt » (19)
const VIDEO = ["newBlankVideoLayer", "newVideoLayerFromFile", "insertBlankFrame", "duplicateFrame", "deleteFrame", "replaceFootage", "interpretFootage",
  "showAlteredVideo", "restoreFrame", "restoreAllFrames", "reloadFrame", "rasterize"].map((k) => "layer.videoLayers." + k);
const GRISEES = [...VIDEO, "layer.rasterize.video", "edit.purge.videoCache", "edit.colorSettings", "layer.smartObjects.revealInFinder",
  "edit.perspectiveWarp", "layer.smartObjects.perspectiveWarp", COMPOSEUR];
check("1.1 les 19 entrées grisées sont nommées une à une", GRISEES.length === 19 && GRISEES.every((id) => BIENTOT_ECRAN.has(id)) && BIENTOT_ECRAN.size === 19,
  [...BIENTOT_ECRAN].filter((id) => !GRISEES.includes(id)));
const etats = GRISEES.map((id) => [id, rechercherEntree(fr, id)]);
check("1.2 « bientôt » même quand le moteur les dit actives et sans champ", etats.every(([, e]) => e && e.etat === "bientot" && actionEntree(e) === "rien"),
  etats.filter(([, e]) => !e || e.etat !== "bientot").map(([id]) => id));
check("1.3 le composeur n'est plus servi par l'écran", !TRAITES_PAR_ECRAN.has(COMPOSEUR));
const texte = decorerTexte([{ entrees: [{ type: "commande", id: COMPOSEUR, etat: "bientot" }] }], { ...PREFS_DEFAUT, composeur: true });
check("1.4 menu Texte : le composeur reste grisé, sans coche", texte[0].entrees[0].etat === "bientot" && texte[0].entrees[0].coche === undefined);
check("1.5 basculerPref ignore le composeur", JSON.stringify(basculerPref(PREFS_DEFAUT, COMPOSEUR)) === JSON.stringify(PREFS_DEFAUT));
check("1.6 Purger › Tout et les autres purges restent actives", ["edit.purge.all", "edit.purge.undo", "edit.purge.clipboard", "edit.purge.histories"]
  .every((id) => rechercherEntree(fr, id).etat === "actif"));

// 2. Image › Analyse › Outil Règle / Outil Compteur -> l'outil de l'écran
check("2.1 deux outils", JSON.stringify(OUTILS_ANALYSE) === JSON.stringify({ "image.analysis.rulerTool": "ruler", "image.analysis.countTool": "count" }));
check("2.2 servis par l'écran, sans document requis", Object.keys(OUTILS_ANALYSE).every((id) => TRAITES_PAR_ECRAN.has(id) && !NECESSITE_DOC.has(id)
  && actionEntree(rechercherEntree(fr, id)) === "ecran"));

// 3. Plan de travail d'après un groupe : s'exécute, donc sans « … » (menus.json intact)
const pt = "layer.new.artboardFromGroup";
check("3.1 libellé sans « … » (fr, en)", SANS_POINTS.has(pt) && rechercherEntree(fr, pt).libelle === "Plan de travail d'après un groupe"
  && rechercherEntree(en, pt).libelle === "Artboard from Group", [rechercherEntree(fr, pt).libelle, rechercherEntree(en, pt).libelle]);
check("3.2 menus.json garde « … »", /…$/.test(catalogue.entrees.find((e) => e.id === pt).libelle_fr));

// 4. raccourcis de l'écran : Ctrl+C / X / V, Suppr ; affichés dans le menu (Annuler / Rétablir aussi)
check("4.1 Ctrl+C, Ctrl+X, Ctrl+V, Suppr", RACCOURCIS_ECRAN["ctrl+c"] === "edit.copy" && RACCOURCIS_ECRAN["ctrl+x"] === "edit.cut"
  && RACCOURCIS_ECRAN["ctrl+v"] === "edit.paste" && RACCOURCIS_ECRAN.delete === "edit.clear");
check("4.2 raccourciEcran : Suppr seul est pris, une lettre seule ou Maj+Suppr non", raccourciEcran("delete") === "edit.clear" && raccourciEcran("ctrl+v") === "edit.paste"
  && raccourciEcran("v") === null && raccourciEcran("shift+delete") === null && raccourciEcran("") === null);
const racc = (m, id) => rechercherEntree(m, id).raccourci;
check("4.3 affichés en français", racc(fr, "edit.copy") === "Ctrl+C" && racc(fr, "edit.cut") === "Ctrl+X" && racc(fr, "edit.paste") === "Ctrl+V"
  && racc(fr, "edit.clear") === "Suppr" && racc(fr, "edit.undo") === "Ctrl+Z" && racc(fr, "edit.redo") === "Ctrl+Maj+Z" && racc(fr, "select.inverse") === "Ctrl+Maj+I",
  ["edit.copy", "edit.clear", "edit.undo", "edit.redo", "select.inverse"].map((id) => racc(fr, id)));
check("4.4 affichés en anglais", racc(en, "edit.clear") === "Delete" && racc(en, "edit.redo") === "Ctrl+Shift+Z");
check("4.5 aucun raccourci de l'écran ne double un raccourci du catalogue", catalogue.entrees.every((e) => !e.raccourci
  || !Object.keys(RACCOURCIS_ECRAN).includes(e.raccourci.toLowerCase().replace("cmd", "ctrl"))));

// 5. masque de calque : libellé selon l'état suivi par le panneau Calques, grisé sans masque
const menuMasque = () => [{ nom: "Layer", entrees: [{ type: "sous-menu", nom: "Layer Mask", entrees: [
  { type: "commande", id: "layer.layerMask.enabled", libelle: "Activer le masque de calque", etat: "actif" },
  { type: "commande", id: "layer.layerMask.linked", libelle: "Lier le masque de calque", etat: "actif" }] }] }];
const dm = (calque, em, lang = "fr") => decorerMasque(menuMasque(), calque, em, tr(lang))[0].entrees[0].entrees;
check("5.1 deux entrées servies par l'écran, document requis", IDS_MASQUE.every((id) => TRAITES_PAR_ECRAN.has(id) && NECESSITE_DOC.has(id)));
check("5.2 masque actif et lié (défaut) : Désactiver / Délier", JSON.stringify(dm({ id: 3, hasMask: true }, undefined).map((e) => e.libelle))
  === JSON.stringify(["Désactiver le masque de calque", "Délier le masque de calque"]));
check("5.3 masque désactivé et délié : Activer / Lier", JSON.stringify(dm({ id: 3, hasMask: true }, { active: false, lie: false }).map((e) => e.libelle))
  === JSON.stringify(["Activer le masque de calque", "Lier le masque de calque"]));
check("5.4 anglais", dm({ id: 3, hasMask: true }, { active: true, lie: false }, "en").map((e) => e.libelle).join("|") === "Disable Layer Mask|Link Layer Mask");
check("5.5 calque sans masque ou pas de calque : grisées", dm({ id: 3, hasMask: false }).every((e) => e.etat === "inactif") && dm(null).every((e) => e.etat === "inactif"));
check("5.6 une entrée « bientôt » le reste", decorerMasque([{ entrees: [{ type: "commande", id: "layer.layerMask.enabled", etat: "bientot" }] }],
  { id: 3, hasMask: true }, undefined, tr("fr"))[0].entrees[0].etat === "bientot");
check("5.7 l'arbre reçu n'est pas modifié", (() => { const m = menuMasque(); decorerMasque(m, null, undefined, tr("fr")); return m[0].entrees[0].entrees[0].etat === "actif"; })());

// ── Lot B : dialogues complétés ──
const { choixCouches, choixDuplication, choixMotifs } = await import("../js/mod-documents.js");
const { editeurContenu } = await import("../js/mod-calques.js");
const { corpsBibliotheque, FORMATS_BIBLIO } = await import("../js/mod-fichier.js");
const { IDS_DIALOGUES_ECRAN } = await import("../js/mod-menus.js");
const T = (c, v) => (v && v.nom ? c + ":" + v.nom : c);

// 6. Sélection › Charger la sélection… : la couche (transparence, masque du calque actif, couches alpha par index)
const docC = { activeLayer: 3, layers: [{ id: 3, name: "Calque", hasMask: true, hasVectorMask: false }],
  channels: { alpha: [{ index: 0, name: "Alpha A" }, { index: 1, name: "Détourage" }] } };
const cc = choixCouches(docC, T);
check("6.1 une seule liste, clé channel, défaut transparence", cc.length === 1 && cc[0].cle === "channel" && cc[0].defaut === "transparency");
check("6.2 transparence, masque, couches alpha (index du moteur, nom brut)", JSON.stringify(cc[0].valeurs) === JSON.stringify([
  { valeur: "transparency", libelle: "photolab.valeur.transparency" }, { valeur: "mask", libelle: "photolab.valeur.layermask" },
  { valeur: 0, libelle: "Alpha A" }, { valeur: 1, libelle: "Détourage" }]), JSON.stringify(cc[0].valeurs));
const sansMasque = choixCouches({ activeLayer: 3, layers: [{ id: 3, hasMask: false, hasVectorMask: true }], channels: { alpha: [] } }, T)[0].valeurs.map((v) => v.valeur);
check("6.3 sans masque de fusion : pas de « masque » ; masque vectoriel proposé", JSON.stringify(sansMasque) === JSON.stringify(["transparency", "vectorMask"]));
check("6.4 sans document : transparence seule", JSON.stringify(choixCouches(null, T)[0].valeurs.map((v) => v.valeur)) === JSON.stringify(["transparency"]));

// 7. Calque › Dupliquer le calque… : ce document (rien envoyé), nouveau document, autres documents ouverts
const session = { active: 0, documents: [{ index: 0, name: "photo.png" }, { index: 1, name: "fond" }] };
const cd = choixDuplication(session, T);
check("7.1 clé document ; ce document en tête (valeur vide = rien envoyé)", cd.length === 1 && cd[0].cle === "document" && cd[0].valeurs[0].valeur === ""
  && cd[0].valeurs[0].libelle === "photolab.choix.ce_document:photo");
check("7.2 puis nouveau document, puis les autres", JSON.stringify(cd[0].valeurs.slice(1)) === JSON.stringify([{ valeur: "new", libelle: "photolab.nouveau.titre" }, { valeur: 1, libelle: "fond" }]));

// 8. Calque › Nouveau calque de remplissage › Motif… : le motif de la bibliothèque (pattern.list)
const cm = choixMotifs([{ id: "a1", name: "Damier" }, { id: "b2", name: "Rayures" }, { id: "", name: "sans id" }], T);
check("8.1 clé pattern, ids du moteur, noms bruts, premier par défaut", cm.length === 1 && cm[0].cle === "pattern" && cm[0].defaut === "a1"
  && JSON.stringify(cm[0].valeurs) === JSON.stringify([{ valeur: "a1", libelle: "Damier" }, { valeur: "b2", libelle: "Rayures" }]));
check("8.2 aucun motif : null (l'écran le dit)", choixMotifs([], T) === null && choixMotifs(null, T) === null);

// 9. Calque › Options de contenu du calque… : l'éditeur que le moteur désigne
check("9.1 calque de réglage -> Propriétés", editeurContenu({ editor: "adjustment:levels", layer: 4 }) === "proprietes");
check("9.2 remplissage -> pas d'éditeur", editeurContenu({ editor: "fill", layer: 3 }) === "remplissage");
check("9.3 réponse inconnue -> rien", editeurContenu({}) === null && editeurContenu(null) === null);
check("9.4 Dupliquer, Options de contenu, Enregistrer sous : de l'écran, document requis", IDS_DIALOGUES_ECRAN.length === 2
  && [...IDS_DIALOGUES_ECRAN, "file.saveAs"].every((id) => TRAITES_PAR_ECRAN.has(id) && NECESSITE_DOC.has(id)));

// 10. Fichier › Enregistrer sous… : un NOUVEAU fichier dans la Bibliothèque, sous le nom saisi
check("10.1 PNG ou JPG (formats de la route /bibliotheque)", JSON.stringify(FORMATS_BIBLIO.map((f) => f.id)) === JSON.stringify(["png", "jpg"]));
check("10.2 corps PNG", JSON.stringify(corpsBibliotheque("png", " Affiche ", 90)) === JSON.stringify({ format: "png", nom: "Affiche" }));
check("10.3 corps JPG : qualité bornée 1..100", JSON.stringify(corpsBibliotheque("jpg", "a", 250)) === JSON.stringify({ format: "jpg", nom: "a", quality: 100 })
  && corpsBibliotheque("jpg", "a", "abc").quality === 90);
const refus = (f) => { try { f(); return null; } catch (e) { return e.cle; } };
check("10.4 nom vide ou format hors liste : refusés", refus(() => corpsBibliotheque("png", "  ", 90)) === "photolab.enregistrer_sous.erreur.nom"
  && refus(() => corpsBibliotheque("webp", "a", 90)) === "photolab.export.erreur.format");

// ── Lot C : dialogues sur mesure ──
const { remplacementsPolices, fauteSuivante, cleFaute, paramsCorrection, IDS_VERIF_TEXTE } = await import("../js/mod-verifier-texte.js");
const { emplacementsVisibles, outilParLettre, EMPLACEMENTS } = await import("../js/mod-outils.js");
const { etatDefaut, normaliser } = await import("../js/mod-preferences.js");

// 11. Texte › Résoudre les polices manquantes… : une police installée par famille manquante -> {map}
check("11.1 seules les familles remplacées partent", JSON.stringify(remplacementsPolices(["Vieille", "Autre"], { Vieille: "Inter", Autre: "" }))
  === JSON.stringify({ map: { Vieille: "Inter" } }));
check("11.2 rien de choisi : null (rien n'est envoyé)", remplacementsPolices(["Vieille"], {}) === null && remplacementsPolices([], { a: "b" }) === null);
check("11.3 une famille hors liste est ignorée", JSON.stringify(remplacementsPolices(["A"], { A: "Inter", B: "Arial" })) === JSON.stringify({ map: { A: "Inter" } }));

// 12. Édition › Vérifier l'orthographe… : une faute à la fois, Ignorer saute cette occurrence, Changer la remplace
const fautes = [{ layer: 4, start: 0, end: 6, word: "Bonjur", suggestions: ["Bonjour"] }, { layer: 4, start: 10, end: 16, word: "mondee", suggestions: [] }];
check("12.1 la première faute non sautée", fauteSuivante(fautes, new Set()).word === "Bonjur" && fauteSuivante(fautes, new Set([cleFaute(fautes[0])])).word === "mondee");
check("12.2 plus rien : null", fauteSuivante(fautes, new Set(fautes.map(cleFaute))) === null && fauteSuivante(null, new Set()) === null);
check("12.3 Changer : calque, bornes, mot vérifié, remplacement", JSON.stringify(paramsCorrection(fautes[0], "change", "Bonjour"))
  === JSON.stringify({ action: "change", layer: 4, start: 0, end: 6, word: "Bonjur", replace: "Bonjour" }));
check("12.4 Tout changer / Ajouter au dictionnaire", JSON.stringify(paramsCorrection(fautes[1], "changeAll", "monde")) === JSON.stringify({ action: "changeAll", word: "mondee", replace: "monde" })
  && JSON.stringify(paramsCorrection(fautes[1], "addToDictionary")) === JSON.stringify({ action: "addToDictionary", word: "mondee" }));
check("12.5 remplacement vide : refusé (null)", paramsCorrection(fautes[0], "change", "  ") === null);
check("12.6 polices et orthographe : de l'écran, document requis", IDS_VERIF_TEXTE.length === 2 && IDS_VERIF_TEXTE.every((id) => TRAITES_PAR_ECRAN.has(id) && NECESSITE_DOC.has(id)));

// 13. Édition › Barre d'outils… : outils masqués gardés dans les préférences de l'écran (le moteur n'est pas appelé)
check("13.1 servie par l'écran, sans document", TRAITES_PAR_ECRAN.has("edit.toolbar") && !NECESSITE_DOC.has("edit.toolbar"));
const vis = emplacementsVisibles(["ellipseMarquee", "zoom"]);
check("13.2 un outil masqué sort de son emplacement ; un emplacement vide disparaît", vis.length === EMPLACEMENTS.length
  && !vis[1].some((o) => o.id === "ellipseMarquee") && vis[1].length === EMPLACEMENTS[1].length - 1 && vis[EMPLACEMENTS.length - 1].length === 0);
check("13.3 sans masque : tout", emplacementsVisibles([]).every((e, i) => e.length === EMPLACEMENTS[i].length) && emplacementsVisibles(undefined).length === EMPLACEMENTS.length);
check("13.4 la lettre saute un outil masqué", outilParLettre("M", "rectMarquee", false, false, null, ["ellipseMarquee"]) === "rowMarquee"
  && outilParLettre("Z", null, false, false, null, ["zoom"]) === null);
check("13.5 préférences : outils.masques par défaut vide, ids inconnus écartés", JSON.stringify(etatDefaut().outils) === JSON.stringify({ masques: [] })
  && JSON.stringify(normaliser({ outils: { masques: ["zoom", "inconnu", 3, "zoom"] } }).outils) === JSON.stringify({ masques: ["zoom"] }));

console.log(`defauts-menus : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
