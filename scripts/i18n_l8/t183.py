"""t183 (G1, génération IA enrichie, 11/10/2026) — changements FONCTIONNELS de l'Atelier posés APRÈS L8.

La table réversible L8 (scripts/i18n_l8_paires.json) exige : source du poste == base 1515d67b + éditions. Une
modification du code d'après L8 passe donc par ici, comme une édition S() (même mécanisme que t182.py).

Décision de l'utilisateur (11/10/2026) : un modèle dont la clé manque reste CHOISISSABLE dans tout sélecteur, avec
son prix et la mention « clé X à ajouter dans Réglages » ; le serveur refuse le tir en 503 AVANT toute dépense.
- atelier/index.html charge /shared/dz-modeles-ia.js (une page HTML n'est jamais réécrite par L8 : éditée telle quelle) ;
- 🎨 DA, #daProvider : TOUS les générateurs raster (`tous` de /atelier/providers : dispo, clé, prix du catalogue
  unique), les sans-clé compris, jamais désactivés ; la note des seeds lit la même liste ;
- l'image de production d'un plan : son prix vient du catalogue (GET /ia/catalogue?nature=image), plus d'une clé de
  la grille de tarifs choisie dans ce fichier.
"""
from outils import S

_AT = "atelier/atelier.js"

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
]
