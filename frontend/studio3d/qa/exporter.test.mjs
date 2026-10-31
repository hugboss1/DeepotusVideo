// t400 — le calcul de l'écran Exporter du 3D Studio (node, sans DOM). Run : node frontend/studio3d/qa/exporter.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SECTIONS, ACTIONS, CIBLES_ETABLI, USAGES_LOD, NOMMAGES, FORMATS_PAYANTS, nomSur, nomExport, clipsCoches,
  hitboxesParDefaut, disponibilite, nomDeReponse, octets, formatsLocaux, corpsGlb } from "../ecrans/exporter_calc.js";

let ok = 0;
const t = (nom, f) => { f(); ok++; console.log("  ✓ " + nom); };
const DICO = JSON.parse(readFileSync(new URL("../../shared/i18n/studio3decrans_exporter.json", import.meta.url), "utf-8"));
const cle = (k) => "studio3decrans." + k;

const CLIPS = [{ nom: "Marche", duree: 1 }, { nom: "Saut", duree: 1.5 }];
const OS = [{ nom: "pelvis", role: "bassin" }, { nom: "spine_01", role: "colonne" }, { nom: "spine_02", role: "colonne" },
  { nom: "head", role: "tete" }, { nom: "hand_l", role: "main_g" }, { nom: "hand_r", role: "main_d" },
  { nom: "upperarm_l", role: "bras_g" }, { nom: "foot_l", role: "pied_g" }, { nom: "x", role: null }];
const ETAT = { clips: CLIPS, a_squelette: true, os: OS, blender: { dispo: true, version: "5.2.2" } };

t("six sections, l'ordre du relevé ; chaque action et chaque section a son libellé et son aide FR/EN", () => {
  assert.deepEqual(SECTIONS.map((s) => s.id), ["moteur", "web", "optimisation", "impression", "formats", "bibliotheque"]);
  assert.deepEqual(SECTIONS[0].actions.slice(0, 3), ["glb_maillage", "glb_pose", "glb_animation"]);
  assert.equal(new Set(ACTIONS).size, ACTIONS.length);
  for (const s of SECTIONS) assert.ok(DICO[cle("exp.section_" + s.id)], s.id);
  for (const a of ACTIONS) assert.ok(DICO[cle("exp.aide_" + a)], a);
  for (const c of CIBLES_ETABLI) assert.ok(DICO[cle("exp." + c)], c);
  for (const u of USAGES_LOD) assert.ok(DICO[cle("exp.usage_" + u)], u);
  for (const n of NOMMAGES) assert.ok(DICO[cle("exp.nommage_" + n)], n);
  for (const r of ["modele", "clips", "squelette", "blender"]) assert.ok(DICO[cle("exp.raison_" + r)], r);
  for (const [k, v] of Object.entries(DICO)) assert.equal(v.contexte, true, k);
});

t("le nom de fichier suit la règle du serveur (accents retirés, 48 caractères)", () => {
  assert.equal(nomSur("Héros vert/../x"), "Heros_vert_x");
  assert.equal(nomSur("", "job 1"), "job_1");
  assert.equal(nomSur("///", ""), "modele");
  assert.equal(nomSur("a".repeat(60)).length, 48);
  assert.equal(nomExport("", "Sorcière", 3, "pose"), "Sorciere_v3_pose.glb");
  assert.equal(nomExport("Mon perso", "x", 1, "threejs", "zip"), "Mon_perso_v1_threejs.zip");
});

t("les clips cochés : aucun ou tous = null (le GLB part entier)", () => {
  assert.equal(clipsCoches(CLIPS, []), null);
  assert.equal(clipsCoches(CLIPS, ["Saut", "Marche"]), null);
  assert.deepEqual(clipsCoches(CLIPS, ["Saut", "Inconnu"]), ["Saut"]);
  assert.deepEqual(corpsGlb("animation", { version: 2, coches: ["Saut"], clips: CLIPS }), { variante: "animation", version: 2, nom: undefined, clips: ["Saut"] });
  assert.deepEqual(corpsGlb("pose", { version: 2, clipPose: "Saut", nom: "h" }), { variante: "pose", version: 2, nom: "h", clip: "Saut" });
  assert.deepEqual(corpsGlb("maillage", { version: 1, clipPose: "Saut", coches: ["Saut"], clips: CLIPS }), { variante: "maillage", version: 1, nom: undefined });
});

t("hitboxes Godot par défaut : un os par rôle, hurt au corps, hit aux extrémités", () => {
  const hb = hitboxesParDefaut(OS);
  assert.deepEqual(hb.map((h) => [h.os, h.role]), [["pelvis", "hurt"], ["spine_01", "hurt"], ["head", "hurt"],
    ["hand_l", "hit"], ["hand_r", "hit"], ["foot_l", "hit"]]);
  for (const h of hb) assert.ok(h.forme === "capsule" && h.rayon >= 0.05 && h.rayon <= 1, h.os);
  assert.deepEqual(hitboxesParDefaut([{ nom: "a", role: "bras_g" }]), []);
  assert.deepEqual(hitboxesParDefaut(null), []);
});

t("chaque action dit si elle est permise, et sinon pourquoi", () => {
  for (const a of ACTIONS) assert.equal(disponibilite(a, ETAT).ok, true, a);
  for (const a of ACTIONS) assert.equal(disponibilite(a, null).raison, "exp.raison_modele", a);
  const sans = { ...ETAT, clips: [], a_squelette: false, os: [], blender: { dispo: false } };
  assert.deepEqual(disponibilite("glb_animation", sans), { ok: false, raison: "exp.raison_clips" });
  assert.deepEqual(disponibilite("godot", sans), { ok: false, raison: "exp.raison_squelette" });
  assert.deepEqual(disponibilite("fbx", sans), { ok: false, raison: "exp.raison_blender" });
  assert.equal(disponibilite("glb_pose", sans).ok, true);          // sans clip : la pose de repos
  assert.equal(disponibilite("inconnue", ETAT).ok, false);
});

t("nom tiré de Content-Disposition, octets lisibles, formats locaux sans les payants", () => {
  assert.equal(nomDeReponse('attachment; filename="a_v2_godot.zip"', "x"), "a_v2_godot.zip");
  assert.equal(nomDeReponse("attachment; filename*=UTF-8''h%C3%A9ros.zip", "x"), "héros.zip");
  assert.equal(nomDeReponse(null, "d.zip"), "d.zip");
  assert.equal(octets(512), "512 o");
  assert.equal(octets(1536), "1,5 Ko");
  assert.equal(octets(3 * 1024 * 1024, "en"), "3.0 MB");
  assert.equal(octets(undefined), "—");
  assert.deepEqual(formatsLocaux({ local_export: ["obj", "stl", "3mf", "gltf", "fbx"] }), ["obj", "stl", "3mf", "gltf"]);
  assert.deepEqual(formatsLocaux(null), []);
  assert.deepEqual(FORMATS_PAYANTS, ["fbx", "usdz", "blend"]);
});

console.log(`\nOK — ${ok} tests (écran Exporter)`);
