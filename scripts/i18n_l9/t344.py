"""t344 (lot Scenario, B9, 29/10/2026) — « Comparer les moteurs » : un lien de plus dans le rail du 3D Studio.

Aucun script de frontend/studio3d de la liste du générateur ne change : la page du banc (comparer.html, comparer.js,
comparer_calc.js) est à part et se traduit par son propre dictionnaire (frontend/shared/i18n/comparatif3d.json, dzT).
index.html n'est jamais réécrit par L9 : le texte et l'infobulle du lien sont traduits par la surcouche (entrées H).
"""
from outils import H

ENTREES = [
    H("studio3d.t344_h.comparer", "Comparer les moteurs", "Compare engines"),
    H("studio3d.t344_h.comparer_aide",
      "Une image, plusieurs moteurs, le même éclairage : triangles, arêtes ouvertes, temps et coût côte à côte",
      "One image, several engines, the same lighting: triangles, open edges, time and cost side by side"),
]
