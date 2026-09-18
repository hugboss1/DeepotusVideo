// mod-histogramme.js — le panneau Histogramme d'Affinity (R6) : quatre
// canaux de 256 (R, V, B, luminance Rec. 601) depuis un tampon {w, h, data}
// (le format d'ImageData de mod-pixel), pixels transparents ignorés,
// moyenne / écart-type / médiane de la luminance, chemins SVG normalisés
// au maximum. Feuille pure.
const vide = () => new Array(256).fill(0);
export function histogramme(tampon) {
  const r = vide(), g = vide(), b = vide(), l = vide();
  const out = { r, g, b, l, pixels: 0, moyenne: 0, ecartType: 0, mediane: 0 };
  const d = tampon && tampon.data;
  if (!d || !d.length) return out;
  let n = 0, somme = 0;
  for (let i = 0; i + 3 < d.length; i += 4) {
    if (!d[i + 3]) continue;
    const R = d[i], G = d[i + 1], B = d[i + 2];
    const L = Math.round(0.299 * R + 0.587 * G + 0.114 * B);
    r[R]++; g[G]++; b[B]++; l[L]++;
    n++; somme += L;
  }
  if (!n) return out;
  const moyenne = somme / n;
  let variance = 0, cumul = 0, mediane = 0;
  for (let v = 0; v < 256; v++) variance += l[v] * (v - moyenne) * (v - moyenne);
  for (let v = 0; v < 256; v++) { cumul += l[v]; if (cumul * 2 >= n) { mediane = v; break; } }
  out.pixels = n; out.moyenne = Math.round(moyenne); out.ecartType = Math.round(Math.sqrt(variance / n) * 100) / 100; out.mediane = mediane;
  return out;
}
export function histogramme_chemins(h, w, hauteur) {
  const out = { r: "", g: "", b: "", l: "" };
  if (!h || !h.pixels || !(w > 0) || !(hauteur > 0)) return out;
  const max = Math.max(1, ...["r", "g", "b", "l"].flatMap((k) => h[k]));
  for (const k of ["r", "g", "b", "l"]) {
    const c = h[k];
    if (!c.some((v) => v)) continue;
    let s = `M0 ${hauteur}`;
    for (let i = 0; i < 256; i++) {
      const x = Math.round(i * w / 255 * 100) / 100, y = Math.round((hauteur - c[i] / max * hauteur) * 100) / 100;
      s += ` L${x} ${y}`;
    }
    out[k] = s + ` L${w} ${hauteur}Z`;
  }
  return out;
}
