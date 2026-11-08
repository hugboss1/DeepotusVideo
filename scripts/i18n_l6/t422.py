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
      'export const cibles_b = (doc, ids) => _ciblesB(doc, ids);', {}),
    H("vectorlab.traces.sans_contour",
      "Vectoriser le contour : sélectionnez un tracé, une forme ou une ligne qui a un contour plein (épaisseur > 0, "
      "sans pointillés)",
      "Outline Stroke: select a path, shape or line with a solid stroke (width > 0, not dashed)"),
]
