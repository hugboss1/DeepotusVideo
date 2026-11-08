"""t422 (08/11/2026) — lot D1 « Tracés » (spec 2026-11-08-illustrator-vectorlab-inventaire.md, plan
2026-11-08-vectorlab-d1-traces.md), postérieur à L6 : le module NEUF js/mod-traces.js (hors table : il n'existait
pas à la BASE) porte les commandes de tracé ; la seule édition d'un module de BASE est consignée ICI en édition S,
pour que la table reste réversible (test_i18n_l6 [2]) : mod-bool.js exporte son écriture d'un multipolygone en `d`
(multi_vers_d) et sa sélection d'objets déverrouillés (cibles_b), lues par mod-traces.js sans copie. Le
dictionnaire de mod-traces.js (zone vectorlab.traces) est saisi en entrées H."""
from outils import L, S, X, H  # noqa: F401

BOOL = "js/mod-bool.js"

ENTREES = [
    # rotation de 90° : cos(π/2) = 6e-15 au lieu de 0 ; martinez boucle sans fin sur ces quasi-colinéarités
    # (mesuré : contour_en_multi d'un rect tourné de 90° ne rend jamais la main) — les points transformés sont
    # arrondis au milliardième, bien sous la tolérance d'aplatissement (0,25 px)
    S(BOOL, 48, 'const _pt = (m, x, y) => [m[0] * x + m[2] * y + m[4],\r\n'
                '                          m[1] * x + m[3] * y + m[5]];',
      'const _net = (v) => Math.round(v * 1e9) / 1e9 + 0;   // t422 : 6e-15 → 0 (sinon martinez boucle)\r\n'
      'const _pt = (m, x, y) => [_net(m[0] * x + m[2] * y + m[4]),\r\n'
      '                          _net(m[1] * x + m[3] * y + m[5])];', {}),
    S(BOOL, 205, 'const _dDeMulti = (mp) => mp.map(_dDePoly).filter(Boolean).join(" ");',
      'const _dDeMulti = (mp) => mp.map(_dDePoly).filter(Boolean).join(" ");\r\n'
      '// t422 : lus par mod-traces.js (lot D1 « Tracés ») — l\'écriture d\'un multipolygone et les cibles '
      'déverrouillées\r\n'
      'export const multi_vers_d = (mp) => _dDeMulti(mp);\r\n'
      'export const cibles_b = (doc, ids) => _ciblesB(doc, ids);\r\n'
      'export const martinez = () => _martinez();   // t427 : intersection / diff de Diviser les objets en dessous', {}),
    H("vectorlab.traces.sans_contour",
      "Vectoriser le contour : sélectionnez un tracé, une forme ou une ligne qui a un contour plein (épaisseur > 0, "
      "sans pointillés)",
      "Outline Stroke: select a path, shape or line with a solid stroke (width > 0, not dashed)"),
    # t423 Simplifier
    H("vectorlab.traces.simplifier_rien", "Simplifier : sélectionnez un tracé ou une forme (pas un texte ni un groupe)",
      "Simplify: select a path or a shape (not a text or a group)"),
    H("vectorlab.traces.simplifier_deja", "Simplifier : ces tracés ont déjà le moins de points possible à cette précision",
      "Simplify: these paths already have the fewest points at this precision"),
    # t424 Ajouter des points d'ancrage
    H("vectorlab.traces.points_rien", "Ajouter des points : sélectionnez un tracé ou une forme (pas un texte ni un groupe)",
      "Add anchor points: select a path or a shape (not a text or a group)"),
    # t426 Nettoyer
    H("vectorlab.traces.nettoyer_rien", "Rien à nettoyer : aucun point isolé, objet invisible ni texte vide",
      "Nothing to clean up: no stray points, invisible objects or empty texts"),
    # t427 Diviser les objets en dessous
    H("vectorlab.traces.diviser_couteau", "Diviser les objets en dessous : sélectionnez UN tracé ou une forme posé au-dessus des objets à découper",
      "Divide Objects Below: select ONE path or shape placed above the objects to cut"),
    H("vectorlab.traces.diviser_rien", "Diviser les objets en dessous : ce tracé ne traverse aucun objet rempli déverrouillé placé sous lui",
      "Divide Objects Below: this path does not cross any unlocked filled object below it"),
    # t428 Lignes et colonnes
    H("vectorlab.traces.lignes_nombre", "Lignes et colonnes : de 1 à 100 lignes et colonnes (nombres entiers)",
      "Rows and Columns: 1 to 100 rows and columns (whole numbers)"),
    H("vectorlab.traces.lignes_taille", "Lignes et colonnes : les gouttières (≥ 0) ne laissent pas de place aux cellules",
      "Rows and Columns: the gutters (≥ 0) leave no room for the cells"),
    H("vectorlab.traces.lignes_objet", "Lignes et colonnes : sélectionnez un rectangle, une forme ou un tracé",
      "Rows and Columns: select a rectangle, a shape or a path"),
]

CORE = "js/core.js"
MENUS = "js/mod-menus.js"
CHARPENTE = "js/mod-charpente.js"
FLYOUT = "js/mod-flyout.js"

# t430 (T9) : les commandes de tracé dans l'interface — tout vit dans le module NEUF js/mod-tracesui.js ; ici, les
# seules éditions des modules de BASE : l'import et l'init (après initStyle : il emballe VL.actions.selection.booleen
# pour « Répéter le dernier Pathfinder »), le bloc Tracé + Pathfinder à la fin du menu Vecteur, le préfixe
# « traces: » résolu par mod-charpente, les six Pathfinder du menu détaché Sélection.
ENTREES_T430 = [
    S(CORE, 41, 'import { initStyle } from "./mod-style.js";',
      'import { initStyle } from "./mod-style.js";\r\nimport { initTracesUI } from "./mod-tracesui.js";', {}),
    S(CORE, 787, "initStyle(VL);",
      "initStyle(VL);\r\ninitTracesUI(VL);   // t430 : commandes de tracé (menu Vecteur, Pathfinder, Ctrl+4) — après initStyle", {}),
    S(MENUS, 40, "  ] },",
      '    "-",\r\n'
      '    e("tracesContour", T("vectorlab.traces.m_contour"), "traces:contour"), e("tracesSimplifier", T("vectorlab.traces.m_simplifier"), "traces:simplifier"), e("tracesAjouter", T("vectorlab.traces.m_ajouter"), "traces:ajouter"), e("tracesSupprimer", T("vectorlab.traces.m_supprimer"), "traces:supprimer"),\r\n'
      '    e("tracesMoyenne", T("vectorlab.traces.m_moyenne"), "traces:moyenne"), e("tracesNettoyer", T("vectorlab.traces.m_nettoyer"), "traces:nettoyer"), e("tracesDiviser", T("vectorlab.traces.m_diviser"), "traces:diviser"), e("tracesLignes", T("vectorlab.traces.m_lignes"), "traces:lignes"), "-",\r\n'
      '    e("pfExclusion", T("vectorlab.traces.pf_exclusion"), "traces:pf-exclusion"), e("pfSoustractionArriere", T("vectorlab.traces.pf_soustraction_arriere"), "traces:pf-soustraction_arriere"), e("pfDecoupage", T("vectorlab.traces.pf_decoupage"), "traces:pf-decoupage"),\r\n'
      '    e("pfFusion", T("vectorlab.traces.pf_fusion"), "traces:pf-fusion"), e("pfRecadrage", T("vectorlab.traces.pf_recadrage"), "traces:pf-recadrage"), e("pfContour", T("vectorlab.traces.pf_contour"), "traces:pf-contour"), e("pfRepeter", T("vectorlab.traces.m_repeter"), "traces:repeter", "ctrl+4"),\r\n'
      '  ] },', {}),
    S(CHARPENTE, 82, 'if (pre === "bool") return',
      'if (pre === "traces") return VL.traces ? VL.traces.action(arg) : { peut: () => false, faire: () => {} };   // t430\r\n    if (pre === "bool") return', {}),
    S(FLYOUT, 95, '...BOOL.map(([k, l, ic]) => e("bo-" + k, l, p.n >= 2, () => A.booleen(k), ic)),',
      '...BOOL.map(([k, l, ic]) => e("bo-" + k, l, p.n >= 2, () => A.booleen(k), ic)),\r\n'
      '      ...(c.actions && c.actions.traces ? c.actions.traces.flyoutBool(e, p) : []),   // t430 : les six Pathfinder', {}),
    # libellés et dialogues (mod-tracesui.js, hors table)
    H("vectorlab.traces.m_contour", "Vectoriser le contour", "Outline Stroke"),
    H("vectorlab.traces.m_simplifier", "Simplifier…", "Simplify…"),
    H("vectorlab.traces.m_ajouter", "Ajouter des points d'ancrage", "Add Anchor Points"),
    H("vectorlab.traces.m_supprimer", "Supprimer des points d'ancrage", "Remove Anchor Points"),
    H("vectorlab.traces.m_moyenne", "Moyenne…", "Average…"),
    H("vectorlab.traces.m_nettoyer", "Nettoyer…", "Clean Up…"),
    H("vectorlab.traces.m_diviser", "Diviser les objets en dessous", "Divide Objects Below"),
    H("vectorlab.traces.m_lignes", "Lignes et colonnes…", "Split Into Grid…"),
    H("vectorlab.traces.m_repeter", "Répéter le dernier Pathfinder", "Repeat Pathfinder"),
    H("vectorlab.traces.pf_exclusion", "Exclusion", "Exclude", contexte=True),
    H("vectorlab.traces.pf_soustraction_arriere", "Soustraction arrière", "Minus Back"),
    H("vectorlab.traces.pf_decoupage", "Découpage", "Trim", contexte=True),
    H("vectorlab.traces.pf_fusion", "Fusion", "Merge", contexte=True),
    H("vectorlab.traces.pf_recadrage", "Recadrage", "Crop", contexte=True),
    H("vectorlab.traces.pf_contour", "Contour", "Outline", contexte=True),
    H("vectorlab.traces.annuler", "Annuler", "Cancel"),
    H("vectorlab.traces.appliquer", "Appliquer", "Apply"),
    H("vectorlab.traces.simplifier_titre", "Simplifier", "Simplify"),
    H("vectorlab.traces.precision", "Précision (%)", "Precision (%)"),
    H("vectorlab.traces.droites", "Lignes droites", "Straight lines"),
    H("vectorlab.traces.simplifier_apercu", "Points : {avant} → {apres}", "Points: {avant} → {apres}"),
    H("vectorlab.traces.moyenne_titre", "Moyenne", "Average", contexte=True),
    H("vectorlab.traces.moyenne_h", "Horizontale (même hauteur)", "Horizontal (same height)"),
    H("vectorlab.traces.moyenne_v", "Verticale (même position en x)", "Vertical (same x position)"),
    H("vectorlab.traces.moyenne_deux", "Les deux", "Both"),
    H("vectorlab.traces.nettoyer_titre", "Nettoyer", "Clean Up"),
    H("vectorlab.traces.n_isoles", "Points isolés", "Stray points"),
    H("vectorlab.traces.n_invisibles", "Objets sans fond ni contour", "Unpainted objects"),
    H("vectorlab.traces.n_textes", "Textes vides", "Empty texts"),
    H("vectorlab.traces.nettoyer_bilan_un", "1 objet supprimé", "1 object deleted"),
    H("vectorlab.traces.nettoyer_bilan_plusieurs", "{n} objets supprimés", "{n} objects deleted"),
    H("vectorlab.traces.lignes_titre", "Lignes et colonnes", "Split Into Grid"),
    H("vectorlab.traces.l_lignes", "Lignes", "Rows", contexte=True),
    H("vectorlab.traces.l_colonnes", "Colonnes", "Columns"),
    H("vectorlab.traces.l_g_lignes", "Gouttière entre les lignes", "Gutter between rows"),
    H("vectorlab.traces.l_g_colonnes", "Gouttière entre les colonnes", "Gutter between columns"),
    H("vectorlab.traces.l_reperes", "Ajouter des repères", "Add guides"),
    H("vectorlab.traces.repeter_rien", "Aucun Pathfinder à répéter sur cette sélection", "No Pathfinder to repeat on this selection"),
]
ENTREES = ENTREES + ENTREES_T430
