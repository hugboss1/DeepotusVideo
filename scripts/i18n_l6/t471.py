"""t471 (09/11/2026) — lot D4 « Interop », T3 : lire la première page d'un PDF en objets vectoriels (module NEUF
js/mod-importpdf.js, hors table). Aucune édition de BASE : les refus traduits, en entrées H."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.importer.pdf_invalide", "Ce fichier n'est pas un PDF lisible (ou il n'a aucune page).",
      "This file is not a readable PDF (or it has no page)."),
    H("vectorlab.importer.pdf_chiffre", "Ce PDF est protégé (chiffré) : il ne peut pas être importé.",
      "This PDF is protected (encrypted): it cannot be imported."),
    H("vectorlab.importer.pdf_filtre", "Ce PDF utilise une compression non prise en charge ({filtre}).",
      "This PDF uses an unsupported compression ({filtre})."),
]
