"""t183 (G1, génération IA enrichie, 11/10/2026) — changements FONCTIONNELS du Card Forge posés APRÈS L7.

Décision de l'utilisateur (11/10/2026) : un modèle d'image dont la clé manque reste CHOISISSABLE dans tout sélecteur,
avec la mention « clé X à ajouter dans Réglages » ; le serveur refuse le tir en 503 avant toute dépense. La route de
la pièce (`ai-models`, face.py et frame.py) liste désormais tout le catalogue raster avec `dispo` et `cle` ; « aucune
clé » se lit sur `cle_absente` (dérivé de `dispo`), la liste n'étant plus jamais vide.
- mod-face / mod-frame : l'option d'un modèle sans clé porte la mention ; le message « aucune clé » s'affiche aussi
  quand aucun modèle n'est disponible (AI_META.cle_absente) ;
- core.js : le repli CF.images.models() (backend sans route ai-models) lit `tous` de /image-models de la même façon.
La table réversible L7 exige : source du poste == base f788790b + éditions ; d'où cette saisie (comme t182 pour L8).
"""
from outils import S

_MENTION = ("clé {cle} à ajouter dans Réglages", "add the {cle} key in Settings")

ENTREES = [
    S("js/mod-face.js", 4192, ") + '</option>').join(\"\")",
      ") + (m.dispo === false && m.cle ? \" — \" + esc(dzT(\"cartes.face.cle_a_ajouter\", { cle: m.cle })) : \"\")"
      " + '</option>').join(\"\")",
      {"cartes.face.cle_a_ajouter": _MENTION}),
    S("js/mod-face.js", 4057, "if (!MODELS.length) {", "if (!MODELS.length || AI_META.cle_absente) {", {}),
    S("js/mod-frame.js", 6310, ') + "</option>").join("");',
      ') + (m.dispo === false && m.cle ? " — " + esc(dzT("cartes.frame2.cle_a_ajouter", { cle: m.cle })) : "")'
      ' + "</option>").join("");',
      {"cartes.frame2.cle_a_ajouter": _MENTION}),
    S("js/mod-frame.js", 6315, "if (!AI_MODELS.length) {", "if (!AI_MODELS.length || AI_META.cle_absente) {", {}),
    S("js/core.js", 1462, 'try { return await jsonFetch("GET", "/image-models"); }',
      'try {\r\n'
      '        /* t183 : tout le catalogue raster (`tous`), les modèles sans clé compris (dispo, cle) — décision du 11/10 */\r\n'
      '        const d = await jsonFetch("GET", "/image-models");\r\n'
      '        const tous = ((d && d.tous) || []).filter((e) => e.sortie !== "svg");\r\n'
      '        return tous.length ? Object.assign({}, d, { models: tous.map((e) => ({ id: e.id, label: e.label,\r\n'
      '          provider: e.voie, note: "", usd_par_image: Number(e.usd) || null, dispo: !!e.dispo, cle: e.cle })) }) : d;\r\n'
      '      }', {}),
]
