// t398 + t399 — le calcul de l'écran Animer du 3D Studio (node, sans DOM). Run : node frontend/studio3d/qa/animer.test.mjs
import assert from "node:assert/strict";
import { listeGeneres, choisirMarche, cleCategorie, cleSous, pagesVisibles, requeteCatalogue, VUES, vueCamera, miroir,
  curseurVersTemps, tempsVersCurseur, horloge, actionDeTouche, pasConduite, bornerDuree, prix, blocageTexte, lienEtabli,
  ORIGINES } from "../ecrans/animer_calc.js";

let ok = 0;
const t = (nom, f) => { f(); ok++; console.log("  ✓ " + nom); };
const proche = (a, b, e = 1e-9) => assert.ok(Math.abs(a - b) < e, `${a} ≠ ${b}`);

t("Générés : clips de la version jouables, clips Meshy jouables par leur GLB, mouvements rangés à appliquer", () => {
  const etat = {
    clips: [{ nom: "prudent", canaux: 60 }, { nom: "prudent", canaux: 60 }],
    sources: [
      { type: "fichier", nom: "prudent.bvh", origine: "meshy-motion", secondes: 3 },
      { type: "fichier", nom: "danse.glb", origine: "uthana" },
      { type: "fichier", nom: "x.bvh", origine: "bizarre" },
      { type: "meshy", nom: "walking", origine: "meshy" },
    ],
  };
  const l = listeGeneres(etat, "j 1");
  assert.deepEqual(l.map((c) => c.cle), ["clip:prudent", "fichier:prudent.bvh", "fichier:danse.glb", "fichier:x.bvh", "meshy:walking"]);
  assert.deepEqual(l.map((c) => c.jouable), [true, false, false, false, true]);
  assert.equal(l[3].origine, "import");                         // origine inconnue → import
  assert.equal(l[4].url, "/api/assets/3d/j%201/animation/walking");
  assert.equal(l[1].secondes, 3);
  assert.deepEqual(listeGeneres(null, "j"), []);
  assert.ok(ORIGINES.includes("meshy-motion"));
});

t("la marche du mode conduite : walk, sinon run, sinon le premier jouable", () => {
  assert.equal(choisirMarche([{ nom: "idle" }, { nom: "Running" }, { nom: "Walking_Woman" }]).nom, "Walking_Woman");
  assert.equal(choisirMarche([{ nom: "idle" }, { nom: "action_12_run" }]).nom, "action_12_run");
  assert.equal(choisirMarche([{ nom: "walk", jouable: false }, { nom: "saut" }]).nom, "saut");
  assert.equal(choisirMarche([]), null);
});

t("catalogue : clés de catégorie, pagination compacte, requête", () => {
  assert.equal(cleCategorie("WalkAndRun"), "anim.cat_walkandrun");
  assert.equal(cleSous("HangingfromLedge"), "anim.sous_hangingfromledge");
  assert.deepEqual(pagesVisibles(1, 5), [1, 2, 3, 4, 5]);
  assert.deepEqual(pagesVisibles(1, 14), [1, 2, 3, 4, 5, null, 14]);
  assert.deepEqual(pagesVisibles(7, 14), [1, null, 6, 7, 8, null, 14]);
  assert.deepEqual(pagesVisibles(14, 14), [1, null, 10, 11, 12, 13, 14]);
  assert.deepEqual(pagesVisibles(99, 0), [1]);
  for (let n = 1; n < 30; n++) for (let p = 1; p <= n; p++) {
    const v = pagesVisibles(p, n);
    assert.ok(v.length <= 7 && v.includes(p) && v[0] === 1 && v[v.length - 1] === n, `${p}/${n} ${v}`);
  }
  assert.equal(requeteCatalogue({ q: "  walk ", categorie: "WalkAndRun", sous: "Walking", page: 2 }),
    "/api/studio3d/animer/catalogue?q=walk&categorie=WalkAndRun&sous_categorie=Walking&page=2&par_page=40");
  assert.equal(requeteCatalogue({ vue: "favoris", sous: "Walking" }), "/api/studio3d/animer/catalogue?vue=favoris&page=1&par_page=40");
  assert.equal(requeteCatalogue({ vue: "collection", collection: "abc" }),
    "/api/studio3d/animer/catalogue?vue=collection&collection=abc&page=1&par_page=40");
});

t("vues P/F/B/L/R/T : orientation du viewer + miroir", () => {
  assert.deepEqual(VUES, ["P", "F", "B", "L", "R", "T"]);
  assert.deepEqual(vueCamera("F"), { orientation: "face", miroir: false });
  assert.deepEqual(vueCamera("B"), { orientation: "face", miroir: true });
  assert.deepEqual(vueCamera("L"), { orientation: "profil", miroir: false });
  assert.deepEqual(vueCamera("R"), { orientation: "profil", miroir: true });
  assert.deepEqual(vueCamera("T"), { orientation: "dessus", miroir: false });
  assert.deepEqual(vueCamera("?"), { orientation: "libre", miroir: false });
  assert.deepEqual(miroir({ x: 3, y: 1, z: 0 }, { x: 1, y: 0, z: 0 }), { x: -1, y: 1, z: 0 });
});

t("lecteur : curseur ↔ temps, horloge dans les deux langues", () => {
  proche(curseurVersTemps(500, 3), 1.5);
  proche(curseurVersTemps(2000, 3), 3);
  proche(curseurVersTemps(-5, 3), 0);
  assert.equal(curseurVersTemps(500, 0), 0);
  assert.equal(tempsVersCurseur(1.5, 3), 500);
  assert.equal(tempsVersCurseur(9, 3), 1000);
  assert.equal(horloge(1.25, 3, "fr"), "1,25 s / 3,00 s");
  assert.equal(horloge(1.25, 3, "en"), "1.25 s / 3.00 s");
});

t("conduite : ZQSD sur AZERTY = WASD sur QWERTY (touches physiques), flèches", () => {
  assert.equal(actionDeTouche("KeyW"), "avant");
  assert.equal(actionDeTouche("KeyA"), "gauche");
  assert.equal(actionDeTouche("KeyS"), "arriere");
  assert.equal(actionDeTouche("KeyD"), "droite");
  assert.equal(actionDeTouche("ArrowLeft"), "gauche");
  assert.equal(actionDeTouche("KeyQ"), null);                    // la touche Q du QWERTY n'est pas une commande
});

t("conduite : avancer suit le cap, tourner ne déplace pas, reculer est plus lent, dt borné", () => {
  let e = pasConduite({ x: 0, z: 0, cap: 0 }, new Set(["avant"]), 1 / 10);
  proche(e.x, 0); proche(e.z, 0.14); assert.ok(e.bouge);
  e = pasConduite({ x: 0, z: 0, cap: Math.PI / 2 }, ["avant"], 0.1);
  proche(e.x, 0.14); proche(e.z, 0, 1e-12);
  e = pasConduite({ x: 0, z: 0, cap: 0 }, ["gauche"], 0.1);
  proche(e.x, 0); proche(e.z, 0); assert.ok(e.cap > 0 && e.bouge && e.avance === 0);
  e = pasConduite({ x: 0, z: 0, cap: 0 }, ["droite"], 0.1);
  assert.ok(e.cap < 0);
  e = pasConduite({ x: 0, z: 0, cap: 0 }, ["arriere"], 0.1);
  proche(e.z, -0.07);
  e = pasConduite({ x: 0, z: 0, cap: 0 }, ["avant", "arriere"], 0.1);
  assert.equal(e.bouge, false);
  e = pasConduite({ x: 0, z: 0, cap: 0 }, ["avant"], 5);         // un onglet en veille ne téléporte pas
  proche(e.z, 0.14);
  e = pasConduite({ x: 0, z: 0, cap: 0 }, ["avant"], 0.1, 0.85); // un personnage deux fois plus petit marche moins vite
  proche(e.z, 0.07);
  assert.equal(pasConduite(null, [], 0.1).bouge, false);
});

t("texte → mouvement : durée au pas de 0,5 dans [2, 10], prix lisible, blocages dans l'ordre", () => {
  assert.equal(bornerDuree(2.3), 2.5);
  assert.equal(bornerDuree(2.2), 2);
  assert.equal(bornerDuree(0), 2);
  assert.equal(bornerDuree(99), 10);
  assert.equal(bornerDuree("x"), 2);
  assert.equal(prix({ credits: { meshy: 3 }, total_usd: 0.06 }, "fr"), "anim.prix");   // sans dzT : la clé
  assert.equal(prix(null), "");
  const f = { job: "j", rig: { rigge: true } };
  assert.equal(blocageTexte({ fiche: null }), "anim.bloc_modele");
  assert.equal(blocageTexte({ fiche: { job: "j", rig: { rigge: false } }, meshy: true, prompt: "a", mode: "swift" }), "anim.bloc_rig");
  assert.equal(blocageTexte({ fiche: f, meshy: false, prompt: "a", mode: "swift" }), "anim.bloc_cle");
  assert.equal(blocageTexte({ fiche: f, meshy: true, prompt: "a", mode: "prime" }), "anim.bloc_mode");
  assert.equal(blocageTexte({ fiche: f, meshy: true, prompt: "  ", mode: "swift" }), "anim.bloc_prompt");
  assert.equal(blocageTexte({ fiche: f, meshy: true, prompt: "x".repeat(401), mode: "swift" }), "anim.bloc_long");
  assert.equal(blocageTexte({ fiche: f, meshy: true, prompt: "a", mode: "swift", occupe: true }), "anim.bloc_occupe");
  assert.equal(blocageTexte({ fiche: f, meshy: true, prompt: "saute", mode: "swift" }), null);
  assert.equal(lienEtabli("a b", 3), "/etabli/?job=a%20b&version=3");
});

console.log(`\nOK — ${ok} tests (écran Animer)`);
