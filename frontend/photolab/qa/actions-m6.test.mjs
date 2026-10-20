// qa/actions-m6.test.mjs — t255 (Photolab M6) : le panneau Actions, fonctions PURES de mod-actions.js (arbre du panneau,
// libellés et détails des étapes, plan de lecture pas à pas, noms, .atn en base64, commandes insérables, menu du
// panneau, Traitement par lots) ; copies des listes du pont (conditions, couleurs, bornes) relues dans le source
// Python ; branchement de l'écran (onglet, rail, Fenêtre › Actions, groupe Calques, TRAITES_PAR_ECRAN) et textes.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  COULEURS, CONDITIONS, MAX_NOM, MAX_MESSAGE, MAX_OCTETS_ATN, cleCouleur, cleCondition, arbreActions, actionsDe, jeuxDe,
  libelleEtape, indexCatalogue, detailsEtape, planLecture, paramsSegment, nomCopie, nomNouvelle, nomFichierAtn, versBase64,
  depuisBase64, controleAtn, messageValide, rangInsertion, deplacement, commandesInserables, filtrerCommandes, entreesMenu,
  paramsLot, corpsLot,
} from "../js/mod-actions.js";
import { TRAITES_PAR_ECRAN } from "../js/mod-menus.js";
import { GROUPES, PANNEAUX } from "../js/mod-espaces.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const ici = dirname(fileURLToPath(import.meta.url));
const racine = join(ici, "..");
const depot = join(racine, "..", "..");
const lire = (...p) => readFileSync(join(...p), "utf8");
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// 1. arbre du panneau
const R = { recording: "B", actions: [
  { name: "A", set: null, color: "red", steps: [["image.adjustments.invert", {}], ["select.all", {}]], disabled: [1], dialogs: [] },
  { name: "B", set: "Jeu 1", color: "", steps: [["filter.blur.gaussianBlur", { radius: 2 }]], disabled: [], dialogs: [0] },
  { name: "C", set: null, color: "", steps: [], disabled: [], dialogs: [] },
  { name: "D", set: "Jeu 1", color: "blue", steps: [["select.all", {}], ["select.all", {}]], disabled: [0, 1], dialogs: [1] },
] };
const ar = arbreActions(R, ["Vide", "Jeu 1"]);
check("1.1 ordre du moteur : A, jeu « Jeu 1 » (à la place de B), C, puis les jeux vides de l'écran", eq(ar.map((n) => n.type + ":" + n.nom), ["action:A", "jeu:Jeu 1", "action:C", "jeu:Vide"]), ar.map((n) => n.nom));
check("1.2 le jeu regroupe ses actions dans l'ordre (B, D) ; un jeu vide déjà porté n'est pas doublé", eq(ar[1].actions.map((a) => a.nom), ["B", "D"]) && ar[3].vide === true && ar.length === 4);
const parNom = Object.fromEntries(actionsDe(ar).map((a) => [a.nom, a]));
check("1.3 allumage : partiel (A), plein (B), plein sans étape (C), vide (D)", eq(["A", "B", "C", "D"].map((n) => parNom[n].allumage), ["partiel", "plein", "plein", "vide"]));
check("1.4 dialogues : vide (A), plein (B), vide (C), partiel (D)", eq(["A", "B", "C", "D"].map((n) => parNom[n].dialogues), ["vide", "plein", "vide", "partiel"]));
check("1.5 étapes : index, allumée, dialogue ; enregistre = l'action en cours", ar[0].etapes[1].allumee === false && ar[1].actions[0].etapes[0].dialogue === true
  && ar[1].actions[0].enregistre && !ar[0].enregistre, ar[0].etapes);
check("1.6 actionsDe suit l'arbre (A, B, D, C) et garde le rang du moteur ; jeuxDe", eq(actionsDe(ar).map((a) => a.nom + a.index), ["A0", "B1", "D3", "C2"]) && eq(jeuxDe(ar), ["Jeu 1", "Vide"]));
check("1.7 réponse vide ou absente -> arbre vide", eq(arbreActions(null), []) && eq(arbreActions({ actions: [] }), []));

// 2. libellés et détails
const cat = indexCatalogue({ entrees: [{ chemin: ["Filter", "Blur"], id: "filter.blur.gaussianBlur", libelle_fr: "Flou gaussien…", libelle_en: "Gaussian Blur…" }, { chemin: ["File"], separateur: true }] });
const t = (c, v) => c + (v ? JSON.stringify(v) : "");
check("2.1 commande du catalogue : libellé fr / en sans « … »", libelleEtape({ id: "filter.blur.gaussianBlur", params: {} }, cat, "fr").texte === "Flou gaussien"
  && libelleEtape({ id: "filter.blur.gaussianBlur", params: {} }, cat, "en").texte === "Gaussian Blur");
check("2.2 commande hors catalogue : l'id, brut", eq(libelleEtape({ id: "layer.select", params: {} }, cat, "fr"), { texte: "layer.select", brut: true }));
check("2.3 étapes des actions par le dictionnaire (jouer, arrêt, condition)",
  libelleEtape({ id: "actions.play", params: { action: "X" } }, cat, "fr", t) === undefined ? false
    : libelleEtape({ id: "actions.play", params: { action: "X" } }, cat, "fr", t).texte === 'photolab.actions.etape_jouer{"nom":"X"}'
    && libelleEtape({ id: "actions.stopMessage", params: {} }, cat, "fr", t).texte === "photolab.actions.etape_arret"
    && libelleEtape({ id: "actions.conditional", params: { if: "hasSelection" } }, cat, "fr", t).texte === 'photolab.actions.etape_condition{"si":"photolab.actions.condition.has_selection"}');
check("2.4 étape .atn sans équivalent : son nom, brut, marquée", eq(libelleEtape({ id: "actions.photoshopStep", params: { event: "Abcd", name: "Truc" } }, cat), { texte: "Truc", brut: true, sansEquivalent: true }));
check("2.5 détails : « clé : valeur », coalesce caché, objets en JSON, coupés à 80", eq(detailsEtape({ radius: 2, coalesce: "x", corners: [[1, 2]], else: null }), ["radius : 2", "corners : [[1,2]]"])
  && detailsEtape({ t: "x".repeat(200) })[0].length === 4 + 80 && detailsEtape({ t: "x".repeat(200) })[0].endsWith("…"));

// 3. plan de lecture pas à pas
const act = (etapes) => ({ etapes: etapes.map(([id, o = {}], index) => ({ index, id, params: o.params || {}, allumee: o.allumee !== false, dialogue: !!o.dialogue })) });
const dlg = (id) => id === "filter.blur.gaussianBlur";
const A0 = act([["image.adjustments.invert"], ["select.all"]]);
check("3.1 sans point : UN segment, une seule lecture du moteur", eq(planLecture(A0, 0, dlg), [{ type: "segment", from: 0, until: null }]));
const A1 = act([["image.adjustments.invert"], ["filter.blur.gaussianBlur", { dialogue: true, params: { radius: 3 } }], ["select.all"]]);
check("3.2 dialogue au milieu : segment [0,1), dialogue 1, segment depuis 2", eq(planLecture(A1, 0, dlg),
  [{ type: "segment", from: 0, until: 1 }, { type: "dialogue", step: 1 }, { type: "segment", from: 2, until: null }]));
check("3.3 dialogue allumé sur une commande sans formulaire : ignoré (le moteur la joue)", eq(planLecture(A1, 0, () => false), [{ type: "segment", from: 0, until: null }]));
const A2 = act([["actions.stopMessage", { params: { message: "Vérifie", allowContinue: true } }], ["select.all"], ["filter.blur.gaussianBlur", { dialogue: true }]]);
check("3.4 Arrêt en tête (message, continuer), dialogue en dernier : rien après", eq(planLecture(A2, 0, dlg),
  [{ type: "arret", step: 0, message: "Vérifie", continuer: true }, { type: "segment", from: 1, until: 2 }, { type: "dialogue", step: 2 }]));
const A3 = act([["actions.stopMessage", { allumee: false, params: { message: "x" } }], ["filter.blur.gaussianBlur", { dialogue: true, allumee: false }], ["select.all"]]);
check("3.5 points éteints : ignorés", eq(planLecture(A3, 0, dlg), [{ type: "segment", from: 0, until: null }]));
check("3.6 depuis une étape : les points d'avant ignorés", eq(planLecture(A1, 2, dlg), [{ type: "segment", from: 2, until: null }]));
check("3.7 action vide : un segment (le moteur dit ce qu'il fait)", eq(planLecture(act([]), 0, dlg), [{ type: "segment", from: 0, until: null }]));
check("3.8 paramsSegment : sans from à 0, avec until au milieu", eq(paramsSegment("A", { from: 0, until: null }), { action: "A" })
  && eq(paramsSegment("A", { from: 2, until: null }), { action: "A", from: 2 }) && eq(paramsSegment("A", { from: 0, until: 1 }), { action: "A", from: 0, until: 1 }));

// 4. noms, fichiers, base64
check("4.1 nomCopie : « X copie », puis « X copie 2 »", nomCopie("X", ["X"]) === "X copie" && nomCopie("X", ["X", "X copie"]) === "X copie 2"
  && nomCopie("y".repeat(200), []).length <= MAX_NOM);
check("4.2 nomNouvelle : le premier « Action N » libre", nomNouvelle(["Action 1", "Action 3"]) === "Action 2");
check("4.3 nomFichierAtn : sans accents ni séparateurs, .atn", nomFichierAtn("Mes réglages/été") === "Mes-reglages-ete.atn" && nomFichierAtn("") === "actions.atn");
const oct = new Uint8Array(70000).map((_, i) => (i * 37) % 256);
check("4.4 base64 aller-retour (plus de 32 Ko : par morceaux)", eq(Array.from(depuisBase64(versBase64(oct))), Array.from(oct)));
check("4.5 controleAtn : extension .atn, 1 octet .. 2 Mo", controleAtn("a.ATN", 10).ok && controleAtn("a.json", 10).erreur === "photolab.actions.atn_extension"
  && controleAtn("a.atn", 0).erreur === "photolab.actions.atn_taille" && controleAtn("a.atn", MAX_OCTETS_ATN + 1).erreur === "photolab.actions.atn_taille");
check("4.6 messageValide : texte propre ou null (vide, trop long, contrôle)", messageValide("  Vérifie\nle cadrage ") === "Vérifie\nle cadrage"
  && messageValide("  ") === null && messageValide("x".repeat(MAX_MESSAGE + 1)) === null && messageValide("a\u0007") === null);
const aI = { nom: "A", etapes: [{}, {}, {}] };
check("4.7 rangInsertion : après l'étape choisie, sinon en fin", rangInsertion({ action: "A", step: 0 }, aI) === 1 && rangInsertion({ action: "A" }, aI) === 3
  && rangInsertion({ action: "B", step: 0 }, aI) === 3 && rangInsertion(null, null) === null);
check("4.8 deplacement : bornes", deplacement(0, -1, 3) === null && deplacement(0, 1, 3) === 1 && deplacement(2, 1, 3) === null);

// 5. Insérer un élément de menu
const catalogue = { menus_fr: { Filter: "Filtre", Blur: "Flou", File: "Fichier", Image: "Image", Adjustments: "Réglages", Window: "Fenêtre" }, entrees: [
  { chemin: ["Filter", "Blur"], id: "filter.blur.gaussianBlur", libelle_fr: "Flou gaussien…", libelle_en: "Gaussian Blur…" },
  { chemin: ["Image", "Adjustments"], id: "image.adjustments.invert", libelle_fr: "Négatif", libelle_en: "Invert" },
  { chemin: ["File"], id: "file.saveAs", libelle_fr: "Enregistrer sous…", libelle_en: "Save As…" },
  { chemin: ["File"], id: "file.automate.fitImage", libelle_fr: "Adapter l’image…", libelle_en: "Fit Image…" },
  { chemin: ["Window"], id: "window.panel.actions", libelle_fr: "Actions", libelle_en: "Actions" },
  { chemin: ["Image"], id: "image.inconnue", libelle_fr: "Inconnue", libelle_en: "Unknown" },
  { chemin: ["File"], separateur: true },
] };
const reg = [{ id: "filter.blur.gaussianBlur" }, { id: "image.adjustments.invert" }, { id: "file.saveAs" }, { id: "file.automate.fitImage" }, { id: "window.panel.actions" }];
const ins = commandesInserables(catalogue, reg, "fr");
check("5.1 insérables : connues du moteur, hors familles refusées et hors écran, triées par chemin FR", eq(ins.map((x) => x.id), ["filter.blur.gaussianBlur", "image.adjustments.invert"])
  && ins[0].chemin === "Filtre › Flou › Flou gaussien" && commandesInserables(catalogue, reg, "en")[0].chemin === "Filter › Blur › Gaussian Blur", ins);
check("5.2 filtrer par texte ou id", eq(filtrerCommandes(ins, "négat").map((x) => x.id), ["image.adjustments.invert"]) && filtrerCommandes(ins, "GAUSSIAN").length === 1 && filtrerCommandes(ins, "").length === 2);

// 6. menu du panneau
const m0 = entreesMenu({ sel: null, action: null, n: 0, enregistre: false, modeBouton: true });
const act1 = { nom: "A" };
const actif = (m, id) => (m.find((x) => x && x.id === id) || {}).actif;
check("6.1 sans action : nouvelle / jeu / charger actifs ; jouer, dupliquer, sauver, lot, effacer inactifs ; mode Bouton coché",
  actif(m0, "nouvelle") && actif(m0, "jeu") && actif(m0, "charger") && !actif(m0, "jouer") && !actif(m0, "dupliquer") && !actif(m0, "sauver")
  && !actif(m0, "lot") && !actif(m0, "effacer") && m0[0].coche === true);
const m1 = entreesMenu({ sel: { action: "A" }, action: act1, n: 1, enregistre: false });
check("6.2 action choisie : jouer, options, insérer actifs ; Modifier l'étape inactif", actif(m1, "jouer") && actif(m1, "options") && actif(m1, "arret") && !actif(m1, "modifier"));
const m2 = entreesMenu({ sel: { action: "A", step: 0 }, action: act1, n: 1, enregistre: false });
check("6.3 étape choisie : Modifier l'étape actif, Options d'action inactif", actif(m2, "modifier") && !actif(m2, "options"));
const m3 = entreesMenu({ sel: { action: "A" }, action: act1, n: 1, enregistre: true });
check("6.4 pendant l'enregistrement : rien qui change la liste (jouer, nouvelle, charger, lot…), insérer reste possible",
  !actif(m3, "jouer") && !actif(m3, "nouvelle") && !actif(m3, "charger") && !actif(m3, "lot") && !actif(m3, "supprimer") && actif(m3, "arret"));
check("6.5 chaque entrée a sa clé de texte, séparateurs compris", m1.every((x) => x === null || /^photolab\.actions\.menu\./.test(x.cle)));

// 7. Traitement par lots
check("7.1 paramsLot : action et image requises", paramsLot({ images: ["a.png"] }).erreur === "photolab.actions.lot_erreur_action"
  && paramsLot({ action: "A", images: [] }).erreur === "photolab.actions.lot_erreur_images"
  && paramsLot({ action: "A", images: Array.from({ length: 501 }, (_, i) => i + ".png") }).erreur === "photolab.actions.lot_erreur_trop");
const pl = paramsLot({ action: "A", images: ["a.png", "a.png", "b.jpg"], format: "jpg", quality: "250", suffixe: "  inverse  ", continuer: 1 });
check("7.2 paramsLot : doublons ôtés, jpg + qualité bornée, suffixe propre", eq(pl, { action: "A", images: ["a.png", "b.jpg"], format: "jpg", suffixe: "inverse", continuer: true, quality: 100 }), pl);
check("7.3 png sans qualité ; format inconnu = png", paramsLot({ action: 0, images: ["a.png"], format: "tif" }).format === "png" && !("quality" in paramsLot({ action: 0, images: ["a.png"] })));
check("7.4 corpsLot : le corps de /actions/lot (sans continuer ni images)", eq(corpsLot(pl, "a.png"), { action: "A", filename: "a.png", format: "jpg", quality: 100, suffixe: "inverse" }));

// 8. copies du pont relues dans le source Python
const py = lire(depot, "backend", "app", "services", "photolab_registre.py");
const tuple = (nom) => {
  const m = py.match(new RegExp(nom + " = \\(([\\s\\S]*?)\\)\\r?\\n"));
  return m ? [...m[1].matchAll(/"([^"]*)"/g)].map((x) => x[1]) : null;
};
check("8.1 CONDITIONS = CONDITIONS_ACTION du pont (même ordre)", eq(CONDITIONS, tuple("CONDITIONS_ACTION")), tuple("CONDITIONS_ACTION"));
check("8.2 COULEURS = COULEURS_ACTION du pont", eq(COULEURS, tuple("COULEURS_ACTION")), tuple("COULEURS_ACTION"));
const borne = (nom) => Number((py.match(new RegExp("^" + nom + " = ([0-9_]+)", "m")) || [])[1].replace(/_/g, ""));
check("8.3 bornes : nom, message, .atn", MAX_NOM === borne("MAX_NOM_ACTION") && MAX_MESSAGE === borne("MAX_MESSAGE_ARRET") && MAX_OCTETS_ATN === borne("MAX_OCTETS_ATN"));

// 9. branchement de l'écran
const html = lire(racine, "index.html");
check("9.1 onglet Actions dans le groupe Calques, après Historique ; corps #corpsActions", /data-onglet="historique">Historique<\/button>[\s\S]{0,200}data-onglet="actions">Actions<\/button>/.test(html)
  && /id="corpsActions" data-vue="actions" hidden/.test(html));
check("9.2 bouton du rail (icône dz-nav-panneau-actions)", /data-panneau="actions"[^>]*>[\s\S]{0,200}#dz-nav-panneau-actions/.test(html));
check("9.3 Fenêtre › Actions et Traitement par lots servis par l'écran", TRAITES_PAR_ECRAN.has("window.panel.actions") && TRAITES_PAR_ECRAN.has("file.automate.batch"));
check("9.4 groupe Calques : Actions entre Historique et Navigateur ; Fenêtre › Actions y mène", eq(GROUPES.calques, ["calques", "couches", "traces", "historique", "actions", "navigateur"])
  && eq(PANNEAUX["window.panel.actions"], { groupe: "calques", onglet: "actions" }));
const pyEsp = lire(depot, "backend", "app", "services", "photolab_espaces.py");
check("9.5 copie Python des groupes (photolab_espaces) à jour", /"calques": \("calques", "couches", "traces", "historique", "actions", "navigateur"\)/.test(pyEsp));
check("9.6 core : init du panneau et relecture à l'onglet montré", /initActions\(PL\)/.test(lire(racine, "js", "core.js")) && /nom === "actions" && PL\.actionsPanneau/.test(lire(racine, "js", "core.js")));

// 10. textes : toutes les clés du panneau, fr et en
const dico = { ...JSON.parse(lire(racine, "..", "shared", "i18n", "commun.json")), ...JSON.parse(lire(racine, "..", "shared", "i18n", "photolab.json")) };
const present = (k) => !!(dico[k] && dico[k].fr && dico[k].en);
const src = lire(racine, "js", "mod-actions.js");
const ecrites = [...new Set([...src.matchAll(/"((?:photolab|commun)\.[a-z0-9_.]+[a-z0-9_])"/g)].map((x) => x[1]))];
const composees = [...COULEURS.map(cleCouleur), ...CONDITIONS.map(cleCondition), ...m1.filter(Boolean).map((x) => x.cle), "photolab.panneau.actions"];
check("10.1 clés écrites en toutes lettres : présentes en fr et en", ecrites.every(present), ecrites.filter((k) => !present(k)));
check("10.2 clés composées (couleurs, conditions, menu, rail) : présentes en fr et en", composees.every(present), composees.filter((k) => !present(k)));
check("10.3 noms d'actions, de jeux, de fichiers et messages d'arrêt : jamais traduits (data-dz-brut)",
  /brut\(el\("span", "ac-nom", a\.nom\)\)/.test(src) && /brut\(el\("span", "ac-nom", n\.nom\)\)/.test(src) && /brut\(el\("p", "ac-message", op\.message\)\)/.test(src)
  && /brut\(el\("button", "lib-carte ac-lot-carte/.test(src) && /brut\(el\("button", "ac-bouton/.test(src));
check("10.4 aucun chemin envoyé au pont : actions.load / actions.save en données seulement", !/actions\.(load|save)", \{[^}]*path/.test(src) && /actions\.load", \{ data, replace: false \}/.test(src));

console.log(`actions-m6 : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
