"""t476 (09/11/2026) — lot D5 « Couleur et motif », T2 : Édition › Couleurs. Les transformations vivent dans les
modules NEUFS js/mod-recolorer.js et js/mod-recolorerui.js (hors table) ; ici, les seules éditions des modules de BASE,
chacune sur un fragment de sa ligne qui ne recouvre aucun libellé déjà traduit :
  * core.js : l'import et l'init (initRecolorerUI, avant initTrace) ;
  * mod-menus.js : le bloc Couleurs du menu Édition, avant « Créer un style » (avec Recolorer l'illustration, t477) ;
  * mod-charpente.js : le préfixe « couleurs: ».
Les libellés, les dialogues et les refus sont saisis en entrées H."""
from outils import L, S, X, H  # noqa: F401

CORE = "js/core.js"
MENUS = "js/mod-menus.js"
CHARPENTE = "js/mod-charpente.js"

_BLOC = (
    '    e("coulRecolorer", T("vectorlab.recolorer.m_recolorer"), "couleurs:recolorer"), '
    'e("coulInverser", T("vectorlab.couleurs.m_inverser"), "couleurs:inverser"), e("coulGris", T("vectorlab.couleurs.m_gris"), "couleurs:gris"), '
    'e("coulSaturer", T("vectorlab.couleurs.m_saturer"), "couleurs:saturer"), e("coulEquilibre", T("vectorlab.couleurs.m_equilibre"), "couleurs:equilibre"),\r\n'
    '    e("coulFusionH", T("vectorlab.couleurs.m_fusion_h"), "couleurs:fusion_h"), e("coulFusionV", T("vectorlab.couleurs.m_fusion_v"), "couleurs:fusion_v"), '
    'e("coulFusionZ", T("vectorlab.couleurs.m_fusion_z"), "couleurs:fusion_z"), "-",\r\n'
    '    e("style", '
)

ENTREES = [
    S(CORE, 45, 'import { initIA } from "./mod-ia.js";',
      'import { initRecolorerUI } from "./mod-recolorerui.js";   // t476 : lot D5\r\nimport { initIA } from "./mod-ia.js";', {}),
    S(CORE, 789, "initTrace(VL);",
      "initRecolorerUI(VL); // t476 : Édition › Couleurs (inverser, gris, saturer, équilibre, fusions)\r\ninitTrace(VL);", {}),
    S(MENUS, 21, '    e("style", ', _BLOC, {}),
    S(CHARPENTE, 85, 'if (pre === "pixel") return',
      'if (pre === "couleurs") return VL.couleursUI ? VL.couleursUI.action(arg) : { peut: () => false, faire: () => {} };   // t476\r\n'
      '    if (pre === "pixel") return', {}),

    H("vectorlab.couleurs.m_inverser", "Inverser les couleurs", "Invert Colors"),
    H("vectorlab.couleurs.m_gris", "Convertir en niveaux de gris", "Convert to Grayscale"),
    H("vectorlab.couleurs.m_saturer", "Saturation…", "Saturate…"),
    H("vectorlab.couleurs.m_equilibre", "Régler l'équilibre des couleurs…", "Adjust Color Balance…"),
    H("vectorlab.couleurs.m_fusion_h", "Fusion horizontale", "Blend Horizontally"),
    H("vectorlab.couleurs.m_fusion_v", "Fusion verticale", "Blend Vertically"),
    H("vectorlab.couleurs.m_fusion_z", "Fusion avant-arrière", "Blend Front to Back"),
    H("vectorlab.couleurs.d_saturer", "Saturation des couleurs sélectionnées", "Saturation of the selected colors"),
    H("vectorlab.couleurs.c_pct", "Intensité (−100 = gris, +100 = saturation doublée)", "Intensity (−100 = grey, +100 = doubled saturation)"),
    H("vectorlab.couleurs.d_equilibre", "Équilibre des couleurs sélectionnées", "Color balance of the selection"),
    H("vectorlab.couleurs.o_rvb", "Rouge, vert, bleu", "Red, green, blue"),
    H("vectorlab.couleurs.o_cmjn", "Cyan, magenta, jaune, noir", "Cyan, magenta, yellow, black"),
    H("vectorlab.couleurs.c_a", "Rouge ou cyan (%)", "Red or cyan (%)"),
    H("vectorlab.couleurs.c_b", "Vert ou magenta (%)", "Green or magenta (%)"),
    H("vectorlab.couleurs.c_c", "Bleu ou jaune (%)", "Blue or yellow (%)"),
    H("vectorlab.couleurs.c_d", "Noir (%), en CMJN seulement", "Black (%), CMYK only"),
    H("vectorlab.couleurs.borne", "Valeur hors bornes : de {min} à {max}.", "Value out of range: from {min} to {max}."),
    H("vectorlab.couleurs.mode", "Mode de couleur inconnu : « {mode} ».", "Unknown color mode: “{mode}”."),
    H("vectorlab.couleurs.sens", "Sens de fusion inconnu : « {sens} ».", "Unknown blend direction: “{sens}”."),
    H("vectorlab.couleurs.fusion_trois", "Il faut au moins trois objets à fond de couleur simple pour fusionner.",
      "Blending needs at least three objects filled with a plain color."),
]
