// qa/api.test.mjs — fonctions pures de mod-api.js : traduction des erreurs, suivi de génération.
import { messageErreur, memeGeneration, detailDe } from "../js/mod-api.js";

let ko = 0;
function check(label, cond, detail = "") { if (!cond) { ko++; console.error("ECHEC :", label, detail); } }

const t = (c) => c;
check("409 -> occupé", messageErreur(409, null, t) === "photolab.moteur.occupe");
check("503 -> absent", messageErreur(503, { detail: "binaire manquant" }, t) === "photolab.moteur.absent binaire manquant");
check("504 -> délai", messageErreur(504, null, t) === "photolab.moteur.delai");
check("422 -> refus + détail", messageErreur(422, { detail: [{ msg: "x" }, { msg: "y" }] }, t) === "photolab.moteur.refuse x ; y");
check("500 -> détail brut", messageErreur(500, { detail: "boum" }, t) === "boum");
check("500 sans détail", messageErreur(500, null, t) === "photolab.moteur.erreur (500)");
check("detailDe tronque", detailDe({ detail: "a".repeat(500) }).length === 300);
check("même génération", memeGeneration("3", 3) && memeGeneration(null, "4") && !memeGeneration("3", "4"));

if (ko) process.exit(1);
console.log("api : ok");
