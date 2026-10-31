// t395 — le calcul de l'écran Rig (node, sans DOM). Run : node frontend/studio3d/qa/rig.test.mjs
import assert from "node:assert/strict";
import * as RC from "../ecrans/rig_calc.js";

let ok = 0;
const t = (nom, f) => { f(); ok++; console.log("  ✓ " + nom); };

/* un squelette symétrique autour de x = 0,1 (un modèle pas centré sur l'origine) */
const AXE = 0.1;
const J = {};
for (const id of RC.ordre(true)) {
  const c = RC.cote(id);
  const k = RC.ordre(true).indexOf(id);
  const x = c === "l" ? AXE + 0.1 + k / 100 : c === "r" ? null : AXE;
  J[id] = [x, 1 + k / 10, 0.02 * k];
}
for (const id of RC.ordre(true)) if (RC.cote(id) === "r") J[id] = RC.miroirX(J[RC.paire(id)], AXE);

t("22 os SMPL, 24 avec la poitrine ; parenté et côtés", () => {
  assert.equal(RC.ordre().length, 22);
  assert.equal(RC.ordre(true).length, 24);
  assert.equal(new Set(RC.ordre(true)).size, 24);
  assert.equal(RC.parentDe("pelvis"), null);
  assert.equal(RC.parentDe("hand_l"), "lowerarm_l");
  assert.equal(RC.parentDe("breast_r"), "spine_03");
  for (const id of RC.ordre(true)) if (id !== "pelvis") assert.ok(RC.ordre(true).includes(RC.parentDe(id)), id);
  assert.equal(RC.paire("thigh_l"), "thigh_r");
  assert.equal(RC.paire("spine_02"), null);
  assert.equal(RC.profondeur("pelvis"), 0);
  assert.equal(RC.profondeur("hand_l"), 7);
  assert.deepEqual(RC.enfants("spine_03"), ["neck_01", "clavicle_l", "clavicle_r"]);
  assert.deepEqual(RC.enfants("spine_03", true), ["neck_01", "clavicle_l", "clavicle_r", "breast_l", "breast_r"]);
  assert.deepEqual(RC.descendants("upperarm_l"), ["lowerarm_l", "hand_l"]);
  assert.equal(RC.descendants("pelvis").length, 21);
});

t("déplacer : seul, puis avec les enfants ; l'original reste intact", () => {
  const avant = JSON.stringify(J);
  const a = RC.deplacer(J, ["upperarm_l"], [0, 0.5, 0]);
  assert.deepEqual(a.upperarm_l, [J.upperarm_l[0], J.upperarm_l[1] + 0.5, J.upperarm_l[2]]);
  assert.deepEqual(a.lowerarm_l, J.lowerarm_l);
  const b = RC.deplacer(J, ["upperarm_l"], [0, 0.5, 0], { avecEnfants: true });
  assert.equal(b.hand_l[1], J.hand_l[1] + 0.5);
  assert.equal(b.lowerarm_l[1], J.lowerarm_l[1] + 0.5);
  assert.deepEqual(b.clavicle_l, J.clavicle_l);
  assert.equal(JSON.stringify(J), avant);
});

t("miroir : le geste gauche recopié à droite autour de l'axe ; un os du milieu reste sur l'axe", () => {
  const a = RC.deplacer(J, ["lowerarm_l"], [0.2, -0.1, 0.05], { miroir: true, axe: AXE });
  assert.deepEqual(a.lowerarm_r, RC.miroirX(a.lowerarm_l, AXE));
  assert.ok(Math.abs((a.lowerarm_l[0] + a.lowerarm_r[0]) / 2 - AXE) < 1e-12);
  const sansMiroir = RC.deplacer(J, ["lowerarm_l"], [0.2, -0.1, 0.05], { miroir: false, axe: AXE });
  assert.deepEqual(sansMiroir.lowerarm_r, J.lowerarm_r);
  const m = RC.deplacer(J, ["spine_02"], [0.3, 0.1, 0], { miroir: true, axe: AXE });
  assert.equal(m.spine_02[0], AXE);
  assert.equal(m.spine_02[1], J.spine_02[1] + 0.1);
  // miroir + enfants : toute la jambe droite suit la gauche
  const e = RC.deplacer(J, ["thigh_l"], [0.05, 0, 0], { miroir: true, avecEnfants: true, axe: AXE });
  for (const id of ["thigh", "calf", "foot", "ball"]) assert.deepEqual(e[id + "_r"], RC.miroirX(e[id + "_l"], AXE), id);
  // les deux côtés sélectionnés : chacun garde son propre geste (pas d'écrasement par le miroir)
  const d = RC.deplacer(J, ["hand_l", "hand_r"], [0, 1, 0], { miroir: true, axe: AXE });
  assert.equal(d.hand_l[1], J.hand_l[1] + 1);
  assert.equal(d.hand_r[1], J.hand_r[1] + 1);
});

t("poser une coordonnée = un geste ; sélection Maj+clic ; Échap = sélection vide", () => {
  const p = RC.poser(J, "head", [AXE, 9, 0.5], { miroir: true, axe: AXE });
  assert.deepEqual(p.head, [AXE, 9, 0.5]);
  assert.deepEqual(RC.selectionner([], "head", false), ["head"]);
  assert.deepEqual(RC.selectionner(["head"], "hand_l", false), ["hand_l"]);
  assert.deepEqual(RC.selectionner(["head"], "hand_l", true), ["head", "hand_l"]);
  assert.deepEqual(RC.selectionner(["head", "hand_l"], "head", true), ["hand_l"]);
  assert.deepEqual(RC.selectionner(["head"], null, false), ["head"]);
});

t("segments, référence décalée, axe auto, pas de l'axe", () => {
  assert.equal(RC.segmentsOs(J).length, 21);
  assert.equal(RC.segmentsOs(J, true).length, 23);
  const s = RC.segmentsOs(J).find((x) => x[2] === "hand_l");
  assert.deepEqual([s[0], s[1]], [J.lowerarm_l, J.hand_l]);
  const r = RC.decaler(J, 0.7);
  assert.equal(r.head[0], J.head[0] + 0.7);
  assert.equal(RC.decalageReference(70, 2), 1.4);
  assert.ok(Math.abs(RC.axeAuto(J) - AXE) < 1e-12);
  assert.equal(RC.axeAuto({}, { min: [-1, 0, 0], max: [3, 1, 1] }), 1);
  assert.equal(RC.pasAxe(1.8, 5), 0.045);
  assert.equal(RC.pasAxe(1.8, -1), -0.009);
});

t("corps de requête : 22 os (24 avec poitrine), manquants, différences", () => {
  const c = RC.corps(J, { version: 3 });
  assert.equal(Object.keys(c.joints).length, 22);
  assert.equal(c.version, 3);
  assert.equal(c.poitrine, false);
  assert.equal(Object.keys(RC.corps(J, { avecPoitrine: true }).joints).length, 24);
  assert.deepEqual(RC.manquants(J), []);
  const trou = { ...J, head: [0, NaN, 0] };
  delete trou.ball_r;
  assert.deepEqual(RC.manquants(trou), ["head", "ball_r"]);
  assert.equal(RC.differe(J, JSON.parse(JSON.stringify(J))), false);
  assert.equal(RC.differe(J, RC.deplacer(J, ["head"], [0, 1e-3, 0])), true);
  assert.equal(RC.differe(J, RC.deplacer(J, ["breast_l"], [0, 1, 0])), false);    // poitrine non comptée
  assert.equal(RC.differe(J, RC.deplacer(J, ["breast_l"], [0, 1, 0]), true), true);
});

t("auto-rig IA : chaque porte du devis a sa raison", () => {
  const d = { meshy: true, fal: true, approuve: true, texture: true };
  assert.equal(RC.refusIA(d), "");
  assert.equal(RC.refusIA(null), "rigx.ia_refus_devis");
  assert.equal(RC.refusIA({ ...d, meshy: false }), "rigx.ia_refus_meshy");
  assert.equal(RC.refusIA({ ...d, fal: false }), "rigx.ia_refus_fal");
  assert.equal(RC.refusIA({ ...d, approuve: false }), "rigx.ia_refus_approuve");
  assert.equal(RC.refusIA({ ...d, texture: false }), "rigx.ia_refus_texture");
  assert.equal(RC.decimales(1.8), 3);
  assert.equal(RC.decimales(0.018), 5);
  assert.equal(RC.decimales(180), 3);
});

console.log(`\nOK — ${ok} tests (écran Rig)`);
