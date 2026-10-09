// qa/preferences.test.mjs — t159 (parité L9) : Préférences, Raccourcis clavier, Menus, Préréglages, Touches de
// modification. Fonctions PURES (mod-preferences, mod-clavier, mod-modificateurs, mod-gestionnaire) et leurs crochets
// dans les modules qui servent (vue, outils, documents, espaces, texte, menus).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { SCHEMA, SECTIONS, IDS_PREFERENCES, SI, etatDefaut, valeurAdmise, normaliser, damier, fondToile, pxParUnite, pasGrillePrefs,
  tirets, bornerVue, centrerSur, curseurPeinture, curseurAutre, extension, reprendre, clesTextes, clePref, APERCU_ID } from "../js/mod-preferences.js";
import { comboAffiche, appliquerRaccourcis, appliquerMenus, listeCommandes, effectif, conflit, assigner, lettreOutil, lettreAdmise,
  resume, ID_TOUT_MONTRER, NON_MASQUABLES, COULEURS_MENU, TOUCHES_NOMMEES } from "../js/mod-clavier.js";
import { suivant, actives, TOUCHES } from "../js/mod-modificateurs.js";
import { deplacement, lireFichier, nomFichier, cleGenre, GENRES } from "../js/mod-gestionnaire.js";
import { exportRapidePrefs, nomTelecharge } from "../js/mod-documents.js";
import { construireMenus, REFUSES, PERMIS, TRAITES_PAR_ECRAN, IDS_PREFERENCES_ECRAN, entreesVisibles, rechercherEntree, actionEntree } from "../js/mod-menus.js";
import { outilParLettre, infobulle, outilDe, lettreDe } from "../js/mod-outils.js";
import { gesteMolette } from "../js/mod-vue.js";
import { memoriser, etatDefaut as espacesDefaut } from "../js/mod-espaces.js";
import { APERCU_PREF, APERCUS } from "../js/mod-texte.js";
import { indexRaccourcis, normaliser as normCombo } from "../js/mod-raccourcis.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const dico = {
  ...JSON.parse(readFileSync(join(racine, "../shared/i18n/commun.json"), "utf8")),
  ...JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8")),
};
const present = (k) => !!(dico[k] && dico[k].fr && dico[k].en);
const manque = (cles) => cles.filter((k) => !present(k));
const T = (k, v) => (dico[k] ? dico[k].fr.replace(/\{(\w+)\}/g, (m, n) => (v && v[n] != null ? v[n] : m)) : k);

// 1. schéma et état
const d = etatDefaut();
check("1.1 18 sections dans l'ordre du menu ; 11 réglables", SECTIONS.length === 18 && Object.keys(SCHEMA).length === 11
  && SECTIONS.filter(([, s]) => SCHEMA[s]).length === 11 && IDS_PREFERENCES[0] === "edit.preferences.general");
check("1.2 défauts gardant l'aspect d'avant t159 : damier du thème, filet autour du document, fond du thème",
  d.prefs.transparencyAndGamut.gridColors === "theme" && d.prefs.interface.canvasBorder === "line" && d.prefs.interface.canvasColor === "default");
check("1.3 valeurAdmise : types et bornes", valeurAdmise(["bool", false], true) && !valeurAdmise(["bool", false], 1)
  && valeurAdmise(["int", 4, [1, 100]], 100) && !valeurAdmise(["int", 4, [1, 100]], 4.5) && !valeurAdmise(["int", 4, [1, 100]], 0)
  && valeurAdmise(["num", 1, [0.001, 10000]], 0.5) && !valeurAdmise(["num", 1, [0.001, 10000]], NaN)
  && valeurAdmise(["couleur", "#000000"], "#a0b1c2") && !valeurAdmise(["couleur", "#000000"], "#A0B1C2x") && !valeurAdmise(["enum", "a", ["a"]], "b"));
const n = normaliser({ prefs: { tools: { overscroll: false, inconnu: 1 }, export: { jpegQuality: 500 }, interface: { canvasCustomColor: "#ABCDEF" } },
  raccourcis: { commandes: { "edit.fill": "shift+f5" } }, menus: { masques: ["a.b", 3] }, texte: { langue: "zz" } });
check("1.4 normaliser : valeur refusée -> défaut, couleur en minuscules, morceaux gardés", n.prefs.tools.overscroll === false
  && n.prefs.export.jpegQuality === 85 && n.prefs.interface.canvasCustomColor === "#abcdef" && n.raccourcis.commandes["edit.fill"] === "shift+f5"
  && JSON.stringify(n.menus.masques) === '["a.b"]' && n.texte.langue === d.texte.langue);
check("1.5 normaliser(null) = défaut", JSON.stringify(normaliser(null)) === JSON.stringify(d));
check("1.6 champs conditionnels : chaque clé et sa clé de décision existent", Object.entries(SI).every(([k, [c]]) => {
  const [s1, k1] = k.split("."), [s2, k2] = c.split("."); return SCHEMA[s1] && SCHEMA[s1][k1] && SCHEMA[s2] && SCHEMA[s2][k2];
}));

// 2. ce que les modules lisent
const P = (modif) => { const e = etatDefaut().prefs; for (const [s, kv] of Object.entries(modif)) Object.assign(e[s], kv); return e; };
check("2.1 damier : thème = couleurs nulles, 8 px ; aucune = 0 ; personnalisé", JSON.stringify(damier(P({}))) === '{"taille":8,"c1":null,"c2":null}'
  && damier(P({ transparencyAndGamut: { gridSize: "none" } })).taille === 0
  && damier(P({ transparencyAndGamut: { gridSize: "large", gridColors: "light" } })).c2 === "#cccccc"
  && damier(P({ transparencyAndGamut: { gridColors: "custom", customLight: "#111111", customDark: "#222222" } })).c1 === "#111111");
check("2.2 fond : défaut = thème (null), noir, personnalisé", fondToile(P({})) === null && fondToile(P({ interface: { canvasColor: "black" } })) === "#000000"
  && fondToile(P({ interface: { canvasColor: "custom", canvasCustomColor: "#123456" } })) === "#123456");
check("2.3 unités : pouce = ppi, cm, mm, points, picas, pourcentage de la largeur", pxParUnite("inches", 300, 0) === 300
  && Math.abs(pxParUnite("cm", 254, 0) - 100) < 1e-9 && Math.abs(pxParUnite("mm", 254, 0) - 10) < 1e-9 && pxParUnite("points", 72, 0) === 1
  && pxParUnite("picas", 72, 0) === 12 && pxParUnite("percent", 72, 800) === 8 && pxParUnite("pixels", 300, 0) === 1 && pxParUnite("inches", 0, 0) === 72);
const pg = pasGrillePrefs(P({ guidesGridAndSlices: { gridlineEvery: 2, gridUnit: "cm", subdivisions: 5 } }), 254, 1000);
check("2.4 grille : une ligne tous les 2 cm à 254 ppi = 200 px, 5 subdivisions = 40 px", Math.abs(pg.majeur - 200) < 1e-9 && Math.abs(pg.mineur - 40) < 1e-9);
check("2.5 défaut de la grille = un pouce en 4 (comme avant t159)", JSON.stringify(pasGrillePrefs(etatDefaut().prefs, 72, 100)) === '{"majeur":72,"mineur":18}');
check("2.6 tirets", tirets("lines") === "" && tirets("dashedLines") === "6 4" && tirets("dots") === "1 3");
const bv = bornerVue({ z: 1, ox: 500, oy: -900 }, { w: 400, h: 300 }, { w: 800, h: 600 });
const bv2 = bornerVue({ z: 4, ox: 100, oy: -5000 }, { w: 400, h: 300 }, { w: 800, h: 600 });
check("2.7 sans défilement au-delà : centré s'il tient, bords collés sinon", bv.ox === 200 && bv.oy === 150 && bv2.ox === 0 && bv2.oy === 600 - 1200);
const cz = centrerSur({ z: 2, ox: 10, oy: 20 }, 100, 50, { w: 800, h: 600 });
check("2.8 zoom au centre : le point cliqué va au centre de la vue", cz.ox === 10 + 300 && cz.oy === 20 + 250 && cz.z === 2);
check("2.9 curseurs de peinture", curseurPeinture(P({ cursors: { painting: "standard" } })).cercle === 0
  && curseurPeinture(P({ cursors: { painting: "precise" } })).css === "crosshair"
  && curseurPeinture(P({}), 1).cercle === 1 && curseurPeinture(P({}), 0).cercle === 0.5 && curseurPeinture(P({ cursors: { painting: "fullSizeTip" } }), 0).cercle === 1
  && curseurPeinture(P({ cursors: { showCrosshairInBrushTip: true } })).reticule === true
  && curseurPeinture(P({ cursors: { showOnlyCrosshairWhilePainting: true } }), 1, true).cercle === 0 && curseurPeinture(P({}), 1).css === "none");
check("2.10 autres curseurs : précis remplace flèche et loupe, garde les curseurs propres", curseurAutre(P({ cursors: { other: "precise" } }), "default") === "crosshair"
  && curseurAutre(P({ cursors: { other: "precise" } }), "grab") === "grab" && curseurAutre(P({}), "default") === "default");
check("2.11 extension", extension(P({}), "PNG") === "png" && extension(P({ fileHandling: { lowercaseExtension: false } }), "png") === "PNG");
const rp = reprendre(etatDefaut(), { grille: true }, { apercu: "type.fontPreviewSize.huge", langue: "type.languageOptions.eastAsianFeatures", composeur: true });
check("2.12 reprise du navigateur : options d'Affichage, aperçu, langue, composeur", rp.affichage.grille === true && rp.prefs.type.fontPreview === "huge"
  && rp.texte.langue === "type.languageOptions.eastAsianFeatures" && rp.texte.composeur === true && reprendre(etatDefaut(), null, null).affichage === null);
check("2.13 aperçus : mod-texte et mod-preferences d'accord (5 tailles)", JSON.stringify(APERCU_PREF) === JSON.stringify(APERCU_ID)
  && Object.values(APERCU_PREF).every((id) => APERCUS[id] != null) && JSON.stringify(Object.keys(APERCU_ID)) === JSON.stringify(SCHEMA.type.fontPreview[2]));

// 3. textes
check("3.1 chaque clé composée par le dialogue existe en fr et en en", !manque(clesTextes()).length, manque(clesTextes()));
check("3.2 clés en minuscules (test_i18n_l0)", clesTextes().every((k) => /^[a-z0-9]+(\.[a-z0-9_]+){2,}$/.test(k)) && clePref("guidesGridAndSlices", "gridUnit", "cm") === "photolab.pref.guides_grid_and_slices.grid_unit.cm");
const autres = [...COULEURS_MENU.map((c) => "photolab.menus.couleur." + c), "photolab.menus.couleur.aucune", ...TOUCHES_NOMMEES.map((t) => "photolab.touche." + t),
  ...TOUCHES.map((t) => "photolab.modificateurs." + t), ...GENRES.map(cleGenre)];
check("3.3 couleurs de menu, touches nommées, modificateurs, genres de préréglage", !manque(autres).length, manque(autres));
const src = (f) => readFileSync(join(racine, "js", f), "utf8");
const litt = ["mod-preferences.js", "mod-clavier.js", "mod-modificateurs.js", "mod-gestionnaire.js"].flatMap((f) => [...src(f).matchAll(/T\("(photolab\.[a-z0-9_.]+|commun\.[a-z0-9_.]+)"/g)].map((m) => m[1])).filter((k) => !k.endsWith("."));
check("3.4 chaque clé écrite en toutes lettres dans les 4 modules existe", litt.length > 40 && !manque(litt).length, manque(litt));

// 4. raccourcis clavier
const menus = [{ nom_affiche: "Édition", entrees: [
  { type: "commande", id: "edit.fill", libelle: "Remplir…", raccourci: "Shift+F5", etat: "actif" },
  { type: "commande", id: "edit.clear", libelle: "Effacer", raccourci: "", etat: "actif" },
  { type: "separateur" },
  { type: "sous-menu", nom_affiche: "Préférences", entrees: [{ type: "commande", id: "edit.preferences.general", libelle: "Paramètres…", raccourci: "Cmd+K", etat: "actif" }] },
  { type: "commande", id: "edit.undo", libelle: "Annuler", raccourci: "Cmd+Z", etat: "actif" },
] }, { nom_affiche: "Image", entrees: [{ type: "commande", id: "image.adjustments.levels", libelle: "Niveaux…", raccourci: "Cmd+L", etat: "actif" }] }];
check("4.1 comboAffiche : fr Maj, en Shift, touches nommées traduites", comboAffiche("ctrl+alt+shift+f5", "fr") === "Ctrl+Alt+Maj+F5"
  && comboAffiche("ctrl+shift+k", "en") === "Ctrl+Shift+K" && comboAffiche("ctrl+delete", "fr", T) === "Ctrl+Suppr" && comboAffiche("", "fr") === "");
const ar = appliquerRaccourcis(menus, { "edit.clear": "ctrl+k", "image.adjustments.levels": "" }, "fr");
check("4.2 surcharge : Effacer prend Ctrl+K, Paramètres le perd, Niveaux retiré, défaut gardé",
  rechercherEntree(ar, "edit.clear").raccourci === "Ctrl+K" && rechercherEntree(ar, "edit.preferences.general").raccourci === ""
  && rechercherEntree(ar, "image.adjustments.levels").raccourci === "" && rechercherEntree(ar, "image.adjustments.levels").raccourciDefaut === "Cmd+L"
  && rechercherEntree(ar, "edit.fill").raccourci === "Shift+F5");
const idx = indexRaccourcis(ar);
check("4.3 mod-raccourcis indexe les raccourcis appliqués (Ctrl+K -> Effacer, Ctrl+L libre)", idx.get("ctrl+k") && idx.get("ctrl+k").id === "edit.clear" && !idx.has("ctrl+l"));
const liste = listeCommandes(ar);
check("4.4 listeCommandes : à plat, chemin, défauts normalisés", liste.length === 5 && liste.find((c) => c.id === "edit.preferences.general").chemin.join("/") === "Édition/Préférences"
  && liste.find((c) => c.id === "edit.fill").defaut === "shift+f5");
check("4.5 conflit : forme (lettre seule, Maj+lettre), réservé (Ctrl+Z), conflit nommé",
  conflit(liste, {}, "edit.clear", "k").raison === "forme" && conflit(liste, {}, "edit.clear", "shift+k").raison === "forme"
  && conflit(liste, {}, "edit.clear", "ctrl+z").raison === "reserve" && conflit(liste, {}, "edit.clear", "ctrl+l").id === "image.adjustments.levels"
  && conflit(liste, {}, "edit.clear", "ctrl+alt+j") === null && conflit(liste, {}, "edit.clear", "f9") === null);
const as = assigner(liste, {}, "edit.clear", "ctrl+l");
check("4.6 assigner : la commande prend, l'autre perd ; revenir au défaut efface la surcharge", as["edit.clear"] === "ctrl+l" && as["image.adjustments.levels"] === ""
  && effectif(liste, as).get("image.adjustments.levels") === "" && !("edit.fill" in assigner(liste, { "edit.fill": "f7" }, "edit.fill", "shift+f5"))
  && JSON.stringify(assigner(liste, {}, "edit.clear", "ctrl+z")) === "{}");
const am = appliquerMenus(menus, { masques: ["edit.clear", "edit.menus"], couleurs: { "edit.fill": "red", "edit.undo": "pink" } }, {}, T);
check("4.7 menus : masqué marqué, couleur admise seulement, « Afficher tous les éléments » ajouté au menu concerné",
  rechercherEntree(am, "edit.clear").masque === true && rechercherEntree(am, "edit.fill").couleur === "red" && !rechercherEntree(am, "edit.undo").couleur
  && am[0].entrees[am[0].entrees.length - 1].id === ID_TOUT_MONTRER && am[1].entrees.every((e) => e.id !== ID_TOUT_MONTRER));
check("4.8 menus : couleurs coupées par la préférence, tout montrer", !rechercherEntree(appliquerMenus(menus, { couleurs: { "edit.fill": "red" } }, { montrerCouleurs: false }), "edit.fill").couleur
  && !rechercherEntree(appliquerMenus(menus, { masques: ["edit.clear"] }, { montrerTout: true }), "edit.clear").masque);
check("4.9 Préférences et Menus… ne se masquent pas", NON_MASQUABLES.includes("edit.menus") && !rechercherEntree(appliquerMenus(menus, { masques: ["edit.preferences.general"] }), "edit.preferences.general").masque);
const ev = entreesVisibles([{ type: "separateur" }, { type: "commande", id: "a", masque: true }, { type: "commande", id: "b" }, { type: "separateur" }, { type: "separateur" },
  { type: "sous-menu", entrees: [{ type: "commande", id: "c", masque: true }] }, { type: "commande", id: "d" }, { type: "separateur" }]);
check("4.10 entreesVisibles : masquées sautées, sous-menu vide retiré, séparateurs ni en tête, ni doublés, ni en queue",
  JSON.stringify(ev.map((e) => e.id || e.type)) === '["b","separateur","d"]');
check("4.11 lettres d'outils : surcharge, défaut, réservées X et D", lettreOutil("brush", {}) === "b" && lettreOutil("brush", { brush: "k" }) === "k" && lettreOutil("blur", {}) === ""
  && lettreAdmise("k") && lettreAdmise("") && !lettreAdmise("x") && !lettreAdmise("d") && !lettreAdmise("1"));
check("4.12 mod-outils suit les surcharges (K -> Pinceau, B ne mène plus au Pinceau)", outilParLettre("K", "move", false, false, { brush: "k" }) === "brush"
  && outilParLettre("B", "move", false, false, { brush: "k" }) === "pencil" && outilParLettre("B", "move", false) === "brush"
  && infobulle(outilDe("brush"), (c) => c, { brush: "k" }).endsWith("(K)") && lettreDe(outilDe("brush"), {}) === "B");
const html = resume(liste, { "edit.clear": "ctrl+k" }, {}, "fr", T);
check("4.13 résumé : HTML autonome, échappé, commandes et outils", html.startsWith("<!doctype html>") && html.includes("Ctrl+K") && html.includes("Effacer")
  && !resume([{ id: "x.y", chemin: ["<b>"], libelle: "a&b", defaut: "ctrl+j" }], {}, {}, "fr", T).includes("<b>"));

// 5. touches de modification, préréglages
check("5.1 touches : clic arme, reclic relâche, double clic tient, consommé seulement « une »", suivant("", "clic") === "une" && suivant("une", "clic") === ""
  && suivant("", "double") === "tenue" && suivant("tenue", "clic") === "" && suivant("une", "consomme") === "" && suivant("tenue", "consomme") === "tenue"
  && JSON.stringify(actives({ shift: "une", ctrl: "", alt: "tenue" })) === '["shift","alt"]');
check("5.2 déplacement d'un cran borné", JSON.stringify(deplacement(2, -1, 5)) === '{"index":2,"to":1}' && deplacement(0, -1, 5) === null && deplacement(4, 1, 5) === null);
check("5.3 fichier importé : JSON, format, taille", lireFichier("{").erreur === "photolab.gestionnaire.illisible" && lireFichier('{"format":"abr"}').erreur === "photolab.gestionnaire.pas_presets"
  && lireFichier("x".repeat(2_000_001)).erreur === "photolab.gestionnaire.trop_gros" && lireFichier('{"format":"photocraft-presets","version":1}').donnees.version === 1);
check("5.4 nom du fichier exporté daté", nomFichier(new Date("2026-10-09T12:00:00Z")) === "preregles-photolab-2026-10-09.json");

// 6. crochets dans les autres modules
const pr = (e) => ({ export: { quickExportFormat: "png", jpegQuality: 85, quickExportLocation: "download", ...e } });
check("6.1 exportation rapide : téléchargement PNG par défaut, JPG avec qualité, Bibliothèque, WEBP -> téléchargement, demander -> dialogue",
  JSON.stringify(exportRapidePrefs(pr({}))) === '{"route":"/enregistrer","corps":{"format":"png"}}'
  && JSON.stringify(exportRapidePrefs(pr({ quickExportFormat: "jpg", jpegQuality: 70 })).corps) === '{"format":"jpg","quality":70}'
  && exportRapidePrefs(pr({ quickExportLocation: "library" })).corps.destination === "bibliotheque"
  && exportRapidePrefs(pr({ quickExportLocation: "library", quickExportFormat: "webp" })).route === "/enregistrer"
  && exportRapidePrefs(pr({ quickExportLocation: "ask" })).dialogue === true && exportRapidePrefs(null).route === "/enregistrer");
check("6.2 nom téléchargé : extension en majuscules sur demande", nomTelecharge("a.b.png", false) === "a.b.PNG" && nomTelecharge("x.png") === "x.png");
check("6.3 molette : zoom sans Ctrl avec la préférence, Maj garde le panoramique", gesteMolette({ deltaY: 100 }).type === "pan"
  && gesteMolette({ deltaY: 100 }, true).type === "zoom" && gesteMolette({ deltaY: 100, shiftKey: true }, true).type === "pan");
const es = { ...espacesDefaut(), actif: "photo" };
check("6.4 espaces : « mémoriser » décochée = rien n'est gardé", Object.keys(memoriser(es, { x: 1 }, false).modifs).length === 0 && memoriser(es, { x: 1 }).modifs.photo.x === 1);

// 7. menus générés : les 23 entrées de l'écran actives, Migrer reste « bientôt »
const catalogue = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));
const reg = ["edit.presets.presetManager", "edit.presets.exportImportPresets", "edit.presets.migratePresets", "edit.undo"].map((id) => ({ id, label: id, params: "{}", enabled: true, champs: [] }));
const arbre = construireMenus(catalogue, reg, REFUSES, "fr", (k) => k);
check("7.1 IDS_PREFERENCES_ECRAN : 18 sections + Raccourcis + Menus + Touches + 2 préréglages, toutes traitées par l'écran",
  IDS_PREFERENCES_ECRAN.length === 23 && IDS_PREFERENCES_ECRAN.every((id) => TRAITES_PAR_ECRAN.has(id))
  && JSON.stringify(IDS_PREFERENCES_ECRAN.slice(0, 18)) === JSON.stringify(IDS_PREFERENCES));
check("7.2 toutes présentes dans le catalogue et actives", IDS_PREFERENCES_ECRAN.every((id) => rechercherEntree(arbre, id) && rechercherEntree(arbre, id).etat === "actif"),
  IDS_PREFERENCES_ECRAN.filter((id) => !rechercherEntree(arbre, id) || rechercherEntree(arbre, id).etat !== "actif"));
check("7.3 elles s'ouvrent par l'écran, jamais par le moteur", IDS_PREFERENCES_ECRAN.every((id) => actionEntree(rechercherEntree(arbre, id)) === "ecran"));
check("7.4 Migrer les préréglages (chemin) reste « bientôt » ; PERMIS a les deux commandes rouvertes",
  rechercherEntree(arbre, "edit.presets.migratePresets").etat === "bientot" && PERMIS.includes("edit.presets.presetManager") && PERMIS.includes("edit.presets.exportImportPresets")
  && !PERMIS.includes("edit.presets.migratePresets"));
check("7.5 normaliser des raccourcis : la forme d'affichage relue donne la combinaison", normCombo(comboAffiche("ctrl+alt+shift+f5", "fr")) === "ctrl+alt+shift+f5"
  && normCombo(comboAffiche("ctrl+shift+k", "en")) === "ctrl+shift+k");

console.log(`preferences : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
