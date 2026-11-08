"""Plateau hexagonal, lot 1 (08/11/2026) — Vectorlab : Export › Découper en hexagones… (js/mod-export.js, postérieur à L6).
Le module NEUF js/mod-decoupehex.js (hors table : il n'existait pas à la BASE) porte la logique ; les seules éditions
du module de BASE sont consignées ICI, pour que la table reste réversible (test_i18n_l6 [2]) : l'import, le nom déposé
(k arrondi à deux décimales), la règle d'opacité (`opts.opaque`, fonction transparentExport), le libellé et le clic du
bouton #expPlateau (index.html porte le bouton vide, le texte vient de T) et l'exposition de rasteriser."""
from outils import L, S, X, H  # noqa: F401

EXPORT = "js/mod-export.js"

ENTREES = [
    S(EXPORT, 9, 'import { image_hrefs, image_rev_max } from "./mod-image.js";',
      'import { image_hrefs, image_rev_max } from "./mod-image.js";\r\n'
      'import { decouperHex } from "./mod-decoupehex.js";\r\n'
      '\r\n'
      '/** Nom déposé dans la Bibliothèque : vector_<docId><suffixe>_<k>x[_t].png. Un k non entier (plateau) est arrondi à\r\n'
      '    deux décimales : le nom reste sûr pour un fichier ; les exports 1×/2×/4× gardent leur nom. */\r\n'
      'export function nomExportPNG(docId, suffixe, k, transparent) {\r\n'
      '  return `vector_${docId}${suffixe || ""}_${Math.round(k * 100) / 100}x${transparent ? "_t" : ""}.png`;\r\n'
      '}\r\n'
      '\r\n'
      "/** Fond transparent ou non : l'export plateau (`opts.opaque`) ne lit jamais la case, les autres la suivent. */\r\n"
      'export function transparentExport(opts, caseCochee) {\r\n'
      '  return opts.opaque ? false : !!caseCochee;\r\n'
      '}', {}),
    S(EXPORT, 76, 'const transparent = $("#expTransparent").checked;',
      'const transparent = transparentExport(opts, $("#expTransparent").checked);', {}),
    S(EXPORT, 80, 'const nom = `vector_${etat.docId}${opts.suffixe || ""}_${k}x${transparent ? "_t" : ""}.png`;',
      "const nom = nomExportPNG(etat.docId, opts.suffixe, k, transparent);", {}),
    S(EXPORT, 149, '  $("#expBible").addEventListener("click", garde(versBible));',
      '  $("#expPlateau").textContent = T("vectorlab.export.plateau");\r\n'
      '  $("#expPlateau").title = T("vectorlab.export.plateau_titre");\r\n'
      '  $("#expPlateau").addEventListener("click", garde(() => decouperHex(VL, T)));\r\n'
      '  $("#expBible").addEventListener("click", garde(versBible));',
      {"vectorlab.export.plateau": ("Découper en hexagones…", "Cut into hexagons…"),
       "vectorlab.export.plateau_titre": (
           "Découpe le document en tuiles hexagonales pour créer un jeu plateau du Card Forge — exporté en PNG, "
           "300 ppp sur la grille choisie ; les zones sans fond deviennent blanches",
           "Cuts the document into hexagonal tiles to create a Card Forge board deck — exported as a PNG, "
           "300 ppi on the chosen grid; areas without a background become white")}),
    S(EXPORT, 152, "  VL.exporterPNG = exporterPNG;      // la preuve et les phases suivantes",
      "  VL.exporterPNG = exporterPNG;      // la preuve et les phases suivantes\r\n"
      "  VL.rasteriser = rasteriser;        // plateau (lot 1) : l'aperçu du dialogue « Découper en hexagones »", {}),
]
