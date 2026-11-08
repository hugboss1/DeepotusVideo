"""t421 (cartes hexagonales, 08/11/2026, vague finale) — posé APRÈS L7 (comme t421.py et t421_apercu.py).

core.js :
- `setFormatInternal` : un hexagone est TOUJOURS à coin 0 (ruling : le fichier de coupe SVG/DXF, le trait imprimé, le
  masque de planche et le gabarit n'ont pas d'arcs ; l'aperçu ne doit pas arrondir seul). Même règle que
  `normalize_format` du backend. Tout passe par là : le sélecteur, les champs, et `hydrate` (document relu).
- `syncFormatWidget` : sur un hexagone, le champ « Rayon de coin » est GRISÉ (désactivé) et son infobulle (sur le champ
  et sur son libellé, qu'un champ désactivé peut ne pas montrer) dit pourquoi ; en rectangle il redevient actif et
  l'infobulle part. Un rectangle ne change d'aucun pixel : la branche rectangle ne touche le champ que s'il était grisé.
Les sauts de ligne des insertions sont CRLF, comme la source.
"""
from outils import S

C = "js/core.js"


def _crlf(t):
    return t.replace("\n", "\r\n")


_FORCE = r"""    /* t421 (vague finale) : un hexagone est TOUJOURS a sommets vifs (coin 0), comme normalize_format */
    if (FMT_BY_ID[out.fmt].forme === "hex") out.corner_mm = 0;
    DOC.format = out;"""

_CHAMP = r"""    const c1 = el("#cornerInp"); if (c1) c1.value = f.corner_mm;
    /* t421 (vague finale) : un hexagone garde des sommets vifs — le champ est grise et dit pourquoi */
    if (c1) {
      const lb = typeof c1.closest === "function" ? c1.closest("label") : null;
      if (g.forme === "hex") {
        c1.disabled = true;
        c1.title = dzT("cartes.core.coin_hex");
        if (lb) lb.title = c1.title;
      } else if (c1.disabled) {
        c1.disabled = false;
        c1.removeAttribute("title");
        if (lb) lb.removeAttribute("title");
      }
    }"""

_DICO = {
    "cartes.core.coin_hex": (
        "Un hexagone garde des sommets vifs : le fichier de coupe et le trait imprimé n'ont pas d'arrondi.",
        "A hexagon keeps sharp corners: the cut file and the printed cut line have no rounding."),
}

ENTREES = [
    S(C, 420, "    DOC.format = out;", _crlf(_FORCE), {}),
    S(C, 1282, '    const c1 = el("#cornerInp"); if (c1) c1.value = f.corner_mm;', _crlf(_CHAMP), _DICO),
]
