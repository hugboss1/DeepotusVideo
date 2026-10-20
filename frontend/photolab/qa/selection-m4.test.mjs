// qa/selection-m4.test.mjs — t253 (Photolab M4, moteur photocraft 0.10) : sélection d'une rangée / d'une colonne, Lasso
// magnétique, Recadrage avec « Contenu pris en compte », Recadrage de perspective, Échantillonneur de couleur, Rotation
// de la vue, Alt-glisser du Déplacement (flotter puis déposer), Sélection › Charger la luminosité.
// Fonctions PURES ; paramètres relevés sur le vrai moteur (backend/tests/test_photolab_m4.py [2]).
import { commandeLigne, pasFrequence, ajouterAttache, commandeMagnetique } from "../js/mod-selection.js";
import { rectRecadrage, redimensionner, commandeRecadrage } from "../js/mod-recadrer.js";
import { ordonnerCoins, convexe, commandePerspective, coinSous, coinsDepuisRect } from "../js/mod-perspective.js";
import { MAX_ECHANTILLONS, positionEchantillon, echantillonProche, actionEchantillon, lectureEchantillon } from "../js/mod-echantillons.js";
import { normaliserAngle, angleGlisser, pointeurTourne, tournerVecteur } from "../js/mod-vue.js";
import { deltaGlisser, commandesDeplacement } from "../js/mod-deplacer.js";
import { EMPLACEMENTS, outilDe, optionsPour, OPTIONS_DEFAUT, outilParLettre } from "../js/mod-outils.js";
import { construireMenus, actionEntree, REFUSES } from "../js/mod-menus.js";
import { ETATS_MOTEUR } from "../js/mod-historique.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const proche = (a, b, e = 1e-9) => Math.abs(a - b) < e;
const DOC = { width: 200, height: 120 };
const OPT = { ...OPTIONS_DEFAUT };

// 1. les six outils, dans les groupes de la référence, actifs
const groupe = (premier) => EMPLACEMENTS.find((e) => e[0].id === premier).map((x) => x.id);
check("1.1 groupe M : Rectangle, Ellipse, Rangée, Colonne (lettre M)", eq(groupe("rectMarquee"), ["rectMarquee", "ellipseMarquee", "rowMarquee", "columnMarquee"])
  && ["rowMarquee", "columnMarquee"].every((id) => outilDe(id).lettre === "M"), groupe("rectMarquee"));
check("1.2 groupe L : Lasso, Lasso polygonal, Lasso magnétique (lettre L)", eq(groupe("lasso"), ["lasso", "polygonLasso", "magneticLasso"])
  && outilDe("magneticLasso").lettre === "L", groupe("lasso"));
check("1.3 groupe C : Recadrage puis Recadrage de perspective, avant les tranches", eq(groupe("crop"), ["crop", "perspectiveCrop", "slice", "sliceSelect"])
  && outilDe("perspectiveCrop").lettre === "C", groupe("crop"));
check("1.4 groupe I : Pipette puis Échantillonneur de couleur", eq(groupe("eyedropper").slice(0, 2), ["eyedropper", "colorSampler"])
  && outilDe("colorSampler").lettre === "I", groupe("eyedropper"));
check("1.5 groupe H : Main puis Rotation de la vue (lettre R)", eq(groupe("hand"), ["hand", "rotateView"]) && outilDe("rotateView").lettre === "R", groupe("hand"));
check("1.6 les six sont actifs, chacun avec une icône de la suite", ["rowMarquee", "columnMarquee", "magneticLasso", "perspectiveCrop", "colorSampler", "rotateView"]
  .every((id) => outilDe(id).p2 === true && /^dz-outil-/.test(outilDe(id).icone)));
check("1.7 R choisit la Rotation de la vue ; M depuis Ellipse -> Rangée -> Colonne -> Rectangle",
  outilParLettre("R", "move", false) === "rotateView" && outilParLettre("M", "ellipseMarquee", false) === "rowMarquee"
  && outilParLettre("M", "rowMarquee", false) === "columnMarquee" && outilParLettre("M", "columnMarquee", false) === "rectMarquee");

// 2. rangée, colonne : le moteur ne prolonge pas la ligne, l'écran envoie toute la largeur / hauteur
let c = commandeLigne(37.6, 40.2, OPT, "replace", "row", DOC);
check("2.1 rangée : select.rect {x:0, y, width: largeur du document, height:1, line:row}", c && c.command === "select.rect"
  && eq(c.params, { x: 0, y: 40, width: 200, height: 1, line: "row", mode: "replace", antiAlias: true, feather: 0 }), c);
c = commandeLigne(70.9, 3, { ...OPT, feather: 2, antiAlias: false }, "add", "column", DOC);
check("2.2 colonne : {x, y:0, width:1, height: hauteur, line:column}, mode et options de la barre", c
  && eq(c.params, { x: 70, y: 0, width: 1, height: 120, line: "column", mode: "add", antiAlias: false, feather: 2 }), c);
check("2.3 hors du document (rangée sous le bas, colonne à gauche) : rien", commandeLigne(10, 120, OPT, "replace", "row", DOC) === null
  && commandeLigne(-0.5, 10, OPT, "replace", "column", DOC) === null && commandeLigne(1, 1, OPT, "replace", "row", null) === null);
check("2.4 une rangée hors largeur mais dans la hauteur reste une rangée (le x ne compte pas)", eq(commandeLigne(-50, 5, OPT, "replace", "row", DOC).params.y, 5));

// 3. Lasso magnétique
check("3.1 options : mode, contour, lissage, largeur, contraste, fréquence ; défauts 10 px, 10 %, 57",
  eq(optionsPour("magneticLasso").map((x) => x.cle).slice(0, 6), ["mode", "feather", "antiAlias", "lassoWidth", "edgeContrast", "frequency"])
  && OPT.lassoWidth === 10 && OPT.edgeContrast === 10 && OPT.frequency === 57, optionsPour("magneticLasso").map((x) => x.cle));
const bornes = Object.fromEntries(optionsPour("magneticLasso").filter((x) => x.type === "nombre").map((x) => [x.cle, [x.min, x.max]]));
check("3.2 bornes du moteur : largeur 1..256, contraste 1..100, fréquence 0..100", eq(bornes.lassoWidth, [1, 256]) && eq(bornes.edgeContrast, [1, 100]) && eq(bornes.frequency, [0, 100]), bornes);
check("3.3 fréquence -> espacement écran des points d'attache : plus fréquent = plus serré, borné", pasFrequence(100) < pasFrequence(57)
  && pasFrequence(57) < pasFrequence(0) && pasFrequence(100) >= 4 && pasFrequence(0) <= 100 && pasFrequence("x") === pasFrequence(57));
let pts = ajouterAttache([], 10.4, 10.6, 1, 20);
pts = ajouterAttache(pts, 20, 10, 1, 20);
check("3.4 un point d'attache n'est posé qu'à `espacement` px écran du précédent (le zoom compte)", eq(pts, [[10, 11]])
  && eq(ajouterAttache(pts, 31, 11, 1, 20), [[10, 11], [31, 11]]) && eq(ajouterAttache(pts, 20, 11, 2, 20), [[10, 11], [20, 11]]));
const P = [[48, 28], [112, 28], [112, 72], [48, 72]];
c = commandeMagnetique(P, { ...OPT, feather: 3 }, "subtract");
check("3.5 select.magneticLasso {points, width, contrast, close:magnetic, trace, mode, antiAlias, feather}", c && c.command === "select.magneticLasso"
  && eq(c.params, { points: P, width: 10, contrast: 10, close: "magnetic", trace: true, mode: "subtract", antiAlias: true, feather: 3 }), c);
check("3.6 fermer en droite (Alt) : close straight", commandeMagnetique(P, OPT, "replace", true).params.close === "straight");
check("3.7 moins de 3 points : désélectionner en mode nouvelle, rien sinon", commandeMagnetique(P.slice(0, 2), OPT, "replace").command === "select.deselect"
  && commandeMagnetique(P.slice(0, 2), OPT, "add") === null);

// 4. Recadrage : « Contenu pris en compte » laisse le cadre sortir du document
check("4.1 options du Recadrage : Supprimer les pixels recadrés, Contenu pris en compte (défaut : non)",
  eq(optionsPour("crop").map((x) => x.cle), ["deleteCroppedPixels", "contentAware"]) && OPT.contentAware === false);
check("4.2 sans l'option, le cadre reste borné au document", eq(rectRecadrage(-10, -10, 210, 130, {}, DOC), { x: 0, y: 0, width: 200, height: 120 }));
check("4.3 avec l'option, il peut l'agrandir", eq(rectRecadrage(-10, -10, 210, 130, {}, DOC, true), { x: -10, y: -10, width: 220, height: 140 }));
check("4.4 une poignée tirée hors du document l'agrandit aussi", eq(redimensionner({ x: 0, y: 0, width: 200, height: 120 }, "se", 230, 140, DOC, true),
  { x: 0, y: 0, width: 230, height: 140 }) && eq(redimensionner({ x: 0, y: 0, width: 200, height: 120 }, "se", 230, 140, DOC), { x: 0, y: 0, width: 200, height: 120 }));
c = commandeRecadrage({ x: -10, y: -10, width: 220, height: 140 }, false, true, true);
check("4.5 image.crop {…, contentAware:true}", c && eq(c.params, { x: -10, y: -10, width: 220, height: 140, deleteCroppedPixels: true, contentAware: true }), c);
c = commandeRecadrage({ x: 1, y: 2, width: 3, height: 4 }, false, false, false);
check("4.6 sans l'option : les paramètres d'avant, inchangés", eq(c.params, { x: 1, y: 2, width: 3, height: 4, deleteCroppedPixels: false }), c);

// 5. Recadrage de perspective
const Q = [[20, 10], [180, 20], [170, 110], [30, 100]];
check("5.1 coins remis dans l'ordre du moteur (haut-gauche, haut-droit, bas-droit, bas-gauche), quel que soit l'ordre des clics",
  eq(ordonnerCoins([Q[2], Q[0], Q[3], Q[1]]), Q) && eq(ordonnerCoins([Q[3], Q[2], Q[1], Q[0]]), Q), ordonnerCoins([Q[2], Q[0], Q[3], Q[1]]));
// le tri par angle commence ici au coin bas-gauche (le plus proche de -180°) : la liste doit être remise au haut-gauche
check("5.1b un bas-gauche haut placé ne prend pas la place du haut-gauche", eq(ordonnerCoins([[100, 100], [0, 30], [100, 0], [0, 0]]), [[0, 0], [100, 0], [100, 100], [0, 30]]),
  ordonnerCoins([[100, 100], [0, 30], [100, 0], [0, 0]]));
check("5.2 convexe : le quadrilatère du banc oui ; un nœud papillon ou un coin rentrant non", convexe(Q)
  && !convexe([[0, 0], [100, 100], [100, 0], [0, 100]]) && !convexe([[0, 0], [100, 0], [50, 20], [50, 100]]) && !convexe(Q.slice(0, 3)));
c = commandePerspective([Q[1], Q[3], Q[0], Q[2]]);
check("5.3 image.perspectiveCrop {corners ordonnés, interpolation bicubic}", c && c.command === "image.perspectiveCrop"
  && eq(c.params, { corners: Q, interpolation: "bicubic" }), c);
check("5.4 coins arrondis au centième ; un coin rentrant ou trois coins : null", eq(commandePerspective([[0.123, 0], [10, 0], [10, 10], [0, 10.456]]).params.corners[0], [0.12, 0])
  && commandePerspective([[0, 0], [100, 0], [50, 20], [50, 100]]) === null && commandePerspective(Q.slice(0, 3)) === null);
check("5.5b des clics « en nœud papillon » sont remis en carré (l'ordre des clics ne compte pas)",
  eq(commandePerspective([[0, 0], [100, 100], [100, 0], [0, 100]]).params.corners, [[0, 0], [100, 0], [100, 100], [0, 100]]));
check("5.5 un glisser pose quatre coins (rectangle)", eq(coinsDepuisRect({ x: 5, y: 6, width: 10, height: 20 }), [[5, 6], [15, 6], [15, 26], [5, 26]]));
const V = { z: 2, ox: 10, oy: 0 };
check("5.6 coin sous le pointeur ÉCRAN (8 px), sinon -1", coinSous(Q, 10 + 180 * 2 + 5, 40 - 6, V) === 1 && coinSous(Q, 0, 0, V) === -1);

// 6. Échantillonneur de couleur
check("6.1 10 points au plus (moteur)", MAX_ECHANTILLONS === 10);
check("6.2 un point se pose au centre du pixel cliqué", eq(positionEchantillon(60.9, 40.1), { x: 60.5, y: 40.5 }));
const L = [{ index: 0, position: [12, 12] }, { index: 1, position: [60.5, 40.5] }];
check("6.3 point sous le pointeur ÉCRAN (6 px), sinon -1", echantillonProche(L, 10 + 60.5 * 2 + 4, 81, V) === 1 && echantillonProche(L, 500, 500, V) === -1);
// relevé à l'écran de preuve : le moteur rend la position ENTIÈRE du pixel ([60, 40] pour un point posé en 60.5, 40.5)
check("6.3b position entière du moteur : le point se montre et se saisit au centre du pixel", echantillonProche([{ index: 0, position: [60, 40] }], 10 + 60.5 * 2, 81, V, 0.01) === 0
  && echantillonProche([{ index: 0, position: [60, 40] }], 10 + 60 * 2, 80, V, 0.01) === -1);
let a = actionEchantillon(L, { x: 100.2, y: 50.7, sx: 0, sy: 0 }, false, DOC, V);
check("6.4 clic ailleurs : view.colorSamplers.add au centre du pixel", eq(a, { type: "ajouter", command: "view.colorSamplers.add", params: { x: 100.5, y: 50.5 } }), a);
a = actionEchantillon(L, { x: 60, y: 40, sx: 10 + 121, sy: 81 }, false, DOC, V);
check("6.5 clic sur un point : le saisir pour le déplacer", eq(a, { type: "saisir", index: 1 }), a);
a = actionEchantillon(L, { x: 60, y: 40, sx: 10 + 121, sy: 81 }, true, DOC, V);
check("6.6 Alt+clic sur un point : view.colorSamplers.delete {index}", eq(a, { type: "supprimer", command: "view.colorSamplers.delete", params: { index: 1 } }), a);
const dix = Array.from({ length: 10 }, (_, i) => ({ index: i, position: [i * 10 + 0.5, 0.5] }));
check("6.7 au dixième point, ou hors du document : un message, aucune commande", actionEchantillon(dix, { x: 150, y: 90, sx: 900, sy: 900 }, false, DOC, V).type === "plein"
  && actionEchantillon(L, { x: 250, y: 50, sx: 900, sy: 900 }, false, DOC, V) === null && actionEchantillon(L, { x: 5, y: 5, sx: 900, sy: 900 }, true, DOC, V) === null);
const lu = lectureEchantillon({ index: 0, number: 1, position: [12, 12], rgb: [32, 64, 255], cmyk: [87, 75, 0, 0] });
check("6.8 lecture : numéro, R/V/B 0..255, C/M/J/N en %", eq(lu, { numero: 1, r: 32, v: 64, b: 255, c: 87, m: 75, j: 0, n: 0 }), lu);
check("6.9 lecture d'un point incomplet : null", lectureEchantillon({ number: 2 }) === null && lectureEchantillon(null) === null);
check("6.10 l'outil a le bouton « Tout effacer »", optionsPour("colorSampler").some((x) => x.type === "bouton" && x.action === "pl.echantillons.effacer"));

// 7. Rotation de la vue
check("7.1 angle ramené dans ]-180, 180]", normaliserAngle(190) === -170 && normaliserAngle(-180) === 180 && normaliserAngle(540) === 180 && normaliserAngle(0) === 0 && normaliserAngle("x") === 0);
const ctr = { x: 100, y: 100 };
check("7.2 glisser d'un quart de tour autour du centre : +90°", proche(angleGlisser(ctr, { x: 200, y: 100 }, { x: 100, y: 200 }, 0, false), 90));
check("7.3 Maj : par pas de 15° ; on part de l'angle déjà posé", angleGlisser(ctr, { x: 200, y: 100 }, { x: 200, y: 120 }, 30, true) === 45
  && proche(angleGlisser(ctr, { x: 200, y: 100 }, { x: 100, y: 0 }, 0, false), -90));
let lp = pointeurTourne(150, 50, { left: 0, top: 0, width: 200, height: 100 }, 200, 100, 0);
check("7.4 sans rotation : le point client est le point local", eq(lp, { x: 150, y: 50 }), lp);
// canevas 200 × 100 tourné de 90° : sa boîte englobante fait 100 × 200, centrée au même point (100, 50) -> rect {50, -50, 100, 200}
lp = pointeurTourne(100, 0, { left: 50, top: -50, width: 100, height: 200 }, 200, 100, 90);
check("7.5 tourné de 90° : un point au-dessus du centre est, dans le canevas, à gauche du centre", proche(lp.x, 50) && proche(lp.y, 50), lp);
const tv = tournerVecteur(10, 0, 90);
check("7.6 vecteur tourné de 90° (y vers le bas : sens horaire)", proche(tv.dx, 0) && proche(tv.dy, 10), tv);
check("7.7 l'outil a l'angle (lié à la vue, pas rangé) et « Réinitialiser la vue »", optionsPour("rotateView").some((x) => x.cle === "rotationVue" && x.doc && x.min === -180 && x.max === 180)
  && optionsPour("rotateView").some((x) => x.type === "bouton" && x.action === "pl.vue.reinitialiserRotation"));

// 8. Déplacement : le glisser suit la vue tournée ; Alt-glisser d'une sélection flotte une copie puis la dépose
let dg = deltaGlisser({ clientX: 0, clientY: 0 }, { clientX: 0, clientY: 20 }, 2, false, 90);
check("8.1 vue tournée de 90° (sens horaire) : l'axe x du document pointe vers le bas, glisser vers le bas = +x", proche(dg.dx, 10) && proche(dg.dy, 0), dg);
dg = deltaGlisser({ clientX: 0, clientY: 0 }, { clientX: 20, clientY: 10 }, 2);
check("8.2 sans rotation : inchangé", eq(dg, { dx: 10, dy: 5 }), dg);
let cs = commandesDeplacement(true, true, 30.4, -9.6, 3);
check("8.3 Alt + sélection : select.float {dx, dy, copy:true} puis select.drop (un seul état « Déplacement »)",
  eq(cs, [{ command: "select.float", params: { dx: 30, dy: -10, copy: true } }, { command: "select.drop", params: {} }]), cs);
cs = commandesDeplacement(true, false, 3, 0, 3);
check("8.4 sans Alt : edit.transform comme avant", eq(cs, [{ command: "edit.transform", params: { matrix: [1, 0, 0, 1, 3, 0] } }]), cs);
check("8.5 Alt sans sélection : le calque bouge (layer.translate), rien ne bouge : aucune commande",
  eq(commandesDeplacement(false, true, 2, 1, 4), [{ command: "layer.translate", params: { layer: 4, dx: 2, dy: 1 } }]) && eq(commandesDeplacement(true, true, 0.2, 0.3, 4), []));

// 9. Sélection › Charger la luminosité (Ctrl+Alt+2), juste après « Charger la sélection… »
const registre = [{ id: "select.loadSelection", enabled: true, champs: [] }, { id: "select.loadLuminosity", enabled: true, champs: [] }];
const catalogue = { entrees: [{ chemin: ["Select"], id: "select.loadSelection", libelle_fr: "Charger la sélection…", libelle_en: "Load Selection…", raccourci: null }] };
const menus = construireMenus(catalogue, registre, REFUSES, "fr", (kk) => kk);
const sel = menus.find((m) => m.nom === "Select");
const k = sel ? sel.entrees.findIndex((e) => e.id === "select.loadLuminosity") : -1;
check("9.1 l'entrée suit « Charger la sélection… », active, raccourci Ctrl+Alt+2", k > 0 && sel.entrees[k - 1].id === "select.loadSelection"
  && sel.entrees[k].etat === "actif" && sel.entrees[k].raccourci === "Ctrl+Alt+2" && sel.entrees[k].libelle === "photolab.menu.charger_luminosite", sel && sel.entrees);
check("9.2 elle s'exécute directement (aucun champ)", k > 0 && actionEntree(sel.entrees[k]) === "executer");
const sansMoteur = construireMenus(catalogue, [{ id: "select.loadSelection", enabled: true, champs: [] }], REFUSES, "fr", (kk) => kk);
const e2 = sansMoteur.find((m) => m.nom === "Select").entrees.find((e) => e.id === "select.loadLuminosity");
check("9.3 moteur sans la commande : l'entrée reste visible, « bientôt »", e2 && e2.etat === "bientot", e2);

// 10. noms d'historique traduits
for (const n of ["Magnetic Lasso", "Single Row Marquee", "Single Column Marquee", "Load Selection", "Perspective Crop"]) {
  check(`10 « ${n} » a une clé dans ETATS_MOTEUR`, /^photolab\./.test(ETATS_MOTEUR[n] || ""), ETATS_MOTEUR[n]);
}

console.log(`selection-m4 : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
