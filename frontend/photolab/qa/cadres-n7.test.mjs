// qa/cadres-n7.test.mjs — t417 (Photolab N7, photocraft 0.21) : Calque › Cadre. Fonctions PURES ; moteur prouvé par backend/tests/test_photolab_n7.py.
import { IDS_CADRE, LIBELLES_CADRE, peutAjuster, cadreActif, decorerCadres, contenusPossibles, champsCadre, commandeCadre } from "../js/mod-cadres.js";
import { construireMenus, actionEntree, REFUSES, TRAITES_PAR_ECRAN, NECESSITE_DOC } from "../js/mod-menus.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const catalogue = JSON.parse(readFileSync(new URL("../donnees/menus.json", import.meta.url), "utf8"));
const T = (c) => (dico[c] ? dico[c].fr : c);
const menus = construireMenus(catalogue, [], REFUSES, "fr", T);
const trouver = (l, id) => { for (const e of l) { if (e.id === id) return e; if (e.entrees) { const f = trouver(e.entrees, id); if (f) return f; } } return null; };
const calque = menus.find((m) => m.nom === "Layer");
const sm = calque.entrees.find((e) => e.nom === "Frame");

check("1.1 un sous-menu Cadre, en cinq entrées", sm && eq(sm.entrees.map((e) => e.id), IDS_CADRE), sm);
check("1.2 son nom français", sm.nom_affiche === "Cadre");
check("1.3 des entrées de l'écran, document requis", IDS_CADRE.every((id) => TRAITES_PAR_ECRAN.has(id) && NECESSITE_DOC.has(id) && actionEntree(trouver(menus, id)) === "ecran"));
check("1.4 libellés français", sm.entrees.every((e) => e.libelle && !e.libelle.startsWith("photolab.")));

check("2.1 Convertir : forme ou texte", cadreActif("pl.cadre.convertir", { kind: "Shape" }) && cadreActif("pl.cadre.convertir", { kind: "Type" }) && !cadreActif("pl.cadre.convertir", { kind: "Pixel" }));
check("2.2 le reste : un groupe", cadreActif("pl.cadre.proprietes", { kind: "Group" }) && !cadreActif("pl.cadre.proprietes", { kind: "Pixel" }));
check("2.3 sans calque : rien", !cadreActif("pl.cadre.contenu", null));
const d = decorerCadres(menus, { kind: "Group" });
check("2.4 décor", trouver(d, "pl.cadre.proprietes").etat === "actif" && trouver(d, "pl.cadre.convertir").etat === "inactif");

check("2.5 un cadre vide ne s'ajuste pas", peutAjuster({ content: null }) === false && peutAjuster({ content: 4 }) === true && peutAjuster({ content: 0 }) === true);
const doc = { layers: [{ id: 1, name: "c", kind: "Group" }, { id: 2, name: "a", kind: "Pixel" }, { id: 3, name: "b", kind: "Shape" }] };
check("3.1 le cadre ne se contient pas lui-même", eq(contenusPossibles(doc, 1).map((x) => x.valeur), [2, 3]));
const info = { layer: 4, name: "F", frame: [1, 2, 30, 40], transform: [30, 0.5, -0.5, 40, 1, 2], stroke: { width: 3 } };
check("3.2 les champs partent de la fiche", eq(champsCadre(info).map((c) => c.defaut), ["F", 1, 2, 30, 40, 3]));
check("3.3 sans contour : 0", champsCadre({ ...info, stroke: null })[5].defaut === 0);
const c = commandeCadre(info, { name: "G", x: 5, y: 6, largeur: 70, hauteur: 80, contour: 2 }, "#123456");
check("3.4 matrice : position et taille, rotation gardée", eq(c.params.transform, [70, 0.5, -0.5, 80, 5, 6]) && c.params.layer === 4 && c.params.name === "G", c);
check("3.5 contour : couleur de premier plan", eq(c.params.stroke, { width: 2, color: "#123456" }));
check("3.6 contour 0 : retiré", commandeCadre(info, { name: "G", x: 5, y: 6, largeur: 7, hauteur: 8, contour: 0 }, "#000000").params.stroke === null);
check("3.7 nom vide : l'ancien", commandeCadre(info, { name: "", x: 0, y: 0, largeur: 1, hauteur: 1, contour: 0 }, "#000000").params.name === "F");

for (const c2 of [...Object.values(LIBELLES_CADRE), "photolab.menu.cadre_sous_menu", "photolab.cadre.pas_un_cadre", "photolab.cadre.vide", "photolab.cadre.aucun_contenu", "photolab.cadre.calque_contenu",
  "photolab.cadre.nom", "photolab.cadre.x", "photolab.cadre.y", "photolab.cadre.largeur", "photolab.cadre.hauteur", "photolab.cadre.contour"]) check(`4.1 ${c2} fr et en`, dico[c2]?.fr && dico[c2]?.en, c2);

console.log(`cadres-n7 : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
