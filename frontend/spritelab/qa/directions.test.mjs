// directions.test.mjs — t111 (plan-sprites T9-T11, écrans) : le module PUR des onglets Bible et Prompt. Les noms des
// 8 directions et leur ORDRE sont lus dans le backend (sprite_directions.py, en texte) : si l'un change, les tags de
// la feuille mentiraient — ce banc rougit.
import { readFileSync } from "node:fs";
import * as D from "../directions.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 240) : "")); };
const J = JSON.stringify;

const py = readFileSync(new URL("../../../backend/app/services/sprite_directions.py", import.meta.url), "utf-8");
const HUIT = py.match(/HUIT = \(([^)]*)\)/)[1].match(/"(\w+)"/g).map((s) => s.slice(1, -1));
ok("ORBITES : les 8 noms du backend, dans SON ordre", J(D.ORBITES.map(([n]) => n)) === J(HUIT), J(D.ORBITES));
ok("ORBITES : sud face caméra (0°), puis 45° par direction, sens de HUIT", J(D.ORBITES.map(([, a]) => a)) === J([0, 45, 90, 135, 180, 225, 270, 315]));
// ouest = profil au nez vers la GAUCHE du cadre (sprite_directions.VERS_HUIT : left → west). Le modèle glTF regarde
// +Z ; θ = 90° pose la caméra sur +X (model-viewer : x = r·sinφ·sinθ) : la droite de l'écran y est −Z, le nez (+Z) à
// GAUCHE. Le banc le recalcule plutôt que de le croire.
const az = Object.fromEntries(D.ORBITES), rad = (d) => d * Math.PI / 180;
const cam = (t) => [Math.sin(rad(t)), 0, Math.cos(rad(t))];
const droiteEcran = (t) => { const f = cam(t).map((v) => -v); return [f[1] * 0 - f[2] * 1, f[2] * 0 - f[0] * 0, f[0] * 1 - f[1] * 0]; };
const nezADroite = (t) => droiteEcran(t)[2] > 1e-9;          // le nez (+Z) projeté sur la droite de l'écran
ok("ouest (θ 90°) : le nez à GAUCHE du cadre, comme le profil « left » de la planche", !nezADroite(az.west) && Math.abs(droiteEcran(az.west)[2]) > 0.99);
ok("est (θ 270°) : le nez à DROITE", nezADroite(az.east));
ok("sud (θ 0°) : la caméra sur +Z, face au modèle", cam(az.south)[2] > 0.99);
ok("orbite : attribut camera-orbit θ, φ fixe, rayon auto", D.orbite(45) === "45deg 78deg auto");

// la source : UNE fonction, deux formes (T0 : job vidéo, ou images de la Library)
ok("sourceBody images", J(D.sourceBody({ kind: "images", filenames: ["a.png", "b.png"], label: "x" })) === J({ kind: "images", filenames: ["a.png", "b.png"] }));
ok("sourceBody job", J(D.sourceBody({ kind: "job", job_id: "abc", label: "x" })) === J({ kind: "job", job_id: "abc" }));
ok("sourceBody sans source", D.sourceBody(null) === null);

// la planche : seules les entités de PERSONNAGE qui ont une planche (le backend refuse les autres en le disant)
const ents = [{ id: "1", name: "Octo", kind: "character", ref_image: "b1.png" },
              { id: "2", name: "Phare", kind: "place", ref_image: "b2.png" },
              { id: "3", name: "Nemo", kind: "character", ref_image: null },
              { id: "4", name: "Octavia", kind: "character", ref_image: "b4.png", model3d_job: "j4" }];
ok("entitesDecoupables : personnages AVEC planche", J(D.entitesDecoupables(ents, "").map((e) => e.id)) === J(["1", "4"]));
ok("entitesDecoupables : filtre sur le nom, sans casse", J(D.entitesDecoupables(ents, "OCTAV").map((e) => e.id)) === J(["4"]));
// le disque est en CRLF (autocrlf) : on découpe par blocs « "kind": { » au lieu de compter sur \n
const bs = readFileSync(new URL("../../../backend/app/services/board_service.py", import.meta.url), "utf-8");
const plans = bs.slice(bs.indexOf("PANEL_PLANS"), bs.indexOf("PANEL_PLANS") + 20000).split(/^ {4}"(\w+)": \{/m);
const composes = []; for (let i = 1; i < plans.length; i += 2) if (plans[i + 1].includes('"compose": "character"')) composes.push(plans[i]);
ok("KINDS_PLANCHE = les plans « compose: character » du backend", composes.length >= 1 && J(D.KINDS_PLANCHE) === J(composes), J(composes));

// les 8 orbites -> le corps de /assets/sprite : la MESURE de l'alpha décide du détourage
const noms = D.ORBITES.map(([n]) => `gen_dir3d_abcd1234_${n}.png`);
const b = D.corpsOrbites(noms, [], { cell: { size: 128 }, titre: "Octavia" });
ok("corps : source images, dans l'ordre des orbites", J(b.source) === J({ kind: "images", filenames: noms }));
ok("corps : rendu déjà transparent → aucun détourage", b.remove_bg === "none");
ok("corps : rendu opaque (une vue suffit) → clé chroma locale", D.corpsOrbites(noms, ["north"], {}).remove_bg === "chroma");
ok("corps : un tag d'UNE image par direction", J(b.anim.tags) === J(HUIT.map((n, i) => ({ name: n, from: i, to: i, direction: "forward" }))));
ok("corps : 8 vues gardées (max_frames ≥ 8, sinon l'échantillonnage en jetterait)", b.max_frames === 8 && b.columns === 4);
ok("corps : pixel / post seulement s'ils sont demandés", !("pixel" in b) && !("post" in b) && D.corpsOrbites(noms, [], { pixel: { target_px: 64 } }).pixel.target_px === 64);
ok("corps : titre", b.title === "Sprites · 8 directions · Octavia" && b.cell.size === 128);
ok("corps : refuse un compte de vues qui n'est pas 8", (() => { try { D.corpsOrbites(noms.slice(1), [], {}); return false; } catch (e) { return /8/.test(e.message); } })());

ok("hex8 : 8 hexadécimaux minuscules (le motif de la route)", /^[0-9a-f]{8}$/.test(D.hex8()) && D.hex8(() => 0) === "00000000" && D.hex8(() => 0.9999) === "ffffffff");

// le prompt : style par DESCRIPTEURS, jamais par un nom d'artiste (les générateurs refusent ou pastichent)
for (const mot of ["pixel art", "sprite", "solid", "background", "full body"])
  ok("PIXEL_SUFFIX dit « " + mot + " »", D.PIXEL_SUFFIX.toLowerCase().includes(mot));
const INTERDITS = ["wyspianski", "walkuski", "mucha", "moebius", "miyazaki", "rutkowski", "artstation"];
const src = readFileSync(new URL("../directions.js", import.meta.url), "utf-8").toLowerCase();
ok("aucun nom d'artiste dans le module", INTERDITS.every((n) => !src.includes(n)), INTERDITS.filter((n) => src.includes(n)));
ok("promptFinal : sujet, puces, suffixe — dans cet ordre", D.promptFinal("  an octopus walking ", ["deep sea", "palette accent #00ffcc"]) === "an octopus walking, deep sea, palette accent #00ffcc, " + D.PIXEL_SUFFIX);
ok("promptFinal : sujet vide → vide (rien n'est payé pour un suffixe seul)", D.promptFinal("   ", ["x"]) === "");
ok("corpsPrompt : n borné à 1..4, source « sprites »", J(D.corpsPrompt("octo", [], 9, "square_hd")) === J({ prompt: D.promptFinal("octo", []), n: 4, size: "square_hd", source: "sprites" }) && D.corpsPrompt("octo", [], 0, "x").n === 1);
const p = { vibe_keywords: Array.from({ length: 15 }, (_, i) => "k" + i), brand_colors: { a: "#112233", b: "#445566" } };
const pu = D.puces(p);
ok("puces : 12 mots-clés au plus, puis une puce par couleur de marque", pu.length === 14 && pu[0].v === "k0" && pu[12].v === "palette accent #112233" && pu[12].couleur === true);
ok("puces : persona vide → aucune", J(D.puces({})) === "[]" && J(D.puces(null)) === "[]");

if (echecs.length) { console.log("ÉCHECS :\n  " + echecs.join("\n  ")); process.exit(1); }
console.log("PASS directions.test.mjs");
