// qa/outils/formulaires.mjs — outil du banc backend/tests/test_photolab_formulaires.py (pas un *.test.mjs : run.mjs
// ne le lance pas). Remplit le formulaire de chaque commande du périmètre P3 avec des saisies hostiles, puis rend les
// paramètres que l'écran enverrait. Le registre arrive par FICHIER (jamais en argument : la ligne de commande Windows
// plafonne à 32 767 caractères).
// usage : node formulaires.mjs <registre structuré .json> <sortie .json>
//   registre : {id: {champs: [...]}} (photolab_registre.structurer) ; sortie : [{id, scen, params, sans, aig, act}]
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const js = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "js");
const C = await import(pathToFileURL(join(js, "mod-champs.js")));
const M = await import(pathToFileURL(join(js, "mod-menus.js")));

const reg = JSON.parse(readFileSync(process.argv[2], "utf8"));
const PERIMETRE = /^(filter\.|image\.adjustments\.|layer\.layerStyle\.|layer\.newAdjustmentLayer\.)/;
// Saisies hostiles : chaque champ visible reçoit la même saisie (texte, nombre, tableau…), quel que soit son type.
const SCENARIOS = {
  defaut: (c) => C.valeurInitiale(c),
  zorg: () => "zorg",
  grand: () => 1e9,
  negatif: () => -1e9,
  nan: () => NaN,
  virgule: () => "3,7",
  tableau: () => [300, -5, 2],
  hex3: () => "#ABC",
  vide: () => "",
};
const sortie = [];
for (const id of Object.keys(reg).filter((x) => PERIMETRE.test(x)).sort()) {
  const champs = reg[id].champs;
  const visibles = C.champsVisibles(champs);
  // « bientôt » comme le menu le décide (etatDe) : les familles sur mesure (Courbes…) sont exemptées de sansEcran.
  const aig = M.aiguillage(id);
  const sans = C.D9.has(id) || (aig === "generique" && C.sansEcran(id, champs));
  const commun = { sans, aig, act: M.actionEntree({ id, etat: "actif", champs }) };
  for (const [scen, f] of Object.entries(SCENARIOS)) {
    const vals = {};
    for (const c of visibles) vals[c.cle] = f(c);
    sortie.push({ id, scen, params: C.parametres(champs, vals), ...commun });
    // Teinte/Saturation : la même saisie, colorisation ALLUMÉE (bornes 0..360 / 0..100 côté pont)
    if (visibles.some((c) => c.cle === "colorize")) sortie.push({ id, scen: scen + "+colorize", params: C.parametres(champs, { ...vals, colorize: true }), ...commun });
  }
}
writeFileSync(process.argv[3], JSON.stringify(sortie));
console.log(JSON.stringify({ commandes: new Set(sortie.map((o) => o.id)).size, formulaires: sortie.length }));
