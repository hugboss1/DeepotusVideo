// qa/historique-n5.test.mjs — t415 (Photolab N5, photocraft 0.21) : options d'historique, Effacer l'historique, Options de
// lecture. Fonctions PURES et lecture des sources ; le moteur est prouvé par backend/tests/test_photolab_n5.py.
import { OPTIONS_HISTORIQUE, corpsOptions, nomInstantane, instantanesDe } from "../js/mod-historique.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const lire = (n) => readFileSync(new URL("../js/" + n, import.meta.url), "utf8");
const py = readFileSync(new URL("../../../backend/app/services/photolab_options.py", import.meta.url), "utf8");

check("1.1 quatre options, chacune connue du pont", OPTIONS_HISTORIQUE.length === 4 && OPTIONS_HISTORIQUE.every(([c]) => py.includes(`"${c}"`)));
check("1.2 l'historique non linéaire n'est pas proposé", !OPTIONS_HISTORIQUE.some(([c]) => /lineaire/i.test(c)));
const avant = { premierInstantane: true, instantaneEnregistrement: false, dialogueInstantane: false, visibiliteAnnulable: true };
const cases = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, { checked: v }]));
check("1.3 rien de changé : corps vide", eq(corpsOptions(avant, cases(avant)), {}));
check("1.4 seules les cases changées partent", eq(corpsOptions(avant, cases({ ...avant, dialogueInstantane: true })), { dialogueInstantane: true }));
check("1.5 une case décochée part à faux", eq(corpsOptions(avant, cases({ ...avant, premierInstantane: false })), { premierInstantane: false }));

const doc = { name: "c4532058-fond.png" };
check("1.6 premier instantané : le nom du document, sans sa copie de travail", nomInstantane("c4532058-fond.png", doc) === "fond");
check("1.7 un nom de l'utilisateur reste tel quel", nomInstantane("Avant.png", doc) === "Avant.png");
check("1.8 un document sans empreinte garde son nom, sans extension", nomInstantane("Sans titre", { name: "Sans titre" }) === "Sans titre");
check("1.9 instantanesDe applique ce nom", eq(instantanesDe({ ...doc, snapshots: [{ id: 0, name: "c4532058-fond.png" }, { id: 1, name: "x" }] }), [{ id: 0, nom: "fond" }, { id: 1, nom: "x" }]));

const hist = lire("mod-historique.js"), act = lire("mod-actions.js");
check("2.1 Effacer l'historique passe par la commande moteur", hist.includes('PL.executer("history.clear", {})'));
check("2.2 le panneau a ses deux boutons", hist.includes("barre.append(bAnnuler, bRetablir, bInstantane, bDocument, bEffacer, bOptions)"));
check("2.3 mod-fichier et mod-nommer à la demande (mod-cycle importe mod-historique)", !/^import .*mod-(fichier|nommer)/m.test(hist));
check("2.4 Options de lecture branchées dans le menu du panneau", act.includes('else if (id === "lecture") optionsLecture();'));
for (const c of ["photolab.commande.history.clear", "photolab.historique.options", ...OPTIONS_HISTORIQUE.map((x) => x[1]), "photolab.actions.menu.lecture",
  "photolab.actions.lecture_titre", "photolab.actions.lecture_un_etat"])
  check(`3.1 ${c} fr et en`, dico[c]?.fr && dico[c]?.en, c);

console.log(`historique-n5 : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
