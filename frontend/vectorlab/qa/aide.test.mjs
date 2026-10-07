// aide.test.mjs — t126 : les fiches didactiques du vectorlab (aide/index.json + animations à trois temps),
// contrôlées par le banc commun (vectorlab/qa/aide_commun.mjs).
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { verifier_aide } from "./aide_commun.mjs";

const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const dossierJs = join(racine, "js");
const sources = [readFileSync(join(racine, "index.html"), "utf-8"),
  ...readdirSync(dossierJs).filter((n) => n.endsWith(".js")).map((n) => readFileSync(join(dossierJs, n), "utf-8"))];
const echecs = verifier_aide(join(racine, "aide"), sources);
if (echecs.length) { console.error("ECHECS aide vectorlab :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA aide vectorlab : PASS (fiches valides, animations 320×200 à trois temps, ids présents)");
