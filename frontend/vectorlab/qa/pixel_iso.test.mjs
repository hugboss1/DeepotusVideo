// pixel_iso.test.mjs — t125 (07/10/2026) : la tuile iso 2:1 du persona Pixel
// gagne la symétrie sur ses DIAGONALES (les bords du losange, pente ±1/2) et
// le raccord iso PAR TUILE (la tuile sous le curseur, plus l'image entière) ;
// le Vectorlab s'ouvre sur un persona demandé (lanceur « Assets 2D »).
//
// La diagonale « ⟋ » d'une tuile w × h (k = w/h) envoie le centre de pixel
// (cx + dx, cy + dy) sur (cx + k·dy, cy + dx/k) : en 2:1, le pixel (x, y)
// devient la PAIRE (2y, ⌊x/2⌋) + (2y+1, ⌊x/2⌋) — l'empreinte naturelle d'un
// pixel iso — et l'application est une involution exacte sur ces paires.
import { symetrie_iso, miroirs, tuile_sous, masque_losange, pavage_iso } from "../js/mod-pixelart.js";
import { persona_demandee } from "../js/mod-persona.js";
import { tampon } from "../js/mod-pixel.js";
import { op_pixelart } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
const tri = (pts) => JSON.stringify(pts.map((p) => p.join(",")).sort());
let n = 0;
const ctl = (nom, cond, detail) => { n++; ok(nom, cond, detail); };

/* ── symétrie diagonale, entière ── */
{
  const s1 = symetrie_iso([[3, 2]], 32, 16, 32, 16, { d1: true });
  ctl("⟋ en 2:1 : (3,2) → la paire (4,1)+(5,1), l'original gardé", tri(s1) === tri([[3, 2], [4, 1], [5, 1]]), tri(s1));
  const s2 = symetrie_iso([[3, 2]], 32, 16, 32, 16, { d2: true });
  ctl("⟍ en 2:1 : (3,2) → la paire (26,14)+(27,14)", tri(s2) === tri([[3, 2], [26, 14], [27, 14]]), tri(s2));
  const s3 = symetrie_iso([[3, 2]], 32, 16, 32, 16, { d1: true, d2: true });
  ctl("⟋ + ⟍ : les deux paires ET le symétrique central (28,13)",
      tri(s3) === tri([[3, 2], [4, 1], [5, 1], [26, 14], [27, 14], [28, 13]]), tri(s3));
  // involution sur les paires : l'image d'une paire est une paire, et l'image de l'image est la paire d'origine
  let inv = true, det = "";
  for (let y = 0; y < 16 && inv; y++) for (let x = 0; x < 32; x += 2) {
    const paire = [[x, y], [x + 1, y]];
    const im = symetrie_iso(paire, 32, 16, 32, 16, { d1: true }).filter((p) => !paire.some((q) => q[0] === p[0] && q[1] === p[1]));
    const re = symetrie_iso(im, 32, 16, 32, 16, { d1: true }).filter((p) => !im.some((q) => q[0] === p[0] && q[1] === p[1]));
    const surDiag = im.length === 0;               // la paire est sur l'axe : son image est elle-même
    if (!surDiag && (im.length !== 2 || tri(re) !== tri(paire))) { inv = false; det = `${x},${y} → ${tri(im)} → ${tri(re)}`; }
  }
  ctl("⟋ est une involution exacte sur les paires 2×1 de toute la tuile", inv, det);
  // le losange est stable : tout pixel du losange a ses images dans le losange
  const m = masque_losange(32, 16);
  let stable = true, hors = "";
  for (let y = 0; y < 16; y++) for (let x = 0; x < 32; x++) {
    if (!m[y * 32 + x]) continue;
    for (const [a, b] of symetrie_iso([[x, y]], 32, 16, 32, 16, { d1: true, d2: true }))
      if (!m[b * 32 + a]) { stable = false; hors = `${x},${y} → ${a},${b}`; }
  }
  ctl("le losange 32×16 est stable par ⟋ et ⟍ (aucune image hors du losange)", stable && m.some(Boolean), hors);
  // par tuile : la tuile du pixel, pas l'image
  const s4 = symetrie_iso([[35, 18]], 64, 32, 32, 16, { d1: true });
  ctl("par tuile : (35,18) dans la tuile (1,1) → (36,17)+(37,17)", tri(s4) === tri([[35, 18], [36, 17], [37, 17]]), tri(s4));
  const s5 = symetrie_iso([[3, 2]], 32, 16, 0, 0, { d1: true });
  ctl("sans tuile : l'image entière sert de tuile", tri(s5) === tri(s1), tri(s5));
  const s6 = symetrie_iso([[3, 5]], 16, 16, 16, 16, { d1: true });
  ctl("tuile carrée (k = 1) : ⟋ = la transposée (3,5) → (5,3)", tri(s6) === tri([[3, 5], [5, 3]]), tri(s6));
  const s7 = symetrie_iso([[3, 2]], 32, 16, 32, 16, {});
  ctl("sans diagonale : les points tels quels", tri(s7) === tri([[3, 2]]));
  // image 40 × 16, tuile (1,0) tronquée à 8 colonnes : (39,6) = local (7,6) → (12,3)+(13,3) = (44,3)+(45,3), hors image
  const s8 = symetrie_iso([[39, 6]], 40, 16, 32, 16, { d1: true });
  ctl("une image hors de l'image (tuile tronquée au bord) est écartée", tri(s8) === tri([[39, 6]]), tri(s8));
  const s9 = symetrie_iso([[35, 3]], 40, 16, 32, 16, { d1: true });
  ctl("témoin : dans la même tuile tronquée, (35,3) → (38,1)+(39,1) reste", tri(s9) === tri([[35, 3], [38, 1], [39, 1]]), tri(s9));
}

/* ── miroirs : les points regroupés PAR IMAGE (le pinceau trace une polyligne par image) ── */
{
  const pts = [[1, 1], [2, 1]];
  const r = miroirs(pts, false, 8, 8, { h: true, v: true }, null);
  ctl("H + V continus : 4 groupes contigus de 2 (l'entrelacement mêlait les traits)",
      r.length === 8 && JSON.stringify(r.slice(2, 4)) === JSON.stringify([[7, 1], [6, 1]])
      && JSON.stringify(r.slice(4, 6)) === JSON.stringify([[1, 7], [2, 7]])
      && JSON.stringify(r.slice(6, 8)) === JSON.stringify([[7, 7], [6, 7]]), JSON.stringify(r));
  // continu, centre (16, 8) : (4,4) → dx −12, dy −4 → (16 − 8, 8 − 6) = (8,2) ; (6,4) → (8,3)
  const d = miroirs([[4, 4], [6, 4]], false, 32, 16, { d1: true }, { w: 32, h: 16 });
  ctl("⟋ continu : (4,4) → (cx + 2·dy, cy + dx/2) = (8,2) ; (6,4) → (8,3)",
      d.length === 4 && Math.abs(d[2][0] - 8) < 1e-9 && Math.abs(d[2][1] - 2) < 1e-9 && Math.abs(d[3][0] - 8) < 1e-9 && Math.abs(d[3][1] - 3) < 1e-9, JSON.stringify(d));
  const e = miroirs([[3, 2]], true, 32, 16, { d1: true }, { w: 32, h: 16 });
  ctl("miroirs entier ⟋ = symetrie_iso", tri(e) === tri([[3, 2], [4, 1], [5, 1]]), tri(e));
  const f = miroirs([[1, 2]], true, 8, 8, { h: true }, null);
  ctl("miroirs entier H = symetrie d'avant : (1,2) et (6,2)", tri(f) === tri([[1, 2], [6, 2]]), tri(f));
  const g = miroirs([[3, 2]], true, 32, 16, { d1: true }, null);
  ctl("diagonale sans tuile iso transmise : rien (les diagonales n'existent qu'en iso)", tri(g) === tri([[3, 2]]), tri(g));
}

/* ── tuile_sous : la tuile du dernier pixel survolé, pour le raccord ── */
{
  const img = tampon(64, 16);
  for (let y = 0; y < 16; y++) for (let x = 0; x < 64; x++) {
    const i = (y * 64 + x) * 4;
    if (x < 32) img.data.set([200, 40, 40, 255], i);                       // tuile 0 : uni
    else img.data.set([(x * 53 + y * 97) % 256, (x * 11) % 256, (y * 29) % 256, 255], i);   // tuile 1 : bruit
  }
  const t1 = tuile_sous(img, 40, 5, 32, 16);
  ctl("tuile_sous(40,5) : la tuile (1,0), 32×16, ses pixels", t1.tx === 1 && t1.ty === 0 && t1.img.w === 32 && t1.img.h === 16
      && t1.img.data[0] === img.data[(0 * 64 + 32) * 4], JSON.stringify([t1.tx, t1.ty, t1.img.w, t1.img.h]));
  const t0 = tuile_sous(img, null, null, 32, 16);
  ctl("sans survol : la tuile (0,0)", t0.tx === 0 && t0.ty === 0 && t0.img.w === 32);
  const tz = tuile_sous(img, 40, 5, 0, 0);
  ctl("sans grille de tuiles : l'image entière", tz.img.w === 64 && tz.img.h === 16 && tz.tx === null);
  const tb = tuile_sous(img, 999, -4, 32, 16);
  ctl("survol hors image : ramené dans l'image", tb.tx === 1 && tb.ty === 0, JSON.stringify([tb.tx, tb.ty]));
  const sc0 = pavage_iso(t0.img).score, sc1 = pavage_iso(t1.img).score, scTout = pavage_iso(img).score;
  ctl("le raccord iso d'une tuile unie ≠ celui d'une tuile bruitée ≠ celui de l'image entière (la mesure dépend de la tuile)",
      sc0 !== sc1 && sc1 !== scTout && sc0 !== scTout, JSON.stringify([sc0, sc1, scTout]));
  ctl("témoin : la tuile unie raccorde mieux que la bruitée", sc0 > sc1, JSON.stringify([sc0, sc1]));
}

/* ── le document garde les diagonales (op_pixelart) ── */
{
  const d = {};
  op_pixelart(d, { symetrie: { h: true, v: false, d1: true, d2: false } });
  ctl("op_pixelart garde ⟋ et n'écrit pas ⟍ faux", JSON.stringify(d.pixelart.symetrie) === JSON.stringify({ h: true, v: false, d1: true }), JSON.stringify(d.pixelart));
  op_pixelart(d, { symetrie: { h: false, v: true } });
  ctl("décocher : les diagonales disparaissent, forme d'avant t125", JSON.stringify(d.pixelart.symetrie) === JSON.stringify({ h: false, v: true }), JSON.stringify(d.pixelart));
}

/* ── persona demandé à l'ouverture ── */
{
  const vide = () => null;
  ctl("?persona=pixel → pixel", persona_demandee("?persona=pixel", vide) === "pixel");
  ctl("?persona=inconnu → rien", persona_demandee("?persona=zz", vide) === null);
  ctl("demande à usage unique (stockage) → pixel", persona_demandee("", (k) => (k === "dz_vl_persona" ? "pixel" : null)) === "pixel");
  ctl("rien demandé → rien", persona_demandee("", vide) === null && persona_demandee(undefined, () => { throw new Error("bloqué"); }) === null);
  ctl("l'URL l'emporte sur le stockage", persona_demandee("?persona=vecteur", () => "pixel") === "vecteur");
}

if (echecs.length) {
  console.error("ECHECS pixel_iso :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log(`QA pixel_iso : PASS (${n} controles)`);
