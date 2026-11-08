"""t456 (08/11/2026) — lot D2, T7 : poignées sur la toile des répétitions radiale et miroir, dans les modules NEUFS
js/mod-repeter.js et js/mod-repeterui.js (hors table). Aucune édition de module de BASE (le dessin se greffe au
crochet VL.surOverlay). Ici, les libellés accessibles des poignées, en entrées H."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.repeter.poignee_rayon", "Tirer pour changer le rayon de la rosace", "Drag to change the rosette radius"),
    H("vectorlab.repeter.poignee_nombre", "Tirer le long du cercle pour changer le nombre d'instances",
      "Drag along the circle to change the number of instances"),
    H("vectorlab.repeter.poignee_ecart", "Tirer pour éloigner ou rapprocher l'axe du miroir",
      "Drag to move the mirror axis closer or further"),
    H("vectorlab.repeter.poignee_angle", "Tirer autour de l'axe pour le faire tourner",
      "Drag around the axis to rotate it"),
]
