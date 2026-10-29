// t344 — banc du calcul de l'écran « Comparer les moteurs » (node, sans DOM). Run : node frontend/studio3d/qa/comparer.test.mjs
import assert from "node:assert/strict";
import { trier, meilleur, cellule, totalCoches, avisCle, grouperParImage, usd, duree, taille } from "../comparer_calc.js";

let ok = 0;
const t = (nom, f) => { f(); ok++; console.log("  ✓ " + nom); };

const L = [
  { moteur: "tripo", label: "Tripo v2.5", statut: "termine", tris: 30000, aretes_bord: 0, octets: 2097152, duree_s: 41, usd_estime: 0.3, usd_reel: null },
  { moteur: "trellis", label: "Trellis", statut: "termine", tris: 12000, aretes_bord: 18, octets: 500000, duree_s: 95, usd_estime: 0.35, usd_reel: 0.33 },
  { moteur: "hunyuan", label: "Hunyuan3D v2", statut: "echec", tris: null, aretes_bord: null, octets: null, duree_s: null, usd_estime: 0.48, usd_reel: null },
];

t("trier : croissant, décroissant, l'inconnu toujours en dernier", () => {
  assert.deepEqual(trier(L, "tris").map((l) => l.moteur), ["trellis", "tripo", "hunyuan"]);
  assert.deepEqual(trier(L, "tris", true).map((l) => l.moteur), ["tripo", "trellis", "hunyuan"]);
  assert.deepEqual(trier(L, "moteur").map((l) => l.moteur), ["hunyuan", "trellis", "tripo"]);
  assert.deepEqual(trier(L, "usd_reel", true).map((l) => l.moteur), ["trellis", "tripo", "hunyuan"]);
});

t("meilleur : parmi les terminés, null quand rien ne départage", () => {
  assert.equal(meilleur(L, "tris"), 12000);
  assert.equal(meilleur(L, "aretes_bord"), 0);
  assert.equal(meilleur(L, "moteur"), null);
  assert.equal(meilleur([L[0], L[2]], "tris"), null);
  assert.equal(meilleur([L[0], { ...L[0], moteur: "x" }], "tris"), null);
});

t("cellules : tailles, durées, coûts ; le réel inconnu le dit", () => {
  assert.equal(cellule(L[0], "octets"), "2.0 unite.mo");
  assert.equal(taille(500000), "488 unite.ko");
  assert.equal(duree(95), "1 min 35 s");
  assert.equal(usd(0.3), "0,30 $");
  assert.equal(cellule(L[0], "usd_reel"), "reel.non_rapproche");
  assert.equal(cellule(L[2], "tris"), "—");
});

t("le total vient du devis du serveur, pour les seuls moteurs cochés", () => {
  const d = { lignes: [{ moteur: "tripo", usd: 0.3 }, { moteur: "trellis", usd: 0.35 }, { moteur: "triposr", usd: 0.07 }] };
  assert.equal(totalCoches(d, ["tripo", "triposr"]), 0.37);
  assert.equal(totalCoches(d, []), 0);
});

t("un moteur sans clé reste choisissable : seul un avis le dit", () => {
  assert.equal(avisCle({ cle: "fal", cle_ok: false }), "cle.fal");
  assert.equal(avisCle({ cle: "local", cle_ok: false }), "cle.local");
  assert.equal(avisCle({ cle: "fal", cle_ok: true }), "");
});

t("les modèles existants se regroupent par image, les groupes les plus fournis d'abord", () => {
  const g = grouperParImage([{ job: "a", image_filename: "x.png" }, { job: "b", image_filename: "y.png" },
    { job: "c", image_filename: "y.png" }, { job: "d", image_filename: null }]);
  assert.deepEqual(g.map(([k, v]) => [k, v.length]), [["y.png", 2], ["", 1], ["x.png", 1]]);
});

console.log(`\nOK — ${ok} tests (comparer_calc)`);
