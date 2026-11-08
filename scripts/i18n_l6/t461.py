"""t461 (08/11/2026) — lot D3, T2 : Distorsion libre et Torsion dans le module NEUF js/mod-deformer.js (hors table).
Aucune édition de module de BASE : les messages de la zone vectorlab.deformer, en entrées H."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.deformer.coins",
      "Distorsion libre : il faut le déplacement des quatre coins (deux nombres chacun)",
      "Free Distort: the offset of the four corners is needed (two numbers each)"),
    H("vectorlab.deformer.angle", "Torsion : l'angle va de {min} à {max}°", "Twist: the angle ranges from {min} to {max}°"),
]
