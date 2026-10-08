// envoi.test.mjs — t139 (Photolab P4) : « Envoyer vers › Vectorlab » crée un document à la taille de l'image et la
// pose. La logique PURE de mod-envoi (taille du document, corps de la création, adresse de la suite) ; le DOM n'entre
// pas ici.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { tailleDoc, corpsCreation, suite, COTE_MAX } from "../js/mod-envoi.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

// 1. la taille : celle de l'image, ramenée sous 8192 px de côté en gardant le rapport (borne de la création)
ok("1.1 image ordinaire : sa taille", JSON.stringify(tailleDoc(1920, 1080)) === '{"w":1920,"h":1080}');
ok("1.2 côté > 8192 : ramené, rapport gardé", (() => { const t = tailleDoc(16384, 4096); return t.w === COTE_MAX && t.h === 2048; })(),
  JSON.stringify(tailleDoc(16384, 4096)));
ok("1.3 portrait géant", (() => { const t = tailleDoc(3000, 30000); return t.h === COTE_MAX && t.w === 819; })(), JSON.stringify(tailleDoc(3000, 30000)));
ok("1.4 jamais 0 px", tailleDoc(1, 100000).w === 1);
for (const [w, h] of [[0, 10], [NaN, 10], [-5, 10], [10, Infinity]])
  ok("1.5 dimensions illisibles -> erreur " + JSON.stringify([w, h]), (() => { try { tailleDoc(w, h); return false; } catch (e) { return true; } })());

// 2. le corps de POST /api/vector/docs : nom tiré du fichier (sans extension), rôle libre, document vierge en px
const c = corpsCreation("photolab_20261008-154030_herbe.png", 640, 480);
ok("2.1 nom sans extension ni préfixe d'enregistrement", c.name === "herbe", c.name);
ok("2.2 rôle libre", c.role === "libre");
ok("2.3 document vierge à la taille, nom repris", c.doc && c.doc.taille.w === 640 && c.doc.taille.h === 480 && c.doc.nom === "herbe"
  && c.doc.calques.length === 1 && c.doc.calques[0].objets.length === 0, JSON.stringify(c.doc));
ok("2.4 nom ordinaire", corpsCreation("Mon image.jpg", 10, 10).name === "Mon image");
ok("2.5 nom trop long tronqué à 120", corpsCreation("x".repeat(300) + ".png", 10, 10).name.length === 120);

// 3. la suite : ouvrir le document créé avec l'image à poser (?doc=…&img=…), noms encodés
ok("3.1 adresse de la suite", suite("ab 12", "a b.png") === "?doc=ab%2012&img=a%20b.png", suite("ab 12", "a b.png"));

// 4. câblage : charger() reçoit l'envoi avant la page d'accueil, et pose l'image une fois le document chargé
const core = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../js/core.js"), "utf8");
const ch = core.slice(core.indexOf("async function charger()"), core.indexOf("function majTete()"));
ok("4.1 sans ?doc : l'envoi d'abord, la bibliothèque sinon", /if \(await VL\.recevoirEnvoi\(\)\) return;\s*\/\/[^\n]*\n\s*VL\.ouvrirBiblio\(\);/.test(ch), ch.slice(0, 400));
const appel = /^\s*VL\.poserEnvoi\(\);/m.exec(ch);
ok("4.2 avec ?doc : l'image posée APRÈS le chargement du document (un vrai appel, pas un commentaire)",
  appel !== null && appel.index > ch.indexOf("VL.surCharge()"));
ok("4.3 initEnvoi branché", /initEnvoi\(VL\);/.test(core) && /import \{ initEnvoi \} from "\.\/mod-envoi\.js";/.test(core));

if (echecs.length) { console.error("envoi : " + echecs.length + " échec(s)\n  " + echecs.join("\n  ")); process.exit(1); }
console.log("envoi : ok");
