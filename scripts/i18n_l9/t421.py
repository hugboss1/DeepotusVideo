"""t421 (cartes hexagonales, 07/11/2026) — l'envoi vers le Tile Lab DIT un nom d'image refusé.

Le serveur refuse désormais les noms d'image invalides (garde unique `backend/app/services/noms.py`) ; le contrat
/shared/dz-envoi.js rend alors `{ refus: nom }`. tilelab/envoi.js (GÉNÉRÉ par L9) affiche la phrase
`commun.envoi.refuse` (dictionnaire commun.json, hors zones L9) dans le toast de l'écran au lieu de rester muet.
`t(...)` (alias de dzT) : la clé est celle de commun.json, pas du dico L9, que le générateur réécrirait en
__dzT9 s'il la voyait écrite `dzT(`. La table réversible L9 exige : source du poste == base + éditions ; d'où cette saisie sans texte neuf pour L9.
"""
from outils import S

EV = "tilelab/envoi.js"

ENTREES = [
    S(EV, 6, "export function appliquer(recu, tl) {\r\n  if (!recu ||",
      "// t421 : un nom refusé est DIT dans le toast de l'écran (jamais une source vide en silence).\r\n"
      "function dire(nom) {\r\n"
      "  const el = typeof document !== \"undefined\" ? document.getElementById(\"toast\") : null;\r\n"
      "  const t = globalThis.dzT;\r\n"
      "  if (!el || typeof t !== \"function\") return;\r\n"
      "  el.textContent = t(\"commun.envoi.refuse\", { nom });\r\n"
      "  el.classList.remove(\"hidden\"); el.classList.add(\"err\");\r\n"
      "  setTimeout(() => el.classList.add(\"hidden\"), 4200);\r\n"
      "}\r\n\r\n"
      "export function appliquer(recu, tl) {\r\n"
      "  if (recu && recu.refus) { dire(recu.refus); return false; }\r\n"
      "  if (!recu ||", {}),
]
