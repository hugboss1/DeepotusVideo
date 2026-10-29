"""t374 (lot A « Finitions esthétiques », 29/10/2026) — angles vifs : le seul rayon écrit en dur dans studio3d.js,
celui du toast, passe au jeton de la charte (`var(--r)`, qui vaut 0 depuis t370). Aucun texte affiché.
studio3d.js est GÉNÉRÉ par L9 : la retouche passe par cette saisie, jamais à la main.
"""
from outils import S

SJ = "studio3d/studio3d.js"

ENTREES = [
    S(SJ, 903, "padding:9px 14px; border-radius:9px;", "padding:9px 14px; border-radius:var(--r);", {}),
]
