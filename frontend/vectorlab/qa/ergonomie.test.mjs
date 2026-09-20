// ergonomie.test.mjs — mod-controles : curseur (valeur ↔ position, pas),
// rangée à largeurs égales, et l'AUDIT d'ergonomie qui juge des mesures DOM
// (relevées in-page par VL.ergonomie.mesurer) : débordement, contrôles < 28 px,
// boutons inégaux, natifs interdits. Le DOM est mesuré dans la page ; ici on
// bance le jugement.
import { curseur_valeur, curseur_pas, curseur_position, rangee_largeurs, auditer } from "../js/mod-controles.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : "")); };
{
  ok("valeur : milieu de piste = milieu d'échelle, bornée, arrondie au pas", curseur_valeur(50, 100, { min: 0, max: 100, step: 1 }) === 50 && curseur_valeur(-10, 100, { min: 0, max: 1, step: 0.05 }) === 0 && curseur_valeur(37, 100, { min: 0, max: 1, step: 0.05 }) === 0.35 && curseur_valeur(999, 100, { min: 1, max: 60, step: 1 }) === 60);
  ok("état vide : piste de largeur 0 → min", curseur_valeur(10, 0, { min: 2, max: 8, step: 1 }) === 2);
  ok("position : fraction de la valeur sur l'échelle, bornée", curseur_position(0.5, { min: 0, max: 1 }) === 0.5 && curseur_position(-5, { min: 0, max: 10 }) === 0 && curseur_position(3, { min: 3, max: 3 }) === 0);
  ok("pas : ±step, Maj ×10, borné, arrondi au pas", curseur_pas(0.5, +1, { min: 0, max: 1, step: 0.05 }) === 0.55 && curseur_pas(0.5, -1, { min: 0, max: 1, step: 0.05 }, true) === 0 && curseur_pas(99, +1, { min: 0, max: 100, step: 1 }, true) === 100 && curseur_pas(0.1 + 0.2, +1, { min: 0, max: 1, step: 0.1 }) === 0.4);
  ok("rangée : n largeurs égales à ±1 px qui remplissent la place", JSON.stringify(rangee_largeurs(3, 200, 8)) === JSON.stringify([62, 61, 61]) && rangee_largeurs(0, 200, 8).length === 0 && rangee_largeurs(1, 100, 8)[0] === 100);
  const mesures = [
    { id: "l1", panneau: "#panneauPixel", scrollWidth: 240, clientWidth: 240, controles: [{ tag: "vl-curseur", h: 28, w: 120 }], boutons: [] },
    { id: "l2", panneau: "#panneauPixel", scrollWidth: 262, clientWidth: 240, controles: [], boutons: [{ w: 90 }, { w: 40 }] },
    { id: "l3", panneau: "#panneauApparence2", scrollWidth: 240, clientWidth: 240, controles: [{ tag: "input", type: "range", h: 20, w: 100 }, { tag: "input", type: "checkbox", h: 13, w: 13 }], boutons: [{ w: 60 }, { w: 61 }, { w: 60 }] },
  ];
  const v = auditer(mesures);
  ok("audit : déborde (l2), boutons inégaux (l2), natif range + checkbox (l3), contrôle < 28 px (l3 ×2), l1 propre", v.length === 6 && v.filter((x) => x.ligne === "l1").length === 0 && v.some((x) => x.ligne === "l2" && x.type === "deborde") && v.some((x) => x.ligne === "l2" && x.type === "inegal") && v.filter((x) => x.ligne === "l3" && x.type === "natif").length === 2 && v.filter((x) => x.ligne === "l3" && x.type === "petit").length === 2, JSON.stringify(v));
  ok("audit : ±1 px de tolérance sur le débordement et les largeurs", auditer([{ id: "t", panneau: "p", scrollWidth: 241, clientWidth: 240, controles: [], boutons: [{ w: 50 }, { w: 51 }] }]).length === 0);
  ok("état vide : aucune mesure → aucune violation", auditer([]).length === 0 && auditer(null).length === 0);
}
if (echecs.length) { console.error("ECHECS ergonomie :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA ergonomie : PASS (8 controles)");
