"""L'éditeur de texte en place (js/mod-typo.js, VL.editerTexte : textarea.tx-editeur posé DANS #stage) garde ses
clics, postérieur à L6 : comme le panneau de js/mod-iacalque.js (garderClics, t190) et le dialogue IA de js/mod-ia.js
(iaclics.py), le pointerdown d'un clic dans le champ remontait au gestionnaire de l'outil Sélection (mod-tools, en
bulle sur #stage, setPointerCapture) — l'éditeur se FERMAIT au lieu de placer le curseur (vu à la preuve 8799).
L'édition de code est consignée ICI, en édition S sur la source de BASE, pour que la table reste réversible
(test_i18n_l6 [2]). Aucun texte affiché : pas de clé."""
from outils import L, S, X, H  # noqa: F401

FI = "js/mod-typo.js"


def c(s):
    """fins de ligne de la BASE (CRLF)"""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


ENTREES = [
    S(FI, 143, c("    stage.appendChild(ta);\n    editeur = { ta, id, neuf };"), c('''    stage.appendChild(ta);
    editeur = { ta, id, neuf };
    // le champ vit DANS #stage : sans garde, le pointerdown d'un clic dedans remonte au gestionnaire de l'outil
    // Sélection (mod-tools, en bulle sur #stage, setPointerCapture) et l'éditeur se FERME au lieu de placer le
    // curseur (vu à la preuve 8799). Mêmes gestes gardés que garderClics de mod-iacalque et le dialogue de mod-ia.
    for (const t of ["pointerdown", "mousedown", "dblclick", "contextmenu", "wheel"]) {
      ta.addEventListener(t, (ev) => ev.stopPropagation(), t === "wheel" ? { passive: true } : false);
    }'''), {}),
]
