// qa/presets-n6.test.mjs — t416 (Photolab N6, photocraft 0.21) : importer et exporter styles et formes. Fonctions PURES ;
// le moteur est prouvé par backend/tests/test_photolab_n6.py.
import { EXTENSIONS_BIBLIO, groupeDeFichier, corpsImport, octetsEnBase64 } from "../js/mod-presets.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const src = readFileSync(new URL("../js/mod-presets.js", import.meta.url), "utf8");

check("1.1 styles .asl, formes .csh, rien d'autre", eq(EXTENSIONS_BIBLIO, { styles: ".asl", formes: ".csh" }));
check("1.2 le groupe prend le nom du fichier", groupeDeFichier("Mes styles.asl") === "Mes styles");
check("1.3 nom vide : un repli", groupeDeFichier(".asl") === "Import" && groupeDeFichier("") === "Import");
check("1.4 borné à 64 caractères", groupeDeFichier("x".repeat(90) + ".csh").length === 64);
check("1.5 corps de l'import", eq(corpsImport("formes", "a.csh", "QQ=="), { genre: "formes", groupe: "a", data: "QQ==" }));
check("1.6 base64 fidèle", octetsEnBase64(new Uint8Array([0, 255, 65])) === Buffer.from([0, 255, 65]).toString("base64"));
const gros = new Uint8Array(100000).map((_, i) => i % 256);
check("1.7 un gros fichier passe", octetsEnBase64(gros) === Buffer.from(gros).toString("base64"));
check("2.1 export des styles seulement", src.includes('if (genre === "styles") {') && src.includes('"/bibliotheques/exporter"'));
for (const c of ["photolab.presets.importer", "photolab.presets.exporter", "photolab.presets.importes", "photolab.presets.choisir_groupe"]) check(`3.1 ${c} fr et en`, dico[c]?.fr && dico[c]?.en, c);

console.log(`presets-n6 : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
