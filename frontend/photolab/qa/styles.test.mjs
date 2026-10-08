// qa/styles.test.mjs — Style de calque (t138 B6) : STYLES (ordre et champs du dialogue de photocraft,
// crates/ui-egui/src/layer_style.rs), etatStyles (mémoire de l'écran + effects de doc.inspect), etapesStyles (étapes
// minimales : le moteur REMPLACE un effet par ses défauts + les clés reçues, il faut tout renvoyer), memoriser,
// ouvertureStyles, libelleStyle. Fonctions PURES.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { STYLES, EFFETS, OPTIONS_FUSION, infoStyle, defautsStyle, normaliserParams, egalParams, etatStyles, etapesStyles,
  memoriser, libelleStyle, ouvertureStyles, marqueHistorique, memoireValide, memoireDuCalque } from "../js/mod-styles.js";
import * as ST from "../js/mod-styles.js";
import { libelleOption, identiteDocument } from "../js/mod-dialogue-reglage.js";
import { valeursDe } from "../js/mod-champs.js";
import { MODES_FUSION, aDesEffets } from "../js/mod-calques.js";
import { construireMenus } from "../js/mod-menus.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, typeof detail === "string" ? detail : JSON.stringify(detail)); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const json = (x) => JSON.stringify(x);
const copie = (x) => JSON.parse(JSON.stringify(x));
const ids = new Set(MODES_FUSION.map((m) => m.id));

// 1. ordre et champs (layer_style.rs : KINDS, spec, defaults)
check("1.1 options de fusion en tête, puis les 10 effets dans l'ordre de photocraft", json(STYLES.map((s) => s.kind)) === json([OPTIONS_FUSION,
  "bevelEmboss", "stroke", "innerShadow", "innerGlow", "satin", "colorOverlay", "gradientOverlay", "patternOverlay", "outerGlow", "dropShadow"]));
check("1.2 EFFETS = les 10 sans les options de fusion", EFFETS.length === 10 && !EFFETS.some((s) => s.kind === OPTIONS_FUSION));
check("1.3 libellé moteur (doc.inspect) de chaque effet", json(EFFETS.map((s) => s.moteur)) === json(["Bevel & Emboss", "Stroke", "Inner Shadow",
  "Inner Glow", "Satin", "Color Overlay", "Gradient Overlay", "Pattern Overlay", "Outer Glow", "Drop Shadow"]));
check("1.4 ordre des champs de l'ombre portée", json(infoStyle("dropShadow").champs.map((c) => c.cle)) ===
  json(["blend", "color", "opacity", "angle", "distance", "spread", "size", "knocksOut"]));
check("1.5 défauts de l'ombre portée (ids de fusion, pas les libellés)", json(defautsStyle("dropShadow")) === json({ blend: "multiply", color: "#000000",
  opacity: 75, angle: 120, distance: 5, spread: 0, size: 5, knocksOut: true }), defautsStyle("dropShadow"));
check("1.6 défauts du satin et du contour", json(defautsStyle("satin")) === json({ blend: "multiply", color: "#000000", opacity: 50, angle: 19, distance: 11, size: 14, invert: true })
  && json(defautsStyle("stroke")) === json({ size: 3, position: "outside", blend: "normal", opacity: 100, color: "#000000" }));
check("1.7 le contour n'a ni from ni to (from présent = contour en DÉGRADÉ pour le moteur)", !infoStyle("stroke").champs.some((c) => c.cle === "from" || c.cle === "to"));
check("1.8 biseau : 4 styles du dialogue, défauts", json(infoStyle("bevelEmboss").champs.find((c) => c.cle === "style").valeurs) === json(["inner", "outer", "emboss", "pillow"])
  && json(defautsStyle("bevelEmboss")) === json({ style: "inner", depth: 100, direction: "up", size: 5, soften: 0, angle: 120, altitude: 30 }));
check("1.9 chaque effet a des champs et des défauts complets", EFFETS.every((s) => s.champs.length && Object.keys(defautsStyle(s.kind)).length === s.champs.length));
check("1.10 aucun champ caché/opaque (layer, add, enabled, pattern)", STYLES.every((s) => s.champs.every((c) => !["layer", "add", "enabled", "pattern", "blendIf"].includes(c.cle))));
check("1.11 bornes des curseurs : distance 0..300, taille 0..250, échelle du dégradé 10..150",
  (() => { const c = (k, cle) => infoStyle(k).champs.find((x) => x.cle === cle); return c("dropShadow", "distance").max === 300 && c("dropShadow", "size").max === 250
    && c("gradientOverlay", "scale").min === 10 && c("gradientOverlay", "scale").max === 150 && c("stroke", "size").min === 1; })());
check("1.12 kind inconnu -> null", infoStyle("zorg") === null && json(defautsStyle("zorg")) === "{}");

// 2. normalisation (coercition de mod-champs)
const n = normaliserParams("dropShadow", { color: "#ABC", opacity: 150, size: "3,7", blend: "Linear Dodge (Add)", add: true, layer: 4 });
check("2.1 couleur #ABC -> #aabbcc, opacité bornée, « 3,7 » -> 4, fusion lisible -> id, clés étrangères retirées",
  n.color === "#aabbcc" && n.opacity === 100 && n.size === 4 && n.blend === "linearDodge" && !("add" in n) && !("layer" in n) && Object.keys(n).length === 8, n);
check("2.2 fusion « zorg » ou passThrough dans un effet -> défaut du style", normaliserParams("dropShadow", { blend: "zorg" }).blend === "multiply"
  && normaliserParams("outerGlow", { blend: "passThrough" }).blend === "screen");
check("2.3 options de fusion : passThrough GARDÉ (un groupe), « Multiply » -> multiply", normaliserParams(OPTIONS_FUSION, { blend: "Pass Through" }).blend === "passThrough"
  && normaliserParams(OPTIONS_FUSION, { blend: "Multiply", opacity: 50.4 }).blend === "multiply" && normaliserParams(OPTIONS_FUSION, { opacity: 50.4 }).opacity === 50);
check("2.4 egalParams ignore l'ordre et la forme d'écriture", egalParams("dropShadow", { color: "#ABC" }, { color: "#aabbcc" }) && !egalParams("dropShadow", { size: 6 }, {}));

// 3. etatStyles
const calque = { id: 3, name: "Calque 1", blend: "Multiply", opacity: 0.5, fill: 1 };
let e = etatStyles({}, undefined, calque);
check("3.1 rien au moteur, rien en mémoire : 10 effets éteints aux défauts", EFFETS.every((s) => e[s.kind].actif === false && e[s.kind].present === false
  && !e[s.kind].inconnu && json(e[s.kind].params) === json(defautsStyle(s.kind))));
check("3.2 options de fusion relues sur le calque (Multiply, 50 %, fond 100 %)", json(e[OPTIONS_FUSION].params) === json({ blend: "multiply", opacity: 50, fillOpacity: 100 }), e[OPTIONS_FUSION]);
check("3.3 sans calque : options de fusion par défaut", json(etatStyles(null, null, null)[OPTIONS_FUSION].params) === json({ blend: "normal", opacity: 100, fillOpacity: 100 }));
const fx = { enabled: true, items: [{ enabled: true, kind: "Drop Shadow" }, { enabled: false, kind: "Bevel & Emboss" }] };
e = etatStyles({}, fx, calque);
check("3.4 effet au moteur inconnu de la mémoire (document rouvert) -> actif, défauts, inconnu", e.dropShadow.actif && e.dropShadow.present && e.dropShadow.inconnu === true
  && json(e.dropShadow.params) === json(defautsStyle("dropShadow")));
check("3.5 effet éteint au moteur -> présent mais pas actif", e.bevelEmboss.present && e.bevelEmboss.actif === false && e.bevelEmboss.inconnu === true);
const mem = { dropShadow: { actif: true, params: { ...defautsStyle("dropShadow"), size: 12 } }, satin: { actif: true, params: { ...defautsStyle("satin"), angle: 45 } } };
e = etatStyles(mem, fx, calque);
check("3.6 mémoire connue : ses paramètres, plus d'inconnu", e.dropShadow.params.size === 12 && !e.dropShadow.inconnu);
check("3.7 en mémoire mais plus au moteur (effacé, annulé) : éteint, paramètres gardés", e.satin.actif === false && e.satin.present === false && e.satin.params.angle === 45);
check("3.8 libellé ou id du kind admis (« dropShadow »)", etatStyles({}, { items: [{ enabled: true, kind: "dropShadow" }] }, calque).dropShadow.present === true);
check("3.9 tableau d'items admis tel quel", etatStyles({}, [{ enabled: true, kind: "Stroke" }], calque).stroke.actif === true);

// 4. etapesStyles : les 8 cas du plan + autres
const base = etatStyles({}, undefined, calque);
const avec = (etat, kind, f) => { const x = copie(etat); f(x[kind]); return x; };
check("4.1 aucun changement -> []", json(etapesStyles(base, copie(base), 3)) === "[]");
let apres = avec(base, "dropShadow", (s) => { s.actif = true; });
let et = etapesStyles(base, apres, 3);
check("4.2 un ajout -> une étape, calque + TOUS les paramètres", et.length === 1 && et[0].command === "layer.layerStyle.dropShadow"
  && json(et[0].params) === json({ layer: 3, ...defautsStyle("dropShadow") }), et);
const actifOmbre = avec(base, "dropShadow", (s) => { s.actif = true; s.present = true; });
apres = avec(actifOmbre, "dropShadow", (s) => { s.params.distance = 20; });
et = etapesStyles(actifOmbre, apres, 3);
check("4.3 modification d'un seul paramètre -> tous les paramètres renvoyés", et.length === 1 && json(et[0].params) === json({ layer: 3, ...defautsStyle("dropShadow"), distance: 20 }), et);
apres = avec(actifOmbre, "dropShadow", (s) => { s.actif = false; });
et = etapesStyles(actifOmbre, apres, 3);
check("4.4 désactivation -> enabled:false + tous les paramètres", et.length === 1 && json(et[0].params) === json({ layer: 3, enabled: false, ...defautsStyle("dropShadow") }), et);
apres = avec(avec(base, "dropShadow", (s) => { s.actif = true; }), "stroke", (s) => { s.actif = true; s.params.size = 8; });
et = etapesStyles(base, apres, 3);
check("4.5 deux kinds -> deux étapes, dans l'ordre du dialogue (contour avant ombre portée)", json(et.map((x) => x.command)) ===
  json(["layer.layerStyle.stroke", "layer.layerStyle.dropShadow"]) && et[0].params.size === 8, et);
apres = avec(apres, OPTIONS_FUSION, (s) => { s.params.fillOpacity = 40; });
et = etapesStyles(base, apres, 3);
check("4.6 options de fusion changées -> blendingOptions {layer, blend, opacity, fillOpacity} en tête", et.length === 3 && et[0].command === "layer.layerStyle.blendingOptions"
  && json(et[0].params) === json({ layer: 3, blend: "multiply", opacity: 50, fillOpacity: 40 }), et);
apres = avec(avec(base, "outerGlow", (s) => { s.actif = true; s.params.blend = "Color Dodge"; }), "satin", (s) => { s.actif = true; s.params.blend = "zorg"; });
et = etapesStyles(base, apres, 3);
check("4.7 mode de fusion validé contre MODES_FUSION (lisible -> id, inconnu -> défaut)", et.length === 2 && et.every((x) => ids.has(x.params.blend))
  && et.find((x) => x.command.endsWith("outerGlow")).params.blend === "colorDodge" && et.find((x) => x.command.endsWith("satin")).params.blend === "multiply", et);
apres = avec(base, "colorOverlay", (s) => { s.actif = true; s.params.color = "#0F0"; });
et = etapesStyles(base, apres, 3);
check("4.8 couleur normalisée (#0F0 -> #00ff00)", et.length === 1 && et[0].params.color === "#00ff00", et);
const ecrite = avec(actifOmbre, "dropShadow", (s) => { s.params.color = "#000"; });
check("4.9 même valeur sous une autre écriture -> aucun envoi", etapesStyles(actifOmbre, ecrite, 3).length === 0);
et = etapesStyles(base, avec(base, "dropShadow", (s) => { s.actif = true; }), null);
check("4.10 sans calque visé : pas de clé layer (le moteur prend le calque actif)", et.length === 1 && !("layer" in et[0].params));
const inconnu = etatStyles({}, fx, calque);
check("4.11 effet inconnu laissé tel quel -> aucun envoi (le moteur garde ses vrais paramètres)", etapesStyles(inconnu, copie(inconnu), 3).length === 0);
et = etapesStyles(inconnu, avec(inconnu, "dropShadow", (s) => { s.params.size = 9; }), 3);
check("4.12 effet inconnu édité -> tous ses paramètres", et.length === 1 && Object.keys(et[0].params).length === 9 && et[0].params.size === 9, et);
et = etapesStyles(inconnu, avec(inconnu, "bevelEmboss", (s) => { s.params.depth = 300; }), 3);
check("4.13 effet éteint au moteur, réglé sans le rallumer -> enabled:false + paramètres", et.length === 1 && et[0].params.enabled === false && et[0].params.depth === 300, et);
check("4.14 effet absent du moteur, réglé sans être coché -> rien (il n'existe pas)", etapesStyles(base, avec(base, "satin", (s) => { s.params.size = 30; }), 3).length === 0);
et = etapesStyles(inconnu, avec(inconnu, "bevelEmboss", (s) => { s.actif = true; }), 3);
check("4.15 effet éteint rallumé -> paramètres complets, sans enabled:false", et.length === 1 && !("enabled" in et[0].params) && et[0].params.depth === 100, et);
apres = copie(base); for (const s of EFFETS) apres[s.kind].actif = true;
apres[OPTIONS_FUSION].params.opacity = 10;
et = etapesStyles(base, apres, 3);
check("4.16 tout coché + options : 11 étapes (≤ 12, borne de /apercu)", et.length === 11 && et.length <= 12);
const ombreGroupe = etatStyles({}, undefined, { id: 9, blend: "Pass Through", opacity: 1, fill: 1, children: [] });
et = etapesStyles(ombreGroupe, avec(ombreGroupe, OPTIONS_FUSION, (s) => { s.params.opacity = 60; }), 9);
check("4.17 groupe en Pass Through : l'opacité changée ne le repasse pas en Normal", et.length === 1 && et[0].params.blend === "passThrough", et);

// 5. mémoire
const etapes = etapesStyles(inconnu, avec(avec(inconnu, "stroke", (s) => { s.actif = true; s.params.size = 7; }), OPTIONS_FUSION, (s) => { s.params.opacity = 20; }), 3);
const apresM = avec(avec(inconnu, "stroke", (s) => { s.actif = true; s.params.size = 7; }), OPTIONS_FUSION, (s) => { s.params.opacity = 20; });
const m2 = memoriser({ satin: { actif: false, params: { angle: 1 } } }, apresM, etapes);
check("5.1 seuls les kinds envoyés entrent en mémoire (pas l'ombre inconnue, pas les options de fusion relues au moteur)",
  json(Object.keys(m2).sort()) === json(["satin", "stroke"]) && m2.stroke.actif === true && m2.stroke.params.size === 7, m2);
check("5.2 mémoire d'origine intacte", (() => { const m = { a: 1 }; memoriser(m, apresM, etapes); return json(m) === json({ a: 1 }); })());
// La mémoire est rangée sous identiteDocument (mod-dialogue-reglage), plus de copie locale cleDocument.
check("5.3 clé de mémoire = identiteDocument : nom|index|génération ; plus de cleDocument", identiteDocument({ name: "Sans titre-1", index: 0 }, 4) === "Sans titre-1|0|4"
  && identiteDocument(null, 1) === null && !("cleDocument" in ST));
check("5.4 deux documents de même nom : deux clés", identiteDocument({ name: "Sans titre-1", index: 0 }, 4) !== identiteDocument({ name: "Sans titre-1", index: 1 }, 4));
// repère d'historique : la mémoire ne vaut que si l'historique contient encore, à sa place, l'entrée notée après OK
const H = ["Open", "Fill", "Layer Style: Stroke", "Layer Style: Drop Shadow"];
const marque = marqueHistorique(H);
check("5.5 marque = longueur + dernier libellé", json(marque) === json({ n: 4, libelle: "Layer Style: Drop Shadow" }) && marqueHistorique([]) === null && marqueHistorique(undefined) === null);
const entree = { effets: { dropShadow: { actif: true, params: { size: 12 } } }, marque };
check("5.6 même historique, ou gestes ajoutés depuis : valide", memoireValide(entree, H) && memoireValide(entree, [...H, "Brush"]));
check("5.7 Ctrl+Z (historique plus court) : invalide", !memoireValide(entree, H.slice(0, 3)));
check("5.8 Ctrl+Z puis autre geste (entrée remplacée à sa place) : invalide", !memoireValide(entree, [...H.slice(0, 3), "Brush"]));
check("5.9 Ctrl+Z puis Ctrl+Y : de nouveau valide", memoireValide(entree, H));
check("5.10 sans repère : valide seulement si le pont ne rend pas d'historique", memoireValide({ effets: {} }, undefined) && !memoireValide({ effets: {} }, H) && !memoireValide(null, H));
check("5.11 memoireDuCalque : effets si valide, {} sinon", memoireDuCalque(entree, H) === entree.effets && json(memoireDuCalque(entree, ["Open"])) === "{}");
const apresUndo = etatStyles(memoireDuCalque(entree, H.slice(0, 3)), { items: [{ enabled: true, kind: "Drop Shadow" }] }, calque);
check("5.12 après Ctrl+Z : l'effet encore au moteur redevient inconnu (défauts)", apresUndo.dropShadow.inconnu === true && apresUndo.dropShadow.params.size === 5);

// 6. ouverture : style demandé coché et sélectionné (photocraft : initial_fields(select))
let o = ouvertureStyles(base, "stroke");
check("6.1 depuis le menu Contour… : contour sélectionné et coché", o.selection === "stroke" && o.etat.stroke.actif === true && base.stroke.actif === false);
o = ouvertureStyles(inconnu, undefined);
check("6.2 bouton fx : premier effet présent (ordre du dialogue), rien coché de plus", o.selection === "bevelEmboss" && o.etat.bevelEmboss.actif === false);
check("6.3 aucun effet : ombre portée sélectionnée, non cochée", ouvertureStyles(base).selection === "dropShadow" && ouvertureStyles(base).etat.dropShadow.actif === false);
check("6.4 Options de fusion… : page des options, rien coché", ouvertureStyles(base, OPTIONS_FUSION).selection === OPTIONS_FUSION
  && EFFETS.every((s) => ouvertureStyles(base, OPTIONS_FUSION).etat[s.kind].actif === false));

// 7. libellés : catalogue des menus (Calque › Style de calque), jamais de clé ajoutée
const catalogue = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));
const arbreFr = construireMenus(catalogue, [], [], "fr");
const arbreEn = construireMenus(catalogue, [], [], "en");
const t = (c) => (c === "photolab.styles.options_fusion" ? "Options de fusion" : c);
check("7.1 fr : libellé du catalogue sans « … »", libelleStyle("dropShadow", arbreFr, t) === "Ombre portée"
  && EFFETS.every((s) => libelleStyle(s.kind, arbreFr, t) === titreCat("layer.layerStyle." + s.kind, "libelle_fr")), EFFETS.map((s) => libelleStyle(s.kind, arbreFr, t)));
check("7.2 en : libellé anglais du catalogue", libelleStyle("dropShadow", arbreEn, t) === "Drop Shadow");
check("7.3 options de fusion : clé photolab.styles.options_fusion", libelleStyle(OPTIONS_FUSION, arbreFr, t) === "Options de fusion");
check("7.4 sans catalogue : libellé moteur (jamais vide)", libelleStyle("innerGlow", [], t) === "Inner Glow");
check("7.5 les 10 effets ont leur entrée au catalogue", EFFETS.every((s) => catalogue.entrees.some((x) => x.id === "layer.layerStyle." + s.kind)));
const dico = JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8"));
const tFr = (c) => (dico[c] ? dico[c].fr : c), tEn = (c) => (dico[c] ? dico[c].en : c);
check("7.6 vocabulaire Photoshop (dictionnaire) : Contour, Biseautage et estampage, Incrustation couleur…",
  json(EFFETS.map((s) => libelleStyle(s.kind, arbreFr, tFr))) === json(["Biseautage et estampage", "Contour", "Ombre interne", "Lueur interne", "Satin",
    "Incrustation couleur", "Incrustation en dégradé", "Incrustation de motif", "Lueur externe", "Ombre portée"]), EFFETS.map((s) => libelleStyle(s.kind, arbreFr, tFr)));
check("7.7 en anglais : Stroke, Bevel & Emboss", libelleStyle("stroke", arbreEn, tEn) === "Stroke" && libelleStyle("bevelEmboss", arbreEn, tEn) === "Bevel & Emboss");
check("7.8 jamais « Contourner » quand le dictionnaire est là", libelleStyle("stroke", arbreFr, tFr) !== "Contourner");
check("7.9 clés des 8 styles renommés : fr et en", STYLES.filter((s) => s.cle).length === 8 && STYLES.every((s) => !s.cle || (dico[s.cle] && dico[s.cle].fr && dico[s.cle].en)));
// Transfert (passThrough) : libellé photolab.fusion.pass_through, et toujours listé pour les options de fusion d'un groupe
check("7.10 libelleOption(passThrough) -> photolab.fusion.pass_through", libelleOption({ cle: "blend", type: "str" }, "passThrough", tFr) === "Transfert");
check("7.11 valeursDe : passThrough en tête seulement si transfert", valeursDe({ cle: "blend", type: "str", transfert: true })[0] === "passThrough"
  && valeursDe({ cle: "blend", type: "str", transfert: true }).length === 28 && !valeursDe({ cle: "blend", type: "str" }).includes("passThrough"));
function titreCat(id, cle) { const x = catalogue.entrees.find((y) => y.id === id); return x ? String(x[cle]).replace(/…$/, "") : null; }

// 8. badge « fx » du panneau Calques
check("8.1 aDesEffets : items non vides seulement", aDesEffets({ effects: fx }) && !aDesEffets({ effects: { items: [] } }) && !aDesEffets({}) && !aDesEffets(null));

console.log(`styles : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
