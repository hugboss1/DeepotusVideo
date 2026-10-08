// qa/outils/courbes.mjs — outil du banc backend/tests/test_photolab_formulaires.py, section [4] (pas un *.test.mjs :
// run.mjs ne le lance pas). Rejoue des éditions types de Courbes et de Niveaux avec les fonctions PURES de
// mod-courbes.js et rend les paramètres que l'écran enverrait, pour que le banc les passe à la liste blanche du pont.
// usage : node courbes.mjs <sortie .json>  ->  [{nom, command, params}]
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const js = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "js");
const K = await import(pathToFileURL(join(js, "mod-courbes.js")));

const sortie = [];
const pousser = (nom, sorte, params) => {
  sortie.push({ nom, command: K.COMMANDES[sorte], params });
  // Le même jeu sert au calque de réglage (B5 : création, puis modification complète).
  sortie.push({ nom: nom + " (calque)", command: "layer.newAdjustmentLayer." + (sorte === "courbes" ? "curves" : "levels"), params });
};

// Courbes : une courbe en S à 5 points (clics + glisser, coordonnées flottantes comme au pointeur)
let p = K.IDENTITE.map((q) => q.slice());
for (const [x, y] of [[63.7, 40.2], [128.4, 128.9], [191.2, 219.6]]) p = K.ajouterPoint(p, x, y).points;
p = K.deplacerPoint(p, 0, 999, 12.4);                       // extrémité : x figé
const s5 = { ...K.etatNeutre("courbes"), rvb: p };
pousser("courbe à 5 points", "courbes", K.paramsCourbes(s5));
// Canal bleu seul
pousser("canal bleu seul", "courbes", K.paramsCourbes({ ...K.etatNeutre("courbes"), bleu: K.ajouterPoint(K.IDENTITE, 120, 170).points }));
// 19 points (le maximum), sur tous les canaux
let plein = K.IDENTITE.map((q) => q.slice());
for (let x = 9; plein.length < K.MAX_POINTS; x += 13) plein = K.ajouterPoint(plein, x, 255 - x).points;
pousser("19 points sur les 4 canaux", "courbes", K.paramsCourbes({ rvb: plein, rouge: plein, vert: plein, bleu: plein }));
// Gestes au hasard (graine fixe) : ajouts, déplacements hors bornes, retraits
let r = K.IDENTITE.map((q) => q.slice()), g = 11;
const alea = () => { g = (g * 1103515245 + 12345) % 2147483648; return g / 2147483648; };
for (let k = 0; k < 500; k++) {
  const t = alea(), x = alea() * 400 - 70, y = alea() * 400 - 70, i = Math.floor(alea() * r.length);
  const n = t < 0.45 ? (K.ajouterPoint(r, x, y) || {}).points : t < 0.85 ? K.deplacerPoint(r, i, x, y) : K.retirerPoint(r, i);
  if (n) r = n;
}
pousser("500 gestes au hasard (rouge)", "courbes", K.paramsCourbes({ ...K.etatNeutre("courbes"), rouge: r }));
pousser("courbes complètes (calque, canaux neutres compris)", "courbes", K.paramsCourbes(s5, { complet: true }));

// Niveaux : bornés, saisies hostiles, curseur gris aux extrêmes
const n1 = { ...K.etatNeutre("niveaux"), rvb: K.normaliserNiveaux({ inBlack: 300, inWhite: -9, gamma: 1e9, outBlack: -5, outWhite: 1e9 }) };
pousser("niveaux bornés (saisies hostiles)", "niveaux", K.paramsNiveaux(n1));
const n2 = { ...K.etatNeutre("niveaux"), rvb: { inBlack: 20, inWhite: 230, gamma: K.gammaDepuisCurseur(25, 20, 230) },
  vert: { outBlack: 30, outWhite: 220, gamma: K.gammaDepuisCurseur(9999, 0, 255) } };
pousser("niveaux composite + vert (curseur gris aux extrêmes)", "niveaux", K.paramsNiveaux(n2));
pousser("niveaux complets (calque)", "niveaux", K.paramsNiveaux(n2, { complet: true }));

writeFileSync(process.argv[2], JSON.stringify(sortie));
console.log(JSON.stringify({ editions: sortie.length }));
