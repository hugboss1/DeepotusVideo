// qa/outils/libelles.mjs — outil du banc backend/tests/test_photolab_libelles.py (pas un *.test.mjs : run.mjs ne le
// lance pas). Calcule, avec la MÊME définition que l'écran (mod-champs.js, mod-menus.js), le périmètre de textes de
// la tâche B3 : les clés de paramètres visibles et les valeurs d'énumération fermée des commandes qui ouvrent un
// dialogue (filtres du menu, ajustements, calques de réglage, styles de calque).
// usage : node libelles.mjs <registre structuré .json> <menus.json> <sortie .json>
//   sortie : {ids: [...], params: {cle: [ids]}, valeurs: {valeur: [ids]}}
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const js = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "js");
const C = await import(pathToFileURL(join(js, "mod-champs.js")));
const M = await import(pathToFileURL(join(js, "mod-menus.js")));

const reg = JSON.parse(readFileSync(process.argv[2], "utf8"));
const menus = readFileSync(process.argv[3], "utf8");
const FILTRES_MENU = new Set([...menus.matchAll(/"(filter\.[A-Za-z.]+)"/g)].map((m) => m[1]));
const STYLES_B6 = ["bevelEmboss", "colorOverlay", "dropShadow", "gradientOverlay", "innerGlow", "innerShadow", "outerGlow", "patternOverlay", "satin", "stroke", "blendingOptions", "globalLight"];

const ids = [];
for (const id of Object.keys(reg).sort()) {
  let dedans = false;
  if (id.startsWith("filter.")) dedans = FILTRES_MENU.has(id) && !id.startsWith("filter.gallery.");
  else if (id.startsWith("image.adjustments.")) dedans = true;
  else if (id.startsWith("layer.newAdjustmentLayer.")) dedans = true;
  else if (id.startsWith("layer.layerStyle.")) dedans = STYLES_B6.includes(id.slice("layer.layerStyle.".length));
  if (!dedans) continue;
  const champs = reg[id].champs;
  // « bientôt » : l'écran n'ouvre aucun dialogue, aucun texte à écrire (les familles sur mesure sont exemptées).
  if (C.D9.has(id) || (M.aiguillage(id) === "generique" && C.sansEcran(id, champs))) continue;
  ids.push(id);
}
const params = {}, valeurs = {};
for (const id of ids) {
  for (const c of C.champsVisibles(reg[id].champs)) {
    (params[c.cle] = params[c.cle] || []).push(id);
    // Énumération fermée hors modes de fusion (clé blend : textes photolab.fusion.*, jamais photolab.valeur.*).
    if (c.type === "enum" && !c.ouverte && String(c.cle).toLowerCase() !== "blend") {
      for (const v of c.valeurs || []) (valeurs[String(v)] = valeurs[String(v)] || []).push(id);
    }
  }
}
writeFileSync(process.argv[4], JSON.stringify({ ids, params, valeurs }));
console.log(JSON.stringify({ commandes: ids.length, cles: Object.keys(params).length, valeurs: Object.keys(valeurs).length }));
