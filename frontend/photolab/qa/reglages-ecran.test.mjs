// qa/reglages-ecran.test.mjs — l'éditeur des calques de réglage TEL QU'IL TOURNE (t138 B5, relecture) : faux DOM
// (qa/outils/faux-dom.mjs) et faux PL qui enregistre les commandes. Tue les mutations que les fonctions pures ne voient
// pas : calque visé quand le calque actif change, re-rendu après Colorer / Monochrome, saisie non envoyée gardée,
// contrôle sous les doigts jamais réécrit, état relu différé pendant un geste des Niveaux, liste des LUT redemandée.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { installerFauxDom } from "./outils/faux-dom.mjs";
import { initReglages, GAMMES_TEINTE } from "../js/mod-reglages.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, typeof detail === "string" ? detail : JSON.stringify(detail)); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const fixture = JSON.parse(readFileSync(join(racine, "qa/fixtures/reglages-inspect.json"), "utf8"));
const json = (x) => JSON.stringify(x);
const pause = (ms = 5) => new Promise((r) => setTimeout(r, ms));
const copie = (x) => JSON.parse(JSON.stringify(x));

const doc = installerFauxDom();
const corps = doc.createElement("div"); corps.id = "corpsProprietes";
const corpsAj = doc.createElement("div");
const grp = doc.createElement("section");
grp.append(corps, corpsAj); doc.body.appendChild(grp);

// Registre (forme structurée du pont) : les champs dont les vues ont besoin.
const n = (cle, min, max) => ({ cle, type: "number", min, max, entier: true, defaut: 0 });
const REGISTRE = [
  { id: "layer.newAdjustmentLayer.hueSaturation", champs: [n("hue", -180, 180), n("saturation", -100, 100), n("lightness", -100, 100),
    { cle: "colorize", type: "bool", defaut: false }, ...GAMMES_TEINTE.map((g) => ({ cle: g, type: "json" }))] },
  { id: "layer.newAdjustmentLayer.channelMixer", champs: ["red", "green", "blue", "gray"].map((cle) => ({ cle, type: "json" }))
    .concat([{ cle: "monochrome", type: "bool", defaut: false }]) },
  { id: "layer.newAdjustmentLayer.colorLookup", champs: [{ cle: "lut", type: "enum", valeurs: ["none", "warm"], defaut: "none" }] },
];
const appels = [];
let reponseListe = { ok: false };
const PL = {
  etat: { doc: null, generation: 1 }, surDoc: [],
  $: (sel) => ({ "#grpProprietes": grp, "#corpsProprietes": corps, "#corpsAjustements": corpsAj }[sel] || null),
  $$: () => [],
  hydraterIcones: () => Promise.resolve(),
  executer: (command, params, opts) => { appels.push({ command, params, opts }); return Promise.resolve(command.endsWith(".list") ? reponseListe : { ok: true, r: {} }); },
  get: () => Promise.resolve(null),
  menus: { registre: REGISTRE },
};
initReglages(PL);

const calque = (id, cas, nom) => ({ id, name: nom || cas, kind: "Adjustment", adjustment: copie(fixture[cas].adjustment) });
const docDe = (actif, layers) => ({ index: 0, name: "essai", activeLayer: actif, layers });
const afficher = (d) => { PL.etat.doc = d; return PL.reglages.proprietes(corps, d); };
const ligne = (cle) => corps.tous((x) => x.dataset && x.dataset.cle === cle)[0];
const champ = (cle, type) => { const l = ligne(cle); return l ? l.tous((x) => x.tagName === "INPUT" && x.type === type)[0] : null; };
const selects = () => corps.tous((x) => x.tagName === "SELECT");
const dernier = () => appels[appels.length - 1];

// 1. le calque visé suit le calque actif (clé d'identité de l'éditeur : id du calque compris)
const hs5 = calque(5, "hueSaturation/base", "Hue/Saturation 1"), hs8 = calque(8, "hueSaturation/base", "Hue/Saturation 2");
check("1.1 calque de réglage actif : l'éditeur prend le panneau", afficher(docDe(5, [hs5, hs8])) === true && !!champ("saturation", "range"));
let c = champ("saturation", "range"); c.value = "-90"; c.envoyer("change");
check("1.2 relâchement -> layer.setAdjustment {layer: 5, saturation: -90} (rien d'autre)", json(dernier()) === json({ command: "layer.setAdjustment", params: { layer: 5, saturation: -90 }, opts: undefined }), dernier());
afficher(docDe(8, [hs5, hs8]));
c = champ("saturation", "range"); c.value = "-50"; c.envoyer("change");
check("1.3 autre calque actif du même kind : l'envoi vise le calque 8", dernier().params.layer === 8 && dernier().params.saturation === -50, dernier());
check("1.4 calque de pixels actif : le panneau rend la main", afficher(docDe(1, [{ id: 1, name: "Fond", kind: "Pixel" }])) === false && !corps.tous((x) => x.className === "rg-editeur").length);

// 2. Colorer / Monochrome changent la STRUCTURE : re-rendu immédiat
afficher(docDe(5, [hs5]));
check("2.1 Teinte/Saturation : sélecteur de gamme présent", selects().length === 1 && selects()[0].children.length === 7);
const k = champ("colorize", "checkbox"); k.checked = true; k.envoyer("change");
check("2.2 Colorer -> {layer, colorize: true}", json(dernier().params) === json({ layer: 5, colorize: true }), dernier());
check("2.3 … et le sélecteur de gamme disparaît aussitôt", selects().length === 0, selects().length);
afficher(docDe(9, [calque(9, "channelMixer/base")]));
check("2.4 Mélangeur : sorties Rouge/Vert/Bleu", selects().length === 1 && json(selects()[0].children.map((o) => o.value)) === json(["red", "green", "blue"]));
const m = champ("monochrome", "checkbox"); m.checked = true; m.envoyer("change");
check("2.5 Monochrome -> sortie Gris seule, tout de suite", dernier().params.monochrome === true && json(selects()[0].children.map((o) => o.value)) === json(["gray"]));

// 3. saisie non envoyée gardée ; contrôle sous les doigts jamais réécrit ; retour égal à l'envoi ignoré
const hsA = calque(5, "hueSaturation/base");
afficher(docDe(5, [hsA]));
c = champ("saturation", "range"); c.value = "-30"; c.envoyer("input");
const nAvant = appels.length;
check("3.1 pendant le glisser : rien n'est envoyé", appels.length === nAvant);
const hsB = copie(hsA); hsB.adjustment.HueSaturation.lightness = 7;           // le moteur a changé autre chose (annuler…)
afficher(docDe(5, [hsB]));
check("3.2 l'état relu réécrit les autres contrôles", champ("lightness", "number").value === "7", champ("lightness", "number").value);
c = champ("saturation", "range"); c.value = "-30"; c.envoyer("change");
check("3.3 la saisie en cours a survécu à l'état relu : seule elle part", json(dernier().params) === json({ layer: 5, saturation: -30 }), dernier());
// curseur TENU : un état relu arrive pendant le glisser ; au relâchement (pointerup hors du panneau), le curseur et son
// champ montrent toujours la saisie, pas l'ancienne valeur du moteur
c = champ("saturation", "range"); c.envoyer("pointerdown"); c.value = "-60"; c.envoyer("input");
const hsB2 = copie(hsB); hsB2.adjustment.HueSaturation.saturation = -30; hsB2.adjustment.HueSaturation.lightness = 9;
afficher(docDe(5, [hsB2]));
check("3.3b curseur tenu : son champ n'est pas réécrit", champ("saturation", "number").value === "-60", champ("saturation", "number").value);
doc.envoyer("pointerup");
await pause();
check("3.3c relâché : la saisie non envoyée reste affichée, le reste suit le moteur",
  champ("saturation", "number").value === "-60" && champ("lightness", "number").value === "9", [champ("saturation", "number").value, champ("lightness", "number").value]);
c = champ("saturation", "range"); c.value = "-60"; c.envoyer("change");
check("3.3d puis le relâchement n'envoie qu'elle", json(dernier().params) === json({ layer: 5, saturation: -60 }), dernier());
const hsC0 = copie(hsB2); hsC0.adjustment.HueSaturation.saturation = -60;
afficher(docDe(5, [hsC0]));
const num = champ("hue", "number"); num.focus(); num.value = "33";
const hsC = copie(hsB); hsC.adjustment.HueSaturation.hue = 12; hsC.adjustment.HueSaturation.saturation = -30;
afficher(docDe(5, [hsC]));
check("3.4 champ qui a le focus : jamais réécrit sous les doigts", num.value === "33", num.value);
doc.envoyer("pointerup");                          // une fin de prise ailleurs ne le réécrit pas non plus
await pause();
check("3.4b fin de prise : le champ qui a le focus reste tel quel", num.value === "33", num.value);
// structure changée (Colorer allumé par le moteur, annuler…) pendant que le champ a le focus : reconstruction DIFFÉRÉE
const hsD = copie(hsC); hsD.adjustment.HueSaturation.colorize = true;
afficher(docDe(5, [hsD]));
check("3.4c reconstruction différée : le champ reste en place, le sélecteur aussi", num.isConnected && selects().length === 1);
num.blur(); num.envoyer("focusout");
await pause();
check("3.4d focus perdu : reconstruit (plus de sélecteur de gamme)", !num.isConnected && selects().length === 0);
afficher(docDe(5, [hsC]));
const avantEcho = selects()[0];
afficher(docDe(5, [hsC]));
check("3.5 retour égal à l'état connu : aucune reconstruction", selects()[0] === avantEcho);

// 4. Niveaux (éditeur de B4) : état relu différé pendant une saisie, posé à la fin ; retour de notre envoi ignoré
const nv = calque(12, "levels/base");
afficher(docDe(12, [nv]));
const nums = () => corps.tous((x) => x.tagName === "INPUT" && x.type === "number");
check("4.1 Niveaux : champs numériques de B4 (inBlack = 20)", nums().length === 5 && nums()[0].value === "20", nums().map((x) => x.value));
nums()[0].focus();
const nv2 = copie(nv); nv2.adjustment.Levels.master.in_black = 40 / 255;
afficher(docDe(12, [nv2]));
check("4.2 saisie en cours : l'état relu attend", nums()[0].value === "20", nums()[0].value);
doc.activeElement = doc.body; nums()[0].envoyer("focusout");
await pause();
check("4.3 fin de la saisie : l'état relu est posé", nums()[0].value === "40", nums()[0].value);
const n0 = appels.length;
nums()[2].value = "200"; nums()[2].envoyer("change");
check("4.4 une saisie part en layer.setAdjustment avec les quatre canaux", appels.length === n0 + 1 && dernier().params.layer === 12
  && ["red", "green", "blue"].every((x) => x in dernier().params) && dernier().params.inWhite === 200, dernier());

// 4b. Courbes : le point actif reste choisi quand l'état relu le garde
const cb = calque(13, "curves/base");
afficher(docDe(13, [cb]));
const grille = corps.tous((x) => /pl-ton-grille/.test(x.getAttribute("class") || ""))[0];
const actifs = () => corps.tous((x) => /pl-ton-point actif/.test(x.getAttribute("class") || "")).length;
// point (64, 40) de la courbe : unités SVG (64·256/255, 256 − 40·256/255), écran = unités × 262/256
grille.envoyer("pointerdown", { clientX: (64 * 256 / 255) * 262 / 256, clientY: (256 - 40 * 256 / 255) * 262 / 256 });
grille.envoyer("pointerup");
check("4b.1 clic sur un point : actif, relâchement envoyé", actifs() === 1 && dernier().params.layer === 13, [actifs(), dernier()]);
const cb2 = copie(cb); cb2.adjustment.Curves.master[2].output = 0.9;     // le moteur relit un autre point
afficher(docDe(13, [cb2]));
check("4b.2 état relu : le point actif reste choisi", actifs() === 1, actifs());

// 5. liste des LUT : redemandée après un échec
const nList = () => appels.filter((a) => a.command === "image.adjustments.colorLookup.list").length;
afficher(docDe(20, [calque(20, "colorLookup/base")]));
await pause();
check("5.1 Color Lookup : la liste est demandée hors cycle", nList() === 1 && appels.find((a) => a.command.endsWith(".list")).opts.cycle === false);
reponseListe = { ok: true, r: fixture["colorLookup/base"].lut_list };
afficher(docDe(20, [calque(20, "colorLookup/base")]));
await pause();
check("5.2 échec précédent : redemandée, puis le LUT relu est choisi", nList() === 2 && corps.tous((x) => x.tagName === "SELECT")[0].value === "warm",
  [nList(), (corps.tous((x) => x.tagName === "SELECT")[0] || {}).value]);
afficher(docDe(20, [calque(20, "colorLookup/base")]));
check("5.3 chargée une fois : plus redemandée", nList() === 2);

// 6. épingle : l'éditeur de B4 est construit en mode cible (sans aperçu JS, envoi des 4 canaux au relâchement)
const src = readFileSync(join(racine, "js/mod-reglages.js"), "utf8");
check("6.1 construireEditeurTon(…, { …, cible: true, … })", /construireEditeurTon\(s, zone, \{ T, etat: etatDepuisParams\(s, etat\), cible: true,/.test(src));

console.log(`reglages-ecran : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
