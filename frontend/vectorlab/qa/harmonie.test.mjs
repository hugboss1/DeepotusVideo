// harmonie.test.mjs — mod-couleur (lot F) : palettes harmoniques pures
// (complémentaire, analogue, triade, tétrade, monochrome) en hex majuscules.
import { palette_harmonique, HARMONIES } from "../js/mod-couleur.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
const HEX = /^#[0-9A-F]{6}$/;
{
  ok("cinq harmonies nommées", JSON.stringify(HARMONIES.map((h) => h.id)) === '["complementaire","analogue","triade","tetrade","monochrome"]');
  const c = palette_harmonique("#ff0000", "complementaire");
  ok("complémentaire du rouge : rouge puis cyan", c.length === 2 && c[0] === "#FF0000" && c[1] === "#00FFFF", JSON.stringify(c));
  const t = palette_harmonique("#FF0000", "triade");
  ok("triade du rouge : rouge, vert, bleu", JSON.stringify(t) === '["#FF0000","#00FF00","#0000FF"]', JSON.stringify(t));
  const q = palette_harmonique("#FF0000", "tetrade");
  ok("tétrade : 4 couleurs à 90°, la 3e est le cyan", q.length === 4 && q[2] === "#00FFFF" && q.every((x) => HEX.test(x)), JSON.stringify(q));
  const a = palette_harmonique("#FF0000", "analogue");
  ok("analogue : 3 couleurs, la base au milieu, ±30°", a.length === 3 && a[1] === "#FF0000" && a[0] === "#FF0080" && a[2] === "#FF8000", JSON.stringify(a));
  const m = palette_harmonique("#3360B5", "monochrome");
  ok("monochrome : 5 luminosités croissantes de la même teinte, la base présente", m.length === 5 && m.includes("#3360B5") && new Set(m).size === 5 && m.every((x) => HEX.test(x)), JSON.stringify(m));
  let refus = 0; try { palette_harmonique("#FF0000", "zz"); } catch { refus++; }
  try { palette_harmonique("rouge", "triade"); } catch { refus++; }
  ok("harmonie inconnue ou hex invalide refusés", refus === 2);
  ok("le gris (saturation nulle) : la complémentaire reste un gris", palette_harmonique("#808080", "complementaire")[1] === "#808080");
}
if (echecs.length) {
  console.error("ECHECS harmonie :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA harmonie : PASS (8 controles)");
