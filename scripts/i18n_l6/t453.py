"""t453 (08/11/2026) — lot D2, T4 : fusion (blend) de deux formes dans le module NEUF js/mod-repeter.js (hors
table). La seule édition de BASE (op_derive_detacher décompose aussi une fusion) est portée par l'entrée S de
t450.py. Ici, les messages de la zone vectorlab.fusion, en entrées H."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.fusion.deux", "Fusion : sélectionnez exactement deux objets",
      "Blend: select exactly two objects"),
    H("vectorlab.fusion.type",
      "Fusion : seuls les rectangles, ellipses, formes et tracés se fusionnent (pas un texte, une image ni un groupe)",
      "Blend: only rectangles, ellipses, shapes and paths can be blended (not a text, an image or a group)"),
    H("vectorlab.fusion.mode", "Fusion : espacement inconnu « {mode} »",
      "Blend: unknown spacing “{mode}”"),
    H("vectorlab.fusion.etapes", "Fusion : de {min} à {max} étapes",
      "Blend: {min} to {max} steps"),
    H("vectorlab.fusion.pas", "Fusion : la distance entre deux étapes doit être positive",
      "Blend: the distance between two steps must be positive"),
]
