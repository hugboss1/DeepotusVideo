// image.test.mjs — l'objet `image` du lot A (D1/D2) : validation, compilation
// uniforme <g><svg viewBox><image/></svg></g>, résolveur d'href, rognage,
// verrou d'objet ignoré par les commandes, fill-rule. Aucun DOM.
import { parserDoc, compilerSVG, op_ajouter, op_deplacer, op_redimensionner,
         op_supprimer, op_miroir, op_style, op_dupliquer,
         op_image_rogner, op_image_verrou } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const clone = (d) => JSON.parse(JSON.stringify(d));
const base = () => ({
  v: 1, nom: "Images", taille: { w: 400, h: 300 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [] }],
});
const img = (sur = {}) => ({ id: "i1", type: "image", x: 10, y: 20, w: 200, h: 100,
  href: "img1.png", nat: { w: 800, h: 400 }, style: {}, ...sur });

/* ── validation ── */
{
  let refus = 0;
  for (const mauvais of [
    img({ href: "" }), img({ href: 42 }), img({ nat: null }),
    img({ nat: { w: 0, h: 5 } }), img({ w: 0 }),
    img({ rognage: { x: -1, y: 0, w: 10, h: 10 } }),
    img({ rognage: { x: 0, y: 0, w: 900, h: 10 } }),   // déborde nat
    img({ rognage: { x: 0, y: 0, w: 0, h: 10 } }),
  ]) {
    const d = base(); d.calques[0].objets.push(mauvais);
    try { parserDoc(d); } catch { refus++; }
  }
  ok("parserDoc refuse 8 images malformées", refus === 8, String(refus));
  const d = base(); d.calques[0].objets.push(img());
  let accepte = true;
  try { parserDoc(d); } catch (e) { accepte = false; }
  ok("parserDoc accepte une image bien formée", accepte);
  // dans un groupe aussi
  const g = base();
  g.calques[0].objets.push({ id: "g1", type: "groupe", style: {},
    enfants: [img({ href: "" })] });
  let refusG = false;
  try { parserDoc(g); } catch { refusG = true; }
  ok("parserDoc descend dans les groupes", refusG);
}

/* ── compilation : uniforme, href verbatim sans résolveur ── */
{
  const d = base(); d.calques[0].objets.push(img({ style: { opacite: 0.5 } }));
  const svg = compilerSVG(d);
  ok("image : <g data-objet> hôte", svg.includes('<g data-objet="i1"'), svg);
  ok("image : svg imbriqué à la boîte de l'objet et viewBox natif entier",
     svg.includes('<svg x="10" y="20" width="200" height="100" viewBox="0 0 800 400" preserveAspectRatio="none">'), svg);
  ok("image : <image> à la taille native, href VERBATIM sans résolveur",
     svg.includes('<image x="0" y="0" width="800" height="400" href="img1.png" preserveAspectRatio="none"/>'), svg);
  ok("image : l'opacité du style porte sur le <g>", svg.includes('opacity="0.5"'));
  ok("image : pas de data-verrou sans verrou", !svg.includes("data-verrou"));
  // résolveur
  const svg2 = compilerSVG(d, { image: (h) => "/api/vector/docs/abc/images/" + h });
  ok("résolveur d'href appliqué", svg2.includes('href="/api/vector/docs/abc/images/img1.png"'), svg2);
  // href échappé
  const e = base(); e.calques[0].objets.push(img({ href: 'a"b<c.png' }));
  ok("href échappé", compilerSVG(e).includes('href="a&quot;b&lt;c.png"'));
}

/* ── rognage ── */
{
  const d = base(); d.calques[0].objets.push(img());
  op_image_rogner(d, "i1", { x: 100, y: 50, w: 400, h: 200 });
  ok("op_image_rogner pose la fenêtre", JSON.stringify(d.calques[0].objets[0].rognage)
     === JSON.stringify({ x: 100, y: 50, w: 400, h: 200 }));
  ok("compilation : viewBox = rognage",
     compilerSVG(d).includes('viewBox="100 50 400 200"'), compilerSVG(d));
  op_image_rogner(d, "i1", null);
  ok("op_image_rogner(null) retire la fenêtre", d.calques[0].objets[0].rognage === undefined);
  let refus = 0;
  for (const r of [{ x: -5, y: 0, w: 10, h: 10 }, { x: 0, y: 0, w: 801, h: 10 },
                   { x: 0, y: 0, w: 0, h: 10 }, "x"]) {
    try { op_image_rogner(clone(d), "i1", r); } catch { refus++; }
  }
  ok("op_image_rogner refuse 4 fenêtres hors image", refus === 4, String(refus));
  const r = base(); r.calques[0].objets.push({ id: "r1", type: "rect", x: 0, y: 0, w: 5, h: 5, style: {} });
  let refusType = false;
  try { op_image_rogner(r, "r1", { x: 0, y: 0, w: 1, h: 1 }); } catch { refusType = true; }
  ok("op_image_rogner refuse un non-image", refusType);
}

/* ── verrou d'objet : l'état vide construit (rien verrouillé) puis le verrou ── */
{
  const d = base();
  d.calques[0].objets.push(img(), img({ id: "i2", x: 300 }));
  op_deplacer(d, ["i1", "i2"], 5, 5);
  ok("sans verrou, les deux images bougent (négation démasquée)",
     d.calques[0].objets[0].x === 15 && d.calques[0].objets[1].x === 305);
  op_image_verrou(d, "i1", true);
  ok("op_image_verrou pose verrou:true", d.calques[0].objets[0].verrou === true);
  ok("compilation : data-verrou", compilerSVG(d).includes('data-verrou="1"'));
  op_deplacer(d, ["i1", "i2"], 5, 5);
  ok("l'image verrouillée ne bouge pas, l'autre si",
     d.calques[0].objets[0].x === 15 && d.calques[0].objets[1].x === 310);
  op_redimensionner(d, ["i1"], { x: 15, y: 25, w: 200, h: 100 }, { x: 0, y: 0, w: 50, h: 50 });
  ok("verrouillée : pas de redimensionnement", d.calques[0].objets[0].w === 200);
  op_style(d, ["i1"], { opacite: 0.2 });
  ok("verrouillée : pas de style", d.calques[0].objets[0].style.opacite === undefined);
  const n = op_supprimer(d, ["i1"]);
  ok("verrouillée : pas de suppression", n === 0 && d.calques[0].objets.length === 2);
  op_image_verrou(d, "i1", false);
  ok("déverrouiller retire la clé", d.calques[0].objets[0].verrou === undefined);
  op_deplacer(d, ["i1"], 1, 0);
  ok("déverrouillée : elle bouge à nouveau", d.calques[0].objets[0].x === 16);
}

/* ── géométrie : miroir, redimensionnement, duplication ── */
{
  const d = base(); d.calques[0].objets.push(img());
  op_redimensionner(d, ["i1"], { x: 10, y: 20, w: 200, h: 100 }, { x: 0, y: 0, w: 100, h: 50 });
  const o = d.calques[0].objets[0];
  ok("redimensionner mappe x,y,w,h", o.x === 0 && o.y === 0 && o.w === 100 && o.h === 50, JSON.stringify(o));
  op_miroir(d, ["i1"], "h", { x: 0, y: 0, w: 400, h: 300 });
  ok("miroir h : position réfléchie (pixels non retournés — écart dit)", o.x === 300 && o.w === 100);
  const ids = op_dupliquer(d, ["i1"], 3, 3);
  const c = d.calques[0].objets.find((x) => x.id === ids[0]);
  ok("dupliquer : clone décalé, même href", c && c.href === "img1.png" && c.x === 303);
  const a = op_ajouter(base(), "c1", img({ id: undefined }));
  ok("op_ajouter accepte une image", a === "o1");
}

/* ── fill-rule (la vectorisation en a besoin pour les trous) ── */
{
  const d = base();
  d.calques[0].objets.push({ id: "p", type: "path", d: "M 0 0 L 10 0 L 10 10 Z",
    style: { fond: "#112233", regle: "evenodd" } });
  ok("style.regle → fill-rule", compilerSVG(d).includes('fill-rule="evenodd"'));
  d.calques[0].objets[0].style = { fond: "#112233" };
  ok("sans regle, pas de fill-rule", !compilerSVG(d).includes("fill-rule"));
}

if (echecs.length) {
  console.error("ECHECS image :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA image : PASS (33 controles)");
