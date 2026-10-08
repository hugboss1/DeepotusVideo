// qa/peinture.test.mjs — t155 (parité L5) : peinture et retouche, fonctions PURES de mod-peinture.js.
// Commande par outil (conversion d'unités : paint.stroke en 0..1, retouche en 0..100), clic (pot, gomme magique),
// dégradé (Maj = 45°), contrainte de trait (Maj), [ ] / Maj+[ ] et chiffres, garde de la source du tampon.
import {
  OUTILS_PEINTURE, OPTIONS_PEINTURE, defautsPeinture, optionsPeinture, commandeTrait, commandeClic, commandeDegrade,
  contraindreTrait, ligneDepuis, ajouterPointTrait, tailleCran, dureteCran, valeurChiffres, sourceRequise, cibleChiffres,
  altPipette, sourceActive, TAILLE_MIN, TAILLE_MAX,
} from "../js/mod-peinture.js";
import { EMPLACEMENTS } from "../js/mod-outils.js";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// 1. les outils
const ATTENDUS = ["brush", "pencil", "mixerBrush", "eraser", "backgroundEraser", "magicEraser", "cloneStamp", "historyBrush",
  "spotHealing", "healing", "gradient", "paintBucket", "blur", "sharpen", "smudge", "dodge", "burn", "sponge"];
check("1.1 18 outils de peinture et de retouche", eq(Object.keys(OUTILS_PEINTURE).sort(), [...ATTENDUS].sort()), Object.keys(OUTILS_PEINTURE));
const tous = EMPLACEMENTS.flat();
check("1.2 chacun existe dans la barre d'outils", ATTENDUS.every((id) => tous.some((o) => o.id === id)));
check("1.3 la Pièce n'est pas un outil de peinture (absente du moteur 0.3.0)", !("patch" in OUTILS_PEINTURE));
check("1.4 chaque outil a ses options et un défaut pour chacune", ATTENDUS.every((id) => {
  const d = defautsPeinture(id);
  return optionsPeinture(id).length > 0 && optionsPeinture(id).every((o) => d[o.cle] !== undefined);
}));
check("1.5 les défauts sont DANS leurs bornes", ATTENDUS.every((id) => {
  const d = defautsPeinture(id);
  return optionsPeinture(id).filter((o) => o.type === "nombre").every((o) => d[o.cle] >= o.min && d[o.cle] <= o.max);
}));
check("1.6 taille 1..5000 px partout où elle existe", ATTENDUS.every((id) => {
  const t = optionsPeinture(id).find((o) => o.cle === "taille");
  return !t || (t.min === TAILLE_MIN && t.max === TAILLE_MAX && TAILLE_MIN === 1 && TAILLE_MAX === 5000);
}));
check("1.7 defautsPeinture rend une COPIE", defautsPeinture("brush") !== defautsPeinture("brush"));
check("1.8 outil inconnu : aucune option", optionsPeinture("move").length === 0 && eq(defautsPeinture("move"), {}));

// 2. traits : conversion d'unités
const P = [[1, 2], [3, 4]];
const C = { fg: "#112233", bg: "#ffffff" };
const o = (id, extra = {}) => ({ ...defautsPeinture(id), ...extra });
let c = commandeTrait("brush", P, o("brush", { taille: 20, durete: 50, opacite: 40, flux: 70, lissageTrait: 10, fusion: "multiply" }), C);
check("2.1 Pinceau -> paint.stroke, dureté/opacité/flux/lissage en 0..1, couleur de premier plan",
  c.command === "paint.stroke" && eq(c.params, { points: P, size: 20, hardness: 0.5, opacity: 0.4, flow: 0.7, smoothing: 0.1, mode: "multiply", color: "#112233" }), c);
c = commandeTrait("pencil", P, o("pencil", { taille: 3, opacite: 100, effacementAuto: true, fusion: "normal" }), C);
check("2.2 Crayon -> paint.pencil", c.command === "paint.pencil" && eq(c.params, { points: P, size: 3, opacity: 1, mode: "normal", autoErase: true, color: "#112233" }), c);
c = commandeTrait("mixerBrush", P, o("mixerBrush", { taille: 7, humidite: 60, charge: 40, melange: 50, flux: 90, tousCalques: true }), C);
check("2.3 Mélangeur -> paint.mixerBrush, valeurs 0..100", c.command === "paint.mixerBrush"
  && eq(c.params, { points: P, size: 7, wet: 60, load: 40, mix: 50, flow: 90, sampleAllLayers: true, color: "#112233" }), c);
c = commandeTrait("eraser", P, o("eraser", { modeGomme: "pinceau", taille: 9, durete: 100, opacite: 50, flux: 100, lissageTrait: 0, historique: false }), C);
check("2.4 Gomme (pinceau) -> paint.stroke erase, 0..1", c.command === "paint.stroke"
  && eq(c.params, { points: P, size: 9, hardness: 1, opacity: 0.5, flow: 1, smoothing: 0, erase: true }), c);
c = commandeTrait("eraser", P, o("eraser", { modeGomme: "crayon", taille: 4, opacite: 100 }), C);
check("2.5 Gomme (crayon) -> paint.pencil erase", c.command === "paint.pencil" && eq(c.params, { points: P, size: 4, opacity: 1, erase: true }), c);
c = commandeTrait("eraser", P, o("eraser", { taille: 9, durete: 30, opacite: 80, flux: 60, historique: true }), C);
check("2.6 Gomme « d'après l'historique » -> paint.historyBrush, 0..100", c.command === "paint.historyBrush"
  && eq(c.params, { points: P, size: 9, hardness: 30, opacity: 80, flow: 60 }), c);
c = commandeTrait("backgroundEraser", P, o("backgroundEraser", { taille: 9, durete: 50, echantillonnage: "once", limites: "findEdges", tolerance: 40, protegerPremierPlan: true }), C);
check("2.7 Gomme d'arrière-plan -> dureté 0..1, tolérance %", c.command === "paint.backgroundEraser"
  && eq(c.params, { points: P, size: 9, hardness: 0.5, sampling: "once", limits: "findEdges", tolerance: 40, protectForegroundColor: true }), c);
c = commandeTrait("cloneStamp", P, o("cloneStamp", { taille: 21, durete: 0, fusion: "normal", opacite: 90, flux: 80, aligne: false, echantillon: "all" }), C);
check("2.8 Tampon -> 0..100, aligné, échantillon, jamais de source dans le trait", c.command === "paint.cloneStamp"
  && eq(c.params, { points: P, size: 21, hardness: 0, opacity: 90, flow: 80, aligned: false, sampleLayer: "all", mode: "normal" }), c);
c = commandeTrait("healing", P, o("healing", { taille: 19, durete: 100, fusion: "normal", aligne: true, echantillon: "current" }), C);
check("2.9 Correcteur -> paint.healingBrush", c.command === "paint.healingBrush"
  && eq(c.params, { points: P, size: 19, hardness: 100, aligned: true, sampleLayer: "current", mode: "normal" }), c);
c = commandeTrait("spotHealing", P, o("spotHealing", { taille: 19, durete: 100, type: "createTexture" }), C);
check("2.10 Correcteur de tache -> type", c.command === "paint.spotHealing" && eq(c.params, { points: P, size: 19, hardness: 100, type: "createTexture" }), c);
c = commandeTrait("historyBrush", P, o("historyBrush", { taille: 21, durete: 0, opacite: 70, flux: 100 }), C);
check("2.11 Forme d'historique -> 0..100", c.command === "paint.historyBrush" && eq(c.params, { points: P, size: 21, hardness: 0, opacity: 70, flow: 100 }), c);
c = commandeTrait("blur", P, o("blur", { taille: 13, durete: 0, intensite: 50, tousCalques: false }), C);
check("2.12 Goutte -> strength", c.command === "paint.blur" && eq(c.params, { points: P, size: 13, hardness: 0, strength: 50, sampleAllLayers: false }), c);
c = commandeTrait("sharpen", P, o("sharpen", { intensite: 30, protegerDetails: false }), C);
check("2.13 Netteté -> protectDetail", c.command === "paint.sharpen" && c.params.protectDetail === false && c.params.strength === 30, c);
c = commandeTrait("smudge", P, o("smudge", { peintureDoigt: true }), C);
check("2.14 Doigt -> fingerPainting", c.command === "paint.smudge" && c.params.fingerPainting === true && "strength" in c.params, c);
c = commandeTrait("dodge", P, o("dodge", { taille: 65, durete: 0, gamme: "highlights", exposition: 30, protegerTons: false }), C);
check("2.15 Densité − -> paint.dodge", c.command === "paint.dodge"
  && eq(c.params, { points: P, size: 65, hardness: 0, range: "highlights", exposure: 30, protectTones: false }), c);
check("2.16 Densité + -> paint.burn", commandeTrait("burn", P, o("burn"), C).command === "paint.burn");
c = commandeTrait("sponge", P, o("sponge", { taille: 65, durete: 0, modeEponge: "saturate", flux: 50, vibrance: true }), C);
check("2.17 Éponge -> mode, flow, vibrance", c.command === "paint.sponge"
  && eq(c.params, { points: P, size: 65, hardness: 0, mode: "saturate", vibrance: true, flow: 50 }), c);
check("2.18 aucun point -> null", commandeTrait("brush", [], o("brush"), C) === null && commandeTrait("brush", null, o("brush"), C) === null);
check("2.19 outil de clic ou inconnu -> null", commandeTrait("paintBucket", P, o("paintBucket"), C) === null && commandeTrait("move", P, {}, C) === null);
check("2.20 taille arrondie et bornée", commandeTrait("brush", P, o("brush", { taille: 9999.6 }), C).params.size === 5000
  && commandeTrait("brush", P, o("brush", { taille: 0.2 }), C).params.size === 1);

// 3. clics et dégradé
const DOC = { width: 100, height: 50 };
c = commandeClic("paintBucket", 10.7, 20.2, o("paintBucket", { tolerance: 40, opacite: 80, lissage: true, contigu: false }), C, DOC);
check("3.1 Pot -> pixel entier, premier plan", c.command === "paint.bucket"
  && eq(c.params, { x: 10, y: 20, tolerance: 40, contiguous: false, antiAlias: true, contents: "foreground", opacity: 80, color: "#112233" }), c);
c = commandeClic("magicEraser", 3, 4, o("magicEraser", { tolerance: 32, lissage: true, contigu: true, tousCalques: false, opacite: 100 }), C, DOC);
check("3.2 Gomme magique", c.command === "paint.magicEraser"
  && eq(c.params, { x: 3, y: 4, tolerance: 32, antiAlias: true, contiguous: true, sampleAllLayers: false, opacity: 100 }), c);
check("3.3 clic hors du document -> null", commandeClic("paintBucket", -1, 3, o("paintBucket"), C, DOC) === null
  && commandeClic("paintBucket", 100, 3, o("paintBucket"), C, DOC) === null && commandeClic("magicEraser", 3, 50, o("magicEraser"), C, DOC) === null);
check("3.4 clic sans document -> null", commandeClic("paintBucket", 3, 3, o("paintBucket"), C, null) === null);
c = commandeDegrade([0, 0], [10, 3], o("gradient", { style: "radial", fusion: "normal", opacite: 60, inverser: true, tramage: false }), false);
check("3.5 Dégradé -> from/to", c.command === "paint.gradient"
  && eq(c.params, { from: [0, 0], to: [10, 3], style: "radial", mode: "normal", opacity: 60, reverse: true, dither: false }), c);
c = commandeDegrade([0, 0], [10, 3], o("gradient"), true);
check("3.6 Dégradé Maj : calé à 0°", eq(c.params.to, [10, 0]), c.params.to);
c = commandeDegrade([0, 0], [10, 9], o("gradient"), true);
check("3.7 Dégradé Maj : calé à 45°, même longueur projetée", Math.abs(c.params.to[0] - c.params.to[1]) < 1e-9 && c.params.to[0] > 9, c.params.to);
c = commandeDegrade([5, 5], [6, 30], o("gradient"), true);
check("3.8 Dégradé Maj : calé à 90°", c.params.to[0] === 5 && c.params.to[1] > 29, c.params.to);
check("3.9 Dégradé de longueur < 1 px -> null", commandeDegrade([1, 1], [1.5, 1.4], o("gradient"), false) === null);

// 4. gestes
check("4.1 Maj : trait contraint à 0°", eq(contraindreTrait([0, 0], [10, 2]), [[0, 0], [10, 0]]));
check("4.2 Maj : trait contraint à 90°", eq(contraindreTrait([0, 0], [1, -10]), [[0, 0], [0, -10]]));
const d45 = contraindreTrait([0, 0], [10, -9]);
check("4.3 Maj : trait contraint à 45°", Math.abs(d45[1][0] + d45[1][1]) < 1e-9 && d45[1][0] > 9, d45);
check("4.4 Maj-clic : ligne depuis la fin du trait précédent", eq(ligneDepuis([4, 5], [9, 9]), [[4, 5], [9, 9]]) && ligneDepuis(null, [9, 9]) === null);
let pts = ajouterPointTrait([], 1.234, 5.678, 1);
check("4.5 point arrondi au dixième", eq(pts, [[1.2, 5.7]]), pts);
check("4.6 point trop proche (à l'écran) ignoré", ajouterPointTrait(pts, 1.3, 5.7, 1).length === 1);
check("4.7 le zoom compte : 0,5 px document à 400 % = 2 px écran", ajouterPointTrait(pts, 1.7, 5.7, 4).length === 2);
pts = ajouterPointTrait([], 3, 4, 1, 0.42);
check("4.8 stylet : pression en 3e valeur (bornée 0..1)", eq(pts, [[3, 4, 0.42]]) && eq(ajouterPointTrait([], 3, 4, 1, 7), [[3, 4, 1]]), pts);
check("4.9 souris (pression null) : deux valeurs", eq(ajouterPointTrait([], 3, 4, 1, null), [[3, 4]]));

// 5. clavier
check("5.1 ] grossit de 25 %", tailleCran(20, 1) === 25 && tailleCran(100, 1) === 125);
check("5.2 [ réduit de 25 %", tailleCran(25, -1) === 20 && tailleCran(125, -1) === 100);
check("5.3 petites tailles : au moins 1 px de pas", tailleCran(1, 1) === 2 && tailleCran(2, -1) === 1 && tailleCran(3, 1) === 4);
check("5.4 bornes 1..5000", tailleCran(1, -1) === 1 && tailleCran(5000, 1) === 5000 && tailleCran(4500, 1) === 5000);
check("5.5 Maj+] / Maj+[ : dureté ±25, bornée", dureteCran(50, 1) === 75 && dureteCran(90, 1) === 100 && dureteCran(10, -1) === 0 && dureteCran(100, -1) === 75);
let e = valeurChiffres(null, 4, 1000);
check("5.6 un chiffre : 4 -> 40 %", e.valeur === 40, e);
e = valeurChiffres(e.etat, 5, 1500);
check("5.7 deux chiffres en moins de 800 ms : 4 puis 5 -> 45 %", e.valeur === 45, e);
e = valeurChiffres(e.etat, 7, 1700);
check("5.8 un 3e chiffre recommence : 7 -> 70 %", e.valeur === 70, e);
e = valeurChiffres(e.etat, 3, 2600);
check("5.9 après 800 ms : nouveau premier chiffre", e.valeur === 30, e);
check("5.10 0 seul -> 100 %", valeurChiffres(null, 0, 0).valeur === 100);
check("5.11 0 puis 5 -> 5 %", valeurChiffres(valeurChiffres(null, 0, 0).etat, 5, 100).valeur === 5);
check("5.12 1 puis 0 -> 10 %", valeurChiffres(valeurChiffres(null, 1, 0).etat, 0, 100).valeur === 10);
check("5.13 cible des chiffres : opacité ; Maj : flux", cibleChiffres("brush", false) === "opacite" && cibleChiffres("brush", true) === "flux"
  && cibleChiffres("gradient", false) === "opacite" && cibleChiffres("gradient", true) === null && cibleChiffres("dodge", false) === null
  && cibleChiffres("move", false) === null);

// 6. source et Alt
check("6.1 tampon et correcteur exigent une source", sourceRequise("cloneStamp") && sourceRequise("healing") && !sourceRequise("brush") && !sourceRequise("spotHealing"));
check("6.2 Alt = pipette pour pinceau, crayon, dégradé, pot", ["brush", "pencil", "gradient", "paintBucket"].every(altPipette)
  && !altPipette("cloneStamp") && !altPipette("eraser") && !altPipette("dodge"));

// cloneSource.list tel que le moteur le rend (sonde du 08/10) : source active posée ou non
const L0 = { active: 0, sources: [{ index: 0, source: null }, { index: 1, source: [5, 5] }] };
check("6.3 sourceActive : la source ACTIVE compte, pas une autre", !sourceActive(L0) && sourceActive({ ...L0, active: 1 })
  && sourceActive({ active: 0, sources: [{ index: 0, source: [5.0, 5.0] }] }) && !sourceActive(null) && !sourceActive({}));

// 7. les options référencent des valeurs que le moteur accepte
const VALEURS = { fusion: null, echantillon: ["current", "currentAndBelow", "all"], type: ["contentAware", "createTexture", "proximityMatch"],
  gamme: ["shadows", "midtones", "highlights"], modeEponge: ["desaturate", "saturate"], style: ["linear", "radial", "angle", "reflected", "diamond"],
  echantillonnage: ["continuous", "once", "backgroundSwatch"], limites: ["discontiguous", "contiguous", "findEdges"], modeGomme: ["pinceau", "crayon"] };
check("7.1 listes : valeurs du moteur", Object.values(OPTIONS_PEINTURE).flat().filter((x) => x.valeurs && VALEURS[x.cle]).every((x) => eq(x.valeurs, VALEURS[x.cle])),
  Object.values(OPTIONS_PEINTURE).flat().filter((x) => x.valeurs && VALEURS[x.cle] && !eq(x.valeurs, VALEURS[x.cle])).map((x) => x.cle));
check("7.2 libellés photolab.peinture.<cle minuscule>", Object.values(OPTIONS_PEINTURE).flat().every((x) => /^photolab\.peinture\.[a-z_]+$/.test(x.libelle)));

// 8. dictionnaire : chaque libellé d'option (et de valeur), chaque message et chaque texte du panneau Pinceaux existe
// en fr ET en en (clés composées : le banc des textes ne les voit pas dans le source).
const ici = dirname(fileURLToPath(import.meta.url));
const dico = JSON.parse(readFileSync(join(ici, "..", "..", "shared", "i18n", "photolab.json"), "utf8"));
const snk = (s) => s.replace(/[A-Z]/g, (c) => "_" + c.toLowerCase());
const cles = new Set(["photolab.peinture.source_requise", "photolab.peinture.source_definie"]);
for (const x of Object.values(OPTIONS_PEINTURE).flat()) {
  cles.add(x.libelle);
  if (x.valeurs && !x.fusion) for (const v of x.valeurs) cles.add(x.libelle + "." + snk(v));
}
const srcPinceaux = readFileSync(join(ici, "..", "js", "mod-pinceaux.js"), "utf8");
for (const m of srcPinceaux.matchAll(/T\("(photolab\.pinceaux\.[a-z_]+)"/g)) cles.add(m[1]);
for (const m of srcPinceaux.matchAll(/(?:nombre|casePointe|nombreSrc|caseSrc)\("([A-Za-z]+)"/g)) cles.add("photolab.pinceaux." + snk(m[1]));
for (const k of ["photolab.panneau.pinceaux", "photolab.panneau.parametres_pinceau", "photolab.panneau.source_duplication", "photolab.panneau.outils_predefinis"]) cles.add(k);
const manquantes = [...cles].filter((k) => !dico[k] || !dico[k].fr || !dico[k].en);
check("8.1 toutes les clés existent en fr et en en", manquantes.length === 0, manquantes.join(" "));
check("8.2 clés en minuscules (règle de test_i18n_l0)", [...cles].every((k) => /^[a-z0-9_.]+$/.test(k)), [...cles].filter((k) => !/^[a-z0-9_.]+$/.test(k)));

console.log(`peinture : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
