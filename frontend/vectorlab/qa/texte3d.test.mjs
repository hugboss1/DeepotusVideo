// texte3d.test.mjs — lot D : les glyphes d'une police du dist deviennent
// des chemins du modèle (opentype.js vendorisé, en vrai sur Anton.ttf), et
// op_texte_vectoriser remplace le texte par un path (même id, même fond).
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { POLICES, commandes_vers_d, texte_vers_d } from "../js/mod-texte3d.js";
import { parserDoc, compilerSVG, op_texte_vectoriser, chemin_parser } from "../js/mod-doc.js";

const require = createRequire(import.meta.url);
const opentype = require("../vendor/opentype.min.js");
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
{
  ok("POLICES : ≥ 12 entrées {id, nom, fichier}, fichiers .ttf, ids uniques", POLICES.length >= 12
     && POLICES.every((p) => p.id && p.nom && /\.ttf$/.test(p.fichier)) && new Set(POLICES.map((p) => p.id)).size === POLICES.length);
  ok("POLICES : les polices de provenance incertaine ne sont PAS listées",
     !POLICES.some((p) => /DistantGalaxy|Hacked|SuperFeel|SuperPencil|PolandKaito|GraffitiBrush|DrippingMarker/.test(p.fichier)));
}
{
  const d = commandes_vers_d([{ type: "M", x: 0, y: 0 }, { type: "L", x: 10, y: 0 }, { type: "Q", x1: 10, y1: 5, x: 10, y: 10 },
                              { type: "C", x1: 8, y1: 12, x2: 2, y2: 12, x: 0, y: 10 }, { type: "Z" }]);
  ok("commandes → d canonique absolu", d === "M 0 0 L 10 0 Q 10 5 10 10 C 8 12 2 12 0 10 Z", d);
  let refus = 0; try { commandes_vers_d([{ type: "H", x: 1 }]); } catch { refus++; }
  ok("commande inconnue refusée", refus === 1);
}
{
  const buf = readFileSync(new URL("../../dist/fonts/Anton.ttf", import.meta.url));
  const font = opentype.parse(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
  const d = texte_vers_d(font, "A", 100, 20, 120);
  const segs = chemin_parser(d);
  ok("« A » : un chemin avec son trou (2 × M), que M/L/Q/C/Z", (d.match(/M /g) || []).length === 2 && segs.every((s) => "MLQCZ".includes(s.c)), d.slice(0, 80));
  let minX = 1e9, maxX = -1e9, maxY = -1e9;
  for (const s of segs) for (let k = 0; k < s.p.length; k += 2) { minX = Math.min(minX, s.p[k]); maxX = Math.max(maxX, s.p[k]); maxY = Math.max(maxY, s.p[k + 1]); }
  ok("posé à x≈20, ligne de base y=120, largeur < corps", minX >= 19 && maxX < 120 && maxY <= 121, [minX, maxX, maxY].join(" "));
  const largeurA = maxX - minX;
  const d2 = texte_vers_d(font, "AA", 100, 0, 0, 10);
  let maxX2 = -1e9;
  for (const s of chemin_parser(d2)) for (let k = 0; k < s.p.length; k += 2) maxX2 = Math.max(maxX2, s.p[k]);
  ok("deux lettres + interlettrage 10 : plus large qu'une lettre et demie", maxX2 > largeurA * 1.5, `${maxX2} vs ${largeurA}`);
  ok("texte vide → d vide", texte_vers_d(font, "", 100, 0, 0) === "");
  // la commande du modèle
  const doc = { v: 1, nom: "T", taille: { w: 400, h: 200 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
    { id: "t1", type: "texte", x: 20, y: 120, contenu: "A", style: { fond: "#0047AB", police: "Anton", corps: 100 } }] }] };
  op_texte_vectoriser(doc, "t1", d);
  const o = doc.calques[0].objets[0];
  ok("op_texte_vectoriser : même id, type path, fond gardé, evenodd, plus de contenu ni de fonte", o.id === "t1" && o.type === "path" && o.d === d
     && o.style.fond === "#0047AB" && o.style.regle === "evenodd" && o.contenu === undefined && o.style.police === undefined, JSON.stringify(o));
  ok("le document compilé passe", compilerSVG(parserDoc(doc)).includes('data-objet="t1"'));
  let refus = 0;
  try { op_texte_vectoriser(doc, "t1", d); } catch { refus++; }           // déjà un path
  try { op_texte_vectoriser(doc, "zz", d); } catch { refus++; }
  try { op_texte_vectoriser({ ...doc, calques: [{ id: "c", verrou: false, objets: [{ id: "t", type: "texte", contenu: "x" }] }] }, "t", ""); } catch { refus++; }
  ok("refus : pas un texte, introuvable, d vide", refus === 3, String(refus));
}
if (echecs.length) {
  console.error("ECHECS texte3d :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA texte3d : PASS (11 controles)");
