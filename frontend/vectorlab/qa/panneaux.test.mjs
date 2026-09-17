// panneaux.test.mjs — mod-panneaux : l'état ouvert / replié des sections
// du panneau de droite, par id, relu et écrit en JSON (localStorage côté
// UI), défauts sûrs, application à une liste d'objets {id, open}. Feuille.
import { PANNEAUX_DEFAUT, etat_lire, etat_poser, etat_serialiser, appliquer } from "../js/mod-panneaux.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
{
  ok("défauts : Apparence et Calques ouverts, Carte réelle et Bibliothèque repliées", PANNEAUX_DEFAUT.styleDetails === true && PANNEAUX_DEFAUT.calquesDetails === true && PANNEAUX_DEFAUT.carteDetails === false && PANNEAUX_DEFAUT.assetsDetails === false);
  const e = etat_lire('{"styleDetails":false,"zz":true,"carteDetails":"oui"}');
  ok("lire : fusionne sur les défauts, ignore les ids inconnus et les valeurs non booléennes", e.styleDetails === false && e.zz === undefined && e.carteDetails === false && e.calquesDetails === true, JSON.stringify(e));
  ok("état vide : JSON illisible, vide ou null → défauts", etat_lire("{oops").styleDetails === true && etat_lire("").calquesDetails === true && etat_lire(null).carteDetails === false);
  const e2 = etat_poser(e, "carteDetails", true);
  ok("poser : nouvel objet, l'ancien intact", e2.carteDetails === true && e.carteDetails === false);
  ok("poser un id inconnu : refusé", (() => { try { etat_poser(e, "zz", true); return false; } catch { return true; } })());
  ok("sérialiser → JSON relisible", etat_lire(etat_serialiser(e2)).carteDetails === true);
  const details = [{ id: "styleDetails", open: true }, { id: "carteDetails", open: false }, { id: "inconnu", open: false }];
  appliquer(e2, details);
  ok("appliquer : les details connus prennent l'état, l'inconnu reste tel quel", details[1].open === true && details[2].open === false && details[0].open === (e2.styleDetails));
  ok("appliquer avec un état où Apparence est repliée", (() => { const d = [{ id: "styleDetails", open: true }]; appliquer(etat_poser(e2, "styleDetails", false), d); return d[0].open === false; })());
}
if (echecs.length) {
  console.error("ECHECS panneaux :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA panneaux : PASS (8 controles)");
