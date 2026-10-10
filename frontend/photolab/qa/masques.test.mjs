// qa/masques.test.mjs — t157 (parité L7) : masques, liens, filtres dynamiques, Sélectionner et masquer, Galerie de
// filtres, Sélection d'objet — fonctions PURES de mod-calques, mod-masquer, mod-galerie, mod-selection, et branchement.
import { commandeMasque, calquesChoisis, peutLier, gesteMasque, filtresDynamiques, deplacementFiltre } from "../js/mod-calques.js";
import { VUES, SORTIES, REGLAGES, DEPART, RACCOURCI, decorerMasquer, vueSuivante, vueParLettre, borner, reglagesEnvoyes, commandesValidation, depuisMemoire } from "../js/mod-masquer.js";
import { CATEGORIES, cleFiltre, cleCategorie, MAX_EFFETS, FILTRE_DEPART, effet, nouvelEffet, supprimerEffet, deplacerEffet, basculerEffet,
  changerFiltre, auMoinsUnVisible, champsEffet, lueurVersHex, hexVersLueur, effetsEnvoyes, valeursEffet, pileDepuis, dossiers } from "../js/mod-galerie.js";
import { commandeObjet } from "../js/mod-selection.js";
import { indexRaccourcis } from "../js/mod-raccourcis.js";
import { aiguillage, cibleDialogue, TRAITES_PAR_ECRAN, NECESSITE_DOC, actionEntree } from "../js/mod-menus.js";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { existe as existeIcone, CLES as CLES_SUITE } from "./outils/suite-icones.mjs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const ici = dirname(fileURLToPath(import.meta.url));
const lire = (...p) => readFileSync(join(ici, ...p), "utf8");
const moteur = lire("..", "..", "..", "backend", "app", "services", "photolab_moteur.py");
const registrePy = lire("..", "..", "..", "backend", "app", "services", "photolab_registre.py");

/* 1. Masque et Lier */
check("1.1 masque sans sélection : tout révéler", eq(commandeMasque(false, false, false), { command: "layer.layerMask.revealAll", params: {} }));
check("1.2 masque sans sélection, Alt : tout masquer", commandeMasque(false, true, false).command === "layer.layerMask.hideAll");
check("1.3 masque avec sélection : la révéler", commandeMasque(true, false, false).command === "layer.layerMask.revealSelection");
check("1.4 masque avec sélection, Alt : la masquer", commandeMasque(true, true, false).command === "layer.layerMask.hideSelection");
check("1.5 calque déjà masqué : masque vectoriel (Alt = tout masquer)", eq(commandeMasque(true, false, true), { command: "layer.vectorMask.add", params: {} })
  && eq(commandeMasque(false, true, true), { command: "layer.vectorMask.add", params: { hide: true } }));
const doc = { activeLayer: 3, layers: [{ id: 4, selected: true, linkGroup: null }, { id: 9, children: [{ id: 3, selected: true, linkGroup: null }] }, { id: 2 }] };
check("1.6 calques choisis (groupes compris)", calquesChoisis(doc).map((c) => c.id).join() === "4,3");
check("1.7 Lier : deux calques choisis", peutLier(doc) === true);
check("1.8 Lier : un seul, non lié -> non", peutLier({ activeLayer: 2, layers: [{ id: 2, selected: true, linkGroup: null }] }) === false);
check("1.9 Lier : un seul déjà lié -> oui (délier)", peutLier({ activeLayer: 2, layers: [{ id: 2, selected: true, linkGroup: 1 }] }) === true);
check("1.10 Lier : aucun « selected », le calque actif compte", peutLier({ activeLayer: 2, layers: [{ id: 2, linkGroup: 3 }] }) === true);
check("1.11 Lier : sans document -> non", peutLier(null) === false);

/* 2. gestes sur la vignette d'un masque */
check("2.1 clic simple : choisir", gesteMasque({}).action === "choisir");
check("2.2 Maj-clic : activer / désactiver", gesteMasque({ shiftKey: true }).action === "activer");
check("2.3 Alt-clic : voir le masque", gesteMasque({ altKey: true }).action === "voir");
check("2.4 Maj+Alt : voir (pas de rubis : le rendu du moteur ne le montre pas)", gesteMasque({ altKey: true, shiftKey: true }).action === "voir");
check("2.5 Ctrl-clic : sélection nouvelle", eq(gesteMasque({ ctrlKey: true }), { action: "selection", operation: "new" }));
check("2.6 Ctrl+Maj : ajouter ; Ctrl+Alt : soustraire ; les trois : intersection",
  gesteMasque({ ctrlKey: true, shiftKey: true }).operation === "add" && gesteMasque({ metaKey: true, altKey: true }).operation === "subtract"
  && gesteMasque({ ctrlKey: true, shiftKey: true, altKey: true }).operation === "intersect");

/* 3. filtres dynamiques */
const so = { id: 6, smartFilters: [{ command: "filter.blur.gaussianBlur", visible: true }, { command: "filter.filterGallery", visible: false }] };
const fd = filtresDynamiques(so);
check("3.1 le dernier appliqué en haut, index du moteur gardé", fd.map((f) => f.index).join() === "1,0" && fd[0].command === "filter.filterGallery");
check("3.2 calque sans filtres : liste vide", filtresDynamiques({ id: 1 }).length === 0 && filtresDynamiques(null).length === 0);
check("3.3 glisser un filtre sur un autre (même calque) -> move", eq(deplacementFiltre({ layer: 6, index: 0 }, { layer: 6, index: 1 }), { layer: 6, index: 0, to: 1 }));
check("3.4 sur lui-même ou un autre calque : rien", deplacementFiltre({ layer: 6, index: 1 }, { layer: 6, index: 1 }) === null
  && deplacementFiltre({ layer: 6, index: 0 }, { layer: 7, index: 1 }) === null);

/* 4. Sélectionner et masquer */
const vuesPy = /VUES_MASQUER = \(([^)]*)\)/.exec(moteur);
check("4.1 les 7 vues == VUES_MASQUER du pont (même ordre)", vuesPy && eq(VUES.map((v) => v.id), vuesPy[1].split(",").map((x) => x.trim().replace(/"/g, "")).filter(Boolean)), vuesPy && vuesPy[1]);
check("4.2 lettres de la référence (O M V A T K Y)", VUES.map((v) => v.lettre).join("") === "OMVATKY");
check("4.3 F parcourt les vues et reboucle", vueSuivante("oignon") === "fourmis" && vueSuivante("calques") === "oignon");
check("4.4 lettre -> vue (minuscule admise), inconnue -> null", vueParLettre("k") === "nb" && vueParLettre("Q") === null);
const clesPy = /CLES_MASQUER = frozenset\(\{([^}]*)\}\)/.exec(moteur);
check("4.5 réglages envoyés == CLES_MASQUER du pont", clesPy && eq(REGLAGES.map((r) => r.cle).sort(), clesPy[1].split(",").map((x) => x.trim().replace(/"/g, "")).filter(Boolean).sort()));
const r = REGLAGES.find((x) => x.cle === "radius"), f = REGLAGES.find((x) => x.cle === "feather");
check("4.6 rayon borné 0..250 (CHAMPS_AFFINER du pont)", borner(r, 999) === 250 && borner(r, -3) === 0 && borner(r, "12,6") === 13
  && /"radius", "type": "number", "min": 0, "max": 250/.test(registrePy));
check("4.7 contour progressif au dixième, illisible -> départ", borner(f, "2,34") === 2.3 && borner(f, "zorg") === 0);
check("4.8 réglages envoyés : ni sortie, ni vue, ni transparence", !("output" in reglagesEnvoyes(DEPART)) && !("vue" in reglagesEnvoyes(DEPART))
  && !("transparence" in reglagesEnvoyes(DEPART)) && reglagesEnvoyes({ ...DEPART, smartRadius: "oui" }).smartRadius === false);
check("4.9 OK : refineEdge avec la sortie choisie", eq(commandesValidation({ ...DEPART, output: "layerMask" }).map((c) => c.command), ["select.refineEdge"])
  && commandesValidation({ ...DEPART, output: "layerMask" })[0].params.output === "layerMask");
check("4.10 OK avec Inverser : select.inverse d'abord", eq(commandesValidation({ ...DEPART, inverser: true }).map((c) => c.command), ["select.inverse", "select.refineEdge"]));
check("4.11 sortie inconnue -> sélection", commandesValidation({ ...DEPART, output: "newDocument" })[0].params.output === "selection");
check("4.12 4 sorties du moteur (nouveau document : écarté)", eq(SORTIES, ["selection", "layerMask", "newLayer", "newLayerWithMask"]));
const mem = depuisMemoire({ radius: 9999, smooth: "zorg", output: "newLayer", vue: "nb", transparence: 70.4, inverser: true, zorg: 1 });
check("4.13 mémoire relue : bornée, typée, Inverser jamais mémorisé", mem.radius === 250 && mem.smooth === 0 && mem.output === "newLayer"
  && mem.vue === "nb" && mem.transparence === 70 && mem.inverser === false && !("zorg" in mem));
check("4.14 mémoire illisible -> départ", eq(depuisMemoire(null), DEPART) && eq(depuisMemoire("x"), DEPART));
// Défaut vu à l'écran : le catalogue ne porte aucun raccourci pour cette entrée, Alt+Ctrl+R n'ouvrait rien.
const arbre = [{ nom: "Select", entrees: [{ type: "commande", id: "select.all", raccourci: "Ctrl+A", etat: "actif" },
  { type: "sous-menu", nom: "x", entrees: [] }, { type: "commande", id: "select.selectAndMask", raccourci: "", etat: "actif" }] }];
const deco = decorerMasquer(arbre, "fr");
check("4.15 raccourci de la référence posé sur l'entrée (affiché)", RACCOURCI === "Cmd+Alt+R" && deco[0].entrees[2].raccourci === "Ctrl+Alt+R"
  && deco[0].entrees[0].raccourci === "Ctrl+A" && arbre[0].entrees[2].raccourci === "");
check("4.16 … et pris par les raccourcis (Ctrl+Alt+R)", (indexRaccourcis(deco).get("ctrl+alt+r") || {}).id === "select.selectAndMask");

/* 5. galerie */
const MAXPy = /MAX_EFFETS_GALERIE = (\d+)/.exec(registrePy);
check("5.1 plafond d'effets == MAX_EFFETS_GALERIE du pont", MAXPy && Number(MAXPy[1]) === MAX_EFFETS);
check("5.2 6 catégories, clés de dictionnaire en minuscules", CATEGORIES.length === 6 && cleCategorie("Brush Strokes") === "photolab.galerie.cat.brush_strokes"
  && cleFiltre("coloredPencil") === "photolab.galerie.f.colored_pencil" && cleFiltre("sumiE") === "photolab.galerie.f.sumi_e");
let p = [effet("cutout", { numberOfLevels: 5 }), effet("filmGrain")];
let n = nouvelEffet(p, 0);
check("5.3 nouveau : copie AU-DESSUS de l'effet choisi, choisie", n.i === 1 && n.pile.length === 3 && n.pile[1].filter === "cutout"
  && n.pile[1].params.numberOfLevels === 5 && n.pile[1].params !== p[0].params);
check("5.4 nouveau : pile pleine -> rien", nouvelEffet(Array.from({ length: MAX_EFFETS }, () => effet("cutout")), 0).pile.length === MAX_EFFETS);
check("5.5 supprimer : jamais le dernier", supprimerEffet([effet("cutout")], 0).pile.length === 1);
const s = supprimerEffet(n.pile, 1);
check("5.6 supprimer : l'effet du dessous est choisi", s.pile.length === 2 && s.i === 0);
check("5.7 monter / descendre, bornés", deplacerEffet(p, 0, 1).i === 1 && deplacerEffet(p, 0, 1).pile[1].filter === "cutout"
  && deplacerEffet(p, 1, 1).i === 1 && deplacerEffet(p, 0, -1).i === 0);
check("5.8 œil : bascule un seul effet", basculerEffet(p, 1)[1].visible === false && basculerEffet(p, 1)[0].visible === true);
check("5.9 changer de filtre : réglages remis, visibilité gardée", eq(changerFiltre([effet("cutout", { numberOfLevels: 5 }, false)], 0, "sponge")[0], { filter: "sponge", params: {}, visible: false }));
check("5.10 au moins un visible", auMoinsUnVisible(p) && !auMoinsUnVisible([effet("cutout", {}, false)]) && !auMoinsUnVisible([]));
const CUTOUT = [{ cle: "numberOfLevels", type: "number", min: 2, max: 8, entier: true, defaut: 4, optionnel: true },
  { cle: "edgeSimplicity", type: "number", min: 0, max: 10, entier: true, defaut: 4, optionnel: true }];
const NEON = [{ cle: "glowSize", type: "number", min: -24, max: 24, entier: true, defaut: 5, optionnel: true }, { cle: "glowColor", type: "json", optionnel: true }];
const SKETCH = [{ cle: "detail", type: "number", min: 1, max: 15, entier: true, defaut: 7, optionnel: true }, { cle: "foreground", type: "json", optionnel: true }];
const champsDe = (k) => ({ cutout: CUTOUT, neonGlow: NEON, photocopy: SKETCH }[k] || []);
check("5.11 champs éditables : glowColor devient une couleur, foreground reste caché", champsEffet(NEON).map((c) => c.cle + ":" + c.type).join() === "glowSize:number,glowColor:color"
  && champsEffet(SKETCH).map((c) => c.cle).join() === "detail");
check("5.12 lueur : [r,g,b,1] <-> #rrggbb", lueurVersHex([1, 0.5, 0, 1]) === "#ff8000" && eq(hexVersLueur("#ff8000"), [1, 0.502, 0, 1]) && eq(hexVersLueur("zorg"), [1, 1, 1, 1]));
const env = effetsEnvoyes([effet("cutout", { numberOfLevels: 99, edgeSimplicity: "3", zorg: 1 }), effet("neonGlow", { glowColor: "#00ff00" }, false),
  effet("photocopy", { detail: 3, foreground: "#123456" })], champsDe);
check("5.13 envoi : bornes du registre (99 -> 8 : le moteur reviendrait à 4 en silence)", env[0].params.numberOfLevels === 8 && env[0].params.edgeSimplicity === 3);
check("5.14 envoi : clés inconnues et couleurs d'effet retirées", !("zorg" in env[0].params) && !("foreground" in env[2].params));
check("5.15 envoi : lueur en [r,g,b,1] 0..1, visibilité transmise", eq(env[1].params.glowColor, [0, 1, 0, 1]) && env[1].visible === false);
check("5.16 valeurs du formulaire : défauts complétés", eq(valeursEffet(effet("cutout", { numberOfLevels: 6 }), CUTOUT), { numberOfLevels: 6, edgeSimplicity: 4 }));
check("5.17 pile reprise d'un filtre dynamique (params ou values du moteur)", eq(pileDepuis([{ filter: "cutout", values: { numberOfLevels: 3 } }, { filter: "sponge", visible: false }, "x"]),
  [effet("cutout", { numberOfLevels: 3 }), effet("sponge", {}, false)]));
check("5.18 pile vide ou illisible -> Crayon de couleur (amont)", eq(pileDepuis(null), [effet(FILTRE_DEPART)]) && FILTRE_DEPART === "coloredPencil");
const cat = { categories: ["Artistic", "Distort"], filters: [{ category: "Distort", key: "glass", name: "Glass" }, { category: "Artistic", key: "cutout", name: "Cutout" }] };
check("5.19 dossiers dans l'ordre des catégories du moteur", eq(dossiers(cat), [{ categorie: "Artistic", filtres: [{ key: "cutout", name: "Cutout" }] },
  { categorie: "Distort", filtres: [{ key: "glass", name: "Glass" }] }]));

/* 6. sélection d'objet */
check("6.1 rectangle -> select.object [x, y, w, h]", eq(commandeObjet({ x: 3, y: 4, width: 50, height: 20 }, { sampleAllLayers: true }, "add"),
  { command: "select.object", params: { rect: [3, 4, 50, 20], mode: "add", sampleAllLayers: true } }));
check("6.2 moins de 2 px : ignoré (amont)", commandeObjet({ x: 0, y: 0, width: 1, height: 40 }, {}, "replace") === null);

/* 7. branchement */
check("7.1 Galerie : aiguillage « galerie », ouverte par PL.ouvrirGalerie", aiguillage("filter.filterGallery") === "galerie"
  && cibleDialogue({ id: "filter.filterGallery", champs: [] }, { ouvrirGalerie() {} }) === "galerie");
check("7.2 Galerie : un clic ouvre son dialogue (champs opaques)", actionEntree({ type: "commande", id: "filter.filterGallery", etat: "actif",
  champs: [{ cle: "effects", type: "json", optionnel: false }] }) === "dialogue");
check("7.3 Sélectionner et masquer : traité par l'écran, document requis", TRAITES_PAR_ECRAN.has("select.selectAndMask") && NECESSITE_DOC.has("select.selectAndMask"));
const src = (f) => lire("..", "js", f);
const core = src("core.js"), galerie = src("mod-galerie.js"), masquer = src("mod-masquer.js"), calques = src("mod-calques.js"), gestes = src("mod-gestes.js");
check("7.4 core : galerie et masquer initialisés après le dialogue générique", core.indexOf("initGalerie(PL)") > core.indexOf("initDialogueReglage(PL)")
  && core.indexOf("initMasquer(PL)") > core.indexOf("initDialogueReglage(PL)"));
check("7.5 aperçus par le MOTEUR (POST /apercu, /masquer/apercu), jamais un calcul de pixels en JS", /PL\.api\("POST", "\/apercu"/.test(galerie)
  && /PL\.api\("POST", "\/masquer\/apercu"/.test(masquer) && !/getImageData|putImageData/.test(galerie + masquer));
check("7.6 un seul dialogue de réglage à la fois (prendreReglage / libererReglage)", /PL\.prendreReglage\(etat\)/.test(galerie) && /PL\.libererReglage\(etat\)/.test(galerie)
  && /PL\.prendreReglage\(etat\)/.test(masquer) && /PL\.libererReglage\(etat\)/.test(masquer));
check("7.7 réédition d'un filtre dynamique : setParams pour l'aperçu ET la validation", /layer\.smartFilter\.setParams/.test(calques) && /versCommande: vers/.test(calques)
  && /filtreDynamique: \{ layer: c\.id, index: f\.index \}/.test(calques));
check("7.8 Lier et Masque ne sont plus « bientôt »", !/bientot\(bouton\(""/.test(calques));
check("7.9 fourmis : le cadre de la sélection affinée remplace celui du document", /PL\.fourmisApercu/.test(gestes));
check("7.10 vignettes de masque chargées avec celles des calques", /\/masques\?maxSide=/.test(src("mod-cycle.js")));
// Défaut vu à l'écran (preuve 8799) : les données du masque arrivaient, la ligne restait vide — le crochet des vignettes
// ne reposait que celle du calque.
check("7.11 le crochet des vignettes repose aussi celle du masque", /PL\.surVignettes\.push[\s\S]*\.cq-masque\[data-masque\][\s\S]*vignettesMasques/.test(calques));
// Défaut vu à l'écran : l'icône « unlink » n'existait pas (chaîne vide). Toute icône demandée par ces modules existe
// (G4 : dans la suite Deepotus Glyph).
const icones = CLES_SUITE;
const demandees = [...(calques + galerie + masquer).matchAll(/(?:bouton\([^,]*,\s*|icone\(|PL\.icone\()"([a-z0-9-]+)"/g)].map((m) => m[1]);
// mod-galerie a son propre bouton(icône, clé, action) : l'icône est le PREMIER argument.
demandees.push(...[...galerie.matchAll(/bouton\("([a-z0-9-]+)", "photolab\./g)].map((m) => m[1]));
const ternaires = [...(calques + galerie).matchAll(/\? "([a-z0-9-]+)" : "([a-z0-9-]+)"/g)].flatMap((m) => [m[1], m[2]]).filter((x) => /^dz-(etat-visible|etat-cache|action-deplier)$/.test(x));
const manquantes = [...new Set([...demandees, ...ternaires])].filter((n) => !icones.has(n));
check("7.12 toute icône demandée existe dans la suite (dz-calque-objet-dynamique : badge de l'objet dynamique)", demandees.length >= 8 && !manquantes.length
  && demandees.includes("dz-calque-objet-dynamique") && ternaires.length >= 4, manquantes);

console.log(`masques : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
