"""Trame horizontale (29/10/2026, demande de l'utilisateur dans l'Établi) — changement FONCTIONNEL de lib3d/viewer.js
posé APRÈS L9 : hors vues d'axe « face » et « profil », la trame reste le sol, même caméra sous l'horizon.
La table réversible L9 exige : source du poste == base 7f99c72c + éditions ; d'où cette saisie (comme t339, t340).
Banc : test_etabli_canevas::test_en_ORBITE_la_trame_reste_le_SOL_meme_sous_l_horizon. Aucun texte affiché.
"""
from outils import S

V = "lib3d/viewer.js"

ENTREES = [
    S(V, 608, 'const _reperes = new WeakMap();',
      'const _reperes = new WeakMap();\r\n\r\n/* LA VUE D\'AXE TENUE, par vue : la direction (unitaire, de la cible vers la\r\n   caméra) posée par orienter() pour « face » et « profil », et RIEN d\'autre.\r\n\r\n   LE DÉFAUT QUE CETTE TABLE CORRIGE, VU PAR L\'UTILISATEUR LE 29/10 : en orbite\r\n   libre, une caméra amenée près de l\'horizon — ou juste dessous — passait sous\r\n   le seuil de planDeTrame et la trame se redressait en mur VERTICAL derrière\r\n   le modèle. Le redressement n\'a de sens que dans les vues d\'axe, où le sol\r\n   est vu exactement par la tranche ; en orbite ou en iso, le sol reste le sol,\r\n   même rasant.\r\n\r\n   UNE DIRECTION ET NON UN DRAPEAU : la molette et le panoramique gardent la vue\r\n   d\'axe (le regard ne tourne pas), une orbite la quitte (il tourne). Écouter\r\n   l\'évènement « start » des contrôles aurait confondu les deux — la molette\r\n   l\'émet aussi. Une WeakMap pour la même raison que `_reperes` : le contrat de\r\n   forme d\'`api` n\'a pas à porter un état de dessin. */\r\nconst _vueAxiale = new WeakMap();\r\nconst VUES_AXIALES = new Set(["face", "profil"]);\r\n/* cos(2,6°) : la tolérance d\'un regard « toujours dans l\'axe ». Un cadrage\r\n   recalculé ou un arrondi flottant reste dedans ; un geste d\'orbite délibéré\r\n   en sort dès les premiers pixels. */\r\nconst COS_AXE_TENU = 0.999;', {}),
    S(V, 686, '  const plan = planDeTrame(axeDeVue(api.camera.matrixWorld.elements), e.plan);',
      '  const avant = axeDeVue(api.camera.matrixWorld.elements);\r\n  /* HORS VUE D\'AXE, LE SOL : voir `_vueAxiale`. `avant` regarde VERS la cible,\r\n     la direction tenue part de la cible : d\'où le signe. */\r\n  let plan = "y";\r\n  const tenue = _vueAxiale.get(api);\r\n  if (tenue) {\r\n    if (-(avant.x * tenue.x + avant.y * tenue.y + avant.z * tenue.z)\r\n        >= COS_AXE_TENU) plan = planDeTrame(avant, e.plan);\r\n    else _vueAxiale.delete(api);\r\n  }', {}),
    S(V, 1218, '  if (!ORIENTATIONS[nom]) return null;\r\n  api.vueCadrage = nom;',
      '  if (!ORIENTATIONS[nom]) return null;\r\n  api.vueCadrage = nom;\r\n  if (VUES_AXIALES.has(nom)) {\r\n    const d = ORIENTATIONS[nom].dir, n = Math.hypot(d.x, d.y, d.z);\r\n    _vueAxiale.set(api, { x: d.x / n, y: d.y / n, z: d.z / n });\r\n  } else _vueAxiale.delete(api);', {}),
]
