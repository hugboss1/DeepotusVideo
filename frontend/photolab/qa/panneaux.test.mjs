// qa/panneaux.test.mjs — panneaux (C2) : Calques, Propriétés, Couleur, Historique, Navigateur — fonctions PURES.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { aplatirCalques, actionSelection, pourcent, depuisPourcent, MODES_FUSION, MODE_TRANSFERT, idFusion, positionDepot,
  VERROUS, basculerVerrou, estFond, trouverCalque, cibleDepot } from "../js/mod-calques.js";
import { proprietesDe } from "../js/mod-proprietes.js";
import { versHex, hexValide } from "../js/mod-couleur.js";
import { etatsHistorique, annulationsPour, tableEtats, traduireEtat, tranches, ETATS_MOTEUR } from "../js/mod-historique.js";
import { cadreNavigateur, rectVue, centrerVue } from "../js/mod-navigateur.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const dico = JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8"));
const json = (x) => JSON.stringify(x);
const proche = (a, b, e = 1e-9) => Math.abs(a - b) <= e;

// Arbre au format doc.inspect (relevé sur le vrai moteur le 08/10) : haut -> bas, groupes avec children.
const arbre = [
  { id: 4, name: "G", kind: "Group", expanded: true, visible: true, children: [
    { id: 3, name: "Rouge", kind: "Pixel", visible: true },
    { id: 5, name: "Sous", kind: "Group", expanded: true, children: [{ id: 6, name: "Fond du sous-groupe", kind: "Pixel" }] },
  ] },
  { id: 2, name: "Background", kind: "Pixel", visible: true },
];

// 1. aplatir
const plat = aplatirCalques(arbre);
check("1.1 ordre haut -> bas, enfants sous le groupe", plat.map((c) => c.id).join() === "4,3,5,6,2", plat.map((c) => c.id).join());
check("1.2 profondeurs", plat.map((c) => c.profondeur).join() === "0,1,1,2,0", plat.map((c) => c.profondeur).join());
check("1.3 groupes repérés", plat.filter((c) => c.groupe).map((c) => c.id).join() === "4,5");
const replie = aplatirCalques(arbre, new Set([4]));
check("1.4 groupe replié par l'écran : enfants masqués", replie.map((c) => c.id).join() === "4,2", replie.map((c) => c.id).join());
check("1.5 groupe fermé dans le moteur (expanded false) : enfants masqués",
  aplatirCalques([{ id: 1, kind: "Group", expanded: false, children: [{ id: 2 }] }]).length === 1);
check("1.8 filtre : tout déplié, même un groupe fermé dans le moteur ou replié par l'écran",
  aplatirCalques([{ id: 1, kind: "Group", expanded: false, children: [{ id: 2 }] }], new Set([1]), true).map((c) => c.id).join() === "1,2");
check("1.6 arbre vide", aplatirCalques(null).length === 0);
check("1.7 trouverCalque profond", (trouverCalque(arbre, 6) || {}).name === "Fond du sous-groupe" && trouverCalque(arbre, 99) === null);

// 2. clic sur une ligne
check("2.1 clic", JSON.stringify(actionSelection(3, false, false)) === JSON.stringify({ layer: 3, mode: "replace" }));
check("2.2 Ctrl+clic", actionSelection(3, true, false).mode === "toggle");
check("2.3 Maj+clic", actionSelection(3, false, true).mode === "range");
check("2.4 Maj l'emporte (plage)", actionSelection(3, true, true).mode === "range");

// 3. pourcentages
check("3.1 0.5 -> « 50 % » (fr)", pourcent(0.5) === "50 %");
check("3.2 anglais sans espace", pourcent(0.5, "en") === "50%");
check("3.3 arrondi", pourcent(0.333) === "33 %" && pourcent(1) === "100 %");
check("3.4 depuisPourcent", depuisPourcent("50") === 0.5 && depuisPourcent("50 %") === 0.5 && depuisPourcent("12,5") === 0.125);
check("3.5 borné 0..1", depuisPourcent("150") === 1 && depuisPourcent("-3") === 0);
check("3.6 illisible -> null", depuisPourcent("abc") === null && depuisPourcent("") === null);

// 4. modes de fusion : les 27 de photocraft dans l'ordre (inventaire B §4.3), + Transfert pour les groupes
check("4.1 27 modes", MODES_FUSION.length === 27, MODES_FUSION.length);
check("4.2 ordre de photocraft", MODES_FUSION.map((m) => m.id).join() === ["normal", "dissolve", "darken", "multiply", "colorBurn",
  "linearBurn", "darkerColor", "lighten", "screen", "colorDodge", "linearDodge", "lighterColor", "overlay", "softLight", "hardLight",
  "vividLight", "linearLight", "pinLight", "hardMix", "difference", "exclusion", "subtract", "divide", "hue", "saturation", "color",
  "luminosity"].join(), MODES_FUSION.map((m) => m.id).join());
check("4.3 Transfert à part", MODE_TRANSFERT.id === "passThrough" && !MODES_FUSION.includes(MODE_TRANSFERT));
check("4.4 libellés au dictionnaire", [...MODES_FUSION, MODE_TRANSFERT].every((m) => dico[m.cle] && dico[m.cle].fr && dico[m.cle].en),
  [...MODES_FUSION, MODE_TRANSFERT].filter((m) => !dico[m.cle]).map((m) => m.cle));
check("4.5 libellés fr de photocraft", dico["photolab.fusion.multiply"].fr === "Produit" && dico["photolab.fusion.color_burn"].fr === "Densité couleur +"
  && dico["photolab.fusion.linear_dodge"].fr === "Densité linéaire − (Addition)");
check("4.6 nom rendu par le moteur -> id envoyé", idFusion("Linear Dodge (Add)") === "linearDodge" && idFusion("Color Burn") === "colorBurn"
  && idFusion("Pass Through") === "passThrough" && idFusion("Normal") === "normal" && idFusion("??") === null);

// 5. glisser-déposer dans la liste
check("5.1 moitié haute -> au-dessus", positionDepot(4, 28, false) === "above");
check("5.2 moitié basse -> en dessous", positionDepot(20, 28, false) === "below");
check("5.3 groupe, 30-70 % -> dedans", positionDepot(14, 28, true) === "into" && positionDepot(5, 28, true) === "above" && positionDepot(25, 28, true) === "below");

// 5b. « en dessous » d'un groupe DÉPLIÉ : l'indicateur est sous la ligne du groupe, donc au-dessus de sa première ligne
//     visible (moveTo below du groupe le mettrait sous TOUT le groupe, loin de l'indicateur)
check("5.4 sous un groupe déplié -> au-dessus de la ligne suivante", json(cibleDepot(plat, 0, "below")) === json({ target: 3, position: "above" }));
check("5.5 sous un groupe replié -> sous le groupe", json(cibleDepot(replie, 0, "below")) === json({ target: 4, position: "below" }));
check("5.6 ailleurs inchangé", json(cibleDepot(plat, 1, "below")) === json({ target: 3, position: "below" }) && json(cibleDepot(plat, 0, "into")) === json({ target: 4, position: "into" }));

// 6. verrous (tenus par l'écran : le moteur ne les relit pas)
check("6.1 cinq verrous", VERROUS.map((v) => v.cle).join() === "transparency,pixels,position,artboard,all");
check("6.2 icônes présentes", VERROUS.every((v) => { try { readFileSync(join(racine, "icones", v.icone + ".svg")); return true; } catch (e) { return false; } }));
const v1 = basculerVerrou(undefined, "pixels");
check("6.3 objet complet de 5 booléens", Object.keys(v1).length === 5 && v1.pixels === true && v1.all === false);
check("6.4 bascule", basculerVerrou(v1, "pixels").pixels === false);
check("6.5 libellés au dictionnaire", VERROUS.every((v) => dico[v.cle_libelle]));
check("6.6 fond = dernier calque racine nommé Background", estFond(arbre[1], arbre) && !estFond(arbre[0], arbre));

// 7. propriétés
const doc = { width: 1920, height: 1080, resolution: 72, mode: "Rgb", depth: 8, activeLayer: 3, layers: arbre };
const t = (c, v) => c + (v ? JSON.stringify(v) : "");
const pd = proprietesDe({ ...doc, activeLayer: null }, t);
check("7.1 sans calque : le document", pd.titre === "photolab.proprietes.document" && pd.lignes.some((l) => l.valeur === "1920 × 1080 px"), pd);
const pc = proprietesDe({ ...doc, layers: [{ ...arbre[0], children: [{ ...arbre[0].children[0], bounds: [4, 0, 28, 16] }] }, arbre[1]] }, t);
check("7.2 avec calque : nom, type, bornes", pc.titre === "photolab.proprietes.calque" && pc.lignes.some((l) => l.valeur === "Rouge")
  && pc.lignes.some((l) => l.valeur === "4, 0 · 28 × 16 px"), pc);
check("7.4 le nom du calque est une donnée (brut : jamais traduit)", pc.lignes.find((l) => l.valeur === "Rouge").brut === true && pc.lignes.filter((l) => l.brut).length === 1);
check("7.3 aucun document", proprietesDe(null, t).lignes.length === 0);

// 8. couleur
check("8.1 versHex", versHex([1, 0, 0, 1]) === "#ff0000" && versHex([0.5, 0.5, 0.5]) === "#808080");
check("8.2 versHex borné / invalide", versHex([2, -1, 0]) === "#ff0000" && versHex(null) === "#000000");
check("8.3 hexValide", hexValide("#AABBCC") === "#aabbcc" && hexValide("aabbcc") === "#aabbcc" && hexValide("#abc") === "#aabbcc" && hexValide("#12") === null && hexValide("zz0000") === null);

// 9. historique (les états annulés disparaissent de doc.inspect.history)
const h = ["Open", "New Layer", "Fill", "Move"];
const e = etatsHistorique(h, false);
check("9.1 un état par nom, le dernier courant", e.length === 4 && e[3].courant && !e[2].courant && e[0].index === 0);
check("9.2 clic sur l'état k de n -> n-1-k annulations", annulationsPour(1, h) === 2 && annulationsPour(3, h) === 0 && annulationsPour(0, h) === 3);
check("9.3 index hors liste -> 0", annulationsPour(9, h) === 0 && annulationsPour(-1, h) === 0);
check("9.4 historique vide", etatsHistorique(null, false).length === 0);
const table = tableEtats(JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8")));
check("9.5 nom d'état traduit par le catalogue (sans « … »)", traduireEtat("Gaussian Blur", table) === "Flou gaussien", traduireEtat("Gaussian Blur", table));
check("9.7 au-delà de 100 (borne de /historique) : tranches de 100", JSON.stringify(tranches(237)) === "[100,100,37]" && JSON.stringify(tranches(100)) === "[100]" && tranches(0).length === 0);
const tDico = (lang) => (c) => (dico[c] ? dico[c][lang] : c);
check("9.8 carte choisie d'abord (fr)", traduireEtat("Rectangular Marquee", table, tDico("fr")) === "Sélection rectangulaire"
  && traduireEtat("Layer Via Copy", null, tDico("fr")) === "Calque par copie" && traduireEtat("Layer Visibility", null, tDico("fr")) === "Visibilité du calque");
check("9.9 carte choisie aussi en anglais", traduireEtat("Rename Layer", null, tDico("en")) === "Rename Layer");
check("9.10 puis le catalogue des menus", traduireEtat("Gaussian Blur", table, tDico("fr")) === "Flou gaussien");
check("9.11 puis le nom brut", traduireEtat("Zzz Inconnu", table, tDico("fr")) === "Zzz Inconnu");
const noms = ["Open", "New", "Rectangular Marquee", "Elliptical Marquee", "Lasso", "Polygonal Lasso", "Magic Wand", "Quick Selection",
  "Deselect", "Select All", "Inverse", "Reselect", "Layer Via Copy", "Layer Via Cut", "New Layer", "New Group", "Duplicate Layer",
  "Delete Layer", "Merge Down", "Group Layers", "Reorder Layers", "Layer Properties", "Layer Visibility", "Rename Layer", "Move",
  "Free Transform", "Crop", "Invert", "Fill", "Brush Tool"];
check("9.12 chaque état produit par les commandes P2 est dans la carte", noms.every((n) => ETATS_MOTEUR[n]), noms.filter((n) => !ETATS_MOTEUR[n]));
check("9.13 chaque clé de la carte existe (fr et en)", Object.values(ETATS_MOTEUR).every((k) => dico[k] && dico[k].fr && dico[k].en),
  Object.values(ETATS_MOTEUR).filter((k) => !dico[k]));
check("9.6 nom inconnu gardé tel quel", traduireEtat("Rectangular Marquee", new Map()) === "Rectangular Marquee");

// 10. navigateur
const cadre = cadreNavigateur({ w: 2000, h: 1000 }, { w: 260, h: 180 });
check("10.1 échelle qui tient dans la boîte", proche(cadre.echelle, 0.13) && proche(cadre.w, 260) && proche(cadre.h, 130) && proche(cadre.y, 25), cadre);
const v = { z: 0.5, ox: 100, oy: 50 };
const r = rectVue(v, { w: 800, h: 600 }, cadre);
// vue : document de (0-100)/0.5 = -200 à (800-100)/0.5 = 1400 en x ; (−50)/0.5 = −100 à 1100 en y
check("10.2 rectangle de la vue", proche(r.x, cadre.x - 200 * 0.13) && proche(r.w, 1600 * 0.13) && proche(r.y, cadre.y - 100 * 0.13) && proche(r.h, 1200 * 0.13), r);
const v2 = centrerVue(cadre.x + 1000 * 0.13, cadre.y + 500 * 0.13, cadre, v, { w: 800, h: 600 });
check("10.3 clic au centre du document : il passe au centre de la vue, zoom gardé",
  v2.z === 0.5 && proche(v2.ox + 1000 * 0.5, 400) && proche(v2.oy + 500 * 0.5, 300), v2);

// 11. t138 B5 : Propriétés | Ajustements dans #grpProprietes, calques de réglage dans le panneau Calques (lecture des
//     sources : ces branchements sont du DOM, les fonctions pures sont dans qa/reglages.test.mjs).
const html = readFileSync(join(racine, "index.html"), "utf8");
const css = readFileSync(join(racine, "photolab.css"), "utf8");
const src = (f) => readFileSync(join(racine, "js", f), "utf8");
const grp = (html.match(/<section id="grpProprietes"[\s\S]*?<\/section>/) || [""])[0];
check("11.1 deux onglets dans #grpProprietes : Propriétés puis Ajustements",
  /data-onglet-pr="proprietes"[^>]*>Propriétés</.test(grp) && /data-onglet-pr="ajustements"[^>]*>Ajustements</.test(grp)
  && grp.indexOf('data-onglet-pr="proprietes"') < grp.indexOf('data-onglet-pr="ajustements"'), grp);
check("11.2 deux corps : Propriétés visible, Ajustements caché", /id="corpsProprietes" data-vue-pr="proprietes">/.test(grp)
  && /id="corpsAjustements" data-vue-pr="ajustements" hidden>/.test(grp));
check("11.3 six sections (t155 : + #grpPinceaux ; t153 : + #grpInfos ; t156 : + #grpTexte, repliés) et huit boutons de rail (+ pinceaux, infos, texte)", (html.match(/<section\b/g) || []).length === 6
  && ((html.match(/id="rail"[\s\S]*?<\/nav>/) || [""])[0].match(/<button\b/g) || []).length === 8
  && /<section id="grpTexte" class="groupe" hidden>/.test(html) && /data-panneau="texte"/.test(html)
  && /<section id="grpPinceaux" class="groupe" hidden>/.test(html) && /data-panneau="pinceaux"/.test(html)
  && /<section id="grpInfos" class="groupe" hidden>/.test(html) && /data-panneau="infos"/.test(html));
const regle = (css.match(/#grpProprietes\s*\{[^}]*\}/) || [""])[0];
check("11.4 #grpProprietes : hauteur souple bornée (plus de 170 px fixes)", !/height\s*:\s*170px/.test(regle) && /max-height\s*:/.test(regle) && /flex\s*:\s*0 1 auto/.test(regle), regle);
check("11.5 son corps défile (overflow des .groupe-corps) et suit son contenu", /\.groupe-corps\s*\{[^}]*overflow\s*:\s*auto/.test(css) && /#grpProprietes \.groupe-corps\s*\{[^}]*flex\s*:\s*0 1 auto/.test(css));
check("11.6 bouton « nouveau calque de réglage » actif (menu des 16 kinds)", !/bientot\(bouton\("", "circle"/.test(src("mod-calques.js")) && /PL\.reglages\.menu\(bReglage\)/.test(src("mod-calques.js")));
check("11.7 ligne d'un calque de réglage : icône du kind, double-clic -> Propriétés", /PL\.reglages\.kindDe\(c\)/.test(src("mod-calques.js")) && /PL\.reglages\.montrer\("proprietes"\)/.test(src("mod-calques.js")));
check("11.8 Propriétés délègue l'éditeur au module des réglages", /PL\.reglages && PL\.reglages\.proprietes\(corps, doc\)/.test(src("mod-proprietes.js")));
check("11.9 core.js initialise les réglages après les Courbes", src("core.js").indexOf("initReglages(PL)") > src("core.js").indexOf("initCourbes(PL)") && src("core.js").includes("PL.majRail = majRail"));
const pc2 = proprietesDe({ ...doc, activeLayer: 7, layers: [{ id: 7, name: "Levels 1", kind: "Adjustment", adjustment: { Levels: {} } }] }, t);
check("11.10 proprietesDe d'un calque de réglage : nom brut, type « adjustment »", pc2.lignes.some((l) => l.valeur === "Levels 1" && l.brut) && pc2.lignes.some((l) => l.valeur === "photolab.type_calque.adjustment"), pc2);

console.log(`panneaux : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
