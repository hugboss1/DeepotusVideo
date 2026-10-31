// t398 + t399 + t405 — le calcul de l'écran Animer du 3D Studio (node, sans DOM). Run : node frontend/studio3d/qa/animer.test.mjs
import assert from "node:assert/strict";
import { listeGeneres, choisirMarche, cleCategorie, cleSous, pagesVisibles, requeteCatalogue, VUES, vueCamera, miroir,
  curseurVersTemps, tempsVersCurseur, horloge, actionDeTouche, pasConduite, bornerDuree, prix, blocageTexte, lienEtabli,
  ORIGINES, DUREE, DUREE_HY, estHy, bornesDuree, corpsTexte, roleOs, osParRole, chaineIK, doigtsDe, typeDoigt, prise, PRISES,
  ORDRE_PRISES, courbureDoigt, classerPhysique, familleOs, configPhysique, pasRessort, ikDeuxOs, distance, unitaire,
  longueur, vectoriel, axeCourbure } from "../ecrans/animer_calc.js";

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

/* ── t405 : HY-Motion, physique, IK, prises ── */

t("HY-Motion : licence puis clé fal à la place de la clé Meshy ; bornes 0,5–12 s ; corps de la requête", () => {
  const f = { job: "j", version: 2, rig: { rigge: true } };
  assert.equal(blocageTexte({ fiche: f, modele: "hy-motion", licence: false, fal: true, prompt: "a" }), "anim.bloc_licence");
  assert.equal(blocageTexte({ fiche: f, modele: "hy-motion-fast", licence: true, fal: false, prompt: "a" }), "anim.bloc_cle_fal");
  assert.equal(blocageTexte({ fiche: f, modele: "hy-motion", licence: true, fal: true, meshy: false, mode: "prime", prompt: "a" }), null);
  assert.equal(blocageTexte({ fiche: f, modele: "hy-motion", licence: true, fal: true, prompt: " " }), "anim.bloc_prompt");
  assert.equal(blocageTexte({ fiche: f, modele: "meshy", licence: true, fal: true, meshy: false, mode: "swift", prompt: "a" }), "anim.bloc_cle");
  assert.ok(estHy("hy-motion") && estHy("hy-motion-fast") && !estHy("meshy") && !estHy("kimodo"));
  assert.deepEqual(bornesDuree("hy-motion"), DUREE_HY);
  assert.deepEqual(bornesDuree("meshy"), DUREE);
  assert.equal(bornerDuree(0.2, DUREE_HY), 0.5);
  assert.equal(bornerDuree(30, DUREE_HY), 12);
  assert.deepEqual(corpsTexte({ fiche: f, modele: "hy-motion", prompt: " saute ", duree: 1.2, guidance: 99, licence: true }),
    { job: "j", version: 2, prompt: "saute", duree: 1, modele: "hy-motion", guidance: 10, licence_acceptee: true });
  assert.deepEqual(corpsTexte({ fiche: f, prompt: "x", duree: 1.2 }), { job: "j", version: 2, prompt: "x", duree: 2, modele: "meshy", mode: "swift" });
  assert.equal(corpsTexte({ fiche: f, modele: "hy-motion", prompt: "x" }).licence_acceptee, false);
});

t("rôles des os : Unreal, Mixamo, SMPL renommé ; chaînes IK ; doigts", () => {
  assert.equal(roleOs("upperarm_l"), "bras_g");
  assert.equal(roleOs("mixamorig:RightForeArm"), "avantbras_d");
  assert.equal(roleOs("hand_r"), "main_d");
  assert.equal(roleOs("thigh_l"), "cuisse_g");
  assert.equal(roleOs("calf_r"), "jambe_d");
  assert.equal(roleOs("LeftFoot"), "pied_g");
  assert.equal(roleOs("pelvis"), "bassin");
  assert.equal(roleOs("spine_02"), "colonne");
  assert.equal(roleOs("hair_01"), null);
  const os = ["pelvis", "spine_01", "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l", "thigh_r", "calf_r", "foot_r",
    "upperarm_twist_l"].map((nom, i) => ({ nom, profondeur: i }));
  const r = osParRole(os);
  assert.deepEqual(chaineIK(r, "bras", "g"), [3, 4, 5]);
  assert.deepEqual(chaineIK(r, "jambe", "d"), [6, 7, 8]);
  assert.equal(chaineIK(r, "bras", "d"), null);
  const noms = ["hand_l", "index_01_l", "index_02_l", "thumb_01_l", "middle_01_r", "mixamorig:LeftHandPinky1", "ring_01"];
  assert.deepEqual(doigtsDe(noms, "g"), [1, 2, 3, 5]);
  assert.deepEqual(doigtsDe(noms, "d"), [4]);
  assert.equal(typeDoigt("thumb_01_l"), "pouce");
  assert.equal(typeDoigt("index_02_l"), "index");
  const p = prise("gun_d", 2);
  assert.equal(courbureDoigt("index_01_r", p), 0.25);
  assert.equal(courbureDoigt("thumb_01_r", p), 0.35);
  assert.equal(courbureDoigt("middle_01_r", p), 0.75);
  assert.deepEqual(p.cible, [-0.14, 1.56, 0.6]);
  assert.equal(prise("main_g").cible, null);
  assert.equal(prise("bidon"), null);
  assert.deepEqual(ORDRE_PRISES.slice().sort(), Object.keys(PRISES).sort());
});

t("physique : familles Jiggle / Hair / Cloth reconnues par leur nom, grisées sinon", () => {
  const noms = ["spine_03", "chest", "breast_l", "Chest_R", "jiggle_belly", "hair_01", "Ponytail2", "tail_03", "cape_01",
    "skirt_front", "cloth_back", "upperarm_l"];
  const c = classerPhysique(noms);
  assert.deepEqual(c.jiggle, [2, 3, 4]);
  assert.deepEqual(c.hair, [5, 6, 7]);
  assert.deepEqual(c.cloth, [8, 9, 10]);
  assert.equal(familleOs("chest"), null);                  // la poitrine du TRONC n'est pas un os à ressort
  assert.deepEqual(classerPhysique(["pelvis", "head"]), { jiggle: [], hair: [], cloth: [] });
  const cfg = configPhysique({ job: "j", version: 3, actifs: { hair: true }, reglages: { raideur: 2, amortissement: 0.5, gravite: 0 },
    os: { hair: ["hair_01"] } });
  assert.equal(cfg.format, "deepotus-physics-config");
  assert.deepEqual(cfg.familles.hair, { actif: true, os: ["hair_01"] });
  assert.deepEqual(cfg.familles.jiggle, { actif: false, os: [] });
  assert.deepEqual(cfg.reglages, { raideur: 2, amortissement: 0.5, gravite: 0 });
  assert.deepEqual(JSON.parse(JSON.stringify(cfg)), cfg);
});

t("os à ressort : écarté de 90°, il revient à sa direction de repos (gravité nulle), longueur gardée", () => {
  const tete = [0, 1, 0], cible = [0, 0.8, 0];             // repos : la queue pend de 0,2 sous la tête
  let e = { queue: [0.2, 1, 0], avant: [0.2, 1, 0] };       // écartée de 90°
  const r = { raideur: 1, amortissement: 0.4, gravite: 0 };
  let max = 0;
  for (let i = 0; i < 2000; i++) {
    e = pasRessort(e, tete, cible, r, 1 / 60);
    max = Math.max(max, Math.abs(distance(e.queue, tete) - 0.2));
  }
  assert.ok(distance(e.queue, cible) < 1e-3, `queue ${e.queue}`);
  assert.ok(max < 1e-9, `longueur ${max}`);
  // l'élan : un os qui bouge DÉPASSE puis revient (amorti), il ne glisse pas
  let f = { queue: [0.2, 1, 0], avant: [0.2, 1, 0] }, depasse = false;
  for (let i = 0; i < 600; i++) { f = pasRessort(f, tete, cible, { raideur: 1, amortissement: 0.05, gravite: 0 }, 1 / 60); if (f.queue[0] < -1e-3) depasse = true; }
  assert.ok(depasse);
  // amortissement 1 : aucun élan gardé, la queue rejoint son repos SANS le dépasser
  let h = { queue: [0.2, 1, 0], avant: [0.2, 1, 0] };
  for (let i = 0; i < 600; i++) { h = pasRessort(h, tete, cible, { raideur: 1, amortissement: 1, gravite: 0 }, 1 / 60); assert.ok(h.queue[0] > -1e-9, `dépasse : ${h.queue}`); }
  // la gravité fait pendre une queue horizontale plus bas que son repos
  const th = [0, 1, 0], horiz = [0.2, 1, 0];
  let g = { queue: horiz.slice(), avant: horiz.slice() };
  for (let i = 0; i < 2000; i++) g = pasRessort(g, th, horiz, { raideur: 1, amortissement: 0.4, gravite: 0.5 }, 1 / 60);
  assert.ok(g.queue[1] < 1 - 0.01 && Math.abs(distance(g.queue, th) - 0.2) < 1e-9, `${g.queue}`);
  // premier pas : l'état naît sur la cible ; os de longueur nulle : rien ne bouge
  assert.deepEqual(pasRessort(null, tete, cible).queue, cible);
  assert.deepEqual(pasRessort({ queue: [1, 1, 1], avant: [1, 1, 1] }, tete, tete).queue, tete);
});

t("IK à deux os : cible atteignable rejointe à 1e-3, longueurs gardées ; hors de portée, le bras s'étend droit", () => {
  const a = [0, 1.4, 0], b = [0.28, 1.4, -0.01], c = [0.52, 1.4, 0];
  const L1 = distance(a, b), L2 = distance(b, c);
  for (const tg of [[0.3, 1.2, 0.25], [0.1, 1.0, 0.2], [0.4, 1.5, -0.1], [0.05, 1.45, 0.3]]) {
    const r = ikDeuxOs(a, b, c, tg, [0, 0, -1]);
    assert.ok(r.atteint);
    assert.ok(distance(r.bout, tg) < 1e-3, `bout ${r.bout} ≠ ${tg}`);
    assert.ok(Math.abs(distance(r.coude, a) - L1) < 1e-9 && Math.abs(distance(r.bout, r.coude) - L2) < 1e-9);
  }
  const loin = [2, 1.4, 1];
  const r = ikDeuxOs(a, b, c, loin);
  assert.equal(r.atteint, false);
  const dir = unitaire([loin[0] - a[0], loin[1] - a[1], loin[2] - a[2]]);
  assert.ok(distance(r.bout, [a[0] + dir[0] * (L1 + L2), a[1] + dir[1] * (L1 + L2), a[2] + dir[2] * (L1 + L2)]) < 1e-9);
  const u = [r.coude[0] - a[0], r.coude[1] - a[1], r.coude[2] - a[2]], v = [r.bout[0] - r.coude[0], r.bout[1] - r.coude[1], r.bout[2] - r.coude[2]];
  assert.ok(longueur(vectoriel(u, v)) < 1e-9, "le bras n'est pas droit");
  // membre droit (en T) : le pli prend le plan du pôle (coude vers l'arrière, −Z)
  const droit = ikDeuxOs([0, 0, 0], [1, 0, 0], [2, 0, 0], [1, 0, 0], [0, 0, -1]);
  assert.ok(droit.coude[2] < -0.5 && distance(droit.bout, [1, 0, 0]) < 1e-9, `${droit.coude}`);
  // l'axe de courbure d'un doigt : vers le dessous de la main
  assert.deepEqual(axeCourbure([1, 0, 0], [0, 1, 0]), [0, 0, -1]);
});

console.log(`\nOK — ${ok} tests (écran Animer)`);
