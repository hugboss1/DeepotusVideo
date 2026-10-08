// qa/apropos.test.mjs — t140 (P5) : « À propos du Photolab » — crédits et licences livrées (GET /api/photolab/licences).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { contenuApropos, libelleLicence } from "../js/mod-apropos.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const dico = JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8"));
const fr = (c, v) => { const s = dico[c] ? dico[c].fr : c; return s.replace(/\{(\w+)\}/g, (_, k) => (v && k in v ? v[k] : "{" + k + "}")); };
const en = (c, v) => { const s = dico[c] ? dico[c].en : c; return s.replace(/\{(\w+)\}/g, (_, k) => (v && k in v ? v[k] : "{" + k + "}")); };

const INFO = { version: "0.3.0", depot: "storytold/photocraft", licence: "MIT OR Apache-2.0",
  fichiers: ["NOTICE-photocraft.txt", "licences-photocraft/LICENSE-SCOWL.txt", "licences-photocraft/LICENSE-lucide.txt",
    "licences-photocraft/NOTICE", "licences-photocraft/OFL-Inter.txt", "licences-photocraft/OFL-JetBrainsMono.txt",
    "LICENSE-APACHE", "LICENSE-MIT", "OFL-biz-ud-mincho.txt", "OFL-biz-ud-pgothic.txt", "OFL-shippori-mincho.txt"] };

// 1. libellés lisibles, jamais de nom de fichier brut pour une licence connue
const attendus = {
  "NOTICE-photocraft.txt": "Composants tiers",
  "licences-photocraft/NOTICE": "Mentions requises par photocraft",
  "LICENSE-MIT": "photocraft — licence MIT",
  "LICENSE-APACHE": "photocraft — licence Apache 2.0",
  "licences-photocraft/OFL-Inter.txt": "Police Inter — SIL OFL 1.1",
  "licences-photocraft/OFL-JetBrainsMono.txt": "Police JetBrains Mono — SIL OFL 1.1",
  "OFL-biz-ud-mincho.txt": "Police BIZ UDMincho — SIL OFL 1.1",
  "OFL-biz-ud-pgothic.txt": "Police BIZ UDPGothic — SIL OFL 1.1",
  "OFL-shippori-mincho.txt": "Police Shippori Mincho — SIL OFL 1.1",
  "licences-photocraft/LICENSE-SCOWL.txt": "Liste de mots SCOWL — licence SCOWL",
  "licences-photocraft/LICENSE-lucide.txt": "Icônes Lucide — licence ISC",
};
for (const [nom, lib] of Object.entries(attendus)) check("1.1 " + nom, libelleLicence(nom, fr) === lib, libelleLicence(nom, fr));
check("1.2 en anglais aussi", libelleLicence("LICENSE-MIT", en) === "photocraft — MIT license" && libelleLicence("OFL-Inter.txt", en) === "Inter font — SIL OFL 1.1",
  [libelleLicence("LICENSE-MIT", en), libelleLicence("OFL-Inter.txt", en)]);
check("1.3 un fichier inconnu garde son nom", libelleLicence("AUTRE.txt", fr) === "AUTRE.txt");

// 2. le contenu du dialogue
const c = contenuApropos(INFO, fr);
check("2.1 titre", c.titre === "Photolab, d'après photocraft", c.titre);
check("2.2 le moteur : version, licence, dépôt", c.lignes[0].includes("0.3.0") && c.lignes[0].includes("MIT") && c.lignes[0].includes("Apache"),
  c.lignes[0]);
check("2.3 le lien du dépôt", c.depot === "https://github.com/storytold/photocraft", c.depot);
check("2.4 crédits : icônes, polices, liste de mots, catalogue des menus", c.lignes.join(" ").includes("Lucide")
  && c.lignes.join(" ").includes("polices") && c.lignes.join(" ").includes("SCOWL") && c.lignes.join(" ").includes("menus"), c.lignes);
check("2.5 les licences : toutes, notre NOTICE d'abord, puis les mentions amont", c.licences.length === 11
  && c.licences[0].nom === "NOTICE-photocraft.txt" && c.licences[1].nom === "licences-photocraft/NOTICE", c.licences.map((l) => l.nom));
check("2.6 chaque licence porte son adresse de lecture", c.licences.every((l) => l.url === "/api/photolab/licences/" + l.nom.split("/").map(encodeURIComponent).join("/")));
check("2.7 pont injoignable : le dialogue garde les crédits, sans liste", (() => { const d = contenuApropos(null, fr); return d.lignes.length >= 3 && d.licences.length === 0 && d.lignes[0].includes("photocraft"); })());
check("2.8 aucune marque ArtCraft ni Photoshop", !/artcraft|photoshop/i.test(JSON.stringify([c, contenuApropos(INFO, en)])));

// 3. câblage
const menus = readFileSync(join(racine, "js/mod-menus.js"), "utf8"), core = readFileSync(join(racine, "js/core.js"), "utf8");
check("3.1 le menu Aide ouvre PL.apropos (remplaçable par le module)", /case "apropos": PL\.apropos\(\); break;/.test(menus));
check("3.2 initApropos branché après les menus", /import \{ initApropos \} from "\.\/mod-apropos\.js";/.test(core)
  && core.indexOf("initApropos(PL);") > core.indexOf("initMenus(PL);"));

console.log(`apropos : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
