// Plateau hexagonal — géométrie de la grille de découpe (miroir JS de
// backend/app/services/cards/plateau.py : mêmes formules, mêmes bornes).
// `FORMATS_HEX` est vérifié contre contract.FORMATS par
// backend/tests/test_cards_plateau_grille.py (p = min(trim_mm), orientation).
// Rang `r` et colonne `c` sont 1-based ; tout est en mm sauf le cadrage (pixels source).

export const FORMATS_HEX = {
  hex_p50: { p: 50, o: "pointe" },
  hex_p635: { p: 63.5, o: "pointe" },
  hex_p75: { p: 75, o: "pointe" },
  hex_p90: { p: 90, o: "pointe" },
  hex_f50: { p: 50, o: "plat" },
  hex_f635: { p: 63.5, o: "plat" },
  hex_f75: { p: 75, o: "plat" },
  hex_f90: { p: 90, o: "plat" },
};

export const COTE_MAX = 30;
export const TUILES_MAX = 500;
const FOND_PERDU_NATIF_MM = 3;   // = contract.BLEED_METRIC_MM (formats hexagonaux métriques)
const FOND_PERDU_MAX_MM = 10;    // = contract.BLEED_MM_MAX

/** Grille `colonnes` × `rangees` ; `bleedMm` absent = fond perdu natif. Lève Error si hors bornes. */
export function grille(fmt, colonnes, rangees, bleedMm) {
  const f = FORMATS_HEX[String(fmt || "").trim().toLowerCase()];
  if (!f) throw new Error("Format non hexagonal : " + fmt);
  if (!Number.isInteger(colonnes) || !Number.isInteger(rangees)
      || colonnes < 1 || rangees < 1 || colonnes > COTE_MAX || rangees > COTE_MAX) {
    throw new Error("colonnes et rangées doivent tenir entre 1 et " + COTE_MAX);
  }
  if (colonnes * rangees > TUILES_MAX) throw new Error(colonnes * rangees + " tuiles : " + TUILES_MAX + " au plus");
  const b = bleedMm == null ? FOND_PERDU_NATIF_MM : Number(bleedMm);
  if (!Number.isFinite(b) || b < 0 || b > FOND_PERDU_MAX_MM) {
    throw new Error("Le fond perdu doit tenir entre 0 et " + FOND_PERDU_MAX_MM + " mm");
  }
  const p = f.p;
  const h = 2 * p / Math.sqrt(3);
  const pas = 0.75 * h;
  const pointe = f.o === "pointe";
  const centres = [];
  for (let r = 1; r <= rangees; r++) {
    for (let c = 1; c <= colonnes; c++) {
      if (pointe) {
        centres.push({ r, c, x: b + p / 2 + (c - 1) * p + (r % 2 === 0 ? p / 2 : 0), y: b + h / 2 + (r - 1) * pas });
      } else {
        centres.push({ r, c, x: b + h / 2 + (c - 1) * pas, y: b + p / 2 + (r - 1) * p + (c % 2 === 0 ? p / 2 : 0) });
      }
    }
  }
  const largeurMm = pointe
    ? colonnes * p + (rangees > 1 ? p / 2 : 0) + 2 * b
    : h + (colonnes - 1) * pas + 2 * b;
  const hauteurMm = pointe
    ? h + (rangees - 1) * pas + 2 * b
    : rangees * p + (colonnes > 1 ? p / 2 : 0) + 2 * b;
  return { centres, largeurMm, hauteurMm };
}

/** Rectangle {x, y, w, h} en pixels source, du rapport extW/extH ; zoom ≥ 1, x et y ∈ [0, 1]. */
export function cadrageCouvrant(srcW, srcH, extW, extH, zoom = 1, x = 0.5, y = 0.5) {
  const rapport = extW / extH;
  const [w0, h0] = srcW / srcH > rapport ? [srcH * rapport, srcH] : [srcW, srcW / rapport];
  const z = Math.max(1, Number(zoom));
  const w = w0 / z, h = h0 / z;
  const fx = Math.min(1, Math.max(0, Number(x)));
  const fy = Math.min(1, Math.max(0, Number(y)));
  return { x: fx * (srcW - w), y: fy * (srcH - h), w, h };
}

/** Points par pouce réels : pixels source du cadrage / largeur imprimée. */
export function pppEffectif(rectW, largeurMm) {
  return rectW / (largeurMm / 25.4);
}
