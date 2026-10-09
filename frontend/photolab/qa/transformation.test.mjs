// qa/transformation.test.mjs — t154 (parité L4) : Transformation libre et Transformation › — fonctions PURES de
// mod-transformer.js (homographie, cadre source, prise des poignées, gestes, champs, commande) et branchement.
import { MODES, coins, carreVersQuad, appliquer, inverse, cadreSource, etatInitial, prise, sorteGeste, geste, lecture,
  placerPivot, echelleAutour, rotationAutour, inclinerAutour, pointReference, estIdentite, commande, curseur, LIB_MODES, LIB_INTERP,
  INTERPOLATIONS } from "../js/mod-transformer.js";
import { TRAITES_PAR_ECRAN, NECESSITE_DOC } from "../js/mod-menus.js";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const pres = (a, b, e = 1e-6) => Math.abs(a - b) < e;
const ppres = (p, q, e = 1e-6) => pres(p[0], q[0], e) && pres(p[1], q[1], e);
const qpres = (A, B, e = 1e-6) => A.every((p, i) => ppres(p, B[i], e));
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");

// 1. homographie
const R = [20, 20, 60, 50];
const Q = coins(R);
check("1.1 coins : HG, HD, BD, BG", JSON.stringify(Q) === JSON.stringify([[20, 20], [60, 20], [60, 50], [20, 50]]));
const Ha = carreVersQuad(Q);
check("1.2 parallélogramme -> affine (g = h = 0) ; (0,0) -> HG, (1,1) -> BD", Ha[6] === 0 && Ha[7] === 0 && ppres(appliquer(Ha, [0, 0]), [20, 20]) && ppres(appliquer(Ha, [1, 1]), [60, 50]));
const Qp = [[10, 10], [90, 0], [100, 80], [0, 60]];
const Hp = carreVersQuad(Qp);
check("1.3 perspective : les quatre coins unité tombent sur le quadrilatère", [[0, 0], [1, 0], [1, 1], [0, 1]].every((u, i) => ppres(appliquer(Hp, u), Qp[i], 1e-9)));
const Hi = inverse(Hp);
check("1.4 inverse : aller-retour exact", ppres(appliquer(Hi, appliquer(Hp, [0.3, 0.7])), [0.3, 0.7], 1e-9));
check("1.5 inverse d'une matrice dégénérée : null", inverse([0, 0, 0, 0, 0, 0, 0, 0, 1]) === null);

// 2. cadre source
const doc = { activeLayer: 3, hasSelection: false, layers: [{ id: 3, kind: "Pixel", name: "Layer 1", bounds: [20, 20, 40, 30] }, { id: 2, kind: "Pixel", name: "Background", bounds: [0, 0, 200, 100] }] };
check("2.1 cadre = contenu du calque", JSON.stringify(cadreSource(doc)) === JSON.stringify({ calque: 3, rect: [20, 20, 60, 50] }));
check("2.2 avec sélection : contenu ∩ sélection", JSON.stringify(cadreSource({ ...doc, hasSelection: true, selectionBounds: [40, 0, 100, 30] }).rect) === "[40,20,60,30]");
check("2.3 sélection hors du contenu : vide", cadreSource({ ...doc, hasSelection: true, selectionBounds: [100, 0, 10, 10] }).erreur === "vide");
check("2.4 arrière-plan sans sélection : refusé (amont)", cadreSource({ ...doc, activeLayer: 2 }).erreur === "fond");
check("2.5 arrière-plan avec sélection : admis", JSON.stringify(cadreSource({ ...doc, activeLayer: 2, hasSelection: true, selectionBounds: [0, 0, 10, 10] }).rect) === "[0,0,10,10]");
check("2.6 calque de réglage sans masque : refusé", cadreSource({ ...doc, activeLayer: 4, layers: [{ id: 4, kind: "Adjustment", hasMask: false, bounds: null }, ...doc.layers] }).erreur === "reglage");
check("2.7 calque vide : refusé", cadreSource({ ...doc, layers: [{ id: 3, kind: "Pixel", name: "L", bounds: [0, 0, 0, 0] }, doc.layers[1]] }).erreur === "vide");
check("2.8 calque dans un groupe : trouvé", cadreSource({ activeLayer: 7, layers: [{ id: 6, kind: "Group", children: [{ id: 7, kind: "Pixel", name: "x", bounds: [1, 2, 3, 4] }] }] }).rect.join() === "1,2,4,6");
const e0 = etatInitial(R);
check("2.9 état initial : coins, point de référence au centre", qpres(e0.quad, Q) && ppres(e0.pivot, [40, 35]) && e0.inclH === 0);

// 3. prise (écran = document × 2)
const ecran = (x, y) => ({ x: x * 2, y: y * 2 });
const P = (sx, sy) => prise(e0, { x: sx, y: sy }, ecran);
check("3.1 coin HG à 12 px près", JSON.stringify(P(45, 45)) === JSON.stringify({ type: "coin", i: 0 }) && P(40 + 13, 40).type !== "coin");
check("3.2 milieu du bord droit", JSON.stringify(P(120, 70)) === JSON.stringify({ type: "bord", i: 1 }));
check("3.3 point de référence", P(80, 70).type === "pivot");
check("3.4 dedans / dehors", P(60, 90).type === "dedans" && P(200, 200).type === "dehors");

// 4. sorte de geste selon mode et modificateurs
const C0 = { type: "coin", i: 0 }, B1 = { type: "bord", i: 1 };
check("4.1 libre : coin = échelle ; Ctrl = déformation ; Ctrl+Alt+Maj = perspective", sorteGeste(C0, "libre") === "echelle"
  && sorteGeste(C0, "libre", { ctrl: true }) === "deformation" && sorteGeste(C0, "libre", { ctrl: true, alt: true, maj: true }) === "perspective");
check("4.2 libre : bord = échelle ; Ctrl+bord = inclinaison ; dehors = rotation ; dedans = déplacer", sorteGeste(B1, "libre") === "echelle"
  && sorteGeste(B1, "libre", { ctrl: true }) === "inclinaison" && sorteGeste({ type: "dehors" }, "libre") === "rotation" && sorteGeste({ type: "dedans" }, "libre") === "deplacer");
check("4.3 sous-modes : Rotation tourne partout ; Mise à l'échelle ne tourne pas dehors", sorteGeste(C0, "rotation") === "rotation"
  && sorteGeste({ type: "dedans" }, "rotation") === "rotation" && sorteGeste({ type: "dehors" }, "echelle") === "rien");
check("4.4 sous-modes : Déformation et Perspective sur les coins, Inclinaison sur les bords", sorteGeste(C0, "deformation") === "deformation"
  && sorteGeste(C0, "perspective") === "perspective" && sorteGeste(B1, "inclinaison") === "inclinaison" && sorteGeste(C0, "inclinaison") === "coinAxe");
check("4.5 point de référence : toujours le déplacer", sorteGeste({ type: "pivot" }, "rotation") === "pivot");

// 5. gestes
let e = geste(e0, { type: "dedans" }, [30, 30], [80, 30], "libre");
check("5.1 déplacer : quad et point de référence suivent, e0 intact", qpres(e.quad, coins([70, 20, 110, 50])) && ppres(e.pivot, [90, 35]) && qpres(e0.quad, Q));
e = geste(e0, { type: "dedans" }, [0, 0], [10, 1], "libre", { maj: true });
check("5.2 déplacer + Maj : 8 directions (horizontal)", pres(e.quad[0][1], 20, 1e-9) && e.quad[0][0] > 29);
e = geste(e0, { type: "coin", i: 2 }, [60, 50], [100, 60], "libre");
check("5.3 coin BD : homothétie proportionnelle, coin HG fixe", ppres(e.quad[0], [20, 20]) && pres((e.quad[1][0] - 20) / 40, (e.quad[3][1] - 20) / 30, 1e-9) && pres(e.quad[2][0], 100, 1e-9), e.quad);
e = geste(e0, { type: "coin", i: 2 }, [60, 50], [100, 60], "libre", { maj: true });
check("5.4 coin + Maj : libre (le coin va sous le pointeur)", ppres(e.quad[2], [100, 60]) && ppres(e.quad[0], [20, 20]));
e = geste(e0, { type: "coin", i: 2 }, [60, 50], [80, 65], "libre", { alt: true, maj: true });
check("5.5 coin + Alt : symétrique autour du point de référence", ppres(e.quad[0], [0, 5]) && ppres(e.quad[2], [80, 65]) && ppres(e.pivot, [40, 35]), e.quad);
e = geste(e0, { type: "bord", i: 1 }, [60, 35], [80, 99], "libre");
check("5.6 bord droit : un seul axe", ppres(e.quad[1], [80, 20]) && ppres(e.quad[2], [80, 50]) && ppres(e.quad[0], [20, 20]));
e = geste(e0, { type: "dehors" }, [40, 0], [75, 35], "libre");
check("5.7 rotation de 90° autour du point de référence", ppres(e.quad[0], [55, 15]) && ppres(e.pivot, [40, 35]), e.quad);
e = geste(e0, { type: "dehors" }, [40, 0], [44, 0.4], "libre", { maj: true });
check("5.8 rotation + Maj : pas de 15° (petit geste -> 0°)", qpres(e.quad, Q, 1e-9));
e = geste(e0, { type: "dehors" }, [40, 0], [60, 10], "libre", { maj: true });
const ang = Math.atan2(e.quad[1][1] - e.quad[0][1], e.quad[1][0] - e.quad[0][0]) * 180 / Math.PI;
check("5.9 rotation + Maj : angle multiple de 15°", pres(ang % 15, 0, 1e-6) || pres(Math.abs(ang % 15), 15, 1e-6), ang);
e = geste(e0, C0, [20, 20], [25, 28], "libre", { ctrl: true });
check("5.10 Ctrl+coin : déformation libre (seul ce coin bouge)", ppres(e.quad[0], [25, 28]) && qpres(e.quad.slice(1), Q.slice(1)));
e = geste(e0, C0, [20, 20], [30, 22], "libre", { ctrl: true, alt: true, maj: true });
check("5.11 perspective horizontale : le coin apparié part à l'opposé", ppres(e.quad[0], [30, 20]) && ppres(e.quad[1], [50, 20]) && qpres(e.quad.slice(2), Q.slice(2)), e.quad);
e = geste(e0, { type: "coin", i: 3 }, [20, 50], [21, 60], "perspective");
check("5.12 perspective verticale (mode) : BG et HG s'écartent", ppres(e.quad[3], [20, 60]) && ppres(e.quad[0], [20, 10]));
e = geste(e0, { type: "bord", i: 0 }, [40, 20], [50, 25], "libre", { ctrl: true });
check("5.13 Ctrl+bord haut : inclinaison (les deux coins du bord)", ppres(e.quad[0], [30, 25]) && ppres(e.quad[1], [70, 25]) && qpres(e.quad.slice(2), Q.slice(2)));
e = geste(e0, { type: "bord", i: 0 }, [40, 20], [50, 25], "libre", { ctrl: true, maj: true });
check("5.14 Ctrl+Maj+bord : le long du bord", ppres(e.quad[0], [30, 20]) && ppres(e.quad[1], [70, 20]));
e = geste(e0, { type: "pivot" }, [40, 35], [22, 21], "libre");
check("5.15 glisser le point de référence", ppres(e.pivot, [22, 21]) && qpres(e.quad, Q));
e = geste(e0, { type: "coin", i: 0 }, [20, 20], [21, 30], "inclinaison");
check("5.16 Inclinaison : un coin suit l'axe dominant", ppres(e.quad[0], [20, 30]));

// 6. champs
const L0 = lecture(e0, R, e0.pivot);
check("6.1 lecture initiale : X/Y = centre, 100 %, 0°", L0.x === 40 && L0.y === 35 && L0.l === 100 && L0.h === 100 && L0.angle === 0 && L0.inclH === 0);
check("6.2 Δ : relatif au départ", lecture(placerPivot(e0, 50, 30), R, e0.pivot, true).x === 10);
e = echelleAutour(e0, 2, 0.5);
check("6.3 échelle 200 % / 50 % autour du centre", ppres(e.quad[0], [0, 27.5]) && lecture(e, R, e0.pivot).l === 200 && lecture(e, R, e0.pivot).h === 50);
check("6.4 échelle nulle ou non finie : inchangé", echelleAutour(e0, 0, 1) === e0 && echelleAutour(e0, Infinity, 1) === e0);
e = rotationAutour(e0, 30);
check("6.5 rotation : angle lu = 30°", lecture(e, R, e0.pivot).angle === 30);
e = inclinerAutour(e0, "h", 45);
check("6.6 inclinaison H 45° : le haut part à gauche, le bas à droite ; cumulée", ppres(e.quad[0], [5, 20]) && ppres(e.quad[3], [35, 50]) && e.inclH === 45);
e = inclinerAutour(e0, "v", 45);
check("6.7 inclinaison V 45° : le coin HG (20 px à gauche du centre) monte de 20 px", ppres(e.quad[0], [20, 0]) && e.inclV === 45, e.quad);
check("6.8 point de référence : grille 3 × 3", ppres(pointReference(e0, 0).pivot, [20, 20]) && ppres(pointReference(e0, 8).pivot, [60, 50]) && ppres(pointReference(e0, 4).pivot, [40, 35]));
check("6.9 placer le point de référence déplace le cadre", qpres(placerPivot(e0, 50, 35).quad, coins([30, 20, 70, 50])));

// 7. commande
check("7.1 cadre inchangé : aucune commande (aucun état d'historique)", commande(e0, R, 3) === null && estIdentite(e0, R));
const c = commande(geste(e0, { type: "dedans" }, [0, 0], [50, 0], "libre"), R, 3, "nearest");
check("7.2 commande : edit.transform {layer, rect, quad, interpolation}", c.command === "edit.transform" && c.params.layer === 3 && c.params.rect.join() === "20,20,60,50"
  && JSON.stringify(c.params.quad) === "[[70,20],[110,20],[110,50],[70,50]]" && c.params.interpolation === "nearest");
check("7.3 interpolation inconnue -> bicubique", commande(rotationAutour(e0, 10), R, 3, "zorg").params.interpolation === "bicubic");
check("7.4 coordonnées arrondies au millième", commande(rotationAutour(e0, 10), R, 3).params.quad.flat().every((v) => Math.abs(v * 1000 - Math.round(v * 1000)) < 1e-6));
check("7.5 curseurs", curseur({ type: "coin", i: 0 }, "libre") === "nwse-resize" && curseur({ type: "bord", i: 1 }, "libre") === "ew-resize"
  && curseur({ type: "dehors" }, "libre") === "alias" && curseur({ type: "dehors" }, "echelle") === "default" && curseur({ type: "dedans" }, "rotation") === "alias");

// 8. branchement
const ids = Object.keys(MODES);
check("8.1 six entrées servies par l'écran, document requis", ids.length === 6 && ids.every((id) => TRAITES_PAR_ECRAN.has(id) && NECESSITE_DOC.has(id)));
check("8.2 libellés des modes et des interpolations écrits en entier", Object.values(MODES).every((m) => LIB_MODES[m]) && INTERPOLATIONS.every((i) => LIB_INTERP[i]));
const gestes = readFileSync(join(racine, "js", "mod-gestes.js"), "utf8"), core = readFileSync(join(racine, "js", "core.js"), "utf8");
check("8.3 le répartiteur passe la main à la session avant l'outil courant", /\(PL\.gestesPrioritaires && PL\.gestesPrioritaires\(\)\) \|\| PL\.gestes\[PL\.etat\.outil\]/.test(gestes)
  && /PL\.dessinerTransformation\(svg, el, ecran\)/.test(gestes));
check("8.4 core.js initialise la transformation après les gestes", core.indexOf("initTransformer(PL)") > core.indexOf("initGestes(PL)") && core.indexOf("initTransformer(PL)") > core.indexOf("initOutils(PL)"));

console.log(`transformation : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
