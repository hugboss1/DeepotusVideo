"""t183 (G1, génération IA enrichie, 11/10/2026) — changement FONCTIONNEL du Spritelab posé APRÈS L9.

Le prompt → sprites n'envoyait AUCUN modèle : /images/generate prenait le défaut du serveur, et le devis estimait
celui des Réglages. Le panneau Prompt gagne un sélecteur (#pmModel, index.html) rempli par DzModelesIA depuis le
catalogue unique (GET /api/ia/catalogue?nature=image) : un <optgroup> par voie, le prix sur chaque option, les
modèles sans clé VISIBLES ET CHOISISSABLES (décision de l'utilisateur, 11/10/2026 — le serveur refuse le tir en 503
avant toute dépense), jamais un modèle vectoriel. Le choix part dans le corps de /images/generate et dans le devis.
La table réversible L9 exige : source du poste == base 7f99c72c + éditions ; d'où cette saisie (comme t182 pour L8).
index.html n'est jamais réécrit par L9 : le <select> y est posé tel quel, son title traduit par l'entrée H.
"""
from outils import S, H

SL = "spritelab/spritelab.js"

ENTREES = [
    S(SL, 1013, 'try { imageModel = ((await api.get("/atelier/settings")).settings || {}).image_model_default || ""; }'
                ' catch (e) { imageModel = ""; }',
      'try { imageModel = ((await api.get("/atelier/settings")).settings || {}).image_model_default || ""; }'
      ' catch (e) { imageModel = ""; }\r\n'
      '  /* t183 : le modèle du prompt se CHOISIT (DzModelesIA : un <optgroup> par voie, prix, sans-clé choisissables).\r\n'
      '     Valeur initiale = le modèle d\'image GLOBAL du serveur (/image-models : configured, sinon default) — celui que\r\n'
      '     /images/generate prendrait sans `model` : l\'envoyer tel quel ne change rien ; le choix part dans le tir et le\r\n'
      '     devis. Catalogue injoignable : une seule option « défaut des Réglages » (aucun modèle envoyé). */\r\n'
      '  const pmSel = $("#pmModel");\r\n'
      '  if (pmSel) {\r\n'
      '    try {\r\n'
      '      const im = await api.get("/image-models");\r\n'
      '      imageModel = (im && (im.configured || im.default)) || imageModel;\r\n'
      '      if (!window.DzModelesIA) throw new Error("DzModelesIA absent");\r\n'
      '      await window.DzModelesIA.select(pmSel, "image", { valeur: imageModel,\r\n'
      '        onChange: (v) => { imageModel = v; majDevisPrompt(); } });\r\n'
      '      imageModel = pmSel.value || imageModel;\r\n'
      '    } catch (e) {\r\n'
      '      pmSel.innerHTML = `<option value="">${esc(__dzT9("sprites.t183_pm.defaut", "défaut des Réglages"))}</option>`;\r\n'
      '      imageModel = "";\r\n'
      '    }\r\n'
      '  }', {"sprites.t183_pm.defaut": ("défaut des Réglages", "Settings default")}),
    S(SL, 1042, 'window.SLD.corpsPrompt(sujet, [...pucesOn], $("#pmN").value, $("#pmSize").value)',
      'Object.assign(window.SLD.corpsPrompt(sujet, [...pucesOn], $("#pmN").value, $("#pmSize").value),\r\n'
      '      imageModel ? { model: imageModel } : {})', {}),
    H("sprites.t183_pm.modele", "Modèle", "Model"),
    H("sprites.t183_pm.modele_t", "Modèle d'image du prompt — prix sur chaque option ; un modèle sans clé reste "
      "choisissable (clé à ajouter dans Réglages)",
      "Image model for the prompt — price on each option; a model without a key stays selectable (add the key in "
      "Settings)"),
]
