// schema.test.mjs — t314 : mod-schema, la logique pure — analyse d'un schéma → document aux calques nommés (ordre de
// révélation et natures dans doc.schema), ordre d'envoi vers Animation qui suit le document modifié, corps de
// POST /api/schema/animation, nom stable des PNG, lignes du choix de détourage. Feuille.
import { doc_depuis_analyse, ordre_envoi, nom_png, corps_animation, script_de, texte_de_ligne, options_detourage,
         libelle_nature } from "../js/mod-schema.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 300) : "")); };

const ANALYSE = {
  largeur: 800, hauteur: 500, liens: [{ fleche: "e03", de: "e01", vers: "e04" }],
  elements: [
    { id: "e01", nature: "forme", nom: "Forme 1 — Client", ordre: 0, boite: { x: 60, y: 200, w: 160, h: 90 }, png: "data:" },
    { id: "e02", nature: "etiquette", nom: "Étiquette 1 : Client", ordre: 1, parent: "e01", texte: "Client", couleur: "#141414",
      boite: { x: 95, y: 232, w: 90, h: 26 }, lignes: [{ texte: "Client", boite: { x: 95, y: 232, w: 90, h: 26 } }] },
    { id: "e03", nature: "fleche", nom: "Flèche 1 : Client → Serveur", ordre: 2, boite: { x: 230, y: 235, w: 320, h: 20 },
      queue: { x: 231, y: 245 }, pointe: { x: 549, y: 245 }, png: "data:" },
    { id: "e04", nature: "forme", nom: "Forme 2", ordre: 3, boite: { x: 560, y: 200, w: 160, h: 90 }, png: "data:" },
    { id: "e05", nature: "forme", nom: "Forme 3", ordre: 4, boite: { x: 1, y: 1, w: 2, h: 2 }, png: "data:" },   // tracé vide
  ],
};
const carre = (x, y) => [{ type: "path", d: `M ${x} ${y} L ${x + 10} ${y} L ${x + 10} ${y + 10} Z`, style: { fond: "#000000", regle: "evenodd" } }];
const TRACES = new Map([["e01", carre(60, 200)], ["e03", carre(230, 235)], ["e04", carre(560, 200)], ["e05", []]]);
const doc = doc_depuis_analyse(ANALYSE, TRACES, "Mon schéma");

{
  ok("5a taille, fond blanc, nom", doc.taille.w === 800 && doc.taille.h === 500 && doc.fond === "#FFFFFF" && doc.nom === "Mon schéma");
  ok("5a calques nommés (tracé vide sauté)", JSON.stringify(doc.calques.map((c) => c.nom)) ===
     JSON.stringify(["Forme 1 — Client", "Forme 2", "Flèche 1 : Client → Serveur", "Étiquette 1 : Client"]), doc.calques.map((c) => c.nom));
  const ids = doc.calques.flatMap((c) => c.objets.map((o) => o.id));
  ok("5a ids d'objets uniques", new Set(ids).size === ids.length && ids.every(Boolean), ids);
  ok("5a étiquettes au-dessus", doc.calques[doc.calques.length - 1].objets[0].type === "texte");
  const cid = (nom) => doc.calques.find((c) => c.nom === nom).id;
  ok("5b ordre de révélation gardé", JSON.stringify(doc.schema.ordre) ===
     JSON.stringify([cid("Forme 1 — Client"), cid("Étiquette 1 : Client"), cid("Flèche 1 : Client → Serveur"), cid("Forme 2")]), doc.schema.ordre);
  const nf = doc.schema.natures[cid("Flèche 1 : Client → Serveur")];
  ok("5b nature et sens de la flèche", nf.nature === "fleche" && nf.queue.x === 231 && nf.pointe.x === 549, nf);
  const t = doc.calques[doc.calques.length - 1].objets[0];
  ok("5c étiquette = texte au bon corps, couleur lue", t.contenu === "Client" && t.style.corps === 23 && t.style.fond === "#141414"
     && t.style.police === "Segoe UI" && Math.abs(t.y - (232 + 26 * 0.82)) < 0.1 && t.x === 95, t);
  ok("5c texte_de_ligne : corps minimal", texte_de_ligne({ texte: "x", boite: { x: 0, y: 0, w: 4, h: 2 } }).style.corps === 6);
}
{
  const ord = ordre_envoi(doc);
  ok("5d envoi = ordre du scan", JSON.stringify(ord) === JSON.stringify(doc.schema.ordre), ord);
  const d2 = JSON.parse(JSON.stringify(doc));
  const [a, lab, fl, b] = d2.schema.ordre;
  d2.calques = d2.calques.filter((c) => c.id !== fl);                       // supprimé
  d2.calques.find((c) => c.id === lab).visible = false;                     // masqué
  d2.calques.push({ id: "c99", nom: "ajouté", visible: true, verrou: false, objets: carre(0, 0) });   // ajouté
  d2.calques.push({ id: "c98", nom: "vide", visible: true, verrou: false, objets: [] });               // vide
  ok("5d supprimé, masqué, vide sautés ; ajouté à la fin", JSON.stringify(ordre_envoi(d2)) === JSON.stringify([a, b, "c99"]), ordre_envoi(d2));
  ok("5d document sans schema : empilement", JSON.stringify(ordre_envoi({ calques: [{ id: "x", objets: carre(0, 0) }, { id: "y", objets: carre(1, 1) }] })) === '["x","y"]');
}
{
  ok("5e nom stable du PNG", nom_png("d42", "c3") === "vector_d42_cc3.png");
  const r = new Map(doc.schema.ordre.map((id, i) => [id, { image: nom_png("d42", id), boite: { x: i, y: i, w: 10, h: 10 } }]));
  r.delete(doc.schema.ordre[1]);                                             // un calque sans pixels : absent
  const c = corps_animation(doc, "d42", r);
  ok("5f corps : document, ordre, natures, sens", c.doc_id === "d42" && c.largeur === 800 && c.fond === "#FFFFFF"
     && c.calques.length === 3 && c.calques[1].nature === "fleche" && c.calques[1].queue.x === 231
     && c.calques[0].image === nom_png("d42", doc.schema.ordre[0]) && !("queue" in c.calques[0]), c.calques);
  ok("5f script : les étiquettes, sinon les noms", script_de(doc, doc.schema.ordre) === "Client"
     && script_de(doc, [doc.schema.ordre[0]]) === "Forme 1 — Client");
}
{
  const o = options_detourage([{ id: "local-chroma", voie: "local", usd: 0, disponible: true, label: "x" },
    { id: "bria-rmbg", voie: "fal", usd: 0.018, disponible: true, label: "Bria RMBG 2.0" },
    { id: "pixelcut", voie: "fal", usd: 0, disponible: false, label: "Pixelcut", raison: "FAL_KEY" }]);
  ok("5g détourages : local gratuit, fal payant avec prix, clé absente dite", o[0].payant === false && o[0].libelle.includes("gratuit")
     && o[1].payant && o[1].libelle.includes("Bria RMBG 2.0") && o[1].libelle.includes("0.018") && o[2].libelle.includes("FAL_KEY"), o.map((x) => x.libelle));
  ok("5g natures traduites", libelle_nature("fleche") === "Flèche" && libelle_nature("zz") === "Forme");
}
if (echecs.length) { console.error("ECHECS schema :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA schema : PASS (17 controles)");
