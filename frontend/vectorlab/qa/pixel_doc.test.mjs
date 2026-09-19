// pixel_doc.test.mjs — lot E côté modèle : doc.pixelart {tuile, palette,
// symetrie} validé, op_pixelart, op_image_rev (la révision raster suit
// l'objet image, le résolveur d'href ajoute ?v=rev), image_url avec rev.
import { parserDoc, compilerSVG, op_pixelart, op_image_rev } from "../js/mod-doc.js";
import { image_url, image_rev_max } from "../js/mod-image.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const base = () => ({
  v: 1, nom: "Pix", taille: { w: 64, h: 64 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
    { id: "i1", type: "image", x: 0, y: 0, w: 64, h: 64, href: "img1.png", nat: { w: 16, h: 16 }, style: {} },
  ] }],
});

/* ── validation ── */
{
  let refus = 0;
  for (const mauvais of [null, [], { tuile: { w: 0, h: 16 } }, { tuile: { w: 16.5, h: 16 } }, { palette: "#FFF" },
                         { palette: ["rouge"] }, { symetrie: 3 }, { inconnu: 1 }]) {
    const d = base(); d.pixelart = mauvais;
    try { parserDoc(d); } catch { refus++; }
  }
  ok("parserDoc refuse 8 pixelart malformés", refus === 8, String(refus));
  const d = base(); d.pixelart = { tuile: { w: 16, h: 16 }, palette: ["#FF0000", "#00ff00"], symetrie: { h: true, v: false } };
  let accepte = true; try { parserDoc(d); } catch (e) { accepte = false; }
  ok("parserDoc accepte un pixelart complet", accepte);
  ok("état vide : un doc sans pixelart passe", (() => { try { parserDoc(base()); return true; } catch { return false; } })());
}
/* ── op_pixelart ── */
{
  const d = base();
  op_pixelart(d, { tuile: { w: 32, h: 32 } });
  ok("op_pixelart pose la tuile", d.pixelart.tuile.w === 32 && d.pixelart.tuile.h === 32);
  op_pixelart(d, { palette: ["#ff0000"], symetrie: { h: true } });
  ok("op_pixelart fusionne : la tuile reste, la palette est normalisée en majuscules, la symétrie v est fausse", d.pixelart.tuile.w === 32 && d.pixelart.palette[0] === "#FF0000" && d.pixelart.symetrie.h === true && d.pixelart.symetrie.v === false);
  op_pixelart(d, { tuile: null, palette: null, symetrie: null });
  ok("tout retirer efface le champ", d.pixelart === undefined);
  let refus = 0;
  try { op_pixelart(d, { tuile: { w: -1, h: 1 } }); } catch { refus++; }
  try { op_pixelart(d, null); } catch { refus++; }
  ok("patch invalide refusé, le doc reste sans pixelart", refus === 2 && d.pixelart === undefined);
}
/* ── révision raster ── */
{
  const d = base();
  const svg0 = compilerSVG(d, { image: (h, rev) => image_url("D", h, rev) });
  ok("sans rev : l'href est nu", svg0.includes('href="/api/vector/docs/D/images/img1.png"') && !svg0.includes("?v="), svg0);
  op_image_rev(d, "i1", 3);
  ok("op_image_rev pose rev sur l'objet", d.calques[0].objets[0].rev === 3);
  const svg = compilerSVG(d, { image: (h, rev) => image_url("D", h, rev) });
  ok("avec rev : ?v=3 sur l'href, le JSON ne porte pas les pixels", svg.includes('href="/api/vector/docs/D/images/img1.png?v=3"'), svg);
  op_image_rev(d, "i1", 0);
  ok("rev 0 retire le champ", d.calques[0].objets[0].rev === undefined);
  let refus = 0;
  try { op_image_rev(d, "zz", 1); } catch { refus++; }
  try { op_image_rev(d, "i1", -1); } catch { refus++; }
  ok("id inconnu ou rev négative refusés", refus === 2);
  ok("image_url : une URL absolue ne prend pas de ?v", image_url("D", "https://x/y.png", 2) === "https://x/y.png");
  ok("image_rev_max : la plus haute rev des objets qui partagent l'href, 0 à vide", (() => {
    const a = base(); a.calques[0].objets[0].rev = 2;
    a.calques[0].objets.push({ ...a.calques[0].objets[0], id: "i2", rev: 5 });
    return image_rev_max(a, "img1.png") === 5 && image_rev_max(a, "autre.png") === 0 && image_rev_max(base(), "img1.png") === 0;
  })());
  ok("parserDoc accepte rev entier, refuse rev négative", (() => {
    const a = base(); a.calques[0].objets[0].rev = 2; try { parserDoc(a); } catch { return false; }
    const b = base(); b.calques[0].objets[0].rev = -2; try { parserDoc(b); return false; } catch { return true; }
  })());
}

/* ── lot 2 : pixelart.iso ── */
{
  const d = base();
  op_pixelart(d, { tuile: { w: 32, h: 16 }, iso: true });
  ok("pixelart.iso accepté", d.pixelart.iso === true);
  let refus = 0; try { op_pixelart(d, { iso: "oui" }); } catch { refus++; }
  ok("iso non booléen refusé", refus === 1);
  parserDoc(JSON.parse(JSON.stringify(d)));
  op_pixelart(d, { iso: null });
  ok("iso retiré par null", d.pixelart.iso === undefined);
}
/* ── lot 3 : pixelart.modele et pixelart.calque ── */
{
  const d = base();
  op_pixelart(d, { modele: { id: "i1", cellule: 16 }, calque: "i1" });
  ok("modele {id, cellule} et calque acceptés", d.pixelart.modele.id === "i1" && d.pixelart.modele.cellule === 16 && d.pixelart.calque === "i1");
  let refus = 0;
  for (const m of [{ modele: { id: "i1" } }, { modele: { id: "", cellule: 4 } }, { modele: { id: "i1", cellule: 0 } }, { calque: 7 }]) { try { op_pixelart(base(), m); } catch { refus++; } }
  ok("modele sans cellule, id vide, cellule 0, calque non-chaîne → refusés", refus === 4, refus);
  parserDoc(JSON.parse(JSON.stringify(d)));
  op_pixelart(d, { modele: null, calque: null });
  ok("retirés par null", d.pixelart === undefined || (d.pixelart.modele === undefined && d.pixelart.calque === undefined));
}
/* ── lot 5 : plusieurs modèles — pixelart.paires ── */
{
  const d = base();
  op_pixelart(d, { paires: [{ modele: "i1", cellule: 8, calque: null }, { modele: "i2", cellule: 16, calque: "i3" }] });
  ok("paires acceptées (calque null ou id)", d.pixelart.paires.length === 2 && d.pixelart.paires[1].calque === "i3");
  let refus = 0;
  for (const m of [{ paires: "x" }, { paires: [{ cellule: 8 }] }, { paires: [{ modele: "i1", cellule: 0 }] }, { paires: [{ modele: "i1", cellule: 8, calque: 5 }] }]) { try { op_pixelart(base(), m); } catch { refus++; } }
  ok("paires non-liste, sans modèle, cellule 0, calque non-chaîne → refusés", refus === 4, refus);
  parserDoc(JSON.parse(JSON.stringify(d)));
  op_pixelart(d, { paires: null });
  ok("paires retirées par null", d.pixelart === undefined || d.pixelart.paires === undefined);
}
if (echecs.length) {
  console.error("ECHECS pixel_doc :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA pixel_doc : PASS (26 controles)");
