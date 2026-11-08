"""t464 (08/11/2026) — lot D3, T5 : Pointes de flèche dans le module NEUF js/mod-deformer.js (hors table). Aucune
édition de module de BASE : les messages de la zone vectorlab.deformer, en entrées H."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.deformer.ouvert", "Pointes de flèche : sélectionnez un tracé ouvert (une ligne, pas une forme fermée)",
      "Arrowheads: select an open path (a line, not a closed shape)"),
    H("vectorlab.deformer.pointe", "Pointes de flèche : style inconnu « {pointe} »", "Arrowheads: unknown style “{pointe}”"),
    H("vectorlab.deformer.aucune_pointe", "Pointes de flèche : choisissez une pointe au début, à la fin, ou aux deux",
      "Arrowheads: choose a head at the start, at the end, or both"),
]
