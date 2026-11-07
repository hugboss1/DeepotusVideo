// qa/traces-n3.test.mjs — t413 (Photolab N3, photocraft 0.21) : menu des tracés (opérations, fusion, sélection), angles
// arrondis des polygones, flèches du Trait. Fonctions PURES ; moteur prouvé par backend/tests/test_photolab_n3.py.
import { entreesMenuTrace, sousTracesVises, OPERATIONS_TRACE } from "../js/mod-trace.js";
import { commandeForme, FORMES_DEFAUT, ajoutForme, OPERATIONS_FORME } from "../js/mod-formes.js";
import { traduireEtat } from "../js/mod-historique.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const T = (c) => (dico[c] ? dico[c].fr : c);
const par = (e, id) => entreesMenuTrace(e).filter(Boolean).find((x) => x.id === id);

check("1.1 quatre opérations", eq(OPERATIONS_TRACE, ["combine", "subtract", "intersect", "exclude"]));
const e2 = { nom: "layer", composants: 2 };
check("1.2 opérations actives dès deux composants", OPERATIONS_TRACE.every((o) => par(e2, "path.op." + o)?.actif === true));
check("1.3 inactives avec un seul composant", OPERATIONS_TRACE.every((o) => par({ nom: "layer", composants: 1 }, "path.op." + o)?.actif === false));
check("1.4 fusion : dès deux composants", par(e2, "path.mergeShapeComponents").actif === true && par({ nom: "work", composants: 1 }, "path.mergeShapeComponents").actif === false);
check("1.5 ajouter et soustraire : dès qu'un tracé est visé", par({ nom: "work" }, "path.selection.add").actif && par({ nom: "work" }, "path.selection.subtract").actif && !par({}, "path.selection.add").actif);
check("1.6 le reste du menu est là", !!par(e2, "path.toSelection") && !!par(e2, "path.transform"));

check("2.1 sous-tracés choisis, uniques et triés", eq(sousTracesVises([[2, 0], [1, 3], [2, 1]], 3), [1, 2]));
check("2.2 rien de choisi : tous sauf le premier", eq(sousTracesVises([], 3), [1, 2]));
check("2.3 seul le premier choisi : idem (il combine toujours)", eq(sousTracesVises([[0, 1]], 3), [1, 2]));
check("2.4 un choix qui dépasse est ignoré", eq(sousTracesVises([[5, 0], [1, 0]], 2), [1]));

const g = { rect: { x: 0, y: 0, w: 50, h: 50 } }, ligne = { de: [0, 0], a: [50, 0] };
check("3.1 polygone sans rayon : clé absente", !("cornerRadius" in commandeForme("polygon", g, FORMES_DEFAUT).params));
check("3.2 polygone avec rayon", commandeForme("polygon", g, { ...FORMES_DEFAUT, rayon: 8 }).params.cornerRadius === 8);
check("3.3 triangle avec rayon", commandeForme("triangle", g, { ...FORMES_DEFAUT, rayon: 4 }).params.cornerRadius === 4);
check("3.4 rectangle : toujours radii", commandeForme("rectangle", g, { ...FORMES_DEFAUT, rayon: 8 }).params.radii === 8);
const sans = commandeForme("line", ligne, FORMES_DEFAUT).params;
check("3.5 trait sans flèche : aucune clé de flèche", !Object.keys(sans).some((k) => k.startsWith("arrow")), sans);
const fin = commandeForme("line", ligne, { ...FORMES_DEFAUT, flecheFin: true, flecheLargeur: 60, flecheLongueur: 70, flecheCreux: 20 }).params;
check("3.6 flèche de fin et ses mesures", fin.arrowEnd === true && fin.arrowStart === false && fin.arrowWidth === 60 && fin.arrowLength === 70 && fin.arrowConcavity === 20, fin);
check("3.7 flèche de début", commandeForme("line", ligne, { ...FORMES_DEFAUT, flecheDebut: true }).params.arrowStart === true);
check("3.8 creux borné à 100", commandeForme("line", ligne, { ...FORMES_DEFAUT, flecheFin: true, flecheCreux: 400 }).params.arrowConcavity === 100);

const cr = commandeForme("ellipseShape", g, FORMES_DEFAUT, "#ff0000");
check("3.9 par défaut : un calque neuf", OPERATIONS_FORME[0] === "nouveau" && eq(ajoutForme(cr, "ellipseShape", FORMES_DEFAUT, 7), cr));
const aj = ajoutForme(cr, "ellipseShape", { ...FORMES_DEFAUT, operation: "subtract" }, 7);
check("3.10 opération : ajoutée au calque actif, sans fond ni contour", aj.params.addTo === 7 && aj.params.op === "subtract" && !("fill" in aj.params) && !("stroke" in aj.params), aj);
check("3.11 sans calque de forme actif : un calque neuf", eq(ajoutForme(cr, "ellipseShape", { ...FORMES_DEFAUT, operation: "subtract" }, null), cr));
const tr = commandeForme("line", ligne, FORMES_DEFAUT);
check("3.12 le trait reste à part", eq(ajoutForme(tr, "line", { ...FORMES_DEFAUT, operation: "subtract" }, 7), tr));
for (const [nom] of [["Add Shape"], ["Path Operation"], ["Merge Shape Components"]]) check(`4.1 ${nom} traduit`, traduireEtat(nom, null, T) !== nom);
for (const c of ["photolab.traces.op_combine", "photolab.traces.op_subtract", "photolab.traces.op_intersect", "photolab.traces.op_exclude", "photolab.traces.fusionner_composants",
  "photolab.traces.selection_ajouter", "photolab.traces.selection_soustraire", "photolab.formes.fleche_debut", "photolab.formes.fleche_fin", "photolab.formes.fleche_largeur",
  "photolab.formes.fleche_longueur", "photolab.formes.fleche_creux", "photolab.histo.operation_trace", "photolab.formes.operation", "photolab.formes.op_nouveau"])
  check(`4.2 ${c} fr et en`, dico[c]?.fr && dico[c]?.en, c);

console.log(`traces-n3 : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
