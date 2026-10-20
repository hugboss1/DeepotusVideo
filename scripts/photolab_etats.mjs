// photolab_etats.mjs — relevé COMPLET des états de l'écran du Photolab (t250, 20/10/2026) : chaque entrée de menu
// générée (actif / inactif / bientot), chaque outil (p2), chaque onglet de panneau amont, et l'ensemble
// TRAITES_PAR_ECRAN. Relit le code réel de l'écran (mod-menus.construireMenus, mod-outils, index.html), comme
// lister_bientot.mjs du skill parite-photolab, mais sans filtrer : c'est la base du banc de non-régression
// (backend/tests/test_photolab_non_regression.py) qui garde une montée de moteur de rien retirer à l'écran.
//
//   node scripts/photolab_etats.mjs <racine-du-depot> <registre-structuré.json> <sortie.json>
//
// <registre-structuré.json> : la forme de GET /api/photolab/commandes (chaque commande avec ses `champs`).
import fs from "node:fs";
import { pathToFileURL } from "node:url";

const [R, REG, OUT] = process.argv.slice(2);
if (!R || !REG || !OUT) { console.error("usage: node photolab_etats.mjs <racine> <registre.json> <sortie.json>"); process.exit(2); }
const M = await import(pathToFileURL(R + "/frontend/photolab/js/mod-menus.js").href);
const cat = JSON.parse(fs.readFileSync(R + "/frontend/photolab/donnees/menus.json", "utf8"));
const reg = JSON.parse(fs.readFileSync(REG, "utf8"));
const menus = M.construireMenus(cat, reg, M.REFUSES, "fr", (k) => k);

const entrees = {};
const walk = (l, chemin) => {
  for (const e of l) {
    if (e.type === "sous-menu") { walk(e.entrees, chemin + " › " + e.nom_affiche); continue; }
    if (e.type !== "commande") continue;
    // Un même id peut paraître deux fois (raccourci dans deux menus) : on garde le PIRE état vu, pour ne rien masquer.
    const rang = { actif: 2, inactif: 1, bientot: 0 };
    const prev = entrees[e.id];
    if (!prev || (rang[e.etat] ?? 0) < (rang[prev.etat] ?? 0)) entrees[e.id] = { etat: e.etat, chemin: chemin.slice(3) };
  }
};
for (const m of menus) walk(m.entrees, " › " + m.nom_affiche);

// Outils : le tableau de mod-outils est lu dans le SOURCE (le module touche au DOM à l'import).
const srcOutils = fs.readFileSync(R + "/frontend/photolab/js/mod-outils.js", "utf8");
const outils = {};
for (const m of srcOutils.matchAll(/\{\s*id:\s*"([A-Za-z]+)",\s*lettre:\s*"([A-Z]*)",\s*icone:\s*"([a-z0-9-]+)",\s*p2:\s*(true|false)\s*\}/g))
  outils[m[1]] = m[4] === "true";

// Panneaux : les onglets de photocraft (inventaire P0 §3) contre ceux que index.html déclare.
const AMONT = { color: "couleur", swatches: "nuancier", gradients: "degrades", patterns: "motifs", properties: "proprietes",
  adjustments: "ajustements", character: "caractere", paragraph: "paragraphe", navigator: "navigateur", histogram: "histogramme",
  info: "infos", history: "historique", actions: "actions", layerComps: "compositions", layers: "calques", channels: "couches", paths: "traces" };
const html = fs.readFileSync(R + "/frontend/photolab/index.html", "utf8");
const panneaux = {};
for (const [amont, nous] of Object.entries(AMONT))
  panneaux[amont] = new RegExp(`data-(panneau|onglet|onglet-pr|onglet-pi|onglet-co|onglet-in|onglet-tx)="${nous}"`).test(html);

const compte = { actif: 0, inactif: 0, bientot: 0 };
for (const e of Object.values(entrees)) compte[e.etat] = (compte[e.etat] || 0) + 1;
const sortie = { entrees, outils, panneaux, traites_par_ecran: [...M.TRAITES_PAR_ECRAN].sort(), compte };
fs.writeFileSync(OUT, JSON.stringify(sortie, null, 1) + "\n");
console.log(JSON.stringify({ entrees: Object.keys(entrees).length, ...compte, outils: Object.keys(outils).length,
  outils_actifs: Object.values(outils).filter(Boolean).length, panneaux_presents: Object.values(panneaux).filter(Boolean).length }));
