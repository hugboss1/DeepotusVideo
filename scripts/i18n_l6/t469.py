"""t469 (09/11/2026) — lot D4 « Interop », T1 : lire un SVG en objets du Vectorlab (module NEUF
js/mod-importsvg.js, hors table). Aucune édition de BASE : les refus traduits, en entrées H."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.importer.xml_invalide", "Ce fichier n'est pas un SVG lisible (XML mal formé).",
      "This file is not a readable SVG (malformed XML)."),
    H("vectorlab.importer.svg_invalide", "Ce fichier ne contient pas de dessin SVG (aucune balise <svg>).",
      "This file contains no SVG drawing (no <svg> tag)."),
    H("vectorlab.importer.chemin_invalide", "Un tracé du SVG est illisible : il ne peut pas être importé.",
      "A path in the SVG is unreadable: it cannot be imported."),
    H("vectorlab.importer.trop_grand", "Ce SVG est trop gros ({n} éléments au plus).",
      "This SVG is too large ({n} elements at most)."),
]
