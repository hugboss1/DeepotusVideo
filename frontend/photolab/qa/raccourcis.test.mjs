// qa/raccourcis.test.mjs — raccourcis clavier : les combinaisons du catalogue (menus générés) et celles que l'écran
// ajoute (Ctrl+Z, Ctrl+Maj+Z, Ctrl+Maj+I : absentes du catalogue de photocraft).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { normaliser, comboDe, indexRaccourcis, RACCOURCIS_ECRAN, aIntercepter } from "../js/mod-raccourcis.js";
import { construireMenus, REFUSES } from "../js/mod-menus.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const catalogue = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));

// 1. forme canonique
check("1.1 Cmd -> ctrl, ordre des modificateurs fixe", normaliser("Cmd+Shift+N") === "ctrl+shift+n" && normaliser("Shift+Cmd+N") === "ctrl+shift+n");
check("1.2 Maj (affichage fr) = shift", normaliser("Ctrl+Maj+N") === "ctrl+shift+n");
check("1.3 trois modificateurs", normaliser("Cmd+Alt+Shift+W") === "ctrl+alt+shift+w" && normaliser("Ctrl+Maj+Alt+W") === "ctrl+alt+shift+w");
check("1.4 touche de fonction", normaliser("Shift+F5") === "shift+f5" && normaliser("F12") === "f12");
check("1.5 vide", normaliser("") === "" && normaliser(null) === "");

// 2. événement -> combinaison
const ev = (o) => ({ ctrlKey: false, metaKey: false, altKey: false, shiftKey: false, key: "", code: "", ...o });
check("2.1 Ctrl+J", comboDe(ev({ ctrlKey: true, key: "j", code: "KeyJ" })) === "ctrl+j");
check("2.2 Cmd (Mac) = Ctrl", comboDe(ev({ metaKey: true, key: "s", code: "KeyS" })) === "ctrl+s");
check("2.3 Ctrl+Maj+Z : la majuscule ne compte pas deux fois", comboDe(ev({ ctrlKey: true, shiftKey: true, key: "Z", code: "KeyW" })) === "ctrl+shift+z");
check("2.4 Ctrl+Alt+Maj+W", comboDe(ev({ ctrlKey: true, altKey: true, shiftKey: true, key: "W", code: "KeyW" })) === "ctrl+alt+shift+w");
check("2.5 touche morte : repli sur le code physique", comboDe(ev({ ctrlKey: true, key: "Dead", code: "KeyE" })) === "ctrl+e");
check("2.6 Maj+F5", comboDe(ev({ shiftKey: true, key: "F5", code: "F5" })) === "shift+f5");
check("2.7 touche de modification seule : rien", comboDe(ev({ ctrlKey: true, key: "Control", code: "ControlLeft" })) === "");

// 3. quelles combinaisons l'écran prend (les lettres seules restent aux outils)
check("3.1 lettre seule : non (outils)", !aIntercepter("v") && !aIntercepter("q") && !aIntercepter("shift+m"));
check("3.2 Ctrl+lettre : oui", aIntercepter("ctrl+j") && aIntercepter("ctrl+alt+shift+w"));
check("3.3 touche de fonction : oui", aIntercepter("f12") && aIntercepter("shift+f5"));

// 4. index depuis les menus générés (fr ET en : même index malgré « Maj »/« Shift »)
const registre = [{ id: "layer.new.layerViaCopy", params: "{}", enabled: true }, { id: "select.all", params: "{}", enabled: true }];
for (const lang of ["fr", "en"]) {
  const idx = indexRaccourcis(construireMenus(catalogue, registre, REFUSES, lang));
  check("4.1 " + lang + " Ctrl+N -> file.new", (idx.get("ctrl+n") || {}).id === "file.new");
  check("4.2 " + lang + " Ctrl+J -> calque par copie", (idx.get("ctrl+j") || {}).id === "layer.new.layerViaCopy");
  check("4.3 " + lang + " Ctrl+Alt+Maj+W -> exporter", (idx.get("ctrl+alt+shift+w") || {}).id === "file.export.exportAs");
  check("4.4 " + lang + " Ctrl+Maj+N -> nouveau calque", (idx.get("ctrl+shift+n") || {}).id === "layer.new.layer");
  check("4.5 " + lang + " Ctrl+A, Ctrl+D", (idx.get("ctrl+a") || {}).id === "select.all" && (idx.get("ctrl+d") || {}).id === "select.deselect");
}

// 5. ajouts de l'écran : annuler, rétablir, inverser la sélection ; aucun ne masque une combinaison du catalogue
check("5.1 Ctrl+Z annule, Ctrl+Maj+Z rétablit", RACCOURCIS_ECRAN["ctrl+z"] === "edit.undo" && RACCOURCIS_ECRAN["ctrl+shift+z"] === "edit.redo");
check("5.2 Ctrl+Maj+I inverse la sélection", RACCOURCIS_ECRAN["ctrl+shift+i"] === "select.inverse");
const idxFr = indexRaccourcis(construireMenus(catalogue, registre, REFUSES, "fr"));
check("5.3 aucun conflit avec le catalogue", Object.keys(RACCOURCIS_ECRAN).every((k) => !idxFr.has(k)), Object.keys(RACCOURCIS_ECRAN).filter((k) => idxFr.has(k)));

console.log(`raccourcis : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
