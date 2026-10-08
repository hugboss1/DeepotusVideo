// qa/menus.test.mjs — menus générés (B4) : catalogue réel donnees/menus.json + registre factice minimal.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { construireMenus, raccourciAffiche, indexRegistre, REFUSES, TRAITES_PAR_ECRAN, actionEntree, parametresRequis, rechercherEntree, placerPanneau } from "../js/mod-menus.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const catalogue = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));
const src = readFileSync(join(racine, "js/mod-menus.js"), "utf8");

const registre = [
  { id: "filter.blur.gaussianBlur", label: "Gaussian Blur…", menu: ["Filter", "Blur"], shortcut: null, params: "{radius}", enabled: true },
  { id: "edit.undo", label: "Undo", menu: ["Edit"], shortcut: "Cmd+Z", params: "{}", enabled: false },
  { id: "image.adjustments.invert", label: "Invert", menu: ["Image", "Adjustments"], shortcut: "Cmd+I", params: "{}", enabled: true },
  { id: "select.all", label: "All", menu: ["Select"], shortcut: "Cmd+A", params: "", enabled: true },
];
const t = (lang) => (c) => ({
  fr: { "photolab.menu.aide": "Aide", "photolab.menu.apropos": "À propos du Photolab" },
  en: { "photolab.menu.aide": "Help", "photolab.menu.apropos": "About Photolab" },
}[lang][c] || c);

const fr = construireMenus(catalogue, registre, REFUSES, "fr", t("fr"));
const en = construireMenus(catalogue, registre, REFUSES, "en", t("en"));

// 1. structure
check("1.1 dix menus (9 + Aide)", fr.length === 10 && en.length === 10, fr.map((m) => m.nom).join());
check("1.2 ordre du catalogue puis Aide", fr.map((m) => m.nom).join() === "File,Edit,Image,Layer,Type,Select,Filter,View,Window,Aide", fr.map((m) => m.nom).join());
check("1.3 noms affichés fr", fr.slice(0, 9).map((m) => m.nom_affiche).join() === "Fichier,Édition,Image,Calque,Texte,Sélection,Filtre,Affichage,Fenêtre", fr.map((m) => m.nom_affiche).join());
check("1.4 noms affichés en = noms du catalogue", en.slice(0, 9).every((m) => m.nom_affiche === m.nom));
check("1.5 Aide : À propos / About", fr[9].nom_affiche === "Aide" && fr[9].entrees[0].libelle === "À propos du Photolab" && en[9].nom_affiche === "Help" && en[9].entrees[0].libelle === "About Photolab");
check("1.6 Aide : id pl.apropos, actif", fr[9].entrees.length === 1 && fr[9].entrees[0].id === "pl.apropos" && fr[9].entrees[0].etat === "actif");

// 2. menu Fichier
const fichier = fr[0].entrees, fichierEn = en[0].entrees;
check("2.1 File commence par Nouveau…", fichier[0].libelle === "Nouveau…" && fichierEn[0].libelle === "New…", fichier[0].libelle);
check("2.2 raccourci Ctrl+N", fichier[0].raccourci === "Ctrl+N");
const trouver = (entrees, id) => { for (const e of entrees) { if (e.id === id) return e; if (e.entrees) { const r = trouver(e.entrees, id); if (r) return r; } } return null; };
check("2.3 file.saveAs traité par l'écran : actif sans registre", trouver(fichier, "file.saveAs").etat === "actif");
check("2.4 file.export.exportAs actif (sous-menu Exporter)", trouver(fichier, "file.export.exportAs").etat === "actif");
check("2.5 file.placeEmbedded -> bientot", trouver(fichier, "file.placeEmbedded").etat === "bientot");
check("2.6 file.automate.batch -> bientot (préfixe refusé)", trouver(fichier, "file.automate.batch").etat === "bientot");
for (const id of ["file.new", "file.open", "file.close", "file.save", "file.saveAs", "file.export.exportAs"])
  check("2.7 écran : " + id, TRAITES_PAR_ECRAN.has(id));

// 3. sous-menus : position et contenu
const exporter = fichier.find((e) => e.type === "sous-menu" && e.nom === "Export");
check("3.1 sous-menu Exporter dans Fichier", !!exporter && exporter.nom_affiche === "Exporter");
const posExport = fichier.indexOf(exporter), posRevert = fichier.findIndex((e) => e.id === "file.revert");
check("3.2 sous-menu après « Revenir », à la place de son premier enfant", posExport > posRevert && fichier[posExport - 1].type === "separateur", [posRevert, posExport]);
const filtre = fr[6].entrees;
const flou = filtre.find((e) => e.type === "sous-menu" && e.nom === "Blur");
check("3.3 Filtre › Flou", !!flou && flou.nom_affiche === "Flou");
const gauss = flou.entrees.find((e) => e.id === "filter.blur.gaussianBlur");
check("3.4 Flou gaussien…", gauss && gauss.libelle === "Flou gaussien…", gauss && gauss.libelle);
check("3.5 flou gaussien actif et à paramètres", gauss.etat === "actif" && gauss.parametres === true);
check("3.6 en : Gaussian Blur…", en[6].entrees.find((e) => e.nom === "Blur").entrees.find((e) => e.id === "filter.blur.gaussianBlur").libelle === "Gaussian Blur…");
check("3.7 flou « moyenne » absent du registre -> bientot", flou.entrees.find((e) => e.id === "filter.blur.average").etat === "bientot");
const profond = fr[3].entrees.find((e) => e.nom === "Smart Objects");
check("3.8 sous-menu de sous-menu (Calque › Objets intelligents › Mode de pile)", profond && profond.entrees.some((e) => e.type === "sous-menu" && e.nom === "Stack Mode"));

// 4. états
check("4.1 enabled:false -> inactif", trouver(fr[1].entrees, "edit.undo").etat === "inactif");
const neg = trouver(fr[2].entrees, "image.adjustments.invert");
check("4.2 négatif : actif, sans paramètres", neg.etat === "actif" && neg.parametres === false);
check("4.3 select.all (params vide) : actif sans paramètres", trouver(fr[5].entrees, "select.all").parametres === false);
check("4.4 raccourci converti", neg.raccourci === "Ctrl+I" && trouver(fichier, "file.save").raccourci === "Ctrl+S" && trouver(fr[1].entrees, "edit.undo").raccourci === "");

// 5. séparateurs
function verifSeparateurs(entrees, chemin) {
  let bon = true;
  if (entrees.length && (entrees[0].type === "separateur" || entrees[entrees.length - 1].type === "separateur")) { bon = false; console.error("  séparateur en tête/fin :", chemin); }
  for (let i = 1; i < entrees.length; i++) if (entrees[i].type === "separateur" && entrees[i - 1].type === "separateur") { bon = false; console.error("  séparateurs doublés :", chemin); }
  for (const e of entrees) if (e.type === "sous-menu") { if (!e.entrees.length) { bon = false; console.error("  sous-menu vide :", chemin + ">" + e.nom); } bon = verifSeparateurs(e.entrees, chemin + ">" + e.nom) && bon; }
  return bon;
}
check("5.1 aucun séparateur en tête/fin/doublé, aucun sous-menu vide (fr)", fr.every((m) => verifSeparateurs(m.entrees, m.nom)));
check("5.2 idem (en)", en.every((m) => verifSeparateurs(m.entrees, m.nom)));
// catalogue mal formé : doubles et bords supprimés
const mauvais = { menus_fr: {}, entrees: [
  { chemin: ["A"], separateur: true }, { chemin: ["A"], id: "x.a", libelle_en: "A", libelle_fr: "A", raccourci: null },
  { chemin: ["A"], separateur: true }, { chemin: ["A"], separateur: true }, { chemin: ["A"], id: "x.b", libelle_en: "B", libelle_fr: "B", raccourci: null },
  { chemin: ["A"], separateur: true } ] };
const mm = construireMenus(mauvais, [], REFUSES, "en", t("en"))[0].entrees;
check("5.3 catalogue mal formé nettoyé", mm.map((e) => e.type === "separateur" ? "-" : e.id).join() === "x.a,-,x.b", mm.map((e) => e.type === "separateur" ? "-" : e.id).join());
// un sous-menu dont tous les enfants disparaissent n'existe pas (ici : aucun, mais le séparateur seul ne fait pas un menu)
const seul = construireMenus({ menus_fr: {}, entrees: [{ chemin: ["A", "B"], separateur: true }, { chemin: ["A"], id: "x.a", libelle_en: "A", libelle_fr: "A", raccourci: null }] }, [], REFUSES, "en", t("en"))[0].entrees;
check("5.4 sous-menu réduit à un séparateur supprimé", seul.length === 1 && seul[0].id === "x.a");

// 6. raccourcis
check("6.1 fr", raccourciAffiche("Cmd+Shift+N", "fr") === "Ctrl+Maj+N");
check("6.2 en", raccourciAffiche("Cmd+Shift+N", "en") === "Ctrl+Shift+N");
check("6.3 Cmd+=", raccourciAffiche("Cmd+=", "fr") === "Ctrl+=" && raccourciAffiche("Cmd+=", "en") === "Ctrl+=");
check("6.4 ordre conservé, Alt inchangé", raccourciAffiche("Cmd+Alt+Shift+W", "fr") === "Ctrl+Alt+Maj+W");
check("6.5 touches seules", raccourciAffiche("F12", "fr") === "F12" && raccourciAffiche("Q", "fr") === "Q");
check("6.6 vide/null", raccourciAffiche(null, "fr") === "" && raccourciAffiche("", "en") === "");
check("6.7 ponctuation", raccourciAffiche("Cmd+-", "fr") === "Ctrl+-" && raccourciAffiche("Cmd+Shift+[", "fr") === "Ctrl+Maj+[");

// 7. refuses : copie de PREFIXES_REFUSES du pont
const py = readFileSync(join(racine, "../../backend/app/services/photolab_moteur.py"), "utf8");
const m = py.match(/PREFIXES_REFUSES = \(([\s\S]*?)\)\s*#/);
const prefPy = m ? [...m[1].matchAll(/"([^"]+)"/g)].map((x) => x[1].toLowerCase()) : [];
check("7.1 REFUSES identique à PREFIXES_REFUSES (lecture du source Python)", prefPy.length > 0 && JSON.stringify(prefPy) === JSON.stringify(REFUSES.map((x) => x.toLowerCase())), JSON.stringify([prefPy, REFUSES]));
check("7.2 REFUSES en minuscules", REFUSES.every((x) => x === x.toLowerCase()));

// 8. actions
const idx = indexRegistre(registre);
check("8.1 indexRegistre (tableau)", idx.get("edit.undo").enabled === false && indexRegistre({ commands: registre }).size === 4 && indexRegistre(null).size === 0);
check("8.2 parametresRequis", parametresRequis("{radius}") === true && parametresRequis("{}") === false && parametresRequis("") === false && parametresRequis(null) === false && parametresRequis(" { } ") === false);
check("8.3 action écran", actionEntree(trouver(fichier, "file.new")) === "ecran");
check("8.4 action à propos", actionEntree(fr[9].entrees[0]) === "apropos");
check("8.5 action exécuter", actionEntree(neg) === "executer");
check("8.6 action dialogue P3 pour paramètres", actionEntree(gauss) === "dialogue");
check("8.7 bientôt / inactif -> rien", actionEntree(trouver(fichier, "file.placeEmbedded")) === "rien" && actionEntree(trouver(fr[1].entrees, "edit.undo")) === "rien");

// 9. recherche d'une entrée par raccourci (Ctrl+Z, etc. : le moteur seul dit si la commande existe)
check("9.1 rechercherEntree par id", rechercherEntree(fr, "image.adjustments.invert").id === "image.adjustments.invert" && rechercherEntree(fr, "nimporte") === null);

// 11. placement des panneaux dans la fenêtre (M11) : sous-menu retourné à gauche s'il déborde, hauteur et haut bornés
const F = { w: 1000, h: 700 };
const sm = placerPanneau({ gauche: 100, droite: 340, haut: 50, bas: 74 }, { w: 240, h: 200 }, F, "droite");
check("11.1 sous-menu à droite de la ligne", sm.x === 338 && sm.y === 46 && sm.maxH >= 200, JSON.stringify(sm));
const smG = placerPanneau({ gauche: 800, droite: 960, haut: 50, bas: 74 }, { w: 240, h: 200 }, F, "droite");
check("11.2 débordement à droite : retourné à gauche", smG.x === 800 - 240 + 2, JSON.stringify(smG));
const bas = placerPanneau({ gauche: 100, droite: 340, haut: 600, bas: 624 }, { w: 240, h: 300 }, F, "droite");
check("11.3 sous-menu trop bas : remonté dans la fenêtre", bas.y + 300 <= F.h - 8 && bas.y >= 8, JSON.stringify(bas));
const haut = placerPanneau({ gauche: 10, droite: 60, haut: 31, bas: 31 }, { w: 240, h: 900 }, F, "bas");
check("11.4 menu de la barre : sous le bouton, hauteur bornée à la fenêtre", haut.y === 31 && haut.maxH === F.h - 31 - 8 && haut.x === 10, JSON.stringify(haut));
const bordD = placerPanneau({ gauche: 900, droite: 960, haut: 31, bas: 31 }, { w: 240, h: 100 }, F, "bas");
check("11.5 menu de la barre : borné au bord droit", bordD.x + 240 <= F.w - 2, JSON.stringify(bordD));
const tiny = placerPanneau({ gauche: 0, droite: 50, haut: 0, bas: 10 }, { w: 240, h: 900 }, { w: 300, h: 100 }, "droite");
check("11.6 fenêtre minuscule : jamais de y négatif", tiny.y >= 0 && tiny.x >= 0, JSON.stringify(tiny));

// 10. aucune chaîne française en dur dans le module (C4) ni mot interdit
check("10.1 sans ArtCraft/Discord/Photoshop", !/artcraft|discord|photoshop/i.test(src));
check("10.2 pas de texte français accentué en dur", !/[éèêàùçô]/i.test(src.replace(/\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "")));

console.log(`menus : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
