// mod-couleur.js — éditeur complet (E4) : conversions de couleur
// hex/RGB/HSV/CMJN (naïf, SANS profil ICC — assumé et dit dans l'UI),
// palette par défaut générée, ops de palette du document (annulables).
// La partie PURE est en tête (bancable node) ; le nuancier DOM
// (initCouleur) ne touche le document qu'à l'appel.

/* ── pur : conversions ── */
export function hexVersRgb(hex) {
  const m = /^#([0-9A-Fa-f]{6})$/.exec(String(hex || ""));
  if (!m) throw new Error(`couleur attendue en #RRGGBB : ${hex}`);
  const v = parseInt(m[1], 16);
  return { r: (v >> 16) & 255, g: (v >> 8) & 255, b: v & 255 };
}

export function rgbVersHex({ r, g, b }) {
  const c = (x) => Math.max(0, Math.min(255, Math.round(x)))
    .toString(16).padStart(2, "0");
  return ("#" + c(r) + c(g) + c(b)).toUpperCase();
}

export function rgbVersHsv({ r, g, b }) {
  const rn = r / 255, gn = g / 255, bn = b / 255;
  const max = Math.max(rn, gn, bn), min = Math.min(rn, gn, bn);
  const d = max - min;
  let h = 0;
  if (d > 0) {
    if (max === rn) h = ((gn - bn) / d) % 6;
    else if (max === gn) h = (bn - rn) / d + 2;
    else h = (rn - gn) / d + 4;
    h = Math.round(h * 60);
    if (h < 0) h += 360;
  }
  return { h, s: Math.round(max ? (d / max) * 100 : 0),
           v: Math.round(max * 100) };
}

export function hsvVersRgb({ h, s, v }) {
  const sn = s / 100, vn = v / 100;
  const c = vn * sn, hp = (((h % 360) + 360) % 360) / 60;
  const x = c * (1 - Math.abs((hp % 2) - 1));
  let [r, g, b] = hp < 1 ? [c, x, 0] : hp < 2 ? [x, c, 0]
    : hp < 3 ? [0, c, x] : hp < 4 ? [0, x, c]
    : hp < 5 ? [x, 0, c] : [c, 0, x];
  const m = vn - c;
  return { r: Math.round((r + m) * 255), g: Math.round((g + m) * 255),
           b: Math.round((b + m) * 255) };
}

export function rgbVersCmjn({ r, g, b }) {
  const rn = r / 255, gn = g / 255, bn = b / 255;
  const n = 1 - Math.max(rn, gn, bn);
  if (n >= 1) return { c: 0, m: 0, j: 0, n: 100 };
  const c = (1 - rn - n) / (1 - n), m = (1 - gn - n) / (1 - n),
        j = (1 - bn - n) / (1 - n);
  const p = (x) => Math.round(x * 100);
  return { c: p(c), m: p(m), j: p(j), n: p(n) };
}

export function cmjnVersRgb({ c, m, j, n }) {
  const f = (x) => Math.max(0, Math.min(100, +x || 0)) / 100;
  const nn = f(n);
  const v = (k) => Math.round(255 * (1 - f(k)) * (1 - nn));
  return { r: v(c), g: v(m), b: v(j) };
}

/* ── pur : la palette étendue par défaut — 12 teintes × 3 clartés + 12
   neutres, générée (jamais recopiée à la main) ── */
export function palette_defaut() {
  const out = [];
  for (let h = 0; h < 360; h += 30) {
    out.push(rgbVersHex(hsvVersRgb({ h, s: 88, v: 92 })));
    out.push(rgbVersHex(hsvVersRgb({ h, s: 62, v: 72 })));
    out.push(rgbVersHex(hsvVersRgb({ h, s: 38, v: 46 })));
  }
  for (let i = 0; i < 12; i++) {
    out.push(rgbVersHex(hsvVersRgb({ h: 0, s: 0, v: Math.round(100 - i * (100 / 11)) })));
  }
  return out;
}

/* ── pur : la palette DU DOCUMENT (sauvée avec lui, annulable) ── */
function _hexNorme(hex) {
  return rgbVersHex(hexVersRgb(hex));       // valide ET normalise la casse
}

export function op_palette_ajouter(doc, hex) {
  const h = _hexNorme(hex);
  if (!Array.isArray(doc.palette)) doc.palette = [];
  if (doc.palette.some((x) => String(x).toUpperCase() === h)) {
    throw new Error(`déjà dans la palette : ${h}`);
  }
  doc.palette.push(h);
  return h;
}

export function op_palette_retirer(doc, hex) {
  const h = _hexNorme(hex);
  const p = Array.isArray(doc.palette) ? doc.palette : [];
  const i = p.findIndex((x) => String(x).toUpperCase() === h);
  if (i < 0) throw new Error(`absente de la palette : ${h}`);
  p.splice(i, 1);
}
