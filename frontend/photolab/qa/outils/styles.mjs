// qa/outils/styles.mjs — outil du banc backend/tests/test_photolab_formulaires.py (pas un *.test.mjs : run.mjs ne le
// lance pas). Rejoue le dialogue Style de calque (mod-styles.js) sur des éditions types et des saisies hostiles, et
// rend les étapes que l'écran enverrait (etapesStyles), pour que le banc Python les passe à la liste blanche du pont
// puis, pour quelques-unes, au VRAI moteur. Le calque visé vaut CALQUE (le banc le remplace par un vrai id).
// usage : node styles.mjs <sortie .json>   -> [{nom, kind, command, params}]
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const js = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "js");
const S = await import(pathToFileURL(join(js, "mod-styles.js")));
const C = await import(pathToFileURL(join(js, "mod-calques.js")));

const CALQUE = 1;
const copie = (x) => JSON.parse(JSON.stringify(x));
const calque = { id: CALQUE, name: "haut", blend: "Normal", opacity: 1, fill: 1 };
const base = S.etatStyles({}, undefined, calque);
const sortie = [];
const ajouter = (nom, avant, apres) => {
  for (const e of S.etapesStyles(avant, apres, CALQUE)) sortie.push({ nom, kind: e.command.slice("layer.layerStyle.".length), ...e });
};
const regle = (etat, kind, f) => { const x = copie(etat); f(x[kind]); return x; };
// Saisies hostiles, appliquées à TOUS les champs du style (comme le banc des formulaires génériques).
const HOSTILES = { zorg: "zorg", grand: 1e9, negatif: -1e9, nan: NaN, virgule: "3,7", hex3: "#ABC", vide: "", tableau: [300, -5, 2] };

for (const s of S.EFFETS) {
  const coche = regle(base, s.kind, (x) => { x.actif = true; });
  ajouter(`${s.kind} coché aux défauts`, base, coche);
  for (const c of s.champs) {
    // chaque champ à sa borne haute (ou basculé) : tous les paramètres repartent
    const v = c.type === "number" ? c.max : c.type === "bool" ? !S.defautsStyle(s.kind)[c.cle]
      : c.type === "enum" ? c.valeurs[c.valeurs.length - 1] : c.type === "color" ? "#12ab34" : "difference";
    ajouter(`${s.kind} ${c.cle} = ${v}`, coche, regle(coche, s.kind, (x) => { x.params[c.cle] = v; }));
  }
  for (const [nom, v] of Object.entries(HOSTILES)) {
    ajouter(`${s.kind} saisie ${nom}`, base, regle(coche, s.kind, (x) => { for (const c of s.champs) x.params[c.cle] = v; }));
  }
  const actif = regle(coche, s.kind, (x) => { x.present = true; });
  ajouter(`${s.kind} désactivé`, actif, regle(actif, s.kind, (x) => { x.actif = false; }));
}
// Options de fusion : chaque mode (passThrough compris, pour un groupe), opacités aux bornes, saisies hostiles.
for (const m of [C.MODE_TRANSFERT, ...C.MODES_FUSION]) {
  ajouter(`options fusion ${m.id}`, base, regle(base, S.OPTIONS_FUSION, (x) => { x.params.blend = m.moteur; }));
}
for (const [nom, v] of Object.entries(HOSTILES)) {
  ajouter(`options saisie ${nom}`, base, regle(base, S.OPTIONS_FUSION, (x) => { x.params = { blend: v, opacity: v, fillOpacity: v }; }));
}
ajouter("options opacité 0 fond 0", base, regle(base, S.OPTIONS_FUSION, (x) => { x.params.opacity = 0; x.params.fillOpacity = 0; }));
// Tout coché d'un coup (11 étapes : borne de /apercu = 12).
const tout = copie(base);
for (const s of S.EFFETS) tout[s.kind].actif = true;
tout[S.OPTIONS_FUSION].params.fillOpacity = 60;
ajouter("tout coché", base, tout);

writeFileSync(process.argv[2], JSON.stringify(sortie));
console.log(JSON.stringify({ etapes: sortie.length }));
