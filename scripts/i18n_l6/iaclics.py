"""Le dialogue IA du canevas (js/mod-ia.js, posé DANS #stage) garde ses clics, postérieur à L6 : comme le panneau de
js/mod-iacalque.js (garderClics, t190), le pointerdown d'un contrôle remontait au gestionnaire de l'outil Sélection
(mod-tools, en bulle sur #stage) qui pose setPointerCapture(#stage) — le click partait sur #stage, la croix ne fermait
pas. L'édition de code est consignée ICI, en édition S sur la source de BASE, pour que la table reste réversible
(test_i18n_l6 [2]). Aucun texte affiché : pas de clé."""
from outils import L, S, X, H  # noqa: F401

FI = "js/mod-ia.js"


def c(s):
    """fins de ligne de la BASE (CRLF)"""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


ENTREES = [
    S(FI, 199, c("  const el = hote();\n  if (el) {"), c('''  const el = hote();
  if (el) {
    // le dialogue vit DANS #stage : sans garde, le pointerdown d'un contrôle remonte au gestionnaire de l'outil
    // Sélection (mod-tools, en bulle sur #stage) qui pose setPointerCapture(#stage) — le click part alors sur
    // #stage, la croix ne ferme pas, « Générer » ne part pas (vu à la preuve 8799). Mêmes gestes gardés que
    // garderClics de mod-iacalque ; la poignée de glisser (pointerdown du dialogue, plus bas) n'en souffre pas.
    for (const t of ["pointerdown", "mousedown", "dblclick", "contextmenu", "wheel"]) {
      el.addEventListener(t, (ev) => ev.stopPropagation(), t === "wheel" ? { passive: true } : false);
    }'''), {}),
]
