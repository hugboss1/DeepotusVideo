// aide.test.mjs — t140 : les fiches didactiques du Photolab (aide/index.json + animations à trois temps), contrôlées
// par le banc commun (vectorlab/qa/aide_commun.mjs). Les ids des barres d'icônes sont COMPOSÉS à l'exécution
// (idEmplacement, idReglage) : le banc les produit à partir des mêmes tables que la page, pour que le contrôleur
// commun les trouve écrits.
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { verifier_aide } from "../../vectorlab/qa/aide_commun.mjs";
import { EMPLACEMENTS, idEmplacement } from "../js/mod-outils.js";
import { KINDS, idReglage } from "../js/mod-reglages.js";

const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const ids = [...EMPLACEMENTS.map((_, i) => idEmplacement(i)), ...KINDS.map((k) => idReglage(k.kind))];
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
const html = readFileSync(join(racine, "index.html"), "utf-8"), css = readFileSync(join(racine, "photolab.css"), "utf-8");
ok("l'encart partagé est chargé, sur le dossier aide/ du Photolab", /import \{ initDidact \} from "\/vectorlab\/js\/mod-didact\.js"; initDidact\(\{\}, \{ aide: "aide\/", racine: "body" \}\);/.test(html));
ok("dans les barres d'icônes, le « ? » est masqué (pas de case en plus dans la colonne d'outils)",
  /#outils \.vl-didact-q, \.rg-grille \.vl-didact-q \{ display: none; \}/.test(css));

if (echecs.length) { console.error("QA aide photolab : " + echecs.length + " échec(s)\n  " + echecs.join("\n  ")); process.exit(1); }
console.log("QA aide photolab : PASS (fiches valides, animations 320×200 à trois temps, ids présents)");
