// couleur.test.mjs — éditeur complet (E4) : conversions hex/rgb/hsv/cmjn
// (naïf, sans ICC — assumé), palette par défaut générée, palette du
// document (ops annulables), champs optionnels du parseur (E1).
import { hexVersRgb, rgbVersHex, rgbVersHsv, hsvVersRgb, rgbVersCmjn,
         cmjnVersRgb, palette_defaut, op_palette_ajouter,
         op_palette_retirer } from "../js/mod-couleur.js";
import { parserDoc } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 140) : ""));
};

/* ── hex ↔ rgb : strict #RRGGBB ── */
{
  const c = hexVersRgb("#FF8000");
  ok("hexVersRgb", c.r === 255 && c.g === 128 && c.b === 0, JSON.stringify(c));
  ok("rgbVersHex majuscule", rgbVersHex({ r: 255, g: 128, b: 0 }) === "#FF8000");
  let refus = 0;
  for (const mauvais of ["FF8000", "#F80", "#GG0000", "", "#12345"]) {
    try { hexVersRgb(mauvais); } catch { refus++; }
  }
  ok("hexVersRgb strict (5 refus)", refus === 5, String(refus));
}

/* ── hsv : aller-retour stable à ±1 ── */
{
  const h = rgbVersHsv({ r: 255, g: 0, b: 0 });
  ok("rouge pur → h0 s100 v100", h.h === 0 && h.s === 100 && h.v === 100,
     JSON.stringify(h));
  const org = { r: 64, g: 128, b: 192 };
  const rt = hsvVersRgb(rgbVersHsv(org));
  ok("hsv aller-retour ±1", Math.abs(rt.r - 64) <= 1 && Math.abs(rt.g - 128) <= 1
     && Math.abs(rt.b - 192) <= 1, JSON.stringify(rt));
}

/* ── cmjn naïf : bornes et aller-retour ── */
{
  ok("blanc → 0/0/0/0", JSON.stringify(rgbVersCmjn({ r: 255, g: 255, b: 255 }))
     === JSON.stringify({ c: 0, m: 0, j: 0, n: 0 }));
  ok("noir → n100", rgbVersCmjn({ r: 0, g: 0, b: 0 }).n === 100);
  const rouge = rgbVersCmjn({ r: 255, g: 0, b: 0 });
  ok("rouge → m100 j100", rouge.c === 0 && rouge.m === 100 && rouge.j === 100
     && rouge.n === 0, JSON.stringify(rouge));
  const org = { r: 34, g: 139, b: 34 };
  const rt = cmjnVersRgb(rgbVersCmjn(org));
  ok("cmjn aller-retour ±3", Math.abs(rt.r - 34) <= 3 && Math.abs(rt.g - 139) <= 3
     && Math.abs(rt.b - 34) <= 3, JSON.stringify(rt));
}

/* ── palette par défaut : 48 nuances valides et uniques ── */
{
  const p = palette_defaut();
  ok("48 nuances", p.length === 48, p.length);
  ok("toutes hex valides", p.every((h) => /^#[0-9A-F]{6}$/.test(h)));
  ok("uniques", new Set(p).size === p.length);
}

/* ── palette du document : ops de commande ── */
{
  const doc = { v: 1, taille: { w: 10, h: 10 },
                calques: [{ id: "c1", objets: [] }] };
  op_palette_ajouter(doc, "#9B111E");
  op_palette_ajouter(doc, "#0047AB");
  ok("ajout", JSON.stringify(doc.palette) === '["#9B111E","#0047AB"]',
     JSON.stringify(doc.palette));
  let refus = 0;
  try { op_palette_ajouter(doc, "#9b111e"); } catch { refus++; }   // doublon (casse ignorée)
  try { op_palette_ajouter(doc, "rouge"); } catch { refus++; }     // pas un hex
  ok("doublon et non-hex refusés", refus === 2 && doc.palette.length === 2,
     String(refus));
  op_palette_retirer(doc, "#9B111E");
  ok("retrait", JSON.stringify(doc.palette) === '["#0047AB"]');
  let r2 = 0;
  try { op_palette_retirer(doc, "#123456"); } catch { r2++; }
  ok("retrait d'une absente refusé", r2 === 1);
}

/* ── E1 : parserDoc accepte unites/palette, refuse les formes invalides ── */
{
  const base = () => ({ v: 1, taille: { w: 10, h: 10 },
    calques: [{ id: "c1", objets: [] }] });
  let accepte = true;
  try {
    parserDoc({ ...base(), unites: { affichage: "mm", dpi: 300 },
                palette: ["#FFFFFF"] });
  } catch { accepte = false; }
  ok("parserDoc accepte unites+palette", accepte);
  let refus = 0;
  try { parserDoc({ ...base(), unites: { affichage: "furlong", dpi: 300 } }); }
  catch { refus++; }
  try { parserDoc({ ...base(), unites: { affichage: "mm", dpi: 0 } }); }
  catch { refus++; }
  try { parserDoc({ ...base(), palette: "rouge,bleu" }); } catch { refus++; }
  ok("parserDoc refuse unites/palette invalides (3)", refus === 3, String(refus));
}

if (echecs.length) {
  console.error("ECHECS couleur :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA couleur : PASS (15 controles)");
