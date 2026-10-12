"""L'éditeur de texte en place (js/mod-typo.js, VL.editerTexte : textarea.tx-editeur posé DANS #stage) garde ses
clics, postérieur à L6 : comme le panneau de js/mod-iacalque.js (garderClics, t190) et le dialogue IA de js/mod-ia.js
(iaclics.py), le pointerdown d'un clic dans le champ remontait au gestionnaire de l'outil Sélection (mod-tools, en
bulle sur #stage, setPointerCapture) — l'éditeur se FERMAIT au lieu de placer le curseur (vu à la preuve 8799).
L'édition de code est consignée ICI, en édition S sur la source de BASE, pour que la table reste réversible
(test_i18n_l6 [2]). Aucun texte affiché : pas de clé. t190-bis : la boucle locale devient le garderClics partagé
(js/mod-flottant.js)."""
from outils import L, S, X, H  # noqa: F401

FI = "js/mod-typo.js"


def c(s):
    """fins de ligne de la BASE (CRLF)"""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


ENTREES = [
    S(FI, 11, 'import { dzi } from "./mod-icones.js";',
      c('import { dzi } from "./mod-icones.js";\nimport { garderClics } from "./mod-flottant.js";'), {}),
    S(FI, 143, c("    stage.appendChild(ta);\n    editeur = { ta, id, neuf };"), c('''    stage.appendChild(ta);
    editeur = { ta, id, neuf };
    // le champ vit DANS #stage : sans garde, le pointerdown d'un clic dedans remonte au gestionnaire de l'outil
    // Sélection (mod-tools, en bulle sur #stage, setPointerCapture) et l'éditeur se FERME au lieu de placer le
    // curseur (vu à la preuve 8799). Le garderClics PARTAGÉ (mod-flottant), comme le panneau de mod-iacalque et le
    // dialogue de mod-ia ; les outils en CAPTURE sortent par VL.dansPanneau (classe .tx-editeur).
    garderClics(ta);'''), {}),
]
