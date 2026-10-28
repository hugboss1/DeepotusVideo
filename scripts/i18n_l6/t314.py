"""t314 (28/10/2026) — « Scanner un schéma… » et « Envoyer vers › Animation » (chantier boîte à outils C2, spec §7.3),
postérieurs à L6 : le module NEUF js/mod-schema.js (hors table : il n'existait pas à la BASE) porte toute la logique ;
les seules éditions des modules de BASE sont consignées ICI en éditions S, pour que la table reste réversible
(test_i18n_l6 [2]) : l'import et l'init dans js/core.js (après initExport : VL.svgCourant), deux entrées du menu
Fichier (js/mod-menus.js) et leurs deux actions (js/mod-charpente.js). Le dictionnaire de mod-schema.js (zone
vectorlab.schema) est saisi ici avec la première édition."""
from outils import L, S, X, H  # noqa: F401

CORE = "js/core.js"
MENUS = "js/mod-menus.js"
CHARPENTE = "js/mod-charpente.js"

DICO_SCHEMA = {
    "vectorlab.schema.titre": ("Scanner un schéma", "Scan a diagram"),
    "vectorlab.schema.fermer": ("Fermer", "Close"),
    "vectorlab.schema.depot": ("Déposez une photo d'illustration ou de schéma, ou cliquez pour choisir un fichier",
                               "Drop a photo of an illustration or a diagram, or click to choose a file"),
    "vectorlab.schema.detourage": ("Détourage", "Remove BG"),
    "vectorlab.schema.det_local": ("Fond uni ou image transparente (local, gratuit)",
                                   "Plain background or transparent image (local, free)"),
    "vectorlab.schema.det_rembg": ("rembg (local, gratuit)", "rembg (local, free)"),
    "vectorlab.schema.det_payant": ("{label} — {usd} $ (IA, payant)", "{label} — ${usd} (AI, paid)"),
    "vectorlab.schema.det_a_mesurer": ("{label} — prix à mesurer (IA, payant)", "{label} — price not measured yet (AI, paid)"),
    "vectorlab.schema.det_sans_cle": ("{label} — clé {cle} absente", "{label} — {cle} key missing"),
    "vectorlab.schema.langue": ("Langue des étiquettes", "Label language"),
    "vectorlab.schema.langue_fr": ("Français", "French"),
    "vectorlab.schema.langue_en": ("Anglais", "English"),
    "vectorlab.schema.aide": ("Chaque forme, flèche et étiquette devient un calque nommé ; l'ordre de révélation suit "
                              "les flèches.",
                              "Each shape, arrow and label becomes a named layer; the reveal order follows the arrows."),
    "vectorlab.schema.calques": ("Calques, dans l'ordre de révélation", "Layers, in reveal order"),
    "vectorlab.schema.choisir": ("Choisissez une image pour commencer.", "Choose an image to start."),
    "vectorlab.schema.pret": ("{nom} prête : lancez l'analyse.", "{nom} ready: run the analysis."),
    "vectorlab.schema.analyser": ("Analyser", "Analyze"),
    "vectorlab.schema.creer": ("Créer le document", "Create the document"),
    "vectorlab.schema.analyse_en_cours": ("Analyse en cours : détourage, lecture des étiquettes, séparation des "
                                          "éléments…",
                                          "Analyzing: background removal, reading labels, separating elements…"),
    "vectorlab.schema.bilan": ("{n} calques, {l} liens suivis par les flèches.",
                               "{n} layers, {l} links followed by the arrows."),
    "vectorlab.schema.avert_ocr": ("Lecture du texte indisponible : aucune étiquette.",
                                   "Text reading unavailable: no labels."),
    "vectorlab.schema.avert_fond": ("Fond estimé d'après le pourtour.", "Background estimated from the edges."),
    "vectorlab.schema.confirmer_cout": ("Le détourage par {modele} coûte environ {usd} $. Lancer l'analyse ?",
                                        "Background removal by {modele} costs about ${usd}. Run the analysis?"),
    "vectorlab.schema.confirmer_titre": ("Détourage payant", "Paid background removal"),
    "vectorlab.schema.confirmer_ok": ("Lancer", "Run"),
    "vectorlab.schema.cout_change": ("Le coût a changé ({usd} $) : relancez l'analyse pour le confirmer.",
                                     "The cost changed (${usd}): run the analysis again to confirm it."),
    "vectorlab.schema.aucun_element": ("Aucun élément trouvé dans cette image.", "No element found in this image."),
    "vectorlab.schema.pas_image": ("Ce fichier n'est pas une image.", "This file is not an image."),
    "vectorlab.schema.image_illisible": ("Découpe illisible.", "Unreadable cut-out."),
    "vectorlab.schema.trace_en_cours": ("Vectorisation {i}/{n}…", "Vectorizing {i}/{n}…"),
    "vectorlab.schema.creation_en_cours": ("Création du document…", "Creating document…"),
    "vectorlab.schema.cree": ("Document créé : {n} calques nommés.", "Document created: {n} named layers."),
    "vectorlab.schema.quitter_sale": ("Le document ouvert a des modifications non enregistrées. Le quitter pour le "
                                      "nouveau document ?",
                                      "The open document has unsaved changes. Leave it for the new document?"),
    "vectorlab.schema.nom_doc": ("Schéma", "Diagram"),
    "vectorlab.schema.nature_forme": ("Forme", "Shape"),
    "vectorlab.schema.nature_fleche": ("Flèche", "Arrow"),
    "vectorlab.schema.nature_etiquette": ("Étiquette", "Label"),
    "vectorlab.schema.nature_details": ("Détails", "Details"),
    "vectorlab.schema.rendu_calque": ("Rendu d'un calque impossible.", "A layer could not be rendered."),
    "vectorlab.schema.sans_doc": ("Ouvrez ou enregistrez d'abord un document.", "Open or save a document first."),
    "vectorlab.schema.envoi_vide": ("Aucun calque visible à animer.", "No visible layer to animate."),
    "vectorlab.schema.envoi_en_cours": ("Préparation des calques pour l'Animation {i}/{n}…",
                                        "Preparing layers for Animation {i}/{n}…"),
    "vectorlab.schema.envoi_ok": ("{n} calques envoyés au Studio : nœud Animation prêt.",
                                  "{n} layers sent to the Studio: Animation node ready."),
    "vectorlab.schema.envoi_seul": ("Le graphe « {nom} » est enregistré : ouvrez-le dans le Studio (Ouvrir un graphe).",
                                    "The graph “{nom}” is saved: open it in the Studio (Open a graph)."),
    "vectorlab.schema.envoi_titre": ("Envoyer vers Animation", "Send to Animation"),
    "vectorlab.schema.envoi_echec": ("Envoi vers Animation impossible : {m}", "Could not send to Animation: {m}"),
}

ENTREES = [
    S(CORE, 42, 'import { initExport } from "./mod-export.js";',
      'import { initExport } from "./mod-export.js";\r\nimport { initSchema } from "./mod-schema.js";', {}),
    S(CORE, 796, "initExport(VL);",
      "initExport(VL);\r\ninitSchema(VL);    // t314 : Scanner un schéma…, Envoyer vers › Animation — après initExport "
      "(VL.svgCourant)", DICO_SCHEMA),
    S(MENUS, 13, '"imageGenerer"), ',
      '"imageGenerer"), e("schema", T("vectorlab.menus.schema"), "schemaScanner"), ',
      {"vectorlab.menus.schema": ("Scanner un schéma…", "Scan a diagram…")}),
    S(MENUS, 14, '"expBible"), "-",',
      '"expBible"), e("schemaAnimation", T("vectorlab.menus.schema_animation"), "schemaAnimation"), "-",',
      {"vectorlab.menus.schema_animation": ("Envoyer vers › Animation", "Send to › Animation")}),
    S(CHARPENTE, 38, 'faire: () => clic("#expBible") },',
      'faire: () => clic("#expBible") },\r\n'
      '    schemaScanner: { peut: () => !!VL.schemaScanner, faire: () => VL.schemaScanner() },   // t314\r\n'
      '    schemaAnimation: { peut: () => !!(etat.doc && VL.schemaAnimation), faire: () => VL.schemaAnimation() },', {}),
]
