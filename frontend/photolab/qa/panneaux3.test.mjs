// qa/panneaux3.test.mjs — t153 (parité L3) : Nuancier, Dégradés, Motifs, Histogramme, Infos, Couches, Compositions —
// fonctions PURES des modules, branchement des onglets (index.html, core.js), espaces et menus.
import { etatDefaut, DEFAUT_GROUPES, NOMS_GROUPES, nomGroupe, ajouterRecente, ajouterNuance, nouveauGroupe, renommerGroupe,
  supprimer, filtrer, cibleClic, MAX_RECENTES } from "../js/mod-nuancier.js";
import { nomAffiche, groupesDe, courantDe, filtrerGroupes, opaciteA, cssDegrade, COMMANDES, paramsEdition, NOMS_INTEGRES } from "../js/mod-presets.js";
import { statistiques, lecturePixel, pixelSous, tailleSelection, CANAUX } from "../js/mod-infos.js";
import { lignesCouches, operationClic, modeVue, composerVue, ligneDuRaccourci, NOMS_COULEURS } from "../js/mod-couches.js";
import { lignesCompositions, cible, paramsNouvelle, OPTIONS } from "../js/mod-compositions.js";
import { nomValide } from "../js/mod-nommer.js";
import { GROUPES, PANNEAUX } from "../js/mod-espaces.js";
import { TRAITES_PAR_ECRAN } from "../js/mod-menus.js";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const t = (cle) => "«" + cle + "»";
const ici = dirname(fileURLToPath(import.meta.url));
const racine = join(ici, "..");

// 1. Nuancier
const e0 = etatDefaut();
check("1.1 défaut : 4 groupes fournis, 40 nuances (amont), aucune récente", e0.groupes.length === 4
  && e0.groupes.reduce((n, g) => n + g.couleurs.length, 0) === 40 && e0.recentes.length === 0 && DEFAUT_GROUPES[0][1][0] === "#000000");
check("1.2 nom d'un groupe fourni traduit, d'un groupe créé tel quel", nomGroupe(e0.groupes[2], t) === t(NOMS_GROUPES.vives)
  && nomGroupe({ id: "g-1", nom: "Marque" }, t) === "Marque");
let e = ajouterRecente(e0, "#ff0000");
e = ajouterRecente(e, "#00ff00");
e = ajouterRecente(e, "#ff0000");
check("1.3 récentes : la dernière en tête, sans doublon", eq(e.recentes, ["#ff0000", "#00ff00"]) && e0.recentes.length === 0);
let plein = e0;
for (let i = 0; i < 20; i++) plein = ajouterRecente(plein, "#0000" + String(i).padStart(2, "0"));
check("1.4 récentes : 12 au plus", plein.recentes.length === MAX_RECENTES && plein.recentes[0] === "#000019");
const n = nouveauGroupe(e0, "  Ma marque ");
check("1.5 nouveau groupe : id g-1, nom propre, vide", n.id === "g-1" && n.etat.groupes[4].nom === "Ma marque" && n.etat.groupes[4].couleurs.length === 0);
check("1.6 nouveau groupe sans nom ou sur deux lignes : refusé", nouveauGroupe(e0, "  ").erreur && nouveauGroupe(e0, "a\nb").erreur);
const n2 = nouveauGroupe(n.etat, "Autre");
check("1.7 deuxième groupe : id suivant", n2.id === "g-2");
const a = ajouterNuance(n.etat, "g-1", "#123456", "Nuit");
check("1.8 nouvelle nuance dans le groupe visé, original intact", eq(a.groupes[4].couleurs, [{ hex: "#123456", nom: "Nuit" }]) && n.etat.groupes[4].couleurs.length === 0);
check("1.9 groupe inconnu -> le premier", ajouterNuance(e0, "zorg", "#abcdef").groupes[0].couleurs.length === 11);
check("1.10 sans aucun groupe : un groupe est créé", ajouterNuance({ ...e0, groupes: [] }, null, "#abcdef").groupes.length === 1);
check("1.11 renommer un groupe ; nom vide refusé", renommerGroupe(e0, "gris", "Neutres").groupes[0].nom === "Neutres" && renommerGroupe(e0, "gris", " ") === e0);
check("1.12 supprimer une nuance par index", supprimer(e0, { groupe: "gris", index: 0 }).groupes[0].couleurs[0].hex === "#1a1a1a");
check("1.13 supprimer un groupe entier", supprimer(e0, { groupe: "pastels" }).groupes.map((g) => g.id).join() === "gris,vives,foncees");
check("1.14 supprimer sans sélection : inchangé", supprimer(e0, null) === e0);
const f = filtrer(a, "nuit");
check("1.15 recherche par nom : un seul groupe, index d'origine gardé", f.length === 1 && f[0].id === "g-1" && f[0].couleurs[0].i === 0);
check("1.16 recherche par code : #e62828 trouvé dans « vives »", filtrer(e0, "e62828").map((g) => g.id).join() === "vives");
check("1.17 recherche vide : tout, avec index", filtrer(e0, "").length === 4 && filtrer(e0, "")[1].couleurs[3].i === 3);
check("1.18 clic = premier plan, Alt+clic = arrière-plan", cibleClic({}) === "foreground" && cibleClic({ altKey: true }) === "background");
check("1.19 nomValide", nomValide("  a  ") === "a" && nomValide("") === null && nomValide("x".repeat(65)) === null);

// 2. Dégradés et Motifs
const listeG = { current: { name: "Blue 01" }, groups: [{ name: "Basics", presets: [{ name: "Foreground to Background", stops: [[0, "foreground"], [1, "background"]], transparency: [] }] },
  { name: "Blues", presets: [{ name: "Blue 01", stops: [[0, "#0b3d91"], [1, "#4fa3e0"]], transparency: [] }] }] };
const gG = groupesDe("degrades", listeG);
check("2.1 dégradés : groupes et clé = nom", gG.length === 2 && gG[1].items[0].cle === "Blue 01" && courantDe("degrades", listeG) === "Blue 01");
const listeM = { current: null, groups: [{ name: "Geometric", patterns: [{ id: "059289fb-e0b5-6144-cf07-4e299f48629e", name: "Checkerboard", width: 16, height: 16 }] }] };
const gM = groupesDe("motifs", listeM);
check("2.2 motifs : clé = id, dimensions", gM[0].items[0].cle === "059289fb-e0b5-6144-cf07-4e299f48629e" && gM[0].items[0].largeur === 16 && courantDe("motifs", listeM) === null);
check("2.3 noms intégrés traduits, nom de l'utilisateur brut", eq(nomAffiche("Basics", t), { texte: t("photolab.presets.basiques"), brut: false })
  && nomAffiche("Blue 03", t).texte === t("photolab.presets.bleu") + " 03" && eq(nomAffiche("Ma rampe", t), { texte: "Ma rampe", brut: true }));
check("2.4 recherche sur le nom traduit et le nom moteur", filtrerGroupes(gG, "blue", t).length === 1 && filtrerGroupes(gG, "presets.bleu", t).length === 1 && filtrerGroupes(gG, "zzz", t).length === 0);
check("2.5 opacité interpolée ; aucun arrêt = opaque", opaciteA([], 0.5) === 1 && opaciteA([[0, 100], [1, 0]], 0.25) === 0.75 && opaciteA([[0.2, 50]], 0) === 0.5);
const css = cssDegrade([[0, "foreground"], [1, "background"]], [], "#ff0000", "#0000ff");
check("2.6 CSS : premier et arrière-plan résolus", css === "linear-gradient(90deg, rgba(255, 0, 0, 1) 0%, rgba(0, 0, 255, 1) 100%)", css);
check("2.7 CSS : transparence et couleur [r,g,b] 0..1", cssDegrade([[0, [1, 1, 1]], [1, "#000000"]], [[0, 100], [1, 0]]).includes("rgba(255, 255, 255, 1) 0%")
  && cssDegrade([[0, "#000000"], [1, "#000000"]], [[0, 100], [1, 0]]).includes("rgba(0, 0, 0, 0) 100%"));
check("2.8 un seul arrêt : bande unie (deux fois l'arrêt)", (cssDegrade([[0.5, "#112233"]]).match(/rgba/g) || []).length === 2);
check("2.9 commandes du moteur par genre", COMMANDES.degrades.choisir === "gradient.presets.select" && COMMANDES.motifs.appliquer === "pattern.presets.apply"
  && COMMANDES.motifs.champ === "pattern" && COMMANDES.degrades.champ === "preset");
check("2.10 paramètres d'édition", eq(paramsEdition("renommer", { nom: "Dots" }, "Geometric", "Points"), { action: "rename", preset: "Dots", group: "Geometric", name: "Points" })
  && eq(paramsEdition("supprimerGroupe", null, "Blues"), { action: "deleteGroup", group: "Blues" }) && eq(paramsEdition("nouveauGroupe", null, null, "G"), { action: "newGroup", name: "G" })
  && paramsEdition("zorg") === null);

// 3. Histogramme et Infos
const bins = new Array(256).fill(0); bins[0] = 1; bins[255] = 1;
const st = statistiques(bins);
check("3.1 statistiques : moyenne 127,5, écart type 127,5, médiane 0 (premier rang atteignant la moitié)", st.moyenne === 127.5 && st.ecartType === 127.5 && st.mediane === 0 && st.compte === 2, st);
const b2 = new Array(256).fill(0); b2[10] = 3; b2[20] = 1;
check("3.2 médiane et moyenne pondérées", statistiques(b2).mediane === 10 && statistiques(b2).moyenne === 12.5);
check("3.3 aucun pixel : null", statistiques(new Array(256).fill(0)) === null && statistiques(null) === null);
check("3.4 quatre canaux (luminosité, rouge, vert, bleu)", eq(CANAUX.map((c) => c.id), ["l", "r", "g", "b"]));
const lu = lecturePixel([0.2, 0.4, 0.6, 1]);
check("3.5 pixel du moteur -> R/V/B 0..255", lu.r === 51 && lu.v === 102 && lu.b === 153 && lu.a === 255, lu);
check("3.6 C/M/J/N naïfs de l'amont", lu.n === 40 && lu.c === 67 && lu.m === 33 && lu.j === 0, lu);
check("3.7 noir : N 100 %, encres 0 (pas de division par zéro)", eq((({ c, m, j, n }) => [c, m, j, n])(lecturePixel([0, 0, 0, 1])), [0, 0, 0, 100]));
check("3.8 pixel illisible : null", lecturePixel(null) === null && lecturePixel([1]) === null);
const d = { width: 100, height: 50 };
check("3.9 pixel sous le pointeur : arrondi bas, hors document null", eq(pixelSous({ x: 3.9, y: 49.99 }, d), { x: 3, y: 49 }) && pixelSous({ x: 100, y: 0 }, d) === null
  && pixelSous({ x: -0.1, y: 0 }, d) === null);
check("3.10 taille de la sélection [x,y,w,h] ; sans sélection null", eq(tailleSelection({ hasSelection: true, selectionBounds: [1, 2, 30, 40] }), { l: 30, h: 40 })
  && tailleSelection({ hasSelection: false, selectionBounds: [0, 0, 1, 1] }) === null);

// 4. Couches
const ch = { alpha: [{ color: [1, 0, 0], index: 0, indicates: "maskedAreas", name: "Alpha 1", opacity: 0.5, spot: null, visible: false }],
  colors: [{ name: "Red", visible: true }, { name: "Green", visible: true }, { name: "Blue", visible: true }],
  composite: "RGB", compositeVisible: true, target: { kind: "composite" } };
const L = lignesCouches(ch);
check("4.1 lignes : composite, trois couleurs, l'alpha", eq(L.map((l) => l.type + ":" + l.ref), ["composite:composite", "couleur:red", "couleur:green", "couleur:blue", "alpha:0"]));
check("4.2 raccourcis Ctrl+2 (composite) … Ctrl+6 (première alpha)", eq(L.map((l) => l.raccourci), ["Ctrl+2", "Ctrl+3", "Ctrl+4", "Ctrl+5", "Ctrl+6"]));
check("4.3 cible : composite", L[0].cible && !L[1].cible);
const L2 = lignesCouches({ ...ch, target: { kind: "alpha", index: 0 } });
check("4.4 cible : l'alpha", L2[4].cible && !L2[0].cible);
check("4.5 document en niveaux de gris : pas de composite, Ctrl+3 = la couche", eq(lignesCouches({ colors: [{ name: "Gray", visible: true }], alpha: [], target: { kind: "color", index: 0 } }).map((l) => l.raccourci), ["Ctrl+3"]));
check("4.6 Ctrl+clic : nouvelle, Maj ajouter, Alt soustraire, Maj+Alt intersection", operationClic({}) === "new" && operationClic({ shiftKey: true }) === "add"
  && operationClic({ altKey: true }) === "subtract" && operationClic({ shiftKey: true, altKey: true }) === "intersect");
check("4.7 vue : composite tel quel quand tout est visible et aucune alpha", modeVue(ch) === null);
check("4.8 vue : rouge seul", eq(modeVue({ ...ch, colors: ch.colors.map((c, i) => ({ ...c, visible: i === 0 })) }), { couleurs: [true, false, false], alphas: [] }));
check("4.9 vue : alpha visible", eq(modeVue({ ...ch, alpha: [{ ...ch.alpha[0], visible: true }] }), { couleurs: [true, true, true], alphas: [0] }));
const src = new Uint8ClampedArray([51, 102, 153, 255, 10, 20, 30, 128]);
check("4.10 composer : rouge seul -> gris du rouge (alpha gardé)", eq([...composerVue(src, { couleurs: [true, false, false], alphas: [] })], [51, 51, 51, 255, 10, 10, 10, 128]));
check("4.11 composer : rouge + vert -> bleu à zéro", eq([...composerVue(src, { couleurs: [true, true, false], alphas: [] })], [51, 102, 0, 255, 10, 20, 0, 128]));
check("4.12 composer : alpha seule -> son gris", eq([...composerVue(src, { couleurs: [false, false, false], alphas: [0] }, { 0: new Uint8Array([255, 0]) }, [{ index: 0, couleur: [1, 0, 0], opacite: 0.5 }])],
  [255, 255, 255, 255, 0, 0, 0, 128]));
const rec = composerVue(src, { couleurs: [true, true, true], alphas: [0] }, { 0: new Uint8Array([255, 0]) }, [{ index: 0, couleur: [1, 0, 0], opacite: 0.5 }]);
check("4.13 composer : recouvrement rouge à 50 % là où l'alpha masque (noir), rien là où elle sélectionne (blanc) ; 132,5 -> 132 (Uint8ClampedArray arrondit au pair)",
  eq([...rec.slice(0, 4)], [51, 102, 153, 255]) && rec[4] === 132 && rec[5] === 10 && rec[6] === 15, [...rec]);
check("4.14 Ctrl+n -> ligne", ligneDuRaccourci(L, 4).ref === "green" && ligneDuRaccourci(L, 9) === null);
check("4.15 noms des couches du moteur traduits", NOMS_COULEURS.Red && NOMS_COULEURS.RGB && NOMS_COULEURS.Blue);

// 5. Compositions
const r = { comps: [{ id: 1, name: "A", comment: "c", visibility: true, position: false, appearance: true, missingLayers: 0, layers: 3 },
  { id: 2, name: "B", comment: "", visibility: true, position: true, appearance: true, missingLayers: 2, layers: 3 }], lastApplied: 2, hasLastDocumentState: true };
const v = lignesCompositions(r);
check("5.1 lignes : appliquée, manquants, options", v.lignes[1].appliquee && !v.lignes[0].appliquee && v.lignes[1].manquants === 2 && v.lignes[0].position === false && v.lignes[0].commentaire === "c");
check("5.2 Dernier état : non coché, actif quand une composition est appliquée", !v.dernierEtat.coche && v.dernierEtat.actif);
const v0 = lignesCompositions({ comps: [], lastApplied: null, hasLastDocumentState: false });
check("5.3 sans composition appliquée : Dernier état coché, inactif", v0.dernierEtat.coche && !v0.dernierEtat.actif && v0.lignes.length === 0);
check("5.3b une composition appliquée sans état retenu : Dernier état ni coché ni actif (moteur : hasLastDocumentState faux)",
  (({ coche, actif }) => !coche && !actif)(lignesCompositions({ comps: r.comps, lastApplied: 2, hasLastDocumentState: false }).dernierEtat));
check("5.4 cible : la sélection, sinon la dernière appliquée", cible(1, r) === 1 && cible(null, r) === 2 && cible(9, r) === 2 && cible(null, { comps: [] }) === null);
check("5.5 nouvelle : nom et commentaire facultatifs, options en booléens", eq(paramsNouvelle({ nom: "  X ", visibility: true, position: false, appearance: 1, commentaire: "" }),
  { visibility: true, position: false, appearance: true, name: "X" }) && !("name" in paramsNouvelle({ nom: "" })));
check("5.6 trois options (visibilité, position, apparence)", eq(OPTIONS.map((o) => o.cle), ["visibility", "position", "appearance"]));

// 6. Branchement : page, onglets, espaces, menus, icônes
const html = readFileSync(join(racine, "index.html"), "utf8");
const core = readFileSync(join(racine, "js", "core.js"), "utf8");
check("6.1 groupe Couleur : Couleur | Nuancier | Dégradés | Motifs, quatre corps", ["couleur", "nuancier", "degrades", "motifs"].every((o) => html.includes(`data-onglet-co="${o}"`) && html.includes(`data-vue-co="${o}"`)));
check("6.2 Compositions dans Propriétés, Couches dans Calques", html.includes('data-onglet-pr="compositions"') && html.includes('id="corpsCompositions" data-vue-pr="compositions" hidden')
  && html.includes('data-onglet="couches"') && html.includes('id="corpsCouches" data-vue="couches" hidden'));
check("6.3 groupe Infos : Histogramme | Infos, replié, bouton de rail", html.includes('<section id="grpInfos" class="groupe" hidden>') && html.includes('data-onglet-in="histogramme"')
  && html.includes('data-onglet-in="infos"') && html.includes('data-panneau="infos"'));
check("6.4 onglets du HTML = GROUPES des espaces", Object.entries(GROUPES).every(([g, os]) => os.every((o) => new RegExp(`data-(onglet|onglet-pr|onglet-pi|onglet-co|onglet-in|onglet-tx)="${o}"`).test(html))));
const sept = ["window.panel.swatches", "window.panel.gradients", "window.panel.patterns", "window.panel.layerComps", "window.panel.channels", "window.panel.histogram", "window.panel.info"];
check("6.5 Fenêtre : les 7 panneaux servis par l'écran et rattachés à leur onglet", sept.every((id) => TRAITES_PAR_ECRAN.has(id) && PANNEAUX[id] && GROUPES[PANNEAUX[id].groupe].includes(PANNEAUX[id].onglet)));
check("6.6 core.js : les cinq modules initialisés après la Couleur et le cycle", ["initNuancier(PL)", 'initPresets(PL, "degrades")', 'initPresets(PL, "motifs")', "initInfos(PL)", "initCouches(PL)", "initCompositions(PL)"]
  .every((x) => core.indexOf(x) > core.indexOf("initCouleur(PL)") && core.indexOf(x) > core.indexOf("initCycle(PL)")));
check("6.7 un onglet montré relit sa liste (Dégradés, Motifs, Histogramme, Compositions)", /nom === "degrades"[^\n]*relire/.test(core) && /nom === "motifs"[^\n]*relire/.test(core)
  && /nom === "histogramme"[^\n]*relire/.test(core) && /nom === "compositions"[^\n]*relire/.test(core));
const vue = readFileSync(join(racine, "js", "mod-vue.js"), "utf8");
check("6.8 la vue dessine l'image filtrée par les couches", /const image = vue\.filtre \? vue\.filtre\(vue\.rendu\.image\) : vue\.rendu\.image;/.test(vue) && /ctx\.drawImage\(image, x, y, W, H\)/.test(vue));
const icones = ["info", "chevrons-left", "chevrons-right", "rotate-cw", "sparkles", "circle-dashed", "square-dashed", "folder-plus", "plus", "trash-2", "eye", "eye-off", "move", "file-plus"];
check("6.9 icônes des nouveaux panneaux présentes (Lucide)", icones.every((i) => existsSync(join(racine, "icones", i + ".svg"))), icones.filter((i) => !existsSync(join(racine, "icones", i + ".svg"))));
check("6.10 noms intégrés du moteur : tous ont une clé photolab.presets.*", Object.values(NOMS_INTEGRES).every((k) => k.startsWith("photolab.presets.")));

const gestes = readFileSync(join(racine, "js", "mod-gestes.js"), "utf8");
check("6.11 aperçu de sélection et cadre de recadrage normalisés (vue en miroir : jamais de largeur négative)",
  /rectVersEcran\(PL\.vue\.v, a\.x, a\.y, a\.width, a\.height\)/.test(gestes) && /rectVersEcran\(PL\.vue\.v, c\.x, c\.y, c\.width, c\.height\)/.test(gestes)
  && !/width: Math\.round\(p1\.x - p0\.x\)/.test(gestes) && !/width: p1\.x - p0\.x/.test(gestes));

console.log(`panneaux3 : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
