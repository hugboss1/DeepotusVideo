// qa/mesure.test.mjs — t160 (parité L10) : Règle, Comptage, Note, Tranches, Journal des mesures, Notes. Fonctions PURES.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { OUTILS_MESURE, hexDe, contraindre, lectureRegle, extremiteSous, marqueSous, noteSous, tranchesVisibles, trancheSous,
  cibleTranche, rectTranche, rectVersTableau, tableauVersRect, colonnesJournal, cellule, cleColonne, analyseUtile, positionNote, deplacerRect,
  rectChange, arrondirPoint, SOURCES } from "../js/mod-mesure.js";
import { construireMenus, REFUSES, TRAITES_PAR_ECRAN, NECESSITE_DOC, IDS_MESURE, rechercherEntree, actionEntree } from "../js/mod-menus.js";
import { EMPLACEMENTS, outilDe } from "../js/mod-outils.js";
import { ciblesAimant, OPTIONS_DEFAUT, OUTILS_AIMANTES } from "../js/mod-affichage.js";
import { PANNEAUX, GROUPES } from "../js/mod-espaces.js";
import { ETATS_MOTEUR } from "../js/mod-historique.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const dico = { ...JSON.parse(readFileSync(join(racine, "../shared/i18n/commun.json"), "utf8")), ...JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8")) };
const manque = (cles) => cles.filter((k) => !(dico[k] && dico[k].fr && dico[k].en));
const pres = (a, b, e = 1e-9) => Math.abs(a - b) < e;

// 1. règle
check("1.1 cinq outils, tous actifs", OUTILS_MESURE.length === 5 && OUTILS_MESURE.every((id) => outilDe(id) && outilDe(id).p2));
const [cx, cy] = contraindre(0, 0, 10, 9);
check("1.2 Maj : angle par pas de 45°, longueur gardée", pres(cx, cy, 1e-9) && pres(Math.hypot(cx, cy), Math.hypot(10, 9)) && JSON.stringify(contraindre(0, 0, 10, 1).map(Math.round)) === "[10,0]"
  && JSON.stringify(contraindre(5, 5, 5, 5)) === "[5,5]");
const L = Object.fromEntries(lectureRegle({ x: 10, y: 20, w: 100, h: 0, angle: -0, l1: 100, l2: null, length: 2, protractor: false, units: "cm" }));
check("1.3 lecture : L1 = longueur à l'échelle avec son unité, pas de L2 sans rapporteur", L.x === "10" && L.l1 === "2 cm" && L.l2 === "" && L.a === "0°");
const LP = Object.fromEntries(lectureRegle({ x: 1, y: 1, w: 1, h: 1, angle: 90, l1: 100, l2: 50.456, length: 2, protractor: true, units: "cm" }));
check("1.4 lecture du rapporteur : angle, L1 et L2 en pixels", LP.a === "90°" && LP.l1 === "100" && LP.l2 === "50.46");
check("1.5 lecture vide sans règle", lectureRegle(null).every(([, v]) => v === ""));
const R = { start: [10, 10], end: [110, 10], protractor: null };
check("1.6 extrémité sous le point (tolérance document)", extremiteSous(R, { x: 112, y: 11 }, 3) === "end" && extremiteSous(R, { x: 50, y: 10 }, 3) === null
  && extremiteSous({ ...R, protractor: [10, 60] }, { x: 11, y: 59 }, 3) === "protractor" && extremiteSous(null, { x: 0, y: 0 }, 3) === null);

// 2. comptage, notes
const C = { groups: [{ points: [[10, 10], [50, 50]], visible: true }, { points: [[11, 11]], visible: false }, { points: [[52, 52]], visible: true }] };
check("2.1 marque la plus proche, groupes masqués ignorés", JSON.stringify(marqueSous(C, { x: 10.5, y: 10.5 }, 5)) === '{"group":0,"index":0}'
  && JSON.stringify(marqueSous(C, { x: 51.5, y: 51.5 }, 5)) === '{"group":2,"index":0}' && marqueSous(C, { x: 200, y: 200 }, 5) === null);
const N = [{ index: 0, position: [10, 10] }, { index: 1, position: [12, 12] }];
check("2.2 note sous le point : la dernière posée d'abord ; hors de l'icône -> null", noteSous(N, { x: 13, y: 13 }, 8) === 1 && noteSous(N, { x: 10, y: 10 }, 1) === 0
  && noteSous(N, { x: 40, y: 40 }, 8) === null);
check("2.3 couleur du moteur 0..1 -> #rrggbb", hexDe([1, 1, 0.51]) === "#ffff82" && hexDe([0, 0, 1]) === "#0000ff" && hexDe("#123456") === "#123456");

// 3. tranches
const S = [{ number: 1, id: null, origin: "auto", rect: [0, 0, 400, 20] }, { number: 2, id: 1, origin: "user", rect: [20, 20, 100, 80] },
  { number: 3, id: 2, origin: "layer", rect: [30, 30, 20, 20] }];
check("3.1 automatiques montrées s'il y a des tranches réelles (ou outil actif), jamais si masquées", tranchesVisibles(S, false).length === 3
  && tranchesVisibles([S[0]], false).length === 0 && tranchesVisibles([S[0]], true).length === 1 && tranchesVisibles(S, true, true).length === 2);
check("3.2 tranche sous le point : la plus petite réelle d'abord, l'automatique en dernier", trancheSous(S, { x: 35, y: 35 }).number === 3
  && trancheSous(S, { x: 25, y: 25 }).number === 2 && trancheSous(S, { x: 5, y: 5 }).number === 1 && trancheSous(S, { x: 500, y: 500 }) === null);
check("3.3 cible : id d'une tranche utilisateur, numéro d'une automatique (promue par le moteur)", JSON.stringify(cibleTranche(S[1])) === '{"slice":1}'
  && JSON.stringify(cibleTranche(S[0])) === '{"number":1}');
const doc = { width: 100, height: 80 };
check("3.4 glisser : pixels entiers bornés au document, dans tous les sens, Maj = carré", JSON.stringify(rectTranche(10.4, 10.6, 30.2, 40.9, false, doc)) === '{"x":10,"y":11,"width":20,"height":30}'
  && JSON.stringify(rectTranche(30, 40, 10, 10, false, doc)) === '{"x":10,"y":10,"width":20,"height":30}'
  && JSON.stringify(rectTranche(90, 70, 130, 120, false, doc)) === '{"x":90,"y":70,"width":10,"height":10}'
  && JSON.stringify(rectTranche(10, 10, 20, 50, true, doc)) === '{"x":10,"y":10,"width":40,"height":40}');
check("3.5 rect <-> tableau", JSON.stringify(rectVersTableau(tableauVersRect([1, 2, 3, 4]))) === "[1,2,3,4]");
const ca = ciblesAimant({ ...OPTIONS_DEFAUT, aimanterA: { reperes: false, grille: false, calques: false, document: false, tranches: true } },
  { width: 400, height: 300, layers: [] }, null, S);
check("3.6 aimantation : bords des tranches réelles seulement", JSON.stringify(ca.x) === "[20,120,30,50]" && JSON.stringify(ca.y) === "[20,100,30,50]");
check("3.7 aimantation aux tranches coupée par l'option", ciblesAimant({ ...OPTIONS_DEFAUT, aimanterA: { ...OPTIONS_DEFAUT.aimanterA, tranches: false, document: false, calques: false } },
  { width: 400, height: 300, layers: [] }, null, S).x.length === 0);

// 4. journal des mesures
const J = { rows: [{ id: 1, values: { label: "M1", source: "Ruler Tool", length: 2, angle: 0, histogram: [1, 2] } }, { id: 2, values: { label: "M2", count: 3 } }],
  columns: ["label", "count", "length", "angle", "histogram", "area"] };
const PTS = { dataPoints: { ruler: ["label", "length"], count: ["label", "count"] }, columns: J.columns.map((k) => ({ key: k, name: k })) };
check("4.1 colonnes : choisies, avec une valeur, sans l'histogramme, dans l'ordre du moteur", JSON.stringify(colonnesJournal(J, PTS).map((c) => c.key)) === '["label","count","length"]');
check("4.2 sans selectDataPoints : toutes les colonnes qui ont une valeur", JSON.stringify(colonnesJournal(J, null).map((c) => c.key)) === '["label","count","length","angle"]');
check("4.3 cellule : entiers, décimales à 4 chiffres, vide", cellule(2) === "2" && cellule(0.123456) === "0.1235" && cellule(null) === "" && cellule("x") === "x");
const colonnes = ["label", "dateTime", "document", "source", "scale", "scaleUnits", "scaleFactor", "count", "area", "perimeter", "circularity", "height",
  "width", "grayMin", "grayMax", "grayMean", "grayMedian", "integratedDensity", "histogram", "length", "angle"];
check("4.4 un libellé par colonne du moteur (21), clés en minuscules", !manque(colonnes.map(cleColonne)).length && cleColonne("grayMin") === "photolab.mesure.col.gray_min", manque(colonnes.map(cleColonne)));
check("4.5 relire l'analyse : outil de mesure, interrupteur, panneau ; sinon non", analyseUtile("ruler", {}, false) && analyseUtile("move", { notes: true }, false)
  && analyseUtile("move", {}, true) && !analyseUtile("move", { compteur: false, notes: false, tranches: false }, false));

// 5. menus, panneaux, historique, textes
const catalogue = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));
const reg = ["edit.undo", "file.import.notes"].map((id) => ({ id, label: id, params: "{}", enabled: true, champs: [] }));
const arbre = construireMenus(catalogue, reg, REFUSES, "fr", (k) => k);
check("5.1 les 7 entrées de menu servies par l'écran, présentes et actives", IDS_MESURE.length === 7 && IDS_MESURE.every((id) => TRAITES_PAR_ECRAN.has(id)
  && rechercherEntree(arbre, id) && rechercherEntree(arbre, id).etat === "actif" && actionEntree(rechercherEntree(arbre, id)) === "ecran"),
  IDS_MESURE.filter((id) => !rechercherEntree(arbre, id) || rechercherEntree(arbre, id).etat !== "actif"));
check("5.2 Importer › Notes demande un document", NECESSITE_DOC.has("file.import.notes"));
check("5.3 Journal des mesures et Notes : onglets du groupe Infos", PANNEAUX["window.panel.measurementLog"].onglet === "mesures"
  && PANNEAUX["window.panel.notes"].onglet === "notes" && GROUPES.infos.includes("mesures") && GROUPES.infos.includes("notes"));
const html = readFileSync(join(racine, "index.html"), "utf8");
check("5.4 index.html : onglets et corps Mesures / Notes", /data-onglet-in="mesures"/.test(html) && /id="corpsMesures"/.test(html) && /id="corpsNotes"/.test(html));
const noms = ["Count", "Clear Count", "New Count Group", "Delete Count Group", "Count Group Options", "New Note", "Edit Note", "Move Note", "Delete Note", "Slice",
  "Slice Options", "Divide Slice", "Promote to User Slice", "Delete Slice", "Slices From Guides", "New Layer Based Slice", "Clear Slices", "Straighten",
  "Set Measurement Scale", "Place Scale Marker"];
check("5.5 noms d'étapes du moteur traduits (fr et en)", noms.every((n) => ETATS_MOTEUR[n]) && !manque(noms.map((n) => ETATS_MOTEUR[n])).length, manque(noms.map((n) => ETATS_MOTEUR[n])));
const src = readFileSync(join(racine, "js", "mod-mesure.js"), "utf8");
const litt = [...src.matchAll(/"(photolab\.[a-z0-9_.]+|commun\.[a-z0-9_.]+)"/g)].map((m) => m[1]).filter((k) => !k.endsWith("."));
check("5.6 chaque clé écrite dans mod-mesure existe", litt.length > 50 && !manque(litt).length, manque(litt));
const types = ["image", "no_image", "table"].map((k) => "photolab.tranche.type." + k);
const regle = ["x", "y", "w", "h", "a", "l1", "l2"].map((k) => "photolab.regle." + k);
check("5.7 types de tranche et champs de la règle (clés composées)", !manque([...types, ...regle]).length, manque([...types, ...regle]));
check("5.8 noms saisis par l'utilisateur jamais traduits (data-dz-brut) : auteur, texte de note, nom de groupe, options de tranche, liste de documents",
  (src.match(/setAttribute\("data-dz-brut", ""\)/g) || []).length >= 7);
check("5.9 cinq outils dans EMPLACEMENTS avec leur lettre (C et I)", ["slice", "sliceSelect"].every((id) => outilDe(id).lettre === "C")
  && ["ruler", "note", "count"].every((id) => outilDe(id).lettre === "I") && EMPLACEMENTS.flat().filter((o) => OUTILS_MESURE.includes(o.id)).length === 5);

// 6. défauts trouvés à la preuve (09/10/2026)
check("6.1 glisser une note : depuis l'origine du geste, jamais cumulé (la surcouche peut être relue en route)",
  JSON.stringify(positionNote({ origine: [60, 40], de: [62, 42], a: [150, 120] })) === "[148,118]");
check("6.2 déplacer une tranche : depuis le rectangle d'origine, pixels entiers", JSON.stringify(deplacerRect({ x: 20, y: 20, width: 100, height: 80 }, [50, 50], [90.4, 70.6]))
  === '{"x":60,"y":41,"width":100,"height":80}');
check("6.3 un clic qui choisit une tranche sans la bouger ne fait aucune étape", !rectChange({ x: 1, y: 2, width: 3, height: 4 }, { x: 1, y: 2, width: 3, height: 4 })
  && rectChange({ x: 1, y: 2, width: 3, height: 4 }, { x: 1, y: 2, width: 3, height: 5 }) && rectChange(null, { x: 0, y: 0, width: 1, height: 1 }));
check("6.4 points de la règle arrondis au centième (99.99999… -> 100)", JSON.stringify(arrondirPoint([99.99999999999972, 0.123456])) === "[100,0.12]" && arrondirPoint(null) === null);
check("6.5 « -0 » s'affiche « 0 »", cellule(-0) === "0" && cellule(-0.5) === "-0.5");
check("6.6 la colonne Source dit le nom de l'outil de l'écran", SOURCES["Ruler Tool"] === "photolab.outil.ruler" && !manque(Object.values(SOURCES)).length);
check("6.7 l'outil Tranche s'aimante (repères, grille, tranches, bords)", OUTILS_AIMANTES.has("slice"));

console.log(`mesure : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
