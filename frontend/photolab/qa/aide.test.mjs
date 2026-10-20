// aide.test.mjs — t140 : les fiches didactiques du Photolab (aide/index.json + animations à trois temps), contrôlées
// par le banc commun (vectorlab/qa/aide_commun.mjs). Les ids des barres d'icônes sont COMPOSÉS à l'exécution
// (idEmplacement, idReglage) : le banc les produit à partir des mêmes tables que la page, pour que le contrôleur
// commun les trouve écrits.
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { verifier_aide } from "../../vectorlab/qa/aide_commun.mjs";
import { EMPLACEMENTS, idEmplacement, idFlyout } from "../js/mod-outils.js";
import { KINDS, idReglage } from "../js/mod-reglages.js";

const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const ids = [...EMPLACEMENTS.map((_, i) => idEmplacement(i)), ...KINDS.map((k) => idReglage(k.kind)),
  "pl-espace",           // t151 : le sélecteur d'espace de travail (mod-espaces.js)
  "pl-calque-ia", "pl-iac-detourer",   // t193 : le calque IA (pied des Calques) et le détourage (mod-iacalque.js)
  // t259 : chaque ligne de flyout porte l'id de SON outil — les outils neufs de photocraft 0.10 (M3-M5) y vivent
  ...EMPLACEMENTS.flat().map((o) => idFlyout(o.id))];
const sources = [readFileSync(join(racine, "index.html"), "utf-8"),
  ...readdirSync(join(racine, "js")).filter((n) => n.endsWith(".js")).map((n) => readFileSync(join(racine, "js", n), "utf-8")),
  ids.map((i) => `id="${i}"`).join("\n")];
const echecs = verifier_aide(join(racine, "aide"), sources);

const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
ok("ids des emplacements : pl-outil-<outil principal>, uniques", new Set(ids).size === ids.length && idEmplacement(1) === "pl-outil-rectMarquee"
  && idReglage("blackWhite") === "pl-aj-blackWhite", ids.slice(0, 4));
const index = JSON.parse(readFileSync(join(racine, "aide", "index.json"), "utf-8"));
ok("au moins quatre fiches (options principales : sélection, baguette, recadrage, un réglage)", index.length >= 4, index.length);
ok("chaque fiche vise une option qui EXISTE dans la page", index.every((f) => ids.includes(f.id)), index.map((f) => f.id));
ok("phrases courtes (≤ 25 mots), sans jargon", index.every((f) => f.phrase.split(/\s+/).length <= 25 && !/alpha|calque de réglage|pixel/i.test(f.phrase)),
  index.map((f) => f.phrase.split(/\s+/).length));
// t259 : les lignes de flyout ont un id stable, posé par le code (pas seulement par ce banc)
const outils = readFileSync(join(racine, "js", "mod-outils.js"), "utf-8");
ok("t259 idFlyout : pl-flyout-<outil>, posé sur chaque ligne du flyout", idFlyout("patch") === "pl-flyout-patch"
  && /l\.id = idFlyout\(o\.id\)/.test(outils));
const NEUFS = ["patch", "contentAwareMove", "patternStamp", "redEye", "remove", "rowMarquee", "columnMarquee", "magneticLasso",
  "perspectiveCrop", "colorSampler", "rotateView", "freeformPen", "curvaturePen", "addAnchorPoint", "deleteAnchorPoint", "convertPoint",
  "verticalType", "horizontalTypeMask", "verticalTypeMask", "directSelection"];
ok("t259 : chaque outil neuf de photocraft 0.10 (M3-M5) a sa fiche, en français ET en anglais",
  NEUFS.every((o) => index.some((f) => f.id === idFlyout(o) && f.titre_en && f.phrase_en && f.fichier_en)),
  NEUFS.filter((o) => !index.some((f) => f.id === idFlyout(o) && f.titre_en && f.phrase_en && f.fichier_en)));
ok("t259 : phrases anglaises courtes aussi (≤ 25 mots)", index.every((f) => !f.phrase_en || f.phrase_en.split(/\s+/).length <= 25));
const html = readFileSync(join(racine, "index.html"), "utf-8"), css = readFileSync(join(racine, "photolab.css"), "utf-8");
ok("l'encart partagé est chargé, sur le dossier aide/ du Photolab", /import \{ initDidact \} from "\/vectorlab\/js\/mod-didact\.js"; initDidact\(\{\}, \{ aide: "aide\/", racine: "body" \}\);/.test(html));
ok("dans les barres d'icônes (outils, grille de réglages, pied des Calques — t193), le « ? » est masqué : pas de case en plus",
  /#outils \.vl-didact-q, \.rg-grille \.vl-didact-q, \.cq-pied \.vl-didact-q, \.flyout \.vl-didact-q \{ display: none; \}/.test(css));

if (echecs.length) { console.error("QA aide photolab : " + echecs.length + " échec(s)\n  " + echecs.join("\n  ")); process.exit(1); }
console.log("QA aide photolab : PASS (fiches valides, animations 320×200 à trois temps, ids présents)");
