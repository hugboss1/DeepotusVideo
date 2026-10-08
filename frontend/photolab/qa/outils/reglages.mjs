// qa/outils/reglages.mjs — outil du banc backend/tests/test_photolab_formulaires.py, section [5] (pas un *.test.mjs :
// run.mjs ne le lance pas). Pour chaque cas de qa/fixtures/reglages-inspect.json (relevé sur le VRAI moteur) :
//   - l'état relu par depuisInspect (ce que l'éditeur du calque de réglage tient pour « avant ») ;
//   - Courbes / Niveaux : les quatre canaux que l'éditeur de B4 envoie au relâchement (mode cible, complet) ;
//   - les autres : chaque contrôle de chaque vue (toutes les gammes / tons / couches de sortie) saisi avec des valeurs
//     hostiles, et la `difference` qu'enverrait layer.setAdjustment.
// Le banc Python passe chaque jeu à PM.commande_autorisee("layer.setAdjustment", {layer, ...}, kind, etat=adjustment).
// usage : node reglages.mjs <registre .json {id: {champs}}> <sortie .json>  ->  [{nom, kind, params, etat}]
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ici = dirname(fileURLToPath(import.meta.url));
const js = join(ici, "..", "..", "js");
const R = await import(pathToFileURL(join(js, "mod-reglages.js")));
const K = await import(pathToFileURL(join(js, "mod-courbes.js")));
const registre = JSON.parse(readFileSync(process.argv[2], "utf8"));
const fixture = JSON.parse(readFileSync(join(ici, "..", "fixtures", "reglages-inspect.json"), "utf8"));

const SAISIES = [undefined, "zorg", 1e9, -1e9, Number.NaN, "3,7", "#ABC", "", true, false, [300, -5, 2]];
const sortie = [];
for (const [nom, f] of Object.entries(fixture)) {
  const champs = (registre["layer.newAdjustmentLayer." + f.kind] || {}).champs || [];
  const etat = R.depuisInspect(f.kind, f.adjustment, f.lut_list);
  const pousser = (n, params) => sortie.push({ nom: nom + " " + n, kind: f.kind, params, etat: f.adjustment });
  pousser("état relu", etat);
  const sorte = R.sorteEditeur(f.kind);
  if (sorte === "ton") {
    const s = f.kind === "curves" ? "courbes" : "niveaux";
    const p = s === "courbes" ? K.paramsCourbes(K.etatDepuisParams(s, etat), { complet: true }) : K.paramsNiveaux(K.etatDepuisParams(s, etat), { complet: true });
    pousser("quatre canaux (éditeur B4, cible)", p);
    continue;
  }
  const vue0 = R.vueReglage(f.kind, etat, null, champs);
  const choix = vue0.selecteur ? vue0.selecteur.options.map((o) => o.valeur) : [null];
  for (const ch of choix) {
    const vue = R.vueReglage(f.kind, etat, ch, champs);
    for (const e of vue.champs) {
      const b = e.c;
      const extremes = typeof b.min === "number" ? [b.min, b.max, (b.min + b.max) / 2 + 0.37] : [];
      for (const s of [...extremes, ...SAISIES]) {
        const apres = R.appliquer(etat, e, s === undefined ? e.valeur : s, R.valeursVue(vue, etat));
        const d = R.difference(etat, apres);
        if (Object.keys(d).length) pousser(`${ch || ""}/${b.cle}=${JSON.stringify(s)}`, d);
      }
    }
  }
}
writeFileSync(process.argv[3], JSON.stringify(sortie));
