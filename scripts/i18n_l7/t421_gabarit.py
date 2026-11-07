"""t421 (cartes hexagonales, 07/11/2026, tâche 6) — le GABARIT DE DESSIN d'un format hexagonal, posé APRÈS L7
(comme t421.py).

mod-print.js (onglet Impression) : un bloc « Gabarit de dessin » en tête du panneau, avec deux liens de téléchargement
(PNG transparent, SVG en mm) vers GET /api/cards/gabarit/{format}.{png|svg}?dpi=&bleed_mm=&safe_mm= (adresse donnée par CF.gabaritUrl) ; `syncGabaritHex`
(appelée par `sync`, donc à chaque changement de format, de DPI ou de fond perdu) règle les adresses et n'affiche le bloc
que pour un hexagone. Des liens simples : l'adresse vient du CORE (CF.gabaritUrl), un lien de téléchargement n'est pas un appel. Rien ne change pour un rectangle : le bloc reste caché. Les sauts de ligne des insertions sont CRLF.
"""
from outils import S

F = "js/mod-print.js"
CRLF = chr(13) + chr(10)


def _crlf(t):
    return t.replace("\n", "\r\n")


_COMMENT = "/* ── GABARIT D'IMPRIMEUR (tache #83) : le choix qui regle tout le reste ── */"

_BLOC = r"""/* ── t421 : GABARIT DE DESSIN d'un format hexagonal (visible pour un hexagone seulement) ── */
      + '<div class="cf-print-gabhex" data-role="gabhex" hidden>'
      + '<details class="grp" open><summary>' + dzT("cartes.print.gabhex_titre") + '</summary><div class="grp-body">'
      + '<div class="btn-row">'
      + '<a class="btn sm" data-role="gabhex-png" href="#" download>' + ICO("dz-action-telecharger", 16, "cf-ic") + dzT("cartes.print.gabhex_png") + '</a>'
      + '<a class="btn sm" data-role="gabhex-svg" href="#" download>' + ICO("dz-action-telecharger", 16, "cf-ic") + dzT("cartes.print.gabhex_svg") + '</a>'
      + '</div>'
      + '<p class="hint">' + dzT("cartes.print.gabhex_aide") + '</p>'
      + '</div></details></div>'

      """

_FONCTION = r"""/* t421 : les liens du gabarit de dessin suivent le format, le DPI et le fond perdu du jeu ;
     le bloc n'est visible que pour un hexagone. */
  function syncGabaritHex(g) {
    const box = q('[data-role="gabhex"]');
    if (!box) return;
    const hex = !!g && g.forme === "hex";
    box.hidden = !hex;
    if (!hex) return;
    const fmt = CF.doc().format.fmt, opt = { dpi: g.dpi, bleed_mm: g.bleed_mm, safe_mm: g.safe_mm };
    ["png", "svg"].forEach((ext) => {
      const a = q('[data-role="gabhex-' + ext + '"]');
      if (a) a.setAttribute("href", CF.gabaritUrl(fmt, ext, opt));
    });
  }

  function sync() {
    const s = currentState(), f = CF.doc().format, g = CF.geom();
    syncGabaritHex(g);"""

ENTREES = [
    S(F, 718, _COMMENT, _crlf(_BLOC) + _COMMENT, {
        "cartes.print.gabhex_titre": ("Gabarit de dessin", "Drawing template"),
        "cartes.print.gabhex_png": ("Télécharger le gabarit (PNG)", "Download the template (PNG)"),
        "cartes.print.gabhex_svg": ("Télécharger le gabarit (SVG)", "Download the template (SVG)"),
        "cartes.print.gabhex_aide": (
            "Un PNG transparent à la taille de la toile et un SVG en millimètres montrent la coupe, le fond perdu, "
            "la zone sûre et le milieu de chaque côté, où placer vos symboles de liens. Ouvrez-le dans le Photolab "
            "ou le Vectorlab pour dessiner par-dessus.",
            "A transparent PNG at canvas size and an SVG in millimetres show the cut line, the bleed, the safe zone "
            "and the middle of each side, where your link symbols go. Open it in the Photolab or the Vectorlab to "
            "draw over it."),
    }),
    S(F, 2427, "function sync() {" + CRLF + "    const s = currentState(), f = CF.doc().format, g = CF.geom();",
      _crlf(_FONCTION), {}),
]
