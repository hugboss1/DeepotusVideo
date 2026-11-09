"""t479 (09/11/2026) — lot D5 « Couleur et motif », T5 : l'éditeur de motif (module NEUF js/mod-motifsui.js, hors
table ; les deux entrées du menu Vecteur sont au bout du bloc D2 / D3 de t455.py, résolues par le préfixe « couleurs: »
de t476.py). Aucune édition de BASE : les libellés, en entrées H."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.motifs.m_creer", "Créer un motif…", "Make Pattern…"),
    H("vectorlab.motifs.m_liste", "Motifs du document…", "Document Patterns…"),
    H("vectorlab.motifs.d_creer", "Créer un motif depuis la sélection", "Make a pattern from the selection"),
    H("vectorlab.motifs.d_regler", "Réglages du motif {id}", "Settings of pattern {id}"),
    H("vectorlab.motifs.d_liste", "Motifs du document", "Document patterns"),
    H("vectorlab.motifs.p_grille", "Grille", "Grid"),
    H("vectorlab.motifs.p_brique_lignes", "Brique par lignes", "Brick by row"),
    H("vectorlab.motifs.p_brique_colonnes", "Brique par colonnes", "Brick by column"),
    H("vectorlab.motifs.p_hexagone", "Hexagone", "Hexagon"),
    H("vectorlab.motifs.c_eh", "Espacement horizontal (px, négatif = chevauchement)", "Horizontal spacing (px, negative = overlap)"),
    H("vectorlab.motifs.c_ev", "Espacement vertical (px, négatif = chevauchement)", "Vertical spacing (px, negative = overlap)"),
    H("vectorlab.motifs.c_fond_actif", "Fond de tuile", "Tile background"),
    H("vectorlab.motifs.c_fond", "Couleur du fond", "Background color"),
    H("vectorlab.motifs.cree", "Motif {id} créé : appliquez-le depuis Vecteur › Motifs du document…",
      "Pattern {id} created: apply it from Vector › Document Patterns…"),
    H("vectorlab.motifs.aucun", "Ce document n'a aucun motif fait d'objets : créez-en un avec Vecteur › Créer un motif…",
      "This document has no pattern made of objects: make one with Vector › Make Pattern…"),
    H("vectorlab.motifs.usages", "{n} objet(s) rempli(s)", "{n} filled object(s)"),
    H("vectorlab.motifs.appliquer", "Appliquer à la sélection", "Apply to selection"),
    H("vectorlab.motifs.regler", "Réglages…", "Settings…"),
    H("vectorlab.motifs.remplacer", "Remplacer par la sélection", "Replace with selection"),
    H("vectorlab.motifs.supprimer", "Supprimer le motif", "Delete pattern"),
    H("vectorlab.motifs.fermer", "Fermer", "Close"),
    H("vectorlab.motifs.selection_requise", "Sélectionnez les objets à remplir de ce motif.", "Select the objects to fill with this pattern."),
]
