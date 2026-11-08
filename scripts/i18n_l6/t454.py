"""t454 (08/11/2026) — lot D2, T5 : trajectoire, inversions et options de la fusion, dans le module NEUF
js/mod-repeter.js (hors table). Aucune édition de module de BASE (mod-traces.js, qui protège la trajectoire
invisible de Nettoyer, est un module neuf de D1, hors table lui aussi). Ici, les messages de la zone
vectorlab.fusion, en entrées H."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.fusion.pas_fusion", "{id} n'est pas une fusion", "{id} is not a blend"),
    H("vectorlab.fusion.deja_trajectoire",
      "Cette fusion suit déjà un tracé : décomposez-la pour en changer",
      "This blend already follows a path: expand it to change it"),
    H("vectorlab.fusion.trajectoire_introuvable",
      "Remplacer la trajectoire : sélectionnez la fusion et un tracé du même document",
      "Replace Spine: select the blend and a path in the same document"),
    H("vectorlab.fusion.trajectoire_type",
      "Remplacer la trajectoire : il faut un tracé, une forme, un rectangle ou une ellipse qui a une longueur",
      "Replace Spine: a path, shape, rectangle or ellipse with some length is needed"),
]
