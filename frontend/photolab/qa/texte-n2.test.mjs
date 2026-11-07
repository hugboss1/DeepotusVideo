// qa/texte-n2.test.mjs — t412 (Photolab N2, photocraft 0.21) : sous-menus Chiffres et Jeux stylistiques, Texte dans une
// forme, polices favorites. Fonctions PURES ; le moteur est prouvé par backend/tests/test_photolab_n2.py.
import { construireMenus, actionEntree, TRAITES_PAR_ECRAN, NECESSITE_DOC, REFUSES, IDS_CHIFFRES, IDS_JEUX, SOUS_MENUS_N2 } from "../js/mod-menus.js";
import { cocheOpenType, decorerTexte, ordonnerPolices, basculerFavori, choixFormes } from "../js/mod-texte.js";
import { LIBELLES_COMMANDES } from "../js/mod-libelles.js";
import { traduireEtat } from "../js/mod-historique.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const catalogue = JSON.parse(readFileSync(new URL("../donnees/menus.json", import.meta.url), "utf8"));
const T = (c, v) => (dico[c] ? dico[c].fr.replace("{nom}", v?.nom ?? "") : c);
// `on` et `range` : les champs réels des jeux stylistiques (registre 0.21) ; ils ne doivent pas ouvrir de dialogue.
const reg = [...IDS_CHIFFRES, ...IDS_JEUX, "type.fillPath"].map((id) => ({ id, enabled: true, champs: [{ cle: "on", type: "bool", optionnel: true }, { cle: "range", type: "struct", optionnel: true }] }));
reg.push({ id: "type.openType.swash", enabled: true, champs: [] });
const trouver = (l, id) => { for (const e of l) { if (e.id === id) return e; if (e.entrees) { const f = trouver(e.entrees, id); if (f) return f; } } return null; };
const menus = construireMenus(catalogue, reg, REFUSES, "fr", T);
const texte = menus.find((m) => m.nom === "Type");
const ot = texte.entrees.find((e) => e.nom === "OpenType");
const sm = (n) => ot.entrees.find((e) => e.nom === n);

check("1.1 9 styles de chiffres, 20 jeux", IDS_CHIFFRES.length === 9 && IDS_JEUX.length === 20);
check("1.2 deux sous-menus sous OpenType, dans l'ordre", sm("Numerals") && sm("Stylistic Sets")
  && eq(sm("Numerals").entrees.map((e) => e.id), IDS_CHIFFRES) && eq(sm("Stylistic Sets").entrees.map((e) => e.id), IDS_JEUX), ot.entrees.map((e) => e.nom || e.id));
check("1.3 noms français", sm("Numerals").nom_affiche === "Chiffres" && sm("Stylistic Sets").nom_affiche === "Jeux stylistiques");
check("1.4 chaque entrée a son libellé, sans clé brute", [...sm("Numerals").entrees, ...sm("Stylistic Sets").entrees].every((e) => e.libelle && !e.libelle.startsWith("photolab.")));
check("1.5 elles s'exécutent directement", [...sm("Numerals").entrees, ...sm("Stylistic Sets").entrees].every((e) => actionEntree(e) === "executer"), sm("Numerals").entrees[0]);
check("1.6 SOUS_MENUS_N2 décrit ces deux sous-menus", SOUS_MENUS_N2.length === 2);
check("1.7 chaque commande est au tableau des libellés", [...IDS_CHIFFRES, ...IDS_JEUX, "type.fillPath"].every((id) => LIBELLES_COMMANDES[id]));

const info = (tags) => ({ runs: [{ style: { features: tags.map((tag) => ({ tag, value: 1 })) } }] });
check("2.1 oldstyle coché sur onum seul", cocheOpenType("type.openType.numerals.oldstyle", info(["onum"])) === true);
check("2.2 mais pas sur onum + tnum", cocheOpenType("type.openType.numerals.oldstyle", info(["onum", "tnum"])) === false);
check("2.3 tabulaires elzéviriens : onum + tnum", cocheOpenType("type.openType.numerals.tabularOldstyle", info(["onum", "tnum"])) === true);
check("2.4 Par défaut : aucun trait de chiffres", cocheOpenType("type.openType.numerals.default", info(["swsh"])) === true && cocheOpenType("type.openType.numerals.default", info(["lnum"])) === false);
check("2.5 un autre trait ne gêne pas", cocheOpenType("type.openType.numerals.lining", info(["swsh", "lnum"])) === true);
check("2.6 jeu 3 : ss03, jeu 13 : ss13", cocheOpenType("type.openType.stylisticSets.set3", info(["ss03"])) === true && cocheOpenType("type.openType.stylisticSets.set13", info(["ss13"])) === true);
check("2.7 un jeu n'est coché que s'il l'est sur tout le texte", cocheOpenType("type.openType.stylisticSets.set1", { runs: [...info(["ss01"]).runs, ...info([]).runs] }) === false);
check("2.8 sans calque de texte : pas de coche", cocheOpenType("type.openType.stylisticSets.set1", null) === false);
check("2.9 autre entrée : sans objet", cocheOpenType("type.fillPath", info(["ss01"])) === undefined);
const deco = decorerTexte(menus, {}, info(["onum"]));
check("2.10 decorerTexte pose la coche", trouver(deco, "type.openType.numerals.oldstyle").coche === true && !trouver(deco, "type.openType.numerals.lining").coche);
check("2.11 Texte dans une forme grisé sans calque de texte", trouver(decorerTexte(menus, {}, null), "type.fillPath").etat === "inactif");
check("2.11b calque de texte encore sans type.info : actif quand même", trouver(decorerTexte(menus, {}, null, true), "type.fillPath").etat === "actif");
check("2.12 actif sur un calque de texte", trouver(deco, "type.fillPath").etat === "actif");

check("3.1 Texte dans une forme : écran, document requis", TRAITES_PAR_ECRAN.has("type.fillPath") && NECESSITE_DOC.has("type.fillPath"));
check("3.2 proposé dans le menu Texte", !!trouver([texte], "type.fillPath"));
const doc = { layers: [{ id: 1, kind: "Type", name: "t" }, { id: 2, kind: "Shape", name: "Ellipse" }, { id: 3, kind: "Group", name: "g", children: [{ id: 4, kind: "Shape", name: "Rect" }] }, { id: 5, kind: "Pixel", name: "p" }] };
check("3.3 choix : tracé de travail puis formes, sous-groupes compris", eq(choixFormes(doc, true, (k) => k).map((x) => x.valeur), ["", 2, 4]), choixFormes(doc, true, (k) => k));
check("3.4 sans tracé de travail : les formes seules", eq(choixFormes(doc, false, (k) => k).map((x) => x.valeur), [2, 4]));
check("3.5 rien de possible : liste vide", eq(choixFormes({ layers: [] }, false, (k) => k), []));

check("4.1 favoris d'abord, chacun dans son ordre", eq(ordonnerPolices(["Arial", "Inter", "Zed"], ["Zed"], ""), ["Zed", "Arial", "Inter"]));
check("4.2 la recherche vaut aussi pour les favoris", eq(ordonnerPolices(["Arial", "Inter", "Zed"], ["Zed"], "in"), ["Inter"]));
check("4.3 un favori absent du poste n'apparaît pas", eq(ordonnerPolices(["Arial"], ["Zed"], ""), ["Arial"]));
check("4.4 bascule", eq(basculerFavori(["A"], "B"), ["A", "B"]) && eq(basculerFavori(["A", "B"], "A"), ["B"]));

check("5.1 états traduits", traduireEtat("Area Type", null, T) === dico["photolab.commande.type.fill_path"].fr
  && traduireEtat("Change OpenType Numerals", null, T) === dico["photolab.historique.opentype_chiffres"].fr
  && traduireEtat("Change OpenType Feature", null, T) === dico["photolab.historique.opentype_trait"].fr);
for (const c of ["photolab.menu.chiffres", "photolab.menu.jeux_stylistiques", "photolab.texte.favori", "photolab.texte.forme_cible", "photolab.texte.aucune_forme"])
  check(`5.2 ${c} fr et en`, dico[c]?.fr && dico[c]?.en, c);

console.log(`texte-n2 : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
