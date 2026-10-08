// qa/natif.test.mjs — t140 (P5, D10) : le repli « app native » dans le menu Fichier.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { construireMenus, REFUSES, TRAITES_PAR_ECRAN, NECESSITE_DOC, actionEntree } from "../js/mod-menus.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const dico = JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8"));
const catalogue = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));
const t = (c) => (dico[c] ? dico[c].fr : c), tEn = (c) => (dico[c] ? dico[c].en : c);
const f = construireMenus(catalogue, [], REFUSES, "fr", t)[0].entrees;
const fEn = construireMenus(catalogue, [], REFUSES, "en", tEn)[0].entrees;
const k = (id, l = f) => l.findIndex((e) => e.id === id);

// 1. les deux entrées, juste après « Envoyer vers… », avant le séparateur d'Exporter
check("1.1 ordre : Envoyer vers…, Ouvrir dans l'app native…, Reprendre depuis l'app native",
  k("pl.natif.ouvrir") === k("pl.envoyer") + 1 && k("pl.natif.reprendre") === k("pl.envoyer") + 2, [k("pl.envoyer"), k("pl.natif.ouvrir"), k("pl.natif.reprendre")]);
check("1.2 puis le séparateur qui précède Exporter", f[k("pl.natif.reprendre") + 1] && f[k("pl.natif.reprendre") + 1].type === "separateur");
check("1.3 libellés fr", f[k("pl.natif.ouvrir")].libelle === "Ouvrir dans l'app native…" && f[k("pl.natif.reprendre")].libelle === "Reprendre depuis l'app native",
  [f[k("pl.natif.ouvrir")].libelle, f[k("pl.natif.reprendre")].libelle]);
check("1.4 libellés en", fEn[k("pl.natif.ouvrir", fEn)].libelle === "Open in the native app…" && fEn[k("pl.natif.reprendre", fEn)].libelle === "Bring back from the native app");
check("1.5 traitées par l'écran", TRAITES_PAR_ECRAN.has("pl.natif.ouvrir") && TRAITES_PAR_ECRAN.has("pl.natif.reprendre")
  && actionEntree(f[k("pl.natif.ouvrir")]) === "ecran" && actionEntree(f[k("pl.natif.reprendre")]) === "ecran");
check("1.6 envoyer demande un document ; reprendre non (l'app native peut avoir le sien)",
  NECESSITE_DOC.has("pl.natif.ouvrir") && !NECESSITE_DOC.has("pl.natif.reprendre"));

// 2. les actions de l'écran : les routes, et rien d'autre
const src = readFileSync(join(racine, "js/mod-fichier.js"), "utf8");
check("2.1 actions branchées", /PL\.actions\["pl\.natif\.ouvrir"\] = natifOuvrir;/.test(src) && /PL\.actions\["pl\.natif\.reprendre"\] = natifReprendre;/.test(src));
check("2.2 ouvrir = POST /natif/ouvrir ; reprendre = POST /natif/reprendre puis le cycle de l'ouverture",
  /PL\.post\("\/natif\/ouvrir"/.test(src) && /PL\.post\("\/natif\/reprendre"[\s\S]{0,200}apresOuverture\(\)/.test(src));
for (const c of ["photolab.natif.ouvert", "photolab.natif.repris", "photolab.menu.natif_ouvrir", "photolab.menu.natif_reprendre"])
  check("3.1 " + c + " fr et en", dico[c] && dico[c].fr && dico[c].en, c);

console.log(`natif : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
