"""t334 (A4 du lot Scenario, 29/10/2026) — « Passes Blender » sur les cartes du storyboard, posé APRÈS L8 (même
mécanisme que t335.py / t337.py : une édition S() par ancre de la BASE 1515d67b).

Une SEULE édition, en fin de renderBoard() : la boîte partagée /shared/dz-passes-plan.js (textes passesplan.*) pose
elle-même, sur chaque carte, le bouton « Passes Blender » (act-passes, glyphe dz-nav-panneau-calques) après « Revue du
plan », et sous la vignette la bande des passes du dernier rendu (GET /api/passes/chapitre/{id}). Rien d'autre de la
carte n'est touché : le gabarit de la carte reste celui de t335/t337.
"""
from outils import S

_AT = "atelier/atelier.js"

FIN_AV = "  });\r\n}\r\n\r\nasync function moveShot"
FIN_AP = ("  });\r\n"
          "  // t334 : le bouton « Passes Blender » de chaque carte et la bande des passes du dernier rendu (dz-passes-plan.js)\r\n"
          "  if (window.__dzPassesPlan) window.__dzPassesPlan.vignettes(list, chapter.id);\r\n"
          "}\r\n\r\nasync function moveShot")

ENTREES = [
    S(_AT, 915, FIN_AV, FIN_AP, {}),
]
