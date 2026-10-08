// qa/reglages.test.mjs — calques de réglage (t138 B5) : KINDS, kindDe, depuisInspect (sur les 21 cas de la fixture
// relevée sur le VRAI moteur par backend/tests/test_photolab_reglages_moteur.py), difference, vues des éditeurs sur
// mesure (gammes, tons, couches de sortie, dégradé). Fonctions PURES.
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { KINDS, kindDe, infoKind, depuisInspect, difference, egalProfond, avecValeur, lireChemin, sorteEditeur,
  vueReglage, appliquer, valeursVue, signatureVue, GAMMES_TEINTE, BORNES_GAMMES, TONS, GAMMES_SELECTIVE, LIGNES_MIXEUR,
  DEGRADE_DEFAUT, lutsDepuisReponse } from "../js/mod-reglages.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, typeof detail === "string" ? detail : JSON.stringify(detail)); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const dico = JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8"));
const fixture = JSON.parse(readFileSync(join(racine, "qa/fixtures/reglages-inspect.json"), "utf8"));
const menus = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));
const json = (x) => JSON.stringify(x);

// Champs du registre (forme de photolab_registre.structurer) des seuls réglages dont les vues ont besoin, recopiés du
// registre réel 0.3.0 : le banc reste hors ligne et sans Python. Le registre COMPLET est rejoué par
// backend/tests/test_photolab_formulaires.py section [5] (qa/outils/reglages.mjs).
const CH = {
  hueSaturation: [
    { cle: "hue", type: "number", min: -180, max: 180, entier: true, defaut: 0 },
    { cle: "saturation", type: "number", min: -100, max: 100, entier: true, defaut: 0 },
    { cle: "lightness", type: "number", min: -100, max: 100, entier: true, defaut: 0 },
    { cle: "colorize", type: "bool", defaut: false },
    ...GAMMES_TEINTE.map((g) => ({ cle: g, type: "json" })),
  ],
  colorBalance: [{ cle: "shadows", type: "json" }, { cle: "midtones", type: "json" }, { cle: "highlights", type: "json" }, { cle: "preserveLuminosity", type: "bool", defaut: true }],
  channelMixer: [{ cle: "red", type: "json" }, { cle: "green", type: "json" }, { cle: "blue", type: "json" }, { cle: "gray", type: "json" }, { cle: "monochrome", type: "bool", defaut: false }],
  selectiveColor: [{ cle: "method", type: "enum", valeurs: ["relative", "absolute"], defaut: "relative" },
    { cle: "colors", type: "enum", valeurs: GAMMES_SELECTIVE.slice(), defaut: "reds" },
    ...["cyan", "magenta", "yellow", "black"].map((cle) => ({ cle, type: "number", min: -100, max: 100, entier: true, defaut: 0 })), { cle: "reds", type: "json" }],
  gradientMap: [{ cle: "stops", type: "json" }, { cle: "reverse", type: "bool", defaut: false }, { cle: "dither", type: "bool", defaut: false }],
  colorLookup: [{ cle: "lut", type: "enum", valeurs: ["none", "warm", "cool"], defaut: "none" }, { cle: "file", type: "str" },
    { cle: "interpolation", type: "enum", valeurs: ["trilinear", "tetrahedral"], defaut: "trilinear" }, { cle: "dither", type: "bool", defaut: false }, { cle: "data", type: "json" }],
};

// 1. les 16 kinds
const kindsCatalogue = menus.entrees.map((e) => e.id || "").filter((i) => i.startsWith("layer.newAdjustmentLayer.")).map((i) => i.slice(25));
check("1.1 16 kinds dans l'ordre du catalogue de photocraft", KINDS.map((k) => k.kind).join() === kindsCatalogue.join(), KINDS.map((k) => k.kind).join());
check("1.2 variantes = noms de doc.inspect", KINDS.map((k) => k.variante).join() === "BrightnessContrast,Levels,Curves,Exposure,Vibrance,HueSaturation,ColorBalance,BlackWhite,PhotoFilter,ChannelMixer,ColorLookup,Invert,Posterize,Threshold,GradientMap,SelectiveColor");
check("1.3 clé photolab.kind.<kind en minuscules>, fr et en", KINDS.every((k) => k.cle === "photolab.kind." + k.kind.toLowerCase() && dico[k.cle] && dico[k.cle].fr && dico[k.cle].en));
check("1.4 chaque icône existe dans icones/ (Lucide, aucune copie nouvelle)", KINDS.every((k) => existsSync(join(racine, "icones", k.icone + ".svg"))), KINDS.filter((k) => !existsSync(join(racine, "icones", k.icone + ".svg"))).map((k) => k.icone));
check("1.5 infoKind", infoKind("curves").variante === "Curves" && infoKind("zorg") === null);

// 2. kindDe
check("2.1 objet { Curves: … }", kindDe({ kind: "Adjustment", adjustment: { Curves: {} } }) === "curves");
check("2.2 chaîne \"Invert\"", kindDe({ kind: "Adjustment", adjustment: "Invert" }) === "invert");
check("2.3 calque de pixels", kindDe({ kind: "Pixel" }) === null && kindDe(null) === null && kindDe({}) === null);
check("2.4 variante inconnue", kindDe({ kind: "Adjustment", adjustment: { Zorg: {} } }) === null && kindDe({ adjustment: "Zorg" }) === null);
check("2.5 les 21 cas de la fixture", Object.values(fixture).every((f) => kindDe({ adjustment: f.adjustment }) === f.kind));

// 3. depuisInspect sur les 21 cas : égal à `envoye` à l'arrondi près (1 sur 0..255, 0,01 sur gamma et les flottants,
//    exact pour bool / énumérations / couleurs), toute clé en plus vaut le défaut du moteur.
const DEFAUTS = {
  brightnessContrast: { brightness: 0, contrast: 0, legacy: false },
  levels: { inBlack: 0, gamma: 1, inWhite: 255, outBlack: 0, outWhite: 255 },
  curves: { points: [[0, 0], [255, 255]] },
  exposure: { exposure: 0, offset: 0, gamma: 1 },
  vibrance: { vibrance: 0, saturation: 0 },
  hueSaturation: { hue: 0, saturation: 0, lightness: 0, colorize: false,
    ...Object.fromEntries(GAMMES_TEINTE.map((g) => [g, { hue: 0, saturation: 0, lightness: 0, range: BORNES_GAMMES[g] }])) },
  colorBalance: { shadows: [0, 0, 0], midtones: [0, 0, 0], highlights: [0, 0, 0], preserveLuminosity: true },
  blackWhite: { reds: 40, yellows: 60, greens: 40, cyans: 60, blues: 20, magentas: 80, tint: false },
  photoFilter: { density: 25, preserveLuminosity: true },
  channelMixer: { monochrome: false, red: [100, 0, 0, 0], green: [0, 100, 0, 0], blue: [0, 0, 100, 0] },
  invert: {},
  posterize: { levels: 4 },
  threshold: { level: 128 },
  gradientMap: { reverse: false, dither: false },
  selectiveColor: { method: "relative", ...Object.fromEntries(GAMMES_SELECTIVE.map((g) => [g, [0, 0, 0, 0]])) },
  colorLookup: { lut: "none", interpolation: "trilinear", dither: false },
};
function proche(attendu, obtenu, cle) {
  if (typeof attendu === "number") {
    const tol = cle === "gamma" || !Number.isInteger(attendu) ? 0.01 : 1;
    return typeof obtenu === "number" && Math.abs(attendu - obtenu) <= tol + 1e-9;
  }
  if (Array.isArray(attendu)) return Array.isArray(obtenu) && obtenu.length === attendu.length && attendu.every((x, i) => proche(x, obtenu[i], cle));
  if (attendu && typeof attendu === "object") return !!obtenu && typeof obtenu === "object" && Object.keys(attendu).every((k) => proche(attendu[k], obtenu[k], k));
  return attendu === obtenu;
}
const IDENTITE = [[0, 0], [255, 255]];
for (const [nom, f] of Object.entries(fixture)) {
  const r = depuisInspect(f.kind, f.adjustment, f.lut_list);
  const att = JSON.parse(JSON.stringify(f.envoye));
  const absents = [], exemptes = [];
  // préréglage PERDU par le moteur : l'écran garde la couleur qu'il a posée (vérifiée en 3.4)
  if (f.kind === "photoFilter") { delete att.filter; exemptes.push("color"); }
  if (f.kind === "selectiveColor" && att.colors) {                         // forme plate -> la gamme visée en tableau
    att[att.colors] = [att.cyan || 0, att.magenta || 0, att.yellow || 0, att.black || 0];
    for (const k of ["colors", "cyan", "magenta", "yellow", "black"]) delete att[k];
  }
  if (f.kind === "curves") for (const k of ["red", "green", "blue"]) if (json(att[k]) === json(IDENTITE)) { delete att[k]; absents.push(k); }
  if (f.kind === "levels") for (const k of ["red", "green", "blue"]) if (att[k]) att[k] = { ...DEFAUTS.levels, ...att[k] };
  check("3 " + nom + " : envoye retrouvé", proche(att, r, ""), { attendu: att, obtenu: r });
  check("3 " + nom + " : canal identité absent", absents.every((k) => !(k in r)), r);
  const extras = Object.keys(r).filter((k) => !(k in att) && !exemptes.includes(k));
  const mauvais = extras.filter((k) => !(k in DEFAUTS[f.kind]) || !proche(DEFAUTS[f.kind][k], r[k], k));
  check("3 " + nom + " : toute autre clé vaut le défaut du moteur", !mauvais.length, mauvais.map((k) => k + "=" + json(r[k])));
}
check("3.1 21 cas (16 base + 5 pièges)", Object.keys(fixture).length === 21 && Object.keys(fixture).filter((k) => k.endsWith("/base")).length === 16);
const fx = (k) => depuisInspect(fixture[k].kind, fixture[k].adjustment, fixture[k].lut_list);
check("3.2 f32 arrondis (1.2999999523 -> 1.3, -0.0199999996 -> -0.02)", fx("levels/base").gamma === 1.3 && fx("exposure/base").offset === -0.02 && fx("exposure/base").gamma === 1.2);
check("3.3 niveaux : canaux neutres absents", !("green" in fx("levels/base")) && !("blue" in fx("levels/base")) && fx("levels/base").red.inBlack === 10);
check("3.4 photoFilter : couleur gardée, préréglage absent", fx("photoFilter/base").color === "#006dff" && !("filter" in fx("photoFilter/base")) && fx("photoFilter/base").density === 40);
check("3.5 noir et blanc sans teinte : tint faux, aucune tintColor", fx("blackWhite/sans-teinte").tint === false && !("tintColor" in fx("blackWhite/sans-teinte")));
check("3.6 noir et blanc teinté : #c08040", fx("blackWhite/base").tint === true && fx("blackWhite/base").tintColor === "#c08040");
check("3.7 mélangeur monochrome : gray + monochrome, jamais red", json(fx("channelMixer/monochrome").gray) === "[30,60,10,5]" && fx("channelMixer/monochrome").monochrome === true && !("red" in fx("channelMixer/monochrome")));
check("3.8 inverser : {}", json(fx("invert/base")) === "{}");
check("3.9 LUT retrouvée par son libellé ; sans LUT : none", fx("colorLookup/base").lut === "warm" && fx("colorLookup/none").lut === "none");
check("3.10 LUT inconnue ou liste pas encore chargée : lut absent (jamais une valeur inventée)",
  !("lut" in depuisInspect("colorLookup", fixture["colorLookup/base"].adjustment, null)) && !("lut" in depuisInspect("colorLookup", { ColorLookup: { name: "Zorg" } }, fixture["colorLookup/base"].lut_list)));
check("3.11 couleur sélective : les 9 gammes en tableaux [c,m,y,k], méthode absolue", GAMMES_SELECTIVE.every((g) => Array.isArray(fx("selectiveColor/base")[g]) && fx("selectiveColor/base")[g].length === 4) && fx("selectiveColor/base").method === "absolute");
check("3.12 teinte/saturation : 6 gammes, range = bornes du moteur", GAMMES_TEINTE.every((g) => json(fx("hueSaturation/base")[g].range) === json(fixture["hueSaturation/base"].adjustment.HueSaturation.ranges[GAMMES_TEINTE.indexOf(g)].bounds)));
check("3.13 dégradé : [[pos, \"#rrggbb\"]]", json(fx("gradientMap/base").stops) === json([[0, "#101030"], [0.4, "#c04020"], [1, "#fff0b0"]]), fx("gradientMap/base").stops);
check("3.14 seuil 0..1 -> 0..255", fx("threshold/base").level === 100);
check("3.15 état illisible -> {} (jamais d'exception)", json(depuisInspect("curves", null, null)) === "{}" && json(depuisInspect("levels", "Invert", null)) === "{}" && json(depuisInspect("zorg", {}, null)) === "{}");
check("3.16 courbes : points entiers strictement croissants", fx("curves/base").points.every((p, i, a) => Number.isInteger(p[0]) && Number.isInteger(p[1]) && (!i || p[0] > a[i - 1][0])));

// 4. difference : ce qu'envoie layer.setAdjustment (le moteur FUSIONNE)
check("4.1 rien de changé -> {}", json(difference({ a: 1, b: [1, 2], c: { x: 1 } }, { a: 1, b: [1, 2], c: { x: 1 } })) === "{}");
check("4.2 seules les clés changées", json(difference({ a: 1, b: 2 }, { a: 1, b: 3 })) === json({ b: 3 }));
check("4.3 profonde : tableau ou objet changé envoyé entier", json(difference({ m: [0, 0, 20], r: { hue: 1, range: [1, 2, 3, 4] } }, { m: [5, 0, 20], r: { hue: 1, range: [1, 2, 3, 4] } })) === json({ m: [5, 0, 20] })
  && json(difference({ r: { hue: 1, range: [1, 2, 3, 4] } }, { r: { hue: 2, range: [1, 2, 3, 4] } })) === json({ r: { hue: 2, range: [1, 2, 3, 4] } }));
check("4.4 clé nouvelle envoyée ; clé disparue ignorée (le moteur la garde)", json(difference({ a: 1 }, { b: 2 })) === json({ b: 2 }));
check("4.5 ordre des clés indifférent", json(difference({ r: { a: 1, b: 2 } }, { r: { b: 2, a: 1 } })) === "{}" && egalProfond({ a: 1, b: 2 }, { b: 2, a: 1 }) && !egalProfond([1, 2], [2, 1]));
check("4.6 entrées absurdes", json(difference(null, { a: 1 })) === json({ a: 1 }) && json(difference({ a: 1 }, null)) === "{}");

// 5. avecValeur / lireChemin : immuables, conteneur absent créé depuis son défaut
const e0 = { midtones: [0, 0, 20], x: 1 };
const e1 = avecValeur(e0, ["midtones", 0], 30);
check("5.1 immuable", json(e0.midtones) === "[0,0,20]" && json(e1.midtones) === "[30,0,20]" && e1.x === 1 && e1 !== e0);
check("5.2 conteneur absent -> défaut", json(avecValeur({}, ["shadows", 2], 7, [0, 0, 0]).shadows) === "[0,0,7]");
check("5.3 objet", json(avecValeur({}, ["reds", "hue"], 5, { hue: 0, saturation: 0, lightness: 0 }).reds) === json({ hue: 5, saturation: 0, lightness: 0 }));
check("5.4 trois niveaux (couleur d'un arrêt de dégradé)", json(avecValeur({ stops: [[0, "#000000"], [1, "#ffffff"]] }, ["stops", 1, 1], "#ff0000").stops) === json([[0, "#000000"], [1, "#ff0000"]]));
check("5.5 lireChemin", lireChemin({ a: [1, { b: 2 }] }, ["a", 1, "b"]) === 2 && lireChemin({}, ["a", 0]) === undefined);

// 6. sortes d'éditeurs
check("6.1 Courbes / Niveaux : éditeur de B4", sorteEditeur("curves") === "ton" && sorteEditeur("levels") === "ton");
check("6.2 Inverser : aucun paramètre", sorteEditeur("invert") === "aucun");
check("6.3 sur mesure : teinte, balance, mélangeur, sélective, dégradé",
  ["hueSaturation", "colorBalance", "channelMixer", "selectiveColor", "gradientMap"].every((k) => sorteEditeur(k) === "surmesure"));
check("6.4 les autres : formulaire généré", ["brightnessContrast", "exposure", "vibrance", "blackWhite", "photoFilter", "colorLookup", "posterize", "threshold"].every((k) => sorteEditeur(k) === "formulaire"));

// 7. vues sur mesure
const etHS = fx("hueSaturation/base");
const vM = vueReglage("hueSaturation", etHS, "master", CH.hueSaturation);
check("7.1 teinte : sélecteur Global + 6 gammes", vM.selecteur && json(vM.selecteur.options.map((o) => o.valeur)) === json(["master", ...GAMMES_TEINTE]) && vM.selecteur.valeur === "master");
check("7.2 teinte Global : hue/saturation/lightness du registre + colorize", json(vM.champs.map((e) => e.c.cle)) === json(["hue", "saturation", "lightness", "colorize"]) && json(vM.champs[0].chemin) === json(["hue"]));
const vR = vueReglage("hueSaturation", etHS, "reds", CH.hueSaturation);
check("7.3 teinte Rouges : chemins sous reds", json(vR.champs.slice(0, 3).map((e) => e.chemin)) === json([["reds", "hue"], ["reds", "saturation"], ["reds", "lightness"]]));
const apHS = appliquer(etHS, vR.champs[0], "40", valeursVue(vR, etHS));
check("7.4 teinte Rouges hue 40 -> difference = reds entier, range conservé", json(difference(etHS, apHS)) === json({ reds: { ...etHS.reds, hue: 40 } }) && json(difference(etHS, apHS).reds.range) === "[-45,-15,15,45]");
check("7.5 colorisation : pas de sélecteur de gamme, bornes 0..360", vueReglage("hueSaturation", fx("hueSaturation/colorize"), "reds", CH.hueSaturation).selecteur === null
  && appliquer(fx("hueSaturation/colorize"), vueReglage("hueSaturation", fx("hueSaturation/colorize"), "reds", CH.hueSaturation).champs[0], 300, valeursVue(vueReglage("hueSaturation", fx("hueSaturation/colorize"), "reds", CH.hueSaturation), fx("hueSaturation/colorize"))).hue === 300);
const etCB = fx("colorBalance/base");
const vCB = vueReglage("colorBalance", etCB, "midtones", CH.colorBalance);
check("7.6 balance : tons Ombres / Tons moyens / Tons clairs, 3 curseurs -100..100 + préserver", json(vCB.selecteur.options.map((o) => o.valeur)) === json(TONS)
  && vCB.champs.length === 4 && vCB.champs.slice(0, 3).every((e) => e.c.min === -100 && e.c.max === 100 && e.c.cleLibelle) && vCB.champs[3].c.cle === "preserveLuminosity");
check("7.7 balance : Cyan–Rouge des tons moyens à 150 -> borné, tableau [3] entier", json(difference(etCB, appliquer(etCB, vCB.champs[0], 150, valeursVue(vCB, etCB)))) === json({ midtones: [100, 0, 20] }));
const etMX = fx("channelMixer/base");
const vMX = vueReglage("channelMixer", etMX, "green", CH.channelMixer);
check("7.8 mélangeur : sortie Rouge/Vert/Bleu, 4 curseurs -200..200 + monochrome", json(vMX.selecteur.options.map((o) => o.valeur)) === json(["red", "green", "blue"])
  && vMX.champs.length === 5 && vMX.champs.slice(0, 4).every((e) => e.c.min === -200 && e.c.max === 200) && json(vMX.champs[3].chemin) === json(["green", 3]));
check("7.9 mélangeur : constante de Vert à -250 -> [5,90,5,-200]", json(difference(etMX, appliquer(etMX, vMX.champs[3], -250, valeursVue(vMX, etMX)))) === json({ green: [5, 90, 5, -200] }));
const vMono = vueReglage("channelMixer", fx("channelMixer/monochrome"), "red", CH.channelMixer);
check("7.10 mélangeur monochrome : seule la sortie Gris", json(vMono.selecteur.options.map((o) => o.valeur)) === json(["gray"]) && vMono.selecteur.valeur === "gray" && json(vMono.champs[0].chemin) === json(["gray", 0]));
check("7.11 lignes par défaut du mélangeur", json(LIGNES_MIXEUR.red) === "[100,0,0,0]" && json(LIGNES_MIXEUR.gray) === "[40,40,20,0]");
const etSC = fx("selectiveColor/base");
const vSC = vueReglage("selectiveColor", etSC, "neutrals", CH.selectiveColor);
check("7.12 sélective : 9 gammes, 4 curseurs cyan/magenta/yellow/black + méthode", json(vSC.selecteur.options.map((o) => o.valeur)) === json(GAMMES_SELECTIVE)
  && json(vSC.champs.map((e) => e.c.cle)) === json(["cyan", "magenta", "yellow", "black", "method"]) && vSC.champs[0].valeur === 1);
check("7.13 sélective : jaune des neutres -> neutrals:[1,2,50,4]", json(difference(etSC, appliquer(etSC, vSC.champs[2], 50, valeursVue(vSC, etSC)))) === json({ neutrals: [1, 2, 50, 4] }));
const etGM = fx("gradientMap/base");
const vGM = vueReglage("gradientMap", etGM, null, CH.gradientMap);
check("7.14 dégradé : couleurs de départ et d'arrivée + inverser + tramer", json(vGM.champs.map((e) => e.c.cle)) === json(["debut", "fin", "reverse", "dither"])
  && json(vGM.champs[1].chemin) === json(["stops", 2, 1]) && vGM.champs[0].valeur === "#101030");
const apGM = appliquer(etGM, vGM.champs[1], "#00FF00", valeursVue(vGM, etGM));
check("7.15 dégradé : couleur d'arrivée changée, arrêt intermédiaire gardé", json(difference(etGM, apGM)) === json({ stops: [[0, "#101030"], [0.4, "#c04020"], [1, "#00ff00"]] }));
check("7.16 dégradé sans arrêts connus : défaut noir -> blanc", json(appliquer({}, vueReglage("gradientMap", {}, null, CH.gradientMap).champs[0], "#112233", {}).stops) === json([[0, "#112233"], DEGRADE_DEFAUT[1]]));
const vFG = vueReglage("colorLookup", fx("colorLookup/base"), null, CH.colorLookup);
check("7.17 formulaire : champs visibles du registre (ni file ni data)", vFG.selecteur === null && json(vFG.champs.map((e) => e.c.cle)) === json(["lut", "interpolation", "dither"]) && vFG.champs[0].valeur === "warm");
check("7.18 signature : change avec la structure, pas avec les valeurs",
  signatureVue(vMX) === signatureVue(vueReglage("channelMixer", { ...etMX, green: [1, 1, 1, 1] }, "green", CH.channelMixer)) && signatureVue(vMX) !== signatureVue(vMono));
check("7.19 aucun / ton : vue vide", vueReglage("invert", {}, null, []).champs.length === 0 && vueReglage("curves", {}, null, []).champs.length === 0);

// 8. liste des LUT (image.adjustments.colorLookup.list) : tableau direct ou enveloppé
const L = fixture["colorLookup/base"].lut_list;
check("8.1 liste directe", lutsDepuisReponse(L).length === 8 && lutsDepuisReponse({ looks: L }).length === 8 && lutsDepuisReponse({ list: L }).length === 8);
check("8.2 illisible -> null", lutsDepuisReponse(null) === null && lutsDepuisReponse({}) === null && lutsDepuisReponse([{ x: 1 }]) === null);

console.log(`reglages : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
