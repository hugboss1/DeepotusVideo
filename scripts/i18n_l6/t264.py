"""t264 (20/10/2026) — les pastilles fond / contour à la Photoshop (modèle du Photolab #410), postérieures à L6 : les
éditions de code de js/mod-style.js (le carré .vl-pastilles avant la rangée Fond, qui reprend la pastille de fond et
celle du contour, l'échange et les couleurs par défaut ; les deux anciennes pastilles retirées de leurs rangées) et de
js/mod-couleur.js (pastilles_echanger, PASTILLES_DEFAUT, purs) sont consignées ICI, en éditions S sur la source de BASE,
pour que la table reste réversible (test_i18n_l6 [2]). Les titres des deux pastilles (fond_titre, contour_titre) étaient
saisis par apparence.py (lignes 119 et 129) : ces éditions-là chevauchaient la pastille réécrite, elles passent ici avec
leurs clés, inchangées."""
from outils import L, S, X, H  # noqa: F401

ST = "js/mod-style.js"
CO = "js/mod-couleur.js"


def c(s):
    """fins de ligne de la BASE (CRLF)"""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


PASTILLES = c('''
      ${/* t264 : les pastilles à la Photoshop (modèle du Photolab #410) — le fond (premier plan) chevauche le contour
           (arrière-plan) ; échange en haut à droite, couleurs par défaut en bas à gauche. Hors .ap-ligne : la rangée
           reste à l'onglet Couleur (mod-pile ne déplace que les .ap-ligne) et l'audit d'ergonomie ne mesure pas ses
           boutons de 18 px. */ ""}
      <div class="vl-pastilles">
        <button class="vl-pastille-contour${contourVide ? " vide" : ""}" id="apContour"
                style="background:${contourCouleur}" data-hex="${contourCouleur}"
                title="${T("vectorlab.style.contour_titre")}" aria-label="${T("vectorlab.style.contour_titre")}"></button>
        <button class="vl-pastille-fond${s.fond === "none" ? " vide" : ""}" id="apFond" style="background:${fondCouleur}"
                data-hex="${fondCouleur}"
                title="${T("vectorlab.style.fond_titre")}" aria-label="${T("vectorlab.style.fond_titre")}"></button>
        <button class="vl-pastille-echanger" id="apEchanger" ${pastilles_echanger(s) ? "" : "disabled"}
                title="${T("vectorlab.style.pastilles_echanger")}" aria-label="${T("vectorlab.style.pastilles_echanger")}">${dzi("dz-edit-echanger-couleurs", 12)}</button>
        <button class="vl-pastille-defaut" id="apDefaut"
                title="${T("vectorlab.style.pastilles_defaut")}" aria-label="${T("vectorlab.style.pastilles_defaut")}">${dzi("dz-edit-couleurs-defaut", 12)}</button>
      </div>''')

FOND_AVANT = c('''        <button class="nu-pastille" id="apFond" style="background:${fondCouleur}"
                data-hex="${fondCouleur}"
                title="Couleur de fond — ouvre le nuancier (RGB, CMJN, hex, palettes)"></button>
''')

CONTOUR_AVANT = c('''        <button class="nu-pastille" id="apContour"
                style="background:${s.contour && s.contour !== "none" ? s.contour : "#1F1512"}"
                data-hex="${s.contour && s.contour !== "none" ? s.contour : "#1F1512"}"
                title="Couleur de contour — ouvre le nuancier"></button>
''')

ECOUTE = c('''    $("#apEchanger").addEventListener("click", () => {
      const patch = pastilles_echanger(styleReflete());
      if (patch) appliquer(patch);
    });
    $("#apDefaut").addEventListener("click", () => appliquer({ ...PASTILLES_DEFAUT }));
''')

PUR = c('''/* ── pur : les pastilles fond / contour (t264, 20/10/2026, modèle du Photolab #410) ── */
const _hexValide = (c) => typeof c === "string" && /^#[0-9a-fA-F]{3,8}$/.test(c);
// le patch d'op_style qui échange fond et contour ; null s'il n'y a rien à échanger ou si le fond est un dégradé
// (un contour ne porte qu'une couleur). contour: null = sans contour (comme le bouton « Sans contour »).
export function pastilles_echanger(style) {
  const s = style || {};
  if (typeof s.fond === "string" && s.fond.startsWith("grad:")) return null;
  const fond = _hexValide(s.fond) ? s.fond : null, contour = _hexValide(s.contour) ? s.contour : null;
  if (!fond && !contour) return null;
  return { fond: contour || "none", contour: fond };
}
// couleurs par défaut : fond blanc, contour noir (le D d'Illustrator)
export const PASTILLES_DEFAUT = Object.freeze({ fond: "#FFFFFF", contour: "#000000" });

''')

ENTREES = [
    S(ST, 15, 'import { dzi } from "./mod-icones.js";',
      c('import { dzi } from "./mod-icones.js";\nimport { pastilles_echanger, PASTILLES_DEFAUT } from "./mod-couleur.js";'), {}),
    S(ST, 95, "    const gid = fondDegradeId();",
      c('    const contourVide = !s.contour || s.contour === "none";\n'
        '    const contourCouleur = contourVide ? "#1F1512" : s.contour;\n'
        "    const gid = fondDegradeId();"), {}),
    S(ST, 116, "    hote.innerHTML += `", "    hote.innerHTML += `" + PASTILLES,
      {"vectorlab.style.fond_titre": ("Couleur de fond — ouvre le nuancier (RGB, CMJN, hex, palettes)",
                                      "Fill color — opens the color picker (RGB, CMYK, hex, palettes)"),
       "vectorlab.style.contour_titre": ("Couleur de contour — ouvre le nuancier", "Stroke color — opens the color picker"),
       "vectorlab.style.pastilles_echanger": ("Échanger le fond et le contour", "Swap fill and stroke"),
       "vectorlab.style.pastilles_defaut": ("Couleurs par défaut : fond blanc, contour noir",
                                            "Default colors: white fill, black stroke")}),
    S(ST, 118, FOND_AVANT, "", {}),
    S(ST, 127, CONTOUR_AVANT, "", {}),
    S(ST, 256, '    $("#apContourAucun").addEventListener("click",',
      ECOUTE + '    $("#apContourAucun").addEventListener("click",', {}),
    S(CO, 163, "/* ── DOM : le nuancier (E4) — un popover unique, ouvert par",
      PUR + "/* ── DOM : le nuancier (E4) — un popover unique, ouvert par", {}),
]
