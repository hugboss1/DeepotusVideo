// unites.test.mjs — éditeur complet (E2) : conversions px↔mm/cm/in par
// dpi, formatage à la française, libellés de cote des gestes.
import { pxParUnite, versUnite, formatNombre, formatMesure, suffixe,
         libelle_mesure } from "../js/mod-unites.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 140) : ""));
};
const U = (affichage, dpi = 300) => ({ affichage, dpi });

/* ── conversions exactes à 300 dpi : 300 px = 1 in = 25,4 mm = 2,54 cm ── */
{
  ok("pxParUnite px", pxParUnite("px", 300) === 1);
  ok("pxParUnite in = dpi", pxParUnite("in", 300) === 300);
  ok("300 px → 25,4 mm", Math.abs(versUnite(300, U("mm")) - 25.4) < 1e-9,
     versUnite(300, U("mm")));
  ok("300 px → 2,54 cm", Math.abs(versUnite(300, U("cm")) - 2.54) < 1e-9);
  ok("300 px → 1 in", Math.abs(versUnite(300, U("in")) - 1) < 1e-9);
  ok("96 dpi : 96 px → 1 in", Math.abs(versUnite(96, U("in", 96)) - 1) < 1e-9);
}

/* ── formatage : précision par unité, virgule française, zéros élagués ── */
{
  ok("format px entier", formatNombre(300.4, U("px")) === "300",
     formatNombre(300.4, U("px")));
  ok("format mm 1 déc.", formatNombre(300, U("mm")) === "25,4");
  ok("format mm élague ,0", formatNombre(0, U("mm")) === "0"
     && formatNombre(2 * 300 / 25.4 * 12.5, U("mm")) === "25");
  ok("format cm 2 déc.", formatNombre(300, U("cm")) === "2,54");
  ok("format in 2 déc.", formatNombre(450, U("in")) === "1,5",
     formatNombre(450, U("in")));
  ok("formatMesure porte le suffixe", formatMesure(300, U("mm")) === "25,4 mm");
  ok("suffixe", suffixe("in") === "in" && suffixe("px") === "px");
}

/* ── libellés de cote : la grandeur suit CE qu'on dessine ── */
{
  const mm = U("mm");
  const r = libelle_mesure("rect", { w: 300, h: 150 }, mm);
  ok("rect → L × H", r === "25,4 × 12,7 mm", r);
  const c = libelle_mesure("ellipse", { rx: 150, ry: 150 }, mm);
  ok("cercle → rayon et diamètre", c.includes("r 12,7") && c.includes("⌀ 25,4")
     && c.endsWith("mm"), c);
  const e = libelle_mesure("ellipse", { rx: 150, ry: 75 }, mm);
  // 6,35 mm arrondi à la précision mm (1 déc.) : 6,4 — demi vers le haut,
  // jamais le 6,3 du flottant nu (patron toPrecision(12) du sérialiseur)
  ok("ellipse → rx × ry", e === "r 12,7 × 6,4 mm", e);
  const s = libelle_mesure("segment", { dx: 300, dy: 0 }, mm);
  ok("segment → longueur ∠ angle", s === "25,4 mm ∠ 0°", s);
  const s2 = libelle_mesure("segment", { dx: 0, dy: 300 }, mm);
  ok("segment vertical → 90°", s2.includes("∠ 90°"), s2);
  const d = libelle_mesure("delta", { dx: 300, dy: -150 }, mm);
  ok("delta signé", d === "Δ 25,4 ; -12,7 mm", d);
  const px = libelle_mesure("rect", { w: 64, h: 32 }, U("px"));
  ok("rect px", px === "64 × 32 px", px);
}

if (echecs.length) {
  console.error("ECHECS unites :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA unites : PASS (17 controles)");
