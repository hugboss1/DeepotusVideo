"""t183 (G1, génération IA enrichie, 11/10/2026) — changements FONCTIONNELS de l'Atelier posés APRÈS L8.

La table réversible L8 (scripts/i18n_l8_paires.json) exige : source du poste == base 1515d67b + éditions. Une
modification du code d'après L8 passe donc par ici, comme une édition S() (même mécanisme que t182.py).

Décision de l'utilisateur (11/10/2026) : un modèle dont la clé manque reste CHOISISSABLE dans tout sélecteur, avec
son prix et la mention « clé X à ajouter dans Réglages » ; le serveur refuse le tir en 503 AVANT toute dépense.
- atelier/index.html charge /shared/dz-modeles-ia.js (une page HTML n'est jamais réécrite par L8 : éditée telle quelle) ;
- 🎨 DA, #daProvider : TOUS les générateurs raster (`tous` de /atelier/providers : dispo, clé, prix du catalogue
  unique), les sans-clé compris, jamais désactivés ; la note des seeds lit la même liste ;
- l'image de production d'un plan : son prix vient du catalogue (GET /ia/catalogue?nature=image), plus d'une clé de
  la grille de tarifs choisie dans ce fichier ;
- Material Forge : plus de MODEL_COST écrit en dur — le crédit de l'estimation se lit dans le `usd` du catalogue
  (crédits = usd × 100, au moins 1) ; #model liste TOUT le catalogue raster (`tous`) par DzModelesIA (un <optgroup>
  par voie, prix, mention), les sans-clé jamais désactivés. Reprend les éditions de t182 sur ces deux endroits.
"""
from outils import S

_AT = "atelier/atelier.js"
_MF = "materialforge/materialforge.js"

ENTREES = [
    S(_AT, 952, 'const grille = await api.get("/cost/pricing");\r\n'
                '    usd = grille[provider === "nano-banana" ? "nano_banana_usd" : "nano_banana_pro_usd"];',
      '/* t183 : le prix par image vient du catalogue unique (usd), pas d\'une clé de grille écrite ici */\r\n'
      '    const cat = await api.get("/ia/catalogue?nature=image");\r\n'
      '    const ent = ((cat && cat.modeles) || []).find(e => e.id === provider);\r\n'
      '    usd = ent && ent.usd ? ent.usd : null;', {}),
    S(_AT, 1387, '$("#daProvider").innerHTML = pv.providers.map(p =>\r\n'
                 '      `<option value="${p.id}" ${p.id === cur ? "selected" : ""}>${esc(p.label)}</option>`).join("");',
      '/* t183 : TOUS les générateurs raster (pv.tous : dispo, clé, prix — catalogue unique), les sans-clé compris,\r\n'
      '       choisissables avec la mention « clé X à ajouter dans Réglages » (décision du 11/10/2026) ; le serveur\r\n'
      '       refuse le tir en 503 avant toute dépense. Un <optgroup> par voie (DzModelesIA). */\r\n'
      '    const tous = (pv.tous && pv.tous.length) ? pv.tous : pv.providers.map(p => Object.assign({ dispo: true }, p));\r\n'
      '    if (window.DzModelesIA) window.DzModelesIA.remplir($("#daProvider"), tous, { valeur: cur });\r\n'
      '    else $("#daProvider").innerHTML = tous.map(p =>\r\n'
      '      `<option value="${p.id}" ${p.id === cur ? "selected" : ""}>${esc(p.label)}${p.dispo === false && p.cle\r\n'
      '        ? " — " + esc(dzT("atelier.t183_da.cle_a_ajouter", { cle: p.cle })) : ""}</option>`).join("");',
      {"atelier.t183_da.cle_a_ajouter": ("clé {cle} à ajouter dans Réglages", "add the {cle} key in Settings")}),
    S(_AT, 1390, 'const sel = pv.providers.find(p => p.id === $("#daProvider").value);',
      'const sel = tous.find(p => p.id === $("#daProvider").value);', {}),
    S(_MF, 133, 'const MODEL_COST = {\r\n'
                '  "flux": 4, "nano-banana": 9, "gpt-image-2": 12,\r\n'
                '  "gpt-image-1": 8, "gpt-image-1-mini": 3,\r\n'
                '  "nano-banana-pro": 13, "gpt-image-2-fal": 13,\r\n'
                '  "gpt-image-2.5-flare": 10, "gpt-image-2.5-sunburst": 10,\r\n'
                '  "gpt-image-2.5-flare-fal": 10, "gpt-image-2.5-sunburst-fal": 10,\r\n'
                '};\r\n',
      '/* t183 : plus de table de crédits écrite ici — le crédit vient du `usd` du catalogue (voir estimate) */\r\n', {}),
    S(_MF, 553, '    models = (d && d.models) || [];\r\n'
                '    state.model = d.default || (models[0] && models[0].id) || "";',
      '    /* t182 : un modèle vectoriel (sortie "svg", lue au catalogue) ne fait pas une texture.\r\n'
      '       Décision de l\'utilisateur (11/10/2026) : TOUS les modèles raster, de toutes les\r\n'
      '       voies, sont choisissables — ceux dont la clé manque avec la mention « clé X à\r\n'
      '       ajouter dans Réglages », jamais désactivés ; le serveur refuse le tir en 503 tant\r\n'
      '       que la clé manque. t183 : la liste est `tous` (le catalogue unique : dispo, clé,\r\n'
      '       voie, prix `usd`), `models` (servis) seulement face à un serveur d\'avant t182. */\r\n'
      '    const tous = ((d && d.tous) || []).filter((e) => e.sortie !== "svg");\r\n'
      '    models = tous.length ? tous : ((d && d.models) || []).filter((m) => m.sortie !== "svg");\r\n'
      '    state.model = d.default || ((models.find((m) => m.dispo !== false) || models[0]) || {}).id || "";', {}),
    S(_MF, 563, '$("#model").innerHTML = models.map((m) =>\r\n'
                '    `<option value="${esc(m.id)}"${m.id === state.model ? " selected" : ""}>${esc(m.label || m.id)}</option>`).join("");',
      '/* t183 : un <optgroup> par voie, le prix sur chaque option (DzModelesIA, /shared/dz-modeles-ia.js) */\r\n'
      '  if (window.DzModelesIA) window.DzModelesIA.remplir($("#model"), models, { valeur: state.model });\r\n'
      '  else $("#model").innerHTML = models.map((m) =>\r\n'
      '    `<option value="${esc(m.id)}"${m.id === state.model ? " selected" : ""}>${esc(m.label || m.id)}${\r\n'
      '      m.dispo === false && m.cle ? " — " + esc(dzT("matiere.t182_modele.cle_a_ajouter", { cle: m.cle })) : ""}</option>`).join("");',
      {"matiere.t182_modele.cle_a_ajouter": ("clé {cle} à ajouter dans Réglages", "add the {cle} key in Settings")}),
    S(_MF, 633, 'let cr = fromLib ? 0 : (MODEL_COST[m] != null ? MODEL_COST[m] : 6);',
      '/* t183 : le crédit indicatif = usd du catalogue × 100 (au moins 1) ; 6 pour un modèle sans prix connu */\r\n'
      '  const ent = (state.models || []).find((x) => x.id === m);\r\n'
      '  let cr = fromLib ? 0 : (ent && Number(ent.usd) ? Math.max(1, Math.round(Number(ent.usd) * 100)) : 6);', {}),
]
