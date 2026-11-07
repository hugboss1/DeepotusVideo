// qa/taches-n9.test.mjs — t419 (Photolab N9, photocraft 0.21) : progression et annulation des longues opérations.
// Fonctions PURES ; le moteur est prouvé par backend/tests/test_photolab_n9.py.
import { estTacheLongue, pctTache, issueTache, suivre, DELAI_BARRE } from "../js/mod-taches.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const py = readFileSync(new URL("../../../backend/app/api/photolab_routes.py", import.meta.url), "utf8");
const cycle = readFileSync(new URL("../js/mod-cycle.js", import.meta.url), "utf8");

check("1.1 filtres et remplissage d'après le contenu", estTacheLongue("filter.blur.gaussianBlur") && estTacheLongue("edit.contentAwareFill") && estTacheLongue("edit.contentAwareScale"));
check("1.2 le reste ne passe pas par là", !estTacheLongue("layer.new.layer") && !estTacheLongue("image.adjustments.invert") && !estTacheLongue(undefined));
check("1.3 pourcentage borné", pctTache({ progress: 0.688 }) === 69 && pctTache({ progress: 3 }) === 100 && pctTache({}) === 0);
check("1.4 en cours : rien", issueTache({ state: "running" }) === null);
check("1.5 fini : le résultat", eq(issueTache({ state: "done", result: { layer: 2 } }), { ok: true, r: { layer: 2 } }));
check("1.6 annulé", eq(issueTache({ state: "cancelled" }), { ok: false, annule: true }));
check("1.7 échec : le message", eq(issueTache({ state: "failed", error: "x" }), { ok: false, erreur: "x" }));

async function joue(etats, pas) {
  const vus = [], lectures = []; let t = 0, i = 0;
  const fin = await suivre(7, { lire: async (n) => { lectures.push(n); return etats[Math.min(i++, etats.length - 1)]; }, attendre: async (ms) => { t += pas ?? ms; }, maintenant: () => t, montrer: (p) => vus.push(p) });
  return { fin, vus, lectures };
}
const run = (p) => ({ state: "running", progress: p });
let r = await joue([run(0.1), { state: "done", result: 1 }]);
check("2.1 une tâche brève : pas de barre", eq(r.vus, []) && r.fin.ok === true, r);
r = await joue([run(0.1), run(0.2), run(0.5), run(0.8), { state: "done", result: 1 }]);
check("2.2 une tâche longue : la barre après le délai", eq(r.vus, [50, 80]) && DELAI_BARRE === 400, r.vus);
check("2.3 la bonne tâche est lue", r.lectures.every((n) => n === 7));
r = await joue([run(0.1), { state: "cancelled" }]);
check("2.4 annulation rendue", r.fin.annule === true);
const panne = await suivre(1, { lire: async () => { throw new Error("moteur perdu"); }, attendre: async () => {}, maintenant: () => 0, montrer: () => {} });
check("2.5 lecture impossible : on s'arrête en le disant", eq(panne, { ok: false, erreur: "moteur perdu" }));

check("3.1 les routes existent", py.includes('@router.get("/taches/{job}")') && py.includes('@router.post("/taches/{job}/annuler")'));
check("3.2 PL.executer passe par la tâche de fond", cycle.includes("estTacheLongue(command)") && cycle.includes("if (longue && r && r.job != null)") && cycle.includes("await PL.suivreTache(r.job)"));
for (const c of ["photolab.tache.calcul", "photolab.tache.annulee", "photolab.tache.echec"]) check(`3.3 ${c} fr et en`, dico[c]?.fr && dico[c]?.en, c);

console.log(`taches-n9 : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
