"""t182 (G0, génération IA enrichie, 11/10/2026) — changements FONCTIONNELS du Material Forge posés APRÈS L8.

La table réversible L8 (scripts/i18n_l8_paires.json) exige : source du poste == base 1515d67b + éditions. Une
modification du code d'après L8 passe donc par ici, comme une édition S() sans dictionnaire :
- MODEL_SEC : les cinq modèles d'image fal raster (6 s) ;
(t183 a repris les éditions de MODEL_COST, supprimé, et de loadModels : voir t183.py.)
- loadModels() : le sélecteur #model liste TOUS les modèles raster, de toutes les voies — les servis (`models` de
  /api/image-models), puis ceux dont la clé manque (`tous`), avec la mention dzT("matiere.t182_modele.cle_a_ajouter") ; un modèle
  vectoriel (sortie "svg") n'y est jamais (décision de l'utilisateur du 11/10 : un modèle sans clé reste choisissable).
"""
from outils import S

# La clé est dans la zone du lab (un lab = une zone, règle du générateur L8) : même texte que ia.cle.a_ajouter
# (commun.json, la pastille de dz-champ-ia).

_MF = "materialforge/materialforge.js"

ENTREES = [
    S(_MF, 145, '  "gpt-image-2.5-flare-fal": 24, "gpt-image-2.5-sunburst-fal": 24,',
      '  "gpt-image-2.5-flare-fal": 24, "gpt-image-2.5-sunburst-fal": 24,\r\n  "nano-banana-2.1": 6, "flux-3": 6, "seedream-5-pro": 6,\r\n  "ideogram-4.5": 6, "qwen-image-3": 6,', {}),
]
