// qa/historique-nuancier-m7.test.mjs — t256 (Photolab M7 PR 2, moteur photocraft 0.10) : instantanés du panneau
// Historique (doc.inspect.snapshots) et échange du Nuancier avec un fichier .aco / .ase (routes /nuancier/importer,
// /nuancier/exporter : base64). Fonctions PURES ; formes relevées sur le vrai moteur (backend/tests/test_photolab_m7.py [5][6]).
import { readFileSync } from "node:fs";
import { instantanesDe, etatBrut, traduireEtat } from "../js/mod-historique.js";
import { FORMATS_ECHANGE, MAX_OCTETS_FICHIER, formatFichier, groupesExport, versBase64, depuisBase64, etatImporte, etatDefaut }
  from "../js/mod-nuancier.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// 1. instantanés
check("1.1 doc.inspect.snapshots -> {id, nom}", eq(instantanesDe({ snapshots: [{ id: 1, name: "Avant" }, { id: 4, name: "Fond" }] }),
  [{ id: 1, nom: "Avant" }, { id: 4, nom: "Fond" }]));
check("1.2 sans document, sans liste, entrées illisibles : rien", eq(instantanesDe(null), []) && eq(instantanesDe({}), [])
  && eq(instantanesDe({ snapshots: [{ id: "1", name: "x" }, { id: 2 }, null] }), []));
check("1.3 l'état d'un instantané choisi garde son nom (pas de traduction) -> brut", traduireEtat("Fond", null, (k) => k) === "Fond" && etatBrut("Fond", "Fond"));
check("1.4 un état traduit n'est pas brut", !etatBrut("New Layer", "Nouveau calque"));

// 2. nuancier : formats et bornes alignés sur le pont
const py = readFileSync(new URL("../../../backend/app/services/photolab_nuancier.py", import.meta.url), "utf8");
check("2.1 MAX_OCTETS_FICHIER = celui du pont", new RegExp("MAX_OCTETS_FICHIER = " + String(MAX_OCTETS_FICHIER).replace(/(\d)(?=(\d{3})+$)/g, "$1_")).test(py), MAX_OCTETS_FICHIER);
check("2.2 FORMATS_ECHANGE = ceux du pont", /FORMATS_ECHANGE = \("aco", "ase"\)/.test(py) && eq(FORMATS_ECHANGE, ["aco", "ase"]));
check("2.3 format lu à l'extension, sans casse", formatFichier("Marque.ASE") === "ase" && formatFichier("a.b.aco") === "aco"
  && formatFichier("x.gpl") === null && formatFichier("aco") === null && formatFichier("") === null);

// 3. groupes exportés : noms traduits pour les groupes fournis, groupes vides écartés
const T = (k) => "<" + k + ">";
const e = { ...etatDefaut(), groupes: [...etatDefaut().groupes.slice(0, 1), { id: "g-1", nom: "Marque", couleurs: [{ hex: "#e35d4a", nom: "Corail" }, { hex: "#5ec8a0", nom: "" }] },
  { id: "g-2", nom: "Vide", couleurs: [] }] };
const gx = groupesExport(e, T);
check("3.1 groupe fourni : son nom traduit ; groupe créé : son nom ; groupe vide écarté", gx.length === 2
  && gx[0].nom === "<photolab.nuancier.groupe_gris>" && gx[1].nom === "Marque", gx.map((g) => g.nom));
check("3.2 couleurs {hex, nom} (nom vide gardé vide)", eq(gx[1].couleurs, [{ hex: "#e35d4a", nom: "Corail" }, { hex: "#5ec8a0", nom: "" }]));
check("3.3 rien à exporter : liste vide", eq(groupesExport({ groupes: [{ id: "g-1", nom: "a", couleurs: [] }] }, T), []));

// 4. base64 aller-retour (fichiers binaires .aco / .ase)
const octets = new Uint8Array(70000); for (let i = 0; i < octets.length; i++) octets[i] = (i * 37) & 255;
const b64 = versBase64(octets);
check("4.1 base64 standard (sans saut de ligne) et aller-retour exact sur 70 000 octets",
  /^[A-Za-z0-9+/]+=*$/.test(b64) && eq(Array.from(depuisBase64(b64)), Array.from(octets)));
check("4.2 « ASEF » encodé comme le moteur l'attend", versBase64(new Uint8Array([65, 83, 69, 70])) === "QVNFRg==");

// 5. réponse de l'import
check("5.1 l'état sans le compte", eq(etatImporte({ version: 1, recentes: [], groupes: [], importees: 3 }), { version: 1, recentes: [], groupes: [] }));
check("5.2 réponse illisible : null", etatImporte(null) === null && etatImporte({ importees: 1 }) === null);

console.log(`historique-nuancier-m7 : ${ok} ok, ${ko} échec(s)`);
if (ko) process.exit(1);
