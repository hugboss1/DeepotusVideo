"""t455 (08/11/2026) — lot D2, T6 : les répétitions et fusions vivantes dans l'interface. Tout vit dans le module NEUF
js/mod-repeterui.js (hors table) ; ici, les seules éditions des modules de BASE, chacune sur un fragment de sa ligne
qui ne recouvre aucun libellé déjà traduit (les éditions L6 sont positionnelles) :
  * core.js : l'import et l'init (initRepeterUI, avant initImage) ;
  * mod-menus.js : le bloc Répétition + Fusion du menu Vecteur, après « Formes paramétriques… » ;
  * mod-charpente.js : le préfixe « repeter: » ;
  * mod-tools.js : un Ctrl+clic sur une copie générée vise le groupe vivant (id_non_genere) ;
  * mod-doc.js : une copie générée, ou son intérieur, n'est jamais une cible des opérations (_objetsCibles) ;
  * mod-apparence2.js : la section « vivant » de la recette (VL.repeterUI.sectionApparence) et son bouton Options….
Les libellés et dialogues (zones vectorlab.repeter et vectorlab.fusion) sont saisis en entrées H."""
from outils import L, S, X, H  # noqa: F401

CORE = "js/core.js"
MENUS = "js/mod-menus.js"
CHARPENTE = "js/mod-charpente.js"
TOOLS = "js/mod-tools.js"
DOC = "js/mod-doc.js"
AP2 = "js/mod-apparence2.js"
NL = "\r\n"

_BLOC_MENU = NL.join([
    '"flyout:forme"),',
    '    "-",',
    '    e("repRadiale", T("vectorlab.repeter.m_radiale"), "repeter:radiale"), e("repGrille", T("vectorlab.repeter.m_grille"), "repeter:grille"), '
    'e("repMiroir", T("vectorlab.repeter.m_miroir"), "repeter:miroir"), e("repOptions", T("vectorlab.repeter.m_options"), "repeter:options"), '
    'e("repDecomposer", T("vectorlab.repeter.m_decomposer"), "repeter:decomposer"), "-",',
    '    e("fusCreer", T("vectorlab.fusion.m_creer"), "repeter:fusionner", "ctrl+alt+b"), e("fusOptions", T("vectorlab.fusion.m_options"), "repeter:fusionOptions"), '
    'e("fusAnnuler", T("vectorlab.fusion.m_annuler"), "repeter:fusionAnnuler"), e("fusTrajectoire", T("vectorlab.fusion.m_trajectoire"), "repeter:trajectoire"),',
    '    e("fusInverserTrajectoire", T("vectorlab.fusion.m_inverser_trajectoire"), "repeter:inverserTrajectoire"), '
    'e("fusInverserOrdre", T("vectorlab.fusion.m_inverser_ordre"), "repeter:inverserOrdre"), "-",',
    # t465 (lot D3) : le bloc Déformer, résolu par mod-repeterui.js (« repeter:def-<x> ») qui délègue à mod-deformerui.js
    '    e("defEnveloppe", T("vectorlab.deformer.m_enveloppe"), "repeter:def-enveloppe"), e("defDistorsion", T("vectorlab.deformer.m_distorsion"), "repeter:def-distorsion"), '
    'e("defTorsion", T("vectorlab.deformer.m_torsion"), "repeter:def-torsion"), e("defRugosite", T("vectorlab.deformer.m_rugosite"), "repeter:def-rugosite"),',
    '    e("defZigzag", T("vectorlab.deformer.m_zigzag"), "repeter:def-zigzag"), e("defGonfler", T("vectorlab.deformer.m_gonfler"), "repeter:def-gonfler"), '
    'e("defPointes", T("vectorlab.deformer.m_pointes"), "repeter:def-pointes"),',
    '    e("defEditer", T("vectorlab.deformer.m_editer"), "repeter:def-editer"), e("defAnnuler", T("vectorlab.deformer.m_annuler"), "repeter:def-annuler"),',
    # t479 (lot D5) : l'éditeur de motif, résolu par mod-recolorerui.js (« couleurs:motif_creer », « couleurs:motifs »)
    '    "-", e("motifCreer", T("vectorlab.motifs.m_creer"), "couleurs:motif_creer"), e("motifsDoc", T("vectorlab.motifs.m_liste"), "couleurs:motifs"),',
    # t481 (lot D5) : les pinceaux artistique, dispersion et motif, résolus par mod-recolorerui.js (« couleurs:pinceau_* »)
    '    "-", e("pinNouveau", T("vectorlab.pinceaux.m_nouveau"), "couleurs:pinceau_nouveau"), e("pinAppliquer", T("vectorlab.pinceaux.m_appliquer"), "couleurs:pinceau_appliquer"), '
    'e("pinOptions", T("vectorlab.pinceaux.m_options"), "couleurs:pinceau_options"), e("pinRetirer", T("vectorlab.pinceaux.m_retirer"), "couleurs:pinceau_retirer"), '
    'e("pinSupprimer", T("vectorlab.pinceaux.m_supprimer"), "couleurs:pinceau_supprimer"),',
])

ENTREES = [
    S(CORE, 43, 'import { initVitrail } from "./mod-vitrail.js";',
      'import { initRepeterUI } from "./mod-repeterui.js";   // t455 : lot D2\r\n'
      'import { initDeformerUI } from "./mod-deformerui.js";   // t465 : lot D3\r\nimport { initVitrail } from "./mod-vitrail.js";', {}),
    S(CORE, 788, "initImage(VL);",
      "initRepeterUI(VL);  // t455 : répétitions et fusions vivantes (menu Vecteur, Apparence, Ctrl+Alt+B)\r\n"
      "initDeformerUI(VL); // t465 : déformations vivantes (bloc Déformer, délégué par mod-repeterui)\r\ninitImage(VL);", {}),
    S(MENUS, 39, '"flyout:forme"),', _BLOC_MENU, {}),
    S(CHARPENTE, 83, 'if (pre === "ordre") return',
      'if (pre === "repeter") return VL.repeterUI ? VL.repeterUI.action(arg) : { peut: () => false, faire: () => {} };   // t455\r\n'
      '    if (pre === "ordre") return', {}),
    S(TOOLS, 11, 'import { noeuds_deplacer_segs } from "./mod-noeuds.js";',
      'import { noeuds_deplacer_segs } from "./mod-noeuds.js";\r\nimport { id_non_genere } from "./mod-repeter.js";   // t455', {}),
    S(TOOLS, 146, 'ev.ctrlKey && etat.outil === "select" ? idBrut :',
      'ev.ctrlKey && etat.outil === "select" ? id_non_genere(etat.doc, idBrut) :', {}),
    S(DOC, 504, 'if (voulu.has(o.id) && !o.verrou) yield',
      'if (voulu.has(o.id) && !o.verrou && !o.genere) yield', {}),
    S(DOC, 505, 'if (o.type === "groupe" && Array.isArray(o.enfants)) yield* dans(c, o.enfants);',
      'if (o.type === "groupe" && Array.isArray(o.enfants) && !o.genere) yield* dans(c, o.enfants);   // t455 : une copie générée n\'est jamais une cible', {}),
    S(AP2, 187, '      </details>` : ""}',
      '      </details>` : ""}\r\n'
      '      ${o1 && sel === 1 && VL.repeterUI ? VL.repeterUI.sectionApparence(o1) : ""}', {}),
    S(AP2, 263, 'on("a2Detacher", "click", () => VL.executer(op_derive_detacher, etat.selection[0]));',
      'on("a2Detacher", "click", () => VL.executer(op_derive_detacher, etat.selection[0]));\r\n'
      '    on("a2VivantOptions", "click", () => VL.repeterUI && VL.repeterUI.action("options").faire());   // t455', {}),
    # menus
    H("vectorlab.repeter.m_radiale", "Répétition radiale…", "Radial Repeat…"),
    H("vectorlab.repeter.m_grille", "Répétition en grille…", "Grid Repeat…"),
    H("vectorlab.repeter.m_miroir", "Répétition en miroir…", "Mirror Repeat…"),
    H("vectorlab.repeter.m_options", "Options de répétition ou de fusion…", "Repeat or Blend Options…"),
    H("vectorlab.repeter.m_decomposer", "Décomposer", "Expand", contexte=True),
    H("vectorlab.fusion.m_creer", "Créer une fusion", "Make Blend"),
    H("vectorlab.fusion.m_options", "Options de fusion…", "Blend Options…"),
    H("vectorlab.fusion.m_annuler", "Annuler la fusion", "Release Blend"),
    H("vectorlab.fusion.m_trajectoire", "Remplacer la trajectoire", "Replace Spine"),
    H("vectorlab.fusion.m_inverser_trajectoire", "Inverser la trajectoire", "Reverse Spine"),
    H("vectorlab.fusion.m_inverser_ordre", "Inverser l'ordre de superposition", "Reverse Front to Back"),
    # dialogues de répétition
    H("vectorlab.repeter.d_radiale", "Répétition radiale", "Radial Repeat"),
    H("vectorlab.repeter.d_grille", "Répétition en grille", "Grid Repeat"),
    H("vectorlab.repeter.d_miroir", "Répétition en miroir", "Mirror Repeat"),
    H("vectorlab.repeter.c_nombre", "Nombre d'instances", "Number of instances"),
    H("vectorlab.repeter.c_rayon", "Rayon (px)", "Radius (px)"),
    H("vectorlab.repeter.c_orienter", "Tourner les copies avec le cercle", "Rotate copies along the circle"),
    H("vectorlab.repeter.c_lignes", "Lignes", "Rows", contexte=True),
    H("vectorlab.repeter.c_colonnes", "Colonnes", "Columns", contexte=True),
    H("vectorlab.repeter.c_ecart_x", "Écart horizontal (px)", "Horizontal spacing (px)"),
    H("vectorlab.repeter.c_ecart_y", "Écart vertical (px)", "Vertical spacing (px)"),
    H("vectorlab.repeter.dec_aucun", "Grille droite", "Straight grid"),
    H("vectorlab.repeter.dec_brique_lignes", "Brique par lignes", "Brick by row"),
    H("vectorlab.repeter.dec_brique_colonnes", "Brique par colonnes", "Brick by column"),
    H("vectorlab.repeter.dec_hexagones", "Hexagones (plateau)", "Hexagons (game board)"),
    H("vectorlab.repeter.c_miroir_lignes", "Retourner une ligne sur deux", "Flip every other row"),
    H("vectorlab.repeter.c_miroir_colonnes", "Retourner une colonne sur deux", "Flip every other column"),
    H("vectorlab.repeter.c_angle", "Angle de l'axe (°)", "Axis angle (°)"),
    H("vectorlab.repeter.c_ecart", "Écart à l'axe (px)", "Distance to axis (px)"),
    # dialogue de fusion
    H("vectorlab.fusion.d_options", "Options de fusion", "Blend Options", contexte=True),
    H("vectorlab.fusion.mode_etapes", "Nombre d'étapes fixé", "Specified steps"),
    H("vectorlab.fusion.mode_distance", "Distance fixée", "Specified distance"),
    H("vectorlab.fusion.mode_couleur", "Couleur lissée", "Smooth color"),
    H("vectorlab.fusion.c_etapes", "Étapes", "Steps", contexte=True),
    H("vectorlab.fusion.c_pas", "Distance (px)", "Distance (px)"),
    H("vectorlab.fusion.c_orienter", "Orienter selon la trajectoire", "Align to path"),
    # onglet Apparence
    H("vectorlab.repeter.a_titre", "Répétition vivante", "Live repeat"),
    H("vectorlab.fusion.a_titre", "Fusion vivante", "Live blend"),
    H("vectorlab.repeter.a_options", "Options…", "Options…", contexte=True),
    H("vectorlab.repeter.a_decomposer_titre",
      "La répétition ou la fusion devient un groupe ordinaire : ses copies ne suivent plus la source",
      "The repeat or blend becomes an ordinary group: its copies no longer follow the source"),
    H("vectorlab.repeter.resume_radiale", "Radiale : {nombre} instances, rayon {rayon} px",
      "Radial: {nombre} instances, radius {rayon} px"),
    H("vectorlab.repeter.resume_grille", "Grille : {lignes} × {colonnes}", "Grid: {lignes} × {colonnes}"),
    H("vectorlab.repeter.resume_miroir", "Miroir : axe à {angle}°", "Mirror: axis at {angle}°"),
    H("vectorlab.fusion.resume", "{n} étapes entre les deux formes", "{n} steps between the two shapes"),
    H("vectorlab.fusion.resume_trajectoire", "{n} étapes le long de la trajectoire", "{n} steps along the spine"),
]
