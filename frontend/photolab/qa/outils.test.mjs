// qa/outils.test.mjs — données et fonctions pures de la barre d'outils (B3) : 20 emplacements, lettres et cyclage,
// infobulles, barre d'options, conversion de couleur.
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { EMPLACEMENTS, SECTIONS, outilParLettre, emplacementDe, outilDe, cleNom, infobulle, optionsPour, OPTIONS_DEFAUT, rgbaVersHex, groupeDeLettre } from "../js/mod-outils.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");

// 1. structure
check("1.1 20 emplacements", EMPLACEMENTS.length === 20, EMPLACEMENTS.length);
check("1.2 sections : somme 20", SECTIONS.reduce((a, b) => a + b, 0) === 20 && SECTIONS.length === 4);
const tous = EMPLACEMENTS.flat();
check("1.3 identifiants uniques", new Set(tous.map((o) => o.id)).size === tous.length);
check("1.4 chaque icône existe dans icones/", tous.every((o) => existsSync(join(racine, "icones", o.icone + ".svg"))),
  tous.filter((o) => !existsSync(join(racine, "icones", o.icone + ".svg"))).map((o) => o.icone));
check("1.5 44 outils actifs (P2 : 11 ; t155 peinture et retouche : +18 ; t156 texte, formes, plume : +9 ; t157 sélection d'objet : +1 ; t160 Règle, Note, Comptage, Tranche, Sélection de tranche : +5)", tous.filter((o) => o.p2).length === 44, tous.filter((o) => o.p2).map((o) => o.id).join());
check("1.6 emplacementDe", emplacementDe("move") === 0 && emplacementDe("ellipseMarquee") === 1 && emplacementDe("zoom") === 19 && emplacementDe("nimporte") === -1);
check("1.7 outilDe", outilDe("crop").lettre === "C" && outilDe("x") === null);
check("1.8 cleNom", cleNom("rectMarquee") === "photolab.outil.rect_marquee" && cleNom("move") === "photolab.outil.move");

// 2. cyclage des lettres (shortcuts.rs:327-340)
check("2.1 M depuis move -> rectMarquee", outilParLettre("M", "move", false) === "rectMarquee");
check("2.2 M depuis rectMarquee -> ellipseMarquee", outilParLettre("M", "rectMarquee", false) === "ellipseMarquee");
check("2.3 M depuis ellipseMarquee -> rectMarquee", outilParLettre("M", "ellipseMarquee", false) === "rectMarquee");
check("2.4 W depuis magicWand -> quickSelection", outilParLettre("W", "magicWand", false) === "quickSelection");
check("2.5 W depuis quickSelection -> objectSelection (t157), puis magicWand", outilParLettre("W", "quickSelection", false) === "objectSelection"
  && outilParLettre("W", "objectSelection", false) === "magicWand");
check("2.6 W depuis un autre groupe -> premier du groupe", outilParLettre("W", "move", false) === "magicWand");
check("2.7 lettre en minuscule", outilParLettre("m", "move", false) === "rectMarquee");
check("2.8 prefMaj sans Maj garde l'outil courant du groupe", outilParLettre("M", "rectMarquee", false, true) === "rectMarquee");
check("2.9 prefMaj avec Maj cycle", outilParLettre("M", "rectMarquee", true, true) === "ellipseMarquee");
check("2.10 prefMaj, autre groupe : premier outil", outilParLettre("M", "move", false, true) === "rectMarquee");
check("2.11 B -> Pinceau ; B depuis Pinceau -> Crayon (t155)", outilParLettre("B", "move", false) === "brush" && outilParLettre("B", "brush", false) === "pencil");
check("2.11b J saute la Pièce (absente du moteur) : healing -> spotHealing", outilParLettre("J", "healing", false) === "spotHealing");
check("2.11c t156 : P choisit la Plume ; une lettre sans outil (K) -> null", outilParLettre("P", "move", false) === "pen" && outilParLettre("K", "move", false) === null);
check("2.12 lettre inconnue -> null", outilParLettre("K", "move", false) === null && outilParLettre("", "move", false) === null);
check("2.13 V depuis move -> move (un seul)", outilParLettre("V", "move", false) === "move");
check("2.14 t160 : I cycle pipette -> règle -> note -> comptage -> pipette ; C : recadrage -> tranche -> sélection de tranche",
  outilParLettre("I", "eyedropper", false) === "ruler" && outilParLettre("I", "ruler", false) === "note" && outilParLettre("I", "note", false) === "count"
  && outilParLettre("I", "count", false) === "eyedropper" && outilParLettre("C", "crop", false) === "slice" && outilParLettre("C", "slice", false) === "sliceSelect");
check("2.15 L : lasso -> polygonLasso -> lasso", outilParLettre("L", "lasso", false) === "polygonLasso" && outilParLettre("L", "polygonLasso", false) === "lasso");
check("2.16 groupeDeLettre W : 3 outils, tous actifs (t157)", groupeDeLettre("W").length === 3 && groupeDeLettre("W").filter((o) => o.p2).length === 3);
check("2.17 outil sans lettre (blur) ignoré", groupeDeLettre("").length === 0);

// 3. infobulles
const t = (c) => ({ "photolab.outil.move": "Déplacement", "photolab.outil.bientot": "bientôt" }[c] || c);
check("3.1 infobulle avec lettre", infobulle(outilDe("move"), t) === "Déplacement (V)");
check("3.2 infobulle outil à venir (la Pièce)", infobulle(outilDe("patch"), t).endsWith(" — bientôt") && !infobulle(outilDe("brush"), t).includes("bientôt"));
check("3.3 infobulle sans lettre", !infobulle(outilDe("blur"), t).includes("("));

// 4. barre d'options
const kinds = (id) => optionsPour(id).map((o) => o.cle).join();
// t157 : boutons « Sélectionner un sujet » et « Sélectionner et masquer… » en queue des outils de sélection.
check("4.1 rectangle : mode, contour, lissage, Sélectionner et masquer", kinds("rectMarquee") === "mode,feather,antiAlias,selectAndMask", kinds("rectMarquee"));
check("4.2 lasso polygonal idem", kinds("polygonLasso") === "mode,feather,antiAlias,selectAndMask");
check("4.3 baguette", kinds("magicWand") === "mode,tolerance,antiAlias,contiguous,sampleAllLayers,selectSubject,selectAndMask", kinds("magicWand"));
check("4.4 sélection rapide", kinds("quickSelection") === "mode,size,sampleAllLayers,selectSubject,selectAndMask", kinds("quickSelection"));
check("4.4b sélection d'objet (t157)", kinds("objectSelection") === "mode,sampleAllLayers,selectSubject,selectAndMask", kinds("objectSelection"));
check("4.4c les boutons portent l'entrée qu'ils déclenchent", optionsPour("objectSelection").filter((o) => o.type === "bouton").map((o) => o.action).join() === "select.subject,select.selectAndMask");
check("4.5 recadrage", kinds("crop") === "deleteCroppedPixels");
check("4.6 déplacement", kinds("move") === "autoSelect,autoCible", kinds("move"));
check("4.7 main, zoom, pipette : aucune", kinds("hand") === "" && kinds("zoom") === "" && kinds("eyedropper") === "");
check("4.8 valeurs par défaut du plan", OPTIONS_DEFAUT.tolerance === 32 && OPTIONS_DEFAUT.size === 30 && OPTIONS_DEFAUT.contiguous === true
  && OPTIONS_DEFAUT.sampleAllLayers === false && OPTIONS_DEFAUT.deleteCroppedPixels === true && OPTIONS_DEFAUT.mode === "replace" && OPTIONS_DEFAUT.feather === 0);
const tol = optionsPour("magicWand").find((o) => o.cle === "tolerance");
check("4.9 tolérance 0..255", tol.min === 0 && tol.max === 255 && tol.type === "nombre");
const mode = optionsPour("lasso")[0];
check("4.10 quatre modes", mode.type === "mode" && mode.valeurs.join() === "replace,add,subtract,intersect");
check("4.11 chaque option (hors boutons d'action) a un défaut dans OPTIONS_DEFAUT", ["move", "rectMarquee", "magicWand", "quickSelection", "crop", "objectSelection"].every((id) =>
  optionsPour(id).every((o) => o.type === "bouton" || o.cle in OPTIONS_DEFAUT)));
check("4.12 clés de libellé en snake_case sous photolab.option.", ["magicWand", "move", "crop", "quickSelection"].every((id) => optionsPour(id).every((o) => /^photolab\.option\.[a-z0-9_]+$/.test(o.libelle))));

// 5. couleurs du moteur (flottants RGBA) -> #rrggbb
check("5.1 noir", rgbaVersHex([0, 0, 0, 1]) === "#000000");
check("5.2 blanc", rgbaVersHex([1, 1, 1, 1]) === "#ffffff");
check("5.3 rouge", rgbaVersHex([1, 0, 0, 1]) === "#ff0000");
check("5.4 arrondi et bornes", rgbaVersHex([0.5, 2, -1]) === "#80ff00");
check("5.5 entrée invalide -> noir", rgbaVersHex(null) === "#000000" && rgbaVersHex("x") === "#000000");

// 6. cohérence avec le CSS : pas de nom d'outil Photoshop, mots interdits
const src = readFileSync(join(racine, "js/mod-outils.js"), "utf8");
check("6.1 sans ArtCraft/Discord/Photoshop", !/artcraft|discord|photoshop/i.test(src));

console.log(`outils : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
