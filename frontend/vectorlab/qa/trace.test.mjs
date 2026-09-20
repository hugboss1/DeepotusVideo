// trace.test.mjs — la vectorisation (D6) : options bornées, définition de
// tracé, conversion tracedata → objets path du modèle (trous en evenodd,
// couleurs hex, coordonnées ramenées au cadre de l'image), et la commande
// op_vectoriser_poser. Le vendor est exercé EN VRAI sur une ImageData
// synthétique (node : require CommonJS du même fichier que le navigateur).
import { createRequire } from "node:module";
import { TRACE_DEFAUTS, options_trace, definition_trace, tracedata_vers_objets }
  from "../js/mod-trace.js";
import { parserDoc, compilerSVG, op_vectoriser_poser, chemin_parser } from "../js/mod-doc.js";

const ImageTracer = createRequire(import.meta.url)("../vendor/imagetracer_v1.2.6.js");
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

/* ── options ── */
{
  const o = options_trace(TRACE_DEFAUTS);
  ok("défauts : 8 couleurs, lissage 1, seuil 8, pas de trait, coordonnées 2 déc.",
     o.numberofcolors === 8 && o.ltres === 1 && o.qtres === 1 && o.pathomit === 8
     && o.strokewidth === 0 && o.roundcoords === 2 && o.blurradius === 0, JSON.stringify(o));
  const b = options_trace({ couleurs: 999, lissage: 0, seuil: -4 });
  ok("options bornées : 64 couleurs max, lissage ≥ 0.1, seuil ≥ 0",
     b.numberofcolors === 64 && b.ltres === 0.1 && b.pathomit === 0, JSON.stringify(b));
  ok("options : 2 couleurs min", options_trace({ couleurs: 1 }).numberofcolors === 2);
}
/* ── définition : la fenêtre tracée tient dans `definition` px de côté ── */
{
  const d = definition_trace({ w: 1600, h: 800 }, 512);
  ok("définition : plus grand côté = 512, ratio gardé", d.w === 512 && d.h === 256, JSON.stringify(d));
  const p = definition_trace({ w: 100, h: 60 }, 512);
  ok("définition : une petite fenêtre n'est pas agrandie", p.w === 100 && p.h === 60);
}
/* ── tracedata → objets, sur une image synthétique : fond bleu, carré rouge
   avec un trou — le vendor en vrai ── */
function imageSynthetique() {
  const W = 40, H = 40, data = new Uint8ClampedArray(W * H * 4);
  const poser = (x, y, r, g, b) => { const i = (y * W + x) * 4; data[i] = r; data[i + 1] = g; data[i + 2] = b; data[i + 3] = 255; };
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    let c = [0, 71, 171];                                   // #0047AB
    if (x >= 8 && x < 32 && y >= 8 && y < 32) c = [155, 17, 30];   // #9B111E
    if (x >= 16 && x < 24 && y >= 16 && y < 24) c = [0, 71, 171];  // trou
    poser(x, y, ...c);
  }
  return { width: W, height: H, data };
}
{
  const td = ImageTracer.imagedataToTracedata(imageSynthetique(), options_trace({ couleurs: 2, seuil: 0 }));
  ok("vendor : tracedata 40×40 avec palette", td.width === 40 && td.height === 40 && td.palette.length === 2, JSON.stringify([td.width, td.palette]));
  const objets = tracedata_vers_objets(td, { x: 100, y: 200, w: 80, h: 80 });
  ok("au moins deux chemins (fond et carré)", objets.length >= 2, objets.length);
  ok("tous des path evenodd à fond hex", objets.every((o) => o.type === "path"
     && o.style.regle === "evenodd" && /^#[0-9A-F]{6}$/.test(o.style.fond)
     && o.style.contour === undefined), JSON.stringify(objets[0]));
  const couleurs = new Set(objets.map((o) => o.style.fond));
  ok("les deux couleurs du synthétique ressortent", couleurs.has("#0047AB") && couleurs.has("#9B111E"), [...couleurs].join(","));
  // coordonnées : dans le cadre [100..180]×[200..280] (tolérance 1 px de lissage)
  let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
  for (const o of objets) for (const s of chemin_parser(o.d)) {
    for (let k = 0; k < s.p.length; k += 2) {
      minX = Math.min(minX, s.p[k]); maxX = Math.max(maxX, s.p[k]);
      minY = Math.min(minY, s.p[k + 1]); maxY = Math.max(maxY, s.p[k + 1]);
    }
  }
  ok("coordonnées ramenées au cadre", minX >= 99 && maxX <= 181 && minY >= 199 && maxY <= 281,
     [minX, maxX, minY, maxY].join(" "));
  // le carré rouge porte son trou : un sous-chemin de plus (deux M)
  const rouge = objets.find((o) => o.style.fond === "#9B111E");
  ok("le trou est un sous-chemin du carré (2 × M)", rouge && (rouge.d.match(/M /g) || []).length === 2, rouge && rouge.d);
  // parse canonique : tout d est relisible par chemin_parser
  ok("tous les d sont canoniques", objets.every((o) => { try { chemin_parser(o.d); return true; } catch { return false; } }));
  // état vide : image transparente → aucun objet
  const vide = { width: 4, height: 4, data: new Uint8ClampedArray(64) };
  const tdVide = ImageTracer.imagedataToTracedata(vide, options_trace({ couleurs: 2 }));
  ok("image transparente → aucun objet (alpha < 32 ignoré)",
     tracedata_vers_objets(tdVide, { x: 0, y: 0, w: 4, h: 4 }).length === 0);
  /* ── la commande ── */
  const doc = { v: 1, nom: "T", taille: { w: 400, h: 400 },
    calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [] }] };
  const r = op_vectoriser_poser(doc, objets, "vectorisé");
  ok("op_vectoriser_poser : calque neuf au-dessus, ids rendus", r.calqueId === "c2"
     && doc.calques[1].nom === "vectorisé" && r.ids.length === objets.length
     && doc.calques[1].objets.length === objets.length, JSON.stringify(r));
  ok("le document compilé passe parserDoc et porte fill-rule",
     (() => { try { return compilerSVG(parserDoc(doc)).includes('fill-rule="evenodd"'); } catch { return false; } })());
  let refus = 0;
  try { op_vectoriser_poser(doc, [], "x"); } catch { refus++; }
  ok("op_vectoriser_poser refuse une liste vide", refus === 1);
}

if (echecs.length) {
  console.error("ECHECS trace :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA trace : PASS (17 controles)");
