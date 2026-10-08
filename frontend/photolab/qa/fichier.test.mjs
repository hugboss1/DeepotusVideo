// qa/fichier.test.mjs — fichier (C1) : préréglages du dialogue Nouveau, lecture du formulaire, formats d'export.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { PRESETS, CATEGORIES, parametresNouveau, FORMATS_EXPORT, corpsExport, aSauvegarder, orientation, nomDocument } from "../js/mod-fichier.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const dico = JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8"));
const erreur = (f) => { try { f(); return null; } catch (e) { return e.cle || e.message; } };

// 1. préréglages : bornes, catégories, libellés au dictionnaire, aucune marque (D8)
check("1.1 au moins 7 préréglages", PRESETS.length >= 7, PRESETS.length);
check("1.2 chaque préréglage dans les bornes 1..30000, ppi > 0",
  PRESETS.every((p) => Number.isInteger(p.w) && Number.isInteger(p.h) && p.w >= 1 && p.h >= 1 && p.w <= 30000 && p.h <= 30000 && p.ppi > 0));
check("1.3 chaque préréglage dans une catégorie connue", PRESETS.every((p) => CATEGORIES.includes(p.categorie)));
check("1.4 libellés au dictionnaire (fr et en)", PRESETS.every((p) => dico[p.cle] && dico[p.cle].fr && dico[p.cle].en),
  PRESETS.filter((p) => !dico[p.cle]).map((p) => p.cle));
check("1.5 catégories au dictionnaire", CATEGORIES.every((c) => dico["photolab.nouveau.categorie." + c]));
check("1.6 aucun préréglage ne nomme Photoshop", PRESETS.every((p) => !/photoshop/i.test(JSON.stringify([p, dico[p.cle]]))));
const par = (id) => PRESETS.find((p) => p.id === id) || {};
check("1.7 taille par défaut 2100 × 1500 @ 300", par("defaut").w === 2100 && par("defaut").h === 1500 && par("defaut").ppi === 300);
check("1.8 HDTV 1080p", par("hdtv").w === 1920 && par("hdtv").h === 1080 && par("hdtv").ppi === 72);
check("1.9 4K UHD", par("uhd4k").w === 3840 && par("uhd4k").h === 2160);
check("1.10 A4 300 ppi", par("a4").w === 2480 && par("a4").h === 3508 && par("a4").ppi === 300);
check("1.11 identifiants uniques", new Set(PRESETS.map((p) => p.id)).size === PRESETS.length);

// 2. parametresNouveau : bornes, fonds, rejet clair
const base = { nom: "Essai", largeur: "1920", hauteur: "1080", resolution: "72", fond: "white" };
const p = parametresNouveau(base);
check("2.1 forme complète", p.width === 1920 && p.height === 1080 && p.resolution === 72 && p.mode === "rgb" && p.depth === 8
  && p.background === "white" && p.name === "Essai", p);
check("2.2 largeur 0 -> erreur", erreur(() => parametresNouveau({ ...base, largeur: "0" })) === "photolab.nouveau.erreur.largeur");
check("2.3 hauteur 30001 -> erreur", erreur(() => parametresNouveau({ ...base, hauteur: 30001 })) === "photolab.nouveau.erreur.hauteur");
check("2.4 largeur non numérique -> erreur", erreur(() => parametresNouveau({ ...base, largeur: "abc" })) === "photolab.nouveau.erreur.largeur");
check("2.5 largeur décimale -> erreur (pas d'arrondi muet)", erreur(() => parametresNouveau({ ...base, largeur: "12.5" })) === "photolab.nouveau.erreur.largeur");
check("2.6 fond transparent accepté", parametresNouveau({ ...base, fond: "transparent" }).background === "transparent");
check("2.7 fond noir accepté", parametresNouveau({ ...base, fond: "black" }).background === "black");
check("2.8 fond #RRGGBB accepté, mis en minuscules", parametresNouveau({ ...base, fond: "#AABBCC" }).background === "#aabbcc");
check("2.9 hex invalide -> erreur", erreur(() => parametresNouveau({ ...base, fond: "#12345" })) === "photolab.nouveau.erreur.fond");
check("2.10 fond inconnu -> erreur", erreur(() => parametresNouveau({ ...base, fond: "rouge" })) === "photolab.nouveau.erreur.fond");
check("2.11 résolution 0 -> erreur", erreur(() => parametresNouveau({ ...base, resolution: "0" })) === "photolab.nouveau.erreur.resolution");
check("2.12 nom vide -> nom par défaut fourni", parametresNouveau({ ...base, nom: "  " }, "Sans titre").name === "Sans titre");
check("2.13 nom rogné et borné à 120 caractères", parametresNouveau({ ...base, nom: "  x".padEnd(300, "y") }).name.length === 120);
check("2.14 bornes atteintes acceptées", parametresNouveau({ ...base, largeur: 1, hauteur: 30000 }).height === 30000);
check("2.15 chaque erreur a sa clé au dictionnaire",
  ["largeur", "hauteur", "resolution", "fond"].every((k) => dico["photolab.nouveau.erreur." + k]));

// 3. orientation
check("3.1 paysage / portrait / carré", orientation(1920, 1080) === "paysage" && orientation(1080, 1920) === "portrait" && orientation(5, 5) === "carre");

// 4. export : formats du pont, qualité seulement pour jpg/webp
check("4.1 formats PSD PCRAFT PNG JPG WEBP TIFF", ["psd", "pcraft", "png", "jpg", "webp", "tif"].every((f) => FORMATS_EXPORT.some((x) => x.format === f)));
const routes = readFileSync(join(racine, "../../backend/app/api/photolab_routes.py"), "utf8");
const formatsPont = ((routes.match(/FORMATS = \(([^)]*)\)/) || [])[1] || "").match(/"(\w+)"/g).map((s) => s.slice(1, -1));
check("4.2 chaque format est accepté par /enregistrer", FORMATS_EXPORT.every((x) => formatsPont.includes(x.format)), formatsPont);
check("4.3 corps jpg avec qualité", JSON.stringify(corpsExport("jpg", "Mon doc", 85)) === JSON.stringify({ format: "jpg", nom: "Mon doc", quality: 85 }));
check("4.4 corps png sans qualité", JSON.stringify(corpsExport("png", "x", 85)) === JSON.stringify({ format: "png", nom: "x" }));
check("4.5 qualité bornée 1..100", corpsExport("webp", "x", 400).quality === 100 && corpsExport("jpg", "x", -3).quality === 1);
check("4.6 format hors liste -> erreur", erreur(() => corpsExport("exe", "x")) === "photolab.export.erreur.format");

// 5. fermer sans enregistrer : confirmation seulement si la révision a bougé depuis le dernier enregistrement
check("5.1 rien de neuf", !aSauvegarder({ revision: 4 }, 4));
check("5.2 modifié depuis", aSauvegarder({ revision: 5 }, 4));
check("5.3 jamais enregistré : à confirmer dès la première modification", aSauvegarder({ revision: 2 }, null, 1) && !aSauvegarder({ revision: 1 }, null, 1));
check("5.4 aucun document", !aSauvegarder(null, 3));

// 6. nom affiché : /ouvrir copie l'image sous « <empreinte 8>-<nom> » dans le dossier du moteur, qui nomme le document
//    d'après cette copie (relevé le 08/10 : « e99baeb8-herbe.png ») ; l'écran montre et enregistre « herbe ».
check("6.1 empreinte et extension retirées", nomDocument("e99baeb8-herbe.png") === "herbe");
check("6.2 nom d'un document neuf gardé", nomDocument("Sans titre") === "Sans titre" && nomDocument("Affiche v2") === "Affiche v2");
check("6.3 un tiret ordinaire n'est pas une empreinte", nomDocument("mon-image.jpg") === "mon-image");
check("6.4 vide -> vide", nomDocument("") === "" && nomDocument(null) === "");

console.log(`fichier : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
