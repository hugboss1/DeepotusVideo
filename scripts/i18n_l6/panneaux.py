"""t190-bis — les PANNEAUX FLOTTANTS de #stage (dialogue IA de mod-ia, panneau « Image IA sur le calque » de
mod-iacalque, éditeur de texte en place de mod-typo) gardent leurs gestes quel que soit l'outil, postérieur à L6.
Les outils qui écoutent #stage EN CAPTURE (Plume, Texte, Nœud, Pipette, outils R7, Pixel, pinceau vectoriel,
tranches, Alt+glisser, formes de mod-outils2, le panoramique et la molette de core.js) jouaient AVANT le panneau :
garderClics (en bulle, sur le panneau) arrivait trop tard, le panneau redevenait inerte dès qu'on changeait d'outil.
Chaque gestionnaire qui COMMENCE un geste (pointerdown, dblclick, contextmenu, molette) sort désormais tout de suite
si VL.dansPanneau(ev) (js/mod-flottant.js, posé dans VL par core.js) ; mod-tools (en bulle) aussi, par symétrie.
Les pointermove / pointerup ne sont PAS gardés : un geste commencé sur la scène et relâché au-dessus d'un panneau
doit finir. L'édition de code est consignée ICI, en éditions S sur la source de BASE, pour que la table reste
réversible (test_i18n_l6 [2]). Aucun texte affiché : pas de clé."""
from outils import L, S, X, H  # noqa: F401

GARDE = "if (VL.dansPanneau(ev)) return;"
NOTE = "  // t190-bis : un panneau flottant garde ses gestes (mod-flottant)"


def c(s):
    """fins de ligne de la BASE (CRLF)"""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


def garde(fichier, ligne, geste, indent="  "):
    """la garde en PREMIÈRE instruction d'un gestionnaire `stage.addEventListener("<geste>", (ev) => {` multiligne"""
    tete = f'stage.addEventListener("{geste}", (ev) => {{'
    return S(fichier, ligne, tete, c(f"{tete}\n{indent}  {GARDE}{NOTE}"), {})


def garde_ligne(fichier, ligne, debut):
    """la garde en tête d'un gestionnaire écrit sur UNE ligne"""
    return S(fichier, ligne, debut, debut + " " + GARDE, {})


CORE = "js/core.js"

ENTREES = [
    # ── core.js : l'utilitaire dans VL, la molette (zoom) et le panoramique (clic du milieu / Espace + clic) ──
    S(CORE, 39, 'import { initOutils } from "./mod-tools.js";',
      c('import { initOutils } from "./mod-tools.js";\nimport { dansPanneau } from "./mod-flottant.js";'), {}),
    S(CORE, 626, 'stage.addEventListener("wheel", (ev) => {',
      c('stage.addEventListener("wheel", (ev) => {\n  if (dansPanneau(ev)) return;        // t190-bis : la molette d\'un panneau flottant ne zoome pas'), {}),
    S(CORE, 638, 'stage.addEventListener("pointerdown", (ev) => {',
      c('stage.addEventListener("pointerdown", (ev) => {\n  if (dansPanneau(ev)) return;        // t190-bis : un panneau flottant garde ses gestes (mod-flottant)'), {}),
    S(CORE, 768, "  etat, api, $,", "  etat, api, $, dansPanneau,", {}),

    # ── les outils en CAPTURE ──
    garde("js/mod-apparence2.js", 91, "pointerdown", "  "),
    garde("js/mod-exportplus.js", 144, "pointerdown", "  "),
    garde("js/mod-noeudui.js", 31, "pointerdown", "  "),
    garde("js/mod-noeudui.js", 109, "dblclick", "  "),
    garde("js/mod-outils2.js", 58, "pointerdown", "  "),
    garde("js/mod-outils3ui.js", 62, "pointerdown", "  "),
    garde("js/mod-outils3ui.js", 145, "dblclick", "  "),
    garde_ligne("js/mod-pipetteui.js", 94, 'stage.addEventListener("contextmenu", (ev) => {'),
    garde("js/mod-pipetteui.js", 95, "pointerdown", "  "),
    garde_ligne("js/mod-pixelui.js", 324, 'stage.addEventListener("contextmenu", (ev) => {'),
    garde("js/mod-pixelui.js", 326, "pointerdown", "  "),
    garde("js/mod-plumeui.js", 70, "pointerdown", "  "),
    garde("js/mod-plumeui.js", 120, "contextmenu", "  "),
    garde_ligne("js/mod-plumeui.js", 128, 'stage.addEventListener("dblclick", (ev) => {'),
    garde("js/mod-selectionui.js", 21, "pointerdown", "  "),
    garde("js/mod-selectionui.js", 63, "dblclick", "  "),
    garde("js/mod-texteui.js", 22, "pointerdown", "  "),

    # ── l'outil Sélection (mod-tools, en BULLE) : garderClics l'arrête déjà, la garde le dit aussi ──
    garde("js/mod-tools.js", 90, "pointerdown", "  "),
    garde("js/mod-tools.js", 548, "dblclick", "  "),
]
