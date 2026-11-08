"""t451 (08/11/2026) — lot D2, T2 : répétition en grille (briques, miroirs alternés, hexagones) dans le module NEUF
js/mod-repeter.js (hors table). Aucune édition de module de BASE : seulement les messages de la zone
vectorlab.repeter, en entrées H."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.repeter.lignes", "Répétition en grille : de {min} à {max} lignes",
      "Grid repeat: {min} to {max} rows"),
    H("vectorlab.repeter.colonnes", "Répétition en grille : de {min} à {max} colonnes",
      "Grid repeat: {min} to {max} columns"),
    H("vectorlab.repeter.une_seule", "Répétition en grille : il faut au moins deux cases",
      "Grid repeat: at least two cells are needed"),
    H("vectorlab.repeter.decalage", "Répétition en grille : décalage inconnu « {decalage} »",
      "Grid repeat: unknown offset “{decalage}”"),
    H("vectorlab.repeter.ecart",
      "Répétition en grille : cet écart négatif superpose toutes les copies, réduisez-le",
      "Grid repeat: this negative spacing stacks every copy, reduce it"),
    H("vectorlab.repeter.ecart_invalide", "Répétition en grille : l'écart doit être un nombre",
      "Grid repeat: the spacing must be a number"),
]
