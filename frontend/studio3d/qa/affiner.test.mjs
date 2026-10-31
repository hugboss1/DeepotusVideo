// t396 + t405 — le calcul des poids de l'écran Affiner, la cinématique inverse de l'outil Pose et l'occlusion du
// lasso (node, sans DOM). Run : node frontend/studio3d/qa/affiner.test.mjs
import assert from "node:assert/strict";
import * as PC from "../ecrans/poids_calc.js";
import * as IK from "../ecrans/ik_calc.js";

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
  for (const p of Object.keys(PC.POSES)) assert.ok(Object.keys(PC.rotationsDePose(p, ["upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r", "thigh_l", "thigh_r", "calf_l", "calf_r", "neck_01", "spine_02"])).length, p);
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

/* ── t405 : la cinématique inverse des poignées ambre (ik_calc.js) ─────────── */

const procheV = (a, b, e = 1e-6) => a.forEach((x, k) => proche(x, b[k], e));

t("IK à deux os : une cible atteignable est atteinte, longueurs gardées, rotations cohérentes", () => {
  /* un bras en T, le coude légèrement plié vers l'arrière (−Z) */
  const a = [0.18, 1.47, 0], b = [0.48, 1.47, -0.03], c = [0.74, 1.47, 0];
  const l1 = IK.dist(a, b), l2 = IK.dist(b, c);
  for (const cible of [[0.55, 1.2, 0.1], [0.3, 1.0, 0.2], [0.6, 1.6, -0.1], [0.4, 1.47, 0.15]]) {
    const r = IK.deuxOs(a, b, c, cible, { naturel: [0, 0, -1] });
    assert.ok(r.atteint, `${cible}`);
    assert.ok(IK.dist(r.bout, cible) < 1e-3, `${cible} : ${IK.dist(r.bout, cible)}`);
    proche(IK.dist(a, r.milieu), l1, 1e-9);
    proche(IK.dist(r.milieu, r.bout), l2, 1e-9);
    /* les rotations rendues mènent les os là où le calcul les met (qBas s'applique APRÈS qHaut, dont il hérite) */
    procheV(IK.add(a, IK.qrot(r.qHaut, IK.sub(b, a))), r.milieu, 1e-9);
    const bas = IK.qrot(IK.qmul(r.qBas, r.qHaut), IK.sub(c, b));
    procheV(IK.add(r.milieu, bas), r.bout, 1e-9);
  }
});

t("IK à deux os : hors de portée, le membre se tend DROIT vers la cible", () => {
  const a = [0, 0, 0], b = [1, 0, -0.1], c = [2, 0, 0];
  const l = IK.dist(a, b) + IK.dist(b, c);
  const cible = [0, -5, 3];
  const r = IK.deuxOs(a, b, c, cible, { naturel: [0, 0, -1] });
  assert.equal(r.atteint, false);
  const dir = IK.norm(IK.sub(cible, a));
  procheV(r.bout, IK.mul(dir, l), 1e-9);
  /* le coude est SUR la droite épaule → cible (angle intérieur de 180°) */
  proche(IK.len(IK.cross(IK.sub(r.milieu, a), dir)), 0, 1e-9);
  assert.ok(IK.dot(IK.sub(r.milieu, a), dir) > 0);
});

t("IK à deux os : le pli garde son côté ; jamais de genou ni de coude retourné ; un pli minimal", () => {
  const cote = (r, a, ref) => IK.dot(IK.perp(IK.sub(r.milieu, a), IK.norm(IK.sub(r.bout, a))), ref);
  /* une jambe : hanche, genou plié vers l'AVANT (+Z), cheville ; on remonte le pied */
  const a = [0.1, 0.9, 0], b = [0.1, 0.5, 0.05], c = [0.1, 0.08, 0];
  for (const cible of [[0.1, 0.4, 0.1], [0.2, 0.3, -0.2], [0.0, 0.6, 0.3]]) {
    assert.ok(cote(IK.deuxOs(a, b, c, cible, { naturel: [0, 0, 1] }), a, [0, 0, 1]) > 0, `${cible}`);
    /* sans côté naturel, le pli courant décide aussi */
    assert.ok(cote(IK.deuxOs(a, b, c, cible), a, [0, 0, 1]) > 0, `${cible} sans naturel`);
  }
  /* un coude plié vers +Z sans côté naturel reste vers +Z (le pli courant) */
  const coude = IK.deuxOs([0, 0, 0], [1, 0, 0.2], [2, 0, 0], [1.2, -0.5, 0]);
  assert.ok(coude.milieu[2] > 0);
  /* un genou plié vers l'ARRIÈRE (genou retourné) ou tendu : le côté naturel (+Z) l'emporte */
  for (const bb of [[0.1, 0.5, -0.05], [0.1, 0.5, 0]]) {
    const r = IK.deuxOs(a, bb, c, [0.1, 0.4, 0.05], { naturel: [0, 0, 1] });
    assert.ok(cote(r, a, [0, 0, 1]) > 0, `${bb}`);
  }
  /* une cible sur la hanche : le membre se replie jusqu'au pli minimal, pas au-delà */
  const r = IK.deuxOs(a, b, c, [0.1, 0.88, 0], { naturel: [0, 0, 1] });
  const int = Math.acos(IK.dot(IK.norm(IK.sub(a, r.milieu)), IK.norm(IK.sub(r.bout, r.milieu)))) * 180 / Math.PI;
  assert.ok(int >= IK.PLI_MIN - 1e-6, `${int}`);
  proche(int, IK.PLI_MIN, 1e-6);
});

t("IK de la colonne (CCD) : la tête atteint une cible proche, chaque vertèbre reste dans sa borne", () => {
  /* bassin → 3 vertèbres → cou → tête, à la verticale */
  const pts = [[0, 1.05, 0], [0, 1.17, 0], [0, 1.3, 0], [0, 1.5, 0], [0, 1.58, 0]];
  const longs = pts.slice(1).map((p, i) => IK.dist(p, pts[i]));
  const cible = [0.12, 1.55, 0.05];
  const r = IK.ccd(pts, cible);
  assert.ok(r.atteint && IK.dist(r.points[4], cible) < 1e-3, `${r.distance}`);
  r.points.slice(1).forEach((p, i) => proche(IK.dist(p, r.points[i]), longs[i], 1e-9));
  procheV(r.points[0], pts[0], 1e-12);                                 // la racine ne bouge pas
  /* les rotations monde cumulées reproduisent les points ; Δ en chaîne recompose G */
  for (let i = 0; i < 4; i++) procheV(IK.add(r.points[i], IK.qrot(r.rotations[i], IK.sub(pts[i + 1], pts[i]))), r.points[i + 1], 1e-9);
  const D = IK.deltasEnChaine(r.rotations);
  let acc = [...IK.ID];
  D.forEach((d, i) => { acc = IK.qmul(d, acc); procheV(acc, r.rotations[i], 1e-9); });
  for (let i = 0; i < 4; i++) {
    const rel = IK.qmul(IK.qconj(i ? r.rotations[i - 1] : IK.ID), r.rotations[i]);
    assert.ok(IK.qangle(rel) <= (IK.LIMITE_COLONNE * Math.PI) / 180 + 1e-6, `${i}`);
  }
  /* une cible très loin : bornée, la tête s'en APPROCHE sans casser les bornes ni les longueurs */
  const loin = [2, 0.5, 0];
  const r2 = IK.ccd(pts, loin, { limites: 10 });
  assert.equal(r2.atteint, false);
  assert.ok(IK.dist(r2.points[4], loin) < IK.dist(pts[4], loin) - 0.05);
  for (let i = 0; i < 4; i++) {
    const rel = IK.qmul(IK.qconj(i ? r2.rotations[i - 1] : IK.ID), r2.rotations[i]);
    assert.ok(IK.qangle(rel) <= (10 * Math.PI) / 180 + 1e-6, `${i} : ${IK.qangle(rel)}`);
  }
});

t("les chaînes d'un squelette : mains et pieds (deux os au-dessus), tête par la colonne", () => {
  const os = [["pelvis", null], ["spine_01", "pelvis"], ["spine_02", "spine_01"], ["neck_01", "spine_02"], ["head", "neck_01"],
    ["clavicle_l", "spine_02"], ["upperarm_l", "clavicle_l"], ["lowerarm_l", "upperarm_l"], ["hand_l", "lowerarm_l"],
    ["thigh_r", "pelvis"], ["calf_r", "thigh_r"], ["foot_r", "calf_r"], ["ball_r", "foot_r"]].map(([nom, parent]) => ({ nom, parent }));
  const ch = IK.chaines(os, PC.role);
  assert.deepEqual(ch, [
    { poignee: "head", type: "colonne", os: ["spine_01", "spine_02", "neck_01", "head"], naturel: null },
    { poignee: "hand_l", type: "membre", os: ["upperarm_l", "lowerarm_l", "hand_l"], naturel: "arriere" },
    { poignee: "foot_r", type: "membre", os: ["thigh_r", "calf_r", "foot_r"], naturel: "avant" },
  ]);
  assert.deepEqual(IK.chaines([{ nom: "hand_l", parent: null }], PC.role), []);
});

/* ── t405 : le lasso ne prend que les sommets vus ─────────────────────────── */

t("le lasso caché : un plan devant en masque un autre ; « à travers le modèle » prend tout", () => {
  /* deux grilles 5 × 5 : la proche (profondeur 1) couvre x ∈ [90, 200] × y ∈ [90, 210], la lointaine (profondeur 3)
     x ∈ [100, 300] × y ∈ [100, 200] */
  const grille = (x0, larg, z, y0, haut) => {
    const n = 25, ecran = new Float32Array(n * 2), prof = new Float32Array(n).fill(z), index = [];
    for (let j = 0; j < 5; j++) for (let i = 0; i < 5; i++) { ecran[(j * 5 + i) * 2] = x0 + (larg * i) / 4; ecran[(j * 5 + i) * 2 + 1] = y0 + (haut * j) / 4; }
    for (let j = 0; j < 4; j++) for (let i = 0; i < 4; i++) { const v = j * 5 + i; index.push(v, v + 1, v + 6, v, v + 6, v + 5); }
    return { ecran, prof, index, n };
  };
  const pres = grille(90, 110, 1, 90, 120), loin = grille(100, 200, 3, 100, 100);
  const poly = [[80, 80], [310, 80], [310, 220], [80, 220]];
  const { selections, ms } = PC.lassoMaillages([pres, loin], poly, 400, 300, { eps: 0.05 });
  assert.equal(selections[0].length, 25);                             // la grille proche : entière
  /* la lointaine : seulement ses colonnes x ≥ 200 (x = 200 tombe sur le bord de la proche : un pixel de silhouette
     est toléré, un sommet n'y est jamais caché par sa propre bordure) */
  const xs = selections[1].map((v) => loin.ecran[v * 2]);
  assert.ok(xs.every((x) => x >= 200), `${xs}`);
  assert.deepEqual([...new Set(xs)].sort((p, q) => p - q), [200, 250, 300]);
  assert.equal(selections[1].length, 15);
  assert.ok(ms >= 0);
  const tous = PC.lassoMaillages([pres, loin], poly, 400, 300, { travers: true });
  assert.deepEqual(tous.selections.map((x) => x.length), [25, 25]);
  /* un sommet derrière la caméra n'est jamais vu ; un triangle à cheval n'écrit rien */
  const tb = PC.tamponProfondeur(10, 10);
  PC.rasteriser(tb, new Float32Array([0, 0, 9, 0, 0, 9]), new Float32Array([1, -1, 1]), null, 3);
  assert.ok(tb.z.every((x) => x === Infinity));
  assert.deepEqual([...PC.visibles(tb, new Float32Array([2, 2]), new Float32Array([-1]), 1, 0.1)], [0]);
  /* la boîte du lasso, bornée au canevas */
  assert.deepEqual(PC.boitePolygone([[5, 5], [50, 8], [20, 70]], 40, 60), [3, 3, 39, 59]);
});

t("le lasso caché sur 50 000 sommets : la face arrière d'une sphère n'est jamais prise, et c'est rapide", () => {
  /* une sphère de rayon 1 (250 × 200 sommets = 50 000), centrée à 4 unités devant une caméra perspective */
  const NL = 250, NA = 200, n = NL * NA, W = 1000, H = 800, f = 700;
  const ecran = new Float32Array(n * 2), prof = new Float32Array(n), devant = new Uint8Array(n), index = [];
  for (let j = 0; j < NA; j++) {
    const th = (Math.PI * (j + 0.5)) / NA;
    for (let i = 0; i < NL; i++) {
      const ph = (2 * Math.PI * i) / NL, v = j * NL + i;
      const x = Math.sin(th) * Math.cos(ph), y = Math.cos(th), z = Math.sin(th) * Math.sin(ph);
      const d = 4 - z;                       // la caméra en z = 4 regarde vers −z : profondeur 4 − z
      prof[v] = d; ecran[v * 2] = W / 2 + (f * x) / d; ecran[v * 2 + 1] = H / 2 - (f * y) / d;
      devant[v] = z > 0.3 ? 1 : 0;           // nettement tourné vers la caméra
    }
  }
  for (let j = 0; j < NA - 1; j++) for (let i = 0; i < NL; i++) {
    const a = j * NL + i, b = j * NL + ((i + 1) % NL), c = a + NL, d = b + NL;
    index.push(a, c, b, b, c, d);
  }
  const maillage = { ecran, prof, index: Uint32Array.from(index), n };
  const poly = [[350, 250], [650, 250], [650, 550], [350, 550]];
  PC.lassoMaillages([maillage], poly, W, H, { eps: 0.02 });            // chauffe
  const mesures = [];
  let sel = null;
  for (let k = 0; k < 5; k++) { const r = PC.lassoMaillages([maillage], poly, W, H, { eps: 0.02 }); mesures.push(r.ms); sel = r.selections[0]; }
  const travers = PC.lassoMaillages([maillage], poly, W, H, { travers: true }).selections[0];
  const ms = mesures.sort((p, q) => p - q)[2];
  console.log(`    (50 000 sommets, ${index.length / 3} triangles : lasso caché ${ms.toFixed(1)} ms médian, `
    + `${sel.length} sommets vus / ${travers.length} entourés)`);
  /* aucun sommet de l'arrière (z < 0) ; tous les sommets nettement de face, dans le lasso, sont pris */
  for (const v of sel) assert.ok(prof[v] < 4, `${v}`);
  const attendus = travers.filter((v) => devant[v]);
  const pris = new Set(sel);
  assert.ok(attendus.every((v) => pris.has(v)), "un sommet de face manque");
  assert.ok(travers.length > 1.8 * sel.length, `${travers.length} / ${sel.length}`);
  assert.ok(ms < 400, `${ms} ms`);
});

console.log(`\nOK — ${ok} tests (poids, IK et lasso de l'écran Affiner)`);
