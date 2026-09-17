// tuiles.test.mjs — lot C : doc.grille (commande op_grille), la fiche de
// terrains (défauts + surcharges), l'objet `tuile` compilé en hexagone de
// la grille, le pinceau (op_tuiles_peindre : peint l'existant, pose le
// manquant) et le générateur de plateau. États vides construits.
import { parserDoc, compilerSVG, op_grille, terrains_de, op_terrain_definir,
         op_terrain_supprimer, op_tuiles_peindre, op_plateau_generer, tuile_a,
         op_deplacer, op_redimensionner, TERRAINS_DEFAUT } from "../js/mod-doc.js";
import { hex_centre } from "../js/mod-grille.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const base = () => ({ v: 1, nom: "P", taille: { w: 800, h: 600 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [] }] });
const nbc = (x) => Math.round(x * 100) / 100;

/* ── grille ── */
{
  const d = base();
  op_grille(d, { type: "hex", pas: 24 });
  ok("op_grille pose une grille normalisée", d.grille.type === "hex" && d.grille.sous === 1 && d.grille.orientation === "pointe", JSON.stringify(d.grille));
  op_grille(d, { orientation: "plat", origine: [10, 5] });
  ok("op_grille : patch partiel fusionné", d.grille.type === "hex" && d.grille.orientation === "plat" && d.grille.origine[0] === 10);
  op_grille(d, null);
  ok("op_grille(null) retire la grille", d.grille === undefined);
  let refus = 0;
  for (const p of [{ type: "octo" }, { pas: -1 }, { type: "hex", pas: 8, sous: 0 }]) {
    const e = base(); try { op_grille(e, p); } catch { refus++; }
  }
  ok("op_grille refuse 3 patchs", refus === 3, String(refus));
  const m = base(); m.grille = { type: "hex", pas: 0 };
  let refusDoc = false; try { parserDoc(m); } catch { refusDoc = true; }
  ok("parserDoc refuse une grille malformée", refusDoc);
}
/* ── terrains ── */
{
  const d = base();
  const t = terrains_de(d);
  ok("état vide : les défauts (mer, plaine, foret, colline, montagne)", Object.keys(t).length === 5 && t.mer.hauteur_mm === 0 && t.montagne.hauteur_mm === 8, JSON.stringify(Object.keys(t)));
  ok("TERRAINS_DEFAUT n'est pas muté par terrains_de", terrains_de(d) !== TERRAINS_DEFAUT);
  op_terrain_definir(d, "lave", { nom: "Lave", couleur: "#D33", hauteur_mm: 1 });
  ok("définir ajoute au document, fusionné", terrains_de(d).lave.couleur === "#D33" && d.terrains.lave && Object.keys(terrains_de(d)).length === 6);
  op_terrain_definir(d, "mer", { couleur: "#123456" });
  ok("surcharger un défaut garde son nom et sa hauteur", terrains_de(d).mer.couleur === "#123456" && terrains_de(d).mer.hauteur_mm === 0 && terrains_de(d).mer.nom === "Mer");
  op_terrain_supprimer(d, "lave");
  ok("supprimer retire la surcharge", terrains_de(d).lave === undefined);
  let refus = 0;
  for (const [k, f] of [["Lave!", {}], ["x", { hauteur_mm: -1 }], ["x", { couleur: "rouge" }], ["x", null]]) {
    try { op_terrain_definir(base(), k, f); } catch { refus++; }
  }
  ok("définir refuse clé/hauteur/couleur/fiche invalides", refus === 4, String(refus));
}
/* ── tuile : compilation ── */
{
  const d = base();
  op_grille(d, { type: "hex", pas: 20 });
  d.calques[0].objets.push({ id: "t1", type: "tuile", q: 1, r: 1, terrain: "foret" });
  const svg = compilerSVG(d);
  const [cx, cy] = hex_centre(1, 1, d.grille);
  ok("tuile : path data-q/data-r/data-terrain", svg.includes('data-objet="t1"') && svg.includes('data-q="1" data-r="1" data-terrain="foret"'), svg);
  ok("tuile : fond = couleur du terrain, contour fin", svg.includes(`fill="${TERRAINS_DEFAUT.foret.couleur}"`) && svg.includes('stroke-width="1"'));
  ok("tuile : d = hexagone centré sur la cellule", svg.includes(`M ${nbc(cx)} ${nbc(cy - 20)}`), svg);
  d.calques[0].objets[0].terrain = "inconnu";
  ok("terrain inconnu : gris et dit", compilerSVG(d).includes('fill="#888888"') && compilerSVG(d).includes('data-terrain-inconnu="1"'));
  const sans = base(); sans.calques[0].objets.push({ id: "t1", type: "tuile", q: 0, r: 0, terrain: "mer" });
  ok("sans grille hex : hexagone par défaut (32, pointe) — le doc ne casse pas", compilerSVG(sans).includes('data-objet="t1"'));
  let refus = 0;
  for (const o of [{ id: "t", type: "tuile", q: 0.5, r: 0, terrain: "mer" }, { id: "t", type: "tuile", q: 0, r: 0 }, { id: "t", type: "tuile", q: 0, r: 0, terrain: "mer", hauteur_mm: -2 }]) {
    const e = base(); e.calques[0].objets.push(o); try { parserDoc(e); } catch { refus++; }
  }
  ok("parserDoc refuse 3 tuiles malformées", refus === 3, String(refus));
}
/* ── tuile_a, déplacer (aimanté à la cellule), redimensionner (no-op) ── */
{
  const d = base(); op_grille(d, { type: "hex", pas: 20 });
  d.calques[0].objets.push({ id: "t1", type: "tuile", q: 0, r: 0, terrain: "mer" });
  ok("tuile_a trouve (0,0), pas (1,0)", tuile_a(d, 0, 0) && tuile_a(d, 0, 0).id === "t1" && tuile_a(d, 1, 0) === null);
  const [cx1] = hex_centre(1, 0, d.grille), [cx0] = hex_centre(0, 0, d.grille);
  op_deplacer(d, ["t1"], cx1 - cx0 + 1, 0);
  ok("déplacer une tuile la ré-ancre à la cellule voisine", d.calques[0].objets[0].q === 1 && d.calques[0].objets[0].r === 0, JSON.stringify(d.calques[0].objets[0]));
  op_redimensionner(d, ["t1"], { x: 0, y: 0, w: 10, h: 10 }, { x: 0, y: 0, w: 100, h: 100 });
  ok("redimensionner une tuile est sans effet (ancrée)", d.calques[0].objets[0].q === 1);
}
/* ── pinceau ── */
{
  const d = base(); op_grille(d, { type: "hex", pas: 20 });
  d.calques[0].objets.push({ id: "t1", type: "tuile", q: 0, r: 0, terrain: "mer" });
  const r = op_tuiles_peindre(d, "c1", [{ q: 0, r: 0 }, { q: 1, r: 0 }, { q: 1, r: 0 }], "foret");
  ok("peindre : 1 repeinte, 1 posée (doublon ignoré)", r.peintes.length === 1 && r.posees.length === 1 && d.calques[0].objets.length === 2, JSON.stringify(r));
  ok("la posée porte le terrain et la cellule", tuile_a(d, 1, 0).terrain === "foret" && tuile_a(d, 0, 0).terrain === "foret");
  let refus = 0;
  try { op_tuiles_peindre(d, "c1", [], "foret"); } catch { refus++; }
  try { op_tuiles_peindre(d, "c1", [{ q: 0, r: 0 }], "inconnu"); } catch { refus++; }
  ok("peindre refuse : aucune cellule ; terrain inconnu", refus === 2, String(refus));
  const v = base(); op_grille(v, { type: "hex", pas: 20 }); v.calques[0].verrou = true;
  v.calques[0].objets.push({ id: "t1", type: "tuile", q: 0, r: 0, terrain: "mer" });
  v.calques.push({ id: "c2", nom: "libre", visible: true, verrou: false, objets: [] });
  const rv = op_tuiles_peindre(v, "c2", [{ q: 0, r: 0 }], "foret");
  ok("une tuile d'un calque verrouillé n'est ni peinte ni doublée", rv.peintes.length === 0 && rv.posees.length === 0 && v.calques[0].objets[0].terrain === "mer");
}
/* ── générateur ── */
{
  const d = base();
  const r = op_plateau_generer(d, { mode: "rayon", rayon: 2, pas: 30, orientation: "plat", terrain: "plaine", numeroter: true });
  ok("générer pose la grille hex du document", d.grille && d.grille.type === "hex" && d.grille.pas === 30 && d.grille.orientation === "plat");
  ok("un calque « plateau » de 19 tuiles + un calque « numéros » de 19 textes", r.tuiles.length === 19
     && d.calques.find((c) => c.id === r.calqueId).objets.length === 19
     && d.calques.find((c) => c.id === r.calqueNumeros).objets.filter((o) => o.type === "texte").length === 19, JSON.stringify(r));
  ok("les numéros lisent « q,r »", d.calques.find((c) => c.id === r.calqueNumeros).objets.some((o) => o.contenu === "0,0"));
  ok("le plateau est centré : l'origine de la grille est au centre de la page", d.grille.origine[0] === 400 && d.grille.origine[1] === 300, JSON.stringify(d.grille.origine));
  const r2 = op_plateau_generer(d, { mode: "rect", colonnes: 3, lignes: 2, terrain: "mer" });
  ok("un second plateau : la grille existante est GARDÉE, calque neuf", d.grille.pas === 30 && r2.tuiles.length === 6 && !r2.calqueNumeros);
  ok("le document compilé passe parserDoc", (() => { try { compilerSVG(parserDoc(d)); return true; } catch { return false; } })());
  let refus = 0;
  try { op_plateau_generer(base(), { mode: "rayon", rayon: 2, terrain: "inconnu" }); } catch { refus++; }
  try { op_plateau_generer(base(), { mode: "rect", colonnes: 0, lignes: 1 }); } catch { refus++; }
  ok("générer refuse terrain inconnu et rect vide", refus === 2, String(refus));
}

if (echecs.length) {
  console.error("ECHECS tuiles :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA tuiles : PASS (30 controles)");
