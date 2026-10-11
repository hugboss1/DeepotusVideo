"""t182 (G0, génération IA enrichie, 11/10/2026) — changements FONCTIONNELS du Material Forge posés APRÈS L8.

La table réversible L8 (scripts/i18n_l8_paires.json) exige : source du poste == base 1515d67b + éditions. Une
modification du code d'après L8 passe donc par ici, comme une édition S() sans dictionnaire :
- MODEL_COST / MODEL_SEC : les cinq modèles d'image fal raster (crédits = usd × 100, 6 s) ;
- loadModels() : le sélecteur #model liste TOUS les modèles raster, de toutes les voies — les servis (`models` de
  /api/image-models), puis ceux dont la clé manque (`tous`), avec la mention dzT("matiere.t182_modele.cle_a_ajouter") ; un modèle
  vectoriel (sortie "svg") n'y est jamais (décision de l'utilisateur du 11/10 : un modèle sans clé reste choisissable).
"""
from outils import S

# La clé est dans la zone du lab (un lab = une zone, règle du générateur L8) : même texte que ia.cle.a_ajouter
# (commun.json, la pastille de dz-champ-ia).

_MF = "materialforge/materialforge.js"

ENTREES = [
    S(_MF, 138, '  "gpt-image-2.5-flare-fal": 10, "gpt-image-2.5-sunburst-fal": 10,',
      '  "gpt-image-2.5-flare-fal": 10, "gpt-image-2.5-sunburst-fal": 10,\r\n  /* t182 : modèles d’image fal (crédits = usd × 100, arrondi) */\r\n  "nano-banana-2.1": 4, "flux-3": 5, "seedream-5-pro": 7,\r\n  "ideogram-4.5": 22, "qwen-image-3": 4,', {}),
    S(_MF, 145, '  "gpt-image-2.5-flare-fal": 24, "gpt-image-2.5-sunburst-fal": 24,',
      '  "gpt-image-2.5-flare-fal": 24, "gpt-image-2.5-sunburst-fal": 24,\r\n  "nano-banana-2.1": 6, "flux-3": 6, "seedream-5-pro": 6,\r\n  "ideogram-4.5": 6, "qwen-image-3": 6,', {}),
    S(_MF, 553, '    models = (d && d.models) || [];\r\n    state.model = d.default || (models[0] && models[0].id) || "";',
      '    /* t182 : un modèle vectoriel (sortie "svg", lue au catalogue) ne fait pas une texture.\r\n       Décision de l\'utilisateur (11/10/2026) : TOUS les modèles raster, de toutes les\r\n       voies, sont choisissables — les servis d\'abord (`models`), puis ceux dont la clé\r\n       manque (`tous`), avec la mention « clé X à ajouter dans Réglages », jamais\r\n       désactivés ; le serveur refuse le tir en 503 tant que la clé manque. */\r\n    const servis = ((d && d.models) || []).filter((m) => m.sortie !== "svg");\r\n    const vus = new Set(servis.map((m) => m.id));\r\n    const sansCle = ((d && d.tous) || [])\r\n      .filter((e) => e.sortie !== "svg" && !e.dispo && !vus.has(e.id))\r\n      .map((e) => ({ id: e.id, label: e.label, cle: e.cle, sansCle: true }));\r\n    models = servis.concat(sansCle);\r\n    state.model = d.default || (servis[0] && servis[0].id) || (models[0] && models[0].id) || "";', {}),
    S(_MF, 564, '    `<option value="${esc(m.id)}"${m.id === state.model ? " selected" : ""}>${esc(m.label || m.id)}</option>`).join("");',
      '    `<option value="${esc(m.id)}"${m.id === state.model ? " selected" : ""}>${esc(m.label || m.id)}${\r\n      m.sansCle && m.cle ? " — " + esc(dzT("matiere.t182_modele.cle_a_ajouter", { cle: m.cle })) : ""}</option>`).join("");', {"matiere.t182_modele.cle_a_ajouter": ("clé {cle} à ajouter dans Réglages", "add the {cle} key in Settings")}),
]
