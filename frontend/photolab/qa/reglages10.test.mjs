// qa/reglages10.test.mjs — t251 (Photolab M2) : la forme 0.10 de doc.inspect ({kind, params}) donne À L'ÉCRAN les
// MÊMES paramètres que la forme 0.3.0 pour le même état. Les deux fixtures sont relevées sur les vrais moteurs par
// backend/tests/test_photolab_reglages_moteur.py, avec les mêmes paramètres envoyés (reglages-inspect-0.3.0.json :
// copie de la fixture d'avant la montée ; reglages-inspect.json : moteur épinglé, 0.10.0).
// Seule perte admise, dite en clair : Color Lookup — 0.10 ne décrit plus QUEL LUT est posé, `lut` reste absent.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { kindDe, depuisInspect, egalProfond, KINDS } from "../js/mod-reglages.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const lire = (n) => JSON.parse(readFileSync(join(racine, "qa/fixtures", n), "utf8"));
const v03 = lire("reglages-inspect-0.3.0.json"), v10 = lire("reglages-inspect.json");

check("1 mêmes 21 cas dans les deux fixtures, mêmes paramètres envoyés",
  egalProfond(Object.keys(v03).sort(), Object.keys(v10).sort()) && Object.keys(v10).every((k) => egalProfond(v03[k].envoye, v10[k].envoye)));
check("2 la fixture épinglée est bien en forme 0.10 ({kind, params}) partout",
  Object.values(v10).every((f) => f.adjustment && f.adjustment.kind === f.kind && typeof f.adjustment.params === "object"));
check("3 kindDe lit la forme 0.10 (21 cas) et refuse un kind inconnu",
  Object.values(v10).every((f) => kindDe({ adjustment: f.adjustment }) === f.kind)
  && kindDe({ adjustment: { kind: "zorg", params: {} } }) === null && kindDe({ adjustment: { kind: "curves" } }) === null);

for (const k of Object.keys(v10).sort()) {
  const f = v10[k];
  const nouveau = depuisInspect(f.kind, f.adjustment, f.lut_list);
  const ancien = depuisInspect(f.kind, v03[k].adjustment, v03[k].lut_list);
  if (f.kind === "colorLookup") {
    const { lut, ...reste } = ancien;
    check("4 " + k + " : mêmes paramètres SANS `lut` (0.10 ne dit plus quel LUT ; le moteur garde le sien)",
      egalProfond(nouveau, reste) && !("lut" in nouveau), { ancien, nouveau });
  } else {
    check("4 " + k + " : mêmes paramètres qu'avec l'état 0.3.0", egalProfond(nouveau, ancien), { ancien, nouveau });
  }
}
check("5 un état 0.10 d'un AUTRE kind que celui demandé -> {} (jamais d'exception)",
  JSON.stringify(depuisInspect("curves", v10["levels/base"].adjustment, null)) === "{}"
  && JSON.stringify(depuisInspect("levels", { kind: "levels", params: null }, null)) === "{}");
check("6 les 16 kinds de l'écran ont un cas 0.10", KINDS.every((x) => (v10[x.kind + "/base"] || {}).kind === x.kind));

console.log("reglages10 :", ok, "ok,", ko, "echec(s)");
if (ko) process.exit(1);
