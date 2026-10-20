// photolab_menus.mjs — la barre de menus du Photolab telle que l'écran la construit, pour le catalogue de l'assistant
// (catalogue_sources.depuis_menus_photolab). Appelle la VRAIE construireMenus de frontend/photolab/js/mod-menus.js
// (menus.json + insertions de l'écran + entrées « pl.* ») sur le registre reçu, en FR puis en EN, et rend à plat les
// commandes avec leur chemin de sous-menus affiché et leur état (actif | inactif | bientot).
//   node photolab_menus.mjs <racine>   ; stdin : {"registre": [...avec champs], "dico": {clé: {fr, en}}}
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const racine = process.argv[2];
const { registre, dico } = JSON.parse(readFileSync(0, "utf8"));
const M = await import(pathToFileURL(join(racine, "frontend", "photolab", "js", "mod-menus.js")).href);
const catalogue = JSON.parse(readFileSync(join(racine, "frontend", "photolab", "donnees", "menus.json"), "utf8"));
const sortie = {};
for (const lang of ["fr", "en"]) {
  const t = (c) => (dico[c] && dico[c][lang]) || c;        // dzT rend la clé elle-même quand elle manque
  const L = [];
  const voir = (entrees, chemin) => {
    for (const e of entrees) {
      if (e.type === "sous-menu") voir(e.entrees, [...chemin, e.nom_affiche]);
      else if (e.type === "commande") L.push({ id: e.id, libelle: e.libelle, raccourci: e.raccourci || "", etat: e.etat, chemin });
    }
  };
  for (const m of M.construireMenus(catalogue, registre, M.REFUSES, lang, t)) voir(m.entrees, [m.nom_affiche]);
  sortie[lang] = L;
}
process.stdout.write(JSON.stringify(sortie));
