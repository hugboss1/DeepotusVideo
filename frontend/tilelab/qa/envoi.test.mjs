// envoi.test.mjs — t139 (Photolab P4) : « Envoyer vers › Tile Lab » choisit l'image comme source de la tuile.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { appliquer } from "../envoi.js";

const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");

const choisies = [];
const tl = { select: (fn) => choisies.push(fn) };
ok("1.1 une image reçue devient la source (poignée __tl.select de tilelab.js)", appliquer({ image: "herbe.png", via: "envoi" }, tl) === true
  && JSON.stringify(choisies) === '["herbe.png"]', JSON.stringify(choisies));
ok("1.2 rien de reçu : rien choisi", appliquer(null, tl) === false && choisies.length === 1);
ok("1.3 Tile Lab pas prêt (pas de poignée) : rien, sans lever", appliquer({ image: "a.png" }, undefined) === false && appliquer({ image: "a.png" }, {}) === false);

const html = readFileSync(join(racine, "index.html"), "utf-8");
const iEnvoi = html.indexOf('<script type="module" src="envoi.js"></script>'), iTl = html.indexOf('<script src="tilelab.js"></script>');
ok("2.1 envoi.js chargé en module APRÈS tilelab.js (la poignée __tl existe quand il s'exécute)", iEnvoi > iTl && iTl > 0, [iTl, iEnvoi]);
const src = readFileSync(join(racine, "envoi.js"), "utf-8");
ok("2.2 le contrat partagé, pour la cible tilelab", /from "\.\.\/shared\/dz-envoi\.js"/.test(src) && /recevoir\("tilelab"\)/.test(src));
const tl_js = readFileSync(join(racine, "tilelab.js"), "utf-8");
const sel = tl_js.slice(tl_js.indexOf("  select(fn) {"), tl_js.indexOf("  run,", tl_js.indexOf("  select(fn) {")));
ok("2.3 select redessine la grille quand la liste est chargée (la vignette envoyée est surlignée)",
  /if \(libImages\.length\) renderImgGrid\(\);/.test(sel), sel);

if (echecs.length) { console.error("envoi : " + echecs.length + " échec(s)\n  " + echecs.join("\n  ")); process.exit(1); }
console.log("envoi tilelab : ok");
