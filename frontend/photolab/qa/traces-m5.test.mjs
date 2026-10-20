// qa/traces-m5.test.mjs — t254 (Photolab M5, moteur photocraft 0.10) : Sélection directe, Conversion de point, Ajout et
// Suppression de point d'ancrage, Plume de courbure, Plume libre, menu des tracés (détourage, transformation, fond et
// contour), Texte vertical, Masques de texte, texte sur tracé, taille ±.
// Fonctions PURES ; paramètres relevés sur le vrai moteur (backend/tests/test_photolab_m5.py [2]).
import { toucher, segments, pointSegment, poigneesMontrees, ancresDans, paramsCible, commandeEdition, apercuEdition, outilAncre,
  commandeAncre, ordreSuppression, commandesSuppression, noeudsCourbure, commandesCourbure, simplifier, anglesVifs, traceLibre, entreesMenuTrace,
  CHAMPS_TRANSFORMER, CHAMPS_DETOURAGE, OUTILS_TRACE, OUTILS_ANCRES, AJUSTEMENT, dChemin } from "../js/mod-trace.js";
import { OUTILS_TEXTE, estMasque, estVertical, jumeau, paramsMasque, paramsCreation, longueurJusqua, surTrace, commandeTaille,
  surUnTrace, DEFAUT_TEXTE } from "../js/mod-texte.js";
import { EMPLACEMENTS, outilDe, outilParLettre, groupeDeLettre, cleNom } from "../js/mod-outils.js";
import { ETATS_MOTEUR } from "../js/mod-historique.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const K = (x, y, s = false) => ({ anchor: [x, y], in: [x, y], out: [x, y], smooth: s });
// Tracé du banc moteur : 20,20 -> 100,20 -> 100,100 (ouvert, deux segments droits)
const P = { subpaths: [{ closed: false, op: "combine", knots: [K(20, 20), K(100, 20), K(100, 100)] }], fillRule: "nonzero" };
const COURBE = { subpaths: [{ closed: false, knots: [{ anchor: [0, 0], in: [0, 0], out: [0, -40], smooth: false }, { anchor: [100, 0], in: [100, -40], out: [100, 0], smooth: false }] }] };

/* 1 — outils */
for (const id of ["freeformPen", "curvaturePen", "addAnchorPoint", "deleteAnchorPoint", "convertPoint", "verticalType", "horizontalTypeMask", "verticalTypeMask", "directSelection"]) {
  const o = outilDe(id);
  check(`1.1 ${id} actif, dans la barre`, o && o.p2 === true, o);
}
check("1.2 le groupe P a six outils, la Plume en tête (amont : Pen, Freeform, Curvature, Add, Delete, Convert)",
  eq(groupeDeLettre("P").map((o) => o.id), ["pen", "freeformPen", "curvaturePen", "addAnchorPoint", "deleteAnchorPoint", "convertPoint"]));
check("1.3 le groupe T : Texte, Texte vertical, deux masques ; A : Sélection de tracé puis Sélection directe",
  eq(groupeDeLettre("T").map((o) => o.id), OUTILS_TEXTE) && eq(groupeDeLettre("A").map((o) => o.id), ["pathSelection", "directSelection"]));
check("1.4 P depuis la Plume -> Plume libre ; A depuis Sélection de tracé -> Sélection directe", outilParLettre("P", "pen", false) === "freeformPen" && outilParLettre("A", "pathSelection", false) === "directSelection");
check("1.5 la Plume reste le premier outil de son emplacement (son id DOM ne change pas)", EMPLACEMENTS.find((e) => e.some((o) => o.id === "convertPoint"))[0].id === "pen");
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
for (const id of ["freeformPen", "curvaturePen", "addAnchorPoint", "deleteAnchorPoint", "convertPoint", "verticalType", "horizontalTypeMask", "verticalTypeMask", "directSelection"]) {
  const e = dico[cleNom(id)];
  check(`1.6 ${cleNom(id)} en fr et en, sans nom de marque`, e && e.fr && e.en && !/photoshop|adobe/i.test(e.fr + e.en), e);
}
check("1.7 OUTILS_TRACE : les trois plumes, les quatre outils d'ancre, la Sélection de tracé", OUTILS_TRACE.length === 8 && OUTILS_ANCRES.length === 4);

/* 2 — toucher : poignée montrée > ancre > segment (t affiné) */
check("2.1 une ancre sous le point (tolérance)", eq(toucher(P, [101, 21], 6), { type: "ancre", sp: 0, k: 1, d: Math.hypot(1, 1) }));
const s1 = toucher(P, [60, 23], 6);
check("2.2 un segment : le premier, t ≈ 0,5", s1 && s1.type === "segment" && s1.k === 0 && Math.abs(s1.t - 0.5) < 0.01, s1);
check("2.3 rien près du point -> null", toucher(P, [60, 60], 6) === null);
check("2.4 une poignée MONTRÉE passe avant l'ancre", toucher(COURBE, [0, -39], 6, [{ sp: 0, k: 0, h: "out" }]).type === "poignee"
  && (toucher(COURBE, [0, -39], 6) || {}).type !== "poignee");
check("2.5 t reste strictement dans ]0, 1[ (path.addAnchor le refuserait)", (() => { const t = toucher(P, [20.5, 20], 0.1); return !t || t.type === "ancre" || (t.t > 0 && t.t < 1); })());
check("2.6 un sous-tracé fermé a le segment du retour", segments({ closed: true, knots: [K(0, 0), K(10, 0), K(10, 10)] }).length === 3
  && segments({ closed: false, knots: [K(0, 0), K(10, 0), K(10, 10)] }).length === 2);
check("2.7 pointSegment : extrémités et milieu d'un segment droit", eq(pointSegment(K(0, 0), K(10, 0), 0), [0, 0]) && eq(pointSegment(K(0, 0), K(10, 0), 1), [10, 0])
  && eq(pointSegment(K(0, 0), K(10, 0), 0.5), [5, 0]));

/* 3 — poignées montrées, cadre de points, cibles */
check("3.1 poignées montrées : les deux d'une ancre choisie, jamais une rentrée", eq(poigneesMontrees(COURBE, [[0, 0]]), [{ sp: 0, k: 0, h: "out" }])
  && eq(poigneesMontrees(P, [[0, 1]]), []));
check("3.2 segment cliqué : sa poignée de sortie et l'entrée du suivant", eq(poigneesMontrees(COURBE, [], [0, 0]), [{ sp: 0, k: 0, h: "out" }, { sp: 0, k: 1, h: "in" }]));
check("3.3 cadre de sélection des points (coins dans n'importe quel ordre)", eq(ancresDans(P, [110, 10, 50, 30]), [[0, 1]]) && eq(ancresDans(P, [0, 0, 200, 200]), [[0, 0], [0, 1], [0, 2]]));
check("3.4 cibles : travail -> work, forme active -> layer (sans id : path.info ne prend pas de calque), tracé enregistré -> son nom",
  eq(paramsCible({ type: "travail" }), { name: "work" }) && eq(paramsCible({ type: "forme" }), { name: "layer" }) && eq(paramsCible({ type: "enregistre", nom: "Tracé 1" }), { name: "Tracé 1" }) && paramsCible(null) === null);

/* 4 — commandes des glisser (forme exacte du banc moteur) */
const W = { type: "travail" };
check("4.1 glisser des ancres -> path.moveAnchors {anchors, move}", eq(commandeEdition({ type: "ancres", ancres: [[0, 1]] }, [100, 20], [110, 25], W),
  { command: "path.moveAnchors", params: { name: "work", anchors: [[0, 1]], move: [10, 5] } }));
check("4.2 un clic (moins d'un demi-pixel) ne déplace rien", commandeEdition({ type: "ancres", ancres: [[0, 1]] }, [100, 20], [100.2, 20.1], W) === null);
check("4.3 Plume de courbure au repos : la courbe suit (curvature)", commandeEdition({ type: "ancres", ancres: [[0, 0]], courbure: true }, [0, 0], [0, 10], W).params.curvature === true);
check("4.4 glisser une poignée -> path.moveHandle {to = départ + glisser, independent}", eq(commandeEdition({ type: "poignee", sp: 0, k: 1, h: "out", de: [110, 25], independant: true }, [110, 25], [130, 40], W),
  { command: "path.moveHandle", params: { name: "work", subpath: 0, knot: 1, handle: "out", to: [130, 40], independent: true } }));
check("4.5 glisser un segment -> path.bendSegment {t, move}", eq(commandeEdition({ type: "segment", sp: 0, k: 0, t: 0.5 }, [60, 20], [60, 0], W),
  { command: "path.bendSegment", params: { name: "work", subpath: 0, knot: 0, t: 0.5, move: [0, -20] } }));
check("4.6 Conversion de point : clic = angle (sans out), glisser = lisse (out = le pointeur)",
  eq(commandeEdition({ type: "convertir", sp: 0, k: 1 }, [100, 20], [100, 20], W), { command: "path.convertPoint", params: { name: "work", subpath: 0, knot: 1 } })
  && eq(commandeEdition({ type: "convertir", sp: 0, k: 1 }, [100, 20], [140, 30], W).params.out, [140, 30]));
check("4.7 la forme active : name layer", commandeEdition({ type: "ancres", ancres: [[0, 0]] }, [0, 0], [5, 5], { type: "forme" }).params.name === "layer");
const ap = apercuEdition(P, { type: "ancres", ancres: [[0, 1]] }, [0, 0], [10, 5]);
check("4.8 aperçu : l'ancre suit, le tracé d'origine reste intact", eq(ap.subpaths[0].knots[1].anchor, [110, 25]) && eq(P.subpaths[0].knots[1].anchor, [100, 20]));
const apS = apercuEdition(P, { type: "segment", sp: 0, k: 0, t: 0.5 }, [0, 0], [0, -20]);
check("4.9 aperçu d'un segment droit : il se déplace avec ses deux ancres (moteur : « a straight segment moves »)", eq(apS.subpaths[0].knots[0].anchor, [20, 0]) && eq(apS.subpaths[0].knots[1].anchor, [100, 0]));
const apC = apercuEdition(P, { type: "convertir", sp: 0, k: 1 }, [100, 20], [140, 30]);
check("4.10 aperçu de Conversion (glisser) : poignée d'entrée symétrique (moteur 2e)", eq(apC.subpaths[0].knots[1].in, [60, 10]) && apC.subpaths[0].knots[1].smooth === true);
const lisse = { subpaths: [{ knots: [{ anchor: [50, 50], in: [40, 50], out: [60, 50], smooth: true }] }] };
const apH = apercuEdition(lisse, { type: "poignee", sp: 0, k: 0, h: "out", de: [60, 50], independant: false }, [0, 0], [0, 10]);
check("4.11 aperçu d'une poignée d'un point lisse : l'autre reste alignée, à sa longueur", Math.abs(apH.subpaths[0].knots[0].in[1] - 40) < 1e-9 === false
  && Math.abs(Math.hypot(apH.subpaths[0].knots[0].in[0] - 50, apH.subpaths[0].knots[0].in[1] - 50) - 10) < 1e-9);

/* 5 — Ajout / Suppression de point d'ancrage */
check("5.1 Alt échange Ajout et Suppression", outilAncre("addAnchorPoint", true) === "deleteAnchorPoint" && outilAncre("deleteAnchorPoint", true) === "addAnchorPoint"
  && outilAncre("addAnchorPoint", false) === "addAnchorPoint" && outilAncre("pen", true) === "pen");
check("5.2 Ajout sur un segment -> path.addAnchor {t}", eq(commandeAncre("addAnchorPoint", { type: "segment", sp: 0, k: 0, t: 0.25 }, W),
  { command: "path.addAnchor", params: { name: "work", subpath: 0, knot: 0, t: 0.25 } }));
check("5.3 Suppression sur une ancre -> path.deleteAnchor", eq(commandeAncre("deleteAnchorPoint", { type: "ancre", sp: 0, k: 2 }, W),
  { command: "path.deleteAnchor", params: { name: "work", subpath: 0, knot: 2 } }));
check("5.4 Ajout sur une ancre, Suppression sur un segment : rien (amont)", commandeAncre("addAnchorPoint", { type: "ancre", sp: 0, k: 0 }, W) === null
  && commandeAncre("deleteAnchorPoint", { type: "segment", sp: 0, k: 0, t: 0.5 }, W) === null);
check("5.5 Suppr de la Sélection directe : de la dernière ancre à la première", eq(ordreSuppression([[0, 1], [1, 0], [0, 3]]), [[1, 0], [0, 3], [0, 1]]));
const sup = commandesSuppression(P, [[0, 0], [0, 2]], W, "k");
check("5.6 Suppr : une commande par ancre, même clé coalesce (un état)", sup.length === 2 && sup.every((c) => c.command === "path.deleteAnchor" && c.params.coalesce === "k") && sup[0].params.knot === 2);
check("5.7 toutes les ancres choisies : le tracé entier (path.delete) ; jamais la forme d'un calque ; rien choisi : rien",
  eq(commandesSuppression(P, [[0, 0], [0, 1], [0, 2]], W, "k"), [{ command: "path.delete", params: { name: "work" } }])
  && eq(commandesSuppression(P, [[0, 0], [0, 1], [0, 2]], { type: "forme" }, "k"), []) && eq(commandesSuppression(P, [], W, "k"), []));

/* 6 — Plume de courbure et Plume libre */
const nc = noeudsCourbure([[20, 100], [60, 30], [120, 90]], [false, false, false], false);
check("6.1 aperçu de courbure : extrémités ouvertes rentrées, ancre du milieu lisse (tangente des voisines)", eq(nc[0].in, nc[0].anchor) && eq(nc[0].out, nc[0].anchor) && nc[1].smooth
  && Math.abs((nc[1].out[1] - nc[1].in[1]) / (nc[1].out[0] - nc[1].in[0]) - (90 - 100) / (120 - 20)) < 1e-9);
check("6.2 un angle (double-clic) reste un angle", eq(noeudsCourbure([[0, 0], [10, 10], [20, 0]], [false, true, false], false)[1].in, [10, 10]));
const cc = commandesCourbure("trace", [[20, 100], [60, 30], [120, 90]], [false, false, false], false, "#000000", "pl-courbure-x");
check("6.3 fin de courbure (Tracé) : path.set puis path.moveAnchors curvature, MÊME clé coalesce (un état)", cc.length === 2 && cc[0].command === "path.set"
  && cc[0].params.path.subpaths[0].knots.every((k) => k.smooth && eq(k.in, k.anchor)) && cc[1].command === "path.moveAnchors" && cc[1].params.curvature === true
  && eq(cc[1].params.move, [0, 0]) && cc[0].params.coalesce === "pl-courbure-x" && cc[1].params.coalesce === "pl-courbure-x");
const cf = commandesCourbure("forme", [[20, 100], [60, 30], [120, 90]], [false, false, false], true, "#123456", "k");
check("6.4 mode Forme fermé : shape.create rempli de la couleur, puis recalcul sur name layer", cf[0].command === "shape.create" && cf[0].params.fill === "#123456"
  && cf[0].params.path.subpaths[0].closed && cf[1].params.name === "layer");
check("6.5 que des angles : pas de recalcul ; moins de deux ancres : rien", commandesCourbure("trace", [[0, 0], [10, 0]], [true, true], false, "#000", "k").length === 1
  && commandesCourbure("trace", [[0, 0]], [false], false, "#000", "k") === null);
check("6.6 simplifier (RDP) : une droite bruitée -> ses deux bouts ; un L -> trois points", eq(simplifier([[0, 0], [5, 0.3], [10, -0.2], [20, 0]], 1), [[0, 0], [20, 0]])
  && simplifier([[0, 0], [10, 0], [20, 0], [20, 10], [20, 20]], 1).length === 3);
check("6.7 angles vifs : le coin d'un L, pas une courbe douce", eq(anglesVifs([[0, 0], [20, 0], [20, 20]]), [false, true, false]) && eq(anglesVifs([[0, 0], [10, 2], [20, 0]]), [false, false, false]));
const tl = traceLibre([[0, 0], [10, 0], [20, 0], [20, 10], [20, 20], [10, 20], [0, 20], [0, 10], [0, 0.5]], 2, 6);
check("6.8 Plume libre : revenir au départ ferme (dernier point retiré) ; ancres et angles", tl && tl.ferme === true && tl.ancres.length === 4 && tl.angles.filter(Boolean).length === 4, tl);
check("6.9 un clic ne trace rien ; ajustement borné 0,5..10", traceLibre([[5, 5], [5, 5]], 2, 6) === null && AJUSTEMENT.min === 0.5 && AJUSTEMENT.max === 10
  && traceLibre([[0, 0], [5, 0.4], [10, 0]], 9999, 1).ancres.length === 2);

/* 7 — menu des tracés */
const ids = (e) => entreesMenuTrace(e).filter(Boolean).filter((x) => x.actif).map((x) => x.id);
check("7.1 tracé de travail : sélection, remplir, contour, transformer ; détourage refusé (il faut un tracé enregistré)", eq(ids({ nom: "work" }), ["path.toSelection", "path.fill", "path.stroke", "path.transform"]));
check("7.2 tracé enregistré : + Tracé de détourage ; Retirer seulement s'il y en a un", ids({ nom: "Tracé 1" }).includes("path.clippingPath.set") && !ids({ nom: "Tracé 1" }).includes("path.clippingPath.clear")
  && ids({ nom: "Tracé 1", detourage: true }).includes("path.clippingPath.clear"));
check("7.3 calque de forme : copier selon fond / contour ; coller seulement après une copie", eq(ids({ nom: "layer", forme: { fond: true, contour: false }, presse: {} }), ["path.toSelection", "path.transform", "path.style.copyFill"])
  && ids({ nom: "layer", forme: { fond: true, contour: true }, presse: { fond: true, contour: true } }).includes("path.style.pasteStroke"));
check("7.4 sans tracé : tout grisé sauf rien", eq(ids({}), []));
check("7.5 dialogue Transformer : bornes et défauts de l'amont (translation ±30000, échelle 0,01..100 = 1, angle ±360)",
  eq(CHAMPS_TRANSFORMER.map((c) => [c.cle, c.min, c.max, c.defaut]), [["translateX", -30000, 30000, 0], ["translateY", -30000, 30000, 0], ["scaleX", 0.01, 100, 1], ["scaleY", 0.01, 100, 1], ["angle", -360, 360, 0]])
  && eq(CHAMPS_DETOURAGE.map((c) => [c.cle, c.min, c.max, c.defaut]), [["flatness", 0, 100, 0]]));

/* 8 — texte */
check("8.1 masques et vertical", estMasque("horizontalTypeMask") && estMasque("verticalTypeMask") && !estMasque("type") && estVertical("verticalType") && estVertical("verticalTypeMask") && !estVertical("horizontalTypeMask"));
check("8.2 bouton Orientation : l'outil jumeau", jumeau("type") === "verticalType" && jumeau("verticalType") === "type" && jumeau("horizontalTypeMask") === "verticalTypeMask" && jumeau("move") === "move");
const pm = paramsMasque({ x: 20, y: 100 }, "ABC", { ...DEFAUT_TEXTE, size: 40 }, "verticalTypeMask", "add");
check("8.3 masque de texte -> type.createSelection (texte temporaire, operation, vertical) ; jamais de couleur ni de calque", pm.text === "ABC" && pm.operation === "add" && pm.orientation === "vertical"
  && pm.size === 40 && !("color" in pm) && !("layer" in pm) && !("removeLayer" in pm));
check("8.4 mode Nouvelle -> operation new ; texte vide -> rien", paramsMasque({ x: 0, y: 0 }, "A", DEFAUT_TEXTE, "horizontalTypeMask").operation === "new" && !("orientation" in paramsMasque({ x: 0, y: 0 }, "A", DEFAUT_TEXTE, "horizontalTypeMask"))
  && paramsMasque({ x: 0, y: 0 }, "  ", DEFAUT_TEXTE, "horizontalTypeMask") === null);
check("8.5 Texte vertical : type.create orientation vertical ; horizontal : rien d'ajouté (comme avant)", paramsCreation({ x: 1, y: 2 }, "a", { ...DEFAUT_TEXTE, orientation: "vertical" }, "#000000").orientation === "vertical"
  && !("orientation" in paramsCreation({ x: 1, y: 2 }, "a", DEFAUT_TEXTE, "#000000")));
const ligne = { closed: false, knots: [K(20, 100), K(180, 100)] };
// (poignées rentrées : le paramètre t n'est pas proportionnel à la longueur — on compare au point du segment)
check("8.6 longueur le long du tracé jusqu'au point touché", Math.abs(longueurJusqua(ligne, 0, 0.25) - (pointSegment(ligne.knots[0], ligne.knots[1], 0.25)[0] - 20)) < 0.01
  && longueurJusqua(ligne, 1, 0) === 160 && longueurJusqua(ligne, 0, 0) === 0);
const st = surTrace([{ path: { subpaths: [ligne] } }], [60, 101], 6);
check("8.7 clic de l'outil Texte sur le tracé de travail -> {subpath, start ≈ 40 px}", st && st.subpath === 0 && Math.abs(st.start - 40) < 0.5 && !("shape" in st), st);
check("8.8 sur la forme active -> + shape (id du calque) ; hors tracé -> null", surTrace([{ path: { subpaths: [ligne] }, shape: 7 }], [180, 99], 6).shape === 7
  && surTrace([{ path: { subpaths: [ligne] } }], [60, 60], 6) === null);
const k = (o) => commandeTaille({ ctrlKey: true, shiftKey: true, ...o });
check("8.9 Ctrl+Maj+. / , = taille ± ; avec Alt : de 10 ; sans Maj : rien", k({ code: "Period" }) === "type.increaseSize" && k({ code: "Comma" }) === "type.decreaseSize"
  && k({ key: ">", altKey: true }) === "type.increaseSizeMore" && k({ key: "<", altKey: true }) === "type.decreaseSizeMore"
  && commandeTaille({ ctrlKey: true, code: "Period" }) === null && k({ code: "KeyA" }) === null);
check("8.10 texte sur un tracé : type.info shape = {Path}", surUnTrace({ shape: { Path: { start: 10 } } }) && !surUnTrace({ shape: "Point" }) && !surUnTrace(null));

/* 9 — dessin (aucune régression) */
check("9.1 dChemin d'un tracé à deux segments : M puis deux C", (dChemin(P, (x, y) => ({ x, y })).match(/C/g) || []).length === 2);

/* 10 — noms d'historique relevés sur le vrai moteur */
for (const n of ["Work Path", "New Shape Layer", "New Type Layer", "Drag Anchor Points", "Drag Direction Point", "Drag Segment", "Convert Point", "Add Anchor Point",
  "Delete Anchor Point", "Transform Path", "Clipping Path", "Clear Clipping Path", "Paste Fill", "Paste Complete Stroke", "Type Mask", "Change Type Size", "Release Type from Path", "Type on a Path", "Save Path", "Delete Path"]) {
  check(`10 « ${n} » a une clé dans ETATS_MOTEUR, traduite`, /^photolab\./.test(ETATS_MOTEUR[n] || "") && dico[ETATS_MOTEUR[n]] && dico[ETATS_MOTEUR[n]].en, ETATS_MOTEUR[n]);
}

console.log(`traces-m5 : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
