// t393 — le calcul de l'écran Texture (node, sans DOM). Run : node frontend/studio3d/qa/texture.test.mjs
import assert from "node:assert/strict";
import { VUES, PAS, ELEVATION_MAX, vue, normaliser, orbiter, direction, positionCamera, poseDepuis, vueDe, ECLAIRAGES,
  eclairage, RATIOS, ratioNombre, cadre, tailleCapture, RESOLUTIONS, modeleParDefaut, resolutionPermise, trierRail,
  referenceChoisie, usd } from "../ecrans/texture_calc.js";

let ok = 0;
const t = (nom, f) => { f(); ok++; console.log("  ✓ " + nom); };
const pres = (a, b, e = 1e-6) => Math.abs(a - b) < e;

t("la rosace a dix vues : six d'axe, quatre ¾, ids uniques", () => {
  assert.deepEqual(VUES.map((v) => v.id), ["face", "dos", "gauche", "droite", "dessus", "dessous",
    "avant_droite", "avant_gauche", "arriere_droite", "arriere_gauche"]);
  assert.equal(new Set(VUES.map((v) => v.id)).size, 10);
  assert.deepEqual(PAS, [15, 30, 45, 90]);
  assert.equal(vue("inconnue"), null);
});

t("chaque vue pointe du bon côté (y en haut, le modèle regarde +z)", () => {
  const d = (id) => direction(vue(id));
  assert.deepEqual(d("face"), { x: 0, y: 0, z: 1 });
  assert.deepEqual(d("dos"), { x: 0, y: 0, z: -1 });
  assert.deepEqual(d("droite"), { x: 1, y: 0, z: 0 });
  assert.deepEqual(d("gauche"), { x: -1, y: 0, z: 0 });
  assert.ok(d("dessus").y > 0.99 && d("dessous").y < -0.99);
  const ad = d("avant_droite");
  assert.ok(ad.x > 0 && ad.z > 0 && ad.y > 0 && pres(ad.x, ad.z));
  const ag = d("arriere_gauche");
  assert.ok(ag.x < 0 && ag.z < 0);
  for (const v of VUES) { const u = direction(v); assert.ok(pres(Math.hypot(u.x, u.y, u.z), 1), v.id); }
});

t("l'orbite tourne par le pas choisi, boucle l'azimut et borne l'élévation à ±89°", () => {
  assert.deepEqual(orbiter({ azimut: 0, elevation: 0 }, 1, 0, 15), { azimut: 15, elevation: 0 });
  assert.deepEqual(orbiter({ azimut: 0, elevation: 0 }, -1, 0, 90), { azimut: 270, elevation: 0 });
  assert.deepEqual(orbiter({ azimut: 350, elevation: 0 }, 1, 0, 30), { azimut: 20, elevation: 0 });
  assert.deepEqual(orbiter({ azimut: 0, elevation: 80 }, 0, 1, 45), { azimut: 0, elevation: ELEVATION_MAX });
  assert.deepEqual(orbiter({ azimut: 0, elevation: -80 }, 0, -1, 90), { azimut: 0, elevation: -ELEVATION_MAX });
  assert.deepEqual(orbiter({ azimut: 0, elevation: 0 }, 1, 0, 7), { azimut: 45, elevation: 0 }, "un pas inconnu retombe sur 45");
  // quatre crans de 90 reviennent au départ ; vingt-quatre de 15 aussi
  let p = { azimut: 0, elevation: 0 };
  for (let i = 0; i < 24; i++) p = orbiter(p, 1, 0, 15);
  assert.deepEqual(p, { azimut: 0, elevation: 0 });
});

t("position ↔ pose : aller-retour, et la vue nommée d'une pose", () => {
  const c = { x: 1, y: 2, z: 3 };
  for (const v of VUES) {
    const pos = positionCamera(c, 5, v);
    assert.ok(pres(Math.hypot(pos.x - c.x, pos.y - c.y, pos.z - c.z), 5));
    const p = poseDepuis(c, pos);
    assert.ok(pres(p.elevation, v.elevation, 1e-6), v.id);
    if (Math.abs(v.elevation) < ELEVATION_MAX) assert.ok(pres(p.azimut, v.azimut, 1e-6), v.id);
    assert.equal(vueDe(p), v.id);
  }
  assert.equal(vueDe({ azimut: 15, elevation: 0 }), null);
  assert.equal(vueDe({ azimut: 359.6, elevation: 0.3 }), "face");
  assert.deepEqual(normaliser({ azimut: -90, elevation: 120 }), { azimut: 270, elevation: ELEVATION_MAX });
});

t("les éclairages : sans lumière éteint tout, Bright et Ambient multiplient, mode inconnu → doux", () => {
  assert.deepEqual(ECLAIRAGES, ["sans", "plat", "doux", "trois", "vif"]);
  const s = eclairage("sans", 2, 2);
  assert.equal(s.sansLumiere, true);
  assert.deepEqual([s.hemi, s.cle, s.appoint, s.contre], [0, 0, 0, 0]);
  const p = eclairage("plat");
  assert.ok(p.hemi > 0 && p.cle === 0 && !p.sansLumiere, "plat : ambiance seule, aucune ombre");
  const t3 = eclairage("trois");
  assert.ok(t3.cle > t3.appoint && t3.contre > 0 && t3.hemi < t3.cle, "3 points : clé > appoint, un contre-jour");
  const d2 = eclairage("doux", 2, 0.5), d1 = eclairage("doux");
  assert.ok(pres(d2.cle, d1.cle * 2) && pres(d2.hemi, d1.hemi * 0.5));
  assert.equal(eclairage("inconnu").mode, "doux");
  assert.equal(eclairage("vif", 99).cle, eclairage("vif", 3).cle, "Bright borné à 3");
});

t("le cadre de capture garde le ratio, tient dans la vue et se centre", () => {
  assert.deepEqual(RATIOS, ["1:1", "16:9", "9:16", "4:3", "3:4"]);
  assert.ok(pres(ratioNombre("16:9"), 16 / 9) && ratioNombre("n'importe") === 1);
  for (const r of RATIOS) for (const [L, H] of [[800, 600], [600, 900], [1000, 300]]) {
    const c = cadre(r, L, H);
    assert.ok(c.x >= 0 && c.y >= 0 && c.x + c.w <= L && c.y + c.h <= H, `${r} ${L}×${H}`);
    assert.ok(Math.abs(c.w / c.h - ratioNombre(r)) < 0.02, `${r} ${L}×${H}`);
    assert.ok(Math.abs(c.x - (L - c.x - c.w)) <= 1 && Math.abs(c.y - (H - c.y - c.h)) <= 1);
  }
  const c = cadre("1:1", 800, 600, 0);
  assert.deepEqual(c, { x: 100, y: 0, w: 600, h: 600 });
  assert.deepEqual(tailleCapture("1:1"), { w: 1536, h: 1536 });
  assert.deepEqual(tailleCapture("16:9"), { w: 1536, h: 864 });
  assert.deepEqual(tailleCapture("9:16", 1024), { w: 576, h: 1024 });
});

t("le modèle par défaut et la résolution permise", () => {
  const l = [{ id: "nano-banana-pro", resolutions: ["1K", "2K", "4K"] }, { id: "nano-banana-2.1", resolutions: ["1K"] }];
  assert.equal(modeleParDefaut(l, "nano-banana-2.1"), "nano-banana-2.1");
  assert.equal(modeleParDefaut(l, "nano-banana-2"), "nano-banana-pro", "un défaut absent → le premier");
  assert.equal(modeleParDefaut([], "x"), null);
  assert.deepEqual(RESOLUTIONS, ["1K", "2K", "4K"]);
  assert.equal(resolutionPermise(l[0], "4K"), "4K");
  assert.equal(resolutionPermise(l[1], "4K"), "1K");
  assert.equal(resolutionPermise(null, "2K"), "1K");
});

t("le rail : du plus récent au plus ancien ; la référence choisie suit la demande puis la dernière générée", () => {
  const refs = [
    { id: "a", sorte: "generee", cree_le: "2026-10-31T10:00:00" },
    { id: "b", sorte: "style", cree_le: "2026-10-31T12:00:00" },
    { id: "c", sorte: "generee", cree_le: "2026-10-31T11:00:00" },
  ];
  assert.deepEqual(trierRail(refs).map((r) => r.id), ["b", "c", "a"]);
  assert.equal(referenceChoisie(refs, "a"), "a");
  assert.equal(referenceChoisie(refs, "disparue"), "c", "une planche de style n'est pas choisie d'office");
  assert.equal(referenceChoisie([{ id: "b", sorte: "style" }], null), null);
  assert.equal(referenceChoisie(refs, "b"), "b");
});

t("les montants en dollars, à la française ou à l'anglaise", () => {
  assert.equal(usd(0.15), "0,15 $");
  assert.equal(usd(0.035, "en"), "$0.035");
  assert.equal(usd(null), "—");
});

console.log(`\nOK — ${ok} tests (écran Texture)`);
