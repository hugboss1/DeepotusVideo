"""Le dialogue IA du canevas (js/mod-ia.js, posé DANS #stage) garde ses clics, postérieur à L6 : comme le panneau de
js/mod-iacalque.js (garderClics, t190), le pointerdown d'un contrôle remontait au gestionnaire de l'outil Sélection
(mod-tools, en bulle sur #stage) qui pose setPointerCapture(#stage) — le click partait sur #stage, la croix ne fermait
pas. L'édition de code est consignée ICI, en édition S sur la source de BASE, pour que la table reste réversible
(test_i18n_l6 [2]). Aucun texte affiché : pas de clé. t190-bis : la boucle locale devient le garderClics partagé
(js/mod-flottant.js), qui garde aussi keydown."""
from outils import L, S, X, H  # noqa: F401

FI = "js/mod-ia.js"


def c(s):
    """fins de ligne de la BASE (CRLF)"""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


ENTREES = [
    S(FI, 22, 'import { dzi } from "./mod-icones.js";',
      c('import { dzi } from "./mod-icones.js";\nimport { garderClics } from "./mod-flottant.js";'), {}),
    S(FI, 199, c("  const el = hote();\n  if (el) {"), c('''  const el = hote();
  if (el) {
    // le dialogue vit DANS #stage : sans garde, le pointerdown d'un contrôle remonte au gestionnaire de l'outil
    // Sélection (mod-tools, en bulle sur #stage) qui pose setPointerCapture(#stage) — le click part alors sur
    // #stage, la croix ne ferme pas, « Générer » ne part pas (vu à la preuve 8799). Le garderClics PARTAGÉ
    // (mod-flottant) : mêmes gestes que le panneau de mod-iacalque, clavier compris (une lettre tapée dans une liste
    // changeait d'outil) ; les outils en CAPTURE sortent par VL.dansPanneau. La poignée n'en souffre pas.
    garderClics(el);'''), {}),
]
