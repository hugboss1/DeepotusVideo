// qa/calques-m7.test.mjs — t256 (Photolab M7, moteur photocraft 0.10) : calques. Entrées de 0.10 insérées dans les
// menus (Calque, Filtre), Alt-clic sur l'œil, couleur d'étiquette, « / » (verrou de transparence), badge fx glissé,
// cadre, densité / contour progressif du masque, défauts d'effet du dialogue Style de calque.
// Fonctions PURES ; réponses relevées sur le vrai moteur (backend/tests/test_photolab_m7.py [2]).
import { construireMenus, actionEntree, REFUSES, INSERTIONS_M7, IDS_CALQUES_M7, DIALOGUES_ECRAN_M7, TRAITES_PAR_ECRAN, NECESSITE_DOC }
  from "../js/mod-menus.js";
import { commandeOeil, COULEURS_ETIQUETTE, couleurEtiquette, toucheVerrouTransparence, verrousApresBascule, transfertEffets,
  rectCadre, masqueDefaut } from "../js/mod-calques.js";
import { defautEffet, defautsStyle } from "../js/mod-styles.js";
import { readFileSync } from "node:fs";
import { ETATS_MOTEUR } from "../js/mod-historique.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// 1. menus : chaque entrée de 0.10 à sa place, son état suit le registre
const cat = (chemin, id) => ({ chemin, id, libelle_fr: id, libelle_en: id, raccourci: null });
const catalogue = { entrees: [
  cat(["Layer", "New"], "layer.new.layer"), cat(["Layer", "New"], "layer.new.layerFromBackground"), cat(["Layer", "New"], "layer.new.group"),
  cat(["Layer", "New"], "layer.new.artboard"), cat(["Layer", "New"], "layer.new.artboardFromLayers"), cat(["Layer", "New"], "layer.new.frameFromLayers"),
  cat(["Layer"], "layer.duplicate"), cat(["Layer"], "layer.renameLayer"),
  cat(["Layer", "Smart Objects"], "layer.smartObjects.convertToSmartObject"), cat(["Layer", "Smart Objects"], "layer.smartObjects.newSmartObjectViaCopy"),
  cat(["Layer", "Smart Objects"], "layer.smartObjects.revealInFinder"),
  cat(["Layer", "Rasterize"], "layer.rasterize.smartObject"), cat(["Layer", "Rasterize"], "layer.rasterize.layer"),
  cat(["Layer"], "layer.mergeLayers"), cat(["Layer"], "layer.mergeVisible"),
  cat(["Filter", "Render"], "filter.render.lensFlare"), cat(["Filter", "Render"], "filter.render.lightingEffects"),
  cat(["Filter", "Other…"], "filter.other.highPass"),
] };
const champ = (cle, type, extra = {}) => ({ cle, type, optionnel: false, ...extra });
const registre = [
  ...catalogue.entrees.map((e) => ({ id: e.id, enabled: true, champs: [] })),
  { id: "layer.new.backgroundFromLayer", enabled: false, champs: [{ cle: "layer", type: "layerId", optionnel: true }] },
  { id: "layer.artboard.addBeside", enabled: false, champs: [champ("side", "enum", { valeurs: ["left", "right", "top", "bottom"], defaut: "right" }), champ("duplicate", "bool", { defaut: false })] },
  { id: "layer.removeBackground", enabled: true, champs: [champ("sampleAllLayers", "bool", { defaut: false }), champ("refine", "bool", { defaut: true })] },
  { id: "layer.setLabelColor", enabled: true, champs: [champ("color", "enum", { valeurs: ["none", ...COULEURS_ETIQUETTE] }), { cle: "layer", type: "layerId", optionnel: true }] },
  { id: "layer.smartObjects.convertToLayers", enabled: true, champs: [{ cle: "layer", type: "layerId", optionnel: true }] },
  { id: "layer.rasterize.layerStyle", enabled: true, champs: [{ cle: "layer", type: "layerId", optionnel: true }] },
  { id: "layer.mergeGroup", enabled: true, champs: [{ cle: "layer", type: "layerId", optionnel: true }] },
  { id: "filter.render.relight", enabled: true, champs: [champ("angle", "number", { min: -180, max: 180, defaut: 45 })] },
  { id: "filter.other.colorToAlpha", enabled: true, champs: [champ("color", "color", { formes: ["hex"] })] },
];
const menus = construireMenus(catalogue, registre, REFUSES, "fr", (k) => k);
const sous = (chemin) => {
  let l = menus.find((m) => m.nom === chemin[0]).entrees;
  for (const n of chemin.slice(1)) l = l.find((x) => x.type === "sous-menu" && x.nom === n).entrees;
  return l;
};
for (const ins of INSERTIONS_M7) {
  const l = sous(ins.chemin);
  const k = l.findIndex((e) => e.id === ins.id);
  const avant = l[k - 1];
  check(`1.1 ${ins.id} inséré dans ${ins.chemin.join(" › ")} ${ins.apres ? "après " + ins.apres : "en fin"}`,
    k >= 0 && (ins.apres ? avant && avant.id === ins.apres : k === l.length - 1) && l[k].libelle === ins.cle, l.map((e) => e.id));
}
const entree = (id) => { for (const ins of INSERTIONS_M7) if (ins.id === id) return sous(ins.chemin).find((e) => e.id === id); return null; };
check("1.2 Calque › Nouveau : Plan de travail voisin puis Cadre…", (() => {
  const l = sous(["Layer", "New"]).map((e) => e.id);
  return l.indexOf("pl.calque.cadre") === l.indexOf("layer.artboard.addBeside") + 1;
})());
check("1.3 l'état suit le registre : sans plan de travail / avec un arrière-plan, inactif ; sinon actif",
  entree("layer.artboard.addBeside").etat === "inactif" && entree("layer.new.backgroundFromLayer").etat === "inactif"
  && entree("filter.render.relight").etat === "actif", [entree("layer.artboard.addBeside").etat, entree("filter.render.relight").etat]);
check("1.4 sans champ visible : exécution directe (Fusionner le groupe, Convertir en calques, Pixelliser le style)",
  ["layer.mergeGroup", "layer.smartObjects.convertToLayers", "layer.rasterize.layerStyle"].every((id) => actionEntree(entree(id)) === "executer"));
check("1.5 avec champs : dialogue (Rééclairer, Couleur en alpha, Retirer l'arrière-plan (local), Couleur du calque, Plan voisin)",
  ["filter.render.relight", "filter.other.colorToAlpha", "layer.removeBackground", "layer.setLabelColor"].every((id) => actionEntree(entree(id)) === "dialogue"));
check("1.6 Cadre… et Dupliquer vers un document… : entrées de l'écran, actives, document requis",
  IDS_CALQUES_M7.every((id) => TRAITES_PAR_ECRAN.has(id) && NECESSITE_DOC.has(id) && actionEntree(entree(id)) === "ecran" && entree(id).etat === "actif")
  && eq(Object.keys(DIALOGUES_ECRAN_M7).sort(), [...IDS_CALQUES_M7].sort()));
check("1.7 aucune commande moteur insérée n'est dans TRAITES_PAR_ECRAN (jamais envoyée au moteur sinon)",
  INSERTIONS_M7.filter((x) => !x.id.startsWith("pl.")).every((x) => !TRAITES_PAR_ECRAN.has(x.id)));
const sansMoteur = construireMenus(catalogue, catalogue.entrees.map((e) => ({ id: e.id, enabled: true, champs: [] })), REFUSES, "fr", (k) => k);
const relight = (() => { let l = sansMoteur.find((m) => m.nom === "Filter").entrees.find((x) => x.nom === "Render").entrees; return l.find((e) => e.id === "filter.render.relight"); })();
check("1.8 moteur sans la commande : l'entrée reste visible, « bientôt »", relight && relight.etat === "bientot", relight);

// 1.9 sur le VRAI catalogue (donnees/menus.json) : chaque chemin existe et chaque ancre y est (ou est une insertion de
// l'écran placée avant) — le sous-menu « Autre » s'écrit « Other… » au catalogue, une faute d'un caractère suffit.
const vrai = JSON.parse(readFileSync(new URL("../donnees/menus.json", import.meta.url), "utf8"));
const chemins = new Set(vrai.entrees.map((e) => e.chemin.join("/")));
const ids = new Set(vrai.entrees.map((e) => e.id).filter(Boolean));
const vus = new Set(["pl.calque.ia", "pl.calque.detourer"]);
for (const ins of INSERTIONS_M7) {
  check(`1.9 ${ins.id} : chemin ${ins.chemin.join(" › ")} au catalogue, ancre ${ins.apres} présente`,
    chemins.has(ins.chemin.join("/")) && (ins.apres === null || ids.has(ins.apres) || vus.has(ins.apres)), ins);
  vus.add(ins.id);
}

// 2. œil : clic = montrer / masquer, Alt-clic = ce calque seul
check("2.1 clic : layer.setProps visible inversé", eq(commandeOeil({ id: 4, visible: true }, false), { command: "layer.setProps", params: { layer: 4, visible: false } })
  && eq(commandeOeil({ id: 4, visible: false }, false).params.visible, true));
check("2.2 Alt-clic : layer.showOnly {layer}", eq(commandeOeil({ id: 4, visible: true }, true), { command: "layer.showOnly", params: { layer: 4 } }));

// 3. couleur d'étiquette relue dans doc.inspect
check("3.1 les onze couleurs du moteur, « none » à part", COULEURS_ETIQUETTE.length === 11 && !COULEURS_ETIQUETTE.includes("none"));
check("3.2 labelColor connu -> la couleur ; none / absent / inconnu -> null",
  couleurEtiquette({ labelColor: "seafoam" }) === "seafoam" && couleurEtiquette({ labelColor: "none" }) === null
  && couleurEtiquette({}) === null && couleurEtiquette({ labelColor: "pink" }) === null);

// 4. « / » : verrou de transparence
const ev = (o) => ({ key: "/", ctrlKey: false, metaKey: false, altKey: false, repeat: false, target: { tagName: "DIV" }, ...o });
check("4.1 « / » seul hors saisie", toucheVerrouTransparence(ev({})));
check("4.2 pas avec Ctrl, Alt, en répétition, dans un champ, ni une autre touche",
  !toucheVerrouTransparence(ev({ ctrlKey: true })) && !toucheVerrouTransparence(ev({ altKey: true })) && !toucheVerrouTransparence(ev({ repeat: true }))
  && !toucheVerrouTransparence(ev({ target: { tagName: "INPUT" } })) && !toucheVerrouTransparence(ev({ target: { tagName: "DIV", isContentEditable: true } }))
  && !toucheVerrouTransparence(ev({ key: "x" })));
const v0 = { transparency: false, pixels: true, position: false, artboard: false, all: false };
check("4.3 réponse {locked} -> seul le verrou de transparence change", eq(verrousApresBascule(v0, true), { ...v0, transparency: true })
  && eq(verrousApresBascule(undefined, false), { transparency: false, pixels: false, position: false, artboard: false, all: false }));

// 5. badge fx glissé
check("5.1 sur une autre ligne : déplacer ; Alt : copier", eq(transfertEffets(3, 4, false), { from: 3, to: 4, copy: false }) && transfertEffets(3, 4, true).copy === true);
check("5.2 sur sa propre ligne, ou source illisible : rien", transfertEffets(3, 3, false) === null && transfertEffets(NaN, 3, false) === null);

// 6. cadre : la sélection, sinon la toile
check("6.1 sélection [x, y, l, h] arrondie", eq(rectCadre({ width: 200, height: 120, hasSelection: true, selectionBounds: [10.4, 20.6, 50, 40] }), { x: 10, y: 21, width: 50, height: 40 }));
check("6.2 sans sélection : toute la toile", eq(rectCadre({ width: 200, height: 120, hasSelection: false }), { x: 0, y: 0, width: 200, height: 120 }));
check("6.3 sélection vide : la toile", eq(rectCadre({ width: 200, height: 120, hasSelection: true, selectionBounds: [5, 5, 0, 0] }), { x: 0, y: 0, width: 200, height: 120 }));

// 7. masque : ce que l'écran a posé, 100 / 0 sinon
check("7.1 défaut : densité 100, contour 0", eq(masqueDefaut(undefined), { density: 100, feather: 0 }) && eq(masqueDefaut({ active: true }), { density: 100, feather: 0 }));
check("7.2 valeurs rendues par le moteur", eq(masqueDefaut({ densite: 50, contour: 4 }), { density: 50, feather: 4 }));

// 8. défauts d'effet
check("8.1 sans défaut de l'utilisateur : ceux du dialogue (pas les défauts d'usine du moteur)",
  eq(defautEffet("dropShadow", { params: { distance: 5, angle: 120 }, user: false }), defautsStyle("dropShadow")));
const d = defautEffet("dropShadow", { params: { distance: 12 }, user: true });
check("8.2 défaut de l'utilisateur par-dessus ceux du dialogue", d.distance === 12 && d.size === defautsStyle("dropShadow").size, d);
check("8.3 réponse illisible : ceux du dialogue", eq(defautEffet("stroke", null), defautsStyle("stroke")));

// 9. noms d'historique traduits
for (const n of ["Remove Background", "Relight", "Color to Alpha", "Lock Transparent Pixels", "Unlock Transparent Pixels", "Layer Color",
  "Show Only This Layer", "Edit Layer Mask", "Copy Layer Effects", "Move Layer Effects", "Rasterize Layer Style", "Merge Group",
  "New Frame", "Convert to Layers", "New Artboard", "Duplicate Artboard", "Background From Layer"]) {
  check(`9 « ${n} » a une clé dans ETATS_MOTEUR`, /^photolab\./.test(ETATS_MOTEUR[n] || ""), ETATS_MOTEUR[n]);
}

console.log(`calques-m7 : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
