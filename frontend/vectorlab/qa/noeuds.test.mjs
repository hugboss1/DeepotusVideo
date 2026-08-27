// noeuds.test.mjs — édition de nœuds Bézier (T1.3) : lecture des ancres,
// déplacement (les poignées C attachées suivent), conversion angle↔courbe
// (poignées symétriques déduites des voisins, fermé-conscient), suppression
// d'ancre, fermeture de chemin. Toutes les valeurs sont FIGÉES ici.
import { chemin_parser, chemin_ancres, op_noeud_deplacer, op_noeud_convertir,
         op_noeud_supprimer, op_chemin_fermer } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

const D0 = "M 0 0 L 100 0 C 100 50 50 100 0 100 Z";
const banc = () => ({
  v: 1, nom: "Banc", taille: { w: 200, h: 200 },
  calques: [{ id: "c1", nom: "l", visible: true, verrou: false, objets: [
    { id: "p1", type: "path", d: D0, style: {} },
  ] }],
});
const dDe = (d) => d.calques[0].objets[0].d;

// ── lecture des ancres : point + poignées entrante/sortante ──
{
  const a = chemin_ancres(chemin_parser(D0));
  ok("3 ancres", a.length === 3, JSON.stringify(a.map(x => [x.x, x.y])));
  ok("ancre1 = (100,0), sortante (100,50)",
     a[1].x === 100 && a[1].y === 0
     && a[1].sortante && a[1].sortante.x === 100 && a[1].sortante.y === 50);
  ok("ancre2 = (0,100), entrante (50,100), pas de sortante",
     a[2].x === 0 && a[2].y === 100
     && a[2].entrante && a[2].entrante.x === 50 && a[2].entrante.y === 100
     && !a[2].sortante);
}

// ── déplacer une ancre : la géométrie ET les poignées attachées suivent ──
{
  const d = banc();
  op_noeud_deplacer(d, "p1", 1, 10, 20);
  ok("déplacer ancre1 (le C suivant suit)",
     dDe(d) === "M 0 0 L 110 20 C 110 70 50 100 0 100 Z", dDe(d));
}
{
  const d = banc();
  op_noeud_deplacer(d, "p1", 0, 5, 5);
  ok("déplacer ancre0 (M)",
     dDe(d) === "M 5 5 L 100 0 C 100 50 50 100 0 100 Z", dDe(d));
}

// ── convertir angle → courbe : poignées ± (suivant−précédent)/4 ──
{
  const d = banc();
  op_noeud_convertir(d, "p1", 1);
  ok("angle→courbe sur ancre1",
     dDe(d) === "M 0 0 C 0 0 100 -25 100 0 C 100 25 50 100 0 100 Z", dDe(d));
}

// ── convertir courbe → angle : poignées dégénérées sur l'ancre ──
{
  const d = banc();
  op_noeud_convertir(d, "p1", 2);
  ok("courbe→angle sur ancre2",
     dDe(d) === "M 0 0 L 100 0 C 100 50 0 100 0 100 Z", dDe(d));
  // re-convertir : fermé-conscient (le suivant de la dernière = la première)
  op_noeud_convertir(d, "p1", 2);
  ok("angle→courbe fermé-conscient",
     dDe(d) === "M 0 0 L 100 0 C 100 50 25 100 0 100 Z", dDe(d));
}

// ── supprimer une ancre ──
{
  const d = banc();
  op_noeud_supprimer(d, "p1", 1);
  ok("supprimer ancre1 (le C suivant devient L)",
     dDe(d) === "M 0 0 L 0 100 Z", dDe(d));
}
{
  const d = banc();
  op_noeud_supprimer(d, "p1", 0);
  ok("supprimer ancre0 (le suivant devient M)",
     dDe(d) === "M 100 0 C 100 50 50 100 0 100 Z", dDe(d));
}

// ── fermer un chemin (idempotent) ──
{
  const d = banc();
  d.calques[0].objets[0].d = "M 0 0 L 10 10";
  op_chemin_fermer(d, "p1");
  ok("fermer", dDe(d) === "M 0 0 L 10 10 Z", dDe(d));
  op_chemin_fermer(d, "p1");
  ok("fermer idempotent", dDe(d) === "M 0 0 L 10 10 Z", dDe(d));
}

if (echecs.length) {
  console.error("ECHECS noeuds :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA noeuds : PASS (10 controles)");
