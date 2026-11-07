// qa/objets-n1.test.mjs — t411 (Photolab N1, photocraft 0.21) : Remplacer et Exporter le contenu d'un objet dynamique.
// Fonctions PURES ; le comportement du moteur est prouvé par backend/tests/test_photolab_n1.py.
import { construireMenus, actionEntree, TRAITES_PAR_ECRAN, NECESSITE_DOC, REFUSES, IDS_OBJETS } from "../js/mod-menus.js";
import { estObjetDynamique, decorerObjets } from "../js/mod-objets.js";
import { traduireEtat } from "../js/mod-historique.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const menusJson = JSON.parse(readFileSync(new URL("../donnees/menus.json", import.meta.url), "utf8"));

check("1.1 deux entrées, servies par l'écran, document requis", IDS_OBJETS.length === 2
  && IDS_OBJETS.every((id) => TRAITES_PAR_ECRAN.has(id) && NECESSITE_DOC.has(id)), IDS_OBJETS);
check("1.2 elles existent dans l'arbre des menus", IDS_OBJETS.every((id) => menusJson.entrees.some((e) => e.id === id)));
check("1.3 les liens et les vecteurs ne sont pas ouverts", !TRAITES_PAR_ECRAN.has("layer.smartObjects.relinkToFile")
  && !TRAITES_PAR_ECRAN.has("layer.smartObjects.convertToLinked"));

const registre = [{ id: "layer.smartObjects.replaceContents", enabled: false, champs: [] }, { id: "layer.smartObjects.exportContents", enabled: false, champs: [] }];
const trouver = (menus, id) => { for (const m of menus) { const l = m.entrees || []; for (const e of l) { if (e.id === id) return e; if (e.entrees) { const f = trouver([e], id); if (f) return f; } } } return null; };
const menus = construireMenus(menusJson, registre, REFUSES, "fr");
check("2.1 l'entrée sort de « bientôt »", IDS_OBJETS.every((id) => { const e = trouver(menus, id); return e && e.etat === "actif"; }), IDS_OBJETS.map((id) => trouver(menus, id)));
check("2.2 elle passe par l'écran, jamais par le moteur", IDS_OBJETS.every((id) => actionEntree(trouver(menus, id)) === "ecran"));

check("3.1 objet dynamique reconnu", estObjetDynamique({ kind: "Smart Object" }) === true);
check("3.2 autre calque, ou aucun : non", estObjetDynamique({ kind: "Pixel" }) === false && estObjetDynamique(null) === false);
const inactive = decorerObjets(menus, { kind: "Pixel" }), active = decorerObjets(menus, { kind: "Smart Object" });
check("3.3 grisées hors d'un objet dynamique", IDS_OBJETS.every((id) => trouver(inactive, id).etat === "inactif"));
check("3.4 actives sur un objet dynamique", IDS_OBJETS.every((id) => trouver(active, id).etat === "actif"));
check("3.5 les autres entrées ne bougent pas", trouver(inactive, "layer.smartObjects.convertToLayers")?.etat === trouver(menus, "layer.smartObjects.convertToLayers")?.etat);

const T = (c, v) => (dico[c] ? dico[c].fr.replace("{nom}", v?.nom ?? "") : c);
check("4.1 état d'historique traduit", traduireEtat("Replace Contents", null, T) === "Remplacer le contenu", traduireEtat("Replace Contents", null, T));
for (const c of ["photolab.objets.remplacer_choisir", "photolab.objets.remplace", "photolab.objets.exporte"])
  check(`4.2 ${c} fr et en`, dico[c]?.fr && dico[c]?.en, c);

console.log(`objets-n1 : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
