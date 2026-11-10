"""t477 (09/11/2026) — lot D5 « Couleur et motif », T3 : Recolorer l'illustration (modules NEUFS js/mod-recolorer.js et
js/mod-recolorerui.js, hors table ; l'entrée du menu Édition est dans le bloc Couleurs greffé par t476.py). Aucune
édition de BASE : le dialogue et ses refus, en entrées H. Les règles d'harmonie reprennent vectorlab.couleur.harm_*."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.recolorer.m_recolorer", "Recolorer l'illustration…", "Recolor Artwork…"),
    H("vectorlab.recolorer.d_titre", "Recolorer l'illustration", "Recolor Artwork"),
    H("vectorlab.recolorer.aucune_couleur", "La sélection n'a aucune couleur à recolorer.", "The selection has no color to recolor."),
    H("vectorlab.recolorer.actuelle", "Actuelle", "Current"),
    H("vectorlab.recolorer.nouvelle", "Nouvelle", "New"),
    H("vectorlab.recolorer.usages", "{n} usage(s)", "{n} use(s)"),
    H("vectorlab.recolorer.harmonie", "Harmonie depuis la couleur principale", "Harmony from the main color"),
    H("vectorlab.recolorer.appliquer_harmonie", "Harmoniser", "Harmonize"),
    H("vectorlab.recolorer.reduire", "Réduire à", "Reduce to"),
    H("vectorlab.recolorer.reduire_unite", "couleurs", "colors"),
    H("vectorlab.recolorer.reduire_btn", "Réduire", "Reduce"),
    H("vectorlab.recolorer.melanger", "Mélanger", "Shuffle"),
    H("vectorlab.recolorer.reinitialiser", "Réinitialiser", "Reset"),
]
