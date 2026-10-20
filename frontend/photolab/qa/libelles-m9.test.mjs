// qa/libelles-m9.test.mjs — t258 (Photolab M9, moteur photocraft 0.10) : libellé d'une commande hors de l'arbre des
// menus. Ordre : catalogue (nos libellés) -> nos clés (LIBELLES_COMMANDES) -> repli de l'amont (menus.json `repli`,
// fr.tsv v0.10.0) -> id brut. Étapes du panneau Actions et états de l'Historique. Fonctions PURES.
import { LIBELLES_COMMANDES, libelleCommande, indexRepli } from "../js/mod-libelles.js";
import { libelleEtape, indexCatalogue } from "../js/mod-actions.js";
import { tableEtats, traduireEtat } from "../js/mod-historique.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const menus = JSON.parse(readFileSync(new URL("../donnees/menus.json", import.meta.url), "utf8"));
const dzT = (lang) => (c) => (dico[c] ? dico[c][lang] : c);

// 1. ordre de résolution, sur un catalogue témoin
const cat = indexCatalogue({
  entrees: [{ chemin: ["Filter", "Blur"], id: "filter.blur.gaussianBlur", libelle_fr: "Flou gaussien…", libelle_en: "Gaussian Blur…" },
    { chemin: ["Layer"], id: "paint.patch", libelle_fr: "Pièce (catalogue)", libelle_en: "Patch (catalogue)" }],
  repli: { "paint.redEye": { libelle_en: "Red Eye", libelle_fr: "Yeux rouges" }, "layer.select": { libelle_en: "Select Layer" },
    "select.rect": { libelle_en: "Rectangular Selection", libelle_fr: "Sélection rectangulaire…" } },
});
check("1.1 indexCatalogue porte le repli à part : get() ne rend que l'arbre", cat.get("paint.redEye") === undefined && cat.repli.get("paint.redEye").libelle_fr === "Yeux rouges");
check("1.2 le catalogue d'abord, même si nous avons une clé (nos libellés existants restent)",
  eq(libelleCommande("paint.patch", cat, "fr", dzT("fr")), { texte: "Pièce (catalogue)" }));
check("1.3 puis notre clé, devant le repli de l'amont (Œil rouge, pas « Yeux rouges »)",
  eq(libelleCommande("paint.redEye", cat, "fr", dzT("fr")), { texte: "Œil rouge" }) && eq(libelleCommande("paint.redEye", cat, "en", dzT("en")), { texte: "Red Eye" }));
check("1.4 sans traducteur ou clé absente du dictionnaire : le repli de l'amont, marqué",
  eq(libelleCommande("paint.redEye", cat, "fr", (c) => c), { texte: "Yeux rouges", amont: true }));
check("1.5 repli sans français : l'id brut en fr, le libellé du moteur en en",
  eq(libelleCommande("layer.select", cat, "fr", dzT("fr")), { texte: "layer.select", brut: true })
  && eq(libelleCommande("layer.select", cat, "en", dzT("en")), { texte: "Select Layer", amont: true }));
check("1.6 « … » final retiré (étape d'action, pas une entrée de menu)", libelleCommande("select.rect", cat, "fr").texte === "Sélection rectangulaire");
check("1.7 inconnue partout : l'id brut", eq(libelleCommande("zz.inconnue", cat, "en", dzT("en")), { texte: "zz.inconnue", brut: true }));
check("1.8 sans catalogue (pas encore chargé) : notre clé, sinon l'id", libelleCommande("select.float", null, "fr", dzT("fr")).texte === "Rendre la sélection flottante"
  && eq(libelleCommande("select.float", null, "fr"), { texte: "select.float", brut: true }));
check("1.9 indexRepli : vide sans section repli", indexRepli({}).size === 0 && indexRepli(null).size === 0);

// 2. étapes du panneau Actions : même ordre, les étapes propres aux actions gardent leur traitement
const vrai = indexCatalogue(menus);
check("2.1 étape d'une commande ouverte par M3 : notre libellé dans les deux langues",
  libelleEtape({ id: "paint.patch", params: {} }, vrai, "fr", dzT("fr")).texte === "Pièce" && libelleEtape({ id: "paint.patch", params: {} }, vrai, "en", dzT("en")).texte === "Patch");
check("2.2 étape d'une commande du catalogue : inchangée", libelleEtape({ id: "filter.blur.gaussianBlur", params: {} }, vrai, "fr", dzT("fr")).texte === "Flou gaussien");
check("2.3 l'étape .atn sans équivalent garde son nom brut", eq(libelleEtape({ id: "actions.photoshopStep", params: { name: "Truc" } }, vrai, "fr", dzT("fr")),
  { texte: "Truc", brut: true, sansEquivalent: true }));
check("2.4 commande de 0.3.0 hors arbre traduite par l'amont (repli) quand nous n'avons rien",
  (() => { const [id, v] = Object.entries(menus.repli).find(([i, x]) => x.libelle_fr && !LIBELLES_COMMANDES[i]) || []; return id && eq(libelleEtape({ id, params: {} }, vrai, "fr", dzT("fr")), { texte: v.libelle_fr.replace(/…$/, "").trim(), amont: true }); })());

// 3. Historique : la table fr reprend le repli APRÈS le catalogue ; ETATS_MOTEUR reste devant
const table = tableEtats({ entrees: [{ id: "a.b", libelle_en: "Patch", libelle_fr: "Rapiécer" }], repli: { "c.d": { libelle_en: "Patch", libelle_fr: "Pièce amont" }, "e.f": { libelle_en: "New Snapshot", libelle_fr: "Nouvel instantané" }, "g.h": { libelle_en: "Only En" } } });
check("3.1 le catalogue l'emporte sur le repli pour un même nom anglais", table.get("Patch") === "Rapiécer");
check("3.2 un nom absent du catalogue prend la traduction de l'amont", table.get("New Snapshot") === "Nouvel instantané" && !table.has("Only En"));
check("3.3 ETATS_MOTEUR (dictionnaire) passe devant la table", traduireEtat("Patch", table, dzT("fr")) === "Pièce");
check("3.4 la vraie table : un état neuf de 0.10 sans clé chez nous se lit en français",
  (() => { const t = tableEtats(menus); return t.size > tableEtats({ entrees: menus.entrees }).size; })());

// 4. nos clés : toutes au dictionnaire, fr et en non vides
const absentes = Object.entries(LIBELLES_COMMANDES).filter(([, c]) => !dico[c] || !String(dico[c].fr).trim() || !String(dico[c].en).trim());
check("4.1 chaque clé de LIBELLES_COMMANDES existe en fr et en", absentes.length === 0, absentes);
check("4.2 aucune de nos commandes n'est dans l'arbre (le catalogue l'emporterait : clé morte)",
  Object.keys(LIBELLES_COMMANDES).filter((id) => menus.entrees.some((e) => e.id === id)).length === 0);
check("4.3 aucun libellé de repli ne nomme Photoshop (D8)", !JSON.stringify(menus.repli).includes("Photoshop"));

console.log(`libelles-m9 : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
