// Motifs propres à la mission « media » (n'altère pas motifs.js).
// profil (tête de profil, voix), triTransport (triangle de la série transport), losangeCle (image clé).
"use strict";
const G = require("../geo.js"), M = require("../motifs.js");
const { placer, polyR } = M;
const MM = {};

/** profil — tête de profil tournée à droite (voix, générer/cloner/isoler la voix) : crâne, front, nez, lèvres,
 *  menton, cou. Dessinée dans la boîte x 2–15,4 / y 2–22 ; o.k (échelle autour de 12,12), o.dx, o.dy. */
MM.profil = (o = {}) => {
  const d = "M4.4 22C4 19.4 2.4 17.4 2.2 13.8C1.8 6.8 5.6 2 10.4 2C13.6 2 15.2 4.2 15.2 7" +
    "L15.4 8.8L17.4 12.2C17.6 12.7 17.3 13.1 16.8 13.1H15.6V14.2L15.9 15C16 15.5 15.7 15.9 15.2 15.9V17.4" +
    "C15.2 18.6 14.4 19.2 13.2 19.2H11.6V22Z";
  return placer(d, { k: o.k ?? 1, dx: o.dx || 0, dy: o.dy || 0 });
};

/** Triangle de la série transport, pointe à droite (ou à gauche), boîte x0–x1, y0–y1, angles arrondis 1. */
MM.tri = (x0, x1, y0, y1, dir = "droite", r = 1) => dir === "droite"
  ? polyR([[x0, y0], [x1, (y0 + y1) / 2], [x0, y1]], r)
  : polyR([[x1, y0], [x0, (y0 + y1) / 2], [x1, y1]], r);

/** Losange de clé (image clé) centré, demi-diagonales a (horizontale) et b (verticale). */
MM.losange = (cx, cy, a, b = a, r = 0.8) => polyR([[cx, cy - b], [cx + a, cy], [cx, cy + b], [cx - a, cy]], r);

module.exports = MM;
