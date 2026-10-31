// t394 — la texture auto (dispositions) et la projection multi-vues (node, sans DOM).
// Run : node frontend/studio3d/qa/projection.test.mjs
import assert from "node:assert/strict";
import { DISPOSITIONS, poses, prixImage, devisDisposition, ELEVATION_MAX } from "../ecrans/texture_calc.js";
import { regarder, perspective, multiplier, matriceCamera, projeterPoint, cameraDePose, sphereDe, tailleAtlas,
  rasteriserUV, carteProfondeur, poche, nouvelAccumulateur, accumulerVue, finaliser, nouvelEtat, poids, echantillon,
  gommer, estomper, combler, trous, coutures, soigner, deborder, nouvellePile, memoriser, annuler, retablir,
  unionRect, rectPinceau, couleurVue, composer, rectTout } from "../ecrans/projection_calc.js";

let ok = 0;
const t = (nom, f) => { f(); ok++; console.log("  ✓ " + nom); };
const pres = (a, b, e = 1e-6) => Math.abs(a - b) < e;

/* ── les dispositions ─────────────────────────────────────────────────────── */
t("sept dispositions, chacune avec son nombre de vues", () => {
  assert.deepEqual(DISPOSITIONS, [4, 6, 8, 10, 12, 16, 18]);
  for (const n of DISPOSITIONS) assert.equal(poses(n).length, n, String(n));
  assert.deepEqual(poses(5), []);
});

t("4 vues : les quatre côtés ; 6 et 10 ajoutent les deux pôles", () => {
  assert.deepEqual(poses(4).map((p) => p.azimut), [0, 90, 180, 270]);
  for (const n of [6, 10]) {
    const el = poses(n).map((p) => p.elevation);
    assert.ok(el.includes(ELEVATION_MAX) && el.includes(-ELEVATION_MAX), String(n));
  }
  assert.ok(!poses(8).some((p) => Math.abs(p.elevation) === ELEVATION_MAX), "8 = un anneau, sans pôle");
});

t("16 vues : un anneau au pas de 22,5°", () => {
  const a = poses(16).map((p) => p.azimut);
  a.forEach((v, i) => assert.ok(pres(v, i * 22.5), `${i} : ${v}`));
});

t("12 détail : quatre côtés puis les moitiés haute et basse zoomées", () => {
  const p = poses(12);
  assert.deepEqual(p.slice(0, 4).map((x) => [x.zoom, x.decalage]), [[1, 0], [1, 0], [1, 0], [1, 0]]);
  assert.ok(p.slice(4, 8).every((x) => x.zoom === 2 && x.decalage > 0));
  assert.ok(p.slice(8).every((x) => x.zoom === 2 && x.decalage < 0));
});

t("18 sphère complète : anneau, plongée, contre-plongée, pôles", () => {
  const p = poses(18);
  assert.equal(p.filter((x) => x.elevation === 0).length, 8);
  assert.equal(p.filter((x) => x.elevation === 45).length, 4);
  assert.equal(p.filter((x) => x.elevation === -45).length, 4);
  assert.equal(p.filter((x) => Math.abs(x.elevation) === ELEVATION_MAX).length, 2);
  // toutes les poses sont distinctes
  assert.equal(new Set(p.map((x) => `${x.azimut}/${x.elevation}`)).size, 18);
});

t("le devis vaut N × le prix d'une image (4K double là où le modèle le prend)", () => {
  const pro = { usd: 0.15, resolutions: ["1K", "2K", "4K"] }, simple = { usd: 0.039, resolutions: ["1K"] };
  assert.equal(prixImage(pro, "4K"), 0.3);
  assert.equal(prixImage(simple, "4K"), 0.039);
  assert.deepEqual(devisDisposition(8, pro, "1K"), { vues: 8, usd: 1.2 });
  assert.deepEqual(devisDisposition(18, pro, "4K"), { vues: 18, usd: 5.4 });
  assert.deepEqual(devisDisposition(4, simple, "2K"), { vues: 4, usd: 0.156 });
  assert.equal(devisDisposition(7, pro, "1K"), null);
  assert.equal(devisDisposition(4, null, "1K"), null);
});

/* ── matrices ─────────────────────────────────────────────────────────────── */
t("la caméra en +z qui regarde l'origine : l'origine au centre, w = la distance", () => {
  const M = matriceCamera({ oeil: [0, 0, 5], cible: [0, 0, 0], fov: 30, aspect: 1, pres: 0.1, loin: 100 });
  const o = projeterPoint(M, 0, 0, 0);
  assert.ok(pres(o.u, 0.5) && pres(o.v, 0.5) && pres(o.w, 5), JSON.stringify(o));
  const d = projeterPoint(M, 1, 0, 0), h = projeterPoint(M, 0, 1, 0);
  assert.ok(d.u > 0.5 && pres(d.v, 0.5), "+x à droite");
  assert.ok(h.v < 0.5 && pres(h.u, 0.5), "+y en haut de l'image");
  assert.equal(projeterPoint(M, 0, 0, 6).devant, false, "derrière la caméra");
  // le bord du champ vertical tombe au bord de l'image
  const bord = projeterPoint(M, 0, 5 * Math.tan((15 * Math.PI) / 180), 0);
  assert.ok(pres(bord.v, 0, 1e-9), String(bord.v));
});

t("regarder × perspective = matriceCamera ; l'identité ne change rien", () => {
  const I = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  const V = regarder([1, 2, 3], [0, 0, 0]), P = perspective(40, 1.5, 0.5, 50);
  assert.deepEqual(multiplier(I, V), V);
  assert.deepEqual(multiplier(P, V), matriceCamera({ oeil: [1, 2, 3], cible: [0, 0, 0], fov: 40, aspect: 1.5, pres: 0.5, loin: 50 }));
});

t("la caméra d'une pose cadre la sphère entière (zoom 1) et le centre au milieu", () => {
  const sph = { centre: [1, 2, 3], rayon: 2 };
  for (const p of poses(18)) {
    const c = cameraDePose(p, sph);
    const o = projeterPoint(c.M, 1, 2, 3);
    assert.ok(pres(o.u, 0.5, 1e-6) && pres(o.v, 0.5, 1e-6), JSON.stringify(p));
    for (const [dx, dy, dz] of [[2, 0, 0], [-2, 0, 0], [0, 2, 0], [0, -2, 0], [0, 0, 2], [0, 0, -2]]) {
      const q = projeterPoint(c.M, 1 + dx, 2 + dy, 3 + dz);
      assert.ok(q.devant && q.u > 0 && q.u < 1 && q.v > 0 && q.v < 1, JSON.stringify([p, dx, dy, dz, q]));
    }
  }
  const haut = cameraDePose({ azimut: 0, elevation: 0, zoom: 2, decalage: 0.5 }, sph);
  assert.deepEqual(haut.cible, [1, 3, 3]);
  assert.deepEqual(sphereDe([0, 0, 0, 2, 4, 4]), { centre: [1, 2, 2], rayon: 3 });
});

t("la taille de l'atlas suit la texture d'origine, bornée, 2048 sans texture", () => {
  assert.deepEqual(tailleAtlas(1024, 1024), { W: 1024, H: 1024 });
  assert.deepEqual(tailleAtlas(8192, 8192), { W: 4096, H: 4096 });
  assert.deepEqual(tailleAtlas(64, 128), { W: 512, H: 512 });
  assert.deepEqual(tailleAtlas(0, 0), { W: 2048, H: 2048 });
});

/* ── un quad synthétique ──────────────────────────────────────────────────── */
// le plan z = 0, de (-1,-1) à (1,1), normale +z ; UV : u suit x, v DESCEND quand y monte (convention glTF)
const quad = (z = 0, nz = 1) => ({
  positions: Float32Array.from([-1, -1, z, 1, -1, z, 1, 1, z, -1, 1, z]),
  normales: Float32Array.from([0, 0, nz, 0, 0, nz, 0, 0, nz, 0, 0, nz]),
  uvs: Float32Array.from([0, 1, 1, 1, 1, 0, 0, 0]),
  indices: Uint32Array.from([0, 1, 2, 0, 2, 3]),
});
// une image 2×2 : moitié gauche rouge, droite bleue (le haut et le bas pareils) ; et la même en 16×16
const image2 = { width: 2, height: 2, data: Uint8ClampedArray.from([255, 0, 0, 255, 0, 0, 255, 255, 255, 0, 0, 255, 0, 0, 255, 255]) };
const image16 = { width: 16, height: 16, data: Uint8ClampedArray.from({ length: 1024 }, (_, i) => {
  const x = (i >> 2) % 16, q = i % 4;
  return q === 3 ? 255 : (x < 8 ? [255, 0, 0] : [0, 0, 255])[q];
}) };
const vueDe = (maillage, oeil, image, pw = 64) => {
  const M = matriceCamera({ oeil, cible: [0, 0, 0], fov: 60, aspect: 1, pres: 0.1, loin: 100 });
  return { M, oeil, image, pw, ph: pw, profondeur: carteProfondeur(maillage, M, pw, pw) };
};
const fond = (W, H, v = 10) => new Uint8ClampedArray(W * H * 4).fill(v);

t("rastériser le quad couvre tout l'atlas, positions et normales interpolées", () => {
  const A = rasteriserUV(quad(), 8, 8);
  assert.equal(A.n, 64);
  assert.ok(A.masque.every((m) => m === 1));
  // le texel (0, 0) : u ≈ 1/16, v ≈ 1/16 → x ≈ -1 + 2/16, y ≈ +1 - 2/16 (v monte vers le bas)
  const j = Array.from(A.texels).indexOf(0);
  assert.ok(pres(A.pos[3 * j], -0.875, 1e-5) && pres(A.pos[3 * j + 1], 0.875, 1e-5) && pres(A.pos[3 * j + 2], 0, 1e-6));
  assert.deepEqual(Array.from(A.nrm.slice(3 * j, 3 * j + 3)), [0, 0, 1]);
  // un triangle seul couvre la moitié (plus la marge conservatrice)
  const demi = rasteriserUV({ ...quad(), indices: Uint32Array.from([0, 1, 2]) }, 8, 8, 0);
  assert.ok(demi.n >= 28 && demi.n <= 36, String(demi.n));
});

t("un texel face à la caméra prend le pixel de la caméra ; un texel de dos ne prend rien", () => {
  const W = 8, H = 8, m = quad();
  const A = rasteriserUV(m, W, H);
  const E = nouvelEtat(W, H, fond(W, H), A.masque);
  const acc = nouvelAccumulateur(A);
  const vus = accumulerVue(A, vueDe(m, [0, 0, 3], image16), acc, 0);
  assert.equal(vus, 64);
  assert.equal(finaliser(A, acc, E), 64);
  const px = (x, y) => Array.from(E.couleur.slice(4 * (y * W + x), 4 * (y * W + x) + 3));
  assert.deepEqual(px(1, 4), [255, 0, 0], "u = 0,19 : le rouge de gauche");
  assert.deepEqual(px(6, 4), [0, 0, 255], "u = 0,81 : le bleu de droite");
  assert.equal(E.peint[0], 1);
  assert.equal(E.proprio[0], 0);
  // de dos : la caméra en -z voit la face arrière du quad, dont la normale regarde +z → rien
  const E2 = nouvelEtat(W, H, fond(W, H), A.masque), acc2 = nouvelAccumulateur(A);
  assert.equal(accumulerVue(A, vueDe(m, [0, 0, -3], image16), acc2, 0), 0);
  assert.equal(finaliser(A, acc2, E2), 0);
  assert.equal(trous(E2), 64, "tout l'atlas reste un trou");
  assert.deepEqual(Array.from(E2.couleur.slice(0, 4)), [10, 10, 10, 10], "l'origine reste");
});

t("un texel caché par une autre surface ne prend rien de cette vue (test de profondeur)", () => {
  const W = 8, H = 8, m = quad();
  const A = rasteriserUV(m, W, H);
  // un écran devant (z = 1) qui ne couvre que la moitié gauche (x < 0)
  const ecran = { positions: Float32Array.from([-1.5, -1.5, 1, 0, -1.5, 1, 0, 1.5, 1, -1.5, 1.5, 1]), indices: Uint32Array.from([0, 1, 2, 0, 2, 3]) };
  const scene = { positions: Float32Array.from([...m.positions, ...ecran.positions]),
    indices: Uint32Array.from([...m.indices, ...Array.from(ecran.indices, (i) => i + 4)]) };
  const M = matriceCamera({ oeil: [0, 0, 3], cible: [0, 0, 0], fov: 60, aspect: 1, pres: 0.1, loin: 100 });
  const vue = { M, oeil: [0, 0, 3], image: image16, pw: 128, ph: 128, profondeur: carteProfondeur(scene, M, 128, 128) };
  const E = nouvelEtat(W, H, fond(W, H), A.masque), acc = nouvelAccumulateur(A);
  accumulerVue(A, vue, acc, 0, { biais: 1e-3 });
  finaliser(A, acc, E);
  assert.equal(E.peint[4 * W + 1], 0, "à gauche : caché");
  assert.equal(E.peint[4 * W + 6], 1, "à droite : vu");
  // sans carte de profondeur, tout serait vu : c'est bien le test qui cache
  const acc2 = nouvelAccumulateur(A);
  assert.equal(accumulerVue(A, { ...vue, profondeur: null }, acc2, 0), 64);
});

t("deux vues se fondent au poids max(0, n·v)^k ; la plus frontale possède le texel", () => {
  const W = 4, H = 4, m = quad();
  const A = rasteriserUV(m, W, H);
  const rouge = { width: 1, height: 1, data: Uint8ClampedArray.from([200, 0, 0, 255]) };
  const vert = { width: 1, height: 1, data: Uint8ClampedArray.from([0, 200, 0, 255]) };
  const E = nouvelEtat(W, H, fond(W, H), A.masque), acc = nouvelAccumulateur(A);
  const face = [0, 0, 3], biais = [3 * Math.sin(Math.PI / 3), 0, 3 * Math.cos(Math.PI / 3)];   // 60° de côté
  // la vue de biais passe la PREMIÈRE : la propriété va à la plus forte, pas à la première venue
  accumulerVue(A, vueDe(m, biais, vert), acc, 1, { k: 1 });
  accumulerVue(A, vueDe(m, face, rouge), acc, 0, { k: 1 });
  finaliser(A, acc, E);
  // au texel central, le poids de face vaut ≈ 1, celui de biais ≈ cos 60° = 0,5 → rouge 2/3, vert 1/3
  const k = 1 * W + 1, j = Array.from(A.texels).indexOf(k);
  const wf = poids([0, 0, 1], face, Array.from(A.pos.slice(3 * j, 3 * j + 3)), 1);
  const wb = poids([0, 0, 1], biais, Array.from(A.pos.slice(3 * j, 3 * j + 3)), 1);
  assert.ok(Math.abs(E.couleur[4 * k] - (200 * wf) / (wf + wb)) <= 1, `${E.couleur[4 * k]}`);
  assert.ok(Math.abs(E.couleur[4 * k + 1] - (200 * wb) / (wf + wb)) <= 1);
  assert.equal(E.proprio[k], 0);
  assert.equal(poids([0, 0, 1], [0, 0, -3], [0, 0, 0]), 0, "de dos : poids nul");
  assert.ok(pres(poids([0, 0, 1], [0, 0, 3], [0, 0, 0], 4), 1));
});

t("l'échantillon est bilinéaire au centre des pixels", () => {
  const out = [0, 0, 0];
  echantillon(image2, 0.5, 0.5, out);
  assert.deepEqual(out.map(Math.round), [128, 0, 128]);
  echantillon(image2, 0.1, 0.9, out);
  assert.deepEqual(out, [255, 0, 0]);
});

/* ── les retouches ────────────────────────────────────────────────────────── */
const etatPeint = (W = 16, H = 16) => {
  const orig = new Uint8ClampedArray(W * H * 4);
  for (let k = 0; k < W * H; k++) orig.set([10, 20, 30, 255], 4 * k);
  const E = nouvelEtat(W, H, orig, new Uint8Array(W * H).fill(1));
  for (let k = 0; k < W * H; k++) { E.couleur.set([200, 100, 50, 255], 4 * k); E.peint[k] = 1; E.proprio[k] = 2; }
  return E;
};

t("la gomme rend le texel d'origine et retire la peinture, dans le disque seulement", () => {
  const E = etatPeint();
  gommer(E, 8, 8, 2);
  assert.deepEqual(Array.from(E.couleur.slice(4 * (8 * 16 + 8), 4 * (8 * 16 + 8) + 4)), [10, 20, 30, 255]);
  assert.equal(E.peint[8 * 16 + 8], 0);
  assert.equal(E.proprio[8 * 16 + 8], -1);
  assert.equal(E.peint[0], 1, "hors du disque : intact");
  assert.equal(trous(E) > 0 && trous(E) < 20, true);
});

t("combler remplit les trous depuis les voisins peints ; tout combler ne laisse aucun trou", () => {
  const E = etatPeint();
  gommer(E, 8, 8, 3);
  gommer(E, 2, 2, 1.2);                                            // une seconde poche, séparée
  const avant = trous(E);
  // le pinceau posé au fond de la grande poche la comble entière, pas l'autre
  const { combles, rect } = combler(E, { x: 8, y: 8, r: 1 });
  assert.ok(combles > 20 && combles < avant, `${combles}/${avant}`);
  assert.ok(trous(E) > 0 && E.peint[2 * 16 + 2] === 0, "l'autre poche reste");
  assert.ok(rect.x <= 5 && rect.x + rect.w >= 11, JSON.stringify(rect));
  const r = combler(E);
  assert.equal(trous(E), 0);
  assert.equal(r.combles + combles, avant);
  // la couleur comblée vient des voisins (200, 100, 50), pas de l'origine
  assert.deepEqual(Array.from(E.couleur.slice(4 * (8 * 16 + 8), 4 * (8 * 16 + 8) + 3)), [200, 100, 50]);
  assert.equal(E.peint[8 * 16 + 8], 2);
  // un îlot sans aucune peinture reste un trou (rien à copier)
  const F = nouvelEtat(4, 4, fond(4, 4), new Uint8Array(16).fill(1));
  assert.equal(combler(F).combles, 0);
  assert.equal(trous(F), 16);
});

t("estomper adoucit un bord net vers la moyenne des voisins", () => {
  const E = etatPeint();
  for (let y = 0; y < 16; y++) for (let x = 8; x < 16; x++) E.couleur.set([0, 0, 0, 255], 4 * (y * 16 + x));
  const avant = E.couleur[4 * (8 * 16 + 7)];
  estomper(E, 8, 8.5, 3, 1);
  const apres = E.couleur[4 * (8 * 16 + 7)];
  assert.ok(apres < avant && apres > 0, `${avant} → ${apres}`);
  assert.equal(E.couleur[4 * (0 * 16 + 0)], 200, "loin du pinceau : intact");
});

t("les coutures : une arête partagée en 3D, deux UV différents ; soigner moyenne les deux bords", () => {
  // deux triangles qui partagent l'arête (0,0,0)-(0,1,0), coupés en deux îlots dans l'atlas
  const m = {
    positions: Float32Array.from([0, 0, 0, 0, 1, 0, -1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0]),
    uvs: Float32Array.from([0.4, 0.9, 0.4, 0.1, 0.1, 0.9, 0.6, 0.9, 0.6, 0.1, 0.9, 0.9]),
    indices: Uint32Array.from([0, 1, 2, 3, 4, 5]),
  };
  const c = coutures(m, 10, 10);
  assert.equal(c.length, 1, JSON.stringify(c));
  const [a0, a1, b0, b1] = c[0];
  assert.ok(pres(a0[0], 4) && pres(b0[0], 6) && pres(a0[1], b0[1]) && pres(a1[1], b1[1]), JSON.stringify(c[0]));
  // un maillage sans couture (sommets partagés, mêmes UV) n'en a aucune
  assert.equal(coutures(quad(), 10, 10).length, 0);
  const E = nouvelEtat(10, 10, fond(10, 10), new Uint8Array(100).fill(1));
  for (let y = 0; y < 10; y++) { E.couleur.set([200, 0, 0, 255], 4 * (y * 10 + 4)); E.couleur.set([0, 0, 200, 255], 4 * (y * 10 + 6)); }
  assert.ok(soigner(E, c) > 0);
  assert.deepEqual(Array.from(E.couleur.slice(4 * (5 * 10 + 4), 4 * (5 * 10 + 4) + 3)), [100, 0, 100]);
  assert.deepEqual(Array.from(E.couleur.slice(4 * (5 * 10 + 6), 4 * (5 * 10 + 6) + 3)), [100, 0, 100]);
});

t("annuler puis rétablir rendent exactement l'état d'avant et d'après", () => {
  const E = etatPeint();
  const pile = nouvellePile();
  const avant = E.couleur.slice(), avantP = E.peint.slice();
  // un trait : trois touches qui se chevauchent, mémorisées touche par touche, annulées d'un coup
  memoriser(pile, E, rectPinceau(E, 4, 4, 2)); gommer(E, 4, 4, 2);
  memoriser(pile, E, rectPinceau(E, 5, 5, 2), true); estomper(E, 5, 5, 2, 1);
  memoriser(pile, E, rectPinceau(E, 10, 10, 2), true); gommer(E, 10, 10, 2);
  assert.equal(pile.passe.length, 1);
  const apres = E.couleur.slice();
  memoriser(pile, E, rectTout(E));
  combler(E);
  const comble = E.couleur.slice();
  assert.deepEqual(annuler(pile, E), rectTout(E));
  assert.deepEqual(E.couleur, apres);
  annuler(pile, E);
  assert.deepEqual(E.couleur, avant);
  assert.deepEqual(E.peint, avantP);
  assert.equal(annuler(pile, E), null, "rien de plus à annuler");
  retablir(pile, E);
  assert.deepEqual(E.couleur, apres);
  retablir(pile, E);
  assert.deepEqual(E.couleur, comble);
  assert.equal(retablir(pile, E), null);
  // un geste neuf efface le futur ; la pile se borne
  annuler(pile, E);
  memoriser(pile, E, rectPinceau(E, 1, 1, 1));
  assert.equal(pile.futur.length, 0);
  assert.ok(unionRect(null, { x: 1, y: 1, w: 1, h: 1 }).w === 1);
  const p2 = nouvellePile(1e12, 3);
  for (let i = 0; i < 5; i++) memoriser(p2, E, rectPinceau(E, i, i, 1));
  assert.equal(p2.passe.length, 3);
});

t("déborder pousse la couleur hors des îlots, sans toucher l'intérieur", () => {
  const W = 6, H = 1, c = new Uint8ClampedArray(W * 4), m = Uint8Array.from([0, 0, 1, 1, 0, 0]);
  c.set([100, 100, 100, 255], 8); c.set([200, 200, 200, 255], 12);
  deborder(c, m, W, H, 1);
  assert.deepEqual(Array.from(c.slice(4, 8)), [100, 100, 100, 255]);
  assert.deepEqual(Array.from(c.slice(16, 20)), [200, 200, 200, 255]);
  assert.deepEqual(Array.from(c.slice(0, 4)), [0, 0, 0, 0], "une seule passe");
});

t("l'affichage : peint, vues (une teinte par vue), trous en magenta, original, base masquée", () => {
  const E = etatPeint(4, 4);
  gommer(E, 0.5, 0.5, 0.6);
  const s = new Uint8ClampedArray(64);
  composer(E, "trous", false, s);
  assert.deepEqual(Array.from(s.slice(0, 3)), [255, 0, 200]);
  assert.deepEqual(Array.from(s.slice(4, 7)), [200, 100, 50]);
  composer(E, "original", false, s);
  assert.deepEqual(Array.from(s.slice(4, 7)), [10, 20, 30]);
  composer(E, "peint", true, s);
  assert.ok(s[0] === 96 || s[0] === 128, "la base masquée : un damier gris");
  composer(E, "peint", false, s);
  assert.deepEqual(Array.from(s.slice(0, 3)), [10, 20, 30], "base visible : l'origine");
  composer(E, "vues", false, s);
  assert.deepEqual(Array.from(s.slice(0, 3)), [48, 48, 48]);
  assert.notDeepEqual(Array.from(s.slice(4, 7)), [200, 100, 50]);
  const teintes = new Set(Array.from({ length: 18 }, (_, i) => couleurVue(i).join(",")));
  assert.equal(teintes.size, 18);
});

console.log(`\n${ok} tests verts (projection multi-vues)`);
