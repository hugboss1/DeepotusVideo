// qa/textes.test.mjs — textes (C4) : les clés du dictionnaire COMPOSÉES à l'exécution (outils, options, préréglages,
// modes de fusion, verrous, types de calque) existent toutes, en fr et en en. Les clés écrites en toutes lettres et
// l'absence de français hors dictionnaire sont vérifiées par backend/tests/test_photolab_textes.py (relevé du skill).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { EMPLACEMENTS, cleNom, optionsPour } from "../js/mod-outils.js";
import { PRESETS, CATEGORIES } from "../js/mod-fichier.js";
import { MODES_FUSION, MODE_TRANSFERT, VERROUS } from "../js/mod-calques.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const dico = {
  ...JSON.parse(readFileSync(join(racine, "../shared/i18n/commun.json"), "utf8")),
  ...JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8")),
};
const present = (k) => !!(dico[k] && dico[k].fr && dico[k].en);
const manque = (cles) => cles.filter((k) => !present(k));

const outils = EMPLACEMENTS.flat();
check("1 un nom par outil (20 emplacements, tous les outils)", !manque(outils.map((o) => cleNom(o.id))).length, manque(outils.map((o) => cleNom(o.id))));
const opts = outils.flatMap((o) => optionsPour(o.id));
const clesOptions = opts.flatMap((o) => [o.libelle, ...(o.valeurs || []).map((v) => o.libelle + "." + v)]);
check("2 options et leurs valeurs", !manque(clesOptions).length, manque(clesOptions));
check("3 préréglages et catégories", !manque([...PRESETS.map((p) => p.cle), ...CATEGORIES.map((c) => "photolab.nouveau.categorie." + c)]).length);
check("4 modes de fusion", !manque([...MODES_FUSION, MODE_TRANSFERT].map((m) => m.cle)).length);
check("5 verrous", !manque(VERROUS.map((v) => v.cle_libelle)).length);
// Types rendus par doc.inspect (relevés : Pixel, Group) et ceux que photocraft annonce ; un type inconnu s'affiche brut.
const types = ["pixel", "group", "text", "shape", "adjustment", "fill", "smartobject"].map((k) => "photolab.type_calque." + k);
check("6 types de calque", !manque(types).length, manque(types));
// 2.4 de test_i18n_l0 vu d'ici : un même texte français n'a qu'UNE traduction anglaise (sinon la surcouche hésite).
const fr = new Map();
for (const [k, v] of Object.entries(dico)) { if (!fr.has(v.fr)) fr.set(v.fr, new Set()); fr.get(v.fr).add(v.en); }
const ambigus = [...fr].filter(([, s]) => s.size > 1).map(([f]) => f);
check("7 aucun texte français à deux traductions", !ambigus.length, ambigus);

// 8. données de l'utilisateur jamais traduites par la surcouche (data-dz-brut) : nom de calque (liste, Propriétés),
//    nom de fichier (grille de repli de la Bibliothèque), nom du document (onglet). Lecture statique des chemins de code.
const src = (f) => readFileSync(join(racine, "js", f), "utf8");
const brutOk = [
  ["mod-calques.js : nom de calque", /brut\(el\("span", "cq-nom"/.test(src("mod-calques.js"))],
  ["mod-proprietes.js : ligne Nom marquée", /valeur: c\.name \|\| "", brut: true/.test(src("mod-proprietes.js")) && /if \(l\.brut\) brut\(dd\)/.test(src("mod-proprietes.js"))],
  ["mod-fichier.js : carte de la grille", /brut\(document\.createElement\("button"\)\);[^\n]*lib-carte/.test(src("mod-fichier.js"))],
  // t158 : les onglets (un par document de la session) sont dessinés par mod-documents
  ["mod-documents.js : onglet du document", /function dessiner\(\)[\s\S]{0,1200}brut\(document\.createElement\("span"\)\)/.test(src("mod-documents.js"))],
  ["mod-documents.js : noms des documents dans les listes de choix", /nonTraduit\(document\.createElement\("option"\)\)/.test(src("mod-dialogue-reglage.js"))],
  ["mod-cycle.js : brut pose data-dz-brut", /setAttribute\("data-dz-brut", "1"\)/.test(src("mod-cycle.js"))],
];
for (const [nom, okb] of brutOk) check("8 " + nom, okb);
check("8.1 le runtime honore data-dz-brut", /data-dz-brut/.test(readFileSync(join(racine, "../shared/dz-i18n.js"), "utf8")));

// 9. bouton « Ajustements » du rail (mot de photocraft) : sa propre clé — « Réglages » se traduisait « Settings » par la
//    clé commune, faux pour ce panneau.
const html = readFileSync(join(racine, "index.html"), "utf8");
check("9.1 index.html : le bouton porte « Ajustements »", /data-panneau="reglages"[^>]*title="Ajustements"[^>]*aria-label="Ajustements"/.test(html));
check("9.2 core.js le nomme par photolab.rail.ajustements", /"photolab\.rail\.ajustements"/.test(src("core.js")) && !/photolab\.rail\.reglages/.test(src("core.js")));
check("9.3 dictionnaire : Ajustements / Adjustments, l'ancienne clé retirée",
  dico["photolab.rail.ajustements"] && dico["photolab.rail.ajustements"].fr === "Ajustements" && dico["photolab.rail.ajustements"].en === "Adjustments"
  && !dico["photolab.rail.reglages"]);

// 10. familles composées de P3 (B3) : photolab.param.<cle>, photolab.valeur.<v>, photolab.kind.<kind>. Les clés
//     viennent du dictionnaire lui-même (la liste des clés visibles du périmètre est calculée par
//     backend/tests/test_photolab_libelles.py avec mod-champs.js) ; ici on tient la forme : fr ET en non vides, un
//     libellé jamais recopié de la clé brute, et chaque kind de calque de réglage du catalogue y est.
const famille = (pre) => Object.keys(dico).filter((k) => k.startsWith(pre));
for (const pre of ["photolab.param.", "photolab.valeur.", "photolab.kind."]) {
  const cles = famille(pre);
  check("10 famille " + pre + " non vide", cles.length > 10, cles.length);
  check("10 famille " + pre + " : fr et en non vides", !manque(cles).length, manque(cles));
  const brut = cles.filter((k) => /[a-z][A-Z]/.test(dico[k].fr) || /[a-z][A-Z]/.test(dico[k].en));
  check("10 famille " + pre + " : aucun libellé en camelCase brut", !brut.length, brut);
}
const menus = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));
const kindsCatalogue = menus.entrees.map((e) => e.id || "").filter((i) => i.startsWith("layer.newAdjustmentLayer.")).map((i) => i.slice("layer.newAdjustmentLayer.".length));
check("10 les 16 réglages du catalogue ont leur photolab.kind.*", kindsCatalogue.length === 16 && !manque(kindsCatalogue.map((k) => "photolab.kind." + k.toLowerCase())).length, kindsCatalogue);
check("10 le nom d'un réglage est celui du catalogue (sans « … »)", kindsCatalogue.every((k) => {
  const e = menus.entrees.find((x) => x.id === "layer.newAdjustmentLayer." + k);
  return dico["photolab.kind." + k.toLowerCase()].fr === e.libelle_fr.replace(/…$/, "") && dico["photolab.kind." + k.toLowerCase()].en === e.libelle_en.replace(/…$/, "");
}));
// Les modes de fusion gardent leurs libellés photolab.fusion.* : aucune valeur de fusion dupliquée sous photolab.valeur.*.
const fusions = new Set(MODES_FUSION.map((m) => m.id.toLowerCase()));
const doublons = famille("photolab.valeur.").map((k) => k.slice("photolab.valeur.".length)).filter((v) => fusions.has(v) && !["color", "hue", "saturation", "luminosity"].includes(v) && v !== "normal");
check("10 pas de mode de fusion dupliqué sous photolab.valeur.*", !doublons.length, doublons);

console.log(`textes :${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
