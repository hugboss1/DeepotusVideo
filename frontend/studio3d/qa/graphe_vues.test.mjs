// t344 — ce que montre chaque nœud du graphe Meshy (node, sans DOM). Run : node frontend/studio3d/qa/graphe_vues.test.mjs
import assert from "node:assert/strict";
import { resultatNoeud, tacheDe, glbDe, rendable } from "../graphe_vues_calc.js";

let ok = 0;
const t = (nom, f) => { f(); ok++; console.log("  ✓ " + nom); };
const N = (id, phase, extra) => ({ id, phase, ...(extra || {}) });

const journal = [
  { id: "t-rem", phase: "remesh", status: "SUCCEEDED", local_files: { glb: "/api/meshy3d/files/t-rem/model.glb", thumbnail: "/api/meshy3d/files/t-rem/preview.png" } },
  { id: "t-prev", phase: "preview", status: "SUCCEEDED", local_files: { fbx: "/x/model.fbx", obj: "/x/model.glb" }, thumbnail_url: "https://cdn/p.png" },
  { id: "t-old", phase: "preview", status: "SUCCEEDED", local_files: { glb: "/x/old.glb" } },
];

t("hors série : la dernière tâche réussie de la phase, au journal", () => {
  const S = { cfg: { prompt: "pieuvre" }, persisted: journal, run: null };
  const r = resultatNoeud(N("remesh", "remesh"), S);
  assert.deepEqual([r.etat, r.glb, r.img], ["pret", "/api/meshy3d/files/t-rem/model.glb", "/api/meshy3d/files/t-rem/preview.png"]);
  assert.equal(resultatNoeud(N("preview", "preview"), S).glb, "/x/model.glb");   // le premier .glb des fichiers
  assert.equal(resultatNoeud(N("rig", "rig"), S).etat, "attente");
});

t("en série : jamais le reliquat d'une autre série ; la tâche se lit par son taskId", () => {
  const S = { cfg: {}, persisted: journal, run: { phases: [{ id: "preview", status: "SUCCEEDED", taskId: "t-old" },
    { id: "remesh", status: "IN_PROGRESS" }, { id: "rig", status: "PENDING" }], outputs: {} } };
  assert.equal(resultatNoeud(N("preview", "preview"), S).glb, "/x/old.glb");
  const rm = resultatNoeud(N("remesh", "remesh"), S);
  assert.deepEqual([rm.etat, rm.glb, rm.img], ["en_cours", null, null]);
  assert.equal(tacheDe("rig", S), null);
});

t("en série, avant le rapatriement : ce que la série tient en mémoire (rig, animation, modèle)", () => {
  const S = { cfg: {}, persisted: [], run: { phases: [{ id: "rig", status: "SUCCEEDED", taskId: "r" },
    { id: "animate", status: "SUCCEEDED", taskId: "a" }, { id: "export", status: "SUCCEEDED" }],
    outputs: { rigged: { rigged_character_glb_url: "/m/rig.glb" }, animations: [{ animation_glb_url: "/m/a1.glb" },
      { animation_glb_url: "/m/a2.glb" }], modelUrls: { glb: "/m/model.glb" }, thumbnail: "https://cdn/t.png" } } };
  assert.equal(resultatNoeud(N("rig", "rig"), S).glb, "/m/rig.glb");
  assert.equal(resultatNoeud(N("animate", "animate"), S).glb, "/m/a2.glb");
  const ex = resultatNoeud(N("export", "export"), S);
  assert.deepEqual([ex.glb, ex.img], ["/m/model.glb", "https://cdn/t.png"]);
});

t("image-to-3d : le nœud texture montre la tâche du maillage (une seule passe)", () => {
  const S = { cfg: { source: "image" }, persisted: journal, run: null };
  assert.equal(resultatNoeud(N("texture", "texture"), S).glb, "/x/model.glb");
});

t("prompt, image de départ, Établi, sauté, échec", () => {
  const S = { cfg: { prompt: "  ", imageUrl: "/api/images/a.png" }, persisted: [], run: { phases: [
    { id: "rig", status: "SKIPPED" }, { id: "animate", status: "FAILED" }], outputs: {} } };
  assert.equal(resultatNoeud(N("prompt", "source"), S).etat, "attente");
  assert.equal(resultatNoeud(N("prompt", "source"), { ...S, cfg: { prompt: "pieuvre" } }).texte, "pieuvre");
  assert.equal(resultatNoeud(N("ref", "source"), S).img, "/api/images/a.png");
  assert.equal(resultatNoeud(N("etabli", "etabli", { door: true }), S, "/api/assets/3d/x/vignette?v=2").img, "/api/assets/3d/x/vignette?v=2");
  assert.equal(resultatNoeud(N("etabli", "etabli", { door: true }), S, null).etat, "attente");
  assert.equal(resultatNoeud(N("rig", "rig"), S).etat, "saute");
  assert.equal(resultatNoeud(N("animate", "animate"), S).etat, "echec");
});

t("un instantané : seulement d'un fichier de même origine", () => {
  assert.equal(rendable("/api/meshy3d/files/a/model.glb"), true);
  assert.equal(rendable("https://assets.meshy.ai/x.glb"), false);
  assert.equal(glbDe(null), null);
});

console.log(`\nOK — ${ok} tests (graphe_vues_calc)`);
