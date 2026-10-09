// qa/champs.test.mjs — champs du registre -> formulaire (t138 B1). Les champs sont RECOPIÉS à la main de la sortie de
// photolab_registre.structurer sur le registre réel (backend/tests/photocraft_commandes_0.3.0.json, 08/10/2026).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  CLES_CACHEES, CLES_FICHIER, D9, OPAQUES, champsVisibles, sansEcran, controleDe, valeurInitiale, coercer, parametres,
  libelleParam, libelleValeur, humaniser, pasDe, estEntier, bornesEffectives, valeursDe, VALEURS_FUSION, BORNES_COLORIZE,
} from "../js/mod-champs.js";
import * as CH from "../js/mod-champs.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");

// ── champs recopiés du registre ──
const GAUSS = [{ cle: "radius", type: "number", min: 0.1, max: 1000, entier: false, optionnel: false, defaut: 1 }];
const BRUIT = [
  { cle: "amount", type: "number", min: 0.1, max: 400, entier: false, optionnel: false, defaut: 12.5 },
  { cle: "distribution", type: "enum", valeurs: ["uniform", "gaussian"], optionnel: false },
  { cle: "monochromatic", type: "bool", optionnel: false },
  { cle: "seed", type: "int", optionnel: false, defaut: 0 },
];
const NIVEAUX = [
  { cle: "inBlack", type: "number", min: 0, max: 253, entier: true, optionnel: false, defaut: 0 },
  { cle: "gamma", type: "number", min: 0.01, max: 9.99, entier: false, optionnel: false, defaut: 1 },
  { cle: "inWhite", type: "number", min: 2, max: 255, entier: true, optionnel: false, defaut: 255 },
  { cle: "outBlack", type: "number", min: 0, max: 255, entier: true, optionnel: false, defaut: 0 },
  { cle: "outWhite", type: "number", min: 0, max: 255, entier: true, optionnel: false, defaut: 255 },
  { cle: "red", type: "json", optionnel: false }, { cle: "green", type: "json", optionnel: false }, { cle: "blue", type: "json", optionnel: false },
];
const OMBRE = [
  { cle: "color", type: "color", formes: ["hex"], optionnel: false },
  { cle: "opacity", type: "number", min: 0, max: 100, entier: true, optionnel: false, defaut: 75 },
  { cle: "blend", type: "str", optionnel: false, defaut: "multiply" },
  { cle: "angle", type: "number", unite: "deg", optionnel: false, defaut: 120 },
  { cle: "useGlobalLight", type: "bool", optionnel: false },
  { cle: "distance", type: "number", unite: "px", optionnel: false, defaut: 5 },
  { cle: "spread", type: "number", min: 0, max: 100, entier: true, optionnel: false },
  { cle: "size", type: "number", unite: "px", optionnel: false, defaut: 5 },
  { cle: "knocksOut", type: "bool", optionnel: false },
  { cle: "add", type: "bool", optionnel: false }, { cle: "layer", type: "layerId", optionnel: false },
];
const GALERIE = [{ cle: "effects", type: "json", optionnel: false }, { cle: "foreground", type: "json", optionnel: false },
  { cle: "background", type: "json", optionnel: false }, { cle: "list", type: "bool", optionnel: false }];
const DEPLACEMENT = [
  { cle: "horizontal", type: "number", min: -999, max: 999, entier: true, optionnel: false, defaut: 10 },
  { cle: "vertical", type: "number", min: -999, max: 999, entier: true, optionnel: false, defaut: 10 },
  { cle: "fit", type: "enum", valeurs: ["stretch", "tile"], optionnel: false },
  { cle: "undefinedAreas", type: "enum", valeurs: ["repeat", "wrap"], optionnel: false },
  { cle: "mapDocument", type: "docIndex", optionnel: false }, { cle: "mapPath", type: "str", optionnel: false },
  { cle: "mapLayer", type: "json", optionnel: false },
];
const OBJECTIF = [
  { cle: "profile", type: "enum", valeurs: ["none", "auto", "generic"], optionnel: false },
  { cle: "focalLength", type: "number", unite: "mm", optionnel: false, defaut: 0 },
  { cle: "correctCA", type: "bool", optionnel: false, defaut: true },
  { cle: "scale", type: "number", min: 50, max: 150, entier: true, optionnel: false, defaut: 100 },
  { cle: "straighten", type: "struct", forme: "[[x,y],[x,y]]", optionnel: true },
];
const ECLAIRAGE = [
  { cle: "lightType", type: "enum", valeurs: ["spot", "point", "infinite"], optionnel: false },
  { cle: "lightX", type: "number", min: 0, max: 1, entier: false, optionnel: false, defaut: 0.25 },
  { cle: "lightZ", type: "number", min: 0, max: 2, entier: true, optionnel: false, defaut: 0.6 },
  { cle: "whiteIsHigh", type: "bool", optionnel: false, defaut: true },
  { cle: "lights", type: "json", optionnel: false },
];
const COURBES = [{ cle: "points", type: "json", optionnel: false }, { cle: "red", type: "json", optionnel: false },
  { cle: "green", type: "json", optionnel: false }, { cle: "blue", type: "json", optionnel: false }];
const REVELER = [{ cle: "layer", type: "layerId", optionnel: true }];
const REMPLIR_COULEUR = { cle: "color", type: "color", formes: ["hex", "rgba"], optionnel: false, defaut: { texte: "foreground" }, note: "contents=color" };
const REMPLIR_MODE = { cle: "mode", type: "enum", valeurs: ["normal", "multiply"], ouverte: true, optionnel: false, defaut: "normal" };
const FILTRE_PHOTO = { cle: "filter", type: "enum", valeurs: ["warming85", "warmingLBA", "cooling80"], optionnel: false };
const CORRESPONDANCE = [{ cle: "source", type: "docIndex", optionnel: false }, { cle: "sourceLayer", type: "json", optionnel: false },
  { cle: "luminance", type: "number", min: 1, max: 200, entier: true, optionnel: false, defaut: 100 }];
const cles = (l) => l.map((c) => c.cle).join();
const TEXTE = { cle: "name", type: "str", optionnel: false, defaut: "abc" };
const ENTIER = { cle: "count", type: "int", optionnel: false };

// 1. champs visibles
check("1.1 flou gaussien : radius", cles(champsVisibles(GAUSS)) === "radius");
check("1.2 bruit : 4 visibles", cles(champsVisibles(BRUIT)) === "amount,distribution,monochromatic,seed");
check("1.3 niveaux : 5 visibles, red/green/blue (json) cachés", cles(champsVisibles(NIVEAUX)) === "inBlack,gamma,inWhite,outBlack,outWhite");
check("1.4 ombre portée : layer et add cachés", cles(champsVisibles(OMBRE)) === "color,opacity,blend,angle,useGlobalLight,distance,spread,size,knocksOut");
check("1.5 enabled caché", champsVisibles([{ cle: "enabled", type: "bool", optionnel: true }]).length === 0);
check("1.6 déplacement : mapPath (fichier) et mapDocument (référence) cachés", cles(champsVisibles(DEPLACEMENT)) === "horizontal,vertical,fit,undefinedAreas");
check("1.7 null / non-tableau -> []", champsVisibles(null).length === 0 && champsVisibles(undefined).length === 0 && champsVisibles({}).length === 0);
check("1.8 constantes", CLES_CACHEES.has("layer") && OPAQUES.has("json") && OPAQUES.has("?") && D9.size === 6);
// CLES_FICHIER est la copie de CLES_CHEMIN du pont (photolab_registre.py) : relue dans le source, toute dérive rougit.
const py = readFileSync(join(racine, "../../backend/app/services/photolab_registre.py"), "utf8");
const mpy = py.match(/CLES_CHEMIN = \{([^}]*)\}/);
const chemPy = mpy ? [...mpy[1].matchAll(/"([^"]+)"/g)].map((x) => x[1]).sort() : [];
check("1.9 CLES_FICHIER == CLES_CHEMIN du pont", chemPy.length > 0 && JSON.stringify(chemPy) === JSON.stringify([...CLES_FICHIER].sort()), JSON.stringify([chemPy, [...CLES_FICHIER]]));

// 2. sans écran (« bientôt »)
for (const id of ["filter.cameraRaw", "filter.liquify", "filter.vanishingPoint", "filter.adaptiveWideAngle", "layer.smartObjects.puppetWarp", "edit.puppetWarp"])
  check("2.1 D9 : " + id, sansEcran(id, GAUSS) === true);
// Sans éditeur : un champ requis que le formulaire ne sait pas montrer (noyau 5×5 de Personnalisé) -> « bientôt », même
// avec des champs. t157 : Convertir pour les filtres dynamiques en est sorti (le panneau Calques montre les filtres).
const PERSO = [{ cle: "kernel", type: "intArray", optionnel: false }, { cle: "scale", type: "number", min: 1, max: 9999, entier: true, optionnel: false, defaut: 1 },
  { cle: "offset", type: "number", min: -9999, max: 9999, entier: true, optionnel: false, defaut: 0 }];
check("2.20 SANS_EDITEUR : Personnalisé seul (t157)",
  CH.SANS_EDITEUR instanceof Set && CH.SANS_EDITEUR.size === 1 && CH.SANS_EDITEUR.has("filter.other.custom"));
check("2.21 Personnalisé (kernel requis, scale/offset visibles) -> bientôt", sansEcran("filter.other.custom", PERSO) === true);
check("2.22 Convertir pour les filtres dynamiques ({layer?} seul) -> s'exécute (t157)",
  sansEcran("filter.convertForSmartFilters", [{ cle: "layer", type: "layerId", optionnel: true }]) === false);
// Le générique n'a toujours rien à montrer pour la galerie : c'est mod-galerie qui l'édite (aiguillage « galerie »).
check("2.2 galerie de filtres : rien d'éditable au générique, effects json requis", sansEcran("filter.filterGallery", GALERIE) === true);
check("2.3 déplacement : mapDocument requis (autre document)", sansEcran("filter.distort.displace", DEPLACEMENT) === true);
check("2.4 correspondance de couleur : source requise (autre document)", sansEcran("image.adjustments.matchColor", CORRESPONDANCE) === true);
check("2.5 flou gaussien : non", sansEcran("filter.blur.gaussianBlur", GAUSS) === false);
check("2.6 correction de l'objectif (straighten optionnel) : non", sansEcran("filter.lensCorrection", OBJECTIF) === false);
check("2.7 effets d'éclairage (lights json, mais 18 réglages visibles) : non", sansEcran("filter.render.lightingEffects", ECLAIRAGE) === false);
check("2.8 révéler tout (layer seul) : non", sansEcran("layer.layerMask.revealAll", REVELER) === false);
check("2.9 courbes vues par le générique : rien d'éditable -> oui", sansEcran("image.adjustments.curves", COURBES) === true);
check("2.10 aucun champ : non", sansEcran("image.adjustments.invert", []) === false && sansEcran("x.y", null) === false);
check("2.11 opaque optionnel seul : non", sansEcran("x.y", [{ cle: "pts", type: "json", optionnel: true }]) === false);
check("2.13 fichier exigé (replaceContents {layer?, path:str}) : oui ; fichier optionnel : non",
  sansEcran("layer.smartObjects.replaceContents", [{ cle: "layer", type: "layerId", optionnel: true }, { cle: "path", type: "str", optionnel: false }]) === true
  && sansEcran("x.y", [{ cle: "file", type: "str", optionnel: true }, { cle: "a", type: "bool", optionnel: false }]) === false);
const LUT = [{ cle: "lut", type: "enum", valeurs: ["none", "warm"], optionnel: false, defaut: "none" }, { cle: "file", type: "str", optionnel: false },
  { cle: "dither", type: "bool", optionnel: false, defaut: false }, { cle: "data", type: "json", optionnel: false }];
check("2.14 colorLookup : file:text « requis » mais lut visible -> non ; file et data cachés", sansEcran("image.adjustments.colorLookup", LUT) === false
  && cles(champsVisibles(LUT)) === "lut,dither");
const REMPLISSAGE = [{ cle: "output", type: "enum", valeurs: ["current", "new", "duplicate"], optionnel: false }, { cle: "seed", type: "int", optionnel: false, defaut: 1 }];
check("2.15 contentAwareFill : output est une énumération (admise par le pont), visible", cles(champsVisibles(REMPLISSAGE)) === "output,seed"
  && sansEcran("edit.contentAwareFill", REMPLISSAGE) === false);
check("2.12 docIndex optionnel ou avec défaut : non", sansEcran("x.y", [{ cle: "d", type: "docIndex", optionnel: true }]) === false
  && sansEcran("x.y", [{ cle: "d", type: "docIndex", optionnel: false, defaut: 0 }]) === false);

// 3. contrôles
check("3.1 nombre borné -> curseur", controleDe(GAUSS[0]) === "curseur");
check("3.2 nombre à unité -> nombre", controleDe(OMBRE[3]) === "nombre");
check("3.3 int -> nombre", controleDe(BRUIT[3]) === "nombre");
check("3.4 enum -> liste (ouverte aussi)", controleDe(BRUIT[1]) === "liste" && controleDe(REMPLIR_MODE) === "liste");
check("3.5 bool -> case", controleDe(BRUIT[2]) === "case");
check("3.6 couleur -> couleur", controleDe(OMBRE[0]) === "couleur");
check("3.7 str -> texte", controleDe(TEXTE) === "texte");
check("3.8 références -> nombre", controleDe({ type: "index" }) === "nombre" && controleDe({ type: "docIndex" }) === "nombre" && controleDe({ type: "layerId" }) === "nombre");
check("3.9 opaques -> aucun", ["json", "struct", "intArray", "union", "?"].every((t) => controleDe({ type: t }) === "aucun"));

// 4. entier effectif
check("4.1 int, entier:true -> entier", estEntier(BRUIT[3]) && estEntier(NIVEAUX[0]));
check("4.2 lightZ 0..2=0.6 : l'indication entier est démentie par le défaut", estEntier(ECLAIRAGE[2]) === false);
check("4.3 fraction 0..1 -> non", estEntier(ECLAIRAGE[1]) === false);

// 5. valeur initiale
check("5.1 défaut du registre", valeurInitiale(GAUSS[0]) === 1 && valeurInitiale(BRUIT[0]) === 12.5);
check("5.2 valeur connue prioritaire (et coercée)", valeurInitiale(GAUSS[0], 4) === 4 && valeurInitiale(GAUSS[0], 5000) === 1000 && valeurInitiale(GAUSS[0], "2,5") === 2.5);
check("5.3 connue null -> défaut", valeurInitiale(GAUSS[0], null) === 1);
check("5.4 curseur sans défaut : 0 borné", valeurInitiale(OMBRE[6]) === 0 && valeurInitiale({ cle: "a", type: "number", min: 1, max: 100, entier: true }) === 1
  && valeurInitiale({ cle: "a", type: "number", min: -10, max: -2, entier: true }) === -2);
check("5.5 bool sans défaut -> false ; défaut true gardé", valeurInitiale(BRUIT[2]) === false && valeurInitiale(OBJECTIF[2]) === true);
check("5.6 enum sans défaut -> 1re valeur ; défaut gardé", valeurInitiale(BRUIT[1]) === "uniform" && valeurInitiale(REMPLIR_MODE) === "normal");
check("5.7 couleur sans défaut -> #000000", valeurInitiale(OMBRE[0]) === "#000000");
check("5.8 défaut en prose {texte} jamais utilisé comme valeur", valeurInitiale(REMPLIR_COULEUR) === "#000000");
check("5.9 str : défaut ou vide", valeurInitiale(OMBRE[2]) === "multiply" && valeurInitiale({ cle: "s", type: "str" }) === "");
check("5.10 nombre à unité sans défaut -> 0", valeurInitiale({ cle: "angle", type: "number", unite: "deg" }) === 0);
check("5.11 lightZ garde 0.6", valeurInitiale(ECLAIRAGE[2]) === 0.6);
check("5.12 enum numérique", valeurInitiale({ cle: "n", type: "enum", valeurs: [1, 2, 4] }) === 1);

// 6. coercition
check("6.1 \"12.7\" -> 12.7", coercer(GAUSS[0], "12.7") === 12.7);
check("6.2 virgule décimale française", coercer(GAUSS[0], "12,7") === 12.7);
check("6.3 5000 -> borné au max", coercer(GAUSS[0], 5000) === 1000);
check("6.4 sous le min -> min", coercer(GAUSS[0], 0) === 0.1 && coercer(GAUSS[0], -3) === 0.1);
check("6.5 NaN / texte / vide / Infinity -> défaut", coercer(GAUSS[0], NaN) === 1 && coercer(GAUSS[0], "abc") === 1 && coercer(GAUSS[0], "") === 1 && coercer(GAUSS[0], Infinity) === 1);
check("6.6 booléen pour un nombre -> défaut", coercer(GAUSS[0], true) === 1);
check("6.7 entier arrondi", coercer(NIVEAUX[0], 12.6) === 13 && coercer(BRUIT[3], "7.4") === 7);
check("6.8 int sans bornes (hors seed) : pas de borne", coercer(ENTIER, 123456) === 123456 && coercer(ENTIER, -5) === -5);
check("6.9 nombre à unité sans bornes : pas de borne, pas d'arrondi", coercer(OMBRE[3], 400.5) === 400.5);
check("6.10 lightZ non arrondi", coercer(ECLAIRAGE[2], 0.6) === 0.6 && coercer(ECLAIRAGE[2], 3) === 2);
check("6.11 bool strict", coercer(BRUIT[2], true) === true && coercer(BRUIT[2], "true") === true && coercer(BRUIT[2], "false") === false
  && coercer(BRUIT[2], 1) === false && coercer(OBJECTIF[2], "oui") === true);
check("6.12 enum : \"zorg\" -> 1re valeur ; défaut si présent", coercer(BRUIT[1], "zorg") === "uniform" && coercer(BRUIT[1], "gaussian") === "gaussian"
  && coercer({ ...BRUIT[1], defaut: "gaussian" }, "zorg") === "gaussian");
check("6.13 enum numérique depuis un <select> (texte)", coercer({ cle: "n", type: "enum", valeurs: [1, 2, 4] }, "4") === 4);
check("6.14 enum ouverte : valeur libre gardée, vide -> défaut", coercer(REMPLIR_MODE, "screen") === "screen" && coercer(REMPLIR_MODE, "") === "normal"
  && coercer(REMPLIR_MODE, "x".repeat(65)) === "normal");
check("6.15 couleur : #ABCDEF -> #abcdef", coercer(OMBRE[0], "#ABCDEF") === "#abcdef");
check("6.16 couleur : sans dièse, courte, tableau", coercer(OMBRE[0], "ff8000") === "#ff8000" && coercer(OMBRE[0], "#F80") === "#ff8800"
  && coercer(OMBRE[0], [255, 128, 0, 255]) === "#ff8000" && coercer(OMBRE[0], [255, 128.4, 0]) === "#ff8000");
check("6.17 couleur illisible -> #000000", coercer(OMBRE[0], "rouge") === "#000000" && coercer(OMBRE[0], [300, 0, 0]) === "#000000" && coercer(REMPLIR_COULEUR, null) === "#000000");
check("6.18 str : borne 256", coercer(TEXTE, "y".repeat(300)).length === 256 && coercer(TEXTE, 5) === "5" && coercer(TEXTE, null) === "abc" && coercer({ cle: "s", type: "str" }, null) === "");
check("6.19 références : entier >= 0", coercer({ type: "index" }, "3") === 3 && coercer({ type: "docIndex" }, -1) === 0 && coercer({ type: "layerId" }, "x") === 0);

// 7. paramètres à envoyer
const pb = parametres(BRUIT, { amount: "20", distribution: "gaussian", monochromatic: true, seed: 3.2 });
check("7.1 bruit : coercés", JSON.stringify(pb) === JSON.stringify({ amount: 20, distribution: "gaussian", monochromatic: true, seed: 3 }), JSON.stringify(pb));
const po = parametres(OMBRE, { layer: 7, add: true, enabled: false, color: "#FF0000", opacity: 50 });
check("7.2 jamais de clé cachée", !("layer" in po) && !("add" in po) && !("enabled" in po) && po.color === "#ff0000" && po.opacity === 50, JSON.stringify(po));
const pn = parametres(NIVEAUX, { gamma: 1.2, red: [0, 1, 255, 0, 255] });
check("7.3 jamais d'opaque", JSON.stringify(pn) === JSON.stringify({ gamma: 1.2 }), JSON.stringify(pn));
check("7.4 clé absente des valeurs -> omise (défaut du moteur)", JSON.stringify(parametres(GAUSS, {})) === "{}" && JSON.stringify(parametres(GAUSS, null)) === "{}");
check("7.5 texte vide omis ; blend vide -> défaut du registre", !("name" in parametres([TEXTE], { name: "" })) && parametres(OMBRE, { blend: "" }).blend === "multiply" && parametres(OMBRE, { blend: "screen" }).blend === "screen");
check("7.6 jamais de clé fichier", JSON.stringify(parametres(DEPLACEMENT, { mapPath: "m.psd", mapDocument: 1, fit: "tile" })) === JSON.stringify({ fit: "tile" }));
check("7.7 clé inconnue du registre ignorée", JSON.stringify(parametres(GAUSS, { radius: 2, zorglub: 1 })) === JSON.stringify({ radius: 2 }));

// 8. libellés
const tr = (c) => ({ "photolab.param.radius": "Rayon", "photolab.valeur.gaussian": "Gaussienne" }[c] || c);
check("8.1 libelleParam traduit", libelleParam("radius", tr) === "Rayon");
check("8.2 libelleParam : repli humanisé", libelleParam("blurAngle", tr) === "Blur angle");
check("8.3 sans traducteur", libelleParam("blurAngle") === "Blur angle");
check("8.4 traducteur qui rend vide -> repli", libelleParam("radius", () => "") === "Radius");
check("8.5 libelleValeur", libelleValeur("gaussian", tr) === "Gaussienne" && libelleValeur("tealOrange", tr) === "Teal orange" && libelleValeur(4, tr) === "4");
check("8.6 humaniser blurAngle / cooling80", humaniser("blurAngle") === "Blur angle" && humaniser("cooling80") === "Cooling80");
check("8.7 humaniser : acronymes gardés", humaniser("warmingLBA") === "Warming LBA" && humaniser("correctCA") === "Correct CA" && humaniser("HDRToning") === "HDR toning");
check("8.8 humaniser : lettre seule en capitale", humaniser("lightX") === "Light X" && humaniser("x") === "X");
check("8.9 humaniser : mots, soulignés, vide", humaniser("useGlobalLight") === "Use global light" && humaniser("under_score") === "Under score"
  && humaniser("") === "" && humaniser(null) === "");

// 9. pas du curseur
check("9.1 0..1 -> 0.01", pasDe(ECLAIRAGE[1]) === 0.01);
check("9.2 0.1..1000 -> 0.1", pasDe(GAUSS[0]) === 0.1);
check("9.3 0..255 entier -> 1", pasDe(NIVEAUX[3]) === 1);
check("9.4 gamma 0.01..9.99 -> 0.01", pasDe(NIVEAUX[1]) === 0.01);
check("9.5 lightZ 0..2=0.6 -> 0.01", pasDe(ECLAIRAGE[2]) === 0.01);
check("9.6 0.5..3 (décimales) -> 0.1", pasDe({ type: "number", min: 0.5, max: 3, entier: false, defaut: 1 }) === 0.1);
check("9.7 non entier, écart <= 20 -> 0.1 ; sinon 1", pasDe({ type: "number", min: 0, max: 10, entier: false }) === 0.1
  && pasDe({ type: "number", min: 0, max: 400, entier: false }) === 1);
check("9.8 unité sans bornes : 1, ou les décimales du défaut, ev -> 0.01", pasDe(OMBRE[3]) === 1
  && pasDe({ type: "number", unite: "px", defaut: 0.5 }) === 0.1 && pasDe({ type: "number", unite: "ev" }) === 0.01);
check("9.9 int -> 1", pasDe(BRUIT[3]) === 1);

// 11. modes de fusion (relecture B1) : `blend` -> liste des 27 modes, quel que soit le type du registre
const BLEND_STR = OMBRE[2];                                                                   // str="multiply"
const BLEND_STR_SANS = { cle: "blend", type: "str", optionnel: false };                       // stroke : str sans défaut
const BLEND_OUVERT = { cle: "blend", type: "enum", valeurs: ["Multiply"], ouverte: true, optionnel: true };   // layer.setProps
check("11.1 27 modes, sans passThrough", VALEURS_FUSION.length === 27 && !VALEURS_FUSION.includes("passThrough") && VALEURS_FUSION[0] === "normal");
check("11.2 controleDe -> liste (str et enum ouverte)", controleDe(BLEND_STR) === "liste" && controleDe(BLEND_OUVERT) === "liste" && controleDe(BLEND_STR_SANS) === "liste");
check("11.3 valeursDe -> les 27 modes ; sinon les valeurs du registre", valeursDe(BLEND_OUVERT).join() === VALEURS_FUSION.join() && valeursDe(BRUIT[1]).join() === "uniform,gaussian" && valeursDe(OMBRE[0]).length === 0);
check("11.4 un mode connu passe (id, libellé moteur, casse)", coercer(BLEND_STR, "screen") === "screen" && coercer(BLEND_OUVERT, "Multiply") === "multiply"
  && coercer(BLEND_STR, "Linear Dodge (Add)") === "linearDodge" && coercer(BLEND_STR, "COLOR_BURN") === "colorBurn");
check("11.5 hors liste -> défaut du registre s'il est un mode", coercer(BLEND_STR, "zorg") === "multiply" && coercer(BLEND_STR, 3) === "multiply" && coercer(BLEND_STR, "") === "multiply");
check("11.6 hors liste sans défaut -> normal", coercer(BLEND_STR_SANS, "zorg") === "normal" && coercer(BLEND_OUVERT, "add") === "normal");
check("11.7 passThrough refusé (groupes seulement)", coercer(BLEND_STR, "passThrough") === "multiply" && coercer(BLEND_STR_SANS, "Pass Through") === "normal");
check("11.8 défaut du registre qui n'est pas un mode -> normal", coercer({ cle: "blend", type: "str", defaut: "zorg" }, null) === "normal");
check("11.9 valeurInitiale", valeurInitiale(BLEND_STR) === "multiply" && valeurInitiale(BLEND_STR_SANS) === "normal" && valeurInitiale(BLEND_OUVERT, "Screen") === "screen");
check("11.10 parametres : blend toujours un mode", parametres([BLEND_STR_SANS], { blend: "zorg" }).blend === "normal");

// 12. colorisation de Teinte/Saturation (relecture B1) : mêmes bornes que BORNES_COLORIZE du pont
const TS = [
  { cle: "hue", type: "number", min: -180, max: 180, entier: true, optionnel: false, defaut: 0 },
  { cle: "saturation", type: "number", min: -100, max: 100, entier: true, optionnel: false, defaut: 0 },
  { cle: "lightness", type: "number", min: -100, max: 100, entier: true, optionnel: false, defaut: 0 },
  { cle: "colorize", type: "bool", optionnel: false, defaut: false },
  { cle: "reds", type: "json", optionnel: false },
];
const pyReg = py.match(/BORNES_COLORIZE = \{"hue": \((\d+), (\d+)\), "saturation": \((\d+), (\d+)\)\}/);
check("12.1 BORNES_COLORIZE == celles du pont", !!pyReg && JSON.stringify(BORNES_COLORIZE) === JSON.stringify({ hue: [+pyReg[1], +pyReg[2]], saturation: [+pyReg[3], +pyReg[4]] }));
check("12.2 bornesEffectives hors colorisation", JSON.stringify(bornesEffectives(TS[0], { colorize: false })) === '{"min":-180,"max":180}' && JSON.stringify(bornesEffectives(TS[0], {})) === '{"min":-180,"max":180}');
check("12.3 bornesEffectives en colorisation", JSON.stringify(bornesEffectives(TS[0], { colorize: true })) === '{"min":0,"max":360}'
  && JSON.stringify(bornesEffectives(TS[1], { colorize: "true" })) === '{"min":0,"max":100}');
check("12.4 lightness inchangée en colorisation", JSON.stringify(bornesEffectives(TS[2], { colorize: true })) === '{"min":-100,"max":100}');
const tsC = parametres(TS, { hue: 300, saturation: -50, lightness: 20, colorize: true });
check("12.5 parametres en colorisation : hue 300 gardée, saturation ramenée à 0", JSON.stringify(tsC) === JSON.stringify({ hue: 300, saturation: 0, lightness: 20, colorize: true }), JSON.stringify(tsC));
const tsN = parametres(TS, { hue: 300, saturation: -50, colorize: false });
check("12.6 parametres hors colorisation : hue 300 -> 180", tsN.hue === 180 && tsN.saturation === -50, JSON.stringify(tsN));
check("12.7 colorize en texte (case du formulaire)", parametres(TS, { hue: 300, colorize: "true" }).hue === 300);
check("12.8 coercer avec les valeurs", coercer(TS[0], 400, { colorize: true }) === 360 && coercer(TS[0], -20, { colorize: true }) === 0 && coercer(TS[0], 400) === 180);
check("12.9 pasDe suit les bornes effectives", pasDe(TS[0], { colorize: true }) === 1 && pasDe({ cle: "hue", type: "number", min: -1, max: 1, entier: false }) === 0.01
  && pasDe({ cle: "hue", type: "number", min: -1, max: 1, entier: false }, { colorize: true }) === 1);
check("12.10 valeurInitiale en colorisation", valeurInitiale(TS[1], -40, { colorize: true }) === 0 && valeurInitiale(TS[1], -40) === -40);

// 13. seed (u32/u64 au registre, `int` dans le champ) -> ≥ 0 par son nom
const GRAINE = BRUIT[3];
check("13.1 bornesEffectives(seed) = {min:0}", JSON.stringify(bornesEffectives(GRAINE)) === '{"min":0}');
check("13.2 seed négatif -> 0 ; grand gardé", coercer(GRAINE, -1e9) === 0 && coercer(GRAINE, 1e9) === 1e9 && coercer(GRAINE, "3,7") === 4);
check("13.3 seed borné du registre (s'il l'était) prioritaire", JSON.stringify(bornesEffectives({ cle: "seed", type: "number", min: 1, max: 9 })) === '{"min":1,"max":9}');

// 14. fichier requis : grise même avec des champs visibles (relecture B1)
const EXPORTER = [{ cle: "layer", type: "layerId", optionnel: true }, { cle: "path", type: "str", optionnel: false },
  { cle: "scale", type: "number", min: 1, max: 1000, entier: true, optionnel: false, defaut: 100 }];
check("14.1 layer.exportAs (scale visible, path requis) -> bientôt", sansEcran("layer.exportAs", EXPORTER) === true);
const FLAMME = [{ cle: "length", type: "number", min: 1, max: 1000, entier: true, optionnel: false, defaut: 150 }, { cle: "path", type: "str", optionnel: false }];
check("14.2 filter.render.flame (path = tracé) -> bientôt", sansEcran("filter.render.flame", FLAMME) === true);
const FORME = [{ cle: "kind", type: "enum", valeurs: ["rect", "path"], optionnel: false, defaut: "rect" }, { cle: "path", type: "struct", forme: "{…}", optionnel: false }];
check("14.3 shape.create (path opaque requis) -> bientôt", sansEcran("shape.create", FORME) === true);
check("14.4 path optionnel -> non", sansEcran("x.y", [{ cle: "path", type: "str", optionnel: true }, EXPORTER[2]]) === false);
check("14.5 output énumération (contentAwareFill) -> hors règle", sansEcran("edit.contentAwareFill", REMPLISSAGE) === false);
check("14.6 colorLookup file/data -> hors règle", sansEcran("image.adjustments.colorLookup", LUT) === false);
check("14.7 input opaque requis -> bientôt", sansEcran("file.automate.batch", [{ cle: "input", type: "union", optionnel: false }, { cle: "x", type: "bool", optionnel: false }]) === true);

// 10. module sans texte français en dur
const src = readFileSync(join(racine, "js/mod-champs.js"), "utf8");
check("10.1 pas de texte français accentué hors commentaires", !/[éèêàùçô]/i.test(src.replace(/\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "")));

console.log(`champs : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
