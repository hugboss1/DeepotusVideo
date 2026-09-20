// pixel_ui.test.mjs — lot E : la logique PURE des deux modules UI du persona
// Pixel — les personas (classe body, outils visibles), la correspondance
// point du document → pixel natif (rognage compris), le nom du dépôt vers
// la Bibliothèque, l'op locale de taille native, la palette HTML.
import { PERSONAS, persona_classe, persona_de_outil } from "../js/mod-persona.js";
import { OUTILS_PIXEL, HINTS_PIXEL, pixel_de_doc, doc_de_pixel, nom_depot, op_image_nat, paletteHTML,
         cadres_de } from "../js/mod-pixelui.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

/* ── personas ── */
{
  ok("deux personas : vecteur, pixel (l'export est un onglet, relooking 18/09)", JSON.stringify(PERSONAS.map((p) => p.id)) === '["vecteur","pixel"]');
  ok("tranche : outil de tous les personas", persona_de_outil("tranche") === "tous");
  ok("classe body", persona_classe("pixel") === "persona-pixel" && persona_classe("zz") === "persona-vecteur");
  ok("les outils pixel appartiennent au persona Pixel, la sélection est partagée, la plume est vecteur",
     persona_de_outil("px-pinceau") === "pixel" && persona_de_outil("select") === "tous" && persona_de_outil("plume") === "vecteur");
}
/* ── outils et correspondance ── */
{
  ok("dix outils pixel au moins, tous préfixés px-", OUTILS_PIXEL.length >= 10 && OUTILS_PIXEL.every((o) => o.id.startsWith("px-") && o.touche && o.titre));
  ok("chaque outil a son indice", OUTILS_PIXEL.every((o) => typeof HINTS_PIXEL[o.id] === "string"));
  const o = { type: "image", x: 100, y: 50, w: 200, h: 100, nat: { w: 40, h: 20 } };
  ok("doc → pixel : (100,50) = (0,0), (300,150) = (40,20), le centre = (20,10)",
     JSON.stringify(pixel_de_doc(o, 100, 50)) === "[0,0]" && JSON.stringify(pixel_de_doc(o, 300, 150)) === "[40,20]"
     && JSON.stringify(pixel_de_doc(o, 200, 100)) === "[20,10]");
  const r = { ...o, rognage: { x: 10, y: 5, w: 20, h: 10 } };
  ok("avec rognage : la fenêtre est étirée sur l'objet", JSON.stringify(pixel_de_doc(r, 100, 50)) === "[10,5]" && JSON.stringify(pixel_de_doc(r, 300, 150)) === "[30,15]");
  ok("pixel → doc : le coin du pixel (20,10) revient au centre", JSON.stringify(doc_de_pixel(o, 20, 10)) === "[200,100]");
  ok("nom du dépôt : préfixe vector_ (provenance vectorlab), sans caractères hors patron",
     nom_depot("abc-1", "img1.png", "tuile") === "vector_abc-1_tuile_img1.png" && !/[^A-Za-z0-9_.-]/.test(nom_depot("a b/c", "x y.png", "feuille")));
}
/* ── op_image_nat, cadres ── */
{
  const doc = { v: 1, taille: { w: 100, h: 100 }, calques: [
    { id: "c1", nom: "c", visible: true, verrou: false, objets: [{ id: "i1", type: "image", x: 0, y: 0, w: 64, h: 64, href: "img1.png", nat: { w: 16, h: 16 }, rognage: { x: 0, y: 0, w: 8, h: 8 } }] },
    { id: "c2", nom: "cadres", visible: true, verrou: false, objets: [
      { id: "f1", type: "image", x: 0, y: 0, w: 16, h: 16, href: "img2.png", nat: { w: 16, h: 16 } },
      { id: "r1", type: "rect", x: 0, y: 0, w: 5, h: 5 },
      { id: "f2", type: "image", x: 20, y: 0, w: 16, h: 16, href: "img3.png", nat: { w: 16, h: 16 } }] },
  ] };
  op_image_nat(doc, "i1", { w: 32, h: 32 });
  ok("op_image_nat pose la taille native et retire le rognage devenu faux", doc.calques[0].objets[0].nat.w === 32 && doc.calques[0].objets[0].rognage === undefined);
  let refus = 0; try { op_image_nat(doc, "r1", { w: 1, h: 1 }); } catch { refus++; }
  try { op_image_nat(doc, "i1", { w: 0, h: 1 }); } catch { refus++; }
  ok("op_image_nat refuse un non-image et une taille nulle", refus === 2);
  const c = cadres_de(doc);
  ok("cadres_de : les images du calque « cadres », dans l'ordre, sans les autres objets", c.length === 2 && c[0].id === "f1" && c[1].id === "f2");
  ok("état vide : sans calque cadres → []", cadres_de({ calques: [doc.calques[0]] }).length === 0);
  const html = paletteHTML(["#FF0000", "#00FF00"], "#00FF00");
  ok("palette HTML : une pastille par couleur, la courante marquée", (html.match(/data-couleur=/g) || []).length === 2 && html.includes('data-couleur="#00FF00" class="px-pastille actif"'));
  ok("palette vide → texte d'état vide", paletteHTML([], "#000000").includes("aucune"));
}

if (echecs.length) {
  console.error("ECHECS pixel_ui :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA pixel_ui : PASS (16 controles)");
