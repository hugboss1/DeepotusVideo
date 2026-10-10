// qa/outils/suite-icones.mjs — G4 : les clés de la suite Deepotus Glyph (/shared/icons/dz-icons.js), lues en EXÉCUTANT
// le runtime partagé sous node (window factice) : un banc QA du Photolab vérifie ainsi qu'une icône demandée existe
// (une clé inconnue rendrait un bouton vide, sans erreur).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ici = dirname(fileURLToPath(import.meta.url));
export const CHEMIN_SUITE = join(ici, "..", "..", "..", "shared", "icons", "dz-icons.js");
const fenetre = {};
vm.runInNewContext(readFileSync(CHEMIN_SUITE, "utf8"), { window: fenetre });
export const CLES = new Set(Object.keys(fenetre.DZ_ICONS || {}));
export const dzIcone = fenetre.dzIcone;
export const existe = (cle) => CLES.has(cle);
