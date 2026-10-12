"""PR #315 (Impression 3D : id en double), postérieure à L6 : la table des hauteurs par couleur du mode Pixel-art
passe de l'id `impHauteurs` (déjà pris par le champ « nom=mm » du mode Calques) à `impHauteursPx`. Ces éditions de
code de js/mod-impression.js sont consignées ICI, en éditions S sur la source de BASE, pour que la table reste
réversible (test_i18n_l6 [2]) ; elles ne créent aucune clé. Le champ du mode Calques (lignes 241 et 362) garde
`impHauteurs`."""
from outils import L, S, X, H  # noqa: F401

IMP = "js/mod-impression.js"

ENTREES = [
    S(IMP, 227, '$("#impHauteurs").querySelectorAll', '$("#impHauteursPx").querySelectorAll', {}),
    S(IMP, 355, 'imp-hauteurs" id="impHauteurs">', 'imp-hauteurs" id="impHauteursPx">', {}),
    S(IMP, 390, '$("#impHauteurs").innerHTML', '$("#impHauteursPx").innerHTML', {}),
    S(IMP, 393, '$("#impHauteurs").innerHTML', '$("#impHauteursPx").innerHTML', {}),
]
