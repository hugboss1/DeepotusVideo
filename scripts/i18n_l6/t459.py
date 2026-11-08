"""t459 (08/11/2026) — panneau de droite : les sections INTERNES (Effets, Fusion & contours, Remplissage +…) gardent
leur état ouvert / replié d'un rendu à l'autre. Le module NEUF js/mod-sections.js (hors table) porte la mémoire ; les
seules éditions de BASE sont ici : l'import et l'init dans core.js, juste après initPanneaux."""
from outils import L, S, X, H  # noqa: F401

CORE = "js/core.js"

ENTREES = [
    S(CORE, 20, 'import { initPanneaux } from "./mod-panneaux.js";',
      'import { initPanneaux } from "./mod-panneaux.js";\r\nimport { initSections } from "./mod-sections.js";   // t459', {}),
    S(CORE, 822, "initPanneaux(VL);   // sections du panneau de droite : état ouvert / replié mémorisé (dz_vl_panneaux)",
      "initPanneaux(VL);   // sections du panneau de droite : état ouvert / replié mémorisé (dz_vl_panneaux)\r\n"
      "initSections(VL);   // t459 : les sections internes reconstruites gardent leur état ouvert / replié", {}),
]
