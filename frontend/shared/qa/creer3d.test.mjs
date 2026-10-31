// t389 — le calcul de l'écran Créer (onglet 3D), sous node. Run : node frontend/shared/qa/creer3d.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
// script classique de la SPA : joué dans un bac à sable qui offre `module` — il y rend son CALCUL sans toucher au DOM
const bac = { module: { exports: {} } };
vm.runInNewContext(readFileSync(new URL("../dz-creer3d.js", import.meta.url), "utf8"), bac);
const C = bac.module.exports;
// le bac à sable a ses propres prototypes : comparer des copies JSON
const eq = (a, b) => assert.deepEqual(JSON.parse(JSON.stringify(a)), b);

let ok = 0;
const t = (nom, f) => { f(); ok++; console.log("  ✓ " + nom); };

const E = [
  { id: "tripo", label: "Tripo v2.5" }, { id: "tripo-p2", label: "Tripo P2", neuf: true, texte: true, fournisseur: "Tripo" },
  { id: "trellis-2", label: "TRELLIS 2", neuf: true, fournisseur: "Microsoft" }, { id: "meshy-7.1", label: "Meshy 7.1", neuf: true, texte: true, fournisseur: "Meshy" },
  { id: "hunyuan-local", label: "Hunyuan local", local: true }, { id: "inconnu", label: "X" },
];

t("les modèles rangés par fournisseur dans l'ordre de Sorceress, les neufs d'abord", () => {
  const g = C.groupes(E);
  eq(g.map((x) => x.fournisseur), ["Meshy", "Tripo", "Hunyuan", "Microsoft", "Autres"]);
  eq(g[1].moteurs.map((m) => m.id), ["tripo-p2", "tripo"]);
});

t("en mode texte, seuls les modèles qui savent générer depuis un texte restent cochables", () => {
  assert.equal(C.cochable(E[0], "texte"), false);
  assert.equal(C.cochable(E[1], "texte"), true);
  assert.equal(C.cochable(E[0], "image"), true);
});

t("le corps : réglages des seuls modèles cochés, sans valeur vide ; une image en mode image", () => {
  const b = C.corps({ mode: "image", moteurs: ["tripo-p2"], images: ["a.png", "b.png"], quantite: 2,
    reglages: { "tripo-p2": { quad: true, face_limit: null }, "trellis-2": { resolution: 512 } }, pose: "a-pose" });
  eq(b, { mode: "image", moteurs: ["tripo-p2"], quantite: 2, reglages: { "tripo-p2": { quad: true } },
    pose: "a-pose", textures: true, images: ["a.png"] });
  const tx = C.corps({ mode: "texte", moteurs: ["meshy-7.1"], prompt: "  un chevalier ", images: ["a.png"] });
  assert.equal(tx.prompt, "un chevalier");
  assert.equal(tx.images, undefined);
  eq(C.corps({ mode: "multi", moteurs: ["tripo"], images: ["a", "b", "c"] }).images, ["a", "b", "c"]);
});

t("une saisie convertie au type du schéma ; vide = défaut du modèle", () => {
  assert.equal(C.valeur({ type: "int" }, "1200"), 1200);
  assert.equal(C.valeur({ type: "int" }, ""), null);
  assert.equal(C.valeur({ type: "enum", valeurs: [512, 1024] }, "1024"), 1024);
  assert.equal(C.valeur({ type: "enum", valeurs: ["a"] }, "z"), null);
  assert.equal(C.valeur({ type: "bool" }, 1), true);
});

t("galerie : filtres et recherche ; relais vers le 3D Studio ; prix", () => {
  const M = [{ job: "a", nom: "Sorcière", rig: { rigge: true } }, { job: "b", nom: "Caisse", moteur: "trellis-2" }];
  eq(C.filtrer(M, "rigges").map((m) => m.job), ["a"]);
  eq(C.filtrer(M, "non_rigges").map((m) => m.job), ["b"]);
  eq(C.filtrer(M, "tous", "TRELLIS").map((m) => m.job), ["b"]);
  eq(JSON.parse(C.relais("j1", "rig", 42)), { job: "j1", ecran: "rig", t: 42 });
  assert.equal(C.usd(1.1), "$1.10");
});

console.log(`\nOK — ${ok} tests (Créer 3D)`);
