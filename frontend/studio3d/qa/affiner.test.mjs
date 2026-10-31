// t396 — le calcul des poids de l'écran Affiner (node, sans DOM). Run : node frontend/studio3d/qa/affiner.test.mjs
import assert from "node:assert/strict";
import * as PC from "../ecrans/poids_calc.js";

let ok = 0;
const t = (nom, f) => { f(); ok++; console.log("  ✓ " + nom); };
const proche = (a, b, e = 1e-5) => assert.ok(Math.abs(a - b) < e, `${a} ≠ ${b}`);
const sommeOk = (P) => { for (let v = 0; v < P.n; v++) proche(PC.somme(P, v), 1); };

/* une bande de 2 × 6 sommets le long de X, symétrique autour de x = 0 (aucun sommet sur l'axe) ; os : 0 tronc,
   1 bras_l, 2 bras_r ; poids : tronc au centre, bras vers les bouts */
const XS = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5];
const N = 12;
const POS = new Float32Array(N * 3);
XS.forEach((x, i) => { POS.set([x, 0, 0], i * 3); POS.set([x, 1, 0], (i + 6) * 3); });
const INDEX = [];
/* une topologie symétrique elle aussi : les diagonales des quads se reflètent ; le quad du milieu en éventail */
for (let i = 0; i < 5; i++) {
  if (i < 2) INDEX.push(i, i + 1, i + 6, i + 1, i + 7, i + 6);
  else if (i > 2) INDEX.push(i, i + 1, i + 7, i, i + 7, i + 6);
  else INDEX.push(2, 3, 8, 2, 8, 9, 2, 9, 3, 3, 9, 8);
}
const NOMS = ["spine_03", "upperarm_l", "upperarm_r"];
function bande() {
  const j = new Uint16Array(N * 4), w = new Float32Array(N * 4);
  for (let v = 0; v < N; v++) {
    const x = POS[v * 3];
    const bras = x > 0 ? 1 : 2, a = Math.min(1, Math.abs(x) / 2.5);
    j.set([bras, 0, 0, 0], v * 4);
    w.set([a, 1 - a, 0, 0], v * 4);
  }
  return PC.creerPoids(j, w, N);
}
const MIROIR = PC.carteMiroir(POS, N, 0);
const OSM = PC.osMiroir(NOMS);
const symetrique = (P) => {
  for (let v = 0; v < N; v++) {
    const m = MIROIR[v];
    for (const os of [0, 1, 2]) proche(PC.poidsDe(P, v, os), PC.poidsDe(P, m, OSM[os]), 1e-6);
  }
};

t("lire, normaliser, écrire : quatre influences triées, somme 1, jamais vide", () => {
  assert.deepEqual(PC.normaliser({ 3: 2, 1: 2 }), { 1: 0.5, 3: 0.5 });
  const n5 = PC.normaliser({ 0: 0.4, 1: 0.3, 2: 0.2, 3: 0.05, 4: 0.05 });
  assert.deepEqual(Object.keys(n5).map(Number).sort(), [0, 1, 2]);   // égalité à la coupe : les deux partent
  proche(Object.values(n5).reduce((a, b) => a + b), 1);
  const P = PC.creerPoids([0, 0, 0, 0], [0, 0, 0, 0], 1);
  assert.equal(PC.ecrire(P, 0, {}), false);
  assert.equal(PC.ecrire(P, 0, { 5: 1, 2: 3 }), true);
  assert.deepEqual([...P.j], [2, 5, 0, 0]);
  assert.deepEqual([...P.w], [0.75, 0.25, 0, 0]);
  assert.deepEqual(PC.lire(P, 0), { 2: 0.75, 5: 0.25 });
});

t("fixer garde les proportions des autres os et passe le reste au repli", () => {
  const o = PC.fixer({ 0: 0.5, 1: 0.3, 2: 0.2 }, 0, 0.8);
  proche(o[0], 0.8); proche(o[1], 0.12); proche(o[2], 0.08);
  assert.deepEqual(PC.fixer({ 4: 1 }, 4, 0.3, 7), { 4: 0.3, 7: 0.7 });
  assert.deepEqual(PC.fixer({ 4: 1 }, 4, 0.3), { 4: 1 });              // sans repli : l'os garde tout
  assert.deepEqual(PC.fixer({ 4: 1 }, 6, 1), { 6: 1 });
});

t("l'atténuation : linéaire, douce, constante, nulle hors du rayon", () => {
  proche(PC.attenuation(0, "lineaire"), 1); proche(PC.attenuation(0.5, "lineaire"), 0.5);
  proche(PC.attenuation(0.5, "douce"), 0.5); proche(PC.attenuation(0.25, "douce"), 1 - 0.15625);
  assert.equal(PC.attenuation(0.9, "constante"), 1);
  assert.equal(PC.attenuation(1.01, "constante"), 0);
  const r = PC.dansRayon(POS, N, [2.25, 0, 0], 0.8, "lineaire");
  assert.deepEqual(r.map(([v]) => v), [4, 5]);
  proche(r[1][1], 1 - 0.25 / 0.8); proche(r[0][1], 1 - 0.75 / 0.8);
});

t("les cinq opérations : fixer, ajouter, retirer, lisser, flouter", () => {
  const o = { 0: 0.6, 1: 0.4 };
  proche(PC.operer(o, "fixer", 1, 0.9, 1)[1], 0.9);
  proche(PC.operer(o, "fixer", 1, 0.9, 0.5)[1], 0.65);
  proche(PC.operer(o, "ajouter", 1, 0.2, 1)[1], 0.6);
  proche(PC.operer(o, "retirer", 1, 0.2, 0.5)[1], 0.3);
  proche(PC.operer(o, "lisser", 1, 1, 1, { 1: 0.8, 0: 0.2 })[1], 0.8);
  const fl = PC.operer(o, "flouter", 1, 0.5, 1, { 2: 1 });
  proche(fl[2], 0.5); proche(fl[0], 0.3);
  assert.equal(PC.operer(o, "lisser", 1, 1, 1, null), o);
});

t("soudure et adjacence : une couture d'UV est un seul sommet", () => {
  const pos = new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0]);   // le sommet 3 double le 1
  const canon = PC.souder(pos, 5);
  assert.deepEqual([...canon], [0, 1, 2, 1, 4]);
  const adj = PC.adjacence([0, 1, 2, 3, 4, 2], 5, canon);
  assert.deepEqual([...PC.voisins(adj, 3)].sort(), [0, 2, 4]);
  assert.deepEqual([...PC.voisins(adj, 0)].sort(), [1, 2]);
});

t("le miroir des sommets et des os", () => {
  assert.deepEqual([...MIROIR], [5, 4, 3, 2, 1, 0, 11, 10, 9, 8, 7, 6]);
  assert.deepEqual([...OSM], [0, 2, 1]);
  assert.equal(PC.nomMiroir("thigh_l"), "thigh_r");
  assert.equal(PC.nomMiroir("Hand.R"), "Hand.L");
  assert.equal(PC.nomMiroir("mixamorig:LeftForeArm"), "mixamorig:RightForeArm");
  assert.equal(PC.nomMiroir("right_foot"), "left_foot");
  assert.equal(PC.nomMiroir("spine_02"), "spine_02");
  const decale = PC.carteMiroir(new Float32Array([1, 0, 0, 3, 0, 0, 7, 0, 0]), 3, 2);
  assert.deepEqual([...decale], [1, 0, -1]);
  // un modèle presque symétrique : le plus proche du reflet, à la tolérance près
  const presque = PC.carteMiroir(new Float32Array([1, 0, 0, -1.02, 0.01, 0, -0.97, 0, 0, 5, 0, 0]), 4, 0, 0.05);
  assert.deepEqual([...presque], [1, 0, 0, -1]);
  // l'échelle du maillage : la bande a des arêtes de 1 (horizontales, verticales) et de √2 (diagonales)
  const am = PC.areteMoyenne(POS, PC.adjacence(INDEX, N, PC.souder(POS, N)));
  assert.ok(am > 1 && am < Math.SQRT2, am);
});

t("peindre en miroir garde une peau symétrique symétrique, pour chaque opération", () => {
  const adj = PC.adjacence(INDEX, N, PC.souder(POS, N));
  for (const mode of PC.MODES) {
    const P = bande();
    symetrique(P);
    const touches = PC.dansRayon(POS, N, [1.5, 0.5, 0], 1.3, "douce");
    assert.ok(touches.length >= 2);
    PC.appliquer(P, touches, { mode, os: 1, force: 0.6, repli: 0, adj, miroir: MIROIR, osM: OSM });
    sommeOk(P);
    symetrique(P);
    // un coup À CHEVAL sur l'axe : chaque sommet reçoit son geste ET le reflet de celui de son miroir (autre force)
    const cheval = PC.dansRayon(POS, N, [0.3, 0.5, 0], 1.6, "lineaire");
    assert.ok(cheval.some(([v]) => POS[v * 3] < 0) && cheval.some(([v]) => POS[v * 3] > 0));
    PC.appliquer(P, cheval, { mode, os: 1, force: 0.6, repli: 0, adj, miroir: MIROIR, osM: OSM });
    sommeOk(P);
    symetrique(P);
  }
  // un sommet SUR l'axe (son propre miroir) reçoit les deux os à parts égales, quel que soit l'ordre
  for (const mode of ["fixer", "ajouter", "retirer"]) {
    const Q = PC.creerPoids([0, 1, 2, 0], [0.6, 0.2, 0.2, 0], 1);
    PC.appliquer(Q, [[0, 0.7]], { mode, os: 1, force: 0.5, repli: 0, miroir: Int32Array.from([0]), osM: OSM });
    proche(PC.poidsDe(Q, 0, 1), PC.poidsDe(Q, 0, 2), 1e-6);
    sommeOk(Q);
  }
  // sans miroir, l'autre côté ne bouge pas
  const P = bande();
  const avant = PC.poidsDe(P, 1, 2);
  PC.appliquer(P, PC.dansRayon(POS, N, [1.5, 0, 0], 0.6), { mode: "ajouter", os: 1, force: 0.5 });
  assert.equal(PC.poidsDe(P, 1, 2), avant);
  assert.ok(PC.poidsDe(P, 4, 1) > 0.6);
});

t("retirer l'os qui tient tout donne le reste au repli ; l'isolement protège hors du domaine", () => {
  const P = bande();
  PC.appliquer(P, [[5, 1]], { mode: "retirer", os: 1, force: 1, repli: 0 });
  proche(PC.poidsDe(P, 5, 0), 1);
  sommeOk(P);
  const Q = bande();
  const verrou = PC.horsDomaine(Q, 1);
  assert.ok(verrou.has(0) && !verrou.has(5));
  const faits = PC.appliquer(Q, [[0, 1], [5, 1]], { mode: "fixer", os: 1, force: 0.3, verrou });
  assert.deepEqual(faits, [5]);
  proche(PC.poidsDe(Q, 0, 1), 0);
});

t("annuler et rétablir un trait, et la pile qui se tronque", () => {
  const P = bande();
  const h = new PC.Historique();
  const ref = [P.j.slice(), P.w.slice()];
  const tr = PC.debutTrait();
  PC.appliquer(P, PC.dansRayon(POS, N, [0.5, 0, 0], 1.2), { mode: "fixer", os: 1, force: 1, repli: 0 }, tr);
  const apres = [P.j.slice(), P.w.slice()];
  const d = PC.finTrait(tr, P);
  assert.ok(d.sommets.length >= 2);
  h.pousser(d);
  assert.ok(h.peutAnnuler && !h.peutRetablir);
  const rendus = h.annuler(P);
  assert.deepEqual(rendus, [...d.sommets]);
  assert.deepEqual([P.j.slice(), P.w.slice()], ref);
  h.retablir(P);
  assert.deepEqual([P.j.slice(), P.w.slice()], apres);
  h.annuler(P);
  h.pousser(PC.finTrait(PC.debutTrait(), P));      // un trait vide ne compte pas
  assert.ok(h.peutRetablir);
  const tr2 = PC.debutTrait();
  PC.appliquer(P, [[0, 1]], { mode: "ajouter", os: 2, force: 0.1 }, tr2);
  h.pousser(PC.finTrait(tr2, P));
  assert.ok(!h.peutRetablir && h.pos === 1);
  // un trait sur deux maillages : une seule entrée, rendue maillage par maillage
  const Q = bande(), R = bande();
  const t1 = PC.debutTrait(), t2 = PC.debutTrait();
  PC.appliquer(Q, [[0, 1]], { mode: "fixer", os: 1, force: 1, repli: 0 }, t1);
  PC.appliquer(R, [[1, 1]], { mode: "fixer", os: 1, force: 1, repli: 0 }, t2);
  const h2 = new PC.Historique();
  h2.pousser({ parts: [{ cle: "q", d: PC.finTrait(t1, Q) }, { cle: "r", d: PC.finTrait(t2, R) }] });
  h2.pousser({ parts: [] });
  assert.equal(h2.pile.length, 1);
  const rendus2 = h2.annuler((c) => (c === "q" ? Q : R));
  assert.deepEqual(rendus2, [{ cle: "q", sommets: [0] }, { cle: "r", sommets: [1] }]);
  assert.deepEqual([Q.j.slice(), Q.w.slice(), R.j.slice(), R.w.slice()], [bande().j, bande().w, bande().j, bande().w]);
});

t("le lasso, les sommets sans poids, les couleurs", () => {
  const ecran = new Float32Array(N * 2);
  for (let v = 0; v < N; v++) { ecran[v * 2] = POS[v * 3] * 100 + 300; ecran[v * 2 + 1] = 200 - POS[v * 3 + 1] * 100; }
  const poly = [[320, 80], [470, 80], [470, 220], [320, 220]];
  assert.deepEqual(PC.selectionLasso(ecran, N, poly), [3, 4, 9, 10]);
  const vis = new Uint8Array(N).fill(1); vis[9] = 0;
  assert.deepEqual(PC.selectionLasso(ecran, N, poly, vis), [3, 4, 10]);
  assert.deepEqual(PC.selectionLasso(ecran, N, poly.slice(0, 2)), []);
  const P = bande();
  P.w.fill(0, 4 * 4, 4 * 4 + 4);
  assert.deepEqual(PC.sansPoids(P), [4]);
  const c = PC.couleurs(P, 1);
  assert.deepEqual([...c.slice(12, 15)], [1, 0, 1]);                 // magenta : sans poids
  assert.deepEqual(PC.chaleur(0).map((x) => Math.round(x * 100)), [5, 8, 32]);
  assert.deepEqual(PC.chaleur(1).map((x) => Math.round(x * 100)), [92, 12, 10]);
  const iso = PC.couleurs(P, 1, { isoler: true });
  assert.deepEqual([...iso.slice(0, 3)].map((x) => Math.round(x * 100)), [16, 16, 18]);
});

t("le clavier de Sorceress et les réglages à la molette", () => {
  assert.deepEqual(PC.action({ key: "2" }), { outil: "peindre" });
  assert.deepEqual(PC.action({ key: "P" }), { outil: "pose" });
  assert.deepEqual(PC.action({ key: "d" }), { mode: "lisser" });
  assert.deepEqual(PC.action({ key: "m" }), { bascule: "miroir" });
  assert.deepEqual(PC.action({ key: "]" }), { taille: 1 });
  assert.deepEqual(PC.action({ key: "z", ctrlKey: true }), { histoire: "annuler" });
  assert.deepEqual(PC.action({ key: "z", ctrlKey: true, shiftKey: true }), { histoire: "retablir" });
  assert.deepEqual(PC.action({ key: "y", ctrlKey: true }), { histoire: "retablir" });
  assert.equal(PC.action({ key: "2", altKey: true }), null);
  assert.equal(PC.action({ key: "s", ctrlKey: true }), null);
  for (const m of PC.MODES) assert.ok(Object.values(PC.TOUCHES).some((x) => x.mode === m), m);
  for (const o of PC.OUTILS) assert.ok(Object.values(PC.TOUCHES).some((x) => x.outil === o), o);
  proche(PC.ajusterTaille(0.1, 1), 0.115);
  proche(PC.ajusterTaille(0.1, -1), 0.1 / 1.15);
  proche(PC.ajusterTaille(10, 1, 1.8), 3.6);
  assert.equal(PC.ajusterForce(0.15, 1), 0.2);
  assert.equal(PC.ajusterForce(0.02, -1), 0.01);
  assert.equal(PC.ajusterForce(0.98, 1), 1);
});

t("les rôles et les poses d'essai, des deux côtés en miroir", () => {
  assert.equal(PC.role("upperarm_l"), "bras_g");
  assert.equal(PC.role("mixamorig:RightForeArm"), "avantbras_d");
  assert.equal(PC.role("thigh_r"), "cuisse_d");
  assert.equal(PC.role("calf_l"), "jambe_g");
  assert.equal(PC.role("spine_02"), "colonne");
  assert.equal(PC.role("neck_01"), "cou");
  assert.equal(PC.role("head"), "tete");
  assert.equal(PC.role("breast_l"), null);
  const r = PC.rotationsDePose("bras_leves", ["upperarm_l", "upperarm_r", "lowerarm_l"]);
  assert.deepEqual(r, { upperarm_l: [0, 0, -60], upperarm_r: [0, 0, 60] });
  assert.deepEqual(PC.rotationsDePose("inconnue", ["upperarm_l"]), {});
  for (const p of Object.keys(PC.POSES)) assert.ok(Object.keys(PC.rotationsDePose(p, ["upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r", "thigh_l", "thigh_r", "calf_l", "calf_r", "neck_01"])).length, p);
});

t("le quaternion relatif au repos", () => {
  const s = Math.SQRT1_2;
  const q = PC.quatRelatif([0, 0, s, s], [0, 0, s, s]);
  q.forEach((x, k) => proche(x, [0, 0, 0, 1][k]));
  const r = PC.quatRelatif([0, 0, 0, 1], [s, 0, 0, s]);
  r.forEach((x, k) => proche(x, [s, 0, 0, s][k]));
  // repos à 90° autour de Z, posé à 180° autour de Z : la différence est 90° autour de Z
  const d = PC.quatRelatif([0, 0, s, s], [0, 0, 1, 0]);
  d.forEach((x, k) => proche(x, [0, 0, s, s][k]));
});

t("les corps de requête : seuls les sommets touchés, triés", () => {
  const P = bande();
  const c = PC.corpsEnregistrer(3, [{ mesh: 0, primitive: 1, P, sales: new Set([5, 0]) }, { mesh: 1, primitive: 0, P, sales: new Set() }]);
  assert.equal(c.version, 3);
  assert.equal(c.modifs.length, 1);
  assert.deepEqual(c.modifs[0].sommets, [0, 5]);
  assert.equal(c.modifs[0].joints.length, 8);
  assert.deepEqual(c.modifs[0].joints.slice(4), [1, 0, 0, 0]);
  proche(c.modifs[0].poids[4], 1);
  assert.deepEqual(PC.corpsCorriger(2, "confinement", { os: "upperarm_l", parametres: { force: 0.7 } }),
    { version: 2, operation: "confinement", os: "upperarm_l", parametres: { force: 0.7 } });
  assert.deepEqual(PC.corpsCorriger(2, "tout"), { version: 2, operation: "tout", parametres: {} });
  assert.deepEqual(PC.resumeRapport({ correction: "orphelins", ilots: 3 }), { cle: "aff.rap_orphelins", v: { n: 3 } });
  assert.deepEqual(PC.resumeRapport({ correction: "guerison", guerison: [{ avant: 10, apres: 4 }, { avant: 2, apres: 2 }] }),
    { cle: "aff.rap_guerison", v: { a: 12, b: 6, p: 2 } });
  assert.deepEqual(PC.OPERATIONS, ["orphelins", "confinement", "epaules", "coutures", "guerison", "tout"]);
});

console.log(`\nOK — ${ok} tests (poids de l'écran Affiner)`);
