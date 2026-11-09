"""t470 (09/11/2026) — lot D4 « Interop », T2 : importer un SVG dans le document. L'opération (js/mod-importsvg.js)
et l'interface (js/mod-importerui.js) sont des modules NEUFS (hors table) ; ici, les seules éditions des modules de
BASE, chacune sur un fragment de sa ligne qui ne recouvre aucun libellé déjà traduit :
  * core.js : l'import et l'init (initImporterUI, avant initBiblio) ;
  * mod-menus.js : l'entrée « Importer (SVG, PDF)… » du menu Fichier, avant « Insérer une image… » ;
  * mod-charpente.js : l'action « importer ».
Les libellés, le bilan et les refus sont saisis en entrées H."""
from outils import L, S, X, H  # noqa: F401

CORE = "js/core.js"
MENUS = "js/mod-menus.js"
CHARPENTE = "js/mod-charpente.js"

ENTREES = [
    S(CORE, 44, 'import { initBiblio } from "./mod-biblio.js";',
      'import { initImporterUI } from "./mod-importerui.js";   // t470 : lot D4\r\nimport { initBiblio } from "./mod-biblio.js";', {}),
    S(CORE, 800, "initBiblio(VL);",
      "initImporterUI(VL); // t470 : Fichier › Importer (SVG, PDF), SVG collé ou déposé sur la toile\r\ninitBiblio(VL);", {}),
    S(MENUS, 13, '    e("inserer", ',
      '    e("importer", T("vectorlab.importer.m_importer"), "importer"), e("inserer", ', {}),
    S(CHARPENTE, 28, "    imageFichier: {",
      "    importer: { peut: () => !!(etat.doc && VL.importer), faire: () => VL.importer.ouvrir() },   // t470\r\n"
      "    imageFichier: {", {}),

    H("vectorlab.importer.m_importer", "Importer (SVG, PDF)…", "Import (SVG, PDF)…"),
    H("vectorlab.importer.aucun_doc", "Ouvrez ou créez un document avant d'importer.",
      "Open or create a document before importing."),
    H("vectorlab.importer.vide", "Rien à importer : le fichier ne contient aucun objet dessiné.",
      "Nothing to import: the file contains no drawn object."),
    H("vectorlab.importer.type_inconnu", "Seuls les fichiers SVG et PDF s'importent.",
      "Only SVG and PDF files can be imported."),
    H("vectorlab.importer.bilan", "{n} objet(s) importé(s)", "{n} object(s) imported"),
    H("vectorlab.importer.non_repris", "{bilan} ; non repris : {liste}", "{bilan}; not carried over: {liste}"),
    H("vectorlab.importer.r_cache", "éléments cachés", "hidden elements"),
    H("vectorlab.importer.r_image", "images liées", "linked images"),
    H("vectorlab.importer.r_inconnu", "éléments inconnus", "unknown elements"),
    H("vectorlab.importer.r_filtre", "filtres", "filters"),
    H("vectorlab.importer.r_decoupe", "découpes", "clipping paths"),
    H("vectorlab.importer.r_masque", "masques", "masks"),
    H("vectorlab.importer.r_degrade", "dégradés (1re couleur gardée)", "gradients (first color kept)"),
    H("vectorlab.importer.r_use", "références absentes", "missing references"),
    H("vectorlab.importer.r_chemin", "tracés illisibles", "unreadable paths"),
]
