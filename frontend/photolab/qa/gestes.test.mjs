// qa/gestes.test.mjs — outils du canevas (C3) : sélections, déplacement, recadrage, pipette, contour de sélection.
// Chaque geste validé devient UNE commande moteur ; ces fonctions PURES fabriquent la commande à partir du geste.
import { rectDepuisGlisser, modeSelection, fermeturePolygone, ajouterPoint, commandeRect, commandeLasso, commandeBaguette,
  commandeRapide } from "../js/mod-selection.js";
import { deplacementCommande, contrainteAxe, pasFleche, deltaGlisser, cumulerPas } from "../js/mod-deplacer.js";
import { rectRecadrage, poigneeSous, redimensionner, commandeRecadrage } from "../js/mod-recadrer.js";
import { pixelDans, commandeCouleur } from "../js/mod-pipette.js";
import { formeFourmis } from "../js/mod-gestes.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const json = (x) => JSON.stringify(x);
const opts = { mode: "replace", feather: 0, antiAlias: true, tolerance: 32, contiguous: true, sampleAllLayers: false, size: 30, deleteCroppedPixels: true };

// 1. rectangle depuis un glisser
check("1.1 glisser simple", json(rectDepuisGlisser(10, 20, 110, 70)) === json({ x: 10, y: 20, width: 100, height: 50 }));
check("1.2 glisser à rebours", json(rectDepuisGlisser(110, 70, 10, 20)) === json({ x: 10, y: 20, width: 100, height: 50 }));
check("1.3 entiers (bords arrondis)", json(rectDepuisGlisser(10.4, 20.6, 50.5, 60.2)) === json({ x: 10, y: 21, width: 41, height: 39 }));
check("1.4 carré (Maj) : le plus grand côté", json(rectDepuisGlisser(0, 0, 100, 40, { carre: true })) === json({ x: 0, y: 0, width: 100, height: 100 }));
check("1.5 carré vers le haut-gauche", json(rectDepuisGlisser(100, 100, 60, 90, { carre: true })) === json({ x: 60, y: 60, width: 40, height: 40 }));
check("1.6 depuis le centre (Alt)", json(rectDepuisGlisser(50, 50, 70, 60, { centre: true })) === json({ x: 30, y: 40, width: 40, height: 20 }));
check("1.7 centre + carré", json(rectDepuisGlisser(50, 50, 70, 55, { centre: true, carre: true })) === json({ x: 30, y: 30, width: 40, height: 40 }));
check("1.8 aucune taille négative", rectDepuisGlisser(5, 5, 5, 5).width === 0);

// 2. mode : règle « fresh » (B §8) — un modificateur tenu À L'APPUI choisit le mode ; tenu après, il contraint la forme
check("2.1 sans modificateur : mode de la barre", modeSelection("intersect", false, false, true) === "intersect");
check("2.2 Maj à l'appui : ajouter", modeSelection("replace", true, false, true) === "add");
check("2.3 Alt à l'appui : soustraire", modeSelection("replace", false, true, true) === "subtract");
check("2.4 Maj+Alt à l'appui : intersection", modeSelection("replace", true, true, true) === "intersect");
check("2.5 modificateur après l'appui : mode de la barre", modeSelection("replace", true, true, false) === "replace");

// 3. lasso polygonal : fermeture à moins de 8 px ÉCRAN du premier sommet, avec au moins 3 sommets
const poly = [[0, 0], [100, 0], [100, 100]];
check("3.1 près du premier sommet (zoom 1)", fermeturePolygone(poly, 5, 5, 1));
check("3.2 trop loin", !fermeturePolygone(poly, 10, 10, 1));
check("3.3 le zoom compte : 5 px document = 20 px écran à 400 %", !fermeturePolygone(poly, 5, 0, 4) && fermeturePolygone(poly, 1, 1, 4));
check("3.4 moins de 3 sommets : jamais", !fermeturePolygone([[0, 0], [10, 0]], 0, 0, 1));
check("3.5 tracé : un point n'est gardé qu'à 2 px écran du précédent", ajouterPoint([[0, 0]], 1, 0, 1).length === 1 && ajouterPoint([[0, 0]], 3, 0, 1).length === 2);
check("3.6 tracé : points entiers", json(ajouterPoint([], 1.6, 2.4, 1)) === json([[2, 2]]));

// 4. commandes de sélection
check("4.1 rectangle", json(commandeRect({ x: 1, y: 2, width: 30, height: 40 }, opts, "add", false))
  === json({ command: "select.rect", params: { x: 1, y: 2, width: 30, height: 40, mode: "add", ellipse: false, antiAlias: true, feather: 0 } }));
check("4.2 ellipse", commandeRect({ x: 1, y: 2, width: 30, height: 40 }, opts, "replace", true).params.ellipse === true);
check("4.3 moins de 2 px, mode nouvelle : désélectionner", json(commandeRect({ x: 1, y: 2, width: 1, height: 40 }, opts, "replace", false)) === json({ command: "select.deselect", params: {} }));
check("4.4 moins de 2 px, autre mode : rien", commandeRect({ x: 1, y: 2, width: 1, height: 1 }, opts, "add", false) === null);
check("4.5 lasso", json(commandeLasso(poly, opts, "replace")) === json({ command: "select.lasso", params: { points: poly, mode: "replace", antiAlias: true, feather: 0 } }));
check("4.6 lasso de 2 points : désélectionner", commandeLasso([[0, 0], [1, 1]], opts, "replace").command === "select.deselect");
const doc = { width: 200, height: 100 };
check("4.7 baguette", json(commandeBaguette(10.7, 20.2, opts, "replace", doc)) === json({ command: "select.magicWand",
  params: { x: 10, y: 20, tolerance: 32, contiguous: true, antiAlias: true, sampleAllLayers: false, mode: "replace" } }));
check("4.8 baguette hors du document : rien", commandeBaguette(-1, 5, opts, "replace", doc) === null && commandeBaguette(200, 5, opts, "replace", doc) === null);
check("4.9 sélection rapide", json(commandeRapide([[1, 1], [5, 5]], opts, "add")) === json({ command: "select.quick", params: { points: [[1, 1], [5, 5]], size: 30, mode: "add", sampleAllLayers: false } }));
check("4.10 sélection rapide sans trace : rien", commandeRapide([], opts, "add") === null);

// 5. déplacement
check("5.1 avec sélection : edit.transform sur le contenu", json(deplacementCommande(true, 12, -3, 7))
  === json({ command: "edit.transform", params: { matrix: [1, 0, 0, 1, 12, -3] } }));
check("5.2 sans sélection : layer.translate du calque", json(deplacementCommande(false, 12, -3, 7))
  === json({ command: "layer.translate", params: { layer: 7, dx: 12, dy: -3 } }));
check("5.3 sans calque actif : pas de clé layer (le moteur prend l'actif)", !("layer" in deplacementCommande(false, 1, 1, null).params));
check("5.4 déplacement entier", json(deplacementCommande(false, 1.6, -0.4, 2).params) === json({ layer: 2, dx: 2, dy: 0 }));
check("5.5 déplacement nul : rien", deplacementCommande(true, 0.2, -0.3, 2) === null);
check("5.6 axe dominant (Maj)", json(contrainteAxe(10, 3)) === json({ dx: 10, dy: 0 }) && json(contrainteAxe(-2, -9)) === json({ dx: 0, dy: -9 }));
check("5.7 flèches : 1 px, Maj 10 px", json(pasFleche("ArrowLeft", false)) === json({ dx: -1, dy: 0 }) && json(pasFleche("ArrowDown", true)) === json({ dx: 0, dy: 10 }) && pasFleche("a", false) === null);

// 5b. le delta du glisser se mesure en coordonnées CLIENT depuis l'appui : l'aperçu translate #toile, son rectangle
//     bouge avec lui ; mesurer depuis ce rectangle renverrait le pointeur sur lui-même (dérive).
check("5.8 delta = (client - client à l'appui) / zoom", json(deltaGlisser({ clientX: 100, clientY: 50 }, { clientX: 160, clientY: 20 }, 2)) === json({ dx: 30, dy: -15 }));
check("5.9 zoom 1 : pixels écran = pixels document", json(deltaGlisser({ clientX: 0, clientY: 0 }, { clientX: 7, clientY: 3 }, 1)) === json({ dx: 7, dy: 3 }));
check("5.10 flèches cumulées en un seul déplacement", json(cumulerPas({ dx: 1, dy: 0 }, { dx: 10, dy: -1 })) === json({ dx: 11, dy: -1 }));

// 6. recadrage
check("6.1 cadre borné au document", json(rectRecadrage(-10, -5, 250, 50, {}, doc)) === json({ x: 0, y: 0, width: 200, height: 50 }));
check("6.2 cadre entièrement dehors : vide", rectRecadrage(300, 300, 400, 400, {}, doc).width === 0);
const v = { z: 2, ox: 10, oy: 10 };
const cadre = { x: 10, y: 10, width: 50, height: 30 };     // coins écran : (30,30) (130,30) (30,90) (130,90)
check("6.3 poignée nord-ouest à 8 px écran", poigneeSous(cadre, 34, 26, v) === "nw" && poigneeSous(cadre, 130, 90, v) === "se");
check("6.4 hors poignée", poigneeSous(cadre, 80, 60, v) === null && poigneeSous(null, 0, 0, v) === null);
check("6.5 tirer le coin sud-est", json(redimensionner(cadre, "se", 80, 70, doc)) === json({ x: 10, y: 10, width: 70, height: 60 }));
check("6.6 tirer le coin nord-ouest au-delà de l'autre coin : cadre retourné", json(redimensionner(cadre, "nw", 70, 50, doc)) === json({ x: 60, y: 40, width: 10, height: 10 }));
check("6.7 redimensionner reste dans le document", redimensionner(cadre, "se", 900, 900, doc).width === 190);
check("6.8 commande", json(commandeRecadrage(cadre, false, true)) === json({ command: "image.crop", params: { x: 10, y: 10, width: 50, height: 30, deleteCroppedPixels: true } }));
check("6.9 sans cadre, avec sélection : à la sélection", json(commandeRecadrage(null, true, false)) === json({ command: "image.crop", params: {} }));
check("6.10 sans cadre ni sélection : rien", commandeRecadrage(null, false, true) === null && commandeRecadrage({ x: 0, y: 0, width: 0, height: 5 }, false, true) === null);

// 7. pipette
check("7.1 pixel entier dans le document", json(pixelDans(doc, 10.9, 3.2)) === json({ x: 10, y: 3 }) && pixelDans(doc, 200, 3) === null && pixelDans(doc, 3, -0.1) === null);
check("7.2 premier plan", json(commandeCouleur([1, 0, 0, 1], false)) === json({ command: "tools.setColors", params: { foreground: "#ff0000" } }));
check("7.3 Alt : arrière-plan", json(commandeCouleur([0, 0, 1, 1], true)) === json({ command: "tools.setColors", params: { background: "#0000ff" } }));
check("7.4 réponse illisible : rien", commandeCouleur(null, false) === null && commandeCouleur({ x: 1 }, false) === null);

// 8. contour de sélection (bornes du moteur -> écran, sur demi-pixel pour un trait net)
check("8.1 bornes -> rectangle écran", json(formeFourmis([10, 20, 30, 40], { z: 2, ox: 5, oy: 7 })) === json({ x: 25.5, y: 47.5, w: 60, h: 80 }));
check("8.2 aucune sélection", formeFourmis(null, { z: 1, ox: 0, oy: 0 }) === null);

console.log(`gestes : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
