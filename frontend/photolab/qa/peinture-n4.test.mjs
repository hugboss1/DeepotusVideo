// qa/peinture-n4.test.mjs — t414 (Photolab N4, photocraft 0.21) : Mélangeur, Forme d'art d'historique, source de l'historique,
// pinceau précédent / suivant. Fonctions PURES ; le moteur est prouvé par backend/tests/test_photolab_n4.py.
import { commandeTrait, commandeChargeMelangeur, OPTIONS_PEINTURE, OUTILS_PEINTURE, STYLES_ART, optionsPeinture, defautsPeinture, altCharge } from "../js/mod-peinture.js";
import { EMPLACEMENTS } from "../js/mod-outils.js";
import { estSource, commandeSource, traduireEtat } from "../js/mod-historique.js";
import { touchePinceau } from "../js/mod-pinceaux.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const T = (c) => (dico[c] ? dico[c].fr : c);
const P = [[1, 2], [3, 4]];

const m = commandeTrait("mixerBrush", P, { ...defautsPeinture("mixerBrush"), nettoyerApres: true, chargerApres: false }, { fg: "#123456" });
check("1.1 Mélangeur : options après le trait", m.params.cleanAfterStroke === true && m.params.loadAfterStroke === false, m.params);
check("1.2 par défaut : ni nettoyé ni chargé après le trait", commandeTrait("mixerBrush", P, defautsPeinture("mixerBrush"), { fg: "#000000" }).params.cleanAfterStroke === false);
check("1.3 Alt-clic : charger depuis la toile, pixel entier, sonde de l'outil", eq(commandeChargeMelangeur(10.6, 20.2, { tousCalques: true }), { command: "paint.mixerLoad", params: { x: 10, y: 20, size: 1, sampleAllLayers: true } }));
check("1.4 Alt charge le Mélangeur seul", altCharge("mixerBrush") === true && altCharge("brush") === false);
const barre = OPTIONS_PEINTURE.mixerBrush.map((o) => o.cle);
check("1.5 barre : cases et boutons", ["nettoyerApres", "chargerApres", "chargerPinceau", "nettoyerPinceau"].every((c) => barre.includes(c)), barre);
check("1.6 boutons branchés", OPTIONS_PEINTURE.mixerBrush.find((o) => o.cle === "nettoyerPinceau").action === "brush.mixer.clean"
  && OPTIONS_PEINTURE.mixerBrush.find((o) => o.cle === "chargerPinceau").action === "brush.mixer.load");

check("2.1 Forme d'art : un outil de trait", OUTILS_PEINTURE.artHistoryBrush.commande === "paint.artHistoryBrush" && OUTILS_PEINTURE.artHistoryBrush.sorte === "trait");
check("2.2 huit styles", STYLES_ART.length === 8 && STYLES_ART.includes("tightMedium") && STYLES_ART.includes("looseCurl"));
const a = commandeTrait("artHistoryBrush", P, { ...defautsPeinture("artHistoryBrush"), styleArt: "dab", zone: 30, toleranceArt: 10, opacite: 80, taille: 15, durete: 20 }, {});
check("2.3 paramètres du moteur", eq(a.params, { points: P, size: 15, hardness: 20, opacity: 80, style: "dab", area: 30, tolerance: 10 }), a.params);
check("2.4 défauts du moteur", eq(commandeTrait("artHistoryBrush", P, defautsPeinture("artHistoryBrush"), {}).params.style, "tightMedium"));
check("2.5 barre", optionsPeinture("artHistoryBrush").map((o) => o.cle).join() === "taille,durete,opacite,styleArt,zone,toleranceArt", optionsPeinture("artHistoryBrush").map((o) => o.cle));
const y = EMPLACEMENTS.find((e) => e[0].id === "historyBrush");
check("2.6 dans le groupe Y, avec son icône", y.some((o) => o.id === "artHistoryBrush" && o.lettre === "Y" && o.icone === "dz-outil-photo-pinceau-art-historique" && o.p2));
const icones = readFileSync(new URL("../../shared/icons/dz-icons.js", import.meta.url), "utf8");
check("2.7 l'icône est dans la suite", icones.includes('"dz-outil-photo-pinceau-art-historique"'));

check("3.1 état source", estSource({ historySource: { state: 3 } }, { etat: 3 }) === true && estSource({ historySource: { state: 3 } }, { etat: 2 }) === false);
check("3.2 instantané source", estSource({ historySource: { snapshot: 4 } }, { instantane: 4 }) === true && estSource({ historySource: { snapshot: 4 } }, { etat: 4 }) === false);
check("3.2b un autre instantané : non", estSource({ historySource: { snapshot: 4 } }, { instantane: 5 }) === false);
check("3.3 sans source dite : aucune", estSource({}, { etat: 0 }) === false);
check("3.4 commandes", eq(commandeSource({ etat: 2 }), { state: 2 }) && eq(commandeSource({ instantane: 5 }), { snapshot: 5 }));

check("4.1 , et . : précédent et suivant", touchePinceau(",", false) === "tools.previousBrush" && touchePinceau(".", false) === "tools.nextBrush");
check("4.2 Maj : premier et dernier", touchePinceau("<", true) === "tools.firstBrush" && touchePinceau(">", true) === "tools.lastBrush" && touchePinceau(",", true) === "tools.firstBrush" && touchePinceau(".", true) === "tools.lastBrush");
check("4.3 une autre touche : rien", touchePinceau("a", false) === null);

check("5.1 état traduit", traduireEtat("Art History Brush", null, T) === dico["photolab.outil.art_history_brush"].fr);
for (const c of ["photolab.outil.art_history_brush", "photolab.peinture.style_art", "photolab.peinture.zone", "photolab.peinture.tolerance_art", "photolab.peinture.nettoyer_apres",
  "photolab.peinture.charger_apres", "photolab.peinture.charger_pinceau", "photolab.peinture.nettoyer_pinceau", "photolab.historique.source", "photolab.peinture.melangeur_charge",
  ...STYLES_ART.map((s) => "photolab.peinture.style_art." + s.replace(/[A-Z]/g, (x) => "_" + x.toLowerCase()))])
  check(`5.2 ${c} fr et en`, dico[c]?.fr && dico[c]?.en, c);

console.log(`peinture-n4 : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
