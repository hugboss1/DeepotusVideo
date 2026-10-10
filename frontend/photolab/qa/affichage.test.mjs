// qa/affichage.test.mjs — t152 (parité L2) : menu Affichage, fonctions PURES de mod-affichage.js et du miroir de mod-vue.
import {
  OPTIONS_DEFAUT, IDS_AFFICHAGE, IDS_ZOOM, basculer, coche, visible, grillePixelsVisible, pasGrille, lignesGrille, graduations,
  aimanter, aimanterPoint, aimanterDeplacement, ciblesAimant, relireReperes, ecranSuivant, zoomImpression, bornesCalques,
  decorerAffichage, normaliserOptions, SEUIL_AIMANT_PX,
} from "../js/mod-affichage.js";
import { versDoc, versEcran, rectVersEcran } from "../js/mod-vue.js";
import { deltaGlisser } from "../js/mod-deplacer.js";
import { construireMenus, REFUSES, TRAITES_PAR_ECRAN, NECESSITE_DOC, actionEntree } from "../js/mod-menus.js";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const presque = (a, b) => Math.abs(a - b) < 1e-9;

// 1. options par défaut = celles de photocraft (view_cmds.rs Show / SnapTo, state.rs Extras)
const o = OPTIONS_DEFAUT;
check("1.1 extras oui, règles et grille non, repères oui, aimanter oui, repères non verrouillés", o.extras && !o.regles && !o.grille && o.reperes && o.aimanter && !o.verrouReperes);
check("1.2 afficher : sélection, grille de pixels, aperçu du pinceau, repères du canevas oui ; contours du calque non",
  o.afficher.contoursSelection && o.afficher.grillePixels && o.afficher.apercuPinceau && o.afficher.reperesCanevas && !o.afficher.contoursCalque);
check("1.3 aimanter à : tout (t160 : + tranches)", eq(o.aimanterA, { reperes: true, grille: true, calques: true, document: true, tranches: true }));
check("1.4 écran standard, pas de miroir, pas d'aperçu pixel art", o.ecran === "standard" && !o.miroir && !o.pixelArt);
check("1.5 seuil d'aimantation : 8 px d'écran (snap_ui.rs)", SEUIL_AIMANT_PX === 8);

// 2. bascules et coches
let b = basculer(o, "view.extras");
check("2.1 Extras se décoche ; l'original ne bouge pas", b.extras === false && o.extras === true && coche(b, "view.extras") === false);
check("2.2 sans extras, aucun extra visible", !visible(b, "grille") && !visible(basculer(b, "view.show.grid"), "grille") && !visible(b, "reperes"));
b = basculer(o, "view.show.grid");
check("2.3 Ctrl+' : grille visible", b.grille && visible(b, "grille") && coche(b, "view.show.grid"));
check("2.4 Ctrl+; : repères masqués", basculer(o, "view.show.guides").reperes === false && !visible(basculer(o, "view.show.guides"), "reperes"));
check("2.5 repères du canevas : second interrupteur des repères", !visible(basculer(o, "view.show.canvasGuides"), "reperes"));
check("2.6 Afficher › contours du calque, sélection, grille de pixels, aperçu du pinceau", basculer(o, "view.show.layerEdges").afficher.contoursCalque
  && !basculer(o, "view.show.selectionEdges").afficher.contoursSelection && !basculer(o, "view.show.pixelGrid").afficher.grillePixels
  && !basculer(o, "view.show.brushPreview").afficher.apercuPinceau);
const tout = basculer({ ...o, grille: false, reperes: false, afficher: { contoursCalque: false, contoursSelection: false, grillePixels: false, apercuPinceau: false, reperesCanevas: false } }, "view.show.all");
check("2.7 Afficher › Tout : tous les extras allumés", tout.grille && tout.reperes && Object.values(tout.afficher).every(Boolean));
check("2.8 Ctrl+R règles, Maj+Ctrl+; aimanter, Alt+Ctrl+; verrouiller", basculer(o, "view.rulers").regles && !basculer(o, "view.snap").aimanter && basculer(o, "view.lockGuides").verrouReperes);
check("2.9 Aimanter à › repères / grille / calques / limites du document", !basculer(o, "view.snapTo.guides").aimanterA.reperes && !basculer(o, "view.snapTo.grid").aimanterA.grille
  && !basculer(o, "view.snapTo.layers").aimanterA.calques && !basculer(o, "view.snapTo.documentBounds").aimanterA.document);
check("2.10 Aimanter à › Tout : tout rallumé", eq(basculer({ ...o, aimanterA: { reperes: false, grille: false, calques: false, document: false, tranches: false } }, "view.snapTo.all").aimanterA, o.aimanterA));
check("2.11 Symétrie horizontale, aperçu pixel art", basculer(o, "view.flipHorizontal").miroir && basculer(o, "view.pixelArtPreview").pixelArt);
check("2.12 modes d'écran : coche radio", basculer(o, "view.screenMode.fullScreen").ecran === "plein" && coche(basculer(o, "view.screenMode.fullScreen"), "view.screenMode.fullScreen")
  && !coche(basculer(o, "view.screenMode.fullScreen"), "view.screenMode.standard") && basculer(o, "view.screenMode.fullScreenWithMenuBar").ecran === "menus");
check("2.13 zooms : ni bascule ni coche", IDS_ZOOM.every((id) => coche(o, id) === undefined && eq(basculer(o, id), o)));
check("2.14 F : standard -> menus -> plein -> standard", ecranSuivant("standard") === "menus" && ecranSuivant("menus") === "plein" && ecranSuivant("plein") === "standard");
check("2.15 34 entrées servies (t160 : + Compteur, Notes, Tranches, Aimanter à › Tranches), aucune hors du catalogue Affichage",
  IDS_AFFICHAGE.length === 34 && IDS_AFFICHAGE.every((id) => id.startsWith("view."))
  && ["view.show.count", "view.show.slices", "view.show.notes", "view.snapTo.slices"].every((id) => IDS_AFFICHAGE.includes(id)));
check("2.16 entrées écartées absentes", !["view.fitArtboardOnScreen", "view.show.artboardGuides", "view.show.mesh", "view.show.editPins", "view.patternPreview",
  "view.show.targetPath", "view.show.smartGuides"].some((id) => IDS_AFFICHAGE.includes(id)));
check("2.16b t160 : Compteur, Notes, Tranches cochés par défaut, une bascule les coupe", ["compteur", "notes", "tranches"].every((k) => o.afficher[k] === true)
  && basculer(o, "view.show.count").afficher.compteur === false && basculer(o, "view.snapTo.slices").aimanterA.tranches === false);
check("2.17 normaliserOptions : stockage illisible ou partiel -> défauts complétés, types forcés", eq(normaliserOptions(null), o)
  && normaliserOptions({ grille: true, afficher: { contoursCalque: true }, ecran: "zorg", zorg: 1 }).grille === true
  && normaliserOptions({ afficher: { contoursCalque: true } }).afficher.contoursSelection === true
  && normaliserOptions({ ecran: "zorg" }).ecran === "standard" && !("zorg" in normaliserOptions({ zorg: 1 }))
  && normaliserOptions({ regles: "oui" }).regles === false);
check("2.18 grille de pixels : au-delà de 500 % seulement", !grillePixelsVisible(o, 5) && grillePixelsVisible(o, 6) && !grillePixelsVisible(basculer(o, "view.extras"), 8));

// 3. grille, règles
check("3.1 pas de grille : 1 pouce (ppi du document), 4 subdivisions", eq(pasGrille(72), { majeur: 72, mineur: 18 }) && eq(pasGrille(300), { majeur: 300, mineur: 75 }));
check("3.2 ppi absent ou nul -> 72", eq(pasGrille(0), { majeur: 72, mineur: 18 }) && eq(pasGrille(undefined), { majeur: 72, mineur: 18 }));
const v = { z: 1, ox: 0, oy: 0 };
let L = lignesGrille(v, { w: 200, h: 100 }, { w: 200, h: 100 }, "x", { majeur: 72, mineur: 18 });
check("3.3 lignes verticales visibles : multiples de 18 dans le document, majeures à 0, 72, 144", eq(L.map((l) => l.pos), [0, 18, 36, 54, 72, 90, 108, 126, 144, 162, 180, 198])
  && eq(L.filter((l) => l.majeure).map((l) => l.pos), [0, 72, 144]));
L = lignesGrille({ z: 0.1, ox: 0, oy: 0 }, { w: 2000, h: 1000 }, { w: 200, h: 100 }, "x", { majeur: 72, mineur: 18 });
check("3.4 subdivisions trop serrées (< 4 px) : majeures seulement", L.every((l) => l.majeure) && L.length > 0);
L = lignesGrille({ z: 4, ox: -400, oy: 0 }, { w: 2000, h: 1000 }, { w: 200, h: 100 }, "x", { majeur: 72, mineur: 18 });
check("3.5 seules les lignes de la vue (bornées par l'écran, jamais par le document)", L.length > 0 && L.every((l) => l.pos >= 100 && l.pos <= 150), L.map((l) => l.pos));
let g = graduations(0, 1000, 1);
check("3.6 règle à 100 % : graduations tous les 50 px (premier pas 1-2-5 à ≥ 50 px d'écran), 5 mineures par pas", g.pas === 50 && g.majeurs[0] === 0 && g.majeurs.includes(500) && g.mineur === 10, g);
g = graduations(0, 40, 16);
check("3.7 règle à 1600 % : pas de 5 px", g.pas === 5, g);
g = graduations(-30, 210, 0.5);
check("3.8 règle à 50 % : pas de 100 ; les graduations couvrent la plage (négatives comprises)", g.pas === 100 && g.majeurs[0] === -100 && g.majeurs.at(-1) === 200, g);

// 4. aimantation
const s = 8 / 1;    // seuil doc à 100 %
check("4.1 aimanter : la cible la plus proche dans le seuil", aimanter(103, [100, 110], s).valeur === 100 && aimanter(107, [100, 110], s).valeur === 110 && aimanter(103, [100, 110], s).cible === 100);
check("4.2 hors seuil : inchangé, sans cible", aimanter(120, [100, 109], s).valeur === 120 && aimanter(120, [100, 109], s).cible === null);
check("4.3 seuil en px d'écran : à 400 % le seuil document vaut 2 px", aimanter(103, [100], 8 / 4).valeur === 103 && aimanter(101.5, [100], 8 / 4).valeur === 100);
const C = { x: [0, 50, 100], y: [0, 40] };
check("4.4 aimanterPoint : chaque axe séparément", eq(aimanterPoint({ x: 47, y: 30 }, C, s), { x: 50, y: 30 }));
check("4.5 aimanterDeplacement : le bord gauche (ou droit, ou le centre) du calque se pose sur la cible la plus proche",
  eq(aimanterDeplacement([10, 10, 20, 20], 36, 0, C, s), { dx: 40, dy: 0 }) && eq(aimanterDeplacement([10, 10, 20, 20], 63, 0, C, s), { dx: 70, dy: 0 })
  && eq(aimanterDeplacement([10, 10, 20, 20], 87, 0, C, s), { dx: 90, dy: 0 }));
check("4.6 rien à moins du seuil : delta inchangé", eq(aimanterDeplacement([10, 10, 20, 20], 20, 3, { x: [100], y: [100] }, s), { dx: 20, dy: 3 }));
const doc = { width: 200, height: 100, resolution: 72, layers: [{ id: 1, bounds: [10, 10, 20, 20] }, { id: 2, bounds: [100, 50, 30, 10] }], activeLayer: 1, selectedLayers: [1] };
const rep = { horizontal: [25], vertical: [60] };
let c = ciblesAimant(o, doc, rep);
check("4.7 cibles : repères, limites et centre du document, bords et centres des AUTRES calques",
  [60, 0, 200, 100, 130, 115].every((x) => c.x.includes(x)) && [25, 0, 100, 50, 60, 55].every((y) => c.y.includes(y)) && !c.x.includes(10) && !c.x.includes(30), c);
c = ciblesAimant({ ...o, grille: true }, doc, rep);
check("4.8 grille visible : ses lignes (mineures) deviennent des cibles", c.x.includes(18) && c.x.includes(72));
check("4.9 grille masquée : pas de cible de grille", !ciblesAimant(o, doc, rep).x.includes(18));
check("4.10 Aimanter coupé : aucune cible", eq(ciblesAimant(basculer(o, "view.snap"), doc, rep), { x: [], y: [] }));
check("4.11 Aimanter à › repères coupé : plus les repères", !ciblesAimant(basculer(o, "view.snapTo.guides"), doc, rep).x.includes(60));
check("4.12 repères masqués : on n'y aimante plus", !ciblesAimant(basculer(o, "view.show.guides"), doc, rep).x.includes(60));
check("4.13 sans document : aucune cible", eq(ciblesAimant(o, null, rep), { x: [], y: [] }));

// 5. relecture des repères, zooms
const H = ["Open", "Brush Tool"];
check("5.1 nouveau document : relire", relireReperes(null, { nom: "a", history: H }) === true);
check("5.2 même historique : ne rien relire", relireReperes({ nom: "a", history: H }, { nom: "a", history: H }) === false);
check("5.3 un trait de pinceau : ne rien relire (130 ms par lecture)", relireReperes({ nom: "a", history: H }, { nom: "a", history: [...H, "Brush Tool"] }) === false);
check("5.4 New Guide, Move Guide, Clear Guides, Crop, Canvas Size, Image Size, Flip, Trim, Rotate : relire",
  ["New Guide", "Move Guide", "Delete Guide", "Clear Guides", "New Guide Layout", "Crop", "Canvas Size", "Image Size", "Flip Canvas Horizontal", "Trim", "Rotate 90° Clockwise"]
    .every((n) => relireReperes({ nom: "a", history: H }, { nom: "a", history: [...H, n] })));
check("5.5 annulation (historique plus court) : relire", relireReperes({ nom: "a", history: [...H, "Brush Tool"] }, { nom: "a", history: H }) === true);
check("5.6 autre document : relire", relireReperes({ nom: "a", history: H }, { nom: "b", history: H }) === true);
check("5.7 Taille d'impression : 72 / ppi", presque(zoomImpression(300), 0.24) && zoomImpression(72) === 1 && zoomImpression(0) === 1);
check("5.8 Adapter le(s) calque(s) : bornes des calques sélectionnés", eq(bornesCalques({ ...doc, selectedLayers: [1, 2] }), { x: 10, y: 10, w: 120, h: 50 })
  && eq(bornesCalques(doc), { x: 10, y: 10, w: 20, h: 20 }));
check("5.9 sans bornes (calque vide) : tout le document", eq(bornesCalques({ ...doc, layers: [{ id: 1, bounds: null }], selectedLayers: [1] }), { x: 0, y: 0, w: 200, h: 100 }));

// 6. miroir de la vue (mod-vue)
const vm = { z: 2, ox: 10, oy: 5, miroir: true, dw: 100 };
check("6.1 versEcran en miroir : x = (dw - x) * z + ox", eq(versEcran(vm, 0, 0), { x: 210, y: 5 }) && eq(versEcran(vm, 100, 0), { x: 10, y: 5 }));
check("6.2 versDoc réciproque", [[0, 0], [30, 7], [100, 50]].every(([x, y]) => { const e = versEcran(vm, x, y); const d = versDoc(vm, e.x, e.y); return presque(d.x, x) && presque(d.y, y); }));
check("6.3 sans miroir : inchangé", eq(versEcran({ z: 2, ox: 10, oy: 5 }, 3, 4), { x: 16, y: 13 }));
check("6.4 rectVersEcran en miroir : rectangle écran à largeur positive", eq(rectVersEcran(vm, 10, 0, 20, 10), { x: 150, y: 5, w: 40, h: 20 })
  && eq(rectVersEcran({ z: 2, ox: 10, oy: 5 }, 10, 0, 20, 10), { x: 30, y: 5, w: 40, h: 20 }));
check("6.5 déplacement en miroir : le glisser vers la droite déplace vers la gauche du document",
  eq(deltaGlisser({ clientX: 0, clientY: 0 }, { clientX: 10, clientY: 4 }, 2, true), { dx: -5, dy: 2 }) && eq(deltaGlisser({ clientX: 0, clientY: 0 }, { clientX: 10, clientY: 4 }, 2), { dx: 5, dy: 2 }));

// 7. menus
const ici = dirname(fileURLToPath(import.meta.url));
const cat = JSON.parse(readFileSync(join(ici, "..", "donnees", "menus.json"), "utf8"));
const reg = JSON.parse(readFileSync(join(ici, "..", "..", "..", "backend", "tests", "photocraft_commandes_0.3.0.json"), "utf8"));
const arbre = construireMenus(cat, reg, REFUSES, "fr", (k) => k);
const dec = decorerAffichage(arbre, basculer(o, "view.show.grid"));
const plat = []; const voir = (l) => { for (const x of l) { if (x.type === "sous-menu") voir(x.entrees); else if (x.type === "commande") plat.push(x); } };
voir(dec.find((m) => m.nom === "View").entrees);
const servies = plat.filter((x) => IDS_AFFICHAGE.includes(x.id));
check("7.1 les 34 entrées servies sont actives", servies.length === 34 && servies.every((x) => x.etat === "actif"), servies.filter((x) => x.etat !== "actif").map((x) => x.id));
check("7.2 coches : grille cochée, règles non, extras oui ; zooms sans coche", plat.find((x) => x.id === "view.show.grid").coche === true && plat.find((x) => x.id === "view.rulers").coche === false
  && plat.find((x) => x.id === "view.extras").coche === true && plat.find((x) => x.id === "view.zoomIn").coche === undefined);
check("7.3 les écartées restent « bientôt »", ["view.fitArtboardOnScreen", "view.show.mesh", "view.show.targetPath"].every((id) => plat.find((x) => x.id === id).etat === "bientot"));
check("7.4 traitées par l'écran (jamais envoyées au moteur)", servies.every((x) => TRAITES_PAR_ECRAN.has(x.id) && actionEntree(x) === "ecran"));
check("7.5 les zooms demandent un document", IDS_ZOOM.every((id) => NECESSITE_DOC.has(id)));
check("7.6 decorerAffichage ne modifie pas l'arbre reçu", arbre.find((m) => m.nom === "View").entrees.every((x) => x.coche === undefined));
check("7.7 les commandes moteur des repères ne sont PAS prises par l'écran (Nouveau repère… reste au moteur)", !TRAITES_PAR_ECRAN.has("view.newGuide") && !TRAITES_PAR_ECRAN.has("view.clearGuides"));

// 8. branchements DOM (épingles : ces lignes ne s'exécutent pas sous node)
const src = (f) => readFileSync(join(ici, "..", "js", f), "utf8");
check("8.1 mod-gestes : le point de geste passe par l'aimantation", /if \(PL\.affichage\) d = PL\.affichage\.aimanterPointDoc\(d, ev\);/.test(src("mod-gestes.js")));
check("8.2 mod-gestes : le contour de sélection suit Afficher › Contours de la sélection", /PL\.affichage\.voir\("contoursSelection"\)/.test(src("mod-gestes.js")));
check("8.3 mod-deplacer : le déplacement s'aimante (Ctrl l'interrompt)", /if \(PL\.affichage && !ev\.ctrlKey\) \(\{ dx, dy \} = PL\.affichage\.aimanterDeplacement\(dx, dy\)\);/.test(src("mod-deplacer.js"))
  && /deltaGlisser\(g\.appui, ev, g\.z, !!PL\.vue\.v\.miroir\)/.test(src("mod-deplacer.js")));
check("8.4 mod-peinture : le cercle de la pointe suit Afficher › Aperçu du pinceau", /PL\.affichage\.voir\("apercuPinceau"\)/.test(src("mod-peinture.js")));
check("8.5 mod-vue : dessin retourné en miroir, pixels francs en aperçu pixel art", /if \(v\.miroir\) \{/.test(src("mod-vue.js")) && /!vue\.pixelArt/.test(src("mod-vue.js")));

console.log(`affichage : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
