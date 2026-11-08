"""t421 (cartes hexagonales, 07/11/2026, tâche 6) — le GABARIT DE DESSIN d'un format hexagonal, posé APRÈS L7
(comme t421.py).

mod-print.js (onglet Impression) : un bloc « Gabarit de dessin » en tête du panneau HEXAGONAL (tâche 8 : le bloc est
posé par t421_impression.py dans `shellHex` ; le panneau rectangulaire ne le porte plus), avec deux liens de téléchargement
(PNG transparent, SVG en mm) vers GET /api/cards/gabarit/{format}.{png|svg}?dpi=&bleed_mm=&safe_mm= (adresse donnée par CF.gabaritUrl) ; `syncGabaritHex`
(appelée par `sync`, donc à chaque changement de format, de DPI ou de fond perdu) règle les adresses et n'affiche le bloc
que pour un hexagone. Des liens simples : l'adresse vient du CORE (CF.gabaritUrl), un lien de téléchargement n'est pas un appel. Rien ne change pour un rectangle : il n'a pas le bloc. Les sauts de ligne des insertions sont CRLF.
"""
from outils import S

F = "js/mod-print.js"
CRLF = chr(13) + chr(10)


def _crlf(t):
    return t.replace("\n", "\r\n")


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
    # t421 tâche 8 : le bloc du gabarit (et ses quatre clés) vit dans le panneau hexagonal : t421_impression.py.
    S(F, 2427, "function sync() {" + CRLF + "    const s = currentState(), f = CF.doc().format, g = CF.geom();",
      _crlf(_FONCTION), {}),
]
