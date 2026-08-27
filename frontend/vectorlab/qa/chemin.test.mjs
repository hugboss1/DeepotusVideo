// chemin.test.mjs — le d de path est LA vérité : parseur structurant,
// sérialiseur canonique, aller-retour stable à l'octet (T1.1).
import { chemin_parser, chemin_serialiser } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 140) : ""));
};
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// 1. structure exacte M/L/C/Q/Z
ok("parse M L C Q Z", eq(chemin_parser("M 10 10 L 20 30 C 1 2 3 4 5 6 Q 7 8 9 10 Z"), [
  { c: "M", p: [10, 10] }, { c: "L", p: [20, 30] },
  { c: "C", p: [1, 2, 3, 4, 5, 6] }, { c: "Q", p: [7, 8, 9, 10] },
  { c: "Z", p: [] },
]), JSON.stringify(chemin_parser("M 10 10 L 20 30 C 1 2 3 4 5 6 Q 7 8 9 10 Z")));

// 2. round-trip canonique stable à l'octet
for (const s of ["M 10 10 L 20 30 C 1 2 3 4 5 6 Z",
                 "M 1.5 -2.25 L 3.1 4",
                 "M 40 300 Q 320 60 600 300"]) {
  ok("round-trip octet: " + s, chemin_serialiser(chemin_parser(s)) === s,
     chemin_serialiser(chemin_parser(s)));
}

// 3. lecture tolérante : virgules, commandes implicites (paires après M = L,
//    répétition après L/C/Q), puis canonisation
ok("virgules + implicites",
   chemin_serialiser(chemin_parser("M10,10 20,30 L40,40 50,60")) ===
   "M 10 10 L 20 30 L 40 40 L 50 60");
ok("C implicite répété",
   chemin_serialiser(chemin_parser("C 1 2 3 4 5 6 7 8 9 10 11 12")) ===
   "C 1 2 3 4 5 6 C 7 8 9 10 11 12");

// 4. canonisation des nombres (zéros traînants, arrondi 2 décimales)
ok("nombres canoniques",
   chemin_serialiser(chemin_parser("M 3.10 4.000 L 1.005 2")) ===
   "M 3.1 4 L 1.01 2");

// 5. refus nets : relatif, arité fausse, commande inconnue
let refus = 0;
for (const mauvais of ["M 10 10 l 5 5", "C 1 2 3", "M 1 2 T 3 4", "X 1 2"]) {
  try { chemin_parser(mauvais); } catch { refus++; }
}
ok("refus relatif/arité/commande", refus === 4, String(refus));

if (echecs.length) {
  console.error("ECHECS chemin :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA chemin : PASS (9 controles)");
