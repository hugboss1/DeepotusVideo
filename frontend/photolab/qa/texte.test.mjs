// qa/texte.test.mjs — t156 (parité L6) : texte, formes, plume, tracés, Formes / Styles, Rechercher — fonctions PURES de
// mod-texte, mod-formes, mod-trace, mod-recherche, mod-presets (genres formes et styles), et branchement.
import { DEFAUT_TEXTE, stylesDe, nomStyle, couleurHex, lecture, alignDe, alignMoteur, calqueTexteSous, placement, paramsCreation,
  paramsEdition, paramsStyle, CATEGORIES, caracteres, recents, pointDeCode, decorerTexte, basculerPref, APERCUS, LANGUES, COMPOSEUR,
  PREFS_DEFAUT, PANNEAUX_TEXTE, NOMS_POIDS, ALIGNS, LIB_ALIGNS } from "../js/mod-texte.js";
import { OUTILS_FORME, FORMES_DEFAUT, geometrie, tropPetite, sommetsPolygone, apercuForme, peinture, commandeForme } from "../js/mod-formes.js";
import { noeudAngle, tirerPoignee, fermeLeTrace, chemin, commandePlume, dChemin, deplacerChemin, bornes, lignesTraces, cibleSelection,
  commandeDeplacement, nomLibre } from "../js/mod-trace.js";
import { entreesCherchables, score, chercher } from "../js/mod-recherche.js";
import { groupesDe, COMMANDES, ECRANS, urlVignette, nomAffiche, NOMS_INTEGRES } from "../js/mod-presets.js";
import { EMPLACEMENTS } from "../js/mod-outils.js";
import { TRAITES_PAR_ECRAN } from "../js/mod-menus.js";
import { GROUPES, PANNEAUX } from "../js/mod-espaces.js";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const pres = (a, b, e = 1e-6) => Math.abs(a - b) < e;
const t = (c) => "«" + c + "»";
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");

// 1. texte : polices, lecture de type.info
check("1.1 défaut de l'amont : Inter, 48 pt, gauche, lissage net", DEFAUT_TEXTE.font === "Inter" && DEFAUT_TEXTE.size === 48 && DEFAUT_TEXTE.align === "left" && DEFAUT_TEXTE.antialias === "sharp");
const ss = stylesDe([{ weight: 700, italic: true }, { weight: 400, italic: false }, { weight: 400, italic: false }, { weight: 450, italic: false }, { weight: 700, italic: false }]);
check("1.2 styles d'une police : sans doublon, triés, poids arrondis à la centaine", eq(ss, [{ weight: 400, italic: false }, { weight: 500, italic: false }, { weight: 700, italic: false }, { weight: 700, italic: true }]), ss);
check("1.3 nom d'un style : poids + italique", nomStyle({ weight: 700, italic: true }, t) === t(NOMS_POIDS[700]) + " " + t("photolab.texte.italique"));
check("1.4 couleur du moteur {c:[r,g,b,a]} -> hex", couleurHex({ c: [1, 0.5, 0, 1] }) === "#ff8000" && couleurHex(null) === "#000000" && couleurHex([0, 0, 1]) === "#0000ff");
const info = { text: "Bonjour monde", antialias: "Smooth", orientation: "Horizontal", shape: "Point",
  runs: [{ start: 0, end: 7, style: { font_family: "Arial", weight: 700, italic: false, size_pt: 36, leading_pt: null, kerning: "Metrics", tracking: 20, vertical_scale: 1, horizontal_scale: 1.5,
    baseline_shift_pt: 0, color: { c: [1, 0, 0, 1] }, faux_bold: true, faux_italic: false, caps: "All", underline: false, strikethrough: true } },
  { start: 7, end: 13, style: { font_family: "Inter", weight: 400, size_pt: 24, color: { c: [0, 0, 0, 1] }, caps: "Normal" } }],
  paragraphs: [{ start: 0, end: 13, style: { align: "Center", auto_leading: 1.2, start_indent_pt: 6, end_indent_pt: 0, first_line_indent_pt: 0, space_before_pt: 3, space_after_pt: 0, hyphenate: true, direction: "Auto" } }] };
const v0 = lecture(info, 0), v9 = lecture(info, 9);
check("1.5 lecture au début : police, poids, taille, interlignage auto, crénage, approche, échelle %", v0.font === "Arial" && v0.weight === 700 && v0.size === 36 && v0.leading === "auto"
  && v0.kerning === "metrics" && v0.tracking === 20 && v0.horizontalScale === 150 && v0.verticalScale === 100, v0);
check("1.6 lecture : couleur, faux gras, capitales, barré", v0.color === "#ff0000" && v0.fauxBold && v0.caps === "all" && v0.strikethrough && !v0.underline);
check("1.7 lecture : paragraphe (centré, retrait, espace avant, césure)", v0.align === "center" && v0.startIndent === 6 && v0.spaceBefore === 3 && v0.hyphenate);
check("1.8 lecture à la position 9 : la deuxième plage", v9.font === "Inter" && v9.size === 24 && v9.color === "#000000");
check("1.9 lecture sans info : null", lecture(null) === null && lecture({ runs: [] }) === null);
check("1.10 alignements du moteur -> écran ; écran -> moteur (justify)", alignDe("JustifyAll") === "justifyAll" && alignDe("Justify") === "justifyLeft" && alignDe("zorg") === "left"
  && alignMoteur("justifyLeft") === "justify" && alignMoteur("center") === "center");
check("1.11 sept alignements, libellés écrits en entier", ALIGNS.length === 7 && ALIGNS.every((a) => LIB_ALIGNS[a]));

// 2. texte : création, édition, styles
const doc = { layers: [{ id: 5, kind: "Type", visible: true, bounds: [20, 40, 100, 30] }, { id: 4, kind: "Type", visible: false, bounds: [0, 0, 300, 200] }, { id: 2, kind: "Pixel", bounds: [0, 0, 300, 200] }] };
check("2.1 calque de texte sous le point (marge 6 px) ; invisible et pixel ignorés", calqueTexteSous(doc, [18, 50]).id === 5 && calqueTexteSous(doc, [200, 150]) === null);
check("2.2 clic = texte de point (ligne de base au point)", eq(placement([20, 30], [21, 31], 1), { x: 20, y: 30 }));
check("2.3 glisser ≥ 4 px écran sur les deux axes = boîte", eq(placement([20, 30], [120, 80], 1), { box: [20, 30, 100, 50] }) && eq(placement([20, 30], [21.5, 31.5], 4), { box: [20, 30, 1.5, 1.5] }));
check("2.4 glisser trop plat : texte de point", "x" in placement([20, 30], [120, 31], 1));
const pc = paramsCreation({ x: 1, y: 2 }, "Salut", { ...DEFAUT_TEXTE, align: "justifyLeft" }, "#123456");
check("2.5 type.create : texte, police, poids, taille, couleur, alignement moteur", pc.text === "Salut" && pc.font === "Inter" && pc.weight === 400 && pc.size === 48 && pc.color === "#123456" && pc.align === "justify" && pc.x === 1);
check("2.6 texte vide ou blanc : aucun calque", paramsCreation({ x: 0, y: 0 }, "  \n ", DEFAUT_TEXTE, "#000000") === null);
check("2.7 type.edit seulement si le texte a changé", paramsEdition(5, "a", "a") === null && eq(paramsEdition(5, "a", "b"), { layer: 5, text: "b" }));
check("2.8 champs -> type.setStyle", eq(paramsStyle("style", { weight: 700, italic: true }), { weight: 700, italic: true }) && eq(paramsStyle("leading", "auto"), { leading: "auto" })
  && eq(paramsStyle("leading", "18"), { leading: 18 }) && eq(paramsStyle("kerning", "optical"), { kerning: "optical" }) && eq(paramsStyle("kerning", "-50"), { kerning: -50 })
  && eq(paramsStyle("align", "justifyLeft"), { align: "justify" }) && eq(paramsStyle("size", 12), { size: 12 }));

// 3. glyphes et menu Texte
check("3.1 catégories de l'amont", CATEGORIES.length === 11 && CATEGORIES[0].id === "latinBase");
const lat = caracteres("latinBase");
check("3.2 latin de base : ! à ~ (94 caractères)", lat.length === 94 && lat[0] === "!" && lat[93] === "~");
check("3.3 latin 1 sans les codes de contrôle", caracteres("latin1").every((c) => c.codePointAt(0) >= 0xa1));
check("3.4 monnaies : €", caracteres("monnaies").includes("€") && pointDeCode("€") === "U+20AC");
check("3.5 récents : tête, sans doublon, 12 au plus", eq(recents(["a", "b"], "b"), ["b", "a"]) && recents([..."abcdefghijkl"], "z").length === 12);
const menus = [{ entrees: [{ type: "sous-menu", entrees: [{ type: "commande", id: "type.fontPreviewSize.large", etat: "bientot" },
  { type: "commande", id: "type.languageOptions.eastAsianFeatures", etat: "bientot" }, { type: "commande", id: COMPOSEUR, etat: "bientot" },
  { type: "commande", id: "type.panels.glyphs", etat: "bientot" }] }] }];
const dec = decorerTexte(menus, { apercu: "type.fontPreviewSize.large", langue: "type.languageOptions.eastAsianFeatures", composeur: true });
const plats = dec[0].entrees[0].entrees;
check("3.6 menu Texte : actifs et cochés selon les préférences", plats.every((e) => e.etat === "actif") && plats[0].coche && plats[1].coche && plats[2].coche && plats[3].coche === undefined);
check("3.7 menu Texte : l'arbre reçu n'est pas modifié", menus[0].entrees[0].entrees[0].etat === "bientot");
check("3.8 préférences : radio pour l'aperçu et la langue, bascule pour le composeur",
  basculerPref(PREFS_DEFAUT, "type.fontPreviewSize.huge").apercu === "type.fontPreviewSize.huge" && basculerPref(PREFS_DEFAUT, LANGUES[2]).langue === LANGUES[2]
  && basculerPref(PREFS_DEFAUT, COMPOSEUR).composeur === true && basculerPref({ ...PREFS_DEFAUT, composeur: true }, COMPOSEUR).composeur === false);
check("3.9 tailles d'aperçu croissantes de 11 à 32 px", eq(Object.values(APERCUS), [11, 14, 18, 24, 32]));
check("3.10 Texte › Panneaux -> onglets du groupe Texte", Object.values(PANNEAUX_TEXTE).every((o) => GROUPES.texte.includes(o)) && Object.keys(PANNEAUX_TEXTE).every((id) => PANNEAUX[id] && PANNEAUX[id].groupe === "texte"));

// 4. formes
check("4.1 six outils de forme", eq(OUTILS_FORME, ["rectangle", "ellipseShape", "triangle", "polygon", "line", "customShape"]));
check("4.2 géométrie : rectangle normalisé", eq(geometrie("rectangle", [50, 50], [10, 20]).rect, { x: 10, y: 20, w: 40, h: 30 }));
check("4.3 Maj : carré", eq(geometrie("rectangle", [0, 0], [40, 10], { maj: true }).rect, { x: 0, y: 0, w: 40, h: 40 }));
check("4.4 Alt : depuis le centre", eq(geometrie("rectangle", [50, 50], [60, 70], { alt: true }).rect, { x: 40, y: 30, w: 20, h: 40 }));
const tr = geometrie("line", [0, 0], [10, 2], { maj: true });
check("4.5 trait + Maj : pas de 45° (horizontal)", pres(tr.a[1], 0) && pres(tr.a[0], Math.hypot(10, 2)), tr);
check("4.6 moins d'un pixel : rien", tropPetite(geometrie("rectangle", [0, 0], [0.5, 10])) && commandeForme("rectangle", geometrie("rectangle", [0, 0], [0.5, 10])) === null);
const tri = sommetsPolygone({ x: 0, y: 0, w: 100, h: 60 }, 3);
check("4.7 polygone : premier sommet en haut au milieu, ajusté à la hauteur du cadre", pres(tri[0][0], 50) && pres(tri[0][1], 0) && pres(Math.max(...tri.map((p) => p[1])), 60), tri);
check("4.8 aperçu : ellipse 48 points, polygone N sommets, trait sans contour", apercuForme("ellipseShape", { rect: { x: 0, y: 0, w: 10, h: 10 } }).length === 48
  && apercuForme("polygon", { rect: { x: 0, y: 0, w: 10, h: 10 } }, { cotes: 7 }).length === 7 && apercuForme("line", { de: [0, 0], a: [1, 1] }) === null);
check("4.9 remplissage = premier plan si coché ; contour si épaisseur > 0", eq(peinture({ ...FORMES_DEFAUT }, "#ff0000"), { fill: "#ff0000", stroke: null })
  && eq(peinture({ ...FORMES_DEFAUT, remplir: false, contour: 3, couleurContour: "#00ff00", alignContour: "outside" }, "#f00"), { fill: null, stroke: { width: 3, color: "#00ff00", align: "outside" } }));
const g = geometrie("rectangle", [10, 10], [60, 50]);
check("4.10 rectangle -> shape.create rect ; rayon -> roundedRect", eq(commandeForme("rectangle", g, FORMES_DEFAUT, "#000000").params, { kind: "rect", rect: [10, 10, 50, 40], fill: "#000000", stroke: null })
  && commandeForme("rectangle", g, { ...FORMES_DEFAUT, rayon: 8 }).params.kind === "roundedRect" && commandeForme("rectangle", g, { ...FORMES_DEFAUT, rayon: 8 }).params.radii === 8);
check("4.11 triangle = polygone à 3 côtés ; polygone = côtés bornés 3..100", commandeForme("triangle", g).params.sides === 3 && commandeForme("polygon", g, { ...FORMES_DEFAUT, cotes: 200 }).params.sides === 100
  && commandeForme("ellipseShape", g).params.kind === "ellipse");
const cl = commandeForme("line", geometrie("line", [0, 0], [30, 40]), { ...FORMES_DEFAUT, epaisseur: 5 }, "#abcdef");
check("4.12 trait -> line {from, to, weight}", cl.params.kind === "line" && eq(cl.params.from, [0, 0]) && eq(cl.params.to, [30, 40]) && cl.params.weight === 5);
const cp = commandeForme("customShape", g, FORMES_DEFAUT, "#000000", { preset: "Heart", group: "Symbols" }, { maj: true });
check("4.13 forme personnalisée -> shape.presets.place {preset, group, rect, keepAspect}", cp.command === "shape.presets.place" && cp.params.preset === "Heart" && cp.params.group === "Symbols" && cp.params.keepAspect === true
  && commandeForme("customShape", g, FORMES_DEFAUT, "#000", null) === null);

// 5. plume et tracés
let n = [noeudAngle([0, 0]), noeudAngle([10, 0])];
n = tirerPoignee(n, [14, 4]);
check("5.1 glisser : poignées symétriques, sommet lisse", eq(n[1].out, [14, 4]) && eq(n[1].in, [6, -4]) && n[1].smooth && !n[0].smooth);
check("5.2 tirer sans bouger : reste un angle", tirerPoignee([noeudAngle([5, 5])], [5, 5])[0].smooth === false);
const ecran = (x, y) => ({ x: x * 2, y: y * 2 });
check("5.3 fermer : au moins deux sommets, à 6 px écran du premier", fermeLeTrace(n, { x: 4, y: 4 }, ecran) && !fermeLeTrace(n, { x: 10, y: 10 }, ecran) && !fermeLeTrace([n[0]], { x: 0, y: 0 }, ecran));
const ch = chemin(n, true);
check("5.4 chemin du moteur : sous-tracé fermé, sommets {anchor, in, out, smooth}", ch.subpaths[0].closed && ch.subpaths[0].knots.length === 2 && eq(ch.subpaths[0].knots[1].in, [6, -4]));
check("5.5 fin : mode Tracé -> path.set work ; mode Forme -> shape.create path (fermé : rempli, ouvert : contour)",
  commandePlume("trace", n, false).command === "path.set" && commandePlume("trace", n, false).params.name === "work"
  && commandePlume("forme", n, true, "#f00").params.fill === "#f00" && commandePlume("forme", n, false, "#f00").params.stroke.width === 1 && commandePlume("forme", n, false).params.fill === null
  && commandePlume("trace", [n[0]], false) === null);
const d = dChemin({ subpaths: [{ closed: true, knots: [[0, 0], [10, 0], { anchor: [10, 10], in: [12, 8], out: [8, 12] }] }] }, (x, y) => ({ x, y }));
check("5.6 d SVG : M puis courbes de Bézier, fermé par Z", d.startsWith("M0 0 C0 0 10 0 10 0 C10 0 12 8 10 10") && d.endsWith("Z"), d);
const dep = deplacerChemin({ subpaths: [{ knots: [[0, 0], { anchor: [5, 5], in: [4, 4], out: [6, 6] }] }] }, 10, 20);
check("5.7 déplacer un chemin : ancres et poignées", eq(dep.subpaths[0].knots[0], [10, 20]) && eq(dep.subpaths[0].knots[1].in, [14, 24]));
check("5.8 bornes (ancres et poignées)", eq(bornes({ subpaths: [{ knots: [[0, 5], { anchor: [10, 10], in: [12, 1], out: [8, 20] }] }] }), [0, 1, 12, 20]) && bornes({}) === null);
const liste = { paths: [{ name: "Tracé 1" }], workPath: { knots: 3 }, layerPath: { name: "Heart Shape Path", layer: 9 } };
check("5.9 lignes du panneau : enregistrés, de travail, du calque", eq(lignesTraces(liste).map((l) => l.type + ":" + l.cle), ["enregistre:Tracé 1", "travail:work", "calque:layer"]));
check("5.10 Sélection de tracé : la forme active, sinon le tracé de travail", eq(cibleSelection({ activeLayer: 9, layers: [{ id: 9, kind: "Shape" }] }, liste), { type: "forme", calque: 9 })
  && eq(cibleSelection({ activeLayer: 2, layers: [{ id: 2, kind: "Pixel" }] }, liste), { type: "travail" }) && cibleSelection({ activeLayer: 2, layers: [] }, { paths: [] }) === null);
check("5.11 déplacement : shape.edit move ; tracé de travail : path.set déplacé ; moins de 0,5 px : rien",
  eq(commandeDeplacement({ type: "forme", calque: 9 }, 20, 30), { command: "shape.edit", params: { layer: 9, move: [20, 30] } })
  && commandeDeplacement({ type: "travail" }, 5, 0, { subpaths: [{ knots: [[0, 0]] }] }).params.path.subpaths[0].knots[0][0] === 5
  && commandeDeplacement({ type: "forme", calque: 9 }, 0.2, 0.1) === null);
check("5.12 nom libre", nomLibre(liste, "Tracé") === "Tracé 2" && nomLibre({ paths: [] }, "Tracé") === "Tracé 1");

// 6. Rechercher
const arbre = [{ nom: "Layer", nom_affiche: "Calque", entrees: [{ type: "commande", id: "layer.duplicate", libelle: "Dupliquer le calque…", etat: "actif" },
  { type: "commande", id: "layer.x", libelle: "Bientôt", etat: "bientot" }, { type: "sous-menu", nom_affiche: "Nouveau", entrees: [{ type: "commande", id: "layer.new.layer", libelle: "Calque…", etat: "actif" }] },
  { type: "commande", id: "edit.search", libelle: "Rechercher…", etat: "actif" }] }];
const ec = entreesCherchables(arbre);
check("6.1 entrées actives seulement, avec leur chemin ; Rechercher exclu ; « … » retiré", eq(ec.map((e) => e.libelle + "|" + e.chemin), ["Dupliquer le calque|Calque", "Calque|Calque › Nouveau"]));
check("6.2 score : début > mot > contenu > sous-suite > rien", score("dup", "Dupliquer") > score("calq", "Dupliquer le calque") && score("calq", "Dupliquer le calque") > score("liq", "Dupliquer")
  && score("dpq", "Dupliquer") === 10 && score("zz", "Dupliquer") === 0 && score("éc", "Ecran") > 0);
const els = [...ec, { sorte: "outil", libelle: "Calque magique", chemin: "Outils" }];
check("6.3 chercher : libellé exact d'abord, puis l'outil (+2) avant « Dupliquer le calque » ; chemin seulement s'il contient la recherche", eq(chercher("calque", els).map((e) => e.libelle), ["Calque", "Calque magique", "Dupliquer le calque"]) && chercher("nouveau", els).length === 1
  && chercher("xyz", els).length === 0);

// 7. préréglages Formes et Styles
const gf = groupesDe("formes", { groups: [{ name: "Symbols", shapes: [{ name: "Heart", subpaths: 1 }] }] });
const gs = groupesDe("styles", { groups: [{ name: "Basics", presets: [{ name: "Drop Shadow" }] }] });
check("7.1 groupes : formes (shapes) et styles (presets), clé = nom, groupe gardé", eq(gf, [{ nom: "Symbols", items: [{ cle: "Heart", nom: "Heart", groupe: "Symbols" }] }]) && gs[0].items[0].cle === "Drop Shadow");
check("7.2 commandes : place / apply / new / edit", COMMANDES.formes.appliquer === "shape.presets.place" && COMMANDES.styles.appliquer === "style.presets.apply" && COMMANDES.formes.choisir === null
  && ECRANS.formes.corps === "#corpsFormes" && ECRANS.styles.doc === true);
check("7.3 vignettes : motif par id, forme et style par nom et groupe (encodés)", urlVignette("motifs", { cle: "abc" }) === "/api/photolab/motifs/abc.png"
  && urlVignette("formes", { cle: "Arrow Right", groupe: "Arrows" }) === "/api/photolab/presets/forme/vignette.png?cle=Arrow%20Right&groupe=Arrows" && urlVignette("degrades", { cle: "x" }) === null);
check("7.4 noms intégrés des formes et styles traduits", nomAffiche("Heart", t).brut === false && nomAffiche("Drop Shadow", t).texte === t(NOMS_INTEGRES["Drop Shadow"]) && Object.keys(NOMS_INTEGRES).length >= 80);

// 8. branchement
const neuf = ["pen", "type", "pathSelection", ...OUTILS_FORME];
check("8.1 les 9 outils sont actifs (p2)", neuf.every((id) => EMPLACEMENTS.flat().find((o) => o.id === id).p2 === true));
const ids = ["window.panel.character", "window.panel.paragraph", "window.panel.glyphs", "window.panel.characterStyles", "window.panel.paragraphStyles", "window.panel.paths",
  "window.panel.shapes", "window.panel.styles", ...Object.keys(PANNEAUX_TEXTE), ...Object.keys(APERCUS), ...LANGUES, COMPOSEUR, "edit.search"];
check("8.2 les 23 entrées de menu servies par l'écran", ids.length === 23 && ids.every((id) => TRAITES_PAR_ECRAN.has(id)), ids.filter((id) => !TRAITES_PAR_ECRAN.has(id)));
check("8.3 Fenêtre : les 8 panneaux rattachés à leur onglet", ids.slice(0, 8).every((id) => PANNEAUX[id] && GROUPES[PANNEAUX[id].groupe].includes(PANNEAUX[id].onglet)));
const html = readFileSync(join(racine, "index.html"), "utf8"), core = readFileSync(join(racine, "js", "core.js"), "utf8");
check("8.4 index.html : groupe Texte (5 onglets, replié), Formes, Styles, Tracés, bouton de rail", /<section id="grpTexte" class="groupe" hidden>/.test(html)
  && GROUPES.texte.every((o) => html.includes(`data-onglet-tx="${o}"`) && html.includes(`data-vue-tx="${o}"`)) && html.includes('data-onglet-co="formes"')
  && html.includes('data-onglet-pr="styles"') && html.includes('data-onglet="traces"') && html.includes('data-panneau="texte"'));
check("8.5 core.js : modules initialisés après les gestes et les outils", ["initFormes(PL)", "initTrace(PL)", "initTexte(PL)", "initRecherche(PL)", 'initPresets(PL, "formes")', 'initPresets(PL, "styles")']
  .every((x) => core.indexOf(x) > core.indexOf("initGestes(PL)") && core.indexOf(x) > core.indexOf("initOutils(PL)")));
const outils = readFileSync(join(racine, "js", "mod-outils.js"), "utf8"), gestes = readFileSync(join(racine, "js", "mod-gestes.js"), "utf8"), menusSrc = readFileSync(join(racine, "js", "mod-menus.js"), "utf8");
check("8.6 barres d'outils déclarées (PL.barresOutils), dessins (PL.dessinsSup), décorateurs de menu", /PL\.barresOutils && PL\.barresOutils\[PL\.etat\.outil\]/.test(outils)
  && /for \(const f of PL\.dessinsSup\) f\(svg, el, ecran\)/.test(gestes) && /for \(const f of PL\.decorateursMenus\) menus = f\(menus\)/.test(menusSrc));

console.log(`texte : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
