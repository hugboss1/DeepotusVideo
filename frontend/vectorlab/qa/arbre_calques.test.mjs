// arbre_calques.test.mjs — mod-layers : l'ARBRE du panneau Calques (pur) —
// calques (dessus en haut), leurs objets, les enfants de groupe, l'enfant
// d'écrêtage marqué « Masque d'écrêtage », les sous-rangées « Masque de
// transparence » et « Effets (n) », le repli par calque, une icône par rangée.
import { arbre_calques, icone_objet } from "../js/mod-layers.js";
import { ICONES } from "../js/mod-icones.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
{
  const doc = { calques: [
    { id: "c1", nom: "Fond", visible: true, objets: [
      { id: "r1", type: "rect", style: {} },
      { id: "g1", type: "groupe", nom: "Badge", clip: "p1", enfants: [{ id: "e1", type: "ellipse", style: {} }, { id: "p1", type: "path", style: {} }] },
    ] },
    { id: "c2", nom: "pixel", visible: true, objets: [
      { id: "o1", type: "image", href: "img1.png", style: { masque: "grad:g1", effets: [{ type: "ombre" }] } },
    ] },
  ] };
  const a = arbre_calques(doc, "c2", new Set());
  const lig = (r) => `${r.niveau}:${r.genre}:${r.id}${r.actif ? "*" : ""}`;
  ok("ordre d'affichage : le calque pixel (actif) en haut, l'image, son masque et ses effets ; puis Fond, le groupe, l'écrêtage, l'ellipse, le rect",
     a.map(lig).join(" | ") === "0:calque:c2* | 1:objet:o1 | 2:masque:o1 | 2:effet:o1 | 0:calque:c1 | 1:objet:g1 | 2:ecretage:p1 | 2:objet:e1 | 1:objet:r1", a.map(lig).join(" | "));
  ok("libellés : Masque de transparence, Effets (1), Masque d'écrêtage, nom du groupe, type · id sinon",
     a[2].nom === "Masque de transparence" && a[3].nom === "Effets (1)" && a[6].nom === "Masque d'écrêtage" && a[5].nom === "Badge" && a[8].nom === "rect · r1", a.map((r) => r.nom).join(" | "));
  ok("chaque rangée porte une icône connue d'ICONES et son calque", a.every((r) => ICONES[r.icone] && r.calque));
  const b = arbre_calques(doc, "c2", new Set(["c1"]));
  ok("plié : les rangées de Fond disparaissent, le calque reste, marqué plie", b.length === 5 && b[4].id === "c1" && b[4].plie === true && !b[0].plie, b.map(lig).join(" | "));
  ok("état vide : doc null / sans calques → []", arbre_calques(null, "x", new Set()).length === 0 && arbre_calques({ calques: [] }, "x", new Set()).length === 0);
  ok("icone_objet : par type, groupe écrêté → ecretage, inconnu → repli 'forme'", icone_objet({ type: "image" }) === "image" && icone_objet({ type: "groupe" }) === "groupe" && icone_objet({ type: "texte" }) === "texte" && icone_objet({ type: "zzz" }) === "forme");
}
if (echecs.length) { console.error("ECHECS arbre_calques :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA arbre_calques : PASS (6 controles)");
