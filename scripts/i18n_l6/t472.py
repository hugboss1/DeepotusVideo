"""t472 (09/11/2026) — lot D4 « Interop », T4 : importer un PDF dans le document (module js/mod-importerui.js,
hors table). Aucune édition de BASE : la lecture, les raisons propres au PDF et le nombre de pages, en entrées H."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.importer.pdf_lecture", "Lecture de « {nom} »…", "Reading “{nom}”…"),
    H("vectorlab.importer.pdf_pages", "(page 1 sur {n})", "(page 1 of {n})"),
    H("vectorlab.importer.r_texte", "textes", "texts"),
    H("vectorlab.importer.r_motif", "motifs (en gris)", "patterns (as grey)"),
]
