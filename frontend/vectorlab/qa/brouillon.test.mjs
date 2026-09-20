// brouillon.test.mjs — le brouillon (lot A) : clé par document, contenu
// cloné, pertinence (même document, même version serveur, contenu DIFFÉRENT
// du serveur), libellé horaire. L'état vide (aucun brouillon) est construit.
import { BROUILLON_PERIODE_MS, brouillon_cle, brouillon_faire,
         brouillon_pertinent, brouillon_libelle } from "../js/mod-brouillon.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const doc = { v: 1, taille: { w: 1, h: 1 }, calques: [{ id: "c", objets: [] }] };

ok("période : 30 s", BROUILLON_PERIODE_MS === 30000);
ok("clé par document", brouillon_cle("ab12") === "dz_vl_brouillon_ab12");
{
  const b = brouillon_faire("ab12", 3, doc, 1700000000000);
  ok("brouillon : docId, version, t, doc cloné", b.docId === "ab12" && b.version === 3
     && b.t === 1700000000000 && b.doc !== doc && JSON.stringify(b.doc) === JSON.stringify(doc));
  const meta = { id: "ab12", version: 3 };
  ok("état vide : null n'est pas pertinent", brouillon_pertinent(null, meta, doc) === false);
  ok("identique au serveur : pas pertinent", brouillon_pertinent(b, meta, doc) === false);
  const modif = JSON.parse(JSON.stringify(doc)); modif.calques[0].objets.push({ id: "o1", type: "rect", x: 0, y: 0, w: 1, h: 1 });
  const b2 = brouillon_faire("ab12", 3, modif, 1);
  ok("différent du serveur, même version : PERTINENT", brouillon_pertinent(b2, meta, doc) === true);
  ok("autre version serveur (sauvé ailleurs depuis) : pas pertinent",
     brouillon_pertinent(b2, { id: "ab12", version: 4 }, doc) === false);
  ok("autre document : pas pertinent", brouillon_pertinent(b2, { id: "zz", version: 3 }, doc) === false);
  ok("brouillon corrompu (sans doc) : pas pertinent", brouillon_pertinent({ docId: "ab12", version: 3 }, meta, doc) === false);
  ok("libellé : heure lisible", /brouillon du \d{2}:\d{2}/.test(brouillon_libelle(b)), brouillon_libelle(b));
}

if (echecs.length) {
  console.error("ECHECS brouillon :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA brouillon : PASS (10 controles)");
