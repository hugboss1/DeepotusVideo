// t388 / t392 / t401 — le calcul du 3D Studio à écrans (node, sans DOM). Run : node frontend/studio3d/qa/ecrans.test.mjs
import assert from "node:assert/strict";
import { ECRANS, SUIVANT, ECRAN_DU_NOEUD, permis, lireAdresse, ecrireAdresse, nb, bandeau, filtrer, compter, estDecor,
  reduction, presetProche, curseurVersTris, trisVersCurseur, cibleBornee } from "../ecrans/coque_calc.js";
import { ESPECES, GROUPES, ONGLETS, REGLAGES_DEFAUT, presetDe, optionsPour, hauteurCible, echelleVers, vent, recette, lireRecette,
  nomFichier, melanger, VARIANTES_DEFAUT, corpsVariantes, valeurMasque, profilMasque, cadreCartes, vueCarte, facesCartes,
  ATLAS, USAGES_LOD, niveauxLod } from "../ecrans/decor_calc.js";
import * as DONNEES from "../../lib3d/eztree/presets/donnees.js";

const eq = (a, b) => assert.deepEqual(a, b);
let ok = 0;
const t = (nom, f) => { f(); ok++; console.log("  ✓ " + nom); };

/* les préréglages d'ez-tree rangés par nom, comme TreePreset (presets/index.js importe three par options.js) */
const PRESETS = {
  "Ash Small": DONNEES.ashSmall, "Ash Medium": DONNEES.ashMedium, "Ash Large": DONNEES.ashLarge,
  "Aspen Small": DONNEES.aspenSmall, "Aspen Medium": DONNEES.aspenMedium, "Aspen Large": DONNEES.aspenLarge,
  "Bush 1": DONNEES.bush1, "Bush 2": DONNEES.bush2, "Bush 3": DONNEES.bush3,
  "Oak Small": DONNEES.oakSmall, "Oak Medium": DONNEES.oakMedium, "Oak Large": DONNEES.oakLarge,
  "Pine Small": DONNEES.pineSmall, "Pine Medium": DONNEES.pineMedium, "Pine Large": DONNEES.pineLarge,
  "Trellis": DONNEES.trellis,
};

/* ── coque ── */
t("onze écrans en trois groupes ; seul le groupe 2 exige un modèle ouvert", () => {
  eq(ECRANS.map((e) => e.id), ["ouvrir", "importer", "preparer", "etabli", "texture", "rig", "affiner", "animer", "exporter", "decor", "graphe"]);
  assert.deepEqual([...new Set(ECRANS.map((e) => e.groupe))], [1, 2, 3]);
  for (const e of ECRANS) assert.equal(permis(e.id, null), e.groupe !== 2, e.id);
  for (const e of ECRANS) assert.equal(permis(e.id, { job: "j" }), true, e.id);
  assert.equal(permis("inconnu", { job: "j" }), false);
});

t("le parcours « Envoyer vers » suit l'ordre du groupe 2 et chaque nœud du graphe a son écran", () => {
  const g2 = ECRANS.filter((e) => e.groupe === 2 && e.id !== "etabli").map((e) => e.id);   // l'Établi : un atelier, hors parcours
  for (let i = 0; i < g2.length - 1; i++) assert.equal(SUIVANT[g2[i]], g2[i + 1]);
  assert.equal(SUIVANT.exporter, undefined);
  for (const n of ["prompt", "ref", "preview", "texture", "remesh", "rig", "animate", "export", "etabli"])
    assert.ok(ECRANS.some((e) => e.id === ECRAN_DU_NOEUD[n]), n);
});

t("l'adresse : lien profond, écran par défaut, écran interdit sans modèle, job nettoyé", () => {
  assert.deepEqual(lireAdresse("?job=abc&version=3&ecran=rig"), { job: "abc", version: 3, ecran: "rig" });
  assert.deepEqual(lireAdresse(""), { job: null, version: null, ecran: "ouvrir" });
  assert.deepEqual(lireAdresse("?job=abc"), { job: "abc", version: null, ecran: "preparer" });
  assert.equal(lireAdresse("?ecran=rig").ecran, "ouvrir");
  assert.equal(lireAdresse("?ecran=decor").ecran, "decor");
  assert.equal(lireAdresse("?job=../x%2Fy&version=0").job, "..xy");
  assert.equal(lireAdresse("?job=a&version=-2").version, null);
  assert.equal(ecrireAdresse({ job: "abc", version: 2, ecran: "rig" }), "?job=abc&version=2&ecran=rig");
  assert.equal(ecrireAdresse({ job: null, version: 2, ecran: "ouvrir" }), "?ecran=ouvrir");
  for (const q of ["?job=abc&version=2&ecran=rig", "?ecran=decor"]) assert.equal(ecrireAdresse(lireAdresse(q)), q);
});

t("les nombres : espace fine en français, virgule en anglais", () => {
  assert.equal(nb(1499810, "fr"), "1 499 810");
  assert.equal(nb(1499810, "en"), "1,499,810");
  assert.equal(nb(500, "fr"), "500");
  assert.equal(nb(null), "—");
});

t("le bandeau : vide, riggé ou non, version ouverte / dernière", () => {
  assert.equal(bandeau(null).vide, true);
  const f = { job: "j", nom: "Sorcière", version: 2, derniere: 3, sommets: 49976, triangles: 99962, vignette: "/v",
    rig: { rigge: true, os: 26 } };
  const b = bandeau(f, true);
  assert.equal(b.nom, "Sorcière");
  assert.equal(b.rigge, true);
  assert.equal(b.version, "v2/3");
  assert.equal(b.sale, true);
  assert.equal(b.detail.split(" · ").length, 3);                      // os · sommets · triangles
  assert.equal(bandeau({ ...f, derniere: 2, rig: { rigge: false } }).detail.split(" · ").length, 2);
  assert.equal(bandeau({ ...f, derniere: 2 }).version, "v2");
});

t("la galerie : filtres, recherche, compte par filtre", () => {
  const M = [
    { job: "a", nom: "Sorcière", moteur: "tripo", rig: { rigge: true } },
    { job: "b", nom: "Caisse en bois", moteur: "trellis", rig: { rigge: false } },
    { job: "c", nom: "Guerrier", moteur: "meshy", rig: { rigge: false } },
    { job: "d", nom: "rocher", moteur: "hunyuan", rig: { rigge: false } },
  ];
  assert.deepEqual(filtrer(M, "rigges").map((m) => m.job), ["a"]);
  assert.deepEqual(filtrer(M, "decor").map((m) => m.job), ["b", "d"]);
  assert.deepEqual(filtrer(M, "personnages").map((m) => m.job), ["a", "c"]);
  assert.deepEqual(filtrer(M, "tous", "MESHY").map((m) => m.job), ["c"]);
  assert.deepEqual(compter(M), { tous: 4, rigges: 1, non_rigges: 3, personnages: 2, decor: 2 });
  assert.equal(estDecor({ nom: "arbre", rig: { rigge: true } }), false);   // riggé = personnage
  assert.equal(estDecor({ nom: "x", categorie: "decor" }), true);
  assert.equal(estDecor({ nom: "saule_moyen_1", rig: { rigge: false } }), true);       // rangé depuis le Décor
  assert.equal(estDecor({ nom: "Chêne du lac" }), true);
  assert.equal(estDecor({ nom: "Pinocchio" }), false);                                 // un mot entier, pas un morceau
});

/* ── Préparer ── */
const CIBLES = [["micro", 500], ["small", 1000], ["prop", 2500], ["detailed", 5000], ["game", 10000], ["balanced", 25000],
  ["high", 50000], ["ultra", 100000], ["extreme", 150000], ["max", 200000]].map(([preset, triangles]) => ({ preset, triangles }));

t("Préparer : réduction, préréglage proche, curseur logarithmique aller-retour, cible bornée", () => {
  assert.equal(reduction(1499810, 99962), 93);                          // le « 93 % » relevé chez Sorceress
  assert.equal(reduction(0, 10), null);
  assert.equal(presetProche(CIBLES, 10000), "game");
  assert.equal(presetProche(CIBLES, 10100), "game");
  assert.equal(presetProche(CIBLES, 12000), null);
  assert.equal(curseurVersTris(0, 500, 200000), 500);
  assert.equal(curseurVersTris(1000, 500, 200000), 200000);
  for (const n of [500, 2500, 10000, 99962, 200000]) {
    const back = curseurVersTris(trisVersCurseur(n, 500, 200000), 500, 200000);
    assert.ok(Math.abs(back - n) / n < 0.01, `${n} → ${back}`);
  }
  assert.equal(cibleBornee(200000, 12000), 12000);
  assert.equal(cibleBornee(5000, null), 5000);
});

/* ── Décor ── */
t("23 espèces, chacune rangée dans un groupe d'un onglet et servie par un préréglage d'ez-tree", () => {
  assert.equal(ESPECES.length, 23);
  assert.equal(new Set(ESPECES.map((e) => e.id)).size, 23);
  assert.deepEqual([...ONGLETS.arbres, ...ONGLETS.sol].sort(), [...GROUPES].sort());
  for (const e of ESPECES) {
    assert.ok(GROUPES.includes(e.groupe), e.id);
    for (const taille of ["petit", "moyen", "grand"]) assert.ok(PRESETS[presetDe(e, taille)], `${e.id} ${taille}`);
  }
  assert.equal(presetDe("chene", "grand"), "Oak Large");
  assert.equal(presetDe("bonsai", "grand"), "Oak Small");                // taille fixe
  assert.equal(presetDe("buisson", "petit"), "Bush 2");
});

t("les options : graine, niveaux bornés, écorce et feuille auto ou choisies, préréglage jamais modifié", () => {
  const avant = JSON.stringify(PRESETS["Oak Medium"]);
  const o = optionsPour({ espece: "chene", graine: 42, niveaux: 2 }, PRESETS);
  assert.equal(JSON.stringify(PRESETS["Oak Medium"]), avant);
  assert.equal(o.seed, 42);
  assert.equal(o.branch.levels, Math.min(PRESETS["Oak Medium"].branch.levels, 2));
  assert.equal(o.bark.type, "oak");
  assert.equal(o.leaves.type, "oak");
  const b = optionsPour({ espece: "chene", ecorce: "birch", forme: "pine" }, PRESETS);
  assert.deepEqual([b.bark.type, b.leaves.type], ["birch", "pine"]);
  assert.equal(optionsPour({ espece: "chene", ecorce: "inventee" }, PRESETS).bark.type, "oak");
});

t("densité, cartes, saisons, sans feuilles : ce qui change le feuillage", () => {
  const base = optionsPour({ espece: "chene" }, PRESETS).leaves;
  assert.equal(base.count, PRESETS["Oak Medium"].leaves.count);         // densité 50 = le préréglage
  assert.equal(optionsPour({ espece: "chene", densite: 100 }, PRESETS).leaves.count, base.count * 2);
  const cartes = optionsPour({ espece: "chene", feuillage: "cartes" }, PRESETS).leaves;
  assert.equal(cartes.billboard, "single");
  assert.equal(cartes.count, Math.round(base.count / 2));
  assert.equal(optionsPour({ espece: "chene", saison: "hiver" }, PRESETS).leaves.count, 0);   // feuillu nu l'hiver
  assert.ok(optionsPour({ espece: "pin", saison: "hiver" }, PRESETS).leaves.count > 0);      // persistant
  assert.notEqual(optionsPour({ espece: "chene", saison: "automne" }, PRESETS).leaves.tint, base.tint);
  assert.equal(optionsPour({ espece: "pin", saison: "automne" }, PRESETS).leaves.tint, optionsPour({ espece: "pin" }, PRESETS).leaves.tint);
  assert.equal(optionsPour({ espece: "arbre_nu" }, PRESETS).leaves.count, 0);
  assert.equal(optionsPour({ espece: "chene", feuilles: false }, PRESETS).leaves.count, 0);
  assert.equal(optionsPour({ espece: "saule" }, PRESETS).branch.force.direction.y, -1);
  assert.equal(optionsPour({ espece: "palmier" }, PRESETS).branch.levels, 1);
  assert.equal(melanger(0xffffff, 0x123456), 0x123456);
  assert.equal(melanger(0x808080, 0xffffff), 0x808080);
});

t("hauteur réelle : espèce × taille × échelle, et l'échelle qui y mène depuis l'arbre brut", () => {
  assert.equal(hauteurCible({ espece: "chene" }), 15);                   // le chêne moyen de TreeGen : 15,4 m
  assert.equal(hauteurCible({ espece: "chene", taille: "grand" }), 19.5);
  assert.equal(hauteurCible({ espece: "chene", taille: "petit", echelle: 2 }), 21);
  assert.equal(hauteurCible({ espece: "bonsai", taille: "grand" }), 0.4);  // taille fixe
  assert.equal(hauteurCible({ espece: "chene", echelle: 99 }), 60);        // échelle bornée à 4
  assert.equal(echelleVers(64.6, { espece: "chene" }), 15 / 64.6);
  assert.equal(echelleVers(0, { espece: "chene" }), 1);
  for (const e of ESPECES) assert.ok(e.hauteur > 0 && e.hauteur <= 25, e.id);
  /* chaque réglage par défaut a une valeur : un curseur sans défaut affiche « undefined » (vu à l'écran le 31/10) */
  for (const [k, v] of Object.entries(REGLAGES_DEFAUT)) assert.ok(v !== undefined && v !== null, k);
  for (const k of ["echelle", "niveaux", "densite", "tailleFeuille", "retombee", "ventForce", "ventVitesse", "ventDirection", "frisson", "graine"])
    assert.equal(typeof REGLAGES_DEFAUT[k], "number", k);
  const v = vent({ ventForce: 1, ventDirection: 90, ventVitesse: 2, frisson: 5 });
  assert.deepEqual(v.force, [0, 0, 1]);
  assert.equal(v.frequence, 1);
  assert.equal(v.echelle, 70);
  assert.deepEqual(vent({ vent: false }).force, [0, 0, 0]);
});

t("la recette : aller-retour, clés inconnues et types faux écartés, refus d'un autre format", () => {
  const r = recette({ ...REGLAGES_DEFAUT, espece: "saule", graine: 7 }, "Saule du lac");
  const lu = lireRecette(JSON.stringify(r));
  assert.equal(lu.nom, "Saule du lac");
  assert.deepEqual(lu.reglages, { ...REGLAGES_DEFAUT, espece: "saule", graine: 7 });
  const sale = lireRecette({ format: "deepotus-decor", reglages: { espece: "baobab", graine: "x", inconnu: 1, densite: 80 } });
  assert.equal(sale.reglages.espece, REGLAGES_DEFAUT.espece);
  assert.equal(sale.reglages.graine, REGLAGES_DEFAUT.graine);
  assert.equal(sale.reglages.densite, 80);
  assert.ok(!("inconnu" in sale.reglages));
  assert.throws(() => lireRecette("{"), /json/);
  assert.throws(() => lireRecette({ format: "treegen" }), /format/);
  assert.equal(recette({ espece: "pin", taille: "grand", graine: 3 }).nom, "pin_grand_3");
  assert.equal(nomFichier("Chêne du Lac !"), "chene_du_lac");
  assert.equal(nomFichier("***"), "decor");
});

/* ── Décor › Accessoire (t402) : variantes, masque de vent, cartes, LOD ── */
t("les variantes : le corps envoyé reste dans les bornes du service", () => {
  eq(corpsVariantes("j", 2, {}), { job: "j", version: 2, ...VARIANTES_DEFAUT });
  const c = corpsVariantes("j", 1, { nombre: 12, graine: -3, echelle_pct: 90, teinte: 2, luminosite: 1, rotation: 0 });
  eq([c.nombre, c.graine, c.echelle_pct, c.teinte, c.luminosite, c.rotation], [8, 0, 50, 1, 0.6, false]);
  eq(corpsVariantes("j", 1, { nombre: 1.4 }).nombre, 2);
  eq(corpsVariantes("j", 1, { graine: 7.9 }).graine, 7);
  eq(corpsVariantes("j", 1, { teinte: "x" }).teinte, 0.25);
});

t("le masque de vent croît avec la hauteur (mêmes valeurs que studio3d_decor.valeur_masque)", () => {
  eq(valeurMasque(0.5, 2), 0.25);
  eq(valeurMasque(0.2, 1, 0.25), 0);
  assert.ok(Math.abs(valeurMasque(0.625, 1, 0.25) - 0.5) < 1e-12);
  eq([valeurMasque(-1), valeurMasque(0), valeurMasque(1), valeurMasque(3)], [0, 0, 1, 1]);
  for (const [c, s] of [[0.5, 0], [1.5, 0], [3, 0.4]]) {
    const v = Array.from({ length: 51 }, (_, i) => valeurMasque(i / 50, c, s));
    for (let i = 1; i < v.length; i++) assert.ok(v[i] >= v[i - 1], `${c}/${s}/${i}`);
    eq(v[50], 1);
  }
  eq(profilMasque(1, 0, 120, 40, 4).split(" "), ["0,40", "30,30", "60,20", "90,10", "120,0"]);
});

t("les cartes : cadre carré, huit caméras sur l'azimut, faces et cases de l'atlas", () => {
  const c = cadreCartes({ min: [-1, 0, -0.5], max: [3, 2, 0.5] });          // même boîte que le banc python
  eq(c.centre, [1, 1, 0]);
  assert.ok(Math.abs(c.cote - 2 * Math.sqrt(4.25)) < 1e-12);
  eq(cadreCartes({ min: [0, 0, 0], max: [1, 10, 1] }).cote, 10);
  const k = { centre: [0, 1, 0], cote: 2 };
  eq(vueCarte(0, k), { position: [0, 1, 4], cible: [0, 1, 0], colonne: 0, ligne: 0 });     // face : +Z
  eq(vueCarte(2, k).position, [4, 1, 0]);                                                  // 90° : +X
  eq(vueCarte(4, k).position, [0, 1, -4]);
  eq([vueCarte(5, k).colonne, vueCarte(5, k).ligne], [1, 1]);
  eq(ATLAS, { colonnes: 4, lignes: 2 });
  eq(facesCartes(2).map((f) => f.case), [0, 4, 2, 6]);
  eq(facesCartes(3).map((f) => f.case), [0, 4, 1, 5, 3, 7]);
  assert.throws(() => facesCartes(4), /plans/);
});

t("la chaîne de LOD : les usages de mesh_lod et une ligne par niveau", () => {
  eq(USAGES_LOD, ["mobile", "pc", "impression"]);
  eq(niveauxLod({ niveaux: [{ niveau: 0, tris: 900 }, { niveau: 1, tris: 300 }] }),
    [{ niveau: 0, triangles: 900 }, { niveau: 1, triangles: 300 }]);
  eq(niveauxLod(null), []);
});

console.log(`\nOK — ${ok} tests (3D Studio à écrans)`);
