// qa/pinceaux.test.mjs — t155 : panneau Pinceaux (onglets Pinceaux │ Paramètres de pinceau │ Source de duplication │
// Outils prédéfinis), fonctions PURES de mod-pinceaux.js. Formes des réponses relevées sur le vrai moteur (08/10).
import { TRAITES_PAR_ECRAN, REFUSES } from "../js/mod-menus.js";
import { presetsVisibles, pointeVersOptions, paramsPointe, paramsSource, sourceVersChamps, predefinisVisibles, outilDuPreset,
  ONGLETS_PINCEAUX, ACTIONS_FENETRE, cibleSynchro } from "../js/mod-pinceaux.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// 1. onglets et entrées du menu Fenêtre
check("1.1 quatre onglets dans l'ordre", eq(ONGLETS_PINCEAUX, ["pinceaux", "parametres", "source", "predefinis"]));
check("1.2 Fenêtre › Pinceaux, Paramètres du pinceau (F5), Source de duplication, Outils prédéfinis -> onglet",
  eq(ACTIONS_FENETRE, { "window.panel.brushes": "pinceaux", "window.panel.brushSettings": "parametres",
    "window.panel.cloneSource": "source", "window.panel.toolPresets": "predefinis" }));

check("1.3 ces entrées sont traitées par l'écran (actives malgré le refus de window.* au moteur)",
  Object.keys(ACTIONS_FENETRE).every((id) => TRAITES_PAR_ECRAN.has(id)) && REFUSES.includes("window."));

// 2. préréglages de pointe (brush.presets.list)
const LISTE = { presets: [{ builtin: true, hardness: 1, name: "Hard Round", size: 30, tip: "round" },
  { builtin: true, hardness: 0, name: "Soft Round", size: 45, tip: "round" }, { name: "Calligraphy Flat", size: 28 }] };
check("2.1 sans filtre : tout, dans l'ordre", eq(presetsVisibles(LISTE, "").map((p) => p.name), ["Hard Round", "Soft Round", "Calligraphy Flat"]));
check("2.2 filtre sans casse", eq(presetsVisibles(LISTE, "rOUnd").map((p) => p.name), ["Hard Round", "Soft Round"]));
check("2.3 réponse illisible -> []", eq(presetsVisibles(null, ""), []) && eq(presetsVisibles({ presets: "x" }, ""), []));

// 3. pointe <-> options de l'outil
check("3.1 brush.get -> taille et dureté de l'outil (%)", eq(pointeVersOptions({ size: 25.4, hardness: 0.5 }), { taille: 25, durete: 50 }));
check("3.2 taille bornée 1..5000", pointeVersOptions({ size: 9000, hardness: 2 }).taille === 5000 && pointeVersOptions({ size: 9000, hardness: 2 }).durete === 100);
check("3.3 brush.get illisible -> null", pointeVersOptions(null) === null && pointeVersOptions({}) === null);
check("3.4 champ -> tools.setBrush, unités du moteur (0..1, espacement en fraction)",
  eq(paramsPointe("espacement", 25), { spacing: 0.25 }) && eq(paramsPointe("durete", 40), { hardness: 0.4 })
  && eq(paramsPointe("rondeur", 50), { roundness: 0.5 }) && eq(paramsPointe("angle", -30), { angle: -30 })
  && eq(paramsPointe("taille", 12), { size: 12 }) && eq(paramsPointe("espacementActif", false), { spacingEnabled: false })
  && eq(paramsPointe("retournerX", true), { flipX: true }) && eq(paramsPointe("retournerY", true), { flipY: true }));
check("3.5 bornes du pont (CHAMPS_POINTE)", eq(paramsPointe("espacement", 0), { spacing: 0.01 }) && eq(paramsPointe("espacement", 5000), { spacing: 10 })
  && eq(paramsPointe("rondeur", 0), { roundness: 0.01 }) && eq(paramsPointe("angle", 400), { angle: 180 }) && eq(paramsPointe("taille", 0), { size: 1 }));
check("3.6 champ inconnu -> null", paramsPointe("zorg", 1) === null);

// 4. source de duplication (cloneSource.list / cloneSource.set)
const SRC = { active: 0, sources: [{ index: 0, source: [5, 5], offset: [-35, -5], width: 100, height: 100, rotation: 0, flipH: false, flipV: false },
  { index: 1, source: null, offset: null, width: 100, height: 100, rotation: 0, flipH: false, flipV: false }] };
check("4.1 source active -> champs", eq(sourceVersChamps(SRC), { index: 0, source: [5, 5], decalageX: -35, decalageY: -5, largeur: 100, hauteur: 100, angle: 0, retournerH: false, retournerV: false }));
check("4.2 sans décalage -> 0, 0 ; sans source -> null", eq(sourceVersChamps({ ...SRC, active: 1 }).source, null) && sourceVersChamps({ ...SRC, active: 1 }).decalageX === 0);
check("4.3 liste illisible -> null", sourceVersChamps(null) === null);
check("4.4 champs -> cloneSource.set sur la source active",
  eq(paramsSource(0, "decalage", [3, -4]), { index: 0, offset: [3, -4] }) && eq(paramsSource(2, "largeur", 120), { index: 2, width: 120 })
  && eq(paramsSource(1, "angle", 15), { index: 1, rotation: 15 }) && eq(paramsSource(1, "retournerH", true), { index: 1, flipH: true }));
check("4.5 champ inconnu -> null", paramsSource(0, "zorg", 1) === null);

// 5. outils prédéfinis (tool.presets.list : {presets:[{name, tool}]})
const PRE = { presets: [{ name: "Soft Round 100 px", tool: "brush" }, { name: "Soft Eraser 60 px", tool: "eraser" }, { name: "Clone Soft 40 px", tool: "cloneStamp" }] };
check("5.1 tous", predefinisVisibles(PRE, "brush", false).length === 3);
check("5.2 outil actif uniquement", eq(predefinisVisibles(PRE, "eraser", true).map((p) => p.name), ["Soft Eraser 60 px"]));
check("5.3 illisible -> []", eq(predefinisVisibles(null, "brush", false), []));
check("5.4 outil du préréglage : un outil de l'écran ou null", outilDuPreset("cloneStamp") === "cloneStamp" && outilDuPreset("brush") === "brush" && outilDuPreset("zorg") === null);

// 6. la pointe ne suit que l'outil courant (défaut vu en preuve : un préréglage de gomme changeait aussi le Pinceau)
check("6.1 outil courant avec taille -> lui-même", cibleSynchro("eraser") === "eraser" && cibleSynchro("cloneStamp") === "cloneStamp");
check("6.2 outil sans taille (pot, dégradé, gomme magique) ou hors peinture -> Pinceau", cibleSynchro("paintBucket") === "brush"
  && cibleSynchro("gradient") === "brush" && cibleSynchro("magicEraser") === "brush" && cibleSynchro("move") === "brush");
const src = (await import("node:fs")).readFileSync(new URL("../js/mod-pinceaux.js", import.meta.url), "utf8");
check("6.3 synchroniserPointe n'écrit plus dans une liste fixe d'outils", !/\["brush", "eraser"\]/.test(src) && /cibleSynchro\(PL\.etat\.outil\)/.test(src));

console.log(`pinceaux : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
