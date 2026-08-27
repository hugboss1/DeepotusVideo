// historique.test.mjs — l'annulation (T1.5) : pile d'INSTANTANÉS du JSON,
// pure et sans partage de référence. capturer() AVANT chaque commande ;
// annuler/refaire échangent l'état courant contre le sommet des piles.
import { Historique } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 140) : ""));
};
const J = (x) => JSON.stringify(x);

const d0 = { v: 1, nom: "a", taille: { w: 1, h: 1 }, calques: [] };

// annuler rend exactement l'état capturé ; refaire rend l'état d'avant l'annulation
{
  const h = new Historique();
  ok("rien à annuler au départ", !h.peutAnnuler() && !h.peutRefaire());
  const doc = JSON.parse(J(d0));
  h.capturer(doc);                 // instantané AVANT la commande
  doc.nom = "b";
  ok("annulable après capture", h.peutAnnuler());
  const avant = h.annuler(doc);    // rend l'état capturé
  ok("annuler == état capturé", J(avant) === J(d0), J(avant));
  ok("refaire disponible", h.peutRefaire());
  const apres = h.refaire(avant);
  ok("refaire == état muté", apres.nom === "b");
}

// une nouvelle capture invalide la pile refaire
{
  const h = new Historique();
  const doc = JSON.parse(J(d0));
  h.capturer(doc); doc.nom = "b";
  const avant = h.annuler(doc);
  h.capturer(avant); avant.nom = "c";
  ok("nouvelle commande invalide refaire", !h.peutRefaire());
}

// aucun partage de référence : muter ce qui est rendu ne corrompt pas la pile
{
  const h = new Historique();
  const doc = JSON.parse(J(d0));
  h.capturer(doc); doc.nom = "b";
  h.capturer(doc); doc.nom = "c";
  const un = h.annuler(doc);       // état "b"
  un.nom = "MUTILE";
  const deux = h.annuler(un);      // état "a" — intact malgré la mutation
  ok("instantanés clonés", J(deux) === J(d0), J(deux));
}

// cap : les plus anciens instantanés tombent
{
  const h = new Historique(3);
  const doc = JSON.parse(J(d0));
  for (let i = 1; i <= 5; i++) { h.capturer(doc); doc.nom = "n" + i; }
  let n = 0;
  let cur = doc;
  while (h.peutAnnuler()) { cur = h.annuler(cur); n++; }
  ok("cap 3 : trois annulations possibles", n === 3, String(n));
  ok("le plus ancien restant est n2", cur.nom === "n2", cur.nom);
}

if (echecs.length) {
  console.error("ECHECS historique :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA historique : PASS (9 controles)");
